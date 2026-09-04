# -*- coding: utf-8 -*-
"""Grind 3: deklarationsmatchning mot signalkartan.

Grinden står i docs/spec/50_grindar.md som "den billigaste vinsten": eftersom
deklarationerna **genereras** ur scenens signalkarta kan en tagg inte bli fel.
Den här filen är kontrollen som gör påståendet mätbart i stället för hoppfullt.
Den fäller i båda riktningarna:

    ST-koden -> kartan   en lokaliserad tagg i koden som kartan inte känner
    kartan -> ST-koden   en signal i kartan som koden aldrig deklarerar eller rör

Grinden **implementerar inte om** grind 2. Den läser med ST-lagrets egen läsare
och kan köra ST-lagrets egen validator, och rapporterar dess dom oförvanskad
(invariant I1: grinden parsar observatörens utdata, den räknar inte om måttet).
Det som ligger här är precis det grind 2 inte kan veta: vad scenen har för
signaler.

Namn som används men aldrig deklarerats är **grind 2:s** fall (ODEKLARERAD).
Grind 3 upprepar det inte; kör `granska(..., aven_grind2=True)` för båda.

Felklasserna kommer ur docs/spec/82_felklasser.md: F3 är "fel tagg — taggnamn
som inte finns i signalkartan", F4 är "typ- eller riktningsfel i
variabeldeklaration". SKRIVEN_INGANG är F4 av samma skäl som RIKTNING i
ST-lagret: riktningen är deklarerad, och koden bryter mot den.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ..st import modell as M
from ..st.fel import Syntaxfel
from ..st.lasare import las
from ..st.validator import Rapport, validera
from .signalkarta import Signalkarta, TILL_PLC

# kod -> (felklass enligt 82_felklasser.md, vad kontrollen fäller)
KONTROLLER_PLC = {
    "OLASLIG": ("F1", "ST-text som inte går att läsa; grind 3 kan då inte döma"),
    "SAKNAD_POU": ("F3", "ingen POU med stationens namn i källan"),
    "OKARTLAGD_TAGG": ("F3", "lokaliserad tagg i koden som saknas i signalkartan"),
    "SAKNAD_DEKLARATION": ("F3", "signal i kartan som koden inte deklarerar"),
    "AVVIKANDE_DEKLARATION": ("F4", "tagg vars typ, adress eller skyddsmärkning "
                                    "inte är kartans"),
    "ORORD_SIGNAL": ("F3", "signal i kartan som koden varken läser eller skriver"),
    "SKRIVEN_INGANG": ("F4", "skrivning till en signal som PLC:n bara läser"),
    "ODRIVEN_UTGANG": ("F3", "utgång i kartan som koden aldrig skriver"),
}


@dataclass(frozen=True)
class PlcAnmarkning:
    """Samma form som ST-lagrets Anmarkning, egen kodtabell.

    Egen tabell därför att ST-lagrets `KONTROLLER` beskriver grind 2 och inte
    ska växa med grind 3:s koder — två grindar i samma register går inte att
    räkna per grind, och bänken rapporterar fel per klass och grind.
    """

    kod: str
    rad: int
    text: str

    @property
    def felklass(self) -> Optional[str]:
        return KONTROLLER_PLC[self.kod][0]

    def __str__(self):
        return "rad %d: [%s/%s] %s" % (self.rad, self.kod,
                                       self.felklass or "-", self.text)


@dataclass(frozen=True)
class Grind3Rapport:
    """Grind 3:s dom, och grind 2:s dom bredvid den — inte hopblandad."""

    ok: bool
    anmarkningar: Tuple[PlcAnmarkning, ...]
    st_rapport: Optional[Rapport] = None

    def koder(self) -> Tuple[str, ...]:
        return tuple(a.kod for a in self.anmarkningar)

    def __str__(self):
        rader = []
        if self.anmarkningar:
            rader.append("GRIND 3 EJ GODKAND")
            rader.extend("  " + str(a) for a in self.anmarkningar)
        else:
            rader.append("GRIND 3 GODKAND")
        if self.st_rapport is not None:
            rader.append("GRIND 2: " + str(self.st_rapport))
        return "\n".join(rader)


# ---- gång igenom modellen ------------------------------------------------

def _basnamn(u: M.Uttryck) -> Optional[str]:
    """Namnet ett skrivmål till slut rör: ut, ut.falt och ut[3] är alla ut."""
    while True:
        if isinstance(u, M.Namn):
            return u.ident
        if isinstance(u, (M.Medlem, M.Element)):
            u = u.bas
            continue
        return None


def _namn_i_uttryck(u: M.Uttryck, lasta: Set[str], skrivna: Set[str]) -> None:
    if isinstance(u, M.Namn):
        lasta.add(u.ident.upper())
        return
    if isinstance(u, M.Literal):
        return
    if isinstance(u, M.Medlem):
        _namn_i_uttryck(u.bas, lasta, skrivna)
        return
    if isinstance(u, M.Element):
        _namn_i_uttryck(u.bas, lasta, skrivna)
        for i in u.index:
            _namn_i_uttryck(i, lasta, skrivna)
        return
    if isinstance(u, M.Unar):
        _namn_i_uttryck(u.operand, lasta, skrivna)
        return
    if isinstance(u, M.Binar):
        _namn_i_uttryck(u.vanster, lasta, skrivna)
        _namn_i_uttryck(u.hoger, lasta, skrivna)
        return
    if isinstance(u, M.Anrop):
        lasta.add(u.namn.upper())
        for a in u.argument:
            if a.ut:
                # Q => klar skriver klar, den läser den inte.
                bas = _basnamn(a.uttryck)
                if bas:
                    skrivna.add(bas.upper())
            else:
                _namn_i_uttryck(a.uttryck, lasta, skrivna)
        return
    # Fail-closed (I3): en uttrycksnod vi inte känner får inte tyst räknas som
    # "rör ingenting". Då hade en oanvänd signal kunnat se använd ut.
    raise ValueError("grind 3 känner inte uttrycksnoden %s" % type(u).__name__)


def _namn_i_satser(satser, lasta: Set[str], skrivna: Set[str]) -> None:
    for s in satser:
        if isinstance(s, M.Kommentar) or isinstance(s, (M.Avbryt, M.Retur)):
            continue
        if isinstance(s, M.Tilldelning):
            bas = _basnamn(s.mal)
            if bas:
                skrivna.add(bas.upper())
            if isinstance(s.mal, (M.Medlem, M.Element)):
                # ut[i] := ... läser i, och ut.falt := ... rör basen som helhet.
                _namn_i_uttryck(s.mal, lasta, set())
                lasta.discard((bas or "").upper())
            _namn_i_uttryck(s.uttryck, lasta, skrivna)
            continue
        if isinstance(s, M.Anropssats):
            _namn_i_uttryck(s.anrop, lasta, skrivna)
            continue
        if isinstance(s, M.Om):
            for g in s.grenar:
                _namn_i_uttryck(g.villkor, lasta, skrivna)
                _namn_i_satser(g.satser, lasta, skrivna)
            if s.annars is not None:
                _namn_i_satser(s.annars, lasta, skrivna)
            continue
        if isinstance(s, M.Fall):
            _namn_i_uttryck(s.uttryck, lasta, skrivna)
            for g in s.grenar:
                _namn_i_satser(g.satser, lasta, skrivna)
            if s.annars is not None:
                _namn_i_satser(s.annars, lasta, skrivna)
            continue
        if isinstance(s, M.ForSats):
            skrivna.add(s.styrvar.upper())
            _namn_i_uttryck(s.fran, lasta, skrivna)
            _namn_i_uttryck(s.till, lasta, skrivna)
            if s.steg is not None:
                _namn_i_uttryck(s.steg, lasta, skrivna)
            _namn_i_satser(s.satser, lasta, skrivna)
            continue
        if isinstance(s, M.Medan):
            _namn_i_uttryck(s.villkor, lasta, skrivna)
            _namn_i_satser(s.satser, lasta, skrivna)
            continue
        if isinstance(s, M.Upprepa):
            _namn_i_satser(s.satser, lasta, skrivna)
            _namn_i_uttryck(s.villkor, lasta, skrivna)
            continue
        raise ValueError("grind 3 känner inte satsen %s" % type(s).__name__)


def bruk(pou: M.Pou) -> Tuple[Set[str], Set[str]]:
    """(lästa, skrivna) namn i POU:ns kropp, versaler. ST är skiftlägesokänsligt."""
    lasta: Set[str] = set()
    skrivna: Set[str] = set()
    _namn_i_satser(pou.kropp, lasta, skrivna)
    return lasta, skrivna


# ---- grinden -------------------------------------------------------------

def granska(kalla: str, karta: Signalkarta,
            aven_grind2: bool = True) -> Grind3Rapport:
    """Döm ST-texten `kalla` mot `karta`.

    `aven_grind2=True` kör ST-lagrets validator med kartans skyddade taggar och
    utgångar ifyllda, och lägger dess rapport bredvid. Det är så grind 2 får
    veta vilka namn som är utgångar: dubbelskrivningskontrollen gäller bara
    utgångar, och utan kartan vet den inte vilka de är.
    """
    anm: List[PlcAnmarkning] = []

    try:
        enhet = las(kalla)
    except Syntaxfel as fel:
        # Fail-closed (I3): går texten inte att läsa är svaret "inte godkänt",
        # inte "inga anmärkningar".
        return Grind3Rapport(False,
                             (PlcAnmarkning("OLASLIG", fel.rad, fel.text),),
                             validera(kalla) if aven_grind2 else None)

    st_rapport = None
    if aven_grind2:
        st_rapport = validera(kalla, skyddade=karta.skyddade(),
                              utgangar=karta.utgangar())

    pou = None
    for p in enhet.pouer:
        if p.namn.upper() == karta.station.upper():
            pou = p
            break
    if pou is None:
        namn = ", ".join(p.namn for p in enhet.pouer) or "ingen alls"
        anm.append(PlcAnmarkning(
            "SAKNAD_POU", 0,
            "kartan gäller stationen %s, men källan har %s"
            % (karta.station, namn)))
        return Grind3Rapport(False, tuple(anm), st_rapport)

    # ---- riktning 1: koden -> kartan ------------------------------------
    deklarerade: Dict[str, M.Deklaration] = {}
    for _block, d in pou.deklarationer():
        nyckel = d.namn.upper()
        signal = karta.med_tagg(d.namn)
        if signal is None:
            if d.adress is not None:
                anm.append(PlcAnmarkning(
                    "OKARTLAGD_TAGG", d.rad,
                    "%s AT %s finns inte i signalkartan för %s"
                    % (d.namn, d.adress, karta.station)))
            # En lokal variabel utan adress är modellens egen och angår inte
            # grind 3. Att den är deklarerad prövas av grind 2.
            continue
        deklarerade[nyckel] = d
        if d.adress is None:
            anm.append(PlcAnmarkning(
                "AVVIKANDE_DEKLARATION", d.rad,
                "%s är kartlagd till %s men deklareras utan adress"
                % (d.namn, signal.adress.text())))
        elif d.adress != signal.adress.text():
            anm.append(PlcAnmarkning(
                "AVVIKANDE_DEKLARATION", d.rad,
                "%s ligger på %s i kartan men deklareras på %s"
                % (d.namn, signal.adress.text(), d.adress)))
        if d.typ != signal.typ:
            anm.append(PlcAnmarkning(
                "AVVIKANDE_DEKLARATION", d.rad,
                "%s är %s i kartan men deklareras som %s"
                % (d.namn, signal.typ.st(), d.typ.st())))
        if bool(d.skyddad) != bool(signal.skyddad):
            anm.append(PlcAnmarkning(
                "AVVIKANDE_DEKLARATION", d.rad,
                "%s är %s i kartan men %s i deklarationen (I15)"
                % (d.namn,
                   "sakerhetsmarkt" if signal.skyddad else "omarkt",
                   "sakerhetsmarkt" if d.skyddad else "omarkt")))

    # ---- riktning 2: kartan -> koden ------------------------------------
    lasta, skrivna = bruk(pou)
    for s in karta.signaler:
        nyckel = s.tagg.upper()
        if nyckel not in deklarerade:
            anm.append(PlcAnmarkning(
                "SAKNAD_DEKLARATION", 0,
                "signalen %s.%s (%s, %s) deklareras inte i %s"
                % (s.komponent, s.scensignal, s.tagg, s.adress.text(),
                   karta.station)))
            continue
        rord = nyckel in lasta or nyckel in skrivna
        if not rord:
            anm.append(PlcAnmarkning(
                "ORORD_SIGNAL", deklarerade[nyckel].rad,
                "%s (%s.%s) rörs aldrig av koden"
                % (s.tagg, s.komponent, s.scensignal)))
            continue
        if s.riktning == TILL_PLC and nyckel in skrivna:
            anm.append(PlcAnmarkning(
                "SKRIVEN_INGANG", deklarerade[nyckel].rad,
                "%s är en insignal (%s) och ägs av scenen; koden skriver den"
                % (s.tagg, s.adress.text())))
        if s.ar_utgang and nyckel not in skrivna:
            anm.append(PlcAnmarkning(
                "ODRIVEN_UTGANG", deklarerade[nyckel].rad,
                "%s är en utgång (%s) som koden bara läser; inget driver den"
                % (s.tagg, s.adress.text())))

    ok = not anm and (st_rapport is None or st_rapport.ok)
    return Grind3Rapport(ok, tuple(anm), st_rapport)
