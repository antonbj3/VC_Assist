# -*- coding: utf-8 -*-
"""REDOVISNINGEN: tva satt att gora ett riktigt underlag till en osanning.

Bada reglerna har var bedda fram till M-53, och bada handlar om samma sak:
underlaget ar akta, och slutsatsen ar for stor.

  avkortat_som_helhet   VRK-009. Ett listande verktyg klipper vid 500 poster
                        (kodmall.MAX_POSTER, ur bryggans 1 MiB-kropp) och
                        sager det i svaret med avkortad=true. Talet i svaret
                        ar da ett tal om DE FORSTA 500, inte om layouten. En
                        modell som rapporterar "layouten har 500 komponenter"
                        har ett verktygssvar bakom sig - verify-contract
                        stodjer talet - och sager anda nagot falskt.
  bevis_ur_simulering   SYS-003. Simuleringen ar felfinnande, aldrig bevis.
                        Sensorstuds, stalldonsdynamik, faltbussjitter och
                        verklig hardvara finns inte i den. Ett godkant
                        simuleringsvarv som beskrivs som ett BEVIS ar den
                        dyraste sortens overtro i driftsattning, och
                        grindkedjans egen rubrik "Vad ingen grind fangar"
                        star dar just for att racka vidden ska sta utskriven.

RIKTNINGEN i bada: grinden kraver en TYDLIG markor och slapper vid tvivel.
Avkortningsgrinden anklagar bara nar ett verktygssvar FAKTISKT bar
avkortad=true; bevisgrinden kraver bade ett bevisord och ett simuleringsord i
SAMMA mening, och inget nekande. "Simuleringen bevisar ingenting om verklig
hardvara" bar bada orden och ett nekande, och gar fri.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple

from .text import bar_delstrang, bar_ord, meningar, NEKANDE

KODER = ("avkortat_som_helhet", "bevis_ur_simulering")

# Nycklar i ett verktygssvar som sager att listan ar klippt. Bada formerna
# star har darfor att svaren ar var egen JSON: avkortad ar vart faltnamn
# (verktyg/kodmall.py), truncated ar den engelska formen ett framtida verktyg
# kan komma att anvanda. Fail-closed: okand nyckel raknas inte som klippt,
# men provet test_varje_listande_verktyg_bar_avkortadfaltet haller listan
# levande.
AVKORTNINGSNYCKLAR = ("avkortad", "truncated")

# Ord som visar att svaret SJALVT sager att listan ar ofullstandig.
AVKORTNINGSORD = (
    "avkortad", "avkortat", "avkortade", "klippt", "klippts", "kapad",
    "kapat", "ofullstandig", "ofullständig", "ofullstandigt",
    "ofullständigt", "inte hela", "inte alla", "bara de forsta",
    "bara de första", "de forsta", "de första", "delvis", "fler an",
    "fler än", "minst", "atminstone", "åtminstone",
    "truncated", "partial", "incomplete", "at least", "first 500",
)

# Ord som gor en mening till ett BEVISPASTAENDE.
BEVISORD = (
    "bevis", "bevisar", "bevisat", "bevisad", "bevisade", "bevisning",
    "garanterar", "garanterat", "garanterad", "garanti", "sakerstaller",
    "säkerställer", "sakerstallt", "säkerställt", "utesluter", "uteslutet",
    "proves", "proven", "proof", "guarantees", "guaranteed", "ensures",
    "verifierar att",
)

# Ord som gor meningen till en mening OM SIMULERINGEN. Bevisordet ensamt
# racker inte: "matningen bevisar" ar en annan sak, och det ar just
# simuleringens rackvidd SYS-003 handlar om.
SIMULERINGSORD = (
    "simulering", "simuleringen", "simulerat", "simulerad", "simulerade",
    "simulation", "simulerar", "korningen", "körningen", "simvarvet",
    "cykeln gick", "simuleringsvarv", "sim run", "the run",
)


@dataclass(frozen=True)
class Anmarkning:
    kod: str
    skal: str
    mening: str = ""

    def text(self) -> str:
        if self.mening:
            return "%s: %s (i meningen: %r)" % (self.kod, self.skal, self.mening)
        return "%s: %s" % (self.kod, self.skal)


def _avkortade(utfall: Sequence[Any]) -> List[str]:
    """Verktygen i turen vars svar sager att listan ar klippt."""
    ut = []
    for u in utfall:
        if not getattr(u, "ok", False):
            continue
        resultat = getattr(u, "resultat", None)
        if not isinstance(resultat, dict):
            continue
        for nyckel in AVKORTNINGSNYCKLAR:
            if resultat.get(nyckel) is True:
                ut.append(getattr(u, "verktyg", "verktyget"))
                break
    return ut


def granska(text: str, utfall: Sequence[Any] = ()) -> Tuple[Anmarkning, ...]:
    """Provar slutsvaret mot turens utfall och mot simuleringens rackvidd."""
    anmarkningar: List[Anmarkning] = []

    klippta = _avkortade(utfall)
    if klippta and not bar_delstrang((text or "").lower(), AVKORTNINGSORD):
        anmarkningar.append(Anmarkning(
            kod="avkortat_som_helhet",
            skal=("%s svarade avkortad=true, alltsa en KLIPPT lista, och "
                  "svaret sager ingenstans att den ar ofullstandig. Talen i "
                  "svaret galler da de forsta posterna och inte layouten; "
                  "behandla svaret som ofullstandigt och skriv det (VRK-009)"
                  % ", ".join(sorted(set(klippta))))))

    for mening in meningar(text or ""):
        lag = mening.lag
        if bar_ord(lag, NEKANDE):
            continue
        if not bar_delstrang(lag, BEVISORD):
            continue
        if not bar_delstrang(lag, SIMULERINGSORD):
            continue
        anmarkningar.append(Anmarkning(
            kod="bevis_ur_simulering",
            skal=("simuleringen ar felfinnande, aldrig bevis: sensorstuds, "
                  "stalldonsdynamik, faltbussjitter och verklig hardvara "
                  "finns inte i den. Ett godkant simuleringsvarv sager att "
                  "inget fel HITTADES, inte att inget fel FINNS (SYS-003)"),
            mening=mening.text))
    return tuple(anmarkningar)


def omskrivningskrav(anmarkningar: Sequence[Anmarkning]) -> str:
    rader = ["Svaret godkanns inte. Det drar en storre slutsats an "
             "underlaget bar:"]
    for a in anmarkningar:
        rader.append("  - %s" % a.text())
    rader.append("Skriv om svaret. Sag vad underlaget FAKTISKT racker till: "
                 "en klippt lista ar de forsta posterna, och ett godkant "
                 "simuleringsvarv ar ett varv utan hittade fel (VRK-009, "
                 "SYS-003).")
    return "\n".join(rader)
