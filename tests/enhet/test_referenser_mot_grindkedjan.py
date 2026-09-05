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
