# -*- coding: utf-8 -*-
"""Domanen selection: vad anvandaren PEKAR PA, och vad scenen BESTAR AV.

Tva verktyg, bada lasande, och de svarar pa de tva fragor som gor pekord
mojliga att losa ut:

    get_selection    vad ar markerat just nu
    scene_snapshot   vad finns i scenen, vilken SORT var sak ar, och vad av
                     det som ar markerat

Registret bar 122 verktyg och hade INGET som rorde markering. Ytan fanns hela
tiden - den var bara aldrig kopplad.

VAD SOM AR MATT, OCH VAD SOM DARFOR INTE GISSAS (M-171, korande VC 4.10
under Wine, DISPLAY=:99, alltsa utan synlig vy):

  * ``app.SelectionManager`` finns och bar FYRA anrop: ``clear``,
    ``getSelection``, ``setSelection`` och ``setGeometrySelectEnabled``. Det
    sista star inte i api.xml.
  * De deprekerade vagarna ar DODA headless: ``app.CurrentSelection`` och
    ``app.Selections`` ar bada ``None``. VC skriver sjalv i sitt Output-
    fonster att man ska anvanda SelectionManager. Darfor kraver verktygen
    ``app.SelectionManager`` och inte ``app.getSelection``.
  * Markering FUNGERAR headless: setSelection foljt av getSelection ger
    tillbaka samma komponenter, och GUI:ts egen egenskapsruta foljer med.
    GUI och API delar alltsa ETT markeringslager - det ar det som gor att
    verktyget laser samma sak som anvandaren klickade pa.
  * ``VC_SELECTION_COMPONENT`` ar 1, och konstanten ligger i ``vcScript``.
  * Ett beteendes ``Type`` ar EXAKT filformatets markorstrang:
    ``VC_ONEWAYPATH == 'rOneWayPath'``. Katalogens familjemarkorer galler
    darfor OFORANDRADE mot en levande scen, utan oversattningstabell.
  * Tva lasningar av samma komponent ar INTE samma objekt (``is`` ar falskt),
    men de ar lika (``==``) och hashar lika. Markeringen paras darfor ihop med
    scenen genom en ordbok pa objektet - ``is`` hade gett en flagga som alltid
    var falsk, tyst.
  * Komponentnamn ar INTE unika: provscenen bar fyra ``ST8_Mall`` och tva
    ``Name``, och ``VCID`` var tom for alla sessionsbyggda. Namnet duger
    darfor inte som identitet, och bilden bar dubbletterna som dubbletter i
    stallet for att slaa ihop dem tyst.

SORTEN LASES UR STRUKTUREN, ALDRIG UR NAMNET

M-69 matte vad namnhardledning kostar: katalognamnet "Robots" ger 1736
komponenter, strukturen 2202. I provscenen finns samma fel att gora - en
komponent som HETER ``Robot`` bar bara en boolsignal och ingen robotstyrning.
Markorerna importeras darfor ur ``datablad.FAMILJEMARKORER`` och skrivs in i
mallen som literaler. En tredje kopia av listan hade varit precis den skuld
S12 handlar om.

En komponent utan markor far sorten "" - inte "ovrig". Skillnaden ar
katalogindexets egen och den ar riktig: tomt betyder "gick inte att avgora",
medan "ovrig" later som ett svar.
"""
from __future__ import annotations

from ..datablad import FAMILJEMARKORER
from .bas import RET_ANTAL, RET_AVKORTAD, laggare, params, returns, tak
from .fel import Schemafel
from .kodmall import bygg, lit
from .register import REGISTER

DOMAN = "selection"
_lagg = laggare(DOMAN)

# Ytorna verktygen star och faller med. app.SelectionManager ar MATT (M-171)
# som den enda som svarar headless; comp.Behaviours ar den som bar sorten.
_YTOR = ("app.SelectionManager", "app.Components", "comp.Behaviours",
         "comp.Name")

# Markorerna som literal, i den form mallen skriver in i VC-koden:
# [[sort, [markor, ...]], ...]. Listan HARLEDS ur datablad.FAMILJEMARKORER
# och skrivs aldrig av - den som doper om en markor dar andrar bada stallen.
_MARKORER = [[sort, list(markorer)] for sort, markorer in FAMILJEMARKORER]

_MARKERINGSPOST = {
    "type": "object",
    "description": "En markerad komponent.",
    "properties": {
        "name": {"type": "string", "description": "Komponentens namn i scenen."},
        "sort": {
            "type": "string",
            "description": ("Komponentens familj, last ur dess beteenden: "
                            "%s. Tom strang betyder att sorten INTE gick att "
                            "avgora - den gissas aldrig ur namnet."
                            % ", ".join(s for s, _m in FAMILJEMARKORER)),
        },
    },
}
_KOMPONENTPOST = {
    "type": "object",
    "description": "En komponent i scenen, med sin sort och sin markering.",
    "properties": {
        "name": _MARKERINGSPOST["properties"]["name"],
        "sort": _MARKERINGSPOST["properties"]["sort"],
        "selected": {"type": "boolean",
                     "description": "True om anvandaren har markerat den."},
    },
}


# ---- den gemensamma mallbiten -------------------------------------------

def _rader_sort():
    """Raderna som laser sorten ur beteendena. Samma kod i bada verktygen.

    Skriven som EN funktion och inte kopierad: de tva verktygen maste svara
    samma sort om samma komponent, annars kan ett pekord losas ut mot en sort
    som det andra verktyget inte kanner igen.
    """
    return [
        "MARKORER = %s" % lit(_MARKORER),
        "def _sort(k):",
        "    typer = {}",
        "    for b in k.Behaviours:",
        "        typer[b.Type] = True",
        "    for post in MARKORER:",
        "        for m in post[1]:",
        "            if m in typer:",
        "                return post[0]",
        # Tom strang, aldrig "ovrig": den som far tomt vet att fragan inte
        # gick att besvara (katalogindex._familj, samma val och samma skal).
        '    return ""',
    ]


def _rader_markerade():
    """Raderna som bygger uppslaget over vad som ar markerat.

    Ordboken nycklas pa KOMPONENTOBJEKTET och inte pa namnet. MATT (M-171):
    namnen ar inte unika - provscenen bar fyra ST8_Mall - och `is` ar falskt
    mellan tva lasningar medan `==` och hash haller.
    """
    return [
        "markerade = {}",
        "valda = _app().SelectionManager.getSelection(",
        "    vcScript.VC_SELECTION_COMPONENT)",
        "if valda:",
        "    for o in valda:",
        "        markerade[o] = True",
    ]


# ---- get_selection -------------------------------------------------------

def _kod_get_selection(argument):
    rader = _rader_sort()
    rader += _rader_markerade()
    rader += [
        "rader = []",
        "avkortad = False",
        # Gar genom app.Components och inte genom markeringslistan, sa att
        # ordningen blir SCENENS och sorten kommer ur samma pass som
        # scene_snapshot anvander.
        "for k in _app().Components:",
        "    if k not in markerade:",
        "        continue",
    ]
    rader += tak("rader")
    rader += [
        '    rader.append({"name": k.Name, "sort": _sort(k)})',
        '_svara({"selected": rader, "antal": len(rader),'
        ' "avkortad": avkortad})',
    ]
    return bygg(["_app", "_svara"], rader, importer=("vcScript",))


_lagg(
    "get_selection",
    "Listar de komponenter anvandaren har MARKERAT i Visual Components, med "
    "varje komponents sort. Anvand den nar meningen bar ett pekord - 'det "
    "dar gripdonet', 'den har linan', 'de tva' - i stallet for att fraga "
    "vilken komponent som menas. En tom lista ar ett giltigt svar och betyder "
    "att ingenting ar markerat; det ar inte ett fel, och det far aldrig "
    "tolkas som ett godkannande av ett val du gjort sjalv.",
    "read",
    params({}),
    returns({"selected": {"type": "array", "description": "De markerade komponenterna.",
                          "items": _MARKERINGSPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["selected", "antal", "avkortad"]),
    _YTOR,
    _kod_get_selection,
)


# ---- scene_snapshot ------------------------------------------------------

def _kod_scene_snapshot(argument):
    rader = _rader_sort()
    rader += _rader_markerade()
    rader += [
        "rader = []",
        "avkortad = False",
        "n_markerade = 0",
        "for k in _app().Components:",
    ]
    rader += tak("rader")
    rader += [
        "    vald = k in markerade",
        "    if vald:",
        "        n_markerade = n_markerade + 1",
        '    rader.append({"name": k.Name, "sort": _sort(k),'
        ' "selected": vald})',
        '_svara({"components": rader, "antal": len(rader),'
        ' "markerade": n_markerade, "avkortad": avkortad})',
    ]
    return bygg(["_app", "_svara"], rader, importer=("vcScript",))


_lagg(
    "scene_snapshot",
    "Ger hela scenen i kort form: varje komponents namn, vilken SORT den ar "
    "enligt sina beteenden, och om anvandaren har markerat den. Sorten kommer "
    "ur strukturen och aldrig ur namnet - en komponent som heter Robot men "
    "saknar robotstyrning far tom sort, inte 'robot'. Svaret ar avsett att "
    "lasas i varje tur i stallet for att fragas fram.",
    "read",
    params({}),
    returns({"components": {"type": "array", "description": "Komponenterna i scenen.",
                            "items": _KOMPONENTPOST},
             "antal": RET_ANTAL,
             "markerade": {"type": "integer",
                           "description": "Hur manga av dem som ar markerade."},
             "avkortad": RET_AVKORTAD},
            ["components", "antal", "markerade", "avkortad"]),
    _YTOR,
    _kod_scene_snapshot,
)


VERKTYG = ("get_selection", "scene_snapshot")


# ---- grinden: markeringsverktygen far ALDRIG kunna andra nagot -----------

def granska_domanen(register):
    """Kastar Schemafel om nagot verktyg i domanen inte ar deklarerat read.

    Grinden ar inte dekoration. Ett markeringsverktyg med effect=write skulle
    routas till exec_queue av utforaren (I12) och darmed vara en vag att
    ANDRA scenen genom att fraga vad som ar markerat. Fragan "vad pekar du
    pa" far inte kunna flytta nagot.

    Kravet stalls pa det DEKLARERADE faltet, som ar oforanderligt efter
    registrering (Verktyg.__setattr__), sa grinden och utforarens routing
    laser samma varde.
    """
    fel = sorted(namn for namn, v in register.items()
                 if getattr(v, "doman", None) == DOMAN
                 and getattr(v, "effect", None) != "read")
    if fel:
        raise Schemafel(
            "%s ligger i domanen %s men ar inte deklarerade read. Ett "
            "markeringsverktyg som kan skriva ar en vag runt godkannandekon "
            "(I12): en fraga om vad anvandaren pekar pa far aldrig kunna "
            "flytta nagot." % (", ".join(fel), DOMAN))
    return True


granska_domanen(REGISTER)
