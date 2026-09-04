# -*- coding: utf-8 -*-
"""L3: fas 1:s acceptans mot en KORANDE VC. Kors fran Linux, py3.

Utfor de elva stegen i tests/protocol/fas1_bryggan.md och de sex trasiga
fallen, och skriver ned de matta storheterna. Skriver ingen dom sjalv utover
det den faktiskt provat.

    python3 tests/protocol/kor_fas1.py [--token FIL] [--port 8901]
"""
import argparse
import json
import os
import socket
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import protokoll as P                                  # noqa: E402
from vc_assist_svc.klient import Klient, BryggFel      # noqa: E402
from vc_assist_svc.tokenplats import tokenfil        # noqa: E402

STEG = []


def steg(nr, vad):
    def dek(fn):
        STEG.append((nr, vad, fn))
        return fn
    return dek


class Kor(object):
    def __init__(self, port, tokenfil):
        self.port = port
        self.tokenfil = tokenfil
        self.k = Klient(port=port, tokenfil=tokenfil)
        self.k.anslut()
        self.matt = {}
        self.qid = None
        # Kor-unikt namn: acceptansen far inte falla pa sin egen kvarleva fran
        # forra korningen, och den far inte heller lita pa att scenen ar tom.
        self.namn = "AcceptansFas1_%d" % int(time.time())

    def ny_ra(self):
        return socket.create_connection(("127.0.0.1", self.port), timeout=5)

    def rakna(self, namn):
        """Hur manga komponenter i scenen som heter sa har."""
        kod = ("import json\n"
               "n = len([c for c in getApplication().Components if c.Name == %r])\n"
               "print(json.dumps({'n': n}))\n" % str(namn))
        return self.k.kor(kod)["result"]["n"]


@steg(3, "formagerapporten finns och listar ytorna")
def s3(r):
    rap = r.k.anrop("capability")["result"]
    s = rap["summering"]
    r.matt["formaga_finns"] = s["finns"]
    r.matt["formaga_provade"] = s["provade"]
    r.matt["formaga_saknas"] = rap["saknade_ytor"]
    assert s["provade"] > 0
    return "%d av %d ytor finns, saknas: %s" % (
        s["finns"], s["provade"], ", ".join(rap["saknade_ytor"]) or "inga")


@steg(4, "ping svarar")
def s4(r):
    t0 = time.time()
    p = r.k.ping()
    rtt = (time.time() - t0) * 1000
    r.matt["ping_rtt_ms"] = round(rtt, 2)
    assert p["protokoll"] == P.PROTOKOLL_VERSION
    return "%.2f ms, python %s, tick %d" % (rtt, p["python"], p["tick"])


@steg(5, "exec med lasande kod ger JSON ur sista raden")
def s5(r):
    kod = ("import json\n"
           "app = getApplication()\n"
           "namn = [c.Name for c in app.Components]\n"
           "print('brus fore')\n"
           "print(json.dumps({'antal': len(namn), 'namn': namn[:5]}))\n")
    sv = r.k.kor(kod)
    assert sv["ok"] and isinstance(sv["result"], dict), sv
    assert "brus fore" in sv["stdout"]
    r.matt["komponenter_i_scenen"] = sv["result"]["antal"]
    return "scenen har %d komponenter: %s" % (sv["result"]["antal"], sv["result"]["namn"])


@steg(6, "kon: koa, lista, godkann, verifiera att koden kort")
def s6(r):
    kod = ("import json\n"
           "app = getApplication()\n"
           "c = app.createComponent()\n"
           "c.Name = '%s'\n"
           "print(json.dumps({'skapade': c.Name}))\n" % r.namn)
    post = r.k.koa(kod, desc="skapa en komponent")
    r.qid = post["qid"]
    assert post["state"] == "pending"

    # Kon lever i VC-processen och kan innehalla poster fran tidigare
    # korningar. Steget provar SIN post, inte att kon ar tom.
    mina = [p for p in r.k.ko() if p["qid"] == r.qid]
    assert len(mina) == 1, "den koade posten syns inte i queue_list"
    assert mina[0]["state"] == "pending"
    assert mina[0]["desc"] == "skapa en komponent"

    fanns_innan = r.rakna(r.namn)
    assert fanns_innan == 0, "koad kod hade redan kort - det ar hela poangen som brister"

    sv = r.k.godkann(r.qid)
    assert sv["ok"], sv
    efterat = r.rakna(r.namn)
    assert efterat == 1, "godkannandet korde inte koden"
    assert [p for p in r.k.ko() if p["qid"] == r.qid][0]["state"] == "done"
    return "post %s: pending -> done, komponenten finns i scenen efterat" % r.qid


@steg(7, "kod som kastar ger E_EXEC med traceback, bryggan lever")
def s7(r):
    try:
        r.k.kor("1/0")
        raise AssertionError("inget fel kastades")
    except BryggFel as e:
        assert e.kod == P.E_EXEC, e.kod
        assert "ZeroDivisionError" in (e.traceback or "")
    assert r.k.ping()["protokoll"] == 1
    return "E_EXEC med traceback, ping svarar efterat"


@steg(8, "timeout ger E_TIMEOUT och degraded, lasande exec ar vagen ut")
def s8(r):
    try:
        r.k.kor("import time\ntime.sleep(0.3)", timeout_ms=100)
        raise AssertionError("ingen timeout")
    except BryggFel as e:
        assert e.kod == P.E_TIMEOUT, e.kod
    assert r.k.ping()["degraded"] is True
    r.k.kor("print(1)")
    assert r.k.ping()["degraded"] is False
    return "E_TIMEOUT, degraded satt och sedan rensat av en lasande korning"


@steg(9, "trasig ram ger E_PARSE, servern lever")
def s9(r):
    s = r.ny_ra()
    s.sendall(b"XXXXXXXX\n{}")
    a = P.Avramare()
    sv = P.avkoda(a.mata(s.recv(65536))[0])
    s.close()
    assert sv["error"]["code"] == P.E_PARSE, sv
    assert r.k.ping()["protokoll"] == 1
    return "E_PARSE, anslutningen stangd, bryggan svarar pa nasta"


@steg(10, "fel token ger E_AUTH")
def s10(r):
    k = Klient(port=r.port, token="fel losen")
    try:
        k.anrop("ping")
        raise AssertionError("fel token slapptes igenom")
    except BryggFel as e:
        assert e.kod == P.E_AUTH, e.kod
    finally:
        k.stang()
    return "E_AUTH och anslutningen stangs"


@steg(11, "kropp over 1 MB ger E_TOO_LARGE")
def s11(r):
    s = r.ny_ra()
    s.sendall(b"%08x\n" % (P.MAX_KROPP + 1))
    a = P.Avramare()
    sv = P.avkoda(a.mata(s.recv(65536))[0])
    s.close()
    assert sv["error"]["code"] == P.E_TOO_LARGE, sv
    return "E_TOO_LARGE"


@steg(12, "exec av skrivande kod avvisas och hanvisar till kon")
def s12(r):
    try:
        r.k.kor("getApplication().createComponent()")
        raise AssertionError("skrivande kod slapptes genom exec")
    except BryggFel as e:
        assert e.kod == P.E_NOT_APPROVED, e.kod
        assert "exec_queue" in e.meddelande
    return "E_NOT_APPROVED, hanvisar till kon"


@steg(13, "provtagningstakten matt, bada regimerna var for sig")
def s13(r):
    # Pumpen har tva lagen. Ett medelvarde over ett blandat fonster ar ingen
    # takt, det ar tva takter i samma tal - darfor mats de var for sig.
    a = r.k.ping()
    t0 = time.time()
    while time.time() - t0 < 2.0:
        r.k.ping()
    b = r.k.ping()
    aktiv = (b["tick"] - a["tick"]) / (time.time() - t0)
    r.matt["pump_hz_aktiv"] = round(aktiv, 1)

    # Tyst fonster. De forsta AKTIV_FONSTER_S sekunderna lever den aktiva
    # takten kvar, och dras darfor bort som en KAND korrigering.
    c = r.k.ping()
    t1 = time.time()
    time.sleep(20.0)
    d = r.k.ping()
    gick = time.time() - t1
    aktiv_svans = 2.0
    tom = (d["tick"] - c["tick"] - aktiv * aktiv_svans) / (gick - aktiv_svans)
    r.matt["pump_hz_tom"] = round(tom, 1)
    r.matt["pump_tom_matt_over_s"] = round(gick - aktiv_svans, 1)
    assert tom > 0 and aktiv > tom
    return "aktiv %.1f Hz, tom %.1f Hz (efter avdrag for %.0f s aktiv svans)" % (
        aktiv, tom, aktiv_svans)


@steg(14, "ping under last: bryggan svarar medan pumpen gar")
def s14(r):
    tider = []
    for _ in range(20):
        t0 = time.time()
        r.k.ping()
        tider.append((time.time() - t0) * 1000)
    tider.sort()
    r.matt["ping_median_ms"] = round(tider[len(tider) // 2], 2)
    r.matt["ping_max_ms"] = round(tider[-1], 2)
    return "median %.2f ms, varsta %.2f ms over 20 anrop" % (tider[len(tider) // 2], tider[-1])


@steg(15, "stadning: komponenten tas bort via kon")
def s15(r):
    assert r.rakna(r.namn) == 1, "ingenting att stada - steg 6 lamnade inget efter sig"
    post = r.k.koa("app = getApplication()\n"
                   "for c in list(app.Components):\n"
                   "    if c.Name == %r:\n"
                   "        app.deleteComponent(c)\n" % str(r.namn),
                   desc="ta bort acceptanskomponenten")
    r.k.godkann(post["qid"])
    assert r.rakna(r.namn) == 0, "komponenten finns kvar efter borttagning"
    return "%s borttagen, scenen ar som fore korningen" % r.namn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    # Ingen standardsokvag. Den gamla ("~/.wine-vc-test/drive_c/users/anton/
    # vc_assist_token") bar tre antaganden som alla ar falska pa Windows: att
    # det finns ett wine-prefix, vad det heter, och vad anvandaren heter.
    ap.add_argument("--token", default=None,
                    help="tokenfilen. Utan flaggan soks den upp; se "
                         "vc_assist_svc.tokenplats")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    r = Kor(a.port, a.token or tokenfil())
    resultat = []
    fel = 0
    for nr, vad, fn in STEG:
        try:
            notis = fn(r)
            resultat.append((nr, vad, True, notis))
            print("  OK   %2d  %-58s %s" % (nr, vad, notis))
        except Exception as e:
            fel += 1
            resultat.append((nr, vad, False, "%s: %s" % (type(e).__name__, e)))
            print("  FEL  %2d  %-58s %s: %s" % (nr, vad, type(e).__name__, e))

    print("\n  matt:")
    for k in sorted(r.matt):
        print("    %-24s %s" % (k, r.matt[k]))
    print("\n  %d av %d steg gick igenom" % (len(STEG) - fel, len(STEG)))

    if a.json:
        with open(a.json, "w") as f:
            json.dump({"steg": [{"nr": n, "vad": v, "ok": o, "notis": t}
                                for n, v, o, t in resultat],
                       "matt": r.matt}, f, indent=2)
    r.k.stang()
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
