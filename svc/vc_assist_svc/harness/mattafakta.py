# -*- coding: utf-8 -*-
"""MATTA FAKTA: forslag som vilar pa nagot som INTE FINNS i VC 4.10.

Domankunskapen om VC var noll av sju mekaniserad efter M-46, och skalet som
gavs var att det ar kunskap och inte beteende. Det stammer for det mesta av
blocket, men inte for allt: TVA av reglerna handlar om vagar som ar MATTA
till att inte finnas, och en modell som kanner andra simuleringsverktyg
foreslar dem i sin forsta mening.

  DOM-006  USD finns inte i VC, varken lasare eller skrivare, och FBX finns
           bara som EXPORT. Matt genom strangsokning i samtliga binarer
           (docs/spec/10_matta_fakta.md).
  DOM-005  VC ar alltid OPC UA-KLIENT, aldrig server. Matt i
           Connectivity.OpcUA.xml: IOpcUAServer beskrivs som "a server
           connection", alltsa en anslutning TILL en server. Det utesluter
           OpenPLC v3 och varje klient-till-klient-uppsattning.

En sadan vag ar inte fel i grad utan i art: den gar inte att gora. Ett
forslag som bygger pa den kostar operatoren en hel runda av forsok innan
felet visar sig, och felet visar sig da som "det gar inte att oppna filen"
och inte som "produkten har ingen USD-lasare".

RIKTNINGEN, och varfor grinden inte anklagar den som HAR ratt. Tre saker
kravs i SAMMA mening: ett namn ur den matta listan, ett verb som gor det till
en vag framat, och att meningen inte nekar sitt eget forslag. Meningen "VC har ingen USD-lasare,
sa den vagen finns inte" bar bade namnet och ett nekande ord, och gar fri.
Meningen "vi kan importera USD-filen direkt" bar namnet och verbet och inget
nekande, och faller. Samma monster som sakerhet.granska_text, av samma skal:
ett ord ensamt ar inte ett forslag.

Meningsklassningen anvands INTE har. En vag foreslas nastan alltid i
framtidsform ("vi kan importera", "nasta steg ar att exportera"), och
text.ar_pastaende raknar just den formen som en plan och skulle slappa den.
Det ar ratt for verify-contract, som provar pastaenden om varlden, och fel
har: det ar forslaget som ar felet.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from .text import bar_delstrang, bar_ord, meningar, nekar_pastaendet

GRIND = "matta_fakta"

# Verb som gor en mening till ett forslag om en VAG IN i VC.
INVERB = ("importer", "ladda", "laddar", "lasa in", "läsa in", "laser in",
          "läser in", "oppna", "öppna", "oppnar", "öppnar", "konverter",
          "import", "load", "read ", "open ", "bring in", "convert")

# Verb som gor den till en vag UT ur VC.
UTVERB = ("exporter", "spara som", "spara till", "export", "save as",
          "write out")

# Verb som gor en mening till ett forslag om att SATTA UPP nagot.
# "serve" star INTE med, och det ar matt: listan matchas som delstrang, och
# "server" bar "serve". Med ordet i listan fallde grinden meningen "PLC:n ar
# OPC UA-server och VC ansluter som klient", alltsa exakt den riktiga
# uppsattningen. Ett verb som ar en delstrang av sitt eget substantiv kan
# inte skilja forslaget fran beskrivningen.
UPPSATTNINGSVERB = ("satt upp", "sätt upp", "satta upp", "sätta upp",
                    "konfigurer", "starta", "startar", "kor som", "kör som",
                    "agera", "agerar", "fungera som", "fungerar som",
                    "expon", "publicer", "set up", "configure", "run as",
                    "act as", "host ", "expose")


@dataclass(frozen=True)
class Fakta:
    """En matt icke-existens, och vad som gor en mening till ett forslag."""

    id: str            # instruktionsregeln den mekaniserar
    ord: Tuple[str, ...]
    verb: Tuple[str, ...]
    kravda_ord: Tuple[str, ...]   # ord som OCKSA maste sta i meningen
    skal: str


FAKTA = (
    Fakta(
        id="DOM-006",
        ord=("usd", "usda", "usdc", "usdz", "openusd", "universal scene "
             "description"),
        verb=INVERB + UTVERB,
        kravda_ord=(),
        skal=("USD finns inte i VC 4.10, varken som lasare eller som "
              "skrivare. MATT genom strangsokning i samtliga binarer "
              "(docs/spec/10_matta_fakta.md). En vag som bygger pa USD gar "
              "inte att gora, oavsett riktning (DOM-006)")),
    Fakta(
        id="DOM-006",
        ord=("fbx",),
        verb=INVERB,
        kravda_ord=(),
        skal=("FBX finns i VC 4.10 bara som EXPORT. MATT i "
              "docs/spec/10_matta_fakta.md: det finns ingen lasare. Att "
              "exportera FBX gar; att lasa in det gor det inte (DOM-006)")),
    Fakta(
        id="DOM-005",
        ord=("opc ua", "opcua", "opc-ua"),
        verb=UPPSATTNINGSVERB,
        kravda_ord=("server",),
        skal=("VC ar alltid OPC UA-KLIENT, aldrig server. MATT i "
              "Connectivity.OpcUA.xml: IOpcUAServer beskrivs som 'a server "
              "connection', alltsa en anslutning TILL en server. PLC:n maste "
              "vara servern, och det utesluter OpenPLC v3 (DOM-005)")),
)

# Meningen maste ocksa handla om VC for att OPC UA-regeln ska falla: "PLC:n
# ar OPC UA-server" ar precis den riktiga uppsattningen.
VC_ORD = ("vc", "visual components", "simuleringen", "scenen")


@dataclass(frozen=True)
class Anmarkning:
    regel: str
    skal: str
    mening: str

    def text(self) -> str:
        return "%s (i meningen: %r)" % (self.skal, self.mening)


def granska(text: str) -> Tuple[Anmarkning, ...]:
    """Meningarna som foreslar en vag som ar matt till att inte finnas."""
    ut: List[Anmarkning] = []
    for mening in meningar(text or ""):
        lag = mening.lag
        if nekar_pastaendet(lag):
            # Meningen sager att nagot INTE gar. Den ar precis vad regeln
            # vill se, och far aldrig anklagas.
            #
            # SKARPT AV M-95, samma felklass som M-94 fynd 1 och 4: fragan
            # var "bar meningen nagot nekande ord", och forbehallet "utan"
            # rakades da som ett nekande. MATT: "VC exporterar scenen till
            # USD" fallde, "VC exporterar scenen till USD utan problem" gick
            # fri - och den andra ar ett starkare forslag an den forsta.
            continue
        for fakta in FAKTA:
            # NAMNEN provas pa ordgrans och VERBEN som delstrang, av samma
            # skal som text.py skiljer pa riktningarna: "usd" star inne i
            # "husdjur" och skulle med delstrang gora ett husdjur till en
            # filformatsfraga, medan verben ar STAMMAR och maste kunna
            # matcha importerar, importera och import.
            if not bar_ord(lag, fakta.ord):
                continue
            if not bar_delstrang(lag, fakta.verb):
                continue
            if fakta.kravda_ord and not bar_delstrang(lag, fakta.kravda_ord):
                continue
            if fakta.id == "DOM-005" and not bar_ord(lag, VC_ORD):
                continue
            ut.append(Anmarkning(regel=fakta.id, skal=fakta.skal,
                                 mening=mening.text))
            break
    return tuple(ut)


def skal(anmarkningar: Sequence[Anmarkning]) -> Tuple[str, ...]:
    """Avvisningens skal, ett per anmarkning, plus vad modellen ska gora."""
    if not anmarkningar:
        return ()
    rader = [a.text() for a in anmarkningar]
    rader.append("Skriv om svaret utan den vagen. Sag rakt ut att produkten "
                 "inte har den, och foresla en vag som finns i den matta "
                 "API-ytan.")
    return tuple(rader)
