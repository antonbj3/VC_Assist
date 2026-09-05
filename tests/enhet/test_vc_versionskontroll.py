# -*- coding: utf-8 -*-
"""L1: Enhetsprov for E10 - versionskontroll av VC vid start."""
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import formaga


class FalskApp(object):
    def __init__(self, ver):
        self.ProductVersion = ver


def test_vc_4_10_ar_matt():
    app = FalskApp("4.10.0.1")
    rap = formaga.formaga({"app": app})
    assert rap["vc_product_version"] == "4.10.0.1"
    assert rap["vc_version_status"] == "matt"


def test_vc_5_0_ar_oprovad_men_kraschar_inte():
    """E10: VC 5.0 ska saga oprovad, inte krascha och inte latsas fungera."""
    app = FalskApp("5.0.0.0")
    rap = formaga.formaga({"app": app})
    assert rap["vc_product_version"] == "5.0.0.0"
    assert rap["vc_version_status"] == "oprovad"


def test_vc_4_9_ar_oprovad():
    app = FalskApp("4.9.1.2")
    rap = formaga.formaga({"app": app})
    assert rap["vc_product_version"] == "4.9.1.2"
    assert rap["vc_version_status"] == "oprovad"
