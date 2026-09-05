# -*- coding: utf-8 -*-
"""M-171: markeringen headless, och scenens sort ur strukturen.

Kors i tva halvor, och de svarar pa olika fragor:

  LEVANDE VC   Finns markeringsytan? Svarar den headless? Ger de tva
               verktygen ratt sort, och ratt markering, i en scen med
               DUBBLETTNAMN? Och hur stor blir ogonblicksbilden av en
               riktig scen?

  FALLBANKEN   Hur manga av de tvetydiga fallen loser markeringen faktiskt
               ut - och, viktigare, loser den nagonsin ut FEL? Den halvan
               kraver ingen VC: den provar tjanstens egen logik over ett
               fullstandigt korsprov av scener och markeringslagen.

    python3 tests/protocol/kor_markering.py            # bada halvorna
    python3 tests/protocol/kor_markering.py --utan-vc  # bara fallbanken

Markeringen ATERSTALLS alltid: sonden satter en markering, laser, och rensar.
Riggen delas med andra sessioner, och en kvarlamnad markering ar en andring av
nagon annans lage.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from vc_assist_svc import verktyg as V                      # noqa: E402
from vc_assist_svc.llm import matt                          # noqa: E402
from vc_assist_svc.scenarbete import avsikt as A            # noqa: E402
from vc_assist_svc.scenarbete import markering as M         # noqa: E402

# Komponenterna sonden markerar i den levande scenen. Valda for att de bar
# OLIKA sort (ST8_Bana ar transportor, ST8A_Don har ingen markor alls), sa att
# provet ser bade en avgjord sort och en okand i samma svar.
LEVANDE_MAL = ("ST8_Bana", "ST8A_Don")

SATT_MARKERING = '''
from __future__ import print_function
import json
import vcScript
app = getApplication()
sm = app.SelectionManager
mal = []
for k in app.Components:
    if k.Name in %r:
        mal.append(k)
sm.setSelection(mal)
valda = sm.getSelection(vcScript.VC_SELECTION_COMPONENT)
print(json.dumps({"satta": [o.Name for o in valda]}))
''' % (list(LEVANDE_MAL),)

RENSA_MARKERING = '''
from __future__ import print_function
import json
import vcScript
sm = getApplication().SelectionManager
sm.clear()
kvar = sm.getSelection(vcScript.VC_SELECTION_COMPONENT)
print(json.dumps({"kvar": [o.Name for o in kvar]}))
'''

# Ytorna sonden fragar efter i formagerapporten, och de deprekerade grannarna
# den provar for att kunna saga VARFOR de inte anvands.
SOND_YTOR = '''
from __future__ import print_function
import json
import vcScript
app = getApplication()
ut = {}
ut["SelectionManager_finns"] = hasattr(app, "SelectionManager")
sm = app.SelectionManager
ut["SelectionManager_anrop"] = sorted(
    [n for n in dir(sm) if not n.startswith("_")])
ut["CurrentSelection"] = repr(app.CurrentSelection)
ut["Selections"] = repr(app.Selections)
ut["VC_SELECTION_COMPONENT"] = repr(vcScript.VC_SELECTION_COMPONENT)
# Beteendetypens VARDE. Fragan M-85 lamnade oppen: ar VC_ONEWAYPATH samma sak
# som filformatets rOneWayPath, eller tva namnrymder?
konst = {}
for n in ("VC_ONEWAYPATH", "VC_TWOWAYPATH", "VC_TRANSPORTNODE",
          "VC_TOOLCONTAINER", "VC_ROBOTCONTROLLER", "VC_RRSROBOTCONTROLLER",
          "VC_CAPACITYCONTROLLER", "VC_BOOLEANSIGNAL", "VC_PYTHONSCRIPT"):
    konst[n] = vcScript.__dict__.get(n)
ut["beteendekonstanter"] = konst
# Ar tva lasningar av samma komponent samma objekt?
a = []
for k in app.Components:
    a.append(k)
b = []
for k in app.Components:
    b.append(k)
if a and b:
    ut["identitet_is"] = (a[0] is b[0])
    ut["identitet_eq"] = (a[0] == b[0])
    ut["identitet_in"] = (b[0] in a)
namn = {}
for k in a:
    namn[k.Name] = namn.get(k.Name, 0) + 1
ut["dubblettnamn"] = dict((n, c) for n, c in namn.items() if c > 1)
print(json.dumps(ut, sort_keys=True))
'''


# --------------------------------------------------------------------------
# Fallbanken: hur manga tvetydiga fall loser markeringen ut?
# --------------------------------------------------------------------------

# Scen A ar den LEVANDE scenens egna sorter, matta genom scene_snapshot.
# Scen B ar brevets eget fall: tre gripdon och en transportor, med namn som
# med flit INTE alla bar ordet - det ar den namnbundenhet M-69 matte.
SCEN_A = (
    ("ST8_Mall", ""), ("ST8_Matare", ""), ("ST8_Bana", "transportor"),
    ("ST8_Mall", ""), ("ST8_Bana2", "transportor"), ("ST8_Mall", ""),
    ("ST8_Mall", ""), ("ST8A_Givare", ""), ("ST8B_Givare", ""),
    ("ST8_Linje", ""), ("ST8A_Don", ""), ("ST8B_Don", ""),
    ("ST8_BromsA", ""), ("ST8_BromsB", ""), ("ST8_Utmatare", ""),
    ("VcAssistBridge", ""), ("Name", ""), ("Name", ""), ("Robot", ""),
    ("P15_7_kropp", ""),
)
SCEN_B = (
    ("ST210_gripdon", "verktyg"), ("GRP_A", "verktyg"),
    ("Gripper_2F_85", "verktyg"), ("ST210_BAND", "transportor"),
    ("ST210_BAND2", "transportor"), ("IRB4600", "robot"),
)
SCENER = (("levande", SCEN_A), ("tre_gripdon", SCEN_B))

# Ordet operatoren sager, per sort. Det ar med flit ETT ord som INTE ar ett
# komponentnamn - det ar hela deixisfallet ("det dar gripdonet").
ORD = {"verktyg": "gripdon", "transportor": "bandet", "robot": "roboten"}


def _bild(scen, markerade):
    return M.Ogonblicksbild(
        [(n, s, i in markerade) for i, (n, s) in enumerate(scen)],
        kalla="scene_snapshot")


def _markeringslagen(scen, sort):
    """Alla markeringslagen som ar VARDA att prova, per tvetydigt fall.

    Namngivna, sa att utfallstabellen gar att lasa som en fraga i taget i
    stallet for som en summa.
    """
    ratt = [i for i, (_n, s) in enumerate(scen) if s == sort]
    fel = [i for i, (_n, s) in enumerate(scen) if s and s != sort]
    okand = [i for i, (_n, s) in enumerate(scen) if not s]
    lagen = [("inget markerat", ())]
    if ratt:
        lagen.append(("en av kandidaterna", (ratt[0],)))
    if len(ratt) >= 2:
        lagen.append(("tva av kandidaterna", tuple(ratt[:2])))
        lagen.append(("alla kandidaterna", tuple(ratt)))
    if fel:
        lagen.append(("en av ANNAN sort", (fel[0],)))
    if okand:
        lagen.append(("en av OKAND sort", (okand[0],)))
    return lagen


def fallbanken():
    """Korsprovet. Returnerar (rader, sammanfattning)."""
    rader = []
    for scennamn, scen in SCENER:
        sorter = sorted(set(s for _n, s in scen if s))
        for sort in sorter:
            kandidatnamn = tuple(n for n, s in scen if s == sort)
            if len(kandidatnamn) < 2:
                continue        # inte tvetydigt: meningen raknar ut det sjalv
            ord_ = ORD.get(sort, sort)
            for lagesnamn, markerade in _markeringslagen(scen, sort):
                bild = _bild(scen, markerade)
                p = A.Avsiktspastaende(
                    A.ANDRING, belagg="byt %s" % ord_, mal=ord_,
                    malbelagg=ord_, malsort=sort)
                dom = A.granska(p, "byt %s" % ord_, bild.scenlage(),
                                markering=bild.markering())
                mdom = M.prova(bild.markering(), kandidatnamn, sort)
                rader.append({
                    "scen": scennamn, "sort": sort, "ord": ord_,
                    "kandidater_ur_meningen": len(kandidatnamn),
                    "markeringslage": lagesnamn,
                    "markerade": [scen[i][0] for i in markerade],
                    "utfall": mdom.utfall,
                    "dom": dom.dom,
                    "kandidater_efter": list(dom.kandidater),
                    "belagg": (dom.markering.belagg
                               if dom.markering is not None else None),
                })
    # Hinkarna ar DISJUNKTA och delas pa markeringens eget utfall. En
    # tidigare version raknade "motsagelse" och "fragan star kvar" som tva
    # hinkar over samma rader, och summan blev da storre an antalet fall -
    # en tabell som inte gar att lagga ihop ar en tabell som inte gar att
    # lasa.
    def _antal(utfall):
        return len([r for r in rader if r["utfall"] == utfall])

    sammanfattning = {
        "tvetydiga_fall": len(rader),
        "AVGJORD_markeringen_loste_ut": _antal(M.AVGJORD),
        "SMALNAD_farre_kandidater": _antal(M.SMALNAD),
        "MOTSAGELSE_annan_sort_markerad": _antal(M.MOTSAGELSE),
        "SAKNAS_inget_markerat": _antal(M.SAKNAS),
        "OVIDKOMMANDE_bar_ingen_upplysning": _antal(M.OVIDKOMMANDE),
        "domar_utan_fraga": len([r for r in rader if r["dom"] != A.FRAGA]),
    }
    summa = sum(sammanfattning[k] for k in sammanfattning
                if k.split("_")[0] in M.UTFALL)
    if summa != len(rader):
        raise AssertionError(
            "hinkarna summerar till %d men fallen ar %d; de ar inte "
            "disjunkta" % (summa, len(rader)))
    return rader, sammanfattning


def sakerhetsprovet(rader):
    """Loser markeringen NAGONSIN ut fel? Det ar den enda fraga som betyder
    nagot om den gar at fel hall.

    Tre krav, och alla tre provas pa VARJE utlost rad:
      1. det utlosta malet ar MARKERAT
      2. det ar av den sort meningen namnde
      3. det bar ett belagg som namner bade markeringen och komponenten
    """
    brott = []
    for r in rader:
        if r["dom"] == A.FRAGA:
            # En fraga far aldrig ha FLER kandidater an meningen gav.
            if len(r["kandidater_efter"]) > r["kandidater_ur_meningen"]:
                brott.append("%s/%s/%s: markeringen LA TILL kandidater"
                             % (r["scen"], r["sort"], r["markeringslage"]))
            continue
        if len(r["kandidater_efter"]) != 1:
            brott.append("%s/%s/%s: utlost men %d kandidater kvar"
                         % (r["scen"], r["sort"], r["markeringslage"],
                            len(r["kandidater_efter"])))
            continue
        valt = r["kandidater_efter"][0]
        if valt not in r["markerade"]:
            brott.append("%s/%s/%s: loste ut %s som INTE ar markerad"
                         % (r["scen"], r["sort"], r["markeringslage"], valt))
        if not r["belagg"] or valt not in r["belagg"]:
            brott.append("%s/%s/%s: %s utlost utan belagg som namner den"
                         % (r["scen"], r["sort"], r["markeringslage"], valt))
    return brott


# --------------------------------------------------------------------------
# Levande VC
# --------------------------------------------------------------------------

def levande(port, token):
    from vc_assist_svc.klient import Klient
    from vc_assist_svc.tokenplats import tokenfil

    k = Klient(port=port, tokenfil=token or tokenfil(), timeout=120.0).anslut()
    ut = {}
    try:
        sv = k.anrop("exec", {"code": SOND_YTOR, "timeout_ms": 20000},
                     rasa=False)
        if not sv.get("ok"):
            raise RuntimeError("ytsonden foll: %r" % (sv.get("error"),))
        ut["ytor"] = sv["result"]

        post = k.anrop("exec_queue", {"code": SATT_MARKERING,
                                      "desc": "M-171: satt markering"})["result"]
        svar = k.godkann_och_vanta(post["qid"], timeout=60)
        if svar["state"] != "done":
            raise RuntimeError("kunde inte satta markering: %s" % svar["state"])
        ut["satta"] = (((svar.get("svar") or {}).get("result") or {})
                       .get("result") or {})

        for namn in ("get_selection", "scene_snapshot"):
            kod = V.CODE_GEN_HANDLERS[namn]({})
            sv = k.anrop("exec", {"code": kod, "timeout_ms": 20000},
                         rasa=False)
            if not sv.get("ok"):
                raise RuntimeError("%s foll i VC: %r" % (namn, sv.get("error")))
            ut[namn] = sv["result"]
            ut[namn + "_ms"] = sv.get("elapsed_ms")
            # Svaret maste halla verktygets egen returdeklaration.
            V.validera_resultat(V.REGISTER[namn], sv["result"])
    finally:
        try:
            post = k.anrop("exec_queue",
                           {"code": RENSA_MARKERING,
                            "desc": "M-171: rensa markering"})["result"]
            svar = k.godkann_och_vanta(post["qid"], timeout=60)
            ut["rensad"] = (((svar.get("svar") or {}).get("result") or {})
                            .get("result") or {})
        finally:
            k.stang()
    return ut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=None)
    ap.add_argument("--utan-vc", action="store_true")
    ap.add_argument("--ut", default=os.path.join(
        _ROT, "docs", "matningar", "radata", "m171_markeringen.json"))
    a = ap.parse_args()

    rapport = {}

    rader, sammanfattning = fallbanken()
    brott = sakerhetsprovet(rader)
    rapport["fallbank"] = {"rader": rader, "sammanfattning": sammanfattning,
                           "sakerhetsbrott": brott}
    print("FALLBANKEN")
    for nyckel, varde in sorted(sammanfattning.items()):
        print("  %-28s %s" % (nyckel, varde))
    print("  %-28s %s" % ("sakerhetsbrott",
                          brott if brott else "0 (inget fall loste ut fel)"))

    if not a.utan_vc:
        print("\nLEVANDE VC")
        lev = levande(a.port, a.token)
        rapport["levande"] = lev
        bild = M.ogonblicksbild_ur_svar(lev["scene_snapshot"])
        m = bild.matt()
        rapport["bildens_storlek"] = {
            "komponenter": bild.antal(), "markerade": len(bild.markering()),
            "byte": m.byte, "tecken": m.tecken, "tokens": m.tokens,
            "tokens_ur_byte": m.tokens_ur_byte,
            "tokens_ur_tecken": m.tokens_ur_tecken,
            "tak_tokens": M.TAK_TOKENS, "ryms": bild.ryms(),
            "text": bild.text(),
        }
        print("  markerade enligt get_selection: %s"
              % [p["name"] for p in lev["get_selection"]["selected"]])
        print("  scene_snapshot: %d komponenter, %d markerade, %d ms"
              % (lev["scene_snapshot"]["antal"],
                 lev["scene_snapshot"]["markerade"],
                 lev.get("scene_snapshot_ms", -1)))
        print("  markeringen aterstalld: %s" % (lev["rensad"],))
        print("\n  OGONBLICKSBILDEN, %d komponenter:" % bild.antal())
        for rad in bild.text().splitlines():
            print("    " + rad)
        print("\n  storlek: %s" % m.rad())
        print("  tak: %d tokens (%s)"
              % (M.TAK_TOKENS, "ryms" if bild.ryms() else "FOR STOR"))

    mapp = os.path.dirname(a.ut)
    if mapp and not os.path.isdir(mapp):
        os.makedirs(mapp)
    with open(a.ut, "w") as f:
        json.dump(rapport, f, indent=1, sort_keys=True)
    print("\nskrev %s" % a.ut)
    return 1 if brott else 0


if __name__ == "__main__":
    sys.exit(main())
