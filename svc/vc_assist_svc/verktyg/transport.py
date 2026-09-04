# -*- coding: utf-8 -*-
"""Domanen transport: transportorer, floden och processer (45_verktyg.md).

Alla verktyg ar kodgenererande. Samma skal som scenen: VC:s objektmodell ar
metodbaserad, sa allt som ror en korande layout maste ga in i VC och fraga.

VAD SOM AR MATT, OCH VAD SOM DARFOR INTE FINNS HAR
--------------------------------------------------
Katalogen i 45_verktyg.md namner en processgrupp. Den har modulen bygger den
och den transport- och flodesyta som lag underforstadd, men BARA pa namn som
star i den matta API-ytan under docs/referens/vc_api/.

MATT 2026-09-04 mot api_index (212 typer): dessa TYPER finns INTE i VC 4.10:s
egen autokomplettering och gar alltsa inte att skriva kod mot -

    vcConveyorTransportController   vcPath          vcOneWayPath
    vcTwoWayPath                    vcPositionPath  vcComponentPathSensor
    vcContainerFiller               vcCapacityController
    vcVehicle (heter vcSimVehicle)  vcProcessPoint (bara vcProcessPointSensor)

Deras KONSTANTER finns (VC_ONEWAYPATH, VC_CONVEYORTRANSPORTCONTROLLER,
VC_COMPONENTPATHSENSOR, VC_CONTAINERFILLER, VC_CAPACITYCONTROLLER,
VC_BUFFERMODE_FIFO/LIFO ...), men en konstant ar inget API: den sager vilket
SLAG ett beteende har, inte vilka namn objektet bar. Foljden ar konkret:

  * En transportors HASTIGHET, LANGD, RIKTNING och ACKUMULERING har inget
    deklarerat API-namn i den matta ytan. De ligger som PARAMETRAR pa
    komponenten eller pa banbeteendet, och deras namn varierar per komponent.
    Darfor finns inga get_conveyor_speed/set_conveyor_direction har. I stallet
    finns list_transport_parameters (som VISAR vad som finns) och
    get/set_transport_parameter (som laser och satter det modellen sag).
    Samma regel som katalogen: modellen valjer bara ur en trafflista, den
    hittar aldrig pa ett namn (I9).
  * KAPACITET har daremot ett deklarerat namn - vcContainer.Capacity - och far
    darfor egna verktyg.

BETEENDETS SLAG KANNS IGEN PA SIN YTA, INTE PA EN KONSTANT
----------------------------------------------------------
Samma regel som granssnitt.py: formaga.py provar ATTRIBUT pa objekt, aldrig
namn i en modul. En konstant som saknas ger NameError i stallet for ett
begripligt svar. Tabellen SLAG nedan ar darfor bade schemats enum och
mallarnas kod - de kan inte drifta isar, eftersom mallens _slag() GENERERAS ur
tabellen. Varje rads urskiljningsformaga ar matt mot api_index och provas om i
tests/enhet/test_verktyg_transport.py.

VARFOR MALLARNA ANROPAR getApplication() INLINE
-----------------------------------------------
MATT 2026-09-04: api_index.Validator harleder inte returtypen ur en funktion
som koden sjalv definierar. Gar komponenten genom kodmall._komp() blir k av
typen "okand", och VARJE lasning efterat ar odomd - korsprovet mot API-indexet
blir da en grind som aldrig kan falla. Med findComponent inline typas k till
vcComponent och resten av mallen domes. Samma mall gick fran 1 till 10
kontrollerade namn nar anropet flyttades in. Darfor har, och bara har, ligger
komponentuppslaget i mallen i stallet for i en delad hjalpare.

OPROVAT MOT VC: det finns noll komponenter i den lokala katalogen (mat i
katalog.py: fem komponentfiler, noll layouter), sa ingen av mallarna har kort
mot en verklig transportor. De ar provade mot bada grindarna som gar att kora
utan VC - bryggans skrivgrind och API-indexet - och mot schemat.
"""
from __future__ import annotations

from .bas import (ARG_KOMPONENT, RET_ANTAL, RET_AVKORTAD, laggare, params,
                  returns, tak)
from .kodmall import bygg, lit, tal

DOMAN = "transport"
_lagg = laggare(DOMAN)


# ---- vilket slag ett beteende ar ----------------------------------------

# (slag, ytattribut). Ett beteende ar av slaget om det bar BADA attributen.
# Urskiljningsformagan ar MATT mot api_index 2026-09-04 och provas om av
# test_varje_slag_traffar_de_typer_det_mattes_mot:
#
#   container          vcContainer, vcTransport, vcComponentCreator,
#                      vcRoutingRule, vcInterpolatingTransportController,
#                      vcMotionPath, vcPatternContainer   (familj, avsiktligt)
#   flow               de sju ovan plus vcFlow, vcComponentFlowProxy,
#                      vcProductCreator                   (familj, avsiktligt)
#   statistics         vcStatistics                       (exakt en)
#   sensor             vcProcessPointSensor               (exakt en)
#   routing_rule       vcRoutingRule                      (exakt en)
#   product_creator    vcProductCreator                   (exakt en)
#   component_creator  vcComponentCreator                 (exakt en)
#   process_controller vcProcessController                (exakt en)
#   process_executor   vcProcessExecutor                  (exakt en)
#   transport_node     vcTransportNode                    (exakt en)
#
# De tva forsta ar FAMILJER och ska vara det: en planerare vill se allt som
# haller komponenter respektive allt som har flodesportar. De atta ovriga
# pekar ut precis en typ var, sa ett verktyg som kraver ett av dem kan lita pa
# vilken yta det far.
SLAG = (
    ("container", ("Capacity", "Components")),
    ("flow", ("Connectors", "CapacityAvailable")),
    ("statistics", ("ComponentsArrived", "ComponentsDeparted")),
    ("sensor", ("BoolSignal", "TriggerAt")),
    ("routing_rule", ("processRoute", "setTarget")),
    ("product_creator", ("SingleFeed", "FeedMode")),
    ("component_creator", ("TemplateComponent", "Interval")),
    ("process_controller", ("ProcessManager", "TransportSystem")),
    ("process_executor", ("Processes", "ProcessController")),
    ("transport_node", ("TransportLinks", "TransportSystem")),
)
SLAGNAMN = tuple(namn for namn, _ytor in SLAG)


# ---- lokala kodhjalpare --------------------------------------------------
#
# De ligger har och inte i kodmall.py av tva skal: de anvands bara av den har
# domanen, och kodmall.py ligger utanfor cellens skrivstaket. Ingen av dem tar
# emot eller lamnar ifran sig ett VC-objekt - det ar ett KRAV, inte en slump:
# en hjalpare som lamnar ett VC-objekt gor resten av mallen odomd for
# API-indexet (se modulens huvud).

def _rader_slag():
    """Genererar mallens _slag() ur SLAG, sa kod och enum inte kan drifta."""
    rader = [
        "def _slag(b):",
        "    # Beteendets slag kanns igen pa dess YTA, aldrig pa en",
        "    # VC_-konstant: formaga.py provar attribut pa objekt, och en",
        "    # konstant som saknas ger NameError i stallet for ett svar.",
        "    # Genererad ur transport.SLAG - andra tabellen, inte den har koden.",
        # Listan heter INTE slagen: mallarna binder slagen till _slag(b), och
        # bryggans skrivgrind stryker ett namn ur sina egna behallare sa fort
        # det nagon gang binds till nagot annat an en behallarliteral. MATT
        # 2026-09-04: med namnet slagen domdes list_transport_behaviours som
        # SKRIVANDE pa sina egna append-anrop.
        "    slaglista = []",
    ]
    for namn, ytor in SLAG:
        villkor = " and ".join('hasattr(b, "%s")' % y for y in ytor)
        rader.append("    if %s:" % villkor)
        rader.append('        slaglista.append("%s")' % namn)
    rader.append("    return slaglista")
    return rader


_HJALPARE = {
    "_slag": _rader_slag(),
    "_kvot": [
        "def _kvot(antal, tak_):",
        "    # Fyllnadsgrad. Kapacitet 0 eller mindre betyder ingen grans i",
        "    # VC, och en kvot mot noll ar inget tal - da lamnas None i",
        "    # stallet for en nolla som ser ut som en matt tomhet (I3).",
        "    if tak_ is None or tak_ <= 0:",
        "        return None",
        "    return float(antal) / float(tak_)",
    ],
}
# Fast ordning sa att tva mallar med samma hjalpare blir byte for byte lika.
_ORDNING = ("_slag", "_kvot")


def _lokala(namn):
    return [rad for n in _ORDNING if n in namn for rad in _HJALPARE[n]]


def _hamta_komponent(namn, variabel="k"):
    """Raderna som hamtar komponenten och ger den en KAND typ."""
    return [
        "%s = getApplication().findComponent(%s)" % (variabel, lit(namn)),
        "if %s is None:" % variabel,
        '    raise ValueError("ingen komponent heter " + %s)' % lit(namn),
    ]


def _hamta_beteende(namn):
    """Raderna som hamtar beteendet ur komponenten k, ocksa de inline."""
    return [
        "b = k.findBehaviour(%s)" % lit(namn),
        "if b is None:",
        '    raise ValueError("komponenten har inget beteende som heter " + %s)'
        % lit(namn),
    ]


def _krav_slag(slag, variabel="b"):
    """Raderna som avvisar ett beteende av fel slag, med slaget i felet."""
    return [
        'if "%s" not in _slag(%s):' % (slag, variabel),
        '    raise ValueError(%s + " ar inget beteende av slaget %s; dess'
        ' slag ar " + (", ".join(_slag(%s)) or "inget kant"))'
        % (variabel + ".Name", slag, variabel),
    ]


def _komponentkalla(argument, listnamn="komponenter"):
    """Raderna som binder listan av komponenter mallen ska ga igenom."""
    if "component" in argument:
        rader = _hamta_komponent(argument["component"], "k0")
        rader.append("%s = [k0]" % listnamn)
        return rader
    return ["%s = getApplication().Components" % listnamn]


# ---- aterkommande schemabitar --------------------------------------------

ARG_BETEENDE = {
    "type": "string",
    "description": ("Beteendets namn pa komponenten, exakt som det star i "
                    "beteendelistan. Anvand list_transport_behaviours for att "
                    "se vilka som finns."),
}
ARG_KOMPONENT_VALFRI = dict(ARG_KOMPONENT, description=(
    "Begransa till en komponent. Utelamnad gar hela layouten igenom."))
ARG_PARAMETER = {
    "type": "string",
    "description": ("Parameterns namn, exakt som list_transport_parameters "
                    "lamnade det. Ett uppfunnet namn ger found=false, aldrig "
                    "en gissning."),
}
RET_SLAG = {
    "type": "array",
    "description": ("Vilka slag beteendet ar av, avgjort pa dess yta. Ett "
                    "beteende kan vara flera: en dirigeringsregel ar bade "
                    "container, flow och routing_rule."),
    "items": {"type": "string", "description": "Ett slag ur listan i schemat."},
    # Langden foljer tabellen SLAG, inte layouten. Det ar skalet till att
    # listan inte behover nagot tak och nagon avkortad-flagga, och maxItems
    # sager det i schemat i stallet for i en kommentar.
    "maxItems": len(SLAG),
}
RET_VARDE = {
    "type": ["string", "number", "integer", "boolean", "null"],
    "description": ("Vardet. Det VC inte kan ge som enkel typ kommer som "
                    "text, aldrig som ett tal det inte ar."),
}
_PARAMETERPOST = {
    "type": "object",
    "description": "En parameter pa komponenten eller pa beteendet.",
    "properties": {
        "name": {"type": "string", "description": "Parameterns namn."},
        "value": RET_VARDE,
        "type": {"type": ["string", "number", "integer", "null"],
                 "description": "VC:s typupprakning for parametern."},
        "writable_when_simulating": {
            "type": "boolean",
            "description": "Om den gar att andra medan simuleringen kor."},
        "writable_when_connected": {
            "type": "boolean",
            "description": "Om den gar att andra medan komponenten ar kopplad."},
    },
}
_STATIONSPOST = {
    "type": "object",
    "description": ("En stations genomstromning. Falten in, out, avg_s, min_s "
                    "och max_s ar valda for att ga rakt in i ogats "
                    "STATION-rad (oga_kontrakt.py) utan omtolkning."),
    "properties": {
        "station": {"type": "string", "description": "Komponentens namn."},
        "behaviour": {"type": "string",
                      "description": "Statistikbeteendet vardena kom ur."},
        "in": {"type": "integer",
               "description": "ComponentsArrived: antal som kommit in."},
        "out": {"type": "integer",
                "description": "ComponentsDeparted: antal som gatt ut."},
        "avg_s": {"type": "number",
                  "description": "ComponentsAverageTime: medeltid i sekunder."},
        "min_s": {"type": "number",
                  "description": "ComponentMinTime: kortaste tiden i sekunder."},
        "max_s": {"type": "number",
                  "description": "ComponentMaxTime: langsta tiden i sekunder."},
        "current": {"type": "integer",
                    "description": "ComponentsCurrent: antal inne just nu."},
        "min_count": {"type": "integer",
                      "description": "ComponentMinCount: minsta samtidiga antal."},
        "max_count": {"type": "integer",
                      "description": "ComponentMaxCount: storsta samtidiga antal."},
    },
}

# Formageytor som ateranvands. En komponent nas alltid genom findComponent
# eller Components; beteenden genom Behaviours eller findBehaviour.
_Y_KOMP = ("app.findComponent", "comp.Name")
_Y_BET = _Y_KOMP + ("comp.findBehaviour",)
_Y_BETLISTA = _Y_KOMP + ("comp.Behaviours",)


# ---- list_transport_behaviours -------------------------------------------

def _kod_list_transport_behaviours(argument):
    rader = _komponentkalla(argument)
    rader += [
        "rader = []",
        "avkortad = False",
        "for k in komponenter:",
        "    if avkortad:",
        "        break",
        "    for b in k.Behaviours:",
    ]
    rader += tak("rader", "        ")
    rader += [
        "        slagen = _slag(b)",
        "        if not slagen:",
        "            continue",
    ]
    if "kind" in argument:
        # Plain strangliteral och inte lit(): slaget nar aldrig VC:s API, det
        # jamfors mot _slag():s egna literaler. Vardet kan bara vara ett av
        # SLAGNAMN - schemats enum provas av validera_argument INNAN nagon kod
        # genereras, och det provas i sin tur av
        # test_ett_slag_utanfor_enumen_avvisas_innan_kod_genereras.
        rader += [
            '        if "%s" not in slagen:' % argument["kind"],
            "            continue",
        ]
    rader += [
        '        rader.append({"component": k.Name, "behaviour": b.Name,',
        '                      "kinds": slagen, "enabled": bool(b.Enabled)})',
        '_svara({"behaviours": rader, "antal": len(rader),'
        ' "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_transport_behaviours",
    "Listar de transport-, flodes- och processbeteenden som finns, i en "
    "komponent eller i hela layouten. Slaget avgors av vilken yta beteendet "
    "bar, inte av vad det heter. Detta ar ingangen till hela domanen: allt "
    "annat vill ha ett beteendenamn harifran.",
    "read",
    params({"component": ARG_KOMPONENT_VALFRI,
            "kind": {"type": "string", "enum": list(SLAGNAMN),
                     "description": ("Ta bara med beteenden av det har slaget. "
                                     "Utelamnad tar med alla.")}}),
    returns({"behaviours": {
                 "type": "array", "description": "Beteendena.",
                 "items": {"type": "object", "description": "Ett beteende.",
                           "properties": {
                               "component": {"type": "string",
                                             "description": "Komponenten det sitter pa."},
                               "behaviour": {"type": "string",
                                             "description": "Beteendets namn."},
                               "kinds": RET_SLAG,
                               "enabled": {"type": "boolean",
                                           "description": "Om beteendet ar pa."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["behaviours", "antal", "avkortad"]),
    ("app.Components", "app.findComponent", "comp.Name", "comp.Behaviours"),
    _kod_list_transport_behaviours,
)


# ---- transport_behaviour_info --------------------------------------------

def _kod_transport_behaviour_info(argument):
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += [
        'ut = {"component": k.Name, "behaviour": b.Name, "kinds": _slag(b),',
        '      "enabled": bool(b.Enabled), "type": _enkelt(b.Type),',
        '      "property_count": len(b.Properties)}',
        # Toleransen for vad som finns per objekt ar densamma som i
        # granssnitt.py: saknas ytan utelamnas nyckeln hellre an att svaret
        # ljuger om en nolla.
        'if hasattr(b, "Capacity"):',
        '    ut["capacity"] = b.Capacity',
        '    ut["component_count"] = b.ComponentCount',
        '    ut["fill_ratio"] = _kvot(b.ComponentCount, b.Capacity)',
        'if hasattr(b, "CapacityAvailable"):',
        '    ut["capacity_available"] = bool(b.CapacityAvailable)',
        'if hasattr(b, "Connectors"):',
        '    ut["connector_count"] = b.ConnectorCount',
        'if hasattr(b, "Statistics"):',
        '    ut["has_statistics"] = b.Statistics is not None',
        "_svara(ut)",
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag", "_kvot"]) + rader)


_lagg(
    "transport_behaviour_info",
    "Allt om ett namngivet transport- eller flodesbeteende: vilka slag det ar "
    "av, om det ar pa, kapacitet och fyllnadsgrad, antal flodesportar och om "
    "det for statistik. Nycklar vars yta saknas pa just det beteendet "
    "utelamnas i stallet for att svara noll.",
    "read",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE},
           ["component", "behaviour"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Beteendet."},
             "kinds": RET_SLAG,
             "enabled": {"type": "boolean", "description": "Om beteendet ar pa."},
             "type": {"type": ["string", "number", "integer", "null"],
                      "description": "VC:s typupprakning for beteendet."},
             "property_count": {"type": "integer",
                                "description": "Antal parametrar pa beteendet."},
             "capacity": {"type": "integer",
                          "description": "Hur manga komponenter det rymmer. Utelamnas om beteendet inte haller nagot."},
             "component_count": {"type": "integer",
                                 "description": "Hur manga som ligger i det nu."},
             "fill_ratio": {"type": ["number", "null"],
                            "description": "component_count delat med capacity. null nar kapaciteten ar obegransad."},
             "capacity_available": {"type": "boolean",
                                    "description": "Om det finns plats kvar."},
             "connector_count": {"type": "integer",
                                 "description": "Antal flodesportar. Utelamnas om beteendet inte ar ett flode."},
             "has_statistics": {"type": "boolean",
                                "description": "Om beteendet har ett statistikobjekt."}},
            ["component", "behaviour", "kinds", "enabled", "property_count"]),
    _Y_BET,
    _kod_transport_behaviour_info,
)


# ---- list_transport_parameters -------------------------------------------

def _kod_list_transport_parameters(argument):
    rader = _hamta_komponent(argument["component"])
    if "behaviour" in argument:
        rader += _hamta_beteende(argument["behaviour"])
        rader += ["agare = b.Name", "kalla = b.Properties"]
    else:
        rader += ["agare = k.Name", "kalla = k.Properties"]
    rader += ["rader = []", "avkortad = False", "for p in kalla:"]
    rader += tak("rader")
    rader += [
        '    rader.append({"name": p.Name, "value": _enkelt(p.Value),',
        '                  "type": _enkelt(p.Type),',
        '                  "writable_when_simulating": bool(p.WritableWhenSimulating),',
        '                  "writable_when_connected": bool(p.WritableWhenConnected)})',
    ]
    rader += [
        '_svara({"component": k.Name, "owner": agare, "parameters": rader,',
        '        "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "list_transport_parameters",
    "Listar parametrarna pa en komponent eller pa ett av dess beteenden. HAR "
    "ligger transportorens hastighet, langd, riktning och ackumulering: VC "
    "exponerar dem som parametrar med namn som varierar per komponent, inte "
    "som ett fast API. Las listan forst, valj sedan namnet ur den.",
    "read",
    params({"component": ARG_KOMPONENT,
            "behaviour": dict(ARG_BETEENDE, description=(
                "Las beteendets egna parametrar. Utelamnad laser komponentens."))},
           ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "owner": {"type": "string",
                       "description": "Vem parametrarna sitter pa: komponenten eller beteendet."},
             "parameters": {"type": "array", "description": "Parametrarna.",
                            "items": _PARAMETERPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "owner", "parameters", "antal", "avkortad"]),
    _Y_KOMP + ("comp.Properties", "comp.findBehaviour"),
    _kod_list_transport_parameters,
)


# ---- get_transport_parameter ---------------------------------------------

def _rader_sok_parameter(argument):
    """Raderna som letar upp EN parameter i en lista. p ar None om den saknas.

    Sokningen gar genom listan och inte genom getProperty, av ett matt skal:
    getProperty finns pa vcComponent men INTE pa vcBehaviour i den matta ytan.
    En sokning duger till bada, sa bada vagarna blir samma kod.
    """
    if "behaviour" in argument:
        kalla = ["kalla = b.Properties", "agare = b.Name"]
    else:
        kalla = ["kalla = k.Properties", "agare = k.Name"]
    return kalla + [
        "p = None",
        "for q in kalla:",
        "    if q.Name == %s:" % lit(argument["parameter"]),
        "        p = q",
    ]


def _kod_get_transport_parameter(argument):
    rader = _hamta_komponent(argument["component"])
    if "behaviour" in argument:
        rader += _hamta_beteende(argument["behaviour"])
    rader += _rader_sok_parameter(argument)
    rader += [
        "if p is None:",
        '    _svara({"found": False, "component": k.Name, "owner": agare,',
        '            "parameter": %s})' % lit(argument["parameter"]),
        "else:",
        '    _svara({"found": True, "component": k.Name, "owner": agare,',
        '            "parameter": p.Name, "value": _enkelt(p.Value),',
        '            "type": _enkelt(p.Type),',
        '            "writable_when_simulating": bool(p.WritableWhenSimulating),',
        '            "writable_when_connected": bool(p.WritableWhenConnected)})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "get_transport_parameter",
    "Laser en namngiven parameter pa en komponent eller pa ett av dess "
    "beteenden, och sager om den gar att andra. found=false ar ett giltigt "
    "svar och betyder att namnet inte finns - det ar aldrig en gissning.",
    "read",
    params({"component": ARG_KOMPONENT, "parameter": ARG_PARAMETER,
            "behaviour": dict(ARG_BETEENDE, description=(
                "Las pa beteendet. Utelamnad laser pa komponenten."))},
           ["component", "parameter"]),
    returns({"found": {"type": "boolean", "description": "Om parametern fanns."},
             "component": {"type": "string", "description": "Komponenten."},
             "owner": {"type": "string", "description": "Komponenten eller beteendet."},
             "parameter": {"type": "string", "description": "Parameterns namn."},
             "value": RET_VARDE,
             "type": {"type": ["string", "number", "integer", "null"],
                      "description": "VC:s typupprakning."},
             "writable_when_simulating": {"type": "boolean",
                                          "description": "Om den gar att andra under korning."},
             "writable_when_connected": {"type": "boolean",
                                         "description": "Om den gar att andra nar komponenten ar kopplad."}},
            ["found", "component", "owner", "parameter"]),
    _Y_KOMP + ("comp.Properties", "comp.findBehaviour"),
    _kod_get_transport_parameter,
)


# ---- set_transport_parameter ---------------------------------------------

def _kod_set_transport_parameter(argument):
    rader = _hamta_komponent(argument["component"])
    if "behaviour" in argument:
        rader += _hamta_beteende(argument["behaviour"])
    rader += _rader_sok_parameter(argument)
    rader += [
        "if p is None:",
        # En parameter som inte finns far inte skapas har. Att skapa en
        # egenskap ar en annan sak an att stalla in en transportor, och en
        # tyst nyskapad parameter gor ingenting i VC (S1).
        '    raise ValueError(agare + " har ingen parameter som heter " + %s)'
        % lit(argument["parameter"]),
        "p.Value = %s" % lit(argument["value"]),
        '_svara({"set": True, "component": k.Name, "owner": agare,',
        '        "parameter": p.Name, "value": _enkelt(p.Value)})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "set_transport_parameter",
    "Satter en namngiven parameter pa en komponent eller pa ett av dess "
    "beteenden. Det ar vagen att andra en transportors hastighet, riktning, "
    "langd eller ackumulering. Parametern maste redan finnas; verktyget skapar "
    "aldrig en ny.",
    "write",
    params({"component": ARG_KOMPONENT, "parameter": ARG_PARAMETER,
            "value": {"type": ["string", "number", "integer", "boolean"],
                      "description": "Det nya vardet, i parameterns egen typ."},
            "behaviour": dict(ARG_BETEENDE, description=(
                "Satt pa beteendet. Utelamnad satter pa komponenten."))},
           ["component", "parameter", "value"]),
    returns({"set": {"type": "boolean",
                     "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "owner": {"type": "string", "description": "Komponenten eller beteendet."},
             "parameter": {"type": "string", "description": "Parameterns namn."},
             "value": RET_VARDE},
            ["set", "component", "owner", "parameter", "value"]),
    _Y_KOMP + ("comp.Properties", "comp.findBehaviour"),
    _kod_set_transport_parameter,
)


# ---- get_capacity --------------------------------------------------------

def _kod_get_capacity(argument):
    rader = _hamta_komponent(argument["component"])
    if "behaviour" in argument:
        rader += _hamta_beteende(argument["behaviour"])
        rader += _krav_slag("container")
        rader += ["beteenden = [b]"]
    else:
        rader += ["beteenden = k.Behaviours"]
    rader += ["rader = []", "avkortad = False", "for b in beteenden:"]
    rader += tak("rader")
    rader += [
        '    if "container" not in _slag(b):',
        "        continue",
        '    post = {"behaviour": b.Name, "capacity": b.Capacity,',
        '            "component_count": b.ComponentCount,',
        '            "fill_ratio": _kvot(b.ComponentCount, b.Capacity),',
        '            "capacity_available": bool(b.CapacityAvailable),',
        '            "head": None, "tail": None}',
        "    if b.HeadComponent is not None:",
        '        post["head"] = b.HeadComponent.Name',
        "    if b.TailComponent is not None:",
        '        post["tail"] = b.TailComponent.Name',
        "    rader.append(post)",
        '_svara({"component": k.Name, "containers": rader,',
        '        "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag", "_kvot"]) + rader)


_lagg(
    "get_capacity",
    "Kapacitet och fyllnadsgrad for de beteenden pa en komponent som haller "
    "andra komponenter - transportorer, buffertar och magasin. Utan behaviour "
    "gas alla igenom. fill_ratio ar antal delat med kapacitet och ar null nar "
    "kapaciteten ar obegransad.",
    "read",
    params({"component": ARG_KOMPONENT,
            "behaviour": dict(ARG_BETEENDE, description=(
                "Begransa till ett beteende. Utelamnad tar alla som haller "
                "komponenter."))},
           ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "containers": {
                 "type": "array", "description": "Beteendena som haller komponenter.",
                 "items": {"type": "object", "description": "En behallare.",
                           "properties": {
                               "behaviour": {"type": "string", "description": "Beteendets namn."},
                               "capacity": {"type": "integer", "description": "Hur manga det rymmer."},
                               "component_count": {"type": "integer", "description": "Hur manga som ligger i det nu."},
                               "fill_ratio": {"type": ["number", "null"],
                                              "description": "Antal delat med kapacitet, null vid obegransad kapacitet."},
                               "capacity_available": {"type": "boolean", "description": "Om det finns plats kvar."},
                               "head": {"type": ["string", "null"], "description": "Namnet pa komponenten langst fram, null om tom."},
                               "tail": {"type": ["string", "null"], "description": "Namnet pa komponenten langst bak, null om tom."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "containers", "antal", "avkortad"]),
    _Y_BETLISTA + ("comp.findBehaviour",),
    _kod_get_capacity,
)


# ---- set_capacity --------------------------------------------------------

def _kod_set_capacity(argument):
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += _krav_slag("container")
    rader += [
        "b.Capacity = %d" % argument["capacity"],
        '_svara({"set": True, "component": k.Name, "behaviour": b.Name,',
        '        "capacity": b.Capacity, "component_count": b.ComponentCount,',
        '        "fill_ratio": _kvot(b.ComponentCount, b.Capacity)})',
    ]
    return bygg(["_svara"], _lokala(["_slag", "_kvot"]) + rader)


_lagg(
    "set_capacity",
    "Satter hur manga komponenter ett transport-, buffert- eller "
    "magasinbeteende rymmer. Beteendet maste vara ett som haller komponenter; "
    "annars kastar verktyget och sager vilka slag det var.",
    "write",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE,
            "capacity": {"type": "integer",
                         "description": ("Nytt antal platser. Noll eller mindre "
                                         "betyder obegransat i VC.")}},
           ["component", "behaviour", "capacity"]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Beteendet."},
             "capacity": {"type": "integer", "description": "Kapaciteten efterat, last ur VC."},
             "component_count": {"type": "integer", "description": "Antal i beteendet nu."},
             "fill_ratio": {"type": ["number", "null"], "description": "Fyllnadsgrad efterat."}},
            ["set", "component", "behaviour", "capacity", "component_count"]),
    _Y_BET,
    _kod_set_capacity,
)


# ---- list_buffer_contents ------------------------------------------------

def _kod_list_buffer_contents(argument):
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += _krav_slag("container")
    rader += ["rader = []", "avkortad = False", "for c in b.Components:"]
    rader += tak("rader")
    rader += [
        '    post = {"name": c.Name, "uri": c.Uri, "product_type": None}',
        "    pr = c.Product",
        "    if pr is not None and pr.ProductType is not None:",
        '        post["product_type"] = pr.ProductType.Name',
        "    rader.append(post)",
        '_svara({"component": k.Name, "behaviour": b.Name, "contents": rader,',
        '        "capacity": b.Capacity, "antal": len(rader),',
        '        "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_buffer_contents",
    "Vad som ligger i en buffert, ett magasin eller pa en transportor just nu, "
    "med produkttyp per post. Ordningen ar VC:s egen. Om bufferten tommer "
    "FIFO eller LIFO ar en PARAMETER pa komponenten, inte ett API-varde - las "
    "den med list_transport_parameters.",
    "read",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE},
           ["component", "behaviour"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Beteendet."},
             "capacity": {"type": "integer", "description": "Hur manga beteendet rymmer."},
             "contents": {
                 "type": "array", "description": "Innehallet i VC:s egen ordning.",
                 "items": {"type": "object", "description": "En komponent i behallaren.",
                           "properties": {
                               "name": {"type": "string", "description": "Komponentens namn."},
                               "uri": {"type": ["string", "null"], "description": "URI den laddades fran."},
                               "product_type": {"type": ["string", "null"],
                                                "description": "Produkttypens namn, null om komponenten inte ar en produkt."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "behaviour", "contents", "antal", "avkortad"]),
    _Y_BET + ("comp.Uri",),
    _kod_list_buffer_contents,
)


# ---- list_flow_connectors ------------------------------------------------

def _kod_list_flow_connectors(argument):
    rader = _komponentkalla(argument)
    rader += [
        "rader = []",
        "avkortad = False",
        "for k in komponenter:",
        "    if avkortad:",
        "        break",
        "    for b in k.Behaviours:",
        "        if avkortad:",
        "            break",
        '        if "flow" not in _slag(b):',
        "            continue",
        "        for c in b.Connectors:",
    ]
    rader += tak("rader", "            ")
    rader += [
        '            post = {"component": k.Name, "behaviour": b.Name,',
        '                    "connector": c.Name, "index": c.Index,',
        '                    "connected_to": None,',
        '                    "connected_behaviour": None,',
        '                    "connected_component": None}',
        "            d = c.Connection",
        "            if d is not None:",
        '                post["connected_to"] = d.Name',
        "                if d.Behaviour is not None:",
        '                    post["connected_behaviour"] = d.Behaviour.Name',
        "                    if d.Behaviour.Component is not None:",
        '                        post["connected_component"] = d.Behaviour.Component.Name',
        "            rader.append(post)",
        '_svara({"connectors": rader, "antal": len(rader),'
        ' "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_flow_connectors",
    "Hur produkterna kan ta sig vidare: flodesbeteendenas portar och vad varje "
    "port ar kopplad till, per komponent eller for hela layouten. Det ar den "
    "snabbaste bilden av vagvalen i linan.",
    "read",
    params({"component": ARG_KOMPONENT_VALFRI}),
    returns({"connectors": {
                 "type": "array", "description": "Flodesportarna.",
                 "items": {"type": "object", "description": "En flodesport.",
                           "properties": {
                               "component": {"type": "string", "description": "Komponenten."},
                               "behaviour": {"type": "string", "description": "Flodesbeteendet."},
                               "connector": {"type": "string", "description": "Portens namn."},
                               "index": {"type": "integer", "description": "Portens index i beteendet."},
                               "connected_to": {"type": ["string", "null"], "description": "Motpartens portnamn, null om okopplad."},
                               "connected_behaviour": {"type": ["string", "null"], "description": "Motpartens beteende."},
                               "connected_component": {"type": ["string", "null"], "description": "Motpartens komponent."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["connectors", "antal", "avkortad"]),
    ("app.Components", "app.findComponent", "comp.Name", "comp.Behaviours"),
    _kod_list_flow_connectors,
)


# ---- get_routing_rule ----------------------------------------------------

def _kod_get_routing_rule(argument):
    rader = _hamta_komponent(argument["component"])
    if "behaviour" in argument:
        rader += _hamta_beteende(argument["behaviour"])
        rader += _krav_slag("routing_rule")
        rader += ["beteenden = [b]"]
    else:
        rader += ["beteenden = k.Behaviours"]
    rader += ["rader = []", "avkortad = False", "for b in beteenden:"]
    rader += tak("rader")
    rader += [
        '    if "routing_rule" not in _slag(b):',
        "        continue",
        '    post = {"behaviour": b.Name, "rule": _enkelt(b.RuleComponent),',
        '            "connector_count": b.ConnectorCount,',
        '            "capacity": b.Capacity,',
        '            "component_count": b.ComponentCount,',
        '            "flow_proxy": None, "targets": []}',
        "    if b.FlowProxy is not None:",
        '        post["flow_proxy"] = b.FlowProxy.Name',
        "    for c in b.Connectors:",
        '        post["targets"].append({"connector": c.Name, "index": c.Index})',
        "    rader.append(post)",
        '_svara({"component": k.Name, "rules": rader, "antal": len(rader),',
        '        "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "get_routing_rule",
    "Dirigeringsreglerna pa en komponent: vilken regel som styr valet, hur "
    "manga utgangar den har och vad de heter. Regelvardet kommer som VC:s eget "
    "upprakningsvarde och tolkas inte om.",
    "read",
    params({"component": ARG_KOMPONENT,
            "behaviour": dict(ARG_BETEENDE, description=(
                "Begransa till en regel. Utelamnad tar alla pa komponenten."))},
           ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "rules": {
                 "type": "array", "description": "Dirigeringsreglerna.",
                 "items": {"type": "object", "description": "En dirigeringsregel.",
                           "properties": {
                               "behaviour": {"type": "string", "description": "Regelbeteendets namn."},
                               "rule": {"type": ["string", "number", "integer", "null"],
                                        "description": "VC:s upprakningsvarde for regeln."},
                               "connector_count": {"type": "integer", "description": "Antal utgangar."},
                               "capacity": {"type": "integer", "description": "Hur manga regeln rymmer."},
                               "component_count": {"type": "integer", "description": "Hur manga som ligger i den nu."},
                               "flow_proxy": {"type": ["string", "null"], "description": "Flodesproxyns namn, null om ingen."},
                               "targets": {"type": "array", "description": "Utgangarna.",
                                           "items": {"type": "object", "description": "En utgang.",
                                                     "properties": {
                                                         "connector": {"type": "string", "description": "Portens namn."},
                                                         "index": {"type": "integer", "description": "Portens index, det setTarget tar."}}}}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "rules", "antal", "avkortad"]),
    _Y_BETLISTA + ("comp.findBehaviour",),
    _kod_get_routing_rule,
)


# ---- set_routing_target --------------------------------------------------

def _kod_set_routing_target(argument):
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += _krav_slag("routing_rule")
    rader += [
        "b.setTarget(%d)" % argument["connector"],
        '_svara({"set": True, "component": k.Name, "behaviour": b.Name,',
        '        "connector": %d, "connector_count": b.ConnectorCount})'
        % argument["connector"],
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "set_routing_target",
    "Pekar ut vilken utgang en dirigeringsregel ska skicka nasta produkt "
    "genom. Indexet maste komma ur get_routing_rule; ett uppfunnet index ar "
    "ett hart fel.",
    "write",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE,
            "connector": {"type": "integer",
                          "description": ("Utgangens index, exakt som "
                                          "get_routing_rule lamnade det.")}},
           ["component", "behaviour", "connector"]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Regelbeteendet."},
             "connector": {"type": "integer", "description": "Indexet som sattes."},
             "connector_count": {"type": "integer", "description": "Antal utgangar regeln har."}},
            ["set", "component", "behaviour", "connector"]),
    _Y_BET,
    _kod_set_routing_target,
)


# ---- list_path_sensors ---------------------------------------------------

def _kod_list_path_sensors(argument):
    rader = _komponentkalla(argument)
    rader += [
        "rader = []",
        "avkortad = False",
        "for k in komponenter:",
        "    if avkortad:",
        "        break",
        "    for b in k.Behaviours:",
    ]
    rader += tak("rader", "        ")
    rader += [
        '        if "sensor" not in _slag(b):',
        "            continue",
        '        post = {"component": k.Name, "sensor": b.Name,',
        '                "enabled": bool(b.Enabled),',
        '                "trigger_at": _enkelt(b.TriggerAt),',
        '                "process_at": _enkelt(b.ProcessAt),',
        '                "rule": _enkelt(b.RuleComponent),',
        '                "frame": None, "signal": None, "value": None}',
        "        if b.Frame is not None:",
        '            post["frame"] = b.Frame.Name',
        "        sg = b.BoolSignal",
        "        if sg is not None:",
        '            post["signal"] = sg.Name',
        # Signalens varde ar det enda sensorn sjalv minns av vad som passerat:
        # den bar ingen lista over passager i den matta ytan. Vardet ar sant
        # medan nagot star pa sensorn, och det sags i beskrivningen.
        '            post["value"] = _enkelt(sg.Value)',
        "        rader.append(post)",
        '_svara({"sensors": rader, "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_path_sensors",
    "Sensorerna pa banan, per komponent eller for hela layouten: var de sitter "
    "(deras ram), vilken signal de driver, signalens varde just nu och nar de "
    "loser ut. VC:s sensor for ingen lista over vad som passerat - value ar "
    "sant medan nagot star pa sensorn, och rakningen av passager gor "
    "statistikbeteendet (station_statistics).",
    "read",
    params({"component": ARG_KOMPONENT_VALFRI}),
    returns({"sensors": {
                 "type": "array", "description": "Sensorerna.",
                 "items": {"type": "object", "description": "En sensor pa banan.",
                           "properties": {
                               "component": {"type": "string", "description": "Komponenten."},
                               "sensor": {"type": "string", "description": "Sensorbeteendets namn."},
                               "enabled": {"type": "boolean", "description": "Om sensorn ar pa."},
                               "trigger_at": {"type": ["string", "number", "integer", "null"],
                                              "description": "VC:s upprakningsvarde for nar sensorn loser ut."},
                               "process_at": {"type": ["string", "number", "integer", "null"],
                                              "description": "VC:s upprakningsvarde for nar den bearbetar."},
                               "rule": {"type": ["string", "number", "integer", "null"],
                                        "description": "VC:s upprakningsvarde for vilken komponent regeln galler."},
                               "frame": {"type": ["string", "null"], "description": "Ramens namn, alltsa var pa banan sensorn sitter."},
                               "signal": {"type": ["string", "null"], "description": "Signalens namn."},
                               "value": {"type": ["boolean", "string", "number", "integer", "null"],
                                         "description": "Signalens varde just nu."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["sensors", "antal", "avkortad"]),
    ("app.Components", "app.findComponent", "comp.Name", "comp.Behaviours"),
    _kod_list_path_sensors,
)


# ---- get_feeder_info -----------------------------------------------------

def _kod_get_feeder_info(argument):
    rader = _hamta_komponent(argument["component"])
    if "behaviour" in argument:
        rader += _hamta_beteende(argument["behaviour"])
        rader += _krav_slag("product_creator")
        rader += ["beteenden = [b]"]
    else:
        rader += ["beteenden = k.Behaviours"]
    rader += ["rader = []", "avkortad = False", "for b in beteenden:"]
    rader += tak("rader")
    rader += [
        '    if "product_creator" not in _slag(b):',
        "        continue",
        '    post = {"behaviour": b.Name, "feed_mode": _enkelt(b.FeedMode),',
        '            "part_pooling": bool(b.PartPooling),',
        '            "single": None, "distribution": None,',
        '            "batch": None, "table": None}',
        "    sf = b.SingleFeed",
        "    if sf is not None:",
        '        enkel = {"interval": _enkelt(sf.Interval), "limit": sf.Limit,',
        '                 "product_type": None}',
        "        if sf.Part is not None:",
        '            enkel["product_type"] = sf.Part.Name',
        '        post["single"] = enkel',
        "    df = b.DistributionFeed",
        "    if df is not None:",
        '        poster = []',
        "        for e in df.ProductEntries:",
        '            namn = None',
        "            if e.ProductType is not None:",
        "                namn = e.ProductType.Name",
        '            poster.append({"product_type": namn,',
        '                           "probability": e.Probability})',
        '        post["distribution"] = {"interval": _enkelt(df.Interval),',
        '                                "limit": df.Limit,',
        '                                "random_stream": df.RandomStream,',
        '                                "entries": poster}',
        "    bf = b.BatchFeed",
        "    if bf is not None:",
        '        post["batch"] = {"batch_interval": bf.BatchInterval,',
        '                         "loop": bool(bf.Loop),',
        '                         "batch_count": len(bf.ProductBatches)}',
        "    tf = b.TableFeed",
        "    if tf is not None:",
        '        post["table"] = {"file": tf.File, "row_count": tf.RowCount}',
        "    rader.append(post)",
        '_svara({"component": k.Name, "feeders": rader, "antal": len(rader),',
        '        "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "get_feeder_info",
    "Hur produkter matas in: produktskaparens matningslage och alla fyra "
    "lagens installningar - enkel takt, fordelning med sannolikheter, batch "
    "och tabell. Intervallet kommer som VC:s fordelningsuttryck i text, "
    "eftersom det kan vara en fordelning och inte ett tal.",
    "read",
    params({"component": ARG_KOMPONENT,
            "behaviour": dict(ARG_BETEENDE, description=(
                "Begransa till en produktskapare. Utelamnad tar alla pa "
                "komponenten."))},
           ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "feeders": {
                 "type": "array", "description": "Produktskaparna.",
                 "items": {"type": "object", "description": "En produktskapare.",
                           "properties": {
                               "behaviour": {"type": "string", "description": "Beteendets namn."},
                               "feed_mode": {"type": ["string", "number", "integer", "null"],
                                             "description": "VC:s upprakningsvarde for vilket matningslage som ar valt."},
                               "part_pooling": {"type": "boolean", "description": "Om skaparen ateranvander produkter."},
                               "single": {"type": ["object", "null"], "description": "Enkelt lage: takt, gras och produkttyp.",
                                          "properties": {
                                              "interval": {"type": ["string", "number", "null"], "description": "Fordelningsuttryck for tiden mellan tva produkter."},
                                              "limit": {"type": "integer", "description": "Hogsta antal produkter, 0 for obegransat."},
                                              "product_type": {"type": ["string", "null"], "description": "Produkttypens namn."}}},
                               "distribution": {"type": ["object", "null"], "description": "Fordelningslage.",
                                                "properties": {
                                                    "interval": {"type": ["string", "number", "null"], "description": "Fordelningsuttryck for takten."},
                                                    "limit": {"type": "integer", "description": "Hogsta antal produkter."},
                                                    "random_stream": {"type": "integer", "description": "Vilken slumpstrom fordelningen drar ur."},
                                                    "entries": {"type": "array", "description": "Produkttyperna och deras sannolikheter.",
                                                                "items": {"type": "object", "description": "En rad i fordelningen.",
                                                                          "properties": {
                                                                              "product_type": {"type": ["string", "null"], "description": "Produkttypens namn."},
                                                                              "probability": {"type": "number", "description": "Sannolikhet for raden."}}}}}},
                               "batch": {"type": ["object", "null"], "description": "Batchlage.",
                                         "properties": {
                                             "batch_interval": {"type": "number", "description": "Tid mellan batcher i sekunder."},
                                             "loop": {"type": "boolean", "description": "Om batchlistan borjar om."},
                                             "batch_count": {"type": "integer", "description": "Antal batcher i listan."}}},
                               "table": {"type": ["object", "null"], "description": "Tabellage.",
                                         "properties": {
                                             "file": {"type": ["string", "null"], "description": "Filen tabellen lases ur."},
                                             "row_count": {"type": "integer", "description": "Antal rader i tabellen."}}}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "feeders", "antal", "avkortad"]),
    _Y_BETLISTA + ("comp.findBehaviour",),
    _kod_get_feeder_info,
)


# ---- set_product_feed ----------------------------------------------------

def _kod_set_product_feed(argument):
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += _krav_slag("product_creator")
    rader += [
        "sf = b.SingleFeed",
        "if sf is None:",
        '    raise ValueError(b.Name + " har inget enkelt matningslage")',
    ]
    if "interval" in argument:
        # Intervallet ar ett FORDELNINGSUTTRYCK, inte ett tal: VC deklarerar
        # typen "Distribution expression". Det skickas darfor som text, och
        # texten gar genom _s() som allt annat som nar VC:s py2-bindning.
        rader.append("sf.Interval = %s" % lit(argument["interval"]))
    if "limit" in argument:
        rader.append("sf.Limit = %d" % argument["limit"])
    rader += [
        '_svara({"set": True, "component": k.Name, "behaviour": b.Name,',
        '        "interval": _enkelt(sf.Interval), "limit": sf.Limit})',
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "set_product_feed",
    "Satter takten pa en produktskapares enkla matningslage: tiden mellan tva "
    "produkter och hogsta antal. Tiden ar ett fordelningsuttryck i text, "
    "exempelvis ett tal for fast takt eller ett uttryck for en fordelning - "
    "las get_feeder_info forst for att se vilken form komponenten redan bar.",
    "write",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE,
            "interval": {"type": "string",
                         "description": ("Nytt fordelningsuttryck for tiden "
                                         "mellan tva produkter, i sekunder.")},
            "limit": {"type": "integer",
                      "description": "Hogsta antal produkter. 0 betyder obegransat."}},
           ["component", "behaviour"],
           minst_en_av=[("interval", "limit")]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Produktskaparen."},
             "interval": {"type": ["string", "number", "null"], "description": "Intervallet efterat, last ur VC."},
             "limit": {"type": "integer", "description": "Gransen efterat, last ur VC."}},
            ["set", "component", "behaviour", "interval", "limit"]),
    _Y_BET,
    _kod_set_product_feed,
)


# ---- get_component_creator_info ------------------------------------------

def _kod_get_component_creator_info(argument):
    rader = _hamta_komponent(argument["component"])
    rader += ["rader = []", "avkortad = False", "for b in k.Behaviours:"]
    rader += tak("rader")
    rader += [
        '    if "component_creator" not in _slag(b):',
        "        continue",
        '    post = {"behaviour": b.Name, "interval": b.Interval,',
        '            "limit": b.Limit, "part": b.Part,',
        '            "part_pooling": bool(b.PartPooling),',
        '            "blocking_optimization": bool(b.BlockingOptimization),',
        '            "capacity": b.Capacity,',
        '            "component_count": b.ComponentCount,',
        '            "template": None}',
        "    if b.TemplateComponent is not None:",
        '        post["template"] = b.TemplateComponent.Name',
        "    rader.append(post)",
        '_svara({"component": k.Name, "creators": rader, "antal": len(rader),',
        '        "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "get_component_creator_info",
    "Komponentskaparna pa en komponent: takt, hogsta antal, vilken del de "
    "skapar och vilken mallkomponent de kopierar. Det ar den andra "
    "matningsvagen i VC vid sidan av produktskaparen.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "creators": {
                 "type": "array", "description": "Komponentskaparna.",
                 "items": {"type": "object", "description": "En komponentskapare.",
                           "properties": {
                               "behaviour": {"type": "string", "description": "Beteendets namn."},
                               "interval": {"type": "number", "description": "Tid mellan tva skapade komponenter, i sekunder."},
                               "limit": {"type": "integer", "description": "Hogsta antal, 0 for obegransat."},
                               "part": {"type": ["string", "null"], "description": "Namnet pa delen som skapas."},
                               "part_pooling": {"type": "boolean", "description": "Om skaparen ateranvander komponenter."},
                               "blocking_optimization": {"type": "boolean", "description": "Om VC:s blockeringsoptimering ar pa."},
                               "capacity": {"type": "integer", "description": "Hur manga skaparen rymmer."},
                               "component_count": {"type": "integer", "description": "Hur manga som ligger i den nu."},
                               "template": {"type": ["string", "null"], "description": "Mallkomponentens namn, null om ingen."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "creators", "antal", "avkortad"]),
    _Y_BETLISTA,
    _kod_get_component_creator_info,
)


# ---- set_component_feed --------------------------------------------------

def _kod_set_component_feed(argument):
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += _krav_slag("component_creator")
    if "interval" in argument:
        # vcComponentCreator.Interval ar deklarerad Real, inte ett
        # fordelningsuttryck. Darfor tal() och inte lit().
        rader.append("b.Interval = %s" % tal(argument["interval"]))
    if "limit" in argument:
        rader.append("b.Limit = %d" % argument["limit"])
    rader += [
        '_svara({"set": True, "component": k.Name, "behaviour": b.Name,',
        '        "interval": b.Interval, "limit": b.Limit})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "set_component_feed",
    "Satter takten pa en komponentskapare: sekunder mellan tva komponenter och "
    "hogsta antal. Till skillnad fran produktskaparen ar takten har ett rent "
    "tal, inte ett fordelningsuttryck.",
    "write",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE,
            "interval": {"type": "number",
                         "description": "Sekunder mellan tva skapade komponenter."},
            "limit": {"type": "integer",
                      "description": "Hogsta antal komponenter. 0 betyder obegransat."}},
           ["component", "behaviour"],
           minst_en_av=[("interval", "limit")]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Komponentskaparen."},
             "interval": {"type": "number", "description": "Takten efterat, last ur VC."},
             "limit": {"type": "integer", "description": "Gransen efterat, last ur VC."}},
            ["set", "component", "behaviour", "interval", "limit"]),
    _Y_BET,
    _kod_set_component_feed,
)


# ---- list_transport_nodes ------------------------------------------------

def _kod_list_transport_nodes(argument):
    rader = _komponentkalla(argument)
    rader += [
        "rader = []",
        "avkortad = False",
        "for k in komponenter:",
        "    if avkortad:",
        "        break",
        "    for b in k.Behaviours:",
    ]
    rader += tak("rader", "        ")
    rader += [
        '        if "transport_node" not in _slag(b):',
        "            continue",
        '        lankar = []',
        "        for l in b.TransportLinks:",
        '            lank = {"source": None, "destination": None,',
        '                    "implementer": None, "group": None}',
        "            if l.Source is not None:",
        '                lank["source"] = l.Source.Name',
        "            if l.Destination is not None:",
        '                lank["destination"] = l.Destination.Name',
        "            if l.Implementer is not None:",
        '                lank["implementer"] = l.Implementer.Name',
        "            if l.SupportedGroup is not None:",
        '                lank["group"] = l.SupportedGroup.Name',
        "            lankar.append(lank)",
        '        rader.append({"component": k.Name, "node": b.Name,',
        '                      "enabled": bool(b.Enabled),',
        '                      "reset_at": _enkelt(b.ResetAt),',
        '                      "trigger_at": _enkelt(b.TriggerAt),',
        '                      "links": lankar})',
        '_svara({"nodes": rader, "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_transport_nodes",
    "Transportnoderna och deras lankar: varifran och vart en produkt kan "
    "flyttas, vem som utfor flytten och vilken flodesgrupp lanken bar. Det ar "
    "kartan over transportsystemet i en processlayout.",
    "read",
    params({"component": ARG_KOMPONENT_VALFRI}),
    returns({"nodes": {
                 "type": "array", "description": "Transportnoderna.",
                 "items": {"type": "object", "description": "En transportnod.",
                           "properties": {
                               "component": {"type": "string", "description": "Komponenten noden sitter pa."},
                               "node": {"type": "string", "description": "Nodbeteendets namn."},
                               "enabled": {"type": "boolean", "description": "Om noden ar pa."},
                               "reset_at": {"type": ["string", "number", "integer", "null"], "description": "VC:s upprakningsvarde for nar noden nollstalls."},
                               "trigger_at": {"type": ["string", "number", "integer", "null"], "description": "VC:s upprakningsvarde for nar noden loser ut."},
                               "links": {"type": "array", "description": "Lankarna ut ur och in i noden.",
                                         "items": {"type": "object", "description": "En transportlank.",
                                                   "properties": {
                                                       "source": {"type": ["string", "null"], "description": "Kallnodens namn."},
                                                       "destination": {"type": ["string", "null"], "description": "Malnodens namn."},
                                                       "implementer": {"type": ["string", "null"], "description": "Transportregulatorn som utfor flytten."},
                                                       "group": {"type": ["string", "null"], "description": "Flodesgruppen lanken bar."}}}}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["nodes", "antal", "avkortad"]),
    ("app.Components", "app.findComponent", "comp.Name", "comp.Behaviours"),
    _kod_list_transport_nodes,
)


# ---- list_process_flow_groups --------------------------------------------

def _kod_list_process_flow_groups(argument):
    rader = _hamta_komponent(argument["component"])
    rader += [
        "styrning = None",
        "for b in k.Behaviours:",
        '    if "process_controller" in _slag(b):',
        "        styrning = b",
        "if styrning is None:",
        '    raise ValueError(k.Name + " bar ingen processregulator")',
        "chef = styrning.FlowGroupManager",
        "if chef is None:",
        '    raise ValueError(k.Name + " har en processregulator utan'
        ' flodesgrupphanterare")',
        "rader = []",
        "avkortad = False",
        "for g in chef.Groups:",
    ]
    rader += tak("rader")
    rader += [
        "    typer = []",
        "    for t in g.ProductTypes:",
        "        typer.append(t.Name)",
        '    rader.append({"group": g.Name, "visible": bool(g.IsVisible),',
        '                  "product_types": typer})',
        '_svara({"component": k.Name, "behaviour": styrning.Name,',
        '        "groups": rader, "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_process_flow_groups",
    "Flodesgrupperna i processregulatorn och vilka produkttyper som ligger i "
    "var grupp. Grupperna ar det som avgor vilka transportlankar en produkt "
    "far anvanda. Komponenten maste bara en processregulator; annars kastar "
    "verktyget i stallet for att svara tomt.",
    "read",
    params({"component": dict(ARG_KOMPONENT, description=(
        "Komponenten som bar processregulatorn. Hitta den med "
        "list_transport_behaviours och kind=process_controller."))},
           ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Processregulatorns namn."},
             "groups": {
                 "type": "array", "description": "Flodesgrupperna.",
                 "items": {"type": "object", "description": "En flodesgrupp.",
                           "properties": {
                               "group": {"type": "string", "description": "Gruppens namn."},
                               "visible": {"type": "boolean", "description": "Om gruppen visas i granssnittet."},
                               "product_types": {"type": "array", "description": "Produkttyperna i gruppen.",
                                                 "items": {"type": "string", "description": "Produkttypens namn."}}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "behaviour", "groups", "antal", "avkortad"]),
    _Y_BETLISTA,
    _kod_list_process_flow_groups,
)


# ---- list_product_types --------------------------------------------------

def _kod_list_product_types(argument):
    rader = _hamta_komponent(argument["component"])
    rader += [
        "styrning = None",
        "for b in k.Behaviours:",
        '    if "process_controller" in _slag(b):',
        "        styrning = b",
        "if styrning is None:",
        '    raise ValueError(k.Name + " bar ingen processregulator")',
        "chef = styrning.ProductTypeManager",
        "if chef is None:",
        '    raise ValueError(k.Name + " har en processregulator utan'
        ' produkttyphanterare")',
        "rader = []",
        "avkortad = False",
        "for t in chef.ProductTypes:",
    ]
    rader += tak("rader")
    rader += [
        '    post = {"product_type": t.Name, "uri": t.ComponentUri,',
        '            "is_assembly": bool(t.IsAssembly),',
        '            "is_system": bool(t.IsSystem),',
        '            "flow_group": None,',
        '            "product_property_count": len(t.ProductProperties),',
        '            "component_property_count": len(t.ComponentProperties)}',
        "    if t.FlowGroup is not None:",
        '        post["flow_group"] = t.FlowGroup.Name',
        "    rader.append(post)",
        '_svara({"component": k.Name, "behaviour": styrning.Name,',
        '        "product_types": rader, "antal": len(rader),',
        '        "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_product_types",
    "Produkttyperna som processregulatorn kanner: namn, vilken komponent-URI "
    "typen bygger pa, vilken flodesgrupp den ligger i och om den ar en "
    "sammansattning med stycklista. Anvand product_type_info for stycklistan.",
    "read",
    params({"component": dict(ARG_KOMPONENT, description=(
        "Komponenten som bar processregulatorn."))},
           ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Processregulatorns namn."},
             "product_types": {
                 "type": "array", "description": "Produkttyperna.",
                 "items": {"type": "object", "description": "En produkttyp.",
                           "properties": {
                               "product_type": {"type": "string", "description": "Typens namn."},
                               "uri": {"type": ["string", "null"], "description": "Komponent-URI typen bygger pa."},
                               "is_assembly": {"type": "boolean", "description": "Om typen ar en sammansattning."},
                               "is_system": {"type": "boolean", "description": "Om typen ar en av VC:s egna."},
                               "flow_group": {"type": ["string", "null"], "description": "Flodesgruppens namn."},
                               "product_property_count": {"type": "integer", "description": "Antal egenskaper pa produkten."},
                               "component_property_count": {"type": "integer", "description": "Antal egenskaper pa komponenten typen skapar."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "behaviour", "product_types", "antal", "avkortad"]),
    _Y_BETLISTA,
    _kod_list_product_types,
)


# ---- product_type_info ---------------------------------------------------

def _kod_product_type_info(argument):
    typ = lit(argument["product_type"])
    rader = _hamta_komponent(argument["component"])
    rader += [
        "styrning = None",
        "for b in k.Behaviours:",
        '    if "process_controller" in _slag(b):',
        "        styrning = b",
        "if styrning is None:",
        '    raise ValueError(k.Name + " bar ingen processregulator")',
        "chef = styrning.ProductTypeManager",
        "if chef is None:",
        '    raise ValueError(k.Name + " har en processregulator utan'
        ' produkttyphanterare")',
        "t = chef.findProductType(%s)" % typ,
        "if t is None:",
        '    _svara({"found": False, "component": k.Name, "product_type": %s,'
        % typ,
        '            "properties": [], "bom": [], "avkortad": False})',
        "else:",
        "    egenskaper = []",
        "    avkortad = False",
        "    for p in t.ProductProperties:",
    ]
    rader += tak("egenskaper", "        ")
    rader += [
        '        egenskaper.append({"name": p.Name, "value": _enkelt(p.Value)})',
        "    stycklista = []",
        '    if bool(t.IsAssembly) and hasattr(t, "AssemblySteps"):',
        "        for s in t.AssemblySteps:",
    ]
    rader += tak("stycklista", "            ")
    rader += [
        '            steg = {"step": s.Name, "parent": None,',
        '                    "children": len(s.ChildSteps)}',
        "            if s.ParentStep is not None:",
        '                steg["parent"] = s.ParentStep.Name',
        "            stycklista.append(steg)",
        '    _svara({"found": True, "component": k.Name,',
        '            "product_type": t.Name, "uri": t.ComponentUri,',
        '            "is_assembly": bool(t.IsAssembly),',
        '            "properties": egenskaper, "bom": stycklista,',
        '            "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "product_type_info",
    "En produkttyp i detalj: dess egna egenskaper och, om den ar en "
    "sammansattning, dess stycklista som sammansattningsstegen ser den. "
    "found=false ar ett giltigt svar for ett namn som inte finns.",
    "read",
    params({"component": dict(ARG_KOMPONENT, description=(
                "Komponenten som bar processregulatorn.")),
            "product_type": {"type": "string",
                             "description": ("Produkttypens namn, exakt som "
                                             "list_product_types lamnade det.")}},
           ["component", "product_type"]),
    returns({"found": {"type": "boolean", "description": "Om produkttypen fanns."},
             "component": {"type": "string", "description": "Komponenten."},
             "product_type": {"type": "string", "description": "Typens namn."},
             "uri": {"type": ["string", "null"], "description": "Komponent-URI typen bygger pa."},
             "is_assembly": {"type": "boolean", "description": "Om typen ar en sammansattning."},
             "properties": {"type": "array", "description": "Produktens egenskaper.",
                            "items": {"type": "object", "description": "En egenskap.",
                                      "properties": {
                                          "name": {"type": "string", "description": "Egenskapens namn."},
                                          "value": RET_VARDE}}},
             "bom": {"type": "array",
                     "description": "Stycklistan som sammansattningssteg, tom for en typ som inte ar en sammansattning.",
                     "items": {"type": "object", "description": "Ett sammansattningssteg.",
                               "properties": {
                                   "step": {"type": "string", "description": "Stegets namn."},
                                   "parent": {"type": ["string", "null"], "description": "Foraldrastegets namn."},
                                   "children": {"type": "integer", "description": "Antal understeg."}}}},
             "avkortad": RET_AVKORTAD},
            ["found", "component", "product_type", "properties", "bom",
             "avkortad"]),
    _Y_BETLISTA,
    _kod_product_type_info,
)


# ---- list_processes ------------------------------------------------------

def _kod_list_processes(argument):
    rader = _hamta_komponent(argument["component"])
    rader += ["rader = []", "avkortad = False", "for b in k.Behaviours:"]
    rader += tak("rader")
    rader += [
        '    if "process_executor" not in _slag(b):',
        "        continue",
        "    processer = []",
        "    for pr in b.Processes:",
        '        processer.append({"process": pr.Name,',
        '                          "description": pr.Description,',
        '                          "statements": len(pr.Statements)})',
        '    post = {"behaviour": b.Name, "enabled": bool(b.IsEnabled),',
        '            "looping": bool(b.IsLooping),',
        '            "current_statement": None,',
        '            "transport_node": None, "processes": processer}',
        "    if b.CurrentStatement is not None:",
        '        post["current_statement"] = b.CurrentStatement.Name',
        "    if b.TransportNode is not None:",
        '        post["transport_node"] = b.TransportNode.Name',
        "    rader.append(post)",
        '_svara({"component": k.Name, "executors": rader,',
        '        "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_processes",
    "Processerna en station kan utfora, i den ordning processexekveraren bar "
    "dem, med antal steg per process och vilket steg som kors just nu. "
    "Processernas TIDER ligger som parametrar pa stegen - las dem med "
    "list_process_statements.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "executors": {
                 "type": "array", "description": "Processexekverarna pa komponenten.",
                 "items": {"type": "object", "description": "En processexekverare.",
                           "properties": {
                               "behaviour": {"type": "string", "description": "Beteendets namn."},
                               "enabled": {"type": "boolean", "description": "Om exekveraren ar pa."},
                               "looping": {"type": "boolean", "description": "Om programmet borjar om."},
                               "current_statement": {"type": ["string", "null"], "description": "Steget som kors just nu, null nar inget kors."},
                               "transport_node": {"type": ["string", "null"], "description": "Transportnoden exekveraren hor till."},
                               "processes": {"type": "array", "description": "Processerna i ordning.",
                                             "items": {"type": "object", "description": "En process.",
                                                       "properties": {
                                                           "process": {"type": "string", "description": "Processens namn."},
                                                           "description": {"type": ["string", "null"], "description": "Processens beskrivning."},
                                                           "statements": {"type": "integer", "description": "Antal steg i processen."}}}}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "executors", "antal", "avkortad"]),
    _Y_BETLISTA,
    _kod_list_processes,
)


# ---- list_process_statements ---------------------------------------------

def _kod_list_process_statements(argument):
    process = lit(argument["process"])
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += _krav_slag("process_executor")
    rader += [
        "vald = None",
        "for pr in b.Processes:",
        "    if pr.Name == %s:" % process,
        "        vald = pr",
        "if vald is None:",
        '    raise ValueError(b.Name + " har ingen process som heter " + %s)'
        % process,
        "rader = []",
        "avkortad = False",
        "for s in vald.Statements:",
    ]
    rader += tak("rader")
    rader += [
        "    parametrar = []",
        "    for p in s.Properties:",
        '        parametrar.append({"name": p.Name, "value": _enkelt(p.Value)})',
        '    rader.append({"statement": s.Name, "type": _enkelt(s.Type),',
        '                  "parameters": parametrar})',
        '_svara({"component": k.Name, "behaviour": b.Name,',
        '        "process": vald.Name, "statements": rader,',
        '        "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "list_process_statements",
    "Stegen i EN process, i ordning, med varje stegs parametrar. Har ligger "
    "processtiderna och resursbehoven: VC bar dem som parametrar pa steget, "
    "inte som fasta API-varden, sa de kommer med sina egna namn och lamnas "
    "otolkade.",
    "read",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE,
            "process": {"type": "string",
                        "description": ("Processens namn, exakt som "
                                        "list_processes lamnade det.")}},
           ["component", "behaviour", "process"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Processexekveraren."},
             "process": {"type": "string", "description": "Processens namn."},
             "statements": {
                 "type": "array", "description": "Stegen i ordning.",
                 "items": {"type": "object", "description": "Ett steg i processen.",
                           "properties": {
                               "statement": {"type": "string", "description": "Stegets namn."},
                               "type": {"type": ["string", "number", "integer", "null"],
                                        "description": "VC:s upprakningsvarde for stegets slag."},
                               "parameters": {"type": "array", "description": "Stegets parametrar, dar processtiden ligger.",
                                              "items": {"type": "object", "description": "En parameter.",
                                                        "properties": {
                                                            "name": {"type": "string", "description": "Parameterns namn."},
                                                            "value": RET_VARDE}}}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["component", "behaviour", "process", "statements", "antal",
             "avkortad"]),
    _Y_BET,
    _kod_list_process_statements,
)


# ---- station_statistics --------------------------------------------------

def _rader_stationspost(indrag):
    """Raderna som bygger EN STATION-post ur ett statistikbeteende.

    Faltnamnen ar valda mot ogats grammatik i oga_kontrakt.py:
        STATION <namn> in=.. out=.. avg=..s min=..s max=..s
    in/out/avg_s/min_s/max_s gar rakt in i den raden. Ingen omraekning, ingen
    omtolkning: raknar nagon om ett av talen har har ogat och grinden tva
    olika storheter.
    """
    return [
        '%srader.append({"station": k.Name, "behaviour": b.Name,' % indrag,
        '%s              "in": b.ComponentsArrived,' % indrag,
        '%s              "out": b.ComponentsDeparted,' % indrag,
        '%s              "avg_s": b.ComponentsAverageTime,' % indrag,
        '%s              "min_s": b.ComponentMinTime,' % indrag,
        '%s              "max_s": b.ComponentMaxTime,' % indrag,
        '%s              "current": b.ComponentsCurrent,' % indrag,
        '%s              "min_count": b.ComponentMinCount,' % indrag,
        '%s              "max_count": b.ComponentMaxCount})' % indrag,
    ]


def _kod_station_statistics(argument):
    rader = _hamta_komponent(argument["component"])
    rader += ["rader = []", "avkortad = False", "for b in k.Behaviours:"]
    rader += tak("rader")
    rader += [
        '    if "statistics" not in _slag(b):',
        "        continue",
    ]
    rader += _rader_stationspost("    ")
    rader += [
        '_svara({"component": k.Name, "stations": rader,',
        '        "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_RETURNS_STATIONER = returns(
    {"component": {"type": "string", "description": "Komponenten som lastes."},
     "stations": {"type": "array",
                  "description": "En post per statistikbeteende pa komponenten.",
                  "items": _STATIONSPOST},
     "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
    ["component", "stations", "antal", "avkortad"])


_lagg(
    "station_statistics",
    "Genomstromningen for EN station: antal in, antal ut, medeltid, kortaste "
    "och langsta tid, plus antal inne nu och de samtidiga ytterlagena. "
    "Falten ar namngivna sa att de gar rakt in i ogats STATION-rad utan att "
    "nagot behover raknas om.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    _RETURNS_STATIONER,
    _Y_BETLISTA,
    _kod_station_statistics,
)


# ---- layout_statistics ---------------------------------------------------

def _kod_layout_statistics(argument):
    rader = [
        "rader = []",
        "avkortad = False",
        "for k in getApplication().Components:",
        "    if avkortad:",
        "        break",
        "    for b in k.Behaviours:",
    ]
    rader += tak("rader", "        ")
    rader += [
        '        if "statistics" not in _slag(b):',
        "            continue",
    ]
    if "min_arrived" in argument:
        rader += [
            "        if b.ComponentsArrived < %d:" % argument["min_arrived"],
            "            continue",
        ]
    rader += _rader_stationspost("        ")
    rader += [
        '_svara({"stations": rader, "antal": len(rader),'
        ' "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "layout_statistics",
    "Genomstromningen for HELA layouten, en post per station. Det ar den "
    "billigaste bilden av var flaskhalsen sitter, och samma falt som "
    "station_statistics sa att de gar rakt in i ogats STATION-rader. Anvand "
    "min_arrived for att stanga ute stationer som aldrig sag nagon produkt.",
    "read",
    params({"min_arrived": {
        "type": "integer",
        "description": ("Ta bara med stationer dar minst sa manga produkter "
                        "kommit in. Utelamnad tar med alla, aven de tomma.")}}),
    returns({"stations": {"type": "array",
                          "description": "En post per statistikbeteende i layouten.",
                          "items": _STATIONSPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["stations", "antal", "avkortad"]),
    ("app.Components", "comp.Name", "comp.Behaviours"),
    _kod_layout_statistics,
)


# ---- station_state_times -------------------------------------------------

def _kod_station_state_times(argument):
    rader = _hamta_komponent(argument["component"])
    rader += _hamta_beteende(argument["behaviour"])
    rader += _krav_slag("statistics")
    rader += [
        # States ar deklarerad "unknown" i den matta ytan och beskrivs som en
        # mappning tillstand -> systemtillstand. Vad ELEMENTEN ar gar inte att
        # avgora ur kallan, sa de lamnas som VC:s egen text och tolkas inte.
        # Det ar upptackten; matningen sker sedan med de namn anroparen valjer.
        "raa = []",
        "avkortad = False",
        "for st in b.States:",
    ]
    rader += tak("raa")
    rader += [
        "    raa.append(repr(st))",
        "rader = []",
    ]
    if "states" in argument:
        rader += [
            "for namn in %s:" % lit(list(argument["states"])),
            '    rader.append({"state": namn,',
            "                  \"percentage\": b.getPercentage(namn),",
            '                  "seconds": b.getTime(namn)})',
        ]
    rader += [
        '_svara({"component": k.Name, "behaviour": b.Name,',
        '        "states_raw": raa, "times": rader, "antal": len(rader),',
        '        "avkortad": avkortad})',
    ]
    return bygg(["_svara"], _lokala(["_slag"]) + rader)


_lagg(
    "station_state_times",
    "Hur lange en station stod i vart tillstand - ledig, upptagen, blockerad, "
    "svalter, trasig. Anropa FORST utan states: da kommer bara states_raw, "
    "VC:s egen text for stationens definierade tillstand, otolkad. Valj "
    "tillstandsnamnen ur den och anropa igen med states for att fa procent och "
    "sekunder per namn. Skalet star i koden: den matta API-ytan deklarerar "
    "States som okand typ, sa vad elementen ar gar inte att avgora i forvag - "
    "och en gissning har hade blivit en siffra utan harkomst.",
    "read",
    params({"component": ARG_KOMPONENT,
            "behaviour": dict(ARG_BETEENDE, description=(
                "Statistikbeteendets namn. Hitta det med "
                "list_transport_behaviours och kind=statistics.")),
            "states": {"type": "array", "minItems": 1,
                       "description": ("Tillstandsnamnen att mata, valda ur "
                                       "states_raw i ett tidigare anrop."),
                       "items": {"type": "string",
                                 "description": "Ett tillstandsnamn."}}},
           ["component", "behaviour"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Statistikbeteendet."},
             "states_raw": {"type": "array",
                            "description": ("VC:s egen text for stationens "
                                            "definierade tillstand. Otolkad."),
                            "items": {"type": "string",
                                      "description": "Ett tillstand som VC beskriver det."}},
             "times": {"type": "array",
                       "description": "Tid per efterfragat tillstand. Tom nar states inte gavs.",
                       "items": {"type": "object", "description": "Ett tillstands tid.",
                                 "properties": {
                                     "state": {"type": "string", "description": "Tillstandets namn."},
                                     "percentage": {"type": "number", "description": "Andel av total tid, i procent som VC raknar den."},
                                     "seconds": {"type": "number", "description": "Ackumulerad tid i sekunder."}}}},
             "antal": RET_ANTAL,
             "avkortad": dict(RET_AVKORTAD, description=(
                 "True om states_raw klipptes vid taket. Da ar listan over "
                 "stationens tillstand ofullstandig."))},
            ["component", "behaviour", "states_raw", "times", "antal",
             "avkortad"]),
    _Y_BET,
    _kod_station_state_times,
)
