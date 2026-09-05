# -*- coding: utf-8 -*-
"""L1: svepet. Varje ST-konstruktion genom BADA grindarna, och en facitrad
per konstruktion for hur de tva far skilja sig at.

Provet finns darfor att en FALSK RODGRIND ar dyr. Grind 2 och 3 - vart eget
ST-lager - kor FORE grind 1 i `stationsgrind.granska_station`, och med
`stanna_vid_forsta` far kompilatorn aldrig ens se koden nar vart lager
avvisar den. En modell som far tillbaka ett fel som inte finns brinner
reparationsvarv pa att laga nagot som redan fungerade, och lar sig fel sak.

M-48 matte fjorton konstruktioner och hittade tre avvikelser. Fjorton ar ett
stickprov. M-51 svepte 185 och lagade fem klasser av falsk rodgrind; det som
star kvar star kvar MED SKAL, en rad per fall i tabellerna nedan.

Tva forbehall om facit, bada matta i M-51:

* **STruC++:s framande ar ingen namnauktoritet.** `HITTEPA(x)` gar igenom den
  utan anmarkning; namnet faller forst nar g++ ser den genererade C++:en.
  Ett svep som bara kor framande hade darfor "bevisat" att `NOW()` finns.
  Namnen provas separat, med `--build`, i sista provet i filen.
* **Kompilatorn ar inte strangare an oss.** Den godkanner `iA := rA`, index
  utanfor faltets granser och `T#5s10m`. Att var grind fallr dem ar hela
  skalet att den finns, och sadana fall star som STRANGARE nedan - aldrig som
  fel.

Kompilatorn ligger inte i repot (skuld, oppen sedan M-48). Provet hoppar over
sig sjalvt med ett uttalat skal nar den saknas; ett svep utan facit vore ett
tyst gront.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import stdbibliotek as SB          # noqa: E402
from vc_assist_svc.st import typer as T                  # noqa: E402
from vc_assist_svc.st import validera                    # noqa: E402


# ---- att hitta kompilatorn ----------------------------------------------

def hitta_strucpp():
    """STruC++:s CLI, eller None.

    Sokordningen ar uttalad: miljovariabeln forst, PATH sedan. Ingen
    gissning pa sessionskataloger - en sokvag som rakar finnas pa EN maskin
    ar inte ett facit, den ar en tillfallighet.
    """
    ur_miljon = os.environ.get("VC_ASSIST_STRUCPP")
    if ur_miljon and os.path.isfile(ur_miljon) and os.access(ur_miljon, os.X_OK):
        return ur_miljon
    return shutil.which("strucpp")


STRUCPP = hitta_strucpp()
GPP = shutil.which("g++")

SKAL_UTAN_CLI = (
    "STruC++ hittades inte, och svepet mater vart ST-lager MOT den riktiga "
    "kompilatorn. Utan facit finns ingen matning. Peka ut den med "
    "VC_ASSIST_STRUCPP=<sokvag till strucpp> eller lagg den i PATH.")

pytestmark = pytest.mark.skipif(STRUCPP is None, reason=SKAL_UTAN_CLI)


# ---- konstruktionerna ----------------------------------------------------
#
# Ett gemensamt deklarationsblock, sa att varje fall bara behover bara sin
# egen konstruktion. STRING star utan langd med avsikt: STRING[n] bygger inte
# i STruC++ 0.6.6 och skulle ha forgiftat samtliga fall (det gjorde det ocksa
# i forsta korningen av svepet, och alla 131 sag ut att avvika).

DEKL = """\
VAR
    bA, bB, bC : BOOL;
    iA, iB, iC : INT;
    dA : DINT;
    rA, rB : REAL;
    lrA : LREAL;
    wA : WORD;
    byA : BYTE;
    tA, tB : TIME;
    sA : STRING;
    ton1 : TON;
    tof1 : TOF;
    tp1 : TP;
    rt1 : R_TRIG;
    ft1 : F_TRIG;
    ctu1 : CTU;
    ctd1 : CTD;
    ctud1 : CTUD;
    sr1 : SR;
    rs1 : RS;
    arr : ARRAY[1..10] OF INT;
END_VAR
"""


def kalla(kropp, dekl=None, prolog=""):
    return "%sPROGRAM Main\n%s%s\nEND_PROGRAM\n" % (
        prolog, DEKL if dekl is None else dekl, kropp)


FALL = []


def f(namn, grupp, kropp, dekl=None, prolog=""):
    FALL.append((namn, grupp, kropp, dekl, prolog))


# ---- 1. satsformer -------------------------------------------------------
f("tilldelning", "sats", "    bA := bB;")
f("if_then", "sats", "    IF bA THEN\n        bB := TRUE;\n    END_IF;")
f("if_else", "sats", "    IF bA THEN\n        bB := TRUE;\n    ELSE\n        bB := FALSE;\n    END_IF;")
f("if_elsif_else", "sats",
  "    IF bA THEN\n        iA := 1;\n    ELSIF bB THEN\n        iA := 2;\n"
  "    ELSE\n        iA := 3;\n    END_IF;")
f("if_nastlad", "sats",
  "    IF bA THEN\n        IF bB THEN\n            iA := 1;\n        END_IF;\n    END_IF;")
f("case_enkel", "sats",
  "    CASE iA OF\n        1: bA := TRUE;\n        2: bA := FALSE;\n    END_CASE;")
f("case_med_else", "sats",
  "    CASE iA OF\n        1: bA := TRUE;\n    ELSE\n        bA := FALSE;\n    END_CASE;")
f("case_omrade", "sats",
  "    CASE iA OF\n        1..5: bA := TRUE;\n        6..9: bA := FALSE;\n    END_CASE;")
f("case_kommalista", "sats",
  "    CASE iA OF\n        1, 3, 5: bA := TRUE;\n        2, 4: bA := FALSE;\n    END_CASE;")
f("case_negativ_etikett", "sats",
  "    CASE iA OF\n        -3: bA := TRUE;\n        0: bA := FALSE;\n    END_CASE;")
f("while", "sats", "    WHILE iA < 10 DO\n        iA := iA + 1;\n    END_WHILE;")
f("repeat", "sats", "    REPEAT\n        iA := iA + 1;\n    UNTIL iA > 10\n    END_REPEAT;")
f("for", "sats", "    FOR iA := 1 TO 10 DO\n        iB := iB + 1;\n    END_FOR;")
f("for_by", "sats", "    FOR iA := 1 TO 10 BY 2 DO\n        iB := iB + 1;\n    END_FOR;")
f("for_by_negativ", "sats", "    FOR iA := 10 TO 1 BY -1 DO\n        iB := iB + 1;\n    END_FOR;")
f("exit_i_slinga", "sats",
  "    WHILE bA DO\n        IF bB THEN\n            EXIT;\n        END_IF;\n    END_WHILE;")
f("return", "sats", "    IF bA THEN\n        RETURN;\n    END_IF;")
f("tom_sats_semikolon", "sats", "    ;")
f("tom_kropp", "sats", "")

# ---- 2. semikolon efter blockslut ---------------------------------------
f("end_if_utan_semikolon", "semikolon", "    IF bA THEN\n        bB := TRUE;\n    END_IF")
f("end_case_utan_semikolon", "semikolon",
  "    CASE iA OF\n        1: bA := TRUE;\n    END_CASE")
f("end_while_utan_semikolon", "semikolon",
  "    WHILE iA < 10 DO\n        iA := iA + 1;\n    END_WHILE")
f("end_repeat_utan_semikolon", "semikolon",
  "    REPEAT\n        iA := iA + 1;\n    UNTIL iA > 10\n    END_REPEAT")
f("end_for_utan_semikolon", "semikolon",
  "    FOR iA := 1 TO 10 DO\n        iB := iB + 1;\n    END_FOR")
f("end_if_utan_semikolon_mitt_i", "semikolon",
  "    IF bA THEN\n        bB := TRUE;\n    END_IF\n    iA := 1;")
f("end_var_med_semikolon", "semikolon", "    bA := bB;",
  dekl="VAR\n    bA, bB : BOOL;\nEND_VAR;\n")

# ---- 3. literaler --------------------------------------------------------
f("tid_t_ms", "literal", "    tA := T#500ms;")
f("tid_t_sammansatt", "literal", "    tA := T#1d2h3m4s5ms;")
f("tid_time_prefix", "literal", "    tA := TIME#1s;")
f("tid_negativ", "literal", "    tA := T#-2h;")
f("tid_decimal", "literal", "    tA := T#1.5h;")
f("hex", "literal", "    iA := 16#7F;")
f("oktal", "literal", "    iA := 8#77;")
f("binar", "literal", "    iA := 2#1010;")
f("understreck_i_tal", "literal", "    dA := 1_000_000;")
f("exponent_e", "literal", "    rA := 1.5e3;")
f("exponent_stor_e_negativ", "literal", "    rA := 1.0E-3;")
f("real_typad", "literal", "    rA := REAL#1.5;")
f("int_typad", "literal", "    iA := INT#5;")
f("word_typad_hex", "literal", "    wA := WORD#16#FF;")
f("bool_typad", "literal", "    bA := BOOL#1;")
f("strang", "literal", "    sA := 'hej';")
f("strang_dollarkod", "literal", "    sA := 'rad$R$L';")
f("strang_dollar_hex", "literal", "    sA := 'a$41b';")
f("sann_falsk", "literal", "    bA := TRUE;\n    bB := FALSE;")
f("datum_literal", "literal", "    dt := DATE#2026-01-01;",
  dekl="VAR\n    dt : DATE;\nEND_VAR\n")
f("tid_pa_dagen_literal", "literal", "    tod := TOD#12:00:00;",
  dekl="VAR\n    tod : TIME_OF_DAY;\nEND_VAR\n")
f("negativt_heltal", "literal", "    iA := -5;")

# ---- 4. operatorer och prioritet ----------------------------------------
f("prioritet_plus_gange", "operator", "    iA := iB + iC * 2;")
f("prioritet_parentes", "operator", "    iA := (iB + iC) * 2;")
f("prioritet_not_and", "operator", "    bA := NOT bB AND bC;")
f("prioritet_and_or", "operator", "    bA := bB AND bC OR bA;")
f("ampersand_and", "operator", "    bA := bB & bC;")
f("xor", "operator", "    bA := bB XOR bC;")
f("mod", "operator", "    iA := iB MOD 3;")
f("division", "operator", "    rA := rB / 2.0;")
f("jamforelser", "operator", "    bA := (iA = iB) OR (iA <> iC);")
f("mindre_storre_lika", "operator", "    bA := (iA <= iB) AND (iA >= iC);")
f("exponent_operator", "operator", "    rA := rB ** 2.0;")
f("unart_minus", "operator", "    iA := -iB;")
f("unart_plus", "operator", "    iA := +iB;")
f("tid_plus_tid", "operator", "    tA := tB + T#1s;")
f("tid_gange_tal", "operator", "    tA := tB * 2;")

# ---- 5. standardfunktionsblock ------------------------------------------
f("ton_namngivet", "block", "    ton1(IN := bA, PT := T#1s);\n    bB := ton1.Q;")
f("ton_positionellt", "block", "    ton1(bA, T#1s);\n    bB := ton1.Q;")
f("ton_et", "block", "    ton1(IN := bA, PT := T#1s);\n    tA := ton1.ET;")
f("tof", "block", "    tof1(IN := bA, PT := T#1s);\n    bB := tof1.Q;")
f("tp", "block", "    tp1(IN := bA, PT := T#1s);\n    bB := tp1.Q;")
f("r_trig", "block", "    rt1(CLK := bA);\n    bB := rt1.Q;")
f("f_trig", "block", "    ft1(CLK := bA);\n    bB := ft1.Q;")
f("ctu", "block", "    ctu1(CU := bA, R := bB, PV := 10);\n    bC := ctu1.Q;\n    iA := ctu1.CV;")
f("ctd", "block", "    ctd1(CD := bA, LD := bB, PV := 10);\n    bC := ctd1.Q;")
f("ctud", "block", "    ctud1(CU := bA, CD := bB, R := bC, LD := bA, PV := 10);\n    iA := ctud1.CV;")
f("sr", "block", "    sr1(S1 := bA, R := bB);\n    bC := sr1.Q1;")
f("rs", "block", "    rs1(S := bA, R1 := bB);\n    bC := rs1.Q1;")
f("block_utgang_pil", "block", "    ton1(IN := bA, PT := T#1s, Q => bB);")

# ---- 6. standardfunktioner ----------------------------------------------
f("abs", "funktion", "    iA := ABS(iB);")
f("sqrt", "funktion", "    rA := SQRT(rB);")
f("min", "funktion", "    iA := MIN(iB, iC);")
f("max_tre", "funktion", "    iA := MAX(iB, iC, 3);")
f("limit", "funktion", "    iA := LIMIT(0, iB, 100);")
f("sel", "funktion", "    iA := SEL(bA, iB, iC);")
f("mux", "funktion", "    iA := MUX(iB, 1, 2, 3);")
f("trunc", "funktion", "    dA := TRUNC(rA);")
f("shl", "funktion", "    wA := SHL(wA, 2);")
f("shr", "funktion", "    wA := SHR(wA, 2);")
f("rol", "funktion", "    wA := ROL(wA, 2);")
f("ror", "funktion", "    wA := ROR(wA, 2);")
f("len", "funktion", "    iA := LEN(sA);")
f("int_to_real", "funktion", "    rA := INT_TO_REAL(iA);")
f("real_to_int", "funktion", "    iA := REAL_TO_INT(rA);")
f("bool_to_int", "funktion", "    iA := BOOL_TO_INT(bA);")
f("time_to_dint", "funktion", "    dA := TIME_TO_DINT(tA);")
f("expt", "funktion", "    rA := EXPT(rB, 2.0);")
f("ln", "funktion", "    rA := LN(rB);")
f("log", "funktion", "    rA := LOG(rB);")
f("exp", "funktion", "    rA := EXP(rB);")
f("sin", "funktion", "    rA := SIN(rB);")
f("cos", "funktion", "    rA := COS(rB);")
f("atan", "funktion", "    rA := ATAN(rB);")
f("add_funktion", "funktion", "    iA := ADD(iB, iC);")
f("mul_funktion", "funktion", "    iA := MUL(iB, iC);")
f("concat", "funktion", "    sA := CONCAT('a', 'b');")
f("left_strang", "funktion", "    sA := LEFT(sA, 2);")
f("mid_strang", "funktion", "    sA := MID(sA, 2, 1);")
f("find_strang", "funktion", "    iA := FIND(sA, 'a');")
f("time_funktion", "funktion", "    bA := tA > TIME();")

# ---- 7. kommentarer och pragma ------------------------------------------
f("kommentar_block", "kommentar", "    (* en kommentar *)\n    bA := bB;")
f("kommentar_radslut", "kommentar", "    bA := bB; // en kommentar")
f("kommentar_dubbelsnedstreck_egen_rad", "kommentar", "    // en kommentar\n    bA := bB;")
f("kommentar_nastlad", "kommentar", "    (* yttre (* inre *) yttre *)\n    bA := bB;")
f("kommentar_flerradig", "kommentar", "    (* rad ett\n       rad tva *)\n    bA := bB;")
f("pragma", "kommentar", "    {attribute} \n    bA := bB;")

# ---- 8. deklarationsformer ----------------------------------------------
f("var_med_startvarde", "deklaration", "    bA := bB;",
  dekl="VAR\n    bA : BOOL := FALSE;\n    bB : BOOL := TRUE;\nEND_VAR\n")
f("var_constant", "deklaration", "    iA := GRANS;",
  dekl="VAR CONSTANT\n    GRANS : INT := 10;\nEND_VAR\nVAR\n    iA : INT;\nEND_VAR\n")
f("var_flera_namn_en_rad", "deklaration", "    bA := bB;",
  dekl="VAR\n    bA, bB, bC : BOOL;\nEND_VAR\n")
f("var_falt", "deklaration", "    arr[1] := 5;",
  dekl="VAR\n    arr : ARRAY[1..10] OF INT;\nEND_VAR\n")
f("var_falt_tva_dim", "deklaration", "    arr[1,2] := 5;",
  dekl="VAR\n    arr : ARRAY[1..10, 1..10] OF INT;\nEND_VAR\n")
f("var_string_langd", "deklaration", "    sA := 'x';",
  dekl="VAR\n    sA : STRING[20];\nEND_VAR\n")
f("var_string_utan_langd", "deklaration", "    sA := 'x';",
  dekl="VAR\n    sA : STRING;\nEND_VAR\n")
f("struct_typ", "deklaration", "    p.x := 1;",
  dekl="VAR\n    p : Punkt;\nEND_VAR\n",
  prolog="TYPE\n    Punkt : STRUCT\n        x : INT;\n        y : INT;\n    END_STRUCT;\nEND_TYPE\n")
f("egen_funktionsblock", "deklaration", "    fb1(IN := bA);\n    bB := fb1.UT;",
  dekl="VAR\n    fb1 : Egen;\n    bA, bB : BOOL;\nEND_VAR\n",
  prolog="FUNCTION_BLOCK Egen\nVAR_INPUT\n    IN : BOOL;\nEND_VAR\n"
         "VAR_OUTPUT\n    UT : BOOL;\nEND_VAR\n    UT := IN;\nEND_FUNCTION_BLOCK\n")
f("egen_funktion", "deklaration", "    iA := Dubbla(iB);",
  dekl="VAR\n    iA, iB : INT;\nEND_VAR\n",
  prolog="FUNCTION Dubbla : INT\nVAR_INPUT\n    v : INT;\nEND_VAR\n"
         "    Dubbla := v * 2;\nEND_FUNCTION\n")
f("var_at_adress", "deklaration", "    bA := bB;",
  dekl="VAR\n    bA AT %QX0.0 : BOOL;\n    bB AT %IX0.0 : BOOL;\nEND_VAR\n")
f("var_global", "deklaration", "    bA := TRUE;",
  dekl="VAR_EXTERNAL\n    bA : BOOL;\nEND_VAR\n",
  prolog="VAR_GLOBAL\n    bA : BOOL;\nEND_VAR\n")
f("var_temp", "deklaration", "    bA := TRUE;",
  dekl="VAR_TEMP\n    bA : BOOL;\nEND_VAR\n")
f("var_retain", "deklaration", "    bA := TRUE;",
  dekl="VAR RETAIN\n    bA : BOOL;\nEND_VAR\n")

# ---- 9. skiftlage och blanksteg -----------------------------------------
f("gemener_nyckelord", "form", "    if bA then\n        bB := TRUE;\n    end_if;")
f("blandat_skiftlage_namn", "form", "    BA := bB;",
  dekl="VAR\n    bA, bB : BOOL;\nEND_VAR\n")
f("allt_pa_en_rad", "form", "    IF bA THEN bB := TRUE; END_IF;")
f("extra_blankrader", "form", "\n\n    bA := bB;\n\n")

# ---- 10. former som SKA falla (jakten pa falsk gron) --------------------
f("if_utan_end_if", "trasig", "    IF bA THEN\n        bB := TRUE;")
f("case_utan_grenar", "trasig", "    CASE iA OF\n    END_CASE;")
f("tva_else", "trasig",
  "    IF bA THEN\n        iA := 1;\n    ELSE\n        iA := 2;\n"
  "    ELSE\n        iA := 3;\n    END_IF;")
f("odeklarerat_namn", "trasig", "    bA := hittepa;")
f("odeklarerat_skrivmal", "trasig", "    hittepa := TRUE;")
f("fel_end_ord", "trasig", "    IF bA THEN\n        bB := TRUE;\n    END_WHILE;")
f("int_far_real", "trasig", "    iA := rA;")
f("bool_far_int", "trasig", "    bA := iA;")
f("time_far_int", "trasig", "    tA := iA;")
f("dint_far_lint", "trasig", "    dA := lA;",
  dekl="VAR\n    dA : DINT;\n    lA : LINT;\nEND_VAR\n")
f("literal_over_int", "trasig", "    iA := 40000;")
f("jamfor_bool_med_int", "trasig", "    bA := (bB = iA);")
f("if_pa_heltal", "trasig", "    IF iA THEN\n        bA := TRUE;\n    END_IF;")
f("for_pa_real", "trasig", "    FOR rA := 1.0 TO 2.0 DO\n        iA := 1;\n    END_FOR;")
f("skriv_till_constant", "trasig", "    GRANS := 5;",
  dekl="VAR CONSTANT\n    GRANS : INT := 10;\nEND_VAR\n")
f("exit_utanfor_slinga", "trasig", "    EXIT;")
f("for_manga_argument", "trasig", "    iA := ABS(iB, iC);")
f("okant_argumentnamn", "trasig", "    ton1(IN := bA, PT := T#1s, HITTEPA := 1);")
f("blockinstans_i_uttryck", "trasig", "    bA := ton1(IN := bB, PT := T#1s);")
f("blocktyp_anropad_direkt", "trasig", "    TON(IN := bA, PT := T#1s);")
f("okant_falt_pa_block", "trasig", "    ton1(IN := bA, PT := T#1s);\n    bB := ton1.HITTEPA;")
f("index_utanfor_granser", "trasig", "    arr[99] := 1;")
f("fel_antal_index", "trasig", "    arr[1,2] := 1;")
f("hex_med_ogiltig_siffra", "trasig", "    iA := 16#GG;")
f("tid_fel_ordning", "trasig", "    tA := T#5s10m;")
f("tid_utan_enhet", "trasig", "    tA := T#500;")
f("okommenterad_kommentar", "trasig", "    (* aldrig avslutad\n    bA := bB;")
f("oavslutad_strang", "trasig", "    sA := 'aldrig slut;")
f("icke_ascii", "trasig", "    bA := bB; // h\u00e4r \u00e4r \u00e5")
f("bas_som_inte_finns", "trasig", "    iA := 3#12;")
f("ingen_pou", "trasig", "", dekl="", prolog="")

# ---- 11. fler giltiga former --------------------------------------------
f("tva_pouer", "form", "    bA := bB;",
  dekl="VAR\n    bA, bB : BOOL;\nEND_VAR\n",
  prolog="FUNCTION_BLOCK Extra\nVAR_INPUT\n    x : BOOL;\nEND_VAR\n"
         "VAR_OUTPUT\n    y : BOOL;\nEND_VAR\n    y := x;\nEND_FUNCTION_BLOCK\n")
f("funktion_med_lokala_var", "form", "    iA := Summa(1, 2);",
  dekl="VAR\n    iA : INT;\nEND_VAR\n",
  prolog="FUNCTION Summa : INT\nVAR_INPUT\n    a : INT;\n    b : INT;\nEND_VAR\n"
         "VAR\n    t : INT;\nEND_VAR\n    t := a + b;\n    Summa := t;\nEND_FUNCTION\n")
f("var_in_out", "form", "    vx(v := iA);",
  dekl="VAR\n    iA : INT;\n    vx : Vaxlare;\nEND_VAR\n",
  prolog="FUNCTION_BLOCK Vaxlare\nVAR_IN_OUT\n    v : INT;\nEND_VAR\n"
         "    v := v + 1;\nEND_FUNCTION_BLOCK\n")
f("namngivet_funktionsargument", "form", "    iA := ABS(IN := iB);")
f("djupt_nastlat", "form",
  "    IF bA THEN\n     IF bB THEN\n      IF bC THEN\n       IF bA THEN\n"
  "        IF bB THEN\n         iA := 1;\n        END_IF;\n       END_IF;\n"
  "      END_IF;\n     END_IF;\n    END_IF;")
f("ledande_understreck", "form", "    _a := TRUE;",
  dekl="VAR\n    _a : BOOL;\nEND_VAR\n")
f("langt_namn", "form", "    ett_mycket_langt_variabelnamn_som_ingen_skulle_skriva := TRUE;",
  dekl="VAR\n    ett_mycket_langt_variabelnamn_som_ingen_skulle_skriva : BOOL;\nEND_VAR\n")
f("falt_negativa_granser", "form", "    n[-3] := 1;",
  dekl="VAR\n    n : ARRAY[-5..5] OF INT;\nEND_VAR\n")
f("falt_av_bool", "form", "    fb[1] := TRUE;",
  dekl="VAR\n    fb : ARRAY[1..4] OF BOOL;\nEND_VAR\n")
f("struct_i_struct", "form", "    y.inre.x := 1;",
  dekl="VAR\n    y : Yttre;\nEND_VAR\n",
  prolog="TYPE\n    Inre : STRUCT\n        x : INT;\n    END_STRUCT;\n"
         "    Yttre : STRUCT\n        inre : Inre;\n    END_STRUCT;\nEND_TYPE\n")
f("startvarde_pa_tid", "form", "    tB := tA;",
  dekl="VAR\n    tA : TIME := T#1s;\n    tB : TIME;\nEND_VAR\n")
f("strang_med_apostrof", "form", "    sA := 'det$'s';")
f("exponent_med_variabler", "form", "    rA := rB ** rA;")
f("exponent_heltal", "form", "    iA := iB ** 2;")
f("exponent_prioritet", "form", "    rA := 2.0 * rB ** 2.0;")
f("typad_hex_int", "form", "    iA := INT#16#7F;")
f("typad_binar_byte", "form", "    byA := BYTE#2#1010;")
f("mux_bool", "form", "    bA := MUX(iA, TRUE, FALSE);")
f("sel_tid", "form", "    tA := SEL(bA, T#1s, T#2s);")
f("jamforelsefunktion", "form", "    bA := GT(iA, iB);")
f("strangfunktion_kedja", "form", "    sA := CONCAT(LEFT(sA, 2), RIGHT(sA, 2));")
f("move", "form", "    iA := MOVE(iB);")
f("sub_div", "form", "    iA := DIV(SUB(iB, 1), 2);")

# ---- 12. M-99:s axlar ---------------------------------------------------
#
# M-51 svepte 185 konstruktioner och missade skiftlage; M-96 hittade det
# felet i drift och bokforde nio av sexton grinddomar som VART fel. M-99
# svepte 394 konstruktioner till, axel for axel, och de fall som bar ett
# fynd eller en dom star har sa att de fortsatter matas.

# skiftlage pa allt som inte var provat
f("skift_typnamn_gemener", "form", "    v := v;",
  dekl="VAR\n    v : int;\nEND_VAR\n")
f("skift_var_gemener", "form", "    bA := TRUE;",
  dekl="var\n    bA : BOOL;\nend_var\n")
f("skift_program_gemener", "form", None, None,
  "program Main\nVAR\n    bA : BOOL;\nEND_VAR\n    bA := TRUE;\nend_program\n")
f("skift_fbnamn_gemener", "form", "    t1(IN := bA, PT := T#1s);",
  dekl="VAR\n    t1 : ton;\n    bA : BOOL;\nEND_VAR\n")
f("skift_funknamn_gemener", "form", "    iA := abs(iB);")
f("skift_blockparam_gemener", "form",
  "    ton1(in := bA, pt := T#1s);\n    bB := ton1.q;")
f("skift_literalprefix_gemener", "form", "    wA := word#16#ff;")
f("skift_adress_gemener", "form", "    bA := bB;",
  dekl="VAR\n    bA : BOOL;\n    bB at %ix0.0 : BOOL;\nEND_VAR\n")
f("skift_true_gemener", "form", "    bA := true;\n    bB := false;")
f("skift_struct_gemener", "form", "    p.x := 1;",
  dekl="VAR\n    p : Punkt;\nEND_VAR\n",
  prolog="type\n    Punkt : struct\n        x : INT;\n    end_struct;\nend_type\n")

# tidsliteraler utover skiftlage
f("tid_noll", "literal", "    tA := T#0s;")
f("tid_versal_sammansatt", "literal", "    tA := T#1D2H3M4S5MS;")
f("tid_understreck", "literal", "    tA := T#1_000ms;")
f("tid_us_ns", "literal", "    tA := T#500us;\n    tB := T#100ns;")
f("tid_dubbel_enhet", "trasig", "    tA := T#5s5s;")
f("tid_decimal_i_fel_del", "trasig", "    tA := T#1.5h30m;")

# blanksteg och radbrytningar
f("blank_radbrytning_i_tilldelning", "form", "    bA :=\n        bB;")
f("blank_tabbar", "form", "\tbA\t:=\tbB;")
f("blank_runt_punktpunkt", "form",
  "    CASE iA OF\n        1 .. 5: bA := TRUE;\n    END_CASE;")
f("blank_crlf", "form", "    bA := bB;\r\n    iA := 1;")
f("blank_sidmatning", "form", "    bA := bB;\x0c\n    iA := 1;")
f("blank_vertikaltabb", "form", "    bA := bB;\x0b\n    iA := 1;")
f("blank_i_anrop", "form", "    ton1 ( IN := bA , PT := T#1s ) ;")
f("blank_i_index", "form", "    arr [ 1 ] := 5;")
f("blank_radbrytning_i_villkor", "form",
  "    IF bA\n       AND bB\n    THEN\n        bC := TRUE;\n    END_IF;")

# kommentarer
f("kommentar_mitt_i_uttryck", "kommentar", "    iA := iB (* mitt i *) + iC;")
f("kommentar_mitt_i_tilldelning", "kommentar", "    bA (* x *) := (* y *) bB;")
f("kommentar_rad_mitt_i_uttryck", "kommentar", "    iA := iB + // hej\n        iC;")
f("kommentar_djupt_nastlad", "kommentar",
  "    (* a (* b (* c *) b *) a *)\n    bA := bB;")
f("kommentar_efter_end_if", "kommentar",
  "    IF bA THEN\n        bB := TRUE;\n    END_IF (* x *);")
f("kommentarstart_i_strang", "form", "    sA := 'a(*b';")

# talformer
f("tal_int_minsta", "literal", "    iA := -32768;")
f("tal_dint_minsta", "literal", "    dA := -2147483648;")
f("tal_negativ_noll", "literal", "    iA := -0;")
f("tal_understreck_i_realdel", "form", "    rA := 1_000.5;")
f("tal_exponent_utan_punkt", "literal", "    rA := 1E3;")
f("tal_int_over_omradet_negativt", "trasig", "    iA := -32769;")
f("tal_real_utan_brakdel", "trasig", "    rA := 1.;")
f("tal_real_punkt_fore_exponent", "trasig", "    rA := 1.e3;")

# strangar
f("strang_dollar_N", "literal", "    sA := 'a$Nb';")
f("strang_dollar_hex_52", "literal", "    sA := 'a$52b';")
f("strang_dollarcitat", "form", "    sA := 'a$\"b';")
f("strang_over_radbrytning", "trasig", "    sA := 'a\nb';")

# uttrycksformer
f("uttryck_atta_parenteser", "form", "    iA := ((((((((iB))))))));")
f("uttryck_not_not", "form", "    bA := NOT NOT bB;")
f("uttryck_dubbelt_unart_minus", "form", "    iA := - -iB;")
f("uttryck_jamforelse_utan_parentes", "form", "    bA := iA < iB = TRUE;")
f("uttryck_exponent_hogerassociativ", "form", "    rA := 2.0 ** 3.0 ** 2.0;")
f("uttryck_kedjetilldelning", "trasig", "    iA := iB := iC;")
f("uttryck_index_ar_uttryck", "form", "    arr[iA + 1] := 5;")

# deklarationsformer
f("dekl_adress_bool_pa_bitadress", "deklaration", "    bA := bB;",
  dekl="VAR\n    bA AT %QX0.0 : BOOL;\n    bB : BOOL;\nEND_VAR\n")
f("dekl_adress_int_pa_ordadress", "deklaration", "    n := 1;",
  dekl="VAR\n    n AT %QW1 : INT;\nEND_VAR\n")
f("dekl_adress_real_pa_dubbelordadress", "deklaration", "    r := 1.0;",
  dekl="VAR\n    r AT %MD4 : REAL;\nEND_VAR\n")
f("dekl_adress_bool_pa_ordadress", "trasig", "    bA := bA;",
  dekl="VAR\n    bA AT %QW1 : BOOL;\nEND_VAR\n")
f("dekl_adress_int_pa_bitadress", "trasig", "    n := 1;",
  dekl="VAR\n    n AT %IX0.0 : INT;\nEND_VAR\n")
f("dekl_falt_omvand_grans", "trasig", "    a[1] := 1;",
  dekl="VAR\n    a : ARRAY[10..1] OF INT;\nEND_VAR\n")
f("dekl_retain_constant", "trasig", "    iA := G;",
  dekl="VAR RETAIN CONSTANT\n    G : INT := 1;\nEND_VAR\n"
       "VAR\n    iA : INT;\nEND_VAR\n")
f("dekl_faltinitiering", "deklaration", "    iA := a[1];",
  dekl="VAR\n    a : ARRAY[1..3] OF INT := [1, 2, 3];\n    iA : INT;\nEND_VAR\n")
f("dekl_faltinitiering_upprepning", "deklaration", "    iA := a[1];",
  dekl="VAR\n    a : ARRAY[1..3] OF INT := [3(0)];\n    iA : INT;\nEND_VAR\n")

# POU-former
f("pou_tom_kropp_i_funktion", "trasig", None, None,
  "FUNCTION F : INT\nVAR_INPUT\n    v : INT;\nEND_VAR\n    ;\n"
  "END_FUNCTION\nPROGRAM Main\nVAR\n    iA : INT;\nEND_VAR\n"
  "    iA := F(1);\nEND_PROGRAM\n")
f("pou_konfigurationsblock", "trasig", None, None,
  "PROGRAM Main\nVAR\n    bA : BOOL;\nEND_VAR\n    bA := TRUE;\n"
  "END_PROGRAM\nCONFIGURATION C\n  RESOURCE R ON PLC\n"
  "    TASK T(INTERVAL := T#20ms, PRIORITY := 1);\n"
  "    PROGRAM P WITH T : Main;\n  END_RESOURCE\nEND_CONFIGURATION\n")
f("sats_tom_gren_i_case", "trasig",
  "    CASE iA OF\n        1: ;\n    END_CASE;")


# ---- facit: var far de tva svaren skilja sig at, och varfor --------------
#
# Tva riktningar, och de ar inte symmetriska:
#
#   STRANGARE  vi avvisar, kompilatorn godkanner. Ofarligt bara nar det ar
#              avsiktligt - annars ar det just den falska rodgrinden som
#              kostar reparationsvarv.
#   LATTARE    vi godkanner, kompilatorn avvisar. Farligare i princip; har
#              fangas bada av grind 1, som kor i samma anrop.
#
# Varje rad bar sitt skal. En avvikelse UTAN rad ar ett fel.

STRANGARE = {
    # -- avsiktlig stranghet: det ar det har grind 2 och 3 finns for. --
    "int_far_real":
        "REAL till INT hugger av. Kompilatorn tiger; var typregel kraver ett "
        "uttryckligt REAL_TO_INT (typer.py: en konvertering som inte ar "
        "bevisat forlustfri ar forbjuden).",
    "bool_far_int":
        "INT till BOOL ar ingen vidgning. Kompilatorn tiger.",
    "dint_far_lint":
        "LINT till DINT ar en avhuggning. Kompilatorn tiger.",
    "literal_over_int":
        "40000 ryms inte i INT. Kompilatorn tiger; talet skulle slaa runt i "
        "falt.",
    "jamfor_bool_med_int":
        "BOOL mot INT har ingen gemensam typ. Kompilatorn tiger.",
    "index_utanfor_granser":
        "arr[99] i ett ARRAY[1..10]. Kompilatorn tiger; i drift ar det en "
        "lasning utanfor minnet.",
    "exit_utanfor_slinga":
        "EXIT utan nagon oppen slinga. Kompilatorn tiger; satsen ar antingen "
        "verkningslos eller ett tecken pa att en slinga tappats bort.",
    "okant_argumentnamn":
        "TON har ingen ingang HITTEPA. Kompilatorn tiger - I9 sager att ett "
        "uppfunnet namn ar ett hart fel.",
    "okant_falt_pa_block":
        "TON har ingen anslutning HITTEPA. Kompilatorn tiger.",
    "blocktyp_anropad_direkt":
        "TON(...) anropar TYPEN, inte en instans, och har inget minne. "
        "Kompilatorn tiger.",
    "blockinstans_i_uttryck":
        "ton1(...) i ett uttryck. Ett funktionsblock lamnar inget varde; "
        "utgangen laeses med ton1.Q efterat. Kompilatorn tiger.",
    "case_utan_grenar":
        "CASE utan en enda gren ar en gren som aldrig kan valjas. "
        "Kompilatorn tiger.",
    "tid_fel_ordning":
        "T#5s10m har enheterna i stigande signifikans. IEC 61131-3 kraver "
        "fallande. Kompilatorn tiger.",
    "icke_ascii":
        "Icke-ASCII i kallan. Teckenkodningen genom OpenPLC och vidare ut som "
        "OPC UA-namn ager vi inte, sa lagret vagrar hellre. Kompilatorn tiger.",

    # -- akta falska rodgrindar som INTE lagas, och varfor -----------------
    "tom_sats_semikolon":
        "Ett ensamt ';' som sats. LAGAS INTE. Regeln som star kvar ar 'ett "
        "semikolon avslutar nagot, det ar aldrig en sats': efter END_IF, "
        "END_CASE, END_FOR, END_WHILE, END_REPEAT och END_VAR ar det valfritt, "
        "men ensamt bar det ingen mening. En tom sats ar dessutom det som blir "
        "kvar nar en modell skriver en halv sats, och T7 i "
        "tests/protocol/fas7_stationen.md ar precis den kroppen.",
    "datum_literal":
        "DATE#. LAGAS INTE. Typlagret har ingen DATE-typ, och att slappa in "
        "literalen utan typ hade betytt att den passerar OKONTROLLERAD - en "
        "falsk gron i stallet for en falsk rod. Att lagga till typen skulle "
        "dessutom auto-generera DATE_TO_* -konverteringar som ingen matt. "
        "Meddelandet sager redan rakt ut att lagret inte stodjer formen.",
    "tid_pa_dagen_literal":
        "TOD#, tid pa dagen. LAGAS INTE, exakt samma skal som DATE#: typlagret har ingen TIME_OF_DAY-typ att kontrollera den mot.",

    # -- M-99: avsiktlig stranghet som svepet hittade -------------------
    "tid_dubbel_enhet":
        "T#5s5s namner samma enhet tva ganger. IEC 61131-3 kraver fallande "
        "signifikans och varje enhet hogst en gang; kompilatorn tiger och "
        "summerar dem tyst till 10 s. Samma familj som tid_fel_ordning.",
    "tid_decimal_i_fel_del":
        "T#1.5h30m har decimaler i en del som INTE ar den minsta. IEC "
        "61131-3 tillater decimaler bara i den minsta delen, annars ar "
        "literalens varde tvetydigt. Kompilatorn tiger.",
    "tal_int_over_omradet_negativt":
        "-32769 ryms inte i INT. Kompilatorn tiger; talet skulle slaa runt i "
        "falt. Grannen till M-99:s lagning: -32768 SKA ga igenom, -32769 ska "
        "inte, och bada matas nu.",
    "strang_over_radbrytning":
        "En strangliteral som lopper over en radbrytning. IEC 61131-3 har "
        "$L och $N just for att en strang inte ska behova bryta raden; "
        "STruC++ 0.6.6 slapper igenom formen anda. En oavslutad strang och "
        "en flerradig strang ser likadana ut for den som laser felet.",
    "uttryck_kedjetilldelning":
        "iA := iB := iC. Tilldelning ar en SATS i ST, inte ett uttryck, sa "
        "kedjan gar inte att harleda ur IEC 61131-3:s grammatik. "
        "Kompilatorn bygger den anda och far da valja associativitet sjalv.",
    "dekl_falt_omvand_grans":
        "ARRAY[10..1] har ingen enda giltig index. Kompilatorn tiger. MATT i "
        "M-99: hos oss kom formen ut som en OFANGAD ValueError - grinden "
        "kraschade i stallet for att doma - och det ar vad som lagades.",
    "pou_tom_kropp_i_funktion":
        "En FUNCTION vars hela kropp ar ';'. Samma regel som "
        "tom_sats_semikolon och samma skal: ett ensamt semikolon avslutar "
        "nagot, det ar aldrig en sats. Har ar foljden dessutom en funktion "
        "som aldrig tilldelar sitt returvarde.",
    "sats_tom_gren_i_case":
        "En CASE-gren vars hela kropp ar ';'. Samma regel som "
        "tom_sats_semikolon. En gren som inte gor nagot ar antingen en halv "
        "sats eller en gren som skulle ha tagits bort.",

    # -- M-99: falska rodgrindar som star kvar, och varfor ---------------
    "dekl_faltinitiering":
        "ARRAY[1..3] OF INT := [1, 2, 3]. FALSK RODGRIND, LAGAS INTE AN. "
        "Formen star i IEC 61131-3 och STruC++ 0.6.6 bygger den; lasaren "
        "laser startvarden som ETT uttryck och har ingen nod for en "
        "faltinitierare. Lagningen ror modell, lasare, skrivare och "
        "typkontroll pa en gang, och tur-och-retur-provet maste halla hela "
        "vagen. Kostnaden ar dessutom MATT till noll pa modellvagen: "
        "skelett.granska_arbetsvariabler slapper bara elementara typer och "
        "standardfunktionsblocken, sa modellen kan inte deklarera ett falt "
        "over huvud taget - resten av deklarationsdelen genererar kedjan "
        "sjalv. Skulden ar bokford i M-99, inte gomd.",
    "dekl_faltinitiering_upprepning":
        "ARRAY[1..3] OF INT := [3(0)], upprepningsformen. FALSK RODGRIND, "
        "LAGAS INTE AN, exakt samma skal och samma lagning som "
        "dekl_faltinitiering: utan en nod for faltinitieraren finns det "
        "ingenstans att lagga upprepningsantalet.",
    "pou_konfigurationsblock":
        "CONFIGURATION / RESOURCE / TASK. FALSK RODGRIND, LAGAS INTE. "
        "Formen star i IEC 61131-3 och kompilatorn bygger den, men lagrets "
        "domanen ar POU:er: konfigurationen kring dem genereras av kedjan "
        "sjalv (plc/skelett.py), aldrig av modellen. Att lasa den skulle "
        "vara en ny grammatik utan en enda kallare.",
}

LATTARE = {
    "tid_negativ":
        "T#-2h ar giltig IEC 61131-3 och vart lager raknar den ratt, men "
        "STruC++ 0.6.6 lexar inte '#-'. LAGAS INTE: att skriva in kompilatorns "
        "begransning i vart lager binder oss till en version, och grind 1 kor "
        "i samma anrop som grind 2 och 3 (stationsgrind.granska_station) sa "
        "fallet fangas anda innan stationen doms. Formen '-T#2h' bygger.",
    # -- M-99: kompilatorbegransningar, inte var stranghet --------------
    "kommentarstart_i_strang":
        "sA := 'a(*b'. STruC++ 0.6.6 lexar '(*' aven INNE i en strangliteral "
        "och svarar 'Unclosed block comment'. Var lexer laser strangen forst, "
        "vilket ar ratt: en kommentarstart inuti en strang ar text. LAGAS "
        "INTE - att harma felet vore att skriva in en kompilatorbugg i "
        "lagret, och grind 1 kor anda i samma anrop.",
    "tal_understreck_i_realdel":
        "rA := 1_000.5. Understreck i ett tal ar lasbarhetsavskiljare i IEC "
        "61131-3 och tillatna i BADA delarna; STruC++ 0.6.6 tar dem bara i "
        "heltalsdelen. LAGAS INTE av samma skal som ovan.",
    "strang_dollarcitat":
        "sA := 'a$\"b'. $\" star i IEC 61131-3:s tabell over $-sekvenser; "
        "STruC++ 0.6.6 kanner den inte inne i en enkelciterad strang. LAGAS "
        "INTE: vart lager avkodar sekvensen till ett tecken och tappar "
        "ingenting.",
    "uttryck_not_not":
        "bA := NOT NOT bB. IEC 61131-3:s grammatik tillater en unar operator "
        "per uttryck, och STruC++ 0.6.6 haller pa den bokstaven. LAGAS INTE: "
        "att avvisa formen skulle gora oss strangare an de kompilatorer "
        "modellen troligast har sett, alltsa en NY falsk rodgrind - och "
        "grind 1 fangar den anda i samma anrop.",
    "uttryck_dubbelt_unart_minus":
        "iA := - -iB. Samma grammatikrad och samma dom som uttryck_not_not: "
        "en unar operator per uttryck. LAGAS INTE, samma skal.",
    "uttryck_jamforelse_utan_parentes":
        "bA := iA < iB = TRUE. IEC 61131-3 skiljer comparison fran "
        "equ_expression, sa formen ar harledbar; STruC++ 0.6.6 kraver "
        "parenteser. LAGAS INTE - vart trad bygger samma vansterassociativa "
        "form som standarden anger.",
    "uttryck_exponent_hogerassociativ":
        "rA := 2.0 ** 3.0 ** 2.0. Exponentoperatorn ar hogerassociativ och "
        "kedjebar i IEC 61131-3 (tabell 71); STruC++ 0.6.6 tar bara en. "
        "LAGAS INTE: test_st_syntax provar redan att var kedja lases och "
        "skrivs tillbaka likadant.",
    "var_string_langd":
        "STRING[20] ar giltig IEC 61131-3 och vart typlager anvander langden "
        "till en verklig kontroll (test_st_semantik: 'abcdefg' ryms inte i "
        "STRING[4]). STruC++ 0.6.6 kan inte deklarera den. LAGAS INTE: att "
        "avvisa formen skulle kasta bort en fungerande langdkontroll for att "
        "spegla en kompilatorversion, och grind 1 fangar den anda.",
}


# ---- korningen -----------------------------------------------------------

def _kompilera(cli, kalltext, katalog, namn):
    inn = os.path.join(katalog, "%s.st" % namn)
    with open(inn, "w", encoding="utf-8") as fh:
        fh.write(kalltext)
    klar = subprocess.run(
        [cli, inn, "-o", os.path.join(katalog, "%s.cpp" % namn)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return klar.returncode == 0, klar.stdout.decode("utf-8", "replace")


@pytest.fixture(scope="module")
def svep():
    """Hela svepet, en gang. 185 kompilatorstarter tar tid; att starta om
    dem per prov hade gjort provet sa dyrt att nagon stanger av det."""
    katalog = tempfile.mkdtemp(prefix="m51_svep_")
    ut = {}

    def en(post):
        namn, _grupp, kropp, dekl, prolog = post
        # kropp=None: fallet ar HELA kallan, inte en kropp i Main. Formerna
        # som provar POU-ramen sjalv (CONFIGURATION, en FUNCTION med tom
        # kropp) gar inte att uttrycka som en kropp inuti ett program.
        text = prolog if kropp is None else kalla(kropp, dekl, prolog)
        kok, kutdata = _kompilera(STRUCPP, text, katalog, namn)
        return namn, (validera(text), kok, kutdata)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for namn, svar in pool.map(en, FALL):
            ut[namn] = svar
    return ut


def test_svepet_har_unika_namn_och_tacker_alla_grupper():
    """En dubblett hade tyst skrivit over ett fall i svepets tabell."""
    namn = [n for n, _g, _k, _d, _p in FALL]
    assert len(namn) == len(set(namn)), "dubbla namn i svepet"
    grupper = set(g for _n, g, _k, _d, _p in FALL)
    assert grupper == {"sats", "semikolon", "literal", "operator", "block",
                       "funktion", "kommentar", "deklaration", "form",
                       "trasig"}


def test_facittabellerna_namnger_bara_fall_som_finns():
    """En rad i STRANGARE for ett fall som inte langre svepts ar en rad som
    slutat mata nagot. Den ska tas bort, inte lamnas kvar."""
    namn = set(n for n, _g, _k, _d, _p in FALL)
    assert set(STRANGARE) <= namn, sorted(set(STRANGARE) - namn)
    assert set(LATTARE) <= namn, sorted(set(LATTARE) - namn)
    assert not (set(STRANGARE) & set(LATTARE))
    for skal in list(STRANGARE.values()) + list(LATTARE.values()):
        assert len(skal) > 40, "ett skal maste saga VARFOR: %r" % skal


@pytest.mark.parametrize(
    "namn", [n for n, _g, _k, _d, _p in FALL],
    ids=[n for n, _g, _k, _d, _p in FALL])
def test_var_grind_och_kompilatorn_ar_overens_dar_de_ska_vara_det(namn, svep):
    rapport, kompilerade, kutdata = svep[namn]
    if namn in STRANGARE:
        assert not rapport.ok, (
            "%s star som avsiktligt strangare men vart lager SLAPPTE IGENOM "
            "den. Antingen har en kontroll slutat falla, eller sa ska raden "
            "tas bort ur STRANGARE.\nSkal pa raden: %s" % (namn, STRANGARE[namn]))
        assert kompilerade, (
            "%s star som avsiktligt strangare, men kompilatorn avvisar den "
            "ocksa. Da ar den ingen avvikelse och raden ska bort.\n%s"
            % (namn, kutdata))
        return
    if namn in LATTARE:
        assert rapport.ok, (
            "%s star som dokumenterat lattare men vart lager avvisar den nu. "
            "Raden ska bort.\nSkal pa raden: %s\n%s"
            % (namn, LATTARE[namn], rapport))
        assert not kompilerade, (
            "%s star som dokumenterat lattare, men STruC++ bygger den nu. "
            "Kompilatorn har alltsa andrats: ta bort raden.\n%s" % (namn, kutdata))
        return
    assert rapport.ok == kompilerade, (
        "NY AVVIKELSE i %s.\n"
        "vart lager: %s\nkompilatorn: %s\n%s\n%s\n"
        "Ar den avsiktlig ska den in i STRANGARE eller LATTARE med sitt skal. "
        "Ar den inte det ar den ett fel i ST-lagret."
        % (namn, "GODKAND" if rapport.ok else "AVVISAD",
           "bygger" if kompilerade else "bygger inte", rapport, kutdata))


def test_antalet_dokumenterade_avvikelser_gar_inte_upp_av_sig_sjalvt():
    """Sparr at ett hall.

    Talet var M-51:s 19. M-99 svepte 394 nya konstruktioner over skiftlage,
    blanksteg, kommentarer, talformer, tidsliteraler, strangar, uttryck och
    POU-ramen, lagade fyra falska rodgrindar och fyra hal, och lamnade 18
    nya dokumenterade avvikelser: elva dar vi ar avsiktligt strangare - varav
    TRE ar falska rodgrindar som star kvar med skal utskrivet
    (faltinitieraren i tva former och CONFIGURATION) - och sju dar
    kompilatorversionen ar begransningen.

    Taket ar hojt MEDVETET till 40. Det far sjunka nar en avvikelse lagas,
    men en ny rad ska fortsatta kosta ett beslut."""
    assert len(STRANGARE) + len(LATTARE) <= 40, (
        "fler dokumenterade avvikelser an M-99 matte. Lagade du en, sank "
        "talet; behover du en ny rad, hoj det medvetet och skriv ned varfor.")


# ---- namnen: den enda fragan framande INTE kan svara pa ------------------

def _kalla_med_alla_funktioner():
    """Ett program som anropar VARJE namn i standardbiblioteket en gang."""
    var = dict((n, "v_%s" % n) for n in sorted(T.ELEMENTARA))
    argument = {"ANY": "v_INT", "ANY_NUM": "v_INT", "ANY_INT": "v_INT",
                "ANY_REAL": "v_REAL", "ANY_BIT": "v_WORD", "STRING": "v_STR"}

    def arg(klass):
        return argument.get(klass, var.get(klass, "v_INT"))

    def mal(fd):
        r = fd.resultat
        if r.startswith("="):
            for p in fd.parametrar:
                if p.namn == r[1:]:
                    return arg(p.klass)
            return "v_INT"
        if r == "GEM":
            return arg(fd.parametrar[-1].klass)
        if r == "STRING":
            return "v_STR"
        return var.get(r, "v_INT")

    rader = ["PROGRAM M", "VAR"]
    for n in sorted(T.ELEMENTARA):
        rader.append("    v_%s : %s;" % (n, n))
    rader.append("    v_STR : STRING;")
    rader.append("END_VAR")
    for namn in sorted(SB.FUNKTIONER):
        fd = SB.FUNKTIONER[namn]
        rader.append("    %s := %s(%s);"
                     % (mal(fd), namn, ", ".join(arg(p.klass)
                                                 for p in fd.parametrar)))
    rader.append("END_PROGRAM")
    return "\n".join(rader) + "\n"


def _bygg(kalltext, katalog, namn):
    inn = os.path.join(katalog, "%s.st" % namn)
    with open(inn, "w", encoding="utf-8") as fh:
        fh.write(kalltext)
    klar = subprocess.run(
        [STRUCPP, inn, "-o", os.path.join(katalog, "%s.cpp" % namn), "--build"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=katalog)
    return klar.returncode == 0, klar.stdout.decode("utf-8", "replace")


@pytest.mark.skipif(GPP is None,
                    reason="g++ saknas; --build kan inte lanka den genererade "
                           "C++:en och namnfragan gar da inte att stalla")
def test_ett_uppfunnet_funktionsnamn_faller_forst_i_bygget():
    """Den trasiga fixturen for namnprovet nedan.

    Utan den vore namnprovet en grind som inte kan falla: STruC++:s framande
    slapper igenom HITTEPA(x) UTAN ANMARKNING. Det ar hela skalet att
    namnprovet maste ga via --build.
    """
    kalltext = ("PROGRAM M\nVAR\n    v : INT;\nEND_VAR\n"
                "    v := HITTEPA(v);\nEND_PROGRAM\n")
    katalog = tempfile.mkdtemp(prefix="m51_namn_")
    framande_ok, _ = _kompilera(STRUCPP, kalltext, katalog, "framande")
    assert framande_ok, ("STruC++:s framande brukade slappa igenom uppfunna "
                         "namn. Gor den inte det langre ar den en "
                         "namnauktoritet, och svepet kan forenklas.")
    byggde, utdata = _bygg(kalltext, katalog, "bygget")
    assert not byggde, "HITTEPA lankade; den trasiga fixturen ar inte trasig"
    assert "HITTEPA" in utdata


@pytest.mark.skipif(GPP is None,
                    reason="g++ saknas; --build kan inte lanka den genererade "
                           "C++:en och namnfragan gar da inte att stalla")
def test_varje_namn_vi_slapper_igenom_finns_ocksa_i_strucpp():
    """I9 at andra hallet.

    Standardbiblioteket ar en sluten lista, och ett namn PA den listan ar ett
    lofte: skriver modellen sa har kommer koden igenom hela kedjan. Ett namn
    som inte lankar ar ett brutet lofte som syns forst i bygget - en falsk
    gron i den ande dar den kostar mest.
    """
    katalog = tempfile.mkdtemp(prefix="m51_alla_")
    kalltext = _kalla_med_alla_funktioner()
    rapport = validera(kalltext)
    assert rapport.ok, ("vart eget lager avvisar sitt eget bibliotek: %s"
                        % rapport)
    byggde, utdata = _bygg(kalltext, katalog, "alla")
    assert byggde, (
        "namn i standardbiblioteket som inte gar att bygga i STruC++:\n%s"
        % "\n".join(r for r in utdata.split("\n") if "error" in r.lower()))
