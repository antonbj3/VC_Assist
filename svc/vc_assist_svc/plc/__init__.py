# -*- coding: utf-8 -*-
"""PLC-bandet: signalkartan, grind 3, paketeringen och REST-klienten.

Kedjan mellan genererad ST och den simulerade scenen, mätt 2026-09-04 och
beskriven i docs/matningar/M-20_plcbandet.md:

    signalkarta --> VAR-block --> ST --> STruC++ --> projekt.zip
                                                 --> OpenPLC v4 (REST/JWT)
                                                 --> OPC UA-server
                                                 --> VC:s OPC UA-klient --> scenen

Arkitekturen är mätt, inte antagen: Visual Components har ingen ST-motor, och
VC Premiums connectivity är en OPC UA-**klient**. PLC:n måste alltså vara
server, och det är OpenPLC v4:s opcua-plugin som är den servern.

Allt i det här lagret använder **endast standardbiblioteket**. Undantaget är
`matning.py`, som är en mätharness och inte tjänstelager; den beror på asyncua
och exporteras inte härifrån.
"""
from . import matiec
from .deklarationsgrind import (Grind3Rapport, KONTROLLER_PLC, PlcAnmarkning,
                                bruk, granska)
from .opcuakonfig import konfiguration, nodid, variabel
from .openplc import Kompilering, OpenPlcFel, OpenPlcV4
from .paket import (Byggfel, Debugkarta, Lov, bygg_projekt, kompilera,
                    konfigurationstext, skriv_arkiv)
from .signalkarta import (Adress, FRAN_PLC, KartFel, Signal, Signalkarta,
                          TILL_PLC, karta_av_rader, las_adress)

__all__ = [
    "matiec",
    "Adress", "FRAN_PLC", "KartFel", "Signal", "Signalkarta", "TILL_PLC",
    "karta_av_rader", "las_adress",
    "Grind3Rapport", "KONTROLLER_PLC", "PlcAnmarkning", "bruk", "granska",
    "Byggfel", "Debugkarta", "Lov", "bygg_projekt", "kompilera",
    "konfigurationstext", "skriv_arkiv",
    "konfiguration", "nodid", "variabel",
    "Kompilering", "OpenPlcFel", "OpenPlcV4",
]
