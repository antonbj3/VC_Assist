# -*- coding: utf-8 -*-
"""Turens tillstandsmaskin: varje lage, varje overgang, och vad som avslutar.

VARFOR MASKINEN LIGGER UTANFOR LOOPEN
-------------------------------------
Loopen ar byggd (`harness/loop.py`) och kors i banken. Att skriva en ANDRA
loop hade gett tva storheter med samma namn, och den ena hade blivit den som
provas medan den andra kordes. Modulen bygger darfor ingen loop: den
DEKLARERAR maskinen och laser den riktiga turens protokoll som ett SPAR genom
den.

Det ar skillnaden mellan en beskrivning och en grind. En beskrivning sager
"loopen har foljande lagen". Grinden sager: kor 95 riktiga turer, oversatt
varje handelse till ett lage, och fall om nagon tur gar en vag som inte star i
tabellen - eller slutar i ett lage som inte ar ett slut.

TRE REGLER SOM ALLA HAR SAMMA MOTIV
-----------------------------------
1. **STOPPAD ar absorberande.** Efter ett stopp hander ingenting mer. Ett
   stopp som senare blir ett KLAR ar ett godkannande ur ingenting.
2. **Tystnad ar aldrig ett godkannande (I3).** Ett tomt modellsvar ar ett
   STOPP med koden TYSTNAD, och ett KLAR utan slutsvarstext ar ett fel i sig -
   bada provas.
3. **Ett slutlage ar uttalat.** Ett spar som tar slut i ARBETE (VERKTYG,
   MODELL, KO) ar en tur som slutade utan att saga att den slutade. Det ar
   samma tysta form som ett verktyg som aldrig svarar.

VERKTYGET SOM ALDRIG SVARAR
---------------------------
Det gar INTE att avbryta. Det ar mätt, inte antaget: `pump._op_cancel` svarar
`{"cancelled": false, "why": "exec kors synkront pa VC:s trad och kan inte
avbrytas"}` (KOD@HEAD, M-13), och VC:s Python ar kooperativ (M-07).
Tidsvakten kan darfor inte bryta anropet - den kan bara vagra lita pa ett svar
som kom efter taket, och det ar precis vad `Tidsvaktkanal` gor: utfallet blir
ett FALL med koden TAK_TID, aldrig ett ok. Det operatoren ser under tiden ar
HJARTSLAG (24_samtalsloopen.md avsnitt 7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ..harness import loop as _loop
from ..harness.kanal import Anropsutfall, Verktygskanal
from .fel import Turfel

# --- lagen ---------------------------------------------------------------

START = "START"
MODELL = "MODELL"
VERKTYG = "VERKTYG"
GRIND = "GRIND"
KO = "KO"
SVARSGRIND = "SVARSGRIND"
KLAR = "KLAR"
STOPPAD = "STOPPAD"

TILLSTAND = (START, MODELL, VERKTYG, GRIND, KO, SVARSGRIND, KLAR, STOPPAD)
TERMINALA = (KLAR, STOPPAD)
ARBETE = (START, MODELL, VERKTYG, GRIND, KO, SVARSGRIND)

# Pseudohandelsen for rundgransen: modellen far ordet igen.
RUNDA = "runda"

# Den slutna overgangstabellen. Nyckeln ar (lage, handelsesort) och vardet ar
# (nytt lage, skal). Ett par som inte star har ar inte en laglig overgang.
OVERGANGAR: Dict[Tuple[str, str], Tuple[str, str]] = {
    (START, RUNDA): (MODELL, "turen borjar med att modellen far ordet"),
    (MODELL, RUNDA): (MODELL, "ny runda utan att nagot hande - rundtaket rakas"),
    (MODELL, "VERKTYG_OK"): (VERKTYG, "modellen bad om ett anrop och det gick"),
    (MODELL, "VERKTYG_FEL"): (VERKTYG, "anropet foll; felnyckeln gar tillbaka"),
    (MODELL, "AVVISAD"): (GRIND, "en grind avvisade anropet FORE korning"),
    (MODELL, "VARNING"): (MODELL, "en anmarkning fore korning, inte ett avslag"),
    (MODELL, "OMSKRIVNING"): (SVARSGRIND, "slutsvaret krav omskrivning"),
    (MODELL, "KLAR"): (KLAR, "slutsvaret passerade samtliga grindar"),
    (MODELL, "STOPP"): (STOPPAD, "ett tak eller en stoppregel slog"),
    (MODELL, "KO"): (KO, "en skrivande post vantar pa operatoren"),

    (VERKTYG, RUNDA): (MODELL, "resultatet gar tillbaka och modellen far ordet"),
    (VERKTYG, "VERKTYG_OK"): (VERKTYG, "nasta anrop i samma runda"),
    (VERKTYG, "VERKTYG_FEL"): (VERKTYG, "nasta anrop i samma runda foll"),
    (VERKTYG, "AVVISAD"): (GRIND, "nasta anrop avvisades av en grind"),
    (VERKTYG, "VARNING"): (VERKTYG, "anmarkning pa ett anrop i samma runda"),
    (VERKTYG, "OMSKRIVNING"): (SVARSGRIND, "slutsvaret krav omskrivning"),
    (VERKTYG, "KLAR"): (KLAR, "slutsvaret passerade samtliga grindar"),
    (VERKTYG, "STOPP"): (STOPPAD, "ett tak eller en stoppregel slog"),
    (VERKTYG, "KO"): (KO, "en skrivande post vantar pa operatoren"),

    (GRIND, RUNDA): (MODELL, "avslaget gar tillbaka och modellen far ordet"),
    (GRIND, "VERKTYG_OK"): (VERKTYG, "nasta anrop i samma runda"),
    (GRIND, "VERKTYG_FEL"): (VERKTYG, "nasta anrop i samma runda foll"),
    (GRIND, "AVVISAD"): (GRIND, "annu ett avvisat anrop i samma runda"),
    (GRIND, "VARNING"): (GRIND, "anmarkning i samma runda"),
    (GRIND, "OMSKRIVNING"): (SVARSGRIND, "slutsvaret krav omskrivning"),
    (GRIND, "KLAR"): (KLAR, "slutsvaret passerade samtliga grindar"),
    (GRIND, "STOPP"): (STOPPAD, "ett tak eller en stoppregel slog"),

    (KO, RUNDA): (MODELL, "operatoren svarade och turen fortsatter"),
    (KO, "STOPP"): (STOPPAD, "turen stannar och vantar pa operatoren"),

    (SVARSGRIND, RUNDA): (MODELL, "omskrivningskravet gar tillbaka"),
    (SVARSGRIND, "OMSKRIVNING"): (SVARSGRIND, "annu ett omskrivningskrav"),
    (SVARSGRIND, "AVVISAD"): (GRIND, "svarstexten avvisades av en grind"),
    (SVARSGRIND, "VERKTYG_OK"): (VERKTYG, "modellen anropade i stallet"),
    (SVARSGRIND, "VERKTYG_FEL"): (VERKTYG, "modellens nya anrop foll"),
    (SVARSGRIND, "VARNING"): (SVARSGRIND, "anmarkning pa svarsvagen"),
    (SVARSGRIND, "KLAR"): (KLAR, "det omskrivna svaret gick igenom"),
    (SVARSGRIND, "STOPP"): (STOPPAD, "omskrivningstaket slog"),
}

# --- stoppkoderna --------------------------------------------------------

# 23_llm_granssnitt.md avsnitt 6 har en SLUTEN lista, och loopen har en egen.
# Tabellen binder ihop dem, och `okanda_stoppkoder()` faller den dag koden far
# en stoppregel specen inte kanner. En sluten lista som inte provas mot koden
# ar en lista som redan glidit.
STOPPKODER = {
    "tystnad": ("TYSTNAD",
                "modellen svarade varken med text eller anrop. Tystnad ar "
                "aldrig ett godkannande (I3)"),
    "rundtak": ("TAK_RUNDOR", "10 rundor utan godkant slutsvar"),
    "raka_misslyckanden": ("TAK_FALL", "6 anrop i rad foll eller avvisades"),
    "upprepat_anrop": ("UPPREPAT_ANROP",
                       "samma anrop med samma argument efter tva fall"),
    "omskrivning_misslyckades": ("OMSKRIVNING_MISSLYCKADES",
                                 "svaret holls inne efter omskrivningstaket"),
}

# Koder som finns i specen men som loopen inte kan gora sjalv: de kommer ur
# lager utanfor turen. De star har for att listan ska vara HEL - en sluten
# lista med ett hal i ar inte sluten.
YTTRE_STOPPKODER = {
    "VANTAR_GODKANNANDE": "en kopost ar pending; turen fortsatter efter svar",
    "TAK_TOKEN": "kontextbudgeten tog slut (25_kontextbudget.md)",
    "TAK_TID": "vaggklockan; ett anrop svarade inte inom taket",
    "BRYGGA_NERE": "ingen formagerapport, eller anslutningen brots",
    "AVBRUTEN": "operatoren avbrot (24_samtalsloopen.md avsnitt 8)",
}

# ETT STOPP AR ALDRIG ETT GODKANNANDE (I3). Bara KLAR ar det.
KLARKOD = "KLAR"


def okanda_stoppkoder() -> Tuple[str, ...]:
    """Stoppregler i den byggda loopen som tabellen ovan inte kanner."""
    return tuple(sorted(set(_loop.STOPPREGLER) - set(STOPPKODER)))


def overflodiga_stoppkoder() -> Tuple[str, ...]:
    """Koder i tabellen som loopen inte langre kan ge."""
    return tuple(sorted(set(STOPPKODER) - set(_loop.STOPPREGLER)))


# --- sparet --------------------------------------------------------------

@dataclass(frozen=True)
class Steg:
    fran: str
    handelse: str
    till: str
    kod: str = ""

    def rad(self) -> str:
        return "%s --%s%s--> %s" % (self.fran, self.handelse,
                                    ("/" + self.kod) if self.kod else "",
                                    self.till)


def spar_ur_protokoll(protokoll) -> List[Steg]:
    """Turens protokoll -> sparet genom maskinen.

    Rundgranserna ar inte handelser i protokollet; de lases ur handelsernas
    rundnummer. En runda som stiger betyder att modellen fick ordet igen, och
    det ar en overgang som maste sta i tabellen som alla andra.
    """
    lage = START
    steg: List[Steg] = []
    runda = 0
    for h in protokoll.handelser:
        if h.runda != runda:
            runda = h.runda
            till = _nasta(lage, RUNDA)
            steg.append(Steg(lage, RUNDA, till))
            lage = till
        till = _nasta(lage, h.sort)
        steg.append(Steg(lage, h.sort, till, h.kod))
        lage = till
    return steg


def _nasta(lage: str, handelse: str) -> str:
    par = OVERGANGAR.get((lage, handelse))
    if par is None:
        raise Turfel(
            "ingen deklarerad overgang fran %s pa handelsen %s. En tur som gar "
            "en vag tabellen inte kanner ar en tur ingen har provat"
            % (lage, handelse))
    return par[0]


def slutlage(steg: Sequence[Steg]) -> str:
    return steg[-1].till if steg else START


T1_OKAND_OVERGANG = "T1_OKAND_OVERGANG"
T2_SLUTAR_I_ARBETE = "T2_SLUTAR_I_ARBETE"
T3_TYST_GODKANNANDE = "T3_TYST_GODKANNANDE"
T4_EFTER_STOPP = "T4_EFTER_STOPP"
T5_OKAND_STOPPKOD = "T5_OKAND_STOPPKOD"


def granska(protokoll) -> List[str]:
    """Faller pa varje tur som inte ar en laglig vag genom maskinen."""
    ut: List[str] = []
    try:
        steg = spar_ur_protokoll(protokoll)
    except Turfel as e:
        return ["%s: %s" % (T1_OKAND_OVERGANG, e)]

    lage = slutlage(steg)
    if lage in ARBETE:
        ut.append("%s: turen slutade i lage %s. Ett slut ar uttalat - ett spar "
                  "som tar slut i arbete ar en tur som slutade utan att saga "
                  "det" % (T2_SLUTAR_I_ARBETE, lage))
    sett_stopp = False
    for s in steg:
        if sett_stopp:
            ut.append("%s: %s kom efter ett STOPP. STOPPAD ar absorberande"
                      % (T4_EFTER_STOPP, s.rad()))
        if s.till == STOPPAD:
            sett_stopp = True
        if s.handelse == "STOPP" and s.kod and s.kod not in STOPPKODER:
            ut.append("%s: stoppkoden %r star varken i STOPPKODER eller i "
                      "loopens egen lista" % (T5_OKAND_STOPPKOD, s.kod))
    if getattr(protokoll, "klar", False):
        if lage != KLAR:
            ut.append("%s: protokollet ar markt klart men sparet slutar i %s"
                      % (T3_TYST_GODKANNANDE, lage))
        if not (protokoll.slutsvar or "").strip():
            ut.append("%s: turen ar markt klar med ett TOMT slutsvar. Tystnad "
                      "ar aldrig ett godkannande (I3)" % T3_TYST_GODKANNANDE)
    else:
        if lage == KLAR:
            ut.append("%s: sparet slutar i KLAR men protokollet ar inte markt "
                      "klart" % T3_TYST_GODKANNANDE)
    return ut


@dataclass
class Tackning:
    """Vilka lagen och overgangar 95 riktiga turer faktiskt korde igenom.

    En maskin ingen tur besoker ar en beskrivning, inte en grind. Talet
    rapporteras alltid som par: hur manga overgangar som finns, och hur manga
    som nagon tur verkligen gick.
    """

    lagen: Dict[str, int] = field(default_factory=dict)
    overgangar: Dict[Tuple[str, str], int] = field(default_factory=dict)

    def lagg(self, steg: Sequence[Steg]) -> None:
        for s in steg:
            self.lagen[s.fran] = self.lagen.get(s.fran, 0) + 1
            self.lagen[s.till] = self.lagen.get(s.till, 0) + 1
            nyckel = (s.fran, s.handelse)
            self.overgangar[nyckel] = self.overgangar.get(nyckel, 0) + 1

    def obesokta_overgangar(self) -> Tuple[Tuple[str, str], ...]:
        return tuple(sorted(set(OVERGANGAR) - set(self.overgangar)))

    def obesokta_lagen(self) -> Tuple[str, ...]:
        return tuple(sorted(set(TILLSTAND) - set(self.lagen)))

    def rad(self) -> str:
        return ("tackning: %d av %d lagen, %d av %d overgangar"
                % (len(self.lagen), len(TILLSTAND), len(self.overgangar),
                   len(OVERGANGAR)))


# --- tidsvakten ----------------------------------------------------------

# Vaggklockan for en hel tur. PRELIMINAR, satts av matning M-28. Vald over
# operatorens talamodsgrans pa tva minuter (24_samtalsloopen.md), sa att taket
# aldrig ar det som gor granssnittet tyst.
VAGGKLOCKA_MAX_S = 180.0    # PRELIMINAR, satts av M-28

# Taket for ETT verktygsanrop. Harkomst: bryggans eget standardtak ar 5 000 ms
# (verktyg/bas.py TIMEOUT_MS, ur 31_brygga_protokoll.md), och filoperationer
# 60 000 ms. Taket har ligger pa filtaket sa att tidsvakten aldrig faller ett
# anrop bryggan sjalv skulle ha slappt igenom.
ANROP_MAX_S = 60.0          # verktyg/bas.py TIMEOUT_MS_FIL, 31_brygga_protokoll.md


class Tidsvaktkanal(Verktygskanal):
    """En kanal som vagrar lita pa ett svar som kom efter taket.

    Den avbryter INGENTING, och det ar inte en lucka. `pump._op_cancel` svarar
    att exec kors synkront pa VC:s trad och inte gar att avbryta (KOD@HEAD,
    M-13). Det enda arliga en tidsvakt kan gora i det laget ar att vagra rakna
    svaret som ett ok - bryggan ar da dessutom markt degraded, och ett svar
    fran en degraderad brygga hor inte till den har turen.

    Klockan ar injicerad sa att provet inte behover sova. Ett prov som mater
    en tidsgrans genom att vanta mater schemalaggaren.
    """

    def __init__(self, kanal: Verktygskanal, tak_s: float = ANROP_MAX_S,
                 klocka: Optional[Callable[[], float]] = None):
        self.kanal = kanal
        self.tak_s = tak_s
        if klocka is None:
            import time
            klocka = time.monotonic
        self.klocka = klocka
        self.tider: List[Tuple[str, float]] = []

    def utfor(self, namn: str, argument: Dict[str, Any]) -> Anropsutfall:
        t0 = self.klocka()
        utfall = self.kanal.utfor(namn, argument)
        gick = self.klocka() - t0
        self.tider.append((namn, gick))
        if gick <= self.tak_s:
            return utfall
        return Anropsutfall(
            verktyg=namn, argument=dict(argument), ok=False,
            fel=("TAK_TID: %s svarade efter %.1f s, taket ar %.1f s. Svaret "
                 "raknas inte: bryggan ar markt osaker efter en timeout och "
                 "ett svar darifran hor inte till den har turen. Anropet gick "
                 "INTE att avbryta - exec kors synkront pa VC:s trad (M-13)"
                 % (namn, gick, self.tak_s)),
            varningar=tuple(utfall.varningar) + ("svaret kom efter taket",))


# --- svaret som inte gar att tolka ---------------------------------------

# Hur manga omforsok ett otolkbart modellsvar far. Harkomst:
# 24_samtalsloopen.md avsnitt 1 steg 6 - "tidsoverdrag eller leverantorsfel =>
# ETT omforsok, sedan TAK_TID. Aldrig tyst."
OMFORSOK_MAX = 1            # 24_samtalsloopen.md avsnitt 1, steg 6

SVARSFEL = "SVARSFEL"


class Tolkvakt(object):
    """En modell som overlever ett svar adaptern inte kan tolka.

    Adaptern kastar Modellfel nar leverantorens svar inte haller formen
    (`harness/oversattning.py`: argumenten gar inte att avkoda som JSON,
    svaret saknar sina falt). Utan en vakt tar det undantaget hela turen med
    sig: ingen stoppkod, inget protokoll, ingenting att visa operatoren - och
    en tur som dor pa sin egen bokforing har inte matt nagot.

    Vakten gor tre saker och ingenting mer:
      1. gor ETT omforsok (24_samtalsloopen.md steg 6),
      2. lamnar darefter ett TOMT modellsvar, vilket den byggda loopen stoppar
         pa - fail-closed, ingenting levereras,
      3. minns VARFOR, sa att stoppet kan rapporteras som SVARSFEL i stallet
         for som tystnad.

    Punkt 3 ar skalet att vakten finns i stallet for ett tyst try/except: ett
    otolkbart svar och en tyst modell ar tva olika fel med samma utseende, och
    en kod som slar ihop dem lar aldrig nagon vad som verkligen hande.
    """

    def __init__(self, modell, omforsok: int = OMFORSOK_MAX):
        self.modell = modell
        self.omforsok = omforsok
        self.fall: List[str] = []

    @property
    def namn(self) -> str:
        return getattr(self.modell, "namn", "okand")

    @property
    def leverantor(self) -> str:
        return getattr(self.modell, "leverantor", "okand")

    def svara(self, systemprompt, meddelanden, verktyg):
        from ..harness.fel import Modellfel
        from ..harness.modell import Modellsvar
        for forsok in range(self.omforsok + 1):
            try:
                return self.modell.svara(systemprompt, meddelanden, verktyg)
            except Modellfel as e:
                self.fall.append("forsok %d: %s" % (forsok + 1, e))
        return Modellsvar(text="", anrop=())


def stoppkod(protokoll, vakt: Optional[Tolkvakt] = None) -> str:
    """Turens stoppkod med SPECENS namn, inte loopens interna.

    En tur som stoppade darfor att svaret inte gick att TOLKA far koden
    SVARSFEL, aven om den byggda loopen sag den som tystnad. De tva ar olika
    fel, och det ar vakten som vet vilket.
    """
    if vakt is not None and vakt.fall:
        return SVARSFEL
    for h in protokoll.handelser:
        if h.sort == "STOPP":
            return STOPPKODER.get(h.kod, (h.kod, ""))[0]
    if getattr(protokoll, "klar", False):
        return KLARKOD
    return "STOPP:okant"
