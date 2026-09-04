# -*- coding: utf-8 -*-
"""L0/L1 för layoutmotorn: enheter, rum, kollision, fria ytor, utdata mot VC.

Placeringsspråket och lösaren provas i test_layout_placering.py.

Tre saker prövas här, och den sista är den som gör proven värda något:

1. ENHETSSKYDDET. Ett bart tal går inte att göra till en längd. Det är
   uppdragets krav på att mm och m inte ska gå att blanda ihop, och det
   prövas som ett fel som KASTAS, inte som en konvention som beskrivs.
2. GEOMETRIN. Överlapp, underhållsutrymme, zoner, fri höjd, passagebredd och
   fria ytor, var för sig, på handräknade fall.
3. TRASIGA FIXTURER. Varje grind har minst ett fall som MÅSTE falla.
   docs/spec/95_testprotokoll.md: "En grind som aldrig fällt är oprövad."
"""
import ast
import io
import math
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import layout as L                       # noqa: E402

_LAYOUTMAPP = os.path.join(_ROT, "svc", "vc_assist_svc", "layout")
_MODULER = sorted(f for f in os.listdir(_LAYOUTMAPP) if f.endswith(".py"))


def _kalla(fil):
    with io.open(os.path.join(_LAYOUTMAPP, fil), encoding="utf-8") as f:
        return f.read()


# ==== 1. enheterna ========================================================

def test_en_langd_gar_inte_att_bygga_ur_ett_bart_tal():
    """TRASIG FIXTUR för enhetsskyddet. Måste falla."""
    with pytest.raises(L.Enhetsfel):
        L.Langd(1.2)


def test_millimeter_och_meter_ger_samma_langd():
    assert L.Langd.mm(1200).som_m == pytest.approx(1.2)
    assert L.Langd.m(1.2).som_mm == pytest.approx(1200.0)
    assert L.Langd.mm(1200) == L.Langd.m(1.2)


def test_langd_gar_inte_att_bygga_ur_nan_eller_oandlighet():
    for tal in (float("nan"), float("inf")):
        with pytest.raises(L.Enhetsfel):
            L.Langd.m(tal)


def test_krav_avvisar_ett_tal_men_slapper_igenom_en_langd():
    assert L.krav(L.Langd.mm(500), "prov").som_mm == 500.0
    with pytest.raises(L.Enhetsfel) as fel:
        L.krav(500, "prov")
    # Felet ska säga vad man skulle skrivit i stället, inte bara att det var fel.
    assert "Langd.mm" in str(fel.value)


def test_langd_gange_langd_ar_en_yta_och_avvisas_som_langd():
    with pytest.raises(L.Enhetsfel):
        L.Langd.m(2) * L.Langd.m(3)
    assert L.area_m2(L.Langd.m(2), L.Langd.m(3)) == pytest.approx(6.0)


def test_kvoten_mellan_tva_langder_ar_enhetslos():
    assert L.Langd.m(3) / L.Langd.m(1.5) == pytest.approx(2.0)
    assert (L.Langd.m(3) / 2).som_m == pytest.approx(1.5)


def test_en_vinkel_ar_inte_en_langd():
    with pytest.raises(L.Enhetsfel):
        L.krav_vinkel(L.Langd.m(90), "vridning")
    assert L.krav_vinkel(450.0, "vridning") == pytest.approx(90.0)


def test_konstruktorerna_kraver_langd_inte_tal():
    """Skyddet ska sitta i KONSTRUKTORERNA, inte bara i typen."""
    with pytest.raises(L.Enhetsfel):
        L.Objekt("x", 1.2, L.Langd.m(0.8), L.Langd.m(1.0))
    with pytest.raises(L.Enhetsfel):
        L.Hall("h", 20, L.Langd.m(10), L.Langd.m(6))


def test_vek3_lamnar_millimeter_i_den_form_set_transform_vill_ha():
    assert L.Vek3.mm(1200, 800, 144).som_mm_lista() == [1200.0, 800.0, 144.0]
    assert L.Vek3.m(1.2, 0.8, 0.144).som_mm_lista() == pytest.approx(
        [1200.0, 800.0, 144.0])


def test_varje_parameter_som_bar_en_vinkel_heter_grader():
    """En vinkel i radianer där grader väntades är samma sorts fälla som mm
    mot m. Disciplinen är mekanisk i stället för beskriven."""
    fel = []
    for fil in _MODULER:
        trad = ast.parse(_kalla(fil))
        for nod in ast.walk(trad):
            if not isinstance(nod, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for arg in list(nod.args.args) + list(nod.args.kwonlyargs):
                n = arg.arg
                if ("vinkel" in n or "vridning" in n) and not n.endswith("_grader"):
                    fel.append("%s:%s(%s)" % (fil, nod.name, n))
    assert not fel, "vinkelparametrar utan enhet i namnet: " + ", ".join(fel)


# ==== 2. rummet ===========================================================

def _hall(bredd=20.0, djup=12.0, hojd=6.0, zoner=(), pelare=()):
    return L.Hall("prov", L.Langd.m(bredd), L.Langd.m(djup), L.Langd.m(hojd),
                  zoner=zoner, pelare=pelare)


def _lada(namn, l=2.0, b=1.0, h=1.0, **kw):
    return L.Objekt(namn, L.Langd.m(l), L.Langd.m(b), L.Langd.m(h), **kw)


def test_hallen_lagger_in_sina_pelare_som_lasta_objekt():
    hall = _hall(pelare=[L.Pelare("p", L.Vek2.m(10, 6), L.Langd.mm(400),
                                  L.Langd.mm(400))])
    scen = L.Scen(hall)
    assert scen.namn() == ("pelare:p",)
    assert scen.fria_namn() == ()
    assert scen.ar_placerad("pelare:p")
    with pytest.raises(L.Layoutfel):
        scen.placera("pelare:p", L.Pose.meter(1, 1, 0, 0))


def test_ett_objekt_far_inte_heta_som_en_pelare():
    scen = L.Scen(_hall())
    with pytest.raises(L.Layoutfel):
        scen.lagg_till(_lada("pelare:p"))


def test_ett_for_hogt_objekt_avvisas_redan_vid_inlaggningen():
    scen = L.Scen(_hall(hojd=3.0))
    with pytest.raises(L.Layoutfel):
        scen.lagg_till(_lada("torn", h=4.0))


def test_en_otillaten_vridning_avvisas():
    scen = L.Scen(_hall())
    scen.lagg_till(_lada("a", tillatna_vridningar_grader=(0.0,)))
    with pytest.raises(L.Layoutfel):
        scen.placera("a", L.Pose.meter(5, 5, 0, 90))


def test_kroppen_vrids_kring_z_och_lador_blir_ratt_stora():
    scen = L.Scen(_hall())
    scen.lagg_till(_lada("a", l=3.0, b=1.0))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 90.0))
    lada = scen.kropp("a").aabb()
    assert lada.bredd_m == pytest.approx(1.0)
    assert lada.djup_m == pytest.approx(3.0)


def test_en_zon_som_ar_smalare_an_sitt_eget_breddkrav_avvisas():
    """En gång som inte går att uppfylla ens i en tom hall är ett fel i
    beskrivningen, inte ett resultat av en sökning."""
    zon = L.Zon("g", L.Zontyp.GANG,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(0),
                               L.Langd.m(10), L.Langd.m(1.0)),
                minsta_bredd=L.Langd.m(1.5))
    with pytest.raises(L.Layoutfel):
        _hall(zoner=[zon])


def test_fri_hojd_hor_inte_till_en_arbetsyta():
    """Två höjdmått i ett fält hade dolt felet i det vanliga fallet."""
    with pytest.raises(L.Layoutfel):
        L.Zon("a", L.Zontyp.ARBETSYTA,
              L.Rektangel.av(L.Langd.m(0), L.Langd.m(0), L.Langd.m(2),
                             L.Langd.m(2)),
              fri_hojd=L.Langd.m(2.0))


# ==== 3. kollisionen ======================================================

def _scen_med(*objekt):
    scen = L.Scen(_hall())
    for o in objekt:
        scen.lagg_till(o)
    return scen


def test_tva_lador_som_overlappar_rapporteras_med_par_djup_och_axel():
    """TRASIG FIXTUR för överlappsgrinden. Måste falla."""
    scen = _scen_med(_lada("a"), _lada("b"))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    scen.placera("b", L.Pose.meter(6.5, 5.0, 0.0, 0.0))   # 500 mm in i a
    dom = L.granska(scen)
    assert not dom.ok
    assert dom.antal_overlapp == 1
    o = dom.overlapp[0]
    assert {o.a, o.b} == {"a", "b"}
    assert o.typ == L.Overlapp.KROPP
    assert o.axel == "x"
    assert o.djup_m == pytest.approx(0.5)
    assert "500.0 mm" in o.text()


def test_beroring_kant_i_kant_ar_inte_overlapp():
    """Ett tätt palleteringsmönster får inte läsas som en kollision."""
    scen = _scen_med(_lada("a"), _lada("b"))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    scen.placera("b", L.Pose.meter(7.0, 5.0, 0.0, 0.0))   # exakt intill
    assert L.granska(scen).ok


def test_overlapp_i_z_rapporteras_i_z_nar_det_ar_kortaste_vagen_ut():
    scen = _scen_med(_lada("a", h=1.0), _lada("b", h=1.0))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    scen.placera("b", L.Pose.meter(5.0, 5.0, 0.9, 0.0))   # 100 mm ner i a
    o = L.granska(scen).overlapp[0]
    assert o.axel == "z"
    assert o.djup_m == pytest.approx(0.1)


def test_en_lada_pa_en_annan_ar_inte_en_kollision():
    scen = _scen_med(_lada("pall", h=0.144, barande=True), _lada("kolli", h=0.3))
    scen.placera("pall", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    scen.placera("kolli", L.Pose.meter(5.0, 5.0, 0.144, 0.0))
    assert L.granska(scen).ok


def test_underhallsutrymmet_kraver_den_storre_av_marginalerna():
    a = _lada("a", underhallsmarginal=L.Langd.m(0.8))
    b = _lada("b", underhallsmarginal=L.Langd.m(0.3))
    scen = _scen_med(a, b)
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    scen.placera("b", L.Pose.meter(7.7, 5.0, 0.0, 0.0))   # 700 mm luft
    dom = L.granska(scen)
    assert dom.antal_overlapp == 1
    assert dom.overlapp[0].typ == L.Overlapp.MARGINAL
    assert dom.overlapp[0].kravd_marginal_m == pytest.approx(0.8)
    # 800 mm luft räcker exakt, och exakt uppfyllt är uppfyllt.
    scen.ta_bort_placering("b")
    scen.placera("b", L.Pose.meter(7.8, 5.0, 0.0, 0.0))
    assert L.granska(scen).ok


def test_objekt_i_samma_enhet_kraver_inget_utrymme_av_varandra():
    a = _lada("a", underhallsmarginal=L.Langd.m(0.8), enhet="CELL")
    b = _lada("b", underhallsmarginal=L.Langd.m(0.8), enhet="CELL")
    scen = _scen_med(a, b)
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    scen.placera("b", L.Pose.meter(7.05, 5.0, 0.0, 0.0))  # 50 mm luft
    assert L.granska(scen).ok
    assert L.kravd_separation_m(scen.kropp("a"), scen.kropp("b")) == 0.0


def test_ett_objekt_som_sticker_ut_ur_hallen_fangas():
    """TRASIG FIXTUR för hallgränsen. Måste falla."""
    scen = _scen_med(_lada("a", l=2.0))
    scen.placera("a", L.Pose.meter(0.5, 5.0, 0.0, 0.0))
    dom = L.granska(scen)
    assert [u.vagg for u in dom.utanfor] == ["vaster"]
    assert dom.utanfor[0].overskott_m == pytest.approx(0.5)


def test_ett_objekt_i_ett_forbjudet_omrade_fangas():
    """TRASIG FIXTUR för zongrinden. Måste falla."""
    zon = L.Zon("bur", L.Zontyp.FORBJUDET,
                L.Rektangel.av(L.Langd.m(8), L.Langd.m(4),
                               L.Langd.m(12), L.Langd.m(8)))
    scen = L.Scen(_hall(zoner=[zon]))
    scen.lagg_till(_lada("a"))
    scen.placera("a", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    dom = L.granska(scen)
    assert len(dom.zonbrott) == 1
    assert dom.zonbrott[0].zon == "bur"
    assert dom.zonbrott[0].intrang_m2 == pytest.approx(2.0)


def test_en_transportor_over_en_utrymningsvag_ar_tillaten_om_den_gar_hogt():
    """Fri höjd är ett riktigt mått, inte en etikett: samma kropp fälls på
    2,0 m och släpps på 2,4 m."""
    zon = L.Zon("ut", L.Zontyp.UTRYMNINGSVAG,
                L.Rektangel.av(L.Langd.m(8), L.Langd.m(0),
                               L.Langd.m(10), L.Langd.m(12)),
                fri_hojd=L.Langd.m(2.2), minsta_bredd=L.Langd.m(1.2))
    scen = L.Scen(_hall(zoner=[zon]))
    scen.lagg_till(_lada("bana", l=6.0, b=0.6, h=0.4))
    scen.placera("bana", L.Pose.meter(9.0, 6.0, 2.0, 0.0))
    assert not L.granska(scen).ok
    scen.ta_bort_placering("bana")
    scen.placera("bana", L.Pose.meter(9.0, 6.0, 2.4, 0.0))
    assert L.granska(scen).ok


def test_en_gang_matas_pa_sin_fria_bredd_och_inte_pa_narvaro():
    """En bred gång tål ett skåp, en smal gör det inte. Grinden ska mäta
    bredden; en grind som bara ser närvaron mäter fel storhet."""
    zon = L.Zon("gang", L.Zontyp.GANG,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(5),
                               L.Langd.m(20), L.Langd.m(8)),
                fri_hojd=L.Langd.m(2.4), minsta_bredd=L.Langd.m(1.6))
    scen = L.Scen(_hall(zoner=[zon]))
    scen.lagg_till(_lada("skap", l=1.0, b=1.0, h=2.0))
    # 1,0 m in i en 3,0 m gång lämnar 2,0 m: tillåtet.
    scen.placera("skap", L.Pose.meter(10.0, 5.5, 0.0, 0.0))
    assert L.granska(scen).ok
    # 1,5 m in lämnar 1,5 m: för smalt.
    scen.ta_bort_placering("skap")
    scen.placera("skap", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    dom = L.granska(scen)
    assert len(dom.passagebrott) == 1
    p = dom.passagebrott[0]
    assert p.matt_bredd_m == pytest.approx(1.5)
    assert p.kravd_bredd_m == pytest.approx(1.6)
    assert p.hinder == ("skap",)


def test_fri_bredd_mater_den_storsta_luckan_inte_summan_av_dem():
    zon = L.Zon("gang", L.Zontyp.GANG,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(5),
                               L.Langd.m(20), L.Langd.m(8)),
                fri_hojd=L.Langd.m(2.4), minsta_bredd=L.Langd.m(1.0))
    scen = L.Scen(_hall(zoner=[zon]))
    scen.lagg_till(_lada("mitt", l=1.0, b=1.0, h=2.0))
    scen.placera("mitt", L.Pose.meter(10.0, 6.5, 0.0, 0.0))  # mitt i gången
    bredd, _vid, hinder = L.fri_bredd_m(scen, scen.hall.zon("gang"))
    # Två luckor om 1,0 m var. Största luckan är 1,0 m, inte summan 2,0 m.
    assert bredd == pytest.approx(1.0)
    assert hinder == ("mitt",)


def test_en_travers_over_halva_hallen_begransar_hojden_dar():
    """TRASIG FIXTUR för höjdgrinden. Måste falla på ena halvan och släppa
    igenom på den andra."""
    zon = L.Zon("travers", L.Zontyp.ARBETSYTA,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(0),
                               L.Langd.m(10), L.Langd.m(12)),
                takhojd=L.Langd.m(2.0))
    scen = L.Scen(_hall(zoner=[zon]))
    scen.lagg_till(_lada("press", l=1.4, b=1.2, h=2.2))
    scen.placera("press", L.Pose.meter(5.0, 6.0, 0.0, 0.0))
    dom = L.granska(scen)
    assert len(dom.hojdbrott) == 1
    assert "travers" in dom.hojdbrott[0].orsak
    scen.ta_bort_placering("press")
    scen.placera("press", L.Pose.meter(15.0, 6.0, 0.0, 0.0))
    assert L.granska(scen).ok


def test_kravd_fri_hojd_over_ett_objekt_raknas_med():
    scen = L.Scen(_hall(hojd=3.0))
    scen.lagg_till(_lada("robot", h=2.8, kravd_fri_hojd=L.Langd.m(0.5)))
    scen.placera("robot", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    dom = L.granska(scen)
    assert len(dom.hojdbrott) == 1
    assert dom.hojdbrott[0].kravd_fri_hojd_m == pytest.approx(0.5)


def test_ett_oplacerat_objekt_gor_granskningen_underkand():
    """Fail-closed: tystnad är inte ett godkännande."""
    scen = _scen_med(_lada("a"))
    dom = L.granska(scen)
    assert not dom.ok
    assert dom.oplacerade == ("a",)


def test_forhandskontrollen_andrar_inte_scenen():
    scen = _scen_med(_lada("a"), _lada("b"))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    svar = L.provplacera(scen, "b", L.Pose.meter(5.5, 5.0, 0.0, 0.0))
    assert not svar.fri
    assert svar.skal()
    assert not scen.ar_placerad("b")
    assert L.granska(scen).oplacerade == ("b",)


def test_forhandskontrollen_och_efterhandsgranskningen_ar_eniga():
    """Samma geometri ska ge samma dom oavsett vilken väg den frågas."""
    scen = _scen_med(_lada("a"), _lada("b"))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    for x in (5.5, 6.0, 7.0, 7.5, 9.0):
        pose = L.Pose.meter(x, 5.0, 0.0, 0.0)
        fore = L.provplacera(scen, "b", pose).fri
        scen.placera("b", pose)
        efter = L.granska(scen).ok
        scen.ta_bort_placering("b")
        assert fore == efter, "x=%.1f: förhand %s, efterhand %s" % (x, fore, efter)


def test_avstand_ar_en_undre_grans_och_exakt_for_axelriktade():
    scen = _scen_med(_lada("a"), _lada("b"))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    scen.placera("b", L.Pose.meter(8.0, 5.0, 0.0, 0.0))
    assert L.avstand_m(scen.kropp("a"), scen.kropp("b")) == pytest.approx(1.0)


def test_radie_langs_ar_halva_utstrackningen_i_en_riktning():
    scen = _scen_med(_lada("a", l=3.0, b=1.0,
                           tillatna_vridningar_grader=(45.0,)))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 45.0))
    kropp = scen.kropp("a")
    vantad = (1.5 + 0.5) * math.cos(math.radians(45.0))
    assert L.radie_langs(kropp, (1.0, 0.0)) == pytest.approx(vantad)


def test_tillganglig_hojd_ar_det_lagsta_taket_over_ladan():
    zon = L.Zon("t", L.Zontyp.ARBETSYTA,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(0), L.Langd.m(10),
                               L.Langd.m(12)),
                takhojd=L.Langd.m(2.5))
    scen = L.Scen(_hall(zoner=[zon]))
    hojd, orsak = L.tillganglig_hojd_m(
        scen, L.Rektangel.av(L.Langd.m(1), L.Langd.m(1), L.Langd.m(2),
                             L.Langd.m(2)))
    assert hojd == pytest.approx(2.5)
    assert "t" in orsak


# ==== 4. fria ytor ========================================================

def test_storsta_lediga_rektangel_ar_verkligen_ledig():
    scen = _scen_med(_lada("a", l=4.0, b=4.0, h=2.0))
    scen.placera("a", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    rekt = L.storsta_lediga_rektangel(scen, L.Langd.m(1.0))
    assert rekt is not None
    assert scen.hall.golv.omsluter(rekt)
    assert rekt.snitt(scen.kropp("a").aabb()) is None


def test_en_lag_ledig_yta_ser_inte_ett_hogt_hinder():
    """Höjdfiltret är ett riktigt filter: en travers på 4 m spärrar ingen
    golvyta för en pall på 0,15 m."""
    scen = _scen_med(_lada("hangande", l=6.0, b=6.0, h=1.0))
    scen.placera("hangande", L.Pose.meter(10.0, 6.0, 4.0, 0.0))
    lag = L.ledig_area_m2(scen, L.Langd.m(0.15))
    hog = L.ledig_area_m2(scen, L.Langd.m(5.0))
    assert lag == pytest.approx(scen.hall.golv.area_m2, abs=0.5)
    assert hog < lag - 30.0


def test_far_plats_ger_ett_lage_som_haller_for_den_exakta_kontrollen():
    scen = _scen_med(_lada("stor", l=18.0, b=10.0, h=1.0),
                     _lada("pall", l=1.2, b=0.8, h=0.144))
    scen.placera("stor", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    pose = L.far_plats(scen, "pall")
    assert pose is not None
    assert L.provplacera(scen, "pall", pose).fri


def test_far_plats_sager_nej_nar_det_inte_finns_plats():
    """Fail-closed: hellre ett nej än en gissning."""
    scen = _scen_med(_lada("stor", l=19.9, b=11.9, h=1.0),
                     _lada("pall", l=1.2, b=0.8, h=0.144))
    scen.placera("stor", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    assert L.far_plats(scen, "pall") is None


def test_far_plats_avvisar_ett_objekt_som_redan_star_nagonstans():
    scen = _scen_med(_lada("a"))
    scen.placera("a", L.Pose.meter(5.0, 5.0, 0.0, 0.0))
    with pytest.raises(L.Layoutfel):
        L.far_plats(scen, "a")


def test_rasterkartan_ar_konservativ_mot_ett_snett_hinder():
    """En vriden kropp räknas genom sin omslutande låda, alltså större än den
    är. Den lediga ytan ska därför bli mindre, aldrig större."""
    scen = _scen_med(_lada("a", l=4.0, b=1.0, h=1.0,
                           tillatna_vridningar_grader=(0.0, 45.0)))
    scen.placera("a", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    rakt = L.ledig_area_m2(scen, L.Langd.m(1.0))
    scen.ta_bort_placering("a")
    scen.placera("a", L.Pose.meter(10.0, 6.0, 0.0, 45.0))
    snett = L.ledig_area_m2(scen, L.Langd.m(1.0))
    assert snett < rakt


def test_rasterkartan_grovnar_hellre_an_att_svalla_over_taket():
    scen = L.Scen(_hall(bredd=200.0, djup=200.0))
    karta = L.Rasterkarta(scen, 1.0, raster_m=L.Langd.mm(10))
    assert karta.nx * karta.ny <= L.fria_ytor.MAX_CELLER
    assert karta.grovnad > 1.0


# ==== 5. utdata mot VC ====================================================

def _scen_for_utdata(ankare):
    scen = L.Scen(_hall())
    scen.lagg_till(L.Objekt("band", L.Langd.m(3.0), L.Langd.m(0.6),
                            L.Langd.m(0.9), ankare=ankare))
    scen.placera("band", L.Pose.meter(4.0, 2.0, 0.0, 90.0))
    return scen


def test_ett_antaget_ankare_ger_inget_anrop_som_forval():
    """TRASIG FIXTUR för ankargrinden. Måste falla.

    Ett antagande om var komponentens origo sitter flyttar komponenten fel,
    tyst, i en riktig scen. Fail-closed.
    """
    scen = _scen_for_utdata(L.Ankare.antagen_mitt_golv())
    with pytest.raises(L.Ankarfel) as fel:
        L.till_verktygsanrop(scen)
    assert "get_bounds" in str(fel.value)
    # Och med uttryckligt val går det, för prov utan VC.
    assert len(L.till_verktygsanrop(scen, strikt=False)) == 1


def test_ett_matt_ankare_raknar_om_origo_ratt():
    """get_bounds ger lådans mitt och halva utsträckning i nodens EGEN ram.
    Handräknat: fotavtryckets mitt vid underkanten ligger 1500 mm framför
    origo, och vid 90 graders vridning hamnar origo 1500 mm söder om målet."""
    ankare = L.Ankare.ur_bounds([1500.0, 0.0, 450.0], [1500.0, 300.0, 450.0])
    anrop = L.till_verktygsanrop(_scen_for_utdata(ankare))
    assert len(anrop) == 1
    a = anrop[0].som_dict()
    assert a["verktyg"] == "set_transform"
    assert a["argument"]["component"] == "band"
    assert a["argument"]["position"] == pytest.approx([4000.0, 500.0, 0.0])
    # Vridningen kring Z hör i det TREDJE talet: W kring X, P kring Y, R kring Z.
    assert a["argument"]["wpr"] == pytest.approx([0.0, 0.0, 90.0])


def test_anropen_haller_det_riktiga_verktygsschemat():
    """Formen prövas mot REGISTRET, inte mot en kopia av schemat här."""
    ankare = L.Ankare.ur_bounds([0.0, 0.0, 450.0], [1500.0, 300.0, 450.0])
    anrop = L.till_verktygsanrop(_scen_for_utdata(ankare))
    kompletta = L.validera_mot_registret(anrop)
    assert kompletta[0]["component"] == "band"


def test_ett_anrop_med_fel_form_avvisas_av_registret():
    """TRASIG FIXTUR för schemaprovet. Måste falla."""
    from vc_assist_svc.verktyg import Argumentfel
    fel_anrop = (L.Anrop("set_transform", {"komponent": "band"}, "band"),)
    with pytest.raises(Argumentfel):
        L.validera_mot_registret(fel_anrop)


def test_ett_okant_verktyg_avvisas():
    with pytest.raises(L.Layoutfel):
        L.validera_mot_registret((L.Anrop("flytta_grejen", {}, "band"),))


def test_hallens_pelare_blir_inga_verktygsanrop():
    """Pelarna är byggnaden, inte komponenter i layouten."""
    hall = _hall(pelare=[L.Pelare("p", L.Vek2.m(10, 6), L.Langd.mm(400),
                                  L.Langd.mm(400))])
    scen = L.Scen(hall)
    assert L.till_verktygsanrop(scen) == ()


def test_komponentnamn_kan_mappas_om():
    ankare = L.Ankare.ur_bounds([0.0, 0.0, 450.0], [1500.0, 300.0, 450.0])
    scen = _scen_for_utdata(ankare)
    anrop = L.till_verktygsanrop(scen, komponentnamn={"band": "Belt Conveyor"})
    assert anrop[0].argument["component"] == "Belt Conveyor"


# ==== 6. linters på motorns egen källa ====================================

_KONSTANT = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)\s*(#.*)?$")
_HARKOMST = ("MÄTT", "MATT", "ANTAG", "STANDARDMATT", "PUBLICERAD", "SI-",
             "BANK")


def _konstanter(fil):
    ut = []
    rader = _kalla(fil).split("\n")
    for nr, rad in enumerate(rader, 1):
        m = _KONSTANT.match(rad.rstrip())
        if not m:
            continue
        # Härkomsten får stå på raden eller i kommentarsblocket ovanför.
        sammanhang = [m.group(3) or ""]
        i = nr - 2
        while i >= 0 and rader[i].lstrip().startswith("#"):
            sammanhang.append(rader[i])
            i -= 1
        ut.append((nr, m.group(1), " ".join(sammanhang)))
    return ut


@pytest.mark.parametrize("fil", _MODULER)
def test_varje_troskel_i_motorn_namner_vad_som_satte_den(fil):
    """Samma regel som ögat lyder under: ett tal utan härkomst är ett
    linterfel (docs/spec/96_ingen_skuld.md S6)."""
    utan = []
    for nr, namn, sammanhang in _konstanter(fil):
        if not any(o in sammanhang.upper() for o in _HARKOMST):
            utan.append("%s:%d %s" % (fil, nr, namn))
    assert not utan, "trösklar utan härkomst:\n  " + "\n  ".join(utan)


def test_lintern_hittar_nagot_att_prova():
    """En grind som inte har någon indata mäter ingenting."""
    antal = sum(len(_konstanter(f)) for f in _MODULER)
    assert antal >= 10, "hittade bara %d konstanter att pröva" % antal


def test_ett_antaget_ankare_ar_inte_en_troskel_utan_harkomst():
    """TRASIG FIXTUR för härkomstlintern. En konstant utan kommentar MÅSTE
    fällas, annars provar lintern ingenting."""
    utan_harkomst = "TROSKEL_UTAN_URSPRUNG = 42\n"
    rader = utan_harkomst.split("\n")
    m = _KONSTANT.match(rader[0])
    assert m is not None
    assert not any(o in (m.group(3) or "").upper() for o in _HARKOMST)


@pytest.mark.parametrize("fil", _MODULER)
def test_ingen_bar_todo_och_inget_tyst_undantag(fil):
    """S8 och S9 i docs/spec/96_ingen_skuld.md."""
    kalla = _kalla(fil)
    bara_todo = [rad for rad in kalla.split("\n")
                 if "TODO" in rad and not re.search(r"TODO\(\d{4}-\d{2}-\d{2}", rad)]
    assert not bara_todo, "bar TODO i %s: %r" % (fil, bara_todo[:2])
    trad = ast.parse(kalla)
    for nod in ast.walk(trad):
        if not isinstance(nod, ast.ExceptHandler):
            continue
        # Ett undantag måste antingen kastas vidare, ge ett eget fel, eller
        # svara med ett värde som bäraren kan se. Ett tyst pass är förbjudet.
        assert not all(isinstance(k, ast.Pass) for k in nod.body), (
            "tyst except i %s rad %d" % (fil, nod.lineno))


def test_varje_publikt_namn_har_en_konsument():
    """S3: ingen kod utan konsument. Varje namn i ett moduls __all__ ska
    användas någon annanstans i paketet eller prövas i testerna."""
    import importlib

    testkalla = ""
    for fil in ("test_layout.py", "test_layout_placering.py"):
        stig = os.path.join(_ROT, "tests", "enhet", fil)
        if os.path.exists(stig):
            with io.open(stig, encoding="utf-8") as f:
                testkalla += f.read()
    foraldralosa = []
    for fil in _MODULER:
        if fil == "__init__.py":
            continue
        modul = importlib.import_module(
            "vc_assist_svc.layout." + fil[:-3])
        annan = testkalla + "".join(_kalla(f) for f in _MODULER if f != fil)
        for namn in getattr(modul, "__all__", ()):
            if not re.search(r"\b%s\b" % re.escape(namn), annan):
                foraldralosa.append("%s.%s" % (fil, namn))
    assert not foraldralosa, ("publika namn utan konsument:\n  "
                              + "\n  ".join(foraldralosa))
