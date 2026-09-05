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
