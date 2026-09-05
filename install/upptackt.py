# -*- coding: utf-8 -*-
"""Upptackt: hitta VC:s tillaggsmapp utan att anta en sokvag.

Vad som ar MATT och vad som INTE ar det:

* ``My Commands/Python 2/<paket>/__init__.py`` fungerar pa VC 4.10.
  ``My Commands/<paket>/__init__.py`` gor det INTE - kroken fyrar aldrig.
  Bada matta i M-01. Nivan "Python 2" ar alltsa inte kosmetisk.
* VC:s egen konfiguration lagger tillaggsmappen pa
  ``%MYDOCUMENTS%\\%COMPANY%\\%VERSION_2%\\My Commands``
  (``VisualComponents.Engine.exe.config``, nyckeln ``MyCommandsFolder``).
  Foretagsnamnet och versionen ar alltsa VARIABLER i VC:s egen kalla.
  Darfor soker den har modulen efter monstret ``*/*/My Commands`` i stallet
  for att skriva "Visual Components" i koden.
* VC 5.0 kor Python 3 och har SANNOLIKT nivan "Python 3". Det ar OMATT.
  Sokningen letar darfor efter vilka ``Python N``-nivaer som faktiskt finns,
  och harleder en niva ur versionsnumret bara nar ingen finns pa disk - och
  markerar da resultatet som oprovat.
* Under Wine bor anvandarmappen i ett prefix. MATT i M-02: prefixets
  ``Documents`` ar som standard en SYMLANK till vardens ``~/Documents``, sa
  tva prefix kan dela tillaggsmapp. Sokningen loser darfor upp realpath och
  rapporterar vilka prefix som pekar pa samma mapp. Att inte gora det var
  precis felet i M-02.

Ingenting harinne skriver till disk.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field

WINDOWSPLATTFORMAR = ("win32", "cygwin", "msys")

# Foretags- och versionsniva under dokumentmappen soks som ett MONSTER: VC:s
# egen config har bada som variabler, sa namnen skrivs aldrig i koden.
MY_COMMANDS = "My Commands"

_VERSION_RE = re.compile(r"^(\d+(?:\.\d+)*)")
_PYNIVA_RE = re.compile(r"^Python[ _]?(\d+)$", re.IGNORECASE)


# --------------------------------------------------------------------------
# Miljon. Allt som skiljer Windows fran Linux gar genom det har objektet, och
# det gar att injicera - annars gar Windows-vagen inte att prova alls harifran.
# --------------------------------------------------------------------------

# De tva registernycklar som bar Personal-mappen, i den ordning de ska provas.
# "User Shell Folders" ar den som Windows sjalv skriver till nar mappen flyttas
# eller omdirigeras till OneDrive. "Shell Folders" ar en aldre cache som finns
# kvar for bakatkompatibilitet - den lastes forst av den har koden, alltsa just
# den nyckel som kan slapa efter i exakt det OneDrive-fall funktionen skrevs
# for. MATT (M-91): pa en riktig Windows 10 19041-kupa finns BADA, och de
# stammer overens - men den maskinen har ingen omdirigering, sa den kan inte
# visa fallet dar de gar isar.
_NYCKLAR = (
    (r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
     "User Shell Folders\\Personal"),
    (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
     "Shell Folders\\Personal"),
)


def skalmapp_windows(winreg_modul=None):
    """Windows egen "Personal"-mapp ur registret, med kallan den kom ur.

    Behovs for att ``~/Documents`` kan vara omdirigerad till OneDrive. Ren
    stdlib: ``winreg`` foljer med Python pa Windows och finns inte alls
    pa Linux, darfor importen inne i funktionen. ``winreg_modul`` finns bara
    for att kunna prova bada nycklarna och expansionen harifran.

    ``User Shell Folders`` levererar REG_EXPAND_SZ, alltsa "%USERPROFILE%\\
    Documents" och inte en fardig sokvag. Att bara byta nyckel utan att
    expandera hade gett en sokvag med ett procenttecken i - samma fel som
    forut, fast tystare.
    """
    if winreg_modul is None:
        import winreg as winreg_modul  # finns bara pa Windows

    fel = []
    for nyckel, kallnamn in _NYCKLAR:
        try:
            with winreg_modul.OpenKey(winreg_modul.HKEY_CURRENT_USER, nyckel) as k:
                varde, typ = winreg_modul.QueryValueEx(k, "Personal")
        except Exception as e:                      # noqa: BLE001 - samlas nedan
            fel.append("%s: %r" % (kallnamn, e))
            continue
        if typ == getattr(winreg_modul, "REG_EXPAND_SZ", 2):
            # ntpath, INTE os.path. Pa Linux ar os.path posixpath, som bara
            # kanner $VAR och lamnar %USERPROFILE% orort - koden hade da varit
            # ratt pa Windows och oprovbar harifran, vilket ar samma sak som
            # oprovad. ntpath.expandvars gor Windows-expansionen pa bada
            # plattformarna och lases av provet nedan.
            import ntpath
            varde = ntpath.expandvars(varde)
        skalmapp_windows.senaste_kalla = "registret: " + kallnamn
        return varde
    raise OSError("Personal fanns i ingen av registernycklarna: " + "; ".join(fel))


skalmapp_windows.senaste_kalla = None


class Miljo(object):
    """Plattformen som data i stallet for utspridda ``sys.platform``-koll.

    Varje falt gar att satta, sa Windows-vagen kan provas fran Linux med en
    attrappmapp. Det ar inte samma sak som att ha kort den pa Windows, och
    det pastas inte heller nagonstans.
    """

    def __init__(self, plattform=None, hem=None, env=None, skalmapp=None,
                 extra_prefix=()):
        self.plattform = sys.platform if plattform is None else plattform
        self.env = dict(os.environ) if env is None else dict(env)
        self.hem = os.path.expanduser("~") if hem is None else hem
        self._skalmapp = skalmapp_windows if skalmapp is None else skalmapp
        self.extra_prefix = tuple(extra_prefix)
        # S9: ingenting far svaljas tyst. Allt som gick fel under sokningen
        # hamnar har och skrivs ut av kommandoraden.
        self.varningar = []
        self.skalmapp_kalla = "registret"

    @property
    def ar_windows(self):
        return self.plattform in WINDOWSPLATTFORMAR or self.plattform.startswith("win")

    def hemta_skalmapp(self):
        """Personal-mappen, eller None. Ett fel blir en varning, aldrig tystnad."""
        if not self.ar_windows:
            return None
        try:
            svar = self._skalmapp()
        except Exception as e:                      # noqa: BLE001 - loggas nedan
            self.varningar.append("kunde inte lasa Personal ur registret: %r" % (e,))
            return None
        # Kallan maste namna nyckeln som faktiskt svarade. Stod forst som en
        # fast strang "Shell Folders\\Personal" i konsumenten, vilket hade
        # blivit ett falskt harkomstpastaende sa fort varden kom ur den andra
        # nyckeln. En sokvags harkomst hor till sokvagen.
        self.skalmapp_kalla = getattr(self._skalmapp, "senaste_kalla",
                                      None) or "registret"
        return svar

    def varna(self, text):
        self.varningar.append(text)


# --------------------------------------------------------------------------
# Fynd
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Dokumentrot:
    """En mapp som kan innehalla ``<foretag>/<version>/My Commands``."""

    sokvag: str
    kallor: tuple = ()


@dataclass(frozen=True)
class VcMapp:
    """En funnen ``My Commands`` med foretag och version ur sokvagen."""

    my_commands: str
    foretag: str
    version: str
    dokumentrot: str
    kallor: tuple = ()
    pythonnivaer: tuple = ()

    @property
    def nyckel(self):
        return versionsnyckel(self.version)



@dataclass(frozen=True)
class Programinstallation:
    """En VC-installation pa disk, funnen via ``Python N/Auto Complete/api.xml``.

    Poangen ar 36_versioner.md: installationen gar att LASA utan licens och
    utan att starta programmet. Vilken Python-niva motorn bar ar darfor en
    matning, inte en gissning ur versionsnumret.
    """

    sokvag: str
    produkt: str
    pythonnivaer: tuple = ()


@dataclass
class Sokresultat:
    dokumentrotter: list = field(default_factory=list)
    vcmappar: list = field(default_factory=list)
    programinstallationer: list = field(default_factory=list)
    varningar: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Versionsnummer
# --------------------------------------------------------------------------

def versionsnyckel(namn):
    """Sorteringsnyckel dar 4.10 ar STORRE an 4.9.

    Lexikalisk sortering ger fel svar, och bada mapparna finns pa den har
    maskinen. Ett namn som inte borjar med siffror sorteras sist.
    """
    m = _VERSION_RE.match((namn or "").strip())
    if not m:
        return (0, (), namn or "")
    return (1, tuple(int(x) for x in m.group(1).split(".")), namn)


def huvudversion(namn):
    """Forsta talet i versionsnamnet, eller None om det inte gar att lasa."""
    nyckel = versionsnyckel(namn)
    if not nyckel[1]:
        return None
    return nyckel[1][0]


def forvantad_pythonniva(version):
    """Nivan som versionsnumret PEKAR pa. Bara 4.x ar matt.

    36_versioner.md tillater exakt tre bruk av versionsnumret, och ett av dem
    ar att harleda sokvagen till tillaggsmappen. Detta ar det bruket - och
    svaret markeras oprovat overallt utom pa 4.x.
    """
    major = huvudversion(version)
    if major is None:
        return None
    if major <= 4:
        return "Python 2"       # MATT M-01 pa 4.10
    return "Python 3"           # OMATT: 36_versioner.md sager "sannolikt"


def sokvagen_ar_matt(version, pythonniva):
    """Sant bara for den enda kombination som faktiskt korts i VC (M-01)."""
    return huvudversion(version) == 4 and pythonniva == "Python 2"


# --------------------------------------------------------------------------
# Wine-prefix
# --------------------------------------------------------------------------

def pythonnivanamn(namn):
    """"Python 3" om namnet ar en Python-niva, annars None.

    Publik sa att kommandoraden slipper rora regexet. Namnet normaliseras,
    sa "python3" och "Python_3" ger samma svar som "Python 3".
    """
    m = _PYNIVA_RE.match((namn or "").strip())
    return "Python %s" % m.group(1) if m else None


def wineprefix(miljo):
    """Kandidatprefix, i ordning: WINEPREFIX, uttryckliga, ~/.wine, ~/.wine*.

    Ett prefix raknas som prefix nar det har en ``drive_c``. Ingen lista over
    namn: operatorens egna heter ``.wine-vc`` och ``.wine-vc-test``, och nasta
    maskin har andra.
    """
    if miljo.ar_windows:
        return []

    kandidater = []

    def lagg(sokvag, kalla):
        if sokvag:
            kandidater.append((os.path.abspath(os.path.expanduser(sokvag)), kalla))

    lagg(miljo.env.get("WINEPREFIX"), "WINEPREFIX")
    for p in miljo.extra_prefix:
        lagg(p, "--prefix")
    lagg(os.path.join(miljo.hem, ".wine"), "~/.wine")
    try:
        for namn in sorted(os.listdir(miljo.hem)):
            if namn.startswith(".wine"):
                lagg(os.path.join(miljo.hem, namn), "~/%s" % namn)
    except OSError as e:
        miljo.varna("kunde inte lista hemmappen %s: %s" % (miljo.hem, e))

    ut = []
    sedda = set()
    for sokvag, kalla in kandidater:
        if not os.path.isdir(os.path.join(sokvag, "drive_c")):
            continue
        riktig = os.path.realpath(sokvag)
        if riktig in sedda:
            continue
        sedda.add(riktig)
        ut.append((sokvag, kalla))
    return ut


# --------------------------------------------------------------------------
# Dokumentrotter
# --------------------------------------------------------------------------

def _windowsrotter(miljo):
    ut = []
    personal = miljo.hemta_skalmapp()
    if personal:
        ut.append((personal, miljo.skalmapp_kalla))
    profil = miljo.env.get("USERPROFILE")
    if profil:
        ut.append((os.path.join(profil, "Documents"), "%USERPROFILE%\\Documents"))
    ut.append((os.path.join(miljo.hem, "Documents"), "~/Documents"))
    for nyckel in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        rot = miljo.env.get(nyckel)
        if rot:
            ut.append((os.path.join(rot, "Documents"), "%%%s%%\\Documents" % nyckel))
    return ut


def _winerotter(miljo):
    ut = []
    for prefix, kalla in wineprefix(miljo):
        anvandarrot = os.path.join(prefix, "drive_c", "users")
        try:
            anvandare = sorted(os.listdir(anvandarrot))
        except OSError as e:
            miljo.varna("kunde inte lasa %s: %s" % (anvandarrot, e))
            continue
        for namn in anvandare:
            if namn.lower() == "public":
                continue
            for dokumentnamn in ("Documents", "My Documents"):
                ut.append((os.path.join(anvandarrot, namn, dokumentnamn),
                           "%s (%s)" % (kalla, namn)))
    return ut


def dokumentrotter(miljo=None):
    """Alla dokumentmappar som finns, deduplicerade pa realpath.

    Dedupliceringen ar inte kosmetik. M-02: ett kopierat wine-prefix delar
    ``Documents`` med originalet via symlank, och den som inte loser upp
    lanken tror att den installerar i tva mappar men skriver i en.
    """
    if miljo is None:
        miljo = Miljo()

    kandidater = _windowsrotter(miljo) if miljo.ar_windows else _winerotter(miljo)

    per_riktig = {}
    ordning = []
    for sokvag, kalla in kandidater:
        if not os.path.isdir(sokvag):
            continue
        riktig = os.path.realpath(sokvag)
        if riktig not in per_riktig:
            per_riktig[riktig] = []
            ordning.append(riktig)
        absolut = os.path.abspath(sokvag)
        etikett = kalla if riktig == absolut else "%s -> %s" % (kalla, absolut)
        if etikett not in per_riktig[riktig]:
            per_riktig[riktig].append(etikett)
    return [Dokumentrot(sokvag=r, kallor=tuple(per_riktig[r])) for r in ordning]


# --------------------------------------------------------------------------
# VC-mappar under en dokumentrot
# --------------------------------------------------------------------------

def _lista(mapp, miljo):
    try:
        return sorted(os.listdir(mapp))
    except OSError as e:
        if miljo is not None:
            miljo.varna("kunde inte lasa %s: %s" % (mapp, e))
        return []


def pythonnivaer(my_commands, miljo=None):
    """De ``Python N``-mappar som FAKTISKT finns under My Commands."""
    ut = []
    for namn in _lista(my_commands, miljo):
        m = _PYNIVA_RE.match(namn)
        if m and os.path.isdir(os.path.join(my_commands, namn)):
            ut.append((int(m.group(1)), namn))
    return tuple(namn for _n, namn in sorted(ut))


def vcmappar_i(rot, miljo=None):
    """``<rot>/<foretag>/<version>/My Commands``, allt som finns.

    Tva nivaer djupt, inte fler: djupare sokning hittar sakerhetskopior och
    exporterade layouter och kostar tid pa en stor dokumentmapp.
    """
    ut = []
    for foretag in _lista(rot.sokvag, miljo):
        foretagsmapp = os.path.join(rot.sokvag, foretag)
        if not os.path.isdir(foretagsmapp):
            continue
        for version in _lista(foretagsmapp, miljo):
            my_commands = os.path.join(foretagsmapp, version, MY_COMMANDS)
            if not os.path.isdir(my_commands):
                continue
            ut.append(VcMapp(
                my_commands=my_commands,
                foretag=foretag,
                version=version,
                dokumentrot=rot.sokvag,
                kallor=rot.kallor,
                pythonnivaer=pythonnivaer(my_commands, miljo),
            ))
    return ut


def vcmappar(miljo=None):
    """Alla funna VC-mappar, nyaste versionen forst."""
    if miljo is None:
        miljo = Miljo()
    ut = []
    for rot in dokumentrotter(miljo):
        ut.extend(vcmappar_i(rot, miljo))
    ut.sort(key=lambda m: (m.nyckel, m.my_commands), reverse=True)
    return ut


# --------------------------------------------------------------------------
# Programinstallationer - formageprovning utan licens
# --------------------------------------------------------------------------

def _programrotter(miljo):
    ut = []
    if miljo.ar_windows:
        for nyckel in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            rot = miljo.env.get(nyckel)
            if rot:
                ut.append(rot)
        ut.append(os.path.join(miljo.env.get("SystemDrive", "C:") + os.sep, "Program Files"))
    else:
        for prefix, _kalla in wineprefix(miljo):
            ut.append(os.path.join(prefix, "drive_c", "Program Files"))
            ut.append(os.path.join(prefix, "drive_c", "Program Files (x86)"))
    sedda = set()
    kvar = []
    for rot in ut:
        riktig = os.path.realpath(rot)
        if riktig in sedda or not os.path.isdir(rot):
            continue
        sedda.add(riktig)
        kvar.append(rot)
    return kvar


def _nivaer_med_api(produktmapp, miljo):
    ut = []
    for namn in _lista(produktmapp, miljo):
        m = _PYNIVA_RE.match(namn)
        if not m:
            continue
        api = os.path.join(produktmapp, namn, "Auto Complete", "api.xml")
        if os.path.isfile(api):
            ut.append((int(m.group(1)), namn))
    return tuple(namn for _n, namn in sorted(ut))


def programinstallationer(miljo=None):
    """VC-installationer pa disk, funna pa ``Python N/Auto Complete/api.xml``.

    Sokdjup: ``<Program Files>/<leverantor>/<produkt>`` och
    ``<Program Files>/<produkt>``. Bada forekommer; har ligger den under
    leverantorsmappen ``Visual Components``.
    """
    if miljo is None:
        miljo = Miljo()
    ut = []
    sedda = set()
    for rot in _programrotter(miljo):
        kandidater = []
        for niva1 in _lista(rot, miljo):
            m1 = os.path.join(rot, niva1)
            if not os.path.isdir(m1):
                continue
            kandidater.append(m1)
            for niva2 in _lista(m1, miljo):
                m2 = os.path.join(m1, niva2)
                if os.path.isdir(m2):
                    kandidater.append(m2)
        for produktmapp in kandidater:
            riktig = os.path.realpath(produktmapp)
            if riktig in sedda:
                continue
            nivaer = _nivaer_med_api(produktmapp, miljo)
            if not nivaer:
                continue
            sedda.add(riktig)
            ut.append(Programinstallation(
                sokvag=produktmapp,
                produkt=os.path.basename(produktmapp),
                pythonnivaer=nivaer,
            ))
    ut.sort(key=lambda p: (versionsnyckel(p.produkt), p.sokvag), reverse=True)
    return ut


def sok(miljo=None):
    """Hela sokningen i ett anrop. Skriver ingenting."""
    if miljo is None:
        miljo = Miljo()
    rotter = dokumentrotter(miljo)
    mappar = []
    for rot in rotter:
        mappar.extend(vcmappar_i(rot, miljo))
    mappar.sort(key=lambda m: (m.nyckel, m.my_commands), reverse=True)
    return Sokresultat(
        dokumentrotter=rotter,
        vcmappar=mappar,
        programinstallationer=programinstallationer(miljo),
        varningar=list(miljo.varningar),
    )


# --------------------------------------------------------------------------
# Val av niva
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Nivaval:
    namn: str
    kalla: str          # vald | funnen | funnen-flera | harledd
    matt: bool          # sant bara for 4.x + "Python 2" (M-01)
    motivering: str


class IngenNiva(Exception):
    """Nivan gar varken att hitta eller harleda. Vi gissar inte."""


def valj_pythonniva(vcmapp, onskad=None):
    """Vilken ``Python N`` tillagget ska ligga under.

    Ordning: uttryckligt val, sedan vad som FINNS pa disk, sist en harledning
    ur versionsnumret. Gar inget av det gar installationen inte att gora, och
    da kastar den - den valjer inte en sannolik mapp och later VC tiga
    (M-01: fel niva = kroken fyrar aldrig, utan ett ord).
    """
    finns = tuple(vcmapp.pythonnivaer)
    forvantad = forvantad_pythonniva(vcmapp.version)

    if onskad:
        namn = pythonnivanamn(onskad)
        if namn is None:
            raise IngenNiva("nivanamnet %r ser inte ut som 'Python N'" % (onskad,))
        return Nivaval(
            namn=namn,
            kalla="vald",
            matt=sokvagen_ar_matt(vcmapp.version, namn),
            motivering="vald pa kommandoraden%s" % (
                "" if namn in finns else " (mappen finns inte an, den skapas)"),
        )

    if len(finns) == 1:
        namn = finns[0]
        return Nivaval(
            namn=namn, kalla="funnen",
            matt=sokvagen_ar_matt(vcmapp.version, namn),
            motivering="enda Python N-mappen under %s" % MY_COMMANDS)

    if len(finns) > 1:
        namn = forvantad if forvantad in finns else finns[-1]
        return Nivaval(
            namn=namn, kalla="funnen-flera",
            matt=sokvagen_ar_matt(vcmapp.version, namn),
            motivering="flera nivaer finns (%s); vald: %s" % (", ".join(finns), namn))

    if forvantad is None:
        raise IngenNiva(
            "ingen Python N-mapp under %s och versionen %r gar inte att lasa "
            "som ett tal - ange --python-niva" % (vcmapp.my_commands, vcmapp.version))

    return Nivaval(
        namn=forvantad, kalla="harledd",
        matt=sokvagen_ar_matt(vcmapp.version, forvantad),
        motivering="ingen Python N-mapp fanns; harledd ur versionen %s"
                   % vcmapp.version)


def valj_vcmapp(mappar, version=None):
    """Nyaste versionen, eller den som begarts. Tom lista ger None."""
    if not mappar:
        return None
    if version is None:
        return mappar[0]
    traffar = [m for m in mappar if m.version == version]
    if not traffar:
        return None
    return traffar[0]
