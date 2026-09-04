# -*- coding: utf-8 -*-
"""Ogats provtagande halva. Kors INNE i VC, py2.7.

Provtagaren rors av pumpen (M-08) och laser scenen. Domen fals inte har - den
fals i oga_analys.py, utanfor VC, pa den tidsserie som skrivs har. Uppdelningen
ar avsiktlig: domaren gar da att prova utan VC.

Kalla: docs/spec/40_ogat.md, docs/spec/41_ogat_kontrakt.md
Matt: M-11 (kvaternionens ordning och varldsmatrisens eftersläpning)
"""
from __future__ import absolute_import, division, print_function

import json
import os
import time

# Hur ofta serien skrivs till disk. Kontraktet kraver inkrementell skrivning
# sa en avbruten korning anda gar att lasa.
SKRIV_VAR_N_RAD = 100       # PRELIMINAR. Satts av matning M-10.


def kvat_fran_vc(vcvektor):
    """VC ger kvaternionen SKALAR-FORST. MATT i M-11.

    q.X foljer cos(theta/2) och ar alltsa skalaren; vektordelen ligger i
    (Y, Z, W). Las man rakt av blir en orord detalj en 180-graders vridning,
    och CARRY SLIPPING faller pa varje korning med en orsak som ser ut att
    sitta i scenen.
    """
    return [vcvektor.Y, vcvektor.Z, vcvektor.W, vcvektor.X]


class Scen(object):
    """Vad provtagaren behover av en scen. Finns for att kunna bytas ut i test."""

    def uppdatera(self):
        pass

    def pose(self, spec):
        raise NotImplementedError

    def signal(self, spec):
        raise NotImplementedError

    def mindist(self, spec):
        return None

    def stat(self, spec):
        return None

    def traff(self):
        return None


class VcScen(Scen):
    """Den riktiga scenen. Namnger objekt som 'Komponent' eller 'Komponent/Nod'."""

    def __init__(self, app, sim, uppdatera_fore_last=True):
        self.app = app
        self.sim = sim
        # M-11: varldsmatrisen slapar ett scenuppdateringssteg, och varken
        # render() eller flush() hamtar hem den. Bara sim.update() gor det.
        self.uppdatera_fore_last = uppdatera_fore_last
        self._cache = {}
        self.saknade = []

    def uppdatera(self):
        if self.uppdatera_fore_last:
            self.sim.update()

    def _nod(self, spec):
        if spec in self._cache:
            return self._cache[spec]
        delar = spec.split("/", 1)
        comp = self.app.findComponent(str(delar[0]))
        if comp is None:
            self._saknas(spec, "ingen komponent som heter %r" % delar[0])
            return None
        objekt = comp
        if len(delar) == 2:
            objekt = comp.findNode(str(delar[1]))
            if objekt is None:
                self._saknas(spec, "komponenten %r har ingen nod %r"
                             % (delar[0], delar[1]))
                return None
        self._cache[spec] = objekt
        return objekt

    def _saknas(self, spec, varfor):
        post = {"spec": spec, "varfor": varfor}
        if post not in self.saknade:
            self.saknade.append(post)

    def pose(self, spec):
        nod = self._nod(spec)
        if nod is None:
            return None
        try:
            m = nod.WorldPositionMatrix
            p = m.P
            return {"p": [p.X, p.Y, p.Z], "q": kvat_fran_vc(m.getQuaternion())}
        except Exception as e:
            self._saknas(spec, "kunde inte lasa posen: %s" % type(e).__name__)
            return None

    def signal(self, spec):
        delar = spec.split("/", 1)
        if len(delar) != 2:
            self._saknas(spec, "en signal namnges 'Komponent/Signal'")
            return None
        comp = self.app.findComponent(str(delar[0]))
        if comp is None:
            self._saknas(spec, "ingen komponent som heter %r" % delar[0])
            return None
        try:
            beh = comp.findBehaviour(str(delar[1]))
            if beh is None:
                self._saknas(spec, "ingen signal %r" % delar[1])
                return None
            return beh.Value
        except Exception as e:
            self._saknas(spec, "kunde inte lasa signalen: %s" % type(e).__name__)
            return None


class Provtagare(object):
    def __init__(self, scen, plan, sokvag=None):
        self.scen = scen
        self.plan = dict(plan or {})
        self.rate_hz = float(self.plan.get("rate_hz", 20.0))
        self.intervall = 1.0 / self.rate_hz if self.rate_hz > 0 else 0.05
        self.sokvag = sokvag or os.path.join(
            os.path.expanduser("~"), "vc_assist_eyes.json")
        self.rader = []
        self.startad = None
        self.t0 = None
        self.nasta_t = None
        self.aktiv = False
        self.n_skrivna = 0

    # -- livscykel --

    def starta(self, t):
        self.rader = []
        self.startad = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.t0 = float(t)
        self.nasta_t = float(t)
        self.aktiv = True
        return self

    def stoppa(self):
        self.aktiv = False
        self.skriv()
        return self.sokvag

    # -- provtagning --

    def kanske_prov(self, t):
        """Anropas varje pumpvarv. Provtar nar simuleringstiden natt intervallet."""
        if not self.aktiv:
            return False
        t = float(t)
        if t + 1e-9 < self.nasta_t:
            return False
        self.prov(t)
        # Nasta punkt ska ligga PA rutnatet och samtidigt minst ett helt
        # intervall bort. Bara det forsta ger drift efter ett uppehall; bara
        # det andra ger en for kort lucka nar man snapper tillbaka till
        # rutnatet - matt till 0,01 s i ett prov med ojamn pump.
        mal = t + self.intervall
        steg = int((mal - self.nasta_t) / self.intervall)
        if self.nasta_t + steg * self.intervall < mal - 1e-9:
            steg += 1
        self.nasta_t += max(1, steg) * self.intervall
        if len(self.rader) % SKRIV_VAR_N_RAD == 0:
            self.skriv(delvis=True)
        return True

    def prov(self, t):
        self.scen.uppdatera()
        rad = {"t": round(float(t) - self.t0, 4)}
        for grupp, nyckel in (("parts", "parts"), ("tools", "tools")):
            ut = {}
            for spec in (self.plan.get(grupp) or []):
                pose = self.scen.pose(spec)
                if pose is not None:
                    ut[spec] = pose
            if ut:
                rad[nyckel] = ut
        sig = {}
        for spec in (self.plan.get("signals") or []):
            v = self.scen.signal(spec)
            if v is not None:
                sig[spec] = bool(v)
        if sig:
            rad["sig"] = sig
        for namn, hamta in (("mind", self.scen.mindist), ("stat", self.scen.stat)):
            ut = {}
            for spec in (self.plan.get(namn) or []):
                v = hamta(spec)
                if v is not None:
                    ut[spec] = v
            if ut:
                rad[namn] = ut
        traff = self.scen.traff()
        if traff:
            rad["hit"] = list(traff)
        self.rader.append(rad)
        return rad

    # -- utdata --

    def data(self, delvis=False):
        dur = (self.rader[-1]["t"] if self.rader else 0.0)
        takt = (len(self.rader) / dur) if dur > 0 else 0.0
        d = {
            "v": 1,
            "template": self.plan.get("template", "okand"),
            "run": {"started": self.startad or "okand", "dur_s": round(dur, 3),
                    "samples": len(self.rader), "rate_hz": round(takt, 3)},
            "tracked": {"parts": list(self.plan.get("parts") or []),
                        "tools": list(self.plan.get("tools") or []),
                        "signals": list(self.plan.get("signals") or []),
                        "pairs": list(self.plan.get("mind") or [])},
            "rows": self.rader,
        }
        saknade = getattr(self.scen, "saknade", None)
        if saknade:
            # Det som INTE gick att lasa ska synas i underlaget. En tyst lucka
            # blir annars en dom pa ofullstandig grund.
            d["saknade"] = list(saknade)
        if delvis:
            d["partial"] = True
        return d

    def skriv(self, delvis=False):
        f = open(self.sokvag, "w")
        try:
            json.dump(self.data(delvis=delvis), f)
        finally:
            f.close()
        self.n_skrivna = len(self.rader)
        return self.sokvag
