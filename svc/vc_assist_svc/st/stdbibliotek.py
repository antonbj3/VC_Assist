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
    "SEL": Funktionsdef("SEL", (_B("G", "BOOL"), _B("IN0", "ANY"),
                                _B("IN1", "ANY")), "GEM"),
    "TRUNC": Funktionsdef("TRUNC", (_B("IN", "ANY_REAL"),), "DINT"),
    "SHL": Funktionsdef("SHL", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "SHR": Funktionsdef("SHR", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "ROL": Funktionsdef("ROL", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "ROR": Funktionsdef("ROR", (_B("IN", "ANY_BIT"), _B("N", "ANY_INT")), "=IN"),
    "LEN": Funktionsdef("LEN", (_B("IN", "STRING"),), "INT"),
}

# Konverteringsfunktionerna genereras ur typtabellen i stället för att skrivas
# för hand. Skälet är mätt i källprojektet: handskrivna namnlistor blir
# ofullständiga, och en saknad post ser ut som ett uppfunnet namn.
for _fran in sorted(T.ELEMENTARA):
    for _till in sorted(T.ELEMENTARA):
        if _fran == _till:
            continue
        _n = "%s_TO_%s" % (_fran, _till)
        FUNKTIONER[_n] = Funktionsdef(_n, (_B("IN", _fran),), _till)
