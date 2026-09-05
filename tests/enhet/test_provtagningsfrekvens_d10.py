# -*- coding: utf-8 -*-
"""D10: Enhetsprov för provtagningsfrekvens och domarnas giltighet (M-140).

Uppdrag D10 i docs/uppdrag/KO_D_ogat_och_scenen.md:
"Ögat provtar 17,2 Hz tyst och 224,7 Hz under trafik. En rörelse som är klar
på 30 ms syns inte vid 17 Hz. Räkna, per domare, vilken snabbaste händelse den
kan se — och jämför mot vad bankens uppgifter faktiskt kräver. Om någon uppgift
kräver mer än ögat ger, är den uppgiftens dom ogiltig."
"""
from __future__ import annotations

import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in [_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "tests"),
          os.path.join(_ROT, "tests", "protocol"),
          os.path.join(_ROT, "ext", "vc_addon", "vc_assist")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import kor_D10_provtagningsfrekvens as D10


def test_d10_domarnas_upplosningsgranser():
    """Verifiera beräknade upplösningsgränser per domare."""
    granser = D10.berakna_domargranser()
    assert len(granser) == 5

    # Sekvens, kollision och genomflöde begränsas av provintervallet dt
    assert granser["sekvens"]["tyst_ms"] == pytest.approx(58.1, abs=0.1)
    assert granser["sekvens"]["trafik_ms"] == pytest.approx(4.45, abs=0.05)

    # Timing kräver fönster > 2*dt för att inte hamna i osäkerhet (INCONCLUSIVE)
    assert granser["timing"]["tyst_ms"] == pytest.approx(116.3, abs=0.1)
    assert granser["timing"]["trafik_ms"] == pytest.approx(8.90, abs=0.1)

    # Grepp har ett fast golv CARRY_MIN_SPAN_S = 500 ms
    assert granser["grepp"]["tyst_ms"] == 500.0


def test_d10_ogiltiga_domar_vid_tyst_regim():
    """Minst 10 uppgifter i banken kräver snabbare provtagning än 17.2 Hz."""
    bank = D10.analysera_bankens_tidskrav()
    ogiltiga = bank["ogiltiga_vid_tyst"]

    assert len(ogiltiga) >= 10, f"Fann bara {len(ogiltiga)} uppgifter med dt < 58.1 ms"
    ogiltiga_namn = [u["namn"] for u in ogiltiga]
    assert "A-02.json" in ogiltiga_namn
    assert "T-01.json" in ogiltiga_namn
    assert "L-01.json" in ogiltiga_namn


def test_d10_trafikregim_heltackande():
    """Vid 224.7 Hz (4.45 ms) täcks 100 % av bankens uppgifter."""
    bank = D10.analysera_bankens_tidskrav()
    assert len(bank["ogiltiga_vid_trafik"]) == 0, (
        f"Fann uppgifter som överskrider även 224.7 Hz: {bank['ogiltiga_vid_trafik']}"
    )
