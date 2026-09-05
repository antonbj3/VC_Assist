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


def exempel_fran_annan_uppgift(post, alla):
    """En FARDIG, grindgodkand kropp fran en ANNAN uppgift.

    Ett arbetat exempel ar den starkaste hjalpen mot formfel: modellen ser hur
    en godkand kropp ser ut i stallet for att harleda formen ur en regellista.

    Att den kommer fran en annan uppgift ar inte en detalj utan hela
    giltigheten. Uppgiftens EGEN referens ar facit; visas den mater korningen
    hur bra modellen kopierar. Grannens referens delar form och idiom men
    ingen logik, och korningen mater anda kodlikheten mot den egna referensen
    sa att en lackage skulle synas.
    """
    for annan in alla:
        if annan["task_id"] != post["task_id"]:
            return annan["task_id"], RB.bygg_uppsattning(annan)["referens"]
    return None, None


def kor_en(post, lage, modellnamn, max_varv, forhandsregler=True,
           exempel=None):
    upps = RB.bygg_uppsattning(post)
    # A/B:t. Utan forhandsregler far modellen bara uppdraget, precis som fore
    # M-97 - grindarnas kunskap nar den forst NAR den skrivit fel.
    prompt = R.SYSTEMPROMPT if forhandsregler else R._GRUNDPROMPT
    if exempel:
        tid_exempel, kropp_exempel = exempel
        prompt = prompt + (
            "\n\nSa har ser en godkand kropp ut. Den loser en ANNAN uppgift"
            " (%s) - kopiera inte dess logik, bara dess form.\n\n%s\n"
            % (tid_exempel, kropp_exempel))
    slinga = R.Reparationsslinga(upps["skelett"], upps["grindar"],
                                 lage=lage, max_varv=max_varv,
                                 systemprompt=prompt)
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
        "forhandsregler": bool(forhandsregler),
        "exempel_fran": exempel[0] if exempel else None,
        "anrop": modell.anrop,
        "kostnad_usd": round(modell.kostnad_usd, 4),
        "sekunder": round(time.time() - t0, 1),
        # Grindens EGNA ord per varv, sa domen gar att lasa i efterhand.
        "domar_per_varv": [
            [d.utdata[:300] for d in getattr(v, "domar", ())]
            for v in protokoll.varv],
        # ...och KROPPEN som domdes. En dom utan sin kod gar inte att granska:
        # nar TIDLITERAL-domarna visade sig vara var egen falska rodgrind
        # (M-96) fanns modellens kod inte kvar att lasa, sa fyndet fick goras
        # om fran borjan. Det som dommer och det som doms hor ihop.
        "kroppar_per_varv": [getattr(v, "kropp", "") for v in protokoll.varv],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modell", default="sonnet")
    p.add_argument("--lage", default=R.LAGE_RENT, choices=list(R.LAGEN))
    p.add_argument("--uppgift", action="append",
                   help="kor bara den har uppgiften (kan upprepas)")
    p.add_argument("--max-varv", type=int, default=R.MAX_VARV)
    p.add_argument("--utan-forhandsregler", action="store_true",
                   help="ge modellen bara uppdraget, inte grindarnas regler")
    p.add_argument("--exempel", action="store_true",
                   help="lagg en godkand kropp fran en ANNAN uppgift i prompten")
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
    print("  modell: %s   lage: %s   tak: %d varv (M-52)   forhandsregler: %s\n"
          % (a.modell, a.lage, a.max_varv,
             "nej" if a.utan_forhandsregler else "ja"))
    if a.exempel:
        print("  exempel: en godkand kropp fran en ANNAN uppgift ligger i"
              " prompten\n")

    resultat = []
    for post in poster:
        print("  %s ..." % post["task_id"], end="", flush=True)
        try:
            r = kor_en(post, a.lage, a.modell, a.max_varv,
                       forhandsregler=not a.utan_forhandsregler,
                       exempel=exempel_fran_annan_uppgift(post, poster)
                       if a.exempel else None)
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
                       "forhandsregler": not a.utan_forhandsregler,
                       "max_varv": a.max_varv, "resultat": resultat,
                       "lost": len(losta), "slog_i_taket": len(taket),
                       "kostnad_usd": round(kostnad, 4)}, f,
                      indent=2, ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)
    return 0 if not fel else 1


if __name__ == "__main__":
    sys.exit(main())
