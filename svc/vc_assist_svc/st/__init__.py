# -*- coding: utf-8 -*-
"""ST-lagret: modell, skrivare, läsare, validator och sekvensbyggare.

Ett lager som ska göra det svårt att generera fel ST och lätt att upptäcka när
det ändå skedde. Fyra delar, en riktning:

    Sekvens  --bygg-->  Pou  --skriv_pou-->  text  --validera-->  Rapport
                         ^                     |
                         +-------- las --------+

Skrivaren och läsaren ligger i samma lager mot samma modell, så de kan inte
drifta isär utan att turen-och-retur-provet fäller. Samma grepp som ögats
domskontrakt (docs/spec/41_ogat_kontrakt.md).

Vad lagret INTE gör: det kompilerar ingenting. Grind 1 i docs/spec/50_grindar.md
är STruC++ och den är inte körd här. Validatorn är grind 2, statisk analys, och
den ersätter inte kompilatorn.
"""
from .fel import Anmarkning, KONTROLLER, SkrivFel, Syntaxfel
from .lasare import las
from .lexer import tokenisera, tolka_tidliteral
from .modell import (Anrop, Anropssats, Argument, Avbryt, Binar, Deklaration,
                     Element, Enhet, Etikett, Fall, Fallgren, ForSats, Gren,
                     Kommentar, Literal, Medan, Medlem, Namn, Om, Pou, Retur,
                     Sats, Strukturdef, Tilldelning, Unar, Upprepa, Uttryck,
                     Varblock)
from .sekvens import Sekvens, SekvensFel, Steg, bygg, bygg_text
from .skrivare import skriv_enhet, skriv_pou, skriv_satser, skriv_uttryck
from .typer import (Blocktyp, Elementar, Falt, Literaltyp, Strang, Strukturtyp,
                    Typ, far_tilldelas)
from .validator import Rapport, validera

__all__ = [
    "Anmarkning", "KONTROLLER", "SkrivFel", "Syntaxfel",
    "las", "tokenisera", "tolka_tidliteral",
    "Anrop", "Anropssats", "Argument", "Avbryt", "Binar", "Deklaration",
    "Element", "Enhet", "Etikett", "Fall", "Fallgren", "ForSats", "Gren",
    "Kommentar", "Literal", "Medan", "Medlem", "Namn", "Om", "Pou", "Retur",
    "Sats", "Strukturdef", "Tilldelning", "Unar", "Upprepa", "Uttryck",
    "Varblock",
    "Sekvens", "SekvensFel", "Steg", "bygg", "bygg_text",
    "skriv_enhet", "skriv_pou", "skriv_satser", "skriv_uttryck",
    "Blocktyp", "Elementar", "Falt", "Literaltyp", "Strang", "Strukturtyp",
    "Typ", "far_tilldelas",
    "Rapport", "validera",
]
