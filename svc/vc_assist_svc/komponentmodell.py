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
    "utan det finns ingen vcConnector att binda flodesfaltets %s till, "
    "%s star kvar pa None, och canConnect blir False utan att VC sager "
    "nagot (MATT M-40, E6)" % (EGENSKAP_PORT, EGENSKAP_BETEENDE))

_UTAN_GRANSSNITT = (
    "utan det finns inget att anropa canConnect PA: findBehaviour ger None "
    "och kopplingen kan inte ens efterfragas (MATT M-40, koppla-receptet "
    "foll pa exakt det)")

_BANA = Krav(
    nyckel="bana", slag="beteende", namn="Path", konstant="VC_ONEWAYPATH",
    roll="flodesbarare: bar bade vcFlow och vcContainer, alltsa kontakter OCH lagring",
    harkomst="BELAGT api.xml vcMotionPath <parents>vcBehaviour vcFlow vcContainer</parents>; MATT C0/C3",
    utan="beteendet Path (VC_ONEWAYPATH) saknas: " + _UTAN_FLODESBETEENDE)

_SKAPARE = Krav(
    nyckel="skapare", slag="beteende", namn="Creator",
    konstant="VC_COMPONENTCREATOR",
    roll="producerar komponenter ur en mall och lamnar dem genom sin utkontakt",
    harkomst="MATT D1/D5 (2026-09-04); klassnamnet rapporteras som rResourceCreator",
    utan="beteendet Creator (VC_COMPONENTCREATOR) saknas: "
         "ingenting produceras, och " + _UTAN_FLODESBETEENDE)

_BEHALLARE = Krav(
    nyckel="behallare", slag="beteende", namn="Sink",
    konstant="VC_COMPONENTCONTAINER",
    roll="lagrar mottagna komponenter; vcSimContainer med Input och Output",
    harkomst="MATT D0/D2 (2026-09-04): VC_CONTAINER ger None, VC_COMPONENTCONTAINER ger vcSimContainer",
    utan="beteendet Sink (VC_COMPONENTCONTAINER) saknas: "
         "det finns ingenstans att ta emot, och " + _UTAN_FLODESBETEENDE)


def _granssnittskrav(nyckel, namn, riktning, ram, beteende, kontakttyp):
    return Granssnitt(
        nyckel=nyckel, namn=namn, riktning=riktning, ram=ram,
        beteende=beteende, kontakttyp=kontakttyp, falttyp="VC_FLOWFIELD",
        harkomst="MATT punkt 1-3 (interface, section, field skapas); "
                 "BELAGT Create3D BehaviorType.OneToOneInterface",
        utan="granssnittet %s (VC_ONETOONEINTERFACE) saknas: %s"
             % (namn, _UTAN_GRANSSNITT))


def _ramkrav(nyckel, namn, roll):
    return Krav(
        nyckel=nyckel, slag="ram", namn=namn, konstant="VC_FRAME", roll=roll,
        harkomst="MATT M-40 villkor 1: utan rebuild() star ramens verkliga "
                 "lage kvar i nodens ursprung och PathLength blir 0.0",
        utan="ramen %s (VC_FRAME) saknas: sektionen far ingen Frame, och en "
             "bana utan tva atskilda ramar far PathLength 0.0 -- den tar inte "
             "emot nagot och matningen uppstrom tystnar (MATT M-40, linje M41B)"
             % namn)


_TRANSPORTOR = Klass(
    namn="transportor",
    rubrik="TRANSPORTOR: tar emot i ena anden, lamnar i den andra",
    beteenden=(_BANA,),
    ramar=(_ramkrav("ram_in", "PathIn", "banans borjan och in-sektionens lage"),
           _ramkrav("ram_ut", "PathOut", "banans slut och ut-sektionens lage")),
    granssnitt=(
        _granssnittskrav("in_granssnitt", "InInterface", "in", "ram_in",
                         "bana", "VC_CONNECTOR_INPUT"),
        _granssnittskrav("ut_granssnitt", "OutInterface", "ut", "ram_ut",
                         "bana", "VC_CONNECTOR_OUTPUT"),
    ),
    egenskaper=(
        Krav("path", "egenskap", "Path", "", "banans vag: [PathIn, PathOut]",
             "MATT: Path = [ram_in, ram_ut] tas emot",
             "egenskapen Path ar tom: PathLength blir 0.0 och banan bar inget"),
        Krav("uppdaterad", "egenskap", "update()", "",
             "raknar om PathLength efter att Path satts",
             "MATT M-40 villkor 2: p.Path satt -> PathLength 0.0; p.update() -> 3000.0",
             "bana.update() utelamnad: PathLength ar 0.0 fast ramarna star "
             "3000 mm isar, banan tar inte emot nagot och mataren uppstrom "
             "producerar noll (MATT M-40, linje M41B: 0 produkter pa 7 intervall)"),
        Krav("hastighet", "egenskap", "Speed", "", "mm/s langs banan",
             "MATT M-41: uppmatt rorelse 250.0000 mm/s mot Speed 250.0, spridning 0.0000",
             "Speed osatt: forvalet galler; ingen mätning sager vilket det ar"),
    ),
    parbarhet=("in: matare, transportor, buffert", "ut: transportor, buffert, sanka"),
)

_BUFFERT = Klass(
    namn="buffert",
    rubrik="BUFFERT: en bana som HALLER KVAR N komponenter",
    beteenden=(_BANA,),
    ramar=_TRANSPORTOR.ramar,
    granssnitt=_TRANSPORTOR.granssnitt,
    egenskaper=_TRANSPORTOR.egenskaper + (
        Krav("ackumulera", "egenskap", "Accumulate", "",
             "later komponenter ko sig i stallet for att bara passera",
             "HYPOTES D4: aldrig matt med Accumulate=False mot True pa samma bana",
             "Accumulate=False: komponenterna passerar utan att ko sig; "
             "buffert och transportor blir samma sak"),
        Krav("kapacitet", "egenskap", "Capacity", "", "antal platser",
             "HYPOTES D4: kapacitetens verkan aldrig matt",
             "Capacity osatt: forvalet galler, och hur manga platser en bana "
             "har som forval ar inte matt"),
    ),
    parbarhet=("in: matare, transportor, buffert", "ut: transportor, buffert, sanka"),
)

_MATARE = Klass(
    namn="matare",
    rubrik="MATARE: skapar komponenter och lamnar dem nedstroms",
    beteenden=(_SKAPARE,),
    ramar=(_ramkrav("ram_ut", "Out", "utgangens lage"),),
    granssnitt=(
        _granssnittskrav("ut_granssnitt", "OutInterface", "ut", "ram_ut",
                         "skapare", "VC_CONNECTOR_OUTPUT"),
    ),
    egenskaper=(
        Krav("mall", "egenskap", "TemplateComponent", "",
             "komponenten som kopieras vid varje intervall",
             "MATT M-40: tar en komponent som STAR i scenen, aven en utan URI "
             "och utan VCID; Part maste inte peka pa en losbar URI",
             "TemplateComponent osatt: skaparen har ingenting att kopiera"),
        Krav("intervall", "egenskap", "Interval", "", "sekunder mellan produkter",
             "MATT M-41: atta mellanrum, alla exakt 4.000 s mot Interval 4.0",
             "Interval osatt: forvalet galler och takten ar inte matt"),
        Krav("grans", "egenskap", "Limit", "", "hogsta antal produkter",
             "MATT M-40/D5: Limit osatt -> noll produkter pa 6 s; Limit=10 "
             "slutade tyst vid t=50 och sag ut som en trasig matare",
             "Limit osatt: mataren stannar tyst nar forvalet nas, och en "
             "stannad matare ser exakt ut som en trasig"),
        Krav("pa", "egenskap", "Enabled", "", "skaparen ar igang",
             "MATT M-40: Enabled rapporterades True i alla tre linjerna",
             "Enabled=False: ingenting produceras"),
    ),
    parbarhet=("in: -- (en matare tar inte emot)", "ut: transportor, buffert, sanka"),
)

_SANKA = Klass(
    namn="sanka",
    rubrik="SANKA: tar emot komponenter och behaller dem",
    beteenden=(_BEHALLARE,),
    ramar=(_ramkrav("ram_in", "In", "ingangens lage"),),
    granssnitt=(
        _granssnittskrav("in_granssnitt", "InInterface", "in", "ram_in",
                         "behallare", "VC_CONNECTOR_INPUT"),
    ),
    egenskaper=(
        Krav("kapacitet", "egenskap", "Capacity", "", "hur manga som far plats",
             "BELAGT api.xml vcContainer.Capacity: \"the maximum number of "
             "components that can be stored in the container at any given time\"",
             "Capacity for lag: sankan blir full och stoppar linjen uppstrom"),
        Krav("dolt", "egenskap", "ContentVisible", "",
             "gommer det lagrade i 3D-vyn",
             "BELAGT api.xml vcContainer.ContentVisible (W)",
             "ContentVisible=True: innehallet syns; kosmetiskt, inte funktionellt"),
    ),
    parbarhet=("in: matare, transportor, buffert", "ut: -- (en sanka lamnar inte ifran sig)"),
)

KLASSER = collections.OrderedDict((
    ("transportor", _TRANSPORTOR),
    ("matare", _MATARE),
    ("sanka", _SANKA),
    ("buffert", _BUFFERT),
))

# Vilket krav den trasiga fixturen utelamnar per klass. Alltid det som barer
# flodet: da finns granssnittet kvar, canConnect GAR att anropa, och False
# betyder nagot. Utelamnas granssnittet i stallet gar fragan inte att stalla,
# och "gick inte" hade blivit tvetydigt.
TRASIG_UTELAMNING = collections.OrderedDict((
    ("transportor", "bana"),
    ("matare", "skapare"),
    ("sanka", "behallare"),
    ("buffert", "bana"),
))

# Vilka par specen sager ska ga ihop: (ut-sida, in-sida).
PAR_SOM_SKA_GA = (
    ("matare", "transportor"),
    ("transportor", "buffert"),
    ("buffert", "sanka"),
    ("transportor", "transportor"),
    ("matare", "sanka"),
)

# Par som INTE ska ga ihop, och skalet.
PAR_SOM_INTE_GAR = (
    ("matare", "matare", "bada sidor bar VC_CONNECTOR_OUTPUT; "
                         "MATT M-67: ut mot ut ger canConnect False"),
    ("sanka", "sanka", "bada sidor bar VC_CONNECTOR_INPUT"),
    ("sanka", "matare", "sankan har ingen utgang och mataren ingen ingang"),
)


# ---- matchningsregeln for canConnect ---------------------------------------
#
# Ordningen ar VAR provordning, inte VC:s. VC:s inre ordning ar INTE matt --
# canConnect ger ett enda False utan att saga vilket villkor som brast. Att
# skriva ordningen som om den vore VC:s hade varit ett antagande i
# matningsklader.

MATCHNINGSREGEL = (
    Regel("R1", "bada sidor har ett beteende med granssnittets namn, och det "
                "beteendet ar ett simuleringsgranssnitt (bar canConnect)",
          "MATT M-40: koppla-receptet foll pa findBehaviour som gav None",
          "granssnittet saknas -- fragan gar inte att stalla, och 'gick inte' "
          "vore tvetydigt"),
    Regel("R2", "flodesfaltets %s pekar pa ett beteende (inte None)" % EGENSKAP_BETEENDE,
          "MATT E0/E6 2026-09-04: med Port bundet och Container=None pa bada "
          "sidor ar canConnect False och connectComponents False",
          "canConnect returnerar False. VC sager INGENTING -- ingen exception, "
          "ingen logg, inget falskt returvarde nagon annanstans"),
    Regel("R3", "flodesfaltets %s ar ett heltal >= 0" % EGENSKAP_PORT,
          "MATT M-40: Port = -1 ger canConnect False; MATT B3: Port tar ett "
          "heltal (kontaktens Index), inte ett vcConnector-objekt",
          "canConnect returnerar False, tyst. Ett falt med Port = -1 ser i "
          "ovrigt fardigbundet ut"),
    Regel("R4", "bindningsordningen ar %s FORE %s"
                % (EGENSKAP_BETEENDE, EGENSKAP_PORT),
          "MATT M-40: Port satt forst -> Container satt -> Port ar nu -1",
          "Port nollstalls till -1 av Container-tilldelningen. Kopplingen "
          "faller pa R3 av ett skal som inte finns i koden dar felet ser ut "
          "att vara"),
    Regel("R5", "ut-sidans kontakt ar VC_CONNECTOR_OUTPUT och in-sidans "
                "VC_CONNECTOR_INPUT",
          "MATT M-67: ut mot ut ger canConnect False, connect False, "
          "IsConnected False -- och flyttar ingenting",
          "canConnect returnerar False. Riktningen bor i kontakten, inte i "
          "granssnittets namn: ett granssnitt som HETER OutInterface men bar "
          "en Input-kontakt matchar som ingang"),
    Regel("R6", "bada sektionernas falt har samma typ (VC_FLOWFIELD mot "
                "VC_FLOWFIELD)",
          "BELAGT Create3D ISimInterfaceSection.IsCompatibleWith: \"True if "
          "connection between these sections is possible\"",
          "canConnect returnerar False. Aldrig matt med BLANDADE falttyper -- "
          "regeln ar belagd, inte matt"),
    Regel("R7", "falten star i samma ORDNING i bada sektionerna",
          "BELAGT api.xml vcSimInterfaceField.Index: \"sections may have "
          "compatible fields but cannot connect because the order of fields "
          "differ in each section\"",
          "canConnect returnerar False. Aldrig matt hos oss: alla vara "
          "sektioner har exakt ett falt, sa ordningen kan inte skilja"),
    Regel("R8", "ett VC_ONETOONEINTERFACE ar inte redan kopplat",
          "BELAGT Create3D ISimInterface.Connect: \"Thrown when interface "
          "cannot be connected (it is one to one interface and already "
          "connected ...)\"",
          "connect kastar i .NET. I Python-bindningen ar utfallet inte matt -- "
          "vi vet inte om det blir False eller ett undantag"),
    Regel("R9", "avstandet mellan granssnitten spelar INGEN roll vid forvald "
                "DistanceTolerance",
          "MATT M-67: canConnect True med 1670 mm mellan komponenterna; "
          "MATT punkt 9: forvalet ar 1e9 mm och 360 grader",
          "-- ingen regel att brista mot. Raden star har for att M-40:s "
          "formulering \"canConnect ar en geometrisk fraga\" ar SKARPT av "
          "M-67: det var ett falt med Port = -1, inte avstandet"),
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


def _egenskapsrader(klass, klassnamn, argument, utelamna, hojd):
    """Egenskaperna som specen kraver, per klass. Varje varde las TILLBAKA i
    svaret: det som star dar ar VC:s varde, inte det vi skickade."""
    rader = []
    if klassnamn in ("transportor", "buffert"):
        if utelamna == "bana":
            rader += ["path_length = None", "speed = None",
                      "accumulate = None", "capacity = None"]
            return rader
        ramar = [k.nyckel for k in klass.ramar]
        levande = [n for n in ramar if n != utelamna]
        rader += ["bana.Path = [%s]" % ", ".join(levande),
                  "bana.Speed = %s" % tal(float(argument.get("hastighet", 400.0)))]
        if klassnamn == "buffert":
            rader += ["bana.Accumulate = True",
                      "bana.Capacity = %d" % int(argument.get("kapacitet", 10))]
        else:
            rader.append("bana.Accumulate = %r"
                         % bool(argument.get("ackumulera", False)))
        rader += [
            # MATT M-40 villkor 2: PathLength ar 0.0 tills BANBETEENDET
            # uppdaterats. komponent.update() och sim.update() racker inte.
            "bana.update()",
            "path_length = bana.PathLength",
            "speed = bana.Speed",
            "accumulate = bool(bana.Accumulate)",
            "capacity = bana.Capacity",
        ]
        return rader
    if klassnamn == "matare":
        if utelamna == "skapare":
            rader += ["interval = None", "limit = None", "mallnamn = None",
                      "enabled = None"]
            return rader
        rader += [
            "skapare.Enabled = True",
            "skapare.Interval = %s" % tal(float(argument.get("intervall", 3.0))),
            # MATT D5: Limit satts ALLTID. Osatt gav noll produkter pa 6 s.
            "skapare.Limit = %d" % int(argument.get("grans", 1000000)),
            "mallnamn = None",
        ]
        if "mall" in argument:
            rader += [
                "mall = app.findComponent(%s)" % lit(argument["mall"]),
                "if mall is None:",
                '    raise ValueError("mallkomponenten finns inte i scenen")',
                "skapare.TemplateComponent = mall",
                "if skapare.TemplateComponent is not None:",
                "    mallnamn = skapare.TemplateComponent.Name",
            ]
        rader += ["interval = skapare.Interval", "limit = skapare.Limit",
                  "enabled = bool(skapare.Enabled)"]
        return rader
    if klassnamn == "sanka":
        if utelamna == "behallare":
            rader += ["capacity = None", "content_visible = None"]
            return rader
        rader += [
            "behallare.Capacity = %d" % int(argument.get("kapacitet", 1000000)),
            "behallare.ContentVisible = %r" % bool(argument.get("synlig", True)),
            "capacity = behallare.Capacity",
            "content_visible = bool(behallare.ContentVisible)",
        ]
        return rader
    raise KeyError(klassnamn)


def _svarsrader(klass, klassnamn, namn, utelamna):
    extra = {
        "transportor": '"path_length": path_length, "speed": speed, '
                       '"accumulate": accumulate, "capacity": capacity,',
        "buffert": '"path_length": path_length, "speed": speed, '
                   '"accumulate": accumulate, "capacity": capacity,',
        "matare": '"interval": interval, "limit": limit, '
                  '"template": mallnamn, "enabled": enabled,',
        "sanka": '"capacity": capacity, "content_visible": content_visible,',
    }[klassnamn]
    return [
        '_svara({"built": True, "klass": %s, "component": k.Name,' % lit(klassnamn),
        '        "utelamnat": %s,' % lit(utelamna) if utelamna else
        '        "utelamnat": None,',
        '        %s' % extra,
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
        '_svara({"koppling": %s, "a": %s, "b": %s,'
        % (lit(etikett or (a + "->" + b)), lit(a), lit(b)),
        '        "granssnitt_a": %s, "granssnitt_b": %s,'
        % (lit(granssnitt_a), lit(granssnitt_b)),
        '        "vantas_ga": %r,' % bool(vantas_ga),
        '        "granssnitt_a_fanns": ga is not None,',
        '        "granssnitt_b_fanns": gb is not None,',
        '        "canConnect": kan, "connect": kopplad,',
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
