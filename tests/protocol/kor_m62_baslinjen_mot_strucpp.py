# -*- coding: utf-8 -*-
"""M-62: baslinjens fyra program genom BADA motorerna, scan for scan.

Baslinjen loser 4 av 4 av bankens sparfacituppgifter. Domen kommer fran
`svc/vc_assist_svc/st/tolk.py`, alltsa fran vart eget ST-lager. Om tolken har
fel om ST-semantiken har facit fel, och da mater banken var egen
missuppfattning med stor precision.

Den har korningen ar den ANDRA motorn: STruC++ 0.6.6 bygger samma kalla till
en korbar REPL och drivs med samma spar, scan for scan, med samma 20 ms cykel.
Skillnaden per signal och per scan redovisas.

Det ar precis den matning `M-45` sager ska goras nar kedjan star, och den ar
har begransad till STruC++ - inte OpenPLC. Den bevisar att tva oberoende
implementationer av ST-semantiken ar overens om baslinjens kod, eller pekar ut
exakt var de inte ar det. Den bevisar ingenting om runtimen.

Kors:
    python3 tests/protocol/kor_m62_baslinjen_mot_strucpp.py --strucpp-cli <sokvag>

beskriver: svc/vc_assist_svc/plc/baslinje/, svc/vc_assist_svc/st/strucpp_orakel.py
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Baslinjens fyra program ger samma utsignaler i var tolk som i "
        "STruC++, scan for scan over hela bankens spar, eller sa pekas det ut "
        "var de skiljer sig.",
    "under_prov": (
        "svc/vc_assist_svc/st/tolk.py",
        "svc/vc_assist_svc/plc/baslinje/generator.py",
    ),
    "facit":
        "STruC++ 0.6.6 bygger samma kalla till en korbar REPL och drivs med "
        "samma spar, samma 20 ms cykel, ett steg per scan",
    "facitkalla":
        "STruC++ ar den andra motorn: tva oberoende implementationer av "
        "ST-semantiken. Domen kommer inte ur tolken som prova, och det ar "
        "hela skalet till att korningen finns (M-45).",
    "facitkalla_filer": ("svc/vc_assist_svc/st/strucpp_orakel.py",),
    "trasiga_fall": (
        "en skillnad i nagon scan maste pekas ut med signal och scannummer",
        "jamforelsen far inte bara titta dar facit tittar - ett steg per "
        "scan, inte ett steg per facitpunkt, annars hittas bara de skillnader "
        "facit redan letar efter",
    ),
    "kraver": ("strucpp",),
    "matningar": ("M-62",),
}

import argparse
import os
import shutil
import sys
import tempfile

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import baslinjebank as B                                          # noqa: E402
from vc_assist_svc.plc.baslinje.generator import Baslinje         # noqa: E402
from vc_assist_svc.st import tolk as T                            # noqa: E402
from vc_assist_svc.st.strucpp_orakel import (Orakelfel, Steg,     # noqa: E402
                                             jamfor)


def spar_ur_sekvens(post, sekvens, scan_ms):
    """Ett Steg per scan, med varje utsignal avlast varje scan.

    Ett steg per scan och inte ett steg per facitpunkt: fragan ar var motorerna
    skiljer sig, och en jamforelse som bara tittar dar facit tittar hittar bara
    de skillnader facit redan letar efter.
    """
    utsignaler = tuple(s["name"] for s in post["control"]["signals"]
                       if s["dir"] == "out")
    punkter = {}
    for steg in sekvens["steg"]:
        punkter[round(float(steg["t_ms"]) / scan_ms)] = steg.get("satt") or {}
    slut = max(punkter) if punkter else 0
    ut = []
    for k in range(slut + 1):
        ut.append(Steg(dict(punkter.get(k, {})), 1, utsignaler))
    return ut


def kor(strucpp_cli):
    poster = B.med_sparfacit(B.genereringsuppgifter(B.las_uppgifter()))
    baslinje = Baslinje()
    scan_ms = T.SCAN_MS
    rader = []
    scan_totalt = 0
    avlasningar = 0
    avvikelser_totalt = 0
    byggda = 0
    for post in poster:
        tid = post["task_id"]
        bygge = B.bygg(post, baslinje)
        katalog = tempfile.mkdtemp(prefix="m62_orakel_")
        try:
            for sekvens in post["facit_spar"]["sekvenser"]:
                spar = spar_ur_sekvens(post, sekvens, scan_ms)
                try:
                    avvikelser = jamfor(bygge.st_kalla, bygge.karta.station,
                                        spar, strucpp_cli, katalog=katalog)
                except Orakelfel as fel:
                    rader.append("%-6s %-42s ORAKELFEL %s"
                                 % (tid, sekvens["id"], fel))
                    continue
                byggda += 1
                scan_totalt += len(spar)
                avlasningar += sum(len(s.las) for s in spar)
                avvikelser_totalt += len(avvikelser)
                rader.append("%-6s %-42s %5d scan  %5d avlasningar  "
                             "%3d avvikelser"
                             % (tid, sekvens["id"], len(spar),
                                sum(len(s.las) for s in spar),
                                len(avvikelser)))
                for a in avvikelser[:10]:
                    rader.append("        %s" % a)
        finally:
            shutil.rmtree(katalog, ignore_errors=True)
    return rader, scan_totalt, avlasningar, avvikelser_totalt, byggda


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="M-62: baslinjen genom tolken och genom STruC++")
    ap.add_argument("--strucpp-cli", required=True)
    a = ap.parse_args(argv)
    if not os.path.exists(a.strucpp_cli):
        raise SystemExit("hittar inte STruC++ pa %s" % a.strucpp_cli)

    rader, scan, avlasningar, avvikelser, korda = kor(a.strucpp_cli)
    print("M-62: BASLINJENS KOD GENOM TVA MOTORER")
    print("tolken: %s, cykel %.1f ms" % ("vc_assist_svc.st.tolk", T.SCAN_MS))
    print("oraklet: STruC++ --build, cykel last ur binarens egen startrad")
    print("")
    print("\n".join(rader))
    print("")
    print("SUMMA: %d sekvenser korda, %d scan, %d avlasningar, "
          "%d avvikelser" % (korda, scan, avlasningar, avvikelser))
    print("")
    if avvikelser:
        print("MOTORERNA AR INTE OVERENS. Varje avvikelse ovan ar ett stalle "
              "dar bankens dom vilar pa var egen tolk och inte pa nagot annat.")
        return 1
    print("MOTORERNA AR OVERENS pa varje avlast signal i varje scan.")
    print("Det bevisar INTE nagot om OpenPLC:s runtime; det bevisar att tva "
          "oberoende implementationer av ST-semantiken ger samma spar for "
          "baslinjens kod.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
