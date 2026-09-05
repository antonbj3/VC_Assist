# -*- coding: utf-8 -*-
"""Återhämtningens ordförråd: lägena, orsakerna och vägarna tillbaka.

Fas 17 byggde ytan som visar vad som händer **medan** en körning går. Den här
modulen tar vid där körningen dog. Skillnaden är inte kosmetisk:

* fas 17 frågar *hur går det för körningen?* och svaret bor i körningens egna
  händelser,
* den här frågar *lever systemet, och kommer det tillbaka?* och svaret bor i
  avläsningar av något som kan ha slutat svara mitt i meningen.

En körning som föll kan berätta att den föll. Ett system som dog kan inte
berätta någonting alls, och det är hela svårigheten: **tystnaden måste tolkas
av någon annan än den som tystnade.**

## De tre falska grönen den här modulen finns för att förbjuda

1. **Ett dött läge som ser arbetande ut.** Fas 17 mätte formen två gånger: ett
   hjärtslag som räknades som framsteg gav ARBETAR i 600 av 600 avläsningar
   (M-64), och en läsare som frös klockan gav ARBETAR i 60 av 60 avläsningar
   av en körning vars skrivare dog före den första (M-93). Båda nollade en
   klocka. Här nollas den en tredje gång: en avläsning som återanvänds efter
   att den blivit gammal.
2. **"Ett problem uppstod, vi försöker igen" när ingenting försöker igen.**
   Meningen är värre än tystnad, för den ber användaren vänta på något som
   inte händer. Ett försök som redovisas som pågående måste finnas i
   protokollet, och det måste kunna lyckas.
3. **Ett tillstånd som inte gick att avgöra som visas som grönt eller
   utelämnas.** I3: tystnad är aldrig ett godkännande. `OBESTÄMT` är den
   regeln på visningens våning.

## Lägena är bryggans sju, plus två som visningen inte klarar sig utan

`28_lagen_och_aterhamtning.md` §1 listar sju lägen. Två till behövs, och de
står i `TILLAGDA_LAGEN` av samma skäl som `forlopp.handelser.TILLAGDA_SORTER`:
ett tillägg till en spec'ad lista ska **synas** i stället för att glida in.

* `OBESTÄMT` — frågan gick inte att besvara ur det underlag som finns. Det är
  inte ett fall och inte ett arbete.
* `BLOCKERAD` — bryggan svarar inte, och orsaken är känd och ofarlig: en modal
  ruta står öppen i VC (§3.6:s undantag, `26_appen.md` A-3). Specen säger att
  det inte får bli `NERE`; utan ett eget ord blev det i stället `ANSLUTEN`,
  vilket är en lögn åt andra hållet.

`BLOCKERAD` bär en gräns som måste stå med: raden `modal oppen` **finns inte i
koden**. Den är spec'ad i `26_appen.md` A-3 och obyggd, och läget kan därför
inte fyras i dag. Det står som en permanent ovisshet i varje visning i stället
för att låtsas vara en förmåga.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Optional, Tuple

# ------------------------------------------------------------- delsystemen

# De tre saker som kan sluta svara mitt i ett uppdrag, var och en med sin egen
# tystnad och sin egen väg tillbaka. Att slå ihop dem till ett "systemet" vore
# att svara "nere" på frågan "vad är det som är nere?".
BRYGGAN = "bryggan"
PLC = "OpenPLC"
MODELLEN = "modellen"
DELSYSTEM = (BRYGGAN, PLC, MODELLEN)

# ----------------------------------------------------------------- lägena

FRANKOPPLAD = "FRÅNKOPPLAD"
ANSLUTEN = "ANSLUTEN"
SIMULERING_IGANG = "SIMULERING IGÅNG"
PROVTAGNING_PAGAR = "PROVTAGNING PÅGÅR"
KO_VANTAR = "KÖ VÄNTAR"
DEGRADERAD = "DEGRADERAD"
NERE = "NERE"

SPECADE_LAGEN = (FRANKOPPLAD, ANSLUTEN, SIMULERING_IGANG, PROVTAGNING_PAGAR,
                 KO_VANTAR, DEGRADERAD, NERE)

OBESTAMT = "OBESTÄMT"
BLOCKERAD = "BLOCKERAD"
TILLAGDA_LAGEN = (OBESTAMT, BLOCKERAD)

LAGEN = SPECADE_LAGEN + TILLAGDA_LAGEN

# Underläget. Det visas ALLTID som ett tillägg, aldrig i stället för ett läge
# (§1.1). Bryggan har nått taket 20 omstarter per minut och slagit av sin egen
# självstart (`pump.begar_omstart`).
UTAN_SJALVSTART = "utan självstart"

# Företrädet när flera gäller samtidigt, uppifrån och ned. Ordningen är
# specens (§1.1) med de två tilläggen inlagda där de hör hemma:
#
#   OBESTÄMT först, därför att "vet inte" aldrig får trängas undan av en
#   gissning. BLOCKERAD före NERE, därför att specen förbjuder övergången till
#   NERE medan en modal står öppen — och en känd, ofarlig orsak till tystnaden
#   är ett annat besked än en död brygga.
FORETRADE = (OBESTAMT, NERE, BLOCKERAD, DEGRADERAD, PROVTAGNING_PAGAR,
             KO_VANTAR, SIMULERING_IGANG, ANSLUTEN, FRANKOPPLAD)

# Lägen där ingenting av det användaren bad om går framåt. En återhämtnings-
# eller framstegsmarkör i något av dem är precis den snurrande symbolen fasens
# grind förbjuder.
STILLA = (FRANKOPPLAD, DEGRADERAD, NERE, BLOCKERAD, OBESTAMT)

# Lägen som betyder att systemet svarade. Bara de får kallas levande, och bara
# efter ett SVAR — aldrig efter en lyckad `connect()` (regel L-1).
LEVANDE = (ANSLUTEN, SIMULERING_IGANG, PROVTAGNING_PAGAR, KO_VANTAR,
           DEGRADERAD)


class Aterhamtningsfel(Exception):
    """Läget går inte att avgöra, eller doktrinen bröts på vägen ut."""


# ---------------------------------------------------------- vägarna tillbaka

@dataclass(frozen=True)
class Vag:
    """En väg tillbaka, och vem som går den.

    `av_operatoren` är inte en detalj: en väg systemet kan gå själv får
    redovisas som ett pågående försök, en väg operatören måste gå får det
    aldrig. Att skriva "återhämtar" om något som väntar på en människa är att
    be henne vänta på sig själv.
    """

    nyckel: str
    text: str
    av_operatoren: bool
    stampel: str

    def rad(self) -> str:
        vem = "du" if self.av_operatoren else "systemet"
        return "%s  [%s, %s]" % (self.text, vem, self.stampel)


MENYVAL2 = Vag(
    "menyval2",
    "Öppna Add-Ons i VC och välj \"VC Assist — starta om bryggan\".",
    True, "MÄTT M-13")
SJALVSTART = Vag(
    "sjalvstart",
    "Bryggan startar om sig själv från kommandots scope.",
    False, "MÄTT M-13 — täcker inte de operationer som monterar ned "
           "skriptmiljön")
VC_OMSTART = Vag(
    "vc_omstart", "Starta om Visual Components.", True, "MÄTT M-13")
LASANDE_EXEC = Vag(
    "lasande_exec",
    "Kör en läsande exec. Bara en lyckad körning rensar flaggan.",
    False, "KOD@HEAD pump._kor")
STANG_MODALEN = Vag(
    "stang_modalen", "Stäng statusrutan i VC, så svarar bryggan igen.",
    True, "ANTAGET — mäts i M-21")
FRIGOR_PORTEN = Vag(
    "frigor_porten",
    "Linux: kör ~/bin/vc-stoppa.sh, som gör wineserver -k och kontrollerar "
    "att porten är fri. Windows: netstat -ano | findstr :8901, avsluta det "
    "PID:et.",
    True, "MÄTT M-13 på Linux; OPRÖVAT på Windows (M-44)")
LAS_OM_TOKEN = Vag(
    "las_om_token",
    "Tjänsten läser om ~/vc_assist_token och försöker en gång till.",
    False, "KOD@HEAD")
ANSLUT_IGEN = Vag(
    "anslut_igen", "Tjänsten öppnar en ny anslutning till bryggan.",
    False, "KOD@HEAD klient.anslut")
STARTA_OPENPLC = Vag(
    "starta_openplc",
    "Starta OpenPLC v4 på den adress som är konfigurerad, och läs in koden "
    "igen.",
    True, "ANTAGET — ingen mätning av OpenPLC:s omstart finns")
NY_KORNING = Vag(
    "ny_korning",
    "Kör uppdraget igen. Det som gjordes står kvar i scenen; planen läses om "
    "mot den (regel L-3).",
    True, "KOD@HEAD — scenfingeravtrycket i 24_samtalsloopen.md §5")

VAGAR = (MENYVAL2, SJALVSTART, VC_OMSTART, LASANDE_EXEC, STANG_MODALEN,
         FRIGOR_PORTEN, LAS_OM_TOKEN, ANSLUT_IGEN, STARTA_OPENPLC, NY_KORNING)

# --------------------------------------------------- kan försöket lyckas?

# Tre svar, aldrig två. Ett `okänt` som klumpas ihop med `ja` blir ett löfte,
# och ett som klumpas ihop med `nej` slänger en väg som kanske fungerar.
# Orden är valda så att INGET är en delsträng av ett annat. Det är inte
# stilistik: grinden letar efter dem i en främmande renderares text, och den
# första formuleringen — `okänt om den kan lyckas` — bar `kan lyckas` inuti
# sig. En grind som letar efter `kan lyckas` hade då sagt ja om en väg som
# stod som okänd, alltså gjort ett okänt till ett löfte i just det steg som
# finns för att förhindra det. `test_ingen_kanskap_ar_delstrang_av_en_annan`
# håller regeln.
KAN_JA = "kan lyckas"
KAN_NEJ = "kan inte lyckas"
KAN_OKAND = "okänt om den hjälper"
KANSKAP = (KAN_JA, KAN_NEJ, KAN_OKAND)


# ------------------------------------------------------------- orsakerna

@dataclass(frozen=True)
class Orsak:
    """Varför något slutade svara, i klarspråk, med sin härkomst.

    `text` är den mening användaren läser. Den ska gå att förstå ensam, utan
    att först läsa specen: `operatoren-behover-klarsprak`. `stampel` säger var
    påståendet kommer ifrån, och den står i visningen — en orsak utan
    härkomst är en gissning som fått en ram.
    """

    nyckel: str
    delsystem: str
    text: str
    stampel: str
    vagar: Tuple[Vag, ...]
    # Den väg systemet självt försöker. `None` betyder att INGENTING försöker
    # igen, och det ska stå med de orden.
    automatisk: Optional[Vag] = None


def _orsak(*a, **kw) -> Orsak:
    o = Orsak(*a, **kw)
    if o.delsystem not in DELSYSTEM:
        raise Aterhamtningsfel("unknown subsystem %r" % (o.delsystem,))
    if o.automatisk is not None and o.automatisk not in o.vagar:
        raise Aterhamtningsfel(
            "orsaken %s försöker automatiskt en väg som inte står bland dess "
            "vägar tillbaka" % o.nyckel)
    if o.automatisk is not None and o.automatisk.av_operatoren:
        raise Aterhamtningsfel(
            "orsaken %s redovisar en väg operatören måste gå som ett "
            "automatiskt försök" % o.nyckel)
    return o


SKRIPTBETEENDE = _orsak(
    "skriptbeteende", BRYGGAN,
    "Koden skapade ett skriptbeteende. Simuleringen stoppades och bryggan gick "
    "ned. Det finns ingen väg tillbaka utan att du startar om VC.",
    "MÄTT M-13", (VC_OMSTART,))

SPARAD_LAYOUT = _orsak(
    "sparad_layout", BRYGGAN,
    "Layouten sparades. Det stoppar simuleringen, och pumpen bor i "
    "simuleringen. Posten kördes, men något utfall kommer aldrig.",
    "MÄTT M-13", (MENYVAL2, VC_OMSTART))

OPERATOREN_STOPPADE = _orsak(
    "operatoren_stoppade", BRYGGAN,
    "Simuleringen stoppades i VC. Pumpen bor i simuleringen och slutade ticka "
    "i samma ögonblick.",
    "MÄTT M-08", (SJALVSTART, MENYVAL2, VC_OMSTART), automatisk=SJALVSTART)

VC_AVSLUTADES = _orsak(
    "vc_avslutades", BRYGGAN,
    "Visual Components avslutades. Anslutningen bröts av att processen "
    "försvann.",
    "31_brygga_protokoll.md, ECONNRESET", (VC_OMSTART,))

SOCKET_BRUTEN = _orsak(
    "socket_bruten", BRYGGAN,
    "Anslutningen till bryggan bröts, men bryggan svarar fortfarande. Bara "
    "vår ände tappade den.",
    "KOD@HEAD klient.anslut", (ANSLUT_IGEN,), automatisk=ANSLUT_IGEN)

PORT_UPPTAGEN = _orsak(
    "port_upptagen", BRYGGAN,
    "Ingenting lyssnar på porten. En kvarlevande process kan hålla den utan "
    "att någon brygga finns bakom.",
    "MÄTT M-13, sidofynd", (FRIGOR_PORTEN, VC_OMSTART))

TOKEN_GAMMALT = _orsak(
    "token_gammalt", BRYGGAN,
    "Tokenet är från en tidigare VC-session. Bryggan skriver om det vid varje "
    "start.",
    "KOD@HEAD", (LAS_OM_TOKEN,), automatisk=LAS_OM_TOKEN)

TIMEOUT = _orsak(
    "timeout", BRYGGAN,
    "En körning överskred sin tidsgräns. Bryggans tillstånd är okänt tills en "
    "läsande körning lyckats — det betyder inte att den är trasig.",
    "KOD@HEAD pump._kor", (LASANDE_EXEC,))

MODAL_OPPEN = _orsak(
    "modal_oppen", BRYGGAN,
    "En statusruta står öppen i VC. Bryggan svarar inte medan den står öppen.",
    "ANTAGET — raden modal oppen är spec'ad i 26_appen.md A-3 och finns inte "
    "i koden; mäts i M-21",
    (STANG_MODALEN,))

KROKEN_FYRADE_INTE = _orsak(
    "kroken_fyrade_inte", BRYGGAN,
    "Tillägget startade aldrig. VC startade normalt och sa ingenting — det är "
    "vad fel Python N-nivå ser ut som.",
    "MÄTT M-01", (VC_OMSTART,))

MODULEN_KORDES_ALDRIG = _orsak(
    "modulen_kordes_aldrig", BRYGGAN,
    "Kommandot laddades men modulens kropp kördes aldrig. Ett syntaxfel i "
    "tillägget ser exakt så ut, och VC säger ingenting.",
    "MÄTT M-09", (VC_OMSTART,))

SKRIPTET_KOMPILERAR_INTE = _orsak(
    "skriptet_kompilerar_inte", BRYGGAN,
    "Brygg-skriptet gick inte att kompilera. Bootloggen bär raden med "
    "radnummer och tre rader sammanhang.",
    "MÄTT M-06, M-09", (VC_OMSTART,))

PLC_SVARAR_INTE = _orsak(
    "plc_svarar_inte", PLC,
    "OpenPLC svarade inte inom tidsgränsen. Kopplaren räknar raka fel och ger "
    "upp vid tredje — den mal inte vidare mot en död PLC.",
    "MÄTT M-39", (STARTA_OPENPLC,))

KOPPLAREN_GAV_UPP = _orsak(
    "kopplaren_gav_upp", PLC,
    "Kopplaren gav upp efter tre raka fel. Ingenting försöker igen, och det "
    "är avsiktligt: en slinga som mal vidare mot en död PLC ser ut att arbeta.",
    "MÄTT M-39, kopplare.MAX_RAKA_FEL", (STARTA_OPENPLC, NY_KORNING))

MODELLEN_TOG_SLUT = _orsak(
    "modellen_tog_slut", MODELLEN,
    "Modellen slutade svara mitt i en reparation. Varvet blev aldrig klart, "
    "och de grindar som skulle ha kört efter det kördes aldrig.",
    "KOD@HEAD modellklient.Modellfel", (NY_KORNING,))

MODELLEN_TYSTNADE = _orsak(
    "modellen_tystnade", MODELLEN,
    "Modellen svarade varken text eller anrop. Slingan stannade i stället för "
    "att köra ett tomt varv.",
    "KOD@HEAD reparation.UTFALL_TYSTNAD", (NY_KORNING,))

REPARATIONSTAKET = _orsak(
    "reparationstaket", MODELLEN,
    "Reparationsslingan nådde sitt tak utan att grindarna höll. Fler varv "
    "hade inte gett en annan dom.",
    "KOD@HEAD reparation.UTFALL_TAK", (NY_KORNING,))

# Orsaken som INTE gick att avgöra. Den är inte en tom sträng och inte ett
# utelämnande: N-5 i `28_lagen_och_aterhamtning.md` säger att panelen aldrig
# får säga att bryggan är nere utan att säga varför, och det ärliga svaret när
# stegen inte räckte är att säga just det.
OKAND = _orsak(
    "okand", BRYGGAN,
    "Systemet svarar inte, och orsaken gick inte att avgöra ur loggarna. "
    "Stegen nedan visar hur långt de kom och var de tog slut.",
    "N-5, 28_lagen_och_aterhamtning.md", ())

ORSAKER = (SKRIPTBETEENDE, SPARAD_LAYOUT, OPERATOREN_STOPPADE, VC_AVSLUTADES,
           SOCKET_BRUTEN, PORT_UPPTAGEN, TOKEN_GAMMALT, TIMEOUT, MODAL_OPPEN,
           KROKEN_FYRADE_INTE, MODULEN_KORDES_ALDRIG,
           SKRIPTET_KOMPILERAR_INTE, PLC_SVARAR_INTE, KOPPLAREN_GAV_UPP,
           MODELLEN_TOG_SLUT, MODELLEN_TYSTNADE, REPARATIONSTAKET, OKAND)

ORSAK_UR_NYCKEL: Dict[str, Orsak] = MappingProxyType(
    dict((o.nyckel, o) for o in ORSAKER))


# ------------------------------------------- tabellen som avgör ett försök

# ETT ställe där frågan "kan det här försöket lyckas?" besvaras, och det är
# oskrivbart. Samma form som `utforare.OP_FOR_EFFECT`, och av samma skäl: en
# fråga som besvaras på två ställen besvaras förr eller senare olika, och den
# som besvarar den fel här lovar en användare något som aldrig kommer.
#
# Nyckeln är (orsakens nyckel, vägens nyckel). Saknas paret är svaret
# KAN_OKAND — aldrig KAN_JA. Fail-closed (I3).
_KAN: Dict[Tuple[str, str], str] = {
    # De två mätta dödarna. `M-13`: handlaren i kommandots scope täcker de fall
    # där skriptmiljön INTE monteras ned, och de här två monterar ned den.
    ("skriptbeteende", "sjalvstart"): KAN_NEJ,
    ("skriptbeteende", "vc_omstart"): KAN_JA,
    ("skriptbeteende", "menyval2"): KAN_NEJ,
    ("sparad_layout", "sjalvstart"): KAN_NEJ,
    ("sparad_layout", "vc_omstart"): KAN_JA,
    # Menyval 2 gör samma sak som självstarten, men från operatörens hand. Att
    # den räcker EFTER en app.save() är inte mätt, och specen listar den ändå
    # som en väg (§3.6 steg 3). Den står därför som okänd i stället för som
    # ett löfte.
    ("sparad_layout", "menyval2"): KAN_OKAND,
    ("operatoren_stoppade", "sjalvstart"): KAN_OKAND,
    ("operatoren_stoppade", "menyval2"): KAN_JA,
    ("operatoren_stoppade", "vc_omstart"): KAN_JA,
    ("vc_avslutades", "vc_omstart"): KAN_JA,
    ("socket_bruten", "anslut_igen"): KAN_JA,
    ("port_upptagen", "frigor_porten"): KAN_JA,
    ("port_upptagen", "vc_omstart"): KAN_OKAND,
    ("token_gammalt", "las_om_token"): KAN_JA,
    ("timeout", "lasande_exec"): KAN_JA,
    ("modal_oppen", "stang_modalen"): KAN_OKAND,
    ("kroken_fyrade_inte", "vc_omstart"): KAN_NEJ,
    ("modulen_kordes_aldrig", "vc_omstart"): KAN_NEJ,
    ("skriptet_kompilerar_inte", "vc_omstart"): KAN_NEJ,
    ("plc_svarar_inte", "starta_openplc"): KAN_OKAND,
    ("kopplaren_gav_upp", "starta_openplc"): KAN_OKAND,
    ("kopplaren_gav_upp", "ny_korning"): KAN_OKAND,
    ("modellen_tog_slut", "ny_korning"): KAN_OKAND,
    ("modellen_tystnade", "ny_korning"): KAN_OKAND,
    ("reparationstaket", "ny_korning"): KAN_NEJ,
    ("okand", "vc_omstart"): KAN_OKAND,
}
KAN = MappingProxyType(_KAN)


def kan_lyckas(orsak: Orsak, vag: Vag,
               utan_sjalvstart: bool = False) -> str:
    """Kan den här vägen lyckas för den här orsaken?

    `utan_sjalvstart` är inte en detalj i marginalen. Har bryggan slagit av sin
    egen omstart efter 20 försök på en minut kan självstarten inte lyckas —
    oavsett orsak, och oavsett vad tabellen säger. En omstartsstorm är mätt
    till tusentals varv i sekunden (M-13), och spärren finns just för att den
    aldrig ska upprepas. Ett försök som redovisas som pågående medan spärren
    är slagen är en väntan på ingenting.
    """
    if not isinstance(orsak, Orsak):
        raise Aterhamtningsfel("kan_lyckas takes an Orsak, not %s"
                               % type(orsak).__name__)
    if not isinstance(vag, Vag):
        raise Aterhamtningsfel("kan_lyckas takes a Vag, not %s"
                               % type(vag).__name__)
    if utan_sjalvstart and vag is SJALVSTART:
        return KAN_NEJ
    return KAN.get((orsak.nyckel, vag.nyckel), KAN_OKAND)


def vagarna(orsak: Orsak, utan_sjalvstart: bool = False):
    """Vägarna tillbaka för en orsak, var och en med sin kanskap."""
    return tuple((v, kan_lyckas(orsak, v, utan_sjalvstart))
                 for v in orsak.vagar)


__all__ = [
    "ANSLUTEN", "ANSLUT_IGEN", "Aterhamtningsfel", "BLOCKERAD", "BRYGGAN",
    "DEGRADERAD", "DELSYSTEM", "FORETRADE", "FRANKOPPLAD", "FRIGOR_PORTEN",
    "KAN", "KANSKAP", "KAN_JA", "KAN_NEJ", "KAN_OKAND", "KOPPLAREN_GAV_UPP",
    "KO_VANTAR", "KROKEN_FYRADE_INTE", "LAGEN", "LASANDE_EXEC", "LAS_OM_TOKEN",
    "LEVANDE", "MENYVAL2", "MODAL_OPPEN", "MODELLEN", "MODELLEN_TOG_SLUT",
    "MODELLEN_TYSTNADE", "MODULEN_KORDES_ALDRIG", "NERE", "NY_KORNING",
    "OBESTAMT", "OKAND", "OPERATOREN_STOPPADE", "ORSAKER", "ORSAK_UR_NYCKEL",
    "Orsak", "PLC", "PLC_SVARAR_INTE", "PORT_UPPTAGEN", "PROVTAGNING_PAGAR",
    "REPARATIONSTAKET", "SIMULERING_IGANG", "SJALVSTART", "SKRIPTBETEENDE",
    "SKRIPTET_KOMPILERAR_INTE", "SOCKET_BRUTEN", "SPARAD_LAYOUT",
    "SPECADE_LAGEN", "STANG_MODALEN", "STARTA_OPENPLC", "STILLA",
    "TILLAGDA_LAGEN", "TIMEOUT", "TOKEN_GAMMALT", "UTAN_SJALVSTART",
    "VAGAR", "VC_AVSLUTADES", "VC_OMSTART", "Vag", "kan_lyckas", "vagarna",
]
