# -*- coding: utf-8 -*-
"""M-121: matningen bakom dubbelskrivningsgrindens uteslutningsprov.

Tre tal, alla ur repot:

  1. bankens referenser med sparfacit genom grind 2/3: hur manga falls, pa vad
  2. M-96-korpusen (modellskrivna kroppar ur fas 9:s forsta modelldrivna
     korning, docs/matningar/m96_korpus_*.json) genom samma grind: hur manga
     DUBBELSKRIVNING-domar star kvar - det ar priset i falska grona, mätt
  3. mutationer av referenserna som tar bort uteslutningen: faller de?

Talen star i docs/matningar/M-121_dubbelskrivning_mot_egna_referenser.md.
Kors som `python3 tests/protocol/kor_m121_uteslutning.py`.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bank import reparationsbank as RB  # noqa: E402

KORPUS = os.path.join(_ROT, "docs", "matningar", "m96_korpus_*.json")


def grind2(u, kropp):
    try:
        kalla = u["skelett"].las_svar(kropp)
    except Exception:
        # En kropp som inte gar in i skelettet (modellen rorde ramen) doms som
        # den ar; den faller pa annat an DUBBELSKRIVNING och raknas inte har.
        kalla = kropp
    dom = u["grindar"][0].doma(kalla)
    text = getattr(dom, "utdata", "") or ""
    return [r.strip() for r in text.splitlines() if re.search(r"\[[A-Z_]+/", r)]


def referenserna():
    poster = RB.uppgifter_med_sparfacit()
    fallda = {}
    for post in poster:
        u = RB.bygg_uppsattning(post)
        rader = grind2(u, u["referens"])
        koder = sorted(set(re.findall(r"\[([A-Z_]+)/", "\n".join(rader))))
        if koder:
            fallda[post["task_id"]] = koder
    return len(poster), fallda


def korpusen():
    poster = dict((p["task_id"], p) for p in RB.uppgifter_med_sparfacit())
    upps = {}
    kroppar = 0
    domar = []
    for f in sorted(glob.glob(KORPUS)):
        d = json.load(open(f, encoding="utf-8"))
        for r in d.get("resultat", []):
            tid = r["uppgift"]
            if tid not in poster:
                continue
            if tid not in upps:
                upps[tid] = RB.bygg_uppsattning(poster[tid])
            for i, kropp in enumerate(r.get("kroppar_per_varv") or []):
                kroppar += 1
                for rad in grind2(upps[tid], kropp):
                    if "DUBBELSKRIVNING" in rad:
                        domar.append((os.path.basename(f), tid, i + 1, rad))
    return kroppar, domar


def main():
    n, fallda = referenserna()
    print("REFERENSER: %d med sparfacit, %d falls av grind 2/3" % (n, len(fallda)))
    for tid, koder in sorted(fallda.items()):
        print("   %s %s" % (tid, koder))
    kroppar, domar = korpusen()
    print("M-96-KORPUS: %d modellskrivna kroppar, %d DUBBELSKRIVNING-domar"
          % (kroppar, len(domar)))
    for fil, tid, varv, rad in domar:
        print("   %s %s varv %d: %s" % (fil, tid, varv, rad[:110]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
