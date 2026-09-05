#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-85, andra halvan: svarar databladet pa det M-84 lamnade oppet?

M-84 slutade med fyra namngivna osakerheter. Den har korningen staller dem som
FRAGOR TILL DET LEVERERADE VERKTYGET (tests/protocol/stod/slaupp.py, samma
underprocess en modell skulle anropa) och raknar hur manga som far ett svar.

Poangen ar inte att verktyget finns. Poangen ar om de NAMNGIVNA halen stangdes,
och de tva som INTE stangdes ska synas lika tydligt som de tva som gjorde det.

Kors med
    nice -n 19 ionice -c3 python3 tests/protocol/kor_m85_halen_ur_m84.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(HAR, "..", ".."))
SLAUPP = os.path.join(HAR, "stod", "slaupp.py")
sys.path.insert(0, os.path.join(ROT, "svc"))

# M-84:s tre scener och de komponenter de bygger med, lasta ur uppgifterna.
SCENER = ("T-90", "S-03", "L-05")


def _fraga(*argv):
    k = subprocess.run([sys.executable, SLAUPP] + list(argv),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       cwd=ROT, timeout=300)
    try:
        return json.loads(k.stdout.decode("utf-8"))
    except ValueError:
        return {"_oparsbart": k.stdout.decode("utf-8")[:400]}


def _uris(o, ut):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and v.startswith("bank://"):
                ut.add(v)
            _uris(v, ut)
    elif isinstance(o, list):
        for x in o:
            _uris(x, ut)


def main():
    uppgifter = {}
    alla_uris = set()
    for scen in SCENER:
        with open(os.path.join(ROT, "bank", "uppgifter", "%s.json" % scen),
                  encoding="utf-8") as f:
            d = json.load(f)
        u = set()
        _uris(d, u)
        uppgifter[scen] = sorted(u)
        alla_uris |= u
    alla_uris = sorted(alla_uris)

    with open(os.path.join(ROT, "bank", "katalog_index.json"),
              encoding="utf-8") as f:
        bank = {p["uri"]: p for p in json.load(f)["poster"]}

    print("M-84:s tre scener bygger med %d olika bank-komponenter." % len(alla_uris))
    for scen in SCENER:
        print("  %-6s %d st" % (scen, len(uppgifter[scen])))

    # ---- HAL 2: bank://-URI:erna gar inte att verifiera genom indexet -------
    print("\n=== HAL 2: bank://-URI:erna ===")
    ok = 0
    for uri in alla_uris:
        svar = _fraga("bank", uri)
        traff = bool(svar.get("found"))
        ok += traff
        if not traff:
            print("  EJ VERIFIERAD: %s" % uri)
    print("  %d av %d URI:er verifierade genom `slaupp.py bank <uri>`"
          % (ok, len(alla_uris)))
    påhittad = _fraga("bank", "bank://robot/finns_inte_alls")
    print("  en pahittad URI ger found=%s med %d verkliga alternativ"
          % (påhittad.get("found"), len(påhittad.get("alternativ") or [])))

    # ---- HAL 1 och 3: egenskapsnamn och VILKEN boolsk signal ---------------
    #
    # Fragan stalls mot BIBLIOTEKET, och forsta ledet ar om bankposten
    # overhuvudtaget gar att sla upp dar. Det ledet ar sjalv ett matt.
    print("\n=== HAL 1 och 3: egenskapsnamn och signalnamn ===")
    print("Steg 1 - gar bankposten att sla upp i det installerade biblioteket?")
    bryggade = []
    for uri in alla_uris:
        namn = bank.get(uri, {}).get("namn", "")
        svar = _fraga("komponent", namn) if namn else {"funnet": False}
        if svar.get("funnet"):
            bryggade.append((uri, namn, svar))
        else:
            print("  NEJ  %-46s %s" % (uri, namn))
    print("  %d av %d bankposter i scenerna gar att sla upp"
          % (len(bryggade), len(alla_uris)))

    # Steg 2: hela banken mot biblioteket, sa att glappet far en storlek.
    print("\nSteg 2 - hela bankens 65 poster mot biblioteket:")
    from vc_assist_svc.verktyg import katalog as K
    katalog, skal = K._bibliotek()
    if katalog is None:
        print("  inget bibliotek: %s" % skal)
        traffar = []
    else:
        # Bankens namn bar TILLVERKAREN ("ABB IRB 1200-5/0.9"), bibliotekets
        # inte ("IRB 1200-5/0.9"). Bryggan provar bada, och att den maste gora
        # det ar sjalv ett fynd: vokabularen ar inte densamma.
        _TILLVERKARE = ("ABB ", "KUKA ", "Fanuc ", "FANUC ", "Yaskawa ",
                        "Universal Robots ")
        traffar = []
        for u, p in sorted(bank.items()):
            kandidater = [p["namn"]] + [p["namn"][len(tv):] for tv in _TILLVERKARE
                                        if p["namn"].startswith(tv)]
            for k in kandidater:
                if katalog.med_namn(k) is not None:
                    traffar.append((u, k))
                    break
        print("  %d av %d bankposter finns i biblioteket, efter att bankens "
              "tillverkarprefix strukits" % (len(traffar), len(bank)))
        grupper = {}
        for u, _k in traffar:
            grupper[u.split("/")[2]] = grupper.get(u.split("/")[2], 0) + 1
        print("  fordelning: %s" % (grupper or "ingen"))

    # Steg 3: for de komponenter som GAR att sla upp - svarar databladet?
    print("\nSteg 3 - for de biblioteksposter som gar att sla upp, svarar "
          "databladet pa de tva fragorna?")
    prov = [b[1] for b in bryggade]
    if not prov and katalog is not None:
        prov = [k for _u, k in traffar]
        if prov:
            print("  (scenernas komponenter gick inte att sla upp; provar i "
                  "stallet de %d bankposter som gar, med BIBLIOTEKETS namn)"
                  % len(prov))
    svarade_egenskaper = 0
    svarade_signal = 0
    ej_tillamplig = 0
    for namn in prov:
        svar = _fraga("komponent", namn)
        if not svar.get("funnet"):
            continue
        egenskaper = svar.get("egenskapsnamn") or []
        boolska = svar.get("boolska_signaler") or []
        if egenskaper:
            svarade_egenskaper += 1
        if len(boolska) == 1:
            svarade_signal += 1
        elif len(boolska) == 0:
            ej_tillamplig += 1
        print("  %-34s %3d egenskaper, %d boolska signaler%s"
              % (namn[:34], len(egenskaper), len(boolska),
                 "  ([0] entydigt: %s)" % boolska[0] if len(boolska) == 1
                 else ("  ([0] kastar IndexError)" if not boolska
                       else "  ([0] beror pa ordning som inte ar matt)")))
    print("  exakta egenskapsnamn: %d av %d" % (svarade_egenskaper, len(prov)))
    print("  boolsk signal [0] entydig: %d av %d (%d bar ingen boolsk signal "
          "alls, och da ar RATT svar att [0] kastar)"
          % (svarade_signal, len(prov), ej_tillamplig))

    # ---- HAL 4: vcHelpers.Robot mot Robot2 --------------------------------
    print("\n=== HAL 4: vcHelpers.Robot mot vcHelpers.Robot2 ===")
    for typ in ("vcHelpers.Robot", "vcHelpers.Robot2"):
        svar = _fraga("yta", typ)
        n = len(svar.get("medlemmar") or svar.get("members") or [])
        print("  %-20s %s, %d medlemmar" % (typ, svar.get("found"), n))
    print("  Databladet ror inte den har fragan: den handlar om VC:s "
          "hjalpmoduler, inte om en komponent. HALET STAR OPPET.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
