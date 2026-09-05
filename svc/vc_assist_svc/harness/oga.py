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
from .text import ogonmeningar, satsen_med

_EXT = os.path.join(ROT, "ext", "vc_addon", "vc_assist")
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import oga_kontrakt as K  # noqa: E402

KODER = ("oga_utan_korning", "oga_mildrad", "guld_utan_grind")

# Ord som gor en ogonmening till ett GODKANNANDE. Prova alltid mot
# NEKANDE_OGONORD forst: "ogat sa inte PASS" ar inget godkannande - och prova
# det pa SATSEN, inte pa meningen. Se _obestridd_sats.
GODKANNANDEORD = ("pass", "godkand", "godkänd", "godkant", "godkänt",
                  "gron", "grön", "klart", "fardigt", "färdigt", "verifierad",
                  "verifierat", "guld", "gold", "l1", "l2", "approved")

# Orden som gor att en ogonmening INTE ar ett godkannande. Listan ar en KOPIA
# av samma slag som text.NEKANDE var fore M-95, och den bar samma tva
# storheter: ord som sager att domen var ett UNDERKANNANDE, och bara
# negationer som negerar det de star bredvid. Delningen star har for att den
# ska synas; unionen ar det som provas, och den ar ordagrant lika bred som
# fore M-98. Det som andrades ar VAR fragan stalls - se _obestridd_sats.
UNDERKANNANDEORD = ("fail", "inconclusive", "not gold", "underkand",
                    "underkänd", "rott", "rött", "avbrots", "avbröts",
                    "saknas")

# "inga" tillkom med M-98 och ar det ENDA ord listan blev bredare med. Skalet
# ar matt: "Det finns inga PASS i rapporten." anklagades for att uttala en dom
# i ogats namn, trots att meningen sager motsatsen. Listan bar "ingen" och
# "inget" men inte pluralformen, och text.BARA_NEGATION bar den redan.
# Efterlevnadsbanken star kvar pa 58 av 58 och 28 av 28 med tillagget - inget
# matt fall tystnar av det.
BARA_NEGATION_OGA = ("inte", "icke", "ingen", "inget", "inga", "utan att",
                     "aldrig", "not ", "no ")

NEKANDE_OGONORD = UNDERKANNANDEORD + BARA_NEGATION_OGA

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


def _obestridd_sats(mening_lag: str, ord_: Sequence[str]) -> Optional[str]:
    """Den forsta SATSEN som bar ett ord ur ord_ utan att neka det.

    HELA M-98 ligger i den har funktionen. Fram till dess fragade grinden
    "bar MENINGEN nagot nekande ord?", och det ar fel storhet sa fort
    meningen har mer an en sats. Matt 2026-09-05:

        "Ogat sa PASS, sa cellen ar godkand."  -> ['oga_utan_korning']
        "Ogat sa PASS och inget fel uppstod."  -> []
        "Domen ar guld."        -> ['guld_utan_grind', 'oga_utan_korning']
        "Domen ar guld, och inget fel finns."  -> []

    Nekandet i andra satsen horde till felen. Domen stod kvar oemotsagd, och
    grinden tego. Det ar samma felklass som M-94 fynd 1 och 4, i en KOPIERAD
    ordlista - den sjatte grinden av samma slag.

    Varje sats provas for sig, och det ar med flit: "Ogat sa inte PASS, men
    cellen ar godkand" bar bade en nekad och en obestridd dom, och det ar den
    obestridda som ska anklagas.

    Matchningen gar pa ORDGRANS och inte pa delstrang, och det ar ocksa matt:
    "placeringen" innehaller "ingen", och med delstrangsmatchning trodde
    grinden att en mildrad dom nekade nagot (efterlevnadsbanken 2026-09-04,
    falla F-32). Ordgransen ligger i text.bar_ord, som satsen_med anropar.
    """
    return satsen_med(mening_lag, ord_, NEKANDE_OGONORD)


def _godkannande(mening) -> bool:
    return _obestridd_sats(mening.lag, GODKANNANDEORD) is not None


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

    guld = [m for m in meningar_ if _obestridd_sats(m.lag, GULDORD)]
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
