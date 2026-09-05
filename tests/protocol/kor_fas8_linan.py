# -*- coding: utf-8 -*-
"""Fas 8: KOMPOSITIONEN. Tva stationer pa en lina, och felen som bara uppstar
tillsammans.

Fas 7 stangde med en station: grind 1-5 grona, ogat PASS, L1-guld (M-49,
M-50). Fas 8:s kontrakt i docs/spec/70_faser.md ar "Guld per station, sedan
guld for linan. L2".

    matare -> ST8_Bana1 [station A] -> ST8_Bana2 [station B] -> av i anden

Det svara ar inte att kora tva stationer. Det ar att fanga fel som BARA
uppstar tillsammans. Korningen kor darfor varje program i TRE konfigurationer:

    LINJE   bada stationernas block i samma PLC-program
    A       bara station A:s block, egen signalkarta, egen uppladdning
    B       bara station B:s block

Ett kompositionsfel ar ett fall som ogat FALLER i LINJE och SLAPPER IGENOM i
bade A och B. Syns felet i en station for sig ar det inget kompositionsfel -
da ar det ett fas 7-fel, och det ar redan matt.

## Vad som ar VC:s och vad som ar tjanstens

Precis som i fas 7 (M-49) bor givarna och stalldonen i ANLAGGNING, som kors
inne i VC genom godkannandekon en gang per varv. Den ar en MODELL av
processen, inte en del av losningen: den laser produkternas verkliga
banavstand (getPathDistance) och skriver banornas verkliga fart. Ingen
sekvenslogik bor dar.

Tva ting i anlaggningen ar NYA for fas 8 och deklareras har, fore
losningarna:

1. **Tva banor i serie.** MATT i den har korningens forsta steg (M-73): en
   produkt gar over kopplingen fran ST8_Bana1 till ST8_Bana2 och banavstandet
   raknas om mot den nya banan. M-41 och M-67 lamnade bada det oprovat.
2. **En DELAD utmatare.** Stationerna delar ETT utmatningsdon. Kommenderar
   bada det samtidigt kan det inte tjana bagge: anlaggningen later da INGEN
   av dem fa det, halter bada banorna stilla, och RAPPORTERAR konflikten i
   stallet for att tiga (samma hallning som M-49:s bromskonflikt).

    python3 tests/protocol/kor_fas8_linan.py --strucpp <npm-katalog> \\
        --runtime-include <include> [--fall HEL,K1] [--konfig LINJE,A,B]
"""
import argparse
import json
import os
import subprocess
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import oga_analys as A                                      # noqa: E402
from vc_assist_svc import guldgrind                         # noqa: E402
from vc_assist_svc.api_index import bygg_validator          # noqa: E402
from vc_assist_svc.byggrecept import recept as R            # noqa: E402
from vc_assist_svc.klient import Klient                     # noqa: E402
from vc_assist_svc.plc import opcuakonfig, paket            # noqa: E402
from vc_assist_svc.plc import stationsgrind as S            # noqa: E402
from vc_assist_svc.plc.kopplare import Kopplare             # noqa: E402
from vc_assist_svc.plc.openplc import OpenPlcV4             # noqa: E402
from vc_assist_svc.plc.signalkarta import karta_av_rader    # noqa: E402
from vc_assist_svc.plc.skelett import Skelett               # noqa: E402

LINJE = "ST8"
TOKEN = os.path.expanduser("~/.wine-vc-test/drive_c/users/anton/vc_assist_token")
STARTSKRIPT = os.path.expanduser(
    "~/.wine-vc-test/drive_c/users/anton/vc_assist_startskript.py")

# ---- linjen ---------------------------------------------------------------
#
# Talen ar LINJENS, inte trosklar: de ar det korningen bad om, och grinden
# jamfor det uppmatta mot dem i stallet for att anta dem.
BANDFART_MM_S = 250.0        # M-41 matte 250,0000 mm/s over 25 par.
UTMATNINGSFART_MM_S = 600.0  # Satt av M-73.
BANLANGD_MM = 3000.0
MATARLANGD_MM = 400.0
LINJE_Y_MM = 8000.0          # vid sidan av M-41 (y=0,2000,4000) och fas 7 (y=6000)

# Matarintervallet ar VALT sa att stationernas faser MOTS. Skalet star i M-73:
# en serielina vars takt ar langre an bada stationernas upptagenhet stor
# aldrig pa varandra, och da prover den ingenting av kompositionen. Talet ar
# alltsa en RIGGPARAMETER, inte ett facit.
MATARINTERVALL_S = 8.0       # Satt av M-73.

# Givarna: punkter PA sin bana, inte i varlden. Banavstandet ar VC:s egen
# matning (getPathDistance) och slapar inte ett scenuppdateringssteg (M-11).
# Lagena ar valda sa att overlamningen fran A till B tar 2,6 s: station A star
# vid slutet av sin bana, station B vid borjan av sin.
GIVARE_A_D_MM = 2400.0       # Satt av M-73.
GIVARE_B_D_MM = 1400.0       # Satt av M-73.
GIVARE_HALVBREDD_MM = 150.0  # Satt av M-73.

# Bromsklackarna: det enda stationerna kommenderar som ogat kan se RORA sig.
BROMS_INNE_Y_MM = LINJE_Y_MM - 500.0
BROMS_UTE_Y_MM = LINJE_Y_MM - 300.0
BROMS_STEG_MM = 30.0         # hur langt klacken hinner per varv

# Den DELADE utmataren: ett don, tva stationer. Den star vid den station som
# far den, och i mitten nar ingen begar den.
UTMATARE_X_A_MM = MATARLANGD_MM + GIVARE_A_D_MM
UTMATARE_X_B_MM = MATARLANGD_MM + BANLANGD_MM + GIVARE_B_D_MM
UTMATARE_X_HEM_MM = 0.5 * (UTMATARE_X_A_MM + UTMATARE_X_B_MM)
UTMATARE_Y_MM = LINJE_Y_MM + 500.0
UTMATARE_STEG_MM = 400.0     # Satt av M-73.

# ---- PLC:ns egna tal ------------------------------------------------------
PROCESSTID = "T#2s"
PROCESSTID_S = 2.0
UTMATNINGSTID = "T#1s"
UTMATNINGSTID_S = 1.0

# ---- korningens perturbation ----------------------------------------------
PAUS_TIDIGAST_S = 25.0      # Satt av M-50.
PAUS_FORDROJNING_S = 0.2    # Satt av M-50.
PAUS_LANGD_S = 1.0

# ---- signalkartan ---------------------------------------------------------
#
# Adresserna ar FASTA per signal, ocksa i en enstationskonfiguration. Skalet:
# en station som kors for sig ska ha exakt den adress den har i linan, annars
# ar kontrollkorningen inte samma station.
RADER_A = [
    ("ST8A_Givare", "Puls", "a_givare", "BOOL", "TILL_PLC", "%IX0.0",
     False, "fotocellen vid station A, banavstand %.0f mm" % GIVARE_A_D_MM),
    ("ST8A_Don", "Stopp", "a_stopp", "BOOL", "FRAN_PLC", "%QX0.0",
     False, "station A: bromsklacken ut, bana 1 stannar"),
    ("ST8A_Don", "Slapp", "a_slapp", "BOOL", "FRAN_PLC", "%QX0.1",
     False, "station A: begar den DELADE utmataren"),
]
RADER_B = [
    ("ST8B_Givare", "Puls", "b_givare", "BOOL", "TILL_PLC", "%IX0.1",
     False, "fotocellen vid station B, banavstand %.0f mm" % GIVARE_B_D_MM),
    ("ST8B_Don", "Stopp", "b_stopp", "BOOL", "FRAN_PLC", "%QX0.2",
     False, "station B: bromsklacken ut, bana 2 stannar"),
    ("ST8B_Don", "Slapp", "b_slapp", "BOOL", "FRAN_PLC", "%QX0.3",
     False, "station B: begar den DELADE utmataren"),
]
RADER_LINJE = [
    ("ST8_Linje", "Kor", "kor", "BOOL", "TILL_PLC", "%IX0.2",
     False, "linjens driftvaljare"),
    ("ST8_Linje", "Nod", "nodstopp", "BOOL", "TILL_PLC", "%IX0.3",
     True, "nodstoppet ar utlost - skyddad (I15)"),
]

KONFIGURATIONER = ("LINJE", "A", "B")


def karta(konfig):
    rader = list(RADER_LINJE)
    if konfig in ("LINJE", "A"):
        rader = RADER_A + rader
    if konfig in ("LINJE", "B"):
        rader = rader + RADER_B
    return karta_av_rader(LINJE, rader)


# Arbetsvariablerna deklareras for BADA stationerna i alla konfigurationer.
# Skalet ar de trasiga fallen K1 och K2: de bytar en stations INSTANS mot den
# andras, och en enstationskorning maste kunna kora fallets EGEN text. En
# odeklarerad instans hade tvingat fram en omskrivning, och da vore
# kontrollkorningen inte langre samma program. Oanvanda VAR-rader ar giltig ST
# och ror ingen signal, sa grind 3 ser dem inte.
DEKLARATIONER = "\n".join(
    ["VAR"]
    + ["    %s_laget : INT;\n    %s_flank : R_TRIG;\n"
       "    %s_tid : TON;\n    %s_utid : TON;" % (p, p, p, p)
       for p in ("a", "b")]
    + ["END_VAR"])


# Scenkoden ar formen verktygsmallarna sjalva skriver: getApplication() INLINE.
# MATT (M-48): med ett fritt `app` kontrollerar grind 4 noll namn.
SCENKOD = ("app = getApplication()\n"
           "bana1 = app.findComponent('ST8_Bana')\n"
           "bana2 = app.findComponent('ST8_Bana2')\n"
           "path1 = bana1.findBehaviour('Path')\n"
           "path2 = bana2.findBehaviour('Path')\n")


# ---- ST-kropparna ---------------------------------------------------------
#
# Kroppen byggs av BITAR: en inledning, ett block per station och en
# forreglingsrad per station. Ett trasigt fall byter EN bit, och varje byte
# bar ett `assert` som faller om biten bytt form - en trasig fixtur som tyst
# blir hel igen ar varre an ingen fixtur alls (matt i M-41, dar en fixtur
# lakte sig sjalv).
#
# Att kroppen byggs av bitar i stallet for att str.replace:as i ett stycke ar
# ocksa det som gor ENSTATIONSKORNINGEN mojlig: konfigurationen A ar samma
# bitar utan station B:s block - alltsa exakt fas 7:s uppstallning.

def _reset(pre):
    """Vad en station gor nar linan star: slapper den DELADE utmataren.

    Bromsen ror den INTE - en pausad lina far inte slappa en klamd produkt
    (M-50). Och timrarna nollstalls inte: en TON som inte anropas star kvar
    dar den star, sa processen fortsatter dar den var i stallet for att borja
    om. Nollstallde man dem blev den perturberade cykeln pausen PLUS en hel
    processtid langre, och da maste varje fonster vidgas med lika mycket.
    """
    return "        %s_slapp := FALSE;\n" % pre


def _block(pre, villkor, inst=None, stopprad=None):
    """En stations sekvens.

    `villkor` ar det som utover processtiden maste galla for att stationen
    ska fa lamna processlaget och ta den DELADE utmataren.
    `inst` ar {"flank": p, "laget": p, "tid": p}: prefixet pa var och en av
    stationens ARBETSINSTANSER. De ar skilda fran `pre` bara i de trasiga fall
    som later tva stationer dela en instans.
    """
    i = dict((n, pre) for n in ("flank", "laget", "tid"))
    i.update(inst or {})
    # Bromsen skrivs EN gang per scan, inne i sitt eget lage. En andra
    # skrivning efter CASE:t hade varit en DUBBELSKRIVNING, och grind 2 faller
    # den (F7) - matt i den har korningens forsta forsok. Forreglingen mellan
    # bromsen och utmatningen ar darfor STRUKTURELL: de bor i olika lagen.
    stopp = "TRUE" if stopprad is None else stopprad
    return ("        %(f)s_flank(CLK := %(p)s_givare);\n"
            "        CASE %(l)s_laget OF\n"
            "        0:\n"
            "            IF %(f)s_flank.Q THEN\n"
            "                %(l)s_laget := 1;\n"
            "            END_IF;\n"
            "        1:\n"
            "            %(p)s_stopp := %(s)s;\n"
            "            %(t)s_tid(IN := TRUE, PT := %(pt)s);\n"
            "            IF %(t)s_tid.Q%(v)s THEN\n"
            "                %(l)s_laget := 2;\n"
            "            END_IF;\n"
            "        2:\n"
            "            %(p)s_stopp := FALSE;\n"
            "            %(p)s_slapp := TRUE;\n"
            "            %(t)s_tid(IN := FALSE, PT := %(pt)s);\n"
            "            %(t)s_utid(IN := TRUE, PT := %(ut)s);\n"
            "            IF %(t)s_utid.Q THEN\n"
            "                %(l)s_laget := 3;\n"
            "            END_IF;\n"
            "        3:\n"
            "            %(p)s_slapp := FALSE;\n"
            "            %(t)s_utid(IN := FALSE, PT := %(ut)s);\n"
            "            %(l)s_laget := 0;\n"
            "        END_CASE;\n"
            % {"p": pre, "f": i["flank"], "l": i["laget"], "t": i["tid"],
               "pt": PROCESSTID, "ut": UTMATNINGSTID, "v": villkor,
               "s": stopp})


# LINJEVILLKORET: ingen station tar den delade utmataren medan den andra har
# den. Villkoret ar SYMMETRISKT, och det ar mätt varfor.
#
# Forsta forsoket lade turordningen bara pa station B, med skalet att en
# enkelriktad prioritet inte kan lasa sig. Den holl sa lange B:s timer gick ut
# EFTER A:s. Efter driftpausen sköt fasen sig sa att B:s gick ut forst, B tog
# donet - och A, som inte hade nagot villkor alls, tog det ocksa. Ogat matte
# overlappet och fallde den hela losningen, med ratta.
#
# Symmetriskt kan det inte lasa sig, och skalet ar STRUKTURELLT: en station
# som redan ar i utmatningslaget lamnar det pa sin EGEN timer och vantar
# aldrig pa nagon. Den som vantar vantar alltsa alltid pa nagot som tar slut.
# Ett samtidigt utgangsvillkor avgors av SCANORDNINGEN: station A:s block kors
# forst och stiger in i laget, och station B ser det redan i samma scan.
#
# Villkoret laser den andra stationens LAGE, inte dess utgang. Skillnaden ar
# matt, och den var forsta forsokets fel: `AND NOT b_slapp` las ett STALLDON
# som satts en scan EFTER beslutet. Bada stationerna sag darfor ett lagt
# `slapp` i samma scan, bada steg in i utmatningslaget, och i nasta scan gick
# bada utgangarna hoga samtidigt. Ett villkor som fragar efter foljden av ett
# beslut i stallet for efter beslutet sjalvt slapper igenom precis den
# samtidighet det skulle hindra.
LINJEVILLKOR = {"a": " AND b_laget <> 2", "b": " AND a_laget <> 2"}

STATIONER = {"LINJE": ("a", "b"), "A": ("a",), "B": ("b",)}


def _bitar():
    """Den hela losningens bitar, per konfiguration oberoende."""
    return {"villkor": dict(LINJEVILLKOR),
            "instans": {"a": {}, "b": {}},
            "stopprad": lambda pre, med: "TRUE"}


def kropp(bitar, konfig):
    """Sy ihop kroppen for en konfiguration."""
    med = STATIONER[konfig]
    ut = ["    IF NOT kor OR nodstopp THEN\n"]
    for pre in med:
        ut.append(_reset(pre))
    ut.append("    ELSE\n")
    for pre in med:
        villkor = bitar["villkor"][pre]
        # Ett villkor som pekar pa den ANDRA stationens signal har ingen
        # referent i en enstationskonfiguration. Det tas bort, och det ar
        # inte en uppmjukning: stationen kors da precis som i fas 7.
        for annan in ("a", "b"):
            if annan not in med:
                villkor = villkor.replace(" AND %s_laget <> 2" % annan, "")
                villkor = villkor.replace(" AND NOT %s_givare" % annan, "")
        ut.append(_block(pre, villkor, bitar["instans"][pre],
                         bitar["stopprad"](pre, med)))
    ut.append("    END_IF;\n")
    text = "".join(ut)
    for annan in ("a", "b"):
        if annan in med:
            continue
        for sig in ("givare", "stopp", "slapp"):
            assert "%s_%s" % (annan, sig) not in text, (
                "konfiguration %s ror station %s:s signal %s"
                % (konfig, annan.upper(), sig))
    return text


# ---- de trasiga fallen ----------------------------------------------------
#
# Vart och ett ar EN andring mot den hela losningen, och var och en ar ett fel
# som INTE kan finnas nar stationen kors for sig. Det ar hela poangen med L2:
# syns felet i en station ar det inget kompositionsfel.
#
# Andringarna ar av tva slag, och skillnaden ar viktig for beviset:
#
#   INSTANS  fallet later stationerna dela en arbetsvariabel (K1, K2). Texten
#            ar DENSAMMA i alla tre konfigurationerna - enstationskorningen
#            kor fallets egen kod, och delningen har da bara en delagare.
#   VILLKOR  fallet ror ett villkor eller en rad som namner den ANDRA
#            stationens signal (K3, K4, K5). I en enstationskonfiguration har
#            den ingen referent, och kroppen reduceras da till den hela
#            losningens - vilket ar precis pastaendet: felet FINNS inte i en
#            station for sig. Korningen kontrollerar reduktionen mekaniskt.

def _fixtur_K1(b):
    """Delad tillstandsvariabel: station B:s block raknar i A:s `a_laget`.

    Klipp-och-klistra-felet: blocket kopieras, signalerna byts, men
    tillstandsvariabeln glomms. Ensam ar stationen orord - det finns ingen
    andra lasare, och `a_laget` ar da bara ett annat namn pa `b_laget`.
    Tillsammans driver bada stationernas givare SAMMA tillstandsmaskin.
    """
    assert b["instans"]["b"] == {}
    b["instans"]["b"] = {"laget": "a"}
    return b


def _fixtur_K2(b):
    """Delad flankdetektor: bada stationerna anropar samma R_TRIG.

    En R_TRIG som anropas TVA ganger per scan med olika CLK ger vid det andra
    anropet Q = CLK AND NOT (den forsta CLK:n), och vid det forsta anropet i
    nasta scan Q = CLK AND NOT (den andras CLK). Ensam anropas den en gang
    per scan och ar da en riktig flank - det ar precis fas 7:s HEL-kropp.
    """
    assert b["instans"]["b"] == {}
    b["instans"]["b"] = {"flank": "a"}
    return b


def _fixtur_K3(b):
    """Den delade utmataren utan turordning: bada stationerna far ta den nar
    de vill.

    Ensam har ingen station nagon att sla sig med. Tillsammans begar de den
    samtidigt, och ETT don kan inte tjana tva stationer.
    """
    assert b["villkor"] == LINJEVILLKOR
    b["villkor"] = {"a": "", "b": ""}
    return b


def _fixtur_K4(b):
    """Forreglingen skriven for LINAN i stallet for per station.

    Bromsen ska sta ute sa lange stationen processar och slappa nar
    UTMATNINGEN gar. Har slapper den nar NAGON av stationernas utmatning gar.
    Inne i en station haller den precis lika bra - bromsen och stationens egen
    utmatning kan fortfarande inte vara hoga samtidigt - men mellan
    stationerna ar den fel: station B:s broms slapper mitt i B:s process
    darfor att station A matar ut, och B:s produkt gar ifran den obehandlad.
    Med EN station i programmet ar raden tecken for tecken den hela
    losningens.
    """
    def korsad(pre, med):
        andra = [p for p in med if p != pre]
        if not andra:
            return "TRUE"
        return " AND ".join(["NOT %s_slapp" % p for p in andra])
    assert korsad("a", ("a",)) == "TRUE"
    assert korsad("b", ("b",)) == "TRUE"
    assert korsad("b", ("a", "b")) == "NOT a_slapp"
    b["stopprad"] = korsad
    return b


def _fixtur_K5(b):
    """Station A slapper inte sin produkt forran station B:s zon ar tom.

    "Lamna inte ifran dig till en upptagen station" later som en rimlig regel,
    och ensam ar den gratis - `b_givare` finns da inte i kartan alls. I linan
    ar den hog en stor del av takten, och station A blir staende med bromsen
    ute: kon vaxer uppstroms och linan mattas.
    """
    assert b["villkor"]["a"] == LINJEVILLKOR["a"]
    b["villkor"]["a"] = LINJEVILLKOR["a"] + " AND NOT b_givare"
    return b


FALL = [
    ("HEL", lambda b: b, "den rimliga losningen for linan", True),
    ("K1", _fixtur_K1, "delad tillstandsvariabel mellan stationerna", False),
    ("K2", _fixtur_K2, "delad flankdetektor mellan stationerna", False),
    ("K3", _fixtur_K3, "den delade utmataren utan turordning", False),
    ("K4", _fixtur_K4, "forregling som haller inom en station men korsar", False),
    ("K5", _fixtur_K5, "station A vantar pa station B:s zon och mattar linan", False),
]
FIXTURSLAG = {"HEL": "-", "K1": "INSTANS", "K2": "INSTANS", "K3": "VILLKOR",
              "K4": "VILLKOR", "K5": "VILLKOR"}


def kroppar(fallnamn):
    """{konfig: ST-kropp} for ett fall."""
    fixtur = dict((n, f) for n, f, _v, _p in FALL)[fallnamn]
    return dict((k, kropp(fixtur(_bitar()), k)) for k in KONFIGURATIONER)


def reduktionen(fallnamn):
    """Vilka enstationskonfigurationer som ar tecken for tecken den hela
    losningens. Det ar HALVA beviset for att fallet ar ett kompositionsfel:
    det som inte gar att skriva med en station kan inte fallas i en."""
    hel = kroppar("HEL")
    egen = kroppar(fallnamn)
    return dict((k, egen[k] == hel[k]) for k in KONFIGURATIONER)


# ---- ogats plan -----------------------------------------------------------
#
# Facit, deklarerat FORE losningarna. Talen ar linjens krav, inte matta
# trosklar, och de star har - pa ett stalle - sa att alla fall doms av exakt
# samma facit i exakt samma konfigurationer.
#
# TVA KLOCKOR. PLC:ns timers rakar i VAGGKLOCKA; ogats serie ar stamplad i
# SIMULERINGSTID. M-49 matte kvoten till 1,000 i tre driftpunkter med slingan
# sluten, sedan den dyra pollningen tagits bort. Braketten nedan ar darfor
# snavare an fas 7:s 0,6-1,6, och snavheten ar KOPT: korningen mater kvoten om
# i sin egen rigg och skriver ut den, och en kvot utanfor braketten faller
# korningen i stallet for att tyst gora fonstren meningslosa.
KLOCKA_LAG = 0.75           # Satt av M-73.
KLOCKA_HOG = 1.40           # Satt av M-73.
TRANSPORTVARV = 3           # Satt av M-49 (genomslag 1-2 varv, ett till marginal).

# Hur lange en station som mest far VANTA pa den delade utmataren innan den
# far lamna processlaget: en hel utmatning, for det ar sa lange den andra
# stationen som mest kan halla donet. Talet ar linjens KONSTRUKTION, inte en
# matt troskel.
VANTAN_S = {"a": UTMATNINGSTID_S, "b": UTMATNINGSTID_S}

# Hur langt in i givarfonstret produkten hinner innan bandet star stilla, och
# hur lang tid det tar att kora ut den ur fonstret igen. Bada ar SIMULERINGSTID
# (banans egen fart) och skalas darfor inte med klockbraketten.
KLAMLAGE_MM = TRANSPORTVARV * 0.05 * BANDFART_MM_S
UTKORNING_S = (2.0 * GIVARE_HALVBREDD_MM - KLAMLAGE_MM) / UTMATNINGSFART_MM_S
UTKORNING_LANGSAM_S = (2.0 * GIVARE_HALVBREDD_MM) / BANDFART_MM_S

# Overlamningen: fran att station A slapper utmataren till att produkten nar
# station B:s givare. Ren geometri och banornas egen fart - ingen PLC-tid.
OVERLAMNING_MM = (BANLANGD_MM - GIVARE_A_D_MM - GIVARE_HALVBREDD_MM
                  - KLAMLAGE_MM + UTMATNINGSFART_MM_S * UTMATNINGSTID_S * -1.0
                  + GIVARE_A_D_MM * 0.0)
# Talet ovan blir latt fel om man raknar i huvudet, sa det raknas i klartext:
_EFTER_UTMATNING_MM = (GIVARE_A_D_MM - GIVARE_HALVBREDD_MM + KLAMLAGE_MM
                       + UTMATNINGSFART_MM_S * UTMATNINGSTID_S)
OVERLAMNING_MM = ((BANLANGD_MM - _EFTER_UTMATNING_MM)
                  + (GIVARE_B_D_MM - GIVARE_HALVBREDD_MM))
OVERLAMNING_S = OVERLAMNING_MM / BANDFART_MM_S


def _transport(varvtid_s):
    """Transporttiden scen -> PLC -> scen, pa ogats axel."""
    return TRANSPORTVARV * max(varvtid_s, 0.1) * KLOCKA_HOG


def _fonster(nominell_s, vantan_s, varvtid_s, extra_s=0.0):
    """PLC-sekunder -> ett fonster pa ogats axel.

    Ovre kanten bar tre pafyllnader utover klockbraketten, och var och en har
    ett skal: VANTAN pa den delade utmataren (linjens konstruktion),
    DRIFTPAUSEN (perturbationen aterstaller TON:en, sa processen blir langre),
    och TRANSPORTEN scen -> PLC -> scen.
    """
    return (max(0.0, nominell_s * KLOCKA_LAG + extra_s),
            (nominell_s + vantan_s + PAUS_LANGD_S) * KLOCKA_HOG
            + _transport(varvtid_s) + extra_s)


def provplan(rate_hz=20.0):
    """Vad ogat ska PROVA. Skild fran facit: samma serie doms sedan av tre
    olika planer - station A:s, station B:s och linjens."""
    return {
        "template": "fas8_linan",
        "rate_hz": float(rate_hz),
        "floor_z": 0.0,
        "scene": "all",
        "movers": {"ST8A_Don/Stopp": "ST8_BromsA",
                   "ST8B_Don/Stopp": "ST8_BromsB"},
        "parts": ["ST8_BromsA", "ST8_BromsB", "ST8_Utmatare"],
        "tools": [],
        "signals": ["ST8A_Givare/Puls", "ST8B_Givare/Puls",
                    "ST8_Linje/Kor",
                    "ST8A_Don/Stopp", "ST8A_Don/Slapp",
                    "ST8B_Don/Stopp", "ST8B_Don/Slapp"],
    }


def stationsplan(pre, rate_hz=20.0, varvtid_s=0.3):
    """Facit for EN station, samma form som fas 7:s (M-49)."""
    S_ = "ST8%s" % pre.upper()
    givare = "%s_Givare/Puls" % S_
    stopp = "%s_Don/Stopp" % S_
    slapp = "%s_Don/Slapp" % S_
    vantan = VANTAN_S[pre]
    return {
        "template": "fas8_linan",
        "rate_hz": float(rate_hz),
        "floor_z": 0.0,
        "scene": "all",
        "movers": {stopp: "ST8_Broms%s" % pre.upper()},
        "parts": ["ST8_Broms%s" % pre.upper()],
        "tools": [],
        "signals": [givare, stopp, slapp],
        "sekvens": {
            "start": {"signal": givare, "flank": "RISE"},
            # Stationen far STOPPA en produkt EN gang. Ordningen ensam ser inte
            # en station som gor om allt (M-50).
            "hogst": {stopp: 1},
            "steg": [
                {"signal": stopp, "flank": "RISE",
                 "min_s": 0.0, "max_s": _transport(varvtid_s)},
                {"signal": stopp, "flank": "FALL",
                 "min_s": _fonster(PROCESSTID_S, vantan, varvtid_s)[0],
                 "max_s": _fonster(PROCESSTID_S, vantan, varvtid_s)[1]},
                {"signal": slapp, "flank": "RISE",
                 "min_s": _fonster(PROCESSTID_S, vantan, varvtid_s)[0],
                 "max_s": _fonster(PROCESSTID_S, vantan, varvtid_s)[1]},
                # Produkten MASTE lamna stationen, och den gor det MEDAN
                # utmatningen gar: utmatningen ar 1,5 s och fonstret ar
                # utkort pa 0,66 s. Stegen star darfor i den ordning fysiken
                # ger dem - en ordningsdom soker varje steg efter det
                # foregaende, sa en omkastad lista fäller en riktig station.
                # MATT i den har korningens forsta korning, dar `Puls FALL`
                # lag fore `Slapp FALL` och doms som uteblivet.
                {"signal": givare, "flank": "FALL",
                 "min_s": _fonster(PROCESSTID_S, vantan, varvtid_s,
                                   extra_s=UTKORNING_S)[0],
                 "max_s": _fonster(PROCESSTID_S, vantan, varvtid_s,
                                   extra_s=UTKORNING_LANGSAM_S)[1]},
                {"signal": slapp, "flank": "FALL",
                 "min_s": _fonster(PROCESSTID_S + UTMATNINGSTID_S, vantan,
                                   varvtid_s)[0],
                 "max_s": _fonster(PROCESSTID_S + UTMATNINGSTID_S, vantan,
                                   varvtid_s)[1]},
            ],
            "min_cykler": 3,
        },
        "forregling": [[stopp, slapp]],
    }


def linjeplan(rate_hz=20.0, varvtid_s=0.3):
    """Facit for LINAN. Tva krav, och bada ar omojliga att stalla pa en station.

    1. OVERLAMNINGEN. Varje produkt station A lamnar ifran sig ska na station
       B och klammas dar, inom den tid banornas egen fart medger. Cykeln
       borjar pa A:s utmatning och slutar hos B - den korsar alltsa
       stationsgransen, och en enstationskorning kan inte ens borja den.
    2. DEN DELADE UTMATAREN. Stationerna far aldrig begara den samtidigt. Ett
       don kan inte tjana tva stationer, och anlaggningen later da INGEN fa
       det.
    """
    return {
        "template": "fas8_linan",
        "rate_hz": float(rate_hz),
        "floor_z": 0.0,
        "scene": "all",
        "movers": {"ST8A_Don/Stopp": "ST8_BromsA",
                   "ST8B_Don/Stopp": "ST8_BromsB"},
        "parts": ["ST8_BromsA", "ST8_BromsB", "ST8_Utmatare"],
        "tools": [],
        "signals": ["ST8A_Givare/Puls", "ST8B_Givare/Puls",
                    "ST8A_Don/Stopp", "ST8A_Don/Slapp",
                    "ST8B_Don/Stopp", "ST8B_Don/Slapp"],
        "sekvens": {
            "start": {"signal": "ST8A_Don/Slapp", "flank": "FALL"},
            "hogst": {"ST8B_Givare/Puls": 1},
            "steg": [
                {"signal": "ST8B_Givare/Puls", "flank": "RISE",
                 "min_s": OVERLAMNING_S * KLOCKA_LAG,
                 "max_s": OVERLAMNING_S * KLOCKA_HOG + _transport(varvtid_s)},
                {"signal": "ST8B_Don/Stopp", "flank": "RISE",
                 "min_s": OVERLAMNING_S * KLOCKA_LAG,
                 "max_s": OVERLAMNING_S * KLOCKA_HOG
                          + 2.0 * _transport(varvtid_s)},
            ],
            "min_cykler": 3,
        },
        "forregling": [["ST8A_Don/Slapp", "ST8B_Don/Slapp"]],
    }


# ---- scenen ---------------------------------------------------------------

MALLKOD = """
app = getApplication()
for _c in list(app.Components):
    if _c.Name[:4] == 'ST8_':
        app.deleteComponent(_c)
_p = app.createComponent()
_p.Name = 'ST8_Mall'
_f = _p.RootFeature.createFeature(VC_BLOCK, "kropp")
for _q in _f.Properties:
    if _q.Name in ("Length", "Width", "Height"):
        _q.Value = 200.0
_p.RootFeature.rebuild()
_m = _p.PositionMatrix
_m.translateAbs(-5000.0 - _m.P.X, %(y).1f - _m.P.Y, 0.0 - _m.P.Z)
_p.PositionMatrix = _m
"""

PLACERAKOD = """
app = getApplication()
_k = app.findComponent(%(namn)r)
_m = _k.PositionMatrix
_m.translateAbs(%(x).1f - _m.P.X, %(y).1f - _m.P.Y, %(z).1f - _m.P.Z)
_k.PositionMatrix = _m
"""

SIGNALKOD = """
app = getApplication()
for _namn, _signaler in (('ST8A_Givare', ('Puls',)),
                         ('ST8B_Givare', ('Puls',)),
                         ('ST8_Linje', ('Kor', 'Nod')),
                         ('ST8A_Don', ('Stopp', 'Slapp')),
                         ('ST8B_Don', ('Stopp', 'Slapp'))):
    _k = app.createComponent()
    _k.Name = _namn
    for _s in _signaler:
        _b = _k.createBehaviour(VC_BOOLEANSIGNAL, _s)
        _b.Value = False
"""

KROPPSKOD = """
app = getApplication()
_b = app.createComponent()
_b.Name = %(namn)r
_f = _b.RootFeature.createFeature(VC_BLOCK, "kropp")
for _q in _f.Properties:
    if _q.Name == "Length":
        _q.Value = %(l).1f
    elif _q.Name == "Width":
        _q.Value = %(w).1f
    elif _q.Name == "Height":
        _q.Value = %(h).1f
_b.RootFeature.rebuild()
_m = _b.PositionMatrix
_m.translateAbs(%(x).1f - _m.P.X, %(y).1f - _m.P.Y, %(z).1f - _m.P.Z)
_b.PositionMatrix = _m
"""


def _startskript():
    """Koden som bygger linjen, FORE startSimulation().

    Ordningen ar inte fri: M-40 matte att en matare som byggs i en redan
    korande simulering aldrig fyrar, hur ratt den an ar kopplad. Och banans
    langd maste vara verklig innan nagot flodar - `bana.update()` efter att
    Path satts, annars ar PathLength 0 och mataren har ingenstans att lamna.
    """
    delar = [MALLKOD % {"y": LINJE_Y_MM}]
    delar.append(R.generera("flodeslinje", {
        "name": LINJE, "mall": "ST8_Mall",
        "intervall": MATARINTERVALL_S, "grans": 100000,
        "hastighet": BANDFART_MM_S, "banlangd": BANLANGD_MM,
        "matarlangd": MATARLANGD_MM, "x": 0.0, "y": LINJE_Y_MM,
    }).replace("from __future__ import print_function\n", ""))
    # Bana 2, lagd sa att dess in-ram sammanfaller med bana 1:s ut-ram.
    delar.append(R.generera("transportor", {
        "name": "ST8_Bana2", "langd": BANLANGD_MM,
        "hastighet": BANDFART_MM_S,
    }).replace("from __future__ import print_function\n", ""))
    delar.append(PLACERAKOD % {"namn": "ST8_Bana2",
                               "x": MATARLANGD_MM + BANLANGD_MM,
                               "y": LINJE_Y_MM, "z": 0.0})
    delar.append(R.generera("koppla", {
        "a": "ST8_Bana", "b": "ST8_Bana2",
    }).replace("from __future__ import print_function\n", ""))
    delar.append(SIGNALKOD)
    for namn, x in (("ST8_BromsA", MATARLANGD_MM + GIVARE_A_D_MM),
                    ("ST8_BromsB", MATARLANGD_MM + BANLANGD_MM + GIVARE_B_D_MM)):
        delar.append(KROPPSKOD % {"namn": namn, "l": 120.0, "w": 120.0,
                                  "h": 400.0, "x": x, "y": BROMS_INNE_Y_MM,
                                  "z": 0.0})
    delar.append(KROPPSKOD % {"namn": "ST8_Utmatare", "l": 200.0, "w": 200.0,
                              "h": 300.0, "x": UTMATARE_X_HEM_MM,
                              "y": UTMATARE_Y_MM, "z": 0.0})
    kropp_ = "\n".join(delar)
    inne = "\n".join(("    " + r) if r.strip() else ""
                     for r in kropp_.splitlines())
    return (
        "# Skrivet av tests/protocol/kor_fas8_linan.py. Kors av bridge_cmd\n"
        "# FORE startSimulation(); dar, och bara dar, initieras beteendena.\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "import traceback\n"
        "\n"
        "_LOGG = os.path.join(os.path.expanduser('~'), 'vc_assist_fas8.json')\n"
        "\n"
        "\n"
        "class _Fangare(object):\n"
        "    def __init__(self):\n"
        "        self.rader = []\n"
        "\n"
        "    def write(self, s):\n"
        "        self.rader.append(s)\n"
        "\n"
        "    def flush(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "_fang = _Fangare()\n"
        "_gammal = sys.stdout\n"
        "sys.stdout = _fang\n"
        "try:\n"
        + inne + "\n"
        "    _res = {'stdout': ''.join(_fang.rader)}\n"
        "except Exception:\n"
        "    _res = {'fel': traceback.format_exc(),\n"
        "            'stdout': ''.join(_fang.rader)}\n"
        "sys.stdout = _gammal\n"
        "_f = open(_LOGG, 'w')\n"
        "try:\n"
        "    _f.write(json.dumps(_res, sort_keys=True))\n"
        "finally:\n"
        "    _f.close()\n")


# ---- anlaggningen ---------------------------------------------------------
#
# Ett steg av processen: las produkternas verkliga lagen, satt fotocellerna,
# och lat stalldonen verka. INGEN logik - villkoren nedan ar fysik, inte
# sekvens. Koden kors inne i VC (py2.7) genom godkannandekon (I12).
#
# DEN DELADE UTMATAREN ar fas 8:s enda nya fysik, och den ar deklarerad har,
# fore losningarna: ETT don, tva stationer. Begar bada det samtidigt far
# INGEN av dem det, bada banorna star kvar stilla, och donet star still.
# Konflikten TIGS inte - den rapporteras, precis som bromskonflikten i M-49.

ANLAGGNING = """import json
app = getApplication()
sim = getSimulation()
bana1 = app.findComponent('ST8_Bana').findBehaviour('Path')
bana2 = app.findComponent('ST8_Bana2').findBehaviour('Path')

# Produkterna far unika namn ur sin egen skapelsetid. Klonerna arver mallens
# namn, och tva objekt med samma namn hade blivit EN serie i ogats scenbild.
prod = []
for c in list(app.Components):
    n = c.Name
    if n == 'ST8_Mall':
        d = c.getPathDistance()
        if d >= 0.0:
            n = 'ST8_P%%02d' %% int(round(c.CreationTime / %(intervall).6f))
            c.Name = n
    if n[:5] == 'ST8_P':
        d = c.getPathDistance()
        x = c.WorldPositionMatrix.P.X
        # Vilken bana produkten star pa: pa bana 1 ar varldens x =
        # matarlangden + banavstandet, pa bana 2 ar det matarlangden +
        # banlangden + banavstandet. Skillnaden mellan de tva hypoteserna ar
        # en hel banlangd, sa DIFFERENSEN x - d avgor med bred marginal.
        #
        # MATT i den har korningens forsta korning: ett tathetsprov (< 1 mm)
        # pa den ena hypotesen fallde ut fel med jamna mellanrum, for
        # WorldPositionMatrix slapar ett scenuppdateringssteg (M-11) medan
        # getPathDistance ar fardt. En produkt pa bana 2 vid banavstand 2400
        # blev da en produkt pa bana 1 vid banavstand 2400 - alltsa mitt i
        # station A:s givarfonster - och gav en falsk puls dar.
        pa2 = (x - d) > %(mitt)s
        prod.append({'namn': n, 'd': d, 'x': x, 'bana': 2 if pa2 else 1})

a_puls = False
b_puls = False
for p in prod:
    if p['bana'] == 1 and abs(p['d'] - %(ad).6f) <= %(gh).6f:
        a_puls = True
    if p['bana'] == 2 and abs(p['d'] - %(bd).6f) <= %(gh).6f:
        b_puls = True

app.findComponent('ST8A_Givare').findBehaviour('Puls').Value = bool(a_puls)
app.findComponent('ST8B_Givare').findBehaviour('Puls').Value = bool(b_puls)
_linje = app.findComponent('ST8_Linje')
_linje.findBehaviour('Kor').Value = %(kor)s
_linje.findBehaviour('Nod').Value = False

da = app.findComponent('ST8A_Don')
db = app.findComponent('ST8B_Don')
%(donskrivning)s
a_stopp = bool(da.findBehaviour('Stopp').Value)
a_slapp = bool(da.findBehaviour('Slapp').Value)
b_stopp = bool(db.findBehaviour('Stopp').Value)
b_slapp = bool(db.findBehaviour('Slapp').Value)

# Den delade utmataren. ETT don kan inte tjana tva stationer.
konflikt = a_slapp and b_slapp
a_far = a_slapp and not b_slapp
b_far = b_slapp and not a_slapp

# Bandet: bromsen vinner, och en utmatning som inte fick donet haller kvar
# produkten i stallet for att slappa den obehandlad.
#
# DRIFTVALJAREN stannar bada banorna. Det ar inte en detalj: med banorna
# igang medan `kor` ar av glider produkter forbi en station som inte far
# arbeta, och da mater perturbationen riggens brist i stallet for losningen.
# MATT i den har korningens tredje korning: en produkt passerade station B
# obehandlad under pausen, och stationens facit foll pa det.
kor_pa = %(kor)s
if not kor_pa:
    bana1.Speed = 0.0
    bana2.Speed = 0.0
elif a_stopp or (a_slapp and not a_far):
    bana1.Speed = 0.0
elif a_far:
    bana1.Speed = %(snabb).6f
else:
    bana1.Speed = %(normal).6f
if kor_pa:
    if b_stopp or (b_slapp and not b_far):
        bana2.Speed = 0.0
    elif b_far:
        bana2.Speed = %(snabb).6f
    else:
        bana2.Speed = %(normal).6f

for namn, ute in (('ST8_BromsA', a_stopp), ('ST8_BromsB', b_stopp)):
    b = app.findComponent(namn)
    m = b.PositionMatrix
    mal = %(ute).6f if ute else %(inne).6f
    dy = mal - m.P.Y
    if dy > %(steg).6f:
        dy = %(steg).6f
    elif dy < -%(steg).6f:
        dy = -%(steg).6f
    m.translateAbs(0.0, dy, 0.0)
    b.PositionMatrix = m

u = app.findComponent('ST8_Utmatare')
mu = u.PositionMatrix
if konflikt:
    malx = mu.P.X
elif a_far:
    malx = %(ux_a).6f
elif b_far:
    malx = %(ux_b).6f
else:
    malx = %(ux_hem).6f
dx = malx - mu.P.X
if dx > %(usteg).6f:
    dx = %(usteg).6f
elif dx < -%(usteg).6f:
    dx = -%(usteg).6f
mu.translateAbs(dx, 0.0, 0.0)
u.PositionMatrix = mu

print(json.dumps({'t': sim.SimTime, 'v1': bana1.Speed, 'v2': bana2.Speed,
                  'a_puls': a_puls, 'b_puls': b_puls,
                  'a_stopp': a_stopp, 'a_slapp': a_slapp,
                  'b_stopp': b_stopp, 'b_slapp': b_slapp,
                  'konflikt': bool(konflikt),
                  'utmatare_x': u.PositionMatrix.P.X,
                  'antal': len(prod),
                  'bana1': len([p for p in prod if p['bana'] == 1]),
                  'bana2': len([p for p in prod if p['bana'] == 2]),
                  'prod': prod}))
"""


def anlaggningskod(kor, donskrivning):
    return ANLAGGNING % {
        "intervall": MATARINTERVALL_S, "ad": GIVARE_A_D_MM,
        "bd": GIVARE_B_D_MM, "gh": GIVARE_HALVBREDD_MM,
        "mitt": repr(MATARLANGD_MM + 0.5 * BANLANGD_MM),
        "kor": "True" if kor else "False",
        "snabb": UTMATNINGSFART_MM_S, "normal": BANDFART_MM_S,
        "ute": BROMS_UTE_Y_MM, "inne": BROMS_INNE_Y_MM,
        "steg": BROMS_STEG_MM, "donskrivning": donskrivning,
        "ux_a": UTMATARE_X_A_MM, "ux_b": UTMATARE_X_B_MM,
        "ux_hem": UTMATARE_X_HEM_MM, "usteg": UTMATARE_STEG_MM,
    }


# Hur manga anlaggningssteg som far vara pa vag samtidigt (M-49).
MAX_UTESTAENDE = 2          # Satt av M-49.
PLC_TATHET_S = 0.05         # Satt av M-49.


class Linjekopplare(Kopplare):
    """Kopplaren, med anlaggningssteget i SAMMA koade anrop som donskrivningen.

    Skalet ar matt (M-49): tva koade anrop per varv kostar tva pumpvarv, och
    da spricker ogats gruns for hur gammalt ett PLC-varde far vara.
    """

    def __init__(self, *a, **kw):
        Kopplare.__init__(self, *a, **kw)
        self.kor_signal = True
        self.anlaggning = []
        self.pollintervall = 0.1
        self._utestaende = []
        # En SKYDDAD ingang gar inte att driva harifran, och det ar ratt
        # (M-49): opcuakonfig ger den lasrattigheter bara, och en skrivning
        # svarar BadInternalError. Sakerhetskedjan hor inte till den
        # genererade logiken (I15).
        self.skyddade = [s for s in self.till_plc if s.skyddad]
        self.till_plc = [s for s in self.till_plc if not s.skyddad]

    def _vanta_latt(self, qid, timeout=60.0):
        """Vantar ut posten UTAN att be om kons svar (M-49: `queue_list`
        serialiserar hela kon med varje posts svar och foll pa E_TOO_LARGE)."""
        slut = time.time() + timeout
        while time.time() < slut:
            kon = self.brygga.anrop(
                "queue_list", {"with_code": False,
                               "with_result": False})["result"]["queue"]
            for post in kon:
                if post["qid"] == qid:
                    if post["state"] in ("done", "failed", "interrupted",
                                         "rejected"):
                        return post
                    break
            time.sleep(self.pollintervall)
        raise RuntimeError("posten %s fick inget utfall inom %.0f s"
                           % (qid, timeout))

    def skriv_scenen(self, varden):
        rader = []
        for s in self.fran_plc:
            v = varden.get(s.tagg)
            if v is None:
                continue
            komp = "da" if s.komponent.startswith("ST8A") else "db"
            rader.append("_b = %s.findBehaviour(%r)" % (komp, str(s.scensignal)))
            rader.append("if _b is not None:")
            rader.append("    _b.Value = %r" % (bool(v),))
        kod = anlaggningskod(self.kor_signal, "\n".join(rader) or "pass")
        post = self.brygga.koa(kod, desc="anlaggningen: ett processteg")
        self.brygga.godkann(post["qid"])
        self._utestaende.append(post["qid"])
        if len(self._utestaende) > MAX_UTESTAENDE:
            aldst = self._utestaende.pop(0)
            ut = self._vanta_latt(aldst)
            if ut["state"] != "done":
                raise RuntimeError("anlaggningssteget %s slutade som %r"
                                   % (aldst, ut["state"]))
            # Anlaggningens EGET svar gar inte att lasa har, och det ar med
            # flit: `_vanta_latt` hamtar posten UTAN resultat, for `queue_list`
            # serialiserar annars hela kon med varje posts svar (M-49). Ett
            # konflikttal hamtat harifran hade darfor alltid varit noll - ett
            # matt som ser matt ut och strukturellt inte kan bli annat an
            # gront. Konflikterna raknas i slingan i stallet, ur kopplarens
            # egna varden.
        self.anlaggning.append(post["qid"])
        return {}

    def stang_av(self):
        for qid in list(self._utestaende):
            try:
                self._vanta_latt(qid, timeout=30.0)
            except Exception:
                pass
        self._utestaende = []


# ---- VC -------------------------------------------------------------------

# Den virtuella skarmen. VC far ALDRIG hamna pa operatorens skarm - hen sitter
# vid datorn. `os.environ.get("DISPLAY", ":99")` ar precis fallan: ett arvt
# DISPLAY ser ut som ett standardvarde och ar det inte (M-49). Skarmen sags
# darfor uttryckligen, och LASES TILLBAKA ur processen efterat.
HEADLESS_DISPLAY = ":99"        # docs/spec/00_arbetssatt.md: VC kors headless.


def _vc_pids():
    """VC:s egna processer, ur /proc. INTE `pgrep -f`, som traffar sin egen
    sokning: kravet ar att programmet i argv[0] ar VC:s exe."""
    ut = []
    for post in os.listdir("/proc"):
        if not post.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % post, "rb") as f:
                argv = f.read().split(b"\0")
        except (IOError, OSError):
            continue
        if argv and argv[0].replace(b"\\", b"/").endswith(
                b"VisualComponents.Engine.exe"):
            ut.append(post)
    return ut


def _vcs_skarm(tak_s=120.0):
    """Vilken skarm VC:s process FAKTISKT hamnade pa, last ur /proc."""
    slut = time.time() + tak_s
    while time.time() < slut:
        for pid in _vc_pids():
            try:
                with open("/proc/%s/environ" % pid, "rb") as f:
                    for post in f.read().split(b"\0"):
                        if post.startswith(b"DISPLAY="):
                            return pid, post[8:].decode()
            except (IOError, OSError):
                continue
        time.sleep(2.0)
    return None, None


def _starta_om_vc():
    subprocess.call([os.path.expanduser("~/bin/vc-stoppa.sh")])
    miljo = dict(os.environ, DISPLAY=HEADLESS_DISPLAY)
    subprocess.Popen([os.path.expanduser("~/bin/vc-test.sh")], env=miljo,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, start_new_session=True)
    pid, skarm = _vcs_skarm()
    if skarm != HEADLESS_DISPLAY:
        raise RuntimeError(
            "VC startade pa skarmen %r (pid %s), inte %r. Korningen avbryts: "
            "ett VC-fonster pa operatorens skarm ar aldrig acceptabelt."
            % (skarm, pid, HEADLESS_DISPLAY))
    print("  VC kor headless pa %s (pid %s)" % (skarm, pid))


def _vanta_pa_bryggan(tak_s):
    slut = time.time() + tak_s
    while time.time() < slut:
        try:
            k = Klient(port=8901, tokenfil=TOKEN, timeout=5.0).anslut()
            k.ping()
            k.stang()
            return True
        except Exception:
            time.sleep(3.0)
    return False


# ---- OPC UA ---------------------------------------------------------------

class UaKanal:
    """Den minsta yta kopplaren begar: las(taggar) och skriv(varden)."""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.klient = None
        self._noder = {}

    def anslut(self, kravda_taggar=(), tak_s=60.0):
        """Anslut och KRAV att adressrummet ar linjens (M-49: en korning mot
        forra programmets adressrum sag ut som en linje som aldrig gjorde
        nagot, for `las` svarar None for en tagg den inte hittar)."""
        from asyncua.sync import Client as SyncClient
        slut = time.time() + tak_s
        sista = None
        while time.time() < slut:
            try:
                self.klient = SyncClient(url=self.endpoint)
                self.klient.connect()
                break
            except Exception as fel:
                sista = fel
                self.klient = None
                time.sleep(2.0)
        if self.klient is None:
            raise RuntimeError("nadde inte OPC UA-servern: %s" % sista)
        for barn in self.klient.nodes.objects.get_children():
            namn = barn.read_browse_name().Name
            self._noder[namn] = barn
        saknade = [t for t in kravda_taggar if t not in self._noder]
        if saknade:
            self.stang()
            raise RuntimeError(
                "OPC UA-servern saknar %s. Adressrummet ar inte linjens: "
                "den kanner %s" % (", ".join(saknade),
                                   ", ".join(sorted(self._noder))))
        return self

    def stang(self):
        if self.klient is not None:
            try:
                self.klient.disconnect()
            except Exception:
                pass
            finally:
                self.klient = None

    def las(self, taggar):
        """Laser ALLA taggar i EN begaran.

        MATT i den har korningens femte korning: en lasning i taget hamtar
        varden ur OLIKA PLC-scan. Just nar en station gar fran broms till
        utmatning las `stopp` fore skiftet och `slapp` efter, bada svarade
        TRUE, och kopplaren skrev bada hoga i scenen. Ogat sag da ett
        forreglingsbrott pa 0,10 s som PLC:n aldrig gjorde - ett
        matinstrument som tillverkar sitt eget fynd. En samlad lasning kan
        servern besvara ur ETT tillstand.
        """
        noder = [self._noder.get(t) for t in taggar]
        kanda = [n for n in noder if n is not None]
        varden = {}
        if kanda:
            try:
                lasta = self.klient.read_values(kanda)
            except Exception:
                lasta = [n.read_value() for n in kanda]
            for n, v in zip(kanda, lasta):
                varden[id(n)] = v
        return dict((t, None if n is None else varden.get(id(n)))
                    for t, n in zip(taggar, noder))

    def skriv(self, varden):
        for t, v in varden.items():
            n = self._noder.get(t)
            if n is not None and v is not None:
                n.write_value(bool(v) if isinstance(v, bool) else v)


# ---- en korning -----------------------------------------------------------

def granska(namn, kropp_, sk, k, byggrot, strucpp, index):
    """Grind 1-4 over kandidaten. Returnerar (dom, kandidat)."""
    kand = S.Kandidat.fran_modellsvar(sk, kropp_, SCENKOD)
    dom = S.granska_station(kand, k, index=index, strucpp_paket=strucpp,
                            byggkatalog=os.path.join(byggrot, namn),
                            stanna_vid_forsta=False)
    return dom, kand


def starta_om_runtimen(kommando, bas, anvandare, losenord, tak_s=180.0):
    """Starta om HELA runtimeprocessen och vanta tills den svarar igen.

    MATT (M-49): OPC UA-pluginet laser sin conf nar RUNTIMEPROCESSEN startar,
    inte nar PLC:n startar. En uppladdning som bygger ratt program och
    kopierar ratt conf ger anda det FORRA adressrummet.
    """
    if subprocess.call(kommando, shell=True) != 0:
        raise RuntimeError("kunde inte starta om runtimen: %r" % kommando)
    klient = OpenPlcV4(bas, anvandare, losenord, tillat_osignerat=True)
    slut = time.time() + tak_s
    while time.time() < slut:
        try:
            if klient.svarar():
                break
        except Exception:
            pass
        time.sleep(3.0)
    else:
        raise RuntimeError("runtimen kom aldrig tillbaka efter omstarten")
    if klient.status() != "RUNNING":
        klient.starta_och_vanta(60.0)
    return klient.status()


def driftsatt(kand, k, byggrot, namn, strucpp, runtime_include, bas,
              anvandare, losenord, endpoint_server, omstartskommando):
    """Kompilera, bygg arkivet, ladda upp, starta - och starta om runtimen."""
    kalla = kand.st_kalla + paket.konfigurationstext(LINJE)
    ut = os.path.join(byggrot, namn, "drift")
    forbygge = paket.kompilera(kalla, os.path.join(ut, "forbygge"), strucpp)
    konfig = opcuakonfig.konfiguration(k, forbygge, endpoint_server)
    zipvag, _karta = paket.bygg_projekt(kalla, os.path.join(ut, "arkiv"),
                                        strucpp, runtime_include,
                                        opcua_konfig=konfig)
    klient = OpenPlcV4(bas, anvandare, losenord, tillat_osignerat=True)
    klient.skapa_forsta_anvandare()
    # STOPPA forst (M-49: RUNNING betyder inte att det ar DITT program).
    klient.stoppa()
    klient.ladda_och_starta(zipvag)
    return starta_om_runtimen(omstartskommando, bas, anvandare, losenord)


def kor_slingan(brygga, kopplare, sekunder, varvtid_s=0.0):
    """Sluter slingan tills tiden gatt. Returnerar en logg over varven."""
    logg = {"varv": 0, "paus": None, "konflikter": 0, "fel": []}
    t_start = time.time()
    forra_stopp = False
    paus_till = None
    varvtider = []
    while time.time() - t_start < sekunder:
        t_varv = time.time()
        v = kopplare.kor_varv()
        logg["varv"] += 1
        if v.fel:
            logg["fel"].append(v.fel)
        if v.fran_plc.get("a_slapp") and v.fran_plc.get("b_slapp"):
            # Bada stationerna begar den DELADE utmataren samtidigt. Raknas
            # HAR, ur kopplarens egna varden: `_vanta_latt` hamtar posten utan
            # resultat (annars serialiserar `queue_list` hela kon, M-49), sa
            # anlaggningens egen konfliktflagga gar inte att lasa tillbaka.
            logg["konflikter"] += 1
        # Perturbationen ARMAS pa vilken som helst av stationernas bromsar.
        # I en enstationskonfiguration finns bara den enas, och en paus som
        # aldrig kom hade gjort kontrollkorningen mildare an linjekorningen.
        stopp = bool(v.fran_plc.get("a_stopp") or v.fran_plc.get("b_stopp"))
        if (stopp and not forra_stopp and paus_till is None
                and logg["paus"] is None
                and time.time() - t_start >= PAUS_TIDIGAST_S):
            paus_till = time.time() + PAUS_FORDROJNING_S
        forra_stopp = stopp
        # Perturbationen: driftvaljaren slas av en stund, lika for alla fall.
        if paus_till is not None and time.time() >= paus_till:
            if kopplare.kor_signal:
                kopplare.kor_signal = False
                logg["paus"] = {"start_s": round(time.time() - t_start, 3)}
                paus_till = time.time() + PAUS_LANGD_S
            else:
                kopplare.kor_signal = True
                logg["paus"]["slut_s"] = round(time.time() - t_start, 3)
                paus_till = None
        varvtider.append((time.time() - t_varv) * 1000.0)
        kvar = varvtid_s - (time.time() - t_varv)
        if kvar > 0:
            time.sleep(kvar)
    varvtider.sort()
    if varvtider:
        logg["varv_ms"] = {
            "median": round(varvtider[len(varvtider) // 2], 1),
            "p95": round(varvtider[int(0.95 * (len(varvtider) - 1))], 1),
            "max": round(varvtider[-1], 1)}
    return logg


def _domar(data, a, konfig):
    """Samma serie, tre facit. Det ar sa 'guld per station, sedan guld for
    linan' gar att stalla som en fraga at gangen."""
    ut = {}
    for pre in STATIONER[konfig]:
        namn = "station%s" % pre.upper()
        text, rapport, analys = A.doma(data, stationsplan(pre, a.ogonrate,
                                                          a.varvtid))
        ut[namn] = {"text": text, "dom": list(rapport.dom),
                    "harledt": (analys.harledt.get("station") or {})}
    if konfig == "LINJE":
        text, rapport, analys = A.doma(data, linjeplan(a.ogonrate, a.varvtid))
        ut["linan"] = {"text": text, "dom": list(rapport.dom),
                       "harledt": (analys.harledt.get("station") or {})}
    return ut


def kor_en(namn, konfig, kropp_, a, index, brygga):
    """Hela vagen for ETT fall i EN konfiguration."""
    rad = {"fall": namn, "konfig": konfig}
    k = karta(konfig)
    sk = Skelett.av_karta(k, DEKLARATIONER)
    byggnamn = "%s_%s" % (namn, konfig)
    dom, kand = granska(byggnamn, kropp_, sk, k, a.byggrot, a.strucpp, index)
    rad["forgrindar"] = dict((g, (True if v is True else str(v)))
                             for g, v in dom.forgrindar.items())
    rad["forsta_fallande"] = dom.forsta_fallande
    rad["grindarnas_egna_ord"] = dict((g, t) for g, t in dom.utdata.items() if t)
    if not dom.ok:
        rad["celler"] = dict(
            ("station%s" % p.upper(), dom.till_cell(byggnamn, "station"))
            for p in STATIONER[konfig])
        return rad

    rad["plc_tillstand"] = driftsatt(kand, k, a.byggrot, byggnamn, a.strucpp,
                                     a.runtime_include, a.bas, a.anvandare,
                                     a.losenord, a.endpoint_server,
                                     a.runtime_omstart)
    ua = UaKanal(a.endpoint).anslut([s.tagg for s in k.signaler])
    try:
        # UPPVARMNING innan ogat startar (M-50): den forsta cykeln efter start
        # ar inget prov, den ar ett uppstartsforlopp. Linan bringas i jamvikt
        # forst, och ogat far se en lina som redan gar.
        # SAMMA kopplare varmer och mater. MATT i den har korningens fjarde
        # korning: en ny kopplare mellan uppvarmningen och matningen ger ett
        # glapp dar inget anlaggningssteg kors, banorna behaller sin sista
        # fart och linans takt hoppar - de tva forsta cyklerna i serien blev
        # 5,1 s i stallet for 8,1 s, och linjefacit foll pa dem. Glappet ar
        # riggens, inte losningens.
        kopplare = Linjekopplare(k, ua, brygga, oga=None)
        t_varm = time.time()
        while time.time() - t_varm < a.uppvarmning:
            t0v = time.time()
            kopplare.kor_varv()
            kvar = a.varvtid - (time.time() - t0v)
            if kvar > 0:
                time.sleep(kvar)
        rad["uppvarmning"] = {"sekunder": a.uppvarmning,
                              "varv": len(kopplare.varv)}

        simtid_fore = brygga.simtid()
        vagg_fore = time.time()
        plan = provplan(a.ogonrate)
        rad["oga_start"] = brygga.oga_start(plan, simtid_fore)
        rad["slinga"] = kor_slingan(brygga, kopplare, a.sekunder, a.varvtid)
        # Ogat stoppas FORST (M-49): allt som gors efter slingan ar tid da
        # ogat provtar utan att fa nagot nytt.
        stopp = brygga.oga_stopp()
        simtid_efter = brygga.simtid()
        vagg_efter = time.time()
        kopplare.stang_av()
        rad["kopplaren"] = kopplare.sammanfattning()
        rad["slinga"]["varv_efter_uppvarmning"] = (
            len(kopplare.varv) - rad["uppvarmning"]["varv"])
        rad["anlaggning"] = {"steg": len(kopplare.anlaggning)}
        # De tva klockorna, matta i DEN HAR korningen. Ett facit vars fonster
        # ar snava maste veta att kvoten var 1 - annars mater fonstren
        # kopplingen mellan klockorna, inte stationen.
        vagg = vagg_efter - vagg_fore
        rad["klockkvot"] = round(((simtid_efter - simtid_fore) / vagg)
                                 if vagg > 0 else 0.0, 4)
        # KLOCKGRINDEN. Facits fonster ar skalade med braketten, sa en kvot
        # utanfor den gor fonstren meningslosa i stallet for snava: med kvoten
        # 0,61 syns en 2-sekunderstimer som 1,22 s pa ogats axel, och en
        # riktig station faller da pa TOO_EARLY. MATT i den har korningen: en
        # provsvit som kordes samtidigt pa samma maskin tog pumpens tid och
        # tryckte kvoten till 0,6131. Korningen sager nu ifran i stallet for
        # att doma pa ett fonster som inte langre betyder nagot.
        rad["klockan_ok"] = bool(KLOCKA_LAG <= rad["klockkvot"] <= KLOCKA_HOG)
    finally:
        ua.stang()
    rad["oga_stopp"] = dict((x, stopp.get(x))
                            for x in ("samples", "dur_s", "rate_hz", "saknade"))
    data = stopp.get("data")
    if data is None:
        rad["fel"] = "ogats serie kom inte med i svaret (%s)" % stopp.get(
            "for_stor_for_svaret")
        rad["celler"] = dict(
            ("station%s" % p.upper(), dom.till_cell(byggnamn, "station"))
            for p in STATIONER[konfig])
        return rad
    rad["domar"] = _domar(data, a, konfig)
    rad["celler"] = dict((n, dom.till_cell("%s_%s" % (byggnamn, n),
                                           "linje" if n == "linan" else "station",
                                           eyes=d["text"]))
                         for n, d in rad["domar"].items())
    if a.serier:
        with open(os.path.join(a.serier, "%s_%s.json" % (namn, konfig)), "w") as f:
            json.dump(data, f)
    return rad


# ---- huvudprogram ---------------------------------------------------------

def _klockan_ok(rad):
    """Lag klockkvoten i braketten? None nar ingen kvot mattes.

    Kvoten kontrolleras HAR ocksa nar korningen ar inlast ur en aldre
    JSON-fil, sa att en sammanstallning inte kan bli mildare an korningen.
    """
    if "klockan_ok" in rad:
        return rad["klockan_ok"]
    kvot = rad.get("klockkvot")
    if kvot is None:
        return None
    return bool(KLOCKA_LAG <= kvot <= KLOCKA_HOG)


def _dom_av(rad, namn):
    """Domen for en cell, eller None om korningen inte gar att lasa.

    En korning vars klockkvot lag utanfor braketten ar OGILTIG, inte fallande:
    facits fonster ar skalade med braketten, och utanfor den mater de
    kopplingen mellan klockorna i stallet for stationen.
    """
    if _klockan_ok(rad) is False:
        return "OGILTIG"
    d = ((rad.get("domar") or {}).get(namn) or {}).get("dom")
    return d[0] if d else None


def _skriv(ut):
    print("\n=== fas 8: linan ===")
    fel = 0
    for rad in ut["korningar"]:
        domar = []
        for namn in ("stationA", "stationB", "linan"):
            d = _dom_av(rad, namn)
            if d:
                domar.append("%s=%s" % (namn, d))
        print("\n  %-4s %-5s  %s" % (rad["fall"], rad["konfig"],
                                     " ".join(domar) or rad.get("fel", "")))
        for g in ("statisk_analys", "deklarationsmatchning", "anropsvalidering",
                  "kompilering"):
            v = rad["forgrindar"].get(g)
            if v is not True:
                print("        %-24s %s" % (g, v))
        for namn in ("stationA", "stationB", "linan"):
            d = (rad.get("domar") or {}).get(namn)
            if d:
                print("        %-9s %-13s %s" % (namn, d["dom"][0],
                                                 d["dom"][1][:100]))
        if rad.get("slinga"):
            s = rad["slinga"]
            print("        %-9s %d varv, paus %s, %d konflikter, klockkvot %s%s"
                  % ("slingan", s["varv"], s.get("paus"), s["konflikter"],
                     rad.get("klockkvot"),
                     "" if _klockan_ok(rad) is not False
                     else "  <- UTANFOR BRAKETTEN, korningen ar OGILTIG"))
    print("\n  guldgrinden: %s" % ut.get("guld"))
    for rad in ut.get("kompositionsprov", []):
        print("  %-4s %-28s linje=%-13s A=%-13s B=%-13s  %s"
              % (rad["fall"], rad["vad"], rad["linje"], rad["a"], rad["b"],
                 "KOMPOSITIONSFEL" if rad["kompositionsfel"] else "NEJ"))
        if rad.get("vantas_passera") is False and not rad["kompositionsfel"]:
            fel += 1
        if rad.get("vantas_passera") is True and rad["linje"] != "PASS":
            fel += 1
    return fel


def _guld(ut):
    """Guldgrinden over den HELA losningens celler.

    Linan ar guld forst nar BADA stationerna och LINAN ar det - tre celler,
    tre klasser, och en okand klass ar inget godkannande. Cellerna ur
    enstationskorningarna ar med: kontraktet sager "guld per station, SEDAN
    guld for linan", och det ar tva pastaenden, inte ett.
    """
    grind = guldgrind.Guldgrind(["station", "linje"])
    celler = []
    for rad in ut["korningar"]:
        if rad["fall"] != "HEL":
            continue
        if _klockan_ok(rad) is False:
            continue
        for namn, cell in sorted((rad.get("celler") or {}).items()):
            if rad["konfig"] != "LINJE" and namn == "linan":
                continue
            celler.append(cell)
    if not celler:
        return None, None
    beslut = grind.doma(celler)
    return beslut.text(), beslut.niva


def _kompositionsprov(ut):
    """Fallets tre domar stallda mot varandra.

    Ett KOMPOSITIONSFEL ar ett fall som ogat faller i LINJE och slapper
    igenom i BADA enstationskonfigurationerna. Bade halvorna kravs: ett fall
    som ogat faller ocksa i en station for sig ar inget kompositionsfel, och
    ett fall som ingen faller ar inget fel alls.
    """
    per = {}
    for rad in ut["korningar"]:
        per.setdefault(rad["fall"], {})[rad["konfig"]] = rad
    rader = []
    for namn, _f, vad, vantas in FALL:
        if namn not in per:
            continue
        d = per[namn]
        linje = d.get("LINJE")
        a = d.get("A")
        b = d.get("B")

        def _samlad(rad, vilka):
            if rad is None:
                return "EJ KORD"
            domar = [_dom_av(rad, x) for x in vilka]
            if "OGILTIG" in domar:
                return "OGILTIG"
            if any(x is None for x in domar):
                return "EJ KORD"
            if all(x == "PASS" for x in domar):
                return "PASS"
            for x in domar:
                if x == "FAIL":
                    return "FAIL"
            return "INCONCLUSIVE"

        linjedom = _samlad(linje, ("stationA", "stationB", "linan"))
        adom = _samlad(a, ("stationA",))
        bdom = _samlad(b, ("stationB",))
        rader.append({
            "fall": namn, "vad": vad, "vantas_passera": vantas,
            "alla_korda": not ({"EJ KORD", "OGILTIG"}
                               & {linjedom, adom, bdom}),
            "slag": FIXTURSLAG.get(namn), "reduktion": reduktionen(namn),
            "linje": linjedom, "a": adom, "b": bdom,
            # Bada halvorna kravs, och BADA korningarna maste ha gjorts. En
            # kontrollkorning som inte kordes ar inte ett godkannande.
            "kompositionsfel": (not ({"EJ KORD", "OGILTIG"}
                                     & {linjedom, adom, bdom})
                                and linjedom != "PASS" and adom == "PASS"
                                and bdom == "PASS"),
        })
    return rader


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strucpp", required=True,
                   help="uppackad strucpp-npm-katalog (den med dist/ och libs/)")
    p.add_argument("--runtime-include", required=True)
    p.add_argument("--byggrot", default=None)
    p.add_argument("--bas", default="https://127.0.0.1:18443")
    p.add_argument("--anvandare", default="vcassist")
    p.add_argument("--losenord", default="vcassist")
    p.add_argument("--endpoint", default="opc.tcp://127.0.0.1:14840/")
    p.add_argument("--runtime-omstart",
                   default="docker restart vcassist-openplc-v4")
    p.add_argument("--endpoint-server",
                   default="opc.tcp://172.17.0.2:4840/openplc/opcua")
    p.add_argument("--sekunder", type=float, default=70.0)
    p.add_argument("--uppvarmning", type=float, default=25.0)
    p.add_argument("--ogonrate", type=float, default=20.0)
    p.add_argument("--varvtid", type=float, default=0.3)
    p.add_argument("--fall", default=None, help="komma-lista, t.ex. HEL,K1")
    p.add_argument("--konfig", default=None, help="komma-lista, t.ex. LINJE,A")
    p.add_argument("--starta-om", action="store_true")
    p.add_argument("--ingen-omstart-per-korning", action="store_true")
    p.add_argument("--bara-scen", action="store_true",
                   help="skriv startskriptet och prova anlaggningen, kor inget fall")
    p.add_argument("--json", default=None)
    p.add_argument("--sammanstall", default=None,
                   help="komma-lista med tidigare --json-filer. Slar ihop dem, "
                        "skriver kompositionstabellen och guldgrinden, och kor "
                        "ingenting. Korningarna delas ofta upp over flera "
                        "anrop av vaggklockskal, och tabellen ska anda komma "
                        "ur samma kod som domde dem")
    p.add_argument("--serier", default=None)
    a = p.parse_args(argv)
    if a.byggrot is None:
        a.byggrot = os.path.join(os.path.expanduser("~"), ".cache", "vcassist_fas8")
    os.makedirs(a.byggrot, exist_ok=True)
    if a.serier:
        os.makedirs(a.serier, exist_ok=True)

    if a.sammanstall:
        ut = {"linje": LINJE, "korningar": []}
        for fil in a.sammanstall.split(","):
            with open(fil.strip()) as f:
                ut["korningar"].extend(json.load(f)["korningar"])
        ut["guld"], ut["guld_niva"] = _guld(ut)
        ut["kompositionsprov"] = _kompositionsprov(ut)
        fel = _skriv(ut)
        if a.json:
            with open(a.json, "w") as f:
                json.dump(ut, f, indent=1, sort_keys=True, ensure_ascii=False)
        print("\n%s" % ("ALLA FALL STAMDE" if fel == 0
                        else "%d FALL STAMDE INTE" % fel))
        return 0 if fel == 0 else 1

    kalla = _startskript()
    with open(STARTSKRIPT, "w") as f:
        f.write(kalla)
    print("  startskript skrivet: %s (%d tecken)" % (STARTSKRIPT, len(kalla)))
    if a.starta_om:
        print("  startar om VC ...")
        _starta_om_vc()
        if not _vanta_pa_bryggan(300.0):
            print("  FEL  bryggan kom aldrig upp")
            return 1
    elif not _vanta_pa_bryggan(5.0):
        print("  FEL  ingen brygga svarar; VC maste startas om for hand")
        return 1

    brygga = Klient(port=8901, tokenfil=TOKEN, timeout=180.0).anslut()
    index = bygg_validator()

    if a.bara_scen:
        post = brygga.koa(anlaggningskod(True, "pass"), desc="prov av anlaggningen")
        svar = brygga.godkann_och_vanta(post["qid"], timeout=60)
        res = ((svar.get("svar") or {}).get("result") or {})
        print(json.dumps(res.get("result"), indent=1)[:2000])
        if svar.get("state") != "done":
            print("TILLSTAND: %s\n%s" % (svar.get("state"),
                                         json.dumps(svar)[:1500]))
        brygga.stang()
        return 0

    valda = set((a.fall or ",".join(n for n, _f, _v, _p in FALL)).split(","))
    konfigar = [k for k in KONFIGURATIONER
                if k in set((a.konfig or ",".join(KONFIGURATIONER)).split(","))]
    ut = {"linje": LINJE, "korningar": []}
    forsta = True
    try:
        for namn, _f, vad, _vantas in FALL:
            if namn not in valda:
                continue
            kropparna = kroppar(namn)
            for konfig in konfigar:
                if not forsta and not a.ingen_omstart_per_korning:
                    # VC startas om mellan korningarna. Skalet ar matt (M-49):
                    # godkannandekon vaxer med en post per varv. En omstart ger
                    # dessutom varje korning SAMMA utgangslage: samma scen,
                    # samma simuleringstid, samma tomma ko - och det ar
                    # avgorande nar tva korningar ska jamforas.
                    brygga.stang()
                    print("  startar om VC infor %s/%s ..." % (namn, konfig))
                    _starta_om_vc()
                    if not _vanta_pa_bryggan(300.0):
                        raise RuntimeError("bryggan kom aldrig upp igen")
                    brygga = Klient(port=8901, tokenfil=TOKEN,
                                    timeout=180.0).anslut()
                forsta = False
                print("\n  --- %s / %s: %s ---" % (namn, konfig, vad))
                ut["korningar"].append(
                    kor_en(namn, konfig, kropparna[konfig], a, index, brygga))
                if a.json:
                    with open(a.json, "w") as f:
                        json.dump(ut, f, indent=1, sort_keys=True,
                                  ensure_ascii=False)
    finally:
        brygga.stang()

    ut["guld"], ut["guld_niva"] = _guld(ut)
    ut["kompositionsprov"] = _kompositionsprov(ut)
    fel = _skriv(ut)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(ut, f, indent=1, sort_keys=True, ensure_ascii=False)
    print("\n%s" % ("ALLA FALL STAMDE" if fel == 0
                    else "%d FALL STAMDE INTE" % fel))
    return 0 if fel == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
