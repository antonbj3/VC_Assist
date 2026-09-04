# -*- coding: utf-8 -*-
"""Felklasser for planeringslagret.

S9 i docs/spec/96_ingen_skuld.md: inga tysta undantag. Varje avslag har en
egen klass och ett meddelande som namner VAD som var fel och VILKET steg det
gallde, sa att den som laser felet slipper gissa.

Ett fel som upptacks vid PLANERINGEN kastar har. Ett fel som upptacks vid
KORNINGEN kastar aldrig - det blir en post i protokollet med skal, for en
korning som slutar med ett undantag har inget protokoll att lasa (S10).
"""
from __future__ import annotations


class Planfel(Exception):
    """Bas for allt som gar fel i planeringslagret."""


class Specfel(Planfel):
    """Specen haller inte sin egen form.

    Bar HELA problemlistan, av samma skal som verktygslagrets Argumentfel:
    den som skrev specen ska kunna ratta allt i ett svep.
    """

    def __init__(self, vad, problem):
        self.vad = vad
        self.problem = list(problem)
        Exception.__init__(
            self, "%s: %d fel: %s" % (vad, len(self.problem),
                                      "; ".join(self.problem)))


class Graffel(Planfel):
    """Uppgiftsgrafen gar inte att ordna.

    Bar cyklerna i .cykler sa att anroparen kan skriva ut vilka steg som
    ingar. Kravet i uppgiften: en cykel ska UPPTACKAS och rapporteras, aldrig
    bli en oandlig loop.
    """

    def __init__(self, text, cykler=()):
        self.cykler = [list(c) for c in cykler]
        Exception.__init__(self, text)


class Layoutfel(Planfel):
    """Layoutmotorn svarade nagot som inte haller portens kontrakt.

    Kastar hellre an returnerar en halv placering: en placering vi inte kan
    lita pa ar inte en placering (I3, fail-closed).
    """


class Verifieringsfel(Planfel):
    """Verifieringskravet gar inte att uttrycka i ogats grammatik.

    Ett krav som ogat aldrig kan skriva ar inget krav, det ar en onskan.
    """


class Korningsfel(Planfel):
    """Koraren ombads gora nagot omojligt, till exempel aterupptas ur ett
    protokoll som horde till en annan plan."""
