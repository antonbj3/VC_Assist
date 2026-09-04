# -*- coding: utf-8 -*-
"""Datamodell för Structured Text.

En modell, inte en textbuffert. Skrivaren gör text av den och läsaren gör den
av text, och det är samma modell åt båda hållen — precis som ögats kontrakt
har skrivare och läsare i samma fil så att de inte kan drifta isär
(docs/spec/41_ogat_kontrakt.md).

Alla noder är frysta dataklasser. Radnumret bär inte jämförelse: två modeller
som beskriver samma program är lika även om de lästes ur olika filer.

Källa: docs/spec/60_plc.md, IEC 61131-3 (3:e utg.) avsnitt om ST.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from .typer import Typ


def _rad():
    """Radnummer följer med noden men styr aldrig likhet."""
    return field(default=0, compare=False)


# ---- uttryck -------------------------------------------------------------

class Uttryck:
    pass


@dataclass(frozen=True)
class Namn(Uttryck):
    """En identifierare. ST är skiftlägesokänsligt; originalskiftet bevaras."""

    ident: str
    rad: int = _rad()


@dataclass(frozen=True)
class Medlem(Uttryck):
    """bas.falt — utgång på en blockinstans, eller fält i en struktur."""

    bas: Uttryck
    falt: str
    rad: int = _rad()


@dataclass(frozen=True)
class Element(Uttryck):
    """bas[i] eller bas[i, j]."""

    bas: Uttryck
    index: Tuple[Uttryck, ...]
    rad: int = _rad()


@dataclass(frozen=True)
class Literal(Uttryck):
    """klass: HELTAL | REAL | BOOL | TID | STRANG.

    `text` är exakt vad som ska skrivas ut, `varde` det tolkade värdet.
    Att båda finns är avsikten: skrivaren är då byte-trogen mot indata,
    och typkontrollen slipper tolka text.
    """

    klass: str
    text: str
    varde: object = None
    typnamn: Optional[str] = None       # INT#5 ger typnamn="INT"
    rad: int = _rad()


@dataclass(frozen=True)
class Binar(Uttryck):
    op: str
    vanster: Uttryck
    hoger: Uttryck
    rad: int = _rad()


@dataclass(frozen=True)
class Unar(Uttryck):
    op: str                              # NOT eller -
    operand: Uttryck
    rad: int = _rad()


@dataclass(frozen=True)
class Argument:
    """Ett argument i ett anrop.

    namn=None är positionellt. ut=True är utgångsbindningen `Q => klar`.
    """

    uttryck: Uttryck
    namn: Optional[str] = None
    ut: bool = False
    rad: int = _rad()


@dataclass(frozen=True)
class Anrop(Uttryck):
    namn: str
    argument: Tuple[Argument, ...] = ()
    rad: int = _rad()


# ---- satser --------------------------------------------------------------

class Sats:
    pass


@dataclass(frozen=True)
class Tilldelning(Sats):
    mal: Uttryck
    uttryck: Uttryck
    rad: int = _rad()


@dataclass(frozen=True)
class Gren:
    villkor: Uttryck
    satser: Tuple[Sats, ...]
    rad: int = _rad()


@dataclass(frozen=True)
class Om(Sats):
    """IF/ELSIF/ELSE. Första grenen är IF, resten ELSIF."""

    grenar: Tuple[Gren, ...]
    annars: Optional[Tuple[Sats, ...]] = None
    rad: int = _rad()


@dataclass(frozen=True)
class Etikett:
    """En CASE-etikett: ett värde, eller ett område lo..hi."""

    fran: int
    till: Optional[int] = None

    def varden(self):
        if self.till is None:
            return (self.fran,)
        return tuple(range(self.fran, self.till + 1))


@dataclass(frozen=True)
class Fallgren:
    etiketter: Tuple[Etikett, ...]
    satser: Tuple[Sats, ...]
    rad: int = _rad()


@dataclass(frozen=True)
class Fall(Sats):
    """CASE uttryck OF ... ELSE ... END_CASE."""

    uttryck: Uttryck
    grenar: Tuple[Fallgren, ...]
    annars: Optional[Tuple[Sats, ...]] = None
    rad: int = _rad()


@dataclass(frozen=True)
class ForSats(Sats):
    styrvar: str
    fran: Uttryck
    till: Uttryck
    steg: Optional[Uttryck]
    satser: Tuple[Sats, ...]
    rad: int = _rad()


@dataclass(frozen=True)
class Medan(Sats):
    villkor: Uttryck
    satser: Tuple[Sats, ...]
    rad: int = _rad()


@dataclass(frozen=True)
class Upprepa(Sats):
    satser: Tuple[Sats, ...]
    villkor: Uttryck                     # UNTIL villkor
    rad: int = _rad()


@dataclass(frozen=True)
class Avbryt(Sats):
    rad: int = _rad()


@dataclass(frozen=True)
class Retur(Sats):
    rad: int = _rad()


@dataclass(frozen=True)
class Anropssats(Sats):
    anrop: Anrop
    rad: int = _rad()


@dataclass(frozen=True)
class Kommentar(Sats):
    """Fristående kommentarrad. Bärs i modellen för att den ska överleva en
    tur och retur genom läsaren; annars vore skrivarens utdata inte ett
    kontrakt utan bara ungefär rätt."""

    text: str
    rad: int = _rad()


# ---- deklarationer -------------------------------------------------------

VARSORTER = ("VAR", "VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT", "VAR_GLOBAL",
             "VAR_EXTERNAL", "VAR_TEMP")
KVALIFICERARE = ("CONSTANT", "RETAIN", "NON_RETAIN")


@dataclass(frozen=True)
class Deklaration:
    namn: str
    typ: Typ
    init: Optional[Uttryck] = None
    adress: Optional[str] = None         # AT %QX0.0, ur signalkartan
    skyddad: bool = False                # {SAKERHET}: skrivskyddad (I15)
    kommentar: Optional[str] = None
    rad: int = _rad()


@dataclass(frozen=True)
class Varblock:
    sort: str
    deklarationer: Tuple[Deklaration, ...]
    kvalificerare: Tuple[str, ...] = ()
    rad: int = _rad()

    def __post_init__(self):
        if self.sort not in VARSORTER:
            raise ValueError("okänd VAR-sort: %r" % (self.sort,))
        for k in self.kvalificerare:
            if k not in KVALIFICERARE:
                raise ValueError("okänd kvalificerare: %r" % (k,))


POUSORTER = ("PROGRAM", "FUNCTION_BLOCK", "FUNCTION")


@dataclass(frozen=True)
class Pou:
    sort: str
    namn: str
    block: Tuple[Varblock, ...] = ()
    kropp: Tuple[Sats, ...] = ()
    returtyp: Optional[Typ] = None       # endast FUNCTION
    rad: int = _rad()

    def __post_init__(self):
        if self.sort not in POUSORTER:
            raise ValueError("okänd POU-sort: %r" % (self.sort,))
        if self.sort == "FUNCTION" and self.returtyp is None:
            raise ValueError("en FUNCTION utan returtyp går inte att deklarera")
        if self.sort != "FUNCTION" and self.returtyp is not None:
            raise ValueError("bara en FUNCTION har returtyp")

    def deklarationer(self):
        for b in self.block:
            for d in b.deklarationer:
                yield b, d


@dataclass(frozen=True)
class Strukturdef:
    namn: str
    falt: Tuple[Deklaration, ...]
    rad: int = _rad()


@dataclass(frozen=True)
class Enhet:
    """En ST-fil: typdefinitioner, globala block och POU:er i skrivordning."""

    typer: Tuple[Strukturdef, ...] = ()
    globala: Tuple[Varblock, ...] = ()
    pouer: Tuple[Pou, ...] = ()
