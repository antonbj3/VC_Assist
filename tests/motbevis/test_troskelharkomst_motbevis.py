# -*- coding: utf-8 -*-
"""Motbevis: tröskelhärkomsten mäter formen på en hänvisning, inte att den bär.

`tests/enhet/test_troskelharkomst.py` godkänner varje kommentar som matchar
`\\bM-\\d+\\b`. Den slår aldrig upp om mätningen finns. Alla elva trösklar i
ögat och utföraren pekar på M-10 respektive M-14 — och varken
`docs/matningar/M-10_*.md` eller `M-14_*.md` finns.

I2 i 90_invarianter.md: "Ett tal utan hänvisning till mätningen som satte det
är ett linterfel." En hänvisning till en mätning som inte finns är samma sak,
bara svårare att se.
"""
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_MATNINGAR = os.path.join(_ROT, "docs", "matningar")
_KODKATALOGER = [
    os.path.join(_ROT, "ext", "vc_addon", "vc_assist"),
    os.path.join(_ROT, "svc", "vc_assist_svc"),
    os.path.join(_ROT, "bank"),
]

_M = re.compile(r"\bM-(\d+)\b")
_KONSTANT = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)\s*(#.*)?$")


def _pyfiler():
    ut = []
    for kat in _KODKATALOGER:
        for rot, kataloger, filer in os.walk(kat):
            kataloger[:] = [d for d in kataloger if d != "__pycache__"]
            ut += [os.path.join(rot, f) for f in sorted(filer) if f.endswith(".py")]
    return sorted(ut)


def _matningar_pa_disk():
    return set(int(m.group(1))
               for m in (re.match(r"M-(\d+)_", f) for f in os.listdir(_MATNINGAR))
               if m)


def test_varje_matningshanvisning_i_koden_pekar_pa_en_matning_som_finns():
    """En hänvisning som inte går att slå upp är inte en härkomst."""
    finns = _matningar_pa_disk()
    doda = []
    for sokvag in _pyfiler():
        with open(sokvag, encoding="utf-8") as f:
            for nr, rad in enumerate(f, 1):
                for m in _M.finditer(rad):
                    if int(m.group(1)) not in finns:
                        doda.append("%s:%d  %s -> ingen fil i docs/matningar/"
                                    % (os.path.relpath(sokvag, _ROT), nr, m.group(0)))
    assert not doda, ("hänvisningar till mätningar som inte finns:\n  "
                      + "\n  ".join(doda))


def test_ingen_troskel_som_styr_en_dom_ar_fortfarande_preliminar():
    """I2: ett tal utan sin incident är ett linterfel.

    Alla tio trösklar i ögat bär ordet PRELIMINAR och pekar på en mätning som
    aldrig gjordes. Ögat är grind 5 i kedjan — den som fäller domen — och inte
    en enda av dess trösklar har mätt härkomst i dag.
    """
    finns = _matningar_pa_disk()
    utan = []
    for sokvag in _pyfiler():
        with open(sokvag, encoding="utf-8") as f:
            for nr, rad in enumerate(f, 1):
                m = _KONSTANT.match(rad.rstrip("\n"))
                if not m:
                    continue
                kommentar = (m.group(3) or "").strip()
                hanvisade = [int(x.group(1)) for x in _M.finditer(kommentar)]
                if hanvisade and all(h in finns for h in hanvisade):
                    continue
                utan.append("%s:%d %s = %s   %r"
                            % (os.path.relpath(sokvag, _ROT), nr,
                               m.group(1), m.group(2), kommentar))
    assert not utan, ("trösklar utan mätt härkomst:\n  " + "\n  ".join(utan))


def test_troskellintern_tacker_varje_modul_som_bar_en_troskel():
    """Lintern är riktad mot EN fil. Trösklarna bor i flera.

    `test_troskelharkomst.MODULER == ["oga_analys.py"]`, så
    `oga_provtagning.SKRIV_VAR_N_RAD`, `utforare.KO_POLL_S`,
    `utforare.KO_TIMEOUT_S` och `pump.MAX_KO` granskas av ingen.
    """
    sys.path.insert(0, os.path.join(_ROT, "tests", "enhet"))
    import test_troskelharkomst as L

    granskade = set(L.MODULER)
    obevakade = []
    for sokvag in _pyfiler():
        with open(sokvag, encoding="utf-8") as f:
            for nr, rad in enumerate(f, 1):
                if _KONSTANT.match(rad.rstrip("\n")) and os.path.basename(sokvag) not in granskade:
                    obevakade.append("%s:%d %s" % (
                        os.path.relpath(sokvag, _ROT), nr,
                        rad.split("=")[0].strip()))
    assert not obevakade, (
        "numeriska konstanter som ingen tröskellinter tittar på (S6 kräver "
        "varje numerisk konstant i analyskod):\n  " + "\n  ".join(obevakade))

