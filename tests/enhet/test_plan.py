# -*- coding: utf-8 -*-
"""L0/L1/L2 for planeringslagret (svc/vc_assist_svc/plan/).

Kors utan VC. Fem saker provas, och varje kontroll provas at BADA hallen -
att den faller pa ett verkligt fel OCH slapper igenom det korrekta. En grind
som bara provats at ena hallet ar oprovad (docs/spec/95_testprotokoll.md).

1. SPECMODELLEN. Tre nivaer, JSON in och ut identiskt, och en strikt lasning
   som avvisar en okand nyckel i stallet for att ignorera den.
2. FORFININGEN. Allt som behovs men inte star i begaran ar ett markt antagande
   med motiv eller en fraga. Provet ar mekaniskt: det finns ingen tredje vag
   in i specen.
3. PLANEN MOT REGISTRET. Okant verktyg och fel argument avvisas VID
   PLANERINGEN, med registrets EGEN validering. Planen kan inte valja
   exekveringslage - routingen ags av utforaren (I12).
4. VERIFIERINGEN. Kravet skrivs i ogats grammatik, och en rad ogat inte kan
   skriva avvisas. Ingen rapport, avhuggen rapport och fel dom ar alla
   underkant (fail-closed, I3).
5. KORNINGEN. Protokoll med skal for varje steg, och aterupptagning som inte
   kor om det som lyckats.

Villkoren och ordningen provas i test_plan_villkor.py.

Bryggattrappen ags av test_verktyg.py och importeras darifran: en kopia hade
kunnat drifta ifran bryggans protokoll utan att nagot markte det.
"""
import ast
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lasare                                            # noqa: E402
import oga_kontrakt as K                                 # noqa: E402
from test_verktyg import Attrappbrygga, svar_for         # noqa: E402
from vc_assist_svc import verktyg as V                   # noqa: E402
from vc_assist_svc.plan import (Antagande, Bindning, Byggplan,  # noqa: E402
                                Del, DetaljeradSpec, Fraga,
                                Grundbegaran, Kontroll, Koppling, Korare,
                                Krav, Layoutport, Protokoll, Signal,
                                Steg, Takt, Uppgiftsgraf, Uppskjutet,
                                Verifieringskrav, planera, ur_bankuppgift,
                                ur_fritext)
from vc_assist_svc.plan import provplaner as PP          # noqa: E402
from vc_assist_svc.plan.fel import (Korningsfel, Layoutfel,  # noqa: E402
                                    Specfel, Verifieringsfel)
from vc_assist_svc.plan.korning import (EJ_UTFORD, FALLEN,  # noqa: E402
                                        HOPPAD, KORD)
from vc_assist_svc.plan.planering import OGA_FAKTUM      # noqa: E402


# ---- gemensamt ----------------------------------------------------------

BANK = lasare.ladda(strikt=False)
KARTA = PP.demonstrationskarta(BANK)

# Uppgifter vars facit ligger FORE ogat (grind 1-4) och som darfor inte bar
# nagon ogonrad att bevisa. Listan star har som facit, inte som ursakt: de ska
# falla pa P6, och gor de inte det har namnet nagot andrats.
UTAN_OGONFACIT = ("A-90", "P-90", "S-90", "S-91", "T-90")


def spec_for(task_id, karta=KARTA):
    return ur_bankuppgift(BANK[task_id].data, BANK.katalogindex, karta)


def plan_for(task_id, **kv):
    return planera(spec_for(task_id), **kv)


def ogonrapport(rader=(("SAFETY", "MINDIST stoppgrind+sidostyrning 14.0mm t=1.0s"),
                       ("SAFETY", "COLLISION none"),
                       ("HONESTY", "TELEPORT_TRANSFER OK"),
                       ("HONESTY", "BLOWUP OK"),
                       ("HONESTY", "UNDERGROUND OK")),
                dom=("PASS", "allt ratt")):
    """En ogonrapport skriven med ogats EGEN skrivare, aldrig for hand."""
    r = K.Rapport("prov", "2026-09-04T12:00:00", 10.0, 100, 10.0)
    aktiv = None
    for sektion, rad in rader:
        if sektion != aktiv:
            r.sektion(sektion)
            aktiv = sektion
        r.rad(rad)
    r.satt_dom(*dom)
    return r.text()


class Scenattrapp(Attrappbrygga):
    """Bryggattrapp som svarar som en scen: ekar namn och gransnitt.

    Bygger varje svar ur verktygets returns-schema (svar_for) och byter bara
    de falt provet handlar om. Da kan attrappen inte svara nagot verktyget
    inte fick svara.
    """

    def __init__(self, granssnitt=None, kan_koppla=True):
        Attrappbrygga.__init__(self)
        self.granssnitt = dict(granssnitt or {})
        self.kan_koppla = kan_koppla
        self.anropade = []

    def _resultat(self, args):
        namn, argument = _las_desc(args.get("desc") or "")
        self.anropade.append((namn, argument))
        svar = svar_for(V.REGISTER[namn])
        if namn == "load_component":
            svar["name"] = argument.get("name", "namnlos")
            svar["uri"] = argument["uri"]
        elif namn == "clone_component":
            svar["name"] = argument["new_name"]
            svar["source"] = argument["name"]
        elif namn == "list_interfaces":
            komponent = argument["component"]
            svar["component"] = komponent
            svar["interfaces"] = [
                {"name": n, "is_abstract": False, "is_connected": False,
                 "sections": 1}
                for n in self.granssnitt.get(komponent, ["Flow"])]
        elif namn == "can_connect":
            svar["can_connect"] = self.kan_koppla
        elif namn == "connect":
            svar["connected"] = True
        return svar


def _las_desc(desc):
    """'connect(component='A', interface='Flow')' -> (namn, argument).

    Attrappen far argumenten samma vag som operatoren ser dem i kolistan:
    genom verktygets egen beskriv_anrop.
    """
    trad = ast.parse(desc.strip(), mode="eval").body
    return (trad.func.id,
            dict((n.arg, ast.literal_eval(n.value)) for n in trad.keywords))


def utforare(brygga=None, urval=None):
    brygga = brygga or Scenattrapp()
    return V.Utforare(brygga, urval or V.urval_allt_pa(V.REGISTER)), brygga


def godkann_allt(qid, verktyg, beskrivning):
    return True


# ======================================================================
# 1. SPECMODELLEN
# ======================================================================

def test_grundbegaran_gar_ut_och_in_identiskt():
    b = Grundbegaran("fri-1", "bygg en singuleringsstation", "operator")
    assert Grundbegaran.fran_json(b.till_json()).till_json() == b.till_json()


def test_detaljerad_spec_gar_ut_och_in_identiskt():
    spec = spec_for("T-01")
    ut = spec.till_json()
    assert DetaljeradSpec.fran_json(ut).till_json() == ut
    assert json.dumps(DetaljeradSpec.fran_json(ut).till_json(), sort_keys=True) \
        == json.dumps(ut, sort_keys=True)


def test_byggplanen_gar_ut_och_in_identiskt():
    plan = plan_for("T-01")
    ut = plan.till_json()
    assert Byggplan.fran_json(ut).till_json() == ut


def test_hela_banken_gar_ut_och_in_identiskt():
    """En plan som inte overlever en tur genom JSON gar inte att aterupptas."""
    for uppgift in BANK:
        plan, fel = PP.bygg(uppgift, BANK.katalogindex, KARTA)
        assert plan is not None, fel
        ut = plan.till_json()
        assert Byggplan.fran_json(ut).till_json() == ut


def test_en_okand_nyckel_i_json_avvisas_i_stallet_for_att_ignoreras():
    data = Grundbegaran("a", "text", "operator").till_json()
    data["extra"] = 1
    with pytest.raises(Specfel) as fel:
        Grundbegaran.fran_json(data)
    assert "extra" in str(fel.value)


def test_en_saknad_nyckel_i_json_avvisas():
    data = Grundbegaran("a", "text", "operator").till_json()
    del data["kalla"]
    with pytest.raises(Specfel):
        Grundbegaran.fran_json(data)


def test_fel_formatversion_avvisas_i_stallet_for_att_gissas():
    data = Grundbegaran("a", "text", "operator").till_json()
    data["v"] = 99
    with pytest.raises(Specfel) as fel:
        Grundbegaran.fran_json(data)
    assert "99" in str(fel.value)


def test_ett_antagande_utan_motiv_avvisas_och_med_motiv_slapps_igenom():
    with pytest.raises(Specfel):
        Antagande("takten", "45/min", "for att", "standard")
    a = Antagande("takten", "45/min",
                  "takten star i begaran och behovde inte antas alls, men "
                  "motivet maste anda ga att lasa", "begaran")
    assert a.kalla == "begaran"


def test_ett_antagande_utan_kand_kalla_avvisas():
    with pytest.raises(Specfel):
        Antagande("x", "1", "ett motiv som ar tillrackligt langt for kravet pa "
                  "fyrtio tecken", "gissning")


def test_en_koppling_kan_inte_bara_koordinater():
    """I8: modellen anger relationer, aldrig koordinater."""
    data = Koppling("a", "b").till_json()
    data["position"] = [1, 2, 3]
    with pytest.raises(Specfel) as fel:
        Koppling.fran_json(data)
    assert "position" in str(fel.value)
    assert Koppling.fran_json(Koppling("a", "b").till_json()).till_roll == "b"


def test_en_takt_utan_tolerans_avvisas_och_med_tolerans_slapps_igenom():
    with pytest.raises(Specfel) as fel:
        Takt(cykeltid_s=1.33)
    assert "tolerans" in str(fel.value)
    assert Takt(cykeltid_s=1.33, tolerans_s=0.05).cykeltid_s == 1.33


def test_fa_korningar_avvisas_I5_kraver_minst_tre():
    with pytest.raises(Specfel) as fel:
        Takt(genomflode_per_h=100.0, korningar=1)
    assert "minst 3 oberoende" in str(fel.value)
    assert Takt(genomflode_per_h=100.0, korningar=3).korningar == 3


def test_en_takt_utan_tal_ar_ingen_takt():
    with pytest.raises(Specfel):
        Takt()


def test_en_koppling_till_en_roll_som_inte_finns_avvisas():
    begaran = Grundbegaran("x", "t", "operator")
    with pytest.raises(Specfel) as fel:
        DetaljeradSpec("x", begaran, [Del("a", "file:///a.vcm")],
                       [Koppling("a", "saknas")])
    assert "saknas" in str(fel.value)


def test_tva_delar_med_samma_roll_avvisas():
    begaran = Grundbegaran("x", "t", "operator")
    with pytest.raises(Specfel):
        DetaljeradSpec("x", begaran, [Del("a", "file:///a.vcm"),
                                      Del("a", "file:///b.vcm")])


# ======================================================================
# 2. FORFININGEN: antagande eller fraga, aldrig ett tyst val
# ======================================================================

def test_bankens_egna_antaganden_foljer_med_och_ar_markta_som_bankens():
    spec = spec_for("T-01")
    ur_bank = [a for a in spec.antaganden if a.kalla == "bank"]
    assert len(ur_bank) == len(BANK["T-01"].data["antaganden"])
    assert all(a.motiv for a in ur_bank)


def test_en_uri_utan_karta_blir_en_blockerande_fraga():
    """bank:// ar bankens vokabular, inte en fil VC kan ladda. En uppfunnen
    URI ar ett hart fel (I9), sa planen far inte valja."""
    spec = spec_for("T-01", karta=None)
    uri_fragor = [f for f in spec.fragor if f.id.startswith("uri:")]
    assert len(uri_fragor) == 3
    assert all(f.blockerar for f in uri_fragor)
    assert all("eCatalog" in f.vad for f in uri_fragor)


def test_samma_uri_med_karta_ger_ingen_fraga_alls():
    spec = spec_for("T-01")
    assert [f for f in spec.fragor if f.id.startswith("uri:")] == []
    assert all(d.uri.startswith("file:///") for d in spec.delar)


def test_en_uri_som_delas_av_tva_roller_ger_EN_fraga_med_bada_rollerna():
    spec = spec_for("A-03", karta=None)
    delade = [f for f in spec.fragor
              if f.id == "uri:bank://station/fixtur_pneumatisk_spann"]
    assert len(delade) == 1
    assert delade[0].vad.count(",") >= 1


def test_planeringens_egna_val_hamnar_i_SAMMA_lista_som_forfiningens():
    """Operatoren ska ha en lista att lasa, inte tva."""
    spec = spec_for("T-01")
    fore = len(spec.antaganden)
    plan = planera(spec)
    assert len(plan.spec.antaganden) > fore
    assert any(a.vad == "gransnittsval" for a in plan.spec.antaganden)
    assert any(a.vad == "placering" for a in plan.spec.antaganden)


def test_varje_antagande_i_varje_plan_bar_motiv_och_kalla():
    """Den mekaniska formen av regeln: det finns ingen omarkt vag in."""
    for uppgift in BANK:
        plan, _fel = PP.bygg(uppgift, BANK.katalogindex, KARTA)
        for a in plan.spec.antaganden:
            assert len(a.motiv) >= 40, (uppgift.id, a.vad)
            assert a.kalla in ("begaran", "bank", "katalog", "standard", "layout")
        for f in plan.spec.fragor:
            assert len(f.varfor) >= 40, (uppgift.id, f.id)


def test_fritext_med_en_entydig_katalogtraff_blir_ett_markt_antagande():
    b = Grundbegaran("fri-1", "En pneumatisk stoppgrind pa bandet, 600 mm "
                     "bandbredd, 45 burkar per minut.", "operator")
    spec = ur_fritext(b, BANK.katalogindex, KARTA)
    roller = sorted(d.roll for d in spec.delar)
    assert roller == ["band", "stoppgrind"]
    for a in spec.antaganden:
        if a.vad.startswith("komponent for"):
            assert "katalogindexet" in a.motiv and a.kalla == "katalog"


def test_fritext_med_flera_kandidater_blir_en_fraga_som_listar_dem():
    b = Grundbegaran("fri-2", "En robot som plockar ur en lada.", "operator")
    spec = ur_fritext(b, BANK.katalogindex, KARTA)
    val = [f for f in spec.fragor if f.id == "val:robot"]
    assert len(val) == 1 and val[0].blockerar
    assert "bank://robot/" in val[0].vad


def test_fritext_gissar_aldrig_topologin():
    b = Grundbegaran("fri-3", "Ett band med bandbredd 600 mm och en "
                     "pneumatisk stoppgrind.", "operator")
    spec = ur_fritext(b, BANK.katalogindex, KARTA)
    assert len(spec.delar) == 2
    assert spec.kopplingar == []
    fraga = [f for f in spec.fragor if f.id == "kopplingar"]
    assert len(fraga) == 1 and fraga[0].blockerar
    assert "I8" in fraga[0].varfor


def test_fritext_utan_matt_vagrar_valja_mellan_tva_lika_troliga_poster():
    """Katalogen har band_600 och band_400. Utan matt gar valet inte att
    harleda, och da ar det operatorens."""
    spec = ur_fritext(Grundbegaran("fri-3b", "Ett band och en pneumatisk "
                                   "stoppgrind.", "operator"),
                      BANK.katalogindex, KARTA)
    val = [f for f in spec.fragor if f.id == "val:band"]
    assert len(val) == 1
    assert "band_600" in val[0].vad and "band_400" in val[0].vad
    assert [d.roll for d in spec.delar] == ["stoppgrind"]


def test_fritext_utan_takt_fragar_och_med_takt_lases_den_ur_texten():
    utan = ur_fritext(Grundbegaran("f4", "En pneumatisk stoppgrind.",
                                   "operator"), BANK.katalogindex, KARTA)
    assert utan.takt is None
    assert any(f.id == "takt" for f in utan.fragor)

    med = ur_fritext(Grundbegaran("f5", "En pneumatisk stoppgrind, 45 burkar "
                                  "per minut.", "operator"),
                     BANK.katalogindex, KARTA)
    assert med.takt.genomflode_per_h == 2700.0
    assert not any(f.id == "takt" for f in med.fragor)


def test_fritext_gissar_aldrig_en_signals_riktning():
    spec = ur_fritext(Grundbegaran("f6", "Stoppgrinden styrs av "
                                   "ST010_STP_OPEN och ST010_PEC_PART.",
                                   "operator"), BANK.katalogindex, KARTA)
    assert spec.signaler == []
    riktning = [f for f in spec.fragor if f.id == "signalriktning"]
    assert len(riktning) == 1
    assert "ST010_STP_OPEN" in riktning[0].vad


def test_bankens_signaler_kommer_med_som_de_star():
    spec = spec_for("T-01")
    namn = [s.namn for s in spec.signaler]
    assert "ST010_PEC_PART" in namn and "EMG_OK" in namn
    assert all(isinstance(s, Signal) for s in spec.signaler)


# ======================================================================
# 3. PLANEN MOT VERKTYGSREGISTRET
# ======================================================================

def _plan_med_steg(steg, verifiering=None):
    begaran = Grundbegaran("prov", "en provplan", "test")
    krav = verifiering or Verifieringskrav(
        "PASS", [Krav("SAFETY", "COLLISION none")])
    spec = DetaljeradSpec("prov", begaran, verifiering=krav)
    return Byggplan("prov", spec, Uppgiftsgraf(steg))


def _oga_steg(beroenden=()):
    return Steg.kontrollsteg("verifiera",
                             Kontroll("oga", fakta_nyckel=OGA_FAKTUM),
                             "provar kravet mot ogats rapport",
                             beroenden=beroenden)


def test_ett_steg_med_okant_verktyg_avvisas_vid_planeringen():
    plan = _plan_med_steg([Steg.verktygssteg("a", "spawna_robot", {},
                                             "ett verktyg som inte finns"),
                           _oga_steg(("a",))])
    koder = [kod for kod, _ in plan.granska()]
    assert "P1_OKANT_VERKTYG" in koder


def test_ett_steg_med_kant_verktyg_slapps_igenom():
    plan = _plan_med_steg([Steg.verktygssteg("a", "list_components", {},
                                             "listar scenen"),
                           _oga_steg(("a",))])
    assert plan.granska() == []


def test_fel_argument_avvisas_vid_planeringen_inte_vid_korningen():
    plan = _plan_med_steg([Steg.verktygssteg("a", "load_component",
                                             {"url": "file:///x.vcm"},
                                             "stavfel i argumentnamnet"),
                           _oga_steg(("a",))])
    problem = plan.granska()
    assert [kod for kod, _ in problem] .count("P2_ARGUMENTFEL") >= 1
    assert any("url" in text for _kod, text in problem)


def test_saknat_obligatoriskt_argument_avvisas_vid_planeringen():
    plan = _plan_med_steg([Steg.verktygssteg("a", "load_component", {},
                                             "utan uri"), _oga_steg(("a",))])
    assert any("uri" in text for kod, text in plan.granska()
               if kod == "P2_ARGUMENTFEL")


def test_fel_typ_pa_ett_argument_avvisas_vid_planeringen():
    plan = _plan_med_steg([Steg.verktygssteg(
        "a", "set_transform", {"component": "R", "position": [1, 2]},
        "tva tal i stallet for tre"), _oga_steg(("a",))])
    assert "P2_ARGUMENTFEL" in [kod for kod, _ in plan.granska()]


def test_valideringen_ar_registrets_egen_och_inte_en_andra():
    """Provet: samma argument som registrets validera_argument fallr pa, med
    samma text. En andra validering hade kunnat saga nagot annat."""
    argument = {"component": "R", "position": [1, 2]}
    with pytest.raises(V.Argumentfel) as direkt:
        V.validera_argument(V.REGISTER["set_transform"], argument)
    plan = _plan_med_steg([Steg.verktygssteg("a", "set_transform", argument,
                                             "samma fel"), _oga_steg(("a",))])
    ur_planen = [t for kod, t in plan.granska() if kod == "P2_ARGUMENTFEL"]
    assert direkt.value.problem[0] in ur_planen[0]


def test_planen_kan_inte_bara_ett_exekveringslage_ens_i_json():
    """I12: routingen read->exec / write->exec_queue ags av utforaren."""
    steg = Steg.verktygssteg("a", "list_components", {}, "listar").till_json()
    steg["op"] = "exec_queue"
    with pytest.raises(Specfel) as fel:
        Steg.fran_json(steg)
    assert "I12" in str(fel.value)


def test_ett_argument_som_heter_som_routingen_fangas_ocksa():
    plan = _plan_med_steg([Steg.verktygssteg("a", "list_components",
                                             {"effect": "read"},
                                             "smyger in routingen"),
                           _oga_steg(("a",))])
    koder = [kod for kod, _ in plan.granska()]
    assert "P3_ROUTING_I_PLANEN" in koder


def test_routingen_sker_i_utforaren_och_foljer_verktygets_effect():
    plan = plan_for("T-01")
    utf, brygga = utforare()
    Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    ops = brygga.op_lista
    assert "exec_queue" in ops                 # load_component och connect
    assert "exec" in ops                       # list_interfaces och can_connect
    for op, args in brygga.logg:
        if op in ("exec", "exec_queue"):
            namn, _arg = _las_desc(args["desc"])
            vantad = V.op_for_effect(V.REGISTER[namn].effect)
            assert op == vantad, namn


def test_ett_avstangt_verktyg_avvisas_vid_planeringen_med_skalet():
    rapport = {"ytor": {yta: {"finns": True} for yta in V.KANDA_YTOR}}
    rapport["ytor"]["app.load"] = {"finns": False}
    urval = V.urval_ur_rapport(rapport, V.REGISTER)
    plan = plan_for("T-01")
    problem = plan.granska(urval=urval)
    assert "P4_AVSTANGT_VERKTYG" in [kod for kod, _ in problem]
    assert any("app.load" in text for _kod, text in problem)


def test_samma_plan_ar_ren_nar_ytan_finns():
    rapport = {"ytor": {yta: {"finns": True} for yta in V.KANDA_YTOR}}
    assert plan_for("T-01").granska(
        urval=V.urval_ur_rapport(rapport, V.REGISTER)) == []


def test_en_bindning_till_en_vag_verktyget_aldrig_svarar_med_avvisas():
    steg = [Steg.verktygssteg("lista", "list_interfaces",
                              {"component": "A"}, "hamtar gransnitten"),
            Steg.verktygssteg("hitta", "find_component",
                              {"name": Bindning("steg", "lista",
                                                vag="interfaces.0.namn",
                                                typ="string")},
                              "stavfel i vagen", beroenden=("lista",)),
            _oga_steg(("hitta",))]
    problem = _plan_med_steg(steg).granska()
    assert "P5_BINDNING" in [kod for kod, _ in problem]


def test_samma_bindning_med_ratt_vag_slapps_igenom():
    steg = [Steg.verktygssteg("lista", "list_interfaces",
                              {"component": "A"}, "hamtar gransnitten"),
            Steg.verktygssteg("hitta", "find_component",
                              {"name": Bindning("steg", "lista",
                                                vag="interfaces.0.name",
                                                typ="string")},
                              "ratt vag", beroenden=("lista",)),
            _oga_steg(("hitta",))]
    assert _plan_med_steg(steg).granska() == []


def test_en_bindning_med_fel_typ_avvisas():
    steg = [Steg.verktygssteg("lista", "list_interfaces",
                              {"component": "A"}, "hamtar gransnitten"),
            Steg.verktygssteg("hitta", "find_component",
                              {"name": Bindning("steg", "lista",
                                                vag="interfaces.0.name",
                                                typ="integer")},
                              "fel typ", beroenden=("lista",)),
            _oga_steg(("hitta",))]
    assert "P5_BINDNING" in [kod for kod, _ in _plan_med_steg(steg).granska()]


def test_en_namngiven_bindning_maste_komma_ur_en_bindningskontroll():
    steg = [Steg.verktygssteg("lista", "list_interfaces",
                              {"component": "A"}, "hamtar gransnitten"),
            Steg.verktygssteg("hitta", "find_component",
                              {"name": Bindning("namngiven", "lista",
                                                namn="if_a")},
                              "binder till ett verktygssteg",
                              beroenden=("lista",)),
            _oga_steg(("hitta",))]
    assert "P5_BINDNING" in [kod for kod, _ in _plan_med_steg(steg).granska()]


def test_bindningar_provas_med_vittnesvarden_mot_schemat():
    """Vittnet har ratt typ, sa allt utom det annu okanda vardet provas."""
    steg = Steg.verktygssteg("a", "connect",
                             {"component": "A",
                              "interface": Bindning("namngiven", "p",
                                                    namn="if_a"),
                              "other_component": "B",
                              "other_interface": Bindning("namngiven", "p",
                                                          namn="if_b")},
                             "kopplar")
    argument = steg.argument_med_vittnen()
    assert argument["interface"] == "vittne"
    V.validera_argument(V.REGISTER["connect"], argument)


def test_en_plan_utan_verifiering_ar_en_kandidat_aldrig_en_leverans():
    plan = _plan_med_steg([Steg.verktygssteg("a", "list_components", {}, "x")],
                          verifiering=Verifieringskrav("PASS"))
    koder = [kod for kod, _ in plan.granska()]
    assert "P6_INGEN_VERIFIERING" in koder
    ja, skal = plan.leverabel()
    assert not ja and "candidate" in skal


def test_en_plan_med_verifiering_men_utan_kontrollsteg_avvisas():
    plan = _plan_med_steg([Steg.verktygssteg("a", "list_components", {}, "x")])
    assert "P10_INGEN_OGONKONTROLL" in [kod for kod, _ in plan.granska()]


def test_en_blockerande_fraga_gor_planen_ej_leverabel_tills_den_ar_besvarad():
    spec = spec_for("T-01")
    spec.fragor.append(Fraga("hjalp", "vilken hall ska bandet ga?",
                             "riktningen framgar inte av begaran och styr "
                             "hela cellens geometri"))
    plan = planera(spec)
    ja, _skal = plan.leverabel()
    assert not ja
    assert "P7_OBESVARAD_FRAGA" in [kod for kod, _ in plan.granska()]
    spec.fragor[-1].besvara("fran vanster till hoger")
    assert plan.leverabel()[0]


def test_ett_tomt_svar_pa_en_fraga_ar_inget_svar():
    with pytest.raises(Specfel):
        Fraga("x", "vad?", "ett skal som ar langt nog for kravet pa fyrtio "
              "tecken").besvara("   ")


def test_sammanfattningen_bar_talen_en_matning_vill_ha():
    s = plan_for("T-01").sammanfattning()
    assert s["steg"] == 19 and s["kontrollsteg"] == 8
    assert s["skrivande_steg"] == 5     # tre inlasningar och tva kopplingar
    assert s["verifieringskrav"] == 5 and s["uppskjutna_krav"] == 7


# ======================================================================
# 4. VERIFIERINGEN
# ======================================================================

def test_en_rad_ogat_inte_kan_skriva_avvisas():
    with pytest.raises(Verifieringsfel):
        Krav("SAFETY", "KOLLISION ingen")
    with pytest.raises(Verifieringsfel):
        Krav("SAKERHET", "COLLISION none")


def test_en_rad_ogat_kan_skriva_slapps_igenom():
    assert Krav("SAFETY", "COLLISION none").sektion == "SAFETY"
    assert Krav("TIMING", "DWELL ST010 *s req=0.4s OK").matchar(
        "DWELL ST010 0.42s req=0.4s OK")


def test_ett_krav_som_kraver_en_hederlighetsovertradelse_och_PASS_avvisas():
    with pytest.raises(Verifieringsfel) as fel:
        Verifieringskrav("PASS", [Krav("HONESTY",
                                       "TELEPORT_TRANSFER VIOLATION")])
    assert "HONESTY" in str(fel.value)


def test_ett_uppskjutet_krav_utan_skal_avvisas():
    with pytest.raises(Verifieringsfel):
        Uppskjutet("TIMING", "RACE none", "senare")


def test_en_ratt_rapport_uppfyller_kravet():
    dom = spec_for("T-01").verifiering.doma(ogonrapport())
    assert dom.uppfyllt and dom.observerad_dom == "PASS"


def test_en_rapport_som_saknar_en_kravd_rad_underkanns_och_sager_vilken():
    krav = spec_for("T-01").verifiering
    dom = krav.doma(ogonrapport(
        rader=(("SAFETY", "COLLISION none"),
               ("HONESTY", "TELEPORT_TRANSFER OK"),
               ("HONESTY", "BLOWUP OK"),
               ("HONESTY", "UNDERGROUND OK"))))
    assert not dom.uppfyllt
    assert any(k.mall.startswith("MINDIST") for k in dom.saknade)


def test_en_forbjuden_rad_underkanner_aven_ett_PASS():
    krav = Verifieringskrav(
        "PASS", [Krav("SAFETY", "COLLISION none")],
        [Krav("SAFETY", "MINDIST stoppgrind+sidostyrning *mm t=*s")])
    dom = krav.doma(ogonrapport())
    assert not dom.uppfyllt and dom.forbjudna_traffar


def test_ingen_rapport_ar_inte_ett_godkannande():
    dom = spec_for("T-01").verifiering.doma(None)
    assert not dom.uppfyllt and "tystnad" in dom.text()


def test_en_avhuggen_rapport_ar_inte_ett_godkannande():
    text = ogonrapport()
    avhuggen = "\n".join(text.splitlines()[:-1]) + "\n"
    dom = spec_for("T-01").verifiering.doma(avhuggen)
    assert not dom.uppfyllt and "truncated" in dom.text()


def test_en_rapport_fran_en_okand_ogonversion_ar_inte_ett_godkannande():
    text = ogonrapport().replace("EYES v%d" % K.EYES_VERSION, "EYES v99", 1)
    dom = spec_for("T-01").verifiering.doma(text)
    assert not dom.uppfyllt and "unknown eyes version" in dom.text()


def test_fel_dom_underkanns_aven_om_alla_rader_finns():
    krav = Verifieringskrav("PASS", [Krav("SAFETY", "COLLISION none")])
    text = ogonrapport(rader=(("SAFETY", "COLLISION none"),),
                       dom=("INCONCLUSIVE", "for fa prov"))
    dom = krav.doma(text)
    assert not dom.uppfyllt and dom.observerad_dom == "INCONCLUSIVE"


def test_varje_facitrad_i_banken_hamnar_i_EN_av_listorna_ingen_tappas():
    """Ett uppskjutet krav ar markt. Ett bortglomt ar osynligt."""
    for uppgift in BANK:
        e = uppgift.data["expect"]
        krav = spec_for(uppgift.id).verifiering
        antal_in = len(e["lines"]) + len(e["forbidden_lines"])
        antal_ut = (len(krav.rader) + len(krav.forbjudna)
                    + len(krav.uppskjutna))
        assert antal_in == antal_ut, uppgift.id


def test_uppskjutna_krav_bar_skalet_och_pekar_ut_vem_som_bevisar_dem():
    krav = spec_for("T-01").verifiering
    assert krav.uppskjutna
    for u in krav.uppskjutna:
        assert u.sektion in ("TIMING", "THROUGHPUT", "MOTION")
        assert "fas 7" in u.skal


# ======================================================================
# 5. LAYOUTPORTEN
# ======================================================================

class Provlayout(object):
    """En layoutmotor som lagger ut delarna pa en rad. Provets motpart."""

    def __init__(self, steg_mm=1000.0, antaganden=(), fragor=(), extra=None):
        self.steg_mm = steg_mm
        self.antaganden = list(antaganden)
        self.fragor = list(fragor)
        self.extra = extra
        self.begaran = None

    def placera(self, begaran):
        self.begaran = begaran
        placeringar = []
        for n, del_ in enumerate(begaran["delar"]):
            placeringar.append({
                "roll": del_["roll"],
                "position_mm": [n * self.steg_mm, 0.0, 0.0],
                "wpr_deg": [0.0, 0.0, 0.0],
                "motiv": "lagd pa rad med %.0f mm mellan mitterna"
                         % self.steg_mm})
        if self.extra:
            placeringar.append(self.extra)
        return {"v": 1, "placeringar": placeringar,
                "antaganden": self.antaganden, "fragor": self.fragor}


def test_utan_layoutmotor_satts_inga_koordinater_och_det_star_utskrivet():
    plan = plan_for("T-01")
    assert not [s for s in plan.graf if s.verktyg == "set_transform"]
    antagande = [a for a in plan.spec.antaganden if a.vad == "placering"]
    assert len(antagande) == 1 and "plug and play" in antagande[0].varde


def test_med_layoutmotor_blir_varje_placering_ett_set_transform_med_motiv():
    motor = Provlayout()
    plan = plan_for("T-01", layout=Layoutport(motor), frigang_mm=800.0)
    placeringar = [s for s in plan.graf if s.verktyg == "set_transform"]
    assert len(placeringar) == 3
    assert all("layoutmotorn:" in s.motiv for s in placeringar)
    assert motor.begaran["frigang_mm"] == 800.0
    assert plan.granska() == []


def test_layoutbegaran_bar_relationerna_men_inga_koordinater():
    motor = Provlayout()
    plan_for("T-01", layout=Layoutport(motor), frigang_mm=800.0)
    text = json.dumps(motor.begaran)
    assert "kopplingar" in motor.begaran and motor.begaran["kopplingar"]
    assert "position" not in text and "wpr" not in text


def test_layout_utan_frigang_blir_en_fraga_och_inga_koordinater():
    """Ett avstand vi valde sjalva hade bestamt cellens yta."""
    plan = plan_for("T-01", layout=Layoutport(Provlayout()))
    assert not [s for s in plan.graf if s.verktyg == "set_transform"]
    assert any(f.id == "frigang" for f in plan.spec.fragor)


def test_en_placering_av_en_roll_som_inte_finns_avvisas():
    motor = Provlayout(extra={"roll": "spoke", "position_mm": [0, 0, 0],
                              "wpr_deg": [0, 0, 0], "motiv": "hittad pa"})
    with pytest.raises(Layoutfel) as fel:
        plan_for("T-01", layout=Layoutport(motor), frigang_mm=800.0)
    assert "spoke" in str(fel.value)


def test_en_placering_utan_motiv_avvisas():
    class Utanmotiv(Provlayout):
        def placera(self, begaran):
            svar = Provlayout.placera(self, begaran)
            svar["placeringar"][0]["motiv"] = ""
            return svar
    with pytest.raises(Layoutfel) as fel:
        plan_for("T-01", layout=Layoutport(Utanmotiv()), frigang_mm=800.0)
    assert "motiv" in str(fel.value)


def test_en_position_som_inte_ar_tre_tal_avvisas():
    class Trasig(Provlayout):
        def placera(self, begaran):
            svar = Provlayout.placera(self, begaran)
            svar["placeringar"][0]["position_mm"] = [0.0, 0.0]
            return svar
    with pytest.raises(Layoutfel):
        plan_for("T-01", layout=Layoutport(Trasig()), frigang_mm=800.0)


def test_en_okand_version_pa_layoutsvaret_avvisas():
    class Framtida(Provlayout):
        def placera(self, begaran):
            svar = Provlayout.placera(self, begaran)
            svar["v"] = 2
            return svar
    with pytest.raises(Layoutfel):
        plan_for("T-01", layout=Layoutport(Framtida()), frigang_mm=800.0)


def test_layoutmotorns_antaganden_och_fragor_hamnar_i_specen():
    motor = Provlayout(
        antaganden=[{"vad": "radavstand", "varde": "1000 mm",
                     "motiv": "avstandet ar valt sa att en operator kommer "
                              "mellan maskinerna; det ar inte matt"}],
        fragor=[{"id": "hall", "vad": "at vilket hall gar flodet?",
                 "varfor": "flodesriktningen bestammer var stationerna hamnar "
                           "och gar inte att lasa ur delarna",
                 "blockerar": False}])
    plan = plan_for("T-01", layout=Layoutport(motor), frigang_mm=800.0)
    assert any(a.kalla == "layout" for a in plan.spec.antaganden)
    assert any(f.id == "hall" for f in plan.spec.fragor)


def test_en_motor_utan_placera_avvisas_direkt():
    with pytest.raises(Layoutfel):
        Layoutport(object())


def test_delar_motorn_inte_placerade_blir_ett_antagande():
    class Halv(Provlayout):
        def placera(self, begaran):
            svar = Provlayout.placera(self, begaran)
            svar["placeringar"] = svar["placeringar"][:1]
            return svar
    plan = plan_for("T-01", layout=Layoutport(Halv()), frigang_mm=800.0)
    assert len([s for s in plan.graf if s.verktyg == "set_transform"]) == 1
    assert any(a.vad.startswith("placering av") for a in plan.spec.antaganden)


# ======================================================================
# 6. KORNINGEN
# ======================================================================

def test_en_hel_korning_ger_en_post_per_steg_och_varje_post_bar_ett_skal():
    plan = plan_for("T-01")
    utf, _brygga = utforare()
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    assert len(prot) == len(plan.graf)
    assert all(p.skal for p in prot)
    assert prot.klar(plan)[0]
    assert prot.rakning()[KORD] == len(plan.graf)


def test_skrivande_steg_stannar_i_kon_nar_ingen_godkanner():
    """I12: godkannandet ar operatorens. Koraren godkanner sig inte sjalv."""
    plan = plan_for("T-01")
    utf, _brygga = utforare()
    prot = Korare(utf).kor(plan, fakta={OGA_FAKTUM: ogonrapport()})
    koade = prot.koade()
    assert koade and all(p.qid for p in koade)
    assert all(V.REGISTER[p.verktyg].effect == "write" for p in koade)
    assert prot.status("namn_band") == EJ_UTFORD


def test_verifieringssteget_faller_utan_ogonrapport():
    plan = plan_for("T-01")
    utf, _brygga = utforare()
    prot = Korare(utf, godkannare=godkann_allt).kor(plan, fakta={})
    post = prot.verifieringspost(plan)
    assert post.status == FALLEN and "tystnad" in post.skal
    assert not prot.klar(plan)[0]


def test_verifieringssteget_gar_igenom_med_en_ratt_rapport():
    plan = plan_for("T-01")
    utf, _brygga = utforare()
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    post = prot.verifieringspost(plan)
    assert post.status == KORD and post.resultat["uppfyllt"] is True
    assert post.resultat["dom"] == "PASS"


def test_en_komponent_med_tva_gransnitt_faller_kontrollen_med_kandidaterna():
    """Da ar valet operatorens, och planen tiger inte om det."""
    plan = plan_for("T-01")
    brygga = Scenattrapp(granssnitt={"band": ["Flow", "Backflow"]})
    utf, _b = utforare(brygga)
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    post = prot.post("par1")
    assert post.status == FALLEN
    assert "Backflow" in post.skal and "operatoren" in post.skal
    assert prot.status("koppla1") == EJ_UTFORD


def test_ett_nej_fran_can_connect_stoppar_kopplingen():
    """VC domer kompatibiliteten; planen raknar aldrig om den (I1)."""
    plan = plan_for("T-01")
    utf, _b = utforare(Scenattrapp(kan_koppla=False))
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    assert prot.status("kan1") == KORD          # fragan stalldes
    assert prot.status("kanok1") == FALLEN      # och svaret var nej
    assert prot.status("koppla1") == EJ_UTFORD


def test_ett_verktygsfel_blir_en_post_med_skal_och_inte_en_krasch():
    plan = plan_for("T-01")

    class Fallande(Scenattrapp):
        def _resultat(self, args):
            namn, _arg = _las_desc(args.get("desc") or "")
            if namn == "list_interfaces":
                return {"component": "band"}       # bryter returns-schemat
            return Scenattrapp._resultat(self, args)

    utf, _b = utforare(Fallande())
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    post = prot.post("gr1_a")
    assert post.status == FALLEN and "Svarsfel" in post.skal


def test_ett_fel_namn_efter_inlasning_stoppar_planen_med_skal():
    """VC byter namn pa en komponent vars namn redan finns i layouten."""
    plan = plan_for("T-01")

    class Namnbytare(Scenattrapp):
        def _resultat(self, args):
            svar = Scenattrapp._resultat(self, args)
            namn, _arg = _las_desc(args.get("desc") or "")
            if namn == "load_component":
                svar["name"] = svar["name"] + "#2"
            return svar

    utf, _b = utforare(Namnbytare())
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    assert prot.status("namn_band") == FALLEN
    assert "band#2" in prot.post("namn_band").skal


class Trasigalistning(Scenattrapp):
    """Bryggan svarar utan gransnittslistan: svaret haller inte returns."""

    def _resultat(self, args):
        namn, _arg = _las_desc(args.get("desc") or "")
        if namn == "list_interfaces":
            return {"component": "band"}
        return Scenattrapp._resultat(self, args)


def test_aterupptagning_kor_inte_om_det_som_redan_lyckats():
    plan = plan_for("T-01")
    utf, _b = utforare(Trasigalistning())
    forsta = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    assert forsta.status("gr1_a") == FALLEN
    assert forsta.status("ladda_band") == KORD
    lyckade_forst = [p.steg for p in forsta if p.status == KORD]

    hel = Scenattrapp()
    utf2, _b2 = utforare(hel)
    andra = Korare(utf2, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()}, tidigare=forsta)

    kordes_igen = set(namn for namn, _arg in hel.anropade)
    assert "load_component" not in kordes_igen      # lyckades redan
    for steg in lyckade_forst:
        assert andra.post(steg).skal.startswith("aterupptagen")
    assert andra.klar(plan)[0]


def test_aterupptagning_provar_om_det_som_INTE_lyckades():
    plan = plan_for("T-01")
    utf, _b = utforare(Trasigalistning())
    forsta = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    hel = Scenattrapp()
    utf2, _b2 = utforare(hel)
    andra = Korare(utf2, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()}, tidigare=forsta)
    kordes_igen = set(namn for namn, _arg in hel.anropade)
    assert "list_interfaces" in kordes_igen         # foll, provas om
    assert andra.status("gr1_a") == KORD
    assert andra.status("koppla1") == KORD


def test_ett_lyckat_stegs_svar_bars_over_och_lases_igen_vid_aterupptagning():
    """Aterupptagningen laser inte om scenen: det som lyckades bar sitt svar.

    Darfor gar en KOPPLING som foll pa ett tvetydigt gransnitt inte att laga
    genom att bara kora igen - listningen lyckades ju. Det ar avsiktligt:
    ett nytt svar pa en gammal fraga vore en ny korning, inte en fortsattning.
    """
    plan = plan_for("T-01")
    utf, _b = utforare(Scenattrapp(granssnitt={"band": ["Flow", "Backflow"]}))
    forsta = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    assert forsta.status("par1") == FALLEN and forsta.status("gr1_a") == KORD
    andra = Korare(utforare(Scenattrapp())[0], godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()}, tidigare=forsta)
    assert andra.status("par1") == FALLEN
    assert "Backflow" in andra.post("par1").skal


def test_ett_protokoll_fran_en_annan_plan_avvisas():
    plan = plan_for("T-01")
    frammande = Protokoll("nagon_annan_plan")
    with pytest.raises(Korningsfel):
        Korare(utforare()[0]).kor(plan, tidigare=frammande)


def test_protokollet_gar_ut_och_in_identiskt():
    plan = plan_for("T-01")
    utf, _b = utforare()
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    ut = prot.till_json()
    assert Protokoll.fran_json(ut).till_json() == ut


def test_en_koad_plan_kan_aterupptas_efter_godkannandet():
    """Vagen operatoren faktiskt gar: kor, godkann kon, kor vidare."""
    plan = plan_for("T-01")
    utf, _b = utforare()
    utan = Korare(utf).kor(plan, fakta={OGA_FAKTUM: ogonrapport()})
    assert utan.koade()
    utf2, _b2 = utforare()
    med = Korare(utf2, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()}, tidigare=utan)
    assert med.klar(plan)[0]


def test_alternativet_klona_eller_las_in_igen_kors_som_ett_alternativ():
    """En del med antal 2: antingen klonas den, eller lases in en gang till."""
    begaran = Grundbegaran("tva", "tva likadana banor", "operator")
    spec = DetaljeradSpec(
        "tva", begaran, [Del("band", "file:///band.vcm", antal=2)],
        verifiering=Verifieringskrav("PASS", [Krav("SAFETY", "COLLISION none")]))
    plan = planera(spec)
    assert plan.granska() == []
    utf, brygga = utforare()
    prot = Korare(utf, godkannare=godkann_allt).kor(
        plan, fakta={OGA_FAKTUM: ogonrapport()})
    assert prot.status("inst_band_2_a_klon") == KORD
    assert prot.status("inst_band_2_b_ladd") == HOPPAD
    assert "clone_component" in set(n for n, _a in brygga.anropade)


# ======================================================================
# 7. PROVPLANERNA OCH MATNINGEN
# ======================================================================

def test_minst_tio_provplaner_gar_att_bygga_ur_banken():
    byggen = PP.bygg_alla(BANK, KARTA)
    byggda = [p for _id, p, _fel in byggen if p is not None]
    assert len(byggda) >= 10
    assert len(byggda) == len(BANK)          # ingen uppgift ar oplanerbar


def test_varje_provplan_ar_ordnad_och_cykelfri():
    for _id, plan, _fel in PP.bygg_alla(BANK, KARTA):
        ordning = plan.ordning()
        assert len(ordning) == len(plan.graf)
        assert plan.graf.cykler() == []


def test_matningen_rapporterar_antaganden_och_fragor():
    m = PP.mat(PP.bygg_alla(BANK, KARTA))
    r = m["rakning"]
    assert r["planer"] == len(BANK)
    assert r["antaganden"] > 0 and m["antagandekallor"]["bank"] > 0
    assert r["verifieringskrav"] > 0 and r["uppskjutna_krav"] > 0


def test_utan_urikarta_blockeras_varje_plan_av_uri_fragan():
    m = PP.mat(PP.bygg_alla(BANK))
    assert m["rakning"]["leverabla"] == 0
    assert m["lintkoder"]["P7_OBESVARAD_FRAGA"] > 0


def test_med_karta_ar_bara_uppgifterna_utan_ogonfacit_kvar():
    m = PP.mat(PP.bygg_alla(BANK, KARTA))
    ej = sorted(task_id for task_id, _problem in m["ej_leverabla"])
    assert ej == sorted(UTAN_OGONFACIT)
    assert m["rakning"]["leverabla"] == len(BANK) - len(UTAN_OGONFACIT)


def test_de_uppgifterna_falls_pa_att_deras_grind_ligger_fore_ogat():
    for task_id in UTAN_OGONFACIT:
        assert BANK[task_id].data["expect"]["gate"] in ("G1", "G2", "G3", "G4")
        koder = [kod for kod, _ in plan_for(task_id).granska()]
        assert "P6_INGEN_VERIFIERING" in koder


def test_rapporten_gar_att_skriva_ut():
    import io
    strom = io.StringIO()
    PP.skriv_rapport(BANK, strom)
    text = strom.getvalue()
    assert "PROVPLANER" in text and "leverabla" in text
    assert "INTE verkliga VC-URI" in text
