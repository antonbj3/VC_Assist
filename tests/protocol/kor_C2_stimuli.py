# -*- coding: utf-8 -*-
"""C2: stimulusgrinden - nya stimuli for bankens domare, en i taget provade.

Kor C punkt C2 bygger stimuli ur M-134:s klassning: punktkrav dar facit ser
skillnaden men saknar punkten (klass 1-2), nya sekvenser dar stimulusen inte
nar raden (klass 3-6). Varje stimulus provas av `verifiera_stimulus` INNAN den
committas in i uppgiften:

* referensen maste vara gron MED stimulusen - faller den avvisas stimulusen.
  Ett scenario som faller bade mutanten och referensen ar ett facit i
  forkla dnad, inte en stimulus (C2:s trasiga fixtur).
* varje mutant stimulusen ar byggd for maste falla - annars ser den inget.
* en ersatt sekvens far aldrig ta bort ett gammalt steg - grinden far inte
  bli billig. Att lagga TILL sekvenser kan per konstruktion aldrig fa en
  gammal fangst att slappa: domen samlar brister over alla sekvenser.

Korning: python3 tests/protocol/kor_C2_stimuli.py [--json ut.json]
Slutkod 0 nar alla stimuli haller, 2 nar nagot faller.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)
sys.path.insert(0, os.path.dirname(__file__))

BANKPOST = {
    "pastar": "en ny stimulus for bankens domare faller de mutanter den ar "
              "byggd for och referensen forblir gron - en stimulus som faller "
              "referensen avvisas",
    "under_prov": ("bank/domare.py", "svc/vc_assist_svc/st/tolk.py",
                   "svc/vc_assist_svc/plc/mutation.py"),
    "facit": "skadan sjalv (kand textandring) och referensens eget "
             "utgangsspar: mutanten ska falla, referensen bestas",
    "facitkalla": "kand textandring i en referens som redan uppfyller sitt "
                  "handskrivna facit (85_bankkontraktet.md §2 klass 4), och "
                  "referensens utgangsspar under samma stimulus",
    "facitkalla_filer": ("bank/uppgifter",),
    "trasiga_fall": (
        "en stimulus som faller referensen avvisas med slutkod 2 - ett facit "
        "i forkla dnad, inte en stimulus",
        "en stimulus som inte faller nagon av sina mutanter avvisas med "
        "slutkod 2 - den ser inget",
        "en ersatt sekvens som tar bort ett gammalt steg avvisas - grinden "
        "far inte bli billig",
    ),
    "kraver": ("inget",),
    "matningar": ("M-135",),
}

from vc_assist_svc.plc.mutation import skador          # noqa: E402
from bank import domare                                # noqa: E402


def med_sekvens(post, ny_sekvens, ersatt_id=None):
    """Proben: uppgiften med stimulusen inlagd. Ror aldrig `post`."""
    facit = dict(post.get("facit_spar") or {})
    gamla = list(facit.get("sekvenser") or [])
    if ersatt_id is None:
        if any(s.get("id") == ny_sekvens.get("id") for s in gamla):
            raise ValueError("sekvens %r finns redan - anvand ersatt_id"
                             % (ny_sekvens.get("id"),))
        facit["sekvenser"] = gamla + [ny_sekvens]
    else:
        if not any(s.get("id") == ersatt_id for s in gamla):
            raise ValueError("sekvens %r finns inte att ersatta" % (ersatt_id,))
        facit["sekvenser"] = [ny_sekvens if s.get("id") == ersatt_id else s
                              for s in gamla]
    probe = dict(post)
    probe["facit_spar"] = facit
    return probe


def _stegnyckel(steg):
    return (float(steg.get("t_ms", 0.0)),
            json.dumps(steg.get("satt") or {}, sort_keys=True),
            json.dumps(steg.get("krav") or {}, sort_keys=True))


def verifiera_stimulus(post, ny_sekvens, mutanter, ersatt_id=None):
    """Provar en stimulus. Returnerar (ok, skal, detaljer).

    `mutanter` ar ST-kroppar. Tom lista ar fellagt anvand - en stimulus utan
    mutanter att falla provas inte, den pastas.
    """
    if not mutanter:
        return False, "avvisas: inga mutanter att falla", {}
    if ersatt_id is not None:
        gammal = next(s for s in (post.get("facit_spar") or {}).get("sekvenser")
                      or [] if s.get("id") == ersatt_id)
        gamla_steg = set(_stegnyckel(s) for s in gammal.get("steg") or [])
        nya_steg = set(_stegnyckel(s) for s in ny_sekvens.get("steg") or [])
        borttagna = gamla_steg - nya_steg
        if borttagna:
            return False, ("avvisas: ersattningen tar bort %d gamla steg - "
                           "grinden far inte bli billig" % len(borttagna)), {}
    try:
        probe = med_sekvens(post, ny_sekvens, ersatt_id)
    except ValueError as fel:
        return False, "avvisas: %s" % (fel,), {}
    ref = (post.get("facit_spar") or {}).get("referens") or ""
    dref = domare.dom(probe, ref)
    if not dref.godkand:
        return False, ("avvisas: faller referensen (%s) - ett facit i "
                       "fork ladnad, inte en stimulus"
                       % ", ".join(dref.koder[:5])), {"referens_koder": dref.koder}
    fallda, blinda = [], []
    for m in mutanter:
        dm = domare.dom(probe, m)
        (fallda if not dm.godkand else blinda).append(dm.koder)
    if not fallda:
        return False, ("avvisas: ser ingen av %d mutanterna"
                       % len(mutanter)), {}
    return True, ("ok: referensen gron, %d av %d mutanter fallda"
                  % (len(fallda), len(mutanter))), {"fallda": fallda}


def _las_post(task_id):
    with open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % task_id),
              "r", encoding="utf-8") as h:
        return json.load(h)


def _bygg_mutanter(ref, val):
    """Valda mutanter ur motorn: {sort, rad, fore, forekomst}. Forekomst ar
    index bland kandidater med samma (sort, rad, fore) - svepets ordning."""
    ut = []
    for v in val:
        cand = [s for s in skador(ref, per_sort=3)
                if s.sort == v["sort"] and s.rad == v["rad"]
                and s.fore == v["fore"]]
        if len(cand) <= v.get("forekomst", 0):
            return None, ("hittar inte mutanten %s rad %s (%s): %d kandidater"
                          % (v["sort"], v["rad"], v["fore"], len(cand)))
        ut.append(cand[v.get("forekomst", 0)].kropp)
    return ut, ""


# En stimulus per klass ur M-134. Fylls pa klass for klass; korningen
# verifierar dem alla. "lage": "ny" (sekvens + scenariokatalogpost laggs
# till) eller "ersatt:<sekvens-id>" (steg laggs till i befintlig sekvens).
STIMULI = []


def kor_stimulus(defn):
    post = _las_post(defn["uppgift"])
    facit = post.get("facit_spar") or {}
    ref = facit.get("referens") or ""
    mutanter, fel = _bygg_mutanter(ref, defn["mutanter"])
    if mutanter is None:
        return False, fel, {}
    ersatt_id = None
    if defn["lage"].startswith("ersatt:"):
        ersatt_id = defn["lage"].split(":", 1)[1]
    ok, skal, detaljer = verifiera_stimulus(post, defn["sekvens"], mutanter,
                                            ersatt_id)
    if not ok:
        return False, skal, detaljer
    if defn["lage"] == "ny":
        if defn.get("scenario") is None:
            return False, "ny sekvens saknar scenariokatalogpost", detaljer
        ids = [s.get("id") for s in post.get("scenarios") or []]
        if defn["scenario"].get("id") not in ids:
            return False, ("scenariot %r ligger inte i uppgiftens scenarios"
                           % (defn["scenario"].get("id"),)), detaljer
    return True, skal, detaljer


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    a = p.parse_args(argv)
    if not STIMULI:
        print("inga stimuli definierade annu")
        return 0
    daliga = []
    for d in STIMULI:
        ok, skal, _ = kor_stimulus(d)
        print("%-8s %-40s %s" % (d["uppgift"], d["sekvens"].get("id"), skal))
        if not ok:
            daliga.append(d["sekvens"].get("id"))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as h:
            json.dump([dict(uppgift=d["uppgift"], sekvens=d["sekvens"].get("id"))
                       for d in STIMULI], h, ensure_ascii=False, indent=1)
    if daliga:
        print("UNDERKANDA: %s" % ", ".join(daliga), file=sys.stderr)
        return 2
    print("%d stimuli haller" % len(STIMULI))
    return 0


if __name__ == "__main__":
    sys.exit(main())
