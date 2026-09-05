# -*- coding: utf-8 -*-
"""Databladet for EN komponent, last ur dess egen component.rsc.

VARFOR DEN HAR FILEN FINNS
--------------------------
M-84 matte vad API-uppslagen var varda (ordforradet gick fran 13 till 32
distinkta namn) och namngav exakt var de TOG SLUT:

    "Indexet tacker API-symboler. Det tacker inte per-komponent-data:
     komponenternas egenskapsnamn (ConveyorSpeed, StrokeTime, MaxPayload ...),
     bank://-URI:erna, och VILKEN boolsk signal
     findBehavioursByType(VC_BOOLEANSIGNAL)[0] ar pa en given komponent."

Ett API-index svarar pa "finns metoden". Det kan inte svara pa "heter den har
transportorens hastighetsegenskap Speed eller ConveyorSpeed", och det ar den
fragan som avgor om en genererad rad kor eller kastar.

VAD SOM SKILJER DEN HAR MODULEN FRAN katalogindex.parametrar
------------------------------------------------------------
`katalogindex._parametrar` soker med ett regexuttryck i HELA filtexten och far
darfor med variabler som sitter inne i geometriprimitiver. Dess egen docstring
sager det rent ut: "Indexets parameterlista ar alltsa en LISTA OVER VAD SOM
NAMNS, inte over komponentens egenskaper." M-59 matte felet: Prorunner mk1 bar
namnet `Length` 24 ganger i sina 16 lador och noll ganger som komponentens egen
egenskap.

Den har modulen laser i stallet STRUKTUREN. Komponentens egna egenskaper ligger
i rotnodens `VariableSpace ""` och ingen annanstans; geometrin ligger under
`NodeClass`, som hoppas over i sin helhet. Skillnaden ar inte kosmetisk - den
ar skillnaden mellan en lista pa 1806 namn utan agare och en lista dar varje
namn hor till komponenten.

FORMATET, MATT OCH INTE ANTAGET
-------------------------------
component.rsc ar ett klammerformat med citerade strangar. Rotnoden ser ut sa
har, och djupen ar rakmatta med en klammerraknare (samma metod som M-58
anvande for byteoffset):

    Node "rSimResource"          djup 0
    {
      Name "AccuVeyor AVh"       djup 1   komponentens namn
      NodeClass { ... }          djup 1   GEOMETRIN - hoppas over
      Functionality "rOneWayPath" { ... }  djup 1   ett beteende
      Category "Conveyors"       djup 1
      VariableSpace "" { ... }   djup 1   KOMPONENTENS EGNA EGENSKAPER
      Node "rSimLink" { ... }    djup 1   en led (robotar)
    }

Notera att indraget INTE bar djupet: inne i ett `Functionality`-block skriver
VC:s serialiserare alla rader i kolumn 0, medan `VariableSpace` indrar tva steg
per niva. Ett radbaserat djupmatt hade darfor gett fel svar, och det ar skalet
till att den har modulen klammerraknar i stallet.

ENHETER SAGS, HARLEDS ALDRIG
----------------------------
En egenskap kan bara ett `Quantity "Distance"`-falt. Det ar en STORHET, inte en
enhet. Databladet skriver ut storheten ordagrant och sager `saknas` nar den
inte star dar. Att en egenskap heter `Speed` och har vardet 820 far ALDRIG bli
"820 mm/s" i det har lagret - VC:s varldsenhet ar millimeter, men vilken enhet
just den har variabeln bar ar inte deklarerat i filen, och en enhet som harleds
ur ett talvarde ar en gissning som ser ut som ett matt (samma felklass som
en-parameter-som-bar-tva-storheter).
"""
from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

METADATA = "component.rsc"
KATALOGPOST = "model.xml"

SAKNAS = "saknas"


class Databladfel(Exception):
    pass


# ---------------------------------------------------------------------------
# Klammerlasaren
# ---------------------------------------------------------------------------
#
# Tva monster i stallet for en teckenloop: sokningen sker da i C och inte i
# Python, och bara de tecken som betyder nagot besoks. MATT nedan i M-85.
_KLAMMER = re.compile(r'["{}]')
_STRANGSLUT = re.compile(r'["\\]')
_ORD = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_BLANK = re.compile(r'[^\S\n]*')


def _strangslut(text: str, pos: int) -> int:
    """Index EFTER den avslutande citattecknet i en strang som borjar pa pos.

    Bakstrecket ar en riktig escape i formatet: `ProgramData` bar `\\"` inne i
    sin XML, och `BOMdescription` bryter rader med bakstreck-radbrytning. Den
    som laser strangar med ett girigt monster far darfor fel slut pa exakt de
    komponenter som bar mest text.
    """
    while True:
        m = _STRANGSLUT.search(text, pos)
        if m is None:
            return len(text)
        if m.group() == "\\":
            pos = m.end() + 1
            continue
        return m.end()


def _kroppsslut(text: str, i: int) -> int:
    """i pekar pa ett '{'. Ger index EFTER den matchande '}'."""
    if i >= len(text) or text[i] != "{":
        raise Databladfel("_kroppsslut anropad pa nagot som inte ar en klammer")
    djup = 0
    pos = i
    while True:
        m = _KLAMMER.search(text, pos)
        if m is None:
            raise Databladfel("obalanserade klamrar i component.rsc")
        c = m.group()
        p = m.start()
        if c == '"':
            pos = _strangslut(text, p + 1)
            continue
        if c == "{":
            djup += 1
        else:
            djup -= 1
            if djup == 0:
                return p + 1
        pos = p + 1


def _radslut(text: str, pos: int, slut: int) -> int:
    """Slutet pa huvudraden fran pos, med strangar hoppade over."""
    while pos < slut:
        m = _KLAMMER.search(text, pos)
        n = text.find("\n", pos)
        if n == -1:
            n = slut
        if m is None or m.start() > n:
            return min(n, slut)
        c = m.group()
        if c == '"':
            pos = _strangslut(text, m.end())
            continue
        # En klammer pa huvudraden avslutar den ocksa.
        return min(m.start(), n)
    return slut


# DOTALL ar inte kosmetik: `BOMdescription` bryter rader med bakstreck-
# radbrytning inne i strangen, sa `\\.` maste kunna matcha en radbrytning.
# Utan flaggan slutade beskrivningen for AccuVeyor AVh efter ett enda ord
# ("Ambaflex") och sag ut som en kort beskrivning i stallet for en kapad.
_ARG = re.compile(r'"((?:[^"\\]|\\.)*)"|([^\s{}"]+)', re.S)


@dataclass
class Del:
    """En direkt barnpost: nyckelord, argument och eventuell kropp."""

    nyckel: str
    argument: List[str]
    kropp: Tuple[int, int]          # (start, slut) i texten, tomt = (-1, -1)

    @property
    def har_kropp(self) -> bool:
        return self.kropp[0] >= 0

    def arg(self, n: int = 0) -> str:
        return self.argument[n] if len(self.argument) > n else ""


def delar(text: str, start: int, slut: int):
    """De DIREKTA barnen i regionen [start, slut).

    Genererar `Del`. Regionen ska vara insidan av en kropp, klammerbalanserad.
    """
    pos = start
    while pos < slut:
        m = _BLANK.match(text, pos)
        pos = m.end()
        if pos >= slut:
            return
        c = text[pos]
        if c == "\n":
            pos += 1
            continue
        if c == "}":
            return
        if c == "{":
            # Anonym kropp utan nyckelord: hoppa over den hellre an att
            # tolka den som nagot. En tyst feltolkning ar varre an ett hopp.
            pos = _kroppsslut(text, pos)
            continue
        o = _ORD.match(text, pos)
        if o is None:
            # Skrap som inte ar ett nyckelord: ga till nasta rad.
            n = text.find("\n", pos)
            pos = slut if n == -1 else n + 1
            continue
        nyckel = o.group()
        huvudslut = _radslut(text, o.end(), slut)
        argument = []
        for a in _ARG.finditer(text, o.end(), huvudslut):
            argument.append(a.group(1) if a.group(1) is not None else a.group(2))
        # Kropp? Nasta icke-blanka tecken efter huvudraden.
        p = huvudslut
        while p < slut and text[p] in " \t\r\n":
            p += 1
        if p < slut and text[p] == "{":
            k_slut = _kroppsslut(text, p)
            yield Del(nyckel, argument, (p + 1, k_slut - 1))
            pos = k_slut
        else:
            yield Del(nyckel, argument, (-1, -1))
            pos = huvudslut if huvudslut > pos else pos + 1


# ---------------------------------------------------------------------------
# Beteendetyper
# ---------------------------------------------------------------------------
#
# Filformatet skriver `Functionality "rSimBoolSignal"`. Pythonsidan heter
# `VC_BOOLEANSIGNAL`. Det ar TVA NAMNRYMDER, och avbildningen mellan dem star
# inte i nagon kalla vi har - varken api.xml, constants.xml eller filerna
# sjalva namner den andra sidan.
#
# Tabellen ar darfor HANDSKRIVEN, och det ar sagt hogt i stallet for att doljas.
# Tva prov haller den arlig:
#
#   test_varje_api_typ_finns_i_constants_xml     varje VC_-namn har maste sta i
#                                                docs/referens/vc_api/constants.xml
#   test_okand_beteendetyp_ger_saknas            en typ utanfor tabellen ger
#                                                SAKNAS, aldrig en gissning
#
# Det forsta provet ar inte formalia. M-84 matte att modellen var pa vag att
# skriva `VC_BOOLSIGNAL` i alla tre scenfilerna - ett forkortat konstantnamn som
# INTE finns. Ett uppslag stoppade det tre ganger. Samma fel i den har tabellen
# hade spridit sig till varje datablad i stallet, och provet ar det som gor att
# det inte kan.
#
# Vad provet INTE visar: att avbildningen ar RATT. Att VC_BOOLEANSIGNAL finns
# bevisar inte att det ar just den konstant findBehavioursByType vill ha for
# rSimBoolSignal. Den kontrollen kraver ett kort VC, och den star i M-85:s
# LIMITS.
HARLEDD = "harledd"     # rsc-namnet normaliserar EXAKT till en kand konstant
HANDSATT = "handsatt"   # namnen skiljer sig; avbildningen ar ett pastaende


def harled_konstant(rsc_typ: str) -> str:
    """Konstantnamnet som rsc-typen normaliserar till.

    Regeln, och den ar hela poangen med att den star som KOD och inte i en
    kommentar: stryk ledande `rSim` eller `r`, versalisera, satt `VC_` framfor.
    `rOneWayPath` -> `VC_ONEWAYPATH`. Provet
    test_harledda_avbildningar_harleds_verkligen kor den har funktionen mot
    varje HARLEDD post, sa en post som pastar sig vara harledd men inte ar det
    faller.
    """
    bas = rsc_typ
    for prefix in ("rSim", "r"):
        if bas.startswith(prefix):
            bas = bas[len(prefix):]
            break
    return "VC_" + bas.upper()


# Filformatet skriver `Functionality "rSimBoolSignal"`. Pythonsidan heter
# `VC_BOOLEANSIGNAL`. Det ar TVA NAMNRYMDER, och ingen kalla vi har - varken
# api.xml, constants.xml eller komponentfilerna - skriver ut avbildningen
# mellan dem. Tabellen ar darfor delvis harledd och delvis ett PASTAENDE, och
# varje post bar vilket den ar.
#
# TRE PROV HALLER DEN ARLIG (tests/enhet/test_komponentdatablad.py):
#
#   test_varje_konstant_finns_i_constants_xml   varje VC_-namn maste sta i
#                                               docs/referens/vc_api/constants.xml
#   test_harledda_avbildningar_harleds_verkligen  en HARLEDD post maste falla ut
#                                               ur harled_konstant()
#   test_handsatta_avbildningar_harleds_inte    en HANDSATT post far INTE gora
#                                               det - annars ska den vara HARLEDD
#
# Det forsta provet ar inte formalia. Den forsta versionen av den har tabellen
# innehöll `VC_PROCESS`, som INTE finns bland constants.xml:s 709 konstanter -
# samma felklass som M-84 matte hos modellen, som var pa vag att skriva
# `VC_BOOLSIGNAL` i tre scenfiler innan ett uppslag stoppade den. Provet fallde
# min egen variant av exakt det felet innan tabellen anvants en enda gang.
#
# Sju nycklar ur den forsta versionen ar OCKSA borta: rSimComponentContainer,
# rSimComponentSignal, rSimMatrixSignal, rSimProcess, rSimRealSignal,
# rSimServoController och rSimToolContainer. De forekom i NOLL av 3201
# komponenter (M-85) - jag hade hittat pa filformatets namn ur Python-sidans.
# Ett namn som ingen fil bar gar inte att kontrollera, och det ar just darfor
# det hade overlevt.
#
# Vad proven INTE visar: att en avbildning ar RATT. Att VC_BOOLEANSIGNAL finns
# bevisar inte att det ar just den konstant findBehavioursByType vill ha for
# rSimBoolSignal. Den kontrollen kraver ett kort VC, och den star i M-85:s
# LIMITS.
API_TYP: Dict[str, Tuple[str, str]] = {
    # ---- harledda: rsc-namnet ger konstanten rakt av ----
    "rPythonScript": ("VC_PYTHONSCRIPT", HARLEDD),
    "rSimStatistics": ("VC_STATISTICS", HARLEDD),
    "rRobotExecutor": ("VC_ROBOTEXECUTOR", HARLEDD),
    "rSimRobotController": ("VC_ROBOTCONTROLLER", HARLEDD),
    "rActionContainer": ("VC_ACTIONCONTAINER", HARLEDD),
    "rPythonKinematics": ("VC_PYTHONKINEMATICS", HARLEDD),
    "rSimRrsRobotController": ("VC_RRSROBOTCONTROLLER", HARLEDD),
    "rSimStringSignal": ("VC_STRINGSIGNAL", HARLEDD),
    "rSimContainer": ("VC_CONTAINER", HARLEDD),
    "rOneWayPath": ("VC_ONEWAYPATH", HARLEDD),
    "rToolContainer": ("VC_TOOLCONTAINER", HARLEDD),
    "rTwoWayPath": ("VC_TWOWAYPATH", HARLEDD),
    "rProcessExecutor": ("VC_PROCESSEXECUTOR", HARLEDD),
    "rTransportNode": ("VC_TRANSPORTNODE", HARLEDD),
    "rJogInfo": ("VC_JOGINFO", HARLEDD),
    "rPythonProcessHandler": ("VC_PYTHONPROCESSHANDLER", HARLEDD),
    "rNote": ("VC_NOTE", HARLEDD),
    "rBaseContainer": ("VC_BASECONTAINER", HARLEDD),
    "rProductCreator": ("VC_PRODUCTCREATOR", HARLEDD),
    "rPythonTransportController": ("VC_PYTHONTRANSPORTCONTROLLER", HARLEDD),
    "rRayCastSensor": ("VC_RAYCASTSENSOR", HARLEDD),
    "rSimPatternContainer": ("VC_PATTERNCONTAINER", HARLEDD),
    "rContainerFiller": ("VC_CONTAINERFILLER", HARLEDD),

    # ---- handsatta: namnen skiljer sig, och skalet star per rad ----
    # Bool i filen, BOOLEAN i konstanten. VC_BOOLEANSIGNAL ar den ENDA
    # boolska signalkonstanten bland de 709.
    "rSimBoolSignal": ("VC_BOOLEANSIGNAL", HANDSATT),
    "rSimBoolSignalMap": ("VC_BOOLEANSIGNALMAP", HANDSATT),
    # Int i filen, INTEGER i konstanten. Enda heltalssignalkonstanten.
    "rSimIntSignal": ("VC_INTEGERSIGNAL", HANDSATT),
    # Double i filen, REAL i konstanten. Enda reellvarda signalkonstanten.
    "rSimDoubleSignal": ("VC_REALSIGNAL", HANDSATT),
    # Filen sager bara "Interface". Konstanterna skiljer ETT-TILL-ETT fran
    # ETT-TILL-MANGA, och det ar `rSimDynamicInterface` som bar
    # TemplateSection - alltsa den som kan koppla flera.
    "rSimInterface": ("VC_ONETOONEINTERFACE", HANDSATT),
    "rSimDynamicInterface": ("VC_ONETOMANYINTERFACE", HANDSATT),
    # `rSimKinController` heter "Servo Controller" i komponenternas EGNA
    # Name-falt (AccuVeyor AVh och 509 andra), och VC_SERVOCONTROLLER ar den
    # konstant som svarar mot det namnet. Stodet ar alltsa filens eget namn,
    # inte en likhet mellan typnamnen.
    "rSimKinController": ("VC_SERVOCONTROLLER", HANDSATT),
}

# MATT i M-85: de har trettio posterna tacker 92,8 procent av bibliotekets
# 31403 beteendeforekomster. Biblioteket bar 44 distinkta beteendetyper, och de
# 14 som INTE star har - rKinArticulated2 (1231 komponenter), rKinScara2 (406),
# rSimResourcePtrSignal (157), rResourceSensor (80), rCustomFunctionality (72)
# och nio till - ger `saknas`. De ar till storsta delen kinematik, som ingen
# skriver findBehavioursByType pa; namnet gar anda att fa, med
# findBehaviour(namn).


def api_konstant(rsc_typ: str) -> str:
    """VC_-konstanten for en rsc-beteendetyp, eller "" nar ingen ar kand."""
    post = API_TYP.get(rsc_typ)
    return post[0] if post else ""


def api_harkomst(rsc_typ: str) -> str:
    """HARLEDD, HANDSATT, eller "" nar typen inte star i tabellen."""
    post = API_TYP.get(rsc_typ)
    return post[1] if post else ""


# Beteenden som ar SIGNALER. Ordningen i listan `Datablad.signaler` ar filens
# egen, och det ar just den fragan M-84 lamnade oppen.
SIGNALTYPER = ("rSimBoolSignal", "rSimRealSignal", "rSimIntSignal",
               "rSimStringSignal", "rSimMatrixSignal", "rSimComponentSignal")

# Beteenden som ar GRANSSNITT: det ar de som kan kopplas till en annan komponent.
GRANSSNITTSTYPER = ("rSimInterface", "rSimDynamicInterface")

# Falt vi plockar ur ett beteende, per beteendetyp. Ett falt som inte star har
# hamnar inte i databladet - inte for att det saknas i filen, utan for att
# databladet ska ga att lasa. `ovriga_falt` raknar hur manga som utelamnades,
# sa att den som laser vet att listan inte ar uttommande.
_BETEENDEFALT = {
    "rOneWayPath": ("Speed", "Capacity", "Accumulate", "Direction",
                    "Interpolation", "RetainOffset"),
    "rTwoWayPath": ("Speed", "Capacity", "Accumulate", "Direction",
                    "Interpolation", "RetainOffset"),
    "rSimBoolSignal": ("AutomaticReset",),
    "rSimRealSignal": ("AutomaticReset",),
    "rSimComponentContainer": ("Capacity",),
    "rRobotExecutor": ("Controller", "SignalMapDigitalIn",
                       "SignalMapDigitalOut", "IsLooping", "IsEnabled"),
    "rSimRobotController": ("Controller",),
    "rSimBoolSignalMap": ("Ports", "StartIndex", "Direction"),
}

# Egenskaper som varje komponent bar och som darfor inte sager nagot om NAGON.
# `Visible` finns i rotens variabelrymd i praktiskt taget alla komponenter.
_OINTRESSANTA_EGENSKAPER = ("Visible",)


# ---------------------------------------------------------------------------
# Databladets delar
# ---------------------------------------------------------------------------

@dataclass
class Egenskap:
    """En av komponentens EGNA egenskaper, ur rotens variabelrymd."""

    namn: str
    typ: str                        # rDouble, rBool, rString, rInt, ...
    varde: Optional[str] = None     # deklarerat standardvarde, None = saknas
    kvantitet: str = ""             # Quantity "Distance" - en STORHET, ej enhet
    steg: List[str] = field(default_factory=list)   # tillatna varden
    skrivbar: Optional[bool] = None
    synlig: Optional[bool] = None
    behallare: str = ""             # rTVariable, rTStepVariable, rTPointerList...

    def deklarerad_typ(self) -> str:
        """Typen som KALLAN skriver den, sa att en lista syns som en lista."""
        if not self.typ:
            return SAKNAS
        if self.behallare and self.behallare != "rTVariable":
            return "%s<%s>" % (self.behallare, self.typ)
        return self.typ

    def rad(self) -> str:
        d = ["%s : %s" % (self.namn, self.deklarerad_typ())]
        d.append("standard %s" % (SAKNAS if self.varde is None else self.varde))
        d.append("storhet %s" % (self.kvantitet or SAKNAS))
        if self.steg:
            d.append("varden {%s}" % (", ".join(self.steg[:8])
                                      + (" ..." if len(self.steg) > 8 else "")))
        if self.skrivbar is None:
            d.append("redigerbarhet %s i Settings" % SAKNAS)
        return " | ".join(d)


@dataclass
class Beteende:
    """Ett beteende pa komponenten, med sitt namn - det ar namnet som behovs."""

    typ: str                        # rSimBoolSignal
    namn: str
    api_typ: str = ""               # VC_BOOLEANSIGNAL, "" = ingen avbildning
    falt: Dict[str, str] = field(default_factory=dict)
    ovriga_falt: int = 0

    def rad(self) -> str:
        d = ['"%s"' % self.namn, self.typ,
             self.api_typ or ("%s (%s)" % (SAKNAS, "ingen avbildning i API_TYP"))]
        for k in sorted(self.falt):
            d.append("%s=%s" % (k, self.falt[k]))
        return " | ".join(d)


@dataclass
class Sektionsfalt:
    typ: str                        # rSimFlowField, rSimSignalField, ...
    namn: str
    mot: str = ""                   # Func/Signal/Node - vad faltet pekar pa


@dataclass
class Granssnitt:
    """Ett granssnitt: vad komponenten kan kopplas till, och med vad."""

    namn: str
    typ: str
    api_typ: str = ""
    abstrakt: bool = False
    sektioner: List[Tuple[str, List[Sektionsfalt]]] = field(default_factory=list)

    def rad(self) -> str:
        sek = []
        for namn, falt in self.sektioner:
            f = ", ".join("%s:%s" % (x.namn, x.typ) for x in falt) or SAKNAS
            sek.append("%s[%s]" % (namn or "(namnlos)", f))
        return '"%s" | %s | %s | %s' % (
            self.namn, self.typ, self.api_typ or SAKNAS,
            " ".join(sek) if sek else "inga sektioner")


@dataclass
class Led:
    """En led ur en rSimLink-nod. Robotens axelgranser hor till databladet."""

    namn: str
    dof: str = ""                   # Rotational / Translational
    min_grans: str = ""             # ur MinLimit { Expression "-170" }
    max_grans: str = ""
    max_hastighet: str = ""
    max_acceleration: str = ""

    def rad(self) -> str:
        # Ingen enhet skrivs ut. Granserna ar UTTRYCK i filen ("-170", men
        # ocksa "Axis2>0?(-0.35*Axis2+64.412):70"), och vilken enhet de bar
        # star inte dar. En rotationsled i grader och en linjarled i
        # millimeter ser likadana ut har, och det ska de gora.
        return "%s | %s | granser %s .. %s | maxhastighet %s | maxacc %s" % (
            self.namn, self.dof or SAKNAS,
            self.min_grans or SAKNAS, self.max_grans or SAKNAS,
            self.max_hastighet or SAKNAS, self.max_acceleration or SAKNAS)


@dataclass
class Datablad:
    """Allt databladet vet om EN komponent, plus vad det inte vet.

    Tva kallor, och de bar olika saker (M-76):

      model.xml       katalogposten, 2-3 kB, finns i 3201 av 3201. DEKLARERADE
                      falt: tillverkare, MaxPayload, Reach, taggar, utfasad.
      component.rsc   modellen, 200-300 kB. Komponentens INRE: egenskaperna,
                      beteendena vid namn, granssnitten och lederna.

    `MaxPayload` stod pa M-84:s lista over namn modellen inte var saker pa. Det
    ar inte en egenskap i rotens variabelrymd - det ar ett deklarerat falt i
    katalogposten, och det ar precis darfor det inte gick att hitta genom att
    leta bland egenskaper.
    """

    namn: str
    sokvag: str
    vcid: str = ""
    kategori: str = ""
    tillverkare: str = ""
    revision: str = ""
    beskrivning: str = ""
    produktfamilj: str = ""
    nyttolast_kg: Optional[float] = None
    rackvidd_mm: Optional[float] = None
    etiketter: str = ""
    forfattare: str = ""
    utfasad: bool = False
    # Tillverkarens EGEN beskrivning ur model.xml. katalogindex utelamnar den
    # med flit - "hundratals ord bruksanvisning per komponent" skulle femdubbla
    # ETT INDEX utan att hjalpa nagon att VALJA (M-60). For ETT datablad ar den
    # tvartom det mest varda i filen: manga tillverkare skriver en
    # "### Key properties ###"-rubrik och listar egenskaperna med sin BETYDELSE,
    # vilket ingen struktur i component.rsc bar.
    katalogbeskrivning: str = ""
    # De ORDAGRANNA strangarna ur model.xml, med sina egna nycklar i gemener.
    # Faltnamnen ovan (`nyttolast_kg`, `rackvidd_mm`) bar en enhet i SITT EGET
    # NAMN som katalogposten aldrig deklarerar - filen skriver talet och
    # ingenting mer (M-85). Den som behover talet ORDAGRANT, utan den pahangda
    # enheten och utan float-omvandlingen, laser det harifran. M-107 bygger
    # lagen enhet_saknas pa exakt den skillnaden: `MaxPayload = 0` ska kunna
    # visas som "0" utan att nagon rad i systemet kan gora det till "0 kg".
    katalogfalt: Dict[str, str] = field(default_factory=dict)
    egenskaper: List[Egenskap] = field(default_factory=list)
    beteenden: List[Beteende] = field(default_factory=list)
    granssnitt: List[Granssnitt] = field(default_factory=list)
    leder: List[Led] = field(default_factory=list)
    olasta: List[str] = field(default_factory=list)

    # ---- de fragor M-84 lamnade oppna ----

    def signaler(self) -> List[Beteende]:
        """Signalbeteendena i FILENS ordning."""
        return [b for b in self.beteenden if b.typ in SIGNALTYPER]

    def signaler_av_typ(self, typ: str) -> List[Beteende]:
        return [b for b in self.beteenden if b.typ == typ]

    def egenskap(self, namn: str) -> Optional[Egenskap]:
        n = (namn or "").strip().lower()
        for e in self.egenskaper:
            if e.namn.lower() == n:
                return e
        return None

    def egenskaper_som_namner(self, ord_: str) -> List[Egenskap]:
        o = (ord_ or "").strip().lower()
        return [e for e in self.egenskaper if o and o in e.namn.lower()]


# ---------------------------------------------------------------------------
# Lasningen
# ---------------------------------------------------------------------------

def _sant(varde: str) -> Optional[bool]:
    v = (varde or "").strip().lower()
    if v in ("1", "true", "yes"):
        return True
    if v in ("0", "false", "no"):
        return False
    return None


def _variabel(text: str, d: Del) -> Optional[Egenskap]:
    """En `Variable "rTVariable<rDouble>"`-post ur en variabelrymd."""
    behallare, _sep, resten = d.arg(0).partition("<")
    typ = resten[:-1] if resten.endswith(">") else resten
    namn = ""
    varde = None
    kvantitet = ""
    steg: List[str] = []
    synlig = None
    skrivbar = None
    if not d.har_kropp:
        return None
    for b in delar(text, d.kropp[0], d.kropp[1]):
        if b.nyckel == "Name":
            namn = b.arg(0)
        elif b.nyckel == "Value":
            if b.har_kropp:
                # Ett strukturerat varde (uttryck, pekarlista). Vi skriver ut
                # det inre uttrycket nar det finns, annars sags det saknas -
                # aldrig en tom strang, som lases som "tomt varde".
                inre = [x for x in delar(text, b.kropp[0], b.kropp[1])]
                uttryck = [x.arg(0) for x in inre if x.nyckel == "Expression"]
                varde = uttryck[0] if uttryck and uttryck[0] else None
            else:
                varde = b.arg(0) if b.argument else None
        elif b.nyckel == "Quantity":
            kvantitet = b.arg(0)
        elif b.nyckel == "StepList" and b.har_kropp:
            for s in delar(text, b.kropp[0], b.kropp[1]):
                if s.nyckel == "Step" and s.har_kropp:
                    for sv in delar(text, s.kropp[0], s.kropp[1]):
                        if sv.nyckel == "Value":
                            steg.append(sv.arg(0))
        elif b.nyckel == "Settings" and b.har_kropp:
            flaggor = set()
            for f in delar(text, b.kropp[0], b.kropp[1]):
                flaggor.add(f.nyckel)
            synlig = "VISIBLE" in flaggor
            # SANT nar filen deklarerar redigerbarhet, annars None. ALDRIG
            # False: att flaggan inte star dar betyder att filen inte sager
            # nagot, inte att egenskapen ar skrivskyddad. 210 av bibliotekets
            # egenskaper saknar flaggan helt (M-85), och att kalla dem
            # "lasbara endast" hade varit ett pastaende kallan inte gor.
            skrivbar = (True if (flaggor & {"EDITABLE_DISCONNECTED",
                                            "EDITABLE_CONNECTED",
                                            "EDITABLE_SIMULATING"})
                        else None)
    if not namn:
        return None
    return Egenskap(namn=namn, typ=typ, varde=varde, kvantitet=kvantitet,
                    steg=steg, skrivbar=skrivbar, synlig=synlig,
                    behallare=behallare)


def _sektionsfalt(text: str, d: Del) -> List[Sektionsfalt]:
    ut: List[Sektionsfalt] = []
    if not d.har_kropp:
        return ut
    for f in delar(text, d.kropp[0], d.kropp[1]):
        if not f.har_kropp:
            continue
        namn = ""
        mot = ""
        for x in delar(text, f.kropp[0], f.kropp[1]):
            if x.nyckel == "Name":
                namn = x.arg(0)
            elif x.nyckel in ("Func", "Signal", "Node", "Controller",
                              "Container", "Path"):
                mot = "%s=%s" % (x.nyckel, x.arg(0))
        ut.append(Sektionsfalt(typ=f.nyckel, namn=namn, mot=mot))
    return ut


def _funktionalitet(text: str, d: Del):
    """Ett `Functionality`-block -> Beteende, och Granssnitt nar det ar ett."""
    typ = d.arg(0)
    namn = ""
    abstrakt = False
    falt: Dict[str, str] = {}
    onskade = _BETEENDEFALT.get(typ, ())
    sektioner: List[Tuple[str, List[Sektionsfalt]]] = []
    ovriga = 0
    if d.har_kropp:
        for b in delar(text, d.kropp[0], d.kropp[1]):
            if b.nyckel == "Name" and not namn:
                namn = b.arg(0)
            elif b.nyckel == "Abstract":
                abstrakt = _sant(b.arg(0)) is True
            elif b.nyckel in ("Section", "TemplateSection"):
                snamn = ""
                sfalt: List[Sektionsfalt] = []
                if b.har_kropp:
                    for s in delar(text, b.kropp[0], b.kropp[1]):
                        if s.nyckel == "Name":
                            snamn = s.arg(0)
                        elif s.nyckel == "Fields":
                            sfalt.extend(_sektionsfalt(text, s))
                sektioner.append((snamn, sfalt))
            elif b.nyckel in onskade and not b.har_kropp:
                falt[b.nyckel] = b.arg(0)
            elif not b.har_kropp and b.nyckel not in ("Id", "Visible", "Flags",
                                                      "Name"):
                ovriga += 1
    api = api_konstant(typ)
    beteende = Beteende(typ=typ, namn=namn, api_typ=api, falt=falt,
                        ovriga_falt=ovriga)
    gr = None
    if typ in GRANSSNITTSTYPER:
        gr = Granssnitt(namn=namn, typ=typ, api_typ=api, abstrakt=abstrakt,
                        sektioner=sektioner)
    return beteende, gr


def _leder(text: str, d: Del, ut: List[Led]) -> None:
    """Samla lederna ur en `Node "rSimLink"` och dess barnlankar.

    Kedjan ar NASTAD i filen: Axis2 ligger inne i Axis1, Axis3 inne i Axis2.
    En platt lasning av rotnodens direkta barn ser darfor exakt EN lank, och
    den forsta versionen av den har funktionen gjorde just det - den svarade
    "0 leder" pa en sexaxlig ABB-robot. Felet syntes inte som ett undantag
    utan som ett trovardigt tal, vilket ar varfor tackningsmatningen i M-85
    raknar leder per robot och inte bara "gick det att lasa".

    Leddatan sitter i lankens `Dof`-block:

        Dof "Rotational"
        {
          VariableSpace { ... MaxSpeed ... }
          MinLimit { Expression "-170" }
          MaxLimit { Expression "170" }
        }

    En lank UTAN Dof-block ar ingen led (den ar en stel del av kroppen) och
    hoppas over - inte en led med tomma granser, som hade sett ut som en led
    utan granser.
    """
    if not d.har_kropp:
        return
    namn = ""
    led: Optional[Led] = None
    barn: List[Del] = []
    for b in delar(text, d.kropp[0], d.kropp[1]):
        if b.nyckel == "Name" and not namn:
            namn = b.arg(0)
        elif b.nyckel == "NodeClass":
            continue                        # geometrin
        elif b.nyckel == "Node":
            barn.append(b)
        elif b.nyckel == "Dof" and b.har_kropp:
            led = Led(namn=namn, dof=b.arg(0))
            for j in delar(text, b.kropp[0], b.kropp[1]):
                if j.nyckel == "Name" and j.argument:
                    led.namn = j.arg(0)     # ledens eget namn, inte lankens
                elif j.nyckel == "Properties" and j.har_kropp:
                    for vd in delar(text, j.kropp[0], j.kropp[1]):
                        if vd.nyckel != "Variable":
                            continue
                        e = _variabel(text, vd)
                        if e is None:
                            continue
                        if e.namn == "MaxSpeed":
                            led.max_hastighet = e.varde or ""
                        elif e.namn == "MaxAcceleration":
                            led.max_acceleration = e.varde or ""
                elif j.nyckel in ("MinLimit", "MaxLimit") and j.har_kropp:
                    uttryck = [x.arg(0) for x in
                               delar(text, j.kropp[0], j.kropp[1])
                               if x.nyckel == "Expression"]
                    v = uttryck[0] if uttryck else ""
                    if j.nyckel == "MinLimit":
                        led.min_grans = v
                    else:
                        led.max_grans = v
    if led is not None:
        if not led.namn:
            led.namn = namn
        ut.append(led)
    for b in barn:
        _leder(text, b, ut)


def _rotnod(text: str) -> Optional[Del]:
    """Rotnoden `Node "rSimResource"`, eller None."""
    for d in delar(text, 0, len(text)):
        if d.nyckel == "Node" and d.har_kropp:
            return d
    return None


def las_text(text: str, sokvag: str = "", tillverkare: str = "") -> Datablad:
    """Databladet ur en component.rsc som redan ar last till en strang."""
    rot = _rotnod(text)
    if rot is None:
        raise Databladfel("ingen rotnod (Node) i component.rsc")
    blad = Datablad(namn="", sokvag=sokvag, tillverkare=tillverkare)
    for d in delar(text, rot.kropp[0], rot.kropp[1]):
        n = d.nyckel
        if n == "NodeClass":
            continue                        # geometrin, avsiktligt oläst
        if n == "Name" and not blad.namn:
            blad.namn = d.arg(0)
        elif n == "VCID":
            blad.vcid = d.arg(0)
        elif n == "Category":
            blad.kategori = d.arg(0)
        elif n == "Revision":
            blad.revision = d.arg(0)
        elif n == "ProductFamily":
            blad.produktfamilj = d.arg(0)
        elif n == "BOMdescription":
            # Bakstreck-radbrytning ar formatets radfortsattning, inte text.
            blad.beskrivning = " ".join(d.arg(0).replace("\\\n", "").split())
        elif n == "Functionality":
            beteende, gr = _funktionalitet(text, d)
            blad.beteenden.append(beteende)
            if gr is not None:
                blad.granssnitt.append(gr)
        elif n == "VariableSpace" and d.har_kropp and not blad.egenskaper:
            for vd in delar(text, d.kropp[0], d.kropp[1]):
                if vd.nyckel != "Variable":
                    continue
                e = _variabel(text, vd)
                if e is None:
                    blad.olasta.append("en Variable utan Name i rotens "
                                       "variabelrymd")
                elif e.namn not in _OINTRESSANTA_EGENSKAPER:
                    blad.egenskaper.append(e)
        elif n == "Node":
            _leder(text, d, blad.leder)
    if not blad.namn:
        blad.olasta.append("Name i rotnoden")
    return blad


_KATALOGFALT = re.compile(r'<Property name="([^"]+)">(.*?)</Property>', re.S)


def _tal(varde) -> Optional[float]:
    """Ett tal ur ett deklarerat falt, eller None.

    None och inte 0.0: en robot utan angiven nyttolast bar inte nyttolasten
    noll. Samma regel som katalogindex._tal, och av samma skal.
    """
    try:
        return float(str(varde).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _katalogpost(z) -> Dict[str, str]:
    """De deklarerade falten ur model.xml, eller {} nar posten saknas."""
    if KATALOGPOST not in z.namelist():
        return {}
    try:
        rå = z.read(KATALOGPOST).decode("utf-8", "replace")
    except (KeyError, OSError):
        return {}
    ut: Dict[str, str] = {}
    for namn, varde in _KATALOGFALT.findall(rå):
        # Falten star i bada skiftlagen i biblioteket (imageuri mot ImageUri).
        v = varde.strip()
        if v:
            ut[namn.lower()] = v
    return ut


def las(vcmx: str, tillverkare: str = "") -> Datablad:
    """Databladet ur en .vcmx pa disk: bada metadataposterna.

    `tillverkare` anvands bara nar katalogposten inte deklarerar en - det ar
    katalogtradets katalognamn, och det ar en SAMRE kalla an det deklarerade
    faltet (M-76). Att den gar att skicka in gor att den som redan vet slipper
    gissa, inte att modulen gissar.
    """
    if not os.path.exists(vcmx):
        raise Databladfel("ingen fil pa %s" % vcmx)
    try:
        with zipfile.ZipFile(vcmx) as z:
            kat = _katalogpost(z)
            if METADATA not in z.namelist():
                raise Databladfel("%s saknar %s" % (vcmx, METADATA))
            text = z.read(METADATA).decode("utf-8", "replace")
    except zipfile.BadZipFile as fel:
        raise Databladfel("%s gar inte att oppna som arkiv: %s" % (vcmx, fel))
    blad = las_text(text, sokvag=vcmx)
    blad.katalogfalt = dict(kat)
    blad.tillverkare = kat.get("manufacturer") or tillverkare
    blad.nyttolast_kg = _tal(kat.get("maxpayload"))
    blad.rackvidd_mm = _tal(kat.get("reach"))
    blad.etiketter = kat.get("tags", "")
    blad.katalogbeskrivning = kat.get("description", "")
    blad.forfattare = kat.get("author", "")
    blad.utfasad = str(kat.get("isdeprecated", "")).strip().lower() == "true"
    if kat.get("name"):
        blad.namn = kat["name"]
    if not kat:
        blad.olasta.append("model.xml (katalogposten): tillverkare, MaxPayload, "
                           "Reach, taggar och utfasad-flaggan gar darfor inte "
                           "att lasa")
    return blad


# ---------------------------------------------------------------------------
# Formen: databladet som text en sprakmodell kan lasa
# ---------------------------------------------------------------------------
#
# Samma tre regler som katalogsok.py foljer, av samma skal:
#
#   1. RADER, inte JSON. En rad per egenskap, fasta falt.
#   2. Kapa pa ANTAL POSTER, aldrig mitt i en struktur. Felet ar redan gjort en
#      gang i det har repot: slaupp.py skivade JSON-strangen pa TECKEN och gav
#      utdata som var lasbar for ett oga men oparsbar for allt annat. Provet
#      som star kvar heter test_slaupp.py::test_kapning_ger_giltig_json.
#   3. Ett falt kallan inte bar sags `saknas`. Aldrig noll, aldrig tomt.
#
# En kapad lista sager ALLTID hur manga som inte visades. Ett svar som inte
# sager vad det utelamnade ser uttommande ut, och det ar samma tysta lognen
# som ett utelamnat falt.

# Standardtak per avsnitt, ett per avsnitt och alla ur SAMMA regel:
#
#     taket ar p90 for avsnittets EGEN fordelning over biblioteket.
#
# Nio komponenter av tio kommer alltsa igenom HELA, och den tionde far veta
# exakt hur manga rader som inte visades. Ett gemensamt tak hade varit fel
# storhet: fordelningarna ar helt olika (M-85, 3201 komponenter):
#
#     egenskaper   median 21  p90  47  p99 103  max 110
#     beteenden    median 11  p90  12  p99  20  max  59
#     granssnitt   median  3  p90   3  p99   5  max  23
#     leder        median  6  p90  17  p99  71  max  88
#
# Beteendena far p99 och inte p90 i alla fall: p90 ar 12, men det ar just
# beteendelistan som bar SVARET pa M-84:s oppna fraga (vilken signal heter
# vad), och skillnaden mellan 12 och 20 rader ar under tusen tecken.
MAX_EGENSKAPER = 47             # p90, satt av M-85.
MAX_BETEENDEN = 20              # p99, satt av M-85.
MAX_GRANSSNITT = 5              # p99, satt av M-85 - samma skal
                                # som beteendena: 'vad kan den kopplas
                                # till' ar en namngiven leverans, och
                                # tva extra rader kostar 300 tecken.
MAX_LEDER = 17                  # p90, satt av M-85.

# Tillverkarens beskrivning ar fritext och kapas darfor pa TECKEN - den har
# ingen struktur att kapa pa. Det ar tillatet just for att den star SIST i
# svaret och inte kan skiva nagon annan post. MATT i M-85: 2130 av 3201
# beskrivningar ar exakt 1179 tecken (samma mall aterkommer), p99 ar 1275 och
# max 2083. Taket ligger over p99 sa att naveln pa fordelningen kommer igenom
# hel.
MAX_BESKRIVNING = 1300          # p99, satt av M-85.


def _avsnitt(rubrik: str, rader: List[str], tak: int, tomt: str) -> List[str]:
    """Ett kapat avsnitt som sager vad det inte visade."""
    if not rader:
        return ["%s: %s (%s)" % (rubrik, SAKNAS, tomt)]
    ut = ["%s (%d st):" % (rubrik, len(rader))]
    ut.extend("  " + r for r in rader[:tak])
    if len(rader) > tak:
        ut.append("  ... %d till, ej visade. Kapat pa ANTAL POSTER, sa ingen "
                  "rad ar halv." % (len(rader) - tak))
    return ut


def text(blad: Datablad,
         max_egenskaper: int = MAX_EGENSKAPER,
         max_beteenden: int = MAX_BETEENDEN,
         max_granssnitt: int = MAX_GRANSSNITT,
         max_leder: int = MAX_LEDER) -> str:
    """Databladet som text.

    Ordningen ar vald efter vad som avgor om en genererad rad KOR: namnet
    forst, sedan egenskaperna (det ar de `getProperty` slar upp), sedan
    signalerna vid namn, sedan granssnitten.
    """
    r = ["KOMPONENT: %s" % (blad.namn or SAKNAS),
         "tillverkare: %s" % (blad.tillverkare or SAKNAS),
         "kategori: %s" % (blad.kategori or SAKNAS),
         "produktfamilj: %s" % (blad.produktfamilj or SAKNAS),
         "VCID: %s" % (blad.vcid or SAKNAS),
         "revision: %s" % (blad.revision or SAKNAS),
         # Deklarerade katalogfalt (model.xml). MaxPayload och Reach ar INTE
         # egenskaper i variabelrymden - de star i katalogposten, och det ar
         # darfor de inte gar att hitta bland egenskaperna nedan.
         # Vardet ordagrant, utan pahangd enhet. model.xml deklarerar TALET
         # och ingenting mer: det star inget "mm" och inget "kg" i filen.
         # Repots katalogskikt (katalogsok.Traff.rad) skriver ut dem som mm
         # och kg, och den tolkningen kommer darifran - inte harifran.
         "MaxPayload (deklarerat falt i katalogposten, ENHET EJ DEKLARERAD "
         "i filen): %s"
         % ("%g" % blad.nyttolast_kg if blad.nyttolast_kg is not None
            else SAKNAS),
         "Reach (deklarerat falt i katalogposten, ENHET EJ DEKLARERAD i "
         "filen): %s"
         % ("%g" % blad.rackvidd_mm if blad.rackvidd_mm is not None
            else SAKNAS),
         "taggar: %s" % (blad.etiketter or SAKNAS),
         "utfasad av tillverkaren: %s" % ("JA" if blad.utfasad else "nej"),
         "fil: %s" % (blad.sokvag or SAKNAS),
         "beskrivning: %s" % (blad.beskrivning or SAKNAS),
         "",
         "ENHETER: kallan deklarerar en STORHET per egenskap (Distance, "
         "Velocity, Angle, Time ...), inte en enhet. Storheten star nedan "
         "ordagrant. Star det `storhet saknas` sager filen ingenting, och "
         "talet far da INTE forses med en enhet - VC:s varldsenhet ar "
         "millimeter, men vilken enhet just den variabeln bar ar inte "
         "deklarerad.",
         ""]

    r.extend(_avsnitt("EGENSKAPER (det getProperty(namn) slar upp)",
                      [e.rad() for e in blad.egenskaper], max_egenskaper,
                      "rotens variabelrymd bar inga egna egenskaper"))
    r.append("")

    signaler = blad.signaler()
    if signaler:
        r.append("SIGNALER, i filens ordning (%d st):" % len(signaler))
        for i, s in enumerate(signaler):
            r.append('  [%d] "%s" : %s -> %s'
                     % (i, s.namn, s.typ, s.api_typ or SAKNAS))
        # M-84 lamnade exakt den har fragan oppen. Svaret ar entydigt bara nar
        # det finns EN signal av typen; med flera hanger [0] pa en ordning som
        # inte ar verifierad mot ett kort VC.
        for typ in sorted({s.typ for s in signaler}):
            av_typ = blad.signaler_av_typ(typ)
            konst = api_konstant(typ) or SAKNAS
            if len(av_typ) == 1:
                r.append('  findBehavioursByType(%s)[0] ar "%s" - komponenten '
                         "bar bara en av den typen, sa indexet spelar ingen roll."
                         % (konst, av_typ[0].namn))
            else:
                r.append("  findBehavioursByType(%s) ger %d stycken: %s. VILKEN "
                         "som ar [0] gar INTE att lasa ur filen - ordningen har "
                         "ar filens, och att den ar samma som API:ets ar inte "
                         "matt. Anvand findBehaviour(namn) i stallet."
                         % (konst, len(av_typ),
                            ", ".join('"%s"' % b.namn for b in av_typ)))
    else:
        r.append("SIGNALER: %s (komponenten bar inga signalbeteenden)" % SAKNAS)
    r.append("")

    r.extend(_avsnitt("BETEENDEN (findBehaviour(namn))",
                      [b.rad() for b in blad.beteenden], max_beteenden,
                      "komponenten bar inga beteenden"))
    r.append("")
    r.extend(_avsnitt("GRANSSNITT (vad den kan kopplas till)",
                      [g.rad() for g in blad.granssnitt], max_granssnitt,
                      "komponenten bar inga granssnitt"))
    if blad.leder:
        r.append("")
        r.extend(_avsnitt("LEDER", [l.rad() for l in blad.leder], max_leder,
                          "inga leder"))
    handsatta = sorted({b.typ for b in blad.beteenden
                        if api_harkomst(b.typ) == HANDSATT})
    if handsatta:
        r.append("")
        r.append("AVBILDNINGAR SOM AR PASTAENDEN, inte harledda ur namnet: %s. "
                 "Filen skriver typnamnet, konstanten star i VC:s Python-API, "
                 "och att de hor ihop ar inte verifierat mot ett kort VC "
                 "(M-85 LIMITS). findBehaviour(namn) beror inte av dem."
                 % ", ".join("%s -> %s" % (x, api_konstant(x))
                             for x in handsatta))
    okanda = sorted({b.typ for b in blad.beteenden if not b.api_typ})
    if okanda:
        r.append("")
        r.append("BETEENDETYPER UTAN KAND API-KONSTANT: %s. Databladet vet vad "
                 "de HETER men inte vilken VC_-konstant findBehavioursByType "
                 "vill ha for dem - anvand findBehaviour(namn)."
                 % ", ".join(okanda))
    if blad.katalogbeskrivning:
        r.append("")
        r.append("TILLVERKARENS EGEN BESKRIVNING (model.xml, Description):")
        d = blad.katalogbeskrivning.strip()
        if len(d) > MAX_BESKRIVNING:
            d = d[:MAX_BESKRIVNING] + ("\n  ... kapad vid %d tecken av %d."
                                       % (MAX_BESKRIVNING,
                                          len(blad.katalogbeskrivning.strip())))
        for rad in d.splitlines():
            r.append("  " + rad)
    if blad.olasta:
        r.append("")
        r.append("EJ LASTA FALT: %s" % "; ".join(blad.olasta))
    return "\n".join(r)
