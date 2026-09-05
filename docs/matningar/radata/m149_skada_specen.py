# -*- coding: utf-8 -*-
"""C9: Skada krav i uppgiftens expect och kontrollera om referensen fälls."""
import copy
import json
import os
import sys

_ROT = "/home/anton/projects/VC_Assist"
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "bank"))

import domare
import schema

TASKS = ["A-03", "P-03", "S-07", "C-04", "T-04"]

SKADOR_EXPECT = [
    ("THROUGHPUT_ORIMLIG", lambda e: e.update({"throughput_per_h": 999999.0})),
    ("MAX_COLLISIONS_MINUS", lambda e: e.update({"max_collisions": -1})),
    ("MIN_CLEARANCE_5M", lambda e: e.update({"min_clearance_mm": 5000.0})),
    ("MUST_PASS_EMPTY", lambda e: e.update({"must_pass": []})),
    ("FORBIDDEN_LINE_WILDCARD", lambda e: e.update({"forbidden_lines": [{"section": "TIMING", "template": "*"}]})),
    ("VERDICT_FAIL", lambda e: e.update({"verdict": "FAIL"})),
]

print("=== C9: SKADA SPECEN (EXPECT) MOT DOMARE OCH REFERENSLÖSNING ===")
resultat = []
for tid in TASKS:
    p = json.load(open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % tid), encoding="utf-8"))
    ref = p["facit_spar"]["referens"]
    print("\n--- %s ---" % tid)
    for namn, mut_fn in SKADOR_EXPECT:
        p_mut = copy.deepcopy(p)
        mut_fn(p_mut["expect"])
        
        # 1. Prövas det av spårdomaren?
        d = domare.dom(p_mut, ref)
        dom_reagerar = not d.godkand
        
        # 2. Prövas det av schemavalideraren?
        val_fel = schema.validera(p_mut)
        schema_reagerar = bool(val_fel)
        
        status = "FÄLLDES" if (dom_reagerar or schema_reagerar) else "GRÖN (OMÄTT)"
        print("  %-25s: dom=%-5s schema=%-5s -> %s" % (
            namn, "RÖD" if dom_reagerar else "GRÖN",
            "RÖD" if schema_reagerar else "GRÖN", status))
        resultat.append((tid, namn, dom_reagerar, schema_reagerar))

omatta = sum(1 for _, _, d, s in resultat if not d and not s)
print("\nTotalt provade spec-skador: %d" % len(resultat))
print("Antal skador där referenslösningen förblir GRÖN (kravet mäts aldrig): %d (%.0f %%)" % (
    omatta, 100.0 * omatta / len(resultat)))
