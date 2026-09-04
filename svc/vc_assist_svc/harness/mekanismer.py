# -*- coding: utf-8 -*-
"""Namnen pa de tvingande mekanismerna. En enda kalla.

En instruktionsregel som ar markt allvar="block" MASTE namnge den mekanism som
tvingar den, och namnet maste sta har. Det ar bindningen mellan korpusen pa
disk och koden: en regel som pastar sig vara tvingad av nagot som inte finns
ar en asikt med en grind-etikett, och det ar precis den sortens dod grind
96_ingen_skuld.md S2 handlar om.

Bindningen provas at bada hallen i tests/enhet/test_harness.py:

  * varje mekanismnamn i en regel finns har  (instruktioner.granska_korpus)
  * varje mekanism har namns av minst en regel  (ingen kod utan konsument, S3)
  * varje mekanism har minst en falla i efterlevnadsbanken (fallor.py)

Ingen import harifran och ingen import hit ur nagot annat i harnessen an
namnuppslag. Modulen ar ren data, sa att den kan lasas av bade
instruktionslasaren och grindarna utan att skapa en cirkel.
"""
from __future__ import annotations

from types import MappingProxyType

# namn -> (kort beskrivning, var mekanismen bor)
MEKANISMER = MappingProxyType({
    "arlighet": (
        "honesty-rewrite: ett svar som pastar framgang medan sista verktyget "
        "foll tvingas skrivas om",
        "harness/arlighet.py"),
    "verifiering": (
        "verify-contract: namn och tal plockas ur modellens egen text och "
        "provas mot vad verktygen faktiskt returnerade",
        "harness/verifiering.py"),
    "schema": (
        "verktygsregistret och validera_argument: okant verktyg, okant "
        "argument, saknat obligatoriskt argument och fel typ avvisas fore "
        "korning",
        "verktyg/schema.py via harness/forgranskning.py"),
    "api_index": (
        "AST-validering mot den matta API-ytan: ett uppfunnet VC-namn "
        "avvisas fore korning",
        "api_index.py via harness/forgranskning.py"),
    "skrivgrind": (
        "bryggans skrivgrind: kod som skriver utan att ga genom kon, och "
        "skriptbeteenden som dodar bryggan, avvisas",
        "ext/vc_addon/vc_assist/skrivgrind.py via harness/forgranskning.py"),
    "sakerhet": (
        "sakerhetsgrinden: varje beroring av en sakerhetsmarkt tagg eller "
        "komponent i ett skrivande lage avvisas ovillkorligt",
        "harness/sakerhet.py"),
    "katalog": (
        "kataloggrinden: en komponent-URI som inte star i det matta "
        "katalogindexet avvisas fore korning",
        "harness/forgranskning.py mot bank/katalog_index.json"),
    "oga": (
        "ogongrinden: en dom i ogats namn utan att ogat kort, en mildrad dom "
        "och ett sjalvsatt guld avvisas",
        "harness/oga.py mot oga_kontrakt.py och guldgrind.py"),
    "loop": (
        "verktygsloopens tak och stoppregler: rundtak, raka misslyckanden, "
        "upprepat identiskt anrop och tystnad",
        "harness/loop.py"),
    "ratkod": (
        "ra kod fran modellen avvisas: kod smugglad i ett argument och kod "
        "som foreslas for korning utanfor verktygen",
        "harness/forgranskning.py"),
})

NAMN = tuple(sorted(MEKANISMER))


def beskrivning(namn):
    """Kastar KeyError pa okant namn.

    Det ar avsikten: ett okant mekanismnamn ska aldrig passera tyst.
    """
    return MEKANISMER[namn][0]
