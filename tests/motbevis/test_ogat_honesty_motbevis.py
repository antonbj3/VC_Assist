# -*- coding: utf-8 -*-
"""Motbevis: ögats grindar täcker för varandra, så en död grind syns inte.

`tests/celler.py` säger om sig själv: *"Varje trasig cell isolerar EN felklass,
så en fällning går att härleda till sin orsak."* För två celler stämmer det
inte, och det får en mätbar följd.

Mätt med mutation över hela sviten (838 tester):

    oga_analys.py:438  overtradelse = True -> False   (BLOWUP)         ÖVERLEVER
    oga_analys.py:455  overtradelse = True -> False   (NEVER_GRIPPED)  ÖVERLEVER
    oga_analys.py:428  overtradelse = True -> False   (TELEPORT)       dödas

Skälet är att `explosion` också hamnar 94 000 mm fel, och `aldrig_gripen`
också saknar grepp. Cellerna faller på en annan grind, raden `BLOWUP
VIOLATION` skrivs ändå ut, och FACIT-provet som letar efter raden är nöjt.
Två av ögats fyra hederlighetsgrindar kan alltså stängas av utan att ett
enda test märker det.

Några prov här är GRÖNA. De är de saknade proven — hål som mätningen fann men
som koden faktiskt klarar när någon väl frågar. De hör hemma i `tests/enhet/`.
"""
import ast
import os
import sys
import types

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests"))

import celler                 # noqa: E402
import oga_analys as A        # noqa: E402
import oga_kontrakt as K      # noqa: E402


def _rapport(data, plan, modul=A):
    _text, rapport, _analys = modul.doma(data, plan)
    return rapport


# ---- 1. cellerna isolerar inte sin felklass ----------------------------


def test_greppgrinden_och_never_gripped_ar_inte_samma_grind():
    """`aldrig_gripen` fälls både av `mh["grip"] is None` (rad 517) och av
    NEVER_GRIPPED (rad 455). Den ena döljer att den andra är död."""
    b, plan = celler.aldrig_gripen()
    _t, _r, analys = A.doma(b.data(), plan)
    h = analys.harledt
    saknar_grepp = h["motion"].get("grip") is None
    honesty = h["honesty"].get("overtradelse")
    assert not (saknar_grepp and honesty), (
        "samma cell fälls av två oberoende grindar samtidigt; ingen av dem "
        "har ett prov där den är den enda som kan fälla")

