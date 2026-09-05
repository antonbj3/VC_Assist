# -*- coding: utf-8 -*-
"""L1/L2 för placeringsspråket och lösaren, plus mätningen över bänken.

Tre lager:

1. RELATIONERNA, en i taget, på handräknade fall. Varje relation prövas både
   som DOM (``prova``) och som FÖRSLAG (``forslag_for``), och den tredje
   utgången - obestämbar, alltså "går inte att pröva ännu" - prövas också.
   En relation som svarar ja när den inte kan veta är den farligaste sorten.
2. LÖSAREN: determinism, de fyra svaren, och att den aldrig säger LOST om
   den oberoende granskningen har något att anmärka.
3. MÄTNINGEN över 24 provscener byggda ur bank/uppgifter och
   bank/katalog_index.json, med verkliga mått. Talen står i testet, så en
   försämring blir ett testfel och inte en formulering i en rapport.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import layout as L                       # noqa: E402
from vc_assist_svc.layout import provscener as P            # noqa: E402


# ==== fixturer ============================================================

def _hall(bredd=20.0, djup=12.0, hojd=6.0, zoner=(), pelare=()):
    return L.Hall("prov", L.Langd.m(bredd), L.Langd.m(djup), L.Langd.m(hojd),
                  zoner=zoner, pelare=pelare)


def _scen(*objekt, **kw):
    scen = L.Scen(_hall(**kw))
    for o in objekt:
        scen.lagg_till(o)
    return scen


def _lada(namn, l=2.0, b=1.0, h=1.0, **kw):
    kw.setdefault("tillatna_vridningar_grader", (0.0,))
    return L.Objekt(namn, L.Langd.m(l), L.Langd.m(b), L.Langd.m(h), **kw)


# ==== 1. relationerna =====================================================

def test_en_relation_som_inte_kan_provas_svarar_obestambar_inte_ja():
    """Fail-closed. En obestämbar relation är INTE uppfylld."""
    scen = _scen(_lada("a"), _lada("b"))
    utfall = L.Framfor("b", "a", avstand=L.Langd.m(1.0)).prova(scen)
    assert not utfall.provbar
    assert not utfall.ok


def test_en_relation_mot_ett_okant_namn_ar_ett_hart_fel():
    """Ett uppfunnet objektnamn är ett hårt fel, inte en varning."""
    scen = _scen(_lada("a"))
    with pytest.raises(L.Layoutfel):
        L.Framfor("b", "a").prova(scen)
    with pytest.raises(L.Layoutfel):
        L.losa(scen, [L.Framfor("b", "a")])


def test_framfor_mater_mot_referensens_framsida_inte_mot_vaderstrecket():
    """Konventionen: framsidan pekar mot +X vid vridning 0. Vrids referensen
    90 grader ska "framför" följa med, annars håller inte språket."""
    scen = _scen(_lada("ref", l=2.0, b=1.0,
                       tillatna_vridningar_grader=(0.0, 90.0)),
                 _lada("mal", l=1.0, b=1.0))
    rel = L.Framfor("mal", "ref", avstand=L.Langd.m(1.0))
    scen.placera("ref", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    assert rel.forslag_for(scen, "mal")[0].x_m == pytest.approx(12.5)
    scen.ta_bort_placering("ref")
    scen.placera("ref", L.Pose.meter(10.0, 6.0, 0.0, 90.0))
    forslag = rel.forslag_for(scen, "mal")[0]
    assert forslag.x_m == pytest.approx(10.0)
    assert forslag.y_m == pytest.approx(8.5)


def test_de_fyra_sidorna_pekar_at_var_sitt_hall():
    scen = _scen(_lada("ref", l=2.0, b=1.0), _lada("mal", l=1.0, b=1.0))
    scen.placera("ref", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    lagen = {}
    for klass in (L.Framfor, L.Bakom, L.TillVanster, L.TillHoger):
        rel = klass("mal", "ref", avstand=L.Langd.m(1.0))
        p = rel.forslag_for(scen, "mal")[0]
        lagen[klass.__name__] = (round(p.x_m, 3), round(p.y_m, 3))
    assert lagen["Framfor"] == (12.5, 6.0)
    assert lagen["Bakom"] == (7.5, 6.0)
    assert lagen["TillVanster"] == (10.0, 8.0)
    assert lagen["TillHoger"] == (10.0, 4.0)


def test_bredvid_utan_angivet_mellanrum_har_ett_tak():
    scen = _scen(_lada("ref"), _lada("mal", l=1.0, b=1.0))
    scen.placera("ref", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    rel = L.Bredvid("mal", "ref")
    scen.placera("mal", L.Pose.meter(10.0, 7.1, 0.0, 0.0))   # 100 mm luft
    assert rel.prova(scen).ok
    scen.ta_bort_placering("mal")
    # Längre bort än taket: då är det inte "bredvid" längre.
    scen.placera("mal", L.Pose.meter(10.0, 8.6, 0.0, 0.0))
    utfall = rel.prova(scen)
    assert not utfall.ok and utfall.provbar
    assert "%.0f" % (L.BREDVID_MAX_M * 1000.0) in utfall.text


def test_bredvid_kraver_att_objekten_star_mitt_for_varandra():
    """Ett objekt snett bakom är inte bredvid, hur nära det än står."""
    scen = _scen(_lada("ref", l=2.0, b=1.0), _lada("mal", l=1.0, b=1.0))
    scen.placera("ref", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    scen.placera("mal", L.Pose.meter(13.0, 7.1, 0.0, 0.0))
    assert not L.Bredvid("mal", "ref").prova(scen).ok


def test_mot_vaggen_mater_mot_ratt_vagg():
    scen = _scen(_lada("a", l=2.0, b=1.0))
    rel = L.MotVagg("a", L.Vagg.VASTER, marginal=L.Langd.mm(500))
    scen.placera("a", L.Pose.meter(1.5, 6.0, 0.0, 0.0))
    assert rel.prova(scen).ok
    scen.ta_bort_placering("a")
    scen.placera("a", L.Pose.meter(3.0, 6.0, 0.0, 0.0))
    assert not rel.prova(scen).ok


def test_i_hornet_ar_mot_bada_vaggarna_samtidigt():
    scen = _scen(_lada("a", l=2.0, b=1.0))
    rel = L.IHorn("a", L.Horn.NORDOST)
    pose = rel.forslag_for(scen, "a")[0]
    assert pose.x_m == pytest.approx(19.0)
    assert pose.y_m == pytest.approx(11.5)
    scen.placera("a", pose)
    assert rel.prova(scen).ok
    scen.ta_bort_placering("a")
    scen.placera("a", L.Pose.meter(19.0, 6.0, 0.0, 0.0))  # rätt vägg, fel hörn
    utfall = rel.prova(scen)
    assert not utfall.ok
    assert "norr" in utfall.text


def test_pa_kraver_barande_underlag():
    scen = _scen(_lada("pall", barande=False), _lada("kolli", l=0.4, b=0.3,
                                                     h=0.3))
    scen.placera("pall", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    with pytest.raises(L.Layoutfel) as fel:
        L.Pa("kolli", "pall").prova(scen)
    assert "barande" in str(fel.value)


def test_pa_lagger_underkanten_pa_underlagets_overkant_och_forbjuder_overhang():
    pall = _lada("pall", l=1.2, b=0.8, h=0.144, barande=True)
    kolli = _lada("kolli", l=0.4, b=0.3, h=0.147)
    scen = _scen(pall, kolli)
    scen.placera("pall", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    rel = L.Pa("kolli", "pall")
    forslag = rel.forslag_for(scen, "kolli")
    assert forslag[0].z_m == pytest.approx(0.144)
    # Mitt på först, sedan de fyra hörnen kant i kant.
    assert (round(forslag[1].x_m, 3), round(forslag[1].y_m, 3)) == (9.6, 5.75)
    scen.placera("kolli", forslag[0])
    assert rel.prova(scen).ok
    scen.ta_bort_placering("kolli")
    scen.placera("kolli", L.Pose.meter(10.5, 6.0, 0.144, 0.0))  # hänger ut
    utfall = rel.prova(scen)
    assert not utfall.ok
    assert "hänger ut" in utfall.text


def test_under_kraver_att_objektet_faktiskt_ligger_i_skuggan():
    tak = _lada("hylla", l=2.0, b=2.0, h=0.2, barande=True)
    lada = _lada("back", l=0.6, b=0.4, h=0.4)
    scen = _scen(tak, lada)
    scen.placera("hylla", L.Pose.meter(10.0, 6.0, 1.0, 0.0))
    rel = L.Under("back", "hylla")
    scen.placera("back", rel.forslag_for(scen, "back")[0])
    assert rel.prova(scen).ok
    scen.ta_bort_placering("back")
    scen.placera("back", L.Pose.meter(15.0, 6.0, 0.0, 0.0))
    assert not rel.prova(scen).ok


def test_centrerad_i_hallen_och_i_en_zon():
    zon = L.Zon("yta", L.Zontyp.ARBETSYTA,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(0), L.Langd.m(4),
                               L.Langd.m(4)))
    scen = _scen(_lada("a", l=1.0, b=1.0), zoner=[zon])
    assert L.CentreradI("a").forslag_for(scen, "a")[0].x_m == pytest.approx(10.0)
    assert L.CentreradI("a", "yta").forslag_for(scen, "a")[0].x_m == pytest.approx(2.0)


def test_i_zon_kraver_hela_fotavtrycket_inne():
    zon = L.Zon("yta", L.Zontyp.ARBETSYTA,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(0), L.Langd.m(4),
                               L.Langd.m(4)))
    scen = _scen(_lada("a", l=2.0, b=1.0), zoner=[zon])
    rel = L.IZon("a", "yta")
    scen.placera("a", L.Pose.meter(2.0, 2.0, 0.0, 0.0))
    assert rel.prova(scen).ok
    scen.ta_bort_placering("a")
    scen.placera("a", L.Pose.meter(3.5, 2.0, 0.0, 0.0))
    assert not rel.prova(scen).ok


def test_utanfor_zon_ar_ett_filter_utan_forslag():
    zon = L.Zon("bur", L.Zontyp.ARBETSYTA,
                L.Rektangel.av(L.Langd.m(0), L.Langd.m(0), L.Langd.m(4),
                               L.Langd.m(4)))
    scen = _scen(_lada("a"), zoner=[zon])
    rel = L.UtanforZon("a", "bur")
    assert rel.positionerar() == ()
    assert rel.forslag_for(scen, "a") is None
    scen.placera("a", L.Pose.meter(2.0, 2.0, 0.0, 0.0))
    assert not rel.prova(scen).ok


def test_i_rad_mater_mellanrum_och_att_raden_ar_rak():
    scen = _scen(_lada("a", l=1.0, b=1.0), _lada("b", l=1.0, b=1.0),
                 _lada("c", l=1.0, b=1.0))
    rel = L.IRad(("a", "b", "c"), L.Riktning.OSTER, L.Langd.m(0.5))
    scen.placera("a", L.Pose.meter(5.0, 6.0, 0.0, 0.0))
    scen.placera("b", rel.forslag_for(scen, "b")[0])
    assert scen.pose("b").x_m == pytest.approx(6.5)
    scen.placera("c", rel.forslag_for(scen, "c")[0])
    assert scen.pose("c").x_m == pytest.approx(8.0)
    assert rel.prova(scen).ok
    # Ett steg vid sidan av linjen fäller raden.
    scen.ta_bort_placering("c")
    scen.placera("c", L.Pose.meter(8.0, 6.3, 0.0, 0.0))
    utfall = rel.prova(scen)
    assert not utfall.ok
    assert "vid sidan" in utfall.text


def test_en_rad_behover_minst_tva_objekt():
    with pytest.raises(L.Layoutfel):
        L.IRad(("a",), L.Riktning.OSTER, L.Langd.m(1.0))


def test_mellanrum_och_minsta_avstand_ar_olika_krav():
    scen = _scen(_lada("a"), _lada("b"))
    scen.placera("a", L.Pose.meter(5.0, 6.0, 0.0, 0.0))
    scen.placera("b", L.Pose.meter(9.0, 6.0, 0.0, 0.0))    # 2,0 m luft
    assert L.Mellanrum("a", "b", L.Langd.m(2.0)).prova(scen).ok
    assert not L.Mellanrum("a", "b", L.Langd.m(1.0)).prova(scen).ok
    assert L.MinstaAvstand("a", "b", L.Langd.m(1.0)).prova(scen).ok
    assert not L.MinstaAvstand("a", "b", L.Langd.m(3.0)).prova(scen).ok


def test_inom_rackvidd_helt_ar_hardare_an_delvis():
    robot = _lada("robot", l=0.5, b=0.5, h=1.5, rackvidd=L.Langd.mm(900))
    pall = _lada("pall", l=1.2, b=0.8, h=0.144)
    scen = _scen(robot, pall)
    scen.placera("robot", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    scen.placera("pall", L.Pose.meter(11.0, 6.0, 0.0, 0.0))
    assert L.InomRackvidd("pall", "robot", helt=False).prova(scen).ok
    assert not L.InomRackvidd("pall", "robot", helt=True).prova(scen).ok


def test_inom_rackvidd_gissar_aldrig_en_rackvidd():
    """En robot utan publicerad räckvidd ska ge ett fel, inte ett antagande."""
    robot = _lada("robot", l=0.5, b=0.5, h=1.5)
    scen = _scen(robot, _lada("pall"))
    scen.placera("robot", L.Pose.meter(10.0, 6.0, 0.0, 0.0))
    scen.placera("pall", L.Pose.meter(11.0, 6.0, 0.0, 0.0))
    with pytest.raises(L.Layoutfel) as fel:
        L.InomRackvidd("pall", "robot").prova(scen)
    assert "guess" in str(fel.value)


def test_fast_lage_ar_den_enda_relation_som_bar_en_koordinat():
    scen = _scen(_lada("a"))
    rel = L.FastLage("a", L.Vek2.m(3.0, 4.0))
    pose = rel.forslag_for(scen, "a")[0]
    assert (pose.x_m, pose.y_m) == (3.0, 4.0)
    scen.placera("a", pose)
    assert rel.prova(scen).ok
    scen.ta_bort_placering("a")
    scen.placera("a", L.Pose.meter(3.1, 4.0, 0.0, 0.0))
    assert not rel.prova(scen).ok


def test_varje_relation_i_spraket_har_en_kod_och_en_text():
    """Rapporten namnger relationen. En kod som saknas gör svaret oläsbart."""
    scen = _scen(_lada("a"), _lada("b", barande=True))
    exempel = [
        L.FastLage("a", L.Vek2.m(1, 1)), L.Bredvid("a", "b"),
        L.Framfor("a", "b"), L.Bakom("a", "b"), L.TillVanster("a", "b"),
        L.TillHoger("a", "b"), L.MotVagg("a", L.Vagg.NORR),
        L.IHorn("a", L.Horn.SYDOST), L.Pa("a", "b"), L.Under("a", "b"),
        L.CentreradI("a"), L.IRad(("a", "b"), L.Riktning.NORR, L.Langd.m(1)),
        L.Mellanrum("a", "b", L.Langd.m(1)),
        L.MinstaAvstand("a", "b", L.Langd.m(1)),
    ]
    for rel in exempel:
        assert isinstance(rel, L.Relation)
        assert rel.kod and rel.kod != "RELATION", rel
        assert rel.text()
        assert set(rel.berorda()) <= {"a", "b"}
        assert not rel.prova(scen).provbar   # inget är placerat ännu


def test_sida_och_riktning_ar_uppraknade_och_inte_strangar():
    assert set(L.Sida) == {L.Sida.FRAM, L.Sida.BAK, L.Sida.VANSTER,
                           L.Sida.HOGER}
    assert L.Riktning.OSTER.value == (1.0, 0.0)
    assert L.Utfall.uppfylld("x").ok


# ==== 2. lösaren ==========================================================

def _enkel_cell():
    scen = _scen(_lada("robot", l=0.5, b=0.5, h=1.5, rackvidd=L.Langd.mm(1650),
                       tillatna_vridningar_grader=(0.0,)),
                 _lada("band", l=3.0, b=0.6, h=0.9),
                 _lada("pall", l=1.2, b=0.8, h=0.144))
    relationer = [L.CentreradI("robot"),
                  L.Framfor("band", "robot", avstand=L.Langd.m(1.0)),
                  L.InomRackvidd("pall", "robot", helt=False)]
    return scen, relationer


def test_losaren_placerar_allt_och_granskar_sig_sjalv():
    scen, relationer = _enkel_cell()
    losning = L.losa(scen, relationer)
    assert losning.status is L.Status.LOST
    assert losning.ok
    assert set(losning.placeringar) == {"robot", "band", "pall"}
    # Domen kommer från den OBEROENDE granskningen, inte från sökningen.
    assert losning.granskning.ok
    assert losning.granskning.antal_overlapp == 0


def test_losaren_ar_deterministisk():
    """Samma indata ger samma utdata, alltid."""
    forsta = L.losa(*_enkel_cell()).placeringar
    for _ in range(3):
        igen = L.losa(*_enkel_cell()).placeringar
        assert {n: p.nyckel() for n, p in igen.items()} == \
               {n: p.nyckel() for n, p in forsta.items()}


def test_sparet_sager_vilken_relation_som_gav_varje_lage():
    scen, relationer = _enkel_cell()
    losning = L.losa(scen, relationer)
    kallor = {steg.namn: steg.kalla for steg in losning.spar}
    assert kallor["robot"] == "CENTRERAD_I"
    assert kallor["band"] == "FRAMFOR"
    assert kallor["pall"] == "INOM_RACKVIDD"
    assert any("PLACERING" in rad for rad in losning.rapport())


def test_ett_overbestamt_problem_namnger_vilka_relationer_som_band():
    """TRASIG FIXTUR för lösaren. Måste falla, och falla med adress."""
    scen = _scen(_lada("pall", l=1.2, b=0.8, h=0.144))
    relationer = [L.IHorn("pall", L.Horn.SYDVAST), L.CentreradI("pall")]
    losning = L.losa(scen, relationer)
    assert losning.status is L.Status.OVERBESTAMD
    assert not losning.ok
    assert losning.placeringar == {}
    assert {r.kod for r in losning.konflikt} == {"I_HORN", "CENTRERAD_I"}
    assert "minimal" in losning.skal
    assert any("KONFLIKT" in rad for rad in losning.rapport())


def test_konfliktmangden_ar_minimal_den_oskyldiga_relationen_pekas_inte_ut():
    """Ett constraint som INTE deltar i konflikten får inte hamna i svaret."""
    scen = _scen(_lada("pall", l=1.2, b=0.8, h=0.144),
                 _lada("skap", l=1.0, b=1.0, h=2.0))
    oskyldig = L.MotVagg("skap", L.Vagg.NORR)
    relationer = [L.IHorn("pall", L.Horn.SYDVAST), oskyldig,
                  L.CentreradI("pall")]
    losning = L.losa(scen, relationer)
    assert losning.status is L.Status.OVERBESTAMD
    assert oskyldig not in losning.konflikt
    assert len(losning.konflikt) == 2


def test_nagot_som_inte_ryms_i_hallen_far_ett_eget_svar():
    """"Ryms inte" och "överbestämt" är olika saker och ska inte blandas."""
    scen = _scen(_lada("a", l=1.2, b=0.8, h=0.2),
                 _lada("b", l=1.2, b=0.8, h=0.2),
                 _lada("c", l=1.2, b=0.8, h=0.2),
                 bredd=2.5, djup=1.0)
    losning = L.losa(scen, [])
    assert losning.status is L.Status.RYMS_INTE
    assert "m2" in losning.skal


def test_en_slut_budget_ger_obestambart_och_aldrig_ett_ja():
    """Fail-closed: kan lösaren inte garantera att en placering är fri ska
    den säga nej, inte gissa."""
    scen, relationer = _enkel_cell()
    losning = L.losa(scen, relationer, budget=1)
    assert losning.status is L.Status.OBESTAMBART
    assert not losning.ok
    assert "budget" in losning.skal


def test_losaren_lamnar_underhallsutrymme_runt_maskiner():
    scen = _scen(_lada("maskin_a", l=2.0, b=2.0, h=2.0,
                       underhallsmarginal=L.Langd.m(1.0)),
                 _lada("maskin_b", l=2.0, b=2.0, h=2.0,
                       underhallsmarginal=L.Langd.m(1.0)))
    losning = L.losa(scen, [L.CentreradI("maskin_a"),
                            L.Bredvid("maskin_b", "maskin_a")])
    assert losning.status is L.Status.LOST
    # losa rör aldrig scenen den fick; svaret bär sin egen scen.
    assert not scen.ar_placerad("maskin_a")
    a = losning.scen.kropp("maskin_a")
    b = losning.scen.kropp("maskin_b")
    assert L.avstand_m(a, b) >= 1.0 - 1e-6


def test_losaren_respekterar_passagematt():
    """Samma scen, två gångbredder: den smala ska fällas och den breda inte."""
    def bygg(minsta_bredd_m):
        zon = L.Zon("gang", L.Zontyp.GANG,
                    L.Rektangel.av(L.Langd.m(0), L.Langd.m(5),
                                   L.Langd.m(20), L.Langd.m(7)),
                    fri_hojd=L.Langd.m(2.4),
                    minsta_bredd=L.Langd.m(minsta_bredd_m))
        scen = _scen(_lada("skap", l=1.0, b=1.2, h=2.0), zoner=[zon])
        return scen, [L.IZon("skap", "gang")]

    assert L.losa(*bygg(0.5)).status is L.Status.LOST
    assert L.losa(*bygg(1.6)).status is L.Status.OVERBESTAMD


def test_losaren_respekterar_fri_hojd():
    """Traversen ligger över halva hallen. Kravet att pressen ska stå mitt i
    hallen hamnar under den, och det är ett annat fel än att den inte ryms."""
    def bygg(takhojd_m):
        zon = L.Zon("under", L.Zontyp.ARBETSYTA,
                    L.Rektangel.av(L.Langd.m(0), L.Langd.m(0),
                                   L.Langd.m(12), L.Langd.m(12)),
                    takhojd=L.Langd.m(takhojd_m))
        scen = _scen(_lada("press", l=1.4, b=1.2, h=2.2), zoner=[zon])
        return scen, [L.CentreradI("press")]

    assert L.losa(*bygg(3.0)).status is L.Status.LOST
    lag = L.losa(*bygg(2.0))
    assert lag.status is L.Status.OVERBESTAMD
    assert [r.kod for r in lag.konflikt] == ["CENTRERAD_I"]


def test_ett_redan_placerat_objekt_star_kvar():
    scen, relationer = _enkel_cell()
    scen.placera("robot", L.Pose.meter(6.0, 4.0, 0.0, 0.0))
    losning = L.losa(scen, [r for r in relationer
                            if not isinstance(r, L.CentreradI)])
    assert losning.status is L.Status.LOST
    assert losning.placeringar["robot"].nyckel()[:2] == (6.0, 4.0)


def test_lasta_pelare_ar_hinder_som_losaren_maste_gora_om_for():
    hall = _hall(bredd=6.0, djup=6.0,
                 pelare=[L.Pelare("mitt", L.Vek2.m(3.0, 3.0), L.Langd.m(1.0),
                                  L.Langd.m(1.0))])
    scen = L.Scen(hall)
    scen.lagg_till(_lada("a", l=2.0, b=2.0, h=1.0))
    losning = L.losa(scen, [L.CentreradI("a")])
    # Centrerad i hallen är precis där pelaren står.
    assert losning.status is L.Status.OVERBESTAMD
    assert [r.kod for r in losning.konflikt] == ["CENTRERAD_I"]


def test_losningen_gar_att_skriva_som_verktygsanrop():
    scen, relationer = _enkel_cell()
    losning = L.losa(scen, relationer)
    anrop = L.till_verktygsanrop(losning.scen, strikt=False)
    assert [a.verktyg for a in anrop] == ["set_transform"] * 3
    L.validera_mot_registret(anrop)


# ==== 3. mätningen över bänken ===========================================

@pytest.fixture(scope="module")
def matning():
    return P.mat()


def test_provscenerna_bygger_pa_bankens_verkliga_matt():
    """Måtten läses ur banken. En avskrift här hade kunnat drifta."""
    kat = P.katalog()
    pall = kat["bank://last/eur_pall"]
    assert (pall["l_mm"], pall["b_mm"], pall["h_mm"]) == (1200, 800, 144)
    scen, _rel = P._l01(kat)
    assert scen.objekt("pall").langd == L.Langd.mm(1200)
    assert scen.objekt("pall").bredd == L.Langd.mm(800)
    assert scen.objekt("kolli_0").langd == L.Langd.mm(400)
    # Räckvidden kommer ur tillverkarens publicerade siffra i banken.
    assert scen.objekt("robot").rackvidd == L.Langd.mm(3150)


def test_provscenerna_kommer_ur_riktiga_bankuppgifter():
    ids = {p.uppgift_id for p in P.PROVSCENER}
    for task_id in ids:
        assert P.uppgift(task_id)["task_id"] == task_id
    assert len(P.PROVSCENER) >= 12
    assert len(ids) >= 12
    for prov in P.PROVSCENER:
        assert isinstance(prov, P.Provscen)
        assert prov.beskrivning and prov.id
        assert prov.vantat in (L.Status.LOST, L.Status.OVERBESTAMD,
                               L.Status.RYMS_INTE)


def test_antal_scener_och_hur_manga_som_loses(matning):
    assert matning["antal_scener"] == 24
    assert matning["vantade_losta"] == 18
    assert matning["losta_av_vantade"] == 18


def test_alla_overbestamda_upptacks_som_overbestamda(matning):
    assert matning["overbestamda_vantade"] == 5
    assert matning["overbestamda_upptackta"] == 5


def test_noll_falska_losta_och_noll_overlapp(matning):
    """Fas 5:s grind. Båda talen MÅSTE vara noll."""
    assert matning["falska_losta"] == 0
    assert matning["overlapp_totalt"] == 0


def test_varje_provscen_ger_sitt_facit(matning):
    fel = ["%s: vantat %s, fick %s" % (r["id"], r["vantat"], r["fick"])
           for r in matning["per_scen"] if not r["enligt_facit"]]
    assert not fel, "\n".join(fel)
    assert matning["enligt_facit"] == matning["antal_scener"]


def test_varje_lost_scen_ger_ett_verktygsanrop_per_komponent(matning):
    for r in matning["per_scen"]:
        if r["fick"] != "LOST":
            continue
        assert r["anrop"] > 0, r["id"]
    assert matning["anrop_totalt"] == 66


def test_budgeten_racker_med_marginal_till_den_dyraste_scenen(matning):
    """Tröskelns härkomst är den här mätningen och ingen gissning."""
    assert matning["dyraste_sokning_noder"] == 15912
    assert matning["dyraste_sokning_noder"] < L.NODBUDGET


def test_varje_lost_provscen_haller_for_en_oberoende_granskning():
    """Sökningen får aldrig vara sin egen domare (I11)."""
    kat = P.katalog()
    for prov in P.PROVSCENER:
        if prov.vantat is not L.Status.LOST:
            continue
        _scen_ut, losning = prov.kor(kat)
        assert losning.status is L.Status.LOST, prov.id
        assert L.granska(losning.scen).ok, prov.id


def test_provscenerna_ar_deterministiska():
    kat = P.katalog()
    for prov in P.PROVSCENER:
        _s1, forsta = prov.kor(kat)
        _s2, andra = prov.kor(kat)
        assert forsta.status is andra.status, prov.id
        assert ({n: p.nyckel() for n, p in forsta.placeringar.items()}
                == {n: p.nyckel() for n, p in andra.placeringar.items()}), prov.id
        assert ([r.kod for r in forsta.konflikt]
                == [r.kod for r in andra.konflikt]), prov.id


def test_rapporten_gar_att_lasa_och_bar_summeringen():
    text = P.rapport()
    assert "SUMMA falska losta 0" in text
    assert "SUMMA overlapp i losta layouter 0" in text
    assert "SUMMA enligt facit 24 av 24" in text
