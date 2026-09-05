# -*- coding: utf-8 -*-
"""Omsesidig uteslutning mellan tva skrivningar: kan bada koras i samma scan?

## Varfor modulen finns

Dubbelskrivningsgrinden (F7, `validator._doma_dubbelskrivning`) faller tva
villkorade skrivningar av samma utgang med olika varden. Regelns skal ar att
ordningen da avgor vilken som vinner. Men skalet haller bara om bada villkoren
KAN vara sanna i samma scan. M-121 matte att sex av bankens 26 egna
referenslosningar falls fast villkoren utesluter varandra:

    xAuto := ... AND SYS_AUTO AND ...;
    xHand := ... AND NOT SYS_AUTO AND ...;
    IF xAuto THEN ... ST260_LFT_DOWN := TRUE; ... END_IF;
    ST260_LFT_UP := xHand AND ST260_MAN_JOG AND NOT ST260_LFT_TOP;
    IF ST260_LFT_UP THEN ST260_LFT_DOWN := FALSE; END_IF;

Uteslutningen ar semantisk (SYS_AUTO mot NOT SYS_AUTO, genom tva
mellanvariabler) och grinden var syntaktisk. Den har modulen gor grinden
semantisk sa langt det gar att BEVISA, och inte langre.

## Vad som bevisas, och vad som inte gors

Varje skrivning bar ett SOKVAGSVILLKOR: konjunktionen av de IF/ELSIF/ELSE- och
CASE-villkor som omger den. Tva skrivningar kan koras i samma scan om
konjunktionen av deras sokvagsvillkor ar satisfierbar. Det avgors har med en
liten SAT-sokning over villkorens atomer.

Atomerna ar variabler och jamforelser. Att behandla dem som oberoende ar en
OVERSKATTNING av vad som kan hinna sant samtidigt (`x < 25.0` och `x > 35.0`
raknas som forenliga), och en overskattning ger fler fallningar, aldrig farre.
Tva undantag dar mer vetande ar sakert:

  * `x = 3` och `x = 4` for samma x kan inte bada vara sanna (likhetsgrupp).
  * `x <> y` ar NOT (x = y), `x >= y` ar NOT (x < y), `x <= y` ar NOT (x > y).

Mellanvariabler foljs: `xAuto := uttryck;` som en OVILLKORAD tilldelning fore
bada skrivningarna byts mot sitt uttryck. Ocksa `IF c THEN v := TRUE; ELSE
v := FALSE; END_IF;` raknas som `v := c`.

## Stabiliteten ar det som gor substitutionen sund

Ett namn betyder samma sak pa tva stallen bara om ingen skrivit det emellan.
Varje atom bar darfor sin UTVARDERINGSPOSITION (satsens plats i programmets
forordning), och tva forekomster av samma atom slas ihop bara om ingen av
atomens variabler tilldelas mellan positionerna. Annars ar de tva OBEROENDE
atomer, och uteslutningen gar forlorad - hellre en fallning for mycket an en
falsk gron. Samma regel galler substitutionen: `xAuto` byts mot sitt uttryck
bara om xAuto inte skrivs om mellan definitionen och anvandningen.

Den falska grona som regeln hindrar (fixtur i test_st_semantik.py):

    xD := NOT xLarm;
    IF g THEN xLarm := TRUE; END_IF;
    IF xD THEN ut := TRUE; END_IF;
    IF xLarm THEN ut := FALSE; END_IF;

En naiv substitution ger NOT xLarm AND xLarm och kallar det uteslutet. Men
xLarm skrivs pa rad 2, sa xLarm i xD:s definition och xLarm pa rad 4 ar tva
olika varden, och med g sant skrivs ut tva ganger i samma scan.

## Vad modulen INTE gor

Den foljer inte tillstand over scan-granser. `IF ST470_ARC_ON THEN
ST470_TBL_INDEX := FALSE;` efter en sekvens som satter ARC_ON i steg 2 och
slacker den i steg 4 kan aldrig kollidera med TBL_INDEX := TRUE i steg 6 - men
det vet man bara genom att spela stegmaskinen. Det ar en modellkontroll, inte en
statisk grind, och koden som beror pa det bryter mot F7-doktrinen ("skriv den
omsesidiga uteslutningen som ett villkor i koden, inte som en foljd av att
stegen rakar vara olika"). Sadana fall SKA falla har och skrivas om.

beskriver: docs/matningar/M-121_dubbelskrivning_mot_egna_referenser.md
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from . import modell as M
from .skrivare import skriv_uttryck

# ---- formler ---------------------------------------------------------------
#
# En formel ar True, False eller en tupel:
#   ("A", atom)          atom = Atom nedan
#   ("N", f)             NOT f
#   ("&", f, g)          f AND g
#   ("|", f, g)          f OR g

Formel = object

# Tak for SAT-sokningen. Over taket svarar modulen "vet inte", och vet-inte
# raknas som forenligt: grinden faller da precis som fore M-121.
MAX_ATOMER = 24

# Fler CASE-varden an sa har i en gren gors till en ogenomskinlig atom i stallet
# for en likhetsgrupp. Sunt: ogenomskinlig ar "vet inte", och vet-inte faller.
MAX_ETIKETTVARDEN = 16

_raknare = itertools.count(1)


@dataclass(frozen=True)
class Atom:
    """En atom i ett sokvagsvillkor.

    kanon   kanonisk text, samma text = samma storhet (fore stabilitetsprovet)
    varr    variablerna atomen laser; skrivs nagon av dem emellan tva
            forekomster ar forekomsterna olika atomer
    pos     utvarderingsposition i programmets forordning
    grupp   likhetsgrupp: (kanon for vanstersidan) nar atomen ar `x = literal`,
            annars None. Tva atomer i samma grupp kan inte bada vara sanna.
    """
    kanon: str
    varr: FrozenSet[str]
    pos: int
    grupp: Optional[str] = None


def och(f: Formel, g: Formel) -> Formel:
    if f is False or g is False:
        return False
    if f is True:
        return g
    if g is True:
        return f
    return ("&", f, g)


def eller(f: Formel, g: Formel) -> Formel:
    if f is True or g is True:
        return True
    if f is False:
        return g
    if g is False:
        return f
    return ("|", f, g)


def icke(f: Formel) -> Formel:
    if f is True:
        return False
    if f is False:
        return True
    if isinstance(f, tuple) and f[0] == "N":
        return f[1]
    return ("N", f)


def ogenomskinlig(pos: int) -> Formel:
    """En atom som aldrig slas ihop med nagon annan: 'vet inte'."""
    return ("A", Atom("?%d" % next(_raknare), frozenset(), pos))


# ---- ur AST ----------------------------------------------------------------

_KOMPLEMENT = {"<>": "=", ">=": "<", "<=": ">"}


def _variabler(u: M.Uttryck, ut: set) -> None:
    if isinstance(u, M.Namn):
        ut.add(u.ident.upper())
    elif isinstance(u, (M.Medlem, M.Element)):
        _variabler(u.bas, ut)
        if isinstance(u, M.Element):
            for i in u.index:
                _variabler(i, ut)
    elif isinstance(u, M.Binar):
        _variabler(u.vanster, ut)
        _variabler(u.hoger, ut)
    elif isinstance(u, M.Unar):
        _variabler(u.operand, ut)
    elif isinstance(u, M.Anrop):
        for a in u.argument:
            _variabler(a.uttryck, ut)


def _kanon(u: M.Uttryck) -> str:
    return skriv_uttryck(u).upper()


def _har_anrop(u: M.Uttryck) -> bool:
    if isinstance(u, M.Anrop):
        return True
    if isinstance(u, M.Binar):
        return _har_anrop(u.vanster) or _har_anrop(u.hoger)
    if isinstance(u, M.Unar):
        return _har_anrop(u.operand)
    if isinstance(u, (M.Medlem, M.Element)):
        return _har_anrop(u.bas)
    return False


def _literaltext(u: M.Uttryck) -> Optional[str]:
    if isinstance(u, M.Literal) and u.klass != "FALT":
        return u.text.upper()
    return None


def formel_av(u: M.Uttryck, pos: int) -> Formel:
    """Sokvagsvillkorets formel for ett BOOL-uttryck utvarderat vid `pos`.

    Allt som inte ar logik, namn eller jamforelse blir en ogenomskinlig atom:
    ett funktionsanrop kan ha sidoeffekter, och "vet inte" ska falla.
    """
    if isinstance(u, M.Literal):
        if u.klass == "BOOL":
            return bool(u.varde)
        return ogenomskinlig(pos)
    if isinstance(u, M.Unar) and u.op == "NOT":
        return icke(formel_av(u.operand, pos))
    if isinstance(u, M.Binar):
        if u.op == "AND":
            return och(formel_av(u.vanster, pos), formel_av(u.hoger, pos))
        if u.op == "OR":
            return eller(formel_av(u.vanster, pos), formel_av(u.hoger, pos))
        if u.op == "XOR":
            a = formel_av(u.vanster, pos)
            b = formel_av(u.hoger, pos)
            return eller(och(a, icke(b)), och(icke(a), b))
        if u.op in ("=", "<>", "<", ">", "<=", ">="):
            return _jamforelse(u, pos)
        return ogenomskinlig(pos)
    if isinstance(u, (M.Namn, M.Medlem, M.Element)):
        if _har_anrop(u):
            return ogenomskinlig(pos)
        varr: set = set()
        _variabler(u, varr)
        return ("A", Atom(_kanon(u), frozenset(varr), pos))
    return ogenomskinlig(pos)


def _jamforelse(u: M.Binar, pos: int) -> Formel:
    if _har_anrop(u):
        return ogenomskinlig(pos)
    op = u.op
    v, h = u.vanster, u.hoger
    neg = False
    if op in _KOMPLEMENT:
        op = _KOMPLEMENT[op]
        neg = True
    if op == ">":
        op, v, h = "<", h, v
    kv, kh = _kanon(v), _kanon(h)
    varr: set = set()
    _variabler(v, varr)
    _variabler(h, varr)
    grupp = None
    if op == "=":
        # x = 3 och 3 = x ar samma atom. Ar ena sidan en literal bildar
        # atomen en likhetsgrupp kring den andra sidan.
        if _literaltext(h) is not None and _literaltext(v) is None:
            grupp = kv
        elif _literaltext(v) is not None and _literaltext(h) is None:
            grupp = kh
            kv, kh = kh, kv
        elif kv > kh:
            kv, kh = kh, kv
    f: Formel = ("A", Atom("%s %s %s" % (kv, op, kh), frozenset(varr), pos, grupp))
    return icke(f) if neg else f


def fall_villkor(uttryck: M.Uttryck, gren: M.Fallgren, pos: int) -> Formel:
    """Villkoret for en CASE-gren: uttrycket ar lika med nagon av etiketterna."""
    varden: List[int] = []
    for e in gren.etiketter:
        varden.extend(e.varden())
    if len(varden) > MAX_ETIKETTVARDEN or _har_anrop(uttryck):
        return ogenomskinlig(pos)
    kanon = _kanon(uttryck)
    varr: set = set()
    _variabler(uttryck, varr)
    f: Formel = False
    for v in varden:
        f = eller(f, ("A", Atom("%s = %d" % (kanon, v), frozenset(varr), pos, kanon)))
    return f


# ---- miljo: definitioner av mellanvariabler ---------------------------------

@dataclass(frozen=True)
class Definition:
    """`namn := uttryck` som en OVILLKORAD sats pa position `pos`.

    `negerad` bar IF/ELSE-formen `IF c THEN v := FALSE; ELSE v := TRUE;`.
    """
    pos: int
    uttryck: M.Uttryck
    negerad: bool = False
    slut: int = 0        # sista positionen i satsens eget deltrad

    def __post_init__(self):
        if self.slut < self.pos:
            object.__setattr__(self, "slut", self.pos)


def definition_av(s: M.Sats, pos: int, slut: Optional[int] = None
                  ) -> Optional[Tuple[str, Definition]]:
    """Namnet och definitionen om satsen ar en ren tilldelning till ett namn,
    eller en IF/ELSE som satter samma namn till TRUE i ena grenen och FALSE i
    den andra. Annars None.

    `slut` ar sista positionen i satsens deltrad: IF/ELSE-formens egna tva
    tilldelningar ligger dar, och de far inte raknas som omskrivningar av
    namnet efter definitionen."""
    slut = pos if slut is None else slut
    if isinstance(s, M.Tilldelning) and isinstance(s.mal, M.Namn):
        return s.mal.ident.upper(), Definition(pos, s.uttryck, slut=slut)
    if isinstance(s, M.Om) and len(s.grenar) == 1 and s.annars is not None:
        a = _enda_literaltilldelning(s.grenar[0].satser)
        b = _enda_literaltilldelning(s.annars)
        if a and b and a[0] == b[0] and a[1] != b[1]:
            return a[0], Definition(pos, s.grenar[0].villkor, negerad=not a[1],
                                    slut=slut)
    return None


def _enda_literaltilldelning(satser) -> Optional[Tuple[str, bool]]:
    rena = [x for x in satser if not isinstance(x, M.Kommentar)]
    if len(rena) != 1:
        return None
    s = rena[0]
    if (isinstance(s, M.Tilldelning) and isinstance(s.mal, M.Namn)
            and isinstance(s.uttryck, M.Literal) and s.uttryck.klass == "BOOL"):
        return s.mal.ident.upper(), bool(s.uttryck.varde)
    return None


# ---- domaren ---------------------------------------------------------------

class Uteslutning(object):
    """Avgor om tva sokvagsvillkor kan vara sanna i samma scan.

    `skrivpositioner`: variabelnamn -> sorterade positioner dar variabeln
    tilldelas (tilldelningar, FB-anrop, utbindningar, slingvariabler).
    """

    def __init__(self, skrivpositioner: Dict[str, Sequence[int]]):
        self.skriv = dict((k.upper(), tuple(sorted(v)))
                          for k, v in skrivpositioner.items())

    # -- stabilitet --

    def stabil(self, variabler: FrozenSet[str], fran: int, till: int) -> bool:
        """Sant om ingen av variablerna tilldelas pa en position i (fran, till]."""
        if fran > till:
            fran, till = till, fran
        for v in variabler:
            for p in self.skriv.get(v, ()):
                if fran < p <= till:
                    return False
        return True

    # -- substitution --

    def substituera(self, f: Formel, miljo: Dict[str, Definition],
                    djup: int = 0, kedja: FrozenSet[str] = frozenset()) -> Formel:
        if f is True or f is False:
            return f
        slag = f[0]
        if slag == "N":
            return icke(self.substituera(f[1], miljo, djup, kedja))
        if slag in ("&", "|"):
            a = self.substituera(f[1], miljo, djup, kedja)
            b = self.substituera(f[2], miljo, djup, kedja)
            return och(a, b) if slag == "&" else eller(a, b)
        atom: Atom = f[1]
        if djup >= 8 or len(atom.varr) != 1 or atom.kanon not in atom.varr:
            return f
        namn = atom.kanon
        d = miljo.get(namn)
        if d is None or namn in kedja or d.pos >= atom.pos:
            return f
        # Definitionen galler vid atom.pos bara om namnet inte skrivits om
        # mellan definitionen (hela dess deltrad) och anvandningen.
        if not self.stabil(frozenset([namn]), d.slut, atom.pos):
            return f
        inre = formel_av(d.uttryck, d.pos)
        if d.negerad:
            inre = icke(inre)
        return self.substituera(inre, miljo, djup + 1, kedja | {namn})

    # -- sammanslagning av atomer over positioner --

    def _numrera(self, f: Formel) -> Tuple[Formel, Dict[int, Atom], Dict[str, List[int]]]:
        """Byt Atom-objekt mot heltal. Tva forekomster med samma kanon blir
        samma heltal bara om atomen ar stabil mellan deras positioner."""
        atomer: List[Atom] = []
        _samla(f, atomer)
        per_kanon: Dict[str, List[Atom]] = {}
        for a in atomer:
            per_kanon.setdefault(a.kanon, []).append(a)
        nummer: Dict[Tuple[str, int], int] = {}
        beskrivning: Dict[int, Atom] = {}
        grupper: Dict[str, List[int]] = {}
        n = 0
        for kanon, lista in per_kanon.items():
            lista = sorted(set(lista), key=lambda a: a.pos)
            klass_start = None
            for a in lista:
                if klass_start is None or not self.stabil(a.varr, klass_start.pos, a.pos):
                    klass_start = a
                    n += 1
                    beskrivning[n] = a
                    if a.grupp is not None:
                        grupper.setdefault("%s@%d" % (a.grupp, a.pos), []).append(n)
                nummer[(kanon, a.pos)] = n
        # Likhetsgrupper maste ocksa respektera stabiliteten: `steg = 1` vid
        # pos 10 och `steg = 2` vid pos 30 utesluter varandra bara om steg inte
        # skrivs emellan. Grupperna slas ihop over positioner pa samma satt.
        grupper = self._sla_ihop_grupper(grupper, beskrivning)
        return _byt(f, nummer), beskrivning, grupper

    def _sla_ihop_grupper(self, grupper: Dict[str, List[int]],
                          beskrivning: Dict[int, Atom]) -> Dict[str, List[int]]:
        per_namn: Dict[str, List[Tuple[int, int]]] = {}
        for nyckel, nummer in grupper.items():
            namn = nyckel.rsplit("@", 1)[0]
            for n in nummer:
                per_namn.setdefault(namn, []).append((beskrivning[n].pos, n))
        ut: Dict[str, List[int]] = {}
        for namn, lista in per_namn.items():
            lista.sort()
            start_pos = None
            k = 0
            for pos, n in lista:
                varr = beskrivning[n].varr
                if start_pos is None or not self.stabil(varr, start_pos, pos):
                    start_pos = pos
                    k += 1
                ut.setdefault("%s#%d" % (namn, k), []).append(n)
        return dict((k, v) for k, v in ut.items() if len(v) >= 2)

    # -- SAT --

    def forenliga(self, a: Formel, b: Formel,
                  miljo_a: Optional[Dict[str, Definition]] = None,
                  miljo_b: Optional[Dict[str, Definition]] = None
                  ) -> Tuple[bool, Optional[Dict[str, bool]]]:
        """(kan bada vara sanna samtidigt?, vittne eller None).

        Vittnet ar en tilldelning av atomer (kanon -> varde) som gor bada
        sanna. Over MAX_ATOMER svaras (True, None): vet inte, alltsa faller.

        Varje villkor substitueras med SIN miljo: definitionerna som galler
        fore den sats som bar skrivningen. En definition mellan de tva
        satserna (L-05: `ST260_LFT_UP := xHand AND ...` pa rad 102, mellan
        sekvensen pa rad 62 och forreglingen pa rad 106) galler for den senare
        skrivningen och ar det som gor uteslutningen synlig.
        """
        f = och(self.substituera(a, miljo_a or {}),
                self.substituera(b, miljo_b if miljo_b is not None else (miljo_a or {})))
        if f is True:
            return True, {}
        if f is False:
            return False, None
        g, beskrivning, grupper = self._numrera(f)
        if len(beskrivning) > MAX_ATOMER:
            return True, None
        grupp_av: Dict[int, List[int]] = {}
        for medlemmar in grupper.values():
            for n in medlemmar:
                grupp_av[n] = medlemmar
        modell = _sat(g, {}, grupp_av)
        if modell is None:
            return False, None
        vittne = dict((beskrivning[n].kanon, v) for n, v in modell.items())
        return True, vittne


def _samla(f: Formel, ut: List[Atom]) -> None:
    if f is True or f is False:
        return
    if f[0] == "A":
        ut.append(f[1])
    elif f[0] == "N":
        _samla(f[1], ut)
    else:
        _samla(f[1], ut)
        _samla(f[2], ut)


def _byt(f: Formel, nummer: Dict[Tuple[str, int], int]) -> Formel:
    if f is True or f is False:
        return f
    if f[0] == "A":
        return ("a", nummer[(f[1].kanon, f[1].pos)])
    if f[0] == "N":
        return ("N", _byt(f[1], nummer))
    return (f[0], _byt(f[1], nummer), _byt(f[2], nummer))


def _forenkla(f: Formel, t: Dict[int, bool]) -> Formel:
    if f is True or f is False:
        return f
    slag = f[0]
    if slag == "a":
        v = t.get(f[1])
        return f if v is None else v
    if slag == "N":
        return icke(_forenkla(f[1], t))
    a = _forenkla(f[1], t)
    b = _forenkla(f[2], t)
    return och(a, b) if slag == "&" else eller(a, b)


def _forsta_atom(f: Formel) -> Optional[int]:
    if f is True or f is False:
        return None
    if f[0] == "a":
        return f[1]
    if f[0] == "N":
        return _forsta_atom(f[1])
    return _forsta_atom(f[1]) or _forsta_atom(f[2])


def _sat(f: Formel, t: Dict[int, bool],
         grupp_av: Dict[int, List[int]]) -> Optional[Dict[int, bool]]:
    f = _forenkla(f, t)
    if f is True:
        return t
    if f is False:
        return None
    a = _forsta_atom(f)
    for v in (True, False):
        if v and any(t.get(m) for m in grupp_av.get(a, ()) if m != a):
            continue
        t2 = dict(t)
        t2[a] = v
        r = _sat(f, t2, grupp_av)
        if r is not None:
            return r
    return None


def vittnestext(vittne: Optional[Dict[str, bool]], max_atomer: int = 5) -> str:
    """'t.ex. nar SYS_AUTO ar TRUE och STEG = 3 ar TRUE', for grindens dom."""
    if not vittne:
        return ""
    delar = []
    for kanon, v in sorted(vittne.items()):
        if kanon.startswith("?"):
            continue
        delar.append("%s ar %s" % (kanon, "TRUE" if v else "FALSE"))
        if len(delar) >= max_atomer:
            break
    if not delar:
        return ""
    return " (t.ex. nar %s)" % " och ".join(delar)
