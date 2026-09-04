# -*- coding: utf-8 -*-
"""L1 for katalogindexet. Ingen VC, inget riktigt bibliotek.

Biblioteket attrapperas som riktiga .vcmx: zip-arkiv med en component.rsc i
VC:s eget textformat. Det som provas ar UPPTACKTEN och LASNINGEN, inte att
just den har maskinen har ett bibliotek.
"""
import json
import os
import sys
import zipfile

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import katalogindex as K                      # noqa: E402


RSC = '''VCMD0028041000000000COMPONENT
Node "rSimResource"
{
Name "%(namn)s"
Category  "%(kategori)s"
VariableSpace
{
  Variable "rTVariable<rDouble>"
  {
    Name "ConveyorLength"
    Value 500
  }
  Variable "rTVariable<rDouble>"
  {
    Name "BrepChordHeightRatio"
    Value 0.1
  }
}
%(granssnitt)s
}
'''


def gor_komponent(sokvag, namn="Del", kategori="Robots", granssnitt=2):
    os.makedirs(os.path.dirname(sokvag), exist_ok=True)
    with zipfile.ZipFile(sokvag, "w") as z:
        z.writestr("component.rsc", RSC % {
            "namn": namn, "kategori": kategori,
            "granssnitt": "\n".join(["rSimInterface"] * granssnitt)})
        z.writestr("geo-1", b"\x00\x01")


def bibliotek(tmp_path, version="4.10"):
    rot = tmp_path / "Documents" / "Visual Components" / version / "Models" / "Components"
    gor_komponent(str(rot / "ABB" / "Robots" / "IRB 6700.vcmx"), "IRB 6700", "Robots")
    gor_komponent(str(rot / "ABB" / "Robots" / "IRB 120.vcmx"), "IRB 120", "Robots")
    gor_komponent(str(rot / "Qimarox" / "Conveyors" / "mk1.vcmx"), "Prorunner mk1",
                  "Conveyors", granssnitt=5)
    return rot


# ---- upptackten ------------------------------------------------------------

def test_hittar_biblioteket_och_sager_hur(tmp_path):
    bibliotek(tmp_path)
    fynd = K.hitta([(str(tmp_path / "Documents"), "provrot")])
    assert len(fynd) == 1
    assert "provrot" in fynd[0].hur and "4.10" in fynd[0].hur


def test_tva_versioner_ger_TVA_fynd(tmp_path):
    """Vilken som ska anvandas ar inte indexbyggarens beslut."""
    bibliotek(tmp_path, "4.10")
    bibliotek(tmp_path, "4.9")
    fynd = K.hitta([(str(tmp_path / "Documents"), "provrot")])
    assert len(fynd) == 2
    assert {"4.10", "4.9"} == set(f.hur.split("version ")[1] for f in fynd)


def test_inget_bibliotek_ger_TOMT_inte_en_gissad_sokvag(tmp_path):
    assert K.hitta([(str(tmp_path / "finns-inte"), "provrot")]) == []


def test_kandidatrotterna_bar_ett_skal_var():
    for sokvag, hur in K.kandidatrotter("/hem/nagon"):
        assert sokvag and hur, (sokvag, hur)


# ---- lasningen -------------------------------------------------------------

def test_bygger_index_med_namn_tillverkare_och_kategori(tmp_path):
    rot = bibliotek(tmp_path)
    ix = K.bygg(str(rot))
    assert ix["antal"] == 3
    assert ix["tillverkare"] == ["ABB", "Qimarox"]
    namn = sorted(p["namn"] for p in ix["poster"])
    assert namn == ["IRB 120", "IRB 6700", "Prorunner mk1"]
    assert all(p["kategori"] in ("Robots", "Conveyors") for p in ix["poster"])


def test_grunt_lage_laser_inga_parametrar(tmp_path):
    """Namnet racker for att veta VAD som finns; parametrar kostar mer."""
    ix = K.bygg(str(bibliotek(tmp_path)))
    assert all(not p.get("parametrar") for p in ix["poster"])
    assert all(p["granssnitt"] == 0 for p in ix["poster"])


def test_djupt_lage_ger_parametrar_och_granssnitt(tmp_path):
    ix = K.bygg(str(bibliotek(tmp_path)), djupt=True)
    mk1 = [p for p in ix["poster"] if p["namn"] == "Prorunner mk1"][0]
    assert mk1["granssnitt"] == 5
    assert mk1["parametrar"]["ConveyorLength"] == "500"


def test_ritparametrar_dranker_inte_indexet(tmp_path):
    """MATT: sju parametrar finns i 3193 av 3201 och sager darfor ingenting."""
    ix = K.bygg(str(bibliotek(tmp_path)), djupt=True)
    for p in ix["poster"]:
        assert not any("Brep" in k for k in p.get("parametrar", {})), p["namn"]


def test_en_trasig_vcmx_raknas_som_olaslig_i_stallet_for_att_tigas_bort(tmp_path):
    """Tystnad ar aldrig ett godkannande, inte heller har."""
    rot = bibliotek(tmp_path)
    trasig = rot / "ABB" / "Robots" / "trasig.vcmx"
    trasig.write_bytes(b"det har ar inte ett zip-arkiv")
    ix = K.bygg(str(rot))
    assert ix["antal"] == 3
    assert len(ix["olasliga"]) == 1
    assert "trasig.vcmx" in ix["olasliga"][0]


def test_en_vcmx_utan_metadata_ar_olaslig(tmp_path):
    rot = bibliotek(tmp_path)
    tom = rot / "ABB" / "Robots" / "utan.vcmx"
    with zipfile.ZipFile(str(tom), "w") as z:
        z.writestr("geo-1", b"\x00")
    ix = K.bygg(str(rot))
    assert len(ix["olasliga"]) == 1


def test_saknad_rot_falls(tmp_path):
    with pytest.raises(K.Katalogfel):
        K.bygg(str(tmp_path / "finns-inte"))


def test_indexet_gar_att_skriva_och_lasa(tmp_path):
    ix = K.bygg(str(bibliotek(tmp_path)), djupt=True)
    ut = tmp_path / "index.json"
    K.skriv_fil(ix, str(ut))
    igen = json.load(open(str(ut), encoding="utf-8"))
    assert igen["antal"] == ix["antal"]
    assert igen["format"] == K.FORMAT
