# -*- coding: utf-8 -*-
"""Förloppsytan: vad användaren ser medan systemet arbetar.

Fas 17 i `70_faser.md`, och den enda fasen som riktar sig till någon utanför
bygget. Operatörens krav, ordagrant: *"användaren vill förmodligen också
gärna kunna veta vad som händer också när saker arbetar."*

Tre delar:

* `handelser` — lägena, den slutna händelselistan och ovissheten
* `yta`       — `Forlopp` (protokollet som förs medan körningen pågår)
                och `rendera` (texten)
* `grind`     — `granska`, som dömer PARET protokoll och text och därför
                fäller vilken renderare som helst, också en som inte finns än
* `kallor`    — hur kopplaren, stationsgrinden, reparationsslingan,
                guldgrinden och planen matar förloppet

Ytan är TEXT. Hur den sedan visas — terminal, webbsida, panel — är ett senare
beslut (`26_appen.md` §7, öppen fråga 1), och att bygga ett fönster nu vore
att låsa det beslutet i förväg. Grinden binder ändå den framtida ytan: den
dömer texten, inte renderaren.
"""
from .grind import (Brott, Forloppsdom, REGLER, granska, granska_eller_kasta)
from .handelser import (ABSORBERANDE, ARBETAR, AVBRUTET, EJ_FRAMSTEG,
                        EJ_PROVAT, EJ_STARTAT, FALLET, Forloppsfel, Handelse,
                        KLART, LAGEN, Ovisshet, PAGAR_MARKOR, RACKVIDDEN,
                        SLUTLIGA, SORTER, SPECADE_SORTER, STILLA, Steg,
                        TILLAGDA_SORTER, TYST, UTANFOR_RACKVIDD, VANTAR)
from .kallor import (fran_guldbeslut, fran_kopplarvarv, fran_ogonkoppling,
                     fran_planprotokoll, fran_reparationsprotokoll,
                     fran_stationsdom, kor_kopplaren)
from .yta import (Forlopp, MAX_HANDELSERADER, OBLIGATORISKA_SEKTIONER,
                  RUBRIK_VET_INTE, SAKNAS, SEKTION_SAKNAS, TYSTNADSTAK_S,
                  okorda_steg, rendera,
                  saknade_sektioner)

__all__ = [
    "ABSORBERANDE", "ARBETAR", "AVBRUTET", "Brott", "EJ_FRAMSTEG",
    "EJ_PROVAT", "EJ_STARTAT", "FALLET", "Forlopp", "Forloppsdom",
    "Forloppsfel", "Handelse", "KLART", "LAGEN", "MAX_HANDELSERADER",
    "OBLIGATORISKA_SEKTIONER", "Ovisshet", "PAGAR_MARKOR", "RACKVIDDEN",
    "REGLER", "RUBRIK_VET_INTE", "SAKNAS", "SEKTION_SAKNAS", "SLUTLIGA",
    "SORTER", "SPECADE_SORTER", "STILLA", "Steg", "TILLAGDA_SORTER",
    "TYST", "TYSTNADSTAK_S", "UTANFOR_RACKVIDD", "VANTAR",
    "fran_guldbeslut", "fran_kopplarvarv", "fran_ogonkoppling",
    "fran_planprotokoll", "fran_reparationsprotokoll", "fran_stationsdom",
    "granska", "granska_eller_kasta", "kor_kopplaren", "okorda_steg",
    "rendera",
    "saknade_sektioner",
]
