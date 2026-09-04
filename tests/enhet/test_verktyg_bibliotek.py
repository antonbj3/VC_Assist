# -*- coding: utf-8 -*-
"""L1 for de tva verktygen mot det INSTALLERADE biblioteket.

Ingen VC och inget riktigt bibliotek: upptackten attrapperas, sa proven kor
likadant pa en maskin utan VC installerat.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

import vc_assist_svc.verktyg as V                                  # noqa: E402
from vc_assist_svc import katalogindex as KI                       # noqa: E402
from vc_assist_svc.verktyg import katalog as KT                    # noqa: E402


def poster(n_robotar=3):
    ut = [{"namn": "IRB %d" % (100 + i), "tillverkare": "ABB",
           "kategori": "Robots", "sokvag": "/x/%d.vcmx" % i,
           "granssnitt": 2, "familj": "robot",
           "parametrar": {"MaxSpeed": "180"}}
          for i in range(n_robotar)]
    ut.append({"namn": "mk1", "tillverkare": "Qimarox", "kategori": "Conveyors",
               "sokvag": "/x/mk1.vcmx", "granssnitt": 4,
               "familj": "transportor", "parametrar": {}})
    return ut


@pytest.fixture
def bibliotek(monkeypatch):
    """Attrapperar upptackten OCH genomgangen. Ingen disk ror provet."""
    def stall(n_robotar=3, djupt=True):
        KT._nollstall_bibliotek()
        monkeypatch.setattr(KI, "hitta",
                            lambda *a, **k: [KI.Fynd("/x", "provrot, version 4.10")])
        monkeypatch.setattr(KI, "bygg",
                            lambda rot, **k: {"format": 1, "rot": rot,
                                              "djupt": djupt,
                                              "poster": poster(n_robotar)})
        return None
    yield stall
    KT._nollstall_bibliotek()


def sok(**kw):
    return V.DATA_HANDLERS["search_installed_library"](kw)


# ---- verktygen finns och ar data ------------------------------------------

def test_bada_verktygen_ar_registrerade_som_lasande_data():
    for namn in ("search_installed_library", "library_overview"):
        v = V.REGISTER[namn]
        assert v.mode == "data" and v.effect == "read", namn
        assert v.doman == "catalog", namn


def test_beskrivningen_skiljer_de_tva_kallorna_at():
    """En modell som inte vet vilken katalog den soker i valjer fel."""
    b = V.REGISTER["search_installed_library"].beskrivning
    assert "search_catalog" in b, "beskrivningen maste peka pa den andra kallan"
    assert "banken" in b.lower() or "bankens" in b.lower()


# ---- svaren ----------------------------------------------------------------

def test_oversikten_raknar_per_tillverkare_och_kategori(bibliotek):
    bibliotek()
    r = V.DATA_HANDLERS["library_overview"]({})
    assert r["antal"] == 4
    assert r["tillverkare"] == {"ABB": 3, "Qimarox": 1}
    assert r["kategorier"] == {"Robots": 3, "Conveyors": 1}
    assert "provrot" in r["kalla"]


def test_namnsokning_ger_filen_som_ska_laddas(bibliotek):
    bibliotek()
    s = sok(query="IRB 10")
    assert s["antal"] == 3
    assert all(t["fil"].endswith(".vcmx") for t in s["traffar"])


def test_en_bred_fraga_ger_sammandrag_och_INGEN_lista(bibliotek):
    """Att radda upp traffarna ar att branna kontexten pa det som inte fragades."""
    bibliotek(n_robotar=60)
    s = sok(category="Robots")
    assert s["antal"] == 60
    assert s["visade"] == 0
    assert s["traffar"] == []
    assert s["sammandrag"] == {"ABB": 60}
    assert "for manga" in s["notering"]


def test_svaret_sager_alltid_hur_mycket_det_inte_visade(bibliotek):
    bibliotek(n_robotar=25)
    s = sok(category="Robots", max_rows=5)
    assert s["visade"] == 5 and s["antal"] == 25
    assert "5 av 25" in s["notering"]


# ---- de trasiga fallen -----------------------------------------------------

def test_inget_bibliotek_ger_SKALET_inte_ett_tomt_lyckat_svar(monkeypatch):
    """Ett tomt bibliotek och ett bibliotek som inte hittades ar tva svar."""
    KT._nollstall_bibliotek()
    monkeypatch.setattr(KI, "hitta", lambda *a, **k: [])
    try:
        s = sok(query="vad som helst")
        assert s["antal"] == 0
        assert s["kalla"] == "inget bibliotek"
        assert s["notering"] and "hittades" in s["notering"]
        assert "Provade:" in s["notering"], "svaret ska saga VAR den letade"
    finally:
        KT._nollstall_bibliotek()


def test_ett_bibliotek_som_inte_gar_att_lasa_ger_skalet(monkeypatch):
    KT._nollstall_bibliotek()
    monkeypatch.setattr(KI, "hitta",
                        lambda *a, **k: [KI.Fynd("/x", "provrot, version 4.10")])
    def spricker(*a, **k):
        raise KI.Katalogfel("katalogen ar trasig")
    monkeypatch.setattr(KI, "bygg", spricker)
    try:
        s = sok()
        assert s["antal"] == 0
        assert "trasig" in s["notering"]
    finally:
        KT._nollstall_bibliotek()


def test_ett_grunt_index_sager_att_kategorin_kommer_fran_katalognamnet(bibliotek):
    """M-58: tva falt som nastan alltid ar lika ar tva falt, inte ett."""
    bibliotek(djupt=False)
    r = V.DATA_HANDLERS["library_overview"]({})
    assert r["notering"] and "M-58" in r["notering"]
    s = sok(query="IRB")
    assert all(t["granssnitt"] is None for t in s["traffar"]), \
        "ett grunt index har inte raknat granssnitt och far inte pasta noll"


def test_bankens_katalog_ar_ororda(bibliotek):
    """Bankens vokabular ar ett kontrakt. Det nya verktyget far inte rora det."""
    bibliotek()
    r = V.DATA_HANDLERS["search_catalog"]({})
    assert r["antal"] == 65


# ---- familjen ar det sanna mattet (M-69) -----------------------------------

def test_verktyget_filtrerar_pa_familj_och_inte_bara_pa_kategori(bibliotek,
                                                                 monkeypatch):
    """MATT: strukturen ger 227 transportorer, katalognamnet 58.

    Trasig fixtur for verktyget: en transportor i katalogen 'Legacy'. Ett
    filter pa kategori missar den; ett pa familj gor det inte.
    """
    KT._nollstall_bibliotek()
    monkeypatch.setattr(KI, "hitta",
                        lambda *a, **k: [KI.Fynd("/x", "provrot, version 4.10")])
    monkeypatch.setattr(KI, "bygg", lambda rot, **k: {
        "format": 1, "rot": rot, "djupt": True, "poster": [
            {"namn": "synlig", "tillverkare": "Q", "kategori": "Conveyors",
             "sokvag": "/x/a.vcmx", "granssnitt": 2, "familj": "transportor"},
            {"namn": "gomd", "tillverkare": "Q", "kategori": "Legacy",
             "sokvag": "/x/b.vcmx", "granssnitt": 2, "familj": "transportor"}]})
    try:
        assert sok(category="Conveyors")["antal"] == 1
        assert sok(family="transportor")["antal"] == 2
    finally:
        KT._nollstall_bibliotek()


def test_oversikten_bar_familjerna(bibliotek):
    bibliotek()
    r = V.DATA_HANDLERS["library_overview"]({})
    assert r["familjer"] == {"robot": 3, "transportor": 1}


def test_beskrivningen_sager_att_family_ska_foredras_framfor_category():
    """En modell som valjer category missar var fjarde robot."""
    v = V.REGISTER["search_installed_library"]
    fam = v.parameters["properties"]["family"]["description"]
    kat = v.parameters["properties"]["category"]["description"]
    assert "2202" in fam and "1736" in fam
    assert "Foredra family" in kat


def test_has_parameter_sager_att_det_ar_en_namnlista():
    """M-59: parameternamnen ar oscopeade och kommer ocksa ur geometrilador."""
    b = V.REGISTER["search_installed_library"].parameters
    assert "geometrilada" in b["properties"]["has_parameter"]["description"]
