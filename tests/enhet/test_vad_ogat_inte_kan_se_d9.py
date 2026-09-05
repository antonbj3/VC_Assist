# -*- coding: utf-8 -*-
"""D9: Enhetsprov för vad ögat inte kan se av konstruktion (M-138).

Uppdrag D9 i docs/uppdrag/KO_D_ogat_och_scenen.md:
"Gör listan färdig: vilka av felklasserna i docs/spec/82_felklasser.md går
principiellt inte att se i ett spår, hur mycket man än förbättrar domarna?
Den listan är produktens ärliga gräns och hör hemma i README."
"""
from __future__ import annotations

import os
import re
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_README = os.path.join(_ROT, "README.md")
_FELKLASSER_MD = os.path.join(_ROT, "docs", "spec", "82_felklasser.md")

# Klasser som principiellt / strukturellt inte går att se i ett exekveringsspår:
# - F1..F4: Statiska fel (syntax, symboler, taggar, deklarationer). Kräver kompilator/AST.
# - F13: Agent- och orkestreringsfel. Kräver samtalslogg.
# - F15: Flank- och latchsemantik (nivå vs flank / internt minnestillstånd).
STRUKTURELLT_OSYNLIGA_I_SPAR = {"F1", "F2", "F3", "F4", "F13", "F15"}

# Klasser som är synliga i ett spår under körning:
SYNLIGA_I_SPAR = {"F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"}


def _las_felklasser() -> dict[str, str]:
    """Läser alla koder ur 82_felklasser.md."""
    klasser = {}
    with open(_FELKLASSER_MD, "r", encoding="utf-8") as f:
        for rad in f:
            m = re.match(r"^\|\s*`(F\d+)`\s*\|\s*([^|]+)\s*\|", rad)
            if m:
                klasser[m.group(1)] = m.group(2).strip()
    return klasser


def test_alla_felklasser_ar_kategoriserade():
    """Varje felklass i 82_felklasser.md ska ha en fastställd synlighet."""
    klasser = _las_felklasser()
    assert len(klasser) >= 14

    for kod in klasser:
        if kod == "F14":  # Annat (slasktratt)
            continue
        assert kod in STRUKTURELLT_OSYNLIGA_I_SPAR or kod in SYNLIGA_I_SPAR, (
            f"Felklass {kod} ({klasser[kod]}) saknar synlighetskategorisering!"
        )


def test_readme_innehaller_arliga_gransen_och_felklasserna():
    """README ska lista vad ögat inte kan se av konstruktion (M-138)."""
    with open(_README, "r", encoding="utf-8") as f:
        text = f.read()

    assert "Vad ögat inte kan se, av konstruktion" in text
    assert "M-138" in text

    # Kontrollera att de strukturellt osynliga klasserna nämns
    for f in ["F1", "F2", "F3", "F4", "F8", "F13", "F15"]:
        assert f in text, f"README saknar omnämnande av osynliga felklassen {f}"
