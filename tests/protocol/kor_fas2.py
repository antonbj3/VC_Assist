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
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests"))

import celler                                        # noqa: E402
import oga_analys as A                               # noqa: E402
from vc_assist_svc.klient import Klient, BryggFel    # noqa: E402

DEL = "OgaDel"
VERKTYG = "OgaVerktyg"
DRIVARE = "OgaDrivare"


def _bana(cellnamn):
    """Vagpunkter ur den syntetiska cellen, sa facit ar kant i forvag."""
    b, plan = celler.ALLA[cellnamn]()
    rader = b.data()["rows"]
    ut = []
    for r in rader:
        d = r["parts"]["del"]["p"]
        v = r["tools"]["gripper"]["p"]
        ut.append([round(x, 5) for x in (d[0], d[1], d[2], v[0], v[1], v[2])])
    return ut, plan


DRIVSKRIPT = """from vcScript import *

BANA = %(bana)s

def satt(c, x, y, z):
    # translateAbs ar RELATIV i absoluta axlar (matt M-11), sa en absolut
    # position satts som skillnaden mot nuvarande lage.
    m = c.PositionMatrix
    m.translateAbs(x - m.P.X, y - m.P.Y, z - m.P.Z)
    c.PositionMatrix = m

def OnRun():
    app = getApplication()
    d = app.findComponent('%(del)s')
    v = app.findComponent('%(verktyg)s')
    if d is None or v is None:
        return
    for rad in BANA:
        satt(d, rad[0], rad[1], rad[2])
        satt(v, rad[3], rad[4], rad[5])
        delay(0.05)
"""


def _bygg(k, cellnamn):
    """Bygger cellen i VC. Gar via kon - allt detta skriver."""
    bana, plan = _bana(cellnamn)
    kod = (
        "import json\n"
        "app = getApplication()\n"
        "for namn in (%r, %r, %r):\n"
        "    for c in list(app.Components):\n"
        "        if c.Name == namn:\n"
        "            app.deleteComponent(c)\n"
        "d = app.createComponent()\n"
        "d.Name = %r\n"
        "v = app.createComponent()\n"
        "v.Name = %r\n"
        "dr = app.createComponent()\n"
        "dr.Name = %r\n"
        "beh = dr.createBehaviour(VC_SCRIPT, 'bana')\n"
        "beh.Script = SRC\n"
        "print(json.dumps({'byggd': True}))\n"
    ) % (str(DEL), str(VERKTYG), str(DRIVARE),
         str(DEL), str(VERKTYG), str(DRIVARE))
    src = DRIVSKRIPT % {"bana": json.dumps(bana), "del": DEL, "verktyg": VERKTYG}
    # SRC skickas som en egen rad sa den inte behover flykttecknas in i koden
    kod = "SRC = %r\n" % str(src) + kod
    post = k.koa(kod, desc="bygg cellen %s" % cellnamn)
    k.godkann(post["qid"])
    return bana, plan


def _starta_om_simuleringen(k):
    post = k.koa("app = getApplication()\n"
                 "app.getSimulation().reset()\n"
                 "app.startSimulation()\n", desc="starta om simuleringen")
    k.godkann(post["qid"])
    # Bryggan overlever omstarten (sockeln lamnas oppen), men pumpen behover
    # nagra varv innan den ar igang igen.
    for _ in range(60):
        try:
            if k.ping()["tick"] > 0:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def kor_cell(k, cellnamn, langd_s):
    bana, plan = _bygg(k, cellnamn)
    if not _starta_om_simuleringen(k):
        raise RuntimeError("pumpen kom aldrig igang efter omstarten")

    t0 = k.simtid()
    k.oga_start({"template": cellnamn, "parts": [DEL], "tools": [VERKTYG],
                 "rate_hz": 20.0}, simtid=t0)
    time.sleep(langd_s)
    ut = k.oga_stopp()
    if "data" not in ut:
        raise RuntimeError("serien kom inte med i svaret: %r" % ut)
    data = ut["data"]
    # Ogats analys forvantar sig namnen i planen; kartlagg fran VC:s namn.
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
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=os.path.expanduser(
        "~/.wine-vc-test/drive_c/users/anton/vc_assist_token"))
    ap.add_argument("--langd", type=float, default=8.0)
    ap.add_argument("--celler", default=",".join(sorted(FACIT)))
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    k = Klient(port=a.port, tokenfil=a.token, timeout=60.0).anslut()
    utfall = []
    fel = 0
    for namn in a.celler.split(","):
        vantat = FACIT[namn]
        try:
            ut, rapport, text = kor_cell(k, namn, a.langd)
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
                           "saknade": ut["saknade"], "rader": rader})
        except Exception as e:
            fel += 1
            print("  FEL  %-14s %s: %s" % (namn, type(e).__name__, e))
            if isinstance(e, BryggFel) and e.traceback:
                print((e.traceback or "")[-600:])
            utfall.append({"cell": namn, "fel": "%s: %s" % (type(e).__name__, e)})

    print("\n  %d av %d celler domdes enligt facit" % (len(utfall) - fel, len(utfall)))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(utfall, f, indent=2)
    k.stang()
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
