# -*- coding: utf-8 -*-
"""L1 for uppslagsverktyget. Det ar modellens enda tillatna vag in i repot.

Verktyget finns for M-84, matningen som jamfor en modell MED API-uppslag mot en
UTAN (M-82). Jamforelsens giltighet star pa att verktyget svarar pa API-fragor
och pa ingenting annat: en modell som kan lasa repot ser facit.
"""
import json
import os
import subprocess
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SLAUPP = os.path.join(_ROT, "tests", "protocol", "stod", "slaupp.py")


def kor(*argv, **kw):
    return subprocess.run([sys.executable, _SLAUPP] + list(argv),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          cwd=kw.get("cwd") or _ROT, timeout=120)


def test_slar_upp_ett_namn_med_signatur_och_returtyp():
    r = kor("namn", "vcApplication.load")
    assert r.returncode == 0
    d = json.loads(r.stdout.decode("utf-8"))
    assert d["found"] is True
    s = d["symbols"][0]
    assert s["signature"] == "String uri"
    assert s["value_type"] == "vcComponent"
    assert "returns the component" in s["description"]


def test_fungerar_fran_en_annan_katalog():
    """Repots rot harleds ur filens plats, inte ur arbetskatalogen.

    Trasig fixtur for just det: forsta versionen gick TVA niva upp i stallet
    for tre, och felet syntes som "No module named vc_assist_svc" i
    underprocessen - alltsa langt fran orsaken.
    """
    import tempfile
    r = kor("namn", "vcApplication.load", cwd=tempfile.gettempdir())
    assert r.returncode == 0
    assert json.loads(r.stdout.decode("utf-8"))["found"] is True


def test_ett_okant_namn_sager_att_det_inte_finns():
    r = kor("namn", "vcApplication.hittepaMetod")
    d = json.loads(r.stdout.decode("utf-8"))
    assert d["found"] is False


def test_sokning_och_typyta_svarar():
    assert json.loads(kor("sok", "interface").stdout.decode("utf-8"))["traffar"]
    assert json.loads(kor("yta", "vcMatrix").stdout.decode("utf-8"))


def test_en_okand_fragesort_avvisas():
    """Verktyget far inte gora nagot annat an de tre fragorna."""
    r = kor("las", "/etc/passwd")
    assert r.returncode == 2
    assert b"passwd" not in r.stdout


def test_fel_antal_argument_avvisas():
    assert kor("namn").returncode == 2
    assert kor("namn", "a", "b").returncode == 2


# --- att en KOPIA av verktyget ocksa hittar repot (M-84) ----------------------
#
# Trasig fixtur for ett fel som en riktig korning gick pa: verktyget kopierades
# till en scratchpad, och "tre niva upp ur filens plats" pekade da pa
# sessionskatalogen. Underprocessen dog pa "No module named vc_assist_svc" -
# ett fel som inte namner sin orsak och inte sager vad man ska gora.

def kor_kopia(tmp_path, *argv, **kw):
    kopia = tmp_path / "slaupp.py"
    kopia.write_bytes(open(_SLAUPP, "rb").read())
    miljo = dict(os.environ)
    miljo.pop("VC_ASSIST_REPO", None)
    miljo.update(kw.get("env") or {})
    return subprocess.run([sys.executable, str(kopia)] + list(argv),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          cwd=kw.get("cwd") or str(tmp_path), env=miljo,
                          timeout=120)


def test_kopia_utanfor_repot_sager_vad_som_saknas(tmp_path):
    r = kor_kopia(tmp_path, "namn", "vcApplication.load")
    ut = r.stdout.decode("utf-8")
    assert r.returncode == 2
    assert "VC_ASSIST_REPO" in ut
    assert "ModuleNotFoundError" not in ut, "felet far inte komma ur underprocessen"


def test_kopia_hittar_repot_ur_miljon(tmp_path):
    r = kor_kopia(tmp_path, "namn", "vcApplication.load",
                  env={"VC_ASSIST_REPO": _ROT})
    assert r.returncode == 0
    assert json.loads(r.stdout.decode("utf-8"))["found"] is True


def test_kopia_hittar_repot_genom_att_leta_uppat_fran_arbetskatalogen(tmp_path):
    """Star man NAGONSTANS i repot racker det, aven om verktyget ligger ute."""
    djupt = os.path.join(_ROT, "svc", "vc_assist_svc")
    r = kor_kopia(tmp_path, "namn", "vcApplication.load", cwd=djupt)
    assert r.returncode == 0
    assert json.loads(r.stdout.decode("utf-8"))["found"] is True


def test_en_pekare_till_fel_katalog_i_miljon_avvisas(tmp_path):
    """VC_ASSIST_REPO provas mot svc/vc_assist_svc, inte bara mot att den finns.

    En pekare som accepteras utan prov hade gett samma importfel igen, fast med
    en miljovariabel att skylla pa.
    """
    r = kor_kopia(tmp_path, "namn", "vcApplication.load",
                  env={"VC_ASSIST_REPO": str(tmp_path)})
    assert r.returncode == 2
    assert "VC_ASSIST_REPO" in r.stdout.decode("utf-8")


# --- komponentfragorna (M-85) -------------------------------------------------
#
# `komponent` och `komponentsok` stanger halet M-84 namngav: API-indexet
# tacker symbolerna men inte per-komponent-data. De anropar befintliga
# handlers - component_datasheet och search_installed_library - precis som de
# tre aldre fragorna, sa att verktyget fortfarande inte ar en vag in i repot.
#
# Proven nedan domer FORMEN, inte att just den har maskinen har ett bibliotek
# installerat. Utan bibliotek svarar handlaren funnet=false med ett skal, och
# det ar ett giltigt svar - ett tomt svar utan skal ar det inte.

def _svar(*argv):
    r = kor(*argv)
    assert r.returncode == 0, r.stdout.decode("utf-8")
    return json.loads(r.stdout.decode("utf-8"))


# Varje anrop som ror det installerade biblioteket bygger ett DJUPT index i sin
# egen underprocess, och det kostar tio sekunder (M-69). Fixturerna ar darfor
# module-scopade: tre bygganden i stallet for fem, och proven delar svaren.
@pytest.fixture(scope="module")
def komponentsvar():
    return _svar("komponent", "IRB 1200-5/0.9")


@pytest.fixture(scope="module")
def okant_komponentsvar():
    return _svar("komponent", "den har komponenten finns inte")


@pytest.fixture(scope="module")
def komponentsoksvar():
    return _svar("komponentsok", "conveyor")


def test_kapning_ger_giltig_json(komponentsvar, komponentsoksvar):
    """Kapningen far ALDRIG skiva mitt i en struktur.

    Det felet ar redan gjort en gang har: svaret kapades pa TECKEN, vilket gav
    utdata som var lasbar for ett oga och oparsbar for allt annat. Provet
    galler alla fem fragorna - `json.loads` ar hela domen, och den kan inte
    passera pa en halv struktur.
    """
    svar = [_svar("sok", "interface"), _svar("yta", "vcComponent"),
            _svar("namn", "vcApplication.load"), komponentsoksvar,
            komponentsvar]
    for d in svar:
        assert isinstance(d, dict)
        if "kapat" in d:
            # Kapningen sager hur mycket den inte visade, och listan den
            # kapade ar fortfarande en lista av HELA poster.
            assert " av " in d["kapat"]
            for nyckel in ("symbols", "traffar", "medlemmar", "members"):
                if nyckel in d:
                    assert all(isinstance(x, (dict, str)) for x in d[nyckel])


def test_komponentfragan_svarar_med_ett_datablad_eller_ett_skal(komponentsvar):
    d = komponentsvar
    assert "funnet" in d
    if not d["funnet"]:
        assert d["notering"], "ett nej utan skal ar inte ett svar"
        return
    assert isinstance(d["datablad"], list), \
        "databladet ska vara RADER, inte en strang med escapade radbrytningar"
    assert d["datablad"][0].startswith("KOMPONENT: ")
    assert isinstance(d["egenskapsnamn"], list)
    assert isinstance(d["boolska_signaler"], list)


def test_komponentfragan_pa_ett_okant_namn_ger_ett_nej_med_skal(
        okant_komponentsvar):
    d = okant_komponentsvar
    assert d["funnet"] is False
    assert d["notering"]
    assert d["datablad"] is None


def test_komponentsok_svarar_med_traffar_eller_ett_skal(komponentsoksvar):
    d = komponentsoksvar
    assert "antal" in d and "traffar" in d
    if d["antal"] == 0:
        assert d["notering"] or d["kalla"] == "inget bibliotek"


def test_de_gamla_tre_fragorna_svarar_som_forut():
    """Att fragorna blev fem far inte andra vad de tre forsta ger.

    M-84 mattes med de tre, och en tyst formandring hade gjort matningen
    ojamforbar med sin egen uppfoljning.
    """
    assert _svar("namn", "vcApplication.load")["found"] is True
    assert _svar("sok", "interface")["traffar"]
    assert _svar("yta", "vcMatrix")


def test_fortfarande_bara_de_fem_fragorna():
    for okand in ("las", "komponentdatablad", "eval", "komponent2"):
        assert kor(okand, "x").returncode == 2
