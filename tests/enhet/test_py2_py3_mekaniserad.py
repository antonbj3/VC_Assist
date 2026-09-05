# -*- coding: utf-8 -*-
"""L1/L2: Enhetsprov for E5 - mekaniserad Python 2.7 & 3.x kompatibilitetskontroll.

Provar att granskningen vid installation mekaniskt avvisar py2/py3-inkompatibiliteter
i ext/ oavsett vilken pythonniva malet ar (E5).
"""
import ast
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "install"))

from install import paket


def test_alla_ext_filer_ar_giltiga_i_bada_versionerna():
    """Alla 11 filer i ext/vc_addon/vc_assist maste klara granskningen utan fel."""
    kalla = paket.kallmapp()
    filer = paket.kallfiler(kalla)
    problem = paket.granska_pythonfiler(kalla, filer, krav_bada=True)
    assert problem == [], "ext/ innehaller py2/py3-problem: %s" % problem


def test_f_strang_avvisas_mekaniskt_aven_pa_python3_niva(tmp_path):
    """Trasig fixtur: f-strang maste falla aven nar pythonniva='Python 3'."""
    kalla = tmp_path / "kalla"
    kalla.mkdir()
    # Kopiera over filer fran riktiga kallan
    riktig_kalla = paket.kallmapp()
    for f in paket.kallfiler(riktig_kalla):
        (kalla / f).write_bytes(open(os.path.join(riktig_kalla, f), "rb").read())

    # Introducera en f-strang i en fil
    with open(str(kalla / "protokoll.py"), "a") as fp:
        fp.write('\ndef nyhet(x):\n    return f"fel_{x}"\n')

    filer = paket.kallfiler(str(kalla))
    # Med krav_bada=True maste den falla
    problem = paket.granska_pythonfiler(str(kalla), filer, pythonniva="Python 3", krav_bada=True)
    assert any("f-strang" in p for p in problem), "f-strang maste avvisas"

    # Och installera() maste kasta Verifieringsfel
    mal = tmp_path / "mal"
    with pytest.raises(paket.Verifieringsfel):
        paket.installera(str(mal), kalla=str(kalla), pythonniva="Python 3")


def test_typannotering_avvisas_mekaniskt(tmp_path):
    """Trasig fixtur: typannotering i ext/ maste avvisas for py2-kompatibilitet."""
    kalla = tmp_path / "kalla"
    kalla.mkdir()
    riktig_kalla = paket.kallmapp()
    for f in paket.kallfiler(riktig_kalla):
        (kalla / f).write_bytes(open(os.path.join(riktig_kalla, f), "rb").read())

    with open(str(kalla / "protokoll.py"), "a") as fp:
        fp.write('\ndef med_typ(x: int) -> str:\n    return str(x)\n')

    filer = paket.kallfiler(str(kalla))
    problem = paket.granska_pythonfiler(str(kalla), filer, krav_bada=True)
    assert any("annotering" in p for p in problem), "Typannotering maste avvisas"
