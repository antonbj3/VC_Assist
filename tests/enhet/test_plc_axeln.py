# -*- coding: utf-8 -*-
"""L1: PLC-axelns giltighet (M-97) - en korning vars hopfogning inte gar att
lita pa ska fallas som OBESTAMBAR, inte domas.

Fas 8:s forebild: en korning vars klockkvot lag utanfor braketten blev
OGILTIG. Har ar storheten hopfogningens MATTA tak (M-87) stallt mot
farskhetsfonstret PLC_FARSK_S: ar alder + tak storre an fonstret gar vardets
farskhet inte att styrka, och raden ligger inte bevisat pa fysikens tidsaxel.

Tre lager, och var och en har en fixtur som FALLER:
  raden      plc_otackt: alder + tak > fonster
  flanken    sekvensdom: ett steg utanfor sitt fonster med MINDRE an
             flankernas tak ar INCONCLUSIVE, inte TOO_LATE/TOO_EARLY
  korningen  _dom: andel otackta over PLC_AXEL_MAX_ANDEL -> INCONCLUSIVE

Och ett injicerat kant svar (hubbens varning: "prova grinden mot ett kant
svar du sjalv injicerar"): samma serie, samma fel pa 0,1 s, tre olika tak -
och tre olika domar. Grinden diskriminerar pa taket, och ett tak som ljuger
ligger utanfor dess rackvidd (det star i M-97:s LIMITS).
"""
import os
import sys

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "tests")))

import celler                                                   # noqa: E402
import oga_analys as A                                          # noqa: E402
import oga_harledning as H                                      # noqa: E402
import oga_kontrakt as K                                        # noqa: E402
from oga_provtagning import PLC_FARSK_S                         # noqa: E402

FONSTER = PLC_FARSK_S


def _doma(b, plan):
    _text, rapport, a = A.doma(b.data(), plan)
    return rapport, a


def _flankrader(rader):
    """Index for de rader som bar en PLC-flank - dar ett tak avgor en dom."""
    ut = []
    forra = None
    for i, r in enumerate(rader):
        plc = r.get("plc") or {}
        if forra is not None and any(bool(plc.get(k)) != bool(forra.get(k))
                                     for k in set(plc) | set(forra)):
            ut.append(i)
        forra = plc
    return ut


def _satt_tak(rader, tak_s, index=None):
    for i, r in enumerate(rader):
        if index is None or i in index:
            r["plc_hopfogning_s"] = tak_s


# ---- raden ---------------------------------------------------------------

@pytest.mark.parametrize("alder,tak,otackt", [
    (0.20, 0.05, False),        # exakt pa fonstret: styrkt
    (0.20, 0.0501, True),       # ett hundradels ms over: inte styrkt
    (0.05, 0.25, True),         # farsk alder, men taket ar hela fonstret
    (0.10, 1.8, True),          # M-87 §6: sa stora tak fanns i en frisk korning
    (0.30, 0.0, False),         # gammal men med noll-tak: det ar plc_gammal, inte otackt
])
def test_otackt_ar_alder_plus_tak_over_fonstret(alder, tak, otackt):
    rad = {"plc": {"Start": True}, "plc_alder_s": alder, "plc_hopfogning_s": tak}
    assert H.plc_otackt(rad, FONSTER) is otackt


def test_utan_matt_tak_ar_raden_inte_otackt_utan_PRIOR():
    """Ett tak som SAKNAS ar en annan storhet an ett tak som inte racker.
    Det forsta redovisas som PRIOR i LIMITS; det andra ar M-97:s fraga."""
    rad = {"plc": {"Start": True}, "plc_alder_s": 0.05}
    assert H.plc_otackt(rad, FONSTER) is False
    ax = H.plc_axel([rad], FONSTER)
    assert ax["utan_tak"] == 1 and ax["otackta"] == 0


def test_axelns_rakning_skiljer_otackta_fran_gamla():
    """plc_gammal satts pa punktskattningen; otackt pa alder + tak. En rad
    kan vara det ena utan det andra, och rakningen blandar dem inte."""
    rader = [{"t": 0.0, "plc": {"a": True}, "plc_alder_s": 0.05, "plc_hopfogning_s": 0.01},
             {"t": 0.05, "plc": {"a": True}, "plc_alder_s": 0.05, "plc_hopfogning_s": 0.30},
             {"t": 0.10, "plc": {"a": True}, "plc_alder_s": 0.40, "plc_gammal": True}]
    ax = H.plc_axel(rader, FONSTER)
    assert ax["rader_med_plc"] == 3
    assert ax["otackta"] == 1 and ax["t_otackta"] == [0.05]
    assert ax["utan_tak"] == 1
    assert ax["tak_max_s"] == 0.30


# ---- korningen: braketten -----------------------------------------------

def _station_bra_med_tak(tak_s, andel):
    """station_bra med ett stort tak pa `andel` av raderna, jamnt spritt."""
    b, plan = celler.ALLA["station_bra"]()
    n = len(b.rader)
    steg = max(1, int(round(1.0 / andel))) if andel > 0 else n + 1
    for i, r in enumerate(b.rader):
        r["plc_hopfogning_s"] = tak_s if (i % steg == 0) else 0.005
    return b, plan


def test_en_korning_over_braketten_ar_obestambar_inte_pass():
    """DEN TRASIGA FIXTUREN for braketten. Samma serie som far PASS med ett
    litet tak far INCONCLUSIVE - och namner PLC-axeln - nar hopfogningen
    tacker fonstret i mer an braketten av proven."""
    b, plan = _station_bra_med_tak(FONSTER, 2 * A.PLC_AXEL_MAX_ANDEL)
    rapport, a = _doma(b, plan)
    ax = a.harledt["timing"]["plc_axel"]
    assert ax["andel_otackt"] > A.PLC_AXEL_MAX_ANDEL
    assert ax["over_braketten"] is True
    assert rapport.dom[0] == "INCONCLUSIVE"
    assert rapport.dom[1].startswith("PLC-axeln går inte att lita på")


def test_samma_serie_under_braketten_far_sin_vanliga_dom():
    b, plan = _station_bra_med_tak(FONSTER, A.PLC_AXEL_MAX_ANDEL / 2.0)
    rapport, a = _doma(b, plan)
    ax = a.harledt["timing"]["plc_axel"]
    assert 0 < ax["andel_otackt"] <= A.PLC_AXEL_MAX_ANDEL
    assert ax["over_braketten"] is False
    assert rapport.dom == ("PASS", "allt inom marginal")


def test_braketten_ar_det_som_faller(monkeypatch):
    """Mutation: hojs braketten till 100 % ska samma serie fa PASS. Annars ar
    det nagot annat an braketten som fallde, och provet ovan mater fel sak."""
    b, plan = _station_bra_med_tak(FONSTER, 2 * A.PLC_AXEL_MAX_ANDEL)
    monkeypatch.setattr(A, "PLC_AXEL_MAX_ANDEL", 1.0)
    rapport, _a = _doma(b, plan)
    assert rapport.dom[0] == "PASS"


def test_en_korning_utan_plc_beror_inte_av_braketten():
    b, plan = celler.ALLA["bra"]()
    rapport, a = _doma(b, plan)
    ax = a.harledt["timing"]["plc_axel"]
    assert ax["rader_med_plc"] == 0 and ax["over_braketten"] is False
    assert rapport.dom[0] == "PASS"


def test_braketten_faller_ocksa_en_cell_som_annars_hade_fallts():
    """OGILTIG ar inte FAIL. En trasig station over braketten far inte heller
    sin fallning - for fallningen vilar pa samma opalitliga axel."""
    b, plan = celler.ALLA["station_forsent"]()
    _satt_tak(b.rader, FONSTER)
    rapport, _a = _doma(b, plan)
    assert rapport.dom[0] == "INCONCLUSIVE"
    assert "PLC-axeln" in rapport.dom[1]


# ---- flanken: ett steg inom hopfogningens osakerhet ---------------------

def _forsent_med_tak_pa_flankerna(tak_s):
    """station_forsent: stegen ar 0,2-0,5 s for sena. Taket laggs BARA pa
    flankraderna (~5 % av raderna) sa braketten inte slar - det som provas
    ar steget, inte korningen."""
    b, plan = celler.ALLA["station_forsent"]()
    _satt_tak(b.rader, 0.005)
    _satt_tak(b.rader, tak_s, set(_flankrader(b.rader)))
    return b, plan


def test_ett_steg_inom_hopfogningens_osakerhet_ar_INCONCLUSIVE_inte_TOO_LATE():
    """DEN TRASIGA FIXTUREN for flanken. Stegen ar for sena med 0,2-0,5 s.
    Med start- och stegflank pa 0,3 s var (0,6 s tillsammans) ar det mindre
    an osakerheten, och da ar det inget fel - och inget godkannande."""
    b, plan = _forsent_med_tak_pa_flankerna(0.30)
    rapport, a = _doma(b, plan)
    seq = a.harledt["station"]["sekvens"]
    assert not seq["tidsbrott"], seq["tidsbrott"]
    assert seq["osakra"], "inget steg markt osakert"
    assert all(s["status"] in ("OK", "INCONCLUSIVE")
               for c in seq["cykler"] for s in c["steg"])
    assert a.harledt["timing"]["plc_axel"]["over_braketten"] is False
    assert rapport.dom[0] == "INCONCLUSIVE"
    assert rapport.dom[1].startswith("timing: stegets tid ligger inom "
                                     "hopfogningens osäkerhet")


def test_ett_fel_storre_an_osakerheten_falls_anda():
    """Grinden far inte gora ogat snallt: ar felet storre an taket ar det ett
    fel. 0,05 + 0,05 = 0,1 s osakerhet mot 0,2-0,5 s forsening -> TOO_LATE."""
    b, plan = _forsent_med_tak_pa_flankerna(0.05)
    rapport, a = _doma(b, plan)
    seq = a.harledt["station"]["sekvens"]
    assert seq["tidsbrott"] and not seq["osakra"]
    assert rapport.dom[0] == "FAIL"
    assert rapport.dom[1].startswith("timing:")


def test_MISSING_paverkas_inte_av_taket():
    """Ett steg som aldrig kom i hela cykeln saknas oavsett hur stort taket
    ar. Osakerheten flyttar flanker, den uppfinner inga."""
    b, plan = celler.ALLA["station_utan_stopp"]()
    _satt_tak(b.rader, 0.005)
    _satt_tak(b.rader, 1.0, set(_flankrader(b.rader)))
    rapport, a = _doma(b, plan)
    assert rapport.dom[0] == "FAIL" and rapport.dom[1].startswith("sekvens:")
    assert a.harledt["domar"]["sekvens"]["utfall"] == "FAIL"
    assert a.harledt["domar"]["timing"]["utfall"] != "FAIL"


def test_osakerheten_ar_bada_flankernas_tak_inte_bara_stegets():
    """Startflanken har ocksa ett tak. Lagg hela osakerheten pa STARTEN och
    inget pa steget: domen ska anda bli osaker, for dt = t - t0 bar bada."""
    b, plan = celler.ALLA["station_forsent"]()
    _satt_tak(b.rader, 0.005)
    flank = _flankrader(b.rader)
    # Startflanken ar givarens RISE: forsta flanken i varje cykel.
    starter = [i for i in flank if b.rader[i]["plc"].get("givare")
               and not b.rader[i - 1]["plc"].get("givare")]
    assert len(starter) == 3
    _satt_tak(b.rader, 0.60, set(starter))
    rapport, a = _doma(b, plan)
    assert a.harledt["station"]["sekvens"]["osakra"]
    assert rapport.dom[0] == "INCONCLUSIVE"


# ---- det injicerade kanda svaret ----------------------------------------

def _station_med_ett_steg_0_1_s_for_sent():
    """station_bra dar stoppets FALL kommer vid 2,6 s - fonstret ar 1,5-2,5 s.
    Ett kant fel pa exakt 0,1 s, i ett enda steg."""
    b = celler.Stationsbygge("injicerat_fel")
    for _ in range(3):
        celler._stationscykel(b, t_stopp_s=2.6)
    return b, celler.stationsplan()


@pytest.mark.parametrize("tak_s,vantad_dom,vantad_borjan", [
    (0.005, "FAIL", "timing:"),          # taket sager: felet ar verkligt
    (0.06, "INCONCLUSIVE", "timing:"),   # 2 x 0,06 > 0,1: felet drunknar
    (0.049, "FAIL", "timing:"),          # 2 x 0,049 < 0,1: felet star kvar
])
def test_samma_kanda_fel_tre_tak_tre_domar(tak_s, vantad_dom, vantad_borjan):
    """Injicerat kant svar: ett steg ar 0,100 s for sent. Det ENDA som andras
    mellan raderna ar taket pa flankraderna. Grinden ska diskriminera pa
    taket, precis dar summan av de tva flankernas tak passerar felet."""
    b, plan = _station_med_ett_steg_0_1_s_for_sent()
    _satt_tak(b.rader, 0.005)
    _satt_tak(b.rader, tak_s, set(_flankrader(b.rader)))
    rapport, a = _doma(b, plan)
    assert a.harledt["timing"]["plc_axel"]["over_braketten"] is False
    assert rapport.dom[0] == vantad_dom, rapport.dom
    assert rapport.dom[1].startswith(vantad_borjan), rapport.dom


def test_ett_tak_som_ljuger_ligger_utanfor_grindens_rackvidd():
    """Det grinden INTE kan: samma 0,1 s-fel med ett tak pa 0,005 s falls som
    verkligt. Om taket i sjalva verket var 0,3 s (hopfogningen ljog) ar
    fallningen falsk, och ogat kan inte se det - det har bara taket. Det
    star i M-97:s LIMITS, och provet finns for att gransen ska vara skriven
    i kod och inte bara i text."""
    b, plan = _station_med_ett_steg_0_1_s_for_sent()
    _satt_tak(b.rader, 0.005)
    rapport, _a = _doma(b, plan)
    assert rapport.dom[0] == "FAIL"


# ---- rapporten och kontraktet -------------------------------------------

def test_rapporten_med_ett_osakert_steg_gar_att_lasa_tillbaka():
    """Grammatiken (v2) har ingen INCONCLUSIVE-form for STEP. Rapporten far
    darfor inte skriva en sadan rad - lasaren hade kastat - och den ska anda
    ga att lasa, med domen INCONCLUSIVE och CYCLES late=0."""
    b, plan = _forsent_med_tak_pa_flankerna(0.30)
    text, rapport, _a = A.doma(b.data(), plan)
    last = K.las(text)
    assert last.dom[0] == "INCONCLUSIVE"
    rader = [r.strip() for r in text.splitlines()]
    assert not any(r.startswith("STEP") and "INCONCLUSIVE" in r for r in rader)
    assert any(r.startswith("CYCLES judged=3 broken=0 late=0") for r in rader)


def test_rakningen_ligger_i_underlaget_och_LIMITS_bar_seriens_varsta_tak():
    b, plan = _station_bra_med_tak(0.9, A.PLC_AXEL_MAX_ANDEL / 2.0)
    text, _rapport, a = A.doma(b.data(), plan)
    ax = a.harledt["timing"]["plc_axel"]
    for nyckel in ("rader_med_plc", "otackta", "andel_otackt", "utan_tak",
                   "tak_max_s", "alder_tak_max_s", "max_andel", "over_braketten"):
        assert nyckel in ax
    assert ax["tak_max_s"] == 0.9
    assert "RESOLUTION" in text and "join=900.00ms RUN" in text
