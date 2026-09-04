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
