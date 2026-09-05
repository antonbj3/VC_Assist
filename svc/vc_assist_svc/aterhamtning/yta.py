# -*- coding: utf-8 -*-
"""Ytan: vad användaren ser när något har dött, och om det kommer tillbaka.

Formen är fas 17:s och katalogsökningens (M-60), och den ärvs med flit i
stället för att uppfinnas om:

1. **Rader, inte JSON.** Ett fast antal fält per rad.
2. **Alltid "N totalt, visar M".** En visning som inte säger hur mycket den
   inte visade ser uttömmande ut.
3. **`saknas` är ett förstklassigt svar.**
4. **Ett fällt läge ser ut som fällt.** Läget står först och är härlett.

Till dem kommer tre som hör just den här ytan till, och var och en är en
mening operatören har sagt att han inte vill läsa:

5. **Ingenting försöker igen — om ingenting försöker igen.** *"Ett problem
   uppstod, vi försöker igen"* är värre än tystnad när ingen återhämtning
   pågår: den ber användaren vänta på något som inte händer. Står det ett
   försök i visningen står det ett försök i protokollet, och det kan lyckas.
6. **Varje väg tillbaka bär sin kanskap.** Tre svar: kan lyckas, kan inte
   lyckas, okänt. Ett okänt som skrivs som ett ja är ett löfte, och ett löfte
   till någon som väntar på en död brygga är det dyraste vi kan ge.
7. **Vet inte står kvar också när allt är grönt.** Räckvidden nedan är
   permanent: raden `modal oppen` finns inte i koden, Wines lyssningskö är
   oprövad, ingen väg tillbaka är prövad på Windows.

Rubriken `VET INTE:` och frasen `pågår sedan` importeras ur `forlopp` i
stället för att skrivas av. Två ytor som säger samma sak med olika ord är två
ordförråd, och det ena kommer att glida.
"""
from __future__ import annotations

import textwrap
import time
from typing import List, Optional, Sequence, Tuple

from ..forlopp.handelser import (EJ_PROVAT, Ovisshet, PAGAR_MARKOR,
                                 UTANFOR_RACKVIDD)
from ..forlopp.yta import RUBRIK_VET_INTE, SAKNAS
from .bild import Blick, MODAL_OPPEN_RAD, lage_for
from .lagen import (ANSLUTEN, Aterhamtningsfel, BLOCKERAD, DEGRADERAD,
                    DELSYSTEM, FRANKOPPLAD, KAN_NEJ, KO_VANTAR, LEVANDE, NERE,
                    OBESTAMT, OKAND, Orsak, PROVTAGNING_PAGAR,
                    SIMULERING_IGANG, STILLA, UTAN_SJALVSTART, kan_lyckas,
                    vagarna)
from .stegen import BOOTLOGG, BRYGGLOGG, kor_stegen, orsak_ur_stegen, sammanfatta

# Hur många avläsningar som får synas. En sond som går varje sekund lämnar
# tusentals rader över ett uppdrag, och alla är samma rad.
MAX_AVLASNINGSRADER = 8     # PRELIMINÄR. Samma form som M-64. Satt av M-103.

RUBRIK_LAGE = "LÄGE:"
RUBRIK_ORSAK = "ORSAK:"
RUBRIK_ATERHAMTNING = "ÅTERHÄMTNING:"
RUBRIK_VAGAR = "VÄGAR TILLBAKA:"
RUBRIK_DELSYSTEM = "DELSYSTEM:"
RUBRIK_AVLASNINGAR = "AVLÄSNINGAR:"
RUBRIK_STEGEN = "STEGEN SOM HITTAR ORSAKEN:"

# Meningarna grinden letar efter i en FRÄMMANDE renderares text. De står som
# konstanter av samma skäl som `PAGAR_MARKOR` i fas 17: en grind som letar
# efter en formulering den hittat på i farten mäter sin egen fantasi.
FORSOKER_MARKOR = "försöker igen"
ATERHAMTAR_MARKOR = "återhämtning pågår"
INGET_FORSOK = "Ingenting försöker igen."

# Radbredden. En rad som inte får plats i ett terminalfönster läses inte, och
# en yta som inte läses är samma sak som ingen yta. Gränsen gäller VISNINGENS
# EGNA rader: någon annans ord bryts aldrig, för då finns de inte längre.
MAX_BREDD = 100     # 26_appen.md, panelens sju fält är text i en terminal.

_MARKOR_START = "--- %s, ordagrant ---"
_MARKOR_SLUT = "--- slut ---"

# Allvarsordningen ACROSS delsystem: vilken rad som får stå överst när tre
# saker kan vara sjuka samtidigt. Den är INTE samma sak som `FORETRADE` i
# `lagen.py`, som ordnar flera samtidiga lägen hos ETT delsystem (§1.1). De
# två svarar på olika frågor, och att slå ihop dem skulle göra en av dem fel.
#
# `NERE` står först och inte `OBESTÄMT`: en känd död är det användaren kan
# göra något åt. Ingenting göms av valet — varje delsystem står med sitt eget
# läge i sitt eget block, alltid.
ALLVAR = (NERE, OBESTAMT, BLOCKERAD, DEGRADERAD, FRANKOPPLAD, KO_VANTAR,
          PROVTAGNING_PAGAR, SIMULERING_IGANG, ANSLUTEN)

# Det återhämtningen inte kan veta, och som ingen körning kan beta av. Formen
# är fas 17:s RACKVIDDEN: nyckel, namn, skäl. Var och en pekar på det som
# saknas, inte på en känsla.
RACKVIDDEN = (
    ("modal_oppen_raden", "den öppna statusrutan",
     "raden %r finns inte i ext/vc_addon/; läget BLOCKERAD kan inte fyras "
     "förrän den skrivs (26_appen.md A-3, M-21)" % MODAL_OPPEN_RAD),
    ("wines_lyssningsko", "Wines lyssningskö",
     "att connect() lyckas mot en död pump också genom Wines winsock är "
     "oprövat (M-25)"),
    ("windows", "vägarna på Windows",
     "ingen väg tillbaka är prövad på Windows; wineserver finns inte där "
     "(M-44, I17)"),
    ("tidsgranserna", "tidsgränserna",
     "T_ping och T_nere är PRELIMINÄRA, härledda ur M-03:s tur och retur och "
     "aldrig mätta mot en död brygga"),
    ("levande_vc", "en levande VC",
     "ingen väg tillbaka i den här ytan har körts mot en VC som verkligen "
     "gick ned; allt är attrapper"),
)


def rackvidden() -> Tuple[Ovisshet, ...]:
    return tuple(Ovisshet(namn, "%-19s %s" % (nyckel, skal), UTANFOR_RACKVIDD)
                 for nyckel, namn, skal in RACKVIDDEN)


def allvarligast(blick: Blick) -> str:
    """Delsystemet vars läge ska stå överst. Ingenting göms av valet."""
    ordning = dict((lage, i) for i, lage in enumerate(ALLVAR))
    return min(DELSYSTEM, key=lambda d: (ordning.get(blick.lage(d), 99), d))


def ovissheter(blick: Blick) -> Tuple[Ovisshet, ...]:
    """Räckvidden plus det just den här blicken inte kunde avgöra.

    De läggs av den som LÄSER, inte av den som sonderar. En sond som är död
    kan inte skriva att den är död — samma skäl som M-93 lade speglingens
    ovissheter i läsaren.
    """
    ut: List[Ovisshet] = list(rackvidden())
    for d in DELSYSTEM:
        alder = blick.alder(d)
        if alder is None:
            ut.append(Ovisshet(
                d, "ingen avläsning gjord; om %s lever är inte prövat" % d,
                EJ_PROVAT))
            continue
        if alder < 0.0:
            ut.append(Ovisshet(
                d, "avläsningen ligger %.1f s i framtiden; klockorna är osams "
                   "och åldern går inte att räkna" % (-alder,), EJ_PROVAT))
            continue
        if alder > blick.bild.t_nere:
            ut.append(Ovisshet(
                d, "avläsningen är %.1f s gammal, taket är %.1f s; om det "
                   "läget fortfarande gäller går inte att avgöra"
                   % (alder, blick.bild.t_nere), EJ_PROVAT))
    return tuple(ut)


def _bryt(text: str, indrag: str = "  ") -> List[str]:
    """Visningens egna meningar, brutna så att de går att läsa.

    Bara våra egna. Ett `ordagrant` block bryts aldrig — bryter man det finns
    strängen inte längre i texten, och då går det inte att kontrollera att den
    kom fram hel.
    """
    rader = textwrap.wrap(text, width=MAX_BREDD - len(indrag),
                          subsequent_indent=indrag,
                          break_long_words=False, break_on_hyphens=False)
    return rader or [text]


def _block(vem: str, text: str) -> List[str]:
    """Någon annans ord, rått, mellan två markörrader.

    Prefixas varje rad finns strängen inte längre i texten, och då går det inte
    att kontrollera att den kom fram hel. Samma val som
    `reparation.standardinramning`.
    """
    return [_MARKOR_START % vem, text, _MARKOR_SLUT]


def _lagerader(blick: Blick) -> List[str]:
    d = allvarligast(blick)
    rader = ["%s %s %s" % (RUBRIK_LAGE, d, blick.lage(d))]
    if blick.bild.utan_sjalvstart:
        rader.extend(_bryt(
            "  %s — bryggan har slagit av sin egen omstart efter taket 20 på "
            "en minut. Den försöker inte igen." % UTAN_SJALVSTART, "    "))
    return rader


def _orsakrader(blick: Blick) -> List[str]:
    rader: List[str] = []
    for d in DELSYSTEM:
        lage = blick.lage(d)
        if lage in LEVANDE and lage != DEGRADERAD:
            continue
        if lage == FRANKOPPLAD and blick.bild.sista(d) is None:
            rader.extend(_bryt("%s %s: ingen avläsning gjord. Det är ett "
                               "besked om oss, inte om %s."
                               % (RUBRIK_ORSAK, d, d)))
            continue
        orsak = blick.orsak(d)
        if orsak is None:
            rader.extend(_bryt("%s %s: %s — orsaken gick inte att avgöra. %s"
                               % (RUBRIK_ORSAK, d, SAKNAS, OKAND.text)))
        else:
            rader.extend(_bryt("%s %s: %s  [%s]"
                               % (RUBRIK_ORSAK, d, orsak.text,
                                  orsak.stampel)))
        sista = blick.bild.sista(d)
        if sista is not None and sista.fel:
            rader.extend(_block(d, sista.fel))
    return rader


def mojliga_och_omojliga(blick: Blick):
    """De pågående försöken, delade på om de KAN lyckas — räknat om NU.

    Kanskapen frystes när försöket började, och världen kan ha ändrat sig
    sedan dess: slår bryggan av sin egen självstart mitt i ett självstartsförsök
    blir försöket omöjligt utan att någon rör det. Ett sådant försök får inte
    räknas bland dem som pågår. Det ska stå kvar, med beskedet att det inte
    längre kan lyckas — att stryka det vore att dölja att vi väntade förgäves.
    """
    mojliga, omojliga = [], []
    for f in blick.bild.forsoken:
        if not f.pagar:
            continue
        nu_kan = kan_lyckas(f.orsak, f.vag, blick.bild.utan_sjalvstart)
        (omojliga if nu_kan == KAN_NEJ else mojliga).append((f, nu_kan))
    return tuple(mojliga), tuple(omojliga)


def _forsokrader(blick: Blick) -> List[str]:
    """Vad som försöker, och — mycket oftare — att ingenting gör det."""
    rader: List[str] = []
    mojliga, omojliga = mojliga_och_omojliga(blick)
    avslutade = [f for f in blick.bild.forsoken if not f.pagar]
    if not mojliga:
        rader.append("%s inget försök pågår" % RUBRIK_ATERHAMTNING)
        rader.extend(_bryt("  %s Systemet gör ingenting av sig självt förrän "
                           "du säger till." % INGET_FORSOK, "    "))
    else:
        rader.append("%s %d försök pågår" % (RUBRIK_ATERHAMTNING,
                                             len(mojliga)))
        for f, nu_kan in mojliga:
            rader.extend(_bryt(
                "  %s (%s), %s sedan %.1f s"
                % (f.vag.text, nu_kan, f.orsak.delsystem,
                   blick.nu - f.t_start), "    "))
    for f, nu_kan in omojliga:
        rader.extend(_bryt(
            "  %s: %s. Det försöket %s längre, och ingenting väntar på det."
            % (f.vag.text, nu_kan, "kan inte" if nu_kan == KAN_NEJ else "kan"),
            "    "))
    if avslutade:
        rader.append("  tidigare försök: %d totalt, visar %d"
                     % (len(avslutade), len(avslutade)))
        for f in avslutade:
            utfall = "lyckades" if f.lyckades else "misslyckades"
            rader.append("    %-10s %s" % (utfall, f.vag.text))
            if f.ordagrant:
                rader.extend("    " + r for r in _block(f.vag.nyckel,
                                                        f.ordagrant))
    return rader


def _vagrader(blick: Blick) -> List[str]:
    """Vägarna tillbaka, var och en med sin kanskap och sin härkomst."""
    d = allvarligast(blick)
    orsak = blick.orsak(d)
    if orsak is None or blick.lage(d) in (ANSLUTEN, SIMULERING_IGANG,
                                          PROVTAGNING_PAGAR, KO_VANTAR):
        return ["%s 0 totalt, visar 0 — %s svarar, och det finns inget att "
                "ta sig tillbaka från" % (RUBRIK_VAGAR, d)]
    par = vagarna(orsak, blick.bild.utan_sjalvstart)
    rader = ["%s %d totalt, visar %d" % (RUBRIK_VAGAR, len(par), len(par))]
    if not par:
        rader.extend(_bryt("  %s — orsaken bär ingen väg tillbaka. Det "
                           "betyder att ingen är känd, inte att det är "
                           "hopplöst." % SAKNAS, "    "))
    for i, (vag, kan) in enumerate(par, 1):
        rader.extend(_bryt("  %d %s" % (i, vag.rad()), "    "))
        rader.append("    %s" % kan)
    return rader


def _delsystemrader(blick: Blick) -> List[str]:
    rader = ["%s %d totalt, visar %d" % (RUBRIK_DELSYSTEM, len(DELSYSTEM),
                                         len(DELSYSTEM))]
    for d in DELSYSTEM:
        alder = blick.alder(d)
        if alder is None:
            nar = "ingen avläsning gjord"
        elif alder < 0.0:
            nar = "avläst %.1f s i framtiden" % (-alder,)
        else:
            nar = "avläst för %.1f s sedan" % alder
        rader.append("  %-9s %-17s %s" % (d, blick.lage(d), nar))
    return rader


def _avlasningsrader(blick: Blick) -> List[str]:
    alla = blick.bild.avlasningar
    visade = alla[-MAX_AVLASNINGSRADER:]
    rader = ["%s %d totalt, visar %d" % (RUBRIK_AVLASNINGAR, len(alla),
                                         len(visade))]
    dolda = len(alla) - len(visade)
    if dolda:
        rader.append("  ... %d till, ej visade." % dolda)
    for a in visade:
        svar = {True: "svar", False: "tyst", None: "ej frågat"}[a.svarade]
        rader.append("  t-%-7.1f %-9s %-10s %s"
                     % (blick.nu - a.t, a.delsystem, svar,
                        a.fel or a.orsak or ""))
    return rader


def _stegrader(blick: Blick, loggar) -> List[str]:
    """Stegen, men bara när de har en fråga att svara på.

    Regel L-8: panelen kör stegen SJÄLV när läget blir nere. Att visa dem när
    allt svarar vore att fylla ytan med grönt som ingen läser.
    """
    lage = blick.lage("bryggan")
    if lage not in (NERE, OBESTAMT, FRANKOPPLAD, BLOCKERAD):
        return []
    if loggar is None:
        return ["%s 7 totalt, visar 0 — loggarna lästes inte" % RUBRIK_STEGEN]
    svaren = kor_stegen(loggar)
    tal = sammanfatta(svaren)
    orsak, steget = orsak_ur_stegen(svaren)
    rader = ["%s %d totalt, visar %d" % (RUBRIK_STEGEN, len(svaren),
                                         len(svaren)),
             "  %d ja, %d nej, %d vet inte" % (tal["ja"], tal["nej"],
                                               tal["vet inte"])]
    rader.extend("  " + s.rad() for s in svaren)
    if steget is None:
        rader.extend(_bryt("  stegen fann ingen orsak: %s" % orsak.text,
                           "    "))
    else:
        rader.extend(_bryt("  stegen pekar på steg %d: %s"
                           % (steget.steg.nr, orsak.text), "    "))
    return rader


def _ovissrader(blick: Blick) -> List[str]:
    poster = ovissheter(blick)
    rader = ["%s %d poster" % (RUBRIK_VET_INTE, len(poster))]
    utanfor = [o for o in poster if o.klass == UTANFOR_RACKVIDD]
    ejprovat = [o for o in poster if o.klass == EJ_PROVAT]
    if utanfor:
        rader.append("  utanför räckvidd, permanent:")
        for o in utanfor:
            rader.extend(_bryt("    %-24s %s" % (o.namn, o.skal),
                               "      "))
    if ejprovat:
        rader.append("  ej prövat i den här avläsningen:")
        for o in ejprovat:
            rader.extend(_bryt("    %-24s %s" % (o.namn, o.skal),
                               "      "))
    return rader


def _rendera_obestamd(blick: Blick) -> str:
    """Ytan för en systembild som inte gick att läsa.

    Läget är OBESTÄMT och felet står ordagrant. Ett läsfel som ser ut som en
    lugn början är den falska grönen i sin renaste form — M-93 skrev formen,
    och den gäller ord för ord här.
    """
    rader = ["%s %s %s" % (RUBRIK_LAGE, "systembilden", OBESTAMT),
             "%s systembilden %s gick inte att läsa."
             % (RUBRIK_ORSAK, blick.kalla or SAKNAS)]
    rader.extend(_block("läsfelet", blick.fel))
    rader.append("")
    rader.append("%s inget försök pågår" % RUBRIK_ATERHAMTNING)
    rader.extend(_bryt("  %s Ingen avläsning finns att försöka utifrån."
                       % INGET_FORSOK, "    "))
    rader.append("")
    rader.extend(_bryt("%s 0 totalt, visar 0 — orsaken är okänd, så vägen "
                       "tillbaka är det också" % RUBRIK_VAGAR))
    rader.append("")
    rader.append("%s %d totalt, visar %d" % (RUBRIK_DELSYSTEM, len(DELSYSTEM),
                                             len(DELSYSTEM)))
    for d in DELSYSTEM:
        rader.append("  %-9s %-17s filen gick inte att läsa" % (d, OBESTAMT))
    rader.append("")
    rader.append("%s 0 totalt, visar 0" % RUBRIK_AVLASNINGAR)
    rader.append("")
    poster = list(rackvidden())
    poster.append(Ovisshet("hela systembilden",
                           "filen gick inte att läsa, så ingenting i den går "
                           "att svara på", EJ_PROVAT))
    rader.append("%s %d poster" % (RUBRIK_VET_INTE, len(poster)))
    rader.append("  utanför räckvidd, permanent:")
    for o in poster[:-1]:
        rader.extend(_bryt("    %-24s %s" % (o.namn, o.skal), "      "))
    rader.append("  ej prövat i den här avläsningen:")
    rader.extend(_bryt("    %-24s %s" % (poster[-1].namn, poster[-1].skal),
                       "      "))
    rader.append("")
    rader.append("LÄST: %s" % time.strftime("%Y-%m-%d %H:%M:%S",
                                            time.localtime(blick.nu)))
    return "\n".join(rader)


def rendera(blick: Blick, loggar=None) -> str:
    """Hela ytan som text. `loggar` = {filnamn: innehåll eller None}."""
    if blick.obestamd:
        return _rendera_obestamd(blick)
    delar = [_lagerader(blick), _orsakrader(blick), _forsokrader(blick),
             _vagrader(blick), _delsystemrader(blick),
             _avlasningsrader(blick), _stegrader(blick, loggar),
             _ovissrader(blick)]
    rader: List[str] = []
    for del_ in delar:
        if not del_:
            continue
        if rader:
            rader.append("")
        rader.extend(del_)
    rader.append("")
    rader.append("LÄST: %s" % time.strftime("%Y-%m-%d %H:%M:%S",
                                            time.localtime(blick.nu)))
    return "\n".join(rader)


__all__ = ["ALLVAR", "ATERHAMTAR_MARKOR", "FORSOKER_MARKOR", "INGET_FORSOK",
           "MAX_AVLASNINGSRADER", "MAX_BREDD", "PAGAR_MARKOR",
           "mojliga_och_omojliga",
           "RACKVIDDEN",
           "RUBRIK_ATERHAMTNING", "RUBRIK_AVLASNINGAR", "RUBRIK_DELSYSTEM",
           "RUBRIK_LAGE", "RUBRIK_ORSAK", "RUBRIK_STEGEN", "RUBRIK_VAGAR",
           "RUBRIK_VET_INTE", "allvarligast", "ovissheter", "rackvidden",
           "rendera"]
