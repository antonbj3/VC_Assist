# -*- coding: utf-8 -*-
"""Grinden som domer bankens facitkallor, provad i den grona sviten.

`tests/protocol/kor_bankens_facit.py` ar korningen. Den har filen provar dess
kontroller sa att de inte kan ruttna tyst: varje kontroll far en trasig fixtur
som MASTE falla, och hela banken provas mot dem.

Den tunga delen - att kora varje referenslosning och varje motbevis genom
ST-tolken - ligger i `tests/enhet/test_domare.py` och upprepas inte har.

beskriver: tests/protocol/kor_bankens_facit.py
"""
import copy
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "tests", "protocol")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import kor_bankens_facit as G                                    # noqa: E402
import lasare                                                    # noqa: E402


@pytest.fixture(scope="module")
def bank():
    return lasare.ladda(strikt=True)


@pytest.fixture(scope="module")
def matningar():
    return G.matningar_pa_disk()


@pytest.fixture(scope="module")
def verifierade():
    return G.las_verifierade_paragrafer()


# ------------------------------------------------------ kallan till listan

def test_paragraflistan_lases_ur_matningen_och_ar_inte_tom(verifierade):
    """En kopia i koden kan drifta fran matningen utan att nagon markte det."""
    assert len(verifierade) > 30, (
        "hittade %d uppslagna paragrafer i M-106; tabellformen har andrats"
        % len(verifierade))
    for vantad in (("IEC 60204-1", "9.2.3.4.2"), ("ISO 13850", "4.1.4"),
                   ("ISO 13855", "5.2"), ("IEC 61131-3", "6.6.3.5")):
        assert vantad in verifierade, vantad


def test_paragrafen_som_inte_finns_star_inte_i_listan(verifierade):
    """9.2.4 ar det uppfunna numret M-106 hittade i banken. Star det i listan
    ar listan inte langre en uppslagning."""
    assert ("IEC 60204-1", "9.2.4") not in verifierade


# ------------------------------------------------------- hela banken haller

def test_hela_banken_gar_igenom_utan_brister(bank, matningar, verifierade):
    brister = []
    for u in bank:
        brister += G.granska_uppgift(u.data, matningar, kor_domen=False,
                                     verifierade=verifierade)
    assert not brister, "\n".join(b.rad() for b in brister)


def test_varje_uppgift_med_sparfacit_namnger_en_kallklass(bank):
    med = [u for u in bank if u.data.get("facit_spar")]
    assert med, "banken bar inget sparfacit alls"
    for u in med:
        kk = u.data["facit_spar"].get("kallklass")
        assert kk, "%s: facit_spar saknar kallklass-falt" % u.id
        for k in kk.split("+"):
            assert k.strip() in G.KALLKLASSER, "%s: okand kallklass %r" % (u.id, k)


def test_saknad_kallklass_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["facit_spar"].pop("kallklass", None)
    assert "KALLKLASS_SAKNAS" in _koder(p, matningar, verifierade)


def test_okand_kallklass_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["facit_spar"]["kallklass"] = "PÅHITTAD_KLASS"
    assert "OKAND_KALLKLASS" in _koder(p, matningar, verifierade)


# ---------------------------------------------- trasiga fixturer (regel S2)

def _fixtur(bank):
    return copy.deepcopy(
        [u.data for u in bank if u.data.get("facit_spar")][0])


def _koder(post, matningar, verifierade):
    return [b.kod for b in G.granska_uppgift(post, matningar, kor_domen=False,
                                             verifierade=verifierade)]


def test_en_orord_fixtur_slapps_igenom(bank, matningar, verifierade):
    """Utan detta ar varje fallning nedan vardelos: en grind som avvisar allt
    klarar alla ovriga prov."""
    assert _koder(_fixtur(bank), matningar, verifierade) == []


def test_facit_ur_var_egen_tolk_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["facit_spar"]["harkomst"] = (
        "RAKNAD: fonstret ar hamtat ur svc/vc_assist_svc/st/tolk.py genom att "
        "kora referensen = 4,0 s. M-45")
    assert "FACIT_UR_EGEN_KOD" in _koder(p, matningar, verifierade)


def test_ett_antagande_utan_motiv_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["antaganden"][0]["motiv"] = ""
    assert "ANTAGANDE_UTAN_MOTIV" in _koder(p, matningar, verifierade)


def test_ett_tal_med_enhet_i_namnet_men_inte_i_vardet_falls(bank, matningar,
                                                            verifierade):
    """M-85: en enhet far aldrig harledas ur ett talvarde."""
    p = _fixtur(bank)
    p["antaganden"].append({"vad": "spanntrycket 4,5 bar", "varde": "4,5",
                            "motiv": "spanntrycket ar antaget och valt sa att "
                                     "spannaren haller detaljen med marginal"})
    assert "TAL_UTAN_ENHET" in _koder(p, matningar, verifierade)


def test_ett_uppfunnet_paragrafnummer_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["facit_spar"]["harkomst"] = (
        'STANDARD: manuell aterstallning enligt IEC 60204-1:2016 9.2.4 '
        '"Reset". M-45')
    assert "OVERIFIERAD_PARAGRAF" in _koder(p, matningar, verifierade)


def test_ett_bart_standardnummer_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["facit_spar"]["harkomst"] = "STANDARD: hall-for-att-kora enligt IEC 60204-1. M-45"
    p["facit_spar"]["standard"] = "IEC 60204-1 och IEC 61131-3"
    assert "STANDARD_UTAN_PARAGRAF" in _koder(p, matningar, verifierade)


def test_en_paragraf_utan_utgivare_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["facit_spar"]["harkomst"] = "STANDARD: kravet star i 9.2.3.7 och 4.1.4. M-45"
    p["facit_spar"]["standard"] = "paragraf 9.2.3.7 och paragraf 4.1.4"
    assert "STANDARD_UTAN_UTGIVARE" in _koder(p, matningar, verifierade)


def test_en_karnutgang_utan_spar_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    karn = p["core_outputs"][0]
    for sekv in p["facit_spar"]["sekvenser"]:
        for steg in sekv["steg"]:
            (steg.get("krav") or {}).pop(karn, None)
    p["facit_spar"]["invarianter"] = [
        i for i in (p["facit_spar"]["invarianter"] or [])
        if karn not in (i.get("nar") or {})
        and karn not in (i.get("kraver") or {})]
    p["facit_spar"]["flanker"] = [
        f for f in (p["facit_spar"]["flanker"] or [])
        if f.get("signal") != karn]
    assert "KARNUTGANG_UTAN_SPAR" in _koder(p, matningar, verifierade)


def test_en_harkomst_som_pekar_pa_en_matning_som_inte_finns_falls(
        bank, matningar, verifierade):
    p = _fixtur(bank)
    p["facit_spar"]["harkomst"] = "RAKNAD: 12,0 m / 0,010 m/s = 1200 s. M-9999"
    assert "HARKOMST_DOD_MATNING" in _koder(p, matningar, verifierade)


def test_en_karnutgang_som_inte_ar_utsignal_falls(bank, matningar, verifierade):
    p = _fixtur(bank)
    p["core_outputs"] = list(p["core_outputs"]) + ["ST999_XXX_YYY"]
    assert "KARNUTGANG_EJ_UTSIGNAL" in _koder(p, matningar, verifierade)


# ------------------------------------------------------------- larmskulden

class _Falsk(object):
    def __init__(self, data):
        self.data = data


def test_larmskulden_hittar_en_uppgift_som_ber_om_ett_larm_den_inte_kan_ge():
    """Trasig fixtur for skuldraknaren: ett scenario som sager larma i en
    signalkarta utan SYS_ALARM."""
    post = {"task_id": "X-42",
            "control": {"signals": [
                {"name": "ST999_CNV_RUN", "dir": "out", "type": "bool"},
                {"name": "EMG_OK", "dir": "in", "type": "bool"}]},
            "scenarios": [{"id": "a", "typ": "vandning", "signal": None,
                           "beskrivning": "givaren faller bort",
                           "forvantat": "styrningen ska larma och stanna"}]}
    utan_larm, utan_kvittens = G.larmskuld([_Falsk(post)])
    assert utan_larm == ["X-42"]
    assert utan_kvittens == []


def test_larmskulden_hittar_ett_larm_ingen_kan_kvittera():
    post = {"task_id": "X-43",
            "control": {"signals": [
                {"name": "SYS_ALARM", "dir": "out", "type": "bool"},
                {"name": "EMG_OK", "dir": "in", "type": "bool"}]},
            "scenarios": []}
    utan_larm, utan_kvittens = G.larmskuld([_Falsk(post)])
    assert utan_larm == [] and utan_kvittens == ["X-43"]


def test_larmskulden_star_pa_sitt_tak(bank):
    """Sparren far bara ga at ett hall. Vaxer listan har en ny uppgift lagts in
    som ber om ett larm den inte kan ge; krymper den ska talet skrivas ned."""
    utan_larm, utan_kvittens = G.larmskuld(bank)
    assert len(utan_larm) <= G.LARMSKULD, sorted(set(utan_larm))
    assert len(utan_kvittens) <= G.KVITTENSSKULD, sorted(set(utan_kvittens))
    assert len(utan_larm) == G.LARMSKULD, (
        "skulden ar nere i %d men taket star pa %d; skriv ned det nya talet i "
        "kor_bankens_facit.py och i M-106" % (len(utan_larm), G.LARMSKULD))


def test_ingen_av_de_nya_uppgifterna_ber_om_ett_larm_den_inte_kan_ge(bank):
    """M-106:s egna tolv uppgifter bar alla SYS_ALARM och SYS_RESET."""
    nya = {"P-06", "P-07", "A-07", "A-08", "H-05", "S-06", "S-07",
           "T-08", "T-09", "L-06", "L-07", "C-06"}
    utan_larm, utan_kvittens = G.larmskuld(bank)
    assert not (set(utan_larm) & nya), sorted(set(utan_larm) & nya)
    assert not (set(utan_kvittens) & nya), sorted(set(utan_kvittens) & nya)


# -------------------------------------------------------- korningens egen post

def test_korningen_bar_en_giltig_bankpost():
    """85_bankkontraktet.md §4: ingen foraldralos korning."""
    from vc_assist_svc import bankkontrakt as BK
    sokvag = os.path.join(_ROT, "tests", "protocol", "kor_bankens_facit.py")
    d = BK.las_bankpost(sokvag)
    assert d is not None, "korningen saknar BANKPOST"
    post, brister = BK.granska_post("kor_bankens_facit.py", d)
    assert not brister, brister
    assert set(post.facitkalla_filer) & set(post.under_prov) == set()
