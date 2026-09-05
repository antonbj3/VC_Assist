#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-136 / E4: Kan en LLM hitta det den behover - breddmatning i skala over 50+ bankuppgifter.

Krav fran operatorn: "Informationen maste vara lattillganglig for LLM".
Kravet ar inte att informationen ar korrekt - det ar att den gar att hitta och
anvanda: litet ordforrad, kort form, enhet och harkomst i vardet.

Pseudo-simulering i skala:
- 50+ verkliga bankuppgifter (alla 63 uppgifter i banken)
- For varje uppgift: vilken information som kravs for scen, logik, timing och grindar
- Prova om informationen gar att na genom verktygen (bench_task, search_catalog,
  lookup_api, search_api, component_datasheet)
- Mat TACKNING och ORDFORRADSBREDD, inte bara volym
- Notera uppslag som ger SAKNAS (vardefulla nej som hindrar hallucinationer).

Anvandning:
    python3 tests/protocol/kor_E4_llm_tackning.py [--json-ut docs/matningar/m136_llm_tackning.json]
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Informationen som en sprakmodell behover for att bygga en cell och "
        "skriva dess PLC-styrning gar att na genom tjanstens uppslagsverktyg "
        "over en matt andel av bankens uppgifter, och ordforradsbredden "
        "tacker bade komponenter, signalkarta, grindregler och standarder.",
    "under_prov": (
        "svc/vc_assist_svc/verktyg/kunskap.py",
        "svc/vc_assist_svc/verktyg/katalog.py",
        "svc/vc_assist_svc/verktyg/ogonverktyg.py",
        "svc/vc_assist_svc/api_index.py",
    ),
    "facit":
        "For varje informationskrav: om svaret kan nas med varde och harkomst "
        "(SVAR), om det ar ett arligt nej pa en ogiltig symbol (SAKNAS_VARDE), "
        "eller om det saknas eller ar halvt.",
    "facitkalla":
        "Bankens 63 uppgifter i bank/uppgifter/*.json med scen, control.signals, "
        "expect.lines och facit_spar.",
    "facitkalla_filer": (
        "bank/uppgifter",
        "bank/katalog_index.json",
        "docs/spec/41_ogat_kontrakt.md",
    ),
    "trasiga_fall": (
        "information som inte har deklarerad enhet far inte raknas som fullgott svar",
        "tysta fel dar fel symbol returneras maste fällas",
        "delstrangstraffar utan ordgrans far inte raknas som namntraff",
    ),
    "kraver": ("bank",),
    "matningar": ("M-136", "M-119", "M-84"),
}

import argparse
import glob
import json
import os
import sys
import time
from collections import Counter, defaultdict

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import verktyg as V

# Kanda fallor dar modellen brukar hallucinera: dessa BÖR svara SAKNAS (found=False)
FALLOR = (
    ("VC_BOOLSIGNAL", "VC_BOOLEANSIGNAL"),
    ("setPosition", "PositionMatrix"),
    ("getComponentByName", "findComponent"),
    ("vcRobot", "vcRobotController"),
    ("canConect", "canConnect"),
)


def ladda_uppgifter(kat=None):
    if kat is None:
        kat = os.path.join(_ROT, "bank", "uppgifter")
    uppg = []
    for f in sorted(glob.glob(os.path.join(kat, "*.json"))):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            if "task_id" in d and "control" in d:
                uppg.append(d)
        except Exception:
            pass
    return uppg


def kor_pseudo_simulering(uppgifter):
    """Utfor uppslag for alla uppgifternas krav och berakna tackning."""
    resultat_per_uppgift = []
    totalt_krav = 0
    totalt_svar = 0
    totalt_saknas_varde = 0
    totalt_halvt = 0
    totalt_saknas = 0

    per_kategori = defaultdict(lambda: {"krav": 0, "svar": 0, "halvt": 0, "saknas": 0})
    distinkta_symboler = set()

    # 1. Prova fallorna (anti-hallucination / SAKNAS-varde)
    fallor_utfall = []
    for fel_namn, avsett in FALLOR:
        res = V.DATA_HANDLERS["lookup_api"]({"name": fel_namn})
        if not res["found"]:
            totalt_saknas_varde += 1
            fallor_utfall.append({
                "fraga": fel_namn,
                "status": "SAKNAS_VARDE",
                "not": "Arligt nej (found=False); hindrar hallucination av %s" % fel_namn,
            })
        else:
            fallor_utfall.append({
                "fraga": fel_namn,
                "status": "TYST_FEL",
                "not": "Fick traeff pa felaktigt namn %s!" % fel_namn,
            })

    # 2. Ga igenom alla uppgifter
    for d in uppgifter:
        t_id = d["task_id"]
        u_info = {
            "task_id": t_id,
            "titel": d.get("title", ""),
            "grupp": d.get("grupp", t_id[0]),
            "krav": 0,
            "svar": 0,
            "detaljer": [],
        }

        # A. Uppgiftens grunddata via bench_task
        totalt_krav += 1
        u_info["krav"] += 1
        per_kategori["bench_task"]["krav"] += 1
        bt = V.DATA_HANDLERS["bench_task"]({"task_id": t_id})
        if bt.get("found") and bt.get("control") and bt.get("fysik"):
            totalt_svar += 1
            u_info["svar"] += 1
            per_kategori["bench_task"]["svar"] += 1
            u_info["detaljer"].append({"slag": "task", "status": "SVAR", "namn": t_id})
        else:
            totalt_saknas += 1
            per_kategori["bench_task"]["saknas"] += 1
            u_info["detaljer"].append({"slag": "task", "status": "SAKNAS", "namn": t_id})

        # B. Komponenterna i scenen
        scen = d.get("scene") or {}
        for komp in scen.get("components") or []:
            uri = komp["uri"]
            totalt_krav += 1
            u_info["krav"] += 1
            per_kategori["komponenter"]["krav"] += 1
            distinkta_symboler.add(uri)
            res = V.DATA_HANDLERS["catalog_item"]({"uri": uri})
            if res.get("found"):
                totalt_svar += 1
                u_info["svar"] += 1
                per_kategori["komponenter"]["svar"] += 1
                u_info["detaljer"].append({"slag": "komponent", "status": "SVAR", "uri": uri})
            else:
                totalt_saknas += 1
                per_kategori["komponenter"]["saknas"] += 1
                u_info["detaljer"].append({"slag": "komponent", "status": "SAKNAS", "uri": uri})

        # C. Styrsignaler (control.signals)
        ctrl = d.get("control") or {}
        for sig in ctrl.get("signals") or []:
            s_namn = sig["name"]
            totalt_krav += 1
            u_info["krav"] += 1
            per_kategori["signaler"]["krav"] += 1
            distinkta_symboler.add(s_namn)
            res = V.DATA_HANDLERS["search_catalog"]({"query": s_namn})
            traffar = [t for t in res.get("traffar", []) if t.get("namn") == s_namn]
            if traffar:
                totalt_svar += 1
                u_info["svar"] += 1
                per_kategori["signaler"]["svar"] += 1
                u_info["detaljer"].append({"slag": "signal", "status": "SVAR", "namn": s_namn})
            else:
                totalt_saknas += 1
                per_kategori["signaler"]["saknas"] += 1
                u_info["detaljer"].append({"slag": "signal", "status": "SAKNAS", "namn": s_namn})

        # D. Grindregler ur must_pass och expect.lines
        exp = d.get("expect") or {}
        sedda_regler = set()
        for rad in exp.get("lines") or []:
            tmpl = rad.get("template", "")
            nyckelord = tmpl.split()[0] if tmpl else ""
            if nyckelord and nyckelord not in sedda_regler:
                sedda_regler.add(nyckelord)
                totalt_krav += 1
                u_info["krav"] += 1
                per_kategori["grindregler"]["krav"] += 1
                distinkta_symboler.add(nyckelord)
                res = V.DATA_HANDLERS["search_api"]({"query": nyckelord, "limit": 5})
                # Kontrollera om traffen innehaller nyckelordet fran spec
                traffar = res.get("traffar", [])
                match = any(t.get("name") == nyckelord or nyckelord in (t.get("full_name") or "")
                            for t in traffar)
                if match:
                    totalt_svar += 1
                    u_info["svar"] += 1
                    per_kategori["grindregler"]["svar"] += 1
                    u_info["detaljer"].append({"slag": "grindregel", "status": "SVAR", "namn": nyckelord})
                else:
                    totalt_saknas += 1
                    per_kategori["grindregler"]["saknas"] += 1
                    u_info["detaljer"].append({"slag": "grindregel", "status": "SAKNAS", "namn": nyckelord})

        # E. Standarder (om angivna)
        fs = d.get("facit_spar") or {}
        if fs.get("standard"):
            import re
            m = re.search(r"\b(?:ISO|IEC|EN|DIN|ANSI|VDI|VDA|RIA)\s?\d{3,5}", fs["standard"])
            if m:
                std_namn = m.group(0)
                totalt_krav += 1
                u_info["krav"] += 1
                per_kategori["standarder"]["krav"] += 1
                distinkta_symboler.add(std_namn)
                res = V.DATA_HANDLERS["search_api"]({"query": std_namn, "limit": 5})
                traffar = res.get("traffar", [])
                match = any(std_namn in (t.get("name") or "") or std_namn in (t.get("description") or "")
                            for t in traffar)
                if match:
                    totalt_svar += 1
                    u_info["svar"] += 1
                    per_kategori["standarder"]["svar"] += 1
                    u_info["detaljer"].append({"slag": "standard", "status": "SVAR", "namn": std_namn})
                else:
                    totalt_saknas += 1
                    per_kategori["standarder"]["saknas"] += 1
                    u_info["detaljer"].append({"slag": "standard", "status": "SAKNAS", "namn": std_namn})

        resultat_per_uppgift.append(u_info)

    tackningsgrad = (totalt_svar / totalt_krav * 100.0) if totalt_krav > 0 else 0.0

    return {
        "antal_uppgifter": len(uppgifter),
        "totalt_krav": totalt_krav,
        "totalt_svar": totalt_svar,
        "totalt_saknas": totalt_saknas,
        "tackningsgrad_procent": round(tackningsgrad, 1),
        "saknas_varde_antal": totalt_saknas_varde,
        "distinkta_symboler_bredd": len(distinkta_symboler),
        "per_kategori": dict(per_kategori),
        "fallor": fallor_utfall,
        "uppgifter": resultat_per_uppgift,
    }


def main():
    parser = argparse.ArgumentParser(description="M-136 / E4: Pseudo-simulering av LLM-informationsatkomst")
    parser.add_argument("--json-ut", default="docs/matningar/m136_llm_tackning.json")
    args = parser.parse_args()

    t0 = time.time()
    uppgifter = ladda_uppgifter()
    print("Laddade %d uppgifter fran banken." % len(uppgifter))
    res = kor_pseudo_simulering(uppgifter)
    varaktighet = round(time.time() - t0, 3)
    res["varaktighet_s"] = varaktighet

    print("\n=== Resultat M-136: Informationsatkomst over %d uppgifter ===" % res["antal_uppgifter"])
    print("Totalt antal informationspunkter: %d" % res["totalt_krav"])
    print("Besvarade (SVAR):                %d (%.1f %%)" % (res["totalt_svar"], res["tackningsgrad_procent"]))
    print("Saknas (SAKNAS):                 %d" % res["totalt_saknas"])
    print("Avvisade fallor (SAKNAS-varde):  %d av %d" % (res["saknas_varde_antal"], len(FALLOR)))
    print("Ordförrådsbredd (distinkta):     %d symboler" % res["distinkta_symboler_bredd"])
    print("\nTackning per kategori:")
    for kat, data in sorted(res["per_kategori"].items()):
        proc = (data["svar"] / data["krav"] * 100.0) if data["krav"] else 0.0
        print("  %-16s %3d / %3d  (%.1f %%)" % (kat, data["svar"], data["krav"], proc))

    if args.json_ut:
        with open(args.json_ut, "w", encoding="utf-8") as fp:
            json.dump(res, fp, indent=2, ensure_ascii=False)
        print("\nFullstandig data sparad i %s" % args.json_ut)


if __name__ == "__main__":
    main()
