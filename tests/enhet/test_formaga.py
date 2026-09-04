# -*- coding: utf-8 -*-
"""L0: formagerapporten. Kalla: 36_versioner.md."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "ext", "vc_addon", "vc_assist"))
import formaga as F  # noqa: E402


class FalskApp(object):
    Components = []

    def findComponent(self, n):
        return None


class KastandeApp(object):
    @property
    def Components(self):
        raise RuntimeError("kraschar vid uppslag")


def test_saknad_yta_rapporteras_som_saknad():
    r = F.formaga({"app": FalskApp()})
    assert r["ytor"]["app.Components"]["finns"] is True
    assert r["ytor"]["app.load"]["finns"] is False
    assert "app.load" in r["saknade_ytor"]


def test_yta_som_kastar_raknas_som_saknad_inte_som_finns():
    """Ett attribut som kastar ar inte en formaga. Det ska inte se ut som en."""
    r = F.formaga({"app": KastandeApp()})
    assert r["ytor"]["app.Components"]["finns"] is False
    assert "kastade" in r["ytor"]["app.Components"]["typ"]


def test_utan_objekt_blir_ytan_oprovad_inte_saknad():
    """Skillnaden mellan 'provat och borta' och 'aldrig provat' maste synas."""
    r = F.formaga({"app": FalskApp()})
    assert r["ytor"]["comp.Name"]["finns"] is None
    assert "comp.Name" in r["oprovade_ytor"]
    assert "comp.Name" not in r["saknade_ytor"]


def test_summeringen_summerar_till_antalet_provade():
    r = F.formaga({"app": FalskApp()})
    s = r["summering"]
    assert s["finns"] + s["saknas"] + s["oprovade"] == s["provade"] == len(F.YTOR)


def test_skriver_giltig_json(tmp_path):
    p = str(tmp_path / "f.json")
    F.skriv(p, {"app": FalskApp()}, extra={"port": 8901})
    with open(p) as f:
        d = json.load(f)
    assert d["port"] == 8901 and d["summering"]["provade"] == len(F.YTOR)
