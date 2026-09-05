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


def _ogonrapport(dom="PASS", orsak="allt inom marginal", extra=None, granser=True):
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
    if granser:
        _granser(r)
    r.satt_dom(dom, orsak)
    return r.text()


def _granser(r):
    """LIMITS: v2 (M-65). Grinden kraver att ogat sager vad det inte ser."""
    r.sektion("LIMITS")
    for namn in K.EJ_SIMULERAT:
        r.rad("NOT_SIMULATED %s" % namn)
    r.rad("RESOLUTION sample=50.0ms read=50.0ms join=13.45ms PRIOR phase=63.5ms")
    r.rad("EXCLUDED plc_scan 40.0ms")
    return r


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
    b = _grind().doma([_cell(eyes=_ogonrapport().replace(
        "EYES v%d" % K.EYES_VERSION, "EYES v9", 1))])
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
    Sedan v2 vagrar redan skrivaren; kommer texten utifran faller den pa
    kontraktet, och grinden svarar med kontraktets egen dom.
    """
    r = K.Rapport("plocka", "2026-09-04T18:00:00", 9.5, 190, 20.0)
    r.sektion("MOTION")
    r.rad("PLACE OFF_TARGET err=812.0mm z=0.750m")
    r.sektion("HONESTY")
    r.rad("NEVER_GRIPPED OK")
    _granser(r)
    with pytest.raises(K.Kontraktsfel):
        r.satt_dom("PASS", "ser bra ut")
    r.satt_dom("FAIL", "fel placerad")
    text = r.text().replace("EYES VERDICT FAIL fel placerad", "EYES VERDICT PASS ser bra ut")
    b = _grind().doma([_cell(eyes=text)])
    assert b.guld is False and "malformed" in b.skal


def test_PASS_med_kollision_ar_inte_guld():
    """Sedan v2 vagrar SKRIVAREN sjalv ett PASS bredvid en kollision (regel 5,
    utokad). Kommer texten utifran ar den ett kontraktsfel, och grinden ger
    NOT GOLD med kontraktets egen dom."""
    r = K.Rapport("plocka", "2026-09-04T18:00:00", 9.5, 190, 20.0)
    r.sektion("MOTION")
    r.rad("GRIP FORMED t=1.0s dist=0.0mm")
    r.sektion("SAFETY")
    r.rad("COLLISION gripare x fixtur t=3.100s")
    r.sektion("HONESTY")
    r.rad("NEVER_GRIPPED OK")
    _granser(r)
    with pytest.raises(K.Kontraktsfel):
        r.satt_dom("PASS", "ser bra ut")
    r.satt_dom("FAIL", "kollision")
    text = r.text().replace("EYES VERDICT FAIL kollision", "EYES VERDICT PASS ser bra ut")
    b = _grind().doma([_cell(eyes=text)])
    assert b.guld is False and "malformed" in b.skal


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
    r.sektion("HONESTY")
    r.rad("NEVER_GRIPPED OK")
    _granser(r)
    r.satt_dom("PASS", "inom den har cellens tolerans")
    assert _grind().doma([_cell(eyes=r.text())]).guld is True


# ---- hal funna av motbevisningen 2026-09-04 -----------------------------

def test_en_rapport_som_inte_matt_nagot_ar_inte_guld():
    """Noll sektioner, SAMPLES 0, DUR 0.000s + VERDICT PASS gav GOLD.

    Sista grinden fore leverans slappte igenom en rapport som inte hade matt
    en enda sak. Rakt emot I3: tystnad ar aldrig ett godkannande.
    """
    r = K.Rapport("tom", "2026-09-04T00:00:00", 0.0, 0, 0.0)
    r.satt_dom("PASS", "inget att invanda mot")
    b = _grind().doma([_cell(eyes=r.text())])
    assert b.guld is False
    assert "noll prov" in b.skal


def test_en_rapport_utan_varaktighet_ar_inte_guld():
    r = K.Rapport("kort", "2026-09-04T00:00:00", 0.0, 200, 20.0)
    r.sektion("MOTION"); r.rad("GRIP FORMED t=1.0s dist=0.0mm")
    r.sektion("HONESTY"); r.rad("NEVER_GRIPPED OK")
    r.satt_dom("PASS", "gick fort")
    b = _grind().doma([_cell(eyes=r.text())])
    assert b.guld is False and "varaktighet" in b.skal


def test_en_rapport_utan_HONESTY_ar_inte_guld():
    """Kontraktets regel 5 sager att en overtradelse tvingar FAIL - men regeln
    ar TOM om sektionen inte finns. Utan HONESTY finns ingen arlighetsgrind."""
    r = K.Rapport("utan", "2026-09-04T00:00:00", 9.0, 180, 20.0)
    r.sektion("MOTION")
    r.rad("GRIP FORMED t=1.0s dist=0.0mm")
    r.rad("CARRY RIGID rot=0.0deg span=4.0s")
    r.rad("PLACE IN_TARGET err=1.0mm z=0.7m")
    _granser(r)
    r.satt_dom("PASS", "ser bra ut")
    b = _grind().doma([_cell(eyes=r.text())])
    assert b.guld is False and "HONESTY" in b.skal


def test_en_rapport_utan_MOTION_ar_inte_guld():
    r = K.Rapport("utan", "2026-09-04T00:00:00", 9.0, 180, 20.0)
    r.sektion("HONESTY"); r.rad("NEVER_GRIPPED OK")
    _granser(r)
    r.satt_dom("PASS", "ser bra ut")
    b = _grind().doma([_cell(eyes=r.text())])
    assert b.guld is False and "MOTION" in b.skal


# ---- v2 (M-65): rapporten maste saga vad ogat INTE ser ------------------

def test_en_rapport_utan_LIMITS_ar_inte_guld():
    """TRASIG FIXTUR (M-65 §6). Samma rapport som ger guld, utan LIMITS.

    Ogat ar felfinnande, aldrig bevis. Sensorstuds, stalldonsdynamik,
    faltbussjitter och degraderade lagen finns inte i simuleringen, och det
    ska sta i rapporten - som en sektion grinden kraver, inte som en fotnot.
    """
    b = _grind().doma([_cell(eyes=_ogonrapport(granser=False))])
    assert b.guld is False and "LIMITS" in b.skal


def test_en_v1_rapport_lases_men_ar_inte_guld_langre():
    """v1 ar en delmangd av v2 och lases. Men den saknar LIMITS, och da ar
    den inte guld: det finns ingen vag runt kravet genom att tala v1."""
    text = _ogonrapport(granser=False).replace("EYES v2", "EYES v1", 1)
    assert K.las(text).version == 1
    b = _grind().doma([_cell(eyes=text)])
    assert b.guld is False and "LIMITS" in b.skal


def test_LIMITS_maste_namna_varje_sak_som_inte_finns_i_simuleringen():
    """En rubrik ar ingen arlighet. Grinden laser namnen ur kontraktets egen
    lista - saknas ett ar sektionen ofullstandig."""
    text = _ogonrapport().replace("  NOT_SIMULATED fieldbus_jitter\n", "")
    b = _grind().doma([_cell(eyes=text)])
    assert b.guld is False and "fieldbus_jitter" in b.skal


def test_LIMITS_maste_bara_en_upplosning():
    text = "\n".join(r for r in _ogonrapport().splitlines()
                     if not r.startswith("  RESOLUTION")) + "\n"
    b = _grind().doma([_cell(eyes=text)])
    assert b.guld is False and "RESOLUTION" in b.skal


@pytest.mark.parametrize("rad", [
    ("SEQUENCE", "STEP 0 plc:stopp RISE MISSING win=0.00s..0.50s"),
    ("SEQUENCE", "STEP 1 plc:stopp FALL TOO_LATE t=3.400s win=1.50s..2.50s"),
    ("SEQUENCE", "INTERLOCK plc:stopp+plc:slapp BROKEN overlap=0.750s"),
    ("TIMING", "PHASE plc:Start -> grip_out dt=510.0ms tol=100.0ms res=63.5ms OUT_OF_TOL"),
    ("THROUGHPUT", "STARVED station1 9.500s req=1.000s EXCEEDED"),
    ("SCENE", "UNCOMMANDED stallage dist=500.0mm t=2.000s"),
    ("SCENE", "FLUNG del 5.39m/s t=2.500s"),
    ("SCENE", "THINNED factor=64 CEILING budget=5.0ms median=15.200ms"),
])
def test_ett_v2_fynd_bredvid_PASS_ar_inte_guld(rad):
    """Regel 5, utokad: orden ar ogats egna, och grinden laser dem som HELA
    ord - "LATE" inne i "LATENCY" far inte falla en rapport."""
    sektion, text = rad
    r = K.Rapport("plocka", "2026-09-04T18:00:00", 9.5, 190, 20.0)
    r.sektion("MOTION"); r.rad("GRIP FORMED t=0.950s dist=0.0mm")
    r.sektion("TIMING"); r.rad("LATENCY grip_out -> gripper 20.0ms")
    r.sektion(sektion); r.rad(text)
    r.sektion("HONESTY"); r.rad("NEVER_GRIPPED OK")
    _granser(r)
    with pytest.raises(K.Kontraktsfel):
        r.satt_dom("PASS", "ser bra ut")
    r.satt_dom("FAIL", "fynd")
    smugglad = r.text().replace("EYES VERDICT FAIL fynd", "EYES VERDICT PASS ser bra ut")
    b = _grind().doma([_cell(eyes=smugglad)])
    assert b.guld is False


def test_LATENCY_faller_inte_pa_ordet_LATE():
    """Den andra riktningen for ordmatchningen."""
    text = _ogonrapport(extra="GRIP FORMED t=0.950s dist=0.0mm").replace(
        "SECTION SAFETY", "SECTION TIMING\n  LATENCY grip_out -> gripper 20.0ms\nSECTION SAFETY")
    assert _grind().doma([_cell(eyes=text)]).guld is True


def test_en_fullstandig_rapport_ar_fortfarande_guld():
    """Grinden far inte bli sa bred att den faller det riktiga."""
    assert _grind().doma([_cell()]).guld is True


TOM_MB = ("EYES v1\n"
          "TEMPLATE plocka_och_placera\n"
          "RUN 2026-09-04T17:00:00 DUR 0.000s SAMPLES 0 RATE 0.00Hz\n"
          "EYES VERDICT PASS inget uppmatt\n")


def _cell_mb(eyes, namn="station1"):
    return {"namn": namn, "klass": "plocka_och_placera",
            "forgrindar": dict((g, True) for g in FORGRINDAR), "eyes": eyes}


def _grind_mb():
    return Guldgrind(["plocka_och_placera"])


def test_en_rapport_utan_en_enda_matning_ar_inte_guld():
    b = _grind_mb().doma([_cell_mb(TOM_MB)])
    assert not b.guld, (
        "en rapport med noll sektioner, SAMPLES 0 och DUR 0,000 s gav %s. "
        "Tystnad är aldrig ett godkännande (I3)." % b.text())

