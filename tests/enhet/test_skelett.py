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
