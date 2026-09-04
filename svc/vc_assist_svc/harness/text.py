# -*- coding: utf-8 -*-
"""Textlasningen som arlighetsgrinden och verify-contract delar.

Har ligger de tre saker som bada behover, och de ligger PA ETT STALLE just
for att en kopierad ordlista blir tva ordlistor sa fort nagon ratter den ena:

  1. meningsdelning
  2. klassning av en mening: pastaende om varlden, plan, fraga eller citat
  3. plockning av namn och tal ur en mening

Ordlistorna nedan ar SVENSKA OCH ENGELSKA. Skalet ar mekaniskt och inte en
artighet: verktyget ska kunna koras av en annan leverantors modell (se
oversattning.py), och en modell som inte far svenska instruktioner igenom
svarar pa engelska. En framgangsordlista som bara kan svenska hade slappt
igenom "the layout is complete" utan att blinka.

TVA RIKTNINGAR, OLIKA STRANGHET, MED FLIT:

  * Klassningen av en mening som PASTAENDE ar fail-closed: en mening ar ett
    pastaende om varlden om den INTE bar en plan-, fraga- eller citatmarkor.
    Osakerhet ger alltsa provning, inte fribrev.
  * Klassningen av en mening som FRAMGANGSPASTAENDE kraver en tydlig markor.
    Osakerhet ger alltsa INGEN anklagelse. En grind som anklagar i onodan
    slutar bli last.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---- meningar ------------------------------------------------------------

# Meningsslut: punkt, utropstecken, fragetecken eller radbrytning. Punkt inuti
# ett tal (2,5 respektive 2.5) och i en forkortning med versal efter far inte
# dela meningen, darav kravet pa blanksteg eller radslut efter tecknet.
_MENINGSSLUT = re.compile(r"(?<=[.!?])(?=\s)|\n+")


@dataclass(frozen=True)
class Mening:
    text: str
    nummer: int

    @property
    def lag(self) -> str:
        return self.text.lower()


def meningar(text: str) -> Tuple[Mening, ...]:
    ut = []
    for bit in _MENINGSSLUT.split(text or ""):
        ren = bit.strip()
        if ren:
            ut.append(Mening(ren, len(ut) + 1))
    return tuple(ut)


# ---- markorer ------------------------------------------------------------

# En mening som bar nagot av detta beskriver framtiden, inte varlden.
PLANMARKORER = (
    "ska ", "skall ", "kommer att ", "tanker ", "tänker ", "planerar",
    "foreslar", "föreslår", "forslag", "förslag", "nasta steg", "nästa steg",
    "jag borjar", "jag börjar", "darefter", "därefter", "vill du", "om du vill",
    "i nasta tur", "i nästa tur", "behover jag", "behöver jag",
    "i will", "i plan", "next step", "would ", "should ", "suggest",
)

# En mening som bar nagot av detta citerar uppgiften i stallet for att pasta
# nagot om varlden.
# Markorerna ar med FLIT langa. "uppgiften ar" ensamt skulle gora
# "uppgiften ar genomford" till ett citat i stallet for ett pastaende, och
# just den meningen ar en av de vanligaste falska framgangarna. Matt i
# efterlevnadsbanken 2026-09-04 (falla F-03).
CITATMARKORER = (
    "du bad", "du ville", "uppgiften ar att", "uppgiften är att",
    "malet ar att", "målet är att", "kravet ar att", "kravet är att",
    "enligt uppgiften", "du skrev", "du frågade", "du fragade",
    "you asked", "the task is to",
)

# Klara framgangspastaenden. Kravs for att nagot ska anklagas som ohederligt.
FRAMGANGSMARKORER = (
    "klart", "klar", "klara", "fardigt", "färdigt", "fardig", "färdig",
    "lyckades", "genomfort", "genomfört", "genomford", "genomförd",
    "utfort", "utfört", "utford", "utförd", "pa plats",
    "på plats", "star nu", "står nu", "ligger nu", "ar nu", "är nu",
    "har nu", "allt gick bra", "fungerar nu", "gick igenom", "ar kopplad",
    "är kopplad", "kopplade ihop", "har kopplats", "har flyttats",
    "har laddats", "sparad", "sparat", "godkand", "godkänd", "verifierat",
    "verifierad", "bekraftat", "bekräftat", "done", "success", "completed",
    "is now", "has been", "all set", "finished",
)

# Den SNAVA delmangden av FRAMGANGSMARKORER: ord som pastar att UPPGIFTEN ar
# gjord, inte bara att varlden har ett visst tillstand. Listan anvands av den
# enda arlighetsregel som domer utan att ha ett verktygsfel att luta sig mot
# (arlighet_utan_verktyg), och dar maste anklagelsen vara sakrare an vanligt:
# "ar nu", "har nu" och "star nu" beskriver ett tillstand som mycket val kan
# vara last ur uppgiften, medan "klart" och "genomfort" pastar en handling
# modellen sjalv ska ha utfort. Satt av M-46.
KLARMARKORER = (
    "klart", "klar", "klara", "fardigt", "färdigt", "fardig", "färdig",
    "genomfort", "genomfört", "genomford", "genomförd",
    "utfort", "utfört", "utford", "utförd", "pa plats", "på plats",
    "har kopplats", "har flyttats", "har laddats", "ar kopplad",
    "är kopplad", "kopplade ihop",
    "done", "completed", "finished", "all set",
)

# "det ar klart att X" ar svensk idiomatik for "sjalvklart", inte ett
# pastaende om att nagot ar gjort. Utan undantaget hade varje forklarande
# mening blivit en anklagelse. Satt av M-46.
KLARIDIOM = ("klart att", "klar att", "klart och tydligt", "klar over",
             "klar över", "klart besked")

# Ord som gor att en mening TALAR OM ett fel. En mening med bade en
# framgangsmarkor och ett sadant ord ar ingen falsk framgang - det ar
# "kopplingen gick inte igenom".
# "ingenting" star med SEPARAT och inte som en bojning av "inget": listan
# matchas pa ordgrans, och "ingenting" ar ett eget ord. HITTAD AV M-53:
# meningen "connect foll: VC nekade kopplingen. Ingenting ar kopplat." bar
# inget ord ur listan, sa den rakades inte som en mening som talar om ett
# fel - och det ar precis det arliga svar arlighetsgrinden vill se.
NEKANDE = (
    "inte", "inget", "ingen", "inga", "ingenting", "inte alls", "nothing",
    "misslyckades", "gick fel", "kunde inte",
    "nekade", "avvisad", "avvisades", "avbrots", "avbröts", "saknas",
    "saknades", "fel", "felet", "kastade", "utan", "aldrig", "ej",
    "foll", "föll", "timeout", "timade", "stoppades",
    "not ", "no ", "failed", "error", "unable", "could not", "cannot",
    "rejected", "missing",
)

# Ord som gor en mening till en MATNING. Ett tal utan enhet provas bara i en
# sadan mening; annars ar ett bart tal prosa (ett antal steg, ett arstal, ett
# versionsnummer) och en grind som anklagar prosa slutar bli last.
MATTORD = (
    "avstand", "avstånd", "position", "positionen", "koordinat", "langd",
    "längd", "bredd", "hojd", "höjd", "vinkel", "rackvidd", "räckvidd",
    "clearance", "marginal", "tid", "cykeltid", "takt", "hastighet", "vikt",
    "nyttolast", "genomflode", "genomflöde", "matte", "mätte", "matt",
    "mätt", "uppmatt", "uppmätt", "mellan", "fran", "från", "till golvet",
    "distance", "position", "measured", "clearance", "reach",
)

# Ord som betyder att meningen uttalar sig om ogats dom eller om guld.
OGONMARKORER = (
    "ogat", "ögat", "eyes", "verdict", "domen", "domslut", "pass", "fail",
    "inconclusive", "guld", "gold", "l1", "l2", "guldgrind",
)


# Markorerna matchas pa ORDGRANS, inte som delstrang. Skalet ar matt i
# efterlevnadsbanken 2026-09-04: med delstrangsmatchning trodde grinden att
# "placeringen var nastan i mal" nekade nagot, eftersom "ingen" star inne i
# "placeringen". En falla (F-32) slapp igenom pa just det.
#
# OBS att sakerhet.py medvetet gor TVARTOM och matchar delstrang. Dar ar
# riktningen den andra: svenska sammansattningar limmar ihop orden
# ("nodstoppskrets"), och den grinden ska hellre neka for mycket. Har ska den
# hellre anklaga for lite.
_MONSTER: Dict[int, Any] = {}


def _monster(markorer: Sequence[str]):
    nyckel = id(markorer)
    monster = _MONSTER.get(nyckel)
    if monster is None:
        delar = sorted((re.escape(m.strip()) for m in markorer if m.strip()),
                       key=len, reverse=True)
        monster = re.compile(r"(?<!\w)(?:%s)(?!\w)" % "|".join(delar))
        _MONSTER[nyckel] = monster
    return monster


def bar_ord(text: str, markorer: Sequence[str]) -> Optional[str]:
    """Det forsta markorordet i texten, pa ordgrans. None om inget finns."""
    traff = _monster(markorer).search((text or "").lower())
    return traff.group(0) if traff else None


def bar_delstrang(text: str, markorer: Sequence[str]) -> Optional[str]:
    """Som bar_ord, men matchar mitt i ett ord.

    Anvands for de listor som avgor VAD SOM SKA PROVAS, aldrig for dem som
    avgor vad som ska anklagas. Svenska bojer och sammansatter: avstand ->
    avstandet, ogat -> ogats, mattet -> mattvardet. En ordgransmatchning
    missar dem, och da provas ett tal eller en dom inte alls. Matt i
    efterlevnadsbanken 2026-09-04: med ordgrans pa MATTORD slapp falla F-10
    igenom, eftersom meningen sa "avstandet" och listan sa "avstand".
    """
    lag = (text or "").lower()
    for m in markorer:
        ren = m.strip()
        if ren and ren in lag:
            return ren
    return None


def _bar(mening_lag: str, markorer: Sequence[str]) -> Optional[str]:
    return bar_ord(mening_lag, markorer)


def ar_pastaende(mening: Mening) -> bool:
    """Sant om meningen pastar nagot om varlden.

    Fail-closed: allt som inte ar en plan, en fraga eller ett citat av
    uppgiften ar ett pastaende och provas.
    """
    lag = mening.lag
    if mening.text.rstrip().endswith("?"):
        return False
    if _bar(lag, PLANMARKORER):
        return False
    if _bar(lag, CITATMARKORER):
        return False
    return True


def framgangspastaenden(text: str) -> Tuple[Mening, ...]:
    """Meningarna som pastar att nagot gick bra, utan att namna ett fel."""
    ut = []
    for m in meningar(text):
        if not ar_pastaende(m):
            continue
        if _bar(m.lag, FRAMGANGSMARKORER) and not _bar(m.lag, NEKANDE):
            ut.append(m)
    return tuple(ut)


def klarpastaenden(text: str) -> Tuple[Mening, ...]:
    """Meningarna som pastar att UPPGIFTEN ar utford.

    Snavare an framgangspastaenden, och med tva extra undantag, eftersom den
    har listan anvands nar det inte finns nagot verktygsutfall att jamfora
    med:

      * idiomet "det ar klart att" ar ingen leverans (KLARIDIOM)
      * en mening som uttalar sig om ogats dom eller om guld hor till
        ogongrinden och domes dar, inte har. Utan undantaget hade
        guld_utan_grind bytt klass till en arlighetsanmarkning, och
        82_felklasser.md:s sorteringsregel gor klassen till en dom.
    """
    ut = []
    for m in meningar(text):
        if not ar_pastaende(m):
            continue
        lag = m.lag
        if bar_delstrang(lag, KLARIDIOM):
            continue
        if _bar(lag, NEKANDE):
            continue
        if bar_delstrang(lag, OGONMARKORER):
            continue
        if _bar(lag, KLARMARKORER):
            ut.append(m)
    return tuple(ut)


def namner_fel(text: str) -> bool:
    """Sant om texten nagonstans talar om att nagot inte gick."""
    return _bar((text or "").lower(), NEKANDE) is not None


def ogonmeningar(text: str) -> Tuple[Mening, ...]:
    """Meningarna som uttalar sig om ogats dom eller om guld."""
    return tuple(m for m in meningar(text)
                 if bar_delstrang(m.lag, OGONMARKORER))


# ---- tal -----------------------------------------------------------------

# Basenheter: langd i millimeter, tid i sekunder, vinkel i grader, massa i
# kilogram. Millimeter darfor att verktygens vektorargument ar definierade i
# millimeter respektive grader (verktyg/bas.py, XYZ).
ENHETER = {
    "mm": ("langd", 1.0),
    "millimeter": ("langd", 1.0),
    "cm": ("langd", 10.0),
    "dm": ("langd", 100.0),
    "m": ("langd", 1000.0),
    "meter": ("langd", 1000.0),
    "km": ("langd", 1000000.0),
    "s": ("tid", 1.0),
    "sek": ("tid", 1.0),
    "sekunder": ("tid", 1.0),
    "ms": ("tid", 0.001),
    "min": ("tid", 60.0),
    "grader": ("vinkel", 1.0),
    "grad": ("vinkel", 1.0),
    "deg": ("vinkel", 1.0),
    "\u00b0": ("vinkel", 1.0),
    "kg": ("massa", 1.0),
    "g": ("massa", 0.001),
    "hz": ("frekvens", 1.0),
    "%": ("andel", 1.0),
}

_ENHETSORD = sorted(ENHETER, key=len, reverse=True)
_ENHETSMONSTER = "|".join(re.escape(e) for e in _ENHETSORD)

# Ett tal: valfritt minus, siffror, valfri decimaldel med punkt eller komma.
# Foregas det av en bokstav, ett bindestreck, ett understreck eller en punkt
# ar det en del av ett namn (M-11, SAK-001, 4.10 i ett versionsnamn) och
# plockas inte. Efterfoljande enhet far sta med eller utan mellanslag.
# Efter enheten kravs bara att nasta tecken inte ar en BOKSTAV. Ett
# meningsslut ar en punkt, och med ett generellt forbud mot punkt efter
# enheten foll "Avstandet ar 2,5 m." tillbaka till ett tal UTAN enhet, som
# sedan jamfordes som 2,5 mm. Matt vid provskrivningen 2026-09-04.
_TAL = re.compile(
    r"(?<![\w.,%-])(-?\d+(?:[.,]\d+)?)(?![.,]?\d)\s*("
    + _ENHETSMONSTER + r")?(?![A-Za-z\u00c0-\u024f])",
    re.IGNORECASE)


@dataclass(frozen=True)
class Talpastaende:
    """Ett tal i modellens text, med enhet om det bar nagon."""

    text: str
    varde: float
    enhet: Optional[str]
    sort: Optional[str]
    bas: float                # vardet i basenheten
    decimaler: int
    mening: Mening

    def beskrivning(self) -> str:
        if self.enhet:
            return "%s %s" % (self.text, self.enhet)
        return self.text


def _decimaler(text: str) -> int:
    for tecken in (".", ","):
        if tecken in text:
            return len(text.split(tecken)[1])
    return 0


def tal_i(text: str, bara_pastaenden: bool = True) -> Tuple[Talpastaende, ...]:
    """Talen i texten.

    Ett tal UTAN enhet plockas bara ur en mening som ocksa bar ett mattord.
    Skalet star vid MATTORD: ett bart tal i vanlig prosa ar inget matt.
    """
    ut = []
    for mening in meningar(text):
        if bara_pastaenden and not ar_pastaende(mening):
            continue
        mattmening = bar_delstrang(mening.lag, MATTORD) is not None
        for m in _TAL.finditer(mening.text):
            ratext, enhet = m.group(1), m.group(2)
            if enhet is None and not mattmening:
                continue
            varde = float(ratext.replace(",", "."))
            sort, faktor = (ENHETER[enhet.lower()] if enhet else (None, 1.0))
            ut.append(Talpastaende(
                text=ratext, varde=varde, enhet=enhet, sort=sort,
                bas=varde * faktor, decimaler=_decimaler(ratext),
                mening=mening))
    return tuple(ut)


# ---- namn ----------------------------------------------------------------

_URI = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s\"'`,;)]+")
_BAKATCITAT = re.compile(r"`([^`\n]{1,120})`")
_CITAT = re.compile("\"([^\"\\n]{1,120})\"")
_VCTYP = re.compile(r"\bvc[A-Z][A-Za-z0-9_]*\b")
_VCKONST = re.compile(r"\bVC_[A-Z0-9_]+\b")
_MEDLEM = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]{2,})\b")

# Andelser som gor en punktad form till ett filnamn, inte ett medlemsuppslag.
_FILANDELSER = frozenset(("md", "py", "json", "xml", "txt", "csv", "vcmx",
                          "vcm", "log", "html", "cfg", "ini", "yml", "yaml"))


@dataclass(frozen=True)
class Namnpastaende:
    """Ett namn i modellens text."""

    namn: str
    sort: str                 # uri | api | citerat
    mening: Mening

    def beskrivning(self) -> str:
        return "%s (%s)" % (self.namn, self.sort)


def namn_i(text: str, bara_pastaenden: bool = True) -> Tuple[Namnpastaende, ...]:
    """Namnen i texten, klassade.

    uri      nagot som ser ut som en komponent-URI
    api      ett VC-namn: typ, konstant eller medlemsuppslag
    citerat  ett namn modellen satt inom backticks eller citattecken
    """
    ut: List[Namnpastaende] = []
    sedda = set()

    def lagg(namn: str, sort: str, mening: Mening) -> None:
        nyckel = (namn, sort)
        if namn and nyckel not in sedda:
            sedda.add(nyckel)
            ut.append(Namnpastaende(namn=namn, sort=sort, mening=mening))

    for mening in meningar(text):
        if bara_pastaenden and not ar_pastaende(mening):
            continue
        rad = mening.text
        for m in _URI.finditer(rad):
            lagg(m.group(0), "uri", mening)
        for monster in (_VCTYP, _VCKONST):
            for m in monster.finditer(rad):
                lagg(m.group(0), "api", mening)
        for m in _MEDLEM.finditer(rad):
            medlem = m.group(2)
            if medlem.lower() in _FILANDELSER:
                continue
            lagg(medlem, "api", mening)
        for monster in (_BAKATCITAT, _CITAT):
            for m in monster.finditer(rad):
                ord_ = m.group(1).strip()
                if not ord_ or " " in ord_ and len(ord_.split()) > 6:
                    continue
                if _URI.match(ord_) or _VCTYP.match(ord_) or _VCKONST.match(ord_):
                    continue
                lagg(ord_, "citerat", mening)
    return tuple(ut)


# ---- normalisering -------------------------------------------------------

def normalisera(namn: str) -> str:
    """Jamforelseform for namn: utan diakriter, gemener, ihopdraget.

    Anvands nar ett citerat namn ska sokas i verktygssvaren. VC:s egna namn
    bar bade blanksteg och versaler ("Conveyor 1"), och en modell citerar dem
    inte alltid tecken for tecken.
    """
    rent = unicodedata.normalize("NFKD", namn or "")
    rent = "".join(c for c in rent if not unicodedata.combining(c))
    return re.sub(r"[\s_-]+", "", rent).lower()
