# -*- coding: utf-8 -*-
"""C6: åtta nya skadesorter för industriell Structured Text.

Varje sort motsvarar ett verkligt driftfel i en PLC:
1. FLANK_TAVLAR: R_TRIG som läses i fel ordning inom samma skann
2. TILLSTAND_FASTNAR: tillståndsmaskin som fastnar (tillstånd utan väg ut)
3. KVARHALLEN_UTGANG_STOPP: utgång nollställs inte när cykeln bryts
4. LARM_KVITTERAT_UTAN_ORSAK: larm kvitteras utan att orsaken försvunnit
5. TIMER_FORVAL_ANDRAS: timerns förval ändras under drift (förkortat till 10 ms)
6. DIVISION_MED_NOLL: division med noll i aritmetiskt uttryck
7. ARRAY_INDEX_UTANFOR: arrayindex utanför dimensionen
8. RETENTIV_FORLORAD: RETAIN struket ur deklaration

PROVEN SKREVS FÖRE MEKANISMEN och var röda då.
"""
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc.mutation import skador  # noqa: E402

KROPP_FIXTUR = """PROGRAM Komplett
VAR RETAIN
    nRaknare : INT := 1;
END_VAR
VAR
    steg : INT := 0;
    trigPart : R_TRIG;
    tmrPaus : TON;
    xLarm : BOOL := FALSE;
    xDrift : BOOL := FALSE;
    buffer : ARRAY[1..10] OF INT;
    nKvot : REAL := 0.0;
    ST100_CNV_RUN : BOOL := FALSE;
END_VAR
    trigPart(CLK := xGivare);
    tmrPaus(IN := xDrift, PT := T#500ms);
    IF trigPart.Q THEN
        steg := 1;
    END_IF;
    IF tmrPaus.Q THEN
        xLarm := TRUE;
    END_IF;
    IF trigPart.Q AND EMG_OK AND AIR_OK THEN
        xLarm := FALSE;
    END_IF;
    IF NOT EMG_OK THEN
        ST100_CNV_RUN := FALSE;
        steg := 0;
    END_IF;
    CASE steg OF
        0: IF trigPart.Q THEN steg := 1; END_IF;
        1: ST100_CNV_RUN := TRUE; steg := 2;
        2: buffer[nRaknare] := 42;
           nKvot := 100.0 / nRaknare;
    END_CASE;
END_PROGRAM"""


def test_c6_flank_tavlar():
    """1. R_TRIG läses i fel ordning: trig()-anropet flyttat sist i skannet."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "FLANK_TAVLAR"]
    assert len(s) >= 1
    assert "trigPart(CLK := xGivare);" in s[0].fore
    assert s[0].vantat_lager == "beteende"
    # Anropet ska ha flyttats till slutet före END_PROGRAM
    assert s[0].kropp.strip().endswith("trigPart(CLK := xGivare);\nEND_PROGRAM")


def test_c6_tillstand_fastnar():
    """2. Tillståndsmaskin fastnar: tillståndsövergång struken."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "TILLSTAND_FASTNAR"]
    assert len(s) >= 1
    assert "steg :=" in s[0].fore
    assert "fastnar" in s[0].efter
    assert s[0].vantat_lager == "beteende"


def test_c6_kvarhallen_utgang_stopp():
    """3. Kvarhållen utgång vid stopp: utgångsnollställning i stoppvillkor struken."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "KVARHALLEN_UTGANG_STOPP"]
    assert len(s) >= 1
    assert "ST100_CNV_RUN := FALSE;" in s[0].fore
    assert "kvarhalls" in s[0].efter
    assert s[0].vantat_lager == "beteende"


def test_c6_larm_kvitterat_utan_orsak():
    """4. Larm kvitteras utan att orsaken försvunnit: säkerhetsvillkor strukna ur reset."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "LARM_KVITTERAT_UTAN_ORSAK"]
    assert len(s) >= 1
    assert "AND EMG_OK" in s[0].fore
    assert s[0].vantat_lager == "beteende"
    # Ny rad ska bara kräva trigPart.Q utan EMG_OK
    assert "IF trigPart.Q THEN" in s[0].kropp


def test_c6_timer_forval_andras():
    """5. Timerns förval ändras under drift: förval förkortas till 10 ms."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "TIMER_FORVAL_ANDRAS"]
    assert len(s) >= 1
    assert "PT := T#500ms" in s[0].fore
    assert "PT := T#10ms" in s[0].efter
    assert s[0].vantat_lager == "beteende"


def test_c6_division_med_noll():
    """6. Division med noll i aritmetiskt uttryck."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "DIVISION_MED_NOLL"]
    assert len(s) >= 1
    assert "/ nRaknare" in s[0].fore
    assert "/ 0.0" in s[0].efter
    assert s[0].vantat_lager == "beteende"


def test_c6_array_index_utanfor():
    """7. Arrayindex utanför dimensionen."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "ARRAY_INDEX_UTANFOR"]
    assert len(s) >= 1
    assert "buffer[nRaknare]" in s[0].fore
    assert "+ 100" in s[0].efter
    assert s[0].vantat_lager == "beteende"


def test_c6_retentiv_forlorad():
    """8. Retentivitet förlorad: VAR RETAIN -> VAR."""
    s = [x for x in skador(KROPP_FIXTUR) if x.sort == "RETENTIV_FORLORAD"]
    assert len(s) >= 1
    assert "VAR RETAIN" in s[0].fore
    assert s[0].efter == "VAR"
    assert s[0].vantat_lager == "beteende"
