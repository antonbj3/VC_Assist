# -*- coding: utf-8 -*-
"""M-125 (ko A, punkt A1): OpenPLC som tredje motor - BETEENDE (utfall 3).

M-99:s konstruktioner ar korsprövade tolk<->STruC++ pa KOMPILERING.
A1 kraver KORNING: konstruktioner som bada accepterar men som ger olika
VARDEN vid korning i OpenPLC.

Metod (tur-retur, se M-20):
  1. Trasig fixtur forst: `o := REAL_TO_INT(1.5)` - tolken sager 1
     (trunkering), OpenPLC sager 2 (avrundning). Redovisad ROD innan
     systematiseringen byggdes (se /tmp/a1_fixtur/fix_red_ut.txt).
  2. Varje konstruktion: (a) lokal STruC++-kompilering som fristaende
     program (enkelt att avgora VAD som accepteras), (b) tolk-korning,
     (c) korning i OpenPLC Runtime v4 med mappad I/O over OPC UA,
     samma stimuli i bada motorerna, varden jamforda.
  3. Matekonomi: konstruktionerna grupperas i fyra program (A1K, A1A,
     A1T, A1B) med ett uppladdningsvarv var. Varje konstruktion har
     EGNA mappade utgangar och kompileras dessutom ENSKILT lokalt -
     grupperingen delar aldrig tillstand mellan konstruktioner (varje
     utgang tilldelas en gang ur konstanter/indata, ingen aterkoppling).

Fail-closed:
  * En konstruktion som faller i lokal kompilering eller i tolken blir
    EJ_KORD, aldrig OVERENS.
  * Ett program vars kanariekontroll (q_ok foljer p_in) faller blir
    EJ_KORT - korningen matte bara start, inte exekvering.
  * Ett kanalfel (insignal som inte fastnar) klassas aldrig som oenighet.
  * OpenPLC som inte svarar ger exit != 0 med skal, aldrig tyst gront.

Kors:
    nice -n 19 ionice -c3 python3 tests/protocol/kor_A1_beteende.py \\
        --byggkatalog /tmp/a1_bygg --json /tmp/a1.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.plc import opcuakonfig, paket as P  # noqa: E402
from vc_assist_svc.plc.matning import _anslut, _asyncua  # noqa: E402
from vc_assist_svc.plc.openplc import OpenPlcV4, OpenPlcFel  # noqa: E402
from vc_assist_svc.plc.signalkarta import karta_av_rader  # noqa: E402
from vc_assist_svc.st import tolk as T  # noqa: E402
from vc_assist_svc.st import validera  # noqa: E402

BANKPOST = {
    "pastar": (
        "Samma ST-konstruktion ger samma VARDE i var tolk som vid korning "
        "i OpenPLC Runtime v4, eller sa pekas konstruktion, tokvarde och "
        "OpenPLC-varde ut var for sig."),
    "under_prov": ("svc/vc_assist_svc/st/tolk.py",),
    "facit": "OpenPLC Runtime v4:s korning (beteende), avlast over OPC UA",
    "facitkalla": "OpenPLC Runtime v4.2.1 (oberoende tredje motor)",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "REAL_TO_INT(1.5): tolken sager 1, OpenPLC sager 2 - "
        "fixturen sag ROTT innan systematiseringen byggdes",
        "ett program vars kanarieutgang inte foljer insignalen falls, "
        "inte godkans",
        "kanalens eget fel far inte klassas som motoroenighet",
        "EJ_KORD far aldrig rapporteras som OVERENS",
    ),
    "kraver": ("openplc",),
    "matningar": ("M-125",),
}

# REAL-jamforelsens tolerans. INGEN grind: ravarderna redovisas alltid
# exakt i tabellen. Skalet for 1e-6: float32:s maskinepsilon ar ~1,2e-7,
# sa samma rakning i 32 mot 64 bitar skiljer hogst nagra epsilon;
# 1e-6 ger ~8x marginal mot breddeffekten. Allt bortom ar en annan
# berakning, inte en annan bredd. Referens: IEEE 754 + tabellens ravarde.
REAL_TOL = 1e-6

# OPC UA-variant per ST-typ (asyncua VariantType-namn).
VARIANT = {"BOOL": "Boolean", "INT": "Int16", "DINT": "Int32",
           "REAL": "Float", "WORD": "UInt16", "DWORD": "UInt32",
           "BYTE": "Byte"}

# Storleksklass per typ (for adressering; speglar signalkarta.STORLEK_TYPER).
KLASS = {"BOOL": "X", "BYTE": "B", "INT": "W", "WORD": "W", "DINT": "D",
         "REAL": "D", "DWORD": "D"}

# Fall: namn, kategori, uttyp, interna deklarationer, tilldelning,
# forvantat beteende (formulerat FORE korning - kalla avgor).
# hypotes: LIKA / NARA / DIVERGERAR / OVISS.
FALL = [
    # ---- konvertering: avrundning (fixturens familj) ----
    dict(namn="c01", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(1.5);",
         forvantat="tolk trunkerar till 1; STruC++:s iec_convert_value avrundar (std::round, half away) till 2",
         hypotes="DIVERGERAR"),
    dict(namn="c02", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(2.5);",
         forvantat="tolk 2; PLC round(2.5)=3 (half away from zero)",
         hypotes="DIVERGERAR"),
    dict(namn="c03", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(0.5);",
         forvantat="tolk 0; PLC round(0.5)=1",
         hypotes="DIVERGERAR"),
    dict(namn="c04", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(-1.5);",
         forvantat="tolk -1 (mot noll); PLC round(-1.5)=-2 (half away)",
         hypotes="DIVERGERAR"),
    dict(namn="c05", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(-0.5);",
         forvantat="tolk 0; PLC round(-0.5)=-1",
         hypotes="DIVERGERAR"),
    dict(namn="c06", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(2.49);",
         forvantat="bada 2; ingen halvgrans, kontrollfall",
         hypotes="LIKA"),
    dict(namn="c07", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(-2.49);",
         forvantat="bada -2; kontrollfall",
         hypotes="LIKA"),
    dict(namn="c08", kat="konv", typ="DINT", extra="", st="o := REAL_TO_DINT(1.5);",
         forvantat="tolk 1; PLC 2 (samma avrundning, vidare typ)",
         hypotes="DIVERGERAR"),
    dict(namn="c09", kat="konv", typ="DINT", extra="", st="o := REAL_TO_DINT(123456.789);",
         forvantat="tolk trunkerar 123456; PLC round ger 123457",
         hypotes="DIVERGERAR"),
    dict(namn="c10", kat="konv", typ="INT", extra="", st="o := LREAL_TO_INT(2.5);",
         forvantat="tolk 2; PLC 3 om LREAL-vagen avrundar likadant",
         hypotes="DIVERGERAR"),
    dict(namn="c11", kat="konv", typ="DINT", extra="", st="o := TRUNC(1.9);",
         forvantat="bada 1; TRUNC trunkerar uttryckligen, kontrollfall",
         hypotes="LIKA"),
    dict(namn="c12", kat="konv", typ="DINT", extra="", st="o := TRUNC(-1.9);",
         forvantat="bada -1; kontrollfall",
         hypotes="LIKA"),
    dict(namn="c13", kat="konv", typ="DINT", extra="", st="o := REAL_TO_DINT(16777217.0);",
         forvantat="tolk 16777217 (float64 exakt); PLC: literalen ar float32 (2^24+1 ej representerbart -> 16777216)",
         hypotes="DIVERGERAR"),
    dict(namn="c14", kat="konv", typ="DINT", extra="", st="o := REAL_TO_DINT(0.5);",
         forvantat="tolk 0; PLC 1",
         hypotes="DIVERGERAR"),
    dict(namn="c23", kat="konv", typ="DINT", extra="", st="o := REAL_TO_DINT(-2.5);",
         forvantat="tolk -2; PLC -3",
         hypotes="DIVERGERAR"),
    dict(namn="c24", kat="konv", typ="INT", extra="", st="o := REAL_TO_INT(16777216.0);",
         forvantat="bada 16777216; exakt representerbart aven i float32, kontrollfall",
         hypotes="LIKA"),
    dict(namn="c25", kat="konv", typ="DINT", extra="x_c25 : REAL;", st="x_c25 := 16777217.0; o := REAL_TO_DINT(x_c25);",
         forvantat="tolk: x=16777217.0 exakt (float64), o=16777217; PLC: x blir 16777216.0f i REAL-variabeln, o=16777216 - literal- mot variabelvag",
         hypotes="DIVERGERAR"),
    dict(namn="c15", kat="konv", typ="REAL", extra="", st="o := INT_TO_REAL(7);",
         forvantat="bada 7.0 exakt; kontrollfall",
         hypotes="LIKA"),
    dict(namn="c16", kat="konv", typ="INT", extra="", st="o := DINT_TO_INT(70000);",
         forvantat="tolk 70000 (obegransat int, ingen viddkontroll); PLC int16 -> 70000 mod 65536 = 4464",
         hypotes="DIVERGERAR"),
    dict(namn="c17", kat="konv", typ="INT", extra="", st="o := DINT_TO_INT(-5);",
         forvantat="bada -5; kontrollfall",
         hypotes="LIKA"),
    dict(namn="c18", kat="konv", typ="BOOL", extra="", st="o := REAL_TO_BOOL(0.5);",
         forvantat="bada TRUE; nollskilt ar sant i bada",
         hypotes="LIKA"),
    dict(namn="c19", kat="konv", typ="BOOL", extra="", st="o := REAL_TO_BOOL(0.0);",
         forvantat="bada FALSE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="c20", kat="konv", typ="INT", extra="", st="o := BOOL_TO_INT(TRUE);",
         forvantat="bada 1; kontrollfall",
         hypotes="LIKA"),
    dict(namn="c21", kat="konv", typ="BOOL", extra="", st="o := INT_TO_BOOL(5);",
         forvantat="bada TRUE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="c22", kat="konv", typ="BOOL", extra="", st="o := INT_TO_BOOL(0);",
         forvantat="bada FALSE; kontrollfall",
         hypotes="LIKA"),
    # ---- aritmetik ----
    dict(namn="a01", kat="arit", typ="REAL", extra="", st="o := 1.0/3.0*3.0;",
         forvantat="bada 1.0: avrundningen faller tillbaka i bada bredderna; kandidat som INTE divergerar",
         hypotes="LIKA"),
    dict(namn="a02", kat="arit", typ="BOOL", extra="", st="o := (0.1 + 0.2) = 0.3;",
         forvantat="tolk FALSE (float64: 0.30000000000000004); PLC float32: 0.1f+0.2f avrundas till 0.3f -> TRUE",
         hypotes="DIVERGERAR"),
    dict(namn="a03", kat="arit", typ="REAL", extra="", st="o := 0.1 + 0.2;",
         forvantat="tolk 0.30000000000000004; PLC ~0.3000000119; NARA (breddeffekt, ej annan berakning)",
         hypotes="NARA"),
    dict(namn="a04", kat="arit", typ="INT", extra="", st="o := -7 MOD 3;",
         forvantat="bada -1; tolken implementerar IEC-tecken (taljarens), C likadant",
         hypotes="LIKA"),
    dict(namn="a05", kat="arit", typ="INT", extra="", st="o := 7 MOD -3;",
         forvantat="bada 1; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a06", kat="arit", typ="INT", extra="", st="o := -7 MOD -3;",
         forvantat="bada -1; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a07", kat="arit", typ="INT", extra="", st="o := -7 / 3;",
         forvantat="bada -2; heltalstrunkering mot noll i bada",
         hypotes="LIKA"),
    dict(namn="a08", kat="arit", typ="INT", extra="", st="o := 7 / -3;",
         forvantat="bada -2; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a09", kat="arit", typ="DINT", extra="", st="o := 2147483647 + 1;",
         forvantat="tolk 2147483648 (obegransat); PLC int32 sveper till -2147483648",
         hypotes="DIVERGERAR"),
    dict(namn="a10", kat="arit", typ="INT", extra="", st="o := 32767 + 1;",
         forvantat="tolk 32768; PLC int16 sveper till -32768",
         hypotes="DIVERGERAR"),
    dict(namn="a11", kat="arit", typ="DINT", extra="", st="o := 100000 * 100000;",
         forvantat="tolk 10000000000; PLC 10^10 mod 2^32 = 1410065408",
         hypotes="DIVERGERAR"),
    dict(namn="a12", kat="arit", typ="BYTE", extra="", st="o := 255 + 1;",
         forvantat="tolk 256; PLC uint8 sveper till 0",
         hypotes="DIVERGERAR"),
    dict(namn="a13", kat="arit", typ="INT", extra="", st="o := 2 ** 10;",
         forvantat="bada 1024; kontrollfall for potensoperatorn",
         hypotes="LIKA"),
    dict(namn="a14", kat="arit", typ="REAL", extra="", st="o := SQRT(2.0);",
         forvantat="NARA: samma funktion, olika bredd",
         hypotes="NARA"),
    dict(namn="a15", kat="arit", typ="INT", extra="", st="o := 10 / 3;",
         forvantat="bada 3; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a16", kat="arit", typ="REAL", extra="", st="o := 10.0 / 3.0;",
         forvantat="tolk 3.3333333333333335; PLC ~3.3333332539; NARA",
         hypotes="NARA"),
    dict(namn="a17", kat="arit", typ="INT", extra="", st="o := ABS(-7);",
         forvantat="bada 7; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a18", kat="arit", typ="INT", extra="", st="o := LIMIT(0, 42, 10);",
         forvantat="bada 10; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a19", kat="arit", typ="INT", extra="", st="o := SEL(TRUE, 11, 22);",
         forvantat="bada 22; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a20", kat="arit", typ="REAL", extra="", st="o := 3.14159265;",
         forvantat="literalen trunkeras till float32 i PLC; NARA",
         hypotes="NARA"),
    dict(namn="a21", kat="arit", typ="REAL", extra="", st="o := 1.0 / 3.0;",
         forvantat="tolk 0.3333333333333333; PLC ~0.3333333433; NARA",
         hypotes="NARA"),
    dict(namn="a22", kat="arit", typ="DINT", extra="", st="o := -2147483648 - 1;",
         forvantat="tolk -2147483649; PLC sveper (int32) till 2147483647",
         hypotes="DIVERGERAR"),
    dict(namn="a23", kat="arit", typ="INT", extra="", st="o := MIN(3, 9);",
         forvantat="bada 3; kontrollfall",
         hypotes="LIKA"),
    dict(namn="a24", kat="arit", typ="INT", extra="", st="o := MAX(3, 9);",
         forvantat="bada 9; kontrollfall",
         hypotes="LIKA"),
    # ---- tid (via BOOL/DINT-sonder; TIME gar ej att mappa) ----
    dict(namn="t01", kat="tid", typ="BOOL", extra="", st="o := T#1s = T#1000ms;",
         forvantat="bada TRUE; enhetsrakning",
         hypotes="LIKA"),
    dict(namn="t02", kat="tid", typ="BOOL", extra="", st="o := T#1m = T#60s;",
         forvantat="bada TRUE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="t03", kat="tid", typ="BOOL", extra="", st="o := T#25h > T#1d;",
         forvantat="bada TRUE; 90M ms ryms i int32 - ingen granspassage annu",
         hypotes="LIKA"),
    dict(namn="t04", kat="tid", typ="DINT", extra="", st="o := TIME_TO_DINT(T#1s);",
         forvantat="bada 1000; kontrollfall",
         hypotes="LIKA"),
    dict(namn="t05", kat="tid", typ="DINT", extra="", st="o := TIME_TO_DINT(T#1s + T#500ms);",
         forvantat="bada 1500 om PLC adderar TIME likadant",
         hypotes="LIKA"),
    dict(namn="t06", kat="tid", typ="BOOL", extra="", st="o := T#0ms = T#0s;",
         forvantat="bada TRUE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="t07", kat="tid", typ="DINT", extra="", st="o := TIME_TO_DINT(T#100d);",
         forvantat="tolk 8640000000; PLC oviss - beror pa TIME-bredden i kedjan; matningen avgor",
         hypotes="OVISS"),
    dict(namn="t08", kat="tid", typ="BOOL", extra="", st="o := T#1d = T#24h;",
         forvantat="bada TRUE; dagnormalisering",
         hypotes="LIKA"),
    dict(namn="t09", kat="tid", typ="BOOL", extra="", st="o := T#2s > T#1500ms;",
         forvantat="bada TRUE; kontrollfall",
         hypotes="LIKA"),
    # ---- strang (via INT/BOOL-sonder; STRING gar ej att mappa) ----
    dict(namn="s01", kat="strang", typ="INT", extra="v_s01 : STRING;", st="v_s01 := 'hej'; o := LEN(v_s01);",
         forvantat="bada 3",
         hypotes="LIKA"),
    dict(namn="s02", kat="strang", typ="INT", extra="v_s02 : STRING;", st="v_s02 := ''; o := LEN(v_s02);",
         forvantat="bada 0; tom strang",
         hypotes="LIKA"),
    dict(namn="s03", kat="strang", typ="BOOL", extra="", st="o := 'abc' = 'abc';",
         forvantat="bada TRUE",
         hypotes="LIKA"),
    dict(namn="s04", kat="strang", typ="BOOL", extra="", st="o := 'abc' <> 'abd';",
         forvantat="bada TRUE",
         hypotes="LIKA"),
    dict(namn="s05", kat="strang", typ="BOOL", extra="", st="o := 'abc' < 'abd';",
         forvantat="bada TRUE om PLC jamfor strangar lexikografiskt",
         hypotes="LIKA"),
    dict(namn="s06", kat="strang", typ="BOOL", extra="", st="o := SEL(TRUE, 'a', 'b') = 'b';",
         forvantat="bada TRUE; SEL over strangar",
         hypotes="LIKA"),
    dict(namn="s07", kat="strang", typ="INT", extra="v_s07 : STRING;", st="v_s07 := '12345678901234567890'; o := LEN(v_s07);",
         forvantat="bada 20; langre strang",
         hypotes="LIKA"),
    dict(namn="s08", kat="strang", typ="INT", extra="v_s08 : STRING;", st="v_s08 := 'hello'; o := LEN(v_s08);",
         forvantat="bada 5; tilldelning + LEN",
         hypotes="LIKA"),
    dict(namn="s09", kat="strang", typ="BOOL", extra="", st="o := 'ABC' = 'abc';",
         forvantat="bada FALSE om jamforelsen ar skiftlageskanslig i bada",
         hypotes="LIKA"),
    # ---- bit ----
    dict(namn="b01", kat="bit", typ="BOOL", extra="", st="o := TRUE AND FALSE;",
         forvantat="bada FALSE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="b02", kat="bit", typ="BOOL", extra="", st="o := TRUE XOR TRUE;",
         forvantat="bada FALSE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="b03", kat="bit", typ="BOOL", extra="", st="o := NOT TRUE;",
         forvantat="bada FALSE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="b04", kat="bit", typ="WORD", extra="a_b04 : WORD := 16#FF00; b_b04 : WORD := 16#0F0F;", st="o := a_b04 AND b_b04;",
         forvantat="bada 16#0F00 = 3840",
         hypotes="LIKA"),
    dict(namn="b05", kat="bit", typ="WORD", extra="a_b05 : WORD := 16#FF00; b_b05 : WORD := 16#0F0F;", st="o := a_b05 OR b_b05;",
         forvantat="bada 16#FF0F = 65295",
         hypotes="LIKA"),
    dict(namn="b06", kat="bit", typ="WORD", extra="a_b06 : WORD := 16#FF00; b_b06 : WORD := 16#0F0F;", st="o := a_b06 XOR b_b06;",
         forvantat="bada 16#F00F = 61455",
         hypotes="LIKA"),
    dict(namn="b07", kat="bit", typ="WORD", extra="a_b07 : WORD := 16#00FF;", st="o := NOT a_b07;",
         forvantat="tolk -256 (ingen breddmask, obegransat int); PLC uint16 -> 65280",
         hypotes="DIVERGERAR"),
    dict(namn="b08", kat="bit", typ="BOOL", extra="", st="o := TRUE OR FALSE;",
         forvantat="bada TRUE; kontrollfall",
         hypotes="LIKA"),
    dict(namn="b09", kat="bit", typ="DWORD", extra="", st="o := 16#FFFFFFFF;",
         forvantat="bada 4294967295; DWORD-vagen hel",
         hypotes="LIKA"),
    # ---- stimuli (TILL_PLC-vagen; samma vardens i bada motorerna) ----
    dict(namn="i01", kat="stim", typ="INT", extra="", st="o := in_i;",
         forvantat="bada 20000; identitet over OPC UA",
         hypotes="LIKA"),
    dict(namn="i02", kat="stim", typ="INT", extra="", st="o := in_i * 2 + 1;",
         forvantat="tolk 40001; PLC int16 sveper: 40001 - 65536 = -25535",
         hypotes="DIVERGERAR"),
    dict(namn="i03", kat="stim", typ="INT", extra="", st="o := REAL_TO_INT(in_x);",
         forvantat="tolk 2; PLC 3 (avrundning via stimulus)",
         hypotes="DIVERGERAR"),
    dict(namn="i04", kat="stim", typ="REAL", extra="", st="o := in_x * 2.0;",
         forvantat="bada 5.0 exakt; REAL tur-och-retur",
         hypotes="LIKA"),
    dict(namn="i05", kat="stim", typ="BOOL", extra="", st="o := in_b AND TRUE;",
         forvantat="bada TRUE; BOOL tur-och-retur",
         hypotes="LIKA"),
]

# Grupper: program som laddas (ett uppladdningsvarv var).
# stimuli ges till BADA motorerna.
GRUPPER = [
    dict(station="A1K", fall=[f["namn"] for f in FALL if f["kat"] == "konv"],
         indata=[], stimuli={}),
    dict(station="A1A", fall=[f["namn"] for f in FALL if f["kat"] == "arit"],
         indata=[], stimuli={}),
    dict(station="A1T", fall=[f["namn"] for f in FALL if f["kat"] in ("tid", "strang")],
         indata=[], stimuli={}),
    dict(station="A1B", fall=[f["namn"] for f in FALL if f["kat"] in ("bit", "stim")],
         indata=[("Givare", "IntIn", "in_i", "INT", "TILL_PLC", None),
                 ("Givare", "RealIn", "in_x", "REAL", "TILL_PLC", None),
                 ("Givare", "BoolIn", "in_b", "BOOL", "TILL_PLC", None)],
         stimuli={"in_i": 20000, "in_x": 2.5, "in_b": True}),
]

FALL_AV_NAMN = dict((f["namn"], f) for f in FALL)


def _adress_for(klass, index, bit=None):
    if klass == "X":
        return "%%QX%d.%d" % (index // 8, bit if bit is not None else index % 8)
    return "%%%s%s%d" % ("Q", klass, index)


def bygg_program(grupp):
    """Karta + POU for en grupp. Varje fall far egna mappade utgangar."""
    fall = [FALL_AV_NAMN[n] for n in grupp["fall"]]
    raknare = {"X": 0, "B": 0, "W": 0, "D": 0, "L": 0}
    bitrak = [0]

    def naesta(typ):
        k = KLASS[typ]
        i = raknare[k]
        raknare[k] += 1
        if k == "X":
            b = bitrak[0]
            bitrak[0] += 1
            return "%%QX%d.%d" % (b // 8, b % 8)
        return "%%Q%s%d" % (k, i)

    rader = []
    for (komp, scen, tagg, typ, rikt, _adr) in grupp["indata"]:
        k = KLASS[typ]
        i = raknare[k]
        # Indataklassernas index ar egna (I-omradet); borja om per grupp.
        rader.append((komp, scen, tagg, typ, rikt, None))
    # Satt inadresserna: eget indexrum (%I).
    inrak = {"X": 0, "B": 0, "W": 0, "D": 0, "L": 0}
    inbit = [0]
    for j, rad in enumerate(rader):
        komp, scen, tagg, typ, rikt, _ = rad
        k = KLASS[typ]
        if k == "X":
            b = inbit[0]
            inbit[0] += 1
            adr = "%%IX%d.%d" % (b // 8, b % 8)
        else:
            adr = "%%I%s%d" % (k, inrak[k])
            inrak[k] += 1
        rader[j] = (komp, scen, tagg, typ, rikt, adr)
    # Kanarie: bevisar att programmet VERKLIGEN kors (fail-closed mot
    # "matte bara start"). Sist i varje program.
    b = inbit[0]
    inbit[0] += 1
    rader.append(("Kanarie", "In", "p_in", "BOOL", "TILL_PLC",
                  "%%IX%d.%d" % (b // 8, b % 8)))
    tagg_av_fall = {}
    for f in fall:
        tagg = "o_" + f["namn"]
        tagg_av_fall[f["namn"]] = tagg
        rader.append(("A1", "Ut_" + f["namn"], tagg, f["typ"], "FRAN_PLC",
                      naesta(f["typ"])))
    b = bitrak[0]
    bitrak[0] += 1
    rader.append(("Kanarie", "Ut", "q_ok", "BOOL", "FRAN_PLC",
                  "%%QX%d.%d" % (b // 8, b % 8)))
    karta = karta_av_rader(grupp["station"], rader)
    delar = [("PROGRAM %s\n" % grupp["station"]), karta.deklarationstext()]
    interna = "".join("    %s\n" % f["extra"] for f in fall if f["extra"])
    if interna:
        delar.append("VAR\n" + interna + "END_VAR\n")
    for f in fall:
        delar.append("    " + f["st"].replace("o :=", tagg_av_fall[f["namn"]] + " :=", 1) + "\n")
    delar.append("    q_ok := p_in;\n")
    delar.append("END_PROGRAM\n")
    return karta, "".join(delar), tagg_av_fall


def tolk_kor(karta, pou, stimuli):
    # Tolkens NOLLVARDE kan bool/int/real; alla heltalstyper (DINT, WORD,
    # DWORD, BYTE) lagras som obegransade Python-int i tolken.
    def tolktyp(namn):
        return {"BOOL": "bool", "REAL": "real"}.get(namn, "int")
    signaler = dict((s.tagg, tolktyp(s.typ.namn)) for s in karta.signaler)
    rikt = dict((s.tagg, ("in" if s.riktning == "TILL_PLC" else "out"))
                for s in karta.signaler)
    t = T.Tolk(pou, signaler, rikt)
    for namn, varde in stimuli.items():
        t.satt(namn, varde)
    t.scan()
    return t


def jamfor(typ, tolkvarde, oplcvarde):
    if typ == "REAL":
        a, b = float(tolkvarde), float(oplcvarde)
        if a == b:
            return "LIKA"
        skala = max(1.0, abs(a), abs(b))
        if abs(a - b) <= REAL_TOL * skala:
            return "NARA"
        return "DIVERGERAR"
    if typ == "BOOL":
        return "LIKA" if bool(tolkvarde) == bool(oplcvarde) else "DIVERGERAR"
    return "LIKA" if int(tolkvarde) == int(oplcvarde) else "DIVERGERAR"


def kompiler_enkelt(fall, utkat, strucpp_paket, node):
    """Varje konstruktion kompileras ENSKILT som fristaende program."""
    decl = "o : %s;\n" % fall["typ"]
    # Stimulifallen refererar insignaler; de deklareras i det enskilda
    # programmet sa att kompileringen prover samma konstruktion.
    decl += "    in_i : INT;\n    in_x : REAL;\n    in_b : BOOL;\n"
    if fall["extra"]:
        decl += "    %s\n" % fall["extra"]
    pou = ("PROGRAM Ens\nVAR\n    " + decl + "END_VAR\n    " + fall["st"]
           + "\nEND_PROGRAM\n")
    full = pou + P.konfigurationstext("Ens", intervall=P.TASKINTERVALL)
    P.kompilera(full, os.path.join(utkat, fall["namn"]), strucpp_paket, node=node)
    return pou


async def _las_alla(klient_opc, station, taggar):
    ut = {}
    for tagg in taggar:
        nod = klient_opc.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, tagg))
        ut[tagg] = await nod.read_value()
    return ut


async def _skriv_alla(klient_opc, ua, station, stimuli, typer):
    for tagg, varde in stimuli.items():
        nod = klient_opc.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, tagg))
        vt = getattr(ua.VariantType, VARIANT[typer[tagg]])
        await nod.write_value(ua.DataValue(ua.Variant(varde, vt)))


async def mat_program(klient, args, grupp, karta, pou):
    Client, ua = _asyncua()
    full = pou + P.konfigurationstext(grupp["station"], intervall=P.TASKINTERVALL)
    kat = os.path.join(args.byggkatalog, grupp["station"])
    forb = P.kompilera(full, os.path.join(kat, "for"), args.strucpp_paket, node=args.node)
    konf = opcuakonfig.konfiguration(karta, forb, args.endpoint)
    zipvag, _ = P.bygg_projekt(full, os.path.join(kat, "arkiv"),
                               args.strucpp_paket, args.runtime_include,
                               opcua_konfig=konf)
    klient.ladda_upp(zipvag)
    await asyncio.sleep(0.5)
    klient.vanta_pa_kompilering()
    tillstand = klient.starta_och_vanta()
    typer = dict((s.tagg, s.typ.namn) for s in karta.signaler)
    uttagg = [s.tagg for s in karta.signaler if s.riktning == "FRAN_PLC"]
    opc = Client(url=args.endpoint, timeout=5.0)
    await _anslut(opc, tidsgrans=30.0)
    try:
        stimuli = dict(grupp["stimuli"])
        stimuli["p_in"] = True
        await _skriv_alla(opc, ua, grupp["station"], stimuli, typer)
        await asyncio.sleep(0.6)
        # Kanalkontroll: insignalerna maste ha fastnat.
        for tagg, varde in stimuli.items():
            nod = opc.get_node("ns=2;s=%s" % opcuakonfig.nodid(grupp["station"], tagg))
            tillbaka = await nod.read_value()
            if isinstance(varde, bool):
                ok = bool(tillbaka) == varde
            elif isinstance(varde, float):
                ok = abs(float(tillbaka) - varde) < 1e-9
            else:
                ok = int(tillbaka) == int(varde)
            if not ok:
                return {"ok": False, "tillstand": tillstand,
                        "skal": "kanalfel: %s skrevs %r men lastes %r"
                                % (tagg, varde, tillbaka)}
        varden = await _las_alla(opc, grupp["station"], uttagg)
        # Kanarie: q_ok ska folja p_in - annars kors inte programmet.
        if not bool(varden.get("q_ok", False)):
            return {"ok": False, "tillstand": tillstand,
                    "skal": "kanarie q_ok hogt vantat men %r - programmet kors inte"
                            % (varden.get("q_ok"),)}
        await _skriv_alla(opc, ua, grupp["station"], {"p_in": False}, typer)
        await asyncio.sleep(0.6)
        nod = opc.get_node("ns=2;s=%s" % opcuakonfig.nodid(grupp["station"], "q_ok"))
        if bool(await nod.read_value()):
            return {"ok": False, "tillstand": tillstand,
                    "skal": "kanarie q_ok foljde inte p_in till FALSE"}
        return {"ok": True, "tillstand": tillstand, "varden": varden}
    finally:
        await opc.disconnect()


def kor(args):
    klient = OpenPlcV4(args.bas, args.anvandare, args.losenord, tillat_osignerat=True)
    klient.skapa_forsta_anvandare()
    version = klient.version()
    print("runtime: %s" % version)
    resultat = {"runtime": version, "program": [], "fall": []}
    for grupp in GRUPPER:
        if args.program and grupp["station"] not in args.program:
            continue
        print("=== %s ===" % grupp["station"])
        karta, pou, tagg_av_fall = bygg_program(grupp)
        post = {"station": grupp["station"]}
        # Lokal grind: hela POU:n genom validatorn.
        try:
            rapp = validera(pou)
            if not rapp.ok:
                post.update(ok=False, skal="validator foll: %s" % str(rapp)[:300])
                for f in [FALL_AV_NAMN[n] for n in grupp["fall"]]:
                    resultat["fall"].append(
                        {"namn": f["namn"], "program": grupp["station"],
                         "dom": "EJ_KORD", "skal": "programmets grind foll"})
                resultat["program"].append(post)
                print("  EJ_KORT: %s" % post["skal"])
                continue
        except Exception as fel:
            post.update(ok=False, skal="validator kraschade: %r" % fel)
            resultat["program"].append(post)
            print("  EJ_KORT: %s" % post["skal"])
            continue
        # Varje konstruktion kompileras ENSKILT.
        enskilt_ok = {}
        for f in [FALL_AV_NAMN[n] for n in grupp["fall"]]:
            try:
                kompiler_enkelt(f, os.path.join(args.byggkatalog, "enskilt"),
                                args.strucpp_paket, args.node)
                enskilt_ok[f["namn"]] = True
            except Exception as fel:
                enskilt_ok[f["namn"]] = str(fel)[:200]
        # Tolken kor samma stimuli.
        stimuli = dict(grupp["stimuli"])
        stimuli["p_in"] = True
        try:
            t = tolk_kor(karta, pou, stimuli)
        except Exception as fel:
            post.update(ok=False, skal="tolken foll: %r" % fel)
            resultat["program"].append(post)
            print("  EJ_KORT: %s" % post["skal"])
            continue
        if args.bara_lokalt:
            for f in [FALL_AV_NAMN[n] for n in grupp["fall"]]:
                resultat["fall"].append(
                    {"namn": f["namn"], "program": grupp["station"],
                     "dom": "EJ_KORD" if enskilt_ok[f["namn"]] is not True else "LOKALT_OK",
                     "tolk": repr(t.las(tagg_av_fall[f["namn"]]))})
            post.update(ok=True, skal="bara lokalt")
            resultat["program"].append(post)
            continue
        try:
            mot = asyncio.run(mat_program(klient, args, grupp, karta, pou))
        except (OpenPlcFel, Exception) as fel:
            post.update(ok=False, skal="matningen foll: %r" % fel)
            resultat["program"].append(post)
            print("  EJ_KORT: %s" % post["skal"])
            for f in [FALL_AV_NAMN[n] for n in grupp["fall"]]:
                resultat["fall"].append(
                    {"namn": f["namn"], "program": grupp["station"],
                     "dom": "EJ_KORD", "skal": post["skal"]})
            continue
        if not mot["ok"]:
            post.update(ok=False, skal=mot["skal"])
            resultat["program"].append(post)
            print("  EJ_KORT: %s" % mot["skal"])
            for f in [FALL_AV_NAMN[n] for n in grupp["fall"]]:
                resultat["fall"].append(
                    {"namn": f["namn"], "program": grupp["station"],
                     "dom": "EJ_KORD", "skal": mot["skal"]})
            continue
        post.update(ok=True, tillstand=mot["tillstand"])
        resultat["program"].append(post)
        for f in [FALL_AV_NAMN[n] for n in grupp["fall"]]:
            tagg = tagg_av_fall[f["namn"]]
            if enskilt_ok[f["namn"]] is not True:
                resultat["fall"].append(
                    {"namn": f["namn"], "program": grupp["station"],
                     "dom": "EJ_KORD",
                     "skal": "enskild kompilering foll: %s" % enskilt_ok[f["namn"]]})
                print("  %-5s EJ_KORD (enskild kompilering)" % f["namn"])
                continue
            tolkvarde = t.las(tagg)
            oplcvarde = mot["varden"][tagg]
            dom = jamfor(f["typ"], tolkvarde, oplcvarde)
            resultat["fall"].append(
                {"namn": f["namn"], "kat": f["kat"], "typ": f["typ"],
                 "program": grupp["station"], "konstruktion": f["st"],
                 "forvantat": f["forvantat"], "hypotes": f["hypotes"],
                 "tolk": tolkvarde if isinstance(tolkvarde, bool) else (
                     tolkvarde if isinstance(tolkvarde, int) else float(tolkvarde)),
                 "openplc": (bool(oplcvarde) if f["typ"] == "BOOL"
                             else (float(oplcvarde) if f["typ"] == "REAL"
                                   else int(oplcvarde))),
                 "dom": dom})
            print("  %-5s %-10s tolk=%r openplc=%r %s" % (
                f["namn"], dom, tolkvarde, oplcvarde,
                "(!)" if dom != f["hypotes"] and f["hypotes"] != "OVISS" else ""))
    return resultat


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bas", default="https://127.0.0.1:18444")
    ap.add_argument("--anvandare", default="vcassist")
    ap.add_argument("--losenord", default="vcassist")
    ap.add_argument("--endpoint", default="opc.tcp://172.17.0.3:4840/openplc/opcua")
    ap.add_argument("--strucpp-paket", default="/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/scratchpad/strucpp_npm/package")
    ap.add_argument("--runtime-include", default="/tmp/opencode/m108/strucpp-bin/strucpp/runtime/include")
    ap.add_argument("--byggkatalog", default="/tmp/a1_bygg")
    ap.add_argument("--node", default="node")
    ap.add_argument("--program", nargs="*", default=None)
    ap.add_argument("--bara-lokalt", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    os.makedirs(a.byggkatalog, exist_ok=True)
    if abs(T.SCAN_MS - 20.0) > 1e-9:
        print("FEL: tolkens cykel %.3f != 20.0" % T.SCAN_MS)
        return 1
    try:
        r = kor(a)
    except (OpenPlcFel, Exception) as fel:
        print("FEL: %r" % (fel,))
        return 1
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"bankpost": BANKPOST, "resultat": r}, fh,
                      indent=2, ensure_ascii=False, sort_keys=True)
    n = len(r["fall"])
    n_lika = sum(1 for f in r["fall"] if f.get("dom") == "LIKA")
    n_nara = sum(1 for f in r["fall"] if f.get("dom") == "NARA")
    n_div = sum(1 for f in r["fall"] if f.get("dom") == "DIVERGERAR")
    n_ej = sum(1 for f in r["fall"] if f.get("dom") not in ("LIKA", "NARA", "DIVERGERAR"))
    print("A1-SLUT: %d fall: %d LIKA, %d NARA, %d DIVERGERAR, %d EJ_KORD/ovrigt"
          % (n, n_lika, n_nara, n_div, n_ej))
    felhyp = [f["namn"] for f in r["fall"]
              if f.get("hypotes") not in (None, "OVISS") and f.get("dom") != f.get("hypotes")]
    if felhyp:
        print("HYPOTESFEL (vantat %s, fick annat): %s" % ("enligt kalla", " ".join(felhyp)))
    return 0 if (n_div == 0 and n_ej == 0 and n == len(FALL)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
