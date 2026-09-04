# -*- coding: utf-8 -*-
"""Sokskiktet over komponentindexet, format for en sprakmodell.

Operatorens krav, ordagrant: "Informationen maste vara lattillganglig for LLM."
Det ar ett krav pa FORMEN, och det ar skarpare an det later.

Indexet (`katalogindex.py`) bar 3201 komponenter och 4,3 MB. Ett korrekt index
som kostar 4,3 MB att lasa ar oanvandbart for en agent - den laser det inte, och
gissar i stallet, vilket ar precis vad indexet skulle hindra. Korrekt racker
alltsa inte. Det maste ocksa vara BILLIGT.

TRE REGLER SOM FORMEN FOLJER
----------------------------
1. En trafflista ar RADER, inte JSON. En rad per komponent, ett fast antal falt,
   och alltid "N traffar, visar M". Ett svar som inte sager hur mycket det inte
   visade ar ett svar som ser uttommande ut.

2. En bred fraga far ett SAMMANDRAG, inte en lista. "robotar" traffar 1736
   stycken; att radda upp dem ar att branna kontexten pa det agenten inte
   fragade efter. Svaret blir da fordelningen per tillverkare och en uppmaning
   att smalna av. Det ar samma doktrin som 25_kontextbudget.md:s trimning:
   ingen bortprioritering ar tyst.

3. Ett falt som datan inte bar sags SAKNAS. Aldrig noll, aldrig tomt, aldrig
   utelamnat. Ett utelamnat falt lases som "noll" av bade manniskor och
   modeller, och da har indexet ljugit tyst.

VAD DEN INTE GOR
----------------
Den tolkar inte parameternamn. Biblioteket bar 1806 unika namn utan gemensamt
schema (M-57), och en avbildning fran storhet till parameternamn hor till
databladslagret, inte hit. Det som star har ar sokningen och FORMEN pa svaret.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# Sa manga traffar en lista visar innan svaret blir ett sammandrag i stallet.
# MATT i M-60: en rad ar 40-70 tecken, sa tio rader ar under 700 tecken - i
# storleksordningen ett par hundra tokens, vilket far plats i posten
# "verktygsresultat" (25_kontextbudget.md, post 8) utan att tranga ut nagot.
MAX_RADER = 10                  # Satt av M-60.

# Over sa manga traffar ar en lista meningslos oavsett tak: agenten har fragat
# for brett, och det ar den upplysningen den behover.
BRED_FRAGA = 40                 # Satt av M-60.

SAKNAS = "saknas"


class Sokfel(Exception):
    pass


def _text(x) -> str:
    return "" if x is None else str(x)


@dataclass
class Traff:
    namn: str
    tillverkare: str
    kategori: str
    sokvag: str
    granssnitt: int = 0
    parametrar: Dict[str, str] = field(default_factory=dict)

    def rad(self) -> str:
        """En rad, fasta falt, ingen JSON."""
        return "%s | %s | %s | granssnitt %s" % (
            self.tillverkare or SAKNAS, self.namn, self.kategori or SAKNAS,
            self.granssnitt if self.granssnitt else SAKNAS)

    def fullt(self, max_parametrar: int = 25) -> str:
        rader = ["namn: %s" % self.namn,
                 "tillverkare: %s" % (self.tillverkare or SAKNAS),
                 "kategori: %s" % (self.kategori or SAKNAS),
                 "granssnitt: %s" % (self.granssnitt if self.granssnitt else SAKNAS),
                 "fil: %s" % self.sokvag]
        if not self.parametrar:
            rader.append("parametrar: %s (indexet byggdes i grunt lage)" % SAKNAS)
            return "\n".join(rader)
        nycklar = sorted(self.parametrar)
        rader.append("parametrar (%d st):" % len(nycklar))
        for k in nycklar[:max_parametrar]:
            rader.append("  %s = %s" % (k, self.parametrar[k]))
        if len(nycklar) > max_parametrar:
            rader.append("  ... %d till, ej visade"
                         % (len(nycklar) - max_parametrar))
        return "\n".join(rader)


@dataclass
class Svar:
    """Ett sokresultat, med sin egen arlighet inbyggd."""

    totalt: int
    traffar: List[Traff]
    sammandrag: Optional[Dict[str, int]] = None
    fraga: str = ""

    @property
    def visade(self) -> int:
        return len(self.traffar)

    def text(self) -> str:
        if self.totalt == 0:
            return "0 traffar for %s." % (self.fraga or "fragan")
        if self.sammandrag is not None:
            rader = ["%d traffar for %s - for manga for en lista."
                     % (self.totalt, self.fraga or "fragan"),
                     "Fordelning per tillverkare:"]
            for namn, n in sorted(self.sammandrag.items(),
                                  key=lambda p: (-p[1], p[0]))[:15]:
                rader.append("  %-24s %4d" % (namn or SAKNAS, n))
            ovriga = len(self.sammandrag) - 15
            if ovriga > 0:
                rader.append("  ... %d tillverkare till" % ovriga)
            rader.append("Smalna av med tillverkare, kategori eller ett "
                         "namnfragment.")
            return "\n".join(rader)
        rader = ["%d traffar, visar %d." % (self.totalt, self.visade)]
        rader.extend(t.rad() for t in self.traffar)
        if self.visade < self.totalt:
            rader.append("... %d till, ej visade." % (self.totalt - self.visade))
        return "\n".join(rader)

    def tecken(self) -> int:
        return len(self.text())


class Katalog(object):
    """Indexet i minnet, med sokning.

    3201 poster ar litet. En linjar genomsokning tar millisekunder, och en
    databas skulle inte gora nagot billigare - den skulle bara flytta samma
    paase parametrar till en annan lagringsform. Skalet att INTE bygga en
    grafdatabas ar alltsa matt och inte principiellt.
    """

    def __init__(self, poster: Sequence[Traff], rot: str = "", djupt: bool = False):
        self.poster = list(poster)
        self.rot = rot
        self.djupt = bool(djupt)

    # ---- lasning -------------------------------------------------------

    @staticmethod
    def fran_index(index: Dict[str, object]) -> "Katalog":
        if not isinstance(index, dict) or "poster" not in index:
            raise Sokfel("det har ar inget katalogindex")
        poster = [Traff(namn=_text(p.get("namn")),
                        tillverkare=_text(p.get("tillverkare")),
                        kategori=_text(p.get("kategori")),
                        sokvag=_text(p.get("sokvag")),
                        granssnitt=int(p.get("granssnitt") or 0),
                        parametrar=dict(p.get("parametrar") or {}))
                   for p in index["poster"]]
        return Katalog(poster, _text(index.get("rot")),
                       bool(index.get("djupt")))

    @staticmethod
    def las_fil(sokvag: str) -> "Katalog":
        if not os.path.exists(sokvag):
            raise Sokfel("inget index pa %s" % sokvag)
        with open(sokvag, "r", encoding="utf-8") as f:
            return Katalog.fran_index(json.load(f))

    # ---- sokningen -----------------------------------------------------

    def sok(self, fraga: str = "", tillverkare: str = "", kategori: str = "",
            har_parameter: str = "", max_rader: int = MAX_RADER) -> Svar:
        """Filtrera och lamna ett svar som bar sin egen arlighet.

        `fraga` matchas mot namnet, skiftlagesokansligt och som delstrang -
        en modell skriver "IRB 6700" nar filen heter "IRB 6700-150_3_20".
        """
        traffar = self._filtrera(fraga, tillverkare, kategori, har_parameter)
        beskrivning = self._beskriv_fraga(fraga, tillverkare, kategori,
                                          har_parameter)
        if len(traffar) > BRED_FRAGA:
            fordelning: Dict[str, int] = {}
            for t in traffar:
                fordelning[t.tillverkare] = fordelning.get(t.tillverkare, 0) + 1
            return Svar(len(traffar), [], fordelning, beskrivning)
        return Svar(len(traffar), traffar[:max(int(max_rader), 1)],
                    None, beskrivning)

    def _filtrera(self, fraga, tillverkare, kategori, har_parameter) -> List[Traff]:
        f = (fraga or "").strip().lower()
        tv = (tillverkare or "").strip().lower()
        kt = (kategori or "").strip().lower()
        hp = (har_parameter or "").strip().lower()
        ut = []
        for t in self.poster:
            if f and f not in t.namn.lower():
                continue
            if tv and tv != t.tillverkare.lower():
                continue
            if kt and kt != t.kategori.lower():
                continue
            if hp and not any(hp in k.lower() for k in t.parametrar):
                continue
            ut.append(t)
        # Kortast namn forst: "IRB 120" fore "IRB 120-3/0.6 LID". En modell som
        # sokte pa ett kort namn menade oftast grundmodellen.
        ut.sort(key=lambda t: (len(t.namn), t.tillverkare, t.namn))
        return ut

    @staticmethod
    def _beskriv_fraga(fraga, tillverkare, kategori, har_parameter) -> str:
        delar = []
        if fraga:
            delar.append('namn ~ "%s"' % fraga)
        if tillverkare:
            delar.append("tillverkare = %s" % tillverkare)
        if kategori:
            delar.append("kategori = %s" % kategori)
        if har_parameter:
            delar.append('bar parameter ~ "%s"' % har_parameter)
        return " och ".join(delar) if delar else "hela katalogen"

    # ---- oversikter ----------------------------------------------------

    def tillverkare(self) -> Dict[str, int]:
        ut: Dict[str, int] = {}
        for t in self.poster:
            ut[t.tillverkare] = ut.get(t.tillverkare, 0) + 1
        return ut

    def kategorier(self) -> Dict[str, int]:
        ut: Dict[str, int] = {}
        for t in self.poster:
            ut[t.kategori] = ut.get(t.kategori, 0) + 1
        return ut

    def oversikt(self, max_rader: int = 12) -> str:
        """Det forsta en agent bor se: vad finns det HAR, i stora drag."""
        k = self.kategorier()
        tv = self.tillverkare()
        rader = ["%d komponenter, %d tillverkare, %d kategorier."
                 % (len(self.poster), len(tv), len(k)),
                 "Indexet ar %s." % ("djupt (parametrar ingar)" if self.djupt
                                     else "grunt (kategori kommer fran "
                                          "katalognamnet, se M-58)"),
                 "Storsta kategorierna:"]
        for namn, n in sorted(k.items(), key=lambda p: (-p[1], p[0]))[:max_rader]:
            rader.append("  %-32s %5d" % (namn or SAKNAS, n))
        return "\n".join(rader)

    def med_namn(self, namn: str) -> Optional[Traff]:
        n = (namn or "").strip().lower()
        for t in self.poster:
            if t.namn.lower() == n:
                return t
        return None
