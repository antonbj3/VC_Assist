# -*- coding: utf-8 -*-
"""D6: Verifiering av kompositionsdomarna över fyra nya linjetopologier.

Topologier:
1. SERIELL_3: Tre stationer i serie (A -> B -> C)
2. BUFFERT: Två stationer med mellanliggande buffert (A -> BUF -> B)
3. PARALLELL: Parallella grenar med merge (IN -> G1 // G2 -> UT)
4. ATERFLODE: Sluten slinga med omarbete (A -> B -> RETUR -> A)

Provet säkerställer:
- 4 av 4 HEL ger PASS.
- 8 av 8 kompositionsfel fälls av kompositionsdomarna (sekvens eller genomflöde).
- Lokal specifikation räcker inte för global hälsa: komponenter som isolerat
  följer sitt lokala arbetsschema orsakar krock eller dödläge i kompositionen.
"""
import os
import sys
import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in [os.path.join(_ROT, "tests", "protocol"),
          os.path.join(_ROT, "ext", "vc_addon", "vc_assist"),
          os.path.join(_ROT, "svc")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import kor_D6_linjetopologier as D6
import oga_analys as A


def test_d6_alla_fyra_topologier_hel_och_fel():
    """Alla 4 topologier ska ge PASS vid HEL och fällas på 8 kompositionsfel."""
    res = D6.kor_alla()
    assert len(res) == 4

    for top_namn, fall_dict in res.items():
        # HEL ska passera
        assert fall_dict["HEL"]["dom"] == "PASS", f"{top_namn} HEL gav inte PASS"
        assert len(fall_dict["HEL"]["fallande"]) == 0

        # Fel ska fällas
        fel_fall = [f for f in fall_dict if f != "HEL"]
        assert len(fel_fall) >= 2, f"{top_namn} saknar minst 2 felfall"
        for f in fel_fall:
            assert fall_dict[f]["dom"] == "FAIL", f"{top_namn} {f} fälldes inte"
            assert len(fall_dict[f]["fallande"]) >= 1, f"{top_namn} {f} saknar fallande domare"


def test_d6_fallande_domare_typer():
    """Verifiera att kompositionsfelen fälls av rätt domare."""
    res = D6.kor_alla()

    # Kaskadsvält och buffertblockering/svält fälls av genomflöde
    assert "genomflode" in res["SERIELL_3"]["K_SER_1"]["fallande"]
    assert "genomflode" in res["BUFFERT"]["K_BUF_1"]["fallande"]
    assert "genomflode" in res["BUFFERT"]["K_BUF_2"]["fallande"]
    assert "genomflode" in res["PARALLELL"]["K_PAR_2"]["fallande"]
    assert "genomflode" in res["ATERFLODE"]["K_REC_2"]["fallande"]

    # Sammanflödeskrock och delade resurskonflikter fälls av sekvens (förregling)
    assert "sekvens" in res["SERIELL_3"]["K_SER_2"]["fallande"]
    assert "sekvens" in res["PARALLELL"]["K_PAR_1"]["fallande"]
    assert "sekvens" in res["ATERFLODE"]["K_REC_1"]["fallande"]


def test_lokal_spec_racker_inte_for_global_halsa():
    """Visa varför lokal komponenthälsa inte garanterar systemhälsa.

    I K_PAR_1 arbetar gren 2 helt enligt sin lokala specifikation:
    stationen bearbetar detaljer, svälter inte och blockeras inte.
    Lokalt döms gren 2 till PASS.
    Men i kompositionen släpper gren 1 och gren 2 samtidigt mot en delad
    sammanflödespunkt utan ömsesidig uteslutning. Den globala planen
    med förreglingskrav fäller kompositionen med FAIL (sekvensdomaren).
    """
    data, plan_global = D6.topologi_parallell("K_PAR_1")

    # Isolerad plan för gren 2: känner bara till sin lokala station
    plan_lokal_g2 = {
        "template": "g2_lokal",
        "parts": ["broms"],
        "tools": [],
        "rate_hz": plan_global["rate_hz"],
        "stat": ["stat_g2"],
        "genomstromning": {"max_svalt_s": 2.5},
    }
    _, rap_g2, _ = A.doma(data, plan_lokal_g2)
    # Lokalt är gren 2 helt frisk!
    assert rap_g2.dom[0] == "PASS", "Lokal kontroll av gren 2 ska ge PASS (ingen lokal brist)"

    # Global plan med kompositionskrav över båda grenarna
    _, rap_global, an_global = A.doma(data, plan_global)
    assert rap_global.dom[0] == "FAIL", "Global komposition ska fälla sammanflödeskollisionen"
    assert an_global.harledt["domar"]["sekvens"]["utfall"] == "FAIL"
