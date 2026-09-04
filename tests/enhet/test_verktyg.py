# -*- coding: utf-8 -*-
"""L0/L1/L2 for verktygsregistret (fas 4-5, docs/spec/45_verktyg.md).

Kors utan VC. Tre saker provas, och den mellersta ar den viktigaste:

1. SCHEMAT. Varje verktyg bar effect, mode, returns, since och kraver, och
   argument provas mot schemat innan nagot skickas.
2. ROUTINGEN. effect=read -> exec, effect=write -> exec_queue, mekaniskt.
   Testerna visar att det inte GAR att kringga, inte bara att det ar
   forbjudet.
3. KORSPROVET MOT SKRIVGRINDEN. Varje lasande verktygs genererade kod kors
   genom bryggans egen skrivgrind.granska() och far INTE domas som skrivande;
   varje skrivande verktygs kod MASTE domas som skrivande. Det ar det enda
   provet som binder ihop tjanstens routing med bryggans andra forsvarslinje.

95_testprotokoll.md: varje grind har ocksa en trasig fixtur som MASTE falla.
En grind som aldrig fallit ar oprovad.
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

import formaga                                   # noqa: E402
import skrivgrind                                # noqa: E402
from vc_assist_svc import verktyg as V           # noqa: E402
from vc_assist_svc.verktyg import kodmall            # noqa: E402


# ---- fixturer ------------------------------------------------------------

# Ett minimalt och ett maximalt anrop per verktyg. Listan MASTE tacka hela
# registret; testet nedan faller annars. Skalet: ett korsprov som inte tacker
# allt mater fel, och ett nytt verktyg ska inte kunna slinka forbi grinden.
EXEMPEL = {
    "list_components": [{}, {"name_contains": "Conveyor"}],
    "find_component": [{"name": "Robot"}],
    "component_info": [{"name": "Robot"}],
    "load_component": [{"uri": "file:///c/x.vcm"},
                       {"uri": "file:///c/x.vcm", "name": "Bana 1"}],
    "clone_component": [{"name": "Robot", "new_name": "Robot 2"}],
    "delete_component": [{"name": "Robot"}],
    "get_transform": [{"component": "Robot"},
                      {"component": "Robot", "node": "Joint1", "frame": "parent"}],
    "set_transform": [{"component": "Robot", "position": [1.0, 2.0, 3.0]},
                      {"component": "Robot", "node": "J", "wpr": [0, 0, 90]},
                      {"component": "R", "position": [1, 2, 3], "wpr": [0, 0, 90]}],
    "get_bounds": [{"component": "Robot"}, {"component": "Robot", "node": "J"}],
    "list_nodes": [{"component": "Robot"}],
    "find_node": [{"component": "Robot", "node": "Joint1"}],
    "get_property": [{"component": "Robot", "property": "Speed"}],
    "set_property": [{"component": "R", "property": "Speed", "value": 1.5},
                     {"component": "R", "property": "Namn", "value": "Bana"},
                     {"component": "R", "property": "On", "value": True}],
    "list_properties": [{"component": "Robot"}],
    "save_layout": [{"uri": "file:///c/lina.vcmx"}],
    "list_interfaces": [{"component": "Robot"}],
    "interface_info": [{"component": "Robot", "interface": "Flow"}],
    "can_connect": [{"component": "A", "interface": "I",
                     "other_component": "B", "other_interface": "J"}],
    "connect": [{"component": "A", "interface": "I",
                 "other_component": "B", "other_interface": "J"}],
    "disconnect": [{"component": "A", "interface": "I"},
                   {"component": "A", "interface": "I",
                    "other_component": "B", "other_interface": "J"}],
    "list_connections": [{}, {"component": "A"}],
}

# Namn den genererade koden far anvanda utan att sjalv definiera dem.
# getApplication kommer ur "from vcScript import *" i bryggans skript, och
# _s laggs i exec-globalerna av pump.py vid varje korning.
VC_GLOBALER = {"getApplication", "_s", "json", "vcVector", "vcMatrix"}

# Inbyggda namn som bara finns i Python 2. Mallarna ror dem enbart inne i
# try/except NameError, precis som skrivgrind.py sjalv gor.
PY2_INBYGGDA = {"unicode", "long", "basestring", "xrange"}

# Konstruktioner som inte finns i Python 2.7. Koden kors i VC 4.10:s
# Stackless 2.7 och i VC 5.0:s 3.x (36_versioner.md), sa den maste ga i bada.
FORBJUDNA_NODER = ("JoinedStr", "FormattedValue", "NamedExpr", "AnnAssign",
                   "AsyncFunctionDef", "Await", "AsyncFor", "AsyncWith",
                   "Match", "TryStar")


def alla_anrop():
    """(namn, argument) for varje exempel, med default-varden ifyllda."""
    for namn in sorted(EXEMPEL):
        for rat in EXEMPEL[namn]:
            yield namn, V.validera_argument(V.REGISTER[namn], rat)


def kod_for(namn, argument):
    return V.CODE_GEN_HANDLERS[namn](argument)


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
        n = s.get("minItems", 1)
        return [_syntetiskt(s["items"]) for _ in range(n)]
    if typ == "object":
        return {n: _syntetiskt(us) for n, us in s.get("properties", {}).items()}
    raise AssertionError("okand type %r i schemat" % (typ,))


def svar_for(verktyg):
    r = verktyg.returns
    return {n: _syntetiskt(r["properties"][n]) for n in r["required"]}


class Attrappbrygga(object):
    """Talar bryggans klientyta utan VC (L2). Loggar VARJE anrop."""

    def __init__(self, register=None):
        self.logg = []
        self._register = register or V.REGISTER
        self.qid = 0
        self.ko = []          # bryggans ko: godkannandet kvitteras, pumpen kor
        self.nasta_utfall = "done"   # satts till "failed" av det test som vill det

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
            # Bryggan KVITTERAR bara; pumpen kor koden (M-13). Attrappen
            # harmar det genom att lata posten bli klar vid nasta queue_list.
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
                ut.append(dict((k, v) for k, v in post.items()
                               if not k.startswith("_")))
            return {"v": 1, "ok": True, "stdout": "", "result": {"queue": ut}}
        raise AssertionError("attrappen kan inte %r" % (op,))

    def _resultat(self, args):
        """Bygger ett svar ur det verktyg vars beskrivning star i desc."""
        namn = (args.get("desc") or "").split("(")[0]
        return svar_for(self._register[namn])

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


# ---- 1. registret och schemat -------------------------------------------

def test_registret_ar_fullt_och_delat_i_tva():
    # Ett MATT antal, inte ett tak. Raden ska andras MEDVETET nar en doman
    # laggs till - det ar hela poangen: ett verktyg far aldrig registrera sig
    # av misstag.
    assert len(V.REGISTER) == 121, (
        "registret har %d verktyg. Domaner: %r"
        % (len(V.REGISTER),
           sorted(set(v.doman for v in V.REGISTER.values()))))
    assert len(V.CODE_GEN_HANDLERS) + len(V.DATA_HANDLERS) == len(V.REGISTER)
    # DATA_HANDLERS ar tomt: 45_verktyg.md lagger allt som ror SCENEN i
    # kodgenereringsgrenen. Data-verktygen hor till katalog, kunskap och plc.
    assert len(V.DATA_HANDLERS) == 13, \
        "catalog 3 + 2 mot installerade biblioteket, knowledge 4, eyes 3, plus ett"
    assert set(V.CODE_GEN_HANDLERS) | set(V.DATA_HANDLERS) == set(V.REGISTER)


def test_de_tva_domaner_filen_ager_ligger_i_registret():
    """Filen ager scene och composition. Registret bar fler domaner an sa,
    fyllda av andra celler - det ar inte ett fel utan meningen."""
    mina = set(v.doman for v in mitt_register().values())
    assert mina == set(MINA_DOMANER)
    assert len(mitt_register()) == 21, "scene har 15 verktyg och composition 6"


MINA_DOMANER = ("scene", "composition")


def mitt_register():
    """De domaner DEN HAR filen ager.

    Registret ar processglobalt och fylls av alla domanmoduler. Ovriga domaner
    har egna testfiler med egna exempellistor; att krava exempel for dem har
    skulle mata grannens arbete och falla varje gang nagon lagger till ett
    verktyg nagon annanstans.
    """
    return dict((n, v) for n, v in V.REGISTER.items() if v.doman in MINA_DOMANER)


def test_exempellistan_tacker_de_domaner_filen_ager():
    """En lista som inte tacker allt mater fel. Nytt verktyg -> nytt exempel."""
    assert set(EXEMPEL) == set(mitt_register())


@pytest.mark.parametrize("namn", sorted(V.REGISTER))
def test_varje_verktyg_bar_de_obligatoriska_falten(namn):
    v = V.REGISTER[namn]
    assert v.mode in ("data", "codegen")
    assert v.effect in ("read", "write")
    assert v.since == "4.10"
    assert v.kraver
    assert v.returns["required"]
    assert v.beskrivning.strip()


@pytest.mark.parametrize("namn", sorted(V.REGISTER))
def test_varje_kravd_yta_finns_i_formagerapportens_egen_lista(namn):
    """En yta grinden inte kan prova ar ingen grind (S2)."""
    kanda = {yta for yta, _o, _a in formaga.YTOR}
    for yta in V.REGISTER[namn].kraver:
        assert yta in kanda, "%s kraver %s som formaga.py inte provar" % (namn, yta)


def test_verktygsdefinitionen_gar_inte_att_andra_efteråt():
    """Kunde effect skrivas om vore routingregeln bara ett forslag."""
    with pytest.raises(AttributeError):
        V.REGISTER["list_components"].effect = "write"


def test_openai_formen_bar_inga_egna_nycklar():
    """Modellen ska se OpenAI-schemat, inte vara interna villkorsnycklar."""
    f = V.REGISTER["set_transform"].som_openai()
    assert f["type"] == "function"
    assert f["function"]["name"] == "set_transform"
    assert "x-minst-en-av" in V.REGISTER["set_transform"].parameters
    assert "x-minst-en-av" not in f["function"]["parameters"]


def test_ett_verktyg_med_trasigt_schema_avvisas_vid_definitionen():
    """Trasig fixtur for schemagrinden (95_testprotokoll.md)."""
    with pytest.raises(V.Schemafel) as e:
        V.Verktyg(namn="trasigt", beskrivning="x", mode="codegen",
                  effect="read",
                  parameters={"type": "object", "properties": {}},
                  returns={"type": "object", "properties": {}, "required": []},
                  since="4.10", kraver=("app.Components",), doman="prov",
                  timeout_ms=1000)
    assert "additionalProperties" in str(e.value)


def test_ett_verktyg_som_kraver_en_okand_yta_avvisas():
    with pytest.raises(V.Schemafel) as e:
        V.Verktyg(namn="trasigt", beskrivning="x", mode="codegen",
                  effect="read",
                  parameters={"type": "object", "properties": {},
                              "additionalProperties": False},
                  returns={"type": "object",
                           "properties": {"ok": {"type": "boolean",
                                                 "description": "x"}},
                           "required": ["ok"]},
                  since="4.10", kraver=("app.hittarPaSig",), doman="prov",
                  timeout_ms=1000)
    assert "app.hittarPaSig" in str(e.value)


def test_ett_data_verktyg_som_skriver_far_inte_ens_definieras():
    """data+write skulle ga forbi godkannandekon helt (I12)."""
    with pytest.raises(V.Schemafel) as e:
        V.Verktyg(namn="plc_deploy", beskrivning="x", mode="data",
                  effect="write",
                  parameters={"type": "object", "properties": {},
                              "additionalProperties": False},
                  returns={"type": "object",
                           "properties": {"ok": {"type": "boolean",
                                                 "description": "x"}},
                           "required": ["ok"]},
                  since="4.10", kraver=("app.Components",), doman="plc",
                  timeout_ms=1000)
    assert "kringgar godkannandekon" in str(e.value)


# ---- 2. argumentvalidering ----------------------------------------------

def test_ratt_argument_slapps_igenom_och_default_fylls_i():
    args = V.validera_argument(V.REGISTER["get_transform"], {"component": "R"})
    assert args == {"component": "R", "frame": "world"}


def test_okant_argument_avvisas_med_listan_over_de_riktiga():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["find_component"],
                            {"name": "R", "namn": "R"})
    assert "okant argument 'namn'" in str(e.value)
    assert "find_component tar name" in str(e.value)


def test_saknat_obligatoriskt_argument_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["find_component"], {})
    assert "obligatoriskt argument 'name' saknas" in str(e.value)


def test_fel_typ_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["find_component"], {"name": 17})
    assert "forvantade string, fick int" in str(e.value)


def test_bool_raknas_inte_som_heltal():
    """True ar en int i Python. Som antal ar det ett modellfel."""
    v = V.REGISTER["list_nodes"]
    prov = V.Verktyg(namn="prov_heltal", beskrivning="x", mode="codegen",
                     effect="read",
                     parameters={"type": "object", "additionalProperties": False,
                                 "properties": {"n": {"type": "integer",
                                                      "description": "x"}},
                                 "required": ["n"]},
                     returns=v.returns, since="4.10",
                     kraver=("app.Components",), doman="prov", timeout_ms=1)
    with pytest.raises(V.Argumentfel):
        V.validera_argument(prov, {"n": True})
    assert V.validera_argument(prov, {"n": 3}) == {"n": 3}


def test_enum_utanfor_listan_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["get_transform"],
                            {"component": "R", "frame": "varlden"})
    assert "inte ett av" in str(e.value)


def test_vektor_med_fel_antal_tal_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["set_transform"],
                            {"component": "R", "position": [1.0, 2.0]})
    assert "minst 3 varden" in str(e.value)


def test_alla_problem_rapporteras_pa_en_gang():
    """Modellen ska kunna ratta allt i ett svar, inte ett fel per varv."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["can_connect"],
                            {"component": 1, "granssnitt": "I"})
    assert len(e.value.problem) == 5   # 1 okant + 3 saknade + 1 feltypad


def test_minst_ett_av_position_och_wpr_kravs():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["set_transform"], {"component": "R"})
    assert "minst ett av position, wpr" in str(e.value)


def test_argument_som_hor_ihop_maste_komma_tillsammans():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(V.REGISTER["disconnect"],
                            {"component": "A", "interface": "I",
                             "other_component": "B"})
    assert "other_interface saknas" in str(e.value)


def test_argumenten_provas_innan_nagon_kod_genereras(utf, brygga):
    with pytest.raises(V.Argumentfel):
        utf.utfor("find_component", {"namn": "R"})
    assert brygga.logg == [], "bryggan far inte ha rorts vid ett argumentfel"


def test_okant_verktygsnamn_avvisas(utf, brygga):
    with pytest.raises(V.OkantVerktyg):
        utf.utfor("spawn_robot", {})
    assert brygga.logg == []


# ---- 3. routingregeln, och att den inte gar att kringga -------------------

def test_tabellen_ar_den_enda_regeln():
    assert dict(V.OP_FOR_EFFECT) == {"read": "exec", "write": "exec_queue"}


def test_tabellen_gar_inte_att_skriva_i():
    """Kunde en handlare skriva om tabellen vore regeln inte mekanisk."""
    with pytest.raises(TypeError):
        V.OP_FOR_EFFECT["read"] = "exec_queue"


def test_okand_effect_ger_fel_i_stallet_for_en_gissning():
    with pytest.raises(ValueError) as e:
        V.op_for_effect("sideeffect")
    assert "tabellen ar sluten" in str(e.value)


@pytest.mark.parametrize("namn", sorted(EXEMPEL))
def test_varje_verktyg_routas_efter_sin_deklarerade_effect(namn, utf, brygga):
    v = V.REGISTER[namn]
    utf.utfor(namn, EXEMPEL[namn][0])
    assert brygga.op_lista == [V.OP_FOR_EFFECT[v.effect]]


@pytest.mark.parametrize("namn", sorted(V.CODE_GEN_HANDLERS))
def test_ingen_handlare_kan_se_bryggan(namn):
    """Signaturen ar kontrollen: en handlare tar (argument) och inget mer."""
    p = list(inspect.signature(V.CODE_GEN_HANDLERS[namn]).parameters.values())
    assert [x.name for x in p] == ["argument"]
    assert p[0].kind is p[0].POSITIONAL_OR_KEYWORD


def test_en_handlare_med_extra_parameter_avvisas_vid_registrering():
    """Trasig fixtur for handlargrinden."""
    v = V.Verktyg(namn="prov_smitare", beskrivning="x", mode="codegen",
                  effect="read",
                  parameters={"type": "object", "properties": {},
                              "additionalProperties": False},
                  returns={"type": "object",
                           "properties": {"ok": {"type": "boolean",
                                                 "description": "x"}},
                           "required": ["ok"]},
                  since="4.10", kraver=("app.Components",), doman="prov",
                  timeout_ms=1)
    with pytest.raises(V.Schemafel) as e:
        V.registrera(v, lambda argument, klient: "")
    assert "ska ta exakt en" in str(e.value)
    assert "prov_smitare" not in V.REGISTER


def test_en_handlare_med_kwargs_avvisas():
    v = V.Verktyg(namn="prov_kwargs", beskrivning="x", mode="codegen",
                  effect="read",
                  parameters={"type": "object", "properties": {},
                              "additionalProperties": False},
                  returns={"type": "object",
                           "properties": {"ok": {"type": "boolean",
                                                 "description": "x"}},
                           "required": ["ok"]},
                  since="4.10", kraver=("app.Components",), doman="prov",
                  timeout_ms=1)
    with pytest.raises(V.Schemafel):
        V.registrera(v, lambda **argument: "")
    assert "prov_kwargs" not in V.REGISTER


MODULER_UTAN_LAGESVAL = ("scen.py", "granssnitt.py", "kodmall.py", "bas.py",
                         "register.py", "schema.py", "formagegrind.py")


@pytest.mark.parametrize("fil", MODULER_UTAN_LAGESVAL)
def test_operationsnamnen_star_bara_i_utforaren(fil):
    """Sokvagen ut ur tjansten far ha exakt en ingang."""
    sokvag = os.path.join(_ROT, "svc", "vc_assist_svc", "verktyg", fil)
    with open(sokvag, encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    konstanter = [n.value for n in ast.walk(trad)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "exec" not in konstanter
    assert "exec_queue" not in konstanter


def test_en_handlare_som_lamnar_skrivande_kod_routas_anda_som_read(utf, brygga,
                                                                  monkeypatch):
    """Handlarens INNEHALL far inte kunna flytta ett verktyg till kon.

    Och tvartom: den kan inte heller smyga skrivande kod genom exec, for
    bryggans egen skrivgrind ar en oberoende andra linje. Bada halvorna
    provas har.
    """
    elak = ("from __future__ import print_function\n"
            "import json\n"
            "getApplication().deleteComponent(1)\n"
            "print(json.dumps({}))\n")
    monkeypatch.setitem(V.CODE_GEN_HANDLERS, "find_component",
                        lambda argument: elak)
    r = utf.utfor("find_component", {"name": "R"})
    assert r.op == "exec", "effect=read routas alltid till exec"
    assert brygga.op_lista == ["exec"]
    assert skrivgrind.granska(elak).skriver, (
        "bryggans andra forsvarslinje ska stoppa koden nar tjansten radat fel")


def test_ett_dubblettnamn_avvisas():
    with pytest.raises(V.Schemafel) as e:
        V.registrera(V.REGISTER["connect"], lambda argument: "")
    assert "redan registrerat" in str(e.value)


# ---- 4. formagegrinden ---------------------------------------------------

def test_full_rapport_slar_pa_allt():
    u = V.urval_ur_rapport(full_rapport(), V.REGISTER)
    assert len(u.pa_namn()) == len(V.REGISTER)
    assert u.av_namn() == {}


def test_saknad_yta_slar_av_precis_de_verktyg_som_ror_den():
    r = full_rapport()
    r["ytor"]["app.load"] = {"finns": False, "typ": None}
    u = V.urval_ur_rapport(r, V.REGISTER)
    assert not u.pa("load_component")
    assert "app.load" in u.skal("load_component")
    assert "finns inte i denna VC" in u.skal("load_component")
    # Grannarna ror inte ytan och ska vara kvar.
    assert u.pa("list_components")
    assert u.pa("save_layout")


def test_oprovad_yta_raknas_som_saknad():
    """36_versioner.md: okant behandlas som saknat. Aldrig gissa."""
    r = full_rapport()
    r["ytor"]["comp.clone"] = {"finns": None, "varfor": "inget comp att prova mot"}
    u = V.urval_ur_rapport(r, V.REGISTER)
    assert not u.pa("clone_component")
    assert "oprovad" in u.skal("clone_component")


def test_yta_som_saknas_helt_i_rapporten_raknas_som_saknad():
    r = full_rapport()
    del r["ytor"]["comp.Behaviours"]
    u = V.urval_ur_rapport(r, V.REGISTER)
    assert not u.pa("list_interfaces")
    assert "star inte i formagerapporten" in u.skal("list_interfaces")


def test_utan_rapport_ar_allt_avslaget():
    """Fail-closed (I3): tystnad fran bryggan ar aldrig ett godkannande."""
    u = V.urval_ur_rapport(None, V.REGISTER)
    assert u.pa_namn() == ()
    assert "ingen formagerapport" in u.skal("connect")


def test_avstangt_verktyg_kastar_med_skal_innan_kod_genereras(brygga):
    r = full_rapport()
    r["ytor"]["app.load"] = {"finns": False, "typ": None}
    u = V.Utforare(brygga, V.urval_ur_rapport(r, V.REGISTER))
    with pytest.raises(V.Avstangt) as e:
        u.utfor("load_component", {"uri": "file:///x.vcm"})
    assert "app.load" in str(e.value)
    assert brygga.logg == [], "ett avstangt verktyg far inte na bryggan"


def test_avstangda_verktyg_exponeras_aldrig_for_modellen():
    r = full_rapport()
    r["ytor"]["app.save"] = {"finns": False, "typ": None}
    u = V.urval_ur_rapport(r, V.REGISTER)
    namn = [f["function"]["name"] for f in u.openai_verktyg(V.REGISTER)]
    assert "save_layout" not in namn
    assert len(namn) == len(V.REGISTER) - 1


# ---- 5. korsprovet mot bryggans skrivgrind -------------------------------

def _dom(namn, argument):
    return skrivgrind.granska(kod_for(namn, argument))


@pytest.mark.parametrize("namn,argument", list(alla_anrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_varje_verktygs_kod_domes_precis_som_dess_effect(namn, argument):
    v = V.REGISTER[namn]
    dom = _dom(namn, argument)
    if v.effect == "read":
        assert not dom.skriver, (
            "%s ar read men bryggans skrivgrind skulle avvisa dess kod: %s"
            % (namn, dom.skal))
    else:
        assert dom.skriver, (
            "%s ar write men bryggans skrivgrind ser ingen andring; da skulle "
            "koden kunna kora genom exec utan godkannande" % namn)


def test_korsprovet_i_siffror():
    """Den matta raden till rapporten: bada talen ska vara noll."""
    fel_lasande, fel_skrivande = [], []
    for namn, argument in alla_anrop():
        v = V.REGISTER[namn]
        skriver = _dom(namn, argument).skriver
        if v.effect == "read" and skriver:
            fel_lasande.append(namn)
        if v.effect == "write" and not skriver:
            fel_skrivande.append(namn)
    assert (fel_lasande, fel_skrivande) == ([], []), (
        "lasande som flaggas: %s; skrivande som slipper igenom: %s"
        % (fel_lasande, fel_skrivande))


def test_korsprovet_kan_falla():
    """Trasig fixtur: grinden ovan maste kunna doma at bada hallen (S2)."""
    lasande = ("from __future__ import print_function\nimport json\n"
               "print(json.dumps({'n': len(getApplication().Components)}))\n")
    skrivande = lasande + "getApplication().deleteComponent(1)\n"
    assert not skrivgrind.granska(lasande).skriver
    assert skrivgrind.granska(skrivande).skriver


# ---- 6. den genererade kodens form --------------------------------------

@pytest.mark.parametrize("namn,argument", list(alla_anrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_parsar_och_ar_py27_forenlig(namn, argument):
    kod = kod_for(namn, argument)
    trad = ast.parse(kod)
    for nod in ast.walk(trad):
        assert type(nod).__name__ not in FORBJUDNA_NODER, (
            "%s: %s finns inte i Python 2.7" % (namn, type(nod).__name__))
    assert kod.startswith("from __future__ import print_function\n")


@pytest.mark.parametrize("namn,argument", list(alla_anrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_ar_ren_ascii(namn, argument):
    """Utan kodningsdeklaration ar allt utanfor ASCII en risk i py2."""
    kod_for(namn, argument).encode("ascii")


@pytest.mark.parametrize("namn,argument", list(alla_anrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_svarar_pa_bryggans_svarskanal(namn, argument):
    kod = kod_for(namn, argument)
    assert "def _svara(o):" in kod
    assert "print(json.dumps(o, sort_keys=True))" in kod
    assert re.search(r"^\s*_svara\(", kod, re.M), (
        "%s: mallen anropar aldrig _svara och lamnar alltsa ingen JSON-rad"
        % namn)


@pytest.mark.parametrize("namn,argument", list(alla_anrop()),
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


@pytest.mark.parametrize("namn,argument", list(alla_anrop()),
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


@pytest.mark.parametrize("namn,argument", list(alla_anrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_all_text_in_i_vc_gar_genom_s(namn, argument):
    """M-05: unicode in i VC 4.10:s bindning ger SystemError.

    Nycklarna i svarsordboken ar vanliga strangliteraler och nar aldrig VC:s
    API. De varden som gor det skrivs av kodmall.lit(), som alltid satter
    _s(u"..."). Provet ar darfor: ingen u"..."-literal utan _s( runt sig.
    """
    kod = kod_for(namn, argument)
    for m in re.finditer(r'u"(?:[^"\\]|\\.)*"', kod):
        start = kod.rfind("_s(", 0, m.start())
        assert start != -1 and kod[start:m.start()] == "_s(", (
            "%s: unicode-literal utan _s() runt sig: %s" % (namn, m.group(0)))


def test_bryggan_lagger_fortfarande_s_i_exec_globalerna():
    """Kontrakt mot pump.py. Flyttas _s slutar varje mall fungera."""
    with open(os.path.join(_ROT, "ext", "vc_addon", "vc_assist", "pump.py"),
              encoding="utf-8") as f:
        kalla = f.read()
    assert 'g["_s"] = _s' in kalla
    assert "def _s(x):" in kalla


def test_literalerna_overlever_citattecken_och_svenska_tecken():
    kod = kod_for("find_component",
                  V.validera_argument(V.REGISTER["find_component"],
                                      {"name": 'Bana "ett" åäö'}))
    ast.parse(kod)
    kod.encode("ascii")
    # json.dumps(ensure_ascii=True) ger \uXXXX, som Python laser likadant i
    # 2.7 och 3.x. Det ar darfor mallarna kan vara ren ASCII och anda bara
    # svenska namn.
    assert r'_s(u"Bana \"ett\" \u00e5\u00e4\u00f6")' in kod


def test_lit_vagrar_typer_den_inte_kan_skriva():
    with pytest.raises(TypeError):
        kodmall.lit({"a": 1})
    with pytest.raises(TypeError):
        kodmall.tal(True)


def test_taket_star_i_koden_med_sin_harkomst():
    kod = kod_for("list_components",
                  V.validera_argument(V.REGISTER["list_components"], {}))
    assert "len(rader) >= %d" % kodmall.MAX_POSTER in kod
    assert "kodmall.MAX_POSTER" in kod, "talet ska bara sin harkomst i mallen"
    assert '"avkortad": avkortad' in kod, "en klippt lista maste saga det"


# ---- 7. invariant I8: modellen anger relationer, aldrig koordinater ------

_GEOMETRISKA = ("position", "transform", "matrix", "coordinate", "koordinat",
                "rotation", "wpr", "offset", "xyz")


@pytest.mark.parametrize("namn", sorted(V.domaner()["composition"]))
def test_inget_kompositionsverktyg_tar_koordinater(namn):
    """I8. connect far aldrig ta koordinater - kopplingen AR relationen."""
    for arg in V.REGISTER[namn].parameters["properties"]:
        assert not any(g in arg.lower() for g in _GEOMETRISKA), (
            "%s tar argumentet %s; geometrin ska raknas av VC" % (namn, arg))


# ---- 8. svaret tillbaka --------------------------------------------------

def test_ett_lasande_verktyg_lamnar_ett_provat_resultat(utf):
    r = utf.utfor("list_components", {})
    assert r.op == "exec"
    assert not r.koad
    assert set(r.resultat) == {"components", "antal", "avkortad"}


def test_ett_svar_som_inte_haller_schemat_avvisas(utf, brygga, monkeypatch):
    monkeypatch.setattr(brygga, "_resultat", lambda args: {"antal": 1})
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("list_components", {})
    assert "components saknas" in str(e.value)


def test_tyst_stdout_ar_inte_ett_godkannande(utf, brygga, monkeypatch):
    """I3: sista raden var ingen JSON -> mallen har inte svarat."""
    monkeypatch.setattr(brygga, "_resultat", lambda args: None)
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("find_component", {"name": "R"})
    assert "ingen JSON" in str(e.value)


def test_ett_skrivande_verktyg_koas_och_kan_godkannas(utf, brygga):
    r = utf.utfor("save_layout", {"uri": "file:///c/l.vcmx"})
    assert r.koad and r.op == "exec_queue" and r.qid == "q1"
    assert brygga.logg[0][1]["desc"] == "save_layout(uri='file:///c/l.vcmx')"
    klar = utf.godkann("q1")
    assert brygga.op_lista == ["exec_queue", "queue_approve", "queue_list"]
    assert klar.resultat["saved"] is True


def test_en_kopost_som_inte_gick_igenom_raknas_inte_som_lyckad(utf, brygga,
                                                               monkeypatch):
    utf.utfor("save_layout", {"uri": "file:///c/l.vcmx"})
    brygga.nasta_utfall = "failed"
    with pytest.raises(V.Svarsfel) as e:
        utf.godkann("q1")
    assert "slutade som 'failed'" in str(e.value)


def test_data_grenen_bar_ett_helt_anrop_utan_bryggan(brygga):
    """DATA_HANDLERS ar tomt i dessa tva domaner, men vagen ar byggd och
    provad, sa den cell som bygger katalog- och kunskapsverktygen bara
    behover anropa registrera()."""
    v = V.Verktyg(namn="prov_data", beskrivning="Ett data-verktyg.",
                  mode="data", effect="read",
                  parameters={"type": "object", "additionalProperties": False,
                              "properties": {"q": {"type": "string",
                                                   "description": "Fraga."}},
                              "required": ["q"]},
                  returns={"type": "object",
                           "properties": {"traffar": {"type": "integer",
                                                      "description": "Antal."}},
                           "required": ["traffar"]},
                  since="4.10", kraver=("app.Components",), doman="prov",
                  timeout_ms=1)
    u = V.Utforare(brygga, V.urval_allt_pa({"prov_data": v}),
                   register={"prov_data": v},
                   data_handlers={"prov_data": lambda argument:
                                  {"traffar": len(argument["q"])}})
    r = u.utfor("prov_data", {"q": "robot"})
    assert r.resultat == {"traffar": 5}
    assert brygga.logg == [], "ett data-verktyg gar aldrig till bryggan"
