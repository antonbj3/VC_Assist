# -*- coding: utf-8 -*-
"""Instruktionskorpusen: modellens beteenderegler som DATA pa disk.

Reglerna ligger i instruktioner/ i repots rot, en JSON-fil per block, och
laddas harifran. De ar INTE hardkodade i Python, av tre skal som alla ar
mekaniska och inte smakfragor:

  1. En regel utan harkomst ar en asikt. Varje regel bar falten skal och
     harkomst, och harkomsten SLAS UPP mot disken: en filsokvag maste finnas,
     en matningskod M-nn maste ha en fil under docs/matningar/, och en
     invariant- eller skuldkod maste sta i 90_invarianter.md respektive
     96_ingen_skuld.md. En regel vars kalla inte langre finns faller
     laddningen (fail-closed, I3).
  2. En regel som ar markt "block" pastar att en mekanism tvingar den. Namnet
     provas mot mekanismer.MEKANISMER, sa etiketten kan inte bli en dod grind
     (S2).
  3. Versionerna gor korpusen diffbar. diffa() jamfor tva korpusar regel for
     regel och ANMARKER pa en regel vars text andrats utan att versionen
     hojts - annars driftar innehallet fran sin egen version, och tva
     korningar med "version 1" blir ojamforbara.

Format per fil (instruktioner/<NN>_<id>.json):

    id               maste vara filnamnets del efter siffrorna
    titel            rubrik i systemprompten
    version          heltal >= 1, hojs nar nagon regel i blocket andras
    prioritet        1 ar viktigast. Unik over korpusen. Styr kapordningen.
    kapbar           false = blocket far aldrig kapas ur en prompt
    prioritet_skal   VARFOR blocket ligger dar det ligger i kapordningen
    beskriver        filer blocket handlar om, S7. Maste finnas pa disk
    regler[]         id, version, allvar, tvingas_av, text, skal, harkomst[]

Bara standardbiblioteket. Ingen natverkstrafik.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .fel import Instruktionsfel
from .mekanismer import MEKANISMER
from .text import utan_diakritik

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", "..", ".."))
KORPUSKATALOG = os.path.join(ROT, "instruktioner")

ALLVAR = ("block", "regel")

# Regel-id: tre versaler, bindestreck, tre siffror (SAK-001). Prefixet ar
# blockets, sa ett id sager vilket block regeln hor till aven nar den citeras
# ensam i ett omskrivningskrav.
_REGEL_ID = re.compile(r"^[A-Z]{3}-\d{3}$")
_FILNAMN = re.compile(r"^(\d{2})_([a-z_]+)\.json$")
# Matningskoden. MATT 2026-09-05 (M-105): monstret var `^M-(\d{2})$`, skrivet
# nar hogsta numret var tvasiffrigt, och repot skrev M-100 den 2026-09-04.
# En regel med harkomsten "M-100" foll darfor igenom till filkontrollen och
# anmarktes som "varken en fil eller en matningskod" - en falsk anmarkning i
# den grind som granskar modellens egna beteenderegler. Talet ar oppet uppat
# nu, sa monstret aldras inte om med numret igen.
_MATNING = re.compile(r"^M-(\d{2,})$")
_INVARIANT = re.compile(r"^I\d{1,2}$")
_SKULD = re.compile(r"^S\d{1,2}$")

# Talen nedan ar inte matta utan valda, och de ar valda sa att de faller pa
# TOMHET, inte pa stil. En regel pa tre ord och ett skal pa ett ord ar det
# som ska fastna; en valskriven lang regel ska inte det.
#
# MAX_REGELTEXT: en regel som inte far plats i en mening blir tva regler.
# Talet ar satt over den langsta regeln i korpusen 2026-09-04 (SAK-001, 251
# tecken) med marginal, och sanks aldrig utan att korpusen rattas i samma
# andring.
MAX_REGELTEXT = 400        # 96_ingen_skuld.md S6, matt over korpusen
# MIN_SKAL: ett skal kortare an sa har ar en etikett, inte ett skal.
# Kortaste verkliga skalet i korpusen 2026-09-04 ar 118 tecken.
MIN_SKAL = 40              # 96_ingen_skuld.md S6, matt over korpusen
# MIN_PRIORITET_SKAL: samma krav pa blockets motivering av sin plats i
# kapordningen. Kortaste verkliga 2026-09-04 ar 214 tecken.
MIN_PRIORITET_SKAL = 60    # 96_ingen_skuld.md S6, matt over korpusen

# Formuleringar som gor en regel beroende av sitt sammanhang. Systemprompten
# kapas, sa "se ovan" kan peka pa nagot som inte langre finns med. Regeln ska
# bara sin egen mening.
# Provas mot texten UTAN diakritik (se text.utan_diakritik). MATT 2026-09-05
# (M-105): posten "som namnts" ar skriven i ASCII som all kod i repot, men 46
# av 46 regeltexter i instruktioner/ innehaller a, a eller o, och jamforelsen
# gjordes mot ett rent `text.lower()`. Grenen kunde alltsa aldrig fyra pa den
# enda stavning en riktig regel anvander. Samma felklass som M-70.
_KORSREFERENSER = ("se ovan", "enligt ovan", "som namnts", "se regel",
                   "se nedan", "enligt nedan", "punkten ovan")


@dataclass(frozen=True)
class Regel:
    """En instruktion. Oforanderlig."""

    id: str
    version: int
    allvar: str
    tvingas_av: Optional[str]
    text: str
    skal: str
    harkomst: Tuple[str, ...]
    block: str

    @property
    def tvingad(self) -> bool:
        return self.allvar == "block"

    def rad(self) -> str:
        """Regeln som en rad i systemprompten."""
        return "%s %s" % (self.id, self.text)

    def kanonisk(self) -> Dict[str, object]:
        return {"id": self.id, "version": self.version, "allvar": self.allvar,
                "tvingas_av": self.tvingas_av, "text": self.text,
                "skal": self.skal, "harkomst": list(self.harkomst)}


@dataclass(frozen=True)
class Block:
    """Ett block instruktioner. Ordningen bland reglerna ar viktighetsordning."""

    id: str
    titel: str
    version: int
    prioritet: int
    kapbar: bool
    prioritet_skal: str
    beskriver: Tuple[str, ...]
    regler: Tuple[Regel, ...]
    fil: str

    def text(self, antal_regler: Optional[int] = None) -> str:
        """Blocket som prompttext. antal_regler kapar fran slutet."""
        regler = self.regler if antal_regler is None else self.regler[:antal_regler]
        rader = ["## %s" % self.titel]
        rader += ["- %s" % r.rad() for r in regler]
        return "\n".join(rader)

    def kanonisk(self) -> Dict[str, object]:
        return {"id": self.id, "titel": self.titel, "version": self.version,
                "prioritet": self.prioritet, "kapbar": self.kapbar,
                "prioritet_skal": self.prioritet_skal,
                "beskriver": list(self.beskriver),
                "regler": [r.kanonisk() for r in self.regler]}


class Korpus(object):
    """Alla block, i kapordning: prioritet 1 forst."""

    def __init__(self, block: Sequence[Block], katalog: str):
        self.block = tuple(sorted(block, key=lambda b: b.prioritet))
        self.katalog = katalog

    def __len__(self) -> int:
        return len(self.block)

    def __repr__(self) -> str:
        return "Korpus(%d block, %d regler)" % (len(self.block),
                                                len(self.regler()))

    def regler(self) -> Tuple[Regel, ...]:
        return tuple(r for b in self.block for r in b.regler)

    def block_med_id(self, id_: str) -> Block:
        for b in self.block:
            if b.id == id_:
                return b
        raise KeyError("inget block heter %r" % (id_,))

    def regel_med_id(self, id_: str) -> Regel:
        for r in self.regler():
            if r.id == id_:
                return r
        raise KeyError("ingen regel heter %r" % (id_,))

    def tvingade(self) -> Tuple[Regel, ...]:
        return tuple(r for r in self.regler() if r.tvingad)

    def mekanismer(self) -> Tuple[str, ...]:
        return tuple(sorted({r.tvingas_av for r in self.tvingade()
                             if r.tvingas_av}))

    def kanonisk(self) -> List[Dict[str, object]]:
        return [b.kanonisk() for b in self.block]

    def fingeravtryck(self) -> str:
        """Sha256 over korpusens kanoniska form, forkortat till 12 tecken.

        Varje turprotokoll bar det. Andras en enda regel andras talet, och da
        gar det att se att tva matningar inte lags pa samma instruktioner.
        """
        text = json.dumps(self.kanonisk(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# ---- harkomstuppslag -----------------------------------------------------

def _koder_ur(fil: str, monster: str) -> frozenset:
    """Plockar koderna ur ett specdokument, t.ex. **I7.** ur 90_invarianter."""
    if not os.path.exists(fil):
        return frozenset()
    with open(fil, "r", encoding="utf-8") as f:
        return frozenset(re.findall(monster, f.read()))


class Harkomstuppslag(object):
    """Provar att en harkomstangivelse pekar pa nagot som faktiskt finns."""

    def __init__(self, rot: str = ROT):
        self.rot = rot
        self.invarianter = _koder_ur(
            os.path.join(rot, "docs", "spec", "90_invarianter.md"),
            r"\*\*(I\d{1,2})\.")
        self.skuldregler = _koder_ur(
            os.path.join(rot, "docs", "spec", "96_ingen_skuld.md"),
            r"\*\*(S\d{1,2})\.")
        katalog = os.path.join(rot, "docs", "matningar")
        self.matningar = frozenset(
            n.split("_")[0] for n in sorted(os.listdir(katalog))
            if n.endswith(".md")) if os.path.isdir(katalog) else frozenset()

    def problem(self, post: str) -> Optional[str]:
        """None om harkomsten gar att sla upp, annars skalet den inte gor det."""
        if _MATNING.match(post):
            if post in self.matningar:
                return None
            return ("matningen %s finns inte under docs/matningar/" % post)
        if _INVARIANT.match(post):
            if post in self.invarianter:
                return None
            return "%s finns inte i docs/spec/90_invarianter.md" % post
        if _SKULD.match(post):
            if post in self.skuldregler:
                return None
            return "%s finns inte i docs/spec/96_ingen_skuld.md" % post
        if os.path.exists(os.path.join(self.rot, post)):
            return None
        return ("harkomsten %r ar varken en fil i repot, en matningskod "
                "M-nn, en invariant I-n eller en skuldregel S-n" % post)


# ---- laddning och granskning ---------------------------------------------

def _kraev(d, nyckel, typ, stig, problem):
    """Hamtar ett falt av ratt typ, eller anmarker och ger None."""
    if nyckel not in d:
        problem.append("%s: faltet %s saknas" % (stig, nyckel))
        return None
    varde = d[nyckel]
    if not isinstance(varde, typ) or isinstance(varde, bool) != (typ is bool):
        problem.append("%s: %s ar %s, forvantade %s"
                       % (stig, nyckel, type(varde).__name__,
                          getattr(typ, "__name__", typ)))
        return None
    return varde


def _las_regel(rad, blockid, stig, uppslag, problem) -> Optional[Regel]:
    if not isinstance(rad, dict):
        problem.append("%s: en regel ar %s, inte ett objekt"
                       % (stig, type(rad).__name__))
        return None
    id_ = _kraev(rad, "id", str, stig, problem)
    version = _kraev(rad, "version", int, stig, problem)
    allvar = _kraev(rad, "allvar", str, stig, problem)
    text = _kraev(rad, "text", str, stig, problem)
    skal = _kraev(rad, "skal", str, stig, problem)
    harkomst = _kraev(rad, "harkomst", list, stig, problem)
    if "tvingas_av" not in rad:
        problem.append("%s: faltet tvingas_av saknas; skriv null nar regeln "
                       "inte har nagon mekanism bakom sig" % stig)
        return None
    tvingas_av = rad["tvingas_av"]
    if None in (id_, version, allvar, text, skal, harkomst):
        return None

    namn = "%s/%s" % (stig, id_)
    if not _REGEL_ID.match(id_):
        problem.append("%s: id ska vara tre versaler, bindestreck och tre "
                       "siffror" % namn)
    if version < 1:
        problem.append("%s: version %d ar mindre an 1" % (namn, version))
    if allvar not in ALLVAR:
        problem.append("%s: allvar %r ar varken %s"
                       % (namn, allvar, " eller ".join(ALLVAR)))
    if allvar == "block":
        if not isinstance(tvingas_av, str) or tvingas_av not in MEKANISMER:
            problem.append(
                "%s: allvar block kraver ett mekanismnamn ur "
                "harness/mekanismer.py; %r ar inte ett av %s"
                % (namn, tvingas_av, ", ".join(sorted(MEKANISMER))))
    elif tvingas_av is not None:
        problem.append("%s: allvar regel far inte namnge en mekanism (%r); "
                       "en regel som tvingas ska markas block"
                       % (namn, tvingas_av))
    if not text.strip():
        problem.append("%s: text ar tom" % namn)
    if len(text) > MAX_REGELTEXT:
        problem.append("%s: text ar %d tecken, taket ar %d; dela regeln"
                       % (namn, len(text), MAX_REGELTEXT))
    if text.strip() and not text.strip().endswith((".", "!", "?")):
        problem.append("%s: text slutar inte som en mening" % namn)
    lag = utan_diakritik(text).lower()
    for kors in _KORSREFERENSER:
        if kors in lag:
            problem.append("%s: text bar korsreferensen %r; en kapad prompt "
                           "kan sakna det den pekar pa" % (namn, kors))
    if len(skal.strip()) < MIN_SKAL:
        problem.append("%s: skal ar %d tecken, minst %d kravs; en regel utan "
                       "harkomst ar en asikt"
                       % (namn, len(skal.strip()), MIN_SKAL))
    if not harkomst:
        problem.append("%s: harkomst ar tom" % namn)
    for post in harkomst:
        if not isinstance(post, str):
            problem.append("%s: en harkomstpost ar %s, inte en strang"
                           % (namn, type(post).__name__))
            continue
        fel = uppslag.problem(post)
        if fel:
            problem.append("%s: %s" % (namn, fel))
    if problem and any(p.startswith(namn) for p in problem):
        return None
    return Regel(id=id_, version=version, allvar=allvar,
                 tvingas_av=tvingas_av if allvar == "block" else None,
                 text=text.strip(), skal=skal.strip(),
                 harkomst=tuple(harkomst), block=blockid)


def _las_block(sokvag, uppslag, problem) -> Optional[Block]:
    filnamn = os.path.basename(sokvag)
    m = _FILNAMN.match(filnamn)
    if not m:
        problem.append("%s: filnamnet ska vara <tva siffror>_<id>.json"
                       % filnamn)
        return None
    try:
        with open(sokvag, "r", encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        problem.append("%s: gar inte att lasa som JSON: %s" % (filnamn, e))
        return None
    if not isinstance(data, dict):
        problem.append("%s: filen ar %s, inte ett objekt"
                       % (filnamn, type(data).__name__))
        return None

    id_ = _kraev(data, "id", str, filnamn, problem)
    titel = _kraev(data, "titel", str, filnamn, problem)
    version = _kraev(data, "version", int, filnamn, problem)
    prioritet = _kraev(data, "prioritet", int, filnamn, problem)
    kapbar = _kraev(data, "kapbar", bool, filnamn, problem)
    prioritet_skal = _kraev(data, "prioritet_skal", str, filnamn, problem)
    beskriver = _kraev(data, "beskriver", list, filnamn, problem)
    regler = _kraev(data, "regler", list, filnamn, problem)
    if None in (id_, titel, version, prioritet, kapbar, prioritet_skal,
                beskriver, regler):
        return None

    if id_ != m.group(2):
        problem.append("%s: id %r stammer inte med filnamnet" % (filnamn, id_))
    if version < 1:
        problem.append("%s: version %d ar mindre an 1" % (filnamn, version))
    if prioritet < 1:
        problem.append("%s: prioritet %d ar mindre an 1" % (filnamn, prioritet))
    if len(prioritet_skal.strip()) < MIN_PRIORITET_SKAL:
        problem.append("%s: prioritet_skal ar %d tecken, minst %d kravs; "
                       "kapordningen ska vara motiverad, inte pastadd"
                       % (filnamn, len(prioritet_skal.strip()),
                          MIN_PRIORITET_SKAL))
    if not beskriver:
        problem.append("%s: beskriver ar tom; S7 kraver att ett dokument som "
                       "beskriver kod namnger filen" % filnamn)
    for post in beskriver:
        if not isinstance(post, str) or not os.path.exists(
                os.path.join(uppslag.rot, post)):
            problem.append("%s: beskriver pekar pa %r som inte finns i repot"
                           % (filnamn, post))
    if not regler:
        problem.append("%s: blocket har inga regler" % filnamn)

    lasta = []
    for rad in regler:
        regel = _las_regel(rad, id_, filnamn, uppslag, problem)
        if regel is not None:
            lasta.append(regel)
    if len(lasta) != len(regler):
        return None
    return Block(id=id_, titel=titel, version=version, prioritet=prioritet,
                 kapbar=kapbar, prioritet_skal=prioritet_skal.strip(),
                 beskriver=tuple(beskriver), regler=tuple(lasta),
                 fil=filnamn)


def granska_korpus(katalog: str = KORPUSKATALOG,
                   rot: str = ROT) -> Tuple[List[Block], List[str]]:
    """Laser och granskar. Returnerar (block, problem) utan att kasta."""
    problem: List[str] = []
    if not os.path.isdir(katalog):
        return [], ["instruktionskatalogen %s finns inte" % katalog]
    uppslag = Harkomstuppslag(rot)
    filer = sorted(n for n in os.listdir(katalog) if n.endswith(".json"))
    if not filer:
        problem.append("%s innehaller inga instruktionsfiler" % katalog)
    block: List[Block] = []
    for filnamn in filer:
        b = _las_block(os.path.join(katalog, filnamn), uppslag, problem)
        if b is not None:
            block.append(b)

    sedda_block: Dict[str, str] = {}
    sedda_prioriteter: Dict[int, str] = {}
    sedda_regler: Dict[str, str] = {}
    for b in block:
        if b.id in sedda_block:
            problem.append("blocket %s finns i bade %s och %s"
                           % (b.id, sedda_block[b.id], b.fil))
        sedda_block[b.id] = b.fil
        if b.prioritet in sedda_prioriteter:
            problem.append(
                "prioritet %d delas av %s och %s; kapordningen maste vara "
                "total, annars avgor filordningen vad som kapas"
                % (b.prioritet, sedda_prioriteter[b.prioritet], b.fil))
        sedda_prioriteter[b.prioritet] = b.fil
        for r in b.regler:
            if r.id in sedda_regler:
                problem.append("regel-id %s anvands i bade %s och %s"
                               % (r.id, sedda_regler[r.id], b.fil))
            sedda_regler[r.id] = b.fil
    return block, problem


def las_korpus(katalog: str = KORPUSKATALOG, rot: str = ROT) -> Korpus:
    """Laddar korpusen. Kastar Instruktionsfel med hela problemlistan.

    Fail-closed: en korpus som inte haller sitt format laddas inte alls. Att
    kora med halva instruktionerna vore att kora utan att veta vilka.
    """
    block, problem = granska_korpus(katalog, rot)
    if problem:
        raise Instruktionsfel(katalog, problem)
    return Korpus(block, katalog)


# ---- diff ----------------------------------------------------------------

# Falten som gor en regel till vad den ar. Andras nagot av dem ska regelns
# version hojas, annars betyder "REG-001 v1" tva olika saker i tva korningar.
_INNEHALLSFALT = ("allvar", "tvingas_av", "text", "skal", "harkomst")


@dataclass(frozen=True)
class Regelandring:
    id: str
    falt: str
    fore: object
    efter: object


@dataclass(frozen=True)
class Diff:
    """Skillnaden mellan tva korpusar."""

    nya_block: Tuple[str, ...]
    borttagna_block: Tuple[str, ...]
    nya_regler: Tuple[str, ...]
    borttagna_regler: Tuple[str, ...]
    andringar: Tuple[Regelandring, ...]
    anmarkningar: Tuple[str, ...]

    @property
    def orord(self) -> bool:
        return not (self.nya_block or self.borttagna_block or self.nya_regler
                    or self.borttagna_regler or self.andringar)

    def text(self) -> str:
        if self.orord:
            return "ingen skillnad"
        rader = []
        for namn, poster in (("nytt block", self.nya_block),
                             ("borttaget block", self.borttagna_block),
                             ("ny regel", self.nya_regler),
                             ("borttagen regel", self.borttagna_regler)):
            for p in poster:
                rader.append("%s: %s" % (namn, p))
        for a in self.andringar:
            rader.append("andrad: %s.%s: %r -> %r"
                         % (a.id, a.falt, a.fore, a.efter))
        for a in self.anmarkningar:
            rader.append("ANMARKNING: %s" % a)
        return "\n".join(rader)


def diffa(fore: Korpus, efter: Korpus) -> Diff:
    """Jamfor tva korpusar regel for regel.

    Anmarker pa varje regel vars innehall andrats utan versionshojning, och
    pa varje block vars innehall andrats utan att blockets version hojts. Det
    ar den enda mekaniska sparren mot att "version 1" betyder tva saker.
    """
    fore_block = {b.id: b for b in fore.block}
    efter_block = {b.id: b for b in efter.block}
    fore_regler = {r.id: r for r in fore.regler()}
    efter_regler = {r.id: r for r in efter.regler()}

    andringar: List[Regelandring] = []
    anmarkningar: List[str] = []

    for id_ in sorted(set(fore_regler) & set(efter_regler)):
        a, b = fore_regler[id_], efter_regler[id_]
        andrad = False
        for falt in _INNEHALLSFALT:
            fa, fb = getattr(a, falt), getattr(b, falt)
            if fa != fb:
                andrad = True
                andringar.append(Regelandring(id_, falt, fa, fb))
        if a.version != b.version:
            andringar.append(Regelandring(id_, "version", a.version, b.version))
        elif andrad:
            anmarkningar.append(
                "%s andrades utan att regelns version hojdes (bada sager v%d)"
                % (id_, a.version))
        if a.block != b.block:
            andringar.append(Regelandring(id_, "block", a.block, b.block))

    for id_ in sorted(set(fore_block) & set(efter_block)):
        a, b = fore_block[id_], efter_block[id_]
        for falt in ("titel", "prioritet", "kapbar", "prioritet_skal"):
            fa, fb = getattr(a, falt), getattr(b, falt)
            if fa != fb:
                andringar.append(Regelandring(id_, falt, fa, fb))
        rort = (a.kanonisk() != b.kanonisk())
        if rort and a.version == b.version:
            anmarkningar.append(
                "blocket %s andrades utan att blockets version hojdes "
                "(bada sager v%d)" % (id_, a.version))

    return Diff(
        nya_block=tuple(sorted(set(efter_block) - set(fore_block))),
        borttagna_block=tuple(sorted(set(fore_block) - set(efter_block))),
        nya_regler=tuple(sorted(set(efter_regler) - set(fore_regler))),
        borttagna_regler=tuple(sorted(set(fore_regler) - set(efter_regler))),
        andringar=tuple(andringar),
        anmarkningar=tuple(anmarkningar),
    )
