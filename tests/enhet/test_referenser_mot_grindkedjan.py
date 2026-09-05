# -*- coding: utf-8 -*-
"""M-121: bankens egna referenslosningar gar igenom bankens egen grindkedja.

Sju av 26 referenser med sparfacit folls av grind 2 (sex pa DUBBELSKRIVNING,
en pa TYP). Falls referensen falls modellen pa samma sak, och varje sadan traff
branner ett reparationsvarv. Domen per fall star i DOMAR nedan och i
docs/matningar/M-121_dubbelskrivning_mot_egna_referenser.md.

Provet ar last i bada riktningarna: varje referens ska ga igenom, och
MUTATIONER som tar bort just den uteslutning grinden nu ser ska falla. Utan
den andra halvan hade en grind som slapper allt ocksa sett gron ut har.
"""
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bank import reparationsbank as RB  # noqa: E402

_POSTER = dict((p["task_id"], p) for p in RB.uppgifter_med_sparfacit())

# task_id -> (vem hade fel, vad som gjordes)
DOMAR = {
    "A-07": ("referensen",
             "ARC_ON/WIR_FEED/TBL_INDEX: uteslutningen mot GAS_ON och ARC_ON "
             "gick genom stegmaskinens tillstand (satt i steg 2, slackt i steg "
             "4) - osynlig for en statisk grind och emot F7-doktrinen. "
             "Omskriven: en skrivning per utgang ur xBage/xTrad/xIndex med "
             "forreglingen i uttrycket."),
    "C-06": ("referensen",
             "RB_START skrevs ur bada maskinernas CASE; uteslutningen gick "
             "genom xRobot1/xRobot2:s tillstand. Omskriven: "
             "ST560_RB_START := xDrift AND (xStart1 OR xStart2)."),
    "L-05": ("grinden",
             "LFT_DOWN := TRUE kraver xAuto (SYS_AUTO), forreglingen kraver "
             "ST260_LFT_UP := xHand AND ... (NOT SYS_AUTO). Grinden foljer nu "
             "rena mellanvariabler och ser uteslutningen."),
    "P-06": ("bada",
             "UNCLAMP, DOR_OPEN, CYC_START: grinden - samma ingang med och "
             "utan NOT i de tva villkoren. CHK_CLAMP: referensen - "
             "uteslutningen mot UNCLAMP var tillstandsbaserad; omskriven till "
             "ST450_CHK_CLAMP := xSpann AND NOT ST450_CHK_UNCLAMP."),
    "S-07": ("grinden",
             "PSH_REJ := TRUE kraver xDriftsklar (AIR_OK), forreglingen kraver "
             "NOT AIR_OK. Ett steg genom mellanvariabeln."),
    "T-04": ("referensen",
             "4.0 * antal med antal INT. matiec (OpenPLC) avvisar: 'Data type "
             "mismatch for * expression'; IEC 61131-3:2003 2.5.1.4. Rattad "
             "till 4.0 * INT_TO_REAL(antal). STruC++ ar inget typfacit: den "
             "accepterar aven BOOL := REAL."),
    "T-09": ("bada",
             "CNV_IN: grinden - LFT_BOT i bada villkoren. LFT_UP/LFT_DOWN: "
             "referensen - 'IF LFT_UP AND LFT_DOWN' laste utgangarna efter "
             "sekvensen skrivit dem; omskrivna till en skrivning var ur "
             "xUpp/xNer med xGrensle i uttrycket."),
}

# Mutationer som tar bort just den uteslutning grinden nu ser. Faller de inte
# ar den grona referensen ingen matning.
MUTATIONER = {
    "L-05": ("NOT SYS_AUTO AND NOT xLarm", "SYS_AUTO AND NOT xLarm"),
    "S-07": ("xDriftsklar := EMG_OK AND AIR_OK AND SYS_AUTO",
             "xDriftsklar := EMG_OK AND SYS_AUTO"),
    "P-06": ("IF ST450_SPN_RUN THEN\n    ST450_CHK_UNCLAMP := FALSE;",
             "IF ST450_CHK_CLAMPED THEN\n    ST450_CHK_UNCLAMP := FALSE;"),
    "T-09": ("IF NOT ST530_LFT_BOT THEN\n    ST530_CNV_IN := FALSE;",
             "IF NOT ST530_PEC_OUT THEN\n    ST530_CNV_IN := FALSE;"),
    # Tillbaka till tva villkorade block vars villkor kan vara sanna samtidigt
    # (ett ovillkorat grundvarde plus en villkorad overskrivning ar daremot
    # det tillatna monstret och faller INTE - med ratt).
    "A-07": ("ST470_TBL_INDEX := xIndex AND NOT ST470_ARC_ON AND ST470_LGT_CLEAR;",
             "IF xIndex THEN\n    ST470_TBL_INDEX := TRUE;\nEND_IF;\n"
             "IF ST470_ARC_ON THEN\n    ST470_TBL_INDEX := FALSE;\nEND_IF;"),
    "C-06": ("ST560_RB_START := xDrift AND (xStart1 OR xStart2);",
             "IF xStart1 THEN\n    ST560_RB_START := TRUE;\nEND_IF;\n"
             "IF NOT xStart2 THEN\n    ST560_RB_START := FALSE;\nEND_IF;"),
    "T-04": ("4.0 * INT_TO_REAL(antal)", "4.0 * antal"),
}


def _grind2_koder(post, kropp):
    """Grind 2/3 (Stationssteg) over en kropp: koderna i [KOD/Fn]-form."""
    u = RB.bygg_uppsattning(post)
    kalla = u["skelett"].las_svar(kropp)
    dom = u["grindar"][0].doma(kalla)
    return sorted(set(re.findall(r"\[([A-Z_]+)/", getattr(dom, "utdata", "") or "")))


@pytest.mark.parametrize("tid", sorted(_POSTER))
def test_varje_referens_gar_igenom_grind_2_och_3(tid):
    post = _POSTER[tid]
    u = RB.bygg_uppsattning(post)
    assert _grind2_koder(post, u["referens"]) == [], tid


def test_de_sju_domda_finns_i_banken_och_ar_grona():
    assert set(DOMAR) <= set(_POSTER), sorted(set(DOMAR) - set(_POSTER))
    for tid in DOMAR:
        u = RB.bygg_uppsattning(_POSTER[tid])
        assert _grind2_koder(_POSTER[tid], u["referens"]) == [], tid


@pytest.mark.parametrize("tid", sorted(MUTATIONER))
def test_mutationen_som_tar_bort_uteslutningen_falls(tid):
    gammal, ny = MUTATIONER[tid]
    u = RB.bygg_uppsattning(_POSTER[tid])
    assert u["referens"].count(gammal) == 1, (tid, gammal)
    koder = _grind2_koder(_POSTER[tid], u["referens"].replace(gammal, ny))
    vantad = "TYP" if tid == "T-04" else "DUBBELSKRIVNING"
    assert vantad in koder, (tid, koder)


def test_referensen_gar_ocksa_igenom_sparfacit():
    """Omskrivningarna (A-07, C-06, P-06, T-09, T-04) andrade referensernas
    text; sparfacit ar beviset att beteendet star kvar."""
    for tid in ("A-07", "C-06", "P-06", "T-09", "T-04"):
        u = RB.bygg_uppsattning(_POSTER[tid])
        kalla = u["skelett"].las_svar(u["referens"])
        dom = u["grindar"][1].doma(kalla)
        assert dom.ok, (tid, getattr(dom, "utdata", ""))


# ---------------------------------------------------------------- M-167
#
# ORORD_SIGNAL fallde nio referenser pa tretton signaler. Domen per fall star i
# docs/matningar/M-167_orord_signal_mot_egna_referenser.md: alla tretton var
# REFERENSENS fel, ingen var kartans och ingen var grindens.
#
# task_id -> (vem hade fel, vad referensen nu gor med signalen)
DOMAR_M167 = {
    "C-02": ("referensen",
             "ST400_LNE_CNT: linjeraknaren vags mot station 4:s egen rakning "
             "(hogst en enhet efter, aldrig fore). Vid raknefel slapper "
             "station 1 inga fler enheter."),
    "C-03": ("referensen",
             "ST410_PRD_CNT: raknaren far bara rora sig nar bandet gar, och "
             "maste rora sig inom tva halvtaktscykler (24,0 s). Tva NYA "
             "sparsekvenser ar fixturen; utan dem hade grinden aldrig fyrat."),
    "C-05": ("referensen",
             "ST430_PRD_CNT, ST440_RWK_CNT och ST440_RWK_QUE vags mot "
             "styrningens egen bokforing (godkanda, kvitterade, kolangd) och "
             "kon mot omarbetningsplatsens tio platser."),
    "H-03": ("referensen",
             "ST330_AGV_WGT: vagcellen vags mot ST330_LOD_CNT (22,0 kg per "
             "kolli) och mot AGV:ns hogsta last 100,0 kg. AGV:n slapps inte."),
    "L-02": ("referensen",
             "ST160_PLT_HGT mot lagerraknaren (144 mm pall + 200 mm per "
             "fardigt lager, tak 750 mm) och ST160_VAC_OK fore robotrorelse. "
             "BADA satts redan av L-02:s eget spar - stimulansen fanns, "
             "referensen konsumerade den aldrig."),
    "L-03": ("referensen",
             "ST170_VAC_OK: gripdonet ror sig inte forran undertrycket "
             "bekraftats."),
    "L-04": ("referensen",
             "ST180_MAG_RDY: vaxlingen startar inte utan tom pall klar i "
             "magasinet. Spar satte redan signalen vid 89 100 ms."),
    "P-01": ("referensen",
             "ST100_RB_BUSY: ST100_RB_DONE godtas bara efter att roboten "
             "kvitterat starten - uppgiftens 'slapp aldrig pa robotens "
             "lagesignal ensam'."),
    "P-02": ("referensen",
             "ST110_RB_BUSY och ST110_VAC_OK: plocket raknas som gjort bara "
             "om robotprogrammet startade OCH sugkoppen fick grepp."),
}

# (uppgift, sekvens, signal, varde) - signalen tvingas till vardet i hela
# sekvensen. Referensen SKA falla. Utan den halvan ar en gron referens ingen
# matning: en lasning som ingen stimulans kan fella ar dekoration.
STIMULI_M167 = [
    ("C-02", "normal_handskakning", "ST400_LNE_CNT", 2),
    ("C-05", "normal_med_godkand_och_omarbetad", "ST430_PRD_CNT", 5),
    ("C-05", "normal_med_godkand_och_omarbetad", "ST440_RWK_CNT", 5),
    ("C-05", "normal_med_godkand_och_omarbetad", "ST440_RWK_QUE", 14),
    ("H-03", "normal_lastning_fyra_kollin", "ST330_AGV_WGT", 0.0),
    ("H-03", "normal_lastning_fyra_kollin", "ST330_AGV_WGT", 132.0),
    ("L-02", "normal_lager_med_mellanlagg", "ST160_PLT_HGT", 100.0),
    ("L-02", "normal_lager_med_mellanlagg", "ST160_PLT_HGT", 1250.0),
    ("L-02", "normal_lager_med_mellanlagg", "ST160_VAC_OK", False),
    ("L-03", "normal_avpalletering", "ST170_VAC_OK", False),
    ("L-04", "normal_pallvaxling", "ST180_MAG_RDY", False),
    ("P-01", "normal_plock_och_avlagg", "ST100_RB_BUSY", False),
    ("P-02", "normal_kexplock", "ST110_RB_BUSY", False),
    ("P-02", "normal_kexplock", "ST110_VAC_OK", False),
]

# C-03:s stimulans ligger i BANKEN i stallet: raknaren gar inte att fella med
# ett konstant varde, den maste sta still MEDAN bandet gar. De tva sekvenserna
# ar darfor sparfacit, och gamla referensen faller pa bada (M-167 §C-03).
C03_FIXTURSEKVENSER = ("raknaren_star_still_medan_bandet_gar",
                       "raknaren_stiger_medan_bandet_star")


def test_de_nio_domda_i_m167_finns_i_banken_och_ar_grona():
    assert set(DOMAR_M167) <= set(_POSTER), sorted(set(DOMAR_M167) - set(_POSTER))
    for tid in DOMAR_M167:
        u = RB.bygg_uppsattning(_POSTER[tid])
        assert _grind2_koder(_POSTER[tid], u["referens"]) == [], tid


@pytest.mark.parametrize("fall", STIMULI_M167,
                         ids=["%s-%s=%s" % (t, s, v) for t, _k, s, v in STIMULI_M167])
def test_stimulansen_som_signalen_lastes_for_faller_referensen(fall):
    import copy

    import domare                                                # noqa: E402

    tid, sekv, signal, varde = fall
    post = _POSTER[tid]
    facit = copy.deepcopy(post["facit_spar"])
    facit["sekvenser"] = [s for s in facit["sekvenser"] if s["id"] == sekv]
    assert facit["sekvenser"], (tid, sekv)
    facit["flanker"] = [f for f in (facit.get("flanker") or [])
                        if f.get("sekvens") == sekv]
    for steg in facit["sekvenser"][0]["steg"]:
        if steg.get("satt") and signal in steg["satt"]:
            del steg["satt"][signal]
    facit["sekvenser"][0]["steg"][0].setdefault("satt", {})[signal] = varde
    dom = domare.dom(post, facit["referens"], spar=facit)
    assert not dom.godkand, (
        "%s: %s = %r far igenom - lasningen av signalen ar dekoration"
        % (tid, signal, varde))


def test_c03_bar_de_tva_sparsekvenser_som_provar_raknarovervakningen():
    ider = set(s["id"] for s in _POSTER["C-03"]["facit_spar"]["sekvenser"])
    for namn in C03_FIXTURSEKVENSER:
        assert namn in ider, (namn, sorted(ider))
