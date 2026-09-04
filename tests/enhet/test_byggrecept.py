# -*- coding: utf-8 -*-
"""L0/L1 for byggrecepten (docs/spec/49_komponentmodellen.md). Kors utan VC.

Fyra saker provas, och de tva mellersta ar de viktiga:

1. FORMEN. Varje recepts kod parsar, ar Python 2.7-kompatibel (inga
   f-strangar, ingen print-sats, inget "except E, e"), slutar med _svara()
   och skickar varje namn till VC genom _s() (M-05).
2. NAMNEN. Koden passerar api_index-validatorn UTAN fel och utan
   obestambarheter, och varje attributnamn och VC_-konstant i koden finns i
   indexet. Ett uppfunnet namn ar ett I9-brott, och det ar den hallucination
   recepten ar byggda for att inte kunna bara.
3. GRINDEN. Bryggans skrivgrind.granska() MASTE doma varje recept som
   skrivande (de skapar komponenter), och inget recept far skapa ett
   skriptbeteende (M-13) eller anropa save().
4. HYPOTESERNA. Varje id bar en kalla, ar namnt i spec 49, provas i den
   ordning hypoteser.py sager, och varje VC-namn i hypotestexten finns.

95_testprotokoll.md: varje grind har en trasig fixtur som MASTE falla.
"""
import ast
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import skrivgrind                                        # noqa: E402
from vc_assist_svc import byggrecept as B                # noqa: E402
from vc_assist_svc.api_index import bygg_index, Validator  # noqa: E402

SPEC = os.path.join(_ROT, "docs", "spec", "49_komponentmodellen.md")

# Samma lista som test_verktyg.py: konstruktioner som inte finns i 2.7.
FORBJUDNA_NODER = ("JoinedStr", "FormattedValue", "NamedExpr", "AnnAssign",
                   "AsyncFunctionDef", "Await", "AsyncFor", "AsyncWith",
                   "Match", "TryStar")
_PY2_PRINT = re.compile(r"^[ \t]*print[ \t]+[^(=\n]", re.MULTILINE)
_PY2_EXCEPT = re.compile(r"^[ \t]*except[ \t]+\w+[ \t]*,", re.MULTILINE)

# Attributnamn som inte ar VC-namn: Pythons egna och de moduler mallen
# importerar (json.dumps, vcVector.new ar VC och finns i indexet).
_PYTHON_ATTRIBUT = frozenset(
    n for t in (str, bytes, list, dict, tuple, set, int, float, object)
    for n in dir(t)) | {"dumps", "__name__", "exc_info"}

# Namn den genererade koden far anvanda utan att definiera dem (som i
# test_verktyg.py, plus _s som recepten binder sjalva vid behov).
VC_GLOBALER = {"getApplication", "json", "vcVector", "vcMatrix"}


@pytest.fixture(scope="module")
def index():
    return bygg_index()


@pytest.fixture(scope="module")
def validator(index):
    return Validator(index)


def alla_anrop():
    for namn in sorted(B.EXEMPEL):
        for arg in B.EXEMPEL[namn]:
            yield namn, arg


ANROP = list(alla_anrop())
ANROP_ID = ["%s:%s" % (n, ",".join(sorted(a)) or "-") for n, a in ANROP]


# ---- 0. tackning -----------------------------------------------------------

def test_exempellistan_tacker_alla_recept():
    assert set(B.EXEMPEL) == set(B.RECEPT)
    for namn in B.RECEPT:
        assert B.EXEMPEL[namn], "receptet %s saknar exempel" % namn


def test_okant_recept_ar_ett_fel_inte_en_gissning():
    with pytest.raises(KeyError):
        B.generera("transportoer", {"name": "x"})


def test_okand_falttyp_ar_ett_fel():
    with pytest.raises(ValueError):
        B.generera("transportor", {"name": "x", "falttyp": "flode"})


def test_buffert_utan_platser_avvisas():
    with pytest.raises(ValueError):
        B.generera("buffert", {"name": "x", "kapacitet": 0})


# ---- 1. formen ---------------------------------------------------------------

@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_koden_parsar_och_ar_py2_kompatibel(namn, arg):
    kod = B.generera(namn, arg)
    trad = ast.parse(kod)
    for nod in ast.walk(trad):
        assert type(nod).__name__ not in FORBJUDNA_NODER, (
            "%s anvander %s som inte finns i Python 2.7"
            % (namn, type(nod).__name__))
    assert not _PY2_PRINT.search(kod), "print-sats i %s" % namn
    assert not _PY2_EXCEPT.search(kod), "except E, e i %s" % namn
    assert "from __future__ import print_function" in kod


@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_sista_satsen_ar_svaret(namn, arg):
    """31_brygga_protokoll.md: JSON pa sista raden av stdout. Mallens _svara
    ar den enda vagen dit, och den maste vara sista satsen."""
    trad = ast.parse(B.generera(namn, arg))
    sista = trad.body[-1]
    assert isinstance(sista, ast.Expr) and isinstance(sista.value, ast.Call)
    assert isinstance(sista.value.func, ast.Name)
    assert sista.value.func.id == "_svara"


@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_namn_till_vc_gar_genom_s(namn, arg):
    """M-05: VC 4.10 tar bara bytestrangar. Varje argumentstrang som nar VC
    ska sta som _s(u"...") i koden, aldrig som naken literal."""
    kod = B.generera(namn, arg)
    for nyckel, varde in arg.items():
        # falttyp ar en VALJARE som blir en VC_-konstant, inte en strang
        # som nar VC.
        if not isinstance(varde, str) or nyckel == "falttyp":
            continue
        assert '_s(u"%s")' % varde in kod, (nyckel, varde)
        naken = re.findall(r'(?<!\(u)"%s"' % re.escape(varde), kod)
        assert not naken, "%r star naken i koden for %s" % (varde, namn)


@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_inga_dynamiska_uppslag(namn, arg):
    """getattr/setattr/hasattr/eval gor bade api_index-validatorn och
    skrivgrinden blinda. Recepten ska vara helt statiskt domda."""
    trad = ast.parse(B.generera(namn, arg))
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Call) and isinstance(nod.func, ast.Name):
            assert nod.func.id not in skrivgrind.OGENOMSKINLIGA, nod.func.id


# ---- 2. namnen -----------------------------------------------------------------

@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_validatorn_godkanner_utan_uppfunna_namn(namn, arg):
    g = validator_for(namn, arg)
    assert g.godkand, g.rapport()
    # Ett godkannande utan kontrollerade namn ar tomt. Minst granssnittet,
    # sektionen och faltet ska ha domts pa typ.
    assert g.kontrollerade_namn >= 8, g.rapport()


def validator_for(namn, arg):
    return Validator(bygg_index()).granska(B.generera(namn, arg))


@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_varje_attributnamn_finns_i_indexet(namn, arg, index):
    """Validatorn domer bara det den kan typa; recepten har egna hjalpare
    vars parametrar ar otypade. Darfor ocksa en global kontroll: varje
    attributnamn i koden finns NAGONSTANS i API-indexet."""
    trad = ast.parse(B.generera(namn, arg))
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Attribute) and nod.attr not in _PYTHON_ATTRIBUT:
            assert index.finns(nod.attr), (
                "rad %d: attributet %s finns inte i API-indexet"
                % (nod.lineno, nod.attr))


@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_varje_konstant_i_koden_finns(namn, arg, index):
    kod = B.generera(namn, arg)
    for konst in sorted(set(re.findall(r"\bVC_[A-Z0-9_]+\b", kod))):
        assert konst in index.konstanter, konst


@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_inga_fria_namn_utover_bryggans(namn, arg):
    """Allt koden anvander ar antingen bundet i koden, inbyggt i Python,
    eller ett av bryggans globaler. Ett fjarde slag ar ett uppfunnet namn."""
    trad = ast.parse(B.generera(namn, arg))
    bundna = set()
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Name) and isinstance(nod.ctx, ast.Store):
            bundna.add(nod.id)
        elif isinstance(nod, (ast.FunctionDef, ast.ClassDef)):
            bundna.add(nod.name)
        elif isinstance(nod, ast.arg):
            bundna.add(nod.arg)
        elif isinstance(nod, ast.ExceptHandler) and nod.name:
            bundna.add(nod.name)
        elif isinstance(nod, (ast.Import, ast.ImportFrom)):
            for a in nod.names:
                bundna.add((a.asname or a.name).split(".")[0])
    inbyggda = set(dir(__builtins__)) if isinstance(__builtins__, dict) is False \
        else set(__builtins__)
    inbyggda |= {"unicode", "long", "basestring", "xrange"}
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Name) and isinstance(nod.ctx, ast.Load):
            n = nod.id
            if n.startswith("VC_") or n in bundna or n in inbyggda \
                    or n in VC_GLOBALER or n == "_s":
                continue
            raise AssertionError("rad %d: fritt namn %s" % (nod.lineno, n))


def test_trasig_fixtur_uppfunnet_metodnamn_faller(validator, index):
    """Grinden maste kunna falla. Ett recept med ett pahittat namn ska ge FEL.

    Tva lager, for att de ser olika saker. Validatorn domer pa TYP och ser
    anropet i sondera_falt, dar granssnittet skapas pa toppniva. I
    transportor sker samma anrop inne i hjalparen _granssnitt(), vars
    parametrar ar otypade -- dar ar validatorn blind (uttalat i
    api_index.py) och den globala attributkontrollen ar det som faller."""
    kod = B.generera("sondera_falt", {})
    trasig = kod.replace("createSection(", "createSektion(")
    assert trasig != kod
    g = validator.granska(trasig)
    assert not g.godkand
    assert any(f.namn.endswith("createSektion") for f in g.fel), g.rapport()

    kod = B.generera("transportor", {"name": "x"})
    trasig = kod.replace("createSection(", "createSektion(")
    assert validator.granska(trasig).godkand, "validatorn ser inte in i hjalparen"
    attribut = {n.attr for n in ast.walk(ast.parse(trasig))
                if isinstance(n, ast.Attribute)}
    assert "createSektion" in attribut
    assert not index.finns("createSektion")


def test_trasig_fixtur_uppfunnen_konstant_faller(validator):
    kod = B.generera("sanka", {"name": "x"})
    trasig = kod.replace("VC_COMPONENTCONTAINER", "VC_CONTAINERBEHAVIOUR")
    g = validator.granska(trasig)
    assert any(f.sort == "okand_konstant" for f in g.fel), g.rapport()


# ---- 3. grinden ------------------------------------------------------------------

@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_skrivgrinden_domer_recepten_som_skrivande(namn, arg):
    dom = skrivgrind.granska(B.generera(namn, arg))
    assert dom.skriver, "%s slapp forbi skrivgrinden som lasande" % namn
    assert any("create" in s or "connect" in s for s in dom.skal), dom.skal


@pytest.mark.parametrize("namn,arg", ANROP, ids=ANROP_ID)
def test_inget_recept_skapar_skript_eller_dodar_pumpen(namn, arg):
    """M-13: ett skriptbeteende stoppar simuleringen och bryggan dor. Sankan
    ar darfor en behallare och inte en fornstorare (hypotes D2)."""
    kod = B.generera(namn, arg)
    assert skrivgrind.skapar_skriptbeteende(kod) == []
    assert skrivgrind.dodar_pumpen(kod) == []


def test_trasig_fixtur_skriptsanka_fastnar():
    kod = B.generera("sanka", {"name": "x"}).replace(
        "VC_COMPONENTCONTAINER", "VC_PYTHONSCRIPT")
    assert skrivgrind.skapar_skriptbeteende(kod)


# ---- 4. hypoteserna ----------------------------------------------------------------

def test_hypotesid_ar_unika_och_har_kalla():
    idn = [h.id for h in B.HYPOTESER]
    assert len(idn) == len(set(idn))
    for h in B.HYPOTESER:
        assert h.kalla.strip(), h.id
        assert h.status in (B.BELAGT, B.HYPOTES, B.MATT), h.id
        assert h.fraga in "ABCDEFG" and h.id.startswith(h.fraga), h.id
        assert (h.rang == 0) == (h.status != B.HYPOTES), (
            "%s: rang 0 ar reserverat for belagt/matt" % h.id)


def test_provordningen_ar_entydig_per_fraga():
    for fraga in "ABCDEFG":
        provas = [h for h in B.per_fraga(fraga) if h.status == B.HYPOTES]
        ranger = [h.rang for h in provas]
        # Tva hypoteser far dela rang bara nar de svarar pa OLIKA delfragor
        # (D1 matare / D2 sanka / D4 buffert). Inom samma delfraga ar
        # ordningen total, och det provas har for B, dar allt hanger.
        if fraga == "B":
            assert ranger == sorted(ranger) and len(set(ranger)) == len(ranger)
    assert B.provordning("B") == ("B1", "B2", "B3", "B4", "B5", "B6")


def test_varje_hypotes_ar_namnd_i_specen():
    assert os.path.exists(SPEC), SPEC
    with open(SPEC, encoding="utf-8") as f:
        text = f.read()
    for h in B.HYPOTESER:
        assert re.search(r"\b%s\b" % h.id, text), "%s saknas i spec 49" % h.id


def test_varje_vc_namn_i_hypotestexten_finns(index):
    for h in B.HYPOTESER:
        for konst in re.findall(r"\bVC_[A-Z0-9_]+\b", h.text + " " + h.kalla):
            assert konst in index.konstanter, (h.id, konst)
        for typ in re.findall(r"\bvc[A-Z][A-Za-z0-9]+\b", h.text):
            assert typ in index.typer, (h.id, typ)


def test_recepten_bokfor_bara_kanda_hypotesid():
    """Varje id koden skriver i 'forsok' maste finnas i hypoteser.py; annars
    pekar matningen pa en hypotes som inte star nagonstans."""
    for namn, arg in ANROP:
        kod = B.generera(namn, arg)
        for hid in set(re.findall(r'_s\(u"([A-G]\d)"\)', kod)):
            assert hid in B.PER_ID, (namn, hid)


def test_bindstegen_i_koden_foljer_provordningen():
    """Rangordningen ar data i hypoteser.py. Koden far inte ha en egen."""
    kod = B.generera("transportor", {"name": "x"})
    steg = re.findall(r'\("(B\d)", ', kod)
    assert steg == ["B1", "B2", "B3", "B4"], steg


def test_falttyperna_pekar_pa_kanda_konstanter(index):
    for konst in B.FALTTYPER.values():
        assert konst in index.konstanter, konst
    for konst in B.FALTKONSTANTER + B.BETEENDEKONSTANTER:
        assert konst in index.konstanter, konst
    assert B.FALTTYPER["flow"] == "VC_FLOWFIELD"      # rang 1 (B1)
