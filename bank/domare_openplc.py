# -*- coding: utf-8 -*-
"""OpenPLC-domaren: dömer en ST-lösning mot uppgiftens spårfacit genom körning.

Varför den finns. `docs/spec/85_bankkontraktet.md` §2 förbjuder att ett facit
kommer ur koden som döms. `bank/domare.py` dömer spårfacit genom vår egen
ST-tolk, alltså är tolken både den som prövas och den som dömer — precis den
tautologi kontraktet förbjuder. `M-110` skrev det rakt ut: *"Domen kommer ur
vår ST-tolk, inte ur OpenPLC."*

OpenPLC Runtime v4 ligger utanför vår kod, är motorn produkten faktiskt
använder, och är skriven av någon annan. Den är därför en laglig facitkälla
(sort 1 i §2: en annan implementation). Den här domaren har **samma
domarmekanik** som `domare.py` — samma Dom, samma Brist, samma Domsfel, samma
punktkrav, invarianter och flankräkning — med en annan motor under. Att den
skillnaden spelar roll är mätt: `M-125` fann att 22 av 81 konstruktioner ger
olika värden i vår tolk och i OpenPLC (avrundning REAL->INT, int32-svep,
REAL som float32), och `M-108` steg 3 fann backendfel som ingen av våra
grindar ser.

Yta: `dom(post, st_text, spar=None, stationsdom=None, rigg=None, ...)` -> Dom.
Dom/Brist/Domsfel/`forgrindsbrist` **importeras** ur `domare.py`, dupliceras
aldrig: två domarmekaniker som ska vara lika men är två kodstycken glider isär
utan att någon ser det.

Mekanik, steg för steg:

(a) Förgrinden först: `domare.forgrindsbrist` återanvänds. Fäller grind 1-4
    körs spåret inte alls (I1).
(b) Program: signalerna i `post["control"]["signals"]` mappas namn -> %IX/%QX
    (skilda indexrum för %I och %Q, BOOL->X bitvis, INT->W, DINT/REAL->D),
    samma mönster som `tests/protocol/kor_A1_beteende.py::bygg_program`.
    Lösningens POU parsas med `st.lasare`, kartans VAR-block läggs FÖRST
    (I10: modellen skriver aldrig deklarationerna) och texten skrivs tillbaka
    med `st.skrivare`. Adresserna är alltså våra, aldrig modellens.
(c) Bygge + start: STruC++ -> arkiv -> upload -> SUCCESS -> RUNNING, över
    `plc.paket`, `plc.opcuakonfig` och `plc.openplc`.
(d) Körning: varje facitsekvens körs i realtid mot en startad PLC. Alla
    ingångar nollställs, sekvensens t=0-stimuli skrivs, kanalen kontrolleras
    med återläsning, och därefter körs sekvensen: insignaler skrivs vid sina
    `t_ms` över OPC UA, alla mappade signaler samplas var 10:e ms. Spåret
    samplas om till 20 ms scanrutnät och döms som i `domare.py`.
(e) Sekvenserna isoleras med en omstart av PLC:n mellan varje. `domare.py`
    bygger en ny Tolk per sekvens; utan omstart hade OpenPLC-domaren dömt en
    annan storhet (sekvenser i följd) än tolkdomaren (sekvenser var för sig).

## Vad som är en DOM och vad som är ett DOMSFEL

Den här gränsen är hela poängen med punkt A2:s trasiga fixtur, och den går
inte mellan "det gick bra" och "det gick illa" utan mellan **ett påstående om
lösningen** och **ett påstående om maskinen**.

**Dom (UNDERKÄND, en Brist med namn):**

* `openplc:kompilerar_inte` — STruC++ eller OpenPLC:s g++ kördes och svarade
  NEJ om den här texten. Det är lösningens egenskap. Trasig fixtur, mätt
  2026-09-05 (M-146): en dubblerad CASE-etikett passerar vår ST-tolk och
  STruC++:s frontend men fälls av OpenPLC:s backend med
  `duplicate case value`.
* `openplc:startar_inte` — programmet byggde men runtimen gick till EMPTY,
  alltså laddades .so:n inte. Också lösningens egenskap (M-20: ett .so utan
  debugtabell ger START:OK följt av EMPTY).
* `openplc:signal_omdeklarerad` — lösningen deklarerar om en mappad signal.
  Deklarationerna ägs av kartan (I10).
* `openplc:skriver_egen_ingang` — lösningen tilldelar en mappad INGÅNG och
  skrev över facits stimulus, så spåret prövar inte det facit ber om. Symptomet
  är detsamma som en kanal som tappar värden, och skillnaden avgörs statiskt:
  ligger namnet bland lösningens egna tilldelningar är det lösningens fel.
  Mätt 2026-09-05 (M-146 §4) på P-07:s motbevis
  `ridans_signal_tvingas_hog_i_koden`, som utan den här klassningen blev ett
  Domsfel — alltså ingen dom alls — fast lösningen var den som var fel.
* punktkrav, invarianter och flanker: exakt `domare.py`:s bristkoder.

**Domsfel (ingen dom alls, ett undantag i klartext):**

* riggen saknas: STruC++-paketet, runtime-headerna eller `node` finns inte.
* kompilatorn gick inte att köra, eller svarade inte inom tidsgränsen.
* OpenPLC svarar inte, uppladdningen når inte fram, kompileringen står kvar i
  COMPILING, runtimen når inte RUNNING inom tidsgränsen.
* OPC UA-servern går inte att nå, kanalen faller mitt i en sekvens, en
  sekvens svarar inte inom sitt tak, en skriven insignal läses inte tillbaka.
* uppgiften saknar spårfacit, sekvenser eller signaler, facit nämner en
  signal som inte finns, eller en signal går inte att mappa.

En rigg som är nere ska aldrig kunna se ut som en lösning som är fel. Det är
skälet att `plc/paket.py` fick `Kompilatorfel` som egen klass: utan den var
"kompilatorn saknas" och "koden kompilerar inte" samma undantag.

## Toleransen, och varifrån varje siffra kommer

`domare.py` läser punktkravet i exakt det scan vars klocka står på `t_ms`.
Över en riktig kedja går det inte: OPC UA-pluginen ligger mellan skrivningen
och bildtabellen, och mellan bildtabellen och läsningen.

* `MARGINAL_SCAN` = 2 scan. PLC:ns egen uppmätta svarstid, **M-20**: exakt två
  scan, 40,0 ms vid 20 ms scanperiod. Ärvs ur `domare.py`, räknas inte om.
* Kanalfas = 2 scan. **M-108** mätte Δ = +2 scan konstant över 1, 50 och 200
  scans horisont i nio mätningar med noll avvikelse: skriv->tabell ≤1 scan vid
  10 ms pluginsynk, tabell->läsning ≤1 scan.
* `TOLERANS_SCAN` = 2 + 2 = 4 scan = 80 ms.

Så tillämpas den:

* punktkrav vid `t`: godkänt om det väntade värdet syns i något scan i
  [t, t + 4 scan]. Domaren mäter dessutom **vid vilket scan** det syntes och
  lämnar det i `Dom.matpunkter`, så att toleransen går att pröva mot sin egen
  mätning i stället för att tros på.
* invariant: fäller först när villkoret gäller och kravet brister i fem
  följande scan i rad (>4 scan = bortom kanal + svarstid, alltså logik).
* flankfönster: [fran_ms, till_ms + 4 scan]. Kanalen kan bara försena, aldrig
  tidigarelägga: en flank kan inte komma före insignalen som orsakade den.

Vad som inte går att mappa (fail-closed, aldrig grönt): bara elementära typer
med en bildtabellbredd mappas (BOOL/BYTE/SINT/USINT/WORD/INT/UINT/DWORD/
DINT/UDINT/REAL/LWORD/LINT/ULINT/LREAL). TIME saknar storleksklass i
bildtabellen, och STRING/STRUCT/ARRAY/FB-instanser är inga bildtabellplatser:
en uppgift med en sådan signal ger Domsfel, inte en dom. Bankens samtliga 33
uppgifter med spårfacit bär bara bool/int/real (mätt 2026-09-05), så alla går
att mappa.

Facit: bankens spårfacit (människoskrivet före körningen, laglig källa 4 i
`docs/spec/85_bankkontraktet.md` §2) dömt genom OpenPLC Runtime v4.2.1
(laglig källa 1). Facit kommer aldrig ur koden som döms.

beskriver: bank/domare_openplc.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import time

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, ".."))
for _p in (_HAR, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import domare as _bankdomare  # noqa: E402
from vc_assist_svc.plc import deklarationsgrind as _dekl  # noqa: E402
from vc_assist_svc.plc import opcuakonfig as _opcuakonfig  # noqa: E402
from vc_assist_svc.plc import openplc as _plc  # noqa: E402
from vc_assist_svc.plc import paket as _paket  # noqa: E402
from vc_assist_svc.plc.matning import _anslut as _opcua_anslut  # noqa: E402
from vc_assist_svc.plc.matning import _asyncua as _opcua_bibliotek  # noqa: E402
from vc_assist_svc.plc.signalkarta import (  # noqa: E402
    FRAN_PLC,
    TILL_PLC,
    KartFel,
    karta_av_rader,
)
from vc_assist_svc.st import lasare as _lasare  # noqa: E402
from vc_assist_svc.st import skrivare as _skrivare  # noqa: E402
from vc_assist_svc.st import tolk as _tolk  # noqa: E402
from vc_assist_svc.st.modell import Enhet as _Enhet  # noqa: E402
from vc_assist_svc.st.modell import Pou as _Pou  # noqa: E402

Brist = _bankdomare.Brist
Dom = _bankdomare.Dom
Domsfel = _bankdomare.Domsfel
forgrindsbrist = _bankdomare.forgrindsbrist
_lika = _bankdomare._lika
_skriv = _bankdomare._skriv

# Samma klocka i tre led: vår tolk, PLC-uppgiften och facit. M-108 mätte
# OpenPLC:s cycle_time_avg mot tolk.SCAN_MS och paket.TASKINTERVALL.
SCAN_MS = _tolk.SCAN_MS

# Tolerans i scan. 2 (M-20, PLC:ns svarstid, ärvd ur domare.MARGINAL_SCAN)
# + 2 (M-108, kanalfas). Se huvudets härledning. Facit med annan scan_ms kan
# inte dömas på vårt rutnät och ger Domsfel.
TOLERANS_SCAN = _bankdomare.MARGINAL_SCAN + 2

# Samplingsavstånd över OPC UA. 10 ms ger ~2 prover per scan vid 20 ms period
# och matchar pluginets egen cykeltid (opcuakonfig.CYKELTID_MS).
POLL_S = 0.010

# Svans efter sekvensens sista tid, så att en sen flank inom toleransen fångas.
# 0,3 s = 15 scan > TOLERANS_SCAN (4). Marginal, ingen grind.
TAIL_S = 0.3

# Tak per sekvens utöver dess egen längd. Gräns mot hängning, inte en
# förväntan: går den över är det ett Domsfel, aldrig en dom.
SEQ_MARGINAL_S = 60.0

# Hur länge OPC UA-servern får dröja efter (om)start. M-108 steg 1 mätte 1,5 s
# glapp mellan RUNNING och en svarande server; matning.py väntar 30 s.
OPCUA_START_TIMEOUT = 30.0

# Hur länge insignalerna får ta på sig att synas i bildtabellen innan
# kanalkontrollen läser tillbaka dem. 0,15 s = 15 pluginscykler à 10 ms.
SETTLE_S = 0.15

# Tolerans vid återläsning av en skriven REAL. Insignalen går genom float32 i
# PLC:n; 1e-5 relativt är ~80x float32:s epsilon (1,2e-7) och skiljer alltså
# breddeffekt från en skrivning som inte fastnade.
REAL_ATERLAS_TOL = 1e-5

# Storleksklass per ST-typ för adresseringen; speglar
# signalkarta.STORLEK_TYPER och kor_A1_beteende.KLASS.
KLASS = {"BOOL": "X", "BYTE": "B", "SINT": "B", "USINT": "B", "WORD": "W",
         "INT": "W", "UINT": "W", "DWORD": "D", "DINT": "D", "UDINT": "D",
         "REAL": "D", "LWORD": "L", "LINT": "L", "ULINT": "L", "LREAL": "L"}

# OPC UA-variant per ST-typ (asyncua VariantType-namn); samma mönster som
# kor_A1_beteende.VARIANT, utökat till alla mappbara typer.
VARIANT = {"BOOL": "Boolean", "BYTE": "Byte", "SINT": "SByte",
           "USINT": "Byte", "WORD": "UInt16", "INT": "Int16",
           "UINT": "UInt16", "DWORD": "UInt32", "DINT": "Int32",
           "UDINT": "UInt32", "REAL": "Float", "LINT": "Int64",
           "ULINT": "UInt64", "LWORD": "UInt64", "LREAL": "Double"}


# --------------------------------------------------------------------- rigg

class Rigg(object):
    """Var motorn finns. Ingen adress är en konstant i domarens kropp.

    Skälet är mätt, inte principiellt: två OpenPLC-runtimes kör samtidigt på
    den här maskinen (14840/18443 och 14841/18444) och hör till olika
    mätningar. En hårdkodad port i domaren hade dömt genom någon annans PLC.
    """

    def __init__(self, bas=None, endpoint=None, anvandare=None, losenord=None,
                 strucpp_paket=None, runtime_include=None, node=None):
        self.bas = bas or os.environ.get(
            "VC_ASSIST_OPENPLC_BAS", "https://127.0.0.1:18443")
        self.endpoint = endpoint or os.environ.get(
            "VC_ASSIST_OPENPLC_ENDPOINT",
            "opc.tcp://172.17.0.2:4840/openplc/opcua")
        self.anvandare = anvandare or os.environ.get(
            "VC_ASSIST_OPENPLC_ANVANDARE", "vcassist")
        self.losenord = losenord or os.environ.get(
            "VC_ASSIST_OPENPLC_LOSENORD", "vcassist")
        self.strucpp_paket = strucpp_paket or _leta_strucpp_paket()
        self.runtime_include = runtime_include or _leta_runtime_include()
        self.node = node or os.environ.get("VC_ASSIST_NODE", "node")

    def __repr__(self):
        return "<Rigg %s / %s>" % (self.bas, self.endpoint)

    def kontrollera(self):
        """Fäller med Domsfel om något i kedjan saknas. Aldrig en dom."""
        if not self.strucpp_paket:
            raise Domsfel(
                "hittar inget STruC++-paket. Sätt VC_ASSIST_STRUCPP_PAKET "
                "till katalogen med dist/index.js, eller kör "
                "install/verktygskedjan.py. Utan kompilator finns ingen dom "
                "att fälla — bara en rigg som saknas.")
        for vad, sokvag in (
                ("STruC++-paketet", self.strucpp_paket),
                ("dist/index.js", os.path.join(self.strucpp_paket, "dist",
                                               "index.js"))):
            if not os.path.exists(sokvag):
                raise Domsfel("hittar inte %s på %s" % (vad, sokvag))
        if not self.runtime_include or not os.path.isdir(self.runtime_include):
            raise Domsfel(
                "hittar inga STruC++-runtimeheaders (%r). Sätt "
                "VC_ASSIST_STRUCPP_RUNTIME_INCLUDE; runtimen vendorar dem "
                "inte, de följer med varje uppladdning."
                % (self.runtime_include,))
        if not shutil.which(self.node):
            raise Domsfel("hittar inte %r på PATH; STruC++ körs genom node"
                          % (self.node,))

    def klient(self):
        return _plc.OpenPlcV4(self.bas, self.anvandare, self.losenord,
                              tillat_osignerat=True)


# Kandidatsökvägar för STruC++-paketet, i fallande styrka. Den första är
# install/verktygskedjan.py:s egen målkatalog (hashkontrollerad); de senare är
# de platser M-108 och M-125 faktiskt körde ifrån på den här maskinen.
_STRUCPP_KANDIDATER = (
    os.path.join(os.path.expanduser("~"), ".cache", "vc_assist",
                 "verktygskedjan", "uppackat", "npm", "package"),
    "/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/"
    "scratchpad/strucpp_npm/package",
)

_RUNTIME_KANDIDATER = (
    os.path.join(os.path.expanduser("~"), ".cache", "vc_assist",
                 "verktygskedjan", "uppackat", "linux-x64", "strucpp",
                 "runtime", "include"),
    "/tmp/opencode/m108/strucpp-bin/strucpp/runtime/include",
)


def _leta_strucpp_paket():
    ur_miljon = os.environ.get("VC_ASSIST_STRUCPP_PAKET")
    if ur_miljon:
        return ur_miljon
    for kandidat in _STRUCPP_KANDIDATER:
        if os.path.exists(os.path.join(kandidat, "dist", "index.js")):
            return kandidat
    return None


def _leta_runtime_include():
    ur_miljon = os.environ.get("VC_ASSIST_STRUCPP_RUNTIME_INCLUDE")
    if ur_miljon:
        return ur_miljon
    for kandidat in _RUNTIME_KANDIDATER:
        if os.path.isdir(kandidat):
            return kandidat
    return None


# ------------------------------------------------------------------ program

def _stationsnamn(task_id):
    """OPC UA-stationens namn ur task_id. Ren ASCII-identifierare, aldrig
    modellens: nodnamnen är kartans, inte lösningens."""
    stam = "".join(c if (c.isalnum() or c == "_") else ""
                   for c in (task_id or ""))
    return "Bank" + stam if stam else "Bank"


def _karta_for_post(post):
    """Signalkarta ur post["control"]["signals"].

    Kastar Domsfel när en signal inte går att mappa (TIME/STRING/STRUCT/
    ARRAY/FB) — en uppgift vi inte kan köra får inte bli en dom.
    """
    signaler = (post.get("control") or {}).get("signals") or []
    if not signaler:
        raise Domsfel("%s saknar control.signals att mappa"
                      % post.get("task_id"))
    raknare = {"I": {"X": 0, "B": 0, "W": 0, "D": 0, "L": 0},
               "Q": {"X": 0, "B": 0, "W": 0, "D": 0, "L": 0}}
    rader = []
    for s in signaler:
        namn = s.get("name")
        typnamn = (s.get("type") or "").upper()
        riktning = s.get("dir")
        if riktning == "in":
            plc_rikt, omrade = TILL_PLC, "I"
        elif riktning == "out":
            plc_rikt, omrade = FRAN_PLC, "Q"
        else:
            raise Domsfel("%s: signalen %r har okänd riktning %r"
                          % (post.get("task_id"), namn, riktning))
        klass = KLASS.get(typnamn)
        if klass is None or typnamn not in VARIANT:
            raise Domsfel(
                "%s: signalen %s (%s) går inte att mappa till bildtabellen; "
                "bara BOOL/BYTE/SINT/USINT/WORD/INT/UINT/DWORD/DINT/UDINT/"
                "REAL/LWORD/LINT/ULINT/LREAL mappas (TIME saknar "
                "storleksklass, STRING/STRUCT/ARRAY/FB är inga "
                "bildtabellplatser)" % (post.get("task_id"), namn, typnamn))
        if klass == "X":
            n = raknare[omrade]["X"]
            raknare[omrade]["X"] += 1
            adress = "%%%sX%d.%d" % (omrade, n // 8, n % 8)
        else:
            n = raknare[omrade][klass]
            raknare[omrade][klass] += 1
            adress = "%%%s%s%d" % (omrade, klass, n)
        rader.append(("BANK", namn, namn, typnamn, plc_rikt, adress))
    try:
        return karta_av_rader(_stationsnamn(post.get("task_id")), rader)
    except (KartFel, KeyError, ValueError) as fel:
        raise Domsfel("%s: signalerna går inte att mappa: %s"
                      % (post.get("task_id"), fel))


def program_for_st(st_text, karta):
    """Full kompilatortext: kartans VAR-block först, lösningens POU orörd.

    Lämnar `(text, programnamn)` eller en `Brist` — det senare när felet är
    lösningens (den går inte att läsa, den bär inte exakt ett PROGRAM, den
    deklarerar om en mappad signal).
    """
    try:
        enhet = _lasare.las(st_text)
    except Exception as fel:
        return Brist("openplc:kompilerar_inte",
                     "läsaren avvisade lösningen, den når aldrig OpenPLC: %s"
                     % fel)
    program = [p for p in enhet.pouer if p.sort == "PROGRAM"]
    if len(program) != 1:
        return Brist("openplc:kompilerar_inte",
                     "lösningen bär %d PROGRAM; exakt ett krävs för bygget"
                     % len(program))
    pou = program[0]
    signalnamn = set(s.tagg.upper() for s in karta.signaler)
    egna = set()
    for _block, dek in pou.deklarationer():
        egna.add(dek.namn.upper())
    krock = sorted(signalnamn & egna)
    if krock:
        return Brist("openplc:signal_omdeklarerad",
                     "lösningen deklarerar om mappade signaler: %s. "
                     "Signaldeklarationerna ägs av kartan (I10)."
                     % ", ".join(krock))
    ny_pou = _Pou(pou.sort, pou.namn, (karta.varblock(),) + tuple(pou.block),
                  tuple(pou.kropp), pou.returtyp)
    ovriga = tuple(p for p in enhet.pouer if p is not pou)
    try:
        text = _skrivare.skriv_enhet(_Enhet(enhet.typer, enhet.globala,
                                            (ny_pou,) + ovriga))
    except Exception as fel:
        return Brist("openplc:kompilerar_inte",
                     "lösningen gick inte att skriva tillbaka: %s" % fel)
    return text + _paket.konfigurationstext(ny_pou.namn), ny_pou.namn


# ------------------------------------------------------------- bygge & start

def _bygg(full_text, karta, rigg, byggkatalog):
    """STruC++ + arkiv. Lämnar zip-sökvägen, eller en Brist när KODEN föll.

    Kastar Domsfel när RIGGEN föll. Skillnaden bärs av `paket.Kompilatorfel`,
    som bara reses när kompilatorn kördes och svarade nej.
    """
    rigg.kontrollera()
    try:
        forbock = _paket.kompilera(
            full_text, os.path.join(byggkatalog, "for"), rigg.strucpp_paket,
            node=rigg.node)
        konfig = _opcuakonfig.konfiguration(karta, forbock, rigg.endpoint)
        zipvag, _ = _paket.bygg_projekt(
            full_text, os.path.join(byggkatalog, "arkiv"), rigg.strucpp_paket,
            rigg.runtime_include, opcua_konfig=konfig, node=rigg.node)
    except _paket.Kompilatorfel as fel:
        return Brist("openplc:kompilerar_inte",
                     "STruC++ avvisade lösningen:\n%s" % str(fel)[:4000])
    except _paket.Byggfel as fel:
        raise Domsfel("riggen kunde inte bygga lösningen (kompilatorn kördes "
                      "aldrig eller svarade inte): %s" % fel)
    return zipvag


def _ladda(klient, zipvag, tidsgrans=300.0, paus=2.0):
    """Ladda upp och vänta ut OpenPLC:s egen kompilering.

    Lämnar None (byggde) eller en Brist (OpenPLC sa nej om koden). Kastar
    Domsfel när runtimen inte går att nå eller står kvar i COMPILING.
    """
    try:
        klient.ladda_upp(zipvag)
    except _plc.OpenPlcFel as fel:
        raise Domsfel("uppladdningen till OpenPLC nådde inte fram: %s" % fel)
    slut = time.time() + tidsgrans
    try:
        senaste = klient.kompileringsstatus()
        while senaste.pagar and time.time() < slut:
            time.sleep(paus)
            senaste = klient.kompileringsstatus()
    except _plc.OpenPlcFel as fel:
        raise Domsfel("OpenPLC slutade svara under kompileringen: %s" % fel)
    if senaste.pagar:
        raise Domsfel("OpenPLC stod kvar i %s efter %.0f s; bygget hängde, "
                      "lösningen är inte dömd" % (senaste.status, tidsgrans))
    if not senaste.klar:
        return Brist(
            "openplc:kompilerar_inte",
            "OpenPLC vägrade kompilera lösningen (%s, exit %s). "
            "Kompilatorns egna ord:\n%s"
            % (senaste.status, senaste.exit_kod, _fel_ur_logg(senaste.logg)))
    return None


def _fel_ur_logg(logg, rader=12):
    """Byggloggens FELRADER, inte dess sista rader.

    Skälet är mätt 2026-09-05: OpenPLC:s logg slutar med länkkommandon och
    `make: *** Error 1`, medan g++:s `error:` ligger mitt i. En dom som
    citerar de sista 2000 tecknen säger "bygget föll" och inte varför.
    """
    alla = [r for r in (logg or "").splitlines() if r.strip()]
    fel = [r for r in alla if "error:" in r.lower() or "Error " in r]
    valda = fel[:rader] if fel else alla[-rader:]
    return "\n".join(v[:400] for v in valda)


def _stoppa(klient, tidsgrans=30.0, paus=0.25):
    """Stoppa PLC:n och vänta tills den faktiskt slutat köra.

    MÄTT 2026-09-05: `stop-plc` svarar innan omställningen är klar, och ett
    `start-plc` i det glappet svarar **BUSY** i stället för OK. Utan den här
    väntan föll domaren mellan sekvens 1 och 2 med ett Domsfel som såg ut som
    en trasig runtime men var vår egen kapplöpning.
    """
    try:
        klient.stoppa()
    except _plc.OpenPlcFel as fel:
        raise Domsfel("stop-plc nådde inte fram: %s" % fel)
    slut = time.time() + tidsgrans
    senaste = ""
    while time.time() < slut:
        try:
            senaste = klient.status()
        except _plc.OpenPlcFel as fel:
            raise Domsfel("runtimen slutade svara under stopp: %s" % fel)
        if senaste != _plc.KOR:
            return senaste
        time.sleep(paus)
    raise Domsfel("runtimen stod kvar i %s efter %.0f s stopp; sekvenserna "
                  "går inte att isolera och lösningen är inte dömd"
                  % (senaste, tidsgrans))


def _starta(klient, tidsgrans=30.0, paus=0.5):
    """Starta PLC:n. Lämnar None, eller en Brist när programmet inte laddades.

    EMPTY efter start betyder att .so:n inte gick att ladda — lösningens
    egenskap (M-20). Att runtimen inte når RUNNING alls är riggens fel och
    kastar Domsfel. BUSY är varken: det är en omställning som pågår, och den
    får försöka färdigt inom samma tidsgräns.
    """
    slut = time.time() + tidsgrans
    svar = ""
    while time.time() < slut:
        try:
            svar = klient.starta()
        except _plc.OpenPlcFel as fel:
            raise Domsfel("start-plc nådde inte fram: %s" % fel)
        if svar == "OK":
            break
        if svar != "BUSY":
            raise Domsfel("start-plc svarade %r; runtimen tog inte emot "
                          "begäran" % (svar,))
        time.sleep(paus)
    if svar != "OK":
        raise Domsfel("start-plc svarade BUSY i %.0f s; runtimen ställde "
                      "aldrig om och lösningen är inte dömd" % tidsgrans)
    senaste = ""
    while time.time() < slut:
        try:
            senaste = klient.status()
        except _plc.OpenPlcFel as fel:
            raise Domsfel("runtimen slutade svara under start: %s" % fel)
        if senaste == _plc.KOR:
            return None
        if senaste == _plc.TOM:
            return Brist(
                "openplc:startar_inte",
                "programmet byggde men runtimen gick till EMPTY: .so:n "
                "laddades aldrig. Runtimens egna loggrader:\n%s"
                % klient.logg(rader=12)[:2000])
        time.sleep(paus)
    raise Domsfel("runtimen nådde inte RUNNING inom %.0f s (sist: %s); "
                  "lösningen är inte dömd" % (tidsgrans, senaste))


# -------------------------------------------------------------------- körning

class _Kanalfel(Exception):
    """OPC UA-sidan svarade fel. Sidan kördes inte, alltså finns ingen dom."""


class _SkriverEgenIngang(Exception):
    """Lösningen tilldelar en mappad INGÅNG, och skrev över vår stimulus.

    Skild från `_Kanalfel`, och skillnaden är mätt 2026-09-05 (M-146 §4):
    P-07:s motbevis `ridans_signal_tvingas_hog_i_koden` tvingar ljusridåns
    givarsignal hög i koden. Ateradlasningen ser då ett annat värde än vi
    skrev — precis som en kanal som tappar värden. Men orsaken är lösningens,
    inte riggens: stimulus nådde aldrig logiken, så spåret prövar inte det
    facit ber om. Utan den här klassen blev motbeviset ett Domsfel, alltså
    ingen dom alls, fast lösningen är den som är fel.
    """

    def __init__(self, signal, skrivet, last):
        Exception.__init__(
            self, "%s tilldelas i lösningen och skrevs över: vi satte %r, "
                  "PLC:n läste tillbaka %r. En ingång ägs av bildtabellen, "
                  "inte av programmet (I15/grind 2, dubbelskrivning)."
                  % (signal, skrivet, last))
        self.signal = signal


def tilldelade_namn(st_text):
    """Namnen lösningens PROGRAM tilldelar, i versaler. Tom mängd om texten
    inte går att läsa — den vägen har redan gett en Brist före det här."""
    try:
        enhet = _lasare.las(st_text)
    except Exception:
        return set()
    for p in enhet.pouer:
        if p.sort == "PROGRAM":
            return _dekl.bruk(p)[1]
    return set()


def _nollvarde(typnamn):
    if typnamn == "BOOL":
        return False
    if typnamn in ("REAL", "LREAL"):
        return 0.0
    return 0


def _till_plc_varde(typnamn, varde):
    if typnamn == "BOOL":
        return bool(varde)
    if typnamn in ("REAL", "LREAL"):
        return float(varde)
    return int(varde)


def _samma_varde(typnamn, skrivet, last):
    if typnamn == "BOOL":
        return bool(skrivet) == bool(last)
    if typnamn in ("REAL", "LREAL"):
        a, b = float(skrivet), float(last)
        return abs(a - b) <= REAL_ATERLAS_TOL * max(1.0, abs(a), abs(b))
    return int(skrivet) == int(last)


def _tagg_for(karta, namn):
    tagg = karta.med_tagg(namn)
    if tagg is not None:
        return tagg
    raise Domsfel("facit nämner signalen %r, som inte finns i uppgiftens "
                  "control.signals" % (namn,))


async def _kor_sekvens(opc, ua, station, karta, sekv, flanker,
                       egna_skrivningar=()):
    """Kör en facitsekvens i realtid mot en startad PLC.

    Allt — anslutning, nollställning, kanalkontroll, körning — ligger i EN
    händelseslinga. asyncua binder sina primitiver till slingan de skapades i;
    att ansluta i en `asyncio.run` och läsa i en annan ger ett fel som ser ut
    som en trasig PLC.
    """
    steg = sorted(sekv["steg"], key=lambda x: float(x["t_ms"]))
    slut_ms = max([float(s["t_ms"]) for s in steg] +
                  [float(f.get("till_ms", 0.0)) for f in flanker
                   if f.get("sekvens") == sekv["id"]] or [0.0])
    noder = dict((s.tagg,
                  opc.get_node("ns=2;s=%s" % _opcuakonfig.nodid(station, s.tagg)))
                 for s in karta.signaler)
    # Fast ordning: en batchläsning svarar i samma ordning som den frågade.
    lasordning = [s.tagg for s in karta.signaler]
    lasnoder = [noder[t] for t in lasordning]

    async def skriv(tagg, varde):
        vt = getattr(ua.VariantType, VARIANT[tagg.typ.namn])
        try:
            await noder[tagg.tagg].write_value(
                ua.DataValue(ua.Variant(
                    _till_plc_varde(tagg.typ.namn, varde), vt)))
        except Exception as fel:
            raise _Kanalfel("skrivningen av %s föll: %s" % (tagg.tagg, fel))

    async def las_alla():
        """Alla signaler i ETT anrop, och tiden mitt i anropet.

        En läsning per nod hade blivit n tur-och-retur per prov. Med 22 mappade
        signaler (bankens största uppgift) och M-108:s uppmätta RTT hade
        provtagningen blivit långsammare än scanperioden den ska mäta — och
        provet hade då mätt sin egen provtagare. `read_values` är en enda
        Read-tjänst över alla noder.

        Tidsstämpeln tas mitt i anropet. Före anropet underskattar tiden med
        anropets längd, efter överskattar den; mitten är symmetrisk och har
        halva felet.
        """
        fore = time.perf_counter()
        try:
            varden = await opc.read_values(lasnoder)
        except Exception as fel:
            raise _Kanalfel("batchläsningen av %d signaler föll: %s"
                            % (len(lasnoder), fel))
        efter = time.perf_counter()
        return (fore + efter) / 2.0, dict(zip(lasordning, varden))

    # Nollställning: domare.py bygger en ny Tolk per sekvens, alltså startar
    # varje sekvens från nollvärden. Utan det här hade den ena domaren dömt
    # sekvenser var för sig och den andra sekvenser i följd.
    #
    # Sekvensens t=0-stimuli skrivs INTE här utan i första varvet av
    # körslingan. FUNNET 2026-09-05 (M-146): skrevs de före en insättningspaus
    # hann PLC:n svara på dem innan klockan startade, och den första flanken
    # låg då utanför spåret. P-05:s referens föll på `flank:antal_starter`
    # med 1 av 2 RISE — en artefakt i domaren, inte en oenighet mellan
    # motorerna.
    for s in karta.signaler:
        if s.riktning == TILL_PLC:
            await skriv(s, _nollvarde(s.typ.namn))
    await asyncio.sleep(SETTLE_S)

    # Kanalkontroll före: läsvägen svarar och bildtabellen står på noll.
    _, tillbaka = await las_alla()
    for s in karta.signaler:
        if s.riktning != TILL_PLC:
            continue
        noll = _nollvarde(s.typ.namn)
        if _samma_varde(s.typ.namn, noll, tillbaka.get(s.tagg)):
            continue
        if s.tagg.upper() in egna_skrivningar:
            raise _SkriverEgenIngang(s.tagg, noll, tillbaka.get(s.tagg))
        raise _Kanalfel(
            "kanalfel före sekvensen: %s nollställdes men lästes %r; "
            "insignalen fastnade inte i bildtabellen"
            % (s.tagg, tillbaka.get(s.tagg)))

    t0 = time.perf_counter()
    spar = []
    skrivet = {}
    i = 0
    t_slut = slut_ms / 1000.0 + TAIL_S
    while True:
        nu = time.perf_counter() - t0
        while i < len(steg) and float(steg[i]["t_ms"]) / 1000.0 <= nu:
            for namn, varde in (steg[i].get("satt") or {}).items():
                tagg = _tagg_for(karta, namn)
                if tagg.riktning == FRAN_PLC:
                    raise Domsfel(
                        "facit skriver utgången %s; utgångar är skrivskyddade "
                        "på nodnivå (I15)" % tagg.tagg)
                skrivet[tagg.tagg] = varde
                await skriv(tagg, varde)
            i += 1
        t_prov, varden = await las_alla()
        spar.append(((t_prov - t0) * 1000.0, varden))
        if nu >= t_slut:
            break
        await asyncio.sleep(POLL_S)

    # Kanalkontroll efter: varje insignal vi skrev ska läsas tillbaka som den
    # skrevs. En skrivväg som tyst tappar värden hade annars sett ut som en
    # lösning som inte reagerar — alltså ett körningsfel maskerat som en dom.
    _, sist = await las_alla()
    for namn, varde in skrivet.items():
        tagg = karta.med_tagg(namn)
        if _samma_varde(tagg.typ.namn, varde, sist.get(namn)):
            continue
        if namn.upper() in egna_skrivningar:
            raise _SkriverEgenIngang(namn, varde, sist.get(namn))
        raise _Kanalfel(
            "kanalfel efter sekvensen: %s skrevs sist %r men lästes %r; "
            "skrivvägen tappade värden" % (namn, varde, sist.get(namn)))
    return spar


async def _anslut_och_kor(rigg, station, karta, sekv, flanker,
                          egna_skrivningar=()):
    Client, ua = _opcua_bibliotek()
    opc = Client(url=rigg.endpoint, timeout=5.0)
    try:
        await _opcua_anslut(opc, tidsgrans=OPCUA_START_TIMEOUT)
    except Exception as fel:
        raise Domsfel("nådde inte OPC UA-servern på %s: %s"
                      % (rigg.endpoint, fel))
    try:
        return await _kor_sekvens(opc, ua, station, karta, sekv, flanker,
                                  egna_skrivningar)
    finally:
        try:
            await opc.disconnect()
        except Exception:
            pass


def _kor_en_sekvens(rigg, station, karta, sekv, flanker,
                    egna_skrivningar=()):
    """Synkron omslutning. Alla fel utom Domsfel blir Domsfel: en sekvens som
    inte kördes får aldrig bli en dom."""
    tak = (max([float(s["t_ms"]) for s in sekv["steg"]] +
               [float(f.get("till_ms", 0.0)) for f in flanker
                if f.get("sekvens") == sekv["id"]] or [0.0]) / 1000.0
           + TAIL_S + SEQ_MARGINAL_S)

    async def med_tak():
        return await asyncio.wait_for(
            _anslut_och_kor(rigg, station, karta, sekv, flanker,
                            egna_skrivningar), timeout=tak)

    try:
        return asyncio.run(med_tak())
    except (Domsfel, _SkriverEgenIngang):
        raise
    except asyncio.TimeoutError:
        raise Domsfel("sekvensen %s svarade inte inom %.0f s; sidan kördes "
                      "inte och lösningen är inte dömd" % (sekv["id"], tak))
    except _Kanalfel as fel:
        raise Domsfel("sekvensen %s: %s; sidan kördes inte" % (sekv["id"], fel))
    except Exception as fel:
        raise Domsfel("sekvensen %s kraschade: %s (%s)"
                      % (sekv["id"], fel, type(fel).__name__))


def _sampla(spar, n_scan):
    """Nollte ordningens hållning till 20 ms rutnät, ankrat i sekvensstarten.

    Scan k bär det sista värde som lästes före (k+1)*SCAN_MS, alltså samma
    kant som domare.py läser efter: den scan vars klocka står på k*SCAN_MS.
    """
    ut = []
    idx = 0
    hall = {}
    for k in range(n_scan):
        grans = (k + 1) * SCAN_MS
        while idx < len(spar) and spar[idx][0] < grans - 1e-9:
            hall = spar[idx][1]
            idx += 1
        ut.append(dict(hall))
    return ut


def _dom_sekvens(karta, sekv, invarianter, flanker, spar):
    """Samma semantik som domare.dom, med TOLERANS_SCAN där kanalen kräver det.

    Lämnar `(brister, n_scan, matpunkter)`. `matpunkter` är domarens egen
    mätning av toleransen: för varje punktkrav hur många scan efter `t_ms`
    det väntade värdet först syntes (None = syntes aldrig inom fönstret).
    Utan den är 4 en siffra utan härkomst.
    """
    brister = []
    matpunkter = []
    sid = sekv["id"]
    steg = sorted(sekv["steg"], key=lambda x: float(x["t_ms"]))
    slut_ms = max([float(s["t_ms"]) for s in steg] +
                  [float(f.get("till_ms", 0.0)) for f in flanker
                   if f.get("sekvens") == sid] or [0.0])
    n_scan = int((slut_ms / 1000.0 + TAIL_S) * 1000.0 / SCAN_MS) + 1
    grid = _sampla(spar, n_scan)

    def las(namn, scan):
        tagg = karta.med_tagg(namn)
        if tagg is None or scan >= len(grid) or tagg.tagg not in grid[scan]:
            return None
        return grid[scan][tagg.tagg]

    for s in steg:
        k0 = int(round(float(s["t_ms"]) / SCAN_MS))
        for namn, vantat in (s.get("krav") or {}).items():
            traff = None
            for k in range(k0, min(k0 + TOLERANS_SCAN + 1, n_scan)):
                faktiskt = las(namn, k)
                if faktiskt is not None and _lika(vantat, faktiskt):
                    traff = k - k0
                    break
            matpunkter.append({"sekvens": sid, "t_ms": float(s["t_ms"]),
                               "signal": namn, "offset_scan": traff})
            if traff is None:
                sist = las(namn, min(k0 + TOLERANS_SCAN, n_scan - 1))
                brister.append(Brist(
                    "%s@%.0fms:%s" % (sid, float(s["t_ms"]), namn),
                    "%s skulle vara %s men var %s inom %d scan efter %.0f ms. %s"
                    % (namn, _skriv(vantat), _skriv(sist), TOLERANS_SCAN,
                       float(s["t_ms"]), s.get("varfor") or "")))

    mina_inv = [i for i in invarianter
                if i.get("sekvens") in (None, "*", sid)]
    for inv in mina_inv:
        foljd = 0
        for k in range(n_scan):
            villkor = all(
                (las(n, k) is not None and _lika(v, las(n, k)))
                for n, v in inv["nar"].items())
            krav = all(
                (las(n, k) is not None and _lika(v, las(n, k)))
                for n, v in inv["kraver"].items())
            if villkor and not krav:
                foljd += 1
                if foljd > TOLERANS_SCAN:
                    brister.append(Brist(
                        "invariant:%s@%s" % (inv["namn"], sid),
                        "vid t=%.0f ms gällde %s men inte %s i %d scan i rad "
                        "(bortom %d scan kanal+svarstid). %s"
                        % ((k - foljd + 1) * SCAN_MS,
                           ", ".join("%s=%s" % (n, _skriv(v))
                                     for n, v in inv["nar"].items()),
                           ", ".join("%s=%s" % (n, _skriv(v))
                                     for n, v in inv["kraver"].items()),
                           foljd, TOLERANS_SCAN,
                           inv.get("varfor") or "")))
                    break
            else:
                foljd = 0

    # Föregående scans värden skrivs FÖRST när alla flankkrav lästs. Skrevs de
    # inne i loopen fick det andra flankkravet på samma signal i samma sekvens
    # redan det uppdaterade värdet som sitt "föregående" och kunde aldrig
    # fällas. FUNNET 2026-09-05 i M-106; samma rättelse som i domare.py.
    mina_flank = [f for f in flanker if f.get("sekvens") == sid]
    flankraknare = dict((f["namn"], 0) for f in mina_flank)
    forra = {}
    for k in range(n_scan):
        t_ledd = k * SCAN_MS
        nu_varden = {}
        for f in mina_flank:
            signal = f["signal"]
            if signal not in nu_varden:
                v = las(signal, k)
                nu_varden[signal] = bool(v) if v is not None else False
            v = nu_varden[signal]
            p = forra.get(signal)
            if p is not None and float(f["fran_ms"]) <= t_ledd <= float(
                    f["till_ms"]) + TOLERANS_SCAN * SCAN_MS:
                if f["typ"] == "RISE" and v and not p:
                    flankraknare[f["namn"]] += 1
                elif f["typ"] == "FALL" and p and not v:
                    flankraknare[f["namn"]] += 1
        forra.update(nu_varden)
    for f in mina_flank:
        if flankraknare[f["namn"]] != int(f["antal"]):
            brister.append(Brist(
                "flank:%s" % f["namn"],
                "%s skulle ha %d %s-flank(er) mellan %.0f och %.0f ms "
                "(+ %d scan kanalfas), hade %d. %s"
                % (f["signal"], int(f["antal"]), f["typ"],
                   float(f["fran_ms"]), float(f["till_ms"]),
                   TOLERANS_SCAN, flankraknare[f["namn"]],
                   f.get("varfor") or "")))
    return brister, n_scan, matpunkter


# ---------------------------------------------------------------------- domen

def dom(post, st_text, spar=None, stationsdom=None, rigg=None, klient=None,
        byggkatalog=None):
    """Dömer `st_text` mot uppgiftens spårfacit genom körning i OpenPLC.

    Samma yta som `domare.dom`, plus riggen. Lämnar en Dom; `Dom.matpunkter`
    bär domarens egen mätning av toleransen (se `_dom_sekvens`).

    Kastar Domsfel så fort domen inte går att fälla på lösningens egenskaper:
    uppgiften saknar facit, riggen saknas, runtimen svarar inte, en sekvens
    kördes inte. En halv körning får aldrig bli en dom, och ett körningsfel
    får aldrig maskeras som ett underkännande.
    """
    brist = forgrindsbrist(stationsdom)
    if brist is not None:
        return _dom_med(post, [brist], 0, [])
    facit = spar if spar is not None else post.get("facit_spar")
    if not isinstance(facit, dict):
        raise Domsfel("%s har inget facit_spar att döma mot"
                      % post.get("task_id"))
    scan_ms = float(facit.get("scan_ms") or SCAN_MS)
    if abs(scan_ms - SCAN_MS) > 1e-9:
        raise Domsfel("%s kräver %.1f ms scan; domaren kör %.1f ms (PLC-"
                      "uppgiftens TASKINTERVALL, M-108). Facit på ett annat "
                      "rutnät går inte att döma här."
                      % (post.get("task_id"), scan_ms, SCAN_MS))
    sekvenser = facit.get("sekvenser") or []
    if not sekvenser:
        raise Domsfel("%s facit_spar saknar sekvenser; en tom körning får "
                      "aldrig bli GODKÄND" % post.get("task_id"))
    rigg = rigg or Rigg()
    rigg.kontrollera()
    karta = _karta_for_post(post)
    bygge = program_for_st(st_text, karta)
    if isinstance(bygge, Brist):
        return _dom_med(post, [bygge], 0, [])
    full_text, _prognamn = bygge
    # Vilka namn lösningen SJÄLV tilldelar. Behövs för att skilja en kanal som
    # tappar värden (riggens fel, Domsfel) från en lösning som skriver över
    # sin egen ingång (lösningens fel, en Brist). Se `_SkriverEgenIngang`.
    egna = tilldelade_namn(st_text)

    egen_katalog = byggkatalog is None
    if egen_katalog:
        byggkatalog = tempfile.mkdtemp(prefix="domare_openplc_")
    try:
        return _dom_med_katalog(post, facit, sekvenser, karta, full_text,
                                rigg, klient, byggkatalog, egna)
    finally:
        if egen_katalog:
            shutil.rmtree(byggkatalog, ignore_errors=True)


def _dom_med(post, brister, scan, matpunkter):
    d = Dom(post.get("task_id"), brister, scan)
    d.matpunkter = matpunkter
    return d


def _dom_med_katalog(post, facit, sekvenser, karta, full_text, rigg, klient,
                     byggkatalog, egna_skrivningar=()):
    zipvag = _bygg(full_text, karta, rigg, byggkatalog)
    if isinstance(zipvag, Brist):
        return _dom_med(post, [zipvag], 0, [])
    if klient is None:
        klient = rigg.klient()
    try:
        if not klient.svarar():
            raise Domsfel("OpenPLC på %s svarar inte på /api/ping; ingen "
                          "lösning är dömd" % rigg.bas)
    except _plc.OpenPlcFel as fel:
        raise Domsfel("nådde inte OpenPLC på %s: %s" % (rigg.bas, fel))
    try:
        klient.skapa_forsta_anvandare()
    except _plc.OpenPlcFel as fel:
        raise Domsfel("kunde inte logga in på OpenPLC: %s" % fel)

    brist = _ladda(klient, zipvag)
    if brist is not None:
        return _dom_med(post, [brist], 0, [])

    invarianter = facit.get("invarianter") or []
    flanker = facit.get("flanker") or []
    brister = []
    matpunkter = []
    scan_totalt = 0
    for n, sekv in enumerate(sekvenser):
        if n > 0:
            _stoppa(klient)
        startbrist = _starta(klient)
        if startbrist is not None:
            return _dom_med(post, [startbrist], 0, [])
        try:
            spar = _kor_en_sekvens(rigg, karta.station, karta, sekv, flanker,
                                   egna_skrivningar)
        except _SkriverEgenIngang as fel:
            return _dom_med(post, [Brist("openplc:skriver_egen_ingang",
                                         str(fel))], scan_totalt, matpunkter)
        seq_brister, n_scan, seq_matt = _dom_sekvens(
            karta, sekv, invarianter, flanker, spar)
        brister.extend(seq_brister)
        matpunkter.extend(seq_matt)
        scan_totalt += n_scan
    try:
        klient.stoppa()
    except (_plc.OpenPlcFel, Domsfel):
        # Att städa efter sig får inte kunna ändra en dom som redan är fälld.
        pass
    return _dom_med(post, brister, scan_totalt, matpunkter)


def dom_referens(post, **kwargs):
    """Dömer uppgiftens egen referenslösning. Ska bli godkänd."""
    facit = post.get("facit_spar") or {}
    return dom(post, facit.get("referens") or "", **kwargs)


def dom_motbevis(post, **kwargs):
    """Dömer varje motbevis. Lämnar (namn, Dom, faller_pa)."""
    facit = post.get("facit_spar") or {}
    ut = []
    for mb in facit.get("motbevis") or []:
        ut.append((mb["namn"], dom(post, mb["st"], **kwargs),
                   list(mb.get("faller_pa") or [])))
    return ut
