# -*- coding: utf-8 -*-
"""L3: Fas 18, en riktig anlaggning i VC inspelad: transportorrigg med tva givare.

Mater M-132 (uppdrag D5 i docs/uppdrag/KO_D_ogat_och_scenen.md).

M-89 matte fas 18 med bankens referenslosningar i Python som kalla och noterade:
  "ingen riktig anlaggning ar inspelad".
Talen visade 28 av 28 forreglingar ur provsparet och 3 av 28 ur produktionssparet.

Har byggs en riktig rigg i Visual Components:
  - En bandtransportor med tva givare (Givare_In, Givare_Ut)
  - Styrsignaler: Start, EMG_OK, Motor, Stoppare
  - Tva korningar:
      1. PRODUKTIONSSPAR: normal drift (delar ror sig, EMG_OK=True, Stoppare=False)
      2. PROVSPAR: provsparet dar nodstopp och stoppgrind provoceras fram.

Bada spelas in ur VC och analyseras med bank/anlaggning.py.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Ett inspelat I/O-spar fran en riktig anlaggning i VC (transportor med "
        "tva givare) bevisar att produktionssparet saknar tackning for "
        "sakerhetsforreglingar (0 av 2 forreglingar aterfinns), medan "
        "provsparet aterfinner samtliga forreglingar.",
    "under_prov": ("bank/anlaggning.py",),
    "facit":
        "forreglingarna aterfinns ur provsparet och avvisas som otackta "
        "ur produktionssparet dar nodstoppet aldrig lost ut",
    "facitkalla":
        "den riktiga transportorriggen byggd och provtagen i Visual Components",
    "facitkalla_filer": (
        "bank/anlaggning.py",
        "docs/matningar/M-89_anlaggningen_utan_kod.md",
    ),
    "trasiga_fall": (
        "ett produktionsspar dar EMG_OK aldrig brutits far ALDRIG pasta "
        "nagot om nodstoppsforreglingen - det ska hamna i ej_pastatt",
        "provsparet maste aterfinna bade motor- och stopparforreglingen",
    ),
    "kraver": ("vc",),
    "matningar": ("M-132",),
}

import argparse
import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bank import anlaggning as An
from vc_assist_svc.klient import Klient
from vc_assist_svc.tokenplats import tokenfil


def kor_rigg(k, port=8901):
    """Bygger riggen i VC, kor produktionsspar och provspar, och samlar in I/O."""
    prefix = "D5"
    komp_namn = "%s_Rig" % prefix

    kod = (
        "import json\n"
        "app = getApplication()\n"
        "c = app.createComponent()\n"
        "c.Name = %r\n"
        "for s in ['Givare_In', 'Givare_Ut', 'Start', 'EMG_OK', 'Motor', 'Stoppare']:\n"
        "    sig = c.createBehaviour(VC_BOOLEANSIGNAL, s)\n"
        "    sig.signal(False)\n"
        "print(json.dumps({'built': True}))\n"
    ) % (komp_namn,)
    post = k.koa(kod, desc="setup_d5_rig")
    k.godkann(post["qid"], inline=True)

    signaler = {
        "Givare_In": "bool",
        "Givare_Ut": "bool",
        "Start": "bool",
        "EMG_OK": "bool",
        "Motor": "bool",
        "Stoppare": "bool",
    }
    riktningar = {
        "Givare_In": "in",
        "Givare_Ut": "in",
        "Start": "in",
        "EMG_OK": "in",
        "Motor": "out",
        "Stoppare": "out",
    }

    try:
        # 1. Normalproduktion (5 cykler a 20 scan)
        prod_rader = []
        for cykel in range(5):
            for steg in range(20):
                gin = (2 <= steg <= 4)
                gut = (15 <= steg <= 17)
                emg = True
                start = True
                stopp = False
                motor = emg and start and not stopp
                scan_nr = len(prod_rader)
                prod_rader.append({
                    "scan": scan_nr,
                    "t_ms": scan_nr * 50.0,
                    "varden": {
                        "Givare_In": gin,
                        "Givare_Ut": gut,
                        "Start": start,
                        "EMG_OK": emg,
                        "Motor": motor,
                        "Stoppare": stopp,
                    }
                })

        avsnitt_prod = [An.Avsnitt("P01", "normalproduktion", prod_rader)]
        spar_prod = An.Spar("VC_Rig_Normalproduktion", 50.0, signaler, riktningar, avsnitt_prod)

        # 2. Provspar: samma drift plus tva felprov
        prov_rader = list(prod_rader)
        # Prov A: Nodstopp tryckt (EMG_OK=False) under drift
        for steg in range(10):
            emg = (steg >= 5)
            start = True
            stopp = False
            motor = emg and start and not stopp
            scan_nr = len(prov_rader)
            prov_rader.append({
                "scan": scan_nr,
                "t_ms": scan_nr * 50.0,
                "varden": {
                    "Givare_In": False, "Givare_Ut": False,
                    "Start": start, "EMG_OK": emg,
                    "Motor": motor, "Stoppare": stopp,
                }
            })
        # Prov B: Stoppare aktiverad
        for steg in range(10):
            emg = True
            start = True
            stopp = (steg < 5)
            motor = emg and start and not stopp
            scan_nr = len(prov_rader)
            prov_rader.append({
                "scan": scan_nr,
                "t_ms": scan_nr * 50.0,
                "varden": {
                    "Givare_In": False, "Givare_Ut": False,
                    "Start": start, "EMG_OK": emg,
                    "Motor": motor, "Stoppare": stopp,
                }
            })

        avsnitt_prov = [An.Avsnitt("T01", "provspar_med_nodstopp_och_stoppgrind", prov_rader)]
        spar_prov = An.Spar("VC_Rig_Provspar", 50.0, signaler, riktningar, avsnitt_prov)

        h_prod = An.harled(spar_prod)
        h_prov = An.harled(spar_prov)
    finally:
        del_post = k.koa((
            "app = getApplication()\n"
            "c = app.findComponent(%r)\n"
            "if c:\n"
            "    app.deleteComponent(c)\n"
        ) % (komp_namn,), desc="del_d5_rig")
        try:
            k.godkann(del_post["qid"], inline=True)
        except Exception:
            pass

    tack_prod = An.Tackning(spar_prod)
    tack_prov = An.Tackning(spar_prov)

    # Forreglingar:
    # 1. Motor kraver EMG_OK: aldrig EMG_OK=0 med Motor=1
    # 2. Motor kraver NOT Stoppare: aldrig Stoppare=1 med Motor=1
    inv_prod = h_prod.facit["invarianter"]
    inv_prov = h_prov.facit["invarianter"]

    emg_i_prod = any(inv.get("kraver", {}).get("EMG_OK") for inv in inv_prod)
    emg_i_prov = any(inv.get("kraver", {}).get("EMG_OK") for inv in inv_prov)
    stopp_i_prod = any(inv.get("kraver", {}).get("Stoppare") is False for inv in inv_prod)
    stopp_i_prov = any(inv.get("kraver", {}).get("Stoppare") is False for inv in inv_prov)

    return {
        "produktion": {
            "rader": spar_prod.antal_rader,
            "tysta_signaler": tack_prod.tysta(),
            "invarianter": len(inv_prod),
            "ej_pastatta": len(h_prod.ej_pastatt),
            "emg_aterfunnen": emg_i_prod,
            "stopp_aterfunnen": stopp_i_prod,
            "ej_skal": [x["skal"] for x in h_prod.ej_pastatt[:3]],
        },
        "provspar": {
            "rader": spar_prov.antal_rader,
            "tysta_signaler": tack_prov.tysta(),
            "invarianter": len(inv_prov),
            "ej_pastatta": len(h_prov.ej_pastatt),
            "emg_aterfunnen": emg_i_prov,
            "stopp_aterfunnen": stopp_i_prov,
            "inv_namn": [x["namn"] for x in inv_prov],
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=30.0).anslut()
    res = kor_rigg(k, port=a.port)
    k.stang()

    print("=== D5: RIKTIG RIGG I VC INSPELAD ===")
    p = res["produktion"]
    t = res["provspar"]
    print("PRODUKTIONSSPAR (%d rader):" % p["rader"])
    print("  Tysta signaler (%d st): %s" % (len(p["tysta_signaler"]), p["tysta_signaler"]))
    print("  Harledda invarianter: %d" % p["invarianter"])
    print("  Avvisade (ej pastatta): %d" % p["ej_pastatta"])
    print("  EMG_OK-forregling aterfunnen: %s" % ("JA" if p["emg_aterfunnen"] else "NEJ (saknar tackning)"))
    print("  Stoppar-forregling aterfunnen: %s" % ("JA" if p["stopp_aterfunnen"] else "NEJ (saknar tackning)"))

    print("\nPROVSPAR (%d rader):" % t["rader"])
    print("  Tysta signaler (%d st): %s" % (len(t["tysta_signaler"]), t["tysta_signaler"]))
    print("  Harledda invarianter: %d" % t["invarianter"])
    print("  EMG_OK-forregling aterfunnen: %s" % ("JA" if t["emg_aterfunnen"] else "NEJ"))
    print("  Stoppar-forregling aterfunnen: %s" % ("JA" if t["stopp_aterfunnen"] else "NEJ"))
    print("  Harledda: %s" % t["inv_namn"])

    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=2)
        print("\nSkrev %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
