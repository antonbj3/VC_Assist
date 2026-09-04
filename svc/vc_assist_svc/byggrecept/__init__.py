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

Koden ar Python 2.7 och 3.x, lamnar JSON pa sista raden av stdout och gar
rakt in i bryggan som ett exec_queue-anrop (den ar skrivande).
"""
from .hypoteser import (BELAGT, HYPOTES, HYPOTESER, MATT, PER_ID, Hypotes,
                        per_fraga, provordning)
from .recept import (BETEENDEKONSTANTER, EXEMPEL, FALTKONSTANTER, FALTNAMN,
                     FALTTYPER, RECEPT, REFERENSNAMN, generera)

__all__ = [
    "BELAGT", "HYPOTES", "HYPOTESER", "MATT", "PER_ID", "Hypotes",
    "per_fraga", "provordning",
    "BETEENDEKONSTANTER", "EXEMPEL", "FALTKONSTANTER", "FALTNAMN",
    "FALTTYPER", "RECEPT", "REFERENSNAMN", "generera",
]
