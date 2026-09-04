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


# ---- hela scenen ---------------------------------------------------------
#
# Operatörens skärpta krav: ögat provtar HELA scenen, inte bara de utpekade
# objekten. `parts` och `tools` är en ROLLTILLDELNING ovanpå, inte ett filter.

class ScenScen(P.Scen):
    """En scen med roller OCH bakgrund, plus en styrbar avläsningskostnad."""

    def __init__(self, roller, bakgrund, klocka=None, kostnad_s=0.0):
        self.roller = dict(roller)
        self.bakgrund = dict(bakgrund)
        self.klocka = klocka
        self.kostnad_s = kostnad_s
        self.n_scenlasningar = 0
        self.saknade = []
        self.plan = {}

    def konfigurera(self, plan):
        self.plan = dict(plan or {})
        return self

    def pose(self, spec):
        return self.roller.get(spec)

    def poser_alla(self):
        self.n_scenlasningar += 1
        if self.klocka is not None:
            self.klocka.tick(self.kostnad_s)
        return dict((n, {"p": list(v["p"]), "q": list(v["q"])})
                    for n, v in self.bakgrund.items())

    def signal(self, spec):
        return False


class Klocka(object):
    def __init__(self):
        self.t = 0.0

    def tick(self, s):
        self.t += s

    def __call__(self):
        return self.t


def _rollplan(**extra):
    p = {"parts": ["del"], "tools": ["gripper"], "rate_hz": 20.0}
    p.update(extra)
    return p


def _scenscen(klocka=None, kostnad_s=0.0, bakgrund=None):
    roller = {"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]},
              "gripper": {"p": [0, 0, 1], "q": [0, 0, 0, 1]}}
    bak = bakgrund if bakgrund is not None else {
        "stallage": {"p": [3, 1, 0], "q": [0, 0, 0, 1]},
        "staket": {"p": [-2, 0, 0], "q": [0, 0, 0, 1]}}
    return ScenScen(roller, bak, klocka=klocka, kostnad_s=kostnad_s)


def test_hela_scenen_provtas_som_standard_inte_bara_rollerna():
    scen = _scenscen()
    p = P.Provtagare(scen, _rollplan()).starta(0.0)
    for i in range(5):
        p.kanske_prov(i * 0.05)
    rad = p.rader[0]
    assert set(rad["parts"]) == {"del"} and set(rad["tools"]) == {"gripper"}
    assert set(rad["scene"]) == {"stallage", "staket"}
    assert rad["scenlast"] is True


def test_planen_kan_valja_bort_scenen_men_bara_uttryckligen():
    """Ett medvetet val, aldrig ett tyst standardvärde."""
    p = P.Provtagare(_scenscen(), _rollplan(scene="roles")).starta(0.0)
    p.kanske_prov(0.0)
    assert "scene" not in p.rader[0]
    assert p.data()["scen"]["lage"] == "roles"


def test_bara_det_som_andrats_lagras_men_en_full_rad_kommer_med_jamna_mellanrum():
    """Lagringsformen får inte svälla, och en avbruten fil ska ändå gå att läsa."""
    scen = _scenscen()
    p = P.Provtagare(scen, _rollplan()).starta(0.0)
    for i in range(P.H.SCEN_FULL_VAR_N_RAD + 2):
        scen.bakgrund["stallage"]["p"][0] += 0.001 if i == 3 else 0.0
        p.kanske_prov(i * 0.05)
    assert p.rader[0].get("scenfull") is True
    assert p.rader[1]["scene"] == {}, "en orörd rad ska inte lagra något"
    assert set(p.rader[3]["scene"]) == {"stallage"}
    fulla = [i for i, r in enumerate(p.rader) if r.get("scenfull")]
    assert fulla == [0, P.H.SCEN_FULL_VAR_N_RAD]


def test_lagringen_gar_att_packa_upp_till_en_tat_serie():
    """Läsaren ska se en tät serie oavsett hur den lagrats."""
    scen = _scenscen()
    p = P.Provtagare(scen, _rollplan()).starta(0.0)
    for i in range(10):
        scen.bakgrund["staket"]["p"][1] = i * 0.01
        p.kanske_prov(i * 0.05)
    tat = P.H.expandera(p.rader)
    assert all(set(r["scene"]) == {"stallage", "staket"} for r in tat)
    assert abs(tat[7]["scene"]["staket"]["p"][1] - 0.07) < 1e-9


def test_nya_och_borttagna_objekt_blir_handelser_i_serien():
    """En produkt som skapas eller förbrukas är just det man vill kunna se."""
    scen = _scenscen()
    p = P.Provtagare(scen, _rollplan()).starta(0.0)
    p.kanske_prov(0.0)
    scen.bakgrund["produkt_1"] = {"p": [0, 0, 0.5], "q": [0, 0, 0, 1]}
    p.kanske_prov(0.05)
    del scen.bakgrund["produkt_1"]
    p.kanske_prov(0.10)
    assert p.rader[1]["scen_nya"] == ["produkt_1"]
    assert p.rader[2]["scen_borta"] == ["produkt_1"]
    assert "produkt_1" not in P.H.expandera(p.rader)[2]["scene"]


# ---- kostnaden mäts, den antas inte --------------------------------------

def test_glesningen_utloses_av_en_MATT_kostnad_och_skrivs_ner():
    """Ögat får aldrig tyst tappa objekt. Glesar det ut ska det SÄGA det,
    med faktorn och med talet som orsakade den."""
    klocka = Klocka()
    dyrt = (P.SCEN_BUDGET_MS * 3.0) / 1000.0
    scen = _scenscen(klocka=klocka, kostnad_s=dyrt)
    p = P.Provtagare(scen, _rollplan(), klocka=klocka).starta(0.0)
    for i in range(P.GLES_FONSTER * 3):
        p.kanske_prov(i * 0.05)
    assert p.gles_faktor > 1, "kostnaden låg tre gånger över budget"
    handelse = p.glesningar[0]
    assert handelse["orsak"] == "OVER_BUDGET"
    assert handelse["median_ms"] > handelse["budget_ms"]
    rapport = p.data()["scen"]
    assert rapport["gles_faktor"] == p.gles_faktor
    assert rapport["kostnad_ms"]["median"] > P.SCEN_BUDGET_MS


def test_en_billig_scen_glesas_aldrig_ut():
    """Den andra riktningen. En degradering som alltid slår till är ingen
    degradering, bara en lägre takt."""
    klocka = Klocka()
    scen = _scenscen(klocka=klocka, kostnad_s=0.0001)
    p = P.Provtagare(scen, _rollplan(), klocka=klocka).starta(0.0)
    for i in range(P.GLES_FONSTER * 4):
        p.kanske_prov(i * 0.05)
    assert p.gles_faktor == 1 and p.glesningar == []


def test_rollerna_provtas_i_full_takt_aven_nar_scenen_glesas():
    """Det utpekade får aldrig betala för att scenen är stor."""
    klocka = Klocka()
    scen = _scenscen(klocka=klocka, kostnad_s=(P.SCEN_BUDGET_MS * 5.0) / 1000.0)
    p = P.Provtagare(scen, _rollplan(), klocka=klocka).starta(0.0)
    for i in range(60):
        p.kanske_prov(i * 0.05)
    assert p.gles_faktor > 1
    assert all("parts" in r and "tools" in r for r in p.rader), \
        "en roll får aldrig glesas bort"
    lasta = [r for r in p.rader if r.get("scenlast")]
    assert len(lasta) < len(p.rader), "scenen skulle ha glesats"


def test_glesningen_har_ett_tak_och_taket_skrivs_ner():
    """Över taket är serien inget underlag längre, och då säger ögat det i
    stället för att glesa vidare."""
    klocka = Klocka()
    scen = _scenscen(klocka=klocka, kostnad_s=1.0)          # 1000 ms per avläsning
    p = P.Provtagare(scen, _rollplan(), klocka=klocka).starta(0.0)
    for i in range(P.GLES_TAK * P.GLES_FONSTER * 2):
        p.kanske_prov(i * 0.05)
    assert p.gles_faktor == P.GLES_TAK
    assert any(g.get("orsak") == "TAK" for g in p.glesningar)


def test_en_scen_som_inte_stoder_fullscen_sager_det_i_stallet_for_att_tiga():
    p = P.Provtagare(FalskScen({"del": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}}),
                     _rollplan()).starta(0.0)
    p.kanske_prov(0.0)
    assert p.data()["scen"]["avstangd"]


# ---- kostnaden som funktion av scenens storlek ---------------------------

def test_kostnaden_vaxer_med_antalet_komponenter_och_talet_mats_har():
    """VC:s egen läskostnad kan inte mätas utan VC, men provtagarens EGEN
    kostnad går att mäta utan den. Talet skrivs ut så en förändring syns som en
    förändring.

    Det som INTE mäts här är VC:s egen kostnad för att läsa
    WorldPositionMatrix, och den är sannolikt den tyngre halvan.
    """
    import time as _time
    matt = {}
    for antal in (10, 100, 400):
        scen = _scenscen(bakgrund=dict(
            ("k%d" % i, {"p": [i, 0, 0], "q": [0, 0, 0, 1]}) for i in range(antal)))
        p = P.Provtagare(scen, _rollplan()).starta(0.0)
        t0 = _time.time()
        for i in range(20):
            p.kanske_prov(i * 0.05)
        matt[antal] = (_time.time() - t0) / 20.0 * 1000.0
    print("provtagarens egen kostnad per prov (ms): %r" % matt)
    assert matt[400] > matt[10], "kostnaden ska växa med scenen"
    assert matt[400] < 25.0, ("400 komponenter kostade %.1f ms per prov, mer än "
                              "hela pumpens tick-budget" % matt[400])


# ---- PLC på samma tidsaxel ----------------------------------------------

def test_plcvarden_skjuts_in_utifran_och_hamnar_i_samma_rad():
    """PUSH, inte pull: en OPC UA-läsning inne i pumpens tick kan blockera på
    nätverket, och då stannar både provtagningen och bryggan."""
    kalla = P.Plckalla().skjut_in({"Start": True, "Klar": False}, t=1.0)
    p = P.Provtagare(_scenscen(), _rollplan(), plckalla=kalla).starta(0.0)
    p.kanske_prov(1.0)
    assert p.rader[0]["plc"] == {"Start": True, "Klar": False}
    assert p.rader[0]["plc_alder_s"] == 0.0
    assert "plc_gammal" not in p.rader[0]


def test_ett_gammalt_plcvarde_markeras_och_gor_sig_inte_till_samtidigt():
    kalla = P.Plckalla().skjut_in({"Start": True}, t=1.0)
    p = P.Provtagare(_scenscen(), _rollplan(), plckalla=kalla).starta(0.0)
    p.kanske_prov(1.0 + P.PLC_FARSK_S * 2)
    assert p.rader[0]["plc_gammal"] is True
    assert p.rader[0]["plc_alder_s"] > P.PLC_FARSK_S


def test_ett_plcvarde_utan_tidsstampel_ar_alltid_gammalt():
    """Fail-closed: utan tidsstämpel går samtidigheten inte att styrka."""
    kalla = P.Plckalla().skjut_in({"Start": True})
    p = P.Provtagare(_scenscen(), _rollplan(), plckalla=kalla).starta(0.0)
    p.kanske_prov(0.0)
    assert p.rader[0]["plc_gammal"] is True


# ---- en falsk VC för de nya ytorna --------------------------------------

class VcMatris(object):
    def __init__(self, p, q=(1.0, 0.0, 0.0, 0.0)):
        self.P = VcVektor(*p)
        self._q = q

    def getQuaternion(self):
        return VcVektor(*self._q)


class FalskDof(object):
    def __init__(self, typ):
        self.JointServoType = typ


class FalskLed(object):
    def __init__(self, varde, lag, hog, typ="Rotational"):
        self.CurrentValue = varde
        self.MinValue = lag
        self.MaxValue = hog
        self.Dof = FalskDof(typ)


class FalskServo(object):
    def __init__(self, leder, mal=None):
        self.Joints = leder
        self._mal = mal or [0.0] * len(leder)

    def getJointTarget(self, i):
        return self._mal[i]


class FalskStatistik(object):
    ComponentsArrived = 7
    ComponentsDeparted = 5
    ComponentsCurrent = 2
    IdlePercentage = 12.5
    BusyPercentage = 60.0
    BlockedPercentage = 27.5
    BreakPercentage = 0.0
    State = "BUSY"


class FalskDetektor(object):
    def __init__(self):
        self.NodeListA = None
        self.NodeListB = None
        self.Tolerance = None
        self.DisplayMinimumDistance = None
        self.StopOnCollision = None
        self.Active = False
        # VC:s varldsenhet ar MILLIMETER (M-33). Attrappen talar VC:s sprak.
        self.avstand = 12.0
        self.traffar = False

    def testMinimumDistance(self):
        return self.avstand <= (self.Tolerance or 0.0)

    def getMinimumDistanceDistance(self):
        return self.avstand

    def getMinimumDistancePoint1(self):
        return VcVektor(0.0, 0.0, 0.0)

    def getMinimumDistancePoint2(self):
        return VcVektor(self.avstand, 0.0, 0.0)

    def testAllCollisions(self):
        return self.traffar

    def getHitNodeA(self):
        return FalskNamn("finger")

    def getHitNodeB(self):
        return FalskNamn("vagg")

    def getHitFeatureA(self):
        return FalskNamn("Face_12")

    def getHitFeatureB(self):
        return FalskNamn("Face_3")


class FalskNamn(object):
    def __init__(self, namn):
        self.Name = namn


class FalskNod(object):
    def __init__(self, namn, p=(0.0, 0.0, 0.0)):
        self.Name = namn
        self.WorldPositionMatrix = VcMatris(p)


class FalskKomponent(FalskNod):
    def __init__(self, namn, p=(0.0, 0.0, 0.0), beteenden=None, noder=None):
        FalskNod.__init__(self, namn, p)
        self.Behaviours = list(beteenden or [])
        self._noder = dict(noder or {})

    def findNode(self, namn):
        return self._noder.get(namn)

    def findBehaviour(self, namn):
        for b in self.Behaviours:
            if getattr(b, "Name", None) == namn:
                return b
        return None


class FalskApp(object):
    def __init__(self, komponenter):
        self.Components = list(komponenter)

    def findComponent(self, namn):
        for c in self.Components:
            if c.Name == namn:
                return c
        return None


class FalskSim(object):
    def __init__(self, detektor=None, kastar=False):
        self.n_uppdateringar = 0
        self.detektor = detektor
        self.kastar = kastar

    def update(self):
        self.n_uppdateringar += 1

    def newCollisionDetector(self):
        if self.kastar:
            raise RuntimeError("ingen detektor i den här VC:n")
        return self.detektor


def _vcscen(komponenter, sim=None):
    return P.VcScen(FalskApp(komponenter), sim or FalskSim())


def test_vcscen_laser_hela_komponentlistan_och_hoppar_over_rollerna():
    scen = _vcscen([FalskKomponent("Robot", (1, 0, 0)),
                    FalskKomponent("Del", (2, 0, 0)),
                    FalskKomponent("Staket", (3, 0, 0))])
    scen.konfigurera({"parts": ["Del"], "tools": ["Robot"]})
    poser = scen.poser_alla()
    assert set(poser) == {"Staket"}, "roller bär redan en egen serie"
    # VC:s 3 (millimeter, M-33) ar 0,003 i seriens kanoniska meter - SAMMA
    # vag som pose() gar. Fore M-65 stod har [3, 0, 0], och provet laste in
    # felet: scenen lag i mm medan rollerna lag i m.
    assert poser["Staket"]["p"] == [0.003, 0.0, 0.0]
    assert poser["Staket"]["p"] == scen.pose("Staket")["p"], "en enhet, inte tva"
    assert poser["Staket"]["q"] == [0.0, 0.0, 0.0, 1.0], "skalär-först, M-11"


def test_kollisionsdetektorn_skapas_ur_planen_och_matar_avstandet():
    """sim.newCollisionDetector() finns i API-ytan och var aldrig anropad."""
    det = FalskDetektor()
    noder = {"Finger": FalskNod("Finger"), "Vagg": FalskNod("Vagg")}
    komp = FalskKomponent("Cell", noder=noder)
    scen = P.VcScen(FalskApp([komp]), FalskSim(det))
    scen.konfigurera({"mind": [{"namn": "gripper+fixtur", "a": ["Cell/Finger"],
                                "b": ["Cell/Vagg"], "tolerans_mm": 100.0}]})
    assert det.Active is True
    assert det.StopOnCollision is False, \
        "ett stopp river simuleringen och med den pumpen (M-13)"
    assert abs(det.Tolerance - 100.0 / P.VC_TILL_MM) < 1e-12
    d = scen.mindist({"namn": "gripper+fixtur"})
    # VC svarar i millimeter, sa d_mm ar VC:s tal rakt av (VC_TILL_MM = 1.0),
    # medan punkterna raknas till kanonisk meter som poserna.
    assert abs(d["d_mm"] - 12.0) < 1e-9
    assert d["p2"] == [0.012, 0.0, 0.0] and d["inom_tolerans"] is True


def test_traffen_bar_bade_nod_och_yta():
    det = FalskDetektor()
    det.traffar = True
    komp = FalskKomponent("Cell", noder={"A": FalskNod("A"), "B": FalskNod("B")})
    scen = P.VcScen(FalskApp([komp]), FalskSim(det))
    scen.konfigurera({"mind": [{"namn": "par", "a": ["Cell/A"], "b": ["Cell/B"]}]})
    assert scen.traff() == ["finger", "vagg", "Face_12", "Face_3"]


def test_en_detektor_som_inte_gar_att_skapa_blir_ett_saknat_underlag():
    """Fail-closed: ingen detektor ger ingen MINDIST-rad, aldrig ett tyst OK."""
    komp = FalskKomponent("Cell", noder={"A": FalskNod("A"), "B": FalskNod("B")})
    scen = P.VcScen(FalskApp([komp]), FalskSim(kastar=True))
    scen.konfigurera({"mind": [{"namn": "par", "a": ["Cell/A"], "b": ["Cell/B"]}]})
    assert scen.mindist("par") is None
    assert any("newCollisionDetector" in s["varfor"] for s in scen.saknade)


def test_ett_par_utan_nodlistor_gar_inte_att_bygga_en_detektor_av():
    scen = _vcscen([FalskKomponent("Cell")])
    scen.konfigurera({"mind": ["bara_ett_namn"]})
    assert scen.mindist("bara_ett_namn") is None
    assert any("nodlistor" in s["varfor"] for s in scen.saknade)


def test_robotlederna_laser_varde_mal_grans_och_typ():
    servo = FalskServo([FalskLed(10.0, "-170", "170"),
                        FalskLed(-5.0, "-90", "90")], mal=[12.0, -5.0])
    servo.Name = "Servo"
    komp = FalskKomponent("Robot", beteenden=[servo])
    scen = _vcscen([komp])
    scen.konfigurera({"joints": ["Robot"]})
    assert scen.leder("Robot") == [10.0, -5.0]
    assert scen.ledmal("Robot") == [12.0, -5.0]
    assert scen.ledgranser["Robot"] == [[-170.0, 170.0], [-90.0, 90.0]]
    assert scen.ledtyper["Robot"] == ["deg", "deg"]


def test_en_ledgrans_som_ar_ett_uttryck_blir_OKAND_och_inte_gissad():
    """MinValue och MaxValue är UTTRYCK i VC, inte tal. Ett gissat gränsvärde
    vore värre än inget."""
    servo = FalskServo([FalskLed(0.0, "Comp.MinA", "Comp.MaxA")])
    scen = _vcscen([FalskKomponent("Robot", beteenden=[servo])])
    scen.konfigurera({"joints": ["Robot"]})
    assert scen.ledgranser["Robot"] == [None]
    assert any("uttryck" in s["varfor"] for s in scen.saknade)


def test_en_led_med_okand_typ_far_ingen_enhet():
    servo = FalskServo([FalskLed(0.0, "-1", "1", typ="Nagot_annat")])
    scen = _vcscen([FalskKomponent("Robot", beteenden=[servo])])
    scen.konfigurera({"joints": ["Robot"]})
    assert scen.ledtyper["Robot"] == [None]


def test_planen_far_overstyra_ledtypen():
    servo = FalskServo([FalskLed(0.0, "-1", "1", typ="Nagot_annat")])
    scen = _vcscen([FalskKomponent("Robot", beteenden=[servo])])
    scen.konfigurera({"joints": ["Robot"], "ledtyper": {"Robot": ["mm"]}})
    assert scen.ledtyper["Robot"] == ["mm"]


def test_statistiken_per_station_laser_ankomna_avgangna_och_tillstand():
    stat = FalskStatistik()
    stat.Name = "Stat"
    scen = _vcscen([FalskKomponent("Station1", beteenden=[stat])])
    scen.konfigurera({"stat": ["Station1"]})
    d = scen.stat("Station1")
    assert d["in"] == 7 and d["out"] == 5 and d["cur"] == 2
    assert d["state"] == "BUSY" and d["blocked_pct"] == 27.5


def test_en_station_utan_statistikbeteende_blir_ett_saknat_underlag():
    scen = _vcscen([FalskKomponent("Station1")])
    scen.konfigurera({"stat": ["Station1"]})
    assert scen.stat("Station1") is None
    assert any("vcStatistics" in s["varfor"] for s in scen.saknade)


def test_leder_och_statistik_hamnar_i_serien_och_i_tracked():
    servo = FalskServo([FalskLed(3.0, "-170", "170")], mal=[3.0])
    stat = FalskStatistik()
    scen = P.VcScen(FalskApp([FalskKomponent("Robot", beteenden=[servo]),
                              FalskKomponent("Station1", beteenden=[stat])]),
                    FalskSim())
    p = P.Provtagare(scen, {"parts": [], "tools": [], "joints": ["Robot"],
                            "stat": ["Station1"], "rate_hz": 20.0}).starta(0.0)
    p.kanske_prov(0.0)
    d = p.data()
    assert d["rows"][0]["joints"] == {"Robot": [3.0]}
    assert d["rows"][0]["joints_mal"] == {"Robot": [3.0]}
    assert d["rows"][0]["stat"]["Station1"]["in"] == 7
    assert d["tracked"]["joints"] == ["Robot"]
    assert d["tracked"]["stations"] == ["Station1"]
    assert d["ledgranser"]["Robot"] == [[-170.0, 170.0]]
