# -*- coding: utf-8 -*-
"""C10: Två skador samtidigt - hur ofta tar parvisa fel ut varandra?"""
import itertools
import json
import os
import sys
import time

_ROT = "/home/anton/projects/VC_Assist"
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "bank"))

import domare
from vc_assist_svc.plc.mutation import skador

TASKS = ["P-03", "C-04", "S-07", "A-03", "S-01", "P-05"]

print("=== C10: PARVISA SKADOR (SECOND-ORDER MUTATION) ===")
total_par = 0
total_utslagna = 0
detaljer = []

for tid in TASKS:
    p = json.load(open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % tid), encoding="utf-8"))
    ref = p["facit_spar"]["referens"]
    ref_lines = ref.split("\n")
    
    # Alla enkla skador
    alla_skador = skador(ref, per_sort=3)
    
    # Filtrera till de som är enradiga och fångas av beteendelagret individuellt
    fangade_enradiga = []
    for s in alla_skador:
        kropp_lines = s.kropp.split("\n")
        if len(kropp_lines) == len(ref_lines):
            andrade_rader = [i + 1 for i, (l1, l2) in enumerate(zip(ref_lines, kropp_lines)) if l1 != l2]
            if len(andrade_rader) == 1:
                d = domare.dom(p, s.kropp)
                if not d.godkand and not any(k.startswith("tolkfel") for k in d.koder):
                    fangade_enradiga.append((s, andrade_rader[0], kropp_lines[andrade_rader[0] - 1]))
    
    print("\n%s: %d individuellt fangade enradiga beteendeskador" % (tid, len(fangade_enradiga)))
    
    par_testade = 0
    par_utslagna = 0
    
    for (s1, r1, ny_l1), (s2, r2, ny_l2) in itertools.combinations(fangade_enradiga, 2):
        if r1 == r2:
            continue
        par_testade += 1
        
        komb_lines = list(ref_lines)
        komb_lines[r1 - 1] = ny_l1
        komb_lines[r2 - 1] = ny_l2
        komb_kropp = "\n".join(komb_lines)
        
        d = domare.dom(p, komb_kropp)
        if d.godkand:
            par_utslagna += 1
            print("  PARVIS UTSLACKNING: rad %d (%s) + rad %d (%s) -> GODKAND!" % (
                r1, s1.sort, r2, s2.sort))
            detaljer.append((tid, s1, r1, s2, r2))
    
    print("  Par testade: %d, Par dar felen tog ut varandra: %d (%.2f %%)" % (
        par_testade, par_utslagna,
        100.0 * par_utslagna / par_testade if par_testade else 0.0))
    total_par += par_testade
    total_utslagna += par_utslagna

print("\n=== TOTALT OVER ALLA %d UPPGIFTER ===" % len(TASKS))
print("Par testade: %d" % total_par)
print("Par dar felen tar ut varandra och blir osynliga: %d (%.3f %%)" % (
    total_utslagna, 100.0 * total_utslagna / total_par if total_par else 0.0))
