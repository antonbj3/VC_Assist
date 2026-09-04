# -*- coding: utf-8 -*-
"""L0/L1 for data-verktygen: katalog, kunskap och ogat (docs/spec/45_verktyg.md).

Kors utan VC och utan bryggan - det ar hela poangen med data-grenen.
Fem saker provas, och den tredje ar den viktigaste:

1. REGISTRERINGEN. Varje verktyg ligger i DATA_HANDLERS, bar mode=data och
   effect=read, och dess handlare tar bara (argument).
2. VAGEN. Ett data-verktyg kors av utforaren utan att bryggan nas en enda
   gang, och det routas aldrig till godkannandekon.
3. RETURKONTRAKTET FALLER. Varje verktygs riktiga svar provas mot dess
   returns-schema, OCH ett medvetet brutet svar MASTE avvisas. En grind som
   aldrig fallit ar oprovad (docs/spec/95_testprotokoll.md).
4. ARLIGHETEN. Ingen uppfunnen URI, inget uppfunnet API-namn, ingen gissad
   signatur. Ett bomskott ar found=false med VERKLIGA alternativ.
5. FAIL-CLOSED. En ogonrapport som inte gar att lasa ar aldrig ett
   godkannande, och utan formagerapport ar aven data-verktygen avslagna.

URVALET. Domanmodulerna registrerar sig vid import, och verktyg/__init__.py
importerar dem. Den har filen laser darfor ur PAKETETS register och filtrerar
pa de tre domanerna - inte ur ett eget. Det ar samma register som tjansten
anvander, vilket gor provet sannare an en kopia.
"""
import copy
import inspect
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

from vc_assist_svc import verktyg as V                      # noqa: E402
from vc_assist_svc.verktyg import register as _register     # noqa: E402


DOMANER = ("catalog", "knowledge", "eyes")


def _ladda_domanerna():
    """Plockar ut de tre data-domanerna ur PAKETETS eget register.

    Tidigare byttes registren ut mot tomma ordbocker runt importen, for att
    verktyg/__init__.py da INTE importerade domanmodulerna och grannens test
    matte ett register pa exakt 21. Nu importerar paketet dem, sa en andra
    import registrerar ingenting - modulen ar redan laddad. Isoleringen blev
    darmed inte bara onodig utan direkt fel: den gav tomma register.

    Att lasa ur paketets register ar dessutom sannare. Det ar det register
    tjansten faktiskt anvander.
    """
    from vc_assist_svc.verktyg import katalog, kunskap, ogonverktyg
    reg = dict((n, v) for n, v in _register.REGISTER.items() if v.doman in DOMANER)
    data = dict((n, h) for n, h in _register.DATA_HANDLERS.items() if n in reg)
    kodgen = dict((n, h) for n, h in _register.CODE_GEN_HANDLERS.items() if n in reg)
    return reg, data, kodgen, katalog, kunskap, ogonverktyg


REGISTER, DATA_HANDLERS, KODGEN, katalog, kunskap, ogonverktyg = _ladda_domanerna()


# ---- fixturer ------------------------------------------------------------

# En riktig ogonrapport, skriven med ogats EGEN skrivare. Da kan fixturen inte
# drifta fran grammatiken utan att kontraktet sager ifran (41_ogat_kontrakt.md).
K = ogonverktyg.K


def _rapport(dom="PASS", orsak="allt inom facit", overtradelse=False):
    r = K.Rapport("prov_mall", "2026-09-04T12:00:00", 10.0, 200, 20.0)
    r.sektion("MOTION")
    r.rad("GRIP FORMED t=1.0s dist=0.5mm")
    r.rad("PLACE IN_TARGET err=1.2mm z=0.8m")
    r.sektion("SAFETY")
    r.rad("COLLISION none")
    r.sektion("HONESTY")
    r.rad("TELEPORT_TRANSFER %s" % ("VIOLATION" if overtradelse else "OK"))
    r.rad("NEVER_GRIPPED OK")
    r.satt_dom(dom, orsak)
    return r.text()


GRON_RAPPORT = _rapport()
TRASIG_A91 = ogonverktyg.BANK["A-91"].trasig_ogonrapport()

# Ett minimalt och ett maximalt anrop per verktyg. Listan MASTE tacka hela
# registret; testet nedan faller annars. Skalet ar grannens: ett prov som inte
# tacker allt mater fel, och ett nytt verktyg ska inte slinka forbi grinden.
EXEMPEL = {
    "search_catalog": [{},
                       {"query": "pall"},
                       {"category": "robot", "min_rackvidd_mm": 2000.0,
                        "min_nyttolast_kg": 20.0},
                       {"query": "ljusrida"}],
    "catalog_item": [{"uri": "bank://robot/abb_irb_660_180_3150"},
                     {"uri": "bank://robot/finns_inte"}],
    "catalog_categories": [{}],
    # De tva mot det INSTALLERADE biblioteket. Pa en maskin utan VC svarar de
    # "inget bibliotek" med skalet, och det ar ett giltigt svar mot schemat -
    # vilket ar precis vad ett prov utan bibliotek ska visa.
    "search_installed_library": [{},
                                 {"query": "IRB 6700"},
                                 {"manufacturer": "ABB", "category": "Robots"},
                                 {"has_parameter": "conveyor", "max_rows": 3}],
    "library_overview": [{}],
    "lookup_api": [{"name": "vcRobotController.moveTo"},
                   {"name": "moveTo"},
                   {"name": "vcRobotController.moveToo"}],
    "search_api": [{"query": "distance"},
                   {"query": "collision", "limit": 3},
                   {"query": "det_har_finns_inte_i_vc"}],
    "type_surface": [{"type_name": "vcComponent"},
                     {"type_name": "vcCompnent"}],
    "lookup_helper": [{"module": "vcHelpers.Robot"}],
    "eyes_report": [{"report": GRON_RAPPORT},
                    {"report": TRASIG_A91},
                    {"report": "inte en ogonrapport alls"}],
    "bench_task": [{"task_id": "A-01"}, {"task_id": "T-92"},
                   {"task_id": "Z-99"}],
    "bench_compare": [{"task_id": "A-91", "report": TRASIG_A91},
                      {"task_id": "A-01", "report": TRASIG_A91},
                      {"task_id": "A-90", "report": TRASIG_A91},
                      {"task_id": "Z-99", "report": GRON_RAPPORT},
                      {"task_id": "A-01", "report": "trasig text"}],
}


class Attrappbrygga(object):
    """Bryggans klientyta, men den far ALDRIG anropas harifran."""

    def __init__(self):
        self.logg = []

    def anrop(self, op, args=None):
        self.logg.append((op, args or {}))
        raise AssertionError(
            "ett data-verktyg anropade bryggan med %r; data-grenen kors i "
            "tjansten (45_verktyg.md)" % (op,))


def full_rapport():
    """En formagerapport dar allt finns. Samma form som formaga.formaga()."""
    return {"ytor": {yta: {"finns": True, "typ": "builtin_function_or_method"}
                     for yta in V.KANDA_YTOR},
            "summering": {"provade": len(V.KANDA_YTOR)}}


@pytest.fixture
def brygga():
    return Attrappbrygga()


@pytest.fixture
def utf(brygga):
    return V.Utforare(brygga, V.urval_allt_pa(REGISTER), register=REGISTER,
                      data_handlers=DATA_HANDLERS, code_gen_handlers=KODGEN)


def kor(namn, argument):
    """Kor handlaren precis som utforaren gor: validera in, validera ut."""
    v = REGISTER[namn]
    args = V.validera_argument(v, argument)
    resultat = DATA_HANDLERS[namn](args)
    V.validera_resultat(v, resultat)
    return resultat


def alla_anrop():
    for namn in sorted(EXEMPEL):
        for rat in EXEMPEL[namn]:
            yield namn, rat


ANROP = list(alla_anrop())


# ---- 1. registret --------------------------------------------------------

def test_de_tre_domanerna_ar_byggda():
    domaner = {}
    for v in REGISTER.values():
        domaner.setdefault(v.doman, []).append(v.namn)
    assert sorted(domaner) == ["catalog", "eyes", "knowledge"]
    # catalog bar TVA kallor, med flit: tre verktyg mot bankens 65 handskrivna
    # poster (som uppgifterna binder mot, lintkod M4_UNKNOWN_URI) och tva mot
    # det bibliotek som faktiskt ar installerat pa maskinen (M-57: 3201
    # komponenter). Att sla ihop dem hade varit att andra ett kontrakt for att
    # slippa forklara en skillnad.
    assert len(domaner["catalog"]) == 5
    assert len(domaner["knowledge"]) == 4
    assert len(domaner["eyes"]) == 3
    assert len(REGISTER) == 12


def test_allt_ligger_i_data_registret():
    """45_verktyg.md: index, katalog och kunskap ar data, inte kodgenerering."""
    assert set(DATA_HANDLERS) == set(REGISTER)
    assert KODGEN == {}


def test_de_tre_domanerna_ligger_i_paketets_register():
    """Domanerna ska vara inkopplade i paketet, inte bara i den har filen.

    Tidigare provade det har testet motsatsen - att paketets register var
    OROT - eftersom modulerna da inte importerades av verktyg/__init__.py.
    De ar inkopplade nu, och da ar det inkopplingen som ska provas.
    """
    for namn in REGISTER:
        assert namn in V.REGISTER, "%s ar inte inkopplat i paketet" % namn
        assert namn in V.DATA_HANDLERS, "%s ligger inte i DATA_HANDLERS" % namn
    assert len(REGISTER) == 12, "catalog 3 + 2 mot installerade biblioteket, knowledge 4, eyes 3"


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_varje_verktyg_ar_data_och_laser(namn):
    v = REGISTER[namn]
    assert v.mode == "data"
    # effect=read for allt har. Ett data-verktyg som skriver skulle ga forbi
    # godkannandekon helt (I12), och schemat avvisar det redan vid
    # definitionen - men regeln provas har ocksa, pa de verktyg som finns.
    assert v.effect == "read"
    assert v.since == "4.10"
    assert v.beskrivning.strip()
    assert v.returns["required"], "utan required kan ett tomt svar passera (I3)"


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_varje_kravd_yta_finns_i_formagerapportens_egen_lista(namn):
    for yta in REGISTER[namn].kraver:
        assert yta in V.KANDA_YTOR


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_ingen_handlare_kan_se_bryggan(namn):
    """Handlarens enda parameter ar argumenten; se register._granska_handlare."""
    parametrar = list(inspect.signature(DATA_HANDLERS[namn]).parameters.values())
    assert [p.name for p in parametrar] == ["argument"]
    assert parametrar[0].kind in (parametrar[0].POSITIONAL_ONLY,
                                  parametrar[0].POSITIONAL_OR_KEYWORD)


def test_exempellistan_tacker_hela_registret():
    assert set(EXEMPEL) == set(REGISTER)


def test_en_handlare_med_bryggparameter_avvisas_vid_registrering():
    """Den trasiga fixturen: registret MASTE falla den."""
    # En KOPIA med eget namn: originalet ar redan registrerat i paketet, och
    # registret avvisar dubbletter fore det hinner titta pa signaturen.
    original = REGISTER["catalog_categories"]
    v = V.Verktyg(namn="prov_bryggparameter", beskrivning=original.beskrivning,
                  mode="data", effect="read", parameters=original.parameters,
                  returns=original.returns, since=original.since,
                  kraver=original.kraver, doman="prov",
                  timeout_ms=original.timeout_ms)
    with pytest.raises(V.Schemafel) as e:
        _register.registrera(v, lambda argument, klient: {})
    assert "ska ta exakt en" in str(e.value)


# ---- 2. vagen genom utforaren -------------------------------------------

@pytest.mark.parametrize("namn,argument", ANROP)
def test_data_verktyget_kors_utan_att_bryggan_nas(namn, argument, utf, brygga):
    r = utf.utfor(namn, argument)
    assert brygga.logg == [], "ett data-verktyg gar aldrig via bryggan"
    assert r.mode == "data"
    assert r.koad is False and r.qid is None
    assert r.op is None, "data-grenen valjer aldrig exec eller exec_queue"
    assert isinstance(r.resultat, dict)


def test_utan_formagerapport_ar_aven_data_verktygen_avslagna(brygga):
    """I3: tystnad fran bryggan ar aldrig ett godkannande."""
    u = V.Utforare(brygga, V.urval_ur_rapport(None, REGISTER), register=REGISTER,
                   data_handlers=DATA_HANDLERS, code_gen_handlers=KODGEN)
    with pytest.raises(V.Avstangt):
        u.utfor("lookup_api", {"name": "moveTo"})


def test_saknad_yta_slar_av_precis_de_verktyg_som_ror_den(brygga):
    r = full_rapport()
    r["ytor"]["app.load"] = {"finns": False, "typ": None}
    u = V.urval_ur_rapport(r, REGISTER)
    # Katalogen och bankuppgiften pekar bada ut app.load: en post finns for
    # att laddas, och en uppgifts scen ar en lista URI:er som ska laddas.
    assert not u.pa("search_catalog")
    assert not u.pa("bench_task")
    assert "app.load" in u.skal("catalog_item")
    # Kunskapen och ogats rapport ror andra ytor och ska vara kvar.
    assert u.pa("lookup_api")
    assert u.pa("eyes_report")


def test_full_rapport_slar_pa_allt():
    u = V.urval_ur_rapport(full_rapport(), REGISTER)
    assert len(u.pa_namn()) == len(REGISTER)


def test_okant_argument_avvisas_innan_handlaren_kors():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["catalog_item"], {"urn": "bank://x/y"})
    assert "okant argument" in str(e.value)


# ---- 3. returkontraktet, och att det FALLER -----------------------------

@pytest.mark.parametrize("namn,argument", ANROP)
def test_svaret_haller_verktygets_returschema(namn, argument):
    assert isinstance(kor(namn, argument), dict)


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_ett_svar_utan_obligatorisk_nyckel_falls(namn):
    """Den trasiga fixturen for returkontraktet: en saknad nyckel MASTE falla."""
    v = REGISTER[namn]
    riktigt = kor(namn, EXEMPEL[namn][0])
    for nyckel in v.returns["required"]:
        trasigt = dict(riktigt)
        del trasigt[nyckel]
        with pytest.raises(V.Svarsfel) as e:
            V.validera_resultat(v, trasigt)
        assert nyckel in str(e.value)


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_ett_svar_med_fel_typ_falls(namn):
    v = REGISTER[namn]
    riktigt = kor(namn, EXEMPEL[namn][0])
    nyckel = v.returns["required"][0]
    # En lista dar ett objekt eller en strang vantades, och tvartom: bada
    # sorterna finns bland nycklarna, sa vi valjer ett varde som SAKERT ar
    # av fel typ.
    fel_varde = "fel typ" if not isinstance(riktigt[nyckel], str) else []
    with pytest.raises(V.Svarsfel) as e:
        V.validera_resultat(v, dict(riktigt, **{nyckel: fel_varde}))
    assert nyckel in str(e.value)


def test_ett_brutet_varde_djupt_i_en_lista_falls():
    """Kontrollen gar hela vagen ned, inte bara pa toppnivan."""
    v = REGISTER["search_catalog"]
    riktigt = kor("search_catalog", {"query": "pall"})
    trasigt = copy.deepcopy(riktigt)
    del trasigt["traffar"][0]["uri"]
    with pytest.raises(V.Svarsfel) as e:
        V.validera_resultat(v, trasigt)
    assert "uri" in str(e.value)


# ---- 4. katalogen: arlighet om vad som finns ----------------------------

def test_katalogen_ar_den_matta_lokala_banken():
    """MATT: 65 poster. Inget eCatalog, inga .vcmx-layouter pa disk."""
    r = kor("catalog_categories", {})
    assert r["antal_poster"] == 65
    assert r["index"]["index_id"] == "bank-lokal-v1"
    assert sum(k["antal"] for k in r["kategorier"]) == 65
    assert sum(g["antal"] for g in r["grupper"]) == 65
    assert sum(s["antal"] for s in r["stamplar"]) == 65


def test_varje_katalogsvar_sager_att_katalogen_ar_lokal_och_begransad():
    for namn, argument in [("search_catalog", {}),
                           ("catalog_item", {"uri": "bank://last/eur_pall"}),
                           ("catalog_categories", {})]:
        notering = kor(namn, argument)["notering"]
        assert "LOKAL och BEGRANSAD" in notering
        assert "eCatalog" in notering
        assert "nattjanst" in notering


def test_ingen_traff_ar_en_uppfunnen_uri():
    """I9: modellen far bara valja ur trafflistan, sa listan maste vara sann."""
    for traff in kor("search_catalog", {})["traffar"]:
        assert traff["uri"] in katalog.POSTER
    assert kor("search_catalog", {})["antal"] == 65


def test_en_uri_som_inte_finns_ger_found_false_och_verkliga_alternativ():
    r = kor("catalog_item", {"uri": "bank://robot/abb_irb_9999"})
    assert r["found"] is False
    assert r["post"] is None
    assert r["alternativ"], "gruppen robot finns, sa alternativ ska ges"
    for uri in r["alternativ"]:
        assert uri in katalog.POSTER, "ett alternativ maste FINNAS"


def test_en_uri_i_en_okand_grupp_ger_inga_alternativ_alls():
    """Hellre tomt an gissat: en okand grupp har inga verkliga grannar."""
    r = kor("catalog_item", {"uri": "bank://svetspistol/finns_inte"})
    assert r["found"] is False
    assert r["alternativ"] == []


def test_varje_post_bar_sin_harkomststampel():
    """Siffrans harkomst hor till siffran: ANTAGEN far inte se matt ut."""
    r = kor("search_catalog", {})
    for traff in r["traffar"]:
        assert traff["stampel"] in ("PUBLICERAD_SPEC", "STANDARDMATT", "ANTAGEN")
        assert traff["stampel_betydelse"].strip()


def test_varje_matt_varde_bar_sin_enhet():
    post = kor("catalog_item", {"uri": "bank://robot/abb_irb_6700_235_2650"})["post"]
    matt = dict((m["namn"], m) for m in post["matt"])
    assert matt["rackvidd"]["varde"] == 2655 and matt["rackvidd"]["enhet"] == "mm"
    assert matt["nyttolast"]["varde"] == 235.0 and matt["nyttolast"]["enhet"] == "kg"
    # axlar bar inget enhetssuffix, och da gissas ingen enhet fram.
    assert matt["axlar"]["enhet"] is None


def test_granssnitten_saknas_och_det_star_i_svaret():
    """45_verktyg.md vantar granssnitt ur eCatalog. De finns inte har."""
    r = kor("catalog_item", {"uri": "bank://last/eur_pall"})
    assert "granssnitt" not in r["post"]
    assert "Granssnitt" in r["notering_granssnitt"]
    assert "list_interfaces" in r["notering_granssnitt"]


def test_ett_rackviddsfilter_slapper_aldrig_igenom_en_post_utan_rackvidd():
    """En saknad siffra ar inte en uppfylld siffra."""
    r = kor("search_catalog", {"min_rackvidd_mm": 1000.0})
    assert r["antal"] > 0
    for traff in r["traffar"]:
        matt = dict((m["namn"], m["varde"]) for m in traff["matt"])
        assert matt.get("rackvidd", 0) >= 1000.0


def test_sokningen_hittar_over_stavningarna_i_indexet():
    """MATT: 35 av 65 poster bar icke-ASCII, ovriga ar translittererade."""
    assert kor("search_catalog", {"query": "ljusrida"})["antal"] == 1
    assert kor("search_catalog", {"query": "LJUSRIDA"})["antal"] == 1


def test_kategorierna_i_schemat_ar_indexets_verkliga():
    enum = REGISTER["search_catalog"].parameters["properties"]["category"]["enum"]
    assert sorted(enum) == sorted({p["kategori"] for p in katalog.POSTER.values()})
    with pytest.raises(V.Argumentfel):
        V.validera_argument(REGISTER["search_catalog"], {"category": "svetsrobot"})


# ---- 5. kunskapen: exakt namn eller tomt svar ---------------------------

def test_indexet_ar_den_matta_api_ytan():
    """46_kunskapsindex.md: minst 204 typer, 966 metoder, 1159 egenskaper."""
    ix = kor("lookup_api", {"name": "moveTo"})["index"]
    assert ix["typer"] >= 204
    assert ix["metoder"] >= 966
    assert ix["egenskaper"] >= 1159
    assert ix["symboler_totalt"] == 3444
    assert ix["vc_version"] == "4.10"


def test_ett_kant_namn_ger_exakt_signatur_och_harkomst():
    r = kor("lookup_api", {"name": "vcRobotController.moveTo"})
    assert r["found"] is True and r["antal"] == 1
    s = r["symbols"][0]
    assert s["full_name"] == "vcRobotController.moveTo"
    assert s["sort"] == "metod"
    assert "vcMotionTarget target" in s["signature"]
    assert "vc_python_api.json" in s["harkomst"]
    assert "api.xml" in s["harkomst"], "signaturen kommer ur en annan fil"


def test_varje_uppslagssvar_bar_instruktionen_ordagrant():
    """46_kunskapsindex.md: raden som alltid foljer med ett uppslag."""
    vantad = "Anvand namnet exakt som det star. Omformulera det inte."
    for namn, argument in [("lookup_api", {"name": "moveTo"}),
                           ("search_api", {"query": "distance"}),
                           ("type_surface", {"type_name": "vcComponent"}),
                           ("lookup_helper", {"module": "vcHelpers.Math"})]:
        assert kor(namn, argument)["instruktion"] == vantad
    assert vantad in kor("lookup_api", {"name": "moveTo"})["svar"]


def test_ett_pahittat_namn_ger_tomt_svar_aldrig_en_gissning():
    """46_kunskapsindex.md, punkt 3."""
    r = kor("lookup_api", {"name": "vcRobotController.moveToo"})
    assert r["found"] is False
    assert r["symbols"] == [] and r["antal"] == 0 and r["svar"] == ""


def test_forslagen_efter_ett_bomskott_ar_verkliga_namn():
    r = kor("lookup_api", {"name": "vcRobotController.moveToo"})
    assert r["forslag"], "moveTo ligger en redigering bort"
    for f in r["forslag"]:
        assert kunskap.INDEX.finns(f["name"]), "ett forslag maste FINNAS"
        assert f["avstand"] <= kunskap.FORSLAG_AVSTAND_TAK


def test_ett_namn_utan_grannar_ger_tom_forslagslista():
    """Tomt ar det arliga svaret nar inget kant namn ligger nara nog."""
    r = kor("lookup_api", {"name": "xyzzy_kvack_finns_verkligen_inte"})
    assert r["found"] is False
    assert r["forslag"] == []


def test_sokningen_sager_nar_listan_klipptes():
    r = kor("search_api", {"query": "component", "limit": 5})
    assert r["antal"] == 5
    assert r["antal_totalt"] > 5
    assert r["avkortad"] is True


def test_sokningen_klipper_vid_taket_aven_om_modellen_begar_mer():
    r = kor("search_api", {"query": "component", "limit": 10 ** 6})
    assert r["antal"] <= kunskap.MAX_TRAFFAR
    assert r["antal_totalt"] > r["antal"]


def test_sokningen_ger_exakt_traff_forst():
    r = kor("search_api", {"query": "moveTo"})
    assert r["traffar"][0]["name"] == "moveTo"
    assert r["traffar"][0]["rang"] == "exakt"


def test_typytan_bar_hela_arvet():
    r = kor("type_surface", {"type_name": "vcComponent"})
    assert r["found"] is True
    assert r["arvskedja"][0] == "vcComponent"
    namn = set(m["name"] for m in r["medlemmar"])
    assert {"findNode", "getProperty", "Name", "Uri"} <= namn
    assert r["antal"] == len(r["medlemmar"])


def test_ett_okant_typnamn_ger_found_false_och_verkliga_typnamn():
    r = kor("type_surface", {"type_name": "vcCompnent"})
    assert r["found"] is False and r["medlemmar"] == []
    assert any(f["name"].endswith("vcComponent") or f["name"] == "vcComponent"
               for f in r["forslag"])


def test_hjalpmodulerna_ar_en_enum_sa_ett_pahitt_avvisas_fore_korning():
    assert len(kunskap.HJALPMODULER) == 8
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["lookup_helper"],
                            {"module": "vcHelpers.Gripper"})
    assert "vcHelpers.Robot" in str(e.value), "felet ska namna de riktiga"


def test_en_hjalpmodul_ger_sina_medlemmar_med_harkomst():
    r = kor("lookup_helper", {"module": "vcHelpers.Robot"})
    assert r["antal"] == 55
    for m in r["medlemmar"]:
        assert "helpers.xml" in m["harkomst"]


# ---- 6. ogat: ogat faller domen, och fail-closed ------------------------

def test_en_gron_rapport_lases_med_dom_och_sektioner():
    r = kor("eyes_report", {"report": GRON_RAPPORT})
    assert r["ok"] is True and r["dom"] == "PASS" and r["godkand"] is True
    assert [s["namn"] for s in r["sektioner"]] == ["MOTION", "SAFETY", "HONESTY"]
    assert r["sektioner"][0]["rader"][0] == "GRIP FORMED t=1.0s dist=0.5mm"
    assert r["overtradelser"] == []
    assert r["grinddom"] is None


def test_en_inconclusive_rapport_ar_inte_godkand():
    """41_ogat_kontrakt.md regel 4: INCONCLUSIVE raknas som inte godkant."""
    r = kor("eyes_report", {"report": _rapport("INCONCLUSIVE", "for fa prov")})
    assert r["ok"] is True and r["dom"] == "INCONCLUSIVE"
    assert r["godkand"] is False


def test_en_overtradelse_ar_aldrig_godkand():
    r = kor("eyes_report",
            {"report": _rapport("FAIL", "delen teleporterade", overtradelse=True)})
    assert r["overtradelser"] == ["TELEPORT_TRANSFER"]
    assert r["godkand"] is False


def test_ett_pass_med_overtradelse_domes_inte_om_till_godkant():
    """Regel 5: den motsagelsen ar precis den falska framgang ogat finns for."""
    text = _rapport("FAIL", "x", overtradelse=True).replace(
        "EYES VERDICT FAIL x", "EYES VERDICT PASS allt bra")
    r = kor("eyes_report", {"report": text})
    assert r["ok"] is False and r["godkand"] is False
    assert r["grinddom"] == "NOT GOLD (malformed eyes output)"


def test_en_avhuggen_rapport_ar_inte_ett_godkannande():
    """I3 fail-closed. Den trasiga fixturen for ogonlasningen."""
    text = "\n".join(GRON_RAPPORT.splitlines()[:-1]) + "\n"
    r = kor("eyes_report", {"report": text})
    assert r["ok"] is False and r["godkand"] is False
    assert r["grinddom"] == "NOT GOLD (truncated eyes output)"


def test_en_okand_ogonversion_gissas_aldrig():
    # v9: en version ingen kanner. (v2 ar sedan M-65 den skrivna versionen.)
    text = GRON_RAPPORT.replace("EYES v%d" % K.EYES_VERSION, "EYES v9", 1)
    r = kor("eyes_report", {"report": text})
    assert r["grinddom"] == "NOT GOLD (unknown eyes version)"


def test_banken_ar_den_matta():
    """80_bank.md: 51 uppgifter, varav 14 medvetet trasiga varianter.

    Talet var 47 fram till M-45, som la till fyra uppgifter med sparfacit
    (T-07, H-04, S-05, L-05). Sparren star kvar och gar bara at ett hall: en
    uppgift som dyker upp utan att nagon skrivit ned det nya talet ar en
    uppgift ingen granskat.
    """
    assert len(ogonverktyg.BANK) == 51
    assert len(ogonverktyg.BANK.varianter()) == 14


def test_en_bankuppgift_ger_prompt_facit_och_scen():
    r = kor("bench_task", {"task_id": "A-01"})
    assert r["found"] is True
    assert r["uppgift"]["grupp"] == "A"
    assert "OPC UA" in r["uppgift"]["prompt"], "kedjan maste sta i uppgiften"
    assert r["facit"]["grind"] == "OGAT" and r["facit"]["dom"] == "PASS"
    assert r["facit"]["kravda_rader"] and r["facit"]["forbjudna_rader"]
    assert r["facit"]["korningar"] >= 3, "I5: minst tre oberoende korningar"
    for k in r["scen"]["komponenter"]:
        assert k["uri"] in katalog.POSTER, "scenens URI:er star i katalogindexet"


def test_ett_okant_uppgifts_id_ger_bankens_verkliga_id():
    r = kor("bench_task", {"task_id": "Z-99"})
    assert r["found"] is False and r["uppgift"] is None
    assert len(r["kanda_id"]) == 51
    assert "A-01" in r["kanda_id"]


def test_facit_haller_mot_variantens_egen_ogonrapport():
    """A-91 ar den medvetet trasiga varianten och bar sin egen ogonrapport."""
    r = kor("bench_compare", {"task_id": "A-91", "report": TRASIG_A91})
    assert r["jamforbar"] is True and r["uppfyllt"] is True
    assert r["dom_stammer"] is True and r["observerad_dom"] == "FAIL"
    assert r["saknade_rader"] == [] and r["forbjudna_traffar"] == []


def test_samma_rapport_faller_mot_hela_uppgiftens_facit():
    """Den trasiga fixturen for jamforelsen: den MASTE falla nagon gang."""
    r = kor("bench_compare", {"task_id": "A-01", "report": TRASIG_A91})
    assert r["uppfyllt"] is False
    assert r["dom_stammer"] is False
    assert r["forvantad_dom"] == "PASS" and r["observerad_dom"] == "FAIL"
    assert r["saknade_rader"], "A-01 kraver rader den har rapporten inte bar"


def test_en_uppgift_som_falls_fore_ogat_har_ingen_ogondom_att_jamfora_mot():
    r = kor("bench_compare", {"task_id": "A-90", "report": TRASIG_A91})
    assert r["found"] is True and r["jamforbar"] is False
    assert "G1" in r["skal"]
    assert r["uppfyllt"] is False


def test_en_olasbar_rapport_ar_inte_ett_uppfyllt_facit():
    r = kor("bench_compare", {"task_id": "A-01", "report": "inte en rapport"})
    assert r["uppfyllt"] is False
    assert r["fel"], "lasfelet ska sta i svaret"
    assert r["fel"][0]["grinddom"].startswith("NOT GOLD")


def test_okant_uppgifts_id_i_jamforelsen_ger_inget_tyst_godkannande():
    r = kor("bench_compare", {"task_id": "Z-99", "report": GRON_RAPPORT})
    assert r["found"] is False and r["jamforbar"] is False
    assert r["uppfyllt"] is False
    assert len(r["kanda_id"]) == 51
