# -*- coding: utf-8 -*-
"""Felklasser for harnessen.

S9 i 96_ingen_skuld.md: inga tysta undantag. Varje avslag har en egen klass
och ett meddelande som namner VAD som var fel, sa att det kan ga tillbaka
till modellen eller till operatoren utan att nagon gissar.
"""
from __future__ import annotations


class Harnessfel(Exception):
    """Bas for allt som gar fel i harnessen."""


class Instruktionsfel(Harnessfel):
    """Instruktionskorpusen pa disk haller inte sitt eget format.

    Bar HELA problemlistan, inte bara det forsta felet: den som rattar en
    korpus ska se allt i ett svep. Fyrar vid laddning, aldrig i drift.
    """

    def __init__(self, katalog, problem):
        self.katalog = katalog
        self.problem = list(problem)
        Harnessfel.__init__(
            self, "instruktionskorpusen i %s har %d fel: %s"
            % (katalog, len(self.problem), "; ".join(self.problem)))


class Budgetfel(Harnessfel):
    """Systemprompten far inte plats ens efter kapning.

    Fail-closed: hellre ett fel an en prompt dar sakerhetsgransen tystnat.
    """


class Modellfel(Harnessfel):
    """Modelladaptern lamnade nagot som inte ar ett modellsvar."""


class Kanalfel(Harnessfel):
    """Verktygskanalen kunde inte ens forsoka utfora anropet."""
