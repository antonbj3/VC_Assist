# -*- coding: utf-8 -*-
"""M-82: hur manga VC-namn hittar en modell pa nar den skriver scenkod?

Fas 4:s grind lovar: "Modellen kan inte anropa ett verktyg eller argument som
inte finns. Matt over N forsok: noll uppfunna namn."

Den matningen gjordes mot VARA EGNA verktygsmallar. En mall som ar skriven av
oss och provad av oss uppfinner inga namn - det ar inte samma sak som att en
modell inte gor det. Grind 4 har aldrig domt en rad kod som en modell skrivit
(M-81).

Den har korningen staller den fragan. Modellen far en scen ur banken - roller,
URI:er, mattsatta katalogposter och kopplingar - och ombeds skriva den Python
som bygger den i VC. Sedan gar koden genom api_index.Validator, som domer varje
VC-namn mot indexets 3444 symboler.

TRE UTFALL, och skillnaden mellan de tva sista ar hela poangen:

  fel            namnet finns bevisligen inte. En hallucination.
  obestambart    namnet gar inte att avgora statiskt - typen ar okand darfor att
                 kedjan gar genom nagot validatorn inte kan folja. INTE ett
                 godkannande (I3), men inte heller ett bevis pa ett pahitt.
  kontrollerade  hur manga namn grinden faktiskt provade. Ett svep som
                 kontrollerar noll namn godkanner allt.

Kors:
    python3 tests/protocol/kor_m82_scenkod.py --svar <katalog> [--json ut.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from vc_assist_svc.api_index import bygg_validator                # noqa: E402


def kor_en(tid, katalog, validator):
    sokvag = os.path.join(katalog, "%s_scen.py" % tid)
    if not os.path.exists(sokvag):
        return {"task_id": tid, "utfall": "inget svar"}
    with open(sokvag, "r", encoding="utf-8") as f:
        kod = f.read()
    g = validator.granska(kod)
    return {
        "task_id": tid,
        "rader": len([r for r in kod.splitlines() if r.strip()]),
        "kontrollerade_namn": g.kontrollerade_namn,
        "fel": [str(x) for x in g.fel],
        "obestambara": [str(x) for x in g.obestambara],
        "godkand": bool(g.godkand),
        "utfall": "godkand" if g.godkand else "underkand",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--svar", required=True)
    p.add_argument("--json")
    a = p.parse_args(argv)

    uppgifter = sorted(f.split("_scen.md")[0] for f in os.listdir(a.svar)
                       if f.endswith("_scen.md"))
    validator = bygg_validator()
    resultat = [kor_en(t, a.svar, validator) for t in uppgifter]

    print("=== M-82: uppfinner modellen VC-namn nar den bygger en scen? ===\n")
    print("  Grind 4 domer varje VC-namn mot API-indexets 3444 symboler.\n")
    print("  %-6s %7s %14s %6s %13s" % ("", "rader", "kontrollerade", "fel",
                                        "obestambara"))
    fel = obest = kontrollerade = 0
    for r in resultat:
        if r["utfall"] == "inget svar":
            print("  %-6s %s" % (r["task_id"], "inget svar"))
            continue
        print("  %-6s %7d %14d %6d %13d"
              % (r["task_id"], r["rader"], r["kontrollerade_namn"],
                 len(r["fel"]), len(r["obestambara"])))
        for x in r["fel"]:
            print("         FEL  %s" % x[:96])
        for x in r["obestambara"][:4]:
            print("         obestambart  %s" % x[:88])
        fel += len(r["fel"])
        obest += len(r["obestambara"])
        kontrollerade += r["kontrollerade_namn"]

    print("\n  UPPFUNNA NAMN: %d" % fel)
    print("  obestambara:   %d" % obest)
    print("  kontrollerade namn totalt: %d" % kontrollerade)
    if kontrollerade == 0:
        print("\n  VARNING: grinden kontrollerade NOLL namn. Ett svep som inte")
        print("  provar nagot godkanner allt, och talet ovan betyder ingenting.")
    elif fel == 0:
        print("\n  Noll uppfunna namn over %d kontrollerade. Fas 4:s lofte haller")
        print("  ocksa mot en modell - inte bara mot vara egna mallar." % kontrollerade)

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"resultat": resultat, "fel": fel,
                       "obestambara": obest,
                       "kontrollerade": kontrollerade}, f, indent=2,
                      ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
