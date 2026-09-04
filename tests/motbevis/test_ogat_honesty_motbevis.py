# -*- coding: utf-8 -*-
"""Motbevis: ögats grindar täcker för varandra, så en död grind syns inte.

`tests/celler.py` säger om sig själv: *"Varje trasig cell isolerar EN felklass,
så en fällning går att härleda till sin orsak."* För två celler stämmer det
inte, och det får en mätbar följd.

Mätt med mutation över hela sviten (838 tester):

    oga_analys.py:438  overtradelse = True -> False   (BLOWUP)         ÖVERLEVER
    oga_analys.py:455  overtradelse = True -> False   (NEVER_GRIPPED)  ÖVERLEVER
    oga_analys.py:428  overtradelse = True -> False   (TELEPORT)       dödas

Skälet är att `explosion` också hamnar 94 000 mm fel, och `aldrig_gripen`
också saknar grepp. Cellerna faller på en annan grind, raden `BLOWUP
VIOLATION` skrivs ändå ut, och FACIT-provet som letar efter raden är nöjt.
Två av ögats fyra hederlighetsgrindar kan alltså stängas av utan att ett
enda test märker det.

Några prov här är GRÖNA. De är de saknade proven — hål som mätningen fann men
som koden faktiskt klarar när någon väl frågar. De hör hemma i `tests/enhet/`.
"""
import ast
import os
import sys
import types

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests"))

import celler                 # noqa: E402
import oga_analys as A        # noqa: E402
import oga_kontrakt as K      # noqa: E402


def _rapport(data, plan, modul=A):
    _text, rapport, _analys = modul.doma(data, plan)
    return rapport


# ---- 1. cellerna isolerar inte sin felklass ----------------------------

# (cell, den enda klass den ska bryta mot, klasser den INTE får bryta mot)
ISOLERING = [
    ("explosion", "BLOWUP VIOLATION",
     ("OFF_TARGET", "DROPPED", "SLIPPING", "NEVER_FORMED", "NEVER_GRIPPED VIOLATION")),
    ("aldrig_gripen", "NEVER_GRIPPED VIOLATION",
     ("OFF_TARGET", "DROPPED", "SLIPPING", "BLOWUP VIOLATION",
      "UNDERGROUND VIOLATION")),
]


@pytest.mark.parametrize("namn,egen,frammande", ISOLERING,
                         ids=[x[0] for x in ISOLERING])
def test_en_trasig_cell_bryter_mot_exakt_en_felklass(namn, egen, frammande):
    b, plan = celler.ALLA[namn]()
    r = _rapport(b.data(), plan)
    rader = [x for _s, rr in r.sektioner for x in rr]
    assert any(egen in x for x in rader), "%s bröt inte mot sin egen klass" % namn
    smitta = [x for x in rader if any(f in x for f in frammande)]
    assert not smitta, (
        "%s bryter mot fler klasser än sin egen: %s. Då täcker grindarna för "
        "varandra: mutationsprovet visar att %s-grinden kan stängas av utan "
        "att sviten fälls." % (namn, smitta, egen.split()[0]))


def test_greppgrinden_och_never_gripped_ar_inte_samma_grind():
    """`aldrig_gripen` fälls både av `mh["grip"] is None` (rad 517) och av
    NEVER_GRIPPED (rad 455). Den ena döljer att den andra är död."""
    b, plan = celler.aldrig_gripen()
    _t, _r, analys = A.doma(b.data(), plan)
    h = analys.harledt
    saknar_grepp = h["motion"].get("grip") is None
    honesty = h["honesty"].get("overtradelse")
    assert not (saknar_grepp and honesty), (
        "samma cell fälls av två oberoende grindar samtidigt; ingen av dem "
        "har ett prov där den är den enda som kan fälla")


# ---- 2. placeringsgränsen är obestämd ----------------------------------

def _modul_med_bytt_operator(gammal, ny):
    """Laddar oga_analys på nytt med EN operator utbytt. Mätning, inte fix.

    Raden slås upp på sitt INNEHÅLL, inte på ett radnummer: modulen växer, och
    ett prov som bygger på ett radnummer mäter fel sak efter nästa commit.
    """
    stig = os.path.join(_ROT, "ext", "vc_addon", "vc_assist", "oga_analys.py")
    rader = open(stig, encoding="utf-8").read().split("\n")
    traff = [i for i, r in enumerate(rader) if gammal in r]
    assert len(traff) == 1, ("hittade %d rader med %r; provet måste peka ut "
                             "exakt en" % (len(traff), gammal))
    i = traff[0]
    rader[i] = rader[i].replace(gammal, ny, 1)
    kalla = "\n".join(rader)
    ast.parse(kalla)
    m = types.ModuleType("_oga_analys_mut")
    m.__file__ = stig
    exec(compile(kalla, stig, "exec"), m.__dict__)
    return m


def test_placeringsgransen_ar_bestamd_av_minst_en_cell():
    """`if plac["fel_mm"] > plac["tol_mm"]` . Byts `>` mot `>=`
    ändras ingen dom i någon av bankens elva celler: gränsen är obestämd.
    """
    mut = _modul_med_bytt_operator(
        'plac["fel_mm"] > plac["tol_mm"]', 'plac["fel_mm"] >= plac["tol_mm"]')
    fore, efter = {}, {}
    for namn, bygg in sorted(celler.ALLA.items()):
        b, plan = bygg()
        fore[namn] = _rapport(b.data(), plan).dom
        b, plan = bygg()
        efter[namn] = _rapport(b.data(), plan, modul=mut).dom
    assert fore != efter, (
        "`>` och `>=` ger identiska domar för alla elva celler: ingen cell "
        "ligger på toleransgränsen, så gränsen har inget facit")


def test_barstrackans_troskel_ar_bestamd_av_minst_en_cell():
    """Samma sak för `carry["span_s"] < CARRY_MIN_SPAN_S` ."""
    mut = _modul_med_bytt_operator(
        'carry.get("span_s", 0.0) < CARRY_MIN_SPAN_S',
        'carry.get("span_s", 0.0) <= CARRY_MIN_SPAN_S')
    fore, efter = {}, {}
    for namn, bygg in sorted(celler.ALLA.items()):
        b, plan = bygg()
        fore[namn] = _rapport(b.data(), plan).dom
        b, plan = bygg()
        efter[namn] = _rapport(b.data(), plan, modul=mut).dom
    assert fore != efter, (
        "`<` och `<=` ger identiska domar för alla elva celler: bärsträckans "
        "tröskel har inget facit vid sin gräns")


# ---- 3. saknade prov som koden faktiskt klarar -------------------------
#
# Dessa är GRÖNA. Mutationen visade att ingen provade dem; koden håller.

def test_en_rapport_utan_dom_ar_inte_godkand():
    """oga_kontrakt.godkand(): `if self.dom is None: return False`.
    Mutation till `return True` överlever hela sviten. Fail-closed-regeln
    (I3) för en rapport utan dom hade inget prov. Nu har den ett."""
    r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
    r.sektion("MOTION").rad("GRIP FORMED t=0.100s dist=1.0mm")
    assert r.dom is None
    assert r.godkand() is False


def test_blowupgrinden_faller_en_cell_som_bara_bryter_mot_farten():
    """Den isolerande fixtur som saknades: greppet håller, rotationen är noll,
    slutläget ligger i mål — det enda felet är farten."""
    mal = [1.0, 0.0, 0.75]
    b = celler.Bygge("ren_explosion")
    for _ in range(20):
        b.steg([0.0, 0.0, 0.75], [0.0, 0.0, 0.75], sig={"grip_out": False})
    for _ in range(20):
        b.steg([0.0, 0.0, 0.75], [0.0, 0.0, 0.75], sig={"grip_out": True})
    b.steg([3.0, 0.0, 0.75], [3.0, 0.0, 0.75], sig={"grip_out": True})
    for i in range(20):
        u = i / 19.0
        p = [3.0 + (mal[0] - 3.0) * u, 0.0, 0.75]
        b.steg(p, p, sig={"grip_out": True})
    for _ in range(20):
        b.steg(mal, mal, sig={"grip_out": False})

    r = _rapport(b.data(), celler.plan())
    rader = [x for _s, rr in r.sektioner for x in rr]
    assert any("BLOWUP VIOLATION" in x for x in rader), rader
    assert not any("OFF_TARGET" in x or "DROPPED" in x for x in rader), rader
    assert r.dom[0] == "FAIL"
    assert "fart" in r.dom[1], r.dom
