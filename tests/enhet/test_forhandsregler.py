# -*- coding: utf-8 -*-
"""L1: grindarnas regler maste na modellen FORE den skriver.

Fas 9 mater forsta forsoket till 0 av 4 och efter ett reparationsvarv 4 av 4.
Operatorens krav ar det omvanda: enskott ska vara normalfallet, flerskott en
reserv. Sa lange grindarnas kunskap nar modellen forst NAR den redan skrivit
fel ar flerskott inte en installning utan en FORM.

Proven halller fast att prompten och grindarna inte kan glida isar.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc import forhandsregler as F                   # noqa: E402
from vc_assist_svc.plc import reparation as R                       # noqa: E402
from vc_assist_svc.plc.deklarationsgrind import KONTROLLER_PLC      # noqa: E402
from vc_assist_svc.st.fel import KONTROLLER                         # noqa: E402


def test_varje_kod_en_grind_kan_falla_pa_har_en_regel():
    """En kod utan regel ar en FALLA.

    Grinden fallr da pa nagot ingen sagt at modellen att undvika, och forsta
    forsoket kan inte bli ratt av annat an tur.
    """
    assert F.saknade_regler() == (), (
        "kontroller som kan falla men som modellen aldrig fatt veta om: %s"
        % ", ".join(F.saknade_regler()))


def test_ingen_regel_utan_en_grind_bakom_sig():
    """En instruktion utan grind ar en bon som ser ut som en regel."""
    assert F.foraldralosa_regler() == (), (
        "regler for koder ingen grind langre faller pa: %s"
        % ", ".join(F.foraldralosa_regler()))


@pytest.mark.parametrize("kod", sorted(set(KONTROLLER) | set(KONTROLLER_PLC)))
def test_varje_kod_star_i_prompten_slingan_faktiskt_anvander(kod):
    """Det raknas inte att regeln finns i en tabell. Den ska NA modellen.

    Provet laser `reparation.SYSTEMPROMPT`, alltsa strangen slingan skickar -
    inte generatorns utdata. En generator som ingen kopplat in ar ingen
    instruktion.
    """
    assert kod in R.SYSTEMPROMPT


def test_grunden_star_kvar_over_reglerna():
    """Reglerna far inte trycka undan uppdraget."""
    assert R.SYSTEMPROMPT.startswith(R._GRUNDPROMPT)


# --- trasiga fixturer ---------------------------------------------------------

def test_en_ny_kontroll_utan_regel_upptacks(monkeypatch):
    """TRASIG FIXTUR. Nagon lagger till en kontroll och glommer regeln.

    Utan det har provet hade grinden bara vuxit med en fALLA, och den forsta
    som marker det ar en modell som fallr pa nagot ingen sagt at den.
    """
    monkeypatch.setitem(KONTROLLER, "NYKONTROLL", ("F1", "nagot nytt"))
    assert "NYKONTROLL" in F.saknade_regler()


def test_en_regel_utan_kontroll_upptacks(monkeypatch):
    """TRASIG FIXTUR at andra hallet. En kontroll tas bort, regeln star kvar.

    Modellen far da en instruktion ingen grind langre kraver - och den upptar
    plats i prompten som en verklig regel kunde ha haft.
    """
    monkeypatch.setitem(F.REGLER, "BORTTAGEN", "gor inte sa har")
    assert "BORTTAGEN" in F.foraldralosa_regler()


def test_en_tom_regel_raknas_som_saknad(monkeypatch):
    """Blanksteg ar inte en instruktion."""
    monkeypatch.setitem(F.REGLER, "TIDLITERAL", "   ")
    assert "TIDLITERAL" in F.saknade_regler()


# --- att reglerna sager nagot anvandbart --------------------------------------

def test_reglerna_for_de_tva_dyraste_klasserna_ar_konkreta():
    """TIDLITERAL stod for nio av sexton grinddomar i fas 9:s forsta
    modelldrivna korning, DUBBELSKRIVNING for fem (M-96). En regel som bara
    upprepar kodens namn hade inte hjalpt mot nagondera."""
    tid = F.REGLER["TIDLITERAL"]
    assert "T#" in tid and "minsta" in tid, "regeln maste ge FORMEN, inte namnet"
    dubbel = F.REGLER["DUBBELSKRIVNING"]
    assert "ett stalle" in dubbel.lower() or "en sats" in dubbel.lower()


def test_regeln_mot_kodstaket_finns():
    """Modellens allra forsta svar i M-96 var inramat i ett markdown-staket och
    brande ett helt varv pa 'ovantat tecken `'. Adaptern tar bort staketet nu,
    men regeln ska sta i prompten ocksa - ett lager som bara stader upp doljer
    att modellen gor fel sak."""
    assert "kodstaket" in R.SYSTEMPROMPT
