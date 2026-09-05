# -*- coding: utf-8 -*-
"""L0: varje troskel bar sin harkomst.

41_ogat_kontrakt.md: "En troskel utan hanvisning ar ett linterfel."

Den forsta versionen av den har lintern var sjalv en falsk gron. Den
* tackte EN modul av tolv (10 av 125 konstanter)
* godkande formen M-\\d+ utan att sla upp den

Matt 2026-09-04: 27 konstanter pekade pa matningar som inte fanns - M-10 fjorton
ganger, M-18 atta, M-19 fem. Och 79 hade ingen hanvisning alls.

Lintern gor nu tre saker i stallet:
1. laser HELA ext/, svc/ och bank/
2. slar upp varje M-nummer mot docs/matningar/ eller RESERVERADE.md
3. raknar de som saknar hanvisning mot en sparr i TROSKELSKULD.md som bara far
   ga at ett hall
"""
import os
import re

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_MATNINGAR = os.path.join(_ROT, "docs", "matningar")

# Traden som genomsoks. Listan ar med avsikt bred: en troskel som goms i en
# modul lintern inte laser ar precis den skuld som var osynlig forut.
TRAD = ("ext/vc_addon/vc_assist", "svc/vc_assist_svc", "bank")

# Tre former lades till av M-46, efter en matning av vad lintern SLAPPTE:
#   _NAMN      ett understreck framfor namnet gjorde troskeln osynlig. Det ar
#              en enteckens vag ut ur hela sparren, och den vagen fanns.
#   1e-9       exponentform matchade inte alls (verifiering._FLYTTALSMARGINAL
#              var den enda verkliga traffen, men vagen ut var oppen for alla)
#   indrag     en konstant i en klasskropp lag utanfor lintern
# Matt 2026-09-04: de tre formerna tillsammans lade till EN verklig konstant,
# sa skulden var inte storre an den sag ut. Halet var att den kunde bli det,
# nar som helst, utan att nagot blev rott.
_KONSTANT = re.compile(
    r"^\s*(_?[A-Z][A-Z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*(#.*)?$")
_MNUMMER = re.compile(r"\bM-(\d+)\b")
# En konstant kan ha harkomst i SPECEN i stallet for i en matning. En
# portnummer och en grammatikversion ar inte trosklar - de ar beslutade, och
# beslutet star i ett dokument. Kravet ar detsamma: peka ut var.
_SPECREF = re.compile(r"\b(\d\d_[a-z0-9_]+\.md)\b")


def _har_harkomst(kom):
    return bool(_MNUMMER.search(kom) or _SPECREF.search(kom))


def _specdok_finns(namn):
    return os.path.exists(os.path.join(_ROT, "docs", "spec", namn))


def _mnr(x):
    return "M-%02d" % int(x)


def matningar_som_finns():
    ut = set()
    for f in os.listdir(_MATNINGAR):
        m = re.match(r"M-(\d+)", f)
        if m and f.endswith(".md"):
            ut.add(_mnr(m.group(1)))
    return ut


def reserverade():
    with open(os.path.join(_MATNINGAR, "RESERVERADE.md")) as f:
        text = f.read()
    # bara nummer i tabellens forsta kolumn raknas som reserverade
    return set(_mnr(m) for m in re.findall(r"^\| M-(\d+) \|", text, re.M))


def skuldtaket():
    with open(os.path.join(_MATNINGAR, "TROSKELSKULD.md")) as f:
        m = re.search(r"UTAN_HARKOMST\s*=\s*(\d+)", f.read())
    assert m, "TROSKELSKULD.md saknar raden UTAN_HARKOMST = <tal>"
    return int(m.group(1))


def trosklar():
    """[(sokvag, radnr, namn, kommentar)] over hela tradet."""
    ut = []
    for rot in TRAD:
        for dp, _dn, fn in os.walk(os.path.join(_ROT, rot)):
            if "__pycache__" in dp:
                continue
            for f in sorted(fn):
                if not f.endswith(".py"):
                    continue
                sokvag = os.path.join(dp, f)
                rel = os.path.relpath(sokvag, _ROT)
                with open(sokvag) as fh:
                    for nr, rad in enumerate(fh, 1):
                        m = _KONSTANT.match(rad.rstrip("\n"))
                        if m:
                            ut.append((rel, nr, m.group(1), (m.group(3) or "").strip()))
    return ut


ALLA = trosklar()


def test_det_finns_trosklar_att_prova():
    assert len(ALLA) > 50, "hittade bara %d troskelkonstanter" % len(ALLA)


@pytest.mark.parametrize("rad,namn", [
    ("TROSKEL = 5", "TROSKEL"),
    ("_TROSKEL = 5", "_TROSKEL"),
    ("TROSKEL = 1e-9", "TROSKEL"),
    ("TROSKEL = -0.5", "TROSKEL"),
    ("    TROSKEL = 5", "TROSKEL"),
    ("TROSKEL = 5  # Satt av M-46.", "TROSKEL"),
])
def test_lintern_ser_de_former_en_troskel_faktiskt_skrivs_i(rad, namn):
    """Trasig fixtur for LINTERN sjalv (M-46).

    Foll fore lagningen for _TROSKEL, 1e-9 och den indragna raden: lintern
    sag dem inte, sa de kunde bara vilken troskel som helst utan harkomst
    utan att nagot blev rott. En sparr som gar att kliva runt med ett
    understreck mater inte sin egen storhet.
    """
    m = _KONSTANT.match(rad)
    assert m is not None, rad
    assert m.group(1) == namn


def test_ingen_troskel_pekar_pa_en_matning_som_inte_finns():
    """Det var det har som inte provades: formen godkandes, numret slogs
    aldrig upp. 27 hanvisningar pekade i tomma luften."""
    finns = matningar_som_finns() | reserverade()
    doda = []
    for rel, nr, namn, kom in ALLA:
        for r in _MNUMMER.findall(kom):
            if _mnr(r) not in finns:
                doda.append("%s:%d %s -> %s" % (rel, nr, namn, _mnr(r)))
    assert not doda, (
        "trosklar som pekar pa en matning som varken finns eller ar reserverad:\n  "
        + "\n  ".join(doda))


def test_ett_reserverat_nummer_anvands_bara_som_PRELIMINART():
    """Ett reserverat nummer ar ett lofte, inte ett matt varde."""
    res = reserverade() - matningar_som_finns()
    fel = []
    for rel, nr, namn, kom in ALLA:
        for r in _MNUMMER.findall(kom):
            if _mnr(r) in res and "PRELIMIN" not in kom.upper():
                fel.append("%s:%d %s -> %s utan PRELIMINAR" % (rel, nr, namn, _mnr(r)))
    assert not fel, "\n  ".join([""] + fel)


def test_skulden_ar_raknad_och_krymper():
    """Spärren far bara ga at ett hall.

    Star det verkliga antalet hogre an taket ar en ny troskel inforda utan
    harkomst. Star det lagre ska taket skrivas ned - annars ruttnar sparren
    och slutar mata sin egen storhet.
    """
    utan = [(rel, nr, namn) for rel, nr, namn, kom in ALLA
            if not _har_harkomst(kom)]
    tak = skuldtaket()
    assert len(utan) <= tak, (
        "%d trosklar utan harkomst, taket ar %d. Nya utan hanvisning:\n  %s"
        % (len(utan), tak,
           "\n  ".join("%s:%d %s" % x for x in utan[:20])))
    assert len(utan) == tak, (
        "skulden ar nere i %d men taket star kvar pa %d. Skriv ned det nya "
        "talet i docs/matningar/TROSKELSKULD.md." % (len(utan), tak))


def test_en_specreferens_pekar_pa_ett_dokument_som_finns():
    """Samma fella som med M-numren: formen far inte racka."""
    doda = []
    for rel, nr, namn, kom in ALLA:
        for d in _SPECREF.findall(kom):
            if not _specdok_finns(d):
                doda.append("%s:%d %s -> %s" % (rel, nr, namn, d))
    assert not doda, "\n  ".join([""] + doda)


@pytest.mark.parametrize("modul", ["oga_analys.py", "oga_provtagning.py",
                                   "oga_harledning.py",     # M-65, 42_ogat_utbyggt.md §11
                                   "oga_kontrakt.py", "skrivgrind.py", "pump.py"])
def test_ogats_och_bryggans_trosklar_bar_alla_harkomst(modul):
    """De moduler som domer, och den som skyddar scenen, har noll skuld.

    Resten av tradet betar av sig genom sparren ovan; har ar kravet absolut.
    """
    utan = ["%s:%d %s" % (rel, nr, namn) for rel, nr, namn, kom in ALLA
            if os.path.basename(rel) == modul and not _har_harkomst(kom)]
    assert not utan, "\n  ".join([""] + utan)


def test_place_tol_mm_provas_av_minst_ett_prov():
    """En tröskel som inget prov rör är ett påstående, inte en tröskel.

    `PLACE_TOL_MM` används bara som reservvärde i
    `mal.get("tol_mm", PLACE_TOL_MM)`, och varje cell i `tests/celler.py`
    skickar med sitt eget `tol_mm`. Sätts den till 2,5 meter ändras ingen dom.
    Provet: ändra den absurt och kräv att MINST en cellsdom rör sig.
    """
    import sys
    sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
    sys.path.insert(0, os.path.join(_ROT, "tests"))
    import celler
    import oga_analys as A

    def domar():
        ut = {}
        for namn, bygg in sorted(celler.ALLA.items()):
            b, plan = bygg()
            _text, rapport, _analys = A.doma(b.data(), plan)
            ut[namn] = rapport.dom[0]
        return ut

    fore = domar()
    gammal = A.PLACE_TOL_MM
    try:
        A.PLACE_TOL_MM = 2500.0        # 2,5 meter: allt är "i mål"
        efter = domar()
    finally:
        A.PLACE_TOL_MM = gammal

    assert fore != efter, (
        "PLACE_TOL_MM kan sättas till 2500 mm utan att en enda dom ändras: "
        "ingen cell provar tröskeln. Domar: %r" % (fore,))

