# -*- coding: utf-8 -*-
"""L1 for adaptern som satter en riktig modell bakom `Modell`-ytan.

Inga modellanrop. Klienten ar `Inspelad`, sa proven mater ADAPTERN.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import modellklient as MK                        # noqa: E402
from vc_assist_svc.harness import claudeadapter as A                # noqa: E402
from vc_assist_svc.harness.modell import Meddelande                 # noqa: E402


def test_ett_textsvar_gar_hela_vagen_igenom():
    m = A.ClaudeModell(klient=MK.Inspelad(["PROGRAM P\nEND_PROGRAM"]))
    svar = m.svara("du skriver ST", [Meddelande(roll="uppgift", text="skriv P")], [])
    assert svar.text.startswith("PROGRAM P")
    assert svar.ar_slutsvar
    assert svar.leverantor == "anthropic/claude-cli"


def test_verktyg_kastar_i_stallet_for_att_se_ut_som_en_modell_utan_initiativ():
    """Trasig fixtur for adapterns egen grans.

    Klienten kor med tom verktygslista sa modellen inte ska kunna lasa facit.
    En harness som skickar verktyg och far ren text tillbaka hade matt det som
    att MODELLEN lat bli att anvanda dem - en falsk matning om modellen,
    orsakad av adaptern.
    """
    m = A.ClaudeModell(klient=MK.Inspelad(["text"]))
    with pytest.raises(A.Adapterfel) as e:
        m.svara("sp", [Meddelande(roll="uppgift", text="x")], [object()])
    assert "MODELLEN" in str(e.value)


def test_systemprompt_och_historik_nar_hela_vagen_ut():
    """Ett prov mot att promptbygget tappar ett led tyst.

    Tappas systemprompten svarar modellen pa fel fraga, och utfallet skulle
    bokforas som modellens fel.
    """
    k = MK.Inspelad(["ok"])
    A.ClaudeModell(klient=k).svara(
        "SYSTEM-RAD",
        [Meddelande(roll="uppgift", text="FORSTA"),
         Meddelande(roll="modell", text="ANDRA"),
         Meddelande(roll="uppgift", text="TREDJE")], [])
    fraga = k.stalda[0]
    for bit in ("SYSTEM-RAD", "FORSTA", "ANDRA", "TREDJE"):
        assert bit in fraga, "%s tappades pa vagen" % bit
    assert fraga.index("FORSTA") < fraga.index("ANDRA") < fraga.index("TREDJE")


def test_rollerna_star_utskrivna_inte_hopslagna():
    """En modell som inte ser var GRINDENS ord slutar och uppgiftens
    borjar svarar pa fel sak. Rollerna ar repots egna - uppgift,
    modell, verktyg, grind - och de valideras av Meddelande."""
    k = MK.Inspelad(["ok"])
    A.ClaudeModell(klient=k).svara(
        "", [Meddelande(roll="uppgift", text="A"),
             Meddelande(roll="modell", text="B")], [])
    assert "[UPPGIFT]" in k.stalda[0] and "[MODELL]" in k.stalda[0]


def test_tomma_meddelanden_hoppas_over_utan_att_lamna_en_naken_rollrad():
    k = MK.Inspelad(["ok"])
    A.ClaudeModell(klient=k).svara(
        "sp", [Meddelande(roll="uppgift", text="   "),
               Meddelande(roll="uppgift", text="riktig")], [])
    assert k.stalda[0].count("[UPPGIFT]") == 1


def test_kostnaden_summeras_over_turen():
    """Ett tak pa fyra varv ar ett pastaende om ingen kan saga vad det kostade."""
    class Kostsam(MK.Inspelad):
        def fraga(self, prompt):
            s = MK.Inspelad.fraga(self, prompt)
            s.kostnad_usd = 0.05
            return s

    m = A.ClaudeModell(klient=Kostsam(["a", "b", "c"]))
    for _ in range(3):
        m.svara("", [Meddelande(roll="uppgift", text="x")], [])
    assert m.anrop == 3
    assert abs(m.kostnad_usd - 0.15) < 1e-9


def test_ett_tomt_modellsvar_kastar_i_klienten_och_blir_aldrig_tystnad():
    """Harnessen dommer tystnad som modellens fel. Ett tomt svar fran
    TRANSPORTEN far darfor aldrig na dit."""
    with pytest.raises(MK.Modellfel):
        A.ClaudeModell(klient=MK.Inspelad(["   "])).svara(
            "", [Meddelande(roll="uppgift", text="x")], [])
