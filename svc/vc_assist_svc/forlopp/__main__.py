# -*- coding: utf-8 -*-
"""Visaren: den yta en människa faktiskt läser.

    PYTHONPATH=svc python3 -m vc_assist_svc.forlopp <spegelfil>
    PYTHONPATH=svc python3 -m vc_assist_svc.forlopp <spegelfil> --folj 1.0

Filen skrivs av den som kör — `Korare.kor(..., forlopp=f)` eller
`Harness.kor(..., forlopp=f)` med en spegel kopplad — och läses här. De två
delar ingenting utom en sokvag, sa visaren kan sta i en annan process, pa en
annan terminal, och startas nar som helst: under korningen, eller lange efter.

Visaren GRANSKAR sin egen utdata innan den skriver den. `26_appen.md` §5 och
fas 17:s grind sager att ett fallt lage aldrig far se ut som ett arbetande, och
en visare som inte provar det pastar bara att den foljer regeln. Faller
grinden skrivs domen UT, under ytan - den goms inte, och ytan halls inte inne:
en anvandare som vantar ska se bade vad systemet tror och att visningen sjalv
ar oppen for tvivel.

Utgangskoder:

    0   bilden gick att lasa, och visningen holl sin egen grind
    1   visningen bröt mot en regel (domen star i utdatan)
    3   laget gick inte att avgora - filen saknas, ar avhuggen eller talar en
        annan version. Det ar ett svar, inte ett fel: OBESTAMT.
"""
from __future__ import annotations

import argparse
import sys
import time

from .spegel import (granska_spegling, las_spegling, rendera_spegling)


def visa(sokvag, strom=None):
    """Skriver en avlasning. Returnerar utgangskoden."""
    strom = strom or sys.stdout
    o = las_spegling(sokvag)
    text = rendera_spegling(o)
    dom = granska_spegling(o, text)
    strom.write(text + "\n")
    if not dom.ok:
        strom.write("\n" + dom.text() + "\n")
        return 1
    return 3 if o.obestamd else 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python3 -m vc_assist_svc.forlopp",
        description="Visar en korning medan den pagar, eller lange efterat.")
    p.add_argument("spegelfil", help="filen den som kor skriver till")
    p.add_argument("--folj", type=float, metavar="SEKUNDER", default=None,
                   help="las om med det har mellanrummet tills korningen ar "
                        "avslutad eller Ctrl+C")
    p.add_argument("--varv", type=int, default=0,
                   help="med --folj: stanna efter sa har manga avlasningar "
                        "(0 = tills korningen ar slut)")
    a = p.parse_args(argv)

    if a.folj is None:
        return visa(a.spegelfil)

    varv = 0
    kod = 3
    try:
        while True:
            varv += 1
            sys.stdout.write("\n" + "=" * 72 + "\n")
            kod = visa(a.spegelfil)
            o = las_spegling(a.spegelfil)
            if not o.obestamd and o.avslutad:
                break
            if a.varv and varv >= a.varv:
                break
            time.sleep(max(0.05, a.folj))
    except KeyboardInterrupt:
        sys.stdout.write("\navbruten av anvandaren; korningen pagar vidare\n")
    return kod


if __name__ == "__main__":
    sys.exit(main())
