# -*- coding: utf-8 -*-
"""Radatan bakom M-163: forslagen nar valet faller, matta mot det INSTALLERADE
biblioteket.

Kors:
    nice -n 19 ionice -c3 python3 docs/matningar/radata/m163_forslag.py

Skriver bara till stdout. Talen i M-163 ska ga att fa fram igen med den har
filen och ingenting annat.
"""
from __future__ import annotations

import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import katalogindex as KI                   # noqa: E402
from vc_assist_svc import katalogsok as KS                     # noqa: E402
from vc_assist_svc.plan import forslag as FO                   # noqa: E402
from vc_assist_svc.plan import motsagelse as MO                # noqa: E402
from vc_assist_svc.plan import storheter as ST                 # noqa: E402
from vc_assist_svc.plan import villkorssprak as VS             # noqa: E402
from vc_assist_svc.plan.harkomst import Harkomst               # noqa: E402
from vc_assist_svc.plan.spec import (Del, DetaljeradSpec,      # noqa: E402
                                     Grundbegaran, Omrade)


def rubrik(text):
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


class Raknare(object):
    """Sokskiktet, men med varje fraga rakn0ad."""

    def __init__(self, katalog):
        self.katalog = katalog
        self.fragor = 0
        self.sekunder = 0.0

    def sok(self, **kv):
        t0 = time.time()
        self.fragor += 1
        try:
            return self.katalog.sok(**kv)
        finally:
            self.sekunder += time.time() - t0


def _spec(krav_mm, vald_rackvidd_mm):
    begaran = Grundbegaran(
        "m163", "Bygg en plockcell med en robot. Roboten ska na bade bandet "
        "och pallplatsen, %g mm. Cellen ar 2000 x 2000 mm." % krav_mm,
        "operator")
    delar = [Del("robot", "file:///vald.vcm", 1, "robot",
                 [500.0, 500.0, 1400.0], 272.0)]
    villkor = [VS.Typvillkor(
        "rackvidd", "geometri", "del.robot.rackvidd_mm", "ge", float(krav_mm),
        Harkomst("begaran", "Roboten ska na bade bandet och pallplatsen"),
        "roboten maste na %g mm" % krav_mm)]
    omrade = Omrade(2000.0, 2000.0, 3000.0, 200.0,
                    Harkomst("begaran", "Cellen ar 2000 x 2000 mm"))
    spec = DetaljeradSpec("m163", begaran, delar=delar, villkor=villkor,
                          omrade=omrade)
    return spec, {"robot": {"rackvidd_mm": float(vald_rackvidd_mm)}}


def main():
    rubrik("1. BIBLIOTEKET SOM SOKS")
    fynd = KI.hitta()
    if not fynd:
        print("ingen biblioteksrot hittad; provade:")
        for rot, hur in KI.kandidatrotter():
            print("   %-70s %s" % (rot, hur))
        return 1
    for f in fynd:
        print("rot:        %s" % f.rot)
        print("hittad via: %s" % f.hur)
    t0 = time.time()
    index = KI.bygg(fynd[0].rot, djupt=False)
    bygg_s = time.time() - t0
    poster = index["poster"]
    med_reach = sum(1 for p in poster if p.get("rackvidd_mm"))
    med_payload = sum(1 for p in poster if p.get("nyttolast_kg"))
    print("poster:     %d  (olasliga %d, %.1f s grunt)"
          % (index["antal"], len(index["olasliga"]), bygg_s))
    print("med Reach:      %d" % med_reach)
    print("med MaxPayload: %d" % med_payload)

    katalog = KS.Katalog.fran_index(index)

    rubrik("2. FAMILJEFILTRET AR EN FALLA I GRUNT LAGE")
    print("index djupt:            %s" % katalog.djupt)
    print('sok(familj="robot"):    %d traffar av %d poster'
          % (katalog.sok(familj="robot").totalt, len(katalog.poster)))
    print("-> ett forslag som filtrerade pa familj hade svarat 'ingenting")
    print("   racker' om ett fullt bibliotek. Fragan bar darfor bara kravet.")

    rubrik("3. VAD SOKSKIKTET LAMNAR FOR ETT RACKVIDDSKRAV")
    for krav in (1500.0, 2050.0, 2500.0, 3200.0, 9000.0):
        svar = katalog.sok(min_rackvidd_mm=krav, max_rader=100000)
        print("rackvidd >= %6.0f mm: %4d traffar, %4d rader, sammandrag %s"
              % (krav, svar.totalt, svar.visade,
                 "ja (%d tillverkare)" % len(svar.sammandrag)
                 if svar.sammandrag is not None else "nej"))

    rubrik("4. VAD UPPRAKNINGEN PER TILLVERKARE RACKER TILL")
    for krav in (2050.0, 2500.0, 3200.0):
        port = Raknare(katalog)
        rader, totalt, ej = FO._rader(port, "min_rackvidd_mm", krav)
        print("rackvidd >= %6.0f mm: %4d traffar, %4d uppraknade, %4d ej "
              "uppraknade, %2d fragor, %.0f ms"
              % (krav, totalt, len(rader), ej, port.fragor,
                 port.sekunder * 1000))

    rubrik("5. DOMEN MED FORSLAG - EN BESTALLNING SOM FALLER PA VALET")
    for krav, vald in ((2050.0, 1650.0), (9000.0, 1650.0)):
        spec, blad = _spec(krav, vald)
        port = Raknare(katalog)
        t0 = time.time()
        dom = MO.granska(spec.villkor, ST.Faktarum(spec, blad), spec,
                         sokport=port)
        vaggtid = time.time() - t0
        print("\n--- krav ge %g mm, vald robot %g mm ---" % (krav, vald))
        print(dom.text())
        print("[%d sokfragor, %.0f ms totalt]" % (port.fragor, vaggtid * 1000))

    rubrik("6. VAD ETT FORSLAG KOSTAR I TECKEN")
    # Taket lyfts bara for att MATA vad de kapade raderna hade kostat.
    tak = FO.MAX_FORSLAG
    FO.MAX_FORSLAG = 10
    try:
        spec, blad = _spec(2050.0, 1650.0)
        dom = MO.granska(spec.villkor, ST.Faktarum(spec, blad), spec,
                         sokport=katalog)
    finally:
        FO.MAX_FORSLAG = tak
    krock = [k for k in dom.krockar if k.forslag is not None][0]
    alla = list(krock.forslag.alternativ)
    krock.forslag.alternativ = []
    utan = len(krock.text())
    print("krocken utan forslag: %d tecken" % utan)
    for n in (1, 2, 3, 5, 10):
        krock.forslag.alternativ = alla[:n]
        print("  %2d forslag: forslagsblocket %4d tecken, hela krocken %4d"
              % (n, len(krock.forslag.text()), len(krock.text())))
    krock.forslag.alternativ = alla

    rubrik("7. SORTERINGEN: MINSTA SOM RACKER")
    print(json.dumps([{"namn": a.namn, "tillverkare": a.tillverkare,
                       "rackvidd_mm": a.tal}
                      for a in alla], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
