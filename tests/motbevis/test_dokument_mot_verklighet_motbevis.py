# -*- coding: utf-8 -*-
"""Motbevis: påståenden i specen som inte har täckning i det som är byggt.

`96_ingen_skuld.md` listar tio regler och skriver ut en **mekanisk kontroll**
för var och en. `01_kalldisciplin.md` säger att ett DOK-påstående aldrig
ensamt får bli ett designbeslut. Proven nedan slår upp kontrollerna och
siffrorna där de påstås ligga.
"""
import ast
import os
import re
import subprocess
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _las(rel):
    with open(os.path.join(_ROT, rel), encoding="utf-8") as f:
        return f.read()


def _pyfiler(*kataloger):
    ut = []
    for kat in kataloger:
        for rot, ds, fs in os.walk(os.path.join(_ROT, kat)):
            ds[:] = [d for d in ds if d != "__pycache__"]
            ut += [os.path.join(rot, f) for f in sorted(fs) if f.endswith(".py")]
    return ut


# ---- S3: "scripts/check_reachability.py listar symboler utan referens" ---

def test_s3_kontrollen_check_reachability_finns():
    """96_ingen_skuld.md S3: *Kontroll:* `scripts/check_reachability.py` ...
    Ny föräldralös fil bryter bygget. Ingångspunkter deklareras i en
    manifestfil."""
    saknas = [p for p in ("scripts/check_reachability.py",)
              if not os.path.exists(os.path.join(_ROT, p))]
    assert not saknas, ("S3:s kontroll finns inte: %s (scripts/ är tom)"
                        % ", ".join(saknas))


# ---- S9: "linter avvisar except Exception: utan loggning" ----------------

def test_s9_inga_tysta_breda_undantag():
    """S9 mätte ett NameError som försvann i ett brett except och gjorde att
    en fix aldrig fyrade, tyst. Kontrollen är en linter. Den finns inte, och
    mönstret finns i koden — i pump.py, vars hela mätta felbild (M-06, M-09,
    M-13) är att fel försvinner tyst."""
    tysta = []
    for p in _pyfiler("ext", "svc", "bank"):
        trad = ast.parse(open(p, encoding="utf-8").read())
        for nod in ast.walk(trad):
            if not isinstance(nod, ast.ExceptHandler):
                continue
            brett = nod.type is None or (isinstance(nod.type, ast.Name)
                                         and nod.type.id == "Exception")
            if not brett:
                continue
            kropp = ast.dump(ast.Module(body=nod.body, type_ignores=[]))
            loggar = any(o in kropp for o in
                         ("logg", "_log", "print", "format_exc", "logger"))
            kastar = any(isinstance(x, ast.Raise) for x in ast.walk(nod))
            if not (loggar or kastar):
                tysta.append("%s:%d" % (os.path.relpath(p, _ROT), nod.lineno))
    assert not tysta, ("breda undantag utan loggning eller återkastning "
                       "(S9):\n  " + "\n  ".join(tysta))


# ---- S7: "varje dokument bär beskriver: med filsökvägar" ----------------

def test_s7_varje_specdokument_bar_beskriver():
    utan = []
    kat = os.path.join(_ROT, "docs", "spec")
    for f in sorted(os.listdir(kat)):
        if not f.endswith(".md"):
            continue
        if not re.search(r"^\*\*beskriver:\*\*|^beskriver:", _las("docs/spec/" + f),
                         re.M):
            utan.append("docs/spec/" + f)
    assert not utan, ("dokument utan `beskriver:` (S7):\n  " + "\n  ".join(utan))


def test_varje_beskriver_pekar_pa_nagot_som_finns():
    """fas1_bryggan.md säger `beskriver: ext/vc_addon/,
    service/vc_assist/bridge_client.py`. Den andra filen finns inte."""
    doda = []
    kat = os.path.join(_ROT, "tests", "protocol")
    for f in sorted(os.listdir(kat)):
        if not f.endswith(".md"):
            continue
        text = _las("tests/protocol/" + f)
        for rad in re.findall(r"^\*\*beskriver:\*\*(.+)$", text, re.M):
            for stig in re.findall(r"`([^`]+)`", rad):
                if stig.startswith("~"):
                    continue
                if not os.path.exists(os.path.join(_ROT, stig)):
                    doda.append("tests/protocol/%s -> %s" % (f, stig))
    assert not doda, ("`beskriver:` pekar på något som inte finns:\n  "
                      + "\n  ".join(doda))


# ---- siffror i protokollen mot vad som faktiskt är byggt ----------------

def test_antalet_apiytor_i_fas1_stammer_med_formagerapporten():
    sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
    import formaga
    text = _las("tests/protocol/fas1_bryggan.md")
    m = re.search(r"\*\*(\d+) av (\d+)\*\*, inga saknas", text)
    assert m, "hittade inte raden om API-ytor i fas1_bryggan.md"
    assert int(m.group(2)) == len(formaga.YTOR), (
        "fas1_bryggan.md säger %s ytor, formaga.YTOR har %d "
        "(fas5_verktygen.md säger 46). Två protokoll, två tal, en lista."
        % (m.group(2), len(formaga.YTOR)))


def test_antalet_enhetstester_i_fas1_stammer_med_sviten():
    text = _las("tests/protocol/fas1_bryggan.md")
    m = re.search(r"(\d+) av de (\d+)\s*\n?\s*enhetstesterna", text)
    assert m, "hittade inte raden om enhetstester i fas1_bryggan.md"
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/enhet",
                        "--collect-only", "-q", "-p", "no:cacheprovider"],
                       cwd=_ROT, capture_output=True, text=True, timeout=300)
    antal = int(re.search(r"(\d+) tests? collected", r.stdout).group(1))
    assert int(m.group(2)) == antal, (
        "fas1_bryggan.md säger %s enhetstester, sviten har %d"
        % (m.group(2), antal))


def test_utforarens_pastaende_om_att_vara_enda_stallet_haller():
    """utforare.py:13 — '1. Tabellen är det ENDA stället i tjänsten där
    operationsnamnen "exec" och "exec_queue" står.'"""
    traffar = []
    for p in _pyfiler("svc"):
        rel = os.path.relpath(p, _ROT)
        for nr, rad in enumerate(open(p, encoding="utf-8"), 1):
            if rel.endswith("utforare.py"):
                continue
            # Bara stallen dar namnet anvands SOM operation, inte i en
            # ordlista over inbyggda namn (api_index.py:127).
            if re.search(r'anrop\(\s*"exec(?:_queue)?"|op == "exec(?:_queue)?"', rad):
                traffar.append("%s:%d %s" % (rel, nr, rad.strip()[:70]))
    assert not traffar, (
        "operationsnamnen står på fler ställen än tabellen:\n  "
        + "\n  ".join(traffar))
