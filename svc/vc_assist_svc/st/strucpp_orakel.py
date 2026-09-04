# -*- coding: utf-8 -*-
"""Ett andra öga på ST-semantiken: STruC++:s egen körbara REPL.

**Det här är inte tjänstelager.** Filen startar en kompilator och en byggd
binär, precis som `plc/matning.py` gör, och den ska inte dras in i något som
körs i drift. Den finns för att svara på en fråga `tolk.py` själv ställer i sin
docstring:

> Två motorer på samma facit kan drifta isär, och det är precis vad
> `M-45` säger ska mätas när kedjan står.

Kedjan till OpenPLC kräver ett npm-paket som inte längre finns på maskinen
(M-48). Men STruC++:s CLI kan bygga ett ST-program till en **körbar med REPL**:

    strucpp <in.st> -o <ut.cpp> --build

Den binären tar `set <PROGRAM>.<VAR> <värde>`, `run <N>` och
`get <PROGRAM>.<VAR>`, och kör med 20 ms cykel — **samma period som
`tolk.SCAN_MS`**, vilket är hela förutsättningen för att spåren ska gå att
lägga bredvid varandra.

## Varför den här jämförelsen är värd mer än den ser ut

Bänkens facit döms i dag av vår egen tolk. Om tolken har fel om ST-semantiken
har facit fel, och hela bänken mäter vår egen missuppfattning med stor
precision. Ett facit som dömer med samma motor som producerade det är
tautologiskt; det här är den andra motorn.

Den är inte OpenPLC. Den bevisar ingenting om runtimen, om scancykelns
kanter i drift eller om fältbussen. Den bevisar att två oberoende
implementationer av ST-semantiken är överens — eller pekar ut exakt var de
inte är det.

## Namnen versaliseras

REPL:en känner `PRESS.GIVARE`, inte `Press.givare`. ST är skiftlägesokänsligt,
och båda motorerna behandlar det så; jämförelsen görs på versaler.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# REPL:ens cykel, avläst ur dess egen startrad ("Cycle: 20ms"). Talet
# KONTROLLERAS mot tolkens scan_ms i `jamfor`; det antas aldrig.
_CYKELRAD = re.compile(r"Cycle:\s*(\d+)\s*ms")
_SVARSRAD = re.compile(r"^([A-Za-z0-9_.]+)\s*:\s*\S+\s*=\s*(.+)$")


class Orakelfel(Exception):
    """Oraklet gick inte att bygga eller driva."""


def _bool_ur(text: str) -> object:
    t = text.strip()
    if t.upper() in ("TRUE", "FALSE"):
        return t.upper() == "TRUE"
    try:
        if "." in t or "e" in t.lower():
            return float(t)
        return int(t)
    except ValueError:
        return t


def _till_repl(varde: object) -> str:
    if isinstance(varde, bool):
        return "TRUE" if varde else "FALSE"
    return str(varde)


@dataclass
class Steg:
    """Ett steg i spåret: sätt dessa, kör så många scan, läs dessa."""

    satt: Dict[str, object] = field(default_factory=dict)
    scan: int = 1
    las: Tuple[str, ...] = ()


@dataclass
class Avvikelse:
    steg: int
    namn: str
    tolken: object
    oraklet: object

    def __str__(self) -> str:
        return ("steg %d: %s — tolken sa %r, oraklet sa %r"
                % (self.steg, self.namn, self.tolken, self.oraklet))


class Orakel(object):
    """En byggd ST-binär som går att driva stegvis."""

    def __init__(self, binar: str, program: str, cykel_ms: float):
        self.binar = binar
        self.program = program.upper()
        self.cykel_ms = cykel_ms

    @staticmethod
    def bygg(kalla: str, program: str, strucpp_cli: str,
             katalog: Optional[str] = None,
             tidsgrans: float = 600.0) -> "Orakel":
        if not os.path.exists(strucpp_cli):
            raise Orakelfel("hittar inte STruC++ på %s" % strucpp_cli)
        katalog = katalog or tempfile.mkdtemp(prefix="orakel_")
        os.makedirs(katalog, exist_ok=True)
        stfil = os.path.join(katalog, "p.st")
        with open(stfil, "w", encoding="ascii", newline="\n") as f:
            f.write(kalla)
        try:
            k = subprocess.run(
                [strucpp_cli, stfil, "-o", os.path.join(katalog, "p.cpp"),
                 "--build"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=tidsgrans)
        except OSError as fel:
            raise Orakelfel("kunde inte starta %s: %s" % (strucpp_cli, fel))
        except subprocess.TimeoutExpired:
            raise Orakelfel("bygget svarade inte inom %.0f s" % tidsgrans)
        if k.returncode != 0:
            raise Orakelfel("bygget foll (kod %d):\n%s"
                            % (k.returncode,
                               k.stdout.decode("utf-8", "replace").strip()))
        binar = os.path.join(katalog, "p")
        if not os.path.exists(binar):
            raise Orakelfel("bygget sa lyckat men lamnade ingen binar pa %s"
                            % binar)
        cykel = _las_cykel(binar)
        return Orakel(binar, program, cykel)

    def kor(self, spar: Sequence[Steg]) -> List[Dict[str, object]]:
        """Driv spåret och lämna en avläsning per steg.

        Hela spåret körs i EN process. En binär per steg hade nollställt
        funktionsblockens minne mellan stegen, och då hade varje timer och
        varje flank mätt fel sak.
        """
        rader: List[str] = []
        for steg in spar:
            for namn, varde in sorted(steg.satt.items()):
                rader.append("set %s.%s %s"
                             % (self.program, namn.upper(), _till_repl(varde)))
            rader.append("run %d" % max(int(steg.scan), 1))
            for namn in steg.las:
                rader.append("get %s.%s" % (self.program, namn.upper()))
            rader.append("echo_marker_%d" % len(rader))
        rader.append("quit")
        utdata = self._driv("\n".join(rader) + "\n")
        return self._plocka(utdata, spar)

    def _driv(self, indata: str) -> str:
        try:
            k = subprocess.run([self.binar], input=indata.encode("ascii"),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=300.0)
        except OSError as fel:
            raise Orakelfel("kunde inte starta oraklet: %s" % fel)
        except subprocess.TimeoutExpired:
            raise Orakelfel("oraklet svarade inte inom 300 s")
        return k.stdout.decode("utf-8", "replace")

    def _plocka(self, utdata: str, spar: Sequence[Steg]) -> List[Dict[str, object]]:
        """Läser svaren i ordning och delar dem på `run`-raderna.

        Svaren räknas mot spårets EGEN förväntan: saknas ett svar är det ett
        fel, inte ett tomt värde. Ett orakel som tiger får aldrig se ut som ett
        orakel som höll med.
        """
        svar: List[Tuple[str, object]] = []
        korningar = 0
        gransar: List[int] = []
        for rad in utdata.splitlines():
            if rad.startswith("Executed "):
                korningar += 1
                gransar.append(len(svar))
                continue
            if rad.startswith("Unknown variable"):
                raise Orakelfel("oraklet kande inte igen en variabel: %s" % rad)
            m = _SVARSRAD.match(rad.strip())
            if m:
                svar.append((m.group(1).split(".", 1)[-1], _bool_ur(m.group(2))))
        if korningar != len(spar):
            raise Orakelfel("spåret har %d steg men oraklet korde %d"
                            % (len(spar), korningar))
        ut: List[Dict[str, object]] = []
        for i, steg in enumerate(spar):
            start = gransar[i]
            slut = gransar[i + 1] if i + 1 < len(gransar) else len(svar)
            avlast = dict(svar[start:slut])
            saknade = [n.upper().split(".", 1)[-1] for n in steg.las
                       if n.upper().split(".", 1)[-1] not in avlast]
            if saknade:
                raise Orakelfel("steg %d: oraklet svarade inte pa %s"
                                % (i, ", ".join(saknade)))
            ut.append(avlast)
        return ut


def _las_cykel(binar: str) -> float:
    k = subprocess.run([binar], input=b"quit\n", stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60.0)
    text = k.stdout.decode("utf-8", "replace")
    m = _CYKELRAD.search(text)
    if not m:
        raise Orakelfel("hittade ingen cykelrad i orakelts start:\n%s"
                        % text[:400])
    return float(m.group(1))


def jamfor(kalla: str, program: str, spar: Sequence[Steg], strucpp_cli: str,
           signaler: Optional[Dict[str, str]] = None,
           katalog: Optional[str] = None) -> List[Avvikelse]:
    """Kör samma spår genom tolken och genom oraklet; lämna skillnaderna.

    Fäller om motorerna inte kör samma period. Två spår på olika tidsrutnät går
    inte att lägga bredvid varandra, och att jämföra dem ändå hade gett en
    avvikelselista som mäter rutnätet i stället för semantiken.
    """
    from .tolk import Tolk

    orakel = Orakel.bygg(kalla, program, strucpp_cli, katalog)
    tolk = Tolk(kalla, signaler=signaler or {})
    if abs(orakel.cykel_ms - tolk.scan_ms) > 1e-9:
        raise Orakelfel("oraklet kor %.1f ms och tolken %.1f ms; sparen ligger "
                        "inte pa samma rutnat" % (orakel.cykel_ms, tolk.scan_ms))

    orakelsvar = orakel.kor(spar)

    avvikelser: List[Avvikelse] = []
    for i, steg in enumerate(spar):
        for namn, varde in sorted(steg.satt.items()):
            tolk.satt(namn, varde)
        for _ in range(max(int(steg.scan), 1)):
            tolk.scan()
        for namn in steg.las:
            nyckel = namn.upper().split(".", 1)[-1]
            mitt = tolk.las(namn)
            deras = orakelsvar[i].get(nyckel)
            if _skiljer(mitt, deras):
                avvikelser.append(Avvikelse(i, namn, mitt, deras))
    return avvikelser


def _skiljer(a: object, b: object) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) != bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) > 1e-6
    return a != b
