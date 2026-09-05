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
from vc_assist_svc import claudeadapter as A                # noqa: E402
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


# --- kodstaketet, som kostade ett helt reparationsvarv ------------------------
#
# MATT: forsta korningen av kor_fas9_slingan.py mot H-04 gav i varv 1
# "rad 33: [SYNTAX/F1] ovantat tecken '`'". Systemprompten sager redan "Svara
# med enbart kroppens rader"; modellen staketade anda. En prompt ar en bon.

def test_ett_staket_runt_hela_svaret_tas_bort():
    m = A.ClaudeModell(klient=MK.Inspelad(["```st\nIF A THEN\n  B := TRUE;\nEND_IF;\n```"]))
    svar = m.svara("", [Meddelande(roll="uppgift", text="x")], [])
    # Radbrytningen sist ar med FLIT, se test_avskalat_staket_... nedan.
    assert svar.text == "IF A THEN\n  B := TRUE;\nEND_IF;\n"
    assert "`" not in svar.text


def test_staket_utan_sprakrad_ocksa():
    m = A.ClaudeModell(klient=MK.Inspelad(["```\nA := 1;\n```"]))
    assert m.svara("", [Meddelande(roll="uppgift", text="x")], []).text == "A := 1;\n"


def test_flera_block_valjs_INTE_at_modellen():
    """Trasig fixtur for gransen i regeln.

    Med tva block ar det tvetydigt vilket som ar kroppen. Att valja vore att
    skriva modellens svar at den. Texten gar fram orord, och GRINDEN dommer -
    den har ratt att saga nej, det har adaptern inte.
    """
    text = "```st\nA := 1;\n```\noch alternativt\n```st\nA := 2;\n```"
    m = A.ClaudeModell(klient=MK.Inspelad([text]))
    assert m.svara("", [Meddelande(roll="uppgift", text="x")], []).text == text


def test_kod_utan_staket_ror_vi_inte():
    m = A.ClaudeModell(klient=MK.Inspelad(["IF A THEN\n  B := TRUE;\nEND_IF;"]))
    assert m.svara("", [Meddelande(roll="uppgift", text="x")], []).text == \
        "IF A THEN\n  B := TRUE;\nEND_IF;"


def test_prosa_runt_ett_staket_ror_vi_inte_heller():
    """Bara nar HELA svaret ar ett staket. Prosa runt om betyder att modellen
    sa nagot mer, och det nagot far grinden se."""
    text = "Har ar kroppen:\n```st\nA := 1;\n```"
    m = A.ClaudeModell(klient=MK.Inspelad([text]))
    assert m.svara("", [Meddelande(roll="uppgift", text="x")], []).text == text


def test_avskalat_staket_slutar_alltid_med_en_radbrytning():
    """TRASIG FIXTUR for en vaxelverkan mellan tva av nattens andringar.

    Kodstaketsborttagningen gjorde `.strip("\\n")` och lamnade en kalla utan
    radbrytning sist. M-99:s muterade svep fann sedan att `BOOL#7` UTAN
    avslutande radbrytning fick lexern att HANGA - `_kika() in "_.#"` ar sant
    for tomma strangen. Med radbrytning foll samma text ratt hela tiden.

    Felet bet alltsa bara pa exakt den form adaptern tillverkade. Lexern ar
    lagad, men formen ska inte tillverkas: en grind som hanger lamnar inget
    spar alls, och da ar tva lager battre an ett.
    """
    for svar in ("```st\nA := 1;\n```", "```\nA := 1;```", "```st\nA := BOOL#7;\n```"):
        m = A.ClaudeModell(klient=MK.Inspelad([svar]))
        text = m.svara("", [Meddelande(roll="uppgift", text="x")], []).text
        assert text.endswith("\n"), repr(text)
        assert "`" not in text


def test_en_kalla_utan_radbrytning_far_lexern_att_SVARA():
    """Andra halvan: att lexern ar lagad ar ocksa ett pastaende som ska provas.

    Kors med tidsgrans i egen process - ett hangprov i sviten ger inte rott,
    det ger ett prov som aldrig svarar.
    """
    import subprocess as _sp
    import sys as _sys
    kod = (
        "import sys; sys.path.insert(0, %r)\n"
        "from vc_assist_svc.st.validator import validera\n"
        "validera('PROGRAM P\\nVAR\\n a : BOOL;\\nEND_VAR\\n a := BOOL#7;\\nEND_PROGRAM')\n"
        "print('SVARADE')\n" % os.path.join(_ROT, "svc"))
    k = _sp.run([_sys.executable, "-c", kod], stdout=_sp.PIPE, stderr=_sp.STDOUT,
                timeout=30)
    assert b"SVARADE" in k.stdout, k.stdout[:300]


def test_adaptern_summerar_bara_kanda_kostnader():
    """En arm dar halva korningarna saknar kostnadsuppgift far inte rapportera
    summan av den andra halvan som armens kostnad."""
    class Halvkand(MK.Inspelad):
        def __init__(self, svar):
            MK.Inspelad.__init__(self, svar)
            self._n = 0

        def fraga(self, prompt):
            s = MK.Inspelad.fraga(self, prompt)
            self._n += 1
            s.kostnad_usd = 0.05 if self._n == 1 else None
            return s

    m = A.ClaudeModell(klient=Halvkand(["a", "b"]))
    for _ in range(2):
        m.svara("", [Meddelande(roll="uppgift", text="x")], [])
    assert m.kostnad_usd == 0.05
    assert m.anrop == 2


def test_en_adapter_utan_enda_kostnadsuppgift_sager_okand():
    m = A.ClaudeModell(klient=MK.Inspelad(["a"]))
    m.svara("", [Meddelande(roll="uppgift", text="x")], [])
    assert m.kostnad_usd is None, "noll anrop med uppgift ska ge okand, inte 0"
