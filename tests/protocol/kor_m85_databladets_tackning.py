#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-85: vad component.rsc FAKTISKT bar, raknat over hela biblioteket.

Mater tackningen falt for falt, en siffra per falt, over alla .vcmx i det
installerade biblioteket. Fragan ar inte "gick det att lasa" utan "hur manga
av 3201 bar egenskapsnamn, hur manga bar en storhet, hur manga bar ett
standardvarde" - ett datablad vars tackning ingen matt ar ett formular, inte
ett datablad.

Tungt steg (3201 filer, narmare en gigabyte text). Kors med
    nice -n 19 ionice -c3 python3 tests/protocol/kor_m85_databladets_tackning.py
och fyra processer, sa att operatorens skrivbord inte kanner av det.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "component.rsc bar egenskapsnamn, storhet och standardvarde i en matt "
        "andel av bibliotekets 3201 komponenter, raknat falt for falt over "
        "hela biblioteket.",
    "under_prov": (
        "svc/vc_assist_svc/komponentdatablad.py",
        "svc/vc_assist_svc/katalogindex.py",
    ),
    "facit":
        "hur manga av de 3201 databladen som bar egenskapsnamn, kvantitet, "
        "standardvarde och redigerbarhet, hur manga beteenden som har en kand "
        "VC_-konstant, och hur manga som har exakt en boolsk signal",
    "facitkalla":
        "FACIT UR KODEN SOM DOMS. Biblioteket ar externt, men varje tal lases "
        "ut ur det av komponentdatablad.py sjalv - samma modul som doms. Ett "
        "falt parsern missar rapporteras som ett falt filen inte bar, och "
        "ingen oberoende lasare av samma component.rsc finns i korningen.",
    "facitkalla_filer": ("svc/vc_assist_svc/komponentdatablad.py",),
    "trasiga_fall": (
        "ett datablad som inte gar att lasa maste hamna i OLASBARA med sitt "
        "fel, aldrig raknas som tackt",
        "en komponent med noll boolska signaler maste redovisas for sig - [0] "
        "kastar IndexError",
        "en komponent med fler an en boolsk signal far inte raknas som "
        "entydig",
    ),
    "kraver": ("vc",),
    "matningar": ("M-85",),
}

import json
import multiprocessing
import os
import sys
import time
from collections import Counter

HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(HAR, "..", ".."))
sys.path.insert(0, os.path.join(ROT, "svc"))

from vc_assist_svc import katalogindex, komponentdatablad as KD   # noqa: E402

# Namnen M-84 lamnade oppna, ordagrant ur dess sista avsnitt.
M84_NAMN = ("ConveyorSpeed", "StrokeTime", "MaxPayload")


def _en(argument):
    """Ett datablad -> ett matt. Kors i en underprocess."""
    sokvag, tillverkare = argument
    try:
        blad = KD.las(sokvag, tillverkare=tillverkare)
    except Exception as fel:                      # noqa: BLE001
        return {"fel": "%s: %s" % (type(fel).__name__, fel), "sokvag": sokvag}
    e = blad.egenskaper
    boolska = blad.signaler_av_typ("rSimBoolSignal")
    namn_lower = {x.namn.lower() for x in e}
    return {
        "fel": None,
        "sokvag": sokvag,
        "namn": blad.namn,
        "egenskaper": len(e),
        "med_varde": sum(1 for x in e if x.varde is not None),
        "med_kvantitet": sum(1 for x in e if x.kvantitet),
        "med_steg": sum(1 for x in e if x.steg),
        "med_redigerbarhet": sum(1 for x in e if x.skrivbar is not None),
        "beteenden": len(blad.beteenden),
        "beteenden_med_api": sum(1 for b in blad.beteenden if b.api_typ),
        "granssnitt": len(blad.granssnitt),
        "leder": len(blad.leder),
        "signaler": len(blad.signaler()),
        "boolska": len(boolska),
        "kvantiteter": sorted({x.kvantitet for x in e if x.kvantitet}),
        "beteendetyper": sorted({b.typ for b in blad.beteenden}),
        "beteendetyper_utan_api": sorted({b.typ for b in blad.beteenden
                                          if not b.api_typ}),
        "egenskapsnamn": sorted(namn_lower),
        "m84": {n: (n.lower() in namn_lower) for n in M84_NAMN},
        "nyttolast": blad.nyttolast_kg,
        "rackvidd": blad.rackvidd_mm,
        "beskrivning": len(blad.katalogbeskrivning),
        "nyckelrubrik": "### Key" in blad.katalogbeskrivning,
        "olasta": list(blad.olasta),
        "tecken": len(KD.text(blad)),
    }


def _percentil(varden, p):
    if not varden:
        return 0
    v = sorted(varden)
    i = min(len(v) - 1, max(0, int(round((p / 100.0) * (len(v) - 1)))))
    return v[i]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ut_fil = argv[0] if argv else None

    fynd = katalogindex.hitta()
    if not fynd:
        print("hittade inget installerat bibliotek. Provade:")
        for sokvag, hur in katalogindex.kandidatrotter():
            print("  %-60s %s" % (sokvag, hur))
        return 1
    rot = fynd[0].rot
    print("bibliotek: %s\n  hittat via: %s" % (rot, fynd[0].hur))

    jobb = []
    for katalog, _k, filer in os.walk(rot):
        rel = os.path.relpath(katalog, rot)
        delar = [d for d in rel.split(os.sep) if d not in (".", "")]
        tillverkare = delar[0] if delar else ""
        for f in sorted(filer):
            if f.lower().endswith((".vcmx", ".vcm")):
                jobb.append((os.path.join(katalog, f), tillverkare))
    print("%d komponentfiler" % len(jobb))

    t0 = time.time()
    with multiprocessing.Pool(4) as pool:
        matt = pool.map(_en, jobb, chunksize=16)
    sekunder = time.time() - t0

    trasiga = [m for m in matt if m["fel"]]
    ok = [m for m in matt if not m["fel"]]
    n = len(matt)

    def andel(k):
        return "%d/%d (%.1f %%)" % (k, n, 100.0 * k / n if n else 0.0)

    print("\n=== TACKNING, ett tal per falt (av %d komponentfiler) ===" % n)
    print("lasbara datablad                 %s  (%.1f s, 4 processer)"
          % (andel(len(ok)), sekunder))
    print("bar minst en EGEN egenskap       %s"
          % andel(sum(1 for m in ok if m["egenskaper"])))
    print("bar minst ett beteende           %s"
          % andel(sum(1 for m in ok if m["beteenden"])))
    print("bar minst ett granssnitt         %s"
          % andel(sum(1 for m in ok if m["granssnitt"])))
    print("bar minst en signal              %s"
          % andel(sum(1 for m in ok if m["signaler"])))
    print("bar minst en led                 %s"
          % andel(sum(1 for m in ok if m["leder"])))
    print("bar tillverkarbeskrivning        %s"
          % andel(sum(1 for m in ok if m["beskrivning"])))
    print("  darav med '### Key'-rubrik     %s"
          % andel(sum(1 for m in ok if m["nyckelrubrik"])))
    print("MaxPayload deklarerad (ej None)  %s"
          % andel(sum(1 for m in ok if m["nyttolast"] is not None)))
    print("  darav skild fran noll          %s"
          % andel(sum(1 for m in ok if m["nyttolast"])))
    print("Reach deklarerad (ej None)       %s"
          % andel(sum(1 for m in ok if m["rackvidd"] is not None)))
    print("  darav skild fran noll          %s"
          % andel(sum(1 for m in ok if m["rackvidd"])))

    tot_e = sum(m["egenskaper"] for m in ok)
    print("\n=== EGENSKAPSFALTEN, raknat per EGENSKAP (%d st totalt) ===" % tot_e)
    for etikett, nyckel in (("standardvarde", "med_varde"),
                            ("storhet (Quantity)", "med_kvantitet"),
                            ("tillatna varden (StepList)", "med_steg"),
                            ("redigerbarhet i Settings", "med_redigerbarhet")):
        k = sum(m[nyckel] for m in ok)
        print("  bar %-28s %d/%d (%.1f %%)"
              % (etikett, k, tot_e, 100.0 * k / tot_e if tot_e else 0.0))

    tot_b = sum(m["beteenden"] for m in ok)
    tot_ba = sum(m["beteenden_med_api"] for m in ok)
    print("\n=== BETEENDENA ===")
    print("  beteendeforekomster            %d" % tot_b)
    print("  med kand VC_-konstant          %d/%d (%.1f %%)"
          % (tot_ba, tot_b, 100.0 * tot_ba / tot_b if tot_b else 0.0))
    typer = Counter()
    utan = Counter()
    for m in ok:
        for x in m["beteendetyper"]:
            typer[x] += 1
        for x in m["beteendetyper_utan_api"]:
            utan[x] += 1
    print("  distinkta beteendetyper        %d, varav %d utan avbildning"
          % (len(typer), len(utan)))
    print("  de tio vanligaste UTAN avbildning (komponenter som bar dem):")
    for namn, k in utan.most_common(10):
        print("    %-34s %5d" % (namn, k))

    print("\n=== SIGNALERNA: ar [0] entydigt? ===")
    fordelning = Counter(m["boolska"] for m in ok)
    ingen = fordelning[0]
    en = fordelning[1]
    flera = sum(k for b, k in fordelning.items() if b > 1)
    print("  0 boolska signaler             %s  ([0] kastar IndexError)"
          % andel(ingen))
    print("  exakt 1 boolsk signal          %s  ([0] ar ENTYDIGT, namnet vet vi)"
          % andel(en))
    print("  fler an 1                      %s  ([0] beror pa ordning vi inte matt)"
          % andel(flera))

    kvant = Counter()
    for m in ok:
        for k in m["kvantiteter"]:
            kvant[k] += 1
    print("\n=== STORHETER som kallan sjalv deklarerar (%d distinkta) ===" % len(kvant))
    for namn, k in kvant.most_common(15):
        print("  %-24s %5d komponenter" % (namn, k))

    print("\n=== M-84:s namngivna namn, sokta som EGENSKAP ===")
    for namn in M84_NAMN:
        k = sum(1 for m in ok if m["m84"][namn])
        print("  %-16s finns som egenskap i %s" % (namn, andel(k)))

    print("\n=== FORDELNINGAR (satter taken i komponentdatablad.py) ===")
    for etikett, nyckel in (("egenskaper", "egenskaper"),
                            ("beteenden", "beteenden"),
                            ("granssnitt", "granssnitt"),
                            ("leder", "leder"),
                            ("beskrivningens tecken", "beskrivning"),
                            ("hela databladets tecken", "tecken")):
        v = [m[nyckel] for m in ok]
        print("  %-24s median %6d  p90 %6d  p99 %6d  max %7d"
              % (etikett, _percentil(v, 50), _percentil(v, 90),
                 _percentil(v, 99), max(v) if v else 0))

    if trasiga:
        print("\n=== OLASBARA (%d) ===" % len(trasiga))
        for m in trasiga[:15]:
            print("  %s\n    %s" % (m["sokvag"], m["fel"]))

    if ut_fil:
        with open(ut_fil, "w", encoding="utf-8") as f:
            json.dump({"antal": n, "sekunder": sekunder, "matt": matt}, f)
        print("\nskrivet: %s" % ut_fil)
    return 0


if __name__ == "__main__":
    sys.exit(main())
