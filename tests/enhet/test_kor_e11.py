# -*- coding: utf-8 -*-
"""L1/L2: Enhetsprov for E11 / M-141 - Kontextbudgeten mot verkligheten."""
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol"))

import kor_E11_kontextbudget as E11


def test_systemprompt_mater_over_1500_tokens():
    res = E11.mat_systemprompt()
    assert res["totalt_tokens_4b"] >= 1500, "Systemprompten med forhandsregler ar minst 1500 tokens"
    assert res["kritisk_grans_tokens"] >= 30000, "Kritisk grans for 5 % budget ar over 30k tokens"


def test_8k_budget_overskrids_kraftigt():
    res = E11.mat_systemprompt()
    b8k = [b for b in res["budget_analys"] if b["kontext_tokens"] == 8192][0]
    assert not b8k["rymmer"], "8k-fonstret maste overskridas"
    assert b8k["belastning_procent"] > 300.0, "8k-fonstret belastas med >300 %"
