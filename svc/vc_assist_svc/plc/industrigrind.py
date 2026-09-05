# -*- coding: utf-8 -*-
"""Grind 3b: den industriella minimiformen - tidsvakt, larm och forregling.

## Varfor modulen finns

`M-89` matte projektets skarpaste hal. En modell som fick ett inspelat
I/O-spar fran normalproduktion skrev kod som **ateger inspelningen** och andar
fick **0 av 2** mot manniskans facit. Bristerna var inte logikfel: ingen
tidsovervakning av indexet, inget larm nar klamman slapper mitt i ett index,
ingen kontroll av att lagesgivaren ligger inom arbetsomradet.

Det ar inte ett bankproblem utan ett produktfel. Koden ser ratt ut, kor ratt,
och saknar allt som gor den industriell:

* en station som fastnar star tyst for evigt,
* ett fel har ingen larmutgang,
* tva stalldon som kan kollidera saknar forregling.

Grind 1-3 fangar inget av det: texten kompilerar, taggarna finns i kartan,
och ingen utgang skrivs tva ganger. Ogat fangar det bara om stimulit rakar
provocera just det tillstandet - och `M-89` matte att ett produktionsspar
aldrig gor det (`EMG_OK` gick aldrig till 0 i nagot av fyra spar).

## Varfor kraven lases UR UPPGIFTEN och inte ur en handskriven lista

Samma skal som `forhandsregler.py`: en handskriven ordlista over "korrekta
industriprinciper" glider isar fran koden. Kraven lases darfor mekaniskt ur
uppgiftens egna falt:

    control.signals      vilka namn som ar don, givare och larmutgangar
    control.interlocks   uppgiftens egna forreglingar, i klartext
    failure_modes        vilka vantningar uppgiften sjalv kraver tidsovervakade
    facit_spar.invarianter  samma forreglingar i maskinlasbar form

Alla fyra ar MANNISKANS text om anlaggningen, inte kod harledd ur koden som
doms. `docs/spec/85_bankkontraktet.md` §2 tillater dem darfor som facitkalla.

## Varfor grinden INTE kraver en tidsvakt pa allt

Det ar den viktigaste designbegransningen och den ar matt, inte befarad.
`M-96`: nio av sexton grinddomar i fas 9:s forsta modelldrivna korning var var
egen bugg, och tre av fyra uppgifter slog i taket pa grund av det. En grind som
kraver en tidsvakt pa VARJE vantan faller bankens egna referenslosningar pa
tiotals stallen (talet star i `M-159`) - alltsa en falsk rodgrind som branner
reparationsvarv pa nagot facit inte kraver.

Grinden faller darfor bara den vantan uppgiften SJALV pekar ut, och rapporterar
i `matt` hur manga vantningar den sag totalt och hur manga av dem som var
obundna. `vantelagen()` ger hela listan for den som vill mata bredden.
Skillnaden mellan "det grinden faller" och "det grinden ser" star darmed i
utdatan i stallet for i en kommentar.

## Felklass

`docs/spec/82_felklasser.md` sorteringsregel 5: **F6 och F7 far aldrig fallas
av en statisk grind**, darfor att statisk analys inte kan avgora timersemantik.
Den regeln bryts inte har. Grinden domer inte OM en tid ar ratt - den domer om
det finns nagon tidsgrans alls, och franvaro ar avgorbar utan semantik.

`SAKNAD_FORREGLING` far `F8` ("saknad eller felaktig forregling"), samma
lasning som `bank/reparationsbank.SPARKLASS` redan gor for spurfacits
invarianter. De tva andra har **ingen** klass i tabellen och far darfor
`felklass=None` i stallet for att stoppas in i F14 - samma val som
`st.fel.KONTROLLER` redan gjort for `OATKOMLIG` och `SAKERHET`, och av samma
skal: F14 ska hallas nara noll och en vaxande F14 betyder att taxonomin ska
revideras, inte fyllas pa. Det ar en oppen fraga till specen, inte ett hal i
grinden - alla tre faller anda.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

from ..st import modell as M
from ..st import uteslutning as U
from ..st.fel import Syntaxfel
from ..st.lasare import las
from ..st.typer import Elementar
from .signalkarta import Signalkarta, TILL_PLC

# kod -> (felklass enligt 82_felklasser.md eller None, vad kontrollen faller)
KONTROLLER_INDUSTRI: Dict[str, Tuple[Optional[str], str]] = {
    "SAKNAD_TIDSVAKT": (
        None, "vantan pa en kvittensingang som uppgiften kraver tidsovervakad, "
              "utan nagon tidsgrans i koden"),
    "TYST_FELTILLSTAND": (
        None, "latchat feltillstand som aldrig nar en larmutgang uppgiften har"),
    "SAKNAD_FORREGLING": (
        "F8", "forregling som uppgiften deklarerar men koden inte skriver som "
              "villkor pa donet"),
}

# Tidsurstyper som duger som tidsvakt. TOF och TP ar med for att grinden inte
# ska falla en losning som loser uppgiften med ett annat tidsur an TON; vilka
# banken faktiskt anvander star i M-159.
TIDSUR = ("TON", "TOF", "TP")

# Flanktyper - lases for att skilja ett tidsur fran en flankdetektor.
FLANKTYPER = ("R_TRIG", "F_TRIG")

# Failure_mode-rader som deklarerar att en vantan MASTE vara tidsovervakad.
# Uttrycken ar bankens egna formuleringar; traffarna over alla 33 referenser
# star i M-159 §2 sa att recall gar att lasa i stallet for att antas.
_TIDSKRAV = re.compile(
    r"utan tidsgrans|utan tidsur|utan tidsovervakning|ingen kvittensvakt"
    r"|star cellen tyst|star kvar tyst", re.I)

# Kommentarer som gor en utgang till en larmutgang. Ordlistan ar avsiktligt
# SNAV: "larm" som delstrang traffar ocksa "stampelarm" (L-07:s
# ST550_LBL_APPLY), och en falsk larmutgang gor regel 2 till en falsk GRON.
_LARMROLL = ("samlingslarm", "stationen stoppad", "larmutgang")

# Namn som ar projektets deklarerade samlingslarm oavsett kommentar.
_LARMNAMN = ("SYS_ALARM",)


@dataclass(frozen=True)
class Industrianmarkning:
    """Samma form som grind 2:s och grind 3:s anmarkningar, egen kodtabell."""

    kod: str
    rad: int
    text: str

    @property
    def felklass(self) -> Optional[str]:
        return KONTROLLER_INDUSTRI[self.kod][0]

    def __str__(self):
        return "rad %d: [%s/%s] %s" % (self.rad, self.kod,
                                       self.felklass or "-", self.text)


@dataclass(frozen=True)
class Tidsvaktkrav:
    """En vantan uppgiften sjalv kraver tidsovervakad."""

    ingang: str
    kalla: str                       # raden i failure_modes, ordagrant


@dataclass(frozen=True)
class Forregling:
    """`nar` haller ⇒ `kraver` maste halla, som villkor i koden.

    Formen ar spurfacits invariantform, och det ar med flit: den ar manniskans
    egen och den domer redan i korning. Skillnaden ar att korningsdomen bara
    kan falla det stimulit provocerar, och `M-89` matte att ett
    produktionsspar aldrig provocerar nodstoppet.
    """

    nar: Tuple[Tuple[str, object], ...]
    kraver: Tuple[Tuple[str, object], ...]
    kalla: str                       # "invariant" eller "interlock"
    text: str                        # uppgiftens egen formulering


@dataclass(frozen=True)
class Krav:
    """Uppgiftens deklarerade industrikrav, mekaniskt lasta ur uppgiften."""

    tidsvakter: Tuple[Tidsvaktkrav, ...] = ()
    larmutgangar: Tuple[str, ...] = ()
    forreglingar: Tuple[Forregling, ...] = ()
    # Det uppgiften sager men grinden inte kunde gora ett krav av. Bars i
    # utdatan i stallet for att tystas: en grind som slanger det den inte
    # forstod ser storre ut an den ar.
    oklara: Tuple[str, ...] = ()

    @staticmethod
    def ur_uppgift(post: dict, karta: Signalkarta) -> "Krav":
        return Krav(tidsvakter=_tidsvaktkrav(post, karta),
                    larmutgangar=_larmutgangar(post, karta),
                    forreglingar=_forreglingar(post, karta),
                    oklara=_oklara(post, karta))


@dataclass(frozen=True)
class Grind3bRapport:
    ok: bool
    anmarkningar: Tuple[Industrianmarkning, ...]
    matt: Dict[str, int] = field(default_factory=dict)
    oklara: Tuple[str, ...] = ()

    def koder(self) -> Tuple[str, ...]:
        return tuple(a.kod for a in self.anmarkningar)

    def __str__(self):
        rader = []
        if self.anmarkningar:
            rader.append("GRIND 3b EJ GODKAND")
            rader.extend("  " + str(a) for a in self.anmarkningar)
        else:
            rader.append("GRIND 3b GODKAND")
        rader.append("  kontrollerat: " + ", ".join(
            "%s=%d" % (k, self.matt[k]) for k in sorted(self.matt)))
        # De forsta raderna skrivs ut; resten raknas. Listan ar bevis pa vad
        # grinden INTE kunde svara pa, och den ar lang med flit - men en dom
        # som drunknar i den lases inte.
        for o in self.oklara[:6]:
            rader.append("  EJ KONTROLLERAT: " + o)
        if len(self.oklara) > 6:
            rader.append("  EJ KONTROLLERAT: ... och %d till (se .oklara)"
                         % (len(self.oklara) - 6))
        return "\n".join(rader)


# ---- kraven ur uppgiften --------------------------------------------------

def _signalnamn(karta: Signalkarta) -> Dict[str, object]:
    return dict((s.tagg.upper(), s) for s in karta.signaler)


def _namn_i_text(text: str, karta: Signalkarta) -> List[str]:
    """Taggnamn ur kartan som star ordagrant i texten, i textens ordning.

    Langsta namnet forst sa att `ST560_DOR_OPEN` inte plockas ur
    `ST560_DOR_OPENED`.
    """
    traffar = []
    for s in karta.signaler:
        for m in re.finditer(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])"
                             % re.escape(s.tagg), text):
            traffar.append((m.start(), s.tagg.upper()))
    traffar.sort()
    ut = []
    for _p, namn in traffar:
        if namn not in ut:
            ut.append(namn)
    return ut


def _tidsvaktkrav(post: dict, karta: Signalkarta) -> Tuple[Tidsvaktkrav, ...]:
    ut: List[Tidsvaktkrav] = []
    namn = _signalnamn(karta)
    for rad in post.get("failure_modes") or []:
        if not _TIDSKRAV.search(rad):
            continue
        for tagg in _namn_i_text(rad, karta):
            s = namn[tagg]
            # Bara INGANGAR: det ar kvittensen som kan uteble. En larmutgang i
            # samma mening ar utfallet, inte vantan.
            if s.riktning == TILL_PLC:
                ut.append(Tidsvaktkrav(tagg, rad))
    return tuple(ut)


def _larmutgangar(post: dict, karta: Signalkarta) -> Tuple[str, ...]:
    ut = []
    for s in karta.signaler:
        if not s.ar_utgang:
            continue
        tagg = s.tagg.upper()
        komm = (s.kommentar or "").lower()
        if tagg in _LARMNAMN or any(o in komm for o in _LARMROLL):
            ut.append(tagg)
    return tuple(ut)


def _bool(v: object) -> Optional[bool]:
    return v if isinstance(v, bool) else None


def _forreglingar(post: dict, karta: Signalkarta) -> Tuple[Forregling, ...]:
    ut: List[Forregling] = []
    sedda: Set[Tuple] = set()
    for f in list(_ur_invarianter(post, karta)) + list(_ur_interlocktext(post, karta)):
        nyckel = (f.nar, f.kraver)
        if nyckel in sedda:
            continue
        sedda.add(nyckel)
        ut.append(f)
    return tuple(ut)


def _ur_invarianter(post: dict, karta: Signalkarta) -> List[Forregling]:
    """Spurfacits invarianter som statiska krav.

    Bara de som galler i VARJE sekvens (`sekvens: "*"`). En invariant som bara
    galler i en namngiven sekvens ar ett pastaende om det scenariot, och den
    hor till korningsdomaren.
    """
    namn = _signalnamn(karta)
    ut: List[Forregling] = []
    for iv in ((post.get("facit_spar") or {}).get("invarianter") or []):
        if not isinstance(iv, dict):
            continue
        if (iv.get("sekvens") or "*") != "*":
            continue
        nar = iv.get("nar") or {}
        kraver = iv.get("kraver") or {}
        if not nar or not kraver:
            continue
        if any(k.upper() not in namn for k in list(nar) + list(kraver)):
            continue
        n = tuple(sorted((k.upper(), v) for k, v in nar.items()))
        k = tuple(sorted((k.upper(), v) for k, v in kraver.items()))
        ut.append(Forregling(n, k, "invariant", iv.get("namn") or ""))
        # KONTRAPOSITIONEN, nar bada sidor ar EN boolsk signal. "nar donet ar
        # hogt kraver vi att givaren ar hog" ar samma pastaende som "nar
        # givaren ar lag kraver vi att donet ar lagt" - men bara den andra
        # formen gar att prova, darfor att bara den andra har en UTGANG i
        # kraver-ledet. A-05:s pistolen_trycker_bara_mot_en_detalj ar skriven i
        # den forsta formen och var oprovbar utan det har (M-159 §4).
        if len(n) == 1 and len(k) == 1 and isinstance(n[0][1], bool) \
                and isinstance(k[0][1], bool):
            ut.append(Forregling(((k[0][0], not k[0][1]),),
                                 ((n[0][0], not n[0][1]),),
                                 "invariant (kontraposition)",
                                 iv.get("namn") or ""))
    return ut


# Klartextformerna i `control.interlocks`. De ar snava med flit: en rad som
# inte matchar blir `oklar` och rapporteras, i stallet for att gissas.
#
# Parsern ar provad mot ett KANT SVAR: samma uppgifters spurfacit-invarianter.
# Talet star i M-159 §4. Ett instrument som ingen provat mot ett kant svar ar
# projektets vanligaste fel (M-34, M-57, M-66, M-69, M-76, M-77).
_FORBUD = re.compile(r"far (aldrig|inte)", re.I)
_SAMTIDIGT = re.compile(r"samtidigt", re.I)
_VILLKOR_LAG = re.compile(r"\bar lag\b|\bar lagt\b|\bgatt lag\b", re.I)
_VILLKOR_HOG = re.compile(r"\bar hog\b|\bar hogt\b|\bar hoga\b|\bgatt hog\b"
                          r"|\bbekraftat\b|\bkommenderats\b", re.I)
_INNAN = re.compile(r"\binnan\b|\bforran\b", re.I)
# Vad som ar forbjudet for det FORSTA donet i raden.
_DON_HOGT = re.compile(r"ga hog|sta hog|vara hog|kommenderas|oppnas|starta",
                       re.I)
_DON_LAGT = re.compile(r"slappas|nollstallas", re.I)


def _ur_interlocktext(post: dict, karta: Signalkarta) -> List[Forregling]:
    namn = _signalnamn(karta)
    ut: List[Forregling] = []
    for rad in (post.get("control") or {}).get("interlocks") or []:
        taggar = _namn_i_text(rad, karta)
        m = _FORBUD.search(rad)
        if len(taggar) != 2 or m is None:
            continue
        a, b = taggar
        i_a = rad.index(namn[a].tagg)
        i_b = rad.rindex(namn[b].tagg)
        if _SAMTIDIGT.search(rad):
            # Tva former, och bara tva. "hissen far aldrig rora sig nar A och
            # B ar hoga samtidigt" ar en TREDJE form dar bada taggarna ar
            # VILLKORET och donet star i klartext - den lastes fel som en
            # omsesidig uteslutning mellan tva givare (M-159 §4), och den
            # lamnas nu olast i stallet for gissad.
            bada_fore = i_b < m.start()
            samtidigt_som = re.search(r"samtidigt som", rad, re.I) is not None
            if not (bada_fore or (i_a < m.start() and samtidigt_som)):
                continue
            ut.append(Forregling(((a, True),), ((b, False),), "interlock", rad))
            ut.append(Forregling(((b, True),), ((a, False),), "interlock", rad))
            continue
        # Tva-signalsformen: "<A> far aldrig <hogt/lagt> nar <B> ar <lag/hog>".
        # Villkorets polaritet lases pa TEXTEN EFTER B, sa att ett "ar lag" som
        # hor till A inte tas for B:s.
        svans = rad[i_b + len(namn[b].tagg):]
        if _VILLKOR_LAG.search(svans):
            b_varde = False
        elif _VILLKOR_HOG.search(svans):
            b_varde = True
        else:
            continue
        if _INNAN.search(rad):
            # "A far aldrig ga hog INNAN B ar hog" forbjuder A medan B annu
            # INTE ar hog - alltsa den motsatta polariteten mot den svansen
            # namner. Ordagrant fel forst: S-07 och T-04 fick omvand
            # forregling och bada referenserna folls pa det (M-159 §4).
            b_varde = not b_varde
        if _DON_LAGT.search(rad):
            a_varde = True          # A far inte SLAPPAS, alltsa maste vara hog
        elif _DON_HOGT.search(rad):
            a_varde = False
        else:
            continue
        ut.append(Forregling(((b, b_varde),), ((a, a_varde),), "interlock", rad))
    return ut


def _oklara(post: dict, karta: Signalkarta) -> Tuple[str, ...]:
    """Uppgiftens krav som grinden INTE kunde gora nagot av."""
    ut: List[str] = []
    for rad in post.get("failure_modes") or []:
        if _TIDSKRAV.search(rad) and not _tidsvakt_i_rad(rad, karta):
            ut.append("tidsvaktkrav utan namngiven ingang: " + rad)
    for rad in (post.get("control") or {}).get("interlocks") or []:
        if not _ur_interlocktext({"control": {"interlocks": [rad]}}, karta):
            ut.append("forregling i klartext som inte gick att lasa: " + rad)
    for iv in ((post.get("facit_spar") or {}).get("invarianter") or []):
        if isinstance(iv, dict) and (iv.get("sekvens") or "*") != "*":
            ut.append("invariant som bara galler i sekvensen %s: %s"
                      % (iv.get("sekvens"), iv.get("namn")))
    return tuple(ut)


def _tidsvakt_i_rad(rad: str, karta: Signalkarta) -> bool:
    namn = _signalnamn(karta)
    return any(namn[t].riktning == TILL_PLC for t in _namn_i_text(rad, karta))

# ---- analysen -------------------------------------------------------------
#
# Analysen svarar pa en enda fraga i tre skepnader: **vad kan sta i
# utsignalvektorn nar scannen ar klar?**
#
# Formen ar M-121:s, ett steg langre. Dar bar varje skrivning sitt
# sokvagsvillkor och tva skrivningar provades parvis med SAT. Har vecklas hela
# variabeln ut till ett VARDE vid scannens slut:
#
#     v_0 = v_fore_scannen                         (fri atom)
#     v_i = (villkor_i AND uttryck_i) OR (NOT villkor_i AND v_{i-1})
#
# Det ar precis den "symboliska vardeanalys av villkorliga tilldelningar" som
# M-121 lamnade obyggd i sin LIMITS. Utan den gar ingen forreglingsdom att
# stalla: bankens referenser skriver `IF NOT xDriftsklar THEN don := FALSE;`
# och sedan `don := xKommando AND ...`, sa att sambandet mellan EMG_OK och
# donet gar genom en VILLKORAD tilldelning. En analys som gor `xKommando` till
# en fri atom faller varje sadan referens - matt: 29 av 33 (M-159 §3).
#
# Riktningen ar fortfarande sund: atomerna ar oberoende, vilket ar en
# OVERSKATTNING av vad som kan vara sant samtidigt, och en overskattning ger
# fler fallningar - aldrig farre.


@dataclass
class Skrivning:
    """En skrivning till ett namn med sin sokvag.

    `delar` ar sokvagen som UTTRYCK med sin polaritet, inte som en fardig
    formel. Skalet ar att formeln maste kunna byggas om med variablernas
    varden isatta, och en formel som redan blivit atomer gar inte att veckla
    ut igen.
    """

    rad: int
    pos: int
    delar: Tuple[Tuple[M.Uttryck, bool], ...]
    uttryck: Optional[M.Uttryck]     # None = utbindning ur ett FB-anrop
    i_stegmaskin: bool = False


@dataclass
class Timeranrop:
    instans: str
    typ: str
    rad: int
    pos: int
    in_uttryck: Optional[M.Uttryck]
    pt_uttryck: Optional[M.Uttryck]


@dataclass
class Vantan:
    """Ett stegvillkor som haller cellen kvar tills en ingang svarar."""

    steg: Tuple[int, ...]
    rad: int
    ingangar: Tuple[str, ...]
    haller: Tuple[str, ...]          # don som star kommenderade i steget
    bunden: bool


# Tak for SAT-sokningen. M-121 satte 24 med uppmatt marginal 15; vardeanalysen
# har vecklar ut hela variabler och behover mer. Talet kommer ur en matning
# over bankens 33 referenser (M-159 §6): hogsta antal atomer i en
# forreglingsdom var 38, median 12. Taket ar satt med marginal.
MAX_ATOMER = 96  # M-159: hogst 29 atomer uppmatt over bankens 38 referenser

# Tak for hur djupt en variabels varde vecklas ut genom andra variabler.
# M-159 §6: bankens djupaste kedja ar 5 (C-06: RB_START -> xDrift -> xLarm ->
# tidsur). Over taket blir namnet en fri atom, alltsa "vet inte", och vet-inte
# faller.
MAX_VARDEDJUP = 12  # M-159: bankens djupaste kedja ar 5

# Tak for formelns storlek. En formel som spranger taket blir ogenomskinlig,
# och ogenomskinligt faller.
MAX_NODER = 20000  # M-159: storsta uppmatta formel ligger tva tiopotenser under


class Analys:
    """Laser POU:ns kropp en gang och svarar pa grindens tre fragor."""

    def __init__(self, pou: M.Pou, karta: Signalkarta):
        self.pou = pou
        self.karta = karta
        self.utgangar = set(t.upper() for t in karta.utgangar())
        self.ingangar = set(t.upper() for t in karta.ingangar())
        self.signaler = self.utgangar | self.ingangar
        self.typ_av = dict((t.upper(), typ) for t, typ in karta.typer().items())
        self.lokala: Dict[str, M.Deklaration] = {}
        self.tidsur: Dict[str, str] = {}
        for _b, d in pou.deklarationer():
            nyckel = d.namn.upper()
            if nyckel in self.signaler:
                continue
            self.lokala[nyckel] = d
            namn = getattr(d.typ, "namn", "")
            if namn.upper() in TIDSUR:
                self.tidsur[nyckel] = namn.upper()

        self._ordning: Dict[int, int] = {}
        self._slut: Dict[int, int] = {}
        self._skrivpos: Dict[str, List[int]] = {}
        self._numrera(pou.kropp)
        self.slutpos = len(self._ordning) + 1
        self.ute = U.Uteslutning(self._skrivpos)

        self.skrivningar: Dict[str, List[Skrivning]] = {}
        self.timeranrop: List[Timeranrop] = []
        self.q_lasningar: Set[str] = set()
        self.forsta_rad: Dict[str, int] = {}
        self.stegvar = self._stegvariabel()
        self._ga(pou.kropp, (), False)
        self._varden: Dict[object, object] = {}
        self._teckencache: Dict[Tuple[str, bool], FrozenSet[str]] = {}
        self.storsta_formel = 0

    # -- forordning --

    def _numrera(self, satser) -> None:
        for s in satser:
            self._ordning[id(s)] = len(self._ordning) + 1
            pos = self._ordning[id(s)]
            if isinstance(s, M.Tilldelning):
                self._skriv(_rotnamn(s.mal), pos)
            elif isinstance(s, M.Anropssats):
                self._skriv(s.anrop.namn.upper(), pos)
                for arg in s.anrop.argument:
                    if arg.ut:
                        self._skriv(_rotnamn(arg.uttryck), pos)
            elif isinstance(s, M.ForSats):
                self._skriv(s.styrvar.upper(), pos)
            for lista in _underlistor(s):
                self._numrera(lista)
            self._slut[id(s)] = len(self._ordning)

    def _skriv(self, namn: Optional[str], pos: int) -> None:
        if namn:
            self._skrivpos.setdefault(namn, []).append(pos)

    def _pos(self, s: M.Sats) -> int:
        return self._ordning.get(id(s), 0)

    def _stegvariabel(self) -> Optional[str]:
        """Stegmaskinens variabel: CASE-uttrycket som ocksa skrivs i koden."""
        for s in _alla_satser(self.pou.kropp):
            if not isinstance(s, M.Fall) or not isinstance(s.uttryck, M.Namn):
                continue
            namn = s.uttryck.ident.upper()
            if namn in self._skrivpos:
                return namn
        return None

    # -- gangen genom kroppen --

    def _ga(self, satser, delar, i_steg) -> None:
        for s in satser:
            pos = self._pos(s)
            if isinstance(s, M.Tilldelning):
                namn = _rotnamn(s.mal)
                if namn:
                    self.skrivningar.setdefault(namn, []).append(
                        Skrivning(s.rad, pos, delar, s.uttryck, i_steg))
                self._las(s.uttryck, s.rad)
            elif isinstance(s, M.Anropssats):
                self._anropssats(s, delar, i_steg, pos)
            elif isinstance(s, M.Om):
                foregaende: List[Tuple[M.Uttryck, bool]] = []
                for g in s.grenar:
                    self._las(g.villkor, g.rad)
                    self._ga(g.satser,
                             delar + tuple(foregaende) + ((g.villkor, False),),
                             i_steg)
                    foregaende.append((g.villkor, True))
                if s.annars is not None:
                    self._ga(s.annars, delar + tuple(foregaende), i_steg)
            elif isinstance(s, M.Fall):
                self._las(s.uttryck, s.rad)
                inne = i_steg or (isinstance(s.uttryck, M.Namn)
                                  and s.uttryck.ident.upper() == self.stegvar)
                foregaende = []
                for g in s.grenar:
                    villkor = _etikettvillkor(s.uttryck, g)
                    self._ga(g.satser,
                             delar + tuple(foregaende) + ((villkor, False),),
                             inne)
                    foregaende.append((villkor, True))
                if s.annars is not None:
                    self._ga(s.annars, delar + tuple(foregaende), inne)
            elif isinstance(s, (M.ForSats, M.Medan, M.Upprepa)):
                # En slinga kan kora noll ganger: sokvagen blir ogenomskinlig.
                self._ga(s.satser, delar + ((_OKANT, False),), i_steg)

    def _anropssats(self, s: M.Anropssats, delar, i_steg, pos) -> None:
        instans = s.anrop.namn.upper()
        for arg in s.anrop.argument:
            self._las(arg.uttryck, arg.rad)
            if arg.ut:
                namn = _rotnamn(arg.uttryck)
                if namn:
                    self.skrivningar.setdefault(namn, []).append(
                        Skrivning(arg.rad, pos, delar, None, i_steg))
        if instans in self.tidsur:
            argument = {}
            for i, arg in enumerate(s.anrop.argument):
                nyckel = (arg.namn or ("IN" if i == 0 else "PT")).upper()
                if not arg.ut:
                    argument[nyckel] = arg.uttryck
            self.timeranrop.append(Timeranrop(
                instans, self.tidsur[instans], s.anrop.rad, pos,
                argument.get("IN"), argument.get("PT")))

    def _las(self, u: Optional[M.Uttryck], rad: int) -> None:
        if u is None:
            return
        if isinstance(u, M.Namn):
            self.forsta_rad.setdefault(u.ident.upper(), u.rad or rad)
            return
        if isinstance(u, M.Medlem):
            bas = _rotnamn(u.bas)
            if bas in self.tidsur and u.falt.upper() == "Q":
                self.q_lasningar.add(bas)
            self._las(u.bas, rad)
            return
        if isinstance(u, M.Element):
            self._las(u.bas, rad)
            for i in u.index:
                self._las(i, rad)
            return
        if isinstance(u, M.Binar):
            self._las(u.vanster, rad)
            self._las(u.hoger, rad)
            return
        if isinstance(u, M.Unar):
            self._las(u.operand, rad)
            return
        if isinstance(u, M.Anrop):
            for a in u.argument:
                self._las(a.uttryck, rad)

    # -- vardeanalysen --

    def varde(self, namn: str, kedja: FrozenSet[str] = frozenset(),
              djup: int = 0):
        """Formeln for `namn`:s varde NAR SCANNEN AR KLAR.

        En ingang ar en fri atom: den lases vid scannens borjan och star still.
        En lokal variabel eller utgang vecklas ut ur sina skrivningar i
        programordning. En variabel som redan ar under utveckling (`kedja`)
        eller som ligger over djuptaket blir en fri atom - "vet inte", och
        vet-inte faller.
        """
        namn = namn.upper()
        if namn in self.ingangar or namn in kedja or djup > MAX_VARDEDJUP:
            return _fri(namn, self.slutpos)
        skrivningar = self.skrivningar.get(namn)
        if not skrivningar:
            return _fri(namn, self.slutpos)
        if djup == 0 and namn in self._varden:
            return self._varden[namn]
        inre = kedja | {namn}
        # Vardet FORE scannen. En utgang som skrivs ovillkorat nagon gang
        # under scannen ar oberoende av det, och da faller atomen bort av sig
        # sjalv i folden nedan. Ar den DET INTE behaller variabeln sitt varde
        # over scangransen, och det ar just den dorren en forreglingsdom maste
        # kunna stanga - se `_induktionshypotes`.
        v = _fri(namn + "@FORE", self.slutpos)
        for s in sorted(skrivningar, key=lambda x: x.pos):
            p = self._villkor(s.delar, inre, djup + 1)
            if s.uttryck is None:
                e = U.ogenomskinlig(self.slutpos)
            else:
                e = self._formel(s.uttryck, inre, djup + 1)
            v = U.eller(U.och(p, e), U.och(U.icke(p), v))
            if _noder(v) > MAX_NODER:
                return U.ogenomskinlig(self.slutpos)
        if djup == 0:
            self._varden[namn] = v
        return v

    def _villkor(self, delar, kedja: FrozenSet[str], djup: int):
        f = True
        for uttryck, negerad in delar:
            g = self._formel(uttryck, kedja, djup)
            f = U.och(f, U.icke(g) if negerad else g)
        return f

    def _formel(self, u: M.Uttryck, kedja: FrozenSet[str], djup: int):
        """Uttryckets formel med variablernas VARDEN isatta.

        Allt som inte ar logik, namn eller jamforelse blir en ogenomskinlig
        atom - ett funktionsanrop kan ha sidoeffekter, och vet-inte faller.
        """
        if u is _OKANT:
            return U.ogenomskinlig(self.slutpos)
        if isinstance(u, M.Literal):
            if u.klass == "BOOL":
                return bool(u.varde)
            return U.ogenomskinlig(self.slutpos)
        if isinstance(u, M.Unar) and u.op == "NOT":
            return U.icke(self._formel(u.operand, kedja, djup))
        if isinstance(u, M.Binar):
            if u.op == "AND":
                return U.och(self._formel(u.vanster, kedja, djup),
                             self._formel(u.hoger, kedja, djup))
            if u.op == "OR":
                return U.eller(self._formel(u.vanster, kedja, djup),
                               self._formel(u.hoger, kedja, djup))
            if u.op == "XOR":
                a = self._formel(u.vanster, kedja, djup)
                b = self._formel(u.hoger, kedja, djup)
                return U.eller(U.och(a, U.icke(b)), U.och(U.icke(a), b))
            if u.op in ("=", "<>", "<", ">", "<=", ">="):
                # Jamforelser ar atomer med likhetsgrupp, precis som i
                # uteslutning.py: `steg = 1` och `steg = 2` utesluter varandra.
                return U.formel_av(u, self.slutpos)
            return U.ogenomskinlig(self.slutpos)
        if isinstance(u, M.Namn):
            namn = u.ident.upper()
            if (namn in self.lokala or namn in self.utgangar) \
                    and namn not in self.tidsur:
                return self.varde(namn, kedja, djup)
            return _fri(namn, self.slutpos)
        if isinstance(u, M.Medlem) and not _har_anrop_i(u):
            return U.formel_av(u, self.slutpos)
        return U.ogenomskinlig(self.slutpos)

    # -- SAT --

    def satisfierbar(self, f) -> Tuple[bool, Optional[Dict[str, bool]]]:
        """(kan formeln vara sann?, vittne). Over taket: (True, None) - vet
        inte, alltsa faller."""
        if f is True:
            return True, {}
        if f is False:
            return False, None
        g, beskrivning, grupper = self.ute._numrera(f)
        self.storsta_formel = max(self.storsta_formel, len(beskrivning))
        if len(beskrivning) > MAX_ATOMER:
            return True, None
        grupp_av: Dict[int, List[int]] = {}
        for medlemmar in grupper.values():
            for n in medlemmar:
                grupp_av[n] = medlemmar
        modell = U._sat(g, {}, grupp_av)
        if modell is None:
            return False, None
        return True, dict((beskrivning[n].kanon, v) for n, v in modell.items())

    # -- tidsvakten --

    def har_tidsvakt(self, ingang: str) -> Optional[Timeranrop]:
        """Tidsuret som overvakar vantan pa `ingang`, eller None.

        Tre krav, alla ur vad en vakt AR: uret ska ga UNDER vantan, ha en
        tidsgrans storre an noll, och nagon ska lasa dess utfall. Ett ur vars
        `Q` ingen laser ar ingen vakt.

        "Ga under vantan" ar med flit vidare an "lasa kvittensingangen".
        A-08:s referens skriver `tmrStrang(IN := ST480_RB_START, PT := T#8s)`
        - uret gar sa lange KOMMANDOT ligger ute och nollstalls nar kommandot
        tas bort, vilket ar den vanligaste industriella formen. En regel som
        krav att `IN` namner kvittensen fallde den referensen, och det var en
        falsk rodgrind (M-159 §3). Uret raknas darfor ocksa nar dess `IN` beror
        av ett DON som star kommenderat i just det vantesteget.
        """
        ingang = ingang.upper()
        haller = self._haller_i_vantesteg(ingang)
        for t in self.timeranrop:
            if not _positiv_tid(t.pt_uttryck):
                continue
            if t.instans not in self.q_lasningar:
                continue
            varr = self.beror_av(t.in_uttryck)
            if ingang in varr or (varr & haller):
                return t
        return None

    def beror_av(self, u: Optional[M.Uttryck], djup: int = 0,
                 sedda: FrozenSet[str] = frozenset()) -> Set[str]:
        """Namn ett uttryck beror av, ocksa genom mellanvariabler.

        A-07:s referens skriver `xTandning := ST470_ARC_ON AND NOT
        ST470_ARC_OK;` och sedan `tmrTand(IN := xTandning, ...)`. En regel som
        bara laser urets egna argument ser namnet `xTandning` och missar att
        uret bevakar just den vantan - den fallde A-07:s referens, och det var
        en falsk rodgrind (M-159 §3).
        """
        ut: Set[str] = set()
        for namn in _namn_i_uttryck(u):
            ut.add(namn)
            if djup >= MAX_VARDEDJUP or namn in sedda:
                continue
            # Bara RENA mellanvariabler foljs - en enda, ovillkorad skrivning.
            # Samma regel som uteslutning.substituera: en variabel som skrivs
            # pa flera stallen betyder olika saker pa olika stallen, och att
            # folja den vidare gor beroendemangden till hela programmet.
            # ...och bara ARBETSVARIABLER. En UTGANG ar dar kedjan slutar:
            # `xTandning := ARC_ON AND NOT ARC_OK` och `ARC_ON := xBage AND
            # GAS_ON` gor annars att uret pa tandningen ser ut att bevaka varje
            # steg dar gasen star pa, och A-07:s sex vantelagen blev noll
            # obundna (M-159 §5).
            if namn not in self.lokala or not self.ett_skrivstalle(namn):
                continue
            ut |= self.beror_av(self.skrivningar[namn][0].uttryck,
                                djup + 1, sedda | {namn})
        return ut

    def _haller_i_vantesteg(self, ingang: str) -> Set[str]:
        """Don som star kommenderade i de steg dar cellen vantar pa `ingang`."""
        ut: Set[str] = set()
        for v in self.vantelagen(utan_tidsdom=True):
            if ingang in v.ingangar:
                ut |= set(v.haller)
        # Stegvariabeln ar inget DON. Rakna den som ett hallet don och varje
        # tidsur som star pa `steg = N` blir en vakt over varje vantan i
        # programmet - A-07:s sex vantelagen blev da noll obundna (M-159 §5).
        return set(n for n in ut if n != self.stegvar and self._ar_bool(n))

    def ett_skrivstalle(self, namn: str) -> bool:
        """Sant nar utgangen har EN enda, OVILLKORAD skrivning.

        Det ar den form M-121 redan begar av bade modell och referens:
        "en utgang med ett skrivstalle och forreglingen i samma uttryck lases
        pa en rad, och den ATERHAMTAR SIG". For den formen ar fragan "star
        forreglingen i uttrycket" avgorbar utan att veta var stegmaskinen
        star. For allt annat ar den det inte.
        """
        skrivningar = self.skrivningar.get(namn.upper(), [])
        return len(skrivningar) == 1 and not skrivningar[0].delar

    def heltalsdriven(self, namn: str) -> bool:
        """Sant nar utgangens uttryck jamfor en variabel koden skriver med ett
        tal - alltsa nar svaret hanger pa en heltalsvardesanalys som inte finns."""
        for s in self.skrivningar.get(namn.upper(), []):
            if s.uttryck is not None and self._heltalsjamforelse(s.uttryck):
                return True
        return False

    def _heltalsjamforelse(self, u: M.Uttryck) -> bool:
        if isinstance(u, M.Unar):
            return self._heltalsjamforelse(u.operand)
        if not isinstance(u, M.Binar):
            return False
        if u.op in ("AND", "OR", "XOR"):
            return (self._heltalsjamforelse(u.vanster)
                    or self._heltalsjamforelse(u.hoger))
        if u.op not in ("=", "<>", "<", ">", "<=", ">="):
            return False
        for sida in (u.vanster, u.hoger):
            if isinstance(sida, M.Namn):
                n = sida.ident.upper()
                d = self.lokala.get(n)
                if (n in self._skrivpos and d is not None
                        and getattr(d.typ, "namn", "").upper() != "BOOL"):
                    return True
        return False

    # -- feltillstandet --

    def feltillstand(self) -> Dict[str, Skrivning]:
        """Latchade feltillstand: namn -> skrivningen som satter dem.

        Ett feltillstand ar en LOKAL BOOL som

          1. **latchas**: satts TRUE pa ett stalle och FALSE pa ett annat, och
             halls alltsa kvar tills nagon aterstaller den,
          2. satts av ett **utlost tidsur** eller av ett **matvarde utanfor en
             grans**, och
          3. satts **utanfor stegmaskinen**.

        Alla tre behovs, och var och en ar matt mot bankens referenser:

        * Utan latchkravet blir ett kombinatoriskt `xGodkant := (tryck < 0.5)`
          ett larm; det ar ett provresultat.
        * De tva utlosarna ar de enda otvetydiga. En insignal som gar lag ar
          ett TILLSTAND - nodstopp, handlage - inte ett fel, och A-07:s
          `xKravOmstart` ar just det.
        * Utan stegkravet blir varje SEKVENSKOMMANDO ett feltillstand, darfor
          att ett vantesteg ofta star pa ett tidsur: A-06:s `xLid`, `xOppen`
          och `xTrig`, A-07:s `xBage` och `xTrad` och A-08:s `xKassera` foll
          alla pa det (M-159 §3). Ett fel upptacks oberoende av vilket steg
          cellen star i; ett kommando hor till sitt steg.

        Priset star i LIMITS: en modell som latchar sitt larm INNE i
        stegmaskinen slipper undan regel 2.
        """
        ut: Dict[str, Skrivning] = {}
        for namn, skrivningar in sorted(self.skrivningar.items()):
            d = self.lokala.get(namn)
            if d is None or getattr(d.typ, "namn", "").upper() != "BOOL":
                continue
            sanna = [s for s in skrivningar if _literal_bool(s.uttryck) is True]
            falska = [s for s in skrivningar if _literal_bool(s.uttryck) is False]
            if not sanna or not falska:
                continue
            for s in sanna:
                if s.i_stegmaskin:
                    continue
                if self._utloses_av_fel(s):
                    ut[namn] = s
                    break
        return ut

    def _utloses_av_fel(self, s: Skrivning) -> bool:
        for uttryck, _neg in s.delar:
            if uttryck is _OKANT:
                continue
            for namn in _namn_i_uttryck(uttryck):
                if namn in self.tidsur:
                    return True
            if self._analog_grans(uttryck):
                return True
        return False

    def _analog_grans(self, u: M.Uttryck) -> bool:
        """En jamforelse mellan en REAL/INT-signal och ett tal."""
        if isinstance(u, M.Unar):
            return self._analog_grans(u.operand)
        if not isinstance(u, M.Binar):
            return False
        if u.op in ("AND", "OR", "XOR"):
            return (self._analog_grans(u.vanster)
                    or self._analog_grans(u.hoger))
        if u.op not in ("=", "<>", "<", ">", "<=", ">="):
            return False
        for a, b in ((u.vanster, u.hoger), (u.hoger, u.vanster)):
            if not isinstance(a, M.Namn) or not isinstance(b, M.Literal):
                continue
            typ = self.typ_av.get(a.ident.upper())
            if typ is not None and getattr(typ, "namn", "").upper() in ("REAL", "INT"):
                return True
        return False

    def nar_positivt(self, mal: str, djup: int = 0,
                     sedda: FrozenSet[str] = frozenset()) -> FrozenSet[str]:
        """Namn som kan gora `mal` HOG.

        Lasningen ar pa YTAN, inte pa det utvecklade vardet: `varde()` vecklar
        ut hela kedjan till tidsur och ingangar, sa `SYS_ALARM := xLarm` skulle
        dar inte innehalla namnet `xLarm` alls. Fragan har ar en annan - vilket
        NAMN driver utgangen - och den besvaras pa skrivningarnas egna uttryck,
        med en teckenriktig stangning genom mellanvariabler.

        En sparr syns bara som `NOT x` och gor inte utgangen hog; ett
        feltillstand maste DRIVA en utgang, inte sparra den.
        """
        return self._tecken(mal, True, djup, sedda)

    def _tecken(self, mal: str, positiv: bool, djup: int,
                sedda: FrozenSet[str]) -> FrozenSet[str]:
        mal = mal.upper()
        if mal in sedda or djup > MAX_VARDEDJUP:
            return frozenset()
        nyckel = (mal, positiv)
        if djup == 0 and nyckel in self._teckencache:
            return self._teckencache[nyckel]
        plus: Set[str] = set()
        minus: Set[str] = set()
        for s in self.skrivningar.get(mal, []):
            f = True
            for uttryck, negerad in s.delar:
                g = U.formel_av(uttryck, self.slutpos) if uttryck is not _OKANT \
                    else U.ogenomskinlig(self.slutpos)
                f = U.och(f, U.icke(g) if negerad else g)
            if s.uttryck is None:
                f = U.och(f, U.ogenomskinlig(self.slutpos))
            else:
                f = U.och(f, U.formel_av(s.uttryck, self.slutpos))
            _positiva(f, True, plus)
            _positiva(f, False, minus)
        direkt = plus if positiv else minus
        motsatt = minus if positiv else plus
        ut = set(direkt)
        inre = sedda | {mal}
        for namn in list(direkt):
            if self._ar_bool(namn):
                ut |= self._tecken(namn, True, djup + 1, inre)
        for namn in list(motsatt):
            if self._ar_bool(namn):
                ut |= self._tecken(namn, False, djup + 1, inre)
        svar = frozenset(n.split("@")[0] for n in ut)
        if djup == 0:
            self._teckencache[nyckel] = svar
        return svar

    def _ar_bool(self, namn: str) -> bool:
        """Bara BOOL foljs i teckenkedjan.

        Att folja ett HELTAL ar meningslost: `steg := 0` i grenen `NOT xKlar`
        gor inte `xKlar` till nagot som DRIVER en utgang, men en naiv
        teckenkedja laser det sa - och da ser varje feltillstand ut att na en
        utgang. Fixturen `SYS_ALARM := FALSE` slapptes igenom pa det.
        """
        namn = namn.upper()
        d = self.lokala.get(namn)
        if d is not None:
            return getattr(d.typ, "namn", "").upper() == "BOOL"
        typ = self.typ_av.get(namn)
        return typ is not None and getattr(typ, "namn", "").upper() == "BOOL"

    # -- vantelagen: grindens matning, inte dess dom --

    def vantelagen(self, utan_tidsdom: bool = False) -> Tuple[Vantan, ...]:
        """Varje stegvillkor som haller cellen kvar tills en ingang svarar.

        `M-159 §5` matte att ett krav pa tidsvakt over VARJE vantelage faller
        bankens egna referenser pa 51 stallen i 26 av 33 uppgifter. Grinden
        faller darfor bara det uppgiften sjalv pekar ut, och rapporterar det
        har talet bredvid domen sa att skillnaden mellan "det grinden faller"
        och "det grinden ser" star i utdatan i stallet for i en kommentar.
        """
        if self.stegvar is None:
            return ()
        ut: List[Vantan] = []
        for s in _alla_satser(self.pou.kropp):
            if not (isinstance(s, M.Fall) and isinstance(s.uttryck, M.Namn)
                    and s.uttryck.ident.upper() == self.stegvar):
                continue
            haller = self._kommenderade(s)
            for gren in s.grenar:
                etikett = tuple(v for e in gren.etiketter for v in e.varden())
                for delar, rad in self._stegbyten(gren.satser, ()):
                    namn: Set[str] = set()
                    for uttryck, _neg in delar:
                        namn |= _namn_i_uttryck(uttryck)
                    ingangar = tuple(sorted(namn & self.ingangar))
                    if not ingangar:
                        continue
                    bunden = any(n in self.tidsur for n in namn)
                    if not bunden and not utan_tidsdom:
                        bunden = any(self.har_tidsvakt(i) is not None
                                     for i in ingangar)
                    ut.append(Vantan(
                        etikett, rad, ingangar,
                        haller.get(etikett[0] if etikett else None, ()),
                        bunden))
        return tuple(ut)

    def _stegbyten(self, satser, delar):
        """(sokvag, rad) for varje VILLKORAT byte av stegvariabeln.

        Ett OVILLKORAT byte ar ingen vantan: steget slapper av sig sjalvt.
        """
        for s in satser:
            if isinstance(s, M.Tilldelning):
                if _rotnamn(s.mal) == self.stegvar and delar:
                    yield delar, s.rad
            elif isinstance(s, M.Om):
                foregaende: List[Tuple[M.Uttryck, bool]] = []
                for g in s.grenar:
                    for x in self._stegbyten(
                            g.satser,
                            delar + tuple(foregaende) + ((g.villkor, False),)):
                        yield x
                    foregaende.append((g.villkor, True))
                if s.annars is not None:
                    for x in self._stegbyten(s.annars,
                                             delar + tuple(foregaende)):
                        yield x
            elif isinstance(s, M.Fall):
                foregaende = []
                for g in s.grenar:
                    villkor = _etikettvillkor(s.uttryck, g)
                    for x in self._stegbyten(
                            g.satser,
                            delar + tuple(foregaende) + ((villkor, False),)):
                        yield x
                    foregaende.append((villkor, True))
                if s.annars is not None:
                    for x in self._stegbyten(s.annars,
                                             delar + tuple(foregaende)):
                        yield x
            elif isinstance(s, (M.ForSats, M.Medan, M.Upprepa)):
                for x in self._stegbyten(s.satser, delar + ((_OKANT, False),)):
                    yield x

    def _kommenderade(self, fall: M.Fall) -> Dict[object, Tuple[str, ...]]:
        """Vilka don som star kommenderade nar cellen kommer IN i ett steg.

        Framatfixpunkt over stegmaskinens egna overgangar. Over-approximation:
        en skrivning vars varde inte ar en literal raknas som "kan vara hog".
        """
        effekter: Dict[int, Dict[str, Optional[bool]]] = {}
        kanter: Dict[int, Set[int]] = {}
        for gren in fall.grenar:
            for e in gren.etiketter:
                for v in e.varden():
                    effekter.setdefault(v, {})
                    kanter.setdefault(v, set())
            for s in _alla_satser(gren.satser):
                if not isinstance(s, M.Tilldelning):
                    continue
                namn = _rotnamn(s.mal)
                if namn == self.stegvar:
                    mal = _literal_int(s.uttryck)
                    if mal is not None:
                        for e in gren.etiketter:
                            for v in e.varden():
                                kanter[v].add(mal)
                elif namn in self.utgangar or namn in self.lokala:
                    for e in gren.etiketter:
                        for v in e.varden():
                            effekter[v][namn] = _literal_bool(s.uttryck)
        drivande: Set[str] = set()
        for u in self.utgangar:
            drivande |= set(self.nar_positivt(u))
        hallning: Dict[int, Set[str]] = dict((v, set()) for v in effekter)
        andrad = True
        varv = 0
        while andrad and varv < 50:
            andrad = False
            varv += 1
            for v in sorted(effekter):
                efter = set(hallning[v])
                for namn, varde in effekter[v].items():
                    if namn not in self.utgangar and namn not in drivande:
                        continue
                    if varde is False:
                        efter.discard(namn)
                    else:
                        efter.add(namn)
                for nasta in kanter[v]:
                    if nasta in hallning and not efter <= hallning[nasta]:
                        hallning[nasta] |= efter
                        andrad = True
        return dict((v, tuple(sorted(h))) for v, h in hallning.items())


# ---- domarna --------------------------------------------------------------

def _doma_tidsvakter(a: Analys, krav: Krav) -> List[Industrianmarkning]:
    anm = []
    for k in krav.tidsvakter:
        if a.har_tidsvakt(k.ingang) is not None:
            continue
        anm.append(Industrianmarkning(
            "SAKNAD_TIDSVAKT", a.forsta_rad.get(k.ingang, 0),
            "vantan pa %s har ingen tidsgrans: inget tidsur laser %s, har en "
            "PT storre an noll och ett Q som nagon laser. Uppgiften sager: %s"
            % (k.ingang, k.ingang, k.kalla)))
    return anm


def _doma_feltillstand(a: Analys, krav: Krav) -> List[Industrianmarkning]:
    """Nar feltillstandet ut ur PLC:n over huvud taget?

    Kravet ar att det driver NAGON utgang i kartan positivt, inte just
    larmutgangen. A-08:s `xKassera` gar till `ST480_REJ_MARK` och inte till
    `SYS_ALARM`, och det ar ratt: markeringen ar kassationens synliga utfall.
    Ett krav pa just larmutgangen fallde den referensen, och det var en falsk
    rodgrind (M-159 §3).

    Uppgifter UTAN nagon larmutgang undantas helt: en uppgift vars signalkarta
    inte har nagon vag ut for ett fel kan inte kravas pa en. Det star i `matt`
    sa att en tom kontroll inte ser ut som ett godkannande.
    """
    if not krav.larmutgangar:
        return []
    anm = []
    positiva: Set[str] = set()
    for utgang in a.utgangar:
        positiva |= set(a.nar_positivt(utgang))
    for namn, s in sorted(a.feltillstand().items()):
        if namn in positiva:
            continue
        anm.append(Industrianmarkning(
            "TYST_FELTILLSTAND", s.rad,
            "feltillstandet %s latchas men driver ingen utgang i kartan (%s "
            "finns); ett fel som bara satter en intern variabel syns inte for "
            "nagon" % (namn, ", ".join(krav.larmutgangar))))
    return anm


def _doma_forreglingar(a: Analys, krav: Krav) -> List[Industrianmarkning]:
    """Kan utgangen ha FEL varde nar forreglingens villkor haller?

    Domen stalls pa VARDENA vid scannens slut, samma tidpunkt som spurfacits
    invarianter laser. Ar `NAR AND (utgangen har fel varde)` satisfierbar star
    forreglingen inte i koden - och da haller den bara sa lange stegen rakar
    falla ratt, vilket ar precis vad F7- och F8-doktrinen forbjuder.
    """
    anm = []
    ej_kontrollerade: List[str] = []
    provade = [0]
    sedda: Set[Tuple[str, str]] = set()
    for f in krav.forreglingar:
        if _narformel(a, f.nar) is None:
            continue
        for namn, varde in f.kraver:
            v = _bool(varde)
            if v is None or namn not in a.utgangar:
                continue
            if namn not in a.skrivningar:
                continue                       # ODRIVEN_UTGANG ar grind 3:s
            if any(n not in a.ingangar for n, _v in f.nar):
                # `nar`-sidan ar en annan UTGANG, alltsa nagot programmet
                # sjalvt styr. Att tva kommandon inte krockar ar da en
                # SEKVENSegenskap, och den kan en statisk grind inte avgora -
                # samma skal som 82_felklasser.md sorteringsregel 5 ger for att
                # F6 och F7 aldrig far fallas statiskt. En INGANG ar en annan
                # sak: den kan andra sig mitt i ett steg (klamman slapper mitt
                # i indexet - M-89), och da racker inte sekvensens garanti.
                ej_kontrollerade.append(
                    "villkoret i '%s' ar en utgang, inte en ingang; "
                    "sekvensegenskaper lamnas at korningsdomaren" % f.text)
                continue
            if a.heltalsdriven(namn):
                # Utgangen drivs direkt av ett skrivet HELTAL (S-05:s
                # `ST200_CNV_RUN := tillstand = 6`). Vardeanalysen viker
                # boolska tilldelningar, inte heltalstilldelningar, sa svaret
                # vore "vet inte" - och vet-inte far inte bli en dom.
                ej_kontrollerade.append(
                    "%s drivs av ett skrivet heltalsvarde; grind 3b har ingen "
                    "heltalsvardesanalys och lamnar '%s' at korningsdomaren"
                    % (namn, f.text))
                continue
            if not a.ett_skrivstalle(namn):
                # Utgangen skrivs inne i stegmaskinen. Da ar fragan inte "star
                # forreglingen i uttrycket" utan "kan stegmaskinen na det
                # laget", och den fragan kan en statisk grind inte svara pa -
                # samma skal som 82_felklasser.md sorteringsregel 5 ger for att
                # F6 och F7 aldrig far fallas statiskt. Den lamnas at
                # korningsdomaren och rapporteras som EJ KONTROLLERAD.
                ej_kontrollerade.append(
                    "%s skrivs i stegmaskinen; forreglingen '%s' lamnas at "
                    "korningsdomaren" % (namn, f.text))
                continue
            # Utgangens varde fore scannen ar en FRI atom. Det ar med flit:
            # en utgang som bara skrivs i ett steg behaller sitt varde over
            # scangransen, och det ar precis den dorren en ingang kan komma in
            # genom. M-89:s hal i klartext: klamman slapper MITT i indexet, och
            # sekvensen har redan passerat sin kontroll av lagesgivaren.
            provade[0] += 1
            ut = a.varde(namn)
            brott = U.och(_narformel(a, f.nar),
                          U.icke(ut) if v else ut)
            kan, vittne = a.satisfierbar(brott)
            if not kan:
                continue
            nyckel = (namn, _nartext(f.nar))
            if nyckel in sedda:
                continue
            sedda.add(nyckel)
            anm.append(Industrianmarkning(
                "SAKNAD_FORREGLING", a.forsta_rad.get(namn, 0),
                "%s kan vara %s nar %s; forreglingen star inte som villkor i "
                "koden%s. Uppgiften sager: %s"
                % (namn, "hog" if not v else "lag", _nartext(f.nar),
                   U.vittnestext(vittne), f.text)))
    return anm, ej_kontrollerade, provade[0]


def _narformel(a: Analys, nar: Sequence[Tuple[str, object]]):
    """`nar`-sidan som formel, ocksa den pa vardena vid scannens slut."""
    f = True
    for namn, varde in nar:
        if isinstance(varde, bool):
            v = a.varde(namn)
            f = U.och(f, v if varde else U.icke(v))
        elif isinstance(varde, int):
            jam = M.Binar("=", M.Namn(namn),
                          M.Literal("HELTAL", str(varde), varde))
            f = U.och(f, U.formel_av(jam, a.slutpos))
        else:
            return None
    return f


def _nartext(nar: Sequence[Tuple[str, object]]) -> str:
    delar = []
    for namn, varde in nar:
        if varde is True:
            delar.append("%s ar hog" % namn)
        elif varde is False:
            delar.append("%s ar lag" % namn)
        else:
            delar.append("%s = %s" % (namn, varde))
    return " och ".join(delar)


# ---- grinden --------------------------------------------------------------

def granska(kalla: str, karta: Signalkarta, krav: Krav) -> Grind3bRapport:
    """Dom ST-texten mot uppgiftens industrikrav.

    Fail-closed (I3): gar texten inte att lasa ar svaret inte "inga
    anmarkningar" utan "gick inte att doma". Grind 3 rapporterar samma sak som
    OLASLIG; grind 3b upprepar inte den koden - den vagrar bara svara ja.
    """
    try:
        enhet = las(kalla)
    except Syntaxfel as fel:
        return Grind3bRapport(False, (), {"olaslig": 1},
                              ("kallan gick inte att lasa (rad %d: %s); "
                               "grind 3b kunde inte doma" % (fel.rad, fel.text),))
    pou = None
    for p in enhet.pouer:
        if p.namn.upper() == karta.station.upper():
            pou = p
            break
    if pou is None:
        return Grind3bRapport(False, (), {"saknad_pou": 1},
                              ("kallan har ingen POU %s; grind 3b kunde inte "
                               "doma" % karta.station,))

    a = Analys(pou, karta)
    anm: List[Industrianmarkning] = []
    anm.extend(_doma_tidsvakter(a, krav))
    anm.extend(_doma_feltillstand(a, krav))
    forregling, ej_kontrollerade, provade = _doma_forreglingar(a, krav)
    anm.extend(forregling)

    vantelagen = a.vantelagen()
    matt = {
        "tidsvaktkrav": len(krav.tidsvakter),
        "larmutgangar": len(krav.larmutgangar),
        "forreglingar": len(krav.forreglingar),
        "feltillstand": len(a.feltillstand()),
        "vantelagen": len(vantelagen),
        "vantelagen_obundna": len([v for v in vantelagen if not v.bunden]),
        "tidsur": len(a.tidsur),
        "storsta_formel": a.storsta_formel,
        "forreglingspar_provade": provade,
        "forreglingspar_ej_provade": len(ej_kontrollerade),
    }
    return Grind3bRapport(not anm, tuple(anm), matt,
                          krav.oklara + tuple(ej_kontrollerade))


# ---- sma hjalpare ---------------------------------------------------------

# Star for en sokvag grinden inte kan lasa (slingor). Blir alltid en
# ogenomskinlig atom, alltsa "vet inte".
_OKANT = M.Namn("?OKANT")


def _fri(namn: str, pos: int):
    """En fri atom for ett namn: vardet ar okant men KONSEKVENT inom formeln."""
    return ("A", U.Atom(namn.upper(), frozenset([namn.upper()]), pos))


def _etikettvillkor(uttryck: M.Uttryck, gren: M.Fallgren) -> M.Uttryck:
    """CASE-grenens villkor som ett UTTRYCK: sel = v1 OR sel = v2 ..."""
    varden: List[int] = []
    for e in gren.etiketter:
        varden.extend(e.varden())
    if not varden or len(varden) > U.MAX_ETIKETTVARDEN:
        return _OKANT
    villkor: Optional[M.Uttryck] = None
    for v in varden:
        jam = M.Binar("=", uttryck, M.Literal("HELTAL", str(v), v))
        villkor = jam if villkor is None else M.Binar("OR", villkor, jam)
    return villkor


def _rotnamn(mal: M.Uttryck) -> Optional[str]:
    rot = mal
    while isinstance(rot, (M.Medlem, M.Element)):
        rot = rot.bas
    return rot.ident.upper() if isinstance(rot, M.Namn) else None


def _namn_i_uttryck(u: Optional[M.Uttryck]) -> Set[str]:
    ut: Set[str] = set()
    if u is not None and u is not _OKANT:
        U._variabler(u, ut)
    return ut


def _har_anrop_i(u: M.Uttryck) -> bool:
    if isinstance(u, M.Anrop):
        return True
    if isinstance(u, M.Binar):
        return _har_anrop_i(u.vanster) or _har_anrop_i(u.hoger)
    if isinstance(u, M.Unar):
        return _har_anrop_i(u.operand)
    if isinstance(u, (M.Medlem, M.Element)):
        return _har_anrop_i(u.bas)
    return False


def _underlistor(s: M.Sats):
    if isinstance(s, M.Om):
        for g in s.grenar:
            yield g.satser
        if s.annars is not None:
            yield s.annars
    elif isinstance(s, M.Fall):
        for g in s.grenar:
            yield g.satser
        if s.annars is not None:
            yield s.annars
    elif isinstance(s, (M.ForSats, M.Medan, M.Upprepa)):
        yield s.satser


def _alla_satser(satser):
    for s in satser:
        yield s
        for lista in _underlistor(s):
            for inre in _alla_satser(lista):
                yield inre


def _literal_bool(u: Optional[M.Uttryck]) -> Optional[bool]:
    if isinstance(u, M.Literal) and u.klass == "BOOL":
        return bool(u.varde)
    return None


def _literal_int(u: Optional[M.Uttryck]) -> Optional[int]:
    if isinstance(u, M.Literal) and u.klass == "HELTAL":
        try:
            return int(u.varde)
        except (TypeError, ValueError):
            return None
    return None


def _positiv_tid(u: Optional[M.Uttryck]) -> bool:
    """PT ar en TIME-literal storre an noll. T#0s ar ingen tidsgrans."""
    if not isinstance(u, M.Literal) or u.klass != "TID":
        return False
    try:
        return float(u.varde) > 0.0
    except (TypeError, ValueError):
        return bool(re.search(r"[1-9]", u.text))


def _positiva(f, paritet: bool, ut: Set[str]) -> None:
    """Atomvariabler som star med JAMN negationsparitet i formeln."""
    if f is True or f is False:
        return
    slag = f[0]
    if slag == "N":
        _positiva(f[1], not paritet, ut)
        return
    if slag in ("&", "|"):
        _positiva(f[1], paritet, ut)
        _positiva(f[2], paritet, ut)
        return
    if paritet:
        ut |= set(f[1].varr)


def _noder(f) -> int:
    if f is True or f is False:
        return 1
    if f[0] == "A":
        return 1
    if f[0] == "N":
        return 1 + _noder(f[1])
    return 1 + _noder(f[1]) + _noder(f[2])
