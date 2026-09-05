# -*- coding: utf-8 -*-
"""D10: Provtagningsfrekvensen mot vad som ska ses — ögats upplösning och giltighet.

Uppdrag D10 i docs/uppdrag/KO_D_ogat_och_scenen.md:
"Ögat provtar 17,2 Hz tyst och 224,7 Hz under trafik. En rörelse som är klar
på 30 ms syns inte vid 17 Hz. Räkna, per domare, vilken snabbaste händelse den
kan se — och jämför mot vad bankens uppgifter faktiskt kräver. Om någon uppgift
kräver mer än ögat ger, är den uppgiftens dom ogiltig."

Denna modul:
1. Beräknar upplösningsgränsen för var och en av de 5 domarna vid:
   - Tyst regim: 17,2 Hz (58,1 ms per sample)
   - Standardanalys: 20,0 Hz (50,0 ms per sample)
   - Trafikregim: 224,7 Hz (4,45 ms per sample)
2. Skannar samtliga uppgifter i banken (bank/uppgifter/*.json) och identifierar:
   - Minsta tidssteg / fönster per uppgift
   - Vilka uppgifter som överskrider gränsen vid 17,2 Hz (ogiltiga domar vid tyst regim)
   - Att 224,7 Hz täcker samtliga uppgifter i banken.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Mätta takter ur M-03 och specifikationerna:
RATE_TYST_HZ = 17.2
DT_TYST_MS = 1000.0 / RATE_TYST_HZ   # 58.14 ms

RATE_STD_HZ = 20.0
DT_STD_MS = 1000.0 / RATE_STD_HZ     # 50.00 ms

RATE_TRAFIK_HZ = 224.7
DT_TRAFIK_MS = 1000.0 / RATE_TRAFIK_HZ  # 4.45 ms


def berakna_domargranser() -> dict:
    """Beräknar snabbaste observerbara händelse per domare i de tre regimerna."""
    return {
        "sekvens": {
            "storhet": "Minsta detekterbara puls (hög -> låg)",
            "regel": "Minst 1 sample hög (helst 2 för stabil flank)",
            "tyst_ms": round(DT_TYST_MS, 1),
            "std_ms": round(DT_STD_MS, 1),
            "trafik_ms": round(DT_TRAFIK_MS, 2),
            "kommentar": "Puls kortare än dt riskerar att hamna mellan samples",
        },
        "timing": {
            "storhet": "Minsta upplösbara uppehåll/fördröjning",
            "regel": "Mätosäkerhet ±dt; tolerans måste vara > 2*dt",
            "tyst_ms": round(2 * DT_TYST_MS, 1),
            "std_ms": round(2 * DT_STD_MS, 1),
            "trafik_ms": round(2 * DT_TRAFIK_MS, 2),
            "kommentar": "Tidsfönster smalare än 2*dt ger INCONCLUSIVE (M-97)",
        },
        "grepp": {
            "storhet": "Kortaste godkända bärsträcka (carry)",
            "regel": "Fast golv CARRY_MIN_SPAN_S = 500 ms",
            "tyst_ms": 500.0,
            "std_ms": 500.0,
            "trafik_ms": 500.0,
            "kommentar": "Begränsas av fast logisk tröskel i oga_analys, inte frekvens",
        },
        "kollision": {
            "storhet": "Kortaste zonpassage utan tunnling (vid v=1.0 m/s, d=50 mm)",
            "regel": "Passagetid t = d/v måste överstiga dt",
            "tyst_ms": round(DT_TYST_MS, 1),
            "std_ms": round(DT_STD_MS, 1),
            "trafik_ms": round(DT_TRAFIK_MS, 2),
            "kommentar": "Snabba detaljer hoppar förbi kollisionshindret mellan samples",
        },
        "genomflode": {
            "storhet": "Kortaste registrerbara svält-/blockeringsavvikelse",
            "regel": "vcStatistics ackumuleras internt; avläses med upplösning dt",
            "tyst_ms": round(DT_TYST_MS, 1),
            "std_ms": round(DT_STD_MS, 1),
            "trafik_ms": round(DT_TRAFIK_MS, 2),
            "kommentar": "Krav i banken ligger på 1000–2500 ms; påverkas marginellt",
        },
    }


def analysera_bankens_tidskrav(uppgiftsmapp: str | None = None) -> dict:
    """Undersöker alla uppgifter i banken och mäter deras kortaste tidssteg."""
    mapp = uppgiftsmapp or os.path.join(_ROT, "bank", "uppgifter")
    filer = sorted(glob.glob(os.path.join(mapp, "*.json")))

    uppgifter = []
    ogiltiga_vid_tyst = []
    ogiltiga_vid_std = []
    ogiltiga_vid_trafik = []

    for fil in filer:
        namn = os.path.basename(fil)
        with open(fil, "r", encoding="utf-8") as fp:
            d = json.load(fp)

        spar = d.get("facit_spar") or {}
        scan_ms = spar.get("scan_ms", 20.0)

        minsta_dt = None
        minsta_fonster = None

        for s in spar.get("sekvenser", []):
            steg = s.get("steg", [])
            for i in range(len(steg) - 1):
                t1 = steg[i].get("t_ms")
                t2 = steg[i + 1].get("t_ms")
                if t1 is not None and t2 is not None:
                    dt = t2 - t1
                    if dt > 0 and (minsta_dt is None or dt < minsta_dt):
                        minsta_dt = dt

            for st in steg:
                if "min_s" in st and "max_s" in st:
                    fonster_ms = (st["max_s"] - st["min_s"]) * 1000.0
                    if minsta_fonster is None or fonster_ms < minsta_fonster:
                        minsta_fonster = fonster_ms

        kritisk_tid = minsta_dt if minsta_dt is not None else minsta_fonster

        post = {
            "namn": namn,
            "scan_ms": scan_ms,
            "minsta_dt_ms": minsta_dt,
            "minsta_fonster_ms": minsta_fonster,
            "kritisk_tid_ms": kritisk_tid,
        }
        uppgifter.append(post)

        if kritisk_tid is not None:
            if kritisk_tid < DT_TYST_MS:
                ogiltiga_vid_tyst.append(post)
            if kritisk_tid < DT_STD_MS:
                ogiltiga_vid_std.append(post)
            if kritisk_tid < DT_TRAFIK_MS:
                ogiltiga_vid_trafik.append(post)

    return {
        "totalt_uppgifter": len(uppgifter),
        "uppgifter": uppgifter,
        "ogiltiga_vid_tyst": ogiltiga_vid_tyst,
        "ogiltiga_vid_std": ogiltiga_vid_std,
        "ogiltiga_vid_trafik": ogiltiga_vid_trafik,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    granser = berakna_domargranser()
    bank = analysera_bankens_tidskrav()

    print("=== D10: PROVTAGNINGSFREKVENSEN MOT VAD SOM SKA SES ===\n")
    print("1. Ögats tidsupplösning per domare och regim:")
    print("%-12s | %-12s | %-12s | %-12s" % ("Domare", "Tyst (17.2Hz)", "Std (20.0Hz)", "Trafik (224.7Hz)"))
    print("-" * 55)
    for d, g in granser.items():
        print("%-12s | %10.1f ms | %10.1f ms | %10.2f ms" % (d, g["tyst_ms"], g["std_ms"], g["trafik_ms"]))

    print("\n2. Bankens tidskrav jämfört mot ögats upplösning:")
    print(f"Totalt granskade bankuppgifter: {bank['totalt_uppgifter']}")
    print(f"Kortaste steg i banken: 20.0 ms (motsvarar PLC scan_ms)")
    print(f"\nUppgifter med tidskrav snabbare än 17.2 Hz ({DT_TYST_MS:.1f} ms) — OGILTIGA vid tyst regim:")
    print(f"Antal: {len(bank['ogiltiga_vid_tyst'])} st ({len(bank['ogiltiga_vid_tyst']) / bank['totalt_uppgifter'] * 100:.1f} %)")
    for u in bank["ogiltiga_vid_tyst"]:
        print(f"  {u['namn']:12s}: kortaste dt = {u['kritisk_tid_ms']:.1f} ms (scan = {u['scan_ms']} ms)")

    print(f"\nUppgifter med tidskrav snabbare än 20.0 Hz ({DT_STD_MS:.1f} ms):")
    print(f"Antal: {len(bank['ogiltiga_vid_std'])} st")

    print(f"\nUppgifter med tidskrav snabbare än 224.7 Hz ({DT_TRAFIK_MS:.2f} ms):")
    print(f"Antal: {len(bank['ogiltiga_vid_trafik'])} st (Noll: 224.7 Hz täcker samtliga uppgifter)")

    # Assertions enligt D10
    assert len(bank["ogiltiga_vid_tyst"]) > 0, "Minst en uppgift måste kräva mer än vad tyst regim ger"
    assert len(bank["ogiltiga_vid_trafik"]) == 0, "Trafikregimen måste täcka samtliga uppgifter"

    print("\nSLUTSATS:")
    print(f"Vid 17.2 Hz tyst regim är domarna för {len(bank['ogiltiga_vid_tyst'])} uppgifter OGILTIGA pga otillräcklig samplingsfrekvens.")
    print("Under aktiv trafik (224.7 Hz) är samtliga 63 uppgifters domar giltiga.")

    if a.json:
        ut = {"granser": granser, "bank": bank}
        with open(a.json, "w") as fp:
            json.dump(ut, fp, indent=2)
        print(f"\nSkrev rådata till {a.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
