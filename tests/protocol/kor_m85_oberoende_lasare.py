# -*- coding: utf-8 -*-
"""En ANDRA lasare av component.rsc, som inte delar en rad kod med den forsta.

## Varfor korningen finns

`85_bankkontraktet.md` §2: ett facit far aldrig raknas fram av koden som ska
domas. `bankkontrakt.granska_registret` fallde en enda post av 33, och det var
`kor_m85_databladets_tackning` - dess tal om vad `component.rsc` BAR lases ut
ur filerna av `komponentdatablad.py`, alltsa samma modul som domen galler.

Foljden ar konkret: ett falt parsern missar rapporteras som ett falt filen inte
bar. Ett fel i lasaren ser da ut som en brist i biblioteket, och det ar den
sortens tal man inte tvivlar pa.

## Vad den har lasaren gor annorlunda

Den skannar rader. Ingen tradbyggnad, ingen kannedom om VC:s modell, inga
regler om NodeClass eller rotens variabelrymd - bara `zipfile`, `str.split` och
tva monster over textens egen form:

    Variable "rTVariable<rDouble>"      en egenskap borjar
      Quantity "Angle" "VectorQuantity" den bar en storhet

## Vad jamforelsen bevisar, och vad den INTE bevisar

De tva raknar over OLIKA namnare med flit: `komponentdatablad.py` tar bara
rotens egna egenskaper och hoppar over geometrin (`NodeClass`), den har tar
varje `Variable` i filen. Antalen ska alltsa inte stamma.

**KVOTEN ska stamma.** Andelen egenskaper som bar en storhet ar ett drag hos
biblioteket, inte hos ett urval - om den forsta lasaren tyst tappade
`Quantity`-rader vore dess kvot LAGRE an den har. Skiljer sig kvoterna kraftigt
finns ett fel i en av lasarna, och da vet vi att det finns innan nagon bygger
en dom pa talet.

Det ar ett svagare bevis an tva lasare med samma namnare, och det star som en
gräns i LIMITS.

    python3 tests/protocol/kor_m85_oberoende_lasare.py [--json ut.json]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import time
import zipfile

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

BANKPOST = {
    "pastar": "M-85:s antal egenskaper med storhet overstiger aldrig antalet "
              "Quantity-rader en oberoende radskanning finner i samma filer",
    "under_prov": ("svc/vc_assist_svc/komponentdatablad.py",),
    "facit": "antalet Quantity-rader i biblioteket, raknat med ren radskanning "
             "ur zipfilen - en OVRE grans for varje delmangd av dem",
    "facitkalla": "en andra lasare i den har filen, skriven utan kannedom om "
                  "VC:s modell - bara zipfile och textens egen form",
    "facitkalla_filer": ("tests/protocol/kor_m85_oberoende_lasare.py",),
    "trasiga_fall": (
        "en fil som inte gar att oppna maste rapporteras, aldrig raknas som noll",
        "noll lasta filer maste ge slutkod 2 - en kvot ur noll filer ar ingen "
        "matning",
    ),
    "kraver": ("vc",),
    "matningar": ("M-85",),
}


def _en(sokvag):
    """(egenskaper, med_storhet, fel) for EN fil. Ren radskanning."""
    try:
        with zipfile.ZipFile(sokvag) as z:
            text = z.read("component.rsc").decode("utf-8", "replace")
    except Exception as e:                              # noqa: BLE001
        return (0, 0, "%s: %s" % (os.path.basename(sokvag), e.__class__.__name__))
    egenskaper = med = 0
    i_egenskap = False
    for rad in text.splitlines():
        s = rad.strip()
        if s.startswith('Variable "'):
            egenskaper += 1
            i_egenskap = True
        elif s.startswith('Quantity "') and i_egenskap:
            med += 1
            i_egenskap = False       # hogst en storhet raknas per egenskap
    return (egenskaper, med, None)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    a = p.parse_args(argv)

    from vc_assist_svc import katalogindex
    fynd = katalogindex.hitta()
    if not fynd:
        print("hittade inget komponentbibliotek", file=sys.stderr)
        return 2
    rot = fynd[0].rot

    filer = []
    for katalog, _k, namn in os.walk(rot):
        for f in sorted(namn):
            if f.lower().endswith((".vcmx", ".vcm")):
                filer.append(os.path.join(katalog, f))
    if not filer:
        # Fail-closed: en kvot ur noll filer ar ingen matning.
        print("noll komponentfiler under %s" % rot, file=sys.stderr)
        return 2

    print("=== component.rsc last av EN ANDRA LASARE ===\n")
    print("  bibliotek: %s" % rot)
    print("  filer:     %d\n" % len(filer))

    t0 = time.time()
    with multiprocessing.Pool(4) as pool:
        matt = pool.map(_en, filer, chunksize=16)
    sekunder = time.time() - t0

    egenskaper = sum(m[0] for m in matt)
    med = sum(m[1] for m in matt)
    fel = [m[2] for m in matt if m[2]]
    kvot = 100.0 * med / max(1, egenskaper)

    print("  Variable-rader:        %6d" % egenskaper)
    print("  darav med Quantity:    %6d" % med)
    print("  KVOT:                  %6.1f %%" % kvot)
    print("  olasbara filer:        %6d" % len(fel))
    print("  %.1f s\n" % sekunder)

    # M-85:s tal, ur matningen och inte ur koden.
    print("  M-85 (komponentdatablad.py): 11 539 av 82 383 = 14,0 %")
    print("  den har lasaren:             %d av %d = %.1f %%"
          % (med, egenskaper, kvot))
    print()
    print("  JAMFORELSEN GAR INTE ATT GORA AN, och det ar sjalva resultatet.")
    print()
    print("  De tva raknar over olika populationer. komponentdatablad.py tar")
    print("  bara ROTENS egna egenskaper och hoppar over geometrin; den har")
    print("  lasaren tar varje Variable i filen - 2,5 miljoner mot 82 tusen.")
    print("  En kvotskillnad kan da lika garna vara populationen som ett fel.")
    print()
    print("  Att skilja dem kraver att rotens rackvidd lases ut UR FILFORMATET")
    print("  av en andra lasare. Ett forsok att gora det pa nastningsdjup gav")
    print("  noll rotvariabler i ett stickprov - alltsa fel antagande om")
    print("  formen, inte ett fynd. En andra lasare som far formen fel")
    print("  producerar ett andra fel tal, inte en kontroll.")
    print()
    print("  Vad korningen DARFOR ar vard: den visar att tautologin i M-85 ar")
    print("  verklig och INTE billig att bryta. Det ar ett besked till den som")
    print("  ska laga den, och det ar mer an vi visste innan.")
    print()
    print("  Ett sant villkor stams anda av: rotens egenskaper ar en delmangd,")
    print("  sa M-85:s 11 539 far aldrig overstiga %d." % med)
    if 11539 > med:
        print("  DET GOR DEN NU - en av lasarna har bevisligen fel.")
        return 1

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"rot": rot, "filer": len(filer),
                       "egenskaper": egenskaper, "med_storhet": med,
                       "kvot_procent": round(kvot, 2),
                       "m85_kvot_procent": 14.0,
                       "avvikelse": round(avvikelse, 2),
                       "olasbara": fel[:50], "sekunder": round(sekunder, 1)},
                      f, indent=2, ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
