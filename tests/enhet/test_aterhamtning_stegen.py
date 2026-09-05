# -*- coding: utf-8 -*-
"""L1: stegen som hittar orsaken, och raderna de letar efter.

Regel L-8 i `28_lagen_och_aterhamtning.md`: panelen kör stegen själv när läget
blir nere. *Operatören ska inte behöva öppna en loggfil för att få veta varför.*

Två saker gör den här stegen till en grind i stället för en checklista, och
båda har sin egen trasig fixtur här:

**Raderna finns i koden.** `test_varje_markor_skrivs_av_tillagget` läser
`ext/vc_addon/vc_assist/` som text. En stege som letar efter rader ingen skriver
mäter sin egen fantasi, och den skulle stå grön för alltid — samma felklass
`test_forlopp_kallor.py` skyddar mot när den läser `korning.py` som text.

**En obestämd fråga stoppar stegen.** Går loggen inte att läsa är svaret varken
ja eller nej. En stege som hoppar över den frågan pekar ut ett senare steg med
full säkerhet, och en orsak som pekas ut fel skickar operatören åt fel håll med
samma tonfall som en riktig.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.aterhamtning import lagen as L         # noqa: E402
from vc_assist_svc.aterhamtning import stegen as S        # noqa: E402

_TILLAGG = os.path.join(_ROT, "ext", "vc_addon", "vc_assist")

GRON_BOOT = ("OnAppInitialized\nloadCommand uri=vcAssistBridge\n"
             "bridge_cmd executed\n"
             "brygg-komponenten byggd, skriptet kompilerar\n")
GRON_BRYGG = ("startar pa 127.0.0.1:8901\nlyssnar pa 127.0.0.1:8901\n"
              "pumpen igang\n")


def _kallor(boot=GRON_BOOT, brygg=GRON_BRYGG):
    return {S.BOOTLOGG: boot, S.BRYGGLOGG: brygg}


def test_varje_markor_skrivs_av_tillagget():
    """Stegen letar bara efter rader tillägget faktiskt skriver.

    Faller det här provet har en lograd bytt namn, och stegen har tyst slutat
    hitta sin fråga — den skulle svara "nej" på ett steg som gick bra och peka
    ut fel orsak med full säkerhet.
    """
    kalla = ""
    for namn in sorted(os.listdir(_TILLAGG)):
        if namn.endswith(".py"):
            with open(os.path.join(_TILLAGG, namn), encoding="utf-8") as fh:
                kalla += fh.read()
    saknade = []
    for steg in S.STEGEN:
        for markor in steg.ja:
            if markor not in kalla:
                saknade.append("steg %d: %r" % (steg.nr, markor))
    for markor, _orsak in S.DOG_AV:
        if markor not in kalla:
            saknade.append("dödsmarkören %r" % markor)
    assert not saknade, ("stegen letar efter rader ingen skriver: %s"
                         % ", ".join(saknade))


def test_en_gron_start_ger_sju_ja_och_ingen_orsak():
    svaren = S.kor_stegen(_kallor())
    assert S.sammanfatta(svaren) == {"ja": 7, "nej": 0, "vet inte": 0}
    orsak, steget = S.orsak_ur_stegen(svaren)
    assert orsak is L.OKAND and steget is None


@pytest.mark.parametrize("boot,brygg,vantad,nr", [
    ("", GRON_BRYGG, "kroken_fyrade_inte", 1),
    ("OnAppInitialized\n", GRON_BRYGG, "modulen_kordes_aldrig", 2),
    ("OnAppInitialized\nloadCommand uri=x\nbridge_cmd executed\n",
     GRON_BRYGG, "skriptet_kompilerar_inte", 3),
    (GRON_BOOT, "startar pa 127.0.0.1:8901\n", "port_upptagen", 4),
    (GRON_BOOT, "startar pa 127.0.0.1:8901\nlyssnar pa 127.0.0.1:8901\n",
     "operatoren_stoppade", 5),
    (GRON_BOOT, GRON_BRYGG + "simuleringen stoppad\n", "operatoren_stoppade",
     6),
    (GRON_BOOT, GRON_BRYGG + "  varning: q1 dodar pumpen (save)\n",
     "sparad_layout", 6),
    (GRON_BOOT, GRON_BRYGG + "kord q1 -> failed\ncreateBehaviour VC_SCRIPT\n",
     "skriptbeteende", 7),
])
def test_stegen_pekar_ut_ratt_orsak(boot, brygg, vantad, nr):
    svaren = S.kor_stegen(_kallor(boot, brygg))
    orsak, steget = S.orsak_ur_stegen(svaren)
    assert orsak.nyckel == vantad
    assert steget is not None and steget.steg.nr == nr


def test_raden_executed_ensam_racker_inte():
    """M-09, mätt: `loadCommand` gav ett objekt, `execute()` kastade inte, och
    modulkroppen kördes ändå aldrig. Steget kräver därför nästa rad också."""
    svaren = S.kor_stegen(_kallor(
        boot="OnAppInitialized\nloadCommand uri=x\nbridge_cmd executed\n"))
    assert svaren[1].svar is True      # raden finns
    assert svaren[2].svar is False     # och nästa avgör
    assert S.orsak_ur_stegen(svaren)[0].nyckel == "skriptet_kompilerar_inte"


def test_en_olasbar_logg_stoppar_stegen_och_ger_ingen_orsak():
    svaren = S.kor_stegen({S.BOOTLOGG: None, S.BRYGGLOGG: GRON_BRYGG})
    assert [s.svar for s in svaren] == [None] * 7
    assert "gick inte att läsa" in svaren[0].ordagrant
    assert "steg 1 var obestämt" in svaren[1].ordagrant
    orsak, steget = S.orsak_ur_stegen(svaren)
    assert orsak is L.OKAND
    assert steget is svaren[0]


def test_en_olasbar_brygglogg_stoppar_vid_steg_fyra():
    svaren = S.kor_stegen({S.BOOTLOGG: GRON_BOOT, S.BRYGGLOGG: None})
    assert S.sammanfatta(svaren) == {"ja": 3, "nej": 0, "vet inte": 4}
    assert S.orsak_ur_stegen(svaren)[1].steg.nr == 4


def _tom_strang_som_svar(kallor):
    """TRASIG FIXTUR: en olasbar logg blir en TOM STRÄNG i stället för `None`.

    Det är buggen i sin vanligaste form — `except OSError: text = ""` — och
    den ser ut som robusthet. Följden är att varje fråga besvaras med *nej*
    på ett underlag som inte finns, och stegen pekar ut den första orsaken i
    listan med full säkerhet.
    """
    return dict((namn, "" if text is None else text)
                for namn, text in kallor.items())


def test_en_olasbar_logg_som_blir_tom_strang_pekar_ut_fel_orsak_med_sakerhet():
    """Kontrasten är hela provet.

    Bootloggen går inte att läsa. Den ärliga stegen säger *vet inte* på alla
    sju och lämnar orsaken okänd. Den trasiga säger *"Tillägget startade
    aldrig"* — en orsak, en väg tillbaka, och ett tonfall som om saken var
    utredd. Operatören skickas att installera om ett tillägg som kan ha varit
    helt i sin ordning.
    """
    kallor = {S.BOOTLOGG: None, S.BRYGGLOGG: GRON_BRYGG}
    arlig, arligt_steg = S.orsak_ur_stegen(S.kor_stegen(kallor))
    assert arlig is L.OKAND
    assert arligt_steg is not None and arligt_steg.svar is None

    trasig, trasigt_steg = S.orsak_ur_stegen(
        S.kor_stegen(_tom_strang_som_svar(kallor)))
    assert trasig.nyckel == "kroken_fyrade_inte"
    assert trasigt_steg.svar is False
    assert trasig is not arlig, ("den trasiga stegen gav samma svar som den "
                                 "ärliga; då mäter provet ingenting")


def test_stegen_lamnar_aldrig_ut_ett_steg():
    """En stege som visar färre frågor ser säkrare ut än den är."""
    for kallor in (_kallor(), {S.BOOTLOGG: None, S.BRYGGLOGG: None},
                   _kallor(boot="")):
        assert len(S.kor_stegen(kallor)) == len(S.STEGEN) == 7


def test_tre_tal_alltid_aldrig_tva():
    tal = S.sammanfatta(S.kor_stegen({S.BOOTLOGG: None, S.BRYGGLOGG: None}))
    assert set(tal) == {"ja", "nej", "vet inte"}
    assert sum(tal.values()) == 7
