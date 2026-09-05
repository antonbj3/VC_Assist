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
