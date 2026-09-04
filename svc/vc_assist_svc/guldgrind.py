# -*- coding: utf-8 -*-
"""Guldgrinden: laser ogats dom, raknar aldrig om ett matt.

Doktrinen kommer ur en matt incident i kallprojektet: en omimplementerad
positionsdom underkande 2 av 4 medan ogat visade 4 av 4. Grinden parsar darfor
ogats EGEN utdata och implementerar aldrig om storheten.

Fail-closed genomgaende. Okand klass, oparsbar rapport, saknad cell och tystnad
ar alla NOT GOLD. Ett godkannande maste vara uttalat.

Kalla: docs/spec/50_grindar.md
"""
from __future__ import annotations

import os
import sys

_EXT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "ext", "vc_addon", "vc_assist"))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import oga_kontrakt as K  # noqa: E402

# Guldstegen, arvd ur kallans dataset_manifest.py.
L1 = "gold_verified_core"
L2 = "gold_line_verified"
KANDIDAT = "candidate"
INTE_GULD = "NOT GOLD"

# Kategoriska ord i ogats egna rader som betyder att nagot gick fel. De ar
# ORD, inte matt - grinden laser dem, den raknar inte om dem.
DALIGA_ORD = (
    "NEVER_FORMED", "SLIPPING", "OFF_TARGET", "DROPPED",
    "VIOLATION", "SHORT",
)

# Grindarna 1-4 i kedjan. Ogat ar grind 5 och domer sig sjalvt.
FORGRINDAR = ("kompilering", "statisk_analys", "deklarationsmatchning",
              "anropsvalidering")


class Beslut(object):
    def __init__(self, niva, skal, per_cell=None):
        self.niva = niva
        self.skal = skal
        self.per_cell = per_cell or {}

    @property
    def guld(self):
        return self.niva in (L1, L2)

    def __repr__(self):
        return "Beslut(%s, %r)" % (self.niva, self.skal)

    def text(self):
        if self.guld:
            return "GOLD %s (%s)" % (self.niva, self.skal)
        return "%s (%s)" % (INTE_GULD, self.skal)


class Guldgrind(object):
    def __init__(self, kanda_klasser):
        """kanda_klasser: de scenarioklasser grinden vet hur den ska tolka.

        En okand klass ar inte ett godkannande i vantan pa besked. Den ar ett
        underkannande. Arvt ur eyes_gold_gate.
        """
        self.kanda_klasser = set(kanda_klasser)

    # -- en cell --

    def doma_cell(self, cell):
        """Returnerar (ok, skal). Rör aldrig ett matt, bara ogats egna ord."""
        namn = cell.get("namn", "?")
        klass = cell.get("klass")
        if klass not in self.kanda_klasser:
            return False, "okand scenarioklass %r i %s" % (klass, namn)

        for grind in FORGRINDAR:
            utfall = (cell.get("forgrindar") or {}).get(grind)
            if utfall is None:
                return False, "%s: grinden %s ar inte kord" % (namn, grind)
            if utfall is not True:
                return False, "%s: %s underkande (%s)" % (namn, grind, utfall)

        text = cell.get("eyes")
        if not text:
            return False, "%s: ingen ogonrapport" % namn
        try:
            rapport = K.las(text)
        except K.Kontraktsfel as e:
            return False, "%s: %s" % (namn, e.grinddom)

        if not rapport.godkand():
            varde = rapport.dom[0] if rapport.dom else "?"
            return False, "%s: ogat sa %s (%s)" % (
                namn, varde, rapport.dom[1] if rapport.dom else "utan skal")

        # Ogats dom ar auktoritativ, men en rapport far inte motsaga SIG SJALV.
        # Att lasa ett kategoriskt ord ur ogats egen rad ar inte att rakna om
        # ett matt - grinden mater ingenting, den upptacker en sjalvmotsagelse.
        for _sektion, rader in rapport.sektioner:
            for rad in rader:
                for ord_ in DALIGA_ORD:
                    if ord_ in rad:
                        return False, ("%s: rapporten sager PASS men bar raden "
                                       "%r" % (namn, rad))
                if rad.startswith("COLLISION ") and rad != "COLLISION none":
                    return False, "%s: rapporten sager PASS men bar %r" % (namn, rad)
        return True, "ogat sa PASS"

    # -- en samling --

    def doma(self, celler, linje=None):
        """celler: en lista cellrapporter. linje: valfri rapport for hela linan.

        Guld bara nar VARJE cell passerar. En tom lista ar inte guld - det ar
        ingenting att doma.
        """
        if not celler:
            return Beslut(INTE_GULD, "inga celler att doma")

        per_cell = {}
        fallda = []
        for cell in celler:
            ok, skal = self.doma_cell(cell)
            per_cell[cell.get("namn", "?")] = (ok, skal)
            if not ok:
                fallda.append(skal)
        if fallda:
            return Beslut(INTE_GULD, "; ".join(fallda[:3]), per_cell)

        if linje is None:
            return Beslut(L1, "%d av %d celler gav PASS" % (len(celler), len(celler)),
                          per_cell)

        ok, skal = self.doma_cell(linje)
        per_cell[linje.get("namn", "linjen")] = (ok, skal)
        if not ok:
            return Beslut(INTE_GULD, "varje station gav PASS men linan foll: %s" % skal,
                          per_cell)
        return Beslut(L2, "%d stationer och linan gav PASS" % len(celler), per_cell)
