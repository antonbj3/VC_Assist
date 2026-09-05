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

import os
import re

from ..st.fel import KONTROLLER
from .deklarationsgrind import KONTROLLER_PLC

# Felklasstabellen i 82_felklasser.md. Lases ur DOKUMENTET, inte kopieras hit:
# tva kopior av samma tabell glider isar, och natten har redan visat sex
# ordlistor som gjorde just det.
_FELKLASSER_MD = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "docs", "spec", "82_felklasser.md"))
_KLASSRAD = re.compile(r"^\|\s*`(F\d+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")

# kod -> instruktionen som gor att kontrollen inte faller.
#
# Varje rad ar skriven mot vad grinden FAKTISKT gor, inte mot vad den heter.
#
# SYNTAX-regeln bar ett fel som ar vart att minnas: den forbjod icke-ASCII och
# forsokte namna tecknen - men var sjalv skriven i translittererad svenska, sa
# modellen last "a, a och o" och sag tre likadana bokstaver. En regel om tecken
# som inte kan skriva tecknen ar sjalvupphavande.
#
# Kostnaden ar matt (M-96): T-07 forlorade TVA av fyra reparationsvarv pa ett
# enda "a-med-prickar" i en kommentar, i varv 1 och igen i varv 4 - trots att
# den sett grindens dom i varv 1. Uppgiften var pa vag att losas (fyra brister
# i varv 2, EN i varv 3) och slog i taket pa ett formatfel.
#
# Att regeln ar STRANGARE an kompilatorn ar med flit och star kvar: STruC++
# accepterar icke-ASCII i kommentarer, men teckenkodningen genom OpenPLC och
# vidare ut som OPC UA-namn ager vi inte.
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
        "Skriv giltig ST och ingenting annat: ingen prosa, inga "
        "markdown-kodstaket, EXIT bara inne i en slinga.\n"
        "        REN ASCII I HELA KALLAN, ocksa i kommentarer. Uppgiften ar "
        "skriven pa svenska men koden far inte vara det: \u00e5, \u00e4, "
        "\u00f6, \u00c5, \u00c4 och \u00d6 falls, aven inne i (* ... *). "
        "Skriv 'nodstopp' och inte 'n\u00f6dstopp', 'lage' och inte "
        "'l\u00e4ge', 'sankt' och inte 's\u00e4nkt'. Enklast: skriv "
        "kommentarerna pa engelska.",
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
        "Har en utgang tva varden: anvand IF/ELSE (eller ELSIF), skriv den som "
        "ETT uttryck `UT := villkorA AND NOT villkorB;`, eller satt ett "
        "grundvarde OVILLKORAT forst och skriv over det villkorat efterat. "
        "Alla tre gar igenom. Det som falls ar tva SEPARATA IF-block som ger "
        "samma utgang OLIKA varden - bada kan koras i samma scan och da avgor "
        "ordningen, inte logiken. Ocksa: en ovillkorad skrivning EFTER en "
        "villkorad (den villkorade blir verkningslos), och tva ovillkorade "
        "(den forsta syns aldrig).",
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
        "Ror varje signal i skelettets VAR-block minst en gang. Las varje "
        "ingang, skriv varje utgang. En signal som koden varken laser eller "
        "skriver betyder att en del av uppgiften inte ar gjord - ga igenom "
        "deklarationerna och kontrollera att inget namn blev over.",
    "SKRIVEN_INGANG":
        "Skriv aldrig till en signal som PLC:n bara laser. Adressen sager "
        "vilken sort det ar: AT %I... ar en INGANG och lases bara (givare, "
        "knappar, vaktvillkor), AT %Q... ar en UTGANG och skrivs, AT %M... ar "
        "minne. Star det %I i deklarationen far namnet aldrig sta till vanster "
        "om ett :=.",
    "ODRIVEN_UTGANG":
        "Skriv varje utgang i kartan - alltsa varje namn med AT %Q... i "
        "deklarationen. En utgang som koden aldrig satter ar ett stalldon som "
        "aldrig ror sig, och uppgiften ar da inte gjord.",
}


# Ogats klasser: instruktionen som gor att domen inte faller. De kommer ur
# 82_felklasser.md:s definitioner - klasserna sjalva lases ur dokumentet, sa en
# ny klass dar blir en saknad regel har i stallet for en tyst lucka.
OGATS_REGLER: Dict[str, str] = {
    "F5": "Stegen ska ske i den ordning uppgiften anger. Bygg sekvensen som ett "
          "stegvarde som bara gar framat vid sitt eget villkor - inte som "
          "fristaende IF-satser som kan fyra i fel ordning nar tva givare blir "
          "hoga samtidigt.",
    "F6": "Ratt ordning racker inte, tiderna maste stamma. Lat varje rorelse "
          "vanta pa sitt andlage eller sin timer, aldrig pa att foregaende steg "
          "bara har kommenderats. En utgang som satts betyder inte att nagot "
          "har hant an.",
    "F7": "Tva utgangar som styr samma don at olika hall far aldrig vara hoga i "
          "samma scan. Skriv den omsesidiga uteslutningen som ett villkor i "
          "koden, inte som en foljd av att stegen rakar vara olika.",
    "F8": "Forreglingen mellan stationer maste lasa BADA hallen. Las den andra "
          "stationens TILLSTAND, inte dess utgang - utgangen satts en scan "
          "efter beslutet, sa villkoret slapper igenom just den samtidighet det "
          "ska hindra.",
    "F9": "Hall geometrin: rackvidd, fri hojd och avstand. En rorelse som "
          "kommenderas utan att vagen ar fri blir en kollision aven om koden ar "
          "logiskt riktig.",
    "F10": "Greppet ska halla hela vagen. Slapp aldrig fore mottagaren "
           "bekraftat, och kontrollera greppvakten innan rorelsen fortsatter.",
    "F11": "Cellen ska na sin takttid. En sekvens som ar korrekt men vantar i "
           "onodan - till exempel pa en timer nar ett andlage redan svarat - "
           "faller pa genomflode.",
    "F12": "Skriv aldrig kod som far ett prov att passera utan att saken skett. "
           "Att satta en klarsignal utan att rorelsen ar gjord ar ohederligt, "
           "och det ar den enda klassen som ar overordnad alla andra.",
    "F15": "Las en handelse pa FLANK och ett tillstand pa NIVA. En "
           "aterstallningsknapp som lases pa niva startar om sa lange den halls "
           "inne; ett latchat larm som lases pa flank slapper nar orsaken "
           "forsvinner.",
}


def ogats_klasser() -> Dict[str, Tuple[str, str]]:
    """F-klasserna som OGAT faller pa, ur 82_felklasser.md.

    Klassen raknas som ogats om tabellens sista kolumn namner ogat. Tabellen
    lases ur dokumentet i stallet for att kopieras hit - tva kopior av samma
    tabell glider isar, och natten har redan visat sex ordlistor som gjorde
    just det.
    """
    ut = {}
    try:
        with open(_FELKLASSER_MD, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return ut
    for rad in text.splitlines():
        m = _KLASSRAD.match(rad)
        if not m:
            continue
        kod, namn, definition, fangas = m.groups()
        if "gat" in fangas:                      # "ögat" / "ogat"
            ut[kod] = (namn, definition)
    return ut


def saknade_ogonregler() -> Tuple[str, ...]:
    """Ogonklasser modellen aldrig fatt veta om.

    Samma falla som en kontroll utan regel: ogat faller pa nagot ingen sagt at
    modellen att undvika, och forsta forsoket kan inte bli ratt av annat an tur.
    """
    return tuple(k for k in sorted(ogats_klasser())
                 if not OGATS_REGLER.get(k, "").strip())


def foraldralosa_ogonregler() -> Tuple[str, ...]:
    klasser = set(ogats_klasser())
    return tuple(sorted(k for k in OGATS_REGLER if k not in klasser))


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
    klasser = ogats_klasser()
    if klasser:
        rader.append("Ogat - det som doms nar cellen KOR")
        for kod in sorted(klasser, key=lambda k: int(k[1:])):
            namn, _def = klasser[kod]
            regel = OGATS_REGLER.get(kod, "").strip()
            if regel:
                rader.append("  %-6s %-14s %s" % (kod, namn, regel))
        rader.append("")
    return "\n".join(rader).rstrip() + "\n"
