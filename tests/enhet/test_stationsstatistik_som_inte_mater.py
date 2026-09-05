# -*- coding: utf-8 -*-
"""L1: en stationsstatistik som INTE MATER far inte ge PASS (M-88 §5).

DEN TRASIGA FIXTUREN ar tagen rakt ur VC. M-88 byggde cellen `station_svalt`
i en korande VC: en komponent med ett vcStatistics-beteende som ingen produkt
nagonsin nar, och kravet "hogst 1,0 s svalt". Genomflodesdomaren svarade
PASS. VC:s statistik pa en komponent utan process rapporterar korningen
igenom exakt

    {'blocked_pct': 0.0, 'broken_pct': 0.0, 'busy_pct': 0.0, 'cur': 0,
     'idle_pct': 0.0, 'in': 0, 'out': 0, 'state': ''}

och `_ar_svulten` tog den tomma strangen som ett tillstandsnamn - ett som
inte ar IDLE - och svarade aldrig svalt. Stationen var svulten i sex
sekunder och ogat sa att allt var inom marginal.

Regeln nu: en station vars statistik aldrig visat ett tillstand, aldrig
raknat en produkt och aldrig haft en procent over noll har inte MATTS. Den
ar obestambar, och ett deklarerat krav mot den ar obesvarat (M-74:s regel),
inte uppfyllt.
"""
import os
import sys

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "tests")))

import celler                                                   # noqa: E402
import oga_analys as A                                          # noqa: E402
import oga_harledning as H                                      # noqa: E402

# Raden VC gav, ordagrant (M-88, kor_fas15_domarna.py, 2026-09-05 08:30).
VC_INERT = {"blocked_pct": 0.0, "broken_pct": 0.0, "busy_pct": 0.0, "cur": 0,
            "idle_pct": 0.0, "in": 0, "out": 0, "state": ""}


def _cell_med_stat(stat, n=120):
    b = celler._grundcell("station_statistik")
    for r in b.rader[:n]:
        r["stat"] = {"F15D_station/stat": dict(stat)}
    return b


def test_den_inerta_statistiken_ur_VC_ger_INCONCLUSIVE_inte_PASS():
    b = _cell_med_stat(VC_INERT)
    plan = celler.plan(genomstromning={"max_svalt_s": 1.0})
    _text, rapport, a = A.doma(b.data(), plan)
    assert a.harledt["domar"]["genomflode"]["utfall"] == "INCONCLUSIVE"
    assert rapport.dom[0] == "INCONCLUSIVE"
    assert "ingen station provades" in rapport.dom[1]


def test_stationslage_sager_att_statistiken_inte_mater():
    b = _cell_med_stat(VC_INERT)
    h = H.stationslage(b.rader)
    d = h["F15D_station/stat"]
    assert "svalt_s" not in d
    assert "obestambar" in d and "mater inte" in d["obestambar"]


def test_ett_tomt_tillstandsnamn_ar_okant_inte_upptaget():
    """Nar statistiken MATER (procenten ror sig) men tillstandet saknar namn
    ska svalten avgoras pa procenten och innehallet - inte pa att '' inte
    ar 'IDLE'."""
    s = dict(VC_INERT, idle_pct=100.0)
    assert H._ar_svulten(s) is True
    s2 = dict(VC_INERT, idle_pct=100.0, cur=1)
    assert H._ar_svulten(s2) is False


def test_en_station_som_satts_IDLE_ar_svulten_och_falls():
    """Den andra varianten i VC: processen satte tillstandet till IDLE. Da
    mater statistiken, stationen ar ledig och tom, och kravet faller den."""
    b = _cell_med_stat(dict(VC_INERT, state="IDLE"))
    plan = celler.plan(genomstromning={"max_svalt_s": 1.0})
    _text, rapport, a = A.doma(b.data(), plan)
    assert a.harledt["domar"]["genomflode"]["utfall"] == "FAIL"
    assert rapport.dom[0] == "FAIL" and rapport.dom[1].startswith("genomflode:")


def test_samma_IDLE_serie_med_ett_krav_den_haller_ar_PASS():
    b = _cell_med_stat(dict(VC_INERT, state="IDLE"))
    plan = celler.plan(genomstromning={"max_svalt_s": 100.0})
    _text, rapport, a = A.doma(b.data(), plan)
    assert a.harledt["domar"]["genomflode"]["utfall"] == "PASS"


def test_en_statistik_som_borjar_mata_mitt_i_ar_matt():
    """Bara en serie dar INGEN rad mater ar obestambar. Borjar tillstandet
    komma efter halva korningen ar stationen matt fran och med da."""
    b = _cell_med_stat(VC_INERT)
    for r in b.rader[60:120]:
        r["stat"]["F15D_station/stat"]["state"] = "IDLE"
    h = H.stationslage(b.rader)
    d = h["F15D_station/stat"]
    assert "svalt_s" in d and d["svalt_s"] > 1.0
