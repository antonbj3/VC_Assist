# -*- coding: utf-8 -*-
"""Planeringslagret: VAD som ska goras, och i VILKEN ORDNING.

Det fanns verktyg (verktyg/) och en domare (guldgrind.py, ogat), men
ingenting som bestamde vad som skulle goras och i vilken ordning. Det ar det
har lagret.

    spec.py         de tre nivaerna: grundbegaran, detaljerad spec, och
                    vardeobjekten daremellan. JSON in och ut, identiskt.
    harkomst.py     varifran varje krav kom, i en form som gar att sla upp
    lasning.py      vad som gar att lasa UR operatorens text, med belagg
    storheter.py    den slutna listan av storheter ett villkor far handla om
    villkorssprak.py  villkoret sjalvt: typat, relation eller markt prosakrav
    processer.py    ordningen av processer i cellen, med samma cykelkrav
    motsagelse.py   nar bestallningen inte gar att uppfylla, och VILKA villkor
                    som krockar
    ordning.py      cykler och kanonisk topologisk ordning, delad
    forfining.py    grundbegaran -> detaljerad spec. Allt som behovs men inte
                    star i begaran blir ett ANTAGANDE med motiv eller en
                    FRAGA. Aldrig ett tyst val.
    verifiering.py  vad planen ska BEVISA, i ogats egen grammatik. En plan
                    utan verifiering ar en kandidat, aldrig en leverans.
    predikat.py     spraket forvillkor och kontroller ar skrivna i
    steg.py         ett steg: ett verktygsanrop eller en kontroll. Plus
                    bindningar, som laser varden UR SCENEN i stallet for att
                    hitta pa dem.
    graf.py         beroenden, alternativ, parallellitet, cykeldetektering och
                    en DETERMINISTISK topologisk ordning
    byggplan.py     planen provad mot det verkliga verktygsregistret
    planering.py    detaljerad spec -> byggplan
    layoutport.py   porten mot layoutmotorn; det enda stalle koordinater
                    kommer in i en plan
    korning.py      koraren: kor stegen, for protokoll, kan aterupptas
    provplaner.py   tio och fler provplaner ur banken, med matning

De fyra reglerna som ar mekaniska och inte overenskomna:

  * ett steg vars verktyg inte finns i registret avvisas VID PLANERINGEN
  * ett steg vars argument inte haller schemat avvisas VID PLANERINGEN
  * routingen read->exec / write->exec_queue ags av utforaren; planen bar
    inget falt for den och lasningen avvisar nycklarna (I12)
  * en cykel i grafen upptacks och rapporteras med sina steg, aldrig som en
    oandlig loop

Endast standardbiblioteket. Kors utan VC (L0/L1 i docs/spec/95_testprotokoll.md).
"""
from __future__ import annotations

from .byggplan import Byggplan, LINTKODER, OMFATTNINGAR
from .fel import (Graffel, Korningsfel, Layoutfel, Planfel, Specfel,
                  Verifieringsfel)
from .forfining import Forfinare, ur_bankuppgift, ur_fritext
from .graf import Uppgiftsgraf
from .korning import (EJ_UTFORD, FALLEN, HOPPAD, KOAD, KORD, Korare, Post,
                      Protokoll, godkann_aldrig)
from .layoutport import Layoutport, Layoutsvar, Placering, begaran_ur_spec
from .planering import Planerare, planera
from .predikat import Forvillkor, Korlage, Predikat
from .harkomst import Harkomst
from .motsagelse import Motsagelsedom, Krock
from .processer import Ordningskrav, Process, Processordning
from .spec import (Antagande, Del, DetaljeradSpec, Fraga, Grundbegaran,
                   Koppling, Omrade, Signal, Takt)
from .storheter import Faktarum, Varde
from .villkorssprak import Prosakrav, Relation, Typvillkor
from .steg import Bindning, Kontroll, Steg
from .verifiering import (Krav, Uppskjutet, Verifieringsdom, Verifieringskrav)

__all__ = [
    "Antagande", "Bindning", "Byggplan", "Del", "DetaljeradSpec", "EJ_UTFORD",
    "Faktarum", "Harkomst", "Krock", "Motsagelsedom", "Omrade",
    "Ordningskrav", "Process", "Processordning", "Prosakrav", "Relation",
    "Typvillkor", "Varde",
    "FALLEN", "Forfinare", "Forvillkor", "Fraga", "Graffel", "Grundbegaran",
    "HOPPAD", "KOAD", "KORD", "Kontroll", "Koppling", "Korare", "Korlage",
    "Korningsfel", "Krav", "LINTKODER", "Layoutfel", "Layoutport",
    "Layoutsvar", "OMFATTNINGAR", "Placering", "Planerare",
    "Planfel", "Post", "Predikat", "Protokoll", "Signal", "Specfel", "Steg", "Takt",
    "Uppgiftsgraf", "Uppskjutet", "Verifieringsdom", "Verifieringsfel",
    "Verifieringskrav", "begaran_ur_spec", "godkann_aldrig",
    "planera", "ur_bankuppgift", "ur_fritext",
]
