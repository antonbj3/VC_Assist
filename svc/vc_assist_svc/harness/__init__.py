# -*- coding: utf-8 -*-
"""LLM-harnessen: det som inte kan brytas, oavsett vad modellen svarar.

    mekanismer.py     namnen pa de tvingande mekanismerna. En kalla
    instruktioner.py  korpusen pa disk: laddning, granskning, diff
    sammansattning.py systemprompten, och vad som kapas nar den inte far plats
    modell.py         modelladaptern och attrappmodellen
    oversattning.py   enda modulen som far namna en leverantor
    text.py           meningsdelning, namn och tal ur modellens text
    forgranskning.py  allt som avvisas INNAN nagot kors
    sakerhet.py       sakerhetsgrinden, ovillkorlig
    arlighet.py       honesty-rewrite
    verifiering.py    verify-contract
    oga.py            ogats dom och guldgrinden
    kanal.py          dar ett godkant anrop utfors
    loop.py           turen, taken och stoppreglerna
    fallor.py         efterlevnadsbankens fallor och kontrollfall
    efterlevnad.py    banken: kor fallorna och rapporterar talen

Instruktionerna ligger som DATA i instruktioner/ i repots rot och laddas med
instruktioner.las_korpus(). Ingen regel ar hardkodad har.

Ingenting i harnessen oppnar en socket. Vagen ut gar genom kanal.py, som far
en fardig verktyg.Utforare av den som startar tjansten.
"""
from __future__ import annotations

from .arlighet import granska as granska_arlighet
from .efterlevnad import Bankresultat, kor_bank
from .fallor import FALLOR, KLASSER, KONTROLLFALL
from .fel import (Budgetfel, Harnessfel, Instruktionsfel, Kanalfel, Modellfel)
from .forgranskning import Avvisning, Forgranskare, GRINDAR, kodblock
from .instruktioner import (Block, Diff, Korpus, Regel, diffa, granska_korpus,
                            las_korpus)
from .kanal import (Anropsutfall, Attrappkanal, Faller, Utforarkanal,
                    Verktygskanal)
from .loop import (Handelse, Harness, MAX_LIKA_ANROP, MAX_OMSKRIVNINGAR,
                   MAX_RAKA_MISSLYCKANDEN, MAX_RUNDOR, Turprotokoll,
                   bygg_harness)
from .mekanismer import MEKANISMER
from .modell import (AttrappModell, Meddelande, Modell, Modellsvar,
                     Verktygsanrop, anropa, sag)
from .oga import granska as granska_oga
from .sakerhet import Sakerhetsgrind
from .sammansattning import (OKAPBARA, STANDARDBUDGET, Systemprompt,
                             bygg_systemprompt)
from .verifiering import Grund
from .verifiering import granska as granska_verifiering

__all__ = [
    "Anropsutfall", "AttrappModell", "Attrappkanal", "Avvisning",
    "Bankresultat", "Block", "Budgetfel", "Diff", "FALLOR", "Faller",
    "Forgranskare", "GRINDAR", "Grund", "Handelse", "Harness", "Harnessfel",
    "Instruktionsfel", "KLASSER", "KONTROLLFALL", "Kanalfel", "Korpus",
    "MAX_LIKA_ANROP", "MAX_OMSKRIVNINGAR", "MAX_RAKA_MISSLYCKANDEN",
    "MAX_RUNDOR", "MEKANISMER", "Meddelande", "Modell", "Modellfel",
    "Modellsvar", "OKAPBARA", "Regel", "STANDARDBUDGET", "Sakerhetsgrind",
    "Systemprompt", "Turprotokoll", "Utforarkanal", "Verktygsanrop",
    "Verktygskanal", "anropa", "bygg_harness", "bygg_systemprompt", "diffa",
    "granska_arlighet", "granska_korpus", "granska_oga",
    "granska_verifiering", "kodblock", "kor_bank", "las_korpus", "sag",
]
