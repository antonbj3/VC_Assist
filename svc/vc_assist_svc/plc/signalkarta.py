# -*- coding: utf-8 -*-
"""Signalkartan: sambandet mellan en scensignal och en PLC-variabel.

Kartan är fas 6:s svar på den öppna frågan i docs/spec/60_plc.md ("hur
mappningen mellan VC-signal och OPC UA-nod ska deklareras"). Svaret är en
**explicit mappfil per station**, inte en namnkonvention. Skälet är mätt, inte
tyckt: OpenPLC v4:s runtime binder varje ST-variabel till bildtabellen genom
sin lokaliserade adress (`%IX0.0`), och det är adressen — inte variabelnamnet —
som bär över till fältbussidan. En namnkonvention hade behövt uppfinna den
adressen ur ett namn, och då är taggen tillbaka som en felkälla.

Riktningen på kartan i den här filen:

    Signalkarta --varblock()--> st.Varblock --skrivare--> VAR-block i ST-texten

Modellen får aldrig skriva deklarationerna (invariant I10). Den får det block
som `deklarationstext()` producerar, och skriver bara sekvensen.

**Vad som är MÄTT här** (2026-09-04, se docs/matningar/M-20_plcbandet.md):

* STruC++ 0.6.6 översätter `AT %IW1` till `{ Input, Word, 1, 0 }` — index per
  storleksklass, inte byteoffset.
* OpenPLC v4.2.1:s bildtabeller är skilda fält per storleksklass
  (`core/src/plc_app/image_tables.h`: `bool_input[1024][8]`, `byte_input[1024]`,
  `int_input[1024]`, `dint_input[1024]`, `lint_input[1024]`). Två adresser i
  olika storleksklasser delar alltså **inte** minne, och `BUFFER_SIZE` = 1024
  sätter den övre indexgränsen.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

from ..st import modell as M
from ..st import typer as T
from ..st.skrivare import skriv_varblock

# ---- riktning ------------------------------------------------------------
#
# Riktningen är uttryckt ur PLC:ns synvinkel, en gång, och sedan aldrig
# omtolkad. Scenens synvinkel är spegelbilden: det PLC:n läser är något scenen
# skriver. En parameter som bär två storheter döljer felet i det vanliga
# fallet, så ordvalet står i namnen i stället för i en kommentar vid varje bruk.
TILL_PLC = "TILL_PLC"      # givare i scenen -> PLC:ns ingång, %I
FRAN_PLC = "FRAN_PLC"      # PLC:ns utgång -> ställdon i scenen, %Q

RIKTNINGAR = (TILL_PLC, FRAN_PLC)

# Adressområdets bokstav per riktning. Ur IEC 61131-3: I = input, Q = output.
OMRADE = {TILL_PLC: "I", FRAN_PLC: "Q"}

# Storleksbokstav -> de elementära typer som får ligga på den bredden.
# Bredderna står i IEC 61131-3 tabell 10 och speglas av STruC++:s
# LocatedSize-enum (mätt: Bit, Byte, Word, DWord, LWord).
STORLEK_TYPER = {
    "X": ("BOOL",),
    "B": ("BYTE", "SINT", "USINT"),
    "W": ("WORD", "INT", "UINT"),
    "D": ("DWORD", "DINT", "UDINT", "REAL"),
    "L": ("LWORD", "LINT", "ULINT", "LREAL"),
}
TYP_STORLEK = dict((t, s) for s, ts in STORLEK_TYPER.items() for t in ts)

# Övre gräns för adressindex. KOD@HEAD: BUFFER_SIZE i
# core/src/plc_app/image_tables.h i OpenPLC v4.2.1 är 1024, och bildtabellerna
# är fält med precis så många platser. Index 1024 skriver utanför fältet.
MAX_INDEX = 1023
# Bitindex 0..7 därför att bool-tabellen är bool_input[BUFFER_SIZE][8].
MAX_BIT = 7

# IEC 61131-3 ar skiftlagesokansligt, ocksa i den lokaliserade adressen:
# `%qx0.0` och `%QX0.0` ar SAMMA plats i bildtabellen. MATT 2026-09-05 (M-105):
# monstret saknade `re.I` medan `_typ_av_text` i samma fil redan gjorde
# `.upper()` pa typen och `plc.skelett._HAR_ADRESS` redan bar `re.I` - exakt den
# asymmetri M-96 matte i lexern, dar halva filen var skiftlagesokanslig och
# halva inte. En karta skriven i gemener foll pa "ar ingen lokaliserad adress".
#
# `re.I` ENSAMT hade varit varre an felet: `%qx0.0` och `%QX0.0` hade blivit tva
# SKILDA Adress-varden, och `plats()` hade sagt att de inte krockar. Darfor
# normaliserar `las_adress` omradet och storleken till versaler.
_ADRESS = re.compile(r"^%(?P<omrade>[IQ])(?P<storlek>[XBWDL])"
                     r"(?P<index>\d+)(?:\.(?P<bit>\d+))?$", re.I)

# ST-identifierare enligt IEC 61131-3: bokstav eller understreck först, sedan
# bokstäver, siffror och understreck. Skrivaren kräver dessutom ren ASCII.
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Filformatets version. Ett kartformat utan version går inte att ändra utan att
# tysta gamla filer, och en tyst omtolkning är värre än ett fel.
FORMAT = 1


class KartFel(Exception):
    """Kartan vägrar beskriva något som inte går att lita på."""


def _kontrollera_ident(namn: str, vad: str) -> str:
    if not isinstance(namn, str) or not _IDENT.match(namn):
        raise KartFel("%s %r är inget giltigt ST-namn" % (vad, namn))
    return namn


@dataclass(frozen=True)
class Adress:
    """En lokaliserad adress, uppdelad i sina fyra delar.

    Formen är `%<omrade><storlek><index>[.<bit>]`. Delarna hålls isär därför
    att det är just de fyra som STruC++ lägger i sin LocatedVar-post, och det
    är den posten runtimen binder mot bildtabellen.
    """

    omrade: str
    storlek: str
    index: int
    bit: Optional[int] = None

    def __post_init__(self):
        if self.omrade not in ("I", "Q"):
            raise KartFel("okänt adressområde %r; bara %%I och %%Q hör till en "
                          "signalkarta" % (self.omrade,))
        if self.storlek not in STORLEK_TYPER:
            raise KartFel("okänd storleksbokstav %r" % (self.storlek,))
        if not 0 <= self.index <= MAX_INDEX:
            raise KartFel("adressindex %d ligger utanför bildtabellen (0..%d)"
                          % (self.index, MAX_INDEX))
        if self.storlek == "X":
            if self.bit is None:
                raise KartFel("en bitadress kräver ett bitindex, %s saknar det"
                              % self.text())
            if not 0 <= self.bit <= MAX_BIT:
                raise KartFel("bitindex %d ligger utanför 0..%d"
                              % (self.bit, MAX_BIT))
        elif self.bit is not None:
            raise KartFel("bara bitadresser (%%X) har ett bitindex; %s har ett"
                          % self.text())

    def text(self) -> str:
        if self.bit is None:
            return "%%%s%s%d" % (self.omrade, self.storlek, self.index)
        return "%%%s%s%d.%d" % (self.omrade, self.storlek, self.index, self.bit)

    def plats(self) -> Tuple[str, str, int, Optional[int]]:
        """Den plats i bildtabellen adressen pekar ut.

        Två adresser krockar om och endast om de här fyra är lika. Mätt skäl:
        bildtabellerna är skilda fält per storleksklass, så %IB0 och %IW0 rör
        inte varandra (image_tables.h, OpenPLC v4.2.1).
        """
        return (self.omrade, self.storlek, self.index, self.bit)


def las_adress(text: str) -> Adress:
    m = _ADRESS.match(text or "")
    if not m:
        raise KartFel("%r är ingen lokaliserad adress på formen %%QX0.0" % (text,))
    bit = m.group("bit")
    # Versaler ar kanonform: tva skrivningar av samma plats maste bli samma
    # Adress, annars slutar plats() se krocken. Se monstrets kommentar.
    return Adress(m.group("omrade").upper(), m.group("storlek").upper(),
                  int(m.group("index")),
                  None if bit is None else int(bit))


def _typ_av_text(text: str) -> T.Typ:
    """Bara elementära typer får vara scensignaler.

    En lokaliserad variabel binds mot en primitiv plats i bildtabellen. Fält,
    strukturer och blockinstanser har ingen sådan plats, och att låtsas att de
    har det vore att uppfinna en mappning (I3: vet-inte är inte godkänt).
    """
    if not isinstance(text, str):
        raise KartFel("typen måste vara en sträng, inte %s" % type(text).__name__)
    namn = text.strip().upper()
    if namn not in T.ELEMENTARA:
        raise KartFel("%r är ingen elementär typ; en scensignal kan bara ligga "
                      "på en primitiv plats i bildtabellen" % (text,))
    return T.Elementar(namn)


@dataclass(frozen=True)
class Signal:
    """En rad i kartan: en scensignal och den PLC-variabel den blir.

    komponent + scensignal    identiteten i VC-scenen
    tagg                      variabelnamnet i ST-koden
    typ                       ST-typen; styr både deklaration och adressbredd
    riktning                  TILL_PLC eller FRAN_PLC, ur PLC:ns synvinkel
    adress                    den lokaliserade adressen, %I för in, %Q för ut
    skyddad                   säkerhetsmärkt: agenten får läsa, aldrig skriva (I15)
    """

    komponent: str
    scensignal: str
    tagg: str
    typ: T.Typ
    riktning: str
    adress: Adress
    skyddad: bool = False
    kommentar: Optional[str] = None

    def __post_init__(self):
        _kontrollera_ident(self.tagg, "taggnamnet")
        if not self.komponent or not isinstance(self.komponent, str):
            raise KartFel("signalen saknar komponentnamn")
        if not self.scensignal or not isinstance(self.scensignal, str):
            raise KartFel("signalen saknar scensignalnamn")
        for falt, varde in (("komponent", self.komponent),
                            ("scensignal", self.scensignal),
                            ("kommentar", self.kommentar or "")):
            try:
                varde.encode("ascii")
            except UnicodeEncodeError:
                raise KartFel("%s %r innehåller icke-ASCII; namnet ska hela "
                              "vägen ut som OPC UA-namn" % (falt, varde))
        if self.riktning not in RIKTNINGAR:
            raise KartFel("okänd riktning %r; värdena är %s"
                          % (self.riktning, " och ".join(RIKTNINGAR)))
        if not isinstance(self.typ, T.Elementar):
            raise KartFel("signaltypen måste vara elementär, inte %s"
                          % self.typ.st())
        if not isinstance(self.adress, Adress):
            raise KartFel("adressen måste vara en Adress, inte %s"
                          % type(self.adress).__name__)
        vantat = OMRADE[self.riktning]
        if self.adress.omrade != vantat:
            raise KartFel("%s hör i %%%s, men %s ligger i %%%s"
                          % (self.riktning, vantat, self.tagg, self.adress.omrade))
        storlek = TYP_STORLEK[self.typ.namn]
        if self.adress.storlek != storlek:
            raise KartFel("%s är %s och hör på %%%s%s, men adressen är %s"
                          % (self.tagg, self.typ.namn, self.adress.omrade,
                             storlek, self.adress.text()))

    # ---- avledda vyer ---------------------------------------------------

    @property
    def ar_utgang(self) -> bool:
        """Utgång = PLC:n skriver den. Ordet används av grind 2:s
        dubbelskrivningskontroll, som bara gäller utgångar."""
        return self.riktning == FRAN_PLC

    def deklaration(self) -> M.Deklaration:
        return M.Deklaration(namn=self.tagg, typ=self.typ,
                             adress=self.adress.text(), skyddad=self.skyddad,
                             kommentar=self.kommentar or
                             ("%s.%s" % (self.komponent, self.scensignal)))

    def till_json(self) -> Dict[str, object]:
        rad = {
            "komponent": self.komponent,
            "scensignal": self.scensignal,
            "tagg": self.tagg,
            "typ": self.typ.namn,
            "riktning": self.riktning,
            "adress": self.adress.text(),
        }
        if self.skyddad:
            rad["skyddad"] = True
        if self.kommentar:
            rad["kommentar"] = self.kommentar
        return rad

    @staticmethod
    def fran_json(rad: object) -> "Signal":
        if not isinstance(rad, dict):
            raise KartFel("en signalrad måste vara ett objekt, inte %s"
                          % type(rad).__name__)
        kanda = {"komponent", "scensignal", "tagg", "typ", "riktning",
                 "adress", "skyddad", "kommentar"}
        okanda = set(rad) - kanda
        if okanda:
            # Fail-closed (I3): ett fält vi inte förstår kan bära en avsikt vi
            # tappar bort. Tyst ignorerat är värre än avvisat.
            raise KartFel("okända fält i signalraden: %s"
                          % ", ".join(sorted(okanda)))
        saknade = {"komponent", "scensignal", "tagg", "typ", "riktning",
                   "adress"} - set(rad)
        if saknade:
            raise KartFel("signalraden saknar %s" % ", ".join(sorted(saknade)))
        skyddad = rad.get("skyddad", False)
        if not isinstance(skyddad, bool):
            raise KartFel("skyddad måste vara true eller false, inte %r"
                          % (skyddad,))
        return Signal(komponent=rad["komponent"], scensignal=rad["scensignal"],
                      tagg=rad["tagg"], typ=_typ_av_text(rad["typ"]),
                      riktning=rad["riktning"], adress=las_adress(rad["adress"]),
                      skyddad=skyddad, kommentar=rad.get("kommentar"))


@dataclass(frozen=True)
class Signalkarta:
    """Alla signaler för en station, i den ordning de ska deklareras."""

    station: str
    signaler: Tuple[Signal, ...] = ()

    def __post_init__(self):
        _kontrollera_ident(self.station, "stationsnamnet")
        sedda_taggar: Dict[str, Signal] = {}
        sedda_platser: Dict[Tuple, Signal] = {}
        sedda_scensignaler: Dict[Tuple[str, str], Signal] = {}
        for s in self.signaler:
            if not isinstance(s, Signal):
                raise KartFel("kartan innehåller något som inte är en Signal: %s"
                              % type(s).__name__)
            # ST är skiftlägesokänsligt: Ut och ut är samma variabel.
            nyckel = s.tagg.upper()
            if nyckel in sedda_taggar:
                raise KartFel("taggen %s förekommer två gånger (%s och %s)"
                              % (s.tagg, sedda_taggar[nyckel].scensignal,
                                 s.scensignal))
            sedda_taggar[nyckel] = s
            plats = s.adress.plats()
            if plats in sedda_platser:
                raise KartFel("adressen %s delas av %s och %s"
                              % (s.adress.text(), sedda_platser[plats].tagg,
                                 s.tagg))
            sedda_platser[plats] = s
            scen = (s.komponent, s.scensignal)
            if scen in sedda_scensignaler:
                raise KartFel("scensignalen %s.%s är mappad två gånger (%s och %s)"
                              % (s.komponent, s.scensignal,
                                 sedda_scensignaler[scen].tagg, s.tagg))
            sedda_scensignaler[scen] = s

    # ---- uppslag --------------------------------------------------------

    def med_tagg(self, tagg: str) -> Optional[Signal]:
        nyckel = (tagg or "").upper()
        for s in self.signaler:
            if s.tagg.upper() == nyckel:
                return s
        return None

    def taggar(self) -> Tuple[str, ...]:
        return tuple(s.tagg for s in self.signaler)

    def utgangar(self) -> Tuple[str, ...]:
        """Taggarna grind 2 ska räkna som utgångar (dubbelskrivning)."""
        return tuple(s.tagg for s in self.signaler if s.ar_utgang)

    def ingangar(self) -> Tuple[str, ...]:
        return tuple(s.tagg for s in self.signaler if not s.ar_utgang)

    def skyddade(self) -> Tuple[str, ...]:
        """Taggarna som är skrivskyddade för agenten (I15)."""
        return tuple(s.tagg for s in self.signaler if s.skyddad)

    def typer(self) -> Dict[str, T.Typ]:
        """Namn -> typ, i den form validatorns `externa` vill ha den."""
        return dict((s.tagg, s.typ) for s in self.signaler)

    # ---- generering -----------------------------------------------------

    def varblock(self) -> M.Varblock:
        """VAR-blocket som ST-koden ska bära, genererat ur kartan.

        Ett block, sort VAR: en lokaliserad variabel ägs av POU:n och binds av
        runtimen genom sin adress, inte av en anropare. VAR_INPUT hade gjort
        ingången oskrivbar även för runtimen.

        Ordningen är kartans egen. Den är ett kontrakt: samma karta ger
        byte-identisk deklarationstext, annars mäter en guldfil ingenting.
        """
        return M.Varblock("VAR", tuple(s.deklaration() for s in self.signaler))

    def deklarationstext(self) -> str:
        return "\n".join(skriv_varblock(self.varblock(), 0)) + "\n"

    def program(self, kropp: Tuple[M.Sats, ...] = (),
                extra_block: Tuple[M.Varblock, ...] = ()) -> M.Pou:
        """Ett PROGRAM med kartans block först och modellens block efter.

        Att ordningen är låst här är hela poängen med I10: kroppen kommer från
        modellen, deklarationsdelen gör den inte.
        """
        return M.Pou("PROGRAM", self.station,
                     block=(self.varblock(),) + tuple(extra_block),
                     kropp=tuple(kropp))

    # ---- serialisering --------------------------------------------------

    def till_json(self) -> Dict[str, object]:
        return {"format": FORMAT, "station": self.station,
                "signaler": [s.till_json() for s in self.signaler]}

    def text(self) -> str:
        """JSON-texten. Sorterade nycklar och fast indrag: en karta som ändrar
        sig av sig själv går inte att ha i en guldfil."""
        return json.dumps(self.till_json(), indent=2, sort_keys=True,
                          ensure_ascii=True) + "\n"

    @staticmethod
    def fran_json(data: object) -> "Signalkarta":
        if not isinstance(data, dict):
            raise KartFel("en signalkarta måste vara ett objekt, inte %s"
                          % type(data).__name__)
        okanda = set(data) - {"format", "station", "signaler"}
        if okanda:
            raise KartFel("okända fält i kartan: %s" % ", ".join(sorted(okanda)))
        if data.get("format") != FORMAT:
            raise KartFel("kartformat %r; den här koden läser bara %d"
                          % (data.get("format"), FORMAT))
        if "station" not in data or "signaler" not in data:
            raise KartFel("kartan saknar station eller signaler")
        if not isinstance(data["signaler"], list):
            raise KartFel("signaler måste vara en lista")
        return Signalkarta(data["station"],
                           tuple(Signal.fran_json(r) for r in data["signaler"]))

    @staticmethod
    def las_text(text: str) -> "Signalkarta":
        try:
            data = json.loads(text)
        except ValueError as fel:
            raise KartFel("kartan är inte giltig JSON: %s" % fel)
        return Signalkarta.fran_json(data)

    @staticmethod
    def las_fil(sokvag: str) -> "Signalkarta":
        with open(sokvag, "r", encoding="ascii") as f:
            return Signalkarta.las_text(f.read())

    def skriv_fil(self, sokvag: str) -> None:
        # newline="\n": kartan gar in i ett arkiv som packas upp i en
        # Linux-container. Radsluten ska inte bero pa vilken maskin som
        # skrev den. Satt av M-44.
        with open(sokvag, "w", encoding="ascii", newline="\n") as f:
            f.write(self.text())


def karta_av_rader(station: str, rader) -> Signalkarta:
    """Bygg en karta ur enkla tupler, i den ordning de kommer.

    Formen är (komponent, scensignal, tagg, typnamn, riktning, adress) med
    valfria skyddad och kommentar. Finns för att en karta ofta föds ur en
    scenavsökning, och den ska inte behöva bygga JSON på vägen.
    """
    ut: List[Signal] = []
    for rad in rader:
        if len(rad) < 6 or len(rad) > 8:
            raise KartFel("en signalrad har 6 till 8 fält, inte %d" % len(rad))
        komponent, scensignal, tagg, typnamn, riktning, adress = rad[:6]
        skyddad = rad[6] if len(rad) > 6 else False
        kommentar = rad[7] if len(rad) > 7 else None
        ut.append(Signal(komponent=komponent, scensignal=scensignal, tagg=tagg,
                         typ=_typ_av_text(typnamn), riktning=riktning,
                         adress=las_adress(adress), skyddad=bool(skyddad),
                         kommentar=kommentar))
    return Signalkarta(station, tuple(ut))
