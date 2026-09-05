# -*- coding: utf-8 -*-
"""Domanen signals: signaler, signalkartor och uppkoppling (45_verktyg.md).

Det har ar driftsattningsingenjorens doman. Den svarar pa fragorna "vilka
signaler finns", "vad star de pa", "hur hanger de ihop" och "vad ska PLC:n
deklarera" - och den ar darfor ravaran till grind 3 i 50_grindar.md:
deklarationerna GENERERAS ur scenens signalkarta, modellen skriver dem
aldrig sjalv (I10).

Tjugoett verktyg, tio lasande och elva skrivande. Tjugo ar kodgenererande,
ett (connectivity_status) ar data.
Skalet till uppdelningen star i 45_verktyg.md: allt som ror SCENEN maste ga
in i VC och fraga, medan det som ror index och matt arkitektur kor i
tjansten och svarar aven nar VC ar nere.


SAKERHETSGRANSEN - det som INTE ar forhandlingsbart
---------------------------------------------------
50_grindar.md och I15 i 90_invarianter.md: "Taggar markta sakerhet ar
skrivskyddade for agenten." Har ar den mekanisk:

  * ar_sakerhetssignal() domer ett namn mot SAKERHETSMARKORER.
  * VARJE skrivande verktyg i domanen kor _sparra() over sina namnbarande
    argument INNAN nagon kod genereras. Ett traffat namn ger Sakerhetsavslag,
    bryggan ror sig inte, och skalet namner markoren.
  * De fyra verktyg som skriver i en SIGNALKARTA bar dessutom en andra halva
    inne i mallen: _sparra_karta() gar igenom kartans portar och kastar om
    nagon av dem bar en sakerhetstagg. Skalet ar en matt lucka i den forsta
    halvan - tjansten domer NAMN, och en karta som heter BoolMap men bar
    EMG_OK pa en port ar lika mycket en skyddskrets. Vad portarna bar vet
    bara VC, sa den halvan maste ligga dar.
  * LASANDE verktyg sparras INTE - man maste kunna SE nodstoppet - men varje
    signalpost bar "safety" och "safety_reason", sa markningen foljer med in
    i PLC-inventeringen i stallet for att ga forlorad.
  * Samma tabell anvands pa bada sidorna: tjansten domer argumenten, och den
    genererade koden domer de namn den hittar i scenen. Tabellen skrivs in i
    mallen ur SAKERHETSMARKORER, sa de tva kan inte drifta isar.

Markningen ar NAMNBASERAD, och det ar en konvention, inget bevis. Den ar
darfor avsiktligt bred: ett falskt avslag kostar en fraga till operatoren,
ett falskt godkannande skriver i en skyddskrets. Felet ska falla at det
hallet. Den riktiga garantin ligger inte har utan i 50_grindar.md:
sakerhetsfunktionen bor pa en certifierad sakerhets-PLC som den genererade
logiken bara far ligga bredvid och vara forreglad av.

Markorernas harkomst star i tabellen sjalv. Tre av dem kommer ur bankens
egen ANLAGGNINGSSIGNALER (bank/schema.py), och tests/enhet/test_verktyg_
signaler.py laser den tuppeln ur kallfilen och kraver att de tre
sakerhetssignalerna dar fastnar medan de fyra ovriga slapps igenom. En
kopierad lista ar tva listor sa fort nagon andrar den ena.


MATT API-YTA, inte ihagkommen
-----------------------------
Allt nedan ar last ur docs/referens/vc_api/ (vc_python_api.json + api.xml),
och det som INTE star dar byggs inte.

  vcSignal (foralder vcBehaviour)   connect, disconnect, AutomaticReset,
                                    Connections, OnValueChange
  vcBoolSignal / vcRealSignal /     signal([value]), Value
  vcIntegerSignal / vcStringSignal /
  vcComponentSignal / vcMatrixSignal
  vcBooleanSignalMap                addPort, connect, disconnect,
                                    getAllConnectedPorts, getPortName,
                                    getInternalPortSignal,
                                    getConnectedExternalSignals,
                                    getConnectedExternalPorts, input, output,
                                    setPortName, setPortSignal,
                                    trySetDirection, Direction, Listeners,
                                    Name, StartIndex, EndIndex, PortCount, Ports
  vcIntergerSignalMap               getPortName, input, output, setPortName,
                                    Listeners, PortCount   (VC:s EGEN stavning
                                    med "Interger" - namnet ar inte vart)
  vcStringSignalMap                 input, output, Listeners, PortCount
  vcNode                            createBehaviour(type, name), findBehaviour,
                                    findBehavioursByType, getBehaviour,
                                    getBehavioursByType, Behaviours
  vcBehaviour                       delete, update, Component, Enabled, Name,
                                    Parent, Properties, Type, World

Konstanter (constants.xml), och exakt dessa:

  signaltyper       VC_BEHAVIOURSIGNAL, VC_BOOLEANSIGNAL, VC_COMPONENTSIGNAL,
                    VC_FRAMESIGNAL, VC_INTEGERSIGNAL, VC_MATRIXSIGNAL,
                    VC_REALSIGNAL, VC_STRINGSIGNAL
  kartor            VC_BOOLEANSIGNALMAP, VC_REALSIGNALMAP
  adapter           VC_PROPERTYSIGNALADAPTER
  riktning          VC_SIGNALMAP_DIRECTION_INPUT / _OUTPUT / _UNDEFINED

MATT ASYMMETRI som verktygen bar: det finns TYPER for vcIntergerSignalMap
och vcStringSignalMap men INGA konstanter att skapa dem med, och det finns
KONSTANTER for VC_REALSIGNALMAP, VC_FRAMESIGNAL, VC_BEHAVIOURSIGNAL och
VC_PROPERTYSIGNALADAPTER utan att nagon typ beskriver deras yta. Darfor kan
create_signal_map bara skapa de tva kartor som har en konstant.


VAD SOM AR KORT I VC, OCH VAD SOM INTE AR DET
---------------------------------------------
Domanens API-yta ar last ur dokumentationen. Tva matningar har dessutom kort
den i en levande VC 4.10 under Wine, och de styr tre beslut har:

  M-13  createBehaviour(VC_BOOLEANSIGNAL, ...) kordes genom kon mot en
        levande simulering: done, simuleringen gick vidare, bryggan svarade.
        createBehaviour(VC_SCRIPT, ...) daremot STOPPADE simuleringen och
        tog ned pumpen mitt i dess eget svar. Darfor: create_signal tar bara
        SIGNALTYPER, aldrig en skripttyp, och tests provar att ingen mall i
        domanen kan skapa ett skriptbeteende.

  M-15  varje beteendekonstant provades med createBehaviour pa en farsk
        komponent. 80 av 244 gick. ALLA atta signaltyper och BADA
        signalkartetyperna finns bland de 80 - det ar matt, inte antaget.
        VC_REALSIGNALMAP kom tillbaka som en bar vcBehaviour, alltsa utan
        egen bindningsklass; om den saknar PortCount, input och output ser
        list_signal_maps den inte, och det ar en oprovad kant.

  M-15  VC_PROPERTYSIGNALADAPTER ar INTE bland de 80 som gick. Antingen
        gav den None som de 164 ovriga, eller sa foll den utanfor svepets
        244 konstanter - matningen skiljer inte pa de tva. At bada hallen ar
        skapandet OPROVAT, och oprovat raknas som saknat (36_versioner.md,
        I3). Domanen har darfor INGET verktyg som skapar en egenskapsadapter:
        ett skrivande verktyg vars centrala anrop troligen ger None skulle
        kosta operatoren ett godkannande per forsok utan att kunna lyckas.
        Adaptern hanteras i stallet som den redan finns i scenen:
        list_property_adapters visar dess EGNA vcProperty-falt, och
        set_behaviour_property satter dem. Faltnamnen kommer alltid ur VC,
        aldrig ur en gissning. Blir adaptern nagon gang matt skapbar ska
        verktyget byggas, och testet som laser M-15 faller den dagen.

Resten av domanen ar INTE kord mot VC. Signalens connect/disconnect, kartans
portmetoder och riktningen ar lasta ur api.xml och oprovade i drift. Att det
inte ar en formalitet visar M-16: canConnect pa ett simuleringsgranssnitt tog
ned bryggan, och det var ett LASANDE anrop. Domanen ar alltsa klar pa
skrivbordet och oprovad i VC, precis som I17 kraver att det uttalas.


VARFOR YTORNA PROVAS PER OBJEKT
-------------------------------
36_versioner.md: koden fragar VAD SOM FINNS. formaga.py provar ATTRIBUT pa
fyra objekt (app, sim, comp, node) och dess YTOR-lista bar ingen signalyta -
den ar harledd ur kolumnen "Bygger pa" i 45_verktyg.md, och signalraderna dar
namnger inga API-ytor. Foljden ar uttalad, inte gomd:

  * kraver-listorna namnger de ytor verktygen FAKTISKT ror och som grinden
    KAN prova: app.Components, app.findComponent, comp.Name, comp.Behaviours,
    comp.findBehaviour, comp.Properties.
  * createBehaviour, Value, Connections, PortCount, Direction och de ovriga
    signalytorna provas i stallet PER OBJEKT i mallen, med hasattr, precis
    som granssnitt.py provar canConnect och Sections. Saknas de kastar
    mallen med ett namngivet skal i stallet for att falla med AttributeError.

Det ar en svagare grind an en yta i formaga.py, och den ar svagare pa ett
matt satt: ett verktyg vars signalyta saknas slas inte AV, det FALLER med
ett begripligt fel. Att laga det kraver en rad i ext/vc_addon/vc_assist/
formaga.py, som ligger utanfor den har cellens skrivstaket.


UPPKOPPLINGEN, OCH VARFOR DEN INTE GAR ATT LASA HARIFRAN
--------------------------------------------------------
60_plc.md: "MATT: VC:s connectivity finns bara i .NET, inte i Python-API:t."
Matningen ar gjord om har: NOLL av de 3444 symbolerna i
svc/vc_assist_svc/api_index.py rar server, anslutning, variabelgrupp eller
OPC UA. Det finns alltsa ingen kodmall som kan lista scenens servrar.

connectivity_status ljuger darfor inte ihop ett svar och lamnar inte heller
en stubbe. Den svarar pa de tre fragorna med den .NET-medlem som BAR svaret,
citerad ur docs/referens/vc_dotnet/, plus den vag som faktiskt ar oppen:
komponentsignalerna, som resten av den har domanen hanterar. Och den bar
arkitekturfaktumet: IOpcUAServer.Session ar en UnifiedAutomation.UaClient.
Session, alltsa ar VC KLIENT och PLC:n server - vilket ar precis varfor
60_plc.md valde OpenPLC v4, den enda gratis mjuk-PLC som ar OPC UA-server.
"""
from __future__ import annotations

import json as _json
import os
import xml.etree.ElementTree as ET

from .bas import (ARG_KOMPONENT, RET_ANTAL, RET_AVKORTAD, SINCE, TIMEOUT_MS,
                  laggare, params, returns, tak)
from .fel import Argumentfel, Schemafel, Verktygsfel
from .kodmall import MAX_POSTER, bygg, lit
from .register import registrera
from .schema import Verktyg

DOMAN = "signals"
_lagg = laggare(DOMAN)


# ==========================================================================
# 1. SAKERHETSGRANSEN
# ==========================================================================

class Sakerhetsavslag(Verktygsfel):
    """Ett skrivande verktyg fick ett namn som ar markt sakerhet (I15).

    Kastas i handlaren, alltsa INNAN nagon kod genereras och innan bryggan
    rors. Bar bade taggen, argumentet den kom in i och markoren som fallde
    den, sa att avslaget gar att forsta utan att lasa specen.
    """

    def __init__(self, verktyg, argument, tagg, skal):
        self.verktyg = verktyg
        self.argument = argument
        self.tagg = tagg
        self.skal = skal
        Verktygsfel.__init__(
            self,
            "%s: %s=%r ar markt sakerhet och far inte skrivas av agenten "
            "(%s). Sakerhetsfunktioner ligger pa certifierad sakerhets-PLC "
            "och skrivs av manniska (50_grindar.md, I15). Las den garna - "
            "lasande verktyg ar inte sparrade."
            % (verktyg, argument, tagg, skal))


# (markor, skal). Markoren jamfors som DELSTRANG mot namnet i versaler.
# Delstrang och inte prefix: ST230_ESTOP_OK ar lika mycket nodstopp som
# ESTOP_OK, och en stationsprefixad tagg ar bankens normalform
# (bank/schema.py: SIGNALMONSTER = ^ST\d{3}_...).
#
# Harkomst per rad. De tre som star "bank/schema.py" ar de av bankens
# ANLAGGNINGSSIGNALER som ar sakerhetsfunktioner; de fyra ovriga i den
# tuppeln (AIR_OK, SYS_AUTO, SYS_RESET, SYS_ALARM) ar det INTE och far inte
# fastna. Bada halvorna provas i test_verktyg_signaler.py mot tuppeln som
# den star i bank/schema.py, sa listan har inte kan drifta fran bankens.
#
# Markorerna ar rena ASCII-versaler, och det ar ett matt val: bankens egen
# signalkonvention ar ASCII-versaler (SIGNALMONSTER ovan), och samma tabell
# ska fungera bade i tjanstens Python 3 och i VC:s Python 2.7 dar .upper()
# pa en UTF-8-bytestrang inte ror de icke-ASCII-tecknen.
SAKERHETSMARKORER = (
    ("EMG", "nodstoppskrets; bank/schema.py: EMG_OK lases fran sakerhets-PLC"),
    ("ESTOP", "nodstopp"),
    ("E_STOP", "nodstopp"),
    ("EMERGENCY", "nodstopp"),
    ("NODSTOPP", "nodstopp"),
    ("SAFE", "skyddsfunktion; bank/schema.py: SAFE_DOOR_CLOSED"),
    ("SAKERHET", "skyddsfunktion"),
    ("LIGHT_CURTAIN", "ljusrida; bank/schema.py: LIGHT_CURTAIN_OK"),
    ("LIGHTCURTAIN", "ljusrida"),
    ("LJUSRID", "ljusrida"),
    ("GUARD", "skyddsgrind eller skyddsovervakning"),
    ("SKYDD", "skyddsgrind eller skyddsovervakning"),
    ("INTERLOCK", "forregling mot en skyddsfunktion"),
    ("FORREGL", "forregling mot en skyddsfunktion"),
    ("MUTING", "muting av en skyddsanordning"),
    ("ENABLING", "trelagesdon"),
    ("DEADMAN", "trelagesdon"),
)

# Argumentnamn som BAR en tagg. Ett skrivande verktyg i domanen far inte ha
# ett namnbarande argument som inte star har - test_verktyg_signaler.py
# raknar efter och faller annars. Det ar sa sparren blir omojlig att glomma
# i stallet for bara forbjuden.
TAGGARGUMENT = (
    "name",
    "signal",
    "other_signal",
    "map",
    "other_map",
    "port_name",
    "behaviour",
    "property",
    "value",
)


def ar_sakerhetssignal(namn):
    """(ar_sakerhet, skal). skal ar None nar namnet inte ar markt."""
    if not isinstance(namn, str):
        return False, None
    versaler = namn.upper()
    for markor, skal in SAKERHETSMARKORER:
        if markor in versaler:
            return True, "%s innehaller %s: %s" % (namn, markor, skal)
    return False, None


def _sparra(verktyg, argument):
    """Kastar Sakerhetsavslag om nagot taggargument bar en sakerhetstagg.

    Kors forst i VARJE skrivande handlare. Samtliga TAGGARGUMENT provas, aven
    "value": en egenskapsadapter binds till en signal genom att ett
    vcProperty-varde SATTS till signalens namn, sa vardet ar en tagg i just
    det fallet. Att prova det aven nar det inte ar en tagg ger ett falskt
    avslag, och det ar ratt hall att fela at (I15).
    """
    for nyckel in TAGGARGUMENT:
        if nyckel not in argument:
            continue
        ar_sakerhet, skal = ar_sakerhetssignal(argument[nyckel])
        if ar_sakerhet:
            raise Sakerhetsavslag(verktyg, nyckel, argument[nyckel], skal)


def _krav_ickenegativ(verktyg, argument, nyckel):
    """Ett portindex eller portantal far inte vara negativt.

    Schemat i schema.py provar TYP, inte intervall - "minimum" i ett
    parameterschema vore en grind som ser ut att mata utan att gora det.
    Kontrollen ligger darfor dar den faktiskt kan falla, och den kastar
    samma Argumentfel som resten av argumentvalideringen sa att modellen far
    tillbaka ett fel den kanner igen.
    """
    if nyckel in argument and argument[nyckel] < 0:
        raise Argumentfel(verktyg, ["%s ar %d; ett portindex och ett portantal "
                                    "kan inte vara negativa"
                                    % (nyckel, argument[nyckel])])


# ==========================================================================
# 2. VC:s KONSTANTER, MATTA UR constants.xml
# ==========================================================================

# (konstantnamn, kort beskrivning). Exakt de som star i
# docs/referens/vc_api/constants.xml. Inga andra, och ingen harledd form:
# VC_INTEGERSIGNALMAP och VC_STRINGSIGNALMAP LATER rimliga och finns inte.
# Alla atta ar dessutom PROVADE skapbara i VC 4.10 (M-15), sa create_signal
# star pa en matning och inte bara pa en konstantlista.
SIGNALTYPER = (
    ("VC_BOOLEANSIGNAL", "boolesk signal, vcBoolSignal"),
    ("VC_REALSIGNAL", "flyttalssignal, vcRealSignal"),
    ("VC_INTEGERSIGNAL", "heltalssignal, vcIntegerSignal"),
    ("VC_STRINGSIGNAL", "textsignal, vcStringSignal"),
    ("VC_COMPONENTSIGNAL", "signal som bar en komponent, vcComponentSignal"),
    ("VC_MATRIXSIGNAL", "signal som bar en matris, vcMatrixSignal"),
    ("VC_FRAMESIGNAL", "signal som bar en ram; ingen typ beskriver ytan"),
    ("VC_BEHAVIOURSIGNAL", "signal som bar ett beteende; ingen typ beskriver ytan"),
)

# Bada provade skapbara i VC 4.10 (M-15). VC_REALSIGNALMAP kom dar tillbaka
# som en bar vcBehaviour, alltsa utan egen bindningsklass - se docstringen.
KARTTYPER = (
    ("VC_BOOLEANSIGNALMAP", "boolesk signalkarta, vcBooleanSignalMap"),
    ("VC_REALSIGNALMAP", "flyttalssignalkarta; ingen typ beskriver ytan"),
)

# Adaptern gar att KANNA IGEN, men skapandet ar oprovat: M-15 provade
# beteendetyperna och den ar inte bland de 80 som gick. Konstanten anvands
# darfor bara lasande, av signal_types och list_property_adapters.
ADAPTERTYP = "VC_PROPERTYSIGNALADAPTER"

# Allt signal_types provar, i den ordning det redovisas.
_TYPKATALOG = (
    tuple((k, "signal", b) for k, b in SIGNALTYPER)
    + tuple((k, "signalmap", b) for k, b in KARTTYPER)
    + ((ADAPTERTYP, "adapter",
        "binder en signal till en komponentegenskap; ingen typ beskriver ytan"),)
)

# Riktningen ar en EGENSKAP PA KARTAN, aldrig pa signalen. Etiketterna nedan
# ar verktygens sprak utat; konstanterna ar VC:s.
RIKTNINGAR = (
    ("input", "VC_SIGNALMAP_DIRECTION_INPUT"),
    ("output", "VC_SIGNALMAP_DIRECTION_OUTPUT"),
    ("undefined", "VC_SIGNALMAP_DIRECTION_UNDEFINED"),
)

# Filtervardet for "sitter inte pa nagon kartport alls". Skilt fran
# "undefined", som betyder att en karta finns och har odefinierad riktning.
OKARTLAGD = "okartlagd"

NOTERING_RIKTNING = (
    "Riktning ar ingen egenskap pa en VC-signal. Den ar HARLEDD: signalen "
    "sitter pa en port i en signalkarta, och kartans Direction "
    "(VC_SIGNALMAP_DIRECTION_INPUT / _OUTPUT / _UNDEFINED) galler alla dess "
    "portar. En signal som ingen karta bar far direction=null och raknas som "
    "okartlagd - den GISSAS aldrig ur namnet. Kopplingen port->signal lases "
    "med getInternalPortSignal och matchas pa signalens namn inom samma "
    "komponent."
)

NOTERING_SAKERHET = (
    "safety=true betyder att namnet trafffar SAKERHETSMARKORER i "
    "verktyg/signaler.py. Sadana taggar gar att LASA men inget skrivande "
    "verktyg ror dem (50_grindar.md, I15). Markningen ar namnbaserad och "
    "avsiktligt bred; den ar en konvention, inget bevis."
)


# ==========================================================================
# 3. UPPKOPPLINGEN: den matta .NET-ytan och den matta Python-luckan
# ==========================================================================

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", "..", ".."))
DOTNET_KATALOG = os.path.join(ROT, "docs", "referens", "vc_dotnet")

DOTNET_FILER = ("VisualComponents.Connectivity.Core.xml",
                "VisualComponents.Connectivity.OpcUA.xml")


def _las_dotnet(katalog=DOTNET_KATALOG):
    """{medlemsnamn: {"summering", "fil", "assembly"}} ur .NET-doc-XML.

    Kastar vid import om en fil saknas eller ar tom. S5 i 96_ingen_skuld.md:
    ett index som ar tomt ar inget index, och ett verktyg som svarar ur en
    kalla det inte last ar en stubbe.
    """
    ut = {}
    for filnamn in DOTNET_FILER:
        stig = os.path.join(katalog, filnamn)
        if not os.path.exists(stig):
            raise Schemafel("connectivity_status is missing its source: %s" % stig)
        rot = ET.parse(stig).getroot()
        assembly = (rot.findtext("./assembly/name") or "").strip()
        antal = 0
        for medlem in rot.findall("./members/member"):
            namn = (medlem.get("name") or "").strip()
            if not namn:
                continue
            ut[namn] = {
                "summering": " ".join((medlem.findtext("summary") or "").split()),
                "fil": os.path.join("docs", "referens", "vc_dotnet", filnamn),
                "assembly": assembly,
            }
            antal += 1
        if not antal:
            raise Schemafel("%s has no <member>; the source cannot be trusted"
                            % stig)
    return ut


DOTNET = _las_dotnet()


def _dotnet(namn):
    """En .NET-medlem med sin egen summering och sin kallfil.

    Kastar vid import om namnet inte star i XML-filerna. Det ar poangen:
    ett uppfunnet .NET-namn ska falla har och inte i ett svar (I9).
    """
    if namn not in DOTNET:
        raise Schemafel("%s is not in %s; connectivity_status must not "
                        "name a member the source does not have"
                        % (namn, ", ".join(DOTNET_FILER)))
    post = dict(DOTNET[namn])
    post["medlem"] = namn
    return post


# De tre fragorna en driftsattningsingenjor stallar om uppkopplingen, och
# den .NET-medlem som BAR svaret pa var och en. Ingen av dem har nagon
# Python-motsvarighet; det ar matt i _PYTHON_TRAFFAR nedan.
_UPPKOPPLING = {
    "servrar": {
        "fraga": "Vilka servrar och anslutningar ar konfigurerade i scenen?",
        "medlemmar": [
            "P:VisualComponents.Connectivity.Core.IConnectivityCore.ConnectionPlugins",
            "P:VisualComponents.Connectivity.Shared.IServer.DisplayName",
            "P:VisualComponents.Connectivity.Shared.IServer.Connected",
            "M:VisualComponents.Connectivity.Shared.IServer.Connect("
            "VisualComponents.Connectivity.Shared.IServerConnectionSettings)",
            "P:VisualComponents.Connectivity.OpcUA.ServerConnectionSettings.ServerUrl",
        ],
    },
    "tillstand": {
        "fraga": "Vilket tillstand star anslutningarna i?",
        "medlemmar": [
            "T:VisualComponents.Connectivity.Shared.ConnectionState",
            "F:VisualComponents.Connectivity.Shared.ConnectionState.Disconnected",
            "F:VisualComponents.Connectivity.Shared.ConnectionState.Connected",
            "F:VisualComponents.Connectivity.Shared.ConnectionState.ConnectionLost",
            "F:VisualComponents.Connectivity.Shared.ConnectionState."
            "ConnectionLostInternalReconnect",
            "E:VisualComponents.Connectivity.Shared.IServer.ConnectionStateChanged",
        ],
    },
    "variabler": {
        "fraga": "Vilka variabler ar mappade, at vilket hall, och med vilken kvalitet?",
        "medlemmar": [
            "P:VisualComponents.Connectivity.Shared.IVariableGroup.DataFlowDirection",
            "F:VisualComponents.Connectivity.Shared.VariableGroupDataDirection."
            "SimulationToServer",
            "F:VisualComponents.Connectivity.Shared.VariableGroupDataDirection."
            "ServerToSimulation",
            "P:VisualComponents.Connectivity.Shared.IValueItem.ID",
            "P:VisualComponents.Connectivity.Shared.IValueItem.DisplayName",
            "P:VisualComponents.Connectivity.Shared.IValueItem.ValueType",
            "P:VisualComponents.Connectivity.Shared.IValueItem.Access",
            "P:VisualComponents.Connectivity.Shared.IValueItem.Quality",
        ],
    },
}

FRAGOR = tuple(sorted(_UPPKOPPLING))

# Arkitekturfaktumet, med sin egen kalla i stallet for en omskrivning:
# sessionsobjektet ar UnifiedAutomation.UaClient.Session, alltsa ar VC
# KLIENT. Det ar hela skalet till att 60_plc.md valde OpenPLC v4 - den enda
# gratis mjuk-PLC som ar OPC UA-SERVER.
_ROLLMEDLEM = "P:VisualComponents.Connectivity.OpcUA.IOpcUAServer.Session"

# Matt lucka. Monstret sokes i api_index:s symbolnamn av
# test_verktyg_signaler.py, som faller om VC nagon gang far en
# Python-uppkopplingsyta - da ar den har texten inte langre sann.
# Tokens, inte losa delstrangar. MATT varfor: monstret "opc|server" traffade
# vcTopology.getCurveLoopCurve ("lo-OPC-urve") och VC_STATEMENT_RESERVERESOURCE
# ("re-SERVER-esource"), alltsa fem falska traffar som hade fatt luckan att se
# stangd ut. Ett monster som mater fel ar varre an inget monster.
PYTHONLUCKA_MONSTER = (r"opcua|connectivity|variablegroup|valueitem"
                       r"|connectionplugin|connectionstate|\bserver|server\b")

# Traffarna, inte antalet: en tom lista SAGER vad matningen fann, och ett
# framtida VC som far en Python-uppkopplingsyta far en rad har i stallet for
# att bara flytta en siffra. Antalet foljer av listan (I2, siffrans harkomst).
PYTHONLUCKA_TRAFFAR = ()

NOTERING_UPPKOPPLING = (
    "VC:s uppkopplingslager finns BARA i .NET. %d av symbolerna i VC:s "
    "Python-API rar server, anslutning, variabelgrupp eller OPC UA, sa ingen "
    "kodmall kan lista scenens servrar - varken den har eller en annan. "
    "Medlemmarna nedan ar dar svaret bor, citerade ur "
    "docs/referens/vc_dotnet/. VC ar OPC UA-KLIENT: %s bar en "
    "UnifiedAutomation.UaClient.Session. PLC:n ar servern (60_plc.md). "
    "Den vag som AR oppen harifran gar via komponentsignalerna, alltsa "
    "resten av den har domanen: list_signals, signal_inventory och "
    "set_signal ror de simuleringsvariabler som uppkopplingslagret mappar "
    "mot OPC UA-noder."
    % (len(PYTHONLUCKA_TRAFFAR), _ROLLMEDLEM.split(":", 1)[1])
)


# ==========================================================================
# 4. SCHEMABITAR
# ==========================================================================

ARG_SIGNAL = {
    "type": "string",
    "description": "Signalens namn pa komponenten, exakt som det star i beteendelistan.",
}
ARG_KARTA = {
    "type": "string",
    "description": "Signalkartans namn pa komponenten.",
}
ARG_PORT = {
    "type": "integer",
    "description": "Portens index i kartan. Forsta porten har index 0.",
}
ARG_BETEENDE = {
    "type": "string",
    "description": "Beteendets namn pa komponenten.",
}
ARG_RIKTNING_FILTER = {
    "type": "string",
    "enum": [e for e, _k in RIKTNINGAR] + [OKARTLAGD],
    "description": ("Ta bara med signaler med den harledda riktningen. "
                    + OKARTLAGD + " betyder att ingen signalkarta bar dem."),
}
ARG_SIGNALTYP = {
    "type": "string",
    "enum": [namn for namn, _b in SIGNALTYPER],
    "description": "VC:s konstant for signaltypen.",
}
ARG_VARDE = {
    "type": ["string", "number", "integer", "boolean"],
    "description": ("Det nya vardet. Ska passa signalens typ; VC avvisar ett "
                    "varde den inte kan omvandla."),
}

RET_SAKERHET = {
    "type": "boolean",
    "description": ("True om namnet ar markt sakerhet. Sadana taggar gar att "
                    "lasa men inget skrivande verktyg ror dem (I15)."),
}
RET_SAKERHETSSKAL = {
    "type": ["string", "null"],
    "description": "Vilken markor som fallde namnet, eller null.",
}
RET_TYP = {
    "type": ["string", "null"],
    "description": ("VC:s typkonstant, t.ex. VC_BOOLEANSIGNAL. null nar "
                    "beteendets Type inte motsvarar nagon kand konstant - "
                    "typen gissas aldrig."),
}
RET_TYP_ID = {
    "type": ["integer", "string", "null"],
    "description": "Beteendets rana Type-varde ur VC, sa en okand typ anda gar att se.",
}
RET_VARDE = {
    "type": ["string", "number", "integer", "boolean", "null"],
    "description": ("Signalens varde. En komponent- eller matrissignal kan "
                    "inte ges som enkel typ och kommer som text."),
}
RET_RIKTNING = {
    "type": ["string", "null"],
    "description": ("Harledd riktning: input, output eller undefined ur "
                    "signalkartans Direction. null = ingen karta bar signalen."),
}

_ANSLUTNINGSPOST = {
    "type": "object",
    "description": "Ett beteende som signalen ar kopplad till.",
    "properties": {
        "component": {"type": ["string", "null"],
                      "description": "Komponenten beteendet sitter pa."},
        "behaviour": {"type": "string", "description": "Beteendets namn."},
    },
}

_SIGNALPOST = {
    "type": "object",
    "description": "En signal, med sin harledda riktning och sin sakerhetsmarkning.",
    "properties": {
        "component": {"type": "string", "description": "Komponenten signalen sitter pa."},
        "name": {"type": "string", "description": "Signalens namn."},
        "type": RET_TYP,
        "type_id": RET_TYP_ID,
        "value": RET_VARDE,
        "direction": RET_RIKTNING,
        "map": {"type": ["string", "null"],
                "description": "Signalkartan som bar signalen, eller null."},
        "port": {"type": ["integer", "null"],
                 "description": "Portindex i kartan, eller null."},
        "connections": {"type": "integer",
                        "description": "Antal beteenden signalen ar kopplad till."},
        "safety": RET_SAKERHET,
        "safety_reason": RET_SAKERHETSSKAL,
    },
}

_KARTPOST = {
    "type": "object",
    "description": "En signalkarta pa komponenten.",
    "properties": {
        "component": {"type": "string", "description": "Komponenten kartan sitter pa."},
        "name": {"type": "string", "description": "Kartans namn."},
        "type": RET_TYP,
        "type_id": RET_TYP_ID,
        "ports": {"type": "integer", "description": "Antal portar, ur PortCount."},
        "direction": RET_RIKTNING,
        "listeners": {"type": "integer",
                      "description": "Antal beteenden som lyssnar pa kartan."},
    },
}

_EGENSKAPSPOST = {
    "type": "object",
    "description": "En vcProperty pa beteendet.",
    "properties": {
        "name": {"type": "string", "description": "Egenskapens namn."},
        "value": RET_VARDE,
        "type": RET_TYP_ID,
    },
}

RET_NOTERING = {
    "type": "string",
    "description": "Arlighetsrad som foljer med svaret, inte en fotnot i specen.",
}


# ==========================================================================
# 5. MALLENS EGNA HJALPARE
# ==========================================================================
#
# kodmall.py bar de hjalpare alla domaner delar (_svara, _enkelt, _komp,
# _app). Signalytan ar den har domanens ensak och ligger darfor har, byggd
# pa samma satt: ett namn -> (beroenden, kalla), en fast utskriftsordning,
# och bara det som faktiskt anvands skrivs ut. En mall som bar oanvand kod
# ar skuld aven nar den ar genererad (S3), och testet raknar efter.

def _txt(varde):
    """En ren strangliteral UTAN _s().

    Skild fran kodmall.lit() med flit. lit() ger _s(u"...") for allt som gar
    IN i VC:s API (M-05). Text som bara jamfors mot varden VC lamnar IFRAN
    sig ska daremot vara en vanlig strang - en bytestrang i py2, en unicode i
    py3 - precis som strangen den jamfors med. json.dumps ger en ASCII-ren
    literal med Pythons egna escape-regler.
    """
    if not isinstance(varde, str):
        raise TypeError("%r ar ingen strang" % (varde,))
    return _json.dumps(varde, ensure_ascii=True)


def _konstanttabell(namn, poster):
    """Rader som bygger en tabell (konstant, etikett) utan att kunna kasta.

    36_versioner.md: fraga vad som finns. En konstant som saknas i den har
    VC:n ska inte ge NameError mitt i en slinga - den ska helt enkelt inte
    sta i tabellen, och verktyget svarar da att typen ar okand.
    """
    rader = ["%s = []" % namn]
    for konstant, etikett in poster:
        rader += [
            "try:",
            "    %s.append((%s, %s))" % (namn, konstant, _txt(etikett)),
            "except NameError:",
            "    pass",
        ]
    return rader


def _krav_yta(objekt, attribut, vad):
    """Rader som kraver EN namngiven yta pa ETT objekt, med literalt namn.

    36_versioner.md: ytan provas per objekt, eftersom formaga.py:s YTOR-lista
    inte bar nagon signalyta (se modulens docstring). Saknas ytan kastar
    mallen med ett namngivet skal i stallet for att falla med AttributeError
    langt inne i VC.

    Attributnamnet skrivs som LITERAL och inte som en variabel, och det ar
    ett matt val: svc/vc_assist_svc/api_index.py:s validator kan folja
    hasattr(x, "Namn") men inte hasattr(x, namn) - den senare blir
    OBESTAMBAR, och en obestambarhet ar inget godkannande (I3). Samma form
    som granssnitt.py redan anvander for canConnect och Sections.
    """
    return [
        'if not hasattr(%s, "%s"):' % (objekt, attribut),
        "    raise ValueError(%s)" % _txt(
            "%s kraver %s som den har VC saknar" % (vad, attribut)),
    ]


_SAKMARK_RADER = (
    ["# Samma tabell som tjanstens SAKERHETSMARKORER (verktyg/signaler.py).",
     "# Skrivs in ur den, sa de tva kan inte drifta isar.",
     "_SAKMARK = ["]
    + ["    (%s, %s)," % (_txt(m), _txt(s)) for m, s in SAKERHETSMARKORER]
    + ["]"])


_EGNA = {
    "_sakerhet": ((), _SAKMARK_RADER + [
        "",
        "",
        "def _sakerhet(namn):",
        "    # Delstrang i versaler. Bred med flit: ett falskt avslag kostar",
        "    # en fraga, ett falskt godkannande skriver i en skyddskrets.",
        "    versaler = namn.upper()",
        "    for markor, skal in _SAKMARK:",
        "        if markor in versaler:",
        "            return namn + %s + markor + %s + skal"
        % (_txt(" innehaller "), _txt(": ")),
        "    return None",
    ]),
    "_ar_signal": ((), [
        "def _ar_signal(b):",
        "    # En signal kanns igen pa sin YTA, inte pa en konstant.",
        "    # vcSignal bar Connections, undertyperna bar Value och signal().",
        '    return (hasattr(b, "Value") and hasattr(b, "Connections")',
        '            and hasattr(b, "signal"))',
    ]),
    "_ar_karta": ((), [
        "def _ar_karta(b):",
        "    # vcBooleanSignalMap, vcIntergerSignalMap och vcStringSignalMap",
        "    # delar exakt de har tre. Direction och portmetoderna gor de",
        "    # INTE, sa de provas var for sig dar de anvands.",
        '    return (hasattr(b, "PortCount") and hasattr(b, "input")',
        '            and hasattr(b, "output"))',
    ]),
    "_signaltyper": ((), _konstanttabell(
        "_SIGNALTYPER", [(k, k) for k, _b in SIGNALTYPER])),
    "_karttyper": ((), _konstanttabell(
        "_KARTTYPER", [(k, k) for k, _b in KARTTYPER])),
    "_riktningstyper": ((), _konstanttabell(
        "_RIKTNINGSTYPER", [(k, e) for e, k in RIKTNINGAR])),
    "_typnamn": ((), [
        "def _typnamn(b, tabell):",
        "    # Beteendets Type mot de konstanter som FINNS i denna VC.",
        "    # Ingen traff ger None; typen gissas aldrig (I9).",
        "    t = b.Type",
        "    for varde, etikett in tabell:",
        "        if t == varde:",
        "            return etikett",
        "    return None",
    ]),
    "_riktnamn": (("_riktningstyper",), [
        "def _riktnamn(v):",
        "    for varde, etikett in _RIKTNINGSTYPER:",
        "        if v == varde:",
        "            return etikett",
        "    return None",
    ]),
    "_sig": (("_ar_signal",), [
        "def _sig(komp, namn):",
        "    b = komp.findBehaviour(_s(namn))",
        "    if b is None:",
        '        raise ValueError(komp.Name + " har inget beteende som heter " + namn)',
        "    if not _ar_signal(b):",
        '        raise ValueError(namn + " ar ingen signal; den saknar Value,'
        ' Connections eller signal()")',
        "    return b",
    ]),
    "_karta": (("_ar_karta",), [
        "def _karta(komp, namn):",
        "    b = komp.findBehaviour(_s(namn))",
        "    if b is None:",
        '        raise ValueError(komp.Name + " har inget beteende som heter " + namn)',
        "    if not _ar_karta(b):",
        '        raise ValueError(namn + " ar ingen signalkarta; den saknar'
        ' PortCount, input eller output")',
        "    return b",
    ]),
    "_bet": ((), [
        "def _bet(komp, namn):",
        "    b = komp.findBehaviour(_s(namn))",
        "    if b is None:",
        '        raise ValueError(komp.Name + " har inget beteende som heter " + namn)',
        "    return b",
    ]),
    "_anslutna_bet": ((), [
        "def _anslutna_bet(sig):",
        "    ut = []",
        "    for b in sig.Connections:",
        "        k = b.Component",
        '        ut.append({"component": k.Name if k is not None else None,',
        '                   "behaviour": b.Name})',
        "    return ut",
    ]),
    "_riktningar": (("_ar_karta", "_riktnamn"), [
        "def _riktningar(komp):",
        "    # Signalnamn -> {karta, port, riktning}. Riktningen HARLEDS ur",
        "    # kartans Direction; en VC-signal bar ingen egen riktning.",
        "    # Matchningen gar pa signalens namn inom SAMMA komponent, dar",
        "    # beteendenamn ar unika.",
        "    ut = {}",
        "    for m in komp.Behaviours:",
        "        if not _ar_karta(m):",
        "            continue",
        '        if not hasattr(m, "Direction") or not hasattr(m, "getInternalPortSignal"):',
        "            continue",
        "        antal = int(m.PortCount)",
        "        if antal > %d:   # kodmall.MAX_POSTER, ur bryggans 1 MiB-kropp"
        % MAX_POSTER,
        "            antal = %d" % MAX_POSTER,
        "        riktning = _riktnamn(m.Direction)",
        "        for i in range(antal):",
        "            s = m.getInternalPortSignal(i)",
        "            if s is None:",
        "                continue",
        '            ut[s.Name] = {"karta": m.Name, "port": i,',
        '                          "riktning": riktning}',
        "    return ut",
    ]),
    "_signalpost": (("_sakerhet", "_typnamn", "_signaltyper"), [
        "def _signalpost(komp, b, riktningar):",
        "    r = riktningar.get(b.Name)",
        "    skal = _sakerhet(b.Name)",
        '    return {"component": komp.Name, "name": b.Name,',
        '            "type": _typnamn(b, _SIGNALTYPER),',
        '            "type_id": _enkelt(b.Type),',
        '            "value": _enkelt(b.Value),',
        '            "direction": r["riktning"] if r is not None else None,',
        '            "map": r["karta"] if r is not None else None,',
        '            "port": r["port"] if r is not None else None,',
        '            "connections": len(b.Connections),',
        '            "safety": skal is not None,',
        '            "safety_reason": skal}',
    ]),
    "_kartpost": (("_ar_karta", "_typnamn", "_karttyper", "_riktnamn"), [
        "def _kartpost(komp, m):",
        '    riktning = _riktnamn(m.Direction) if hasattr(m, "Direction") else None',
        '    lyssnare = len(m.Listeners) if hasattr(m, "Listeners") else 0',
        '    return {"component": komp.Name, "name": m.Name,',
        '            "type": _typnamn(m, _KARTTYPER),',
        '            "type_id": _enkelt(m.Type),',
        '            "ports": int(m.PortCount),',
        '            "direction": riktning, "listeners": lyssnare}',
    ]),
    "_sparra_karta": (("_sakerhet",), [
        "def _sparra_karta(m, vad):",
        "    # I15, runtime-halvan av sakerhetsgransen. Tjanstens _sparra()",
        "    # domer NAMN och kan omojligt se vad kartans portar BAR - det",
        "    # vet bara VC. En karta som heter BoolMap men bar EMG_OK pa en",
        "    # port ar lika mycket en skyddskrets, sa den provas har, precis",
        "    # innan andringen sker.",
        '    if not hasattr(m, "getInternalPortSignal"):',
        "        return",
        "    antal = int(m.PortCount)",
        "    if antal > %d:   # kodmall.MAX_POSTER, ur bryggans 1 MiB-kropp"
        % MAX_POSTER,
        "        antal = %d" % MAX_POSTER,
        "    for i in range(antal):",
        "        sig = m.getInternalPortSignal(i)",
        "        if sig is None:",
        "            continue",
        "        skal = _sakerhet(sig.Name)",
        "        if skal is not None:",
        "            raise ValueError(vad + %s + str(i) + %s + skal)"
        % (_txt(" avvisas: port "), _txt(" bar en sakerhetstagg: ")),
    ]),
    "_egenskaper": ((), [
        "def _egenskaper(b):",
        "    ut = []",
        "    for p in b.Properties:",
        '        ut.append({"name": p.Name, "value": _enkelt(p.Value),',
        '                   "type": _enkelt(p.Type)})',
        "    return ut",
    ]),
}

# Fast ordning: en hjalpare far bara bero pa nagon som redan skrivits ut.
_EGEN_ORDNING = (
    "_sakerhet", "_ar_signal", "_ar_karta", "_signaltyper", "_karttyper",
    "_riktningstyper", "_typnamn", "_riktnamn", "_sig", "_karta",
    "_bet", "_anslutna_bet", "_sparra_karta", "_riktningar", "_signalpost",
    "_kartpost", "_egenskaper",
)


def _egna(namn):
    """Raderna for hjalparna plus allt de beror av, i fast ordning."""
    behovs = set()
    kvar = list(namn)
    while kvar:
        n = kvar.pop()
        if n in behovs:
            continue
        if n not in _EGNA:
            raise KeyError("okand hjalpare %r i signalmallen" % (n,))
        behovs.add(n)
        kvar.extend(_EGNA[n][0])
    rader = []
    for n in _EGEN_ORDNING:
        if n in behovs:
            rader.extend(_EGNA[n][1])
            rader.append("")
            rader.append("")
    return rader


def _mall(kodmallshjalpare, egna, rader):
    """bygg() med den har domanens egna hjalpare inskjutna forst."""
    return bygg(kodmallshjalpare, _egna(egna) + rader)


# Ytorna som formagegrinden FAKTISKT kan prova. Signalytorna star inte i
# formaga.YTOR och provas per objekt i mallen; se modulens docstring.
_YTOR_SCEN = ("app.Components", "app.findComponent", "comp.Name",
              "comp.Behaviours")
_YTOR_KOMPONENT = ("app.findComponent", "comp.Name", "comp.Behaviours")
_YTOR_BETEENDE = ("app.findComponent", "comp.findBehaviour")
_YTOR_BETEENDE_NAMN = ("app.findComponent", "comp.Name", "comp.findBehaviour")


# ==========================================================================
# 6. LASANDE VERKTYG
# ==========================================================================

# ---- list_signals --------------------------------------------------------

def _kod_list_signals(argument):
    if "component" in argument:
        kalla = "for k in [_komp(%s)]:" % lit(argument["component"])
        hjalpare = ["_komp", "_enkelt", "_svara"]
    else:
        kalla = "for k in _app().Components:"
        hjalpare = ["_app", "_enkelt", "_svara"]
    rader = ["rader = []", "avkortad = False", kalla,
             "    if avkortad:",
             "        break",
             "    riktningar = _riktningar(k)",
             "    for b in k.Behaviours:",
             "        if not _ar_signal(b):",
             "            continue"]
    if "name_contains" in argument:
        rader += ["        if %s not in b.Name:" % lit(argument["name_contains"]),
                  "            continue"]
    rader.append("        post = _signalpost(k, b, riktningar)")
    if "signal_type" in argument:
        rader += ['        if post["type"] != %s:' % _txt(argument["signal_type"]),
                  "            continue"]
    if "direction" in argument:
        if argument["direction"] == OKARTLAGD:
            rader += ['        if post["direction"] is not None:',
                      "            continue"]
        else:
            rader += ['        if post["direction"] != %s:'
                      % _txt(argument["direction"]),
                      "            continue"]
    rader += tak("rader", "        ")
    rader += [
        "        rader.append(post)",
        '_svara({"signals": rader, "antal": len(rader), "avkortad": avkortad,',
        '        "notering": %s})' % _txt(NOTERING_RIKTNING + " " + NOTERING_SAKERHET),
    ]
    return _mall(hjalpare, ["_ar_signal", "_riktningar", "_signalpost"], rader)


_lagg(
    "list_signals",
    "Listar signalerna i scenen eller i en komponent, med varde, typ, harledd "
    "riktning och sakerhetsmarkning. Filtrera med component, signal_type, "
    "direction eller name_contains - det ar den snabbaste bilden av vad "
    "styrningen har att arbeta med.",
    "read",
    params({"component": dict(ARG_KOMPONENT, description=(
                "Begransa till en komponent. Utelamnad listar hela layouten.")),
            "signal_type": dict(ARG_SIGNALTYP, description=(
                "Ta bara med signaler av den har VC-typen.")),
            "direction": ARG_RIKTNING_FILTER,
            "name_contains": {
                "type": "string",
                "description": "Ta bara med signaler vars namn innehaller texten."}}),
    returns({"signals": {"type": "array", "description": "Signalerna.",
                         "items": _SIGNALPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD,
             "notering": RET_NOTERING},
            ["signals", "antal", "avkortad", "notering"]),
    _YTOR_SCEN,
    _kod_list_signals,
)


# ---- signal_info ---------------------------------------------------------

def _kod_signal_info(argument):
    komp = lit(argument["component"])
    rader = [
        "k = _komp(%s)" % komp,
        "b = _sig(k, %s)" % lit(argument["signal"]),
        "post = _signalpost(k, b, _riktningar(k))",
        # Svaret byggs i en EGEN ordbok och _signalpost:s falt kopieras in.
        # Att i stallet skriva post["..."] hade varit en tilldelning till ett
        # index i nagot koden inte sjalv byggt, och bryggans skrivgrind hade
        # da domt det har LASANDE verktyget som skrivande.
        "ut = {}",
        'ut["connected_to"] = _anslutna_bet(b)',
        'ut["automatic_reset"] = (bool(b.AutomaticReset)',
        '                         if hasattr(b, "AutomaticReset") else None)',
        'ut["enabled"] = bool(b.Enabled) if hasattr(b, "Enabled") else None',
        'ut["notering"] = %s' % _txt(NOTERING_RIKTNING + " " + NOTERING_SAKERHET),
        "for nyckel in post:",
        "    ut[nyckel] = post[nyckel]",
        "_svara(ut)",
    ]
    return _mall(["_komp", "_enkelt", "_svara"],
                 ["_sig", "_riktningar", "_signalpost", "_anslutna_bet"], rader)


_lagg(
    "signal_info",
    "Allt om en signal: typ, varde, harledd riktning, vilken kartport den "
    "sitter pa, vilka beteenden den ar kopplad till och om den ar markt "
    "sakerhet. Kastar fel om namnet inte ar en signal.",
    "read",
    params({"component": ARG_KOMPONENT, "signal": ARG_SIGNAL},
           ["component", "signal"]),
    returns(dict(_SIGNALPOST["properties"],
                 connected_to={"type": "array",
                               "description": "Beteendena signalen ar kopplad till.",
                               "items": _ANSLUTNINGSPOST},
                 automatic_reset={
                     "type": ["boolean", "null"],
                     "description": ("Om VC aterstaller signalen vid "
                                     "simuleringsatergang. null om VC saknar "
                                     "egenskapen.")},
                 enabled={"type": ["boolean", "null"],
                          "description": "Om beteendet ar pa. null om VC saknar egenskapen."},
                 notering=RET_NOTERING),
            ["component", "name", "type", "value", "direction", "connections",
             "safety", "safety_reason", "connected_to", "notering"]),
    _YTOR_BETEENDE_NAMN + ("comp.Behaviours",),
    _kod_signal_info,
)


# ---- get_signal ----------------------------------------------------------

def _kod_get_signal(argument):
    namn = lit(argument["signal"])
    return _mall(["_komp", "_enkelt", "_svara"], ["_sig", "_typnamn", "_signaltyper",
                                                  "_sakerhet"], [
        "b = _sig(_komp(%s), %s)" % (lit(argument["component"]), namn),
        "skal = _sakerhet(b.Name)",
        '_svara({"component": %s, "name": b.Name,' % lit(argument["component"]),
        '        "value": _enkelt(b.Value),',
        '        "type": _typnamn(b, _SIGNALTYPER),',
        '        "safety": skal is not None, "safety_reason": skal})',
    ])


_lagg(
    "get_signal",
    "Lasar en enskild signals varde och typ. Det billiga verktyget att stalla "
    "om och om under en driftsattning; signal_info ger hela bilden.",
    "read",
    params({"component": ARG_KOMPONENT, "signal": ARG_SIGNAL},
           ["component", "signal"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "name": {"type": "string", "description": "Signalens namn."},
             "value": RET_VARDE, "type": RET_TYP,
             "safety": RET_SAKERHET, "safety_reason": RET_SAKERHETSSKAL},
            ["component", "name", "value", "type", "safety", "safety_reason"]),
    _YTOR_BETEENDE,
    _kod_get_signal,
)


# ---- signal_types --------------------------------------------------------

def _kod_signal_types(argument):
    # En try/except per konstant, och ingen tabell: en konstant som saknas i
    # den har VC:n ger NameError vid uppslaget och star da helt enkelt inte i
    # svaret. Det ar 36_versioner.md:s regel - fraga vad som FINNS - och den
    # ar synlig rad for rad i stallet for gomd i en slinga.
    rader = ["k = _komp(%s)" % lit(argument["component"]), "rader = []"]
    for konstant, slag, beskrivning in _TYPKATALOG:
        rader += [
            "try:",
            '    rader.append({"constant": %s, "kind": %s,'
            % (_txt(konstant), _txt(slag)),
            '                  "description": %s,' % _txt(beskrivning),
            '                  "type_id": _enkelt(%s)})' % konstant,
            "except NameError:",
            "    pass",
        ]
    rader += [
        '_svara({"component": k.Name, "types": rader, "antal": len(rader),',
        '        "can_create": hasattr(k, "createBehaviour"),',
        '        "notering": %s})' % _txt(
            "Listan ar PROVAD i den har VC:n, inte antagen: en konstant som "
            "saknas star inte med (36_versioner.md). can_create=false betyder "
            "att komponenten saknar createBehaviour, och da gar varken "
            "create_signal eller create_signal_map att kora mot den. Att "
            "VC_PROPERTYSIGNALADAPTER star i listan betyder att KONSTANTEN "
            "finns, inte att adaptern gar att skapa: M-15 provade skapandet "
            "och adaptern ar inte bland de 80 beteenden som gick."),
    ]
    return _mall(["_komp", "_enkelt", "_svara"], [], rader)


_lagg(
    "signal_types",
    "Vilka signal-, signalkarte- och adaptertyper den har VC:n FAKTISKT bar, "
    "och om komponenten gar att skapa beteenden pa. Prova detta innan "
    "create_signal i en okand installation.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten som provades."},
             "types": {"type": "array", "description": "De typkonstanter som finns.",
                       "items": {"type": "object", "description": "En typkonstant.",
                                 "properties": {
                                     "constant": {"type": "string",
                                                  "description": "Konstantens namn."},
                                     "kind": {"type": "string",
                                              "description": "signal, signalmap eller adapter."},
                                     "description": {"type": "string",
                                                     "description": "Vad typen ar, kort."},
                                     "type_id": RET_TYP_ID}}},
             "antal": RET_ANTAL,
             "can_create": {"type": "boolean",
                            "description": "Om komponenten bar createBehaviour."},
             "notering": RET_NOTERING},
            ["component", "types", "antal", "can_create", "notering"]),
    _YTOR_KOMPONENT,
    _kod_signal_types,
)


# ---- list_signal_connections ---------------------------------------------

def _kod_list_signal_connections(argument):
    if "component" in argument:
        kalla = "for k in [_komp(%s)]:" % lit(argument["component"])
        hjalpare = ["_komp", "_svara"]
    else:
        kalla = "for k in _app().Components:"
        hjalpare = ["_app", "_svara"]
    rader = ["rader = []", "avkortad = False", kalla,
             "    if avkortad:",
             "        break",
             "    for b in k.Behaviours:",
             "        if not _ar_signal(b) or not b.Connections:",
             "            continue"]
    rader += tak("rader", "        ")
    rader += [
        "        skal = _sakerhet(b.Name)",
        '        rader.append({"component": k.Name, "signal": b.Name,',
        '                      "connected_to": _anslutna_bet(b),',
        '                      "safety": skal is not None,',
        '                      "safety_reason": skal})',
        '_svara({"connections": rader, "antal": len(rader), "avkortad": avkortad})',
    ]
    return _mall(hjalpare, ["_ar_signal", "_anslutna_bet", "_sakerhet"], rader)


_lagg(
    "list_signal_connections",
    "Listar vilka signaler som ar kopplade till nagot, for en komponent eller "
    "for hela layouten, och till vad. Signaler utan koppling utelamnas.",
    "read",
    params({"component": dict(ARG_KOMPONENT, description=(
        "Begransa till en komponent. Utelamnad listar hela layouten."))}),
    returns({"connections": {
                 "type": "array", "description": "De kopplade signalerna.",
                 "items": {"type": "object",
                           "description": "En signal och dess motparter.",
                           "properties": {
                               "component": {"type": "string",
                                             "description": "Komponenten."},
                               "signal": {"type": "string",
                                          "description": "Signalens namn."},
                               "connected_to": {"type": "array",
                                                "description": "Motparterna.",
                                                "items": _ANSLUTNINGSPOST},
                               "safety": RET_SAKERHET,
                               "safety_reason": RET_SAKERHETSSKAL}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["connections", "antal", "avkortad"]),
    _YTOR_SCEN,
    _kod_list_signal_connections,
)


# ---- list_signal_maps ----------------------------------------------------

def _kod_list_signal_maps(argument):
    if "component" in argument:
        kalla = "for k in [_komp(%s)]:" % lit(argument["component"])
        hjalpare = ["_komp", "_enkelt", "_svara"]
    else:
        kalla = "for k in _app().Components:"
        hjalpare = ["_app", "_enkelt", "_svara"]
    rader = ["rader = []", "avkortad = False", kalla,
             "    if avkortad:",
             "        break",
             "    for m in k.Behaviours:",
             "        if not _ar_karta(m):",
             "            continue"]
    rader += tak("rader", "        ")
    rader += [
        "        rader.append(_kartpost(k, m))",
        '_svara({"maps": rader, "antal": len(rader), "avkortad": avkortad})',
    ]
    return _mall(hjalpare, ["_kartpost"], rader)


_lagg(
    "list_signal_maps",
    "Listar signalkartorna i scenen eller i en komponent med typ, antal "
    "portar och riktning. Kartan ar det enda stallet dar en riktning finns "
    "i VC.",
    "read",
    params({"component": dict(ARG_KOMPONENT, description=(
        "Begransa till en komponent. Utelamnad listar hela layouten."))}),
    returns({"maps": {"type": "array", "description": "Signalkartorna.",
                      "items": _KARTPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["maps", "antal", "avkortad"]),
    _YTOR_SCEN,
    _kod_list_signal_maps,
)


# ---- signal_map_info -----------------------------------------------------

def _kod_signal_map_info(argument):
    rader = [
        "k = _komp(%s)" % lit(argument["component"]),
        "m = _karta(k, %s)" % lit(argument["map"]),
        "post = _kartpost(k, m)",
        # Samma skal som i signal_info: svaret byggs i en EGEN ordbok, sa att
        # skrivgrinden inte ser en tilldelning till ett index i nagot koden
        # inte sjalv byggt och domer det har lasande verktyget som skrivande.
        "ut = {}",
        "portar = []",
        "avkortad = False",
        "antal = int(m.PortCount)",
        "for i in range(antal):",
    ]
    rader += tak("portar")
    rader += [
        '    p = {"port": i, "name": None, "signal": None, "value": None,',
        '         "external": [], "safety": False, "safety_reason": None}',
        '    if hasattr(m, "getPortName"):',
        '        p["name"] = m.getPortName(i)',
        '    if hasattr(m, "getInternalPortSignal"):',
        "        s = m.getInternalPortSignal(i)",
        "        if s is not None:",
        '            p["signal"] = s.Name',
        "            skal = _sakerhet(s.Name)",
        '            p["safety"] = skal is not None',
        '            p["safety_reason"] = skal',
        '    if hasattr(m, "getConnectedExternalSignals"):',
        "        for e in m.getConnectedExternalSignals(i):",
        "            ke = e.Component",
        '            p["external"].append(',
        '                {"component": ke.Name if ke is not None else None,',
        '                 "behaviour": e.Name})',
        '    p["value"] = _enkelt(m.input(i))',
        "    portar.append(p)",
        'ut["ports_listed"] = portar',
        'ut["antal"] = len(portar)',
        'ut["avkortad"] = avkortad',
        "for nyckel in post:",
        "    ut[nyckel] = post[nyckel]",
        "_svara(ut)",
    ]
    return _mall(["_komp", "_enkelt", "_svara"],
                 ["_karta", "_kartpost", "_sakerhet"], rader)


_lagg(
    "signal_map_info",
    "Allt om en signalkarta: riktning och varje port med namn, den interna "
    "signalen, portens varde och de externa signaler porten ar kopplad till. "
    "Det ar den har bilden man behover for att veta vad en OPC UA-variabel "
    "faktiskt landar i.",
    "read",
    params({"component": ARG_KOMPONENT, "map": ARG_KARTA},
           ["component", "map"]),
    returns(dict(_KARTPOST["properties"],
                 ports_listed={
                     "type": "array", "description": "Portarna, en post var.",
                     "items": {"type": "object", "description": "En port i kartan.",
                               "properties": {
                                   "port": {"type": "integer",
                                            "description": "Portens index."},
                                   "name": {"type": ["string", "null"],
                                            "description": ("Portens namn. Tom "
                                                            "strang nar porten saknar signal.")},
                                   "signal": {"type": ["string", "null"],
                                              "description": "Den interna signalens namn."},
                                   "value": RET_VARDE,
                                   "external": {"type": "array",
                                                "description": "Externt kopplade signaler.",
                                                "items": _ANSLUTNINGSPOST},
                                   "safety": RET_SAKERHET,
                                   "safety_reason": RET_SAKERHETSSKAL}}},
                 antal=RET_ANTAL, avkortad=RET_AVKORTAD),
            ["component", "name", "type", "ports", "direction", "ports_listed",
             "antal", "avkortad"]),
    _YTOR_BETEENDE_NAMN,
    _kod_signal_map_info,
)


# ---- list_property_adapters ----------------------------------------------

def _kod_list_property_adapters(argument):
    rader = [
        "k = _komp(%s)" % lit(argument["component"]),
        "typ = None",
        "try:",
        "    typ = %s" % ADAPTERTYP,
        "except NameError:",
        "    pass",
        "rader = []",
        "avkortad = False",
        "if typ is not None:",
        "    for b in k.Behaviours:",
        "        if b.Type != typ:",
        "            continue",
    ]
    rader += tak("rader", "        ")
    rader += [
        '        rader.append({"component": k.Name, "name": b.Name,',
        '                      "type": %s,' % _txt(ADAPTERTYP),
        '                      "type_id": _enkelt(b.Type),',
        '                      "properties": _egenskaper(b)})',
        '_svara({"component": k.Name, "adapters": rader, "antal": len(rader),',
        '        "avkortad": avkortad,',
        '        "constant_present": typ is not None,',
        '        "notering": %s})' % _txt(
            "En egenskapsadapter (VC_PROPERTYSIGNALADAPTER) har INGEN typ i "
            "VC:s matta Python-API, sa dess faltnamn finns inte att sla upp. "
            "Adaptern konfigureras darfor genom sina EGNA vcProperty-poster, "
            "som listas har med namn, varde och typ. Satt dem med "
            "set_behaviour_property - namnen kommer ur den har listan, aldrig "
            "ur en gissning (I9). constant_present=false betyder att den har "
            "VC:n saknar konstanten och att adaptrar da inte gar att "
            "identifiera alls. Adaptern maste redan finnas i scenen: M-15 "
            "provade att skapa beteendetyper och VC_PROPERTYSIGNALADAPTER ar "
            "INTE bland de 80 som gick, sa skapandet ar oprovat och domanen "
            "har inget verktyg for det."),
    ]
    return _mall(["_komp", "_enkelt", "_svara"], ["_egenskaper"], rader)


_lagg(
    "list_property_adapters",
    "Listar komponentens egenskapsadaptrar och visar varje adapters egna "
    "installningsegenskaper med namn och varde. Det ar sa man ser hur en "
    "signal ar bunden till en komponentegenskap, utan att gissa faltnamn. "
    "Adaptern maste redan finnas i scenen - att skapa en ar oprovat i VC "
    "(M-15) och domanen har inget verktyg for det.",
    "read",
    params({"component": ARG_KOMPONENT}, ["component"]),
    returns({"component": {"type": "string", "description": "Komponenten."},
             "adapters": {"type": "array", "description": "Adaptrarna.",
                          "items": {"type": "object", "description": "En adapter.",
                                    "properties": {
                                        "component": {"type": "string",
                                                      "description": "Komponenten."},
                                        "name": {"type": "string",
                                                 "description": "Adapterns namn."},
                                        "type": {"type": "string",
                                                 "description": "Alltid VC_PROPERTYSIGNALADAPTER."},
                                        "type_id": RET_TYP_ID,
                                        "properties": {
                                            "type": "array",
                                            "description": "Adapterns installningsegenskaper.",
                                            "items": _EGENSKAPSPOST}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD,
             "constant_present": {
                 "type": "boolean",
                 "description": "Om VC_PROPERTYSIGNALADAPTER finns i den har VC:n."},
             "notering": RET_NOTERING},
            ["component", "adapters", "antal", "avkortad", "constant_present",
             "notering"]),
    _YTOR_KOMPONENT,
    _kod_list_property_adapters,
)


# ---- signal_inventory ----------------------------------------------------

def _kod_signal_inventory(argument):
    rader = [
        "rader = []",
        "avkortad = False",
        "per_typ = {}",
        "sedda = {}",
        "dubbletter = []",
        "utan_typ = []",
        "sakra = []",
        "for k in _app().Components:",
        "    if avkortad:",
        "        break",
        "    riktningar = _riktningar(k)",
        "    for b in k.Behaviours:",
        "        if not _ar_signal(b):",
        "            continue",
    ]
    rader += tak("rader", "        ")
    rader += [
        "        post = _signalpost(k, b, riktningar)",
        '        rad = {"tag": post["name"], "component": post["component"],',
        '               "type": post["type"], "direction": post["direction"],',
        '               "map": post["map"], "port": post["port"],',
        '               "safety": post["safety"],',
        '               "safety_reason": post["safety_reason"]}',
        "        rader.append(rad)",
        '        nyckel = post["type"] if post["type"] is not None else %s'
        % _txt("okand"),
        "        per_typ[nyckel] = per_typ.get(nyckel, 0) + 1",
        '        if post["type"] is None:',
        '            utan_typ.append(post["name"])',
        '        if post["safety"]:',
        '            sakra.append(post["name"])',
        '        if post["name"] in sedda:',
        '            dubbletter.append({"tag": post["name"],',
        '                               "components": [sedda[post["name"]],',
        '                                              post["component"]]})',
        "        else:",
        '            sedda[post["name"]] = post["component"]',
        "typer = []",
        "for namn in sorted(per_typ):",
        '    typer.append({"type": namn, "antal": per_typ[namn]})',
        '_svara({"declarations": rader, "antal": len(rader),',
        '        "avkortad": avkortad, "per_type": typer,',
        '        "duplicates": dubbletter, "without_type": utan_typ,',
        '        "safety_tags": sakra,',
        '        "notering": %s})' % _txt(
            "Ravaran till grind 3 i 50_grindar.md: PLC-deklarationerna "
            "GENERERAS ur den har listan, modellen skriver dem aldrig sjalv "
            "(I10). tag ar signalens namn i scenen och ingenting annat - "
            "inget taggnamn hittas pa har. duplicates ar signalnamn som "
            "forekommer pa mer an en komponent; i ett platt PLC-namnrum ar de "
            "en kollision som maste losas innan deklarationerna genereras. "
            "without_type ar signaler vars Type inte motsvarar nagon kand "
            "konstant - de far ingen datatyp och maste redas ut, inte gissas. "
            + NOTERING_RIKTNING + " " + NOTERING_SAKERHET),
    ]
    return _mall(["_app", "_enkelt", "_svara"],
                 ["_ar_signal", "_riktningar", "_signalpost"], rader)


_lagg(
    "signal_inventory",
    "Signalinventeringen for hela scenen, avsedd att bli PLC-deklarationerna: "
    "tagg, komponent, typ och riktning per signal, plus namnkollisioner mellan "
    "komponenter, signaler utan kand typ och vilka taggar som ar markta "
    "sakerhet. Kor den innan du later nagon skriva ST.",
    "read",
    params({}),
    returns({"declarations": {
                 "type": "array", "description": "En rad per signal i scenen.",
                 "items": {"type": "object", "description": "En deklarationsrad.",
                           "properties": {
                               "tag": {"type": "string",
                                       "description": "Signalens namn, som ar taggen."},
                               "component": {"type": "string",
                                             "description": "Komponenten den sitter pa."},
                               "type": RET_TYP,
                               "direction": RET_RIKTNING,
                               "map": {"type": ["string", "null"],
                                       "description": "Signalkartan, eller null."},
                               "port": {"type": ["integer", "null"],
                                        "description": "Portindex, eller null."},
                               "safety": RET_SAKERHET,
                               "safety_reason": RET_SAKERHETSSKAL}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD,
             "per_type": {"type": "array", "description": "Antal signaler per typ.",
                          "items": {"type": "object", "description": "En typrad.",
                                    "properties": {
                                        "type": {"type": "string",
                                                 "description": "Typkonstanten eller okand."},
                                        "antal": {"type": "integer",
                                                  "description": "Antal signaler."}}}},
             "duplicates": {
                 "type": "array",
                 "description": "Taggnamn som finns pa mer an en komponent.",
                 "items": {"type": "object", "description": "En namnkollision.",
                           "properties": {
                               "tag": {"type": "string", "description": "Taggen."},
                               "components": {"type": "array",
                                              "description": "Komponenterna som bar namnet.",
                                              "items": {"type": "string",
                                                        "description": "Komponentnamn."}}}}},
             "without_type": {"type": "array",
                              "description": "Signaler vars typ inte gick att avgora.",
                              "items": {"type": "string", "description": "Signalnamn."}},
             "safety_tags": {"type": "array",
                             "description": "Taggar markta sakerhet.",
                             "items": {"type": "string", "description": "Signalnamn."}},
             "notering": RET_NOTERING},
            ["declarations", "antal", "avkortad", "per_type", "duplicates",
             "without_type", "safety_tags", "notering"]),
    ("app.Components", "comp.Name", "comp.Behaviours"),
    _kod_signal_inventory,
)


# ---- connectivity_status (data) ------------------------------------------

def _hamta_uppkoppling(argument):
    """Handlare for det enda data-verktyget i domanen.

    Svarar ur DOTNET, som lastes vid import. Ingen kod, ingen brygga: fragan
    "vilka servrar finns" HAR inget Python-svar, och att generera en mall som
    latsas leta vore precis den stubb 96_ingen_skuld.md kallar varre an
    ingenting (S1).
    """
    vald = argument["question"]
    namn = FRAGOR if vald == "allt" else (vald,)
    avsnitt = []
    for n in namn:
        avsnitt.append({
            "question": n,
            "fraga": _UPPKOPPLING[n]["fraga"],
            "dotnet_members": [_dotnet(m) for m in _UPPKOPPLING[n]["medlemmar"]],
        })
    return {
        "role": "client",
        "role_evidence": _dotnet(_ROLLMEDLEM),
        "python_api_hits": len(PYTHONLUCKA_TRAFFAR),
        "python_api_symbols": list(PYTHONLUCKA_TRAFFAR),
        "python_api_pattern": PYTHONLUCKA_MONSTER,
        "readable_from_python": False,
        "sections": avsnitt,
        "open_path": ["list_signals", "signal_inventory", "signal_map_info",
                      "set_signal"],
        "notering": NOTERING_UPPKOPPLING,
    }


_DOTNETPOST = {
    "type": "object",
    "description": "En .NET-medlem, citerad ur sin egen dokumentationsfil.",
    "properties": {
        "medlem": {"type": "string", "description": "Medlemmens fulla .NET-namn."},
        "summering": {"type": "string",
                      "description": "Medlemmens egen summary, ordagrant ur XML-filen."},
        "fil": {"type": "string", "description": "Kallfilen namnet lastes ur."},
        "assembly": {"type": "string", "description": "Assemblyn filen beskriver."},
    },
}

registrera(
    Verktyg(
        namn="connectivity_status",
        beskrivning=(
            "Svarar pa vad som gar att veta om scenens uppkoppling: vilka "
            "servrar och anslutningar som ar konfigurerade, deras tillstand, "
            "och vilka variabler som ar mappade. VC:s uppkopplingslager finns "
            "bara i .NET, sa svaret ar den .NET-medlem som bar varje uppgift "
            "plus den vag som FAKTISKT ar oppen harifran. VC ar OPC UA-klient, "
            "PLC:n ar server."),
        mode="data", effect="read",
        parameters=params({"question": {
            "type": "string",
            "enum": list(FRAGOR) + ["allt"],
            "default": "allt",
            "description": ("Vilken av de tre fragorna som ska besvaras, eller "
                            "allt for alla tre.")}}),
        returns=returns({
            "role": {"type": "string",
                     "description": "VC:s roll i OPC UA-kedjan. Alltid client."},
            "role_evidence": _DOTNETPOST,
            "python_api_hits": {
                "type": "integer",
                "description": ("Antal symboler i VC:s Python-API som ror "
                                "uppkoppling. Matt, och noll.")},
            "python_api_symbols": {
                "type": "array",
                "description": ("De symboler monstret traffade. Tom, och det ar "
                                "sjalva matningen."),
                "items": {"type": "string", "description": "Symbolnamn."}},
            "python_api_pattern": {
                "type": "string",
                "description": ("Monstret siffran ovan raknades med. Ett tal "
                                "utan sin matmetod gar inte att prova om.")},
            "readable_from_python": {
                "type": "boolean",
                "description": "Om nagot av detta gar att lasa genom bryggan. Alltid false."},
            "sections": {
                "type": "array", "description": "Ett avsnitt per fraga.",
                "items": {"type": "object", "description": "En fraga och dess .NET-medlemmar.",
                          "properties": {
                              "question": {"type": "string",
                                           "description": "Fragans nyckel."},
                              "fraga": {"type": "string",
                                        "description": "Fragan i klartext."},
                              "dotnet_members": {"type": "array",
                                                 "description": "Medlemmarna som bar svaret.",
                                                 "items": _DOTNETPOST}}}},
            "open_path": {"type": "array",
                          "description": "Verktygen som ar den oppna vagen i stallet.",
                          "items": {"type": "string", "description": "Verktygsnamn."}},
            "notering": RET_NOTERING},
            ["role", "role_evidence", "python_api_hits",
             "python_api_symbols", "python_api_pattern",
             "readable_from_python", "sections", "open_path", "notering"]),
        since=SINCE,
        # KRAVER for ett data-verktyg. Schemat kraver minst en yta ur
        # formaga.YTOR, och verktyget kor i tjansten utan att ro VC. Vi
        # deklarerar den yta svaret PEKAR PA: den oppna vagen gar via
        # komponentsignalerna, alltsa comp.Behaviours. Foljden ar avsiktlig -
        # utan formagerapport ar ocksa det har verktyget avslaget, och skalet
        # modellen far namner ytan (I3 fail-closed).
        kraver=("comp.Behaviours",),
        doman=DOMAN, timeout_ms=TIMEOUT_MS),
    _hamta_uppkoppling)


# ==========================================================================
# 7. SKRIVANDE VERKTYG
# ==========================================================================
#
# Alla gar genom godkannandekon: effect="write" och utforare.py slar upp
# operationen i OP_FOR_EFFECT (I12). Ingen handlare har valjer lage.
#
# Alla borjar med _sparra(). Det ar sakerhetsgransen, och den ligger i
# handlaren just for att den ska verka INNAN nagon kod finns och innan
# bryggan rors.
#
# Alla maste dessutom domas som SKRIVANDE av ext/vc_addon/vc_assist/
# skrivgrind.granska(), annars skulle koden kunna ga genom exec utan
# godkannande. Grinden ar syntaktisk: den ser tilldelning till ett attribut
# och anrop vars namn borjar pa set/create/delete/connect/... Det styr
# mallarnas form pa ett stalle, och det stallet ar utpekat:
# set_signal_map_direction skriver m.Direction i stallet for att anropa
# m.trySetDirection(). Bada satter riktningen, men bara den forsta ar synlig
# for grinden. Ett skrivande verktyg vars kod grinden inte kan se ar ett hal
# i andra forsvarslinjen, sa formen ar vald efter vad som gar att GRANSKA -
# och felutfallet fangas anda, genom att riktningen lases tillbaka och
# jamfors.

# ---- set_signal ----------------------------------------------------------

def _kod_set_signal(argument):
    _sparra("set_signal", argument)
    rader = [
        "b = _sig(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument["signal"])),
        "b.Value = %s" % lit(argument["value"]),
    ]
    if argument["trigger"]:
        # signal() utan argument sander det varde som just satts, och det ar
        # den dokumenterade vagen att fa OnSignal att fyra. Tilldelningen
        # ovan ar dessutom det skrivgrinden ser; signal() ensamt hade den
        # inte domt som skrivande.
        rader.append("b.signal()")
    rader += [
        '_svara({"set": True, "component": %s, "name": b.Name,'
        % lit(argument["component"]),
        '        "value": _enkelt(b.Value), "triggered": %s})'
        % repr(bool(argument["trigger"])),
    ]
    return _mall(["_komp", "_enkelt", "_svara"], ["_sig"], rader)


_lagg(
    "set_signal",
    "Satter en signals varde. Med trigger=true sands vardet ocksa till de "
    "kopplade beteendena, sa att OnSignal fyrar - utan trigger andras bara "
    "vardet. Taggar markta sakerhet avvisas (I15).",
    "write",
    params({"component": ARG_KOMPONENT, "signal": ARG_SIGNAL,
            "value": ARG_VARDE,
            "trigger": {"type": "boolean", "default": False,
                        "description": ("True sander vardet vidare sa att "
                                        "OnSignal fyrar hos mottagarna.")}},
           ["component", "signal", "value"]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "name": {"type": "string", "description": "Signalens namn."},
             "value": RET_VARDE,
             "triggered": {"type": "boolean", "description": "Om signal() ocksa kordes."}},
            ["set", "component", "name", "value", "triggered"]),
    _YTOR_BETEENDE,
    _kod_set_signal,
)


# ---- create_signal -------------------------------------------------------

def _kod_create_signal(argument):
    _sparra("create_signal", argument)
    konstant = argument["signal_type"]
    namn = lit(argument["name"])
    rader = [
        "k = _komp(%s)" % lit(argument["component"]),
    ] + _krav_yta("k", "createBehaviour", "create_signal") + [
        "if k.findBehaviour(%s) is not None:" % namn,
        '    raise ValueError(k.Name + " har redan ett beteende som heter "'
        ' + %s)' % namn,
        "try:",
        "    typ = %s" % konstant,
        "except NameError:",
        "    raise ValueError(%s)" % _txt(
            "den har VC:n saknar konstanten " + konstant
            + "; kor signal_types for att se vilka typer som finns"),
        "b = k.createBehaviour(typ, %s)" % namn,
        "if b is None:",
        '    raise ValueError("VC skapade ingen signal som heter " + %s)' % namn,
        '_svara({"created": True, "component": k.Name, "name": b.Name,',
        '        "type": %s, "type_id": _enkelt(b.Type)})' % _txt(konstant),
    ]
    return _mall(["_komp", "_enkelt", "_svara"], [], rader)


_lagg(
    "create_signal",
    "Skapar en signal av angiven typ pa en komponent. Namnet maste vara ledigt. "
    "Bara signaltyper - ett skriptbeteende stoppar simuleringen och tar ned "
    "bryggan (M-13), och gar darfor inte att skapa harifran alls.",
    "write",
    params({"component": ARG_KOMPONENT,
            "name": dict(ARG_SIGNAL, description="Namnet den nya signalen ska fa."),
            "signal_type": ARG_SIGNALTYP},
           ["component", "name", "signal_type"]),
    returns({"created": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "name": {"type": "string", "description": "Signalens namn."},
             "type": {"type": "string", "description": "Typkonstanten som anvandes."},
             "type_id": RET_TYP_ID},
            ["created", "component", "name", "type"]),
    _YTOR_BETEENDE,
    _kod_create_signal,
)


# ---- delete_signal -------------------------------------------------------

def _kod_delete_signal(argument):
    _sparra("delete_signal", argument)
    namn = lit(argument["signal"])
    return _mall(["_komp", "_svara"], ["_sig"], [
        "k = _komp(%s)" % lit(argument["component"]),
        "b = _sig(k, %s)" % namn,
    ] + _krav_yta("b", "delete", "delete_signal") + [
        "b.delete()",
        '_svara({"deleted": True, "component": k.Name, "name": %s})' % namn,
    ])


_lagg(
    "delete_signal",
    "Tar bort en signal ur en komponent. Kopplingar till den forsvinner med "
    "den. Taggar markta sakerhet avvisas (I15).",
    "write",
    params({"component": ARG_KOMPONENT, "signal": ARG_SIGNAL},
           ["component", "signal"]),
    returns({"deleted": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "name": {"type": "string", "description": "Signalens namn."}},
            ["deleted", "component", "name"]),
    _YTOR_BETEENDE,
    _kod_delete_signal,
)


# ---- connect_signals -----------------------------------------------------

def _kod_connect_signals(argument):
    _sparra("connect_signals", argument)
    return _mall(["_komp", "_svara"], ["_sig", "_anslutna_bet"], [
        "a = _sig(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument["signal"])),
        "b = _sig(_komp(%s), %s)" % (lit(argument["other_component"]),
                                     lit(argument["other_signal"])),
        "if not a.connect(b):",
        # En nekad koppling far aldrig se ut som en lyckad (S1).
        '    raise ValueError("VC nekade kopplingen mellan " + a.Name'
        ' + " och " + b.Name)',
        '_svara({"connected": True, "component": %s, "signal": a.Name,'
        % lit(argument["component"]),
        '        "other_component": %s, "other_signal": b.Name,'
        % lit(argument["other_component"]),
        '        "connected_to": _anslutna_bet(a)})',
    ])


_lagg(
    "connect_signals",
    "Kopplar tva signaler sa att den ena driver den andra, aven mellan olika "
    "komponenter. VC avgor sjalv om kopplingen ar tillaten; en nekad koppling "
    "kastar i stallet for att se ut som en lyckad.",
    "write",
    params({"component": ARG_KOMPONENT, "signal": ARG_SIGNAL,
            "other_component": dict(ARG_KOMPONENT,
                                    description="Den andra komponentens namn."),
            "other_signal": dict(ARG_SIGNAL,
                                 description="Signalens namn pa den andra komponenten.")},
           ["component", "signal", "other_component", "other_signal"]),
    returns({"connected": {"type": "boolean", "description": "Alltid true; en nekad koppling kastar."},
             "component": {"type": "string", "description": "Forsta komponenten."},
             "signal": {"type": "string", "description": "Forsta signalen."},
             "other_component": {"type": "string", "description": "Andra komponenten."},
             "other_signal": {"type": "string", "description": "Andra signalen."},
             "connected_to": {"type": "array",
                              "description": "Vad forsta signalen ar kopplad till efterat.",
                              "items": _ANSLUTNINGSPOST}},
            ["connected", "component", "signal", "other_component",
             "other_signal", "connected_to"]),
    _YTOR_BETEENDE,
    _kod_connect_signals,
)


# ---- disconnect_signals --------------------------------------------------

def _kod_disconnect_signals(argument):
    _sparra("disconnect_signals", argument)
    return _mall(["_komp", "_svara"], ["_sig", "_anslutna_bet"], [
        "a = _sig(_komp(%s), %s)" % (lit(argument["component"]),
                                     lit(argument["signal"])),
        "b = _sig(_komp(%s), %s)" % (lit(argument["other_component"]),
                                     lit(argument["other_signal"])),
        "if not a.disconnect(b):",
        '    raise ValueError("VC kunde inte koppla isar " + a.Name'
        ' + " och " + b.Name)',
        '_svara({"disconnected": True, "component": %s, "signal": a.Name,'
        % lit(argument["component"]),
        '        "other_component": %s, "other_signal": b.Name,'
        % lit(argument["other_component"]),
        '        "connected_to": _anslutna_bet(a)})',
    ])


_lagg(
    "disconnect_signals",
    "Kopplar isar tva signaler. Bada maste namnges - domanen har inget "
    "verktyg som river alla kopplingar pa en gang, eftersom en oavsiktligt "
    "bred isarkoppling inte gar att se i godkannandekons enda rad.",
    "write",
    params({"component": ARG_KOMPONENT, "signal": ARG_SIGNAL,
            "other_component": dict(ARG_KOMPONENT,
                                    description="Den andra komponentens namn."),
            "other_signal": dict(ARG_SIGNAL,
                                 description="Signalens namn pa den andra komponenten.")},
           ["component", "signal", "other_component", "other_signal"]),
    returns({"disconnected": {"type": "boolean",
                              "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Forsta komponenten."},
             "signal": {"type": "string", "description": "Forsta signalen."},
             "other_component": {"type": "string", "description": "Andra komponenten."},
             "other_signal": {"type": "string", "description": "Andra signalen."},
             "connected_to": {"type": "array",
                              "description": "Vad som ar kvar kopplat efterat.",
                              "items": _ANSLUTNINGSPOST}},
            ["disconnected", "component", "signal", "other_component",
             "other_signal", "connected_to"]),
    _YTOR_BETEENDE,
    _kod_disconnect_signals,
)


# ---- create_signal_map ---------------------------------------------------

def _kod_create_signal_map(argument):
    _sparra("create_signal_map", argument)
    _krav_ickenegativ("create_signal_map", argument, "port_count")
    konstant = argument["map_type"]
    namn = lit(argument["name"])
    rader = [
        "k = _komp(%s)" % lit(argument["component"]),
    ] + _krav_yta("k", "createBehaviour", "create_signal_map") + [
        "if k.findBehaviour(%s) is not None:" % namn,
        '    raise ValueError(k.Name + " har redan ett beteende som heter "'
        ' + %s)' % namn,
        "try:",
        "    typ = %s" % konstant,
        "except NameError:",
        "    raise ValueError(%s)" % _txt(
            "den har VC:n saknar konstanten " + konstant
            + "; kor signal_types for att se vilka typer som finns"),
        "m = k.createBehaviour(typ, %s)" % namn,
        "if m is None:",
        '    raise ValueError("VC skapade ingen signalkarta som heter " + %s)' % namn,
    ]
    if "port_count" in argument:
        rader += (_krav_yta("m", "PortCount", "create_signal_map med port_count")
                  + ["m.PortCount = %d" % argument["port_count"]])
    rader += [
        '_svara({"created": True, "component": k.Name, "name": m.Name,',
        '        "type": %s, "type_id": _enkelt(m.Type),' % _txt(konstant),
        '        "ports": int(m.PortCount) if hasattr(m, "PortCount") else 0})',
    ]
    return _mall(["_komp", "_enkelt", "_svara"], [], rader)


_lagg(
    "create_signal_map",
    "Skapar en signalkarta pa en komponent, med valfritt antal portar. Bara "
    "de tva karttyper VC faktiskt har en konstant for gar att skapa; "
    "heltals- och textkartor finns som typer men saknar konstant och kan "
    "darfor inte skapas fran Python.",
    "write",
    params({"component": ARG_KOMPONENT,
            "name": dict(ARG_KARTA, description="Namnet den nya kartan ska fa."),
            "map_type": {"type": "string",
                         "enum": [namn for namn, _b in KARTTYPER],
                         "description": "VC:s konstant for karttypen."},
            "port_count": {"type": "integer",
                           "description": ("Antal portar kartan ska fa. "
                                           "Utelamnad lamnar VC:s eget antal.")}},
           ["component", "name", "map_type"]),
    returns({"created": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "name": {"type": "string", "description": "Kartans namn."},
             "type": {"type": "string", "description": "Typkonstanten som anvandes."},
             "type_id": RET_TYP_ID,
             "ports": {"type": "integer", "description": "Antal portar efterat."}},
            ["created", "component", "name", "type", "ports"]),
    _YTOR_BETEENDE,
    _kod_create_signal_map,
)


# ---- signal_map_set_port -------------------------------------------------

def _kod_signal_map_set_port(argument):
    _sparra("signal_map_set_port", argument)
    _krav_ickenegativ("signal_map_set_port", argument, "port")
    rader = [
        "k = _komp(%s)" % lit(argument["component"]),
        "m = _karta(k, %s)" % lit(argument["map"]),
        "s = _sig(k, %s)" % lit(argument["signal"]),
        "_sparra_karta(m, %s)" % _txt("signal_map_set_port"),
    ] + _krav_yta("m", "setPortSignal", "signal_map_set_port") + [
        "if %d >= int(m.PortCount):" % argument["port"],
        '    raise ValueError("porten finns inte; kartan har " '
        '+ str(int(m.PortCount)) + " portar")',
        "m.setPortSignal(%d, s)" % argument["port"],
    ]
    if "port_name" in argument:
        rader += [
        ] + _krav_yta("m", "setPortName", "signal_map_set_port med port_name") + [
            "m.setPortName(%d, %s)" % (argument["port"], lit(argument["port_name"])),
        ]
    rader += [
        'namn = m.getPortName(%d) if hasattr(m, "getPortName") else None'
        % argument["port"],
        '_svara({"set": True, "component": k.Name, "map": m.Name,',
        '        "port": %d, "signal": s.Name, "port_name": namn})'
        % argument["port"],
    ]
    return _mall(["_komp", "_svara"], ["_karta", "_sig", "_sparra_karta"],
                 rader)


_lagg(
    "signal_map_set_port",
    "Satter vilken signal en port i en signalkarta bar, och valfritt portens "
    "namn. Signalen maste ligga pa samma komponent som kartan - det ar sa "
    "VC:s setPortSignal fungerar. Kartan maste redan ha porten; oka i sa fall "
    "port_count med create_signal_map eller lat kartan vaxa i VC.",
    "write",
    params({"component": ARG_KOMPONENT, "map": ARG_KARTA, "port": ARG_PORT,
            "signal": ARG_SIGNAL,
            "port_name": {"type": "string",
                          "description": ("Namn att ge porten. Utelamnat lamnas "
                                          "portens namn orort.")}},
           ["component", "map", "port", "signal"]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "map": {"type": "string", "description": "Kartans namn."},
             "port": {"type": "integer", "description": "Portens index."},
             "signal": {"type": "string", "description": "Signalen porten nu bar."},
             "port_name": {"type": ["string", "null"],
                           "description": "Portens namn efterat, eller null om VC saknar getPortName."}},
            ["set", "component", "map", "port", "signal"]),
    _YTOR_BETEENDE,
    _kod_signal_map_set_port,
)


# ---- signal_map_clear_port -----------------------------------------------

def _kod_signal_map_clear_port(argument):
    _sparra("signal_map_clear_port", argument)
    _krav_ickenegativ("signal_map_clear_port", argument, "port")
    port = argument["port"]
    return _mall(["_komp", "_svara"], ["_karta", "_sparra_karta"], [
        "k = _komp(%s)" % lit(argument["component"]),
        "m = _karta(k, %s)" % lit(argument["map"]),
        "_sparra_karta(m, %s)" % _txt("signal_map_clear_port"),
    ] + _krav_yta("m", "disconnect", "signal_map_clear_port")
      + _krav_yta("m", "setPortSignal", "signal_map_clear_port") + [
        "if %d >= int(m.PortCount):" % port,
        '    raise ValueError("porten finns inte; kartan har " '
        '+ str(int(m.PortCount)) + " portar")',
        # Tva steg, och bada behovs: disconnect river portens fjarrkopplingar,
        # setPortSignal utan signal tar bort portens egen signal. Bara det
        # forsta hade lamnat en port som fortfarande bar en signal.
        "m.disconnect(%d)" % port,
        "m.setPortSignal(%d)" % port,
        'kvar = m.getInternalPortSignal(%d) '
        'if hasattr(m, "getInternalPortSignal") else None' % port,
        '_svara({"cleared": True, "component": k.Name, "map": m.Name,',
        '        "port": %d,' % port,
        '        "signal": kvar.Name if kvar is not None else None})',
    ])


_lagg(
    "signal_map_clear_port",
    "Tommer en port i en signalkarta: river portens fjarrkopplingar och tar "
    "bort dess signal. Svaret bar vad porten star pa efterat, sa en halvt "
    "utford tomning syns i stallet for att tigas ihjal.",
    "write",
    params({"component": ARG_KOMPONENT, "map": ARG_KARTA, "port": ARG_PORT},
           ["component", "map", "port"]),
    returns({"cleared": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "map": {"type": "string", "description": "Kartans namn."},
             "port": {"type": "integer", "description": "Portens index."},
             "signal": {"type": ["string", "null"],
                        "description": "Signalen porten bar efterat; null nar den ar tom."}},
            ["cleared", "component", "map", "port", "signal"]),
    _YTOR_BETEENDE,
    _kod_signal_map_clear_port,
)


# ---- signal_map_connect --------------------------------------------------

def _kod_signal_map_connect(argument):
    _sparra("signal_map_connect", argument)
    _krav_ickenegativ("signal_map_connect", argument, "port")
    _krav_ickenegativ("signal_map_connect", argument, "other_port")
    port, annan = argument["port"], argument["other_port"]
    rader = [
        "k = _komp(%s)" % lit(argument["component"]),
        "m = _karta(k, %s)" % lit(argument["map"]),
        "k2 = _komp(%s)" % lit(argument["other_component"]),
        "m2 = _karta(k2, %s)" % lit(argument["other_map"]),
        "_sparra_karta(m, %s)" % _txt("signal_map_connect"),
        "_sparra_karta(m2, %s)" % _txt("signal_map_connect"),
    ]
    rader += _krav_yta("m", "connect", "signal_map_connect")
    rader += _krav_yta("m", "getAllConnectedPorts", "signal_map_connect")
    rader += [
        "if %d >= int(m.PortCount) or %d >= int(m2.PortCount):" % (port, annan),
        '    raise ValueError("porten finns inte; kartorna har "',
        '                     + str(int(m.PortCount)) + " respektive "',
        '                     + str(int(m2.PortCount)) + " portar")',
        "m.connect(%d, m2, %d)" % (port, annan),
        # connect() lamnar inget returvarde (api.xml: None), sa utfallet maste
        # LASAS. En fjarrkoppling som VC tyst inte gjorde far aldrig se ut som
        # en lyckad (S1).
        "if %d not in m.getAllConnectedPorts():" % port,
        "    raise ValueError(%s)" % _txt(
            "VC gjorde ingen fjarrkoppling; porten star kvar som okopplad"),
        "yttre = []",
        'if hasattr(m, "getConnectedExternalSignals"):',
        "    for e in m.getConnectedExternalSignals(%d):" % port,
        "        ke = e.Component",
        '        yttre.append({"component": ke.Name if ke is not None else None,',
        '                      "behaviour": e.Name})',
        '_svara({"connected": True, "component": k.Name, "map": m.Name,',
        '        "port": %d, "other_component": k2.Name,' % port,
        '        "other_map": m2.Name, "other_port": %d,' % annan,
        '        "external": yttre})',
    ]
    return _mall(["_komp", "_svara"], ["_karta", "_sparra_karta"], rader)


_lagg(
    "signal_map_connect",
    "Fjarrkopplar en port i en signalkarta till en port i en annan komponents "
    "signalkarta. Det ar sa tva stationer kopplas ihop pa signalniva utan att "
    "en signal behover finnas i bada komponenterna. VC lamnar inget svar pa "
    "kopplingen, sa verktyget laser tillbaka portens kopplingslista och kastar "
    "om den star kvar okopplad.",
    "write",
    params({"component": ARG_KOMPONENT, "map": ARG_KARTA, "port": ARG_PORT,
            "other_component": dict(ARG_KOMPONENT,
                                    description="Den andra komponentens namn."),
            "other_map": dict(ARG_KARTA,
                              description="Signalkartans namn pa den andra komponenten."),
            "other_port": dict(ARG_PORT,
                               description="Portens index i den andra kartan.")},
           ["component", "map", "port", "other_component", "other_map",
            "other_port"]),
    returns({"connected": {"type": "boolean",
                           "description": "Alltid true; en utebliven koppling kastar."},
             "component": {"type": "string", "description": "Forsta komponenten."},
             "map": {"type": "string", "description": "Forsta kartan."},
             "port": {"type": "integer", "description": "Porten i forsta kartan."},
             "other_component": {"type": "string", "description": "Andra komponenten."},
             "other_map": {"type": "string", "description": "Andra kartan."},
             "other_port": {"type": "integer", "description": "Porten i andra kartan."},
             "external": {"type": "array",
                          "description": "Signalerna porten nu ar kopplad till.",
                          "items": _ANSLUTNINGSPOST}},
            ["connected", "component", "map", "port", "other_component",
             "other_map", "other_port", "external"]),
    _YTOR_BETEENDE,
    _kod_signal_map_connect,
)


# ---- set_signal_map_direction --------------------------------------------

def _kod_set_signal_map_direction(argument):
    _sparra("set_signal_map_direction", argument)
    etikett = argument["direction"]
    konstant = dict(RIKTNINGAR)[etikett]
    return _mall(["_komp", "_svara"],
                 ["_karta", "_riktnamn", "_sparra_karta"], [
        "k = _komp(%s)" % lit(argument["component"]),
        "m = _karta(k, %s)" % lit(argument["map"]),
        "_sparra_karta(m, %s)" % _txt("set_signal_map_direction"),
    ] + _krav_yta("m", "Direction", "set_signal_map_direction") + [
        "try:",
        "    onskad = %s" % konstant,
        "except NameError:",
        "    raise ValueError(%s)" % _txt(
            "den har VC:n saknar konstanten " + konstant),
        # Tilldelning i stallet for m.trySetDirection(onskad). Bada satter
        # riktningen; skillnaden ar att skrivgrinden SER en tilldelning till
        # ett attribut men inte ett anrop som heter trySetDirection, och ett
        # skrivande verktyg vars kod grinden inte kan se skulle kunna ga
        # genom exec utan godkannande. Utfallet gar inte forlorat: VC kan
        # neka riktningen, sa den lases tillbaka och jamfors.
        "m.Direction = onskad",
        "if m.Direction != onskad:",
        "    raise ValueError(%s)" % _txt(
            "VC godtog inte den nya riktningen; kartan kunde inte sattas "
            "till " + etikett),
        '_svara({"set": True, "component": k.Name, "map": m.Name,',
        '        "direction": _riktnamn(m.Direction)})',
    ])


_lagg(
    "set_signal_map_direction",
    "Satter en signalkartas riktning: input, output eller undefined. Det ar "
    "det enda stallet i VC dar en riktning finns, och det ar den som ger "
    "signalinventeringen sina in- och utsignaler. VC kan neka bytet; da "
    "kastar verktyget i stallet for att svara ja.",
    "write",
    params({"component": ARG_KOMPONENT, "map": ARG_KARTA,
            "direction": {"type": "string",
                          "enum": [e for e, _k in RIKTNINGAR],
                          "description": "Riktningen kartans portar ska fa."}},
           ["component", "map", "direction"]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett nekat byte kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "map": {"type": "string", "description": "Kartans namn."},
             "direction": RET_RIKTNING},
            ["set", "component", "map", "direction"]),
    _YTOR_BETEENDE,
    _kod_set_signal_map_direction,
)


# ---- set_behaviour_property ----------------------------------------------

def _kod_set_behaviour_property(argument):
    _sparra("set_behaviour_property", argument)
    prop = lit(argument["property"])
    return _mall(["_komp", "_enkelt", "_svara"], ["_bet", "_egenskaper"], [
        "k = _komp(%s)" % lit(argument["component"]),
        "b = _bet(k, %s)" % lit(argument["behaviour"]),
        "p = None",
        "for q in b.Properties:",
        "    if q.Name == %s:" % prop,
        "        p = q",
        "if p is None:",
        '    raise ValueError(b.Name + " har ingen egenskap som heter " + %s)' % prop,
        "p.Value = %s" % lit(argument["value"]),
        '_svara({"set": True, "component": k.Name, "behaviour": b.Name,',
        '        "property": p.Name, "value": _enkelt(p.Value),',
        '        "properties": _egenskaper(b)})',
    ])


_lagg(
    "set_behaviour_property",
    "Satter en installningsegenskap pa ett beteende - det ar sa en "
    "egenskapsadapter binds till sin signal och sin komponentegenskap. "
    "Egenskapsnamnet maste komma ur list_property_adapters; ett uppfunnet "
    "namn kastar (I9).",
    "write",
    params({"component": ARG_KOMPONENT, "behaviour": ARG_BETEENDE,
            "property": {"type": "string",
                         "description": "Egenskapens namn pa beteendet."},
            "value": dict(ARG_VARDE, description=(
                "Det nya vardet. Ar det en signalbindning ar vardet signalens "
                "namn - och da avvisas en tagg markt sakerhet."))},
           ["component", "behaviour", "property", "value"]),
    returns({"set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "component": {"type": "string", "description": "Komponenten."},
             "behaviour": {"type": "string", "description": "Beteendets namn."},
             "property": {"type": "string", "description": "Egenskapens namn."},
             "value": RET_VARDE,
             "properties": {"type": "array",
                            "description": "Beteendets alla egenskaper efterat.",
                            "items": _EGENSKAPSPOST}},
            ["set", "component", "behaviour", "property", "value", "properties"]),
    _YTOR_BETEENDE,
    _kod_set_behaviour_property,
)
