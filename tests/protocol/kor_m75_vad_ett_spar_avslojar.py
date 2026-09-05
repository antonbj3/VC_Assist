# -*- coding: utf-8 -*-
"""M-75: hur mycket av ett KANT program gar att se i dess eget I/O-spar?

Fas 18 i `docs/spec/70_faser.md` bygger pa en premiss: ett inspelat I/O-spar
fran en korande linje har redan bankens facitform, och en modell kan skriva ST
som ateger det. Fasen bar fyra arlighetskrav, och alla fyra ar HYPOTESER - de ar
resonerade, inte matta.

Den har korningen matte dem, och den kan gora det darfor att vi har ett fall dar
svaret ar kant: bankens uppgifter har en referenslosning OCH ett sparfacit. Vi
kan alltsa kora det kanda programmet, spela in sparet, och sedan fraga vad
sparet AVSLOJAR om programmet det kom ur.

Det ar samma sak som en anlaggning ger, med en avgorande skillnad: har vet vi
facit, sa vi kan mata vad som INTE syns.

Kors:
    python3 tests/protocol/kor_m75_vad_ett_spar_avslojar.py [--json ut.json]
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Ett I/O-spar fran ett kant program visar inte programmets inre: "
        "stegvariabelns lagen och villkorsgrenarna syns aldrig, och det "
        "satter taket for vad fas 18:s harledning kan pasta.",
    "under_prov": ("bank/anlaggning.py",),
    "facit":
        "programmets egna lagen och villkorsgrenar, raknade ur "
        "referenskallan, mot vad sparet visar per signal: antal varden och "
        "antal byten",
    "facitkalla":
        "bankens uppgifter: referenslosningen ar kand och handskriven fore "
        "korningen, sa det gar att rakna vad som INTE syns i sparet. En "
        "anlaggning ger samma spar utan att facit ar kant.",
    "facitkalla_filer": (
        "bank/uppgifter/T-07.json",
        "bank/uppgifter/H-04.json",
        "bank/uppgifter/S-05.json",
        "bank/uppgifter/L-05.json",
    ),
    "trasiga_fall": (
        "SAKNAS - korningen skriver tal och faller aldrig; den namner tysta "
        "signaler och utgangar med hogst tva byten men har ingen fixtur som "
        "maste fallas",
    ),
    "kraver": ("inget",),
    "matningar": ("M-75",),
}

import argparse
import collections
import json
import os
import re
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from bank import lasare                                          # noqa: E402
from vc_assist_svc.st import lasare as st_lasare                 # noqa: E402
from vc_assist_svc.st import modell as M                         # noqa: E402
from vc_assist_svc.st.tolk import Tolk                           # noqa: E402

def signaler(post):
    """Bankens egna typnamn, som tolken ocksa talar (bool, int, real).

    Ingen oversattningstabell: tva namnrymder for samma sak ar tva namnrymder
    som gar isar, och tolkens NOLLVARDE ar redan bankens form.
    """
    return dict((s["name"], str(s["type"]).lower())
                for s in post["control"]["signals"])


def spela_in(post):
    """Kor referensen genom alla sekvenser och lamna ETT sammanhangande spar.

    Varje sekvens spelas in for sig och laggs efter den forra pa en gemensam
    tidsaxel, precis som en anlaggning som gar hela dagen. Tolken byggs om per
    sekvens, for en anlaggning som spanningssatts pa nytt gor ocksa det.
    """
    fs = post["facit_spar"]
    sig = signaler(post)
    rader = []
    t0 = 0.0
    for sekv in fs["sekvenser"]:
        tolk = Tolk(fs["referens"], signaler=sig, scan_ms=float(fs["scan_ms"]))
        for steg in sekv["steg"]:
            for namn, v in (steg.get("satt") or {}).items():
                tolk.satt(namn, v)
            tolk.kor_till(float(steg["t_ms"]))
            rad = {"t_ms": round(t0 + tolk.tid_ms, 3), "sekvens": sekv["id"]}
            for namn in sig:
                rad[namn] = tolk.las(namn)
            # Det INRE tillstandet spelas INTE in. En anlaggning ger bara sina
            # kontaktdon - det ar hela poangen med matningen.
            rader.append(rad)
        t0 += tolk.tid_ms + float(fs["scan_ms"])
    return rader, sig


def inre_tillstand(post):
    """Vad programmet SJALVT har for lagen, last ur referensens kalla.

    Det har ar facit for tackningsfragan: hur manga av programmets egna steg
    besokte sparet? En anlaggning kan aldrig svara pa det.
    """
    kalla = post["facit_spar"]["referens"]
    lagen = set()
    # CASE-etiketter och jamforelser mot stegvariabeln.
    for m in re.finditer(r"steg\s*(?::=|=)\s*(\d+)", kalla, re.I):
        lagen.add(int(m.group(1)))
    for m in re.finditer(r"^\s*(\d+)\s*:", kalla, re.M):
        lagen.add(int(m.group(1)))
    return sorted(lagen)


def grenar(post):
    """Antal villkorsgrenar i referensen, ur ST-lagrets egen lasare.

    Lasaren och inte en regex: en regex over ST-text raknar ord, och en gren
    inuti en strang eller en kommentar hade rakats med. Samma felklass som
    M-70 matte i mitt eget monster.
    """
    enhet = st_lasare.las(post["facit_spar"]["referens"])
    n = {"IF": 0, "CASE": 0, "grenar": 0}

    def ga(satser):
        for s in satser or ():
            if isinstance(s, M.Om):
                n["IF"] += 1
                for gren in s.grenar or ():
                    n["grenar"] += 1
                    ga(gren.satser)
                if s.annars:
                    n["grenar"] += 1
                    ga(s.annars)
            elif isinstance(s, M.Fall):
                n["CASE"] += 1
                for gren in s.grenar or ():
                    n["grenar"] += 1
                    ga(gren.satser)
                if s.annars:
                    n["grenar"] += 1
                    ga(s.annars)
            elif isinstance(s, (M.Medan, M.Upprepa, M.ForSats)):
                ga(getattr(s, "satser", ()) or ())
    for p_ in enhet.pouer:
        ga(p_.kropp)
    return n


def timrar(post, rader, sig):
    """Hur manga GANGER varje utgang bytte varde - namnaren for varje harledd tid.

    Fas 18:s andra arlighetskrav: en timer som lost ut EN gang ar ett stickprov
    med n = 1. Talet nedan ar den namnaren, och den kan bara raknas ur sparet.
    """
    ut = {}
    for namn, typ in sig.items():
        if typ != "bool":
            continue
        byten = 0
        forra = None
        for r in rader:
            v = bool(r.get(namn))
            if forra is not None and v != forra:
                byten += 1
            forra = v
        ut[namn] = byten
    return ut


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--uppgift", default="T-07")
    p.add_argument("--json")
    a = p.parse_args(argv)

    u = [x for x in lasare.ladda() if x.id == a.uppgift][0]
    post = u.data
    rader, sig = spela_in(post)
    lagen = inre_tillstand(post)
    g = grenar(post)
    byten = timrar(post, rader, sig)

    # Vilka VARDEN antog varje utgang i sparet? En utgang som aldrig andrades
    # sager ingenting om vad som styr den.
    varden = {}
    for namn, typ in sig.items():
        varden[namn] = len(set(json.dumps(r.get(namn)) for r in rader))

    print("=== M-75: vad ett I/O-spar avslojar om programmet det kom ur ===\n")
    print("  uppgift:        %s" % a.uppgift)
    print("  sekvenser:      %d" % len(post["facit_spar"]["sekvenser"]))
    print("  sparrader:      %d" % len(rader))
    print("  signaler:       %d" % len(sig))
    print()
    print("  PROGRAMMETS EGET INRE, som sparet ALDRIG ser:")
    print("    lagen i stegvariabeln: %s" % (lagen or "inga hittade"))
    print("    IF-satser: %d, CASE-satser: %d, villkorsgrenar: %d"
          % (g["IF"], g["CASE"], g["grenar"]))
    print()
    print("  VAD SPARET GER, per signal:")
    print("    %-18s %8s %8s" % ("signal", "varden", "byten"))
    tysta = []
    for namn in sorted(sig):
        print("    %-18s %8d %8s" % (namn, varden[namn],
                                     byten.get(namn, "-")))
        if varden[namn] <= 1:
            tysta.append(namn)
    print()
    print("  SIGNALER SOM ALDRIG ANDRADE SIG: %d av %d%s"
          % (len(tysta), len(sig), (" (%s)" % ", ".join(tysta)) if tysta else ""))
    print("    En signal som star still sager ingenting om vad som styr den.")
    print()
    engangs = sorted(n for n, b in byten.items() if b and b <= 2)
    print("  UTGANGAR MED HOGST TVA BYTEN (n = 1 puls): %d%s"
          % (len(engangs), (" — %s" % ", ".join(engangs)) if engangs else ""))
    print("    Varje tid harledd ur en sadan ar ett stickprov med n = 1.")

    ut = {"uppgift": a.uppgift, "sparrader": len(rader),
          "lagen": lagen, "grenar": g, "varden": varden, "byten": byten,
          "tysta": tysta, "engangs": engangs}
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(ut, f, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
