# -*- coding: utf-8 -*-
"""Fritextvagen till en scen som REDAN FINNS.

plan/ bygger nagot nytt ur en mening. Det har paketet arbetar pa nagot som
star dar: det laser scenen, det svarar pa varfor den gor som den gor, och det
andrar den bara nar andringen gar att belagga.

    sparr.py    LASSPARREN, HARKOMSTGRINDEN och ENTYDIGHETEN. Byggd forst.
    fragor.py   vad vi inte vet, och VEM som kan svara: en matning eller
                operatoren. En vag som fragar honom om nagot den kunde ha
                matt ar lika trasig som en som gissar.
    avsikt.py   tolken: vad meningen vill, och budgeten det kostar.
    diagnos.py  intention 1, ur ogats egna rader.

Tre intentioner, och de ar inte samma sak:

    1 DIAGNOS      "varfor svalter station 3?" Ingen andring. Byggd.
    2 ANDRING      "byt det dar gripdonet." Grindarna byggda, vagen ut till
                   verktygen gar genom harnessen som vanligt.
    3 OPTIMERING   "snabba den har linan." Andra, mata om, jamfora. INTE
                   byggd, och avvisas med det skalet i stallet for att bli en
                   halv andring.
"""
from __future__ import annotations

from . import avsikt, diagnos, fragor, sparr

__all__ = ["avsikt", "diagnos", "fragor", "sparr"]
