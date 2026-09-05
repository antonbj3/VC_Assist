# -*- coding: utf-8 -*-
"""Ogats rapport till modellen: ordagrant, minus hela rader utan fynd.

FAS 22. Det har ar lagrets ORDLISTEPROV, och det star har darfor att
trimningen ar den enda plats i modellagret dar en ordlista avgor nagot: ar
raden "OK" nog for att fa forsvinna?

Fyra ganger har samma felklass matts i det har repot (M-94 tva ganger, M-95,
M-98): en ordlista som fyrar pa FEL STORHET. Har ar de tre formerna som gor
det pa en ogonrapport:

    MINDIST OK_ROBOT+STANGSEL 412.000mm t=1.200s
        "OK" ligger i ett PARNAMN. Raden har ingen dom alls - den bar ett
        avstand. En delstrangsmatchning trimmar en SAFETY-rad.
    STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s
        "OK" ligger i ett SIGNALNAMN och radens dom ar MISSING. En
        delstrangsmatchning trimmar ett FYND.
    EDGE ST100_STA_DONE RISE t=0.500s
        raden bar ingen dom, men den ar HELLER inte ett fynd. Den far trimmas
        - och da ska forsta och sista raden sta kvar sa att tidsspannet inte
        forsvinner.

Losningen ar inte en battre ordlista. Den ar att fraga GRAMMATIKEN: ogats
kontrakt har ett monster per radsort, och domen ligger i en egen
alternativgrupp. Trimningen laser DEN GRUPPEN.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist"),
           os.path.join(_ROT, "tests", "protocol", "stod")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fas22_fixturer as FX                                    # noqa: E402
import oga_kontrakt as K                                       # noqa: E402
from vc_assist_svc.llm import ogontrim as O                    # noqa: E402


# ---- statusen kommer ur grammatiken, inte ur en delstrang ---------------

@pytest.mark.parametrize("sektion,rad,vantad", [
    ("TIMING", "DWELL ST250 19.400s req=26.000s SHORT", "SHORT"),
    ("TIMING", "DWELL ST260 31.050s req=31.000s OK", "OK"),
    ("TIMING", "EDGE ST260_PRT_PRS RISE t=64.200s", None),
    ("TIMING", "RACE none", "none"),
    ("SAFETY", "MINDIST enhet+stationsvagg 34.000mm t=64.350s", None),
    ("SAFETY", "COLLISION none", "none"),
    ("HONESTY", "TELEPORT_TRANSFER OK", "OK"),
    ("HONESTY", "BLOWUP VIOLATION vmax=99.000m/s", "VIOLATION"),
    ("MOTION", "GRIP FORMED t=1.000s dist=2.000mm", "FORMED"),
    ("MOTION", "PLACE OFF_TARGET err=12.000mm z=0.900m", "OFF_TARGET"),
    ("SEQUENCE", "STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s",
     "MISSING"),
    ("SCENE", "OBJECTS total=9 moving=3 still=6 unread=0", None),
    ("SCENE", "THINNED factor=2 CEILING budget=50.000ms median=61.000ms",
     "CEILING"),
])
def test_status_lases_ur_radens_egen_domsgrupp(sektion, rad, vantad):
    assert O.status(sektion, rad) == vantad


def test_riktningsgruppen_ar_ingen_domsgrupp():
    """EDGE bar `(RISE|FALL)` och RESOLUTION bar `(RUN|PRIOR)`.

    Bada ser ut som domsgrupper - versala ord i en alternativgrupp - och ingen
    av dem ar det. Skillnaden gors av kontraktets EGET domsordforrad, inte av
    en lista i den har modulen.
    """
    assert O.statusgrupp("TIMING", "EDGE") is None
    assert O.statusgrupp("LIMITS", "RESOLUTION") is None
    assert O.statusgrupp("TIMING", "DWELL") is not None
    assert "RISE" not in O.DOMSORD and "RUN" not in O.DOMSORD


# ---- ordlistan pa fel storhet -------------------------------------------

def test_den_naiva_domaren_fyrar_pa_fel_storhet():
    """TRASIG FIXTUR. Att den naiva domaren har fel ar sjalva matningen.

    Utan det har provet vore var egen regel bara ett pastaende: att en
    delstrangsmatchning duger. Har ar de tva raderna dar den inte gor det.
    """
    parnamn = "MINDIST OK_ROBOT+STANGSEL 412.000mm t=1.200s"
    signalnamn = "STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s"
    assert FX.naiv_ok(parnamn) is True
    assert FX.naiv_ok(signalnamn) is True

    # Var domare: parnamnsraden har ingen dom alls, signalnamnsraden ar ett
    # fynd. Ingen av dem far raknas som godkand.
    assert O.status("SAFETY", parnamn) is None
    assert O.ar_fynd("SEQUENCE", signalnamn) is True


def test_en_sektion_med_ett_fynd_trimmas_inte_ens_delvis():
    """Sektionen med STEP MISSING ror trimningen aldrig, hur trang budgeten
    an ar. En sektion med en enda avvikelse gar fram HEL."""
    rapport = FX.rapport_med_ok_i_namn()
    trimmad, notiser = O.trimma(rapport, 400)
    assert "STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s" in trimmad
    assert all(n.sektion != "SEQUENCE" for n in notiser), notiser
    assert O.granska(rapport, trimmad) == []


def test_safety_raden_med_minsta_avstandet_star_kvar():
    """En MINDIST-rad ar ett AVSTAND. Trimmar man bort den minsta har man
    tappat just den storhet raden finns for att bara, och det som star kvar
    ser ut som en tryggare korning an den var."""
    rapport = FX.rapport_med_ok_i_namn(antal_mindist=12)
    trimmad, notiser = O.trimma(rapport, 500)
    assert "MINDIST kritiska_paret 12.000mm t=9.000s" in trimmad
    assert any(n.sektion == "SAFETY" for n in notiser), notiser
    assert O.granska(rapport, trimmad) == []


def test_kontrollen_faller_nar_den_minsta_raden_tas_bort():
    """TRASIG FIXTUR for provet ovan: samma domare, en riggad utdata."""
    rapport = FX.rapport_med_ok_i_namn(antal_mindist=12)
    riggad = "\n".join(
        r for r in rapport.splitlines()
        if "MINDIST kritiska_paret" not in r) + "\n"
    koder = O.granska(rapport, riggad)
    assert any(O.O2_FYND_BORTA in k for k in koder), koder


# ---- ordagrannheten -----------------------------------------------------

def test_domsraden_och_varje_rad_gar_fram_ordagrant():
    rapport = FX.lang_rapport()
    trimmad, notiser = O.trimma(rapport, 1200)
    assert notiser, "taket bet inte; provet mater ingenting"
    original = [r.strip() for r in rapport.splitlines() if r.strip()]
    for rad in trimmad.splitlines():
        assert rad.strip() in original, rad
    assert trimmad.splitlines()[0] == rapport.splitlines()[0]
    assert trimmad.strip().splitlines()[-1] == rapport.strip().splitlines()[-1]
    assert O.granska(rapport, trimmad) == []


def test_noteringen_ligger_utanfor_ogats_block():
    """En inskjuten rad INNE i blocket gor rapporten olasbar for
    `oga_kontrakt.las()`, som kastar pa ett okant nyckelord i en kand sektion.
    En sammanfattning som gor domen olasbar ar varre an ingen alls."""
    rapport = FX.lang_rapport()
    trimmad, notiser = O.trimma(rapport, 1200)
    helheten = O.block(trimmad, notiser)
    K.las(trimmad)                       # rapporten sjalv ar fortfarande lasbar
    rader = helheten.strip().splitlines()
    dom = [i for i, r in enumerate(rader) if r.startswith("EYES VERDICT")][0]
    assert dom == len(rader) - 1 - len(notiser)
    for n in notiser:
        assert n.rad() in helheten


def test_honesty_och_limits_trimmas_aldrig():
    """HONESTY: dess franvaro gar inte att skilja fran att den aldrig kordes.
    LIMITS: vad ogat INTE ser, och grinden kraver sektionen (M-65 §6)."""
    rapport = FX.lang_rapport(antal_edge=400, antal_mindist=80)
    trimmad, _n = O.trimma(rapport, 300)
    for sektion in O.ALDRIG_TRIMMADE:
        for rad in K.las(rapport).rader_i(sektion):
            assert rad in trimmad, (sektion, rad)


def test_en_omskriven_domsrad_falls():
    """TRASIG FIXTUR. Sammanfattaren som formulerar om domen."""
    rapport = FX.lang_rapport()
    riggad = rapport.replace("EYES VERDICT PASS allt inom marginal",
                             "EYES VERDICT PASS allt sag bra ut")
    koder = O.granska(rapport, riggad)
    assert any(O.O4_OMSKRIVEN_RAD in k or O.O1_DOM_BORTA in k for k in koder), \
        koder


def test_en_bortklippt_honestysektion_falls():
    """TRASIG FIXTUR."""
    rapport = FX.lang_rapport()
    riggad = "\n".join(r for r in rapport.splitlines()
                       if "TELEPORT_TRANSFER" not in r) + "\n"
    koder = O.granska(rapport, riggad)
    assert any(O.O3_SKYDDAD_SEKTION in k for k in koder), koder


def test_en_rapport_som_inte_gar_att_lasa_trimmas_inte_alls():
    """Fail-closed: en rapport vi inte kan lasa ror vi inte."""
    with pytest.raises(K.Kontraktsfel):
        O.trimma("EYES v2\nnagot helt annat\n", 10)


def test_bankens_riktiga_rapporter_gar_igenom_utan_anmarkning():
    """Kontrollen mot verkligheten: nio riktiga rapporter ur banken."""
    rapporter = FX.ogonrapporter()
    assert len(rapporter) >= 9, len(rapporter)
    for rapport in rapporter:
        trimmad, notiser = O.trimma(rapport, 10000)
        assert notiser == [] and trimmad == rapport, "rymdes redan"
        assert O.granska(rapport, rapport) == []
