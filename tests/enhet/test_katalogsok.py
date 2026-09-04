# -*- coding: utf-8 -*-
"""L1 for sokskiktet. Formen ar det som provas, inte att maskinen har ett index."""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.katalogsok import (BRED_FRAGA, Katalog, SAKNAS,  # noqa: E402
                                      Sokfel, Traff)


def index(n_robotar=3, djupt=True):
    poster = [{"namn": "IRB %d" % (100 + i), "tillverkare": "ABB",
               "kategori": "Robots", "sokvag": "/x/%d.vcmx" % i,
               "granssnitt": 2, "familj": "robot",
               "parametrar": {"MaxSpeed": "180"}}
              for i in range(n_robotar)]
    poster.append({"namn": "mk1", "tillverkare": "Qimarox",
                   "kategori": "Conveyors", "sokvag": "/x/mk1.vcmx",
                   "granssnitt": 4, "familj": "transportor",
                   "parametrar": {"ConveyorLength": "500"}})
    # En transportor som ligger i FEL katalog. MATT (M-69): 182 av 227
    # transportorer gor det, och ett filter pa katalognamn missar dem alla.
    poster.append({"namn": "gomd", "tillverkare": "Qimarox",
                   "kategori": "Legacy", "sokvag": "/x/gomd.vcmx",
                   "granssnitt": 2, "familj": "transportor",
                   "parametrar": {}})
    return {"format": 1, "rot": "/x", "djupt": djupt, "poster": poster}


def kat(**kw):
    return Katalog.fran_index(index(**kw))


# ---- formen pa svaret ------------------------------------------------------

def test_svaret_sager_alltid_hur_mycket_det_INTE_visade():
    """Ett svar som inte sager det ser uttommande ut."""
    s = kat(n_robotar=25).sok(kategori="Robots", max_rader=3)
    assert "25 traffar, visar 3." in s.text()
    assert "22 till, ej visade" in s.text()


def test_en_bred_fraga_ger_sammandrag_i_stallet_for_lista():
    s = kat(n_robotar=BRED_FRAGA + 5).sok(kategori="Robots")
    t = s.text()
    assert "for manga for en lista" in t
    assert "Fordelning per tillverkare" in t
    assert s.visade == 0
    assert "IRB 100" not in t, "en bred fraga ska inte radda upp traffarna"


def test_noll_traffar_sager_noll_och_vilken_fraga():
    s = kat().sok(fraga="finns-inte")
    assert s.totalt == 0
    assert "0 traffar" in s.text() and "finns-inte" in s.text()


def test_traffraden_ar_rader_inte_json():
    s = kat().sok(tillverkare="Qimarox")
    rad = s.traffar[0].rad()
    assert "{" not in rad and '"' not in rad
    assert "Qimarox" in rad and "mk1" in rad


def test_saknade_falt_sags_SAKNAS_aldrig_noll_eller_tomt():
    """Fyra falt kan saknas: tillverkare, familj, kategori och granssnitt."""
    t = Traff(namn="X", tillverkare="", kategori="", sokvag="/x", granssnitt=0)
    assert t.rad().count(SAKNAS) == 4
    assert "0" not in t.rad()


def test_ett_grunt_index_sager_att_parametrar_saknas():
    k = Katalog.fran_index({"format": 1, "djupt": False, "rot": "/x",
                            "poster": [{"namn": "X", "tillverkare": "A",
                                        "kategori": "R", "sokvag": "/x"}]})
    assert SAKNAS in k.med_namn("X").fullt()
    assert "grunt lage" in k.med_namn("X").fullt()


def test_oversikten_sager_om_kategorin_kommer_fran_katalognamnet():
    """M-58: i grunt lage ar kategorin katalognamnet, inte metadatans falt."""
    grunt = Katalog.fran_index(index(djupt=False)).oversikt()
    assert "M-58" in grunt and "M-69" in grunt
    assert "familjen saknas" in grunt
    assert "parametrar och familj ingar" in kat().oversikt()


# ---- sokningen -------------------------------------------------------------

def test_namnsokning_ar_delstrang_och_skiftlagesokanslig():
    assert kat().sok(fraga="irb 10").totalt == 3


def test_tillverkare_och_kategori_ar_exakta():
    assert kat().sok(tillverkare="ABB").totalt == 3
    assert kat().sok(tillverkare="AB").totalt == 0, "delstrang far inte gälla har"


def test_kortast_namn_forst():
    k = Katalog.fran_index({"format": 1, "djupt": True, "rot": "/x", "poster": [
        {"namn": "IRB 120-3/0.6 LID", "tillverkare": "ABB", "kategori": "R",
         "sokvag": "/a"},
        {"namn": "IRB 120", "tillverkare": "ABB", "kategori": "R", "sokvag": "/b"}]})
    assert k.sok(fraga="IRB 120").traffar[0].namn == "IRB 120"


def test_sokning_pa_parameternamn():
    assert kat().sok(har_parameter="conveyor").totalt == 1
    assert kat().sok(har_parameter="finns-inte").totalt == 0


def test_ett_trasigt_index_avvisas():
    with pytest.raises(Sokfel):
        Katalog.fran_index({"nagot": "annat"})
    with pytest.raises(Sokfel):
        Katalog.las_fil("/finns/inte/index.json")


# ---- kostnaden -------------------------------------------------------------

def test_ett_svar_ryms_i_kontextbudgeten():
    """MATT i M-60. Faller det har provet har svaret vuxit ifran sin post."""
    for kw in (dict(fraga="IRB"), dict(kategori="Robots"), dict()):
        assert kat(n_robotar=BRED_FRAGA + 5).sok(**kw).tecken() < 2000, kw


# ---- familjen ar det sanna mattet (M-69) -----------------------------------

def test_familjefiltret_hittar_den_som_ligger_i_fel_katalog():
    """MATT: 182 av 227 transportorer ligger utanfor katalogen Conveyors."""
    k = kat()
    assert k.sok(kategori="Conveyors").totalt == 1
    assert k.sok(familj="transportor").totalt == 2


def test_familjen_star_fore_kategorin_pa_raden():
    """Den sanna storheten forst, den harledda efter."""
    rad = kat().sok(fraga="gomd").traffar[0].rad()
    assert rad.index("transportor") < rad.index("Legacy")


def test_familjer_raknas_per_familj():
    assert kat().familjer() == {"robot": 3, "transportor": 2}


def test_ett_grunt_index_har_ingen_familj_alls():
    """Familjen ligger vid median 14 kB och nas inte av en huvudlasning."""
    k = Katalog.fran_index({"format": 1, "djupt": False, "rot": "/x",
                            "poster": [{"namn": "X", "tillverkare": "A",
                                        "kategori": "Robots", "sokvag": "/x"}]})
    assert k.familjer() == {"": 1}
    assert k.sok(familj="robot").totalt == 0
