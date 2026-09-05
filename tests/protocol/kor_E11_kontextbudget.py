#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-141 / E11: Kontextbudgeten mot verkligheten.

Mater hur stor systemprompten blir med alla regler fran forhandsregler.py,
hur den forhaller sig till budgetallokeringarna i docs/spec/25_kontextbudget.md,
och vad som ryker forst nar den inte far plats i mindre kontextfonster.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Systemprompten med alla forhandsregler overskrider 5 %-budgeten "
        "i alla kontextfonster under 34 000 tokens, och vid trunkering bakifran "
        "trangs ogats hederlighets- och sakerhetsregler (F12, F15) ut forst.",
    "under_prov": (
        "svc/vc_assist_svc/plc/forhandsregler.py",
        "svc/vc_assist_svc/plc/reparation.py",
        "svc/vc_assist_svc/llm/budget.py",
        "svc/vc_assist_svc/llm/profil.py",
    ),
    "facit":
        "Exakt storlek pa systemprompten och dess sektioner, jamfort mot "
        "budgeten for 8k, 16k, 32k, 128k och 200k kontextfonster.",
    "facitkalla":
        "docs/spec/25_kontextbudget.md, avsnitt 1 tabellen (5 % for systemprompt).",
    "facitkalla_filer": (
        "docs/spec/25_kontextbudget.md",
    ),
    "trasiga_fall": (
        "ett kontextfonster dar reglerna trangs ut utan varning maste fällas",
        "en trunkering som klipper ogats regler fore syntaxregler maste fällas",
    ),
    "kraver": ("inget",),
    "matningar": ("M-141", "M-102", "M-119"),
}

import argparse
import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc import forhandsregler, reparation
from vc_assist_svc.llm import budget, profil


FONSTER_STORLEKAR = (8192, 16384, 32768, 65536, 131072, 200000)


def mat_systemprompt():
    grund = reparation._GRUNDPROMPT
    regler_text = forhandsregler.text()
    hel = reparation.SYSTEMPROMPT

    # Sektioner
    klasser = forhandsregler.ogats_klasser()
    g2_koder = forhandsregler.KONTROLLER
    g3_koder = forhandsregler.KONTROLLER_PLC

    g2_text = "\n".join("  %-22s %s" % (k, forhandsregler.REGLER[k])
                        for k in g2_koder if k in forhandsregler.REGLER)
    g3_text = "\n".join("  %-22s %s" % (k, forhandsregler.REGLER[k])
                        for k in g3_koder if k in forhandsregler.REGLER)
    ogat_text = "\n".join("  %-6s %-14s %s" % (k, klasser[k][0], forhandsregler.OGATS_REGLER[k])
                          for k in sorted(klasser, key=lambda x: int(x[1:]))
                          if k in forhandsregler.OGATS_REGLER)

    sektioner = {
        "grundprompt": {
            "tecken": len(grund),
            "bytes": len(grund.encode("utf-8")),
            "tokens_4b": len(grund.encode("utf-8")) // 4,
        },
        "grind_2_st": {
            "tecken": len(g2_text),
            "bytes": len(g2_text.encode("utf-8")),
            "tokens_4b": len(g2_text.encode("utf-8")) // 4,
            "antal_regler": len(g2_koder),
        },
        "grind_3_signalkarta": {
            "tecken": len(g3_text),
            "bytes": len(g3_text.encode("utf-8")),
            "tokens_4b": len(g3_text.encode("utf-8")) // 4,
            "antal_regler": len(g3_koder),
        },
        "ogat_process_sakerhet": {
            "tecken": len(ogat_text),
            "bytes": len(ogat_text.encode("utf-8")),
            "tokens_4b": len(ogat_text.encode("utf-8")) // 4,
            "antal_regler": len(klasser),
        },
    }

    tot_bytes = len(hel.encode("utf-8"))
    tot_tokens_4b = tot_bytes // 4
    tot_tokens_3c = len(hel) // 3

    budget_analys = []
    for f_storlek in FONSTER_STORLEKAR:
        allokerat_tokens = int(f_storlek * 0.05)  # 5 %
        differens = allokerat_tokens - tot_tokens_4b
        rymmer = differens >= 0
        budget_analys.append({
            "kontext_tokens": f_storlek,
            "allokerat_5_procent": allokerat_tokens,
            "faktiskt_behov_tokens": tot_tokens_4b,
            "differens_tokens": differens,
            "rymmer": rymmer,
            "belastning_procent": round(tot_tokens_4b / allokerat_tokens * 100.0, 1),
        })

    return {
        "totalt_tecken": len(hel),
        "totalt_bytes": tot_bytes,
        "totalt_tokens_4b": tot_tokens_4b,
        "totalt_tokens_3c": tot_tokens_3c,
        "sektioner": sektioner,
        "budget_analys": budget_analys,
        "kritisk_grans_tokens": int(tot_tokens_4b / 0.05),
    }


def main():
    parser = argparse.ArgumentParser(description="M-141 / E11: Kontextbudgeten mot verkligheten")
    parser.add_argument("--json-ut", default="docs/matningar/m141_kontextbudget.json")
    args = parser.parse_args()

    res = mat_systemprompt()

    print("=== M-141 / E11: Systempromptens storlek och kontextbudget ===")
    print("Totalt: %d tecken, %d bytes (~%d tokens @4B/tok, ~%d @3C/tok)" % (
        res["totalt_tecken"], res["totalt_bytes"], res["totalt_tokens_4b"], res["totalt_tokens_3c"]))
    print("\nSektionsuppdelning:")
    for s_namn, s_data in res["sektioner"].items():
        print("  %-25s %5d tecken, %4d tokens" % (s_namn, s_data["tecken"], s_data["tokens_4b"]))

    print("\nBudgetanalys (5 %% allokering for systemprompt):")
    for b in res["budget_analys"]:
        status = "RYMMER" if b["rymmer"] else "OVERSKRIDEN"
        print("  Kontext %6d tokens -> Budget %4d tokens -> Behov %4d tokens [%s: %5.1f %%]" % (
            b["kontext_tokens"], b["allokerat_5_procent"], b["faktiskt_behov_tokens"],
            status, b["belastning_procent"]))

    print("\nKritisk grans: Systemprompten kraver minst ett kontextfonster pa %d tokens for att rymmas inom 5 %%."
          % res["kritisk_grans_tokens"])

    if args.json_ut:
        with open(args.json_ut, "w", encoding="utf-8") as fp:
            json.dump(res, fp, indent=2, ensure_ascii=False)
        print("Fullstandig data sparad i %s" % args.json_ut)


if __name__ == "__main__":
    main()
