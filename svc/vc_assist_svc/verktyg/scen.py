# -*- coding: utf-8 -*-
"""Domanen scene: lasa och andra scenen (45_verktyg.md).

Alla femton verktygen ar kodgenererande. Skalet star i 45_verktyg.md:
VC:s objektmodell ar metodbaserad, inte attributsatt som USD, sa allt som
ror scenen maste ga in i VC och fraga. Data-registret ar for index, katalog
och kunskap, som byggs i andra celler.

Varje mall ar skriven mot den MATTA API-ytan i
docs/referens/vc_api/vc_python_api.json (204 typer, 966 metoder), inte mot
minnet. Dar 45_verktyg.md och den matta ytan sager olika ting vinner den
matta: tabellen namner "app.delete()", som inte finns; det heter
app.deleteComponent(comp).
"""
from __future__ import annotations

from .bas import (ARG_KOMPONENT, ARG_NOD, RET_ANTAL, RET_AVKORTAD,
                  TIMEOUT_MS_FIL, XYZ, laggare, params, returns, tak)
from .kodmall import bygg, lit, tal

DOMAN = "scene"
_lagg = laggare(DOMAN)

# ---- aterkommande schemabitar som bara scenen anvander -------------------

_KOMPONENTPOST = {
    "type": "object",
    "description": "En komponent i layouten.",
    "properties": {
        "name": {"type": "string", "description": "Komponentens namn."},
        "uri": {"type": ["string", "null"],
                "description": "URI den laddades fran, null om den byggts i sessionen."},
        "category": {"type": ["string", "null"],
                     "description": "Katalogkategori."},
    },
}
_EGENSKAPSPOST = {
    "type": "object",
    "description": "En egenskap pa komponenten.",
    "properties": {
        "name": {"type": "string", "description": "Egenskapens namn."},
        "value": {"type": ["string", "number", "boolean", "integer", "null"],
                  "description": "Vardet. Varden VC inte kan ge som enkel typ kommer som text."},
        "type": {"type": ["string", "number", "integer", "null"],
                 "description": "VC:s typupprakning for egenskapen."},
    },
}


# ---- list_components -----------------------------------------------------

def _kod_list_components(argument):
    rader = ["rader = []", "avkortad = False", "for k in _app().Components:"]
    rader += tak("rader")
    if "name_contains" in argument:
        rader.append("    if %s not in k.Name:" % lit(argument["name_contains"]))
        rader.append("        continue")
    rader.append('    rader.append({"name": k.Name, "uri": k.Uri,'
                 ' "category": k.Category})')
    rader.append('_svara({"components": rader, "antal": len(rader),'
                 ' "avkortad": avkortad})')
    return bygg(["_app", "_svara"], rader)


_lagg(
    "list_components",
    "Listar komponenterna i layouten med namn, URI och kategori. "
    "Anvand name_contains for att smalna av i en stor layout.",
    "read",
    params({"name_contains": {
        "type": "string",
        "description": "Ta bara med komponenter vars namn innehaller den har texten."}}),
    returns({"components": {"type": "array", "description": "Komponenterna.",
                             "items": _KOMPONENTPOST},
              "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
             ["components", "antal", "avkortad"]),
    ("app.Components", "comp.Name", "comp.Uri", "comp.Category"),
    _kod_list_components,
)


# ---- find_component ------------------------------------------------------

def _kod_find_component(argument):
    namn = lit(argument["name"])
    return bygg(["_app", "_svara"], [
        "k = _app().findComponent(%s)" % namn,
        "if k is None:",
        '    _svara({"found": False, "name": %s})' % namn,
        "else:",
        '    _svara({"found": True, "name": k.Name, "uri": k.Uri,'
        ' "category": k.Category})',
    ])


_lagg(
    "find_component",
    "Soker en komponent pa exakt namn. Svarar found=false om den inte finns, "
    "vilket ar ett giltigt svar och inte ett fel.",
    "read",
    params({"name": ARG_KOMPONENT}, ["name"]),
    returns({"found": {"type": "boolean", "description": "Om komponenten fanns."},
              "name": {"type": "string", "description": "Namnet som soktes eller hittades."},
              "uri": {"type": ["string", "null"], "description": "URI den laddades fran."},
              "category": {"type": ["string", "null"], "description": "Katalogkategori."}},
             ["found", "name"]),
    ("app.findComponent", "comp.Name", "comp.Uri", "comp.Category"),
    _kod_find_component,
)


# ---- component_info ------------------------------------------------------

def _kod_component_info(argument):
    rader = ["k = _komp(%s)" % lit(argument["name"]),
             "egenskaper = []", "avkortad = False", "for p in k.Properties:"]
    rader += tak("egenskaper")
    rader += [
        '    egenskaper.append({"name": p.Name, "value": _enkelt(p.Value)})',
        "m = k.WorldPositionMatrix",
        "w = m.getWPR()",
        '_svara({"name": k.Name, "uri": k.Uri, "category": k.Category,',
        '        "properties": egenskaper, "avkortad": avkortad,',
        '        "world_position": [m.P.X, m.P.Y, m.P.Z],',
        '        "world_wpr": [w.X, w.Y, w.Z]})',
    ]
    return bygg(["_komp", "_enkelt", "_svara"], rader)


_lagg(
    "component_info",
    "Allt om en komponent: URI, kategori, egenskaper och lage i varlden. "
    "Kastar fel om komponenten inte finns.",
    "read",
    params({"name": ARG_KOMPONENT}, ["name"]),
    returns({"name": {"type": "string", "description": "Komponentens namn."},
              "uri": {"type": ["string", "null"], "description": "URI den laddades fran."},
              "category": {"type": ["string", "null"], "description": "Katalogkategori."},
              "properties": {"type": "array", "description": "Komponentens egenskaper.",
                             "items": _EGENSKAPSPOST},
              "avkortad": RET_AVKORTAD,
              "world_position": XYZ,
              "world_wpr": XYZ},
             ["name", "properties", "world_position", "world_wpr"]),
    ("app.findComponent", "comp.Name", "comp.Uri", "comp.Category",
     "comp.Properties", "comp.WorldPositionMatrix"),
    _kod_component_info,
)


# ---- load_component ------------------------------------------------------

def _kod_load_component(argument):
    uri = lit(argument["uri"])
    rader = [
        "k = _app().load(%s)" % uri,
        "if k is None:",
        '    raise ValueError("VC kunde inte ladda " + %s)' % uri,
    ]
    if "name" in argument:
        rader.append("k.Name = %s" % lit(argument["name"]))
    rader.append('_svara({"loaded": True, "name": k.Name, "uri": k.Uri})')
    return bygg(["_app", "_svara"], rader)


_lagg(
    "load_component",
    "Laddar en komponent fran en URI in i layouten. URI:n maste komma ur "
    "katalogindexet; en uppfunnen URI ar ett hart fel (I9).",
    "write",
    params({"uri": {"type": "string",
                     "description": "Komponentens URI, oftast file:/// foljt av full sokvag."},
             "name": {"type": "string",
                      "description": "Namn att ge komponenten efter inlasningen."}},
            ["uri"]),
    returns({"loaded": {"type": "boolean", "description": "Alltid true; misslyckad inlasning kastar."},
              "name": {"type": "string", "description": "Komponentens namn i layouten."},
              "uri": {"type": ["string", "null"], "description": "URI:n VC noterade."}},
             ["loaded", "name"]),
    ("app.load", "comp.Name", "comp.Uri"),
    _kod_load_component,
    timeout_ms=TIMEOUT_MS_FIL,
)


# ---- clone_component -----------------------------------------------------

def _kod_clone_component(argument):
    namn = lit(argument["name"])
    rader = [
        "k = _komp(%s)" % namn,
        # comp.clone() och inte app.cloneComponent(): den senare fungerar
        # bara nar simuleringen star stilla (vc_python_api.json).
        "ny = k.clone()",
        "if ny is None:",
        '    raise ValueError("kloningen gav ingen komponent")',
    ]
    # Namnet ar OBLIGATORISKT, och det ar ett medvetet val pa tva grunder.
    # Utan det numrerar VC klonen sjalv, och modellen maste da GISSA vad
    # kopian heter for att kunna rora den igen - precis den sortens uppfunna
    # namn I9 forbjuder. Dessutom ar ett namnbyte en synlig andring, sa
    # bryggans egen skrivgrind ser att koden skriver aven om den inte kanner
    # igen clone(). MATT: utan raden domer skrivgrind.granska() koden som
    # LASANDE, se rapporten om MUTERANDE_PREFIX i skrivgrind.py.
    rader.append("ny.Name = %s" % lit(argument["new_name"]))
    rader.append('_svara({"cloned": True, "name": ny.Name, "source": %s})' % namn)
    return bygg(["_komp", "_svara"], rader)


_lagg(
    "clone_component",
    "Klonar en komponent som redan finns i layouten.",
    "write",
    params({"name": ARG_KOMPONENT,
             "new_name": {"type": "string",
                          "description": ("Namn att ge klonen. Obligatoriskt: "
                                          "annars numrerar VC sjalv och du vet "
                                          "inte vad kopian heter.")}},
            ["name", "new_name"]),
    returns({"cloned": {"type": "boolean", "description": "Alltid true; en misslyckad kloning kastar."},
              "name": {"type": "string", "description": "Klonens namn."},
              "source": {"type": "string", "description": "Namnet pa originalet."}},
             ["cloned", "name", "source"]),
    ("app.findComponent", "comp.clone", "comp.Name"),
    _kod_clone_component,
    timeout_ms=TIMEOUT_MS_FIL,
)


# ---- delete_component ----------------------------------------------------

def _kod_delete_component(argument):
    namn = lit(argument["name"])
    return bygg(["_komp", "_app", "_svara"], [
        "k = _komp(%s)" % namn,
        # 45_verktyg.md skriver "app.delete()". Den metoden finns inte i den
        # matta API-ytan; det heter app.deleteComponent(comp).
        "_app().deleteComponent(k)",
        '_svara({"deleted": True, "name": %s})' % namn,
    ])


_lagg(
    "delete_component",
    "Tar bort en komponent ur layouten.",
    "write",
    params({"name": ARG_KOMPONENT}, ["name"]),
    returns({"deleted": {"type": "boolean", "description": "Alltid true; en komponent som inte finns kastar."},
              "name": {"type": "string", "description": "Namnet pa den borttagna komponenten."}},
             ["deleted", "name"]),
    ("app.findComponent", "app.deleteComponent"),
    _kod_delete_component,
)


# ---- get_transform -------------------------------------------------------

def _kod_get_transform(argument):
    ram = argument["frame"]
    matris = ("n.WorldPositionMatrix" if ram == "world" else "n.PositionMatrix")
    return bygg(["_komp", "_nod", "_svara"], [
        "n = _nod(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument.get("node", ""))),
        "m = %s" % matris,
        "w = m.getWPR()",
        '_svara({"frame": %s, "position": [m.P.X, m.P.Y, m.P.Z],'
        ' "wpr": [w.X, w.Y, w.Z]})' % lit(ram),
    ])


_lagg(
    "get_transform",
    "Lasar lage och orientering for en komponent eller en nod i den. "
    "frame=world ger laget i varlden, frame=parent laget i foraldern.",
    "read",
    params({"component": ARG_KOMPONENT, "node": ARG_NOD,
             "frame": {"type": "string", "enum": ["world", "parent"],
                       "default": "world",
                       "description": "Vilket koordinatsystem laget ska lasas i."}},
            ["component"]),
    returns({"frame": {"type": "string", "description": "Koordinatsystemet som lastes."},
              "position": XYZ,
              "wpr": XYZ},
             ["frame", "position", "wpr"]),
    ("app.findComponent", "comp.findNode", "comp.PositionMatrix",
     "comp.WorldPositionMatrix", "node.PositionMatrix", "node.WorldPositionMatrix"),
    _kod_get_transform,
)


# ---- set_transform -------------------------------------------------------

def _kod_set_transform(argument):
    rader = [
        "n = _nod(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument.get("node", ""))),
        # Matrisen lases ut, andras och skrivs tillbaka. Den halva som inte
        # angavs behaller darmed sitt varde.
        "m = n.PositionMatrix",
    ]
    importer = []
    if "wpr" in argument:
        w, p, r = argument["wpr"]
        rader.append("m.setWPR(%s, %s, %s)" % (tal(w), tal(p), tal(r)))
    if "position" in argument:
        x, y, z = argument["position"]
        importer.append("vcVector")
        rader.append("m.P = vcVector.new(%s, %s, %s)" % (tal(x), tal(y), tal(z)))
    rader += [
        "n.PositionMatrix = m",
        "u = n.PositionMatrix",
        "w = u.getWPR()",
        '_svara({"set": True, "position": [u.P.X, u.P.Y, u.P.Z],'
        ' "wpr": [w.X, w.Y, w.Z]})',
    ]
    return bygg(["_komp", "_nod", "_svara"], rader, importer)


_lagg(
    "set_transform",
    "Satter lage och orientering RELATIVT foraldern for en komponent eller "
    "nod. Varldsmatrisen gar inte att skriva i VC. Ange position, wpr eller "
    "bada; den som utelamnas lamnas orord. For att stalla komponenter mot "
    "varandra, anvand connect i stallet - VC raknar da geometrin sjalv (I8).",
    "write",
    params({"component": ARG_KOMPONENT, "node": ARG_NOD,
             "position": dict(XYZ, description="Nytt lage x, y, z i millimeter."),
             "wpr": dict(XYZ, description=(
                 "Ny orientering som roll, pitch, yaw i grader, samma ordning "
                 "som get_transform lamnar."))},
            ["component"], minst_en_av=[("position", "wpr")]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
              "position": XYZ, "wpr": XYZ},
             ["set", "position", "wpr"]),
    ("app.findComponent", "comp.findNode", "comp.PositionMatrix",
     "node.PositionMatrix"),
    _kod_set_transform,
)


# ---- get_bounds ----------------------------------------------------------

def _kod_get_bounds(argument):
    return bygg(["_komp", "_nod", "_svara"], [
        "n = _nod(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument.get("node", ""))),
        "c = n.BoundCenter",
        "d = n.BoundDiagonal",
        # BoundDiagonal gar fran mitten till HORNET, alltsa halva
        # utstrackningen (vc_python_api.json: "vector from center of node's
        # geometry bound box to its upper corner"). Darfor min = c - d, inte
        # c - d/2. Ett halvt varv fel har hade blivit en tyst faktor tva i
        # varje avstandsgrind.
        '_svara({"center": [c.X, c.Y, c.Z],',
        '        "half_extent": [d.X, d.Y, d.Z],',
        '        "min": [c.X - d.X, c.Y - d.Y, c.Z - d.Z],',
        '        "max": [c.X + d.X, c.Y + d.Y, c.Z + d.Z],',
        '        "size": [2.0 * d.X, 2.0 * d.Y, 2.0 * d.Z]})',
    ])


_lagg(
    "get_bounds",
    "Geometrins omslutande lada for en komponent eller nod, i nodens EGET "
    "koordinatsystem: mitt, halv utstrackning, min, max och storlek.",
    "read",
    params({"component": ARG_KOMPONENT, "node": ARG_NOD}, ["component"]),
    returns({"center": dict(XYZ, description="Fran nodens origo till ladans mitt."),
              "half_extent": dict(XYZ, description="Fran mitten till ladans horn."),
              "min": dict(XYZ, description="Ladans lagsta horn."),
              "max": dict(XYZ, description="Ladans hogsta horn."),
              "size": dict(XYZ, description="Ladans hela utstrackning.")},
             ["center", "half_extent", "min", "max", "size"]),
    ("app.findComponent", "comp.findNode", "comp.BoundCenter",
     "comp.BoundDiagonal", "node.BoundCenter", "node.BoundDiagonal"),
    _kod_get_bounds,
)


# ---- list_nodes ----------------------------------------------------------

def _kod_list_nodes(argument):
    namn = lit(argument["component"])
    rader = [
        "k = _komp(%s)" % namn,
        # Egen stack i stallet for rekursion: djupet ar okant och VC:s
        # Stackless-tolk delar stack med simuleringen.
        "stack = [(k, 0, %s)]" % lit(""),
        "rader = []",
        "avkortad = False",
        "while stack:",
        "    nod, djup, stig = stack.pop()",
    ]
    rader += tak("rader")
    rader += [
        '    rader.append({"name": nod.Name, "path": stig, "depth": djup,'
        ' "children": len(nod.Children)})',
        "    for b in nod.Children:",
        "        stack.append((b, djup + 1, stig + %s + b.Name))" % lit("/"),
        '_svara({"component": %s, "nodes": rader, "antal": len(rader),'
        ' "avkortad": avkortad})' % namn,
    ]
    return bygg(["_komp", "_svara"], rader)


_lagg(
    "list_nodes",
    "Listar nodtradet i en komponent med sokvag och djup. Roten har djup 0 "
    "och tom sokvag.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten som lastes."},
              "nodes": {"type": "array", "description": "Noderna.",
                        "items": {"type": "object", "description": "En nod.",
                                  "properties": {
                                      "name": {"type": "string", "description": "Nodens namn."},
                                      "path": {"type": "string", "description": "Sokvag fran roten."},
                                      "depth": {"type": "integer", "description": "Djup under roten."},
                                      "children": {"type": "integer", "description": "Antal barn."}}}},
              "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
             ["component", "nodes", "antal", "avkortad"]),
    ("app.findComponent", "comp.Name", "node.Children"),
    _kod_list_nodes,
)


# ---- find_node -----------------------------------------------------------

def _kod_find_node(argument):
    nod = lit(argument["node"])
    return bygg(["_komp", "_svara"], [
        "k = _komp(%s)" % lit(argument["component"]),
        "n = k.findNode(%s)" % nod,
        "if n is None:",
        '    _svara({"found": False, "node": %s})' % nod,
        "else:",
        "    m = n.WorldPositionMatrix",
        '    _svara({"found": True, "node": n.Name, "children": len(n.Children),',
        '            "world_position": [m.P.X, m.P.Y, m.P.Z]})',
    ])


_lagg(
    "find_node",
    "Soker en nod pa namn inne i en komponent. found=false ar ett giltigt svar.",
    "read",
    params({"component": ARG_KOMPONENT,
             "node": {"type": "string", "description": "Nodens namn."}},
            ["component", "node"]),
    returns({"found": {"type": "boolean", "description": "Om noden fanns."},
              "node": {"type": "string", "description": "Nodens namn."},
              "children": {"type": "integer", "description": "Antal barn."},
              "world_position": XYZ},
             ["found", "node"]),
    ("app.findComponent", "comp.findNode", "comp.Name", "node.Children",
     "node.WorldPositionMatrix"),
    _kod_find_node,
)


# ---- get_property --------------------------------------------------------

def _kod_get_property(argument):
    prop = lit(argument["property"])
    return bygg(["_komp", "_enkelt", "_svara"], [
        "k = _komp(%s)" % lit(argument["component"]),
        "p = k.getProperty(%s)" % prop,
        "if p is None:",
        '    _svara({"found": False, "property": %s})' % prop,
        "else:",
        '    _svara({"found": True, "property": p.Name, "value": _enkelt(p.Value),',
        '            "type": _enkelt(p.Type)})',
    ])


_lagg(
    "get_property",
    "Lasar en namngiven egenskap pa en komponent. found=false ar ett giltigt svar.",
    "read",
    params({"component": ARG_KOMPONENT,
             "property": {"type": "string", "description": "Egenskapens namn."}},
            ["component", "property"]),
    returns({"found": {"type": "boolean", "description": "Om egenskapen fanns."},
              "property": {"type": "string", "description": "Egenskapens namn."},
              "value": _EGENSKAPSPOST["properties"]["value"],
              "type": _EGENSKAPSPOST["properties"]["type"]},
             ["found", "property"]),
    ("app.findComponent", "comp.getProperty"),
    _kod_get_property,
)


# ---- set_property --------------------------------------------------------

def _kod_set_property(argument):
    prop = lit(argument["property"])
    return bygg(["_komp", "_enkelt", "_svara"], [
        "k = _komp(%s)" % lit(argument["component"]),
        "p = k.getProperty(%s)" % prop,
        "if p is None:",
        '    raise ValueError("komponenten har ingen egenskap som heter " + %s)' % prop,
        "p.Value = %s" % lit(argument["value"]),
        '_svara({"set": True, "property": p.Name, "value": _enkelt(p.Value)})',
    ])


_lagg(
    "set_property",
    "Satter en egenskap pa en komponent. Egenskapen maste redan finnas.",
    "write",
    params({"component": ARG_KOMPONENT,
             "property": {"type": "string", "description": "Egenskapens namn."},
             "value": {"type": ["string", "number", "integer", "boolean"],
                       "description": "Det nya vardet."}},
            ["component", "property", "value"]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
              "property": {"type": "string", "description": "Egenskapens namn."},
              "value": _EGENSKAPSPOST["properties"]["value"]},
             ["set", "property", "value"]),
    ("app.findComponent", "comp.getProperty"),
    _kod_set_property,
)


# ---- list_properties -----------------------------------------------------

def _kod_list_properties(argument):
    namn = lit(argument["component"])
    rader = ["k = _komp(%s)" % namn, "rader = []", "avkortad = False",
             "for p in k.Properties:"]
    rader += tak("rader")
    rader += [
        '    rader.append({"name": p.Name, "value": _enkelt(p.Value),'
        ' "type": _enkelt(p.Type)})',
        '_svara({"component": %s, "properties": rader, "antal": len(rader),'
        ' "avkortad": avkortad})' % namn,
    ]
    return bygg(["_komp", "_enkelt", "_svara"], rader)


_lagg(
    "list_properties",
    "Listar alla egenskaper pa en komponent med varde och typ.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten som lastes."},
              "properties": {"type": "array", "description": "Egenskaperna.",
                             "items": _EGENSKAPSPOST},
              "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
             ["component", "properties", "antal", "avkortad"]),
    ("app.findComponent", "comp.Properties"),
    _kod_list_properties,
)


# ---- save_layout ---------------------------------------------------------

def _kod_save_layout(argument):
    uri = lit(argument["uri"])
    return bygg(["_app", "_svara"], [
        "_app().save(%s)" % uri,
        '_svara({"saved": True, "uri": %s})' % uri,
    ])


_lagg(
    "save_layout",
    "Sparar hela layouten till en URI. MATT: app.save() stoppar simuleringen, "
    "sa bryggan gar ned efterat och VC maste startas om. Sparandet SKER, men "
    "inget utfall kommer tillbaka.",
    "write",
    params({"uri": {"type": "string",
                     "description": "Mal-URI, oftast file:/// foljt av full sokvag."}},
            ["uri"]),
    returns({"saved": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
              "uri": {"type": "string", "description": "URI:n som skrevs."}},
             ["saved", "uri"]),
    ("app.save",),
    _kod_save_layout,
    timeout_ms=TIMEOUT_MS_FIL,
)
