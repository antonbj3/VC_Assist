# -*- coding: utf-8 -*-
"""C11: Hur många stimuli behövs egentligen - sekvensvis ablationsanalys."""
import copy
import json
import os
import sys
import time

_ROT = "/home/anton/projects/VC_Assist"
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "bank"))

import domare
from vc_assist_svc.plc.mutation import skador

TASKS = ["P-03", "S-07", "C-04", "A-03", "H-04", "H-05", "L-07", "S-01", "T-05"]

print("=== C11: ABLATIONSANALYS ÖVER SEKVENSER (HUR MÅNGA STIMULI BEHÖVS) ===")

total_sekvenser = 0
unika_sekvenser = 0
redundanta_sekvenser = 0
detaljer = []

for tid in TASKS:
    p = json.load(open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % tid), encoding="utf-8"))
    facit = p["facit_spar"]
    ref = facit["referens"]
    sekvenser = facit.get("sekvenser") or []
    
    # Alla mutanter för uppgiften
    mutanter = skador(ref, per_sort=3)
    
    # Baslinje: vilka mutanter fångas av fulla facit (bara beteendefångster, inte tolkfel)
    bas_fangade = []
    for m in mutanter:
        d = domare.dom(p, m.kropp)
        if not d.godkand and not any(k.startswith("tolkfel") for k in d.koder):
            bas_fangade.append(m)
    
    print("\n%s: %d sekvenser, %d beteendefångade mutanter i baslinjen" % (
        tid, len(sekvenser), len(bas_fangade)))
    
    # Ablera en sekvens i taget
    for s in sekvenser:
        sid = s["id"]
        total_sekvenser += 1
        
        # Skapa probe utan denna sekvens
        p_abl = copy.deepcopy(p)
        p_abl["facit_spar"]["sekvenser"] = [x for x in sekvenser if x["id"] != sid]
        
        # Testa alla basline-fångade: hur många slipper igenom när s saknas?
        slappta = []
        for m in bas_fangade:
            d = domare.dom(p_abl, m.kropp)
            if d.godkand:
                slappta.append(m)
        
        unika = len(slappta)
        if unika > 0:
            unika_sekvenser += 1
            status = "NÖDVÄNDIG (%d unika fångster)" % unika
        else:
            redundanta_sekvenser += 1
            status = "REDUNDANT (0 unika fångster mot 22 skadesorter)"
        
        print("  %-42s: %s" % (sid, status))
        detaljer.append((tid, sid, len(bas_fangade), unika))

print("\n=== SAMMANFATTNING ÖVER %d UPPGIFTER ===" % len(TASKS))
print("Sekvenser provade: %d" % total_sekvenser)
print("Sekvenser med unika fångster (nödvändiga): %d (%.1f %%)" % (
    unika_sekvenser, 100.0 * unika_sekvenser / total_sekvenser if total_sekvenser else 0.0))
print("Sekvenser med 0 unika fångster (subsumerade / dekoration): %d (%.1f %%)" % (
    redundanta_sekvenser, 100.0 * redundanta_sekvenser / total_sekvenser if total_sekvenser else 0.0))
