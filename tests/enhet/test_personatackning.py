# -*- coding: utf-8 -*-
"""Personatackningen (fas 19): namnaren far inte krympa tyst.

En tackningssiffra ar den lattaste grinden att gora meningslos. Namnaren kan
krympa till "det vi klarar" utan att en enda rad blir rod, och talet stiger av
raderingen. Tre grindar natten 2026-09-04/05 matte redan nagot annat an de
pastod - en ST-tolk som avvisade `T#3S` fast IEC 61131-3 ar skiftlagesokansligt,
en skrivgrind som gick att kringga via ett mellanled, och en arlighetsgrind som
tystnade av vilket nekande ord som helst.

Provet nedan ar skrivet mot just den felklassen. `test_ett_borttaget_steg_...`
visar den i sin renaste form: samma spec med ETT steg struket ger en HOGRE
procentsats, och maste anda ge ett rott.

Kallor: docs/spec/48_personaprofiler.md, svc/vc_assist_svc/personatackning.py,
tests/protocol/kor_fas19_tackning.py, tests/protocol/fas19_personatackningen.md
"""
import importlib.util
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import personatackning as PT              # noqa: E402
from vc_assist_svc.verktyg import REGISTER                   # noqa: E402


def _korning():
    """Fas 19:s korning laddad som modul, sa dess trasiga fall provas har.

    Utan det har hade protokollet legat utanfor sviten, och en fixtur som
    slutade falla hade synts forst nasta gang nagon korde skriptet for hand.
    """
    sokvag = os.path.join(_ROT, "tests", "protocol", "kor_fas19_tackning.py")
    spec = importlib.util.spec_from_file_location("kor_fas19_tackning", sokvag)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture(scope="module")
def profiler():
    return PT.las_spec()


@pytest.fixture(scope="module")
def domare():
    return PT.Domare()


@pytest.fixture(scope="module")
def korning():
    return _korning()


# ==========================================================================
# 1. Specen sjalv
# ==========================================================================

def test_specen_bar_alla_kanda_profiler(profiler):
    koder = [p.kod for p in profiler]
    assert koder == sorted(koder), "profilerna star inte i ordning: %s" % koder
    for kod in PT.KANDA_PROFILER:
        assert kod in koder, "%s saknas i specen" % kod


def test_specen_domes_utan_fallning(profiler, domare):
    fel = domare.doma(profiler)
    assert not fel, "specen faller pa %d punkter:\n  %s" % (
        len(fel), "\n  ".join(str(f) for f in fel))


def test_golvet_ligger_pa_eller_under_det_matta_antalet(profiler):
    """Golvet far bara ga uppat. Ett golv OVER antalet vore en spec som redan
    faller; ett golv langt UNDER antalet ar ingen sparr alls."""
    per_kod = {p.kod: p.antal for p in profiler}
    assert set(PT.GOLV) == set(per_kod), (
        "GOLV och specen namnger olika profiler: %s mot %s"
        % (sorted(PT.GOLV), sorted(per_kod)))
    for kod, golv in sorted(PT.GOLV.items()):
        assert golv <= per_kod[kod], (
            "%s har %d steg men golvet ar %d" % (kod, per_kod[kod], golv))


def test_varje_steg_har_bade_krav_och_besked(profiler):
    for profil in profiler:
        for steg in profil.steg:
            assert steg.kraver, "%s saknar krav" % steg
            assert steg.tackt_av, "%s saknar besked om tackning" % steg
            assert steg.verkan in PT.VERKAN, "%s: verkan %r" % (steg, steg.verkan)


def test_talen_summerar_till_namnaren(profiler):
    """tackta + utanfor + obyggda MASTE bli alla steg.

    En raknare som inte summerar till helheten mater inte helheten - samma
    regel som domanindelningen i 47_verktygstackning.md redan star under.
    """
    for profil in profiler:
        t = PT.rakna(profil)
        assert t.tackta + t.utanfor + t.obyggda == t.steg == profil.antal


def test_obyggda_steg_ligger_kvar_i_namnaren(profiler):
    """Ett steg markt `saknas` raknas i namnaren men inte i taljaren."""
    obyggda = [s for p in profiler for s in p.steg
               if PT.OBYGGT in s.tackt_av]
    assert obyggda, "specen har inga obyggda steg alls - det ar osannolikt"
    for steg in obyggda:
        assert not steg.tackt
        assert not steg.utanfor_rackvidd


# ==========================================================================
# 2. Sparren mot en krympande namnare
# ==========================================================================

def _utan_ett_obyggt_steg(text, kod):
    """Klipper bort profilens SISTA obyggda steg och numrerar om resten.

    Tre val, och alla tre gor fixturen till just den frestelse den ska prova:
      * ett OBYGGT steg, for det ar det obekvama steget som drar ned talet
      * SISTA, sa att ingen mittrad lamnar ett hal
      * omnumrerad, sa att TRASIG_NUMRERING inte hinner falla forst
    Kvar star bara den tysta krympningen.
    """
    rader = text.splitlines(True)
    i_profilen = False
    sista = None
    for i, rad in enumerate(rader):
        if rad.startswith("## "):
            i_profilen = rad.startswith("## %s " % kod)
        elif i_profilen and PT._TABELLRAD.match(rad):
            if rad.rstrip().endswith("| %s |" % PT.OBYGGT):
                sista = i
    assert sista is not None, "hittade ingen obyggd tabellrad i %s" % kod
    del rader[sista]
    nummer = 0
    i_profilen = False
    for i, rad in enumerate(rader):
        if rad.startswith("## "):
            i_profilen = rad.startswith("## %s " % kod)
        elif i_profilen and PT._TABELLRAD.match(rad):
            nummer += 1
            rader[i] = PT._TABELLRAD.sub("| %d |" % nummer, rad, count=1)
    return "".join(rader)


def test_ett_borttaget_steg_ger_rott_trots_hogre_procent(domare):
    """FASENS KARNA.

    Samma spec med ETT obekvamt steg struket ger en HOGRE tackningssiffra.
    Provet raknar bada talen och kraver bade att siffran steg och att grinden
    anda blev rod. Utan sparren hade raderingen sett ut som framsteg.
    """
    with open(PT.SPEC, "r", encoding="utf-8") as f:
        text = f.read()
    fore = {p.kod: PT.rakna(p) for p in PT.las_profiler(text)}

    # Ett obyggt steg ur P6 - profilen med lagst tackning, alltsa den dar
    # frestelsen att stryka ar storst.
    kortare = _utan_ett_obyggt_steg(text, "P6")
    profiler = PT.las_profiler(kortare)
    efter = {p.kod: PT.rakna(p) for p in profiler}

    assert efter["P6"].steg == fore["P6"].steg - 1
    assert efter["P6"].andel_av_allt > fore["P6"].andel_av_allt, (
        "fixturen strok ett TACKT steg; den ska stryka ett obyggt sa att "
        "procentsatsen stiger")

    koder = [f.kod for f in domare.doma(profiler)]
    assert "NAMNAREN_KRYMPTE" in koder, (
        "P6 tappade ett steg och procentsatsen steg fran %.1f till %.1f - "
        "grinden sag det inte: %s"
        % (100 * fore["P6"].andel_av_allt, 100 * efter["P6"].andel_av_allt,
           koder))


def test_en_struken_profil_ger_rott(domare):
    with open(PT.SPEC, "r", encoding="utf-8") as f:
        text = f.read()
    utan_p5 = text.replace("## P5 —", "## Borttagen —")
    koder = [f.kod for f in domare.doma(PT.las_profiler(utan_p5))]
    assert "PROFIL_SAKNAS" in koder, koder


# ==========================================================================
# 3. De trasiga fallen, ur korningens egen lista
# ==========================================================================

def test_korningens_kontrollfixtur_ar_gron(korning):
    """Gar kontrollen inte igenom mater fixturerna domaren, inte specen."""
    assert korning.domare_pa_fixtur(korning._GRON) == []


def test_varje_trasigt_fall_faller_med_sin_egen_kod(korning, domare):
    riggad = PT.Domare(index=domare.index, register=REGISTER,
                       dotnet=domare.dotnet,
                       golv=korning._FIXTURGOLV,
                       kanda=korning._FIXTURPROFILER)
    utfall = korning.kor_trasiga(riggad)
    assert len(utfall) >= 14, "bara %d trasiga fall" % len(utfall)
    misslyckade = ["%s: vantade %s, fick %s" % (n, v, k)
                   for n, v, k, ok, _w in utfall if not ok]
    assert not misslyckade, "\n  ".join(misslyckade)


def test_varje_felkod_har_minst_en_fixtur(korning):
    """En felkod utan fixtur ar oprovad - och just den sortens kod ar det
    ingen som marker nar den slutar fyra."""
    vantade = set(v for _n, _t, v, _w in korning.TRASIGA)
    kallan = open(os.path.join(_ROT, "svc", "vc_assist_svc",
                               "personatackning.py"), encoding="utf-8").read()
    import re
    kodade = set(re.findall(r'Fel\("([A-Z_]+)"', kallan))
    utan = sorted(kodade - vantade)
    assert not utan, "felkoder utan trasig fixtur: %s" % utan


def test_olasbar_spec_avvisas_i_lasningen(korning):
    misslyckade = [n for n, b, ok, _w in korning.kor_olasbara() if not ok]
    assert not misslyckade, misslyckade


# ==========================================================================
# 4. Enskilda regler
# ==========================================================================

_MALL = """## P1 — Fixturen

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | %s
"""


def _doma(rad, domare, golv=None):
    profiler = PT.las_profiler(_MALL % rad)
    d = PT.Domare(index=domare.index, register=REGISTER, dotnet=domare.dotnet,
                  golv=golv or {}, kanda=("P1",))
    return [f.kod for f in d.doma(profiler)]


def test_lasande_verktyg_far_inte_tacka_ett_andrande_steg(domare):
    koder = _doma("ta bort | ändrar | `vcApplication.deleteComponent` "
                  "| `list_components` |", domare)
    assert koder == ["FEL_VERKAN"], koder


def test_skrivande_verktyg_far_tacka_ett_lasande_steg(domare):
    """measure_distance ar deklarerad write for att den bygger en detektor i
    scenen. Den ska anda fa tacka ett lasande steg - annars hade regeln matt
    verktygets bokforing i stallet for stegets verkan."""
    assert REGISTER["measure_distance"].effect == "write"
    koder = _doma("mata | läser | `vcNode.measureDistance` "
                  "| `measure_distance` |", domare)
    assert koder == [], koder


def test_ui_markor_pa_ett_skriptbart_namn_faller(domare):
    koder = _doma("ladda | ändrar | `UI:load` | UI |", domare)
    assert "FALSK_UTANFOR" in koder, koder


def test_ui_markorens_skiftlage_hjalper_inte(domare):
    """`UI:LOAD` ar samma namn som `load` for en manniska. En markor som staller
    sig utanfor rackvidd pa en skiftlagesskillnad ar precis den tysta vagen ut
    ur namnaren."""
    koder = _doma("ladda | ändrar | `UI:LOAD` | UI |", domare)
    assert "FALSK_UTANFOR" in koder, koder


def test_ui_markor_pa_ett_namn_som_inte_finns_slapper_igenom(domare):
    koder = _doma("bläddra | läser | `UI:eCatalog` | UI |", domare)
    assert koder == [], koder


def test_dotnet_namn_provas_mot_xml(domare):
    ok = _doma("koppla | ändrar | "
               "`.NET:VisualComponents.Connectivity.OpcUA.IOpcUAServer` "
               "| .NET |", domare)
    assert ok == [], ok
    fel = _doma("koppla | ändrar | "
                "`.NET:VisualComponents.Connectivity.OpcUA.IPlcServer` "
                "| .NET |", domare)
    assert "OKANT_DOTNET" in fel, fel


def test_tjanstekallan_maste_finnas_pa_disk(domare):
    assert _doma("söka | läser | `TJÄNST:katalogsok` | `search_catalog` |",
                 domare) == []
    assert "OKAND_TJANST" in _doma(
        "söka | läser | `TJÄNST:finns_inte` | `search_catalog` |", domare)


def test_ett_steg_kan_inte_vara_bade_tackt_och_utanfor(domare):
    koder = _doma("bläddra | läser | `UI:eCatalog` | `list_components`, UI |",
                  domare)
    assert "BADE_OCH" in koder, koder


def test_hal_i_numreringen_faller(domare):
    text = ("## P1 — Fixturen\n\n"
            "| # | Arbetssteg | Verkan | Kräver | Täckt av |\n"
            "|---|---|---|---|---|\n"
            "| 1 | a | läser | `vcApplication.Components` | `list_components` |\n"
            "| 3 | c | läser | `vcApplication.Components` | `list_components` |\n")
    d = PT.Domare(index=domare.index, register=REGISTER, dotnet=domare.dotnet,
                  golv={}, kanda=("P1",))
    koder = [f.kod for f in d.doma(PT.las_profiler(text))]
    assert "TRASIG_NUMRERING" in koder, koder


# ==========================================================================
# 5. Lasningen
# ==========================================================================

def test_tom_cell_ar_ett_specfel():
    with pytest.raises(PT.Specfel):
        PT.las_profiler(_MALL % "a | läser | `vcApplication.Components` |  |")


def test_fyra_kolumner_ar_ett_specfel():
    with pytest.raises(PT.Specfel):
        PT.las_profiler(_MALL % "a | `vcApplication.Components` | saknas |")


def test_markorer_plockas_aven_bredvid_ett_verktygsnamn():
    """Utan det har hade cellen "`x`, UI" tappat sin UI-markor tyst, och
    motsagelsen BADE_OCH hade aldrig kunnat falla."""
    assert PT._poster("`connect`, UI") == ("connect", "UI")
    assert PT._poster("saknas") == ("saknas",)
    assert PT._poster(".NET") == (".NET",)
    assert PT._poster("") == ()


def test_prefixen_kanns_igen_med_svenska_diakriter():
    assert PT._prefix("TJÄNST:katalogsok") == ("TJANST:", "katalogsok")
    assert PT._prefix("TJANST:katalogsok") == ("TJANST:", "katalogsok")
    assert PT._prefix("vcNode.attach") == ("", "vcNode.attach")


# ==========================================================================
# 6. Kallorna som domer
# ==========================================================================

def test_dotnet_indexet_ar_inte_tomt():
    namn = PT.dotnet_namn()
    assert len(namn) > 5000, len(namn)
    assert "VisualComponents.Create3D.ICADReader" in namn


def test_en_tunn_dotnetkalla_avvisas(tmp_path):
    """Ett tomt index godkanner varje pahittat .NET-namn. Det ar den falska
    gron grinden finns for, sa kallan far inte vara tunn."""
    (tmp_path / "tom.xml").write_text(
        "<doc><assembly><name>x</name></assembly><members/></doc>",
        encoding="utf-8")
    with pytest.raises(PT.Specfel):
        PT.dotnet_namn(str(tmp_path))
    with pytest.raises(PT.Specfel):
        PT.dotnet_namn(str(tmp_path / "finns_inte")) if (
            tmp_path / "finns_inte").exists() else PT.dotnet_namn(str(tmp_path))


# ==========================================================================
# 7. Byggd kapacitet ingen bad om
# ==========================================================================

def test_verktyg_ingen_profil_behover_ar_riktiga_verktyg(profiler):
    oanvanda = PT.verktyg_ingen_profil_behover(profiler, REGISTER)
    for namn in oanvanda:
        assert namn in REGISTER
    behovda = set()
    for profil in profiler:
        for steg in profil.steg:
            behovda.update(steg.verktyg)
    assert not (behovda & set(oanvanda))
    assert len(behovda) + len(oanvanda) == len(REGISTER)


def test_varje_namngivet_verktyg_finns_i_registret(profiler):
    for profil in profiler:
        for steg in profil.steg:
            for namn in steg.verktyg:
                assert namn in REGISTER, "%s pekar pa %s" % (steg, namn)


def test_varje_api_namn_finns_i_indexet(profiler, domare):
    saknade = [n for n in PT.api_namn(profiler) if not domare.index.finns(n)]
    assert not saknade, saknade
    assert len(PT.api_namn(profiler)) > 150, (
        "bara %d API-namn - profilerna ar for tunna for att mata en yta pa "
        "3444 symboler" % len(PT.api_namn(profiler)))
