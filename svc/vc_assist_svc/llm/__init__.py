# -*- coding: utf-8 -*-
"""Modellagret: kontraktet mot en sprakmodell, turen och kontextbudgeten.

Tre specdokument bor har, och de ager var sin sak:

    23_llm_granssnitt.md   kontraktet: profilen, systemprompten, urvalet,
                           honesty-rewrite, verify-contract, taken
    24_samtalsloopen.md    turen: lagen, overgangarna, vad som avslutar
    25_kontextbudget.md    budgeten: vad som far plats och vad som gar bort

Modulerna:

    matt        storleken i byte, tecken och tokens - och de tva antaganden
                som gor tokentalet till ett antagande
    profil      modellprofilen, sluten yta, saknat falt = kastar
    urval       vilka verktyg som exponeras nar de inte far plats alla
    kapning     ett verktygssvar som inte far plats, kapat PA POSTER
    ogontrim    ogats rapport, ordagrant, minus hela rader utan fynd
    scenvy      scenen, hel under taket och sammanfattad over det
    budget      posterna, taken, trimordningen och TRIMMAD-handelserna
    delar       limmet: turens innehall som poster i budgeten
    tur         tillstandsmaskinen, laggen mot den byggda loopens protokoll

INGEN LEVERANTOR NAMNS HAR. L1 i 23_llm_granssnitt.md, och det provas
mekaniskt i tests/enhet/test_modellturen.py.
"""
from __future__ import annotations

from . import budget, delar, kapning, matt, ogontrim, profil, scenvy, tur, urval  # noqa: F401
from .fel import Budgetfel, Kapfel, Modellagerfel, Profilfel, Turfel  # noqa: F401
