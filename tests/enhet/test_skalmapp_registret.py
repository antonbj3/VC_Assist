# -*- coding: utf-8 -*-
"""L1 for Personal-mappen ur Windows-registret (M-91).

Funktionen hade INGET prov alls fore de har: den importerar ``winreg``, som
inte finns pa Linux, sa den gick varken att kora eller falla harifran. Den
lastes darfor aldrig av nagon grind - och den ar den enda vagen till
dokumentmappen nar Windows har flyttat den.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROT)

from install import upptackt as U                                   # noqa: E402


class FalsktWinreg(object):
    """Attrapp for winreg. ``kupa`` ar nyckelnamn -> {varde: (data, typ)}."""

    HKEY_CURRENT_USER = object()
    REG_SZ = 1
    REG_EXPAND_SZ = 2

    def __init__(self, kupa):
        self.kupa = kupa
        self.oppnade = []

    def OpenKey(self, rot, nyckel):                                 # noqa: N802
        self.oppnade.append(nyckel)
        if nyckel not in self.kupa:
            raise FileNotFoundError(nyckel)
        varden = self.kupa[nyckel]

        class Nyckel(object):
            def __enter__(sjalv):
                return varden

            def __exit__(sjalv, *a):
                return False

        return Nyckel()

    def QueryValueEx(self, k, namn):                                # noqa: N802
        if namn not in k:
            raise FileNotFoundError(namn)
        return k[namn]


_USF = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
_SF = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"


def test_expanderar_reg_expand_sz(monkeypatch):
    """Trasig fixtur for fallan i rattelsen sjalv.

    Den auktoritativa nyckeln levererar REG_EXPAND_SZ. Matt pa en riktig
    Windows 10 19041-kupa: varden dar star som "%USERPROFILE%\\Documents".
    Att byta till den nyckeln UTAN att expandera hade gett en sokvag med ett
    procenttecken i - fortfarande fel, bara tystare an forut.
    """
    monkeypatch.setenv("USERPROFILE", r"C:\Users\PC")
    w = FalsktWinreg({_USF: {"Personal": (r"%USERPROFILE%\Documents",
                                          FalsktWinreg.REG_EXPAND_SZ)}})
    # ntpath, inte os.path: pa Linux ar os.path posixpath och expanderar INTE
    # %VAR%, sa en jamforelse mot os.path.expandvars hade jamfort oexpanderat
    # mot oexpanderat och passerat utan att mata nagot. Det fallet foll har.
    assert U.skalmapp_windows(w) == r"C:\Users\PC\Documents"
    assert "%" not in U.skalmapp_windows(w)


def test_laser_den_auktoritativa_nyckeln_forst():
    """Nar de tva sager OLIKA saker maste den nyare vinna.

    Det ar hela poangen: "Shell Folders" ar en bakatkompatibel cache som kan
    slapa efter nar mappen omdirigerats till OneDrive - alltsa exakt det fall
    funktionen skrevs for. Koden last den forst.
    """
    w = FalsktWinreg({
        _USF: {"Personal": (r"D:\OneDrive\Documents", FalsktWinreg.REG_SZ)},
        _SF: {"Personal": (r"C:\Users\PC\Documents", FalsktWinreg.REG_SZ)},
    })
    assert U.skalmapp_windows(w) == r"D:\OneDrive\Documents"
    assert w.oppnade[0] == _USF


def test_faller_tillbaka_nar_den_auktoritativa_saknas():
    w = FalsktWinreg({_SF: {"Personal": (r"C:\Users\PC\Documents",
                                         FalsktWinreg.REG_SZ)}})
    assert U.skalmapp_windows(w) == r"C:\Users\PC\Documents"
    assert w.oppnade == [_USF, _SF]


def test_bada_saknas_ger_fel_som_namner_bada():
    w = FalsktWinreg({})
    with pytest.raises(OSError) as e:
        U.skalmapp_windows(w)
    assert "User Shell Folders" in str(e.value)
    assert "Shell Folders" in str(e.value)


def test_kallan_namner_nyckeln_som_svarade():
    """En sokvags harkomst hor till sokvagen.

    Konsumenten skrev forut den FASTA strangen "Shell Folders\\Personal" oavsett
    var vardet kom ifran. Sa fort den andra nyckeln svarade var harkomsten
    darfor ett falskt pastaende - och harkomst ar hela skalet att skriva ut den.
    """
    w = FalsktWinreg({_USF: {"Personal": (r"D:\OD\Documents",
                                          FalsktWinreg.REG_SZ)}})
    m = U.Miljo(plattform="win32", env={}, hem="C:\\Users\\PC",
                skalmapp=lambda: U.skalmapp_windows(w))
    m.hemta_skalmapp()
    # Attrapplambdan bar ingen kalla, sa den generiska anvands - men den far
    # ALDRIG paesta fel nyckel.
    assert "Shell Folders" not in m.skalmapp_kalla or "User" in m.skalmapp_kalla

    U.skalmapp_windows(w)
    assert U.skalmapp_windows.senaste_kalla == "registret: User Shell Folders\\Personal"


def test_en_trasig_lasare_blir_varning_inte_tystnad():
    def sprucken():
        raise OSError("kupan gick inte att oppna")

    m = U.Miljo(plattform="win32", env={}, hem="C:\\Users\\PC", skalmapp=sprucken)
    assert m.hemta_skalmapp() is None
    assert any("Personal" in v for v in m.varningar)


# --- Windows-vagarna som fanns men aldrig kordes (M-92) ----------------------
#
# Matt med coverage over hela enhetssviten: raderna som bygger OneDrive-rotterna
# och Program Files-rotterna var OKORDA. Koden fanns, ingen grind hade last den.
# Bada gar att prova harifran - Miljo tar env och plattform som data - sa de var
# otestade av forbiseende, inte av nodvandighet.
#
# OneDrive-raden ar M-44:s huvudfynd: tillaggsmappen hittas inte nar Dokument
# ligger i OneDrive.

def _windows(env):
    return U.Miljo(plattform="win32", env=env, hem="C:\\Users\\PC",
                   skalmapp=lambda: None)


def test_onedrive_rotterna_kommer_med_alla_tre():
    m = _windows({"OneDrive": "C:\\Users\\PC\\OneDrive",
                  "OneDriveCommercial": "C:\\Users\\PC\\OneDrive - Firman",
                  "OneDriveConsumer": "C:\\Users\\PC\\OneDrive Personal"})
    rotter = dict((s, k) for s, k in U._windowsrotter(m))
    for var, rot in (("OneDrive", "C:\\Users\\PC\\OneDrive"),
                     ("OneDriveCommercial", "C:\\Users\\PC\\OneDrive - Firman"),
                     ("OneDriveConsumer", "C:\\Users\\PC\\OneDrive Personal")):
        vantad = os.path.join(rot, "Documents")
        assert vantad in rotter, "%s saknas bland rotterna" % var
        assert var in rotter[vantad], "kallan namner inte %s" % var


def test_en_osatt_onedrive_variabel_ger_ingen_rot():
    """Trasig fixtur: en tom variabel far inte bli sokvagen "\\Documents".

    os.path.join("", "Documents") ger "Documents" - en RELATIV sokvag som pekar
    pa arbetskatalogen. En sadan rot hade sokt igenom fel trad tyst.
    """
    m = _windows({"OneDrive": ""})
    for sokvag, _kalla in U._windowsrotter(m):
        assert sokvag not in ("Documents", os.path.join("", "Documents"))
        assert os.path.isabs(sokvag) or ":" in sokvag


def test_programrotterna_pa_windows_tar_bada_bitbredderna(tmp_path):
    """_programrotter slapper bara igenom rotter som FINNS.

    Forsta versionen av det har provet pekade pa "C:\\Program Files" och fick
    tom lista - och jag holl pa att kalla det ett fel i koden. Filtret ar ratt:
    en rot som inte finns ar ingen rot. Provet maste alltsa peka pa riktiga
    kataloger, annars mater det filtret i stallet for grenen.
    """
    pf = tmp_path / "Program Files"
    pf86 = tmp_path / "Program Files (x86)"
    sys_ = tmp_path / "sys"
    for d in (pf, pf86, sys_):
        d.mkdir()
    (sys_ / "Program Files").mkdir()
    m = _windows({"ProgramFiles": str(pf),
                  "ProgramFiles(x86)": str(pf86),
                  "SystemDrive": str(sys_).rstrip(os.sep)})
    rotter = U._programrotter(m)
    assert str(pf) in rotter
    assert str(pf86) in rotter, "32-bitarsroten saknas"


def test_tva_variabler_mot_samma_mapp_ger_en_rot(tmp_path):
    """ProgramFiles och ProgramW6432 pekar ofta pa SAMMA mapp pa 64-bitars.

    Utan avdubbleringen hade samma trad sokts igenom tva ganger, och varje
    fynd rapporterats dubbelt.
    """
    pf = tmp_path / "Program Files"
    pf.mkdir()
    m = _windows({"ProgramFiles": str(pf), "ProgramW6432": str(pf)})
    assert U._programrotter(m).count(str(pf)) == 1


def test_en_rot_som_inte_finns_slapps_inte_igenom(tmp_path):
    m = _windows({"ProgramFiles": str(tmp_path / "finns-inte")})
    assert U._programrotter(m) == []
