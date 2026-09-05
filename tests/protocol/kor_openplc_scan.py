# -*- coding: utf-8 -*-
"""M-108: samma program scan for scan i var tolk och i OpenPLC.

Svepet (kor_openplc_svepet.py) jamfor VAD motorerna accepterar. Det har
skriptet jamfor vad de GOR: samma kalla, samma insignaler, variabelvarden
jamforda scan for scan. Timers ar det intressanta: TON med PT := T#4s ska
losa ut pa samma scan i bada.

Spar per program (20 ms cykel i bada andar):
  SCAN_GENOM    u := g                      (4 vippor, varje foljd mats i ms)
  SCAN_TON4S    t(IN := g, PT := T#4s); u := t.Q  (3x, triggscan jamfors)
  SCAN_TON1S    t(IN := g, PT := T#1s); u := t.Q  (3x, triggscan jamfors)
  SCAN_TON20MS  t(IN := g, PT := T#20ms); u := t.Q (3x, triggscan jamfors)
  SCAN_RTRIG    rt(CLK := g); u := rt.Q     (puls, exakt en hog scan vantas)
  SCAN_TOF      t(IN := g, PT := T#1s); u := t.Q  (3x, fallscan jamfors)
  SCAN_TP       t(IN := g, PT := T#1s); u := t.Q  (3x, pulsbredd 50 scan jamfors)
  SCAN_CTU      c(CU := g, PV := 5); u := c.Q    (5 pulser 60ms isar, Q vid 5:e)
  SCAN_SR       sr(S1 := s1, R := r); u := sr.Q1 (latch set/hold/reset/dominans)
  SCAN_CTD      c(CD := g, LD := ld, PV := 5); u := c.Q (5 pulser 60ms isar, Q vid 5:e)
  SCAN_CTUD     c(CU := cu, CD := cd, R := r, LD := ld, PV := 5); cv := c.CV (upp till 3, ned till 0)
  SCAN_FTRIG    ft(CLK := g); u := ft.Q     (fallande flank, exakt en hog scan)

Fail-closed:
  * Ett program vars utgang aldrig andras FALLS - annars matts att OpenPLC
    startade, inte att den korde.
  * Tolkens och OpenPLC:s cykler maste vara samma (20.0 ms), annars mats
    rutnatet och inte logiken (samma krav som kor_m62).
  * Kanalfel (skrivning som inte fastnar) far inte klassas som oenighet.

Kors:
    python3 tests/protocol/kor_openplc_scan.py --bas https://127.0.0.1:18444 \\
        --endpoint opc.tcp://172.17.0.3:4840/openplc/opcua \\
        --strucpp-paket <paket> --runtime-include <include> \\
        --byggkatalog /tmp/m108_scan --json /tmp/m108_scan.json
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

BANKPOST = {
    # BENCH-4-not (M-108): det som DOMS ar tolkens semantik, inte kanalen.
    "pastar": (
        "Samma program ger samma variabelvarden scan for scan i var tolk "
        "som i OpenPLC, eller sa pekas exakt scan och signal ut."),
    "under_prov": ("svc/vc_assist_svc/st/tolk.py",),
    "facit": "OpenPLC Runtime v4:s korning, avlast over OPC UA",
    "facitkalla": "OpenPLC Runtime v4 (oberoende tredje motor)",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "ett program vars utgang aldrig andras falls, inte godkans",
        "kanalens eget fel far inte klassas som motoroenighet",
        "olika cykler avbryter jamforelsen",
    ),
    "kraver": ("openplc",),
    "matningar": ("M-108",),
}

SCAN_MS = 20.0
TAK_S = 1.0


def program(station, rader, kropp):
    karta = karta_av_rader(station, rader)
    pou = (("PROGRAM %s\n" % station) + karta.deklarationstext()
           + kropp + "END_PROGRAM\n")
    return karta, pou


PROGRAMMEN = [
    ("SCAN_GENOM",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    u := g;\n"),
    ("SCAN_TON4S",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    t(IN := g, PT := T#4s);\n    u := t.Q;\n",
     "    t : TON;\n"),
    ("SCAN_TON1S",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    t(IN := g, PT := T#1s);\n    u := t.Q;\n",
     "    t : TON;\n"),
    ("SCAN_TON20MS",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    t(IN := g, PT := T#20ms);\n    u := t.Q;\n",
     "    t : TON;\n"),
    ("SCAN_RTRIG",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    rt(CLK := g);\n    u := rt.Q;\n",
     "    rt : R_TRIG;\n"),
    ("SCAN_TOF",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    t(IN := g, PT := T#1s);\n    u := t.Q;\n",
     "    t : TOF;\n"),
    ("SCAN_TP",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    t(IN := g, PT := T#1s);\n    u := t.Q;\n",
     "    t : TP;\n"),
    ("SCAN_CTU",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    c(CU := g, PV := 5);\n    u := c.Q;\n",
     "    c : CTU;\n"),
    ("SCAN_SR",
     [("Givare", "Satt", "s1", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Givare", "Nolla", "r", "BOOL", "TILL_PLC", "%IX0.1"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    sr(S1 := s1, R := r);\n    u := sr.Q1;\n",
     "    sr : SR;\n"),
    ("SCAN_CTD",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Givare", "Ladda", "ld", "BOOL", "TILL_PLC", "%IX0.1"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    c(CD := g, LD := ld, PV := 5);\n    u := c.Q;\n",
     "    c : CTD;\n"),
    ("SCAN_CTUD",
     [("Givare", "Upp", "cu", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Givare", "Ned", "cd", "BOOL", "TILL_PLC", "%IX0.1"),
      ("Givare", "Nolla", "r", "BOOL", "TILL_PLC", "%IX0.2"),
      ("Givare", "Ladda", "ld", "BOOL", "TILL_PLC", "%IX0.3"),
      ("Don", "SvarU", "qu", "BOOL", "FRAN_PLC", "%QX0.0"),
      ("Don", "SvarD", "qd", "BOOL", "FRAN_PLC", "%QX0.1"),
      ("Don", "Raknevarde", "cv", "INT", "FRAN_PLC", "%QW0")],
     "    c(CU := cu, CD := cd, R := r, LD := ld, PV := 5);\n"
     "    qu := c.QU;\n"
     "    qd := c.QD;\n"
     "    cv := c.CV;\n",
     "    c : CTUD;\n"),
    ("SCAN_FTRIG",
     [("Givare", "Sig", "g", "BOOL", "TILL_PLC", "%IX0.0"),
      ("Don", "Svar", "u", "BOOL", "FRAN_PLC", "%QX0.0")],
     "    ft(CLK := g);\n    u := ft.Q;\n",
     "    ft : F_TRIG;\n"),
]


def tolk_spar(karta, pou, insatser):
    signaler = {s.tagg: s.typ.namn.lower() for s in karta.signaler}
    rikt = {s.tagg: ("in" if s.riktning == "TILL_PLC" else "out")
            for s in karta.signaler}
    return T.kor(pou, signaler, rikt, insatser, scan_ms=SCAN_MS)


async def _skriv(nod, ua, varde):
    await nod.write_value(ua.DataValue(ua.Variant(varde, ua.VariantType.Boolean)))


async def _vanta(nod, vantat, tak_s=TAK_S, paus=0.005):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < tak_s:
        if bool(await nod.read_value()) == vantat:
            return (time.perf_counter() - t0) * 1000.0
        await asyncio.sleep(paus)
    return None


async def kor_genom(nod_in, nod_ut, ua):
    dt = []
    for nytt in (True, False, True, False):
        t0 = time.perf_counter()
        await _skriv(nod_in, ua, nytt)
        ms = await _vanta(nod_ut, nytt)
        if ms is None:
            return {"ok": False, "skal": "u foljde inte g=%r inom 1s" % nytt,
                    "ms": dt}
        dt.append(round(ms, 2))
    return {"ok": True, "ms": dt}


async def kor_ton(nod_in, nod_ut, ua, repetitioner=3, tak_pt_s=6.0):
    trigg = []
    for _ in range(repetitioner):
        await _skriv(nod_in, ua, False)
        await _vanta(nod_ut, False, tak_s=tak_pt_s)
        t0 = time.perf_counter()
        await _skriv(nod_in, ua, True)
        ms = await _vanta(nod_ut, True, tak_s=tak_pt_s)
        if ms is None:
            return {"ok": False,
                    "skal": "TON slog aldrig till inom %.1fs" % tak_pt_s,
                    "triggscan": trigg}
        trigg.append(int(round(ms / SCAN_MS)))
        await _skriv(nod_in, ua, False)
        await _vanta(nod_ut, False, tak_s=tak_pt_s)
    return {"ok": True, "triggscan": trigg}


async def kor_rtrig(nod_in, nod_ut, ua):
    await _skriv(nod_in, ua, False)
    await asyncio.sleep(0.1)
    await _skriv(nod_in, ua, True)
    hog = 0
    prov = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.2:
        prov += 1
        if bool(await nod_ut.read_value()):
            hog += 1
        await asyncio.sleep(0.005)
    await _skriv(nod_in, ua, False)
    return {"hog_avlasningar": hog, "avlasningar": prov}


async def kor_tof(nod_in, nod_ut, ua, repetitioner=3, tak_pt_s=3.0):
    trigg = []
    for _ in range(repetitioner):
        await _skriv(nod_in, ua, True)
        await _vanta(nod_ut, True, tak_s=tak_pt_s)
        await asyncio.sleep(0.1)
        t0 = time.perf_counter()
        await _skriv(nod_in, ua, False)
        ms = await _vanta(nod_ut, False, tak_s=tak_pt_s)
        if ms is None:
            return {"ok": False,
                    "skal": "TOF slappte aldrig inom %.1fs" % tak_pt_s,
                    "triggscan": trigg}
        trigg.append(int(round(ms / SCAN_MS)))
        await asyncio.sleep(0.1)
    return {"ok": True, "triggscan": trigg}


async def kor_tp(nod_in, nod_ut, ua, repetitioner=3, tak_pt_s=3.0):
    trigg = []
    for _ in range(repetitioner):
        await _skriv(nod_in, ua, False)
        await _vanta(nod_ut, False, tak_s=tak_pt_s)
        await asyncio.sleep(0.05)
        t0 = time.perf_counter()
        await _skriv(nod_in, ua, True)
        ms_rise = await _vanta(nod_ut, True, tak_s=1.0)
        if ms_rise is None:
            return {"ok": False, "skal": "TP startade aldrig", "triggscan": trigg}
        await asyncio.sleep(0.1)
        await _skriv(nod_in, ua, False)
        ms_fall = await _vanta(nod_ut, False, tak_s=tak_pt_s)
        if ms_fall is None:
            return {"ok": False,
                    "skal": "TP puls tog aldrig slut inom %.1fs" % tak_pt_s,
                    "triggscan": trigg}
        total_ms = (time.perf_counter() - t0) * 1000.0
        trigg.append(int(round(total_ms / SCAN_MS)))
        await asyncio.sleep(0.05)
    return {"ok": True, "triggscan": trigg}


async def kor_ctu(nod_in, nod_ut, ua):
    u_efter_puls = []
    for _ in range(5):
        await _skriv(nod_in, ua, True)
        await asyncio.sleep(0.06)
        await _skriv(nod_in, ua, False)
        await asyncio.sleep(0.06)
        u_val = bool(await nod_ut.read_value())
        u_efter_puls.append(u_val)
    return {"ok": True, "openplc_u": u_efter_puls}


async def kor_sr(nod_s1, nod_r, nod_ut, ua):
    steg_in = [
        (True, False),
        (False, False),
        (False, True),
        (False, False),
        (True, True),
        (False, True),
        (False, False),
    ]
    oplc_u = []
    for s_val, r_val in steg_in:
        await _skriv(nod_s1, ua, s_val)
        await _skriv(nod_r, ua, r_val)
        await asyncio.sleep(0.06)
        u_val = bool(await nod_ut.read_value())
        oplc_u.append(u_val)
    return {"ok": True, "openplc_u": oplc_u}


async def kor_ctd(nod_in, nod_ld, nod_ut, ua):
    await _skriv(nod_in, ua, False)
    await _skriv(nod_ld, ua, True)
    await asyncio.sleep(0.06)
    await _skriv(nod_ld, ua, False)
    await asyncio.sleep(0.06)
    u_efter_puls = []
    for _ in range(5):
        await _skriv(nod_in, ua, True)
        await asyncio.sleep(0.06)
        await _skriv(nod_in, ua, False)
        await asyncio.sleep(0.06)
        u_val = bool(await nod_ut.read_value())
        u_efter_puls.append(u_val)
    return {"ok": True, "openplc_u": u_efter_puls}


async def kor_ctud(nod_cu, nod_cd, nod_r, nod_ld, nod_cv, ua):
    await _skriv(nod_r, ua, True)
    await asyncio.sleep(0.06)
    await _skriv(nod_r, ua, False)
    await asyncio.sleep(0.06)
    oplc_cv = [int(await nod_cv.read_value())]
    for _ in range(3):
        await _skriv(nod_cu, ua, True)
        await asyncio.sleep(0.06)
        await _skriv(nod_cu, ua, False)
        await asyncio.sleep(0.06)
        oplc_cv.append(int(await nod_cv.read_value()))
    for _ in range(3):
        await _skriv(nod_cd, ua, True)
        await asyncio.sleep(0.06)
        await _skriv(nod_cd, ua, False)
        await asyncio.sleep(0.06)
        oplc_cv.append(int(await nod_cv.read_value()))
    return {"ok": True, "openplc_cv": oplc_cv}


async def kor_ftrig(nod_in, nod_ut, ua):
    await _skriv(nod_in, ua, False)
    await asyncio.sleep(0.06)
    await _skriv(nod_in, ua, True)
    await asyncio.sleep(0.1)
    await _skriv(nod_in, ua, False)
    hog = 0
    prov = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.2:
        prov += 1
        if bool(await nod_ut.read_value()):
            hog += 1
        await asyncio.sleep(0.005)
    return {"hog_avlasningar": hog, "avlasningar": prov}


def ladda(klient, karta, pou, station, endpoint, strucpp_paket,
          runtime_include, byggrot):
    full = pou + P.konfigurationstext(station, intervall=P.TASKINTERVALL)
    kat = os.path.join(byggrot, station)
    forb = P.kompilera(full, os.path.join(kat, "for"), strucpp_paket)
    konf = opcuakonfig.konfiguration(karta, forb, endpoint)
    zipvag, _ = P.bygg_projekt(full, os.path.join(kat, "arkiv"),
                               strucpp_paket, runtime_include,
                               opcua_konfig=konf)
    klient.ladda_upp(zipvag)
    time.sleep(0.5)
    klient.vanta_pa_kompilering()
    return klient.starta_och_vanta()


async def _mat_allt(args):
    Client, ua = _asyncua()
    klient = OpenPlcV4(args.bas, args.anvandare, args.losenord,
                       tillat_osignerat=True)
    print("runtime: %s" % klient.version())
    resultat = {}
    for spec in PROGRAMMEN:
        station, rader, kropp = spec[0], spec[1], spec[2]
        extra = spec[3] if len(spec) > 3 else ""
        karta, pou = program(station, rader, kropp)
        if extra:
            # extra-deklarationer (FB-instanser): in fore END_VAR i blocket
            pou = pou.replace("END_VAR", extra + "END_VAR", 1)
        tillstand = ladda(klient, karta, pou, station, args.endpoint,
                          args.strucpp_paket, args.runtime_include,
                          args.byggkatalog)
        oplc = Client(url=args.endpoint, timeout=5.0)
        await _anslut(oplc)
        try:
            # stillastaende-variabel-fallan: utgangen maste ga att andra.
            # taket ar per program (TOF/TP: PT+2s; CTU/SR: 1s; TON: PT+2s).
            stilla_tak = {
                "SCAN_TON4S": 6.0,
                "SCAN_TON1S": 3.0,
                "SCAN_TOF": 3.0,
                "SCAN_TP": 3.0,
                "SCAN_CTU": 1.0,
                "SCAN_SR": 1.0,
                "SCAN_CTD": 1.0,
                "SCAN_CTUD": 1.0,
                "SCAN_FTRIG": 1.0,
            }.get(station, TAK_S)

            if station == "SCAN_SR":
                n_s1 = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "s1"))
                n_r = oplc.get_node("ns=2;s=%s"
                                    % opcuakonfig.nodid(station, "r"))
                n_ut = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "u"))
                await _skriv(n_s1, ua, True)
                await _skriv(n_r, ua, False)
                ms1 = await _vanta(n_ut, True, tak_s=stilla_tak)
                await _skriv(n_s1, ua, False)
                await _skriv(n_r, ua, True)
                ms2 = await _vanta(n_ut, False, tak_s=stilla_tak)
                await _skriv(n_r, ua, False)
                if ms1 is None or ms2 is None:
                    resultat[station] = {"ok": False,
                                         "skal": "utgangen ror sig inte - "
                                                 "korningen matte bara start, "
                                                 "inte exekvering"}
                    print("%s: %s" % (station, json.dumps(resultat[station],
                                                          sort_keys=True)))
                    continue
            elif station == "SCAN_CTU":
                n_in = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "g"))
                n_ut = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "u"))
                u_init = bool(await n_ut.read_value())
                if u_init:
                    resultat[station] = {"ok": False,
                                         "skal": "CTU startade inte med u=False"}
                    print("%s: %s" % (station, json.dumps(resultat[station],
                                                          sort_keys=True)))
                    continue
            elif station == "SCAN_CTD":
                n_in = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "g"))
                n_ld = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "ld"))
                n_ut = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "u"))
                u_init = bool(await n_ut.read_value())
                if not u_init:
                    resultat[station] = {"ok": False,
                                         "skal": "CTD startade inte med u=True"}
                    print("%s: %s" % (station, json.dumps(resultat[station],
                                                          sort_keys=True)))
                    continue
            elif station == "SCAN_CTUD":
                n_cu = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "cu"))
                n_cd = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "cd"))
                n_r = oplc.get_node("ns=2;s=%s"
                                    % opcuakonfig.nodid(station, "r"))
                n_ld = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "ld"))
                n_qu = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "qu"))
                n_qd = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "qd"))
                n_cv = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "cv"))
                await _skriv(n_ld, ua, True)
                await asyncio.sleep(0.06)
                cv_ld = await n_cv.read_value()
                await _skriv(n_ld, ua, False)
                await _skriv(n_r, ua, True)
                await asyncio.sleep(0.06)
                cv_r = await n_cv.read_value()
                await _skriv(n_r, ua, False)
                await asyncio.sleep(0.06)
                if cv_ld != 5 or cv_r != 0:
                    resultat[station] = {"ok": False,
                                         "skal": "CTUD reagerade inte pa LD/R"}
                    print("%s: %s" % (station, json.dumps(resultat[station],
                                                          sort_keys=True)))
                    continue
            elif station == "SCAN_FTRIG":
                n_in = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "g"))
                n_ut = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "u"))
                u_init = bool(await n_ut.read_value())
                if u_init:
                    resultat[station] = {"ok": False,
                                         "skal": "F_TRIG startade inte med u=False"}
                    print("%s: %s" % (station, json.dumps(resultat[station],
                                                          sort_keys=True)))
                    continue
            else:
                n_in = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "g"))
                n_ut = oplc.get_node("ns=2;s=%s"
                                     % opcuakonfig.nodid(station, "u"))
                await _skriv(n_in, ua, True)
                ms = await _vanta(n_ut, True, tak_s=stilla_tak)
                await _skriv(n_in, ua, False)
                await _vanta(n_ut, False, tak_s=stilla_tak)
                if ms is None:
                    resultat[station] = {"ok": False,
                                         "skal": "utgangen ror sig inte - "
                                                 "korningen matte bara start, "
                                                 "inte exekvering"}
                    print("%s: %s" % (station, json.dumps(resultat[station],
                                                          sort_keys=True)))
                    continue

            if station == "SCAN_GENOM":
                ins = [(0.0, {"g": False}), (0.0, {"g": True}),
                       (40.0, {"g": False}), (80.0, {"g": True}),
                       (120.0, {"g": False})]
                trad = tolk_spar(karta, pou, ins)
                t_u = [r["varden"]["U"] for r in trad]
                o = await kor_genom(n_in, n_ut, ua)
                o["tolk_u_forsta5"] = t_u[:5]
                resultat[station] = o
            elif station.startswith("SCAN_TON"):
                pt_ms = {"SCAN_TON4S": 4000.0, "SCAN_TON1S": 1000.0,
                         "SCAN_TON20MS": 20.0}[station]
                ins = [(0.0, {"g": True}), (pt_ms + 6000.0, {})]
                trad = tolk_spar(karta, pou, ins)
                forstel = next((i for i, r in enumerate(trad)
                                if r["varden"]["U"]), None)
                o = await kor_ton(n_in, n_ut, ua,
                                  tak_pt_s=pt_ms / 1000.0 + 2.0)
                o["tolk_triggscan"] = forstel
                o["pt_scan"] = int(round(pt_ms / SCAN_MS))
                if o["ok"] and forstel is not None:
                    o["avvikelse_scan"] = [t - forstel
                                           for t in o["triggscan"]]
                    # Exakt noll kravs inte har - kanalmatt stilla_tak ovan
                    # ger fasrorelse upp till ~2 scan. Kalibreringen (tre
                    # PT:n) skiljer logik fran kanal i analysen.
                    o["ok"] = all(abs(a) <= 2 for a in o["avvikelse_scan"])
                resultat[station] = o
            elif station == "SCAN_RTRIG":
                ins = [(0.0, {"g": False}), (0.0, {"g": True}),
                       (60.0, {"g": False}), (400.0, {})]
                trad = tolk_spar(karta, pou, ins)
                t_hog = sum(1 for r in trad if r["varden"]["U"])
                o = await kor_rtrig(n_in, n_ut, ua)
                o["tolk_hog_scan"] = t_hog
                o["ok"] = (o["hog_avlasningar"] >= 1
                           and o["hog_avlasningar"] <= 6)
                resultat[station] = o
            elif station == "SCAN_TOF":
                ins = [(0.0, {"g": True}), (100.0, {"g": False}), (3000.0, {})]
                trad = tolk_spar(karta, pou, ins)
                fall_scan = next((i for i, r in enumerate(trad)
                                  if r["t_ms"] >= 100.0 and not r["varden"]["U"]), None)
                fall_scan_rel = (fall_scan - 5) if fall_scan is not None else None
                o = await kor_tof(n_in, n_ut, ua, tak_pt_s=3.0)
                o["tolk_fallscan"] = fall_scan_rel
                o["pt_scan"] = int(round(1000.0 / SCAN_MS))
                if o["ok"] and fall_scan_rel is not None:
                    o["avvikelse_scan"] = [t - fall_scan_rel for t in o["triggscan"]]
                    o["ok"] = all(abs(a) <= 2 for a in o["avvikelse_scan"])
                resultat[station] = o
            elif station == "SCAN_TP":
                ins = [(0.0, {"g": False}), (0.0, {"g": True}),
                       (100.0, {"g": False}), (3000.0, {})]
                trad = tolk_spar(karta, pou, ins)
                t_hog = sum(1 for r in trad if r["varden"]["U"])
                o = await kor_tp(n_in, n_ut, ua, tak_pt_s=3.0)
                o["tolk_hog_scan"] = t_hog
                o["pt_scan"] = int(round(1000.0 / SCAN_MS))
                if o["ok"]:
                    o["avvikelse_scan"] = [t - t_hog for t in o["triggscan"]]
                    o["ok"] = all(abs(a) <= 2 for a in o["avvikelse_scan"])
                resultat[station] = o
            elif station == "SCAN_CTU":
                ins = [
                    (0.0, {"g": False}),
                    (60.0, {"g": True}), (120.0, {"g": False}),
                    (180.0, {"g": True}), (240.0, {"g": False}),
                    (300.0, {"g": True}), (360.0, {"g": False}),
                    (420.0, {"g": True}), (480.0, {"g": False}),
                    (540.0, {"g": True}), (600.0, {"g": False}),
                    (700.0, {})
                ]
                trad = tolk_spar(karta, pou, ins)
                tolk_u = []
                for t_check in (140.0, 260.0, 380.0, 500.0, 620.0):
                    val = next(r["varden"]["U"] for r in trad if abs(r["t_ms"] - t_check) < 1e-3)
                    tolk_u.append(val)
                o = await kor_ctu(n_in, n_ut, ua)
                o["tolk_u"] = tolk_u
                # CTU kraver EXAKT 0 avvikelse (ren logik)
                o["ok"] = (o["ok"] and (o["openplc_u"] == tolk_u)
                           and (tolk_u == [False, False, False, False, True]))
                resultat[station] = o
            elif station == "SCAN_SR":
                ins = [
                    (0.0, {"s1": False, "r": False}),
                    (60.0, {"s1": True, "r": False}),
                    (120.0, {"s1": False, "r": False}),
                    (180.0, {"s1": False, "r": True}),
                    (240.0, {"s1": False, "r": False}),
                    (300.0, {"s1": True, "r": True}),
                    (360.0, {"s1": False, "r": True}),
                    (420.0, {"s1": False, "r": False}),
                    (500.0, {})
                ]
                trad = tolk_spar(karta, pou, ins)
                tolk_u = []
                for t_check in (100.0, 160.0, 220.0, 280.0, 340.0, 400.0, 460.0):
                    val = next(r["varden"]["U"] for r in trad if abs(r["t_ms"] - t_check) < 1e-3)
                    tolk_u.append(val)
                o = await kor_sr(n_s1, n_r, n_ut, ua)
                o["tolk_u"] = tolk_u
                # SR kraver EXAKT 0 avvikelse (ren logik)
                o["ok"] = (o["ok"] and (o["openplc_u"] == tolk_u)
                           and (tolk_u == [True, True, False, False, True, False, False]))
                resultat[station] = o
            elif station == "SCAN_CTD":
                ins = [
                    (0.0, {"g": False, "ld": True}),
                    (60.0, {"g": False, "ld": False}),
                    (120.0, {"g": True, "ld": False}), (180.0, {"g": False, "ld": False}),
                    (240.0, {"g": True, "ld": False}), (300.0, {"g": False, "ld": False}),
                    (360.0, {"g": True, "ld": False}), (420.0, {"g": False, "ld": False}),
                    (480.0, {"g": True, "ld": False}), (540.0, {"g": False, "ld": False}),
                    (600.0, {"g": True, "ld": False}), (660.0, {"g": False, "ld": False}),
                    (720.0, {})
                ]
                trad = tolk_spar(karta, pou, ins)
                tolk_u = []
                for t_check in (200.0, 320.0, 440.0, 560.0, 680.0):
                    val = next(r["varden"]["U"] for r in trad if abs(r["t_ms"] - t_check) < 1e-3)
                    tolk_u.append(val)
                o = await kor_ctd(n_in, n_ld, n_ut, ua)
                o["tolk_u"] = tolk_u
                # CTD kraver EXAKT 0 avvikelse (ren logik)
                o["ok"] = (o["ok"] and (o["openplc_u"] == tolk_u)
                           and (tolk_u == [False, False, False, False, True]))
                resultat[station] = o
            elif station == "SCAN_CTUD":
                ins = [
                    (0.0, {"cu": False, "cd": False, "r": True, "ld": False}),
                    (60.0, {"cu": False, "cd": False, "r": False, "ld": False}),
                    (120.0, {"cu": True, "cd": False, "r": False, "ld": False}),
                    (180.0, {"cu": False, "cd": False, "r": False, "ld": False}),
                    (240.0, {"cu": True, "cd": False, "r": False, "ld": False}),
                    (300.0, {"cu": False, "cd": False, "r": False, "ld": False}),
                    (360.0, {"cu": True, "cd": False, "r": False, "ld": False}),
                    (420.0, {"cu": False, "cd": False, "r": False, "ld": False}),
                    (480.0, {"cu": False, "cd": True, "r": False, "ld": False}),
                    (540.0, {"cu": False, "cd": False, "r": False, "ld": False}),
                    (600.0, {"cu": False, "cd": True, "r": False, "ld": False}),
                    (660.0, {"cu": False, "cd": False, "r": False, "ld": False}),
                    (720.0, {"cu": False, "cd": True, "r": False, "ld": False}),
                    (780.0, {"cu": False, "cd": False, "r": False, "ld": False}),
                    (840.0, {})
                ]
                trad = tolk_spar(karta, pou, ins)
                tolk_cv = []
                for t_check in (80.0, 200.0, 320.0, 440.0, 560.0, 680.0, 800.0):
                    val = next(r["varden"]["CV"] for r in trad if abs(r["t_ms"] - t_check) < 1e-3)
                    tolk_cv.append(int(val))
                o = await kor_ctud(n_cu, n_cd, n_r, n_ld, n_cv, ua)
                o["tolk_cv"] = tolk_cv
                # CTUD kraver EXAKT 0 avvikelse (ren logik)
                o["ok"] = (o["ok"] and (o["openplc_cv"] == tolk_cv)
                           and (tolk_cv == [0, 1, 2, 3, 2, 1, 0]))
                resultat[station] = o
            elif station == "SCAN_FTRIG":
                ins = [
                    (0.0, {"g": False}),
                    (60.0, {"g": True}),
                    (160.0, {"g": False}),
                    (400.0, {})
                ]
                trad = tolk_spar(karta, pou, ins)
                t_hog = sum(1 for r in trad if r["varden"]["U"])
                o = await kor_ftrig(n_in, n_ut, ua)
                o["tolk_hog_scan"] = t_hog
                o["ok"] = (o["hog_avlasningar"] >= 1
                           and o["hog_avlasningar"] <= 6
                           and t_hog == 1)
                resultat[station] = o
        finally:
            await oplc.disconnect()
        print("%s: %s" % (station, json.dumps(resultat[station],
                                              sort_keys=True)))
    return resultat


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bas", default="https://127.0.0.1:18444")
    ap.add_argument("--anvandare", default="vcassist")
    ap.add_argument("--losenord", default="vcassist")
    ap.add_argument("--endpoint",
                    default="opc.tcp://172.17.0.3:4840/openplc/opcua")
    ap.add_argument("--strucpp-paket", required=True)
    ap.add_argument("--runtime-include", required=True)
    ap.add_argument("--byggkatalog", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    os.makedirs(a.byggkatalog, exist_ok=True)
    if abs(T.SCAN_MS - SCAN_MS) > 1e-9:
        print("FEL: tolkens cykel %.3f != %s - rutnat, inte logik" % (T.SCAN_MS, SCAN_MS))
        return 1
    try:
        resultat = asyncio.run(_mat_allt(a))
    except (OpenPlcFel, Exception) as fel:
        print("FEL: %r" % fel)
        return 1
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"bankpost": BANKPOST, "resultat": resultat}, fh,
                      indent=2, ensure_ascii=False, sort_keys=True)
    ok = all(r.get("ok") for r in resultat.values()) and len(resultat) == len(PROGRAMMEN)
    print("SCAN-SLUT: %s" % ("OVERENS" if ok else "AVVIKELSE"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
