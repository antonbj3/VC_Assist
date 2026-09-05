#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-107: vad berikningen ger, raknat over hela det installerade biblioteket.

Fragan ar inte "gick det att bygga" utan tre tal:

  * hur manga komponenter far en ENHET MED KALLA
  * hur manga star kvar som `enhet_saknas`
  * vilka falt gick inte att belagga, och varfor

Plus det svar M-85 gjorde nodvandigt: `MaxPayload = 0` i 628 komponenter. Provet
gar igenom alla och kontrollerar att INGEN av dem pastar en nyttolast.

Tungt steg (3201 arkiv, narmare en gigabyte text). Kors med

    nice -n 19 ionice -c3 python3 tests/protocol/kor_m107_berikningen.py

och fyra processer, sa att operatorens skrivbord inte kanner av det.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Berikningen ur tillverkarnas datablad ger `finns` bara dar en kalla "
        "har sagt enheten, `enhet_saknas` dar VC:s filer bar talet utan enhet, "
        "och `saknas` i ovrigt - och ingen av de 628 komponenter som "
        "deklarerar MaxPayload = 0 pastar en nyttolast.",
    "under_prov": ("svc/vc_assist_svc/tillverkardatablad.py",
                   "svc/vc_assist_svc/komponentdatablad.py"),
    "facit":
        "det installerade biblioteket sjalvt: 3201 .vcmx, deras model.xml och "
        "component.rsc, samt tillverkarkorpusen i data/tillverkardatablad/",
    "facitkalla":
        "VC 4.10:s eCatalog-innehall pa den har maskinen plus tillverkarnas "
        "egna publicerade datablad. Ingen av de tva ar skriven av oss.",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "en nolla utan enhet far aldrig skrivas ut som en storhet",
        "ett varde med kalla och ett utan far inte jamforas",
        "en komponent utan datablad far inte fyllas med en grannes tal",
    ),
    # "vc" ar kontraktets ord for det installerade biblioteket (KRAV i
    # svc/vc_assist_svc/bankkontrakt.py). Korningen kraver bibliotekets filer
    # pa disk, inte en korande VC - det star i facit.
    "kraver": ("vc",),
    "matningar": ("M-107", "M-85"),
}

import json
import multiprocessing
import os
import sys
import time
from collections import Counter

HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(HAR, "..", ".."))
sys.path.insert(0, os.path.join(ROT, "svc"))

from vc_assist_svc import katalogindex, komponentdatablad as KD    # noqa: E402
from vc_assist_svc import tillverkardatablad as TD                 # noqa: E402

FALT = ("nyttolast", "rackvidd")

_KORPUS = None


def _init():
    global _KORPUS
    _KORPUS = TD.Korpus.las()


def _en(argument):
    """En komponent -> ett matt. Kors i en underprocess."""
    sokvag, tillverkare = argument
    try:
        blad = KD.las(sokvag, tillverkare=tillverkare)
    except Exception as fel:                              # noqa: BLE001
        return {"fel": "%s: %s" % (type(fel).__name__, fel), "sokvag": sokvag}
    svar = TD.berika(blad, _KORPUS, FALT)
    ut = {"fel": None, "namn": blad.namn, "tillverkare": blad.tillverkare,
          "sokvag": sokvag,
          "korpus": _KORPUS.for_vc_namn(blad.namn) is not None}
    for f in FALT:
        s = svar[f]
        ut[f] = s.lage
        ut[f + "_ordagrant"] = s.ordagrant
        ut[f + "_text"] = s.text()
        # Det ORDAGRANNA katalogfaltet, oberoende av vilket lage som vann.
        # Utan den raden syns inte att model.xml och tillverkaren skriver
        # olika tal om samma robot.
        for kfalt, vart in TD.KATALOGFALT.items():
            if vart == f:
                ut[f + "_modelxml"] = blad.katalogfalt.get(kfalt)
        if s.lage == TD.FINNS:
            # Vardet som KALLAN skrev det, med KALLANS enhet. Den kanoniska
            # omrakningen star bredvid, aldrig i stallet for.
            ut[f + "_varde"] = s.varde
            ut[f + "_enhet"] = s.enhet
            ut[f + "_kanoniskt"] = s.kanoniskt()
            ut[f + "_lasning"] = s.lasning
    return ut


def _familj(sokvag):
    """Robot eller inte, ur metadatans EGEN struktur (samma markorer som M-69)."""
    import zipfile
    try:
        with zipfile.ZipFile(sokvag) as z:
            if "component.rsc" not in z.namelist():
                return ""
            text = z.read("component.rsc").decode("utf-8", "replace")
    except Exception:                                      # noqa: BLE001
        return ""
    for namn, markorer in (("robot", ("rSimRobotController",
                                      "rSimRrsRobotController")),
                           ("transportor", ("rOneWayPath", "rTwoWayPath",
                                            "rSimCapacityBlock", "rTransportNode")),
                           ("verktyg", ("rToolContainer",))):
        for m in markorer:
            if m in text:
                return namn
    return ""


def main():
    fynd = katalogindex.hitta()
    if not fynd:
        print("inget bibliotek hittat")
        return 2
    rot = fynd[0].rot
    print("bibliotek: %s" % rot)

    filer = []
    for katalog, _k, namn in os.walk(rot):
        rel = os.path.relpath(katalog, rot)
        delar = [d for d in rel.split(os.sep) if d not in (".", "")]
        for f in sorted(namn):
            if f.lower().endswith((".vcmx", ".vcm")):
                filer.append((os.path.join(katalog, f),
                              delar[0] if delar else ""))
    print("%d komponenter" % len(filer))

    t0 = time.time()
    with multiprocessing.Pool(4, initializer=_init) as pool:
        matt = pool.map(_en, filer, chunksize=32)
        familjer = pool.map(_familj, [f for f, _t in filer], chunksize=32)
    sek = time.time() - t0
    ok = [m for m in matt if m["fel"] is None]
    print("last pa %.1f s med fyra processer, %d fel"
          % (sek, len(matt) - len(ok)))

    for m, fam in zip(matt, familjer):
        m["familj"] = fam

    korpus = TD.Korpus.las()

    # ---- 1. Hur manga ar robotar, och vilka tillverkare och modeller -------
    fam = Counter(m.get("familj", "") for m in matt)
    robotar = [m for m in ok if m.get("familj") == "robot"]
    rob_tillv = Counter(m["tillverkare"] for m in robotar)
    print("\n== ROBOTPOPULATIONEN ==")
    print("familjer: %s" % dict(fam))
    print("robotar: %d av %d (%.1f %%)"
          % (len(robotar), len(matt), 100.0 * len(robotar) / len(matt)))
    print("distinkta robottillverkare: %d" % len(rob_tillv))
    print("distinkta robotmodellnamn: %d" % len({m["namn"] for m in robotar}))
    print("de tio storsta: %s" % rob_tillv.most_common(10))

    # ---- 2. Lagena, per falt och per familj -------------------------------
    print("\n== LAGEN, HELA BIBLIOTEKET ==")
    rader = []
    for f in FALT:
        c = Counter(m[f] for m in ok)
        rader.append((f, c))
        print("%-10s finns %4d   enhet_saknas %4d   saknas %4d"
              % (f, c[TD.FINNS], c[TD.ENHET_SAKNAS], c[TD.SAKNAS]))
    print("\n== LAGEN, BARA ROBOTAR (%d) ==" % len(robotar))
    for f in FALT:
        c = Counter(m[f] for m in robotar)
        print("%-10s finns %4d   enhet_saknas %4d   saknas %4d"
              % (f, c[TD.FINNS], c[TD.ENHET_SAKNAS], c[TD.SAKNAS]))

    med_enhet = [m for m in ok
                 if any(m[f] == TD.FINNS for f in FALT)]
    print("\nkomponenter med MINST ETT falt med enhet och kalla: %d av %d"
          % (len(med_enhet), len(ok)))
    for m in sorted(med_enhet, key=lambda x: x["namn"]):
        d = ", ".join("%s=%g %s (=%g %s, %s)"
                      % (f, m[f + "_varde"], m[f + "_enhet"],
                         m[f + "_kanoniskt"], TD.faltdef(f).kanonisk,
                         m[f + "_lasning"])
                      for f in FALT if m[f] == TD.FINNS)
        print("  %-24s %-18s %s" % (m["namn"], m["tillverkare"], d))

    # ---- 3. Nollorna: ingen av dem pastar en nyttolast --------------------
    print("\n== NOLLORNA (M-85: 628 komponenter med MaxPayload = 0) ==")
    nollor = [m for m in ok
              if m["nyttolast"] == TD.ENHET_SAKNAS
              and m["nyttolast_ordagrant"].strip() in ("0", "0.0", "0,0")]
    brott = [m["namn"] for m in nollor if "0 kg" in m["nyttolast_text"]]
    print("komponenter med MaxPayload = 0: %d" % len(nollor))
    print("...som skriver ut '0 kg': %d %s" % (len(brott), brott[:5]))
    print("...som sager 'ofyllt falt': %d"
          % sum(1 for m in nollor if "ofyllt falt" in m["nyttolast_text"]))
    nollor_reach = [m for m in ok
                    if m["rackvidd"] == TD.ENHET_SAKNAS
                    and m["rackvidd_ordagrant"].strip() in ("0", "0.0", "0,0")]
    print("komponenter med Reach = 0: %d, varav '0 mm': %d"
          % (len(nollor_reach),
             sum(1 for m in nollor_reach if "0 mm" in m["rackvidd_text"])))

    # ---- 4. Bryggan korpus <-> bibliotek ---------------------------------
    print("\n== KORPUSEN MOT BIBLIOTEKET ==")
    pa_disk = {m["namn"].strip().lower() for m in ok}
    saknade, funna = [], []
    for b in korpus.blad:
        for n in b.vc_namn:
            (funna if n.strip().lower() in pa_disk else saknade).append(
                (b.modell, n))
    print("korpusen: %d modeller, %d belagda uppgifter"
          % (len(korpus), sum(len(b.uppgifter) for b in korpus.blad)))
    print("vc_namn som finns pa disk: %d" % len(funna))
    print("vc_namn som INTE finns pa disk: %d %s" % (len(saknade), saknade))
    utan_bindning = [b.modell for b in korpus.blad if not b.vc_namn]
    print("modeller utan bindning till biblioteket: %d %s"
          % (len(utan_bindning), utan_bindning))

    # ---- 5. Bankens robotposter mot korpusen ------------------------------
    print("\n== BANKENS ROBOTPOSTER (stampel PUBLICERAD_SPEC) ==")
    with open(os.path.join(ROT, "bank", "katalog_index.json"),
              encoding="utf-8") as f:
        bank = json.load(f)["poster"]
    bankrobotar = [p for p in bank if p.get("kategori") == "robot"]
    print("%d robotposter i banken, varav %d med en kalla i korpusen"
          % (len(bankrobotar),
             sum(1 for p in bankrobotar if korpus.for_bank_uri(p["uri"]))))
    for p in bankrobotar:
        b = korpus.for_bank_uri(p["uri"])
        if b is None:
            print("  %-32s INGEN korpuspost" % p["namn"])
            continue
        rad = []
        for falt, banknyckel, enhet in (("nyttolast", "nyttolast_kg", "kg"),
                                        ("rackvidd", "rackvidd_mm", "mm")):
            s = b.svar(falt)
            bankvarde = p.get(banknyckel)
            if s.lage != TD.FINNS:
                rad.append("%s: banken %s %s, kallan SAKNAS"
                           % (falt, bankvarde, enhet))
                continue
            k = s.kanoniskt()
            lika = (bankvarde is not None and abs(k - float(bankvarde)) < 1e-6)
            rad.append("%s: banken %s %s, kallan %g %s -> %s"
                       % (falt, bankvarde, enhet, k, enhet,
                          "SAMMA" if lika else "SKILJER"))
        print("  %-32s %s" % (p["namn"], " | ".join(rad)))

    # ---- 6. Katalogfaltet mot tillverkarens tal --------------------------
    print("\n== VC:s KATALOGFALT MOT TILLVERKARENS TAL ==")
    print("(bara for de komponenter som HAR ett datablad i korpusen; "
          "katalogfaltet ar ett tal utan enhet och far inte jamforas - "
          "raden nedan sager vad de tva SKRIVER, inte att de ar jamforda)")
    for m in sorted(ok, key=lambda x: x["namn"]):
        b = korpus.for_vc_namn(m["namn"])
        if b is None:
            continue
        d = []
        for falt in ("nyttolast", "rackvidd"):
            s = b.svar(falt)
            rå = m.get(falt + "_modelxml")
            vc = "(ej i model.xml)" if rå is None else repr(rå)
            if s.lage == TD.FINNS:
                d.append("%s: model.xml %s, kallan %g %s (=%g %s)"
                         % (falt, vc, s.varde, s.enhet, s.kanoniskt(),
                            TD.faltdef(falt).kanonisk))
            else:
                d.append("%s: model.xml %s, kallan saknas" % (falt, vc))
        print("  %-24s %s" % (m["namn"], " | ".join(d)))

    # ---- 7. Vilka falt gick inte att belagga -----------------------------
    print("\n== FALT SOM INTE GICK ATT BELAGGA ==")
    per_falt = Counter()
    for b in korpus.blad:
        for falt in b.ej_belagda:
            per_falt[falt] += 1
    for falt in sorted(TD.FALT):
        belagda = sum(1 for b in korpus.blad if falt in b.uppgifter)
        print("%-14s belagt pa %2d av %2d modeller, ej belagt pa %2d"
              % (falt, belagda, len(korpus), per_falt[falt]))
    print("\nmodeller utan EN ENDA belagd uppgift:")
    for b in korpus.blad:
        if not b.uppgifter:
            print("  %-28s %s" % (b.modell,
                                  sorted(b.ej_belagda)[0] + ": "
                                  + b.ej_belagda[sorted(b.ej_belagda)[0]][:110]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
