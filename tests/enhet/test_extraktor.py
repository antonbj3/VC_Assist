# -*- coding: utf-8 -*-
"""L1: Enhetsprov for E13 - extraktorn for API-yta och utgivningskontrollen."""
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "install"))

from install import extraktor


def test_extrahera_kopierar_filer(tmp_path):
    kalla = tmp_path / "Auto Complete"
    kalla.mkdir()
    (kalla / "api.xml").write_text("<api/>")
    (kalla / "constants.xml").write_text("<constants/>")
    (kalla / "readme.txt").write_text("ignore me")

    mal = tmp_path / "mal"
    kopierade = extraktor.extrahera(str(kalla), str(mal))
    assert "api.xml" in kopierade
    assert "constants.xml" in kopierade
    assert "readme.txt" not in kopierade
    assert os.path.isfile(os.path.join(str(mal), "api.xml"))


def test_extrahera_kastar_om_api_xml_saknas(tmp_path):
    kalla = tmp_path / "Auto Complete"
    kalla.mkdir()
    (kalla / "constants.xml").write_text("<constants/>")

    mal = tmp_path / "mal"
    with pytest.raises(extraktor.Extraktionsfel):
        extraktor.extrahera(str(kalla), str(mal))


def test_utgivningskontroll_slapper_igenom_rena_filer():
    rena = [
        "ext/vc_addon/vc_assist/__init__.py",
        "svc/vc_assist_svc/klient.py",
        "install/installera.py",
        "README.md",
    ]
    assert extraktor.granska_utgivningslista(rena) == []
    extraktor.verifiera_utgivning(rena)


def test_utgivningskontroll_avvisar_docs_referens_trasig_fixtur():
    """Trasig fixtur for E13: en docs/referens/-fil i utgivningen ska stoppa utgivningen."""
    oren = [
        "ext/vc_addon/vc_assist/__init__.py",
        "docs/referens/vc_api/api.xml",
        "docs/referens/vc_dotnet/Create3D.Shared.xml",
        "README.md",
    ]
    forbjudna = extraktor.granska_utgivningslista(oren)
    assert len(forbjudna) == 2
    assert "docs/referens/vc_api/api.xml" in forbjudna
    assert "docs/referens/vc_dotnet/Create3D.Shared.xml" in forbjudna

    with pytest.raises(extraktor.Extraktionsfel) as exc:
        extraktor.verifiera_utgivning(oren)
    assert "docs/referens/vc_api/api.xml" in str(exc.value)
