# -*- coding: utf-8 -*-
"""Vilka av grind 2:s fallplatser som ALDRIG fyrar under hela provsviten.

## Varfor korningen finns

`tests/enhet/test_st_semantik.py` bar tolv par - en kalla som faller pa en viss
KOD och en som gar igenom. Det later som tackning, och det ar det inte.

Grind 2 har **68 stallen** i `validator.py` dar den kan falla, och de fordelar
sig ojamnt: `TYP` ensam har 34, `OKANT_NAMN` 9, `ARGUMENT` 6. Ett par per KOD
provar alltsa en av 34 TYP-platser och sager ingenting om de andra 33.

Skillnaden ar inte akademisk. Natten 2026-09-04/05 hittades sju falska
rodgrindar och fyra hal i samma lager (M-99), och en grind som bar MOTSATSEN
till sitt eget faltnamn (`_sekvens`) - alla tolv paren var grona over det felet.
En fallplats som aldrig fyrat ar en fallplats ingen provat.

## Hur den mater

`Validator.fel` lindas med en inspelare som laser anroparens radnummer ur
`sys._getframe(1)`. Sedan kors hela enhetssviten i samma process, sa varje
fallplats som nagot prov nar bokfors med sin rad. Platserna raknas ur koden med
AST - inte med grep, for en regex over kallan hade varit felklassen sjalv.

    python3 tests/protocol/kor_fallplatstackning.py [--json ut.json]
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

BANKPOST = {
    "pastar": "varje stalle dar grind 2 kan falla nas av minst ett prov i "
              "enhetssviten",
    "under_prov": ("svc/vc_assist_svc/st/validator.py",),
    "facit": "de fallplatser som faktiskt fyrar nar hela enhetssviten kors",
    "facitkalla": "en AST-inventering av anropen i kallan, jamford med en "
                  "inspelning av vilka rader som fyrade under sviten",
    "facitkalla_filer": ("tests/enhet",),
    "trasiga_fall": (
        "en fallplats som inget prov nar maste listas, aldrig raknas som tackt",
        "noll fyrade platser maste ge slutkod 2 - en tackning ur noll "
        "observationer ar ingen matning",
    ),
    "kraver": ("inget",),
    "matningar": (),
}

_VALIDATOR = os.path.join(_ROT, "svc", "vc_assist_svc", "st", "validator.py")


def platser_ur_kallan(sokvag):
    """kod -> {radnummer}. Raknat ur AST, aldrig ur en regex."""
    with open(sokvag, "r", encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    ut = collections.defaultdict(set)
    for nod in ast.walk(trad):
        if not isinstance(nod, ast.Call) or not nod.args:
            continue
        f_ = nod.func
        namn = f_.attr if isinstance(f_, ast.Attribute) else getattr(f_, "id", None)
        if namn not in ("fel", "Syntaxfel"):
            continue
        a = nod.args[0]
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            ut[a.value].add(nod.lineno)
    return ut


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    p.add_argument("--vag", default="tests/enhet")
    a = p.parse_args(argv)

    ur_koden = platser_ur_kallan(_VALIDATOR)
    totalt = sum(len(v) for v in ur_koden.values())

    from vc_assist_svc.st import validator as V

    sedda = set()
    original = V.Granskning.fel

    def inspelande(self, kod, rad, text):
        # Anroparens rad, alltsa SJALVA fallplatsen - inte raden i ST-kallan.
        sedda.add((kod, sys._getframe(1).f_lineno))
        return original(self, kod, rad, text)

    V.Granskning.fel = inspelande

    print("=== FALLPLATSTACKNING, grind 2 ===\n")
    print("  stallen i validator.py: %d\n" % totalt)

    import pytest
    kod = pytest.main([os.path.join(_ROT, a.vag), "-q", "--no-header",
                       "-p", "no:randomly", "-p", "no:cacheprovider"])

    V.Granskning.fel = original

    if not sedda:
        # Fail-closed: en tackning ur noll observationer ar ingen matning.
        print("\n  NOLL fallplatser fyrade. Sviten kordes inte, eller "
              "inspelningen kopplades inte in.", file=sys.stderr)
        return 2

    otackta = []
    for k in sorted(ur_koden):
        for rad in sorted(ur_koden[k]):
            if (k, rad) not in sedda:
                otackta.append((k, rad))

    tackta = totalt - len(otackta)
    print("\n  fyrade minst en gang:  %3d av %d  (%.0f %%)"
          % (tackta, totalt, 100.0 * tackta / max(1, totalt)))
    print("  ALDRIG fyrade:         %3d\n" % len(otackta))

    per_kod = collections.Counter(k for k, _r in otackta)
    print("  Otackta per kod:")
    for k, n in per_kod.most_common():
        print("    %-22s %2d av %2d" % (k, n, len(ur_koden[k])))

    print("\n  Otackta stallen, med rad:")
    with open(_VALIDATOR, "r", encoding="utf-8") as f:
        rader = f.read().splitlines()
    for k, rad in otackta[:40]:
        print("    %-20s :%-5d %s" % (k, rad, rader[rad - 1].strip()[:70]))
    if len(otackta) > 40:
        print("    ... och %d till" % (len(otackta) - 40))

    print("\n  Vad talet INTE visar:")
    print("    Att en plats fyrar betyder inte att den fyrar RATT. En falsk")
    print("    rodgrind fyrar precis som en akta - M-99 hittade sju.")
    print("    Bara validator.py. Lexern och lasaren kastar Syntaxfel pa")
    print("    egna stallen som inte raknas har.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"platser": totalt, "tackta": tackta,
                       "otackta": [{"kod": k, "rad": r} for k, r in otackta],
                       "per_kod": {k: {"otackta": n, "totalt": len(ur_koden[k])}
                                   for k, n in per_kod.items()},
                       "provsvit_slutkod": int(kod)}, f, indent=2,
                      ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
