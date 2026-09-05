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


# ---- 3. hopfogningens osakerhet: MATT, per korning och som prior ---------

def _p(v, andel):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(andel * (len(s) - 1))))]


@pytest.mark.parametrize("paus_s", [0.005, 0.010])
def test_hopfogningens_tak_bar_felet_ocksa_vid_VCs_tur_och_retur(tmp_path, paus_s):
    """MATNINGEN i M-65 §3. M-42 matte d mot en rigg med 5,2 ms tur och retur;
    VC:s brygga ar 9,9 ms (M-03). Riggens pump far darfor sova 10 ms per slag
    i den andra korningen, och samma fyra tal mats om.

    Det som provas ar TAKET: ogat bar nu kopplarens matta rtt_tak i serien
    som plc_hopfogning_s. Det talet ar bara vart nagot om felet d verkligen
    ligger inom det - at bada hallen - i varje varv.

    OBSERVERAT 2026-09-05, EN GANG, EJ ATERSKAPAT. Fallet [0.005] foll en gang
    i en full svitkorning. Darefter:

        5 riktade korningar ensamt          alla grona
        6 riktade korningar under CPU-last  alla grona
        2 fulla sviter                      alla grona

    Alltsa en gang pa tre fulla sviter och noll pa elva riktade. Jag antog forst
    att provet var belastningskansligt - det mater vaggklocka med riktiga tradar
    och sleep - men LASTPROVET MOTBEVISADE DET. Orsaken ar okand.

    Raden star har for att en sallsynt slumpfallning ar varre an en vanlig: den
    lar den som ser den att bortse fran provet. Aterkommer den ska den mätas,
    inte tystas. Det som redan ar uteslutet: ren CPU-last.
    """
    import test_ogonkoppling as TO

    class Rigg(TO.Rigg):
        def _pumpa(self):
            while not self._stopp.is_set():
                self.brygga.tick(simtid=self.sim())
                TO.time.sleep(paus_s)

    rigg = Rigg(tmp_path)
    try:
        rigg.vanta_pa_takt()
        p = rigg.starta_ogat()
        rigg.oga.synka()
        k = rigg.kopplare()
        takt = rigg.brygga.takt()
        d_ms, tak_ms, rtt_ms, buret_ms = [], [], [], []
        for _ in range(200):
            tak = rigg.oga.rtt_tak()
            t0 = TO.time.time()
            v = k.kor_varv()
            assert v.fel is None and v.oga_fel is None
            rtt_ms.append((TO.time.time() - t0) * 1000.0)
            d_ms.append((rigg.brygga.provtagare.plckalla.t
                         - rigg.sim.vid(v.t_fran_plc)) * 1000.0)
            tak_ms.append(tak * 1000.0 * takt)
            rad = p.prov(rigg.sim())
            buret_ms.append(rad["plc_hopfogning_s"] * 1000.0)
        print("\nM-65 hopfogningen, paus %.0f ms, %d varv, takt %.3f"
              % (paus_s * 1000.0, len(d_ms), takt))
        print("  d (ms): median %+.2f  p05 %+.2f  p95 %+.2f  min %+.2f  max %+.2f"
              % (_p(d_ms, .5), _p(d_ms, .05), _p(d_ms, .95), min(d_ms), max(d_ms)))
        print("  tur och retur (ms): median %.2f  p95 %.2f  max %.2f"
              % (_p(rtt_ms, .5), _p(rtt_ms, .95), max(rtt_ms)))
        print("  taket i serien, plc_hopfogning_s (ms): median %.2f  max %.2f"
              % (_p(buret_ms, .5), max(buret_ms)))
        print("  andel varv med |d| > taket: %.1f %%"
              % (100.0 * len([1 for d, t in zip(d_ms, tak_ms) if abs(d) > t])
                 / len(d_ms)))
        # 1. taket foljer med i serien, som simuleringssekunder
        assert all(b > 0.0 for b in buret_ms)
        # 2. felet ligger inom taket, at BADA hallen, i varje varv. Annars ar
        #    taket inte en osakerhet utan en gissning.
        varsta = max(abs(d) - t for d, t in zip(d_ms, tak_ms))
        assert varsta <= 0.0, "d overskred taket med %.2f ms" % varsta
        # 3. och hopfogningen lutar at det konservativa hallet (M-42)
        assert _p(d_ms, .5) < 0.0
    finally:
        rigg.stang()


def test_upplosningsformeln_ar_en_ovre_grans_for_fasfelet_och_inte_lost():
    """MATNINGEN i M-65 §3, Monte Carlo. 20 000 slumpade flanker.

    En PLC-flank vid t_p ses av kopplaren vid nasta lasning (intervall L)
    och stamplas konservativt upp till J tidigare. En VC-flank vid t_s ses
    vid nasta prov (intervall S). Felet i fasen ar e_prov - e_las + j, alltsa
    inom (-L, S+J), och gransen ar max(L, S+J) - det ar formeln i
    H.upplosning, och har provas den mot slumpen i stallet for att antas.

    Forsta versionen av formeln var S + L + J. Den var ocksa en grans, men
    en los: vid L=89 ms (M-39:s kopplarvarv) sade den 151 ms dar det verkliga
    felet aldrig passerade 89. En los grans gor varje fasdom mer INCONCLUSIVE
    an den behover vara. Gransen ska vara TAT: ett fel nara den ska
    forekomma, annars ar formeln en marginal och inte en upplosning.
    """
    import random
    rnd = random.Random(65)
    for S, L, J in ((0.05, 0.005, 0.003), (0.05, 0.089, 0.012),
                    (0.02, 0.089, 0.012), (0.1, 0.05, 0.0)):
        fel = []
        for _ in range(5000):
            t_p = rnd.uniform(1.0, 2.0)
            t_s = t_p + rnd.uniform(-0.5, 0.5)
            fas_las = rnd.uniform(0.0, L)          # kopplarens lasfas
            fas_prov = rnd.uniform(0.0, S)         # ogats provfas
            t_las = t_p + ((fas_las - t_p) % L)    # forsta lasning efter t_p
            stampel = t_las - rnd.uniform(0.0, J)  # konservativ stampel
            t_sig = t_s + ((fas_prov - t_s) % S)   # forsta prov efter t_s
            fel.append(abs((t_sig - stampel) - (t_s - t_p)))
        grans = max(L, S + J)
        los = S + L + J
        print("\nM-65 upplosning S=%.3f L=%.3f J=%.3f: max fel %.4f  grans %.4f  "
              "(summan %.4f)  p95 %.4f" % (S, L, J, max(fel), grans, los, _p(fel, .95)))
        assert max(fel) <= grans + 1e-9, "formeln ar ingen ovre grans"
        assert max(fel) >= 0.9 * grans, "formeln ar for los for att kallas upplosning"
        assert H.upplosning([{"t": 0.0, "plc": {"a": 1}, "plc_alder_s": 0.0},
                             {"t": L, "plc": {"a": 1}, "plc_alder_s": 0.0}],
                            1.0 / S, J)["fas_s"] == pytest.approx(grans)


def test_en_plcflank_ligger_pa_lasningens_tid_inte_pa_provets():
    """TRASIG FIXTUR (M-65 §3). Taggen ses hog forst i provet vid t=1,00 -
    men vardet var da 0,20 s gammalt. Flanken hor till lasningen vid 0,80.

    Fore lagningen lades varje PLC-flank pa provets tid, alltsa upp till
    PLC_FARSK_S = 250 ms for sent, och varje fasforhallande mot en VC-signal
    lutade systematiskt at det hallet. Biasen ar EXAKT aldern.
    """
    rader = [{"t": round(i * 0.05, 4), "plc": {"Start": i >= 20},
              "plc_alder_s": 0.2} for i in range(40)]
    f = H.plcflanker(rader)
    assert len(f) == 1
    assert f[0]["t"] == pytest.approx(0.80)
    assert f[0]["t_prov"] == pytest.approx(1.00) and f[0]["alder_s"] == 0.2


def test_upplosningen_mats_ur_serien_och_sager_var_hopfogningen_kom_ifran():
    """Lasintervallet raknas ur de distinkta lastiderna serien sjalv bar, och
    hopfogningen ar RUN nar serien bar kopplarens tak, annars PRIOR."""
    rader = [{"t": round(i * 0.05, 4), "plc": {"a": True},
              "plc_alder_s": round(0.01 + 0.05 * (i % 2), 4)} for i in range(40)]
    u = H.upplosning(rader, 20.0, 0.01345)
    assert u["prov_s"] == pytest.approx(0.05)
    # lastiderna ar t-0,01 pa jamna prov och t-0,06 pa udda: samma tid
    # varannan gang, alltsa en lasning per 0,10 s
    assert u["las_s"] == pytest.approx(0.10)
    assert u["hopfogning_kalla"] == "PRIOR" and u["hopfogning_s"] == 0.01345
    assert u["fas_s"] == pytest.approx(max(0.10, 0.05 + 0.01345))
    for r in rader:
        r["plc_hopfogning_s"] = 0.0053
    u = H.upplosning(rader, 20.0, 0.01345)
    assert u["hopfogning_kalla"] == "RUN" and u["hopfogning_s"] == 0.0053
    assert H.upplosning(rader[:1], 20.0, 0.01345)["fas_s"] is None, \
        "en enda lasning ger inget lasintervall, och da ingen upplosning"


# ---- 4. fem domare, fem trasiga celler - och osynliga for varandra ---------
#
# Fasens grind: domar som faller pa sekvens, timing, grepp, kollision och
# genomflode, var och en med en trasig cell som MASTE fallas. Och den cellen
# ska vara osynlig for de andra fyra domarna - annars provar man inte det man
# tror. Matrisen nedan ar hela provet: rad = cell, kolumn = domare.

def _domar(namn):
    b, plan = celler.ALLA[namn]()
    _text, rapport, a = A.doma(b.data(), plan)
    return rapport, a.harledt["domar"]


# (cell, domaren som ska falla den). Flera celler per domare ar tillatet;
# minst en per domare ar kravet.
TRASIGA = [
    ("station_utan_stopp", "sekvens"),        # ett steg uteblev
    ("station_forregling_bruten", "sekvens"), # tva utgangar hoga samtidigt
    ("station_forsent", "timing"),            # ratt ordning, for sent
    ("fas_utanfor_tolerans", "timing"),       # PLC-fasen over kravet
    ("kort_uppehall", "timing"),              # uppehallet for kort
    ("aldrig_gripen", "grepp"),               # greppet bildades aldrig
    ("glider", "grepp"),                      # delen gled i greppet
    ("fel_placerad", "grepp"),                # delen hamnade fel
    ("kontakt", "kollision"),                 # minsta avstandet 0
    ("kollision", "kollision"),               # detektortraff
    ("station_svalt", "genomflode"),          # svalt over kravet
    ("station_blockerad", "genomflode"),      # blockerad over kravet
]

# Celler dar kontraktets regel 5 (en VIOLATION i HONESTY tvingar FAIL) faller
# FORE domaren. De faller av grepp-domaren OCKSA, men slacks den star regeln
# kvar - det ar 42_ogat_utbyggt.md §13:s "hal som star kvar", och det doljs
# inte: mutationsprovet nedan kraver att de fortsatter falla.
TVINGADE_AV_HONESTY = ("aldrig_gripen",)


def test_varje_domare_har_minst_en_trasig_cell_som_bara_den_bar():
    """Minst en cell per domare som INTE ar tvingad av kontraktet - annars
    kan domaren vara dod utan att nagot marker det."""
    egna = set(d for c, d in TRASIGA if c not in TVINGADE_AV_HONESTY)
    assert egna == set(A.Analys.DOMARE)


@pytest.mark.parametrize("namn,domare", TRASIGA, ids=[c for c, _d in TRASIGA])
def test_en_trasig_cell_falls_av_RATT_domare_och_av_ingen_annan(namn, domare):
    """Matrisen. Cellen ska falla, domen ska namna domaren, domaren ska saga
    FAIL - och de fyra andra far INTE saga FAIL. En cell som tva domare
    faller provar ingen av dem: slacks den ena faller den andra anda."""
    rapport, d = _domar(namn)
    assert rapport.dom[0] == "FAIL", (namn, rapport.dom)
    assert d[domare]["utfall"] == "FAIL", (namn, domare, d[domare])
    andra = dict((k, v["utfall"]) for k, v in d.items()
                 if k != domare and v["utfall"] == "FAIL")
    assert not andra, ("%s falls ocksa av %s - cellen ar inte osynlig for de "
                       "andra domarna" % (namn, andra))
    ord_ = {"sekvens": ("sequence", "interlock"), "timing": ("timing", "race"),
            "grepp": ("grasp",), "kollision": ("collision",),
            "genomflode": ("throughput",)}[domare]
    assert any(rapport.dom[1].startswith(o + ":") for o in ord_), \
        "domsraden namner inte domaren: %r" % rapport.dom[1]


def _analysens_egen_dom(namn):
    """Analysens EGEN dom, fore kontraktets regel 5. Skrivaren far inte saga
    nej har - det ar just analysen som ska provas."""
    b, plan = celler.ALLA[namn]()
    a = A.Analys(b.data(), plan)
    try:
        a.rapport()
    except K.Kontraktsfel:
        pass
    return a.harledt.get("_dom_provad")


@pytest.mark.parametrize("domare", A.Analys.DOMARE)
def test_slacks_en_domare_blir_exakt_dess_celler_grona(domare, monkeypatch):
    """Mutation: EN domare svarar 'ingen fraga stalld'. Da ska varje cell som
    hor till den sluta falla i ANALYSENS egen dom, och varje cell som hor
    till en annan falla precis som forut. Det ar beviset for att domaren bar
    sina egna celler och inte lutar sig mot en granne.

    Kontraktet ar ett ANDRA skikt: regel 5 (v2) forbjuder ett PASS bredvid
    en STEP MISSING-rad, en STARVED EXCEEDED-rad och sa vidare, sa en slackt
    domare ger da ett Kontraktsfel i stallet for ett PASS. Det provas for sig
    i test_kontraktet_vagrar_ett_PASS_nar_domaren_ar_slackt. Har provas
    domaren, och da lases domen fore kontraktet.
    """
    orig = A.Analys._dom

    def bevarande(self, *a, **kw):
        dom = orig(self, *a, **kw)
        self.harledt["_dom_provad"] = dom
        return dom
    monkeypatch.setattr(A.Analys, "_dom", bevarande)
    fore = dict((namn, _analysens_egen_dom(namn)[0]) for namn, _d in TRASIGA)
    assert all(v == "FAIL" for v in fore.values()), fore
    monkeypatch.setattr(A.Analys, "_doma_" + domare,
                        lambda self, h: (None, [], {}))
    for namn, egen in TRASIGA:
        dom = _analysens_egen_dom(namn)[0]
        if egen == domare and namn not in TVINGADE_AV_HONESTY:
            assert dom != "FAIL", ("%s foll fastan domaren %s ar slackt: nagon "
                                   "annan faller den" % (namn, domare))
        else:
            assert dom == "FAIL", (
                "%s andrade dom till %s nar %s slacktes" % (namn, dom, domare))


@pytest.mark.parametrize("domare", A.Analys.DOMARE)
def test_kontraktet_vagrar_ett_PASS_nar_domaren_ar_slackt(domare, monkeypatch):
    """Det andra skiktet. Raderna ar ogats egna ord, och kontraktets regel 5
    (v2) later inte ett PASS sta bredvid dem - aven om analysens domare ar
    slackt. Ett fynd i en rad kan inte tigas ihjal av domsraden."""
    monkeypatch.setattr(A.Analys, "_doma_" + domare,
                        lambda self, h: (None, [], {}))
    for namn, egen in TRASIGA:
        if egen != domare or namn in TVINGADE_AV_HONESTY:
            continue
        b, plan = celler.ALLA[namn]()
        a = A.Analys(b.data(), plan)
        try:
            r = a.rapport()
        except K.Kontraktsfel as e:
            assert "rule 5" in str(e) or "force" in str(e), str(e)
            continue
        assert r.dom[0] != "PASS", (namn, r.dom)


@pytest.mark.parametrize("namn", sorted(celler.ALLA))
def test_domsraden_och_domartabellen_sager_samma_sak(namn):
    """Invarianten over HELA banken: ett PASS bar ingen domare som sagt FAIL
    eller INCONCLUSIVE, och en dom utan hederlighets-, scen- eller robotfel
    som ar FAIL bar minst en domare som sagt FAIL."""
    b, plan = celler.ALLA[namn]()
    _text, rapport, a = A.doma(b.data(), plan)
    d = a.harledt["domar"]
    utfall = set(v["utfall"] for v in d.values())
    if rapport.dom[0] == "PASS":
        assert "FAIL" not in utfall and "INCONCLUSIVE" not in utfall, (namn, d)
    ovriga = (a.harledt["honesty"].get("overtradelse")
              or a.harledt["scene"].get("oombedd")
              or a.harledt["scene"].get("utslungad")
              or a.harledt["scene"].get("orort")
              or A.Analys._robotbrott(a.harledt["robotar"]))
    if rapport.dom[0] == "FAIL" and not ovriga:
        assert "FAIL" in utfall, (namn, rapport.dom, d)


# ---- 5. kollisionsmattet ar measureDistance, inte detektorn (M-36) ---------

class _Matnod(_Nod):
    """En nod som kan mata avstand som VC:s vcNode gor: (d, p1, p2, v), i
    VC:s millimeter, och 0,0 vid nudd eller overlapp (M-36)."""

    def __init__(self, namn, p, storlek=1000.0):
        _Nod.__init__(self, namn, p)
        self.storlek = storlek
        self.n_update = 0

    def update(self):
        self.n_update += 1

    def measureDistance(self, annan):
        a, b = self.WorldPositionMatrix.P, annan.WorldPositionMatrix.P
        glapp = abs(b.X - a.X) - (self.storlek + annan.storlek) / 2.0
        d = max(0.0, glapp)
        return (d, _V(a.X + self.storlek / 2.0, 0.0, 0.0),
                _V(b.X - annan.storlek / 2.0, 0.0, 0.0), _V(d, 0.0, 0.0))


def _parscen(dx_mm):
    a = _Matnod("A", (0.0, 0.0, 0.0))
    b = _Matnod("B", (dx_mm, 0.0, 0.0))
    scen = P.VcScen(_App([a, b]), _Sim())
    scen.konfigurera({"mind": [{"namn": "A+B", "a": ["A"], "b": ["B"]}]})
    return scen, a, b


@pytest.mark.parametrize("dx_mm,vantat_mm", [(0.0, 0.0), (100.0, 0.0),
                                             (1000.0, 0.0), (1500.0, 500.0),
                                             (5000.0, 4000.0)])
def test_minsta_avstandet_mats_med_measureDistance_i_M36s_tabell(dx_mm, vantat_mm):
    """M-36:s fem punkter, genom provtagaren: tva kuber om 1000 mm."""
    scen, a, b = _parscen(dx_mm)
    d = scen.mindist({"namn": "A+B"})
    assert d["metod"] == "measureDistance"
    assert d["d_mm"] == pytest.approx(vantat_mm)
    assert d["kontakt"] is (vantat_mm <= 0.0)
    assert a.n_update == 1 and b.n_update == 1, "M-36: update() fore matningen"


def test_detektorn_ar_inte_standardvagen_langre():
    """TRASIG FIXTUR (M-36). En detektor som svarar noll traffar vid 900 mm
    overlapp far inte vara det ogat litar pa av sig sjalvt."""
    scen, _a, _b = _parscen(100.0)
    assert scen._detektorer == {} and "A+B" in scen._par
    assert scen.mindist({"namn": "A+B"})["kontakt"] is True


def test_kontakten_gar_hela_vagen_till_en_kollisionsdom():
    """Provtagare -> serie -> analys: ett par som nuddar faller kollisions-
    domaren utan att nagon detektor har fyrat."""
    scen, _a, b = _parscen(1500.0)
    # Bara en del, inget verktyg: da vantar ingen ett grepp, och det enda
    # ogat ar ombett att doma ar paret.
    plan = {"parts": ["A"], "rate_hz": 20.0,
            "mind": [{"namn": "A+B", "a": ["A"], "b": ["B"]}]}
    p = P.Provtagare(scen, plan).starta(0.0)
    for i in range(40):
        if 20 <= i < 24:
            b.WorldPositionMatrix = _M((900.0, 0.0, 0.0))     # 100 mm overlapp
        else:
            b.WorldPositionMatrix = _M((1500.0, 0.0, 0.0))
        p.kanske_prov(i * 0.05)
    _text, rapport, a = A.doma(p.data(), plan)
    assert a.harledt["domar"]["kollision"]["utfall"] == "FAIL"
    assert a.harledt["safety"]["kollision"]["kalla"] == "mind"
    assert a.harledt["safety"]["kollision"]["t"] == pytest.approx(1.0)
    assert rapport.dom[0] == "FAIL" and rapport.dom[1].startswith("collision:")
