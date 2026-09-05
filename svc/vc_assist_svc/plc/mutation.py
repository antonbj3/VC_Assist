# -*- coding: utf-8 -*-
"""Kanda skador i en fungerande losning. Facit ar mutationen sjalv.

## Varfor

Banken har 63 uppgifter, 26 med referenslosning. Det ar for lite for att mata
nagot om grindkedjans KANSLIGHET, och `M-111` visade problemet skarpt: 31 av
grind 2:s 68 fallplatser hade aldrig fyrat under hela provsviten.

En mutation loser det utan att fuska. Vi tar en losning som **passerar** alla
grindar, gor EN kand skada, och vet darmed exakt vad som maste fangas. Facit
kommer ur skadan - inte ur var egen domare, som `85_bankkontraktet.md` §2
forbjuder.

De 26 referenserna bar **2 192 brytpunkter**: 971 tilldelningar, 469
TRUE/FALSE-literaler, 282 AND/OR, 193 NOT, 79 jamforelser, 57 IF/ELSE, 42
timerinstanser, 42 tidsliteraler, 30 flankdetektorer, 27 CASE.

## Vad matningen faktiskt svarar pa

Inte "ar koden ratt" - det vet vi, den ar referensen. Utan:

**fangas skadan, och av VEM?**

En textmutation (obalanserat block, ogiltig tidsliteral) ska fangas av grind
1-2. En BETEENDEmutation (ett struket NOT, en flank som blir en niva) kan inte
fangas av en textgrind alls - den maste fangas av sparfacit. Att den slipper
igenom grind 2 ar alltsa RATT, och att den slipper igenom ALLT ar ett hal i
banken.

Det ar samma sak `54_felstallda_fragor.md` §3 efterlyste: andelen domar som
kraver att man ser mer an en fil.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass(frozen=True)
class Skada:
    """En kand skada i en fungerande kropp."""

    sort: str
    beskrivning: str
    # Vilket LAGER som rimligen ska fanga den. Inte ett lofte - en hypotes som
    # matningen provar, och en avvikelse ar fyndet.
    vantat_lager: str          # "text" (grind 1-3) eller "beteende" (sparfacit)
    kropp: str
    rad: int
    fore: str
    efter: str


def _ersatt_n(text: str, monster, ersattning, n: int):
    """Byt ut FOREKOMST n (0-indexerad). Returnerar (ny text, rad, fore, efter)."""
    traffar = list(re.finditer(monster, text))
    if n >= len(traffar):
        return None
    t = traffar[n]
    ny = text[:t.start()] + ersattning(t) + text[t.end():]
    rad = text[:t.start()].count("\n") + 1
    return ny, rad, t.group(0), ersattning(t)


# (namn, monster, ersattning, vantat lager, beskrivning)
_SKADOR: List[Tuple[str, str, Callable, str, str]] = [
    ("NOT_STRUKEN", r"\bNOT\s+", lambda m: "", "beteende",
     "ett NOT struket - villkoret blir sitt eget motsatta"),
    ("AND_TILL_OR", r"\bAND\b", lambda m: "OR", "beteende",
     "AND blir OR - villkoret slapper igenom nar bara ett led haller"),
    ("OR_TILL_AND", r"\bOR\b", lambda m: "AND", "beteende",
     "OR blir AND - villkoret kraver bada leden"),
    ("SANT_TILL_FALSKT", r"\bTRUE\b", lambda m: "FALSE", "beteende",
     "TRUE blir FALSE - utgangen satts aldrig"),
    ("FALSKT_TILL_SANT", r"\bFALSE\b", lambda m: "TRUE", "beteende",
     "FALSE blir TRUE - utgangen nollstalls aldrig"),
    ("FLANK_TILL_NIVA", r"(\w+)\s*\(\s*CLK\s*:=\s*(\w+)\s*\)\s*;",
     lambda m: "(* flank struken *)", "beteende",
     "flankdetektorn struken - villkoret lases pa niva i stallet for pa flank (F15)"),
    ("FLANKENS_Q_TILL_SIGNAL", r"(\w+)\.Q\b", lambda m: m.group(1),
     "beteende", "flankens Q byts mot instansen sjalv"),
    ("TID_FORDUBBLAD", r"T#(\d+(?:\.\d+)?)(ms|s|m|h)\b",
     lambda m: "T#%s%s" % (float(m.group(1)) * 2, m.group(2)), "beteende",
     "tiden fordubblad - vakten faller utanfor sin brakett (F6)"),
    ("TID_OGILTIG", r"T#(\d+(?:\.\d+)?)(ms|s|m|h)\b",
     lambda m: "T#%s" % m.group(1), "text",
     "tidsliteralen tappar sin enhet - grind 2 ska falla den"),
    ("JAMFORELSE_VAND", r"(?<![:<>])(<=|>=|<|>)(?!=)",
     lambda m: {"<": ">", ">": "<", "<=": ">=", ">=": "<="}[m.group(1)],
     "beteende", "jamforelsen vand - villkoret galler tvartom"),
    ("END_IF_STRUKEN", r"\bEND_IF\s*;", lambda m: "", "text",
     "ett END_IF struket - blocket balanserar inte (grind 2)"),
    ("SEMIKOLON_STRUKET", r";", lambda m: "", "text",
     "ett semikolon struket - satsen avslutas inte"),
    ("ICKE_ASCII", r"\(\*", lambda m: "(* ä", "text",
     "ett icke-ASCII-tecken i en kommentar - teckenkodningen agar vi inte"),
]


def skador(kropp: str, per_sort: int = 3) -> List[Skada]:
    """Alla kanda skador vi kan gora i en kropp, hogst `per_sort` av varje.

    Taket per sort finns for att 971 tilldelningar annars dranker de 30
    flankdetektorerna, och det ar flankarna som ar intressanta.
    """
    ut: List[Skada] = []
    for sort, monster, ers, lager, besk in _SKADOR:
        n = 0
        while n < per_sort:
            r = _ersatt_n(kropp, monster, ers, n)
            if r is None:
                break
            ny, rad, fore, efter = r
            if ny != kropp:
                ut.append(Skada(sort=sort, beskrivning=besk, vantat_lager=lager,
                                kropp=ny, rad=rad, fore=fore, efter=efter))
            n += 1
    return ut
