# -*- coding: utf-8 -*-
"""Svepet bakom M-105: vilka monster FYRAR under sviten, och vilka gor det aldrig.

    python3 -m pytest tests/enhet -q -p monsterbevis_svep

Kors som pytest-plugin (lagg katalogen pa PYTHONPATH). Varje kompilerat monster
pa modulniva under svc/ och ext/ byts mot en genomskinlig omslagare som raknar
traff och miss. Utfallet skrivs till $MATFIL (standard /tmp/monsterbevis.json).

VAD SVEPET AR OCH INTE AR
-------------------------
Det ar en KARTA over var man ska sikta, inte en bevisning. Att ett monster
returnerade en traff visar att det ANROPADES - inte att nagon KONTROLLERADE
svaret, och observationen forsvinner den dag det orelaterade provet skrivs om.
Bevisningen ligger i `tests/enhet/test_monsterbevis.py` som konkreta strangar.

MATT 2026-09-05 over 6452 prov: 116 monster, 100 avgor en dom. Av de 100 hade
68 bade en traff och en miss, 28 bara den ena, 4 kordes aldrig alls.
"""
import atexit
import importlib
import json
import os
import re
import sys

ROT = os.environ.get("MONSTERROT", os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
UT = os.environ.get("MATFIL", "/tmp/monsterbevis.json")
_NAMN = re.compile(r"^_?[A-Z][A-Z_0-9]*$")
_MONSTERTYP = type(re.compile(""))

sys.path.insert(0, os.path.join(ROT, "svc"))
sys.path.insert(0, os.path.join(ROT, "ext", "vc_addon", "vc_assist"))

STAT = {}


class Omslag(object):
    """Delegerar allt till det riktiga monstret, och raknar utfallet.

    Ingen arvning: `re.Pattern` gar inte att arva. `__getattr__` slapper igenom
    `.pattern`, `.flags` och allt annat, sa koden under provet ser ingen
    skillnad.
    """

    __slots__ = ("_p", "_k")

    def __init__(self, p, k):
        object.__setattr__(self, "_p", p)
        object.__setattr__(self, "_k", k)

    def __getattr__(self, n):
        return getattr(object.__getattribute__(self, "_p"), n)

    def _rakna(self, traff):
        STAT[object.__getattribute__(self, "_k")]["tr" if traff else "fa"] += 1

    def match(self, *a, **k):
        r = object.__getattribute__(self, "_p").match(*a, **k)
        self._rakna(r is not None)
        return r

    def search(self, *a, **k):
        r = object.__getattribute__(self, "_p").search(*a, **k)
        self._rakna(r is not None)
        return r

    def fullmatch(self, *a, **k):
        r = object.__getattribute__(self, "_p").fullmatch(*a, **k)
        self._rakna(r is not None)
        return r

    def findall(self, *a, **k):
        r = object.__getattribute__(self, "_p").findall(*a, **k)
        self._rakna(bool(r))
        return r

    def finditer(self, *a, **k):
        r = list(object.__getattribute__(self, "_p").finditer(*a, **k))
        self._rakna(bool(r))
        return iter(r)

    def sub(self, *a, **k):
        r, n = object.__getattribute__(self, "_p").subn(*a, **k)
        self._rakna(n > 0)
        return r

    def subn(self, *a, **k):
        r = object.__getattribute__(self, "_p").subn(*a, **k)
        self._rakna(r[1] > 0)
        return r

    def split(self, *a, **k):
        r = object.__getattribute__(self, "_p").split(*a, **k)
        self._rakna(len(r) > 1)
        return r


def _moduler():
    for bas in (os.path.join(ROT, "svc"),
                os.path.join(ROT, "ext", "vc_addon", "vc_assist")):
        for kat, undermappar, filer in os.walk(bas):
            undermappar[:] = [d for d in undermappar if d != "__pycache__"]
            for filnamn in sorted(filer):
                if not filnamn.endswith(".py") or filnamn == "__init__.py":
                    continue
                stig = os.path.join(kat, filnamn)
                yield (os.path.relpath(stig, bas)[:-3].replace(os.sep, "."),
                       os.path.relpath(stig, ROT).replace(os.sep, "/"))


def _installera():
    """Importera allt en gang och byt ut monstren. Proven far samma modulobjekt."""
    misslyckade = []
    for modnamn, fil in _moduler():
        try:
            m = importlib.import_module(modnamn)
        except Exception as e:                                   # noqa: BLE001
            misslyckade.append([fil, "%s: %s" % (type(e).__name__, e)])
            continue
        for namn in list(vars(m)):
            if not _NAMN.match(namn):
                continue
            v = getattr(m, namn)
            if not isinstance(v, _MONSTERTYP):
                continue
            nyckel = "%s::%s" % (fil, namn)
            if nyckel in STAT:
                continue
            STAT[nyckel] = {"tr": 0, "fa": 0}
            setattr(m, namn, Omslag(v, nyckel))
    return misslyckade


MISSLYCKADE = _installera()


@atexit.register
def _skriv():
    with open(UT, "w") as f:
        json.dump({"stat": STAT, "misslyckade_moduler": MISSLYCKADE}, f,
                  ensure_ascii=False, indent=1)
    sys.stderr.write("\nmonsterbevis_svep: %d monster, skrivet till %s\n"
                     % (len(STAT), UT))
