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
    assert "uttryck" in dubbel.lower() or "villkorade" in dubbel.lower()


def test_regeln_mot_kodstaket_finns():
    """Modellens allra forsta svar i M-96 var inramat i ett markdown-staket och
    brande ett helt varv pa 'ovantat tecken `'. Adaptern tar bort staketet nu,
    men regeln ska sta i prompten ocksa - ett lager som bara stader upp doljer
    att modellen gor fel sak."""
    assert "kodstaket" in R.SYSTEMPROMPT


def test_riktningsreglerna_sager_hur_man_SER_riktningen():
    """En regel som sager 'skriv inte till en ingang' utan att saga hur man
    kanner igen en ar en bon.

    Skelettet ger riktningen i adressen - AT %I ar ingang, AT %Q utgang. Utan
    den raden maste modellen veta IEC-adressering utantill, och gor den inte
    det faller SKRIVEN_INGANG pa nagot ingen sagt at den.
    """
    for kod in ("SKRIVEN_INGANG", "ODRIVEN_UTGANG"):
        regel = F.REGLER[kod]
        assert "%I" in regel or "%Q" in regel, \
            "%s sager inte hur riktningen syns" % kod


def test_dubbelskrivningsregeln_stammer_med_grindens_MATTA_grans():
    """Regeln ska komma ur en PROVNING av grinden, inte ur min lasning av den.

    Jag skrev regeln tva ganger och hade fel bada gangerna. Forst "exakt ett
    stalle, aven i olika grenar" - strangare an grinden. Sedan "villkorade
    skrivningar i olika grenar ar i sin ordning" - slappare an grinden, for tva
    separata IF-block med OLIKA varden falls.

    Sa har ser grinden ut nar man fragar den (matt 2026-09-05):

        tva villkorade, OLIKA varden, separata IF   FALLS
        tva villkorade, SAMMA varde                 slapps
        IF/ELSE, olika varden                       slapps
        ett uttryck                                 slapps
        ovillkorad forst, sen villkorad             slapps
        villkorad forst, sen ovillkorad             FALLS
        tva ovillkorade                             FALLS

    Skillnaden mellan rad 1 och rad 3 ar hela poangen: separata IF-block kan
    bada koras i samma scan, IF/ELSE:s grenar utesluter varandra.
    """
    regel = F.REGLER["DUBBELSKRIVNING"]
    for maste in ("IF/ELSE", "uttryck", "separata IF"):
        assert maste.lower() in regel.lower(), \
            "regeln namner inte %r, och da saknar den en av de tre utvagarna" % maste


@pytest.mark.parametrize("namn,kropp,ska_falla", [
    ("tva villkorade, olika varden, separata IF",
     "IF a THEN\n UT := TRUE;\nEND_IF;\nIF b THEN\n UT := FALSE;\nEND_IF;\n", True),
    ("tva villkorade, samma varde",
     "IF a THEN\n UT := TRUE;\nEND_IF;\nIF b THEN\n UT := TRUE;\nEND_IF;\n", False),
    ("IF/ELSE, olika varden",
     "IF a THEN\n UT := TRUE;\nELSE\n UT := FALSE;\nEND_IF;\n", False),
    ("ett uttryck", "UT := a AND NOT b;\n", False),
    ("ovillkorad forst, sen villkorad",
     "UT := FALSE;\nIF a THEN\n UT := TRUE;\nEND_IF;\n", False),
    ("villkorad forst, sen ovillkorad",
     "IF a THEN\n UT := TRUE;\nEND_IF;\nUT := FALSE;\n", True),
    ("tva ovillkorade", "UT := TRUE;\nUT := FALSE;\n", True),
])
def test_gransen_star_kvar_dar_regeln_pastar(namn, kropp, ska_falla):
    """Binder regeln till GRINDEN, inte till min lasning av den.

    Flyttar grinden sin grans nagon gang blir regeln en logn i samma stund, och
    det ska synas har - inte i en modells forsta forsok."""
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.normpath(_os.path.join(
        _os.path.dirname(__file__), "..", "..", "svc")))
    from vc_assist_svc.st.validator import validera
    kalla = ("PROGRAM P\nVAR\n a : BOOL;\n b : BOOL;\n"
             " UT AT %QX0.0 : BOOL;\nEND_VAR\n" + kropp + "END_PROGRAM\n")
    koder = [x.kod for x in validera(kalla).anmarkningar]
    assert ("DUBBELSKRIVNING" in koder) is ska_falla, namn
