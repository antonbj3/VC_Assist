# -*- coding: utf-8 -*-
"""Standardbiblioteket: de funktionsblock och funktioner som får anropas.

Listan är sluten med avsikt. Invariant I9 (docs/spec/90_invarianter.md):
ett uppfunnet API-namn är ett hårt fel, inte en varning. Ett anrop till något
som inte står här fälls — även om det finns i någon annan tillverkares
bibliotek. Vill man ha fler skrivs de in här, inte i koden som genereras.

Signaturerna följer IEC 61131-3 (3:e utg.), bilaga F (standardfunktionsblock)
och kapitlet om standardfunktioner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from . import typer as T

def passar(klass: str, typ: T.Typ) -> bool:
    if isinstance(typ, T.Blocktyp):
        return False
    if klass == "ANY":
        return True
    if klass == "ANY_NUM":
        return T.ar_numerisk(typ)
    if klass == "ANY_INT":
        return T.ar_heltal(typ)
    if klass == "ANY_REAL":
        return (isinstance(typ, T.Elementar) and typ.namn in T.FLYT_MANTISSA) or \
               (isinstance(typ, T.Literaltyp) and typ.klass in ("REAL", "HELTAL"))
    if klass == "ANY_BIT":
        return T.ar_bitlogisk(typ)
    if klass == "STRING":
        return isinstance(typ, T.Strang) or \
               (isinstance(typ, T.Literaltyp) and typ.klass == "STRANG")
    return T.far_tilldelas(T.Elementar(klass), typ)[0]


@dataclass(frozen=True)
class Parameter:
    namn: str
    klass: str
    obligatorisk: bool = True
    # En STYRANDE ingang valjer, den bidrar inte till resultatets typ.
    # SEL:s G ar BOOL och MUX:s K ar ett heltal, men bada funktionerna lamnar
    # typen hos det VALDA vardet. Utan flaggan rakade den gemensamma typen
    # ihop valjaren med de valda och SEL(bA, iB, iC) fick "ingen gemensam
    # typ" fastan bada de valda var INT. MATT i M-51.
    styrande: bool = False


@dataclass(frozen=True)
class Blockdef:
    """Ett funktionsblock: har instanser, minne och namngivna anslutningar."""

    namn: str
    ingangar: Tuple[Parameter, ...]
    utgangar: Tuple[Parameter, ...]


@dataclass(frozen=True)
class Funktionsdef:
    """En funktion: inget minne, ett resultat.

    resultat: ett elementärt typnamn, "=<param>" för samma typ som den
    parametern, eller "GEM" för den gemensamma typen hos ANY-parametrarna.
    """

    namn: str
    parametrar: Tuple[Parameter, ...]
    resultat: str
    variadisk: bool = False


_B = Parameter

BLOCK = {}
for _namn in ("TON", "TOF", "TP"):
    BLOCK[_namn] = Blockdef(
        _namn,
        (_B("IN", "BOOL"), _B("PT", "TIME")),
        (_B("Q", "BOOL"), _B("ET", "TIME")))
for _namn in ("R_TRIG", "F_TRIG"):
    BLOCK[_namn] = Blockdef(_namn, (_B("CLK", "BOOL"),), (_B("Q", "BOOL"),))
BLOCK["SR"] = Blockdef("SR", (_B("S1", "BOOL"), _B("R", "BOOL")), (_B("Q1", "BOOL"),))
BLOCK["RS"] = Blockdef("RS", (_B("S", "BOOL"), _B("R1", "BOOL")), (_B("Q1", "BOOL"),))
BLOCK["CTU"] = Blockdef(
    "CTU", (_B("CU", "BOOL"), _B("R", "BOOL"), _B("PV", "INT")),
    (_B("Q", "BOOL"), _B("CV", "INT")))
BLOCK["CTD"] = Blockdef(
    "CTD", (_B("CD", "BOOL"), _B("LD", "BOOL"), _B("PV", "INT")),
    (_B("Q", "BOOL"), _B("CV", "INT")))
BLOCK["CTUD"] = Blockdef(
    "CTUD", (_B("CU", "BOOL"), _B("CD", "BOOL"), _B("R", "BOOL"),
             _B("LD", "BOOL"), _B("PV", "INT")),
    (_B("QU", "BOOL"), _B("QD", "BOOL"), _B("CV", "INT")))

FUNKTIONER = {
    "ABS": Funktionsdef("ABS", (_B("IN", "ANY_NUM"),), "=IN"),
    "SQRT": Funktionsdef("SQRT", (_B("IN", "ANY_REAL"),), "=IN"),
    "MIN": Funktionsdef("MIN", (_B("IN1", "ANY_NUM"), _B("IN2", "ANY_NUM")),
                        "GEM", variadisk=True),
    "MAX": Funktionsdef("MAX", (_B("IN1", "ANY_NUM"), _B("IN2", "ANY_NUM")),
                        "GEM", variadisk=True),
    "LIMIT": Funktionsdef("LIMIT", (_B("MN", "ANY_NUM"), _B("IN", "ANY_NUM"),
                                    _B("MX", "ANY_NUM")), "=IN"),
    "SEL": Funktionsdef("SEL", (_B("G", "BOOL", True, True), _B("IN0", "ANY"),
                                _B("IN1", "ANY")), "GEM"),
    "MUX": Funktionsdef("MUX", (_B("K", "ANY_INT", True, True), _B("IN0", "ANY"),
                                _B("IN1", "ANY")), "GEM", variadisk=True),
    "MOVE": Funktionsdef("MOVE", (_B("IN", "ANY"),), "=IN"),
    "TRUNC": Funktionsdef("TRUNC", (_B("IN", "ANY_REAL"),), "DINT"),
    "SHL": Funktionsdef("SHL", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "SHR": Funktionsdef("SHR", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "ROL": Funktionsdef("ROL", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "ROR": Funktionsdef("ROR", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "LEN": Funktionsdef("LEN", (_B("IN", "STRING"),), "INT"),
}

# ---- talfunktioner, jamforelser och strangar -----------------------------
#
# Varenda namn har ar MATT i M-51: det bygger och LANKAR i STruC++ 0.6.6
# (`strucpp <fil> -o <ut> --build`). Den matningen behovdes, for STruC++:s
# framande accepterar VILKET namn som helst — `HITTEPA(x)` gick igenom
# frontenden utan anmarkning och foll forst nar g++ sag den genererade C++:en.
# Ett svep som bara kort frontenden hade darfor "bevisat" att NOW() finns.
# Den gor inte det.
#
# Formen `AND(a, b)`, `OR(a, b)`, `XOR(a, b)`, `NOT(a)` och `MOD(a, b)` star
# ocksa i IEC 61131-3 och lankar i STruC++, men de star MEDVETET inte har:
# alla fem ar nyckelord i lexern, och infixformen ar den ST-kod som faktiskt
# skrivs. Att gora nyckelorden sammanhangsberoende ar en lasarrisk for ett
# fall ingen modell producerar. Skalet star i M-51.

# Envariga talfunktioner over ANY_REAL. IEC 61131-3, tabell 23.
for _n in ("LN", "LOG", "EXP", "SIN", "COS", "TAN", "ASIN", "ACOS", "ATAN"):
    FUNKTIONER[_n] = Funktionsdef(_n, (_B("IN", "ANY_REAL"),), "=IN")

FUNKTIONER["ATAN2"] = Funktionsdef(
    "ATAN2", (_B("IN1", "ANY_REAL"), _B("IN2", "ANY_REAL")), "=IN1")
# IEC anger ANY_REAL for basen. Har star ANY_NUM, darfor att STruC++ 0.6.6
# kompilerar `iA := EXPT(iB, 2)` och en modell som skriver den formen inte ska
# fa tillbaka ett fel som inte finns i kedjan. Mätt i M-51.
FUNKTIONER["EXPT"] = Funktionsdef(
    "EXPT", (_B("IN1", "ANY_NUM"), _B("IN2", "ANY_NUM")), "=IN1")

# Aritmetiken i funktionsform. ADD och MUL ar variadiska i IEC, SUB och DIV
# tvastalliga.
for _n in ("ADD", "MUL"):
    FUNKTIONER[_n] = Funktionsdef(
        _n, (_B("IN1", "ANY_NUM"), _B("IN2", "ANY_NUM")), "GEM", variadisk=True)
for _n in ("SUB", "DIV"):
    FUNKTIONER[_n] = Funktionsdef(
        _n, (_B("IN1", "ANY_NUM"), _B("IN2", "ANY_NUM")), "GEM")

# Jamforelserna i funktionsform. Variadiska i IEC: GT(a, b, c) betyder a>b>c.
for _n in ("GT", "GE", "EQ", "NE", "LT", "LE"):
    FUNKTIONER[_n] = Funktionsdef(
        _n, (_B("IN1", "ANY"), _B("IN2", "ANY")), "BOOL", variadisk=True)

# Strangfunktionerna. Resultatet ar INGANGENS strangtyp och inte en naken
# STRING: annars blev `s20 := LEFT(s20, 2)` ett typfel pa en STRING[20], for
# en STRING utan deklarerad langd far inte tilldelas en med.
FUNKTIONER["CONCAT"] = Funktionsdef(
    "CONCAT", (_B("IN1", "STRING"), _B("IN2", "STRING")), "=IN1", variadisk=True)
for _n in ("LEFT", "RIGHT"):
    FUNKTIONER[_n] = Funktionsdef(
        _n, (_B("IN", "STRING"), _B("L", "ANY_INT")), "=IN")
FUNKTIONER["MID"] = Funktionsdef(
    "MID", (_B("IN", "STRING"), _B("L", "ANY_INT"), _B("P", "ANY_INT")), "=IN")
FUNKTIONER["DELETE"] = Funktionsdef(
    "DELETE", (_B("IN", "STRING"), _B("L", "ANY_INT"), _B("P", "ANY_INT")), "=IN")
FUNKTIONER["INSERT"] = Funktionsdef(
    "INSERT", (_B("IN1", "STRING"), _B("IN2", "STRING"), _B("P", "ANY_INT")), "=IN1")
FUNKTIONER["REPLACE"] = Funktionsdef(
    "REPLACE", (_B("IN1", "STRING"), _B("IN2", "STRING"), _B("L", "ANY_INT"),
                _B("P", "ANY_INT")), "=IN1")
FUNKTIONER["FIND"] = Funktionsdef(
    "FIND", (_B("IN1", "STRING"), _B("IN2", "STRING")), "INT")

# TIME() star INTE i IEC 61131-3:s tabeller. Den finns i STruC++:s runtime och
# ar den form en modell skriver nar den vill jamfora mot systemtiden; M-48
# matte just den konstruktionen som falsk rodgrind. Den star har med den
# harkomsten utskriven, inte som om den vore standard.
FUNKTIONER["TIME"] = Funktionsdef("TIME", (), "TIME")

# Konverteringsfunktionerna genereras ur typtabellen i stället för att skrivas
# för hand. Skälet är mätt i källprojektet: handskrivna namnlistor blir
# ofullständiga, och en saknad post ser ut som ett uppfunnet namn.
for _fran in sorted(T.ELEMENTARA):
    for _till in sorted(T.ELEMENTARA):
        if _fran == _till:
            continue
        _n = "%s_TO_%s" % (_fran, _till)
        FUNKTIONER[_n] = Funktionsdef(_n, (_B("IN", _fran),), _till)
