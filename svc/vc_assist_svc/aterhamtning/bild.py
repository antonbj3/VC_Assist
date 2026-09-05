# -*- coding: utf-8 -*-
"""Systembilden: avläsningarna, försöken, och läget som räknas ur dem.

## Ett läge är en SLUTSATS om en tystnad, inte ett fält

`forlopp.yta.Forlopp.lage` räknas ur körningens egna händelser. Det går, för en
körning som lever kan berätta vad den gör. Ett delsystem som dog kan inte
berätta någonting alls, och det som finns att tolka är en **avläsning**: vad
någon frågade, vad som kom tillbaka, och när.

Därför är avläsningen förstklassig och läget härlett. `lage_for` är en fri
funktion som tar de råa avläsningarna och LÄSARENS klocka, och den är avsiktligt
fri: grinden i `grind.py` räknar om läget själv med den, i stället för att fråga
den som visar. En grind som frågar den den dömer mäter till slut sig själv —
samma val som `granska` gör om tystnaden (Y9) och `granska_spegling` om åldern
(S2).

## Tre sätt att nolla en klocka, och det här är det tredje

* **M-64:** ett hjärtslag räknades som framsteg. ARBETAR i 600 av 600.
* **M-93:** en läsare frös klockan vid bildens egen skrivtid. ARBETAR i 60 av 60.
* **här:** en avläsning återanvänds efter att den blivit gammal. Frågan
  ställdes en gång, svaret var ja, och sedan slutade någon fråga.

Alla tre har samma form: ett tal som skulle åldras gör det inte. `lage_for`
räknar därför åldern mot läsarens `nu` vid varje avläsning, och en avläsning
äldre än `T_NERE_S` bär inget läge alls — den blir `OBESTÄMT`.

## En lyckad anslutning är inget livstecken (regel L-1)

Bryggan accepterar anslutningar **inuti** `tick()`, och `tick()` körs bara av
pumpen. Är pumpen död fullbordar kärnans lyssningskö handskakningen ändå:
`connect()` lyckas, och inget svar kommer någonsin. En avläsning som bara bär
`anslutning_oppnades=True` blir därför `OBESTÄMT`, aldrig `ANSLUTEN`.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .lagen import (ANSLUTEN, Aterhamtningsfel, BLOCKERAD, DEGRADERAD,
                    DELSYSTEM, FRANKOPPLAD, KAN_NEJ, KO_VANTAR, NERE,
                    OBESTAMT, ORSAK_UR_NYCKEL, Orsak, PROVTAGNING_PAGAR,
                    SIMULERING_IGANG, Vag, VAGAR, kan_lyckas)

# Tidsgränserna ur `28_lagen_och_aterhamtning.md` §1.3. Båda är PRELIMINÄRA
# där, och de är det här också — de kopieras med sin stämpel, inte med sin
# siffra ensam.
T_PING_S = 3.0      # PRELIMINÄR. 28_lagen_och_aterhamtning.md §1.3, ur M-03.
T_NERE_S = 3.0      # PRELIMINÄR. 28_lagen_och_aterhamtning.md §1.3, ur M-03.
# Hur länge en öppen statusruta får förklara en tystnad. Efter det går det inte
# längre att skilja en ruta som står öppen från en brygga som dog bakom den.
T_MODAL_S = 300.0   # PRELIMINÄR. 26_appen.md A-3, sätts av M-21.

# Raden bryggloggen ska bära före en modal ruta öppnas. Den står som en
# konstant därför att den är SPEC'AD OCH OBYGGD: `grep -n modal` i
# `ext/vc_addon/` ger noll träffar. Läget BLOCKERAD kan alltså inte fyras i
# dag, och det står som en permanent ovisshet i varje visning.
MODAL_OPPEN_RAD = "modal oppen"

BILDVERSION = 1     # 28_lagen_och_aterhamtning.md, första formen av en bild.


@dataclass(frozen=True)
class Avlasning:
    """Vad någon FAKTISKT frågade, och vad som FAKTISKT kom tillbaka.

    `svarade` har tre värden, och skillnaden mellan dem är hela modulen:

    * `True`  — ett svar kom. Bara det är ett livstecken.
    * `False` — frågan ställdes och inget svar kom. En tystnad med ord.
    * `None`  — frågan ställdes inte. Det är inte samma sak som ett nej, och
      att blanda ihop dem gör en oprövad sak till en trasig.
    """

    delsystem: str
    t: float
    svarade: Optional[bool]
    fel: str = ""
    anslutning_oppnades: Optional[bool] = None
    degraded: Optional[bool] = None
    kor: Optional[bool] = None
    keepalive: Optional[bool] = None
    provtagning: Optional[bool] = None
    ko_vantande: Optional[int] = None
    sista_loggrad: str = ""
    orsak: str = ""

    def __post_init__(self):
        if self.delsystem not in DELSYSTEM:
            raise Aterhamtningsfel(
                "okänt delsystem %r; listan är sluten (%s)"
                % (self.delsystem, ", ".join(DELSYSTEM)))
        if self.orsak and self.orsak not in ORSAK_UR_NYCKEL:
            raise Aterhamtningsfel(
                "okänd orsak %r; en orsak som inte står i tabellen når "
                "användaren utan härkomst" % (self.orsak,))
        if self.svarade is False and not (self.fel or "").strip():
            raise Aterhamtningsfel(
                "en avläsning som inte fick svar måste bära sondens egna ord; "
                "en tystnad utan ord går inte att visa för någon")

    @property
    def livstecken(self) -> bool:
        """Bara ett SVAR är ett livstecken. Inte en lyckad anslutning."""
        return self.svarade is True


@dataclass
class Forsok:
    """Ett återhämtningsförsök, med sin kanskap FRÅN BÖRJAN.

    Kanskapen fryses när försöket börjar och skrivs aldrig om. Skälet är att
    den är det enda som skiljer ett försök från en väntan: ett försök som inte
    kan lyckas är ingen återhämtning, det är en tystnad med en snurrande
    symbol framför sig.
    """

    vag: Vag
    orsak: Orsak
    t_start: float
    kanskap: str
    t_slut: Optional[float] = None
    lyckades: Optional[bool] = None
    ordagrant: str = ""

    @property
    def pagar(self) -> bool:
        return self.lyckades is None and self.t_slut is None


class Systembild(object):
    """Avläsningarna och försöken. Bär inget läge — läget räknas ur den.

    Klassen är avsiktligt liten och synkron, precis som `Forlopp`: den som
    sonderar för protokollet själv. Ingen tråd, ingen bakgrundspump.
    """

    def __init__(self, uppdrag: str = "", klocka=time.time,
                 t_ping: float = T_PING_S, t_nere: float = T_NERE_S,
                 t_modal: float = T_MODAL_S):
        self.uppdrag = uppdrag or "utan id"
        self.klocka = klocka
        self.t_ping = float(t_ping)
        self.t_nere = float(t_nere)
        self.t_modal = float(t_modal)
        self.t0 = klocka()
        self.avlasningar: List[Avlasning] = []
        self.forsoken: List[Forsok] = []
        self.spegel = None
        self.skrivet: Optional[float] = None

    # ---- att föra protokollet -------------------------------------------

    def spegla(self, spegel) -> None:
        """Skriv bilden ut ur processen efter varje avläsning.

        Samma spegel som fas 17 använder (`forlopp.spegel.Spegel`): den tar
        vilket objekt som helst med `till_json`, skriver atomiskt med
        `os.replace`, och den är redan provad. Att bygga en andra vore att
        bygga en andra sanning om vad atomisk skrivning betyder.
        """
        self.spegel = spegel
        spegel.skriv(self)

    def _spegla(self) -> None:
        if self.spegel is not None:
            self.spegel.skriv(self)

    def notera(self, avlasning: Avlasning) -> Avlasning:
        if not isinstance(avlasning, Avlasning):
            raise Aterhamtningsfel("notera tar en Avlasning, inte %s"
                                   % type(avlasning).__name__)
        self.avlasningar.append(avlasning)
        self._spegla()
        return avlasning

    def las_av(self, delsystem: str, svarade: Optional[bool],
               **kw) -> Avlasning:
        """En avläsning med sondens klocka. Bekvämlighet, inte en genväg."""
        return self.notera(Avlasning(delsystem=delsystem, t=self.klocka(),
                                     svarade=svarade, **kw))

    def borja_forsok(self, vag: Vag, orsak: Orsak) -> Forsok:
        """Registrerar ett pågående återhämtningsförsök.

        KASTAR om vägen inte kan lyckas för orsaken. Det är regeln
        *"ett återhämtningsförsök som inte kan lyckas får inte rapporteras som
        pågående"* mekaniserad på det enda ställe den kan sättas: där försöket
        skapas. Grinden kontrollerar samma sak i texten, oberoende — två
        linjer, som `OP_FOR_EFFECT` och `skrivgrind`.
        """
        if vag not in VAGAR:
            raise Aterhamtningsfel("okänd väg %r" % (vag,))
        kan = kan_lyckas(orsak, vag, self.utan_sjalvstart)
        if kan == KAN_NEJ:
            raise Aterhamtningsfel(
                "vägen \"%s\" kan inte lyckas för orsaken %s (%s); ett försök "
                "som inte kan lyckas får inte redovisas som pågående"
                % (vag.text, orsak.nyckel, kan))
        f = Forsok(vag=vag, orsak=orsak, t_start=self.klocka(), kanskap=kan)
        self.forsoken.append(f)
        self._spegla()
        return f

    def avsluta_forsok(self, forsok: Forsok, lyckades: bool,
                       ordagrant: str = "") -> Forsok:
        if forsok not in self.forsoken:
            raise Aterhamtningsfel("försöket hör inte till den här bilden")
        if not lyckades and not (ordagrant or "").strip():
            raise Aterhamtningsfel(
                "ett misslyckat försök utan ord är samma tomma besked som "
                "\"något gick fel\"")
        forsok.t_slut = self.klocka()
        forsok.lyckades = bool(lyckades)
        forsok.ordagrant = ordagrant
        self._spegla()
        return forsok

    # ---- vad som gäller just nu -----------------------------------------

    def sista(self, delsystem: str) -> Optional[Avlasning]:
        for a in reversed(self.avlasningar):
            if a.delsystem == delsystem:
                return a
        return None

    def har_svarat(self, delsystem: str) -> bool:
        """Har delsystemet någon gång svarat? `NERE` kräver det (§1)."""
        return any(a.delsystem == delsystem and a.livstecken
                   for a in self.avlasningar)

    @property
    def utan_sjalvstart(self) -> bool:
        """Har bryggan slagit av sin egen omstart? Okänt räknas som PÅ.

        Att räkna okänt som AV vore att slå av en väg vi inte vet är stängd.
        Att räkna det som ett löfte om att självstarten fungerar vore värre —
        och det gör tabellen i `lagen.py` inte: ingen orsak har `KAN_JA` för
        självstarten. Okänt kan därför aldrig bli ett löfte den här vägen.
        """
        for a in reversed(self.avlasningar):
            if a.delsystem == "bryggan" and a.keepalive is not None:
                return not a.keepalive
        return False

    def orsak(self, delsystem: str) -> Optional[Orsak]:
        """Den senast avlästa orsaken för delsystemet."""
        for a in reversed(self.avlasningar):
            if a.delsystem == delsystem and a.orsak:
                return ORSAK_UR_NYCKEL[a.orsak]
        return None

    def pagaende(self, delsystem: str) -> Tuple[Forsok, ...]:
        return tuple(f for f in self.forsoken
                     if f.pagar and f.orsak.delsystem == delsystem)

    def avslutade(self, delsystem: str) -> Tuple[Forsok, ...]:
        return tuple(f for f in self.forsoken
                     if not f.pagar and f.orsak.delsystem == delsystem)

    # ---- ut ur processen ------------------------------------------------

    def till_json(self) -> dict:
        return {
            "v": BILDVERSION,
            "uppdrag": self.uppdrag,
            "t0": self.t0,
            "skrivet": self.klocka(),
            "t_ping": self.t_ping,
            "t_nere": self.t_nere,
            "t_modal": self.t_modal,
            "avlasningar": [
                {"delsystem": a.delsystem, "t": a.t, "svarade": a.svarade,
                 "fel": a.fel,
                 "anslutning_oppnades": a.anslutning_oppnades,
                 "degraded": a.degraded, "kor": a.kor,
                 "keepalive": a.keepalive, "provtagning": a.provtagning,
                 "ko_vantande": a.ko_vantande,
                 "sista_loggrad": a.sista_loggrad, "orsak": a.orsak}
                for a in self.avlasningar],
            "forsok": [
                {"vag": f.vag.nyckel, "orsak": f.orsak.nyckel,
                 "t_start": f.t_start, "kanskap": f.kanskap,
                 "t_slut": f.t_slut, "lyckades": f.lyckades,
                 "ordagrant": f.ordagrant}
                for f in self.forsoken],
        }

    @classmethod
    def fran_json(cls, data: Any, klocka=time.time) -> "Systembild":
        """Läser tillbaka en bild. Fail-closed hela vägen.

        KLOCKAN ÄR LÄSARENS. Tidsstämplarna i bilden är sondens, och åldern
        räknas mot den som läser — annars står ett delsystem vars sond dog kvar
        på ANSLUTEN för alltid, och det är M-93:s odödliga körning med en ny
        mekanism.
        """
        VANTADE = {"v", "uppdrag", "t0", "skrivet", "t_ping", "t_nere",
                   "t_modal", "avlasningar", "forsok"}
        if not isinstance(data, dict):
            raise Aterhamtningsfel("en systembild är ett objekt, inte %s"
                                   % type(data).__name__)
        if set(data) != VANTADE:
            saknas = sorted(VANTADE - set(data))
            extra = sorted(set(data) - VANTADE)
            raise Aterhamtningsfel(
                "systembilden har fel nycklar; saknar %s, har extra %s"
                % (", ".join(saknas) or "inget", ", ".join(extra) or "inget"))
        if data["v"] != BILDVERSION:
            raise Aterhamtningsfel(
                "systembilden är version %r, läsaren kan %d; en läsare som "
                "gissar sig genom ett okänt format visar ett halvt läge som "
                "ett helt" % (data["v"], BILDVERSION))
        b = cls(data["uppdrag"], klocka=klocka, t_ping=data["t_ping"],
                t_nere=data["t_nere"], t_modal=data["t_modal"])
        b.t0 = float(data["t0"])
        b.skrivet = float(data["skrivet"])
        for rad in data["avlasningar"]:
            vantade = {"delsystem", "t", "svarade", "fel",
                       "anslutning_oppnades", "degraded", "kor", "keepalive",
                       "provtagning", "ko_vantande", "sista_loggrad", "orsak"}
            if set(rad) != vantade:
                raise Aterhamtningsfel("en avläsning har fel fält: %r"
                                       % sorted(rad))
            b.avlasningar.append(Avlasning(
                delsystem=rad["delsystem"], t=float(rad["t"]),
                svarade=rad["svarade"], fel=rad["fel"],
                anslutning_oppnades=rad["anslutning_oppnades"],
                degraded=rad["degraded"], kor=rad["kor"],
                keepalive=rad["keepalive"], provtagning=rad["provtagning"],
                ko_vantande=rad["ko_vantande"],
                sista_loggrad=rad["sista_loggrad"], orsak=rad["orsak"]))
        vag_ur_nyckel = dict((v.nyckel, v) for v in VAGAR)
        for rad in data["forsok"]:
            if set(rad) != {"vag", "orsak", "t_start", "kanskap", "t_slut",
                            "lyckades", "ordagrant"}:
                raise Aterhamtningsfel("ett försök har fel fält: %r"
                                       % sorted(rad))
            if rad["vag"] not in vag_ur_nyckel:
                raise Aterhamtningsfel("okänd väg %r i bilden" % (rad["vag"],))
            if rad["orsak"] not in ORSAK_UR_NYCKEL:
                raise Aterhamtningsfel("okänd orsak %r i bilden"
                                       % (rad["orsak"],))
            b.forsoken.append(Forsok(
                vag=vag_ur_nyckel[rad["vag"]],
                orsak=ORSAK_UR_NYCKEL[rad["orsak"]],
                t_start=float(rad["t_start"]), kanskap=rad["kanskap"],
                t_slut=rad["t_slut"], lyckades=rad["lyckades"],
                ordagrant=rad["ordagrant"]))
        return b


# ------------------------------------------------- läget, som en fri funktion

def lage_for(bild: Systembild, delsystem: str, nu: float) -> str:
    """Delsystemets läge, räknat ur de RÅA avläsningarna och LÄSARENS `nu`.

    Fri funktion med flit. Grinden kallar den själv i stället för att fråga
    den som visar, och kan därför fälla en härledning som fryser klockan,
    räknar en lyckad anslutning som liv, eller återanvänder en gammal
    avläsning.
    """
    if delsystem not in DELSYSTEM:
        raise Aterhamtningsfel("okänt delsystem %r" % (delsystem,))
    sista = bild.sista(delsystem)
    if sista is None:
        # Ingen har frågat. Det är ett besked om OSS, inte om den andra sidan,
        # och visningen säger det med de orden.
        return FRANKOPPLAD
    alder = nu - sista.t
    if alder < 0.0:
        # Avläsningen ligger i framtiden: klockorna är osams och åldern går
        # inte att räkna alls.
        return OBESTAMT
    if alder > bild.t_nere:
        # Den tredje nollade klockan. En avläsning som blivit gammal bär inget
        # läge — varken ett grönt eller ett rött.
        return OBESTAMT
    if sista.svarade is True:
        if sista.degraded:
            return DEGRADERAD
        if sista.provtagning:
            return PROVTAGNING_PAGAR
        if sista.ko_vantande:
            return KO_VANTAR
        if sista.kor:
            return SIMULERING_IGANG
        return ANSLUTEN
    if sista.svarade is False:
        if sista.sista_loggrad.strip() == MODAL_OPPEN_RAD:
            # §3.6:s undantag: ingen övergång till NERE medan en modal står
            # öppen. Men undantaget har en gräns. Efter taket går det inte
            # längre att skilja en ruta som står öppen från en brygga som dog
            # bakom den, och då är det ärliga svaret varken det ena eller det
            # andra.
            return BLOCKERAD if alder <= bild.t_modal else OBESTAMT
        if bild.har_svarat(delsystem):
            return NERE
        return FRANKOPPLAD
    # Frågan ställdes inte. En lyckad anslutning är inget livstecken (L-1).
    if sista.anslutning_oppnades:
        return OBESTAMT
    return FRANKOPPLAD


@dataclass(frozen=True)
class Blick:
    """Systemet som det ser ut för den som läser det, JUST NU.

    `nu` fryses vid avläsningstillfället och delas av renderaren och grinden.
    Utan den delningen kan en ålder passera tröskeln mellan de två, och
    användaren får en grindanmärkning på en yta som var korrekt när den skrevs.
    Samma val som `Ogonblick` i fas 17.
    """

    bild: Systembild
    nu: float
    kalla: str = ""
    fel: str = ""

    @property
    def obestamd(self) -> bool:
        return self.bild is None

    def alder(self, delsystem: str) -> Optional[float]:
        sista = self.bild.sista(delsystem)
        return None if sista is None else self.nu - sista.t

    def lage(self, delsystem: str) -> str:
        return lage_for(self.bild, delsystem, self.nu)

    def orsak(self, delsystem: str) -> Optional[Orsak]:
        return self.bild.orsak(delsystem)

    def lagen(self) -> Dict[str, str]:
        return dict((d, self.lage(d)) for d in DELSYSTEM)


def blicka(bild: Systembild, klocka=time.time, kalla: str = "") -> Blick:
    """Öppnar ögonen en gång. Klockan läses EN gång, och delas."""
    return Blick(bild=bild, nu=klocka(), kalla=kalla)


def las_bild(sokvag: str, klocka=time.time) -> Blick:
    """Läser en spegelfil. Ett läsfel blir OBESTÄMT, aldrig ett tomt läge.

    Formen är M-93:s: en trasig fil ger inte ett stacktrace och inte ett lugnt
    startläge. Den ger `Blick(bild=None, fel=...)`, och felets egna ord går
    ordagrant ut i visningen.
    """
    nu = klocka()
    try:
        with open(sokvag, encoding="utf-8") as fh:
            ra = fh.read()
    except OSError as fel:
        return Blick(bild=None, nu=nu, kalla=sokvag,
                     fel="%s: %s" % (type(fel).__name__, fel))
    try:
        data = json.loads(ra)
    except ValueError as fel:
        return Blick(bild=None, nu=nu, kalla=sokvag,
                     fel="filen är inte en hel systembild (%s: %s); den kan "
                         "vara avhuggen mitt i en skrivning"
                         % (type(fel).__name__, fel))
    try:
        b = Systembild.fran_json(data, klocka=lambda: nu)
    except Aterhamtningsfel as fel:
        return Blick(bild=None, nu=nu, kalla=sokvag, fel=str(fel))
    return Blick(bild=b, nu=nu, kalla=sokvag)


__all__ = ["Avlasning", "BILDVERSION", "Blick", "Forsok", "MODAL_OPPEN_RAD",
           "Systembild", "T_MODAL_S", "T_NERE_S", "T_PING_S", "blicka",
           "lage_for", "las_bild"]
