# -*- coding: utf-8 -*-
"""L0/L1/L2 for domanen transport (svc/vc_assist_svc/verktyg/transport.py).

Kors utan VC. Samma tre lager som test_verktyg.py, plus ett fjarde som den
domanen inte hade:

1. SCHEMAT. Varje verktyg bar effect, mode, returns, since, kraver, doman och
   timeout_ms, och argument provas mot schemat innan nagot skickas.
2. ROUTINGEN. effect=read -> exec, effect=write -> exec_queue, mekaniskt.
3. KORSPROVET MOT BRYGGANS SKRIVGRIND. Varje lasande verktygs kod far INTE
   domas som skrivande; varje skrivande verktygs kod MASTE domas som skrivande.
4. KORSPROVET MOT API-INDEXET. Varje mall gar genom api_index.Validator och
   far inte innehalla ett enda uppfunnet VC-namn.

Om punkt 4 och varfor den mater sin egen storhet
------------------------------------------------
En grind som inte NAR fram godkanner allt. api_index.Validator harleder inte
returtypen ur en funktion som koden sjalv definierar, sa en mall som hamtar
komponenten genom en hjalpare far typen "okand" och varje lasning efterat blir
odomd. Da hade korsprovet varit gront aven for en mall full av pahittade namn.
Darfor provas har tre saker och inte en:

  a) noll fel over alla mallar,
  b) att grinden FAKTISKT kontrollerar namn (kontrollerade_namn per anrop),
  c) att samma mall med ett pahittat namn FALLER, och att samma mall skriven
     genom en hjalpare INTE faller - alltsa att skillnaden ar matt och inte
     pastadd (95_testprotokoll.md: en grind som aldrig fallit ar oprovad).

OPROVAT MOT VC: det finns noll komponenter i den lokala katalogen, sa ingen
mall har kort mot en verklig transportor. Allt nedan ar de grindar som gar att
kora utan VC.
"""
import ast
import builtins
import inspect
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import formaga                                        # noqa: E402
import oga_kontrakt                                   # noqa: E402
import skrivgrind                                     # noqa: E402
from vc_assist_svc import api_index                   # noqa: E402
from vc_assist_svc import verktyg as V                # noqa: E402
from vc_assist_svc.verktyg import kodmall             # noqa: E402
from vc_assist_svc.verktyg import transport as T      # noqa: E402


# ---- fixturer ------------------------------------------------------------

# Ett minimalt och ett maximalt anrop per verktyg. Listan MASTE tacka hela
# domanen; testet nedan faller annars. Ett korsprov som inte tacker allt mater
# fel, och ett nytt verktyg ska inte kunna slinka forbi grindarna.
EXEMPEL = {
    "list_transport_behaviours": [
        {}, {"component": "Bana 1"}, {"kind": "statistics"},
        {"component": "Bana 1", "kind": "container"}],
    "transport_behaviour_info": [
        {"component": "Bana 1", "behaviour": "OneWayPath"}],
    "list_transport_parameters": [
        {"component": "Bana 1"},
        {"component": "Bana 1", "behaviour": "OneWayPath"}],
    "get_transport_parameter": [
        {"component": "Bana 1", "parameter": "ConveyorSpeed"},
        {"component": "Bana 1", "parameter": "Capacity",
         "behaviour": "OneWayPath"}],
    "set_transport_parameter": [
        {"component": "Bana 1", "parameter": "ConveyorSpeed", "value": 0.5},
        {"component": "Bana 1", "parameter": "Accumulate", "value": True,
         "behaviour": "OneWayPath"}],
    "get_capacity": [
        {"component": "Buffert"},
        {"component": "Buffert", "behaviour": "Container"}],
    "set_capacity": [
        {"component": "Buffert", "behaviour": "Container", "capacity": 12}],
    "list_buffer_contents": [
        {"component": "Buffert", "behaviour": "Container"}],
    "list_flow_connectors": [{}, {"component": "Bana 1"}],
    "get_routing_rule": [
        {"component": "Vaxel"},
        {"component": "Vaxel", "behaviour": "RoutingRule"}],
    "set_routing_target": [
        {"component": "Vaxel", "behaviour": "RoutingRule", "connector": 2}],
    "list_path_sensors": [{}, {"component": "Bana 1"}],
    "get_feeder_info": [
        {"component": "Matare"},
        {"component": "Matare", "behaviour": "ProductCreator"}],
    "set_product_feed": [
        {"component": "Matare", "behaviour": "ProductCreator",
         "interval": "5.0"},
        {"component": "Matare", "behaviour": "ProductCreator", "limit": 100},
        {"component": "Matare", "behaviour": "ProductCreator",
         "interval": "normal(5,1)", "limit": 50}],
    "get_component_creator_info": [{"component": "Matare"}],
    "set_component_feed": [
        {"component": "Matare", "behaviour": "ComponentCreator",
         "interval": 3.5},
        {"component": "Matare", "behaviour": "ComponentCreator", "limit": 10},
        {"component": "Matare", "behaviour": "ComponentCreator",
         "interval": 2, "limit": 10}],
    "list_transport_nodes": [{}, {"component": "Station"}],
    "list_process_flow_groups": [{"component": "ProcessController"}],
    "list_product_types": [{"component": "ProcessController"}],
    "product_type_info": [
        {"component": "ProcessController", "product_type": "Kolv"}],
    "list_processes": [{"component": "Station"}],
    "list_process_statements": [
        {"component": "Station", "behaviour": "ProcessExecutor",
         "process": "Montera"}],
    "station_statistics": [{"component": "Station"}],
    "layout_statistics": [{}, {"min_arrived": 1}],
    "station_state_times": [
        {"component": "Station", "behaviour": "Statistics"},
        {"component": "Station", "behaviour": "Statistics",
         "states": ["Busy", "Idle"]}],
}

# Namn den genererade koden far anvanda utan att sjalv definiera dem.
# getApplication kommer ur "from vcScript import *" i bryggans skript, och _s
# laggs i exec-globalerna av pump.py vid varje korning.
VC_GLOBALER = {"getApplication", "_s", "json", "vcVector", "vcMatrix"}

# Inbyggda namn som bara finns i Python 2. Mallarna ror dem enbart inne i
# try/except NameError, precis som kodmall.py sjalv gor.
PY2_INBYGGDA = {"unicode", "long", "basestring", "xrange"}

# Konstruktioner som inte finns i Python 2.7. Koden kors i VC 4.10:s
# Stackless 2.7 och i VC 5.0:s 3.x (36_versioner.md), sa den maste ga i bada.
FORBJUDNA_NODER = ("JoinedStr", "FormattedValue", "NamedExpr", "AnnAssign",
                   "AsyncFunctionDef", "Await", "AsyncFor", "AsyncWith",
                   "Match", "TryStar")

# Ett verktyg i den har domanen far aldrig ta ett geometriskt argument (I8).
# Modellen anger relationer och parametrar; laget raknar VC.
GEOMETRISKA = ("position", "transform", "matrix", "coordinate", "koordinat",
               "rotation", "wpr", "offset", "xyz")

# Byggs EN gang: indexet laser fyra XML/JSON-filer och det tar tid nog att
# marka i en parametriserad svit.
VALIDATOR = api_index.bygg_validator()
INDEX = VALIDATOR.index


def transportnamn():
    return tuple(sorted(V.domaner()[T.DOMAN]))


def alla_anrop():
    """(namn, argument) for varje exempel, med default-varden ifyllda."""
    for namn in sorted(EXEMPEL):
        for rat in EXEMPEL[namn]:
            yield namn, V.validera_argument(V.REGISTER[namn], rat)


def kod_for(namn, argument):
    return V.CODE_GEN_HANDLERS[namn](argument)


ANROP = list(alla_anrop())


def _syntetiskt(s):
    """Ett varde som haller ett returns-schema. Facit skrivet ur schemat."""
    typ = s["type"]
    typ = typ[0] if isinstance(typ, list) else typ
    if "enum" in s:
        return s["enum"][0]
    if typ == "string":
        return "x"
    if typ == "integer":
        return 1
    if typ == "number":
        return 1.0
    if typ == "boolean":
        return True
    if typ == "null":
        return None
    if typ == "array":
        return [_syntetiskt(s["items"]) for _ in range(s.get("minItems", 1))]
    if typ == "object":
        return {n: _syntetiskt(us) for n, us in s.get("properties", {}).items()}
    raise AssertionError("okand type %r i schemat" % (typ,))


def svar_for(verktyg):
    r = verktyg.returns
    return {n: _syntetiskt(r["properties"][n]) for n in r["required"]}


class Attrappbrygga(object):
    """Talar bryggans klientyta utan VC (L2). Loggar VARJE anrop.

    Avsiktligt minimal och egen: att dela attrapp med test_verktyg.py skulle
    gora ordningen mellan tva testfilers importer till en del av provet.
    """

    def __init__(self):
        self.logg = []
        self.qid = 0
        self.ko = []
        self.nasta_utfall = "done"

    def anrop(self, op, args=None):
        self.logg.append((op, args or {}))
        if op == "exec":
            return {"v": 1, "ok": True, "result": self._resultat(args),
                    "stdout": "", "stderr": "", "elapsed_ms": 1}
        if op == "exec_queue":
            self.qid += 1
            qid = "q%d" % self.qid
            self.ko.append({"qid": qid, "desc": args.get("desc", ""),
                            "state": "pending", "_args": args})
            return {"v": 1, "ok": True, "stdout": "",
                    "result": {"qid": qid, "desc": args.get("desc", ""),
                               "state": "pending"}}
        if op == "queue_approve":
            for post in self.ko:
                if post["qid"] == args["qid"]:
                    post["state"] = "approved"
            return {"v": 1, "ok": True, "stdout": "",
                    "result": {"qid": args["qid"], "state": "approved"}}
        if op == "queue_list":
            ut = []
            for post in self.ko:
                if post["state"] == "approved":
                    post["state"] = self.nasta_utfall
                    post["svar"] = (
                        {"ok": True, "stdout": "",
                         "result": self._resultat(post["_args"])}
                        if self.nasta_utfall == "done" else
                        {"ok": False, "stdout": "",
                         "error": {"code": "E_EXEC", "message": "provfel"}})
                ut.append({k: v for k, v in post.items()
                           if not k.startswith("_")})
            return {"v": 1, "ok": True, "stdout": "", "result": {"queue": ut}}
        raise AssertionError("attrappen kan inte %r" % (op,))

    def _resultat(self, args):
        namn = (args.get("desc") or "").split("(")[0]
        return svar_for(V.REGISTER[namn])

    @property
    def op_lista(self):
        return [op for op, _ in self.logg]


@pytest.fixture
def brygga():
    return Attrappbrygga()


@pytest.fixture
def utf(brygga):
    return V.Utforare(brygga, V.urval_allt_pa(V.REGISTER))


def full_rapport():
    """En formagerapport dar allt finns. Samma form som formaga.formaga()."""
    return {"ytor": {yta: {"finns": True, "typ": "builtin_function_or_method"}
                     for yta in V.KANDA_YTOR},
            "summering": {"provade": len(V.KANDA_YTOR)}}


# ---- 1. domanen och schemat ---------------------------------------------

def test_domanen_ar_registrerad_och_kodgenererande():
    namn = transportnamn()
    assert len(namn) == 25, "domanen transport bar 25 verktyg"
    for n in namn:
        assert V.REGISTER[n].mode == "codegen"
        assert n in V.CODE_GEN_HANDLERS
        assert n not in V.DATA_HANDLERS


def test_fordelningen_read_write_ar_den_avsedda():
    lasande = [n for n in transportnamn() if V.REGISTER[n].effect == "read"]
    skrivande = [n for n in transportnamn() if V.REGISTER[n].effect == "write"]
    assert len(lasande) == 20
    assert sorted(skrivande) == [
        "set_capacity", "set_component_feed", "set_product_feed",
        "set_routing_target", "set_transport_parameter"]


def test_exempellistan_tacker_hela_domanen():
    """En lista som inte tacker allt mater fel. Nytt verktyg -> nytt exempel."""
    assert set(EXEMPEL) == set(transportnamn())


def test_transportnamnen_krockar_inte_med_de_andra_domanerna():
    """Ett dubblettnamn hade avvisats vid import; provet gor skalet synligt."""
    andra = set(V.REGISTER) - set(transportnamn())
    assert not (set(transportnamn()) & andra)


@pytest.mark.parametrize("namn", transportnamn())
def test_varje_verktyg_bar_de_obligatoriska_falten(namn):
    v = V.REGISTER[namn]
    assert v.mode in ("data", "codegen")
    assert v.effect in ("read", "write")
    assert v.since == "4.10"
    assert v.doman == T.DOMAN
    assert v.timeout_ms > 0
    assert v.kraver
    assert v.returns["required"]
    assert v.beskrivning.strip()
    assert v.parameters["additionalProperties"] is False


@pytest.mark.parametrize("namn", transportnamn())
def test_varje_argument_och_returfalt_bar_en_beskrivning(namn):
    """Utan beskrivning fyller modellen i betydelsen sjalv."""
    v = V.REGISTER[namn]
    for arg, s in v.parameters["properties"].items():
        assert s.get("description", "").strip(), "%s.%s" % (namn, arg)
    for falt, s in v.returns["properties"].items():
        assert s.get("description", "").strip(), "%s -> %s" % (namn, falt)


@pytest.mark.parametrize("namn", transportnamn())
def test_varje_kravd_yta_finns_i_formagerapportens_egen_lista(namn):
    """En yta grinden inte kan prova ar ingen grind (S2)."""
    kanda = {yta for yta, _o, _a in formaga.YTOR}
    for yta in V.REGISTER[namn].kraver:
        assert yta in kanda, "%s kraver %s som formaga.py inte provar" % (
            namn, yta)


@pytest.mark.parametrize("namn", transportnamn())
def test_verktyget_kraver_de_ytor_dess_mall_faktiskt_ror(namn):
    """Kraver far inte vara en onskelista: koden ska anvanda ytorna.

    Kravet galler VERKTYGET och inte ett enskilt anrop - ett verktyg med ett
    valfritt argument har tva vagar genom mallen, och formagegrinden domer om
    bada pa en gang. Darfor provas unionen over exemplen.
    """
    kod = "\n".join(kod_for(namn, V.validera_argument(V.REGISTER[namn], rat))
                    for rat in EXEMPEL[namn])
    for yta in V.REGISTER[namn].kraver:
        medlem = yta.split(".", 1)[1]
        assert medlem in kod, "%s kraver %s men ingen av dess vagar ror den" % (
            namn, yta)


@pytest.mark.parametrize("namn", transportnamn())
def test_inget_transportverktyg_tar_koordinater(namn):
    """I8. Modellen anger relationer och parametrar, aldrig geometri."""
    for arg in V.REGISTER[namn].parameters["properties"]:
        assert not any(g in arg.lower() for g in GEOMETRISKA), (
            "%s tar argumentet %s; geometrin ska raknas av VC" % (namn, arg))


def test_verktygsdefinitionen_gar_inte_att_andra_efterat():
    with pytest.raises(AttributeError):
        V.REGISTER["set_capacity"].effect = "read"


def test_openai_formen_bar_inga_egna_nycklar():
    f = V.REGISTER["set_product_feed"].som_openai()
    assert f["function"]["name"] == "set_product_feed"
    assert "x-minst-en-av" in V.REGISTER["set_product_feed"].parameters
    assert "x-minst-en-av" not in f["function"]["parameters"]


# ---- 2. argumentvalidering ----------------------------------------------

def test_ratt_argument_slapps_igenom():
    args = V.validera_argument(V.REGISTER["get_capacity"],
                               {"component": "Buffert"})
    assert args == {"component": "Buffert"}


def test_okant_argument_avvisas_med_listan_over_de_riktiga():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["set_capacity"],
                            {"component": "B", "behaviour": "C",
                             "capacity": 3, "kapacitet": 3})
    assert "okant argument 'kapacitet'" in str(e.value)
    assert "set_capacity tar behaviour, capacity, component" in str(e.value)


def test_saknat_obligatoriskt_argument_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["set_capacity"], {"component": "B"})
    assert "obligatoriskt argument 'behaviour' saknas" in str(e.value)
    assert "obligatoriskt argument 'capacity' saknas" in str(e.value)


def test_fel_typ_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["set_capacity"],
                            {"component": "B", "behaviour": "C",
                             "capacity": "tolv"})
    assert "forvantade integer, fick str" in str(e.value)


def test_bool_raknas_inte_som_kapacitet():
    """True ar en int i Python. Som antal platser ar det ett modellfel."""
    with pytest.raises(V.Argumentfel):
        V.validera_argument(V.REGISTER["set_capacity"],
                            {"component": "B", "behaviour": "C",
                             "capacity": True})
    assert V.validera_argument(
        V.REGISTER["set_capacity"],
        {"component": "B", "behaviour": "C", "capacity": 3})["capacity"] == 3


def test_ett_slag_utanfor_enumen_avvisas_innan_kod_genereras():
    """Slaget skrivs som en ren strangliteral i mallen. Enumen ar sparren."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["list_transport_behaviours"],
                            {"kind": "conveyor"})
    assert "inte ett av" in str(e.value)
    # Och den korrekta halvan: varje slag i tabellen slapps igenom.
    for slag in T.SLAGNAMN:
        V.validera_argument(V.REGISTER["list_transport_behaviours"],
                            {"kind": slag})


def test_minst_ett_av_interval_och_limit_kravs():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["set_product_feed"],
                            {"component": "M", "behaviour": "PC"})
    assert "minst ett av interval, limit" in str(e.value)
    V.validera_argument(V.REGISTER["set_product_feed"],
                        {"component": "M", "behaviour": "PC", "limit": 1})


def test_tom_tillstandslista_avvisas():
    """En tom lista hade gett ett svar utan matning som sag ut som en matning."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["station_state_times"],
                            {"component": "S", "behaviour": "St", "states": []})
    assert "minst 1 varden" in str(e.value)
    V.validera_argument(V.REGISTER["station_state_times"],
                        {"component": "S", "behaviour": "St",
                         "states": ["Busy"]})


def test_alla_problem_rapporteras_pa_en_gang():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["set_routing_target"],
                            {"component": 1, "port": 2})
    # 1 okant (port) + 2 saknade (behaviour, connector) + 1 feltypad (component)
    assert len(e.value.problem) == 4


def test_argumenten_provas_innan_nagon_kod_genereras(utf, brygga):
    with pytest.raises(V.Argumentfel):
        utf.utfor("get_capacity", {"komponent": "B"})
    assert brygga.logg == [], "bryggan far inte ha rorts vid ett argumentfel"


# ---- 3. routingen --------------------------------------------------------

@pytest.mark.parametrize("namn", sorted(EXEMPEL))
def test_varje_verktyg_routas_efter_sin_deklarerade_effect(namn, utf, brygga):
    v = V.REGISTER[namn]
    utf.utfor(namn, EXEMPEL[namn][0])
    assert brygga.op_lista == [V.OP_FOR_EFFECT[v.effect]]


@pytest.mark.parametrize("namn", transportnamn())
def test_ingen_handlare_kan_se_bryggan(namn):
    p = list(inspect.signature(V.CODE_GEN_HANDLERS[namn]).parameters.values())
    assert [x.name for x in p] == ["argument"]
    assert p[0].kind is p[0].POSITIONAL_OR_KEYWORD


def test_operationsnamnen_star_inte_i_domanmodulen():
    """Sokvagen ut ur tjansten far ha exakt en ingang: utforare.py."""
    sokvag = os.path.join(_ROT, "svc", "vc_assist_svc", "verktyg",
                          "transport.py")
    with open(sokvag, encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    konstanter = [n.value for n in ast.walk(trad)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "exec" not in konstanter
    assert "exec_queue" not in konstanter


def test_ett_skrivande_verktyg_koas_och_kan_godkannas(utf, brygga):
    r = utf.utfor("set_capacity",
                  {"component": "Buffert", "behaviour": "C", "capacity": 12})
    assert r.koad and r.op == "exec_queue" and r.qid == "q1"
    assert brygga.logg[0][1]["desc"] == (
        "set_capacity(behaviour='C', capacity=12, component='Buffert')")
    klar = utf.godkann("q1")
    assert brygga.op_lista == ["exec_queue", "queue_approve", "queue_list"]
    assert klar.resultat["set"] is True


def test_en_kopost_som_inte_gick_igenom_raknas_inte_som_lyckad(utf, brygga):
    utf.utfor("set_routing_target",
              {"component": "V", "behaviour": "R", "connector": 1})
    brygga.nasta_utfall = "failed"
    with pytest.raises(V.Svarsfel) as e:
        utf.godkann("q1")
    assert "ended as 'failed'" in str(e.value)


def test_ett_lasande_verktyg_lamnar_ett_provat_resultat(utf):
    r = utf.utfor("station_statistics", {"component": "Station"})
    assert r.op == "exec" and not r.koad
    assert set(r.resultat) == {"component", "stations", "antal", "avkortad"}


def test_ett_svar_som_inte_haller_schemat_avvisas(utf, brygga, monkeypatch):
    monkeypatch.setattr(brygga, "_resultat", lambda args: {"antal": 1})
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("layout_statistics", {})
    assert "stations saknas" in str(e.value)


def test_tyst_stdout_ar_inte_ett_godkannande(utf, brygga, monkeypatch):
    monkeypatch.setattr(brygga, "_resultat", lambda args: None)
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("station_statistics", {"component": "S"})
    assert "not JSON" in str(e.value)


# ---- 4. formagegrinden ---------------------------------------------------

def test_full_rapport_slar_pa_alla_transportverktyg():
    u = V.urval_ur_rapport(full_rapport(), V.REGISTER)
    for namn in transportnamn():
        assert u.pa(namn), u.skal(namn)


def test_saknad_yta_slar_av_precis_de_verktyg_som_ror_den():
    r = full_rapport()
    r["ytor"]["comp.findBehaviour"] = {"finns": False, "typ": None}
    u = V.urval_ur_rapport(r, V.REGISTER)
    assert not u.pa("set_capacity")
    assert "comp.findBehaviour" in u.skal("set_capacity")
    assert "finns inte i denna VC" in u.skal("set_capacity")
    # Grannen ror inte ytan och ska vara kvar.
    assert u.pa("layout_statistics")
    assert u.pa("list_processes")


def test_oprovad_yta_raknas_som_saknad():
    """36_versioner.md: okant behandlas som saknat. Aldrig gissa."""
    r = full_rapport()
    r["ytor"]["comp.Behaviours"] = {"finns": None,
                                    "varfor": "inget comp att prova mot"}
    u = V.urval_ur_rapport(r, V.REGISTER)
    assert not u.pa("station_statistics")
    assert "oprovad" in u.skal("station_statistics")


def test_utan_rapport_ar_allt_avslaget():
    u = V.urval_ur_rapport(None, V.REGISTER)
    for namn in transportnamn():
        assert not u.pa(namn)
        assert "ingen formagerapport" in u.skal(namn)


def test_avstangt_verktyg_kastar_med_skal_innan_kod_genereras(brygga):
    r = full_rapport()
    r["ytor"]["comp.Properties"] = {"finns": False, "typ": None}
    u = V.Utforare(brygga, V.urval_ur_rapport(r, V.REGISTER))
    with pytest.raises(V.Avstangt) as e:
        u.utfor("list_transport_parameters", {"component": "Bana 1"})
    assert "comp.Properties" in str(e.value)
    assert brygga.logg == [], "ett avstangt verktyg far inte na bryggan"


def test_avstangda_verktyg_exponeras_aldrig_for_modellen():
    r = full_rapport()
    r["ytor"]["comp.Properties"] = {"finns": False, "typ": None}
    u = V.urval_ur_rapport(r, V.REGISTER)
    namn = {f["function"]["name"] for f in u.openai_verktyg(V.REGISTER)}
    assert "list_transport_parameters" not in namn
    assert "set_transport_parameter" not in namn
    assert "station_statistics" in namn


# ---- 5. korsprovet mot bryggans skrivgrind -------------------------------

@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_varje_verktygs_kod_domes_precis_som_dess_effect(namn, argument):
    v = V.REGISTER[namn]
    dom = skrivgrind.granska(kod_for(namn, argument))
    if v.effect == "read":
        assert not dom.skriver, (
            "%s ar read men bryggans skrivgrind skulle avvisa dess kod: %s"
            % (namn, dom.skal))
    else:
        assert dom.skriver, (
            "%s ar write men bryggans skrivgrind ser ingen andring; da skulle "
            "koden kunna kora genom exec utan godkannande" % namn)


def test_korsprovet_mot_skrivgrinden_i_siffror():
    """Den matta raden till rapporten: bada talen ska vara noll."""
    fel_lasande, fel_skrivande = [], []
    for namn, argument in ANROP:
        skriver = skrivgrind.granska(kod_for(namn, argument)).skriver
        if V.REGISTER[namn].effect == "read" and skriver:
            fel_lasande.append(namn)
        if V.REGISTER[namn].effect == "write" and not skriver:
            fel_skrivande.append(namn)
    assert (fel_lasande, fel_skrivande) == ([], []), (
        "lasande som flaggas: %s; skrivande som slipper igenom: %s"
        % (fel_lasande, fel_skrivande))


def test_skrivgrinden_kan_falla_at_bada_hallen():
    """Trasig fixtur: grinden ovan maste kunna doma at bada hallen (S2)."""
    lasande = kod_for("station_statistics",
                      V.validera_argument(V.REGISTER["station_statistics"],
                                          {"component": "S"}))
    assert not skrivgrind.granska(lasande).skriver
    assert skrivgrind.granska(lasande + "b.Capacity = 1\n").skriver


def test_ingen_skrivande_mall_dodar_pumpen():
    """app.save() stoppar simuleringen och dodar bryggan (skrivgrind.py).

    Ingen mall i den har domanen ror den vagen, och det ska den inte borja
    gora obemarkt.
    """
    for namn, argument in ANROP:
        assert skrivgrind.dodar_pumpen(kod_for(namn, argument)) == [], namn


def test_ingen_mall_skapar_ett_skriptbeteende():
    """Ett skriptbeteende stoppar simuleringen mitt i bryggans eget svar."""
    for namn, argument in ANROP:
        assert skrivgrind.skapar_skriptbeteende(kod_for(namn, argument)) == [], namn


# ---- 6. korsprovet mot API-indexet ---------------------------------------

def _granska_api(kod):
    return VALIDATOR.granska(kod)


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_ingen_mall_bar_ett_uppfunnet_vc_namn(namn, argument):
    g = _granska_api(kod_for(namn, argument))
    assert g.fel == [], "%s: %s" % (namn, "; ".join(str(f) for f in g.fel))


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_inget_namn_i_mallen_ar_obestambart_utom_bryggans_egen_hjalpare(
        namn, argument):
    """_s laggs i exec-globalerna av pump.py och star i ingen API-kalla.

    Allt ANNAT som validatorn inte kan avgora ar en lucka, inte ett
    godkannande (I3, fail-closed).
    """
    ovriga = [str(o) for o in _granska_api(kod_for(namn, argument)).obestambara
              if o.namn != "_s"]
    assert ovriga == [], "%s: %s" % (namn, "; ".join(ovriga))


def test_korsprovet_mot_api_indexet_i_siffror():
    """Den matta raden till rapporten: noll fel, noll obestambara utover _s."""
    fel, obestambara, kontrollerade = [], [], []
    for namn, argument in ANROP:
        g = _granska_api(kod_for(namn, argument))
        fel += [(namn, str(f)) for f in g.fel]
        obestambara += [(namn, str(o)) for o in g.obestambara
                        if o.namn != "_s"]
        kontrollerade.append(g.kontrollerade_namn)
    assert (fel, obestambara) == ([], [])
    assert len(kontrollerade) == 43, "43 anrop over 25 verktyg"
    assert sum(kontrollerade) >= 500, (
        "grinden kontrollerade bara %d namn; da mater den inte sin egen "
        "storhet" % sum(kontrollerade))
    assert min(kontrollerade) >= 5, (
        "nagot anrop fick bara %d namn kontrollerade" % min(kontrollerade))


def test_api_grinden_faller_pa_ett_uppfunnet_namn_i_mallens_egen_form():
    """Trasig fixtur. Utan den ar korsprovet ovan en grind som aldrig fallit.

    Formen ar mallarnas egen: komponenten hamtas INLINE, sa validatorn typar
    k till vcComponent och ser resten.
    """
    ratt = ("k = getApplication().findComponent(_s(u\"A\"))\n"
            "b = k.findBehaviour(_s(u\"B\"))\n"
            "x = b.Capacity\n")
    fel = ratt.replace("b.Capacity", "b.ConveyorSpeed")
    assert _granska_api(ratt).fel == []
    trasig = _granska_api(fel).fel
    assert len(trasig) == 1
    assert "ConveyorSpeed" in str(trasig[0])


def test_api_grinden_blir_blind_om_komponenten_gar_genom_en_hjalpare():
    """Skalet till att mallarna anropar getApplication() inline, MATT.

    Samma uppfunna namn som faller ovan slipper igenom sa fort komponenten
    hamtas ur en funktion koden sjalv definierar: validatorn harleder ingen
    returtyp darur. Provet finns for att skalet ska sta kvar nar nagon
    frestas att stada in uppslaget i en hjalpare igen.
    """
    genom_hjalpare = ("def _komp(namn):\n"
                      "    return getApplication().findComponent(namn)\n"
                      "k = _komp(_s(u\"A\"))\n"
                      "b = k.findBehaviour(_s(u\"B\"))\n"
                      "x = b.ConveyorSpeed\n")
    g = _granska_api(genom_hjalpare)
    assert g.fel == [], "om detta borjar falla har validatorn blivit battre"
    assert g.kontrollerade_namn <= 2, (
        "hjalparvagen ska lamna nastan allt okontrollerat; fick %d"
        % g.kontrollerade_namn)


@pytest.mark.parametrize("namn", transportnamn())
def test_mallen_hamtar_komponenten_inline_och_inte_genom_en_hjalpare(namn):
    """Den mekaniska halften av provet ovan: ingen mall far anvanda _komp."""
    kod = kod_for(namn, V.validera_argument(V.REGISTER[namn],
                                            EXEMPEL[namn][-1]))
    assert "_komp(" not in kod
    assert "_app(" not in kod


# ---- 7. tabellen SLAG ----------------------------------------------------

def _typer_med_ytan(ytor):
    return sorted(t for t in INDEX.typer
                  if all(y in INDEX.typytan(t) for y in ytor))


# Facit for tabellens urskiljningsformaga, MATT mot api_index 2026-09-04.
# Faller provet nedan har antingen API-indexet eller tabellen andrats, och
# beskrivningen i transport.py ar inte langre sann.
SLAGFACIT = {
    "container": ["vcComponentCreator", "vcContainer",
                  "vcInterpolatingTransportController", "vcMotionPath",
                  "vcPatternContainer", "vcRoutingRule", "vcTransport"],
    "flow": ["vcComponentCreator", "vcComponentFlowProxy", "vcContainer",
             "vcFlow", "vcInterpolatingTransportController", "vcMotionPath",
             "vcPatternContainer", "vcProductCreator", "vcRoutingRule",
             "vcTransport"],
    "statistics": ["vcStatistics"],
    "sensor": ["vcProcessPointSensor"],
    "routing_rule": ["vcRoutingRule"],
    "product_creator": ["vcProductCreator"],
    "component_creator": ["vcComponentCreator"],
    "process_controller": ["vcProcessController"],
    "process_executor": ["vcProcessExecutor"],
    "transport_node": ["vcTransportNode"],
}


def test_varje_slag_traffar_de_typer_det_mattes_mot():
    assert set(SLAGFACIT) == set(T.SLAGNAMN)
    for slag, ytor in T.SLAG:
        assert _typer_med_ytan(ytor) == SLAGFACIT[slag], slag


def test_atta_av_tio_slag_pekar_ut_exakt_en_typ():
    """De tva familjerna ar container och flow, och bara de.

    Ett verktyg som kraver ett entydigt slag vet vilken yta objektet bar; ett
    som kraver en familj vet det inte och maste fraga med hasattr.
    """
    entydiga = sorted(s for s, t in SLAGFACIT.items() if len(t) == 1)
    familjer = sorted(s for s, t in SLAGFACIT.items() if len(t) > 1)
    assert familjer == ["container", "flow"]
    assert len(entydiga) == 8


def test_ett_uppfunnet_ytpar_traffar_ingenting():
    """Trasig fixtur for tabellen: en yta som inte finns valjer ingen typ."""
    assert _typer_med_ytan(("ConveyorSpeed", "Accumulating")) == []


@pytest.mark.parametrize("slag,ytor", list(T.SLAG))
def test_varje_ytattribut_i_tabellen_finns_i_api_indexet(slag, ytor):
    """En yta som inte star i indexet ar ett uppfunnet namn (I9)."""
    for y in ytor:
        assert INDEX.symboler_med_namn(y), "%s: %s finns inte" % (slag, y)


def test_mallens_slagfunktion_genereras_ur_tabellen():
    """Kod och enum far inte kunna drifta isar."""
    kod = kod_for("station_statistics",
                  V.validera_argument(V.REGISTER["station_statistics"],
                                      {"component": "S"}))
    for slag, ytor in T.SLAG:
        assert 'slaglista.append("%s")' % slag in kod
        for y in ytor:
            assert 'hasattr(b, "%s")' % y in kod
    assert (V.REGISTER["list_transport_behaviours"]
            .parameters["properties"]["kind"]["enum"]) == list(T.SLAGNAMN)


# ---- 8. den genererade kodens form --------------------------------------

@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_parsar_och_ar_py27_forenlig(namn, argument):
    kod = kod_for(namn, argument)
    for nod in ast.walk(ast.parse(kod)):
        assert type(nod).__name__ not in FORBJUDNA_NODER, (
            "%s: %s finns inte i Python 2.7" % (namn, type(nod).__name__))
    assert kod.startswith("from __future__ import print_function\n")


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_ar_ren_ascii(namn, argument):
    kod_for(namn, argument).encode("ascii")


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_svarar_pa_bryggans_svarskanal(namn, argument):
    kod = kod_for(namn, argument)
    assert "def _svara(o):" in kod
    assert "print(json.dumps(o, sort_keys=True))" in kod
    assert re.search(r"^\s*_svara\(", kod, re.M), (
        "%s: mallen anropar aldrig _svara och lamnar alltsa ingen JSON-rad"
        % namn)


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_anvander_bara_namn_den_sjalv_eller_vc_definierar(namn, argument):
    """Ett stavfel i en mall ska falla har, inte som NameError inne i VC."""
    trad = ast.parse(kod_for(namn, argument))
    definierade = set()
    for nod in ast.walk(trad):
        if isinstance(nod, (ast.FunctionDef, ast.ClassDef)):
            definierade.add(nod.name)
        elif isinstance(nod, ast.Name) and isinstance(nod.ctx, ast.Store):
            definierade.add(nod.id)
        elif isinstance(nod, ast.arg):
            definierade.add(nod.arg)
        elif isinstance(nod, (ast.Import, ast.ImportFrom)):
            for a in nod.names:
                definierade.add(a.asname or a.name.split(".")[0])
    tillatna = definierade | VC_GLOBALER | PY2_INBYGGDA | set(dir(builtins))
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Name) and isinstance(nod.ctx, ast.Load):
            assert nod.id in tillatna, "%s: okant namn %s" % (namn, nod.id)


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_mallen_bar_ingen_oanvand_hjalpare(namn, argument):
    """Genererad kod ar ocksa kod: oanvant ar skuld (S3)."""
    trad = ast.parse(kod_for(namn, argument))
    anvanda = {n.id for n in ast.walk(trad)
               if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for nod in trad.body:
        if isinstance(nod, ast.FunctionDef):
            assert nod.name in anvanda, "%s: %s definieras men anvands aldrig" % (
                namn, nod.name)


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_all_text_in_i_vc_gar_genom_s(namn, argument):
    """M-05: unicode in i VC 4.10:s bindning ger SystemError."""
    kod = kod_for(namn, argument)
    for m in re.finditer(r'u"(?:[^"\\]|\\.)*"', kod):
        start = kod.rfind("_s(", 0, m.start())
        assert start != -1 and kod[start:m.start()] == "_s(", (
            "%s: unicode-literal utan _s() runt sig: %s" % (namn, m.group(0)))


def test_literalerna_overlever_citattecken_och_svenska_tecken():
    kod = kod_for("get_transport_parameter",
                  V.validera_argument(
                      V.REGISTER["get_transport_parameter"],
                      {"component": 'Bana "ett" åäö',
                       "parameter": "Hastighet"}))
    ast.parse(kod)
    kod.encode("ascii")
    # json.dumps(ensure_ascii=True) ger \uXXXX, som Python laser likadant i
    # 2.7 och 3.x. Det ar darfor mallarna kan vara ren ASCII och anda bara
    # svenska namn.
    assert r'_s(u"Bana \"ett\" \u00e5\u00e4\u00f6")' in kod


@pytest.mark.parametrize("namn", transportnamn())
def test_varje_verktyg_som_lamnar_en_lista_bar_ocksa_taket(namn):
    """Regeln, mekaniskt: en lista utan tak kan spranga bryggans kropp.

    Taket ligger pa den lista vars langd foljer LAYOUTENS storlek. Tre slags
    listor slipper: den som schemat sjalv begransar med maxItems, de nastlade
    som foljer ett enda objekts egen definition, och ingen fjarde - samma
    husregel som scen.py och granssnitt.py. En klippt lista utan avkortad ar
    en tyst nedgradering (I3).
    """
    v = V.REGISTER[namn]
    listor = [f for f, s in v.returns["properties"].items()
              if "array" in (s["type"] if isinstance(s["type"], list)
                             else [s["type"]])
              and "maxItems" not in s]
    if not listor:
        assert "avkortad" not in v.returns["properties"], (
            "%s bar avkortad utan att lamna nagon lista" % namn)
        return
    assert "avkortad" in v.returns["properties"], (
        "%s lamnar listorna %s utan att kunna saga att de klipptes" % (
            namn, listor))
    assert "avkortad" in v.returns["required"], namn
    kod = "\n".join(kod_for(namn, V.validera_argument(v, rat))
                    for rat in EXEMPEL[namn])
    assert ">= %d" % kodmall.MAX_POSTER in kod
    assert "kodmall.MAX_POSTER" in kod, "talet ska bara sin harkomst i mallen"
    assert '"avkortad": avkortad' in kod


def test_de_enda_verktygen_utan_lista_ar_de_som_svarar_om_ETT_ting():
    utan = sorted(n for n in transportnamn()
                  if "avkortad" not in V.REGISTER[n].returns["properties"]
                  and V.REGISTER[n].effect == "read")
    assert utan == ["get_transport_parameter", "transport_behaviour_info"]


# ---- 9. statistiken som ogats ravara ------------------------------------

def _stationsrad(post):
    """Ogats STATION-rad byggd RAKT ur verktygets falt. Ingen omraekning."""
    return "STATION %s in=%d out=%d avg=%.3fs min=%.3fs max=%.3fs" % (
        post["station"], post["in"], post["out"],
        post["avg_s"], post["min_s"], post["max_s"])


def _rapport():
    return oga_kontrakt.Rapport("prov", "2026-09-04", 1.0, 1, 1.0)


def test_stationsposten_gar_rakt_in_i_ogats_grammatik():
    """41_ogat_kontrakt.md: STATION <namn> in=.. out=.. avg=..s min=..s max=..s

    Provet bygger raden ur ETT syntetiskt svar som haller verktygets eget
    returns-schema, sa den dagen falten byter namn faller detta.
    """
    svar = svar_for(V.REGISTER["station_statistics"])
    post = dict(svar["stations"][0], station="Bana1")
    _rapport().sektion("THROUGHPUT").rad(_stationsrad(post))


def test_bada_statistikverktygen_lamnar_samma_faltnamn():
    """Tva namn pa samma storhet blir tva storheter sa fort nagon andrar den."""
    en = V.REGISTER["station_statistics"].returns["properties"]["stations"]
    alla = V.REGISTER["layout_statistics"].returns["properties"]["stations"]
    assert en["items"] == alla["items"]
    for falt in ("station", "in", "out", "avg_s", "min_s", "max_s"):
        assert falt in en["items"]["properties"], falt


def test_ogats_grammatik_faller_pa_ett_omdopt_falt():
    """Trasig fixtur: grinden ovan maste kunna falla."""
    post = {"station": "Bana1", "in": 3, "out": 2,
            "avg_s": 1.0, "min_s": 0.5, "max_s": 2.0}
    with pytest.raises(oga_kontrakt.Kontraktsfel):
        _rapport().sektion("THROUGHPUT").rad(
            "STATION %s inn=%d out=%d avg=%.3fs min=%.3fs max=%.3fs"
            % (post["station"], post["in"], post["out"], post["avg_s"],
               post["min_s"], post["max_s"]))


def test_ett_stationsnamn_med_blanksteg_ryms_inte_i_raden():
    """MATT begransning i ogats grammatik, inte i verktyget.

    STATION-raden matchar \\S+ som namn. Verktyget lamnar komponentnamnet
    orort - det ar sanningen ur VC - och den som skriver ogats rad far avgora
    hur ett namn med blanksteg ska bara sig. Provet finns for att den
    begransningen ska vara SKRIVEN nagonstans i stallet for att upptackas som
    ett tyst bortfall.
    """
    with pytest.raises(oga_kontrakt.Kontraktsfel):
        _rapport().sektion("THROUGHPUT").rad(
            "STATION Bana 1 in=1 out=1 avg=1.000s min=1.000s max=1.000s")


def test_statistikfalten_kommer_ur_deklarerade_egenskaper_i_api_indexet():
    """Varje tal i STATION-raden ska ha ett namngivet ursprung i VC.

    De atta falten lases ur vcStatistics egenskaper med access R. Inget av dem
    ar harlett eller omraknat - siffrans harkomst hor till siffran.
    """
    kod = kod_for("station_statistics",
                  V.validera_argument(V.REGISTER["station_statistics"],
                                      {"component": "S"}))
    yta = INDEX.typytan("vcStatistics")
    for falt, egenskap in (("in", "ComponentsArrived"),
                           ("out", "ComponentsDeparted"),
                           ("avg_s", "ComponentsAverageTime"),
                           ("min_s", "ComponentMinTime"),
                           ("max_s", "ComponentMaxTime"),
                           ("current", "ComponentsCurrent"),
                           ("min_count", "ComponentMinCount"),
                           ("max_count", "ComponentMaxCount")):
        assert egenskap in yta, egenskap
        assert yta[egenskap][0].sort == "egenskap"
        assert yta[egenskap][0].atkomst == "R"
        assert '"%s": b.%s' % (falt, egenskap) in kod


def test_ingen_mall_ror_de_tvetydiga_statistiknamnen():
    """MATT: kallan deklarerar dem som <method> med atkomsten i parameterfaltet.

    BusyPercentage, Utilization och deras slaktingar gar darfor inte att avgora
    som egenskap eller metod ur kallan. En mall som gissade fel hade lamnat en
    bunden metod dar ett tal skulle sta - ett varde som ser ut som en matning.
    Verktyget station_state_times gar i stallet genom getPercentage/getTime,
    som kallan deklarerar entydigt med parametern String state.
    """
    tvetydiga = [n for n, s in INDEX.typytan("vcStatistics").items()
                 if s[0].sort == "metod" and (s[0].signatur or "") in
                 ("R", "RW", "")]
    assert "Utilization" in tvetydiga and "BusyPercentage" in tvetydiga
    for namn, argument in ANROP:
        kod = kod_for(namn, argument)
        for t in tvetydiga:
            # Ordgrans: .Statements ar inte .State, och en delstrangsjamforelse
            # hade anklagat varje mall som laser en processrutins steg.
            assert not re.search(r"\.%s\b" % re.escape(t), kod), (
                "%s ror %s" % (namn, t))
    kod = kod_for("station_state_times",
                  V.validera_argument(V.REGISTER["station_state_times"],
                                      {"component": "S", "behaviour": "St",
                                       "states": ["Busy"]}))
    assert "b.getPercentage(namn)" in kod and "b.getTime(namn)" in kod


def test_utan_states_lamnar_verktyget_upptackt_men_ingen_matning():
    """Fail-closed: hellre en tom matning an en gissad tillstandslista."""
    utan = kod_for("station_state_times",
                   V.validera_argument(V.REGISTER["station_state_times"],
                                       {"component": "S", "behaviour": "St"}))
    assert "getPercentage" not in utan
    assert "for st in b.States:" in utan
    assert '"times": rader' in utan and "rader = []" in utan
    med = kod_for("station_state_times",
                  V.validera_argument(V.REGISTER["station_state_times"],
                                      {"component": "S", "behaviour": "St",
                                       "states": ["Busy"]}))
    assert "getPercentage" in med
