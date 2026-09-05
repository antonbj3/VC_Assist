# -*- coding: utf-8 -*-
"""Startskriptet far ALDRIG arva DISPLAY.

## Varfor provet finns

`docs/spec/90_invarianter.md` sager "satt DISPLAY explicit, arv den ALDRIG",
och skalet ar mätt: `os.environ.get("DISPLAY", ":99")` ARVER en satt DISPLAY,
och landade en gang pa operatorens `:1`.

Men `~/bin/vc-test.sh` - det DOKUMENTERADE sattet att starta VC, det som fem
protokollkorningar hanvisar till - satte inte DISPLAY alls. Den arvde.

2026-09-05 09:51 startade en session VC med `DISPLAY=:1` och utan WINEPREFIX.
Fonstret var pa vag upp pa operatorens skarm mitt i hans arbete. Halet satt
alltsa i sjalva skyddsracket: det sakra sattet var inte sakert.

## Varfor kopian ligger i repot

Skriptet bodde bara i `~/bin`, utanfor versionshantering. En invariant vars
mekanism inte gar att lasa i repot ar en invariant ingen kan granska. `drift/`
bar nu kopian, och provet nedan halller de tva lika.
"""
import os
import re
import subprocess
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_I_REPOT = os.path.join(_ROT, "drift", "vc-test.sh")
_I_BIN = os.path.expanduser("~/bin/vc-test.sh")


def _text(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def test_skriptet_satter_display_i_stallet_for_att_arva():
    s = _text(_I_REPOT)
    assert 'export DISPLAY=":99"' in s, "skriptet satter inte DISPLAY explicit"
    assert "VC_TEST_DISPLAY" in s, "det finns ingen uttrycklig vag till en synlig VC"


@pytest.mark.parametrize("miljo,vantad", [
    ({"DISPLAY": ":1"}, ":99"),
    ({"DISPLAY": ":0"}, ":99"),
    ({}, ":99"),
    ({"DISPLAY": ":0", "VC_TEST_DISPLAY": ":1"}, ":1"),
])
def test_valet_av_skarm(miljo, vantad):
    """TRASIG FIXTUR for arvet.

    Rad ett ar fallet som intraffade: en session med DISPLAY=:1 startade VC och
    fonstret gick mot operatorens skarm. Fore rattelsen hade skriptet lamnat
    DISPLAY orord och VC hade hamnat pa :1.
    """
    # Kor bara skarmvalet, inte hela skriptet - resten startar VC.
    s = _text(_I_REPOT)
    m = re.search(r'if \[ -n "\$VC_TEST_DISPLAY" \];.*?\nfi\n', s, re.S)
    assert m, "hittar inte skarmvalet i skriptet"
    kod = m.group(0) + '\necho "$DISPLAY"\n'
    e = dict(os.environ)
    e.pop("DISPLAY", None)
    e.pop("VC_TEST_DISPLAY", None)
    e.update(miljo)
    k = subprocess.run(["bash", "-c", kod], stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, env=e, timeout=30)
    assert k.stdout.decode().strip().splitlines()[-1] == vantad


def test_kopian_i_repot_och_den_i_bin_ar_lika():
    """En invariant vars mekanism bara finns utanfor repot gar inte att granska.

    Hoppas over nar ~/bin/vc-test.sh inte finns - pa en annan maskin ar repots
    kopia kallan, inte en spegel.
    """
    if not os.path.exists(_I_BIN):
        pytest.skip("~/bin/vc-test.sh finns inte pa den har maskinen")
    assert _text(_I_REPOT) == _text(_I_BIN), (
        "drift/vc-test.sh och ~/bin/vc-test.sh har glidit isar")


def test_skriptet_kraver_testprefixet():
    """Operatorens eget prefix ~/.wine-vc ror vi aldrig med oprovad kod."""
    s = _text(_I_REPOT)
    assert 'WINEPREFIX="$HOME/.wine-vc-test"' in s
    assert ".wine-vc\"" not in s.replace(".wine-vc-test", "")
