# -*- coding: utf-8 -*-
"""Handbyggda celler som tidsserier: en bra och en rad trasiga.

Varje trasig cell isolerar EN felklass, sa en fallning gar att harleda till sin
orsak. Serierna har samma form som eyes.json (41_ogat_kontrakt.md) och kraver
ingen VC - ogat ska ga att prova utan det system det ska doma.

Kalla: docs/spec/83_scenarier.md
"""
from __future__ import annotations

import math

RATE = 20.0
DT = 1.0 / RATE
Q0 = [0.0, 0.0, 0.0, 1.0]


def _q_z(grader):
    a = math.radians(grader) / 2.0
    return [0.0, 0.0, math.sin(a), math.cos(a)]


def _lerp(a, b, u):
    return [a[i] + (b[i] - a[i]) * u for i in range(3)]


class Bygge(object):
    """Bygger en tidsserie steg for steg."""

    def __init__(self, template, floor_z=0.0):
        self.template = template
        self.floor_z = floor_z
        self.rader = []
        self.t = 0.0

    def steg(self, del_p, verktyg_p, del_q=None, verktyg_q=None, sig=None,
             stat=None, mind=None, hit=None):
        r = {
            "t": round(self.t, 4),
            "parts": {"del": {"p": list(del_p), "q": list(del_q or Q0)}},
            "tools": {"gripper": {"p": list(verktyg_p), "q": list(verktyg_q or Q0)}},
        }
        if sig:
            r["sig"] = dict(sig)
        if stat:
            r["stat"] = dict(stat)
        if mind:
            r["mind"] = dict(mind)
        if hit:
            r["hit"] = list(hit)
        self.rader.append(r)
        self.t += DT
        return self

    def data(self):
        return {
            "v": 1,
            "template": self.template,
            "run": {"started": "2026-09-04T17:00:00", "dur_s": round(self.t, 3),
                    "samples": len(self.rader), "rate_hz": RATE},
            "tracked": {"parts": ["del"], "tools": ["gripper"],
                        "signals": ["grip_out"], "pairs": []},
            "rows": self.rader,
        }


def plan(tol_mm=25.0, mal=(1.0, 0.0, 0.75), floor_z=0.0, stationer=None):
    return {
        "targets": {"del": {"p": list(mal), "tol_mm": tol_mm}},
        "floor_z": floor_z,
        "movers": {"grip_out": "gripper"},
        "stations": stationer or {},
    }


# ---- cellerna -----------------------------------------------------------

def _grundcell(template, glid_deg=0.0, slut=None, teleport_m=0.0,
               bar_z=1.0, tappa=False):
    """Plocka och placera: verktyget gar ner, greppar, bar, slapper.

    Alla trasiga varianter ar samma rorelse med EN sak andrad, sa en skillnad
    i domen gar att harleda till den andringen.
    """
    b = Bygge(template)
    start = [0.0, 0.0, 0.75]
    mal = list(slut or [1.0, 0.0, 0.75])

    # 1. verktyget narmar sig uppifran, delen star still (20 steg = 1,0 s)
    for i in range(20):
        u = i / 19.0
        b.steg(start, _lerp([0.0, 0.0, 1.4], [0.0, 0.0, 0.75 + teleport_m], u),
               sig={"grip_out": False})

    # 2. lyft: delen foljer verktyget (30 steg = 1,5 s)
    for i in range(30):
        u = i / 29.0
        vp = _lerp([0.0, 0.0, 0.75 + teleport_m], [0.0, 0.0, bar_z + teleport_m], u)
        dp = [vp[0], vp[1], vp[2] - teleport_m]
        b.steg(dp, vp, del_q=_q_z(glid_deg * u), sig={"grip_out": True})

    # 3. transport i sidled (40 steg = 2,0 s)
    for i in range(40):
        u = i / 39.0
        vp = _lerp([0.0, 0.0, bar_z + teleport_m], [mal[0], mal[1], bar_z + teleport_m], u)
        dp = [vp[0], vp[1], vp[2] - teleport_m]
        if tappa and u > 0.5:
            # greppet slapper mitt i transporten och delen faller till golvet
            dp = [_lerp([0.0, 0.0, bar_z], [mal[0], mal[1], bar_z], 0.5)[0],
                  0.0, max(0.0, bar_z - 9.81 * ((u - 0.5) * 2.0) ** 2 / 2.0)]
        b.steg(dp, vp, del_q=_q_z(glid_deg), sig={"grip_out": True})

    # 4. satt ned och slapp (20 steg = 1,0 s)
    for i in range(20):
        u = i / 19.0
        vp = _lerp([mal[0], mal[1], bar_z + teleport_m], [mal[0], mal[1], mal[2] + teleport_m], u)
        dp = [vp[0], vp[1], vp[2] - teleport_m]
        if tappa:
            dp = [_lerp([0.0, 0.0, bar_z], [mal[0], mal[1], bar_z], 0.5)[0], 0.0, 0.0]
        b.steg(dp, vp, del_q=_q_z(glid_deg), sig={"grip_out": u < 0.5})

    # 5. verktyget lamnar, delen ligger kvar (20 steg = 1,0 s)
    slutlage = b.rader[-1]["parts"]["del"]["p"]
    for i in range(20):
        u = i / 19.0
        b.steg(slutlage, _lerp([mal[0], mal[1], mal[2] + teleport_m],
                               [mal[0], mal[1], 1.4], u),
               del_q=_q_z(glid_deg), sig={"grip_out": False})
    return b


def bra():
    return _grundcell("plocka_och_placera"), plan()


def teleport():
    """Greppet bildas medan verktyget ar 800 mm bort. VC:s standardgrepp ar
    icke-fysiskt, sa en MISS ser ut som en lyckad plockning utan den har grinden."""
    return _grundcell("teleport", teleport_m=0.8), plan()


def glider():
    """Delen vrider sig 15 grader i verktygets ram under barandet."""
    return _grundcell("glider", glid_deg=15.0), plan()


def tappad():
    return _grundcell("tappad", tappa=True), plan()


def fel_placerad():
    """Slutar 80 mm fran malet - inom synhall, utanfor toleransen."""
    return _grundcell("fel_placerad", slut=[1.08, 0.0, 0.75]), plan()


def aldrig_gripen():
    """Verktyget gor hela rorelsen, delen star still hela tiden."""
    b = Bygge("aldrig_gripen")
    still = [0.0, 0.0, 0.75]
    banor = [([0.0, 0.0, 1.4], [0.0, 0.0, 0.75], 20),
             ([0.0, 0.0, 0.75], [0.0, 0.0, 1.0], 30),
             ([0.0, 0.0, 1.0], [1.0, 0.0, 1.0], 40),
             ([1.0, 0.0, 1.0], [1.0, 0.0, 1.4], 20)]
    for a, c, n in banor:
        for i in range(n):
            b.steg(still, _lerp(a, c, i / float(n - 1)), sig={"grip_out": True})
    return b, plan()


def explosion():
    """Numerisk explosion: verktyg och del far orimlig fart."""
    b = Bygge("explosion")
    for i in range(40):
        x = 0.0 if i < 20 else (i - 20) * 5.0     # 5 m per 0,05 s = 100 m/s
        b.steg([x, 0.0, 0.75], [x, 0.0, 0.75], sig={"grip_out": True})
    return b, plan()


def under_golvet():
    b = _grundcell("under_golvet")
    for r in b.rader[60:80]:
        r["parts"]["del"]["p"][2] = -0.22
    return b, plan()


def kollision():
    b = _grundcell("kollision")
    b.rader[45]["hit"] = ["gripper_finger", "fixtur_vagg"]
    for i, r in enumerate(b.rader):
        d = 200.0 if i < 40 else (2.0 if i == 45 else 50.0)
        r["mind"] = {"gripper+fixtur": {"d_mm": d, "p1": [0, 0, 0], "p2": [0, 0, 0]}}
    return b, plan()


def kort_uppehall():
    """Stationen slapper ut delen fore transportorens eftersläpning gatt ut."""
    b = _grundcell("kort_uppehall")
    for i, r in enumerate(b.rader):
        inne = 1 if 40 <= i < 48 else 0        # 8 prov = 0,4 s
        r["stat"] = {"station1": {"in": 1 if i >= 40 else 0, "out": 1 if i >= 48 else 0}}
        r["stat"]["station1"]["in"] = 1 if i >= 40 else 0
    return b, plan(stationer={"station1": {"dwell_req_s": 2.0}})


def for_fa_prov():
    b = Bygge("for_fa_prov")
    for i in range(4):
        b.steg([0.0, 0.0, 0.75], [0.0, 0.0, 1.0], sig={"grip_out": False})
    return b, plan()


ALLA = {
    "bra": bra,
    "teleport": teleport,
    "glider": glider,
    "tappad": tappad,
    "fel_placerad": fel_placerad,
    "aldrig_gripen": aldrig_gripen,
    "explosion": explosion,
    "under_golvet": under_golvet,
    "kollision": kollision,
    "kort_uppehall": kort_uppehall,
    "for_fa_prov": for_fa_prov,
}
