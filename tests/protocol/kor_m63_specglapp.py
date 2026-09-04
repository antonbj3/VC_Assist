# -*- coding: utf-8 -*-
"""M-63: mater glappet mellan 22_planeringslagret.md och svc/vc_assist_svc/plan/.

Specen ar 384 rader med kravkoder (K0-K29), grindar (P1-P8) och felklasser
(PL1-PL12). Koden ar drygt 4 000 rader. Ingen fas hade byggt lagret, och ingen
hade mott hur mycket av specen som fanns.

Matningen ar med flit GROV och MEKANISK: den raknar hur manga av specens egna
koder som over huvud taget NAMNS nagonstans i koden eller i proven. Ett grovt
matt som gar att kora om ar varre an ett fint matt som ingen kan upprepa - och
noll traffar ar ett svar som inte gar att bortforklara.

Den finare bedomningen - VILKA krav som ar uppfyllda och inte - gors for hand i
docs/matningar/M-63 och bar en rad per krav med fil och radnummer. Det talet
gar inte att rakna fram; det gar bara att lasa fram.

    python3 tests/protocol/kor_m63_specglapp.py

Kraver varken VC, OpenPLC eller kompilator.
"""
from __future__ import annotations

import os
import re
import sys

ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", ".."))
SPEC = os.path.join(ROT, "docs", "spec", "22_planeringslagret.md")
TRAD = (os.path.join("svc", "vc_assist_svc"), "tests")

_KRAV = re.compile(r"\*\*(K\d+)\.")
_GRIND = re.compile(r"^\|\s*(P\d+)\s*\|", re.M)
_FELKLASS = re.compile(r"`(PL\d+)`")


def koder():
    with open(SPEC, encoding="utf-8") as f:
        text = f.read()
    return (sorted(set(_KRAV.findall(text)), key=_nyckel),
            sorted(set(_GRIND.findall(text)), key=_nyckel),
            sorted(set(_FELKLASS.findall(text)), key=_nyckel))


def _nyckel(kod):
    return int(re.sub(r"\D", "", kod))


def kalltext():
    """All kod och alla prov, som en enda strang per trad."""
    ut = {}
    for rot in TRAD:
        bitar = []
        for kat, kataloger, filer in os.walk(os.path.join(ROT, rot)):
            kataloger[:] = [k for k in kataloger if k != "__pycache__"]
            for f in sorted(filer):
                if not f.endswith(".py"):
                    continue
                with open(os.path.join(kat, f), encoding="utf-8") as fh:
                    bitar.append(fh.read())
        ut[rot] = "\n".join(bitar)
    return ut


def rader(katalog):
    """{fil: antal rader} for en katalog med python."""
    ut = {}
    for kat, kataloger, filer in os.walk(katalog):
        kataloger[:] = [k for k in kataloger if k != "__pycache__"]
        for f in sorted(filer):
            if f.endswith(".py"):
                with open(os.path.join(kat, f), encoding="utf-8") as fh:
                    ut[f] = len(fh.readlines())
    return ut


def main():
    krav, grindar, felklasser = koder()
    text = kalltext()
    kod = text[TRAD[0]]
    prov = text[TRAD[1]]

    print("M-63: specens koder mot koden och proven")
    print("=" * 64)
    with open(SPEC, encoding="utf-8") as f:
        print("spec: %s, %d rader" % (os.path.relpath(SPEC, ROT),
                                      len(f.readlines())))
    plan = rader(os.path.join(ROT, "svc", "vc_assist_svc", "plan"))
    print("kod:  svc/vc_assist_svc/plan/, %d filer, %d rader"
          % (len(plan), sum(plan.values())))
    print()

    for namn, lista in (("kravkoder K", krav), ("grindar P", grindar),
                        ("felklasser PL", felklasser)):
        namnda = [k for k in lista
                  if re.search(r"\b%s\b" % k, kod)
                  or re.search(r"\b%s\b" % k, prov)]
        print("%-16s %2d i specen, %2d namns i kod eller prov"
              % (namn, len(lista), len(namnda)))
        saknade = [k for k in lista if k not in namnda]
        if saknade:
            print("%-16s namns ingenstans: %s" % ("", " ".join(saknade)))
    print()

    # Namnkrocken: specens grindnamn P1-P8 ar ocksa byggplanens EGNA
    # lintkoder, med helt andra betydelser. Tva halvor av samma begrepp som
    # inte mots (specens egen felklass PL11).
    sys.path.insert(0, os.path.join(ROT, "svc"))
    sys.path.insert(0, os.path.join(ROT, "bank"))
    sys.path.insert(0, os.path.join(ROT, "ext", "vc_addon", "vc_assist"))
    from vc_assist_svc.plan.byggplan import LINTKODER as BYGGLINT
    krockande = sorted(k for k in BYGGLINT
                       if re.match(r"^P\d+_", k) and k.split("_")[0] in grindar)
    print("namnkrock: %d av byggplanens lintkoder heter samma sak som en "
          "grind i specen" % len(krockande))
    for k in krockande:
        print("    %-24s specens %s: %s" % (k, k.split("_")[0], _grindtext(
            k.split("_")[0])))
    print()

    for fil in sorted(plan):
        print("    %-20s %4d rader" % (fil, plan[fil]))
    return 0


def _grindtext(kod):
    with open(SPEC, encoding="utf-8") as f:
        for rad in f:
            if rad.startswith("| %s |" % kod):
                return rad.split("|")[2].strip()
    return "?"


if __name__ == "__main__":
    sys.exit(main())
