# -*- coding: utf-8 -*-
"""Stegen som hittar orsaken (`28_lagen_och_aterhamtning.md` §5.3).

Sju frågor i ordning, var och en billigare än nästa, var och en med en RIKTIG
rad ur en riktig logg som svar. Regel L-8 säger att panelen kör stegen själv
när läget blir `nere` och visar resultatet: *operatören ska inte behöva öppna
en loggfil för att få veta varför.*

## Två saker som gör den här stegen till en grind och inte till en checklista

**En obestämd fråga stoppar stegen.** Går loggen inte att läsa är svaret på
frågan varken ja eller nej — det är *vet inte*. En stege som hoppar över den
frågan och rapporterar nästa stegs svar som orsaken pekar ut fel sak med full
säkerhet. Därför bär `Stegsvar.svar` tre värden, och första obestämda svaret
gör resten av stegen obestämd med skälet *"steg N var obestämt"*.

**Raderna finns i koden, inte i den här filen.** Varje markör nedan är en
sträng som `ext/vc_addon/vc_assist/` faktiskt skriver.
`test_aterhamtning_stegen.py` läser tilläggets källa som text och faller om en
markör inte längre finns där. En stege som letar efter rader ingen skriver
mäter sin egen fantasi, och den skulle stå grön för alltid.

## Steg 2 bär ett mätt undantag

Raden `bridge_cmd executed` kan komma **även när modulkroppen aldrig kördes**
(M-09): `loadCommand` returnerade ett objekt och `execute()` kastade inte,
trots att modulen var okompilerbar. Steget kräver därför att NÄSTA rad också
finns. Att lita på `executed` ensam är precis den tysta fällan fas 0 mätte.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

from .lagen import (KROKEN_FYRADE_INTE, MODULEN_KORDES_ALDRIG, OKAND,
                    OPERATOREN_STOPPADE, Orsak, PORT_UPPTAGEN,
                    SKRIPTBETEENDE, SKRIPTET_KOMPILERAR_INTE, SPARAD_LAYOUT)

# Källorna. Nycklarna är loggarnas namn utan sökväg: var de ligger är
# plattformsberoende (`~` är profilen på Windows, prefixets användarmapp under
# Wine) och hör inte hemma i en stege.
BOOTLOGG = "vc_assist_boot.log"
BRYGGLOGG = "vc_assist_brygga.log"
KALLOR = (BOOTLOGG, BRYGGLOGG)


@dataclass(frozen=True)
class Stegdef:
    nr: int
    fraga: str
    kalla: str
    # Raden som betyder JA. Alla måste finnas.
    ja: Tuple[str, ...]
    # Orsaken när svaret är nej.
    orsak: Orsak
    # Vad den som läser ska veta om just det här steget.
    anmarkning: str = ""


STEGEN: Tuple[Stegdef, ...] = (
    Stegdef(1, "Fyrade kroken?", BOOTLOGG, ("OnAppInitialized",),
            KROKEN_FYRADE_INTE,
            "Ingen rad alls betyder oftast fel Python N-nivå (M-01). VC "
            "startar normalt och säger ingenting."),
    Stegdef(2, "Laddades kommandot?", BOOTLOGG,
            ("loadCommand uri=", "bridge_cmd executed"),
            MODULEN_KORDES_ALDRIG,
            "Raden \"bridge_cmd executed\" kan komma även när modulkroppen "
            "aldrig kördes (M-09). Nästa rad avgör."),
    Stegdef(3, "Kompilerade skriptmallen?", BOOTLOGG,
            ("brygg-komponenten byggd, skriptet kompilerar",),
            SKRIPTET_KOMPILERAR_INTE,
            "Annars står \"SKRIPTET GAR INTE ATT KOMPILERA\" med radnummer "
            "och tre rader sammanhang."),
    Stegdef(4, "Band bryggan porten?", BRYGGLOGG,
            ("startar pa 127.0.0.1:", "lyssnar pa 127.0.0.1:"),
            PORT_UPPTAGEN,
            "Står bara den första raden är porten upptagen. Loggen skrivs "
            "före bindningen just därför (M-13, sidofynd)."),
    Stegdef(5, "Tickar pumpen?", BRYGGLOGG, ("pumpen igang",),
            OPERATOREN_STOPPADE,
            "Och ping ger ett tick som växer. Ett tick som står stilla är "
            "inte samma sak som ingen rad alls."),
    Stegdef(6, "Dog den, och av vad?", BRYGGLOGG, (),
            OPERATOREN_STOPPADE,
            "Sista raderna före tystnaden: \"kord q<n> -> ...\", "
            "\"simuleringen stoppad\", \"ber om omstart\"."),
    Stegdef(7, "Var det en av de två mätta dödarna?", BRYGGLOGG, (),
            SPARAD_LAYOUT,
            "\"dodar pumpen\" på posten, eller createBehaviour(VC_SCRIPT) i "
            "koden. Se M-13."),
)

# Steg 6 och 7 har ingen enkel ja-rad: de läser vad som HÄNDE, inte om något
# fyrade. Markörerna nedan är pumpens och kommandots egna, och de avgör vilken
# orsak steget pekar ut.
DOG_AV = (
    ("dodar pumpen", SPARAD_LAYOUT),
    ("simuleringen stoppad", OPERATOREN_STOPPADE),
)
SKRIPTMARKOR = "createBehaviour"


@dataclass(frozen=True)
class Stegsvar:
    steg: Stegdef
    # True = ja, False = nej, None = gick inte att avgöra.
    svar: Optional[bool]
    # Källans EGNA rad, eller skälet till att svaret är obestämt. Aldrig en
    # sammanfattning: den som läser ska se raden, inte vår tolkning av den.
    ordagrant: str

    def rad(self) -> str:
        ord_ = {True: "ja", False: "nej", None: "vet inte"}[self.svar]
        return "%d %-8s %-38s %s" % (self.steg.nr, ord_, self.steg.fraga,
                                     self.ordagrant)


def _rad_ur(text: str, markor: str) -> str:
    """Källans egen rad som bär markören, den sista om flera."""
    traff = ""
    for rad in text.splitlines():
        if markor in rad:
            traff = rad.strip()
    return traff


def kor_stegen(kallor: Mapping[str, Optional[str]]) -> Tuple[Stegsvar, ...]:
    """Kör stegen mot loggarnas innehåll. `None` = loggen gick inte att läsa.

    Returnerar ett svar per steg, alltid sju. En stege som lämnar ut ett steg
    ser kortare och säkrare ut än den är.
    """
    ut: List[Stegsvar] = []
    stoppat_vid: Optional[int] = None
    for steg in STEGEN:
        if stoppat_vid is not None:
            ut.append(Stegsvar(steg, None,
                               "steget nåddes inte: steg %d var obestämt"
                               % stoppat_vid))
            continue
        text = kallor.get(steg.kalla)
        if text is None:
            ut.append(Stegsvar(
                steg, None,
                "%s gick inte att läsa; frågan går inte att besvara"
                % steg.kalla))
            stoppat_vid = steg.nr
            continue
        if steg.nr == 6:
            svar, ordagrant = _steg6(text)
        elif steg.nr == 7:
            svar, ordagrant = _steg7(text)
        else:
            saknade = [m for m in steg.ja if m not in text]
            if saknade:
                svar = False
                ordagrant = "raden %r finns inte i %s" % (saknade[0],
                                                          steg.kalla)
            else:
                svar = True
                ordagrant = _rad_ur(text, steg.ja[-1])
        ut.append(Stegsvar(steg, svar, ordagrant))
        if svar is False:
            stoppat_vid = None  # ett NEJ är ett svar, inte en obestämdhet
    return tuple(ut)


def _steg6(text: str) -> Tuple[Optional[bool], str]:
    """Dog den, och av vad? `True` betyder att den INTE dog."""
    for markor, _orsak in DOG_AV:
        rad = _rad_ur(text, markor)
        if rad:
            return False, rad
    return True, "ingen rad om att simuleringen stoppade"


def _steg7(text: str) -> Tuple[Optional[bool], str]:
    """Var det en av de två mätta dödarna? `True` betyder att det inte var."""
    rad = _rad_ur(text, "dodar pumpen")
    if rad:
        return False, rad
    if SKRIPTMARKOR in text:
        return False, _rad_ur(text, SKRIPTMARKOR)
    return True, "ingen av de två mätta dödarna står i loggen"


def orsak_ur_stegen(svaren) -> Tuple[Orsak, Optional[Stegsvar]]:
    """Orsaken stegen pekar ut, och steget som pekade.

    Regeln är sträng och det är hela poängen: **det första nej:et vinner, och
    ett obestämt steg går inte att passera.** Skulle stegen få hoppa över en
    fråga den inte kunde besvara skulle den peka ut ett senare steg med full
    säkerhet — och en orsak som pekas ut fel skickar operatören åt fel håll
    med samma tonfall som en riktig.

    Utan ett nej finns ingen orsak att ge, och då är svaret `OKAND`. Det är
    N-5: `nere` utan orsak får aldrig visas, men *"orsaken gick inte att
    avgöra"* är en orsak att visa — den falska grönen är att tiga.
    """
    for s in svaren:
        if s.svar is None:
            return OKAND, s
        if s.svar is False:
            if s.steg.nr == 6:
                for markor, orsak in DOG_AV:
                    if markor in s.ordagrant:
                        return orsak, s
            if s.steg.nr == 7:
                if SKRIPTMARKOR in s.ordagrant:
                    return SKRIPTBETEENDE, s
                return SPARAD_LAYOUT, s
            return s.steg.orsak, s
    return OKAND, None


def sammanfatta(svaren) -> Dict[str, int]:
    """Ja, nej och vet inte. Tre tal, aldrig två."""
    return {
        "ja": len([s for s in svaren if s.svar is True]),
        "nej": len([s for s in svaren if s.svar is False]),
        "vet inte": len([s for s in svaren if s.svar is None]),
    }


__all__ = ["BOOTLOGG", "BRYGGLOGG", "DOG_AV", "KALLOR", "SKRIPTMARKOR",
           "STEGEN", "Stegdef", "Stegsvar", "kor_stegen", "orsak_ur_stegen",
           "sammanfatta"]
