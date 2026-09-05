# -*- coding: utf-8 -*-
"""Tolken: kör ett ST-PROGRAM scan för scan, i minnet.

Varför den finns. Bänkens facit ska gå att döma mekaniskt. Ett facit som är en
sekvens av (insignaler -> förväntade utsignaler) över tid går bara att döma om
någon faktiskt kör logiken. Den riktiga körningen är kedjan

    ST -> STruC++ -> OpenPLC Runtime v4 -> OPC UA -> kopplaren -> scenen

och den kedjan är mätt (M-20, M-39). Men den kräver en byggd STruC++, en
körande OpenPLC och i förlängningen VC. Utan en tolk går bänken inte att prova
alls förrän hela kedjan står. Med en tolk går varje uppgift att döma i ett
enda `pytest`-anrop, och kedjan blir andra mätpunkten på samma facit i stället
för den enda.

Vad tolken INTE är. Den är ingen kompilator och ingen runtime. Den ersätter
inte grind 1 (`STruC++`) och den bevisar ingenting om vad OpenPLC gör med
samma kod. Två motorer på samma facit kan drifta isär, och det är precis vad
`docs/matningar/M-45_bankens_tackning.md` säger ska mätas när kedjan står:
samma spår genom tolken och genom OpenPLC, och skillnaden redovisad. Tills dess
är tolkens dom en dom om ST-semantiken, inte om runtimen.

Modellen. En scan gör tre saker, i ordning, precis som en PLC:
läser in insignalerna, kör programkroppen en gång uppifrån och ned, och skriver
ut utsignalerna. Tiden går bara mellan scan, aldrig inuti en. Funktionsblockens
minne lever mellan scan.

beskriver: svc/vc_assist_svc/st/tolk.py, bank/domare.py
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from . import modell as M
from . import stdbibliotek as SB
from . import typer as T
from .lasare import las
from .lexer import tolka_tidliteral

# OpenPLC v4:s scanperiod, mätt i M-20: PLC:ns egen svarstid är exakt två scan,
# 40,0 ms vid 20 ms scanperiod. Tolken kör samma period som den uppmätta, så
# ett spår som håller här har en chans att hålla i kedjan.
SCAN_MS = 20.0                  # Mätt i M-20.

# Ett tak på antalet varv i WHILE och REPEAT. En PLC har en cykelvakt och en
# oändlig loop är där ett stopp, inte en hängning. Talet är satt, inte mätt:
# ingen uppgift i banken har en loop över hundra varv, och taket ska falla
# långt innan pytest ser ut att hänga.
MAX_LOOPVARV = 10000            # Satt av M-45.

# Så många scan tolken som mest kör i ett svep innan den ger upp. Bänkens
# längsta spår är under tre minuter simulerad tid; vid 20 ms scan är det
# 9000 scan. Taket ligger en tiopotens över och skyddar mot ett facit som
# råkar begära en timme.
MAX_SCAN = 100000               # Satt av M-45.

BOOL_SANNA = (True, False)


class Tolkfel(Exception):
    """Programmet går inte att köra. Kastar hellre än kör vidare på en gissning."""


def _tid_ms(lit: M.Literal) -> float:
    """TIME-literalen i millisekunder.

    Läsaren fyller i värdet när literalen är välformad. Är den det inte
    försöker vi en gång till med små bokstäver i enheterna: MATIEC, som
    OpenPLC bygger på, är okänslig för skiftläge, och tolken får inte
    underkänna kod som runtimen accepterar.
    """
    if lit.varde is not None:
        return float(lit.varde)
    ok, ms, varfor = tolka_tidliteral(lit.text)
    if ok:
        return float(ms)
    delar = lit.text.split("#", 1)
    if len(delar) == 2:
        ok, ms, _ = tolka_tidliteral(delar[0] + "#" + delar[1].lower())
        if ok:
            return float(ms)
    raise Tolkfel("TIME-literalen %r går inte att läsa: %s" % (lit.text, varfor))


class Blockinstans(object):
    """Ett standardfunktionsblock med minne mellan scan."""

    def __init__(self, sort: str, namn: str):
        self.sort = sort
        self.namn = namn
        self.ut: Dict[str, object] = {}
        self.et = 0.0
        self.forra_in = False
        self.loper = False
        self.cv = 0
        if sort in ("TON", "TOF", "TP"):
            self.ut = {"Q": False, "ET": 0.0}
            if sort == "TOF":
                self.ut["Q"] = False
        elif sort in ("R_TRIG", "F_TRIG"):
            self.ut = {"Q": False}
        elif sort in ("SR", "RS"):
            self.ut = {"Q1": False}
        elif sort == "CTU":
            self.ut = {"Q": False, "CV": 0}
        elif sort == "CTD":
            self.ut = {"Q": False, "CV": 0}
        elif sort == "CTUD":
            self.ut = {"QU": False, "QD": True, "CV": 0}
        else:
            raise Tolkfel("tolken kan inte köra funktionsblocket %s" % sort)

    # -- anropet ----------------------------------------------------------

    # De ingångar varje standardblock FAKTISKT har, enligt IEC 61131-3.
    # Listan finns för att ett okänt argumentnamn ska AVVISAS i stället för att
    # tyst falla bort. MÄTT i M-54: `c(CU := i, RESET := r, PV := 3)` gick rakt
    # igenom tolken, som läser reset ur "R" och därför tyst räknade vidare utan
    # nollställning. Samma kod översätts av STruC++ utan anmärkning men går
    # INTE att bygga — `class strucpp::CTU has no member named RESET`.
    #
    # En bänkuppgift skriven så hade alltså dömts av tolken på en semantik som
    # ingen runtime har. Ett argument som ingen läser är inte en detalj; det är
    # ett tyst bortfall mitt i det facit ska mäta.
    INGANGAR = {
        "TON": ("IN", "PT"),
        "TOF": ("IN", "PT"),
        "TP": ("IN", "PT"),
        "R_TRIG": ("CLK",),
        "F_TRIG": ("CLK",),
        "SR": ("S1", "R"),
        "RS": ("S", "R1"),
        "CTU": ("CU", "R", "PV"),
        "CTD": ("CD", "LD", "PV"),
        "CTUD": ("CU", "CD", "R", "LD", "PV"),
    }

    def anropa(self, arg: Dict[str, object], dt_ms: float):
        kanda = self.INGANGAR.get(self.sort, ())
        okanda = [n for n in arg if n.upper() not in kanda]
        if okanda:
            raise Tolkfel(
                "anropet till %s (%s) bar okanda ingangar: %s. %s tar %s"
                % (self.namn, self.sort, ", ".join(sorted(okanda)),
                   self.sort, ", ".join(kanda)))
        f = getattr(self, "_" + self.sort.lower())
        f(arg, dt_ms)

    def _kravs(self, arg, namn):
        if namn not in arg:
            raise Tolkfel("anropet till %s (%s) saknar %s"
                          % (self.namn, self.sort, namn))
        return arg[namn]

    # IEC 61131-3, tabell 36: Q blir hög när IN varit hög i PT, och ET nollas
    # när IN faller. Räknaren startas om på flanken, aldrig mitt i.
    def _ton(self, arg, dt_ms):
        inn = bool(self._kravs(arg, "IN"))
        pt = float(self._kravs(arg, "PT"))
        if inn and not self.forra_in:
            self.et = 0.0
        elif inn:
            self.et = min(self.et + dt_ms, pt)
        else:
            self.et = 0.0
        self.forra_in = inn
        self.ut["Q"] = inn and self.et >= pt
        self.ut["ET"] = self.et

    # TOF speglar TON: Q följer IN upp direkt och släpper först PT efter fallet.
    def _tof(self, arg, dt_ms):
        inn = bool(self._kravs(arg, "IN"))
        pt = float(self._kravs(arg, "PT"))
        if not inn and self.forra_in:
            self.et = 0.0
        elif not inn:
            self.et = min(self.et + dt_ms, pt)
        else:
            self.et = 0.0
        self.forra_in = inn
        self.ut["Q"] = inn or self.et < pt
        self.ut["ET"] = self.et

    # TP ger en puls på PT och går inte att trigga om under pulsen.
    def _tp(self, arg, dt_ms):
        inn = bool(self._kravs(arg, "IN"))
        pt = float(self._kravs(arg, "PT"))
        if self.loper:
            self.et = min(self.et + dt_ms, pt)
            if self.et >= pt:
                self.loper = False
        elif inn and not self.forra_in:
            self.loper = True
            self.et = 0.0
        if not inn and not self.loper:
            self.et = 0.0
        self.forra_in = inn
        self.ut["Q"] = self.loper
        self.ut["ET"] = self.et

    def _r_trig(self, arg, dt_ms):
        clk = bool(self._kravs(arg, "CLK"))
        self.ut["Q"] = clk and not self.forra_in
        self.forra_in = clk

    def _f_trig(self, arg, dt_ms):
        clk = bool(self._kravs(arg, "CLK"))
        self.ut["Q"] = (not clk) and self.forra_in
        self.forra_in = clk

    # IEC 61131-3, tabell 34: SR är SET-dominant, RS är RESET-dominant.
    def _sr(self, arg, dt_ms):
        s1 = bool(self._kravs(arg, "S1"))
        r = bool(self._kravs(arg, "R"))
        self.ut["Q1"] = s1 or (bool(self.ut["Q1"]) and not r)

    def _rs(self, arg, dt_ms):
        s = bool(self._kravs(arg, "S"))
        r1 = bool(self._kravs(arg, "R1"))
        self.ut["Q1"] = (not r1) and (s or bool(self.ut["Q1"]))

    def _ctu(self, arg, dt_ms):
        cu = bool(self._kravs(arg, "CU"))
        r = bool(arg.get("R", False))
        pv = int(self._kravs(arg, "PV"))
        if r:
            self.cv = 0
        elif cu and not self.forra_in:
            self.cv += 1
        self.forra_in = cu
        self.ut["CV"] = self.cv
        self.ut["Q"] = self.cv >= pv

    def _ctd(self, arg, dt_ms):
        cd = bool(self._kravs(arg, "CD"))
        ld = bool(arg.get("LD", False))
        pv = int(self._kravs(arg, "PV"))
        if ld:
            self.cv = pv
        elif cd and not self.forra_in:
            self.cv -= 1
        self.forra_in = cd
        self.ut["CV"] = self.cv
        self.ut["Q"] = self.cv <= 0

    def _ctud(self, arg, dt_ms):
        cu = bool(arg.get("CU", False))
        cd = bool(arg.get("CD", False))
        r = bool(arg.get("R", False))
        ld = bool(arg.get("LD", False))
        pv = int(self._kravs(arg, "PV"))
        forra_cu, forra_cd = getattr(self, "_forra_cu", False), getattr(self, "_forra_cd", False)
        if r:
            self.cv = 0
        elif ld:
            self.cv = pv
        else:
            if cu and not forra_cu:
                self.cv += 1
            if cd and not forra_cd:
                self.cv -= 1
        self._forra_cu, self._forra_cd = cu, cd
        self.ut["CV"] = self.cv
        self.ut["QU"] = self.cv >= pv
        self.ut["QD"] = self.cv <= 0


class _Avbrott(Exception):
    """EXIT ur en loop. Intern."""


class _Retur(Exception):
    """RETURN ur POU:n. Intern."""


NOLLVARDE = {"bool": False, "int": 0, "real": 0.0}


class Tolk(object):
    """Kör ett PROGRAM scan för scan mot en given signalkarta.

    Signalkartan kommer utifrån, ur uppgiftens `control.signals`, och bär
    riktningen. Riktningen är inte kosmetik: en skrivning till en insignal är
    ett verkligt fel — logiken hittar på ett givarvärde — och tolken fäller det
    i stället för att låta det se ut som att stationen fungerar.
    """

    def __init__(self, kalla: str, signaler: Optional[Dict[str, str]] = None,
                 riktningar: Optional[Dict[str, str]] = None,
                 scan_ms: float = SCAN_MS):
        self.scan_ms = float(scan_ms)
        self.tid_ms = 0.0
        self.scan_nr = 0
        try:
            enhet = las(kalla)
        except Exception as fel:                    # Syntaxfel och allt annat
            raise Tolkfel("koden går inte att läsa: %s" % (fel,))
        program = [p for p in enhet.pouer if p.sort == "PROGRAM"]
        if len(program) != 1:
            raise Tolkfel("tolken kör exakt ett PROGRAM, koden har %d"
                          % len(program))
        self.pou = program[0]
        self.egna_pouer = dict((p.namn.upper(), p) for p in enhet.pouer
                               if p.sort == "FUNCTION_BLOCK")

        self.riktning: Dict[str, str] = dict(riktningar or {})
        self.varden: Dict[str, object] = {}
        self.block: Dict[str, Blockinstans] = {}
        # Retentiva namn (VAR RETAIN) och ursprungsvärdena. Båda finns bara
        # för omstartsbegreppet nedan; utan dem går en varmstart inte att
        # skilja från en kallstart. Se `varmstart`.
        self._retain: set = set()
        self._blocksort: Dict[str, str] = {}
        self._deklarera(signaler or {})
        self._ursprung: Dict[str, object] = dict(self.varden)
        self.omstarter = 0

    # -- uppsättning ------------------------------------------------------

    def _deklarera(self, signaler: Dict[str, str]):
        # Signalkartan först: de finns oavsett om programmet deklarerar dem.
        # Bankens ST är skriven mot en karta, precis som M-39:s program, och
        # den som skriver `AT %IX0.0` ska inte dömas annorlunda än den som
        # skriver VAR_INPUT.
        for namn, typ in signaler.items():
            if typ not in NOLLVARDE:
                raise Tolkfel("okänd signaltyp %r för %s" % (typ, namn))
            self.varden[namn.upper()] = NOLLVARDE[typ]
        for block, dek in self.pou.deklarationer():
            namn = dek.namn.upper()
            typ = dek.typ
            if "RETAIN" in getattr(block, "kvalificerare", ()):
                self._retain.add(namn)
            if hasattr(typ, "namn") and typ.namn.upper() in SB.BLOCK:
                self.block[namn] = Blockinstans(typ.namn.upper(), dek.namn)
                self._blocksort[namn] = typ.namn.upper()
                continue
            if hasattr(typ, "namn") and typ.namn.upper() in self.egna_pouer:
                raise Tolkfel("tolken kör inte egna funktionsblock (%s)"
                              % typ.namn)
            self.varden[namn] = self._nollvarde(typ)
            if dek.init is not None:
                self.varden[namn] = self._varde(dek.init)
            if block.sort == "VAR_INPUT":
                self.riktning.setdefault(namn, "in")
            elif block.sort == "VAR_OUTPUT":
                self.riktning.setdefault(namn, "out")

    @staticmethod
    def _nollvarde(typ):
        if isinstance(typ, T.Pekare):
            return None
        namn = getattr(typ, "namn", "") or ""
        stor = namn.upper()
        if stor in ("BOOL", "BYTE", "WORD", "DWORD", "LWORD"):
            return False if stor == "BOOL" else 0
        if stor in ("REAL", "LREAL"):
            return 0.0
        if stor == "TIME":
            return 0.0
        if stor == "STRING" or stor == "WSTRING":
            return ""
        return 0

    # -- yttre gränssnitt -------------------------------------------------

    def satt(self, namn: str, varde):
        """Sätter en insignal. Fälls om namnet inte finns."""
        nyckel = namn.upper()
        if nyckel not in self.varden:
            raise Tolkfel("okänd signal %r" % (namn,))
        self.varden[nyckel] = varde

    def las(self, namn: str):
        nyckel = namn.upper()
        if nyckel in self.varden:
            return self.varden[nyckel]
        if "." in nyckel:
            bas, falt = nyckel.split(".", 1)
            if bas in self.block:
                return self.block[bas].ut.get(falt)
        raise Tolkfel("okänd signal %r" % (namn,))

    def scan(self):
        """Ett varv: kör kroppen en gång och flyttar klockan ett scansteg."""
        self.scan_nr += 1
        if self.scan_nr > MAX_SCAN:
            raise Tolkfel("över %d scan; spåret är orimligt långt" % MAX_SCAN)
        try:
            self._satser(self.pou.kropp)
        except _Retur:
            pass
        self.tid_ms += self.scan_ms

    def kor_till(self, t_ms: float):
        """Kör scan tills klockan når t_ms. Klockan står på scanrutnätet."""
        while self.tid_ms < t_ms - 1e-9:
            self.scan()

    # -- omstarten --------------------------------------------------------
    #
    # Byggd av M-173 (kö A, punkt A9). Före den hade tolken inget
    # omstartsbegrepp alls: ett spår kördes från scan 0 till slut och kunde
    # aldrig avbrytas av det som händer varje gång strömmen går eller någon
    # trycker på återställningen. `RETAIN` fanns i lexern, i modellen och i
    # validatorn, men ingenstans i körningen — kvalificeraren var alltså en
    # etikett utan verkan, och en uppgift kunde inte skilja en variabel som
    # ÖVERLEVER en omstart från en som inte gör det.
    #
    # IEC 61131-3:2003 §2.4.3.1: vid en VARM start behåller variabler som är
    # deklarerade RETAIN sitt värde; allt annat får sitt initialvärde. Vid en
    # KALL start får också de retentiva sitt initialvärde.
    #
    # Två saker som INTE nollställs, och skälen:
    #   * Insignalerna. Fältet ändras inte av att PLC:n startar om — givaren
    #     står kvar där den står, och bildtabellen läses om från den vid
    #     nästa scan. Att nollställa dem hade mätt "alla givare försvann"
    #     i stället för "styrningen startade om".
    #   * Klockan (`tid_ms`). Spåret är ett förlopp i verkligheten, och
    #     verkligheten pausar inte. Antalet omstarter räknas i `omstarter`.

    def varmstart(self):
        """Varm omstart: allt utom RETAIN får sitt initialvärde.

        Funktionsblocksinstanser (TON, R_TRIG, CTU …) nollställs likaså om de
        inte står i ett RETAIN-block: en flankdetektor som minns sitt
        föregående värde över en omstart hade sett en flank som aldrig hände.
        """
        self._starta_om(behall_retain=True)

    def kallstart(self):
        """Kall omstart: också RETAIN får sitt initialvärde."""
        self._starta_om(behall_retain=False)

    def _starta_om(self, behall_retain: bool):
        for namn, varde in self._ursprung.items():
            if behall_retain and namn in self._retain:
                continue
            if self.riktning.get(namn) == "in":
                continue
            self.varden[namn] = varde
        for namn, sort in self._blocksort.items():
            if behall_retain and namn in self._retain:
                continue
            self.block[namn] = Blockinstans(sort, namn)
        self.omstarter += 1

    # -- satser -----------------------------------------------------------

    def _satser(self, satser: Sequence[M.Sats]):
        for s in satser:
            self._sats(s)

    def _sats(self, s: M.Sats):
        if isinstance(s, M.Kommentar):
            return
        if isinstance(s, M.Tilldelning):
            self._tilldela(s)
            return
        if isinstance(s, M.Om):
            for gren in s.grenar:
                if self._sant(gren.villkor):
                    self._satser(gren.satser)
                    return
            if s.annars is not None:
                self._satser(s.annars)
            return
        if isinstance(s, M.Fall):
            v = self._varde(s.uttryck)
            for gren in s.grenar:
                for e in gren.etiketter:
                    till = e.till if e.till is not None else e.fran
                    if e.fran <= v <= till:
                        self._satser(gren.satser)
                        return
            if s.annars is not None:
                self._satser(s.annars)
            return
        if isinstance(s, M.Anropssats):
            self._anropa(s.anrop)
            return
        if isinstance(s, M.Medan):
            varv = 0
            while self._sant(s.villkor):
                varv += 1
                if varv > MAX_LOOPVARV:
                    raise Tolkfel("WHILE på rad %d snurrar över %d varv"
                                  % (s.rad, MAX_LOOPVARV))
                try:
                    self._satser(s.satser)
                except _Avbrott:
                    break
            return
        if isinstance(s, M.Upprepa):
            varv = 0
            while True:
                varv += 1
                if varv > MAX_LOOPVARV:
                    raise Tolkfel("REPEAT på rad %d snurrar över %d varv"
                                  % (s.rad, MAX_LOOPVARV))
                try:
                    self._satser(s.satser)
                except _Avbrott:
                    break
                if self._sant(s.villkor):
                    break
            return
        if isinstance(s, M.ForSats):
            start = int(self._varde(s.fran))
            slut = int(self._varde(s.till))
            steg = int(self._varde(s.steg)) if s.steg is not None else 1
            if steg == 0:
                raise Tolkfel("FOR på rad %d har steget 0" % s.rad)
            namn = s.styrvar.upper()
            if namn not in self.varden:
                raise Tolkfel("FOR på rad %d styr på odeklarerade %s"
                              % (s.rad, s.styrvar))
            varv = 0
            v = start
            while (steg > 0 and v <= slut) or (steg < 0 and v >= slut):
                varv += 1
                if varv > MAX_LOOPVARV:
                    raise Tolkfel("FOR på rad %d snurrar över %d varv"
                                  % (s.rad, MAX_LOOPVARV))
                self.varden[namn] = v
                try:
                    self._satser(s.satser)
                except _Avbrott:
                    break
                v += steg
            return
        if isinstance(s, M.Avbryt):
            raise _Avbrott()
        if isinstance(s, M.Retur):
            raise _Retur()
        raise Tolkfel("tolken kan inte köra satsen %s på rad %s"
                      % (type(s).__name__, getattr(s, "rad", "?")))

    def _tilldela(self, s: M.Tilldelning):
        mal = s.mal
        if isinstance(mal, M.Avreferering):
            ref = self._varde(mal.bas)
            if ref is None:
                raise Tolkfel("avreferering av NULL-pekare på rad %d" % s.rad)
            if not (isinstance(ref, tuple) and len(ref) == 2 and ref[0] == "REF"):
                raise Tolkfel("kan inte avreferera icke-pekare på rad %d" % s.rad)
            mal_namn = ref[1]
            self._skriv(mal_namn, self._varde(s.uttryck), s.rad)
            return
        if not isinstance(mal, M.Namn):
            raise Tolkfel("tolken tilldelar bara enkla namn, inte %s på rad %d"
                          % (type(mal).__name__, s.rad))
        namn = mal.ident.upper()
        if namn not in self.varden:
            raise Tolkfel("odeklarerat namn %r på rad %d" % (mal.ident, s.rad))
        self._skriv(mal.ident, self._varde(s.uttryck), s.rad)

    def _skriv(self, ident: str, varde, rad: int):
        namn = ident.upper()
        if namn not in self.varden:
            raise Tolkfel("odeklarerat namn %r på rad %d" % (ident, rad))
        if self.riktning.get(namn) == "in":
            raise Tolkfel("rad %d skriver till insignalen %s; en logik som "
                          "sätter sin egen givare mäter ingenting"
                          % (rad, ident))
        self.varden[namn] = varde

    # -- uttryck ----------------------------------------------------------

    def _sant(self, u: M.Uttryck) -> bool:
        return bool(self._varde(u))

    def _varde(self, u: M.Uttryck):
        if isinstance(u, M.Literal):
            if u.klass == "TID":
                return _tid_ms(u)
            if u.klass == "NULL":
                return None
            return u.varde
        if isinstance(u, M.Namn):
            namn = u.ident.upper()
            if namn in self.varden:
                return self.varden[namn]
            raise Tolkfel("odeklarerat namn %r på rad %d" % (u.ident, u.rad))
        if isinstance(u, M.Medlem):
            bas = u.bas
            if not isinstance(bas, M.Namn):
                raise Tolkfel("tolken läser bara fält på enkla namn, rad %d" % u.rad)
            inst = self.block.get(bas.ident.upper())
            if inst is None:
                raise Tolkfel("%s är ingen blockinstans, rad %d" % (bas.ident, u.rad))
            if u.falt.upper() not in inst.ut:
                raise Tolkfel("%s har ingen utgång %s, rad %d"
                              % (inst.sort, u.falt, u.rad))
            return inst.ut[u.falt.upper()]
        if isinstance(u, M.Avreferering):
            return self._avreferera_las(u)
        if isinstance(u, M.Unar):
            v = self._varde(u.operand)
            if u.op == "NOT":
                return (not v) if isinstance(v, bool) else ~int(v)
            if u.op == "-":
                return -v
            raise Tolkfel("okänd unär operator %r" % (u.op,))
        if isinstance(u, M.Binar):
            return self._binar(u)
        if isinstance(u, M.Anrop):
            return self._anropa(u)
        raise Tolkfel("tolken kan inte räkna ut %s" % type(u).__name__)

    def _avreferera_las(self, u: M.Avreferering):
        ref = self._varde(u.bas)
        if ref is None:
            raise Tolkfel("avreferering av NULL-pekare på rad %d" % u.rad)
        if not (isinstance(ref, tuple) and len(ref) == 2 and ref[0] == "REF"):
            raise Tolkfel("kan inte avreferera icke-pekare på rad %d" % u.rad)
        mal_namn = ref[1]
        if mal_namn not in self.varden:
            raise Tolkfel("odeklarerat namn %r på rad %d" % (mal_namn, u.rad))
        return self.varden[mal_namn]

    def _binar(self, u: M.Binar):
        op = u.op
        # AND och OR kortsluter inte i IEC 61131-3, men uttrycken här är
        # sidoeffektfria, så resultatet blir detsamma.
        v = self._varde(u.vanster)
        h = self._varde(u.hoger)
        if op == "AND":
            return (v and h) if isinstance(v, bool) and isinstance(h, bool) else int(v) & int(h)
        if op == "OR":
            return (v or h) if isinstance(v, bool) and isinstance(h, bool) else int(v) | int(h)
        if op == "XOR":
            return (bool(v) != bool(h)) if isinstance(v, bool) and isinstance(h, bool) \
                else int(v) ^ int(h)
        if op == "=":
            return v == h
        if op == "<>":
            return v != h
        if op == "<":
            return v < h
        if op == "<=":
            return v <= h
        if op == ">":
            return v > h
        if op == ">=":
            return v >= h
        if op == "+":
            return v + h
        if op == "-":
            return v - h
        if op == "*":
            return v * h
        if op == "/":
            if h == 0:
                raise Tolkfel("division med noll på rad %d" % u.rad)
            if isinstance(v, int) and isinstance(h, int) \
                    and not isinstance(v, bool) and not isinstance(h, bool):
                return int(v / h)          # IEC: heltalsdivision trunkerar
            return v / h
        if op == "MOD":
            if h == 0:
                raise Tolkfel("MOD med noll på rad %d" % u.rad)
            # IEC 61131-3: MOD har tecknet hos täljaren, python har det hos
            # nämnaren. Skillnaden syns bara på negativa tal, och den syns.
            return int(v) - int(h) * int(v / h)
        if op == "**":
            # Exponentoperatorn, tillagd av M-51 samtidigt som läsaren och
            # validatorn fick den. En operator som validatorn SLÄPPER IGENOM
            # men tolken inte kan räkna är ett hål i den andra motorn, inte
            # ett omfångsbeslut: banken skulle godkänna koden och sedan inte
            # kunna döma den. Heltalsbas med heltalsexponent ger heltal, som
            # IEC:s EXPT.
            if isinstance(h, float) or isinstance(v, float) or h < 0:
                return float(v) ** float(h)
            return int(v) ** int(h)
        raise Tolkfel("okänd operator %r på rad %d" % (op, u.rad))

    # -- anrop ------------------------------------------------------------

    def _anropa(self, a: M.Anrop):
        namn = a.namn.upper()
        if namn == "REF":
            return self._ref(a)
        if namn in self.block:
            return self._anropa_block(self.block[namn], a)
        if namn in SB.FUNKTIONER:
            return self._anropa_funktion(namn, a)
        if namn in SB.BLOCK:
            raise Tolkfel("%s är ett funktionsblock och måste ha en instans, rad %d"
                          % (a.namn, a.rad))
        raise Tolkfel("okänt anrop %r på rad %d; tolken kör bara "
                      "standardbibliotekets funktioner" % (a.namn, a.rad))

    def _ref(self, a: M.Anrop):
        if len(a.argument) != 1 or a.argument[0].ut:
            raise Tolkfel("REF tar exakt ett argument på rad %d" % a.rad)
        arg = a.argument[0].uttryck
        if not isinstance(arg, M.Namn):
            raise Tolkfel("tolken stöder bara REF till enkla namn på rad %d" % a.rad)
        namn = arg.ident.upper()
        if namn not in self.varden:
            raise Tolkfel("odeklarerat namn %r i REF på rad %d" % (arg.ident, a.rad))
        return ("REF", namn)

    def _anropa_block(self, inst: Blockinstans, a: M.Anrop):
        definition = SB.BLOCK[inst.sort]
        ordning = [p.namn for p in definition.ingangar]
        arg: Dict[str, object] = {}
        utbindningar = []
        for i, ar in enumerate(a.argument):
            if ar.namn is None:
                if i >= len(ordning):
                    raise Tolkfel("för många argument till %s på rad %d"
                                  % (inst.namn, a.rad))
                arg[ordning[i]] = self._varde(ar.uttryck)
                continue
            if ar.ut:
                utbindningar.append((ar.namn.upper(), ar.uttryck))
                continue
            arg[ar.namn.upper()] = self._varde(ar.uttryck)
        inst.anropa(arg, self.scan_ms)
        for falt, mal in utbindningar:
            if not isinstance(mal, M.Namn):
                raise Tolkfel("=> binder bara till ett namn, rad %d" % a.rad)
            self._skriv(mal.ident, inst.ut.get(falt), a.rad)
        return None

    def _anropa_funktion(self, namn: str, a: M.Anrop):
        vals = [self._varde(ar.uttryck) for ar in a.argument if not ar.ut]
        if namn == "ABS":
            return abs(vals[0])
        if namn == "SQRT":
            return float(vals[0]) ** 0.5
        if namn == "MIN":
            return min(vals)
        if namn == "MAX":
            return max(vals)
        if namn == "LIMIT":
            mn, v, mx = vals[0], vals[1], vals[2]
            return min(max(v, mn), mx)
        if namn == "SEL":
            return vals[2] if vals[0] else vals[1]
        if namn == "TRUNC":
            return int(vals[0])
        if namn == "LEN":
            return len(vals[0])
        if "_TO_" in namn:
            till = namn.split("_TO_", 1)[1]
            v = vals[0]
            if till == "BOOL":
                return bool(v)
            if till in ("REAL", "LREAL"):
                return float(v)
            if till == "TIME":
                return float(v)
            if till in ("STRING", "WSTRING"):
                return str(v)
            return int(v)
        raise Tolkfel("tolken kan inte räkna funktionen %s på rad %d"
                      % (namn, a.rad))


def kor(kalla: str, signaler: Dict[str, str], riktningar: Dict[str, str],
        insatser: Sequence, scan_ms: float = SCAN_MS) -> List[Dict[str, object]]:
    """Bekvämlighet: kör ett spår och lämna tillbaka en avläsning per scan.

    `insatser` är en sekvens av (t_ms, {signal: värde}). Värdena läggs på
    FÖRE den scan vars klocka är t_ms, precis som en givare byter värde mellan
    två scan.
    """
    tolk = Tolk(kalla, signaler, riktningar, scan_ms)
    plan = sorted(insatser, key=lambda x: x[0])
    slut = plan[-1][0] if plan else 0.0
    ut: List[Dict[str, object]] = []
    i = 0
    while tolk.tid_ms <= slut + 1e-9:
        while i < len(plan) and plan[i][0] <= tolk.tid_ms + 1e-9:
            for namn, v in plan[i][1].items():
                tolk.satt(namn, v)
            i += 1
        tolk.scan()
        ut.append({"t_ms": tolk.tid_ms - tolk.scan_ms,
                   "varden": dict(tolk.varden)})
    return ut
