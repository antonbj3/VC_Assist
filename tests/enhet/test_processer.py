# -*- coding: utf-8 -*-
"""En sokare far aldrig hitta sig sjalv.

Fallan har utlost TRE ganger i det har projektet:

1. `pgrep -f` rapporterade VC igang pa operatorens skarm - traffen var
   sokningen sjalv.
2. En vantare skriven som `until ! pgrep -f kor_fas9_slingan` vantade pa sig
   sjalv och snurrade for evigt.
3. 2026-09-05: ett skal-`case` over `/proc/<pid>/cmdline` rapporterade TVA
   ganger att en session startat VC med `DISPLAY=:1` pa operatorens skarm.
   Falskt bada gangerna, och den rapporterade DISPLAY var sokarens egen.

Det tredje ar det dyraste: ett falsklarm om ett INVARIANTBROTT flyttar
uppmarksamheten till ett fel som inte finns.

Regeln lades i ett minne efter forsta gangen och upprepades anda tva ganger.
Det ar skalet att den nu ar ett verktyg med prov, inte en regel att komma ihag.
"""
import os
import subprocess
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import processer as P                            # noqa: E402


def test_sokaren_hittar_inte_sig_sjalv_pa_sin_egen_strang():
    """TRASIG FIXTUR, och den ar exakt fallet som intraffade.

    Underprocessen soker efter en strang som star i dess EGEN kommandorad. Ett
    naivt `/proc`-svep hittar sig sjalv; det har verktyget far inte.
    """
    magisk = "VCASSIST_SJALVMATCHNING_PROV"
    kod = (
        "import sys; sys.path.insert(0, %r)\n"
        "from vc_assist_svc import processer as P\n"
        "print(len(P.med_argument(%r)))\n" % (os.path.join(_ROT, "svc"), magisk))
    k = subprocess.run([sys.executable, "-c", kod, magisk],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=60)
    ut = k.stdout.decode("utf-8", "replace").strip().splitlines()[-1]
    assert ut == "0", (
        "sokaren hittade %s process(er) - den raknade sig sjalv" % ut)


def test_foraldrarna_utesluts_ocksa():
    """En agent kors av ett skal som kors av en session, och BADA bar
    sokstrangen. Att bara utesluta sig sjalv racker inte."""
    slakt = P._slakt()
    assert os.getpid() in slakt
    assert len(slakt) >= 2, "hittade ingen foralder - kedjan gar inte att lita pa"
    mor = os.getppid()
    if mor > 1:
        assert mor in slakt


def test_binarsokning_ar_forstahandsvalet():
    """med_binar fragar /proc/<pid>/exe. En sokare kan inte rakna sig sjalv sa
    lange den fragar efter ett ANNAT program an det den kors av."""
    mina = P.med_binar("python")
    assert os.getpid() in mina, "borde hitta mig sjalv nar jag fragar efter python"
    assert P.med_binar("ett-program-som-inte-finns-alls") == []


def test_vc_i_operatorens_prefix_ar_tomt():
    """`90_invarianter.md`: operatorens prefix ror vi aldrig med oprovad kod.

    Provet gor invarianten FRAGBAR i stallet for ihagkommen. Faller den har
    nagon startat VC i ~/.wine-vc, och det ska stoppa allt.
    """
    i_hans = P.i_operatorens_prefix()
    assert i_hans == [], (
        "VC kor i operatorens EGNA prefix: %s" % i_hans)


def test_vc_processer_bar_skarm_och_prefix():
    """Utan de tva falten gar det inte att avgora om en korande VC ar laglig.

    Hoppas over nar ingen VC kor - da finns inget att lasa, och det ar inte
    ett godkannande."""
    vc = P.vc_processer()
    if not vc:
        pytest.skip("ingen VC kor just nu")
    for p in vc:
        assert "pid" in p and "display" in p and "wineprefix" in p


def test_en_korande_vc_star_pa_dold_skarm_i_testprefixet():
    """Det som faktiskt ska gälla nar vi kor.

    Hoppas over nar ingen VC kor. En VC pa :0 eller :1, eller i ett annat
    prefix, ar ett invariantbrott och ska fallas har - inte upptackas av att
    operatoren ser ett fonster.
    """
    vc = P.vc_processer()
    if not vc:
        pytest.skip("ingen VC kor just nu")
    test_prefix = os.path.expanduser("~/.wine-vc-test")
    for p in vc:
        assert p["wineprefix"] == test_prefix, (
            "VC pid %s kor i %r, inte i testprefixet" % (p["pid"], p["wineprefix"]))
        assert p["display"] == ":99", (
            "VC pid %s star pa %r - operatoren arbetar pa sin skarm"
            % (p["pid"], p["display"]))
