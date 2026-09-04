# -*- coding: utf-8 -*-
"""Motbevis: grindar som läser KÄLLKOD SOM TEXT i stället för att pröva verkan.

Projektets egen mest kända incident: ett test som skulle fånga en trasig
skriptmall läste filtexten med en regex i stället för strängens verkliga värde.
Grönt test, trasig produkt. `test_tillagg_syntax.py` rättade just det fallet —
men två av dess ANDRA prov är av exakt samma sort. De prövas här genom att
mata dem indata där verkan är borta men texten kvar.
"""
import ast
import os

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TILLAGG = os.path.join(_ROT, "ext", "vc_addon", "vc_assist")
_BRIDGE = os.path.join(_TILLAGG, "bridge_cmd.py")


def _kalla():
    with open(_BRIDGE, encoding="utf-8") as f:
        return f.read()


def test_kompileringsgrinden_provas_pa_verkan_inte_pa_en_strang():
    """`test_uppstarten_kompilerar_skriptet_innan_det_satts` gör två
    substrängsprov på filtexten:

        assert 'compile(kalla, "<vc_assist_pump>", "exec")' in kalla
        assert "GAR INTE ATT KOMPILERA" in kalla

    Kopplar man ur grinden — raderna kvar, men i en gren som aldrig körs —
    säger provet fortfarande ja. Det är samma felslut som regexen på mallen.
    """
    kalla = _kalla()
    urkopplad = kalla.replace(
        '            compile(kalla, "<vc_assist_pump>", "exec")',
        '            pass  # grinden urkopplad\n'
        '            if False:\n'
        '                compile(kalla, "<vc_assist_pump>", "exec")')
    assert urkopplad != kalla, "hittade inte compile-raden att koppla ur"
    ast.parse(urkopplad)          # kopian är fortfarande giltig Python

    # Det befintliga testets exakta predikat, ord för ord:
    hittas = ('compile(kalla, "<vc_assist_pump>", "exec")' in urkopplad
              and "GAR INTE ATT KOMPILERA" in urkopplad)
    assert not hittas, (
        "grinden är urkopplad men test_uppstarten_kompilerar_skriptet_innan_"
        "det_satts hittar sina strängar ändå och förblir grönt: provet mäter "
        "filtexten, inte att en trasig mall verkligen vägras")


def test_s_kravet_utloses_av_att_nagon_skriver_text_till_vc_inte_av_ordet_Name():
    """`test_ingen_tillaggsfil_anvander_unicode_literals_mot_vc` lyder:

        if "unicode_literals" in kalla and ".Name = " in kalla:
            assert "def _s(" in kalla

    Två fel i samma rad. Utlösaren är strängen ".Name = ", men M-05 mätte att
    VARJE strängskrivning faller: `beh.Script`, `prop.Value` och `comp.Name`
    kastade alla SystemError. Och kravet är att `_s` är DEFINIERAD, inte att
    den används. En fil som skriver `prop.Value = "text"` rakt in i VC:s
    bindning, utan `_s` någonstans, passerar grinden orörd.
    """
    trasig_fil = (
        "from __future__ import unicode_literals\n"
        "def satt(prop):\n"
        "    prop.Value = 'en strang rakt in i py2-bindningen'\n")

    # Den befintliga grindens predikat, ord för ord:
    utloses = "unicode_literals" in trasig_fil and ".Name = " in trasig_fil
    passerar = (not utloses) or ("def _s(" in trasig_fil)
    assert not passerar, (
        "en fil som bryter M-05 rakt av passerar grinden, för att den varken "
        "skriver till .Name eller behöver använda _s för att ha den definierad")


def test_s_kravet_ser_att_definitionen_ocksa_anvands():
    """Samma grind, andra halvan: `_s` definierad men aldrig anropad."""
    trasig_fil = (
        "from __future__ import unicode_literals\n"
        "def _s(x):\n"
        "    return x\n"
        "def satt(comp):\n"
        "    comp.Name = 'utan _s'\n")
    utloses = "unicode_literals" in trasig_fil and ".Name = " in trasig_fil
    passerar = (not utloses) or ("def _s(" in trasig_fil)
    assert not passerar, (
        "filen skriver comp.Name = 'utan _s' men grinden godkänner den, "
        "eftersom den bara letar efter att 'def _s(' står någonstans i filen")


def test_kompileringsgrinden_gar_att_prova_utan_att_starta_vc():
    """95_testprotokoll.md: en grind utan trasig fixtur är oprövad.

    Grinden bor mitt i `bridge_cmd._starta()`, som anropar `app.createComponent()`
    på raden före. Den går alltså inte att köra utan VC, och det finns ingen
    trasig fixtur som visar den fälla. Kravet: någon funktion i modulen kör
    compile() på mallen utan att röra VC.
    """
    trad = ast.parse(_kalla())
    VC_NAMN = ("createComponent", "createBehaviour", "getSimulation",
               "startSimulation", "getApplication", "deleteComponent")
    fria = []
    for nod in ast.walk(trad):
        if not isinstance(nod, ast.FunctionDef):
            continue
        har_compile = any(
            isinstance(n, ast.Call) and getattr(n.func, "id", None) == "compile"
            for n in ast.walk(nod))
        if not har_compile:
            continue
        ror_vc = any(
            isinstance(n, ast.Call)
            and (getattr(n.func, "attr", None) in VC_NAMN
                 or getattr(n.func, "id", None) in VC_NAMN)
            for n in ast.walk(nod))
        if not ror_vc:
            fria.append(nod.name)
    assert fria, (
        "ingen VC-fri funktion i bridge_cmd.py kör compile() på mallen; "
        "kompileringsgrinden kan aldrig visas fälla en trasig mall utan att "
        "starta VC, och har därmed ingen trasig fixtur")
