# -*- coding: utf-8 -*-
"""Personatackningen: sju arbetsprofiler mot det byggda verktygsregistret.

`docs/spec/48_personaprofiler.md` beskriver VAD en anvandare gor i Visual
Components, steg for steg. Den har modulen gor den beskrivningen till en
MATNING: hur stor andel av arbetet ett verktyg kan gora, per profil, med ALLA
steg i namnaren.

VARFOR NAMNAREN AR HELA POANGEN
-------------------------------
En tackningssiffra ar det latt att gora meningslos. Om namnaren far vara "de
steg vi rakade skriva ned" gar talet upp av att man SLUTAR skriva steg.
Registret matte tre grindar natten 2026-09-04/05 som matte nagot annat an de
pastod; en tackningsgrind ar samma felklass fast lattare att bygga av misstag.

Darfor har modulen fyra sparrar mot en krympande namnare, och alla fyra ar
mekaniska:

  1. GOLV per profil. Antalet steg far bara ga UPPAT. Ett steg som tystnat
     bort faller pa NAMNAREN_KRYMPTE - inte pa en hogre procentsats.
  2. KANDA_PROFILER. En hel profil som forsvinner ur specen faller pa
     PROFIL_SAKNAS. Utan den kunde man fa 100 % genom att radera P4.
  3. Lopande numrering. Ett steg som klipps ut mitt i en tabell lamnar ett hal
     i numreringen och faller pa TRASIG_NUMRERING.
  4. FALSK_UTANFOR. Ett steg som marks `UI` eller `.NET` raknas som utanfor
     rackvidd - det ar den ARLIGA vagen att sanka kravet. Den vagen ar stangd
     for allt som faktiskt finns i Python-API:t: markningen maste peka pa ett
     namn som INTE resolverar i indexet, och `.NET:`-namnet maste dessutom
     resolvera i .NET-doc-XML:en.

VAD EN RAD I SPECEN BETYDER
---------------------------
Tabellkolumnerna ar fem, och var och en domes:

    #          lopnummer, 1..N utan hal
    Arbetssteg vad anvandaren gor
    Verkan     `laser` eller `andrar` - stegets verkan PA SCENEN, inte
               verktygets. Det ar facit som verktygets effect provas mot.
    Kraver     en eller flera poster, var och en av fyra slag:
                 `vcX.y`      VC:s Python-API. Maste finnas i api_index.
                 `.NET:N`     .NET-ytan. Maste finnas i vc_dotnet/*.xml och
                              INTE i Python-indexet.
                 `UI:N`       bara i granssnittet. Far INTE finnas i indexet.
                 `TJANST:m`   tjanstens egen kalla utanfor VC. Modulen maste
                              finnas i svc/vc_assist_svc/.
    Tackt av   verktygsnamn ur registret, eller `UI`, `.NET` eller `saknas`.

REGELN SOM GOR EFFEKTEN MEKANISK
--------------------------------
Verktygen bar redan `effect` read/write (45_verktyg.md, I12). Ett steg vars
verkan ar `andrar` kan darfor inte tackas av enbart lasande verktyg - det ar
FEL_VERKAN. Omvant ar tillatet: `measure_distance` ar deklarerad `write` for
att den bygger en kollisionsdetektor i scenen, och far darfor tacka ett
lasande steg.

Talen skrivs av `tests/protocol/kor_fas19_tackning.py` (fas 19, M-100).
"""
from __future__ import annotations

import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", ".."))
SPEC = os.path.join(ROT, "docs", "spec", "48_personaprofiler.md")
DOTNET_KATALOG = os.path.join(ROT, "docs", "referens", "vc_dotnet")
TJANSTROT = os.path.join(ROT, "svc", "vc_assist_svc")

# Markorerna i kolumnen "Tackt av" som INTE ar verktygsnamn.
UTANFOR = ("UI", ".NET")
OBYGGT = "saknas"

LASER = "laser"
ANDRAR = "andrar"
VERKAN = (LASER, ANDRAR)

# Prefixen i kolumnen "Kraver" som pekar utanfor VC:s Python-API. Specen
# skriver TJANST med a-umlaut; prefixen provas darfor pa den avdiakritiserade
# posten. En markor som slutar galla for att nagon skrev ett svenskt ord med
# ratt stavning ar en tyst vag ut ur namnaren.
P_DOTNET = ".NET:"
P_UI = "UI:"
P_TJANST = "TJANST:"


def _prefix(post: str) -> Tuple[str, str]:
    """(prefix, resten) om posten bar ett av de tre prefixen, annars ("", posten)."""
    naken = _avdiakritik(post)
    for p in (P_DOTNET, P_UI, P_TJANST):
        if naken.startswith(p):
            return p, post[len(p):].strip()
    return "", post


def _avdiakritik(text: str) -> str:
    """a-ring och a-umlaut ska inte kunna gora en rad oigenkannlig."""
    return "".join(t for t in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(t))


# ==========================================================================
# 1. LASNINGEN
# ==========================================================================

_RUBRIK = re.compile(r"^##\s+(P\d+)\s+[-\u2013\u2014]\s+(.+?)\s*$")
_ANNAN_RUBRIK = re.compile(r"^##\s")
_TABELLRAD = re.compile(r"^\|\s*(\d+)\s*\|")
_KOD = re.compile(r"`([^`]+)`")


class Specfel(Exception):
    """Specen gar inte att lasa. En olasbar spec ar aldrig gron."""


@dataclass(frozen=True)
class Steg:
    """En rad i en profiltabell."""

    profil: str
    nummer: int
    text: str
    verkan: str
    kraver: Tuple[str, ...]
    tackt_av: Tuple[str, ...]

    @property
    def utanfor_rackvidd(self) -> bool:
        return any(t in UTANFOR for t in self.tackt_av)

    @property
    def verktyg(self) -> Tuple[str, ...]:
        return tuple(t for t in self.tackt_av
                     if t not in UTANFOR and t != OBYGGT)

    @property
    def tackt(self) -> bool:
        return bool(self.verktyg)

    def __str__(self) -> str:
        return "%s.%d %s" % (self.profil, self.nummer, self.text)


@dataclass(frozen=True)
class Profil:
    """En persona med alla sina arbetssteg."""

    kod: str
    namn: str
    steg: Tuple[Steg, ...]

    @property
    def antal(self) -> int:
        return len(self.steg)


def _delar(rad: str) -> List[str]:
    bitar = rad.strip().split("|")
    # En markdown-rad borjar och slutar med |, sa forsta och sista biten ar tomma.
    if len(bitar) < 2 or bitar[0].strip() or bitar[-1].strip():
        raise Specfel("raden ar ingen hel tabellrad: %r" % rad[:80])
    return [b.strip() for b in bitar[1:-1]]


def _poster(cell: str) -> Tuple[str, ...]:
    """Kodmarkerade poster plus bara markorer, i ordning. Tom cell ar ett fel.

    Markorerna UI, .NET och `saknas` skrivs UTAN backticks, sa att de syns som
    markorer och inte som namn. De plockas ur det som blir kvar nar de
    kodmarkerade posterna lyfts bort - annars hade cellen "`connect`, UI"
    tappat sin UI-markor tyst, och just den cellen ar en motsagelse som ska
    falla (BADE_OCH).
    """
    ut = [m.strip() for m in _KOD.findall(cell)]
    for ord_ in re.split(r"[,;\s]+", _KOD.sub(" ", cell).strip()):
        if ord_ in UTANFOR or ord_ == OBYGGT:
            ut.append(ord_)
    return tuple(ut)


def las_profiler(text: str) -> List[Profil]:
    """Profilerna ur specens text. Kastar Specfel pa en rad som inte gar att tolka."""
    profiler: List[Profil] = []
    kod: Optional[str] = None
    namn = ""
    steg: List[Steg] = []

    def stang():
        if kod is not None:
            profiler.append(Profil(kod, namn, tuple(steg)))

    for radnr, rad in enumerate(text.splitlines(), 1):
        m = _RUBRIK.match(rad)
        if m:
            stang()
            kod, namn = m.group(1), m.group(2)
            steg = []
            continue
        if _ANNAN_RUBRIK.match(rad):
            stang()
            kod, namn, steg = None, "", []
            continue
        if kod is None:
            continue
        if not _TABELLRAD.match(rad):
            continue
        delar = _delar(rad)
        if len(delar) != 5:
            raise Specfel("rad %d i %s har %d kolumner, ska ha 5: %r"
                          % (radnr, kod, len(delar), rad[:90]))
        nummer = int(delar[0])
        stegtext = delar[1].strip()
        verkan = _avdiakritik(delar[2].strip().lower())
        kraver = _poster(delar[3])
        tackt_av = _poster(delar[4])
        if not stegtext:
            raise Specfel("rad %d i %s saknar stegtext" % (radnr, kod))
        if not kraver:
            raise Specfel("%s steg %d: kolumnen Kraver ar tom; ett steg utan "
                          "krav gar inte att doma" % (kod, nummer))
        if not tackt_av:
            raise Specfel("%s steg %d: kolumnen Tackt av ar tom; skriv "
                          "verktygsnamn, UI, .NET eller %s"
                          % (kod, nummer, OBYGGT))
        steg.append(Steg(kod, nummer, stegtext, verkan, kraver, tackt_av))
    stang()
    return profiler


def las_spec(sokvag: str = SPEC) -> List[Profil]:
    with open(sokvag, "r", encoding="utf-8") as f:
        return las_profiler(f.read())


# ==========================================================================
# 2. KALLORNA SOM DOMER
# ==========================================================================

def dotnet_namn(katalog: str = DOTNET_KATALOG) -> frozenset:
    """Varje typ- och medlemsnamn i .NET-doc-XML:en, utan T:/M:/P:-prefixet.

    Kastar om katalogen ar tom. Ett tomt index godkanner varje pahittat
    .NET-namn, och det ar precis den falska gronen grinden finns for.
    """
    ut = set()
    filer = sorted(f for f in os.listdir(katalog) if f.endswith(".xml"))
    if not filer:
        raise Specfel("inga .NET-XML-filer i %s" % katalog)
    for filnamn in filer:
        rot = ET.parse(os.path.join(katalog, filnamn)).getroot()
        for medlem in rot.findall("./members/member"):
            namn = (medlem.get("name") or "").strip()
            if len(namn) > 2 and namn[1] == ":":
                namn = namn[2:]
            if "(" in namn:
                namn = namn.split("(", 1)[0]
            if namn:
                ut.add(namn)
    if len(ut) < 1000:
        raise Specfel("bara %d .NET-namn lasta ur %s; kallan ar for tunn for "
                      "att doma pa" % (len(ut), katalog))
    return frozenset(ut)


def standardindex():
    from .api_index import bygg_index
    return bygg_index()


def standardregister():
    from .verktyg import REGISTER
    return REGISTER


# ==========================================================================
# 3. DOMEN
# ==========================================================================

@dataclass(frozen=True)
class Fel:
    """En fallning: vilken klass, var, och varfor."""

    kod: str
    var: str
    text: str

    def __str__(self) -> str:
        return "%-18s %-8s %s" % (self.kod, self.var, self.text)


# Golvet per profil: minsta antal arbetssteg specen far bara. Talen ar RAKNADE
# ur 48_personaprofiler.md nar fas 19 stangdes (M-100), inte valda. Regeln ar
# densamma som harnessens (M-53): golvet far bara ga uppat. Sanker nagon ett
# tal har ska det synas i en diff bredvid den spec som blev kortare.
GOLV: Dict[str, int] = {
    "P1": 37,   # layoutplaneraren
    "P2": 36,   # robotprogrammeraren
    "P3": 35,   # driftsattaren
    "P4": 37,   # flodesingenjoren
    "P5": 27,   # losningsarkitekten som saljer
    "P6": 33,   # komponentbyggaren
    "P7": 23,   # utbildaren
}

# Profilerna som MASTE finnas. En profil som stryks tar med sig hela sin
# namnare, och tackningen stiger av det. M-100.
KANDA_PROFILER: Tuple[str, ...] = tuple(sorted(GOLV))


class Domare(object):
    """Domer profilerna mot API-indexet, .NET-ytan och verktygsregistret."""

    def __init__(self, index=None, register=None, dotnet=None,
                 tjanstrot: str = TJANSTROT, golv: Optional[Dict[str, int]] = None,
                 kanda: Optional[Sequence[str]] = None):
        self.index = index if index is not None else standardindex()
        self.register = register if register is not None else standardregister()
        self.dotnet = dotnet if dotnet is not None else dotnet_namn()
        self.tjanstrot = tjanstrot
        self.golv = dict(GOLV if golv is None else golv)
        self.kanda = tuple(KANDA_PROFILER if kanda is None else kanda)
        # Skiftlagesokanslig spegel av hela indexet. `UI:load` ar samma namn
        # som `load` for en manniska, och en markor som staller sig utanfor
        # rackvidd pa en skiftlagesskillnad ar precis den tysta krympningen
        # grinden finns for.
        self._gemener = frozenset(s.namn.lower() for s in self.index.symboler)

    # ---- enskilda krav ----------------------------------------------------

    def _dom_krav(self, steg: Steg) -> List[Fel]:
        fel: List[Fel] = []
        for post in steg.kraver:
            var = str(steg)
            prefix, namn = _prefix(post)
            if prefix == P_DOTNET:
                if namn not in self.dotnet:
                    fel.append(Fel("OKANT_DOTNET", var,
                                   "%s finns inte i docs/referens/vc_dotnet/"
                                   % namn))
                elif self.index.finns(namn):
                    fel.append(Fel("FALSK_UTANFOR", var,
                                   "%s star som .NET men finns i Python-API:t"
                                   % namn))
            elif prefix == P_UI:
                if self.index.finns(namn) or namn.lower() in self._gemener:
                    fel.append(Fel("FALSK_UTANFOR", var,
                                   "%s star som UI men finns i Python-API:t"
                                   % namn))
            elif prefix == P_TJANST:
                modul = namn
                stig = os.path.join(self.tjanstrot, modul.replace(".", os.sep))
                if not (os.path.exists(stig) or os.path.exists(stig + ".py")):
                    fel.append(Fel("OKAND_TJANST", var,
                                   "%s finns inte under svc/vc_assist_svc/"
                                   % modul))
            elif not self.index.finns(post):
                fel.append(Fel("OKANT_API", var,
                               "%s finns inte i API-indexet (3444 symboler)"
                               % post))
        return fel

    # ---- enskilda steg ----------------------------------------------------

    def _dom_steg(self, steg: Steg) -> List[Fel]:
        var = str(steg)
        fel: List[Fel] = self._dom_krav(steg)

        if steg.verkan not in VERKAN:
            fel.append(Fel("OKAND_VERKAN", var,
                           "verkan %r ar varken %s eller %s"
                           % (steg.verkan, LASER, ANDRAR)))

        okanda = [v for v in steg.verktyg if v not in self.register]
        for v in okanda:
            fel.append(Fel("OKANT_VERKTYG", var,
                           "%s star som tackande men finns inte i registret" % v))

        if steg.utanfor_rackvidd:
            if steg.verktyg:
                fel.append(Fel("BADE_OCH", var,
                               "steget ar bade markt utanfor rackvidd och "
                               "tackt av %s" % ", ".join(steg.verktyg)))
            utanfor_krav = [p for p in steg.kraver
                            if _prefix(p)[0] in (P_DOTNET, P_UI)]
            if not utanfor_krav:
                fel.append(Fel("FALSK_UTANFOR", var,
                               "markt %s men varje krav ligger i Python-API:t; "
                               "da ar steget inom rackhall och far inte lyftas "
                               "ur namnaren"
                               % "/".join(t for t in steg.tackt_av
                                          if t in UTANFOR)))

        kanda_verktyg = [v for v in steg.verktyg if v in self.register]
        if steg.verkan == ANDRAR and kanda_verktyg:
            if not any(self.register[v].effect == "write" for v in kanda_verktyg):
                fel.append(Fel("FEL_VERKAN", var,
                               "steget andrar scenen men %s ar %s"
                               % (", ".join(kanda_verktyg),
                                  ", ".join("%s=read" % v for v in kanda_verktyg))))

        if steg.kraver and all(_prefix(p)[0] == P_TJANST for p in steg.kraver):
            fjarr = [v for v in kanda_verktyg
                     if self.register[v].mode != "data"]
            if fjarr:
                fel.append(Fel("FEL_KALLA", var,
                               "steget kraver bara tjanstens egen kalla men "
                               "tacks av %s som maste kora i VC"
                               % ", ".join(fjarr)))
        return fel

    # ---- hela specen ------------------------------------------------------

    def doma(self, profiler: Sequence[Profil]) -> List[Fel]:
        fel: List[Fel] = []
        koder = [p.kod for p in profiler]

        for kod in self.kanda:
            if kod not in koder:
                fel.append(Fel("PROFIL_SAKNAS", kod,
                               "profilen star i KANDA_PROFILER men inte i "
                               "specen; dess steg forsvann ur namnaren"))
        for kod in koder:
            if koder.count(kod) > 1:
                fel.append(Fel("DUBBEL_PROFIL", kod,
                               "profilkoden star mer an en gang"))
                break

        for profil in profiler:
            if not profil.steg:
                fel.append(Fel("TOM_PROFIL", profil.kod,
                               "profilen har noll arbetssteg"))
                continue
            vantade = list(range(1, profil.antal + 1))
            om = [s.nummer for s in profil.steg]
            if om != vantade:
                fel.append(Fel("TRASIG_NUMRERING", profil.kod,
                               "stegen ar numrerade %s, vantade 1..%d"
                               % (om, profil.antal)))
            golv = self.golv.get(profil.kod)
            if golv is not None and profil.antal < golv:
                fel.append(Fel("NAMNAREN_KRYMPTE", profil.kod,
                               "%d steg, golvet ar %d (M-100). Ett steg som "
                               "tystnat bort hojer tackningen utan att nagot "
                               "byggts" % (profil.antal, golv)))
            for steg in profil.steg:
                fel.extend(self._dom_steg(steg))
        return fel


# ==========================================================================
# 4. TALEN
# ==========================================================================

@dataclass(frozen=True)
class Tal:
    """Tackningen for en profil. Alla tal ar ANTAL - kvoten bar sin namnare."""

    kod: str
    namn: str
    steg: int
    tackta: int
    utanfor: int
    obyggda: int

    @property
    def inom_rackhall(self) -> int:
        return self.steg - self.utanfor

    @property
    def andel_av_allt(self) -> float:
        return self.tackta / float(self.steg) if self.steg else 0.0

    @property
    def andel_inom_rackhall(self) -> float:
        n = self.inom_rackhall
        return self.tackta / float(n) if n else 0.0


def rakna(profil: Profil) -> Tal:
    tackta = sum(1 for s in profil.steg if s.tackt)
    utanfor = sum(1 for s in profil.steg if s.utanfor_rackvidd and not s.tackt)
    obyggda = profil.antal - tackta - utanfor
    return Tal(profil.kod, profil.namn, profil.antal, tackta, utanfor, obyggda)


def verktyg_ingen_profil_behover(profiler: Sequence[Profil],
                                 register=None) -> Tuple[str, ...]:
    """Byggd kapacitet som ingen profils arbetssteg pekar pa.

    Det ar inte ett fel - men det ar ett TAL, och det ar lika arligt som
    tackningen: verktyg som ingen bad om ar arbete som inte matts mot ett
    behov.
    """
    register = standardregister() if register is None else register
    behovda = set()
    for profil in profiler:
        for steg in profil.steg:
            behovda.update(steg.verktyg)
    return tuple(sorted(set(register) - behovda))


def api_namn(profiler: Sequence[Profil]) -> Tuple[str, ...]:
    """Varje VC-API-namn profilerna pekar pa, utan de tre markerade slagen."""
    ut = set()
    for profil in profiler:
        for steg in profil.steg:
            for post in steg.kraver:
                if not _prefix(post)[0]:
                    ut.add(post)
    return tuple(sorted(ut))


def sammanfattning(profiler: Sequence[Profil]) -> Dict[str, object]:
    tal = [rakna(p) for p in profiler]
    return {
        "profiler": len(profiler),
        "steg": sum(t.steg for t in tal),
        "tackta": sum(t.tackta for t in tal),
        "utanfor": sum(t.utanfor for t in tal),
        "obyggda": sum(t.obyggda for t in tal),
        "per_profil": tal,
    }
