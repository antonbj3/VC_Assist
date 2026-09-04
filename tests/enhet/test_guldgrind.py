# -*- coding: utf-8 -*-
"""L0: guldgrinden. Kalla: 50_grindar.md.

Grinden ar fail-closed pa varje vag in. De flesta testerna har provar att den
INTE ger guld - det ar hela poangen med en grind.
"""
import os
import sys

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "svc")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))

import oga_kontrakt as K                       # noqa: E402
from vc_assist_svc.guldgrind import (          # noqa: E402
    Guldgrind, L1, L2, INTE_GULD, FORGRINDAR)

KLASSER = {"plocka", "montera", "linje"}


def _ogonrapport(dom="PASS", orsak="allt inom marginal", extra=None):
    r = K.Rapport("plocka", "2026-09-04T18:00:00", 9.5, 190, 20.0)
    r.sektion("MOTION")
    r.rad(extra or "GRIP FORMED t=0.950s dist=0.0mm")
    if not extra:
        r.rad("CARRY RIGID rot=0.0deg span=4.550s")
        r.rad("PLACE IN_TARGET err=1.2mm z=0.750m")
    r.sektion("SAFETY")
    r.rad("COLLISION none")
    r.sektion("HONESTY")
    r.rad("TELEPORT_TRANSFER OK")
    r.rad("NEVER_GRIPPED OK")
    r.satt_dom(dom, orsak)
    return r.text()


def _cell(namn="st010", klass="plocka", eyes=None, forgrindar=None):
    return {"namn": namn, "klass": klass,
            "eyes": _ogonrapport() if eyes is None else eyes,
            "forgrindar": dict((g, True) for g in FORGRINDAR)
            if forgrindar is None else forgrindar}


def _grind():
    return Guldgrind(KLASSER)


# ---- guld ges nar allt stammer ------------------------------------------

def test_en_station_som_passerar_ger_L1():
    b = _grind().doma([_cell()])
    assert b.niva == L1 and b.guld is True
    assert "GOLD" in b.text()


def test_alla_stationer_plus_linan_ger_L2():
    b = _grind().doma([_cell("st010"), _cell("st020")],
                      linje=_cell("linjen", klass="linje"))
    assert b.niva == L2 and b.guld is True


# ---- fail-closed pa varje vag in ----------------------------------------

def test_tom_lista_ar_inte_guld():
    """Ingenting att doma ar inte ett godkannande."""
    assert _grind().doma([]).guld is False


def test_okand_klass_ar_inte_guld():
    b = _grind().doma([_cell(klass="nagot_nytt")])
    assert b.niva == INTE_GULD
    assert "okand scenarioklass" in b.skal


def test_saknad_ogonrapport_ar_inte_guld():
    b = _grind().doma([_cell(eyes="")])
    assert b.guld is False and "ingen ogonrapport" in b.skal


def test_avhuggen_ogonrapport_ar_inte_guld():
    text = "\n".join(_ogonrapport().splitlines()[:-1])
    b = _grind().doma([_cell(eyes=text)])
    assert b.guld is False and "truncated" in b.skal


def test_okand_ogonversion_ar_inte_guld():
    b = _grind().doma([_cell(eyes=_ogonrapport().replace("EYES v1", "EYES v9", 1))])
    assert b.guld is False and "unknown eyes version" in b.skal


def test_FAIL_fran_ogat_ar_inte_guld():
    b = _grind().doma([_cell(eyes=_ogonrapport("FAIL", "delen tappades"))])
    assert b.guld is False and "ogat sa FAIL" in b.skal


def test_INCONCLUSIVE_ar_inte_guld():
    b = _grind().doma([_cell(eyes=_ogonrapport("INCONCLUSIVE", "for fa prov"))])
    assert b.guld is False


@pytest.mark.parametrize("grind", FORGRINDAR)
def test_en_okord_forgrind_ar_inte_guld(grind):
    """Tystnad ar aldrig ett godkannande - en grind som inte kort ar rod."""
    f = dict((g, True) for g in FORGRINDAR)
    del f[grind]
    b = _grind().doma([_cell(forgrindar=f)])
    assert b.guld is False and grind in b.skal


@pytest.mark.parametrize("grind", FORGRINDAR)
def test_en_rod_forgrind_ar_inte_guld(grind):
    f = dict((g, True) for g in FORGRINDAR)
    f[grind] = "tva odeklarerade taggar"
    b = _grind().doma([_cell(forgrindar=f)])
    assert b.guld is False and "underkande" in b.skal


def test_en_enda_fallen_cell_stoppar_guldet_for_alla():
    b = _grind().doma([_cell("st010"), _cell("st020", eyes=_ogonrapport("FAIL", "x")),
                       _cell("st030")])
    assert b.guld is False
    assert b.per_cell["st010"][0] is True
    assert b.per_cell["st020"][0] is False


def test_stationer_kan_vara_grona_men_linan_falla():
    b = _grind().doma([_cell("st010"), _cell("st020")],
                      linje=_cell("linjen", klass="linje",
                                  eyes=_ogonrapport("FAIL", "svalt vid st020")))
    assert b.guld is False and "linan foll" in b.skal


# ---- sjalvmotsagelse ----------------------------------------------------

def test_PASS_med_en_dalig_rad_ar_inte_guld():
    """Ogats dom ar auktoritativ, men en rapport far inte motsaga sig sjalv.

    Grinden mater ingenting har - den laser ogats EGET kategoriska ord.
    """
    r = K.Rapport("plocka", "2026-09-04T18:00:00", 9.5, 190, 20.0)
    r.sektion("MOTION")
    r.rad("PLACE OFF_TARGET err=812.0mm z=0.750m")
    r.satt_dom("PASS", "ser bra ut")
    b = _grind().doma([_cell(eyes=r.text())])
    assert b.guld is False and "motsaga" not in b.skal
    assert "OFF_TARGET" in b.skal


def test_PASS_med_kollision_ar_inte_guld():
    r = K.Rapport("plocka", "2026-09-04T18:00:00", 9.5, 190, 20.0)
    r.sektion("SAFETY")
    r.rad("COLLISION gripare x fixtur t=3.100s")
    r.satt_dom("PASS", "ser bra ut")
    b = _grind().doma([_cell(eyes=r.text())])
    assert b.guld is False and "COLLISION" in b.skal


def test_COLLISION_none_ar_inte_en_kollision():
    """Grinden far inte bli sa bred att den faller det normala."""
    assert _grind().doma([_cell()]).guld is True


# ---- grinden raknar inte om nagot ---------------------------------------

def test_grinden_laser_inte_ut_nagra_tal():
    """50_grindar.md: grinden implementerar ALDRIG om mattet.

    En rapport med grona ord men extrema tal ska ge guld - det ar ogats sak
    att doma talen, och en omimplementering underkande 2 av 4 medan ogat
    visade 4 av 4.
    """
    r = K.Rapport("plocka", "2026-09-04T18:00:00", 9.5, 190, 20.0)
    r.sektion("MOTION")
    r.rad("PLACE IN_TARGET err=999.0mm z=0.750m")   # ogat kallade det ratt
    r.satt_dom("PASS", "inom den har cellens tolerans")
    assert _grind().doma([_cell(eyes=r.text())]).guld is True
