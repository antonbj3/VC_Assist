# -*- coding: utf-8 -*-
"""D11: Enhetsprov för längdomvandling mellan millimeter och meter (M-142).

Uppdrag D11 i docs/uppdrag/KO_D_ogat_och_scenen.md:
"M-86 mätte hela scenen i meter åt båda håll med noll drift. Enhetsbytet är
ändå en av de klassiska felkällorna. Leta i koden efter varje ställe där en
längd byter enhet och kontrollera att omvandlingen finns på båda hållen.
Ett ställe som bara omvandlar åt ena hållet är en bugg som väntar."
"""
from __future__ import annotations

import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in [_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "ext", "vc_addon", "vc_assist")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import oga_harledning as H
import oga_provtagning as P
from vc_assist_svc.layout.matt import Langd, MM_PER_M, Enhetsfel


def test_d11_kanonisk_omvandling_bada_hallen():
    """Ögats brygga har symmetrisk omvandling mm <-> m via KANONISK_TILL_VC."""
    assert P.KANONISK_TILL_VC == 1000.0

    # Läsning från VC (mm -> m)
    class DummyPos:
        X, Y, Z = 1250.0, -3500.0, 750.0

    p_m = [DummyPos.X / P.KANONISK_TILL_VC,
           DummyPos.Y / P.KANONISK_TILL_VC,
           DummyPos.Z / P.KANONISK_TILL_VC]
    assert p_m == [1.25, -3.5, 0.75]

    # Skrivning till VC (m -> mm)
    p_mm = [p_m[0] * P.KANONISK_TILL_VC,
            p_m[1] * P.KANONISK_TILL_VC,
            p_m[2] * P.KANONISK_TILL_VC]
    assert p_mm == [1250.0, -3500.0, 750.0]

    # Rundtur noll drift
    for i in range(3):
        assert getattr(DummyPos, "XYZ"[i]) == p_mm[i]


def test_d11_layout_langd_typ_symmetri():
    """Langd-typen i svc garanterar tvåvägskonvertering utan enhetsglidning."""
    assert MM_PER_M == 1000.0

    l1 = Langd.m(2.5)
    assert l1.som_m == 2.5
    assert l1.som_mm == 2500.0

    l2 = Langd.mm(2500.0)
    assert l2.som_m == 2.5
    assert l2.som_mm == 2500.0

    # Rundtur
    assert Langd.mm(l1.som_mm).som_m == l1.som_m
    assert Langd.m(l2.som_m).som_mm == l2.som_mm

    # Skydd mot bart tal utan enhet
    with pytest.raises(Enhetsfel):
        Langd(1.5)


def test_d11_ledenhet_igenkanning_och_symmetri():
    """_ledenhet i oga_harledning ska känna igen både koder och enhetsnamn."""
    # Rotationsleder -> deg
    for t in ["deg", "rot", "R", "rotational", 0]:
        assert H._ledenhet(t) == "deg", f"Typ {t} mappades inte till deg"

    # Skjutleder -> mm
    for t in ["mm", "trans", "T", "translational", 1]:
        assert H._ledenhet(t) == "mm", f"Typ {t} mappades inte till mm"

    # Okända typer -> None (ingen gissad enhet)
    for okand in [None, "okand", "volt", 99]:
        assert H._ledenhet(okand) is None


def test_d11_ledanalys_kanner_igen_deg_och_mm():
    """Ledanalys ska inte flagga deg- eller mm-leder som enhetslösa."""
    rader = [{"t": 0.05 * i, "joints": {"r1": [i * 1.0, i * 2.0]}} for i in range(10)]
    analys = H.Ledanalys(
        rader,
        granser={"r1": [[-180.0, 180.0], [0.0, 1000.0]]},
        typer={"r1": ["deg", "mm"]}
    ).analysera()["r1"]

    assert analys["enhetslosa_leder"] == [], (
        f"Leder flaggades felaktigt som enhetslösa: {analys['enhetslosa_leder']}"
    )
    assert analys["led"][0]["enhet"] == "deg"
    assert analys["led"][1]["enhet"] == "mm"
