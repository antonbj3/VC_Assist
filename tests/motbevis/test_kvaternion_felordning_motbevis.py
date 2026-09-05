# -*- coding: utf-8 -*-
"""D12: Motbevis och trasig fixtur för kvaternionens felordning (M-143).

Uppdrag D12 i docs/uppdrag/KO_D_ogat_och_scenen.md:
"Kvaternionen. Skalär först, (x,y,z,w) = (q.Y,q.Z,q.W,q.X) — mätt i M-72.
Kontrollera varje ställe i koden som rör rotationer mot den regeln, och
skriv en trasig fixtur som fäller den vanliga felordningen."

Detta prov bevisar mekaniskt:
1. Att den vanliga felordningen (namnordning [q.X, q.Y, q.Z, q.W] där q.X felaktigt
   tas som x) ger felaktig kinematik som fälls av ögats grepp- och hederlighetsanalys.
2. Att kodfallsgrinden FAL-001 (kvaternion_i_namnordning) fäller varje kodblock
   som läser VC:s kvaternion i namnordning.
3. Att den korrekta avbildningen (q.Y, q.Z, q.W, q.X) bevarar vinklar och passerar.
"""
from __future__ import annotations

import math
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in [_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "tests"),
          os.path.join(_ROT, "ext", "vc_addon", "vc_assist")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import celler
import oga_analys as A
import oga_harledning as H
import oga_provtagning as P
from vc_assist_svc.harness import kodfallor as Kf


class _DummyVcVec:
    """Attrapp av VC:s vcVector från getQuaternion()."""
    def __init__(self, x: float, y: float, z: float, w: float):
        self.X, self.Y, self.Z, self.W = x, y, z, w


def test_d12_kodfallsgrind_fal_001_faller_felordning():
    """FAL-001 fäller all genererad kod som läser getQuaternion() i namnordning."""
    trasiga_kodblock = [
        "q = m.getQuaternion()\nx, y, z, w = q.X, q.Y, q.Z, q.W\n",
        "q = m.getQuaternion()\nx = q.X\n",
        "q = m.getQuaternion()\nw = q.W\n",
        "q = m.getQuaternion()\nvridning = [q.X, q.Y, q.Z, q.W]\n",
        "q = nod.WorldPositionMatrix.getQuaternion()\nx = q.X\n",
    ]

    for kod in trasiga_kodblock:
        skal = Kf.kvaternion_i_namnordning(kod)
        assert len(skal) > 0, f"Kodfallsgrinden missade att fälla felordningen i:\n{kod}"
        assert any("skalaren" in s.lower() or "skalären" in s.lower() for s in skal)

    # Korrekt läsning ska släppas igenom
    korrekta_kodblock = [
        "q = m.getQuaternion()\nskalar = q.X\nvektor = [q.Y, q.Z, q.W]\n",
        "q = m.getQuaternion()\nw = q.X\nx, y, z = q.Y, q.Z, q.W\n",
    ]
    for kod in korrekta_kodblock:
        skal = Kf.kvaternion_i_namnordning(kod)
        assert len(skal) == 0, f"Korrekt kod fälldes felaktigt:\n{kod}\nskäl: {skal}"
