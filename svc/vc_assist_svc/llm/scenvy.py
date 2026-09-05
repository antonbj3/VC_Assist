# -*- coding: utf-8 -*-
"""Scenvyn: hela listan nar den ryms, och en sammanfattning som ar OFARLIG.

REGELN SOM GOR SAMMANFATTNINGEN OFARLIG
---------------------------------------
Ett namn som turen behover far ALDRIG sammanfattas bort. Sker det hittar
modellen pa ett namn, och det ar precis den felklass hela kunskapsindexet
finns for att stanga (I9, 46_kunskapsindex.md).

Darfor ar arbetsmangden formulerad som en SKYLDIGHET MOT PLANEN, inte som en
relevansbedomning. Sammanfattaren bedomer ingenting: den laser komponentnamnen
ur plannodernas argument och foljer kopplingsgrafen ETT steg darifran. En
relevansbedomning hade varit en asikt, och en asikt gar inte att prova.

DE FYRA REGLERNA, I ORDNING (25_kontextbudget.md avsnitt 3)
    1. Arbetsmangden gar fram HEL.
    2. Resten blir rakningar per kategori.
    3. En rad sager vad som utelamnades och efter vilken regel.
    4. `avkortad` propageras ordagrant. Att svalja verktygets egen avkortad i
       en sammanfattning vore att gora fail-closed till fail-open.

INGEN SAMMANFATTNING AV EN SAMMANFATTNING
Varje sammanfattning bar `ur_kalla` for det RAVARA-svar den kom ur. Tva led av
grovhet ser likadana ut som ett led, och forlusten gar inte langre att mata -
samma mekanism som gor en cache farlig: tidsvinsten och kvalitetsforlusten
kommer ur samma steg, och bara det ena syns.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

from .kapning import (FALT_ANTAL, FALT_AVKORTAD, FALT_KAPRAD, Anmarkning,
                      Verktygssvar)

# Over den har gransen sammanfattas scenvyn.
# PRELIMINAR, satts av matning M-29. Motivet ar matt: bankens storsta scen ar
# 9 komponenter over 51 uppgifter (M-45), sa INGEN bankuppgift sammanfattas
# nagonsin - en bank som mater sammanfattaren i stallet for modellen mater fel
# sak. Gransens LAGE ar daremot inte matt.
SCEN_FULL_MAX = 60          # PRELIMINAR, satts av M-29; motivet M-45

# Samma sak per komponent. PRELIMINAR, matning M-29.
EGENSKAPER_FULL_MAX = 40    # PRELIMINAR, satts av M-29

S1_NAMN_BORTA = "S1_NAMN_BORTA"
S2_AVKORTAD_SVALD = "S2_AVKORTAD_SVALD"
S3_KATEGORIER_SUMMERAR_INTE = "S3_KATEGORIER_SUMMERAR_INTE"
S4_SAMMANFATTNING_AV_SAMMANFATTNING = "S4_SAMMANFATTNING_AV_SAMMANFATTNING"
S5_UTAN_RAD = "S5_UTAN_RAD"


def arbetsmangd(plannamn: Iterable[str],
                kopplingar: Sequence[Tuple[str, str]]) -> Set[str]:
    """Planens egna namn plus allt som ar kopplat till nagot av dem.

    Ett steg ut i grafen, inte tva. Skalet ar att regeln ska ga att prova:
    "kopplad till planens komponenter" ar en mekanisk fraga, "relevant for
    planen" ar det inte.
    """
    kvar = set(n for n in plannamn if n)
    ut = set(kvar)
    for a, b in kopplingar:
        if a in kvar:
            ut.add(b)
        if b in kvar:
            ut.add(a)
    return ut


def _kategori(post: Dict[str, Any]) -> str:
    v = post.get("category")
    return v if isinstance(v, str) and v else "utan kategori"


def sammanfatta(svar: Verktygssvar, plannamn: Iterable[str],
                kopplingar: Sequence[Tuple[str, str]] = (),
                tak: int = SCEN_FULL_MAX) -> Verktygssvar:
    """list_components-svaret, helt under taket och sammanfattat over det."""
    if svar.sammanfattning:
        raise ValueError(
            "%s ar redan en sammanfattning av %s; en sammanfattning vars kalla "
            "ar en annan sammanfattning ar ett linterfel"
            % (svar.verktyg, svar.ur_kalla))
    resultat = svar.resultat
    if not isinstance(resultat, dict) or not isinstance(
            resultat.get("components"), list):
        return svar
    poster = resultat["components"]
    if len(poster) <= tak:
        return svar

    behovs = arbetsmangd(plannamn, kopplingar)
    visade = [p for p in poster if p.get("name") in behovs]
    kategorier: Dict[str, int] = {}
    for p in poster:
        k = _kategori(p)
        kategorier[k] = kategorier.get(k, 0) + 1

    innehall = {
        "components": visade,
        FALT_ANTAL: len(visade),
        "antal_i_scenen": len(poster),
        "kategorier": kategorier,
        FALT_AVKORTAD: bool(resultat.get(FALT_AVKORTAD)),
        FALT_KAPRAD: (
            "%d av %d komponenter visas: planens och deras kopplade. "
            "Anvand find_component for de ovriga. Kallan ar %s."
            % (len(visade), len(poster), svar.id)),
    }
    if resultat.get(FALT_AVKORTAD):
        innehall[FALT_KAPRAD] += (
            " Verktyget hade dessutom redan klippt listan vid sitt eget tak "
            "(avkortad=true), sa scenen kan innehalla fler komponenter an %d."
            % len(poster))
    return Verktygssvar(verktyg=svar.verktyg, argument=dict(svar.argument),
                        ok=svar.ok, resultat=innehall, fel=svar.fel,
                        felnyckel=svar.felnyckel, id=svar.id,
                        ur_kalla=svar.id, sammanfattning=True)


def granska(ravara: Verktygssvar, vy: Verktygssvar,
            behovda_namn: Iterable[str]) -> List[Anmarkning]:
    """Faller pa en sammanfattning som tappat ett namn turen behover."""
    ut: List[Anmarkning] = []
    if not isinstance(vy.resultat, dict):
        return ut
    if vy is ravara or not vy.sammanfattning:
        # Hela listan gick fram. Da finns inget att sammanfatta bort.
        namn = set()
        if isinstance(ravara.resultat, dict):
            namn = set(p.get("name")
                       for p in ravara.resultat.get("components") or [])
        for n in behovda_namn:
            if n and n not in namn:
                ut.append(Anmarkning(
                    S1_NAMN_BORTA,
                    "%s: turen behover %r och det finns inte i scenvyn"
                    % (vy.verktyg, n)))
        return ut

    visade = set(p.get("name") for p in vy.resultat.get("components") or [])
    for n in behovda_namn:
        if n and n not in visade:
            ut.append(Anmarkning(
                S1_NAMN_BORTA,
                "%s: %r ar en komponent turen anvander, och den finns inte i "
                "den sammanfattade scenvyn. En miss andrar regel 1; den ar "
                "ingen ratt att skruva pa" % (vy.verktyg, n)))
    ra = ravara.resultat if isinstance(ravara.resultat, dict) else {}
    if ra.get(FALT_AVKORTAD) and not vy.resultat.get(FALT_AVKORTAD):
        ut.append(Anmarkning(
            S2_AVKORTAD_SVALD,
            "%s: verktyget sa avkortad=true och sammanfattningen sager det "
            "inte. Att svalja avkortad ar att gora fail-closed till fail-open"
            % vy.verktyg))
    poster = ra.get("components") or []
    summa = sum((vy.resultat.get("kategorier") or {}).values())
    if poster and summa != len(poster):
        ut.append(Anmarkning(
            S3_KATEGORIER_SUMMERAR_INTE,
            "%s: kategorierna summerar till %d, scenen har %d komponenter"
            % (vy.verktyg, summa, len(poster))))
    if not vy.resultat.get(FALT_KAPRAD):
        ut.append(Anmarkning(
            S5_UTAN_RAD,
            "%s: sammanfattningen sager inte vad som utelamnades och efter "
            "vilken regel" % vy.verktyg))
    if ravara.sammanfattning:
        ut.append(Anmarkning(
            S4_SAMMANFATTNING_AV_SAMMANFATTNING,
            "%s: kallan %s ar sjalv en sammanfattning"
            % (vy.verktyg, ravara.id)))
    return ut
