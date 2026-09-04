# -*- coding: utf-8 -*-
"""L1 for bryggan mellan en RIKTIG komponent och layoutlosaren.

Fas 5 stangdes pa 18 layouter med noll kollisioner, och allt var lador. Det
har provet handlar om skillnaden. Tva av fixturerna ar med avsikt TRASIGA:

* en komponent vars matt SAKNAS - den ska ge ett fel med namn pa det som
  fattas, aldrig ett gissat ratblock
* en layout som ser mojlig ut med den GISSADE ladan och blir omojlig med den
  riktiga - grinden ar vardelos om den inte kan falla
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

# `attrapp_vcmx` ligger i samma mapp. pytest lagger den mappen i sokvagen
# sjalv, precis som test_oga_pa_djupet.py forlitar sig pa for
# test_ogonkoppling - ingen egen sys.path-andring behovs, och en sadan hade
# lagt hela provmappen i vagen for alla andra importer.
import attrapp_vcmx as A                                          # noqa: E402
from vc_assist_svc import komponentfil as K                       # noqa: E402
from vc_assist_svc.layout import komponent as KO                  # noqa: E402
from vc_assist_svc.layout import (Ankare, Hall, InomRackvidd, Langd,  # noqa: E402
                                  MinstaAvstand, Scen, Status, losa,
                                  till_verktygsanrop)


# ---------------------------------------------------------------------------
# fixturer
# ---------------------------------------------------------------------------

def robot(tmp_path, namn="IRB prov", rackvidd="2000", profil=None,
          nyttolast="150"):
    extra = {}
    if profil is not None:
        extra["envelopeprofile"] = A.text_envelope(profil)
    kropp = A.GRANSSNITT_MONTERING % {"namn": "Tool", "ram": "FlangeFrame",
                                      "mount": 1, "nod": "mountplate"}
    return A.skriv(tmp_path / (namn + ".vcmx"),
                   A.modelxml(Name=namn, Type="Robots", Manufacturer="ABB",
                              Reach=rackvidd, MaxPayload=nyttolast),
                   A.rsc(namn, kropp), extra)


def verktyg(tmp_path, namn="Grip"):
    kropp = A.GRANSSNITT_MONTERING % {"namn": "ToolMount", "ram": "BaseFrame",
                                      "mount": 0, "nod": "grip"}
    return A.skriv(tmp_path / (namn + ".vcmx"),
                   A.modelxml(Name=namn, Type="Robot Tools",
                              Manufacturer="Schunk"),
                   A.rsc(namn, kropp))


def band(tmp_path, namn="Band"):
    kropp = (A.GRANSSNITT_FLODE % {"namn": "InInterface", "ram": "Start",
                                   "faltnamn": "FlowIn", "port": 0}
             + A.GRANSSNITT_FLODE % {"namn": "OutInterface", "ram": "End",
                                     "faltnamn": "FlowOut", "port": 1})
    return A.skriv(tmp_path / (namn + ".vcmx"),
                   A.modelxml(Name=namn, Type="Conveyors", Manufacturer="A"),
                   A.rsc(namn, kropp))


def bounds(langd_mm, bredd_mm, hojd_mm):
    """Ett get_bounds-svar for en komponent vars origo star pa golvet i mitten."""
    return KO.Bounds([0.0, 0.0, hojd_mm / 2.0],
                     [langd_mm / 2.0, bredd_mm / 2.0, hojd_mm / 2.0])


# ---------------------------------------------------------------------------
# TRASIG FIXTUR 1: matten saknas
# ---------------------------------------------------------------------------

def test_utan_lada_fran_vc_VAGRAR_bryggan_bygga_ett_objekt(tmp_path):
    f = K.las(robot(tmp_path), djupt=True, geometri=True)
    with pytest.raises(KO.Saknasfel) as fel:
        KO.objekt_ur_komponent(f)
    text = str(fel.value)
    assert "get_bounds" in text, "felet ska saga VAR maattet finns"
    assert "IRB prov" in text, "felet ska saga VILKEN komponent det galler"


def test_saknade_matt_ar_en_LISTA_inte_tystnad(tmp_path):
    f = K.las(robot(tmp_path), djupt=True, geometri=True)
    saknas = KO.saknade_matt(f)
    assert any("omslutande volym" in s for s in saknas)


def test_listan_over_saknade_matt_kortas_men_sager_hur_mycket_den_kortade(tmp_path):
    """En lista pa hundra rader lases inte - den scrollas forbi. Men en lista
    som kortas utan att saga det har ljugit tyst (M-60:s regel)."""
    ramar = "".join(A.RAM_UTTRYCK % {"namn": "R%d" % i, "uttryck": "P%d" % i}
                    for i in range(12))
    sokvag = A.skriv(tmp_path / "manga.vcmx",
                     A.modelxml(Name="Manga", Type="Machines",
                                Manufacturer="A"),
                     A.rsc("Manga", ramar))
    rader = KO.saknade_matt(K.las(sokvag, djupt=True))
    ramrader = [r for r in rader if r.startswith("ramen ")]
    assert len(ramrader) == KO.MAX_RAMRADER
    assert any("och 7 ramar till utan lage, av 12" in r for r in rader)


def test_en_lada_med_noll_utstrackning_avvisas():
    with pytest.raises(KO.Saknasfel):
        KO.Bounds([0.0, 0.0, 0.0], [500.0, 0.0, 500.0])


def test_ett_get_bounds_svar_utan_falt_avvisas():
    with pytest.raises(KO.Saknasfel):
        KO.Bounds.ur_svar({"center": [0, 0, 0]})


# ---------------------------------------------------------------------------
# den vanliga vagen: med VC:s lada blir det ett riktigt objekt
# ---------------------------------------------------------------------------

def test_med_vc_ladan_far_objektet_riktiga_matt_och_ett_MATT_ankare(tmp_path):
    f = K.las(robot(tmp_path), djupt=True, geometri=True)
    o = KO.objekt_ur_komponent(f, bounds=bounds(1400.0, 1200.0, 1900.0))
    assert o.langd.som_mm == 1400.0
    assert o.bredd.som_mm == 1200.0
    assert o.hojd.som_mm == 1900.0
    assert o.ankare.stampel == Ankare.MATT
    assert o.kategori == "Robots", "kategorin ar komponentens egen"
    assert o.rackvidd.som_mm == 2000.0


def test_rackvidden_lases_ur_reach_nar_faltet_finns(tmp_path):
    f = K.las(robot(tmp_path, rackvidd="1650"), djupt=True, geometri=True)
    m = KO.rackvidd_ur_fakta(f)
    assert m.harkomst == K.Harkomst.LAST
    assert m.varde.som_mm == 1650.0


def test_rackvidden_harleds_ur_profilen_nar_reach_ar_noll(tmp_path):
    """225 robotar i biblioteket har Reach = 0 eller inget Reach alls men bar
    en rackviddsprofil (M-61). Halet gar att fylla, och det ska synas ATT det
    fylldes pa ett annat satt."""
    profil = [(0.0, 0.0, 870.0), (579.8, 0.0, 273.1), (0.0, 0.0, -112.0)]
    f = K.las(robot(tmp_path, rackvidd="0", profil=profil),
              djupt=True, geometri=True)
    m = KO.rackvidd_ur_fakta(f)
    assert m.harkomst == K.Harkomst.HARLEDD
    assert abs(m.varde.som_mm - 579.8) < 1e-6
    assert "envelopeprofile" in m.kalla


def test_rackvidden_SAKNAS_nar_varken_falt_eller_profil_finns(tmp_path):
    f = K.las(robot(tmp_path, rackvidd="0"), djupt=True, geometri=True)
    m = KO.rackvidd_ur_fakta(f)
    assert m.harkomst == K.Harkomst.SAKNAS
    assert m.varde is None, "noll ar inte en rackvidd, det ar en saknad rackvidd"
    o = KO.objekt_ur_komponent(f, bounds=bounds(1000.0, 1000.0, 1000.0))
    assert o.rackvidd is None


# ---------------------------------------------------------------------------
# TRASIG FIXTUR 2: layouten som saag mojlig ut med lador
# ---------------------------------------------------------------------------

#: Den gissning `provscener.py` gor i dag: robotens fotplatta ar 0,30 gangar
#: rackvidden. Talet star dar som ANTAGET, och det ar precis det antagandet
#: den har fixturen faller.
GISSAD_FOTANDEL = 0.30          # ANTAGET, kopierat ur provscener.ROBOTFOT_ANDEL


def _scen_med_tva_robotar(fotsida_mm, tmp_path):
    """Tva robotar i en 6 x 1,2 m korridor. Enda skillnaden ar fotens storlek."""
    hall = Hall("korridor", Langd.m(6.0), Langd.m(1.2), Langd.m(6.0))
    scen = Scen(hall)
    f = K.las(robot(tmp_path), djupt=True, geometri=True)
    for namn in ("robot_a", "robot_b"):
        scen.lagg_till(KO.objekt_ur_komponent(
            f, bounds=bounds(fotsida_mm, fotsida_mm, 1900.0), namn=namn))
    return scen


def test_lador_ryms_men_de_riktiga_matten_gor_det_inte(tmp_path):
    """Hela poangen med M-61, som ett prov.

    Samma korridor, samma relation, samma losare. Den enda skillnaden ar
    vilken lada objekten bar: den GISSADE ur rackvidden, eller den VC skulle
    ha lamnat. Gissningen sager LOST. Den riktiga sager RYMS_INTE.
    """
    gissad_mm = 2000.0 * GISSAD_FOTANDEL          # 600 mm
    riktig_mm = 1400.0                            # sa stor ar en IRB 6700-fot
    krav = [MinstaAvstand("robot_a", "robot_b", Langd.m(2.0))]

    med_lador = losa(_scen_med_tva_robotar(gissad_mm, tmp_path), krav)
    assert med_lador.status is Status.LOST, \
        "med den gissade ladan ser layouten mojlig ut - det ar felet"

    med_riktiga = losa(_scen_med_tva_robotar(riktig_mm, tmp_path), krav)
    assert med_riktiga.status is not Status.LOST
    assert med_riktiga.status is Status.RYMS_INTE
    assert med_riktiga.skal, "ett nej utan skal ar inget svar"


def test_samma_scen_med_gissade_matt_doljer_att_den_ar_omojlig(tmp_path):
    """Den andra halvan av samma sak: en lag som losaren SAGER ar lost, och
    som VC:s egen geometri hade fallt. Provet later de tva utfallen sta
    bredvid varandra sa att skillnaden ar ett tal och inte en asikt."""
    krav = [MinstaAvstand("robot_a", "robot_b", Langd.m(2.0))]
    lada = losa(_scen_med_tva_robotar(600.0, tmp_path), krav)
    riktig = losa(_scen_med_tva_robotar(1400.0, tmp_path), krav)
    assert (lada.status.value, riktig.status.value) == ("LOST", "RYMS_INTE")


# ---------------------------------------------------------------------------
# vagen ut till VC: den strikta grinden slapper igenom en riktig komponent
# ---------------------------------------------------------------------------

def test_riktiga_komponenter_passerar_den_strikta_ankargrinden(tmp_path):
    """`till_verktygsanrop(strikt=True)` vagrar skriva anrop ur ett ANTAGET
    ankare. En lada har alltid ett antaget ankare; en riktig komponent med
    VC:s get_bounds har ett MATT. Det ar dorren som oppnas har."""
    hall = Hall("hall", Langd.m(20.0), Langd.m(12.0), Langd.m(6.0))
    scen = Scen(hall)
    f = K.las(robot(tmp_path), djupt=True, geometri=True)
    b = KO.Bindning("robot_1", f, bounds(1400.0, 1200.0, 1900.0))
    scen.lagg_till(b.objekt())
    losning = losa(scen, ())
    assert losning.status is Status.LOST
    anrop = till_verktygsanrop(losning.scen, strikt=True,
                               komponentnamn=KO.komponentnamn_karta([b]))
    assert len(anrop) == 1
    assert anrop[0].argument["component"] == "IRB prov"


def test_komponentnamnet_ar_vcs_namn_inte_layoutens(tmp_path):
    f = K.las(robot(tmp_path), djupt=True)
    karta = KO.komponentnamn_karta([KO.Bindning("robot_1", f)])
    assert karta == {"robot_1": "IRB prov"}


# ---------------------------------------------------------------------------
# granssnitten: det en lada inte har
# ---------------------------------------------------------------------------

def test_tva_band_kopplas_ut_till_in(tmp_path):
    a = K.las(band(tmp_path, "B1"), djupt=True)
    b = K.las(band(tmp_path, "B2"), djupt=True)
    par = KO.kopplingsbara(a, b)
    assert len(par) == 1
    assert (par[0].granssnitt_a, par[0].granssnitt_b) == ("OutInterface",
                                                          "InInterface")


def test_ett_verktyg_monteras_pa_en_robot_men_inte_tvartom(tmp_path):
    r = K.las(robot(tmp_path), djupt=True)
    v = K.las(verktyg(tmp_path), djupt=True)
    fram = KO.kopplingsbara(r, v)
    assert [k.granssnitt_a for k in fram] == ["Tool"]
    assert KO.kopplingsbara(v, r) == (), "monteringen har en riktning"


def test_tva_robotar_monteras_INTE_i_varandra(tmp_path):
    """TRASIG FIXTUR: bada bar Mount 1, alltsa bada vill monteras PA nagot.
    En regel som bara letar efter 'samma falttyp' hade parat ihop dem."""
    a = K.las(robot(tmp_path, "R1"), djupt=True)
    b = K.las(robot(tmp_path, "R2"), djupt=True)
    assert KO.kopplingsbara(a, b) == ()


def test_ett_bands_INGANG_kopplas_inte_till_ett_annat_bands_INGANG(tmp_path):
    """TRASIG FIXTUR: tva ingangar. Port 0 mot port 0 ar inget flode."""
    a = K.las(band(tmp_path, "B1"), djupt=True)
    bara_in = tuple(g for g in a.granssnitt if g.namn == "InInterface")
    a.granssnitt = bara_in
    b = K.las(band(tmp_path, "B2"), djupt=True)
    b.granssnitt = tuple(g for g in b.granssnitt if g.namn == "InInterface")
    assert KO.kopplingsbara(a, b) == ()


# ---------------------------------------------------------------------------
# transportorens riktning: ordningen gar att lasa, vektorn nastan aldrig
# ---------------------------------------------------------------------------

def band_med_ramar(tmp_path, namn, ramar):
    kropp = (A.GRANSSNITT_FLODE % {"namn": "InInterface", "ram": "Start",
                                   "faltnamn": "FlowIn", "port": 0}
             + A.GRANSSNITT_FLODE % {"namn": "OutInterface", "ram": "End",
                                     "faltnamn": "FlowOut", "port": 1}
             + ramar)
    return A.skriv(tmp_path / (namn + ".vcmx"),
                   A.modelxml(Name=namn, Type="Conveyors", Manufacturer="A"),
                   A.rsc(namn, kropp))


def test_ordningen_lases_men_riktningen_saknas_nar_ramarna_ar_parametriska(tmp_path):
    ramar = (A.RAM_UTTRYCK % {"namn": "Start", "uttryck": "-FrontExtension"}
             + A.RAM_UTTRYCK % {"namn": "End", "uttryck": "BaseLength"})
    f = K.las(band_med_ramar(tmp_path, "B", ramar), djupt=True)
    flode = KO.flode_ur_fakta(f)
    assert flode.ordning is True
    assert (flode.in_granssnitt, flode.ut_granssnitt) == (("InInterface",),
                                                          ("OutInterface",))
    assert (flode.in_ram, flode.ut_ram) == ("Start", "End")
    assert flode.riktning_mm is None
    assert flode.langd_mm is None
    assert "BaseLength" in flode.skal, "skalet ska namna uttrycket som band"


def test_riktningen_raknas_nar_bada_ramarna_gar_att_lasa(tmp_path):
    ramar = (A.RAM_MATRIS % {"namn": "Start", "x": 0.0, "y": 0.0, "z": 900.0}
             + A.RAM_MATRIS % {"namn": "End", "x": 2000.0, "y": 0.0, "z": 900.0})
    f = K.las(band_med_ramar(tmp_path, "B", ramar), djupt=True)
    flode = KO.flode_ur_fakta(f)
    assert flode.riktning_mm == (2000.0, 0.0, 0.0)
    assert flode.langd_mm == 2000.0
    assert flode.skal == ""


def test_ett_band_med_bara_en_ingang_har_ingen_ordning(tmp_path):
    """TRASIG FIXTUR: 41 av bibliotekets 163 transportorer bar inget
    flodesfalt alls, och ett band med bara en ingang har ingen riktning.
    Att svara "framat" hade varit en gissning som ser komplett ut."""
    kropp = (A.GRANSSNITT_FLODE % {"namn": "InInterface", "ram": "Start",
                                   "faltnamn": "FlowIn", "port": 0}
             + A.RAM_MATRIS % {"namn": "Start", "x": 0.0, "y": 0.0, "z": 0.0})
    sokvag = A.skriv(tmp_path / "halvband.vcmx",
                     A.modelxml(Name="Halvband", Type="Conveyors",
                                Manufacturer="A"),
                     A.rsc("Halvband", kropp))
    flode = KO.flode_ur_fakta(K.las(sokvag, djupt=True))
    assert flode is not None
    assert flode.ordning is False
    assert flode.riktning_mm is None


def test_en_komponent_utan_flodesfalt_ger_inget_flode(tmp_path):
    f = K.las(robot(tmp_path), djupt=True)
    assert KO.flode_ur_fakta(f) is None


# ---------------------------------------------------------------------------
# hela vagen: tre riktiga komponenter, en cell, och anropen ut
# ---------------------------------------------------------------------------

def test_en_hel_cell_av_riktiga_komponenter_gar_hela_vagen(tmp_path):
    """Fas 5:s vag, men med komponentfakta i stallet for lador.

    Tre komponenter, deras EGNA granssnitt kopplade i kedja, layouten lost,
    och anropen skrivna med den STRIKTA grinden pa. Provet visar att bryggan
    barar hela vagen och inte bara ett falt i taget.
    """
    band_in = K.las(band(tmp_path, "Band in"), djupt=True)
    band_ut = K.las(band(tmp_path, "Band ut"), djupt=True)
    robot_f = K.las(robot(tmp_path, "IRB cell", rackvidd="1650"),
                    djupt=True, geometri=True)

    bindningar = [
        KO.Bindning("band_in", band_in, bounds(3000.0, 600.0, 900.0)),
        KO.Bindning("robot_1", robot_f, bounds(1000.0, 1000.0, 1900.0)),
        KO.Bindning("band_ut", band_ut, bounds(3000.0, 600.0, 900.0)),
    ]

    hall = Hall("cell", Langd.m(20.0), Langd.m(12.0), Langd.m(6.0))
    scen = Scen(hall)
    for b in bindningar:
        scen.lagg_till(b.objekt(underhallsmarginal=Langd.mm(400.0),
                                enhet="CELL"))

    # kedjan gar att lasa ur filerna: band_in -> band_ut
    kedja = KO.kopplingsbara(band_in, band_ut)
    assert [(k.granssnitt_a, k.granssnitt_b) for k in kedja] == [
        ("OutInterface", "InInterface")]

    # och roboten nar bada banden, med rackvidden ur filen
    krav = [InomRackvidd("band_in", "robot_1", helt=False),
            InomRackvidd("band_ut", "robot_1", helt=False)]
    losning = losa(scen, krav)
    assert losning.status is Status.LOST, losning.skal

    anrop = till_verktygsanrop(losning.scen, strikt=True,
                               komponentnamn=KO.komponentnamn_karta(bindningar))
    assert len(anrop) == 3
    namn = sorted(a.argument["component"] for a in anrop)
    assert namn == ["Band in", "Band ut", "IRB cell"]
    for a in anrop:
        assert len(a.argument["position"]) == 3
        assert a.argument["wpr"][0] == 0.0 and a.argument["wpr"][1] == 0.0


def test_ett_objekt_utan_lada_stoppar_hela_kedjan(tmp_path):
    """TRASIG FIXTUR: en av tre komponenter saknar sin lada.

    Cellen far INTE bli tva komponenter placerade och en tyst borta. Bryggan
    faller redan nar objektet ska byggas, med namnet pa den som saknar matt.
    """
    band_in = K.las(band(tmp_path, "Band in"), djupt=True)
    robot_f = K.las(robot(tmp_path, "IRB cell"), djupt=True, geometri=True)
    bindningar = [KO.Bindning("band_in", band_in, bounds(3000.0, 600.0, 900.0)),
                  KO.Bindning("robot_1", robot_f, None)]
    byggda = []
    with pytest.raises(KO.Saknasfel) as fel:
        for b in bindningar:
            byggda.append(b.objekt())
    assert len(byggda) == 1
    assert "IRB cell" in str(fel.value)


def test_bryggan_avvisar_nagot_som_inte_ar_komponentfakta():
    with pytest.raises(Exception):
        KO.objekt_ur_komponent({"namn": "inte fakta"})
