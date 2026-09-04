# -*- coding: utf-8 -*-
"""M-54: samma ST genom var egen tolk och genom STruC++:s byggda REPL.

Bankens facit doms av `svc/vc_assist_svc/st/tolk.py`. Om tolken har fel om
ST-semantiken har facit fel, och banken mater var egen missuppfattning med stor
precision. Den har korningen ar den ANDRA motorn.

Kors:
    python3 tests/protocol/kor_m54_tolk_mot_strucpp.py --strucpp-cli <sokvag>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st.strucpp_orakel import Orakelfel, Steg, jamfor   # noqa: E402


def _p(namn, deklarationer, kropp):
    return ("PROGRAM %s\nVAR\n%sEND_VAR\n%sEND_PROGRAM\n"
            % (namn, deklarationer, kropp))


# Konstruktionerna som bankens facit faktiskt lutar sig mot. Varje post ar
# (namn, kalla, spar). Sparet ar det som skiljer en riktig provning fran en
# genomlasning: tiden gar, och funktionsblockens minne lever mellan stegen.
FALL = []

FALL.append(("TON fordrojer och haller", _p(
    "P1", "    i : BOOL;\n    q : BOOL;\n    t : TON;\n",
    "    t(IN := i, PT := T#100ms);\n    q := t.Q;\n"),
    [Steg({"i": True}, 1, ("q",)),
     Steg({}, 3, ("q",)),
     Steg({}, 1, ("q",)),          # 5 scan = 100 ms -> ska sla om
     Steg({}, 2, ("q",)),
     Steg({"i": False}, 1, ("q",))]))

FALL.append(("TOF haller kvar", _p(
    "P2", "    i : BOOL;\n    q : BOOL;\n    t : TOF;\n",
    "    t(IN := i, PT := T#60ms);\n    q := t.Q;\n"),
    [Steg({"i": True}, 2, ("q",)),
     Steg({"i": False}, 1, ("q",)),
     Steg({}, 2, ("q",)),
     Steg({}, 2, ("q",))]))

FALL.append(("R_TRIG bara ett scan", _p(
    "P3", "    i : BOOL;\n    q : BOOL;\n    f : R_TRIG;\n",
    "    f(CLK := i);\n    q := f.Q;\n"),
    [Steg({"i": True}, 1, ("q",)),
     Steg({}, 1, ("q",)),
     Steg({"i": False}, 1, ("q",)),
     Steg({"i": True}, 1, ("q",))]))

FALL.append(("F_TRIG pa fallande", _p(
    "P4", "    i : BOOL;\n    q : BOOL;\n    f : F_TRIG;\n",
    "    f(CLK := i);\n    q := f.Q;\n"),
    [Steg({"i": True}, 2, ("q",)),
     Steg({"i": False}, 1, ("q",)),
     Steg({}, 1, ("q",))]))

FALL.append(("CTU raknar flanker", _p(
    "P5", "    i : BOOL;\n    r : BOOL;\n    n : INT;\n    q : BOOL;\n"
          "    c : CTU;\n",
    # IEC 61131-3 kallar CTU:s nollstallning R, inte RESET. Med RESET
    # oversatter STruC++ utan anmarkning men bygget faller, och tolken
    # AVVISAR numera namnet (M-54). Sparet kor det RATTA namnet.
    "    c(CU := i, R := r, PV := 3);\n    n := c.CV;\n    q := c.Q;\n"),
    [Steg({"i": True}, 1, ("n", "q")),
     Steg({"i": False}, 1, ("n", "q")),
     Steg({"i": True}, 1, ("n", "q")),
     Steg({"i": False}, 1, ("n", "q")),
     Steg({"i": True}, 1, ("n", "q")),
     Steg({"r": True}, 1, ("n", "q"))]))

FALL.append(("latch med SR och kvittens", _p(
    "P6", "    larm : BOOL;\n    kvitt : BOOL;\n    q : BOOL;\n    l : SR;\n",
    "    l(S1 := larm, R := kvitt);\n    q := l.Q1;\n"),
    [Steg({"larm": True}, 1, ("q",)),
     Steg({"larm": False}, 2, ("q",)),
     Steg({"kvitt": True}, 1, ("q",)),
     Steg({"kvitt": False}, 1, ("q",))]))

FALL.append(("IF, CASE och raknare tillsammans", _p(
    "P7", "    start : BOOL;\n    steg : INT;\n    ut : BOOL;\n",
    "    IF start THEN\n"
    "        CASE steg OF\n"
    "        0: steg := 1;\n"
    "        1: steg := 2; ut := TRUE;\n"
    "        2: steg := 0; ut := FALSE;\n"
    "        ELSE steg := 0;\n"
    "        END_CASE;\n"
    "    END_IF;\n"),
    [Steg({"start": True}, 1, ("steg", "ut")),
     Steg({}, 1, ("steg", "ut")),
     Steg({}, 1, ("steg", "ut")),
     Steg({}, 1, ("steg", "ut"))]))

FALL.append(("TON som nollstalls av sitt eget villkor", _p(
    "P8", "    i : BOOL;\n    q : BOOL;\n    t : TON;\n",
    # T4 i fas 7:s protokoll: timern nollstalls av sin egen utgang och
    # faller darfor aldrig. Bada motorerna ska visa samma sak.
    "    t(IN := i AND NOT t.Q, PT := T#60ms);\n    q := t.Q;\n"),
    [Steg({"i": True}, 3, ("q",)),
     Steg({}, 3, ("q",)),
     Steg({}, 4, ("q",))]))

FALL.append(("heltalsaritmetik och jamforelser", _p(
    "P9", "    a : INT;\n    b : INT;\n    c : INT;\n    q : BOOL;\n",
    "    c := a * 3 + b / 2;\n    q := c >= 10 AND c <> 12;\n"),
    [Steg({"a": 3, "b": 4}, 1, ("c", "q")),
     Steg({"a": 4, "b": 0}, 1, ("c", "q")),
     Steg({"a": 1, "b": 1}, 1, ("c", "q"))]))

FALL.append(("REAL och blandad aritmetik", _p(
    "P10", "    x : REAL;\n    y : REAL;\n",
    "    y := x * 2.5;\n"),
    [Steg({"x": 2.0}, 1, ("y",)),
     Steg({"x": -1.5}, 1, ("y",))]))


def kor(cli, behall=False):
    rot = tempfile.mkdtemp(prefix="m54_")
    resultat = {"fall": [], "cli": cli}
    try:
        for i, (namn, kalla, spar) in enumerate(FALL):
            post = {"namn": namn}
            try:
                avvik = jamfor(kalla, kalla.split()[1], spar, cli,
                               katalog=os.path.join(rot, "f%02d" % i))
                post["avvikelser"] = [str(a) for a in avvik]
                post["ok"] = not avvik
            except Orakelfel as fel:
                post["orakelfel"] = str(fel)
                post["ok"] = False
            except Exception as fel:
                post["fel"] = "%s: %s" % (type(fel).__name__, fel)
                post["ok"] = False
            resultat["fall"].append(post)
    finally:
        if not behall:
            shutil.rmtree(rot, ignore_errors=True)
    return resultat


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strucpp-cli", required=True)
    p.add_argument("--json")
    a = p.parse_args(argv)

    r = kor(a.strucpp_cli)
    print("=== M-54: tolken mot STruC++ ===\n")
    daliga = 0
    for post in r["fall"]:
        if post.get("ok"):
            print("  OK   %s" % post["namn"])
            continue
        daliga += 1
        print("  FEL  %s" % post["namn"])
        for rad in post.get("avvikelser", []):
            print("         %s" % rad)
        for nyckel in ("orakelfel", "fel"):
            if nyckel in post:
                print("         %s: %s" % (nyckel, post[nyckel]))
    print("\n%d av %d fall overens" % (len(r["fall"]) - daliga, len(r["fall"])))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=2, ensure_ascii=False)
    return 0 if daliga == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
