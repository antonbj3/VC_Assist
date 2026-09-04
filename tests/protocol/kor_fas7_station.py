# -*- coding: utf-8 -*-
"""Fas 7, andra halvan: en STATION som styrs av ST, i en scen dar material floder.

M-48 korde grind 1-4 skarpt. Den har korningen lagger till det som fattades:
en scen dar produkter matas fram och aker (M-41), en station som stoppar dem,
och OGAT som domer om stationen gjorde sitt arbete.

    produkt pa banan --> fotocellen --> kopplaren --> OPC UA --> OpenPLC
                                                                    |
    bandet stannar <-- stalldonen <-- kopplaren <-- OPC UA <---------+
                            |
                            +--> ogats tidsserie (M-42)

Vad korningen visar, ur tests/protocol/fas7_stationen.md:

    HEL   en rimlig losning passerar grind 1-5 och blir L1-guld
    T3    nivalasning dar en flank kravs        ska fallas av OGAT
    T4    timer som nollstalls av sitt eget villkor   ska fallas av OGAT
    T5    forregling skriven som kommentar      ska fallas av OGAT
    T6    ratt forsta varvet, fel efter ett stopp mitt i sekvensen  OGAT
    NOLL  don := don, alltsa ett program som ror alla signaler utan
          att gora nagot                        ska fallas av OGAT

Kravet ar hart och kommer ur protokollet: raknar en TIDIGARE grind ut T3-T6
ar fallet fel skrivet, inte grinden bevisad. Korningen kor darfor grind 1-4
pa VARJE fall och skriver ut vem som fallde vad.

## Tva ting som INTE ar VC:s egna, och som darfor namns hogt

**Fotocellen och stalldonen simuleras av tjansten.** VC:s egen vag fran en
signal till en rorelse ar ett skriptbeteende, och ett skriptbeteende stoppar
simuleringen och dodar bryggan (M-13). VC_COMPONENTPATHSENSOR gar att skapa
men har ingen matt Python-yta (M-15), och oprovat raknas som saknat (I3).
Anlaggningen - givaren och stalldonen - bor darfor i `ANLAGGNING`, som kors
inne i VC genom godkannandekon en gang per varv. Den ar en MODELL av
processen, inte en del av losningen: den laser produkternas verkliga lagen pa
banan och skriver bandets verkliga fart. Ingen logik bor dar; logiken bor i
PLC:n, dar den ska provas.

**Anlaggningssteget ligger i SAMMA koade anrop som kopplarens donskrivning.**
Skalet ar matt: ogat raknar ett PLC-varde aldre an `PLC_FARSK_S` = 0,25 s som
icke samtidigt med sitt prov och domer INCONCLUSIVE (M-42). Tva koade anrop
per varv kostar tva pumpvarv, och da spricker den gransen.

    python3 tests/protocol/kor_fas7_station.py --strucpp <npm-katalog> \\
        --runtime-include <include> [--fall HEL,T3,...] [--starta-om]
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
from vc_assist_svc.plc.ogonkoppling import Ogonkoppling     # noqa: E402
from vc_assist_svc.plc.openplc import OpenPlcV4             # noqa: E402
from vc_assist_svc.plc.signalkarta import karta_av_rader    # noqa: E402
from vc_assist_svc.plc.skelett import Skelett               # noqa: E402

STATION = "ST7"
TOKEN = os.path.expanduser("~/.wine-vc-test/drive_c/users/anton/vc_assist_token")
STARTSKRIPT = os.path.expanduser(
    "~/.wine-vc-test/drive_c/users/anton/vc_assist_startskript.py")

# ---- linjen ---------------------------------------------------------------
#
# Talen ar LINJENS, inte trosklar: de ar det korningen bad om, och grinden
# jamfor det uppmatta mot dem i stallet for att anta dem.
MATARINTERVALL_S = 10.0     # sa langt isar produkterna skapas
BANDFART_MM_S = 250.0       # bandets normalfart
UTMATNINGSFART_MM_S = 600.0 # bandets fart medan utmatningen gar
BANLANGD_MM = 3000.0
MATARLANGD_MM = 400.0
LINJE_Y_MM = 6000.0         # vid sidan av M41-linjerna (y = 0, 2000, 4000)

# Fotocellen: en punkt PA BANAN, inte i varlden. Banavstandet ar VC:s egen
# matning (getPathDistance), och det ar den enda av de tva som inte slapar ett
# scenuppdateringssteg (M-11).
GIVARE_D_MM = 1200.0
GIVARE_HALVBREDD_MM = 400.0

# Bromsklacken: stationens enda rorliga stalldon. Den finns for att PLC:ns
# utgang ska ha nagot att ROURA i scenen - utan ett kommenderat objekt kan
# ogats scengrind `orort_trots_signal` inte stallas alls.
BROMS_INNE_Y_MM = LINJE_Y_MM - 500.0
BROMS_UTE_Y_MM = LINJE_Y_MM - 300.0
BROMS_STEG_MM = 30.0        # hur langt klacken hinner per varv

# ---- PLC:ns egna tal ------------------------------------------------------
PROCESSTID = "T#2s"
UTMATNINGSTID = "T#500ms"

# ---- korningens perturbation ----------------------------------------------
#
# Linjen pausas EN gang, mitt i en stoppfas, och lika for alla fall. T6 ar
# skrivet for att ga sonder pa just det - men en perturbation som bara det
# trasiga fallet fick hade matt fallet, inte losningen.
PAUS_EFTER_CYKEL = 2        # pausen laggs i den har stoppfasen (1-raknad)
# Fordrojningen raknas fran att SLINGAN ser stoppet ga hogt, och den ser det
# forst efter ett kopplarvarv. Sedan tar det ett varv till innan `kor` nar
# PLC:n. MATT (M-50): med 1,0 s hann processtiden ta slut fore pausen, och da
# ar T6 inte skilt fran HEL - en perturbation som landar utanfor sekvensen
# provar ingenting.
PAUS_FORDROJNING_S = 0.2    # Satt av M-50.
PAUS_LANGD_S = 1.0

# ---- signalkartan ---------------------------------------------------------
RADER = [
    ("ST7_Givare", "Puls", "givare", "BOOL", "TILL_PLC", "%IX0.0",
     False, "fotocellen vid banavstand %.0f mm" % GIVARE_D_MM),
    ("ST7_Givare", "Kor", "kor", "BOOL", "TILL_PLC", "%IX0.1",
     False, "linjens driftvaljare"),
    ("ST7_Givare", "Nod", "nodstopp", "BOOL", "TILL_PLC", "%IX0.2",
     True, "nodstoppet ar utlost - skyddad (I15)"),
    ("ST7_Don", "Stopp", "stopp", "BOOL", "FRAN_PLC", "%QX0.0",
     False, "bromsklacken ut, bandet stannar"),
    ("ST7_Don", "Slapp", "slapp", "BOOL", "FRAN_PLC", "%QX0.1",
     False, "utmatningen, bandet gar snabbt"),
]

EXTRA_DEKLARATIONER = """VAR
    laget : INT;
    flank : R_TRIG;
    tid : TON;
    utid : TON;
END_VAR"""

# Scenkoden ar formen verktygsmallarna sjalva skriver: getApplication() INLINE.
# MATT (M-48): med ett fritt `app` kontrollerar grind 4 noll namn.
SCENKOD = ("app = getApplication()\n"
           "bana = app.findComponent('ST7_Bana')\n"
           "path = bana.findBehaviour('Path')\n"
           "givare = app.findComponent('ST7_Givare')\n")


def karta():
    return karta_av_rader(STATION, RADER)


# ---- ST-kropparna ---------------------------------------------------------
#
# HEL ar den rimliga losningen. De ovriga bryter EN sak var, sa en fallning
# gar att harleda till sin orsak.

_INLEDNING = """    IF NOT kor OR nodstopp THEN
        slapp := FALSE;
        tid(IN := FALSE, PT := %(pt)s);
        utid(IN := FALSE, PT := %(ut)s);
    ELSE
""" % {"pt": PROCESSTID, "ut": UTMATNINGSTID}

_AVSLUTNING = """        END_CASE;
    END_IF;
"""

HEL = _INLEDNING + """        flank(CLK := givare);
        CASE laget OF
        0:
            IF flank.Q THEN
                laget := 1;
            END_IF;
        1:
            stopp := TRUE;
            tid(IN := TRUE, PT := %(pt)s);
            IF tid.Q THEN
                laget := 2;
            END_IF;
        2:
            stopp := FALSE;
            slapp := TRUE;
            tid(IN := FALSE, PT := %(pt)s);
            utid(IN := TRUE, PT := %(ut)s);
            IF utid.Q THEN
                laget := 3;
            END_IF;
        3:
            slapp := FALSE;
            utid(IN := FALSE, PT := %(ut)s);
            laget := 0;
""" % {"pt": PROCESSTID, "ut": UTMATNINGSTID} + _AVSLUTNING

# T3: `IF givare` i stallet for `IF flank.Q`. Nivan i stallet for flanken.
T3 = HEL.replace("""        flank(CLK := givare);
        CASE laget OF
        0:
            IF flank.Q THEN""", """        flank(CLK := givare);
        CASE laget OF
        0:
            IF givare THEN""")
assert T3 != HEL

# T4: timern startas av flankpulsen, som ar hog en enda scan. Villkoret som
# startar timern ar alltsa ocksa det som nollstaller den i nasta scan.
T4 = HEL.replace("            tid(IN := TRUE, PT := %s);" % PROCESSTID,
                 "            tid(IN := flank.Q, PT := %s);" % PROCESSTID)
assert T4 != HEL

# T5: forreglingen - bromsen ska slappa FORE utmatningen - star som kommentar.
T5 = HEL.replace("""        2:
            stopp := FALSE;
            slapp := TRUE;""", """        2:
            (* stopp := FALSE; *)
            slapp := TRUE;""").replace("""        3:
            slapp := FALSE;""", """        3:
            stopp := FALSE;
            slapp := FALSE;""")
assert T5 != HEL
# Bromsen slapper fortfarande - en rad SENARE. Enda skillnaden mot HEL ar
# alltsa att stoppet och utmatningen overlappar under utmatningspulsen.
assert "(* stopp := FALSE; *)" in T5

# T6: driftvaljaren aterstaller sekvensen till vila. Ratt forsta varvet.
T6 = HEL.replace("""    IF NOT kor OR nodstopp THEN
        slapp := FALSE;""", """    IF NOT kor OR nodstopp THEN
        stopp := FALSE;
        laget := 0;
        slapp := FALSE;""")
assert T6 != HEL

# Facitets nollpunkt (rattad av M-48): inte en tom kropp - den falls av grind
# 2 och 3 - utan ett program som ROR alla signaler utan att gora nagot.
NOLL = ("    stopp := stopp AND (givare OR NOT givare);\n"
        "    slapp := slapp AND (kor OR NOT kor) AND "
        "(nodstopp OR NOT nodstopp);\n")

FALL = [
    ("HEL", HEL, "den rimliga losningen", True),
    ("T3", T3, "nivalasning dar en flank kravs", False),
    ("T4", T4, "timer som nollstalls av sitt eget villkor", False),
    ("T5", T5, "forregling skriven som kommentar", False),
    ("T6", T6, "ratt forsta varvet, fel efter ett stopp mitt i sekvensen", False),
    ("NOLL", NOLL, "ror alla signaler, gor ingenting", False),
]


# ---- ogats plan -----------------------------------------------------------
#
# Facit for stationen, deklarerat FORE losningarna. Talen ar stationens krav,
# inte matta trosklar - och de star har, pa ett stalle, sa alla sex fallen
# doms av exakt samma facit.
#
# TVA KLOCKOR, och de gar inte lika. PLC:ns timers rakar i VAGGKLOCKA; ogats
# serie ar stamplad i SIMULERINGSTID. Med bryggan obelastad ar kvoten 1,000
# (M-08), men medan slingan gar stjal den pumpens tickbudget och kvoten faller.
# MATT i M-49: samma 2-sekunderstimer syntes som 0,65 s till 2,60 s pa ogats
# axel i samma korning. Fonstren nedan ar darfor breda med FLIT, och bredden
# ar inte en asikt om stationen utan om kopplingen mellan klockorna.
#
# Snavheten som gar forlorad har finns kvar dar den gar att mata: cellen
# `station_forsent` i tests/celler.py har ett snavt fonster och FALLS av det.
# Braketten kommer ur MATNINGSKORNINGAR, inte ur de korningar den ska doma.
#
# Forst mattes kvoten till 0,15-2,28 - en faktor 15 - och da hade fonstren
# blivit sa vida att "inom tiden" inte matt nagot. ORSAKEN var inte VC utan
# VAR EGEN pollning: `queue_list` serialiserar hela kon MED varje posts svar,
# och slingan fragade efter den flera ganger per varv. Med en lattare fraga
# (utan kod, utan svar) mattes kvoten till 1,000 i tre driftpunkter i rad:
#
#   varvtid 0,30 tathet 0,10 -> sim 45,4 / vagg 45,4 = 1,000 (378 ms/varv)
#   varvtid 0,60 tathet 0,15 -> sim 45,4 / vagg 45,5 = 1,000 (689 ms/varv)
#   varvtid 1,00 tathet 0,20 -> sim 46,0 / vagg 46,0 = 1,000 (1096 ms/varv)
#
# Braketten nedan ar darfor snav, och den snavheten ar KOPT med en mätning.
KLOCKA_LAG = 0.6            # Satt av M-49 (kvoten mattes till 1,000).
KLOCKA_HOG = 1.6            # Satt av M-49 (kvoten mattes till 1,000).
# Vad transporten scen -> PLC -> scen kostar. Genomslaget tar ett till tva
# kopplarvarv (M-39), och varvet ar en vaggklockstid som ocksa maste braketteras.
TRANSPORTVARV = 3           # Satt av M-49 (genomslag 1-2 varv, ett till marginal).
# Hur langt produkten har kvar till fotocellens bortre kant efter utmatningen,
# raknat i banans fart. Den delen gar i SIMULERINGSTID och skalas inte.
UTKORNING_S = (GIVARE_HALVBREDD_MM * 2.0 - (
    float(UTMATNINGSTID.rstrip("ms").lstrip("T#")) / 1000.0
    * UTMATNINGSFART_MM_S)) / BANDFART_MM_S


def _fonster(nominell_s, extra_lag=0.0, extra_hog=0.0):
    """PLC-sekunder -> ett fonster pa ogats axel, med klockbraketten."""
    return (max(0.0, nominell_s * KLOCKA_LAG + extra_lag),
            nominell_s * KLOCKA_HOG + extra_hog)


def _transport(varvtid_s):
    """Transporttiden scen -> PLC -> scen, pa ogats axel."""
    return TRANSPORTVARV * max(varvtid_s, 0.1) * KLOCKA_HOG
def ogonplan(rate_hz=20.0, varvtid_s=0.3):
    return {
        "template": "fas7_station",
        "rate_hz": float(rate_hz),
        "floor_z": 0.0,
        "scene": "all",
        # Bromsklacken ar det enda objekt PLC:n kommenderar. Utan `movers` kan
        # ogat inte fraga om ett kommenderat objekt verkligen rorde sig.
        "movers": {"ST7_Don/Stopp": "ST7_Broms"},
        # Fasforhallandet mellan PLC-taggen och scenens signal ar kopplarens
        # egen transporttid, matt pa ogats axel.
        "plc_par": [("stopp", "ST7_Don/Stopp")],
        # Cykeln borjar pa SCENENS fotocell, inte pa en PLC-tagg. Skalet ar
        # mätt: kopplaren skjuter in PLC:ns UTGANGAR i ogats serie, inte dess
        # ingangar, sa `plc:givare` finns aldrig dar - och en start som aldrig
        # intraffar ger "ingen cykel borjade ens" oavsett vad stationen gjorde.
        # Scenens signal ar dessutom den fysiska handelsen, last av ogat sjalvt
        # utan kopplaren emellan.
        # Sekvensen doms pa SCENENS signaler, inte pa PLC-taggarna. Bada bar
        # samma handelse - kopplaren skriver PLC:ns utgang rakt in i scenen -
        # men scenens signal laeses av ogat sjalvt, i ogats egen takt, utan en
        # transporttid mellan matning och stampel. Det ar den av de tva som ar
        # ett matt pa NAR stationens stalldon fick sin order.
        "sekvens": {
            "start": {"signal": "ST7_Givare/Puls", "flank": "RISE"},
            "steg": [
                # bromsen ut: bara transporten, ingen timer
                {"signal": "ST7_Don/Stopp", "flank": "RISE",
                 "min_s": 0.0, "max_s": _transport(varvtid_s)},
                # bromsen slapper efter processtiden (+ ev. driftpaus)
                {"signal": "ST7_Don/Stopp", "flank": "FALL",
                 "min_s": _fonster(2.0)[0],
                 "max_s": _fonster(2.0 + PAUS_LANGD_S,
                                   extra_hog=_transport(varvtid_s))[1]},
                {"signal": "ST7_Don/Slapp", "flank": "RISE",
                 "min_s": _fonster(2.0)[0],
                 "max_s": _fonster(2.0 + PAUS_LANGD_S,
                                   extra_hog=_transport(varvtid_s))[1]},
                {"signal": "ST7_Don/Slapp", "flank": "FALL",
                 "min_s": _fonster(2.5)[0],
                 "max_s": _fonster(2.5 + PAUS_LANGD_S,
                                   extra_hog=_transport(varvtid_s))[1]},
                # Produkten MASTE lamna stationen. Utan den har raden ar en
                # station som stoppar allt for evigt bara "obestambar" - den
                # gor ju en riktig cykel forst - och det ar for snallt.
                # Utkorningen gar i banans fart, alltsa i SIMULERINGSTID, och
                # skalas darfor inte med klockbraketten.
                {"signal": "ST7_Givare/Puls", "flank": "FALL",
                 "min_s": _fonster(2.5)[0] + UTKORNING_S,
                 "max_s": _fonster(2.5 + PAUS_LANGD_S,
                                   extra_hog=_transport(varvtid_s))[1]
                          + UTKORNING_S},
            ],
            "min_cykler": 3,
        },
        "forregling": [["ST7_Don/Stopp", "ST7_Don/Slapp"]],
        "parts": ["ST7_Broms"],
        "tools": [],
        # Driftvaljaren ar med for att PERTURBATIONEN ska sta i underlaget.
        # En storning som inte syns i serien gar inte att skilja fran en
        # storning som aldrig kom.
        "signals": ["ST7_Givare/Puls", "ST7_Givare/Kor",
                    "ST7_Don/Stopp", "ST7_Don/Slapp"],
    }


# ---- scenen ---------------------------------------------------------------

MALLKOD = """
app = getApplication()
for _c in list(app.Components):
    if _c.Name[:4] == 'ST7_':
        app.deleteComponent(_c)
_p = app.createComponent()
_p.Name = 'ST7_Mall'
_f = _p.RootFeature.createFeature(VC_BLOCK, "kropp")
for _q in _f.Properties:
    if _q.Name in ("Length", "Width", "Height"):
        _q.Value = 200.0
_p.RootFeature.rebuild()
_m = _p.PositionMatrix
_m.translateAbs(-5000.0 - _m.P.X, %(y).1f - _m.P.Y, 0.0 - _m.P.Z)
_p.PositionMatrix = _m
"""

SIGNALKOD = """
app = getApplication()
for _namn, _signaler in (('ST7_Givare', ('Puls', 'Kor', 'Nod')),
                         ('ST7_Don', ('Stopp', 'Slapp'))):
    _k = app.createComponent()
    _k.Name = _namn
    for _s in _signaler:
        _b = _k.createBehaviour(VC_BOOLEANSIGNAL, _s)
        _b.Value = False
"""

BROMSKOD = """
app = getApplication()
_b = app.createComponent()
_b.Name = 'ST7_Broms'
_f = _b.RootFeature.createFeature(VC_BLOCK, "klack")
for _q in _f.Properties:
    if _q.Name == "Length":
        _q.Value = 120.0
    elif _q.Name == "Width":
        _q.Value = 120.0
    elif _q.Name == "Height":
        _q.Value = 400.0
_b.RootFeature.rebuild()
_m = _b.PositionMatrix
_m.translateAbs(%(x).1f - _m.P.X, %(y).1f - _m.P.Y, 0.0 - _m.P.Z)
_b.PositionMatrix = _m
"""


def _startskript():
    """Koden som bygger stationslinjen, FORE startSimulation().

    Ordningen ar inte fri: M-40 matte att en matare som byggs i en redan
    korande simulering aldrig fyrar, hur ratt den an ar kopplad.
    """
    delar = [MALLKOD % {"y": LINJE_Y_MM}]
    delar.append(R.generera("flodeslinje", {
        "name": STATION, "mall": "ST7_Mall",
        "intervall": MATARINTERVALL_S, "grans": 100000,
        "hastighet": BANDFART_MM_S, "banlangd": BANLANGD_MM,
        "matarlangd": MATARLANGD_MM, "x": 0.0, "y": LINJE_Y_MM,
    }).replace("from __future__ import print_function\n", ""))
    delar.append(SIGNALKOD)
    delar.append(BROMSKOD % {"x": MATARLANGD_MM + GIVARE_D_MM,
                             "y": BROMS_INNE_Y_MM})
    kropp = "\n".join(delar)
    inne = "\n".join(("    " + r) if r.strip() else ""
                     for r in kropp.splitlines())
    return (
        "# Skrivet av tests/protocol/kor_fas7_station.py. Kors av bridge_cmd\n"
        "# FORE startSimulation(); dar, och bara dar, initieras beteendena.\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "import traceback\n"
        "\n"
        "_LOGG = os.path.join(os.path.expanduser('~'), 'vc_assist_fas7.json')\n"
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
# Ett steg av processen: las produkternas verkliga lagen, satt fotocellen,
# och lat stalldonen verka. INGEN logik - villkoren nedan ar fysik, inte
# sekvens. Koden kors inne i VC (py2.7) genom godkannandekon (I12).

ANLAGGNING = """import json
app = getApplication()
sim = getSimulation()
bana_k = app.findComponent('ST7_Bana')
path = bana_k.findBehaviour('Path')

# Produkterna far unika namn ur sin egen skapelsetid. Klonerna arver mallens
# namn, och tva objekt med samma namn hade blivit EN serie i ogats scenbild -
# en produkt som teleporterade mellan tva lagen.
prod = []
for c in list(app.Components):
    n = c.Name
    if n == 'ST7_Mall':
        d = c.getPathDistance()
        if d >= 0.0:
            n = 'ST7_P%%02d' %% int(round(c.CreationTime / %(intervall).6f))
            c.Name = n
    if n[:5] == 'ST7_P':
        prod.append({'namn': n, 'd': c.getPathDistance()})

# Fotocellen: en produkt inom fonstret kring banavstandet.
puls = False
for p in prod:
    if abs(p['d'] - %(gd).6f) <= %(gh).6f:
        puls = True

g = app.findComponent('ST7_Givare')
g.findBehaviour('Puls').Value = bool(puls)
g.findBehaviour('Kor').Value = %(kor)s
g.findBehaviour('Nod').Value = False

# Stalldonen. Bromsen vinner over utmatningen nar bada begars samtidigt: en
# klamd produkt far inte matas ut. Konflikten TIGS inte - den rapporteras.
d = app.findComponent('ST7_Don')
%(donskrivning)s
stopp = bool(d.findBehaviour('Stopp').Value)
slapp = bool(d.findBehaviour('Slapp').Value)
if stopp:
    path.Speed = 0.0
elif slapp:
    path.Speed = %(snabb).6f
else:
    path.Speed = %(normal).6f

b = app.findComponent('ST7_Broms')
m = b.PositionMatrix
mal = %(ute).6f if stopp else %(inne).6f
dy = mal - m.P.Y
if dy > %(steg).6f:
    dy = %(steg).6f
elif dy < -%(steg).6f:
    dy = -%(steg).6f
m.translateAbs(0.0, dy, 0.0)
b.PositionMatrix = m

print(json.dumps({'t': sim.SimTime, 'speed': path.Speed, 'puls': puls,
                  'stopp': stopp, 'slapp': slapp,
                  'konflikt': bool(stopp and slapp),
                  'broms_y': b.PositionMatrix.P.Y,
                  'antal': len(prod), 'prod': prod}))
"""


def anlaggningskod(kor, donskrivning):
    return ANLAGGNING % {
        "intervall": MATARINTERVALL_S, "gd": GIVARE_D_MM,
        "gh": GIVARE_HALVBREDD_MM, "kor": "True" if kor else "False",
        "snabb": UTMATNINGSFART_MM_S, "normal": BANDFART_MM_S,
        "ute": BROMS_UTE_Y_MM, "inne": BROMS_INNE_Y_MM,
        "steg": BROMS_STEG_MM, "donskrivning": donskrivning,
    }


class Stationskopplare(Kopplare):
    """Kopplaren, med anlaggningssteget i SAMMA koade anrop som donskrivningen.

    Skalet ar matt och star i modulens huvud: ogat raknar ett PLC-varde aldre
    an PLC_FARSK_S som icke samtidigt med sitt prov, och tva koade anrop per
    varv kostar tva pumpvarv.

    Kopplarens egna tider bar darfor ocksa anlaggningens kostnad. Det ar
    avsiktligt och sags i M-49: `skriv_vc_ms` ar inte langre bara en
    signalskrivning.
    """

    def __init__(self, *a, **kw):
        Kopplare.__init__(self, *a, **kw)
        self.kor_signal = True
        self.anlaggning = []      # anlaggningens svar, ett per varv
        # Hur ofta kon fragas om postens utfall. MATT (M-49): varje fraga ar
        # en bryggbegaran som kostar pumptid, och `queue_list` serialiserar
        # HELA kon - som vaxer med varje post. En tat pollning stryper darfor
        # simuleringen, och alltmer ju langre korningen gar.
        self.pollintervall = 0.1
        # En SKYDDAD ingang gar inte att driva harifran, och det ar ratt.
        # MATT: opcuakonfig.variabel ger en skyddad tagg lasrattigheter bara,
        # och en WriteRequest mot den svarar BadInternalError - kopplaren foll
        # efter tre raka fel (M-39:s sparr, som gjorde precis sitt jobb).
        # Sakerhetskedjan hor inte till den genererade logiken (I15): den bor
        # pa en certifierad sakerhets-PLC som logiken far ligga bredvid. Att
        # lata kopplaren driva den hade varit att bygga just det systemet.
        self.skyddade = [s for s in self.till_plc if s.skyddad]
        self.till_plc = [s for s in self.till_plc if not s.skyddad]

    def _vanta_latt(self, qid, timeout=60.0):
        """Vantar ut posten UTAN att be om kons svar.

        MATT (M-49): `queue_list` serialiserar hela kon MED varje posts svar,
        och kon vaxer med en post per varv. Efter ~1500 poster ar svaret over
        protokollets 1 MiB och bryggan svarar E_TOO_LARGE - mitt i en korning,
        pa en fraga som bara skulle ha last ett tillstand. Innan dess kostar
        varje pollning mer och mer pumptid, och simuleringen tappar fart i
        takt med att kon vaxer. Vi fragar darfor utan kod och utan svar.
        """
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
            rader.append("b = d.findBehaviour(%r)" % str(s.scensignal))
            rader.append("if b is not None:")
            rader.append("    b.Value = %r" % (bool(v),))
        kod = anlaggningskod(self.kor_signal, "\n".join(rader) or "pass")
        post = self.brygga.koa(kod, desc="anlaggningen: ett processteg")
        self.brygga.godkann(post["qid"])
        ut = self._vanta_latt(post["qid"])
        if ut["state"] != "done":
            raise RuntimeError("anlaggningssteget slutade som %r" % ut["state"])
        self.anlaggning.append({"qid": post["qid"], "state": ut["state"]})
        return {}


# ---- VC ------------------------------------------------------------------

# Den virtuella skarmen. VC far ALDRIG hamna pa operatorens skarm - hen sitter
# vid datorn. `os.environ.get("DISPLAY", ":99")` ar precis fallan: ett arvt
# DISPLAY ser ut som ett standardvarde och ar det inte. Skarmen sags darfor
# uttryckligen, och laeses tillbaka ur processen efterat.
HEADLESS_DISPLAY = ":99"        # docs/spec/00_arbetssatt.md: VC kors headless.


def _vc_pids():
    """VC:s egna processer, ur /proc.

    INTE `pgrep -f`: monstret star i den egna kommandoraden och pgrep traffar
    da sin egen sokning. Kravet ar darfor att programmet i argv[0] ar VC:s exe,
    inte att strangen finns nagonstans i raden.
    """
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
    # Skarmen SATTS, den arvs inte. Utan raden hamnar VC pa den skarm som rakar
    # sta i miljon, och det ar operatorens.
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
        """Anslut och KRAV att adressrummet ar stationens.

        `las` svarar None for en tagg den inte hittar, och kopplaren skriver da
        inget - tyst. En korning mot forra programmets adressrum sag darfor ut
        som en station som aldrig gjorde nagot. Namnen kontrolleras nu vid
        anslutningen i stallet, dar felet gar att peka pa.
        """
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
            # Stang FORST. asyncua:s synkrona klient haller en trad som inte
            # ar daemon: kastar man med en oppen klient tar processen aldrig
            # slut, och korningen ser ut att hanga i stallet for att falla.
            self.stang()
            raise RuntimeError(
                "OPC UA-servern saknar %s. Adressrummet ar inte stationens: "
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
        ut = {}
        for t in taggar:
            n = self._noder.get(t)
            ut[t] = None if n is None else n.read_value()
        return ut

    def skriv(self, varden):
        for t, v in varden.items():
            n = self._noder.get(t)
            if n is not None and v is not None:
                n.write_value(bool(v) if isinstance(v, bool) else v)


# ---- ett fall -------------------------------------------------------------

def granska(namn, kropp, sk, k, byggrot, strucpp, index):
    """Grind 1-4 over kandidaten. Returnerar (dom, kandidat)."""
    kand = S.Kandidat.fran_modellsvar(sk, kropp, SCENKOD)
    dom = S.granska_station(kand, k, index=index, strucpp_paket=strucpp,
                            byggkatalog=os.path.join(byggrot, namn),
                            stanna_vid_forsta=False)
    return dom, kand


def starta_om_runtimen(kommando, bas, anvandare, losenord, tak_s=180.0):
    """Starta om HELA runtimeprocessen och vanta tills den svarar igen.

    MATT: OPC UA-pluginet laser sin conf nar RUNTIMEPROCESSEN startar, inte
    nar PLC:n startar. En uppladdning som bygger ratt program och kopierar
    ratt conf/opcua.json ger anda det FORRA adressrummet - `matin`/`matut`
    lag kvar over bade en programbyte och en stop/start av PLC:n. Bara en
    omstart av processen bytte dem mot stationens egna noder.
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
    kalla = kand.st_kalla + paket.konfigurationstext(STATION)
    ut = os.path.join(byggrot, namn, "drift")
    forbygge = paket.kompilera(kalla, os.path.join(ut, "forbygge"), strucpp)
    konfig = opcuakonfig.konfiguration(k, forbygge, endpoint_server)
    zipvag, _karta = paket.bygg_projekt(kalla, os.path.join(ut, "arkiv"),
                                        strucpp, runtime_include,
                                        opcua_konfig=konfig)
    klient = OpenPlcV4(bas, anvandare, losenord, tillat_osignerat=True)
    klient.skapa_forsta_anvandare()
    # STOPPA forst. MATT: `start-plc` mot en runtime som redan kor svarar
    # START:OK och status stannar pa RUNNING - med det GAMLA programmet och det
    # GAMLA adressrummet. Uppladdningen lyckas, bygget lyckas, konfigurationen
    # kopieras, och slingan kor vidare mot forra korningens noder. Det ar samma
    # felklass som M-20:s "START:OK betyder inte att PLC:n kor", men at andra
    # hallet: RUNNING betyder inte att det ar DITT program som kor.
    klient.stoppa()
    klient.ladda_och_starta(zipvag)
    # ... och sedan hela processen, annars star forra korningens adressrum kvar.
    return starta_om_runtimen(omstartskommando, bas, anvandare, losenord)


# Hur tatt PLC:ns utgangar laeses in i ogats serie MELLAN kopplarvarven.
# Ogat raknar ett varde aldre an PLC_FARSK_S = 0,25 s (pa SIN axel) som icke
# samtidigt med provet och domer INCONCLUSIVE (M-42). Vardets alder ar i
# praktiken tiden sedan forra inskottet, sa inskotten maste ligga tatare an sa
# med marginal for att simuleringstiden gar ojamnt under lasten. En OPC
# UA-lasning kostar 0,4 ms (M-20), sa tatheten ar nastan gratis - det dyra ar
# scenskrivningen, och den ligger kvar i kopplarvarvet.
PLC_TATHET_S = 0.05         # Satt av M-49.


def kor_slingan(brygga, kopplare, ogonkoppling, sekunder, paus_i_cykel,
                varvtid_s=0.0, plc_tathet_s=PLC_TATHET_S):
    """Sluter slingan tills tiden gatt. Returnerar en logg over varven."""
    logg = {"varv": 0, "paus": None, "konflikter": 0, "fel": []}
    taggar = [x.tagg for x in kopplare.fran_plc]
    t_start = time.time()
    stoppflanker = 0
    forra_stopp = False
    paus_till = None
    varvtider = []
    while time.time() - t_start < sekunder:
        t_varv = time.time()
        try:
            v = kopplare.kor_varv()
        except Exception as e:
            # Kopplaren gav upp. Ogat far veta det ROP RAKT UT, sa serien far
            # ett hal med skal i stallet for gamla tal (M-42).
            ogonkoppling.bryt("kopplaren gav upp: %s" % str(e)[:120])
            raise
        logg["varv"] += 1
        if v.fel:
            logg["fel"].append(v.fel)
            ogonkoppling.bryt("kopplarvarv %d foll: %s" % (v.nr, v.fel))
        if v.fran_plc.get("stopp") and v.fran_plc.get("slapp"):
            logg["konflikter"] += 1
        stopp = bool(v.fran_plc.get("stopp"))
        if stopp and not forra_stopp:
            stoppflanker += 1
            if stoppflanker == paus_i_cykel and paus_till is None:
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
        # Resten av varvet gar till rena PLC-avlasningar. Varvtiden hallas nere
        # med FLIT: ett kopplarvarv sa fort det gar tar hela pumpens tickbudget,
        # simuleringstiden faller efter och tas igen i skov. Men glesa varv gor
        # PLC-vardena gamla pa ogats axel, och da domer ogat INCONCLUSIVE. De
        # tva kraven drar at var sitt hall, sa de skiljs at: scenskrivningen
        # glest, PLC-avlasningen tatt.
        forsta = True
        while forsta or time.time() - t_varv < varvtid_s:
            forsta = False
            t_las = time.time()
            try:
                varden = kopplare.ua.las(taggar)
            except Exception as e:
                ogonkoppling.bryt("PLC-avlasningen foll: %s"
                                  % str(e)[:100])
                logg["lasfel"] = logg.get("lasfel", 0) + 1
                break
            ogonkoppling.skjut_in(varden, t_las)
            logg["plc_prov"] = logg.get("plc_prov", 0) + 1
            sov = plc_tathet_s - (time.time() - t_las)
            if sov > 0:
                time.sleep(sov)
    varvtider.sort()
    if varvtider:
        logg["varv_ms"] = {
            "median": round(varvtider[len(varvtider) // 2], 1),
            "p95": round(varvtider[int(0.95 * (len(varvtider) - 1))], 1),
            "max": round(varvtider[-1], 1)}
    return logg


def kor_fall(namn, kropp, vad, vantas_passera, a, sk, k, index, brygga):
    """Hela vagen for ett fall: grind 1-4, driftsattning, ogat, guldgrinden."""
    rad = {"namn": namn, "vad": vad, "vantas_passera": vantas_passera}
    dom, kand = granska(namn, kropp, sk, k, a.byggrot, a.strucpp, index)
    rad["forgrindar"] = dict((g, (True if v is True else str(v)))
                             for g, v in dom.forgrindar.items())
    rad["forsta_fallande"] = dom.forsta_fallande
    rad["grindarnas_egna_ord"] = dict((g, t) for g, t in dom.utdata.items() if t)
    if not dom.ok:
        # Fallet falldes fore ogat. Det ar ett SVAR, inte ett hinder: for
        # T3-T6 ar det ett protokollbrott och sags rent ut.
        rad["ogat"] = None
        rad["cell"] = dom.till_cell(namn, "station")
        return rad

    rad["plc_tillstand"] = driftsatt(kand, k, a.byggrot, namn, a.strucpp,
                                     a.runtime_include, a.bas, a.anvandare,
                                     a.losenord, a.endpoint_server,
                                     a.runtime_omstart)
    ua = UaKanal(a.endpoint).anslut([s.tagg for s in k.signaler])
    try:
        simtid = brygga.simtid()
        plan = ogonplan(a.ogonrate, a.varvtid)
        start = brygga.oga_start(plan, simtid)
        rad["oga_start"] = start
        ogon = Ogonkoppling(brygga)
        ogon.synka()
        # Kopplaren skjuter INTE sjalv in i ogat. MATT (M-49): dess inskott
        # sker efter scenskrivningen, och en scenskrivning som fastnat i
        # pumpen i sju sekunder gav ett PLC-varde som var sju sekunder gammalt
        # nar det landade. Slingan laser och skjuter in i stallet, direkt efter
        # varandra, och sager sjalv ifran nar kopplaren ger upp.
        kopplare = Stationskopplare(k, ua, brygga, oga=None)
        rad["slinga"] = kor_slingan(brygga, kopplare, ogon, a.sekunder,
                                    PAUS_EFTER_CYKEL, a.varvtid,
                                    a.plc_tathet)
        rad["kopplaren"] = kopplare.sammanfattning()
        rad["anlaggning"] = {"steg": len(kopplare.anlaggning)}
    finally:
        ua.stang()
    stopp = brygga.oga_stopp()
    rad["oga_stopp"] = dict((x, stopp.get(x))
                            for x in ("samples", "dur_s", "rate_hz", "saknade"))
    data = stopp.get("data")
    if data is None:
        rad["ogat"] = None
        rad["fel"] = "ogats serie kom inte med i svaret (%s)" % stopp.get(
            "for_stor_for_svaret")
        rad["cell"] = dom.till_cell(namn, "station")
        return rad
    text, rapport, analys = A.doma(data, ogonplan(a.ogonrate, a.varvtid))
    rad["ogat"] = text
    rad["ogats_dom"] = list(rapport.dom)
    rad["harledt"] = {"station": analys.harledt.get("station"),
                      "flanker": (analys.harledt.get("timing") or {}).get("flanker")}
    rad["cell"] = dom.till_cell(namn, "station", eyes=text)
    if a.serier:
        with open(os.path.join(a.serier, "%s.json" % namn), "w") as f:
            json.dump(data, f)
    return rad


# ---- huvudprogram ---------------------------------------------------------

def _skriv(ut):
    print("\n=== fas 7: stationen ===")
    fel = 0
    for rad in ut["fall"]:
        dom = (rad.get("ogats_dom") or ["EJ KORD", ""])[0]
        gick = dom == "PASS"
        stamde = gick == rad["vantas_passera"]
        print("\n  %-5s %s  %s" % (rad["namn"], "OK  " if stamde else "FEL ",
                                   rad["vad"]))
        for g in ("statisk_analys", "deklarationsmatchning", "anropsvalidering",
                  "kompilering"):
            v = rad["forgrindar"].get(g)
            print("        %-24s %s" % (g, "GODKAND" if v is True else v))
        if rad.get("ogats_dom"):
            print("        %-24s %s %s" % ("ogat", rad["ogats_dom"][0],
                                           rad["ogats_dom"][1][:110]))
        elif rad.get("fel"):
            print("        %-24s %s" % ("ogat", rad["fel"]))
        if rad.get("slinga"):
            s = rad["slinga"]
            print("        %-24s %d varv, paus %s, %d konflikter"
                  % ("slingan", s["varv"], s.get("paus"), s["konflikter"]))
        if not stamde:
            fel += 1
    print("\n  guldgrinden: %s" % ut["guld"])
    return fel


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strucpp", required=True,
                   help="uppackad strucpp-npm-katalog (den med dist/ och libs/)")
    p.add_argument("--runtime-include", required=True)
    p.add_argument("--byggrot", default=None)
    p.add_argument("--bas", default="https://127.0.0.1:18443")
    p.add_argument("--anvandare", default="vcassist")
    p.add_argument("--losenord", default="vcassist")
    p.add_argument("--endpoint", default="opc.tcp://127.0.0.1:14840/",
                   help="adressen KLIENTEN ansluter till")
    p.add_argument("--runtime-omstart",
                   default="docker restart vcassist-openplc-v4",
                   help="kommandot som startar om HELA runtimeprocessen; "
                        "OPC UA-adressrummet byts inte utan den")
    p.add_argument("--endpoint-server",
                   default="opc.tcp://172.17.0.2:4840/openplc/opcua",
                   help="adressen servern binder till (containerns egen)")
    p.add_argument("--sekunder", type=float, default=60.0)
    p.add_argument("--ogonrate", type=float, default=20.0,
                   help="ogats provtakt i Hz; varje prov kostar ett sim.update()")
    p.add_argument("--plc-tathet", type=float, default=PLC_TATHET_S,
                   help="sekunder mellan rena PLC-avlasningar")
    p.add_argument("--varvtid", type=float, default=0.0,
                   help="kortaste varvtid i sekunder; halller nere pumptrycket")
    p.add_argument("--fall", default=None, help="komma-lista, t.ex. HEL,T3")
    p.add_argument("--starta-om", action="store_true")
    p.add_argument("--ingen-omstart-per-fall", action="store_true",
                   help="starta INTE om VC mellan fallen; kon vaxer da over "
                        "hela korningen och bromsar simuleringen")
    p.add_argument("--bara-scen", action="store_true",
                   help="skriv startskriptet och prova scenen, kor inget fall")
    p.add_argument("--json", default=None)
    p.add_argument("--serier", default=None,
                   help="katalog att skriva ogats rasserier till")
    a = p.parse_args(argv)
    if a.byggrot is None:
        a.byggrot = os.path.join(os.path.expanduser("~"), ".cache", "vcassist_fas7")
    os.makedirs(a.byggrot, exist_ok=True)
    if a.serier:
        os.makedirs(a.serier, exist_ok=True)

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
    k = karta()
    sk = Skelett.av_karta(k, EXTRA_DEKLARATIONER)
    index = bygg_validator()

    if a.bara_scen:
        kopplare_kod = anlaggningskod(True, "pass")
        post = brygga.koa(kopplare_kod, desc="prov av anlaggningen")
        svar = brygga.godkann_och_vanta(post["qid"], timeout=60)
        print(json.dumps(((svar.get("svar") or {}).get("result") or {}).get(
            "result"), indent=1)[:1500])
        brygga.stang()
        return 0

    valda = set((a.fall or ",".join(n for n, _k, _v, _p in FALL)).split(","))
    ut = {"station": STATION, "skelett": sk.text(), "fall": []}
    forsta = True
    try:
        for namn, kropp, vad, vantas in FALL:
            if namn not in valda:
                continue
            if not forsta and not a.ingen_omstart_per_fall:
                # VC startas om mellan fallen. Skalet ar mätt: godkannandekon
                # vaxer med en post per varv och `queue_list` serialiserar hela
                # kon - efter ~1500 poster faller den pa protokollets 1 MiB, och
                # langt innan dess kostar varje pollning mer pumptid an den
                # forra. En omstart ger dessutom varje fall SAMMA utgangslage:
                # samma scen, samma simuleringstid, samma tomma ko.
                brygga.stang()
                print("  startar om VC infor %s ..." % namn)
                _starta_om_vc()
                if not _vanta_pa_bryggan(300.0):
                    raise RuntimeError("bryggan kom aldrig upp igen")
                brygga = Klient(port=8901, tokenfil=TOKEN,
                                timeout=180.0).anslut()
            forsta = False
            print("\n  --- %s: %s ---" % (namn, vad))
            ut["fall"].append(kor_fall(namn, kropp, vad, vantas, a, sk, k,
                                       index, brygga))
    finally:
        brygga.stang()

    grind = guldgrind.Guldgrind(["station"])
    celler = [r["cell"] for r in ut["fall"]
              if r["namn"] == "HEL" and r.get("cell")]
    beslut = grind.doma(celler)
    ut["guld"] = beslut.text()
    ut["guld_niva"] = beslut.niva
    fel = _skriv(ut)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(ut, f, indent=1, sort_keys=True, ensure_ascii=False)
    print("\n%s" % ("ALLA FALL STAMDE" if fel == 0
                    else "%d FALL STAMDE INTE" % fel))
    return 0 if fel == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
