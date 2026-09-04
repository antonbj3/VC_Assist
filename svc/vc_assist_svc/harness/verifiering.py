# -*- coding: utf-8 -*-
"""VERIFY-CONTRACT: modellens egen text provas mot vad verktygen returnerade.

20_arv.md kallar detta den starkaste iden i hela kallrepot. Den ar mekanisk
och gar i tre steg:

    1  PLOCKA   namn och tal ur modellens text (text.py)
    2  PROVA    varje namn och tal mot GRUNDEN
    3  PEKA UT  det som inte stammer, ordagrant, i omskrivningskravet

GRUNDEN ar det modellen har ratt att luta sig mot, och den ar avsiktligt
snav:

    verktygssvaren i turen        allt som verktygen faktiskt returnerade
    operatorens uppgiftstext      det operatoren sjalv skrev
    ogats rapport                 nar en sadan finns i turen
    verktygsnamnen               sa att modellen far namna sina verktyg
    API-indexet                   for VC-namn (204 typer, 966 metoder)
    katalogindexet                for komponent-URI:er

Instruktionskorpusen ar INTE grund. Ett tal i systemprompten ar ingen
matning av den har scenen, och att lata prompten stodja pastaenden vore att
lata modellen citera sina egna instruktioner som bevis.

TVA SORTERS AVVIKELSE, med olika text tillbaka:

    tal   ett tal som ingen matning stodjer. Avrundning tillats: ett tal med
          en decimal stodjs av varje matvarde som avrundas till det. Enheter
          rakas om till bas (millimeter, sekunder, grader, kilogram) fore
          jamforelsen, eftersom verktygens vektorer ar i millimeter.
    namn  ett namn som varken star i ett verktygssvar, i uppgiften, i
          API-indexet eller i katalogen. Det ar den klassiska hallucinationen
          och den domes hardare: den kan inte avrundas ratt.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .text import Namnpastaende, Talpastaende, namn_i, normalisera, tal_i

# Avrundningsmarginal utover halva sista decimalen. Ren flyttalsmarginal, inte
# en tolerans pa matningen: 2,5 far inte falla pa att 2500,0/1000 blir
# 2,4999999999999996.
_FLYTTALSMARGINAL = 1e-9   # Satt av M-46, ren float64-marginal.

# Tal i en strang ur ett verktygssvar, t.ex. modellnamnet "IRB 1200-5/0.9".
# Ett verktygssvar som BAR talet i en text stodjer talet: modellen som
# skriver 1200 har last det, inte hittat pa det.
_TAL_I_STRANG = re.compile(r"-?\d+(?:\.\d+)?")

# Enhetsfaktorer mellan VC:s basenhet och de enheter en modell skriver i.
# MATT: verktygens vektorargument ar definierade i MILLIMETER (verktyg/bas.py,
# XYZ), och de tre stegen upp ar cm, dm och m. Listan finns for EN sak: nar
# ett tal inte stods av nagon matning ska grinden kunna saga OM det hade
# stotts i en annan enhet, i stallet for att bara saga att det saknas. Det ar
# skillnaden mellan "talet ar pahittat" och "du glomde enheten", och DOM-003
# handlar om den andra. Satt av M-53.
ENHETSFAKTORER = (1000.0, 100.0, 10.0, 0.1, 0.01, 0.001)  # Satt av M-53.
# Hur nara kvoten maste ligga en av faktorerna for att det ska rakas som
# samma tal i en annan enhet. Relativ, sa att den galler for bade 0,812 och
# for 2500. Satt av M-53: 1e-6 ar langt under varje verklig matskillnad och
# langt over flyttalsbruset.
ENHETSTOLERANS = 1e-6  # Satt av M-53.


@dataclass(frozen=True)
class Avvikelse:
    """Ett pastaende som grunden inte stodjer."""

    sort: str                 # tal | namn
    vad: str
    mening: str
    skal: str

    def text(self) -> str:
        return "%s: %s (i meningen: %r)" % (self.vad, self.skal, self.mening)


class Grund(object):
    """Allt modellen har ratt att luta sig mot i den har turen."""

    def __init__(self, uppgiftstext: str = "", verktygsnamn: Sequence[str] = (),
                 api=None, katalogindex: Optional[Dict] = None):
        self.uppgiftstext = uppgiftstext or ""
        self.api = api
        self.katalogindex = katalogindex or {}
        self._strangar: List[str] = []
        self._normaliserade: set = set()
        self._tal: List[float] = []
        self.kallor: List[str] = []

        # NAMN, men inte TAL, ur de har tre kallorna. Skalet ar matt i
        # efterlevnadsbanken 2026-09-04: med katalogens tal i grunden stoddes
        # ett pahittat avstand pa 0,45 m av rackvidden i en robotpost som
        # modellen aldrig slagit upp (falla F-10). Ett namn ur katalogen ar
        # ett namn som finns; ett TAL ur katalogen ar ingen matning av DEN
        # HAR scenen. Samma sak for uppgiftstexten: att operatoren namner ett
        # matt gor inte att det ar uppmatt.
        for namn in verktygsnamn:
            self._lagg_strang(namn, med_tal=False)
        for uri, post in self.katalogindex.items():
            self._lagg_strang(uri, med_tal=False)
            if post.get("namn"):
                self._lagg_strang(post["namn"], med_tal=False)
        if self.uppgiftstext:
            self.lagg_text(self.uppgiftstext, "uppgiften", med_tal=False)

    # ---- fylla pa -------------------------------------------------------

    def _lagg_strang(self, text: str, med_tal: bool = True) -> None:
        if not isinstance(text, str) or not text.strip():
            return
        self._strangar.append(text)
        self._normaliserade.add(normalisera(text))
        for bit in re.split(r"[\s/,;]+", text):
            if bit:
                self._normaliserade.add(normalisera(bit))
        if not med_tal:
            return
        for m in _TAL_I_STRANG.finditer(text):
            try:
                self._tal.append(float(m.group(0)))
            except ValueError:
                continue

    def _lagg_varde(self, varde: Any, med_tal: bool = True) -> None:
        if isinstance(varde, bool):
            return
        if isinstance(varde, (int, float)):
            if med_tal:
                self._tal.append(float(varde))
        elif isinstance(varde, str):
            self._lagg_strang(varde, med_tal)
        elif isinstance(varde, dict):
            for n, v in varde.items():
                self._lagg_strang(str(n), med_tal=False)
                self._lagg_varde(v, med_tal)
        elif isinstance(varde, (list, tuple)):
            for v in varde:
                self._lagg_varde(v, med_tal)

    def lagg_resultat(self, verktyg: str, argument: Any, resultat: Any) -> None:
        """Ett LYCKAT verktygsanrop: argumenten OCH svaret.

        Argumenten hor hit darfor att de ar fakta om vad som gjordes. Bad
        modellen om en flytt pa 500 mm och anropet gick igenom, sa ar 500 mm
        ett tal den har ratt att skriva. Argumenten till ett anrop som FOLL
        laggs aldrig hit: da hande ingenting.
        """
        self.kallor.append(verktyg)
        self._lagg_varde(argument)
        self._lagg_varde(resultat)

    def lagg_text(self, text: str, kalla: str, med_tal: bool = True) -> None:
        """En textkalla, t.ex. ogats rapport eller operatorens uppgift."""
        self.kallor.append(kalla)
        self._lagg_strang(text, med_tal)

    # ---- prova ----------------------------------------------------------

    def stodjer_tal(self, tal: Talpastaende) -> Optional[str]:
        """None om talet stods, annars skalet det inte gor det."""
        faktor = tal.bas / tal.varde if tal.varde else 1.0
        marginal = 0.5 * (10.0 ** -tal.decimaler) + _FLYTTALSMARGINAL
        for observerat in self._tal:
            # Jamfor i den enhet MODELLEN skrev talet i: avrundningen skedde
            # dar, sa marginalen hor hemma dar.
            i_modellens_enhet = observerat / faktor if faktor else observerat
            if abs(tal.varde - i_modellens_enhet) <= marginal:
                return None
            if abs(tal.varde - observerat) <= marginal:
                return None
        if not self._tal:
            return ("inget verktyg i turen har returnerat ett enda tal, sa "
                    "talet kan inte komma ur en matning")
        enhet = self._enhetsmiss(tal)
        if enhet:
            return enhet
        return ("inget verktygssvar i turen bar det talet; narmaste varde ar "
                "%s" % _narmast(tal, self._tal, faktor))

    def _enhetsmiss(self, tal: Talpastaende) -> Optional[str]:
        """Skalet nar talet stods i en ANNAN enhet an den skrevs i.

        DOM-003, mekaniserad: langder i VC ar millimeter och vinklar grader,
        och ett matt i meter maste skrivas ut som meter. Ett bart 2,5 i en
        matmening ar inte kontrollerbart - och det ar just formen en modell
        skriver nar den har rakat om till meter i huvudet.
        """
        if not tal.varde:
            return None
        for observerat in self._tal:
            kvot = observerat / tal.varde
            for faktor in ENHETSFAKTORER:
                if abs(kvot - faktor) <= ENHETSTOLERANS * faktor:
                    return ("inget verktygssvar bar %g, men ett bar %g - "
                            "alltsa samma tal en faktor %g bort. VC:s langder "
                            "ar MILLIMETER och vinklar grader (verktyg/bas.py); "
                            "skriver du ett matt i en annan enhet ska enheten "
                            "sta i samma mening som talet (DOM-003)"
                            % (tal.varde, observerat, faktor))
        return None

    def stodjer_namn(self, namn: Namnpastaende) -> Optional[str]:
        if namn.sort == "uri":
            if namn.namn in self.katalogindex:
                return None
            if namn.namn in self.uppgiftstext:
                return None
            if normalisera(namn.namn) in self._normaliserade:
                return None
            return ("URI:n star varken i katalogindexet (%d poster), i "
                    "uppgiften eller i nagot verktygssvar; en uppfunnen URI "
                    "ar ett hart fel (I9)" % len(self.katalogindex))
        if namn.sort == "api":
            if self.api is not None and self.api.finns(namn.namn):
                return None
            if normalisera(namn.namn) in self._normaliserade:
                return None
            forslag = ""
            if self.api is not None:
                narmaste = self.api.narmaste(namn.namn)
                if narmaste:
                    forslag = ". Menade du %s?" % ", ".join(
                        n for n, _ in narmaste[:3])
            return ("namnet finns inte i det matta API-indexet och inte i "
                    "nagot verktygssvar%s" % forslag)
        if normalisera(namn.namn) in self._normaliserade:
            return None
        for strang in self._strangar:
            if normalisera(namn.namn) and normalisera(namn.namn) in normalisera(strang):
                return None
        return ("namnet star varken i ett verktygssvar, i uppgiften eller i "
                "katalogen")


def _narmast(tal: Talpastaende, observerade: Sequence[float],
             faktor: float) -> str:
    basta = min(observerade,
                key=lambda o: abs(tal.varde - (o / faktor if faktor else o)))
    if tal.enhet and faktor and faktor != 1.0:
        return "%g (alltsa %g %s)" % (basta, basta / faktor, tal.enhet)
    return "%g" % basta


def granska(text: str, grund: Grund) -> Tuple[Avvikelse, ...]:
    """Verify-contract over ett slutsvar. Tom lista = inget att anmarka."""
    ut: List[Avvikelse] = []
    for namn in namn_i(text):
        skal = grund.stodjer_namn(namn)
        if skal:
            ut.append(Avvikelse(sort="namn", vad=namn.beskrivning(),
                                mening=namn.mening.text, skal=skal))
    for tal in tal_i(text):
        skal = grund.stodjer_tal(tal)
        if skal:
            ut.append(Avvikelse(sort="tal", vad=tal.beskrivning(),
                                mening=tal.mening.text, skal=skal))
    return tuple(ut)


def omskrivningskrav(avvikelser: Sequence[Avvikelse]) -> str:
    """Texten som gar tillbaka till modellen.

    Pekar ut VAD som inte stammer, en rad per sak. En omskrivning utan
    utpekande ar en uppmaning att gissa om.
    """
    rader = ["Svaret godkanns inte. Foljande i din text stods inte av nagot "
             "verktygssvar i den har turen:"]
    for a in avvikelser:
        rader.append("  - %s" % a.text())
    rader.append("Skriv om svaret. Ta bort eller mat upp varje punkt ovan. "
                 "Ett tal du inte har matt far inte sta kvar, och ett namn du "
                 "inte har sett i ett verktygssvar far inte heller det.")
    return "\n".join(rader)
