# -*- coding: utf-8 -*-
"""Anmärkningar och deras felklass.

Felklasserna kommer ur docs/spec/82_felklasser.md och ändras inte här. Två
kontroller i det här lagret har **ingen** klass i den tabellen, och de får då
`felklass=None` i stället för att stoppas in i F14: specen säger uttryckligen
att F14 ska hållas nära noll och att en växande F14 betyder att taxonomin ska
revideras, inte fyllas på. De två är OATKOMLIG och SAKERHET. Det är en öppen
fråga till specen, inte ett hål i grinden — båda fäller ändå.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# kod -> (felklass enligt 82_felklasser.md, vad kontrollen fäller)
KONTROLLER = {
    "BALANS": ("F1", "block som inte avslutas, eller avslutas med fel END_"),
    "SYNTAX": ("F1", "text som inte är giltig ST: otolkbar sats, källa utan POU, EXIT utanför slinga"),
    "TIDLITERAL": ("F1", "TIME-literal med ogiltig form"),
    "ODEKLARERAD": ("F4", "namn som används utan att vara deklarerat"),
    "DUBBELDEKLARATION": ("F4", "samma namn deklarerat två gånger i samma POU"),
    "OKANT_NAMN": ("F2", "okänt funktionsblock, okänd funktion, okänt fält"),
    "ARGUMENT": ("F2", "fel argumentnamn, fel antal argument"),
    "TYP": ("F4", "tilldelning eller uttryck där typerna inte går ihop"),
    "RIKTNING": ("F4", "skrivning till VAR_INPUT, CONSTANT eller styrvariabel"),
    "DUBBELSKRIVNING": ("F7", "samma utgång skriven på två ställen i samma scan"),
    # F7 i tabellen är den dynamiska kapplöpningen som ögat ser. Den här är
    # dess statiska skugga: samma fel, upptäckt före körning.
    "OATKOMLIG": (None, "kod som aldrig kan köras"),
    "SAKERHET": (None, "skrivning till en tagg märkt {SAKERHET} (I15)"),
}


@dataclass(frozen=True)
class Anmarkning:
    kod: str
    rad: int
    text: str

    @property
    def felklass(self) -> Optional[str]:
        return KONTROLLER[self.kod][0]

    def __str__(self):
        klass = self.felklass or "-"
        return "rad %d: [%s/%s] %s" % (self.rad, self.kod, klass, self.text)


class Syntaxfel(Exception):
    """Kastas av lexer och läsare. Fångas av validatorn och blir anmärkning."""

    def __init__(self, kod, rad, text):
        Exception.__init__(self, "rad %d: %s" % (rad, text))
        self.kod = kod
        self.rad = rad
        self.text = text


class SkrivFel(Exception):
    """Skrivaren vägrar producera text som inte går att lita på."""
