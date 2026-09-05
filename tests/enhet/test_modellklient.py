# -*- coding: utf-8 -*-
"""L1 for modellklienten. Den finns for att fas 9:s slinga ska kunna kora sig
sjalv - fasen star oppen pa exakt "slingan drevs for hand".

Proven koper INGA modellsvar. Transporten provas mot en attrapp-subprocess, och
slingans logik mot `Inspelad`. Ett prov som kostar pengar per korning kors till
slut inte.
"""
import json
import os
import subprocess
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import modellklient as M                         # noqa: E402


class FalskProcess(object):
    def __init__(self, kod=0, ut=b"", fel=b""):
        self.returncode, self.stdout, self.stderr = kod, ut, fel


def _svar(**extra):
    d = {"result": "ST-KOD", "is_error": False, "subtype": "success",
         "total_cost_usd": 0.021, "num_turns": 1}
    d.update(extra)
    return json.dumps(d).encode("utf-8")


def _kor(monkeypatch, process):
    monkeypatch.setattr(M.subprocess, "run", lambda *a, **k: process)


# --- att modellen inte kan lasa facit ----------------------------------------

def test_verktygslistan_ar_tom_sa_modellen_inte_kan_lasa_nagon_fil():
    """Matningens giltighet star pa att modellen inte sett facit.

    Ett forbud i en prompt ar en bon. Det har ar sparren, och den maste synas
    i kommandoraden.
    """
    kommando = M.ClaudeCLI(korbar="/bin/true")._kommando("fraga")
    assert "--allowed-tools" in kommando
    assert kommando[kommando.index("--allowed-tools") + 1] == ""


def test_en_arbetskatalog_i_repot_avvisas(monkeypatch):
    """Trasig fixtur for det andra lagret.

    Verktygslistan ar en FLAGGA. Slapper nagon pa den senare ar en katalog inne
    i repot skillnaden mellan en giltig matning och en modell som star bredvid
    facit. Sokvagen provas darfor separat.
    """
    _kor(monkeypatch, FalskProcess(ut=_svar()))
    k = M.ClaudeCLI(korbar="/bin/true", arbetskatalog=os.path.join(_ROT, "bank"))
    with pytest.raises(M.Modellfel) as e:
        k.fraga("hej")
    assert "reference answer" in str(e.value)


def test_repotsroten_sjalv_avvisas_ocksa(monkeypatch):
    _kor(monkeypatch, FalskProcess(ut=_svar()))
    k = M.ClaudeCLI(korbar="/bin/true", arbetskatalog=_ROT)
    with pytest.raises(M.Modellfel):
        k.fraga("hej")


def test_en_katalog_utanfor_repot_slapps_igenom(monkeypatch, tmp_path):
    """Andra halvan: en sparr som fyrar pa allt gor klienten obrukbar."""
    _kor(monkeypatch, FalskProcess(ut=_svar()))
    k = M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path))
    assert k.fraga("hej").text == "ST-KOD"


# --- att ett misslyckande aldrig ser ut som ett svar --------------------------

def test_tomt_svar_kastar_i_stallet_for_att_se_ut_som_ingen_rattelse(monkeypatch, tmp_path):
    """Skillnaden mellan "modellen lagade ingenting" och "modellen svarade
    aldrig" ar tva olika matningar. En tom strang far inte bli den forsta."""
    _kor(monkeypatch, FalskProcess(ut=_svar(result="   ")))
    with pytest.raises(M.Modellfel):
        M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")


def test_is_error_kastar(monkeypatch, tmp_path):
    _kor(monkeypatch, FalskProcess(ut=_svar(is_error=True, result="nagot gick fel")))
    with pytest.raises(M.Modellfel):
        M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")


def test_annan_subtype_an_success_kastar(monkeypatch, tmp_path):
    _kor(monkeypatch, FalskProcess(ut=_svar(subtype="error_max_turns")))
    with pytest.raises(M.Modellfel):
        M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")


def test_nollskild_slutkod_kastar_och_bar_med_felutdata(monkeypatch, tmp_path):
    _kor(monkeypatch, FalskProcess(kod=1, fel=b"inte inloggad"))
    with pytest.raises(M.Modellfel) as e:
        M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")
    assert "inte inloggad" in str(e.value)


def test_oparsbar_utdata_kastar(monkeypatch, tmp_path):
    _kor(monkeypatch, FalskProcess(ut=b"<html>fel</html>"))
    with pytest.raises(M.Modellfel):
        M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")


def test_tidsgransen_kastar(monkeypatch, tmp_path):
    def slut(*a, **k):
        raise subprocess.TimeoutExpired("claude", 1)
    monkeypatch.setattr(M.subprocess, "run", slut)
    with pytest.raises(M.Modellfel) as e:
        M.ClaudeCLI(korbar="/bin/true", tidsgrans=1,
                    arbetskatalog=str(tmp_path)).fraga("x")
    assert "did not respond within" in str(e.value)


def test_saknad_korbar_kastar_i_stallet_for_att_svara_tomt(monkeypatch):
    """En maskin utan Claude Code. korbar=None betyder "leta upp den sjalv",
    sa provet maste ta bort den ur PATH - annars mater det den har maskinen."""
    monkeypatch.setattr(M.shutil, "which", lambda _: None)
    with pytest.raises(M.Modellfel) as e:
        M.ClaudeCLI().fraga("x")
    assert "Inspelad" in str(e.value), "felet ska peka pa vad man kan gora"


# --- att kostnaden foljer med -------------------------------------------------

def test_kostnaden_foljer_med_svaret(monkeypatch, tmp_path):
    """Ett tak pa fyra varv ar ett pastaende om ingen kan saga vad de kostade."""
    _kor(monkeypatch, FalskProcess(ut=_svar(total_cost_usd=0.37, num_turns=3)))
    s = M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")
    assert s.kostnad_usd == 0.37
    assert s.varv == 3


# --- inspelningen -------------------------------------------------------------

def test_inspelad_ger_svaren_i_ordning():
    k = M.Inspelad(["ett", "tva"])
    assert [k.fraga("a").text, k.fraga("b").text] == ["ett", "tva"]
    assert k.stalda == ["a", "b"]


def test_en_inspelning_som_tar_slut_kastar():
    """Fail-closed. Ett tyst tomt varv hade gjort att provet matte nagot annat
    an det trodde - slingan hade sett ut att ge upp av egen kraft."""
    k = M.Inspelad(["ett"])
    k.fraga("a")
    with pytest.raises(M.Modellfel):
        k.fraga("b")


def test_standardklienten_ger_None_i_stallet_for_en_attrapp(monkeypatch):
    """En anropare som far en attrapp tror att den mater en modell."""
    monkeypatch.setattr(M.shutil, "which", lambda _: None)
    assert M.standardklient() is None


# --- okand kostnad ar inte noll ----------------------------------------------
#
# Operatoren bytte transport fran `claude -p` till en annan modell. En transport
# som inte rapporterar sin kostnad hade da sett ut som en som kostade NOLL, och
# summan over en arm hade blivit ett matt tal som ingen matt. Samma felklass som
# ett tal utan enhet (51_komponentdata.md): ett saknat varde som ser fardigt ut.

def test_transport_utan_kostnadsuppgift_ger_None_inte_noll(monkeypatch, tmp_path):
    _kor(monkeypatch, FalskProcess(ut=json.dumps(
        {"result": "ST", "is_error": False, "subtype": "success"}).encode()))
    s = M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")
    assert s.kostnad_usd is None, "okand kostnad far aldrig bli 0.0"


def test_en_rapporterad_nolla_ar_fortfarande_en_nolla(monkeypatch, tmp_path):
    """Andra halvan. Sager transporten 0 sa ar det ett MATT tal, och det ska
    inte forvandlas till 'okand' - da vore rattelsen lika lognaktig at andra
    hallet."""
    _kor(monkeypatch, FalskProcess(ut=_svar(total_cost_usd=0.0)))
    s = M.ClaudeCLI(korbar="/bin/true", arbetskatalog=str(tmp_path)).fraga("x")
    assert s.kostnad_usd == 0.0


def test_inspelad_transport_rapporterar_ingen_kostnad():
    """Inspelad kostar inget att KORA, men den vet inte vad modellen skulle ha
    kostat. Att skriva 0 vore att pasta nagot om modellen."""
    assert M.Inspelad(["svar"]).fraga("x").kostnad_usd is None
