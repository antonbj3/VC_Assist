# -*- coding: utf-8 -*-
"""Steg-kedjebyggare: en lista steg in, en färdig CASE-sekvens ut.

Det här är mönstret som nästan all virtuell driftsättning består av, och det
är också där handskriven kod går sönder på samma tre sätt varje gång:

1. **Timern behåller sitt Q.** Ett funktionsblock som inte anropas i en scan
   behåller sina utgångar. Anropas TON:en bara inuti sitt eget steg är Q
   fortfarande sant när steget kommer tillbaka, och sekvensen hoppar vidare
   direkt. Därför anropas varje timer **varje scan**, utanför CASE, med
   `IN := (steg = N)`.
2. **Utgångarna hänger kvar vid nödstopp.** Nödstoppsgrenen nollar varje
   utgång som någon steg-verkan sätter. Listan härleds ur stegen, den skrivs
   inte för hand, så den kan inte bli ofullständig.
3. **Ett steg utan väg ut.** Ett steg måste ha framåtvillkor eller uppehåll,
   annars vägrar byggaren. Ett steg som kan bli stående är inte en sekvens.

Modellen skriver bara stegen. Deklarationerna kommer in färdiga ur
signalkartan och byggaren rör dem inte (invariant I10). Nödstoppstaggen läses,
aldrig skrivs — den hör till säkerhets-PLC:n (I15).

Källa: docs/spec/60_plc.md, docs/spec/70_faser.md fas 7, docs/spec/90_invarianter.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import modell as M
from . import typer as T
from .lexer import tolka_tidliteral
from .skrivare import skriv_pou

# Vilosteget är 0 så att en nollställd tillståndsvariabel — vid uppstart och
# efter nödstopp — alltid hamnar i vila. Konvention, ingen mätning.
STEG_VILA = 0
# Steg numreras i tior så att ett steg kan skjutas in utan att numrera om de
# andra. Klassisk PLC-konvention, ingen mätning.
STEG_OKNING = 10
# Felsteget ligger långt ovanför arbetsstegen så att det aldrig kolliderar med
# ett insskjutet steg. Konvention, ingen mätning.
STEG_FEL = 900

_IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class SekvensFel(Exception):
    """Byggaren vägrar bygga något som inte går att lita på."""


@dataclass(frozen=True)
class Steg:
    """Ett steg i kedjan.

    verkan     satser som körs medan steget är aktivt (varje scan)
    villkor    framåtvillkor; None betyder att bara uppehållet styr
    uppehall   TIME-literal: minsta tid i steget innan villkoret får släppa
    tidsgrans  TIME-literal: lämnas steget inte inom den tiden går sekvensen
               till felsteget och larmet går högt
    """

    namn: str
    verkan: Tuple[M.Sats, ...] = ()
    villkor: Optional[M.Uttryck] = None
    uppehall: Optional[str] = None
    tidsgrans: Optional[str] = None


@dataclass(frozen=True)
class Sekvens:
    namn: str
    steg: Tuple[Steg, ...]
    start: M.Uttryck
    nodstopp: str
    deklarationer: Tuple[M.Varblock, ...] = ()
    tillstandsvar: str = "steg"
    larmvar: str = "larm"


def _tid(literal: str, vad: str) -> M.Literal:
    ok, ms, skal = tolka_tidliteral(literal)
    if not ok:
        raise SekvensFel("%s: %s is not a valid TIME literal (%s)"
                         % (vad, literal, skal))
    return M.Literal("TID", literal, ms)


def _namn(u: str) -> M.Namn:
    return M.Namn(u)


def _heltal(v: int) -> M.Literal:
    return M.Literal("HELTAL", str(v), v)


def _sant(v: bool) -> M.Literal:
    return M.Literal("BOOL", "TRUE" if v else "FALSE", v)


def _nolluttryck(typ: T.Typ) -> M.Literal:
    """Uttrycket som stänger av en utgång av den här typen.

    Texten hämtas ur typer.nollvarde_text, som är enda stället där "avstängt"
    är definierat. Vet den inte, kastar den — en utgång vi inte kan nolla får
    inte tyst hoppas över i nödstoppsgrenen.
    """
    text = T.nollvarde_text(typ)
    if isinstance(typ, T.Strang):
        return M.Literal("STRANG", text, "")
    namn = typ.namn
    if namn == "BOOL":
        return M.Literal("BOOL", text, False)
    if namn == "TIME":
        return M.Literal("TID", text, 0.0)
    if namn in T.FLYT_MANTISSA:
        return M.Literal("REAL", text, 0.0)
    return M.Literal("HELTAL", text, 0)


def _skrivmal_i(satser, ut: List[str]):
    for s in satser:
        if isinstance(s, M.Tilldelning):
            rot = s.mal
            while isinstance(rot, (M.Medlem, M.Element)):
                rot = rot.bas
            if isinstance(rot, M.Namn):
                ut.append(rot.ident)
        elif isinstance(s, M.Anropssats):
            for a in s.anrop.argument:
                if a.ut and isinstance(a.uttryck, M.Namn):
                    ut.append(a.uttryck.ident)
        elif isinstance(s, M.Om):
            for g in s.grenar:
                _skrivmal_i(g.satser, ut)
            if s.annars is not None:
                _skrivmal_i(s.annars, ut)
        elif isinstance(s, M.Fall):
            for g in s.grenar:
                _skrivmal_i(g.satser, ut)
            if s.annars is not None:
                _skrivmal_i(s.annars, ut)
        elif isinstance(s, (M.ForSats, M.Medan, M.Upprepa)):
            _skrivmal_i(s.satser, ut)
    return ut


class _Bygge(object):
    def __init__(self, spec: Sekvens):
        self.spec = spec
        self.dekl: Dict[str, Tuple[str, M.Deklaration]] = {}
        for b in spec.deklarationer:
            for d in b.deklarationer:
                nyckel = d.namn.upper()
                if nyckel in self.dekl:
                    raise SekvensFel("%s is declared twice in the signal map"
                                     % d.namn)
                self.dekl[nyckel] = (b.sort, d)
        self._kontrollera_spec()
        self.nummer = dict((i, STEG_VILA + STEG_OKNING * (i + 1))
                           for i in range(len(spec.steg)))
        self.timrar: List[Tuple[str, int, M.Literal]] = []

    # ---- kontroller före bygget -----------------------------------------

    def _kontrollera_spec(self):
        s = self.spec
        if not _IDENT.match(s.namn):
            raise SekvensFel("%r does not work as a POU name in ST" % s.namn)
        if not s.steg:
            raise SekvensFel("a sequence without steps is not a sequence")
        for namn in (s.tillstandsvar, s.larmvar):
            if not _IDENT.match(namn):
                raise SekvensFel("%r does not work as a variable name in ST" % namn)
        sedda = set()
        for st in s.steg:
            if not _IDENT.match(st.namn):
                raise SekvensFel("the step name %r must be an ASCII name; it "
                                 "becomes both a comment and a timer name" % st.namn)
            if st.namn.upper() in sedda:
                raise SekvensFel("two steps are named %s" % st.namn)
            sedda.add(st.namn.upper())
            if st.villkor is None and st.uppehall is None:
                raise SekvensFel("the step %s has neither a forward condition nor "
                                 "a dwell time and can get stuck" % st.namn)
        nod = self.dekl.get(s.nodstopp.upper())
        if nod is None:
            raise SekvensFel("the emergency-stop tag %s is not in the declarations"
                             % s.nodstopp)
        if nod[1].typ != T.BOOL:
            raise SekvensFel("the emergency-stop tag %s must be BOOL, not %s"
                             % (s.nodstopp, nod[1].typ.st()))

    # ---- bygget ----------------------------------------------------------

    def bygg(self) -> M.Pou:
        kropp = []
        kropp.extend(self._stegkropp_forberedelse())
        grenar = [self._vilogren()]
        for i, st in enumerate(self.spec.steg):
            grenar.append(self._stegren(i, st))
        grenar.append(self._felgren())
        fall = M.Fall(_namn(self.spec.tillstandsvar), tuple(grenar),
                      (M.Kommentar("okant tillstand: tillbaka till vila"),
                       M.Tilldelning(_namn(self.spec.tillstandsvar),
                                     _heltal(STEG_VILA))))
        kropp.append(M.Om(
            (M.Gren(M.Unar("NOT", _namn(self.spec.nodstopp)),
                    self._nodstoppsgren()),),
            (fall,)))
        block = list(self.spec.deklarationer) + [self._internt_block()]
        return M.Pou("PROGRAM", self.spec.namn, tuple(block), tuple(kropp))

    def _stegkropp_forberedelse(self):
        """Timeranropen. Ligger före CASE och körs varje scan, med flit."""
        rader = [M.Kommentar(
            "Timrarna anropas varje scan aven i steg de inte hor till. En TON "
            "som inte anropas behaller sitt Q, och da skulle nasta besok i "
            "steget slappa igenom direkt.")]
        for i, st in enumerate(self.spec.steg):
            n = self.nummer[i]
            if st.uppehall:
                rader.append(self._timeranrop(self._urnamn(st), n,
                                              _tid(st.uppehall,
                                                   "the dwell time in %s" % st.namn)))
            if st.tidsgrans:
                rader.append(self._timeranrop(self._gransnamn(st), n,
                                              _tid(st.tidsgrans,
                                                   "the time limit in %s" % st.namn)))
        return rader

    def _timeranrop(self, namn: str, stegnr: int, tid: M.Literal):
        self.timrar.append((namn, stegnr, tid))
        return M.Anropssats(M.Anrop(namn, (
            M.Argument(M.Binar("=", _namn(self.spec.tillstandsvar),
                               _heltal(stegnr)), "IN"),
            M.Argument(tid, "PT"))))

    def _urnamn(self, st: Steg) -> str:
        return self._unikt("ur_%s" % st.namn.lower())

    def _gransnamn(self, st: Steg) -> str:
        return self._unikt("grans_%s" % st.namn.lower())

    def _unikt(self, namn: str) -> str:
        if namn.upper() in self.dekl:
            raise SekvensFel("the builder needs the name %s for a timer, but it "
                             "already exists in the signal map" % namn)
        return namn

    def _vilogren(self) -> M.Fallgren:
        forsta = self.nummer[0]
        return M.Fallgren(
            (M.Etikett(STEG_VILA),),
            (M.Kommentar("vila: vantar pa startvillkoret"),
             M.Om((M.Gren(self.spec.start,
                          (M.Tilldelning(_namn(self.spec.tillstandsvar),
                                         _heltal(forsta)),)),))))

    def _stegren(self, i: int, st: Steg) -> M.Fallgren:
        nasta = self.nummer[i + 1] if i + 1 < len(self.spec.steg) else STEG_VILA
        satser = [M.Kommentar("steg %s" % st.namn)]
        satser.extend(st.verkan)
        framat = st.villkor
        if st.uppehall:
            klar = M.Medlem(_namn(self._urnamn(st)), "Q")
            framat = klar if framat is None else M.Binar("AND", framat, klar)
        grenar = [M.Gren(framat, (M.Tilldelning(_namn(self.spec.tillstandsvar),
                                                _heltal(nasta)),))]
        if st.tidsgrans:
            grenar.append(M.Gren(
                M.Medlem(_namn(self._gransnamn(st)), "Q"),
                (M.Tilldelning(_namn(self.spec.larmvar), _sant(True)),
                 M.Tilldelning(_namn(self.spec.tillstandsvar), _heltal(STEG_FEL)))))
        satser.append(M.Om(tuple(grenar)))
        return M.Fallgren((M.Etikett(self.nummer[i]),), tuple(satser))

    def _felgren(self) -> M.Fallgren:
        return M.Fallgren(
            (M.Etikett(STEG_FEL),),
            (M.Kommentar("felsteg: staende larm tills nodstoppskedjan brutits "
                         "och aterstallts"),
             M.Tilldelning(_namn(self.spec.larmvar), _sant(True))))

    def _nodstoppsgren(self):
        satser = [M.Kommentar("nodstopp: sekvensen till vila och alla utgangar "
                              "som stegen satter nollas"),
                  M.Tilldelning(_namn(self.spec.tillstandsvar), _heltal(STEG_VILA)),
                  M.Tilldelning(_namn(self.spec.larmvar), _sant(False))]
        for namn in self._utgangar_i_stegen():
            sort, d = self.dekl[namn.upper()]
            satser.append(M.Tilldelning(_namn(d.namn), _nolluttryck(d.typ)))
        return tuple(satser)

    def _utgangar_i_stegen(self) -> List[str]:
        """Namnen stegen skriver till, i den ordning de först dyker upp.

        Ordningen är avsiktligt inte sorterad utan följer stegen: det gör
        nödstoppsgrenen läsbar bredvid sekvensen, och den är lika
        deterministisk.
        """
        rakning = []
        for st in self.spec.steg:
            _skrivmal_i(st.verkan, rakning)
        ut = []
        for namn in rakning:
            if namn.upper() in (u.upper() for u in ut):
                continue
            post = self.dekl.get(namn.upper())
            if post is None:
                raise SekvensFel(
                    "the step writes to %s which is not in the declarations; "
                    "tags come from the signal map and are never made up" % namn)
            if post[1].skyddad:
                raise SekvensFel(
                    "%s is marked {SAKERHET} and must not be written by generated "
                    "code (invariant I15)" % namn)
            ut.append(post[1].namn)
        return ut

    def _internt_block(self) -> M.Varblock:
        dekl = [M.Deklaration(self.spec.tillstandsvar, T.Elementar("INT"),
                              _heltal(STEG_VILA), kommentar="sekvensens tillstand")]
        if self.spec.larmvar.upper() not in self.dekl:
            dekl.append(M.Deklaration(self.spec.larmvar, T.BOOL,
                                      kommentar="hogt nar ett steg gatt over tiden"))
        for namn, stegnr, _tid in self.timrar:
            dekl.append(M.Deklaration(namn, T.Blocktyp("TON"),
                                      kommentar="steg %d" % stegnr))
        if self.spec.tillstandsvar.upper() in self.dekl:
            raise SekvensFel("the state variable %s collides with the signal map"
                             % self.spec.tillstandsvar)
        return M.Varblock("VAR", tuple(dekl))


def bygg(spec: Sekvens) -> M.Pou:
    return _Bygge(spec).bygg()


def bygg_text(spec: Sekvens) -> str:
    return skriv_pou(bygg(spec))
