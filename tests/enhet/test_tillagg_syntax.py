# -*- coding: utf-8 -*-
"""L0: tillagget maste GA ATT LADDA. Kors utan VC.

Bakgrund: VC svalde ett syntaxfel i kommandomodulen HELT. loadCommand gav ett
anvandbart objekt, execute() rapporterade lyckat, och modulen kordes aldrig -
noll rader i loggen (M-09). En trasig trippelcitering inne i skriptmallen
rackte. Den sortens fel far aldrig upptackas genom att stirra i en logg.
"""
import ast
import glob
import os
import re

import pytest

_TILLAGG = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "ext", "vc_addon", "vc_assist"))
_FILER = sorted(glob.glob(os.path.join(_TILLAGG, "*.py")))


def test_det_finns_filer_att_prova():
    assert _FILER, "hittade inga tillaggsfiler i %s" % _TILLAGG


@pytest.mark.parametrize("sokvag", _FILER, ids=[os.path.basename(f) for f in _FILER])
def test_varje_tillaggsfil_parsar(sokvag):
    with open(sokvag) as f:
        ast.parse(f.read(), filename=sokvag)


def test_skriptmallen_parsar_efter_formatering():
    """Mallen ar en strang i en strang. Den maste provas FORMATERAD."""
    with open(os.path.join(_TILLAGG, "bridge_cmd.py")) as f:
        kalla = f.read()
    m = re.search(r'SKRIPT = """(.*?)"""', kalla, re.S)
    assert m, "hittade ingen SKRIPT-mall i bridge_cmd.py"
    ut = m.group(1) % {"dir": "C:\\\\nagon\\\\mapp", "port": 8901}
    ast.parse(ut, filename="SKRIPT")


def test_skriptmallen_borjar_med_vcScript_importen():
    """Utan den raden finns varken delay() eller getSimulation(), och OnRun
    dor tyst (M-06)."""
    with open(os.path.join(_TILLAGG, "bridge_cmd.py")) as f:
        m = re.search(r'SKRIPT = """(.*?)"""', f.read(), re.S)
    assert m.group(1).lstrip().startswith("from vcScript import *")


def test_ingen_tillaggsfil_anvander_unicode_literals_mot_vc():
    """unicode_literals + VC:s py2-bindning ger SystemError vid varje
    strangskrivning (M-05). Filer som skriver TILL VC maste ha _s()."""
    for sokvag in _FILER:
        with open(sokvag) as f:
            kalla = f.read()
        if "unicode_literals" in kalla and ".Name = " in kalla:
            assert "def _s(" in kalla, (
                "%s har unicode_literals och skriver till VC utan _s()"
                % os.path.basename(sokvag))
