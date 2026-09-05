# -*- coding: utf-8 -*-
"""Fas 9, den oppna punkten: reparationsslingan driven av en RIKTIG modell.

`tests/protocol/fas9_banken.md` star oppen pa en enda mening:

    "Slingan drevs for hand. Bryggan mellan grind och modell ar ett meddelande,
     inte ett API-anrop. Det finns ingen nyckel och ingen modellklient i repot.
     M-52:s tak pa fyra varv ar darmed oprovat med en riktig modell."

Talen var matta; satten de togs fram pa var det inte. Den har korningen stanger
just det: `Reparationsslinga.kor` tar en `Modell` som inparameter och har alltid
gjort det - vad som saknades var en modell att ge den.

Vad korningen mater, och det ar tva olika saker:

  varv till lost     hur manga varv modellen behovde per uppgift. Talet fanns
                     forut bara for ETT varv, relaat for hand.
  taket              om nagon uppgift slog i M-52:s tak pa fyra varv. Ett tak
                     som aldrig provats ar ett pastaende.

Kostnaden rapporteras per uppgift. Ett tak pa fyra varv sager ingenting om vad
fyra varv kostar, och den som ska kora banken behover veta det.

    python3 tests/protocol/kor_fas9_slingan.py [--modell sonnet] [--lage rent]
                                               [--uppgift H-04] [--json ut.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from bank import reparationsbank as RB                              # noqa: E402
from vc_assist_svc import modellklient                              # noqa: E402
from vc_assist_svc.claudeadapter import ClaudeModell        # noqa: E402
from vc_assist_svc.plc import reparation as R                       # noqa: E402


def kor_en(post, lage, modellnamn, max_varv):
    upps = RB.bygg_uppsattning(post)
    slinga = R.Reparationsslinga(upps["skelett"], upps["grindar"],
                                 lage=lage, max_varv=max_varv)
    modell = ClaudeModell(modell=modellnamn)
    t0 = time.time()
    protokoll = slinga.kor(modell, upps["prompt"], uppgift=post["task_id"])
    return {
        "uppgift": post["task_id"],
        "lage": lage,
        "utfall": protokoll.utfall,
        "lost": bool(protokoll.lost),
        "varv_korda": len(protokoll.varv),
        "varv_till_lost": protokoll.varv_till_lost,
        "slog_i_taket": len(protokoll.varv) >= max_varv and not protokoll.lost,
        "max_varv": max_varv,
        "anrop": modell.anrop,
        "kostnad_usd": round(modell.kostnad_usd, 4),
        "sekunder": round(time.time() - t0, 1),
        # Grindens EGNA ord per varv, sa domen gar att lasa i efterhand.
        "domar_per_varv": [
            [d.utdata[:300] for d in getattr(v, "domar", ())]
            for v in protokoll.varv],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modell", default="sonnet")
    p.add_argument("--lage", default=R.LAGE_RENT, choices=list(R.LAGEN))
    p.add_argument("--uppgift", action="append",
                   help="kor bara den har uppgiften (kan upprepas)")
    p.add_argument("--max-varv", type=int, default=R.MAX_VARV)
    p.add_argument("--json")
    a = p.parse_args(argv)

    if modellklient.standardklient(a.modell) is None:
        # Fail-closed. En korning som tyst faller tillbaka pa en attrapp skulle
        # rapportera attrappens tal som en modells.
        print("INGEN MODELLKLIENT. `claude` finns inte i PATH, och den har\n"
              "korningen far inte falla tillbaka pa en attrapp - da vore talen\n"
              "attrappens och inte en modells.", file=sys.stderr)
        return 2

    poster = RB.uppgifter_med_sparfacit()
    if a.uppgift:
        valda = set(a.uppgift)
        poster = [x for x in poster if x["task_id"] in valda]
    if not poster:
        print("inga uppgifter valda", file=sys.stderr)
        return 2

    print("=== FAS 9: reparationsslingan driven av en riktig modell ===\n")
    print("  modell: %s   lage: %s   tak: %d varv (M-52)\n"
          % (a.modell, a.lage, a.max_varv))

    resultat = []
    for post in poster:
        print("  %s ..." % post["task_id"], end="", flush=True)
        try:
            r = kor_en(post, a.lage, a.modell, a.max_varv)
        except Exception as e:                          # noqa: BLE001
            r = {"uppgift": post["task_id"], "lage": a.lage,
                 "utfall": "KORNINGSFEL", "lost": False, "fel": repr(e),
                 "varv_korda": 0, "varv_till_lost": None,
                 "slog_i_taket": False, "kostnad_usd": 0.0}
            print(" FEL: %r" % e)
        else:
            print(" %s efter %d varv, %.3f USD, %.0f s"
                  % (r["utfall"], r["varv_korda"], r["kostnad_usd"],
                     r["sekunder"]))
        resultat.append(r)

    losta = [r for r in resultat if r["lost"]]
    taket = [r for r in resultat if r.get("slog_i_taket")]
    fel = [r for r in resultat if r["utfall"] == "KORNINGSFEL"]
    kostnad = sum(r.get("kostnad_usd") or 0.0 for r in resultat)

    print("\n  %-22s %s" % ("lost:", "%d av %d" % (len(losta), len(resultat))))
    if losta:
        varv = [r["varv_till_lost"] for r in losta]
        print("  %-22s %s  (median %s)"
              % ("varv till lost:", varv, sorted(varv)[len(varv) // 2]))
    print("  %-22s %d av %d" % ("slog i taket:", len(taket), len(resultat)))
    print("  %-22s %.3f USD" % ("kostnad:", kostnad))
    if fel:
        print("  %-22s %d - talen ovan ar INTE hela banken"
              % ("korningsfel:", len(fel)))

    print("\n  Vad korningen INTE visar:")
    print("    n = 1 per uppgift. Ingen upprepning, ingen spridning.")
    print("    Fyra uppgifter av 51 - bara de har sparfacit.")
    print("    Domen kommer ur var ST-tolk, inte ur OpenPLC.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"modell": a.modell, "lage": a.lage,
                       "max_varv": a.max_varv, "resultat": resultat,
                       "lost": len(losta), "slog_i_taket": len(taket),
                       "kostnad_usd": round(kostnad, 4)}, f,
                      indent=2, ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)
    return 0 if not fel else 1


if __name__ == "__main__":
    sys.exit(main())
