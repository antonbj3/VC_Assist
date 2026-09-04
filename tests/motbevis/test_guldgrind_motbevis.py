# -*- coding: utf-8 -*-
"""Motbevis: en rapport som INTE MÄTT NÅGOT får guld.

Guldgrinden är det sista som står mellan en kandidat och leverans. Den läser
ögats egen dom och räknar aldrig om ett mått — det är rätt doktrin, och skälet
är mätt. Men den kontrollerar inte att det FINNS något mått.

En rapport med noll sektioner, `SAMPLES 0`, `DUR 0.000s` och raden
`EYES VERDICT PASS` ger `GOLD gold_verified_core`.

I3 i 90_invarianter.md: "Okänd klass, avhuggen rapport, obesvarad fråga: allt
är 'inte guld'. Tystnad är aldrig ett godkännande." En rapport som inte mätt
något är tystnad med ett PASS ovanpå.

Följdfelet är värre än det ser ut: kontraktets regel 5 säger att varje
`VIOLATION` i `HONESTY` tvingar `FAIL`. Regeln binder bara om sektionen är
med. Utelämnas `SECTION HONESTY` finns ingen överträdelse att hitta, och hela
ärlighetsgrinden — teleportgrepp, numerisk explosion, detalj under golvet,
aldrig gripen — försvinner tyst.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

from vc_assist_svc.guldgrind import Guldgrind          # noqa: E402

GRONA_FORGRINDAR = {"kompilering": True, "statisk_analys": True,
                    "deklarationsmatchning": True, "anropsvalidering": True}


def _cell(eyes, namn="station1"):
    return {"namn": namn, "klass": "plocka_och_placera",
            "forgrindar": dict(GRONA_FORGRINDAR), "eyes": eyes}


def _grind():
    return Guldgrind(["plocka_och_placera"])


TOM = ("EYES v1\n"
       "TEMPLATE plocka_och_placera\n"
       "RUN 2026-09-04T17:00:00 DUR 0.000s SAMPLES 0 RATE 0.00Hz\n"
       "EYES VERDICT PASS inget uppmatt\n")

UTAN_HONESTY = ("EYES v1\n"
                "TEMPLATE plocka_och_placera\n"
                "RUN 2026-09-04T17:00:00 DUR 9.500s SAMPLES 190 RATE 20.00Hz\n"
                "SECTION MOTION\n"
                "  GRIP FORMED t=0.950s dist=1.0mm\n"
                "  CARRY RIGID rot=0.0deg span=3.0s\n"
                "  PLACE IN_TARGET err=0.5mm z=0.750m\n"
                "EYES VERDICT PASS allt bra\n")


def test_en_rapport_utan_en_enda_matning_ar_inte_guld():
    b = _grind().doma([_cell(TOM)])
    assert not b.guld, (
        "en rapport med noll sektioner, SAMPLES 0 och DUR 0,000 s gav %s. "
        "Tystnad är aldrig ett godkännande (I3)." % b.text())


def test_en_rapport_utan_HONESTY_sektionen_ar_inte_guld():
    """Regel 5 i kontraktet binder bara om sektionen finns. En rapport som
    utelämnar den har inga överträdelser att hitta — och grinden som ska
    fånga teleportgrepp, explosion och detalj under golvet blir tom."""
    b = _grind().doma([_cell(UTAN_HONESTY)])
    assert not b.guld, (
        "rapporten saknar SECTION HONESTY helt och fick %s: hela "
        "ärlighetsgrinden går att koppla ur genom att inte skriva den"
        % b.text())


def test_en_korning_med_for_fa_prov_ar_inte_guld():
    """Ögat har en egen tröskel `MIN_PROV` som gör en för kort körning
    INCONCLUSIVE. Grinden bär ingen motsvarighet: kommer rapporten utifrån
    med SAMPLES 1 och PASS räcker det."""
    ett_prov = TOM.replace("SAMPLES 0", "SAMPLES 1").replace("DUR 0.000s", "DUR 0.050s")
    b = _grind().doma([_cell(ett_prov)])
    assert not b.guld, "en körning på ett enda prov gav %s" % b.text()


def test_facit_grinden_ger_fortfarande_guld_at_en_riktig_rapport():
    """Utan detta vore proven ovan värdelösa: en grind som fäller allt klarar
    varje fällningsprov."""
    sys.path.insert(0, os.path.join(_ROT, "tests"))
    import celler
    import oga_analys as A

    b, plan = celler.bra()
    text, _rapport, _analys = A.doma(b.data(), plan)
    beslut = _grind().doma([_cell(text)])
    assert beslut.guld, "den bra cellens riktiga rapport nekades guld: %s" % beslut.text()
