# -*- coding: utf-8 -*-
"""L1 for fas 11: den klassiska baslinjen, och de tva satten den kan ljuga pa.

Baslinjen finns for att fas 9:s tal aldrig far publiceras ensamt
(`docs/spec/70_faser.md`, fas 11). Talen star i
`docs/matningar/M-62_baslinjen.md`. Det har provet ar grinden runt dem.

TRASIGA FIXTURER, och varfor just de tva ar de som betyder nagot:

1. **En baslinje som far ratt av fel skal.** `baslinjebank.nollprogram` styr
   ingenting alls: varje utgang skrivs till sitt nollvarde en gang. Den gar
   igenom grind 2 OCH grind 3 utan en enda anmarkning, och den uppfyller en
   stor del av spårfacits punktkrav — darfor att manga av dem ar negativa
   ("bandet ska sta", "ingenting far vara kommenderat"). Domaren MASTE falla
   den. Gor den inte det ar varje pastaendetal i M-62 meningslost, for da
   mater det hur manga krav som rakar vara negativa.

2. **Tva sidor domda av OLIKA domare.** `par.para` maste avvisa dem. En
   jamforelse mellan tva domare mater domaren och inte de tva sidorna, och det
   ar precis den incident hela grinddoktrinen vilar pa: en omimplementerad
   positionsdom underkande 2 av 4 medan ogat visade 4 av 4.

Bada riktningarna provas overallt. En grind som bara provas i den fallande
riktningen mater sin egen benagenhet att neka.

beskriver: svc/vc_assist_svc/plc/baslinje/, bank/baslinjebank.py, bank/par.py
"""
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import baslinjebank as B                                     # noqa: E402
import par as Par                                            # noqa: E402
import reparationsbank as RB                                 # noqa: E402
from vc_assist_svc.plc import reparation as R                # noqa: E402
from vc_assist_svc.plc.baslinje import (ATGARDER, Baslinje,  # noqa: E402
                                        Baslinjefel, BaslinjeModell,
                                        NIVA_MAGER, NIVA_PROSA, NIVA_SPEC,
                                        Spec, morfologi as Mo, packml as Pm,
                                        sprak as Sp)
from vc_assist_svc.plc.skelett import Skelett                # noqa: E402
from vc_assist_svc.plc.stationsgrind import (NAMN_DEKLARATION,  # noqa: E402
                                             NAMN_STATISK, Kandidat,
                                             granska_station)

_PAKET = os.path.join(_ROT, "svc", "vc_assist_svc", "plc", "baslinje")


@pytest.fixture(scope="module")
def poster():
    return B.las_uppgifter()


@pytest.fixture(scope="module")
def facitposter(poster):
    return B.med_sparfacit(poster)


def _post(poster, tid):
    for p in poster:
        if p["task_id"] == tid:
            return p
    raise AssertionError("ingen uppgift %s" % tid)


# ====================================================================== 1
# Morfologin: vad en tagg betyder, last ur namnet och riktningen.

def _karta(rader):
    return Mo.Karta(Mo.klassa(rader))


def _sig(namn, riktning, typ="bool", kommentar=""):
    return {"name": namn, "dir": riktning, "type": typ, "comment": kommentar}


@pytest.mark.parametrize("kommando,kvittens", [
    ("ST010_CLP_CLOSE", "ST010_CLP_CLOSED"),
    ("ST010_STP_OPEN", "ST010_STP_OPENED"),
    ("ST010_RB_START", "ST010_RB_DONE"),
    ("ST010_VAC_ON", "ST010_VAC_OK"),
    ("ST010_LFT_UP", "ST010_LFT_TOP"),
    ("ST010_LFT_DOWN", "ST010_LFT_BOT"),
    ("ST010_PSH_OUT", "ST010_PSH_HOME"),
    ("ST010_TCH_LOCK", "ST010_TCH_LOCKED"),
    ("ST010_HSK_REQ", "ST010_HSK_ACK"),
    ("ST010_CAM_TRIG", "ST010_CAM_FOUND"),
])
def test_morfologin_parar_kommando_med_sin_kvittens(kommando, kvittens):
    k = _karta([_sig(kommando, "out"), _sig(kvittens, "in")])
    assert k.get(kommando).roll == Mo.ROLL_KOMMANDO
    assert k.get(kommando).par == kvittens
    assert k.get(kvittens).roll == Mo.ROLL_BEKRAFTELSE


def test_en_ingang_blir_aldrig_ett_kommando():
    """`ST120_MLD_OPEN` ar formsprutverktygets LAGE, inte en order att oppna.

    Riktningen avgor alltid. En morfologi som gick pa ordet hade kommenderat
    en givare, och grind 3 hade fallt den som SKRIVEN_INGANG langt senare.
    """
    k = _karta([_sig("ST120_MLD_OPEN", "in")])
    assert k.get("ST120_MLD_OPEN").roll == Mo.ROLL_GIVARE
    assert not k.kommandon()


def test_en_utgang_utan_kvittens_blir_status_inte_kommando():
    k = _karta([_sig("ST040_BUF_FULL", "out")])
    assert k.get("ST040_BUF_FULL").roll == Mo.ROLL_STATUS


def test_en_transportor_ar_en_driftutgang():
    k = _karta([_sig("ST010_CNV_RUN", "out")])
    assert k.get("ST010_CNV_RUN").roll == Mo.ROLL_DRIFTUTGANG


def test_kvittensen_soks_bara_pa_samma_don():
    """`ST010_CLP_CLOSE` far inte paras med `ST010_GRP_CLOSED`."""
    k = _karta([_sig("ST010_CLP_CLOSE", "out"), _sig("ST010_GRP_CLOSED", "in")])
    assert k.get("ST010_CLP_CLOSE").par is None


def test_stationsnamnet_kommer_ur_taggarna_inte_ur_uppgiftsnumret(poster):
    k = _karta(_post(poster, "T-07")["control"]["signals"])
    assert k.station() == "ST050"


def test_systemsignalerna_kanns_igen_vid_namn():
    k = _karta([_sig(n, "in") for n in
                (Mo.NODSTOPP, Mo.LUFT, Mo.AUTOLAGE, Mo.KVITTENS)]
               + [_sig(Mo.LARM, "out")])
    assert all(t.roll == Mo.ROLL_SYSTEM for t in k.taggar)


# ====================================================================== 2
# Det kontrollerade spraket.

KANDA = {"A_OK", "B_OK", "C_OK", "ST260_LAY_CNT", "ST260_PRT_PRS",
         "ST310_RB_START", "ST320_RB_START", "UT1", "UT2"}


def test_uppraknat_villkor_arver_predikatet_som_star_sist():
    v = Sp.las_villkor("A_OK, B_OK och C_OK ar hoga", KANDA)
    assert [t.signal for t in v.termer] == ["A_OK", "B_OK", "C_OK"]
    assert all(t.sant for t in v.termer)


def test_ett_negerande_ord_efter_signalerna_negerar_dem_inte():
    """Matt fel under bygget: raden slutar med "och inget larm star", och varje
    term blev NOT. Predikatet arvs fran den sista bit som bar en SIGNAL."""
    v = Sp.las_villkor("A_OK, B_OK och C_OK ar hoga och inget larm star", KANDA)
    assert all(t.sant for t in v.termer), [str(t) for t in v.termer]


def test_ett_tal_ur_ett_taggnamn_blir_aldrig_ett_gransvarde():
    """Matt fel under bygget: `ST260_LAY_CNT ar under 5` gav jamforelsen
    `< 260`, darfor att 260 satt i stationsprefixet."""
    v = Sp.las_villkor("ST260_PRT_PRS ar hog och ST260_LAY_CNT ar under 5",
                       KANDA)
    jam = [t for t in v.termer if t.jamforelse]
    assert len(jam) == 1
    assert jam[0].signal == "ST260_LAY_CNT"
    assert (jam[0].jamforelse, jam[0].varde) == ("<", 5.0)


def test_satt_till_ett_tal_tar_aldrig_talet_ur_ett_taggnamn():
    """Matt fel under bygget: "for kartan till ST440" gav vardet 440.

    Samma fella som gransvardet, i den andra riktningen: ett tal som plockas ur
    ett namn ar inget varde, och en generator som skriver 440 till en raknare
    for att stationen heter ST440 ser ut att fungera tills stationen byter
    nummer.
    """
    kanda = KANDA | {"ST160_LYR_NO", "ST440_RWK_CNT"}
    h = Sp.las_handlingar("satt ST160_LYR_NO till 1", kanda)
    assert [(x.sort, x.signal, x.varde) for x in h] == [
        (Sp.SATTVARDE, "ST160_LYR_NO", 1.0)]
    h = Sp.las_handlingar("satt UT1 hog och for kartan till ST440_RWK_CNT",
                          kanda)
    assert Sp.Handling(Sp.SATT, "UT1", True) in h, (
        "handlingen tappades helt; en tappad handling ar en tyst forlust")
    assert not [x for x in h if x.sort == Sp.SATTVARDE], (
        "440 ur taggnamnet ST440_RWK_CNT blev ett varde: %r" % (h,))


def test_raekneord_lases_som_tal():
    """"ar fyra" ar lika vanligt som "ar 4" i banken. En lasare som bara ser
    siffror tappar villkoret TYST, och det ar varre an att inte lasa raden."""
    v = Sp.las_villkor("ST260_LAY_CNT ar fyra", KANDA)
    jam = [t for t in v.termer if t.jamforelse]
    assert jam and (jam[0].jamforelse, jam[0].varde) == ("=", 4.0)


def test_ett_avslutande_verb_stoppar_det_foregaende():
    """Matt fel under bygget: "pulsa X och las Y" gjorde matsignalen Y till ett
    skrivmal, darfor att pulsens rackvidd strackte sig genom hela raden."""
    h = Sp.las_handlingar("pulsa UT1 och las A_OK", KANDA)
    assert [(x.sort, x.signal) for x in h] == [(Sp.PULS, "UT1")]


def test_en_puls_tas_ner_i_nasta_steg():
    """En kamera som triggas pa NIVA tar en bild per scan."""
    signaler = [_sig("ST010_PRT_PRS", "in"), _sig("ST010_CAM_TRIG", "out"),
                _sig("ST010_CAM_FOUND", "in")]
    spec = Spec(tuple(signaler),
                ("vid ST010_PRT_PRS: pulsa ST010_CAM_TRIG",
                 "vanta pa ST010_CAM_FOUND"), (), "")
    kropp = Baslinje().generera(spec).kropp
    assert "ST010_CAM_TRIG := TRUE;" in kropp
    assert "ST010_CAM_TRIG := FALSE;" in kropp


def test_vantan_i_satt_och_vanta_hamnar_pa_nasta_steg():
    """"satt X hog och vanta pa Y" ar X nu och Y som nasta stegs villkor. En
    kommandokedja som inte vantar pa sina kvittenser ar precis den
    driftsattningsmiss banken finns for att hitta."""
    kanda = {"ST010_VAC_ON", "ST010_VAC_OK", "ST010_RB_START"}
    d = Sp.las(["satt ST010_VAC_ON hog och vanta pa ST010_VAC_OK",
                "satt ST010_RB_START hog"], [], kanda).direktiv
    assert len(d) == 2
    assert [h.signal for h in d[0].handlingar] == ["ST010_VAC_ON"]
    assert [t.signal for t in d[1].villkor.termer] == ["ST010_VAC_OK"]


def test_ett_brytord_avslutar_verbets_rackvidd():
    """"satt X hog, aldrig samtidigt med Y" ar en order till X och ett FORBUD
    mot Y. Utan brytordet startades bada."""
    h = Sp.las_handlingar(
        "satt ST320_RB_START hog, aldrig samtidigt med ST310_RB_START", KANDA)
    assert [(x.signal, x.varde) for x in h] == [("ST320_RB_START", True)]


def test_nollstall_tar_alla_signaler_fram_till_nasta_verb():
    h = Sp.las_handlingar("nollstall UT1 och UT2 och satt A_OK hog", KANDA)
    assert [(x.signal, x.varde) for x in h] == [
        ("UT1", False), ("UT2", False), ("A_OK", True)]


def test_en_rad_som_inte_gar_att_lasa_RAKNAS():
    """En parser som tyst hoppar over det den inte forstar ser ut att forsta
    allt. Da mater banken parserns tystnad."""
    lasning = Sp.las(["for skiftregistret framat med UT1, inte med tiden"],
                     [], KANDA)
    assert lasning.direktiv == []
    assert len(lasning.olasta) == 1


def test_en_lasbar_rad_hamnar_inte_bland_de_olasta():
    lasning = Sp.las(["vid A_OK: satt UT1 hog"], [], KANDA)
    assert lasning.olasta == []
    assert len(lasning.direktiv) == 1


def test_vid_och_nar_ar_samma_sats():
    a = Sp.las(["vid A_OK: satt UT1 hog"], [], KANDA).direktiv
    b = Sp.las(["Nar A_OK: satt UT1 hog"], [], KANDA).direktiv
    assert str(a[0]) == str(b[0])


def test_gransvarde_ur_uppgiftstexten_binds_till_sin_matsignal(poster):
    post = _post(poster, "T-07")
    kanda = set(s["name"] for s in post["control"]["signals"])
    iv = Sp.las_intervall(post["prompt"], kanda, ["ST050_IDX_POS"])
    assert [(x.signal, x.lag, x.hog) for x in iv] == [
        ("ST050_IDX_POS", 0.0, 300.0)]


def test_gransvardets_villkor_lases_med(poster):
    post = _post(poster, "H-04")
    kanda = set(s["name"] for s in post["control"]["signals"])
    iv = Sp.las_intervall(post["prompt"], kanda, ["ST320_GRP_FRC"])
    assert iv and iv[0].nar == "ST320_GRP_CLOSED"


def test_ett_tal_i_en_mening_utan_matsignal_blir_inget_intervall():
    """Takttider och antal star ocksa i prompten. Bara matsignaler far ett
    arbetsomrade."""
    iv = Sp.las_intervall("Takttiden ar mellan 5 och 9 s per detalj.",
                          KANDA, [])
    assert iv == []


# ====================================================================== 3
# Generatorn: determinism, och att den aldrig ser facit.

def _spec(post):
    return B.spec_ur_uppgift(post)


@pytest.mark.parametrize("niva", [NIVA_MAGER, NIVA_PROSA, NIVA_SPEC])
def test_samma_spec_ger_byte_identisk_kod(poster, niva):
    """Ingen modell, ingen slump. Star det inte har gar tva korningar av
    banken inte att jamfora med varandra heller."""
    spec = _spec(_post(poster, "T-07"))
    a = Baslinje(niva=niva).generera(spec)
    b = Baslinje(niva=niva).generera(spec)
    assert a.kropp == b.kropp
    assert a.deklarationer == b.deklarationer


class _Fallpost(dict):
    """En uppgift som SKRIKER om nagon ror facit."""

    def __getitem__(self, nyckel):
        if nyckel == "facit_spar":
            raise AssertionError("baslinjen last facit_spar")
        return dict.__getitem__(self, nyckel)

    def get(self, nyckel, standard=None):
        if nyckel == "facit_spar":
            raise AssertionError("baslinjen last facit_spar")
        return dict.get(self, nyckel, standard)


def test_baslinjen_ror_aldrig_facit(poster):
    """Trasig fixtur for regeln sjalv: posten kastar om facit lases."""
    post = _Fallpost(_post(poster, "T-07"))
    resultat = Baslinje().generera(B.spec_ur_uppgift(post))
    assert resultat.kropp
    with pytest.raises(AssertionError):
        post["facit_spar"]


def test_ett_utbytt_facit_ger_samma_kod(poster):
    post = dict(_post(poster, "T-07"))
    forst = Baslinje().generera(B.spec_ur_uppgift(post)).kropp
    post["facit_spar"] = {"skrap": True}
    assert Baslinje().generera(B.spec_ur_uppgift(post)).kropp == forst


def test_ingen_uppgifts_id_finns_i_baslinjens_kalla(poster):
    """En generator som kanner igen uppgiften mater ingenting.

    Dispatchen far ske pa signalform (PackML) och pa den kontrollerade
    grammatiken, aldrig pa uppgiftens nummer.
    """
    ider = sorted(p["task_id"] for p in poster)
    traffar = []
    for rot, mappar, filer in os.walk(_PAKET):
        mappar[:] = [m for m in mappar if m != "__pycache__"]
        for f in sorted(filer):
            if not f.endswith(".py"):
                continue
            text = open(os.path.join(rot, f), encoding="utf-8").read()
            for tid in ider:
                if re.search(r"\b%s\b" % re.escape(tid), text):
                    traffar.append("%s -> %s" % (f, tid))
    assert not traffar, "uppgifts-id i generatorns kalla: %s" % traffar


def test_okand_niva_avvisas():
    with pytest.raises(Baslinjefel):
        Baslinje(niva="gissa")


def test_packml_valjs_pa_signalformen_inte_pa_uppgiften(poster):
    """Mallen far bara utlosas av att kartan BAR en PackML-station."""
    packml = _karta(_post(poster, "S-05")["control"]["signals"])
    assert Pm.ar_packml(packml)
    utan = _karta(_post(poster, "T-07")["control"]["signals"])
    assert not Pm.ar_packml(utan)


def test_packml_matrisen_foljer_standarden():
    """Tre regler ur ISA-TR88.00.02 som en genvag alltid bryter mot."""
    giltiga_abort, mal_abort = Pm.KOMMANDON[Pm.CMD_ABORT]
    assert mal_abort == Pm.ABORTING and mal_abort != Pm.STOPPED
    assert len(giltiga_abort) == 15
    assert Pm.KOMMANDON[Pm.CMD_CLEAR] == ((Pm.ABORTED,), Pm.CLEARING)
    assert Pm.ABORTED not in Pm.KOMMANDON[Pm.CMD_RESET][0]
    assert Pm.ABORTED not in Pm.KOMMANDON[Pm.CMD_STOP][0]
    assert Pm.KOMMANDON[Pm.CMD_HOLD][1] != Pm.KOMMANDON[Pm.CMD_SUSPEND][1]


def test_en_heltalssignal_som_boolesk_term_stryker_direktivet(poster):
    """Fail-closed. Ett svagare villkor som anda kompilerar ar en falsk gron:
    koden ser fardig ut och kommenderar utan sin sparr."""
    signaler = [_sig("ST010_PRT_PRS", "in"), _sig("ST010_CNT", "in", "int"),
                _sig("ST010_RB_START", "out"), _sig("ST010_RB_DONE", "in")]
    spec = Spec(tuple(signaler),
                ("vid ST010_PRT_PRS och ST010_CNT: satt ST010_RB_START hog",),
                (), "")
    resultat = Baslinje().generera(spec)
    assert "ST010_CNT" not in resultat.kropp.replace("ST010_CNT <>", "")
    assert len(resultat.rapport.olasta_rader) == 1


def test_en_skrivning_till_en_insignal_stryker_direktivet():
    signaler = [_sig("ST010_PRT_PRS", "in"), _sig("ST010_RB_START", "out"),
                _sig("ST010_RB_DONE", "in")]
    spec = Spec(tuple(signaler),
                ("vid ST010_RB_DONE: nollstall ST010_PRT_PRS",), (), "")
    resultat = Baslinje().generera(spec)
    assert "ST010_PRT_PRS := " not in resultat.kropp
    assert len(resultat.rapport.olasta_rader) == 1


def test_generatorn_redovisar_sina_obundna_utgangar():
    signaler = [_sig("ST010_PRT_PRS", "in"), _sig("ST010_STA_DONE", "out")]
    resultat = Baslinje().generera(Spec(tuple(signaler), (), (), ""))
    assert "ST010_STA_DONE" in resultat.rapport.obundna_utgangar


def test_vaxlarna_ar_av_som_standard_och_syns_nar_de_ar_pa():
    """Att driva en utgang till FALSE for att klara grind 3 ar
    grindtillfredsstallelse och inte styrning. Den ska ga att sla pa, och den
    ska synas nar den ar pa."""
    signaler = [_sig("ST010_PRT_PRS", "in"), _sig("ST010_STA_DONE", "out")]
    spec = Spec(tuple(signaler), (), (), "")
    av = Baslinje().generera(spec)
    pa = Baslinje(driv_obundna=True, las_obundna=True).generera(spec)
    assert "ST010_STA_DONE" not in av.kropp
    assert "ST010_STA_DONE := FALSE;" in pa.kropp
    assert "ST010_PRT_PRS" in pa.kropp


def test_ordningen_i_specen_bar_resultatet(poster):
    """Kontroll mot att standardramen ensam gor jobbet.

    Vands sekvensen bak och fram ska koden BLI en annan och domen falla. Gor
    den inte det ar "4 av 4" ett tal om ramen och inte om lasningen, och da
    mater ablationen i M-62 ingenting.
    """
    post = _post(poster, "T-07")
    hel = B.kor_ablation(post, "hel spec")
    omvand = B.kor_ablation(post, "omvand sekvens")
    assert hel.godkand
    assert not omvand.godkand
    assert omvand.uppfyllda < hel.uppfyllda


def test_ramen_ensam_racker_inte(poster):
    post = _post(poster, "T-07")
    assert not B.kor_ablation(post, "ramen ensam").godkand


def test_en_okand_ablation_avvisas():
    with pytest.raises(ValueError):
        B.ablera(Spec(()), "hitta pa")


# ====================================================================== 4
# TRASIG FIXTUR 1: en baslinje som far ratt av fel skal.

def test_nollprogrammet_gar_igenom_bada_formgrindarna(facitposter):
    """Golvet kompilerar och matchar kartan. En kompileringsgrad mater alltsa
    inte om koden styr nagonting - det ar hela R-01:s poang, mekaniserad."""
    for post in facitposter:
        st_kalla, karta = B.nollprogram(post)
        dom = granska_station(Kandidat(karta.station, st_kalla), karta,
                              stanna_vid_forsta=False)
        assert dom.forgrindar[NAMN_STATISK] is True, post["task_id"]
        assert dom.forgrindar[NAMN_DEKLARATION] is True, post["task_id"]


def test_domaren_faller_nollprogrammet(facitposter):
    """Den viktigaste raden i hela provet."""
    for post in facitposter:
        st_kalla, _karta = B.nollprogram(post)
        utfall = B.spardom(post, st_kalla)
        assert not utfall.godkand, (
            "%s: ett program som styr ingenting slapptes igenom av domaren"
            % post["task_id"])


def test_nollprogrammet_uppfyller_anda_manga_pastaenden(facitposter):
    """Och darfor far ett pastaendetal aldrig publiceras utan sitt golv.

    Manga punktkrav ar negativa - "bandet ska sta", "ingenting far vara
    kommenderat" - och ett program som aldrig kommenderar nagot uppfyller dem
    alla. Utan den har raden ser 79 % ut som en prestation.
    """
    uppfyllda = 0
    totalt = 0
    for post in facitposter:
        st_kalla, _karta = B.nollprogram(post)
        utfall = B.spardom(post, st_kalla)
        uppfyllda += utfall.uppfyllda
        totalt += utfall.totalt.totalt
    assert totalt > 0
    assert uppfyllda > totalt // 4, (
        "golvet ar %d av %d; ar det lagt ar den har fixturen inte langre "
        "'ratt av fel skal'" % (uppfyllda, totalt))


def test_baslinjen_ligger_over_golvet(facitposter):
    """Kontrollriktningen. En baslinje som inte slar sitt eget golv mater
    ingenting."""
    baslinje = Baslinje(niva=NIVA_SPEC)
    for post in facitposter:
        golv = B.spardom(post, B.nollprogram(post)[0])
        bygge = B.bygg(post, baslinje)
        min_ = B.spardom(post, bygge.st_kalla)
        assert min_.uppfyllda > golv.uppfyllda, post["task_id"]


def test_pastaendeskalan_skiljer_inte_pa_farligt_och_riktigt(facitposter):
    """Den obekvamaste raden i M-62, mekaniserad.

    De arton motbevisen ar vart och ett ett verkligt driftsattningsfel - en
    station som startar av sig sjalv nar nagon drar upp nodstoppsdonet, en
    handkorning som latchas. Pa pastaendeskalan far de over 90 %. Ett
    procenttal ur en pastaenderakning far darfor ALDRIG bli banken huvudtal;
    bara den binara domen per uppgift skiljer dem at.
    """
    u = t = 0
    for tid, vad, godkand, uppfyllda, totalt in B.kalibrering(facitposter):
        if not vad.startswith("motbevis "):
            continue
        assert not godkand, "%s %s slapptes igenom" % (tid, vad)
        u += uppfyllda
        t += totalt
    assert t > 0
    assert u > t * 9 // 10, (
        "motbevisen uppfyller %d av %d pastaenden; ar den kvoten LAG ar den "
        "har varningen inte langre sann och texten i M-62 maste skrivas om"
        % (u, t))


# ====================================================================== 5
# TRASIG FIXTUR 2: tva sidor domda av OLIKA domare.

@pytest.fixture(scope="module")
def signatur(facitposter):
    return Par.signatur(facitposter, B.GRINDAR_UTAN_KOMPILATOR)


def _sida(namn, signatur, utfall=None):
    return Par.Sida(namn, signatur, utfall or {"T-07": True, "H-04": False})


def test_tva_sidor_med_samma_domare_gar_att_para(signatur):
    rapport = Par.para(_sida("var", signatur), _sida("baslinje", signatur))
    assert "T-07" in rapport.text()
    assert "1 av 2" in rapport.text()


@pytest.mark.parametrize("falt,varde", [
    ("scan_ms", 50.0),
    ("marginal_scan", 1),
    ("grindar", ("statisk_analys",)),
    ("kallor", "en annan domarkedja"),
    ("facit", "ett annat facit"),
    ("uppgifter", ("T-07",)),
])
def test_olika_domare_avvisas(signatur, falt, varde):
    """Hela poangen med fas 11. En jamforelse mellan tva domare mater
    domaren, inte de tva sidorna."""
    import dataclasses
    annan = dataclasses.replace(signatur, **{falt: varde})
    with pytest.raises(Par.Parfel) as fel:
        Par.para(_sida("var", signatur), _sida("baslinje", annan))
    assert falt in str(fel.value)


def test_en_sida_utan_utfall_ar_ingen_sida(signatur):
    with pytest.raises(Par.Parfel):
        Par.para(_sida("var", signatur), Par.Sida("tom", signatur, {}))


def test_domarsignaturen_andras_nar_domarkedjans_kalla_andras():
    """Signaturen ar en hash over domarkedjan. Andras tolken ar det en annan
    domare, och ett tal fran i gar gar inte att para med ett fran i dag."""
    a = Par.kallhash()
    b = Par.kallhash(Par.DOMARKALLOR[:-1])
    assert a != b
    assert Par.kallhash() == a


def test_domarkallorna_finns_allihop():
    for rel in Par.DOMARKALLOR:
        assert os.path.exists(os.path.join(_ROT, rel)), rel


# ====================================================================== 6
# Ytan mot reparationsslingan: SAMMA slinga, SAMMA grindar.

def test_baslinjen_kors_av_den_riktiga_slingan(poster):
    post = _post(poster, "T-07")
    protokoll, modell = B.kor_slinga(post, NIVA_SPEC)
    assert protokoll.utfall == R.UTFALL_LOST
    assert protokoll.varv_till_lost == 1
    assert modell.leverantor == "baslinje"


def test_en_deterministisk_generator_utan_regel_laser_slingan(poster):
    """Ett eget utfall, och ett arligt. Baslinjen kan inte reparera ett
    logikfel genom att forsoka igen: andra varvet ger samma kropp."""
    post = _post(poster, "T-07")
    protokoll, modell = B.kor_slinga(post, NIVA_MAGER)
    assert protokoll.utfall == R.UTFALL_LAST
    assert modell.utan_regel, ("baslinjen borde ha rapporterat minst en kod "
                              "den inte har nagon regel for")


def test_slingan_kan_inte_skilja_baslinjen_fran_en_annan_modell(poster):
    """Hela poangen med fas 11:s leveransform.

    SAMMA slingobjekt och SAMMA grindsteg kors med en attrappmodell och med
    baslinjen. Skiljer slingan pa dem mater ett par inte de tva sidorna utan
    vilken vag genom slingan de tog.
    """
    from vc_assist_svc.harness.modell import AttrappModell, Modell, sag

    post = _post(poster, "T-07")
    spec = B.spec_ur_uppgift(post)
    baslinje = BaslinjeModell(spec)
    resultat = baslinje.generator().generera(spec)
    karta = RB.karta_ur_uppgift(post, resultat.station)
    skelett = Skelett.av_karta(karta, resultat.deklarationer)
    grindar = [R.Stationssteg(karta), RB.Sparfacitsteg(post)]
    slinga = R.Reparationsslinga(skelett, grindar)
    uppgiftstext = RB.uppgiftstext(post, skelett)

    assert isinstance(baslinje, Modell)
    a = slinga.kor(AttrappModell([sag(resultat.kropp)]), uppgiftstext,
                   uppgift="T-07")
    b = slinga.kor(BaslinjeModell(spec), uppgiftstext, uppgift="T-07")
    assert a.utfall == b.utfall == R.UTFALL_LOST
    assert a.varv[0].st_kalla == b.varv[0].st_kalla


def test_baslinjen_har_ingen_kanal_ut(poster):
    """Den kan inte na natet, och det ska ga att se utan att lita pa en
    docstring: den bar en spec och en generator, ingenting annat."""
    modell = BaslinjeModell(B.spec_ur_uppgift(_post(poster, "T-07")))
    misstankta = [n for n in vars(modell)
                  if any(o in n.lower()
                         for o in ("socket", "url", "kanal", "http", "klient",
                                   "nyckel", "token"))]
    assert not misstankta, misstankta


def test_atgardstabellen_slar_pa_ratt_installning(poster):
    modell = BaslinjeModell(B.spec_ur_uppgift(_post(poster, "T-07")))
    assert not modell._val["las_obundna"]
    modell._atgarda("rad 9: [ORORD_SIGNAL/F3] SYS_RESET rors aldrig av koden")
    assert modell._val["las_obundna"]
    assert "ORORD_SIGNAL" in modell.atgardade


def test_en_kod_utan_regel_hamnar_i_listan_i_stallet_for_att_forsvinna(poster):
    modell = BaslinjeModell(B.spec_ur_uppgift(_post(poster, "T-07")))
    modell._atgarda("  [invariant:inget_index_utan_klamma@sekv/F8] nagot")
    assert modell.utan_regel == ["invariant:inget_index_utan_klamma@sekv"]
    assert not modell.atgardade


def test_atgardstabellen_tacker_bara_formgrindarnas_koder():
    """Regeln ar mekanisk: en atgard far bara finnas dar grinden pekar ut en
    FORM. En dom som sager "ST050_CNV_RUN var 1 vid 1800 ms" pekar inte ut
    nagon rad att andra, och da finns ingen regel."""
    assert set(ATGARDER) == {"ORORD_SIGNAL", "ODRIVEN_UTGANG"}


# ====================================================================== 7
# Rakningen: nämnaren maste stamma med M-45:s egen.

def test_pastaenderakningen_stammer_med_M45(facitposter):
    punkt = sum(B.pastaenden(p).punktkrav for p in facitposter)
    namn = sum(B.pastaenden(p).invariantnamn for p in facitposter)
    flank = sum(B.pastaenden(p).flanker for p in facitposter)
    assert (punkt, namn, flank) == (190, 18, 10)


def test_ett_tolkfel_raknas_som_noll_uppfyllda(facitposter):
    """En orord grind ar aldrig ett godkannande (I3), och ett papstaende som
    aldrig provades far inte se ut som uppfyllt."""
    post = facitposter[0]
    utfall = B.spardom(post, "PROGRAM X\nVAR\nEND_VAR\nDET HAR AR INTE ST\n"
                             "END_PROGRAM\n")
    assert utfall.tolkfel
    assert utfall.uppfyllda == 0


def test_genereringsuppgifterna_ar_banken_utan_de_trasiga_varianterna(poster):
    gen = B.genereringsuppgifter(poster)
    assert len(gen) + len([p for p in poster if p.get("variant_av")]) == len(poster)
    assert all(not p.get("variant_av") for p in gen)
