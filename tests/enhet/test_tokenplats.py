# -*- coding: utf-8 -*-
"""L1: tjansten hittar bryggans token pa BADA plattformarna.

Windows-grenen kors har pa Linux mot ett attrappträd, med plattformen och
miljon injicerade. Det ar en provning av grenen, inte av Windows.

Fore M-44 stod sokvagen som en literal i fyra provskript:
``~/.wine-vc-test/drive_c/users/anton/vc_assist_token``. Tre antaganden - att
det finns ett wine-prefix, vad det heter, och vad anvandaren heter - och alla
tre ar falska pa Windows.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), _ROT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from install import upptackt                              # noqa: E402
from vc_assist_svc import tokenplats                      # noqa: E402


def _skriv(sokvag, text="deadbeef", tid=None):
    mapp = os.path.dirname(sokvag)
    if not os.path.isdir(mapp):
        os.makedirs(mapp)
    with open(sokvag, "w") as f:
        f.write(text)
    if tid is not None:
        os.utime(sokvag, (tid, tid))
    return sokvag


def _wineprefix(hem, namn, anvandare=("anton",)):
    for a in anvandare:
        os.makedirs(os.path.join(str(hem), namn, "drive_c", "users", a))
    return os.path.join(str(hem), namn)


def _linuxmiljo(hem, **env):
    return upptackt.Miljo(plattform="linux", hem=str(hem), env=env)


def _windowsmiljo(hem, **env):
    return upptackt.Miljo(plattform="win32", hem=str(hem), env=env,
                          skalmapp=lambda: None)


# --------------------------------------------------------------------------
# Wine
# --------------------------------------------------------------------------

def test_wine_hittar_token_utan_att_kanna_till_prefixnamnet(tmp_path):
    """Prefixnamnet ar inte hardkodat - bara monstret ``~/.wine*``."""
    prefix = _wineprefix(tmp_path, ".wine-produktion-2027")
    vantat = _skriv(os.path.join(prefix, "drive_c", "users", "anton",
                                 "vc_assist_token"))
    assert tokenplats.tokenfil(_linuxmiljo(tmp_path)) == vantat


def test_ett_prefix_utanfor_hemmet_kraver_WINEPREFIX(tmp_path):
    """Gransen for sokningen, utskriven: ``upptackt.wineprefix`` listar
    ``$WINEPREFIX``, ``--prefix`` och ``~/.wine*``. Ett prefix som varken
    ligger i hemmet eller heter ``.wine*`` maste pekas ut."""
    annanstans = tmp_path / "srv"
    os.makedirs(str(annanstans))
    prefix = _wineprefix(annanstans, "vcprefix")
    vantat = _skriv(os.path.join(prefix, "drive_c", "users", "anton",
                                 "vc_assist_token"))
    with pytest.raises(tokenplats.TokenSaknas):
        tokenplats.tokenfil(_linuxmiljo(tmp_path))
    assert tokenplats.tokenfil(
        _linuxmiljo(tmp_path, WINEPREFIX=prefix)) == vantat


def test_wine_hoppar_over_public(tmp_path):
    prefix = _wineprefix(tmp_path, ".wine-vc", anvandare=("Public", "anton"))
    _skriv(os.path.join(prefix, "drive_c", "users", "Public", "vc_assist_token"))
    sokvagar = [s for s, _k in tokenplats.kandidater(_linuxmiljo(tmp_path))]
    assert not any("Public" in s for s in sokvagar)
    assert any(os.path.join("users", "anton") in s for s in sokvagar)


def test_senast_skrivna_prefixet_vinner(tmp_path):
    """Tva prefix med var sin brygga. Den som kordes sist ar den som lyssnar."""
    gammal = _skriv(os.path.join(_wineprefix(tmp_path, ".wine-vc"), "drive_c",
                                 "users", "anton", "vc_assist_token"),
                    "gammal", tid=1000.0)
    ny = _skriv(os.path.join(_wineprefix(tmp_path, ".wine-vc-test"), "drive_c",
                             "users", "anton", "vc_assist_token"),
                "ny", tid=2000.0)
    assert tokenplats.tokenfil(_linuxmiljo(tmp_path)) == ny
    assert gammal != ny


def test_ett_prefix_utan_drive_c_ar_inget_prefix(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), ".winerelaterat", "users", "anton"))
    with pytest.raises(tokenplats.TokenSaknas):
        tokenplats.tokenfil(_linuxmiljo(tmp_path))


# --------------------------------------------------------------------------
# Windows
# --------------------------------------------------------------------------

def test_windows_laser_i_anvandarprofilen(tmp_path):
    profil = os.path.join(str(tmp_path), "Users", "anna")
    vantat = _skriv(os.path.join(profil, "vc_assist_token"))
    miljo = _windowsmiljo(tmp_path, USERPROFILE=profil)
    assert tokenplats.tokenfil(miljo) == vantat


def test_windows_med_HOME_satt_laser_anda_i_profilen(tmp_path):
    """Sommen far inte springa isar pa en maskin dar HOME ar satt.

    Bryggans Python 2.7 hade last HOME, tjanstens Python 3 laser den inte
    (bpo-36264). Bada sidor gar nu genom plats.anvandarmapp, som valjer
    USERPROFILE - och det ar det som provas har.
    """
    profil = os.path.join(str(tmp_path), "Users", "anna")
    msys = os.path.join(str(tmp_path), "msys64", "home", "anna")
    _skriv(os.path.join(msys, "vc_assist_token"), "fel fil")
    vantat = _skriv(os.path.join(profil, "vc_assist_token"), "ratt fil")
    miljo = _windowsmiljo(tmp_path, USERPROFILE=profil, HOME=msys)
    assert tokenplats.tokenfil(miljo) == vantat


def test_windows_utan_userprofile_faller_tillbaka_pa_homedrive(tmp_path):
    profil = os.path.join(str(tmp_path), "Users", "anna")
    vantat = _skriv(os.path.join(profil, "vc_assist_token"))
    miljo = _windowsmiljo(tmp_path, HOMEDRIVE="", HOMEPATH=profil)
    assert tokenplats.tokenfil(miljo) == vantat


def test_windows_soker_aldrig_efter_wineprefix(tmp_path):
    """Ett wine-prefix pa en Windows-maskin ar inte var mapp."""
    prefix = _wineprefix(tmp_path, ".wine-vc")
    _skriv(os.path.join(prefix, "drive_c", "users", "anton", "vc_assist_token"))
    miljo = _windowsmiljo(tmp_path, USERPROFILE=os.path.join(str(tmp_path), "P"))
    sokvagar = [s for s, _k in tokenplats.kandidater(miljo)]
    assert not any("drive_c" in s for s in sokvagar)


# --------------------------------------------------------------------------
# Uttryckligt val och den trasiga fixturen
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plattform", ["linux", "win32"])
def test_miljovariabeln_slar_sokningen(tmp_path, plattform):
    egen = _skriv(os.path.join(str(tmp_path), "egen", "token"))
    _skriv(os.path.join(_wineprefix(tmp_path, ".wine-vc"), "drive_c", "users",
                        "anton", "vc_assist_token"))
    miljo = upptackt.Miljo(plattform=plattform, hem=str(tmp_path),
                           env={"VC_ASSIST_TOKEN": egen,
                                "USERPROFILE": str(tmp_path)},
                           skalmapp=lambda: None)
    assert tokenplats.tokenfil(miljo) == egen


@pytest.mark.parametrize("plattform", ["linux", "win32"])
def test_en_utpekad_fil_som_saknas_letar_inte_vidare(tmp_path, plattform):
    """Trasig fixtur: variabeln satt, filen borta, en giltig token bredvid.

    Att da tyst falla tillbaka pa nagon annans token vore ett falskt gront
    utfall - anslutningen hade lyckats mot fel brygga.
    """
    _skriv(os.path.join(_wineprefix(tmp_path, ".wine-vc"), "drive_c", "users",
                        "anton", "vc_assist_token"))
    _skriv(os.path.join(str(tmp_path), "vc_assist_token"))
    miljo = upptackt.Miljo(plattform=plattform, hem=str(tmp_path),
                           env={"VC_ASSIST_TOKEN": os.path.join(str(tmp_path),
                                                                "finns-inte"),
                                "USERPROFILE": str(tmp_path)},
                           skalmapp=lambda: None)
    with pytest.raises(tokenplats.TokenSaknas) as fel:
        tokenplats.tokenfil(miljo)
    assert "VC_ASSIST_TOKEN" in str(fel.value)


def test_ingen_token_ger_ett_fel_som_raknar_upp_stallena(tmp_path):
    _wineprefix(tmp_path, ".wine-vc")
    _wineprefix(tmp_path, ".wine-vc-test")
    with pytest.raises(tokenplats.TokenSaknas) as fel:
        tokenplats.tokenfil(_linuxmiljo(tmp_path))
    assert len(fel.value.provade) == 2
    assert all("vc_assist_token" in rad for rad in fel.value.provade)
    # Meddelandet ska saga VARFOR filen kan saknas, inte bara att den gor det.
    assert "bootloggen" in str(fel.value)


def test_en_katalog_med_ratt_namn_ar_inte_en_tokenfil(tmp_path):
    prefix = _wineprefix(tmp_path, ".wine-vc")
    os.makedirs(os.path.join(prefix, "drive_c", "users", "anton",
                             "vc_assist_token"))
    with pytest.raises(tokenplats.TokenSaknas):
        tokenplats.tokenfil(_linuxmiljo(tmp_path))
