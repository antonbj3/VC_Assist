# -*- coding: utf-8 -*-
"""Fas 9: en spraakmodells ST mot samma bank, samma skelett och samma domare.

Fas 11 (M-62) mätte baslinjen. Den här körningen mäter den andra sidan av
paret, och paret är hela poängen: `docs/spec/70_faser.md` säger att fas 9:s tal
**aldrig får publiceras ensamt**.

## Vad "modellen" är här, och det ska stå i varje rapport

Det finns **ingen API-nyckel och ingen byggd modellklient** i det här repot.
Modellen är därför en Claude-agent som fått **exakt** det slingan ger: uppgiftens
text, dess signaler, sekvens, förreglingar och tider, plus skelettet. Den fick
uttryckligt förbud mot att öppna repot, där facit och referenslösningar ligger.

Det är en verklig modell och en verklig mätning, men den är **inte automatiserad
och inte upprepad**. Ett tal härifrån är ett stickprov med n = 1 per uppgift.

## Vad som mäts

Samma domare som baslinjen, med samma signatur — `bank/par.py` avvisar ett par
vars sidor dömts olika. Tre tal, som kontraktet kräver:

  forsta forsoket   loste den utan reparation?
  efter k varv      inte mätt här: slingan kräver en modell som kan svara
                    automatiskt, och det finns inte
  fel per klass     ur domarens koder

Kors:
    python3 tests/protocol/kor_fas9_modellen.py --svar <katalog> [--json ut.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from bank import domare, lasare, reparationsbank as RB          # noqa: E402
from vc_assist_svc.plc import stationsgrind as SG               # noqa: E402
from vc_assist_svc.plc.skelett import Skelett, Skelettfel       # noqa: E402


def _las(katalog, namn):
    p = os.path.join(katalog, namn)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def kor_en(post, katalog, strucpp_cli=None, byggkatalog=None):
    """Bygg, granska och döm ett svar. Varje steg kan falla, och sägar varför."""
    tid = post.get("task_id")
    station = (tid or "P").replace("-", "_")
    ut = {"task_id": tid}

    kropp = _las(katalog, "%s_kropp.st" % tid)
    arb = _las(katalog, "%s_arbetsvariabler.st" % tid) or ""
    if kropp is None:
        ut["utfall"] = "inget svar"
        return ut

    karta = RB.karta_ur_uppgift(post, station)
    sk = Skelett.av_karta(karta, arbetsvariabler=True)

    # Arbetsvariablerna granskas FORE isattningen. En variabel med adress eller
    # med en signals namn ar inte en arbetsvariabel, och den ska avvisas dar och
    # inte upptackas som ett logikfel tre grindar senare.
    try:
        if arb.strip():
            sk.granska_arbetsvariabler(arb, karta)
        st_kalla = sk.satt_in(kropp, arb)
    except Skelettfel as fel:
        ut["utfall"] = "skelettet avvisade svaret"
        ut["skal"] = str(fel)
        return ut

    ut["arbetsvariabler"] = [r.strip() for r in arb.splitlines() if r.strip()]
    ut["kroppsrader"] = len([r for r in kropp.splitlines() if r.strip()])

    dom_sg = SG.granska_station(
        SG.Kandidat(station, st_kalla, None), karta,
        strucpp_cli=strucpp_cli, byggkatalog=byggkatalog,
        stanna_vid_forsta=False)
    ut["forgrindar"] = dict((g, (True if v is True else str(v)))
                            for g, v in dom_sg.forgrindar.items())

    d = domare.dom(post, st_kalla)
    ut["godkand"] = bool(d.godkand)
    ut["brister"] = [{"kod": b.kod, "text": b.text} for b in d.brister]
    ut["koder"] = list(d.koder())
    ut["scan"] = d.scan_kord
    ut["utfall"] = "godkand" if d.godkand else "underkand"
    return ut


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--svar", required=True, help="katalogen med modellens svar")
    p.add_argument("--strucpp-cli", help="STruC++ CLI for grind 1")
    p.add_argument("--byggkatalog")
    p.add_argument("--json")
    a = p.parse_args(argv)

    poster = [u.data for u in lasare.ladda() if u.data.get("facit_spar")]
    resultat = [kor_en(post, a.svar, a.strucpp_cli, a.byggkatalog)
                for post in poster]

    print("=== FAS 9: en modells ST mot bankens spårfacit ===\n")
    print("  MODELLEN ar en Claude-agent, inte ett API-anrop. Ingen nyckel och")
    print("  ingen modellklient finns i repot. Stickprov n = 1 per uppgift.\n")
    godkanda = 0
    klasser = collections.Counter()
    for r in resultat:
        if r.get("godkand"):
            godkanda += 1
        print("  %-6s %-12s %s" % (r["task_id"], r["utfall"],
                                   "" if r.get("godkand") else
                                   ", ".join(sorted(set(r.get("koder") or []))) or
                                   r.get("skal", "")[:70]))
        for g, v in sorted((r.get("forgrindar") or {}).items()):
            if v is not True:
                print("           grind %-22s %s" % (g, str(v)[:60]))
        klasser.update(r.get("koder") or [])

    print("\n  FORSTA FORSOKET: %d av %d" % (godkanda, len(resultat)))
    print("  BASLINJEN (M-62, basta niva): 4 av 4 i varv 1")
    if godkanda == len(resultat) == 4:
        print("  => OAVGJORT mot en mallkompilator. Det ska sagas med de orden.")
    print("\n  fel per klass:")
    for kod, n in klasser.most_common():
        print("    %-24s %d" % (kod, n))
    print("\n  Efter k varv: EJ MATT. Slingan kraver en modell som svarar")
    print("  automatiskt, och nagon sadan finns inte i repot.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"resultat": resultat, "godkanda": godkanda,
                       "av": len(resultat)}, f, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
