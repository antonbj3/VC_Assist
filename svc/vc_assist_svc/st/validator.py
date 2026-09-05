# -*- coding: utf-8 -*-
"""Validator: ST-text in, lista av anmärkningar ut.

Tolv kontroller. Var och en står i fel.KONTROLLER med sin felklass ur
docs/spec/82_felklasser.md, och var och en har minst ett prov i
tests/enhet/ som visar att den fäller ett verkligt fel — en grind som aldrig
fällt är oprövad (docs/spec/95_testprotokoll.md, regel S2 i 96_ingen_skuld.md).

Fail-closed hela vägen (I3): kan en typ inte härledas, kan ett namn inte
slås upp, eller går texten inte att läsa, så är svaret "inte godkänt".
Tystnad är aldrig ett godkännande.

Dubbelskrivningskontrollen gäller **utgångar**, inte alla variabler. Skälet är
att felet den letar efter är den klassiska PLC-buggen "två ställen driver
samma utgång", medan en mellanlagringsvariabel som skrivs om är normal kod.
Utgång = VAR_OUTPUT, eller en variabel med AT %Q-adress, eller ett namn som
signalkartan lämnat med i `utgangar`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import modell as M
from . import stdbibliotek as SB
from . import typer as T
from . import uteslutning as U
from .fel import Anmarkning, Syntaxfel
from .lasare import las
from .lexer import tolka_tidliteral

JAMFORELSER = ("=", "<>", "<", ">", "<=", ">=")
LOGISKA = ("AND", "OR", "XOR")
ARITMETIK = ("+", "-", "*", "/")

# Strängfunktioner där första strängargumentet inte får vara en literal.
# MÄTT (M-108): STruC++ backend faller med mallhärledningsfel ("mismatched
# types 'const IECString<MaxLen>' and 'const char [N]'") när första
# strängargumentet är en literal; med variabel bygger allt.
STRANGFUNKTIONER_LITERAL = (
    "CONCAT", "LEFT", "RIGHT", "MID", "FIND", "LEN", "INSERT", "DELETE", "REPLACE"
)

# Sorter vars innehåll inte får skrivas inifrån POU:n. IEC 61131-3: ingången
# ägs av anroparen. VAR_EXTERNAL står medvetet INTE här — standarden tillåter
# att en extern variabel skrivs, och det är just så en utgång ur signalkartan
# ser ut när deklarationsdelen ligger i en annan fil.
EJ_SKRIVBARA = {"VAR_INPUT": "en VAR_INPUT ägs av anroparen"}

# Direktadressens storleksbokstav -> de typer som får ligga där.
# IEC 61131-3, tabell 16: X (och utelämnad bokstav) är en bit, B en byte,
# W ett ord, D ett dubbelord, L ett långord.
#
# MÄTT (M-99), inte antagen: sex bokstäver × sexton typer = 96 källor genom
# STruC++ 0.6.6. Kompilatorn byggde exakt de 16 paren nedan och avvisade de
# övriga 80 med sin egen ordalydelse ("Type 'BOOL' is not compatible with
# address size 'W'"). TIME saknas i varje rad: den har ingen adressbredd och
# byggde ingenstans.
ADRESSTORLEK = {
    "X": ("BOOL",),
    "B": ("BYTE", "SINT", "USINT"),
    "W": ("WORD", "INT", "UINT"),
    "D": ("DWORD", "DINT", "UDINT", "REAL"),
    "L": ("LWORD", "LINT", "ULINT", "LREAL"),
}


@dataclass(frozen=True)
class Post:
    namn: str
    typ: T.Typ
    sort: str
    konstant: bool = False
    skyddad: bool = False
    utgang: bool = False
    rad: int = 0


@dataclass(frozen=True)
class Signatur:
    """Gemensam form för standardblock, standardfunktioner och POU:er i filen.

    `krav` i en ingång är antingen en typklass ur stdbibliotek ("ANY_NUM")
    eller en färdig Typ. Att båda ryms i samma kontroll är avsikten: annars
    hade argumentkontrollen behövt skrivas två gånger, och två kopior av en
    regel driftar isär.
    """

    namn: str
    ingangar: Tuple[Tuple[str, object, bool], ...]
    utgangar: Tuple[Tuple[str, object], ...]
    ar_block: bool
    resultat: object = None
    variadisk: bool = False
    # Ingangar som VALJER men inte BIDRAR till resultattypen: SEL:s G och
    # MUX:s K. Utan den har listan rakande gemensamma typen ihop valjaren
    # med de valda, och SEL(bA, iB, iC) fick "ingen gemensam typ" fastan
    # bada de valda var INT. MATT i M-51.
    styrande: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Rapport:
    ok: bool
    anmarkningar: Tuple[Anmarkning, ...]

    def koder(self):
        return tuple(a.kod for a in self.anmarkningar)

    def __str__(self):
        if self.ok:
            return "GODKAND"
        return "EJ GODKAND\n" + "\n".join("  " + str(a) for a in self.anmarkningar)


def _signatur_av_block(b: SB.Blockdef) -> Signatur:
    return Signatur(b.namn,
                    tuple((p.namn, p.klass, False) for p in b.ingangar),
                    tuple((p.namn, p.klass) for p in b.utgangar),
                    True)


def _signatur_av_funktion(f: SB.Funktionsdef) -> Signatur:
    return Signatur(f.namn,
                    tuple((p.namn, p.klass, p.obligatorisk) for p in f.parametrar),
                    (), False, f.resultat, f.variadisk,
                    tuple(p.namn for p in f.parametrar if p.styrande))


@dataclass(frozen=True)
class Lov:
    """En enskild skrivning av en utgang: sokvagsvillkoret relativt den sats
    pa aktuell niva som bar den, raden och literalvardet (None for uttryck)."""
    villkor: object
    rad: int
    varde: object


@dataclass
class Bidrag:
    """Vad en sats bidrar med till en utgang: villkorad eller inte, forsta
    raden, det gemensamma literalvardet (None om grenarna skiljer sig eller
    nagon skriver ett uttryck), loven och miljon (mellanvariablernas
    definitioner) som galler fore satsen."""
    villkorad: bool
    rad: int
    varde: object
    lov: Tuple[Lov, ...]
    miljo: object = None


class Granskning(object):
    def __init__(self, enhet: M.Enhet, externa: Dict[str, T.Typ],
                 skyddade, utgangar):
        self.enhet = enhet
        self.anm: List[Anmarkning] = []
        self.strukturer = dict((s.namn.upper(), s) for s in enhet.typer)
        self.externa = dict((n.upper(), t) for n, t in (externa or {}).items())
        self.skyddade = set(n.upper() for n in (skyddade or ()))
        self.extra_utgangar = set(n.upper() for n in (utgangar or ()))
        self.signaturer = self._bygg_signaturer()
        self.omf: Dict[str, Post] = {}
        self.utgangsnamn = set()
        self.styrvariabler = set()
        self.slingdjup = 0
        self._ordning: Dict[int, int] = {}
        self._slut: Dict[int, int] = {}
        self._skrivpositioner: Dict[str, List[int]] = {}
        self._uteslutning = U.Uteslutning({})

    def fel(self, kod, rad, text):
        self.anm.append(Anmarkning(kod, rad, text))

    # ---- namnrymder -----------------------------------------------------

    def _bygg_signaturer(self) -> Dict[str, Signatur]:
        sig = {}
        for namn, b in SB.BLOCK.items():
            sig[namn] = _signatur_av_block(b)
        for namn, f in SB.FUNKTIONER.items():
            sig[namn] = _signatur_av_funktion(f)
        for p in self.enhet.pouer:
            if p.sort == "FUNCTION_BLOCK":
                sig[p.namn.upper()] = Signatur(
                    p.namn, self._parametrar(p, ("VAR_INPUT", "VAR_IN_OUT"), False),
                    tuple((d.namn.upper(), d.typ)
                          for b, d in p.deklarationer()
                          if b.sort in ("VAR_OUTPUT", "VAR_IN_OUT")),
                    True)
            elif p.sort == "FUNCTION":
                sig[p.namn.upper()] = Signatur(
                    p.namn, self._parametrar(p, ("VAR_INPUT", "VAR_IN_OUT"), True),
                    (), False, p.returtyp)
        return sig

    @staticmethod
    def _parametrar(p: M.Pou, sorter, obligatorisk):
        return tuple((d.namn.upper(), d.typ, obligatorisk and d.init is None)
                     for b, d in p.deklarationer() if b.sort in sorter)

    def _globala_poster(self):
        ut = {}
        for b in self.enhet.globala:
            self._kontrollera_kvalificerare(b)
            for d in b.deklarationer:
                self._kontrollera_adress(d)
                ut[d.namn.upper()] = Post(
                    d.namn, d.typ, b.sort, "CONSTANT" in b.kvalificerare,
                    d.skyddad or d.namn.upper() in self.skyddade,
                    self._ar_utgang(b.sort, d), d.rad)
        for namn, typ in self.externa.items():
            ut.setdefault(namn, Post(namn, typ, "VAR_EXTERNAL",
                                     False, namn in self.skyddade,
                                     namn in self.extra_utgangar))
        return ut

    def _ar_utgang(self, sort, d: M.Deklaration) -> bool:
        if sort == "VAR_OUTPUT":
            return True
        if d.adress and d.adress.upper().startswith("%Q"):
            return True
        return d.namn.upper() in self.extra_utgangar

    # ---- ingång ---------------------------------------------------------

    def granska(self):
        if not self.enhet.pouer:
            # Tystnad är aldrig ett godkännande (I3). En fil utan POU är inte
            # ett program som råkar vara felfritt, den är ingen leverans.
            self.fel("SYNTAX", 1, "källan innehåller ingen POU")
        for sd in self.enhet.typer:
            for d in sd.falt:
                self._kontrollera_typ(d.typ, d.rad)
        for p in self.enhet.pouer:
            self._granska_pou(p)
        return self.anm

    def _granska_pou(self, p: M.Pou):
        self.omf = self._globala_poster()
        self.utgangsnamn = set(n for n, post in self.omf.items() if post.utgang)
        self.styrvariabler = set()
        self.slingdjup = 0
        sedda = {}
        for b in p.block:
            self._kontrollera_kvalificerare(b)
        for b, d in p.deklarationer():
            nyckel = d.namn.upper()
            if nyckel in sedda:
                self.fel("DUBBELDEKLARATION", d.rad,
                         "%s är redan deklarerad på rad %d" % (d.namn, sedda[nyckel]))
                continue
            sedda[nyckel] = d.rad
            self._kontrollera_typ(d.typ, d.rad)
            self._kontrollera_adress(d)
            post = Post(d.namn, d.typ, b.sort, "CONSTANT" in b.kvalificerare,
                        d.skyddad or nyckel in self.skyddade,
                        self._ar_utgang(b.sort, d), d.rad)
            self.omf[nyckel] = post
            if post.utgang:
                self.utgangsnamn.add(nyckel)
            if d.init is not None:
                init_typ = self.typ_av(d.init)
                if init_typ is not None:
                    ok, skal = T.far_tilldelas(d.typ, init_typ)
                    if not ok:
                        self.fel("TYP", d.rad,
                                 "startvärdet för %s: %s" % (d.namn, skal))
        if p.sort == "FUNCTION":
            self.omf.setdefault(p.namn.upper(),
                                Post(p.namn, p.returtyp, "VAR", rad=p.rad))
        self._satser(p.kropp)
        self._oatkomlighet(p.kropp)
        self._ordning = {}
        self._slut = {}
        self._skrivpositioner = {}
        self._numrera_satser(p.kropp)
        self._uteslutning = U.Uteslutning(self._skrivpositioner)
        self._sekvens(p.kropp)

    def _kontrollera_kvalificerare(self, b: M.Varblock):
        """RETAIN och CONSTANT pa samma block.

        En konstant har inget tillstand att behalla over en varmstart - den
        satts om till samma varde varje gang - sa kvalificerarna sager emot
        varandra. MATT (M-99): STruC++ 0.6.6 avvisar `VAR RETAIN CONSTANT`
        med "Variable cannot be both RETAIN and CONSTANT"; vart lager slappte
        igenom den, alltsa ett hal at det hall dar felet syns forst i bygget.
        """
        kval = set(b.kvalificerare)
        if "CONSTANT" in kval and ("RETAIN" in kval or "NON_RETAIN" in kval):
            behall = "RETAIN" if "RETAIN" in kval else "NON_RETAIN"
            self.fel("TYP", b.rad,
                     "%s och CONSTANT gar inte ihop pa samma %s-block: en "
                     "konstant har inget tillstand att behalla"
                     % (behall, b.sort))

    def _kontrollera_adress(self, d: M.Deklaration):
        """Adressens storleksbokstav mot den deklarerade typen.

        `q AT %QW1 : BOOL;` ar ingen typfraga inne i ST-koden - den ar en
        fraga om VAR i bildtabellen variabeln ligger, och en BOOL pa en
        ordadress lasar och skriver fel antal byte i drift.

        Tabellen ar MATT, inte antagen (M-99): 96 kombinationer av sex
        storleksbokstaver och sexton typer genom STruC++ 0.6.6. Kompilatorn
        godkande exakt de par som star har och avvisade de ovriga 80 - och
        vart lager slappte igenom alla 96. Talet 80 ar hela halet.
        """
        if not d.adress:
            return
        adr = d.adress.upper()
        storlek = adr[2] if len(adr) > 2 and adr[2] in "XBWDL" else "X"
        tillatna = ADRESSTORLEK[storlek]
        if not isinstance(d.typ, T.Elementar) or d.typ.namn not in tillatna:
            self.fel("TYP", d.rad,
                     "%s AT %s: storleken %s tar %s, inte %s"
                     % (d.namn, d.adress, storlek, "/".join(sorted(tillatna)),
                        d.typ.st()))

    def _kontrollera_typ(self, typ: T.Typ, rad: int):
        if isinstance(typ, T.Falt):
            self._kontrollera_typ(typ.element, rad)
        elif isinstance(typ, T.Strukturtyp):
            if typ.namn.upper() not in self.strukturer:
                self.fel("OKANT_NAMN", rad,
                         "typen %s är varken elementär, en STRUCT i filen "
                         "eller ett känt funktionsblock" % typ.namn)
        elif isinstance(typ, T.Blocktyp):
            if typ.namn.upper() not in self.signaturer:
                self.fel("OKANT_NAMN", rad, "okänt funktionsblock %s" % typ.namn)

    # ---- satser ---------------------------------------------------------

    def _satser(self, satser):
        for s in satser:
            self._sats(s)

    def _sats(self, s: M.Sats):
        if isinstance(s, M.Kommentar):
            return
        if isinstance(s, M.Tilldelning):
            hoger = self.typ_av(s.uttryck)
            self._skrivmal(s.mal, s.rad)
            vanster = self.typ_av(s.mal)
            if vanster is not None and hoger is not None:
                ok, skal = T.far_tilldelas(vanster, hoger)
                if not ok:
                    self.fel("TYP", s.rad, skal)
            return
        if isinstance(s, M.Anropssats):
            self._anrop(s.anrop, som_sats=True)
            return
        if isinstance(s, M.Om):
            for g in s.grenar:
                self._villkor(g.villkor, "IF")
                self._satser(g.satser)
            if s.annars is not None:
                self._satser(s.annars)
            return
        if isinstance(s, M.Fall):
            t = self.typ_av(s.uttryck)
            if t is not None and not T.ar_heltal(t):
                self.fel("TYP", s.rad,
                         "CASE kräver ett heltalsuttryck, inte %s" % t.st())
            for g in s.grenar:
                if t is not None:
                    for e in g.etiketter:
                        for v in (e.fran, e.till):
                            if v is None:
                                continue
                            ok, skal = T.far_tilldelas(t, T.Literaltyp("HELTAL", v))
                            if not ok:
                                self.fel("TYP", g.rad, "CASE-etikett: %s" % skal)
                self._satser(g.satser)
            if s.annars is not None:
                self._satser(s.annars)
            return
        if isinstance(s, M.ForSats):
            post = self._slau(s.styrvar, s.rad)
            if post is not None and not T.ar_heltal(post.typ):
                self.fel("TYP", s.rad,
                         "styrvariabeln %s måste vara heltal, inte %s"
                         % (s.styrvar, post.typ.st()))
            for u in (s.fran, s.till, s.steg):
                if u is None:
                    continue
                t = self.typ_av(u)
                if t is not None and not T.ar_heltal(t):
                    self.fel("TYP", s.rad,
                             "FOR-gränserna måste vara heltal, inte %s" % t.st())
            self.styrvariabler.add(s.styrvar.upper())
            self.slingdjup += 1
            self._satser(s.satser)
            self.slingdjup -= 1
            self.styrvariabler.discard(s.styrvar.upper())
            return
        if isinstance(s, M.Medan):
            self._villkor(s.villkor, "WHILE")
            self.slingdjup += 1
            self._satser(s.satser)
            self.slingdjup -= 1
            return
        if isinstance(s, M.Upprepa):
            self.slingdjup += 1
            self._satser(s.satser)
            self.slingdjup -= 1
            self._villkor(s.villkor, "UNTIL")
            return
        if isinstance(s, M.Avbryt):
            if self.slingdjup == 0:
                self.fel("SYNTAX", s.rad, "EXIT står utanför alla slingor")
            return
        if isinstance(s, M.Retur):
            return
        self.fel("SYNTAX", getattr(s, "rad", 0),
                 "okänd satstyp %s" % type(s).__name__)

    def _villkor(self, u: M.Uttryck, vad: str):
        t = self.typ_av(u)
        if t is not None and not T.ar_bitlogisk(t):
            self.fel("TYP", getattr(u, "rad", 0),
                     "%s kräver ett booleskt villkor, inte %s" % (vad, t.st()))

    # ---- skrivmål -------------------------------------------------------

    def _skrivmal(self, mal: M.Uttryck, rad: int):
        rot = mal
        while isinstance(rot, (M.Medlem, M.Element)):
            rot = rot.bas
        if not isinstance(rot, M.Namn):
            self.fel("SYNTAX", rad, "vänsterledet går inte att skriva till")
            return
        post = self._slau(rot.ident, rad)
        if post is None:
            return
        if post.skyddad:
            self.fel("SAKERHET", rad,
                     "%s är märkt {SAKERHET} och får inte skrivas av genererad "
                     "kod (invariant I15)" % post.namn)
        if post.konstant:
            self.fel("RIKTNING", rad, "%s är CONSTANT" % post.namn)
        elif post.sort in EJ_SKRIVBARA:
            self.fel("RIKTNING", rad,
                     "%s är %s: %s" % (post.namn, post.sort, EJ_SKRIVBARA[post.sort]))
        if rot.ident.upper() in self.styrvariabler:
            self.fel("RIKTNING", rad,
                     "%s är styrvariabel i en pågående FOR och får inte skrivas"
                     % post.namn)

    def _slau(self, namn: str, rad: int) -> Optional[Post]:
        post = self.omf.get(namn.upper())
        if post is None:
            self.fel("ODEKLARERAD", rad, "%s är inte deklarerad" % namn)
        return post

    # ---- uttryckstyper --------------------------------------------------

    def typ_av(self, u: M.Uttryck) -> Optional[T.Typ]:
        if isinstance(u, M.Namn):
            post = self._slau(u.ident, u.rad)
            return None if post is None else post.typ
        if isinstance(u, M.Literal):
            return self._literaltyp(u)
        if isinstance(u, M.Medlem):
            return self._medlemstyp(u)
        if isinstance(u, M.Avreferering):
            return self._avrefereringstyp(u)
        if isinstance(u, M.Element):
            return self._elementtyp(u)
        if isinstance(u, M.Anrop):
            return self._anrop(u, som_sats=False)
        if isinstance(u, M.Unar):
            t = self.typ_av(u.operand)
            if t is None:
                return None
            if u.op == "NOT":
                if not T.ar_bitlogisk(t):
                    self.fel("TYP", u.rad, "NOT kräver BOOL eller bitsträng, inte %s"
                             % t.st())
                    return None
                return t
            if not T.ar_numerisk(t):
                self.fel("TYP", u.rad, "minustecken kräver ett tal, inte %s" % t.st())
                return None
            # Minustecknet hör till LITERALEN, inte till uttrycket runt den.
            #
            # MÄTT (M-99): `iA := -32768;` avvisades med "literalen 32768
            # ligger utanför INT (-32768..32767)". Talet i meddelandet var
            # 32768 därför att unärt minus lämnade literalvärdet orört och
            # intervallkontrollen därför prövade fel tal. INT:s minsta värde
            # är inte skrivbart som INT-literal utan den här raden, och
            # STruC++ 0.6.6 kompilerar formen.
            if isinstance(t, T.Literaltyp) and t.klass in ("HELTAL", "REAL"):
                return T.Literaltyp(t.klass, -t.varde)
            return t
        if isinstance(u, M.Binar):
            return self._binartyp(u)
        self.fel("TYP", getattr(u, "rad", 0),
                 "okänd uttrycksform %s" % type(u).__name__)
        return None

    def _literaltyp(self, u: M.Literal) -> Optional[T.Typ]:
        if u.klass == "TID":
            ok, _varde, skal = tolka_tidliteral(u.text)
            if not ok:
                self.fel("TIDLITERAL", u.rad, "%s: %s" % (u.text, skal))
                return None
            return T.TIME
        if u.typnamn:
            typ = T.Elementar(u.typnamn)
            varde = T.Literaltyp("HELTAL" if u.klass == "HELTAL" else "REAL", u.varde)
            ok, skal = T.far_tilldelas(typ, varde)
            if not ok:
                self.fel("TYP", u.rad, "%s: %s" % (u.text, skal))
                return None
            return typ
        return T.Literaltyp(u.klass, u.varde)

    def _medlemstyp(self, u: M.Medlem) -> Optional[T.Typ]:
        bas = self.typ_av(u.bas)
        if bas is None:
            return None
        if isinstance(bas, T.Blocktyp):
            sig = self.signaturer.get(bas.namn.upper())
            if sig is None:
                self.fel("OKANT_NAMN", u.rad, "okänt funktionsblock %s" % bas.namn)
                return None
            for namn, krav, _obl in sig.ingangar:
                if namn == u.falt.upper():
                    return self._som_typ(krav)
            for namn, krav in sig.utgangar:
                if namn == u.falt.upper():
                    return self._som_typ(krav)
            self.fel("OKANT_NAMN", u.rad,
                     "%s har ingen anslutning som heter %s" % (bas.namn, u.falt))
            return None
        if isinstance(bas, T.Strukturtyp):
            sd = self.strukturer.get(bas.namn.upper())
            if sd is None:
                self.fel("OKANT_NAMN", u.rad, "okänd struktur %s" % bas.namn)
                return None
            for d in sd.falt:
                if d.namn.upper() == u.falt.upper():
                    return d.typ
            self.fel("OKANT_NAMN", u.rad,
                     "strukturen %s har inget fält som heter %s" % (bas.namn, u.falt))
            return None
        self.fel("TYP", u.rad, "%s har inga fält" % bas.st())
        return None

    def _avrefereringstyp(self, u: M.Avreferering) -> Optional[T.Typ]:
        # M-108: bas^ ger pekarens måltyp. Avreferering av något som inte är
        # REF_TO är ett fel, inte en tolkning (fail-closed).
        bas = self.typ_av(u.bas)
        if bas is None:
            return None
        if not isinstance(bas, T.Pekare):
            self.fel("TYP", u.rad, "kan bara avreferera REF_TO, inte %s"
                     % bas.st())
            return None
        return bas.element

    @staticmethod
    def _ar_pekar_null_jamforelse(a, b) -> bool:
        # M-108: pRef = NULL genererar PREF == IEC_NULL i backend och bygger.
        # Endast NULL-literalen är undantagen; pekare-mot-pekare förblir
        # avvisad (fail-closed — backendbeteendet där är omätt).
        def ar_null(t):
            return isinstance(t, T.Literaltyp) and t.klass == "NULL"
        return ((isinstance(a, T.Pekare) and ar_null(b))
                or (isinstance(b, T.Pekare) and ar_null(a)))

    def _elementtyp(self, u: M.Element) -> Optional[T.Typ]:
        bas = self.typ_av(u.bas)
        for i in u.index:
            it = self.typ_av(i)
            if it is not None and not T.ar_heltal(it):
                self.fel("TYP", u.rad, "fältindex måste vara heltal, inte %s" % it.st())
        if bas is None:
            return None
        if not isinstance(bas, T.Falt):
            self.fel("TYP", u.rad, "%s är inget fält och kan inte indexeras" % bas.st())
            return None
        if len(u.index) != len(bas.granser):
            self.fel("TYP", u.rad,
                     "fältet har %d dimensioner men indexeras med %d"
                     % (len(bas.granser), len(u.index)))
            return None
        for i, (lo, hi) in zip(u.index, bas.granser):
            if isinstance(i, M.Literal) and i.klass == "HELTAL":
                if not (lo <= int(i.varde) <= hi):
                    self.fel("TYP", u.rad,
                             "index %d ligger utanför %d..%d" % (int(i.varde), lo, hi))
        return bas.element

    def _binartyp(self, u: M.Binar) -> Optional[T.Typ]:
        a = self.typ_av(u.vanster)
        b = self.typ_av(u.hoger)
        if a is None or b is None:
            return None
        if u.op in LOGISKA:
            if not (T.ar_bitlogisk(a) and T.ar_bitlogisk(b)):
                self.fel("TYP", u.rad, "%s kräver BOOL eller bitsträngar, inte %s och %s"
                         % (u.op, a.st(), b.st()))
                return None
            gem = T.gemensam_typ(a, b)
            if gem is None:
                self.fel("TYP", u.rad,
                         "%s och %s går inte ihop i %s" % (a.st(), b.st(), u.op))
            return gem
        if u.op == "MOD":
            if not (T.ar_heltal(a) and T.ar_heltal(b)):
                self.fel("TYP", u.rad, "MOD kräver heltal, inte %s och %s"
                         % (a.st(), b.st()))
                return None
            return T.gemensam_typ(a, b)
        if u.op in JAMFORELSER:
            if self._ar_pekar_null_jamforelse(a, b):
                return T.BOOL
            if isinstance(a, (T.Strukturtyp, T.Falt)) or isinstance(b, (T.Strukturtyp, T.Falt)):
                self.fel("TYP", u.rad,
                         "likhet (%s) gäller bara elementära typer, inte %s och %s "
                         "(backend saknar operator==)"
                         % (u.op, a.st(), b.st()))
                return None
            if isinstance(a, T.Blocktyp) or isinstance(b, T.Blocktyp):
                self.fel("TYP", u.rad,
                         "en funktionsblocksinstans kan inte jämföras")
                return None
            if T.gemensam_typ(a, b) is None:
                self.fel("TYP", u.rad, "%s och %s går inte att jämföra"
                         % (a.st(), b.st()))
                return None
            return T.BOOL
        if u.op == "**":
            # IEC 61131-3: samma regel som EXPT. Resultatet har BASENS typ,
            # inte den gemensamma: 2.0 ** 2 ar REAL, inte heltal.
            if not (T.ar_numerisk(a) and T.ar_numerisk(b)):
                self.fel("TYP", u.rad, "** kräver tal, inte %s och %s"
                         % (a.st(), b.st()))
                return None
            return a
        if u.op in ARITMETIK:
            if T.ar_tid(a) or T.ar_tid(b):
                # Tid har egna regler och far inte falla igenom till
                # talreglerna: da skulle samma fel anmarkas tva ganger.
                return self._tidsaritmetik(u, a, b)
            if not (T.ar_numerisk(a) and T.ar_numerisk(b)):
                self.fel("TYP", u.rad, "%s kräver tal, inte %s och %s"
                         % (u.op, a.st(), b.st()))
                return None
            gem = T.gemensam_typ(a, b)
            if gem is None:
                self.fel("TYP", u.rad,
                         "%s och %s går inte ihop i %s; konvertera uttryckligen"
                         % (a.st(), b.st(), u.op))
            return gem
        self.fel("TYP", u.rad, "okänd operator %s" % u.op)
        return None

    def _tidsaritmetik(self, u, a, b):
        """TIME + TIME, TIME - TIME, TIME * tal, TIME / tal. IEC 61131-3."""
        if u.op in ("+", "-") and T.ar_tid(a) and T.ar_tid(b):
            return T.TIME
        if u.op in ("*", "/") and T.ar_tid(a) and T.ar_numerisk(b):
            return T.TIME
        self.fel("TYP", u.rad,
                 "%s %s %s är ingen tillåten tidsoperation" % (a.st(), u.op, b.st()))
        return None

    def _som_typ(self, krav) -> Optional[T.Typ]:
        if isinstance(krav, T.Typ):
            return krav
        if krav in T.ELEMENTARA:
            return T.Elementar(krav)
        return None

    # ---- anrop ----------------------------------------------------------

    def _anrop(self, a: M.Anrop, som_sats: bool) -> Optional[T.Typ]:
        post = self.omf.get(a.namn.upper())
        if post is not None:
            if not isinstance(post.typ, T.Blocktyp):
                self.fel("TYP", a.rad, "%s är ingen blockinstans och kan inte anropas"
                         % a.namn)
                return None
            sig = self.signaturer.get(post.typ.namn.upper())
            if sig is None:
                self.fel("OKANT_NAMN", a.rad, "okänt funktionsblock %s" % post.typ.namn)
                return None
            if not som_sats:
                self.fel("TYP", a.rad,
                         "blockinstansen %s måste anropas som egen sats; "
                         "läs utgången med %s.Q efteråt" % (a.namn, a.namn))
                return None
            self._argumentkontroll(a, sig, kraven_obligatoriska=False)
            return None
        if a.namn.upper() == "REF":
            # M-108: REF(x) är en specialform, ingen biblioteksfunktion.
            # Den står inte i FUNKTIONER därför att namnsvepet bygger varje
            # funktion generiskt (v_INT := F(v_INT)) — en form som för REF
            # alltid är ogiltig (pekaren kan inte bo i en INT).
            return self._ref_anrop(a)
        sig = self.signaturer.get(a.namn.upper())
        if sig is None:
            self.fel("OKANT_NAMN", a.rad,
                     "%s är varken en deklarerad blockinstans, en funktion i "
                     "filen eller en standardfunktion" % a.namn)
            return None
        if sig.ar_block:
            self.fel("OKANT_NAMN", a.rad,
                     "%s är en blocktyp; anropa en deklarerad instans av den, "
                     "inte typen" % a.namn)
            return None
        if som_sats:
            self.fel("TYP", a.rad,
                     "funktionen %s anropas som sats och resultatet försvinner"
                     % a.namn)
        argtyper = self._argumentkontroll(a, sig, kraven_obligatoriska=True)
        return self._resultattyp(sig, argtyper, a.rad)

    def _argumentkontroll(self, a: M.Anrop, sig: Signatur, kraven_obligatoriska):
        namngivna = [x for x in a.argument if x.namn is not None]
        positionella = [x for x in a.argument if x.namn is None]
        if namngivna and positionella:
            self.fel("ARGUMENT", a.rad,
                     "%s anropas med både namngivna och positionella argument"
                     % a.namn)
        bundna = {}
        for i, arg in enumerate(positionella):
            if i >= len(sig.ingangar):
                # Variadisk styrs av signaturens egen flagga. Att doma per
                # namn ("MIN", "MAX") gjorde varje ny variadisk funktion till
                # ett tyst argumentfel tills nagon kom ihag att fylla pa
                # listan; MUX och CONCAT var precis sadana. MATT i M-51.
                if sig.variadisk and sig.ingangar:
                    bundna["IN%d" % (i + 1)] = (sig.ingangar[-1][1], arg)
                    continue
                self.fel("ARGUMENT", arg.rad,
                         "%s tar %d argument, inte %d"
                         % (a.namn, len(sig.ingangar), len(positionella)))
                break
            bundna[sig.ingangar[i][0]] = (sig.ingangar[i][1], arg)
        anslutningar = dict((n, k) for n, k, _o in sig.ingangar)
        utgangar = dict(sig.utgangar)
        for arg in namngivna:
            nyckel = arg.namn.upper()
            if arg.ut:
                if nyckel not in utgangar:
                    self.fel("ARGUMENT", arg.rad,
                             "%s har ingen utgång som heter %s" % (a.namn, arg.namn))
                    self.typ_av(arg.uttryck)
                    continue
                self._skrivmal(arg.uttryck, arg.rad)
                mal = self.typ_av(arg.uttryck)
                kalla = self._som_typ(utgangar[nyckel])
                if mal is not None and kalla is not None:
                    ok, skal = T.far_tilldelas(mal, kalla)
                    if not ok:
                        self.fel("TYP", arg.rad, "%s => : %s" % (arg.namn, skal))
                continue
            if nyckel not in anslutningar:
                self.fel("ARGUMENT", arg.rad,
                         "%s har ingen ingång som heter %s" % (a.namn, arg.namn))
                self.typ_av(arg.uttryck)
                continue
            if nyckel in bundna:
                self.fel("ARGUMENT", arg.rad,
                         "%s binds två gånger i samma anrop" % arg.namn)
                self.typ_av(arg.uttryck)
                continue
            bundna[nyckel] = (anslutningar[nyckel], arg)
        if kraven_obligatoriska:
            for namn, _krav, obl in sig.ingangar:
                if obl and namn not in bundna:
                    self.fel("ARGUMENT", a.rad,
                             "%s saknar argumentet %s" % (a.namn, namn))
        if a.namn.upper() in STRANGFUNKTIONER_LITERAL:
            if sig.ingangar:
                forsta_namn = sig.ingangar[0][0]
                if forsta_namn in bundna:
                    _krav, forsta_arg = bundna[forsta_namn]
                    if isinstance(forsta_arg.uttryck, M.Literal):
                        # M-108: backend härleder IECString-mallen från ett
                        # variabelargument (static_cast på literalen — mätt
                        # för FIND('abcdef', sB) som bygger). Bara när INGET
                        # strängargument är en variabel faller bygget.
                        har_variabel = any(
                            krav == "STRING"
                            and isinstance(arg.uttryck,
                                           (M.Namn, M.Medlem, M.Element))
                            for _n, (krav, arg) in bundna.items())
                        if not har_variabel:
                            self.fel("TYP", forsta_arg.rad,
                                     "%s: strängliteral utan variabel bland "
                                     "strängargumenten "
                                     "(backendens mallhärledning faller; med "
                                     "variabel bygger det)" % a.namn)
        argtyper = {}
        for namn, (krav, arg) in bundna.items():
            t = self.typ_av(arg.uttryck)
            if t is None:
                continue
            argtyper[namn] = t
            if isinstance(krav, T.Typ):
                ok, skal = T.far_tilldelas(krav, t)
                if not ok:
                    self.fel("TYP", arg.rad, "%s.%s: %s" % (a.namn, namn, skal))
            elif not SB.passar(krav, t):
                self.fel("TYP", arg.rad,
                         "%s.%s kräver %s men fick %s" % (a.namn, namn, krav, t.st()))
        return argtyper

    def _ref_anrop(self, a: M.Anrop) -> Optional[T.Typ]:
        # M-108: REF(variabel) ger REF_TO av variabelns typ. Argumentet måste
        # vara adresserbart (Namn/Medlem/Element — aldrig literal, aldrig
        # pekare-till-pekare, aldrig blockinstans). Backend bygger REF(iA)
        # till IEC_REF_TO; REF(5) har ingen adress att ta.
        if len(a.argument) != 1 or a.argument[0].ut:
            self.fel("ARGUMENT", a.rad, "REF tar exakt ett argument: REF(variabel)")
            return None
        arg = a.argument[0]
        if arg.namn is not None and arg.namn.upper() != "IN":
            self.fel("ARGUMENT", a.rad, "REF har inget argument %s" % arg.namn)
            return None
        if not isinstance(arg.uttryck, (M.Namn, M.Medlem, M.Element)):
            self.fel("TYP", a.rad, "REF kräver en variabel, inte en literal")
            return None
        t = self.typ_av(arg.uttryck)
        if t is None:
            return None
        if isinstance(t, (T.Literaltyp, T.Pekare, T.Blocktyp)):
            self.fel("TYP", a.rad, "REF kan inte ta adressen av %s" % t.st())
            return None
        return T.Pekare(t)

    def _resultattyp(self, sig: Signatur, argtyper, rad) -> Optional[T.Typ]:
        r = sig.resultat
        if isinstance(r, T.Typ):
            return r
        if r is None:
            return None
        if r.startswith("="):
            return argtyper.get(r[1:])
        if r == "GEM":
            gem = None
            for namn, t in argtyper.items():
                if namn in sig.styrande:
                    continue
                gem = t if gem is None else T.gemensam_typ(gem, t)
                if gem is None:
                    self.fel("TYP", rad,
                             "argumenten till %s har ingen gemensam typ" % sig.namn)
                    return None
            return gem
        if r == "STRING":
            return T.Strang(None)
        return T.Elementar(r) if r in T.ELEMENTARA else None

    # ---- oåtkomlig kod --------------------------------------------------

    def _oatkomlighet(self, satser):
        for i, s in enumerate(satser):
            if isinstance(s, (M.Retur, M.Avbryt)):
                nasta = [x for x in satser[i + 1:] if not isinstance(x, M.Kommentar)]
                if nasta:
                    ord_ = "RETURN" if isinstance(s, M.Retur) else "EXIT"
                    self.fel("OATKOMLIG", nasta[0].rad,
                             "koden här nås aldrig; %s på rad %d lämnar alltid först"
                             % (ord_, s.rad))
                break
        for s in satser:
            if isinstance(s, M.Om):
                for j, g in enumerate(s.grenar):
                    k = konstant_bool(g.villkor)
                    if k is False:
                        self.fel("OATKOMLIG", g.rad,
                                 "villkoret är alltid falskt; grenen körs aldrig")
                    elif k is True and (j + 1 < len(s.grenar) or s.annars is not None):
                        self.fel("OATKOMLIG", g.rad,
                                 "villkoret är alltid sant; grenarna efter den "
                                 "här nås aldrig")
            if isinstance(s, M.Medan) and konstant_bool(s.villkor) is False:
                self.fel("OATKOMLIG", s.rad,
                         "WHILE-villkoret är alltid falskt; kroppen körs aldrig")
            if isinstance(s, M.Fall):
                sedda = {}
                for g in s.grenar:
                    for e in g.etiketter:
                        for v in e.varden():
                            if v in sedda:
                                self.fel("OATKOMLIG", g.rad,
                                         "etiketten %d täcks redan av grenen på "
                                         "rad %d" % (v, sedda[v]))
                            else:
                                sedda[v] = g.rad
            for lista in underlistor(s):
                self._oatkomlighet(lista)

    # ---- dubbelskrivning ------------------------------------------------
    #
    # Varje skrivning bar sitt SOKVAGSVILLKOR (uteslutning.py). Tva villkorade
    # skrivningar med olika varden falls bara om villkoren KAN vara sanna i
    # samma scan - avgjort med en SAT-sokning, inte med ett syntaktiskt "tva
    # IF-block". Mellanvariabler foljs nar det ar sunt (M-121).

    def _numrera_satser(self, satser) -> None:
        """Forordning over alla satser och var varje variabel tilldelas.

        Positionerna ar det som gor uteslutningsprovet sunt: ett namn betyder
        samma sak pa tva stallen bara om ingen skrivit det emellan.
        """
        for s in satser:
            self._ordning[id(s)] = len(self._ordning) + 1
            pos = self._ordning[id(s)]
            if isinstance(s, M.Tilldelning):
                self._notera_skrivning(self._rotnamn(s.mal), pos)
            elif isinstance(s, M.Anropssats):
                self._notera_skrivning(s.anrop.namn.upper(), pos)
                for arg in s.anrop.argument:
                    if arg.ut:
                        self._notera_skrivning(self._rotnamn(arg.uttryck), pos)
            elif isinstance(s, M.ForSats):
                self._notera_skrivning(s.styrvar.upper(), pos)
            for lista in underlistor(s):
                self._numrera_satser(lista)
            self._slut[id(s)] = len(self._ordning)

    def _notera_skrivning(self, namn: Optional[str], pos: int) -> None:
        if namn:
            self._skrivpositioner.setdefault(namn, []).append(pos)

    @staticmethod
    def _rotnamn(mal: M.Uttryck) -> Optional[str]:
        rot = mal
        while isinstance(rot, (M.Medlem, M.Element)):
            rot = rot.bas
        return rot.ident.upper() if isinstance(rot, M.Namn) else None

    def _pos(self, s: M.Sats) -> int:
        return self._ordning.get(id(s), 0)

    def _sekvens(self, satser, miljo=None) -> Dict[str, "Bidrag"]:
        """namn -> Bidrag for en satslista.

        `miljo` ar definitionerna av mellanvariabler som galler nar listan
        borjar (omgivande nivaers ovillkorade tilldelningar). Listans egna
        ovillkorade tilldelningar laggs till efter hand, sa varje bidrag bar
        miljon som galler FORE dess sats.
        """
        miljo = dict(miljo or {})
        poster: Dict[str, List[Bidrag]] = {}
        for s in satser:
            for namn, b in self._bidrag(s, miljo).items():
                b.miljo = miljo
                poster.setdefault(namn, []).append(b)
            d = U.definition_av(s, self._pos(s), self._slut.get(id(s)))
            if d is not None:
                miljo = dict(miljo)
                miljo[d[0]] = d[1]
        ut = {}
        for namn, lista in poster.items():
            self._doma_dubbelskrivning(namn, lista)
            varden = set(p.varde for p in lista)
            # Falt 1 heter VILLKORAD, och en hopslagen gren ar villkorad bara
            # om VARJE bidrag ar det. Raden stod som `any(not p[0] ...)`,
            # alltsa "minst ett bidrag ar OVILLKORAT" - tecknet var vant, och
            # faltet bar motsatsen till sitt namn.
            #
            # Grinden hade darfor fel at BADA hallen (matt 2026-09-05):
            #
            #   IF/ELSE sen villkorad overskrivning   FALLDES    ska ga igenom
            #     - kodens egen kommentar kallar "berakna, sedan tvinga" for
            #       standardmonstret for en forregling
            #   nastlade villkor i bada grenar + villkorad  SLAPPTES  ska falla
            #     - a=F, b=T, c=T ger FALSE och sedan TRUE i samma scan, alltsa
            #       precis den F7-kapplopning grinden finns for
            ut[namn] = Bidrag(all(p.villkorad for p in lista),
                              min(p.rad for p in lista),
                              lista[0].varde if len(varden) == 1 else None,
                              tuple(l for p in lista for l in p.lov))
        return ut

    def _visningsnamn(self, nyckel):
        post = self.omf.get(nyckel)
        return post.namn if post is not None else nyckel

    def _doma_dubbelskrivning(self, nyckel, lista):
        namn = self._visningsnamn(nyckel)
        ovillkorade = [i for i, p in enumerate(lista) if not p.villkorad]
        villkorade = [i for i, p in enumerate(lista) if p.villkorad]
        if len(ovillkorade) >= 2:
            self.fel("DUBBELSKRIVNING", lista[ovillkorade[1]].rad,
                     "utgången %s skrivs ovillkorat både på rad %d och rad %d; "
                     "den första skrivningen syns aldrig"
                     % (namn, lista[ovillkorade[0]].rad, lista[ovillkorade[1]].rad))
        elif ovillkorade and ovillkorade[0] != 0:
            self.fel("DUBBELSKRIVNING", lista[ovillkorade[0]].rad,
                     "utgången %s skrivs ovillkorat på rad %d efter en villkorad "
                     "skrivning på rad %d, som därmed är verkningslös"
                     % (namn, lista[ovillkorade[0]].rad, lista[0].rad))
        if len(villkorade) >= 2:
            # Tva VILLKORADE skrivningar av samma LITERAL ar bevisbart ofarliga.
            #
            # Regelns eget skal ar att ordningen avgor vilken som vinner. Skriver
            # bada samma varde finns ingen ordning att fa fel: "berakna, sedan
            # tvinga" ar dessutom standardmonstret for en forregling, och den som
            # skriver `IF NOT AIR_OK THEN don := FALSE; END_IF;` efter en sekvens
            # gor precis ratt.
            #
            # Skriver de OLIKA varden faller de bara om bada kan koras i samma
            # scan. Det avgors lov for lov: varje skrivnings sokvagsvillkor, med
            # mellanvariabler substituerade dar det ar sunt, provas parvis med
            # SAT. M-121: sex av bankens 26 referenser folls har fast villkoren
            # utesluter varandra (xAuto mot xHand genom SYS_AUTO), och en falsk
            # rod kostar modellen ett reparationsvarv.
            varden = set(lista[i].varde for i in villkorade)
            if not (len(varden) == 1 and None not in varden):
                konflikt = self._forsta_konflikt([lista[i] for i in villkorade])
                if konflikt is not None:
                    la, lb, vittne = konflikt
                    self.fel("DUBBELSKRIVNING", lb.rad,
                             "utgången %s skrivs på rad %d och rad %d, och båda kan "
                             "köras i samma scan%s; lägg ihop villkoren till en "
                             "enda skrivning"
                             % (namn, la.rad, lb.rad, U.vittnestext(vittne)))

    def _forsta_konflikt(self, bidrag):
        """Forsta paret lov ur tva olika satser som skriver olika varden och
        vars sokvagsvillkor kan vara sanna samtidigt. None om inget finns."""
        for i in range(len(bidrag)):
            for j in range(i + 1, len(bidrag)):
                for la in bidrag[i].lov:
                    for lb in bidrag[j].lov:
                        if la.varde is not None and la.varde == lb.varde:
                            continue
                        kan, vittne = self._uteslutning.forenliga(
                            la.villkor, lb.villkor,
                            bidrag[i].miljo or {}, bidrag[j].miljo or {})
                        if kan:
                            return la, lb, vittne
        return None

    @staticmethod
    def _literalvarde(uttryck):
        """Vardet nar skrivningen ar en literal, annars None.

        Behovs for att skilja tva skrivningar som KAN sta i konflikt fran tva
        som bevisligen inte kan. Ett uttryck ar alltid None: dess varde beror
        pa tillstandet och gar inte att avgora har.
        """
        if isinstance(uttryck, M.Literal):
            return (uttryck.typnamn or "", uttryck.varde)
        return None

    def _bidrag(self, s: M.Sats, miljo) -> Dict[str, "Bidrag"]:
        if isinstance(s, M.Tilldelning):
            namn = self._utgangsnamn(s.mal)
            if not namn:
                return {}
            v = self._literalvarde(s.uttryck)
            return {namn: Bidrag(False, s.rad, v, (Lov(True, s.rad, v),))}
        if isinstance(s, M.Anropssats):
            ut = {}
            for arg in s.anrop.argument:
                if arg.ut:
                    namn = self._utgangsnamn(arg.uttryck)
                    if namn:
                        ut[namn] = Bidrag(False, arg.rad, None,
                                          (Lov(True, arg.rad, None),))
            return ut
        if isinstance(s, M.Om):
            pos = self._pos(s)
            grenar = []
            hittills = False
            for g in s.grenar:
                c = U.formel_av(g.villkor, pos)
                grenar.append((self._sekvens(g.satser, miljo),
                               U.och(c, U.icke(hittills))))
                hittills = U.eller(hittills, c)
            har_annars = s.annars is not None
            if har_annars:
                grenar.append((self._sekvens(s.annars, miljo), U.icke(hittills)))
            return self._sla_ihop_grenar(grenar, har_annars)
        if isinstance(s, M.Fall):
            pos = self._pos(s)
            grenar = []
            hittills = False
            for g in s.grenar:
                c = U.fall_villkor(s.uttryck, g, pos)
                grenar.append((self._sekvens(g.satser, miljo),
                               U.och(c, U.icke(hittills))))
                hittills = U.eller(hittills, c)
            har_annars = s.annars is not None
            if har_annars:
                grenar.append((self._sekvens(s.annars, miljo), U.icke(hittills)))
            return self._sla_ihop_grenar(grenar, har_annars)
        if isinstance(s, (M.ForSats, M.Medan, M.Upprepa)):
            # En slinga kan kora noll ganger: villkorad, med ett villkor som
            # ingen annan atom slas ihop med.
            inre = self._sekvens(s.satser, miljo)
            slinga = U.ogenomskinlig(self._pos(s))
            return dict((n, Bidrag(True, b.rad, b.varde,
                                   tuple(Lov(U.och(slinga, l.villkor), l.rad, l.varde)
                                         for l in b.lov)))
                        for n, b in inre.items())
        return {}

    @staticmethod
    def _sla_ihop_grenar(grenar, har_annars) -> Dict[str, "Bidrag"]:
        """Grenar utesluter varandra: två skrivningar i olika grenar är ingen
        dubbelskrivning. Ovillkorlig blir skrivningen bara om varje gren —
        inklusive ELSE — skriver namnet ovillkorat.

        `grenar` ar par (bidrag per namn, grenens villkor). Varje lov far
        grenens villkor pahangt, sa att provet pa nivan ovanfor ser hela
        sokvagen ner till skrivningen."""
        ut = {}
        alla = set()
        for g, _v in grenar:
            alla |= set(g)
        for namn in alla:
            poster = [g[namn] for g, _v in grenar if namn in g]
            rader = [p.rad for p in poster]
            i_alla = har_annars and all(namn in g and not g[namn].villkorad
                                        for g, _v in grenar)
            # Vardet foljer med bara nar ALLA grenar skriver samma literal.
            # Skiljer de sig kan grenvalet avgora vardet, och da ar det inte
            # langre ett bevisbart ofarligt varde.
            varden = set(p.varde for p in poster)
            varde = poster[0].varde if len(varden) == 1 else None
            lov = tuple(Lov(U.och(v, l.villkor), l.rad, l.varde)
                        for g, v in grenar if namn in g for l in g[namn].lov)
            ut[namn] = Bidrag(not i_alla, min(rader), varde, lov)
        return ut

    def _utgangsnamn(self, mal: M.Uttryck) -> Optional[str]:
        rot = mal
        while isinstance(rot, (M.Medlem, M.Element)):
            rot = rot.bas
        if not isinstance(rot, M.Namn):
            return None
        nyckel = rot.ident.upper()
        return nyckel if nyckel in self.utgangsnamn else None


def konstant_bool(u: M.Uttryck) -> Optional[bool]:
    """TRUE/FALSE-värdet hos ett uttryck som går att avgöra utan att köra.

    Bara literaler och logik över literaler. En variabel som råkar vara
    konstant räknas inte: den kontrollen ska vara uppenbart rätt, inte smart.
    """
    if isinstance(u, M.Literal) and u.klass == "BOOL":
        return bool(u.varde)
    if isinstance(u, M.Unar) and u.op == "NOT":
        inre = konstant_bool(u.operand)
        return None if inre is None else not inre
    if isinstance(u, M.Binar) and u.op in ("AND", "OR"):
        a = konstant_bool(u.vanster)
        b = konstant_bool(u.hoger)
        if u.op == "AND":
            if a is False or b is False:
                return False
            return True if (a and b) else None
        if a is True or b is True:
            return True
        return False if (a is False and b is False) else None
    return None


def underlistor(s: M.Sats):
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


def validera(kalla: str, externa=None, skyddade=(), utgangar=()) -> Rapport:
    """Granskar ST-text. `externa` är namn ur signalkartan som deklareras
    någon annanstans, `skyddade` de taggar som är säkerhetsmärkta och
    `utgangar` extra namn som ska räknas som utgångar i dubbelskrivningen."""
    try:
        enhet = las(kalla)
    except Syntaxfel as f:
        return Rapport(False, (Anmarkning(f.kod, f.rad, f.text),))
    anm = Granskning(enhet, externa, skyddade, utgangar).granska()
    # Ett namn som slås upp både som skrivmål och som uttryck ger samma
    # anmärkning två gånger. Läsaren av rapporten ska se felet, inte
    # validatorns interna vägar.
    unika = sorted(set(anm), key=lambda a: (a.rad, a.kod, a.text))
    anm = tuple(unika)
    return Rapport(not anm, anm)
