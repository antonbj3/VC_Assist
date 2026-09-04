# -*- coding: utf-8 -*-
"""Ogongrinden: modellen far inte doma i ogats namn.

Tre saker fangas, och alla tre ar samma sak sedd fran olika hall: modellen ar
aldrig sin egen domare (I11).

  oga_utan_korning   svaret uttalar en dom i ogats namn utan att ogat har
                     kort, eller med en rapport som inte gar att lasa. Det
                     finns da INGEN dom att referera, och tystnad ar aldrig
                     ett godkannande (I3).
  oga_mildrad        ogat har kort och sagt FAIL eller INCONCLUSIVE, och
                     svaret sager PASS, godkant eller klart. Domen ar
                     auktoritativ; INCONCLUSIVE raknas som inte godkant.
  guld_utan_grind    svaret kallar resultatet guld utan att guldgrinden har
                     fallt ett gulddom. Endast en korning i VC befordrar
                     kandidat till guld (50_grindar.md).

Grinden RAKNAR INTE OM nagot matt. Den anropar oga_kontrakt.las(), som ar
ogats egen lasare, och laser dess dom. Doktrinen kommer ur en matt incident:
en omimplementerad positionsdom underkande 2 av 4 medan ogat visade 4 av 4.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from .sakerhet import ROT
from .text import ogonmeningar

_EXT = os.path.join(ROT, "ext", "vc_addon", "vc_assist")
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import oga_kontrakt as K  # noqa: E402

KODER = ("oga_utan_korning", "oga_mildrad", "guld_utan_grind")

# Ord som gor en ogonmening till ett GODKANNANDE. Prova alltid mot
# NEKANDE_OGONORD forst: "ogat sa inte PASS" ar inget godkannande.
GODKANNANDEORD = ("pass", "godkand", "godkänd", "godkant", "godkänt",
                  "gron", "grön", "klart", "fardigt", "färdigt", "verifierad",
                  "verifierat", "guld", "gold", "l1", "l2", "approved")

NEKANDE_OGONORD = ("fail", "inconclusive", "inte", "icke", "ingen", "inget",
                   "not gold", "underkand", "underkänd", "rott", "rött",
                   "avbrots", "avbröts", "utan att", "aldrig", "saknas",
                   "not ", "no ")

# Ord som pastar guld. Halls skilda fran GODKANNANDEORD darfor att guld ar en
# starkare utsaga an PASS: guld kraver bade ogats PASS och grindens dom.
GULDORD = ("guld", "gold", "l1", "l2", "gold_verified_core",
           "gold_line_verified")


@dataclass(frozen=True)
class Anmarkning:
    kod: str
    skal: str
    mening: str = ""

    def text(self) -> str:
        if self.mening:
            return "%s: %s (i meningen: %r)" % (self.kod, self.skal, self.mening)
        return "%s: %s" % (self.kod, self.skal)


def _bar(lag: str, ord_: Sequence[str]) -> Optional[str]:
    for o in ord_:
        if o in lag:
            return o
    return None


def _godkannande(mening) -> bool:
    lag = mening.lag
    if _bar(lag, NEKANDE_OGONORD):
        return False
    return _bar(lag, GODKANNANDEORD) is not None


def las_dom(ogonrapport: Optional[str]):
    """(dom, skal). dom ar None nar ingen lasbar dom finns.

    Anropar ogats egen lasare. Kastar aldrig vidare: en oparsbar rapport ar
    ingen dom, och grinden ska svara pa det utan att falla sjalv (S10).
    """
    if not ogonrapport or not ogonrapport.strip():
        return None, "ogat har inte kort i den har turen"
    try:
        rapport = K.las(ogonrapport)
    except K.Kontraktsfel as e:
        return None, "ogats rapport gar inte att lasa: %s" % e.grinddom
    if rapport.dom is None:
        return None, "ogats rapport saknar dom"
    return rapport, None


def granska(text: str, ogonrapport: Optional[str] = None,
            guldbeslut: Any = None) -> Tuple[Anmarkning, ...]:
    """Provar slutsvaret mot ogats egen dom och mot guldgrindens beslut."""
    anmarkningar: List[Anmarkning] = []
    meningar_ = ogonmeningar(text)
    if not meningar_:
        return ()

    rapport, skal = las_dom(ogonrapport)
    godkannanden = [m for m in meningar_ if _godkannande(m)]

    if rapport is None:
        for m in godkannanden:
            anmarkningar.append(Anmarkning(
                kod="oga_utan_korning",
                skal=("svaret uttalar en dom i ogats namn men %s; modellen ar "
                      "aldrig sin egen domare (I11)" % skal),
                mening=m.text))
    else:
        varde = rapport.dom[0]
        if not rapport.godkand():
            for m in godkannanden:
                anmarkningar.append(Anmarkning(
                    kod="oga_mildrad",
                    skal=("ogat sa %s (%s) men svaret sager att det gick "
                          "igenom; domen ar auktoritativ och INCONCLUSIVE "
                          "raknas som inte godkant" % (varde, rapport.dom[1])),
                    mening=m.text))

    guld = [m for m in meningar_
            if _bar(m.lag, GULDORD) and not _bar(m.lag, NEKANDE_OGONORD)]
    if guld and not (guldbeslut is not None and getattr(guldbeslut, "guld", False)):
        vad = ("guldgrinden har inte kort" if guldbeslut is None
               else "guldgrinden sa %s" % guldbeslut.text())
        for m in guld:
            anmarkningar.append(Anmarkning(
                kod="guld_utan_grind",
                skal=("svaret kallar resultatet guld men %s; endast en "
                      "korning i VC befordrar kandidat till guld" % vad),
                mening=m.text))
    return tuple(anmarkningar)


def omskrivningskrav(anmarkningar: Sequence[Anmarkning],
                     ogonrapport: Optional[str] = None) -> str:
    """Texten tillbaka till modellen, med ogats egen domsrad citerad."""
    rader = ["Svaret godkanns inte. Det uttalar en dom som inte ar din att "
             "falla:"]
    for a in anmarkningar:
        rader.append("  - %s" % a.text())
    rapport, _skal = las_dom(ogonrapport)
    if rapport is not None:
        rader.append("Ogats egen domsrad: EYES VERDICT %s %s"
                     % (rapport.dom[0], rapport.dom[1]))
    rader.append("Skriv om svaret. Citera ogats dom som den star, eller skriv "
                 "att ogat inte har kort. Kalla ingenting guld sjalv "
                 "(ARL-005, ARL-006).")
    return "\n".join(rader)
