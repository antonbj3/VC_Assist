# -*- coding: utf-8 -*-
"""L0: varje troskel bar sin harkomst.

41_ogat_kontrakt.md: "En troskel utan hanvisning ar ett linterfel."
Kallprojektets scene_eyes har fyra tal utan motivering; det ar dess enda
kanda svaghet och den upprepas inte har.
"""
import os
import re

import pytest

_TILLAGG = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "ext", "vc_addon", "vc_assist"))

# Modul -> konstanter som ar TROSKLAR (tal som styr en dom).
MODULER = ["oga_analys.py"]

_KONSTANT = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)\s*(#.*)?$")


def _trosklar(modul):
    ut = []
    with open(os.path.join(_TILLAGG, modul)) as f:
        for nr, rad in enumerate(f, 1):
            m = _KONSTANT.match(rad.rstrip("\n"))
            if m:
                ut.append((nr, m.group(1), m.group(2), (m.group(3) or "").strip()))
    return ut


@pytest.mark.parametrize("modul", MODULER)
def test_det_finns_trosklar_att_prova(modul):
    assert _trosklar(modul), "hittade inga troskelkonstanter i %s" % modul


@pytest.mark.parametrize("modul", MODULER)
def test_varje_troskel_namner_matningen_som_satte_den(modul):
    utan = []
    for nr, namn, _varde, kommentar in _trosklar(modul):
        harkomst = ("PRELIMINAR" in kommentar.upper()
                    or re.search(r"\bM-\d+\b", kommentar))
        if not harkomst:
            utan.append("%s:%d %s  %r" % (modul, nr, namn, kommentar))
    assert not utan, ("trosklar utan harkomst:\n  " + "\n  ".join(utan))


@pytest.mark.parametrize("modul", MODULER)
def test_en_preliminar_troskel_namner_vilken_matning_som_ska_satta_den(modul):
    """PRELIMINAR utan adress ar ingen harkomst, bara en ursakt."""
    utan = []
    for nr, namn, _varde, kommentar in _trosklar(modul):
        if "PRELIMINAR" in kommentar.upper() and not re.search(r"\bM-\d+\b", kommentar):
            utan.append("%s:%d %s" % (modul, nr, namn))
    assert not utan, ("preliminara trosklar utan utpekad matning:\n  "
                      + "\n  ".join(utan))
