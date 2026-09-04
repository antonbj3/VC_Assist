# -*- coding: utf-8 -*-
"""Installationen av VC Assist-tillagget. Python 3, endast standardbiblioteket.

Tre moduler:

* ``upptackt``   soker upp VC:s tillaggsmapp. Den ANTAR aldrig en sokvag,
                 den letar och rapporterar vad den hittade.
* ``paket``      kopierar tillagget dit, verifierar det pa plats, och tar bort
                 exakt det den lade dit.
* ``installera`` kommandoraden.

Koden ar avsiktligt ren ASCII, inklusive utskrifterna. Skalet ar plattformen:
en Windows-konsol med cp437 eller cp850 kastar UnicodeEncodeError pa a-ring och
o-umlaut, och ett installationsskript som kraschar pa sin egen utskrift ar
varre an ett som ser torftigt ut. Dokumentationen har full svenska.

Kor: ``python3 install/installera.py sok``
"""
from __future__ import annotations

__all__ = ["upptackt", "paket", "installera"]
