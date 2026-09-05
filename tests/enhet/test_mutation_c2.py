# -*- coding: utf-8 -*-
"""C2: stimulusgrinden - en stimulus som faller referensen avvisas.

C2:s bada fallor ar matta i det har projektet: ett scenario som bara faller
mutanten ar ett facit i forkla dnad (referensen maste vara gron), och grinden
far inte bli billig (nya sekvenser far aldrig fa en gammal fangst att slappa).

Proven skrevs FORE mekanismen (`kor_C2_stimuli.verifiera_stimulus`) och var
roda da - ingen grind fanns. Faller mekanismen tillbaka blir de roda igen.
"""
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "tests", "protocol")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import kor_C2_stimuli as C2                                     # noqa: E402
from bank import domare                                          # noqa: E402

REF = ("PROGRAM Mini\nVAR\n    xLatch : BOOL := FALSE;\nEND_VAR\n"
       "    xLatch := xIn AND NOT xFel;\n"
       "    xUt := xLatch;\nEND_PROGRAM\n")
MUTANT = ("PROGRAM Mini\nVAR\n    xLatch : BOOL := FALSE;\nEND_VAR\n"
          "    xLatch := xIn OR NOT xFel;\n"
          "    xUt := xLatch;\nEND_PROGRAM\n")
FANGAD_AV_GAMMAL = ("PROGRAM Mini\nVAR\n    xLatch : BOOL := FALSE;\nEND_VAR\n"
                    "    xLatch := xIn AND NOT xFel;\n"
                    "    xUt := NOT xLatch;\nEND_PROGRAM\n")

POST = {
    "task_id": "MINI",
    "control": {"signals": [
        {"name": "xIn", "type": "bool", "dir": "in"},
        {"name": "xFel", "type": "bool", "dir": "in"},
        {"name": "xUt", "type": "bool", "dir": "out"},
    ]},
    "facit_spar": {
        "harkomst": "fixtur for C2-grinden",
        "scan_ms": 20,
        "referens": REF,
        "sekvenser": [{"id": "gammal", "beskrivning": "en punkt",
                       "steg": [{"t_ms": 0,
                                 "satt": {"xIn": True, "xFel": False},
                                 "krav": {"xUt": True}}]}],
        "invarianter": [],
        "flanker": [],
        "motbevis": [],
    },
}

BRA = {"id": "ny_punkt", "beskrivning": "andra punkten ser mutanten",
       "steg": [{"t_ms": 0, "satt": {"xIn": True, "xFel": False}},
                {"t_ms": 100, "satt": {"xIn": False},
                 "krav": {"xUt": False}}]}
DARLIG = {"id": "faller_referensen", "beskrivning": "kravet motsager referensen",
          "steg": [{"t_ms": 0, "satt": {"xIn": True, "xFel": False}},
                   {"t_ms": 100, "satt": {"xIn": False},
                    "krav": {"xUt": True}}]}
BLIND = {"id": "ser_ingen", "beskrivning": "samma punkt som gamla",
         "steg": [{"t_ms": 0, "satt": {"xIn": True, "xFel": False},
                   "krav": {"xUt": True}}]}


def test_c2_bra_stimulus_slapps_igenom():
    ok, skal, _ = C2.verifiera_stimulus(POST, BRA, [MUTANT])
    assert ok, skal


def test_c2_stimulus_som_faller_referensen_avvisas():
    """C2:s trasiga fixtur: faller referensen ar det ingen stimulus utan ett
    facit i forkla dnad - mekanismen ska avvisa, inte acceptera."""
    ok, skal, _ = C2.verifiera_stimulus(POST, DARLIG, [MUTANT])
    assert not ok, "mekanismen slarppte igenom en stimulus som faller referensen"
    assert "referens" in skal


def test_c2_blind_stimulus_avvisas():
    ok, skal, _ = C2.verifiera_stimulus(POST, BLIND, [MUTANT])
    assert not ok, "mekanismen slappte igenom en stimulus som inget ser"


def test_c2_grinden_blir_aldrig_billigare():
    """Att lagga till en sekvens far aldrig fa en gammal fangst att slappa:
    domen samlar brister over alla sekvenser, sa en ny sekvens kan bara
    lagga till fall - aldrig ta bort."""
    probe = C2.med_sekvens(POST, BRA)
    d = domare.dom(probe, FANGAD_AV_GAMMAL)
    assert not d.godkand, "gammal fangst slapp igenom efter tillaggd sekvens"


FORTUNNAD = {"id": "gammal", "beskrivning": "samma id men kravet borttaget",
             "steg": [{"t_ms": 0, "satt": {"xIn": True, "xFel": False}}]}


def test_c2_ersattning_som_tunnar_ut_avvisas():
    """Samma grind for punktkrav i befintliga sekvenser: en ersatt sekvens
    som tar bort ett gammalt steg tunnar ut grinden och avvisas."""
    ok, skal, _ = C2.verifiera_stimulus(POST, FORTUNNAD, [MUTANT],
                                        ersatt_id="gammal")
    assert not ok, "mekanismen slappte igenom en sekvens som tunnar ut"
    assert "tar bort" in skal


def test_c2_krav_som_laggs_till_ar_inte_att_ta_bort():
    """Att lagga ett krav till ett befintligt steg (samma t_ms, samma satt,
    fler krav) tunnar inte ut - det skärper. Bara borttagna steg avvisas."""
    gammalt = [{"t_ms": 0, "satt": {"xIn": True},
                "krav": {"xUt": True}}]
    assert C2.steg_borttagna(gammalt, gammalt) == []
    skarpt = [{"t_ms": 0, "satt": {"xIn": True},
               "krav": {"xUt": True, "xFel": False}}]
    assert C2.steg_borttagna(gammalt, skarpt) == []
    tunt = [{"t_ms": 0, "satt": {"xIn": True}}]
    assert len(C2.steg_borttagna(gammalt, tunt)) == 1


def test_c2_invariant_som_faller_referensen_avvisas():
    """Samma grind for invarianter: en invariant som referensen bryter ar
    inget skydd utan ett facit i forkla dnad."""
    dålig_inv = [{"namn": "x", "sekvens": "*", "nar": {"xIn": True},
                  "kraver": {"xUt": False}, "varfor": "y"}]
    ok, skal, _ = C2.verifiera_stimulus(POST, BRA, [MUTANT],
                                        extra_invarianter=dålig_inv)
    assert not ok and "referens" in skal
