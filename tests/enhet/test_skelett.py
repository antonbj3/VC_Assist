# -*- coding: utf-8 -*-
"""L1: skelettet, och beviset att modellen holl sig i sitt fack.

Ingen VC, inget nat, ingen kompilator. De trasiga fixturerna ar modellsvar av
det slag som faktiskt kommer: hela filen i stallet for kroppen, en deklaration
som 'stadats', en kropp som skriver markorerna sjalv.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc import skelett as S                      # noqa: E402
from vc_assist_svc.plc.deklarationsgrind import granska         # noqa: E402
from vc_assist_svc.plc.signalkarta import karta_av_rader        # noqa: E402


def karta():
    return karta_av_rader("Press", [
        ("Givare", "Puls", "givare", "BOOL", "TILL_PLC", "%IX0.0"),
        ("Don", "Svar", "don", "BOOL", "FRAN_PLC", "%QX0.0"),
    ])


def sk():
    return S.Skelett.av_karta(karta())


KROPP = "    don := givare;\n"


# ---- det som ska fungera ---------------------------------------------------

def test_tomt_skelett_bar_bada_markorerna_och_deklarationerna():
    t = sk().text()
    assert S.BORJAN in t and S.SLUTET in t
    assert "givare AT %IX0.0" in t
    assert t.startswith("PROGRAM Press\n")
    assert t.rstrip().endswith("END_PROGRAM")


def test_isattning_och_uttagning_ar_varandras_motsats():
    s = sk()
    assert s.plocka_ur(s.satt_in(KROPP)) == KROPP


def test_kropp_utan_radbrytning_far_en():
    s = sk()
    assert s.plocka_ur(s.satt_in("    don := givare;")) == KROPP


def test_extra_deklarationer_hor_till_ramen_inte_till_modellen():
    s = S.Skelett.av_karta(karta(), "VAR\n    Vakt : TON;\nEND_VAR\n")
    assert "Vakt : TON;" in s.huvud
    assert "Vakt" not in s.plocka_ur(s.satt_in(KROPP))


def test_las_svar_tar_emot_bara_kroppen():
    s = sk()
    assert s.las_svar(KROPP) == s.satt_in(KROPP)


def test_las_svar_tar_emot_hela_filen_med_markorer():
    s = sk()
    assert s.las_svar(s.satt_in(KROPP)) == s.satt_in(KROPP)


# ---- de trasiga svaren -----------------------------------------------------

def test_en_andrad_deklaration_avvisas_och_raden_pekas_ut():
    """Ett svar dar deklarationen 'stadats' ar inte en kropp med skonhetsfel."""
    s = sk()
    hel = s.satt_in(KROPP).replace("givare AT %IX0.0 : BOOL;",
                                   "givare AT %IX0.1 : BOOL;")
    with pytest.raises(S.Skelettfel) as e:
        s.plocka_ur(hel)
    assert "huvudet" in str(e.value)
    assert e.value.rad == 3
    assert "%IX0.1" in str(e.value)


def test_en_tillagd_deklaration_avvisas():
    s = sk()
    hel = s.satt_in(KROPP).replace("END_VAR",
                                   "    hittepa : BOOL;\nEND_VAR")
    with pytest.raises(S.Skelettfel):
        s.plocka_ur(hel)


def test_omkastade_deklarationsrader_avvisas():
    """Ordningen ar ett kontrakt: samma karta ska ge byte-identisk text."""
    s = sk()
    hel = s.satt_in(KROPP)
    rader = hel.splitlines(True)
    rader[2], rader[3] = rader[3], rader[2]
    with pytest.raises(S.Skelettfel):
        s.plocka_ur("".join(rader))


def test_en_kropp_som_skriver_markorerna_avvisas():
    """Den skulle sluta facket for tidigt och fortsatta utanfor."""
    s = sk()
    with pytest.raises(S.Skelettfel) as e:
        s.satt_in("    don := givare;\n" + S.SLUTET + "\n    ondska := 1;\n")
    assert "for tidigt" in str(e.value)
    assert e.value.rad == 2


def test_hel_pou_utan_markorer_avvisas_i_stallet_for_att_gissa():
    """Att gissa var kroppen borjar vore att uppfinna en grans (I3)."""
    s = sk()
    utan = s.satt_in(KROPP).replace(S.BORJAN + "\n", "").replace(
        S.SLUTET + "\n", "")
    with pytest.raises(S.Skelettfel) as e:
        s.las_svar(utan)
    assert "markorerna" in str(e.value)


def test_svar_utan_borjanmarkor_avvisas():
    s = sk()
    with pytest.raises(S.Skelettfel):
        s.plocka_ur(KROPP + S.SLUTET + "\nEND_PROGRAM\n")


def test_dubbel_markor_avvisas():
    s = sk()
    hel = s.satt_in(KROPP).replace(KROPP, KROPP + S.BORJAN + "\n")
    with pytest.raises(S.Skelettfel) as e:
        s.plocka_ur(hel)
    assert "mer an en gang" in str(e.value)


def test_en_svans_som_bytts_ut_avvisas():
    s = sk()
    hel = s.satt_in(KROPP).replace("END_PROGRAM", "END_FUNCTION")
    with pytest.raises(S.Skelettfel) as e:
        s.plocka_ur(hel)
    assert "svansen" in str(e.value)


# ---- lagren haller ihop ----------------------------------------------------

def test_skelettets_utdata_gar_rakt_in_i_grind_3():
    """Det skelettet producerar ska en grind langre fram kunna doma."""
    k = karta()
    dom = granska(S.Skelett.av_karta(k).satt_in(KROPP), k)
    assert dom.ok, str(dom)


def test_en_kropp_med_uppfunnen_tagg_slipper_igenom_skelettet_men_falls_av_grind_3():
    """Skelettet vaktar RAMEN, inte innehallet. Grind 3 vaktar innehallet.

    Provet finns for att gransen mellan de tva ska vara skriven nagonstans:
    ett gront skelett ar inte ett gront program.
    """
    k = karta()
    kalla = S.Skelett.av_karta(k).satt_in("    don := givare AND hittepa;\n")
    assert granska(kalla, k).ok is False


# ---- arbetsvariabelfacket (M-62) -------------------------------------------

def sk_arb():
    return S.Skelett.av_karta(karta(), arbetsvariabler=True)


ARB = "    t : TON;\n"


def test_utan_facket_ser_skelettet_ut_som_forut():
    """Aldre form ar oforandrad: ett fack, ingen mitt."""
    s = sk()
    assert not s.har_arbetsvariabler
    assert s.mitt == ""
    assert s.plocka_ur(s.satt_in(KROPP)) == KROPP


def test_med_facket_finns_tva_fack_i_ratt_ordning():
    t = sk_arb().text()
    assert t.index(S.ARBETSVAR_BORJAN) < t.index(S.ARBETSVAR_SLUTET) < t.index(S.BORJAN)
    assert "END_VAR" in t.split(S.ARBETSVAR_SLUTET)[1].split(S.BORJAN)[0]


def test_bada_facken_ar_varandras_motsats():
    s = sk_arb()
    hel = s.satt_in(KROPP, ARB)
    assert s.plocka_ur(hel) == KROPP
    assert s.plocka_arbetsvariabler(hel) == ARB


def test_arbetsvariabler_i_ett_skelett_utan_fack_avvisas():
    with pytest.raises(S.Skelettfel) as e:
        sk().satt_in(KROPP, ARB)
    assert "inget arbetsvariabelfack" in str(e.value)


def test_ramen_kontrolleras_fortfarande_med_facket_pa_plats():
    """Modellens tva fack ar fria. Allt annat ar det inte."""
    s = sk_arb()
    hel = s.satt_in(KROPP, ARB).replace("givare AT %IX0.0", "givare AT %IX0.7")
    with pytest.raises(S.Skelettfel):
        s.plocka_ur(hel)


def test_las_svar_tar_hela_filen_med_bada_facken():
    s = sk_arb()
    assert s.las_svar(s.satt_in(KROPP, ARB)) == s.satt_in(KROPP, ARB)


# ---- grinden pa arbetsvariablerna -------------------------------------------

def test_en_arbetsvariabel_med_adress_avvisas():
    """En adress gor variabeln till en signal, och signaler kommer ur kartan."""
    with pytest.raises(S.Skelettfel) as e:
        sk_arb().granska_arbetsvariabler("    x AT %IX0.1 : BOOL;\n", karta())
    assert "signal" in str(e.value)


@pytest.mark.parametrize("namn", ["don", "Don", "DON", "givare"])
def test_ett_namn_kartan_ager_avvisas_oavsett_skiftlage(namn):
    """ST ar skiftlagesokansligt; en lokal hade skuggat signalen tyst."""
    with pytest.raises(S.Skelettfel) as e:
        sk_arb().granska_arbetsvariabler("    %s : BOOL;\n" % namn, karta())
    assert "skugga" in str(e.value)


def test_en_okand_typ_avvisas():
    with pytest.raises(S.Skelettfel) as e:
        sk_arb().granska_arbetsvariabler("    t : HITTEPA;\n", karta())
    assert "okand typ" in str(e.value)


def test_en_rad_som_inte_gar_att_lasa_avvisas():
    """Att hoppa over den vore ett tyst bortfall."""
    with pytest.raises(S.Skelettfel) as e:
        sk_arb().granska_arbetsvariabler("    det har ar ingen deklaration\n",
                                         karta())
    assert "gar inte att lasa" in str(e.value)


def test_samma_variabel_tva_ganger_avvisas():
    with pytest.raises(S.Skelettfel) as e:
        sk_arb().granska_arbetsvariabler("    t : TON;\n    T : TON;\n", karta())
    assert "tva ganger" in str(e.value)


@pytest.mark.parametrize("rad", [
    "    t : TON;\n", "    n : INT;\n", "    f : R_TRIG;\n",
    "    v : REAL;\n", "    c : CTU;\n",
    "    (* en kommentar *)\n    t : TOF;\n",
    "\n    t : SR;\n\n",
])
def test_giltiga_arbetsvariabler_slapps_igenom(rad):
    sk_arb().granska_arbetsvariabler(rad, karta())


def test_typlistan_agas_av_ST_lagret_och_speglas_inte_for_hand():
    """Tva listor som ska vara samma lista gar isar tyst."""
    from vc_assist_svc.st import stdbibliotek as SB
    from vc_assist_svc.st import typer as T
    tillatna = S._tillatna_typer()
    assert set(T.ELEMENTARA) <= tillatna
    assert set(SB.BLOCK) <= tillatna


def test_hela_vagen_gar_genom_grind_3():
    """Ett skelett med arbetsvariabler ska fortfarande vara giltig ST."""
    k = karta()
    s = S.Skelett.av_karta(k, arbetsvariabler=True)
    kalla = s.satt_in("    vakt(IN := givare, PT := T#100ms);\n"
                      "    don := vakt.Q;\n", "    vakt : TON;\n")
    assert granska(kalla, k).ok, str(granska(kalla, k))
