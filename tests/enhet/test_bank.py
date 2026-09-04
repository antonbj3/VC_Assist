# -*- coding: utf-8 -*-
"""Bänken: mäter banken i stället för att påstå något om den.

Tre krav ur uppdraget prövas mekaniskt och ska falla som testfel om de bryts:

  1. Ingen uppgift utan facit.
  2. Ingen felklass utan uppgift.
  3. Facit uttryckt i ögats faktiska grammatik, alltså den som ligger i
     ext/vc_addon/vc_assist/oga_kontrakt.py och inte i en kopia här.

Till det kommer regel S2 ur docs/spec/96_ingen_skuld.md: varje grind måste ha en
trasig fixtur som fäller den. Den gäller också bankens egen linter, så varje
lintkod som banken lutar sig mot prövas med en medvetet trasig uppgift.
"""
import copy
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "bank"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import lasare                  # noqa: E402
import oga_kontrakt as K       # noqa: E402
import schema                  # noqa: E402

MINSTA_BANK = 40


@pytest.fixture(scope="module")
def bank():
    """Strikt laddning. En ogiltig uppgift ska stoppa hela bänken (I3)."""
    return lasare.ladda(strikt=True)


@pytest.fixture(scope="module")
def felklasser():
    return schema.las_felklasser()


# --------------------------------------------------------------- omfattning

def test_banken_laddar_och_ar_stor_nog(bank):
    assert len(bank) >= MINSTA_BANK, (
        "banken har %d uppgifter, kravet är minst %d" % (len(bank), MINSTA_BANK))


def test_task_id_matchar_filnamn_och_ar_unika(bank):
    sedda = set()
    for u in bank:
        stam = os.path.splitext(os.path.basename(u.sokvag))[0]
        assert stam == u.id, "%s ligger i filen %s" % (u.id, stam)
        assert u.id not in sedda, "dubblerat task_id %s" % u.id
        sedda.add(u.id)


def test_varje_uppgift_pekar_pa_kanda_komponenter(bank):
    for u in bank:
        for k in u.data["scene"]["components"]:
            assert k["uri"] in bank.katalogindex, (
                "%s: okänd URI %s" % (u.id, k["uri"]))


# ------------------------------------------------------- ingen uppgift utan facit

def test_ingen_uppgift_utan_facit(bank):
    """M6 är den bärande regeln: facit skrivs före försöket."""
    for u in bank:
        e = u.data["expect"]
        if e["gate"] == "OGAT":
            assert e["verdict"] in K.DOMAR, "%s saknar ögondom" % u.id
            assert e["lines"], "%s har ingen krävd ögonrad" % u.id
            if e["verdict"] != "PASS":
                assert e["reason_contains"], (
                    "%s fälls men säger inte vad domen ska handla om" % u.id)
        else:
            assert e["gate_code"], (
                "%s fälls av %s men namnger ingen kod" % (u.id, e["gate"]))
        assert e["runs"] >= 3, "%s mäter på färre än tre körningar" % u.id


def test_facitrader_finns_i_ogats_egen_grammatik(bank):
    """Skrivarsidan av kontraktet får pröva varje facitrad.

    Vi kontrollerar inte mot en kopia av grammatiken utan låter ögats egen
    Rapport.rad() ta emot en konkret rad som mallen tillåter. Går den igenom
    kan ögat skriva raden, och då går facit att jämföra maskinellt.
    """
    antal = 0
    for u in bank:
        e = u.data["expect"]
        for krav in list(e["lines"]) + list(e["forbidden_lines"]):
            monster = K.RADER.get((krav["section"], krav["template"].split(" ")[0]))
            assert monster is not None, (
                "%s: %s/%s finns inte i ögats grammatik"
                % (u.id, krav["section"], krav["template"]))
            vittne = None
            for kandidat in schema.vittnen(krav["template"]):
                r = K.Rapport("prov", "2026-09-04T00:00:00", 1.0, 1, 1.0)
                r.sektion(krav["section"])
                try:
                    r.rad(kandidat)
                except K.Kontraktsfel:
                    continue
                vittne = kandidat
                break
            assert vittne is not None, (
                "%s: ögat kan inte skriva någon rad som %r tillåter"
                % (u.id, krav["template"]))
            antal += 1
    assert antal > 200, "misstänkt få facitrader att pröva: %d" % antal


def test_ett_pass_kraver_aldrig_en_hederlighetsovertradelse(bank):
    """Kontraktets regel 5. Ett facit som kräver båda kan aldrig uppfyllas."""
    for u in bank:
        e = u.data["expect"]
        if e["gate"] == "OGAT" and e["verdict"] == "PASS":
            for krav in e["lines"]:
                assert " VIOLATION" not in krav["template"], (
                    "%s kräver %r under ett PASS" % (u.id, krav["template"]))


# ------------------------------------------------- ingen felklass utan uppgift

def test_varje_felklass_i_specen_har_minst_en_uppgift(bank, felklasser):
    """Täckningen mäts mot specens egen tabell, inte mot en lista i banken."""
    tackning = bank.tackning()
    assert set(tackning) == set(felklasser), (
        "banken och specen är inte överens om vilka felklasser som finns")
    tomma = bank.otackta_klasser()
    assert not tomma, "felklasser utan uppgift: %s" % ", ".join(tomma)


def test_varje_felklass_har_en_trasig_fixtur_som_faller_den(bank, felklasser):
    """S2: en grind som inte kan fyra är ett fel, inte en varning."""
    utan = bank.klasser_utan_fallande_fixtur()
    assert not utan, (
        "felklasser utan en medvetet trasig variant: %s" % ", ".join(utan))


def test_varje_variant_pekar_pa_en_hel_uppgift_som_finns(bank):
    ider = set(u.id for u in bank)
    for u in bank.varianter():
        original = u.data["variant_av"]
        assert original in ider, "%s pekar på %s som inte finns" % (u.id, original)
        assert not bank[original].ar_variant, (
            "%s pekar på en annan variant" % u.id)


# --------------------------------------- facit mot verkliga ögonrapporter

def test_de_trasiga_ogonrapporterna_foljer_kontraktet_byte_for_byte(bank):
    for u in bank.varianter():
        text = u.trasig_ogonrapport()
        if text is None:
            continue
        rapport = K.las(text)
        assert rapport.text() == text, (
            "%s: ögonrapporten överlever inte att läsas och skrivas tillbaka" % u.id)
        assert rapport.godkand() is False, (
            "%s: en trasig fixtur som blir godkänd mäter ingenting" % u.id)


def test_facit_haller_mot_varje_trasig_ogonrapport(bank):
    """Den starkaste kontrollen i filen: facit jämförs maskinellt mot en
    ögonrapport som följer den riktiga grammatiken."""
    provade = 0
    for u in bank.varianter():
        text = u.trasig_ogonrapport()
        if text is None:
            continue
        res = u.jamfor(text)
        assert not res.fel, "%s: %s" % (u.id, res.fel)
        assert res.dom_stammer, (
            "%s: facit väntar %s, ögat sa %s"
            % (u.id, u.data["expect"]["verdict"], res.observerad_dom))
        assert res.orsak_stammer, "%s: orsaken nämner inte %r" % (
            u.id, u.data["expect"]["reason_contains"])
        assert not res.saknade_rader, "%s saknar rader: %s" % (u.id, res.saknade_rader)
        assert not res.forbjudna_traffar, (
            "%s träffar förbjudna rader: %s" % (u.id, res.forbjudna_traffar))
        assert res.uppfyllt
        provade += 1
    assert provade >= 8, "för få ögonfixturer att pröva facit mot: %d" % provade


def test_facit_faller_en_rapport_som_inte_stammer(bank):
    """En jämförelse som godkänner allt är lika oanvändbar som en som fäller allt."""
    u = bank["T-91"]
    text = u.trasig_ogonrapport()
    ratt = u.jamfor(text)
    assert ratt.uppfyllt
    # samma rapport, men donet stiger EFTER givaren: ordningen som facit fäller
    vand = text.replace("EDGE ST010_STP_OPEN RISE t=12.150s",
                        "EDGE ST010_STP_OPEN RISE t=12.900s")
    fel = u.jamfor(vand)
    assert not fel.uppfyllt
    assert fel.saknade_rader, "den ändrade raden borde saknas mot facit"


# ---------------------------------------------------- gränsscenarier och spår

def test_varje_uppgift_har_normaldrift_och_ett_vandningsfall(bank):
    for u in bank:
        typer = [s["typ"] for s in u.data["scenarios"]]
        assert "normaldrift" in typer, "%s saknar normaldriftsfall" % u.id
        assert "vandning" in typer, "%s saknar vändningsfall" % u.id


def test_varje_analog_insignal_overskrids_at_bada_hall(bank):
    """Gränsscenarier är obligatoriska. (Tidigare motiverat med ett
    SemaPLC-tal som två källkontroller inte kunnat belägga; talet är struket,
    regeln står på egna ben. Se bank/README.md.) Ursprunglig lydelse:
    17,3 % fel vid gränsöverskridande mot 7,1 % vid
    normaldrift. Ett facit som bara kör normalfallet mäter nästan ingenting."""
    analoga = 0
    for u in bank:
        par = {}
        for s in u.data["control"]["signals"]:
            if s["dir"] == "in" and s["type"] in schema.ANALOGA_TYPER:
                par[s["name"]] = set()
                analoga += 1
        for sc in u.data["scenarios"]:
            if sc["typ"].startswith("gransvarde") and sc["signal"] in par:
                par[sc["signal"]].add(sc["typ"])
        for namn, sedda in par.items():
            assert sedda == {"gransvarde_lag", "gransvarde_hog"}, (
                "%s: %s överskrids inte åt båda håll, bara %s"
                % (u.id, namn, sorted(sedda) or "inget håll"))
    assert analoga >= 20, "för få analoga insignaler i banken: %d" % analoga


def test_karnutgangar_ar_utgangar_och_racker_for_en_sparjamforelse(bank):
    for u in bank:
        utgangar = set(s["name"] for s in u.data["control"]["signals"]
                       if s["dir"] == "out")
        assert u.data["core_outputs"], "%s namnger inga kärnutgångar" % u.id
        for namn in u.data["core_outputs"]:
            assert namn in utgangar, "%s: %s är ingen utsignal" % (u.id, namn)


def test_sparjamforelsen_ger_ett_till_ett_och_noll_till_oläsligt(bank):
    u = bank["T-91"]
    text = u.trasig_ogonrapport()
    karn = u.data["core_outputs"]

    poang, per = lasare.spar_poang(text, text, karn)
    assert poang == 1.0 and all(per.values())

    # en flank flyttad 750 ms, alltså långt utanför toleransen
    flyttad = text.replace("EDGE ST010_STP_OPEN RISE t=12.150s",
                           "EDGE ST010_STP_OPEN RISE t=12.900s")
    poang_flyttad, per_flyttad = lasare.spar_poang(text, flyttad, karn)
    assert poang_flyttad < 1.0
    assert per_flyttad["ST010_STP_OPEN"] is False

    # en flank flyttad 20 ms, alltså inom toleransen
    knuffad = text.replace("EDGE ST010_STP_OPEN RISE t=12.150s",
                           "EDGE ST010_STP_OPEN RISE t=12.170s")
    poang_knuff, _ = lasare.spar_poang(text, knuffad, karn)
    assert poang_knuff == 1.0

    # ett svar som inte går att läsa som en ögonrapport är noll, inte delvis rätt
    poang_trasig, per_trasig = lasare.spar_poang(text, "kompileringsfel\n", karn)
    assert poang_trasig == 0.0
    assert not any(per_trasig.values())


def test_svarighetsgraden_foljer_stegen_pa_svarighetsstegen(bank):
    for u in bank:
        steg = u.data["stege"]
        assert steg in schema.STEGE_SVARIGHET, "%s: okänt steg %s" % (u.id, steg)
        assert u.svarighet == schema.STEGE_SVARIGHET[steg], (
            "%s: steget %s ger %d, uppgiften säger %d"
            % (u.id, steg, schema.STEGE_SVARIGHET[steg], u.svarighet))


def test_uppgiftstexten_ar_sann_i_kedjan_over_opc_ua(bank):
    """VC har ingen inbyggd ST-motor. VC Premium är OPC UA-klient, så kedjan är
    ST -> OpenPLC Runtime v4 -> OPC UA -> scenen."""
    for u in bank:
        assert "OPC UA" in u.data["prompt"], (
            "%s låter som om VC körde logiken själv" % u.id)


# ------------------------------------------------------------- spridning

def test_banken_spanner_over_grupper_svarigheter_och_branscher(bank):
    per_grupp = bank.per_grupp()
    assert all(n > 0 for n in per_grupp.values()), (
        "tomma grupper: %s" % [g for g, n in per_grupp.items() if not n])
    per_svar = bank.per_svarighet()
    assert all(n > 0 for n in per_svar.values()), (
        "tomma svårighetsgrader: %s" % [d for d, n in per_svar.items() if not n])
    per_bransch = bank.per_bransch()
    tackta = [b for b, n in per_bransch.items() if n]
    assert len(tackta) >= 8, (
        "för smal branschtäckning, bara %d av %d: %s"
        % (len(tackta), len(per_bransch), tackta))


def test_talen_i_uppgifterna_ar_grundade_eller_markta_som_antaganden(bank):
    for u in bank:
        assert u.data["antaganden"], "%s påstår sig inte anta något" % u.id
        for a in u.data["antaganden"]:
            assert len(a["motiv"]) >= schema.MIN_MOTIV_TECKEN, (
                "%s: motivet för %r är för kort" % (u.id, a["vad"]))
        assert len(u.data["orsak"]) >= schema.MIN_ORSAK_TECKEN, (
            "%s säger inte vilken verklig driftsättningsmiss den speglar" % u.id)


def test_ingen_uppgift_lutar_sig_mot_ett_layoutarkiv_som_inte_finns(bank):
    """MÄTT 2026-09-04: noll .vcmx-layouter på disk i VC-installationen."""
    for u in bank:
        assert u.data["scene"]["layout_uri"] is None, (
            "%s pekar på en förbyggd layout" % u.id)


def test_robotarna_racker_till_last_och_radie(bank):
    """Mekanisk kontroll mot slarvet fem kilo last och tre meter räckvidd."""
    provade = 0
    for u in bank:
        brister = schema._validera_kapacitet(u.data, bank.katalogindex)
        assert not brister, "%s: %s" % (u.id, brister)
        for k in u.data["scene"]["components"]:
            if bank.katalogindex[k["uri"]]["kategori"] == "robot":
                provade += 1
    assert provade >= 15, "för få robotar att pröva kapaciteten på: %d" % provade


# ------------------------------------------- lintern måste kunna fyra (S2)

def _giltig(bank):
    return copy.deepcopy(bank["T-01"].data)


def _koder(post, bank):
    return set(k for k, _t in schema.validera(
        post, filnamn=os.path.join(schema.UPPGIFTSKATALOG, post["task_id"] + ".json"),
        katalogindex=bank.katalogindex))


def test_en_giltig_uppgift_slapps_igenom(bank):
    """Utan detta är varje fällning nedan värdelös: en linter som avvisar allt
    klarar alla övriga prov."""
    assert _koder(_giltig(bank), bank) == set()


TRASIGA = [
    ("M6_NO_FACIT", lambda p: p["expect"].update({"lines": []})),
    ("M6_NO_FACIT", lambda p: p["expect"].update({"verdict": "GRONT"})),
    ("M7_RUNS_TOO_FEW", lambda p: p["expect"].update({"runs": 2})),
    ("M8_UNKNOWN_CLASS", lambda p: p.update({"targets_class": ["F99"]})),
    ("M4_UNKNOWN_URI",
     lambda p: p["scene"]["components"][0].update({"uri": "bank://hittepa/x"})),
    ("M5_COORDS_IN_CONNECTION",
     lambda p: p["scene"]["connections"][0].update({"x_mm": 1200})),
    ("M19_UNKNOWN_ROLE",
     lambda p: p["scene"]["connections"][0].update({"to_role": "finns_inte"})),
    ("M9_SIGNAL_DIR", lambda p: p["control"]["signals"][0].update({"dir": "inout"})),
    ("M22_SIGNAL_NAME",
     lambda p: p["control"]["signals"][0].update({"name": "sig1"})),
    ("M10_TIMING_NO_TOLERANCE",
     lambda p: p["control"]["timing"].update({"tolerance_s": 0})),
    ("M11_EMPTY_SEQUENCE", lambda p: p["control"].update({"sequence": []})),
    ("M12_STATUS_WITHOUT_RUN", lambda p: p.update({"verified_status": "L1"})),
    ("M13_LINE_NOT_IN_GRAMMAR",
     lambda p: p["expect"]["lines"].append(
         {"section": "TIMING", "template": "DWELL ST010 fort req=0.4s OK"})),
    ("M13_LINE_NOT_IN_GRAMMAR",
     lambda p: p["expect"]["lines"].append(
         {"section": "MOTION", "template": "GRIP HALVVAGS"})),
    ("M14_PASS_WITH_VIOLATION",
     lambda p: p["expect"]["lines"].append(
         {"section": "HONESTY", "template": "TELEPORT_TRANSFER VIOLATION"})),
    ("M15_GATE_FACIT", lambda p: p["expect"].update({"gate": "G1"})),
    ("M17_DIFFICULTY", lambda p: p.update({"difficulty_stamp": "MATT"})),
    ("M18_PROMPT", lambda p: p.update({"prompt": "Bygg en cell."})),
    ("M29_KEDJA",
     lambda p: p.update({"prompt": p["prompt"].replace("OPC UA", "faltbuss")})),
    ("M20_GROUP_MISMATCH", lambda p: p.update({"grupp": "C"})),
    ("M24_LAYOUT_URI",
     lambda p: p["scene"].update({"layout_uri": "file:///C:/lager/cell.vcmx"})),
    ("M26_BRANSCH", lambda p: p.update({"bransch": "rymdfart"})),
    ("M27_ORSAK", lambda p: p.update({"orsak": "Det blir fel ibland."})),
    ("M28_ANTAGANDE", lambda p: p.update({"antaganden": []})),
    ("M28_ANTAGANDE",
     lambda p: p["antaganden"][0].update({"motiv": "for att"})),
    ("M30_SCENARIER",
     lambda p: p.update({"scenarios": [s for s in p["scenarios"]
                                       if s["typ"] != "vandning"]})),
    ("M30_SCENARIER",
     lambda p: p.update({"scenarios": [s for s in p["scenarios"]
                                       if s["typ"] != "gransvarde_hog"]})),
    ("M31_KARNUTGANGAR", lambda p: p.update({"core_outputs": ["ST010_PEC_PART"]})),
    ("M31_KARNUTGANGAR", lambda p: p.update({"core_outputs": []})),
    ("M32_STEGE", lambda p: p.update({"stege": "hiss"})),
    ("M21_VARIANT_TARGET", lambda p: p.update({"variant_av": "T-02"})),
    ("M1_MISSING_FIELD", lambda p: p.pop("goal")),
    ("M3_ID_PATTERN", lambda p: p.update({"task_id": "TX-1"})),
]


@pytest.mark.parametrize("kod,bryt", TRASIGA,
                         ids=["%02d_%s" % (i, k) for i, (k, _) in enumerate(TRASIGA)])
def test_lintern_faller_varje_kod_den_lutar_sig_mot(bank, kod, bryt):
    post = _giltig(bank)
    bryt(post)
    koder = _koder(post, bank)
    assert kod in koder, "väntade %s, fick %s" % (kod, sorted(koder) or "inget alls")


# ------------------------------------------------ M33: sparfacit, tillagt av M-45

def _med_sparfacit(bank):
    """T-07 ar den forsta uppgiften med sparfacit. Den giltiga posten provas
    for sig: en linter som avvisar allt klarar annars varje fallning nedan."""
    return copy.deepcopy(bank["T-07"].data)


def test_en_giltig_uppgift_med_sparfacit_slapps_igenom(bank):
    assert _koder(_med_sparfacit(bank), bank) == set()


def _flytta_krav_intill_en_andring(post):
    """Ett krav som ligger ett scan efter en insignalandring mater hur manga
    scan implementationen rakar ta pa sig, inte om styrlogiken ar riktig."""
    sekv = post["facit_spar"]["sekvenser"][0]
    satt = [s for s in sekv["steg"] if s["satt"]][0]
    sekv["steg"].append({"t_ms": satt["t_ms"] + 20, "satt": {},
                         "krav": {"ST050_CNV_RUN": False}, "varfor": "for nara"})


TRASIGT_SPARFACIT = [
    ("saknat falt", lambda p: p["facit_spar"].pop("motbevis")),
    ("inget motbevis", lambda p: p["facit_spar"].update({"motbevis": []})),
    ("motbevis utan namngiven brist",
     lambda p: p["facit_spar"]["motbevis"][0].update({"faller_pa": []})),
    ("motbevis utan kod",
     lambda p: p["facit_spar"]["motbevis"][0].update({"st": "   "})),
    ("tom referens", lambda p: p["facit_spar"].update({"referens": ""})),
    ("harkomst utan matning",
     lambda p: p["facit_spar"].update({"harkomst": "kanns rimligt"})),
    ("standard som inte namnger nagot",
     lambda p: p["facit_spar"].update({"standard": ""})),
    ("inga sekvenser", lambda p: p["facit_spar"].update({"sekvenser": []})),
    ("krav pa en signal som inte finns",
     lambda p: p["facit_spar"]["sekvenser"][0]["steg"][1]["krav"].update(
         {"ST050_FINNS_EJ": True})),
    ("satter en utsignal",
     lambda p: p["facit_spar"]["sekvenser"][0]["steg"][0]["satt"].update(
         {"SYS_ALARM": True})),
    ("krav utan skal",
     lambda p: p["facit_spar"]["sekvenser"][0]["steg"][1].update({"varfor": ""})),
    ("tid utanfor scanrutnatet",
     lambda p: p["facit_spar"]["sekvenser"][0]["steg"][1].update({"t_ms": 205})),
    ("krav for nara en insignalandring", _flytta_krav_intill_en_andring),
    ("invariant utan villkor",
     lambda p: p["facit_spar"]["invarianter"][0].update({"nar": {}})),
    ("invariant pa en sekvens som inte finns",
     lambda p: p["facit_spar"]["invarianter"][0].update({"sekvens": "hittepa"})),
    ("flankkrav pa en insignal",
     lambda p: p["facit_spar"]["flanker"][0].update({"signal": "ST050_PRT_PRS"})),
    ("okand flanktyp",
     lambda p: p["facit_spar"]["flanker"][0].update({"typ": "BADA"})),
    ("flankfonster som inte ar ett fonster",
     lambda p: p["facit_spar"]["flanker"][0].update({"fran_ms": 900,
                                                     "till_ms": 100})),
    ("referensen lacker in i uppgiftstexten",
     lambda p: p.update({"prompt": p["prompt"] + "\n"
                         + p["facit_spar"]["referens"].strip()[:80]})),
]


@pytest.mark.parametrize("vad,bryt", TRASIGT_SPARFACIT,
                         ids=[v.replace(" ", "_") for v, _ in TRASIGT_SPARFACIT])
def test_m33_faller_ett_sparfacit_som_inte_gar_att_doma(bank, vad, bryt):
    post = _med_sparfacit(bank)
    bryt(post)
    koder = _koder(post, bank)
    assert "M33_SPARFACIT" in koder, (
        "%s slapptes igenom; fick %s" % (vad, sorted(koder) or "inget alls"))


def test_en_gammal_uppgift_utan_sparfacit_ar_fortfarande_giltig(bank):
    """Bakatkompatibiliteten ar inte en avsikt utan ett prov: de 47 uppgifter
    som fanns fore M-45 saknar faltet och ska ga igenom oforandrade."""
    utan = [u for u in bank if not u.data.get("facit_spar")]
    assert len(utan) >= 47
    for u in utan:
        assert _koder(copy.deepcopy(u.data), bank) == set(), u.id


def test_m2_faller_nar_filnamnet_inte_matchar(bank):
    post = _giltig(bank)
    koder = set(k for k, _t in schema.validera(
        post, filnamn="/nagonstans/T-42.json", katalogindex=bank.katalogindex))
    assert "M2_ID_MISMATCH" in koder


def test_m23_faller_en_robot_som_inte_racker_till(bank):
    post = _giltig(bank)
    post["scene"]["components"].append(
        {"role": "robot", "uri": "bank://robot/abb_irb_360_1_1130", "count": 1})
    post["scene"]["components"].append(
        {"role": "gripdon", "uri": "bank://gripdon/vakuum_8_sug_80", "count": 1})
    koder = _koder(post, bank)
    assert "M23_ROBOT_KAPACITET" in koder, (
        "en 1 kg-robot med ett 6,5 kg gripdon och en 0,42 kg detalj ska falla")


def test_m25_faller_en_overlamning_utan_fullstandig_handskakning(bank):
    post = copy.deepcopy(bank["H-01"].data)
    post["control"]["signals"] = [s for s in post["control"]["signals"]
                                  if not s["name"].endswith("_RST")]
    post["core_outputs"] = [n for n in post["core_outputs"] if not n.endswith("_RST")]
    koder = _koder(post, bank)
    assert "M25_HANDSKAKNING" in koder


def test_m16_faller_en_variant_utan_artefakt(bank):
    post = copy.deepcopy(bank["T-91"].data)
    post.pop("broken")
    koder = _koder(post, bank)
    assert "M16_VARIANT_WITHOUT_ARTIFACT" in koder


def test_lintern_kraschar_inte_pa_skrap(bank):
    """S10: en rapport får aldrig kunna fälla domaren."""
    for skrap in (None, [], "en sträng", 17, {}, {"task_id": None},
                  {"task_id": "T-01"}):
        brister = schema.validera(skrap, katalogindex=bank.katalogindex)
        assert brister, "skräpet %r slapp igenom" % (skrap,)


def test_strikt_laddning_kastar_pa_en_ogiltig_bank(tmp_path, bank):
    post = _giltig(bank)
    post["expect"]["lines"] = []
    (tmp_path / "T-01.json").write_text(
        json.dumps(post, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(lasare.Bankfel):
        lasare.ladda(katalog=str(tmp_path), strikt=True)
    slapp = lasare.ladda(katalog=str(tmp_path), strikt=False)
    assert len(slapp) == 0 and slapp.problem


def test_lasaren_svarar_pa_fragorna(bank, felklasser):
    for klass in felklasser:
        traffar = bank.tacker(klass)
        assert traffar, "ingen uppgift täcker %s" % klass
        for u in traffar:
            assert klass in u.klasser
    with pytest.raises(lasare.Bankfel):
        bank.tacker("F404")
    assert sum(bank.per_svarighet().values()) == len(bank)
    assert sum(bank.per_grupp().values()) == len(bank)
    assert sum(bank.per_bransch().values()) == len(bank)
