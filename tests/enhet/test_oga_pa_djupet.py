# -*- coding: utf-8 -*-
"""L1: ogat pa djupet (fas 15). Inspelade och syntetiska serier, ingen VC.

Fasens grind (70_faser.md): tidsserie over VARJE objekt i scenen, PLC-vardena
pa samma axel, och domar som faller pa sekvens, timing, grepp, kollision och
genomflode - var och en med en trasig cell som MASTE fallas. Hopfogningens
osakerhet matt, inte antagen.

Matningen: docs/matningar/M-65.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests"))

import celler                  # noqa: E402
import oga_analys as A         # noqa: E402
import oga_harledning as H     # noqa: E402
import oga_kontrakt as K       # noqa: E402
import oga_provtagning as P    # noqa: E402


# ---- 1. hela scenen, i EN enhet -----------------------------------------
#
# M-65 §2: VcScen.pose() delade med KANONISK_TILL_VC pa vagen in, men
# VcScen.poser_alla() gjorde det inte. Rollerna lag i meter och scenen i
# millimeter, i samma serie. Analysen multiplicerar med 1000 for att fa
# millimeter, sa varje bakgrundsobjekts rorelse blev tusen ganger for stor.
# Osynligt i varje syntetisk cell, for de skriver meter direkt.

class _V(object):
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z


class _Q(object):
    X, Y, Z, W = 1.0, 0.0, 0.0, 0.0        # skalar-forst, M-11


class _M(object):
    def __init__(self, p):
        self.P = _V(*p)

    def getQuaternion(self):
        return _Q()


class _Nod(object):
    def __init__(self, namn, p):
        self.Name = namn
        self.WorldPositionMatrix = _M(p)
        self.Behaviours = []

    def findNode(self, namn):
        return None


class _App(object):
    def __init__(self, komponenter):
        self.Components = list(komponenter)

    def findComponent(self, namn):
        for c in self.Components:
            if c.Name == namn:
                return c
        return None


class _Sim(object):
    def update(self):
        pass


def test_scenens_poser_ar_i_samma_enhet_som_rollernas():
    """TRASIG FIXTUR (M-65 §2). Samma VC-lage, 1000 mm, last tva vagar.

    Foll fore lagningen: pose() gav 1,0 (meter) och poser_alla() gav 1000,0
    (VC:s millimeter). En serie som bar tva enheter under samma nyckel ar den
    fella M-33 redan beskrev: ratt i det vanliga fallet, fel med tusen i alla
    absoluta tal.
    """
    scen = P.VcScen(_App([_Nod("Del", (1000.0, 0.0, 0.0)),
                          _Nod("Staket", (1000.0, 0.0, 0.0))]), _Sim())
    scen.konfigurera({"parts": ["Del"]})
    roll = scen.pose("Del")["p"]
    bakgrund = scen.poser_alla()["Staket"]["p"]
    assert roll == bakgrund, (
        "samma lage lastes till %r som roll och %r som scen" % (roll, bakgrund))
    assert abs(roll[0] - 1.0) < 1e-12, "kanonisk enhet i serien ar meter (M-33)"


def test_ett_bakgrundsobjekt_som_driver_en_halv_millimeter_ar_stilla():
    """Foljden av enhetsfelet, som en dom.

    En orord komponents WorldPositionMatrix driver nagra tiondels millimeter
    (M-10 ska satta talet). Med scenen i millimeter blev 0,5 mm till 500 mm i
    analysen, och ett orort stallage foll som 'oombedd rorelse'. Har gar hela
    vagen: VcScen -> Provtagare -> Analys, utan VC.
    """
    stallage = _Nod("Stallage", (3000.0, 1000.0, 0.0))
    scen = P.VcScen(_App([_Nod("Del", (0.0, 0.0, 750.0)),
                          _Nod("Gripper", (0.0, 0.0, 1400.0)), stallage]), _Sim())
    plan = {"parts": ["Del"], "tools": ["Gripper"], "rate_hz": 20.0,
            "forvantat_rorliga": ["Del", "Gripper"]}
    p = P.Provtagare(scen, plan).starta(0.0)
    for i in range(40):
        # 0,4 mm driv i VC:s enhet, fram och tillbaka. Inte 0,5: den ligger
        # EXAKT pa ROR_SIG_MM, och 3000,5/1000 - 3,0 ar 0,5000000000001 i
        # flyttal - da avgor avrundningen domen, inte scenen.
        stallage.WorldPositionMatrix = _M((3000.0 + 0.4 * (i % 2), 1000.0, 0.0))
        p.kanske_prov(i * 0.05)
    a = A.Analys(p.data(), plan)
    a.rapport()
    assert a.harledt["scene"]["oombedd"] == [], a.harledt["scene"]["oombedd"]
    assert "Stallage" in a.harledt["scene"]["stilla"]


def _serie(punkter, dt=0.05):
    return [(i * dt, tuple(p), (0.0, 0.0, 0.0, 1.0), True)
            for i, p in enumerate(punkter)]


def test_jitter_under_golvet_integrerar_inte_till_vag():
    """TRASIG FIXTUR (M-65 §2). 0,5 mm fram och tillbaka i 201 prov.

    Fore lagningen summerades varje steg: 100 mm 'vag' for ett objekt som
    aldrig lamnade sin halva millimeter. Brus integrerar till noll - det ar
    skillnaden mot rorelse, och det ar den som mats.
    """
    p = H.rorelseprofil(_serie([(0.0005 * (i % 2), 0.0, 0.0) for i in range(201)]))
    assert p["stilla"] is True
    assert p["vaglangd_mm"] == 0.0
    assert abs(p["brus_mm"] - 100.0) < 1e-6, "bruset raknas, men som brus"
    assert p["forflyttning_mm"] < 1e-9


def test_en_langsam_drift_under_golvet_ar_anda_en_rorelse():
    """Den andra riktningen. 0,1 mm per prov, alltid at samma hall: inget
    enskilt steg passerar ROR_SIG_MM, men nettot ar 19,9 mm. Det ar en
    rorelse, och en grind som bara ser steg over golvet hade missat den."""
    p = H.rorelseprofil(_serie([(0.0001 * i, 0.0, 0.0) for i in range(200)]))
    assert p["stilla"] is False
    assert abs(p["forflyttning_mm"] - 19.9) < 1e-6
    assert p["t_forsta"] == 0.0 and p["intervall"]
    o = H.Scenoversikt([{"t": i * 0.05, "scene": {"x": {"p": [0.0001 * i, 0, 0],
                                                          "q": [0, 0, 0, 1]}},
                         "scenlast": True} for i in range(200)],
                       forvantat_rorliga=[])
    assert o.oombedd_rorelse() and o.oombedd_rorelse()[0]["objekt"] == "x"
