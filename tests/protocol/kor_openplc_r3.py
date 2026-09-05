# -*- coding: utf-8 -*-
"""M-108 R3 (våg 1 + våg 2): Sveputökning genom alla tre motorerna.

Provar verdict-nivå (validera, STruC++ compile-API via paket.kompilera, OpenPLC v4
REST-uppladdning) över R3-axlarna:
  Våg 1 (STRUCT och ARRAY OF STRUCT):
    1. STRUCT-deklaration + fältläsning/skrivning (p.x)
    2. STRUCT-kopiering / tilldelning (p1 := p2)
    3. Nästlad STRUCT (y.inre.x)
    4. STRUCT som FB-parameter (VAR_INPUT, VAR_OUTPUT, VAR_IN_OUT)
    5. STRUCT som FUNCTION-parameter och returtyp
    6. ARRAY OF STRUCT med indexering (läsning/skrivning/kopiering)
    7. STRUCT innehållande ARRAY-fält
    8. Flernivåers nästling (3 nivåer) och blandade datatyper
    9. STRUCT-initiering i TYPE-definition
    10. STRUCT-initiering med IEC-form i VAR-deklaration (p : Punkt := (x:=1, y:=2))
    11. ARRAY OF STRUCT initiering i VAR-deklaration
    12. STRUCT- och ARRAY-jämförelser (=, <>)
  Våg 2 (övriga R3-axlar):
    13. REF_TO + dereferensiering (^), inkl. NULL-initiering, NULL-tilldelning,
        kopiering och STRUCT med REF_TO-fält
    14. CASE-satser: intervall+lista i samma gren (1..5, 7:), överlappande grenar,
        CASE på STRUCT-fält och CASE på STRING
    15. REPEAT...UNTIL (basform, EXIT i REPEAT, nästlad REPEAT)
    16. Strängfunktioner på verdict-nivå mot BACKEND (CONCAT, LEFT, RIGHT, MID,
        FIND, LEN, INSERT, DELETE, REPLACE med literal-literalkombinationer och
        variabelkombinationer)

Klassificering via klassificera():
  OVERENS             vi och OpenPLC säger samma sak
  STRANGARE_BEKRAFTAD vi fäller, OpenPLC accepterar, raden finns i STRANGARE
  NY_STRANGARE        vi fäller, OpenPLC accepterar, ingen rad - misstänkt falsk rödgrind
  HAL_BEKRAFTAD       vi släpper, OpenPLC fäller, raden finns i LATTARE
  NYTT_HAL            vi släpper, OpenPLC fäller, ingen rad - hål i vårt lager
  TVAFALL             båda motor 1+2 avvisar, inget att ladda upp
  EJ_KORD             ena sidan kördes inte - får ALDRIG rapporteras som överens

Fail-closed:
  * OpenPLC som inte svarar -> exit 1
  * Saboterad C++ maste ge FAILED (--trasig-fixtur)
  * Exit 1 om NY_STRANGARE eller NYTT_HAL eller EJ_KORD hittas.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.plc import paket as P  # noqa: E402
from vc_assist_svc.plc.openplc import OpenPlcV4, OpenPlcFel  # noqa: E402
from vc_assist_svc.st import validera  # noqa: E402


def _las_svep_avvikelser():
    """Läs STRANGARE och LATTARE från svepfilen."""
    sokvag = os.path.join(_ROT, "tests", "enhet", "test_st_svep_mot_strucpp.py")
    spec = importlib.util.spec_from_file_location("svep_modul", sokvag)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.STRANGARE, mod.LATTARE


BANKPOST = {
    "pastar": (
        "R3-svepet (STRUCT, REF_TO, CASE, REPEAT, strängfunktioner) ger samma dom "
        "i vårt lager som i OpenPLC, eller så klassas avvikelsen som STRANGARE/HAL."),
    "under_prov": ("svc/vc_assist_svc/st/",),
    "facit": "OpenPLC Runtime v4 (oberoende tredje motor)",
    "facitkalla": "OpenPLC Runtime v4:s egen kompilering, läst över REST "
                  "(/api/compilation-status)",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "OpenPLC som inte svarar får aldrig ge tyst grönt",
        "saboterad C++ måste ge FAILED (--trasig-fixtur)",
        "EJ_KORD får aldrig rapporteras som OVERENS",
        "kanalens eget fel (paket/openplc) får inte klassas som motoroenighet",
    ),
    "kraver": ("openplc",),
    "matningar": ("M-108",),
    "utforare": "gemini-1",
}

# Standard deklarationsblock för fall som inte anger eget
DEKL_STD = """\
VAR
    bA, bB, bC : BOOL;
    iA, iB, iC : INT;
    dA : DINT;
    rA, rB : REAL;
    tA, tB : TIME;
    sA, sB, sC : STRING;
END_VAR
"""


def kalla(kropp, dekl=None, prolog=""):
    return "%sPROGRAM Main\n%s%s\nEND_PROGRAM\n" % (
        prolog, DEKL_STD if dekl is None else dekl, kropp)


FALL_R3 = [
    # =========================================================================
    # VÅG 1: STRUCT och ARRAY OF STRUCT (fall 1..24)
    # =========================================================================
    # ---- 1. Grundläggande fältåtkomst och tilldelning ----
    (
        "struct_falt_skriv",
        "deklaration",
        "    p.x := 10;\n    p.y := 20;",
        "VAR\n    p : Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_falt_las",
        "deklaration",
        "    iA := p.x;\n    iB := p.y;",
        "VAR\n    p : Punkt;\n    iA, iB : INT;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_kopiering",
        "deklaration",
        "    p1 := p2;",
        "VAR\n    p1, p2 : Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    # ---- 2. Nästlade strukturer ----
    (
        "struct_nastlad_skriv",
        "deklaration",
        "    y.inre.x := 10;",
        "VAR\n    y : Yttre;\nEND_VAR\n",
        "TYPE\n    Inre : STRUCT\n        x : INT;\n    END_STRUCT;\n"
        "    Yttre : STRUCT\n        inre : Inre;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_nastlad_las",
        "deklaration",
        "    iA := y.inre.x;",
        "VAR\n    y : Yttre;\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Inre : STRUCT\n        x : INT;\n    END_STRUCT;\n"
        "    Yttre : STRUCT\n        inre : Inre;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_tre_nivaer",
        "deklaration",
        "    n3.n2.n1.x := 10;\n    iA := n3.n2.n1.x;",
        "VAR\n    n3 : Niva3;\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Niva1 : STRUCT\n        x : INT;\n    END_STRUCT;\n"
        "    Niva2 : STRUCT\n        n1 : Niva1;\n    END_STRUCT;\n"
        "    Niva3 : STRUCT\n        n2 : Niva2;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    # ---- 3. STRUCT i gränssnitt (FB och funktioner) ----
    (
        "struct_fb_param_in",
        "block",
        "    fb1(inp := p);",
        "VAR\n    fb1 : FB_Punkt;\n    p : Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n"
        "FUNCTION_BLOCK FB_Punkt\nVAR_INPUT\n    inp : Punkt;\nEND_VAR\nEND_FUNCTION_BLOCK\n",
    ),
    (
        "struct_fb_param_ut",
        "block",
        "    fb1(outp => p);",
        "VAR\n    fb1 : FB_Punkt;\n    p : Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n"
        "FUNCTION_BLOCK FB_Punkt\nVAR_OUTPUT\n    outp : Punkt;\nEND_VAR\nEND_FUNCTION_BLOCK\n",
    ),
    (
        "struct_fb_param_inout",
        "block",
        "    fb1(pt := p);",
        "VAR\n    fb1 : FB_Inout;\n    p : Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n"
        "FUNCTION_BLOCK FB_Inout\nVAR_IN_OUT\n    pt : Punkt;\nEND_VAR\n    pt.x := pt.x + 1;\nEND_FUNCTION_BLOCK\n",
    ),
    (
        "struct_funktion_param",
        "funktion",
        "    iA := GetX(p);",
        "VAR\n    p : Punkt;\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n"
        "FUNCTION GetX : INT\nVAR_INPUT\n    inp : Punkt;\nEND_VAR\n    GetX := inp.x;\nEND_FUNCTION\n",
    ),
    (
        "struct_funktion_retur",
        "funktion",
        "    p := SkapaPunkt(1, 2);",
        "VAR\n    p : Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n"
        "FUNCTION SkapaPunkt : Punkt\nVAR_INPUT\n    x_in, y_in : INT;\nEND_VAR\n"
        "    SkapaPunkt.x := x_in;\n    SkapaPunkt.y := y_in;\nEND_FUNCTION\n",
    ),
    # ---- 4. ARRAY OF STRUCT ----
    (
        "array_of_struct_skriv",
        "deklaration",
        "    arr[1].x := 10;",
        "VAR\n    arr : ARRAY[1..3] OF Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "array_of_struct_las",
        "deklaration",
        "    iA := arr[2].x;",
        "VAR\n    arr : ARRAY[1..3] OF Punkt;\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "array_of_struct_element_kopiering",
        "deklaration",
        "    arr[1] := p;\n    p := arr[2];",
        "VAR\n    arr : ARRAY[1..3] OF Punkt;\n    p : Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "array_of_struct_kopiering",
        "deklaration",
        "    arr1 := arr2;",
        "VAR\n    arr1, arr2 : ARRAY[1..2] OF Punkt;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    # ---- 5. STRUCT med sammansatta fält och typer ----
    (
        "struct_med_array_falt",
        "deklaration",
        "    s.data[1] := 10;\n    iA := s.data[1];",
        "VAR\n    s : MedFalt;\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    MedFalt : STRUCT\n        data : ARRAY[1..3] OF INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_blandade_typer",
        "deklaration",
        "    b.flag := TRUE;\n    b.val := 3.14;\n    b.tid := T#100ms;\n    b.text := 'ok';",
        "VAR\n    b : Blandad;\nEND_VAR\n",
        "TYPE\n    Blandad : STRUCT\n        flag : BOOL;\n        val : REAL;\n        tid : TIME;\n        text : STRING;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    # ---- 6. Initiering (TYPE vs VAR) ----
    (
        "struct_typ_initiering",
        "deklaration",
        "    iA := p.x;",
        "VAR\n    p : Punkt;\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT := 42;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_var_initiering_iec",
        "deklaration",
        "    iA := p.x;",
        "VAR\n    p : Punkt := (x := 1, y := 2);\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_nastlad_var_initiering",
        "deklaration",
        "    iA := y.inre.x;",
        "VAR\n    y : Yttre := (inre := (x := 42));\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Inre : STRUCT\n        x : INT;\n    END_STRUCT;\n"
        "    Yttre : STRUCT\n        inre : Inre;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "array_of_struct_var_initiering",
        "deklaration",
        "    iA := arr[1].x;",
        "VAR\n    arr : ARRAY[1..2] OF Punkt := [(x := 1, y := 2), (x := 3, y := 4)];\n    iA : INT;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    # ---- 7. Jämförelseoperatorer ----
    (
        "struct_likhet_jamforelse",
        "operator",
        "    bA := (p1 = p2);",
        "VAR\n    p1, p2 : Punkt;\n    bA : BOOL;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "struct_olikhet_jamforelse",
        "operator",
        "    bA := (p1 <> p2);",
        "VAR\n    p1, p2 : Punkt;\n    bA : BOOL;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "array_of_struct_likhet",
        "operator",
        "    bA := (arr1 = arr2);",
        "VAR\n    arr1, arr2 : ARRAY[1..2] OF Punkt;\n    bA : BOOL;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),

    # =========================================================================
    # VÅG 2: REF_TO, CASE, REPEAT, STRÄNGFUNKTIONER (fall 25..55)
    # =========================================================================
    # ---- 8. REF_TO och dereferensiering (^) ----
    (
        "ref_to_dekl_och_deref",
        "deklaration",
        "    pRef := REF(iA);\n    pRef^ := 42;\n    iB := pRef^;",
        "VAR\n    iA, iB : INT;\n    pRef : REF_TO INT;\nEND_VAR\n",
        "",
    ),
    (
        "ref_to_null_init",
        "deklaration",
        "    IF pRef = NULL THEN\n        iA := 1;\n    END_IF;",
        "VAR\n    iA : INT;\n    pRef : REF_TO INT := NULL;\nEND_VAR\n",
        "",
    ),
    (
        "ref_to_null_tilldelning",
        "deklaration",
        "    pRef := NULL;",
        "VAR\n    pRef : REF_TO INT;\nEND_VAR\n",
        "",
    ),
    (
        "ref_to_kopiering",
        "deklaration",
        "    pRef1 := REF(iA);\n    pRef2 := pRef1;\n    pRef2^ := 99;\n    iB := pRef1^;",
        "VAR\n    iA, iB : INT;\n    pRef1, pRef2 : REF_TO INT;\nEND_VAR\n",
        "",
    ),
    (
        "ref_to_struct_falt",
        "deklaration",
        "    rBox.refVal := REF(iA);\n    rBox.refVal^ := 100;",
        "VAR\n    iA : INT;\n    rBox : RefBox;\nEND_VAR\n",
        "TYPE\n    RefBox : STRUCT\n        refVal : REF_TO INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),

    # ---- 9. CASE-satser ----
    (
        "case_intervall_och_lista",
        "sats",
        "    CASE iA OF\n        1..5, 7: iB := 10;\n        ELSE iB := 20;\n    END_CASE;",
        None,
        "",
    ),
    (
        "case_overlappande_grenar",
        "sats",
        "    CASE iA OF\n        1..5: iB := 10;\n        3..7: iB := 20;\n        ELSE iB := 30;\n    END_CASE;",
        None,
        "",
    ),
    (
        "case_struct_falt",
        "sats",
        "    CASE p.x OF\n        1: iB := 10;\n        2: iB := 20;\n        ELSE iB := 30;\n    END_CASE;",
        "VAR\n    p : Punkt;\n    iB : INT;\nEND_VAR\n",
        "TYPE\n    Punkt : STRUCT\n        x : INT;\n    END_STRUCT;\nEND_TYPE\n",
    ),
    (
        "case_string",
        "sats",
        "    CASE sA OF\n        'abc': iB := 1;\n        'def': iB := 2;\n        ELSE iB := 3;\n    END_CASE;",
        None,
        "",
    ),

    # ---- 10. REPEAT...UNTIL ----
    (
        "repeat_basform",
        "sats",
        "    REPEAT\n        iA := iA + 1;\n    UNTIL iA > 5\n    END_REPEAT;",
        None,
        "",
    ),
    (
        "repeat_med_exit",
        "sats",
        "    REPEAT\n        iA := iA + 1;\n        IF iA = 3 THEN\n            EXIT;\n        END_IF;\n    UNTIL iA > 5\n    END_REPEAT;",
        None,
        "",
    ),
    (
        "repeat_nastlad",
        "sats",
        "    REPEAT\n        iA := iA + 1;\n        REPEAT\n            iB := iB + 1;\n        UNTIL iB > 3\n        END_REPEAT;\n    UNTIL iA > 5\n    END_REPEAT;",
        None,
        "",
    ),

    # ---- 11. Strängfunktioner på verdict-nivå mot backend ----
    (
        "string_concat_lit_lit",
        "funktion",
        "    sA := CONCAT('foo', 'bar');",
        None,
        "",
    ),
    (
        "string_concat_var_lit",
        "funktion",
        "    sA := CONCAT(sB, 'bar');",
        None,
        "",
    ),
    (
        "string_left_lit_lit",
        "funktion",
        "    sA := LEFT('abcdef', 3);",
        None,
        "",
    ),
    (
        "string_left_var_lit",
        "funktion",
        "    sA := LEFT(sB, 3);",
        None,
        "",
    ),
    (
        "string_right_lit_lit",
        "funktion",
        "    sA := RIGHT('abcdef', 3);",
        None,
        "",
    ),
    (
        "string_right_var_lit",
        "funktion",
        "    sA := RIGHT(sB, 3);",
        None,
        "",
    ),
    (
        "string_mid_lit_lit",
        "funktion",
        "    sA := MID('abcdef', 3, 2);",
        None,
        "",
    ),
    (
        "string_mid_var_lit",
        "funktion",
        "    sA := MID(sB, 3, 2);",
        None,
        "",
    ),
    (
        "string_find_lit_lit",
        "funktion",
        "    iA := FIND('abcdef', 'cd');",
        None,
        "",
    ),
    (
        "string_find_var_lit",
        "funktion",
        "    iA := FIND(sB, 'cd');",
        None,
        "",
    ),
    (
        "string_find_lit_var",
        "funktion",
        "    iA := FIND('abcdef', sB);",
        None,
        "",
    ),
    (
        "string_len_lit",
        "funktion",
        "    iA := LEN('abcdef');",
        None,
        "",
    ),
    (
        "string_len_var",
        "funktion",
        "    iA := LEN(sB);",
        None,
        "",
    ),
    (
        "string_insert_lit_lit",
        "funktion",
        "    sA := INSERT('abcdef', 'XYZ', 3);",
        None,
        "",
    ),
    (
        "string_insert_var_lit",
        "funktion",
        "    sA := INSERT(sB, 'XYZ', 3);",
        None,
        "",
    ),
    (
        "string_delete_lit",
        "funktion",
        "    sA := DELETE('abcdef', 2, 3);",
        None,
        "",
    ),
    (
        "string_delete_var",
        "funktion",
        "    sA := DELETE(sB, 2, 3);",
        None,
        "",
    ),
    (
        "string_replace_lit_lit",
        "funktion",
        "    sA := REPLACE('abcdef', 'XYZ', 2, 3);",
        None,
        "",
    ),
    (
        "string_replace_var_lit",
        "funktion",
        "    sA := REPLACE(sB, 'XYZ', 2, 3);",
        None,
        "",
    ),
]


def full_kalla(post):
    namn, _grupp, kropp, dekl, prolog = post
    if kropp is None:
        return prolog
    return kalla(kropp, dekl, prolog)


def lager_a(post, strucpp_paket, byggrot):
    """Lokal dom: vårt lager + STruC++ compile-API."""
    namn = post[0]
    text = full_kalla(post)
    try:
        rapport = validera(text)
        var_ok = bool(rapport.ok)
        var_fel = None if var_ok else str(rapport)[:300]
    except Exception as fel:
        return {"namn": namn, "var": None, "var_fel": "KRASCH: %r" % fel,
                "strucpp": None, "strucpp_fel": None}
    kat = os.path.join(byggrot, namn)
    try:
        P.kompilera(text, kat, strucpp_paket)
        return {"namn": namn, "var": var_ok, "var_fel": var_fel,
                "strucpp": True, "strucpp_fel": None}
    except (P.Byggfel, UnicodeEncodeError, OSError) as fel:
        return {"namn": namn, "var": var_ok, "var_fel": var_fel,
                "strucpp": False, "strucpp_fel": str(fel)[:300]}


def bygg_zip_for_openplc(post, strucpp_paket, runtime_include, byggrot):
    """Full källa + CONFIGURATION -> projekt.zip."""
    namn = post[0]
    text = full_kalla(post)
    if not text.strip():
        raise P.Byggfel("tom källa: inget att bygga")
    try:
        text.encode("ascii")
    except UnicodeEncodeError as fel:
        raise P.Byggfel("icke-ascii i källa: %s" % fel)
    conf = text + P.konfigurationstext("Main", intervall=P.TASKINTERVALL)
    kat = os.path.join(byggrot, namn + "_plc")
    zipvag, _ = P.bygg_projekt(conf, kat, strucpp_paket, runtime_include,
                               opcua_konfig=None)
    return zipvag


def lager_b_ett(post, klient, strucpp_paket, runtime_include, byggrot):
    """Ladda upp ETT fall till OpenPLC, läs tillbaka verdict."""
    namn = post[0]
    try:
        zipvag = bygg_zip_for_openplc(post, strucpp_paket, runtime_include, byggrot)
    except P.Byggfel as fel:
        return {"namn": namn, "openplc": None,
                "skal": "byggdes inte lokalt: %s" % str(fel)[:200]}
    try:
        klient.ladda_upp(zipvag)
        dom = klient.vanta_pa_kompilering(tidsgrans=120.0, paus=1.0)
        return {"namn": namn, "openplc": bool(dom.klar),
                "skal": dom.logg[-500:] if not dom.klar else ""}
    except OpenPlcFel as fel:
        return {"namn": namn, "openplc": False,
                "skal": "OpenPLC-fel: %s" % str(fel)[:500]}


def klassificera(rad, STRANGARE, LATTARE):
    """M-99 / M-108 klassificeringsregel."""
    namn = rad["namn"]
    v, s, o = rad.get("var"), rad.get("strucpp"), rad.get("openplc")
    if v is None or (o is None and s is None):
        return "EJ_KORD"
    if o is None:
        if v is False and s is False:
            return "TVAFALL"
        if v is True and s is False:
            return "LATTARE_OPROVAD"
        if v is False and s is True:
            return "STRANGARE_OPROVAD"
        return "EJ_KORD"
    if v == o:
        return "OVERENS"
    if not v and o:
        return ("STRANGARE_BEKRAFTAD" if namn in STRANGARE
                else "NY_STRANGARE")
    if v and not o:
        return ("HAL_BEKRAFTAD" if namn in LATTARE else "NYTT_HAL")
    return "EJ_KORD"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bas", default="https://127.0.0.1:18444")
    ap.add_argument("--anvandare", default="vcassist")
    ap.add_argument("--losenord", default="vcassist")
    ap.add_argument(
        "--strucpp-paket",
        default="/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/scratchpad/strucpp_npm/package")
    ap.add_argument(
        "--runtime-include",
        default="/tmp/opencode/m108/strucpp-bin/strucpp/runtime/include")
    ap.add_argument("--byggkatalog", default="/tmp/opencode/m108_r3v2/bygg")
    ap.add_argument("--no-upload", action="store_true",
                    help="endast lager A (inget nät, ingen container)")
    ap.add_argument("--trasig-fixtur", action="store_true",
                    help="ladda upp saboterat arkiv och kräv FAILED.")
    ap.add_argument("--json", default="/tmp/opencode/m108_r3v2/r3_verdict.json")
    a = ap.parse_args(argv)

    STRANGARE, LATTARE = _las_svep_avvikelser()
    fall = FALL_R3
    print("M-108 R3-svep: %d fall" % len(fall))

    byggrot = a.byggkatalog
    os.makedirs(byggrot, exist_ok=True)

    # ---- lager A: lokalt ----
    t0 = time.time()
    rader = {}

    def _a(p):
        return lager_a(p, a.strucpp_paket, byggrot)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for rad in pool.map(_a, fall):
            rader[rad["namn"]] = rad
    print("lager A klart: %d fall på %.1f s" % (len(rader), time.time() - t0))

    def _trasig_fixtur(klient):
        """Saboterad C++ måste ge FAILED."""
        import zipfile
        post = fall[0]
        zipvag = bygg_zip_for_openplc(post, a.strucpp_paket,
                                      a.runtime_include, byggrot)
        trasig = os.path.join(byggrot, "trasig.zip")
        with zipfile.ZipFile(zipvag) as zin, \
                zipfile.ZipFile(trasig, "w",
                                compression=zipfile.ZIP_DEFLATED) as zut:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename.endswith(".cpp"):
                    data += b"\nTHIS IS NOT C++;\n"
                zut.writestr(info, data)
        klient.ladda_upp(trasig)
        try:
            klient.vanta_pa_kompilering(tidsgrans=60.0, paus=1.0)
        except OpenPlcFel:
            print("trasig fixtur: saboterat arkiv föll som väntat")
            return True
        print("FEL: saboterat arkiv ACCEPTERADES - verdict-mätningen mäter inte kompilering.")
        return False

    # ---- lager B: mot OpenPLC m108 container ----
    if not a.no_upload:
        if not a.runtime_include:
            print("FEL: lager B kräver --runtime-include")
            return 2
        try:
            klient = OpenPlcV4(a.bas, a.anvandare, a.losenord,
                               tillat_osignerat=True)
            print("runtime: %s status: %s"
                  % (klient.version(), klient.status()))
        except OpenPlcFel as fel:
            print("FEL: OpenPLC svarar inte: %s" % fel)
            print("En OpenPLC som inte svarar får aldrig ge tyst grönt.")
            return 1
        if a.trasig_fixtur:
            return 0 if _trasig_fixtur(klient) else 1

        post_av_namn = {p[0]: p for p in fall}
        for k, namn in enumerate(sorted(post_av_namn)):
            rad = lager_b_ett(post_av_namn[namn], klient,
                              a.strucpp_paket, a.runtime_include, byggrot)
            rader[namn].update(rad)
            if (k + 1) % 5 == 0 or (k + 1) == len(post_av_namn):
                print("  ... %d/%d uppladdade" % (k + 1, len(post_av_namn)))

    for rad in rader.values():
        rad["klass"] = klassificera(rad, STRANGARE, LATTARE)

    klasser: dict = {}
    for rad in rader.values():
        klasser[rad["klass"]] = klasser.get(rad["klass"], 0) + 1
    print("\nKlassammanställning: %s" % json.dumps(klasser, sort_keys=True))

    print("\nResultat per fall:")
    print("%-36s | %-5s | %-7s | %-7s | %-16s" % ("NAMN", "VAR", "STRUCPP", "OPENPLC", "KLASS"))
    print("-" * 80)
    for rad in sorted(rader.values(), key=lambda r: r["namn"]):
        print("%-36s | %-5s | %-7s | %-7s | %-16s" % (
            rad["namn"],
            str(rad.get("var")),
            str(rad.get("strucpp")),
            str(rad.get("openplc")),
            rad["klass"]
        ))

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({
                "bankpost": BANKPOST,
                "fall": rader,
                "klasser": klasser,
                "utforare": "gemini-1",
            }, fh, indent=2, ensure_ascii=False, sort_keys=True)
        print("\nJSON sparad till: %s" % a.json)

    # Exit: EJ_KORD eller nya avvikelser = skarp signal (fail-closed)
    if klasser.get("EJ_KORD"):
        print("EJ_KORD finns: ena sidan kördes inte. Inte överens.")
        return 1
    if klasser.get("NY_STRANGARE") or klasser.get("NYTT_HAL"):
        print("NYA avvikelser hittades (NY_STRANGARE / NYTT_HAL): kräver IEC-bedömning (exit 1).")
        return 1
    print("INGA nya avvikelser i R3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
