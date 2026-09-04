# -*- coding: utf-8 -*-
"""Delade schemabitar och trosklar for domanmodulerna.

Ligger for sig sa att scene och composition inte kopierar samma tal och
samma beskrivningar. En kopierad troskel ar tva trosklar sa fort nagon
andrar den ena.
"""
from __future__ import annotations

from .kodmall import MAX_POSTER
from .register import registrera
from .schema import Verktyg

# Ytorna ar matta pa VC 4.10 (36_versioner.md, tabellen "Vad som maste matas
# per version"). Ingen av dem ar provad pa 5.0, och formagegrinden ar det som
# avgor per installation - since ar markning, aldrig ett villkor.
SINCE = "4.10"

# Bryggans eget standardtak for en korning: pump.py laser
# args.get("timeout_ms", 5000), och 5000 ar vardet i exemplet i
# 31_brygga_protokoll.md. Verktygen ligger pa samma tal sa att tjansten inte
# infor en andra, tystare, grans.
TIMEOUT_MS = 5000

# Filoperationer (app.load, app.save, comp.clone) ar diskbundna. PRELIMINART:
# ingen matning finns av hur lange app.load tar i VC 4.10 under Wine. Talet ar
# valt for att inte falla en normal inlasning och ska ersattas av en matning i
# fas 5 (70_faser.md). Ett overskridande ar inte tyst: bryggan svarar
# E_TIMEOUT och markerar sig degraded.
TIMEOUT_MS_FIL = 60000

ARG_KOMPONENT = {
    "type": "string",
    "description": "Komponentens namn i layouten, exakt som det star i scenen.",
}
ARG_NOD = {
    "type": "string",
    "description": ("Nod inne i komponenten. Utelamnad betyder komponentens "
                    "egen rot."),
}
RET_AVKORTAD = {
    "type": "boolean",
    "description": ("True om listan klipptes vid taket pa %d poster. Da ar "
                    "svaret ofullstandigt." % MAX_POSTER),
}
RET_ANTAL = {"type": "integer", "description": "Antal poster i listan."}
XYZ = {
    "type": "array",
    "description": "Tre tal i millimeter respektive grader, i ordningen x, y, z.",
    "items": {"type": "number", "description": "Komponent i vektorn."},
    "minItems": 3,
    "maxItems": 3,
}


def params(egenskaper, obligatoriska=(), minst_en_av=None, tillsammans=None):
    p = {
        "type": "object",
        "properties": dict(egenskaper),
        "required": list(obligatoriska),
        # Utan detta blir ett uppfunnet argumentnamn tyst tillatet (I9).
        "additionalProperties": False,
    }
    if minst_en_av:
        p["x-minst-en-av"] = [list(g) for g in minst_en_av]
    if tillsammans:
        p["x-tillsammans"] = [list(g) for g in tillsammans]
    return p


def returns(egenskaper, obligatoriska):
    return {"type": "object", "properties": dict(egenskaper),
            "required": list(obligatoriska)}


def laggare(doman):
    """Ger domanens registreringsfunktion. Allt utom namnen ar gemensamt."""

    def _lagg(namn, beskrivning, effect, parameters, returns_, kraver,
              handlare, timeout_ms=TIMEOUT_MS):
        return registrera(
            Verktyg(namn=namn, beskrivning=beskrivning, mode="codegen",
                    effect=effect, parameters=parameters, returns=returns_,
                    since=SINCE, kraver=kraver, doman=doman,
                    timeout_ms=timeout_ms),
            handlare)

    return _lagg


def tak(behallare, indrag="    "):
    """Radarna som klipper en lista vid MAX_POSTER och sager att den klipptes."""
    return [
        "%sif len(%s) >= %d:   # kodmall.MAX_POSTER, ur bryggans 1 MiB-kropp"
        % (indrag, behallare, MAX_POSTER),
        "%s    avkortad = True" % indrag,
        "%s    break" % indrag,
    ]
