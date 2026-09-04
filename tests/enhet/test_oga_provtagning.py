# -*- coding: utf-8 -*-
"""L1: ogats provtagare, med en falsk scen i stallet for VC.

Det viktigaste testet har ar kvaternionens ordning: MATT i M-11, och inskrivet
som tabell sa en framtida omskrivning inte tyst kan vanda tillbaka den.
"""
import json
import math
import os
import sys

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "tests")))

import celler                    # noqa: E402
import oga_analys as A           # noqa: E402
import oga_provtagning as P      # noqa: E402


class VcVektor(object):
    def __init__(self, x, y, z, w=0.0):
        self.X, self.Y, self.Z, self.W = x, y, z, w


# Tabellen ur M-11, mätt i VC 4.10: gir kring Z -> (q.X, q.Y, q.Z, q.W)
M11 = [
    (0.0,   (1.0000, 0.0, 0.0, 0.0000)),
    (30.0,  (0.9659, 0.0, 0.0, 0.2588)),
    (90.0,  (0.7071, 0.0, 0.0, 0.7071)),
    (180.0, (0.0000, 0.0, 0.0, 1.0000)),
]


@pytest.mark.parametrize("grader,vc", M11)
def test_kvaternionen_las_skalar_forst(grader, vc):
    x, y, z, w = P.kvat_fran_vc(VcVektor(*vc))
    assert abs(w - math.cos(math.radians(grader) / 2)) < 1e-3, "w ska vara cos(theta/2)"
    assert abs(z - math.sin(math.radians(grader) / 2)) < 1e-3, "z ska vara sin(theta/2)"
    assert abs(x) < 1e-6 and abs(y) < 1e-6


def test_fellasning_skulle_gora_en_orord_detalj_till_en_halvvarvsvridning():
    """Skalet till att den har omrakningen finns, uttryckt som ett prov."""
    vc = VcVektor(1.0, 0.0, 0.0, 0.0)          # helt orord
    ratt = P.kvat_fran_vc(vc)
    assert A.q_vinkel_deg(ratt) < 1e-6
    fel = (vc.X, vc.Y, vc.Z, vc.W)             # rakt av, som namnen inbjuder till
    assert abs(A.q_vinkel_deg(fel) - 180.0) < 1e-6


# ---- provtagaren --------------------------------------------------------

class FalskScen(P.Scen):
    def __init__(self, bana=None):
        self.bana = bana or {}
        self.n_uppdateringar = 0
        self.t = 0.0
        self.saknade = []

    def uppdatera(self):
        self.n_uppdateringar += 1

    def pose(self, spec):
        if spec not in self.bana:
            self.saknade.append({"spec": spec, "varfor": "finns inte"})
            return None
        return self.bana[spec]

    def signal(self, spec):
        return spec == "C/hog"


def test_en_jamn_pump_ger_exakt_den_begarda_takten():
    p = P.Provtagare(FalskScen({"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}}),
                     {"parts": ["del"], "rate_hz": 20.0}).starta(0.0)
    for i in range(1000):                      # 200 Hz pump, 5 s
        p.kanske_prov(i * 0.005)
    tider = [r["t"] for r in p.rader]
    steg = [round(tider[i] - tider[i - 1], 6) for i in range(1, len(tider))]
    assert set(steg) == {0.05}
    assert abs(len(tider) / tider[-1] - 20.0) < 0.3


def test_en_ojamn_pump_ger_lagre_takt_men_aldrig_drift_eller_skur():
    """Ogat kan inte provta snabbare an pumpen slar. Det ska synas som en
    LAGRE takt, aldrig som drift och aldrig som en skur av tata prov.

    Tidsstamplarna ar de VERKLIGA tidpunkterna - en tidsstampel ska saga nar
    matningen gjordes, inte vilket rutnat den horde till.
    """
    p = P.Provtagare(FalskScen({"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}}),
                     {"parts": ["del"], "rate_hz": 20.0}).starta(0.0)
    t = 0.0
    ojamna = [0.005, 0.005, 0.05, 0.005, 0.2, 0.005, 0.005, 0.05]
    for i in range(400):
        t += ojamna[i % len(ojamna)]
        p.kanske_prov(t)
        assert abs((p.nasta_t / 0.05) - round(p.nasta_t / 0.05)) < 1e-6, \
            "rutnatet drev till %r" % p.nasta_t

    tider = [r["t"] for r in p.rader]
    steg = [tider[i] - tider[i - 1] for i in range(1, len(tider))]
    assert min(steg) >= 0.05 - 1e-9, "provtog i skur: kortaste steget %r" % min(steg)
    takt = len(tider) / tider[-1]
    assert takt <= 20.0 + 1e-6, "provtog snabbare an begart: %.2f Hz" % takt
    assert takt > 5.0, "takten kollapsade till %.2f Hz" % takt


def test_ingen_provtagning_innan_start_och_ingen_efter_stopp(tmp_path):
    p = P.Provtagare(FalskScen({"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}}),
                     {"parts": ["del"]}, sokvag=str(tmp_path / "e.json"))
    assert p.kanske_prov(1.0) is False
    p.starta(0.0)
    assert p.kanske_prov(0.0) is True
    p.stoppa()
    assert p.kanske_prov(99.0) is False


def test_provtagaren_uppdaterar_scenen_fore_varje_lasning():
    """M-11: varldsmatrisen slapar utan sim.update()."""
    scen = FalskScen({"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}})
    p = P.Provtagare(scen, {"parts": ["del"], "rate_hz": 20.0}).starta(0.0)
    for i in range(5):
        p.kanske_prov(i * 0.05)
    assert scen.n_uppdateringar == 5


def test_det_som_inte_gick_att_lasa_syns_i_underlaget(tmp_path):
    """En tyst lucka blir annars en dom pa ofullstandig grund."""
    scen = FalskScen({"finns": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}})
    p = P.Provtagare(scen, {"parts": ["finns", "saknas"], "rate_hz": 20.0},
                     sokvag=str(tmp_path / "e.json")).starta(0.0)
    p.kanske_prov(0.0)
    d = p.data()
    assert "saknade" in d and d["saknade"][0]["spec"] == "saknas"
    assert "saknas" not in d["rows"][0]["parts"]


def test_serien_skrivs_inkrementellt_och_ar_lasbar_mitt_i(tmp_path):
    sokvag = str(tmp_path / "eyes.json")
    p = P.Provtagare(FalskScen({"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}}),
                     {"parts": ["del"], "rate_hz": 20.0}, sokvag=sokvag).starta(0.0)
    for i in range(P.SKRIV_VAR_N_RAD):
        p.kanske_prov(i * 0.05)
    with open(sokvag) as f:
        d = json.load(f)
    assert d["partial"] is True and len(d["rows"]) == P.SKRIV_VAR_N_RAD
    p.stoppa()
    with open(sokvag) as f:
        d = json.load(f)
    assert "partial" not in d


def test_signaler_provtas_som_bool():
    scen = FalskScen({"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}})
    p = P.Provtagare(scen, {"parts": ["del"], "signals": ["C/hog", "C/lag"],
                            "rate_hz": 20.0}).starta(0.0)
    p.kanske_prov(0.0)
    assert p.rader[0]["sig"] == {"C/hog": True, "C/lag": False}


# ---- hela vagen: provtagare -> analys -> dom ----------------------------

class BanScen(P.Scen):
    """Spelar upp en fardig cell som om den vore en scen."""

    def __init__(self, rader):
        self.rader = rader
        self.i = 0
        self.saknade = []

    def _nu(self):
        return self.rader[min(self.i, len(self.rader) - 1)]

    def uppdatera(self):
        self.i += 1

    def pose(self, spec):
        r = self._nu()
        for grupp in ("parts", "tools"):
            if spec in r.get(grupp, {}):
                return r[grupp][spec]
        return None

    def signal(self, spec):
        return self._nu().get("sig", {}).get(spec, False)


def test_provtagare_och_analys_hanger_ihop_hela_vagen(tmp_path):
    """Den bra cellen provtagen genom provtagaren ska fortfarande ge PASS."""
    b, plan = celler.bra()
    kalla = b.data()
    scen = BanScen(kalla["rows"])
    scen.i = -1
    p = P.Provtagare(scen, {"template": "plocka_och_placera",
                            "parts": ["del"], "tools": ["gripper"],
                            "signals": ["grip_out"], "rate_hz": 20.0},
                     sokvag=str(tmp_path / "eyes.json")).starta(0.0)
    for i in range(len(kalla["rows"])):
        p.kanske_prov(i * 0.05)
    p.stoppa()
    with open(str(tmp_path / "eyes.json")) as f:
        provtaget = json.load(f)
    assert provtaget["run"]["samples"] == len(kalla["rows"])
    text, rapport, _a = A.doma(provtaget, plan)
    assert rapport.dom[0] == "PASS", rapport.dom


# ---- bandrivaren --------------------------------------------------------

class SkrivbarScen(FalskScen):
    def __init__(self):
        FalskScen.__init__(self, {})
        self.satta = []

    def satt_pose(self, spec, punkt):
        self.satta.append((spec, list(punkt)))
        self.bana[spec] = {"p": list(punkt), "q": [0, 0, 0, 1]}
        return True


def test_bandrivaren_flyttar_ett_steg_per_intervall():
    scen = SkrivbarScen()
    d = P.Bandrivare(scen, {"objekt": ["a", "b"], "dt": 0.05,
                            "punkter": [[[0, 0, 0], [0, 0, 1]],
                                        [[1, 0, 0], [1, 0, 1]],
                                        [[2, 0, 0], [2, 0, 1]]]}).starta(0.0)
    assert d.kanske_flytta(0.0) is True
    assert d.kanske_flytta(0.01) is False, "far inte flytta tva ganger i samma steg"
    assert d.kanske_flytta(0.05) is True
    assert [s for s, _ in scen.satta] == ["a", "b", "a", "b"]
    assert scen.satta[2][1] == [1, 0, 0]


def test_bandrivaren_stannar_pa_sista_punkten():
    scen = SkrivbarScen()
    d = P.Bandrivare(scen, {"objekt": ["a"], "dt": 0.05,
                            "punkter": [[[0, 0, 0]], [[1, 0, 0]]]}).starta(0.0)
    d.kanske_flytta(0.0)
    d.kanske_flytta(0.05)
    d.kanske_flytta(5.0)
    assert d.klar is True
    assert scen.satta[-1][1] == [1, 0, 0], "ska sta kvar pa sista punkten"
    assert d.kanske_flytta(9.0) is False


def test_bandrivaren_hoppar_over_missade_steg_utan_att_skena():
    """Ett langt uppehall ska ge ETT hopp till ratt punkt, inte en skur."""
    scen = SkrivbarScen()
    punkter = [[[i, 0, 0]] for i in range(20)]
    d = P.Bandrivare(scen, {"objekt": ["a"], "dt": 0.05, "punkter": punkter}).starta(0.0)
    d.kanske_flytta(0.0)
    d.kanske_flytta(0.5)          # tio steg pa en gang
    assert len(scen.satta) == 2
    assert scen.satta[-1][1] == [10, 0, 0]
