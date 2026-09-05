# -*- coding: utf-8 -*-
"""L0/L1/L2 for domanerna simulation och measure (runda 1 av M-47).

Kors utan VC, mot attrapper. Samma ribba som tests/enhet/test_verktyg.py och
test_verktyg_signaler.py, plus de korsprov som biter:

1. SKRIVGRINDEN. Varje lasande verktygs genererade kod genom bryggans egen
   skrivgrind.granska() far INTE domas som skrivande; varje skrivande
   verktygs kod MASTE domas som skrivande. Bada hallen, noll avvikelser.
2. API-INDEXET. Varje mall genom api_index.Validator: noll FEL och noll
   OBESTAMBARA utover _s. Dessutom det grovre men skarpare provet: varje
   attributnamn i mallen ar antingen ett namn som FINNS i indexet eller ett
   uttalat Python-namn ur en kort lista.
3. SKRIPTBETEENDEN. Ingen mall far skapa ett skriptbeteende (M-13).
4. DE MATTA GRANSERNA. M-35 och M-36 sager att vcCollisionDetector inte
   fungerar. Provet laser MATNINGSFILERNA och faller den dag de sager nagot
   annat - da ska de sju detektorverktygen byggas.

95_testprotokoll.md: varje grind har ocksa en TRASIG FIXTUR som MASTE falla.
En grind som aldrig fallit ar oprovad. Varje trasigt fall nedan bar en
kommentar om vad det ar som ska falla.

VARFOR TVA DOMANER I EN FIL
---------------------------
De ar inte tva oberoende domaner. M-36 matte att en avstandsmatning svarar med
ett GAMMALT tal om inte simuleringen uppdaterats forst, sa varje matande mall
gar genom simuleringens uppdatering. Kopplingen ar mekanisk och ska provas i
ett sammanhang, inte i tva filer som var for sig ser hela.
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
import skrivgrind                                     # noqa: E402
from vc_assist_svc import verktyg as V                 # noqa: E402
from vc_assist_svc.verktyg import kodmall             # noqa: E402
from vc_assist_svc.verktyg import matning as MT       # noqa: E402
from vc_assist_svc.verktyg import register as _reg    # noqa: E402
from vc_assist_svc.verktyg import simulering as SM    # noqa: E402
from vc_assist_svc.api_index import bygg_index        # noqa: E402

DOMANER = (SM.DOMAN, MT.DOMAN)

REGISTER = {n: v for n, v in _reg.REGISTER.items() if v.doman in DOMANER}
KODGEN = {n: _reg.CODE_GEN_HANDLERS[n] for n in REGISTER
          if n in _reg.CODE_GEN_HANDLERS}
DATA = {n: _reg.DATA_HANDLERS[n] for n in REGISTER if n in _reg.DATA_HANDLERS}

INDEX = bygg_index()


# ---- fixturer ------------------------------------------------------------

# Ett minimalt och ett maximalt anrop per verktyg. Listan MASTE tacka bada
# domanerna; provet nedan faller annars. Ett nytt verktyg ska inte kunna
# slinka forbi korsproven genom att sakna exempel.
EXEMPEL = {
    # --- simulation ---
    "sim_state": [{}],
    "sim_run": [{"seconds": 10.0}, {"seconds": 0.05}],
    "sim_continue": [{"seconds": 5.0}],
    "sim_halt": [{}],
    "sim_reset": [{}],
    "sim_step": [{}, {"render": True}],
    "sim_speed": [{"speed": 1.0}, {"loop": True}, {"speed": 2.5, "loop": False}],
    "sim_warmup": [{"warmup_seconds": 30.0},
                   {"run_time_seconds": 600.0},
                   {"warmup_seconds": 0.0, "run_time_seconds": 60.0}],
    "set_fast_scheduling": [{"enabled": True}, {"enabled": False}],
    "sim_initial_state": [{"action": "save"}, {"action": "restore"}],
    "sim_autohalt": [{}],
    # --- measure ---
    "measure_distance": [
        {"component": "ST010_CNV", "other_component": "ST020_CNV"},
        {"component": "ST010_CNV", "node": "Bana", "other_component": "Robot",
         "other_node": "Flange", "tolerance": 5.0}],
    "min_distance": [
        {"component": "Robot"},
        {"component": "Robot", "node": "Flange",
         "others": ["ST010_CNV", "ST020_CNV", "Kassation"]}],
    "test_collision": [{}, {"components": ["ST010_CNV", "ST020_CNV", "Robot"],
                            "tolerance": 2.0}],
    "collision_detector_status": [{"component": "ST010_CNV",
                                   "other_component": "ST020_CNV"}],
    "path_distance": [{"component": "Produkt_1"}],
    "ray_cast": [
        {"component": "Givare", "length": 1000.0},
        {"component": "Givare", "node": "Lins", "length": 500.0,
         "rotate_x_deg": 180.0, "rotate_y_deg": 10.0, "rotate_z_deg": 45.0,
         "offset": [0.0, 0.0, 25.0]}],
    "frame_owner_node": [
        {"component": "Robot", "tolerance": 10.0},
        {"component": "Robot", "node": "Flange", "tolerance": 1.0,
         "offset": [10.0, 0.0, 0.0]}],
}

# Namn den genererade koden far anvanda utan att sjalv definiera dem.
VC_GLOBALER = {"getApplication", "getSimulation", "_s", "json", "vcMatrix"}

PY2_INBYGGDA = {"unicode", "long", "basestring", "xrange"}

FORBJUDNA_NODER = ("JoinedStr", "FormattedValue", "NamedExpr", "AnnAssign",
                   "AsyncFunctionDef", "Await", "AsyncFor", "AsyncWith",
                   "Match", "TryStar")

# Attributnamn i mallarna som INTE ar VC-namn: metoder pa Pythons egna
# behallare och pa json-modulen. Allt utanfor listan maste finnas i
# api_index, annars ar det ett uppfunnet VC-namn.
PYTHONATTRIBUT = {"append", "get", "dumps", "join"}


def alla_kodanrop():
    """(namn, argument) for varje kodgenererande exempel, defaults ifyllda."""
    for namn in sorted(EXEMPEL):
        if namn not in KODGEN:
            continue
        for rat in EXEMPEL[namn]:
            yield namn, V.validera_argument(REGISTER[namn], rat)


def kod_for(namn, argument):
    return KODGEN[namn](argument)


def kod_union(namn):
    """Alla vagar genom ett verktygs mall, hoplagda.

    Ett valfritt argument ger tva vagar, och formagegrinden domer om bada pa
    en gang. Darfor provas unionen och inte ett enskilt anrop.
    """
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
        self._register = register or REGISTER
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
                ut.append(dict((k, v) for k, v in post.items()
                               if not k.startswith("_")))
            return {"v": 1, "ok": True, "stdout": "", "result": {"queue": ut}}
        raise AssertionError("attrappen kan inte %r" % (op,))

    def _resultat(self, args):
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
    return V.Utforare(brygga, V.urval_allt_pa(REGISTER), register=REGISTER,
                      data_handlers=DATA, code_gen_handlers=KODGEN)


def full_rapport():
    """En formagerapport dar allt finns. Samma form som formaga.formaga()."""
    return {"ytor": {yta: {"finns": True, "typ": "builtin_function_or_method"}
                     for yta in V.KANDA_YTOR},
            "summering": {"provade": len(V.KANDA_YTOR)}}


def urval(rapport):
    return V.urval_ur_rapport(rapport, REGISTER)


# ==========================================================================
# 1. registret
# ==========================================================================

def test_domanerna_bar_de_verktyg_som_bestalldes():
    sim = [n for n, v in REGISTER.items() if v.doman == "simulation"]
    mat = [n for n, v in REGISTER.items() if v.doman == "measure"]
    assert len(sim) == 11, sorted(sim)
    assert len(mat) == 7, sorted(mat)
    assert len(REGISTER) == 18
    assert set(KODGEN) == set(REGISTER), "bada domanerna ror scenen (45_verktyg.md)"
    assert DATA == {}


def test_fordelningen_read_write():
    lasande = sorted(n for n, v in REGISTER.items() if v.effect == "read")
    skrivande = sorted(n for n, v in REGISTER.items() if v.effect == "write")
    assert lasande == ["frame_owner_node", "path_distance", "ray_cast",
                       "sim_state"]
    assert len(skrivande) == 14
    assert set(lasande) | set(skrivande) == set(REGISTER)


def test_de_tre_matverktygen_ar_write_av_ett_matt_skal():
    """M-36 tvingar en uppdatering, och grinden domer update() som skrivande.

    Raden star har for att valet ska vara SYNLIGT och inte se ut som ett
    slarv: verktygen fragar bara, men de maste rora scenen for att fa ett
    fardigt svar. Ett read-verktyg vars kod grinden domer som skrivande hade
    avvisats av bryggan med E_NOT_APPROVED och aldrig fungerat.
    """
    for namn in ("measure_distance", "min_distance", "test_collision"):
        assert REGISTER[namn].effect == "write", namn
        kod = kod_union(namn)
        assert "_farsk(" in kod, "%s uppdaterar inte scenen (M-36)" % namn
        assert "getSimulation().update()" in kod, namn
        assert "n.update()" in kod, namn


def test_exempellistan_tacker_bada_domanerna():
    """En lista som inte tacker allt mater fel. Nytt verktyg -> nytt exempel."""
    assert set(EXEMPEL) == set(REGISTER)


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_varje_verktyg_bar_de_obligatoriska_falten(namn):
    v = REGISTER[namn]
    assert v.mode in ("data", "codegen")
    assert v.effect in ("read", "write")
    assert v.since == "4.10"
    assert v.kraver
    assert v.returns["required"]
    assert v.beskrivning.strip()
    assert v.timeout_ms > 0
    assert v.parameters["additionalProperties"] is False


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_varje_argument_och_returfalt_bar_en_beskrivning(namn):
    v = REGISTER[namn]
    for s in v.parameters["properties"].values():
        assert s.get("description", "").strip()
        assert "type" in s
    for s in v.returns["properties"].values():
        assert s.get("description", "").strip()
        assert "type" in s


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_varje_kravd_yta_finns_i_formagerapportens_egen_lista(namn):
    """En yta grinden inte kan prova ar ingen grind (S2)."""
    kanda = {yta for yta, _o, _a in formaga.YTOR}
    for yta in REGISTER[namn].kraver:
        assert yta in kanda, "%s kraver %s som formaga.py inte provar" % (namn, yta)


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_verktyget_kraver_de_ytor_dess_mall_faktiskt_ror(namn):
    """Kraver far inte vara en onskelista: koden ska anvanda ytorna."""
    kod = kod_union(namn)
    for yta in REGISTER[namn].kraver:
        medlem = yta.split(".", 1)[1]
        assert medlem in kod, "%s kraver %s men ingen av dess vagar ror den" % (
            namn, yta)


def test_de_odeklarerbara_ytorna_star_medvetet_utanfor_formagegrinden():
    """Den kanda luckan, sagd rakt ut och mekaniskt fastlagd.

    Tio av simuleringens ytor och alla matytorna utom app.rayCast star inte i
    formaga.YTOR, sa `kraver` kan inte namna dem. Mallarna provar dem i
    stallet per objekt med hasattr. Provet finns for att luckan ska SYNAS i
    sviten: den dag formaga.py far raderna faller det har testet, och da ska
    kraver skarpas.
    """
    kanda = {yta.split(".", 1)[1] for yta, _o, _a in formaga.YTOR}
    saknade = ("halt", "continueRun", "update", "setFastScheduling",
               "SimWarmupTime", "SimulationRunTime", "setInitialState",
               "restoreInitialState", "autoHalt", "IsLooping",
               "measureDistance", "getPathDistance", "detectFrameOwnerNode",
               "newCollisionDetector")
    nya = sorted(m for m in saknade if m in kanda)
    assert nya == [], (
        "formaga.py provar nu %s; hoj kraver i simulering.py respektive "
        "matning.py och ta bort raden ur den har listan" % nya)


@pytest.mark.parametrize("namn", sorted(KODGEN))
def test_ingen_handlare_kan_se_bryggan(namn):
    """Signaturen ar kontrollen: en handlare tar (argument) och inget mer."""
    p = list(inspect.signature(KODGEN[namn]).parameters.values())
    assert [x.name for x in p] == ["argument"]
    assert p[0].kind is p[0].POSITIONAL_OR_KEYWORD


@pytest.mark.parametrize("namn", sorted(REGISTER))
def test_verktygsdefinitionen_gar_inte_att_andra_efterat(namn):
    with pytest.raises(AttributeError):
        REGISTER[namn].effect = "read"


def test_ett_dubblettnamn_avvisas():
    """TRASIG FIXTUR for registergrinden: samma namn tva ganger ska falla."""
    with pytest.raises(V.Schemafel) as e:
        V.registrera(REGISTER["sim_state"], lambda argument: "")
    assert "already registered" in str(e.value)


@pytest.mark.parametrize("modul", ["simulering.py", "matning.py"])
def test_operationsnamnen_star_inte_i_domanmodulen(modul):
    """Sokvagen ut ur tjansten far ha exakt en ingang, och den ar utforaren."""
    sokvag = os.path.join(_ROT, "svc", "vc_assist_svc", "verktyg", modul)
    with open(sokvag, encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    konstanter = [n.value for n in ast.walk(trad)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "exec" not in konstanter
    assert "exec_queue" not in konstanter


# ==========================================================================
# 2. argumentvalidering - grind 4, och den ska FALLA
# ==========================================================================

def test_ratt_argument_slapps_igenom_och_default_fylls_i():
    assert V.validera_argument(REGISTER["sim_step"], {}) == {"render": False}
    assert V.validera_argument(
        REGISTER["measure_distance"],
        {"component": "A", "other_component": "B"}) == {
            "component": "A", "other_component": "B",
            "tolerance": MT.TOLERANS_STANDARD}


def test_okant_argument_avvisas_med_listan_over_de_riktiga():
    """TRASIG FIXTUR: ett uppfunnet argumentnamn (I9)."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["sim_run"], {"seconds": 1.0,
                                                  "sekunder": 1.0})
    assert "okant argument 'sekunder'" in str(e.value)
    assert "sim_run tar seconds" in str(e.value)


def test_okant_argument_i_ett_matverktyg_avvisas():
    """TRASIG FIXTUR: 'komponent' later rimligt och finns inte."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["measure_distance"],
                            {"komponent": "A", "other_component": "B"})
    assert "okant argument 'komponent'" in str(e.value)


def test_saknat_obligatoriskt_argument_avvisas():
    """TRASIG FIXTUR: halva anropet."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["measure_distance"], {"component": "A"})
    assert "obligatoriskt argument 'other_component' saknas" in str(e.value)
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["ray_cast"], {"component": "A"})
    assert "obligatoriskt argument 'length' saknas" in str(e.value)


def test_fel_typ_avvisas():
    """TRASIG FIXTUR: en tid som strang."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["sim_run"], {"seconds": "10"})
    assert "forvantade number, fick str" in str(e.value)


def test_bool_raknas_inte_som_tid():
    """True ar en int i Python. Som antal sekunder ar det ett modellfel."""
    with pytest.raises(V.Argumentfel):
        V.validera_argument(REGISTER["sim_run"], {"seconds": True})
    assert V.validera_argument(REGISTER["sim_run"], {"seconds": 1})


def test_okant_enumvarde_avvisas():
    """TRASIG FIXTUR: 'reset' later som ett rimligt tredje lage och finns inte."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["sim_initial_state"], {"action": "reset"})
    assert "inte ett av" in str(e.value)
    assert V.validera_argument(REGISTER["sim_initial_state"],
                               {"action": "save"})


def test_en_vektor_med_fel_antal_tal_avvisas():
    """TRASIG FIXTUR: offset med tva tal i stallet for tre."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["ray_cast"],
                            {"component": "A", "length": 100.0,
                             "offset": [1.0, 2.0]})
    assert "minst 3 varden" in str(e.value)


def test_minst_ett_av_villkoret_faller_pa_ett_tomt_anrop():
    """TRASIG FIXTUR: sim_speed utan vare sig speed eller loop."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["sim_speed"], {})
    assert "minst ett av speed, loop" in str(e.value)
    with pytest.raises(V.Argumentfel):
        V.validera_argument(REGISTER["sim_warmup"], {})


def test_alla_problem_rapporteras_pa_en_gang():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["measure_distance"],
                            {"component": 1, "komponent": "B"})
    assert len(e.value.problem) == 3   # 1 okant + 1 saknat + 1 feltypad


# ---- intervallkontroller: schemat provar TYP, handlaren INTERVALL --------

def test_noll_sekunder_avvisas_av_handlaren():
    """TRASIG FIXTUR: VC:s standard ar tio DYGN, och 0 ar ingen korning."""
    for namn in ("sim_run", "sim_continue"):
        args = V.validera_argument(REGISTER[namn], {"seconds": 0.0})
        with pytest.raises(V.Argumentfel) as e:
            KODGEN[namn](args)
        assert "maste vara storre an noll" in str(e.value)
        assert "tio DYGN" in str(e.value)
    # ...och det korrekta slapps igenom.
    assert "sim.run(0.5)" in kod_for(
        "sim_run", V.validera_argument(REGISTER["sim_run"], {"seconds": 0.5}))


def test_negativ_simhastighet_avvisas_av_handlaren():
    args = V.validera_argument(REGISTER["sim_speed"], {"speed": -1.0})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["sim_speed"](args)
    assert "greater than zero" in str(e.value)


def test_negativ_uppvarmningstid_avvisas_av_handlaren():
    args = V.validera_argument(REGISTER["sim_warmup"], {"warmup_seconds": -1.0})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["sim_warmup"](args)
    assert "cannot be negative" in str(e.value)


def test_negativ_tolerans_avvisas_av_handlaren():
    args = V.validera_argument(REGISTER["test_collision"], {"tolerance": -0.5})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["test_collision"](args)
    assert "cannot be negative" in str(e.value)


def test_for_manga_kroppar_avvisas_med_talets_harkomst():
    """TRASIG FIXTUR for taket: 33 kroppar ger 528 par och spranger svaret."""
    namn = ["K%02d" % i for i in range(MT.MAX_KROPPAR + 1)]
    args = V.validera_argument(REGISTER["test_collision"],
                               {"components": namn})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["test_collision"](args)
    assert "the cap is %d" % MT.MAX_KROPPAR in str(e.value)
    assert "kodmall.MAX_POSTER" in str(e.value)
    # ...och exakt taket gar igenom.
    ok = V.validera_argument(REGISTER["test_collision"],
                             {"components": namn[:MT.MAX_KROPPAR]})
    assert KODGEN["test_collision"](ok)


def test_taket_ar_raknat_ur_max_poster_och_inte_valt():
    """Talets harkomst hor till talet: n(n-1)/2 <= MAX_POSTER."""
    n = MT.MAX_KROPPAR
    assert n * (n - 1) // 2 <= kodmall.MAX_POSTER
    assert (n + 1) * n // 2 > kodmall.MAX_POSTER


def test_en_enda_kropp_kan_inte_krocka():
    args = V.validera_argument(REGISTER["test_collision"],
                               {"components": ["A"]})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["test_collision"](args)
    assert "at least two bodies" in str(e.value)


def test_tom_motpartslista_avvisas():
    args = V.validera_argument(REGISTER["min_distance"],
                               {"component": "A", "others": []})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["min_distance"](args)
    assert "give at least one counterpart" in str(e.value)


def test_noll_langd_pa_en_strale_avvisas():
    args = V.validera_argument(REGISTER["ray_cast"],
                               {"component": "A", "length": 0.0})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["ray_cast"](args)
    assert "greater than zero" in str(e.value)


def test_noll_sokradie_avvisas():
    args = V.validera_argument(REGISTER["frame_owner_node"],
                               {"component": "A", "tolerance": 0.0})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["frame_owner_node"](args)
    assert "greater than zero" in str(e.value)


def test_argumenten_provas_innan_nagon_kod_genereras(utf, brygga):
    with pytest.raises(V.Argumentfel):
        utf.utfor("measure_distance", {"komponent": "A"})
    assert brygga.logg == [], "bryggan far inte ha rorts vid ett argumentfel"


def test_okant_verktygsnamn_avvisas(utf, brygga):
    """TRASIG FIXTUR: ett verktyg specen namner men som INTE ar byggt."""
    with pytest.raises(V.OkantVerktyg):
        utf.utfor("new_collision_detector", {})
    assert brygga.logg == []


# ==========================================================================
# 3. routingen (I12)
# ==========================================================================

@pytest.mark.parametrize("namn", sorted(EXEMPEL))
def test_varje_verktyg_routas_efter_sin_deklarerade_effect(namn, utf, brygga):
    v = REGISTER[namn]
    utf.utfor(namn, EXEMPEL[namn][0])
    assert brygga.op_lista == [V.OP_FOR_EFFECT[v.effect]]


def test_en_handlare_som_lamnar_skrivande_kod_routas_anda_som_read(utf, brygga,
                                                                  monkeypatch):
    """Handlarens INNEHALL far inte kunna flytta ett verktyg till kon."""
    elak = ("from __future__ import print_function\n"
            "import json\n"
            "getSimulation().halt()\n"
            "print(json.dumps({}))\n")
    monkeypatch.setitem(KODGEN, "path_distance", lambda argument: elak)
    r = utf.utfor("path_distance", {"component": "A"})
    assert r.op == "exec", "effect=read routas alltid till exec"
    assert skrivgrind.granska(elak).skriver, (
        "bryggans andra forsvarslinje ska stoppa koden nar tjansten radat fel")


def test_ett_skrivande_verktyg_koas_och_kan_godkannas(utf, brygga):
    r = utf.utfor("sim_run", {"seconds": 10.0})
    assert r.koad and r.op == "exec_queue" and r.qid == "q1"
    assert brygga.logg[0][1]["desc"] == "sim_run(seconds=10.0)"
    klar = utf.godkann("q1")
    assert brygga.op_lista == ["exec_queue", "queue_approve", "queue_list"]
    assert "sim_time" in klar.resultat


def test_en_kopost_som_inte_gick_igenom_raknas_inte_som_lyckad(utf, brygga):
    utf.utfor("sim_reset", {})
    brygga.nasta_utfall = "failed"
    with pytest.raises(V.Svarsfel) as e:
        utf.godkann("q1")
    assert "ended as 'failed'" in str(e.value)


# ==========================================================================
# 4. formagegrinden (36_versioner.md)
# ==========================================================================

def test_full_rapport_slar_pa_allt():
    u = urval(full_rapport())
    assert len(u.pa_namn()) == len(REGISTER)
    assert u.av_namn() == {}


def test_saknad_yta_slar_av_precis_de_verktyg_som_ror_den():
    r = full_rapport()
    r["ytor"]["sim.SimSpeed"] = {"finns": False, "typ": None}
    u = urval(r)
    assert not u.pa("sim_state")
    assert not u.pa("sim_speed")
    assert "sim.SimSpeed" in u.skal("sim_speed")
    assert "finns inte i denna VC" in u.skal("sim_speed")
    # Grannen ror inte ytan och ska vara kvar.
    assert u.pa("sim_halt")
    assert u.pa("measure_distance")


def test_oprovad_yta_raknas_som_saknad():
    """36_versioner.md: okant behandlas som saknat. Aldrig gissa."""
    r = full_rapport()
    r["ytor"]["app.rayCast"] = {"finns": None,
                                "varfor": "inget app att prova mot"}
    u = urval(r)
    assert not u.pa("ray_cast")
    assert "oprovad" in u.skal("ray_cast")


def test_yta_som_saknas_helt_i_rapporten_raknas_som_saknad():
    r = full_rapport()
    del r["ytor"]["app.Components"]
    u = urval(r)
    assert not u.pa("test_collision")
    assert "star inte i formagerapporten" in u.skal("test_collision")


def test_utan_rapport_ar_allt_avslaget():
    """Fail-closed (I3): tystnad fran bryggan ar aldrig ett godkannande."""
    u = urval(None)
    assert u.pa_namn() == ()
    assert "ingen formagerapport" in u.skal("sim_state")


def test_avstangt_verktyg_kastar_med_skal_innan_kod_genereras(brygga):
    r = full_rapport()
    r["ytor"]["sim.run"] = {"finns": False, "typ": None}
    u = V.Utforare(brygga, urval(r), register=REGISTER, data_handlers=DATA,
                   code_gen_handlers=KODGEN)
    with pytest.raises(V.Avstangt) as e:
        u.utfor("sim_run", {"seconds": 1.0})
    assert "sim.run" in str(e.value)
    assert brygga.logg == [], "ett avstangt verktyg far inte na bryggan"


def test_avstangda_verktyg_exponeras_aldrig_for_modellen():
    r = full_rapport()
    r["ytor"]["app.rayCast"] = {"finns": False, "typ": None}
    u = urval(r)
    namn = [f["function"]["name"] for f in u.openai_verktyg(REGISTER)]
    assert "ray_cast" not in namn
    assert "sim_state" in namn


# ==========================================================================
# 5. KORSPROV 1: bryggans skrivgrind
# ==========================================================================

def _dom(namn, argument):
    return skrivgrind.granska(kod_for(namn, argument))


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_varje_verktygs_kod_domes_precis_som_dess_effect(namn, argument):
    v = REGISTER[namn]
    dom = _dom(namn, argument)
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
    for namn, argument in alla_kodanrop():
        skriver = _dom(namn, argument).skriver
        if REGISTER[namn].effect == "read" and skriver:
            fel_lasande.append(namn)
        if REGISTER[namn].effect == "write" and not skriver:
            fel_skrivande.append(namn)
    assert (fel_lasande, fel_skrivande) == ([], []), (
        "lasande som flaggas: %s; skrivande som slipper igenom: %s"
        % (fel_lasande, fel_skrivande))


def test_korsprovet_mot_skrivgrinden_kan_falla():
    """TRASIG FIXTUR: grinden maste kunna doma at bada hallen (S2)."""
    lasande = ("from __future__ import print_function\nimport json\n"
               "print(json.dumps({'t': getSimulation().SimTime}))\n")
    skrivande = lasande + "getSimulation().reset()\n"
    assert not skrivgrind.granska(lasande).skriver
    assert skrivgrind.granska(skrivande).skriver


def test_de_tva_hal_som_runda_1_stangde_i_skrivgrinden():
    """M-47:s eget fynd, mekaniskt fastlagt.

    sim.autoHalt() STOPPAR simuleringen och sim.continueRun() startar den
    igen, men ingen av dem borjar pa nagot av de prefix grinden hade.
    Verktyg pa dem hade darfor kunnat ga genom exec, utan godkannande.
    Provet star har for att bada hallen ska halla: de tva namnen domes, och
    de ord som RAKAR borja pa samma bokstaver gor det inte.
    """
    assert skrivgrind._ar_muterande_namn("autoHalt")
    assert skrivgrind._ar_muterande_namn("continueRun")
    # Motprovet: prefixen far inte vara sa breda att lasande namn fastnar.
    for oskyldigt in ("autoScale", "autoSize", "continueCheck", "runtime",
                      "setupComplete"):
        assert not skrivgrind._ar_muterande_namn(oskyldigt), oskyldigt


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_ingen_mall_skapar_ett_skriptbeteende(namn, argument):
    """M-13: ett skriptbeteende stoppar simuleringen och tar ned pumpen."""
    assert skrivgrind.skapar_skriptbeteende(kod_for(namn, argument)) == []


def test_skriptbeteendegrinden_kan_falla():
    """TRASIG FIXTUR: den mall som INTE far byggas (install_script_behaviour)."""
    farlig = ("from __future__ import print_function\nimport json\n"
              "getApplication().findComponent('a')"
              ".createBehaviour(VC_SCRIPT, 'x')\n")
    assert skrivgrind.skapar_skriptbeteende(farlig)


def test_domanen_bygger_inget_skriptbeteendeverktyg():
    """47_verktygstackning.md 4.3 foreslar det. M-13 forbjuder det.

    Raden star har for att skillnaden ska vara ett VAL och inte ett glomt
    fall. Faller den dag nagon lagger till verktyget, ska M-13 lasas om
    forst.
    """
    assert "install_script_behaviour" not in REGISTER
    for namn in REGISTER:
        assert "VC_PYTHONSCRIPT" not in kod_union(namn), namn
        assert "createBehaviour" not in kod_union(namn), namn


# ==========================================================================
# 6. KORSPROV 2: API-indexet (I9)
# ==========================================================================

def _obestambara_utover_s(granskning):
    return [o for o in granskning.obestambara if o.namn != "_s"]


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_ingen_mall_bar_ett_uppfunnet_vc_namn(namn, argument):
    from vc_assist_svc.api_index import Validator
    g = Validator(INDEX).granska(kod_for(namn, argument))
    assert not g.fel, "%s: %s" % (namn, [str(f) for f in g.fel])
    kvar = _obestambara_utover_s(g)
    assert not kvar, "%s: %s" % (namn, [str(o) for o in kvar])


def test_korsprovet_mot_api_indexet_i_siffror():
    """Den matta raden till rapporten: bada talen ska vara noll."""
    from vc_assist_svc.api_index import Validator
    validator = Validator(INDEX)
    fel, obestambara = 0, 0
    for namn, argument in alla_kodanrop():
        g = validator.granska(kod_for(namn, argument))
        fel += len(g.fel)
        obestambara += len(_obestambara_utover_s(g))
    assert (fel, obestambara) == (0, 0)


def test_korsprovet_mot_api_indexet_kan_falla():
    """TRASIG FIXTUR: ett anrop mot nagot som INTE finns i API-indexet."""
    from vc_assist_svc.api_index import Validator
    validator = Validator(INDEX)
    riktig = ("from __future__ import print_function\nimport json\n"
              "s = getSimulation()\n"
              "print(json.dumps({'t': s.SimTime}))\n")
    # sim.simulationTime later som ett rimligt namn och finns inte.
    uppfunnen = riktig.replace("SimTime", "simulationTime")
    assert not validator.granska(riktig).fel
    assert validator.granska(uppfunnen).fel


def test_de_namn_domanerna_INTE_far_anvanda_finns_inte_i_indexet():
    """Motprovet mot namn som later helt rimliga.

    Var och en av dem har jag varit nara att skriva. Indexet ar det som
    skiljer dem fran de riktiga.
    """
    for uppfunnet in ("simulationTime", "isSimulationRunning", "stopSim",
                      "getDistanceTo", "testCollisionWith", "castRay",
                      "SimulationSpeed", "getMinimumDistance"):
        assert not INDEX.finns(uppfunnet), uppfunnet
    for riktigt in ("SimTime", "IsRunning", "SimSpeed", "measureDistance",
                    "rayCast", "detectFrameOwnerNode", "getPathDistance",
                    "autoHalt", "continueRun", "setFastScheduling"):
        assert INDEX.finns(riktigt), riktigt


def _vc_attribut(kod):
    """Attributnamnen i koden som INTE ar rena Python-namn."""
    return {n.attr for n in ast.walk(ast.parse(kod))
            if isinstance(n, ast.Attribute)} - PYTHONATTRIBUT


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_varje_vc_medlemsnamn_i_mallen_finns_i_indexet(namn, argument):
    """Det skarpa korsprovet: varje attributnamn, inte bara ett per mall."""
    for attribut in _vc_attribut(kod_for(namn, argument)):
        assert INDEX.finns(attribut), (
            "%s: %s finns inte i VC:s API och star inte heller i "
            "PYTHONATTRIBUT" % (namn, attribut))


def test_ingen_mall_namnger_en_vc_konstant():
    """Bada domanerna klarar sig utan konstanter, och det ar ett val.

    En konstant gar inte att formageprova (formaga.py provar attribut pa
    objekt, inte namn i en modul) och saknas den ger den NameError i stallet
    for ett begripligt svar. Faller raden har nagon infort en konstant, och
    da maste den provas mot constants.xml pa samma satt som signaler.py gor.
    """
    for namn, argument in alla_kodanrop():
        for nod in ast.walk(ast.parse(kod_for(namn, argument))):
            if isinstance(nod, ast.Name):
                assert not nod.id.startswith("VC_"), "%s: %s" % (namn, nod.id)


# ==========================================================================
# 7. de MATTA granserna - M-35 och M-36
# ==========================================================================

def _matningstext(fil):
    with open(os.path.join(_ROT, "docs", "matningar", fil),
              encoding="utf-8") as f:
        return f.read()


def test_detektorn_star_kvar_som_matt_trasig():
    """Provet laser MATNINGEN, inte en kommentar i koden.

    Den dag M-36 sager att nodlistorna haller ska de sju detektorverktygen i
    47_verktygstackning.md 4.4 byggas, och da faller den har raden och sager
    det. En grans som bara star i en docstring ruttnar tyst.
    """
    text = _matningstext("M-36_measuredistance_ar_kollisionsmattet.md")
    assert "tömmer den" in text, "M-36 har bytt form; las om den"
    assert "measureDistance" in text
    assert "bygger på `measureDistance`, inte på `vcCollisionDetector`" in text


def test_inget_verktyg_bygger_pa_detektorn_utom_diagnostiken():
    """De sju detektorverktygen ur specen far inte smyga in."""
    forbjudna = ("new_collision_detector", "test_one_collision",
                 "collision_hits", "bbox_collision", "collision_settings",
                 "new_volume_detector", "volume_hits")
    for namn in forbjudna:
        assert namn not in REGISTER, (
            "%s bygger pa en yta M-35 och M-36 matte som trasig" % namn)
    for namn in REGISTER:
        if namn == "collision_detector_status":
            continue
        kod = kod_union(namn)
        assert "newCollisionDetector" not in kod, namn
        assert "testAllCollisions" not in kod, namn


def test_diagnostiken_bar_hela_m36s_prov():
    """collision_detector_status ska mata, inte pasta."""
    kod = kod_union("collision_detector_status")
    assert "newCollisionDetector()" in kod
    assert "d.NodeListA = [a]" in kod, "M-36: en LISTA ar det som accepteras"
    assert "len(d.NodeListA)" in kod, "langden ar hela provet"
    assert 'hasattr(d, "StopOnCollision")' in kod, "M-35:s andra fynd"


def test_diagnostiken_svarar_null_och_inte_false_nar_listan_inte_haller():
    """I3, fail-closed: ett noll fran tomma listor ar inget svar.

    Det ar precis den falska gronen M-35 matte: fyra layouter godkandes av en
    domare som svarade noll darfor att den inte hade nagot att jamfora.
    """
    kod = kod_union("collision_detector_status")
    assert 'svar["collision"] = None' in kod
    assert 'svar["hit_count"] = None' in kod
    v = REGISTER["collision_detector_status"]
    assert v.returns["properties"]["collision"]["type"] == ["boolean", "null"]
    assert v.returns["properties"]["hit_count"]["type"] == ["integer", "null"]


def test_varje_matande_mall_uppdaterar_scenen_forst():
    """M-36:s falla: utan uppdatering svarar VC med ett GAMMALT tal.

    Fem olika lagen gav identiskt 4000.0 i matningen. Det ar den varsta
    sorten - konsekvent och trovardigt fel.
    """
    for namn in ("measure_distance", "min_distance", "test_collision"):
        trad = ast.parse(kod_for(namn, V.validera_argument(
            REGISTER[namn], EXEMPEL[namn][0])))
        anrop = [n for n in ast.walk(trad) if isinstance(n, ast.Call)]
        namnen = [skrivgrind._sista_namnet(n.func) for n in anrop]
        assert "_farsk" in namnen, "%s uppdaterar inte scenen" % namn
        assert namnen.index("_farsk") < namnen.index("_matt"), (
            "%s mater INNAN den uppdaterar; det ar precis M-36:s falla" % namn)


def test_noteringen_om_nollan_foljer_med_i_varje_svar():
    """En arlighetsrad i en docstring ar ingen arlighetsrad i svaret.

    Modellen laser svaret, inte modulen. 0.0 betyder nuddar ELLER
    overlappar, och den skillnaden far inte ga forlorad pa vagen.
    """
    for namn in ("measure_distance", "min_distance", "test_collision"):
        assert "notering" in REGISTER[namn].returns["required"], namn
        kod = kod_union(namn)
        assert "NUDDAR ELLER OVERLAPPAR" in kod, namn
        assert "vcCollisionDetector" in kod, (
            "%s sager inte vilken yta som INTE matte" % namn)


def test_ett_omatbart_par_raknas_aldrig_som_fritt():
    """found=false ar inte samma sak som avstandet noll, och inte som fritt."""
    kod = kod_union("test_collision")
    assert "omatbara = omatbara + 1" in kod
    assert '"unmeasurable": omatbara' in kod
    assert "unmeasurable" in REGISTER["test_collision"].returns["required"]
    # ...och den omatbara gar INTE in i trafflistan.
    assert 'if not post["found"]:' in kod


def test_settet_fast_scheduling_pastar_inte_att_det_gick():
    """41_ogat_kontrakt.md: sag inte att du satt nagot du inte kan lasa tillbaka."""
    kod = kod_union("set_fast_scheduling")
    assert '"verified": False' in kod
    assert "ingen egenskap som speglar setFastScheduling" in kod
    v = REGISTER["set_fast_scheduling"]
    assert "verified" in v.returns["required"]


def test_warmup_laser_tillbaka_och_kastar_om_vardet_inte_tog():
    """Kallan: SimulationRunTime far bara andras i OnRun. Bryggan ar inte OnRun."""
    kod = kod_union("sim_warmup")
    assert "vagrade.append" in kod
    assert "if vagrade:" in kod
    assert "raise ValueError" in kod
    assert "OnRun" in kod


def test_sim_step_bar_skalet_till_att_det_finns():
    kod = kod_union("sim_step")
    assert "M-11 och M-36" in kod
    assert "sim.update()" in kod


# ==========================================================================
# 8. den genererade kodens form
# ==========================================================================

@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_parsar_och_ar_py27_forenlig(namn, argument):
    kod = kod_for(namn, argument)
    trad = ast.parse(kod)
    for nod in ast.walk(trad):
        assert type(nod).__name__ not in FORBJUDNA_NODER, (
            "%s: %s finns inte i Python 2.7" % (namn, type(nod).__name__))
    assert kod.startswith("from __future__ import print_function\n")


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_ar_ren_ascii(namn, argument):
    """Utan kodningsdeklaration ar allt utanfor ASCII en risk i py2."""
    kod_for(namn, argument).encode("ascii")


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_koden_svarar_pa_bryggans_svarskanal(namn, argument):
    kod = kod_for(namn, argument)
    assert "def _svara(o):" in kod
    assert "print(json.dumps(o, sort_keys=True))" in kod
    assert re.search(r"^\s*_svara\(", kod, re.M), (
        "%s: mallen anropar aldrig _svara och lamnar alltsa ingen JSON-rad"
        % namn)


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
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


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
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


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_all_text_in_i_vc_gar_genom_s(namn, argument):
    """M-05: unicode in i VC 4.10:s bindning ger SystemError."""
    kod = kod_for(namn, argument)
    for m in re.finditer(r'u"(?:[^"\\]|\\.)*"', kod):
        start = kod.rfind("_s(", 0, m.start())
        assert start != -1 and kod[start:m.start()] == "_s(", (
            "%s: unicode-literal utan _s() runt sig: %s" % (namn, m.group(0)))


def test_literalerna_overlever_citattecken_och_svenska_tecken():
    kod = kod_for("path_distance",
                  V.validera_argument(REGISTER["path_distance"],
                                      {"component": 'Bana "ett" åäö'}))
    ast.parse(kod)
    kod.encode("ascii")
    # json.dumps(ensure_ascii=True) ger \uXXXX, som Python laser likadant i
    # 2.7 och 3.x. Darfor kan mallen vara ren ASCII och anda bara svenska namn.
    assert r'_s(u"Bana \"ett\" \u00e5\u00e4\u00f6")' in kod


def test_okand_hjalpare_i_mallen_kastar():
    """TRASIG FIXTUR for mallarnas egen hjalparuppslagning."""
    with pytest.raises(KeyError):
        SM._egna(["_finns_inte"])
    with pytest.raises(KeyError):
        MT._egna(["_finns_inte"])


def test_taket_star_i_koden_med_sin_harkomst():
    kod = kod_for("test_collision",
                  V.validera_argument(REGISTER["test_collision"], {}))
    assert "len(kroppar) >= %d" % MT.MAX_KROPPAR in kod
    assert "matning.MAX_KROPPAR" in kod, "talet ska bara sin harkomst i mallen"
    assert '"avkortad": avkortad' in kod, "en klippt lista maste saga det"


def test_filtren_star_faktiskt_i_den_genererade_koden():
    """Ett argument som inte hamnar i koden ar ett argument som inte verkar."""
    v = REGISTER["ray_cast"]
    utan = kod_for("ray_cast", V.validera_argument(
        v, {"component": "Givare", "length": 1000.0}))
    med = kod_for("ray_cast", V.validera_argument(v, EXEMPEL["ray_cast"][1]))
    assert "rotateAbs" not in utan and "translateAbs" not in utan
    assert "m.rotateAbsX(180.0)" in med
    assert "m.rotateAbsY(10.0)" in med
    assert "m.rotateAbsZ(45.0)" in med
    assert "m.translateAbs(0.0, 0.0, 25.0)" in med
    assert "_s(u\"Lins\")" in med


def test_stralen_byggs_utan_setwpr_och_utan_tilldelning_till_p():
    """Formvalet i matning.py, mekaniskt fastlagt.

    setWPR och m.P = ... domes bada som SKRIVANDE av bryggans grind. Skulle
    nagon byta till dem blir ray_cast och frame_owner_node koade fast de inte
    ror scenen, och det har provet sager varfor.
    """
    for namn in ("ray_cast", "frame_owner_node"):
        kod = kod_union(namn)
        assert "setWPR" not in kod, namn
        assert "m.P =" not in kod, namn
        assert "vcMatrix.new(" in kod, "%s ska arbeta pa en KOPIA" % namn
    assert skrivgrind._ar_muterande_namn("setWPR")


def test_stralen_utgar_fran_en_nod_och_aldrig_fran_fria_koordinater():
    """I8: modellen anger relationer, aldrig koordinater."""
    for namn in ("ray_cast", "frame_owner_node"):
        argument = REGISTER[namn].parameters["properties"]
        assert "component" in argument, namn
        assert "component" in REGISTER[namn].parameters["required"], namn
        for forbjudet in ("position", "world_position", "origin", "point"):
            assert forbjudet not in argument, "%s tar %s" % (namn, forbjudet)


def test_ray_cast_pastar_inte_vad_traffens_element_betyder():
    """Kallan sager 'three or five elements' och inget mer. Ingen tolkning.

    Ett verktyg som namngav elementen hade gissat, och gissningen hade sett
    ut som ett matt svar.
    """
    kod = kod_union("ray_cast")
    assert "tolkas inte har" in kod
    v = REGISTER["ray_cast"]
    assert "element_count" in v.returns["required"]
    for gissat in ("hit_node", "hit_point", "normal", "hit_component"):
        assert gissat not in v.returns["properties"], gissat


# ==========================================================================
# 9. svaret tillbaka
# ==========================================================================

def test_ett_lasande_verktyg_lamnar_ett_provat_resultat(utf):
    r = utf.utfor("sim_state", {})
    assert r.op == "exec"
    assert not r.koad
    assert set(r.resultat) == set(REGISTER["sim_state"].returns["required"])


def test_ett_svar_som_inte_haller_schemat_avvisas(utf, brygga, monkeypatch):
    """TRASIG FIXTUR: bryggan svarar utan tidsaxeln."""
    monkeypatch.setattr(brygga, "_resultat", lambda args: {"is_running": True})
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("sim_state", {})
    assert "sim_time saknas" in str(e.value)


def test_tyst_stdout_ar_inte_ett_godkannande(utf, brygga, monkeypatch):
    """I3: sista raden var ingen JSON -> mallen har inte svarat."""
    monkeypatch.setattr(brygga, "_resultat", lambda args: None)
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("path_distance", {"component": "A"})
    assert "not JSON" in str(e.value)


def test_ett_avstand_far_komma_tillbaka_som_null(utf, brygga, monkeypatch):
    """found=false ar ett giltigt svar och far inte tvingas till en nolla."""
    svar = svar_for(REGISTER["measure_distance"])
    svar["found"] = False
    svar["distance"] = None
    monkeypatch.setattr(brygga, "_resultat", lambda args: svar)
    utf.utfor("measure_distance", {"component": "A", "other_component": "B"})
    klar = utf.godkann("q1")
    assert klar.resultat["distance"] is None
