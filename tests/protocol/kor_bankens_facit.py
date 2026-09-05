# -*- coding: utf-8 -*-
"""Bankens facit, dömt post för post: har varje uppgift ett facit, och kommer
facit någon annanstans ifrån än koden som ska dömas?

VARFOR DEN FINNS
----------------
`docs/spec/85_bankkontraktet.md` §2 bär hela bänken: **facitkalla far aldrig
peka pa nagot i under_prov.** BENCH-4 stod grön i månader mot ett facit som
räknades fram av samma algoritm som dömdes. Talet var perfekt och mätte
ingenting.

Bankkontraktet mekaniserar den regeln för de 26 körningarna under
`tests/protocol/` (`svc/vc_assist_svc/bankkontrakt.py`). Den har aldrig gällt
bankens 63 uppgifter, och där ligger den största facitmängden i repot.

Den här körningen är regeln applicerad på uppgifterna. Sex frågor per uppgift:

1. **Har den ett spårfacit?** Utan ett går uppgiften inte att döma idag; den är
   en prompt och inte en bänkpost. Täckningen räknas och jämförs mot ett golv.
2. **Säger spårfacit VARIFRÅN facit kommer?** Ett bart `M-45` namnger en
   mätning av bankens täckning, inte källan till talen. Härkomsten måste
   namnge en källklass ur `KALLKLASSER` och den mätning som bär räkningen.
3. **Ligger källan utanför koden som döms?** Ett facit härlett ur
   `svc/vc_assist_svc/st/` eller `plc/` är tautologiskt: tolken som räknar
   fram facit är samma tolk som dömer mot det.
4. **Går varje citerad paragraf att slå upp?** Paragrafnumren jämförs mot
   tabellerna i `docs/matningar/M-106_bankens_facitkallor.md`, där de faktiskt
   slogs upp. Ett uppfunnet paragrafnummer ser ut precis som ett riktigt, och
   MÄTT 2026-09-05 stod två sådana i banken.
5. **Går signalkartan ihop?** Kärnutgångar som inte är utsignaler, scenarier
   som pekar på signaler som inte finns, kärnutgångar som spårfacit aldrig rör.
6. **Håller facit?** Referenslösningen ska uppfylla sitt eget facit och varje
   motbevis ska falla på de brister det namnger. Ett facit ingen lösning
   uppfyller fäller alla; ett facit inget motbevis faller på mäter ingenting.

TRASIGA FALL
------------
Sju fixturer körs sist och MASTE falla. En grind utan trasig fixtur är en
förhoppning som fått ett filnamn (regel S2, `docs/spec/96_ingen_skuld.md`).

Körs utan VC, utan OpenPLC och utan STruC++.

    python3 tests/protocol/kor_bankens_facit.py [--json ut.json] [--tyst]

beskriver: bank/uppgifter/*.json, bank/schema.py, bank/domare.py,
docs/spec/85_bankkontraktet.md
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", ".."))
for _p in (os.path.join(ROT, "bank"), os.path.join(ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import domare                                        # noqa: E402
import lasare                                        # noqa: E402
import schema                                        # noqa: E402

MATNINGAR = os.path.join(ROT, "docs", "matningar")

BANKPOST = {
    "pastar": (
        "Varje uppgift i banken bar ett facit vars harkomst namnger en kalla "
        "utanfor repots egen kod, och varje sparfacit uppfylls av sin referens "
        "och falls av vart och ett av sina motbevis pa de brister de namnger."),
    "under_prov": ["bank/uppgifter", "bank/schema.py", "bank/domare.py",
                   "svc/vc_assist_svc/st/tolk.py"],
    "facit": (
        "Noll brister over banken: varje sparfacit namnger kallklass och "
        "matning, ingen harkomst pekar in i under_prov, varje karnutgang syns "
        "i sitt spar, referensen ar godkand och varje motbevis falls. "
        "Sparfacittackningen ligger pa eller over golvet i M-106."),
    "facitkalla": (
        "docs/spec/85_bankkontraktet.md §2 (facit hor utanfor koden som provas) "
        "och de standardparagrafer och rakningar som uppgifternas harkomst "
        "citerar; tackningsgolvet ar matt i M-106"),
    "facitkalla_filer": ["docs/spec/85_bankkontraktet.md",
                         "docs/matningar/M-106_bankens_facitkallor.md"],
    "trasiga_fall": [
        "en uppgift vars facit harletts ur svc/vc_assist_svc/st/ eller plc/",
        "ett antagande utan motiv",
        "ett tal med enhet i namnet men utan enhet i vardet",
        "ett facit som kallar sig STANDARD men bara namner standardnumret",
        "en paragraf utan utgivare, som inte gar att sla upp",
        "ett uppfunnet paragrafnummer som inte star i M-106",
        "en karnutgang som sparfacit aldrig ror",
    ],
    "kraver": ["inget"],
    "matningar": ["M-106", "M-45"],
}

# --------------------------------------------------------------- vokabular

# Kallklasserna ar 85_bankkontraktet.md §2:s lagliga facitkallor, i bankens
# ordforrad. Klassen skrivs forst i harkomsten sa den gar att lasa mekaniskt.
# En harkomst utan klass ar inte en kalla utan en hanvisning till att nagon en
# gang tankte pa saken.
KALLKLASSER = {
    "STANDARD": "en paragraf i en publicerad standard; paragrafen ska citeras, "
                "inte bara standardnumret",
    "RAKNAD": "geometri eller fysik raknad ur scenens egna matt; rakningen ska "
              "sta i harkomsten",
    "DATABLAD": "en tillverkares publicerade datablad for den namngivna "
                "komponenten",
    "SPAR": "ett inspelat I/O-spar fran en riktig anlaggning",
}

# En paragrafhanvisning har minst tva led: 9.2.5, 6.2.2.1, 4.1.4. Ett bart
# standardnummer (IEC 60204-1) sager inte VAD i standarden facit lutar sig mot,
# och det ar precis det slarv operatoren forbjod.
#
# Bada leden kravs: utgivaren OCH paragrafen. Ett dottal ensamt racker inte -
# "1.5/10/660" ar en betygsnotation och ingen paragraf - och ett utgivarnamn
# ensamt ar just det bara standardnummer regeln finns emot.
PARAGRAF = re.compile(r"\b\d+\.\d+(?:\.\d+)*\b")
UTGIVARE = re.compile(
    r"\b(?:IEC|ISO|EN|SS|ASTM|ANSI|ISA|VDI|VDE|DIN|GS1|EUROMAP|VDA|OMAC|UL|NFPA)\b")

# En rakning som inte visas gar inte att folja. Likhetstecknet ar det
# billigaste beviset pa att talet HARLETTS och inte valts.
RAKNING = re.compile(r"=")

# Sokvagar in i repots egen kod. En harkomst som namner nagon av dem har hamtat
# facit ur det som ska domas (BENCH-4).
EGEN_KOD = (
    "svc/vc_assist_svc/",
    "svc/",
    "bank/domare.py",
    "bank/schema.py",
    "ext/vc_addon/",
    "tests/",
    "plc/",
    "st/tolk.py",
)

# Enhetssymboler som FAKTISKT forekommer i bankens antaganden, plus de som en
# ny uppgift rimligen behover. Listan ar tight med flit: en generos lista
# hittar en enhet i vilken text som helst och grinden slutar mata nagot.
_ENHETER = (
    "mm/s", "m/s", "m/min", "mm/min", "l/min", "ml/min", "cm3/min", "mm3/s",
    "varv/min", "grader/s",
    "mm2", "mm3", "cm3", "m2",
    "mm", "cm", "dm", "km", "µm",
    "kg", "mg", "kN", "Nm", "kPa", "MPa", "mbar", "kW", "kVA", "kJ",
    "ms", "min", "rpm", "bar", "Pa", "Hz", "°C", "%",
    "g", "N", "s", "h", "A", "V", "W", "l", "t", "m",
)
ENHET = re.compile(
    r"(?<![A-Za-zÅÄÖåäö0-9])(?:%s)(?![A-Za-zÅÄÖåäö0-9])"
    % "|".join(re.escape(e) for e in _ENHETER))

# Ett tal med ett ord intill sig ar ocksa en storhet: "8 kollin", "12 platser",
# "60 per minut", "grind 2". Det ar inte en SI-enhet men det ar en raknad sak,
# och den raknade saken star i ordet. Ordet far sta pa bada sidor om talet:
# MATT 2026-09-05 over bankens 139 antaganden foll tre varden av formen
# "grind 2" ut nar bara efterstallda ord raknades, och en grind som fyrar pa
# ratt sak av fel skal mater inte det den sager.
TAL_MED_ORD = re.compile(
    r"\d[\d\s.,]*\s*[A-Za-zÅÄÖåäö]{2,}|[A-Za-zÅÄÖåäö]{2,}\s*\d")
HAR_SIFFRA = re.compile(r"\d")

_MNUMMER = re.compile(r"\bM-\d+\b")

# En uppgift vars scenarier sager "larma" men vars signalkarta saknar
# SYS_ALARM ber om nagot den inte gett signalen till. MATT i M-106: 30 av
# bankens uppgifter gor det, och tva till har SYS_ALARM men ingen SYS_RESET
# att kvittera med. Alla 32 ar aldre an M-106; ingen av de tolv nya uppgifterna
# ar bland dem.
#
# Talen ar SKULDTAK och far bara ga at ett hall. En ny uppgift som lagger till
# sig i listan faller korningen; blir listan kortare ska talet skrivas ned har,
# annars slutar sparren mata sin egen storhet.
LARMSKULD = 30                  # Matt i M-106.
KVITTENSSKULD = 2               # Matt i M-106.
SAGER_LARM = re.compile(r"\blarm", re.I)


# --------------------------------------------- de verifierade paragraferna

# Uppslagningen av en paragraf gors INTE mot en lista i den har filen. Den gors
# mot tabellerna i M-106, som ar den matning dar paragraferna faktiskt slogs upp
# mot standardorganens innehallsforteckningar. En kopia har hade kunnat drifta
# fran matningen utan att nagon markte det - samma skal som bank/schema.py laser
# felklasserna ur specen i stallet for att bara en kopia.
#
# VARFOR KONTROLLEN FINNS: MATT 2026-09-05 skrev en agent "IEC 60204-1:2016
# 9.2.4" i tva uppgifters standardfalt. Paragrafen finns inte; ratt nummer ar
# 9.2.3.4.2. Lintern sag den inte, och grinden sag den inte heller sa lange den
# bara kravde att NAGOT paragrafnummer stod dar. Ett uppfunnet paragrafnummer
# ser exakt ut som ett riktigt.
M106 = os.path.join(MATNINGAR, "M-106_bankens_facitkallor.md")

# Utgivarbeteckningen i en tabellcell: "IEC 60204-1:2016", "ISO/IEC 15416:2016",
# "ANSI/ISA-TR88.00.02-2022", "EUROMAP 67 v1.11 (2015)", "GS1 General
# Specifications R26.0". Namnet normaliseras till utgivare + nummer, utan ar.
_BETECKNING = re.compile(
    r"^\**\s*(IEC/?T?S?\s*\d+(?:-\d+)*"
    r"|ISO/IEC\s*\d+"
    r"|ISO\s*\d+(?:-\d+)*"
    r"|ASTM\s*[A-Z]\d+"
    r"|(?:ANSI/)?ISA-TR[\d.]+"
    r"|VDA\s*\d+"
    r"|EUROMAP\s*\d+"
    r"|VDI/VDE\s*\d+"
    r"|GS1"
    r"|TIGER)")


def _normalisera(namn):
    return re.sub(r"\s+", " ", namn).strip().replace("ANSI/ISA-TR", "ISA-TR")


def las_verifierade_paragrafer(sokvag=M106):
    """{(beteckning, paragraf)} ur M-106:s tabeller.

    Varje tabellrad vars forsta cell ar en standardbeteckning bidrar med alla
    paragrafliknande tal i sina tva forsta kolumner efter beteckningen. Bade
    paragraftabellen och tabellen over utgavebeteckningar lases, sa ett
    versionsnummer inte fells som en uppfunnen paragraf.
    """
    ut = set()
    if not os.path.exists(sokvag):
        return ut
    with open(sokvag, "r", encoding="utf-8") as f:
        for rad in f:
            if not rad.lstrip().startswith("|"):
                continue
            celler = [c.strip() for c in rad.strip().strip("|").split("|")]
            if len(celler) < 2:
                continue
            m = _BETECKNING.match(celler[0])
            if not m:
                continue
            namn = _normalisera(m.group(1))
            for cell in celler[1:3]:
                for p in PARAGRAF.findall(cell):
                    ut.add((namn, p))
    return ut


def _citat(text):
    """(beteckning, paragraf) ur en fritext. Paragrafen knyts till narmaste
    foregaende beteckning, sa "IEC 60204-1:2016 9.2.3.7" blir ett par."""
    par = []
    senaste = None
    monster = re.compile(
        r"(IEC/?T?S?\s*\d+(?:-\d+)*|ISO/IEC\s*\d+|ISO\s*\d+(?:-\d+)*"
        r"|ASTM\s*[A-Z]\d+|(?:ANSI/)?ISA-TR[\d.]+|VDA\s*\d+|EUROMAP\s*\d+"
        r"|VDI/VDE\s*\d+|GS1|TIGER)|(\b\d+\.\d+(?:\.\d+)*\b)")
    for m in monster.finditer(text):
        if m.group(1):
            senaste = _normalisera(m.group(1))
        elif senaste is not None:
            par.append((senaste, m.group(2)))
    return par


def granska_paragrafer(post, verifierade):
    """Varje citerad paragraf ska vara uppslagen. Ett nummer ingen slagit upp
    ar ett pastaende med falsk precision."""
    brister = []
    if not verifierade:
        return brister
    facit = post.get("facit_spar")
    if not isinstance(facit, dict):
        return brister
    text = str(facit.get("harkomst") or "") + " " + str(facit.get("standard") or "")
    for namn, p in sorted(set(_citat(text))):
        if (namn, p) not in verifierade:
            brister.append(Brist(
                post.get("task_id", "?"), "OVERIFIERAD_PARAGRAF",
                "%s %s star inte i M-106:s tabell over uppslagna paragrafer. "
                "Ett uppfunnet paragrafnummer ser ut precis som ett riktigt."
                % (namn, p)))
    return brister


class Brist(object):
    def __init__(self, uppgift, kod, text):
        self.uppgift = uppgift
        self.kod = kod
        self.text = text

    def __repr__(self):
        return "<Brist %s %s>" % (self.uppgift, self.kod)

    def rad(self):
        return "  %-8s %-24s %s" % (self.uppgift, self.kod, self.text)


def matningar_pa_disk(katalog=MATNINGAR):
    """M-numren som FAKTISKT ligger som filer. En harkomst som pekar pa en
    matning som inte finns ar samma form utan innehall som M-numren i
    trosklarna hade (docs/matningar/RESERVERADE.md)."""
    ut = set()
    if not os.path.isdir(katalog):
        return ut
    for namn in os.listdir(katalog):
        m = re.match(r"^(M-\d+)_", namn)
        if m:
            ut.add(m.group(1))
    return ut


def _enhet_i(text):
    return bool(ENHET.search(str(text)))


# ------------------------------------------------------------ kontrollerna

def granska_antaganden(post):
    """Ett antagande utan motiv ar en gissning som fatt ett falt, och ett tal
    utan enhet ar inget matt varde.

    M-85 matte varfor den andra halvan behovs: VC:s egna komponentfiler
    deklarerar MaxPayload UTAN enhet i 2 986 komponenter, 628 av dem med
    vardet 0. Bara 14 % av 82 383 egenskaper sager vilken storhet de bar. En
    enhet far darfor aldrig harledas ur ett talvarde - den ska sta i vardet.
    """
    brister = []
    tid = post.get("task_id", "?")
    for a in post.get("antaganden") or []:
        if not isinstance(a, dict):
            brister.append(Brist(tid, "ANTAGANDE_FORM",
                                 "antagandet ar inte ett objekt: %r" % (a,)))
            continue
        vad = str(a.get("vad") or "")
        varde = str(a.get("varde") or "")
        motiv = str(a.get("motiv") or "")
        if len(motiv.strip()) < schema.MIN_MOTIV_TECKEN:
            brister.append(Brist(
                tid, "ANTAGANDE_UTAN_MOTIV",
                "%r har motivet %r (%d tecken, kravet ar %d); ett antagande "
                "utan motiv ar en gissning som fatt ett falt"
                % (vad, motiv[:40], len(motiv.strip()),
                   schema.MIN_MOTIV_TECKEN)))
        if not HAR_SIFFRA.search(varde):
            continue
        if _enhet_i(varde) or TAL_MED_ORD.search(varde):
            continue
        if _enhet_i(vad):
            brister.append(Brist(
                tid, "TAL_UTAN_ENHET",
                "%r bar en enhet i namnet men vardet ar %r; en enhet far aldrig "
                "harledas ur ett talvarde (M-85)" % (vad, varde)))
        else:
            brister.append(Brist(
                tid, "TAL_UTAN_ENHET",
                "%r har vardet %r, ett bart tal utan storhet" % (vad, varde)))
    return brister


def larmskuld(bank):
    """Uppgifter som ber om ett larm de inte kan ge, och larm ingen kan kvittera."""
    utan_larm, utan_kvittens = [], []
    for u in bank:
        d = u.data
        signaler = (d.get("control") or {}).get("signals") or []
        ut = set(s["name"] for s in signaler if s.get("dir") == "out")
        inn = set(s["name"] for s in signaler if s.get("dir") == "in")
        sager = any(SAGER_LARM.search("%s %s" % (sc.get("forvantat") or "",
                                                 sc.get("beskrivning") or ""))
                    for sc in (d.get("scenarios") or []))
        if sager and "SYS_ALARM" not in ut:
            utan_larm.append(d["task_id"])
        if "SYS_ALARM" in ut and "SYS_RESET" not in inn:
            utan_kvittens.append(d["task_id"])
    return utan_larm, utan_kvittens


def granska_signalkarta(post):
    """Gar signalkartan ihop med karnutgangarna, scenarierna och sparfacit?"""
    brister = []
    tid = post.get("task_id", "?")
    styr = post.get("control") or {}
    signaler = dict((s["name"], s) for s in (styr.get("signals") or [])
                    if isinstance(s, dict) and "name" in s)
    utgangar = set(n for n, s in signaler.items() if s.get("dir") == "out")

    karn = post.get("core_outputs") or []
    if not karn:
        brister.append(Brist(tid, "KARNUTGANG_SAKNAS",
                             "uppgiften namnger inga karnutgangar"))
    for namn in karn:
        if namn not in utgangar:
            brister.append(Brist(
                tid, "KARNUTGANG_EJ_UTSIGNAL",
                "%s ar ingen utsignal i signalkartan" % namn))

    for sc in post.get("scenarios") or []:
        if not isinstance(sc, dict):
            continue
        namn = sc.get("signal")
        if namn is None:
            continue
        if namn not in signaler:
            brister.append(Brist(
                tid, "SCENARIO_OKAND_SIGNAL",
                "scenariot %r pekar pa %s som inte finns i signalkartan"
                % (sc.get("id"), namn)))

    facit = post.get("facit_spar")
    if isinstance(facit, dict):
        rord = set()
        for sekv in facit.get("sekvenser") or []:
            for steg in (sekv.get("steg") or []):
                rord |= set((steg.get("krav") or {}).keys())
                rord |= set((steg.get("satt") or {}).keys())
        for inv in facit.get("invarianter") or []:
            rord |= set((inv.get("nar") or {}).keys())
            rord |= set((inv.get("kraver") or {}).keys())
        for fl in facit.get("flanker") or []:
            rord.add(fl.get("signal"))
        for namn in sorted(rord):
            if namn is not None and namn not in signaler:
                brister.append(Brist(
                    tid, "SPAR_OKAND_SIGNAL",
                    "sparfacit ror %s som inte finns i signalkartan" % namn))
        for namn in karn:
            if namn in utgangar and namn not in rord:
                brister.append(Brist(
                    tid, "KARNUTGANG_UTAN_SPAR",
                    "karnutgangen %s roes aldrig av sparfacit; en utgang ingen "
                    "sekvens, invariant eller flankrakning namner ar inte domd"
                    % namn))
    return brister


def granska_harkomst(post, kanda_matningar):
    """Sager facit varifran det kommer, och kommer det utifran?"""
    brister = []
    tid = post.get("task_id", "?")
    facit = post.get("facit_spar")
    if not isinstance(facit, dict):
        return brister

    harkomst = str(facit.get("harkomst") or "")
    standard = str(facit.get("standard") or "")

    klasser = [k for k in KALLKLASSER if harkomst.strip().upper().startswith(k)
               or ("%s:" % k) in harkomst.upper()]
    if not klasser:
        brister.append(Brist(
            tid, "HARKOMST_UTAN_KLASS",
            "harkomsten %r namnger ingen kallklass; lagliga ar %s"
            % (harkomst[:60], ", ".join(sorted(KALLKLASSER)))))
    else:
        if "STANDARD" in klasser:
            text = harkomst + " " + standard
            if not PARAGRAF.search(text):
                brister.append(Brist(
                    tid, "STANDARD_UTAN_PARAGRAF",
                    "harkomsten kallar sig STANDARD men citerar ingen paragraf; "
                    "ett bart standardnummer sager inte vad facit lutar sig mot"))
            elif not UTGIVARE.search(text):
                brister.append(Brist(
                    tid, "STANDARD_UTAN_UTGIVARE",
                    "harkomsten citerar en paragraf men namner ingen utgivare; "
                    "ett paragrafnummer utan standard gar inte att sla upp"))
        if "RAKNAD" in klasser and not RAKNING.search(harkomst):
            brister.append(Brist(
                tid, "RAKNING_UTAN_RAKNING",
                "harkomsten kallar sig RAKNAD men visar ingen rakning"))

    nummer = _MNUMMER.findall(harkomst)
    if not nummer:
        brister.append(Brist(
            tid, "HARKOMST_UTAN_MATNING",
            "harkomsten namnger ingen matning som bar talen"))
    for n in nummer:
        if n not in kanda_matningar:
            brister.append(Brist(
                tid, "HARKOMST_DOD_MATNING",
                "harkomsten pekar pa %s som inte finns i docs/matningar/" % n))

    for text, falt in ((harkomst, "harkomst"), (standard, "standard")):
        for sokvag in EGEN_KOD:
            if sokvag in text:
                brister.append(Brist(
                    tid, "FACIT_UR_EGEN_KOD",
                    "facit_spar.%s namner %s. Ett facit raknat av koden som "
                    "doms ar tautologiskt: BENCH-4 stod gron i manader pa just "
                    "det (85_bankkontraktet.md §2)" % (falt, sokvag)))
                break
    return brister


def granska_domen(post):
    """Referensen ska uppfylla sitt facit och varje motbevis ska falla."""
    brister = []
    tid = post.get("task_id", "?")
    facit = post.get("facit_spar")
    if not isinstance(facit, dict):
        return brister
    try:
        d = domare.dom_referens(post)
    except (domare.Domsfel, KeyError, TypeError) as fel:
        return [Brist(tid, "FACIT_GAR_EJ_ATT_KORA", str(fel))]
    if not d.godkand:
        brister.append(Brist(
            tid, "REFERENS_FALLER",
            "referenslosningen uppfyller inte sitt eget facit: %s"
            % ", ".join(d.koder[:6])))
    for namn, md, faller_pa in domare.dom_motbevis(post):
        if not md.brister:
            brister.append(Brist(
                tid, "MOTBEVIS_GAR_IGENOM",
                "motbeviset %r falls inte alls; en grind utan trasig fixtur "
                "mater ingenting" % namn))
            continue
        missade = [k for k in faller_pa if k not in md.koder]
        if missade:
            brister.append(Brist(
                tid, "MOTBEVIS_FEL_BRIST",
                "motbeviset %r faller, men inte pa %s; da kan det ha fallit av "
                "vilket skal som helst" % (namn, ", ".join(missade))))
    return brister


def granska_uppgift(post, kanda_matningar, kor_domen=True, verifierade=None):
    brister = []
    brister += granska_antaganden(post)
    brister += granska_signalkarta(post)
    brister += granska_harkomst(post, kanda_matningar)
    brister += granska_paragrafer(
        post, las_verifierade_paragrafer() if verifierade is None else verifierade)
    if kor_domen:
        brister += granska_domen(post)
    return brister


# --------------------------------------------------------- trasiga fixturer

def _fixtur(bank):
    """En uppgift med sparfacit som utgangslage for de trasiga fallen."""
    for u in bank:
        if u.data.get("facit_spar"):
            return copy.deepcopy(u.data)
    raise SystemExit("banken bar ingen uppgift med sparfacit att bygga "
                     "fixturer ur")


def trasiga_fall(bank, kanda_matningar):
    """Fyra fixturer som MASTE falla, med den kod var och en ska falla pa."""
    ut = []

    p = _fixtur(bank)
    p["task_id"] = "FIX-1"
    p["facit_spar"]["harkomst"] = (
        "RAKNAD: fonstret 3,8 till 4,4 s ar hamtat ur "
        "svc/vc_assist_svc/st/tolk.py genom att kora referensen och skriva ned "
        "vad den gav = 4,0 s. M-45")
    ut.append(("facit harlett ur var egen ST-tolk", p, "FACIT_UR_EGEN_KOD"))

    p = _fixtur(bank)
    p["task_id"] = "FIX-2"
    p["antaganden"][0] = {"vad": p["antaganden"][0]["vad"],
                          "varde": p["antaganden"][0]["varde"],
                          "motiv": ""}
    ut.append(("antagande utan motiv", p, "ANTAGANDE_UTAN_MOTIV"))

    p = _fixtur(bank)
    p["task_id"] = "FIX-3"
    p["antaganden"].append({"vad": "spanntrycket 4,5 bar",
                            "varde": "4,5",
                            "motiv": "spanntrycket ar antaget och valt sa att "
                                     "spannaren haller detaljen med marginal"})
    ut.append(("tal med enhet i namnet men inte i vardet", p, "TAL_UTAN_ENHET"))

    p = _fixtur(bank)
    p["task_id"] = "FIX-7"
    p["facit_spar"]["harkomst"] = (
        "STANDARD: manuell aterstallning efter nodstopp enligt "
        "IEC 60204-1:2016 9.2.4 \"Reset\". M-45")
    ut.append(("uppfunnet paragrafnummer", p, "OVERIFIERAD_PARAGRAF"))

    p = _fixtur(bank)
    p["task_id"] = "FIX-5"
    p["facit_spar"]["harkomst"] = (
        "STANDARD: hall-for-att-kora enligt IEC 60204-1. M-45")
    p["facit_spar"]["standard"] = "IEC 60204-1 och IEC 61131-3"
    ut.append(("standard utan paragraf, bara numret", p,
               "STANDARD_UTAN_PARAGRAF"))

    p = _fixtur(bank)
    p["task_id"] = "FIX-6"
    p["facit_spar"]["harkomst"] = (
        "STANDARD: hall-for-att-kora star i 9.2.3.7 och aterstallningen i "
        "4.1.4. M-45")
    p["facit_spar"]["standard"] = "paragraf 9.2.3.7 och paragraf 4.1.4"
    ut.append(("paragraf utan utgivare", p, "STANDARD_UTAN_UTGIVARE"))

    p = _fixtur(bank)
    p["task_id"] = "FIX-4"
    karn = p["core_outputs"][0]
    for sekv in p["facit_spar"]["sekvenser"]:
        for steg in sekv["steg"]:
            (steg.get("krav") or {}).pop(karn, None)
    p["facit_spar"]["invarianter"] = [
        i for i in (p["facit_spar"]["invarianter"] or [])
        if karn not in (i.get("nar") or {}) and karn not in (i.get("kraver") or {})]
    p["facit_spar"]["flanker"] = [
        f for f in (p["facit_spar"]["flanker"] or []) if f.get("signal") != karn]
    ut.append(("karnutgang som sparfacit aldrig ror", p, "KARNUTGANG_UTAN_SPAR"))

    verifierade = las_verifierade_paragrafer()
    domar = []
    for vad, fixtur, vantad in ut:
        koder = [b.kod for b in granska_uppgift(fixtur, kanda_matningar,
                                                kor_domen=False,
                                                verifierade=verifierade)]
        domar.append((vad, vantad, vantad in koder, koder))
    return domar


# ------------------------------------------------------------------ korning

# Golvet ar MATT, inte satt: sa manga sparfacit bar banken nar M-106 skrevs.
# Sparren far bara ga at ett hall. Faller talet har nagon tagit bort ett facit;
# stiger det ska golvet skrivas upp har och i M-106, annars slutar sparren
# mata sin egen storhet.
SPARFACIT_GOLV = 49             # Matt i M-124 (24 i M-106).


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", help="skriv utfallet som JSON till filen")
    ap.add_argument("--tyst", action="store_true", help="bara summan")
    ap.add_argument("--utan-dom", action="store_true",
                    help="hoppa over referens- och motbevisdomen (snabbt svep)")
    a = ap.parse_args(argv)

    bank = lasare.ladda(strikt=True)
    kanda = matningar_pa_disk()
    brister = []
    med_facit = []
    utan_facit = []

    for u in bank:
        post = u.data
        if post.get("facit_spar"):
            med_facit.append(u.id)
        else:
            utan_facit.append(u.id)
        brister += granska_uppgift(post, kanda, kor_domen=not a.utan_dom)

    if not a.tyst:
        print("BANKENS FACIT — %d uppgifter" % len(bank))
        print("  med sparfacit : %d  (%s)"
              % (len(med_facit), ", ".join(med_facit)))
        print("  utan sparfacit: %d" % len(utan_facit))
        if utan_facit:
            print("    %s" % ", ".join(utan_facit))
        print()

    utan_larm, utan_kvittens = larmskuld(bank)
    if not a.tyst:
        print("LARMSKULD — uppgifter som ber om ett larm de inte kan ge")
        print("  utan SYS_ALARM  : %d (taket ar %d)" % (len(utan_larm), LARMSKULD))
        print("  utan SYS_RESET  : %d (taket ar %d)"
              % (len(utan_kvittens), KVITTENSSKULD))
        print()
    if len(utan_larm) > LARMSKULD:
        brister.append(Brist("BANKEN", "LARMSKULD_VAXER",
                             "%d uppgifter sager larma utan SYS_ALARM, taket ar "
                             "%d: %s" % (len(utan_larm), LARMSKULD,
                                         ", ".join(sorted(set(utan_larm))))))
    if len(utan_kvittens) > KVITTENSSKULD:
        brister.append(Brist("BANKEN", "KVITTENSSKULD_VAXER",
                             "%d uppgifter har SYS_ALARM utan SYS_RESET, taket "
                             "ar %d: %s" % (len(utan_kvittens), KVITTENSSKULD,
                                            ", ".join(sorted(set(utan_kvittens))))))

    golvbrist = len(med_facit) < SPARFACIT_GOLV
    if golvbrist:
        brister.append(Brist("BANKEN", "TACKNING_UNDER_GOLVET",
                             "%d uppgifter bar sparfacit, golvet ar %d (M-106)"
                             % (len(med_facit), SPARFACIT_GOLV)))

    if not a.tyst:
        if brister:
            print("BRISTER (%d)" % len(brister))
            for b in brister:
                print(b.rad())
        else:
            print("BRISTER: inga")
        print()

    domar = trasiga_fall(bank, kanda)
    fixturfel = [d for d in domar if not d[2]]
    if not a.tyst:
        print("TRASIGA FALL — varje fixtur maste falla")
        for vad, vantad, foll, koder in domar:
            print("  %-46s %-24s %s" % (vad, vantad, "FALLS" if foll else
                                        "FALLS INTE (%s)" % ",".join(koder[:4])))
        print()

    ok = not brister and not fixturfel
    if not a.tyst:
        print("DOM: %s" % ("GRONT" if ok else "ROTT"))
        if len(med_facit) > SPARFACIT_GOLV:
            print("     Tackningen star pa %d, golvet pa %d. Skriv upp golvet "
                  "i M-106 och i den har filen." % (len(med_facit),
                                                    SPARFACIT_GOLV))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({
                "uppgifter": len(bank),
                "med_sparfacit": med_facit,
                "utan_sparfacit": utan_facit,
                "golv": SPARFACIT_GOLV,
                "larmskuld": {"utan_sys_alarm": sorted(utan_larm),
                              "utan_sys_reset": sorted(utan_kvittens),
                              "tak": [LARMSKULD, KVITTENSSKULD]},
                "brister": [{"uppgift": b.uppgift, "kod": b.kod, "text": b.text}
                            for b in brister],
                "trasiga_fall": [{"vad": v, "vantad_kod": k, "foll": f,
                                  "koder": c} for v, k, f, c in domar],
                "dom": "GRONT" if ok else "ROTT",
            }, f, ensure_ascii=False, indent=1)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
