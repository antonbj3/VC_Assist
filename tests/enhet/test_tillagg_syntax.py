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


def _skriptmallen():
    """SKRIPT:s VERKLIGA varde, hamtat via ast.

    En regex over filtexten ger fel svar: SKRIPT ar en vanlig trippelciterad
    strang, sa ett \\n i kallan blir en RIKTIG radbrytning nar modulen laddas.
    Ett test som lade texten rakt genom compile() sag tva tecken dar VC sag en
    radbrytning - gront test, trasig verklighet. Det ar precis den falska
    framgang hela projektet ar byggt for att undvika.
    """
    with open(os.path.join(_TILLAGG, "bridge_cmd.py")) as f:
        trad = ast.parse(f.read())
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Assign):
            for m in nod.targets:
                if isinstance(m, ast.Name) and m.id == "SKRIPT":
                    return ast.literal_eval(nod.value)
    raise AssertionError("hittade ingen SKRIPT-tilldelning i bridge_cmd.py")


def test_skriptmallen_parsar_efter_formatering():
    """Mallen ar en strang i en strang. Den maste provas FORMATERAD."""
    ut = _skriptmallen() % {"dir": "C:\\\\nagon\\\\mapp", "port": 8901}
    ast.parse(ut, filename="SKRIPT")


def test_skriptmallen_kompilerar_som_VC_kompilerar_den():
    """compile() pa mallens verkliga varde - samma grind som VC anvander."""
    ut = _skriptmallen() % {"dir": "C:\\\\m", "port": 8901}
    compile(ut, "<SKRIPT>", "exec")


def test_ingen_strangliteral_i_mallen_bryts_av_en_radbrytning():
    """Det konkreta felet: \\n i kallan blev en riktig radbrytning i mallen."""
    for nr, rad in enumerate(_skriptmallen().splitlines(), 1):
        apostrofer = rad.count("'") - rad.count("\\'")
        assert apostrofer % 2 == 0, \
            "rad %d i mallen har udda antal apostrofer: %r" % (nr, rad)


def test_uppstarten_kompilerar_skriptet_innan_det_satts():
    """Grinden ska finnas i KODEN, inte bara i testet - VC:s tystnad drabbar
    operatorens maskin, dar inga tester kors."""
    with open(os.path.join(_TILLAGG, "bridge_cmd.py")) as f:
        kalla = f.read()
    assert 'compile(kalla, "<vc_assist_pump>", "exec")' in kalla
    assert "GAR INTE ATT KOMPILERA" in kalla


def test_skriptmallen_borjar_med_vcScript_importen():
    """Utan den raden finns varken delay() eller getSimulation(), och OnRun
    dor tyst (M-06)."""
    assert _skriptmallen().lstrip().startswith("from vcScript import *")


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




def test_grinden_faller_verkligen_en_mall_med_bruten_strangliteral():
    """En grind som aldrig fallt nagot ar inget bevis.

    Har byggs FELET medvetet: en SKRIPT-mall dar ett \\n i kallan blir en
    riktig radbrytning inne i en strangliteral. Det ar exakt det fel som
    slapp igenom ett test som laste filtexten med en regex.
    """
    trasig = 'SKRIPT = """\ndef f():\n    logga(\'fel\\n\' + x)\n"""\n'
    trad = ast.parse(trasig)
    varde = None
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Assign) and getattr(nod.targets[0], "id", None) == "SKRIPT":
            varde = ast.literal_eval(nod.value)
    assert varde is not None
    assert "\n' + x" in varde, "mallens varde bar en riktig radbrytning i literalen"
    with pytest.raises(SyntaxError):
        compile(varde, "<trasig>", "exec")

    # Och samma mall skriven RATT ska ga igenom.
    hel = 'SKRIPT = """\ndef f():\n    logga(\'fel: \' + x)\n"""\n'
    trad = ast.parse(hel)
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Assign) and getattr(nod.targets[0], "id", None) == "SKRIPT":
            compile(ast.literal_eval(nod.value), "<hel>", "exec")
