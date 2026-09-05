# -*- coding: utf-8 -*-
"""Reparationsslingan: skelett, modellsvar, grind, grindens EGNA ord, nytt varv.

`docs/spec/61_st_generering.md` beskriver slingan och lämnar en fråga öppen:
ska modellen få se sina tidigare försök, eller starta rent varje varv? Frågan
är mätt i `docs/matningar/M-52_reparationsslingan.md`. Den här filen är
mekaniken som mätningen kördes på, och som produkten använder.

## Formen

    skelett  --->  modellen skriver kroppen
                        |
                        v
                   grindarna, i ordning, billigast först
                        |
              godkänt --+-- fällt: grindens EGNA ord tillbaka, ordagrant
                 |                        |
              KANDIDAT                 nytt varv, upp till taket

## Tre saker som är mekaniserade, inte bedda

**Grindens ord går vidare ordagrant.** Doktrinen i `50_grindar.md` är motiverad
av en mätt incident: en omimplementerad positionsdom underkände 2 av 4 medan
ögat visade 4 av 4. Slingan kontrollerar därför att varje fällande grinds
`utdata` finns tecken för tecken i den text som når modellen, och kastar
`Reparationsfel` om den inte gör det. En formaterare får rama in orden. Den får
inte skriva om dem.

**Taket är obligatoriskt.** En slinga utan tak går inte att konstruera: `None`,
noll och negativa tal avvisas, och ett tak över `ABSOLUT_TAK` avvisas också. En
obegränsad slinga döljer att uppgiften är olöslig.

**En låst slinga är ett eget utfall.** Grindarna är rena funktioner av kroppen.
Skickar modellen tillbaka en kropp den redan skickat blir domen med säkerhet
densamma, och slingan är låst — det är något annat än att nå taket, och
räknas därför inte som att ha nått taket.

## Vad slingan ALDRIG säger

Den säger aldrig guld. `50_grindar.md`: endast en körning i VC befordrar
kandidat till guld. `LOST` betyder att de grindar som **kördes** höll, och
protokollet bär alltid `ej_korda` med varje överhoppad grinds egna skäl —
en grind som inte kunde köras är aldrig ett godkännande (I3).

Endast standardbiblioteket, som resten av `plc/`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import forhandsregler
from ..harness.modell import Meddelande, Modell, Modellsvar
from .signalkarta import Signalkarta
from .skelett import Skelett, Skelettfel
from .stationsgrind import (KORORDNING, Kandidat, NAMN_DEKLARATION,
                            NAMN_STATISK, Stationsdom, granska_station)

# Taket på antalet varv. Satt av M-52, och mätt två gånger på samma material.
# Svepet: samma 82 repertoarer med taket 2, 3, 4, 5, 6 och 8. Taket 4 löste
# 43 (rent) och 57 (historik) av 82; taken 5, 6 och 8 löste EXAKT lika många.
# Att höja taket över fyra löste alltså noll ytterligare slingor. Räkningen:
# bankens fyra spårfacituppgifter bär arton motbevis, och antalet DISTINKTA
# felklassignaturer per uppgift är som mest tre (T-07 två, S-05 tre, H-04 tre,
# L-05 två). Med deklarationsklassen blir det fyra olika domar en uppgift över
# huvud taget kan lämna, och ett femte varv har ingen femte dom att svara på.
MAX_VARV = 4                    # Satt av M-52.

# Ett tak över detta avvisas. Skälet är inte att 20 varv är fel tal, utan att
# ett tak som får vara godtyckligt stort är samma sak som inget tak: en slinga
# med tak 10000 döljer en olöslig uppgift lika väl som en oändlig. Talet är
# fem gånger MAX_VARV, så en mätning som vill svepa över taket ryms.
ABSOLUT_TAK = 20                # Satt av M-52.

LAGE_RENT = "rent"              # modellen ser skelettet och SENASTE grinddomen
LAGE_HISTORIK = "historik"      # modellen ser sina tidigare försök också
LAGEN = (LAGE_RENT, LAGE_HISTORIK)

UTFALL_LOST = "LOST"            # alla körda grindar höll. Kandidat, aldrig guld
UTFALL_TAK = "TAK"              # taket nått utan att grindarna höll
UTFALL_LAST = "LAST"            # samma kropp igen; domen kan inte bli en annan
UTFALL_TYSTNAD = "TYSTNAD"      # modellen svarade varken text eller anrop
UTFALLEN = (UTFALL_LOST, UTFALL_TAK, UTFALL_LAST, UTFALL_TYSTNAD)

# Felklassen för en ändrad ram. `82_felklasser.md` F4 är "typ- eller
# riktningsfel i variabeldeklaration"; ramen ÄR deklarationerna, så en ändrad
# ram är en ändrad deklaration. Skelettet vaktar ramen, grind 3 innehållet.
KLASS_RAM = "F4"

# Grindarnas egen märkning i sin utdata: [kod/Fklass]. Grind 2 och 3 skriver
# `[ODEKLARERAD/F4]`, spårfacit `[flank:en_puls_per_detalj/F15]`. Slingan läser
# observatörens egna ord i stället för att räkna om domen (I1). Koden får bära
# vad som helst utom blanktecken, snedstreck och hakparentes: två grindar med
# olika kodformer ska inte tvinga fram två parsrar.
_MARKNING = re.compile(r"\[([^\]\s/]+)/(F\d+|-)\]")


class Reparationsfel(Exception):
    """Slingan går inte att köra, eller doktrinen bröts på vägen."""


# ---------------------------------------------------------------- grinddom

@dataclass(frozen=True)
class Grinddom:
    """En grinds dom över en kandidat, med grindens EGNA ord.

    `utdata` är ordagrant det grinden skrev. Slingan lägger till en inramning
    runt den, aldrig i den.

    `kord=False` betyder att grinden inte kunde köras. Det är inte ett
    godkännande (I3) och `ok` är då alltid False.
    """

    grind: str
    ok: bool
    utdata: str = ""
    koder: Tuple[str, ...] = ()
    klasser: Tuple[str, ...] = ()
    kord: bool = True

    def __post_init__(self):
        if self.ok and not self.kord:
            raise Reparationsfel(
                "grinden %s rapporterar godkänt utan att ha körts; tystnad är "
                "aldrig ett godkännande (I3)" % (self.grind,))


class Grindsteg(object):
    """Basen för ett steg i kedjan. Underklassen implementerar bara `doma`."""

    namn = "okand"

    def doma(self, st_kalla: str) -> Grinddom:
        raise NotImplementedError(
            "ett grindsteg måste implementera doma(); ett steg som svarar "
            "godkänt utan att mäta vore precis den falska grönt slingan "
            "finns för att hitta")

    def ej_korda(self) -> Dict[str, str]:
        """Grindar steget medvetet hoppade över, med varje grinds egna skäl."""
        return {}


def klasser_ur(utdata: str) -> Tuple[str, ...]:
    """Felklasserna som står i grindens EGEN utdata, i den ordning de kommer.

    Grind 2 och 3 skriver `rad 12: [ODEKLARERAD/F4] ...`. Att läsa klassen där
    är att parsa observatörens utdata; att härleda den ur koden på nytt vore
    att implementera om måttet (I1).
    """
    ut: List[str] = []
    for _kod, klass in _MARKNING.findall(utdata or ""):
        if klass != "-" and klass not in ut:
            ut.append(klass)
    return tuple(ut)


def koder_ur(utdata: str) -> Tuple[str, ...]:
    ut: List[str] = []
    for kod, _klass in _MARKNING.findall(utdata or ""):
        if kod not in ut:
            ut.append(kod)
    return tuple(ut)


class Stationssteg(Grindsteg):
    """Grind 1–4 över kandidaten, via `stationsgrind.granska_station`.

    `grindar` är de grindar steget FÅR döma på. Resten hoppas över och läggs i
    `ej_korda` med sina egna skäl, så att en överhoppad grind syns i rapporten
    i stället för att tyst räknas som grön. En grind som blir billig slutar
    mäta sin egen storhet.
    """

    namn = "station"

    def __init__(self, karta: Signalkarta,
                 grindar: Sequence[str] = (NAMN_STATISK, NAMN_DEKLARATION),
                 index=None, strucpp_paket: Optional[str] = None,
                 byggkatalog: Optional[str] = None, node: str = "node",
                 strucpp_cli: Optional[str] = None):
        okanda = [g for g in grindar if g not in KORORDNING]
        if okanda:
            raise Reparationsfel("okänd grind %s; grindarna är %s"
                                 % (", ".join(okanda), ", ".join(KORORDNING)))
        if not grindar:
            raise Reparationsfel(
                "ett stationssteg utan grindar dömer ingenting och skulle "
                "svara godkänt på allt")
        self.karta = karta
        self.grindar = tuple(grindar)
        self.index = index
        self.strucpp_paket = strucpp_paket
        self.byggkatalog = byggkatalog
        self.node = node
        self.strucpp_cli = strucpp_cli
        self._ej_korda: Dict[str, str] = {}

    def granska(self, st_kalla: str) -> Stationsdom:
        return granska_station(
            Kandidat(self.karta.station, st_kalla), self.karta,
            index=self.index, strucpp_paket=self.strucpp_paket,
            byggkatalog=self.byggkatalog, node=self.node,
            strucpp_cli=self.strucpp_cli, stanna_vid_forsta=False)

    def doma(self, st_kalla: str) -> Grinddom:
        dom = self.granska(st_kalla)
        for namn in KORORDNING:
            if namn in self.grindar:
                continue
            utfall = dom.forgrindar.get(namn, "ej kord")
            if utfall is not True:
                self._ej_korda[namn] = str(utfall)
        for namn in KORORDNING:
            if namn not in self.grindar:
                continue
            if dom.forgrindar.get(namn) is True:
                continue
            # Första grinden som fäller bestämmer klassen (82_felklasser.md).
            egen = (dom.utdata or {}).get(namn) or ""
            if not egen.strip():
                egen = str(dom.forgrindar.get(namn, "ej kord"))
            return Grinddom(grind="grind:%s" % namn, ok=False, utdata=egen,
                            koder=koder_ur(egen), klasser=klasser_ur(egen))
        return Grinddom(grind=self.namn, ok=True)

    def ej_korda(self) -> Dict[str, str]:
        return dict(self._ej_korda)


# ------------------------------------------------------------ inramningen

INLEDNING = ("En grind fällde ditt svar. Nedan står grindens EGEN utdata, "
             "ordagrant och utan omskrivning. Rätta kroppen och svara med "
             "bara kroppen igen.")
AVSLUTNING = ("Svara med kroppen, ingenting annat. Skriv aldrig "
              "deklarationerna: de är redan skrivna åt dig.")


def standardinramning(domar: Sequence[Grinddom]) -> str:
    """Grindarnas ord med en inramning runt, aldrig i.

    Formen är avsiktligt tråkig. En inramning som sammanfattar vad grinden
    "menar" är just den omskrivning som gjorde att en positionsdom underkände
    2 av 4 medan ögat visade 4 av 4.
    """
    delar = [INLEDNING]
    for d in domar:
        delar.append("--- %s, grindens egen utdata ---" % d.grind)
        delar.append(d.utdata)
    delar.append(AVSLUTNING)
    return "\n".join(delar)


def kontrollera_ordagrant(text: str, domar: Sequence[Grinddom]) -> None:
    """Fäller om en grinds ord inte nådde modellen tecken för tecken.

    Detta är doktrinen mekaniserad. Utan kontrollen är "grindens egna ord" en
    bön i en docstring, och en inramning som normaliserar, kortar eller
    översätter skulle passera obemärkt.
    """
    for d in domar:
        if not d.utdata:
            continue
        if d.utdata not in text:
            raise Reparationsfel(
                "grinden %s ord nådde inte modellen ordagrant. Inramningen "
                "skrev om domen, och en grind som tolkar om observatörens "
                "svar mäter till slut sig själv (50_grindar.md)." % (d.grind,))


_GRUNDPROMPT = (
    "Du skriver kroppen till ett ST-program enligt IEC 61131-3.\n"
    "Deklarationerna är redan skrivna och tillhör inte dig: skriv aldrig "
    "PROGRAM, VAR, END_VAR eller END_PROGRAM.\n"
    "Svara med enbart kroppens rader.")

# Grindarnas regler sagda FÖRE modellen skriver, i stället för efter.
#
# Fas 9 mäter första försöket till 0 av 4 och efter ett reparationsvarv 4 av 4.
# Operatörens krav är det omvända: enskott ska vara normalfallet och flerskott
# en reserv. Så länge grindarnas kunskap når modellen först NÄR den redan
# skrivit fel är flerskott inte en inställning utan en FORM.
#
# Reglerna GENERERAS ur grindarnas egna kodtabeller (`forhandsregler.REGLER`
# mot `st.fel.KONTROLLER` och `deklarationsgrind.KONTROLLER_PLC`). En
# handskriven lista hade varit samma felklass som fällde tre grindar på en
# natt: någon skriver vad hen kommer ihåg, koden kommer att kräva något annat,
# och de glider isär utan att någon ser det.
SYSTEMPROMPT = _GRUNDPROMPT + "\n\n" + forhandsregler.text()


# ------------------------------------------------------------- protokollet

@dataclass(frozen=True)
class Varv:
    """Ett varv i slingan, som det gick."""

    nummer: int
    kropp: str
    st_kalla: str = ""
    domar: Tuple[Grinddom, ...] = ()
    grindord: str = ""
    upprepar: Optional[int] = None

    @property
    def ok(self) -> bool:
        return bool(self.domar) and all(d.ok for d in self.domar)

    @property
    def fallande(self) -> Tuple[Grinddom, ...]:
        return tuple(d for d in self.domar if not d.ok)

    @property
    def koder(self) -> Tuple[str, ...]:
        ut: List[str] = []
        for d in self.fallande:
            for k in d.koder:
                if k not in ut:
                    ut.append(k)
        return tuple(ut)

    @property
    def klasser(self) -> Tuple[str, ...]:
        ut: List[str] = []
        for d in self.fallande:
            for k in d.klasser:
                if k not in ut:
                    ut.append(k)
        return tuple(ut)

    @property
    def signatur(self) -> Tuple[str, ...]:
        """Domens felklasser, sorterade. Det modellen kan känna igen igen."""
        return tuple(sorted(set(self.klasser)))


@dataclass
class Reparationsprotokoll:
    """Hela slingan, som den gick. Det är detta bänken mäter."""

    station: str
    uppgift: str
    lage: str
    max_varv: int
    varv: List[Varv] = field(default_factory=list)
    utfall: str = ""
    ej_korda: Dict[str, str] = field(default_factory=dict)

    @property
    def lost(self) -> bool:
        return self.utfall == UTFALL_LOST

    @property
    def varv_till_lost(self) -> Optional[int]:
        return self.varv[-1].nummer if self.lost and self.varv else None

    @property
    def niva(self) -> str:
        """Alltid kandidat. Endast en körning i VC befordrar (50_grindar.md)."""
        return "kandidat"

    @property
    def domda_varv(self) -> Tuple[Varv, ...]:
        return tuple(v for v in self.varv if v.domar)

    def klassrakning(self) -> Dict[str, int]:
        """Fel per klass över hela slingan, ett varv räknas en gång per klass."""
        ut: Dict[str, int] = {}
        for v in self.varv:
            for k in v.klasser:
                ut[k] = ut.get(k, 0) + 1
        return ut

    def text(self) -> str:
        rader = ["UPPGIFT: %s  STATION: %s  LAGE: %s  TAK: %d"
                 % (self.uppgift, self.station, self.lage, self.max_varv)]
        for v in self.varv:
            if v.upprepar is not None:
                rader.append("varv %d UPPREPAR varv %d; domen kan inte bli en "
                             "annan" % (v.nummer, v.upprepar))
                continue
            if v.ok:
                rader.append("varv %d GODKAND av %d grindar"
                             % (v.nummer, len(v.domar)))
                continue
            for d in v.fallande:
                rader.append("varv %d %s FALLDE %s"
                             % (v.nummer, d.grind,
                                ", ".join(d.koder) or "(utan kod)"))
        for namn in sorted(self.ej_korda):
            rader.append("EJ KORD GRIND %s: %s" % (namn, self.ej_korda[namn]))
        rader.append("UTFALL: %s (%s)" % (self.utfall, self.niva))
        return "\n".join(rader)


# ------------------------------------------------------------------ slingan

class Reparationsslinga(object):
    """Skelett, modellsvar, grindar, grindens egna ord, nytt varv.

    Modellen är en INPARAMETER. Slingan öppnar ingen socket och känner ingen
    leverantör; den talar bara `harness.modell.Modell`.
    """

    def __init__(self, skelett: Skelett, grindar: Sequence[Grindsteg],
                 lage: str = LAGE_RENT, max_varv: int = MAX_VARV,
                 systemprompt: str = SYSTEMPROMPT,
                 inramning: Optional[Callable[[Sequence[Grinddom]], str]] = None):
        if not grindar:
            raise Reparationsfel(
                "en slinga utan grindar dömer ingenting och skulle släppa "
                "igenom varje svar; ingen grind utan trasig fixtur")
        if lage not in LAGEN:
            raise Reparationsfel("okänt läge %r; lägena är %s"
                                 % (lage, ", ".join(LAGEN)))
        if max_varv is None or isinstance(max_varv, bool) or \
                not isinstance(max_varv, int):
            raise Reparationsfel(
                "slingan måste ha ett tak, och taket måste vara ett heltal "
                "varv; en obegränsad slinga döljer att uppgiften är olöslig "
                "(61_st_generering.md)")
        if max_varv < 1:
            raise Reparationsfel(
                "taket %d ger noll varv; en slinga som aldrig kör mäter "
                "ingenting" % max_varv)
        if max_varv > ABSOLUT_TAK:
            raise Reparationsfel(
                "taket %d ligger över ABSOLUT_TAK %d; ett tak som får vara "
                "godtyckligt stort är samma sak som inget tak"
                % (max_varv, ABSOLUT_TAK))
        self.skelett = skelett
        self.grindar = tuple(grindar)
        self.lage = lage
        self.max_varv = max_varv
        self.systemprompt = systemprompt
        self.inramning = standardinramning if inramning is None else inramning

    # ---- vad modellen ser --------------------------------------------

    def historik(self, uppgiftstext: str,
                 varv: Sequence[Varv]) -> Tuple[Meddelande, ...]:
        """Meddelandena modellen får, enligt läget.

        Skillnaden mellan lägena ligger HÄR och ingen annanstans, så att en
        mätning av de två lägena mäter just den skillnaden.
        """
        ut = [Meddelande("uppgift", uppgiftstext)]
        domda = [v for v in varv if v.grindord]
        if not domda:
            return tuple(ut)
        if self.lage == LAGE_RENT:
            ut.append(Meddelande("grind", domda[-1].grindord))
            return tuple(ut)
        for v in domda:
            ut.append(Meddelande("modell", v.kropp))
            ut.append(Meddelande("grind", v.grindord))
        return tuple(ut)

    # ---- ett varv ------------------------------------------------------

    def _doma(self, kropp: str) -> Tuple[str, Tuple[Grinddom, ...]]:
        try:
            st_kalla = self.skelett.las_svar(kropp)
        except Skelettfel as fel:
            # Ramgrindens egna ord, ordagrant, precis som varje annan grind.
            return "", (Grinddom(grind="skelett", ok=False, utdata=str(fel),
                                 koder=("RAMEN_ANDRAD",),
                                 klasser=(KLASS_RAM,)),)
        domar: List[Grinddom] = []
        for steg in self.grindar:
            dom = steg.doma(st_kalla)
            domar.append(dom)
            if not dom.ok:
                # Första grinden som fäller bestämmer klassen; att köra vidare
                # hade gett en anmärkning om logik där felet var taggnamnet.
                break
        return st_kalla, tuple(domar)

    # ---- hela slingan --------------------------------------------------

    def kor(self, modell: Modell, uppgiftstext: str,
            uppgift: str = "") -> Reparationsprotokoll:
        protokoll = Reparationsprotokoll(
            station=self.skelett.station, uppgift=uppgift or self.skelett.station,
            lage=self.lage, max_varv=self.max_varv)
        sedda: Dict[str, int] = {}

        for n in range(1, self.max_varv + 1):
            svar = modell.svara(self.systemprompt,
                                self.historik(uppgiftstext, protokoll.varv), ())
            if not isinstance(svar, Modellsvar):
                raise Reparationsfel("adaptern lämnade %s, inte ett Modellsvar"
                                     % type(svar).__name__)
            if svar.tomt:
                protokoll.utfall = UTFALL_TYSTNAD
                return self._avsluta(protokoll)
            kropp = svar.text

            if kropp in sedda:
                # Grindarna är rena funktioner av kroppen: samma kropp ger med
                # säkerhet samma dom. Slingan är låst, och det är ett annat
                # utfall än att ha nått taket.
                protokoll.varv.append(Varv(nummer=n, kropp=kropp,
                                           upprepar=sedda[kropp]))
                protokoll.utfall = UTFALL_LAST
                return self._avsluta(protokoll)
            sedda[kropp] = n

            st_kalla, domar = self._doma(kropp)
            varv = Varv(nummer=n, kropp=kropp, st_kalla=st_kalla, domar=domar)
            if varv.ok:
                protokoll.varv.append(varv)
                protokoll.utfall = UTFALL_LOST
                return self._avsluta(protokoll)

            grindord = self.inramning(varv.fallande)
            kontrollera_ordagrant(grindord, varv.fallande)
            protokoll.varv.append(Varv(nummer=n, kropp=kropp,
                                       st_kalla=st_kalla, domar=domar,
                                       grindord=grindord))

        protokoll.utfall = UTFALL_TAK
        return self._avsluta(protokoll)

    def _avsluta(self, protokoll: Reparationsprotokoll) -> Reparationsprotokoll:
        for steg in self.grindar:
            protokoll.ej_korda.update(steg.ej_korda())
        return protokoll
