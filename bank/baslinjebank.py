# -*- coding: utf-8 -*-
"""M-62: baslinjen över banken, med samma domare och samma grindar som modellen.

Fas 11 i `docs/spec/70_faser.md`. Kör den regelbaserade generatorn i
`svc/vc_assist_svc/plc/baslinje/` över bankens uppgifter och rapporterar
**talen först**, alltid med nämnare.

## Vad som mäts, och på vilken nämnare

| Storhet | Nämnare | Vad som kan döma den |
|---|---|---|
| grind 2 statisk analys | genereringsuppgifterna | ST-lagrets validator |
| grind 3 deklarationsmatchning | genereringsuppgifterna | signalkartan |
| grind 1 kompilering | genereringsuppgifterna | STruC++, bara med `--strucpp` |
| spårfacit | uppgifterna med `facit_spar` | `bank/domare.py` |
| mekaniska påståenden | punktkrav, invarianter, flanker | `bank/domare.py` |

Grind 4 körs aldrig här: baslinjen skriver ingen scenkod, och en grind som
inte kunde köras är aldrig ett godkännande (I3). Den står i rapporten med sitt
eget skäl.

## Genereringsuppgifter, och varför de är 37 och inte 51

Fjorton uppgifter är medvetet trasiga varianter (`variant_av` satt). De bär en
färdigskriven trasig lösning och finns för att pröva DOMAREN. Att låta en
generator lösa dem hade mätt fel sak. Nämnaren skrivs därför ut som "37
genereringsuppgifter av bankens 51".

## Tre nivåer, och skillnaden mellan dem är hela slutsatsen

* `mager` — bara I/O-listan. Vad en klassisk generator klarar på en signalkarta.
* `prosa` — I/O-listan plus uppgiftstextens egna numrerade listor, lästa med
  samma grammatik. Det modellen får se.
* `spec` — I/O-listan plus de strukturerade fälten `control.sequence` och
  `control.interlocks`.

Körs som `python3 bank/baslinjebank.py`.

beskriver: bank/baslinjebank.py, svc/vc_assist_svc/plc/baslinje/generator.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, ".."))
for _p in (_HAR, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import domare                                                # noqa: E402
import par as Par                                            # noqa: E402
import reparationsbank as RB                                 # noqa: E402
from vc_assist_svc.plc import reparation as R                 # noqa: E402
from vc_assist_svc.plc.baslinje import (BaslinjeModell, NIVAER,  # noqa: E402
                                        NIVA_MAGER, NIVA_PROSA, NIVA_SPEC,
                                        Spec)
from vc_assist_svc.plc.baslinje.generator import Baslinje     # noqa: E402
from vc_assist_svc.plc.skelett import Skelett                 # noqa: E402
from vc_assist_svc.plc.stationsgrind import (Kandidat,        # noqa: E402
                                             NAMN_ANROP, NAMN_DEKLARATION,
                                             NAMN_KOMPILERING, NAMN_STATISK,
                                             granska_station)

# Grindarna baslinjen döms av utan kompilator. Grind 1 läggs till av --strucpp
# och grind 4 aldrig: den kräver scenkod, som varken baslinjen eller modellen
# levererar i fas 11.
GRINDAR_UTAN_KOMPILATOR = (NAMN_STATISK, NAMN_DEKLARATION)


# ---------------------------------------------------------------- uppgifter

def las_uppgifter() -> List[dict]:
    ut = []
    katalog = os.path.join(_HAR, "uppgifter")
    for f in sorted(os.listdir(katalog)):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(katalog, f), "r", encoding="utf-8") as fh:
            ut.append(json.load(fh))
    return ut


def genereringsuppgifter(poster: Sequence[dict]) -> List[dict]:
    """Uppgifterna en generator ska lösa: allt utom de trasiga varianterna."""
    return [p for p in poster if not p.get("variant_av")]


def med_sparfacit(poster: Sequence[dict]) -> List[dict]:
    return [p for p in poster if p.get("facit_spar")]


def spec_ur_uppgift(post: dict) -> Spec:
    """Uppgiften som baslinjen ser den. `facit_spar` rörs aldrig.

    Att fältet inte läses är inte en artighet utan en mätbar egenskap:
    `tests/enhet/test_baslinje.py` kör generatorn mot en uppgift där facit
    bytts ut mot skräp och kräver byte-identisk kod.
    """
    c = post.get("control") or {}
    return Spec(signaler=tuple(c.get("signals") or ()),
                sekvens=tuple(c.get("sequence") or ()),
                forreglingar=tuple(c.get("interlocks") or ()),
                uppgiftstext=post.get("prompt") or "")


# ---------------------------------------------------------------- byggandet

@dataclass
class Bygge:
    """Ett genererat program, med allt domaren behöver."""

    post: dict
    station: str
    karta: object
    skelett: Skelett
    kropp: str
    st_kalla: str
    rapport: object

    @property
    def task_id(self) -> str:
        return self.post.get("task_id") or ""


def bygg(post: dict, baslinje: Baslinje) -> Bygge:
    spec = spec_ur_uppgift(post)
    resultat = baslinje.generera(spec)
    karta = RB.karta_ur_uppgift(post, resultat.station)
    skelett = Skelett.av_karta(karta, resultat.deklarationer)
    return Bygge(post, resultat.station, karta, skelett, resultat.kropp,
                 skelett.las_svar(resultat.kropp), resultat.rapport)


# ---------------------------------------------------------------- golvet
#
# Ett tal som säger "277 av 349 pastaenden uppfyllda" betyder ingenting utan
# sitt golv. En stor del av bankens punktkrav är NEGATIVA — "bandet ska sta",
# "ingenting far vara kommenderat" — och ett program som aldrig kommenderar
# nagot uppfyller dem alla, av precis fel skäl. Golvet är därför en egen
# mätning och står bredvid varje påståendetal.

def nollprogram(post: dict, station: str = "NOLL") -> Tuple[str, object]:
    """Programmet som inte styr någonting, med sin karta.

    Varje utgång skrivs till sitt nollvärde en gång, varje ingång läses en
    gång. Koden går igenom grind 2 och grind 3 utan anmärkning och styr
    ingenting alls. Den är golvet under varje påståendetal, och den är den
    trasiga fixturen i `tests/enhet/test_baslinje.py`: en baslinje som far
    ratt av fel skal maste falla.
    """
    karta = RB.karta_ur_uppgift(post, station)
    rader = ["(* Golvet: styr ingenting. Finns for att visa vad ett program",
             "   som aldrig kommenderar nagot anda uppfyller. *)"]
    for s in karta.signaler:
        if not s.ar_utgang:
            continue
        noll = {"BOOL": "FALSE", "REAL": "0.0"}.get(s.typ.namn, "0")
        rader.append("%s := %s;" % (s.tagg, noll))
    delar = []
    for s in karta.signaler:
        if s.ar_utgang:
            continue
        if s.typ.namn == "BOOL":
            delar.append(s.tagg)
        elif s.typ.namn == "REAL":
            delar.append("(%s <> 0.0)" % s.tagg)
        else:
            delar.append("(%s <> 0)" % s.tagg)
    dekl = ""
    if delar:
        dekl = "VAR\n    bLast : BOOL := FALSE;\nEND_VAR\n"
        rader.append("bLast := %s;" % " OR ".join(delar))
    skelett = Skelett.av_karta(karta, dekl)
    return skelett.las_svar("\n".join(rader) + "\n"), karta


# ---------------------------------------------------------------- domarna

def stationsdom(bygge: Bygge, strucpp_cli: Optional[str] = None,
                byggkatalog: Optional[str] = None):
    return granska_station(
        Kandidat(bygge.karta.station, bygge.st_kalla), bygge.karta,
        strucpp_cli=strucpp_cli, byggkatalog=byggkatalog,
        stanna_vid_forsta=False)


# ---- påståenderäkningen --------------------------------------------------
#
# Ett tal som säger "3 av 4 uppgifter" döljer att den fjärde missade ett enda
# krav av sextio. Bänken räknar därför också på PÅSTÅENDENIVÅ, med de tre
# formernas egna nämnare.

@dataclass
class Pastaenden:
    punktkrav: int = 0
    invarianter: int = 0          # instanser: (sekvens, invariant)
    invariantnamn: int = 0        # definitioner, som M-45 räknar dem
    flanker: int = 0

    @property
    def totalt(self) -> int:
        return self.punktkrav + self.invarianter + self.flanker


def pastaenden(post: dict) -> Pastaenden:
    facit = post.get("facit_spar") or {}
    invarianter = facit.get("invarianter") or []
    ut = Pastaenden(invariantnamn=len(invarianter),
                    flanker=len(facit.get("flanker") or []))
    for sekv in facit.get("sekvenser") or []:
        sid = sekv["id"]
        for steg in sekv["steg"]:
            ut.punktkrav += len(steg.get("krav") or {})
        ut.invarianter += len([i for i in invarianter
                               if i.get("sekvens") in (None, "*", sid)])
    return ut


@dataclass
class Utfall:
    """Domen över ett bygge, uppdelad på påståendeformerna."""

    task_id: str
    godkand: bool
    totalt: Pastaenden
    brutna_punkt: int = 0
    brutna_invariant: int = 0
    brutna_flank: int = 0
    tolkfel: bool = False
    forgrind: str = ""
    klasser: Tuple[str, ...] = ()
    koder: Tuple[str, ...] = ()

    @property
    def uppfyllda(self) -> int:
        if self.tolkfel or self.forgrind:
            return 0
        return (self.totalt.totalt - self.brutna_punkt
                - self.brutna_invariant - self.brutna_flank)


def spardom(post: dict, st_kalla: str) -> Utfall:
    """Spårfacit över en lösning, räknat per påståendeform.

    Ett tolkfel eller en fälld förgrind räknas som att INGET påstående är
    uppfyllt. Skälet är domarens egen mekanik: ett tolkfel bryter körningen,
    och de påståenden som aldrig prövades får inte se ut som uppfyllda. En
    oprövad grind är aldrig ett godkännande (I3).
    """
    totalt = pastaenden(post)
    d = domare.dom(post, st_kalla)
    ut = Utfall(post.get("task_id") or "", d.godkand, totalt,
                koder=tuple(d.koder))
    klasser: List[str] = []
    for kod in d.koder:
        klass = RB.sparklass(kod)
        if klass not in klasser:
            klasser.append(klass)
        if kod.startswith("tolkfel:"):
            ut.tolkfel = True
        elif kod.startswith("forgrind:"):
            ut.forgrind = kod
        elif kod.startswith("flank:"):
            ut.brutna_flank += 1
        elif kod.startswith("invariant:"):
            ut.brutna_invariant += 1
        else:
            ut.brutna_punkt += 1
    ut.klasser = tuple(klasser)
    return ut


# ---------------------------------------------------------------- körningen

@dataclass
class Nivakorning:
    niva: str
    driv_obundna: bool = False
    las_obundna: bool = False
    grind: Dict[str, Dict[str, object]] = field(default_factory=dict)
    spar: Dict[str, Utfall] = field(default_factory=dict)
    rapporter: Dict[str, object] = field(default_factory=dict)
    fel: Dict[str, str] = field(default_factory=dict)

    @property
    def namn(self) -> str:
        extra = []
        if self.driv_obundna:
            extra.append("driv")
        if self.las_obundna:
            extra.append("las")
        return self.niva + ("+" + "+".join(extra) if extra else "")


def kor_niva(poster: Sequence[dict], niva: str, driv_obundna: bool = False,
             las_obundna: bool = False, strucpp_cli: Optional[str] = None,
             byggkatalog: Optional[str] = None) -> Nivakorning:
    korning = Nivakorning(niva, driv_obundna, las_obundna)
    baslinje = Baslinje(niva=niva, driv_obundna=driv_obundna,
                        las_obundna=las_obundna)
    for post in poster:
        tid = post.get("task_id") or ""
        try:
            bygge = bygg(post, baslinje)
        except Exception as fel:
            # Ett bygge som inte går att göra är ett resultat och inte ett
            # avbrott: uppgiften räknas som fälld, med skälet utskrivet.
            korning.fel[tid] = "%s: %s" % (type(fel).__name__, fel)
            print("BYGGFEL %s: %s" % (tid, fel), file=sys.stderr)
            continue
        korning.rapporter[tid] = bygge.rapport
        dom = stationsdom(bygge, strucpp_cli, byggkatalog)
        korning.grind[tid] = dict(dom.forgrindar)
        if post.get("facit_spar"):
            korning.spar[tid] = spardom(post, bygge.st_kalla)
    return korning


# ---------------------------------------------------------------- slingan

# Skelettets VAR-block är låst när slingan startar, och det är en egenskap hos
# PRODUKTEN och inte hos baslinjen: `61_st_generering.md` säger att modellen
# aldrig skriver deklarationer. Följden mättes här: en reparation som behöver en
# NY arbetsvariabel — en timer, en flankdetektor, en diagnosbit — går inte att
# göra inifrån slingan, och grind 2 fäller nästa varv på ODEKLARERAD. Det
# gäller en språkmodell precis lika hårt.
#
# De två ramlägena mäter de två storheterna var för sig:
RAM_MINIMAL = "minimal"   # ramen ur FÖRSTA svaret: slingans verkliga villkor
RAM_MAXIMAL = "maximal"   # ramen ur generatorns hela arbetsuppsättning
RAMLAGEN = (RAM_MINIMAL, RAM_MAXIMAL)


def kor_slinga(post: dict, niva: str, lage: str = R.LAGE_RENT,
               max_varv: int = R.MAX_VARV, ram: str = RAM_MINIMAL):
    """Reparationsslingan med baslinjen som modell. SAMMA slinga som modellen.

    Grindstegen är reparationsbankens egna: `Stationssteg` för grind 2 och 3
    och `Sparfacitsteg` för spårfacit. Att de är samma objekt är hela poängen
    med fas 11 — ett par som körts genom olika slingor mäter slingan.
    """
    spec = spec_ur_uppgift(post)
    modell = BaslinjeModell(spec, niva=niva)
    forsta = modell.generator().generera(spec)
    karta = RB.karta_ur_uppgift(post, forsta.station)
    if ram == RAM_MAXIMAL:
        # Ramen byggs ur en körning med varje växel på, så att den bär varje
        # arbetsvariabel generatorn kan komma att behöva. Då mäter slingan
        # metodens reparationsförmåga och inte ramens styvhet.
        forsta = Baslinje(niva=niva, driv_obundna=True,
                          las_obundna=True).generera(spec)
    elif ram != RAM_MINIMAL:
        raise ValueError("okänt ramläge %r; lägena är %s"
                         % (ram, ", ".join(RAMLAGEN)))
    skelett = Skelett.av_karta(karta, forsta.deklarationer)
    grindar = [R.Stationssteg(karta), RB.Sparfacitsteg(post)]
    slinga = R.Reparationsslinga(skelett, grindar, lage=lage,
                                 max_varv=max_varv)
    protokoll = slinga.kor(modell, RB.uppgiftstext(post, skelett),
                           uppgift=post.get("task_id") or "")
    return protokoll, modell


# ---------------------------------------------------------------- rapporten

def _kav(k: int, n: int) -> str:
    return "%d av %d" % (k, n)


def grindtal(korning: Nivakorning, poster: Sequence[dict],
             grind: str) -> Tuple[int, int]:
    k = 0
    for post in poster:
        tid = post.get("task_id") or ""
        if korning.grind.get(tid, {}).get(grind) is True:
            k += 1
    return k, len(poster)


def rapport(korningar: Sequence[Nivakorning], poster: Sequence[dict],
            facitposter: Sequence[dict], strucpp: bool) -> str:
    rader: List[str] = []
    rader.append("GENERERINGSUPPGIFTER: %s av bankens %d"
                 % (_kav(len(poster), len(poster)), len(las_uppgifter())))
    rader.append("UPPGIFTER MED SPARFACIT: %s"
                 % _kav(len(facitposter), len(poster)))
    tot = Pastaenden()
    for p in facitposter:
        d = pastaenden(p)
        tot.punktkrav += d.punktkrav
        tot.invarianter += d.invarianter
        tot.invariantnamn += d.invariantnamn
        tot.flanker += d.flanker
    rader.append("MEKANISKA PASTAENDEN: %d punktkrav, %d invariantinstanser "
                 "(%d definitioner), %d flankkrav, %d totalt"
                 % (tot.punktkrav, tot.invarianter, tot.invariantnamn,
                    tot.flanker, tot.totalt))
    rader.append("")
    rader.append("GRINDAR OCH SPARFACIT PER NIVA")
    rubrik = ["%-14s" % "niva", "%-14s" % "grind 2", "%-14s" % "grind 3"]
    if strucpp:
        rubrik.append("%-14s" % "grind 1")
    rubrik += ["%-14s" % "sparfacit", "%s" % "pastaenden"]
    rader.append(" ".join(rubrik))
    for k in korningar:
        rad = ["%-14s" % k.namn,
               "%-14s" % _kav(*grindtal(k, poster, NAMN_STATISK)),
               "%-14s" % _kav(*grindtal(k, poster, NAMN_DEKLARATION))]
        if strucpp:
            rad.append("%-14s" % _kav(*grindtal(k, poster, NAMN_KOMPILERING)))
        klarade = sum(1 for u in k.spar.values() if u.godkand)
        uppfyllda = sum(u.uppfyllda for u in k.spar.values())
        rad.append("%-14s" % _kav(klarade, len(facitposter)))
        rad.append("%s" % _kav(uppfyllda, tot.totalt))
        rader.append(" ".join(rad))
    rader.append("")
    rader.append("GRIND 4 anropsvalidering: 0 av %d kord. Baslinjen skriver "
                 "ingen scenkod," % len(poster))
    rader.append("och en grind som inte kunde koras ar aldrig ett "
                 "godkannande (I3).")

    rader.append("")
    rader.append("GOLVET: ett program som styr ingenting")
    golv_klarade = 0
    golv_uppfyllda = 0
    for post in facitposter:
        st_kalla, _karta = nollprogram(post)
        u = spardom(post, st_kalla)
        golv_klarade += 1 if u.godkand else 0
        golv_uppfyllda += u.uppfyllda
    rader.append("%-14s %-14s %s" % ("noll", _kav(golv_klarade,
                                                  len(facitposter)),
                                     _kav(golv_uppfyllda, tot.totalt)))

    rader.append("")
    rader.append("SPARFACIT PER UPPGIFT OCH PASTAENDEFORM")
    rader.append("%-8s %-14s %-10s %-14s %-14s %-12s"
                 % ("uppgift", "niva", "dom", "punktkrav", "invarianter",
                    "flanker"))
    for post in facitposter:
        tid = post["task_id"]
        d = pastaenden(post)
        for k in korningar:
            u = k.spar.get(tid)
            if u is None:
                rader.append("%-8s %-14s %-10s %s"
                             % (tid, k.namn, "BYGGFEL",
                                k.fel.get(tid, "okant")))
                continue
            noll = u.tolkfel or bool(u.forgrind)
            rader.append(
                "%-8s %-14s %-10s %-14s %-14s %-12s"
                % (tid, k.namn, "GODKAND" if u.godkand else "underkand",
                   _kav(0 if noll else d.punktkrav - u.brutna_punkt,
                        d.punktkrav),
                   _kav(0 if noll else d.invarianter - u.brutna_invariant,
                        d.invarianter),
                   _kav(0 if noll else d.flanker - u.brutna_flank, d.flanker)))

    rader.append("")
    rader.append("FEL PER KLASS (spårfacit; klassningen ar "
                 "reparationsbankens SPARKLASS)")
    klasser = sorted(set(x for k in korningar for u in k.spar.values()
                         for x in u.klasser))
    rader.append("%-14s %s" % ("niva", "  ".join("%-10s" % c for c in klasser)))
    for k in korningar:
        rakn: Dict[str, int] = {}
        for u in k.spar.values():
            for c in u.klasser:
                rakn[c] = rakn.get(c, 0) + 1
        rader.append("%-14s %s   (av %d uppgifter)"
                     % (k.namn,
                        "  ".join("%-10s" % rakn.get(c, 0) for c in klasser),
                        len(k.spar)))

    rader.append("")
    rader.append("GRINDKODER SOM FALLDE, PER NIVA OCH KOD (alla uppgifter)")
    for k in korningar:
        rakn: Dict[str, int] = {}
        for tid, grindar in k.grind.items():
            for namn in (NAMN_STATISK, NAMN_DEKLARATION):
                utfall = grindar.get(namn)
                if utfall is True:
                    continue
                for kod in str(utfall).replace(",", " ").split():
                    if kod.isupper() and len(kod) > 3:
                        rakn[kod] = rakn.get(kod, 0) + 1
        rader.append("  %-14s %s" % (k.namn,
                                     ", ".join("%s %d" % (c, rakn[c])
                                               for c in sorted(rakn)) or "inga"))

    rader.append("")
    rader.append("VAR BASLINJEN GER UPP (generatorns egen redovisning, med namnare)")
    rader.append("%-14s %-16s %-16s %-16s %-16s"
                 % ("niva", "lasta rader", "lasta forregl", "bundna utg",
                    "rorda ing"))
    for k in korningar:
        rap = list(k.rapporter.values())
        olasta = sum(len(r.olasta_rader) for r in rap)
        radtot = sum(r.rader_totalt for r in rap)
        olastaf = sum(len(r.olasta_forreglingar) for r in rap)
        ftot = sum(r.forreglingar_totalt for r in rap)
        obundna = sum(len(r.obundna_utgangar) for r in rap)
        uttot = sum(r.utgangar_totalt for r in rap)
        ororda = sum(len(r.ororda_ingangar) for r in rap)
        intot = sum(r.ingangar_totalt for r in rap)
        rader.append("%-14s %-16s %-16s %-16s %-16s"
                     % (k.namn, _kav(radtot - olasta, radtot),
                        _kav(ftot - olastaf, ftot),
                        _kav(uttot - obundna, uttot),
                        _kav(intot - ororda, intot)))
    rader.append("")
    rader.append("KOSTNAD: baslinjen anvander noll tokens och noll natanrop.")
    rader.append("Genereringstid mats med --tid.")
    return "\n".join(rader)


def _sida(namn: str, korning: Nivakorning, facitposter: Sequence[dict],
          grindar: Sequence[str]) -> Par.Sida:
    utfall = dict((p["task_id"], bool(korning.spar[p["task_id"]].godkand))
                  for p in facitposter if p["task_id"] in korning.spar)
    klasser: Dict[str, int] = {}
    for u in korning.spar.values():
        for c in u.klasser:
            klasser[c] = klasser.get(c, 0) + 1
    return Par.Sida(namn, Par.signatur(facitposter, grindar), utfall, klasser)


def main(argv=None):
    ap = argparse.ArgumentParser(description="M-62: baslinjen over banken")
    ap.add_argument("--niva", action="append", choices=list(NIVAER),
                    help="kor bara den har nivan (kan upprepas)")
    ap.add_argument("--uppgift", help="bara en uppgift")
    ap.add_argument("--strucpp", help="sokvag till STruC++-CLI:t; utan den kors "
                                      "grind 1 inte alls")
    ap.add_argument("--slinga", action="store_true",
                    help="kor ocksa reparationsslingan over sparfacituppgifterna")
    ap.add_argument("--tid", action="store_true",
                    help="mat genereringstiden och determinismen over banken")
    ap.add_argument("--par", action="store_true",
                    help="skriv en parrapport mager mot spec")
    a = ap.parse_args(argv)

    alla = las_uppgifter()
    poster = genereringsuppgifter(alla)
    if a.uppgift:
        poster = [p for p in poster if p["task_id"] == a.uppgift]
        if not poster:
            raise SystemExit("ingen genereringsuppgift %s" % a.uppgift)
    facitposter = med_sparfacit(poster)

    nivaer = a.niva or list(NIVAER)
    byggkatalog = None
    tmp = None
    if a.strucpp:
        tmp = tempfile.TemporaryDirectory(prefix="baslinje-grind1-")
        byggkatalog = tmp.name

    korningar: List[Nivakorning] = []
    for niva in nivaer:
        korningar.append(kor_niva(poster, niva, strucpp_cli=a.strucpp,
                                  byggkatalog=byggkatalog))
    # Grindtillfredsställelsen som egen rad: samma generator med de två
    # växlarna på. Den mäter hur mycket av grind 3 som går att klara utan att
    # styra någonting, och den ska INTE blandas ihop med raderna ovan.
    korningar.append(kor_niva(poster, NIVA_SPEC, driv_obundna=True,
                              las_obundna=True, strucpp_cli=a.strucpp,
                              byggkatalog=byggkatalog))

    print("BASLINJEN, fas 11. INGEN SPRAKMODELL KORDES.")
    print("DOMARE: %s" % Par.signatur(
        facitposter, GRINDAR_UTAN_KOMPILATOR).kort())
    print("")
    print(rapport(korningar, poster, facitposter, bool(a.strucpp)))

    if a.par and len(korningar) >= 2:
        print("")
        vanster = _sida(korningar[0].namn, korningar[0], facitposter,
                        GRINDAR_UTAN_KOMPILATOR)
        hoger = _sida(korningar[-1].namn, korningar[-1], facitposter,
                      GRINDAR_UTAN_KOMPILATOR)
        print(Par.para(vanster, hoger).text())

    if a.tid:
        import time
        print("")
        print("GENERERINGSTID OCH DETERMINISM")
        for niva in nivaer:
            bl = Baslinje(niva=niva)
            forsta = {}
            t0 = time.perf_counter()
            for post in poster:
                try:
                    forsta[post["task_id"]] = bygg(post, bl).kropp
                except Exception as fel:      # redovisas, aldrig tyst
                    print("  byggfel %s: %s" % (post["task_id"], fel))
            t1 = time.perf_counter()
            lika = 0
            for post in poster:
                tid = post["task_id"]
                if tid not in forsta:
                    continue
                try:
                    if bygg(post, Baslinje(niva=niva)).kropp == forsta[tid]:
                        lika += 1
                except Exception as fel:
                    print("  byggfel %s: %s" % (tid, fel))
            print("  %-8s %6.1f ms for %d uppgifter, %.2f ms per uppgift, "
                  "byte-identisk vid omkorning: %s"
                  % (niva, (t1 - t0) * 1000.0, len(poster),
                     (t1 - t0) * 1000.0 / max(1, len(poster)),
                     _kav(lika, len(forsta))))

    if a.slinga:
        print("")
        print("REPARATIONSSLINGAN MED BASLINJEN SOM MODELL")
        print("%-8s %-8s %-10s %-9s %-8s %-6s %s"
              % ("uppgift", "niva", "lage", "ram", "utfall", "varv",
                 "koder utan regel"))
        for post in facitposter:
            for niva in nivaer:
                for lage in R.LAGEN:
                    for ram in RAMLAGEN:
                        protokoll, modell = kor_slinga(post, niva, lage,
                                                       ram=ram)
                        print("%-8s %-8s %-10s %-9s %-8s %-6d %s"
                              % (post["task_id"], niva, lage, ram,
                                 protokoll.utfall, len(protokoll.varv),
                                 ", ".join(modell.utan_regel[:3]) or "-"))
    if tmp is not None:
        tmp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
