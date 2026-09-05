# -*- coding: utf-8 -*-
"""L1: klassificering och bänkkontrakt för OpenPLC-mätningarna (M-108).

Inget här startar docker, öppnar nätverksuttag eller kräver STruC++ (L1-regel,
se tests/enhet/test_plc.py huvudet). Allt som kräver en körande runtime hör till
tests/protocol/fas6_plcbandet.md eller kor_openplc_*.py.

Provet täcker:
  1. klassificera() i kor_openplc_svepet.py: varje gren (OVERENS,
     STRANGARE_BEKRAFTAD, NY_STRANGARE, HAL_BEKRAFTAD, NYTT_HAL, TVAFALL,
     LATTARE_OPROVAD, STRANGARE_OPROVAD, EJ_KORD).
  2. Trasiga fixturer: EJ_KORD får aldrig bli OVERENS (alla None-kombinationer);
     STRANGARE_BEKRAFTAD kräver dict-rad; facit-tabellerna får inte överlappa.
  3. BENCH-4-vakt (docs/spec/85_bankkontraktet.md §2): för BÅDA kör-skriptens
     BANKPOST (svepet och scan). facitkalla_filer ∩ under_prov == tom,
     under_prov icke-tom, facitkalla_filer == ().
  4. Svepets kontrakt: FALL har exakt 247 poster, unika namn, läst via _las_svep.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _ladda_modul(relativ_sokvag: str, modulnamn: str):
    full_sokvag = os.path.join(_ROT, relativ_sokvag)
    spec = importlib.util.spec_from_file_location(modulnamn, full_sokvag)
    if spec is None or spec.loader is None:
        raise ImportError("Kunde inte skapa spec för %s" % full_sokvag)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture(scope="module")
def svep_modul():
    return _ladda_modul(
        os.path.join("tests", "protocol", "kor_openplc_svepet.py"),
        "kor_openplc_svepet"
    )


@pytest.fixture(scope="module")
def scan_modul():
    return _ladda_modul(
        os.path.join("tests", "protocol", "kor_openplc_scan.py"),
        "kor_openplc_scan"
    )


@pytest.fixture(scope="module")
def r3_modul():
    return _ladda_modul(
        os.path.join("tests", "protocol", "kor_openplc_r3.py"),
        "kor_openplc_r3"
    )


@pytest.fixture(scope="module")
def opcua_modul():
    return _ladda_modul(
        os.path.join("tests", "protocol", "kor_openplc_opcua.py"),
        "kor_openplc_opcua"
    )


@pytest.fixture(scope="module")
def hang_modul():
    return _ladda_modul(
        os.path.join("tests", "protocol", "kor_openplc_hang.py"),
        "kor_openplc_hang"
    )


@pytest.fixture(scope="module")
def svep_facit(svep_modul):
    FALL, kalla, STRANGARE, LATTARE = svep_modul._las_svep()
    return {
        "FALL": FALL,
        "kalla": kalla,
        "STRANGARE": STRANGARE,
        "LATTARE": LATTARE,
    }


# ---- 1. klassificera(): varje gren ---------------------------------------

@pytest.mark.parametrize("var_utfall,openplc_utfall", [
    (True, True),
    (False, False),
])
def test_klassificera_overens(svep_modul, svep_facit, var_utfall, openplc_utfall):
    rad = {
        "namn": "fall_overens",
        "var": var_utfall,
        "strucpp": var_utfall,
        "openplc": openplc_utfall,
    }
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "OVERENS"


def test_klassificera_strangare_bekraftad_for_alla_verkliga_rader(svep_modul, svep_facit):
    """Alla verkliga STRANGARE-rader från svepfilen måste bli STRANGARE_BEKRAFTAD."""
    strangare = svep_facit["STRANGARE"]
    assert len(strangare) > 0, "STRANGARE-dict får inte vara tomt"
    for namn in strangare:
        rad = {"namn": namn, "var": False, "openplc": True}
        klass = svep_modul.klassificera(rad, strangare, svep_facit["LATTARE"])
        assert klass == "STRANGARE_BEKRAFTAD", (
            "Väntade STRANGARE_BEKRAFTAD för %s, fick %s" % (namn, klass)
        )


def test_klassificera_ny_strangare_syntetiskt_namn(svep_modul, svep_facit):
    """Ett syntetiskt namn som saknar rad i STRANGARE ska bli NY_STRANGARE."""
    syntetiskt_namn = "syntetisk_ny_strangare_ej_i_dict"
    assert syntetiskt_namn not in svep_facit["STRANGARE"]
    rad = {"namn": syntetiskt_namn, "var": False, "openplc": True}
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "NY_STRANGARE"


def test_klassificera_hal_bekraftad_for_alla_verkliga_rader(svep_modul, svep_facit):
    """Alla verkliga LATTARE-rader från svepfilen måste bli HAL_BEKRAFTAD."""
    lattare = svep_facit["LATTARE"]
    assert len(lattare) > 0, "LATTARE-dict får inte vara tomt"
    for namn in lattare:
        rad = {"namn": namn, "var": True, "openplc": False}
        klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], lattare)
        assert klass == "HAL_BEKRAFTAD", (
            "Väntade HAL_BEKRAFTAD för %s, fick %s" % (namn, klass)
        )


def test_klassificera_nytt_hal_syntetiskt_namn(svep_modul, svep_facit):
    """Ett syntetiskt namn som saknar rad i LATTARE ska bli NYTT_HAL."""
    syntetiskt_namn = "syntetiskt_nytt_hal_ej_i_dict"
    assert syntetiskt_namn not in svep_facit["LATTARE"]
    rad = {"namn": syntetiskt_namn, "var": True, "openplc": False}
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "NYTT_HAL"


def test_klassificera_tvafall(svep_modul, svep_facit):
    """Båda lokala motorer avvisar (False/False/None) -> TVAFALL."""
    rad = {"namn": "bada_avvisar", "var": False, "strucpp": False, "openplc": None}
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "TVAFALL"


def test_klassificera_lattare_oprovad(svep_modul, svep_facit):
    """Vi släpper, STruC++ avvisar lokalt, OpenPLC ej körd (True/False/None) -> LATTARE_OPROVAD."""
    rad = {"namn": "vi_slapper_strucpp_avvisar", "var": True, "strucpp": False, "openplc": None}
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "LATTARE_OPROVAD"


def test_klassificera_strangare_oprovad(svep_modul, svep_facit):
    """Vi avvisar, STruC++ godkänner lokalt, OpenPLC ej körd (False/True/None) -> STRANGARE_OPROVAD."""
    rad = {"namn": "vi_avvisar_strucpp_godkanner", "var": False, "strucpp": True, "openplc": None}
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "STRANGARE_OPROVAD"


@pytest.mark.parametrize("var_val,strucpp_val,openplc_val", [
    (None, True, True),
    (None, False, False),
    (None, None, None),
    (True, True, None),      # True/True/None (båda lokala godkände men OpenPLC kördes inte)
    (True, None, None),
    (False, None, None),
])
def test_klassificera_ej_kord_grenar(svep_modul, svep_facit, var_val, strucpp_val, openplc_val):
    rad = {
        "namn": "ej_kord_fall",
        "var": var_val,
        "strucpp": strucpp_val,
        "openplc": openplc_val,
    }
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "EJ_KORD"


def test_klassificera_ej_kord_vid_krasch(svep_modul, svep_facit):
    """En kraschad grind levererar var=None och var_fel=KRASCH:... -> EJ_KORD."""
    rad = {
        "namn": "kraschfall",
        "var": None,
        "var_fel": "KRASCH: ValueError('syntaktiskt fel')",
        "strucpp": None,
        "strucpp_fel": None,
    }
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "EJ_KORD"


# ---- 2. Trasiga fixturer -------------------------------------------------

NONE_KOMBINATIONER_FOR_EJ_KORD = [
    # (var, strucpp, openplc)
    (None, None, None),
    (None, None, True),
    (None, None, False),
    (None, True, None),
    (None, True, True),
    (None, True, False),
    (None, False, None),
    (None, False, True),
    (None, False, False),
    (True, None, None),
    (True, True, None),
    (False, None, None),
]


@pytest.mark.parametrize("var_val,strucpp_val,openplc_val", NONE_KOMBINATIONER_FOR_EJ_KORD)
def test_trasig_fixtur_ej_kord_blir_aldrig_overens(svep_modul, svep_facit, var_val, strucpp_val, openplc_val):
    """EJ_KORD får aldrig rapporteras som OVERENS."""
    rad = {
        "namn": "trasig_korning",
        "var": var_val,
        "strucpp": strucpp_val,
        "openplc": openplc_val,
    }
    klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
    assert klass == "EJ_KORD"
    assert klass != "OVERENS"


def test_trasig_fixtur_alla_none_kombinationer_utesluter_falsk_overens(svep_modul, svep_facit):
    """Ingen kombination där var eller openplc är None får någonsin bli OVERENS."""
    utfall = [None, True, False]
    for v in utfall:
        for s in utfall:
            for o in utfall:
                rad = {"namn": "kombinationstest", "var": v, "strucpp": s, "openplc": o}
                klass = svep_modul.klassificera(rad, svep_facit["STRANGARE"], svep_facit["LATTARE"])
                if v is None or o is None:
                    assert klass != "OVERENS", (
                        "Falsk OVERENS för v=%s, s=%s, o=%s -> %s" % (v, s, o, klass)
                    )


def test_trasig_fixtur_strangare_bekraftad_kraver_dict_rad(svep_modul, svep_facit):
    """STRANGARE_BEKRAFTAD kräver dict-rad; samma namn utan rad blir NY_STRANGARE."""
    strangare = svep_facit["STRANGARE"]
    for namn in strangare:
        rad = {"namn": namn, "var": False, "openplc": True}
        # Med dict-rad:
        assert svep_modul.klassificera(rad, strangare, svep_facit["LATTARE"]) == "STRANGARE_BEKRAFTAD"
        # Utan dict-rad (tom dict):
        assert svep_modul.klassificera(rad, {}, svep_facit["LATTARE"]) == "NY_STRANGARE"


def test_trasig_fixtur_hal_bekraftad_kraver_dict_rad(svep_modul, svep_facit):
    """HAL_BEKRAFTAD kräver dict-rad; samma namn utan rad blir NYTT_HAL."""
    lattare = svep_facit["LATTARE"]
    for namn in lattare:
        rad = {"namn": namn, "var": True, "openplc": False}
        # Med dict-rad:
        assert svep_modul.klassificera(rad, svep_facit["STRANGARE"], lattare) == "HAL_BEKRAFTAD"
        # Utan dict-rad (tom dict):
        assert svep_modul.klassificera(rad, svep_facit["STRANGARE"], {}) == "NYTT_HAL"


def test_trasig_fixtur_facittabellerna_far_inte_overlappa(svep_facit):
    """STRANGARE och LATTARE får inte ha några gemensamma nycklar."""
    strangare_nycklar = set(svep_facit["STRANGARE"].keys())
    lattare_nycklar = set(svep_facit["LATTARE"].keys())
    overlapp = strangare_nycklar & lattare_nycklar
    assert overlapp == set(), "Facittabellerna överlappar: %s" % overlapp


def test_trasig_fixtur_overlappskontroll_faller_pa_saboterat_overlapp(svep_facit):
    """En trasig fixtur med injicerat överlapp måste upptäckas av kontrollen."""
    saboterat_strangare = dict(svep_facit["STRANGARE"])
    saboterat_strangare["tid_negativ"] = "sabotage: samma nyckel i båda"
    lattare_nycklar = set(svep_facit["LATTARE"].keys())
    assert "tid_negativ" in lattare_nycklar
    overlapp = set(saboterat_strangare.keys()) & lattare_nycklar
    assert "tid_negativ" in overlapp


# ---- 3. BENCH-4-vakt (docs/spec/85_bankkontraktet.md §2) -----------------

def _validera_bench4_post(bankpost: dict) -> list[str]:
    """Mekanisk validering av Bänkkontraktet §1 och §2 (BENCH-4)."""
    fel = []
    obligatoriska = ("pastar", "under_prov", "facit", "facitkalla", "trasiga_fall")
    for f in obligatoriska:
        if f not in bankpost or not bankpost[f]:
            fel.append("Saknar obligatoriskt fält eller är tomt: %s" % f)

    under_prov = bankpost.get("under_prov", ())
    facitkalla_filer = bankpost.get("facitkalla_filer", None)

    if not under_prov:
        fel.append("under_prov får inte vara tom")

    if facitkalla_filer != ():
        fel.append("facitkalla_filer ska vara tom tuple () för externt program, fick %r"
                   % (facitkalla_filer,))

    # BENCH-4-vakt: facitkalla_filer ∩ under_prov får inte överlappa
    for fk in facitkalla_filer or ():
        for up in under_prov:
            if fk == up or fk.startswith(up.rstrip("/") + "/") or up.startswith(fk.rstrip("/") + "/"):
                fel.append("BENCH-4-överträdelse: facitkälla %s överlappar under_prov %s" % (fk, up))

    return fel


@pytest.mark.parametrize("skriptnamn,modul_fixtur", [
    ("kor_openplc_svepet.py", "svep_modul"),
    ("kor_openplc_scan.py", "scan_modul"),
    ("kor_openplc_r3.py", "r3_modul"),
    ("kor_openplc_opcua.py", "opcua_modul"),
    ("kor_openplc_hang.py", "hang_modul"),
])
def test_bench4_bankpost_deklaration(skriptnamn, modul_fixtur, request):
    """Alla protokollskriptens BANKPOST måste uppfylla BENCH-4-kraven."""
    mod = request.getfixturevalue(modul_fixtur)
    assert hasattr(mod, "BANKPOST"), "%s saknar BANKPOST" % skriptnamn
    post = mod.BANKPOST

    fel = _validera_bench4_post(post)
    assert fel == [], "BENCH-4-fel i %s: %s" % (skriptnamn, "; ".join(fel))

    # Specifika assertions enligt uppdragskrav:
    assert len(post["under_prov"]) > 0, "%s: under_prov är tom" % skriptnamn
    assert post["facitkalla_filer"] == (), "%s: facitkalla_filer != ()" % skriptnamn
    snitt = set(post["facitkalla_filer"]) & set(post["under_prov"])
    assert snitt == set(), "%s: facitkalla_filer överlappar under_prov" % skriptnamn


def test_trasig_fixtur_bench4_tautologiskt_facit_falls():
    """Trasig fixtur: facitkälla som pekar inuti under_prov fälls av BENCH-4."""
    tautologisk_post = {
        "pastar": "Ett cirkulärt påstående",
        "under_prov": ("svc/vc_assist_svc/st/",),
        "facit": "Internt facit",
        "facitkalla": "Egen fil",
        "facitkalla_filer": ("svc/vc_assist_svc/st/validera.py",),
        "trasiga_fall": ("ett trasigt fall",),
    }
    fel = _validera_bench4_post(tautologisk_post)
    assert any("BENCH-4" in f for f in fel), "BENCH-4 fångade inte tautologisk deklaration"


def test_trasig_fixtur_bench4_tom_under_prov_falls():
    """Trasig fixtur: tom under_prov fälls."""
    tom_post = {
        "pastar": "Inget under prov",
        "under_prov": (),
        "facit": "Något",
        "facitkalla": "Någon",
        "facitkalla_filer": (),
        "trasiga_fall": ("ett trasigt fall",),
    }
    fel = _validera_bench4_post(tom_post)
    assert any("under_prov" in f for f in fel)


# ---- 4. Svepets kontrakt -------------------------------------------------

def test_svepets_fall_har_exakt_247_poster(svep_facit):
    """Svepet har ett kontrakt på exakt 247 fall."""
    fall = svep_facit["FALL"]
    assert len(fall) == 247, "Förväntade 247 svepfall, hittade %d" % len(fall)


def test_svepets_fall_har_unika_namn(svep_facit):
    """Varje fall i svepet måste ha ett unikt namn."""
    fall = svep_facit["FALL"]
    namn = [f[0] for f in fall]
    unika = set(namn)
    assert len(unika) == 247, "Dubblerade namn i svepet: %d unika av %d totalt" % (
        len(unika), len(namn)
    )


def test_svepets_alla_poster_ar_giltiga_femtupler(svep_facit):
    """Varje post i FALL ska vara en 5-tupel (namn, grupp, kropp, dekl, prolog)."""
    for post in svep_facit["FALL"]:
        assert len(post) == 5, "Posten har fel längd: %r" % (post,)
        namn, grupp, _kropp, _dekl, _prolog = post
        assert isinstance(namn, str) and namn.strip() != "", "Ogiltigt namn: %r" % namn
        assert isinstance(grupp, str) and grupp.strip() != "", "Ogiltig grupp: %r" % grupp


def test_svepets_facittabeller_pekar_pa_existerande_fall(svep_facit):
    """Alla namn i STRANGARE och LATTARE måste referera till ett existerande fall i FALL."""
    alla_namn = set(f[0] for f in svep_facit["FALL"])
    for n in svep_facit["STRANGARE"]:
        assert n in alla_namn, "STRANGARE innehåller föräldralöst fall: %s" % n
    for n in svep_facit["LATTARE"]:
        assert n in alla_namn, "LATTARE innehåller föräldralöst fall: %s" % n
