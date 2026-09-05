# -*- coding: utf-8 -*-
"""C8: Mutera bank/domare.py och se om provsviten fångar det."""
import importlib.util
import json
import os
import sys
import time
import types

_ROT = "/home/anton/projects/VC_Assist"
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "bank"))

import lasare
import domare

bank = lasare.ladda(strikt=False)
bank_spar = [u for u in bank if u.data.get("facit_spar")]
orig_kallkod = open(os.path.join(_ROT, "bank", "domare.py"), encoding="utf-8").read()

def kor_svit(dom_mod):
    # 1. referenser
    for u in bank_spar:
        d = dom_mod.dom_referens(u.data)
        if not d.godkand:
            return False, "referens falldes: %s (%s)" % (u.id, d.koder[:3])
    # 2. motbevis
    for u in bank_spar:
        for namn, d, faller_pa in dom_mod.dom_motbevis(u.data):
            traffar = [k for k in faller_pa if k in d.koder]
            if not d.brister or len(traffar) != len(faller_pa):
                return False, "motbevis falldes inte: %s:%s (fick %s, vantade %s)" % (
                    u.id, namn, d.koder[:3], faller_pa)
    return True, "godkand"

MUTATIONER = [
    # 1. Float-tolerans i _lika: ta bort tolerans helt (exakt flyttalslikhet)
    ("FLOAT_TOLERANS_NOLL",
     "abs(float(vantat) - float(faktiskt)) <= 1e-9",
     "float(vantat) == float(faktiskt)"),

    # 2. Boolesk typkonvertering i _lika: tillåt int 1 mot bool True utan bool-check
    ("BOOL_STRIKT_STRUKEN",
     "if isinstance(vantat, bool) or isinstance(faktiskt, bool):\n        return bool(vantat) == bool(faktiskt)",
     "if False:\n        pass"),

    # 3. Sluttid i dom(): ändra <= till < (avsluta ett scan tidigare)
    ("SLUTTID_ETT_SCAN_TIDIGARE",
     "while motor.tid_ms <= slut_ms + 1e-9:",
     "while motor.tid_ms < slut_ms - 1e-9:"),

    # 4. Punktkravens tidsmatchning: ändra tolerans till 0
    ("PUNKTKRAV_TOLERANS_NOLL",
     "if abs(float(s[\"t_ms\"]) - (nu - scan_ms)) > 1e-9:",
     "if float(s[\"t_ms\"]) != (nu - scan_ms):"),

    # 5. Invariant deduplicering: ta bort inv_falld.add() (rapportera varje scan)
    ("INVARIANT_RAPPPORTERA_ALLA_SCAN",
     "if inv[\"namn\"] in inv_falld:\n                        continue",
     "if False:\n                        continue"),

    # 6. Invariant-villkor: ändra all(nar) till any(nar) (lösare triggning)
    ("INVARIANT_NAR_ANY",
     "all(_lika(v, motor.las(n))\n                           for n, v in inv[\"nar\"].items())",
     "any(_lika(v, motor.las(n))\n                           for n, v in inv[\"nar\"].items())"),

    # 7. Invariant-krav: ändra all(kraver) till any(kraver) (slappare krav)
    ("INVARIANT_KRAVER_ANY",
     "not all(_lika(v, motor.las(n))\n                               for n, v in inv[\"kraver\"].items())",
     "not any(_lika(v, motor.las(n))\n                               for n, v in inv[\"kraver\"].items())"),

    # 8. Flankfönster: ta bort nedre gräns fran_ms
    ("FLANK_STRYK_FRAN_MS",
     "float(f[\"fran_ms\"]) <= t_ledd <= float(f[\"till_ms\"])",
     "t_ledd <= float(f[\"till_ms\"])"),

    # 9. Flankdetektering RISE: ändra v and not p till bara v (nivå i stället för flank!)
    ("FLANK_RISE_TILL_NIVA",
     "if f[\"typ\"] == \"RISE\" and v and not p:",
     "if f[\"typ\"] == \"RISE\" and v:"),

    # 10. Flankdetektering FALL: ändra p and not v till bara not v
    ("FLANK_FALL_TILL_NIVA",
     "elif f[\"typ\"] == \"FALL\" and p and not v:",
     "elif f[\"typ\"] == \"FALL\" and not v:"),

    # 11. M-106 buggen: uppdatera forra omedelbart inne i flankloopen i stället för efteråt
    ("M106_OMEDELBAR_FORRA_UPPDATERING",
     "forra.update(nu_varden)",
     "pass  # forra uppdateras direkt"),

    # 12. Förgrindsbrist: ignorera förgrindar
    ("FORGRIND_IGNORERAS",
     "brist = forgrindsbrist(stationsdom)\n    if brist is not None:\n        return Dom(post.get(\"task_id\"), [brist], 0)",
     "pass"),
]

print("=== KÖR C8: MUTATION AV BANK/DOMARE.PY ===")
resultat = []
for namn, fore, efter in MUTATIONER:
    if fore not in orig_kallkod:
        print("FEL: mönstret för %s finns inte i källkoden!" % namn)
        continue
    ny_kod = orig_kallkod.replace(fore, efter, 1)
    
    # Skapa modul i minnet
    mod = types.ModuleType("domare_muterad")
    mod.__file__ = os.path.join(_ROT, "bank", "domare.py")
    try:
        exec(compile(ny_kod, "<domare_muterad>", "exec"), mod.__dict__)
    except Exception as e:
        print("%-35s -> SYNTAXFEL / IMPORTFEL: %s" % (namn, e))
        resultat.append((namn, "FANGAD", "syntaxfel: %s" % e))
        continue
    
    ok, msg = kor_svit(mod)
    if ok:
        print("%-35s -> OVERLEVDE (provsviten tiger!)" % namn)
        resultat.append((namn, "OVERLEVDE", "ingen reaktion från sviten"))
    else:
        print("%-35s -> FANGAD: %s" % (namn, msg))
        resultat.append((namn, "FANGAD", msg))

print("\nSammanfattning:")
fangade = sum(1 for _, utfall, _ in resultat if utfall == "FANGAD")
overlevde = sum(1 for _, utfall, _ in resultat if utfall == "OVERLEVDE")
print("Mutanter totalt: %d, Fångade: %d (%.0f %%), Överlevde: %d" % (
    len(resultat), fangade, 100.0 * fangade / len(resultat), overlevde))
