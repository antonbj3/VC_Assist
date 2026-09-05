# -*- coding: utf-8 -*-
"""Grindarnas regler, sagda FORE modellen skriver i stallet for efter.

## Varfor modulen finns

Fas 9 mater tva tal: forsta forsoket och efter k varv. Forsta forsoket ar
0 av 4; efter ett reparationsvarv 4 av 4. Operatorens krav ar det omvanda -
**enskott ska vara normalfallet, flerskott en reserv**.

Arkitekturen valjer i dag flerskott, och det ar inte en installning utan en
FORM: grindarnas kunskap nar modellen forst NAR den redan skrivit fel. En
modell som aldrig fatt veta att `T#3.0s` maste ha sin decimal i den minsta
delen kan inte undvika det - den kan bara ratta det efterat.

Modulen flyttar den kunskapen fore skrivningen.

## Varfor den GENERERAS och inte skrivs

En handskriven lista over "korrekta ST-principer" ar en handskriven ordlista,
och det ar den dyraste formen i det har repot. Tre grindar foll pa den under en
och samma natt: `NEKANDE` i harness/text.py fyrade pa fel storhet, `_ARLIGHET`
var skriven i ASCII mot svensk text med atta doda grenar, och verktygens
effektlista sa ett och koden ett annat.

Alla tre har samma form: **nagon skrev vad hen kom ihag, koden kom att krava
nagot annat, och de gled isar utan att nagon sag det.**

Darfor lases reglerna ur grindarnas EGNA kodtabeller - `st.fel.KONTROLLER`
(grind 2) och `plc.deklarationsgrind.KONTROLLER_PLC` (grind 3). En kod utan
regel ar en FALLA: grinden kan falla pa nagot modellen aldrig fick veta. Det
ar mekaniskt kontrollerat i `saknade_regler()`, och provet med samma namn
faller om nagon lagger till en kontroll utan att saga vad man ska gora i
stallet.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..st.fel import KONTROLLER
from .deklarationsgrind import KONTROLLER_PLC

# kod -> instruktionen som gor att kontrollen inte faller.
#
# Varje rad ar skriven mot vad grinden FAKTISKT gor, inte mot vad den heter.
# Tva av dem kommer ur matta modellfel: TIDLITERAL stod for nio av sexton
# grinddomar i fas 9:s forsta modelldrivna korning (M-96), och DUBBELSKRIVNING
# for fem av sexton.
REGLER: Dict[str, str] = {
    # --- grind 2, ST-lagret -------------------------------------------------
    "BALANS":
        "Avsluta varje block med sitt eget END_: IF med END_IF, CASE med "
        "END_CASE, WHILE med END_WHILE, FOR med END_FOR. Ett block som "
        "avslutas med fel END_ falls.",
    "SYNTAX":
        "Skriv giltig ST och ingenting annat. Ingen prosa, inga "
        "markdown-kodstaket, inga icke-ASCII-tecken - a, a och o i en "
        "kommentar falls ocksa. EXIT far bara sta inne i en slinga.",
    "TIDLITERAL":
        "TIME-literaler: T#<tal><enhet>, enheterna d h m s ms us ns i fallande "
        "ordning, varje enhet hogst en gang, och BARA den minsta delen far ha "
        "decimaler. T#4s och T#1h30m ar giltiga; T#500 saknar enhet, T#5s10m "
        "har fel ordning och T#1.5h30m har decimal i fel del. Skiftlage spelar "
        "ingen roll.",
    "ODEKLARERAD":
        "Anvand bara namn som star i skelettets VAR-block. Behover du en egen "
        "arbetsvariabel: deklarera den mellan ARBETSVARIABLER-markorerna, "
        "aldrig i signalernas VAR-block och aldrig med en AT %-adress.",
    "DUBBELDEKLARATION":
        "Deklarera varje namn en gang. Skelettets variabler ar redan "
        "deklarerade - deklarera aldrig om dem.",
    "OKANT_NAMN":
        "Anvand bara funktionsblock och funktioner som finns: TON, TOF, TP, "
        "R_TRIG, F_TRIG, RS, SR, CTU, CTD. Ett funktionsblock maste vara "
        "deklarerat som en instans innan det anropas.",
    "ARGUMENT":
        "Anropa funktionsblock med deras egna faltnamn: TON tar IN och PT och "
        "ger Q och ET; R_TRIG tar CLK och ger Q. Fel faltnamn eller fel antal "
        "argument falls.",
    "TYP":
        "Blanda inte typer. En BOOL jamfors inte med ett tal, en INT tilldelas "
        "inte en REAL utan konvertering, och en TIME jamfors bara med TIME.",
    "RIKTNING":
        "Skriv aldrig till en ingang (VAR_INPUT), till en CONSTANT eller till "
        "en styrvariabel. Ingangar lases; utgangar skrivs.",
    "DUBBELSKRIVNING":
        "Skriv varje utgang pa EXAKT ETT stalle. Tva skrivningar till samma "
        "utgang som kan koras i samma scan falls, aven nar de star i olika "
        "grenar - sist skriven vinner, och da doljer koden sin egen avsikt. "
        "Behover utgangen satta och nollstallas: gor det i EN sats, till "
        "exempel `UT := villkorA AND NOT villkorB;`.",
    "OATKOMLIG":
        "Skriv ingen kod som aldrig kan koras: en gren efter ett villkor som "
        "alltid ar falskt, eller satser efter RETURN eller EXIT.",
    "SAKERHET":
        "Skriv aldrig till en tagg markt {SAKERHET}. Nodstopp och "
        "skyddskretsar ligger pa certifierad sakerhets-PLC och far bara lasas.",
    # --- grind 3, deklarationer mot signalkartan ---------------------------
    "OLASLIG":
        "Lamna en kropp som gar att lasa. En kropp som inte parsar kan grind 3 "
        "inte doma alls.",
    "SAKNAD_POU":
        "Ror aldrig PROGRAM-raden eller END_PROGRAM. De ar skelettets, inte "
        "dina.",
    "OKARTLAGD_TAGG":
        "Anvand bara signalnamn som star i signalkartan. Hitta aldrig pa ett "
        "taggnamn, och skriv det exakt som det star.",
    "SAKNAD_DEKLARATION":
        "Ror inte skelettets VAR-block: varje signal i kartan ar redan "
        "deklarerad dar.",
    "AVVIKANDE_DEKLARATION":
        "Andra aldrig en signals typ, adress eller skyddsmarkning.",
    "ORORD_SIGNAL":
        "Anvand varje signal i kartan. En signal som koden varken laser eller "
        "skriver betyder att en del av uppgiften inte ar gjord.",
    "SKRIVEN_INGANG":
        "Skriv aldrig till en signal som PLC:n bara laser - en givare, en "
        "knapp eller ett vaktvillkor.",
    "ODRIVEN_UTGANG":
        "Skriv varje utgang i kartan. En utgang som koden aldrig satter ar en "
        "stalldon som aldrig ror sig.",
}


def alla_koder() -> Tuple[str, ...]:
    """Varje kod som nagon av de tva grindarna kan falla pa."""
    return tuple(sorted(set(KONTROLLER) | set(KONTROLLER_PLC)))


def saknade_regler() -> Tuple[str, ...]:
    """Koder en grind kan falla pa men som modellen aldrig fatt veta om.

    Det ar en FALLA, inte en bekvamlighetsbrist: grinden fallr da pa nagot
    ingen sagt at modellen att undvika, och forsta forsoket kan aldrig bli
    ratt av annat an tur.
    """
    return tuple(k for k in alla_koder() if not REGLER.get(k, "").strip())


def foraldralosa_regler() -> Tuple[str, ...]:
    """Regler for koder som ingen grind langre kan falla pa.

    En instruktion utan grind bakom sig ar en bon som ser ut som en regel.
    """
    koder = set(alla_koder())
    return tuple(sorted(k for k in REGLER if k not in koder))


def text(rubrik: str = "Vad grindarna faller, och hur du undviker det") -> str:
    """Reglerna som en sektion att lagga i systemprompten.

    Ordningen ar grindens: grind 2 fore grind 3, och inom varje grind i
    kodtabellens egen ordning - sa den som jamfor prompten med grinden laser
    samma lista i samma ordning.
    """
    rader: List[str] = [rubrik, ""]
    for tabell, namn in ((KONTROLLER, "Grind 2 - ST-lagret"),
                         (KONTROLLER_PLC, "Grind 3 - signalkartan")):
        rader.append(namn)
        for kod in tabell:
            regel = REGLER.get(kod, "").strip()
            if regel:
                rader.append("  %-22s %s" % (kod, regel))
        rader.append("")
    return "\n".join(rader).rstrip() + "\n"
