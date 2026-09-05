# -*- coding: utf-8 -*-
"""Kopiera tillagget dit, verifiera det pa plats, och ta bort exakt det igen.

Varfor verifieringen finns, mycket kort: VC svaljer ett trasigt tillagg HELT
tyst. I M-09 returnerade ``loadCommand`` ett anvandbart objekt, ``execute()``
kastade ingenting, min egen krok loggade "executed" - och modulkroppen kordes
aldrig. Ett fel som RAPPORTERAR ATT DET GICK BRA gar inte att hitta i en logg.
Det maste fangas pa disk, fore start. Det ar vad ``granska_pythonfiler`` gor,
och installationen kor den bade pa kallan och pa malet.

Varfor manifestet finns: en avinstallation som gissar vilka filer som var dess
egna raderar antingen for lite eller for mycket. Manifestet ar listan, med
sha256 per fil, skriven av installationen sjalv.
"""
from __future__ import annotations

import ast
import datetime
import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field

PAKETNAMN = "vc_assist"
MANIFESTNAMN = "vc_assist_installation.json"
MANIFESTFORMAT = 1

# Mallen ar en strang inne i en strang, och just det ledet brast i M-09.
# Den provas darfor formaterad, med samma nycklar som bridge_cmd.py anvander.
MALLENS_NYCKLAR = {"dir": "C:\\\\en\\\\mapp", "port": 8901}


class InstallationsFel(Exception):
    """Installationen gick inte att genomfora. Den returnerar aldrig framgang."""


class Verifieringsfel(InstallationsFel):
    """Filerna gick inte att lita pa. Bararen av detaljerna ar ``problem``."""

    def __init__(self, meddelande, problem):
        InstallationsFel.__init__(self, "%s\n  - %s" % (meddelande, "\n  - ".join(problem)))
        self.problem = list(problem)


# --------------------------------------------------------------------------
# Kallan
# --------------------------------------------------------------------------

def kallmapp():
    """``ext/vc_addon/vc_assist`` i det klonade repot."""
    har = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(har, "..", "ext", "vc_addon", PAKETNAMN))


def kallfiler(mapp):
    """Tillaggets filer: alla ``*.py`` direkt i mappen, i namnordning.

    Inga undermappar. VC laddar paketet som en enda mapp, och allt som inte
    ar en modul dar hor inte hemma i installationen.
    """
    if not os.path.isdir(mapp):
        raise InstallationsFel("source folder does not exist: %s" % mapp)
    filer = sorted(n for n in os.listdir(mapp)
                   if n.endswith(".py") and os.path.isfile(os.path.join(mapp, n)))
    if "__init__.py" not in filer:
        raise InstallationsFel(
            "%s saknar __init__.py - utan den ar det inget VC-tillagg" % mapp)
    return filer


def sha256(sokvag):
    h = hashlib.sha256()
    with open(sokvag, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def kallsumma(mapp, filer):
    """En summa over hela uppsattningen, sa "ar installationen aktuell" gar att svara pa."""
    h = hashlib.sha256()
    for namn in sorted(filer):
        h.update(namn.encode("utf-8"))
        h.update(b"\0")
        h.update(sha256(os.path.join(mapp, namn)).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


# --------------------------------------------------------------------------
# Grinden: gar filerna att ladda?
# --------------------------------------------------------------------------

def _skriptmall(kalla, namn):
    """``SKRIPT``-tilldelningens VERKLIGA varde, hamtat via ast.

    En regex over filtexten ger fel svar: ett ``\\n`` i kallan ar en RIKTIG
    radbrytning i mallens varde. Det var precis den skillnaden som gav ett
    gront test och en trasig verklighet.
    """
    trad = ast.parse(kalla, filename=namn)
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Assign):
            for mal in nod.targets:
                if isinstance(mal, ast.Name) and mal.id == "SKRIPT":
                    return ast.literal_eval(nod.value)
    return None


def _py2fallor(trad, kalla, namn):
    """Fel som Python 3 kompilerar men VC:s Python 2.7 vagrar (M-09, E5).

    Bada har fallt pa riktigt: f-strangar finns inte i 2.7, och ``exec`` i en
    funktion som ocksa innehaller en nastlad funktion ar olagligt i 2.7 och
    gjorde hela bridge_cmd.py okompilerbar - tyst (M-09).
    """
    problem = []
    for nod in ast.walk(trad):
        if isinstance(nod, ast.JoinedStr):
            problem.append("%s rad %s: f-strang, finns inte i Python 2.7"
                           % (namn, getattr(nod, "lineno", "?")))
        elif type(nod).__name__ == "Nonlocal":
            problem.append("%s rad %s: nonlocal finns inte i Python 2.7"
                           % (namn, getattr(nod, "lineno", "?")))
        elif type(nod).__name__ in ("AsyncFunctionDef", "AsyncWith", "AsyncFor", "Await"):
            problem.append("%s rad %s: async/await finns inte i Python 2.7"
                           % (namn, getattr(nod, "lineno", "?")))
        elif isinstance(nod, ast.FunctionDef):
            if getattr(nod, "returns", None):
                problem.append("%s: %s() har returtypsannotering, finns inte i Python 2.7"
                               % (namn, nod.name))
            for arg in getattr(nod.args, "args", []) + getattr(nod.args, "kwonlyargs", []):
                if getattr(arg, "annotation", None):
                    problem.append("%s: %s(%s: ...) har parameterannotering, finns inte i Python 2.7"
                                   % (namn, nod.name, getattr(arg, "arg", "?")))
            har_exec = any(isinstance(n, ast.Call) and getattr(n.func, "id", None) == "exec"
                           for n in ast.walk(nod))
            if har_exec:
                nastlade = [n for n in ast.walk(nod)
                            if isinstance(n, (ast.Lambda, ast.FunctionDef)) and n is not nod]
                if nastlade:
                    problem.append("%s: %s() blandar exec med en nastlad funktion - "
                                   "olagligt i Python 2.7" % (namn, nod.name))

    if "unicode_literals" in kalla and ".Name = " in kalla and "def _s(" not in kalla:
        problem.append("%s har unicode_literals och skriver till VC utan _s() (M-05)" % namn)

    return problem


def _crlf_problem(namn):
    """Meddelandet for en fil med CRLF. Egen funktion sa provet kan citera det."""
    return ("%s har CRLF-radslut. Filen kopieras BYTE FOR BYTE in i VC, och "
            "bridge_cmd.py:s SKRIPT ar en strang vars varde da bar \\r\\n - "
            "Python 2:s compile() tar bara \\n. Orsaken ar nastan alltid "
            "core.autocrlf=true, som Git for Windows satter som standard. "
            "Repots .gitattributes tvingar LF; kor 'git rm --cached -r . && "
            "git reset --hard' i en ren klon, eller ratta filen for hand."
            % namn)


def granska_pythonfiler(mapp, filer, pythonniva=None, krav_bada=False):
    """Lista over problem. Tom lista betyder att filerna gar att ladda.

    Prover, i ordning:
      1. filen finns och gar att lasa som UTF-8
      2. den har LF-radslut, inte CRLF (M-44: en klon med core.autocrlf=true
         ger CRLF, och SKRIPT-strangen inne i bridge_cmd.py blir da okompilerbar
         for VC:s Python 2 - men helt gron i den har vardmaskinens Python 3)
      3. den parsar och kompilerar
      4. ``__init__.py`` definierar ``OnAppInitialized`` - utan den gor VC
         ingenting med tillagget, och sager inget om det heller
      5. ``bridge_cmd.py``:s SKRIPT-mall parsar EFTER formatering, och borjar
         med ``from vcScript import *`` (utan den raden finns varken delay()
         eller getSimulation(), och OnRun dor tyst - M-06)
      6. pa en Python 2-niva eller nar krav_bada ar satt: inga py2-fallor
         (E5: allt i ext/ maste vara giltigt i BADE Python 2.7 och 3.x)

    Punkt 3 kors av VARDMASKINENS Python 3. Punkt 6 garanterar att py2-fallor
    fångas aven vid installation pa en Python 3-niva.
    """
    problem = []
    for namn in filer:
        sokvag = os.path.join(mapp, namn)
        if not os.path.isfile(sokvag):
            problem.append("%s saknas i %s" % (namn, mapp))
            continue
        try:
            with open(sokvag, "rb") as f:
                ravaror = f.read()
            kalla = ravaror.decode("utf-8")
        except (OSError, UnicodeDecodeError) as e:
            problem.append("%s gar inte att lasa: %s" % (namn, e))
            continue

        if b"\r\n" in ravaror:
            problem.append(_crlf_problem(namn))
            continue
        try:
            trad = ast.parse(kalla, filename=sokvag)
            compile(kalla, sokvag, "exec")
        except SyntaxError as e:
            problem.append("%s rad %s: %s" % (namn, e.lineno, e.msg))
            continue

        if namn == "__init__.py":
            krokar = [n.name for n in ast.walk(trad) if isinstance(n, ast.FunctionDef)]
            if "OnAppInitialized" not in krokar:
                problem.append("__init__.py definierar ingen OnAppInitialized - "
                               "VC anropar den vid uppstart och gor annars inget")

        if namn == "bridge_cmd.py":
            mall = _skriptmall(kalla, sokvag)
            if mall is None:
                problem.append("bridge_cmd.py saknar SKRIPT-tilldelningen")
            else:
                try:
                    compile(mall % MALLENS_NYCKLAR, "<SKRIPT>", "exec")
                except SyntaxError as e:
                    problem.append("SKRIPT-mallen i bridge_cmd.py gar inte att "
                                   "kompilera efter formatering: rad %s: %s"
                                   % (e.lineno, e.msg))
                except (KeyError, ValueError, TypeError) as e:
                    problem.append("SKRIPT-mallen gar inte att formatera: %r" % (e,))
                if not mall.lstrip().startswith("from vcScript import *"):
                    problem.append("SKRIPT-mallen borjar inte med "
                                   "'from vcScript import *' - OnRun dor tyst (M-06)")

        # E5: Allt i ext/ maste vara giltigt i BADE Python 2.7 och 3.x.
        if krav_bada or not pythonniva or pythonniva.strip().lower() == "python 2":
            problem.extend(_py2fallor(trad, kalla, namn))

    return problem


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def manifestsokvag(malmapp):
    return os.path.join(malmapp, MANIFESTNAMN)


def las_manifest(malmapp):
    """Manifestet, eller None om ingen installation gjord av oss finns dar."""
    sokvag = manifestsokvag(malmapp)
    if not os.path.isfile(sokvag):
        return None
    try:
        with open(sokvag, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise InstallationsFel("cannot read manifest %s: %s" % (sokvag, e))
    if data.get("format") != MANIFESTFORMAT:
        raise InstallationsFel(
            "manifestet %s har format %r, denna installation kan format %d"
            % (sokvag, data.get("format"), MANIFESTFORMAT))
    return data


def _skriv_manifest(malmapp, data):
    with open(manifestsokvag(malmapp), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


# --------------------------------------------------------------------------
# Installation
# --------------------------------------------------------------------------

@dataclass
class Installationsrapport:
    malmapp: str = ""
    vc_version: str = ""
    pythonniva: str = ""
    nivakalla: str = ""
    sokvagen_ar_matt: bool = False
    nya: list = field(default_factory=list)
    uppdaterade: list = field(default_factory=list)
    oforandrade: list = field(default_factory=list)
    borttagna: list = field(default_factory=list)     # foraldralosa fran en tidigare version
    skapade_mappar: list = field(default_factory=list)
    kallsumma: str = ""

    @property
    def antal(self):
        return len(self.nya) + len(self.uppdaterade) + len(self.oforandrade)


def _skapa_mappar(malmapp):
    """Skapa malmappen och returnera de mappar VI skapade, ytterst forst."""
    skapade = []
    saknade = []
    p = malmapp
    while p and not os.path.isdir(p):
        saknade.append(p)
        foralder = os.path.dirname(p)
        if foralder == p:
            break
        p = foralder
    try:
        os.makedirs(malmapp, exist_ok=True)
    except OSError as e:
        raise InstallationsFel(
            "kunde inte skapa %s: %s\n"
            "  Mappen ovanfor ar antagligen skrivskyddad. Ratta rattigheterna "
            "eller ange en annan mapp med --mal." % (malmapp, e))
    skapade.extend(reversed(saknade))
    return skapade


def installera(malmapp, kalla=None, pythonniva=None, vc_version="", nivakalla="",
               sokvagen_ar_matt=False):
    """Lagg tillagget i ``malmapp``. Kastar hellre an lamnar nagot halvt.

    Ordningen ar vald sa att en trasig kalla ALDRIG ror maldisken:
    kallan granskas forst, sedan skrivs filerna, sedan granskas malet.
    Faller malgranskningen tas det nyss skrivna bort igen - ett halvt
    tillagg i VC ar varre an inget, eftersom VC inte sager nagot om det.
    """
    if kalla is None:
        kalla = kallmapp()
    filer = kallfiler(kalla)

    problem = granska_pythonfiler(kalla, filer, pythonniva, krav_bada=True)
    if problem:
        raise Verifieringsfel(
            "kallan i %s gar inte att ladda - ingenting installerat" % kalla, problem)

    rapport = Installationsrapport(
        malmapp=malmapp,
        vc_version=vc_version,
        pythonniva=pythonniva or "",
        nivakalla=nivakalla,
        sokvagen_ar_matt=bool(sokvagen_ar_matt),
        kallsumma=kallsumma(kalla, filer),
    )
    rapport.skapade_mappar = _skapa_mappar(malmapp)

    gammalt = las_manifest(malmapp)
    if gammalt:
        rapport.skapade_mappar = list(gammalt.get("skapade_mappar", [])) or rapport.skapade_mappar

    summor = {}
    try:
        for namn in filer:
            fran = os.path.join(kalla, namn)
            till = os.path.join(malmapp, namn)
            summa = sha256(fran)
            summor[namn] = summa
            if os.path.isfile(till) and sha256(till) == summa:
                # Identisk fil skrivs inte om. Idempotens ar inte bara "samma
                # slutlage" - en omskrivning andrar mtime och far VC att
                # kompilera om i onodan.
                rapport.oforandrade.append(namn)
                continue
            fanns = os.path.isfile(till)
            shutil.copyfile(fran, till)
            (rapport.uppdaterade if fanns else rapport.nya).append(namn)

        # S4: det som ersatts tas bort, det etiketteras inte. Filer som en
        # tidigare version av tillagget lade dit men som inte finns kvar i
        # kallan ska INTE bli liggande och laddas av VC.
        if gammalt:
            for namn in sorted(gammalt.get("filer", {})):
                if namn not in summor:
                    _ta_bort_fil(os.path.join(malmapp, namn), rapport.borttagna)

        _skriv_manifest(malmapp, {
            "format": MANIFESTFORMAT,
            "installerad": datetime.datetime.now().replace(microsecond=0).isoformat(),
            "kalla": os.path.abspath(kalla),
            "mal": os.path.abspath(malmapp),
            "vc_version": vc_version,
            "pythonniva": pythonniva or "",
            "nivakalla": nivakalla,
            "sokvagen_ar_matt": bool(rapport.sokvagen_ar_matt),
            "filer": summor,
            "kallsumma": rapport.kallsumma,
            "skapade_mappar": list(rapport.skapade_mappar),
        })
    except OSError as e:
        raise InstallationsFel("could not write to %s: %s" % (malmapp, e))

    problem = granska_malet(malmapp, summor, pythonniva, krav_bada=True)
    if problem:
        stadat, stadfel = _stada_efter_misslyckad(malmapp, list(summor) + [MANIFESTNAMN],
                                                  rapport.skapade_mappar)
        if stadfel:
            problem.append("kunde inte stada undan alltihop: %s" % "; ".join(stadfel))
        else:
            problem.append("de %d skrivna filerna togs bort igen" % stadat)
        raise Verifieringsfel("the installation in %s cannot be trusted" % malmapp, problem)

    return rapport


def granska_malet(malmapp, summor, pythonniva=None, krav_bada=False):
    """Filerna PA PLATS: ratt innehall (sha256) och gar de att ladda."""
    problem = []
    for namn in sorted(summor):
        sokvag = os.path.join(malmapp, namn)
        if not os.path.isfile(sokvag):
            problem.append("%s kom aldrig fram till %s" % (namn, malmapp))
            continue
        if sha256(sokvag) != summor[namn]:
            problem.append("%s skiljer sig fran kallan efter kopieringen" % namn)
    problem.extend(granska_pythonfiler(malmapp, sorted(summor), pythonniva, krav_bada=krav_bada))
    return problem


def _stada_efter_misslyckad(malmapp, namn, skapade_mappar):
    borttagna = 0
    fel = []
    for n in namn:
        sokvag = os.path.join(malmapp, n)
        try:
            if os.path.isfile(sokvag):
                os.remove(sokvag)
                borttagna += 1
        except OSError as e:
            fel.append("%s: %s" % (sokvag, e))
    for mapp in reversed(list(skapade_mappar) + [malmapp]):
        try:
            if os.path.isdir(mapp) and not os.listdir(mapp):
                os.rmdir(mapp)
        except OSError as e:
            fel.append("%s: %s" % (mapp, e))
    return borttagna, fel


# --------------------------------------------------------------------------
# Avinstallation
# --------------------------------------------------------------------------

@dataclass
class Avinstallationsrapport:
    malmapp: str = ""
    borttagna: list = field(default_factory=list)
    saknades: list = field(default_factory=list)      # stod i manifestet, fanns inte
    andrade: list = field(default_factory=list)       # andrade sedan installationen
    bytekod: list = field(default_factory=list)
    kvar: list = field(default_factory=list)          # frammande filer, lamnade i fred
    mappar_borttagna: list = field(default_factory=list)


def _ta_bort_fil(sokvag, lista):
    if os.path.isfile(sokvag):
        os.remove(sokvag)
        lista.append(os.path.basename(sokvag))
        return True
    return False


def _bytekodsfiler(malmapp, namn):
    """Bytekod som VC:s Python skapat ur VAR fil, och ingen annans.

    Python 2 lagger ``pump.pyc`` bredvid ``pump.py``, Python 3 lagger
    ``__pycache__/pump.cpython-3X.pyc``. Bada raknas som vart avfall.
    """
    stam = namn[:-3] if namn.endswith(".py") else namn
    ut = [os.path.join(malmapp, stam + ".pyc"), os.path.join(malmapp, stam + ".pyo")]
    cache = os.path.join(malmapp, "__pycache__")
    if os.path.isdir(cache):
        try:
            for n in sorted(os.listdir(cache)):
                if n == stam + ".pyc" or n.startswith(stam + "."):
                    ut.append(os.path.join(cache, n))
        except OSError:
            pass
    return ut


def avinstallera(malmapp):
    """Ta bort exakt det manifestet listar, och ingenting annat.

    Utan manifest gors ingenting. Att gissa vilka filer som var vara ar
    precis det som gor en avinstallation farlig: mappen kan lika garna
    innehalla operatorens egna kommandon.
    """
    malmapp = os.path.abspath(malmapp)
    manifest = las_manifest(malmapp)
    if manifest is None:
        raise InstallationsFel(
            "inget manifest i %s - da vet jag inte vilka filer som ar mina, "
            "och gissar inte. Ta bort mappen for hand om den ar din." % malmapp)

    rapport = Avinstallationsrapport(malmapp=malmapp)
    filer = manifest.get("filer", {})
    try:
        for namn in sorted(filer):
            sokvag = os.path.join(malmapp, namn)
            if not os.path.isfile(sokvag):
                rapport.saknades.append(namn)
                continue
            if sha256(sokvag) != filer[namn]:
                rapport.andrade.append(namn)
            for bytekod in _bytekodsfiler(malmapp, namn):
                _ta_bort_fil(bytekod, rapport.bytekod)
            os.remove(sokvag)
            rapport.borttagna.append(namn)

        _ta_bort_fil(manifestsokvag(malmapp), rapport.borttagna)

        cache = os.path.join(malmapp, "__pycache__")
        if os.path.isdir(cache) and not os.listdir(cache):
            os.rmdir(cache)

        rapport.kvar = sorted(os.listdir(malmapp)) if os.path.isdir(malmapp) else []
        if not rapport.kvar:
            # Innerst forst. skapade_mappar ar sparad ytterst forst, och
            # innehaller malmappen sjalv nar installationen skapade den.
            kandidater = [os.path.abspath(m)
                          for m in reversed(manifest.get("skapade_mappar", []))]
            if malmapp not in kandidater:
                kandidater.insert(0, malmapp)
            for mapp in kandidater:
                if os.path.isdir(mapp) and not os.listdir(mapp):
                    os.rmdir(mapp)
                    rapport.mappar_borttagna.append(mapp)
                else:
                    break
    except OSError as e:
        raise InstallationsFel("the uninstall in %s broke off halfway: %s"
                               % (malmapp, e))
    return rapport


# --------------------------------------------------------------------------
# Kontroll av en befintlig installation
# --------------------------------------------------------------------------

@dataclass
class Kontrollrapport:
    malmapp: str = ""
    installerad: bool = False
    aktuell: bool = False
    manifest: dict = field(default_factory=dict)
    problem: list = field(default_factory=list)

    @property
    def ok(self):
        return self.installerad and not self.problem


def kontrollera(malmapp, kalla=None):
    """Ar tillagget installerat, oskadat, och samma som repots kalla?"""
    if kalla is None:
        kalla = kallmapp()
    rapport = Kontrollrapport(malmapp=malmapp)
    manifest = las_manifest(malmapp)
    if manifest is None:
        rapport.problem.append("ingen installation i %s" % malmapp)
        return rapport
    rapport.installerad = True
    rapport.manifest = manifest
    summor = manifest.get("filer", {})
    rapport.problem.extend(granska_malet(malmapp, summor, manifest.get("pythonniva"), krav_bada=True))
    try:
        rapport.aktuell = kallsumma(kalla, kallfiler(kalla)) == manifest.get("kallsumma")
    except InstallationsFel as e:
        rapport.problem.append("kallan gar inte att jamfora mot: %s" % e)
    return rapport
