# -*- coding: utf-8 -*-
"""L1: matiec-klient och typjämförelse mot vår ST-validator.

Ingen docker här (L1): kompilatorn är lokal ($VC_ASSIST_MATIEC eller
/tmp/opencode/matiec/iec2c).

Disciplin:
  - Ingen grind utan trasig fixtur (96_ingen_skuld.md S2).
  - Fixtur: 4.0 * antal (INT) avvisas med 'Data type mismatch' och INT_TO_REAL
    godkänns.
  - Minst 10 typfall med klassificering:
      * OVERENS (båda godkänner eller båda fäller)
      * VI_STRANGARE (vi fäller, matiec godkänner)
      * MATIEC_STRANGARE (matiec fäller, vi släpper — farligaste klassen: vår
        grind läcker typfel som OpenPLC-kedjan fäller).
"""
from __future__ import annotations

import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc import matiec as M  # noqa: E402
from vc_assist_svc.st.validator import validera  # noqa: E402


# ==============================================================================
# TRASIG FIXTUR (FÖRE MEKANISMEN)
# ==============================================================================

def test_trasig_fixtur_data_type_mismatch_och_int_to_real():
    """Trasig fixtur: matiec fäller 4.0 * antal (INT) och godkänner INT_TO_REAL.

    M-121 §T-04: IEC 61131-3:2003 §2.5.1.4 kräver explicit konvertering vid MUL
    över ANY_NUM. STruC++ accepterade tyst, medan matiec avvisar med 'Data type
    mismatch for '*' expression.'.
    """
    trasig_kod = (
        "PROGRAM P\n"
        "VAR\n"
        "    antal : INT;\n"
        "    r : REAL;\n"
        "END_VAR\n"
        "    r := 4.0 * antal;\n"
        "END_PROGRAM\n"
    )
    res_trasig = M.kompilera(trasig_kod)
    assert res_trasig.accepterad is False
    assert len(res_trasig.fel) >= 1
    # Kontrollera att felmeddelandet bär matiecs exakta typdom
    feltexter = " ".join(meddelande for _rad, _kol, meddelande in res_trasig.fel)
    assert "data type mismatch" in feltexter.lower()
    assert "*" in feltexter
    # Kontrollera radnummer
    rader = [rad for rad, _kol, _msg in res_trasig.fel if rad > 0]
    assert 6 in rader or any(rad == 6 for rad, _, _ in res_trasig.fel)

    lagad_kod = (
        "PROGRAM P\n"
        "VAR\n"
        "    antal : INT;\n"
        "    r : REAL;\n"
        "END_VAR\n"
        "    r := 4.0 * INT_TO_REAL(antal);\n"
        "END_PROGRAM\n"
    )
    res_lagad = M.kompilera(lagad_kod)
    assert res_lagad.accepterad is True
    assert len(res_lagad.fel) == 0


# ==============================================================================
# 20+ TYPFALL: MATIEC MOT VÅR VALIDATOR
# ==============================================================================

TYPFALL = [
    # ---- OVERENS (båda fäller) -----------------------------------------------
    (
        "mul_real_int_vars",
        "rA := 4.0 * iA;",
        "iA : INT; rA : REAL;",
        "OVERENS",
        "Data type mismatch for '*' expression.",
    ),
    (
        "assign_real_to_bool",
        "bA := 4.0 * iA;",
        "iA : INT; bA : BOOL;",
        "OVERENS",
        "Data type mismatch for '*' expression.",
    ),
    (
        "assign_int_to_bool",
        "bA := iA;",
        "iA : INT; bA : BOOL;",
        "OVERENS",
        "Incompatible data types for ':=' operation.",
    ),
    (
        "assign_real_to_int",
        "iA := rA;",
        "iA : INT; rA : REAL;",
        "OVERENS",
        "Incompatible data types for ':=' operation.",
    ),
    (
        "assign_dint_to_int",
        "iA := dA;",
        "iA : INT; dA : DINT;",
        "OVERENS",
        "Incompatible data types for ':=' operation.",
    ),
    (
        "bit_int_and_bool",
        "bA := iA AND bA;",
        "iA : INT; bA : BOOL;",
        "OVERENS",
        "Data type mismatch for 'AND' expression.",
    ),
    (
        "time_add_int",
        "tA := tA + iA;",
        "iA : INT; tA : TIME;",
        "OVERENS",
        "Data type mismatch for '+' expression.",
    ),
    (
        "time_cmp_int",
        "bA := tA < iA;",
        "iA : INT; tA : TIME; bA : BOOL;",
        "OVERENS",
        "Data type mismatch for '<' expression.",
    ),
    (
        "byte_assign_word",
        "byA := wA;",
        "wA : WORD; byA : BYTE;",
        "OVERENS",
        "Incompatible data types for ':=' operation.",
    ),
    (
        "assign_real_lit_to_int",
        "iA := 3.5;",
        "iA : INT;",
        "OVERENS",
        "Incompatible data types for ':=' operation.",
    ),
    # ---- OVERENS (båda godkänner) --------------------------------------------
    (
        "mul_real_int_to_real",
        "rA := 4.0 * INT_TO_REAL(iA);",
        "iA : INT; rA : REAL;",
        "OVERENS",
        "",
    ),
    (
        "cmp_real_real_lit",
        "bA := rA < 4.0;",
        "rA : REAL; bA : BOOL;",
        "OVERENS",
        "",
    ),
    (
        "time_mul_int_var",
        "tA := tA * iA;",
        "iA : INT; tA : TIME;",
        "OVERENS",
        "",
    ),
    (
        "time_mul_int_lit",
        "tA := tA * 2;",
        "tA : TIME;",
        "OVERENS",
        "",
    ),
    (
        "time_add_time",
        "tA := tA + tB;",
        "tA, tB : TIME;",
        "OVERENS",
        "",
    ),
    (
        "time_cmp_time",
        "bA := tA < tB;",
        "tA, tB : TIME; bA : BOOL;",
        "OVERENS",
        "",
    ),
    # ---- VI_STRANGARE (vi fäller, matiec godkänner) --------------------------
    (
        "var_input_write",
        "iA := 1;",
        "VAR_INPUT iA : INT; END_VAR",
        "VI_STRANGARE",
        "",
    ),
    (
        "concat_literals",
        "sA := CONCAT('a', 'b');",
        "sA : STRING;",
        "VI_STRANGARE",
        "",
    ),
    (
        "exit_outside_loop",
        "EXIT;",
        "iA : INT;",
        "VI_STRANGARE",
        "",
    ),
    # ---- MATIEC_STRANGARE (matiec fäller, vår validator släpper) -------------
    (
        "assign_int_to_real",
        "rA := iA;",
        "iA : INT; rA : REAL;",
        "MATIEC_STRANGARE",
        "Incompatible data types for ':=' operation.",
    ),
    (
        "assign_int_to_dint",
        "dA := iA;",
        "iA : INT; dA : DINT;",
        "MATIEC_STRANGARE",
        "Incompatible data types for ':=' operation.",
    ),
    (
        "cmp_real_int_var",
        "bA := rA < iA;",
        "iA : INT; rA : REAL; bA : BOOL;",
        "MATIEC_STRANGARE",
        "Data type mismatch for '<' expression.",
    ),
    (
        "cmp_real_int_lit",
        "bA := rA < 4;",
        "rA : REAL; bA : BOOL;",
        "MATIEC_STRANGARE",
        "Data type mismatch for '<' expression.",
    ),
    (
        "add_real_int_var",
        "rA := rA + iA;",
        "iA : INT; rA : REAL;",
        "MATIEC_STRANGARE",
        "Data type mismatch for '+' expression.",
    ),
    (
        "word_assign_byte",
        "wA := byA;",
        "wA : WORD; byA : BYTE;",
        "MATIEC_STRANGARE",
        "Incompatible data types for ':=' operation.",
    ),
    (
        "mul_int_lit_real_lit",
        "rA := 2 * 3.5;",
        "rA : REAL;",
        "MATIEC_STRANGARE",
        "Data type mismatch for '*' expression.",
    ),
    (
        "add_int_lit_real_lit",
        "rA := 2 + 3.5;",
        "rA : REAL;",
        "MATIEC_STRANGARE",
        "Data type mismatch for '+' expression.",
    ),
    (
        "sel_mixed_num",
        "rA := SEL(bA, 1, 2.0);",
        "bA : BOOL; rA : REAL;",
        "MATIEC_STRANGARE",
        "Unable to resolve which overloaded function 'SEL' is being invoked.",
    ),
]


def _skapa_program(body: str, dekl: str) -> str:
    if "VAR_INPUT" in dekl or "VAR CONSTANT" in dekl:
        return f"PROGRAM P\n{dekl}\n    {body}\nEND_PROGRAM\n"
    return f"PROGRAM P\nVAR\n    {dekl}\nEND_VAR\n    {body}\nEND_PROGRAM\n"


@pytest.mark.parametrize("namn,kropp,dekl,forvantad_klass,matiec_delstrang", TYPFALL)
def test_typfall_matiec_mot_validator(namn, kropp, dekl, forvantad_klass, matiec_delstrang):
    """Jämför matiec och validator på typfallet och verifiera klassificeringen."""
    kod = _skapa_program(kropp, dekl)

    # 1. Kör vår validator
    val_res = validera(kod)
    val_ok = val_res.ok

    # 2. Kör matiec
    mat_res = M.kompilera(kod)
    mat_ok = mat_res.accepterad

    # 3. Härled klass
    if val_ok and mat_ok:
        observerad_klass = "OVERENS"
    elif (not val_ok) and (not mat_ok):
        observerad_klass = "OVERENS"
    elif (not val_ok) and mat_ok:
        observerad_klass = "VI_STRANGARE"
    else:
        observerad_klass = "MATIEC_STRANGARE"

    assert observerad_klass == forvantad_klass, (
        f"Typfall '{namn}': förväntade {forvantad_klass}, fick {observerad_klass}. "
        f"Validator ok={val_ok} ({[str(a) for a in val_res.anmarkningar]}), "
        f"Matiec ok={mat_ok} ({mat_res.fel})"
    )

    if not mat_ok and matiec_delstrang:
        feltexter = " ".join(msg for _, _, msg in mat_res.fel)
        assert matiec_delstrang.lower() in feltexter.lower(), (
            f"Typfall '{namn}': förväntade '{matiec_delstrang}' i matiecs fel, fick: {feltexter}"
        )


# ==============================================================================
# KLIENTENS ROBUSTHET OCH FAIL-CLOSED EGENSKAPER
# ==============================================================================

def test_sokordning_hittar_binar():
    """Hittar binären via lokal sökväg eller env."""
    binar, lib = M.hitta_binar()
    assert os.path.isfile(binar)
    assert os.access(binar, os.X_OK)
    assert os.path.isdir(lib)
    assert os.path.isfile(os.path.join(lib, "ieclib.txt"))


def test_sokordning_env_override(monkeypatch, tmp_path):
    """$VC_ASSIST_MATIEC har företräde framför standardsökvägar."""
    fake_iec = tmp_path / "iec2c"
    fake_lib = tmp_path / "lib"
    fake_lib.mkdir()
    (fake_lib / "ieclib.txt").write_text("(* dummy *)", encoding="ascii")
    fake_iec.write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
    fake_iec.chmod(0o755)

    monkeypatch.setenv("VC_ASSIST_MATIEC", str(fake_iec))
    binar, lib = M.hitta_binar()
    assert binar == str(fake_iec)
    assert lib == str(fake_lib)


def test_felaktig_syntax_ger_rad_och_kolumn():
    """Verifierar att syntaxfel parsar rad och kolumn korrekt."""
    kod = (
        "PROGRAM P\n"
        "VAR\n"
        "    i : INT;\n"
        "END_VAR\n"
        "    i := ;\n"
        "END_PROGRAM\n"
    )
    res = M.kompilera(kod)
    assert res.accepterad is False
    assert len(res.fel) >= 1
    rad, kol, msg = res.fel[0]
    assert rad == 5
    assert kol >= 1
    assert "no expression defined" in msg.lower()


def test_tidsgrans_fail_closed(monkeypatch):
    """Timeout ger fail-closed: accepterad=False, felmeddelande, ingen hängning."""
    import subprocess
    orig_run = subprocess.run

    def mock_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=0.1)

    monkeypatch.setattr(subprocess, "run", mock_timeout)
    res = M.kompilera("PROGRAM P\nVAR a: BOOL; END_VAR\nEND_PROGRAM\n", tidsgrans=0.1)
    assert res.accepterad is False
    assert len(res.fel) == 1
    assert "tidsgräns" in res.fel[0][2].lower() or "svarade inte" in res.fel[0][2].lower()
