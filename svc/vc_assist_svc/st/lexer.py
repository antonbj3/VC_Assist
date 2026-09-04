# -*- coding: utf-8 -*-
"""Lexer för Structured Text.

ST är skiftlägesokänsligt: `Steg` och `steg` är samma namn, och `if` är samma
nyckelord som `IF`. Det hanteras här, en gång, så att ingen kontroll längre upp
behöver komma ihåg det.

Icke-ASCII i källan avvisas. Skälet är driftsmässigt: koden ska gå genom
STruC++ och OpenPLC:s inladdning och vidare ut som OPC UA-namn, och där är
teckenkodningen inte något vi äger.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .fel import Syntaxfel

NYCKELORD = {
    "PROGRAM", "END_PROGRAM", "FUNCTION", "END_FUNCTION",
    "FUNCTION_BLOCK", "END_FUNCTION_BLOCK",
    "VAR", "VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT", "VAR_GLOBAL",
    "VAR_EXTERNAL", "VAR_TEMP", "END_VAR",
    "CONSTANT", "RETAIN", "NON_RETAIN", "AT",
    "TYPE", "END_TYPE", "STRUCT", "END_STRUCT", "ARRAY", "OF", "STRING",
    "IF", "THEN", "ELSIF", "ELSE", "END_IF",
    "CASE", "END_CASE",
    "FOR", "TO", "BY", "DO", "END_FOR",
    "WHILE", "END_WHILE",
    "REPEAT", "UNTIL", "END_REPEAT",
    "EXIT", "RETURN",
    "AND", "OR", "XOR", "NOT", "MOD",
    "TRUE", "FALSE",
}

# Blockavslutare -> blocköppnare. Används av läsaren för att kunna säga
# "END_WHILE avslutar en IF" i stället för bara "oväntat nyckelord".
AVSLUTARE = {
    "END_IF": "IF", "END_CASE": "CASE", "END_FOR": "FOR",
    "END_WHILE": "WHILE", "END_REPEAT": "REPEAT", "END_VAR": "VAR",
    "END_PROGRAM": "PROGRAM", "END_FUNCTION": "FUNCTION",
    "END_FUNCTION_BLOCK": "FUNCTION_BLOCK", "END_TYPE": "TYPE",
    "END_STRUCT": "STRUCT",
}

TVATECKEN = ("<=", ">=", "<>", ":=", "=>", "..")
ENTECKEN = "+-*/<>=(),;:.[]&"

# Tidsenheter, störst först. IEC 61131-3 (3:e utg.) tillåter d h m s ms us ns.
# Ordningen i tupeln ÄR signifikansordningen som literalen måste följa.
TIDSENHETER = ("d", "h", "m", "s", "ms", "us", "ns")
_TIDSDEL = re.compile(r"([0-9][0-9_]*(?:\.[0-9][0-9_]*)?)(ms|us|ns|d|h|m|s)")
# Faktor till millisekunder. Rena enhetsdefinitioner, inga valda tal.
_TILL_MS = {"d": 86400000.0, "h": 3600000.0, "m": 60000.0, "s": 1000.0,
            "ms": 1.0, "us": 0.001, "ns": 0.000001}

# %<plats><storlek><tal>[.<tal>...]. IEC 61131-3, direkt representerade
# variabler: plats I/Q/M, storlek X B W D L (utelämnad = bit).
_ADRESS = re.compile(r"%[IQMiqm][XBWDLxbwdl]?[0-9]+(?:\.[0-9]+)*")

_STRANGKOD = {"$": "$", "'": "'", '"': '"', "L": "\n", "N": "\n",
              "P": "\f", "R": "\r", "T": "\t"}


@dataclass(frozen=True)
class Token:
    sort: str            # IDENT NYCKELORD HELTAL REAL TID STRANG OP KOMMENTAR PRAGMA SLUT
    text: str            # exakt som i källan
    rad: int
    kol: int
    varde: object = None

    @property
    def nyckel(self) -> str:
        return self.text.upper()


def tolka_tidliteral(text: str) -> Tuple[bool, Optional[float], str]:
    """Kontrollerar en TIME-literal och räknar ut den i millisekunder.

    Reglerna, direkt ur IEC 61131-3: minst en del, enheterna i fallande
    signifikans, ingen enhet två gånger, och bara den minsta delen får ha
    decimaler. `T#500` (ingen enhet) och `T#5s10m` (fel ordning) är fel.
    """
    m = re.match(r"(?i)^(T|TIME)#(-?)(.+)$", text)
    if not m:
        return False, None, "en TIME-literal börjar med T# eller TIME#"
    kropp = m.group(3).replace("_", "")
    if not kropp:
        return False, None, "TIME-literalen saknar innehåll"
    pos = 0
    delar = []
    while pos < len(kropp):
        d = _TIDSDEL.match(kropp, pos)
        if not d:
            return False, None, ("%r går inte att läsa som tid; enheterna är %s"
                                 % (kropp[pos:], " ".join(TIDSENHETER)))
        delar.append((d.group(1), d.group(2)))
        pos = d.end()
    sett = []
    for i, (tal, enhet) in enumerate(delar):
        if enhet in sett:
            return False, None, "enheten %s förekommer två gånger" % enhet
        if sett and TIDSENHETER.index(enhet) <= TIDSENHETER.index(sett[-1]):
            return False, None, ("enheterna står i fel ordning: %s efter %s"
                                 % (enhet, sett[-1]))
        if "." in tal and i != len(delar) - 1:
            return False, None, ("bara den minsta delen får ha decimaler, "
                                 "inte %s%s" % (tal, enhet))
        sett.append(enhet)
    summa = sum(float(tal) * _TILL_MS[enhet] for tal, enhet in delar)
    return True, -summa if m.group(2) == "-" else summa, ""


def tolka_strangliteral(text: str) -> str:
    """Avkodar '$'-sekvenserna i en ST-sträng."""
    inre = text[1:-1]
    ut = []
    i = 0
    while i < len(inre):
        c = inre[i]
        if c != "$":
            ut.append(c)
            i += 1
            continue
        if i + 1 >= len(inre):
            raise Syntaxfel("SYNTAX", 0, "sträng slutar mitt i en $-sekvens")
        n = inre[i + 1]
        if n.upper() in _STRANGKOD:
            ut.append(_STRANGKOD[n.upper()])
            i += 2
        elif re.match(r"[0-9A-Fa-f]{2}", inre[i + 1:i + 3] or ""):
            ut.append(chr(int(inre[i + 1:i + 3], 16)))
            i += 3
        else:
            raise Syntaxfel("SYNTAX", 0, "okänd $-sekvens: $%s" % n)
    return "".join(ut)


class Lexer(object):
    def __init__(self, kalla: str):
        self._kontrollera_ascii(kalla)
        self.s = kalla
        self.i = 0
        self.rad = 1
        self.kol = 1

    @staticmethod
    def _kontrollera_ascii(kalla: str):
        """Hela källan, inte bara koden utanför strängar och kommentarer.
        En kommentar med fel teckenkodning fäller inladdningen lika säkert
        som ett variabelnamn gör det."""
        for nr, rad in enumerate(kalla.split("\n"), 1):
            for tecken in rad:
                if ord(tecken) > 127:
                    raise Syntaxfel("SYNTAX", nr,
                                    "icke-ASCII-tecken %r i ST-kallan" % tecken)

    def _fram(self, n=1):
        for _ in range(n):
            if self.i < len(self.s):
                if self.s[self.i] == "\n":
                    self.rad += 1
                    self.kol = 1
                else:
                    self.kol += 1
                self.i += 1

    def _kika(self, n=0):
        j = self.i + n
        return self.s[j] if j < len(self.s) else ""

    def tokens(self) -> List[Token]:
        ut = []
        while True:
            t = self._nasta()
            ut.append(t)
            if t.sort == "SLUT":
                return ut

    def _nasta(self) -> Token:
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self._fram()
        if self.i >= len(self.s):
            return Token("SLUT", "", self.rad, self.kol)
        rad, kol = self.rad, self.kol
        c = self._kika()
        if ord(c) > 127:
            raise Syntaxfel("SYNTAX", rad,
                            "icke-ASCII-tecken %r i ST-källan" % c)
        if c == "(" and self._kika(1) == "*":
            return self._kommentar_block(rad, kol)
        if c == "/" and self._kika(1) == "/":
            start = self.i
            while self.i < len(self.s) and self.s[self.i] != "\n":
                self._fram()
            return Token("KOMMENTAR", self.s[start:self.i], rad, kol,
                         self.s[start + 2:self.i].strip())
        if c == "{":
            start = self.i
            while self.i < len(self.s) and self.s[self.i] != "}":
                self._fram()
            if self.i >= len(self.s):
                raise Syntaxfel("SYNTAX", rad, "pragma { } avslutas aldrig")
            self._fram()
            return Token("PRAGMA", self.s[start:self.i], rad, kol,
                         self.s[start + 1:self.i - 1].strip())
        if c == "%":
            return self._adress(rad, kol)
        if c == "'":
            return self._strang(rad, kol)
        if c.isdigit():
            return self._tal(rad, kol)
        if c.isalpha() or c == "_":
            return self._ord(rad, kol)
        for par in TVATECKEN:
            if self.s.startswith(par, self.i):
                self._fram(2)
                return Token("OP", par, rad, kol)
        if c in ENTECKEN:
            self._fram()
            return Token("OP", c, rad, kol)
        raise Syntaxfel("SYNTAX", rad, "oväntat tecken %r" % c)

    def _kommentar_block(self, rad, kol) -> Token:
        start = self.i
        djup = 0
        while self.i < len(self.s):
            if self.s.startswith("(*", self.i):
                djup += 1
                self._fram(2)
            elif self.s.startswith("*)", self.i):
                djup -= 1
                self._fram(2)
                if djup == 0:
                    text = self.s[start:self.i]
                    return Token("KOMMENTAR", text, rad, kol, text[2:-2].strip())
            else:
                self._fram()
        raise Syntaxfel("SYNTAX", rad, "kommentar som börjar här avslutas aldrig")

    def _adress(self, rad, kol) -> Token:
        """En direktadress ur signalkartan: %IX0.0, %QW12, %MD4.

        Lexas som EN token. Delas den upp i % + namn + punkt blir varje
        kontroll ovanför tvungen att sätta ihop den igen, och det är precis
        sådana omtolkningar som ger olika svar i olika lager.
        """
        m = _ADRESS.match(self.s, self.i)
        if not m:
            raise Syntaxfel("SYNTAX", rad,
                            "%r är ingen giltig direktadress" % self.s[self.i:self.i + 12])
        self._fram(m.end() - self.i)
        return Token("ADRESS", m.group(0), rad, kol, m.group(0).upper())

    def _strang(self, rad, kol) -> Token:
        start = self.i
        self._fram()
        while self.i < len(self.s):
            if self.s[self.i] == "$":
                self._fram(2)
                continue
            if self.s[self.i] == "'":
                self._fram()
                text = self.s[start:self.i]
                try:
                    varde = tolka_strangliteral(text)
                except Syntaxfel as f:
                    raise Syntaxfel("SYNTAX", rad, f.text)
                return Token("STRANG", text, rad, kol, varde)
            if self.s[self.i] == "\n":
                break
            self._fram()
        raise Syntaxfel("SYNTAX", rad, "strängliteral som inte avslutas")

    def _tal(self, rad, kol) -> Token:
        start = self.i
        while self._kika().isdigit() or self._kika() == "_":
            self._fram()
        if self._kika() == "#":
            bas_text = self.s[start:self.i].replace("_", "")
            self._fram()
            sif_start = self.i
            while self._kika().isalnum() or self._kika() == "_":
                self._fram()
            siffror = self.s[sif_start:self.i].replace("_", "")
            if bas_text not in ("2", "8", "16"):
                raise Syntaxfel("SYNTAX", rad,
                                "basen %s finns inte i ST; bara 2, 8 och 16" % bas_text)
            try:
                varde = int(siffror, int(bas_text))
            except ValueError:
                raise Syntaxfel("SYNTAX", rad,
                                "%r är inte ett tal i bas %s" % (siffror, bas_text))
            return Token("HELTAL", self.s[start:self.i], rad, kol, varde)
        if self._kika() == "." and self._kika(1) != ".":
            self._fram()
            while self._kika().isdigit() or self._kika() == "_":
                self._fram()
        if self._kika() in ("e", "E"):
            spara = self.i
            self._fram()
            if self._kika() in ("+", "-"):
                self._fram()
            if self._kika().isdigit():
                while self._kika().isdigit():
                    self._fram()
            else:
                self.i = spara
        text = self.s[start:self.i]
        ren = text.replace("_", "")
        if "." in ren or "e" in ren.lower():
            return Token("REAL", text, rad, kol, float(ren))
        return Token("HELTAL", text, rad, kol, int(ren))

    def _ord(self, rad, kol) -> Token:
        start = self.i
        while self._kika().isalnum() or self._kika() == "_":
            self._fram()
        namn = self.s[start:self.i]
        if self._kika() == "#":
            return self._prefixad_literal(namn, rad, kol, start)
        if namn.upper() in NYCKELORD:
            return Token("NYCKELORD", namn, rad, kol)
        return Token("IDENT", namn, rad, kol)

    def _prefixad_literal(self, namn, rad, kol, start) -> Token:
        stor = namn.upper()
        self._fram()
        krop_start = self.i
        if self._kika() == "-":
            self._fram()
        while self._kika().isalnum() or self._kika() in "_.":
            self._fram()
        kropp = self.s[krop_start:self.i]
        text = self.s[start:self.i]
        if stor in ("T", "TIME"):
            ok, varde, skal = tolka_tidliteral(text)
            # Ogiltig form kastas inte här: den blir en anmärkning i validatorn
            # så att alla dåliga literaler i filen syns i samma körning.
            return Token("TID", text, rad, kol, (ok, varde, skal))
        if stor in ("D", "DATE", "TOD", "TIME_OF_DAY", "DT", "DATE_AND_TIME",
                    "LT", "LTIME", "LD", "LDT", "LTOD"):
            raise Syntaxfel("SYNTAX", rad,
                            "%s-literaler stöds inte av det här lagret" % stor)
        if stor == "BOOL":
            if kropp.upper() in ("TRUE", "FALSE", "0", "1"):
                sant = kropp.upper() in ("TRUE", "1")
                return Token("NYCKELORD", "TRUE" if sant else "FALSE", rad, kol)
            raise Syntaxfel("SYNTAX", rad, "BOOL#%s finns inte" % kropp)
        if stor in ("REAL", "LREAL"):
            try:
                return Token("REAL", text, rad, kol, float(kropp.replace("_", "")),)
            except ValueError:
                raise Syntaxfel("SYNTAX", rad, "%s är ingen giltig literal" % text)
        if stor in NYCKELORD or stor in ("SINT", "INT", "DINT", "LINT", "USINT",
                                         "UINT", "UDINT", "ULINT", "BYTE",
                                         "WORD", "DWORD", "LWORD"):
            try:
                varde = int(kropp.replace("_", ""), 0) if "#" in kropp \
                    else int(kropp.replace("_", ""))
            except ValueError:
                raise Syntaxfel("SYNTAX", rad, "%s är ingen giltig heltalsliteral" % text)
            return Token("HELTAL", text, rad, kol, varde)
        raise Syntaxfel("SYNTAX", rad, "okänt literalprefix %s#" % namn)


def tokenisera(kalla: str) -> List[Token]:
    return Lexer(kalla).tokens()
