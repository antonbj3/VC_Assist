# -*- coding: utf-8 -*-
"""L1: Verifiering av reparationerna i E3 (M-119).

Provar:
  E3a: nollan som ser ut som en matning (None blir aldrig 0)
  E3b: grindreglerna ur docs/spec/41_ogat_kontrakt.md nas vid uppslag
  E3c: bench_task bar control, fysik, facit_spar m.fl. och search_catalog hittar signaler
  E3d: konstanter (t.ex. VC_BOOLEANSIGNAL) bar beskrivning
  E3e: delstrang_namn kraver ordgrans, RACE ger inte traceOn som delstrang_namn
  6: arvd medlem (t.ex. vcComponent.findBehavioursByType) namnger fragad typ och arvd harkomst
"""
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import api_index as AI
from vc_assist_svc import katalogindex as KI
from vc_assist_svc import komponentdatablad as KD
from vc_assist_svc import verktyg as V


@pytest.fixture(scope="module")
def index():
    return AI.bygg_index()


def test_e3a_noll_blir_none():
    """E3a: Saknat / noll far aldrig tolkas som ett giltigt matt."""
    assert KI._tal("0") is None
    assert KI._tal("0.0") is None
    assert KI._tal(0) is None
    assert KI._tal(None) is None
    assert KD._tal("0") is None
    assert KD._tal(0.0) is None


def test_e3b_grindregler_ur_spec_nas(index):
    """E3b: RACE och MINDIST hittas i docs/spec/41_ogat_kontrakt.md."""
    race_traffar = index.sok("RACE")
    assert race_traffar, "RACE maste ge traff"
    basta_race = race_traffar[0]
    assert basta_race.symbol.namn == "RACE"
    assert basta_race.symbol.sort == "grindregel"
    assert "41_ogat_kontrakt.md" in basta_race.symbol.kalla

    mindist_traffar = index.sok("MINDIST")
    assert mindist_traffar, "MINDIST maste ge traff"
    basta_mindist = mindist_traffar[0]
    assert basta_mindist.symbol.namn == "MINDIST"
    assert basta_mindist.symbol.sort == "grindregel"


def test_e3c_bench_task_bar_alla_falt():
    """E3c: bench_task utelamnar inte control, fysik eller facit_spar."""
    res = V.DATA_HANDLERS["bench_task"]({"task_id": "A-01"})
    assert res["found"] is True
    assert "control" in res and res["control"] is not None
    assert "signals" in res["control"]
    assert "fysik" in res and res["fysik"] is not None
    assert "facit_spar" in res
    assert "antaganden" in res["uppgift"] or "antaganden" in res


def test_e3c_search_catalog_hittar_signaler():
    """E3c: Signaler ur bankens control.signals kan sokas upp via search_catalog."""
    res = V.DATA_HANDLERS["search_catalog"]({"query": "ST230_CLP_CLOSE"})
    assert res["antal"] > 0
    traff_namn = [t["namn"] for t in res["traffar"]]
    assert "ST230_CLP_CLOSE" in traff_namn


def test_e3d_konstanter_har_beskrivning(index):
    """E3d: Konstanter far inte sakna beskrivning."""
    syms = index.slag_upp("VC_BOOLEANSIGNAL")
    assert syms, "VC_BOOLEANSIGNAL maste finnas"
    konst = syms[0]
    assert konst.beskrivning, "VC_BOOLEANSIGNAL maste ha en beskrivning"
    assert "signal" in konst.beskrivning.lower()

    # Kontrollera att lookup_api returnerar beskrivningen
    res = V.DATA_HANDLERS["lookup_api"]({"name": "VC_BOOLEANSIGNAL"})
    assert res["found"] is True
    assert res["symbols"][0]["description"] != ""


def test_e3e_delstrang_namn_kraver_ordgrans(index):
    """E3e: RACE far inte ge traceOn som delstrang_namn."""
    traffar = index.sok("RACE")
    for t in traffar:
        if t.symbol.namn == "traceOn":
            assert t.rang != "delstrang_namn", "traceOn far inte ges rang delstrang_namn for RACE"


def test_e3_arvd_medlem_namnger_efterfragad_typ():
    """6:e punkten: vcComponent.findBehavioursByType namnger vcComponent."""
    res = V.DATA_HANDLERS["lookup_api"]({"name": "vcComponent.findBehavioursByType"})
    assert res["found"] is True
    s = res["symbols"][0]
    assert s["full_name"] == "vcComponent.findBehavioursByType"
    assert "arvd fran" in s["harkomst"]
    assert "vcNode" in s["harkomst"]
    assert "Anvand namnet exakt som det star" in res["instruktion"]
