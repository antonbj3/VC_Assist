# -*- coding: utf-8 -*-
"""Domanen measure: grindarnas ravara.

Kalla for urvalet: docs/spec/47_verktygstackning.md avsnitt 4.4, som rangordnar
domanen som nummer TVA av tjugotre med grindvardet "barande". 50_grindar.md kan
inte falla nagot utan den och 40_ogat.md kan inte doma utan den.

MATT 2026-09-04 (M-47): av domanens 42 namngivna API-symboler rordes NOLL av
nagon byggd mall. Det var den enda domanen pa exakt noll procent, och den
enda BARANDE domanen som var helt orord.

VARFOR DEN HAR DOMANEN INTE BYGGS PA vcCollisionDetector
---------------------------------------------------------
47_verktygstackning.md avsnitt 4.4 foreslar femton verktyg. Sju av dem
(`new_collision_detector`, `test_one_collision`, `collision_hits`,
`bbox_collision`, `collision_settings`, `new_volume_detector`, `volume_hits`)
bygger pa vcCollisionDetector och vcVolumeDetector. De byggs INTE har, och
skalet ar matt, inte antaget:

  M-35: detektorn svarade NOLL traffar aven for tva kuber om 1000 mm som lag
        100 mm isar, alltsa 900 mm overlapp i varje axel. Aven det trasiga
        fallet var gront. En grind som aldrig fallt nagot mater ingenting.
  M-36: orsaken. vcCollisionDetector.NodeListA tar emot en LISTA men TOMMER
        den - las tillbaka ger [] och langd 0. Ett enskilt objekt och en tupel
        avvisas med AttributeError som pastar att egenskapen inte finns.
        Detektorns nodlistor var alltsa tomma hela tiden.
  M-35: dessutom saknas vcCollisionDetector.StopOnCollision helt pa det objekt
        sim.newCollisionDetector() lamnar, trots att api.xml deklarerar den.

Ett verktyg som bara kan svara "inga kollisioner" ar en stubbe (S1). Sju
sadana verktyg vore sju stubbar. Den vagen star i stallet OPPEN och MATT genom
`collision_detector_status`, som kor M-36:s egen provning inne i den VC som
faktiskt svarar och rapporterar om listan haller. Den dag den gor det ska de
sju verktygen byggas, och da faller ett prov i
tests/enhet/test_verktyg_simmatning.py som sager det.

VAD SOM ERSATTER DEN
--------------------
M-36 matte vad som FUNGERAR: vcNode.measureDistance(annan), och vcComponent
arver hela nodytan. Den returnerar en tupel (avstand, punkt1, punkt2, vektor)
och gav exakt ratt varde i alla fem provade lagen, i millimeter (M-33).

Tva foljder som varje verktyg har bar med sig i sitt svar:

  1. Avstandet 0.0 betyder NUDDAR ELLER OVERLAPPAR. Mattet skiljer inte de
     tva. For en grind som kraver noll kollisioner racker det; vill man veta
     hur DJUPT tva kroppar tranger in i varandra kravs nagot annat, och det
     ar omatt.
  2. Utan en uppdatering emellan svarar VC konsekvent och trovardigt med ett
     GAMMALT tal. M-36 matte det: fem olika lagen gav identiskt 4000.0. Varje
     matande mall har kor darfor nod.update() och sim.update() forst.

Foljd 2 ar ocksa skalet till att tre matande verktyg ar deklarerade `write`
trots att de i sak bara FRAGAR. bryggans skrivgrind domer update() som
skrivande (skrivgrind.MUTERANDE_PREFIX), och ett verktyg som deklarerar read
men vars kod grinden domer som skrivande avvisas av bryggan med
E_NOT_APPROVED och fungerar alltsa aldrig. Deklarationen foljer grinden, inte
tvartom - samma val som robotik.py gjorde for check_reach. Alternativet, att
lasa utan att uppdatera, ar att bygga in M-36:s falla i grindens ravara.

VARFOR STRALARNA UTGAR FRAN EN NAMNGIVEN NOD
---------------------------------------------
`ray_cast` och `frame_owner_node` tar inte fria koordinater utan en KOMPONENT
och en NOD, och gar ut fran den ramens lage. Tva skal, och bada ar starkare an
bekvamligheten:

  * I8 (90_invarianter.md): modellen anger relationer, aldrig koordinater. En
    stralning ur en givares egen ram ar en relation; ett handskrivet
    varldslage ar en gissning som ser ut som ett matt.
  * Formen. Att bygga en fri startmatris kraver m.P = ... eller m.setWPR(...),
    och bada domes som SKRIVANDE av bryggans grind. Bada verktygen hade da
    hamnat i godkannandekon fast de inte ror scenen. Ur en befintlig ram, med
    rotateAbs* och translateAbs, ar koden lasande hela vagen.

VAD SOM AR OPROVAT, SAGT RAKT
-----------------------------
Ingen rad har har kort mot en levande VC. `vcApplication.rayCast` bar dessutom
en osakerhet som star i kallan sjalv: returtypen ar `unknown` och kallan sager
bara "collision data is returned as tuple with three or five elements". Vilket
element som ar vad star INGENSTANS i de fyra kallfilerna. `ray_cast` lamnar
darfor elementen som de kom, med sitt antal, och pastar inte vad de betyder.
Det ar inte en halvfardig mall utan gransen for vad kallan sager.
"""
from __future__ import annotations

from .bas import (ARG_KOMPONENT, ARG_NOD, RET_ANTAL, RET_AVKORTAD, XYZ,
                  laggare, params, returns)
from .fel import Argumentfel
from .kodmall import MAX_POSTER, bygg, lit, tal

DOMAN = "measure"
_lagg = laggare(DOMAN)

# Storsta antal kroppar test_collision jamfor mot varandra.
#
# Harkomst, raknad och inte vald: taket for en svarslista ar
# kodmall.MAX_POSTER = 500 poster, som i sin tur kommer ur bryggans 1 MiB-kropp
# (31_brygga_protokoll.md). n kroppar ger n(n-1)/2 par, och varje par kan bli en
# traffpost. 32 kroppar ger 496 par och 33 ger 528, alltsa over taket. Talet ar
# alltsa det storsta n dar en FULL trafflista fortfarande ryms i ett svar.
# En scen med fler kroppar an sa maste delas upp av den som fragar, och
# verktyget sager det i klartext i stallet for att klippa tyst.
MAX_KROPPAR = 32  # Satt av M-47.

# Toleransen ett kollisionsprov anvander nar ingen anges.
#
# Noll och inte ett litet positivt tal, och det ar en matt slutsats:
# M-36 visade att measureDistance ger EXAKT 0.0 for kant-i-kant och for varje
# grad av overlapp, och exakta positiva tal (500.0, 4000.0) for glapp. Det
# finns alltsa inget brusgolv att marginalera bort - en tolerans over noll
# skulle inte kompensera for matbrus utan tysta bort verkliga narkontakter.
# Den som VILL ha en sakerhetsmarginal anger den, och da star den i svaret.
TOLERANS_STANDARD = 0.0  # Satt av M-36 (M-47 namner ingen tolerans).


# ---- domanens egna hjalpare ---------------------------------------------

_EGNA = {
    "_vek": ((), [
        "def _vek(v):",
        "    # vcVector ut som tre tal. None overlever som null: kallan sager",
        "    # att measureDistance kan lamna None, och en nolla dar hade sett",
        "    # ut som ett matt varde.",
        "    if v is None:",
        "        return None",
        "    return [float(v.X), float(v.Y), float(v.Z)]",
    ]),
    "_farsk": ((), [
        "def _farsk(noder):",
        "    # M-36: utan de har tva raderna svarar VC konsekvent och",
        "    # trovardigt med ett GAMMALT avstand. Fem olika lagen gav",
        "    # identiskt 4000.0 i matningen. Geometrin utvarderas inte om",
        "    # inom samma korning.",
        "    for n in noder:",
        "        n.update()",
        "    getSimulation().update()",
    ]),
    "_matt": (("_vek",), [
        "def _matt(a, b):",
        "    # measureDistance lamnar (avstand, punkt1, punkt2, vektor) eller",
        "    # None nar inget minsta avstand hittas. Bada fallen bars ut.",
        "    r = a.measureDistance(b)",
        "    if r is None:",
        '        return {"found": False, "distance": None, "point1": None,',
        '                "point2": None, "vector": None}',
        '    return {"found": True, "distance": float(r[0]),',
        '            "point1": _vek(r[1]), "point2": _vek(r[2]),',
        '            "vector": _vek(r[3])}',
    ]),
    "_ram": ((), [
        "def _ram(nod):",
        "    # En KOPIA av nodens varldsram. vcMatrix.new(m) kopierar, sa att",
        "    # ingen rotation harinne kan rora scenen.",
        "    return vcMatrix.new(nod.WorldPositionMatrix)",
    ]),
}
_EGEN_ORDNING = ("_vek", "_farsk", "_matt", "_ram")


def _egna(namn):
    """Raderna for hjalparna plus allt de beror av, i fast ordning."""
    behovs = set()
    kvar = list(namn)
    while kvar:
        n = kvar.pop()
        if n in behovs:
            continue
        if n not in _EGNA:
            raise KeyError("okand hjalpare %r i matningsmallen" % (n,))
        behovs.add(n)
        kvar.extend(_EGNA[n][0])
    rader = []
    for n in _EGEN_ORDNING:
        if n in behovs:
            rader.extend(_EGNA[n][1])
            rader.append("")
            rader.append("")
    return rader


def _mall(kodmallshjalpare, egna, rader, importer=()):
    return bygg(kodmallshjalpare, _egna(egna) + rader, importer)


# Ytorna formagegrinden faktiskt kan prova. Ingen av matytorna
# (measureDistance, getPathDistance, rayCast utan matris, detectFrameOwnerNode,
# newCollisionDetector) star i formaga.YTOR utom app.rayCast; det som
# deklareras ar vagen FRAM till kropparna. Se modulens docstring.
_YTOR_PAR = ("app.findComponent", "comp.findNode", "comp.Name")
_YTOR_LAYOUT = ("app.Components", "app.findComponent", "comp.Name")
_YTOR_KOMPONENT = ("app.findComponent", "comp.Name")
_YTOR_RAM = ("app.findComponent", "comp.findNode", "node.WorldPositionMatrix")
_YTOR_STRALE = _YTOR_RAM + ("app.rayCast",)


# Noteringen om vad 0.0 betyder star pa ETT stalle. Tva kopior vore tva
# sanningar sa fort nagon andrar den ena.
NOTERING_NOLLA = (
    "M-36: avstandet 0.0 betyder NUDDAR ELLER OVERLAPPAR - mattet skiljer "
    "inte de tva, och sager alltsa ingenting om hur djupt kropparna tranger "
    "in i varandra. Matt i millimeter (M-33).")

NOTERING_INTE_DETEKTORN = (
    "Matt med vcNode.measureDistance och INTE med vcCollisionDetector. "
    "M-35 och M-36: detektorns nodlistor toms tyst, sa den svarar noll "
    "traffar aven for kroppar med 900 mm overlapp. Kor "
    "collision_detector_status for att se om den VC du ar i har samma fel.")

_RET_MATT = {
    "found": {"type": "boolean",
              "description": "False betyder att VC inte hittade nagot minsta "
                             "avstand alls, till exempel for en nod utan "
                             "geometri. Det ar inte samma sak som avstandet noll."},
    "distance": {"type": ["number", "null"],
                 "description": "Minsta avstand i MILLIMETER, null nar found "
                                "ar false."},
    "point1": {"type": ["array", "null"],
               "description": "Narmaste punkten pa den forsta kroppen.",
               "items": {"type": "number", "description": "Koordinat i millimeter."}},
    "point2": {"type": ["array", "null"],
               "description": "Narmaste punkten pa den andra kroppen.",
               "items": {"type": "number", "description": "Koordinat i millimeter."}},
    "vector": {"type": ["array", "null"],
               "description": "Riktning och langd fran punkt1 till punkt2, i "
                              "den ANROPANDE nodens koordinatsystem enligt "
                              "kallan - inte i varldens.",
               "items": {"type": "number", "description": "Komponent i vektorn."}},
}


# ==========================================================================
# MATANDE VERKTYG (write, for att uppdateringen kravs - se modulens docstring)
# ==========================================================================

# ---- measure_distance ----------------------------------------------------

def _kod_measure_distance(argument):
    rader = [
        "a = _nod(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument.get("node", ""))),
        "b = _nod(_komp(%s), %s)" % (lit(argument["other_component"]),
                                     lit(argument.get("other_node", ""))),
        "if a is b:",
        '    raise ValueError("de tva kropparna ar samma nod; ett avstand '
        'till sig sjalv ar alltid noll och sager ingenting")',
        "_farsk([a, b])",
        "svar = _matt(a, b)",
        'svar["a"] = a.Name',
        'svar["b"] = b.Name',
        'svar["touching"] = bool(svar["found"] and svar["distance"] <= %s)'
        % tal(argument["tolerance"]),
        'svar["tolerance"] = %s' % tal(argument["tolerance"]),
        'svar["notering"] = %s' % lit(NOTERING_NOLLA + " " + NOTERING_INTE_DETEKTORN),
        "_svara(svar)",
    ]
    return _mall(["_komp", "_nod", "_svara"], ["_farsk", "_matt"], rader)


_lagg(
    "measure_distance",
    "Mater minsta avstandet mellan tva kroppar i MILLIMETER och lamnar de tva "
    "narmaste punkterna. Detta ar kollisionsmattet i det har projektet: "
    "avstandet 0.0 betyder att kropparna nuddar eller overlappar. Verktyget "
    "uppdaterar scenen forst, for utan det svarar VC med ett gammalt tal "
    "(M-36) - det ar ocksa hela skalet till att det gar genom godkannandekon "
    "trots att det bara fragar.",
    "write",
    params({"component": ARG_KOMPONENT, "node": ARG_NOD,
            "other_component": dict(ARG_KOMPONENT,
                                    description="Den andra kroppens komponent."),
            "other_node": dict(ARG_NOD,
                               description="Nod inne i den andra komponenten. "
                                           "Utelamnad betyder dess rot."),
            "tolerance": {"type": "number", "default": TOLERANS_STANDARD,
                          "description": "Avstand i millimeter under vilket "
                                         "kropparna raknas som i kontakt. "
                                         "Standard ar noll."}},
           ["component", "other_component"]),
    returns(dict(_RET_MATT, **{
        "a": {"type": "string", "description": "Forsta kroppens nodnamn."},
        "b": {"type": "string", "description": "Andra kroppens nodnamn."},
        "touching": {"type": "boolean",
                     "description": "True nar avstandet ar hogst tolerance."},
        "tolerance": {"type": "number", "description": "Toleransen som anvandes."},
        "notering": {"type": "string",
                     "description": "Vad nollan betyder och vilken yta som matte."}}),
            ["found", "distance", "a", "b", "touching", "tolerance", "notering"]),
    _YTOR_PAR,
    _kod_measure_distance,
)


# ---- min_distance --------------------------------------------------------

def _kod_min_distance(argument):
    andra = argument.get("others")
    if andra is not None:
        if not andra:
            raise Argumentfel("min_distance",
                              ["others is empty; give at least one counterpart "
                               "or omit the argument to measure against the "
                               "whole layout"])
        if len(andra) > MAX_KROPPAR:
            raise Argumentfel("min_distance", [
                "others has %d components; the cap is %d (matning.MAX_KROPPAR, "
                "derived from kodmall.MAX_POSTER). Split the request"
                % (len(andra), MAX_KROPPAR)])
    rader = [
        "a = _nod(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument.get("node", ""))),
    ]
    if andra is None:
        rader += [
            "motparter = []",
            "avkortad = False",
            "for k in _app().Components:",
            "    if k is a or k.Name == a.Name:",
            "        continue",
            "    if len(motparter) >= %d:   # matning.MAX_KROPPAR" % MAX_KROPPAR,
            "        avkortad = True",
            "        break",
            "    motparter.append(k)",
        ]
    else:
        rader += [
            "motparter = [_komp(n) for n in %s]" % lit(list(andra)),
            "avkortad = False",
        ]
    rader += [
        "if not motparter:",
        '    raise ValueError("det finns ingen annan kropp att mata mot")',
        "_farsk([a] + motparter)",
        "rader = []",
        "for b in motparter:",
        "    post = _matt(a, b)",
        '    post["other"] = b.Name',
        "    rader.append(post)",
        "traffar = [p for p in rader if p[%s]]" % lit("found"),
        "narmast = None",
        "for p in traffar:",
        '    if narmast is None or p["distance"] < narmast["distance"]:',
        "        narmast = p",
        '_svara({"component": a.Name, "nearest": narmast, "measured": rader,',
        '        "antal": len(rader), "avkortad": avkortad,',
        '        "unmeasurable": len(rader) - len(traffar),',
        '        "notering": %s})' % lit(NOTERING_NOLLA + " " + NOTERING_INTE_DETEKTORN),
    ]
    hjalpare = ["_komp", "_nod", "_svara"]
    if andra is None:
        hjalpare.append("_app")
    return _mall(hjalpare, ["_farsk", "_matt"], rader)


_lagg(
    "min_distance",
    "Mater en kropp mot flera och sager vilken som ligger NARMAST, med "
    "avstandet i millimeter. Utan others mats mot alla andra komponenter i "
    "layouten. Anvand detta for gangar, sakerhetsavstand och 'far det plats'. "
    "Uppdaterar scenen forst (M-36), darav godkannandekon.",
    "write",
    params({"component": ARG_KOMPONENT, "node": ARG_NOD,
            "others": {"type": "array",
                       "description": "Komponentnamn att mata mot. Utelamnad "
                                      "betyder alla andra i layouten.",
                       "items": {"type": "string",
                                 "description": "En komponents namn."}}},
           ["component"]),
    returns({"component": {"type": "string", "description": "Kroppen som mattes fran."},
             "nearest": {"type": ["object", "null"],
                         "description": "Den narmaste motparten, eller null om "
                                        "ingen motpart gick att mata.",
                         "properties": dict(
                             _RET_MATT,
                             other={"type": "string",
                                    "description": "Motpartens komponentnamn."})},
             "measured": {"type": "array", "description": "Varje matt motpart.",
                          "items": {"type": "object",
                                    "description": "Ett matt par.",
                                    "properties": dict(
                                        _RET_MATT,
                                        other={"type": "string",
                                               "description": "Motpartens namn."})}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD,
             "unmeasurable": {"type": "integer",
                              "description": "Hur manga motparter VC inte kunde "
                                             "ge nagot avstand till, oftast for "
                                             "att de saknar geometri."},
             "notering": {"type": "string", "description": "Vad nollan betyder."}},
            ["component", "nearest", "measured", "antal", "avkortad",
             "unmeasurable", "notering"]),
    _YTOR_LAYOUT + ("comp.findNode",),
    _kod_min_distance,
)


# ---- test_collision ------------------------------------------------------

def _kod_test_collision(argument):
    kroppar = argument.get("components")
    if kroppar is not None:
        if len(kroppar) < 2:
            raise Argumentfel("test_collision",
                              ["components has %d names; at least two bodies "
                               "are required for anything to collide"
                               % len(kroppar)])
        if len(kroppar) > MAX_KROPPAR:
            raise Argumentfel("test_collision", [
                "components has %d bodies; the cap is %d (matning.MAX_KROPPAR, "
                "derived from kodmall.MAX_POSTER: %d pairs fit in a response). "
                "Split the test" % (len(kroppar), MAX_KROPPAR, MAX_POSTER)])
    if argument["tolerance"] < 0.0:
        raise Argumentfel("test_collision",
                          ["tolerance is %r; a distance cannot be negative"
                           % (argument["tolerance"],)])
    rader = ["avkortad = False"]
    if kroppar is None:
        rader += [
            "kroppar = []",
            "for k in _app().Components:",
            "    if len(kroppar) >= %d:   # matning.MAX_KROPPAR" % MAX_KROPPAR,
            "        avkortad = True",
            "        break",
            "    kroppar.append(k)",
        ]
    else:
        rader.append("kroppar = [_komp(n) for n in %s]" % lit(list(kroppar)))
    rader += [
        "if len(kroppar) < 2:",
        '    raise ValueError("det finns farre an tva kroppar att prova")',
        "_farsk(kroppar)",
        "traffar = []",
        "par = 0",
        "omatbara = 0",
        "for i in range(len(kroppar)):",
        "    for j in range(i + 1, len(kroppar)):",
        "        par = par + 1",
        "        post = _matt(kroppar[i], kroppar[j])",
        '        if not post["found"]:',
        "            omatbara = omatbara + 1",
        "            continue",
        '        if post["distance"] > %s:' % tal(argument["tolerance"]),
        "            continue",
        '        post["a"] = kroppar[i].Name',
        '        post["b"] = kroppar[j].Name',
        "        traffar.append(post)",
        # I3, fail-closed, och returschemats egen text: ett omatbart par ar
        # OMATT, aldrig fritt. En traff ar en traff oavsett; men NOLL traffar
        # nar nagot par inte gick att mata ar inget svar, och da svarar
        # faltet null. MATT M-94 fynd 5: fore detta svarade en scen dar
        # measureDistance ger None for varje par (M-36 dokumenterar att det
        # hander) {"collision": false, "pairs_tested": 496,
        # "unmeasurable": 496} - noll par mattes, och svaret sa "ingen
        # kollision". min_distance hade den arliga formen i samma fil.
        "if traffar:",
        "    kollision = True",
        "elif omatbara:",
        "    kollision = None",
        "else:",
        "    kollision = False",
        '_svara({"collision": kollision, "hits": traffar,',
        '        "antal": len(traffar), "bodies": len(kroppar),',
        '        "pairs_tested": par, "unmeasurable": omatbara,',
        '        "tolerance": %s, "avkortad": avkortad,' % tal(argument["tolerance"]),
        '        "notering": %s})' % lit(NOTERING_NOLLA + " " + NOTERING_INTE_DETEKTORN),
    ]
    hjalpare = ["_svara"]
    hjalpare.append("_app" if kroppar is None else "_komp")
    return _mall(hjalpare, ["_farsk", "_matt"], rader)


_lagg(
    "test_collision",
    "Provar varje par av kroppar mot varandra och lamnar de par som ligger "
    "hogst tolerance millimeter isar. Detta ar kollisionsgrindens ravara. "
    "VIKTIGT: mattet bygger pa measureDistance och INTE pa VC:s "
    "kollisionsdetektor, som M-35 och M-36 matte som trasig - detektorn "
    "svarar noll traffar aven for 900 mm overlapp. Utan components provas "
    "hela layouten upp till taket.",
    "write",
    params({"components": {"type": "array",
                           "description": "Komponentnamn att prova mot "
                                          "varandra. Utelamnad betyder hela "
                                          "layouten upp till taket.",
                           "items": {"type": "string",
                                     "description": "En komponents namn."}},
            "tolerance": {"type": "number", "default": TOLERANS_STANDARD,
                          "description": "Kroppar narmare varandra an sa "
                                         "raknas som en traff. Standard noll, "
                                         "vilket betyder nuddar eller "
                                         "overlappar."}},
           []),
    returns({"collision": {"type": ["boolean", "null"],
                           "description": "True om minst ett par ligger inom "
                                          "toleransen. null om inget par "
                                          "traffade OCH minst ett par inte "
                                          "gick att mata: de omatta paren "
                                          "raknas ALDRIG som fria, sa da ar "
                                          "svaret okant och inte nej. False "
                                          "bara nar varje par mattes och "
                                          "inget traffade."},
             "hits": {"type": "array", "description": "De par som traffade.",
                      "items": {"type": "object", "description": "Ett traffat par.",
                                "properties": dict(
                                    _RET_MATT,
                                    a={"type": "string", "description": "Forsta kroppen."},
                                    b={"type": "string", "description": "Andra kroppen."})}},
             "antal": RET_ANTAL,
             "bodies": {"type": "integer", "description": "Antal kroppar som provades."},
             "pairs_tested": {"type": "integer", "description": "Antal par som mattes."},
             "unmeasurable": {"type": "integer",
                              "description": "Par VC inte kunde ge nagot avstand "
                                             "for. De raknas ALDRIG som fria - "
                                             "de ar omatta."},
             "tolerance": {"type": "number", "description": "Toleransen som anvandes."},
             "avkortad": RET_AVKORTAD,
             "notering": {"type": "string", "description": "Vilken yta som matte."}},
            ["collision", "hits", "antal", "bodies", "pairs_tested",
             "unmeasurable", "tolerance", "avkortad", "notering"]),
    _YTOR_LAYOUT,
    _kod_test_collision,
)


# ---- collision_detector_status -------------------------------------------

def _kod_collision_detector_status(argument):
    rader = [
        "a = _komp(%s)" % lit(argument["component"]),
        "b = _komp(%s)" % lit(argument["other_component"]),
        "if a is b:",
        '    raise ValueError("provet kraver tva olika komponenter")',
        "d = getSimulation().newCollisionDetector()",
        'svar = {"detector_created": d is not None,',
        '        "a": a.Name, "b": b.Name}',
        "if d is None:",
        '    svar["nodelist_holds"] = False',
        '    svar["nodelist_a_length"] = 0',
        '    svar["nodelist_b_length"] = 0',
        '    svar["stop_on_collision_present"] = False',
        '    svar["collision"] = None',
        '    svar["hit_count"] = None',
        "else:",
        # M-36: en LISTA accepteras och innehallet kastas; ett enskilt objekt
        # och en tupel avvisas med AttributeError. Vi provar det som
        # accepteras och laser tillbaka langden. Det ar hela provet.
        "    d.NodeListA = [a]",
        "    d.NodeListB = [b]",
        '    svar["nodelist_a_length"] = len(d.NodeListA)',
        '    svar["nodelist_b_length"] = len(d.NodeListB)',
        '    svar["nodelist_holds"] = bool(len(d.NodeListA) == 1'
        ' and len(d.NodeListB) == 1)',
        # M-35: api.xml deklarerar StopOnCollision men den saknas pa objektet.
        '    svar["stop_on_collision_present"] = bool(hasattr(d, "StopOnCollision"))',
        '    if svar["nodelist_holds"]:',
        '        svar["collision"] = bool(d.testAllCollisions(0.0))',
        '        svar["hit_count"] = int(d.HitCount)',
        "    else:",
        # Fail-closed: en detektor med tomma listor svarar alltid False, och
        # det svaret far INTE gan ut som "inga kollisioner" (I3).
        '        svar["collision"] = None',
        '        svar["hit_count"] = None',
        'svar["matches_m36"] = bool(not svar["nodelist_holds"])',
        'svar["notering"] = %s' % lit(
            "M-36 matte att NodeListA tar emot en lista men TOMMER den. "
            "nodelist_holds=false bekraftar samma fel i denna VC, och da ar "
            "collision null och inte false - en detektor med tomma listor "
            "svarar alltid noll traffar. Haller listan ar M-36 motbevisad har "
            "och de sju detektorverktygen i 47_verktygstackning.md 4.4 ska "
            "byggas."),
        "_svara(svar)",
    ]
    return _mall(["_komp", "_svara"], [], rader)


_lagg(
    "collision_detector_status",
    "Provar om VC:s EGEN kollisionsdetektor fungerar i den har installationen, "
    "genom att kora om M-36:s matning: satt NodeListA och NodeListB till var "
    "sin komponent och las tillbaka langden. Svarar nodelist_holds=false om "
    "listorna toms, vilket ar det fel M-35 och M-36 matte och skalet till att "
    "test_collision bygger pa measureDistance i stallet. Kor detta INNAN du "
    "litar pa nagot detektorbaserat verktyg - det finns inga sadana i "
    "biblioteket just for att det har provet var rott.",
    "write",
    params({"component": dict(ARG_KOMPONENT,
                              description="Forsta komponenten i provet. Vilken "
                                          "som helst med geometri duger."),
            "other_component": dict(ARG_KOMPONENT,
                                    description="Andra komponenten i provet. "
                                                "Maste vara en annan an den "
                                                "forsta.")},
           ["component", "other_component"]),
    returns({"a": {"type": "string", "description": "Forsta komponenten i provet."},
             "b": {"type": "string", "description": "Andra komponenten i provet."},
             "detector_created": {"type": "boolean",
                                  "description": "Om sim.newCollisionDetector() "
                                                 "lamnade ett objekt alls."},
             "nodelist_holds": {"type": "boolean",
                                "description": "True bara om bada nodlistorna "
                                               "bar sin komponent efter "
                                               "sattningen. Falskt ar M-36:s fel."},
             "nodelist_a_length": {"type": "integer",
                                   "description": "Langden pa NodeListA efter "
                                                  "att en komponent lagts i den. "
                                                  "M-36 matte 0."},
             "nodelist_b_length": {"type": "integer",
                                   "description": "Samma for NodeListB."},
             "stop_on_collision_present": {
                 "type": "boolean",
                 "description": "Om egenskapen StopOnCollision finns pa "
                                "objektet. api.xml deklarerar den; M-35 fann "
                                "att den saknas."},
             "collision": {"type": ["boolean", "null"],
                           "description": "Detektorns svar, men BARA nar "
                                          "listorna holl. null nar de inte "
                                          "gjorde det - ett noll fran tomma "
                                          "listor ar inget svar."},
             "hit_count": {"type": ["integer", "null"],
                           "description": "Detektorns HitCount, null pa samma "
                                          "villkor som collision."},
             "matches_m36": {"type": "boolean",
                             "description": "True nar denna VC uppvisar samma "
                                            "fel som M-36 matte."},
             "notering": {"type": "string",
                          "description": "Vad utfallet betyder for biblioteket."}},
            ["a", "b", "detector_created", "nodelist_holds", "nodelist_a_length",
             "nodelist_b_length", "stop_on_collision_present", "collision",
             "hit_count", "matches_m36", "notering"]),
    _YTOR_KOMPONENT,
    _kod_collision_detector_status,
)


# ==========================================================================
# LASANDE VERKTYG
# ==========================================================================

# ---- path_distance -------------------------------------------------------

def _kod_path_distance(argument):
    namn = lit(argument["component"])
    return _mall(["_komp", "_svara"], [], [
        "k = _komp(%s)" % namn,
        "d = k.getPathDistance()",
        '_svara({"component": k.Name,',
        '        "on_path": d is not None,',
        '        "distance": float(d) if d is not None else None,',
        '        "notering": %s})' % lit(
            "Avstandet ar hur langt komponenten kommit LANGS banan i "
            "millimeter, inte hur langt den ar fran nagot. Ligger den inte pa "
            "en bana svarar VC ingenting och on_path blir false."),
    ])


_lagg(
    "path_distance",
    "Sager hur langt en komponent kommit langs den bana den star pa, i "
    "millimeter. Anvands for att se var pa ett transportband en produkt "
    "befinner sig. Svarar on_path=false for en komponent som inte ligger pa "
    "nagon bana, vilket ar ett giltigt svar och inte ett fel.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten som lastes."},
             "on_path": {"type": "boolean", "description": "Om komponenten ligger pa en bana."},
             "distance": {"type": ["number", "null"],
                          "description": "Strackan langs banan i millimeter, "
                                         "null nar on_path ar false."},
             "notering": {"type": "string", "description": "Vad talet mater."}},
            ["component", "on_path", "distance", "notering"]),
    _YTOR_KOMPONENT,
    _kod_path_distance,
)


# ---- ray_cast ------------------------------------------------------------

def _kod_ray_cast(argument):
    if argument["length"] <= 0.0:
        raise Argumentfel("ray_cast",
                          ["length is %r; a ray's length must be greater "
                           "than zero" % (argument["length"],)])
    rader = [
        "n = _nod(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument.get("node", ""))),
        "m = _ram(n)",
    ]
    # Rotationerna ligger fore forflyttningen: strale ur ramens origo, vriden,
    # och sedan flyttad. rotateAbs*/translateAbs och inte setWPR/P, for de tva
    # senare domes som SKRIVANDE av bryggans grind (se modulens docstring).
    for axel, arg in (("X", "rotate_x_deg"), ("Y", "rotate_y_deg"),
                      ("Z", "rotate_z_deg")):
        if argument.get(arg):
            rader.append("m.rotateAbs%s(%s)" % (axel, tal(argument[arg])))
    if argument.get("offset"):
        x, y, z = argument["offset"]
        rader.append("m.translateAbs(%s, %s, %s)" % (tal(x), tal(y), tal(z)))
    rader += [
        "traff = _app().rayCast(m, %s)" % tal(argument["length"]),
        # Kallan sager "tuple with three or five elements" och deklarerar
        # returtypen som unknown. Vad varje element ar star ingenstans, sa
        # elementen lamnas som de kom, forenklade, och tolkas INTE.
        "delar = []",
        "if traff is not None:",
        "    for e in traff:",
        "        delar.append(_enkelt(e))",
        '_svara({"origin_node": n.Name, "hit": traff is not None,',
        '        "elements": delar, "element_count": len(delar),',
        '        "length": %s,' % tal(argument["length"]),
        '        "ray_origin": [float(m.P.X), float(m.P.Y), float(m.P.Z)],',
        '        "notering": %s})' % lit(
            "Stralen gar langs den vridna ramens POSITIVA Z-AXEL, enligt "
            "kallan. Kallan deklarerar rayCast:s returtyp som unknown och "
            "sager bara att traffen ar en tupel med tre eller fem element; "
            "vilket element som ar nod, punkt respektive normal star inte i "
            "nagon av de fyra kallfilerna. Elementen lamnas darfor som de "
            "kom och tolkas inte har."),
    ]
    return _mall(["_komp", "_nod", "_app", "_enkelt", "_svara"], ["_ram"],
                 rader, ("vcMatrix",))


_lagg(
    "ray_cast",
    "Skjuter en strale ur en NAMNGIVEN nods egen ram, langs dess positiva "
    "Z-axel, och sager om den traffar nagot. Startpunkten anges som en "
    "komponent och en nod - aldrig som varldskoordinater (I8: modellen anger "
    "relationer). Vrid stralen med rotate_*_deg och flytta startpunkten med "
    "offset om den ska ga at ett annat hall.",
    "read",
    params({"component": ARG_KOMPONENT, "node": ARG_NOD,
            "length": {"type": "number",
                       "description": "Stralens langd i millimeter. Storre an noll."},
            "rotate_x_deg": {"type": "number",
                             "description": "Vrid ramen sa har manga grader "
                                            "runt X innan stralen skjuts. "
                                            "180 vander stralen rakt ned."},
            "rotate_y_deg": {"type": "number",
                             "description": "Vridning runt Y i grader."},
            "rotate_z_deg": {"type": "number",
                             "description": "Vridning runt Z i grader."},
            "offset": dict(XYZ, description="Flytta startpunkten sa har manga "
                                            "millimeter fran nodens origo, "
                                            "efter vridningen.")},
           ["component", "length"]),
    returns({"origin_node": {"type": "string", "description": "Noden stralen utgick fran."},
             "hit": {"type": "boolean", "description": "Om stralen traffade nagot."},
             "elements": {"type": "array",
                          "description": "Traffens element precis som VC lamnade "
                                         "dem, forenklade till JSON. Otolkade.",
                          "items": {"type": ["string", "number", "boolean", "null"],
                                    "description": "Ett element ur VC:s tupel."}},
             "element_count": {"type": "integer",
                               "description": "Antal element. Kallan sager tre "
                                              "eller fem; talet sager vilket det blev."},
             "length": {"type": "number", "description": "Langden som anvandes."},
             "ray_origin": dict(XYZ, description="Startpunkten i varlden, efter "
                                                 "vridning och offset."),
             "notering": {"type": "string",
                          "description": "Riktningen, och vad kallan INTE sager "
                                         "om elementen."}},
            ["origin_node", "hit", "elements", "element_count", "length",
             "ray_origin", "notering"]),
    _YTOR_STRALE,
    _kod_ray_cast,
)


# ---- frame_owner_node ----------------------------------------------------

def _kod_frame_owner_node(argument):
    if argument["tolerance"] <= 0.0:
        raise Argumentfel("frame_owner_node",
                          ["tolerance is %r; the search radius must be "
                           "greater than zero, otherwise no frame can lie "
                           "within it" % (argument["tolerance"],)])
    rader = [
        "n = _nod(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument.get("node", ""))),
        "m = _ram(n)",
    ]
    if argument.get("offset"):
        x, y, z = argument["offset"]
        rader.append("m.translateAbs(%s, %s, %s)" % (tal(x), tal(y), tal(z)))
    rader += [
        "agare = _app().detectFrameOwnerNode(m, %s)" % tal(argument["tolerance"]),
        '_svara({"from_node": n.Name, "found": agare is not None,',
        '        "owner": agare.Name if agare is not None else None,',
        '        "tolerance": %s,' % tal(argument["tolerance"]),
        '        "search_point": [float(m.P.X), float(m.P.Y), float(m.P.Z)],',
        '        "notering": %s})' % lit(
            "Svaret ar noden som ager den NARMASTE ram-featuren inom "
            "toleransen, inte ramen sjalv. found=false betyder att ingen ram "
            "lag inom sokradien - vidga tolerance i stallet for att anta att "
            "det inte finns nagon."),
    ]
    return _mall(["_komp", "_nod", "_app", "_svara"], ["_ram"], rader,
                 ("vcMatrix",))


_lagg(
    "frame_owner_node",
    "Sager vilken nod som ager den narmaste ram-featuren till en given punkt. "
    "Punkten anges som en nod plus en valfri forskjutning, aldrig som fria "
    "varldskoordinater (I8). Anvands for att hitta det monteringsfaste eller "
    "den greppunkt som ligger dar man tror att den ligger.",
    "read",
    params({"component": ARG_KOMPONENT, "node": ARG_NOD,
            "offset": dict(XYZ, description="Sok sa har manga millimeter fran "
                                            "nodens origo i stallet for i det."),
            "tolerance": {"type": "number",
                          "description": "Sokradie i millimeter. Storre an noll."}},
           ["component", "tolerance"]),
    returns({"from_node": {"type": "string", "description": "Noden soket utgick fran."},
             "found": {"type": "boolean", "description": "Om nagon ram lag inom radien."},
             "owner": {"type": ["string", "null"],
                       "description": "Namnet pa noden som ager ramen, null nar "
                                      "ingen hittades."},
             "tolerance": {"type": "number", "description": "Sokradien som anvandes."},
             "search_point": dict(XYZ, description="Punkten det soktes kring, i varlden."),
             "notering": {"type": "string", "description": "Vad found=false betyder."}},
            ["from_node", "found", "owner", "tolerance", "search_point",
             "notering"]),
    _YTOR_RAM,
    _kod_frame_owner_node,
)
