# -*- coding: utf-8 -*-
"""Domanen knowledge: uppslag i VC:s eget API (45_verktyg.md, 46_kunskapsindex.md).

Alla verktyg har ar DATA: de kor i tjansten och gar aldrig via bryggan. De
svarar alltsa aven nar VC inte ar igang, vilket ar poangen - modellen ska
kunna sla upp ett namn INNAN den skriver koden som anvander det.

Kallan ar det byggda indexet i vc_assist_svc/api_index.py, som laser
docs/referens/vc_api/ (vc_python_api.json, api.xml, constants.xml,
helpers.xml). MATT vid bygget: 3444 symboler - 204 typer, 966 metoder,
1159 egenskaper, 175 handelser, 709 konstanter, 8 vcHelpers-moduler med
223 medlemmar. Indexet byggs har en gang vid import (matt: 0,07 s).

46_kunskapsindex.md ger tre frageformer, och alla tre finns har:

    lookup_api     exakt namn        -> signatur, typ, atkomst, beskrivning
    search_api     fri text          -> topp N symboler med relevans
    type_surface   ett typnamn       -> alla metoder, egenskaper och handelser

plus lookup_helper ur 45_verktyg.md:s knowledge-tabell, over de atta
vcHelpers-modulerna.

HARKOMST PER SVAR. Varje symbol bar Symbol.harkomst(): vilken agande typ,
vilken KALLFIL namnet lastes ur, vilken VC-version, och - nar signaturen
kommer fran en annan fil an namnet - vilken fil signaturen kom ur. Ingen rad
lamnar verktyget utan den. Varje svar bar dessutom api_index.INSTRUKTION
ordagrant: "Anvand namnet exakt som det star. Omformulera det inte."

ETT PAHITTAT NAMN GER TOMT SVAR (46_kunskapsindex.md, punkt 3). found=false,
och forslagen som foljer med ar VERKLIGA namn ur indexet inom det matta
avstandstaket. Verktyget gissar aldrig fram en signatur.

lookup_pattern ur 45_verktyg.md ar INTE byggt har, och det ar inte en lucka
som ska fyllas med en stubbe. Monsterlagret skordas ur korningar som passerat
HELA grindkedjan och fatt guld (46_kunskapsindex.md: "endast guld skordas").
Noll sadana korningar finns, sa lagret ar tomt, och ett verktyg som bara kan
svara "hittade inget" mater ingenting. Det byggs nar det finns guld att skorda.
"""
from __future__ import annotations

from ..api_index import (FORSLAG_AVSTAND_TAK, INSTRUKTION, MAX_FORSLAG,
                         VC_VERSION_STANDARD, bygg_index)
from .bas import SINCE, TIMEOUT_MS, params, returns
from .register import registrera
from .schema import Verktyg

DOMAN = "knowledge"

# Byggs en gang vid import. Handlarna ar darmed rena uppslag utan I/O.
INDEX = bygg_index()
STATISTIK = INDEX.statistik()

# De atta vcHelpers-modulerna, ur indexet och inte ur en handskriven lista.
# De ligger som enum i lookup_helper: da avvisar argumentvalideringen ett
# uppfunnet modulnamn INNAN handlaren kors, och modellen ser samtidigt de
# verkliga namnen i verktygsschemat. Anti-hallucinationen blir mekanisk i
# stallet for en tillsagelse (I9).
HJALPMODULER = tuple(sorted(INDEX.hjalpmoduler))

# Default- och maxantal traffar ur search_api.
#
# MATT over 19 realistiska fragor mot indexets 3444 symboler (distance,
# moveTo, robot, signal, collision, camera, property, transform, matrix,
# interface, statistics, joint, simulation, component, target, conveyor,
# grip, "frame grab", bounding): antalet traffar dar frasen star i NAMNET
# (rangerna exakt, exakt_skiftlagesokant, prefix och delstrang_namn) har
# median 21 och spannet 0 till 119. Hela traffmangden, beskrivningstraffar
# inraknade, gar upp till 307.
#
# 20 platser tacker darfor hela namntraffhuvudet for 12 av de 19 fragorna.
# For de ovriga star antal_totalt och avkortad i svaret, sa en for kort lista
# SYNS i stallet for att tyst forsvinna (I3). Taket 100 tacker 18 av 19 och
# hindrar att ett enda anrop drar in tre hundra rader i turen.
STANDARD_TRAFFAR = 20
MAX_TRAFFAR = 100


# ---- registrering --------------------------------------------------------

# bas.laggare() ger mode="codegen"; den har domanen ar data, sa laggaren star
# har. effect ar INTE en parameter: alla kunskapsverktyg laser, och ett
# data-verktyg som skriver avvisas anda av schemat (I12).
#
# KRAVER for ett data-verktyg. Schemat kraver minst en yta ur formaga.YTOR
# och formagegrinden slar av verktyget nar ytan saknas. Ett kunskapsverktyg
# ror ingen VC-yta alls. Vi deklarerar darfor den yta svaret ar TILL FOR:
# app.getApplicationPath. Skalet ar 46_kunskapsindex.md:s eget krav pa
# versionsmedvetenhet - "fragor filtreras pa den version som kors, avlast ur
# installationens egen sokvag". Utan den ytan vet vi inte vilken VC:s API
# svaret beskriver, och da ar ett svar med exakt signatur ett lofte vi inte
# kan halla. Foljden ar uttalad: utan formagerapport fran bryggan ar ocksa
# kunskapsverktygen avslagna (I3 fail-closed), med ytan namngiven i skalet.
KRAVER = ("app.getApplicationPath",)


def _lagg(namn, beskrivning, parameters, returns_, handlare):
    return registrera(
        Verktyg(namn=namn, beskrivning=beskrivning, mode="data", effect="read",
                parameters=parameters, returns=returns_, since=SINCE,
                kraver=KRAVER, doman=DOMAN,
                # timeout_ms ar inert pa data-vagen: utforaren skickar den
                # bara till bryggan for kodgenererande verktyg. Talet halls
                # anda pa bas.TIMEOUT_MS sa att ingen andra, tystare grans
                # uppstar i tjansten.
                timeout_ms=TIMEOUT_MS),
        handlare)


# ---- gemensamma schemabitar ---------------------------------------------

_SYMBOL = {
    "type": "object",
    "description": "En symbol ur API-indexet, med sin harkomst.",
    "properties": {
        "sort": {"type": "string",
                 "description": "typ, metod, egenskap, handelse eller konstant."},
        "type_name": {"type": "string",
                      "description": "Agande typ. Tom strang for konstanter och typer."},
        "name": {"type": "string", "description": "Namnet. Anvand det exakt."},
        "full_name": {"type": "string", "description": "Typ.namn, eller bara namnet."},
        "signature": {"type": ["string", "null"],
                      "description": "Parameterlistan ur api.xml, null nar kallan saknar den."},
        "value_type": {"type": ["string", "null"],
                       "description": "Retur- eller egenskapstyp, null nar kallan saknar den."},
        "access": {"type": ["string", "null"],
                   "description": "R, RW eller W for egenskaper. null for ovrigt."},
        "description": {"type": "string",
                        "description": "Kallans egen beskrivning, tom strang nar den saknas."},
        "harkomst": {"type": "string",
                     "description": "Agande typ, kallfil och VC-version namnet kommer ur."},
        "vc_version": {"type": "string", "description": "VC-versionen symbolen galler."},
    },
    "required": ["sort", "type_name", "name", "full_name", "signature",
                 "value_type", "access", "description", "harkomst", "vc_version"],
}

_FORSLAG = {
    "type": "array",
    "description": ("Verkliga namn ur indexet nara det du fragade efter. "
                    "Tom lista betyder att inget kant namn ligger nara nog - "
                    "da ar tomt svar det arliga svaret."),
    "items": {
        "type": "object",
        "description": "Ett verkligt namn och dess redigeringsavstand.",
        "properties": {
            "name": {"type": "string", "description": "Ett namn som FINNS i indexet."},
            "avstand": {"type": "integer",
                        "description": "Redigeringsavstand till det du fragade efter."},
        },
        "required": ["name", "avstand"],
    },
}

_RET_INSTRUKTION = {
    "type": "string",
    "description": "Instruktionen som varje uppslagssvar bar (46_kunskapsindex.md).",
}
_RET_INDEX = {
    "type": "object",
    "description": "Vilket index svaret kommer ur.",
    "properties": {
        "vc_version": {"type": "string", "description": "VC-versionen indexet ar byggt for."},
        "symboler_totalt": {"type": "integer", "description": "Antal symboler i indexet."},
        "typer": {"type": "integer", "description": "Antal typer."},
        "metoder": {"type": "integer", "description": "Antal metoder."},
        "egenskaper": {"type": "integer", "description": "Antal egenskaper."},
        "kallor": {"type": "array", "description": "Filerna indexet ar byggt ur.",
                   "items": {"type": "string", "description": "En kallfil."}},
    },
    "required": ["vc_version", "symboler_totalt", "typer", "metoder",
                 "egenskaper", "kallor"],
}

_KALLOR = ("vc_python_api.json", "api.xml", "constants.xml", "helpers.xml")


def _index_ut():
    return {"vc_version": VC_VERSION_STANDARD,
            "symboler_totalt": STATISTIK["symboler_totalt"],
            "typer": STATISTIK["typer"],
            "metoder": STATISTIK["metoder"],
            "egenskaper": STATISTIK["egenskaper"],
            "kallor": list(_KALLOR)}


def _symbol_ut(s):
    return {"sort": s.sort, "type_name": s.typ_namn, "name": s.namn,
            "full_name": s.fullnamn, "signature": s.signatur,
            "value_type": s.vardetyp, "access": s.atkomst,
            "description": s.beskrivning, "harkomst": s.harkomst(),
            "vc_version": s.vc_version}


def _forslag_ut(par):
    return [{"name": namn, "avstand": d} for namn, d in par]


# ---- lookup_api ----------------------------------------------------------

def _lookup_api(argument):
    namn = argument["name"].strip()
    symboler = INDEX.slag_upp(namn)
    typ_namn = namn.rpartition(".")[0] or None
    kort = namn.rpartition(".")[2]
    # Forslag bara vid bomskott, och bara verkliga namn. Trosklarna ar
    # api_index:s egna, matta over dess provsamling om 29 kodstrangar:
    # hogst MAX_FORSLAG platser, hogst FORSLAG_AVSTAND_TAK redigeringar bort.
    # De ar INTE omkalibrerade har - samma population, samma namn.
    forslag = [] if symboler else INDEX.narmaste(
        kort, typ_namn if typ_namn in INDEX.typer else None,
        antal=MAX_FORSLAG, tak=FORSLAG_AVSTAND_TAK)
    return {
        "found": bool(symboler),
        "name": namn,
        "symbols": [_symbol_ut(s) for s in symboler],
        "antal": len(symboler),
        "svar": "\n\n".join(s.svar() for s in symboler),
        "forslag": _forslag_ut(forslag),
        "instruktion": INSTRUKTION,
        "index": _index_ut(),
    }


_lagg(
    "lookup_api",
    "Slar upp ett EXAKT namn i VC:s Python-API och ger signatur, typ, atkomst "
    "och beskrivning, med den kallfil namnet kommer ur. Tar bade "
    "vcRobotController.moveTo och ett bart namn som moveTo. Ett namn som inte "
    "finns ger found=false och verkliga naraliggande namn - aldrig en gissad "
    "signatur. Sla upp INNAN du skriver kod som anvander namnet.",
    params({"name": {"type": "string",
                     "description": "Namnet, som Typ.medlem eller bara medlem."}},
           ["name"]),
    returns({
        "found": {"type": "boolean", "description": "Om namnet fanns i indexet."},
        "name": {"type": "string", "description": "Namnet som slogs upp."},
        "symbols": {"type": "array", "description": "Symbolerna med det namnet.",
                    "items": _SYMBOL},
        "antal": {"type": "integer", "description": "Antal symboler i svaret."},
        "svar": {"type": "string",
                 "description": "Fardig svarstext per symbol, med harkomst och instruktion."},
        "forslag": _FORSLAG,
        "instruktion": _RET_INSTRUKTION,
        "index": _RET_INDEX,
    }, ["found", "name", "symbols", "antal", "svar", "forslag", "instruktion",
        "index"]),
    _lookup_api,
)


# ---- search_api ----------------------------------------------------------

def _search_api(argument):
    fras = argument["query"]
    # Schemat kan inte uttrycka ett talintervall - schema.TYPER bar inga
    # min/max for tal, bara enum och listlangder. Taket satts darfor har, och
    # utfallet syns i svaret: antal, antal_totalt och avkortad sager exakt hur
    # manga traffar som fanns och hur manga som kom med.
    grans = max(1, min(int(argument["limit"]), MAX_TRAFFAR))
    alla = INDEX.sok(fras)
    traffar = alla[:grans]
    return {
        "query": fras,
        "traffar": [dict(_symbol_ut(t.symbol), rang=t.rang) for t in traffar],
        "antal": len(traffar),
        "antal_totalt": len(alla),
        "avkortad": len(alla) > len(traffar),
        "instruktion": INSTRUKTION,
        "index": _index_ut(),
    }


_TRAFF = dict(_SYMBOL)
_TRAFF["description"] = "En soktraff: symbolen, plus hur den traffades."
_TRAFF["properties"] = dict(_SYMBOL["properties"])
_TRAFF["properties"]["rang"] = {
    "type": "string",
    "description": ("Hur den traffades: exakt, exakt_skiftlagesokant, prefix, "
                    "delstrang_namn, delstrang_typ eller delstrang_beskrivning."),
}
_TRAFF["required"] = list(_SYMBOL["required"]) + ["rang"]

_lagg(
    "search_api",
    "Fritextsokning i VC:s Python-API nar du inte vet vad namnet heter. "
    "Traffarna kommer med basta rang forst: exakt namn fore prefix fore "
    "delstrang i namn, typnamn och beskrivning. Svaret sager hur manga "
    "traffar som fanns totalt, sa du ser nar listan klipptes.",
    params({
        "query": {"type": "string",
                  "description": "Fri text, till exempel distance eller collision."},
        "limit": {"type": "integer", "default": STANDARD_TRAFFAR,
                  "description": ("Antal traffar, 1 till %d. Standard %d."
                                  % (MAX_TRAFFAR, STANDARD_TRAFFAR))},
    }, ["query"]),
    returns({
        "query": {"type": "string", "description": "Frasen som soktes."},
        "traffar": {"type": "array", "description": "Traffarna, basta rang forst.",
                    "items": _TRAFF},
        "antal": {"type": "integer", "description": "Antal traffar i svaret."},
        "antal_totalt": {"type": "integer",
                         "description": "Antal traffar fore klippet."},
        "avkortad": {"type": "boolean",
                     "description": "True om listan klipptes. Da ar svaret ofullstandigt."},
        "instruktion": _RET_INSTRUKTION,
        "index": _RET_INDEX,
    }, ["query", "traffar", "antal", "antal_totalt", "avkortad", "instruktion",
        "index"]),
    _search_api,
)


# ---- type_surface --------------------------------------------------------

def _type_surface(argument):
    typ_namn = argument["type_name"].strip()
    if typ_namn not in INDEX.typer:
        return {
            "found": False,
            "type_name": typ_namn,
            "arvskedja": [],
            "medlemmar": [],
            "antal": 0,
            "forslag": _forslag_ut(INDEX.narmaste(
                typ_namn, None, antal=MAX_FORSLAG, tak=FORSLAG_AVSTAND_TAK)),
            "instruktion": INSTRUKTION,
            "index": _index_ut(),
        }
    yta = INDEX.typytan(typ_namn)
    medlemmar = []
    for namn in sorted(yta):
        for s in yta[namn]:
            medlemmar.append(_symbol_ut(s))
    medlemmar.sort(key=lambda m: (m["sort"], m["name"], m["type_name"]))
    return {
        "found": True,
        "type_name": typ_namn,
        # Typen sjalv forst, sedan foraldrarna. En medlem vars type_name inte
        # ar typen sjalv ar arvd fran den typ som star dar.
        "arvskedja": INDEX.arvskedja(typ_namn),
        "medlemmar": medlemmar,
        "antal": len(medlemmar),
        "forslag": [],
        "instruktion": INSTRUKTION,
        "index": _index_ut(),
    }


_lagg(
    "type_surface",
    "Hela ytan pa en VC-typ: alla metoder, egenskaper och handelser, arvet "
    "inraknat, med den typ var medlem sitter pa. Anvand den nar du har ett "
    "objekt och behover veta vad du far gora med det. Okant typnamn ger "
    "found=false och verkliga naraliggande typnamn.",
    params({"type_name": {"type": "string",
                          "description": "Typens namn, till exempel vcComponent."}},
           ["type_name"]),
    returns({
        "found": {"type": "boolean", "description": "Om typen fanns i indexet."},
        "type_name": {"type": "string", "description": "Typen som slogs upp."},
        "arvskedja": {"type": "array",
                      "description": "Typen sjalv forst, sedan dess foraldrar.",
                      "items": {"type": "string", "description": "Ett typnamn."}},
        "medlemmar": {"type": "array", "description": "Alla medlemmar pa ytan.",
                      "items": _SYMBOL},
        "antal": {"type": "integer", "description": "Antal medlemmar."},
        "forslag": _FORSLAG,
        "instruktion": _RET_INSTRUKTION,
        "index": _RET_INDEX,
    }, ["found", "type_name", "arvskedja", "medlemmar", "antal", "forslag",
        "instruktion", "index"]),
    _type_surface,
)


# ---- lookup_helper -------------------------------------------------------

def _lookup_helper(argument):
    modul = argument["module"]
    yta = INDEX.typytan(modul)
    medlemmar = []
    for namn in sorted(yta):
        for s in yta[namn]:
            medlemmar.append(_symbol_ut(s))
    medlemmar.sort(key=lambda m: (m["sort"], m["name"]))
    return {
        "module": modul,
        "moduler": list(HJALPMODULER),
        "medlemmar": medlemmar,
        "antal": len(medlemmar),
        "instruktion": INSTRUKTION,
        "index": _index_ut(),
    }


_lagg(
    "lookup_helper",
    "Innehallet i en vcHelpers-modul: funktionerna VC sjalv levererar ovanpa "
    "rena API:t. Modulnamnet valjs ur listan i schemat, sa ett uppfunnet "
    "modulnamn avvisas innan verktyget kors.",
    params({"module": {"type": "string", "enum": list(HJALPMODULER),
                       "description": "Vilken vcHelpers-modul som ska listas."}},
           ["module"]),
    returns({
        "module": {"type": "string", "description": "Modulen som slogs upp."},
        "moduler": {"type": "array",
                    "description": "Alla vcHelpers-moduler som finns i indexet.",
                    "items": {"type": "string", "description": "Ett modulnamn."}},
        "medlemmar": {"type": "array", "description": "Modulens medlemmar.",
                      "items": _SYMBOL},
        "antal": {"type": "integer", "description": "Antal medlemmar."},
        "instruktion": _RET_INSTRUKTION,
        "index": _RET_INDEX,
    }, ["module", "moduler", "medlemmar", "antal", "instruktion", "index"]),
    _lookup_helper,
)
