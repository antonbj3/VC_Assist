# -*- coding: utf-8 -*-
"""TOLKEN: vad operatorens mening om en BEFINTLIG scen vill.

Byggd EFTER sparr.py, och det ar hela poangen. Modulen har ingen ordlista och
laser inga nyckelord. Den tar emot ett PASTAENDE - vad modellen sager att
meningen betyder - och lamnar en DOM over om pastaendet gar att belagga.

    modellen tolkar.  grinden bevisar.  operatoren beslutar.

VARFOR TOLKNINGEN INTE LIGGER HAR

plan/forfining.py laser fri text med ORDBOK: 32 hardkodade svenska ord.
Konstruktionen har en akta fortjanst - en ordlista kan inte hitta pa, sa
saknas ordet blir det en fraga och aldrig en gissning. Priset ar att vagen in
ar svensk. "a conveyor" ger noll delar.

Det gar inte att laga med fler ord. Garantin far i stallet ligga i grinden,
och da kan tolken vara en sprakmodell: den laser meningen pa vilket sprak den
kan, och varje utsaga den gor provas mot nagot som redan finns. Modulen bar
darfor INGET sprak alls - bara fragan "star de har orden i det operatoren
skrev, och finns den har komponenten i det nagon last".

FYRA DOMAR, OCH INGEN AV DEM HETER "GOR DET"

Formen ar arvd ordagrant ur plan/motsagelse.py, och arvet ar avsiktligt: en
scen som tyst andras fel ar varre an ett nej.

    DIAGNOS      meningen fragar om nagot. Ingen andring, och lassparren
                 satts pa i sparr.urval_for_avsikt.
    ANDRING      meningen ger en bestamd operation mot ett entydigt mal.
    OPTIMERING   meningen vill andra, mata om och jamfora. INTE BYGGD - och
                 den domes darfor OKANT med det skalet utskrivet, i stallet
                 for att bli en halv andring.
    FRAGA        meningen ar tvetydig. Malet har flera kandidater i den lasta
                 scenen, och det finns inget ratt svar att valja. Fragan gar
                 tillbaka MED kandidaterna; en fraga utan dem ar inte svarbar.
    OKANT        pastaendet gar inte att belagga. OKANT ar aldrig ett
                 godkannande (I3), och sparr.far_utforas() sager nej.

BUDGETEN AR EN SUMMA, INTE EN TABELL

"Compute i proportion till komplexiteten" blir annars tva pahittade tal
("enkel = 2 turer, komplex = 8"). Har raknas budgeten i stallet ur de anrop
turen MASTE gora, och varje steg bar den regel som kraver det: I9 kraver att
scenen lases innan nagot valjs ur den, I1 att domen kommer ur ogat,
turordning.olast_skrivning att en andring lases tillbaka. Talet foljer alltsa
av grindar som redan ar matta. Se nodvandiga_steg().

Endast standardbiblioteket plus tjanstens egna lager.
"""
from __future__ import annotations

from ..plan.harkomst import normalisera
from . import sparr

DIAGNOS = "DIAGNOS"
ANDRING = "ANDRING"
OPTIMERING = "OPTIMERING"
FRAGA = "FRAGA"
OKANT = "OKANT"

# Vad en modell far pasta att en mening betyder. Sluten lista: ett pastaende
# utanfor den ar inte en ny avsikt, det ar en modell som hittat pa en.
PASTAENDEN = (DIAGNOS, ANDRING, OPTIMERING)
DOMAR = (DIAGNOS, ANDRING, FRAGA, OKANT)

# Avsikter som ar BYGGDA. OPTIMERING ar inte det, och den star darfor inte
# har. Att lata den falla igenom som en ANDRING hade gett en halv optimering:
# scenen andrad, ingenting mattt om, ingenting jamfort. En oppen fas ar
# arlig; en stangd fas med en stub ar en logn (96_ingen_skuld.md).
BYGGDA = (DIAGNOS, ANDRING)

SKAL_OPTIMERING = (
    "avsikten ar OPTIMERING: andra, mata om och jamfora. Slingan ar inte "
    "byggd for en befintlig scen, och en optimering som utfors utan "
    "ommatningen ar en andring utan facit. Dela upp meningen: fraga forst "
    "varfor det gar langsamt (DIAGNOS), begar sedan den andring du vill ha "
    "(ANDRING)")


class Avsiktspastaende(object):
    """Vad MODELLEN sager att meningen betyder. Inget ar bevisat har.

    belagg och malbelagg ar ORDAGRANNA bitar ur operatorens mening. Det ar de
    tva falten grinden kan prova; en modell som skriver om operatorens ord i
    stallet for att citera dem faller pa dem.
    """

    __slots__ = ("avsikt", "belagg", "mal", "malbelagg")

    def __init__(self, avsikt, belagg, mal="", malbelagg=""):
        self.avsikt = avsikt
        self.belagg = belagg
        self.mal = mal
        self.malbelagg = malbelagg

    def __repr__(self):
        return "Avsiktspastaende(%s, mal=%r)" % (self.avsikt, self.mal)


class Avsiktsdom(object):
    """Utfallet, med sitt skal och sina kandidater."""

    __slots__ = ("dom", "pastaende", "skal", "kandidater", "brott")

    def __init__(self, dom, pastaende, skal=(), kandidater=(), brott=()):
        self.dom = dom
        self.pastaende = pastaende
        self.skal = tuple(skal)
        self.kandidater = tuple(kandidater)
        self.brott = tuple(brott)

    def __repr__(self):
        return "Avsiktsdom(%s)" % (self.dom,)

    @property
    def mal(self):
        return self.pastaende.mal if self.pastaende is not None else ""

    def text(self):
        rader = ["AVSIKT: %s" % self.dom]
        for s in self.skal:
            rader.append("    " + s)
        if self.kandidater:
            rader.append("    kandidater i scenen: %s"
                         % ", ".join(self.kandidater))
        for kod, text in self.brott:
            rader.append("    %s: %s" % (kod, text))
        return "\n".join(rader)


def granska(pastaende, begaran_text, scenlage):
    """Provar ett avsiktspastaende. Lamnar en dom, kastar aldrig (S10).

    Ordningen ar 82_felklasser.md sorteringsregel 1: forsta grinden som
    faller bestammer klassen. Den hardaste fragan stalls forst, sa att ett
    uppfunnet komponentnamn aldrig kan dolja sig bakom en tvetydighet.
    """
    if not isinstance(pastaende, Avsiktspastaende):
        return Avsiktsdom(OKANT, None, [
            "det som skulle granskas ar %s, inte ett avsiktspastaende"
            % type(pastaende).__name__])

    if pastaende.avsikt not in PASTAENDEN:
        return Avsiktsdom(OKANT, pastaende, [
            "avsikten %r finns inte; de tre ar %s. En modell som hittar pa en "
            "avsikt har slutat lasa meningen"
            % (pastaende.avsikt, ", ".join(PASTAENDEN))])

    # AV1. Citatet ska sta i operatorens mening. Det ar den enda kontrollen
    # som skiljer "han bad om det" fran "vi tyckte det", och den bar inget
    # sprak: den fragar bara om orden star dar.
    brott = sparr.granska_falt(
        (sparr.Falt("avsikten", pastaende.avsikt,
                    sparr.ur_begaran(pastaende.belagg)),),
        begaran_text, None)
    if brott:
        return Avsiktsdom(OKANT, pastaende, [
            "avsikten gar inte att belagga i din mening"], brott=brott)

    if pastaende.avsikt not in BYGGDA:
        return Avsiktsdom(OKANT, pastaende, [SKAL_OPTIMERING])

    # AV2. Ett mal som inte namns alls ar inte ett mal. En DIAGNOS utan mal
    # ar en fraga om hela scenen och tillats; en ANDRING utan mal ar en order
    # utan foremal.
    if not (pastaende.mal or "").strip():
        if pastaende.avsikt == ANDRING:
            return Avsiktsdom(OKANT, pastaende, [
                "meningen begar en andring men namner ingenting att andra"])
        return Avsiktsdom(DIAGNOS, pastaende)

    # AV3. Malet SLAS UPP i den lasta scenen. Ordningen mellan tvetydighet
    # och existens ar inte godtycklig, och det forsta bygget hade den fel:
    # existensen provades forst, och "byt det dar gripdonet" domdes da OKANT
    # ("gripdon finns inte") i stallet for FRAGA ("scenen har tre"). Det ar
    # fel besked till operatoren - han hade namnt nagot som finns tre ganger,
    # inte nagot som inte finns. Uppslagningen kommer darfor forst, och
    # antalet traffar avgor domen:
    #
    #   0 traffar   OKANT. Ett uppfunnet komponentnamn (I9, hart fel).
    #   >1 traffar  FRAGA, med kandidaterna. Det finns inget ratt val.
    #   1 traff     malet ar avgjort.
    # TVA TOMMA TRAFFISTOR SOM BETYDER OLIKA SAKER, och att blanda ihop dem
    # var en matt felmod: scenen kan bara innehalla `ST210_GRP` med kategorin
    # `Grippers`, och ordet "gripdon" traffar da ingetdera. Den forsta
    # versionen svarade "gripdon finns inte i scenen" om en scen som HADE ett.
    # Delstrangen ar sprakbunden; den ar ett forfilter, aldrig domaren.
    ord_ = (pastaende.malbelagg or pastaende.mal)
    lage, kandidater = scenlage.slaupp(ord_)
    if not kandidater and pastaende.mal:
        lage2, kandidater2 = scenlage.slaupp(pastaende.mal)
        if kandidater2:
            lage, kandidater = lage2, kandidater2
    if not kandidater:
        # I9 FORST, och skild fran uppslagningen. Modellen far namnge det som
        # FINNS i scenen eller det OPERATOREN sa - aldrig nagot den satt ihop
        # sjalv. `ST999_gripdon` ar varken: operatoren sa "ST999", scenen bar
        # det inte, och modellen la till "_gripdon". Ett hopsatt namn ar ett
        # tyst val, och det ar hart fel oavsett vad delstrangen tyckte.
        if pastaende.mal:
            m = normalisera(pastaende.mal)
            i_scenen = any(m == normalisera(n) for n in scenlage.namn())
            i_meningen = m in normalisera(begaran_text or "")
            if not i_scenen and not i_meningen:
                return Avsiktsdom(OKANT, pastaende, [
                    "modellen namngav %r. Det namnet star varken i scenen "
                    "(%s) eller i din mening - det ar hopsatt. Modellen far "
                    "bara valja ur det som finns (I9). Scenen innehaller: %s"
                    % (pastaende.mal, scenlage.kalla or "ingen lasning",
                       ", ".join(scenlage.namn()) or "ingenting")])
        if lage == scenlage.OLAST:
            return Avsiktsdom(OKANT, pastaende, [
                "scenen ar inte last, sa vad %r syftar pa gar inte att "
                "avgora. Modellen far bara valja ur det som finns (I9), och "
                "har finns ingen lasning att valja ur" % (pastaende.mal,)])
        # TOLKAS: scenen ar last och ordet traffade ingen komponent. Det ar
        # INTE ett besked om att komponenten saknas - matchningen ar en
        # delstrang och klarar inte ett sprakbyte. Hela listan gar tillbaka
        # som kandidater, sa att ordet kan tolkas mot den i stallet.
        alla = scenlage.namn()
        return Avsiktsdom(FRAGA, pastaende, [
            "ordet %r matchar inget komponentnamn och ingen kategori i "
            "scenen. Det betyder INTE att komponenten saknas - jamforelsen ar "
            "en delstrang, och den klarar inte att du sager %r om nagot som "
            "heter nagot annat. Scenen (%s) innehaller: %s"
            % (ord_, ord_, scenlage.kalla,
               ", ".join("%s [%s]" % (n, t or "okand sort")
                         for n, t in scenlage.komponenter))
            + ("" if scenlage.fullstandig()
               else ". LASNINGEN AR AVKORTAD - det kan finnas fler")],
            kandidater=alla)
    if len(kandidater) > 1:
        return Avsiktsdom(FRAGA, pastaende, [
            "%r kan syfta pa %d komponenter i scenen. Vilken menar du?"
            % (ord_, len(kandidater))], kandidater=kandidater)

    # En traff, men modellen namngav nagot annat. Da har den valt sjalv, och
    # ett tyst val ar precis vad grinden finns for.
    if pastaende.mal and pastaende.mal not in kandidater:
        return Avsiktsdom(OKANT, pastaende, [
            "modellen namngav %r men orden i din mening (%r) pekar pa %s. "
            "Ett mal som inte foljer av dina ord ar ett tyst val"
            % (pastaende.mal, ord_, kandidater[0])])

    return Avsiktsdom(pastaende.avsikt, pastaende, kandidater=kandidater)


# ---- budgeten ------------------------------------------------------------

class Steg(object):
    """Ett anrop turen MASTE gora, och regeln som kraver det."""

    __slots__ = ("vad", "regel")

    def __init__(self, vad, regel):
        self.vad = vad
        self.regel = regel

    def __repr__(self):
        return "Steg(%s <- %s)" % (self.vad, self.regel)


# Rundan som barar SLUTSVARET. Den ar inte ett anrop och kan darfor inte
# raknas som ett steg, men den kostar en runda: loop.py laser ett svar utan
# anrop som turens slutsvar, alltsa i en egen runda. Talet foljer av loopens
# form och ar inte valt.
RUNDA_FOR_SLUTSVARET = 1    # 24_samtalsloopen.md; loop.py: ett svar utan anrop
                            # ar turens slutsvar och kostar en egen runda.


def nodvandiga_steg(dom):
    """De anrop avsikten inte gar att utfora utan, med sina regler.

    Det ar HAR "compute i proportion till komplexiteten" faktiskt bestams.
    Listan ar inte en uppskattning av hur svar uppgiften kanns - den ar de
    steg grindarna redan kraver, och varje rad bar sin regel.
    """
    if dom.dom == DIAGNOS:
        steg = [Steg("lasa scenen", "I9: modellen far bara valja ur det som "
                                    "finns, och det enda sattet att veta vad "
                                    "som finns ar att lasa")]
        if dom.mal:
            steg.append(Steg("lasa malets egna matt",
                             "I9: en utsaga om %s maste komma ur en lasning "
                             "av %s" % (dom.mal, dom.mal)))
        steg.append(Steg("lasa ogats rapport",
                         "I1: ogat faller domen. Ett matt som raknas om har "
                         "ar ett andra matt"))
        return tuple(steg)
    if dom.dom == ANDRING:
        return (
            Steg("lasa scenen",
                 "turordning.olast_scen (ARB-001): ett scenandrande anrop som "
                 "namnger nagot ingen lasning returnerat ar en gissning"),
            Steg("lasa malets granssnitt",
                 "turordning.olast_scen (ARB-001): det som ska kopplas maste "
                 "vara last"),
            Steg("utfora andringen",
                 "I12: skrivningen gar genom godkannandekon"),
            Steg("lasa tillbaka utfallet",
                 "turordning.olast_skrivning (ARB-003, FAL-005, MATT M-09): "
                 "VC svaljer fel tyst, sa en skrivning som inte tog syns bara "
                 "vid aterlasning"),
        )
    # FRAGA och OKANT kostar ingenting: ingenting ska utforas.
    return ()


# BUDGETENS STATUS. Formen ar lanad ur operatorens eget forarbete i
# sibling-project dar varje
# budgettak bar antingen UPPNADD med en NAMNGIVEN bevis-cell eller HYPOTES med
# bevis_cell: null. Skalet ar detsamma som "ingen troskel utan matreferens":
# ett tak som inte sager om det ar bevisat lases som bevisat.
#
# Hos oss ar STEGEN harledda ur grindar som redan ar matta (I9, I1, M-09) -
# den delen ar inte en gissning. Att rundtalet RACKER ar daremot inte provat
# mot en enda skarp korning, och budgeten sager det sjalv.
UPPNADD = "UPPNADD"
HYPOTES = "HYPOTES"
BUDGETSTATUS = (UPPNADD, HYPOTES)


class Budget(object):
    """Ett rundtak, dess harledning, och om det ar bevisat."""

    __slots__ = ("rundor", "steg", "status", "bevis")

    def __init__(self, rundor, steg, status, bevis=None):
        if status not in BUDGETSTATUS:
            raise ValueError("okand budgetstatus %r" % (status,))
        if status == UPPNADD and not bevis:
            raise ValueError(
                "en UPPNADD budget maste namna korningen som uppnadde den; "
                "ett tak utan bevis ar en HYPOTES med battre sjalvfortroende")
        self.rundor = rundor
        self.steg = tuple(steg)
        self.status = status
        self.bevis = bevis

    def __repr__(self):
        return "Budget(%d rundor, %s)" % (self.rundor, self.status)

    def text(self):
        rader = ["BUDGET %d rundor (%s, bevis: %s)"
                 % (self.rundor, self.status, self.bevis or "inget")]
        for s in self.steg:
            rader.append("    %s <- %s" % (s.vad, s.regel))
        rader.append("    + %d runda for slutsvaret (24_samtalsloopen.md)"
                     % RUNDA_FOR_SLUTSVARET)
        if self.status == HYPOTES:
            rader.append("    stegen ar harledda ur matta grindar; att talet "
                         "RACKER ar inte provat mot en skarp korning (M-162)")
        return "\n".join(rader)


def budget(dom):
    """Budgeten med sin harledning OCH sin status.

    Statusen ar HYPOTES for bada de byggda avsikterna, och det ar ett
    besked och inte en formalitet: ingen skarp tur har korts mot ett
    rundtak harlett pa det har sattet. Den dagen en korning visar att
    taket racker byts statusen mot UPPNADD med korningens namn.
    """
    return Budget(turbudget(dom), nodvandiga_steg(dom), HYPOTES, None)


def turbudget(dom):
    """Hur manga rundor avsikten behover. En summa, inte en tabell.

    Taket ar loopens eget MAX_RUNDOR (arvt, 20_arv.md). En harledd budget som
    gar over taket ar ett besked och inte en avrundning: uppgiften ryms inte i
    en tur, och den ska delas.
    """
    from ..harness.loop import MAX_RUNDOR
    return min(len(nodvandiga_steg(dom)) + RUNDA_FOR_SLUTSVARET, MAX_RUNDOR)


def ryms_i_en_tur(dom):
    """Falskt nar de nodvandiga stegen inte far plats under loopens tak."""
    from ..harness.loop import MAX_RUNDOR
    return len(nodvandiga_steg(dom)) + RUNDA_FOR_SLUTSVARET <= MAX_RUNDOR
