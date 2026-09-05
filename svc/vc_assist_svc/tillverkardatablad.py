# -*- coding: utf-8 -*-
"""Tredje kallskiktet: tillverkarens PUBLICERADE datablad, med enhet och kalla.

VARFOR DEN HAR FILEN FINNS
--------------------------
M-85 matte hela biblioteket: 3201 komponenter, 82 383 egenskaper. Strukturen ar
valfylld (100 procent lasbara datablad, 96 procent med egna egenskaper).
Semantiken ar det inte: bara 14,0 procent av egenskaperna deklarerar vilken
STORHET de bar, och ingen enda deklarerar en ENHET.

Det skarpaste fallet star i katalogposten. `MaxPayload` finns i 2986 av 3201
komponenter, utan enhet, och 628 av dem har vardet `0`. En nolla utan enhet ar
inte en nyttolast pa noll kilo - det ar ett ofyllt falt. Skrivs den ut som
"0 kg" har vi tillverkat ett faktum.

`docs/spec/51_komponentdata.md` §2 namnger tre kallor. De tva forsta ar VC:s
egna filer och de kan inte ge en enhet. Den tredje ligger utanfor:

    model.xml       katalogfalt: familj, tillverkare, MaxPayload, Reach
                    ger INTE: enheter, giltighetsintervall
    component.rsc   egenskaper, beteenden, granssnitt, leder
                    ger INTE: storhet i 86 procent av fallen, aldrig en enhet
    tillverkarens   nyttolast, rackvidd, repeterbarhet - MED ENHET
    datablad        ger INTE: vad komponenten heter invandigt i VC

Den tredje ar ENDA vagen till en enhet som inte ar gissad. Den har modulen ar
den vagen.

DE TRE LAGENA, OCH SKILLNADEN AR INTE KOSMETISK (spec §4)
---------------------------------------------------------
    finns          varde OCH enhet, med kalla.  Grinden far doma pa det.
    saknas         faltet finns inte i nagon kalla. Grinden AVSTAR, och
                   sager att den avstar.
    enhet_saknas   vardet finns, enheten inte. Talet far visas ORDAGRANT,
                   aldrig jamforas.

Det tredje lagets ar det som glomms. Ett tal utan enhet som jamfors med ett tal
med enhet ar ett fel som ser ut som ett svar. Darfor bar `Svar` i laget
`enhet_saknas` INGET talvarde alls, bara strangen `ordagrant`: det gar inte att
rakna pa den av misstag, for det finns inget tal att rakna pa.

ENHETSGRINDEN: EN ENHET SOM HARLETTS UR ETT VARDE FALLS
--------------------------------------------------------
Frestelsen ar att skriva `MaxPayload: 180` som `180 kg`. Det ser ratt ut, det
ar troligen ratt, och det ar anda ett pahitt: ingen kalla har sagt kg.

Grinden ar mekanisk och sitter i `Uppgift.__post_init__`. En uppgift far bara
finnas om TALET OCH ENHETEN STAR BREDVID VARANDRA I ETT ORDAGRANT CITAT ur den
hamtade kallan. `180` plus enheten `kg` ur ett citat som inte skriver "180 kg"
gar inte att konstruera. Utan citat, ingen enhet.

Det ar ocksa skalet till att `Kalla` kraver url, hamtdatum, sha256 och citat:
en siffras harkomst hor till siffran, och ett datablad utan kalla ar ett
pastaende.

TVA GRANSER SOM GALLER AVEN NAR DET AR BYGGT
--------------------------------------------
1. Ett datablad galler en MODELL, inte en instans. Tva robotar av samma typ med
   olika verktyg har olika nyttolast kvar. Databladets tal ar ett TAK, aldrig
   ett driftvarde - ett typskyltvarde ar en anslutning, inte en forbrukning.
   `Domslut.text()` skriver ut det varje gang, och `rymmer()` heter inte
   `racker()`.
2. En komponent utan datablad star som `saknas`. Den fylls ALDRIG med en
   grannes tal. Matchningen mot biblioteket sker darfor pa en UTSKRIVEN lista
   `vc_namn` i korpusposten, aldrig pa likhet - en robot som heter nastan
   likadant ar en annan robot.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, replace, field
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Lagen
# ---------------------------------------------------------------------------

FINNS = "finns"
SAKNAS = "saknas"
ENHET_SAKNAS = "enhet_saknas"
LAGEN = (FINNS, SAKNAS, ENHET_SAKNAS)

# Domslutets utfall. AVSTAR ar ett forstklassigt svar och inte ett fel.
RYMS = "ryms"
RYMS_INTE = "ryms_inte"
AVSTAR = "avstar"


class Tillverkarfel(Exception):
    """Nagot i kallskiktet gick inte att gora ARLIGT. Aldrig ett tyst tomt falt."""


# ---------------------------------------------------------------------------
# Falten och deras enheter
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Faltdef:
    """Ett falt vi berikar, och vilka enheter det far bara.

    `enheter` ar enhet -> faktor till den kanoniska enheten. Listan ar KORT med
    flit: bara SI-enheter som en tillverkare faktiskt skriver ut. En
    tumenhetsomvandling ("27.6 lbs") ar en rakning pa ett tal, och den hor inte
    hemma i kallskiktet - citatet ska bara den enhet vi lagrar.
    """

    namn: str
    storhet: str            # samma ord som VC:s Quantity: Mass, Distance
    kanonisk: str
    enheter: Dict[str, float]


FALT: Dict[str, Faltdef] = {
    "nyttolast": Faltdef("nyttolast", "Mass", "kg", {"kg": 1.0, "g": 0.001}),
    "rackvidd": Faltdef("rackvidd", "Distance", "mm",
                        {"mm": 1.0, "cm": 10.0, "m": 1000.0}),
    "repeterbarhet": Faltdef("repeterbarhet", "Distance", "mm",
                             {"mm": 1.0, "cm": 10.0, "m": 1000.0}),
    "vikt": Faltdef("vikt", "Mass", "kg", {"kg": 1.0, "g": 0.001}),
    # Diametern pa arbetsomradet ar INTE rackvidden, och den ligger har just
    # for att inte bli det. ABB publicerar IRB 360-1/1130 med rubriken
    # "Diameter", inte "Reach". Bankens post for samma robot bar 565 mm =
    # 1130/2 under stampeln PUBLICERAD_SPEC - en RAKNING pa ett publicerat tal,
    # inte ett publicerat tal. Tva namn for tva storheter, sa att ingen kan
    # jamfora dem av misstag.
    "diameter": Faltdef("diameter", "Distance", "mm",
                        {"mm": 1.0, "cm": 10.0, "m": 1000.0}),
}

# De katalogfalt i model.xml som motsvarar ett berikat falt. Namnet till
# vanster ar VC:s, namnet till hoger ar vart - och VC:s namn bar INGEN enhet.
KATALOGFALT: Dict[str, str] = {
    "maxpayload": "nyttolast",
    "reach": "rackvidd",
}


def faltdef(falt: str) -> Faltdef:
    d = FALT.get(falt)
    if d is None:
        raise Tillverkarfel("unknown field %r; known: %s"
                            % (falt, ", ".join(sorted(FALT))))
    return d


# ---------------------------------------------------------------------------
# Kallan: url, hamtdatum, sha256, citat
# ---------------------------------------------------------------------------

_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def normalisera(text: str) -> str:
    """Ett dokuments text som EN rad med enkla mellanslag.

    Databladen ar PDF:er med kolumnlayout. `pdftotext -layout` bryter "Max.
    reach:" och "911 mm" pa var sin rad med trettio mellanslag emellan, och ett
    citat som ska ga att kontrollera far inte bero pa hur mycket luft
    utdragningen lamnade kvar. Normaliseringen ar darfor DEN ENDA jamforelsen
    som anvands, bade nar citatet skrivs och nar det kontrolleras.
    """
    return re.sub(r"\s+", " ", (text or "").replace(" ", " ")).strip()


@dataclass(frozen=True)
class Kalla:
    """Varifran en uppgift kom. Alla fyra falten kravs.

    En siffras harkomst hor till siffran. Ett datablad utan kalla ar ett
    pastaende, och den regeln ar en konstruktor och inte en rekommendation.

    `utdrag` ar den normaliserade texten RUNT citatet, cirka 400 tecken. Den
    ligger i korpusen just for att korpusgrinden ska ga att kora utan natet och
    utan cachen: citatet maste sta i utdraget, och utdraget maste sta i det
    cachade dokumentet. Utan utdraget hade den mellersta grinden krävt att
    varenda PDF lag i repot.
    """

    url: str
    hamtad: str
    sha256: str
    citat: str
    utdrag: str = ""
    dokument: str = ""

    def __post_init__(self):
        if not (self.url or "").startswith(("http://", "https://")):
            raise Tillverkarfel("the source's url is not a url: %r" % (self.url,))
        if not _DATUM.match(self.hamtad or ""):
            raise Tillverkarfel("the source's fetch date must be YYYY-MM-DD, not %r"
                                % (self.hamtad,))
        if not _SHA.match((self.sha256 or "").lower()):
            raise Tillverkarfel("the source's sha256 is not a sha256: %r"
                                % (self.sha256,))
        if not normalisera(self.citat):
            raise Tillverkarfel("a source without a quote is not a source (%s)" % self.url)
        if self.utdrag and normalisera(self.citat) not in normalisera(self.utdrag):
            raise Tillverkarfel(
                "the quote is not in the excerpt from %s: %r" % (self.url, self.citat))

    def rad(self) -> str:
        return '%s (hamtad %s, sha256 %s...): "%s"' % (
            self.url, self.hamtad, self.sha256[:12], normalisera(self.citat))

    def till_json(self) -> Dict[str, str]:
        d = {"url": self.url, "hamtad": self.hamtad, "sha256": self.sha256,
             "citat": self.citat}
        if self.utdrag:
            d["utdrag"] = self.utdrag
        if self.dokument:
            d["dokument"] = self.dokument
        return d

    @staticmethod
    def fran_json(d: Dict[str, str]) -> "Kalla":
        if not isinstance(d, dict):
            raise Tillverkarfel("a source must be an object, not %r" % (d,))
        okanda = set(d) - {"url", "hamtad", "sha256", "citat", "utdrag", "dokument"}
        if okanda:
            raise Tillverkarfel("unknown fields in the source: %s" % ", ".join(sorted(okanda)))
        return Kalla(url=d.get("url", ""), hamtad=d.get("hamtad", ""),
                     sha256=d.get("sha256", ""), citat=d.get("citat", ""),
                     utdrag=d.get("utdrag", ""), dokument=d.get("dokument", ""))


# ---------------------------------------------------------------------------
# Enhetsgrinden: talet och enheten ska sta BREDVID VARANDRA i citatet
# ---------------------------------------------------------------------------

def _talmonster(varde: float) -> str:
    """Ett regexuttryck for hur tillverkaren kan ha skrivit just det talet.

    Tillaten variation: decimalpunkt eller decimalkomma, tusentalsavskiljare
    (Yaskawa skriver "1,693 mm"), och en heltalsdel utan decimaler nar vardet
    ar helt. INTE tillaten: ett annat tal. Avrundning ar en RAKNING och den hor
    inte hemma har - star det "2.65 m" i databladet ar vardet 2.65 m, inte
    2655 mm, och omvandlingen sker i jamforelsen dar den syns.
    """
    if varde == int(varde):
        heltal = str(int(varde))
        # 1693 -> 1[.,]?693 sa att "1,693" och "1693" bada gar
        grupperat = re.sub(r"(?<=\d)(?=(?:\d{3})+$)", "@", heltal).split("@")
        med_avskiljare = r"[.,  ]?".join(re.escape(g) for g in grupperat)
        # "2.00 m" ar samma tal som "2 m". Efterslapande nollor ar
        # skrivsatt, inte precision - ABB skriver bade "2.00" och "3.15"
        # i samma tabell.
        return r"(?:%s(?:[.,]0+)?)" % med_avskiljare
    text = repr(float(varde))
    if text.endswith(".0"):
        text = text[:-2]
    heltalsdel, _punkt, decimaler = text.partition(".")
    return r"(?:%s[.,]%s0*)" % (re.escape(heltalsdel), re.escape(decimaler))


def par_i_citat(citat: str, varde: float, enhet: str) -> bool:
    """Star `varde` och `enhet` BREDVID VARANDRA i citatet?

    Det har ar hela enhetsgrinden. `MaxPayload: 180` gar inte att gora till
    `180 kg` genom att skriva dit "kg" - citatet maste sjalv sага "180 kg".
    Mellanslag och en eventuell enhetsparentes emellan ar tillatna; ett annat
    tal emellan ar det inte.
    """
    n = normalisera(citat)
    # Vansterspärren ar inte kosmetisk: utan den matchar vardet 901 inne i
    # "1901 mm", och grinden hade slappt igenom ett tal som inte star i texten.
    monster = r"(?<![\d.,])%s\s*%s(?![A-Za-zµ])" % (_talmonster(varde),
                                                     re.escape(enhet))
    return re.search(monster, n, re.IGNORECASE) is not None


# ---------------------------------------------------------------------------
# Den andra lasningen: en tabell dar ENHETEN star i rubriken
# ---------------------------------------------------------------------------
#
# Halva bibliotekets robotdatablad skriver inte "20 kg" utan en tabell:
#
#     Robot variant       Handling capacity (kg)   Reach (m)
#     IRB 2600-20/1.65    20                       1.65
#
# Enheten STAR i dokumentet - ABB har sagt kg - men den star i rubriken och
# inte bredvid talet. Att lasa den tabellen ar inte att harleda en enhet ur ett
# varde; det ar att folja en kolumn. Men det ar en SVAGARE lasning an ett
# ordagrant par, den kan lasa fel kolumn, och darfor ar den ett eget lage med
# en egen grind i stallet for ett undantag i den forsta.
#
# Grinden ar positionell och mekanisk:
#   * bade rubriken och raden ska sta ORDAGRANT i dokumentet (utdraget)
#   * raden ska borja med modellnamnet, som stryks innan talen raknas
#   * enheten pa plats `index` bland rubrikens parentesenheter ska vara var
#   * talet pa plats `index` bland radens tal ska vara vart
#
# En kolumnlasning som pekar fel faller alltsa pa sin egen rubrik. Och den
# skrivs alltid ut som "positionsläst kolumn" - en lasare ska kunna se att
# kopplingen mellan talet och enheten kom ur en placering.

_PARENTESENHET = re.compile(r"\(([^)]{1,12}?)\)")
_TAL = re.compile(r"-?\d+(?:[.,]\d+)?")


@dataclass(frozen=True)
class Kolumn:
    """En positionell lasning av en tabellrad vars enhet star i rubriken."""

    rubrik: str
    rad: str
    modell_i_rad: str
    index: int

    def __post_init__(self):
        for namn, v in (("rubrik", self.rubrik), ("rad", self.rad),
                        ("modell_i_rad", self.modell_i_rad)):
            if not normalisera(v):
                raise Tillverkarfel("the column reading is missing %s" % namn)
        if not isinstance(self.index, int) or self.index < 0:
            raise Tillverkarfel("column index must be a non-negative integer, "
                                "not %r" % (self.index,))
        if not normalisera(self.rad).lower().startswith(
                normalisera(self.modell_i_rad).lower()):
            raise Tillverkarfel(
                "the row %r does not start with the model name %r - without that "
                "the numbers cannot be counted, since the model name contains digits"
                % (normalisera(self.rad), normalisera(self.modell_i_rad)))

    def enheter(self) -> List[str]:
        return [normalisera(m.group(1))
                for m in _PARENTESENHET.finditer(normalisera(self.rubrik))]

    def tal(self) -> List[str]:
        svans = normalisera(self.rad)[len(normalisera(self.modell_i_rad)):]
        return _TAL.findall(svans)

    def stammer(self, varde: float, enhet: str) -> Tuple[bool, str]:
        e = self.enheter()
        t = self.tal()
        if self.index >= len(e):
            return False, ("rubriken %r bar %d parentesenheter, kolumn %d finns "
                           "inte" % (normalisera(self.rubrik), len(e), self.index))
        if self.index >= len(t):
            return False, ("raden %r bar %d tal, kolumn %d finns inte"
                           % (normalisera(self.rad), len(t), self.index))
        if e[self.index].lower() != enhet.lower():
            return False, ("kolumn %d i rubriken sager enheten %r, uppgiften "
                           "sager %r" % (self.index, e[self.index], enhet))
        try:
            if float(t[self.index].replace(",", ".")) != float(varde):
                return False, ("kolumn %d i raden sager talet %s, uppgiften "
                               "sager %s" % (self.index, t[self.index], varde))
        except ValueError:
            return False, "kolumn %d i raden ar inget tal: %r" % (self.index,
                                                                  t[self.index])
        return True, ""

    def till_json(self) -> Dict[str, object]:
        return {"rubrik": self.rubrik, "rad": self.rad,
                "modell_i_rad": self.modell_i_rad, "index": self.index}

    @staticmethod
    def fran_json(d: Dict[str, object]) -> "Kolumn":
        okanda = set(d) - {"rubrik", "rad", "modell_i_rad", "index"}
        if okanda:
            raise Tillverkarfel("unknown fields in the column reading: %s"
                                % ", ".join(sorted(okanda)))
        return Kolumn(rubrik=str(d.get("rubrik", "")), rad=str(d.get("rad", "")),
                      modell_i_rad=str(d.get("modell_i_rad", "")),
                      index=int(d.get("index", -1)))


ORDAGRANT_PAR = "ordagrant par"
POSITIONSLAST = "positionslast kolumn"


# ---------------------------------------------------------------------------
# Uppgiften: varde, enhet, kalla - alla tre eller ingen
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Uppgift:
    """En hamtad uppgift. Bar varde, enhet och varifran den kom.

    Konstruktorn ar grinden. Den faller pa:
      * ett okant falt
      * en enhet faltet inte far bara
      * en enhet som inte star bredvid talet i citatet (den harledda enheten)
      * en kalla som saknar url, datum, sha256 eller citat
    """

    falt: str
    varde: float
    enhet: str
    kalla: Kalla
    kolumn: Optional[Kolumn] = None

    def __post_init__(self):
        d = faltdef(self.falt)
        if not isinstance(self.varde, (int, float)) or isinstance(self.varde, bool):
            raise Tillverkarfel("%s: the value is not a number (%r)"
                                % (self.falt, self.varde))
        if self.enhet not in d.enheter:
            raise Tillverkarfel(
                "%s: the unit %r does not belong to the quantity %s; allowed: %s"
                % (self.falt, self.enhet, d.storhet, ", ".join(sorted(d.enheter))))
        if not isinstance(self.kalla, Kalla):
            raise Tillverkarfel("%s: a task without a source is a claim"
                                % self.falt)
        if self.kolumn is None:
            if not par_i_citat(self.kalla.citat, self.varde, self.enhet):
                raise Tillverkarfel(
                    "%s: the unit %r is not next to the value %r in the quote "
                    "from %s. A unit inferred from a value is a guess that "
                    "looks like a measurement. The quote was: %r"
                    % (self.falt, self.enhet, self.varde, self.kalla.url,
                       normalisera(self.kalla.citat)[:200]))
            return
        # Kolumnlasning: enheten star i rubriken, inte bredvid talet. Bada
        # raderna maste sta ordagrant i det citat kallan bar, och kopplingen
        # kontrolleras positionellt.
        n = normalisera(self.kalla.citat)
        for namn, v in (("header", self.kolumn.rubrik), ("row", self.kolumn.rad)):
            if normalisera(v) not in n:
                raise Tillverkarfel(
                    "%s: %s %r is not in the source's quote. A column reading "
                    "whose header is not in the document is a guess."
                    % (self.falt, namn, normalisera(v)[:120]))
        ok, skal = self.kolumn.stammer(self.varde, self.enhet)
        if not ok:
            raise Tillverkarfel(
                "%s: kolumnlasningen ur %s stammer inte: %s"
                % (self.falt, self.kalla.url, skal))

    @property
    def lasning(self) -> str:
        return ORDAGRANT_PAR if self.kolumn is None else POSITIONSLAST

    def kanoniskt(self) -> float:
        d = faltdef(self.falt)
        return float(self.varde) * d.enheter[self.enhet]

    def till_json(self) -> Dict[str, object]:
        d: Dict[str, object] = {"varde": self.varde, "enhet": self.enhet,
                                "kalla": self.kalla.till_json()}
        if self.kolumn is not None:
            d["kolumn"] = self.kolumn.till_json()
        return d

    @staticmethod
    def fran_json(falt: str, d: Dict[str, object]) -> "Uppgift":
        if not isinstance(d, dict):
            raise Tillverkarfel("%s: the task must be an object" % falt)
        okanda = set(d) - {"varde", "enhet", "kalla", "kolumn"}
        if okanda:
            raise Tillverkarfel("%s: unknown fields in the task: %s"
                                % (falt, ", ".join(sorted(okanda))))
        if "varde" not in d or "enhet" not in d or "kalla" not in d:
            raise Tillverkarfel(
                "%s: en uppgift kraver varde, enhet OCH kalla; fick %s"
                % (falt, ", ".join(sorted(d)) or "inget"))
        kol = d.get("kolumn")
        return Uppgift(falt=falt, varde=float(d["varde"]), enhet=str(d["enhet"]),
                       kalla=Kalla.fran_json(d["kalla"]),
                       kolumn=(Kolumn.fran_json(kol) if kol else None))


# ---------------------------------------------------------------------------
# Svaret: ett av de tre lagena
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Svar:
    """Vad kallskiktet kan saga om ETT falt pa EN komponent.

    Invarianten som bar hela lagret:

        lage == FINNS          -> varde och enhet och kalla finns
        lage == SAKNAS         -> inget varde, inget ordagrant, ett skal finns
        lage == ENHET_SAKNAS   -> INGET TALVARDE, bara strangen `ordagrant`

    Det sista ar avsiktligt och det ar poangen. Ett `Svar` i laget
    `enhet_saknas` bar ingen float, sa det gar inte att rakna pa den av
    misstag: `svar.varde` ar None, och den som anda vill visa talet far det
    ordagrant som det stod i filen.
    """

    falt: str
    lage: str
    varde: Optional[float] = None
    enhet: str = ""
    kalla: Optional[Kalla] = None
    skal: str = ""
    ordagrant: str = ""
    kalltyp: str = ""       # "tillverkarens datablad", "model.xml", ...
    lasning: str = ""       # ordagrant par / positionslast kolumn
    # Vad DEN ANDRA kallan sa om samma falt, nar de sager olika. Tomt betyder
    # inte "de var overens" - det betyder att bara en av dem hade ett tal.
    #
    # VARFOR FALTET FINNS (M-107): berikningen lat tillverkarens tal vinna och
    # sa ingenting om motsagelsen. UR10e ar skarpast - model.xml skriver 12,
    # Universal Robots skriver 12,5 kg, och en cell som valjer robot efter last
    # raknade da med ett halvt kilo for lite UTAN att nagon fick veta det.
    # Ett tyst avgjort motsagelse ar ett svar som ser fardigt ut.
    motsagelse: str = ""

    def __post_init__(self):
        faltdef(self.falt)
        if self.lage not in LAGEN:
            raise Tillverkarfel("unknown mode %r; known: %s"
                                % (self.lage, ", ".join(LAGEN)))
        if self.lage == FINNS:
            if self.varde is None or not self.enhet or self.kalla is None:
                raise Tillverkarfel(
                    "%s: mode finns requires a value, a unit AND a source" % self.falt)
        elif self.lage == SAKNAS:
            if self.varde is not None or self.enhet or self.ordagrant:
                raise Tillverkarfel(
                    "%s: mode saknas may not carry a value" % self.falt)
            if not self.skal:
                raise Tillverkarfel(
                    "%s: mode saknas must state WHAT was being looked for" % self.falt)
        else:   # ENHET_SAKNAS
            if self.varde is not None:
                raise Tillverkarfel(
                    "%s: mode enhet_saknas may NOT carry a numeric value - the "
                    "number must be incomparable, not merely unlabeled" % self.falt)
            if self.enhet:
                raise Tillverkarfel(
                    "%s: lage enhet_saknas med en enhet ar en motsagelse"
                    % self.falt)
            if not self.ordagrant:
                raise Tillverkarfel(
                    "%s: mode enhet_saknas without the literal number" % self.falt)
            if not self.skal:
                raise Tillverkarfel(
                    "%s: mode enhet_saknas must state why the unit is missing"
                    % self.falt)

    @property
    def jamforbar(self) -> bool:
        """Bara `finns` far ga in i en jamforelse. Ingen genvag."""
        return self.lage == FINNS

    def kanoniskt(self) -> Optional[float]:
        if self.lage != FINNS:
            return None
        return float(self.varde) * faltdef(self.falt).enheter[self.enhet]

    def text(self) -> str:
        """En rad som bar sitt eget svar, aldrig ett tal som ser fardigt ut."""
        if self.lage == FINNS:
            return "%s: %s %s  [%s, %s: %s]" % (
                self.falt, _tal(self.varde), self.enhet,
                self.kalltyp or "kalla", self.lasning or ORDAGRANT_PAR,
                self.kalla.rad() if self.kalla else "")
        if self.lage == SAKNAS:
            return "%s: saknas (%s)" % (self.falt, self.skal)
        return ("%s: ENHET SAKNAS. Talet star ORDAGRANT som %r i %s och far "
                "visas sa, aldrig jamforas. %s"
                % (self.falt, self.ordagrant, self.kalltyp or "kallan", self.skal))

    def till_json(self) -> Dict[str, object]:
        d: Dict[str, object] = {"falt": self.falt, "lage": self.lage}
        if self.lage == FINNS:
            d["varde"] = self.varde
            d["enhet"] = self.enhet
            d["lasning"] = self.lasning or ORDAGRANT_PAR
            d["kalla"] = self.kalla.till_json() if self.kalla else None
        elif self.lage == ENHET_SAKNAS:
            d["ordagrant"] = self.ordagrant
        if self.skal:
            d["skal"] = self.skal
        if self.kalltyp:
            d["kalltyp"] = self.kalltyp
        return d


def _tal(v) -> str:
    return ("%g" % v) if isinstance(v, float) else str(v)


def finns(falt: str, uppgift: Uppgift,
          kalltyp: str = "tillverkarens datablad") -> Svar:
    return Svar(falt=falt, lage=FINNS, varde=uppgift.varde, enhet=uppgift.enhet,
                kalla=uppgift.kalla, kalltyp=kalltyp, lasning=uppgift.lasning)


def saknas(falt: str, skal: str) -> Svar:
    return Svar(falt=falt, lage=SAKNAS, skal=skal)


def enhet_saknas(falt: str, ordagrant: str, skal: str, kalltyp: str = "") -> Svar:
    return Svar(falt=falt, lage=ENHET_SAKNAS, ordagrant=str(ordagrant), skal=skal,
                kalltyp=kalltyp)


# ---------------------------------------------------------------------------
# Jamforelsen: den avstar hellre an gissar
# ---------------------------------------------------------------------------

# Databladets tal ar ett TAK for MODELLEN. Raden skrivs ut i varje domslut och
# star bara pa ett stalle i sak.
TAKREGELN = ("Databladets tal galler MODELLEN och ar ett TAK, aldrig ett "
             "driftvarde: verktygets och lastbararens vikt ar inte avraknade.")


@dataclass(frozen=True)
class Domslut:
    utfall: str
    skal: str
    behov: Optional[Svar] = None
    tak: Optional[Svar] = None

    @property
    def avstar(self) -> bool:
        return self.utfall == AVSTAR

    def text(self) -> str:
        if self.utfall == AVSTAR:
            return "AVSTAR: %s" % self.skal
        return "%s: %s %s" % (self.utfall.upper(), self.skal, TAKREGELN)


def rymmer(behov: Svar, tak: Svar) -> Domslut:
    """Ryms `behov` under `tak`? AVSTAR nar nagon sida inte ar jamforbar.

    Heter `rymmer` och inte `racker` med flit: den svarar pa om ett tal ligger
    under ett annat tal, inte pa om roboten klarar jobbet. Det senare beror pa
    verktyget, och verktyget star inte i databladet.
    """
    if not isinstance(behov, Svar) or not isinstance(tak, Svar):
        raise Tillverkarfel("rymmer() compares two Svar, not %r and %r"
                            % (type(behov).__name__, type(tak).__name__))
    for namn, s in (("behovet", behov), ("taket", tak)):
        if s.lage == SAKNAS:
            return Domslut(AVSTAR,
                           "%s (%s) saknas i alla kallor: %s. En grind som "
                           "domer pa ett falt den inte har mater ingenting."
                           % (namn, s.falt, s.skal), behov, tak)
        if s.lage == ENHET_SAKNAS:
            return Domslut(AVSTAR,
                           "%s (%s) har vardet %r men INGEN enhet. Ett tal utan "
                           "enhet som jamfors med ett tal med enhet ar ett fel "
                           "som ser ut som ett svar. %s"
                           % (namn, s.falt, s.ordagrant, s.skal), behov, tak)
    if faltdef(behov.falt).storhet != faltdef(tak.falt).storhet:
        return Domslut(AVSTAR,
                       "%s ar %s och %s ar %s - tva olika storheter gar inte "
                       "att jamfora." % (behov.falt, faltdef(behov.falt).storhet,
                                         tak.falt, faltdef(tak.falt).storhet),
                       behov, tak)
    b = behov.kanoniskt()
    t = tak.kanoniskt()
    kanonisk = faltdef(tak.falt).kanonisk
    if b <= t:
        return Domslut(RYMS, "%g %s ryms under %g %s." % (b, kanonisk, t, kanonisk),
                       behov, tak)
    return Domslut(RYMS_INTE,
                   "%g %s overskrider %g %s." % (b, kanonisk, t, kanonisk),
                   behov, tak)


# ---------------------------------------------------------------------------
# Korpusen: en post per MODELL
# ---------------------------------------------------------------------------

KORPUSKATALOG = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "data", "tillverkardatablad"))
CACHEKATALOG = os.path.join(KORPUSKATALOG, "cache")
CACHEINDEX = "_index.json"


@dataclass
class Modellblad:
    """Tillverkarens datablad for EN modell, med de falt vi kunnat belagga.

    `vc_namn` ar de EXAKTA namn den har modellen bar i det installerade
    biblioteket, utskrivna. Ingen likhetsmatchning: `IRB 1200-5/0.9` och
    `IRB 1200-7/0.7` ar tva robotar med olika nyttolast, och en matchning som
    later dem gliida ihop fyller den ena med den andras tal.

    `ej_belagda` ar lika viktigt som `uppgifter`: ett falt vi letade efter och
    inte hittade star dar med skalet, och blir `saknas` - inte tystnad.
    """

    modell: str
    tillverkare: str
    vc_namn: Tuple[str, ...] = ()
    bank_uri: str = ""
    uppgifter: Dict[str, Uppgift] = field(default_factory=dict)
    ej_belagda: Dict[str, str] = field(default_factory=dict)
    fil: str = ""

    def svar(self, falt: str) -> Svar:
        faltdef(falt)
        u = self.uppgifter.get(falt)
        if u is not None:
            return finns(falt, u)
        skal = self.ej_belagda.get(falt)
        if skal:
            return saknas(falt, "%s (%s): %s" % (self.modell, falt, skal))
        return saknas(falt, "%s: faltet %s ar inte belagt i korpusen (%s)"
                            % (self.modell, falt, self.fil or KORPUSKATALOG))

    def till_json(self) -> Dict[str, object]:
        return {
            "modell": self.modell,
            "tillverkare": self.tillverkare,
            "vc_namn": list(self.vc_namn),
            "bank_uri": self.bank_uri,
            "uppgifter": {k: v.till_json() for k, v in sorted(self.uppgifter.items())},
            "ej_belagda": dict(sorted(self.ej_belagda.items())),
        }


_TILLATNA_POSTFALT = {"modell", "tillverkare", "vc_namn", "bank_uri",
                      "uppgifter", "ej_belagda", "not"}


def _post(d: Dict[str, object], fil: str) -> Modellblad:
    if not isinstance(d, dict):
        raise Tillverkarfel("%s: a corpus entry must be an object" % fil)
    okanda = set(d) - _TILLATNA_POSTFALT
    if okanda:
        raise Tillverkarfel("%s: unknown fields in the corpus entry: %s"
                            % (fil, ", ".join(sorted(okanda))))
    modell = str(d.get("modell") or "").strip()
    if not modell:
        raise Tillverkarfel("%s: a corpus entry without a model name" % fil)
    tillverkare = str(d.get("tillverkare") or "").strip()
    if not tillverkare:
        raise Tillverkarfel("%s: %s is missing a manufacturer" % (fil, modell))
    uppgifter: Dict[str, Uppgift] = {}
    for falt, rå in sorted((d.get("uppgifter") or {}).items()):
        uppgifter[falt] = Uppgift.fran_json(falt, rå)
    ej = {}
    for falt, skal in sorted((d.get("ej_belagda") or {}).items()):
        faltdef(falt)
        if not str(skal).strip():
            raise Tillverkarfel("%s: %s: ej_belagda[%s] without a reason"
                                % (fil, modell, falt))
        if falt in uppgifter:
            raise Tillverkarfel(
                "%s: %s: %s appears as both documented and undocumented"
                % (fil, modell, falt))
        ej[falt] = str(skal)
    return Modellblad(modell=modell, tillverkare=tillverkare,
                      vc_namn=tuple(str(x) for x in (d.get("vc_namn") or ())),
                      bank_uri=str(d.get("bank_uri") or ""),
                      uppgifter=uppgifter, ej_belagda=ej,
                      fil=os.path.basename(fil))


class Korpus:
    """Alla modellblad, lasta ur `data/tillverkardatablad/*.json`.

    FAIL-CLOSED. En katalog som inte finns, en fil som inte gar att tolka eller
    en post som bryter mot enhetsgrinden ar ett UNDANTAG, aldrig en tom korpus.
    En kalla som inte gar att na far inte bli ett tyst tomt falt - da hade
    berikningen sett ut att ha kort och ingenting sagt.
    """

    def __init__(self, blad: Sequence[Modellblad], katalog: str = ""):
        self.blad: List[Modellblad] = list(blad)
        self.katalog = katalog
        self._per_vc: Dict[str, Modellblad] = {}
        self._per_modell: Dict[str, Modellblad] = {}
        self._per_bank: Dict[str, Modellblad] = {}
        for b in self.blad:
            nyckel = b.modell.strip().lower()
            if nyckel in self._per_modell:
                raise Tillverkarfel("the model %r appears twice in the corpus "
                                    "(%s and %s)" % (b.modell,
                                                     self._per_modell[nyckel].fil,
                                                     b.fil))
            self._per_modell[nyckel] = b
            if b.bank_uri:
                if b.bank_uri in self._per_bank:
                    raise Tillverkarfel("the bank URI %s appears twice" % b.bank_uri)
                self._per_bank[b.bank_uri] = b
            for n in b.vc_namn:
                k = n.strip().lower()
                if k in self._per_vc:
                    raise Tillverkarfel(
                        "library name %r is claimed by two models "
                        "(%s and %s). A name that points to two datasheets "
                        "fills one with the other's numbers."
                        % (n, self._per_vc[k].modell, b.modell))
                self._per_vc[k] = b

    # -- uppslag; ALLA ar exakta ------------------------------------------
    def for_modell(self, namn: str) -> Optional[Modellblad]:
        return self._per_modell.get((namn or "").strip().lower())

    def for_vc_namn(self, namn: str) -> Optional[Modellblad]:
        """Uppslag pa bibliotekets EXAKTA namn. Ingen likhet, ingen granne."""
        return self._per_vc.get((namn or "").strip().lower())

    def for_bank_uri(self, uri: str) -> Optional[Modellblad]:
        return self._per_bank.get((uri or "").strip())

    def __len__(self) -> int:
        return len(self.blad)

    @staticmethod
    def las(katalog: Optional[str] = None) -> "Korpus":
        kat = katalog or KORPUSKATALOG
        if not os.path.isdir(kat):
            raise Tillverkarfel(
                "no corpus directory at %s. A missing source must not become an "
                "empty corpus - that would silently turn every field into `saknas` "
                "without anyone noticing that the source was gone." % kat)
        blad: List[Modellblad] = []
        filer = sorted(f for f in os.listdir(kat)
                       if f.endswith(".json") and not f.startswith("_"))
        if not filer:
            raise Tillverkarfel("the corpus directory %s is empty" % kat)
        for f in filer:
            hel = os.path.join(kat, f)
            try:
                with open(hel, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError) as fel:
                raise Tillverkarfel("%s cannot be read: %s" % (hel, fel))
            poster = data.get("poster") if isinstance(data, dict) else data
            if not isinstance(poster, list):
                raise Tillverkarfel("%s: the file has no `poster` list" % hel)
            for p in poster:
                blad.append(_post(p, hel))
        return Korpus(blad, kat)


# ---------------------------------------------------------------------------
# Berikningen: VC:s tva kallor plus den tredje
# ---------------------------------------------------------------------------

# Skalstrangar som star bara pa ett stalle.
SKAL_KATALOGFALT = (
    "model.xml deklarerar TALET och ingenting mer - filen skriver varken mm "
    "eller kg. Enheten kan bara komma ur tillverkarens datablad.")
SKAL_NOLLA = (
    "Vardet ar 0 UTAN enhet. En nolla utan enhet ar inte en nyttolast pa noll "
    "kilo - det ar ett ofyllt falt, och skrivs den ut som en storhet har vi "
    "tillverkat ett faktum.")


def _samma_tal(ordagrant: str, varde) -> bool:
    """Ar modellens omarkta tal samma tal som tillverkarens?

    Bara en STRANGjamforelse pa talet, aldrig en enhetsomvandling: modellens
    tal saknar enhet, och att rakna om ett tal vars enhet man inte vet ar just
    det fel `jamforbar` finns for att hindra. 12 mot 12,5 ar olika. 2500 mot
    2500 ar samma. 2,51 m mot 2500 gar INTE att avgora, och da sags de vara
    olika - att gissa att de ar lika vore att avgora motsagelsen tyst igen.
    """
    try:
        a = float(str(ordagrant).replace(",", "."))
    except (TypeError, ValueError):
        return False
    try:
        b = float(varde)
    except (TypeError, ValueError):
        return False
    return abs(a - b) < 1e-9


def _katalogsvar(falt: str, vckalla: str, ordagrant: str) -> Svar:
    skal = SKAL_KATALOGFALT
    if _ar_nolla(ordagrant):
        skal = SKAL_NOLLA + " " + SKAL_KATALOGFALT
    return enhet_saknas(falt, ordagrant, skal, kalltyp=vckalla)


def _ar_nolla(ordagrant: str) -> bool:
    try:
        return float(str(ordagrant).strip().replace(",", ".")) == 0.0
    except (TypeError, ValueError):
        return False


def berika(blad, korpus: Optional[Korpus], falt: Sequence[str] = ()) -> Dict[str, Svar]:
    """Tre kallor -> ett `Svar` per falt, i den ordning kallorna far svara.

    `blad` ar ett `komponentdatablad.Datablad`. Ordningen ar:

      1. tillverkarens datablad, uppslaget pa bibliotekets EXAKTA namn -> finns
      2. katalogfaltet i model.xml, ordagrant                  -> enhet_saknas
      3. ingendera                                             -> saknas

    Steg 2 kan aldrig ge `finns`, och det ar inte en brist i den har koden utan
    i filen: model.xml bar inget enhetsfalt. Samma sak galler component.rsc:s
    `Quantity` - den deklarerar en STORHET (Mass, Distance), inte en enhet, och
    "Mass" sager inte om talet ar gram eller kilo.
    """
    falten = tuple(falt) or tuple(sorted(FALT))
    kat = getattr(blad, "katalogfalt", {}) or {}
    namn = getattr(blad, "namn", "") or ""
    post = korpus.for_vc_namn(namn) if korpus is not None else None
    ut: Dict[str, Svar] = {}
    for f in falten:
        faltdef(f)
        vc_namn = None
        for kfalt, vart in KATALOGFALT.items():
            if vart == f and kat.get(kfalt) is not None:
                vc_namn = kfalt
                break
        if post is not None:
            s = post.svar(f)
            if s.lage == FINNS:
                # BADA kallorna har ett tal om samma falt. Modellens saknar
                # enhet (model.xml bar inget enhetsfalt), sa talen gar inte att
                # jamfora kanoniskt - men de gar att STALLA BREDVID varandra,
                # och det ar skillnaden mot att tiga.
                if vc_namn is not None:
                    modelltal = str(kat[vc_namn]).strip()
                    if modelltal and not _samma_tal(modelltal, s.varde):
                        s = replace(s, motsagelse=(
                            "model.xml (%s) sager %s utan enhet; tillverkarens "
                            "datablad sager %s %s. Talen ar inte samma, och "
                            "vilket som galler i en cell ar inte avgjort har"
                            % (vc_namn, modelltal, s.varde, s.enhet)))
                ut[f] = s
                continue
        for kfalt, vart in KATALOGFALT.items():
            if vart == f and kat.get(kfalt) is not None:
                vc_namn = kfalt
                break
        if vc_namn is not None:
            ut[f] = _katalogsvar(f, "model.xml (%s)" % vc_namn, str(kat[vc_namn]))
            continue
        if post is not None and f in post.ej_belagda:
            ut[f] = post.svar(f)
            continue
        ut[f] = saknas(
            f, "varken tillverkarens datablad (%s) eller model.xml bar %s for "
               "%r" % ("korpusen saknar modellen" if post is None
                       else "modellen %s finns men inte faltet" % post.modell,
                       f, namn or "komponenten"))
    return ut


def text(namn: str, svar: Dict[str, Svar]) -> str:
    r = ["BERIKNING: %s" % (namn or "okand komponent"), ""]
    for f in sorted(svar):
        r.append("  " + svar[f].text())
    r.append("")
    r.append(TAKREGELN)
    return "\n".join(r)


# ---------------------------------------------------------------------------
# Hamtningen: en URL en gang, cachad under sin sha256
# ---------------------------------------------------------------------------

ANVANDARAGENT = ("Mozilla/5.0 (X11; Linux x86_64) VC_Assist/M-107 "
                 "komponentdatablad")


def cacheindex(katalog: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    kat = katalog or CACHEKATALOG
    p = os.path.join(kat, CACHEINDEX)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def hamta(url: str, katalog: Optional[str] = None,
          om: bool = False) -> Tuple[Dict[str, str], bytes]:
    """Hamta EN url en gang och cacha ravyten under sin sha256.

    FAIL-CLOSED i bada riktningarna: en hamtning som inte ger HTTP 200 med en
    kropp KASTAR. Den skriver ingen post, och den lamnar inget tomt falt efter
    sig. En kalla som inte gar att na ska synas som ett fel, inte som ett falt
    som rakade bli `saknas`.

    Cachen ar inte en optimering utan en artighet: ett svep som hamtar samma
    sida tusen ganger ar ett fel mot nagon annans server.
    """
    kat = katalog or CACHEKATALOG
    os.makedirs(kat, exist_ok=True)
    ix = cacheindex(kat)
    if url in ix and not om:
        p = os.path.join(kat, ix[url]["fil"])
        if os.path.exists(p):
            with open(p, "rb") as f:
                return ix[url], f.read()
    r = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "60", "-A", ANVANDARAGENT,
         "-w", "\n@@KOD:%{http_code}", url],
        capture_output=True)
    if r.returncode != 0:
        raise Tillverkarfel("fetching %s failed (curl %d): %s"
                            % (url, r.returncode, r.stderr.decode()[:300]))
    kropp = r.stdout
    m = re.search(rb"\n@@KOD:(\d+)$", kropp)
    kod = int(m.group(1)) if m else 0
    kropp = kropp[:m.start()] if m else kropp
    if kod != 200 or not kropp:
        raise Tillverkarfel(
            "%s responded HTTP %s with %d bytes. A source that cannot be "
            "reached must not become a silent empty field." % (url, kod, len(kropp)))
    s = hashlib.sha256(kropp).hexdigest()
    fil = s + (".pdf" if kropp[:4] == b"%PDF" else ".html")
    with open(os.path.join(kat, fil), "wb") as f:
        f.write(kropp)
    post = {"url": url, "sha256": s, "fil": fil, "byte": len(kropp),
            "hamtad": datetime.date.today().isoformat()}
    ix[url] = post
    with open(os.path.join(kat, CACHEINDEX), "w", encoding="utf-8") as f:
        json.dump(ix, f, indent=1, sort_keys=True, ensure_ascii=False)
    return post, kropp


def dokumenttext(kropp: bytes, fil: str, katalog: Optional[str] = None) -> str:
    """Ravyten -> text. PDF via pdftotext, HTML genom att strippa taggarna."""
    if fil.endswith(".pdf"):
        p = os.path.join(katalog or CACHEKATALOG, fil)
        r = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True)
        if r.returncode != 0:
            raise Tillverkarfel("pdftotext failed on %s: %s"
                                % (fil, r.stderr.decode()[:200]))
        return r.stdout.decode("utf-8", "replace")
    import html as _html
    t = kropp.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = re.sub(r"(?s)<[^>]+>", "\n", t)
    return _html.unescape(t)


# ---------------------------------------------------------------------------
# Korpusgrinden: tre lager, och bara det tredje behover cachen
# ---------------------------------------------------------------------------

def verifiera(korpus: Korpus, katalog: Optional[str] = None,
              kraev_cache: bool = False) -> List[str]:
    """Kontrollera varje uppgift mot sin egen kalla. Ger en lista med fel.

    Tre lager, i den ordning de blir dyrare:

      1. talet och enheten star bredvid varandra i citatet   (konstruktorn)
      2. citatet star i utdraget                             (konstruktorn)
      3. utdraget star i det CACHADE dokumentet, och dokumentets sha256
         stammer                                             (har)

    Lager 3 kraver cachen. `kraev_cache=False` rapporterar ett saknat dokument
    som en NOT i listan bara nar `kraev_cache=True` - annars hoppas det over,
    for cachen ar med flit inte i repot (femton PDF:er pa nara 15 MB).
    """
    kat = katalog or CACHEKATALOG
    ix = cacheindex(kat)
    per_sha = {v["sha256"]: v for v in ix.values()}
    fel: List[str] = []
    text_cache: Dict[str, str] = {}
    for b in korpus.blad:
        for falt, u in sorted(b.uppgifter.items()):
            k = u.kalla
            post = per_sha.get(k.sha256)
            if post is None:
                if kraev_cache:
                    fel.append("%s/%s: dokumentet %s... finns inte i cachen %s"
                               % (b.modell, falt, k.sha256[:12], kat))
                continue
            p = os.path.join(kat, post["fil"])
            if not os.path.exists(p):
                if kraev_cache:
                    fel.append("%s/%s: cachefilen %s saknas" % (b.modell, falt, p))
                continue
            with open(p, "rb") as f:
                rå = f.read()
            verklig = hashlib.sha256(rå).hexdigest()
            if verklig != k.sha256:
                fel.append("%s/%s: cachefilen %s har sha256 %s, korpusen sager %s"
                           % (b.modell, falt, post["fil"], verklig[:12],
                              k.sha256[:12]))
                continue
            if post["fil"] not in text_cache:
                text_cache[post["fil"]] = normalisera(
                    dokumenttext(rå, post["fil"], kat))
            if normalisera(k.utdrag or k.citat) not in text_cache[post["fil"]]:
                fel.append('%s/%s: citatet star INTE i dokumentet %s: %r'
                           % (b.modell, falt, k.url, normalisera(k.citat)[:120]))
    return fel


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    import argparse
    import sys
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("kommando", choices=("hamta", "visa", "verifiera", "lista"))
    p.add_argument("argument", nargs="*")
    p.add_argument("--monster", default="", help="grep i den hamtade texten")
    p.add_argument("--korpus", default=None)
    p.add_argument("--cache", default=None)
    a = p.parse_args(argv)

    if a.kommando == "hamta":
        for url in a.argument:
            post, kropp = hamta(url, a.cache)
            print("# %s\n#   sha256 %s  %d bytes  fetched %s"
                  % (post["url"], post["sha256"], post["byte"], post["hamtad"]))
            t = dokumenttext(kropp, post["fil"], a.cache)
            if a.monster:
                for i, rad in enumerate(t.splitlines()):
                    if re.search(a.monster, rad, re.I):
                        print("%6d | %s" % (i, rad.strip()[:220]))
            else:
                print(t)
        return 0

    korpus = Korpus.las(a.korpus)
    if a.kommando == "lista":
        for b in korpus.blad:
            print("%-30s %-20s vc_namn=%s bank=%s"
                  % (b.modell, b.tillverkare, list(b.vc_namn), b.bank_uri or "-"))
        print("%d models" % len(korpus))
        return 0
    if a.kommando == "verifiera":
        fel = verifiera(korpus, a.cache, kraev_cache=("--hard" in a.argument))
        for f in fel:
            print("FEL " + f)
        print("%d models, %d errors" % (len(korpus), len(fel)))
        return 1 if fel else 0
    # visa
    for namn in a.argument:
        b = korpus.for_modell(namn) or korpus.for_vc_namn(namn)
        if b is None:
            print("%s: missing from the corpus" % namn)
            continue
        print("MODEL: %s (%s)" % (b.modell, b.tillverkare))
        for f in sorted(FALT):
            print("  " + b.svar(f).text())
        print("  " + TAKREGELN)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
