# -*- coding: utf-8 -*-
"""L1/L2: Enhetsprov for E4 / M-136 - LLM-informationstackning i skala."""
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol"))

import kor_E4_llm_tackning as E4


def test_e4_laddar_minst_50_uppgifter():
    uppg = E4.ladda_uppgifter()
    assert len(uppg) >= 50, "Minst 50 bankuppgifter kravs for skalmatningen"


def test_e4_pseudo_simulering_ger_hog_tackning():
    uppg = E4.ladda_uppgifter()[:10]  # stickprov pa 10 uppgifter
    res = E4.kor_pseudo_simulering(uppg)
    assert res["antal_uppgifter"] == 10
    assert res["tackningsgrad_procent"] >= 95.0
    assert res["saknas_varde_antal"] == 5
    assert res["distinkta_symboler_bredd"] > 20
