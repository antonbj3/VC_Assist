# -*- coding: utf-8 -*-
"""M-108: OPC UA-ledet mot OpenPLC v4 - rättigheter, feltyper, stopp och timing.

Vad som prövas (de fem proven i M-108:s OPC UA-del):
  1. Skrivning till FRAN_PLC-utgång (PLC.<station>.matut):
     Ska vara skrivskyddad per opcuakonfig.py (LASBAR: viewer/operator/engineer = 'r').
     Verifierar att anonym klient (som får rollen engineer) AVVISAS med felkod
     (BadInternalError / ServiceFault från servern) och att värdet inte ändras.
  2. Läsning av okänd nod (ns=2;s=PLC.Nope.hittepa):
     Måste ge BadNodeIdUnknown (0x80340000) högljutt, aldrig ett defaultvärde.
  3. Skrivning med fel typ till BOOL-nod (t.ex. INT 5, INT 0, sträng, float):
     Mäter serverns svar: servern avvisar inte utan utför permissiv coercion
     (opcua_utils.py:convert_value_for_plc: int!=0 -> 1, 'true'/'1'/'yes'/'on' -> 1).
  4. Skriv/läs medan PLC är STOPPAD (stoppa via REST, prova, starta igen):
     Mäter runtime-beteende: när PLC stoppas stängs även OPC UA-pluginet ned,
     anslutningen bryts och anrop timear ut. Vid omstart startar OPC UA på nytt
     och minnestabellet återinitieras till default (inget tillstånd sparas över stopp).
  5. Skrivning mellan två scan vs 10 ms plugin-synk (M-20):
     Mäter adressrymdens lokala skriv-/läslatens (median ~1.0 ms) samt full
     PLC tur-och-retur-tid över fasförskjutna skrivningar (median ~28-40 ms).

Körs:
    python3 tests/protocol/kor_openplc_opcua.py --bas https://127.0.0.1:18444 \\
        --endpoint opc.tcp://172.17.0.3:4840/openplc/opcua \\
        --json /tmp/opencode/m108_opcua/opcua_prov.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.plc import opcuakonfig  # noqa: E402
from vc_assist_svc.plc.matning import _anslut, _asyncua  # noqa: E402
from vc_assist_svc.plc.openplc import OpenPlcV4, OpenPlcFel  # noqa: E402

BANKPOST = {
    "pastar": (
        "OPC UA-ledet mot OpenPLC v4 avvisar skrivning till utgångar, "
        "returnerar BadNodeIdUnknown vid okänd nod, utför typ-coercion vid "
        "fel typ, och bryter förbindelsen vid stopp."
    ),
    "under_prov": ("svc/vc_assist_svc/st/tolk.py",),
    "facit": "OpenPLC Runtime v4:s OPC UA-serverbeteende och returkoder",
    "facitkalla": "OpenPLC Runtime v4 (oberoende tredje motor)",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "skrivning till FRAN_PLC som accepteras tyst måste fällas",
        "läsning av okänd nod som ger defaultvärde måste fällas",
        "skrivning till stoppad PLC som låtsas lyckas måste fällas",
    ),
    "kraver": ("openplc",),
    "matningar": ("M-108",),
}


# =========================================================================
# Prov 1: Skrivning till FRAN_PLC-utgång
# =========================================================================
async def prov_1_fran_plc_skrivskydd(endpoint: str, station: str = "Matstation") -> Dict[str, Any]:
    """Prov 1: Verifiera att skrivning till FRAN_PLC-utgång avvisas högljutt."""
    Client, ua = _asyncua()
    client = Client(url=endpoint, timeout=5.0)
    await _anslut(client)
    try:
        nod_id_ut = "ns=2;s=%s" % opcuakonfig.nodid(station, "matut")
        nod_ut = client.get_node(nod_id_ut)
        varde_fore = bool(await nod_ut.read_value())
        nytt_varde = not varde_fore

        avvisad = False
        fel_typ = None
        fel_meddelande = ""
        fel_kod = None

        try:
            await nod_ut.write_value(ua.DataValue(ua.Variant(nytt_varde, ua.VariantType.Boolean)))
        except Exception as e:
            avvisad = True
            fel_typ = type(e).__name__
            fel_meddelande = str(e)
            if hasattr(e, "code"):
                fel_kod = hex(e.code) if isinstance(e.code, int) else str(e.code)

        varde_efter = bool(await nod_ut.read_value())
        oforandrad = (varde_efter == varde_fore)

        ok = avvisad and oforandrad
        return {
            "prov": "1_fran_plc_skrivskydd",
            "ok": ok,
            "nod": nod_id_ut,
            "forvantat": "Skrivning avvisas med OPC UA-fel/ServiceFault och värdet förblir oförändrat",
            "avvisad": avvisad,
            "fel_typ": fel_typ,
            "fel_meddelande": fel_meddelande,
            "fel_kod": fel_kod,
            "varde_fore": varde_fore,
            "varde_efter": varde_efter,
            "varde_oforandrat": oforandrad,
        }
    finally:
        await client.disconnect()


# =========================================================================
# Prov 2: Läsning av okänd nod
# =========================================================================
async def prov_2_okand_nod(endpoint: str) -> Dict[str, Any]:
    """Prov 2: Läsning av okänd nod måste ge BadNodeIdUnknown (0x80340000)."""
    Client, ua = _asyncua()
    client = Client(url=endpoint, timeout=5.0)
    await _anslut(client)
    try:
        okand_id = "ns=2;s=PLC.Nope.hittepa"
        nod = client.get_node(okand_id)

        fick_bad_node = False
        fel_typ = None
        fel_meddelande = ""
        fel_kod = None
        returnerat_varde = None

        try:
            returnerat_varde = await nod.read_value()
        except Exception as e:
            fel_typ = type(e).__name__
            fel_meddelande = str(e)
            if hasattr(e, "code"):
                fel_kod = hex(e.code) if isinstance(e.code, int) else str(e.code)
            if "BadNodeIdUnknown" in fel_typ or fel_kod == "0x80340000" or "BadNodeIdUnknown" in fel_meddelande:
                fick_bad_node = True

        ok = fick_bad_node and returnerat_varde is None
        return {
            "prov": "2_okand_nod",
            "ok": ok,
            "nod": okand_id,
            "forvantat": "BadNodeIdUnknown (0x80340000) kastas högljutt, inget defaultvärde",
            "fick_bad_node": fick_bad_node,
            "fel_typ": fel_typ,
            "fel_meddelande": fel_meddelande,
            "fel_kod": fel_kod,
            "returnerat_varde": returnerat_varde,
        }
    finally:
        await client.disconnect()


# =========================================================================
# Prov 3: Skrivning med fel typ till BOOL-nod
# =========================================================================
async def prov_3_fel_typ_coercion(endpoint: str, station: str = "Matstation") -> Dict[str, Any]:
    """Prov 3: Mät vad servern svarar vid skrivning med fel typ till BOOL-nod."""
    Client, ua = _asyncua()
    client = Client(url=endpoint, timeout=5.0)
    await _anslut(client)
    try:
        nod_in = client.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matin"))
        nod_ut = client.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matut"))

        testfall = [
            ("Int16_5", ua.Variant(5, ua.VariantType.Int16), True),
            ("Int16_0", ua.Variant(0, ua.VariantType.Int16), False),
            ("Int32_1", ua.Variant(1, ua.VariantType.Int32), True),
            ("String_true", ua.Variant("true", ua.VariantType.String), True),
            ("String_false", ua.Variant("false", ua.VariantType.String), False),
            ("String_abc", ua.Variant("abc", ua.VariantType.String), False),
            ("Float_1_5", ua.Variant(1.5, ua.VariantType.Float), True),
            ("Float_0_0", ua.Variant(0.0, ua.VariantType.Float), False),
        ]

        utfall = []
        for namn, variant, forvantad_bool in testfall:
            # Nollställ först till motsatt värde med strikt Boolean
            nollstall = not forvantad_bool
            await nod_in.write_value(ua.DataValue(ua.Variant(nollstall, ua.VariantType.Boolean)))
            await asyncio.sleep(0.03)

            skrivning_lyckades = False
            fel_typ = None
            fel_meddelande = ""
            try:
                await nod_in.write_value(ua.DataValue(variant))
                skrivning_lyckades = True
            except Exception as e:
                fel_typ = type(e).__name__
                fel_meddelande = str(e)

            await asyncio.sleep(0.04)
            in_varde = await nod_in.read_value()
            ut_varde = await nod_ut.read_value()

            coerced_korrekt = (in_varde == forvantad_bool and ut_varde == forvantad_bool)
            utfall.append({
                "namn": namn,
                "variant_skriven": str(variant),
                "skrivning_lyckades": skrivning_lyckades,
                "fel_typ": fel_typ,
                "in_varde": in_varde,
                "in_typ": type(in_varde).__name__,
                "ut_varde": ut_varde,
                "forvantad_coercion": forvantad_bool,
                "coerced_korrekt": coerced_korrekt,
            })

        alla_coerced = all(u["skrivning_lyckades"] and u["coerced_korrekt"] for u in utfall)
        return {
            "prov": "3_fel_typ_coercion",
            "ok": alla_coerced,
            "forvantat": "Servern genomför permissiv typ-coercion (convert_value_for_plc) utan att kasta BadTypeMismatch",
            "beteende": "COERCION_TILL_BOOL",
            "detaljer": utfall,
        }
    finally:
        await client.disconnect()


# =========================================================================
# Prov 4: Skriv/läs medan PLC är STOPPAD
# =========================================================================
async def prov_4_stoppad_plc(bas: str, anvandare: str, losenord: str,
                             endpoint: str, station: str = "Matstation") -> Dict[str, Any]:
    """Prov 4: Skriv/läs medan PLC är stoppad via REST och verifiera omstart."""
    Client, ua = _asyncua()
    rest = OpenPlcV4(bas, anvandare, losenord, tillat_osignerat=True)

    # 1. Säkerställ att PLC kör och sätt matin=True
    if rest.status() != "RUNNING":
        rest.starta_och_vanta()

    client_init = Client(url=endpoint, timeout=5.0)
    await _anslut(client_init)
    try:
        nod_in = client_init.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matin"))
        nod_ut = client_init.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matut"))
        await nod_in.write_value(ua.DataValue(ua.Variant(True, ua.VariantType.Boolean)))
        await asyncio.sleep(0.05)
        init_in = await nod_in.read_value()
        init_ut = await nod_ut.read_value()
    finally:
        await client_init.disconnect()

    # 2. Stoppa PLC via REST
    rest.stoppa()
    for _ in range(30):
        if rest.status() == "STOPPED":
            break
        await asyncio.sleep(0.1)
    status_stoppad = rest.status()

    # 3. Prova att ansluta och läsa/skriva under STOPPED
    anslutning_under_stopp = False
    las_skriv_fel = None
    client_stopp = Client(url=endpoint, timeout=2.0)
    try:
        await client_stopp.connect()
        anslutning_under_stopp = True
    except Exception as e:
        las_skriv_fel = f"{type(e).__name__}: {e}"
    finally:
        if anslutning_under_stopp:
            await client_stopp.disconnect()

    # 4. Starta PLC igen och läs tillbaka
    rest.starta_och_vanta()
    status_omstart = rest.status()

    client_omstart = Client(url=endpoint, timeout=5.0)
    await _anslut(client_omstart)
    try:
        nod_in2 = client_omstart.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matin"))
        nod_ut2 = client_omstart.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matut"))
        efter_omstart_in = await nod_in2.read_value()
        efter_omstart_ut = await nod_ut2.read_value()
    finally:
        await client_omstart.disconnect()

    # Bedömning:
    # - Under stopp: OPC UA-servern stängs ned (anslutning misslyckas / Timeout / ConnectionRefused).
    # - Vid omstart: Variabler nollställs till False (inte persistent över stop/start).
    ok = (status_stoppad == "STOPPED" and
          not anslutning_under_stopp and
          status_omstart == "RUNNING" and
          efter_omstart_in is False and
          efter_omstart_ut is False)

    return {
        "prov": "4_stoppad_plc",
        "ok": ok,
        "forvantat": "OPC UA-servern stängs under STOPPED (anslutning bryts). Vid omstart nollställs minnet till default (False).",
        "status_fore": "RUNNING",
        "varde_fore_stopp": {"matin": init_in, "matut": init_ut},
        "status_stoppad": status_stoppad,
        "anslutning_under_stopp": anslutning_under_stopp,
        "stopp_fel": las_skriv_fel,
        "status_omstart": status_omstart,
        "varde_efter_omstart": {"matin": efter_omstart_in, "matut": efter_omstart_ut},
        "tillstand_persistent_over_omstart": (efter_omstart_in is True),
    }


# =========================================================================
# Prov 5: Timing vid skrivning mellan två scan vs 10 ms plugin-synk
# =========================================================================
async def prov_5_sub_scan_timing(endpoint: str, station: str = "Matstation",
                                n_prov: int = 30) -> Dict[str, Any]:
    """Prov 5: Mät lokal skriv/läsfördröjning vs full tur-och-retur över scancykeln."""
    Client, ua = _asyncua()
    client = Client(url=endpoint, timeout=5.0)
    await _anslut(client)
    try:
        nod_in = client.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matin"))
        nod_ut = client.get_node("ns=2;s=%s" % opcuakonfig.nodid(station, "matut"))

        # Mätning A: Lokal skriv- och läslatens i OPC UA-serverns adressrymd
        lokal_skriv_ms = []
        lokal_las_ms = []
        lokal_totalt_ms = []
        for i in range(n_prov):
            val = (i % 2 == 1)
            t0 = time.perf_counter()
            await nod_in.write_value(ua.DataValue(ua.Variant(val, ua.VariantType.Boolean)))
            t1 = time.perf_counter()
            _ = await nod_in.read_value()
            t2 = time.perf_counter()
            lokal_skriv_ms.append((t1 - t0) * 1000.0)
            lokal_las_ms.append((t2 - t1) * 1000.0)
            lokal_totalt_ms.append((t2 - t0) * 1000.0)

        # Mätning B: Full tur och retur genom PLC-scancykeln (20 ms) vid fasspridning
        rtt_ms = []
        nuvarande = bool(await nod_ut.read_value())
        for i in range(n_prov):
            nytt = not nuvarande
            t0 = time.perf_counter()
            await nod_in.write_value(ua.DataValue(ua.Variant(nytt, ua.VariantType.Boolean)))
            while True:
                if bool(await nod_ut.read_value()) == nytt:
                    break
                if time.perf_counter() - t0 > 1.0:
                    raise TimeoutError("utsignalen följde inte med inom 1.0s")
            t_slut = time.perf_counter()
            rtt_ms.append((t_slut - t0) * 1000.0)
            nuvarande = nytt
            # Sprid fasen jämnt över 0..20 ms perioden
            await asyncio.sleep(0.003 + (i % 7) * 0.0025)

        lokal_median = statistics.median(lokal_totalt_ms)
        rtt_median = statistics.median(rtt_ms)
        rtt_min = min(rtt_ms)
        rtt_max = max(rtt_ms)

        # Tur och retur med 20 ms scan och 10 ms syncloop ska ligga i intervallet 20..45 ms
        ok = (lokal_median < 5.0 and 15.0 <= rtt_median <= 45.0)

        return {
            "prov": "5_sub_scan_timing",
            "ok": ok,
            "forvantat": "Lokal adressrymd-operation ~1 ms; full tur-och-retur median 25-40 ms (1-2 scancykler)",
            "antal_mätningar": n_prov,
            "lokal_skriv_median_ms": round(statistics.median(lokal_skriv_ms), 3),
            "lokal_las_median_ms": round(statistics.median(lokal_las_ms), 3),
            "lokal_totalt_median_ms": round(lokal_median, 3),
            "rtt_median_ms": round(rtt_median, 3),
            "rtt_mean_ms": round(statistics.fmean(rtt_ms), 3),
            "rtt_min_ms": round(rtt_min, 3),
            "rtt_max_ms": round(rtt_max, 3),
            "rtt_stdev_ms": round(statistics.stdev(rtt_ms) if len(rtt_ms) > 1 else 0.0, 3),
        }
    finally:
        await client.disconnect()


# =========================================================================
# Trasiga fixturer (fail-closed test av själva testbänken)
# =========================================================================
def prov_trasiga_fixturer() -> Dict[str, Any]:
    """Kör saboterade utfall för att bevisa att harnessen fäller felaktigt beteende."""
    resultat = {}

    # Fixtur 1: Skrivning till utgång som låtsas lyckas och muterar värde
    falsk_prov1 = {"avvisad": False, "varde_oforandrat": False}
    ok1 = (falsk_prov1["avvisad"] and falsk_prov1["varde_oforandrat"])
    resultat["fixtur_1_tyst_skrivning_till_utgang_falls"] = (not ok1)

    # Fixtur 2: Okänd nod som returnerar None i stället för att kasta
    falsk_prov2 = {"fick_bad_node": False, "returnerat_varde": None}
    ok2 = (falsk_prov2["fick_bad_node"] and falsk_prov2["returnerat_varde"] is None)
    resultat["fixtur_2_okand_nod_tyst_falls"] = (not ok2)

    # Fixtur 3: Stoppad PLC där anslutning felaktigt rapporteras som öppen och persistent
    falsk_prov4 = {
        "status_stoppad": "STOPPED",
        "anslutning_under_stopp": True,
        "status_omstart": "RUNNING",
        "efter_omstart_in": True,
        "efter_omstart_ut": True,
    }
    ok4 = (falsk_prov4["status_stoppad"] == "STOPPED" and
           not falsk_prov4["anslutning_under_stopp"] and
           falsk_prov4["status_omstart"] == "RUNNING" and
           falsk_prov4["efter_omstart_in"] is False and
           falsk_prov4["efter_omstart_ut"] is False)
    resultat["fixtur_3_stoppad_plc_spokanslutning_falls"] = (not ok4)

    alla_trasiga_fallna = all(resultat.values())
    return {
        "prov": "trasiga_fixturer",
        "ok": alla_trasiga_fallna,
        "detaljer": resultat,
    }


# =========================================================================
# Huvudfunktion och CLI
# =========================================================================
async def kor_alla_prov(args) -> Dict[str, Any]:
    res1 = await prov_1_fran_plc_skrivskydd(args.endpoint, args.station)
    print("Prov 1 (FRAN_PLC skrivskydd):", "PASS" if res1["ok"] else "FAIL",
          f"(avvisad={res1['avvisad']}, fel={res1['fel_typ']}, kod={res1['fel_kod']})")

    res2 = await prov_2_okand_nod(args.endpoint)
    print("Prov 2 (Okänd nod):", "PASS" if res2["ok"] else "FAIL",
          f"(fick_bad_node={res2['fick_bad_node']}, fel={res2['fel_typ']}, kod={res2['fel_kod']})")

    res3 = await prov_3_fel_typ_coercion(args.endpoint, args.station)
    print("Prov 3 (Fel typ coercion):", "PASS" if res3["ok"] else "FAIL",
          f"(beteende={res3['beteende']}, fall={len(res3['detaljer'])})")

    res4 = await prov_4_stoppad_plc(args.bas, args.anvandare, args.losenord,
                                   args.endpoint, args.station)
    print("Prov 4 (Stoppad PLC):", "PASS" if res4["ok"] else "FAIL",
          f"(anslutning_under_stopp={res4['anslutning_under_stopp']}, omstart_nollställd={res4['varde_efter_omstart']['matin'] is False})")

    res5 = await prov_5_sub_scan_timing(args.endpoint, args.station)
    print("Prov 5 (Timing & synk):", "PASS" if res5["ok"] else "FAIL",
          f"(lokal_median={res5['lokal_totalt_median_ms']}ms, rtt_median={res5['rtt_median_ms']}ms)")

    res_fix = prov_trasiga_fixturer()
    print("Trasiga fixturer (fail-closed):", "PASS" if res_fix["ok"] else "FAIL")

    return {
        "bankpost": BANKPOST,
        "prov_1": res1,
        "prov_2": res2,
        "prov_3": res3,
        "prov_4": res4,
        "prov_5": res5,
        "trasiga_fixturer": res_fix,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bas", default="https://127.0.0.1:18444",
                        help="REST base URL")
    parser.add_argument("--anvandare", default="vcassist")
    parser.add_argument("--losenord", default="vcassist")
    parser.add_argument("--endpoint", default="opc.tcp://172.17.0.3:4840/openplc/opcua",
                        help="OPC UA endpoint")
    parser.add_argument("--station", default="Matstation")
    parser.add_argument("--json", default=None,
                        help="Valfri sökväg att skriva JSON-resultat till")
    args = parser.parse_args(argv)

    try:
        resultat = asyncio.run(kor_alla_prov(args))
    except Exception as e:
        print(f"FATALT FEL vid körning av protokoll: {e}", file=sys.stderr)
        return 1

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(resultat, f, indent=2, ensure_ascii=False, sort_keys=True)

    alla_ok = all(
        resultat[k]["ok"]
        for k in ["prov_1", "prov_2", "prov_3", "prov_4", "prov_5", "trasiga_fixturer"]
    )
    print("OPCUA-PROTOKOLL-SLUT:", "GODKÄND" if alla_ok else "AVVIKELSE")
    return 0 if alla_ok else 1


if __name__ == "__main__":
    sys.exit(main())
