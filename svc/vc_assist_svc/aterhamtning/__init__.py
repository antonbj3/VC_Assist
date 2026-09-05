# -*- coding: utf-8 -*-
"""Återhämtningen: vad användaren ser när något har dött, och om det kommer
tillbaka.

Fas 23 i `70_faser.md`, och den andra halvan av användarlagret. Fas 17 byggde
ytan som visar vad som händer **medan** en körning går. Den här visar vad som
händer när körningen inte längre går — och den är den svårare halvan, för det
som ska tolkas är en tystnad, och tystnad kan bara tolkas av någon annan än
den som tystnade.

Fem delar:

* `lagen`   — lägena, orsakerna, vägarna tillbaka och tabellen som avgör om
              ett försök kan lyckas
* `bild`    — avläsningarna, försöken, och `lage_for` som räknar läget ur dem
* `stegen`  — de sju frågorna som hittar orsaken (`28_lagen...` §5.3)
* `yta`     — texten
* `grind`   — `granska`, som dömer PARET avläsningar och text och därför
              fäller vilken renderare eller härledning som helst
* `kallor`  — hur bryggan, OpenPLC och modellen matar bilden

Ytan är TEXT, av samma skäl som fas 17:s: hur den sedan visas — terminal,
webbsida, panel — är ett öppet beslut (`26_appen.md` §7 fråga 1), och att bygga
ett fönster nu vore att låsa det i förväg. Grinden binder ändå den framtida
ytan.
"""
from .bild import (Avlasning, BILDVERSION, Blick, Forsok, MODAL_OPPEN_RAD,
                   Systembild, T_MODAL_S, T_NERE_S, T_PING_S, blicka,
                   lage_for, las_bild)
from .grind import (Aterhamtningsdom, Brott, REGLER, frammande, granska,
                    granska_eller_kasta)
from .kallor import (degraderad, fran_bryggfel, fran_kopplarfel,
                     fran_kopplarvarv, fran_modellfel,
                     fran_reparationsprotokoll, loggarna, sondera,
                     utan_sjalvstart, vc_avslutades)
from .lagen import (ANSLUTEN, Aterhamtningsfel, BLOCKERAD, BRYGGAN,
                    DEGRADERAD, DELSYSTEM, FORETRADE, FRANKOPPLAD, KAN,
                    KANSKAP, KAN_JA, KAN_NEJ, KAN_OKAND, KO_VANTAR, LAGEN,
                    LEVANDE, MODELLEN, NERE, OBESTAMT, OKAND, ORSAKER,
                    ORSAK_UR_NYCKEL, Orsak, PLC, PROVTAGNING_PAGAR,
                    SIMULERING_IGANG, SPECADE_LAGEN, STILLA, TILLAGDA_LAGEN,
                    UTAN_SJALVSTART, VAGAR, Vag, kan_lyckas, vagarna)
from .stegen import (BOOTLOGG, BRYGGLOGG, STEGEN, Stegdef, Stegsvar,
                     kor_stegen, orsak_ur_stegen, sammanfatta)
from .yta import (ALLVAR, ATERHAMTAR_MARKOR, FORSOKER_MARKOR, INGET_FORSOK,
                  MAX_AVLASNINGSRADER, MAX_BREDD, RACKVIDDEN, RUBRIK_LAGE,
                  allvarligast, mojliga_och_omojliga, ovissheter, rackvidden,
                  rendera)

__all__ = [
    "ALLVAR", "ANSLUTEN", "ATERHAMTAR_MARKOR", "Aterhamtningsdom",
    "Aterhamtningsfel", "Avlasning", "BILDVERSION", "BLOCKERAD", "BOOTLOGG",
    "BRYGGAN", "BRYGGLOGG", "Blick", "Brott", "DEGRADERAD", "DELSYSTEM",
    "FORETRADE", "FORSOKER_MARKOR", "FRANKOPPLAD", "Forsok", "INGET_FORSOK",
    "KAN", "KANSKAP", "KAN_JA", "KAN_NEJ", "KAN_OKAND", "KO_VANTAR", "LAGEN",
    "LEVANDE", "MAX_AVLASNINGSRADER", "MAX_BREDD", "MODAL_OPPEN_RAD",
    "MODELLEN", "NERE", "OBESTAMT", "OKAND", "ORSAKER", "ORSAK_UR_NYCKEL",
    "Orsak", "PLC", "PROVTAGNING_PAGAR", "RACKVIDDEN", "REGLER",
    "RUBRIK_LAGE", "SIMULERING_IGANG", "SPECADE_LAGEN", "STEGEN", "STILLA",
    "Stegdef", "Stegsvar", "Systembild", "T_MODAL_S", "T_NERE_S", "T_PING_S",
    "TILLAGDA_LAGEN", "UTAN_SJALVSTART", "VAGAR", "Vag", "allvarligast",
    "blicka", "degraderad", "frammande", "fran_bryggfel", "fran_kopplarfel",
    "fran_kopplarvarv", "fran_modellfel", "fran_reparationsprotokoll",
    "granska", "granska_eller_kasta", "kan_lyckas", "kor_stegen", "lage_for",
    "las_bild", "loggarna", "mojliga_och_omojliga", "orsak_ur_stegen",
    "ovissheter", "rackvidden", "rendera", "sammanfatta", "sondera",
    "utan_sjalvstart", "vagarna", "vc_avslutades",
]
