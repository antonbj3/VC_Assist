# -*- coding: utf-8 -*-
"""L1 for verktygskedjans hamtare (install/verktygskedjan.py).

Inget nat. Nedladdningen attrapperas; det som provas ar KONTROLLEN, som ar
hela poangen med modulen.
"""
import hashlib
import os
import sys
import tarfile
import zipfile

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROT)

from install import verktygskedjan as V                          # noqa: E402


def _post(sokvag, sort="tar"):
    data = open(sokvag, "rb").read()
    return V.Post("p", "http://exempel/p", hashlib.sha256(data).hexdigest(),
                  len(data), sort, "ingenting")


# ---- kontrollen ------------------------------------------------------------

def test_en_fil_som_stammer_godkanns(tmp_path):
    f = tmp_path / "p"
    f.write_bytes(b"exakt det har")
    assert V.kontrollera(str(f), _post(str(f))) is True


def test_en_manipulerad_fil_falls_OCH_tas_bort(tmp_path):
    """Att lamna kvar en fil som inte stammer ar att bjuda in nasta korning."""
    f = tmp_path / "p"
    f.write_bytes(b"exakt det har")
    post = _post(str(f))
    f.write_bytes(b"nagot helt annat")
    with pytest.raises(V.Kedjefel) as e:
        V.kontrollera(str(f), post)
    assert "stammer inte" in str(e.value)
    assert not f.exists(), "filen ligger kvar och kan anvandas av nasta korning"


def test_ratt_hash_men_fel_storlek_falls(tmp_path):
    """Bada matten kravs. Ett av dem ensamt ar en svagare grind."""
    f = tmp_path / "p"
    f.write_bytes(b"abc")
    post = _post(str(f))
    post.storlek = 999
    with pytest.raises(V.Kedjefel):
        V.kontrollera(str(f), post)


# ---- manifestet ------------------------------------------------------------

def test_varje_post_bar_en_full_sha256_och_en_storlek():
    for nyckel, post in V.MANIFEST.items():
        assert len(post.sha256) == 64, nyckel
        assert int(post.sha256, 16) >= 0, nyckel
        assert post.storlek > 0, nyckel
        assert V.STRUCPP_VERSION in post.url or post.namn in post.url, nyckel


def test_windowsposterna_ar_identiska_och_det_star_som_varning():
    """MATT: bada Windows-paketen i v0.6.6 ar byte-identiska x64-byggen.

    Provet finns for att fyndet inte ska tappas bort tyst nasta gang nagon
    uppdaterar manifestet. Slutar de vara identiska ar det en NY matning, och
    da ska varningen bort - men det ska vara ett medvetet beslut.
    """
    x64 = V.MANIFEST["win32-x64"]
    arm = V.MANIFEST["win32-arm64"]
    assert x64.sha256 == arm.sha256
    assert x64.storlek == arm.storlek
    assert arm.varning and "ARM64" in arm.varning


def test_openplcavbilden_ar_last_till_en_digest_inte_en_tagg():
    """En tagg ar inget lofte. Digesten ar det."""
    assert "@sha256:" in V.OPENPLC_AVBILD
    assert ":latest" not in V.OPENPLC_AVBILD


# ---- plattformsvalet -------------------------------------------------------

@pytest.mark.parametrize("plattform,maskin,vantat", [
    ("linux", "x86_64", "linux-x64"),
    ("linux", "aarch64", "linux-arm64"),
    ("win32", "AMD64", "win32-x64"),
    ("darwin", "arm64", "darwin-arm64"),
])
def test_plattformsnyckeln(plattform, maskin, vantat):
    assert V.plattformsnyckel(plattform, maskin) == vantat


def test_en_okand_plattform_gissar_inte(tmp_path):
    """Att gissa 'det ar nog linux-x64' ar att hamta fel binar."""
    with pytest.raises(V.Kedjefel):
        V.plattformsnyckel("freebsd", "x86_64")
    with pytest.raises(V.Kedjefel):
        V.plattformsnyckel("linux", "riscv64")


# ---- uppackningen ----------------------------------------------------------

def test_en_arkivpost_som_pekar_utanfor_malet_avvisas(tmp_path):
    """tarfile gor det glatt om ingen sager ifran."""
    inne = tmp_path / "inne"
    inne.mkdir()
    (inne / "ofarlig").write_text("hej")
    arkiv = tmp_path / "elak.tar.gz"
    with tarfile.open(str(arkiv), "w:gz") as t:
        t.add(str(inne / "ofarlig"), arcname="../utanfor")
    with pytest.raises(V.Kedjefel) as e:
        V.packa_upp(str(arkiv), _post(str(arkiv)), str(tmp_path / "mal"))
    assert "utanfor" in str(e.value)


def test_ett_zip_som_pekar_utanfor_malet_avvisas(tmp_path):
    arkiv = tmp_path / "elak.zip"
    with zipfile.ZipFile(str(arkiv), "w") as z:
        z.writestr("../utanfor", "hej")
    with pytest.raises(V.Kedjefel):
        V.packa_upp(str(arkiv), _post(str(arkiv), "zip"), str(tmp_path / "mal"))


def test_ett_vanligt_arkiv_packas_upp(tmp_path):
    arkiv = tmp_path / "ok.tar.gz"
    fil = tmp_path / "a.txt"
    fil.write_text("innehall")
    with tarfile.open(str(arkiv), "w:gz") as t:
        t.add(str(fil), arcname="paket/a.txt")
    mal = V.packa_upp(str(arkiv), _post(str(arkiv)), str(tmp_path / "mal"))
    assert os.path.exists(os.path.join(mal, "paket", "a.txt"))


# ---- hamtningen ------------------------------------------------------------

def test_en_redan_hamtad_fil_kontrolleras_anda(tmp_path, monkeypatch):
    """En cache som inte kontrolleras ar en cache som kan bara skrap."""
    post = V.MANIFEST["npm"]
    f = tmp_path / post.namn
    f.write_bytes(b"fel innehall")
    with pytest.raises(V.Kedjefel):
        V.hamta("npm", str(tmp_path), skriv=lambda *_a: None)
    assert not f.exists()


def test_okand_post_gissar_inte(tmp_path):
    with pytest.raises(V.Kedjefel):
        V.hamta("finns-inte", str(tmp_path), skriv=lambda *_a: None)


# ---- lasfilen --------------------------------------------------------------

def test_lasfilen_finns_och_bar_integritetshashar():
    """Paketet levereras UTAN las och med ett INTERVALL som beroende.

    Utan den vendorade lasfilen hamtar npm vad som rakar vara senast, och da ar
    hela hashkontrollen ovan meningslos: kedjan byter egenskaper under oss anda.
    """
    import json
    assert os.path.exists(V.LASFIL), V.LASFIL
    las = json.load(open(V.LASFIL, encoding="utf-8"))
    paket = las.get("packages", {})
    assert len(paket) > 1
    med = [k for k, v in paket.items() if v.get("integrity")]
    assert len(med) >= len(paket) - 1, "poster utan integritetshash"


def test_lasfilen_spikar_chevrotain_till_ett_nummer():
    import json
    las = json.load(open(V.LASFIL, encoding="utf-8"))
    post = las["packages"].get("node_modules/chevrotain")
    assert post is not None, "chevrotain saknas i lasen"
    assert post["version"].count(".") == 2, post["version"]
    assert not any(c in post["version"] for c in "^~*"), post["version"]
    assert post.get("integrity", "").startswith("sha512-")


def test_utan_lasfil_installeras_inga_beroenden(tmp_path, monkeypatch):
    """Fail-closed: hellre inget an ett olast npm install."""
    monkeypatch.setattr(V, "LASFIL", str(tmp_path / "finns-inte.json"))
    with pytest.raises(V.Kedjefel) as e:
        V.installera_beroenden(str(tmp_path), skriv=lambda *_a: None)
    assert "lasfilen saknas" in str(e.value)
