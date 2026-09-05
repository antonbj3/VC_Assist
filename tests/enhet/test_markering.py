# -*- coding: utf-8 -*-
"""L1: markeringen som INDICIUM, och scenens sort ur strukturen.

De fem trasiga fixturerna ar skrivna FORE mekanismen och sedda roda. Var och
en beskriver ett satt att gora markeringen till en auktoritet, och det ar
precis vad den inte far vara:

  (a) markering som pekar ut tre kandidater och anda loser ut en
  (b) tom markering som tyst blir ett val
  (c) ett utlost namn utan belagg om att markeringen avgjorde
  (d) ett markeringsverktyg deklarerat med annan effect an read
  (e) markering av FEL SORT som anda loser ut   <- den viktigaste

(e) ar viktigast darfor att den ar det vanliga felet, inte det ovanliga:
operatoren har nagot annat markerat an det han talar om. En markering som
tas for facit gor da fel sak med full sjalvsakerhet, och det ar ett tyst fel.

NAIV_UPPLOSNING langre ned ar den implementation vi INTE byggde - "markeringen
vinner". Proven jamfor mekanismen mot den, sa att skillnaden mellan de tva ar
mekaniskt bevakad i stallet for beskriven i en kommentar.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import verktyg as V                       # noqa: E402
from vc_assist_svc.scenarbete import avsikt as A             # noqa: E402
from vc_assist_svc.scenarbete import markering as M          # noqa: E402
from vc_assist_svc.scenarbete import sparr                   # noqa: E402
from vc_assist_svc.verktyg import markering as VM            # noqa: E402


# ---- scenen proven arbetar mot -------------------------------------------
#
# Tre gripdon och en transportor. Namnen ar med flit BLANDADE: ST210_gripdon
# bar ordet, GRP_A och Gripper_2F_85 gor det inte. En upplosning som bygger pa
# namnstrangen klarar bara den forsta, och det ar felet M-69 matte.

SORTER_I_SCENEN = (("ST210_gripdon", "verktyg"), ("GRP_A", "verktyg"),
                   ("Gripper_2F_85", "verktyg"), ("ST210_BAND", "transportor"))


def _bild(markerade=()):
    """En ogonblicksbild av scenen ovan, med sorten ur STRUKTUREN."""
    return M.Ogonblicksbild(
        [(n, s, n in markerade) for n, s in SORTER_I_SCENEN],
        kalla="scene_snapshot")


def _scen():
    """Scenlaget som avsikten slar upp i - HARLETT ur bilden.

    Att bygga det for hand hade gett en scen utan sorter, alltsa precis den
    namnbundna varld ogonblicksbilden finns for att ersatta.
    """
    return _bild().scenlage()


def NAIV_UPPLOSNING(markering, kandidater):
    """Implementationen vi INTE byggde: markeringen vinner, alltid.

    Den ar har for att proven ska kunna visa VAD skillnaden ar. Varje prov
    nedan som jamfor mot den namner ocksa vad den naiva hade svarat.
    """
    if not markering.tom():
        return markering.namn()[0]
    return kandidater[0] if kandidater else None


# ---- (d) verktyget far aldrig kunna andra nagot --------------------------

def test_markeringsverktygen_ar_deklarerade_read():
    for namn in VM.VERKTYG:
        v = V.REGISTER[namn]
        assert v.effect == "read", (
            "%s har effect=%r. Ett verktyg som laser vad anvandaren pekar pa "
            "far aldrig kunna andra nagot." % (namn, v.effect))


def test_trasig_fixtur_d_ett_skrivande_markeringsverktyg_falls():
    """(d) Ett markeringsverktyg med effect=write maste fallas av grinden."""
    class _Falsk(object):
        doman = VM.DOMAN
        effect = "write"
        namn = "sabotera_markeringen"

    with pytest.raises(V.Schemafel) as fel:
        VM.granska_domanen({"sabotera_markeringen": _Falsk()})
    assert "read" in str(fel.value)


def test_grinden_slapper_igenom_ett_riktigt_lasande_register():
    VM.granska_domanen(V.REGISTER)      # kastar inte


# ---- (b) ingen markering ar inte ett fel, och aldrig ett val -------------

def test_trasig_fixtur_b_tom_markering_blir_saknas_aldrig_ett_val():
    """(b) Tystnad ar aldrig ett godkannande (I3)."""
    tom = M.Markering([], kalla="get_selection")
    assert tom.tom()
    dom = M.prova(tom, kandidater=("ST210_gripdon", "GRP_A", "Gripper_2F_85"),
                  malsort="verktyg")
    assert dom.utfall == M.SAKNAS
    assert dom.kandidater == ("ST210_gripdon", "GRP_A", "Gripper_2F_85"), \
        "en tom markering far inte krympa kandidatlistan"
    assert dom.belagg is None, "en tom markering ar inget belagg"


def test_tom_markering_lamnar_avsikten_som_en_fraga():
    """Hela vagen: FRAGA stalls som forut, med alla tre kandidaterna."""
    p = A.Avsiktspastaende(A.ANDRING, belagg="byt det dar gripdonet",
                           mal="gripdon", malbelagg="gripdon",
                           malsort="verktyg")
    dom = A.granska(p, "byt det dar gripdonet", _scen(),
                    markering=M.Markering([], kalla="get_selection"))
    assert dom.dom == A.FRAGA
    assert len(dom.kandidater) == 3
    assert dom.markering is None


# ---- (a) tre kandidater loses aldrig ut ----------------------------------

def test_trasig_fixtur_a_tre_markerade_kandidater_loser_inte_ut_en():
    """(a) Farre kandidater, inte ett pahittat val."""
    bild = _bild(markerade=("ST210_gripdon", "GRP_A", "Gripper_2F_85"))
    dom = M.prova(bild.markering(),
                  kandidater=("ST210_gripdon", "GRP_A", "Gripper_2F_85"),
                  malsort="verktyg")
    assert dom.utfall == M.SMALNAD
    assert len(dom.kandidater) == 3
    assert dom.belagg is None
    # Den naiva hade valt ett av dem.
    assert NAIV_UPPLOSNING(bild.markering(),
                           ("ST210_gripdon", "GRP_A", "Gripper_2F_85")) \
        == "ST210_gripdon"


def test_tre_markerade_ger_fraga_med_tre_kandidater_inte_en_dom():
    p = A.Avsiktspastaende(A.ANDRING, belagg="byt det dar gripdonet",
                           mal="gripdon", malbelagg="gripdon",
                           malsort="verktyg")
    bild = _bild(markerade=("ST210_gripdon", "GRP_A", "Gripper_2F_85"))
    dom = A.granska(p, "byt det dar gripdonet", _scen(),
                    markering=bild.markering())
    assert dom.dom == A.FRAGA
    assert len(dom.kandidater) == 3


def test_markeringen_smalnar_av_nar_den_pekar_pa_tva_av_tre():
    """Farre kandidater ar hela vinsten nar den inte kan avgora."""
    bild = _bild(markerade=("GRP_A", "Gripper_2F_85"))
    dom = M.prova(bild.markering(),
                  kandidater=("ST210_gripdon", "GRP_A", "Gripper_2F_85"),
                  malsort="verktyg")
    assert dom.utfall == M.SMALNAD
    assert dom.kandidater == ("GRP_A", "Gripper_2F_85")


# ---- (e) FEL SORT loser aldrig ut ---------------------------------------

def test_trasig_fixtur_e_markering_av_fel_sort_loser_inte_ut():
    """(e) 'byt det dar gripdonet' med en TRANSPORTOR markerad.

    Den viktigaste av de fem. Den naiva implementationen svarar ST210_BAND -
    alltsa byter transportoren nar operatoren bad om ett gripdon.
    """
    bild = _bild(markerade=("ST210_BAND",))
    kand = ("ST210_gripdon", "GRP_A", "Gripper_2F_85")
    dom = M.prova(bild.markering(), kandidater=kand, malsort="verktyg")
    assert dom.utfall == M.MOTSAGELSE
    assert dom.belagg is None, "en motsagelse loser ingenting ut"
    assert dom.kandidater == kand, "kandidatlistan far inte krympa av en motsagelse"
    text = dom.text()
    assert "ST210_BAND" in text, "motsagelsen maste namna vad som ar markerat"
    assert "transportor" in text, "och vilken sort den ar"
    assert "verktyg" in text, "och vilken sort meningen bad om"
    # Den naiva hade bytt transportoren.
    assert NAIV_UPPLOSNING(bild.markering(), kand) == "ST210_BAND"


def test_motsagelse_ger_fraga_som_namner_bada_sidor():
    p = A.Avsiktspastaende(A.ANDRING, belagg="byt det dar gripdonet",
                           mal="gripdon", malbelagg="gripdon",
                           malsort="verktyg")
    bild = _bild(markerade=("ST210_BAND",))
    dom = A.granska(p, "byt det dar gripdonet", _scen(),
                    markering=bild.markering())
    assert dom.dom == A.FRAGA
    skaltext = dom.text()
    assert "ST210_BAND" in skaltext
    assert dom.markering is None, \
        "en motsagelse far inte lamna ett belagg om att markeringen avgjorde"


# ---- markeringen loser ut nar den STAMMER med meningen -------------------

def test_ratt_sort_och_en_kandidat_loser_ut_malet():
    bild = _bild(markerade=("GRP_A",))
    dom = M.prova(bild.markering(),
                  kandidater=("ST210_gripdon", "GRP_A", "Gripper_2F_85"),
                  malsort="verktyg")
    assert dom.utfall == M.AVGJORD
    assert dom.kandidater == ("GRP_A",)
    assert dom.belagg is not None


# ---- (c) ett utlost namn bar alltid sitt belagg -------------------------

def test_trasig_fixtur_c_utlost_namn_utan_belagg_om_markeringen_falls():
    """(c) Aldrig bara namnet. Belagget ska ga att folja."""
    bild = _bild(markerade=("GRP_A",))
    p = A.Avsiktspastaende(A.ANDRING, belagg="byt det dar gripdonet",
                           mal="gripdon", malbelagg="gripdon",
                           malsort="verktyg")
    dom = A.granska(p, "byt det dar gripdonet", _scen(),
                    markering=bild.markering())
    assert dom.dom == A.ANDRING
    assert dom.kandidater == ("GRP_A",)
    assert dom.markering is not None, \
        "(c) ett utlost mal utan belagg om markeringen ar ett tyst val"
    belagg = dom.markering
    assert belagg.kalla == "scen", \
        "belagget ska ga genom sparr.KALLOR:s 'scen', inte en ny kalla"
    assert "GRP_A" in belagg.belagg, "belagget maste namna KOMPONENTEN"
    assert "selected" in belagg.belagg, \
        ("belagget maste bara verktygets EGET falt, sa att det gar att sla "
         "upp i turens lasning")
    # Den LASBARA meningen - att markeringen avgjorde - star i domens skal.
    assert "GRP_A" in dom.text() and "markerad" in dom.text().lower()


def _grund_med_markeringssvar(namn, sort):
    """En turgrund som bar precis det get_selection returnerade."""
    from vc_assist_svc.harness import verifiering
    g = verifiering.Grund(uppgiftstext="byt det dar gripdonet")
    g.lagg_resultat("get_selection", {},
                    {"selected": [{"name": namn, "sort": sort}],
                     "antal": 1, "avkortad": False})
    return g


def test_belagget_gar_att_folja_tillbaka_till_lasningen():
    """(c) forts: belagget ar UPPSLAGBART, inte prosa.

    Ett belagg som inte gar att sla upp i turens egen lasning bevisar
    ingenting - da hade grinden provat en mening mot sig sjalv.
    """
    bild = _bild(markerade=("GRP_A",))
    p = A.Avsiktspastaende(A.ANDRING, belagg="byt det dar gripdonet",
                           mal="gripdon", malbelagg="gripdon",
                           malsort="verktyg")
    dom = A.granska(p, "byt det dar gripdonet", _scen(),
                    markering=bild.markering())
    grund = _grund_med_markeringssvar("GRP_A", "verktyg")
    assert dom.markering.granska("markeringen", "byt det dar gripdonet",
                                 grund) == [], \
        "belagget maste ga att styrka mot turens egen lasning"


def test_belagget_faller_utan_lasning_i_turen():
    """Trasig fixtur: samma belagg, ingen lasning bakom det."""
    bild = _bild(markerade=("GRP_A",))
    p = A.Avsiktspastaende(A.ANDRING, belagg="byt det dar gripdonet",
                           mal="gripdon", malbelagg="gripdon",
                           malsort="verktyg")
    dom = A.granska(p, "byt det dar gripdonet", _scen(),
                    markering=bild.markering())
    brott = dom.markering.granska("markeringen", "byt det dar gripdonet", None)
    assert brott, ("utan turens lasning ska belagget INTE ga att styrka; "
                   "annars provar grinden ingenting")
    assert brott[0][0] == "SH3_OSTODD_SCENUTSAGA"


def test_ett_belagg_utan_upplosning_gar_inte_att_konstruera():
    """Trasig fixtur: ett belagg om att markeringen avgjorde, pa ett utfall
    dar den inte avgjorde nagot. Formen sjalv maste vagra."""
    with pytest.raises(ValueError):
        M.Markeringsdom(M.SMALNAD, ("A", "B"),
                        belagg=sparr.ur_scenen("selected A verktyg"))


# ---- ingen sort i meningen: smalna av, avgor aldrig ----------------------

def test_utan_sort_i_meningen_far_markeringen_bara_smalna_av():
    """'snabba den har linan' namner ingen sort. En kalla kan inte styrka
    sig sjalv, sa markeringen ensam avgor inte - den smalnar av."""
    bild = _bild(markerade=("ST210_BAND",))
    dom = M.prova(bild.markering(),
                  kandidater=("ST210_BAND", "ST210_gripdon"), malsort="")
    assert dom.utfall == M.SMALNAD
    assert dom.kandidater == ("ST210_BAND",)
    assert dom.belagg is None


def test_okand_sort_raknas_som_ingen_sort_alls():
    """En modell far inte komma runt sortprovet genom att saga 'okand'."""
    bild = _bild(markerade=("ST210_BAND",))
    dom = M.prova(bild.markering(),
                  kandidater=("ST210_BAND", "ST210_gripdon"),
                  malsort=M.OKAND)
    assert dom.utfall == M.SMALNAD
    assert dom.belagg is None


def test_en_uppfunnen_sort_avvisas():
    p = A.Avsiktspastaende(A.ANDRING, belagg="byt det dar gripdonet",
                           mal="gripdon", malbelagg="gripdon",
                           malsort="griparmsklass")
    dom = A.granska(p, "byt det dar gripdonet", _scen(),
                    markering=_bild(markerade=("GRP_A",)).markering())
    assert dom.dom == A.OKANT
    assert "griparmsklass" in dom.text()


# ---- markering utanfor kandidaterna --------------------------------------

def test_markering_som_inte_ar_kandidat_smalnar_inte_bort_allt():
    """Markeringen pekar pa nagot meningens ord inte kan syfta pa alls.

    Da bar den ingen upplysning om malet, och kandidatlistan star kvar hel.
    Att krympa den till tomt hade gjort en ovidkommande markering till ett
    hinder i stallet for en upplysning.
    """
    bild = _bild(markerade=("ST210_BAND",))
    dom = M.prova(bild.markering(),
                  kandidater=("ST210_gripdon", "GRP_A"), malsort="")
    assert dom.utfall == M.OVIDKOMMANDE
    assert dom.kandidater == ("ST210_gripdon", "GRP_A")
    assert dom.belagg is None


# ---- sorten kommer ur STRUKTUREN, aldrig ur namnet ----------------------

def test_sorten_harleds_aldrig_ur_namnet():
    """En komponent som HETER Robot men inte bar nagon markor ar okand sort.

    MATT i M-171 pa en levande scen: komponenten "Robot" bar bara en
    boolsignal, ingen robotstyrning. Namnhardledning hade kallat den robot.
    """
    bild = M.Ogonblicksbild([("Robot", M.OKAND, False),
                             ("ST8_Bana", "transportor", False)],
                            kalla="scene_snapshot")
    assert bild.sort("Robot") == M.OKAND
    assert "robot" not in bild.text().split("Robot")[1].split("\n")[0].lower()


def test_sorterna_ar_katalogens_egna_och_ingen_tredje_kopia():
    """S12: en ordlista som avgor en dom star pa ETT stalle."""
    from vc_assist_svc import datablad
    assert M.SORTER == tuple(n for n, _m in datablad.FAMILJEMARKORER)


def test_okand_ar_inte_en_familj():
    assert M.OKAND not in M.SORTER


# ---- ogonblicksbilden ----------------------------------------------------

def test_bilden_bar_namn_sort_och_markering_for_varje_komponent():
    bild = _bild(markerade=("GRP_A",))
    assert bild.antal() == 4
    t = bild.text()
    for namn in ("ST210_gripdon", "GRP_A", "Gripper_2F_85", "ST210_BAND"):
        assert namn in t
    assert "transportor" in t and "verktyg" in t
    assert "GRP_A" in bild.markering().namn()


def test_bilden_utan_markering_sager_saknas_i_klartext():
    t = _bild().text()
    assert M.SAKNAS in t, \
        "ingen markering ska sta som SAKNAS, inte utelamnas tyst (I3)"


def test_en_avkortad_lasning_sager_det_i_bilden():
    bild = M.Ogonblicksbild([("A", M.OKAND, False)], kalla="scene_snapshot",
                            avkortad=True)
    assert "AVKORTAD" in bild.text()
    assert not bild.fullstandig()


def test_bilden_ger_ett_scenlage_som_avsikten_kan_sla_upp_i():
    bild = _bild(markerade=("GRP_A",))
    lage = bild.scenlage()
    assert isinstance(lage, sparr.Scenlage)
    assert set(lage.namn()) == {"ST210_gripdon", "GRP_A", "Gripper_2F_85",
                                "ST210_BAND"}


def test_bilden_ar_liten_nog_att_skickas_varje_tur():
    """Spar r: blir bilden for stor ar den inget bild, den ar ett verktygssvar.

    Taket och dess harkomst star i markering.TAK_TOKENS.
    """
    from vc_assist_svc.llm import matt
    bild = _bild(markerade=("GRP_A",))
    assert matt.tokens(bild.text()) <= M.TAK_TOKENS


def test_bilden_faller_nar_den_vaxer_forbi_taket():
    """Trasig fixtur: en scen sa stor att bilden inte kan skickas varje tur."""
    poster = [("Komponent_med_ett_ganska_langt_namn_%03d" % i, "transportor",
               False) for i in range(400)]
    stor = M.Ogonblicksbild(poster, kalla="scene_snapshot")
    assert not stor.ryms(), "en bild over taket maste saga att den inte ryms"
    assert "FOR STOR" in stor.text()
    from vc_assist_svc.llm import matt
    assert matt.tokens(stor.text()) <= M.TAK_TOKENS, \
        "aven den avkortade bilden maste ga att skicka"


# ---- svaren fran verktygen -----------------------------------------------

def test_markering_ur_verktygssvar():
    m = M.markering_ur_svar(
        {"selected": [{"name": "GRP_A", "sort": "verktyg"}], "antal": 1},
        kalla="get_selection")
    assert m.namn() == ("GRP_A",)
    assert m.sorter() == ("verktyg",)


def test_ett_svar_utan_markeringsfalt_avvisas():
    with pytest.raises(ValueError):
        M.markering_ur_svar({"komponenter": []}, kalla="get_selection")


def test_bild_ur_verktygssvar():
    bild = M.ogonblicksbild_ur_svar({
        "components": [{"name": "GRP_A", "sort": "verktyg", "selected": True},
                       {"name": "ST8_Mall", "sort": "", "selected": False}],
        "antal": 2, "markerade": 1, "avkortad": False})
    assert bild.antal() == 2
    assert bild.sort("ST8_Mall") == M.OKAND, \
        "tom sort ur verktyget maste bli OKAND, aldrig gissas"
    assert bild.markering().namn() == ("GRP_A",)


def test_ett_svar_utan_komponentfalt_avvisas():
    with pytest.raises(ValueError):
        M.ogonblicksbild_ur_svar({"selected": []})
