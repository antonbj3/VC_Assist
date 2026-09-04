# -*- coding: utf-8 -*-
"""Ögonkopplingen: kopplarens PLC-värden in på ögats tidsaxel.

Kopplaren (`kopplare.py`) bor i tjänsten och räknar i VÄGGKLOCKA. Ögat
(`oga_provtagning.py`) bor inne i VC och räknar i SIMULERINGSTID. De två
tickar i olika takt och på olika sidor av processgränsen, och en tidsstämpel
från den ena betyder inte samma sak som en från den andra.

Den gemensamma klockan är **simuleringstiden**. Skälet är att det är den ögats
serie redan är stämplad i (`rad["t"] = simtid - t0`), och att fysiken i scenen
rör sig i den och inte i väggklockan. Ett fasförhållande mellan en PLC-flank
och en rörelse är bara ett mått om båda ligger på samma axel.

Bron mellan klockorna är därför en **varaktighet, aldrig en tidpunkt**:

* En varaktighet betyder samma sak i båda processerna. En tidpunkt gör det
  bara om klockorna delar epok — och epoken överlever inte ett `sim.reset()`,
  som nollar simuleringstiden mitt i en körning (pump.py startar om
  simuleringen efter varje scenändring).
* Kopplaren skickar alltså värdets ÅLDER i sin egen klocka. Pumpen räknar om
  den till simuleringstid med sin egen MÄTTA takt (`Brygga.takt()`), som är
  1,000 med `app.startSimulation()` (M-08) men 2000 med `sim.run()`.

Vad som INTE kan tigas ihjäl:

* Kopplaren ger upp efter tre raka fel (M-39). Då säger den ifrån med
  `bryt()`, och ögats serie får ett HÅL med skäl i stället för gamla tal.
* Om kopplaren i stället dör tvärt hinner den inte säga någonting. Ögat har
  därför ett eget tystnadstak (`PLC_TYSTNAD_S`) som släpper värdena av sig
  själv. Tystnad går inte att skilja från "inget nytt har hänt", så båda
  mekanismerna behövs — en för varje sida som kan falla.

Källa: docs/matningar/M-42, docs/spec/42_ogat_utbyggt.md §6
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

# Hur många av de senaste turerna och returerna kompensationen tas ur. MÄTT i
# M-42: utan kompensation låg hopfogningsfelet på +5,09 ms median — åt det
# FARLIGA hållet, ögat trodde värdet var färskare än det var. Enkelriktade
# fördröjningar går inte att mäta utan en delad klocka, men de är per
# definition högst en hel tur och retur, och den mäts. Fönstret ska vara
# långt nog att rymma en hicka och kort nog att inte bära med sig en gammal.
KOMPENSATIONSFONSTER = 8    # Satt av M-42.


class Ogonkoppling:
    """Skickar kopplarens ögonblicksbilder till ögat genom bryggan.

    `brygga` är en `vc_assist_svc.klient.Klient` (eller vad som helst som har
    `plc_in`). Ytan är avsiktligt liten: två metoder ut, och varje svar
    räknas — ett värde som inte lagrades får inte se ut som ett som lagrades.
    """

    def __init__(self, brygga, klocka=time.time):
        self.brygga = brygga
        self.klocka = klocka
        self.n_skjutna = 0
        self.n_lagrade = 0
        self.n_brutna = 0
        self.n_utan_axel = 0        # lagrat, men utan giltig simuleringstid
        self.n_oga_stangt = 0       # ögat provtog inte; värdet gick ingenstans
        self.rtt_s: List[float] = []
        self.takt_sist: Optional[float] = None
        self.simtid_sist: Optional[float] = None
        self.klockbakat: int = 0
        self.sista_svar: Optional[Dict] = None

    # ---- ut till ögat ---------------------------------------------------

    def _anrop(self, **args):
        t0 = self.klocka()
        svar = self.brygga.plc_in(**args)
        self.rtt_s.append(self.klocka() - t0)
        self.sista_svar = svar
        self.takt_sist = svar.get("takt")
        self.simtid_sist = svar.get("simtid")
        self.klockbakat = svar.get("klockbakat") or 0
        if not svar.get("oga"):
            self.n_oga_stangt += 1
        elif svar.get("lagrat"):
            self.n_lagrade += 1
            if "pa" in svar and svar.get("pa") is None:
                # Lagrat utan tidsaxel. Ögat räknar det som gammalt, och det
                # ska synas HÄR också - annars ser slingan matad ut.
                self.n_utan_axel += 1
        return svar

    def rtt_tak(self):
        """Övre gräns för hur länge ett inskott kan vara på väg, MÄTT.

        Vägen ut går inte att tidta utan en klocka båda sidor delar. Men den
        är aldrig längre än en hel tur och retur, och de senaste av dem har vi
        mätt. Taket är därför ett mätt tal och inte en gissning på hälften.
        """
        if not self.rtt_s:
            return 0.0
        return max(self.rtt_s[-KOMPENSATIONSFONSTER:])

    def skjut_in(self, varden, t_last=None):
        """Skickar värdena med sin ålder räknad från `t_last` (väggklocka).

        `t_last` ska vara tidpunkten då OPC UA-läsningen PÅBÖRJADES, inte då
        den återvände: värdet är minst så gammalt, och en konservativ ålder
        gör ett gammalt värde till ett gammalt värde.

        Åldern som skickas är därför:  (nu - t_last) + rtt_tak()
        Den sista termen är vägen som återstår, uppåt begränsad. Utan den
        landar värdet i serien som 5 ms färskare än det är (M-42), och ett
        fel åt det hållet är precis det som gör en gammal signal samtidig.
        """
        alder = 0.0 if t_last is None else max(0.0, self.klocka() - float(t_last))
        self.n_skjutna += 1
        tak = self.rtt_tak()
        # Taket skickas OCKSA for sig: det ar hopfogningens egen osakerhet,
        # och ogat ska bara det i serien som ett MATT tal i stallet for att
        # anta M-42:s (M-65 §3). Ett tak pa noll (ingen synkning gjord) ar
        # ingen matning och skickas inte.
        return self._anrop(varden=dict(varden or {}),
                           alder_s=alder + tak,
                           hopfogning_s=(tak if tak > 0.0 else None))

    def synka(self, n=KOMPENSATIONSFONSTER):
        """Mäter tur och retur utan att skjuta in något värde.

        Första inskottet har annars ingen mätning att kompensera med. Anropet
        bär inga värden, och bryggan säger också rent ut att inget lagrades.
        """
        svar = None
        for _ in range(max(1, int(n))):
            svar = self._anrop()
        return svar

    def bryt(self, skal):
        """Talar om att det inte finns något färskt värde att komma med."""
        self.n_brutna += 1
        return self._anrop(avbrott=str(skal)[:200])

    # ---- sammanfattning -------------------------------------------------

    def sammanfattning(self):
        ms = sorted(v * 1000.0 for v in self.rtt_s)

        def p(andel):
            if not ms:
                return None
            i = min(len(ms) - 1, int(round(andel * (len(ms) - 1))))
            return round(ms[i], 3)

        return {
            "skjutna": self.n_skjutna,
            "brutna": self.n_brutna,
            "lagrade": self.n_lagrade,
            "utan_axel": self.n_utan_axel,
            "oga_stangt": self.n_oga_stangt,
            "rtt_median_ms": p(0.5),
            "rtt_p95_ms": p(0.95),
            "rtt_max_ms": round(ms[-1], 3) if ms else None,
            "takt": self.takt_sist,
            "simtid": self.simtid_sist,
            "klockbakat": self.klockbakat,
        }
