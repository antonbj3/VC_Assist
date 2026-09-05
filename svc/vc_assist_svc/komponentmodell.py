# -*- coding: utf-8 -*-
"""Komponentmodellen som DATA: specens minsta uppsattningar, korbara.

`docs/spec/49_komponentmodellen.md` beskriver i text vad en TRANSPORTOR, en
MATARE, en SANKA och en BUFFERT minst behover for att kunna kopplas ihop och
bara material. Den har modulen ar samma sak som data, och darfor tre saker
som texten inte kan vara:

1. **En byggare.** `bygg(klass, namn)` genererar VC-koden ur kravlistan, inte
   ur en handskriven mall. Andras kravet andras bygget.
2. **En domare.** `granska(aterlast)` laser tillbaka en byggd komponent och
   sager vilket krav som fattas -- vid NAMN. VC sjalvt sager ingenting: en
   komponent som saknar sitt flodesbeteende ger `canConnect() == False` utan
   ett enda felmeddelande (MATT M-40). Domen ar var, inte VC:s.
3. **En trasig fixtur.** `bygg(..., utelamna="bana")` bygger allt UTOM ett
   krav. Utan den ar kravlistan bara en asikt: ett krav som aldrig provats
   utelamnat ar inte matt som krav.

Harkomst star pa varje rad. Tre marken, samma som specens:

    MATT <M-nr>     matt i en korande VC, mätningen namngiven
    BELAGT <kalla>  star ordagrant i en kallfil under docs/referens/
    HYPOTES         harledd, inte provad. Far aldrig sta omarkerad.

Kravlistorna och specens tabeller far inte glida isar: `tests/enhet/
test_komponentmodell.py` laser bada och faller om en rad saknas i den ena.

Genererad kod: Stackless Python 2.7 (VC 4.10) OCH 3.x (VC 5.0), varldsenhet
millimeter (M-33), varje strang genom `_s()` (M-05), inga getattr/setattr/
eval (I9: api_index-validatorn maste kunna doma varje namn).
"""
from __future__ import annotations

import collections

from .verktyg.kodmall import bygg as _mall, lit, tal

# Faltnamnet ar detsamma pa bada sidor av en koppling. HYPOTES E3 i spec 49:
# aldrig matt med SKILDA namn, sa likheten ar ett antagande vi haller, inte
# ett krav vi visat.
FALTNAMN = "Flow"

# Flodesfaltets tre egenskaper (MATT B00, sondera_falt 2026-09-04).
EGENSKAP_BETEENDE = "Container"
EGENSKAP_PORT = "Port"
EGENSKAP_PORTNAMN = "PortName"


# ---- kravens form ----------------------------------------------------------

Krav = collections.namedtuple(
    "Krav", "nyckel slag namn konstant roll harkomst utan")
"""Ett krav i en minsta uppsattning.

nyckel    modellens eget namn ("bana"); det man utelamnar med `utelamna=`
slag      "beteende" | "ram" | "granssnitt" | "egenskap"
namn      namnet objektet far i VC ("Path")
konstant  VC-konstanten det skapas med ("VC_ONEWAYPATH"), "" for egenskaper
roll      vad det GOR i uppsattningen
harkomst  MATT/BELAGT/HYPOTES med kalla
utan      vad som hander om det fattas -- felet domaren skriver
"""

Granssnitt = collections.namedtuple(
    "Granssnitt", "nyckel namn riktning ram beteende kontakttyp falttyp harkomst utan")

Regel = collections.namedtuple("Regel", "id kravet harkomst felet")

Klass = collections.namedtuple(
    "Klass", "namn rubrik beteenden ramar granssnitt egenskaper parbarhet")

Brist = collections.namedtuple("Brist", "nyckel slag namn konstant meddelande")


class Rapport(object):
    """Domen over en byggd komponent. Tom brist-lista = uppsattningen hel."""

    def __init__(self, klass, komponent, brister):
        self.klass = klass
        self.komponent = komponent
        self.brister = list(brister)

    @property
    def hel(self):
        return not self.brister

    @property
    def kopplingsbar(self):
        """Specens dom: en uppsattning med en brist far INTE kunna kopplas."""
        return self.hel

    def text(self):
        if self.hel:
            return "%s: uppsattningen for %s ar hel" % (self.komponent, self.klass)
        return "\n".join(b.meddelande for b in self.brister)

    def saknade_beteenden(self):
        return [b.namn for b in self.brister if b.slag == "beteende"]


# ---- de fyra minsta uppsattningarna ----------------------------------------
#
# Varje rad: vad, vilket VC-namn, vilken konstant, vilken roll, harkomst, och
# vad som hander om raden fattas. Den sista kolumnen ar den som gor listan till
# en grind i stallet for en beskrivning.

_UTAN_FLODESBETEENDE = (
    u"utan det finns ingen vcConnector att binda flödesfältets %s till, %s "
    u"står kvar på None, och canConnect blir False utan att VC säger ett ord "
    u"(MÄTT M-40, E6)" % (EGENSKAP_PORT, EGENSKAP_BETEENDE))

_UTAN_GRANSSNITT = (
    u"utan det finns ingenting att anropa canConnect PÅ: findBehaviour ger "
    u"None och kopplingen kan inte ens efterfrågas (MÄTT M-40: koppla-receptet "
    u"föll på exakt det)")

_BANA = Krav(
    nyckel="bana", slag=u"beteende", namn="Path", konstant="VC_ONEWAYPATH",
    roll=u"flödesbärare: bär både vcFlow och vcContainer, alltså kontakter OCH lagring",
    harkomst=u"BELAGT api.xml vcMotionPath <parents>vcBehaviour vcFlow vcContainer</parents>; MÄTT C0/C3",
    utan=u"beteendet Path (VC_ONEWAYPATH) saknas: " + _UTAN_FLODESBETEENDE)

_SKAPARE = Krav(
    nyckel="skapare", slag=u"beteende", namn="Creator",
    konstant="VC_COMPONENTCREATOR",
    roll=u"producerar komponenter ur en mall och lämnar dem genom sin utkontakt",
    harkomst=u"MÄTT D1/D5 (2026-09-04); py2-bindningen rapporterar klassen som rResourceCreator",
    utan=u"beteendet Creator (VC_COMPONENTCREATOR) saknas: ingenting produceras, och "
         + _UTAN_FLODESBETEENDE)

_BEHALLARE = Krav(
    nyckel="behallare", slag=u"beteende", namn="Sink",
    konstant="VC_COMPONENTCONTAINER",
    roll=u"lagrar mottagna komponenter; vcSimContainer med Input och Output",
    harkomst=u"MÄTT D0/D2 (2026-09-04): VC_CONTAINER ger None, VC_COMPONENTCONTAINER ger vcSimContainer",
    utan=u"beteendet Sink (VC_COMPONENTCONTAINER) saknas: det finns ingenstans "
         u"att ta emot, och " + _UTAN_FLODESBETEENDE)


def _granssnittskrav(nyckel, namn, riktning, ram, beteende, kontakttyp):
    return Granssnitt(
        nyckel=nyckel, namn=namn, riktning=riktning, ram=ram,
        beteende=beteende, kontakttyp=kontakttyp, falttyp="VC_FLOWFIELD",
        harkomst=u"MÄTT punkt 1-3 (interface, section och field skapas); "
                 u"BELAGT Create3D BehaviorType.OneToOneInterface",
        utan=u"gränssnittet %s (VC_ONETOONEINTERFACE) saknas: %s"
             % (namn, _UTAN_GRANSSNITT))


def _ramkrav(nyckel, namn, roll):
    return Krav(
        nyckel=nyckel, slag=u"ram", namn=namn, konstant="VC_FRAME", roll=roll,
        harkomst=u"MÄTT M-40 villkor 1: utan rebuild() står ramens verkliga "
                 u"läge kvar i nodens ursprung och PathLength blir 0.0",
        utan=u"ramen %s (VC_FRAME) saknas: sektionen får ingen Frame, och en "
             u"bana utan två åtskilda ramar får PathLength 0.0 — den tar inte "
             u"emot något och matningen uppströms tystnar (MÄTT M-40, linje M41B)"
             % namn)


_TRANSPORTOR = Klass(
    namn="transportor",
    rubrik=u"TRANSPORTÖR: tar emot i ena änden, lämnar i den andra",
    beteenden=(_BANA,),
    ramar=(_ramkrav("ram_in", "PathIn", u"banans början och in-sektionens läge"),
           _ramkrav("ram_ut", "PathOut", u"banans slut och ut-sektionens läge")),
    granssnitt=(
        _granssnittskrav("in_granssnitt", "InInterface", "in", "ram_in",
                         "bana", "VC_CONNECTOR_INPUT"),
        _granssnittskrav("ut_granssnitt", "OutInterface", "ut", "ram_ut",
                         "bana", "VC_CONNECTOR_OUTPUT"),
    ),
    egenskaper=(
        Krav("path", u"egenskap", "Path", "", u"banans väg: [PathIn, PathOut]",
             u"MÄTT: Path = [ram_in, ram_ut] tas emot",
             u"egenskapen Path är tom: PathLength blir 0.0 och banan bär ingenting"),
        Krav("uppdaterad", u"egenskap", "update()", "",
             u"räknar om PathLength efter att Path satts",
             u"MÄTT M-40 villkor 2: p.Path satt ger PathLength 0.0; p.update() ger 3000.0",
             u"update() utelämnad: PathLength är 0.0 fast ramarna står 3000 mm "
             u"isär, banan tar inte emot något och mataren uppströms producerar "
             u"noll (MÄTT M-40, linje M41B: 0 produkter på 7 intervall)"),
        Krav("hastighet", u"egenskap", "Speed", "", u"mm/s längs banan",
             u"MÄTT M-41: uppmätt rörelse 250.0000 mm/s mot Speed 250.0, spridning 0.0000",
             u"Speed osatt: förvalet gäller, och vilket det är har ingen mätt"),
    ),
    parbarhet=(u"in: matare, transportor, buffert",
               u"ut: transportor, buffert, sanka"),
)

_BUFFERT = Klass(
    namn="buffert",
    rubrik=u"BUFFERT: en bana som HÅLLER KVAR N komponenter",
    beteenden=(_BANA,),
    ramar=_TRANSPORTOR.ramar,
    granssnitt=_TRANSPORTOR.granssnitt,
    egenskaper=_TRANSPORTOR.egenskaper + (
        Krav("ackumulera", u"egenskap", "Accumulate", "",
             u"låter komponenter köa sig i stället för att bara passera",
             u"HYPOTES D4: aldrig mätt med Accumulate=False mot True på samma bana",
             u"Accumulate=False: komponenterna passerar utan att köa sig, och "
             u"buffert blir samma sak som transportör"),
        Krav("kapacitet", u"egenskap", "Capacity", "", u"antal platser",
             u"HYPOTES D4: kapacitetens verkan är aldrig mätt",
             u"Capacity osatt: förvalet gäller, och hur många platser en bana "
             u"har som förval är inte mätt"),
    ),
    parbarhet=(u"in: matare, transportor, buffert",
               u"ut: transportor, buffert, sanka"),
)

_MATARE = Klass(
    namn="matare",
    rubrik=u"MATARE: skapar komponenter och lämnar dem nedströms",
    beteenden=(_SKAPARE,),
    ramar=(_ramkrav("ram_ut", "Out", u"utgångens läge"),),
    granssnitt=(
        _granssnittskrav("ut_granssnitt", "OutInterface", "ut", "ram_ut",
                         "skapare", "VC_CONNECTOR_OUTPUT"),
    ),
    egenskaper=(
        Krav("mall", u"egenskap", "TemplateComponent", "",
             u"komponenten som kopieras vid varje intervall",
             u"MÄTT M-40: tar en komponent som STÅR i scenen, även en utan URI "
             u"och utan VCID; Part behöver inte peka på en lösbar URI",
             u"TemplateComponent osatt: skaparen har ingenting att kopiera"),
        Krav("intervall", u"egenskap", "Interval", "", u"sekunder mellan produkter",
             u"MÄTT M-41: åtta mellanrum, alla exakt 4.000 s mot Interval 4.0",
             u"Interval osatt: förvalet gäller och takten är inte mätt"),
        Krav("grans", u"egenskap", "Limit", "", u"högsta antal produkter",
             u"MÄTT M-40/D5: Limit osatt gav noll produkter på 6 s; Limit=10 "
             u"slutade tyst vid t=50 och såg då ut precis som en trasig matare",
             u"Limit osatt: mataren stannar tyst när förvalet nås, och en "
             u"stannad matare ser exakt ut som en trasig"),
        Krav("pa", u"egenskap", "Enabled", "", u"skaparen är igång",
             u"MÄTT M-40: Enabled rapporterades True i alla tre linjerna",
             u"Enabled=False: ingenting produceras"),
    ),
    parbarhet=(u"in: — (en matare tar inte emot)",
               u"ut: transportor, buffert, sanka"),
)

_SANKA = Klass(
    namn="sanka",
    rubrik=u"SÄNKA: tar emot komponenter och behåller dem",
    beteenden=(_BEHALLARE,),
    ramar=(_ramkrav("ram_in", "In", u"ingångens läge"),),
    granssnitt=(
        _granssnittskrav("in_granssnitt", "InInterface", "in", "ram_in",
                         "behallare", "VC_CONNECTOR_INPUT"),
    ),
    egenskaper=(
        Krav("kapacitet", u"egenskap", "Capacity", "", u"hur många som får plats",
             u'BELAGT api.xml vcContainer.Capacity: "the maximum number of '
             u'components that can be stored in the container at any given time"',
             u"Capacity för låg: sänkan blir full och stoppar linjen uppströms"),
    ),
    parbarhet=(u"in: matare, transportor, buffert",
               u"ut: — (en sänka lämnar inte ifrån sig)"),
)

# Vad mätningen har REFUTERAT. En rad här är ett påstående som stod i en källa
# och som VC svarade nej på. Den hör hemma i modellen, inte bara i en mätning:
# nästa gång någon läser api.xml och tror sig ha hittat ett krav ska raden möta
# hen här.
Refuterat = collections.namedtuple("Refuterat", "namn pastod matning utfall")

REFUTERAT = (
    Refuterat(
        namn="ContentVisible",
        pastod=u'BELAGT api.xml vcContainer.ContentVisible (W): "Sets the '
               u'visibility of components stored in the container."',
        matning="M-101",
        utfall=u"finns INTE på det beteende VC_COMPONENTCONTAINER faktiskt ger "
               u"(vcSimContainer). Tilldelningen svarar "
               u'"NameError: Attribute or method \'ContentVisible\' not found." '
               u"— alltså VC:s NameError, inte Pythons AttributeError (samma "
               u"fälla som M-40 beskrev för Connectors). api.xml dokumenterar "
               u"egenskapen på typen vcContainer; py2-bindningens instans bär "
               u"den inte. En BELAGD rad är inte en mätt rad."),
)


KLASSER = collections.OrderedDict((
    ("transportor", _TRANSPORTOR),
    ("matare", _MATARE),
    ("sanka", _SANKA),
    ("buffert", _BUFFERT),
))

# Vilket krav den trasiga fixturen utelämnar per klass. Alltid det som BÄR
# flödet: då finns gränssnittet kvar, canConnect GÅR att anropa, och False
# betyder något. Utelämnas gränssnittet i stället går frågan inte att ställa,
# och "gick inte" hade blivit tvetydigt.
TRASIG_UTELAMNING = collections.OrderedDict((
    ("transportor", "bana"),
    ("matare", "skapare"),
    ("sanka", "behallare"),
    ("buffert", "bana"),
))

# Vilka par specen säger ska gå ihop: (ut-sida, in-sida, härkomst).
# Härkomsten är inte pynt: tre av paren är kedjan i M-101 och alltså MÄTTA,
# två är HÄRLEDDA ur R5 och aldrig byggda. Utan kolumnen hade tabellen sett
# ut som fem mätningar när den är tre.
PAR_SOM_SKA_GA = (
    ("matare", "transportor", u"MÄTT M-101 (kedjans första led)"),
    ("transportor", "buffert", u"MÄTT M-101 (kedjans andra led)"),
    ("buffert", "sanka", u"MÄTT M-101 (kedjans tredje led)"),
    ("transportor", "transportor",
     u"HYPOTES: följer av R5, aldrig byggt som par i M-101"),
    ("matare", "sanka",
     u"HYPOTES: följer av R5, aldrig byggt som par i M-101"),
)

# Par som INTE ska gå ihop, och skälet.
PAR_SOM_INTE_GAR = (
    ("matare", "matare", u"båda sidor bär VC_CONNECTOR_OUTPUT; MÄTT M-67: "
                         u"ut mot ut ger canConnect False"),
    ("sanka", "sanka", u"båda sidor bär VC_CONNECTOR_INPUT"),
    ("sanka", "matare", u"sänkan har ingen utgång och mataren ingen ingång"),
)


# ---- matchningsregeln för canConnect ---------------------------------------
#
# Ordningen är VÅR provordning, inte VC:s. VC:s inre ordning är INTE mätt —
# canConnect ger ett enda False utan att säga vilket villkor som brast. Att
# skriva vår ordning som om den vore VC:s hade varit ett antagande i
# mätningskläder.

MATCHNINGSREGEL = (
    Regel("R1", u"båda sidor har ett beteende med gränssnittets namn, och det "
                u"beteendet är ett simuleringsgränssnitt (bär canConnect)",
          u"MÄTT M-40: koppla-receptet föll på findBehaviour som gav None",
          u"gränssnittet saknas — frågan går inte att ställa, och \"gick inte\" "
          u"vore tvetydigt"),
    Regel("R2", u"flödesfältets %s pekar på ett beteende (inte None)" % EGENSKAP_BETEENDE,
          u"MÄTT E0/E6 2026-09-04: med Port bundet och Container=None på båda "
          u"sidor är canConnect False och connectComponents False",
          u"canConnect returnerar False. VC säger INGENTING — ingen exception, "
          u"ingen logg, inget falskt returvärde någon annanstans"),
    Regel("R3", u"flödesfältets %s är ett heltal >= 0" % EGENSKAP_PORT,
          u"MÄTT M-40: Port = -1 ger canConnect False; MÄTT B3: Port tar ett "
          u"heltal (kontaktens Index), inte ett vcConnector-objekt",
          u"canConnect returnerar False, tyst. Ett fält med Port = -1 ser i "
          u"övrigt färdigbundet ut"),
    Regel("R4", u"bindningsordningen är %s FÖRE %s"
                % (EGENSKAP_BETEENDE, EGENSKAP_PORT),
          u"MÄTT M-40: Port satt först, sedan Container satt — Port är nu -1",
          u"Port nollställs till -1 av Container-tilldelningen. Kopplingen "
          u"faller på R3, av ett skäl som inte syns på raden där felet ser ut "
          u"att vara"),
    Regel("R5", u"ut-sidans kontakt är VC_CONNECTOR_OUTPUT och in-sidans "
                u"VC_CONNECTOR_INPUT",
          u"MÄTT M-67: ut mot ut ger canConnect False, connect False, "
          u"IsConnected False — och flyttar ingenting",
          u"canConnect returnerar False. Riktningen bor i kontakten, inte i "
          u"gränssnittets namn: ett gränssnitt som HETER OutInterface men bär "
          u"en Input-kontakt matchar som ingång"),
    Regel("R6", u"båda sektionernas fält har samma typ (VC_FLOWFIELD mot "
                u"VC_FLOWFIELD)",
          u'BELAGT Create3D ISimInterfaceSection.IsCompatibleWith: "True if '
          u'connection between these sections is possible"',
          u"canConnect returnerar False. Aldrig mätt med BLANDADE fälttyper — "
          u"regeln är belagd, inte mätt"),
    Regel("R7", u"fälten står i samma ORDNING i båda sektionerna",
          u'BELAGT api.xml vcSimInterfaceField.Index: "sections may have '
          u'compatible fields but cannot connect because the order of fields '
          u'differ in each section"',
          u"canConnect returnerar False. Aldrig mätt hos oss: alla våra "
          u"sektioner har exakt ett fält, så ordningen kan inte skilja"),
    Regel("R8", u"ett VC_ONETOONEINTERFACE är inte redan kopplat",
          u'BELAGT Create3D ISimInterface.Connect: "Thrown when interface '
          u'cannot be connected (it is one to one interface and already '
          u'connected ...)"',
          u"connect kastar i .NET. I Python-bindningen är utfallet INTE mätt — "
          u"vi vet inte om det blir False eller ett undantag"),
    Regel("R9", u"avståndet mellan gränssnitten spelar INGEN roll vid förvald "
                u"DistanceTolerance",
          u"MÄTT M-67: canConnect True med 1670 mm mellan komponenterna; "
          u"MÄTT punkt 9: förvalet är 1e9 mm och 360 grader",
          u"— ingen regel att brista mot. Raden står här därför att M-40:s "
          u"formulering \"canConnect är en geometrisk fråga\" är SKÄRPT av "
          u"M-67: det som fällde var ett fält med Port = -1, inte avståndet"),
)


# ---- domaren ---------------------------------------------------------------

def _egenskapskarta(post):
    ut = {}
    for p in post.get("properties_after") or []:
        ut[p.get("name")] = p.get("value")
    return ut


def granska(aterlast):
    """Domer en aterlast komponent mot sin klass minsta uppsattning.

    aterlast ar svaret ur bygg()-koden. Domen ar VAR: VC svarar bara False.
    Varje brist NAMNGER det som fattas, for ett fel som bara sager "gick inte"
    ar ingen grind.
    """
    klassnamn = aterlast.get("klass")
    if klassnamn not in KLASSER:
        raise KeyError("okand klass %r, valj bland %s"
                       % (klassnamn, list(KLASSER)))
    klass = KLASSER[klassnamn]
    komponent = aterlast.get("component") or "?"
    brister = []

    byggda = set()
    for b in aterlast.get("behaviours") or []:
        byggda.add(b.get("name"))
    for krav in klass.beteenden:
        if krav.namn not in byggda:
            brister.append(Brist(
                krav.nyckel, "beteende", krav.namn, krav.konstant,
                "%s: %s" % (komponent, krav.utan)))

    ramar = set(aterlast.get("features") or [])
    for krav in klass.ramar:
        if krav.namn not in ramar:
            brister.append(Brist(
                krav.nyckel, "ram", krav.namn, krav.konstant,
                "%s: %s" % (komponent, krav.utan)))

    # MÄTT M-40 villkor 2, som en riktig grind: en bana vars PathLength är 0.0
    # tar inte emot något, och matningen uppströms tystnar utan ett ord. Den
    # bristen syns inte på beteendelistan — beteendet FINNS, det bär bara
    # ingenting.
    if klassnamn in ("transportor", "buffert") and not brister:
        langd = (aterlast.get("aterlast") or {}).get("path_length")
        if not isinstance(langd, (int, float)) or isinstance(langd, bool) \
                or langd <= 0.0:
            brister.append(Brist(
                "uppdaterad", "egenskap", "PathLength", "",
                u"%s: banan har PathLength = %r. Ramarna byggdes inte om, "
                u"eller bana.update() kördes inte efter att Path sattes. "
                u"Banan tar inte emot något och mataren uppströms producerar "
                u"noll — tyst (MÄTT M-40, linje M41B)" % (komponent, langd)))

    poster = {}
    for g in aterlast.get("interfaces") or []:
        poster[g.get("name")] = g
    for krav in klass.granssnitt:
        post = poster.get(krav.namn)
        if post is None or krav.namn not in byggda:
            brister.append(Brist(
                krav.nyckel, "granssnitt", krav.namn, "VC_ONETOONEINTERFACE",
                "%s: %s" % (komponent, krav.utan)))
            continue
        egen = _egenskapskarta(post)
        if egen.get(EGENSKAP_BETEENDE) is None:
            brister.append(Brist(
                krav.nyckel, "bindning", krav.namn, "VC_FLOWFIELD",
                "%s: flodesfaltet i %s har %s = None. Regel %s: %s"
                % (komponent, krav.namn, EGENSKAP_BETEENDE,
                   MATCHNINGSREGEL[1].id, MATCHNINGSREGEL[1].felet)))
        port = egen.get(EGENSKAP_PORT)
        if not isinstance(port, int) or isinstance(port, bool) or port < 0:
            brister.append(Brist(
                krav.nyckel, "bindning", krav.namn, "VC_FLOWFIELD",
                "%s: flodesfaltet i %s har %s = %r. Regel %s: %s"
                % (komponent, krav.namn, EGENSKAP_PORT, port,
                   MATCHNINGSREGEL[2].id, MATCHNINGSREGEL[2].felet)))
    return Rapport(klassnamn, komponent, brister)


def varfor_inte(ut_sida, in_sida):
    """Vilken regel i MATCHNINGSREGEL som brister forst mellan tva aterlasta
    granssnitt. Returnerar (Regel, text) eller (None, "") nar allt haller.

    ut_sida/in_sida ar granssnittsposter ur bygg()-svaret."""
    for sida, roll, vantad in ((ut_sida, "ut-sidan", "VC_CONNECTOR_OUTPUT"),
                               (in_sida, "in-sidan", "VC_CONNECTOR_INPUT")):
        if not sida:
            return MATCHNINGSREGEL[0], "%s: %s" % (roll, MATCHNINGSREGEL[0].felet)
    for sida, roll in ((ut_sida, "ut-sidan"), (in_sida, "in-sidan")):
        egen = _egenskapskarta(sida)
        if egen.get(EGENSKAP_BETEENDE) is None:
            return MATCHNINGSREGEL[1], "%s: %s = None. %s" % (
                roll, EGENSKAP_BETEENDE, MATCHNINGSREGEL[1].felet)
        port = egen.get(EGENSKAP_PORT)
        if not isinstance(port, int) or isinstance(port, bool) or port < 0:
            return MATCHNINGSREGEL[2], "%s: %s = %r. %s" % (
                roll, EGENSKAP_PORT, port, MATCHNINGSREGEL[2].felet)
    ut_typ = (ut_sida.get("connector") or {}).get("type")
    in_typ = (in_sida.get("connector") or {}).get("type")
    if ut_typ is not None and in_typ is not None and ut_typ == in_typ:
        return MATCHNINGSREGEL[4], "bada sidor bar kontakttypen %s. %s" % (
            ut_typ, MATCHNINGSREGEL[4].felet)
    if ut_sida.get("field_type") != in_sida.get("field_type"):
        return MATCHNINGSREGEL[5], "ut-sidan har falttyp %r, in-sidan %r. %s" % (
            ut_sida.get("field_type"), in_sida.get("field_type"),
            MATCHNINGSREGEL[5].felet)
    return None, ""


# ---- byggaren --------------------------------------------------------------

_HJALP = '''
def _typnamn(o):
    return type(o).__name__


def _egenskaper(o):
    ut = []
    for p in o.Properties:
        ut.append({"name": p.Name, "value": _enkelt(p.Value)})
    return ut


def _hitta_egenskap(o, namn):
    for p in o.Properties:
        if p.Name == namn:
            return p
    return None


def _steg(logg, namn, funk):
    # Ett osakert steg. Undantaget ar ett MATT utfall och far inte doda
    # resten av bygget: en komponent som faller pa sitt tredje krav ska anda
    # kunna lasas tillbaka och domas pa de tva forsta.
    try:
        r = funk()
        logg.append({"steg": namn, "utfall": "ok", "resultat": _enkelt(r)})
        return True, r
    except Exception as e:
        logg.append({"steg": namn, "utfall": "fel",
                     "fel": _typnamn(e) + ": " + str(e)})
        return False, None


def _kontakt(beh, typ):
    # C1 (MATT 2026-09-04): valj pa Type, ALDRIG pa index. Banan bar Input pa
    # index 0 och Output pa 1; skaparen har omvand ordning. Ett index-val hade
    # varit gront pa banan och tyst fel pa mataren.
    if beh is None:
        return None
    for c in beh.Connectors:
        if c.Type == typ:
            return c
    return None


def _kontakter(beh):
    ut = []
    if beh is None:
        return ut
    for c in beh.Connectors:
        ut.append({"name": c.Name, "index": c.Index, "type": _enkelt(c.Type),
                   "connected": c.Connection is not None})
    return ut


def _beteenden(k):
    ut = []
    for b in k.Behaviours:
        ut.append({"name": b.Name, "type": _enkelt(b.Type), "class": _typnamn(b)})
    return ut


def _ramnamn(k):
    ut = []
    for f in k.RootFeature.Children:
        ut.append(f.Name)
    return ut


def _ram(k, namn, x, y, z, vrid):
    f = k.RootFeature.createFeature(VC_FRAME, namn)
    m = f.PositionMatrix
    m.P = vcVector.new(x, y, z)
    if vrid:
        m.rotateRelZ(vrid)
    f.PositionMatrix = m
    # MATT M-40 villkor 1: utan rebuild() star ramens VERKLIGA lage
    # (NodePositionMatrix) kvar i nodens ursprung fast PositionMatrix visar
    # det begarda. Tva ramar i origo ger PathLength 0.0.
    f.rebuild()
    return f


def _bind(logg, falt, kontakt, agare):
    # MATT M-40: Container FORST, Port sedan. Omvand ordning nollstaller Port
    # till -1, och ett falt med Port = -1 ger canConnect False utan att nagot
    # sags nagonstans. Ordningen ar hela skillnaden mellan en linje som
    # kopplar och en som star still.
    bundna = []
    beteendet = _hitta_egenskap(falt, EGENSKAP_BETEENDE)
    if beteendet is not None and agare is not None:
        def satt_beteende():
            beteendet.Value = agare
            return _enkelt(beteendet.Value)
        ok, _r = _steg(logg, "bind." + EGENSKAP_BETEENDE, satt_beteende)
        if ok and beteendet.Value is not None:
            bundna.append(EGENSKAP_BETEENDE)
    porten = _hitta_egenskap(falt, EGENSKAP_PORT)
    if porten is not None and kontakt is not None:
        def satt_port():
            porten.Value = kontakt.Index
            return _enkelt(porten.Value)
        ok, _r = _steg(logg, "bind." + EGENSKAP_PORT, satt_port)
        if ok and porten.Value is not None:
            bundna.append(EGENSKAP_PORT)
    namnet = _hitta_egenskap(falt, EGENSKAP_PORTNAMN)
    if namnet is not None and kontakt is not None:
        def satt_portnamn():
            namnet.Value = kontakt.Name
            return _enkelt(namnet.Value)
        ok, _r = _steg(logg, "bind." + EGENSKAP_PORTNAMN, satt_portnamn)
        if ok:
            bundna.append(EGENSKAP_PORTNAMN)
    return bundna


def _granssnitt(logg, k, namn, ram, falttyp, kontakt, agare):
    g = k.createBehaviour(VC_ONETOONEINTERFACE, namn)
    if g is None:
        raise ValueError("createBehaviour(VC_ONETOONEINTERFACE) gav None")
    sek = g.createSection(namn)
    if sek is None:
        # MATT punkt 2: createSection() UTAN namn ger None i den har
        # bindningen dar .NET kastar. Ett None som inte fangas har blir en
        # sektion som aldrig fanns och ett falt som aldrig skapades.
        raise ValueError("createSection gav None for " + namn)
    if ram is not None:
        sek.Frame = ram
    falt = sek.createField(falttyp, FALTNAMN)
    if falt is None:
        raise ValueError("createField gav None for " + namn)
    fore = _egenskaper(falt)
    bundna = _bind(logg, falt, kontakt, agare)
    kontaktpost = None
    if kontakt is not None:
        kontaktpost = {"name": kontakt.Name, "index": kontakt.Index,
                       "type": _enkelt(kontakt.Type)}
    return {"name": g.Name, "section": sek.Name,
            "frame": None if ram is None else ram.Name,
            "field": falt.Name, "field_type": _enkelt(falt.Type),
            "properties_before": fore, "properties_after": _egenskaper(falt),
            "bound": bundna, "connector": kontaktpost,
            "distance_tolerance": g.DistanceTolerance,
            "is_connected": bool(g.IsConnected)}


def _las_granssnitt(g):
    # Samma form som _granssnitt lamnar vid bygget, men last ur ett
    # BEFINTLIGT granssnitt. Det ar det som gor att varfor_inte() kan koras
    # pa VERKLIG VC-data i stallet for bara pa provfixturer.
    if g is None:
        return None
    post = {"name": g.Name, "section": None, "field": None,
            "field_type": None, "properties_after": [], "connector": None,
            "is_connected": bool(g.IsConnected)}
    for sek in g.Sections:
        post["section"] = sek.Name
        for falt in sek.Fields:
            post["field"] = falt.Name
            post["field_type"] = _enkelt(falt.Type)
            post["properties_after"] = _egenskaper(falt)
            break
        break
    return post


def _kontakttyp_i(g, komp):
    # Vilken kontakt faltets Port pekar pa, och vilken TYP den har. Riktningen
    # bor i kontakten (R5), inte i granssnittets namn: ett granssnitt som
    # HETER OutInterface men bar en Input-kontakt matchar som ingang.
    post = _las_granssnitt(g)
    if post is None:
        return None
    port = None
    for p in post["properties_after"]:
        if p["name"] == EGENSKAP_PORT:
            port = p["value"]
    if not isinstance(port, int) or isinstance(port, bool) or port < 0:
        return post
    for b in komp.Behaviours:
        try:
            kontakter = b.Connectors
        except (AttributeError, NameError):
            continue
        for c in kontakter:
            if c.Index == port:
                post["connector"] = {"name": c.Name, "index": c.Index,
                                     "type": _enkelt(c.Type)}
                return post
    return post


def _placera(k, x, y, z):
    # translateAbs ar RELATIV i absoluta axlar (M-11), sa ett absolut lage
    # skickas som skillnaden mot det nuvarande.
    m = k.PositionMatrix
    m.translateAbs(x - m.P.X, y - m.P.Y, z - m.P.Z)
    k.PositionMatrix = m
    return [m.P.X, m.P.Y, m.P.Z]
'''

_NAMNRADER = [
    "FALTNAMN = %s" % lit(FALTNAMN),
    "EGENSKAP_BETEENDE = %s" % lit(EGENSKAP_BETEENDE),
    "EGENSKAP_PORT = %s" % lit(EGENSKAP_PORT),
    "EGENSKAP_PORTNAMN = %s" % lit(EGENSKAP_PORTNAMN),
]

# _s kommer ur bryggans exec-globaler (pump.py:_kor). Samma kod kors ocksa som
# STARTSKRIPT (bridge_cmd, fore startSimulation()) och dar finns ingen brygga,
# darfor en reserv som bara binds nar namnet saknas.
_S_RESERV = """
try:
    _s
except NameError:
    def _s(x):
        try:
            if isinstance(x, unicode):
                return x.encode("utf-8")
        except NameError:
            pass
        return x
"""


def _inledning():
    return _S_RESERV.split("\n") + _NAMNRADER + _HJALP.split("\n")


def _nyko(namn):
    return [
        "app = getApplication()",
        "gammal = app.findComponent(%s)" % lit(namn),
        "if gammal is not None:",
        "    app.deleteComponent(gammal)",
        "k = app.createComponent()",
        "if k is None:",
        '    raise ValueError("createComponent gav ingen komponent")',
        "k.Name = %s" % lit(namn),
        "steg = []",
    ]


def _kropp(langd, bredd, hojd):
    return [
        "kropp = k.RootFeature.createFeature(VC_BLOCK, %s)" % lit("Kropp"),
        "matt = {%s: %s, %s: %s, %s: %s}" % (
            lit("Length"), tal(langd), lit("Width"), tal(bredd),
            lit("Height"), tal(hojd)),
        "for p in kropp.Properties:",
        "    if p.Name in matt:",
        "        p.Value = matt[p.Name]",
        "k.RootFeature.rebuild()",
    ]


def _matt(klassnamn, argument):
    """Uppstallningens matt. Inga trosklar: det ar korningens val, och
    domarna jamfor mot dem i stallet for att anta dem."""
    if klassnamn == "matare":
        forval = 400.0
    elif klassnamn == "sanka":
        forval = 400.0
    elif klassnamn == "buffert":
        forval = 1000.0
    else:
        forval = 2000.0
    return (float(argument.get("langd", forval)),
            float(argument.get("bredd", 400.0)),
            float(argument.get("hojd", 700.0)))


def bygg(klassnamn, namn, argument=None, utelamna=None):
    """VC-koden som bygger klassens MINSTA UPPSATTNING under `namn`.

    utelamna: nyckeln pa ETT krav som medvetet inte byggs. Det ar den trasiga
    fixturen -- allt annat byggs, sa skillnaden mot den hela uppsattningen ar
    exakt ett krav.
    """
    if klassnamn not in KLASSER:
        raise KeyError("okand klass %r, valj bland %s"
                       % (klassnamn, list(KLASSER)))
    klass = KLASSER[klassnamn]
    argument = dict(argument or {})
    nycklar = ({k.nyckel for k in klass.beteenden}
               | {k.nyckel for k in klass.ramar}
               | {g.nyckel for g in klass.granssnitt})
    if utelamna is not None and utelamna not in nycklar:
        raise ValueError("%r ar inget krav i %s; valj bland %s"
                         % (utelamna, klassnamn, sorted(nycklar)))
    langd, bredd, hojd = _matt(klassnamn, argument)
    rader = _inledning() + _nyko(namn)
    if argument.get("geometri", True):
        rader += _kropp(langd, bredd, hojd)

    # ---- ramarna ----
    ramlagen = {"PathIn": (0.0, 0.0, hojd, 0.0),
                "In": (0.0, 0.0, hojd, 0.0),
                "PathOut": (langd, 0.0, hojd, 180.0),
                "Out": (langd, 0.0, hojd, 180.0)}
    for krav in klass.ramar:
        if krav.nyckel == utelamna:
            rader.append("%s = None" % krav.nyckel)
            continue
        x, y, z, vrid = ramlagen[krav.namn]
        rader.append("%s = _ram(k, %s, %s, %s, %s, %s)"
                     % (krav.nyckel, lit(krav.namn), tal(x), tal(y), tal(z),
                        tal(vrid)))

    # ---- beteendena ----
    for krav in klass.beteenden:
        if krav.nyckel == utelamna:
            rader += [
                "# TRASIG FIXTUR: %s (%s) byggs INTE." % (krav.namn, krav.konstant),
                "%s = None" % krav.nyckel,
            ]
            continue
        rader += [
            "%s = k.createBehaviour(%s, %s)"
            % (krav.nyckel, krav.konstant, lit(krav.namn)),
            "if %s is None:" % krav.nyckel,
            '    raise ValueError("createBehaviour(%s) gav None")' % krav.konstant,
        ]
    rader += _egenskapsrader(klass, klassnamn, argument, utelamna, hojd)

    # ---- granssnitten ----
    rader.append("granssnitt = []")
    for g in klass.granssnitt:
        if g.nyckel == utelamna:
            rader.append("# TRASIG FIXTUR: %s byggs INTE." % g.namn)
            continue
        rader += [
            "kontakt_%s = _kontakt(%s, %s)" % (g.nyckel, g.beteende, g.kontakttyp),
            "def bygg_%s():" % g.nyckel,
            "    return _granssnitt(steg, k, %s, %s, %s, kontakt_%s, %s)"
            % (lit(g.namn), g.ram if g.ram else "None", g.falttyp, g.nyckel,
               g.beteende),
            "ok, r = _steg(steg, %s, bygg_%s)" % (lit("granssnitt." + g.namn),
                                                  g.nyckel),
            "if ok:",
            "    granssnitt.append(r)",
        ]

    rader.append("lage = _placera(k, %s, %s, %s)"
                 % (tal(float(argument.get("x", 0.0))),
                    tal(float(argument.get("y", 0.0))),
                    tal(float(argument.get("z", 0.0)))))
    rader += _svarsrader(klass, klassnamn, namn, utelamna)
    return _mall(["_enkelt", "_svara"], rader, ["vcVector"])


def _satt(steg_namn, obj, egenskap, varde):
    """En egenskapstilldelning som ETT MATT STEG, inte en risk.

    MATT M-101: `behallare.ContentVisible = False` svarade
    "NameError: Attribute or method 'ContentVisible' not found." och tog med
    sig HELA resten av startskriptet -- tretton komponenter och elva
    kopplingar som aldrig byggdes, for en egenskap ingen dom hangde pa.
    En egenskap som inte finns ar ett matvarde. Den far inte vara ett haveri.
    """
    fnamn = "satt_" + steg_namn.replace(".", "_").lower()
    return [
        "def %s():" % fnamn,
        "    %s.%s = %s" % (obj, egenskap, varde),
        "    return %s.%s" % (obj, egenskap),
        "ok, r = _steg(steg, %s, %s)" % (lit("egenskap." + steg_namn), fnamn),
    ]


def _las(steg_namn, rader_i_dict):
    """En aterlasning som ett steg. Vardet i svaret ar VC:s, inte vart."""
    fnamn = "las_" + steg_namn.replace(".", "_").lower()
    return [
        "def %s():" % fnamn,
        "    return {%s}" % ", ".join(rader_i_dict),
        "ok, aterlast = _steg(steg, %s, %s)" % (lit("aterlas." + steg_namn), fnamn),
        "if not ok or aterlast is None:",
        "    aterlast = {}",
    ]


def _egenskapsrader(klass, klassnamn, argument, utelamna, hojd):
    """Egenskaperna specen kraver, per klass, var och en som ett eget steg.

    Varje varde las TILLBAKA: det som star i svaret ar VC:s varde, inte det vi
    skickade. En egenskap som inte gar att satta bokfors i `steg` och stoppar
    ingenting."""
    rader = []
    barare = {"transportor": "bana", "buffert": "bana",
              "matare": "skapare", "sanka": "behallare"}[klassnamn]
    if barare == utelamna or (klassnamn in ("transportor", "buffert")
                              and utelamna == "bana"):
        return ["aterlast = {}", "barens_egenskaper = None"]

    if klassnamn in ("transportor", "buffert"):
        levande = [k.nyckel for k in klass.ramar if k.nyckel != utelamna]
        rader += _satt("Path", "bana", "Path", "[%s]" % ", ".join(levande))
        rader += _satt("Speed", "bana", "Speed",
                       tal(float(argument.get("hastighet", 400.0))))
        if klassnamn == "buffert":
            rader += _satt("Accumulate", "bana", "Accumulate", "True")
            rader += _satt("Capacity", "bana", "Capacity",
                           "%d" % int(argument.get("kapacitet", 10)))
        else:
            rader += _satt("Accumulate", "bana", "Accumulate",
                           "%r" % bool(argument.get("ackumulera", False)))
        # MATT M-40 villkor 2: PathLength ar 0.0 tills BANBETEENDET
        # uppdaterats. komponent.update() och sim.update() racker inte.
        rader += [
            "def uppdatera_banan():",
            "    bana.update()",
            "    return bana.PathLength",
            "ok, r = _steg(steg, %s, uppdatera_banan)" % lit("egenskap.update"),
        ]
        rader += _las("Path", ['%s: bana.PathLength' % lit("path_length"),
                               '%s: bana.Speed' % lit("speed"),
                               '%s: bool(bana.Accumulate)' % lit("accumulate"),
                               '%s: bana.Capacity' % lit("capacity")])
    elif klassnamn == "matare":
        rader += _satt("Enabled", "skapare", "Enabled", "True")
        rader += _satt("Interval", "skapare", "Interval",
                       tal(float(argument.get("intervall", 3.0))))
        # MATT D5/M-40: Limit satts ALLTID. Osatt gav noll produkter pa 6 s.
        rader += _satt("Limit", "skapare", "Limit",
                       "%d" % int(argument.get("grans", 1000000)))
        rader.append("mallnamn = None")
        if "mall" in argument:
            rader += [
                "mall = app.findComponent(%s)" % lit(argument["mall"]),
                "if mall is None:",
                '    raise ValueError("mallkomponenten finns inte i scenen")',
            ]
            rader += _satt("TemplateComponent", "skapare", "TemplateComponent",
                           "mall")
            rader += [
                "if skapare.TemplateComponent is not None:",
                "    mallnamn = skapare.TemplateComponent.Name",
            ]
        rader += _las("Creator", ['%s: skapare.Interval' % lit("interval"),
                                  '%s: skapare.Limit' % lit("limit"),
                                  '%s: bool(skapare.Enabled)' % lit("enabled"),
                                  '%s: mallnamn' % lit("template")])
    elif klassnamn == "sanka":
        rader += _satt("Capacity", "behallare", "Capacity",
                       "%d" % int(argument.get("kapacitet", 1000000)))
        # REFUTERAT (M-101): ContentVisible star i api.xml pa vcContainer men
        # finns inte pa det beteende VC_COMPONENTCONTAINER ger. Steget star
        # kvar SOM MATNING -- faller det inte langre har bindningen andrats,
        # och det vill vi se.
        rader += _satt("ContentVisible", "behallare", "ContentVisible",
                       "%r" % bool(argument.get("synlig", True)))
        rader += _las("Sink", ['%s: behallare.Capacity' % lit("capacity")])
    else:
        raise KeyError(klassnamn)

    # Vilka egenskaper det barande beteendet FAKTISKT har. Det ar beviset bakom
    # varje refuterad rad, och det kostar ett anrop.
    rader += [
        "def las_barens_egenskaper():",
        "    return _egenskaper(%s)" % barare,
        "ok, barens_egenskaper = _steg(steg, %s, las_barens_egenskaper)"
        % lit("aterlas.Properties"),
    ]
    return rader


def _svarsrader(klass, klassnamn, namn, utelamna):
    return [
        '_svara({"built": True, "klass": %s, "component": k.Name,' % lit(klassnamn),
        '        "utelamnat": %s,' % lit(utelamna) if utelamna else
        '        "utelamnat": None,',
        '        "aterlast": aterlast, "behaviour_properties": barens_egenskaper,',
        '        "position": lage, "features": _ramnamn(k),',
        '        "behaviours": _beteenden(k), "interfaces": granssnitt,',
        '        "steg": steg})',
    ]


# ---- kopplingen ------------------------------------------------------------

def koppla(a, b, granssnitt_a="OutInterface", granssnitt_b="InInterface",
           etikett=None, vantas_ga=True):
    """Provar EN koppling: ut-granssnittet i a mot in-granssnittet i b.

    Svaret bar canConnect, connect, IsConnected och bada granssnittens
    faltbindningar, sa att domaren kan saga VARFOR nar svaret ar False.
    VC sjalvt sager ingenting (MATT M-40/E0).
    """
    rader = _inledning() + [
        "app = getApplication()",
        "steg = []",
        "ka = app.findComponent(%s)" % lit(a),
        "kb = app.findComponent(%s)" % lit(b),
        "if ka is None or kb is None:",
        '    raise ValueError("komponenten saknas i scenen")',
        "ga = ka.findBehaviour(%s)" % lit(granssnitt_a),
        "gb = kb.findBehaviour(%s)" % lit(granssnitt_b),
        "kan = None",
        "kopplad = None",
        "if ga is not None and gb is not None:",
        "    def fraga():",
        "        return bool(ga.canConnect(gb))",
        "    ok, kan = _steg(steg, %s, fraga)" % lit("canConnect"),
        "    if kan:",
        "        def utfor():",
        "            return bool(ga.connect(gb))",
        "        ok2, kopplad = _steg(steg, %s, utfor)" % lit("connect"),
        # Las tillbaka BADA sidornas faltbindning och kontakttyp. Utan det
        # ar ett False bara ett False; med det kan varfor_inte() peka ut
        # vilken regel i matchningsregeln som brast -- pa verklig data.
        "post_a = _kontakttyp_i(ga, ka)",
        "post_b = _kontakttyp_i(gb, kb)",
        '_svara({"koppling": %s, "a": %s, "b": %s,'
        % (lit(etikett or (a + "->" + b)), lit(a), lit(b)),
        '        "granssnitt_a": %s, "granssnitt_b": %s,'
        % (lit(granssnitt_a), lit(granssnitt_b)),
        '        "vantas_ga": %r,' % bool(vantas_ga),
        '        "granssnitt_a_fanns": ga is not None,',
        '        "granssnitt_b_fanns": gb is not None,',
        '        "canConnect": kan, "connect": kopplad,',
        '        "post_a": post_a, "post_b": post_b,',
        '        "a_is_connected": bool(ga.IsConnected) if ga is not None else None,',
        '        "b_is_connected": bool(gb.IsConnected) if gb is not None else None,',
        '        "steg": steg})',
    ]
    return _mall(["_enkelt", "_svara"], rader, ["vcVector"])


# ---- specens tabeller ------------------------------------------------------

def spec_rader(klassnamn):
    """Kravlistan som markdown-rader. Specens tabell ar SAMMA data, och
    test_komponentmodell.py faller om en rad saknas dar."""
    klass = KLASSER[klassnamn]
    ut = []
    for krav in klass.beteenden + klass.ramar:
        ut.append("| `%s` | %s | `%s` | %s | %s |"
                  % (krav.namn, krav.slag, krav.konstant, krav.harkomst,
                     krav.utan))
    for g in klass.granssnitt:
        ut.append("| `%s` | granssnitt | `VC_ONETOONEINTERFACE` | %s | %s |"
                  % (g.namn, g.harkomst, g.utan))
    for krav in klass.egenskaper:
        ut.append("| `%s` | egenskap | -- | %s | %s |"
                  % (krav.namn, krav.harkomst, krav.utan))
    return ut


EXEMPEL = {
    "transportor": [{"name": "Bana1"},
                    {"name": "Bana2", "langd": 3000.0, "hastighet": 250.0,
                     "x": 1000.0, "y": -2000.0, "geometri": False}],
    "matare": [{"name": "Matare1"},
               {"name": "Matare2", "mall": "Produkt", "intervall": 2.5,
                "grans": 100}],
    "sanka": [{"name": "Sanka1"}, {"name": "Sanka2", "kapacitet": 50,
                                   "synlig": False}],
    "buffert": [{"name": "Buffert1"}, {"name": "Buffert2", "kapacitet": 5}],
}
