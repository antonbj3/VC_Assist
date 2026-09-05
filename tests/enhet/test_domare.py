# -*- coding: utf-8 -*-
"""M-45: spårfacit går att döma mekaniskt, och domaren fäller det som är fel.

Provet har tre lager, och det mittersta är hela poängen:

1. **Tolken kör ST enligt IEC 61131-3.** TON, TOF, TP, R_TRIG, SR och RS provas
   mot standardens egna tidsdiagram, inte mot sig själva.
2. **Varje uppgift med spårfacit har en referenslösning som uppfyller det.** Ett
   facit ingen kan uppfylla fäller alla, och ser ut som en svår bänk.
3. **Varje motbevis fälls, och på just den brist det namnger.** En grind utan
   trasig fixtur mäter ingenting (regel S2 i docs/spec/96_ingen_skuld.md), och
   ett motbevis som fälls av fel skäl är inte heller en fixtur — det är en
   slump.

beskriver: bank/domare.py, svc/vc_assist_svc/st/tolk.py, bank/uppgifter/*.json
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import domare  # noqa: E402
import lasare  # noqa: E402
from vc_assist_svc.st import tolk  # noqa: E402


# ------------------------------------------------------------------ tolken

SIGNALER = {"IN1": "bool", "IN2": "bool", "UT": "bool", "TAL": "int"}
RIKTNING = {"IN1": "in", "IN2": "in", "UT": "out", "TAL": "out"}


def _kor(kalla, plan, slut_ms, las, scan_ms=20.0):
    """Kör ett program och lämna [(t_ms, värde)] per scan."""
    t = tolk.Tolk(kalla, SIGNALER, RIKTNING, scan_ms)
    plan = sorted(plan)
    i = 0
    ut = []
    while t.tid_ms <= slut_ms + 1e-9:
        while i < len(plan) and plan[i][0] <= t.tid_ms + 1e-9:
            for namn, v in plan[i][1].items():
                t.satt(namn, v)
            i += 1
        t.scan()
        ut.append((t.tid_ms - scan_ms, t.las(las)))
    return ut


def _forsta(spar, varde):
    for t, v in spar:
        if v == varde:
            return t
    return None


TON_PROG = ("PROGRAM P\nVAR t : TON; END_VAR\n"
            "t(IN := IN1, PT := T#100ms);\nUT := t.Q;\nEND_PROGRAM\n")
TOF_PROG = ("PROGRAM P\nVAR t : TOF; END_VAR\n"
            "t(IN := IN1, PT := T#100ms);\nUT := t.Q;\nEND_PROGRAM\n")
TP_PROG = ("PROGRAM P\nVAR t : TP; END_VAR\n"
           "t(IN := IN1, PT := T#100ms);\nUT := t.Q;\nEND_PROGRAM\n")


def test_ton_slar_till_pt_efter_flanken():
    """IEC 61131-3: Q blir hög när IN varit hög i PT."""
    spar = _kor(TON_PROG, [(40, {"IN1": True})], 400, "UT")
    assert _forsta(spar, True) == pytest.approx(140.0)


def test_ton_nollstalls_nar_in_faller():
    """Standardens tidsdiagram: ET går till noll när IN faller, den fryser inte.
    Faller IN före PT blir Q aldrig hög, och nästa flank räknar om från noll."""
    spar = _kor(TON_PROG, [(40, {"IN1": True}), (100, {"IN1": False}),
                           (140, {"IN1": True})], 400, "UT")
    assert _forsta(spar, True) == pytest.approx(240.0), (
        "räknaren fortsatte från det gamla värdet i stället för att nollställas")


def test_tof_slapper_pt_efter_fallet():
    spar = _kor(TOF_PROG, [(40, {"IN1": True}), (200, {"IN1": False})], 500, "UT")
    assert spar[3][1] is True, "TOF ska följa IN upp direkt"
    assert _forsta(spar[10:], False) == pytest.approx(300.0)


def test_tp_ger_en_puls_som_inte_gar_att_trigga_om():
    """En ny flank under pulsen får inte förlänga den."""
    spar = _kor(TP_PROG, [(40, {"IN1": True}), (60, {"IN1": False}),
                          (80, {"IN1": True})], 400, "UT")
    hoga = [t for t, v in spar if v]
    assert min(hoga) == pytest.approx(40.0)
    assert max(hoga) == pytest.approx(120.0), (
        "pulsen forlangdes av en ny flank; TP far inte gå att trigga om")


def test_r_trig_ar_hog_i_exakt_ett_scan():
    prog = ("PROGRAM P\nVAR r : R_TRIG; END_VAR\n"
            "r(CLK := IN1);\nUT := r.Q;\nEND_PROGRAM\n")
    spar = _kor(prog, [(40, {"IN1": True})], 200, "UT")
    assert [t for t, v in spar if v] == [pytest.approx(40.0)]


def test_sr_ar_set_dominant_och_rs_ar_reset_dominant():
    """IEC 61131-3, bistabilerna: den dominanta ingången bär siffran 1."""
    sr = ("PROGRAM P\nVAR b : SR; END_VAR\n"
          "b(S1 := IN1, R := IN2);\nUT := b.Q1;\nEND_PROGRAM\n")
    rs = ("PROGRAM P\nVAR b : RS; END_VAR\n"
          "b(S := IN1, R1 := IN2);\nUT := b.Q1;\nEND_PROGRAM\n")
    plan = [(20, {"IN1": True, "IN2": True})]
    assert _kor(sr, plan, 100, "UT")[-1][1] is True
    assert _kor(rs, plan, 100, "UT")[-1][1] is False


def test_tolken_faller_en_skrivning_till_en_insignal():
    """En logik som sätter sin egen givare mäter ingenting."""
    prog = "PROGRAM P\nIN1 := TRUE;\nEND_PROGRAM\n"
    t = tolk.Tolk(prog, SIGNALER, RIKTNING)
    with pytest.raises(tolk.Tolkfel) as fel:
        t.scan()
    assert "insignalen" in str(fel.value)


def test_tolken_faller_ett_odeklarerat_namn():
    prog = "PROGRAM P\nUT := SAKNAS;\nEND_PROGRAM\n"
    t = tolk.Tolk(prog, SIGNALER, RIKTNING)
    with pytest.raises(tolk.Tolkfel):
        t.scan()


def test_tolken_faller_kod_som_inte_gar_att_lasa():
    with pytest.raises(tolk.Tolkfel):
        tolk.Tolk("PROGRAM P\nUT := ;\nEND_PROGRAM\n", SIGNALER, RIKTNING)


def test_tolken_faller_en_oandlig_loop_i_stallet_for_att_hanga():
    prog = ("PROGRAM P\nVAR n : INT := 0; END_VAR\n"
            "WHILE TRUE DO\n    n := n + 1;\nEND_WHILE;\nEND_PROGRAM\n")
    t = tolk.Tolk(prog, SIGNALER, RIKTNING)
    with pytest.raises(tolk.Tolkfel) as fel:
        t.scan()
    assert "snurrar" in str(fel.value)


# ------------------------------------------------------------------ banken

@pytest.fixture(scope="module")
def bank():
    return lasare.ladda()


def med_sparfacit(bank):
    return [u for u in bank if u.data.get("facit_spar")]


def test_banken_har_minst_en_uppgift_med_sparfacit(bank):
    assert med_sparfacit(bank), (
        "ingen uppgift har spårfacit; då finns ingen dom som går att köra utan VC")


def test_referenslosningen_uppfyller_sitt_eget_facit(bank):
    """Ett facit som ingen lösning uppfyller fäller alla och ser svårt ut."""
    for u in med_sparfacit(bank):
        d = domare.dom_referens(u.data)
        assert d.godkand, "%s referenslösning: %s" % (u.id, d.text())
        assert d.scan_kord > 0, "%s körde noll scan" % u.id


def test_varje_motbevis_falls(bank):
    """S2: en grind som inte kan fyra är ett fel, inte en varning."""
    for u in med_sparfacit(bank):
        motbevis = u.data["facit_spar"]["motbevis"]
        assert motbevis, "%s har spårfacit utan motbevis" % u.id
        for namn, d, _ in domare.dom_motbevis(u.data):
            assert not d.godkand, (
                "%s: motbeviset %r gick igenom domaren" % (u.id, namn))


def test_varje_motbevis_falls_pa_den_brist_det_namnger(bank):
    """Ett motbevis som fälls av fel skäl är ingen fixtur, det är en slump."""
    for u in med_sparfacit(bank):
        for namn, d, faller_pa in domare.dom_motbevis(u.data):
            saknas = [k for k in faller_pa if k not in d.koder]
            assert not saknas, (
                "%s: motbeviset %r skulle fällas på %s men föll på %s"
                % (u.id, namn, ", ".join(saknas), ", ".join(d.koder)))


def test_motbevisen_ar_inte_referensen(bank):
    """Ett motbevis som råkat bli en kopia av referensen faller på ingenting,
    och det syns bara om någon jämför texterna."""
    for u in med_sparfacit(bank):
        referens = u.data["facit_spar"]["referens"].strip()
        for mb in u.data["facit_spar"]["motbevis"]:
            assert mb["st"].strip() != referens, (
                "%s: motbeviset %r är identiskt med referensen" % (u.id, mb["namn"]))


def _utan_kommentarer(st_text):
    """ST utan (* ... *). Kommentarerna jämförs inte mot uppgiftstexten: en
    kommentar som återger PackML:s tillståndstabell är kravet, inte lösningen,
    och tabellen SKA stå i uppgiftstexten."""
    ut, djup, i = [], 0, 0
    while i < len(st_text):
        if st_text[i:i + 2] == "(*":
            djup += 1
            i += 2
        elif st_text[i:i + 2] == "*)" and djup:
            djup -= 1
            i += 2
        else:
            if not djup:
                ut.append(st_text[i])
            i += 1
    return "".join(ut)


def test_referenslosningen_lacker_inte_in_i_uppgiftstexten(bank):
    """Referensen bevisar att facit går att uppfylla. Hamnar den i prompten är
    den i stället svaret, och bänken mäter avskrift."""
    for u in med_sparfacit(bank):
        referens = _utan_kommentarer(u.data["facit_spar"]["referens"])
        rader = [r.strip() for r in referens.splitlines() if len(r.strip()) > 25]
        for r in rader:
            assert r not in u.data["prompt"], (
                "%s: raden %r ur referensen står i uppgiftstexten" % (u.id, r))


def test_kravtiderna_ligger_minst_tva_scan_fran_en_insignalandring(bank):
    """Marginalregeln, mätt i stället för påstådd: under två scan mäter facit
    hur många scan en implementation råkar ta på sig."""
    import schema
    for u in med_sparfacit(bank):
        facit = u.data["facit_spar"]
        scan = float(facit["scan_ms"])
        for sekv in facit["sekvenser"]:
            satt = [float(s["t_ms"]) for s in sekv["steg"] if s["satt"]]
            for s in sekv["steg"]:
                if not s["krav"]:
                    continue
                t = float(s["t_ms"])
                nara = [v for v in satt
                        if 0 <= t - v < schema.MARGINAL_SCAN * scan]
                assert not nara, (
                    "%s/%s: kravet vid %.0f ms ligger för nära ändringen vid %.0f ms"
                    % (u.id, sekv["id"], t, max(nara)))


# ------------------------------------- domaren litar på förgrindarnas egna ord

class _Falldom(object):
    """En Stationsdom-lik dubbel. Riktig Stationsdom kräver en signalkarta med
    scensignalnamn, och banken har roller — inte scensignaler."""

    ok = False
    forsta_fallande = "deklarationsmatchning"
    forgrindar = {"deklarationsmatchning": "taggen FINNS_EJ saknas i kartan"}
    utdata = {"deklarationsmatchning": "F3 rad 12"}


def test_tva_flankkrav_pa_samma_signal_i_samma_sekvens_raknar_bada():
    """Trasig fixtur for domarens egen flankraknare.

    FUNNET 2026-09-05 (M-106): `forra[signal]` skrevs inne i loopen over
    flankkraven, sa det ANDRA kravet pa samma utsignal i samma sekvens fick det
    redan uppdaterade vardet som sitt "foregaende scan". Det sag darfor aldrig
    en flank, rapporterade alltid 0 och kunde aldrig fallas - en grind som inte
    kan falla mater ingenting. Provet har tva krav pa samma signal: ett som ska
    ga igenom och ett som ska FALLAS.
    """
    post = {
        "task_id": "FLANK-1",
        "control": {"signals": [
            {"name": "ST900_PEC_PRT", "dir": "in", "type": "bool"},
            {"name": "ST900_CNV_RUN", "dir": "out", "type": "bool"}]},
        "facit_spar": {
            "scan_ms": 20,
            "sekvenser": [{
                "id": "en_puls", "beskrivning": "en flank pa insignalen",
                "steg": [
                    {"t_ms": 0, "satt": {"ST900_PEC_PRT": False},
                     "krav": {}, "varfor": ""},
                    {"t_ms": 100, "satt": {"ST900_PEC_PRT": True},
                     "krav": {}, "varfor": ""},
                    {"t_ms": 200, "satt": {},
                     "krav": {"ST900_CNV_RUN": True},
                     "varfor": "utgangen foljer insignalen"},
                    {"t_ms": 300, "satt": {"ST900_PEC_PRT": False},
                     "krav": {}, "varfor": ""},
                    {"t_ms": 400, "satt": {}, "krav": {"ST900_CNV_RUN": False},
                     "varfor": "och slapper igen"}]}],
            "flanker": [
                {"namn": "ratt_antal", "sekvens": "en_puls",
                 "signal": "ST900_CNV_RUN", "typ": "RISE",
                 "fran_ms": 0, "till_ms": 400, "antal": 1,
                 "varfor": "en puls in ger en puls ut"},
                {"namn": "andra_kravet_samma_signal", "sekvens": "en_puls",
                 "signal": "ST900_CNV_RUN", "typ": "RISE",
                 "fran_ms": 0, "till_ms": 400, "antal": 1,
                 "varfor": "samma sanning en gang till; med felet rapporterade "
                           "det har kravet 0 och foll, fast det ar uppfyllt"},
                {"namn": "fel_antal", "sekvens": "en_puls",
                 "signal": "ST900_CNV_RUN", "typ": "RISE",
                 "fran_ms": 0, "till_ms": 400, "antal": 7,
                 "varfor": "sju flanker finns inte; det har kravet MASTE fallas"}],
        }}
    st = ("PROGRAM ST900_PROV\nVAR\nEND_VAR\n"
          "ST900_CNV_RUN := ST900_PEC_PRT;\nEND_PROGRAM\n")
    d = domare.dom(post, st)
    assert "flank:andra_kravet_samma_signal" not in d.koder, (
        "det andra flankkravet pa samma signal raknade inte alls och foll pa "
        "ett krav som ar uppfyllt: %s" % d.koder)
    assert "flank:fel_antal" in d.koder, (
        "ett flankkrav med fel antal maste fallas aven som tredje krav pa "
        "samma signal: %s" % d.koder)
    assert "flank:ratt_antal" not in d.koder, d.koder


def test_en_falld_forgrind_stoppar_spardomen(bank):
    u = med_sparfacit(bank)[0]
    d = domare.dom(u.data, u.data["facit_spar"]["referens"], stationsdom=_Falldom())
    assert not d.godkand
    assert d.koder == ["forgrind:deklarationsmatchning"]
    assert d.scan_kord == 0, "spåret kördes trots att en förgrind fällt"
    assert "taggen FINNS_EJ saknas i kartan" in d.brister[0].text, (
        "domaren skrev om grindens svar i stället för att citera det")


def test_en_uppgift_utan_sparfacit_domes_inte_tyst_gron(bank):
    utan = [u for u in bank if not u.data.get("facit_spar")]
    assert utan, "provet förutsätter att det finns uppgifter utan spårfacit"
    with pytest.raises(domare.Domsfel):
        domare.dom(utan[0].data, "PROGRAM P\nEND_PROGRAM\n")
