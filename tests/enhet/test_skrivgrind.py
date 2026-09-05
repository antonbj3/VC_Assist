# -*- coding: utf-8 -*-
"""L0: skrivgrinden. Kalla: 45_verktyg.md, tests/protocol/fas1_bryggan.md."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "ext", "vc_addon", "vc_assist"))
import skrivgrind as S  # noqa: E402

LASER = [
    'import json; print(json.dumps({"a": 1}))',
    'print(app.findComponent("Robot").Name)',
    'n = [x.Name for x in app.Components]; print(len(n))',
    'print(c.getProperty("P").Value)',
    'for c in app.Components:\n    print(c.Name, c.ConnectedComponents)',
    'x = 1\ny = [x for x in range(3)]\nprint(y)',
    'def setup():\n    return 1\nprint(setup())',
    'import time; time.sleep(0.01)',
    'print(open("/tmp/x").read())',
    'print(iface.canConnect(other))',
    'print(node.WorldPositionMatrix)',
]

SKRIVER = [
    'c.Name = "nytt"',
    'c.setProperty("P", 1)',
    'c.set_property("P", 1)',
    'app.createComponent()',
    'app.deleteComponent(c)',
    'app.load("uri")',
    'iface.connect(other)',
    'open("/tmp/x","w").write("a")',
    'open("/tmp/x", mode="a")',
    'getattr(app, namn)()',
    'setattr(c, "Name", "x")',
    'eval("c.Name = 1")',
    'm[0] = 3',
    'import os; os.remove("/tmp/x")',
    'sim.run(10)',
    'del c.Name',
    'lst.append(3)',
    'node.PositionMatrix = m',
]


@pytest.mark.parametrize("kod", LASER)
def test_lasande_kod_slipper_igenom(kod):
    d = S.granska(kod)
    assert d.skriver is False, "flaggades som skrivande: %r" % d.skal


@pytest.mark.parametrize("kod", SKRIVER)
def test_skrivande_kod_fastnar(kod):
    d = S.granska(kod)
    assert d.skriver is True
    assert d.skal, "en dom maste kunna saga VARFOR"


def test_otolkbar_kod_raknas_som_skrivande():
    """Felet ska falla at det hallet. Kod vi inte kan lasa ar inte ofarlig."""
    d = S.granska("def (:")
    assert d.skriver is True
    assert "gar inte att tolka" in d.skal[0]


def test_prefixet_traffar_pa_ordgrans_inte_pa_bokstaver():
    for ord_ in ("setup", "runtime", "startswith", "connected", "additional"):
        assert S._ar_muterande_namn(ord_) is False, ord_
    for ord_ in ("set", "setProperty", "set_property", "run", "removeAll"):
        assert S._ar_muterande_namn(ord_) is True, ord_


# ---- bokforing i en egen behallare ar ingen scenandring ------------------

LOKAL_BOKFORING = [
    'ut = {}\nut["a"] = 1\nprint(ut)',
    'ut = {}\nut["a"] = {}\nut["a"]["b"] = 2\nprint(ut)',
    'rader = []\nrader.insert(0, 1)\nut = dict()\nut["n"] = len(rader)\nprint(ut)',
    'ut = {}\nfor c in app.Components:\n    ut[c.Name] = c.Uri\nprint(ut)',
]

FRAMMANDE_INDEX = [
    'd = comp.Properties\nd[0] = 1',
    'comp.Properties[0] = 1',
    'ut = {}\nut = comp.Properties\nut["a"] = 1',       # namnet ombundet
    'okand[3] = 7',
]


@pytest.mark.parametrize("kod", LOKAL_BOKFORING)
def test_skrivning_i_egen_behallare_ar_lasande(kod):
    d = S.granska(kod)
    assert d.skriver is False, d.skal


@pytest.mark.parametrize("kod", FRAMMANDE_INDEX)
def test_indexskrivning_i_nagot_annat_ar_skrivande(kod):
    assert S.granska(kod).skriver is True


# ---- hal funna av verktygsregistrets korsprov 2026-09-04 -----------------

HAL_2026_09_04 = [
    'k = app.findComponent("R")\nk.clone()',
    'c.clone()',
    'c.makeUnique()',
    'c.transfer(nod)',
    'c.attach(annan)',
    'c.detach()',
    'sim.halt()',
]


@pytest.mark.parametrize("kod", HAL_2026_09_04)
def test_hal_funna_av_korsprovet_ar_stangda(kod):
    """clone() domdes som LASANDE och slapp forbi kon. Regressionsprov."""
    assert S.granska(kod).skriver is True, kod


# ---- skriptbeteenden, den enda operation som dodar pumpen (M-13) ---------

def test_skriptbeteende_upptacks():
    for kod in ("c.createBehaviour(VC_SCRIPT, 'x')",
                "c.createBehaviour(VC_PYTHONSCRIPT, 'x')",
                "b.Script = 'from vcScript import *'"):
        assert S.skapar_skriptbeteende(kod), kod


def test_vanligt_scenbygge_ar_inte_ett_skriptbeteende():
    """M-13: allt annat scenbygge overlever. Grinden far inte bli bredare
    an den matning som motiverar den."""
    for kod in ("c = app.createComponent()",
                "c.createBehaviour(VC_BOOLEANSIGNAL, 'Sig')",
                "c.createProperty(VC_REAL, 'P')",
                "app.deleteComponent(c)",
                "c.PositionMatrix = m"):
        assert S.skapar_skriptbeteende(kod) == [], kod


def test_save_ar_dodande_men_inte_ett_skriptbeteende():
    """Tva olika klasser med olika politik: skriptbeteenden AVVISAS, save
    TILLATS men markeras. Att blanda ihop dem tar bort en formaga som behovs."""
    assert S.dodar_pumpen("app.save('file:///x.vcmx')")
    assert S.skapar_skriptbeteende("app.save('file:///x.vcmx')") == []
    assert S.skapar_skriptbeteende("c.createBehaviour(VC_SCRIPT, 'x')")
    assert S.dodar_pumpen("c.createBehaviour(VC_SCRIPT, 'x')") == []


def test_vanligt_scenbygge_dodar_inte_pumpen():
    for kod in ("app.createComponent()", "app.deleteComponent(c)",
                "c.PositionMatrix = m", "print(c.Name)"):
        assert S.dodar_pumpen(kod) == [], kod


# ---- hal funna av motbevisningen 2026-09-04 -----------------------------

DUNDERVAGAR = [
    'c.__setattr__("Name", "x")',
    'setattr(c, "Name", "x")',
    'c.__setitem__(0, 1)',
    'c.__delattr__("Name")',
]


@pytest.mark.parametrize("kod", DUNDERVAGAR)
def test_dundervagen_runt_en_tilldelning_ar_skrivande(kod):
    """c.__setattr__("Name","x") gor exakt vad c.Name = "x" gor. Grinden
    domde det som LASANDE, alltsa kordes det utan ko."""
    assert S.granska(kod).skriver is True, kod


SKRIPT_VIA_OMVAG = [
    't = VC_SCRIPT\nc.createBehaviour(t, "x")',
    'typ = VC_PYTHONSCRIPT\nb = c.createBehaviour(typ, "s")',
    'k = "Script"\nsetattr(b, k, "x")',
    'setattr(b, "Script", "x")',
    'c.createBehaviour(valj_typ(), "x")',
    'c.createBehaviour()',
]


@pytest.mark.parametrize("kod", SKRIPT_VIA_OMVAG)
def test_skriptbeteende_via_omvag_upptacks(kod):
    """Ett mellanled racker for att komma runt en grind som domer stavning.
    Att skapa ett skriptbeteende dodar bryggan utan vag tillbaka (M-13), sa
    grinden ar fail-closed: gar typen inte att avgora raknas den som skript."""
    assert S.skapar_skriptbeteende(kod), kod


VANLIGT_BETEENDE = [
    'c.createBehaviour(VC_BOOLEANSIGNAL, "Sig")',
    't = VC_ONEWAYPATH\nc.createBehaviour(t, "Path")',
    'c.createBehaviour(VC_TRANSPORT, "Tr")',
    'setattr(c, "Name", "x")',
]


@pytest.mark.parametrize("kod", VANLIGT_BETEENDE)
def test_vanliga_beteenden_flaggas_inte_som_skript(kod):
    """Fail-closed far inte bli fail-allt. Ett bundet VC_-namn som INTE ar en
    skripttyp ska ga igenom."""
    assert S.skapar_skriptbeteende(kod) == [], kod


# --- ett VC-objekt i en egen behallare var en oppning forbi kon (M-94 fynd 2) --
#
# Undantaget for "eget behallaranrop" vandrade rotnamnet genom Subscript och
# Attribute. En egen dict eller lista med ett VC-objekt i blev darfor en vag
# rakt forbi grinden - och bryggan kor da koden utan att den passerat
# godkannandekon (I12). Alla tre foll INTE fore rattelsen.

@pytest.mark.parametrize("kod,vad", [
    ('d = {"app": getApplication()}\nd["app"].deleteComponent(x)\n',
     "VC-objekt i en egen dict"),
    ('L = [getApplication()]\nL[0].deleteComponent(x)\n',
     "VC-objekt i en egen lista"),
    ('d = {}\nd["a"] = {}\nd["a"]["b"].setProperty(1)\n',
     "tva niva ned i egna behallare"),
])
def test_ett_vc_objekt_i_en_egen_behallare_slipper_inte_forbi(kod, vad):
    dom = S.granska(kod)
    assert dom.skriver, "%s slapptes igenom" % vad


@pytest.mark.parametrize("kod", [
    'rader = []\nrader.append(1)\n',
    'ut = {}\nut.update({"a": 1})\n',
    'ut = {}\nut["k"] = 1\n',
    'ut = dict()\nut.pop("a", None)\n',
])
def test_bokforing_i_en_egen_behallare_slapps_fortfarande_igenom(kod):
    """Andra halvan. Undantaget finns for att ett LASANDE skript som samlar
    sitt svar i en dict inte ska fallas - annars faller nastan alla, eftersom
    svaret gar tillbaka som JSON. En rattelse som tar bort det gor grinden
    obrukbar i stallet for strangare."""
    assert not S.granska(kod).skriver, "bokforing fastnade"


@pytest.mark.parametrize("kod", [
    'p = {}\np["external"] = []\np["external"].append(1)\n',
    'd = {}\nd["a"] = []\nd["a"].extend([1, 2])\n',
])
def test_bokforing_GENOM_en_egen_behallare_slapps_ocksa(kod):
    """Forsta rattelsen nekade allt som nas genom en behallare, och var for hard.

    MATT: sex roda prov i test_verktyg_signaler och test_verktyg_transport -
    `p["external"].append(...)` ar ren bokforing i LASANDE verktyg. Gransen gar
    pa metodens art, inte pa djupet: en lista har append, en VC-komponent har
    deleteComponent. Darfor en sluten vitlista i stallet for prefixheuristiken,
    som sager ja till bada.
    """
    assert not S.granska(kod).skriver


def test_harnessen_lanar_vitlistan_i_stallet_for_att_kopiera_den():
    """Tva kopior som glider isar vore ett hal i den ena.

    turordning.py importerar redan skrivgrind (`_sista_namnet`), sa listan gar
    att dela. Provet halller fast att den DELAS och inte dupliceras - en kopia
    hade sett lika ut i dag och kunnat sluta gora det i morgon.
    """
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.normpath(_os.path.join(
        _os.path.dirname(__file__), "..", "..", "svc")))
    from vc_assist_svc.harness import turordning as T
    kalla = _os.path.join(_os.path.dirname(T.__file__), "turordning.py")
    with open(kalla, encoding="utf-8") as f:
        text = f.read()
    assert "skrivgrind.BEHALLARMETODER" in text
    assert "BEHALLARMETODER = (" not in text, "listan ar kopierad, inte lanad"


def test_ett_kedjat_anrop_pa_ett_ANROPS_resultat_ar_fortfarande_konservativt():
    """ut.setdefault("k", []).clear() flaggas, och det ar oforandrat.

    `_rotnamn` vandrar genom Subscript och Attribute men inte genom Call, sa
    mottagaren blir okand. Att flagga ar ratt hall for en skrivgrind, och
    beteendet ar detsamma som fore M-94:s rattelse - det star har for att ingen
    ska tro att rattelsen orsakade det.
    """
    assert S.granska('ut = {}\nut.setdefault("k", []).clear()\n').skriver


DUNDERSKRIVNINGAR_MB = [
    ('c.__setattr__("Name", "x")', 'samma sak som c.Name = "x", som fastnar'),
    ('object.__setattr__(c, "Name", "x")', "omvägen via basklassen"),
    ("d.__setitem__(0, 1)", "samma sak som d[0] = 1, som fastnar"),
    ("comp.Properties.__delitem__(0)", "samma sak som del comp.Properties[0]"),
]


@pytest.mark.parametrize("kod,skal", DUNDERSKRIVNINGAR_MB,
                         ids=[k for k, _ in DUNDERSKRIVNINGAR_MB])
def test_en_skrivning_skriven_som_dunderanrop_maste_ocksa_fastna(kod, skal):
    dom = S.granska(kod)
    assert dom.skriver is True, (
        "%r dömdes som LÄSANDE och skulle köras direkt i exec, utan kö (%s)"
        % (kod, skal))


def test_samma_operation_far_inte_bero_pa_hur_den_stavas():
    """Det egentliga felet i klartext: två skrivningar av samma attribut,
    en fastnar och en går fri."""
    punkt = S.granska('c.Name = "x"').skriver
    dunder = S.granska('c.__setattr__("Name", "x")').skriver
    assert punkt == dunder, (
        "c.Name = 'x' -> skriver=%r men c.__setattr__('Name','x') -> skriver=%r"
        % (punkt, dunder))


SKRIPTBETEENDEN_MB = [
    ("t = VC_SCRIPT\nc.createBehaviour(t, 'x')", "typen via en variabel"),
    ("c.createBehaviour(vcConst.VC_SCRIPT, 'x')", "typen via ett attribut"),
    ("c.createBehaviour(*[VC_SCRIPT, 'x'])", "uppackade argument"),
    ("c.createBehaviour(**{'type': VC_SCRIPT, 'name': 'x'})", "nyckelordsargument"),
    ("setattr(b, 'Script', kod)", "tilldelning till .Script via setattr"),
]


@pytest.mark.parametrize("kod,skal", SKRIPTBETEENDEN_MB,
                         ids=[s for _, s in SKRIPTBETEENDEN_MB])
def test_skriptbeteende_maste_upptackas_oavsett_hur_typen_skrivs(kod, skal):
    skal_lista = S.skapar_skriptbeteende(kod)
    assert skal_lista, (
        "%r (%s) gav tom lista: pump._op_exec_queue köar den utan invändning, "
        "och vid godkännande dör bryggan utan väg tillbaka (M-13)" % (kod, skal))



