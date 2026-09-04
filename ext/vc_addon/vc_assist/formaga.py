# -*- coding: utf-8 -*-
"""Formagerapport: vilka API-ytor finns FAKTISKT i den har VC:n.

36_versioner.md: formaga provas, version antas aldrig. Rapporten skrivs vid
bryggans start och lases av tjansten, som slar av de verktyg vars yta saknas
i stallet for att lata dem falla med AttributeError langt senare.

Ytorna kommer ur kolumnen "Bygger pa" i 45_verktyg.md.
"""
from __future__ import absolute_import, division, print_function

import json
import sys
import time

# (yta, objekt, attribut). Objektet slas upp i den ordbok som skickas in.
YTOR = [
    # scenen
    ("app.Components", "app", "Components"),
    ("app.findComponent", "app", "findComponent"),
    ("app.createComponent", "app", "createComponent"),
    ("app.deleteComponent", "app", "deleteComponent"),
    ("app.cloneComponent", "app", "cloneComponent"),
    ("app.load", "app", "load"),
    ("app.save", "app", "save"),
    ("app.findCamera", "app", "findCamera"),
    ("app.rayCast", "app", "rayCast"),
    ("app.rayIntersect", "app", "rayIntersect"),
    ("app.getSelection", "app", "getSelection"),
    ("app.findLayer", "app", "findLayer"),
    ("app.createLayout", "app", "createLayout"),
    ("app.messageBox", "app", "messageBox"),
    ("app.getApplicationPath", "app", "getApplicationPath"),
    ("app.getPythonDllPath", "app", "getPythonDllPath"),
    # simuleringen
    ("app.startSimulation", "app", "startSimulation"),
    ("app.stopSimulation", "app", "stopSimulation"),
    ("app.resetSimulation", "app", "resetSimulation"),
    ("app.render", "app", "render"),
    ("sim.SimTime", "sim", "SimTime"),
    ("sim.IsRunning", "sim", "IsRunning"),
    ("sim.SimSpeed", "sim", "SimSpeed"),
    ("sim.run", "sim", "run"),
    ("sim.reset", "sim", "reset"),
    # komponenten
    ("comp.Name", "comp", "Name"),
    ("comp.Uri", "comp", "Uri"),
    ("comp.Category", "comp", "Category"),
    ("comp.Properties", "comp", "Properties"),
    ("comp.getProperty", "comp", "getProperty"),
    ("comp.createProperty", "comp", "createProperty"),
    ("comp.findNode", "comp", "findNode"),
    ("comp.findBehaviour", "comp", "findBehaviour"),
    ("comp.Behaviours", "comp", "Behaviours"),
    ("comp.PositionMatrix", "comp", "PositionMatrix"),
    ("comp.WorldPositionMatrix", "comp", "WorldPositionMatrix"),
    ("comp.BoundCenter", "comp", "BoundCenter"),
    ("comp.BoundDiagonal", "comp", "BoundDiagonal"),
    ("comp.clone", "comp", "clone"),
    ("comp.delete", "comp", "delete"),
    # noden
    ("node.Children", "node", "Children"),
    ("node.PositionMatrix", "node", "PositionMatrix"),
    ("node.WorldPositionMatrix", "node", "WorldPositionMatrix"),
    ("node.BoundCenter", "node", "BoundCenter"),
    ("node.BoundDiagonal", "node", "BoundDiagonal"),
]


def _prova(objekt, attribut):
    """Returnerar (finns, typ). Ett attribut som KASTAR raknas som saknat."""
    try:
        if not hasattr(objekt, attribut):
            return False, None
        v = getattr(objekt, attribut)
        return True, type(v).__name__
    except Exception as e:
        return False, "kastade %s" % type(e).__name__


def formaga(objekt, extra=None):
    """objekt: {'app': ..., 'sim': ..., 'comp': ..., 'node': ...}"""
    ytor = {}
    for yta, namn, attribut in YTOR:
        o = objekt.get(namn)
        if o is None:
            ytor[yta] = {"finns": None, "varfor": "inget %s att prova mot" % namn}
            continue
        finns, typ = _prova(o, attribut)
        ytor[yta] = {"finns": finns, "typ": typ}

    finns = [y for y, d in ytor.items() if d["finns"] is True]
    saknas = [y for y, d in ytor.items() if d["finns"] is False]
    oprovade = [y for y, d in ytor.items() if d["finns"] is None]

    rapport = {
        "skriven": time.time(),
        "python": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "exe": sys.executable,
        "ytor": ytor,
        "summering": {
            "provade": len(YTOR),
            "finns": len(finns),
            "saknas": len(saknas),
            "oprovade": len(oprovade),
        },
        "saknade_ytor": sorted(saknas),
        "oprovade_ytor": sorted(oprovade),
    }
    if extra:
        rapport.update(extra)
    return rapport


def skriv(sokvag, objekt, extra=None):
    r = formaga(objekt, extra)
    f = open(sokvag, "w")
    try:
        f.write(json.dumps(r, indent=2, sort_keys=True))
    finally:
        f.close()
    return r
