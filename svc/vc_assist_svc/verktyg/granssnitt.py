# -*- coding: utf-8 -*-
"""Domanen composition: plug and play (45_verktyg.md).

Den viktigaste gruppen. MODELLEN ANGER RELATIONER, VC RAKNAR GEOMETRIN.
Darfor tar connect aldrig koordinater som argument - kopplingen AR
relationen (I8 i 90_invarianter.md). Att inget verktyg har ar det finns ett
geometriskt argument provas mekaniskt i tests/enhet/test_verktyg.py, sa
regeln inte kan glida tillbaka in vid nasta tillagg.

Ett simuleringsgranssnitt kanns igen pa sin yta (canConnect och Sections),
inte pa konstanten VC_ONETOONEINTERFACE. Skalet ar 36_versioner.md: formaga
provas, och formaga.py provar ATTRIBUT pa objekt. En konstant i en modul gar
inte att prova pa det sattet, och en konstant som saknas ger NameError i
stallet for ett begripligt svar.
"""
from __future__ import annotations

from .bas import (ARG_KOMPONENT, RET_ANTAL, RET_AVKORTAD, laggare, params,
                  returns, tak)
from .kodmall import bygg, lit

DOMAN = "composition"
_lagg = laggare(DOMAN)

ARG_GRANSSNITT = {
    "type": "string",
    "description": ("Granssnittets namn pa komponenten, exakt som det heter "
                    "i beteendelistan."),
}
ARG_ANNAN_KOMPONENT = {
    "type": "string",
    "description": "Den andra komponentens namn.",
}
ARG_ANNAT_GRANSSNITT = {
    "type": "string",
    "description": "Granssnittets namn pa den andra komponenten.",
}
RET_ANSLUTNA = {
    "type": "array",
    "description": "Namnen pa de komponenter granssnittet ar kopplat till.",
    "items": {"type": "string", "description": "Komponentnamn."},
}
_GRANSSNITTSPOST = {
    "type": "object",
    "description": "Ett simuleringsgranssnitt pa komponenten.",
    "properties": {
        "name": {"type": "string", "description": "Granssnittets namn."},
        "is_abstract": {"type": "boolean",
                        "description": "Om det tar emot fjarrkopplingar."},
        "is_connected": {"type": "boolean", "description": "Om det ar kopplat."},
        "sections": {"type": "integer", "description": "Antal sektioner."},
        "connected": RET_ANSLUTNA,
    },
}

# Ytorna varje granssnittsverktyg ror. Granssnittet ar ett BETEENDE, sa
# comp.Behaviours och comp.findBehaviour ar det formagegrinden kan prova;
# canConnect och Sections provas i mallen sjalv, per objekt.
_YTOR_EN_KOMPONENT = ("app.findComponent", "comp.Name", "comp.Behaviours")
_YTOR_TVA_KOMPONENTER = ("app.findComponent", "comp.Name", "comp.findBehaviour")


# ---- list_interfaces -----------------------------------------------------

def _kod_list_interfaces(argument):
    namn = lit(argument["component"])
    rader = [
        "k = _komp(%s)" % namn,
        "rader = []",
        "avkortad = False",
        "for b in k.Behaviours:",
        "    if not _ar_grans(b):",
        "        continue",
    ]
    rader += tak("rader")
    rader += [
        '    rader.append({"name": b.Name, "is_abstract": bool(b.IsAbstract),',
        '                  "is_connected": bool(b.IsConnected),',
        '                  "sections": len(b.Sections),',
        '                  "connected": _anslutna(b)})',
        '_svara({"component": %s, "interfaces": rader, "antal": len(rader),'
        ' "avkortad": avkortad})' % namn,
    ]
    return bygg(["_komp", "_ar_grans", "_anslutna", "_svara"], rader)


_lagg(
    "list_interfaces",
    "Listar komponentens simuleringsgranssnitt: vilka den kan kopplas med "
    "och vilka som redan ar kopplade.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten som lastes."},
             "interfaces": {"type": "array", "description": "Granssnitten.",
                            "items": _GRANSSNITTSPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "interfaces", "antal", "avkortad"]),
    _YTOR_EN_KOMPONENT,
    _kod_list_interfaces,
)


# ---- interface_info ------------------------------------------------------

def _kod_interface_info(argument):
    return bygg(["_komp", "_grans", "_anslutna", "_svara"], [
        "g = _grans(_komp(%s), %s)" % (lit(argument["component"]),
                                       lit(argument["interface"])),
        "sektioner = []",
        "for s in g.Sections:",
        '    sektioner.append({"name": s.Name, "index": s.Index})',
        'ut = {"component": %s, "interface": g.Name,' % lit(argument["component"]),
        '      "is_abstract": bool(g.IsAbstract),',
        '      "is_connected": bool(g.IsConnected),',
        '      "sections": sektioner, "connected": _anslutna(g)}',
        # Toleranserna finns pa vcSimInterface i den matta API-ytan men gar
        # inte att formageprova per yta, sa de fragas per objekt.
        # Saknas de utelamnas nycklarna hellre an att svaret ljuger om noll.
        'if hasattr(g, "DistanceTolerance"):',
        '    ut["distance_tolerance"] = g.DistanceTolerance',
        'if hasattr(g, "AngleTolerance"):',
        '    ut["angle_tolerance"] = g.AngleTolerance',
        "_svara(ut)",
    ])


_lagg(
    "interface_info",
    "Allt om ett granssnitt: sektioner, om det ar abstrakt, om det ar kopplat "
    "och vilka toleranser plug and play anvander.",
    "read",
    params({"component": ARG_KOMPONENT, "interface": ARG_GRANSSNITT},
           ["component", "interface"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "interface": {"type": "string", "description": "Granssnittet."},
             "is_abstract": {"type": "boolean", "description": "Om det tar emot fjarrkopplingar."},
             "is_connected": {"type": "boolean", "description": "Om det ar kopplat."},
             "sections": {"type": "array", "description": "Granssnittets sektioner.",
                          "items": {"type": "object", "description": "En sektion.",
                                    "properties": {
                                        "name": {"type": "string", "description": "Sektionens namn."},
                                        "index": {"type": "integer", "description": "Sektionens index."}}}},
             "connected": RET_ANSLUTNA,
             "distance_tolerance": {"type": "number",
                                    "description": "Avstand dar granssnittet snapper. Utelamnas om VC saknar egenskapen."},
             "angle_tolerance": {"type": "number",
                                 "description": "Vinkeltolerans. Utelamnas om VC saknar egenskapen."}},
            ["component", "interface", "is_abstract", "is_connected",
             "sections", "connected"]),
    _YTOR_TVA_KOMPONENTER + ("comp.Behaviours",),
    _kod_interface_info,
)


# ---- can_connect ---------------------------------------------------------

def _kod_can_connect(argument):
    return bygg(["_komp", "_grans", "_svara"], [
        "g1 = _grans(_komp(%s), %s)" % (lit(argument["component"]),
                                        lit(argument["interface"])),
        "g2 = _grans(_komp(%s), %s)" % (lit(argument["other_component"]),
                                        lit(argument["other_interface"])),
        '_svara({"can_connect": bool(g1.canConnect(g2)),',
        '        "component": %s, "interface": g1.Name,' % lit(argument["component"]),
        '        "other_component": %s, "other_interface": g2.Name})'
        % lit(argument["other_component"]),
    ])


_lagg(
    "can_connect",
    "Fragar VC om tva granssnitt gar att koppla. Prova alltid detta innan "
    "connect nar du inte ar saker.",
    "read",
    params({"component": ARG_KOMPONENT, "interface": ARG_GRANSSNITT,
            "other_component": ARG_ANNAN_KOMPONENT,
            "other_interface": ARG_ANNAT_GRANSSNITT},
           ["component", "interface", "other_component", "other_interface"]),
    returns({"can_connect": {"type": "boolean", "description": "VC:s eget svar."},
             "component": {"type": "string", "description": "Forsta komponenten."},
             "interface": {"type": "string", "description": "Forsta granssnittet."},
             "other_component": {"type": "string", "description": "Andra komponenten."},
             "other_interface": {"type": "string", "description": "Andra granssnittet."}},
            ["can_connect", "component", "interface", "other_component",
             "other_interface"]),
    _YTOR_TVA_KOMPONENTER,
    _kod_can_connect,
)


# ---- connect -------------------------------------------------------------

def _kod_connect(argument):
    return bygg(["_komp", "_grans", "_anslutna", "_svara"], [
        "g1 = _grans(_komp(%s), %s)" % (lit(argument["component"]),
                                        lit(argument["interface"])),
        "g2 = _grans(_komp(%s), %s)" % (lit(argument["other_component"]),
                                        lit(argument["other_interface"])),
        "if not g1.connect(g2):",
        # En nekad koppling far aldrig se ut som en lyckad (S1). VC svarar
        # False, mallen kastar, och bryggan lamnar E_EXEC med traceback.
        '    raise ValueError("VC nekade kopplingen mellan " + g1.Name'
        ' + " och " + g2.Name)',
        '_svara({"connected": True,',
        '        "component": %s, "interface": g1.Name,' % lit(argument["component"]),
        '        "other_component": %s, "other_interface": g2.Name,'
        % lit(argument["other_component"]),
        '        "connected_to": _anslutna(g1)})',
    ])


_lagg(
    "connect",
    "Kopplar tva granssnitt. VC raknar sjalv ut geometrin och flyttar "
    "komponenten pa plats - ange darfor ALDRIG koordinater, bara relationen.",
    "write",
    params({"component": ARG_KOMPONENT, "interface": ARG_GRANSSNITT,
            "other_component": ARG_ANNAN_KOMPONENT,
            "other_interface": ARG_ANNAT_GRANSSNITT},
           ["component", "interface", "other_component", "other_interface"]),
    returns({"connected": {"type": "boolean", "description": "Alltid true; en nekad koppling kastar."},
             "component": {"type": "string", "description": "Forsta komponenten."},
             "interface": {"type": "string", "description": "Forsta granssnittet."},
             "other_component": {"type": "string", "description": "Andra komponenten."},
             "other_interface": {"type": "string", "description": "Andra granssnittet."},
             "connected_to": RET_ANSLUTNA},
            ["connected", "component", "interface", "other_component",
             "other_interface", "connected_to"]),
    _YTOR_TVA_KOMPONENTER,
    _kod_connect,
)


# ---- disconnect ----------------------------------------------------------

def _kod_disconnect(argument):
    rader = ["g1 = _grans(_komp(%s), %s)" % (lit(argument["component"]),
                                             lit(argument["interface"]))]
    if "other_component" in argument:
        rader.append("g2 = _grans(_komp(%s), %s)"
                     % (lit(argument["other_component"]),
                        lit(argument["other_interface"])))
        rader.append("g1.disconnect(g2)")
    else:
        rader.append("g1.disconnect()")
    rader += [
        '_svara({"disconnected": True, "component": %s,'
        % lit(argument["component"]),
        '        "interface": g1.Name, "connected_to": _anslutna(g1)})',
    ]
    return bygg(["_komp", "_grans", "_anslutna", "_svara"], rader)


_lagg(
    "disconnect",
    "Kopplar isar. Utan other_component tas ALLA kopplingar i granssnittet "
    "bort; med den tas bara den kopplingen bort.",
    "write",
    params({"component": ARG_KOMPONENT, "interface": ARG_GRANSSNITT,
            "other_component": ARG_ANNAN_KOMPONENT,
            "other_interface": ARG_ANNAT_GRANSSNITT},
           ["component", "interface"],
           tillsammans=[("other_component", "other_interface")]),
    returns({"disconnected": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "interface": {"type": "string", "description": "Granssnittet."},
             "connected_to": dict(RET_ANSLUTNA,
                                  description="Vad som ar kvar kopplat efterat.")},
            ["disconnected", "component", "interface", "connected_to"]),
    _YTOR_TVA_KOMPONENTER,
    _kod_disconnect,
)


# ---- list_connections ----------------------------------------------------

def _kod_list_connections(argument):
    if "component" in argument:
        # En enkomponentslista ar samma slinga over en lista med ett element,
        # sa kroppen nedan ar identisk i bada fallen.
        kalla = "for k in [_komp(%s)]:" % lit(argument["component"])
    else:
        kalla = "for k in _app().Components:"
    rader = [
        "rader = []",
        "avkortad = False",
        kalla,
        "    if avkortad:",
        "        break",
        "    for b in k.Behaviours:",
        "        if not _ar_grans(b) or not b.IsConnected:",
        "            continue",
    ]
    rader += tak("rader", "        ")
    rader += [
        '        rader.append({"component": k.Name, "interface": b.Name,',
        '                      "connected": _anslutna(b)})',
        '_svara({"connections": rader, "antal": len(rader),'
        ' "avkortad": avkortad})',
    ]
    hjalpare = ["_ar_grans", "_anslutna", "_svara"]
    hjalpare.append("_komp" if "component" in argument else "_app")
    return bygg(hjalpare, rader)


_lagg(
    "list_connections",
    "Listar vilka granssnitt som ar kopplade, for en komponent eller for hela "
    "layouten. Det ar den snabbaste bilden av hur linan hanger ihop.",
    "read",
    params({"component": dict(ARG_KOMPONENT, description=(
        "Begransa till en komponent. Utelamnad listar hela layouten."))}),
    returns({"connections": {"type": "array", "description": "Kopplingarna.",
                             "items": {"type": "object",
                                       "description": "Ett kopplat granssnitt.",
                                       "properties": {
                                           "component": {"type": "string", "description": "Komponenten."},
                                           "interface": {"type": "string", "description": "Granssnittet."},
                                           "connected": RET_ANSLUTNA}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["connections", "antal", "avkortad"]),
    ("app.Components", "app.findComponent", "comp.Name", "comp.Behaviours"),
    _kod_list_connections,
)
