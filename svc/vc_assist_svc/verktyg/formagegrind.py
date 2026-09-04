# -*- coding: utf-8 -*-
"""Formagegrinden: vilka verktyg far modellen ens se.

36_versioner.md: "Koden fragar VAD SOM FINNS, inte VILKEN VERSION det ar."
Rapporten som bryggan skriver vid start (ext/vc_addon/vc_assist/formaga.py)
ar facit. Ett verktyg vars kravda yta saknas slas AV har, med ett skal som
namner ytan - i stallet for att falla med AttributeError inne i VC nagon
minut senare, dar felet ser ut som ett kodfel i stallet for ett versionsfel.

Tre svarsformer, aldrig fler (36_versioner.md):
  finns is True  -> pa
  finns is False -> av, "saknas"
  finns is None  -> av, "oprovad". Okant behandlas som saknat. Aldrig gissa.
"""
from __future__ import annotations

import os
import sys

from .fel import Avstangt

# formaga.py kors inne i VC:s Python 2.7 och far inte importera nagot ur
# tjansten. Darfor ligger den under ext/ och nas genom sokvagen, precis som
# klient.py nar protokoll.py. Samma fil, en enda sanning om ytnamnen.
_HAR = os.path.dirname(os.path.abspath(__file__))
_EXT = os.path.normpath(os.path.join(_HAR, "..", "..", "..", "ext", "vc_addon", "vc_assist"))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import formaga  # noqa: E402

KANDA_YTOR = tuple(yta for yta, _objekt, _attribut in formaga.YTOR)

# Skalen ar text som gar tillbaka till modellen och till operatoren. De ska
# ga att lasa utan att kanna till specen.
SKAL_INGEN_RAPPORT = (
    "ingen formagerapport last fran bryggan; okant behandlas som saknat "
    "(36_versioner.md)")


class Urval(object):
    """Vilka verktyg som ar pa, och varfor de andra ar av."""

    def __init__(self, domar, rapport=None):
        # namn -> None (pa) eller skal (av)
        self._domar = dict(domar)
        self.rapport = rapport

    def __len__(self):
        return len(self._domar)

    def pa(self, namn):
        return namn in self._domar and self._domar[namn] is None

    def skal(self, namn):
        """None om verktyget ar pa, annars skalet det ar av."""
        if namn not in self._domar:
            return "verktyget finns inte i registret"
        return self._domar[namn]

    def krav(self, namn):
        """Kastar Avstangt om verktyget inte far anvandas. Annars tyst."""
        skal = self.skal(namn)
        if skal is not None:
            raise Avstangt(namn, skal)

    def pa_namn(self):
        return tuple(sorted(n for n in self._domar if self._domar[n] is None))

    def av_namn(self):
        return {n: s for n, s in self._domar.items() if s is not None}

    def openai_verktyg(self, register):
        """Det som faktiskt exponeras for modellen. Avstangda syns aldrig."""
        return [register[n].som_openai() for n in self.pa_namn()]


def _yta_finns(rapport, yta):
    """(finns, skal). Skalet ar None nar ytan finns."""
    ytor = rapport.get("ytor") or {}
    if yta not in ytor:
        return False, ("ytan %s star inte i formagerapporten; okant "
                       "behandlas som saknat" % yta)
    finns = (ytor[yta] or {}).get("finns")
    if finns is True:
        return True, None
    if finns is False:
        return False, "ytan %s finns inte i denna VC" % yta
    return False, ("ytan %s ar oprovad (%s) och raknas som saknad"
                   % (yta, (ytor[yta] or {}).get("varfor", "utan angivet skal")))


def urval_ur_rapport(rapport, register):
    """Bygger urvalet ur bryggans formagerapport.

    rapport=None betyder att bryggan inte svarat. Da ar ALLT av: att gissa
    att ytorna finns ar precis den tysta nedgraderingen 36_versioner.md
    forbjuder.
    """
    domar = {}
    if rapport is None:
        for namn in register:
            domar[namn] = SKAL_INGEN_RAPPORT
        return Urval(domar, None)

    for namn, verktyg in register.items():
        saknade = []
        for yta in verktyg.kraver:
            finns, skal = _yta_finns(rapport, yta)
            if not finns:
                saknade.append(skal)
        domar[namn] = "; ".join(saknade) if saknade else None
    return Urval(domar, rapport)


def urval_allt_pa(register):
    """Alla verktyg pa. Endast for L1-prov av routing och kodgenerering.

    Konsument: tests/enhet/test_verktyg.py. Den far ALDRIG anvandas i drift -
    dar ar bryggans rapport enda kallan, och den vagen gar genom
    urval_ur_rapport.
    """
    return Urval({namn: None for namn in register}, None)
