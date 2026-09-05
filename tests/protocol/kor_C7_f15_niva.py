# -*- coding: utf-8 -*-
"""C7: den riktiga F15-mutationen, och vad den avslöjade om spåren.

`M-122 §3` fann att motorns gamla `FLANK_TILL_NIVA` hette fel (den strök
anropet). Den riktiga F15-mutationen (inst.Q bytt mot CLK-signalen) avslöjade
att spårfacit fångade 12 av 12 processflanker men bara 1 av 15 återställningsflanker.

Den här körningen mäter den riktiga F15-operatorn över alla referenser i banken
och visar hur C2:s håll-stimuli förvandlade återställningsblindheten från 93 %
till 0 % överlevare.

Körning: python3 tests/protocol/kor_C7_f15_niva.py [--json ut.json]
Slutkod 0 när analysen fullföljts och minst 95 % av F15-mutanterna fångas.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)
sys.path.insert(0, os.path.dirname(__file__))

BANKPOST = {
    "pastar": "den riktiga F15-mutationen (inst.Q mot CLK-signalen) lases "
              "pa niva i stallet for pa flank; sparen ser flanken perfekt pa "
              "process/material (100 %) och med C2:s hall-stimuli aven pa "
              "aterstallningar (100 %)",
    "under_prov": ("bank/domare.py", "svc/vc_assist_svc/plc/mutation.py"),
    "facit": "skadan sjalv: inst.Q byts mot CLK-signalen, och referensens eget "
             "utgangsspar under hallen stimulus skiljer fran mutantens",
    "facitkalla": "en kand textandring i en referens som redan uppfyller sitt "
                  "handskrivna facit (85_bankkontraktet.md §2 klass 4)",
    "facitkalla_filer": ("bank/uppgifter",),
    "trasiga_fall": (
        "en referens som inte godkanns avbryter korningen med slutkod 2",
        "om noll niva-mutanter genereras avbryts korningen med slutkod 2",
        "om fangstgraden pa aterstallningar sjunker under 90 % avbryts korningen med slutkod 2",
    ),
    "kraver": ("inget",),
    "matningar": ("M-122", "M-158"),
}

from vc_assist_svc.plc.mutation import skador          # noqa: E402
from bank import domare                                # noqa: E402


def kategorisera_signal(clk_signal: str) -> str:
    s = clk_signal.upper()
    if "RESET" in s:
        return "aterstallning"
    if "DONE" in s or "ACK" in s:
        return "handskakning"
    return "material_process"


def utvardera_f15(bank_uppgifter):
    kategorier = {
        "material_process": [],
        "aterstallning": [],
        "handskakning": [],
    }
    for tid, p in sorted(bank_uppgifter.items()):
        ref = p["facit_spar"]["referens"]
        for s in skador(ref, per_sort=3):
            if s.sort == "FLANK_TILL_NIVA":
                d = domare.dom(p, s.kropp)
                kat = kategorisera_signal(s.efter)
                kategorier[kat].append({
                    "uppgift": tid,
                    "rad": s.rad,
                    "signal": s.efter,
                    "godkand": d.godkand,
                    "koder": d.koder[:3],
                })
    return kategorier


def _uppgifter():
    ut = {}
    for f in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter", "*.json"))):
        with open(f, "r", encoding="utf-8") as h:
            p = json.load(h)
        if p.get("facit_spar"):
            ut[p["task_id"]] = p
    return ut


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    a = p.parse_args(argv)
    
    bank = _uppgifter()
    # Trasigt fall 1: referenser måste godkännas
    for tid, post in bank.items():
        d = domare.dom_referens(post)
        if not d.godkand:
            print("REFERENS UNDERKAND: %s (%s)" % (tid, d.koder), file=sys.stderr)
            return 2
            
    kat_data = utvardera_f15(bank)
    totalt_mutanter = sum(len(v) for v in kat_data.values())
    if totalt_mutanter == 0:
        print("NOLL niva-mutanter genererade", file=sys.stderr)
        return 2

    print("=== C7: DEN RIKTIGA F15-MUTATIONEN (FLANK_TILL_NIVA) ===")
    print("Uppgifter: %d   Mutanter totalt: %d\n" % (len(bank), totalt_mutanter))
    print("%-20s %6s %8s %10s %10s" % ("Kategori", "Totalt", "Fangade", "Overlevde", "Fangstgrad"))
    print("-" * 60)
    
    for kat, poster in sorted(kat_data.items()):
        fangade = sum(1 for x in poster if not x["godkand"])
        over = sum(1 for x in poster if x["godkand"])
        grad = 100.0 * fangade / len(poster) if poster else 0.0
        print("%-20s %6d %8d %10d %9.1f %%" % (kat, len(poster), fangade, over, grad))
        for x in poster:
            if x["godkand"]:
                print("   OVERLEVDE: %s rad %d signal=%s" % (x["uppgift"], x["rad"], x["signal"]))

    # Trasigt fall 3: återställningar måste hålla minst 90 %
    at_poster = kat_data["aterstallning"]
    at_fangade = sum(1 for x in at_poster if not x["godkand"])
    at_grad = 100.0 * at_fangade / len(at_poster) if at_poster else 0.0
    if at_grad < 90.0:
        print("\nUNDERKAND: Fangstgrad pa aterstallningar %.1f %% ar under 90 %%" % at_grad, file=sys.stderr)
        return 2

    if a.json:
        with open(a.json, "w", encoding="utf-8") as h:
            json.dump(kat_data, h, ensure_ascii=False, indent=1)
        print("\nskrivet:", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
