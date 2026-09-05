# -*- coding: utf-8 -*-
"""C3: mutationspoängen som grind med golv (M-53-mönster).

Kvot fångade / skador blir en grind med ett golv som bara får gå UPPÅT.
Golvet sätts till det uppmätta värdet (M-147: 1174 / 1307 = 89,824 %),
aldrig till ett runt tal.

PROVEN SKREVS FÖRE MEKANISMEN och var röda då:
- mekanismen fanns inte
- ett sänkt värde fälls
- ett för slappt golv fälls
- ett avrundat golv fälls
"""
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), _ROT, os.path.join(_ROT, "tests", "protocol")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from kor_m122_mutationsskikt import (  # noqa: E402
    GOLV_FANGSTGRAD,
    GOLV_SKADOR,
    GOLV_FANGADE,
    GOLV_PER_SORT,
    validera_mutationsgolv,
)

RADATA_JSON = os.path.join(_ROT, "docs", "matningar", "radata", "m147_svep.json")


# ---- trasiga fixturer: grinden måste fälla det som inte håller ----------------

def test_c3_ett_sankt_resultat_falls():
    """Trasig fixtur: en körning med en fångst mindre än golvet ska avvisas."""
    ok, fel = validera_mutationsgolv(GOLV_FANGADE - 1, GOLV_SKADOR)
    assert not ok
    assert "under golvet" in fel


def test_c3_slappare_golv_falls():
    """Ett golv under verkligheten slutar fånga nästa glidning (samma regel
    som M-53 och M-70)."""
    assert GOLV_FANGADE / GOLV_SKADOR == GOLV_FANGSTGRAD
    assert GOLV_FANGADE == 1174
    assert GOLV_SKADOR == 1307


def test_c3_golvet_ar_aldrig_ett_runt_tal():
    """Regel i KO_C: 'Golvet sätts till det uppmätta värdet, aldrig till ett
    runt tal.' Runda tal är gissningar som ser ut som kunskap."""
    assert (GOLV_FANGSTGRAD * 100) % 1 != 0, "golvet är ett runt procenttal: %r" % GOLV_FANGSTGRAD
    assert (GOLV_FANGSTGRAD * 1000) % 1 != 0


def test_c3_sort_under_golv_falls():
    """Om en enskild sort backar ska grinden fälla även om totalen håller."""
    per_sort = dict(GOLV_PER_SORT)
    # Sänk AND_TILL_OR med en fångad
    sort_test = "AND_TILL_OR"
    fangade, n = per_sort[sort_test]
    per_sort[sort_test] = (fangade - 1, n)
    ok, fel = validera_mutationsgolv(GOLV_FANGADE, GOLV_SKADOR, per_sort=per_sort)
    assert not ok
    assert sort_test in fel


# ---- grinden mot det verkliga mätresultatet på disk ---------------------------

def test_c3_diskdata_uppfyller_golvet():
    """Det faktiskt uppmätta svepet i radata måste klara grinden."""
    assert os.path.exists(RADATA_JSON), "radata saknas: %s" % RADATA_JSON
    with open(RADATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    rader = [r for u in data["uppgifter"] for r in u["rader"]]
    fangade = sum(1 for r in rader if r["utfall"] == "FANGAD")
    totalt = len(rader)
    ok, fel = validera_mutationsgolv(fangade, totalt)
    assert ok, fel
    assert fangade == GOLV_FANGADE
    assert totalt == GOLV_SKADOR


def test_c3_diskdata_uppfyller_varje_sortgolv():
    """Varje enskild sorts fångstgrad på disk uppfyller sitt sortgolv."""
    with open(RADATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    rader = [r for u in data["uppgifter"] for r in u["rader"]]
    per_sort = {}
    for sort in set(r["sort"] for r in rader):
        rs = [r for r in rader if r["sort"] == sort]
        fang = sum(1 for r in rs if r["utfall"] == "FANGAD")
        per_sort[sort] = (fang, len(rs))
    ok, fel = validera_mutationsgolv(len([r for r in rader if r["utfall"] == "FANGAD"]),
                                     len(rader), per_sort=per_sort)
    assert ok, fel


def test_c3_troskeln_har_matningsreferens():
    """Regel S6: ingen tröskel utan mätreferens. Källkoden för kor_m122_mutationsskikt
    måste ange mätningen som golvet härrör från."""
    kalla = open(os.path.join(_ROT, "tests", "protocol", "kor_m122_mutationsskikt.py"),
                 encoding="utf-8").read()
    assert "M-147" in kalla, "kor_m122_mutationsskikt.py saknar mätreferens till M-147"
