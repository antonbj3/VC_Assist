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
