# -*- coding: utf-8 -*-
"""Enhetsprov för kor_C7_f15_niva.py och dess trasiga fixturer."""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), _ROT, os.path.join(_ROT, "tests", "protocol")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import kor_C7_f15_niva as C7


def test_c7_kategorisera_signal():
    assert C7.kategorisera_signal("SYS_RESET") == "aterstallning"
    assert C7.kategorisera_signal("trigReset.CLK") == "aterstallning"
    assert C7.kategorisera_signal("ST490_XFR_DONE") == "handskakning"
    assert C7.kategorisera_signal("ST190_PEC_PART") == "material_process"


def test_c7_bankens_f15_tackning():
    bank = C7._uppgifter()
    kat_data = C7.utvardera_f15(bank)
    at_poster = kat_data["aterstallning"]
    at_fangade = sum(1 for x in at_poster if not x["godkand"])
    # Återställningar ska fångas till minst 90 % (här 100 %)
    assert len(at_poster) >= 15
    assert at_fangade / len(at_poster) >= 0.90
    # Handskakning: minst 3 fångade (H-05, S-07 osv)
    hs_poster = kat_data["handskakning"]
    hs_fangade = sum(1 for x in hs_poster if not x["godkand"])
    assert hs_fangade >= 3
