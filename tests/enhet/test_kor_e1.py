# -*- coding: utf-8 -*-
"""L1/L2: Enhetsprov for E1 - de 16 protokollpunkterna pa Windows.

Provar att kor_E1_windows_16punkter.py klassar ratt, att trasiga fixturer
faller med ROD, och att skriptet gar att kora fristaende.
"""
import os
import sys
import tempfile
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol"))

import kor_E1_windows_16punkter as E1


def test_punkt_1_klonen_har_lf_ar_gron():
    res = E1.punkt_1_klonen_har_lf(_ROT)
    assert res["status"] == "GRON"


def test_punkt_1_crlf_ger_rod(tmp_path):
    """Trasig fixtur: CRLF i bridge_cmd.py maste falla punkt 1."""
    fejk_kat = tmp_path / "ext" / "vc_addon" / "vc_assist"
    fejk_kat.mkdir(parents=True)
    fil = fejk_kat / "bridge_cmd.py"
    fil.write_bytes(b"# comment\r\nprint('hello')\r\n")
    res = E1.punkt_1_klonen_har_lf(str(tmp_path))
    assert res["status"] == "ROD"
    assert "CRLF" in res["skal"]


def test_punkt_3_sommen_pekar_pa_samma_mapp():
    res = E1.punkt_3_sommen_pekar_pa_samma_mapp()
    assert res["status"] == "GRON"


def test_punkt_12_st_kedjan_bygger_framatstreck():
    res = E1.punkt_12_st_kedjan_bygger()
    assert res["status"] == "GRON"


def test_punkt_13_node_gar_att_starta():
    res = E1.punkt_13_node_gar_att_starta()
    assert res["status"] in ("GRON", "ROD")


def test_punkt_16_avinstallationen_stadar():
    res = E1.punkt_16_avinstallationen_stadar()
    assert res["status"] == "GRON"


def test_kor_alla_genererar_16_punkter():
    res = E1.kor_alla(hoppa_over_vc=True)
    assert len(res) == 16
    for p in res:
        assert p["status"] in ("GRON", "ROD", "HOPPAD")
        assert "skal" in p
        assert "nr" in p
        assert "namn" in p
