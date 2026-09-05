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


def test_d12_trasig_fixtur_faller_i_ogat():
    """En cell med den vanliga felordningen fälls av ögat under roterande transport."""
    # Roboten roterar verktyget 90 grader kring Z under bärsträckan medan delen hålls fast.
    # Med korrekt ordning roterar delen tillsammans med verktyget (stabil i verktygsramen -> PASS).
    # Med den vanliga felordningen roteras inte förskjutningen i verktygsramen -> greppet bryts -> FAIL!
    dt = 0.05
    n = 40
    rader_korrekt = []
    rader_fel = []
    offset = (0.1, 0.0, 0.0)

    for s in range(n):
        t = s * dt
        u = s / float(n - 1)
        vinkel = u * 90.0
        rad = math.radians(vinkel) / 2.0
        # I VC: q.X = cos(rad), q.Y = 0, q.Z = 0, q.W = sin(rad)
        vc_q = _DummyVcVec(math.cos(rad), 0.0, 0.0, math.sin(rad))

        q_korr = P.kvat_fran_vc(vc_q)
        q_fel = [vc_q.X, vc_q.Y, vc_q.Z, vc_q.W]

        vp = [u * 1.0, 0.0, 0.75]
        dp = [vp[i] + H.q_rotera(q_korr, offset)[i] for i in range(3)]

        rader_korrekt.append({
            "t": round(t, 4),
            "parts": {"del": {"p": dp, "q": q_korr}},
            "tools": {"gripare": {"p": vp, "q": q_korr}},
            "sig": {"grip_out": True},
        })
        rader_fel.append({
            "t": round(t, 4),
            "parts": {"del": {"p": dp, "q": q_fel}},
            "tools": {"gripare": {"p": vp, "q": q_fel}},
            "sig": {"grip_out": True},
        })

    plan = {
        "template": "fixtur_kvat",
        "parts": ["del"],
        "tools": ["gripare"],
        "signals": ["grip_out"],
        "rate_hz": 20.0,
        "targets": {"del": {"p": dp, "tol_mm": 10.0}},
    }

    data_korr = {
        "v": 1, "template": "fixtur_kvat",
        "run": {"started": "2026-09-05T12:00:00", "dur_s": round(n * dt, 3), "samples": n, "rate_hz": 20.0},
        "tracked": {"parts": ["del"], "tools": ["gripare"], "signals": ["grip_out"], "pairs": [], "joints": [], "stations": []},
        "rows": rader_korrekt,
    }
    data_fel = dict(data_korr, rows=rader_fel)

    # Korrekt serie ska ge PASS
    _, rap_korr, _ = A.doma(data_korr, plan)
    assert rap_korr.dom[0] == "PASS", f"Korrekt serie gav oväntat {rap_korr.dom}"

    # Trasig fixtur (felordning) MÅSTE fällas av ögat
    _, rap_fel, _ = A.doma(data_fel, plan)
    assert rap_fel.dom[0] == "FAIL", "Trasig fixtur med felordning fälldes inte!"
    assert "grepp" in rap_fel.dom[1] or "gled" in rap_fel.dom[1], (
        f"Felaktig orsak i domen: {rap_fel.dom[1]}"
    )


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


