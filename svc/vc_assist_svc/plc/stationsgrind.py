# -*- coding: utf-8 -*-
"""Fas 7: kör grind 1-4 över en stationskandidat och producerar guldgrindens cell.

Kedjan i docs/spec/50_grindar.md har fyra förgrindar före ögat, och
`guldgrind.py` läser dem ur en cell:

    cell["forgrindar"] = {"kompilering": ..., "statisk_analys": ...,
                          "deklarationsmatchning": ..., "anropsvalidering": ...}

Ingen producerade den cellen. Grindarna fanns var för sig, guldgrinden väntade
på deras svar, och ingenting band ihop dem. Den här filen är bandet.

**Varje grind rapporterar sin EGEN utdata.** Ett värde i `forgrindar` är `True`
eller den fällande grindens ord, ordagrant. Det är invariant I1, och den är
motiverad av en mätt incident: en omimplementerad positionsdom underkände 2 av 4
medan ögat visade 4 av 4. En grind som skriver om observatörens svar mäter till
slut sig själv.

## Ordningen är billigast först, inte 1 2 3 4

Grind 2 och 3 läser samma träd och körs i ett anrop. Grind 4 parsar Python.
Grind 1 startar en kompilator. En tagg som inte finns i kartan ska aldrig hinna
bli C++; samma skäl som `matning.py` redan följer.

## Varför "ingen kod" aldrig är ett godkännande

En kandidat utan scenkod ger inte `anropsvalidering: True`. Den ger skälet till
att grinden inte kunde köras, och guldgrinden fäller på det.

Detsamma gäller när kompilatorn saknas: det är inte ett grönt i väntan på
besked, det är ett rött (I3).

Och strängare än så: grind 4 räknar hur många namn den faktiskt kontrollerade.
Kontrollerade den noll namn har den inte mätt något, och då är svaret inte
`True` heller — en grind som blir billig slutar mäta sin egen storhet.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..api_index import Granskning
from .deklarationsgrind import granska as granska_deklarationer
from .industrigrind import Krav
from .industrigrind import granska as granska_industriform
from .signalkarta import Signalkarta
from .skelett import Skelett, Skelettfel

# Guldgrindens namn på förgrindarna. Importeras inte därifrån: guldgrinden är
# py2-giltig och ska inte dras in i tjänstelagret. Provet nedan håller ihop dem.
NAMN_KOMPILERING = "kompilering"
NAMN_STATISK = "statisk_analys"
NAMN_DEKLARATION = "deklarationsmatchning"
NAMN_ANROP = "anropsvalidering"

# Grind 3b (M-159) är INTE en av guldgrindens fyra. Den ligger utanför
# KORORDNING med avsikt: guldgrinden räknar "alla fyra körda och alla fyra
# True", och en femte nyckel i den listan hade gjort varje befintlig cell röd
# över en natt. Den körs bara när anroparen lämnar ett `Krav` — alltså när det
# finns en uppgift att läsa kraven ur — och räknas då in i `ok`.
NAMN_INDUSTRI = "industriell_form"

# Ordningen grindarna körs i. Billigast först; se modulens huvud.
KORORDNING = (NAMN_STATISK, NAMN_DEKLARATION, NAMN_ANROP, NAMN_KOMPILERING)


class Stationsfel(Exception):
    """Kandidaten går inte att döma alls; skilt från att den underkänns."""


@dataclass(frozen=True)
class Kandidat:
    """Det en modell levererar för en station.

    st_kalla    hela ST-texten, skelettet med modellens kropp isatt
    scenkod     Python-koden som bygger stationen i scenen, eller None
    """

    station: str
    st_kalla: str
    scenkod: Optional[str] = None

    @staticmethod
    def fran_modellsvar(skelett: Skelett, svar: str,
                        scenkod: Optional[str] = None) -> "Kandidat":
        """Kandidaten ur ett rått modellsvar, efter skelettets ramgrind.

        Skelettfel bubblar med flit. En kandidat vars ram är ändrad ska aldrig
        bli en kandidat: den är inte en kropp med ett fel, den är ett annat
        program, och att låta den nå grind 2 hade gett en anmärkning om logik
        där felet var att deklarationerna byttes ut.
        """
        return Kandidat(skelett.station, skelett.las_svar(svar), scenkod)


@dataclass
class Stationsdom:
    forgrindar: Dict[str, object] = field(default_factory=dict)
    utdata: Dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Alla fyra körda och alla fyra True. Saknad grind är inte grönt.

        Grind 3b räknas in **när den körts**. Att den saknas är inte ett
        underkännande: den kräver en uppgift att läsa kraven ur, och den som
        inte lämnar en har inte hoppat över en grind utan aldrig haft den.
        """
        for namn in KORORDNING:
            if self.forgrindar.get(namn) is not True:
                return False
        if (NAMN_INDUSTRI in self.forgrindar
                and self.forgrindar[NAMN_INDUSTRI] is not True):
            return False
        return True

    @property
    def forsta_fallande(self) -> Optional[str]:
        """Den grind som faktiskt fällde, före den som bara står tom.

        Ordningen är körordningens, med grind 3b insatt där den körs. Att leta
        efter en fällande grind FÖRE en saknad är samma rättelse som redan står
        i `till_cell`: skälet ska namnge orsaken, inte den första grinden som
        råkade stå tom därför att den aldrig hann köras.
        """
        ordning = (NAMN_STATISK, NAMN_DEKLARATION, NAMN_INDUSTRI,
                   NAMN_ANROP, NAMN_KOMPILERING)
        for namn in ordning:
            if namn in self.forgrindar and self.forgrindar[namn] is not True:
                return namn
        for namn in KORORDNING:
            if namn not in self.forgrindar:
                return namn
        return None

    def text(self) -> str:
        rader = []
        for namn in list(KORORDNING) + (
                [NAMN_INDUSTRI] if NAMN_INDUSTRI in self.forgrindar else []):
            utfall = self.forgrindar.get(namn, "EJ KORD")
            if utfall is True:
                rader.append("%-22s GODKAND" % namn)
            else:
                rader.append("%-22s FALLDE: %s" % (namn, utfall))
                egen = self.utdata.get(namn)
                if egen:
                    rader.extend("    | " + r for r in egen.splitlines())
        return "\n".join(rader)

    def till_cell(self, namn: str, klass: str,
                  eyes: Optional[str] = None) -> Dict[str, object]:
        """Cellen som `guldgrind.Guldgrind.doma_cell` läser.

        `eyes` lämnas None när ögat inte körts. Guldgrinden fäller då på
        "ingen ogonrapport", vilket är rätt: grind 5 är den som avgör.
        """
        # Alla fyra nycklarna fylls, aven de som hoppades over. Guldgrinden
        # gar igenom dem i SIN ordning, och en saknad nyckel gjorde att den
        # rapporterade "kompilering ar inte kord" nar det i sjalva verket var
        # anropsvalideringen som fallde. Skalet ska namna orsaken, inte den
        # forsta grinden som rakade sta tom.
        forgrindar = dict(self.forgrindar)
        forst = self.forsta_fallande
        for gnamn in KORORDNING:
            if gnamn not in forgrindar:
                forgrindar[gnamn] = ("ej kord; %s fallde forst" % forst
                                     if forst else "ej kord")
        cell = {"namn": namn, "klass": klass, "forgrindar": forgrindar}
        if eyes is not None:
            cell["eyes"] = eyes
        return cell


def _grind_2_och_3(dom: Stationsdom, kandidat: Kandidat,
                   karta: Signalkarta) -> None:
    """Ett anrop ger båda: deklarationsgrinden bär ST-lagrets rapport bredvid."""
    rapport = granska_deklarationer(kandidat.st_kalla, karta, aven_grind2=True)

    st = rapport.st_rapport
    if st is None:
        dom.forgrindar[NAMN_STATISK] = "grind 2 kordes inte"
    elif st.ok:
        dom.forgrindar[NAMN_STATISK] = True
    else:
        dom.forgrindar[NAMN_STATISK] = "%d anmarkningar: %s" % (
            len(st.anmarkningar), ", ".join(sorted(set(st.koder()))))
    dom.utdata[NAMN_STATISK] = str(st) if st is not None else ""

    # Grind 3:s EGEN dom, inte den kombinerade.
    #
    # `Grind3Rapport.ok` ar `not anm and st_rapport.ok` - alltsa falsk ocksa nar
    # bara GRIND 2 fallde. Att lasa den som grind 3:s dom gav ett besked utan
    # orsak: "deklarationsmatchning: 0 anmarkningar", vilket sag ut som en grind
    # som faller utan att saga varfor. En modell som far det letar efter ett
    # deklarationsfel som inte finns.
    #
    # Den kombinerade flaggan ar riktig for den som vill ha ETT svar. Har vill
    # vi ha fyra, ett per grind, och da maste var och en svara for sig.
    if not rapport.anmarkningar:
        dom.forgrindar[NAMN_DEKLARATION] = True
    else:
        dom.forgrindar[NAMN_DEKLARATION] = "%d anmarkningar: %s" % (
            len(rapport.anmarkningar), ", ".join(sorted(set(rapport.koder()))))
    dom.utdata[NAMN_DEKLARATION] = str(rapport)


def _grind_3b(dom: Stationsdom, kandidat: Kandidat, karta: Signalkarta,
              krav: Krav) -> None:
    """Den industriella minimiformen: tidsvakt, larmutgång och förregling.

    Rapporterar sin EGEN utdata, oförvanskad (invariant I1), och tar med det
    grinden INTE kunde döma — en grind som slänger det den inte förstod ser
    större ut än den är.
    """
    rapport = granska_industriform(kandidat.st_kalla, karta, krav)
    dom.utdata[NAMN_INDUSTRI] = str(rapport)
    if rapport.ok:
        dom.forgrindar[NAMN_INDUSTRI] = True
    else:
        dom.forgrindar[NAMN_INDUSTRI] = "%d anmarkningar: %s" % (
            len(rapport.anmarkningar), ", ".join(sorted(set(rapport.koder()))))


def _grind_4(dom: Stationsdom, kandidat: Kandidat, index) -> None:
    if index is None:
        dom.forgrindar[NAMN_ANROP] = "API-indexet saknas; grinden kunde inte kora"
        dom.utdata[NAMN_ANROP] = ""
        return
    if not (kandidat.scenkod or "").strip():
        # Inte ett godkännande. En station byggs av verktygsanrop, och en
        # kandidat utan dem har inte visat att den kan bygga stationen.
        dom.forgrindar[NAMN_ANROP] = "kandidaten bar ingen scenkod att validera"
        dom.utdata[NAMN_ANROP] = ""
        return

    granskning: Granskning = index.granska(kandidat.scenkod)
    dom.utdata[NAMN_ANROP] = granskning.rapport()
    if not granskning.godkand:
        dom.forgrindar[NAMN_ANROP] = "%d fel, %d obestambara" % (
            len(granskning.fel), len(granskning.obestambara))
        return
    if granskning.kontrollerade_namn <= 0:
        # En grind som inte kontrollerade ett enda namn har inte mätt sin egen
        # storhet, och dess grona ar innehallslost.
        dom.forgrindar[NAMN_ANROP] = ("granskningen kontrollerade noll namn; "
                                      "ingenting blev provat")
        return
    dom.forgrindar[NAMN_ANROP] = True


def _grind_1(dom: Stationsdom, kandidat: Kandidat, strucpp_paket: Optional[str],
             byggkatalog: Optional[str], node: str,
             strucpp_cli: Optional[str] = None) -> None:
    """Kompilatorn, via CLI:t om det finns och annars via npm-paketet.

    CLI-vagen svarar bara pa grind 1:s fraga och kan inte driftsatta; se
    `paket.granska_kompilering`. Den foredras anda nar bada finns, darfor att
    den ar den billiga vagen och en grind som kors sallan mater ingenting.
    """
    if strucpp_cli and byggkatalog:
        from . import paket
        try:
            kdom = paket.granska_kompilering(
                kandidat.st_kalla, os.path.join(byggkatalog, kandidat.station),
                strucpp_cli)
        except Exception as fel:
            dom.forgrindar[NAMN_KOMPILERING] = "%s" % type(fel).__name__
            dom.utdata[NAMN_KOMPILERING] = str(fel)
            return
        dom.utdata[NAMN_KOMPILERING] = kdom.utdata
        dom.forgrindar[NAMN_KOMPILERING] = (
            True if kdom.ok else "kompilatorn foll med kod %d" % kdom.returkod)
        return
    if not strucpp_paket or not byggkatalog:
        dom.forgrindar[NAMN_KOMPILERING] = ("kompilatorn ar inte uppsatt; "
                                            "grind 1 kunde inte kora")
        dom.utdata[NAMN_KOMPILERING] = ""
        return
    from . import paket  # lat: grind 1 ska inte tvinga in bygglagret
    try:
        paket.kompilera(kandidat.st_kalla,
                        os.path.join(byggkatalog, kandidat.station),
                        strucpp_paket, node=node)
    except Exception as fel:
        dom.forgrindar[NAMN_KOMPILERING] = "%s" % type(fel).__name__
        dom.utdata[NAMN_KOMPILERING] = str(fel)
        return
    dom.forgrindar[NAMN_KOMPILERING] = True
    dom.utdata[NAMN_KOMPILERING] = ""


def granska_station(kandidat: Kandidat, karta: Signalkarta, index=None,
                    strucpp_paket: Optional[str] = None,
                    byggkatalog: Optional[str] = None,
                    node: str = "node",
                    strucpp_cli: Optional[str] = None,
                    stanna_vid_forsta: bool = True,
                    krav: Optional[Krav] = None) -> Stationsdom:
    """Kör grind 1-4 över kandidaten och lämna varje grinds egen dom.

    `stanna_vid_forsta` sparar en byggcykel i drift. Sätt False när hela
    grindbilden behövs, till exempel när bänken räknar fel per klass.

    `krav` är uppgiftens industrikrav (`industrigrind.Krav.ur_uppgift`). Lämnas
    det körs grind 3b och läggs till under `NAMN_INDUSTRI`; lämnas det inte är
    domen bit för bit densamma som förut.
    """
    if kandidat.station.upper() != karta.station.upper():
        raise Stationsfel("kandidaten galler %r men kartan galler %r"
                          % (kandidat.station, karta.station))

    dom = Stationsdom()
    _grind_2_och_3(dom, kandidat, karta)
    if stanna_vid_forsta and not dom.ok and dom.forsta_fallande in (
            NAMN_STATISK, NAMN_DEKLARATION):
        return dom
    if krav is not None:
        _grind_3b(dom, kandidat, karta, krav)
        if stanna_vid_forsta and dom.forgrindar[NAMN_INDUSTRI] is not True:
            return dom
    _grind_4(dom, kandidat, index)
    if stanna_vid_forsta and dom.forgrindar.get(NAMN_ANROP) is not True:
        return dom
    _grind_1(dom, kandidat, strucpp_paket, byggkatalog, node, strucpp_cli)
    return dom
