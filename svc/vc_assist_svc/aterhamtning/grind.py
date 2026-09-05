# -*- coding: utf-8 -*-
"""Grinden över återhämtningsytan: dömer PARET systembild och text.

Samma val som fas 17:s `forlopp.grind`, och av samma skäl. En visning är en dom
om systemets tillstånd, ställd till den enda som inte kan kontrollera den. Vi
som bygger kan läsa loggen; användaren kan bara läsa ytan. Grinden dömer därför
TEXTEN mot de RÅA avläsningarna — inte protokollet mot sig självt — och fäller
därmed också en renderare som inte är skriven än.

Skillnaden mot fas 17 är vad som kan ljuga. Där var faran en RENDERARE eller en
LÄSARE. Här finns en tredje: en **härledning**. Ett läge är en slutsats om en
tystnad, och den som drar slutsatsen kan dra fel:

* räkna en lyckad `connect()` som ett livstecken (regel L-1),
* återanvända en avläsning som blivit gammal,
* låta en klocka som gått bakåt betyda att ingen tid gått.

Alla tre ger samma svar: ANSLUTEN om något som inte svarar. Grinden räknar
därför om varje delsystems läge SJÄLV med `bild.lage_for`, ur avläsningarna och
läsarens `nu`. En grind som frågar den den dömer mäter till slut sig själv.

## Reglerna, och den mätta incident var och en kommer ur

**Å1  Läget står först, ordagrant, och grinden räknar om det.** Ett läge som
går att läsa fel kommer att läsas fel.

**Å2  Varje delsystem står med sitt läge.** Tre saker kan sluta svara, och den
som utelämnas antas leva. I3: tystnad är aldrig ett godkännande.

**Å3  Ett stilla läge visar ingen framstegsmarkör.** Fasens egen trasiga
fixtur: *ett dött läge får aldrig se ut som ett arbetande.* Formen är mätt två
gånger — 600 av 600 (M-64) och 60 av 60 (M-93).

**Å4  Ett läge som inte svarar bär en orsak.** N-5 i
`28_lagen_och_aterhamtning.md`: panelen får aldrig säga att bryggan är nere
utan att säga varför. *"Orsaken gick inte att avgöra"* är en orsak att visa —
den falska grönen är att tiga.

**Å5  Någon annans ord når användaren tecken för tecken.** Doktrinen ur
`50_grindar.md`. En omskrivning på vägen till användaren är samma fel som en
omskrivning på vägen till modellen.

**Å6  Ett försök redovisas som pågående bara om det finns och kan lyckas.**
Operatörens egen mening: *"Ett problem uppstod, vi försöker igen"* när
ingenting försöker igen. Den är värre än tystnad, för den ber någon vänta på
något som inte händer.

**Å7  Varje väg tillbaka bär sin kanskap och sin härkomst.** Tre svar, aldrig
två. Ett okänt som skrivs som ett ja är ett löfte.

**Å8  När ingenting försöker igen står det med de orden.** Att bara låta bli
att nämna återhämtning lämnar frågan öppen, och en öppen fråga läses som ett
ja av den som hoppas.

**Å9  Trimningen säger hur mycket den dolde.** M-60:s form.

**Å10 Räckvidden står i varje visning, också en grön.** Raden `modal oppen`
finns inte i koden, Wines lyssningskö är oprövad, ingen väg är prövad på
Windows. Det blir inte mindre sant av att allt svarar just nu.

**Å11 Ett nere eller obestämt hos bryggan visar stegen.** Regel L-8:
operatören ska inte behöva öppna en loggfil för att få veta varför.

**Å12 Underläget `utan självstart` visas som tillägg.** Och då är inget
självstartsförsök pågående: en omstartsstorm är mätt till tusentals varv i
sekunden (M-13), och spärren finns för att den aldrig ska upprepas.

**Å13 Varje delsystems ålder står, räknad mot läsarens klocka.** Åldern är det
enda som skiljer ett svar från ett gammalt svar.

**Å14 Visningens egna rader går att läsa.** Högst `MAX_BREDD` tecken. Någon
annans ord bryts aldrig — bryter man dem finns de inte längre.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..forlopp.grind import Brott
from .bild import Blick, lage_for
from .lagen import (Aterhamtningsfel, BLOCKERAD, DELSYSTEM, FRANKOPPLAD,
                    KAN_NEJ, LEVANDE, NERE, OBESTAMT, OKAND, STILLA,
                    UTAN_SJALVSTART, vagarna)
from .yta import (ATERHAMTAR_MARKOR, FORSOKER_MARKOR, INGET_FORSOK,
                  MAX_AVLASNINGSRADER, MAX_BREDD, PAGAR_MARKOR, RACKVIDDEN,
                  RUBRIK_AVLASNINGAR, RUBRIK_DELSYSTEM, RUBRIK_LAGE,
                  RUBRIK_STEGEN, RUBRIK_VAGAR, RUBRIK_VET_INTE, allvarligast,
                  mojliga_och_omojliga, rendera)

REGLER = ("Å1", "Å2", "Å3", "Å4", "Å5", "Å6", "Å7", "Å8", "Å9", "Å10",
          "Å11", "Å12", "Å13", "Å14")

_AVLASNINGSRAKNING = re.compile(r"AVLÄSNINGAR: (\d+) totalt, visar (\d+)")
_DOLDA = re.compile(r"\.\.\. (\d+) till, ej visade\.")
_DELSYSTEMRAKNING = re.compile(r"DELSYSTEM: (\d+) totalt, visar (\d+)")
_VAGRAKNING = re.compile(r"VÄGAR TILLBAKA: (\d+) totalt, visar (\d+)")


@dataclass
class Aterhamtningsdom:
    brott: List[Brott] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.brott

    @property
    def brutna(self) -> Tuple[str, ...]:
        ut: List[str] = []
        for b in self.brott:
            if b.regel not in ut:
                ut.append(b.regel)
        return tuple(ut)

    def text(self) -> str:
        if self.ok:
            return "ÅTERHÄMTNINGSYTAN GODKÄND: %d regler prövade" % len(REGLER)
        rader = ["ÅTERHÄMTNINGSYTAN FÄLLD: %d brott mot %d regler"
                 % (len(self.brott), len(self.brutna))]
        rader.extend("  " + b.rad() for b in self.brott)
        return "\n".join(rader)


def frammande(blick: Blick) -> Tuple[str, ...]:
    """Varje sträng som MÅSTE nå användaren oförvanskad.

    Sondens egna felord för de delsystem som inte svarar, och varje försöks
    egna utfallsord. Vår egen prosa står inte här: den får brytas och ramas in.
    """
    ut: List[str] = []
    for d in DELSYSTEM:
        if lage_for(blick.bild, d, blick.nu) in LEVANDE:
            continue
        sista = blick.bild.sista(d)
        if sista is not None and sista.fel and sista.fel not in ut:
            ut.append(sista.fel)
    for f in blick.bild.forsoken:
        if f.ordagrant and f.ordagrant not in ut:
            ut.append(f.ordagrant)
    return tuple(ut)


def _utan_frammande(blick: Blick, text: str) -> str:
    ut = text
    for ord_ in frammande(blick):
        ut = ut.replace(ord_, "")
    return ut


_MELLANRUM = re.compile(r"\s+")


def _finns(text: str, fras: str) -> bool:
    """Står vår EGEN mening i texten, oavsett var raderna bröts?

    Skillnaden mot Å5 är avsiktlig och viktig. Någon annans ord prövas tecken
    för tecken i den råa texten: bryter man dem finns de inte längre, och då
    går det inte att visa att de kom fram hela. Vår egen prosa får däremot
    brytas — en yta som inte får radbrytas är en yta som inte går att läsa —
    och prövas därför med mellanrummen hopslagna.
    """
    return _MELLANRUM.sub(" ", fras).strip() in _MELLANRUM.sub(" ", text)


def granska(blick: Blick, text: Optional[str] = None,
            loggar=None) -> Aterhamtningsdom:
    """Dömer texten mot de råa avläsningarna. `text=None` renderar själv."""
    if text is None:
        text = rendera(blick, loggar)
    if not isinstance(text, str):
        raise Aterhamtningsfel("en återhämtningsyta är text; renderaren "
                               "lämnade %s" % type(text).__name__)
    brott: List[Brott] = []
    rader = text.splitlines()
    forsta = next((r.strip() for r in rader if r.strip()), "")

    if blick.obestamd:
        return _granska_obestamd(blick, text, forsta)

    # Grinden räknar om VARJE läge själv. Det är hela skillnaden mot att fråga
    # den som visar: en härledning som fryser klockan eller räknar en lyckad
    # anslutning som liv svarar glatt att allt är i sin ordning.
    lagen = dict((d, lage_for(blick.bild, d, blick.nu)) for d in DELSYSTEM)
    huvud = allvarligast(blick)
    egna = _utan_frammande(blick, text)

    # Å1 -- läget står först, ordagrant
    vantad = "%s %s %s" % (RUBRIK_LAGE, huvud, lagen[huvud])
    if forsta != vantad:
        brott.append(Brott("Å1", "första raden är %r, avläsningarna säger %r"
                           % (forsta, vantad)))

    # Å2 -- varje delsystem står med sitt läge
    for d in DELSYSTEM:
        if not any(d in r and lagen[d] in r for r in rader):
            brott.append(Brott(
                "Å2", "delsystemet %s står inte i visningen med sitt läge "
                      "%s; det som utelämnas antas leva" % (d, lagen[d])))
    if RUBRIK_DELSYSTEM not in text:
        brott.append(Brott("Å2", "visningen saknar avsnittet %r"
                           % RUBRIK_DELSYSTEM))

    # Å3 -- ett stilla läge visar ingen framstegsmarkör
    if lagen[huvud] in STILLA and PAGAR_MARKOR in egna:
        brott.append(Brott(
            "Å3", "läget är %s men visningen skriver %r; ett dött läge får "
                  "aldrig se ut som ett arbetande"
                  % (lagen[huvud], PAGAR_MARKOR)))

    # Å4 -- ett läge som inte svarar bär en orsak
    for d in DELSYSTEM:
        if lagen[d] in LEVANDE:
            continue
        sista = blick.bild.sista(d)
        if sista is None:
            if not _finns(text, "ingen avläsning gjord"):
                brott.append(Brott(
                    "Å4", "%s har aldrig avlästs och visningen säger det "
                          "inte" % d))
            continue
        orsak = blick.bild.orsak(d)
        vantat = OKAND.text if orsak is None else orsak.text
        if not _finns(text, vantat):
            brott.append(Brott(
                "Å4", "%s är %s utan att visningen säger varför. Orsaken som "
                      "saknas: %r" % (d, lagen[d], vantat[:70])))

    # Å5 -- någon annans ord, tecken för tecken
    for ord_ in frammande(blick):
        if ord_ not in text:
            brott.append(Brott(
                "Å5", "någon annans ord nådde inte användaren ordagrant: %r. "
                      "En omskrivning på vägen ut mäter till slut sig själv "
                      "(50_grindar.md)" % (ord_[:80],)))

    # Å6 -- ett försök redovisas som pågående bara om det kan lyckas
    #
    # Kanskapen räknas om HÄR, med tabellen i lagen.py, i stället för att läsas
    # ur försöket. Skälet är att det är just den frusna kanskapen som kan ha
    # blivit fel: bryggan kan ha slagit av sin självstart efter att försöket
    # började.
    mojliga, omojliga = mojliga_och_omojliga(blick)
    # `INGET_FORSOK` innehåller själv frasen `FORSOKER_MARKOR` — den är en
    # NEKANDE mening om precis den saken. Den plockas därför bort innan
    # markören söks; annars fäller regeln varje ärlig visning och släpper
    # igenom noll, vilket är en grind som mäter sin egen formulering.
    utan_nekandet = _MELLANRUM.sub(" ", egna).replace(
        _MELLANRUM.sub(" ", INGET_FORSOK), "")
    lovar = (FORSOKER_MARKOR in utan_nekandet
             or ATERHAMTAR_MARKOR in utan_nekandet)
    if lovar and not mojliga:
        brott.append(Brott(
            "Å6", "visningen skriver %r men inget försök som kan lyckas står "
                  "i protokollet; att be någon vänta på ingenting är värre än "
                  "tystnad" % FORSOKER_MARKOR))
    for f, nu_kan in omojliga:
        if not _finns(text, KAN_NEJ):
            brott.append(Brott(
                "Å6", "försöket \"%s\" kan inte lyckas (%s) och visningen "
                      "säger det inte" % (f.vag.text[:50], nu_kan)))

    # Å7 -- varje väg bär sin kanskap och sin härkomst
    orsak = blick.bild.orsak(huvud)
    if orsak is not None and lagen[huvud] not in LEVANDE:
        for vag, kan in vagarna(orsak, blick.bild.utan_sjalvstart):
            if not _finns(text, vag.text):
                brott.append(Brott("Å7", "vägen tillbaka %r saknas i "
                                         "visningen" % vag.text[:60]))
            elif not _finns(text, kan):
                brott.append(Brott(
                    "Å7", "vägen %r står utan sin kanskap %r; en väg utan "
                          "kanskap är ett löfte" % (vag.text[:40], kan)))
            elif not _finns(text, vag.stampel):
                brott.append(Brott(
                    "Å7", "vägen %r står utan sin härkomst %r"
                          % (vag.text[:40], vag.stampel)))

    # Å8 -- när ingenting försöker igen står det med de orden
    if not mojliga and not _finns(text, INGET_FORSOK):
        brott.append(Brott(
            "Å8", "inget försök pågår, och visningen säger inte %r. En öppen "
                  "fråga läses som ett ja av den som hoppas" % INGET_FORSOK))

    # Å9 -- trimningen säger hur mycket den dolde
    brott.extend(_granska_rakningar(blick, text, huvud, lagen))

    # Å10 -- räckvidden står i varje visning
    if RUBRIK_VET_INTE not in text:
        brott.append(Brott("Å10", "visningen saknar avsnittet %r"
                           % RUBRIK_VET_INTE))
    else:
        saknade = [namn for _n, namn, _s in RACKVIDDEN if namn not in text]
        if saknade:
            brott.append(Brott(
                "Å10", "räckviddens poster saknas: %s. De blir inte mindre "
                       "sanna av att allt svarar just nu"
                       % ", ".join(saknade)))

    # Å11 -- ett nere eller obestämt hos bryggan visar stegen
    if lagen["bryggan"] in (NERE, OBESTAMT, FRANKOPPLAD, BLOCKERAD) \
            and RUBRIK_STEGEN not in text:
        brott.append(Brott(
            "Å11", "bryggan är %s och visningen kör inte stegen som hittar "
                   "orsaken (regel L-8)" % lagen["bryggan"]))

    # Å12 -- underläget visas som tillägg
    if blick.bild.utan_sjalvstart:
        if not _finns(text, UTAN_SJALVSTART):
            brott.append(Brott(
                "Å12", "bryggan har slagit av sin egen självstart och "
                       "visningen säger det inte"))
        for f, _kan in mojliga:
            if f.vag.nyckel == "sjalvstart":
                brott.append(Brott(
                    "Å12", "ett självstartsförsök redovisas som pågående "
                           "medan självstarten är avslagen"))

    # Å13 -- varje delsystems ålder står
    for d in DELSYSTEM:
        alder = blick.alder(d)
        if alder is None:
            if not _finns(text, "ingen avläsning gjord"):
                brott.append(Brott("Å13", "%s har ingen avläsning och "
                                          "visningen säger det inte" % d))
        elif ("%.1f s" % abs(alder)) not in text:
            brott.append(Brott(
                "Å13", "%s:s avläsning är %.1f s gammal och talet står inte i "
                       "visningen; åldern är det enda som skiljer ett svar "
                       "från ett gammalt svar" % (d, alder)))

    # Å14 -- visningens egna rader går att läsa
    brott.extend(_granska_bredd(blick, text))
    return Aterhamtningsdom(brott)


def _granska_rakningar(blick: Blick, text: str, huvud: str,
                       lagen) -> List[Brott]:
    brott: List[Brott] = []
    m = _AVLASNINGSRAKNING.search(text)
    alla = blick.bild.avlasningar
    if m is None:
        brott.append(Brott("Å9", "visningen säger inte hur många avläsningar "
                                 "den inte visade (M-60:s form)"))
    else:
        totalt, visade = int(m.group(1)), int(m.group(2))
        if totalt != len(alla):
            brott.append(Brott("Å9", "visningen säger %d avläsningar, bilden "
                                     "bär %d" % (totalt, len(alla))))
        dolda = totalt - visade
        d = _DOLDA.search(text)
        if dolda and (d is None or int(d.group(1)) != dolda):
            brott.append(Brott("Å9", "%d avläsningar doldes utan att "
                                     "visningen sa det" % dolda))
    d = _DELSYSTEMRAKNING.search(text)
    if d is None or int(d.group(1)) != len(DELSYSTEM):
        brott.append(Brott("Å9", "visningen räknar inte delsystemen till %d"
                           % len(DELSYSTEM)))
    orsak = blick.bild.orsak(huvud)
    if orsak is not None and lagen[huvud] not in LEVANDE:
        v = _VAGRAKNING.search(text)
        vantat = len(orsak.vagar)
        if v is None or int(v.group(1)) != vantat:
            brott.append(Brott(
                "Å9", "visningen räknar inte vägarna tillbaka till %d"
                      % vantat))
    return brott


def _granska_bredd(blick: Blick, text: str) -> List[Brott]:
    fritagna = set()
    for ord_ in frammande(blick):
        for rad in ord_.splitlines():
            fritagna.add(rad.strip())
    brott: List[Brott] = []
    for i, rad in enumerate(text.splitlines(), 1):
        if len(rad) <= MAX_BREDD:
            continue
        if rad.strip() in fritagna or any(f and f in rad for f in fritagna):
            continue
        brott.append(Brott(
            "Å14", "rad %d är %d tecken; visningens egna rader ska rymmas i "
                   "%d. En rad som inte får plats läses inte"
                   % (i, len(rad), MAX_BREDD)))
    return brott


def _granska_obestamd(blick: Blick, text: str,
                      forsta: str) -> Aterhamtningsdom:
    """En systembild som inte gick att läsa. Formen är M-93:s S1.

    Ett läsfel som ser ut som en lugn början är den falska grönen i sin
    renaste form, och därför prövas den obestämda visningen mot samma krav:
    läget först, felet ordagrant, räckvidden kvar.
    """
    brott: List[Brott] = []
    if forsta != "%s systembilden %s" % (RUBRIK_LAGE, OBESTAMT):
        brott.append(Brott(
            "Å1", "systembilden gick inte att läsa men första raden är %r; "
                  "ett läsfel som ser lugnt ut är en falsk grön" % (forsta,)))
    if blick.fel and blick.fel not in text:
        brott.append(Brott("Å5", "läsfelet nådde inte användaren ordagrant: "
                                 "%r" % (blick.fel[:80],)))
    if not _finns(text, INGET_FORSOK):
        brott.append(Brott("Å8", "en obestämd bild säger inte att ingenting "
                                 "försöker igen"))
    if RUBRIK_VET_INTE not in text:
        brott.append(Brott("Å10", "en obestämd bild saknar avsnittet %r; "
                                  "räckvidden gäller också ett system ingen "
                                  "kan läsa" % RUBRIK_VET_INTE))
    else:
        saknade = [namn for _n, namn, _s in RACKVIDDEN if namn not in text]
        if saknade:
            brott.append(Brott("Å10", "räckviddens poster saknas i den "
                                      "obestämda visningen: %s"
                               % ", ".join(saknade)))
    for d in DELSYSTEM:
        if not any(d in r and OBESTAMT in r for r in text.splitlines()):
            brott.append(Brott("Å2", "delsystemet %s står inte som %s i den "
                                     "obestämda visningen" % (d, OBESTAMT)))
    brott.extend(_granska_bredd(blick, text))
    return Aterhamtningsdom(brott)


def granska_eller_kasta(blick: Blick, text: Optional[str] = None,
                        loggar=None) -> str:
    """Som `granska`, men kastar. Använd i en väg som INTE får leverera."""
    if text is None:
        text = rendera(blick, loggar)
    dom = granska(blick, text, loggar)
    if not dom.ok:
        raise Aterhamtningsfel(dom.text())
    return text


__all__ = ["Aterhamtningsdom", "Brott", "REGLER", "frammande", "granska",
           "granska_eller_kasta"]
