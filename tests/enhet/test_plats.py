# -*- coding: utf-8 -*-
"""L1: Windows-grenen provad PA LINUX, genom att attrappera plattformen.

Ingen rad har ar en matning pa Windows. Det som provas ar att grenen FINNS,
att den valjer det den sager att den valjer, och att uppstartskopiorna i
``__init__.py`` och ``bridge_cmd.py`` inte har glidit isar fran ``plats``.

Kalla: docs/matningar/M-44_windows_oprovat.md
"""
import ast
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TILLAGG = os.path.join(_ROT, "ext", "vc_addon", "vc_assist")
if _TILLAGG not in sys.path:
    sys.path.insert(0, _TILLAGG)

import plats                                   # noqa: E402
import pump                                    # noqa: E402


# --------------------------------------------------------------------------
# Miljoer. Varje rad ar ett fall som finns i verkligheten.
# --------------------------------------------------------------------------

WINDOWS_VANLIG = {"USERPROFILE": r"C:\Users\anna",
                  "HOMEDRIVE": "C:", "HOMEPATH": r"\Users\anna"}
# Git for Windows, Cygwin, MSYS och en del Java- och Emacs-installationer
# satter HOME. Python 2.7 laser den, Python 3.8+ gor det inte (bpo-36264).
WINDOWS_MED_HOME = dict(WINDOWS_VANLIG, HOME="C:\\msys64\\home\\anna")
WINDOWS_UTAN_PROFIL = {"HOMEDRIVE": "C:", "HOMEPATH": r"\Users\anna"}
WINE = {"USERPROFILE": r"C:\users\anton", "HOMEDRIVE": "C:",
        "HOMEPATH": r"\users\anton"}
LINUX = {"HOME": "/home/anton"}


def test_ar_windows_kanner_igen_alla_windowsplattformar():
    for p in ("win32", "cygwin", "msys", "win64"):
        assert plats.ar_windows(p), p
    for p in ("linux", "darwin", "freebsd13"):
        assert not plats.ar_windows(p), p


@pytest.mark.parametrize("env,plattform,vantat", [
    (WINDOWS_VANLIG, "win32", r"C:\Users\anna"),
    (WINDOWS_MED_HOME, "win32", r"C:\Users\anna"),
    (WINDOWS_UTAN_PROFIL, "win32", os.path.join("C:", r"\Users\anna")),
    (WINE, "win32", r"C:\users\anton"),
    (LINUX, "linux", "/home/anton"),
])
def test_anvandarmappen_valjer_det_den_sager(env, plattform, vantat):
    assert plats.anvandarmapp(env=env, plattform=plattform,
                              expanduser=_faller) == vantat


def _faller(_t):
    raise AssertionError("expanduser skulle inte ha behovts har")


def test_uttryckligt_hem_slar_allt():
    env = dict(WINDOWS_MED_HOME, VC_ASSIST_HEM=r"D:\vc")
    assert plats.anvandarmapp(env=env, plattform="win32",
                              expanduser=_faller) == r"D:\vc"
    env = dict(LINUX, VC_ASSIST_HEM="/srv/vc")
    assert plats.anvandarmapp(env=env, plattform="linux",
                              expanduser=_faller) == "/srv/vc"


def test_expanduser_ar_sista_utvagen_inte_forsta():
    assert plats.anvandarmapp(env={}, plattform="win32",
                              expanduser=lambda _t: r"C:\reserv") == r"C:\reserv"
    assert plats.anvandarmapp(env={}, plattform="linux",
                              expanduser=lambda _t: "/reserv") == "/reserv"


def test_home_pa_windows_ar_precis_det_som_hade_delat_sommen():
    """Den trasiga fixturen: HOME satt, och HOME != USERPROFILE.

    Sa hade det sett ut om vi last HOME som Python 2.7:s expanduser gor.
    Bryggan hade skrivit sin token i msys-hemmet och tjansten last i
    anvandarprofilen. Provet finns for att visa att skillnaden ar VERKLIG och
    att valet lander pa ratt sida av den.
    """
    som_py27_hade_gjort = WINDOWS_MED_HOME["HOME"]
    som_py38_gor = WINDOWS_MED_HOME["USERPROFILE"]
    assert som_py27_hade_gjort != som_py38_gor
    assert plats.anvandarmapp(env=WINDOWS_MED_HOME, plattform="win32",
                              expanduser=_faller) == som_py38_gor


def test_filnamnen_ar_gemensamma_och_absoluta():
    hem = plats.anvandarmapp(env=WINE, plattform="win32", expanduser=_faller)
    assert plats.fil(plats.TOKEN, env=WINE, plattform="win32",
                     expanduser=_faller) == os.path.join(hem, "vc_assist_token")


# --------------------------------------------------------------------------
# file:/// -> sokvag. M-01: getApplicationPath() ger en URI.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("uri,vantat", [
    ("file:///C:/users/anton/Documents/vc_assist/", r"C:\users\anton\Documents\vc_assist"),
    ("file:///C:/My%20Commands/Python%202/vc_assist/", r"C:\My Commands\Python 2\vc_assist"),
    ("file:///C|/gammal/form/", r"C:\gammal\form"),
    ("file:///home/anton/vc_assist/", "/home/anton/vc_assist"),
    ("file:///C:/", "C:\\"),
    (r"C:\redan\en\sokvag", r"C:\redan\en\sokvag"),
    ("", ""),
])
def test_sokvag_ur_uri(uri, vantat):
    assert plats.sokvag_ur_uri(uri) == vantat


def test_en_uri_ar_alltid_falsk_for_isdir():
    """Skalet till att oversattningen behovs alls."""
    assert not os.path.isdir("file:///C:/users/anton/Documents/vc_assist/")


def test_kandidatsokvagar_ger_bada_tolkningarna_utan_dubbletter():
    kandidater = plats.kandidatsokvagar("file:///C:/My%20Commands/vc_assist/")
    assert kandidater == [r"C:\My Commands\vc_assist", r"C:\My%20Commands\vc_assist"]
    # Utan procenttecken finns bara en tolkning, och den listas en gang.
    assert plats.kandidatsokvagar("file:///C:/a/") == ["C:\\a"]


# --------------------------------------------------------------------------
# Dokumentmappar
# --------------------------------------------------------------------------

def test_onedrive_kommer_med_pa_windows():
    """os.path.join, inte en literal: separatorn ar vardmaskinens.

    Provet kors pa Linux, sa os.sep ar "/" aven i Windows-grenen. Det ar en
    egenskap hos provningen, inte hos koden - pa Windows ar samma anrop "\\".
    Ett prov som skrev ut backslash hade provat vardmaskinen, inte grenen.
    """
    onedrive = r"C:\Users\anna\OneDrive - Foretaget"
    env = dict(WINDOWS_VANLIG, OneDrive=onedrive)
    rotter = plats.dokumentrotter(env=env, plattform="win32", expanduser=_faller)
    assert os.path.join(onedrive, "Documents") in rotter
    assert os.path.join(r"C:\Users\anna", "Documents") in rotter


def test_dokumentrotter_pa_linux_namner_inte_onedrive():
    rotter = plats.dokumentrotter(env=dict(LINUX, OneDrive="/skit"),
                                  plattform="linux", expanduser=_faller)
    assert rotter == [os.path.join("/home/anton", "Documents"),
                      os.path.join("/home/anton", "My Documents")]


def test_dokumentrotter_har_inga_dubbletter():
    env = dict(WINDOWS_VANLIG)
    env["USERPROFILE"] = r"C:\Users\anna"
    rotter = plats.dokumentrotter(env=env, plattform="win32", expanduser=_faller)
    assert len(rotter) == len(set(rotter))


# --------------------------------------------------------------------------
# Sokningen efter tillaggsmappen
# --------------------------------------------------------------------------

def _bygg(rot, delar, med_pump=True):
    mapp = os.path.join(str(rot), *delar)
    os.makedirs(mapp)
    if med_pump:
        with open(os.path.join(mapp, "pump.py"), "w") as f:
            f.write("# pump\n")
    return mapp


M01_DELAR = ("Visual Components", "4.10", "My Commands", "Python 2", "vc_assist")


def test_hittar_paketet_pa_M01s_sokvag(tmp_path):
    vantat = _bygg(tmp_path, M01_DELAR)
    assert plats.leta_tillaggsmapp([str(tmp_path)]) == vantat


def test_djupgransen_slapper_igenom_M01_men_stoppar_djupare(tmp_path):
    """Taket ar harlett ur M-01:s sokvag, inte satt pa kanslan."""
    assert len(M01_DELAR) <= plats.MAXDJUP
    for extra in range(0, 3):
        rot = tmp_path / ("d%d" % extra)
        os.makedirs(str(rot))
        delar = tuple("niva%d" % i for i in range(extra)) + M01_DELAR
        mapp = _bygg(rot, delar)
        traff = plats.leta_tillaggsmapp([str(rot)])
        if len(delar) <= plats.MAXDJUP:
            assert traff == mapp, delar
        else:
            assert traff is None, delar


def test_en_mapp_utan_pump_ar_inte_tillagget(tmp_path):
    _bygg(tmp_path, M01_DELAR, med_pump=False)
    assert plats.leta_tillaggsmapp([str(tmp_path)]) is None


def test_bytekodsmappar_gas_inte_ner_i(tmp_path):
    _bygg(tmp_path, ("__pycache__", "vc_assist"))
    assert plats.leta_tillaggsmapp([str(tmp_path)]) is None


def test_tillaggsmapp_tar_VC_ASSIST_DIR_som_sokvag(tmp_path):
    mapp = _bygg(tmp_path, M01_DELAR)
    sokvag, kalla = plats.tillaggsmapp(env={"VC_ASSIST_DIR": mapp})
    assert sokvag == mapp
    assert "sokvag" in kalla


def test_tillaggsmapp_tolkar_VC_ASSIST_DIR_som_uri(tmp_path):
    """Den gren som faktiskt anvands: M-01 sager att VC ger en URI."""
    mapp = _bygg(tmp_path, M01_DELAR)
    uri = "file://" + mapp.replace(os.sep, "/") + "/"
    sokvag, kalla = plats.tillaggsmapp(env={"VC_ASSIST_DIR": uri})
    assert sokvag == mapp
    assert "URI" in kalla


def test_tillaggsmapp_soker_nar_miljon_ar_tom(tmp_path):
    hem = tmp_path / "hem"
    dok = hem / "Documents"
    os.makedirs(str(dok))
    mapp = _bygg(dok, M01_DELAR)
    sokvag, kalla = plats.tillaggsmapp(env={"HOME": str(hem)}, plattform="linux")
    assert sokvag == mapp
    assert "sokning" in kalla


def test_tillaggsmapp_sager_var_den_letade_nar_den_inte_hittar(tmp_path):
    sokvag, kalla = plats.tillaggsmapp(env={"HOME": str(tmp_path)},
                                       plattform="linux")
    assert sokvag is None
    assert "Documents" in kalla


def test_windows_sokningen_hittar_i_onedrive(tmp_path):
    """Windows-grenen, kord pa Linux mot ett attrappträd."""
    onedrive = tmp_path / "OneDrive - Foretaget"
    dok = onedrive / "Documents"
    os.makedirs(str(dok))
    mapp = _bygg(dok, M01_DELAR)
    env = {"USERPROFILE": str(tmp_path / "tom"), "OneDrive": str(onedrive)}
    sokvag, _kalla = plats.tillaggsmapp(env=env, plattform="win32")
    assert sokvag == mapp


# --------------------------------------------------------------------------
# Wine-detektionen
# --------------------------------------------------------------------------

class _FalskNtdll(object):
    def wine_get_version(self):
        return "11.16"


class _FalskWindll(object):
    def __init__(self, ntdll):
        self.ntdll = ntdll


class _FalskCtypes(object):
    def __init__(self, ntdll):
        self.windll = _FalskWindll(ntdll)


class _TomNtdll(object):
    pass


def test_wine_kanns_igen_pa_ntdlls_egen_symbol():
    assert plats.ar_wine("win32", _FalskCtypes(_FalskNtdll()), env={})


def test_riktig_windows_har_inte_symbolen():
    assert not plats.ar_wine("win32", _FalskCtypes(_TomNtdll()), env={})


def test_linux_ar_aldrig_wine():
    assert not plats.ar_wine("linux", _FalskCtypes(_FalskNtdll()), env={})


def test_ett_ctypes_som_kastar_svarar_inte_wine():
    class Kastar(object):
        @property
        def windll(self):
            raise OSError("ingen windll har")
    assert not plats.ar_wine("win32", Kastar(), env={})


def test_wine_gar_att_tvinga_utifran():
    assert plats.ar_wine("win32", _FalskCtypes(_TomNtdll()),
                         env={"VC_ASSIST_WINE": "1"})
    assert not plats.ar_wine("win32", _FalskCtypes(_FalskNtdll()),
                             env={"VC_ASSIST_WINE": "0"})


# --------------------------------------------------------------------------
# Adressflaggan. SO_REUSEADDR betyder inte samma sak pa de tva.
# --------------------------------------------------------------------------

class _FalskSocketmodul(object):
    SOL_SOCKET = 1
    SO_REUSEADDR = 2

    def __init__(self, med_exclusive=True):
        if med_exclusive:
            self.SO_EXCLUSIVEADDRUSE = -5


def test_linux_far_so_reuseaddr_precis_som_forut():
    namn, flagga = pump.valj_adressflagga(_FalskSocketmodul(), "linux", wine=False)
    assert namn == "SO_REUSEADDR"
    assert flagga == 2


def test_wine_far_so_reuseaddr_precis_som_forut():
    """Wine ar det enda som ar MATT. Dess beteende far inte andras."""
    namn, flagga = pump.valj_adressflagga(_FalskSocketmodul(), "win32", wine=True)
    assert namn == "SO_REUSEADDR"
    assert flagga == 2


def test_riktig_windows_far_inte_so_reuseaddr():
    """Pa Windows later SO_REUSEADDR en andra sockel binda over en LEVANDE
    lyssnare. Bryggan skriver sin token forst efter en lyckad bind, sa just
    den flaggan hade slagit ut det skyddet."""
    namn, flagga = pump.valj_adressflagga(_FalskSocketmodul(), "win32", wine=False)
    assert namn == "SO_EXCLUSIVEADDRUSE"
    assert flagga == -5


def test_windows_utan_exclusive_satter_ingen_flagga_alls():
    namn, flagga = pump.valj_adressflagga(_FalskSocketmodul(med_exclusive=False),
                                          "win32", wine=False)
    assert flagga is None
    assert "ingen" in namn


def test_riktiga_socketmodulen_ger_ett_svar_pa_den_har_maskinen():
    namn, flagga = pump.valj_adressflagga()
    assert namn == "SO_REUSEADDR" and flagga is not None


# --------------------------------------------------------------------------
# Uppstartskopiorna far inte glida isar fran plats
# --------------------------------------------------------------------------

def _plocka(sokvag, namn, extra=None):
    """Kor ut namngivna funktioner ur en fil som inte gar att importera.

    ``__init__.py`` gor ``from vcApplication import *`` och ``bridge_cmd.py``
    ``from vcCommand import *``; bada finns bara inne i VC. Funktionerna sjalva
    ar sjalvstandiga och gar att kora var for sig.
    """
    with open(sokvag) as f:
        trad = ast.parse(f.read(), filename=sokvag)
    valda = [n for n in trad.body
             if isinstance(n, ast.FunctionDef) and n.name in namn]
    assert len(valda) == len(namn), "hittade %s, ville ha %s" % (
        [n.name for n in valda], list(namn))
    rum = {"os": os, "sys": sys}
    rum.update(extra or {})
    exec(compile(ast.Module(body=valda, type_ignores=[]), sokvag, "exec"), rum)
    return rum


URITABELL = [
    "file:///C:/users/anton/Documents/vc_assist/",
    "file:///C:/My%20Commands/Python%202/vc_assist/",
    "file:///C|/gammal/form/",
    "file:///home/anton/vc_assist/",
    "file:///C:/",
    r"C:\redan\en\sokvag",
    "",
]

MILJOTABELL = [(WINDOWS_VANLIG, "win32"), (WINDOWS_MED_HOME, "win32"),
               (WINDOWS_UTAN_PROFIL, "win32"), (WINE, "win32"), (LINUX, "linux")]


def test_uppstartskopian_i_init_svarar_som_plats(monkeypatch):
    rum = _plocka(os.path.join(_TILLAGG, "__init__.py"),
                  ("_avkoda_procent", "_sokvag_ur_uri", "_anvandarmapp"))
    for uri in URITABELL:
        assert rum["_sokvag_ur_uri"](uri) == plats.sokvag_ur_uri(uri), uri
        kandidater = plats.kandidatsokvagar(uri)
        oavkodad = rum["_sokvag_ur_uri"](uri, False)
        if kandidater:
            assert oavkodad == kandidater[-1], uri
        else:
            assert not oavkodad, uri
    for env, plattform in MILJOTABELL:
        monkeypatch.setattr(sys, "platform", plattform)
        assert rum["_anvandarmapp"](env) == plats.anvandarmapp(
            env=env, plattform=plattform), (env, plattform)


def test_uppstartskopian_faller_faktiskt_nar_den_glider(monkeypatch):
    """Trasig fixtur: en kopia som laser HOME forst godkanns inte."""
    def som_py27_hade_gjort(env):
        return env.get("HOME") or env.get("USERPROFILE")
    monkeypatch.setattr(sys, "platform", "win32")
    assert som_py27_hade_gjort(WINDOWS_MED_HOME) != plats.anvandarmapp(
        env=WINDOWS_MED_HOME, plattform="win32")


def test_bridge_cmd_gar_genom_plats_men_overlever_utan_det(monkeypatch):
    """Bade grenen med plats och reservgrenen utan, var for sig."""
    sokvag = os.path.join(_TILLAGG, "bridge_cmd.py")
    med = _plocka(sokvag, ("_anvandarmapp",), extra={"_plats": plats})
    utan = _plocka(sokvag, ("_anvandarmapp",), extra={"_plats": None})
    monkeypatch.setenv("VC_ASSIST_HEM", os.path.join("C:", "vc"))
    assert med["_anvandarmapp"]() == os.path.join("C:", "vc")
    assert utan["_anvandarmapp"]() == os.path.expanduser("~")
