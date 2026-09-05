# -*- coding: utf-8 -*-
"""L0/L1 for komponentmodellen (docs/spec/49_komponentmodellen.md, fas 20).

Modellen ar specens minsta uppsattningar som data. Provet halller fyra saker:

1. FORMEN. Koden modellen genererar parsar, ar giltig i bade 2.7 och 3.x,
   passerar api_index-validatorn utan uppfunna namn, och doms av bryggans
   skrivgrind som SKRIVANDE.
2. DOMAREN. `granska()` sager VILKET krav som fattas, vid namn. Ett fel som
   bara sager "gick inte" ar ingen grind, sa domen provas mot en aterlasning
   dar exakt ett krav ar borta.
3. TRASIGA FIXTURER. Varje klass har en dar ett krav utelamnats, och den MASTE
   fallas. En kravlista som aldrig provats utelamnad ar en asikt.
4. SPECEN. Varje rad i modellens kravlistor star i 49_komponentmodellen.md,
   och varje regel i matchningsregeln likasa. Glider de isar faller provet --
   annars beskriver specen en modell som inte finns.

Kors utan VC. Vad koden GOR i VC mats i M-101 (tests/protocol/kor_fas20_modellen.py).
"""
import ast
import builtins
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import skrivgrind                                          # noqa: E402
from vc_assist_svc import komponentmodell as K             # noqa: E402
from vc_assist_svc.api_index import bygg_index, Validator   # noqa: E402

SPEC = os.path.join(_ROT, "docs", "spec", "49_komponentmodellen.md")

FORBJUDNA_NODER = ("JoinedStr", "FormattedValue", "NamedExpr", "AnnAssign",
                   "AsyncFunctionDef", "Await", "AsyncFor", "AsyncWith",
                   "Match", "TryStar")
_PY2_PRINT = re.compile(r"^[ \t]*print[ \t]+[^(=\n]", re.MULTILINE)
_PY2_EXCEPT = re.compile(r"^[ \t]*except[ \t]+\w+[ \t]*,", re.MULTILINE)
_PYTHON_ATTRIBUT = frozenset(
    n for t in (str, bytes, list, dict, tuple, set, int, float, object)
    for n in dir(t)) | {"dumps", "__name__", "exc_info"}
VC_GLOBALER = {"getApplication", "json", "vcVector", "vcMatrix"}

# Harkomstmarkena. Ett krav utan ett av dem ar ett antagande som ser ut som
# ett faktum, och det ar precis det som gor en spec farlig.
MARKEN = (u"MÄTT", "BELAGT", "HYPOTES")


@pytest.fixture(scope="module")
def index():
    return bygg_index()


@pytest.fixture(scope="module")
def validator(index):
    return Validator(index)


def _alla_koder():
    ut = []
    for klass in K.KLASSER:
        for arg in K.EXEMPEL[klass]:
            a = dict(arg)
            namn = a.pop("name")
            ut.append(("%s:%s" % (klass, namn), K.bygg(klass, namn, a)))
        ut.append(("%s:TRASIG" % klass,
                   K.bygg(klass, "T_" + klass, {},
                          utelamna=K.TRASIG_UTELAMNING[klass])))
    ut.append(("koppla", K.koppla("A", "B")))
    ut.append(("koppla:trasigt-par",
               K.koppla("A", "B", "OutInterface", "OutInterface",
                        vantas_ga=False)))
    return ut


KODER = _alla_koder()
KOD_ID = [n for n, _k in KODER]


# ---- 1. formen -------------------------------------------------------------

@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_koden_parsar_och_ar_py2_kompatibel(namn, kod):
    trad = ast.parse(kod)
    for nod in ast.walk(trad):
        assert type(nod).__name__ not in FORBJUDNA_NODER, (
            "%s anvander %s som inte finns i Python 2.7"
            % (namn, type(nod).__name__))
    assert not _PY2_PRINT.search(kod), "print-sats i %s" % namn
    assert not _PY2_EXCEPT.search(kod), "except E, e i %s" % namn


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_sista_satsen_ar_svaret(namn, kod):
    trad = ast.parse(kod)
    sista = trad.body[-1]
    assert isinstance(sista, ast.Expr) and isinstance(sista.value, ast.Call)
    assert sista.value.func.id == "_svara"


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_namn_till_vc_gar_genom_s(namn, kod):
    """M-05: VC 4.10:s bindning tar bara bytestrangar."""
    for vc_namn in ("Path", "Creator", "Sink", "InInterface", "OutInterface",
                    "Flow", "Kropp"):
        naken = re.findall(r'(?<!\(u)"%s"' % vc_namn, kod)
        assert not naken, "%r star naken i %s" % (vc_namn, namn)


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_inga_dynamiska_uppslag(namn, kod):
    for nod in ast.walk(ast.parse(kod)):
        if isinstance(nod, ast.Call) and isinstance(nod.func, ast.Name):
            assert nod.func.id not in skrivgrind.OGENOMSKINLIGA, nod.func.id


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_validatorn_godkanner_utan_uppfunna_namn(namn, kod, validator):
    g = validator.granska(kod)
    assert g.godkand, g.rapport()
    assert g.kontrollerade_namn >= 8, g.rapport()


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_varje_attributnamn_finns_i_indexet(namn, kod, index):
    for nod in ast.walk(ast.parse(kod)):
        if isinstance(nod, ast.Attribute) and nod.attr not in _PYTHON_ATTRIBUT:
            assert index.finns(nod.attr), (
                "%s rad %d: attributet %s finns inte i API-indexet"
                % (namn, nod.lineno, nod.attr))


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_varje_konstant_i_koden_finns(namn, kod, index):
    for konst in sorted(set(re.findall(r"\bVC_[A-Z0-9_]+\b", kod))):
        assert konst in index.konstanter, "%s: %s" % (namn, konst)


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_inga_fria_namn_utover_bryggans(namn, kod):
    trad = ast.parse(kod)
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
    inbyggda = set(dir(builtins)) | {"unicode", "long", "basestring", "xrange"}
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Name) and isinstance(nod.ctx, ast.Load):
            n = nod.id
            if (n.startswith("VC_") or n in bundna or n in inbyggda
                    or n in VC_GLOBALER or n == "_s"):
                continue
            raise AssertionError("%s rad %d: fritt namn %s"
                                 % (namn, nod.lineno, n))


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_skrivgrinden_domer_koden_som_skrivande(namn, kod):
    dom = skrivgrind.granska(kod)
    assert dom.skriver, "%s slapp forbi skrivgrinden som lasande" % namn
    assert not any("SCRIPT" in s.upper() for s in dom.skal), dom.skal


@pytest.mark.parametrize("namn,kod", KODER, ids=KOD_ID)
def test_inget_skriptbeteende_och_ingen_save(namn, kod):
    """M-13: ett skriptbeteende stoppar pumpen. save() skriver till disk."""
    assert "VC_PYTHONSCRIPT" not in kod
    assert ".save(" not in kod


# ---- 2. kravlistorna -------------------------------------------------------

def test_alla_fyra_klasser_finns():
    assert set(K.KLASSER) == {"transportor", "matare", "sanka", "buffert"}


@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_varje_krav_bar_ett_harkomstmarke(klass):
    k = K.KLASSER[klass]
    for krav in k.beteenden + k.ramar + k.egenskaper:
        assert any(krav.harkomst.startswith(m) or (" " + m) in krav.harkomst
                   or krav.harkomst.find(m) >= 0 for m in MARKEN), (
            "%s/%s saknar harkomstmarke: %r" % (klass, krav.namn, krav.harkomst))
    for g in k.granssnitt:
        assert any(m in g.harkomst for m in MARKEN), g


@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_varje_krav_sager_vad_som_hander_om_det_fattas(klass):
    k = K.KLASSER[klass]
    for krav in k.beteenden + k.ramar + k.egenskaper:
        assert krav.utan and len(krav.utan) > 30, (klass, krav.namn)
        assert krav.namn in krav.utan, (
            "%s/%s: felet namnger inte vad som fattas" % (klass, krav.namn))
    for g in k.granssnitt:
        assert g.namn in g.utan


@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_varje_klass_har_minst_ett_flodesbarande_beteende(klass):
    assert K.KLASSER[klass].beteenden, klass
    assert K.KLASSER[klass].granssnitt, klass


def test_trasig_utelamning_tacker_alla_klasser():
    assert set(K.TRASIG_UTELAMNING) == set(K.KLASSER)


def test_okand_klass_ar_ett_fel_inte_en_gissning():
    with pytest.raises(KeyError):
        K.bygg("transportoer", "x")


def test_okant_krav_att_utelamna_ar_ett_fel():
    with pytest.raises(ValueError):
        K.bygg("transportor", "x", utelamna="bandet")


# ---- 3. den trasiga fixturen skiljer sig med EXAKT ett krav ----------------

@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_trasig_fixtur_utelamnar_exakt_ett_beteende(klass):
    nyckel = K.TRASIG_UTELAMNING[klass]
    hel = K.bygg(klass, "X", {})
    trasig = K.bygg(klass, "X", {}, utelamna=nyckel)
    assert hel != trasig
    krav = [b for b in K.KLASSER[klass].beteenden if b.nyckel == nyckel]
    assert len(krav) == 1
    konstant = krav[0].konstant
    assert ("createBehaviour(%s," % konstant) in hel
    assert ("createBehaviour(%s," % konstant) not in trasig
    # Allt ANNAT ska sta kvar: granssnittet byggs, ramarna byggs.
    for g in K.KLASSER[klass].granssnitt:
        assert ('_s(u"%s")' % g.namn) in trasig, g.namn
    for ram in K.KLASSER[klass].ramar:
        assert ('_s(u"%s")' % ram.namn) in trasig, ram.namn


# ---- 4. domaren ------------------------------------------------------------

def _aterlast(klass, saknat_beteende=None, obundet=False):
    """Bygger en aterlasning som den ur VC ser ut. Namnen kommer ur modellen,
    inte ur en handskriven ordlista: da kan de inte glida isar."""
    k = K.KLASSER[klass]
    beteenden = [{"name": b.namn, "type": b.konstant, "class": "x"}
                 for b in k.beteenden if b.namn != saknat_beteende]
    beteenden += [{"name": g.namn, "type": "VC_ONETOONEINTERFACE", "class": "y"}
                  for g in k.granssnitt]
    granssnitt = []
    for g in k.granssnitt:
        bundet = saknat_beteende is None and not obundet
        granssnitt.append({
            "name": g.namn, "section": g.namn, "field": K.FALTNAMN,
            "field_type": "VC_FLOWFIELD",
            "frame": g.ram,
            "properties_after": [
                {"name": K.EGENSKAP_BETEENDE,
                 "value": "<bana>" if bundet else None},
                {"name": K.EGENSKAP_PORT, "value": 0 if bundet else -1},
            ],
            "connector": {"name": "c", "index": 0,
                          "type": g.kontakttyp} if bundet else None,
        })
    return {"built": True, "klass": klass, "component": klass.upper(),
            "features": [r.namn for r in k.ramar],
            "behaviours": beteenden, "interfaces": granssnitt}


@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_hel_uppsattning_doms_som_hel(klass):
    r = K.granska(_aterlast(klass))
    assert r.hel, r.text()
    assert r.kopplingsbar


@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_saknat_beteende_namnges_vid_namn(klass):
    """Fasens poang: felet ska saga VILKET beteende som fattas."""
    nyckel = K.TRASIG_UTELAMNING[klass]
    krav = [b for b in K.KLASSER[klass].beteenden if b.nyckel == nyckel][0]
    r = K.granska(_aterlast(klass, saknat_beteende=krav.namn))
    assert not r.hel
    assert not r.kopplingsbar
    assert r.saknade_beteenden() == [krav.namn], r.text()
    assert krav.namn in r.text()
    assert krav.konstant in r.text()
    # Ett fel som bara sager "gick inte" ar ingen grind.
    assert "gick inte" not in r.text().lower()


@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_ett_narvarande_beteende_med_obundet_falt_ar_inte_helt(klass):
    """Trasig fixtur for DOMAREN: att beteendet finns racker inte. Ett falt
    med Container = None ger canConnect False (MATT M-40/E0), sa en domare
    som bara raknade beteenden hade sagt gront om en komponent VC vagrar."""
    r = K.granska(_aterlast(klass, obundet=True))
    assert not r.hel
    assert r.saknade_beteenden() == []
    assert K.EGENSKAP_BETEENDE in r.text()


def test_domaren_avvisar_okand_klass():
    with pytest.raises(KeyError):
        K.granska({"klass": "robot"})


# ---- 5. matchningsregeln ---------------------------------------------------

def test_matchningsregeln_ar_ordnad_och_komplett():
    ids = [r.id for r in K.MATCHNINGSREGEL]
    assert ids == ["R%d" % (i + 1) for i in range(len(ids))]
    for r in K.MATCHNINGSREGEL:
        assert any(m in r.harkomst for m in MARKEN), r.id
        assert r.kravet and r.felet


def test_varfor_inte_pekar_pa_riktningsregeln_for_ut_mot_ut():
    ut = _aterlast("transportor")["interfaces"][1]
    regel, text = K.varfor_inte(ut, dict(ut))
    assert regel.id == "R5", (regel, text)
    assert "VC_CONNECTOR_OUTPUT" in text


def test_varfor_inte_pekar_pa_containern_nar_faltet_ar_obundet():
    ut = _aterlast("transportor")["interfaces"][1]
    inn = _aterlast("transportor", obundet=True)["interfaces"][0]
    regel, text = K.varfor_inte(ut, inn)
    assert regel.id == "R2", (regel, text)
    assert K.EGENSKAP_BETEENDE in text


def test_varfor_inte_tiger_nar_allt_haller():
    par = _aterlast("transportor")["interfaces"]
    regel, text = K.varfor_inte(par[1], par[0])
    assert regel is None, text


def test_bindningsordningen_star_i_koden():
    """MATT M-40: Container FORE Port. Omvand ordning nollstaller Port till
    -1 och kopplingen faller tyst. Ordningen ar inte en stilfraga."""
    kod = K.bygg("transportor", "X")
    assert (kod.index("_hitta_egenskap(falt, EGENSKAP_BETEENDE)")
            < kod.index("_hitta_egenskap(falt, EGENSKAP_PORT)"))
    assert (kod.index("beteendet.Value = agare")
            < kod.index("porten.Value = kontakt.Index"))


def test_kontakten_valjs_pa_typ_aldrig_pa_index():
    """C1 (MATT): skaparen bar Output pa index 0, banan pa index 1."""
    kod = K.bygg("matare", "X")
    assert "_kontakt(skapare, VC_CONNECTOR_OUTPUT)" in kod
    assert "Connectors[0]" not in kod
    assert "Connectors[1]" not in kod


def test_banan_uppdateras_efter_att_path_satts():
    """MATT M-40 villkor 2: utan bana.update() ar PathLength 0.0."""
    kod = K.bygg("transportor", "X")
    assert kod.index("bana.Path = [") < kod.index("bana.update()")


def test_ramarna_byggs_om():
    """MATT M-40 villkor 1: utan rebuild() ligger ramen kvar i origo."""
    assert "f.rebuild()" in K.bygg("transportor", "X")


def test_koppla_fragar_innan_den_kopplar():
    kod = K.koppla("A", "B")
    assert kod.index("canConnect") < kod.index("ga.connect(")


# ---- 6. specen och modellen far inte glida isar ---------------------------

@pytest.fixture(scope="module")
def spectext():
    with open(SPEC, "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("klass", sorted(K.KLASSER))
def test_specen_bar_modellens_kravrader(klass, spectext):
    saknade = [r for r in K.spec_rader(klass) if r not in spectext]
    assert not saknade, (
        "%d rader i modellen saknas i 49_komponentmodellen.md:\n%s"
        % (len(saknade), "\n".join(saknade[:4])))


def test_specen_bar_hela_matchningsregeln(spectext):
    for r in K.MATCHNINGSREGEL:
        assert ("**%s**" % r.id) in spectext, r.id
        assert r.kravet in spectext, r.id
        assert r.felet in spectext, r.id


def test_specen_namnger_de_trasiga_fixturerna(spectext):
    for klass, nyckel in K.TRASIG_UTELAMNING.items():
        krav = [b for b in K.KLASSER[klass].beteenden if b.nyckel == nyckel][0]
        assert krav.konstant in spectext, (klass, krav.konstant)


def test_specen_bar_paren(spectext):
    for a, b in K.PAR_SOM_SKA_GA:
        assert "%s -> %s" % (a, b) in spectext, (a, b)
    for a, b, _skal in K.PAR_SOM_INTE_GAR:
        assert "%s -> %s" % (a, b) in spectext, (a, b)
