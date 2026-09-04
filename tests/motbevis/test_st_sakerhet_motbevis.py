# -*- coding: utf-8 -*-
"""Motbevis: I15 håller för `:=` men inte för VAR_IN_OUT.

`validator._skrivmal()` dömer bara det som står i vänsterledet av en
tilldelning. Ett funktionsblocksanrop behandlas som en LÄSNING av sina
aktualparametrar. I IEC 61131-3 är en VAR_IN_OUT-parameter en referens:
anropet `s(m := nod)` ger blocket skrivrätt på `nod`.

Alla fyra riktningsgrindar går att gå runt på samma sätt:

  {SAKERHET}   I15, "detta är inte förhandlingsbart" (50_grindar.md)
  CONSTANT     RIKTNING
  utgångar     DUBBELSKRIVNING (två skrivningar i samma scan)
  VAR_INPUT    RIKTNING

`tests/enhet/test_st_semantik.py` prövar alla fyra — men bara med `:=` i
vänsterledet. Den prövar formen, inte förmågan.

Not: `svc/vc_assist_svc/st/stdbibliotek.py` har inget standardblock med
VAR_IN_OUT, så hålet kräver ett blocket som ligger i samma källa. Validatorn
tar emot och godkänner sådan källa utan invändning, vilket är vad proven nedan
visar. Grind 2 och 3 i `50_grindar.md` är hela mekaniken bakom I15.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import typer as T          # noqa: E402
from vc_assist_svc.st.validator import validera  # noqa: E402

SATT = """
FUNCTION_BLOCK Satt
VAR_IN_OUT
 m : BOOL;
END_VAR
 m := TRUE;
END_FUNCTION_BLOCK
"""


def test_sakerhetstagg_far_inte_skrivas_via_en_var_in_out_parameter():
    """I15: taggar märkta säkerhet är skrivskyddade för agenten."""
    kalla = SATT + """
PROGRAM P
VAR_INPUT
 nod AT %IX0.0 : BOOL; {SAKERHET}
END_VAR
VAR
 s : Satt;
END_VAR
 s(m := nod);
END_PROGRAM
"""
    r = validera(kalla)
    assert "SAKERHET" in r.koder(), (
        "en {SAKERHET}-tagg lämnades som VAR_IN_OUT till ett block som skriver "
        "på den, och validatorn sa ok=%r koder=%r" % (r.ok, r.koder()))


def test_skyddat_namn_ur_signalkartan_far_inte_heller_skrivas_indirekt():
    kalla = SATT + """
PROGRAM P
VAR
 s : Satt;
END_VAR
 s(m := ljusridan);
END_PROGRAM
"""
    r = validera(kalla, externa={"ljusridan": T.BOOL}, skyddade=("ljusridan",))
    assert "SAKERHET" in r.koder(), (
        "ljusridan är säkerhetsmärkt men skrevs via VAR_IN_OUT: ok=%r koder=%r"
        % (r.ok, r.koder()))


def test_constant_far_inte_skrivas_via_en_var_in_out_parameter():
    kalla = SATT + """
PROGRAM P
VAR CONSTANT
 k : BOOL := FALSE;
END_VAR
VAR
 s : Satt;
END_VAR
 s(m := k);
END_PROGRAM
"""
    r = validera(kalla)
    assert "RIKTNING" in r.koder(), (
        "en CONSTANT skrevs via VAR_IN_OUT: ok=%r koder=%r" % (r.ok, r.koder()))


def test_dubbelskrivning_ser_ocksa_skrivningen_som_gar_via_ett_block():
    """Kapplöpningsgrinden: två skrivningar på samma utgång i samma scan.

    Den ena står i klartext, den andra går via VAR_IN_OUT. I PLC:n är det
    samma kapplöpning.
    """
    kalla = SATT + """
PROGRAM P
VAR
 s : Satt;
END_VAR
 ventil := TRUE;
 s(m := ventil);
END_PROGRAM
"""
    r = validera(kalla, externa={"ventil": T.BOOL}, utgangar=("ventil",))
    assert "DUBBELSKRIVNING" in r.koder(), (
        "ventil skrevs två gånger i samma scan, en gång via VAR_IN_OUT: "
        "ok=%r koder=%r" % (r.ok, r.koder()))


def test_en_ingang_far_inte_skrivas_via_en_var_in_out_parameter():
    """Facit för formen: samma tagg skriven med := fälls, som den ska."""
    direkt = validera("""
PROGRAM P
VAR_INPUT
 givare AT %IX0.1 : BOOL;
END_VAR
 givare := TRUE;
END_PROGRAM
""")
    assert "RIKTNING" in direkt.koder(), "facit: := på en ingång SKA fällas"

    indirekt = validera(SATT + """
PROGRAM P
VAR_INPUT
 givare AT %IX0.1 : BOOL;
END_VAR
VAR
 s : Satt;
END_VAR
 s(m := givare);
END_PROGRAM
""")
    assert "RIKTNING" in indirekt.koder(), (
        "samma ingång, samma skrivning, men via VAR_IN_OUT: ok=%r koder=%r"
        % (indirekt.ok, indirekt.koder()))
