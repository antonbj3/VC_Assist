# -*- coding: utf-8 -*-
"""Signalmorfologin: vad en tagg BETYDER, läst ur namnet och riktningen.

Det här är baslinjens första och viktigaste steg, och det som gör den till en
riktig klassisk metod i stället för en halmgubbe. En driftsättares I/O-lista är
inte en påse namn: den bär en konvention, och konventionen bär mening. Ett
kommando heter `..._CLOSE` och dess ändlägesgivare heter `..._CLOSED`. Ett
index startas med `..._START` och kvitteras med `..._DONE`. Ett vakuum slås på
med `..._ON` och bekräftas av `..._OK`.

Det är precis den regeln varje standardbibliotek hos en integratör bygger på —
Rockwells PlantPAx och Siemens PCS7 har båda en enhetsmall per don, med
kommando, återkoppling och fel som tre punkter på samma enhet. Baslinjen gör
samma sak: den letar upp donen i kartan och parar ihop dem.

## Var tabellerna kommer ifrån

Suffixtabellen nedan är avläst ur **hela** bankens 51 uppgifter, inte ur de
fyra som bär spårfacit. Räkningen står i `docs/matningar/M-62_baslinjen.md`.
Att härleda den ur de fyra dömbara uppgifterna hade varit att bygga generatorn
mot domaren, och då mäter bänken inte längre generatorn.

## Vad som INTE går att läsa ur ett namn

Ordningen mellan två don. `ST310_RB_START` och `ST320_RB_START` är två robotar,
och namnet säger inte vilken som ska gå först. Morfologin ger enhetslistan;
ordningen måste komma någon annanstans ifrån (`sprak.py`) eller antas ur
kartans ordning. Det är baslinjens första verkliga gräns och den står i M-62.

beskriver: svc/vc_assist_svc/plc/baslinje/morfologi.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# ---- systemsignalerna, vid namn ------------------------------------------
#
# De fem är anläggningens och inte stationens, och de bär sitt namn oförändrat
# genom hela banken (EMG_OK i 50 av 51 uppgifter). De hanteras vid namn därför
# att de INTE följer stationsprefixmönstret, och därför att var och en har en
# egen roll i ramen: nödstoppet förreglar, tryckluften förreglar, automatläget
# släpper fram automatiken, kvittensen släpper larmet och larmet stoppar allt.
NODSTOPP = "EMG_OK"
LUFT = "AIR_OK"
AUTOLAGE = "SYS_AUTO"
KVITTENS = "SYS_RESET"
LARM = "SYS_ALARM"
SYSTEMSIGNALER = (NODSTOPP, LUFT, AUTOLAGE, KVITTENS, LARM)

# ---- rollerna ------------------------------------------------------------

ROLL_KOMMANDO = "kommando"        # utgång som styr ett don och har en kvittens
ROLL_DRIFTUTGANG = "driftutgang"  # utgång som ska stå hög så länge stationen gar
ROLL_STATUS = "status"            # boolesk utgång utan kvittens (larm, full, klar)
ROLL_RAKNARE = "raknare"          # heltalsutgång
ROLL_BORVARDE = "borvarde"        # flyttalsutgång
ROLL_BEKRAFTELSE = "bekraftelse"  # ingång som kvitterar ett kommando
ROLL_GIVARE = "givare"            # boolesk ingång utan kommando (narvaro, val)
ROLL_MATNING = "matning"          # flyttalsingang (lage, tryck, kraft, vikt)
ROLL_ANTAL = "antal"              # heltalsingang
ROLL_SYSTEM = "system"            # en av de fem vid namn

# ---- suffixtabellen ------------------------------------------------------
#
# kommandosuffix -> de kvittenssuffix som hör till det, i preferensordning.
# Avläst ur hela banken. Ett kommando utan träff är inte ett fel: en
# transportör som bara ska gå har ingen kvittens, och det är rollen
# ROLL_DRIFTUTGANG.
PARSUFFIX: Dict[str, Tuple[str, ...]] = {
    "CLOSE": ("CLOSED", "DONE", "HELD"),
    "OPEN": ("OPENED", "DONE"),
    "LOCK": ("LOCKED",),
    "ON": ("OK", "PRS", "PRESS"),
    "START": ("DONE", "BUSY"),
    "PICK": ("DONE", "BUSY"),
    "PLACE": ("DONE",),
    "TRIG": ("FOUND", "OK", "READY", "DEST", "VERDICT"),
    "REQ": ("ACK", "RDY", "OK", "FREE"),
    "UP": ("TOP",),
    "DOWN": ("BOT", "BOTTOM"),
    "OUT": ("HOME",),
    "CHG": ("RDY",),
    "IN_OPEN": (),
    "OUT_OPEN": (),
    "DOWN_OK": (),
}

# Suffix som betyder "det här donet ska bara gå medan stationen går". En
# transportör kvitterar ingenting; den snurrar.
DRIFTSUFFIX = ("RUN",)

# Enhetskoder vars utgångar aldrig är rörelser utan lägesbesked till någon
# annan. De ska drivas, men de får aldrig hamna i stegkedjan som ett
# don att vänta på.
STATUSSUFFIX = ("FULL", "EMPTY", "DONE", "BUSY", "SAFE", "STARVED", "STOP",
                "ACK", "RST", "CLEAR", "GONE")

# En kvittens som råkar heta som ett kommando. `MLD_OPEN` är formsprutverktygets
# LAGE (ingång), inte en order att öppna. Riktningen avgör alltid: en ingång kan
# aldrig vara ett kommando, hur den än stavas.

_TAGG = re.compile(r"^(?P<station>[A-Z]{2,}\d+)_(?P<rest>.+)$")


@dataclass(frozen=True)
class Tagg:
    """En tagg uppdelad i sina delar, plus rollen den fick.

    `station` är stationsprefixet (`ST050`) eller "" för de fem
    systemsignalerna. `enhet` är donkoden (`CLP`, `IDX`, `RB`), `suffix` är
    resten (`CLOSE`, `IN_OPEN`).
    """

    namn: str
    station: str
    enhet: str
    suffix: str
    riktning: str          # "in" eller "ut", ur PLC:ns synvinkel
    typ: str               # "bool", "int" eller "real"
    roll: str = ""
    par: Optional[str] = None      # kommandots kvittens, eller kvittensens kommando
    kommentar: str = ""

    @property
    def ar_utgang(self) -> bool:
        return self.riktning == "ut"

    @property
    def don(self) -> str:
        """Donets identitet: station och enhetskod. Två taggar på samma don
        hör ihop, och det är den enda hopkopplingen morfologin gör."""
        return "%s_%s" % (self.station, self.enhet)


def dela(namn: str) -> Tuple[str, str, str]:
    """(station, enhet, suffix) ur ett taggnamn.

    Systemsignalerna får tom station och enheten SYS. Ett namn utan
    stationsprefix får tom station och hela namnet som enhet — morfologin
    hittar då inga par, och det är rätt svar: den vet inte vad taggen är.
    """
    stor = (namn or "").upper()
    if stor in SYSTEMSIGNALER:
        return "", "SYS", stor
    m = _TAGG.match(stor)
    if not m:
        return "", stor, ""
    rest = m.group("rest")
    if "_" in rest:
        enhet, suffix = rest.split("_", 1)
    else:
        enhet, suffix = rest, ""
    return m.group("station"), enhet, suffix


def _kvittens_till(kommando: Tagg, ingangar: Sequence[Tagg]) -> Optional[Tagg]:
    """Den ingång som kvitterar `kommando`, eller None.

    Söker bara på SAMMA don. En kvittens på ett annat don är inte en kvittens,
    den är ett annat dons givare, och att para ihop dem hade byggt en stegkedja
    som väntar på fel sak.
    """
    onskade = PARSUFFIX.get(kommando.suffix)
    if onskade is None:
        # Okänt kommandosuffix. Prova ändå de vanligaste kvittenssuffixen på
        # samma don: en okänd verbform är ingen anledning att tappa donet.
        onskade = ("DONE", "OK", "CLOSED", "OPENED")
    for onskad in onskade:
        for i in ingangar:
            if i.don == kommando.don and i.suffix == onskad:
                return i
    return None


def klassa(signaler: Sequence[Dict[str, object]]) -> Tuple[Tagg, ...]:
    """Kartans signalrader som klassade taggar.

    `signaler` är bankens `control.signals`-form: dictar med `name`, `dir`
    ("in"/"out"), `type` ("bool"/"int"/"real") och valfri `comment`. Formen
    är avsiktligt bankens och inte Signalkartans: baslinjen ska kunna få sin
    indata ur en I/O-lista, och en I/O-lista har inga OpenPLC-adresser.
    """
    rader: List[Tagg] = []
    for s in signaler:
        namn = str(s["name"]).upper()
        station, enhet, suffix = dela(namn)
        rader.append(Tagg(namn=namn, station=station, enhet=enhet,
                          suffix=suffix,
                          riktning="in" if s["dir"] == "in" else "ut",
                          typ=str(s["type"]),
                          kommentar=str(s.get("comment") or "")))
    ingangar = [t for t in rader if not t.ar_utgang]
    ut: List[Tagg] = []
    parade_ingangar: Dict[str, str] = {}

    # Utgångarna först: bara en utgång kan vara ett kommando, och det är
    # kommandot som pekar ut sin kvittens och inte tvärtom.
    for t in rader:
        if t.namn in SYSTEMSIGNALER:
            ut.append(Tagg(**dict(t.__dict__, roll=ROLL_SYSTEM)))
            continue
        if not t.ar_utgang:
            ut.append(t)
            continue
        if t.typ == "int":
            ut.append(Tagg(**dict(t.__dict__, roll=ROLL_RAKNARE)))
            continue
        if t.typ == "real":
            ut.append(Tagg(**dict(t.__dict__, roll=ROLL_BORVARDE)))
            continue
        if t.suffix in DRIFTSUFFIX:
            ut.append(Tagg(**dict(t.__dict__, roll=ROLL_DRIFTUTGANG)))
            continue
        kvittens = _kvittens_till(t, ingangar)
        if kvittens is not None and kvittens.namn not in parade_ingangar:
            parade_ingangar[kvittens.namn] = t.namn
            ut.append(Tagg(**dict(t.__dict__, roll=ROLL_KOMMANDO,
                                  par=kvittens.namn)))
            continue
        ut.append(Tagg(**dict(t.__dict__, roll=ROLL_STATUS)))

    # Ingångarna sedan, nu när kvittenserna är utpekade.
    fardiga: List[Tagg] = []
    for t in ut:
        if t.roll:
            fardiga.append(t)
            continue
        if t.namn in parade_ingangar:
            fardiga.append(Tagg(**dict(t.__dict__, roll=ROLL_BEKRAFTELSE,
                                       par=parade_ingangar[t.namn])))
            continue
        if t.typ == "real":
            fardiga.append(Tagg(**dict(t.__dict__, roll=ROLL_MATNING)))
            continue
        if t.typ == "int":
            fardiga.append(Tagg(**dict(t.__dict__, roll=ROLL_ANTAL)))
            continue
        fardiga.append(Tagg(**dict(t.__dict__, roll=ROLL_GIVARE)))
    return tuple(fardiga)


class Karta(object):
    """Uppslagsvyer över de klassade taggarna. Ingen logik, bara register."""

    def __init__(self, taggar: Sequence[Tagg]):
        self.taggar = tuple(taggar)
        self._per_namn = dict((t.namn, t) for t in self.taggar)

    def __contains__(self, namn) -> bool:
        return str(namn).upper() in self._per_namn

    def get(self, namn) -> Optional[Tagg]:
        return self._per_namn.get(str(namn).upper())

    def med_roll(self, *roller: str) -> Tuple[Tagg, ...]:
        return tuple(t for t in self.taggar if t.roll in roller)

    def utgangar(self) -> Tuple[Tagg, ...]:
        return tuple(t for t in self.taggar
                     if t.ar_utgang and t.namn not in SYSTEMSIGNALER)

    def ingangar(self) -> Tuple[Tagg, ...]:
        return tuple(t for t in self.taggar
                     if not t.ar_utgang and t.namn not in SYSTEMSIGNALER)

    def har(self, namn: str) -> bool:
        return str(namn).upper() in self._per_namn

    def kommandon(self) -> Tuple[Tagg, ...]:
        return self.med_roll(ROLL_KOMMANDO)

    def station(self) -> str:
        """Det vanligaste stationsprefixet. Kartans egen identitet.

        Tas ur taggarna och inte ur uppgiftsnumret, därför att uppgiftsnumret
        är bänkens och inte anläggningens. En generator som får sitt
        stationsnamn ur uppgiftsnumret vet vilken uppgift den löser, och det
        ska den inte veta.
        """
        rakn: Dict[str, int] = {}
        for t in self.taggar:
            if t.station:
                rakn[t.station] = rakn.get(t.station, 0) + 1
        if not rakn:
            return "STATION"
        return sorted(rakn.items(), key=lambda x: (-x[1], x[0]))[0][0]
