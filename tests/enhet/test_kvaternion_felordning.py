# -*- coding: utf-8 -*-
"""D12: Verifiering av kvaternionens ordning (M-143).

Uppdrag D12 i docs/uppdrag/KO_D_ogat_och_scenen.md:
"Kvaternionen. Skalär först, (x,y,z,w) = (q.Y,q.Z,q.W,q.X) — mätt i M-72."
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


def test_d12_kvat_fran_vc_motbevis_ren_rotation():
    """Den vanliga felordningen ger 180 graders felvridning för identitet/små vinklar."""
    # VC:s representation av 0 graders vridning (identitet):
    # q.X = cos(0) = 1.0, q.Y = 0, q.Z = 0, q.W = 0
    vc_identitet = _DummyVcVec(1.0, 0.0, 0.0, 0.0)

    # Korrekt omvandling via kvat_fran_vc (q.Y, q.Z, q.W, q.X):
    q_korrekt = P.kvat_fran_vc(vc_identitet)
    assert q_korrekt == [0.0, 0.0, 0.0, 1.0]
    assert H.q_vinkel_deg(q_korrekt) == pytest.approx(0.0, abs=1e-5)

    # Den vanliga felordningen: namnordning [q.X, q.Y, q.Z, q.W]
    q_felordning = [vc_identitet.X, vc_identitet.Y, vc_identitet.Z, vc_identitet.W]
    assert q_felordning == [1.0, 0.0, 0.0, 0.0]
    # Tolkat som (x, y, z, w) är w = 0, vilket motsvarar 2*acos(0) = 180 grader!
    vinkel_fel = H.q_vinkel_deg(q_felordning)
    assert vinkel_fel == pytest.approx(180.0, abs=1e-5), (
        "Den vanliga felordningen ska ge 180 graders felaktig rotation!"
    )
