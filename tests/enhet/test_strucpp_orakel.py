# -*- coding: utf-8 -*-
"""L1 for STruC++-oraklet. Ingen kompilator, ingen binar.

Oraklet ar det ANDRA ogat pa ST-semantiken (M-54). Modulen hade fram till nu
bara en L3-korning som prov, alltsa ingenting som gar att kontrollera pa en ren
maskin. Det som provas har ar tolkningen av orakelts utdata - den delen som gor
en avvikelse till en avvikelse.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import strucpp_orakel as O                  # noqa: E402


def orakel():
    return O.Orakel("/finns/inte/p", "PRESS", 20.0)


def svar(*rader):
    return "\n".join(rader) + "\n"


# ---- vardetolkningen -------------------------------------------------------

@pytest.mark.parametrize("text,vantat", [
    ("TRUE", True), ("FALSE", False), ("true", True),
    ("42", 42), ("-7", -7), ("2.5", 2.5), ("1e3", 1000.0),
    ("nagot", "nagot"),
])
def test_varden_tolkas_efter_sin_form(text, vantat):
    assert O._bool_ur(text) == vantat


@pytest.mark.parametrize("varde,vantat", [
    (True, "TRUE"), (False, "FALSE"), (3, "3"), (2.5, "2.5"),
])
def test_varden_skrivs_som_REPL_en_forstar(varde, vantat):
    assert O._till_repl(varde) == vantat


def test_bool_skrivs_som_bool_och_inte_som_1():
    """True ar 1 i Python. REPL:en vill ha TRUE, och den skillnaden ar tyst."""
    assert O._till_repl(True) == "TRUE"
    assert O._till_repl(1) == "1"


# ---- plockningen ur orakelts utdata ---------------------------------------

def test_plockar_ett_svar_per_steg():
    spar = [O.Steg({"i": True}, 1, ("q",)), O.Steg({}, 2, ("q",))]
    ut = orakel()._plocka(svar(
        "PRESS.I = TRUE",
        "Executed 1 cycle(s). Total: 1",
        "PRESS.Q : BOOL = FALSE",
        "Executed 2 cycle(s). Total: 3",
        "PRESS.Q : BOOL = TRUE",
    ), spar)
    assert ut == [{"Q": False}, {"Q": True}]


def test_ett_steg_som_saknar_sitt_svar_FALLS(orakelspar=None):
    """Ett orakel som tiger far aldrig se ut som ett orakel som holl med."""
    spar = [O.Steg({}, 1, ("q", "et"))]
    with pytest.raises(O.Orakelfel) as e:
        orakel()._plocka(svar("Executed 1 cycle(s). Total: 1",
                              "PRESS.Q : BOOL = TRUE"), spar)
    assert "did not answer" in str(e.value) and "ET" in str(e.value)


def test_fel_antal_korningar_FALLS():
    spar = [O.Steg({}, 1, ("q",)), O.Steg({}, 1, ("q",))]
    with pytest.raises(O.Orakelfel) as e:
        orakel()._plocka(svar("Executed 1 cycle(s). Total: 1",
                              "PRESS.Q : BOOL = TRUE"), spar)
    assert "2 steps" in str(e.value) and "ran 1" in str(e.value)


def test_okand_variabel_FALLS_i_stallet_for_att_tigas_bort():
    """REPL:en svarar 'Unknown variable' och fortsatter glatt. Vi far inte."""
    spar = [O.Steg({}, 1, ("q",))]
    with pytest.raises(O.Orakelfel) as e:
        orakel()._plocka(svar("Unknown variable: q in PRESS",
                              "Executed 1 cycle(s). Total: 1"), spar)
    assert "did not recognize" in str(e.value)


# ---- skillnadsregeln -------------------------------------------------------

@pytest.mark.parametrize("a,b,skiljer", [
    (True, True, False), (True, False, True),
    (1, 1.0, False), (1, 2, True),
    (0.1 + 0.2, 0.3, False),
    ("x", "x", False), ("x", "y", True),
    (True, 1, False),
])
def test_skillnadsregeln(a, b, skiljer):
    assert O._skiljer(a, b) is skiljer


def test_bool_mot_tal_jamfors_som_bool():
    """Annars hade TRUE mot 1 sett ut som en avvikelse i varje boolskt steg."""
    assert O._skiljer(True, 1) is False
    assert O._skiljer(False, 0) is False
    assert O._skiljer(True, 0) is True


# ---- avvikelsen bar sin egen text -----------------------------------------

def test_avvikelsen_sager_steg_namn_och_bada_svaren():
    a = O.Avvikelse(3, "q", True, False)
    t = str(a)
    assert "steg 3" in t and "q" in t and "tolken" in t and "oraklet" in t


# ---- byggandet faller nar det ska -----------------------------------------

def test_saknad_kompilator_falls_med_sokvagen():
    with pytest.raises(O.Orakelfel) as e:
        O.Orakel.bygg("PROGRAM P\nVAR\nEND_VAR\nEND_PROGRAM\n", "P",
                      "/finns/verkligen/inte")
    assert "/finns/verkligen/inte" in str(e.value)


def test_cykelraden_lases_ur_orakelts_egen_start():
    """Perioden ANTAS aldrig - den lases, och jamfors sedan mot tolkens."""
    assert O._CYKELRAD.search("Cycle: 20ms").group(1) == "20"
    assert O._CYKELRAD.search("  Cycle:  5 ms ").group(1) == "5"
    assert O._CYKELRAD.search("ingen cykel har") is None
