# -*- coding: utf-8 -*-
"""README:s fastabell far inte motsaga fasspecen.

Trasig fixtur for ett verkligt fynd (M-90): README sa "**inte paborjad** -
Inget protokoll" om fas 6, 7, 8 och 9 medan `docs/spec/70_faser.md` sa
**STANGD** om alla fyra, var och en med sina matningar. Det ar det forsta en
nedladdare laser, och det motsades av repot sjalvt.

Skulderegistret kunde inte se det: bada texterna ar valskrivna och innehaller
inga markorer. Skuld som inte skriver om sig sjalv ar osynlig for ett monster -
den syns bara nar tva kallor stalls MOT varandra.

Regeln ar med flit ensidig. Specen ager sanningen om ett fas lage; README far
vara kortare och mindre detaljerad. Det som INTE ar tillatet ar att README
sager mindre fardigt an specen.
"""
import os
import re

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_README = os.path.join(_ROT, "docs/ARBETSLAGET.md")
_FASER = os.path.join(_ROT, "docs", "spec", "70_faser.md")

# Bara de ord specen SJALV anvander for att forklara en fas fardig. Forsta
# versionen tog ocksa "klar" och "matt", och foll da pa fas 13: dess rad sager
# "Allt ar byggt och matt under Wine" - en beskrivning av vad som matts pa ANNAT
# hall, inte ett besked om att fasen ar klar. Grinden hade alltsa exakt det fel
# den byggdes for att fanga: ett monster som ser ut att matcha, provat mot
# ingenting. Det ar nu last av det tredje fallet i test_regeln_ar_ensidig.
_FARDIG = re.compile(r"st[aä]ngd|passerad", re.I)
# Ord som betyder "det har finns inte an".
_OGJORT = re.compile(r"inte\s+p[aå]b[oö]rjad|ej\s+p[aå]b[oö]rjad|inget\s+protokoll",
                     re.I)


def _fasrader(sokvag):
    """Fasnummer -> radens text, ur en markdown-tabell som borjar med | N |."""
    ut = {}
    with open(sokvag, "r", encoding="utf-8") as f:
        for rad in f:
            m = re.match(r"\|\s*(\d+)\s*\|", rad)
            if m:
                ut.setdefault(int(m.group(1)), []).append(rad.strip())
    return ut


def test_readme_sager_inte_opaborjad_om_en_stangd_fas():
    spec = _fasrader(_FASER)
    readme = _fasrader(_README)
    motsagelser = []
    for nr, rader in sorted(readme.items()):
        if nr not in spec:
            continue
        spectext = " ".join(spec[nr])
        for rad in rader:
            if _OGJORT.search(rad) and _FARDIG.search(spectext):
                motsagelser.append(
                    "fas %d: README sager %r men 70_faser.md sager %r"
                    % (nr, rad[:70], spectext[:90]))
    assert not motsagelser, (
        "README motsager fasspecen pa %d stallen:\n  %s"
        % (len(motsagelser), "\n  ".join(motsagelser)))


def test_bada_tabellerna_gar_att_lasa():
    """En grind som inte hittar nagra rader godkanner allt.

    Utan det har provet hade en omskriven tabell - eller ett andrat filnamn -
    gjort grinden tyst gron i stallet for rod.
    """
    spec = _fasrader(_FASER)
    readme = _fasrader(_README)
    assert len(spec) >= 10, "fann bara %d fasrader i 70_faser.md" % len(spec)
    assert len(readme) >= 10, "fann bara %d fasrader i README" % len(readme)
    assert set(readme) & set(spec), "tabellerna delar inga fasnummer"


@pytest.mark.parametrize("rad,spectext,ska_falla", [
    ("| 6 | PLC-bandet | **inte påbörjad** | Inget protokoll |",
     "| 6 | PLC-bandet | ... | **stängd** (M-39) |", True),
    ("| 6 | PLC-bandet | klar på Linux | M-39 |",
     "| 6 | PLC-bandet | ... | **stängd** (M-39) |", False),
    ("| 13 | Windows | **inte påbörjad** | Inget protokoll |",
     "| 13 | Windows | ... | kraver en Windows-maskin |", False),
    # Fas 13:s VERKLIGA rad. Den namner "byggt och matt", men om Wine - inte om
    # fasen. Foll som falskt positivt innan monstret snavades in.
    ("| 13 | Windows | **inte påbörjad** | Kräver en Windows-maskin |",
     "| 13 | **Windows** | `M-44`: nio fynd med fil och rad ... Allt är byggt"
     " och mätt under Wine | M-44:s **16 numrerade protokollpunkter** körda"
     " på en riktig Windows-maskin |", False),
])
def test_regeln_ar_ensidig(rad, spectext, ska_falla):
    """README far vara kortare an specen, men inte mindre fardig.

    Tredje fallet ar det viktiga: en fas som specen SJALV inte kallar klar far
    README garna kalla opaborjad. En grind som fallde aven da hade tvingat fram
    en osann README i andra riktningen.
    """
    faller = bool(_OGJORT.search(rad) and _FARDIG.search(spectext))
    assert faller is ska_falla


def test_readme_fas10_text_har_inga_oppna_punkter():
    """Fas 10 ar stangd (M-112); README-texten far inte pasta att den ar oppen."""
    with open(_README, "r", encoding="utf-8") as f:
        text = f.read()

    # Kontrollera att avsnittet Fas 10 inte innehaller gammal text om oppna punkter
    assert "fasens öppna punkt" not in text.lower(), (
        "README innehaller fortfarande gammal text om 'fasens öppna punkt' trots att fas 10 ar stangd"
    )
    assert "inte prövat, och det är fasens öppna punkt" not in text.lower()


def _pyfiler(*kataloger):
    ut = []
    for kat in kataloger:
        for rot, ds, fs in os.walk(os.path.join(_ROT, kat)):
            ds[:] = [d for d in ds if d != "__pycache__"]
            ut += [os.path.join(rot, f) for f in sorted(fs) if f.endswith(".py")]
    return ut


def test_readme_beskriver_ett_repo_med_kod_i():
    """docs/ARBETSLAGET.md: 'Specifikationsfas. Ingen kod byggd ännu.' S7 mätte att
    källprojektets README låg 71 dagar efter koden och påstod funktioner som
    inte fanns. Här påstår den frånvaron av kod som finns."""
    rader = sum(len(open(p, encoding="utf-8").readlines())
                for p in _pyfiler("ext", "svc", "bank"))
    with open(_README, encoding="utf-8") as f:
        text = f.read()
    assert "Ingen kod byggd ännu" not in text, (
        "docs/ARBETSLAGET.md säger 'Ingen kod byggd ännu' medan repot bär %d rader "
        "Python i ext/, svc/ och bank/" % rader)


