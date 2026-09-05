# -*- coding: utf-8 -*-
"""Vilka moduler som registret kallar PROVADE men som ingen korning ror.

`skuld.moduler_utan_prov` fragar om en provfil NAMNER modulens filnamn. Den
docstringen sager sjalv att kriteriet ar grovt och att ett finare matt vore
battre och dyrare. Den har korningen ar det finare mattet.

Skillnaden ar inte akademisk. M-94 fynd 6 matte 4 497 satser (16 %) i moduler
registret kallar provade som aldrig kors av `pytest tests/enhet`. En modul kan
namnas i ett prov som aldrig importerar den, och en modul kan importeras av ett
prov som bara ror en enda funktion i den.

## Var grinden gar, och varfor den inte har nagon troskel

Grinden fragar bara efter NOLL: registret sager provad, coverage sager att inte
en enda sats kordes. Det ar en motsagelse utan tuningparameter - det finns
ingen procentsats att argumentera om, och alltsa ingen troskel som behover en
matreferens. Allt daremellan rapporteras som en fordelning, utan dom.

    python3 tests/protocol/kor_tackning.py [--json ut.json]
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Ingen modul som skuldregistret kallar provad ar helt okord av "
        "enhetssviten - noll korda satser i en provad modul ar en motsagelse "
        "utan tuningparameter.",
    "under_prov": ("svc/vc_assist_svc/skuld.py",),
    "facit":
        "coverage.py:s satstackning over tests/enhet: for varje modul "
        "registret kallar provad ska antalet korda satser vara storre an noll",
    "facitkalla":
        "coverage.py, ett externt verktyg som mater vilka satser som faktiskt "
        "kordes. Registrets eget matt ar en namnsokning i provfilerna; det "
        "har ar exekveringen.",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "en modul som registret kallar provad men dar noll satser kordes "
        "maste listas som MOTSAGELSE med sitt satsantal",
        "allt daremellan rapporteras som en fordelning utan dom - det finns "
        "ingen matt troskel for 'tillrackligt tackt'",
    ),
    "kraver": ("inget",),
    "matningar": ("M-94",),
}

import argparse
import json
import os
import subprocess
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from vc_assist_svc import skuld                                     # noqa: E402

_KALLOR = ("svc/vc_assist_svc", "install", "ext/vc_addon/vc_assist", "bank")


def mat_tackning(datafil):
    """Kor enhetssviten under coverage och ger {relativ sokvag: (korda, satser)}."""
    miljo = dict(os.environ, COVERAGE_FILE=datafil)
    kallor = ",".join(os.path.join(_ROT, k) for k in _KALLOR)
    k = subprocess.run(
        [sys.executable, "-m", "coverage", "run", "--source", kallor,
         "-m", "pytest", os.path.join(_ROT, "tests", "enhet"),
         "-q", "--no-header", "-p", "no:randomly"],
        cwd=_ROT, env=miljo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    provutfall = k.stdout.decode("utf-8", "replace").strip().splitlines()[-1:]

    jsonfil = datafil + ".json"
    subprocess.run([sys.executable, "-m", "coverage", "json", "-o", jsonfil, "-q"],
                   cwd=_ROT, env=miljo, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    with open(jsonfil, "r", encoding="utf-8") as f:
        d = json.load(f)
    ut = {}
    for sokvag, post in d["files"].items():
        rel = os.path.relpath(os.path.join(_ROT, sokvag), _ROT)
        s = post["summary"]
        ut[rel] = (s["covered_lines"], s["num_statements"])
    return ut, (provutfall[0] if provutfall else "okant")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    p.add_argument("--datafil",
                   default=os.path.join(_ROT, ".coverage-tackning"))
    a = p.parse_args(argv)

    print("=== TACKNING: sager registret provad, kor nagon den? ===\n")
    tackning, provutfall = mat_tackning(a.datafil)
    print("  enhetssviten: %s\n" % provutfall)

    hinkar = skuld.moduler_utan_prov(_ROT)
    utan_prov = set()
    for hink in hinkar.values():
        for post in hink:
            utan_prov.add(post[0] if isinstance(post, (list, tuple)) else post)

    # Registret kallar en modul provad om den INTE ligger i nagon hink.
    pastas_provade = [m for m in sorted(tackning) if m not in utan_prov]

    noll = [(m, tackning[m][1]) for m in pastas_provade
            if tackning[m][0] == 0 and tackning[m][1] > 0]
    satser_totalt = sum(tackning[m][1] for m in pastas_provade)
    korda_totalt = sum(tackning[m][0] for m in pastas_provade)

    print("  moduler registret kallar provade: %d" % len(pastas_provade))
    print("  satser i dem:                     %d" % satser_totalt)
    print("  satser som faktiskt kordes:       %d (%.0f %%)"
          % (korda_totalt, 100.0 * korda_totalt / max(1, satser_totalt)))
    print("\n  MOTSAGELSE - provad enligt registret, noll korda satser: %d"
          % len(noll))
    for m, n in sorted(noll, key=lambda x: -x[1]):
        print("    %-58s %4d satser" % (m, n))

    laga = sorted(((tackning[m][0] / float(tackning[m][1]), m)
                   for m in pastas_provade if tackning[m][1] >= 40),
                  key=lambda x: x[0])[:10]
    print("\n  Lagst tackning (utan dom - det finns ingen matt troskel har):")
    for andel, m in laga:
        print("    %5.0f %%  %s" % (100 * andel, m))

    print("\n  Vad korningen INTE visar:")
    print("    Satstackning, inte grentackning. En kord rad kan ha en")
    print("    ogenomgangen gren i sig.")
    print("    Bara tests/enhet. Moduler som bara tests/protocol ror ser")
    print("    nollade ut har, och det ar med flit - de gar inte att")
    print("    kontrollera pa en ren maskin.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"pastas_provade": len(pastas_provade),
                       "satser": satser_totalt, "korda": korda_totalt,
                       "motsagelser": [{"modul": m, "satser": n} for m, n in noll],
                       "per_modul": {m: {"korda": tackning[m][0],
                                         "satser": tackning[m][1]}
                                     for m in pastas_provade}},
                      f, indent=2, ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
