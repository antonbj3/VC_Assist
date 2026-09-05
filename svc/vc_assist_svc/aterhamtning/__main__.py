# -*- coding: utf-8 -*-
"""Visaren: ytan en människa läser när något har dött.

    PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil>
    PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil> --loggar ~/
    PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil> --folj 1.0

Filen skrivs av den som sonderar, med en spegel kopplad, och läses här. De två
delar ingenting utom en sökväg — och det är hela poängen: **den som ska berätta
att systemet dog får inte bo i det som dog.**

Visaren GRANSKAR sin egen utdata innan den skriver den, precis som fas 17:s
visare. Faller grinden skrivs domen ut under ytan; den göms inte, och ytan
hålls inte inne. En användare som väntar ska se både vad systemet tror och att
visningen själv är öppen för tvivel.

Utgångskoder:

    0   bilden gick att läsa, allt svarade, och visningen höll sin egen grind
    1   visningen bröt mot en regel (domen står i utdatan)
    2   något delsystem svarar inte — ytan säger vad och varför
    3   läget gick inte att avgöra: filen saknas, är avhuggen eller talar en
        annan version. Det är ett svar, inte ett fel: OBESTÄMT.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from .bild import las_bild
from .grind import granska
from .kallor import loggarna
from .lagen import DELSYSTEM, LEVANDE, OBESTAMT
from .yta import rendera


def visa(sokvag, loggkatalog=None, strom=None):
    """Skriver en avläsning. Returnerar utgångskoden."""
    strom = strom or sys.stdout
    blick = las_bild(sokvag)
    loggar = loggarna(loggkatalog) if loggkatalog else None
    text = rendera(blick, loggar)
    dom = granska(blick, text, loggar)
    strom.write(text + "\n")
    if not dom.ok:
        strom.write("\n" + dom.text() + "\n")
        return 1
    if blick.obestamd:
        return 3
    lagen = [blick.lage(d) for d in DELSYSTEM]
    if any(l == OBESTAMT for l in lagen):
        return 3
    if any(l not in LEVANDE for l in lagen):
        return 2
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python3 -m vc_assist_svc.aterhamtning",
        description="Visar vad som dog, varför, och om det kommer tillbaka.")
    p.add_argument("bildfil", help="filen den som sonderar skriver till")
    p.add_argument("--loggar", metavar="KATALOG", default=None,
                   help="katalogen med vc_assist_boot.log och "
                        "vc_assist_brygga.log, så stegen kan köras")
    p.add_argument("--folj", type=float, metavar="SEKUNDER", default=None,
                   help="läs om med det här mellanrummet tills Ctrl+C")
    p.add_argument("--varv", type=int, default=0,
                   help="med --folj: stanna efter så här många avläsningar")
    a = p.parse_args(argv)
    katalog = os.path.expanduser(a.loggar) if a.loggar else None

    if a.folj is None:
        return visa(a.bildfil, katalog)

    varv = 0
    kod = 3
    try:
        while True:
            varv += 1
            sys.stdout.write("\n" + "=" * 72 + "\n")
            kod = visa(a.bildfil, katalog)
            if a.varv and varv >= a.varv:
                break
            time.sleep(max(0.05, a.folj))
    except KeyboardInterrupt:
        sys.stdout.write("\navbruten av användaren; systemet är oförändrat\n")
    return kod


if __name__ == "__main__":
    sys.exit(main())
