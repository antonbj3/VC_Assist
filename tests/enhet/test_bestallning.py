# -*- coding: utf-8 -*-
"""L1 for planeringslagrets BESTALLNINGSVAG (fas 16).

Acceptansprotokollet star i tests/protocol/fas16_planeringslagret.md och varje
avsnitt har nedan svarar mot ett avsnitt dar. Grinden som stanger fasen, ur
docs/spec/70_faser.md:

    "En grundbestallning i fritext blir en detaljerad, korbar byggplan med
     villkor och processordning - och planen AVVISAS nar den ar omojlig, i
     stallet for att byggas halvt. Trasigt fall: en bestallning som motsager
     sig sjalv maste fallas med vilket villkor som krockar."

Varje kontroll provas at BADA hallen: att den faller pa ett verkligt fel OCH
slapper igenom det korrekta. En grind som bara provats at ena hallet ar oprovad
(docs/spec/95_testprotokoll.md).

Kors utan VC, utan OpenPLC och utan kompilator.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.plan import bestallning as B              # noqa: E402
from vc_assist_svc.plan import lasning as L                  # noqa: E402
from vc_assist_svc.plan import motsagelse as MO              # noqa: E402
from vc_assist_svc.plan import ordning as ORD                # noqa: E402
from vc_assist_svc.plan import storheter as ST               # noqa: E402
from vc_assist_svc.plan import villkorssprak as VS           # noqa: E402
from vc_assist_svc.plan.fel import Planfel, Specfel          # noqa: E402
from vc_assist_svc.plan.forfining import Forfinare           # noqa: E402
from vc_assist_svc.plan.harkomst import (Harkomst,           # noqa: E402
                                         granska_alla, normalisera)
from vc_assist_svc.plan.layoutmotor import Layoutmotor       # noqa: E402
from vc_assist_svc.plan.layoutport import (Layoutfel,        # noqa: E402
                                           Layoutport, begaran_ur_spec)
from vc_assist_svc.plan.processer import (Ordningskrav,      # noqa: E402
                                          Process, Processordning)
from vc_assist_svc.plan.spec import (Del, DetaljeradSpec,    # noqa: E402
                                     Grundbegaran, Koppling, Omrade)


# ---- gemensamt ----------------------------------------------------------

# En liten katalog dar varje ord i begaran traffar EXAKT en post. Bankens
# riktiga index har 15 robotar, och da blir varje "robot" en fraga i stallet -
# vilket ar ratt beteende, men gor att den positiva vagen inte gar att prova.
KATALOG = {
    "file:///band.vcm": {"uri": "file:///band.vcm",
                         "namn": "Bandtransportor 400", "kategori": "transport",
                         "l_mm": 2000.0, "b_mm": 400.0, "h_mm": 900.0,
                         "massa_kg": 120.0},
    "file:///robot.vcm": {"uri": "file:///robot.vcm", "namn": "IRB 2600",
                          "kategori": "robot", "rackvidd_mm": 1650.0,
                          "massa_kg": 272.0},
    "file:///pall.vcm": {"uri": "file:///pall.vcm", "namn": "EUR-pall",
                         "kategori": "lastbarare", "l_mm": 1200.0,
                         "b_mm": 800.0, "h_mm": 150.0, "massa_kg": 25.0},
}

# Operatorens bestallning, ordagrant. Den ar avsiktligt skriven som en
# manniska skriver, inte som ett schema.
BESTALLNING = (
    "Bygg en plockcell med ett band, en robot och en pall. "
    "Cellen ar 6x6 meter. Gangstrak minst 200 mm. "
    "Bandet matar roboten och roboten kopplas till pallen. "
    "Roboten ska na bandet och pallen. "
    "Forst plockning, sedan packning. "
    "Cellen ska klara 400 detaljer i timmen.")


def _motor():
    """Layoutmotorn i provlage: ankaret ar antaget, sa koordinaterna far
    lasas men aldrig koras mot en riktig scen (se protokollets avsnitt F)."""
    return Layoutmotor(strikt_ankare=False)


def _besked(text=BESTALLNING, motor=True, **kv):
    return B.bestall(text, KATALOG,
                     motor=_motor() if motor else None, **kv)


def _spec(text=BESTALLNING):
    f = Forfinare(KATALOG)
    return f.ur_fritext(Grundbegaran("prov", text, "operator")), f.datablad


def _villkor(id, storhet, operator, varde, belagg, sort="geometri"):
    return VS.Typvillkor(id, sort, storhet, operator, varde,
                         Harkomst("begaran", belagg))


# ======================================================================
# A. DEN POSITIVA RIKTNINGEN - fri text blir en korbar plan
# ======================================================================

def test_A1_en_bestallning_i_fritext_blir_en_byggbar_plan():
    besked = _besked()
    assert besked.status == B.BYGGBAR, besked.text()
    assert besked.plan is not None


def test_A2_planen_bar_steg_och_skrivande_steg():
    plan = _besked().plan
    sammanfattning = plan.sammanfattning()
    assert sammanfattning["steg"] >= 20, sammanfattning
    assert sammanfattning["skrivande_steg"] >= 8, sammanfattning


def test_A3_planen_haller_verktygsregistret():
    assert _besked().plan.granska() == []


def test_A4_ordningen_ar_deterministisk_over_tre_sekvenseringar():
    """K20/K22: samma spec ska ge samma sekvens, korning efter korning."""
    plan = _besked().plan
    ordningar = [plan.ordning() for _ in range(3)]
    assert ordningar[0] == ordningar[1] == ordningar[2]


def test_A4b_tre_skilda_bestallningar_av_samma_text_ger_samma_ordning():
    """Determinismen far inte bero pa att objektet ar detsamma."""
    ordningar = [B.bestall(BESTALLNING, KATALOG,
                           motor=_motor()).plan.ordning() for _ in range(3)]
    assert ordningar[0] == ordningar[1] == ordningar[2]


def test_A5_processordningen_ar_utskriven_och_ordnad():
    besked = _besked()
    assert besked.processordning == ["plockning", "packning"]


def test_A6_koordinaterna_kommer_ur_layoutmotorn():
    plan = _besked().plan
    placeringar = [s for s in plan.graf
                   if s.sort == "verktyg" and s.verktyg == "set_transform"]
    assert placeringar, "ingen placering planerades trots layoutmotor"
    for steg in placeringar:
        assert len(steg.argument["position"]) == 3
        assert "layoutmotorn" in steg.motiv


def test_A6b_utan_motor_planeras_inga_koordinater_och_det_star_utskrivet():
    """En grind som inte kordes far aldrig se ut som en grind som gick."""
    besked = _besked(motor=False)
    placeringar = [s for s in besked.plan.graf
                   if s.sort == "verktyg" and s.verktyg == "set_transform"]
    assert placeringar == []
    motiv = " ".join(a.motiv for a in besked.spec.antaganden)
    assert "plug and play" in motiv


def test_A7_varje_antagande_bar_sitt_motiv():
    besked = _besked()
    assert len(besked.spec.antaganden) >= 10
    for a in besked.spec.antaganden:
        assert len(a.motiv.strip()) >= 40, a


def test_A8_inga_oppna_blockerande_fragor_i_en_byggbar_plan():
    besked = _besked()
    assert besked.spec.blockerande_fragor() == []


def test_A9_beskedet_gar_att_lasa_som_rader():
    rader = _besked().rader()
    assert rader[0] == "BESKED BYGGBAR"
    assert any(r.startswith("PROCESSORDNING") for r in rader)
    assert any(r.startswith("PLAN ") for r in rader)


# ======================================================================
# C. DE TRASIGA FALLEN
# ======================================================================

# ---- T1. bestallningen motsager sig sjalv -------------------------------

MOTSAGELSE = ("Bygg en cell. Cellen far vara hogst 2x2 meter och minst "
              "3 meter bred.")


def test_T1_en_sjalvmotsagande_bestallning_avvisas():
    besked = _besked(MOTSAGELSE)
    assert besked.status == B.AVVISAD
    assert besked.grind == "B3_MOTSAGELSE"


def test_T1b_fallningen_namner_VILKET_VILLKOR_som_krockar():
    """Kravet i grinden: fallas med VILKET villkor som krockar.

    'Planen ar ogiltig' ar inget svar - operatoren kan inte ratta nagot pa
    det. Bada raderna ska sta dar, med hans EGNA ord.
    """
    besked = _besked(MOTSAGELSE)
    text = "\n".join(t for _kod, t in besked.problem)
    assert "MK1_INTERVALL_TOMT" in [k for k, _t in besked.problem]
    assert "hogst 2x2 meter" in text
    assert "minst 3 meter bred" in text
    assert "cell.bredd_mm" in text


def test_T1c_fallningen_bar_en_atgard():
    besked = _besked(MOTSAGELSE)
    krock = besked.motsagelsedom.krockar[0]
    assert krock.atgard
    assert len(krock.ids()) >= 2


def test_T1d_samma_bestallning_utan_motsagelsen_gar_igenom_grinden():
    """Motprovet. En grind som faller pa allt mater ingenting."""
    besked = _besked("Bygg en cell. Cellen far vara hogst 4x4 meter och minst "
                     "3 meter bred.")
    assert besked.grind != "B3_MOTSAGELSE", besked.text()


# ---- T2. cyklisk processordning -----------------------------------------

CYKEL = ("Bygg en cell. Forst svetsning, sedan malning. "
         "Malning fore svetsning.")


def test_T2_en_cyklisk_processordning_avvisas():
    besked = _besked(CYKEL)
    assert besked.status == B.AVVISAD
    assert besked.grind == "B2_PROCESSORDNING"
    assert "PO1_CYKEL" in [k for k, _t in besked.problem]


def test_T2b_fallningen_namner_VILKA_STEG_som_bildar_cykeln():
    besked = _besked(CYKEL)
    text = "\n".join(t for _kod, t in besked.problem)
    assert "malning" in text and "svetsning" in text
    assert "malning -> svetsning -> malning" in text


def test_T2c_samma_processer_utan_ringen_gar_igenom():
    besked = _besked("Bygg en cell. Forst svetsning, sedan malning.")
    assert besked.grind != "B2_PROCESSORDNING", besked.text()
    assert besked.processordning == ["svetsning", "malning"]


def test_T2d_en_cykel_blir_ett_fel_med_stegen_i_sig_inte_en_oandlig_loop():
    """Direkt mot processordningen, utan vagen genom fritexten."""
    h = Harkomst("begaran", "forst a sedan b")
    ordning = Processordning(
        [Process("a", "gora a", None, h), Process("b", "gora b", None, h)],
        [Ordningskrav("a", "b", h), Ordningskrav("b", "a", h)])
    assert ordning.cykler() == [["a", "b"]]
    with pytest.raises(Exception) as fel:
        ordning.ordning()
    assert fel.value.cykler == [["a", "b"]]


# ---- T3. ett antaget krav som inte ar markt som antaget -------------------

def test_T3_ett_uppfunnet_krav_som_pastar_sig_komma_ur_begaran_avvisas():
    """Skyddet mot att detaljeringen hittar pa krav operatoren aldrig stallde.

    Villkoret sager sig komma ur begaran med orden 'hogst 1200 mm'. De orden
    star inte i begaran. Kontrollen ar en delstrangsmatchning pa normaliserad
    text - inte en asikt, och inte en modell som bedomer sig sjalv.
    """
    spec, blad = _spec("Bygg en cell med ett band.")
    spec.villkor.append(_villkor("uppfunnet", "cell.bredd_mm", "le", 1200.0,
                                 "hogst 1200 mm"))
    besked = B.doma(spec, blad)
    assert besked.status == B.AVVISAD
    assert besked.grind == "B1_HARKOMST"
    assert "HK2_FALSK_BEGARAN" in [k for k, _t in besked.problem]


def test_T3b_fallningen_namner_bade_kravet_och_de_pastadda_orden():
    spec, blad = _spec("Bygg en cell med ett band.")
    spec.villkor.append(_villkor("uppfunnet", "cell.bredd_mm", "le", 1200.0,
                                 "hogst 1200 mm"))
    text = "\n".join(t for _kod, t in B.doma(spec, blad).problem)
    assert "uppfunnet" in text
    assert "hogst 1200 mm" in text


def test_T3c_samma_krav_med_ett_belagg_som_STAR_i_begaran_slapps_igenom():
    """Motprovet. En harkomstgrind som faller pa allt mater ingenting."""
    spec, blad = _spec("Bygg en cell med ett band. Hogst 1200 mm bred.")
    spec.villkor.append(_villkor("verkligt", "cell.bredd_mm", "le", 1200.0,
                                 "Hogst 1200 mm"))
    besked = B.doma(spec, blad)
    assert besked.grind != "B1_HARKOMST", besked.text()


def test_T3d_ett_krav_som_pekar_pa_ett_antagande_som_inte_finns_avvisas():
    spec, blad = _spec("Bygg en cell med ett band.")
    spec.villkor.append(VS.Typvillkor(
        "peker_fel", "geometri", "cell.bredd_mm", "le", 1200.0,
        Harkomst("antagande", "ett antagande ingen skrev")))
    besked = B.doma(spec, blad)
    assert "HK3_OKANT_ANTAGANDE" in [k for k, _t in besked.problem]


def test_T3e_ett_krav_som_pekar_pa_ett_antagande_som_FINNS_slapps_igenom():
    spec, blad = _spec("Bygg en cell med ett band.")
    vad = spec.antaganden[0].vad
    spec.villkor.append(VS.Typvillkor(
        "peker_ratt", "geometri", "cell.bredd_mm", "le", 1200.0,
        Harkomst("antagande", vad)))
    besked = B.doma(spec, blad)
    assert besked.grind != "B1_HARKOMST", besked.text()


def test_T3f_ett_krav_utan_harkomst_alls_gar_inte_ens_att_konstruera():
    with pytest.raises(Specfel) as fel:
        VS.Typvillkor("utan", "geometri", "cell.bredd_mm", "le", 1200.0, None)
    assert "harkomst" in str(fel.value)


def test_T3g_granska_alla_ger_HK1_for_ett_krav_vars_harkomst_ar_None():
    problem = granska_alla([("kravet X", None)], "en begaran")
    assert problem[0][0] == "HK1_UTAN_HARKOMST"


# ---- T4. geometrin gor kravet omojligt ----------------------------------

def _rackviddsbegaran(rackvidd_mm, golv=(3000.0, 3000.0)):
    return {
        "v": 1, "plan_id": "prov", "frigang_mm": 200.0,
        "golv_mm": list(golv), "hojd_mm": 4000.0,
        "delar": [
            {"roll": "robot", "uri": "u:r", "kategori": "robot", "antal": 1,
             "matt_mm": None, "massa_kg": None},
            {"roll": "band", "uri": "u:b", "kategori": "transport", "antal": 1,
             "matt_mm": [2000.0, 400.0, 900.0], "massa_kg": None}],
        "kopplingar": [],
        "relationer": [{"sort": "nar", "fran_roll": "robot",
                        "till_roll": "band", "hard": True}],
        "datablad": {"robot": {"rackvidd_mm": rackvidd_mm}},
    }


def test_T4_en_for_kort_rackvidd_gor_layouten_overbestamd():
    svar = _motor().placera(_rackviddsbegaran(900.0))
    assert svar["status"] == "OVERBESTAMD"
    assert svar["placeringar"] == []


def test_T4b_konflikten_namner_den_bindande_relationen():
    svar = _motor().placera(_rackviddsbegaran(900.0))
    koder = [k["kod"] for k in svar["konflikt"]]
    assert "INOM_RACKVIDD" in koder
    roller = [r for k in svar["konflikt"] for r in k["roller"]]
    assert "band" in roller and "robot" in roller


def test_T4c_skalet_namner_sokrastret():
    """Ett rastersvar far aldrig lata som en matematisk omojlighet."""
    svar = _motor().placera(_rackviddsbegaran(900.0))
    skal = [k["text"] for k in svar["konflikt"] if k["kod"] == "SKAL"][0]
    assert "sokraster" in skal


def test_T4d_en_tillracklig_rackvidd_ger_en_losning():
    """Motprovet at andra hallet."""
    svar = _motor().placera(_rackviddsbegaran(2600.0))
    assert svar["status"] == "LOST"
    assert len(svar["placeringar"]) == 2


def test_T4e_bestallningen_stoppas_pa_layoutgrinden():
    """Layouten gar inte, och beskedet namner den bindande relationen.

    Att svaret blir OFULLSTANDIG och inte AVVISAD ar meningen: motorn raknade
    ocksa den MJUKA lasningen av rackvidden, och den gar. Da ar ingenting
    bevisat omojligt - nagot ar obestamt, och det rattas av ett svar.
    """
    spec, blad = _spec(
        "Bygg en cell med ett band och en robot. Cellen ar 3x3 meter. "
        "Gangstrak minst 200 mm. Bandet matar roboten. "
        "Roboten ska na bandet. Roboten har rackvidd 900 mm.")
    besked = B.doma(spec, blad, _motor())
    assert besked.status in (B.AVVISAD, B.OFULLSTANDIG), besked.text()
    assert besked.grind == "B5_LAYOUT"
    assert besked.plan is None
    assert any("INOM_RACKVIDD" in t for _k, t in besked.problem)


# ---- T5. ett hart slot ar tomt ------------------------------------------

def test_T5_en_bestallning_utan_topologi_blir_ofullstandig():
    besked = _besked("Bygg en cell med ett band, en robot och en pall. "
                     "Cellen ar 6x6 meter.")
    assert besked.status == B.OFULLSTANDIG
    assert besked.plan is None


def test_T5b_fragan_namner_rollerna_som_saknar_koppling():
    besked = _besked("Bygg en cell med ett band, en robot och en pall. "
                     "Cellen ar 6x6 meter.")
    text = "\n".join(t for _k, t in besked.problem)
    assert "band" in text and "robot" in text and "pall" in text


def test_T5c_topologin_gissas_aldrig_ur_ordningen_orden_stod_i():
    spec, _blad = _spec("Bygg en cell med ett band, en robot och en pall.")
    assert spec.kopplingar == []


# ---- T6. en storhet som inte gar att sla upp ----------------------------

def test_T6_ett_krav_pa_en_okand_statisk_storhet_ger_OFULLSTANDIG():
    """Kallprojektets stubbar svarade `pass` nar argumentet saknades. Det
    arvs inte: en kontroll utan sitt argument ar OKANT, aldrig godkant."""
    spec, blad = _spec("Bygg en cell med en robot. "
                       "Roboten behover arbetsradie 2500 mm.")
    blad.pop("robot", None)     # rackvidden finns inte nagonstans
    besked = B.doma(spec, blad)
    assert besked.status == B.OFULLSTANDIG, besked.text()
    assert "B3_OKAND_STORHET" in [k for k, _t in besked.problem]


def test_T6b_samma_krav_med_rackvidden_kand_domes_pa_riktigt():
    spec, blad = _spec("Bygg en cell med en robot. "
                       "Roboten behover arbetsradie 2500 mm.")
    blad["robot"] = {"rackvidd_mm": 1650.0}
    besked = B.doma(spec, blad)
    assert besked.status == B.AVVISAD
    assert besked.grind == "B3_MOTSAGELSE"
    assert "MK2_VARDE_MOT_VILLKOR" in [k for k, _t in besked.problem]


def test_T6c_en_rackvidd_som_racker_slapps_igenom():
    spec, blad = _spec("Bygg en cell med en robot. "
                       "Roboten behover arbetsradie 1200 mm.")
    blad["robot"] = {"rackvidd_mm": 1650.0}
    besked = B.doma(spec, blad)
    assert besked.grind != "B3_MOTSAGELSE", besked.text()


def test_T6d_ett_falt_ur_katalogen_som_faller_ar_ett_VAL_som_faller():
    """Skillnaden ar botemedlet: byt komponent, inte krav."""
    spec, blad = _spec("Bygg en cell med en robot. "
                       "Roboten behover arbetsradie 2500 mm.")
    blad["robot"] = {"rackvidd_mm": 1650.0}
    dom = MO.granska(spec.villkor, ST.Faktarum(spec, blad), spec)
    assert dom.dom == MO.VALET_FALLER
    assert "Byt komponent" in dom.krockar[0].atgard


# ---- T7-T9. formkraven --------------------------------------------------

def test_T7_prosa_i_ett_villkor_ar_ett_lintfel_inte_en_varning():
    with pytest.raises(Specfel) as fel:
        VS.Typvillkor("prosa", "geometri", "roboten ska vara snabb", "eq",
                      True, Harkomst("begaran", "roboten ska vara snabb"))
    assert "VS2_OKAND_STORHET" in str(fel.value)


def test_T7b_en_storhet_ur_den_slutna_listan_gar_bra():
    v = _villkor("ok", "cell.bredd_mm", "le", 2000.0, "hogst 2 meter")
    assert v.storhet == "cell.bredd_mm"


def test_T8_ett_prosakrav_utan_konsument_avvisas():
    """PL5 - efterkontroll utan konsument - fanns i vart EGET lager: den gamla
    spec.Villkor.text lastes av noll rader kod i hela repot (M-63)."""
    with pytest.raises(Specfel) as fel:
        VS.Prosakrav("f1", "forregling", "ingen rorelse nar EMG_OK ar lag", "",
                     Harkomst("bank", "A-01#control.interlocks[0]"))
    assert "VS5_PROSAKRAV_UTAN_KONSUMENT" in str(fel.value)


def test_T8b_ett_prosakrav_med_konsument_gar_bra():
    krav = VS.Prosakrav("f1", "forregling", "ingen rorelse nar EMG_OK ar lag",
                        "grind 3 och ST-lagret, docs/spec/50_grindar.md",
                        Harkomst("bank", "A-01#control.interlocks[0]"))
    assert "grind 3" in krav.rad()


def test_T9_ett_nej_far_aldrig_lamna_ut_en_plan():
    besked = _besked()
    with pytest.raises(Planfel):
        B.Besked(B.AVVISAD, besked.spec, besked.plan)


def test_T9b_ett_ja_far_lamna_ut_en_plan():
    besked = _besked()
    assert B.Besked(B.BYGGBAR, besked.spec, besked.plan).plan is not None


# ======================================================================
# D. MOTSAGELSEGRINDENS FYRA DOMAR
# ======================================================================

def _fakta(**kv):
    spec = DetaljeradSpec(
        "f", Grundbegaran("f", "en begaran med hogst 2000 mm", "prov"),
        [Del("band", "file:///band.vcm", 1, "transport",
             [2000.0, 400.0, 900.0])],
        omrade=kv.pop("omrade", None))
    return spec, ST.Faktarum(spec, kv.pop("datablad", None))


def test_D1_tva_villkor_som_inte_kan_galla_samtidigt_ger_OMOJLIG():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("a", "cell.bredd_mm", "ge", 3000.0,
                               "en begaran"),
                      _villkor("b", "cell.bredd_mm", "le", 2000.0,
                               "hogst 2000 mm")], faktarum, spec)
    assert dom.dom == MO.OMOJLIG
    assert dom.krockar[0].kod == "MK1_INTERVALL_TOMT"


def test_D1b_samma_tva_villkor_som_gar_ihop_ger_ingen_krock():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("a", "cell.bredd_mm", "ge", 1000.0,
                               "en begaran"),
                      _villkor("b", "cell.bredd_mm", "le", 2000.0,
                               "hogst 2000 mm")], faktarum, spec)
    assert dom.krockar == []


def test_D1c_en_strikt_grans_pa_samma_tal_ar_ocksa_tomt():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("a", "cell.bredd_mm", "gt", 2000.0,
                               "en begaran"),
                      _villkor("b", "cell.bredd_mm", "le", 2000.0,
                               "hogst 2000 mm")], faktarum, spec)
    assert dom.dom == MO.OMOJLIG


def test_D1d_tva_olika_eq_pa_samma_storhet_krockar():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("a", "cell.bredd_mm", "eq", 2000.0,
                               "en begaran"),
                      _villkor("b", "cell.bredd_mm", "eq", 3000.0,
                               "hogst 2000 mm")], faktarum, spec)
    assert dom.dom == MO.OMOJLIG


def test_D1e_eq_mot_en_grans_som_utesluter_det_krockar():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("a", "cell.bredd_mm", "eq", 1000.0,
                               "en begaran"),
                      _villkor("b", "cell.bredd_mm", "ge", 2000.0,
                               "hogst 2000 mm")], faktarum, spec)
    assert dom.dom == MO.OMOJLIG


def test_D1f_eq_och_ne_pa_samma_varde_krockar():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("a", "cell.bredd_mm", "eq", 2000.0,
                               "en begaran"),
                      _villkor("b", "cell.bredd_mm", "ne", 2000.0,
                               "hogst 2000 mm")], faktarum, spec)
    assert dom.dom == MO.OMOJLIG


def test_D1g_en_in_lista_utan_ett_enda_tillatet_varde_krockar():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("a", "cell.bredd_mm", "in", [1000.0, 1500.0],
                               "en begaran"),
                      _villkor("b", "cell.bredd_mm", "ge", 2000.0,
                               "hogst 2000 mm")], faktarum, spec)
    assert dom.dom == MO.OMOJLIG


def test_D2_en_matt_storhet_ar_okand_men_blockerar_inte():
    """scen.kollisioner finns forst nar scenen ar byggd. Det ar planens
    verifiering, inte ett hal i datan."""
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("k", "scen.kollisioner", "le", 0.0,
                               "en begaran")], faktarum, spec)
    assert dom.okanda == []
    assert dom.att_mata == [("scen.kollisioner", "k")]


def test_D2b_en_statisk_storhet_utan_varde_ar_OKANT():
    spec, faktarum = _fakta()
    dom = MO.granska([_villkor("r", "del.band.rackvidd_mm", "ge", 1000.0,
                               "en begaran")], faktarum, spec)
    assert dom.dom == MO.OKANT
    assert dom.okanda


def test_D3_ingen_motsagelse_funnen_ar_inget_godkannande_av_geometrin():
    spec, faktarum = _fakta()
    dom = MO.granska([], faktarum, spec)
    assert dom.dom in (MO.INGEN_FUNNEN, MO.OKANT)
    assert dom.dom != "MOJLIG"


# ======================================================================
# E. DE HARLEDDA VILLKOREN AR NODVANDIGA, ALDRIG TILLRACKLIGA
# ======================================================================

def _cellspec(bredd, djup, gang, delar):
    h = Harkomst("begaran", "en cell")
    return DetaljeradSpec(
        "c", Grundbegaran("c", "en cell med matt", "prov"), delar,
        omrade=Omrade(bredd, djup, None, gang, h))


def test_E1_en_komponent_som_inte_ryms_i_nagot_ratvinkligt_lage_ar_omojlig():
    spec = _cellspec(1000.0, 1000.0, 0.0,
                     [Del("band", "u:b", 1, "transport",
                          [2000.0, 400.0, 900.0])])
    dom = MO.granska([], ST.Faktarum(spec), spec)
    assert dom.dom == MO.OMOJLIG
    assert dom.krockar[0].kod == "MK4_PASSAR_EJ"


def test_E1b_samma_komponent_vriden_ett_kvarts_varv_ryms():
    """(l<=D och b<=B) racker. En grind som glomde vridningen hade fallt har."""
    spec = _cellspec(500.0, 2500.0, 0.0,
                     [Del("band", "u:b", 1, "transport",
                          [2000.0, 400.0, 900.0])])
    dom = MO.granska([], ST.Faktarum(spec), spec)
    assert [k.kod for k in dom.krockar] == []


def test_E2_ytbeviset_faller_nar_fotavtrycken_inte_far_plats():
    spec = _cellspec(2000.0, 2000.0, 800.0,
                     [Del("band", "u:b", 1, "transport",
                          [2000.0, 400.0, 900.0]),
                      Del("pall", "u:p", 1, "lastbarare",
                          [1200.0, 800.0, 150.0]),
                      Del("fixtur", "u:f", 1, "station",
                          [1200.0, 900.0, 1000.0])])
    dom = MO.granska([], ST.Faktarum(spec), spec)
    assert dom.dom == MO.OMOJLIG
    assert "MK3_YTA" in [k.kod for k in dom.krockar]


def test_E2b_samma_delar_pa_en_storre_yta_faller_inte():
    spec = _cellspec(8000.0, 8000.0, 800.0,
                     [Del("band", "u:b", 1, "transport",
                          [2000.0, 400.0, 900.0]),
                      Del("pall", "u:p", 1, "lastbarare",
                          [1200.0, 800.0, 150.0]),
                      Del("fixtur", "u:f", 1, "station",
                          [1200.0, 900.0, 1000.0])])
    dom = MO.granska([], ST.Faktarum(spec), spec)
    assert [k.kod for k in dom.krockar] == []


def test_E2c_antalet_raknas_in_i_ytan():
    """Sex band tar sex ganger sa mycket golv som ett. En grind som laste
    antal som ett hade sluppit igenom halva bestallningen.

    Cellen ar 2,1 x 2,1 m = 4,41 m2. Ett band ar 0,8 m2 och sex ar 4,8 m2.
    Passformen haller i bada fallen (2000 mm ryms i 2100 mm), sa det ar
    ENBART antalet som avgor."""
    def spec(antal):
        return _cellspec(2100.0, 2100.0, 0.0,
                         [Del("band", "u:b", antal, "transport",
                              [2000.0, 400.0, 900.0])])
    trang = MO.granska([], ST.Faktarum(spec(6)), spec(6))
    rymligt = MO.granska([], ST.Faktarum(spec(1)), spec(1))
    assert "MK3_YTA" in [k.kod for k in trang.krockar]
    assert [k.kod for k in rymligt.krockar] == []


def test_E3_ett_saknat_matt_gor_ytbeviset_EJ_PROVAT_aldrig_gront():
    spec = _cellspec(2000.0, 2000.0, 0.0,
                     [Del("robot", "u:r", 1, "robot", None)])
    dom = MO.granska([], ST.Faktarum(spec), spec)
    assert dom.dom == MO.OKANT
    assert any(kod == "MK3_YTA" for kod, _skal in dom.hoppade)


def test_E4_avstangd_geometri_rapporteras_som_EJ_PROVAD():
    """En avstangd kontroll far aldrig se ut som en kontroll som gick."""
    spec = _cellspec(2000.0, 2000.0, 0.0,
                     [Del("band", "u:b", 1, "transport",
                          [2000.0, 400.0, 900.0])])
    dom = MO.granska([], ST.Faktarum(spec), spec, geometri=False)
    assert dom.hoppade
    assert dom.dom == MO.OKANT


# ======================================================================
# HARKOMSTEN I DETALJ
# ======================================================================

def test_harkomst_normaliserar_a_ring_och_radbrytningar():
    assert normalisera("Högst 2x2   meter\n") == "hogst 2x2 meter"


def test_harkomst_ur_begaran_haller_nar_orden_star_dar():
    h = Harkomst("begaran", "hogst 2x2 meter")
    assert h.granska("villkoret v", "Cellen far vara Högst 2x2 meter.") == []


def test_harkomst_ur_begaran_faller_nar_orden_inte_star_dar():
    h = Harkomst("begaran", "hogst 1x1 meter")
    problem = h.granska("villkoret v", "Cellen far vara hogst 2x2 meter.")
    assert problem[0][0] == "HK2_FALSK_BEGARAN"


def test_ett_for_kort_belagg_gar_inte_att_konstruera():
    """Ett belagg pa ett tecken matchar nastan vilken text som helst och hade
    gjort HK2 trivialt sann - samma falla som en facitmall utan tal."""
    with pytest.raises(Specfel):
        Harkomst("begaran", "a")


def test_en_katalogharkomst_maste_peka_ut_bade_post_och_falt():
    with pytest.raises(Specfel):
        Harkomst("katalog", "en robot")
    assert Harkomst("katalog", "file:///robot.vcm#rackvidd_mm").belagg


def test_det_finns_ingen_kalla_som_betyder_att_vi_tyckte_sa():
    """Vill planeringen valja ett varde at operatoren far den skriva ett
    Antagande med motiv och peka pa det. Det finns ingen genvag."""
    with pytest.raises(Specfel):
        Harkomst("standard", "vi tyckte sa")


def test_harkomsten_gar_att_rundgangas_genom_json():
    h = Harkomst("bank", "A-01#expect.max_collisions")
    assert Harkomst.fran_json(h.till_json()).belagg == h.belagg


# ======================================================================
# STORHETERNA
# ======================================================================

def test_storhetslistan_ar_sluten():
    assert ST.granska_namn("cell.bredd_mm") is None
    assert ST.granska_namn("del.robot.rackvidd_mm") is None
    assert ST.granska_namn("kaffe.styrka") is not None


def test_en_okand_storhet_far_ett_fel_som_listar_formerna():
    fel = ST.granska_namn("kaffe.styrka")
    assert "cell.bredd_mm" in fel


def test_lagena_skiljer_statiskt_fran_matt():
    assert ST.lage("cell.bredd_mm") == ST.STATISK
    assert ST.lage("scen.kollisioner") == ST.MATT
    assert ST.lage("oga.SAFETY") == ST.DOM


def test_faktarummet_laser_ett_matt_ur_specen_med_sin_kalla():
    spec, faktarum = _fakta()
    varde = faktarum.las("del.band.langd_mm")
    assert varde.kant and varde.tal == 2000.0
    assert "katalogposten" in varde.kalla


def test_faktarummet_svarar_OKANT_med_skal_i_stallet_for_noll():
    spec, faktarum = _fakta()
    varde = faktarum.las("del.band.rackvidd_mm")
    assert not varde.kant
    assert "component.rsc" in varde.skal


def test_databladet_gar_fore_specens_matt():
    spec, faktarum = _fakta(datablad={"band": {"langd_mm": 1500.0}})
    assert faktarum.las("del.band.langd_mm").tal == 1500.0


def test_fotavtrycket_kraver_bade_langd_och_bredd():
    spec = DetaljeradSpec("f", Grundbegaran("f", "text", "prov"),
                          [Del("robot", "u:r", 1, "robot", None)])
    assert not ST.Faktarum(spec).las("del.robot.yta_mm2").kant


# ======================================================================
# VILLKORSSPRAKET
# ======================================================================

def test_en_okand_operator_finns_inte():
    with pytest.raises(Specfel) as fel:
        VS.Typvillkor("v", "geometri", "cell.bredd_mm", "ungefar", 2000.0,
                      Harkomst("begaran", "ungefar 2 meter"))
    assert "VS3_OKAND_OPERATOR" in str(fel.value)


def test_en_storleksjamforelse_utan_tal_avvisas():
    with pytest.raises(Specfel) as fel:
        VS.Typvillkor("v", "geometri", "cell.bredd_mm", "le", "brett",
                      Harkomst("begaran", "brett"))
    assert "VS4_VARDE_UTAN_TAL" in str(fel.value)


def test_exists_tar_inget_varde():
    with pytest.raises(Specfel):
        VS.Typvillkor("v", "geometri", "cell.bredd_mm", "exists", 1.0,
                      Harkomst("begaran", "en bredd"))


def test_villkoret_provas_at_bada_hallen():
    spec, faktarum = _fakta(datablad={"band": {"langd_mm": 1500.0}})
    haller = _villkor("a", "del.band.langd_mm", "le", 2000.0, "en begaran")
    faller = _villkor("b", "del.band.langd_mm", "le", 1000.0, "en begaran")
    assert haller.prova(faktarum)[0] == VS.UPPFYLLT
    assert faller.prova(faktarum)[0] == VS.BRUTET


def test_ett_villkor_pa_en_okand_storhet_ar_OKANT_aldrig_uppfyllt():
    spec, faktarum = _fakta()
    v = _villkor("a", "del.band.rackvidd_mm", "ge", 100.0, "en begaran")
    assert v.prova(faktarum)[0] == VS.OKANT


def test_villkoret_kastar_aldrig_vid_provning():
    v = _villkor("a", "cell.bredd_mm", "le", 1.0, "en begaran")
    assert v.prova(None)[0] == VS.OKANT


def test_villkoret_gar_att_rundgangas_genom_json():
    v = _villkor("a", "cell.bredd_mm", "le", 2000.0, "hogst 2 meter")
    ny = VS.Typvillkor.fran_json(v.till_json())
    assert ny.till_json() == v.till_json()


def test_relationen_har_en_sluten_sortlista():
    with pytest.raises(Specfel) as fel:
        VS.Relation("nara", "a", "b", Harkomst("begaran", "a nara b"))
    assert "VS7_OKAND_RELATION" in str(fel.value)


def test_semantiska_relationer_ar_markta_som_semantiska():
    r = VS.Relation("feeds", "a", "b", Harkomst("begaran", "a matar b"))
    assert r.semantisk
    assert not VS.Relation("nar", "a", "b",
                           Harkomst("begaran", "a nar b")).semantisk


def test_relationen_gar_att_rundgangas_genom_json():
    r = VS.Relation("nar", "robot", "band", Harkomst("begaran", "ska na"))
    assert VS.Relation.fran_json(r.till_json()).till_json() == r.till_json()


def test_prosakravet_gar_att_rundgangas_genom_json():
    k = VS.Prosakrav("f", "forregling", "ingen rorelse", "grind 3, 50_grindar",
                     Harkomst("bank", "A-01#control.interlocks[0]"))
    assert VS.Prosakrav.fran_json(k.till_json()).till_json() == k.till_json()


def test_ett_villkor_som_pekar_pa_en_roll_som_inte_finns_avvisas():
    with pytest.raises(Specfel) as fel:
        DetaljeradSpec("s", Grundbegaran("s", "text", "prov"),
                       [Del("band", "u:b")],
                       villkor=[_villkor("v", "del.robot.langd_mm", "le",
                                         100.0, "en begaran")])
    assert "VS6_OKAND_ROLL" in str(fel.value)


# ======================================================================
# PROCESSORDNINGEN
# ======================================================================

def _p(id):
    return Process(id, "gora %s" % id, None, Harkomst("begaran", "gor %s" % id))


def _o(a, b):
    return Ordningskrav(a, b, Harkomst("begaran", "%s fore %s" % (a, b)))


def test_ordningen_ar_kanonisk_och_deterministisk():
    ordning = Processordning([_p("c"), _p("a"), _p("b")],
                             [_o("a", "b"), _o("b", "c")])
    assert ordning.ordning() == ["a", "b", "c"]


def test_samma_processer_i_annan_insattningsordning_ger_samma_svar():
    a = Processordning([_p("a"), _p("b"), _p("c")], [_o("a", "c")]).ordning()
    b = Processordning([_p("c"), _p("b"), _p("a")], [_o("a", "c")]).ordning()
    assert a == b


def test_ett_ordningskrav_pa_en_okand_process_rapporteras():
    ordning = Processordning([_p("a")], [_o("a", "saknas")])
    assert "PO2_OKAND_PROCESS" in [k for k, _t in ordning.problem()]


def test_en_process_fore_sig_sjalv_rapporteras():
    ordning = Processordning([_p("a")], [_o("a", "a")])
    assert "PO4_SJALVORDNING" in [k for k, _t in ordning.problem()]


def test_tva_processer_med_samma_id_rapporteras():
    ordning = Processordning([_p("a"), _p("a")], [])
    assert "PO3_DUBBEL_PROCESS" in [k for k, _t in ordning.problem()]


def test_en_process_pa_en_roll_som_inte_finns_rapporteras():
    process = Process("a", "gora a", "robot", Harkomst("begaran", "gor a"))
    ordning = Processordning([process], [])
    assert "PO5_OKAND_ROLL" in [k for k, _t in ordning.problem(["band"])]
    assert ordning.problem(["robot"]) == []


def test_ett_dubblerat_ordningskrav_rapporteras():
    ordning = Processordning([_p("a"), _p("b")], [_o("a", "b"), _o("a", "b")])
    assert "PO6_DUBBELT_ORDNINGSKRAV" in [k for k, _t in ordning.problem()]


def test_en_hel_processordning_utan_brister_ger_tom_lista():
    assert Processordning([_p("a"), _p("b")], [_o("a", "b")]).problem() == []


def test_processordningen_gar_att_rundgangas_genom_json():
    ordning = Processordning([_p("a"), _p("b")], [_o("a", "b")])
    ny = Processordning.fran_json(ordning.till_json())
    assert ny.till_json() == ordning.till_json()


# ======================================================================
# ORDNINGEN (den delade rakningen)
# ======================================================================

def test_cykler_hittar_ringen_och_dess_medlemmar():
    assert ORD.cykler({"a": ["b"], "b": ["a"], "c": []}) == [["a", "b"]]


def test_cykler_hittar_en_nod_som_beror_pa_sig_sjalv():
    assert ORD.cykler({"a": ["a"]}) == [["a"]]


def test_en_djup_kedja_slar_inte_i_rekursionstaket():
    kanter = dict(("n%04d" % i, ["n%04d" % (i - 1)] if i else [])
                  for i in range(3000))
    assert ORD.cykler(kanter) == []
    ordnade, kvar = ORD.kanonisk_ordning(kanter)
    assert kvar == [] and len(ordnade) == 3000


def test_kanonisk_ordning_valjer_minsta_namnet_forst():
    ordnade, kvar = ORD.kanonisk_ordning({"b": [], "a": [], "c": []})
    assert ordnade == ["a", "b", "c"] and kvar == []


def test_kanonisk_ordning_lamnar_cykeln_i_kvarvarande():
    ordnade, kvar = ORD.kanonisk_ordning({"a": ["b"], "b": ["a"], "c": []})
    assert ordnade == ["c"] and kvar == ["a", "b"]


def test_okanda_kanter_rapporteras_med_bade_nod_och_mal():
    assert ORD.okanda_kanter({"a": ["saknas"]}) == [("a", "saknas")]


def test_lagren_ar_den_ovre_gransen_for_samtidighet():
    assert ORD.lager({"a": [], "b": [], "c": ["a", "b"]}) == [["a", "b"], ["c"]]


# ======================================================================
# TEXTLASNINGEN
# ======================================================================

def test_ett_tak_och_ett_golv_lases_som_olika_krav():
    tak = L.cellmatt("Cellen far vara hogst 2x2 meter.")
    golv = L.cellmatt("Cellen ska vara minst 3 meter bred.")
    assert ("bredd_mm", "le", 2000.0) == tak[0][:3]
    assert ("bredd_mm", "ge", 3000.0) == golv[0][:3]


def test_ett_konstaterande_ar_varken_tak_eller_golv():
    assert L.cellmatt("Cellen ar 6x6 meter.")[0][1] == "eq"


def test_varje_utlast_varde_bar_sin_ordagranna_textbit():
    for _falt, _op, _mm, belagg in L.cellmatt("Cellen far vara hogst 2x2 meter."):
        assert belagg in "Cellen far vara hogst 2x2 meter."


def test_enheter_raknas_till_millimeter():
    assert L.gangstrak("Gangstrak minst 1,2 meter").varde == 1200.0
    assert L.gangstrak("Gangstrak minst 800 mm").varde == 800.0


def test_rackvidd_och_arbetsradie_ar_olika_krav():
    egenskap = L.rackvidd("Roboten har rackvidd 1650 mm")[0]
    krav = L.rackvidd("Uppgiften kraver arbetsradie 1500 mm")[0]
    assert egenskap.vad == "egenskap" and egenskap.varde == 1650.0
    assert krav.vad == "krav" and krav.varde == 1500.0


def test_processer_och_ordning_lases_ur_meningen():
    processer, ordningar = L.processer("Forst plockning, sedan packning.")
    assert ("plockning", "packning") == ordningar[0][:2]
    assert sorted(p[0] for p in processer) == ["packning", "plockning"]


def test_en_process_som_inte_star_i_den_slutna_listan_blir_ingen_process():
    processer, _o = L.processer("Forst kalibrering, sedan justering.")
    assert processer == []


def test_kopplingar_lases_bara_mellan_KANDA_roller():
    assert L.kopplingar("Bandet matar roboten", ["band", "robot"]) \
        == [("band", "robot", "Bandet matar roboten")]
    assert L.kopplingar("Bandet matar traktorn", ["band", "robot"]) == []


def test_nakrav_binder_till_meningens_subjekt():
    krav = L.nakrav("Roboten ska na bandet och pallen.",
                    ["robot", "band", "pall"])
    assert sorted((a, b) for a, b, _c in krav) == [("robot", "band"),
                                                   ("robot", "pall")]


# ======================================================================
# LAYOUTPORTEN OCH LAYOUTMOTORN
# ======================================================================

class Trasigmotor(object):
    """En motor som svarar fel pa ett bestamt satt."""

    def __init__(self, svar):
        self.svar = svar

    def placera(self, begaran):
        return self.svar


def _spec_for_port():
    return DetaljeradSpec("s", Grundbegaran("s", "text", "prov"),
                          [Del("band", "u:b", 1, "transport",
                               [2000.0, 400.0, 900.0])])


def _tomt_svar(**kv):
    svar = {"v": 1, "placeringar": [], "antaganden": [], "fragor": []}
    svar.update(kv)
    return svar


def test_porten_avvisar_en_placering_pa_en_roll_som_inte_finns():
    motor = Trasigmotor(_tomt_svar(placeringar=[
        {"roll": "spoke", "position_mm": [0, 0, 0], "wpr_deg": [0, 0, 0],
         "motiv": "hittade pa"}]))
    with pytest.raises(Layoutfel):
        Layoutport(motor).placera(_spec_for_port(), 100.0)


def test_porten_avvisar_en_placering_utan_motiv():
    motor = Trasigmotor(_tomt_svar(placeringar=[
        {"roll": "band", "position_mm": [0, 0, 0], "wpr_deg": [0, 0, 0],
         "motiv": ""}]))
    with pytest.raises(Layoutfel):
        Layoutport(motor).placera(_spec_for_port(), 100.0)


def test_porten_slapper_igenom_tva_instanser_av_samma_roll():
    motor = Trasigmotor(_tomt_svar(placeringar=[
        {"roll": "band", "position_mm": [0, 0, 0], "wpr_deg": [0, 0, 0],
         "motiv": "instans ett", "instans": 1},
        {"roll": "band", "position_mm": [1, 0, 0], "wpr_deg": [0, 0, 0],
         "motiv": "instans tva", "instans": 2}]))
    svar = Layoutport(motor).placera(_spec_for_port(), 100.0)
    assert [p.instans for p in svar.placeringar] == [1, 2]


def test_porten_avvisar_samma_instans_tva_ganger():
    motor = Trasigmotor(_tomt_svar(placeringar=[
        {"roll": "band", "position_mm": [0, 0, 0], "wpr_deg": [0, 0, 0],
         "motiv": "ett", "instans": 1},
        {"roll": "band", "position_mm": [1, 0, 0], "wpr_deg": [0, 0, 0],
         "motiv": "tva", "instans": 1}]))
    with pytest.raises(Layoutfel):
        Layoutport(motor).placera(_spec_for_port(), 100.0)


def test_porten_avvisar_ett_svar_med_bade_placeringar_och_konflikt():
    """En halv layout ar farligare an ingen: den ser korbar ut."""
    motor = Trasigmotor(_tomt_svar(
        placeringar=[{"roll": "band", "position_mm": [0, 0, 0],
                      "wpr_deg": [0, 0, 0], "motiv": "nagot"}],
        konflikt=[{"kod": "X", "text": "gick inte", "roller": []}]))
    with pytest.raises(Layoutfel):
        Layoutport(motor).placera(_spec_for_port(), 100.0)


def test_porten_bar_motorns_egen_status_vidare():
    motor = Trasigmotor(_tomt_svar(status="RYMS_INTE"))
    svar = Layoutport(motor).placera(_spec_for_port(), 100.0)
    assert svar.status == "RYMS_INTE"
    assert "LAYOUT RYMS_INTE" in svar.rader()


def test_begaran_bar_relationer_datablad_och_omrade():
    spec = DetaljeradSpec(
        "s", Grundbegaran("s", "text", "prov"),
        [Del("robot", "u:r"), Del("band", "u:b")],
        relationer=[VS.Relation("nar", "robot", "band",
                                Harkomst("begaran", "ska na"))],
        omrade=Omrade(3000.0, 3000.0, 4000.0, 200.0,
                      Harkomst("begaran", "3x3 meter")))
    begaran = begaran_ur_spec(spec, 200.0, None, {"robot": {"rackvidd_mm": 1.0}})
    assert begaran["golv_mm"] == [3000.0, 3000.0]
    assert begaran["hojd_mm"] == 4000.0
    assert begaran["relationer"][0]["sort"] == "nar"
    assert begaran["datablad"]["robot"]["rackvidd_mm"] == 1.0


def test_motorn_vagrar_lamna_koordinater_ur_ett_antaget_ankare():
    """set_transform satter komponentens ORIGO, och var origo sitter vet bara
    VC. Ett antaget ankare flyttar komponenten fel, tyst."""
    svar = Layoutmotor(strikt_ankare=True).placera(_rackviddsbegaran(2600.0))
    assert svar["status"] == "LOST"
    assert svar["placeringar"] == []
    assert any(f["id"] == "layout:ankare" for f in svar["fragor"])


def test_motorn_fragar_om_matt_i_stallet_for_att_satta_dem_till_noll():
    begaran = _rackviddsbegaran(2600.0)
    begaran["delar"][1]["matt_mm"] = None
    svar = _motor().placera(begaran)
    assert any(f["id"] == "layout:matt:band" for f in svar["fragor"])
    assert svar["placeringar"] == []


def test_motorn_fragar_om_rackvidden_i_stallet_for_att_gissa_den():
    begaran = _rackviddsbegaran(2600.0)
    begaran["datablad"] = {}
    begaran["delar"][0]["matt_mm"] = [500.0, 500.0, 1400.0]
    svar = _motor().placera(begaran)
    assert any(f["id"] == "layout:rackvidd:robot" for f in svar["fragor"])


def test_motorn_skriver_ut_vilket_raster_svaret_galler():
    svar = _motor().placera(_rackviddsbegaran(2600.0))
    vad = [a["vad"] for a in svar["antaganden"]]
    assert "sokrastret" in vad


def test_motorn_hoppar_over_semantiska_relationer_med_skal():
    """K8: feeds, handoff och sequence domes inte av geometrin."""
    begaran = _rackviddsbegaran(2600.0)
    begaran["relationer"].append({"sort": "feeds", "fran_roll": "band",
                                  "till_roll": "robot", "hard": True})
    svar = _motor().placera(begaran)
    assert any("feeds" in a["vad"] for a in svar["antaganden"])


def test_motorn_utan_golv_fragar_i_stallet_for_att_valja_en_yta():
    begaran = _rackviddsbegaran(2600.0)
    begaran["golv_mm"] = None
    svar = _motor().placera(begaran)
    assert any(f["id"] == "layout:yta" for f in svar["fragor"])


# ======================================================================
# GRINDKEDJAN SOM HELHET
# ======================================================================

def test_grindarna_kors_i_den_ordning_listan_sager():
    """En bestallning som ar trasig i BADE processordning och villkor ska
    falla pa den TIDIGARE grinden. Ordningen ar inte kosmetisk: den billiga
    och exakta grinden ska svara fore den dyra och sokande."""
    besked = _besked("Bygg en cell. Forst svetsning, sedan malning. "
                     "Malning fore svetsning. Cellen far vara hogst 2x2 meter "
                     "och minst 3 meter bred.")
    assert besked.grind == "B2_PROCESSORDNING"


def test_varje_grind_i_listan_har_ett_prov_som_faller_pa_den():
    """Ingen grind utan trasig fixtur.

    Star en grind i GRINDAR men ingen bestallning faller pa den, ar den
    oprovad - och en oprovad grind ar en forhoppning som har fatt ett namn.
    """
    fall = {
        "B1_HARKOMST": test_T3_ett_uppfunnet_krav_som_pastar_sig_komma_ur_begaran_avvisas,
        "B2_PROCESSORDNING": test_T2_en_cyklisk_processordning_avvisas,
        "B3_MOTSAGELSE": test_T1_en_sjalvmotsagande_bestallning_avvisas,
        "B4_FRAGOR": test_T5_en_bestallning_utan_topologi_blir_ofullstandig,
        "B5_LAYOUT": test_T4e_bestallningen_stoppas_pa_layoutgrinden,
        "B6_PLANEN": None,
        "B0_FRAGERUNDOR": test_en_tredje_frageruna_avbryts_och_rapporterar_vad_som_saknas,
    }
    saknade = [g for g in B.GRINDAR if g not in fall]
    assert not saknade, "grindar utan trasig fixtur: %s" % saknade


def test_B6_faller_pa_ett_verktyg_som_inte_finns():
    """Den sjatte grinden, provad direkt: ett steg vars verktyg inte finns i
    registret avvisas VID PLANERINGEN."""
    from vc_assist_svc.plan.byggplan import Byggplan
    from vc_assist_svc.plan.graf import Uppgiftsgraf
    from vc_assist_svc.plan.steg import Steg
    spec, _blad = _spec("Bygg en cell med ett band.")
    plan = Byggplan("p", spec, Uppgiftsgraf([
        Steg.verktygssteg("x", "finns_inte_i_registret", {}, "provsteg")]))
    assert "P1_OKANT_VERKTYG" in [k for k, _t in plan.granska()]


def test_en_bankuppgift_domes_av_samma_grindar_som_en_bestallning():
    """Bankvagen och fritextvagen far inte ha var sin mattstock."""
    import json
    import glob
    sokvag = sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter",
                                           "*.json")))[0]
    with open(sokvag, encoding="utf-8") as f:
        data = json.load(f)
    forfinare = Forfinare()
    spec = forfinare.ur_bankuppgift(data)
    besked = B.doma(spec, forfinare.datablad)
    # Uppgiften bar bank://-URI:er som inte gar att ladda, sa den ar
    # ofullstandig - men den ska falla pa en FRAGA, aldrig pa harkomsten.
    assert besked.status in (B.OFULLSTANDIG, B.AVVISAD)
    assert besked.grind != "B1_HARKOMST", besked.text()


def test_bankens_forreglingar_blir_prosakrav_med_konsument():
    """125 forreglingar i bankens uppgifter (matt vid 51 uppgifter, M-45) ar
    akta krav som K6:s trippelsprak inte
    kan uttrycka. De far darfor en egen form - men aldrig utan en konsument."""
    import json
    import glob
    for sokvag in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter",
                                                "*.json")))[:6]:
        with open(sokvag, encoding="utf-8") as f:
            data = json.load(f)
        spec = Forfinare().ur_bankuppgift(data)
        for krav in spec.prosakrav:
            assert krav.konsument
            assert krav.harkomst.kalla == "bank"


def test_bankens_expect_blir_typade_villkor_med_harkomst():
    import json
    import glob
    sokvag = sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter",
                                           "*.json")))[0]
    with open(sokvag, encoding="utf-8") as f:
        data = json.load(f)
    spec = Forfinare().ur_bankuppgift(data)
    storheter = [v.storhet for v in spec.villkor]
    assert "scen.kollisioner" in storheter
    for v in spec.villkor:
        assert v.harkomst.kalla == "bank"
        assert "#" in v.harkomst.belagg


def test_specen_gar_att_rundgangas_genom_json_med_alla_nya_falt():
    spec, _blad = _spec()
    ut = spec.till_json()
    assert DetaljeradSpec.fran_json(ut).till_json() == ut
    assert ut["v"] == 3
    assert ut["processordning"]["processer"]
    assert ut["villkor"] and ut["relationer"] and ut["omrade"]


def test_en_gammal_spec_i_version_1_faller_pa_versionen():
    spec, _blad = _spec()
    ut = spec.till_json()
    ut["v"] = 1
    with pytest.raises(Specfel):
        DetaljeradSpec.fran_json(ut)


def test_kopplingen_bar_sin_harkomst_ur_begaran():
    spec, _blad = _spec()
    assert spec.kopplingar
    for k in spec.kopplingar:
        assert k.harkomst.kalla == "begaran"
        assert normalisera(k.harkomst.belagg) in normalisera(BESTALLNING)


def test_en_koppling_utan_harkomst_faller_i_harkomstgrinden():
    spec, blad = _spec()
    spec.kopplingar.append(Koppling("band", "pall"))
    besked = B.doma(spec, blad)
    assert besked.grind == "B1_HARKOMST"
    assert "HK1_UTAN_HARKOMST" in [k for k, _t in besked.problem]


# ======================================================================
# HELA BANKEN GENOM GRINDKEDJAN
# ======================================================================
#
# Bankens uppgifter ur bank/uppgifter/ ar det narmaste verkliga bestallningar vi
# har. Att kora dem alla svarar pa den fraga en handplockad fixtur aldrig kan
# svara pa: ar grindarna for TRANGA? En grind som faller pa riktig data den
# borde slappa igenom ar lika trasig som en som slapper igenom allt.

def _bankuppgifter():
    import glob
    import json
    for sokvag in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter",
                                                "*.json"))):
        with open(sokvag, encoding="utf-8") as f:
            yield json.load(f)


def _bankindex():
    import json
    with open(os.path.join(_ROT, "bank", "katalog_index.json"),
              encoding="utf-8") as f:
        kat = json.load(f)
    index = dict((p["uri"], p) for p in kat["poster"])
    # bank:// ar bankens egen vokabular och pekar inte pa nagon fil VC kan
    # ladda. Kartan finns for MATNING och far aldrig koras: en uppfunnen URI
    # ar ett hart fel (I9). provplaner.py gor samma sak, av samma skal.
    karta = dict((u, "file:///demonstration/%s.vcm" % u.split("/")[-1])
                 for u in index)
    return index, karta


def _banksvep():
    index, karta = _bankindex()
    ut = []
    for data in _bankuppgifter():
        forfinare = Forfinare(index, karta)
        spec = forfinare.ur_bankuppgift(data)
        ut.append((data["task_id"], spec,
                   B.doma(spec, forfinare.datablad)))
    return ut


def test_hela_banken_gar_genom_grindkedjan_utan_falska_roda():
    """58 av 63 uppgifter blir BYGGBARA. De fem som inte blir det ar de som
    banken sjalv faller FORE ogat (grind 1-4) och som darfor inte bar en enda
    rad ogat kan skriva - de har inget facit att stalla planen mot.

    Talen var 46 av 51 fram till M-106, som tog in tolv nya industriuppgifter.
    Alla tolv gick genom grindkedjan utan anmarkning, sa de fem ofullstandiga
    ar samma fem som forut. Sparren gar bara at ett hall."""
    svep = _banksvep()
    byggbara = [t for t, _s, b in svep if b.status == B.BYGGBAR]
    ofullstandiga = [t for t, _s, b in svep if b.status == B.OFULLSTANDIG]
    assert len(svep) == 63
    assert len(byggbara) == 58, sorted(set(t for t, _s, _b in svep)
                                       - set(byggbara))
    assert sorted(ofullstandiga) == ["A-90", "P-90", "S-90", "S-91", "T-90"]


def test_ingen_bankuppgift_faller_pa_de_tre_nya_grindarna():
    """Harkomst, processordning och motsagelse far inte fyra pa riktig data.

    Det ar den enda matningen som visar om en ny grind ar for trang, och den
    gar bara att gora over en samling man inte skrev sjalv."""
    for task_id, _spec, besked in _banksvep():
        assert besked.grind not in ("B1_HARKOMST", "B2_PROCESSORDNING",
                                    "B3_MOTSAGELSE"), \
            "%s foll pa %s: %s" % (task_id, besked.grind, besked.problem[:1])


def test_bankens_villkor_ar_typade_och_forreglingarna_bar_konsument():
    """Fore M-63 var alla 301 kraven prosa i ett falt ingen laste."""
    typade = 0
    prosa = 0
    for _t, spec, _b in _banksvep():
        typade += len(spec.villkor)
        prosa += len(spec.prosakrav)
    assert typade >= 170, typade
    assert prosa >= 120, prosa


def test_rackviddskravet_har_ett_kant_varde_i_varje_uppgift_som_bar_det():
    """En grind vars storhet alltid ar OKAND mater ingenting."""
    krav = 0
    kanda = 0
    for _t, spec, besked in _banksvep():
        faktarum = ST.Faktarum(spec, besked.datablad)
        for v in spec.villkor:
            if v.storhet.endswith("rackvidd_mm"):
                krav += 1
                kanda += 1 if faktarum.las(v.storhet).kant else 0
    assert krav >= 25, krav
    assert kanda == krav, "%d av %d rackviddskrav saknade varde" % (
        krav - kanda, krav)


def test_en_planterad_for_stor_arbetsradie_falls_i_en_riktig_bankuppgift():
    """Facitlacka, planterad i riktig data.

    Uppgiften ar gron som den star. Hojs arbetsradien over robotens publicerade
    rackvidd ska den falla - och falla som ett fallt VAL, inte som en omojlig
    bestallning. Skillnaden ar botemedlet: byt robot, inte krav.
    """
    import copy
    index, karta = _bankindex()
    data = next(d for d in _bankuppgifter() if d["task_id"] == "A-01")
    frisk = Forfinare(index, karta)
    assert B.doma(frisk.ur_bankuppgift(data), frisk.datablad).status == B.BYGGBAR

    trasig = copy.deepcopy(data)
    trasig["fysik"]["arbetsradie_mm"] = 9000.0
    forfinare = Forfinare(index, karta)
    besked = B.doma(forfinare.ur_bankuppgift(trasig), forfinare.datablad)
    assert besked.status == B.AVVISAD
    assert besked.grind == "B3_MOTSAGELSE"
    assert besked.motsagelsedom.dom == MO.VALET_FALLER
    text = "\n".join(t for _k, t in besked.problem)
    assert "9000" in text and "1650" in text
    assert "Byt komponent" in text


def test_de_matta_kraven_skjuts_upp_till_efter_bygget_i_varje_uppgift():
    """scen.kollisioner och scen.min_avstand_mm ar okanda av KONSTRUKTION
    fore bygget. De far inte blockera, och de far inte forsvinna."""
    for task_id, _spec, besked in _banksvep():
        storheter = [s for s, _i in besked.motsagelsedom.att_mata]
        assert "scen.kollisioner" in storheter, task_id


# ======================================================================
# DE FYRA ARTEFAKTERNA PA DISK
# ======================================================================
#
# 22_planeringslagret.md: "Alla fyra ar JSON pa disk under
# bank/plans/<plan_id>/. Ingen artefakt far existera enbart som text i en
# modellprompt." Skalet star i samma dokument: en plan som bara finns i en
# prompt gar inte att granska, versionera eller mata mot.

from vc_assist_svc.plan import artefakter as A                # noqa: E402


def test_alla_fyra_artefakterna_skrivs(tmp_path):
    filer = A.skriv(_besked(), str(tmp_path))
    assert sorted(filer) == ["layout", "plan", "sekvens", "spec"]
    for sokvag in filer.values():
        assert os.path.exists(sokvag)
        assert os.path.getsize(sokvag) > 0


def test_artefakterna_hamnar_under_plan_id(tmp_path):
    besked = _besked()
    filer = A.skriv(besked, str(tmp_path))
    for sokvag in filer.values():
        assert os.path.basename(os.path.dirname(sokvag)) == besked.plan.id


def test_ett_nej_skriver_inga_artefakter(tmp_path):
    """En artefaktkatalog med tre av fyra filer ser ut som en plan."""
    with pytest.raises(Planfel):
        A.skriv(_besked(MOTSAGELSE), str(tmp_path))
    assert list(tmp_path.iterdir()) == []


def test_sekvensen_ar_densamma_byte_for_byte_over_tre_korningar(tmp_path):
    """K22: determinism mätt, inte påstådd."""
    hashar = set()
    for varv in range(3):
        filer = A.skriv(_besked(), str(tmp_path / str(varv)))
        hashar.add(A.las_sekvens(filer["sekvens"])["hash"])
    assert len(hashar) == 1, hashar


def test_en_andrad_artefakt_avvisas_pa_hashen(tmp_path):
    """Trasig fixtur for hashen sjalv. En artefakt som andrats efter att den
    skrevs ar inte den artefakt planen godkandes som."""
    import json
    filer = A.skriv(_besked(), str(tmp_path))
    with open(filer["sekvens"], encoding="utf-8") as f:
        data = json.load(f)
    data["anrop"][0]["verktyg"] = "delete_component"
    with open(filer["sekvens"], "w", encoding="utf-8") as f:
        json.dump(data, f)
    with pytest.raises(Planfel) as fel:
        A.las_sekvens(filer["sekvens"])
    assert "changed" in str(fel.value)


def test_en_sekvens_utan_hash_gar_inte_att_lita_pa(tmp_path):
    import json
    sokvag = str(tmp_path / "utan.json")
    with open(sokvag, "w", encoding="utf-8") as f:
        json.dump({"v": 1, "anrop": []}, f)
    with pytest.raises(Planfel):
        A.las_sekvens(sokvag)


def test_sekvensen_bar_lage_ur_REGISTRET_inte_ur_planen():
    """I12: routingen read -> exec och write -> exec_queue ags av utforaren.
    Planen bar inget falt for den, och sekvenseraren skriver ut den."""
    sekvens = A.anropssekvens(_besked().plan)
    lagen = set(a.get("lage") for a in sekvens["anrop"]
                if a["sort"] == "verktyg")
    assert lagen == {"read", "write"}
    assert "OKANT" not in lagen


def test_sekvensen_bar_bindningarna_olosta():
    """En sekvens som bar ett gissat gransnittsnamn hade sett korbar ut och
    varit ett pahitt (I9). Bindningen loses forst ur scenens EGET svar."""
    sekvens = A.anropssekvens(_besked().plan)
    bundna = [a for a in sekvens["anrop"] if a["sort"] == "verktyg"
              and any(isinstance(v, dict) and "$bindning" in v
                      for v in a["argument"].values())]
    assert bundna, "ingen bindning overlevde till sekvensen"


def test_layoutartefakten_bar_harkomst_per_tal():
    """K9: varje tal i LAYOUT bar {value, method, gate}. Ett tal utan grind
    ar ett lintfel."""
    besked = _besked()
    layout = A.layoutartefakt(besked.plan, besked.layoutsvar)
    assert layout["stations"]
    for station in layout["stations"]:
        for falt in ("anchor", "yaw_deg"):
            assert set(station[falt]) == {"value", "method", "gate"}
            assert station[falt]["method"]
            assert station[falt]["gate"] == A.LAYOUTGRIND


def test_arbetsutrymmet_skrivs_som_OKANT_aldrig_som_noll():
    """K12: `work_area_mm` null far inte tyst tolkas som noll."""
    besked = _besked()
    layout = A.layoutartefakt(besked.plan, besked.layoutsvar)
    assert all(s["work_area"] == "UNKNOWN" for s in layout["stations"])


def test_utan_layoutmotor_skrivs_artefakten_anda_med_skal():
    """En artefakt som inte finns lases som 'ingen layout behovdes'."""
    besked = _besked(motor=False)
    layout = A.layoutartefakt(besked.plan, besked.layoutsvar)
    assert layout["status"] == "EJ_KORD"
    assert layout["stations"] == []
    assert "plug and play" in layout["skal"]


def test_specartefakten_gar_att_lasa_tillbaka(tmp_path):
    filer = A.skriv(_besked(), str(tmp_path))
    import json as _json
    with open(filer["spec"], encoding="utf-8") as f:
        data = _json.load(f)
    assert DetaljeradSpec.fran_json(data).id == "bestallning"


# ======================================================================
# TVA TYSTA BORTFALL SOM HITTADES GENOM ATT SPELA SOM OPERATOREN
# ======================================================================
#
# Bada foll ut nar operatorens EGEN exempeltext ur 27_operatorsflodet kordes
# genom lagret, och ingen av dem hade nagot prov emot sig. Bada gav ett gront
# svar pa en fraga som inte var stalld.

OPERATORENS_EXEMPEL = (
    "Bygg en plockstation som klarar 400 detaljer i timmen, med ett "
    "inmatningsband, en robot och en utlastningslåda. Skriv PLC-koden.")


def test_ett_sammansatt_ord_kanns_igen_pa_sitt_efterled():
    """'inmatningsband' ar ett band. Fore rattelsen var det ingenting alls,
    och planen blev BYGGBAR med en tredjedel av det operatoren bad om."""
    spec, _blad = _spec(OPERATORENS_EXEMPEL)
    assert "band" in [d.roll for d in spec.delar]


def test_ett_prefix_kanns_INTE_igen_som_komponent():
    """Motprovet at andra hallet: prefixmatchning hade last 'pallmagasin' som
    'pall' och gett en lastbarare ingen bett om. Det star redan i ORDBOKs
    egen kommentar, och regeln ar suffix - aldrig prefix."""
    katalog = dict(KATALOG)
    katalog["file:///magasin.vcm"] = {
        "uri": "file:///magasin.vcm", "namn": "Pallmagasin",
        "kategori": "station", "l_mm": 1400.0, "b_mm": 1000.0, "h_mm": 2000.0}
    forfinare = Forfinare(katalog)
    spec = forfinare.ur_fritext(Grundbegaran(
        "p", "Bygg en cell med ett pallmagasin.", "operator"))
    assert "pall" not in [d.roll for d in spec.delar]


def test_ett_okant_ord_i_upprakningen_blir_en_BLOCKERANDE_fraga():
    """Det tysta bortfallet, fangat.

    'utlastningslada' finns inte i den slutna ordlistan. Fore rattelsen
    hoppades den tyst over och beskedet blev BYGGBAR.
    """
    besked = _besked(OPERATORENS_EXEMPEL)
    assert besked.status == B.OFULLSTANDIG, besked.text()
    assert any("okant_ord" in t for _k, t in besked.problem), besked.problem


def test_fragan_om_det_okanda_ordet_citerar_operatorens_egna_ord():
    besked = _besked(OPERATORENS_EXEMPEL)
    text = "\n".join(t for _k, t in besked.problem)
    assert "utlastningslåda" in text


def test_en_upprakning_dar_allt_kanns_igen_ger_ingen_sadan_fraga():
    """Motprovet. En grind som faller pa varje upprakning mater ingenting."""
    besked = _besked()
    assert not [k for k, t in besked.problem if "okant_ord" in t]


def test_ett_processord_lases_inte_ur_mitten_av_ett_annat_ord():
    """'inmatningsband' gav fore rattelsen BADE processen 'inmatning' och
    processen 'matning'. Bestallningen fick tva processer den aldrig namnde,
    och bada bar ett akta belagg ur operatorens text - belagget var sant,
    tolkningen var pahittad."""
    processer, ordningar = L.processer(OPERATORENS_EXEMPEL)
    assert processer == []
    assert ordningar == []


def test_samma_processord_som_eget_ord_lases_fortfarande():
    processer, _o = L.processer("Cellen ska klara inmatning och packning.")
    assert sorted(p[0] for p in processer) == ["inmatning", "packning"]


# ======================================================================
# RACKVIDDENS TVA LASNINGAR
# ======================================================================
#
# layout/relationer.py sager sjalv att InomRackvidd har tva lasningar:
# helt=True (hela fotavtrycket inom radien, den harda) och helt=False (nagon
# del inom radien, ratt for ett langt band dar bara plocklaget behover nas).
# MATT i M-63: med den harda lasningen kan en robot pa 1650 mm inte na ett
# 2 m langt band, och varenda cell med en transportor blev avvisad. Ett
# falskt rott ar den varsta sorten, for det ser ut som ett svar.

MONTERINGSCELL = (
    "Bygg en monteringscell med ett band, en robot, en fixtur och en pall. "
    "Cellen är 8x8 meter. Gångstråk minst 800 mm. "
    "Bandet matar roboten, roboten kopplas till fixturen och fixturen matar "
    "pallen. Roboten ska nå bandet och fixturen. "
    "Först inmatning, sedan montering, sedan utmatning.")


def _stor_katalog():
    katalog = dict(KATALOG)
    katalog["file:///fixtur.vcm"] = {
        "uri": "file:///fixtur.vcm", "namn": "Fixtur", "kategori": "station",
        "l_mm": 1200.0, "b_mm": 900.0, "h_mm": 1000.0}
    return katalog


def test_nar_bara_den_mjuka_lasningen_gar_blir_svaret_en_FRAGA_inte_ett_nej():
    """Ingenting ar bevisat omojligt - nagot ar obestamt. Skillnaden ar
    botemedlet: ett svar, inte en ny bestallning."""
    besked = B.bestall(MONTERINGSCELL, _stor_katalog(), motor=_motor())
    assert besked.status == B.OFULLSTANDIG, besked.text()
    assert besked.grind == "B5_LAYOUT"
    assert besked.plan is None


def test_fragan_bar_BADA_svaren_raknade():
    """Ett val vi inte far gora at operatoren ska atminstone komma med vad de
    tva alternativen kostar."""
    besked = B.bestall(MONTERINGSCELL, _stor_katalog(), motor=_motor())
    fragor = [f for f in besked.spec.oppna_fragor()
              if f.id == "layout:rackviddens_lasning"]
    assert fragor, [f.id for f in besked.spec.oppna_fragor()]
    varfor = fragor[0].varfor
    assert "harda" in varfor and "mjuka" in varfor
    assert "sokraster" in varfor


def test_valet_gors_aldrig_at_operatoren():
    """Planen far inte tyst byta till den mjuka lasningen: da skulle den lova
    att roboten nar nagot den kanske inte nar."""
    besked = B.bestall(MONTERINGSCELL, _stor_katalog(), motor=_motor())
    assert besked.plan is None
    varden = [str(a.varde) for a in besked.spec.antaganden]
    assert "hela malets fotavtryck" in varden


def test_nar_INGEN_lasning_gar_ar_det_ett_akta_nej():
    """Motprovet: en robot som inte nar ens en del av malet ger AVVISAD, utan
    fragan om lasningen."""
    svar = _motor().placera(_rackviddsbegaran(400.0, golv=(3000.0, 3000.0)))
    assert svar["status"] in ("OVERBESTAMD", "RYMS_INTE")
    assert not [f for f in svar["fragor"]
                if f["id"] == "layout:rackviddens_lasning"]


# ======================================================================
# ROBOTENS FOTAVTRYCK HARLEDS UR RACKVIDDEN
# ======================================================================

def test_robotens_fotavtryck_harleds_sa_att_ytbeviset_gar_att_kora():
    """En robot i katalogen bar sallan langd och bredd - den bar en rackvidd.
    Utan fotavtrycket blir domen OKANT for varenda bestallning med en robot,
    och en grind som alltid sager okant har slutat mata."""
    from vc_assist_svc.plan.layoutmotor import harled_fotavtryck
    spec, blad = _spec()
    nytt, harledda = harled_fotavtryck(spec, blad)
    assert nytt["robot"]["langd_mm"] > 0
    assert harledda and "rackvidd" in harledda[0][2]


def test_ett_matt_tal_skrivs_aldrig_over_av_ett_harlett():
    from vc_assist_svc.plan.layoutmotor import harled_fotavtryck
    spec, blad = _spec()
    blad["robot"].update({"langd_mm": 1.0, "bredd_mm": 2.0, "hojd_mm": 3.0})
    nytt, harledda = harled_fotavtryck(spec, blad)
    assert nytt["robot"]["langd_mm"] == 1.0
    assert harledda == []


def test_harledningen_ar_ett_MARKT_antagande_i_specen():
    besked = _besked()
    vad = [a.vad for a in besked.spec.antaganden]
    assert "fotavtryck for robot" in vad
    motiv = [a.motiv for a in besked.spec.antaganden
             if a.vad == "fotavtryck for robot"][0]
    assert "harlett" in motiv and "ANTAGNA" in motiv


def test_ytbeviset_faller_pa_en_for_liten_cell_i_en_riktig_bestallning():
    """Fas 16:s namngivna fall, hela vagen fran fri text."""
    besked = _besked(
        "Bygg en plockcell med ett band, en robot och en pall. "
        "Cellen får vara högst 2x2 meter. Gångstråk minst 800 mm. "
        "Bandet matar roboten och roboten kopplas till pallen. "
        "Roboten ska nå bandet och pallen.")
    assert besked.status == B.AVVISAD, besked.text()
    assert besked.grind == "B3_MOTSAGELSE"
    text = "\n".join(t for _k, t in besked.problem)
    assert "MK3_YTA" in [k for k, _t in besked.problem]
    assert "m2" in text and "800 mm gang" in text


def test_samma_fotavtryck_raknas_bara_EN_gang():
    """Tva antaganden om samma sak ar tva halvor av samma begrepp som inte
    mots. Motorn ska anvanda databladets tal, inte rakna om det."""
    besked = _besked()
    vad = [a.vad for a in besked.spec.antaganden]
    assert vad.count("fotavtryck for robot") == 1, vad


# ======================================================================
# SAMTALET: FRAGA, SVAR, PLAN - OCH ETT TAK PA ANTALET RUNDOR
# ======================================================================
#
# K4: "clarify_round <= 2 per plan, annars avbryt och rapportera vad som
# saknas." Kallans loopsparr laste den foregaende turens TEXT och matchade pa
# en svensk-engelsk fras (orchestrator.py:783). Det ar skort; talet bars i
# artefakten i stallet.

TVA_FRAGOR = ("Bygg en plockstation som klarar 400 detaljer i timmen, med ett "
              "inmatningsband, en robot och en utlastningslåda.")


def _katalog_med_kassation():
    katalog = dict(KATALOG)
    katalog["file:///kass.vcm"] = {
        "uri": "file:///kass.vcm", "namn": "Kassationslåda",
        "kategori": "station", "l_mm": 800.0, "b_mm": 600.0, "h_mm": 800.0}
    return katalog


SVAREN = {"okant_ord:utlastningslada": "en kassationslada",
          "kopplingar": "bandet matar roboten och roboten matar kassationsladan",
          "cellyta": "cellen ar 8x8 meter, gangstrak minst 800 mm"}


def test_forsta_turen_fragar_och_lamnar_ingen_plan():
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor())
    assert besked.status == B.OFULLSTANDIG
    assert besked.plan is None
    assert len(besked.problem) >= 2


def test_andra_turen_med_svaren_ger_en_byggbar_plan():
    """Detaljeringen fran grundbegaran, hela vagen: fraga, svar, plan."""
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor(),
                       svar=SVAREN)
    assert besked.status == B.BYGGBAR, besked.text()
    assert len(besked.plan) >= 20


def test_svaren_blir_en_del_av_begaran_ordagrant():
    """Svaren ar operatorens ord lika mycket som den forsta meningen, och
    harkomstgrinden ska kunna hitta dem dar."""
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor(),
                       svar=SVAREN)
    assert "kassationsladan" in normalisera(besked.spec.begaran.text)
    for k in besked.spec.kopplingar:
        assert normalisera(k.harkomst.belagg) in normalisera(
            besked.spec.begaran.text)


def test_en_besvarad_fraga_star_kvar_men_blockerar_inte():
    """Att ta bort fragan hade gjort skillnaden mellan 'vi fragade aldrig' och
    'vi fragade och fick svar' osynlig."""
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor(),
                       svar=SVAREN)
    besvarade = [f for f in besked.spec.fragor if not f.oppen]
    assert [f.id for f in besvarade] == ["okant_ord:utlastningslada"]
    assert besvarade[0].svar == "en kassationslada"
    assert besked.spec.blockerande_fragor() == []


def test_ett_svar_som_inte_namner_nagot_kant_loser_ingenting():
    """Motprovet. Ett svar som inte gar att lasa ar inget svar."""
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor(),
                       svar={"okant_ord:utlastningslada": "en sådan där grej"})
    assert besked.status == B.OFULLSTANDIG
    assert any("okant_ord" in t for _k, t in besked.problem)


def test_en_tredje_frageruna_avbryts_och_rapporterar_vad_som_saknas():
    """K4:s tak. En loop som fragar i evighet ar inte en klarifiering; den ar
    ett satt att aldrig behova svara."""
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor(),
                       svar={"kopplingar": "vet inte"}, fragerunda=3)
    assert besked.status == B.OFULLSTANDIG
    assert besked.grind == "B0_FRAGERUNDOR"
    koder = [k for k, _t in besked.problem]
    assert "B0_FOR_MANGA_RUNDOR" in koder
    assert "B0_SAKNAS" in koder


def test_tva_rundor_ar_tillatna():
    """Motprovet at andra hallet: taket ar tva, inte en."""
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor(),
                       svar=SVAREN, fragerunda=2)
    assert besked.grind != "B0_FRAGERUNDOR", besked.text()


def test_fragerundan_star_i_specen_och_i_artefakten(tmp_path):
    import json as _json
    besked = B.bestall(TVA_FRAGOR, _katalog_med_kassation(), motor=_motor(),
                       svar=SVAREN)
    assert besked.spec.fragerunda == 1
    filer = A.skriv(besked, str(tmp_path))
    with open(filer["spec"], encoding="utf-8") as f:
        assert _json.load(f)["fragerunda"] == 1


# ======================================================================
# K1: VARJE FRAGA SAGER VAD DEN BEHOVS TILL
# ======================================================================

def test_varje_fraga_lagret_stallar_sager_vad_den_behovs_till():
    """K1: ett falt utan `needed_for` far inte finnas i schemat.

    Fragorna ar de tomma slotsen i praktiken. Svepet gar over hela banken och
    over fritextvagen, sa en fraga som lagts till utan en rad i BEHOVS_FOR
    upptacks har och inte hos operatoren.
    """
    from vc_assist_svc.plan.forfining import behovs_for
    sedda = set()
    for text in (BESTALLNING, MOTSAGELSE, CYKEL, TVA_FRAGOR,
                 OPERATORENS_EXEMPEL, MONTERINGSCELL,
                 "Bygg en cell med ett band och en robot. Cellen ar 3x3 meter. "
                 "Gangstrak minst 200 mm. Bandet matar roboten. Roboten ska na "
                 "bandet. Roboten har rackvidd 900 mm."):
        besked = B.bestall(text, _stor_katalog(), motor=_motor())
        for fraga in besked.spec.fragor:
            sedda.add(fraga.id)
            assert behovs_for(fraga.id), fraga.id
    for _t, spec, _b in _banksvep():
        for fraga in spec.fragor:
            sedda.add(fraga.id)
            assert behovs_for(fraga.id), fraga.id
    assert len(sedda) >= 6, sedda


def test_en_fraga_utan_rad_i_tabellen_avvisar_planen():
    """Trasig fixtur for K1 sjalv. En fraga vars id ingen rad tacker ar ett
    fel i VAR kod, och den ska falla har och inte hos operatoren."""
    from vc_assist_svc.plan.spec import Fraga
    spec, blad = _spec("Bygg en cell med ett band.")
    spec.fragor.append(Fraga(
        "nytt_slot_utan_behov", "vad ska det vara?",
        "ett skal som ar langt nog for kravet pa fyrtio tecken i motivet"))
    besked = B.doma(spec, blad)
    assert besked.status == B.AVVISAD
    assert "S1_SLOT_UTAN_BEHOV" in [k for k, _t in besked.problem]


def test_den_blockerande_fragan_skriver_ut_vad_den_behovs_till():
    besked = _besked("Bygg en cell med ett band, en robot och en pall.")
    assert besked.status == B.OFULLSTANDIG
    assert any("behovs for" in t for _k, t in besked.problem)


# ======================================================================
# GRANSEN MOT VC: layout/vc_utdata.py
# ======================================================================
#
# Det ar den modulen som gor layoutmotorns svar till set_transform-anrop, och
# den bar ankargrinden som hela `strikt_ankare` vilar pa. Planeringslagret
# LITAR pa den, sa den provas har - vid gransen, av den som anvander den.
# (M-68 raknade den som helt oprovad.)

def test_vc_utdata_vagrar_skriva_ett_anrop_ur_ett_ANTAGET_ankare():
    """set_transform satter komponentens ORIGO, och var origo sitter i
    forhallande till lados mitt vet bara VC. Ett antaget ankare flyttar
    komponenten fel, tyst."""
    from vc_assist_svc.layout.matt import Langd
    from vc_assist_svc.layout.rum import Hall, Objekt, Pose, Scen
    from vc_assist_svc.layout.vc_utdata import Ankarfel, till_verktygsanrop
    scen = Scen(Hall("h", Langd.mm(4000.0), Langd.mm(4000.0), Langd.mm(3000.0)))
    scen.lagg_till(Objekt("band", Langd.mm(2000.0), Langd.mm(400.0),
                          Langd.mm(900.0)))
    scen.placera("band", Pose.meter(1.0, 1.0, 0.0, 0.0))
    with pytest.raises(Ankarfel):
        till_verktygsanrop(scen)


def test_vc_utdata_skriver_millimeter_och_vridning_i_TREDJE_talet():
    """Motprovet, och den falla modulen sjalv varnar for: wpr ar W kring X,
    P kring Y, R kring Z - vridningen hor i tredje talet."""
    from vc_assist_svc.layout.matt import Langd
    from vc_assist_svc.layout.rum import Hall, Objekt, Pose, Scen
    from vc_assist_svc.layout.vc_utdata import till_verktygsanrop
    scen = Scen(Hall("h", Langd.mm(4000.0), Langd.mm(4000.0), Langd.mm(3000.0)))
    scen.lagg_till(Objekt("band", Langd.mm(2000.0), Langd.mm(400.0),
                          Langd.mm(900.0)))
    scen.placera("band", Pose.meter(1.0, 2.0, 0.0, 90.0))
    anrop = till_verktygsanrop(scen, strikt=False)
    assert len(anrop) == 1
    assert anrop[0].verktyg == "set_transform"
    assert anrop[0].argument["position"][:2] == [1000.0, 2000.0]
    assert anrop[0].argument["wpr"] == [0.0, 0.0, 90.0]


def test_layoutmotorns_koordinater_kommer_genom_vc_utdata():
    """Planeringslagret raknar ingen origoforskjutning sjalvt. Gjorde det
    det vore det tva implementationer av samma omraking, och de tva vore
    olika sa fort nagon andrade den ena (I1)."""
    svar = _motor().placera(_rackviddsbegaran(2600.0))
    assert svar["status"] == "LOST"
    for p in svar["placeringar"]:
        assert p["wpr_deg"][0] == 0.0 and p["wpr_deg"][1] == 0.0
        assert len(p["position_mm"]) == 3
