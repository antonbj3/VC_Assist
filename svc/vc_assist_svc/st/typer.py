# -*- coding: utf-8 -*-
"""Typsystem för IEC 61131-3 Structured Text.

Källa: docs/spec/60_plc.md (PLC-benet), docs/spec/90_invarianter.md (I3 fail-closed).

Hela filen lyder under en regel: **en konvertering som inte är bevisat
förlustfri är förbjuden.** Hellre ett explicit INT_TO_REAL i koden än en tyst
avhuggning i fält. Det gör att typkontrollen kan fälla utan att gissa.

Talen i tabellerna är inte valda här. Heltalens intervall står i
IEC 61131-3 (3:e utg.) tabell 10; mantissbredderna i IEEE 754-2008.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


class Typ:
    """Bas för alla typer. Underklasserna är frysta och jämförbara."""

    def st(self) -> str:
        raise NotImplementedError


# ---- elementära typer ----------------------------------------------------
#
# (bitar, har_tecken, min, max). IEC 61131-3 tabell 10.
HELTAL = {
    "SINT": (8, True, -128, 127),
    "INT": (16, True, -32768, 32767),
    "DINT": (32, True, -2147483648, 2147483647),
    "LINT": (64, True, -9223372036854775808, 9223372036854775807),
    "USINT": (8, False, 0, 255),
    "UINT": (16, False, 0, 65535),
    "UDINT": (32, False, 0, 4294967295),
    "ULINT": (64, False, 0, 18446744073709551615),
}

# Mantissans bredd i bitar, IEEE 754-2008. Styr vilka heltal som får bli
# flyttal utan att tappa precision.
FLYT_MANTISSA = {"REAL": 24, "LREAL": 53}

# Bitsträngar. Bredden står i IEC 61131-3 tabell 10.
BITSTRANG = {"BYTE": 8, "WORD": 16, "DWORD": 32, "LWORD": 64}

ELEMENTARA = set(HELTAL) | set(FLYT_MANTISSA) | set(BITSTRANG) | {"BOOL", "TIME"}


@dataclass(frozen=True)
class Elementar(Typ):
    namn: str

    def __post_init__(self):
        if self.namn not in ELEMENTARA:
            raise ValueError("okänd elementär typ: %r" % (self.namn,))

    def st(self) -> str:
        return self.namn


@dataclass(frozen=True)
class Strang(Typ):
    """STRING eller STRING[n]. langd=None betyder odeklarerad längd."""

    langd: Optional[int] = None

    def st(self) -> str:
        return "STRING" if self.langd is None else "STRING[%d]" % self.langd


@dataclass(frozen=True)
class Falt(Typ):
    """ARRAY [lo..hi, ...] OF typ."""

    element: Typ
    granser: Tuple[Tuple[int, int], ...]

    def __post_init__(self):
        if not self.granser:
            raise ValueError("ett fält utan gränser är inget fält")
        for lo, hi in self.granser:
            if hi < lo:
                raise ValueError("fältgräns %d..%d går baklänges" % (lo, hi))

    def st(self) -> str:
        omr = ", ".join("%d..%d" % g for g in self.granser)
        return "ARRAY [%s] OF %s" % (omr, self.element.st())


@dataclass(frozen=True)
class Pekare(Falt):
    """REF_TO typ — pekartyp i IEC 61131-3 (3:e utg.)."""

    element: Typ
    granser: Tuple[Tuple[int, int], ...] = field(default=(), init=False)

    def __post_init__(self):
        pass

    def st(self) -> str:
        return "REF_TO %s" % self.element.st()


@dataclass(frozen=True)
class Strukturtyp(Typ):
    """Hänvisning till en egen STRUCT deklarerad i TYPE ... END_TYPE."""

    namn: str

    def st(self) -> str:
        return self.namn


@dataclass(frozen=True)
class Blocktyp(Typ):
    """Instanstyp för ett funktionsblock: TON, R_TRIG, egen FB."""

    namn: str

    def st(self) -> str:
        return self.namn


@dataclass(frozen=True)
class Literaltyp(Typ):
    """Typen hos en literal innan den bundits till en deklarerad typ.

    En heltalsliteral är polymorf: 5 får bli INT, DINT eller REAL. Den binds
    av sitt mål, och intervallet kontrolleras då. Det är skillnaden mot att
    gissa en typ åt den.
    """

    klass: str          # HELTAL | REAL | BOOL | TID | STRANG
    varde: object = None

    def st(self) -> str:
        return "literal:%s" % self.klass


BOOL = Elementar("BOOL")
TIME = Elementar("TIME")


# ---- vidgning ------------------------------------------------------------
#
# Direkta, bevisat förlustfria steg. Transitiv slutning byggs nedan.
_DIREKT = {
    "SINT": {"INT"},
    "INT": {"DINT"},
    "DINT": {"LINT"},
    "USINT": {"UINT", "INT"},
    "UINT": {"UDINT", "DINT"},
    "UDINT": {"ULINT", "LINT"},
    "BYTE": {"WORD"},
    "WORD": {"DWORD"},
    "DWORD": {"LWORD"},
    "REAL": {"LREAL"},
}
# Heltal till flyttal: tillåtet först när heltalets bitbredd ryms i mantissan.
# 16 < 24 ger INT -> REAL; 32 > 24 ger inte DINT -> REAL.
for _namn, (_bitar, _tecken, _lo, _hi) in HELTAL.items():
    for _flyt, _mantissa in FLYT_MANTISSA.items():
        _behov = _bitar if _tecken else _bitar + 1
        if _behov <= _mantissa:
            _DIREKT.setdefault(_namn, set()).add(_flyt)


def _slutning(start: str) -> set:
    sedda = set()
    kant = [start]
    while kant:
        n = kant.pop()
        for m in _DIREKT.get(n, ()):
            if m not in sedda:
                sedda.add(m)
                kant.append(m)
    return sedda


VIDGNING = dict((n, _slutning(n)) for n in set(_DIREKT) | set(ELEMENTARA))


def far_vidgas(fran: str, till: str) -> bool:
    return fran == till or till in VIDGNING.get(fran, ())


# ---- tilldelningsregeln --------------------------------------------------

def _heltalsliteral_ryms(varde: int, mal: Typ) -> Tuple[bool, str]:
    if isinstance(mal, Elementar) and mal.namn in HELTAL:
        _b, _t, lo, hi = HELTAL[mal.namn]
        if lo <= varde <= hi:
            return True, ""
        return False, "literalen %d ligger utanför %s (%d..%d)" % (varde, mal.namn, lo, hi)
    if isinstance(mal, Elementar) and mal.namn in FLYT_MANTISSA:
        tak = 1 << FLYT_MANTISSA[mal.namn]
        if abs(varde) <= tak:
            return True, ""
        return False, ("literalen %d är större än %s:s exakta heltalsområde (2^%d)"
                       % (varde, mal.namn, FLYT_MANTISSA[mal.namn]))
    if isinstance(mal, Elementar) and mal.namn in BITSTRANG:
        if 0 <= varde < (1 << BITSTRANG[mal.namn]):
            return True, ""
        return False, "literalen %d ryms inte i %s" % (varde, mal.namn)
    return False, "en heltalsliteral kan inte tilldelas %s" % mal.st()


def _typ_av_init(u: object) -> Optional[Typ]:
    if getattr(u, "typnamn", None):
        return Elementar(getattr(u, "typnamn"))
    klass = getattr(u, "klass", None)
    if klass:
        if klass == "BOOL":
            return BOOL
        if klass == "TID":
            return TIME
        return Literaltyp(klass, getattr(u, "varde", None))
    if getattr(u, "op", None) and hasattr(u, "operand"):
        op = getattr(u, "op")
        sub = _typ_av_init(getattr(u, "operand"))
        if op == "NOT":
            return BOOL
        if op == "-" and isinstance(sub, Literaltyp) and sub.klass in ("HELTAL", "REAL"):
            varde = sub.varde
            return Literaltyp(sub.klass, -varde if varde is not None else None)
        return sub
    return None


def far_tilldelas(mal: Typ, kalla: Typ) -> Tuple[bool, str]:
    """Får ett värde av typen `kalla` skrivas till ett mål av typen `mal`?

    Returnerar (ja, skäl). Skälet är tomt när svaret är ja, annars den mening
    som hamnar i anmärkningen.
    """
    if isinstance(kalla, Literaltyp):
        if kalla.klass == "NULL":
            if isinstance(mal, Pekare):
                return True, ""
            return False, "NULL kan bara tilldelas REF_TO-typer, inte %s" % mal.st()
        if kalla.klass == "HELTAL":
            return _heltalsliteral_ryms(int(kalla.varde), mal)
        if kalla.klass == "REAL":
            if isinstance(mal, Elementar) and mal.namn in FLYT_MANTISSA:
                return True, ""
            return False, "en flyttalsliteral kan inte tilldelas %s" % mal.st()
        if kalla.klass == "BOOL":
            if mal == BOOL:
                return True, ""
            return False, "TRUE/FALSE kan bara tilldelas BOOL, inte %s" % mal.st()
        if kalla.klass == "TID":
            if mal == TIME:
                return True, ""
            return False, "en TIME-literal kan bara tilldelas TIME, inte %s" % mal.st()
        if kalla.klass == "STRANG":
            if isinstance(mal, Strang):
                langd = len(kalla.varde or "")
                if mal.langd is None or langd <= mal.langd:
                    return True, ""
                return False, ("strängliteralen är %d tecken, målet rymmer %d"
                               % (langd, mal.langd))
            return False, "en strängliteral kan inte tilldelas %s" % mal.st()
        if kalla.klass == "FALT":
            if not isinstance(mal, Falt):
                return False, "en fältinitierare kan bara tilldelas ett fält, inte %s" % mal.st()
            kapacitet = 1
            for lo, hi in mal.granser:
                kapacitet *= (hi - lo + 1)
            element_lista = kalla.varde or ()
            totalt_antal = 0
            for elem in element_lista:
                antal = elem.antal if elem.antal is not None else 1
                totalt_antal += antal
                elem_typ = _typ_av_init(elem.varde)
                if elem_typ is None:
                    return False, "ogiltigt uttryck i fältinitierare"
                ok, skal = far_tilldelas(mal.element, elem_typ)
                if not ok:
                    return False, skal
            if totalt_antal != kapacitet:
                return False, ("fältet rymmer %d element men initieraren har %d"
                               % (kapacitet, totalt_antal))
            return True, ""
        return False, "okänd literalklass %s" % kalla.klass

    if isinstance(mal, Strang) and isinstance(kalla, Strang):
        if mal.langd is None:
            return True, ""
        if kalla.langd is None:
            return False, ("källans STRING saknar deklarerad längd; %s kan huggas av"
                           % mal.st())
        if kalla.langd <= mal.langd:
            return True, ""
        return False, "STRING[%d] ryms inte i STRING[%d]" % (kalla.langd, mal.langd)

    if isinstance(mal, Elementar) and isinstance(kalla, Elementar):
        if mal.namn == kalla.namn:
            return True, ""
        if far_vidgas(kalla.namn, mal.namn):
            return True, ""
        return False, ("%s kan inte tilldelas %s utan uttrycklig konvertering (%s_TO_%s)"
                       % (kalla.namn, mal.namn, kalla.namn, mal.namn))

    if mal == kalla:
        return True, ""

    if isinstance(mal, Blocktyp) or isinstance(kalla, Blocktyp):
        return False, "en funktionsblocksinstans kan inte tilldelas"

    return False, "%s kan inte tilldelas %s" % (kalla.st(), mal.st())


def gemensam_typ(a: Typ, b: Typ) -> Optional[Typ]:
    """Typen ett tvåställigt uttryck får, eller None om de inte går ihop.

    None betyder "vet inte", och vet-inte är aldrig godkänt (I3).
    """
    if isinstance(a, Literaltyp) and isinstance(b, Literaltyp):
        if a.klass == b.klass:
            return a
        if {a.klass, b.klass} == {"HELTAL", "REAL"}:
            return Literaltyp("REAL", None)
        return None
    if isinstance(a, Literaltyp):
        return b if far_tilldelas(b, a)[0] else None
    if isinstance(b, Literaltyp):
        return a if far_tilldelas(a, b)[0] else None
    if a == b:
        return a
    if isinstance(a, Elementar) and isinstance(b, Elementar):
        if far_vidgas(a.namn, b.namn):
            return b
        if far_vidgas(b.namn, a.namn):
            return a
    return None


def ar_numerisk(t: Typ) -> bool:
    if isinstance(t, Literaltyp):
        return t.klass in ("HELTAL", "REAL")
    return isinstance(t, Elementar) and (t.namn in HELTAL or t.namn in FLYT_MANTISSA)


def ar_heltal(t: Typ) -> bool:
    if isinstance(t, Literaltyp):
        return t.klass == "HELTAL"
    return isinstance(t, Elementar) and t.namn in HELTAL


def ar_bitlogisk(t: Typ) -> bool:
    """BOOL och bitsträngar; typerna som AND/OR/XOR/NOT är definierade för."""
    if isinstance(t, Literaltyp):
        return t.klass == "BOOL"
    return isinstance(t, Elementar) and (t.namn == "BOOL" or t.namn in BITSTRANG)


def ar_tid(t: Typ) -> bool:
    if isinstance(t, Literaltyp):
        return t.klass == "TID"
    return t == TIME


NOLLVARDE = {
    "BOOL": "FALSE",
    "TIME": "T#0s",
}


def nollvarde_text(t: Typ) -> str:
    """ST-texten för "avstängt" i typen. Kastar hellre än gissar.

    Används av sekvensbyggaren när nödstoppsgrenen ska nolla utgångarna.
    En typ vi inte vet nolläget för får inte tyst hoppas över: då blir en
    utgång kvar hög under nödstopp, och det är precis felet vi bygger mot.
    """
    if isinstance(t, Elementar):
        if t.namn in NOLLVARDE:
            return NOLLVARDE[t.namn]
        if t.namn in HELTAL or t.namn in BITSTRANG:
            return "0"
        if t.namn in FLYT_MANTISSA:
            return "0.0"
    if isinstance(t, Strang):
        return "''"
    if isinstance(t, Pekare):
        return "NULL"
    raise ValueError("vet inte hur %s nollas; utgången kan inte återställas säkert"
                     % t.st())
