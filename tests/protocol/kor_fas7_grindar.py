# -*- coding: utf-8 -*-
"""Fas 7, forsta halvan: kor grind 1-4 SKARPT over en stationskandidat.

Skarpt betyder: riktig STruC++-kompilator, riktigt API-index, ingen attrapp
pa nagon av de fyra grindarna. Ogat (grind 5) ingar INTE - det kraver att
nagot flodar i scenen, och det ar mätt oppet i M-34.

Korning:
    python3 tests/protocol/kor_fas7_grindar.py --strucpp-cli <sokvag> [--json ut.json]

Vad korningen ska visa, ur tests/protocol/fas7_stationen.md:
    en hel kandidat passerar alla fyra
    T1  tagg utanfor kartan          faller
    T2  skrivning till skyddad       faller
    T7  tom kropp                    faller INTE av grind 1-4  <- viktigast

T7 ar den mest upplysande raden i hela korningen. En tom kropp kompilerar och
bryter ingen deklarationsregel; om den inte falls har maste den fallas av
facit, och det ar exakt det protokollet pastar. Korningen bevisar pastaendet i
stallet for att upprepa det.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Grind 1-4 faller en tagg utanfor kartan och en skrivning till en "
        "skyddad signal, men slapper igenom en tom kropp - den maste fallas "
        "av facit och inte av en tidigare grind.",
    "under_prov": (
        "svc/vc_assist_svc/plc/stationsgrind.py",
        "svc/vc_assist_svc/plc/skelett.py",
        "svc/vc_assist_svc/plc/signalkarta.py",
        "svc/vc_assist_svc/plc/deklarationsgrind.py",
        "svc/vc_assist_svc/api_index.py",
    ),
    "facit":
        "HEL passerar; T1 (tagg utanfor kartan) och T2 (skrivning till "
        "skyddad signal) faller; T7 (tom kropp) passerar grind 1-4",
    "facitkalla":
        "protokollets egen falltabell, skriven fore korningen, och grind 3:s "
        "dom tas av STruC++-kompilatorn - ett annat program an var egen "
        "ST-lasare",
    "facitkalla_filer": (
        "tests/protocol/fas7_stationen.md",
        "docs/spec/50_grindar.md",
    ),
    "trasiga_fall": (
        "T1 tagg utanfor kartan maste fallas",
        "T2 skrivning till skyddad signal maste fallas",
        "T7 tom kropp far INTE fallas av grind 1-4; falls den har ar fallet "
        "fel skrivet, inte grinden bevisad",
    ),
    "kraver": ("strucpp",),
    "matningar": ("M-48",),
}

import argparse
import json
import os
import shutil
import sys
import tempfile

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.api_index import bygg_validator                  # noqa: E402
from vc_assist_svc.plc import stationsgrind as S                    # noqa: E402
from vc_assist_svc.plc.skelett import Skelett, Skelettfel           # noqa: E402
from vc_assist_svc.plc.signalkarta import karta_av_rader            # noqa: E402

STATION = "Press"

# Stationen: en press med en givare, en skyddad ljusridå och ett don.
# Ljusridån ar med for att T2 ska ha nagot att bryta mot, och den ar skyddad
# av samma skal som i verkligheten: en sakerhetsfunktion skrivs inte av en
# modell (docs/spec/50_grindar.md).
RADER = [
    ("Givare", "Puls", "givare", "BOOL", "TILL_PLC", "%IX0.0"),
    ("Ljusrida", "Fri", "ridafri", "BOOL", "TILL_PLC", "%IX0.1", True),
    ("Don", "Svar", "don", "BOOL", "FRAN_PLC", "%QX0.0"),
]

# Formen ar verktygsmallarnas egen: getApplication() INLINE, aldrig ett fritt
# `app`. MATT (M-48): med ett fritt `app` kontrollerar grind 4 noll namn och
# hade sagt gront pa vad som helst; med den har formen kontrollerar den tre.
SCENKOD = ("app = getApplication()\n"
           "press = app.findComponent('Press')\n"
           "givare = press.findBehaviour('Puls')\n")


def karta():
    return karta_av_rader(STATION, RADER)


# Kropparna. HEL ar den rimliga losningen; resten ar protokollets trasiga fall.
HEL = "    don := givare AND ridafri;\n"
T1 = "    don := givare AND hittepa;\n"
T2 = "    ridafri := TRUE;\n    don := givare;\n"
T7 = "    ;\n"

FALL = [
    ("HEL", HEL, True, None),
    ("T1", T1, False, "tagg utanfor kartan"),
    ("T2", T2, False, "skrivning till skyddad signal"),
    ("T7", T7, False, "tom kropp"),
]


def kor(strucpp_cli: str, byggrot: str):
    k = karta()
    sk = Skelett.av_karta(k)
    validator = bygg_validator()
    ut = {"station": STATION, "skelett": sk.text(), "fall": []}

    for namn, kropp, vantas_passera, vad in FALL:
        try:
            kand = S.Kandidat.fran_modellsvar(sk, kropp, SCENKOD)
        except Skelettfel as fel:
            ut["fall"].append({"namn": namn, "skelettfel": str(fel)})
            continue
        # stanna_vid_forsta=False: hela grindbilden behovs for att kunna saga
        # VILKEN grind som falde, och for att se att T7 passerar 1-4.
        dom = S.granska_station(kand, k, index=validator,
                                strucpp_cli=strucpp_cli,
                                byggkatalog=os.path.join(byggrot, namn),
                                stanna_vid_forsta=False)
        rad = {
            "namn": namn, "vad": vad,
            "vantas_passera": vantas_passera,
            "passerade": dom.ok,
            "forsta_fallande": dom.forsta_fallande,
            "forgrindar": dict((g, (True if v is True else str(v)))
                               for g, v in dom.forgrindar.items()),
            "grindens_egna_ord": dict(
                (g, t) for g, t in dom.utdata.items() if t),
        }
        ut["fall"].append(rad)
    return ut


def _skriv(ut):
    print("=== fas 7, grind 1-4 skarpt ===")
    print("station: %s\n" % ut["station"])
    fel = 0
    for rad in ut["fall"]:
        if "skelettfel" in rad:
            print("  %-4s SKELETTFEL %s" % (rad["namn"], rad["skelettfel"]))
            fel += 1
            continue
        stamde = rad["passerade"] == rad["vantas_passera"]
        print("  %-4s %s  passerade=%s  forvantat=%s  forst fallande: %s"
              % (rad["namn"], "OK  " if stamde else "FEL ",
                 rad["passerade"], rad["vantas_passera"],
                 rad["forsta_fallande"]))
        for g, v in sorted(rad["forgrindar"].items()):
            print("         %-22s %s" % (g, "GODKAND" if v is True else v))
        if not stamde:
            fel += 1
    return fel


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strucpp-cli", required=True,
                   help="sokvag till STruC++:s korbara CLI")
    p.add_argument("--json", help="skriv rapporten som JSON hit")
    p.add_argument("--behall", action="store_true",
                   help="behall byggkatalogen")
    a = p.parse_args(argv)

    byggrot = tempfile.mkdtemp(prefix="fas7_")
    try:
        ut = kor(a.strucpp_cli, byggrot)
    finally:
        if not a.behall:
            shutil.rmtree(byggrot, ignore_errors=True)

    fel = _skriv(ut)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(ut, f, indent=2, sort_keys=True, ensure_ascii=False)
    print("\n%s" % ("ALLA FALL STAMDE" if fel == 0
                    else "%d FALL STAMDE INTE" % fel))
    return 0 if fel == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
