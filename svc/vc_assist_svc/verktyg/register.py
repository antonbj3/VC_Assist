# -*- coding: utf-8 -*-
"""De tva registren och den enda vagen in i dem.

45_verktyg.md:

    DATA_HANDLERS      handlaren returnerar ett fardigt resultat, som anropas
                       direkt i tjansten
    CODE_GEN_HANDLERS  handlaren returnerar en STRANG med Python 2.7-kod som
                       skickas till bryggan

Handlarnas signatur ar (argument) -> resultat respektive (argument) -> str.
Det ar inte en konvention utan en KONTROLL: registrera() avvisar varje
handlare som tar nagot mer an argumenten. En handlare far darfor aldrig se
bryggklienten, och kan alltsa inte valja exekveringslage sjalv (I12).
Routingen ligger i utforare.py och lases av verktygets deklarerade effect.

Registren fylls av domanmodulerna vid import av paketet (__init__.py).
"""
from __future__ import annotations

import inspect

from .fel import Schemafel

REGISTER = {}
DATA_HANDLERS = {}
CODE_GEN_HANDLERS = {}

# Handlarens enda parameter. Ett fast namn gor kontrollen mekanisk i stallet
# for en regel i text.
PARAMETERNAMN = "argument"


def _granska_handlare(namn, handlare):
    if not callable(handlare):
        raise Schemafel("%s: handlaren ar inte anropbar" % namn)
    sign = inspect.signature(handlare)
    parametrar = list(sign.parameters.values())
    fel = []
    if len(parametrar) != 1:
        fel.append("handlaren tar %d parametrar, ska ta exakt en (%s)"
                   % (len(parametrar), PARAMETERNAMN))
    for p in parametrar:
        if p.name != PARAMETERNAMN:
            fel.append("parametern heter %r, ska heta %r"
                       % (p.name, PARAMETERNAMN))
        if p.kind not in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            fel.append("parametern %s ar av fel slag (%s); *args och **kwargs "
                       "skulle slappa in bryggklienten bakvagen" % (p.name, p.kind))
    if fel:
        raise Schemafel("%s: %s" % (namn, "; ".join(fel)))


def registrera(verktyg, handlare):
    """Lagger verktyget i det register dess mode pekar ut."""
    if verktyg.namn in REGISTER:
        raise Schemafel("%s ar redan registrerat (av doman %s)"
                        % (verktyg.namn, REGISTER[verktyg.namn].doman))
    _granska_handlare(verktyg.namn, handlare)
    REGISTER[verktyg.namn] = verktyg
    if verktyg.mode == "codegen":
        CODE_GEN_HANDLERS[verktyg.namn] = handlare
    else:
        DATA_HANDLERS[verktyg.namn] = handlare
    return verktyg


def domaner():
    """Vilka domaner som ar byggda, och hur manga verktyg var."""
    ut = {}
    for v in REGISTER.values():
        ut.setdefault(v.doman, []).append(v.namn)
    return {d: tuple(sorted(n)) for d, n in ut.items()}
