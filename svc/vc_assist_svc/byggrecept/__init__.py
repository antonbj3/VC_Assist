# -*- coding: utf-8 -*-
"""Byggrecept: kod som bygger komponenter som kan koppla ihop sig i VC.

Specen ar docs/spec/49_komponentmodellen.md. Hypoteserna ar data i
hypoteser.py, recepten ar kodgeneratorer i recept.py:

    generera("sondera_falt", {})            matinstrumentet, kor detta forst
    generera("transportor", {"name": ...})  bana med in- och utgranssnitt
    generera("buffert", {...})              ackumulerande bana med N platser
    generera("matare", {...})               skapare med utgranssnitt
    generera("sanka", {...})                osynlig behallare med ingranssnitt
    generera("koppla", {"a": ..., "b": ...})  provar kopplingsvagarna i ordning
    generera("las_flode", {})               LASANDE: rorde sig nagot?

Koden ar Python 2.7 och 3.x, lamnar JSON pa sista raden av stdout och gar
rakt in i bryggan som ett exec_queue-anrop (den ar skrivande).
"""
from .hypoteser import (BELAGT, HYPOTES, HYPOTESER, MATT, MATTA_KLASSNAMN, PER_ID, Hypotes,
                        per_fraga, provordning)
from .recept import (BEHALLARSTEG, BETEENDEKONSTANTER, BETEENDENAMN, EFFEKT,
                     EXEMPEL, FALTKONSTANTER, FALTNAMN, FALTTYPER, KONTAKTNAMN,
                     RECEPT, generera)

__all__ = [
    "BELAGT", "HYPOTES", "HYPOTESER", "MATT", "MATTA_KLASSNAMN", "PER_ID", "Hypotes",
    "per_fraga", "provordning",
    "BEHALLARSTEG", "BETEENDEKONSTANTER", "BETEENDENAMN", "EFFEKT", "EXEMPEL",
    "FALTKONSTANTER", "FALTNAMN", "FALTTYPER", "KONTAKTNAMN", "RECEPT",
    "generera",
]
