# -*- coding: utf-8 -*-
"""D8: Enhetsprov för domarnas oenighet och oberoende.

Bevisar satsen i D8 (docs/uppdrag/KO_D_ogat_och_scenen.md):
"Två domare som alltid säger samma sak är en domare."

Provet verifierar att:
1. Samtliga fem domare (sekvens, timing, grepp, kollision, genomflode)
   uppvisar oenighet mot varandra.
2. Inget domarpar har 0 % oenighet.
3. Varje domare fäller unika fel som ingen annan domare fäller.
"""
from __future__ import annotations

import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in [_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "tests"),
          os.path.join(_ROT, "tests", "protocol"),
          os.path.join(_ROT, "ext", "vc_addon", "vc_assist")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import kor_D8_domarna_oense as D8
import oga_analys as A


def test_d8_inga_tva_domare_ar_identiska():
    """Alla 10 domarpar ska ha oenighet > 0 % över spåren."""
    spar = D8.samla_alla_spar()
    res = D8.analysera_spar(spar)
    par_matris = res["par_matris"]

    assert len(par_matris) == 10, "Det ska finnas exakt 10 par bland 5 domare"

    for nyckel, par in par_matris.items():
        assert par["aktiva"] >= 6, f"För få aktiva jämförelser för {nyckel}"
        assert par["oense"] > 0, f"Domarna {par['d1']} och {par['d2']} är identiska (0 % oense)!"
        assert par["oense_pct"] >= 20.0, f"Oenighetsgraden för {nyckel} är onormalt låg: {par['oense_pct']}%"
        assert par["d1_fail_d2_inte"] > 0, f"{par['d1']} fäller aldrig ensam mot {par['d2']}"
        assert par["d2_fail_d1_inte"] > 0, f"{par['d2']} fäller aldrig ensam mot {par['d1']}"


def test_d8_fullspektrum_isolering():
    """I en fullspektrum-cell ska varje felklass fällas av EXAKT sin domare."""
    for fel in ["sekvens", "timing", "grepp", "kollision", "genomflode"]:
        d, p = D8.bygg_integrerad_scen(fel)
        _, rap, an = A.doma(d, p)
        domar = an.harledt["domar"]

        assert rap.dom[0] == "FAIL", f"Felfall {fel} gav inte global FAIL"
        # Den avsedda domaren ska fälla
        assert domar[fel]["utfall"] == "FAIL", f"Domare {fel} fällde inte sitt eget fel"

        # Övriga domare ska ge PASS
        for annan in D8.DOMAR_NAMN:
            if annan != fel:
                assert domar[annan]["utfall"] == "PASS", (
                    f"Domare {annan} fällde ovidkommande fel {fel} (utfall: {domar[annan]['utfall']})"
                )


def test_d8_fullspektrum_hel():
    """En hel fullspektrum-cell ska få PASS från ALLA fem domarna."""
    d, p = D8.bygg_integrerad_scen(None)
    _, rap, an = A.doma(d, p)
    domar = an.harledt["domar"]

    assert rap.dom[0] == "PASS"
    for namn in D8.DOMAR_NAMN:
        assert domar[namn]["utfall"] == "PASS", f"Domare {namn} gav inte PASS på frisk cell"
