# -*- coding: utf-8 -*-
"""L0/L1/L2 for domanen robot (svc/vc_assist_svc/verktyg/robotik.py).

Kors utan VC. Samma lager som test_verktyg.py och test_verktyg_transport.py:

1. SCHEMAT. Varje verktyg bar effect, mode, returns, since, kraver, doman och
   timeout_ms, och argument provas mot schemat innan nagot skickas.
2. ROUTINGEN. effect=read -> bryggans direkta lage, effect=write -> kon.
   Mekaniskt, och provat att det inte GAR att kringga.
3. KORSPROVET MOT BRYGGANS SKRIVGRIND. Varje lasande verktygs kod far INTE
   domas som skrivande; varje skrivande verktygs kod MASTE domas som
   skrivande. Bada hallen, noll avvikelser.
4. KORSPROVET MOT API-INDEXET. Varje mall gar genom api_index.Validator och
   far inte bara ett enda uppfunnet VC-namn.

Punkt 4 mater sin egen storhet, i tre steg
------------------------------------------
En grind som inte NAR fram godkanner allt. api_index.Validator harleder ingen
returtyp ur en funktion som koden sjalv definierar, sa en mall som hamtar
komponenten genom en hjalpare far typen okand och varje lasning efterat blir
odomd. Darfor provas tre saker:

  a) noll fel och noll obestambara utover bryggans egen _s,
  b) att grinden FAKTISKT domer namn - antalet kontrollerade namn raknas och
     har ett golv,
  c) att en trasig fixtur FALLER, och att samma kod skriven genom en hjalpare
     INTE faller, sa att skillnaden ar matt och inte pastadd.

Och ett fjarde lager som den har domanen behover mer an de andra: en
NAMNINVENTERING. robotik.VC_MEDLEMMAR raknar upp varje (typ, medlem) modulen
skriver in i en mall. Testet nedan kraver bada riktningarna: varje rad ska
finnas i API-indexet, och varje VC-namn som dyker upp i en genererad mall ska
sta i listan. Ingen rad far vara oanvand och inget namn far vara odeklarerat.

VAD SOM AR OPROVAT
------------------
MATT 2026-09-04: noll komponenter i den lokala katalogen, alltsa ingen robot
att prova mot. Ingen mall har kort mot en levande VC. Allt nedan ar de grindar
som gar att kora utan VC; att VC svarar som kallan sager ar OPROVAT.
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

import formaga                                       # noqa: E402
import skrivgrind                                    # noqa: E402
from vc_assist_svc import api_index                  # noqa: E402
from vc_assist_svc import verktyg as V               # noqa: E402
from vc_assist_svc.verktyg import bas                # noqa: E402
from vc_assist_svc.verktyg import kodmall            # noqa: E402

# ---- domanen laggs i ETT eget register -----------------------------------
#
# robotik.py ar an sa lange inte importerad av verktyg/__init__.py; den
# kopplas in av den cell som ager den filen. Att importera den HAR skulle
# darfor andra det globala registrets storlek mitt under en svit dar
# test_verktyg.py raknar precis det talet.
#
# Losningen: vi noterar registret FORE importen och plockar ut exakt de namn
# var egen import lade till. Ar modulen redan inkopplad i __init__.py lagger
# importen ingenting till - da rors ingenting, och test_verktyg.py:s
# antalsrad faller som den ska tills den cellen hojer sitt tal. Neutraliteten
# far alltsa aldrig dolja en inkoppling.
_FORE_IMPORT = set(V.REGISTER)
from vc_assist_svc.verktyg import robotik as R       # noqa: E402
_LADE_TILL = tuple(sorted(set(V.REGISTER) - _FORE_IMPORT))

REGISTER = {n: v for n, v in V.REGISTER.items() if v.doman == R.DOMAN}
HANDLARE = {n: V.CODE_GEN_HANDLERS[n] for n in REGISTER}

for _namn in _LADE_TILL:
    del V.REGISTER[_namn]
    V.CODE_GEN_HANDLERS.pop(_namn, None)


# ---- fixturer ------------------------------------------------------------

# Ett minimalt och ett maximalt anrop per verktyg. Listan MASTE tacka hela
# domanen; testet nedan faller annars. Ett korsprov som inte tacker allt mater
# fel, och ett nytt verktyg ska inte kunna slinka forbi grindarna.
EXEMPEL = {
    "list_robots": [{}, {"name_contains": "IRB"}],
    "robot_info": [{"component": "Robot"},
                   {"component": "Robot", "controller": "Controller"}],
    "get_joints": [{"component": "Robot"},
                   {"component": "Robot", "controller": "Controller"}],
    "robot_limits": [{"component": "Robot"},
                     {"component": "Robot", "controller": "Controller"}],
    "get_tcp": [{"component": "Robot"},
                {"component": "Robot", "controller": "Controller",
                 "tool": "Gripper"}],
    "list_frames": [{"component": "Robot"},
                    {"component": "Robot", "kind": "tool"},
                    {"component": "Robot", "kind": "base"}],
    "list_routines": [{"component": "Robot"}],
    "read_routine": [{"component": "Robot"},
                     {"component": "Robot", "routine": "Pick"}],
    "program_state": [{"component": "Robot"}],
    "set_joints": [{"component": "Robot", "values": [0.0, 0.0, 0.0]},
                   {"component": "Robot", "controller": "Controller",
                    "values": [0.0, -90.0, 90.0, 0.0, 45.0, 0.0]}],
    "move_to": [{"component": "Robot", "position": [100.0, 0.0, 500.0]},
                {"component": "Robot", "joint_values": [0.0, 10.0],
                 "mode": "immediate"},
                {"component": "Robot", "controller": "Controller",
                 "position": [1.0, 2.0, 3.0], "wpr": [0.0, 0.0, 90.0],
                 "motion": "linear", "target_mode": "world", "base": "Base",
                 "tool": "Tool", "speed": 500.0, "acceleration": 1000.0,
                 "angular_speed": 90.0, "joint_speed_factor": 0.5,
                 "zone_method": "distance", "zone_value": 5.0, "config": 1}],
    "move_targets": [{"component": "Robot",
                      "targets": [{"position": [1.0, 2.0, 3.0]},
                                  {"joint_values": [0.0, 1.0]}]},
                     {"component": "Robot", "run": False,
                      "targets": [{"position": [1.0, 2.0, 3.0],
                                   "motion": "circular", "zone_method": "time",
                                   "zone_value": 0.1}]}],
    "check_reach": [{"component": "Robot", "position": [100.0, 0.0, 500.0]},
                    {"component": "Robot", "position": [1.0, 2.0, 3.0],
                     "wpr": [0.0, 0.0, 0.0], "target_mode": "world",
                     "base": "B", "tool": "T", "motion": "linear"}],
    "forward_kinematics": [{"component": "Robot", "values": [0.0, 0.0, 0.0]},
                           {"component": "Robot", "values": [1.0],
                            "target_mode": "normal", "base": "B", "tool": "T"}],
    "set_robot_config": [
        {"component": "Robot", "speed_percent": 50.0},
        {"component": "Robot", "max_cartesian_speed": 1000.0,
         "max_cartesian_acceleration": 2000.0, "max_angular_speed": 90.0,
         "max_angular_acceleration": 180.0, "lag_time": 0.1,
         "settle_time": 0.2, "initial_tool": "T", "initial_base": "B",
         "approach_axis": "positive_z", "configuration_mode": "fixed"}],
    "add_frame": [{"component": "Robot", "kind": "tool", "name": "Gripper"},
                  {"component": "Robot", "kind": "base", "name": "B1",
                   "node": "Root", "position": [1.0, 2.0, 3.0],
                   "wpr": [0.0, 0.0, 90.0], "position_expression": "Tx(10)"}],
    "create_routine": [{"component": "Robot", "name": "Pick"}],
    "delete_routine": [{"component": "Robot", "routine": "Pick"}],
    "add_motion_statement": [
        {"component": "Robot", "position": [1.0, 2.0, 3.0]},
        {"component": "Robot", "routine": "Pick", "motion": "linear",
         "joint_values": [0.0, 1.0], "index": 2, "name": "P10", "base": "B",
         "tool": "T", "zone_method": "time", "zone_value": 0.5,
         "cycle_time": 2.0, "external_tcp": True,
         "properties": {"MaxSpeed": 250.0}}],
    "add_statement": [{"component": "Robot", "type": "delay"},
                      {"component": "Robot", "routine": "Pick", "type": "call",
                       "index": 0, "name": "Anrop",
                       "properties": {"Routine": "Place"}}],
    "edit_statement": [
        {"component": "Robot", "index": 0, "name": "Ny"},
        {"component": "Robot", "routine": "Pick", "index": 1,
         "position": [1.0, 2.0, 3.0], "wpr": [0.0, 0.0, 0.0], "base": "B",
         "tool": "T", "zone_method": "velocity", "zone_value": 10.0,
         "cycle_time": 1.0, "external_tcp": False,
         "properties": {"Comment": "hej"}},
        {"component": "Robot", "index": 2, "joint_values": [1.0]}],
    "delete_statement": [{"component": "Robot", "index": 3},
                         {"component": "Robot", "routine": "Pick", "index": 0}],
    "run_routine": [{"component": "Robot"},
                    {"component": "Robot", "routine": "Pick", "wait": True}],
    "step_statement": [{"component": "Robot", "index": 0},
                       {"component": "Robot", "routine": "Pick", "index": 1,
                        "wait": False}],
}

# Namn den genererade koden far anvanda utan att sjalv definiera dem.
# getApplication och getSimulation kommer ur "from vcScript import *" i
# bryggans skript (ext/vc_addon/vc_assist/bridge_cmd.py), och _s laggs i
# exec-globalerna av pump.py vid varje korning.
VC_GLOBALER = {"getApplication", "getSimulation", "_s", "json", "vcVector",
               "vcMatrix"}

# Inbyggda namn som bara finns i Python 2. Mallarna ror dem enbart inne i
# try/except NameError, precis som kodmall.py sjalv gor.
PY2_INBYGGDA = {"unicode", "long", "basestring", "xrange"}

# Konstruktioner som inte finns i Python 2.7. Koden kors i VC 4.10:s
# Stackless 2.7 och i VC 5.0:s 3.x (36_versioner.md), sa den maste ga i bada.
FORBJUDNA_NODER = ("JoinedStr", "FormattedValue", "NamedExpr", "AnnAssign",
                   "AsyncFunctionDef", "Await", "AsyncFor", "AsyncWith",
                   "Match", "TryStar")

# Byggs EN gang: indexet laser fyra XML/JSON-filer och det tar tid nog att
# marka i en parametriserad svit.
VALIDATOR = api_index.bygg_validator()
INDEX = VALIDATOR.index

# Medlemsnamn som hor till Python sjalv. Hamtade ur den korande tolkens egna
# typer i stallet for en handskriven lista som skulle aldras.
PYTHONMEDLEMMAR = frozenset(
    namn
    for typ in (str, bytes, list, dict, tuple, set, int, float, bool, object)
    for namn in dir(typ))


def robotnamn():
    return tuple(sorted(REGISTER))


def alla_anrop():
    """(namn, argument) for varje exempel, med default-varden ifyllda."""
    for namn in sorted(EXEMPEL):
        for rat in EXEMPEL[namn]:
            yield namn, V.validera_argument(REGISTER[namn], rat)


def kod_for(namn, argument):
    return HANDLARE[namn](argument)


ANROP = list(alla_anrop())


def kod_union(namn):
    """Alla vagar genom ETT verktygs mall, sammanslagna."""
    return "\n".join(kod_for(namn, V.validera_argument(REGISTER[namn], rat))
                     for rat in EXEMPEL[namn])


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

    Egen och minimal: att dela attrapp med en annan testfil skulle gora
    ordningen mellan tva importer till en del av provet.
    """

    def __init__(self):
        self.logg = []
        self.qid = 0
        self.ko = []
        self.nasta_utfall = "done"

    def anrop(self, op, args=None):
        self.logg.append((op, args or {}))
        if op == V.OP_FOR_EFFECT["read"]:
            return {"v": 1, "ok": True, "result": self._resultat(args),
                    "stdout": "", "stderr": "", "elapsed_ms": 1}
        if op == V.OP_FOR_EFFECT["write"]:
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
        return svar_for(REGISTER[namn])

    @property
    def op_lista(self):
        return [op for op, _ in self.logg]


@pytest.fixture
def brygga():
    return Attrappbrygga()


@pytest.fixture
def utf(brygga):
    return V.Utforare(brygga, V.urval_allt_pa(REGISTER), register=REGISTER,
                      code_gen_handlers=HANDLARE)


def full_rapport():
    """En formagerapport dar allt finns. Samma form som formaga.formaga()."""
    return {"ytor": {yta: {"finns": True, "typ": "builtin_function_or_method"}
                     for yta in V.KANDA_YTOR},
            "summering": {"provade": len(V.KANDA_YTOR)}}


# ---- 1. domanen och schemat ---------------------------------------------

def test_domanen_ar_registrerad_och_kodgenererande():
    assert len(REGISTER) == 24, (
        "domanen har %d verktyg, inte 24: %r" % (len(REGISTER), robotnamn()))
    for namn, v in REGISTER.items():
        assert v.mode == "codegen", namn
        assert v.doman == "robot", namn
    assert set(HANDLARE) == set(REGISTER)


def test_importen_lamnar_det_globala_registret_som_den_fann_det():
    """Den har filen far inte andra det tal test_verktyg.py raknar.

    Ar robotik inkopplad i __init__.py lagger var import ingenting till, och
    da rors ingenting - felet ska da synas i test_verktyg.py, inte doljas har.
    """
    assert set(V.REGISTER) == _FORE_IMPORT, (
        "importen lamnade kvar %s i det globala registret"
        % sorted(set(V.REGISTER) - _FORE_IMPORT))
    for namn in _LADE_TILL:
        assert namn not in V.REGISTER
        assert namn not in V.CODE_GEN_HANDLERS


def test_fordelningen_read_write_ar_den_avsedda():
    las = sorted(n for n in REGISTER if REGISTER[n].effect == "read")
    skriv = sorted(n for n in REGISTER if REGISTER[n].effect == "write")
    assert len(las) == 9, las
    assert len(skriv) == 15, skriv
    # De nio lasande ar de som BARA fragar. check_reach och
    # forward_kinematics fragar ocksa, men maste skapa ett rorelsemal for att
    # gora det, och skrivgrinden domer create* som skrivande. Deklarationen
    # foljer grinden.
    assert las == ["get_joints", "get_tcp", "list_frames", "list_robots",
                   "list_routines", "program_state", "read_routine",
                   "robot_info", "robot_limits"]


def test_exempellistan_tacker_hela_domanen():
    assert set(EXEMPEL) == set(REGISTER)


def test_robotnamnen_krockar_inte_med_de_andra_domanerna():
    """Registret ar platt: tva domaner far inte vilja ha samma namn.

    Provet halls sant bade fore och efter att modulen kopplas in i
    __init__.py: det ar de ANDRA domanernas namn robotnamnen jamfors mot.
    """
    andras = {n for n, v in V.REGISTER.items() if v.doman != R.DOMAN}
    assert set(REGISTER) & andras == set(), (
        "kolliderande namn: %s" % sorted(set(REGISTER) & andras))


@pytest.mark.parametrize("namn", robotnamn())
def test_varje_verktyg_bar_de_obligatoriska_falten(namn):
    v = REGISTER[namn]
    assert v.effect in ("read", "write")
    assert v.since == "4.10"
    assert v.kraver
    assert v.returns["required"]
    assert v.beskrivning.strip()
    assert v.timeout_ms > 0
    assert v.parameters["additionalProperties"] is False


@pytest.mark.parametrize("namn", robotnamn())
def test_varje_argument_och_returfalt_bar_en_beskrivning(namn):
    """Utan beskrivning fyller modellen i betydelsen sjalv."""
    v = REGISTER[namn]

    def granska(schema, stig):
        assert (schema.get("description") or "").strip(), "%s: %s" % (namn, stig)
        if "items" in schema:
            granska(schema["items"], stig + "[]")
        for under, us in schema.get("properties", {}).items():
            granska(us, "%s.%s" % (stig, under))

    for arg, s in v.parameters["properties"].items():
        granska(s, "parameters." + arg)
    for falt, s in v.returns["properties"].items():
        granska(s, "returns." + falt)


@pytest.mark.parametrize("namn", robotnamn())
def test_varje_kravd_yta_finns_i_formagerapportens_egen_lista(namn):
    """En yta grinden inte kan prova ar ingen grind (S2)."""
    kanda = {yta for yta, _o, _a in formaga.YTOR}
    for yta in REGISTER[namn].kraver:
        assert yta in kanda, "%s kraver %s som formaga.py inte provar" % (
            namn, yta)


@pytest.mark.parametrize("namn", robotnamn())
def test_verktyget_kraver_de_ytor_dess_mall_faktiskt_ror(namn):
    """Kraver far inte vara en onskelista: koden ska anvanda ytorna.

    Kravet galler VERKTYGET, inte ett enskilt anrop: ett valfritt argument
    ger tva vagar genom mallen och formagegrinden domer om bada pa en gang.
    Darfor provas unionen over exemplen.
    """
    kod = kod_union(namn)
    for yta in REGISTER[namn].kraver:
        medlem = yta.split(".", 1)[1]
        assert medlem in kod, "%s kraver %s men ingen av dess vagar ror den" % (
            namn, yta)


def test_robotytorna_star_medvetet_utanfor_formagegrinden():
    """Den kanda luckan, sagd rakt ut och mekaniskt fastlagd.

    Ingen av VC:s robotytor star i formaga.YTOR, sa `kraver` kan inte namna
    dem. Mallarna provar dem i stallet per objekt med hasattr. Provet finns
    for att luckan ska SYNAS i sviten: den dag formaga.py far raderna kommer
    det har testet att falla, och da ska kraver skarpas.
    """
    kanda = {yta for yta, _o, _a in formaga.YTOR}
    robotytor = [y for y in kanda
                 if y.split(".", 1)[1] in ("Joints", "createTarget", "Program",
                                           "Bases", "Tools", "callRoutine")]
    assert robotytor == [], (
        "formaga.py provar nu %s; hoj kraver i robotik.py och ta bort det "
        "har testet" % robotytor)


def test_verktygsdefinitionen_gar_inte_att_andra_efterat():
    with pytest.raises(AttributeError):
        REGISTER["move_to"].effect = "read"


def test_openai_formen_bar_inga_egna_nycklar():
    """Modellen ska se OpenAI-schemat, inte vara interna villkorsnycklar."""
    f = REGISTER["move_to"].som_openai()
    assert f["function"]["name"] == "move_to"
    assert "x-minst-en-av" in REGISTER["move_to"].parameters
    assert "x-minst-en-av" not in f["function"]["parameters"]


def test_ett_verktyg_med_trasigt_schema_avvisas_vid_definitionen():
    """Trasig fixtur for schemagrinden (95_testprotokoll.md)."""
    with pytest.raises(V.Schemafel) as e:
        V.Verktyg(namn="trasig_robot", beskrivning="x", mode="codegen",
                  effect="read",
                  parameters={"type": "object", "properties": {}},
                  returns={"type": "object", "properties": {}, "required": []},
                  since="4.10", kraver=("app.findComponent",), doman="robot",
                  timeout_ms=1000)
    assert "additionalProperties" in str(e.value)
    assert "trasig_robot" not in V.REGISTER


def test_ett_verktyg_som_kraver_en_okand_yta_avvisas():
    with pytest.raises(V.Schemafel) as e:
        V.Verktyg(namn="trasig_yta", beskrivning="x", mode="codegen",
                  effect="read",
                  parameters={"type": "object", "properties": {},
                              "additionalProperties": False},
                  returns={"type": "object",
                           "properties": {"ok": {"type": "boolean",
                                                 "description": "x"}},
                           "required": ["ok"]},
                  since="4.10", kraver=("robot.Joints",), doman="robot",
                  timeout_ms=1000)
    assert "robot.Joints" in str(e.value)


# ---- 2. argumentvalidering ----------------------------------------------

def test_ratt_argument_slapps_igenom_och_default_fylls_i():
    args = V.validera_argument(REGISTER["list_frames"], {"component": "R"})
    assert args == {"component": "R", "kind": "both"}


def test_okant_argument_avvisas_med_listan_over_de_riktiga():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["get_joints"],
                            {"component": "R", "komponent": "R"})
    assert "okant argument 'komponent'" in str(e.value)
    assert "get_joints tar component" in str(e.value)


def test_saknat_obligatoriskt_argument_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["set_joints"], {"component": "R"})
    assert "obligatoriskt argument 'values' saknas" in str(e.value)


def test_fel_typ_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["get_joints"], {"component": 17})
    assert "forvantade string, fick int" in str(e.value)


def test_bool_raknas_inte_som_satsindex():
    """True ar en int i Python. Som index ar det ett modellfel."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["delete_statement"],
                            {"component": "R", "index": True})
    assert "forvantade integer, fick bool" in str(e.value)
    assert V.validera_argument(REGISTER["delete_statement"],
                               {"component": "R", "index": 3})["index"] == 3


def test_ett_slag_utanfor_enumen_avvisas_innan_kod_genereras():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["add_statement"],
                            {"component": "R", "type": "script"})
    assert "inte ett av" in str(e.value)


def test_skriptsatsen_gar_inte_att_bestalla():
    """VC_STATEMENT_SCRIPT saknas MED FLIT: den bar godtycklig Python.

    Provet ar bade pa schemat och pa kartan, sa att den inte kan smyga in
    genom att laggas till i SATSTYPER utan att nagon markt det.
    """
    enum = REGISTER["add_statement"].parameters["properties"]["type"]["enum"]
    assert "script" not in enum
    for _etikett, konstant in R.SATSTYPER:
        assert konstant != "VC_STATEMENT_SCRIPT"


def test_vektor_med_fel_antal_tal_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["check_reach"],
                            {"component": "R", "position": [1.0, 2.0]})
    assert "minst 3 varden" in str(e.value)


def test_minst_ett_av_position_och_ledvarden_kravs():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["move_to"], {"component": "R"})
    assert "minst ett av position, joint_values" in str(e.value)


def test_en_andring_utan_nagot_att_andra_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["set_robot_config"], {"component": "R"})
    assert "minst ett av speed_percent" in str(e.value)


def test_alla_problem_rapporteras_pa_en_gang():
    """Modellen ska kunna ratta allt i ett svar, inte ett fel per varv."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["add_frame"],
                            {"component": 1, "slag": "tool"})
    # 1 okant (slag) + 2 saknade (kind, name) + 1 feltypad (component)
    assert len(e.value.problem) == 4, e.value.problem


def test_argumenten_provas_innan_nagon_kod_genereras(utf, brygga):
    with pytest.raises(V.Argumentfel):
        utf.utfor("get_joints", {"komponent": "R"})
    assert brygga.logg == [], "bryggan far inte ha rorts vid ett argumentfel"


def test_ett_mal_utan_lage_avvisas_av_handlaren():
    """Ett nastlat schema kan inte bara "minst ett av". Handlaren gor det.

    Utan detta hade ett mal utan bade position och joint_values genererat kod
    som satter ingenting, och roboten hade kort till sin egen nuvarande pose
    utan att nagon sagt at den att gora det.
    """
    args = V.validera_argument(REGISTER["move_targets"],
                               {"component": "R", "targets": [{"motion": "linear"}]})
    with pytest.raises(V.Argumentfel) as e:
        kod_for("move_targets", args)
    assert "antingen position eller joint_values" in str(e.value)
    assert "move_targets[0]" in str(e.value)


def test_ett_mal_med_bade_lage_och_ledvarden_avvisas():
    args = V.validera_argument(
        REGISTER["move_targets"],
        {"component": "R", "targets": [{"position": [1.0, 2.0, 3.0],
                                        "joint_values": [0.0]}]})
    with pytest.raises(V.Argumentfel) as e:
        kod_for("move_targets", args)
    assert "far inte bara bade" in str(e.value)


def test_wpr_utan_position_avvisas():
    args = V.validera_argument(
        REGISTER["move_targets"],
        {"component": "R", "targets": [{"wpr": [0.0, 0.0, 90.0],
                                        "joint_values": [1.0]}]})
    with pytest.raises(V.Argumentfel) as e:
        kod_for("move_targets", args)
    assert "wpr utan position" in str(e.value)


def test_ett_giltigt_mal_slapps_igenom_av_samma_grind():
    """Den andra halvan av provet: grinden far inte doma allt (S2)."""
    args = V.validera_argument(
        REGISTER["move_targets"],
        {"component": "R", "targets": [{"position": [1.0, 2.0, 3.0],
                                        "wpr": [0.0, 0.0, 0.0]},
                                       {"joint_values": [1.0, 2.0]}]})
    kod = kod_for("move_targets", args)
    assert "r.addTarget(t0)" in kod and "r.addTarget(t1)" in kod


def test_en_tom_mallista_med_run_avvisas():
    """Att "kora" en tom lista ar en tyst icke-handling; den ska sagas nej till."""
    args = V.validera_argument(REGISTER["move_targets"],
                               {"component": "R", "targets": [], "run": True})
    with pytest.raises(V.Argumentfel) as e:
        kod_for("move_targets", args)
    assert "empty target list cannot run" in str(e.value)


def test_en_tom_mallista_utan_run_ar_spec_tabellens_clear_targets():
    """Den andra halvan: samma grind maste slappa igenom det ratta fallet."""
    args = V.validera_argument(REGISTER["move_targets"],
                               {"component": "R", "targets": [], "run": False})
    kod = kod_for("move_targets", args)
    assert "r.clearTargets()" in kod
    assert "r.addTarget(" not in kod
    assert "r.move()" not in kod
    assert skrivgrind.granska(kod).skriver


def test_ett_egenskapsvarde_som_inte_gar_att_skriva_avvisas():
    args = V.validera_argument(REGISTER["add_statement"],
                               {"component": "R", "type": "delay",
                                "properties": {"Delay": [1, 2]}})
    with pytest.raises(V.Argumentfel) as e:
        kod_for("add_statement", args)
    assert "bara text, tal och sant/falskt" in str(e.value)


def test_egenskapsvarden_av_ratt_slag_slapps_igenom():
    args = V.validera_argument(REGISTER["add_statement"],
                               {"component": "R", "type": "delay",
                                "properties": {"Delay": 1.5, "Note": "hej",
                                               "On": True}})
    kod = kod_for("add_statement", args)
    assert 'getProperty(_s(u"Delay"))' in kod
    assert "p.Value = 1.5" in kod
    assert "p.Value = True" in kod


def test_en_rorelsesats_utan_mal_avvisas():
    args = V.validera_argument(REGISTER["add_motion_statement"],
                               {"component": "R", "position": [1.0, 2.0, 3.0]})
    assert "pos.PositionInReference = mm" in kod_for("add_motion_statement", args)
    # Schemat kraver redan minst ett av position och joint_values; handlarens
    # egen kontroll ar den andra linjen, och den provas genom att kringga
    # schemat med ett direkt anrop.
    with pytest.raises(V.Argumentfel) as e:
        kod_for("add_motion_statement", {"component": "R", "motion": "joint"})
    assert "WHERE it's going" in str(e.value)


# ---- 3. routingen --------------------------------------------------------

@pytest.mark.parametrize("namn", robotnamn())
def test_varje_verktyg_routas_efter_sin_deklarerade_effect(namn, utf, brygga):
    utf.utfor(namn, EXEMPEL[namn][0])
    assert brygga.op_lista == [V.OP_FOR_EFFECT[REGISTER[namn].effect]]


@pytest.mark.parametrize("namn", robotnamn())
def test_ingen_handlare_kan_se_bryggan(namn):
    p = list(inspect.signature(HANDLARE[namn]).parameters.values())
    assert [x.name for x in p] == ["argument"]
    assert p[0].kind is p[0].POSITIONAL_OR_KEYWORD


def test_operationsnamnen_star_inte_i_domanmodulen():
    """Sokvagen ut ur tjansten far ha exakt en ingang: utforare.py."""
    sokvag = os.path.join(_ROT, "svc", "vc_assist_svc", "verktyg", "robotik.py")
    with open(sokvag, encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    konstanter = [n.value for n in ast.walk(trad)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    for op in V.OP_FOR_EFFECT.values():
        assert op not in konstanter


def test_ett_skrivande_verktyg_koas_och_kan_godkannas(utf, brygga):
    r = utf.utfor("create_routine", {"component": "Robot", "name": "Pick"})
    assert r.koad and r.qid == "q1"
    assert brygga.logg[0][1]["desc"] == (
        "create_routine(component='Robot', name='Pick')")
    klar = utf.godkann("q1")
    assert klar.resultat["created"] is True


def test_en_kopost_som_inte_gick_igenom_raknas_inte_som_lyckad(utf, brygga):
    utf.utfor("create_routine", {"component": "Robot", "name": "Pick"})
    brygga.nasta_utfall = "failed"
    with pytest.raises(V.Svarsfel) as e:
        utf.godkann("q1")
    assert "ended as 'failed'" in str(e.value)


def test_ett_lasande_verktyg_lamnar_ett_provat_resultat(utf):
    r = utf.utfor("list_robots", {})
    assert not r.koad
    assert set(r.resultat) == {"robots", "antal", "avkortad"}


def test_ett_svar_som_inte_haller_schemat_avvisas(utf, brygga, monkeypatch):
    monkeypatch.setattr(brygga, "_resultat", lambda args: {"antal": 1})
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("list_robots", {})
    assert "robots saknas" in str(e.value)


def test_tyst_stdout_ar_inte_ett_godkannande(utf, brygga, monkeypatch):
    """I3: sista raden var ingen JSON -> mallen har inte svarat."""
    monkeypatch.setattr(brygga, "_resultat", lambda args: None)
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("get_joints", {"component": "R"})
    assert "not JSON" in str(e.value)


def test_en_handlare_som_lamnar_skrivande_kod_routas_anda_som_read(utf, brygga,
                                                                   monkeypatch):
    """Handlarens INNEHALL far inte kunna flytta ett verktyg till kon."""
    elak = ("from __future__ import print_function\nimport json\n"
            "getApplication().deleteComponent(1)\n"
            "print(json.dumps({}))\n")
    monkeypatch.setitem(HANDLARE, "list_robots", lambda argument: elak)
    r = utf.utfor("list_robots", {})
    assert r.op == V.OP_FOR_EFFECT["read"]
    assert skrivgrind.granska(elak).skriver, (
        "bryggans andra forsvarslinje ska stoppa koden nar tjansten radat fel")


# ---- 4. formagegrinden ---------------------------------------------------

def test_full_rapport_slar_pa_alla_robotverktyg():
    u = V.urval_ur_rapport(full_rapport(), REGISTER)
    assert len(u.pa_namn()) == len(REGISTER)
    assert u.av_namn() == {}


def test_saknad_yta_slar_av_precis_de_verktyg_som_ror_den():
    r = full_rapport()
    r["ytor"]["sim.IsRunning"] = {"finns": False, "typ": None}
    u = V.urval_ur_rapport(r, REGISTER)
    for namn in ("program_state", "run_routine", "step_statement"):
        assert not u.pa(namn), namn
        assert "sim.IsRunning" in u.skal(namn)
        assert "finns inte i denna VC" in u.skal(namn)
    # Grannarna ror inte ytan och ska vara kvar.
    assert u.pa("get_joints")
    assert u.pa("move_to")


def test_oprovad_yta_raknas_som_saknad():
    """36_versioner.md: okant behandlas som saknat. Aldrig gissa."""
    r = full_rapport()
    r["ytor"]["comp.findNode"] = {"finns": None,
                                  "varfor": "inget comp att prova mot"}
    u = V.urval_ur_rapport(r, REGISTER)
    assert not u.pa("add_frame")
    assert "oprovad" in u.skal("add_frame")
    assert u.pa("list_frames")


def test_yta_som_saknas_helt_i_rapporten_raknas_som_saknad():
    r = full_rapport()
    del r["ytor"]["comp.Properties"]
    u = V.urval_ur_rapport(r, REGISTER)
    assert not u.pa("robot_info")
    assert "star inte i formagerapporten" in u.skal("robot_info")


def test_utan_rapport_ar_allt_avslaget():
    """Fail-closed (I3): tystnad fran bryggan ar aldrig ett godkannande."""
    u = V.urval_ur_rapport(None, REGISTER)
    assert u.pa_namn() == ()
    assert "ingen formagerapport" in u.skal("move_to")


def test_avstangt_verktyg_kastar_med_skal_innan_kod_genereras(brygga):
    r = full_rapport()
    r["ytor"]["app.Components"] = {"finns": False, "typ": None}
    u = V.Utforare(brygga, V.urval_ur_rapport(r, REGISTER), register=REGISTER,
                   code_gen_handlers=HANDLARE)
    with pytest.raises(V.Avstangt) as e:
        u.utfor("list_robots", {})
    assert "app.Components" in str(e.value)
    assert brygga.logg == [], "ett avstangt verktyg far inte na bryggan"


def test_avstangda_verktyg_exponeras_aldrig_for_modellen():
    r = full_rapport()
    r["ytor"]["comp.Properties"] = {"finns": False, "typ": None}
    u = V.urval_ur_rapport(r, REGISTER)
    namn = [f["function"]["name"] for f in u.openai_verktyg(REGISTER)]
    assert "robot_info" not in namn
    assert len(namn) == len(REGISTER) - 1


# ---- 5. korsprovet mot bryggans skrivgrind -------------------------------

@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_varje_verktygs_kod_domes_precis_som_dess_effect(namn, argument):
    v = REGISTER[namn]
    dom = skrivgrind.granska(kod_for(namn, argument))
    if v.effect == "read":
        assert not dom.skriver, (
            "%s ar read men bryggans skrivgrind skulle avvisa dess kod: %s"
            % (namn, dom.skal))
    else:
        assert dom.skriver, (
            "%s ar write men bryggans skrivgrind ser ingen andring; da skulle "
            "koden kunna kora utan godkannande" % namn)


def test_korsprovet_mot_skrivgrinden_i_siffror():
    """Den matta raden till rapporten: bada talen ska vara noll."""
    fel_lasande, fel_skrivande = [], []
    for namn, argument in ANROP:
        skriver = skrivgrind.granska(kod_for(namn, argument)).skriver
        if REGISTER[namn].effect == "read" and skriver:
            fel_lasande.append(namn)
        if REGISTER[namn].effect == "write" and not skriver:
            fel_skrivande.append(namn)
    assert (fel_lasande, fel_skrivande) == ([], []), (
        "lasande som flaggas: %s; skrivande som slipper igenom: %s"
        % (fel_lasande, fel_skrivande))
    assert len(ANROP) == 47, "47 anrop over 24 verktyg"


def test_skrivgrinden_kan_falla_at_bada_hallen():
    """Trasig fixtur: grinden ovan maste kunna doma at bada hallen (S2)."""
    lasande = kod_for("get_joints",
                      V.validera_argument(REGISTER["get_joints"],
                                          {"component": "R"}))
    assert not skrivgrind.granska(lasande).skriver
    assert skrivgrind.granska(lasande + "r.Speed = 10.0\n").skriver


def test_de_tva_fragande_skrivarna_ar_skrivande_av_ratt_skal():
    """check_reach och forward_kinematics fragar - men createTarget skriver.

    Provet binder skalet till mekanismen: det ar just create-anropet grinden
    reagerar pa, och inget annat i mallen.
    """
    for namn in ("check_reach", "forward_kinematics"):
        kod = kod_for(namn, V.validera_argument(REGISTER[namn],
                                                EXEMPEL[namn][0]))
        skal = skrivgrind.granska(kod).skal
        assert any("createTarget" in s for s in skal), (namn, skal)


@pytest.mark.parametrize("namn", robotnamn())
def test_ingen_lasande_mall_skapar_ett_rorelsemal(namn):
    """Ett lasande verktyg som anropar createTarget vore trasigt fran start."""
    if REGISTER[namn].effect != "read":
        return
    assert "createTarget" not in kod_union(namn)


def test_ingen_mall_dodar_pumpen():
    """app.save() stoppar simuleringen och dodar bryggan (skrivgrind.py)."""
    for namn, argument in ANROP:
        assert skrivgrind.dodar_pumpen(kod_for(namn, argument)) == [], namn


def test_ingen_mall_skapar_ett_skriptbeteende():
    """Ett skriptbeteende stoppar simuleringen mitt i bryggans eget svar."""
    for namn, argument in ANROP:
        assert skrivgrind.skapar_skriptbeteende(
            kod_for(namn, argument)) == [], namn


# ---- 6. korsprovet mot API-indexet ---------------------------------------

@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_ingen_mall_bar_ett_uppfunnet_vc_namn(namn, argument):
    g = VALIDATOR.granska(kod_for(namn, argument))
    assert g.fel == [], "%s: %s" % (namn, "; ".join(str(f) for f in g.fel))


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_inget_namn_i_mallen_ar_obestambart_utom_bryggans_egen_hjalpare(
        namn, argument):
    """_s laggs i exec-globalerna av pump.py och star i ingen API-kalla.

    Allt ANNAT validatorn inte kan avgora ar en lucka, inte ett godkannande
    (I3, fail-closed).
    """
    ovriga = [str(o) for o in VALIDATOR.granska(
        kod_for(namn, argument)).obestambara if o.namn != "_s"]
    assert ovriga == [], "%s: %s" % (namn, "; ".join(ovriga))


def test_korsprovet_mot_api_indexet_i_siffror():
    """Den matta raden till rapporten: noll fel, och grinden nar fram.

    Golvet pa antalet kontrollerade namn ar inte kosmetika. MATT
    2026-09-04 over scen.py och granssnitt.py, som gar via hjalparen _komp:
    1 kontrollerat namn per mall. Robotmallarna skriver kedjan rakt ut och
    far 1293 kontrollerade namn over 47 anrop: minst 13, mest 65, i snitt
    27,5 per anrop. Faller talet tillbaka mot ett har nagon stoppat in en
    hjalpare, och da har korsprovet slutat mata.
    """
    fel, obestambara, kontrollerade = [], [], []
    for namn, argument in ANROP:
        g = VALIDATOR.granska(kod_for(namn, argument))
        fel += [(namn, str(f)) for f in g.fel]
        obestambara += [(namn, str(o)) for o in g.obestambara
                        if o.namn != "_s"]
        kontrollerade.append(g.kontrollerade_namn)
    assert (fel, obestambara) == ([], [])
    assert len(kontrollerade) == 47
    assert sum(kontrollerade) >= 1200, (
        "grinden kontrollerade bara %d namn; da mater den inte sin egen "
        "storhet" % sum(kontrollerade))
    assert min(kontrollerade) >= 10, (
        "nagot anrop fick bara %d namn kontrollerade" % min(kontrollerade))


def test_api_grinden_faller_pa_ett_uppfunnet_namn_i_mallens_egen_form():
    """Trasig fixtur. Utan den ar korsprovet ovan en grind som aldrig fallit."""
    ratt = ('k = getApplication().findComponent(_s(u"R"))\n'
            "for b in k.Behaviours:\n"
            "    n = b.JointCount\n")
    fel = ratt.replace("b.JointCount", "b.JointCountz")
    assert VALIDATOR.granska(ratt).fel == []
    trasig = VALIDATOR.granska(fel).fel
    assert len(trasig) == 1
    assert "JointCountz" in str(trasig[0])


def test_api_grinden_blir_blind_om_komponenten_gar_genom_en_hjalpare():
    """Skalet till att mallarna anropar getApplication() inline, MATT.

    Samma uppfunna namn som faller ovan slipper igenom sa fort komponenten
    hamtas ur en funktion koden sjalv definierar: validatorn harleder ingen
    returtyp darur.
    """
    genom_hjalpare = ("def _komp(namn):\n"
                      "    return getApplication().findComponent(namn)\n"
                      'k = _komp(_s(u"R"))\n'
                      "for b in k.Behaviours:\n"
                      "    n = b.JointCountz\n")
    g = VALIDATOR.granska(genom_hjalpare)
    assert g.fel == [], "om detta borjar falla har validatorn blivit battre"
    assert g.kontrollerade_namn <= 2, (
        "hjalparvagen ska lamna nastan allt okontrollerat; fick %d"
        % g.kontrollerade_namn)


@pytest.mark.parametrize("namn", robotnamn())
def test_mallen_hamtar_komponenten_inline_och_inte_genom_en_hjalpare(namn):
    """Den mekaniska halften av provet ovan."""
    kod = kod_union(namn)
    assert "_komp(" not in kod
    assert "_app(" not in kod
    assert "getApplication().findComponent(" in kod or "getApplication().Components" in kod


# ---- 6b. namninventeringen ----------------------------------------------

def _vc_namn_i_mallarna():
    """Varje VC-namn de genererade mallarna faktiskt ror.

    Tre kallor, for tre slags namn:
      * attributuppslag (b.Joints)      -> medlemsnamn
      * hasattr(b, "Joints")            -> medlemsnamn, provat i stallet for last
      * bara namn som borjar pa VC_/vc  -> konstanter och moduler
    Attribut pa json ar Pythons egna och hor inte hit.
    """
    medlemmar, konstanter, moduler = set(), set(), set()
    for namn, argument in ANROP:
        trad = ast.parse(kod_for(namn, argument))
        for nod in ast.walk(trad):
            if isinstance(nod, ast.Attribute):
                if isinstance(nod.value, ast.Name) and nod.value.id == "json":
                    continue
                if nod.attr not in PYTHONMEDLEMMAR:
                    medlemmar.add(nod.attr)
            elif isinstance(nod, ast.Name) and isinstance(nod.ctx, ast.Load):
                if nod.id.startswith("VC_"):
                    konstanter.add(nod.id)
                elif nod.id.startswith("vc") or nod.id in R.VC_MODULFUNKTIONER:
                    moduler.add(nod.id)
            elif isinstance(nod, ast.Call):
                f = nod.func
                if isinstance(f, ast.Name) and f.id == "hasattr" \
                        and len(nod.args) >= 2 \
                        and isinstance(nod.args[1], ast.Constant):
                    medlemmar.add(nod.args[1].value)
    return medlemmar, konstanter, moduler


@pytest.mark.parametrize("typ,medlem", list(R.VC_MEDLEMMAR))
def test_varje_deklarerat_vc_namn_finns_pa_sin_typ_i_indexet(typ, medlem):
    """Den starkaste anti-hallucinationen: namnet provas mot den MATTA ytan."""
    assert INDEX.medlem(typ, medlem), (
        "%s.%s finns inte i API-indexet (arvet inrakat)" % (typ, medlem))


@pytest.mark.parametrize("konstant", list(R.VC_KONSTANTER))
def test_varje_deklarerad_konstant_finns_i_indexet(konstant):
    assert konstant in INDEX.konstanter, (
        "%s star inte bland VC:s konstanter" % konstant)


@pytest.mark.parametrize("namn", list(R.VC_MODULFUNKTIONER))
def test_varje_modulfunktion_gar_att_sla_upp(namn):
    assert INDEX.slag_upp(namn), namn


def test_inventeringen_tacker_precis_de_namn_mallarna_ror():
    """Bada riktningarna. En rad utan konsument ar skuld (S3); ett namn utan
    rad har aldrig provats mot indexet (I9)."""
    medlemmar, konstanter, moduler = _vc_namn_i_mallarna()
    deklarerade = {m for _t, m in R.VC_MEDLEMMAR}
    assert medlemmar - deklarerade == set(), (
        "mallarna ror VC-namn som inte star i VC_MEDLEMMAR: %s"
        % sorted(medlemmar - deklarerade))
    assert deklarerade - medlemmar == set(), (
        "VC_MEDLEMMAR bar namn ingen mall anvander: %s"
        % sorted(deklarerade - medlemmar))
    assert konstanter - set(R.VC_KONSTANTER) == set(), (
        "mallarna ror konstanter utanfor listan: %s"
        % sorted(konstanter - set(R.VC_KONSTANTER)))
    assert moduler == set(R.VC_MODULFUNKTIONER) | {"vcMatrix", "vcVector"}


def test_inventeringen_faller_pa_ett_uppfunnet_par():
    """Trasig fixtur for inventeringen (S2)."""
    assert INDEX.medlem("vcRobotController", "Joints")
    assert not INDEX.medlem("vcRobotController", "Jointz")
    assert not INDEX.medlem("vcRobotStyrenhet", "Joints")


@pytest.mark.parametrize("grupp", ["RORELSETYPER", "MALLAGEN", "ZONMETODER",
                                   "KONFIGLAGEN", "NARMNINGSAXLAR",
                                   "VARNINGSBITAR", "SATSTYPER",
                                   "RORELSESATSER"])
def test_varje_etikett_i_en_upprakning_pekar_pa_en_verklig_konstant(grupp):
    """Kartan etikett -> konstant maste vara TOTAL och sann.

    Utan detta kunde en enum-etikett finnas i schemat utan en konstant att
    skriva, och felet hade fyrat forst nar modellen valde just den.
    """
    poster = getattr(R, grupp)
    assert poster
    for etikett, konstant in poster:
        assert R._konstant(poster, etikett) == konstant
        assert konstant in INDEX.konstanter, "%s -> %s" % (etikett, konstant)


def test_kartan_faller_pa_en_etikett_som_inte_finns():
    with pytest.raises(KeyError) as e:
        R._konstant(R.ZONMETODER, "avstand")
    assert "glidit isar" in str(e.value)


def test_satstypskartan_i_mallen_bygger_pa_de_deklarerade_konstanterna():
    """Etiketterna read_routine lamnar ut kommer ur samma karta som schemat."""
    kod = kod_for("read_routine",
                  V.validera_argument(REGISTER["read_routine"],
                                      {"component": "R"}))
    for etikett, konstant in R.TYPKARTA:
        assert '%s: "%s",' % (konstant, etikett) in kod
    assert "except NameError:" in kod
    assert '"type_labels": typkarta_kand' in kod


# ---- 7. den genererade kodens form --------------------------------------

@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_parsar_och_ar_py27_forenlig(namn, argument):
    kod = kod_for(namn, argument)
    trad = ast.parse(kod)
    for nod in ast.walk(trad):
        assert type(nod).__name__ not in FORBJUDNA_NODER, (
            "%s: %s finns inte i Python 2.7" % (namn, type(nod).__name__))
    assert kod.startswith("from __future__ import print_function\n")


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_ar_ren_ascii(namn, argument):
    """Utan kodningsdeklaration ar allt utanfor ASCII en risk i py2."""
    kod_for(namn, argument).encode("ascii")


@pytest.mark.parametrize("namn,argument", ANROP,
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_svarar_pa_bryggans_svarskanal(namn, argument):
    kod = kod_for(namn, argument)
    assert "def _svara(o):" in kod
    assert "print(json.dumps(o, sort_keys=True))" in kod
    assert re.search(r"^\s*_svara\(", kod, re.M), (
        "%s: mallen anropar aldrig _svara och lamnar ingen JSON-rad" % namn)


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
    tillatna = (definierade | VC_GLOBALER | PY2_INBYGGDA | set(dir(builtins))
                | set(R.VC_KONSTANTER))
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
def test_mallen_bar_ingen_oanvand_import(namn, argument):
    """En importerad VC-modul som ingen rad anvander ar samma skuld."""
    kod = kod_for(namn, argument)
    trad = ast.parse(kod)
    anvanda = {n.id for n in ast.walk(trad)
               if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Import):
            for a in nod.names:
                rot = (a.asname or a.name).split(".")[0]
                if rot == "json":
                    continue
                assert rot in anvanda, "%s: import %s anvands aldrig" % (
                    namn, rot)


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
    kod = kod_for("get_joints",
                  V.validera_argument(REGISTER["get_joints"],
                                      {"component": 'Robot "ett" åäö'}))
    ast.parse(kod)
    kod.encode("ascii")
    # json.dumps(ensure_ascii=True) ger \uXXXX, som Python laser likadant i
    # 2.7 och 3.x. Det ar darfor mallarna kan vara ren ASCII och anda bara
    # svenska namn.
    assert r'_s(u"Robot \"ett\" \u00e5\u00e4\u00f6")' in kod


# Listor vars langd INTE foljer layouten eller programmet, utan ett enda
# objekts egen definition eller en storhet kinematiken sjalv begransar.
# Deras tak vore ett tak pa maskinen, inte pa svaret, och skulle bara kunna
# gora ett riktigt svar ofullstandigt.
UTAN_TAK = {
    "set_joints": ["joint_values"],
    "move_to": ["joint_values"],
    "move_targets": ["joint_values"],
    "check_reach": ["configurations", "reachable_configs", "joint_values"],
    "add_statement": ["properties"],
    "edit_statement": ["properties"],
}


@pytest.mark.parametrize("namn", robotnamn())
def test_varje_verktyg_som_lamnar_en_layoutstyrd_lista_bar_ocksa_taket(namn):
    """En lista utan tak kan spranga bryggans kropp; en klippt lista utan
    avkortad ar en tyst nedgradering (I3)."""
    v = REGISTER[namn]
    listor = sorted(f for f, s in v.returns["properties"].items()
                    if "array" in (s["type"] if isinstance(s["type"], list)
                                   else [s["type"]])
                    and "maxItems" not in s)
    fritagna = UTAN_TAK.get(namn, [])
    assert set(fritagna) <= set(listor), namn
    kvar = [f for f in listor if f not in fritagna]
    if not kvar:
        assert "avkortad" not in v.returns["properties"], (
            "%s bar avkortad utan att lamna nagon layoutstyrd lista" % namn)
        return
    assert "avkortad" in v.returns["properties"], (
        "%s lamnar listorna %s utan att kunna saga att de klipptes"
        % (namn, kvar))
    assert "avkortad" in v.returns["required"], namn
    kod = kod_union(namn)
    assert ">= %d" % kodmall.MAX_POSTER in kod
    assert "kodmall.MAX_POSTER" in kod, "talet ska bara sin harkomst i mallen"
    assert '"avkortad": avkortad' in kod


def test_fritagningslistan_ar_uttomd_och_motiverad():
    """En fritagning som inte langre gors ar en regel som slutat mata."""
    assert set(UTAN_TAK) == {"set_joints", "move_to", "move_targets",
                             "check_reach", "add_statement", "edit_statement"}
    for namn in UTAN_TAK:
        assert REGISTER[namn].effect == "write", (
            "%s ar lasande; ett lasande verktyg som listar utan tak ar en "
            "riktig lucka" % namn)


# ---- 8. domanens egna invarianter ---------------------------------------

def test_ingen_robotmall_flyttar_en_komponent():
    """I8 galler fortfarande: modellen placerar aldrig en komponent.

    Robotverktygen TAR koordinater, och det ar ratt - en robots mal ar en
    punkt i rummet, inte en relation mellan tva komponenter. Men de far
    aldrig skriva komponentens eller nodens lage; det ar kompositionens och
    scenens sak.
    """
    for namn, argument in ANROP:
        kod = kod_for(namn, argument)
        for forbjudet in (".WorldPositionMatrix =", ".Parent =",
                          ".attach(", ".detach("):
            assert forbjudet not in kod, "%s ror %s" % (namn, forbjudet)


def test_bara_ramens_egen_lagesmatris_far_skrivas():
    """Preciseringen av provet ovan: den enda .PositionMatrix som skrivs ar
    verktygs- eller basramens, aldrig en nods."""
    skrivare = []
    for namn, argument in ANROP:
        if ".PositionMatrix =" in kod_for(namn, argument):
            skrivare.append(namn)
    assert sorted(set(skrivare)) == ["add_frame"]
    kod = kod_union("add_frame")
    assert "f.PositionMatrix = mm" in kod


@pytest.mark.parametrize("namn", robotnamn())
def test_roboten_kanns_igen_pa_sin_yta_och_inte_pa_en_konstant(namn):
    """36_versioner.md: koden fragar VAD SOM FINNS.

    VC_ROBOTCONTROLLER gar inte att formageprova - formaga.py provar attribut
    pa objekt, inte namn i en modul - och en konstant som saknas ger
    NameError i stallet for ett begripligt svar.
    """
    kod = kod_union(namn)
    assert "VC_ROBOTCONTROLLER" not in kod
    assert "getBehavioursByType" not in kod
    assert "findBehavioursByType" not in kod
    if "for b in k.Behaviours:" in kod:
        assert 'hasattr(b, "Joints")' in kod or 'hasattr(b, "Program")' in kod


def test_modulen_infor_ingen_troskel_utan_harkomst():
    """Samma regel som tests/enhet/test_troskelharkomst.py, lokalt.

    Ett bart tal i en modulkonstant ar en troskel utan harkomst. Den enda
    grans domanen har - TIMEOUT_MS_RORELSE - ar bas.TIMEOUT_MS_FIL och inget
    eget tal, sa den bar den harkomst bas.py redan skrivit.
    """
    sokvag = os.path.join(_ROT, "svc", "vc_assist_svc", "verktyg", "robotik.py")
    with open(sokvag, encoding="utf-8") as f:
        rader = f.read().split("\n")
    bara_tal = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)\s*(#.*)?$")
    for nr, rad in enumerate(rader, 1):
        m = bara_tal.match(rad)
        assert not m, (
            "robotik.py:%d %s = %s ar ett bart tal utan matning bakom sig"
            % (nr, m.group(1), m.group(2)))
    assert R.TIMEOUT_MS_RORELSE == bas.TIMEOUT_MS_FIL


def test_de_langsamma_verktygen_har_rorelsetaket():
    """Ett tak som ar for kort ser ut som ett fel i VC i stallet for en tid."""
    langsamma = sorted(n for n in REGISTER
                       if REGISTER[n].timeout_ms == R.TIMEOUT_MS_RORELSE)
    assert R.TIMEOUT_MS_RORELSE > bas.TIMEOUT_MS
    assert langsamma == ["move_targets", "move_to", "run_routine",
                         "step_statement"]
    for namn in REGISTER:
        if namn not in langsamma:
            assert REGISTER[namn].timeout_ms == bas.TIMEOUT_MS, namn


def test_rsl_slakten_namns_men_manipuleras_aldrig():
    """Den uttalade gransen, mekaniskt fastlagd.

    Lasverktygen ska KANNA IGEN en RSL-robot och saga det. Inget verktyg far
    ropa pa RSL-slaktens egna metoder, for de ar oprovade och delvis
    inkompatibla (Program ar en strang dar).
    """
    lasare = kod_union("robot_info") + kod_union("program_state")
    assert '"rsl"' in lasare
    assert 'hasattr(b, "MainRoutine")' in lasare
    for namn, argument in ANROP:
        kod = kod_for(namn, argument)
        for rsl in ("createSubRoutine", "deleteSubRoutine", "newProgram",
                    "deleteProgram", "callRemoteAction", "createStatement"):
            assert rsl not in kod, "%s ror RSL-metoden %s" % (namn, rsl)


def test_utforaren_skiljs_fran_rsl_pa_callStatement():
    """Program finns pa BADA slakterna; callStatement bara pa vcExecutor."""
    assert INDEX.medlem("vcExecutor", "callStatement")
    assert not INDEX.medlem("vcRslProgramExecutor", "callStatement")
    assert INDEX.medlem("vcRslProgramExecutor", "Program")
    for namn in ("list_routines", "read_routine", "create_routine"):
        assert 'hasattr(b, "callStatement")' in kod_union(namn), namn


def test_ledgranserna_lamnas_bade_som_uttryck_och_som_tal():
    """VC lagrar granserna som uttryck. Att evaluera dem vore eval."""
    kod = kod_union("robot_limits")
    assert "def _flyt(v):" in kod
    assert "except (TypeError, ValueError):" in kod
    assert "eval" not in kod
    assert '"min_expression": j.MinValue' in kod
    assert '"min_value": _flyt(j.MinValue)' in kod


def test_nabarheten_domes_med_vc_egna_varningsbitar():
    """Inga magiska tal: bitarna ar konstanter ur VC:s egen upprakning."""
    kod = kod_union("check_reach")
    for etikett, konstant in R.VARNINGSBITAR:
        assert 'w & %s' % konstant in kod
        assert '"%s"' % etikett in kod
    assert "w == %s" % R.VARNING_OK in kod


def test_rorelsemalets_ledvarden_skrivs_tillbaka_som_ett_handtag():
    """Kallans egen regel: hamta handtaget, andra det, TILLDELA tillbaka.

    En andring pa plats utan tilldelningen skulle tyst inte na fram.
    """
    kod = kod_for("set_joints",
                  V.validera_argument(REGISTER["set_joints"],
                                      {"component": "R", "values": [1.0, 2.0]}))
    assert "jv = t.JointValues" in kod
    assert "jv[0] = 1.0" in kod
    assert "jv[1] = 2.0" in kod
    assert "t.JointValues = jv" in kod
    assert kod.index("jv[1]") < kod.index("t.JointValues = jv")


def test_en_insatt_sats_rapporterar_sin_egen_plats_och_inte_listans_slut():
    """En sats som lades in PA ett index ligger inte sist.

    len(Statements) - 1 hade pekat pa nagon annan sats, och modellen hade
    foljt svaret och rort fel rad.
    """
    for namn, extra in (("add_statement", {"type": "delay"}),
                        ("add_motion_statement",
                         {"position": [1.0, 2.0, 3.0]})):
        med = V.validera_argument(REGISTER[namn],
                                  dict(extra, component="R", index=2))
        assert '"index": 2,' in kod_for(namn, med)
        utan = V.validera_argument(REGISTER[namn], dict(extra, component="R"))
        assert '"index": len(ru.Statements) - 1,' in kod_for(namn, utan)


def test_mallistan_tommes_alltid_innan_den_fylls():
    """En mallista som ligger kvar sedan ett tidigare anrop ar en osynlig
    rorelse."""
    kod = kod_for("move_targets",
                  V.validera_argument(REGISTER["move_targets"],
                                      {"component": "R",
                                       "targets": [{"joint_values": [1.0]}]}))
    assert kod.index("r.clearTargets()") < kod.index("r.addTarget(")


def test_ett_program_som_inte_kor_syns_i_svaret():
    """Ett robotprogram ror sig bara medan simuleringen gar. Att inte saga
    det gor en icke-korning till en tyst framgang (I3)."""
    for namn in ("run_routine", "step_statement", "program_state"):
        v = REGISTER[namn]
        assert "simulation_running" in v.returns["required"], namn
        assert "getSimulation().IsRunning" in kod_union(namn), namn


def test_rorelsemalets_antingen_eller_ar_bade_deklarerad_och_tvingad():
    """Regeln star i schemat OCH i koden. Provet hindrar dem fran att glida isar.

    Den stod tidigare bara i koden, med en docstring som sa att den 'inte gar
    att skriva i JSON-schemat'. Den gar - projektets egen nyckel x-minst-en-av
    finns just for det - men schema.py tvingar den bara pa toppniva. Alltsa:
    DEKLARERAD i schemat sa varje lasare ser den (modellen, provens
    argumentgenerator), TVINGAD i _rader_mal som ser den nastlade posten.

    Faller det har provet: nagon har tagit bort den ena halvan.
    """
    import vc_assist_svc.verktyg as V
    from vc_assist_svc.verktyg.fel import Argumentfel

    grupper = R._MALSCHEMA.get("x-minst-en-av")
    assert grupper == [["position", "joint_values"]], \
        "regeln ar inte deklarerad i _MALSCHEMA"

    verktyg = V.REGISTER["move_targets"]
    for falt in grupper[0]:
        assert falt in R._MALSCHEMA["properties"], \
            "%s deklareras i x-minst-en-av men finns inte bland egenskaperna" % falt

    # Tvingandet: ett mal utan bada falten ska avvisas.
    utan_bada = {"component": "R", "targets": [{"motion": "joint"}]}
    argument = V.validera_argument(verktyg, utan_bada)
    with pytest.raises(Argumentfel):
        V.CODE_GEN_HANDLERS["move_targets"](argument)

    # Och med ettdera ska det ga igenom.
    for falt, varde in (("position", [0.0, 0.0, 0.0]),
                        ("joint_values", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])):
        med = {"component": "R", "targets": [{"motion": "joint", falt: varde}]}
        kod = V.CODE_GEN_HANDLERS["move_targets"](V.validera_argument(verktyg, med))
        assert "createTarget()" in kod
