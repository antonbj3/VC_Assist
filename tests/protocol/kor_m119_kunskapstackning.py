#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-119: kan en sprakmodell hitta det den behover - matt BRETT, per frageslag.

Alias for kor_kunskapstackning.py under standardnamnet kor_m119_kunskapstackning.py.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "de levererade uppslagsverktygen svarar pa en matt andel av de fragor "
        "en modell faktiskt staller nar den bygger en cell, och andelen ar "
        "OLIKA STOR per frageslag - namn och URI:er besvaras nastan alltid, "
        "medan enheter, signalkartor och standarder inte besvaras alls.",
    "under_prov": (
        "tests/protocol/stod/slaupp.py",
        "svc/vc_assist_svc/api_index.py",
        "svc/vc_assist_svc/katalogsok.py",
        "svc/vc_assist_svc/katalogindex.py",
        "svc/vc_assist_svc/komponentdatablad.py",
        "svc/vc_assist_svc/verktyg/kunskap.py",
    ),
    "facit":
        "for varje fraga: vilken av klasserna SVAR, HALVT, SAKNAS och TYST FEL "
        "svaret hor till, och for de fragor som har ett oberoende varde "
        "(bankens katalogindex, stamplat PUBLICERAD_SPEC ur tillverkarens "
        "datablad) dessutom om verktygets varde motsager det",
    "facitkalla":
        "Fragorna harleds mekaniskt ur tre kallor som ligger UTANFOR "
        "under_prov och skrevs fore verktygen: bankens 63 uppgifter "
        "(prompt, scene.components, control.signals, fysik, expect.lines, "
        "failure_modes, scenarios), personaspecens 228 arbetssteg med sin "
        "Kraver-kolumn, och de oppna punkter M-84 och M-85 skrivit ut. "
        "De oberoende VARDENA kommer ur bank/katalog_index.json, vars poster "
        "bar stampeln PUBLICERAD_SPEC = tillverkarens publicerade datablad.",
    "facitkalla_filer": (
        "bank/uppgifter",
        "bank/katalog_index.json",
        "docs/spec/48_personaprofiler.md",
        "docs/matningar/M-84_uppslagen_bytte_ordforrad_inte_radantal.md",
        "docs/matningar/M-85_komponentdatabladet.md",
    ),
    "trasiga_fall": (
        "ett svar som namnger en ANNAN symbol an den som fragades far aldrig "
        "raknas som SVAR - det ar HALVT, for verktyget sager samtidigt "
        "'anvand namnet exakt som det star'",
        "ett tal utan deklarerad enhet far aldrig raknas som SVAR",
        "ett biblioteksvarde som MOTSAGER bankens PUBLICERAD_SPEC (rackvidd "
        "0 mm for en robot vars datablad sager 901 mm) maste klassas TYST FEL, "
        "aldrig SVAR och aldrig SAKNAS",
        "en fritextsokning som ger traffar dar ingen traff bar sokordet maste "
        "klassas TYST FEL, inte SVAR",
        "en fraga som kraver ett korande VC far inte raknas i tackningens "
        "namnare - den redovisas i egen kolumn",
    ),
    "kraver": ("vc",),
    "matningar": ("M-119",),
}

import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_DIR, "kor_kunskapstackning.py"), encoding="utf-8") as _f:
    exec(compile(_f.read(), "kor_kunskapstackning.py", "exec"))
