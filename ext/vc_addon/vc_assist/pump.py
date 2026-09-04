# -*- coding: utf-8 -*-
"""Bryggan inne i VC. Kors av ett VC_SCRIPT-beteendes OnRun.

Modellen ar matt, inte antagen:

* Motorn ar Stackless Python 2.7.1 och bakgrundstradar SVALTER sa fort
  huvudtraden lamnar ett anrop som slapper GIL (M-07). Darfor finns ingen trad.
* app.startSimulation() atervander direkt och later simuleringen ga i realtid;
  skriptets delay(0.05) ger da 20,0 Hz mot vaggklockan (M-08). Det ar pumpen.

Allt som ror VC sker har, pa huvudtraden, inne i tick(). Sockeln lases och
skrivs icke-blockerande. tick() far ALDRIG blockera - gor den det star VC still.

Kalla: docs/spec/31_brygga_protokoll.md
"""
from __future__ import absolute_import, division, print_function

import errno
import json
import os
import select
import socket
import sys
import time
import traceback

import formaga as F
import protokoll as P
import skrivgrind

try:
    from StringIO import StringIO          # py2
except ImportError:                        # py3, for L1-testerna
    from io import StringIO

STANDARDPORT = 8901
MAX_KO = 256
# Hur lange tick() far arbeta innan den lamnar tillbaka till simuleringen.
# Pumpen slar var 50 ms; halften av det ar taket.
TICK_BUDGET_S = 0.025

# Pumpens paus, i SIMULERAD tid - som med startSimulation() ar samma sak som
# vaggklockstid (M-08). Tom pump slar 20 Hz; det racker for att uppdaga en
# begaran men gor tur och retur till en hel period, eftersom klienten skickar
# direkt efter forra svaret och alltsa alltid landar strax EFTER ett slag.
# Darfor slar pumpen tatt en stund efter varje trafik.
PAUS_TOM = 0.05
PAUS_AKTIV = 0.005
AKTIV_FONSTER_S = 2.0


def _s(x):
    """Bytestrang i py2, oforandrad i py3.

    VC:s py2-bindning tar bara bytestrangar; unicode ger SystemError (M-05).
    Galler allt som skrivs TILL VC. Denna fil skriver till VC via exec-koden,
    darfor ligger hjalpen har och exponeras till koden som kors.
    """
    try:
        if isinstance(x, unicode):         # noqa: F821 - finns bara i py2
            return x.encode("utf-8")
    except NameError:
        pass
    return x


class Post(object):
    """En post i godkannandekon."""

    def __init__(self, qid, desc, kod, timeout_ms):
        self.qid = qid
        self.desc = desc
        self.kod = kod
        self.timeout_ms = timeout_ms
        self.requested_at = time.time()
        self.state = "pending"
        self.svar = None

    def som_dict(self, med_kod=False):
        d = {
            "qid": self.qid,
            "desc": self.desc,
            "requested_at": self.requested_at,
            "state": self.state,
        }
        if med_kod:
            d["code"] = self.kod
        return d


class Klient(object):
    def __init__(self, sock, adress):
        self.sock = sock
        self.adress = adress
        self.avramare = P.Avramare()
        self.utbox = b""
        self.doomed = False


class Brygga(object):
    def __init__(self, port=STANDARDPORT, tokenfil=None, loggfil=None,
                 exec_globals=None):
        self.port = int(port)
        self.token = None
        self.tokenfil = tokenfil or os.path.join(
            os.path.expanduser("~"), "vc_assist_token")
        self.loggfil = loggfil or os.path.join(
            os.path.expanduser("~"), "vc_assist_brygga.log")
        self.formagefil = os.path.join(
            os.path.expanduser("~"), "vc_assist_formaga.json")
        self.formagerapport = None
        self.lyssnare = None
        self.klienter = []
        self.ko = []
        self.degraded = False
        self.avslutad = False
        self._n_tick = 0
        self._n_begaran = 0
        self._qid = 0
        self._exec_globals = exec_globals or {}
        self._senaste_trafik = 0.0

    # ---- livscykel -------------------------------------------------------

    def logg(self, msg):
        try:
            f = open(self.loggfil, "a")
            f.write("%.3f %s\n" % (time.time(), msg))
            f.close()
        except Exception:
            pass

    def _skriv_token(self):
        # os.urandom finns aven i VC:s Stackless-bygge; misslyckas den ar det
        # ett fel vi vill se, inte tysta ned till nagot svagare.
        ra = os.urandom(24)
        try:
            import binascii
            self.token = binascii.hexlify(ra).decode("ascii")
        except Exception:
            self.token = "".join("%02x" % (b if isinstance(b, int) else ord(b))
                                 for b in ra)
        f = open(self.tokenfil, "w")
        f.write(self.token)
        f.close()
        try:
            os.chmod(self.tokenfil, 0o600)
        except Exception as e:
            # Under Wine ar chmod inte samma sak som pa Linux. Loggas hellre
            # an antas; loopback-bindningen ar det som barvar skyddet.
            self.logg("chmod pa tokenfilen gick inte: %r" % (e,))

    def skriv_formaga(self, objekt):
        """Provar API-ytorna och skriver rapporten. Kalla: 36_versioner.md."""
        try:
            self.formagerapport = F.skriv(self.formagefil, objekt, extra={
                "protokoll": P.PROTOKOLL_VERSION,
                "port": self.port,
                "operationer": self.operationer(),
            })
            sm = self.formagerapport["summering"]
            self.logg("formaga: %d av %d ytor finns, %d saknas, %d oprovade"
                      % (sm["finns"], sm["provade"], sm["saknas"], sm["oprovade"]))
        except Exception:
            self.logg("kunde inte skriva formagerapporten\n" + traceback.format_exc())
        return self.formagerapport

    def starta(self):
        self._skriv_token()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", self.port))     # ALDRIG 0.0.0.0
        s.listen(8)
        s.setblocking(0)
        self.lyssnare = s
        self.logg("lyssnar pa 127.0.0.1:%d, token i %s" % (self.port, self.tokenfil))
        return self

    def stang(self):
        for k in self.klienter:
            try:
                k.sock.close()
            except Exception:
                pass
        self.klienter = []
        if self.lyssnare is not None:
            try:
                self.lyssnare.close()
            except Exception:
                pass
            self.lyssnare = None
        self.logg("stangd efter %d tick, %d begaran" % (self._n_tick, self._n_begaran))

    # ---- pumpen ----------------------------------------------------------

    def nasta_paus(self):
        """Hur lange pumpen ska sova till nasta varv. Anropas av skriptet."""
        if time.time() - self._senaste_trafik < AKTIV_FONSTER_S:
            return PAUS_AKTIV
        return PAUS_TOM

    def tick(self):
        """Ett varv. Anropas fran skriptets OnRun. Blockerar aldrig."""
        self._n_tick += 1
        if self.lyssnare is None:
            return
        slut = time.time() + TICK_BUDGET_S
        try:
            self._acceptera()
            self._las_och_svara(slut)
            self._skriv_ut()
        except Exception:
            # En pump som dor tar VC:s tillagg med sig. Den far aldrig do.
            self.logg("TICK-FEL\n" + traceback.format_exc())
        self._stada()

    def _acceptera(self):
        while True:
            try:
                sock, adr = self.lyssnare.accept()
            except socket.error as e:
                if e.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                    return
                if e.args[0] == 10035:      # WSAEWOULDBLOCK, Wine/Windows
                    return
                raise
            sock.setblocking(0)
            self._senaste_trafik = time.time()
            self.klienter.append(Klient(sock, adr))
            self.logg("anslutning fran %r" % (adr,))

    def _las_och_svara(self, slut):
        if not self.klienter:
            return
        laser = [k.sock for k in self.klienter]
        try:
            redo, _, trasiga = select.select(laser, [], laser, 0)
        except Exception:
            return
        for k in list(self.klienter):
            if k.sock in trasiga:
                k.doomed = True
                continue
            if k.sock not in redo:
                continue
            try:
                data = k.sock.recv(65536)
            except socket.error:
                k.doomed = True
                continue
            if not data:
                k.doomed = True
                continue
            try:
                kroppar = k.avramare.mata(data)
            except P.Ramfel as e:
                self._sanda(k, P.svar_fel(None, e.kod, str(e)))
                k.doomed = True
                continue
            for kropp in kroppar:
                self._behandla(k, kropp)
                if time.time() > slut:
                    # Resten ligger kvar i avramaren och tas nasta varv.
                    break

    def _behandla(self, k, kropp):
        self._n_begaran += 1
        self._senaste_trafik = time.time()
        t0 = time.time()
        try:
            obj = P.avkoda(kropp)
        except P.Ramfel as e:
            self._sanda(k, P.svar_fel(None, e.kod, str(e)))
            k.doomed = True
            return
        id_ = obj.get("id")
        kod, meddelande = P.granska_begaran(obj, self.token)
        if kod is not None:
            self._sanda(k, P.svar_fel(id_, kod, meddelande))
            if kod in (P.E_AUTH, P.E_VERSION):
                k.doomed = True
            return
        op = obj.get("op")
        args = obj.get("args") or {}
        hanterare = getattr(self, "_op_" + str(op), None)
        if hanterare is None:
            self._sanda(k, P.svar_fel(
                id_, P.E_UNKNOWN_OP,
                "okand operation %r; bryggan kan: %s" % (op, ", ".join(self.operationer()))))
            return
        try:
            svar = hanterare(id_, args)
        except Exception as e:
            svar = P.svar_fel(id_, P.E_EXEC, "%s: %s" % (type(e).__name__, e),
                              traceback.format_exc())
        svar["elapsed_ms"] = int((time.time() - t0) * 1000)
        self._sanda(k, svar)

    def operationer(self):
        return sorted(n[4:] for n in dir(self) if n.startswith("_op_"))

    def _sanda(self, k, svar):
        try:
            k.utbox += P.rama(P.koda(svar))
        except P.ForStor:
            k.utbox += P.rama(P.koda(P.svar_fel(
                svar.get("id"), P.E_TOO_LARGE, "svaret ar storre an %d byte" % P.MAX_KROPP)))

    def _skriv_ut(self):
        for k in self.klienter:
            while k.utbox:
                try:
                    n = k.sock.send(k.utbox)
                except socket.error as e:
                    if e.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK, 10035):
                        break
                    k.doomed = True
                    break
                if n <= 0:
                    break
                k.utbox = k.utbox[n:]

    def _stada(self):
        kvar = []
        for k in self.klienter:
            if k.doomed and not k.utbox:
                try:
                    k.sock.close()
                except Exception:
                    pass
            else:
                kvar.append(k)
        self.klienter = kvar

    # ---- operationer -----------------------------------------------------

    def _op_ping(self, id_, args):
        return P.svar_ok(id_, {
            "protokoll": P.PROTOKOLL_VERSION,
            "python": sys.version.split()[0],
            "python_full": sys.version.replace("\n", " "),
            "vc_exe": sys.executable,
            "tick": self._n_tick,
            "begaran": self._n_begaran,
            "degraded": self.degraded,
            "ko": len(self.ko),
        })

    def _op_exec(self, id_, args):
        kod = args.get("code")
        if not kod:
            return P.svar_fel(id_, P.E_ARGS, "code saknas")
        dom = skrivgrind.granska(kod)
        if dom.skriver:
            # Andra forsvarslinjen. Tjansten routar redan pa verktygets
            # deklarerade effect (45_verktyg.md), men bryggan far inte lita
            # pa sin anropare. Skrivande kod gar via kon, aldrig genom exec.
            return P.svar_fel(
                id_, P.E_NOT_APPROVED,
                "koden skriver och maste ga via exec_queue: " + "; ".join(dom.skal))
        # Ingen degraded-sparr har. exec ar vagen UT ur degraded: bara en
        # lyckad korning kan rensa flaggan, sa en sparr har later sig aldrig
        # oppnas igen. Sparren ligger pa queue_approve, som andrar nagot.
        return self._kor(id_, kod, args.get("timeout_ms", 5000))

    def _kor(self, id_, kod, timeout_ms):
        ut, fel = StringIO(), StringIO()
        gamla_ut, gamla_fel = sys.stdout, sys.stderr
        t0 = time.time()
        undantag = None
        sys.stdout, sys.stderr = ut, fel
        try:
            g = dict(self._exec_globals)
            g["_s"] = _s
            g["__name__"] = "__vc_assist_exec__"
            exec(kod, g)
        except Exception:
            undantag = traceback.format_exc()
        finally:
            sys.stdout, sys.stderr = gamla_ut, gamla_fel
        gick = int((time.time() - t0) * 1000)
        so, se = ut.getvalue(), fel.getvalue()
        if undantag is not None:
            return P.svar_fel(id_, P.E_EXEC, "undantag i koden", undantag,
                              stdout=so, stderr=se, elapsed_ms=gick)
        if timeout_ms and gick > int(timeout_ms):
            # Koden kan inte avbrytas mitt i - den har redan kort klart. Det
            # noteras, och bryggan markerar sig degraded tills nasta lyckade.
            self.degraded = True
            return P.svar_fel(id_, P.E_TIMEOUT,
                              "koden tog %d ms, taket var %s ms" % (gick, timeout_ms),
                              stdout=so, stderr=se, elapsed_ms=gick)
        self.degraded = False
        return P.svar_ok(id_, P.sista_raden_json(so), stdout=so, stderr=se,
                         elapsed_ms=gick)

    def _op_capability(self, id_, args):
        if self.formagerapport is None:
            return P.svar_fel(id_, P.E_ARGS,
                              "ingen formagerapport skriven; bryggan startades utan objekt")
        return P.svar_ok(id_, self.formagerapport)

    def _op_exec_queue(self, id_, args):
        kod = args.get("code")
        if not kod:
            return P.svar_fel(id_, P.E_ARGS, "code saknas")
        if len([p for p in self.ko if p.state == "pending"]) >= MAX_KO:
            return P.svar_fel(id_, P.E_QUEUE_FULL, "kon rymmer %d vantande poster" % MAX_KO)
        self._qid += 1
        post = Post("q%d" % self._qid, args.get("desc", ""), kod,
                    args.get("timeout_ms", 5000))
        self.ko.append(post)
        self.logg("koad %s: %s" % (post.qid, post.desc))
        return P.svar_ok(id_, post.som_dict())

    def _op_queue_list(self, id_, args):
        med_kod = bool(args.get("with_code"))
        return P.svar_ok(id_, {"queue": [p.som_dict(med_kod) for p in self.ko]})

    def _hitta(self, qid):
        for p in self.ko:
            if p.qid == qid:
                return p
        return None

    def _op_queue_approve(self, id_, args):
        qid = args.get("qid")
        post = self._hitta(qid)
        if post is None:
            return P.svar_fel(id_, P.E_ARGS, "ingen post med qid %r" % (qid,))
        if post.state != "pending":
            return P.svar_fel(id_, P.E_NOT_APPROVED,
                              "post %s ar %s, bara pending kan godkannas" % (qid, post.state))
        if self.degraded:
            return P.svar_fel(id_, P.E_BUSY,
                              "bryggan ar degraded efter en timeout; kor en lasande exec "
                              "forst sa lamnar den det laget")
        post.state = "approved"
        svar = self._kor(id_, post.kod, post.timeout_ms)
        post.state = "done" if svar.get("ok") else "failed"
        post.svar = svar
        self.logg("kord %s -> %s" % (post.qid, post.state))
        svar["result"] = {"qid": post.qid, "state": post.state, "result": svar.get("result")}
        return svar

    def _op_queue_reject(self, id_, args):
        qid = args.get("qid")
        post = self._hitta(qid)
        if post is None:
            return P.svar_fel(id_, P.E_ARGS, "ingen post med qid %r" % (qid,))
        if post.state != "pending":
            return P.svar_fel(id_, P.E_NOT_APPROVED,
                              "post %s ar %s, bara pending kan avvisas" % (qid, post.state))
        post.state = "rejected"
        return P.svar_ok(id_, post.som_dict())

    def _op_cancel(self, id_, args):
        # Koden kors synkront pa huvudtraden; det finns inget att avbryta mitt i.
        # Det ar en foljd av att VC:s Python ar kooperativ (M-07), inte en lucka.
        return P.svar_ok(id_, {"cancelled": False,
                               "why": "exec kors synkront pa VC:s trad och kan inte avbrytas"})

    def _op_shutdown(self, id_, args):
        self.avslutad = True
        return P.svar_ok(id_, {"bye": True})


# ---- en enda brygga per VC-process ---------------------------------------
#
# Bryggan far INTE skapas om vid varje simuleringsstart: sockeln ar redan
# bunden och OnStart/OnReset fyrar varje gang operatoren trycker play. Den ska
# dessutom overleva att en layout stangs och en ny oppnas
# (31_brygga_protokoll.md, "Beteende nar VC stangs").

INSTANS = None


def hamta_brygga(exec_globals=None, port=STANDARDPORT, **kw):
    """Returnerar processens brygga och startar den forsta gangen."""
    global INSTANS
    if INSTANS is None or INSTANS.lyssnare is None:
        INSTANS = Brygga(port=port, exec_globals=exec_globals or {}, **kw)
        INSTANS.starta()
    elif exec_globals:
        # Ny simuleringsomgang: skriptets scope ar ett annat objekt an forra
        # gangen, sa exec-koden ska se det nya.
        INSTANS._exec_globals = exec_globals
    return INSTANS
