# -*- coding: utf-8 -*-
"""Var filerna bor. En harledning, samma svar pa Windows och under Wine.

Innan den har modulen fanns rakade atta stallen i tillagget ut
``os.path.expanduser("~")`` var for sig, och tjanstens provskript bar en
hardkodad wine-sokvag. Tva saker gor det till ett fel och inte bara upprepning:

* ``expanduser("~")`` svarar OLIKA i VC:s Python 2.7 och i tjanstens Python 3
  nar den kors pa Windows. Python 2.7:s ``ntpath.expanduser`` laser ``HOME``
  forst och faller tillbaka pa ``USERPROFILE``. Python 3.8 och senare tog bort
  ``HOME``-ledet helt (bpo-36264) och laser ``USERPROFILE`` direkt. Ar ``HOME``
  satt pa en Windows-maskin - Git for Windows, Cygwin, MSYS och en del Java-
  och Emacs-installationer satter den - skriver bryggan sin token i en mapp
  tjansten inte tittar i, och tjansten far E_AUTH utan att nagon logg sager
  varfor. Skillnaden mellan de tva standardbiblioteken ar last och lasbar;
  att den faktiskt biter pa en Windows-maskin ar OPROVAT (M-44).

* ``getApplicationPath()`` ger paketets mapp som en ``file:///``-URI (M-01),
  inte som en sokvag. ``os.path.isdir()`` pa en URI ar alltid falskt, pa bada
  plattformarna.

Valet ar uttalat: pa Windows gar ``USERPROFILE`` FORE ``HOME``, sa bada sidor
av sommen svarar lika. ``VC_ASSIST_HEM`` slar allt, sa den som har en udda
uppsattning pekar ut mappen i stallet for att overtala oss.

Endast standardbibliotek som VC:s Python 2.7 bar (regel 6 i
docs/spec/35_plattformar.md). Giltig i bade Python 2.7 och 3.x: inga
f-strangar, inga typannoteringar, ingen pathlib.
"""
from __future__ import absolute_import, division, print_function

import os
import sys

WINDOWSPLATTFORMAR = ("win32", "cygwin", "msys")

# Miljovariabler som slar all harledning. Finns for att en oprovad plattform
# ska ga att RATTA utifran i stallet for att krava en ny kodrunda.
HEMVARIABEL = "VC_ASSIST_HEM"
WINEVARIABEL = "VC_ASSIST_WINE"

PAKETNAMN = "vc_assist"
MARKORFIL = "pump.py"

# Filnamnen i anvandarmappen. Samma strang pa bada sidor av sommen: bryggan
# skriver, tjansten laser.
TOKEN = "vc_assist_token"
BOOTLOGG = "vc_assist_boot.log"
BRYGGLOGG = "vc_assist_brygga.log"
FORMAGA = "vc_assist_formaga.json"
UPPSKJUTET = "vc_assist_uppskjutet.json"
OGONFIL = "vc_assist_eyes.json"
STARTLAYOUT = "vc_assist_startlayout.txt"
STARTSKRIPT = "vc_assist_startskript.py"

# Hur djupt under en dokumentmapp tillaggsmappen far ligga. Harlett, inte
# gissat: sokvagen ar <foretag>/<version>/My Commands/Python N/vc_assist/pump.py
# och det ar sex nivaer under dokumentmappen (M-01). Taket finns for att en
# dokumentmapp som synkas mot OneDrive kan vara enorm, och ett obegransat
# os.walk vid VC:s uppstart da laser fast programmet.
MAXDJUP = 6                # Satt av M-44: sex nivaer enligt M-01:s sokvag.

# Mappnamn som aldrig kan innehalla tillagget och som kostar mest att ga ner i.
HOPPA_OVER = ("__pycache__", "node_modules", ".git")


# --------------------------------------------------------------------------
# Plattform
# --------------------------------------------------------------------------

def ar_windows(plattform=None):
    """Sant nar Pythonen ar en WINDOWS-Python. Wine raknas som Windows har.

    Inne i VC ar svaret alltid sant, aven under Wine: det ar en Windows-Python
    som kor. Skillnaden mellan Wine och riktig Windows gors av ``ar_wine()``
    och bara dar den betyder nagot.
    """
    if plattform is None:
        plattform = sys.platform
    return plattform in WINDOWSPLATTFORMAR or plattform.startswith("win")


def ar_wine(plattform=None, ctypesmodul=None, env=None):
    """Sant nar Windows-Pythonen kor ovanpa Wine.

    Detektionen ar Wines egen och dokumenterade: ``ntdll`` exporterar
    ``wine_get_version``, vilket ingen riktig Windows-ntdll gor. Registret
    duger samre - ``HKCU\\Software\\Wine`` skrivs forst nar nagot konfigurerats.

    Fragan stalls pa exakt ett stalle: vilken adressflagga lyssnaren ska satta.
    Se ``pump.valj_adressflagga``.
    """
    if env is None:
        env = os.environ
    uttryckligt = env.get(WINEVARIABEL)
    if uttryckligt is not None and uttryckligt != "":
        return uttryckligt not in ("0", "nej", "false", "False")
    if not ar_windows(plattform):
        return False
    if ctypesmodul is None:
        try:
            import ctypes as ctypesmodul
        except ImportError:
            return False
    try:
        return hasattr(ctypesmodul.windll.ntdll, "wine_get_version")
    except Exception:
        # En misslyckad detektion far inte bli ett pastaende om Windows: den
        # som inte gar att svara pa svarar "inte Wine", och Windows-grenen ar
        # den forsiktigare av de tva.
        return False


# --------------------------------------------------------------------------
# Anvandarmappen
# --------------------------------------------------------------------------


class HemsokningMisslyckades(RuntimeError):
    """Anvandarmappen gick inte att harleda, och ingen gissning ar battre.

    Egen typ sa att den som anropar kan skilja det har fran vilket fel som
    helst och skriva ut det i bootloggen i stallet for att do tyst (M-09).
    """



def anvandarmapp(env=None, plattform=None, expanduser=None):
    """Mappen dar token, loggar och tillstandsfiler bor.

    Ordning, och skalet till varje led:

    1. ``VC_ASSIST_HEM`` - uttryckligt val slar harledning.
    2. Windows: ``USERPROFILE``. Valt FRAMFOR ``HOME`` sa att VC:s Python 2.7
       och tjanstens Python 3 pekar pa samma mapp (se modulens docstring).
    3. Windows utan ``USERPROFILE``: ``HOMEDRIVE`` + ``HOMEPATH``.
    4. Posix: ``HOME``.
    5. Sist ``expanduser("~")`` - och SVARET PROVAS. Ger den tillbaka ett
       ``~`` har harledningen misslyckats, och da ar tystnad det farliga
       svaret: en relativ mapp som heter "~" skapas dar VC:s arbetskatalog
       rakar ligga, tillagget skriver sin token dit, tjansten letar nagon
       annanstans och far E_AUTH utan att nagon logg sager varfor. MATT
       (M-92): pa Python 3.13.11 ger ``ntpath.expanduser("~")`` exakt "~" nar
       bara ``HOME`` ar satt.
    """
    if env is None:
        env = os.environ
    if expanduser is None:
        expanduser = os.path.expanduser
    uttryckligt = env.get(HEMVARIABEL)
    if uttryckligt:
        return uttryckligt
    if ar_windows(plattform):
        profil = env.get("USERPROFILE")
        if profil:
            return profil
        stig = env.get("HOMEPATH")
        if stig:
            return os.path.join(env.get("HOMEDRIVE", ""), stig)
        return _sista_utvagen(expanduser, ("USERPROFILE", "HOMEDRIVE+HOMEPATH"))
    hem = env.get("HOME")
    if hem:
        return hem
    return _sista_utvagen(expanduser, ("HOME",))


def _sista_utvagen(expanduser, provade):
    """``expanduser("~")``, men bara om den faktiskt svarade nagot.

    Bade Python 2.7:s och Python 3:s ``ntpath.expanduser`` lamnar strangen
    ORORD nar den inte kan losa den - de returnerar alltsa "~" i stallet for
    att saga ifran. Anvands det svaret som en mapp blir felet tyst och
    fjarran fran sin orsak, vilket ar den dyraste sorten (I3, S9).
    """
    svar = expanduser("~")
    if not svar or svar == "~" or svar.startswith("~"):
        raise HemsokningMisslyckades(
            "kunde inte harleda anvandarmappen: %s saknas och expanduser(\"~\")"
            " gav %r. Satt %s till mappen dar token och loggar ska bo."
            % (", ".join(provade), svar, HEMVARIABEL))
    return svar


def fil(namn, env=None, plattform=None, expanduser=None):
    """En av filerna i anvandarmappen, som absolut sokvag."""
    return os.path.join(anvandarmapp(env=env, plattform=plattform,
                                     expanduser=expanduser), namn)


# --------------------------------------------------------------------------
# file:///-URI till sokvag
# --------------------------------------------------------------------------

def _avkoda_procent(text):
    """%XX -> tecken. Egen loop i stallet for urllib: modulen heter olika i
    Python 2 och 3, och det har ledet ska inte bara ett importtrick."""
    if "%" not in text:
        return text
    ut = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "%" and i + 2 < n:
            try:
                ut.append(chr(int(text[i + 1:i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        ut.append(c)
        i += 1
    return "".join(ut)


def _tolka_uri(uri, avkoda):
    if not uri:
        return ""
    text = uri.replace("\\", "/")
    if text[:5].lower() != "file:":
        return uri
    text = text[5:]
    if text.startswith("///"):
        text = text[2:]
    elif text.startswith("//"):
        # file://vardnamn/... stods inte. Vi tar resten som en sokvag i
        # stallet for att kasta: en logg med fel sokvag ar lasbar, en tyst
        # uppstart utan brygga ar det inte.
        text = text[1:]
    if avkoda:
        text = _avkoda_procent(text)
    if len(text) >= 3 and text[0] == "/" and text[2] in ":|":
        text = text[1:]
        if text[1] == "|":
            text = text[0] + ":" + text[2:]
    if len(text) >= 2 and text[1] == ":":
        text = text.replace("/", "\\")
    if len(text) > 1 and text[-1] in "/\\":
        stam = text[:-1]
        if stam and not stam.endswith(":"):
            text = stam
    return text


def sokvag_ur_uri(uri):
    """``file:///C:/a%20b/`` -> ``C:\\a b``. Icke-URI gar oforandrad igenom.

    M-01: ``getApplicationPath()`` ger en URI. Utan den har oversattningen ar
    ``os.path.isdir(VC_ASSIST_DIR)`` alltid falskt, pa bada plattformarna, och
    tillaggsmappen letas alltid upp med ett os.walk som inte behovdes.
    """
    return _tolka_uri(uri, True)


def kandidatsokvagar(uri):
    """Bada tolkningarna av URI:n, mest sannolik forst, utan dubbletter.

    Procentavkodningen ar inte entydig over de tva Python-versionerna: ``%C3%85``
    blir ratt UTF-8-bytestrang i Python 2 och mojibake i Python 3. I stallet
    for att valja at kallaren lamnas bada, och kallaren tar den som FINNS pa
    disk. Ett svar som gar att prova slar ett svar som ar utrett.
    """
    ut = []
    for kandidat in (_tolka_uri(uri, True), _tolka_uri(uri, False)):
        if kandidat and kandidat not in ut:
            ut.append(kandidat)
    return ut


# --------------------------------------------------------------------------
# Tillaggsmappen
# --------------------------------------------------------------------------

def _expandera_windows(stig, env=None):
    """Expandera %VAR% i en sokvag med ntpath.expandvars (aven nar den kors pa Linux)."""
    if not stig:
        return stig
    import ntpath
    if env is not None:
        import re
        def _ersatt(m):
            return env.get(m.group(1), m.group(0))
        stig = re.sub(r"%([^%]+)%", _ersatt, stig)
    stig = ntpath.expandvars(stig)
    if os.sep == "/":
        stig = stig.replace("\\", "/")
    return os.path.normpath(stig)


def skalmapp_windows(env=None, winreg_modul=None):
    """Windows egen 'Personal'-mapp ur registret, expanderad med ntpath."""
    if winreg_modul is None:
        try:
            import winreg as winreg_modul
        except ImportError:
            try:
                import _winreg as winreg_modul
            except ImportError:
                return None
    for nyckel in (
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
    ):
        try:
            with winreg_modul.OpenKey(winreg_modul.HKEY_CURRENT_USER, nyckel) as k:
                varde, typ = winreg_modul.QueryValueEx(k, "Personal")
                return _expandera_windows(varde, env)
        except Exception:
            continue
    return None


def dokumentrotter(env=None, plattform=None, expanduser=None, winreg_modul=None):
    """Mappar dar ``<foretag>/<version>/My Commands`` kan ligga.

    Windows-leden ar inte kosmetik: ``Documents`` kan vara omdirigerad till
    OneDrive, och da finns ``%USERPROFILE%\\Documents`` antingen inte alls
    eller som en tom rest. ``install/upptackt.py`` kan redan det pa
    tjanstesidan; utan detta kan tillagget det inte pa VC-sidan.
    """
    if env is None:
        env = os.environ
    hem = anvandarmapp(env=env, plattform=plattform, expanduser=expanduser)
    kandidater = [os.path.join(hem, "Documents"),
                  os.path.join(hem, "My Documents")]
    if ar_windows(plattform):
        skal = skalmapp_windows(env=env, winreg_modul=winreg_modul)
        if skal:
            kandidater.append(_expandera_windows(skal, env))
        profil = env.get("USERPROFILE")
        if profil:
            kandidater.append(os.path.join(profil, "Documents"))
            profil_exp = _expandera_windows(profil, env)
            if profil_exp != profil:
                kandidater.append(os.path.join(profil_exp, "Documents"))
            kandidater.append(os.path.join(profil_exp, "OneDrive", "Documents"))
            kandidater.append(os.path.join(profil_exp, "OneDrive"))
        for nyckel in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
            rot = env.get(nyckel)
            if rot:
                kandidater.append(os.path.join(rot, "Documents"))
                kandidater.append(rot)
                rot_exp = _expandera_windows(rot, env)
                if rot_exp != rot:
                    kandidater.append(os.path.join(rot_exp, "Documents"))
                    kandidater.append(rot_exp)
    ut = []
    for k in kandidater:
        if k and k not in ut:
            ut.append(k)
    return ut


def leta_tillaggsmapp(rotter, walk=None, isdir=None, paketnamn=PAKETNAMN,
                      markor=MARKORFIL, maxdjup=MAXDJUP):
    """Forsta mappen som heter ``paketnamn`` och innehaller ``markor``.

    Djupet begransas till ``maxdjup`` nivaer under roten. Ett obegransat
    os.walk over en OneDrive-synkad dokumentmapp kan bade ta minuter och
    tvinga fram nedladdning av molnplatshallare - vid VC:s uppstart, i
    huvudtraden, dar ingenting annat hinner ga.
    """
    if walk is None:
        walk = os.walk
    if isdir is None:
        isdir = os.path.isdir
    for rot in rotter:
        if not rot or not isdir(rot):
            continue
        rotdjup = rot.replace("\\", "/").rstrip("/").count("/")
        for har, mappar, filer in walk(rot):
            djup = har.replace("\\", "/").rstrip("/").count("/") - rotdjup
            if djup >= maxdjup:
                del mappar[:]
            else:
                mappar[:] = [m for m in mappar
                             if m not in HOPPA_OVER and not m.startswith(".")]
            if os.path.basename(har.rstrip("/\\")) == paketnamn and markor in filer:
                return har
    return None


class TillaggsmappSaknas(RuntimeError):
    """Tillaggsmappen gick inte att hitta."""


def tillaggsmapp(env=None, plattform=None, expanduser=None, isdir=None,
                 walk=None, winreg_modul=None):
    """Tillaggets egen mapp, harledd i tre led med fallande sakerhet.

    1. ``VC_ASSIST_DIR`` som sokvag - satt av ``__init__.py`` i det normala
       fallet, och da ar det bara ett isdir-anrop.
    2. ``VC_ASSIST_DIR`` tolkat som ``file:///``-URI - vad
       ``getApplicationPath()`` faktiskt ger (M-01).
    3. En djupbegransad sokning under dokumentmapparna.

    Returnerar ``(sokvag, kalla)``; ``(None, felbesked)`` nar inget av
    leden svarade. Kallan loggas av anroparen: en brygga som startar fran fel
    led ar inte samma sak som en som startar fran ratt.
    """
    if env is None:
        env = os.environ
    if isdir is None:
        isdir = os.path.isdir
    rad = env.get("VC_ASSIST_DIR")
    if rad:
        if isdir(rad):
            return rad, "VC_ASSIST_DIR som sokvag"
        for kandidat in kandidatsokvagar(rad):
            if isdir(kandidat):
                return kandidat, "VC_ASSIST_DIR som file:///-URI"
    rotter = dokumentrotter(env=env, plattform=plattform,
                            expanduser=expanduser, winreg_modul=winreg_modul)
    traff = leta_tillaggsmapp(rotter, walk=walk, isdir=isdir)
    if traff:
        return traff, "sokning under dokumentmapparna"
    fel = (
        "hittade inte tillaggsmappen '%s' (med markorfilen '%s'). "
        "Genomsokta dokumentrotter: [%s]. "
        "Satt miljovariabeln VC_ASSIST_DIR eller %s till mappen dar tillagget ar installerat."
        % (PAKETNAMN, MARKORFIL, ", ".join(rotter), HEMVARIABEL)
    )
    return None, fel


def tillaggsmapp_eller_kasta(env=None, plattform=None, expanduser=None,
                             isdir=None, walk=None, winreg_modul=None):
    mapp, kalla = tillaggsmapp(env=env, plattform=plattform,
                               expanduser=expanduser, isdir=isdir,
                               walk=walk, winreg_modul=winreg_modul)
    if mapp is None:
        raise TillaggsmappSaknas(kalla)
    return mapp, kalla
