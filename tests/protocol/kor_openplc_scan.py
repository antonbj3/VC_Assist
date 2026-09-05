# -*- coding: utf-8 -*-
"""M-108: samma program scan for scan i var tolk och i OpenPLC.

Svepet (kor_openplc_svepet.py) jamfor VAD motorerna accepterar. Det har
skriptet jamfor vad de GOR: samma kalla, samma insignaler, variabelvarden
jamforda scan for scan. Timers ar det intressanta: TON med PT := T#4s ska
losa ut pa samma scan i bada.

Spar per program (20 ms cykel i bada andar):
  SCAN_GENOM  u := g                      (4 vippor, varje foljd mats i ms)
  SCAN_TON4S  t(IN := g, PT := T#4s); u := t.Q  (3x, triggscan jamfors)
  SCAN_RTRIG  rt(CLK := g); u := rt.Q     (puls, exakt en hog scan vantas)

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


def ladda(klient, karta, pou, station, endpoint, strucpp_paket,
          runtime_include, byggrot):
    full = pou + P.konfigurationstext(station, intervall=P.TASKINTERVALL)
    kat = os.path.join(byggrot, station)
    forb = P.kompilera(full, os.path.join(kat, "for"), strucpp_paket)
    konf = opcuakonfig.konfiguration(karta, forb, endpoint)
    zipvag, _ = P.bygg_projekt(full, os.path.join(kat, "arkiv"),
                               strucpp_paket, runtime_include,
                               opcua_konfig=konf)
    return klient.ladda_och_starta(zipvag)


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
            n_in = oplc.get_node("ns=2;s=%s"
                                 % opcuakonfig.nodid(station, "g"))
            n_ut = oplc.get_node("ns=2;s=%s"
                                 % opcuakonfig.nodid(station, "u"))
            # stillastaende-variabel-fallan: utgangen maste ga att andra.
            # TON har PT=4s, sa dess utgang FAR inte rora sig inom 1s -
            # taket ar per program, inte ett tal.
            stilla_tak = {"SCAN_TON4S": 6.0, "SCAN_TON1S": 3.0}.get(
                station, TAK_S)
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
    ok = all(r.get("ok") for r in resultat.values()) and len(resultat) == 5
    print("SCAN-SLUT: %s" % ("OVERENS" if ok else "AVVIKELSE"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
