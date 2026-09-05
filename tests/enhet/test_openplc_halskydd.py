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
3. R1: Fältinitiering (ARRAY[1..3] OF INT := [1, 2, 3] och upprepningsform := [3(0)])
   som tidigare avvisades av läsaren/typkontrollen men bygger och kör i OpenPLC.
4. R3: REF_TO-stöd (pRef : REF_TO INT), dereferensiering (^), NULL och restriktion mot REF_TO i STRUCT.

Denna testfil ägs av M-108-mandatet och provar att reglerna fäller trasiga
fall fail-closed och släpper igenom alla giltiga konstruktioner.
"""
from __future__ import annotations

import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import las, skriv_enhet, tolk, validera  # noqa: E402


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
    ("concat_namngiven_omvand_ordning_lit_VAR",
     _pou(DEKL_STRANG, " sA := CONCAT(IN2 := 'bar', IN1 := 'foo');\n"), "CONCAT"),
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
    # M-108 ommätning: literalen static_castas när en variabel finns bland
    # strängargumenten (FIND('abcdef', sB) bygger) — bara helt utan variabel
    # faller backend.
    ("concat_lit_var",
     _pou(DEKL_STRANG, " sA := CONCAT('foo', sB);\n")),
    ("concat_namngiven_lit",
     _pou(DEKL_STRANG, " sA := CONCAT(IN1 := 'foo', IN2 := sB);\n")),
    ("concat_namngiven_omvand_ordning_var",
     _pou(DEKL_STRANG, " sA := CONCAT(IN2 := sB, IN1 := 'foo');\n")),
    ("find_lit_var",
     _pou(DEKL_STRANG, " iA := FIND('abcdef', sB);\n")),
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


# =========================================================================
# REGEL 3: R1 — Fältinitiering och upprepningsform (ARRAY := [1, 2, 3], [3(0)])
# =========================================================================

GILTIGA_FALTINITIERINGAR = [
    ("int_lista",
     _pou("    a : ARRAY[1..3] OF INT := [1, 2, 3];\n    iA : INT;\n", "    iA := a[1];\n")),
    ("int_upprepning",
     _pou("    a : ARRAY[1..3] OF INT := [3(0)];\n    iA : INT;\n", "    iA := a[1];\n")),
    ("blandad_upprepning",
     _pou("    a : ARRAY[1..5] OF INT := [2(1), 3(0)];\n    iA : INT;\n", "    iA := a[1];\n")),
    ("bool_lista",
     _pou("    a : ARRAY[1..3] OF BOOL := [TRUE, FALSE, TRUE];\n    bA : BOOL;\n", "    bA := a[1];\n")),
    ("bool_upprepning",
     _pou("    a : ARRAY[1..4] OF BOOL := [2(TRUE), 2(FALSE)];\n    bA : BOOL;\n", "    bA := a[1];\n")),
    ("real_upprepning",
     _pou("    a : ARRAY[-2..2] OF REAL := [5(0.0)];\n    rA : REAL;\n", "    rA := a[-2];\n")),
    ("real_fran_heltal",
     _pou("    a : ARRAY[1..3] OF REAL := [1, 2, 3];\n    rA : REAL;\n", "    rA := a[1];\n")),
    ("negativa_element",
     _pou("    a : ARRAY[1..3] OF INT := [-1, -2, -3];\n    iA : INT;\n", "    iA := a[1];\n")),
    ("multidim_upprepning",
     _pou("    m : ARRAY[1..2, 1..3] OF INT := [6(0)];\n    iA : INT;\n", "    iA := m[1, 1];\n")),
    ("string_lista",
     _pou("    a : ARRAY[1..2] OF STRING := ['foo', 'bar'];\n    s : STRING;\n", "    s := a[1];\n")),
]


@pytest.mark.parametrize("namn,kalla", GILTIGA_FALTINITIERINGAR,
                         ids=[x[0] for x in GILTIGA_FALTINITIERINGAR])
def test_giltiga_faltinitieringar_passerar(namn, kalla):
    """Giltiga fältinitieringar ska godkännas av validatorn."""
    rapport = validera(kalla)
    assert rapport.ok is True, "Borde ha godkänts (%s): %s" % (namn, rapport)


@pytest.mark.parametrize("namn,kalla", GILTIGA_FALTINITIERINGAR,
                         ids=[x[0] for x in GILTIGA_FALTINITIERINGAR])
def test_faltinitiering_tur_och_retur(namn, kalla):
    """Fältinitieringar ska bevara identitet genom läsare och skrivare."""
    enhet1 = las(kalla)
    text1 = skriv_enhet(enhet1)
    enhet2 = las(text1)
    text2 = skriv_enhet(enhet2)
    assert text1 == text2
    assert enhet1 == enhet2


TRASIGA_FALTINITIERINGAR = [
    ("fel_elementtyp_real_till_int",
     _pou("    a : ARRAY[1..3] OF INT := [1, 2, 3.5];\n", ""),
     "TYP", "flyttalsliteral kan inte tilldelas INT"),
    ("fel_elementtyp_upprepning",
     _pou("    a : ARRAY[1..3] OF INT := [3(1.5)];\n", ""),
     "TYP", "flyttalsliteral kan inte tilldelas INT"),
    ("fel_elementtyp_int_till_bool",
     _pou("    a : ARRAY[1..3] OF BOOL := [1, 2, 3];\n", ""),
     "TYP", "heltalsliteral kan inte tilldelas BOOL"),
    ("for_fa_element",
     _pou("    a : ARRAY[1..3] OF INT := [1, 2];\n", ""),
     "TYP", "rymmer 3 element men initieraren har 2"),
    ("for_manga_element",
     _pou("    a : ARRAY[1..3] OF INT := [1, 2, 3, 4];\n", ""),
     "TYP", "rymmer 3 element men initieraren har 4"),
    ("for_fa_upprepning",
     _pou("    a : ARRAY[1..3] OF INT := [2(0)];\n", ""),
     "TYP", "rymmer 3 element men initieraren har 2"),
    ("for_manga_upprepning",
     _pou("    a : ARRAY[1..3] OF INT := [4(0)];\n", ""),
     "TYP", "rymmer 3 element men initieraren har 4"),
    ("faltinit_till_skalar",
     _pou("    a : INT := [1, 2, 3];\n", ""),
     "TYP", "fältinitierare kan bara tilldelas ett fält"),
    ("literal_over_int",
     _pou("    a : ARRAY[1..2] OF INT := [1, 40000];\n", ""),
     "TYP", "40000 ligger utanför INT"),
    ("upprepning_noll",
     _pou("    a : ARRAY[1..3] OF INT := [0(1)];\n", ""),
     "SYNTAX", "upprepningsantalet"),
    ("tom_initierare",
     _pou("    a : ARRAY[1..3] OF INT := [];\n", ""),
     "SYNTAX", "kan inte vara tom"),
]


@pytest.mark.parametrize("namn,kalla,exp_kod,exp_txt", TRASIGA_FALTINITIERINGAR,
                         ids=[x[0] for x in TRASIGA_FALTINITIERINGAR])
def test_trasiga_faltinitieringar_falls(namn, kalla, exp_kod, exp_txt):
    """Trasiga fältinitieringar (fel typ, fel antal, ogiltig syntax) måste fällas fail-closed."""
    rapport = validera(kalla)
    assert not rapport.ok, "Borde ha fällts: %s" % namn
    assert exp_kod in rapport.koder(), "Väntade felkod %s i %s (%s)" % (exp_kod, rapport.koder(), namn)
    assert any(exp_txt.lower() in a.text.lower() for a in rapport.anmarkningar), (
        "Felmeddelande ska innehålla %r: %s" % (exp_txt, [a.text for a in rapport.anmarkningar])
    )


# =========================================================================
# REGEL 4: R3 — REF_TO-stöd, dereferensiering (^), NULL och STRUCT-begränsning
# =========================================================================

GILTIGA_REF_TO = [
    ("deref_lasning",
     _pou("    pRef : REF_TO INT;\n    iA : INT;\n", "    iA := pRef^;\n")),
    ("deref_skrivning_var",
     _pou("    pRef : REF_TO INT;\n    iA : INT;\n", "    pRef^ := iA;\n")),
    ("deref_skrivning_lit",
     _pou("    pRef : REF_TO INT;\n", "    pRef^ := 42;\n")),
    ("null_init_pekar",
     _pou("    pRef : REF_TO INT := NULL;\n", "    pRef := NULL;\n")),
    ("null_tilldelning_pekar",
     _pou("    pRef : REF_TO INT;\n", "    pRef := NULL;\n")),
    ("pekare_kopiering",
     _pou("    p1, p2 : REF_TO INT;\n", "    p1 := p2;\n")),
    ("deref_i_uttryck",
     _pou("    pRef : REF_TO INT;\n    iA : INT;\n", "    iA := pRef^ + 5;\n")),
    ("deref_real_pekare",
     _pou("    pRef : REF_TO REAL;\n    rA : REAL;\n", "    rA := pRef^;\n    pRef^ := 3.14;\n")),
    ("deref_bool_pekare",
     _pou("    pRef : REF_TO BOOL;\n    bA : BOOL;\n", "    bA := pRef^;\n    pRef^ := TRUE;\n")),
    # M-108 ommätning: pRef = NULL genererar PREF == IEC_NULL och bygger.
    ("null_likhet",
     _pou("    pRef : REF_TO INT;\n    bA : BOOL;\n", "    bA := (pRef = NULL);\n")),
    ("null_olikhet",
     _pou("    pRef : REF_TO INT;\n    bA : BOOL;\n", "    bA := (pRef <> NULL);\n")),
]


@pytest.mark.parametrize("namn,kalla", GILTIGA_REF_TO,
                         ids=[x[0] for x in GILTIGA_REF_TO])
def test_giltiga_ref_to_passerar(namn, kalla):
    """Giltiga REF_TO-deklarationer, deref-läs/skriv, NULL och pekarkopiering ska godkännas."""
    rapport = validera(kalla)
    assert rapport.ok is True, "Borde ha godkänts (%s): %s" % (namn, rapport)


TRASIGA_REF_TO = [
    ("deref_av_int",
     _pou("    iA, iB : INT;\n", "    iA := iB^;\n"),
     "TYP", "kan bara avreferera REF_TO"),
    ("deref_av_int_skriv",
     _pou("    iA : INT;\n", "    iA^ := 10;\n"),
     "TYP", "kan bara avreferera REF_TO"),
    ("deref_av_bool",
     _pou("    bA, bB : BOOL;\n", "    bA := bB^;\n"),
     "TYP", "kan bara avreferera REF_TO"),
    ("struct_falt_ref_to",
     "TYPE\n  S : STRUCT\n    p : REF_TO INT;\n  END_STRUCT;\nEND_TYPE\nPROGRAM P\nVAR\n  s1 : S;\nEND_VAR\nEND_PROGRAM\n",
     "TYP", "STRUCT-fält av REF_TO-typ stöds inte"),
    ("null_till_int",
     _pou("    iA : INT;\n", "    iA := NULL;\n"),
     "TYP", "NULL kan bara tilldelas REF_TO-typer"),
    ("null_init_int",
     _pou("    iA : INT := NULL;\n", ""),
     "TYP", "NULL kan bara tilldelas REF_TO-typer"),
    ("null_till_bool",
     _pou("    bA : BOOL;\n", "    bA := NULL;\n"),
     "TYP", "NULL kan bara tilldelas REF_TO-typer"),
    ("pekare_kopiering_olika_typer",
     _pou("    p1 : REF_TO INT;\n    p2 : REF_TO DINT;\n", "    p1 := p2;\n"),
     "TYP", "REF_TO DINT kan inte tilldelas REF_TO INT"),
    ("pekare_till_int_tilldelning",
     _pou("    p1 : REF_TO INT;\n    iA : INT;\n", "    p1 := iA;\n"),
     "TYP", "INT kan inte tilldelas REF_TO INT"),
    ("int_till_pekare_tilldelning",
     _pou("    p1 : REF_TO INT;\n    iA : INT;\n", "    iA := p1;\n"),
     "TYP", "REF_TO INT kan inte tilldelas INT"),
]


@pytest.mark.parametrize("namn,kalla,exp_kod,exp_txt", TRASIGA_REF_TO,
                         ids=[x[0] for x in TRASIGA_REF_TO])
def test_trasiga_ref_to_falls(namn, kalla, exp_kod, exp_txt):
    """Trasiga REF_TO-konstruktioner (deref av icke-pekare, NULL till skalar, STRUCT-fält) fälls fail-closed."""
    rapport = validera(kalla)
    assert not rapport.ok, "Borde ha fällts: %s" % namn
    assert exp_kod in rapport.koder(), "Väntade felkod %s i %s (%s)" % (exp_kod, rapport.koder(), namn)
    assert any(exp_txt.lower() in a.text.lower() for a in rapport.anmarkningar), (
        "Felmeddelande ska innehålla %r: %s" % (exp_txt, [a.text for a in rapport.anmarkningar])
    )


# =========================================================================
# REGEL 5: M-108 Tolkstöd för REF_TO (tolk.kor-spår över pekarprogram)
# =========================================================================

def test_tolk_kor_pekare_genomslapp():
    """M-108: Genomsläpp via pekare — läsning och skrivning genom dereferensiering."""
    kalla = """\
PROGRAM P
VAR_INPUT
    iIn : INT;
END_VAR
VAR_OUTPUT
    iOut : INT;
END_VAR
VAR
    pIn : REF_TO INT;
    pOut : REF_TO INT;
END_VAR
    pIn := REF(iIn);
    pOut := REF(iOut);
    pOut^ := pIn^ * 2;
END_PROGRAM
"""
    signaler = {"iIn": "int", "iOut": "int"}
    riktningar = {"iIn": "in", "iOut": "out"}
    insatser = [
        (0.0, {"iIn": 5}),
        (20.0, {"iIn": 10}),
        (40.0, {"iIn": 25}),
    ]
    spar = tolk.kor(kalla, signaler, riktningar, insatser)
    forvantat = [
        {"t_ms": 0.0, "varden": {"IIN": 5, "IOUT": 10, "PIN": ("REF", "IIN"), "POUT": ("REF", "IOUT")}},
        {"t_ms": 20.0, "varden": {"IIN": 10, "IOUT": 20, "PIN": ("REF", "IIN"), "POUT": ("REF", "IOUT")}},
        {"t_ms": 40.0, "varden": {"IIN": 25, "IOUT": 50, "PIN": ("REF", "IIN"), "POUT": ("REF", "IOUT")}},
    ]
    assert spar == forvantat


def test_tolk_kor_null_deref_falls_fail_closed():
    """M-108: NULL-deref fäller med Tolkfel (fail-closed, aldrig tyst None)."""
    # Fall 1: NULL-deref vid läsning i senare scan
    kalla_las = """\
PROGRAM P
VAR_INPUT
    bTrigga : BOOL;
END_VAR
VAR_OUTPUT
    iOut : INT;
END_VAR
VAR
    pRef : REF_TO INT := NULL;
END_VAR
    IF bTrigga THEN
        iOut := pRef^;
    END_IF;
END_PROGRAM
"""
    signaler_las = {"bTrigga": "bool", "iOut": "int"}
    riktningar_las = {"bTrigga": "in", "iOut": "out"}
    insatser_las = [
        (0.0, {"bTrigga": False}),
        (20.0, {"bTrigga": True}),
    ]
    with pytest.raises(tolk.Tolkfel) as fel_las:
        tolk.kor(kalla_las, signaler_las, riktningar_las, insatser_las)
    assert "NULL" in str(fel_las.value) or "avreferering" in str(fel_las.value)

    # Fall 2: NULL-deref vid skrivning med oinitierad pekare (standard NULL)
    kalla_skriv = """\
PROGRAM P
VAR_INPUT
    bTrigga : BOOL;
END_VAR
VAR_OUTPUT
    iOut : INT;
END_VAR
VAR
    pRef : REF_TO INT;
END_VAR
    IF bTrigga THEN
        pRef^ := 42;
    END_IF;
END_PROGRAM
"""
    signaler_skriv = {"bTrigga": "bool", "iOut": "int"}
    riktningar_skriv = {"bTrigga": "in", "iOut": "out"}
    insatser_skriv = [
        (0.0, {"bTrigga": False}),
        (20.0, {"bTrigga": True}),
    ]
    with pytest.raises(tolk.Tolkfel) as fel_skriv:
        tolk.kor(kalla_skriv, signaler_skriv, riktningar_skriv, insatser_skriv)
    assert "NULL" in str(fel_skriv.value) or "avreferering" in str(fel_skriv.value)


def test_tolk_kor_ompekning_mitt_i_spar():
    """M-108: Ompekning mitt i spår — pekaren växlar mellan olika mål över tid."""
    kalla = """\
PROGRAM P
VAR_INPUT
    bValjB : BOOL;
    iIn : INT;
END_VAR
VAR_OUTPUT
    iA : INT;
    iB : INT;
END_VAR
VAR
    pMal : REF_TO INT;
END_VAR
    IF bValjB THEN
        pMal := REF(iB);
    ELSE
        pMal := REF(iA);
    END_IF;
    pMal^ := iIn;
END_PROGRAM
"""
    signaler = {"bValjB": "bool", "iIn": "int", "iA": "int", "iB": "int"}
    riktningar = {"bValjB": "in", "iIn": "in", "iA": "out", "iB": "out"}
    insatser = [
        (0.0, {"bValjB": False, "iIn": 11}),
        (20.0, {"bValjB": False, "iIn": 22}),
        (40.0, {"bValjB": True, "iIn": 33}),
        (60.0, {"bValjB": True, "iIn": 44}),
        (80.0, {"bValjB": False, "iIn": 55}),
    ]
    spar = tolk.kor(kalla, signaler, riktningar, insatser)
    forvantat = [
        {"t_ms": 0.0, "varden": {"BVALJB": False, "IIN": 11, "IA": 11, "IB": 0, "PMAL": ("REF", "IA")}},
        {"t_ms": 20.0, "varden": {"BVALJB": False, "IIN": 22, "IA": 22, "IB": 0, "PMAL": ("REF", "IA")}},
        {"t_ms": 40.0, "varden": {"BVALJB": True, "IIN": 33, "IA": 22, "IB": 33, "PMAL": ("REF", "IB")}},
        {"t_ms": 60.0, "varden": {"BVALJB": True, "IIN": 44, "IA": 22, "IB": 44, "PMAL": ("REF", "IB")}},
        {"t_ms": 80.0, "varden": {"BVALJB": False, "IIN": 55, "IA": 55, "IB": 44, "PMAL": ("REF", "IA")}},
    ]
    assert spar == forvantat


def test_tolk_kor_pekare_kopiering_och_null_aterstallning():
    """M-108: Pekarkopiering och NULL-tilldelning under spårkörning."""
    kalla = """\
PROGRAM P
VAR_INPUT
    bNolla : BOOL;
    iIn : INT;
END_VAR
VAR_OUTPUT
    iOut : INT;
    bAktiv : BOOL;
END_VAR
VAR
    p1, p2 : REF_TO INT;
END_VAR
    IF bNolla THEN
        p1 := NULL;
    ELSE
        p1 := REF(iOut);
    END_IF;
    p2 := p1;
    bAktiv := (p2 <> NULL);
    IF bAktiv THEN
        p2^ := iIn;
    END_IF;
END_PROGRAM
"""
    signaler = {"bNolla": "bool", "iIn": "int", "iOut": "int", "bAktiv": "bool"}
    riktningar = {"bNolla": "in", "iIn": "in", "iOut": "out", "bAktiv": "out"}
    insatser = [
        (0.0, {"bNolla": False, "iIn": 100}),
        (20.0, {"bNolla": True, "iIn": 200}),
        (40.0, {"bNolla": False, "iIn": 300}),
    ]
    spar = tolk.kor(kalla, signaler, riktningar, insatser)
    forvantat = [
        {"t_ms": 0.0, "varden": {"BNOLLA": False, "IIN": 100, "IOUT": 100, "BAKTIV": True, "P1": ("REF", "IOUT"), "P2": ("REF", "IOUT")}},
        {"t_ms": 20.0, "varden": {"BNOLLA": True, "IIN": 200, "IOUT": 100, "BAKTIV": False, "P1": None, "P2": None}},
        {"t_ms": 40.0, "varden": {"BNOLLA": False, "IIN": 300, "IOUT": 300, "BAKTIV": True, "P1": ("REF", "IOUT"), "P2": ("REF", "IOUT")}},
    ]
    assert spar == forvantat
