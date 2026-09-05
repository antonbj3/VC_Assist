# -*- coding: utf-8 -*-
"""Felklasser for modellagret.

S9 i 96_ingen_skuld.md: inga tysta undantag. Varje avslag har en egen klass
och ett meddelande som namner VAD som var fel.

Lagret ar fail-closed genomgaende. Det ar med avsikt: varje fel har nedan har
en tyst tvilling som ser ut att fungera, och det ar tvillingen som ar farlig.

    Profilfel      en profil utan falt startar inte tjansten. Den tysta
                   tvillingen ar en profil dar ett saknat falt far ett
                   standardvarde - da kor budgeten pa nagon annans fonster.
    Budgetfel      det skyddade far inte plats. Den tysta tvillingen ar en
                   begaran som skickas anda och kapas av motparten.
    Kapfel         ett svar gick inte att kapa utan att skiva en struktur.
                   Den tysta tvillingen ar den kapade JSON som SER HEL UT.
    Turfel         turens spar bryter mot tillstandsmaskinen. Den tysta
                   tvillingen ar en tur som slutar i ett lage ingen namngav.
"""
from __future__ import annotations


class Modellagerfel(Exception):
    """Bas for allt som gar fel i modellagret."""


class Profilfel(Modellagerfel):
    """Modellprofilen haller inte sitt eget kontrakt (23_llm_granssnitt.md).

    Bar HELA problemlistan: den som skriver en adapter ska se allt i ett svep
    i stallet for att provas fram ett falt i taget.
    """

    def __init__(self, id_, problem):
        self.id = id_
        self.problem = list(problem)
        Modellagerfel.__init__(
            self, "modellprofilen %r har %d fel: %s"
            % (id_, len(self.problem), "; ".join(self.problem)))


class Budgetfel(Modellagerfel):
    """Budgeten haller inte ens efter att allt kapbart kapats.

    Fail-closed (S1): hellre inget anrop an ett anrop dar signalkartan eller
    ogats dom tystnat.
    """


class Kapfel(Modellagerfel):
    """Ett verktygssvar gick inte att kapa utan att skiva mitt i en struktur."""


class Turfel(Modellagerfel):
    """Turens spar ar inte en laglig vag genom tillstandsmaskinen."""
