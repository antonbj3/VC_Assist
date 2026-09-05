# -*- coding: utf-8 -*-
"""Speglingen: förloppet ut ur processen, och tillbaka in hos den som väntar.

`M-64` byggde ytan och lämnade ett hål med flit, och hålet står ordagrant i
mätningens §9: *"Ingenting driver ytan än ... Ska en panel i en annan process
läsa den behövs en serialisering som inte finns."* Så länge det är sant är
"panelen" och "körningen" samma process, och en yta som bara den som redan kör
koden kan läsa är exakt den logg fasen finns för att ersätta.

Den här modulen är den serialiseringen, och den bär EN mätt fara.

## Faran: en bild som inte åldras är en död körning som ser levande ut

Ögonblicksbilden bär skrivarens tidsstämplar. Läses de tillbaka med skrivarens
egen klocka — det vill säga med bildens `skrivet` som "nu" — blir tystnaden
noll i varje avläsning, och läget står på ARBETAR för alltid. Skrivaren kan ha
dött för en timme sedan. Det är samma odödliga körning `M-64` mätte på
hjärtslaget (600 av 600 avläsningar sa ARBETAR), och det är en ANNAN mekanism:
den första nollade klockan med en puls, den här nollar den med ett filfält.

Därför:

* `Forlopp.fran_json` tar LÄSARENS klocka. Åldern räknas mot den som läser.
* Bilden bär `skrivet`, och läsaren mäter filens egen ålder ur den.
* `granska_spegling` räknar om åldern SJÄLV, ur den råa bilden, precis som
  `granska` räknar om tystnaden själv i regel Y9. En grind som frågar den den
  dömer mäter till slut sig själv.

## Tre lägen som inte fanns i processen

En körning inne i en process är antingen igång eller slut. En körning läst ur
en fil har tre lägen till, och alla tre är "vet inte", aldrig "det är lugnt":

1. **filen gick inte att läsa** — avhuggen, halvskriven, fel version.
2. **filen står still och körningen är inte avslutad** — skrivaren kan leva
   eller vara död, och skillnaden syns inte i filen.
3. **filen är skriven i framtiden** — klockorna är osams, och åldern går inte
   att räkna alls.

Alla tre blir `OBESTÄMT` eller en uttalad ovisshet i visningen. Inget av dem
blir EJ STARTAT, och det är hela poängen: ett läsfel som ser ut som en lugn
början är den falska grönen i sin renaste form.

## Skrivningen är atomisk, och den sker EFTER VARJE HÄNDELSE

`os.replace` över en fil i samma katalog. En läsare ser antingen den gamla
bilden eller den nya, aldrig en halv — och en halv bild hade blivit en
`Forloppsfel` i läsaren i vilket fall, alltså ett obestämt läge i stället för
ett falskt.

Att skriva efter varje händelse och inte på en klocka är ett beslut: en yta
som uppdateras av en timer visar ett tillstånd som inte hör till någon
händelse, och en yta som skrivs när körningen är slut är den terminala
rapportyta `M-64` räknade sju av.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from typing import List, Optional

from .grind import Brott, granska
from .handelser import (ARBETAR, AVBRUTET, EJ_PROVAT, FALLET, Forloppsfel,
                        KLART, OBESTAMT, RACKVIDDEN)
from .yta import (FORLOPPSVERSION, Forlopp, RUBRIK_VET_INTE, SAKNAS,
                  TYSTNADSTAK_S, rendera)

# Rubriken på blocket som säger var bilden kommer ifrån och hur gammal den är.
# En visning av en INSPELAD körning som inte säger när den spelades in ser ut
# som en visning av nuet.
RUBRIK_SPEGLING = "SPEGLING:"

# Meningarna grinden letar efter i en FRÄMMANDE renderares text. De står som
# konstanter av samma skäl som `PAGAR_MARKOR`: en grind som letar efter en
# formulering den hittat på i farten mäter sin egen fantasi.
STILLASTAENDE = "filen har inte uppdaterats"
FRAMTID = "filen är skriven i framtiden"
OLASBAR = "gick inte att läsa"

# Lägen som betyder att körningen är SLUT. En fil som står still är helt i sin
# ordning då: det finns inget mer att skriva.
AVSLUTADE = (KLART, FALLET, AVBRUTET)

REGLER = ("S1", "S2", "S3", "S4", "S5")


# ------------------------------------------------------------------ skriva

class Spegel(object):
    """Skriver förloppet till en fil, atomiskt, efter varje händelse."""

    def __init__(self, sokvag: str):
        self.sokvag = str(sokvag)
        self.skrivningar = 0

    def __repr__(self):
        return "Spegel(%s, %d skrivningar)" % (self.sokvag, self.skrivningar)

    def skriv(self, f: Forlopp) -> None:
        katalog = os.path.dirname(os.path.abspath(self.sokvag)) or "."
        text = json.dumps(f.till_json(), ensure_ascii=False, sort_keys=True)
        fd, tmp = tempfile.mkstemp(dir=katalog, prefix=".forlopp-",
                                   suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, self.sokvag)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        self.skrivningar += 1


def spegla(f: Forlopp, sokvag: str) -> Spegel:
    """Koppla en spegel till ett förlopp och skriv den första bilden direkt.

    Den första skrivningen sker med flit innan något hänt: en panel som startas
    före körningen ska hitta en fil som säger EJ STARTAT, inte en fil som inte
    finns. Skillnaden mellan "har inte börjat" och "hittar ingenting" är just
    den skillnad en användare inte kan gissa sig till.
    """
    s = Spegel(sokvag)
    f.spegla(s)
    return s


# -------------------------------------------------------------------- läsa

@dataclass(frozen=True)
class Ogonblick:
    """En spegling som den ser ut för den som läser den, just nu."""

    sokvag: str
    nu: float
    forlopp: Optional[Forlopp] = None
    skrivet: Optional[float] = None
    fel: str = ""

    @property
    def obestamd(self) -> bool:
        return self.forlopp is None

    @property
    def alder(self) -> Optional[float]:
        """Filens ålder mot LÄSARENS klocka. Negativ = skriven i framtiden."""
        if self.skrivet is None:
            return None
        return self.nu - self.skrivet

    @property
    def lage(self) -> str:
        if self.forlopp is None:
            return OBESTAMT
        return self.forlopp.lage

    @property
    def avslutad(self) -> bool:
        return self.lage in AVSLUTADE

    @property
    def tystnadstak(self) -> float:
        if self.forlopp is None:
            return TYSTNADSTAK_S
        return self.forlopp.tystnadstak


def las_spegling(sokvag: str, klocka=time.time) -> Ogonblick:
    """Läser en spegling. Ett fel blir ett OBESTÄMT läge, aldrig ett tomt.

    Funktionen kastar inte på en trasig fil: den som väntar ska få se att
    systemet inte kan svara, inte ett stacktrace. Den kastar däremot inte
    heller bort felet — det går ordagrant ut i visningen.
    """
    nu = klocka()
    try:
        with open(sokvag, encoding="utf-8") as fh:
            ra = fh.read()
    except OSError as fel:
        return Ogonblick(sokvag=sokvag, nu=nu,
                         fel="%s: %s" % (type(fel).__name__, fel))
    try:
        data = json.loads(ra)
    except ValueError as fel:
        return Ogonblick(
            sokvag=sokvag, nu=nu,
            fel="filen är inte en hel ögonblicksbild (%s: %s); den kan vara "
                "avhuggen mitt i en skrivning" % (type(fel).__name__, fel))
    try:
        # EN avlasning ar ETT ogonblick. Klockan fryses vid LASARENS `nu` -
        # aldrig vid filens `skrivet`, som ar precis den bugg S2 finns for.
        #
        # Skillnaden ar hela poangen: `nu` hamtas pa nytt vid varje avlasning,
        # sa bilden aldras. Vad frysningen ger ar att renderaren och grinden
        # ser SAMMA tillstand. Utan den kan tystnaden passera taket mellan
        # `rendera_spegling` och `granska_spegling`, och da far anvandaren en
        # grindanmarkning pa en yta som var korrekt nar den skrevs. Det ar
        # samma regel som `test_visningen_raknar_sitt_lage_exakt_en_gang`
        # redan haller inne i processen, en vaning upp.
        f = Forlopp.fran_json(data, klocka=lambda: nu)
    except Forloppsfel as fel:
        return Ogonblick(sokvag=sokvag, nu=nu, fel=str(fel))

    o = Ogonblick(sokvag=sokvag, nu=nu, forlopp=f, skrivet=f.skrivet)
    _lagg_speglingens_ovissheter(o)
    return o


def _lagg_speglingens_ovissheter(o: Ogonblick) -> None:
    """De tre ovissheter som bara finns när förloppet lämnat processen.

    De läggs av LÄSAREN och inte av skrivaren, och det är avsiktligt: en
    skrivare som är död kan inte skriva att den är död.
    """
    f = o.forlopp
    alder = o.alder
    if alder is None:
        return
    if alder < 0.0:
        f.vet_inte(
            "läsarens klocka",
            "%s: %.1f s framför den här klockan. Åldern går inte att räkna, "
            "och läget är därför obestämt" % (FRAMTID, -alder), EJ_PROVAT)
        return
    if not o.avslutad and alder > f.tystnadstak:
        f.vet_inte(
            "skrivarens liv",
            "%s på %.1f s och körningen är inte avslutad; om den lever eller "
            "dog syns inte i filen" % (STILLASTAENDE, alder), EJ_PROVAT)


# --------------------------------------------------------------- rendera

def _tid(t: Optional[float]) -> str:
    if t is None:
        return SAKNAS
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def _speglingsrader(o: Ogonblick) -> List[str]:
    rader = [RUBRIK_SPEGLING,
             "  fil       %s" % o.sokvag,
             "  skriven   %s" % _tid(o.skrivet),
             "  läst      %s" % _tid(o.nu)]
    alder = o.alder
    if alder is None:
        rader.append("  ålder     %s — bilden bär ingen skrivtid" % SAKNAS)
    elif alder < 0.0:
        rader.append("  ålder     %s, %.1f s framför läsarens klocka"
                     % (FRAMTID, -alder))
    else:
        rader.append("  ålder     %.1f s" % alder)
        if not o.avslutad and alder > o.tystnadstak:
            rader.append("  %s på %.1f s och körningen är inte avslutad."
                         % (STILLASTAENDE, alder))
            rader.append("  Om skrivaren lever eller dog syns inte i filen.")
    return rader


def _rendera_obestamd(o: Ogonblick) -> str:
    """Ytan för en spegling som inte gick att läsa.

    Formen är densamma som `rendera`: läget först, någon annans ord ordagrant,
    och ett avsnitt om vad som inte går att veta. Räckvidden står kvar — den
    gäller varje körning och blir inte mindre sann av att filen är trasig.
    """
    rader = ["LÄGE: %s" % OBESTAMT,
             "spegling %s: %s" % (o.sokvag, OLASBAR),
             "tid: läst %s" % _tid(o.nu),
             "skäl, ordagrant:",
             o.fel,
             "",
             "STEG: okänt — filen bär inga steg som går att lita på",
             "",
             "GRINDAR: %s — filen gick inte att läsa" % SAKNAS,
             "",
             "ÖGATS DOM (grind 5): %s — filen gick inte att läsa." % SAKNAS,
             "  En körning utan ögondom är kandidat, aldrig guld.",
             "GULDBESLUT: %s — filen gick inte att läsa" % SAKNAS,
             "",
             "HÄNDELSER: 0 totalt, visar 0",
             ""]
    rader.append("%s %d poster" % (RUBRIK_VET_INTE, len(RACKVIDDEN) + 1))
    rader.append("  utanför räckvidd (50_grindar.md). Ögats eget namn i "
                 "mitten:")
    for nyckel, namn, skal in RACKVIDDEN:
        rader.append("    %-18s %-19s %s" % (namn, nyckel, skal))
    rader.append("  ej prövat i den här körningen:")
    rader.append("    hela körningen           speglingen %s, så ingenting i "
                 "den går att svara på" % OLASBAR)
    rader.append("")
    rader.extend(_speglingsrader(o))
    return "\n".join(rader)


def rendera_spegling(o: Ogonblick) -> str:
    """Speglingen som text: förloppsytan plus var bilden kommer ifrån."""
    if o.obestamd:
        return _rendera_obestamd(o)
    return rendera(o.forlopp) + "\n\n" + "\n".join(_speglingsrader(o))


# ---------------------------------------------------------------- grinden

@dataclass
class Speglingsdom:
    brott: List[Brott]

    @property
    def ok(self) -> bool:
        return not self.brott

    @property
    def brutna(self):
        ut = []
        for b in self.brott:
            if b.regel not in ut:
                ut.append(b.regel)
        return tuple(ut)

    def text(self) -> str:
        if self.ok:
            return ("SPEGLINGEN GODKÄND: %d egna regler plus förloppsytans"
                    % len(REGLER))
        rader = ["SPEGLINGEN FÄLLD: %d brott mot %d regler"
                 % (len(self.brott), len(self.brutna))]
        rader.extend("  " + b.rad() for b in self.brott)
        return "\n".join(rader)


def _forsta_raden(text: str) -> str:
    return next((r.strip() for r in text.splitlines() if r.strip()), "")


def granska_spegling(o: Ogonblick, text: Optional[str] = None) -> Speglingsdom:
    """Dömer texten mot den RÅA bilden, inte mot det förlopp den byggde.

    Det är hela skillnaden mot `granska`. Förloppsytans elva regler dömer
    texten mot protokollet, och de fäller varje renderare som ljuger. De kan
    däremot inte fälla en LÄSARE som ljuger: en läsare som fryser klockan
    bygger ett protokoll som SJÄLVT säger ARBETAR, och då är texten korrekt
    mot ett protokoll som är fel.

    De fem reglerna nedan räknar därför om åldern ur `skrivet` och läsarens
    klocka, och de läser läget ur TEXTEN i stället för att fråga förloppet.
    """
    if text is None:
        text = rendera_spegling(o)
    if not isinstance(text, str):
        raise Forloppsfel("a mirrored snapshot is text; the renderer returned %s"
                          % type(text).__name__)
    brott: List[Brott] = []
    forsta = _forsta_raden(text)
    alder = o.alder

    # S1 -- en spegling som inte gick att läsa är OBESTÄMD, med felet ordagrant
    if o.obestamd:
        if forsta != "LÄGE: %s" % OBESTAMT:
            brott.append(Brott(
                "S1", "speglingen gick inte att läsa men första raden är %r; "
                      "ett läsfel som ser lugnt ut är en falsk grön"
                      % (forsta,)))
        if o.fel and o.fel not in text:
            brott.append(Brott(
                "S1", "läsfelet nådde inte användaren ordagrant: %r"
                      % (o.fel[:80],)))
        if RUBRIK_VET_INTE not in text:
            brott.append(Brott(
                "S1", "en obestämd spegling saknar avsnittet %r; räckvidden "
                      "gäller också en körning ingen kan läsa"
                      % RUBRIK_VET_INTE))
        saknade = [namn for _n, namn, _s in RACKVIDDEN if namn not in text]
        if saknade:
            brott.append(Brott(
                "S1", "räckviddens poster saknas i den obestämda visningen: %s"
                      % ", ".join(saknade)))

    # S2 -- ett arbetande läge kräver en FÄRSK fil
    #
    # Åldern räknas här, ur bildens `skrivet` och läsarens klocka. Frågar man
    # förloppet svarar en läsare som frusit klockan att allt är i sin ordning.
    if forsta == "LÄGE: %s" % ARBETAR and alder is not None \
            and alder > o.tystnadstak:
        brott.append(Brott(
            "S2", "visningen säger ARBETAR men filen skrevs för %.1f s sedan "
                  "(taket är %.1f s). En bild som inte åldras är en död "
                  "körning som ser levande ut" % (alder, o.tystnadstak)))

    # S3 -- speglingen säger var den kommer ifrån och hur gammal den är
    if RUBRIK_SPEGLING not in text:
        brott.append(Brott(
            "S3", "visningen saknar %r; en inspelad körning som inte säger "
                  "när den spelades in ser ut som nuet" % RUBRIK_SPEGLING))
    elif o.sokvag not in text:
        brott.append(Brott("S3", "visningen säger inte vilken fil den läste"))

    # S4 -- en pågående körning vars fil står still säger att vi inte vet
    if (not o.obestamd and not o.avslutad and alder is not None
            and alder > o.tystnadstak and STILLASTAENDE not in text):
        brott.append(Brott(
            "S4", "filen står still sedan %.1f s och körningen är inte "
                  "avslutad, men visningen säger inte att systemet inte vet "
                  "om skrivaren lever" % alder))

    # S5 -- en fil skriven i framtiden är obestämd, aldrig arbetande
    if alder is not None and alder < 0.0:
        if forsta == "LÄGE: %s" % ARBETAR:
            brott.append(Brott(
                "S5", "filen är skriven %.1f s i framtiden och visningen "
                      "säger ändå ARBETAR; en klocka som gått bakåt gör varje "
                      "död körning evig" % (-alder,)))
        if FRAMTID not in text:
            brott.append(Brott(
                "S5", "filen är skriven i framtiden och visningen säger det "
                      "inte"))

    # Förloppsytans egna elva regler gäller oförändrat när bilden gick att
    # läsa. Speglingen lägger till en yta, den ersätter ingen.
    if not o.obestamd:
        brott.extend(granska(o.forlopp, text).brott)
    return Speglingsdom(brott)


def granska_spegling_eller_kasta(o: Ogonblick,
                                 text: Optional[str] = None) -> str:
    if text is None:
        text = rendera_spegling(o)
    dom = granska_spegling(o, text)
    if not dom.ok:
        raise Forloppsfel(dom.text())
    return text


__all__ = ["AVSLUTADE", "FRAMTID", "FORLOPPSVERSION", "OLASBAR", "Ogonblick",
           "REGLER", "RUBRIK_SPEGLING", "STILLASTAENDE", "Spegel",
           "Speglingsdom", "granska_spegling", "granska_spegling_eller_kasta",
           "las_spegling", "rendera_spegling", "spegla"]
