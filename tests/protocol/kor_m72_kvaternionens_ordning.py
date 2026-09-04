# -*- coding: utf-8 -*-
"""M-72: avgor kvaternionens ordning pa alla tre axlarna, inte bara en.

M-11 slog fast att VC ger kvaternionen skalar-forst:

    (x, y, z, w) = (q.Y, q.Z, q.W, q.X)

och `ext/vc_addon/vc_assist/oga_provtagning.kvat_fran_vc` star pa den tabellen.

MEN M-70 fann att M-11 matte pa en enda axel: ren gir kring Z. I varje matpunkt
dar ar `q.Y = 0` och `q.Z = 0` - alltsa exakt de tva komponenter tabellen
flyttar till x och y. Datan visar att `q.X` bar skalaren och att Z-komponenten
hamnar i `q.W`. Den sager ingenting om vilken av `q.Y` och `q.Z` som ar x
respektive y.

Ett fel dar ar inte kosmetiskt: en oror detalj blir en vridning, och ogats
CARRY SLIPPING faller pa varje korning med en orsak som ser ut att sitta i
scenen.

## Provet

Tre RENA rotationer, en per axel, med TRE OLIKA vinklar. Olika vinklar ar inte
pynt: med samma vinkel pa alla tre gar en forvaxling mellan tva axlar inte att
se, eftersom talen da ar identiska.

For en rotation theta kring enhetsaxeln (ax, ay, az) galler, skalar-forst:

    q = (cos(theta/2), ax*sin(theta/2), ay*sin(theta/2), az*sin(theta/2))

Provet raknar det vantade vardet sjalv och jamfor komponent for komponent.
Facit kommer alltsa ur matematiken, inte ur VC - annars hade provet fragat VC
vad VC tycker och fatt ja.

Kors mot en levande brygga (LASANDE, ingen scenandring):
    python3 tests/protocol/kor_m72_kvaternionens_ordning.py [--json ut.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.klient import Klient                       # noqa: E402
from vc_assist_svc.tokenplats import tokenfil                 # noqa: E402

# Tre olika vinklar, en per axel. Samma vinkel pa alla tre hade gjort en
# forvaxling mellan X och Y osynlig.
VINKLAR = {"X": 30.0, "Y": 50.0, "Z": 70.0}

KOD = r'''
import json
import vcMatrix          # MATT: vcMatrix ligger INTE i bryggans exec-globaler.
                         # Modulen har exakt ett namn, new(), och det racker.

ut = {"matningar": []}

for axel, grader in (("X", %(gx)f), ("Y", %(gy)f), ("Z", %(gz)f)):
    m = vcMatrix.new()
    m.identity()
    if axel == "X":
        m.rotateAbsX(grader)
    elif axel == "Y":
        m.rotateAbsY(grader)
    else:
        m.rotateAbsZ(grader)
    q = m.getQuaternion()
    ut["matningar"].append({
        "axel": axel, "grader": grader,
        "q_X": round(q.X, 9), "q_Y": round(q.Y, 9),
        "q_Z": round(q.Z, 9), "q_W": round(q.W, 9),
        "wpr": [round(v, 6) for v in (m.WPR.X, m.WPR.Y, m.WPR.Z)],
    })

print(json.dumps(ut))
''' % {"gx": VINKLAR["X"], "gy": VINKLAR["Y"], "gz": VINKLAR["Z"]}


def vantat(axel, grader):
    """Facit ur matematiken, skalar-forst: (s, vx, vy, vz)."""
    h = math.radians(grader) / 2.0
    s, v = math.cos(h), math.sin(h)
    return {"skalar": s,
            "vx": v if axel == "X" else 0.0,
            "vy": v if axel == "Y" else 0.0,
            "vz": v if axel == "Z" else 0.0}


def _dom(resultat):
    """Vilken VC-komponent bar vilken storhet? Svaret lases ur talen."""
    print("=== M-72: kvaternionens ordning, alla tre axlarna ===\n")
    print("  %-5s %7s  %10s %10s %10s %10s" % ("axel", "grader", "q.X", "q.Y", "q.Z", "q.W"))
    tilldelning = {}
    fel = 0
    for m in resultat["matningar"]:
        v = vantat(m["axel"], m["grader"])
        print("  %-5s %7.1f  %10.6f %10.6f %10.6f %10.6f"
              % (m["axel"], m["grader"], m["q_X"], m["q_Y"], m["q_Z"], m["q_W"]))
        print("        vantat: skalar %.6f, vektorkomponent %.6f pa axel %s"
              % (v["skalar"], max(v["vx"], v["vy"], v["vz"]), m["axel"]))
        # Vilken komponent bar skalaren, och vilken bar vektordelen?
        komp = {"q.X": m["q_X"], "q.Y": m["q_Y"], "q.Z": m["q_Z"], "q.W": m["q_W"]}
        bar_skalar = [k for k, x in komp.items() if abs(x - v["skalar"]) < 1e-6]
        vektorvarde = max(v["vx"], v["vy"], v["vz"])
        bar_vektor = [k for k, x in komp.items()
                      if abs(x - vektorvarde) < 1e-6 and k not in bar_skalar]
        print("        skalaren i: %s | axelns vektorkomponent i: %s"
              % (", ".join(bar_skalar) or "INGEN", ", ".join(bar_vektor) or "INGEN"))
        if len(bar_skalar) != 1 or len(bar_vektor) != 1:
            print("        FEL: gar inte att avgora entydigt")
            fel += 1
        else:
            tilldelning[m["axel"]] = (bar_skalar[0], bar_vektor[0])
        print()

    print("  Sa har ligger de:")
    for axel in ("X", "Y", "Z"):
        if axel in tilldelning:
            print("    varldsaxel %s -> %s   (skalaren i %s)"
                  % (axel, tilldelning[axel][1], tilldelning[axel][0]))

    pastatt = {"X": "q.Y", "Y": "q.Z", "Z": "q.W"}
    stammer = all(tilldelning.get(a, (None, None))[1] == pastatt[a]
                  for a in ("X", "Y", "Z"))
    print("\n  M-11 pastar (x, y, z, w) = (q.Y, q.Z, q.W, q.X).")
    if stammer:
        print("  BEKRAFTAT pa alla tre axlarna.")
    else:
        print("  MOTBEVISAT. kvat_fran_vc i oga_provtagning.py star pa fel tabell.")
        fel += 1
    return fel


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=8901)
    p.add_argument("--token")
    p.add_argument("--json")
    a = p.parse_args(argv)

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=60.0).anslut()
    svar = k.kor(KOD)
    # MATT: bryggan tolkar utskriven JSON och lagger den i "result". Blir det
    # ingen JSON star den kvar i "stdout". Bada vagarna lases, i den ordningen -
    # att bara lasa den ena hade gett "inget svar" nar svaret faktiskt kom fram.
    resultat = svar.get("result")
    if not isinstance(resultat, dict) or "matningar" not in resultat:
        ut = (svar.get("stdout") or "") if isinstance(svar, dict) else ""
        try:
            resultat = json.loads(ut.strip().splitlines()[-1])
        except (ValueError, IndexError, AttributeError):
            print("bryggan svarade utan lasbart resultat: %s"
                  % json.dumps(svar)[:400])
            return 2
    fel = _dom(resultat)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(resultat, f, indent=2, ensure_ascii=False)
    print("\n%s" % ("ORDNINGEN AR AVGJORD" if fel == 0
                    else "%d FEL - se ovan" % fel))
    return 0 if fel == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
