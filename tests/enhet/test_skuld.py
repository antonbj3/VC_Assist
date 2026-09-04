# -*- coding: utf-8 -*-
"""L1 for skuldregistret, och sparren som bara far ga at ett hall.

Registret genereras, aldrig fors for hand. Proven skyddar tva saker:
att skorden faktiskt hittar skulden, och att antalet matningar UTAN
arlighetsavsnitt bara kan krympa.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import skuld as S                              # noqa: E402

_MATNINGAR = os.path.join(_ROT, "docs", "matningar")

# Sa manga matningar som saknar ett arlighetsavsnitt. MATT 2026-09-05: 24 av
# 44, och alla utom tva ar skrivna fore M-44 - disciplinen satte sig senare.
#
# Talet far BARA ga nedat. Att hoja det ar att skriva en ny matning som inte
# sager vad den inte visar, och det ar precis den skuld registret finns for.
UTAN_ARLIGHETSAVSNITT = 24


def test_sparren_bara_krymper():
    utan = S.matningar_utan_arlighetsavsnitt(_MATNINGAR)
    assert len(utan) <= UTAN_ARLIGHETSAVSNITT, (
        "%d matningar saknar arlighetsavsnitt, taket ar %d. Nya:\n  %s"
        % (len(utan), UTAN_ARLIGHETSAVSNITT, "\n  ".join(utan)))


def test_sparren_ar_inte_slappare_an_verkligheten():
    """Ett tak som ligger over verkligheten mater ingenting.

    Samma regel som troskelskulden: sjunker talet ska taket sanktas, annars
    slutar sparren fanga nasta gang nagon glider.
    """
    utan = S.matningar_utan_arlighetsavsnitt(_MATNINGAR)
    assert len(utan) == UTAN_ARLIGHETSAVSNITT, (
        "verkligheten ar %d men taket sager %d - sank taket i test_skuld.py"
        % (len(utan), UTAN_ARLIGHETSAVSNITT))


# ---- skorden ur en matning -------------------------------------------------

def skriv(tmp_path, namn, text):
    p = tmp_path / namn
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_hittar_ett_arlighetsavsnitt_och_dess_punkter(tmp_path):
    f = skriv(tmp_path, "M-99_prov.md", """# M-99

## Utfall

Allt gick bra.

## Vad som INTE är mätt

* Windows.
* Fler än två signaler.

## Nasta avsnitt

Text.
""")
    poster = S.ur_matning(f)
    assert len(poster) == 1
    assert poster[0].rader == ["Windows.", "Fler än två signaler."]


def test_ett_numrerat_avsnitt_raknas_ocksa(tmp_path):
    """MATT: bade '## 9. Vad som inte ar matt' och '### F9. ...' finns i repot.

    Trasig fixtur for monstret sjalvt: en regex som kraver att rubriken borjar
    med ordet missar de har tyst, och da ser en arlig matning ut som en
    slarvig.
    """
    f = skriv(tmp_path, "M-98_prov.md", "# M-98\n\n## 9. Vad som inte är mätt\n\n* En sak.\n")
    assert S.ur_matning(f)[0].rader == ["En sak."]


def test_en_matning_utan_arlighetsavsnitt_hittas(tmp_path):
    skriv(tmp_path, "M-97_prov.md", "# M-97\n\n## Utfall\n\nAllt gick bra.\n")
    assert S.matningar_utan_arlighetsavsnitt(str(tmp_path)) == ["M-97_prov.md"]


def test_ett_avsnitt_utan_punkter_raknas_som_avsnitt_men_ger_noll_punkter(tmp_path):
    f = skriv(tmp_path, "M-96_prov.md",
              "# M-96\n\n## Vad som INTE är mätt\n\nIngenting, allt är mätt.\n")
    poster = S.ur_matning(f)
    assert len(poster) == 1 and poster[0].antal == 0


# ---- skorden ur koden ------------------------------------------------------

def test_hittar_markorer_i_koden(tmp_path):
    (tmp_path / "m.py").write_text(
        "X = 1  # PRELIMINÄR. Sätts av M-99.\ndef f():\n    pass  # TODO laga\n",
        encoding="utf-8")
    poster = S.ur_kod(str(tmp_path))
    assert len(poster) == 1
    assert poster[0].antal == 2


def test_registret_rapporterar_inte_sig_sjalvt(tmp_path):
    """En grind som far sin egen utdata som indata mater sig sjalv."""
    (tmp_path / "skuld.py").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / "test_skuld.py").write_text("# PRELIMINÄR\n", encoding="utf-8")
    assert S.ur_kod(str(tmp_path)) == []


# ---- registret som helhet --------------------------------------------------

def test_registret_gar_att_bygga_och_bar_bada_kallorna():
    reg = S.bygg(_ROT)
    assert reg["antal_punkter"] > 0
    assert reg["antal_kodmarkorer"] > 0
    t = S.text(reg)
    assert "Genererat" in t
    assert "Markörer i koden" in t
    assert str(len(reg["utan_arlighetsavsnitt"])) in t


def test_registerfilen_pa_disk_ar_aktuell():
    """En generad fil som slutat stamma ar samre an ingen fil.

    Faller det har: kor `PYTHONPATH=svc python3 -m vc_assist_svc.skuld
    --rot . --ut docs/matningar/SKULDREGISTER.md`
    """
    p = os.path.join(_MATNINGAR, "SKULDREGISTER.md")
    assert os.path.exists(p), "registret saknas pa disk"
    pa_disk = open(p, encoding="utf-8").read()
    reg = S.bygg(_ROT)
    # Bara rubrikraderna jamfors: sjalva punkterna andras med varje matning,
    # och ett prov som kraver byte-likhet hade fallit vid varje commit.
    for rad in ("## Mätningar utan ärlighetsavsnitt: %d"
                % len(reg["utan_arlighetsavsnitt"]),):
        assert rad in pa_disk, "registret pa disk ar inaktuellt: saknar %r" % rad
