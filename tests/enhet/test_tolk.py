# -*- coding: utf-8 -*-
"""L1 for ST-tolken (svc/vc_assist_svc/st/tolk.py).

Bankens facit doms av tolken. En tolk som har fel om ST-semantiken ger ett
facit som har fel, och da mater banken var egen missuppfattning med stor
precision. Proven har halls darfor mot den ANDRA motorn - STruC++:s byggda
REPL - och deras gemensamma dom star i docs/matningar/M-54.

Kors utan VC, utan OpenPLC och utan kompilator.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import tolk as T                          # noqa: E402


# ---- M-54: okanda ingangar till ett standardblock ------------------------

def test_ett_okant_argument_till_ett_funktionsblock_avvisas():
    """Ett argument som ingen laser ar ett tyst bortfall mitt i facit.

    MATT i M-54: `c(CU := i, RESET := r, PV := 3)` gick rakt igenom tolken, som
    laser nollstallningen ur "R". Reset foll alltsa tyst bort och raknaren
    raknade vidare - och bankens facit hade domt pa den semantiken.

    Samma kod oversatts av STruC++ med utgangskod 0 och texten
    "Compilation successful!", men gar INTE att bygga:
    `class strucpp::CTU has no member named RESET`. Ingen runtime har den
    semantik tolken visade.
    """
    kalla = ("PROGRAM P\nVAR\n i : BOOL;\n r : BOOL;\n n : INT;\n"
             " c : CTU;\nEND_VAR\n"
             "    c(CU := i, RESET := r, PV := 3);\n    n := c.CV;\n"
             "END_PROGRAM\n")
    with pytest.raises(T.Tolkfel) as e:
        tolk = T.Tolk(kalla)
        tolk.satt("i", True)
        tolk.scan()
    assert "RESET" in str(e.value)
    assert "CU, R, PV" in str(e.value)


def test_det_ratta_namnet_gar_igenom_och_nollstaller():
    """Kontrollen far inte vara sa bred att den avvisar det ratta namnet."""
    kalla = ("PROGRAM P\nVAR\n i : BOOL;\n r : BOOL;\n n : INT;\n"
             " c : CTU;\nEND_VAR\n"
             "    c(CU := i, R := r, PV := 3);\n    n := c.CV;\n"
             "END_PROGRAM\n")
    tolk = T.Tolk(kalla)
    for _ in range(2):
        tolk.satt("i", True)
        tolk.scan()
        tolk.satt("i", False)
        tolk.scan()
    assert tolk.las("n") == 2
    tolk.satt("r", True)
    tolk.scan()
    assert tolk.las("n") == 0
