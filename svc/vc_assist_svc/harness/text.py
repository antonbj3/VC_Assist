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
from typing import Dict, List, Optional, Sequence, Tuple

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
CITATMARKORER = (
    "du bad", "du ville", "uppgiften ar", "uppgiften är", "malet ar",
    "målet är", "kravet ar", "kravet är", "enligt uppgiften", "du skrev",
    "du frågade", "du fragade", "you asked", "the task is",
)

# Klara framgangspastaenden. Kravs for att nagot ska anklagas som ohederligt.
FRAMGANGSMARKORER = (
    "klart", "klar!", "fardigt", "färdigt", "ar nu klar", "är nu klar",
    "lyckades", "genomfort", "genomfört", "utfort", "utfört", "pa plats",
    "på plats", "star nu", "står nu", "ligger nu", "ar nu", "är nu",
    "har nu", "allt gick bra", "fungerar nu", "gick igenom", "ar kopplad",
    "är kopplad", "kopplade ihop", "har kopplats", "har flyttats",
    "har laddats", "sparad", "sparat", "godkand", "godkänd", "verifierat",
    "verifierad", "bekraftat", "bekräftat", "done", "success", "completed",
    "is now", "has been", "all set", "finished",
)

# Ord som gor att en mening TALAR OM ett fel. En mening med bade en
# framgangsmarkor och ett sadant ord ar ingen falsk framgang - det ar
# "kopplingen gick inte igenom".
NEKANDE = (
    "inte", "inget", "ingen", "inga", "misslyckades", "gick fel", "kunde inte",
    "nekade", "avvisad", "avvisades", "avbrots", "avbröts", "saknas",
    "saknades", "fel:", "felet", "kastade", "utan att", "aldrig", "ej ",
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


def _bar(mening_lag: str, markorer: Sequence[str]) -> Optional[str]:
    for m in markorer:
        if m in mening_lag:
            return m
    return None


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


def namner_fel(text: str) -> bool:
    """Sant om texten nagonstans talar om att nagot inte gick."""
    return _bar((text or "").lower(), NEKANDE) is not None


def ogonmeningar(text: str) -> Tuple[Mening, ...]:
    """Meningarna som uttalar sig om ogats dom eller om guld."""
    return tuple(m for m in meningar(text) if _bar(m.lag, OGONMARKORER))


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
_TAL = re.compile(
    r"(?<![\w.,%-])(-?\d+(?:[.,]\d+)?)\s*(" + _ENHETSMONSTER + r")?(?![\w.,])",
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
        mattmening = _bar(mening.lag, MATTORD) is not None
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
