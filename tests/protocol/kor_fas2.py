# -*- coding: utf-8 -*-
"""L3: fas 2:s grind mot en KORANDE VC.

70_faser.md: "Pa en handbyggd bra och en handbyggd trasig cell: ogats dom
matchar facit i bada. Trasig cell MASTE fallas."

Cellerna byggs i VC:s riktiga scengraf: tva komponenter och ett drivskript som
flyttar dem. Ogat provtar genom bryggan och laser vcNode.WorldPositionMatrix -
alltsa samma vag som en riktig cell skulle ge.

    python3 tests/protocol/kor_fas2.py
"""
import argparse
import json
import math
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests"))

import celler                                        # noqa: E402
import oga_analys as A                               # noqa: E402
from vc_assist_svc.guldgrind import Guldgrind, FORGRINDAR   # noqa: E402
from vc_assist_svc.klient import Klient, BryggFel    # noqa: E402
from vc_assist_svc.tokenplats import tokenfil        # noqa: E402

DEL = "OgaDel"
VERKTYG = "OgaVerktyg"
DRIVARE = "OgaDrivare"


def _bana(cellnamn):
    """Vagpunkter ur den syntetiska cellen, sa facit ar kant i forvag.

    Varje punkt ar [x, y, z, gir_i_grader] per objekt.
    """
    b, plan = celler.ALLA[cellnamn]()
    rader = b.data()["rows"]
    punkter = []
    for r in rader:
        d = r["parts"]["del"]
        v = r["tools"]["gripper"]
        punkter.append([_punkt(d), _punkt(v)])
    return punkter, plan


def _punkt(pose):
    """[x, y, z, gir] ur en pose. Giren tas ur kvaternionens z-komponent."""
    p = pose["p"]
    q = pose["q"]
    gir = math.degrees(2.0 * math.atan2(q[2], q[3]))
    return [round(p[0], 5), round(p[1], 5), round(p[2], 5), round(gir, 4)]


def _bygg(k, cellnamn):
    """Bygger cellen i VC. Bara komponenter - INGA skriptbeteenden.

    M-13: createBehaviour(VC_SCRIPT) ar den enda operation som stoppar
    simuleringen och dodar pumpen. Rorelsen drivs darfor av pumpen sjalv
    genom en bana, inte av ett eget drivskript.
    """
    punkter, plan = _bana(cellnamn)
    kod = (
        "import json\n"
        "app = getApplication()\n"
        "namn = [%r, %r]\n"
        "for c in list(app.Components):\n"
        "    if c.Name in namn:\n"
        "        app.deleteComponent(c)\n"
        "for n in namn:\n"
        "    c = app.createComponent()\n"
        "    c.Name = n\n"
        "print(json.dumps({'byggd': True}))\n"
    ) % (str(DEL), str(VERKTYG))
    post = k.koa(kod, desc="bygg cellen %s" % cellnamn)
    ut = k.godkann_och_vanta(post["qid"], timeout=30)
    if ut["state"] != "done":
        raise RuntimeError("cellbygget gav %s: %r" % (ut["state"], ut.get("svar")))
    return punkter, plan


def kor_cell(k, cellnamn, marginal_s=3.0):
    punkter, plan = _bygg(k, cellnamn)
    t0 = k.simtid()
    k.oga_start({"template": cellnamn, "parts": [DEL], "tools": [VERKTYG],
                 "rate_hz": 20.0}, simtid=t0,
                bana={"objekt": [DEL, VERKTYG], "dt": 0.05, "punkter": punkter})
    langd = len(punkter) * 0.05 + marginal_s
    time.sleep(langd)
    ut = k.oga_stopp()
    if "data" not in ut:
        raise RuntimeError("serien kom inte med i svaret: %r" % ut)
    data = ut["data"]
    # Ogats analys forvantar sig planens namn; kartlagg fran VC:s namn.
    for rad in data["rows"]:
        if DEL in rad.get("parts", {}):
            rad["parts"]["del"] = rad["parts"].pop(DEL)
        if VERKTYG in rad.get("tools", {}):
            rad["tools"]["gripper"] = rad["tools"].pop(VERKTYG)
    data["tracked"]["parts"] = ["del"]
    data["tracked"]["tools"] = ["gripper"]
    text, rapport, analys = A.doma(data, plan)
    return ut, rapport, text


FACIT = {
    "bra": "PASS",
    "teleport": "FAIL",
    "glider": "FAIL",
    "fel_placerad": "FAIL",
    "tappad": "FAIL",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    # Ingen standardsokvag. Den gamla ("~/.wine-vc-test/drive_c/users/anton/
    # vc_assist_token") bar tre antaganden som alla ar falska pa Windows: att
    # det finns ett wine-prefix, vad det heter, och vad anvandaren heter.
    ap.add_argument("--token", default=None,
                    help="tokenfilen. Utan flaggan soks den upp; se "
                         "vc_assist_svc.tokenplats")

    ap.add_argument("--celler", default=",".join(sorted(FACIT)))
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=60.0).anslut()
    utfall = []
    fel = 0
    for namn in a.celler.split(","):
        vantat = FACIT[namn]
        try:
            ut, rapport, text = kor_cell(k, namn)
            dom = rapport.dom[0]
            ok = (dom == vantat)
            rader = [r for _s, rr in rapport.sektioner for r in rr]
            viktigt = [r for r in rader
                       if r.startswith(("GRIP", "CARRY", "PLACE")) or "VIOLATION" in r]
            print("  %s %-14s facit=%-4s dom=%-13s prov=%d  %s"
                  % ("OK  " if ok else "FEL ", namn, vantat, dom,
                     ut["samples"], " | ".join(viktigt)[:88]))
            if not ok:
                fel += 1
                print("       orsak: %s" % rapport.dom[1])
            utfall.append({"cell": namn, "facit": vantat, "dom": dom, "ok": ok,
                           "prov": ut["samples"], "rate_hz": ut["rate_hz"],
                           "saknade": ut["saknade"], "rader": rader,
                           "eyes": text})
        except Exception as e:
            fel += 1
            print("  FEL  %-14s %s: %s" % (namn, type(e).__name__, e))
            if isinstance(e, BryggFel) and e.traceback:
                print((e.traceback or "")[-600:])
            utfall.append({"cell": namn, "fel": "%s: %s" % (type(e).__name__, e)})

    print("\n  %d av %d celler domdes enligt facit" % (len(utfall) - fel, len(utfall)))

    # FAS 3: guldgrinden mot ogats VERKLIGA utdata, inte syntetiska rapporter.
    grind = Guldgrind({"cell"})
    grona = [c for c in utfall if c.get("eyes") and c.get("dom") == "PASS"]
    alla = [c for c in utfall if c.get("eyes")]

    def _grindcell(c):
        return {"namn": c["cell"], "klass": "cell", "eyes": c["eyes"],
                "forgrindar": dict((g, True) for g in FORGRINDAR)}

    print("\n  guldgrinden mot ogats verkliga utdata:")
    if grona:
        b = grind.doma([_grindcell(c) for c in grona])
        print("    bara de grona (%d st): %s" % (len(grona), b.text()))
        if not b.guld:
            fel += 1
    if len(alla) > len(grona):
        b = grind.doma([_grindcell(c) for c in alla])
        print("    alla %d cellerna:        %s" % (len(alla), b.text()))
        if b.guld:
            print("    FEL: guld trots en fallen cell")
            fel += 1
    if a.json:
        with open(a.json, "w") as f:
            json.dump(utfall, f, indent=2)
    k.stang()
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
