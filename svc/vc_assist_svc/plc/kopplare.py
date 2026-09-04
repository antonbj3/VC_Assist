# -*- coding: utf-8 -*-
"""Kopplaren: PLC-variabler mot scenens signaler.

MATT i M-38: VC:s Python-API har NOLL yta mot uppkoppling. OPC UA finns bara i
.NET, och VC:s Python nar inte .NET (M-07). VC:s egen OPC UA-klient gar alltsa
inte att konfigurera programmatiskt.

Kedjan sluts darfor genom tjansten i stallet:

    genererad ST -> OpenPLC -> OPC UA -> KOPPLAREN -> bryggan -> scenens signaler

Kopplaren ager en enda sak: att kopiera varden at ratt hall, en gang per varv,
och att MATA hur lang tid varje led tog. Den domer ingenting - domen ar ogats.

Riktningen kommer ur signalkartan, inte ur en gissning:

    TILL_PLC   scenens signal  ->  PLC:ns ingang     (givare)
    FRAN_PLC   PLC:ns utgang   ->  scenens signal    (don)

Kalla: docs/spec/60_plc.md, docs/matningar/M-38
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .signalkarta import FRAN_PLC, TILL_PLC, Signalkarta

# Hur lange kopplaren vantar pa ett OPC UA-svar innan varvet raknas som fallet.
# Satt av M-39: tio ganger det langsta uppmatta varvet, sa en tidsgrans aldrig
# loser ut pa normal drift.
OPCUA_TIDSGRANS_S = 5.0     # Satt av M-39.

# Hur manga varv i rad som far falla innan kopplaren ger upp. En kopplare som
# maler vidare mot en dod PLC ser ut att arbeta.
# Satt av M-39: tva varv racker inte for att skilja en tillfallig hicka fran en
# dod PLC; tre gor det, och kostar hogst tre varv innan larmet.
MAX_RAKA_FEL = 3            # Satt av M-39.


class Kopplarfel(Exception):
    """Kopplaren kan inte fullfolja ett varv."""


class Varv:
    """Vad ett varv gjorde och hur lang tid varje led tog."""

    __slots__ = ("nr", "t0", "las_vc_ms", "skriv_plc_ms", "las_plc_ms",
                 "skriv_vc_ms", "totalt_ms", "till_plc", "fran_plc", "fel",
                 "t_fran_plc", "oga", "oga_fel")

    def __init__(self, nr):
        self.nr = nr
        self.t0 = time.time()
        # Vaggklockan da OPC UA-lasningen PABORJADES. Vardet ar minst sa
        # gammalt; stamplar man i stallet nar lasningen atervande blir varje
        # varde yngre an det ar, och det ar fel hall att gissa at.
        self.t_fran_plc = None
        self.oga = None          # ogats svar pa inskottet
        self.oga_fel = None      # inskottet gick inte fram, och det tigs inte
        self.las_vc_ms = None
        self.skriv_plc_ms = None
        self.las_plc_ms = None
        self.skriv_vc_ms = None
        self.totalt_ms = None
        self.till_plc = {}
        self.fran_plc = {}
        self.fel = None

    def till_json(self):
        return {
            "nr": self.nr,
            "las_vc_ms": self.las_vc_ms, "skriv_plc_ms": self.skriv_plc_ms,
            "las_plc_ms": self.las_plc_ms, "skriv_vc_ms": self.skriv_vc_ms,
            "totalt_ms": self.totalt_ms,
            "till_plc": dict(self.till_plc), "fran_plc": dict(self.fran_plc),
            "fel": self.fel, "oga": self.oga, "oga_fel": self.oga_fel,
        }


class Kopplare:
    """Kopplar en signalkarta mellan en OPC UA-server och en VC-brygga.

    `ua` ska tala tva metoder, bada synkrona:
        las(taggar)  -> {tagg: varde}
        skriv(varden)                     # {tagg: varde}
    `brygga` ar en vc_assist_svc.klient.Klient.

    Gransnittet ar avsiktligt litet: da gar bada sidor att byta ut mot
    attrapper i ett prov utan att kopplaren vet om det.
    """

    def __init__(self, karta, ua, brygga, max_raka_fel=MAX_RAKA_FEL, oga=None):
        if not isinstance(karta, Signalkarta):
            raise Kopplarfel("kopplaren tar en Signalkarta, inte %s"
                             % type(karta).__name__)
        self.karta = karta
        self.ua = ua
        self.brygga = brygga
        self.max_raka_fel = int(max_raka_fel)
        # Ogonkopplingen (plc/ogonkoppling.py) eller None. Kopplaren vet inget
        # om simuleringstid eller brygga har - den lamnar over VARDET och den
        # vaggklocka det lastes vid, och ogonkopplingen gor om det till ogats
        # axel. Det ar darfor bada gar att prova var for sig.
        self.oga = oga
        self.n_ogafel = 0
        self.varv = []
        self._raka_fel = 0
        # Riktningen kommer ur kartan. En signal utan komponent eller
        # scensignal gar inte att koppla, och det ska sagas - inte tigas ihjal.
        self.till_plc = []
        self.fran_plc = []
        # Ingen gren for trasiga signaler. Signalkarta avvisar redan i
        # Signal.__post_init__ en signal utan komponentnamn, utan scensignal
        # eller med okand riktning, sa varje sadan gren har vore OATKOMLIG kod.
        # Garantin bor ett lager upp och provas dar.
        for s in karta.signaler:
            if s.riktning == TILL_PLC:
                self.till_plc.append(s)
            else:
                self.fran_plc.append(s)

    # ---- scenens sida ---------------------------------------------------

    @staticmethod
    def _las_kod(signaler):
        rader = ["import json", "app = getApplication()", "ut = {}"]
        for s in signaler:
            rader += [
                "c = app.findComponent(%r)" % str(s.komponent),
                "b = c.findBehaviour(%r) if c is not None else None" % str(s.scensignal),
                "ut[%r] = None if b is None else b.Value" % str(s.tagg),
            ]
        rader.append("print(json.dumps(ut))")
        return "\n".join(rader)

    @staticmethod
    def _skriv_kod(signaler, varden):
        rader = ["import json", "app = getApplication()", "satt = {}"]
        for s in signaler:
            v = varden.get(s.tagg)
            if v is None:
                continue
            rader += [
                "c = app.findComponent(%r)" % str(s.komponent),
                "b = c.findBehaviour(%r) if c is not None else None" % str(s.scensignal),
                "if b is not None:",
                "    b.Value = %r" % (v,),
                "    satt[%r] = b.Value" % str(s.tagg),
            ]
        rader.append("print(json.dumps(satt))")
        return "\n".join(rader)

    def las_scenen(self):
        if not self.till_plc:
            return {}
        svar = self.brygga.kor(self._las_kod(self.till_plc))
        return svar.get("result") or {}

    def skriv_scenen(self, varden):
        skrivbara = [s for s in self.fran_plc if varden.get(s.tagg) is not None]
        if not skrivbara:
            return {}
        # En signalskrivning ANDRAR scenen och gar darfor genom kon (I12).
        kod = self._skriv_kod(skrivbara, varden)
        post = self.brygga.koa(kod, desc="kopplaren skriver %d signaler" % len(skrivbara))
        ut = self.brygga.godkann_och_vanta(post["qid"], timeout=OPCUA_TIDSGRANS_S * 6)
        if ut["state"] != "done":
            raise Kopplarfel("scenskrivningen slutade som %r" % ut["state"])
        svar = (ut.get("svar") or {}).get("result") or {}
        return svar.get("result", svar) if isinstance(svar, dict) else {}

    # ---- ett varv -------------------------------------------------------

    def kor_varv(self, nr=None):
        v = Varv(len(self.varv) if nr is None else nr)
        try:
            t = time.time()
            fran_scenen = self.las_scenen()
            v.las_vc_ms = (time.time() - t) * 1000.0

            t = time.time()
            if fran_scenen:
                self.ua.skriv(fran_scenen)
            v.skriv_plc_ms = (time.time() - t) * 1000.0
            v.till_plc = fran_scenen

            t = time.time()
            v.t_fran_plc = t
            fran_plc = self.ua.las([s.tagg for s in self.fran_plc])
            v.las_plc_ms = (time.time() - t) * 1000.0
            v.fran_plc = fran_plc

            t = time.time()
            self.skriv_scenen(fran_plc)
            v.skriv_vc_ms = (time.time() - t) * 1000.0
            self._raka_fel = 0
        except Exception as e:
            v.fel = "%s: %s" % (type(e).__name__, str(e)[:120])
            self._raka_fel += 1
        v.totalt_ms = (time.time() - v.t0) * 1000.0
        self._till_ogat(v)
        self.varv.append(v)
        if self._raka_fel >= self.max_raka_fel:
            skal = ("kopplaren gav upp efter %d raka fel; sista: %s"
                    % (self._raka_fel, v.fel))
            # Sista ordet till ogat INNAN slingan faller. Efter det kommer
            # inga fler inskott alls, och en serie som inte far veta det
            # skulle fortsatta visa varden fran ett band som inte finns.
            self._ogonanrop(v, "bryt", skal)
            raise Kopplarfel(skal)
        return v

    # ---- ut till ogats tidsserie ----------------------------------------

    def _till_ogat(self, v):
        """Varje varv sager sitt till ogat - aven ett fallet.

        Ett fallet varv har INGA farska varden. Att da tiga ar inte neutralt:
        tystnad gar inte att skilja fran "inget nytt har hant", och serien
        skulle bara de gamla talen vidare som om de vore samtidiga.
        """
        if self.oga is None:
            return
        if v.fel is not None:
            self._ogonanrop(v, "bryt",
                            "kopplarvarv %d foll: %s" % (v.nr, v.fel))
        elif v.fran_plc:
            self._ogonanrop(v, "skjut_in", v.fran_plc, v.t_fran_plc)

    def _ogonanrop(self, v, metod, *a):
        if self.oga is None:
            return
        try:
            v.oga = getattr(self.oga, metod)(*a)
        except Exception as e:
            # Ogat far aldrig falla kopplarens varv - men felet gar inte att
            # tiga ihjal heller. Kommer inskotten inte fram lamnas serien at
            # sitt eget tystnadstak, och DET ska synas har.
            v.oga_fel = "%s: %s" % (type(e).__name__, str(e)[:120])
            self.n_ogafel += 1

    # ---- sammanfattning -------------------------------------------------

    def sammanfattning(self):
        lyckade = [v for v in self.varv if v.fel is None]
        tider = sorted(v.totalt_ms for v in lyckade)
        def p(andel):
            if not tider:
                return None
            i = min(len(tider) - 1, int(round(andel * (len(tider) - 1))))
            return round(tider[i], 2)
        return {
            "varv": len(self.varv),
            "lyckade": len(lyckade),
            "fallna": len(self.varv) - len(lyckade),
            "median_ms": p(0.5), "p95_ms": p(0.95),
            "min_ms": round(tider[0], 2) if tider else None,
            "max_ms": round(tider[-1], 2) if tider else None,
            "till_plc": [s.tagg for s in self.till_plc],
            "fran_plc": [s.tagg for s in self.fran_plc],
            "ogafel": self.n_ogafel,
            "oga": None if self.oga is None else self.oga.sammanfattning(),
        }
