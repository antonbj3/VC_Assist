# -*- coding: utf-8 -*-
"""L0/L1/L2 for domanen signals (docs/spec/45_verktyg.md, 50_grindar.md, 60_plc.md).

Kors utan VC. Samma ribba som tests/enhet/test_verktyg.py och fyra korsprov
utover den:

1. SKRIVGRINDEN. Varje lasande verktygs genererade kod genom bryggans egen
   skrivgrind.granska() far INTE domas som skrivande; varje skrivande
   verktygs kod MASTE domas som skrivande. Bada hallen, noll avvikelser.
2. API-INDEXET. Varje mall genom svc/vc_assist_svc/api_index.Validator:
   noll FEL, och noll OBESTAMBARA utover _s, som bryggan lagger i
   exec-globalerna och som ingen statisk kalla kan kanna till. Dessutom ett
   grovre men skarpare prov: VARJE attributnamn i mallen ar antingen ett
   namn som FINNS i indexet eller ett uttalat Python-namn ur en kort lista.
   Den delen ar den som faktiskt biter, for validatorn foljer inte kedjor
   genom mallens egna hjalpfunktioner och kontrollerar darfor bara ett
   namn per mall pa egen hand.
3. SKRIPTBETEENDEN. Ingen mall far skapa ett skriptbeteende: det STOPPAR
   simuleringen och tar ned pumpen mitt i dess eget svar (M-13).
4. SAKERHETSGRANSEN. Varje skrivande verktyg avvisar en tagg markt sakerhet
   i vart och ett av sina namnbarande argument, och slapper igenom en tagg
   som inte ar markt. Markortabellen provas dessutom mot bankens EGEN
   ANLAGGNINGSSIGNALER, last ur bank/schema.py.

95_testprotokoll.md: varje grind har ocksa en trasig fixtur som MASTE falla.
En grind som aldrig fallit ar oprovad.


VARFOR REGISTRET LANAS OCH LAMNAS TILLBAKA
------------------------------------------
verktyg/__init__.py importerar an sa lange bara scen och granssnitt; den
raden agas av den som kopplar in domanen. registrera() skriver daremot i de
GLOBALA registren vid import, sa om den har filen bara importerade modulen
skulle tests/enhet/test_verktyg.py se 21 + 21 verktyg och falla pa sina
antalsrader - ett test som gar sonder av att ett annat test finns.

Darfor: registren fotograferas fore importen, domanens verktyg plockas ut,
och EXAKT de poster den har importen la till tas bort igen. Ar modulen redan
inkopplad i __init__.py lagger importen ingenting till, ingenting tas bort,
och samma kod fungerar anda. Domanen provas hela vagen genom Utforare mot
ett eget register, som utforare.Utforare tar som argument just for det har.
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
from vc_assist_svc.verktyg import register as _reg    # noqa: E402
from vc_assist_svc.api_index import bygg_index        # noqa: E402


# ---- lana registret ------------------------------------------------------

_FORE = set(_reg.REGISTER)
from vc_assist_svc.verktyg import signaler as S       # noqa: E402,E501  fyller registren
_TILLAGDA = set(_reg.REGISTER) - _FORE

REGISTER = {n: v for n, v in _reg.REGISTER.items() if v.doman == S.DOMAN}
KODGEN = {n: _reg.CODE_GEN_HANDLERS[n] for n in REGISTER
          if n in _reg.CODE_GEN_HANDLERS}
DATA = {n: _reg.DATA_HANDLERS[n] for n in REGISTER if n in _reg.DATA_HANDLERS}

for _namn in _TILLAGDA:
    del _reg.REGISTER[_namn]
    _reg.CODE_GEN_HANDLERS.pop(_namn, None)
    _reg.DATA_HANDLERS.pop(_namn, None)


# ---- fixturer ------------------------------------------------------------

# Ett minimalt och ett maximalt anrop per verktyg. Listan MASTE tacka hela
# domanen; testet nedan faller annars. Ett nytt verktyg ska inte kunna slinka
# forbi korsproven genom att sakna exempel.
EXEMPEL = {
    "list_signals": [
        {},
        {"component": "Bana", "signal_type": "VC_BOOLEANSIGNAL",
         "direction": "input", "name_contains": "ST010"},
        {"direction": "okartlagd"},
        {"component": "Bana", "direction": "output"},
    ],
    "signal_info": [{"component": "Bana", "signal": "ST010_CNV_RUN"}],
    "get_signal": [{"component": "Bana", "signal": "ST010_CNV_RUN"}],
    "signal_types": [{"component": "Bana"}],
    "list_signal_connections": [{}, {"component": "Bana"}],
    "list_signal_maps": [{}, {"component": "Bana"}],
    "signal_map_info": [{"component": "Bana", "map": "BoolMap"}],
    "list_property_adapters": [{"component": "Bana"}],
    "signal_inventory": [{}],
    "connectivity_status": [{}, {"question": "servrar"}, {"question": "tillstand"},
                            {"question": "variabler"}, {"question": "allt"}],
    "set_signal": [
        {"component": "Bana", "signal": "ST010_CNV_RUN", "value": True},
        {"component": "Bana", "signal": "ST010_CNV_SPD", "value": 1.5,
         "trigger": True},
        {"component": "Bana", "signal": "ST010_CNV_TXT", "value": "start"},
    ],
    "create_signal": [{"component": "Bana", "name": "ST010_CNV_RUN",
                       "signal_type": "VC_BOOLEANSIGNAL"},
                      {"component": "Bana", "name": "ST010_RB_POS",
                       "signal_type": "VC_MATRIXSIGNAL"}],
    "delete_signal": [{"component": "Bana", "signal": "ST010_CNV_RUN"}],
    "connect_signals": [{"component": "A", "signal": "S1",
                         "other_component": "B", "other_signal": "S2"}],
    "disconnect_signals": [{"component": "A", "signal": "S1",
                            "other_component": "B", "other_signal": "S2"}],
    "create_signal_map": [
        {"component": "Bana", "name": "BoolMap", "map_type": "VC_BOOLEANSIGNALMAP"},
        {"component": "Bana", "name": "RealMap", "map_type": "VC_REALSIGNALMAP",
         "port_count": 8}],
    "signal_map_set_port": [
        {"component": "Bana", "map": "BoolMap", "port": 0, "signal": "S1"},
        {"component": "Bana", "map": "BoolMap", "port": 3, "signal": "S1",
         "port_name": "ST010_CNV_RUN"}],
    "signal_map_clear_port": [{"component": "Bana", "map": "BoolMap", "port": 2}],
    "signal_map_connect": [{"component": "A", "map": "BoolMap", "port": 0,
                            "other_component": "B", "other_map": "BoolMap",
                            "other_port": 1}],
    "set_signal_map_direction": [
        {"component": "Bana", "map": "BoolMap", "direction": "input"},
        {"component": "Bana", "map": "BoolMap", "direction": "output"},
        {"component": "Bana", "map": "BoolMap", "direction": "undefined"}],
    "set_behaviour_property": [
        {"component": "Bana", "behaviour": "Adapter1", "property": "Signal",
         "value": "S1"},
        {"component": "Bana", "behaviour": "Adapter1", "property": "Interval",
         "value": 0.05}],
}

# Namn den genererade koden far anvanda utan att sjalv definiera dem.
# getApplication kommer ur "from vcScript import *" i bryggans skript, _s
# laggs i exec-globalerna av pump.py, och VC_-konstanterna finns i VC:s
# inbaddade tolk. De sistnamnda provas dessutom mot api_index nedan, sa en
# uppfunnen konstant kan inte gomma sig i den har listan.
VC_GLOBALER = {"getApplication", "_s", "json"}

PY2_INBYGGDA = {"unicode", "long", "basestring", "xrange"}

FORBJUDNA_NODER = ("JoinedStr", "FormattedValue", "NamedExpr", "AnnAssign",
                   "AsyncFunctionDef", "Await", "AsyncFor", "AsyncWith",
                   "Match", "TryStar")

# Attributnamn i mallarna som INTE ar VC-namn: metoder pa Pythons egna
# behallare och pa json-modulen. Allt utanfor listan maste finnas i
# api_index, annars ar det ett uppfunnet VC-namn.
PYTHONATTRIBUT = {"append", "get", "upper", "dumps"}

INDEX = bygg_index()


def alla_kodanrop():
    """(namn, argument) for varje kodgenererande exempel, defaults ifyllda."""
    for namn in sorted(EXEMPEL):
        if namn not in KODGEN:
            continue
        for rat in EXEMPEL[namn]:
            yield namn, V.validera_argument(REGISTER[namn], rat)


def kod_for(namn, argument):
    return KODGEN[namn](argument)


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
# 1. registret och den lanade importen
# ==========================================================================

def test_domanen_bar_de_verktyg_som_bestalldes():
    assert len(REGISTER) == 21
    assert len(KODGEN) == 20
    assert len(DATA) == 1, "connectivity_status ar det enda data-verktyget"
    assert set(KODGEN) | set(DATA) == set(REGISTER)


def test_fordelningen_read_write():
    lasande = sorted(n for n, v in REGISTER.items() if v.effect == "read")
    skrivande = sorted(n for n, v in REGISTER.items() if v.effect == "write")
    assert len(lasande) == 10 and len(skrivande) == 11
    assert set(lasande) | set(skrivande) == set(REGISTER)


def test_importen_lamnade_det_globala_registret_orort():
    """Ett test far inte ga sonder av att ett annat test finns.

    Domanen ar inte inkopplad i verktyg/__init__.py an, sa den har filens
    import ska inte kunna flytta antalen som test_verktyg.py raknar.
    """
    for namn in REGISTER:
        assert namn not in _reg.REGISTER or namn in _FORE
    assert set(_reg.REGISTER) == _FORE


def test_alla_verktyg_hor_till_signaldomanen():
    assert {v.doman for v in REGISTER.values()} == {"signals"}


def test_exempellistan_tacker_hela_domanen():
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
    """Schemat kraver det, men bara i den form Verktyg._granska provar.

    Provet har ar detsamma en gang till pa toppnivan, sa att ett tomt
    description som rakar passera en nastlad kontroll anda faller.
    """
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
def test_verktygsdefinitionen_gar_inte_att_andra_efterat(namn):
    with pytest.raises(AttributeError):
        REGISTER[namn].effect = "read"


@pytest.mark.parametrize("namn", sorted(KODGEN))
def test_ingen_handlare_kan_se_bryggan(namn):
    """Signaturen ar kontrollen: en handlare tar (argument) och inget mer."""
    p = list(inspect.signature(KODGEN[namn]).parameters.values())
    assert [x.name for x in p] == ["argument"]
    assert p[0].kind is p[0].POSITIONAL_OR_KEYWORD


def test_ett_dubblettnamn_avvisas():
    """Trasig fixtur for registergrinden."""
    with pytest.raises(V.Schemafel) as e:
        V.registrera(REGISTER["get_signal"], lambda argument: "")
    assert "already registered" in str(e.value)


def test_operationsnamnen_star_inte_i_domanmodulen():
    """Sokvagen ut ur tjansten far ha exakt en ingang, och den ar utforaren."""
    sokvag = os.path.join(_ROT, "svc", "vc_assist_svc", "verktyg", "signaler.py")
    with open(sokvag, encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    konstanter = [n.value for n in ast.walk(trad)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "exec" not in konstanter
    assert "exec_queue" not in konstanter


# ==========================================================================
# 2. argumentvalidering
# ==========================================================================

def test_ratt_argument_slapps_igenom_och_default_fylls_i():
    args = V.validera_argument(REGISTER["set_signal"],
                               {"component": "Bana", "signal": "S1", "value": True})
    assert args == {"component": "Bana", "signal": "S1", "value": True,
                    "trigger": False}
    assert V.validera_argument(REGISTER["connectivity_status"], {}) == {
        "question": "allt"}


def test_okant_argument_avvisas_med_listan_over_de_riktiga():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["get_signal"],
                            {"component": "Bana", "signal": "S1", "signalnamn": "S1"})
    assert "okant argument 'signalnamn'" in str(e.value)
    assert "get_signal tar component, signal" in str(e.value)


def test_saknat_obligatoriskt_argument_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["signal_map_set_port"],
                            {"component": "Bana"})
    assert "obligatoriskt argument 'map' saknas" in str(e.value)
    assert "obligatoriskt argument 'port' saknas" in str(e.value)
    assert "obligatoriskt argument 'signal' saknas" in str(e.value)


def test_fel_typ_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["signal_map_clear_port"],
                            {"component": "Bana", "map": "M", "port": "0"})
    assert "forvantade integer, fick str" in str(e.value)


def test_bool_raknas_inte_som_portindex():
    """True ar en int i Python. Som portindex ar det ett modellfel."""
    with pytest.raises(V.Argumentfel):
        V.validera_argument(REGISTER["signal_map_clear_port"],
                            {"component": "Bana", "map": "M", "port": True})
    assert V.validera_argument(REGISTER["signal_map_clear_port"],
                               {"component": "Bana", "map": "M", "port": 0})


def test_enum_utanfor_listan_avvisas():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["set_signal_map_direction"],
                            {"component": "Bana", "map": "M", "direction": "in"})
    assert "inte ett av" in str(e.value)


def test_uppfunnen_signaltyp_avvisas_av_enumet():
    """VC_INTEGERSIGNALMAP later rimlig och finns inte (I9)."""
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["create_signal_map"],
                            {"component": "Bana", "name": "M",
                             "map_type": "VC_INTEGERSIGNALMAP"})
    assert "inte ett av" in str(e.value)
    assert V.validera_argument(REGISTER["create_signal_map"],
                               {"component": "Bana", "name": "M",
                                "map_type": "VC_BOOLEANSIGNALMAP"})


def test_alla_problem_rapporteras_pa_en_gang():
    with pytest.raises(V.Argumentfel) as e:
        V.validera_argument(REGISTER["connect_signals"],
                            {"component": 1, "signalnamn": "S1"})
    assert len(e.value.problem) == 5   # 1 okant + 3 saknade + 1 feltypad


def test_negativt_portindex_avvisas_av_handlaren():
    """Schemat provar TYP, inte intervall. Kontrollen ligger dar den biter."""
    args = V.validera_argument(REGISTER["signal_map_clear_port"],
                               {"component": "Bana", "map": "M", "port": -1})
    with pytest.raises(V.Argumentfel) as e:
        KODGEN["signal_map_clear_port"](args)
    assert "kan inte vara negativa" in str(e.value)


def test_negativt_portantal_avvisas_av_handlaren():
    args = V.validera_argument(REGISTER["create_signal_map"],
                               {"component": "Bana", "name": "M",
                                "map_type": "VC_BOOLEANSIGNALMAP",
                                "port_count": -3})
    with pytest.raises(V.Argumentfel):
        KODGEN["create_signal_map"](args)
    # ...och det korrekta slapps igenom.
    ok = V.validera_argument(REGISTER["create_signal_map"],
                             {"component": "Bana", "name": "M",
                              "map_type": "VC_BOOLEANSIGNALMAP",
                              "port_count": 0})
    assert "m.PortCount = 0" in KODGEN["create_signal_map"](ok)


def test_argumenten_provas_innan_nagon_kod_genereras(utf, brygga):
    with pytest.raises(V.Argumentfel):
        utf.utfor("get_signal", {"komponent": "Bana"})
    assert brygga.logg == [], "bryggan far inte ha rorts vid ett argumentfel"


def test_okant_verktygsnamn_avvisas(utf, brygga):
    with pytest.raises(V.OkantVerktyg):
        utf.utfor("watch_signal", {})
    assert brygga.logg == []


# ==========================================================================
# 3. sakerhetsgransen (50_grindar.md, I15)
# ==========================================================================

SAKRA_NAMN = ("EMG_OK", "ST230_ESTOP_OK", "E_STOP_1", "EMERGENCY_STOP",
              "NODSTOPP", "SAFE_DOOR_CLOSED", "LIGHT_CURTAIN_OK",
              "LJUSRIDA_1", "ST010_GUARD_LOCKED", "SKYDDSGRIND",
              "ST020_INTERLOCK", "MUTING_LAMP", "ENABLING_DEVICE",
              "DEADMAN_OK", "sakerhet_kvitto")

OFARLIGA_NAMN = ("ST010_CNV_RUN", "AIR_OK", "SYS_AUTO", "SYS_RESET",
                 "SYS_ALARM", "ST230_CLP_CLOSED", "Signal", "Interval")


def _anlaggningssignaler():
    """Bankens EGEN tuppel, last ur bank/schema.py utan att importera den.

    En kopierad vokabular ar tva vokabularer sa fort nagon andrar den ena.
    ast.literal_eval i stallet for import: bank/ ar inget paket pa
    tjanstens sokvag, och testet ska inte behova gora det till ett.
    """
    sokvag = os.path.join(_ROT, "bank", "schema.py")
    with open(sokvag, encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    for nod in trad.body:
        if isinstance(nod, ast.Assign):
            for m in nod.targets:
                if isinstance(m, ast.Name) and m.id == "ANLAGGNINGSSIGNALER":
                    return tuple(ast.literal_eval(nod.value))
    raise AssertionError("bank/schema.py bar ingen ANLAGGNINGSSIGNALER langre")


# Vilka av bankens anlaggningssignaler som ar SAKERHETSFUNKTIONER.
# EMG_OK lases fran sakerhets-PLC, SAFE_DOOR_CLOSED ar skyddsgrinden och
# LIGHT_CURTAIN_OK ljusridan. De ovriga fyra ar drift, inte skydd.
BANKENS_SAKRA = {"EMG_OK", "SAFE_DOOR_CLOSED", "LIGHT_CURTAIN_OK"}


def test_markortabellen_domer_bankens_egna_anlaggningssignaler_ratt():
    """Bada hallen mot bankens tuppel: den faller OCH den slapper igenom."""
    signaler = _anlaggningssignaler()
    assert BANKENS_SAKRA <= set(signaler), (
        "bank/schema.py har bytt namn pa sina anlaggningssignaler")
    for namn in signaler:
        ar_sakerhet, skal = S.ar_sakerhetssignal(namn)
        if namn in BANKENS_SAKRA:
            assert ar_sakerhet, "%s ar en sakerhetsfunktion och maste falla" % namn
            assert namn in skal
        else:
            assert not ar_sakerhet, "%s ar drift, inte skydd, och far inte falla" % namn
            assert skal is None


@pytest.mark.parametrize("namn", SAKRA_NAMN)
def test_domen_faller_pa_ett_sakerhetsnamn(namn):
    ar_sakerhet, skal = S.ar_sakerhetssignal(namn)
    assert ar_sakerhet and skal


@pytest.mark.parametrize("namn", OFARLIGA_NAMN)
def test_domen_slapper_igenom_ett_vanligt_namn(namn):
    ar_sakerhet, skal = S.ar_sakerhetssignal(namn)
    assert not ar_sakerhet and skal is None


def test_domen_ar_skiftlagesokanslig():
    assert S.ar_sakerhetssignal("st010_estop_ok")[0]
    assert S.ar_sakerhetssignal("Light_Curtain_Ok")[0]


def test_ett_ickestrangvarde_faller_inte_pa_sakerhetsdomen():
    """set_behaviour_property tar ocksa tal och booleaner som varde."""
    assert S.ar_sakerhetssignal(1.5) == (False, None)
    assert S.ar_sakerhetssignal(True) == (False, None)


def _skrivande():
    return sorted(n for n, v in REGISTER.items() if v.effect == "write")


def _taggargument(namn):
    """Verktygets argument som BAR en tagg."""
    return [a for a in REGISTER[namn].parameters["properties"]
            if a in S.TAGGARGUMENT]


def test_varje_skrivande_verktyg_har_minst_ett_taggargument():
    """Ett skrivande signalverktyg utan tagg vore en sparr utan yta."""
    for namn in _skrivande():
        assert _taggargument(namn), (
            "%s skriver men inget av dess argument star i TAGGARGUMENT; "
            "sparren skulle inte ha nagot att prova" % namn)


def test_varje_skrivande_verktyg_avvisar_en_sakerhetstagg_i_varje_taggargument():
    """Sparren far inte kunna glommas i ett nytt verktyg.

    Provet gar mekaniskt over HELA domanen och over varje namnbarande
    argument, med ett fungerande anrop som grund. Faller nagon kombination
    inte, sa finns halet.
    """
    provade = 0
    for namn in _skrivande():
        grund = V.validera_argument(REGISTER[namn], EXEMPEL[namn][0])
        for arg in _taggargument(namn):
            elakt = dict(grund)
            elakt[arg] = "ST230_ESTOP_OK"
            with pytest.raises(S.Sakerhetsavslag) as e:
                KODGEN[namn](elakt)
            assert e.value.argument == arg
            assert e.value.tagg == "ST230_ESTOP_OK"
            assert "ESTOP" in str(e.value)
            provade += 1
    assert provade >= 15, "korsprovet ska tacka hela domanen, inte ett fall"


def test_domanen_skapar_ingen_egenskapsadapter():
    """M-15 provade skapandet: VC_PROPERTYSIGNALADAPTER ar inte bland de 80.

    Ett verktyg som bara kan misslyckas ar en stubbe (S1). Provet laser
    MATNINGEN och inte en kommentar, sa raden faller den dag adaptern blir
    skapbar - och da SKA verktyget byggas.
    """
    skapbara = _skapbara_ur_m15()
    assert "VC_BOOLEANSIGNAL" in skapbara, "M-15 har bytt form"
    assert S.ADAPTERTYP not in skapbara, (
        "M-15 sager numera att adaptern gar att skapa; bygg verktyget")
    assert not [n for n in REGISTER if "adapter" in n and n.startswith("create")]
    for namn in REGISTER:
        if REGISTER[namn].effect != "write":
            continue
        assert S.ADAPTERTYP not in kod_for(
            namn, V.validera_argument(REGISTER[namn], EXEMPEL[namn][0])), namn


def test_alla_signaltyper_domanen_erbjuder_ar_provade_skapbara():
    """create_signal star pa en MATNING, inte bara pa en konstantlista."""
    skapbara = _skapbara_ur_m15()
    for konstant, _b in S.SIGNALTYPER:
        assert konstant in skapbara, konstant
    for konstant, _b in S.KARTTYPER:
        assert konstant in skapbara, konstant
    # Motprovet: skripttyperna ar ocksa skapbara, och det ar just darfor de
    # aldrig far sta i ett enum har (M-13).
    assert "VC_SCRIPT" in skapbara
    for konstant, _b in S.SIGNALTYPER + S.KARTTYPER:
        assert "SCRIPT" not in konstant


def _skapbara_ur_m15():
    """Konstanterna M-15 matte som skapbara, lasta ur matningsfilen."""
    sokvag = os.path.join(_ROT, "docs", "matningar",
                          "M-15_skapbara_beteenden.md")
    with open(sokvag, encoding="utf-8") as f:
        text = f.read()
    ut = set(re.findall(r"^\| `(VC_[A-Z0-9_]+)` \|", text, re.M))
    assert len(ut) >= 60, "M-15 gav %d konstanter; filen har bytt form" % len(ut)
    return ut


def test_samma_anrop_utan_sakerhetstagg_gar_igenom():
    """Andra halvan av grinden: den slapper igenom det korrekta (S2)."""
    for namn in _skrivande():
        grund = V.validera_argument(REGISTER[namn], EXEMPEL[namn][0])
        kod = KODGEN[namn](grund)
        assert kod.startswith("from __future__ import print_function\n")


def test_sakerhetstagg_stoppas_innan_bryggan_rors(utf, brygga):
    with pytest.raises(S.Sakerhetsavslag):
        utf.utfor("set_signal", {"component": "Bana", "signal": "EMG_OK",
                                 "value": False})
    assert brygga.logg == [], "en sakerhetstagg far aldrig na kon"


def test_sakerhetstagg_i_ett_egenskapsvarde_stoppas_ocksa():
    """En adapter binds till en signal genom ett VARDE, inte ett signalnamn."""
    args = V.validera_argument(
        REGISTER["set_behaviour_property"],
        {"component": "Bana", "behaviour": "Adapter1", "property": "Signal",
         "value": "EMG_OK"})
    with pytest.raises(S.Sakerhetsavslag) as e:
        KODGEN["set_behaviour_property"](args)
    assert e.value.argument == "value"


KARTSKRIVARE = ("signal_map_set_port", "signal_map_clear_port",
                "signal_map_connect", "set_signal_map_direction")


@pytest.mark.parametrize("namn", KARTSKRIVARE)
def test_kartskrivarna_bar_ocksa_en_runtimesparr(namn):
    """Tjanstens sparr domer NAMN och ser inte vad en karta BAR.

    En karta som heter BoolMap men bar EMG_OK pa en port ar lika mycket en
    skyddskrets. Det vet bara VC, sa den halvan av gransen ligger i mallen
    och kastar innan andringen sker.
    """
    kod = kod_for(namn, V.validera_argument(REGISTER[namn], EXEMPEL[namn][0]))
    assert "def _sparra_karta(m, vad):" in kod
    assert "_sparra_karta(m, " in kod
    assert "_sakerhet(sig.Name)" in kod
    assert "getInternalPortSignal" in kod


def test_en_ny_karta_behover_ingen_runtimesparr():
    """create_signal_map skapar en TOM karta; den kan inte bara nagon tagg.

    Raden star har for att skillnaden ska vara ett val och inte ett glomt
    fall: skulle verktyget nagon gang borja satta portar maste sparren med.
    """
    v = REGISTER["create_signal_map"]
    for rat in EXEMPEL["create_signal_map"]:
        kod = kod_for("create_signal_map", V.validera_argument(v, rat))
        assert "_sparra_karta" not in kod
        assert "setPortSignal" not in kod


def test_runtimesparrens_villkor_faller_pa_en_sakerhetstagg():
    """Trasig fixtur for runtimesparren: kor mallens egna rader.

    Sparren kan inte koras mot VC har, sa dess kropp kors mot attrapper som
    talar samma yta. Bada hallen provas: en karta med EMG_OK pa en port
    kastar, en karta utan gor det inte.
    """
    kod = kod_for("signal_map_clear_port",
                  V.validera_argument(REGISTER["signal_map_clear_port"],
                                      {"component": "B", "map": "M", "port": 0}))
    trad = ast.parse(kod)
    behovs = [n for n in trad.body
              if isinstance(n, (ast.FunctionDef, ast.Assign))
              and getattr(n, "name", None) in ("_sakerhet", "_sparra_karta")
              or (isinstance(n, ast.Assign)
                  and any(getattr(m, "id", "") == "_SAKMARK" for m in n.targets))]
    rum = {}
    exec(compile(ast.Module(body=behovs, type_ignores=[]), "<sparr>", "exec"), rum)

    class Signal(object):
        def __init__(self, namn):
            self.Name = namn

    class Karta(object):
        def __init__(self, signaler):
            self._s = signaler
            self.PortCount = len(signaler)

        def getInternalPortSignal(self, i):
            return self._s[i]

    with pytest.raises(ValueError) as e:
        rum["_sparra_karta"](Karta([Signal("ST010_CNV_RUN"), Signal("EMG_OK")]),
                             "prov")
    assert "port 1" in str(e.value) and "EMG" in str(e.value)
    # ...och den slapper igenom en karta utan sakerhetstagg.
    rum["_sparra_karta"](Karta([Signal("ST010_CNV_RUN"), None]), "prov")


def test_lasande_verktyg_ar_inte_sparrade(utf, brygga):
    """Man maste kunna SE nodstoppet. Sparren galler bara skrivandet."""
    utf.utfor("get_signal", {"component": "Bana", "signal": "EMG_OK"})
    assert brygga.op_lista == ["exec"]


def test_lasande_mallar_bar_markningen_ut_i_svaret():
    """Markningen far inte ga forlorad pa vagen till PLC-inventeringen."""
    for namn in ("list_signals", "signal_info", "get_signal",
                 "signal_inventory", "signal_map_info",
                 "list_signal_connections"):
        v = REGISTER[namn]
        assert "safety" in _falt(v.returns), (
            "%s lamnar signaler utan sakerhetsmarkning" % namn)


def _falt(schema):
    """Alla egenskapsnamn i ett returns-schema, hur djupt de an ligger."""
    ut = set()
    stack = [schema]
    while stack:
        s = stack.pop()
        if not isinstance(s, dict):
            continue
        for namn, us in (s.get("properties") or {}).items():
            ut.add(namn)
            stack.append(us)
        if "items" in s:
            stack.append(s["items"])
    return ut


def test_mallens_markortabell_ar_tjanstens():
    """Tva tabeller vore tva sanningar. Den ena skrivs ur den andra."""
    kod = kod_for("get_signal",
                  V.validera_argument(REGISTER["get_signal"],
                                      {"component": "Bana", "signal": "S1"}))
    trad = ast.parse(kod)
    tabell = None
    for nod in trad.body:
        if (isinstance(nod, ast.Assign)
                and any(getattr(m, "id", "") == "_SAKMARK" for m in nod.targets)):
            tabell = ast.literal_eval(nod.value)
    assert tabell is not None, "mallen bar ingen _SAKMARK"
    assert tuple(tuple(rad) for rad in tabell) == S.SAKERHETSMARKORER


def test_markortabellen_ar_ren_ascii_och_versaler():
    """Bade tjanstens py3 och VC:s py2.7 ska kunna jamfora med .upper()."""
    for markor, skal in S.SAKERHETSMARKORER:
        markor.encode("ascii")
        skal.encode("ascii")
        assert markor == markor.upper()
        assert markor.strip() == markor and markor


# ==========================================================================
# 4. routingen
# ==========================================================================

@pytest.mark.parametrize("namn", sorted(EXEMPEL))
def test_varje_verktyg_routas_efter_sin_deklarerade_effect(namn, utf, brygga):
    v = REGISTER[namn]
    utf.utfor(namn, EXEMPEL[namn][0])
    if v.mode == "data":
        assert brygga.logg == [], "ett data-verktyg gar aldrig till bryggan"
    else:
        assert brygga.op_lista == [V.OP_FOR_EFFECT[v.effect]]


def test_en_handlare_som_lamnar_skrivande_kod_routas_anda_som_read(utf, brygga,
                                                                  monkeypatch):
    """Handlarens INNEHALL far inte kunna flytta ett verktyg till kon."""
    elak = ("from __future__ import print_function\n"
            "import json\n"
            "getApplication().findComponent('x').createBehaviour(1, 'y')\n"
            "print(json.dumps({}))\n")
    monkeypatch.setitem(KODGEN, "get_signal", lambda argument: elak)
    r = utf.utfor("get_signal", {"component": "Bana", "signal": "S1"})
    assert r.op == "exec", "effect=read routas alltid till exec"
    assert skrivgrind.granska(elak).skriver, (
        "bryggans andra forsvarslinje ska stoppa koden nar tjansten radat fel")


def test_ett_skrivande_verktyg_koas_och_kan_godkannas(utf, brygga):
    r = utf.utfor("set_signal", {"component": "Bana", "signal": "S1",
                                 "value": True})
    assert r.koad and r.op == "exec_queue" and r.qid == "q1"
    assert brygga.logg[0][1]["desc"] == (
        "set_signal(component='Bana', signal='S1', trigger=False, value=True)")
    klar = utf.godkann("q1")
    assert brygga.op_lista == ["exec_queue", "queue_approve", "queue_list"]
    assert klar.resultat["set"] is True


def test_en_kopost_som_inte_gick_igenom_raknas_inte_som_lyckad(utf, brygga):
    utf.utfor("delete_signal", {"component": "Bana", "signal": "S1"})
    brygga.nasta_utfall = "failed"
    with pytest.raises(V.Svarsfel) as e:
        utf.godkann("q1")
    assert "ended as 'failed'" in str(e.value)


# ==========================================================================
# 5. formagegrinden
# ==========================================================================

def test_full_rapport_slar_pa_allt():
    u = urval(full_rapport())
    assert len(u.pa_namn()) == len(REGISTER)
    assert u.av_namn() == {}


def test_saknad_yta_slar_av_precis_de_verktyg_som_ror_den():
    r = full_rapport()
    r["ytor"]["comp.findBehaviour"] = {"finns": False, "typ": None}
    u = urval(r)
    assert not u.pa("set_signal")
    assert "comp.findBehaviour" in u.skal("set_signal")
    assert "finns inte i denna VC" in u.skal("set_signal")
    # Grannen ror inte ytan och ska vara kvar.
    assert u.pa("signal_inventory")
    assert u.pa("list_signals")


def test_oprovad_yta_raknas_som_saknad():
    """36_versioner.md: okant behandlas som saknat. Aldrig gissa."""
    r = full_rapport()
    r["ytor"]["comp.Behaviours"] = {"finns": None,
                                    "varfor": "inget comp att prova mot"}
    u = urval(r)
    assert not u.pa("signal_inventory")
    assert "oprovad" in u.skal("signal_inventory")


def test_yta_som_saknas_helt_i_rapporten_raknas_som_saknad():
    r = full_rapport()
    del r["ytor"]["app.Components"]
    u = urval(r)
    assert not u.pa("list_signals")
    assert "star inte i formagerapporten" in u.skal("list_signals")


def test_utan_rapport_ar_allt_avslaget():
    """Fail-closed (I3): tystnad fran bryggan ar aldrig ett godkannande."""
    u = urval(None)
    assert u.pa_namn() == ()
    assert "ingen formagerapport" in u.skal("connectivity_status")


def test_avstangt_verktyg_kastar_med_skal_innan_kod_genereras(brygga):
    r = full_rapport()
    r["ytor"]["comp.findBehaviour"] = {"finns": False, "typ": None}
    u = V.Utforare(brygga, urval(r), register=REGISTER, data_handlers=DATA,
                   code_gen_handlers=KODGEN)
    with pytest.raises(V.Avstangt) as e:
        u.utfor("set_signal", {"component": "Bana", "signal": "S1", "value": True})
    assert "comp.findBehaviour" in str(e.value)
    assert brygga.logg == [], "ett avstangt verktyg far inte na bryggan"


def test_avstangda_verktyg_exponeras_aldrig_for_modellen():
    r = full_rapport()
    r["ytor"]["app.Components"] = {"finns": False, "typ": None}
    u = urval(r)
    namn = [f["function"]["name"] for f in u.openai_verktyg(REGISTER)]
    assert "list_signals" not in namn
    assert "signal_inventory" not in namn
    assert "get_signal" in namn


# ==========================================================================
# 6. KORSPROV 1: bryggans skrivgrind
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
    """Trasig fixtur: grinden maste kunna doma at bada hallen (S2)."""
    lasande = ("from __future__ import print_function\nimport json\n"
               "print(json.dumps({'n': len(getApplication().Components)}))\n")
    skrivande = lasande + "getApplication().findComponent('a').delete()\n"
    assert not skrivgrind.granska(lasande).skriver
    assert skrivgrind.granska(skrivande).skriver


def test_en_skrivande_mall_utan_synlig_andring_skulle_fastna():
    """Varfor set_signal_map_direction skriver .Direction i stallet.

    trySetDirection ANDRAR, men grinden ar syntaktisk och ser inte namnet.
    En mall byggd pa det anropet hade domts som LASANDE, alltsa kunnat ga
    genom exec utan godkannande. Provet visar halet, och visar att den
    valda formen tacker det.
    """
    osynlig = ("from __future__ import print_function\nimport json\n"
               "m = getApplication().findComponent('a').findBehaviour('m')\n"
               "m.trySetDirection(1)\n"
               "print(json.dumps({}))\n")
    assert not skrivgrind.granska(osynlig).skriver, (
        "om grinden numera ser trySetDirection ar kommentaren i signaler.py "
        "inte langre sann och formen kan valjas om")
    synlig = osynlig.replace("m.trySetDirection(1)", "m.Direction = 1")
    assert skrivgrind.granska(synlig).skriver
    # ...och det ar den form domanen faktiskt anvander.
    kod = kod_for("set_signal_map_direction",
                  V.validera_argument(REGISTER["set_signal_map_direction"],
                                      {"component": "Bana", "map": "M",
                                       "direction": "input"}))
    assert "m.Direction = onskad" in kod
    assert "trySetDirection" not in kod


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_ingen_mall_skapar_ett_skriptbeteende(namn, argument):
    """M-13: ett skriptbeteende stoppar simuleringen och tar ned pumpen."""
    assert skrivgrind.skapar_skriptbeteende(kod_for(namn, argument)) == []


def test_skriptbeteendegrinden_kan_falla():
    farlig = ("from __future__ import print_function\nimport json\n"
              "getApplication().findComponent('a')"
              ".createBehaviour(VC_SCRIPT, 'x')\n")
    assert skrivgrind.skapar_skriptbeteende(farlig)


# ==========================================================================
# 7. KORSPROV 2: API-indexet
# ==========================================================================

def _obestambara_utover_s(granskning):
    return [o for o in granskning.obestambara if o.namn != "_s"]


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_ingen_mall_bar_ett_uppfunnet_vc_namn(namn, argument):
    """api_index.Validator over varje mall. Inget uppfunnet namn (I9).

    _s ar den enda tillatna obestambarheten: bryggan lagger den i
    exec-globalerna vid varje korning (pump.py), sa ingen statisk kalla kan
    kanna till den. Allt annat obestambart ar fail-closed och far inte
    finnas (I3).
    """
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
    """Trasig fixtur: validatorn maste kunna fyra pa ett uppfunnet namn."""
    from vc_assist_svc.api_index import Validator
    validator = Validator(INDEX)
    riktig = ("from __future__ import print_function\nimport json\n"
              "k = getApplication().findComponent('a')\n"
              "print(json.dumps({'n': k.Name}))\n")
    uppfunnen = riktig.replace("findComponent", "findSignal")
    assert not validator.granska(riktig).fel
    assert validator.granska(uppfunnen).fel


def _vc_attribut(kod):
    """Attributnamnen i koden som INTE ar rena Python-namn."""
    return {n.attr for n in ast.walk(ast.parse(kod))
            if isinstance(n, ast.Attribute)} - PYTHONATTRIBUT


@pytest.mark.parametrize("namn,argument", list(alla_kodanrop()),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_varje_vc_medlemsnamn_i_mallen_finns_i_indexet(namn, argument):
    """Det skarpa korsprovet.

    Validatorn foljer inte kedjor genom mallens egna hjalpfunktioner, sa den
    ensam domer bara ett namn per mall. Har provas i stallet VARJE
    attributnamn mot indexet. Ett stavfel som b.SignalValue faller da har,
    inte som AttributeError inne i VC.
    """
    for attribut in _vc_attribut(kod_for(namn, argument)):
        assert INDEX.finns(attribut), (
            "%s: %s finns inte i VC:s API och star inte heller i "
            "PYTHONATTRIBUT" % (namn, attribut))


def test_medlemsnamnsprovet_kan_falla():
    assert INDEX.finns("Value") and INDEX.finns("getInternalPortSignal")
    assert not INDEX.finns("SignalValue")
    assert not INDEX.finns("getSignalDirection")


def test_varje_vc_konstant_i_mallarna_finns_i_indexet():
    """VC_-konstanterna ar namn precis som metoderna och gissas inte."""
    sedda = set()
    for namn, argument in alla_kodanrop():
        for nod in ast.walk(ast.parse(kod_for(namn, argument))):
            if isinstance(nod, ast.Name) and nod.id.startswith("VC_"):
                sedda.add(nod.id)
    assert sedda, "ingen mall namnger nagon VC-konstant; provet mater inget"
    for konstant in sorted(sedda):
        assert konstant in INDEX.konstanter, (
            "%s star inte i constants.xml" % konstant)


def test_alla_deklarerade_typkonstanter_finns_i_indexet():
    """Domanens egna tabeller far inte namnge en konstant som inte finns."""
    deklarerade = ([k for k, _b in S.SIGNALTYPER]
                   + [k for k, _b in S.KARTTYPER]
                   + [k for _e, k in S.RIKTNINGAR]
                   + [S.ADAPTERTYP])
    for konstant in deklarerade:
        assert konstant in INDEX.konstanter, konstant
    # Motprovet: de tva som LATER rimliga men inte finns.
    assert "VC_INTEGERSIGNALMAP" not in INDEX.konstanter
    assert "VC_STRINGSIGNALMAP" not in INDEX.konstanter


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
            if nod.id.startswith("VC_"):
                # Provas mot constants.xml i sitt eget test ovan.
                continue
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
        if (isinstance(nod, ast.Assign) and len(nod.targets) == 1
                and isinstance(nod.targets[0], ast.Name)
                and nod.targets[0].id.isupper()):
            assert nod.targets[0].id in anvanda, (
                "%s: tabellen %s byggs men lases aldrig"
                % (namn, nod.targets[0].id))


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
    kod = kod_for("get_signal",
                  V.validera_argument(REGISTER["get_signal"],
                                      {"component": 'Bana "ett" åäö',
                                       "signal": "S1"}))
    ast.parse(kod)
    kod.encode("ascii")
    # json.dumps(ensure_ascii=True) ger \uXXXX, som Python laser likadant i
    # 2.7 och 3.x. Darfor kan mallen vara ren ASCII och anda bara svenska namn.
    assert r'_s(u"Bana \"ett\" \u00e5\u00e4\u00f6")' in kod


def test_txt_ger_en_literal_utan_s_och_vagrar_annat():
    """_txt ar skild fran kodmall.lit och far inte kunna forvaxlas med den."""
    assert S._txt("EMG") == '"EMG"'
    assert S._txt("aao å") == '"aao \\u00e5"'
    with pytest.raises(TypeError):
        S._txt(1)


def test_taket_star_i_koden_med_sin_harkomst():
    kod = kod_for("list_signals",
                  V.validera_argument(REGISTER["list_signals"], {}))
    assert "len(rader) >= %d" % kodmall.MAX_POSTER in kod
    assert "kodmall.MAX_POSTER" in kod, "talet ska bara sin harkomst i mallen"
    assert '"avkortad": avkortad' in kod, "en klippt lista maste saga det"


def test_ocksa_portslingan_bar_taket():
    """En obegransad PortCount hade kunnat spranga bryggans 1 MiB-kropp."""
    kod = kod_for("signal_map_info",
                  V.validera_argument(REGISTER["signal_map_info"],
                                      {"component": "Bana", "map": "M"}))
    assert "len(portar) >= %d" % kodmall.MAX_POSTER in kod


def test_okand_hjalpare_i_mallen_kastar():
    """Trasig fixtur for mallens egen hjalparuppslagning."""
    with pytest.raises(KeyError):
        S._egna(["_finns_inte"])


def test_filtren_star_faktiskt_i_den_genererade_koden():
    """Ett filter som inte hamnar i koden ar ett filter som inte filtrerar."""
    v = REGISTER["list_signals"]
    utan = kod_for("list_signals", V.validera_argument(v, {}))
    med = kod_for("list_signals", V.validera_argument(
        v, {"component": "Bana", "signal_type": "VC_REALSIGNAL",
            "direction": "output", "name_contains": "ST010"}))
    assert '_app().Components' in utan
    assert 'if "ST010" not in b.Name' not in utan
    assert '_komp(_s(u"Bana"))' in med
    assert '"VC_REALSIGNAL"' in med
    assert '"output"' in med
    assert '_s(u"ST010") not in b.Name' in med


def test_okartlagd_filtrerar_pa_null_och_inte_pa_en_etikett():
    kod = kod_for("list_signals", V.validera_argument(
        REGISTER["list_signals"], {"direction": "okartlagd"}))
    assert 'if post["direction"] is not None:' in kod
    assert '"okartlagd"' not in kod


# ==========================================================================
# 9. svaret tillbaka
# ==========================================================================

def test_ett_lasande_verktyg_lamnar_ett_provat_resultat(utf):
    r = utf.utfor("list_signals", {})
    assert r.op == "exec"
    assert not r.koad
    assert set(r.resultat) == {"signals", "antal", "avkortad", "notering"}


def test_ett_svar_som_inte_haller_schemat_avvisas(utf, brygga, monkeypatch):
    monkeypatch.setattr(brygga, "_resultat", lambda args: {"antal": 1})
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("list_signals", {})
    assert "signals saknas" in str(e.value)


def test_tyst_stdout_ar_inte_ett_godkannande(utf, brygga, monkeypatch):
    """I3: sista raden var ingen JSON -> mallen har inte svarat."""
    monkeypatch.setattr(brygga, "_resultat", lambda args: None)
    with pytest.raises(V.Svarsfel) as e:
        utf.utfor("get_signal", {"component": "Bana", "signal": "S1"})
    assert "ingen JSON" in str(e.value)


# ==========================================================================
# 10. uppkopplingen (60_plc.md)
# ==========================================================================

def test_connectivity_status_ar_ett_data_verktyg_som_inte_ror_bryggan(utf, brygga):
    r = utf.utfor("connectivity_status", {})
    assert r.mode == "data" and r.effect == "read"
    assert brygga.logg == []
    assert r.resultat["role"] == "client"
    assert r.resultat["readable_from_python"] is False
    assert r.resultat["python_api_hits"] == 0
    assert r.resultat["python_api_symbols"] == []


def test_connectivity_status_svarar_pa_alla_tre_fragorna():
    svar = DATA["connectivity_status"]({"question": "allt"})
    nycklar = [a["question"] for a in svar["sections"]]
    assert nycklar == sorted(S.FRAGOR)
    assert set(nycklar) == {"servrar", "tillstand", "variabler"}
    for avsnitt in svar["sections"]:
        assert avsnitt["dotnet_members"], avsnitt["question"]
        for m in avsnitt["dotnet_members"]:
            assert m["summering"].strip(), m["medlem"]
            assert m["fil"].startswith("docs/referens/vc_dotnet")
            assert m["assembly"].startswith("VisualComponents.Connectivity")


def test_connectivity_status_kan_avgransas_till_en_fraga():
    svar = DATA["connectivity_status"]({"question": "tillstand"})
    assert [a["question"] for a in svar["sections"]] == ["tillstand"]


def test_rollen_bevisas_ur_kallan_och_inte_ur_en_omskrivning():
    svar = DATA["connectivity_status"]({"question": "allt"})
    bevis = svar["role_evidence"]
    assert bevis["medlem"].endswith("IOpcUAServer.Session")
    assert "OPC UA session" in bevis["summering"]
    assert bevis["fil"].endswith("VisualComponents.Connectivity.OpcUA.xml")


def test_en_uppfunnen_dotnet_medlem_kastar():
    """Trasig fixtur: kallan far inte kunna kringgas med ett hittat namn."""
    with pytest.raises(V.Schemafel) as e:
        S._dotnet("P:VisualComponents.Connectivity.Shared.IServer.Servers")
    assert "is not in" in str(e.value)
    # ...och en riktig medlem gar igenom.
    assert S._dotnet(
        "P:VisualComponents.Connectivity.Shared.IServer.Connected")["summering"]


def test_python_luckan_ar_matt_och_inte_pastadd():
    """python_api_hits ska raknas om ur indexet, inte tros pa.

    Faller den har raden har VC fatt en Python-uppkopplingsyta, och da ar
    connectivity_status text inte langre sann - den ska da skrivas om, inte
    tystas.
    """
    monster = re.compile(S.PYTHONLUCKA_MONSTER, re.I)
    traffar = sorted({s.fullnamn for s in INDEX.symboler
                      if monster.search(s.namn)})
    assert traffar == [], traffar
    assert list(S.PYTHONLUCKA_TRAFFAR) == traffar


def test_svaret_bar_monstret_siffran_raknades_med():
    """Siffrans harkomst hor till siffran: 0 utan matmetod gar inte att prova om."""
    svar = DATA["connectivity_status"]({"question": "allt"})
    assert svar["python_api_pattern"] == S.PYTHONLUCKA_MONSTER
    re.compile(svar["python_api_pattern"], re.I)
    assert svar["python_api_symbols"] == []
    assert svar["python_api_hits"] == len(svar["python_api_symbols"])


def test_luckmonstret_kan_traffa():
    """Trasig fixtur: monstret maste kunna hitta nagot alls."""
    monster = re.compile(S.PYTHONLUCKA_MONSTER, re.I)
    assert monster.search("ConnectivityCore")
    assert monster.search("IOpcUAServer")
    assert monster.search("IVariableGroup")
    assert not monster.search("findComponent")
    # MATT: de tva som ett losare monster traffade av misstag och som fick
    # luckan att se stangd ut.
    assert not monster.search("getCurveLoopCurve")
    assert not monster.search("VC_STATEMENT_RESERVERESOURCE")


def test_den_oppna_vagen_pekar_pa_verktyg_som_finns():
    """En hanvisning till ett verktyg som inte finns ar en trasig hanvisning."""
    svar = DATA["connectivity_status"]({"question": "allt"})
    for namn in svar["open_path"]:
        assert namn in REGISTER, namn


def test_en_saknad_dotnet_kalla_kastar_i_stallet_for_att_tiga(tmp_path):
    """S5: ett index som ar tomt ar inget index."""
    with pytest.raises(V.Schemafel) as e:
        S._las_dotnet(str(tmp_path))
    assert "missing its source" in str(e.value)


# ==========================================================================
# 11. PLC-inventeringen (grind 3 i 50_grindar.md)
# ==========================================================================

def test_inventeringen_bar_det_grind_3_behover():
    """Namn, typ, riktning och komponent per tagg - och ingenting pahittat."""
    rad = REGISTER["signal_inventory"].returns["properties"]["declarations"]
    falt = set(rad["items"]["properties"])
    assert {"tag", "component", "type", "direction", "safety"} <= falt


def test_inventeringen_letar_efter_namnkollisioner():
    """Ett platt PLC-namnrum tal inte tva taggar med samma namn."""
    kod = kod_for("signal_inventory",
                  V.validera_argument(REGISTER["signal_inventory"], {}))
    assert 'dubbletter.append' in kod
    assert '"duplicates": dubbletter' in kod
    assert '"without_type": utan_typ' in kod


def test_inventeringen_hittar_inte_pa_nagot_taggnamn():
    """I10: modellen skriver aldrig deklarationer, och verktyget inte heller.

    Taggen ar signalens namn ur scenen, oforandrad. Faller den har raden har
    nagon lagt in en namnomskrivning i mallen.
    """
    kod = kod_for("signal_inventory",
                  V.validera_argument(REGISTER["signal_inventory"], {}))
    assert '"tag": post["name"]' in kod
    for misstankt in ("ST%03d", ".replace(", ".format(", "prefix"):
        assert misstankt not in kod, misstankt


def test_riktningen_harleds_och_gissas_aldrig_ur_namnet():
    kod = kod_for("list_signals",
                  V.validera_argument(REGISTER["list_signals"], {}))
    assert "def _riktningar(komp):" in kod
    assert "getInternalPortSignal" in kod
    assert "m.Direction" in kod


def test_noteringen_om_riktning_foljer_med_i_svaret():
    """En arlighetsrad i specen ar ingen arlighetsrad i svaret."""
    for namn in ("list_signals", "signal_info", "signal_inventory"):
        v = REGISTER[namn]
        assert "notering" in v.returns["required"], namn
    kod = kod_for("signal_inventory",
                  V.validera_argument(REGISTER["signal_inventory"], {}))
    assert "grind 3" in kod
