# -*- coding: utf-8 -*-
"""L1: tillagget kompileras av en RIKTIG Python 2.7, inte av en ordlista.

`test_tillagg_syntax.py` provar 2.7-giltigheten med en handskriven lista over
konstruktioner som inte finns i 2.7: f-strangar, unicode_literals, exec i en
nastlad funktion. Listan ar byggd ur vad nagon rakade komma ihag - samma form
som M-70:s monster, som hade atta doda grenar i manader utan att nagon sag det.

En riktig 2.7 behover ingen lista. Den provet har kor `py_compile` i en
python:2.7-slim-container over varje fil i tillagget.

Hoppas over med SKAL nar varken docker eller en python2 finns. Ett hopp ar inte
ett godkannande, och det star i utskriften vilket det var.
"""
import glob
import os
import shutil
import subprocess

import pytest

_TILLAGG = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "ext", "vc_addon", "vc_assist"))
_AVBILD = "python:2.7-slim"

_KOD = (
    "import py_compile, os, sys\n"
    "fel = []\n"
    "for f in sorted(os.listdir('/m')):\n"
    "    if f.endswith('.py'):\n"
    "        try:\n"
    "            py_compile.compile('/m/' + f, cfile='/tmp/x.pyc', doraise=True)\n"
    "        except Exception as e:\n"
    "            fel.append('%s: %s' % (f, e))\n"
    "sys.stdout.write('\\n'.join(fel))\n"
)


def _har_avbilden():
    if not shutil.which("docker"):
        return False
    k = subprocess.run(["docker", "image", "inspect", _AVBILD],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return k.returncode == 0


def _kompilera_med_27(katalog):
    """Returnerar felraderna som en lista. Tom lista = allt kompilerade."""
    k = subprocess.run(
        ["docker", "run", "--rm", "--network", "none",
         "-v", "%s:/m:ro" % katalog, _AVBILD, "python", "-c", _KOD],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if k.returncode != 0:
        pytest.fail("containern foll: %s" % k.stderr.decode("utf-8", "replace"))
    ut = k.stdout.decode("utf-8", "replace").strip()
    return [r for r in ut.splitlines() if r.strip()]


riktig27 = pytest.mark.skipif(
    not _har_avbilden(),
    reason="python:2.7-slim saknas lokalt; hamta med `docker pull python:2.7-slim`")


@riktig27
def test_varje_tillaggsfil_kompilerar_i_riktig_python_27():
    fel = _kompilera_med_27(_TILLAGG)
    assert not fel, "Python 2.7 avvisade %d fil(er):\n  %s" % (
        len(fel), "\n  ".join(fel))


@riktig27
def test_grinden_faller_verkligen_en_fil_som_bara_3x_forstar(tmp_path):
    """Trasig fixtur. Utan den vet vi bara att grinden ar TYST.

    Tre konstruktioner som Python 3 tar utan att blinka och 2.7 vagrar. Varje
    fil provas for sig, sa provet visar att det ar konstruktionen som falls
    och inte katalogen i stort.
    """
    fall = {
        "fstrang.py": "namn = 'x'\nprint(f'hej {namn}')\n",
        "annotering.py": "def f(x: int) -> int:\n    return x\n",
        "valrossen.py": "if (n := 3) > 2:\n    print(n)\n",
    }
    for filnamn, kod in fall.items():
        d = tmp_path / filnamn[:-3]
        d.mkdir()
        (d / filnamn).write_text(kod, encoding="utf-8")
        fel = _kompilera_med_27(str(d))
        assert fel, "%s slapptes igenom av 2.7-grinden" % filnamn
        assert filnamn in fel[0]


@riktig27
def test_en_helt_vanlig_27_fil_slapps_igenom(tmp_path):
    """Andra halvan: en grind som fyrar pa allt mater ingenting."""
    d = tmp_path / "ok"
    d.mkdir()
    (d / "vanlig.py").write_text(
        "from __future__ import print_function\n"
        "def f(x):\n    return '%s' % x\n", encoding="utf-8")
    assert _kompilera_med_27(str(d)) == []
