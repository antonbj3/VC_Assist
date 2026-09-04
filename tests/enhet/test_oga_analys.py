# -*- coding: utf-8 -*-
"""L2: ogats dom over handbyggda celler. Ingen VC behovs.

Fas 2:s grind (70_faser.md): pa en handbyggd bra och en handbyggd trasig cell
ska ogats dom matcha facit i BADA. Den trasiga MASTE fallas.

Testerna kraver dessutom att fallningen sker pa RATT rad. En domare som faller
allt ar lika oanvandbar som en som godkanner allt, och bada ser bra ut om man
bara raknar fallningar.
"""
import os
import sys

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "tests")))

import celler                 # noqa: E402
import oga_analys as A        # noqa: E402
import oga_kontrakt as K      # noqa: E402


def _doma(namn):
    b, plan = celler.ALLA[namn]()
    text, rapport, analys = A.doma(b.data(), plan)
    # Domen ska overleva att den skrivs ut och lases tillbaka byte for byte.
    tillbaka = K.las(text)
    assert tillbaka.text() == text
    rader = [r for _s, rr in rapport.sektioner for r in rr]
    return rapport, rader, analys


def test_den_bra_cellen_far_PASS():
    """Utan detta ar varje fallning nedan varde los - en domare som faller
    allt klarar alla ovriga prov."""
    r, rader, _ = _doma("bra")
    assert r.dom[0] == "PASS", r.dom
    assert r.godkand() is True
    assert any(x.startswith("GRIP FORMED") for x in rader)
    assert any(x.startswith("CARRY RIGID") for x in rader)
    assert any(x.startswith("PLACE IN_TARGET") for x in rader)
    assert r.overtradelser() == []


FACIT = {
    "teleport":      ("FAIL", "TELEPORT_TRANSFER VIOLATION"),
    "glider":        ("FAIL", "CARRY SLIPPING"),
    "tappad":        ("FAIL", "PLACE DROPPED"),
    "fel_placerad":  ("FAIL", "PLACE OFF_TARGET"),
    "aldrig_gripen": ("FAIL", "NEVER_GRIPPED VIOLATION"),
    "explosion":     ("FAIL", "BLOWUP VIOLATION"),
    "under_golvet":  ("FAIL", "UNDERGROUND VIOLATION"),
    "kollision":     ("FAIL", "COLLISION gripper_finger x fixtur_vagg"),
    "kort_uppehall": ("FAIL", "SHORT"),
    "for_fa_prov":   ("INCONCLUSIVE", None),
}


@pytest.mark.parametrize("namn", sorted(FACIT))
def test_trasig_cell_falls_pa_sin_egen_orsak(namn):
    vantad_dom, vantad_rad = FACIT[namn]
    r, rader, _ = _doma(namn)
    assert r.dom[0] == vantad_dom, "%s fick %s: %s" % (namn, r.dom[0], r.dom[1])
    assert r.godkand() is False
    if vantad_rad:
        assert any(vantad_rad in x for x in rader), \
            "%s falldes, men inte pa %r. Rader: %s" % (namn, vantad_rad, rader)


def test_teleport_matter_avstandet_och_inte_bara_flaggar():
    """Talet ska bara sin egen storhet: 800 mm ar hela poangen."""
    r, rader, _ = _doma("teleport")
    rad = [x for x in rader if x.startswith("TELEPORT_TRANSFER")][0]
    assert "dist=800.0mm" in rad


def test_glidningen_matts_i_grader_i_verktygets_ram():
    r, rader, a = _doma("glider")
    rad = [x for x in rader if x.startswith("CARRY")][0]
    assert "rot=15.0deg" in rad
    assert abs(a.harledt["motion"]["carry"]["rot_deg"] - 15.0) < 0.1


def test_fel_placerad_bar_sitt_fel_i_mm():
    r, rader, _ = _doma("fel_placerad")
    assert "err=80.0mm" in [x for x in rader if x.startswith("PLACE")][0]


def test_en_overtradelse_tvingar_FAIL_aven_nar_allt_annat_ar_gront():
    """Teleportcellen har perfekt grepp, styv barning och ratt placering.
    Den ska anda falla - det ar hela skalet till att grinden finns."""
    r, rader, _ = _doma("teleport")
    assert any(x.startswith("PLACE IN_TARGET") for x in rader)
    assert any(x.startswith("CARRY RIGID") for x in rader)
    assert r.dom[0] == "FAIL"


def test_for_fa_prov_blir_inconclusive_inte_pass():
    """Fail-closed: brist pa underlag ar inte ett godkannande."""
    r, _rader, _ = _doma("for_fa_prov")
    assert r.dom[0] == "INCONCLUSIVE"
    assert r.godkand() is False


def test_ett_stillastaende_verktyg_bredvid_en_stillastaende_del_ar_inget_grepp():
    """Stillhet i verktygsramen ar trivialt sann nar bada star still. Utan
    varldsrorelsevillkoret blev det 'grepp vid t=0' och en falsk teleportdom."""
    b = celler.Bygge("stillastaende")
    for _ in range(40):
        b.steg([0.5, 0.0, 0.75], [0.0, 0.0, 1.4])
    r = A.Analys(b.data(), celler.plan()).rapport()
    rader = [x for _s, rr in r.sektioner for x in rr]
    assert any(x == "GRIP NEVER_FORMED" for x in rader)
    assert not any("TELEPORT_TRANSFER VIOLATION" in x for x in rader)


def test_domen_pekar_ut_orsaken_i_klartext():
    for namn in ("teleport", "glider", "tappad", "kort_uppehall"):
        r, _rader, _ = _doma(namn)
        assert len(r.dom[1]) > 10, "%s: domen sager inte varfor" % namn


@pytest.mark.parametrize("namn", sorted(celler.ALLA))
def test_varje_cell_ger_en_rapport_som_lases_tillbaka(namn):
    """En rapport som kraschar domaren kan dolja rott."""
    _doma(namn)
