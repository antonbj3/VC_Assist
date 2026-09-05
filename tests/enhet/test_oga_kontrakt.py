# -*- coding: utf-8 -*-
"""L0: ogats domskontrakt. Kalla: 41_ogat_kontrakt.md, de fem parsningsreglerna."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "ext", "vc_addon", "vc_assist"))
import oga_kontrakt as K  # noqa: E402


def _rapport(dom="PASS", orsak="allt inom marginal"):
    r = K.Rapport("plocka_och_placera", "2026-09-04T17:00:00", 12.5, 250, 20.0)
    r.sektion("MOTION")
    r.rad("GRIP FORMED t=2.500s dist=3.2mm")
    r.rad("CARRY RIGID rot=0.4deg span=6.100s")
    r.rad("PLACE IN_TARGET err=1.8mm z=0.750m")
    r.sektion("TIMING")
    r.rad("EDGE grip_out RISE t=2.480s")
    r.rad("LATENCY grip_out -> tool 20.0ms")
    r.rad("DWELL station1 4.200s req=4.000s OK")
    r.rad("RACE none")
    r.sektion("THROUGHPUT")
    r.rad("STATION station1 in=10 out=10 avg=4.200s min=4.100s max=4.400s")
    r.sektion("SAFETY")
    r.rad("MINDIST tool+fixture 12.4mm t=3.100s")
    r.rad("COLLISION none")
    r.sektion("HONESTY")
    r.rad("TELEPORT_TRANSFER OK")
    r.rad("BLOWUP OK")
    r.rad("UNDERGROUND OK")
    r.rad("NEVER_GRIPPED OK")
    return r.satt_dom(dom, orsak)


def test_skrivare_och_lasare_ar_varandras_invers():
    a = _rapport()
    b = K.las(a.text())
    assert b.text() == a.text()
    assert b.template == "plocka_och_placera" and b.samples == 250
    assert b.godkand() is True


# ---- regel 1: versionen -------------------------------------------------

def test_okand_version_ger_egen_grinddom():
    t = _rapport().text().replace("EYES v2", "EYES v7", 1)
    with pytest.raises(K.OkandVersion) as ei:
        K.las(t)
    assert ei.value.grinddom == "NOT GOLD (unknown eyes version)"


def test_saknad_versionsrad_gissas_aldrig():
    t = "\n".join(_rapport().text().splitlines()[1:])
    with pytest.raises(K.OkandVersion):
        K.las(t)


# ---- regel 2: avhuggen utdata -------------------------------------------

def test_avhuggen_rapport_ar_aldrig_ett_godkannande():
    rader = _rapport().text().splitlines()
    with pytest.raises(K.Avhuggen) as ei:
        K.las("\n".join(rader[:-1]))
    assert ei.value.grinddom == "NOT GOLD (truncated eyes output)"


def test_tom_utdata_ar_avhuggen():
    with pytest.raises(K.Avhuggen):
        K.las("")


# ---- regel 3: okand sektion mot okand rad -------------------------------

def test_okand_sektion_ignoreras_sa_en_aldre_grind_kan_lasa_en_nyare_rapport():
    rader = _rapport().text().splitlines()
    rader.insert(-1, "SECTION ENERGY")
    rader.insert(-1, "  WATTS peak=42.0W")
    r = K.las("\n".join(rader))
    assert r.okanda_sektioner == ["ENERGY"]
    assert r.godkand() is True


def test_okand_rad_i_KAND_sektion_ar_ett_fel():
    """En rapport som kraschar domaren kan dolja rott. Darfor ar den strikt."""
    rader = _rapport().text().splitlines()
    i = rader.index("SECTION SAFETY")
    rader.insert(i + 1, "  SPARKS many")
    with pytest.raises(K.Kontraktsfel):
        K.las("\n".join(rader))


def test_ratt_nyckelord_men_fel_form_fastnar():
    rader = _rapport().text().splitlines()
    i = rader.index("SECTION MOTION")
    rader[i + 1] = "  GRIP MAYBE t=2.5s dist=3.2mm"
    with pytest.raises(K.Kontraktsfel):
        K.las("\n".join(rader))


def test_saknad_enhet_fastnar():
    rader = _rapport().text().splitlines()
    i = rader.index("SECTION SAFETY")
    rader[i + 1] = "  MINDIST tool+fixture 12.4 t=3.100s"
    with pytest.raises(K.Kontraktsfel):
        K.las("\n".join(rader))


def test_komma_som_decimaltecken_fastnar():
    rader = _rapport().text().splitlines()
    i = rader.index("SECTION SAFETY")
    rader[i + 1] = "  MINDIST tool+fixture 12,4mm t=3.100s"
    with pytest.raises(K.Kontraktsfel):
        K.las("\n".join(rader))


# ---- regel 4: INCONCLUSIVE ar inte godkant ------------------------------

def test_inconclusive_ar_inte_godkant():
    r = K.las(_rapport("INCONCLUSIVE", "for fa prov for att doma").text())
    assert r.dom[0] == "INCONCLUSIVE"
    assert r.godkand() is False


def test_fail_ar_inte_godkant():
    assert K.las(_rapport("FAIL", "detaljen tappades").text()).godkand() is False


# ---- regel 5: en overtradelse tvingar FAIL ------------------------------

def test_skrivaren_vagrar_satta_PASS_nar_en_overtradelse_finns():
    r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
    r.sektion("HONESTY")
    r.rad("TELEPORT_TRANSFER VIOLATION dist=812.0mm t=2.400s")
    with pytest.raises(K.Kontraktsfel) as ei:
        r.satt_dom("PASS", "ser bra ut")
    assert "TELEPORT_TRANSFER" in str(ei.value)


def test_lasaren_domer_inte_om_ett_motsagelsefullt_PASS_till_godkant():
    """Kommer motsagelsen utifran ska den falla, inte tolkas snallt."""
    r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
    r.sektion("HONESTY")
    r.rad("BLOWUP VIOLATION vmax=91.0m/s")
    r.satt_dom("FAIL", "fartexplosion")
    t = r.text().replace("EYES VERDICT FAIL", "EYES VERDICT PASS")
    with pytest.raises(K.Kontraktsfel) as ei:
        K.las(t)
    assert "rule 5" in str(ei.value)


def test_overtradelse_med_FAIL_lases_men_ar_inte_godkant():
    r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
    r.sektion("HONESTY")
    r.rad("UNDERGROUND VIOLATION zmin=-0.220m")
    r.satt_dom("FAIL", "detaljen gick genom golvet")
    b = K.las(r.text())
    assert b.overtradelser() == ["UNDERGROUND"]
    assert b.godkand() is False


# ---- ovrigt --------------------------------------------------------------

def test_rapport_utan_dom_far_inte_skrivas():
    r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
    with pytest.raises(K.Kontraktsfel):
        r.text()


def test_orsak_med_radbrytning_avvisas():
    r = _rapport()
    with pytest.raises(K.Kontraktsfel):
        r.satt_dom("FAIL", "forsta raden\nandra raden")


def test_okand_sektion_kan_inte_byggas_av_misstag():
    r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
    with pytest.raises(K.Kontraktsfel):
        r.sektion("SPARKS")


def test_alla_kanda_radtyper_gar_att_bygga_och_lasa_tillbaka():
    """Varje monster i RADER ska ha minst ett prov som gar hela vagen runt."""
    prov = {
        ("MOTION", "GRIP"): ["GRIP NEVER_FORMED", "GRIP FORMED t=1.0s dist=2.0mm"],
        ("MOTION", "CARRY"): ["CARRY INCONCLUSIVE", "CARRY SLIPPING rot=12.5deg span=3.0s"],
        ("MOTION", "PLACE"): ["PLACE DROPPED z=0.020m err=0.0mm"[:0] or "PLACE DROPPED",
                              "PLACE OFF_TARGET err=45.0mm z=0.700m"],
        ("TIMING", "EDGE"): ["EDGE s1 FALL t=0.5s"],
        ("TIMING", "LATENCY"): ["LATENCY s1 -> robot1 -12.5ms"],
        ("TIMING", "DWELL"): ["DWELL st1 1.0s req=2.0s SHORT"],
        ("TIMING", "RACE"): ["RACE none", "RACE a+b dt=1.5ms"],
        ("THROUGHPUT", "STATION"): ["STATION st1 in=0 out=0 avg=0.0s min=0.0s max=0.0s"],
        ("SAFETY", "MINDIST"): ["MINDIST a+b 0.0mm t=1.0s"],
        ("SAFETY", "COLLISION"): ["COLLISION none", "COLLISION nodA x nodB t=2.0s"],
        ("HONESTY", "TELEPORT_TRANSFER"): ["TELEPORT_TRANSFER OK",
                                           "TELEPORT_TRANSFER VIOLATION dist=800.0mm t=1.0s"],
        ("HONESTY", "BLOWUP"): ["BLOWUP OK", "BLOWUP VIOLATION vmax=99.0m/s"],
        ("HONESTY", "UNDERGROUND"): ["UNDERGROUND OK", "UNDERGROUND VIOLATION zmin=-1.0m"],
        ("HONESTY", "NEVER_GRIPPED"): ["NEVER_GRIPPED OK", "NEVER_GRIPPED VIOLATION"],
        # v2 (M-65 §6)
        ("TIMING", "PHASE"): ["PHASE plc:Start -> grip_out dt=110.0ms tol=300.0ms res=63.5ms OK",
                              "PHASE plc:Start -> grip_out dt=0.0ms tol=20.0ms res=unknown INCONCLUSIVE"],
        ("SEQUENCE", "CYCLES"): ["CYCLES judged=3 broken=0 late=0 truncated=1 req=2"],
        ("SEQUENCE", "STEP"): ["STEP 0 plc:stopp RISE MISSING win=0.00s..0.50s",
                               "STEP 2 plc:slapp FALL TOO_LATE t=3.500s win=2.00s..3.30s"],
        ("SEQUENCE", "COUNT"): ["COUNT 1 plc:stopp n=2 max=1 EXCEEDED"],
        ("SEQUENCE", "INTERLOCK"): ["INTERLOCK plc:stopp+plc:slapp OK overlap=0.000s",
                                    "INTERLOCK a+b INCONCLUSIVE overlap=0.000s"],
        ("THROUGHPUT", "STARVED"): ["STARVED st1 9.500s req=1.000s EXCEEDED"],
        ("THROUGHPUT", "BLOCKED"): ["BLOCKED st1 0.000s req=1.000s OK"],
        ("THROUGHPUT", "BOTTLENECK"): ["BOTTLENECK none", "BOTTLENECK st1 starved 100.0%"],
        ("SCENE", "OBJECTS"): ["OBJECTS total=6 moving=2 still=4 unread=0"],
        ("SCENE", "THINNED"): ["THINNED factor=1 OK budget=5.0ms median=0.021ms"],
        ("SCENE", "UNCOMMANDED"): ["UNCOMMANDED none", "UNCOMMANDED stallage dist=500.0mm t=2.000s"],
        ("SCENE", "IDLE_COMMANDED"): ["IDLE_COMMANDED none", "IDLE_COMMANDED band_ut -> band_in t=2.000s"],
        ("SCENE", "FLUNG"): ["FLUNG none", "FLUNG del 5.39m/s t=2.500s"],
        ("LIMITS", "NOT_SIMULATED"): ["NOT_SIMULATED sensor_bounce"],
        ("LIMITS", "RESOLUTION"): ["RESOLUTION sample=50.0ms read=50.0ms join=13.45ms PRIOR phase=63.5ms",
                                   "RESOLUTION sample=50.0ms read=unknown join=5.30ms RUN phase=unknown"],
        ("LIMITS", "EXCLUDED"): ["EXCLUDED plc_scan 40.0ms"],
    }
    assert set(prov) == set(K.RADER), "varje radtyp i RADER maste ha ett prov"
    for (sektion, _), rader in prov.items():
        for rad in rader:
            r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
            r.sektion(sektion)
            r.rad(rad)
            r.satt_dom("FAIL", "provrapport")
            assert rad in K.las(r.text()).sektioner[0][1]


def test_en_rapport_utan_dom_ar_inte_godkand():
    """oga_kontrakt.godkand(): `if self.dom is None: return False`.
    Mutation till `return True` överlever hela sviten. Fail-closed-regeln
    (I3) för en rapport utan dom hade inget prov. Nu har den ett."""
    r = K.Rapport("t", "2026-09-04T17:00:00", 1.0, 20, 20.0)
    r.sektion("MOTION").rad("GRIP FORMED t=0.100s dist=1.0mm")
    assert r.dom is None
    assert r.godkand() is False

