# -*- coding: utf-8 -*-
"""L1 for planeringslagrets VILLKOR OCH ORDNING (svc/vc_assist_svc/plan/).

Fyra former provas, var och en at BADA hallen - att kontrollen faller pa ett
verkligt fel OCH slapper igenom det korrekta. En grind som bara provats at ena
hallet ar oprovad (docs/spec/95_testprotokoll.md).

    beroenden       A fore B, och en ordning som ar DETERMINISTISK
    forvillkor      steget kors bara om nagot galler
    alternativ      antingen A eller B
    parallellitet   far koras samtidigt

Och det hardaste kravet: en cykel ska UPPTACKAS och rapporteras med vilka steg
som ingar, aldrig bli en oandlig loop.

Kors utan VC.
"""
import itertools
import os
import random
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.plan import graf as G                      # noqa: E402
from vc_assist_svc.plan.fel import Graffel, Specfel           # noqa: E402
from vc_assist_svc.plan.korning import (EJ_UTFORD, FALLEN, HOPPAD,  # noqa: E402
                                        KORD, Korare)
from vc_assist_svc.plan.predikat import (Forvillkor, Korlage,  # noqa: E402
                                         Predikat, granska_vag, las_vag)
from vc_assist_svc.plan.steg import (BINDNINGSREGLER, Bindning,  # noqa: E402
                                     Kontroll, Steg)


# ---- byggstenar ---------------------------------------------------------

def v(id, beroenden=(), **ovrigt):
    """Ett verktygssteg utan sidoeffekter. list_components tar inga argument."""
    return Steg.verktygssteg(id, "list_components", {}, "provsteg %s" % id,
                             beroenden=beroenden, **ovrigt)


def k(id, predikat, beroenden=(), **ovrigt):
    return Steg.kontrollsteg(id, Kontroll("villkor",
                                          villkor=Forvillkor(predikat)),
                             "provkontroll %s" % id, beroenden=beroenden,
                             **ovrigt)


# ---- 1. beroenden och deterministisk ordning ----------------------------

def test_ordningen_respekterar_beroenden():
    g = G.Uppgiftsgraf([v("b", ("a",)), v("a"), v("c", ("b",))])
    ordning = g.ordning()
    assert ordning.index("a") < ordning.index("b") < ordning.index("c")


def test_samma_graf_ger_samma_ordning_oavsett_insattningsordning():
    """Utan det gar en korning inte att jamfora med nasta."""
    steg = [v("a"), v("b", ("a",)), v("c", ("a",)), v("d", ("b", "c")),
            v("e", ("a",)), v("f", ("e",))]
    facit = G.Uppgiftsgraf(steg).ordning()
    slump = random.Random(20260904)          # fast fro: provet ska ga att upprepa
    for _ in range(50):
        blandat = list(steg)
        slump.shuffle(blandat)
        assert G.Uppgiftsgraf(blandat).ordning() == facit


def test_ordningen_ar_kanonisk_minsta_id_forst():
    """Tva korbara steg -> det minsta id:t forst. Ett kanoniskt val, inte ett
    godtyckligt."""
    g = G.Uppgiftsgraf([v("zebra"), v("alfa")])
    assert g.ordning() == ["alfa", "zebra"]


def test_okant_beroende_rapporteras_och_ordningen_vagrar():
    g = G.Uppgiftsgraf([v("a", ("finns_inte",))])
    koder = [kod for kod, _ in g.problem()]
    assert "G1_OKANT_BEROENDE" in koder
    with pytest.raises(Graffel):
        g.ordning()


def test_en_hel_graf_utan_brister_ger_tom_problemlista():
    g = G.Uppgiftsgraf([v("a"), v("b", ("a",))])
    assert g.problem() == []


# ---- 2. cykler ----------------------------------------------------------

def test_tva_steg_i_ring_upptacks_med_bada_stegen():
    g = G.Uppgiftsgraf([v("a", ("b",)), v("b", ("a",))])
    assert g.cykler() == [["a", "b"]]


def test_tre_steg_i_ring_upptacks_med_alla_tre():
    g = G.Uppgiftsgraf([v("a", ("c",)), v("b", ("a",)), v("c", ("b",))])
    assert g.cykler() == [["a", "b", "c"]]


def test_tva_skilda_ringar_rapporteras_var_for_sig():
    g = G.Uppgiftsgraf([v("a", ("b",)), v("b", ("a",)),
                        v("x", ("y",)), v("y", ("x",)), v("fri")])
    assert g.cykler() == [["a", "b"], ["x", "y"]]


def test_cykeln_blir_ett_fel_med_stegen_i_sig_inte_en_oandlig_loop():
    g = G.Uppgiftsgraf([v("a", ("b",)), v("b", ("a",)), v("c", ("a",))])
    with pytest.raises(Graffel) as fel:
        g.ordning()
    assert fel.value.cykler == [["a", "b"]]
    assert "a" in str(fel.value) and "b" in str(fel.value)


def test_ett_steg_som_beror_pa_sig_sjalvt_avvisas_redan_i_steget():
    with pytest.raises(Specfel) as fel:
        v("a", ("a",))
    assert "sig sjalvt" in str(fel.value)


def test_en_djup_kedja_gar_att_ordna_utan_rekursionstak():
    """Cykelletningen ar iterativ; en lang kedja far inte bli RecursionError."""
    steg = [v("s0")] + [v("s%d" % n, ("s%d" % (n - 1),)) for n in range(1, 900)]
    g = G.Uppgiftsgraf(steg)
    assert g.cykler() == []
    assert len(g.ordning()) == 900


def test_en_lang_ring_upptacks_ocksa():
    n = 300
    steg = [v("s%d" % i, ("s%d" % ((i - 1) % n),)) for i in range(n)]
    g = G.Uppgiftsgraf(steg)
    assert len(g.cykler()) == 1 and len(g.cykler()[0]) == n


# ---- 3. forvillkor ------------------------------------------------------

def _lage(**kv):
    return Korlage(**kv)


def test_predikat_pa_resultat_haller_och_faller_at_bada_hall():
    p = Predikat("resultat", steg="a", vag="name", operator="==", varde="band")
    sant, skal = p.prova(_lage(resultat={"a": {"name": "band"}}))
    assert sant and "band" in skal
    falskt, skal = p.prova(_lage(resultat={"a": {"name": "annat"}}))
    assert not falskt and "annat" in skal


def test_predikat_pa_saknad_vag_ar_falskt_med_skal_aldrig_ett_undantag():
    p = Predikat("resultat", steg="a", vag="interfaces.7.name",
                 operator="==", varde="x")
    sant, skal = p.prova(_lage(resultat={"a": {"interfaces": []}}))
    assert not sant and "finns inte" in skal


def test_predikat_pa_steg_utan_svar_ar_falskt_med_skal():
    p = Predikat("resultat", steg="a", vag="name", operator="==", varde="x")
    sant, skal = p.prova(_lage())
    assert not sant and "inget svar" in skal


def test_storleksjamforelse_pa_text_ar_falskt_med_skal_inte_alfabetisk_lycka():
    p = Predikat("resultat", steg="a", vag="n", operator=">", varde=3)
    sant, skal = p.prova(_lage(resultat={"a": {"n": "fyra"}}))
    assert not sant and "inget tal" in skal
    sant, _ = p.prova(_lage(resultat={"a": {"n": 4}}))
    assert sant


def test_statuspredikat_laser_utfallet_at_bada_hall():
    p = Predikat("status", steg="a", status=KORD)
    assert p.prova(_lage(statusar={"a": KORD}))[0]
    assert not p.prova(_lage(statusar={"a": FALLEN}))[0]


def test_faktapredikat_laser_det_koraren_fick_veta():
    p = Predikat("fakta", nyckel="brygga", operator="==", varde="uppe")
    assert p.prova(_lage(fakta={"brygga": "uppe"}))[0]
    assert not p.prova(_lage(fakta={"brygga": "nere"}))[0]
    assert not p.prova(_lage())[0]


def test_okand_operator_avvisas_vid_konstruktionen():
    with pytest.raises(Specfel):
        Predikat("resultat", steg="a", vag="n", operator="ungefar", varde=1)


def test_sammansattning_alla_och_nagot_skiljer_sig():
    sant = Predikat("fakta", nyckel="a", operator="==", varde=1)
    falskt = Predikat("fakta", nyckel="a", operator="==", varde=2)
    lage = _lage(fakta={"a": 1})
    assert not Forvillkor([sant, falskt], "alla").prova(lage)[0]
    assert Forvillkor([sant, falskt], "nagot").prova(lage)[0]


def test_ett_forvillkor_utan_predikat_ar_inget_villkor():
    with pytest.raises(Specfel):
        Forvillkor([])


def test_vagar_provas_mot_verktygets_returns_redan_vid_planeringen():
    schema = {"type": "object",
              "properties": {"interfaces": {
                  "type": "array",
                  "items": {"type": "object",
                            "properties": {"name": {"type": "string"}}}}}}
    assert granska_vag(schema, "interfaces.0.name") is None
    assert "namn" in granska_vag(schema, "interfaces.0.namn")
    assert granska_vag(schema, "interfaces.name") is not None


def test_las_vag_gar_genom_listor_och_ordboker():
    svar = {"interfaces": [{"name": "Flow"}]}
    assert las_vag(svar, "interfaces.0.name") == (True, "Flow")
    assert las_vag(svar, "interfaces.1.name") == (False, None)


# ---- 4. forvillkor i korningen ------------------------------------------

class Tomutforare(object):
    """Utforare-yta utan brygga: raknar anrop och svarar tomt.

    Provar ORDNINGEN och VILLKOREN, inte verktygen. Verktygsvagen provas mot
    bryggattrappen i test_plan.py.
    """

    def __init__(self, svar=None):
        self.anropade = []
        self.svar = svar or {}

    def utfor(self, namn, argument=None):
        self.anropade.append(namn)
        return _Resultat(self.svar.get(namn, {"components": [], "antal": 0,
                                              "avkortad": False}))


class _Resultat(object):
    def __init__(self, resultat):
        self.resultat = resultat
        self.koad = False
        self.qid = None


def _plan_med(steg, verifiering=None):
    """En minimal plan runt en grupp steg, utan att ga via planeringen."""
    from vc_assist_svc.plan.byggplan import Byggplan
    from vc_assist_svc.plan.spec import DetaljeradSpec, Grundbegaran
    from vc_assist_svc.plan.verifiering import Krav, Verifieringskrav
    begaran = Grundbegaran("prov", "en provplan", "test")
    krav = verifiering or Verifieringskrav("PASS", [Krav("SAFETY",
                                                         "COLLISION none")])
    spec = DetaljeradSpec("prov", begaran, verifiering=krav)
    return Byggplan("prov", spec, G.Uppgiftsgraf(steg))


def test_steg_med_uppfyllt_forvillkor_kors():
    steg = [v("a"),
            v("b", ("a",), forvillkor=Forvillkor(
                [Predikat("status", steg="a", status=KORD)]))]
    prot = Korare(Tomutforare()).kor(_plan_med(steg))
    assert prot.status("b") == KORD


def test_steg_med_ouppfyllt_forvillkor_hoppas_over_MED_SKAL():
    steg = [v("a"),
            v("b", ("a",), forvillkor=Forvillkor(
                [Predikat("status", steg="a", status=FALLEN)]))]
    prot = Korare(Tomutforare()).kor(_plan_med(steg))
    post = prot.post("b")
    assert post.status == HOPPAD
    assert "forvillkoret holl inte" in post.skal and "kord" in post.skal


def test_ett_hoppat_steg_ar_inte_ett_fallet_steg():
    """Skillnaden ar hela poangen: hoppat ar ett val, fallet ar ett fel."""
    steg = [v("a"),
            v("b", ("a",), forvillkor=Forvillkor(
                [Predikat("fakta", nyckel="finns_ej", operator="finns")]))]
    prot = Korare(Tomutforare()).kor(_plan_med(steg))
    assert prot.rakning()[HOPPAD] == 1 and prot.rakning()[FALLEN] == 0


def test_en_fallen_kontroll_stoppar_sina_beroende_med_skal():
    steg = [v("a"),
            k("kontroll", [Predikat("resultat", steg="a", vag="antal",
                                    operator=">", varde=5)], ("a",)),
            v("b", ("kontroll",))]
    prot = Korare(Tomutforare()).kor(_plan_med(steg))
    assert prot.status("kontroll") == FALLEN
    assert prot.status("b") == EJ_UTFORD
    assert "kontroll" in prot.post("b").skal


def test_samma_kontroll_slapper_igenom_nar_villkoret_haller():
    utf = Tomutforare({"list_components": {"components": [], "antal": 9,
                                           "avkortad": False}})
    steg = [v("a"),
            k("kontroll", [Predikat("resultat", steg="a", vag="antal",
                                    operator=">", varde=5)], ("a",)),
            v("b", ("kontroll",))]
    prot = Korare(utf).kor(_plan_med(steg))
    assert prot.status("kontroll") == KORD and prot.status("b") == KORD


# ---- 5. alternativ ------------------------------------------------------

class Falandeutforare(Tomutforare):
    """Faller de verktygssteg vars id star i .fall."""

    def __init__(self, fall=()):
        Tomutforare.__init__(self)
        self.fall = set(fall)

    def utfor(self, namn, argument=None):
        self.anropade.append(namn)
        if namn in self.fall:
            from vc_assist_svc.verktyg import Svarsfel
            raise Svarsfel("%s foll med flit" % namn)
        return _Resultat({"components": [], "antal": 0, "avkortad": False})


def _alternativpar():
    return [Steg.verktygssteg("alt_a", "list_components", {}, "forsta vagen",
                              alternativ_grupp="grupp"),
            Steg.verktygssteg("alt_b", "list_connections", {}, "andra vagen",
                              alternativ_grupp="grupp")]


def test_nar_forsta_alternativet_lyckas_hoppas_det_andra_over():
    prot = Korare(Tomutforare()).kor(_plan_med(_alternativpar()))
    assert prot.status("alt_a") == KORD
    assert prot.status("alt_b") == HOPPAD
    assert "alt_a" in prot.post("alt_b").skal


def test_nar_forsta_alternativet_faller_kors_det_andra():
    utf = Falandeutforare(fall={"list_components"})
    prot = Korare(utf).kor(_plan_med(_alternativpar()))
    assert prot.status("alt_a") == FALLEN
    assert prot.status("alt_b") == KORD


def _efter_steget():
    """Ett steg efter alternativgruppen, med ett EGET verktyg sa att provet
    mater beroendet och inte vilket verktyg som rakade falla."""
    return Steg.verktygssteg("efter", "list_nodes", {"component": "X"},
                             "kors nar nagot av alternativen lyckats",
                             beroenden=("alt_a", "alt_b"))


def test_ett_steg_kan_bero_pa_en_alternativgrupp_och_ett_lyckat_racker():
    steg = _alternativpar() + [_efter_steget()]
    prot = Korare(Tomutforare()).kor(_plan_med(steg))
    assert prot.status("alt_a") == KORD and prot.status("alt_b") == HOPPAD
    assert prot.status("efter") == KORD


def test_samma_steg_kors_nar_det_ANDRA_alternativet_ar_det_som_lyckades():
    steg = _alternativpar() + [_efter_steget()]
    prot = Korare(Falandeutforare(fall={"list_components"})).kor(_plan_med(steg))
    assert prot.status("alt_a") == FALLEN and prot.status("alt_b") == KORD
    assert prot.status("efter") == KORD


def test_men_faller_bada_alternativen_kors_inte_steget_efter():
    steg = _alternativpar() + [_efter_steget()]
    utf = Falandeutforare(fall={"list_components", "list_connections"})
    prot = Korare(utf).kor(_plan_med(steg))
    post = prot.post("efter")
    assert post.status == EJ_UTFORD
    assert "inget alternativ i gruppen" in post.skal


def test_en_alternativgrupp_med_ett_enda_steg_ar_ingen_grupp():
    g = G.Uppgiftsgraf([Steg.verktygssteg("ensam", "list_components", {},
                                          "ensam", alternativ_grupp="grupp")])
    assert "G4_ALTERNATIV_ENSAM" in [kod for kod, _ in g.problem()]


def test_ett_alternativ_far_inte_bero_pa_sitt_eget_alternativ():
    g = G.Uppgiftsgraf([
        Steg.verktygssteg("alt_a", "list_components", {}, "a",
                          alternativ_grupp="grupp"),
        Steg.verktygssteg("alt_b", "list_components", {}, "b",
                          beroenden=("alt_a",), alternativ_grupp="grupp")])
    assert "G5_ALTERNATIV_BEROENDE" in [kod for kod, _ in g.problem()]


def test_tva_oberoende_alternativ_ar_inget_problem():
    assert G.Uppgiftsgraf(_alternativpar()).problem() == []


# ---- 6. parallellitet ---------------------------------------------------

def test_tva_oberoende_steg_far_forklaras_samtidiga():
    g = G.Uppgiftsgraf([v("a", parallell_grupp="p"),
                        v("b", parallell_grupp="p")])
    assert g.problem() == []
    assert g.lager() == [["a", "b"]]
    assert g.bredd() == 2


def test_samtidighet_mellan_steg_med_beroendevag_ar_en_motsagelse():
    g = G.Uppgiftsgraf([v("a", parallell_grupp="p"),
                        v("b", ("a",), parallell_grupp="p")])
    koder = [kod for kod, _ in g.problem()]
    assert "G6_PARALLELL_MOTSAGELSE" in koder


def test_samtidighet_over_ett_mellansteg_upptacks_ocksa():
    g = G.Uppgiftsgraf([v("a", parallell_grupp="p"), v("mellan", ("a",)),
                        v("b", ("mellan",), parallell_grupp="p")])
    assert "G6_PARALLELL_MOTSAGELSE" in [kod for kod, _ in g.problem()]


def test_en_parallellgrupp_med_ett_steg_mater_ingenting():
    g = G.Uppgiftsgraf([v("a", parallell_grupp="p")])
    assert "G7_PARALLELL_ENSAM" in [kod for kod, _ in g.problem()]


def test_lagren_ar_den_ovre_gransen_for_samtidighet():
    g = G.Uppgiftsgraf([v("a"), v("b", ("a",)), v("c", ("a",)),
                        v("d", ("b", "c"))])
    assert g.lager() == [["a"], ["b", "c"], ["d"]]
    assert g.bredd() == 2


# ---- 7. lasning utan beroende -------------------------------------------

def test_ett_steg_som_laser_ett_annat_svar_maste_bero_pa_det():
    """Annars ar ordningen inte garanterad, och predikatet laser ett tomt svar."""
    steg = [v("a"),
            k("b", [Predikat("resultat", steg="a", vag="antal",
                             operator=">", varde=0)])]
    koder = [kod for kod, _ in G.Uppgiftsgraf(steg).problem()]
    assert "G3_LASNING_UTAN_BEROENDE" in koder


def test_samma_lasning_med_beroendet_pa_plats_ar_ren():
    steg = [v("a"),
            k("b", [Predikat("resultat", steg="a", vag="antal",
                             operator=">", varde=0)], ("a",))]
    assert G.Uppgiftsgraf(steg).problem() == []


def test_en_bindning_raknas_ocksa_som_lasning():
    steg = [v("a"),
            Steg.verktygssteg("b", "find_component",
                              {"name": Bindning("steg", "a", vag="antal",
                                                typ="string")},
                              "binder utan att bero")]
    assert "G3_LASNING_UTAN_BEROENDE" in [kod for kod, _
                                          in G.Uppgiftsgraf(steg).problem()]


# ---- 8. bindningsregeln -------------------------------------------------

def _granssnittssvar(komponent, namn):
    return {"component": komponent,
            "interfaces": [{"name": n, "is_abstract": False, "connected": False}
                           for n in namn],
            "antal": len(namn), "avkortad": False}


def test_regeln_valjer_nar_det_inte_finns_nagot_val():
    regel = BINDNINGSREGLER["enda_gemensamma_par"]
    bindningar, skal = regel([_granssnittssvar("band", ["Flow"]),
                              _granssnittssvar("grind", ["InFlow"])],
                             [("a", "string"), ("b", "string")])
    assert bindningar == {"a": "Flow", "b": "InFlow"}
    assert "Flow" in skal


def test_regeln_vagrar_valja_nar_det_finns_ett_val_och_sager_vilka():
    regel = BINDNINGSREGLER["enda_gemensamma_par"]
    bindningar, skal = regel([_granssnittssvar("band", ["Flow", "Backflow"]),
                              _granssnittssvar("grind", ["InFlow"])],
                             [("a", "string"), ("b", "string")])
    assert bindningar is None
    assert "Flow" in skal and "Backflow" in skal
    assert "operatoren" in skal


def test_regeln_vagrar_pa_en_komponent_utan_gransnitt():
    regel = BINDNINGSREGLER["enda_gemensamma_par"]
    bindningar, _skal = regel([_granssnittssvar("band", []),
                               _granssnittssvar("grind", ["InFlow"])],
                              [("a", "string"), ("b", "string")])
    assert bindningar is None


def test_en_okand_bindningsregel_finns_inte():
    with pytest.raises(Specfel):
        Kontroll("bindning", regel="valj_nagot", kallor=("a",),
                 ger=(("x", "string"),))


# ---- 9. ordningen over en verklig plan ----------------------------------

def test_alla_permutationer_av_en_liten_graf_ger_samma_ordning():
    steg = [v("a"), v("b", ("a",)), v("c", ("a",)), v("d", ("b", "c"))]
    facit = G.Uppgiftsgraf(steg).ordning()
    for perm in itertools.permutations(steg):
        assert G.Uppgiftsgraf(list(perm)).ordning() == facit


# ---- 10. varje lintkod har en trasig fixtur -----------------------------

# En grind som aldrig fallt ar oprovad (docs/spec/95_testprotokoll.md).
# Tabellen binder varje kod i graf.LINTKODER till provet som faller pa den.
TRASIGA_FIXTURER = {
    "G1_OKANT_BEROENDE": "test_okant_beroende_rapporteras_och_ordningen_vagrar",
    "G2_CYKEL": "test_tva_steg_i_ring_upptacks_med_bada_stegen",
    "G3_LASNING_UTAN_BEROENDE":
        "test_ett_steg_som_laser_ett_annat_svar_maste_bero_pa_det",
    "G4_ALTERNATIV_ENSAM":
        "test_en_alternativgrupp_med_ett_enda_steg_ar_ingen_grupp",
    "G5_ALTERNATIV_BEROENDE":
        "test_ett_alternativ_far_inte_bero_pa_sitt_eget_alternativ",
    "G6_PARALLELL_MOTSAGELSE":
        "test_samtidighet_mellan_steg_med_beroendevag_ar_en_motsagelse",
    "G7_PARALLELL_ENSAM":
        "test_en_parallellgrupp_med_ett_steg_mater_ingenting",
}


def test_varje_lintkod_i_grafen_har_en_trasig_fixtur():
    assert set(TRASIGA_FIXTURER) == set(G.LINTKODER)
    egna = dict(globals())
    for kod, testnamn in sorted(TRASIGA_FIXTURER.items()):
        assert testnamn in egna, "%s pekar pa ett test som inte finns" % kod


def test_varje_kod_som_grafen_kan_lamna_star_i_tabellen():
    """En kod utan text i LINTKODER gar inte att sla upp for den som laser."""
    trasig = G.Uppgiftsgraf([
        v("a", ("saknas",), parallell_grupp="p"),
        v("b", ("a",), parallell_grupp="p"),
        v("ensam", alternativ_grupp="g"),
        k("laser", [Predikat("resultat", steg="a", vag="antal",
                             operator="finns")])])
    koder = set(kod for kod, _ in trasig.problem())
    assert koder and koder <= set(G.LINTKODER)
