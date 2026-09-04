# -*- coding: utf-8 -*-
"""Fran en RIKTIG komponent till ett objekt layoutlosaren kan placera.

VARFOR DEN HAR FILEN FINNS
--------------------------
Fas 5 stangdes pa 18 layouter, 117 objektpar och noll kollisioner. Allt var
lador. `provscener.py` sager det rent ut: maskinernas fotavtryck ar ANTAGNA,
och robotens lada raknas som en andel av rackvidden (`ROBOTFOT_ANDEL = 0.30`).
Ett bevis pa MEKANISMEN, inte pa att en riktig cell gar att stalla upp.

Den har modulen ar bryggan. `komponentfil.py` laser vad en .vcmx faktiskt bar;
den har modulen gor ett `Objekt` av det, med samma harda regel som resten av
motorn: **ett matt som datan inte bar fylls aldrig i.**

DEN OBEKVAMA RADEN, OCH DEN AR MATT
-----------------------------------
Den omslutande volymen star INTE i filen (M-61). Inte i model.xml, inte i
component.rsc, och inte heller i VC:s egen eCatalog-databas. Den ar ingen
egenskap hos filen utan hos den BYGGDA komponenten vid en viss
parameteruppsattning och en viss stallning.

Darfor har `objekt_ur_komponent` inget forval for lada. Utan ett svar fran
VC:s `get_bounds` kastar den `Saknasfel` med namnet pa det som saknas. Det ar
samma fail-closed-hallning som `vc_utdata.till_verktygsanrop` har mot ett
ANTAGET ankare, och av samma skal: ett antagande som kors mot en riktig scen
flyttar komponenten fel, tyst.

VAD SOM DAREMOT GAR ATT LASA
----------------------------
Rackvidden gar. Den star som `Reach` i model.xml, och for 225 robotar dar det
faltet ar tomt ELLER NOLL gar den att rakna ur `envelopeprofile`, robotens egen
rackviddsprofil. Bada vagarna bar sin harkomst.

Transportorens ORDNING gar. Vilket granssnitt som tar emot och vilket som
lamnar ifran sig star i filen for 122 av 163 transportorer. Dess RIKTNING som
en vektor gor det inte: ramarnas lage ar parametriskt i 303 av 324 fall, och
`flode_ur_fakta` lamnar da vektorn outraknad med uttrycket som skal.

Granssnitten gar. Namn, sektioner, ramar och falttyper - allt det en generisk
kontakt inte har. `kopplingsbara()` foreslar par ur den datan, och foreslar ar
ratt ord: regeln ar last ur filerna och ska provas i VC, inte tros pa.

Kalla: docs/matningar/M-61, docs/spec/90_invarianter.md I3 (tystnad ar inget
godkannande), uppdragets punkt 2.
"""
from __future__ import annotations

import math

from ..komponentfil import Harkomst, Komponentfakta
from .matt import Langd, krav
from .rum import Ankare, Layoutfel, Objekt, VRIDNINGAR_RATA

__all__ = ["Saknasfel", "Bounds", "Matt", "Koppling", "Flode", "Bindning",
           "rackvidd_ur_fakta", "objekt_ur_komponent", "saknade_matt",
           "kopplingsbara", "flode_ur_fakta", "komponentnamn_karta"]


class Saknasfel(Layoutfel):
    """Ett matt som datan inte bar begardes, och det finns inget svar.

    Felet bar alltid VAD som saknas och VAR det gar att hamta. Ett tomt matt
    som tyst blir noll ar den falla hela motorn ar byggd for att undvika.
    """


class Matt(object):
    """Ett varde med sin harkomst och sin kalla. Aldrig ett bart tal."""

    __slots__ = ("varde", "harkomst", "kalla")

    def __init__(self, varde, harkomst, kalla):
        self.varde = varde
        self.harkomst = harkomst
        self.kalla = kalla

    def __bool__(self):
        return self.varde is not None

    def __repr__(self):
        return "Matt(%r, %s, %r)" % (self.varde, self.harkomst, self.kalla)


class Bounds(object):
    """VC:s `get_bounds`-svar: `center` och `half_extent` i MILLIMETER.

    Formen provas har och inte i en kommentar. Ett halvt matt som ar noll
    eller negativt ar ingen lada, och en lada med noll utstrackning gar inte
    att placera - da ar svaret fel, inte objektet platt.
    """

    __slots__ = ("center_mm", "halv_mm")

    def __init__(self, center_mm, halv_mm):
        c = [float(v) for v in center_mm]
        h = [float(v) for v in halv_mm]
        if len(c) != 3 or len(h) != 3:
            raise Saknasfel("get_bounds ger tre tal per falt, fick %d och %d"
                            % (len(c), len(h)))
        for v in h:
            if not v > 0.0:
                raise Saknasfel(
                    "halvt matt %.6g mm ar inte positivt. En komponent utan "
                    "utstrackning gar inte att placera, och noll ar inget "
                    "matt - det ar ett saknat matt som ser ut som ett matt."
                    % v)
        self.center_mm = tuple(c)
        self.halv_mm = tuple(h)

    @classmethod
    def ur_svar(cls, svar):
        """Ur verktygsskiktets ordbok: {"center": [...], "half_extent": [...]}."""
        if not isinstance(svar, dict):
            raise Saknasfel("get_bounds-svaret ar ingen ordbok: %r" % (svar,))
        for nyckel in ("center", "half_extent"):
            if nyckel not in svar:
                raise Saknasfel("get_bounds-svaret saknar %r" % nyckel)
        return cls(svar["center"], svar["half_extent"])

    @property
    def storlek_mm(self):
        return tuple(2.0 * v for v in self.halv_mm)

    def __repr__(self):
        return ("Bounds(center=%r mm, halv=%r mm)"
                % (self.center_mm, self.halv_mm))


def rackvidd_ur_fakta(fakta):
    """Robotens rackvidd som ett `Matt`, med harkomst och kalla.

    Sjalva avgorandet ligger i `Komponentfakta.rackvidd`, for det ar en
    egenskap hos FILEN och inte hos layouten. Har byts bara millimetern mot
    en `Langd`, sa att motorns enhetsskydd galler aven for den.
    """
    if not isinstance(fakta, Komponentfakta):
        raise Layoutfel("rackvidd_ur_fakta tar en Komponentfakta")
    mm, harkomst, kalla = fakta.rackvidd()
    return Matt(None if mm is None else Langd.mm(mm), harkomst, kalla)


def saknade_matt(fakta, bounds=None):
    """Vad som fattas innan komponenten gar att placera. En lista, inte tystnad."""
    ut = []
    if bounds is None:
        ut.append("omslutande volym: %s" % fakta.lada_skal)
    if not fakta.namn:
        ut.append("namn: model.xml bar inget Name")
    if fakta.kategori == "Robots" and not rackvidd_ur_fakta(fakta):
        ut.append("rackvidd: %s" % rackvidd_ur_fakta(fakta).kalla)
    for r in fakta.ramar:
        if r.harkomst != Harkomst.LAST:
            ut.append("ramen %r: lage %s%s"
                      % (r.namn, r.harkomst,
                         " (uttryck %r)" % r.uttryck if r.uttryck else ""))
    return tuple(ut)


def objekt_ur_komponent(fakta, bounds=None, namn=None,
                        underhallsmarginal=None, kravd_fri_hojd=None,
                        tillatna_vridningar_grader=VRIDNINGAR_RATA,
                        barande=False, enhet=""):
    """Ett `Objekt` ur en riktig komponent. Kraver VC:s lada.

    `bounds` ar ett `Bounds`, alltsa VC:s `get_bounds`-svar. Utan det kastas
    `Saknasfel`: filen bar ingen omslutande volym, och en lada som gissas ur
    rackvidden eller ur ett katalognamn ar precis den falska greenen fas 5
    stangdes pa.

    Marginalen och den fria hojden ar POLITIK, inte data. De star ingenstans i
    komponentfilen, och forvalet ar darfor noll - alltsa "ingen marginal
    begard", inte "ingen marginal behovs". Den som vill ha en marginal anger
    den, och da bar anropet talet i stallet for modulen.
    """
    if not isinstance(fakta, Komponentfakta):
        raise Layoutfel("objekt_ur_komponent tar en Komponentfakta")
    if bounds is None:
        raise Saknasfel(
            "komponenten %r bar ingen omslutande volym i sin fil. %s. "
            "Las den i VC med verktyget get_bounds och lamna svaret som "
            "Bounds.ur_svar(...). Saknas: %s"
            % (fakta.namn or fakta.sokvag, fakta.lada_skal,
               "; ".join(saknade_matt(fakta)) or "inget mer"))
    if not isinstance(bounds, Bounds):
        raise Layoutfel("bounds maste vara ett Bounds, fick %s"
                        % type(bounds).__name__)
    langd_mm, bredd_mm, hojd_mm = bounds.storlek_mm
    rackvidd = rackvidd_ur_fakta(fakta)
    return Objekt(
        namn or fakta.namn,
        Langd.mm(langd_mm), Langd.mm(bredd_mm), Langd.mm(hojd_mm),
        underhallsmarginal=(Langd.noll() if underhallsmarginal is None
                            else krav(underhallsmarginal, "underhallsmarginal")),
        kravd_fri_hojd=(Langd.noll() if kravd_fri_hojd is None
                        else krav(kravd_fri_hojd, "kravd_fri_hojd")),
        tillatna_vridningar_grader=tillatna_vridningar_grader,
        barande=barande,
        # Ankaret ar MATT: det kommer ur VC:s eget svar, inte ur ett antagande
        # om att origo ligger i fotavtryckets mitt.
        ankare=Ankare.ur_bounds(bounds.center_mm, bounds.halv_mm),
        # Kategorin ar komponentens EGEN (model.xml, egenskapen Type), inte
        # katalogens namn. Skillnaden ar M-58:s hela poang.
        kategori=fakta.kategori,
        rackvidd=rackvidd.varde,
        enhet=enhet)


class Koppling(object):
    """Ett FORESLAGET granssnittspar, med skalet till forslaget.

    Foreslaget, inte fastslaget. Regeln nedan ar last ur filerna, och om VC
    haller med gar bara att veta genom att fraga VC. Fas 5:s omkorning ar den
    fragan.
    """

    __slots__ = ("granssnitt_a", "granssnitt_b", "skal")

    def __init__(self, granssnitt_a, granssnitt_b, skal):
        self.granssnitt_a = granssnitt_a
        self.granssnitt_b = granssnitt_b
        self.skal = skal

    def __eq__(self, annan):
        return (isinstance(annan, Koppling)
                and self.granssnitt_a == annan.granssnitt_a
                and self.granssnitt_b == annan.granssnitt_b
                and self.skal == annan.skal)

    def __hash__(self):
        return hash((self.granssnitt_a, self.granssnitt_b, self.skal))

    def __repr__(self):
        return ("Koppling(%r -> %r, %s)"
                % (self.granssnitt_a, self.granssnitt_b, self.skal))


#: Flodesfaltets portnummer. 0 tar emot, 1 lamnar ifran sig. LAST ur
#: biblioteket: varje rSimFlowField bar Port, och en transportors InInterface
#: har 0 medan dess OutInterface har 1 (M-61).
#:
#: RACKVIDDEN AR MATT OCH BEGRANSAD: av bibliotekets 533 flodesfalt bar 458
#: port 0 eller 1. De ovriga 75 bar 2 till 6 - grenar och samlingar med fler
#: an tva vagar - och dem sager regeln nedan INGENTING om. Ett par som inte
#: foreslas ar inte ett par som ar omojligt; det ar ett par regeln inte tacker,
#: och skillnaden ska sta har och inte upptackas i en korning.
_PORT_IN = 0                    # Satt av M-61.
_PORT_UT = 1                    # Satt av M-61.


def _flodesportar(granssnitt):
    return set(f.port for s in granssnitt.sektioner for f in s.falt
               if f.sort == "rSimFlowField" and f.port is not None)


def _hierarkifalt(granssnitt):
    return [f for s in granssnitt.sektioner for f in s.falt
            if f.sort == "rSimHierarchyField"]


def kopplingsbara(fakta_a, fakta_b):
    """Granssnittspar som ser ut att ga att koppla, A -> B.

    Tva regler, bada lasta ur biblioteket och ingen av dem gissad:

    1. FLODE. Ett `rSimFlowField` med port 1 i A och ett med port 0 i B. Det
       ar transportorkedjan: `OutInterface` till `InInterface`.
    2. MONTERING. Ett `rSimHierarchyField` med `Mount 1` i A och `Mount 0` i
       B, och samma uppsattning falttyper i de tva sektionerna. Det ar
       verktyget pa robotflansen: robotens `Tool` bar Mount 1, och den som
       tar emot bar Mount 0.

    Riktningen betyder nagot. `kopplingsbara(a, b)` ar inte samma sak som
    `kopplingsbara(b, a)`, och ett par som bara gar at ett hall ska bara
    komma tillbaka en gang.
    """
    if not isinstance(fakta_a, Komponentfakta) or not isinstance(
            fakta_b, Komponentfakta):
        raise Layoutfel("kopplingsbara tar tva Komponentfakta")
    ut = []
    for ga in fakta_a.granssnitt:
        for gb in fakta_b.granssnitt:
            if _PORT_UT in _flodesportar(ga) and _PORT_IN in _flodesportar(gb):
                ut.append(Koppling(ga.namn, gb.namn, "flode ut -> in"))
                continue
            ha = [f for f in _hierarkifalt(ga) if f.mount == 1]
            hb = [f for f in _hierarkifalt(gb) if f.mount == 0]
            if ha and hb and set(ga.falttyper) & set(gb.falttyper):
                ut.append(Koppling(ga.namn, gb.namn, "montering pa ramen %s"
                                   % (ga.ramar[0] if ga.ramar else "okand")))
    return tuple(ut)


class Flode(object):
    """Transportorens riktning, sa langt filen bar den.

    Filen ger ORDNINGEN: vilket granssnitt som tar emot och vilket som lamnar
    ifran sig, och vilka ramar de sitter pa. Den ger sallan LAGET: ramarnas
    lage ar parametriskt i 303 av 324 flodesramar bland bibliotekets
    transportorer (M-61), sa riktningen som en VEKTOR kan inte raknas fram.

    Darfor tva falt och inte ett. `ordning` ar last; `riktning_mm` ar None
    med ett skal nar ramlagena inte gar att lasa. Att lamna vektorn
    outraknad ar ratt svar - att peka den langs komponentens X vore en
    gissning som ser komplett ut.
    """

    __slots__ = ("in_granssnitt", "ut_granssnitt", "in_ram", "ut_ram",
                 "in_lage_mm", "ut_lage_mm", "skal")

    def __init__(self, in_granssnitt, ut_granssnitt, in_ram=None, ut_ram=None,
                 in_lage_mm=None, ut_lage_mm=None, skal=""):
        self.in_granssnitt = tuple(in_granssnitt)
        self.ut_granssnitt = tuple(ut_granssnitt)
        self.in_ram = in_ram
        self.ut_ram = ut_ram
        self.in_lage_mm = in_lage_mm
        self.ut_lage_mm = ut_lage_mm
        self.skal = skal

    @property
    def ordning(self):
        """Bar komponenten bade en ingang och en utgang?"""
        return bool(self.in_granssnitt) and bool(self.ut_granssnitt)

    @property
    def riktning_mm(self):
        """Vektorn fran ingangens ram till utgangens, eller None."""
        if self.in_lage_mm is None or self.ut_lage_mm is None:
            return None
        return tuple(self.ut_lage_mm[i] - self.in_lage_mm[i] for i in range(3))

    @property
    def langd_mm(self):
        """Avstandet mellan ramarna, eller None. Aldrig komponentens langd."""
        v = self.riktning_mm
        if v is None:
            return None
        return math.sqrt(sum(x * x for x in v))

    def __repr__(self):
        return ("Flode(%r -> %r, riktning %s)"
                % (self.in_granssnitt, self.ut_granssnitt,
                   self.riktning_mm if self.riktning_mm is not None
                   else Harkomst.SAKNAS))


def flode_ur_fakta(fakta):
    """Transportorens flodesordning och, om den gar att lasa, dess riktning.

    Ger None nar komponenten inte bar nagot flodesfalt alls - 41 av
    bibliotekets 163 transportorer gor inte det (M-61), och det ar ett svar
    och inte ett fel.
    """
    if not isinstance(fakta, Komponentfakta):
        raise Layoutfel("flode_ur_fakta tar en Komponentfakta")
    inn = [g for g in fakta.granssnitt if _PORT_IN in _flodesportar(g)]
    ut = [g for g in fakta.granssnitt if _PORT_UT in _flodesportar(g)]
    if not inn and not ut:
        return None
    ramar = {r.namn: r for r in fakta.ramar}

    def lage(granssnitt):
        for g in granssnitt:
            for sektion in g.sektioner:
                r = ramar.get(sektion.ram)
                if r is not None and r.lage_mm is not None:
                    return sektion.ram, r.lage_mm, ""
                if r is not None:
                    return sektion.ram, None, r.uttryck or "ramens lage saknas"
        return None, None, "inget flodesfalt med en ram"

    in_ram, in_lage, in_skal = lage(inn)
    ut_ram, ut_lage, ut_skal = lage(ut)
    skal = ""
    if in_lage is None or ut_lage is None:
        skal = ("riktningen gar inte att rakna: %s"
                % "; ".join(x for x in (in_skal, ut_skal) if x))
    return Flode([g.namn for g in inn], [g.namn for g in ut],
                 in_ram, ut_ram, in_lage, ut_lage, skal)


class Bindning(object):
    """Ett layoutnamn bundet till en riktig komponent, och till dess lada.

    Bindningen ar det som gor att `vc_utdata.till_verktygsanrop` kan skriva
    RATT komponentnamn i anropet. Layoutens namn ar operatorens ("robot_1");
    VC:s namn ar komponentens ("IRB 6700-150/3.20"). Att blanda ihop dem ar
    att skriva ett anrop mot en komponent som inte finns.
    """

    __slots__ = ("layoutnamn", "fakta", "bounds")

    def __init__(self, layoutnamn, fakta, bounds=None):
        self.layoutnamn = str(layoutnamn)
        if not self.layoutnamn:
            raise Layoutfel("en bindning maste ha ett layoutnamn")
        if not isinstance(fakta, Komponentfakta):
            raise Layoutfel("bindningen tar en Komponentfakta")
        self.fakta = fakta
        self.bounds = bounds

    def objekt(self, **kw):
        return objekt_ur_komponent(self.fakta, bounds=self.bounds,
                                   namn=self.layoutnamn, **kw)

    def __repr__(self):
        return ("Bindning(%r -> %r, lada %s)"
                % (self.layoutnamn, self.fakta.namn,
                   "matt" if self.bounds else Harkomst.SAKNAS))


def komponentnamn_karta(bindningar):
    """{layoutnamn: komponentnamn} for `vc_utdata.till_verktygsanrop`."""
    ut = {}
    for b in bindningar:
        if not isinstance(b, Bindning):
            raise Layoutfel("komponentnamn_karta tar Bindning-poster")
        if not b.fakta.namn:
            raise Saknasfel("komponenten bakom %r bar inget namn i model.xml"
                            % b.layoutnamn)
        ut[b.layoutnamn] = b.fakta.namn
    return ut
