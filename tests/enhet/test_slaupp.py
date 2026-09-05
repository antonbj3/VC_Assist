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
