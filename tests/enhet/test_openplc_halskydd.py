# -*- coding: utf-8 -*-
"""M-108: Hålskydd och fail-closed grindar mot OpenPLC Runtime v4.

Bakgrund (mätt i M-108, docs/matningar/M-108_openplc_som_tredje_motor.md):
1. STRUCT/ARRAY-jämförelse (P1 = P2, arr1 = arr2, P1 <> P2) släpptes tidigare
   av validatorn (_binartyp kontrollerade bara gemensam typ) men OpenPLC:s
   backend faller med "no match for operator==". IEC 61131-3 definierar =/<>
   bara för elementära typer.
2. Strängfunktioner (CONCAT, LEFT, RIGHT, MID, FIND, LEN, INSERT, DELETE, REPLACE)
   med strängliteral som första argument släpptes av validatorn och frontend,
   men backend faller med mallhärledningsfel ("mismatched types 'const IECString<MaxLen>'
   and 'const char [N]'"). Med en variabel som första argument bygger allt.

Denna testfil ägs av M-108-mandatet och provar att båda reglerna fäller trasiga
fall fail-closed och släpper igenom alla giltiga konstruktioner.
"""
from __future__ import annotations

import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import validera  # noqa: E402


def _pou(dekl: str, kropp: str, extra: str = "", prolog: str = "") -> str:
    return "%sPROGRAM P\n%sVAR\n%sEND_VAR\n%sEND_PROGRAM\n" % (
        prolog, extra, dekl, kropp
    )


PROLOG_PUNKT = """\
TYPE
    Punkt : STRUCT
        x : INT;
        y : INT;
        text : STRING;
    END_STRUCT;
END_TYPE
"""

DEKL_PUNKT = """\
    p1, p2 : Punkt;
    b : BOOL;
"""

DEKL_ARRAY = """\
    arr1, arr2 : ARRAY [1..5] OF INT;
    b : BOOL;
"""

DEKL_ARRAY_STRUCT = """\
    arr1, arr2 : ARRAY [1..3] OF Punkt;
    b : BOOL;
"""

DEKL_STRANG = """\
    sA, sB : STRING;\n    iA : INT;\n    arr : ARRAY [1..3] OF STRING;\n"""

DEKL_STRANG_MED_STRUCT = """\
    sA, sB : STRING;\n    iA : INT;\n    p : Punkt;\n    arr : ARRAY [1..3] OF STRING;\n"""


# =========================================================================
# REGEL 1: STRUCT- och ARRAY-jämförelser (=, <>)
# =========================================================================

TRASIGA_STRUCT_ARRAY_JAMFORELSER = [
    ("struct_likhet",
     _pou(DEKL_PUNKT, " b := (p1 = p2);\n", prolog=PROLOG_PUNKT),
     "="),
    ("struct_olikhet",
     _pou(DEKL_PUNKT, " b := (p1 <> p2);\n", prolog=PROLOG_PUNKT),
     "<>"),
    ("array_likhet",
     _pou(DEKL_ARRAY, " b := (arr1 = arr2);\n"),
     "="),
    ("array_olikhet",
     _pou(DEKL_ARRAY, " b := (arr1 <> arr2);\n"),
     "<>"),
    ("array_of_struct_likhet",
     _pou(DEKL_ARRAY_STRUCT, " b := (arr1 = arr2);\n", prolog=PROLOG_PUNKT),
     "="),
    ("array_of_struct_olikhet",
     _pou(DEKL_ARRAY_STRUCT, " b := (arr1 <> arr2);\n", prolog=PROLOG_PUNKT),
     "<>"),
]


@pytest.mark.parametrize("namn,kalla,op", TRASIGA_STRUCT_ARRAY_JAMFORELSER,
                         ids=[x[0] for x in TRASIGA_STRUCT_ARRAY_JAMFORELSER])
def test_trasig_struct_och_array_jamforelse_falls(namn, kalla, op):
    """STRUCT och ARRAY saknar operator== i backend och =/<> i IEC."""
    rapport = validera(kalla)
    assert not rapport.ok, "Borde ha fällts: %s" % namn
    assert "TYP" in rapport.koder()
    typ_anm = [a for a in rapport.anmarkningar if a.kod == "TYP"]
    assert any("operator==" in a.text and "elementära typer" in a.text for a in typ_anm), (
        "Felmeddelandet ska hänvisa till elementära typer och saknad operator==: %s"
        % [a.text for a in typ_anm]
    )


GILTIGA_JAMFORELSER_OCH_TILLDELNINGAR = [
    ("int_likhet",
     _pou(" a, b : INT; c : BOOL;\n", " c := (a = b);\n")),
    ("int_olikhet",
     _pou(" a, b : INT; c : BOOL;\n", " c := (a <> b);\n")),
    ("real_likhet",
     _pou(" a, b : REAL; c : BOOL;\n", " c := (a = b);\n")),
    ("bool_likhet",
     _pou(" a, b, c : BOOL;\n", " c := (a = b);\n")),
    ("time_likhet",
     _pou(" t1, t2 : TIME; c : BOOL;\n", " c := (t1 = t2);\n")),
    ("string_likhet",
     _pou(" s1, s2 : STRING; c : BOOL;\n", " c := (s1 = s2);\n")),
    ("string_literal_likhet",
     _pou(" s1 : STRING; c : BOOL;\n", " c := (s1 = 'test');\n")),
    ("struct_falt_likhet",
     _pou(DEKL_PUNKT, " b := (p1.x = p2.x);\n", prolog=PROLOG_PUNKT)),
    ("array_element_likhet",
     _pou(DEKL_ARRAY, " b := (arr1[1] = arr2[2]);\n")),
    ("struct_tilldelning",
     _pou(DEKL_PUNKT, " p1 := p2;\n", prolog=PROLOG_PUNKT)),
    ("array_tilldelning",
     _pou(DEKL_ARRAY, " arr1 := arr2;\n")),
]


@pytest.mark.parametrize("namn,kalla", GILTIGA_JAMFORELSER_OCH_TILLDELNINGAR,
                         ids=[x[0] for x in GILTIGA_JAMFORELSER_OCH_TILLDELNINGAR])
def test_giltiga_jamforelser_och_tilldelningar_passerar(namn, kalla):
    """Elementära jämförelser och strukturkopiering är giltiga och ska passera."""
    rapport = validera(kalla)
    assert rapport.ok is True, "Borde ha godkänts (%s): %s" % (namn, rapport)


# =========================================================================
# REGEL 2: De 9 strängfunktionerna med literal som första argument
# =========================================================================

TRASIGA_STRANGFUNKTIONER = [
    ("concat_lit_lit",
     _pou(DEKL_STRANG, " sA := CONCAT('foo', 'bar');\n"), "CONCAT"),
    ("concat_lit_var",
     _pou(DEKL_STRANG, " sA := CONCAT('foo', sB);\n"), "CONCAT"),
    ("concat_namngiven_lit",
     _pou(DEKL_STRANG, " sA := CONCAT(IN1 := 'foo', IN2 := sB);\n"), "CONCAT"),
    ("concat_namngiven_omvand_ordning_lit",
     _pou(DEKL_STRANG, " sA := CONCAT(IN2 := sB, IN1 := 'foo');\n"), "CONCAT"),
    ("left_lit",
     _pou(DEKL_STRANG, " sA := LEFT('abcdef', 3);\n"), "LEFT"),
    ("left_namngiven_lit",
     _pou(DEKL_STRANG, " sA := LEFT(IN := 'abcdef', L := 3);\n"), "LEFT"),
    ("right_lit",
     _pou(DEKL_STRANG, " sA := RIGHT('abcdef', 3);\n"), "RIGHT"),
    ("mid_lit",
     _pou(DEKL_STRANG, " sA := MID('abcdef', 3, 2);\n"), "MID"),
    ("find_lit_lit",
     _pou(DEKL_STRANG, " iA := FIND('abcdef', 'cd');\n"), "FIND"),
    ("find_lit_var",
     _pou(DEKL_STRANG, " iA := FIND('abcdef', sB);\n"), "FIND"),
    ("len_lit",
     _pou(DEKL_STRANG, " iA := LEN('abcdef');\n"), "LEN"),
    ("insert_lit_lit",
     _pou(DEKL_STRANG, " sA := INSERT('abcdef', 'XYZ', 3);\n"), "INSERT"),
    ("delete_lit",
     _pou(DEKL_STRANG, " sA := DELETE('abcdef', 2, 3);\n"), "DELETE"),
    ("replace_lit_lit",
     _pou(DEKL_STRANG, " sA := REPLACE('abcdef', 'XYZ', 2, 3);\n"), "REPLACE"),
    ("nastlad_inre_lit",
     _pou(DEKL_STRANG, " sA := CONCAT(sB, LEFT('abcdef', 2));\n"), "LEFT"),
]


@pytest.mark.parametrize("namn,kalla,fn", TRASIGA_STRANGFUNKTIONER,
                         ids=[x[0] for x in TRASIGA_STRANGFUNKTIONER])
def test_trasiga_strangfunktioner_med_literal_forst_falls(namn, kalla, fn):
    """Strängfunktioner med literal som första argument faller i backend mallhärledning."""
    rapport = validera(kalla)
    assert not rapport.ok, "Borde ha fällts: %s" % namn
    assert "TYP" in rapport.koder()
    typ_anm = [a for a in rapport.anmarkningar if a.kod == "TYP"]
    assert any("mallhärledning" in a.text and "variabel" in a.text for a in typ_anm), (
        "Felmeddelandet ska hänvisa till mallhärledning och variabel: %s"
        % [a.text for a in typ_anm]
    )


GILTIGA_STRANGFUNKTIONER = [
    ("concat_var_lit",
     _pou(DEKL_STRANG, " sA := CONCAT(sB, 'bar');\n")),
    ("concat_var_var",
     _pou(DEKL_STRANG, " sA := CONCAT(sA, sB);\n")),
    ("concat_namngiven_var",
     _pou(DEKL_STRANG, " sA := CONCAT(IN1 := sA, IN2 := 'bar');\n")),
    ("left_var",
     _pou(DEKL_STRANG, " sA := LEFT(sB, 3);\n")),
    ("left_namngiven_var",
     _pou(DEKL_STRANG, " sA := LEFT(IN := sB, L := 3);\n")),
    ("right_var",
     _pou(DEKL_STRANG, " sA := RIGHT(sB, 3);\n")),
    ("mid_var",
     _pou(DEKL_STRANG, " sA := MID(sB, 3, 2);\n")),
    ("find_var_lit",
     _pou(DEKL_STRANG, " iA := FIND(sB, 'cd');\n")),
    ("find_var_var",
     _pou(DEKL_STRANG, " iA := FIND(sA, sB);\n")),
    ("len_var",
     _pou(DEKL_STRANG, " iA := LEN(sB);\n")),
    ("insert_var_lit",
     _pou(DEKL_STRANG, " sA := INSERT(sB, 'XYZ', 3);\n")),
    ("delete_var",
     _pou(DEKL_STRANG, " sA := DELETE(sB, 2, 3);\n")),
    ("replace_var_lit",
     _pou(DEKL_STRANG, " sA := REPLACE(sB, 'XYZ', 2, 3);\n")),
    ("strangfunktion_kedja",
     _pou(DEKL_STRANG, " sA := CONCAT(LEFT(sA, 2), RIGHT(sA, 2));\n")),
    ("struct_textfalt_forst",
     _pou(DEKL_STRANG_MED_STRUCT, " sA := CONCAT(p.text, 'bar');\n", prolog=PROLOG_PUNKT)),
    ("array_element_forst",
     _pou(DEKL_STRANG, " sA := CONCAT(arr[1], 'bar');\n")),
]


@pytest.mark.parametrize("namn,kalla", GILTIGA_STRANGFUNKTIONER,
                         ids=[x[0] for x in GILTIGA_STRANGFUNKTIONER])
def test_giltiga_strangfunktioner_med_variabel_passerar(namn, kalla):
    """Strängfunktioner med variabel/uttryck som första argument bygger och ska passera."""
    rapport = validera(kalla)
    assert rapport.ok is True, "Borde ha godkänts (%s): %s" % (namn, rapport)
