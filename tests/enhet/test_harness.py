# -*- coding: utf-8 -*-
"""L0/L1/L2 för LLM-harnessen. Körs utan VC och utan nätverk.

Fyra saker prövas här, och den fjärde är den som gör de tre första värda
något:

  1. INSTRUKTIONSKORPUSEN. Att den laddar, att varje regel har en härkomst som
     går att slå upp på disk, och att varje regel märkt "block" namnger en
     mekanism som verkligen finns.
  2. SAMMANSÄTTNINGEN. Att prompten byggs, att kapningen tar det minst
     farliga först, och att de okapbara blocken står kvar även när budgeten
     är för liten — och att bygget hellre kastar än skickar en prompt utan
     säkerhetsgränsen.
  3. TVINGNINGEN. Att grindarna anropar de mekanismer som redan finns
     (registret, schemat, api_index, skrivgrinden, ST-validatorn) i stället
     för att bygga en andra validering.
  4. TRASIGA FIXTURER. S2 i docs/spec/96_ingen_skuld.md: varje grind måste ha
     ett fall som fäller den. En grind som aldrig fällt är oprövad. Därför
     har varje kontroll i korpuslintern en medvetet trasig korpus här.
"""
import ast
import json
import os
import shutil
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

import skrivgrind                                      # noqa: E402
from vc_assist_svc import verktyg as V                 # noqa: E402
from vc_assist_svc.harness import (arlighet as A, fel as Fel,               # noqa: E402
                                   forgranskning as Fg, instruktioner as I,
                                   kanal as Kn, loop as L, mekanismer as Mk,
                                   modell as Mo, oga as Og,
                                   oversattning as Ov, sakerhet as Sa,
                                   sammansattning as Sam, verifiering as Vf)
from vc_assist_svc.harness import fallor as Fa         # noqa: E402
from vc_assist_svc.harness import kodfallor as Kf      # noqa: E402
from vc_assist_svc.harness import mattafakta as Mf     # noqa: E402

HARNESSKATALOG = os.path.join(_ROT, "svc", "vc_assist_svc", "harness")


# ---- fixturer ------------------------------------------------------------

@pytest.fixture(scope="module")
def korpus():
    return I.las_korpus()


@pytest.fixture(scope="module")
def forgranskare():
    """En delad förgranskare. API-indexet är det dyra och byggs en gång."""
    return Fg.Forgranskare()


def _matningsnummer_som_inte_finns():
    """Ett M-nummer som INTE ligger under docs/matningar/, hämtat ur disken.

    Numret stod som en litteral (`M-99`) fram till M-98, och det gjorde
    provets antagande beroende av vad andra agenter skrev i repot: när
    `M-99_differentialsvepet_mot_kompilatorn.md` skapades 2026-09-05 kl.
    08:06 blev båda proven nedan gröna av fel skäl — härkomsten gick
    plötsligt att slå upp, och den trasiga fixturen var inte längre trasig.

    Det är samma felklass som M-98 mäter i grindarna: ett värde som avgör en
    dom hämtas ur en litteral i stället för ur den storhet det påstår sig
    mäta. Numret räknas därför fram, och provet fäller så länge det finns
    NÅGOT ledigt nummer under 100.
    """
    katalog = os.path.join(_ROT, "docs", "matningar")
    tagna = set()
    for namn in os.listdir(katalog):
        if namn.endswith(".md"):
            tagna.add(namn.split("_")[0])
    for n in range(99, 9, -1):
        kod = "M-%02d" % n
        if kod not in tagna:
            return kod
    raise AssertionError(
        "alla M-nummer 10-99 ar tagna; provet behover ett ledigt nummer")


def _kopiera_korpus(tmp_path):
    mal = tmp_path / "instruktioner"
    shutil.copytree(I.KORPUSKATALOG, str(mal))
    return mal


def _skriv(katalog, filnamn, data):
    with open(os.path.join(str(katalog), filnamn), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _las(katalog, filnamn):
    with open(os.path.join(str(katalog), filnamn), encoding="utf-8") as f:
        return json.load(f)


def _problem(katalog):
    _block, problem = I.granska_korpus(str(katalog), _ROT)
    return problem


# ---- 1. korpusen ---------------------------------------------------------

def test_korpusen_laddar_och_ar_inte_tom(korpus):
    assert len(korpus.block) >= 5
    assert len(korpus.regler()) >= 30


def test_varje_regel_bar_en_harkomst_som_gar_att_sla_upp(korpus):
    """En regel utan härkomst är en åsikt. Uppslaget går mot disken."""
    uppslag = I.Harkomstuppslag(_ROT)
    for regel in korpus.regler():
        assert regel.harkomst, regel.id
        for post in regel.harkomst:
            assert uppslag.problem(post) is None, (regel.id, post)


def test_varje_tvingad_regel_namnger_en_mekanism_som_finns(korpus):
    for regel in korpus.tvingade():
        assert regel.tvingas_av in Mk.MEKANISMER, regel.id


def test_varje_mekanism_namns_av_minst_en_regel(korpus):
    """S3: ingen kod utan konsument. En mekanism som ingen regel lutar sig
    mot är antingen onödig eller odokumenterad, och båda är fel."""
    namnda = set(korpus.mekanismer())
    saknade = sorted(set(Mk.MEKANISMER) - namnda)
    assert not saknade, "mekanismer utan regel: %s" % ", ".join(saknade)


def test_regel_id_ar_unika_och_blockprioriteter_ar_unika(korpus):
    ider = [r.id for r in korpus.regler()]
    assert len(ider) == len(set(ider))
    prioriteter = [b.prioritet for b in korpus.block]
    assert len(prioriteter) == len(set(prioriteter))


def test_fingeravtrycket_andras_nar_en_regel_andras(korpus, tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    fore = I.las_korpus(str(katalog), _ROT).fingeravtryck()
    data = _las(katalog, "30_arlighet.json")
    data["regler"][0]["text"] = data["regler"][0]["text"] + " Och det gäller alltid."
    data["regler"][0]["version"] = 2
    _skriv(katalog, "30_arlighet.json", data)
    efter = I.las_korpus(str(katalog), _ROT).fingeravtryck()
    assert fore != efter
    assert fore == korpus.fingeravtryck()


# ---- 1b. trasiga fixturer för korpuslintern (S2) -------------------------

def test_trasig_korpus_saknad_harkomst_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "30_arlighet.json")
    data["regler"][0]["harkomst"] = ["docs/spec/finns_inte.md"]
    _skriv(katalog, "30_arlighet.json", data)
    problem = _problem(katalog)
    assert any("varken en fil" in p for p in problem), problem


def test_trasig_korpus_okand_matning_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    saknat = _matningsnummer_som_inte_finns()
    data = _las(katalog, "60_matta_fallor.json")
    data["regler"][0]["harkomst"] = [saknat]
    _skriv(katalog, "60_matta_fallor.json", data)
    assert any(saknat in p for p in _problem(katalog))


def test_trasig_korpus_okand_mekanism_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "40_sakerhetsgransen.json")
    data["regler"][0]["tvingas_av"] = "magi"
    _skriv(katalog, "40_sakerhetsgransen.json", data)
    assert any("magi" in p for p in _problem(katalog))


def test_trasig_korpus_regel_utan_mekanism_men_markt_block_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "40_sakerhetsgransen.json")
    data["regler"][0]["tvingas_av"] = None
    _skriv(katalog, "40_sakerhetsgransen.json", data)
    assert any("mekanismnamn" in p for p in _problem(katalog))


def test_trasig_korpus_for_kort_skal_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "10_arbetsordning.json")
    data["regler"][0]["skal"] = "viktigt"
    _skriv(katalog, "10_arbetsordning.json", data)
    assert any("asikt" in p for p in _problem(katalog))


def test_trasig_korpus_korsreferens_i_regeltext_falls(tmp_path):
    """En prompt kapas. En regel som säger "se ovan" kan bli meningslös."""
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "10_arbetsordning.json")
    data["regler"][0]["text"] = "Gör som det står i regeln se ovan."
    _skriv(katalog, "10_arbetsordning.json", data)
    assert any("korsreferensen" in p for p in _problem(katalog))


def test_trasig_korpus_delad_prioritet_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "10_arbetsordning.json")
    data["prioritet"] = _las(katalog, "20_verktygsbruk.json")["prioritet"]
    _skriv(katalog, "10_arbetsordning.json", data)
    assert any("kapordningen maste vara total" in p for p in _problem(katalog))


def test_trasig_korpus_filnamn_utan_id_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "10_arbetsordning.json")
    data["id"] = "nagot_annat"
    _skriv(katalog, "10_arbetsordning.json", data)
    assert any("stammer inte med filnamnet" in p for p in _problem(katalog))


def test_trasig_korpus_beskriver_fil_som_inte_finns_falls(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "00_systemroll.json")
    data["beskriver"] = ["svc/vc_assist_svc/harness/finns_inte.py"]
    _skriv(katalog, "00_systemroll.json", data)
    assert any("beskriver pekar" in p for p in _problem(katalog))


def test_las_korpus_kastar_med_hela_problemlistan(tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "10_arbetsordning.json")
    data["regler"][0]["skal"] = "x"
    data["regler"][1]["harkomst"] = [_matningsnummer_som_inte_finns()]
    _skriv(katalog, "10_arbetsordning.json", data)
    with pytest.raises(Fel.Instruktionsfel) as info:
        I.las_korpus(str(katalog), _ROT)
    assert len(info.value.problem) >= 2


# ---- 1c. diff ------------------------------------------------------------

def test_diff_anmarker_pa_andrad_text_utan_versionshojning(korpus, tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "20_verktygsbruk.json")
    data["regler"][0]["text"] = "Anropa bara verktyg ur listan du fått."
    _skriv(katalog, "20_verktygsbruk.json", data)
    efter = I.las_korpus(str(katalog), _ROT)
    diff = I.diffa(korpus, efter)
    assert not diff.orord
    assert any("utan att regelns version hojdes" in a for a in diff.anmarkningar)


def test_diff_utan_anmarkning_nar_versionen_hojs(korpus, tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "20_verktygsbruk.json")
    data["regler"][0]["text"] = "Anropa bara verktyg ur listan du fått."
    # Relativt och inte hårdkodat till 2: versionerna i korpusen på disk höjs
    # när en regel mekaniseras, och ett prov som skriver in ett fast tal
    # slutar mäta det det påstår sig mäta så fort korpusen rör sig (M-53).
    data["regler"][0]["version"] += 1
    data["version"] += 1
    _skriv(katalog, "20_verktygsbruk.json", data)
    diff = I.diffa(korpus, I.las_korpus(str(katalog), _ROT))
    assert diff.andringar
    assert not diff.anmarkningar


def test_diff_ser_borttagen_regel(korpus, tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "50_domankunskap_vc.json")
    borttagen = data["regler"].pop()["id"]
    data["version"] = 2
    _skriv(katalog, "50_domankunskap_vc.json", data)
    diff = I.diffa(korpus, I.las_korpus(str(katalog), _ROT))
    assert borttagen in diff.borttagna_regler


def test_diff_mot_sig_sjalv_ar_orord(korpus):
    diff = I.diffa(korpus, korpus)
    assert diff.orord
    assert diff.text() == "ingen skillnad"


def test_diffens_text_namner_varje_andring(korpus, tmp_path):
    katalog = _kopiera_korpus(tmp_path)
    data = _las(katalog, "20_verktygsbruk.json")
    data["regler"][0]["text"] = "Anropa bara verktyg ur listan du fått."
    _skriv(katalog, "20_verktygsbruk.json", data)
    text = I.diffa(korpus, I.las_korpus(str(katalog), _ROT)).text()
    assert "VRK-001" in text
    assert "ANMARKNING" in text


# ---- 2. sammansättningen -------------------------------------------------

def test_hela_korpusen_far_plats_i_standardbudgeten(korpus):
    """Talet i sammansattning.STANDARDBUDGET är satt över den här mätningen."""
    prompt = Sam.bygg_systemprompt(korpus)
    assert prompt.hel
    assert prompt.tecken <= Sam.STANDARDBUDGET
    assert not prompt.kapade_regler


def test_prompten_bar_varje_regels_id_och_text(korpus):
    prompt = Sam.bygg_systemprompt(korpus)
    for regel in korpus.regler():
        assert regel.id in prompt.text
        assert regel.text in prompt.text


def test_kapningen_tar_lagsta_prioriteten_forst(korpus):
    prompt = Sam.bygg_systemprompt(korpus)
    trang = Sam.bygg_systemprompt(korpus, prompt.tecken - 400)
    assert trang.kapade_regler
    lagst = max(b.prioritet for b in korpus.block)
    forst_kapad = korpus.regel_med_id(trang.kapade_regler[0])
    assert korpus.block_med_id(forst_kapad.block).prioritet == lagst


def test_kapningen_tar_sista_regeln_i_blocket_forst(korpus):
    prompt = Sam.bygg_systemprompt(korpus)
    trang = Sam.bygg_systemprompt(korpus, prompt.tecken - 200)
    forst_kapad = korpus.regel_med_id(trang.kapade_regler[0])
    block = korpus.block_med_id(forst_kapad.block)
    assert block.regler[-1].id == forst_kapad.id


def test_de_okapbara_blocken_star_kvar_aven_nar_budgeten_ar_minimal(korpus):
    minsta = Sam.bygg_systemprompt(korpus, 3000)
    for block_id in Sam.OKAPBARA:
        block = korpus.block_med_id(block_id)
        for regel in block.regler:
            assert regel.id in minsta.med_regler, (block_id, regel.id)


def test_for_liten_budget_kastar_i_stallet_for_att_tysta_sakerheten(korpus):
    with pytest.raises(Fel.Budgetfel) as info:
        Sam.bygg_systemprompt(korpus, 500)
    assert "sakerhetsgransen" in str(info.value)


def test_kapgolvet_och_korpusens_flaggor_stammer(korpus):
    assert Sam.granska_golv(korpus) == []


def test_kapgolvet_faller_nar_datan_lovar_mer_an_koden_haller(korpus):
    """Farliga riktningen: datan säger okapbar, koden skyddar inte blocket."""
    block = list(korpus.block)
    kapbart = next(b for b in block if b.id not in Sam.OKAPBARA)
    ljugande = I.Block(id=kapbart.id, titel=kapbart.titel,
                       version=kapbart.version, prioritet=kapbart.prioritet,
                       kapbar=False, prioritet_skal=kapbart.prioritet_skal,
                       beskriver=kapbart.beskriver, regler=kapbart.regler,
                       fil=kapbart.fil)
    trasig = I.Korpus([ljugande if b.id == kapbart.id else b for b in block],
                      korpus.katalog)
    assert Sam.granska_golv(trasig)
    with pytest.raises(Fel.Budgetfel):
        Sam.bygg_systemprompt(trasig)


def test_tokentak_raknas_om_till_teckenbudget():
    """ANTAGET, inte mätt. Talet är valt lågt: en för liten budget kapar i
    onödan (ofarligt), en för stor skickar en prompt som inte får plats."""
    assert Sam.budget_ur_tokentak(4000) == int(4000 * Sam.TECKEN_PER_TOKEN)
    with pytest.raises(Fel.Budgetfel):
        Sam.budget_ur_tokentak(0)


def test_kapade_regler_syns_i_sammanfattningen(korpus):
    prompt = Sam.bygg_systemprompt(korpus)
    trang = Sam.bygg_systemprompt(korpus, prompt.tecken - 400)
    assert "kapade" in trang.sammanfattning()
    for regel_id in trang.kapade_regler:
        assert regel_id not in trang.med_regler


# ---- 3. modelloberoendet -------------------------------------------------

def test_ingen_leverantor_namns_utanfor_oversattningen():
    """Modelloberoende, mekaniskt prövat. Ingen leverantör får låsas fast."""
    namn = ("openai", "anthropic", "gemini", "claude", "gpt", "google",
            "mistral", "llama")
    for filnamn in sorted(os.listdir(HARNESSKATALOG)):
        if not filnamn.endswith(".py") or filnamn == "oversattning.py":
            continue
        with open(os.path.join(HARNESSKATALOG, filnamn), encoding="utf-8") as f:
            text = f.read().lower()
        for leverantor in namn:
            assert leverantor not in text, (filnamn, leverantor)


def test_verktygsschemat_oversatts_till_alla_tre_formerna():
    verktyg = [V.REGISTER["get_transform"], V.REGISTER["connect"]]
    oppen = Ov.till_openai(verktyg)
    assert oppen[0]["function"]["name"] == "get_transform"
    antropisk = Ov.till_anthropic(verktyg)
    assert antropisk[0]["input_schema"]["type"] == "object"
    gemini = Ov.till_gemini(verktyg)
    deklarationer = gemini[0]["function_declarations"]
    assert [d["name"] for d in deklarationer] == ["get_transform", "connect"]
    # Geminis schemadel tar inte emot additionalProperties. Spärren mot ett
    # uppfunnet argument ligger då hos oss, inte hos leverantören.
    assert "additionalProperties" not in json.dumps(deklarationer)
    assert oppen[0]["function"]["parameters"]["additionalProperties"] is False


def test_alla_tre_svarsformerna_ger_samma_modellsvar():
    argument = {"component": "IRB1200"}
    svar = {
        "openai": {"choices": [{"message": {
            "content": "läser", "tool_calls": [
                {"id": "1", "function": {"name": "get_transform",
                                         "arguments": json.dumps(argument)}}]}}]},
        "anthropic": {"content": [{"type": "text", "text": "läser"},
                                  {"type": "tool_use", "id": "1",
                                   "name": "get_transform", "input": argument}]},
        "gemini": {"candidates": [{"content": {"parts": [
            {"text": "läser"},
            {"functionCall": {"name": "get_transform", "args": argument}}]}}]},
    }
    for leverantor, rad in svar.items():
        _ut, in_ = Ov.oversattare(leverantor)
        modellsvar = in_(rad)
        assert modellsvar.text == "läser"
        assert len(modellsvar.anrop) == 1
        assert modellsvar.anrop[0].namn == "get_transform"
        assert modellsvar.anrop[0].argument == argument
        assert modellsvar.leverantor == leverantor


def test_okand_leverantor_och_trasigt_svar_kastar():
    with pytest.raises(Fel.Modellfel):
        Ov.oversattare("hemmasnickrad")
    with pytest.raises(Fel.Modellfel):
        Ov.fran_openai({"nagot_annat": 1})
    with pytest.raises(Fel.Modellfel):
        Ov.fran_openai({"choices": [{"message": {"tool_calls": [
            {"id": "1", "function": {"name": "x", "arguments": "{trasig"}}]}}]})


def test_attrappmodellen_ser_systemprompten_och_verktygen(korpus, forgranskare):
    modell = Mo.AttrappModell([Mo.sag("Layouten innehaller 2 komponenter.")])
    harness = L.Harness(modell=modell, kanal=Kn.Attrappkanal(), korpus=korpus,
                        forgranskare=forgranskare)
    harness.kor("Lista komponenterna.")
    assert "SAK-001" in modell.sedda_systemprompter[0]
    assert "get_transform" in modell.sedda_verktygsnamn[0]


def test_slut_manus_blir_tystnad_och_inte_ett_pahittat_svar(korpus,
                                                            forgranskare):
    modell = Mo.AttrappModell([])
    harness = L.Harness(modell=modell, kanal=Kn.Attrappkanal(), korpus=korpus,
                        forgranskare=forgranskare)
    protokoll = harness.kor("Lista komponenterna.")
    assert protokoll.utfall == "STOPP:tystnad"
    assert not protokoll.klar


# ---- 4. förgranskningen anropar de mekanismer som redan finns ------------

_EXEMPELVARDEN = {
    "component": "IRB1200", "other_component": "Transportor",
    "interface": "BaseInterface", "other_interface": "OutFeed",
    "node": "Flange", "name": "IRB1200", "property": "Payload", "value": "5",
    "uri": "bank://robot/abb_irb_1200_5_0900", "position": [0.0, 0.0, 0.0],
}


def _varde_for_schema(schema, namn=None):
    """Ett minimalt giltigt varde for ett schema, rekursivt.

    Rekursionen ar inte pyntning. Den forsta versionen gav [0.0, 0.0, 0.0] for
    VARJE array oavsett items, vilket rackte sa lange alla arrayer var
    koordinater. Nar robotdomanen kopplades in fanns plotsligt en array av
    OBJEKT (move_targets.targets), och generatorn matade den med flyttal - sa
    provet fallde pa sin egen fixtur och inte pa produkten.

    Ett prov som bygger sin indata ur schemat maste folja schemat hela vagen
    ned, annars vaxer det ifran registret det skulle folja med.
    """
    if schema is None:
        return _EXEMPELVARDEN.get(namn, "X")
    if "enum" in schema:
        return schema["enum"][0]
    typ = schema.get("type")
    if typ in ("number", "integer"):
        return 1
    if typ == "boolean":
        return True
    if typ == "array":
        if namn is not None and namn in _EXEMPELVARDEN:
            return _EXEMPELVARDEN[namn]
        poster = schema.get("items")
        antal = max(int(schema.get("minItems", 3) or 3), 1)
        if poster is None:
            return [0.0, 0.0, 0.0]
        return [_varde_for_schema(poster) for _ in range(antal)]
    if typ == "object":
        ut = {}
        egenskaper = schema.get("properties", {})
        # Samma regel som pa toppniva i _argument_for: required, forsta ur
        # varje x-minst-en-av, och hela varje x-tillsammans. Utan den saknar
        # ett nastlat objekt sina antingen-eller-falt och provet faller pa sin
        # egen fixtur.
        nycklar = list(schema.get("required", []))
        for grupp in schema.get("x-minst-en-av", []):
            nycklar.append(grupp[0])
        for grupp in schema.get("x-tillsammans", []):
            nycklar.extend(grupp)
        for nyckel in nycklar:
            if nyckel in ut:
                continue
            ut[nyckel] = _varde_for_schema(egenskaper.get(nyckel), nyckel)
        return ut
    return _EXEMPELVARDEN.get(namn, "X")


def _argument_for(verktyg):
    """Ett minimalt giltigt anrop, byggt ur verktygets EGET schema.

    Byggs ur schemat och inte ur en lista, sa att provet foljer med nar
    registret vaxer. Det gjorde det mitt under den har cellen: 21 verktyg
    blev 77, och sedan 119 nar robotdomanen kopplades in.
    """
    krav = list(verktyg.parameters.get("required", []))
    for grupp in verktyg.parameters.get("x-minst-en-av", []):
        krav.append(grupp[0])
    for grupp in verktyg.parameters.get("x-tillsammans", []):
        krav.extend(grupp)
    argument = {}
    for namn in krav:
        schema = verktyg.parameters["properties"].get(namn)
        if schema is None:
            continue
        argument[namn] = _varde_for_schema(schema, namn)
    return argument


def test_alla_verktygsmallar_passerar_api_grinden(forgranskare):
    """MÄTNINGEN bakom forgranskning.BRYGGANS_GLOBALER, omräknad varje gång.

    Bryggan lägger _s i exec-globalerna, så mallarna anropar en funktion som
    inte står i deras egen kod. Utan den raden blir mallarna obestämbara på
    sitt eget hjälpanrop, och då skulle grinden avvisa varje verktygsanrop i
    hela tjänsten. Mätt 2026-09-04: 55 av 66 kodgenererande verktyg utan
    raden, 0 av 66 med den. Talen räknas om här i stället för att litas på,
    eftersom registret växer.
    """
    utan, med, kollade = 0, 0, 0
    for namn, verktyg in sorted(V.REGISTER.items()):
        if verktyg.mode != "codegen":
            continue
        argument = V.validera_argument(verktyg, _argument_for(verktyg))
        kod = V.CODE_GEN_HANDLERS[namn](argument)
        kollade += 1
        if not forgranskare.validator.granska(kod).godkand:
            utan += 1
        if not forgranskare.validator.granska(
                Fg.BRYGGANS_GLOBALER + kod).godkand:
            med += 1
    assert kollade >= 20
    assert med == 0, "%d mallar avvisas av api-grinden" % med
    assert utan > 0, "utan _s-raden ska mallarna vara obestambara"


def test_varje_uriargument_ar_klassat_som_kalla_mal_eller_fraga():
    """Ett nytt verktyg med en URI ska tvinga fram ett beslut, inte ärva ett.

    Faller det här provet: lägg det nya (verktyg, argument)-paret i
    forgranskning.URIMAL om URI:n är något som ska SKRIVAS, i URIFRAGOR om
    den är en fråga till katalogindexet, och i URIKALLOR om den är något som
    måste finnas. Ett oklassat par behandlas som källa, alltså fail-closed.
    """
    klassade = Fg.URIMAL | Fg.URIFRAGOR | Fg.URIKALLOR
    oklassade = sorted(set(Fg.uriargument(V.REGISTER)) - klassade)
    assert not oklassade, (
        "oklassade uri-argument: %s" % ", ".join("%s.%s" % p for p in oklassade))


def test_grindordningen_ar_den_dokumenterade():
    assert Fg.GRINDAR[0] == "tomt_anrop"
    assert Fg.GRINDAR[1] == "sakerhet"      # ovillkorlig, före allt annat
    # skrivgrind är sista grinden på ett ANROP. Efter den kommer M-53:s
    # kodfällsgrindar, som bara dömer modellens egna kodblock i slutsvaret.
    svarsgrindar = Kf.GRINDAR + (Mf.GRIND,)
    kedjan = Fg.GRINDAR[:len(Fg.GRINDAR) - len(svarsgrindar)]
    assert kedjan[-1] == "skrivgrind"
    assert Fg.GRINDAR[len(kedjan):] == svarsgrindar


def test_sakerhetsgrinden_domer_fore_registret(forgranskare):
    """I15 får inte kunna maskeras av att verktyget inte finns."""
    dom = forgranskare.granska_anrop(
        Mo.Verktygsanrop(namn="finns_inte_alls",
                         argument={"signal": "Nodstopp_kvittering"}))
    assert dom.avvisning.grind == "sakerhet"


def test_lasning_av_skyddad_tagg_ar_tillaten_men_skrivning_aldrig():
    grind = Sa.Sakerhetsgrind(signalkarta=Fa.SIGNALKARTA)
    argument = {"component": "Press", "property": "SKYDDSKRETS_OK"}
    assert not grind.granska_anrop("read", argument).nekas
    assert grind.granska_anrop("write", argument).nekas
    # Okänd verkan räknas som skrivning. Fail-closed.
    assert grind.granska_anrop(None, argument).nekas


def test_st_grinden_anropar_st_validatorn_och_domer_inte_om():
    grind = Sa.Sakerhetsgrind(signalkarta=Fa.SIGNALKARTA)
    dom = grind.granska_st(Fa.ST_SKRIVER_SKYDDAD)
    assert dom.nekas
    assert "SKYDDSKRETS_OK" in dom.text()
    assert not grind.granska_st(Fa.ST_LASER_SKYDDAD).nekas


def test_st_utan_signalkarta_ar_inte_godkant():
    """Fail-closed: utan karta vet grinden inte vad som är skyddat."""
    assert Sa.Sakerhetsgrind(signalkarta=None).granska_st(
        Fa.ST_LASER_SKYDDAD).nekas


def test_skrivande_kod_i_ett_lasande_verktyg_falls(forgranskare):
    """Trasig fixtur för skrivgrindslagret: en kodgenerator som ljuger."""
    def trasig_kodgen(argument):
        return ("app = getApplication()\n"
                "comp = app.findComponent(_s('IRB1200'))\n"
                "comp.Name = _s('nytt')\n")

    egen = Fg.Forgranskare(validator=forgranskare.validator,
                           sakerhetsgrind=forgranskare.sakerhet,
                           kodgen=dict(V.CODE_GEN_HANDLERS,
                                       get_transform=trasig_kodgen))
    dom = egen.granska_anrop(Mo.Verktygsanrop(namn="get_transform",
                                              argument={"component": "IRB1200"}))
    assert dom.avvisning.grind == "skrivgrind"


def test_avstangt_verktyg_avvisas_med_ytans_namn(forgranskare):
    urval = V.urval_ur_rapport({"ytor": {}}, V.REGISTER)
    egen = Fg.Forgranskare(urval=urval, validator=forgranskare.validator,
                           sakerhetsgrind=forgranskare.sakerhet)
    dom = egen.granska_anrop(Mo.Verktygsanrop(namn="get_transform",
                                              argument={"component": "IRB1200"}))
    assert dom.avvisning.grind == "avstangt"


def test_pumpvarning_fore_korning_pa_save_layout(forgranskare):
    """M-13: app.save() dödar bryggan. Varningen måste komma FÖRE körningen."""
    dom = forgranskare.granska_anrop(
        Mo.Verktygsanrop(namn="save_layout",
                         argument={"uri": "file:///tmp/x.vcmx"}),
        uppgiftstext="Spara till file:///tmp/x.vcmx")
    assert dom.slapps
    assert any("M-13" in v for v in dom.varningar)


def test_kodblock_utan_sprakmarkning_som_ar_prosa_domes_inte(forgranskare):
    text = "Sa har ser svaret ut:\n```\nIRB1200 star vid transportoren\n```"
    assert forgranskare.granska_svarstext(text).slapps


def test_kodblock_utan_sprakmarkning_som_ar_kod_domes(forgranskare):
    text = ("Kor den har:\n```\napp = getApplication()\n"
            "comp = app.findComponent('IRB1200')\ncomp.Name = 'nytt'\n```")
    dom = forgranskare.granska_svarstext(text)
    assert not dom.slapps
    assert dom.avvisning.grind == "skrivgrind"


def test_oavslutat_kodblock_raknas_med():
    block = Fg.kodblock("```python\nimport os\n")
    assert block == [("python", "import os")]


# ---- 5. ärlighetsgrinden -------------------------------------------------

def _utfall(ok, verktyg="get_transform", fel=""):
    return Kn.Anropsutfall(verktyg=verktyg, argument={}, ok=ok, fel=fel)


def test_arlighet_faller_pastad_framgang_efter_fallet_verktyg():
    anmarkningar = A.granska("Klart! Roboten ar nu kopplad.",
                             [_utfall(False, fel="E_EXEC")])
    assert anmarkningar[0].kod == "arlighet_sista_verktyget"


def test_arlighet_slapper_ett_arligt_svar_om_samma_fel():
    assert not A.granska(
        "get_transform foll med E_EXEC, sa jag kunde inte lasa lagen.",
        [_utfall(False, fel="E_EXEC")])


def test_arlighet_faller_onamnt_fel_mitt_i_turen():
    anmarkningar = A.granska("Jag laste layouten och allt ser bra ut.",
                             [_utfall(False, fel="E_EXEC"), _utfall(True)])
    assert [a.kod for a in anmarkningar] == ["arlighet_onamnt_fel"]


def test_arlighet_ror_inte_en_tur_utan_verktygsfel():
    assert not A.granska("Klart!", [_utfall(True)])


def test_arlighet_anklagar_inte_for_pastad_framgang_utan_markor():
    """En grind som anklagar i onödan slutar bli läst.

    Meningen nämner inget fel, så regel två (arlighet_onamnt_fel) fäller den
    med rätta. Det som INTE får hända är att den anklagas för att ha påstått
    en framgång den aldrig påstod.
    """
    koder = [a.kod for a in A.granska("Jag tittade lite pa layouten.",
                                      [_utfall(False, fel="E_EXEC")])]
    assert koder == ["arlighet_onamnt_fel"]


# ---- 6. verify-contract --------------------------------------------------

def _grund(**kvarg):
    grund = Vf.Grund(uppgiftstext=kvarg.get("uppgift", ""),
                     verktygsnamn=("get_transform",))
    if "resultat" in kvarg:
        grund.lagg_resultat("get_transform", kvarg.get("argument", {}),
                            kvarg["resultat"])
    return grund


def test_verify_slapper_ett_tal_som_star_i_verktygssvaret():
    grund = _grund(resultat={"position": [812.0, 0.0, 0.0]})
    assert not Vf.granska("Avstandet ar 812 mm.", grund)


def test_verify_slapper_en_korrekt_avrundning():
    grund = _grund(resultat={"position": [2496.0, 0.0, 0.0]})
    assert not Vf.granska("Avstandet ar 2,5 m.", grund)


def test_verify_faller_en_avrundning_som_ingen_matning_stodjer():
    grund = _grund(resultat={"position": [2496.0, 0.0, 0.0]})
    avvikelser = Vf.granska("Avstandet ar 2,4 m.", grund)
    assert [a.sort for a in avvikelser] == ["tal"]


def test_verify_raknar_om_enheter_till_millimeter():
    grund = _grund(resultat={"position": [2500.0, 0.0, 0.0]})
    assert not Vf.granska("Avstandet ar 2,5 m.", grund)
    assert Vf.granska("Avstandet ar 2,5 mm.", grund)


def test_verify_ror_inte_ett_forslag():
    """En plan är inget påstående om världen."""
    grund = _grund(resultat={"position": [812.0, 0.0, 0.0]})
    assert not Vf.granska("Jag kan flytta roboten 500 mm om du vill.", grund)


def test_verify_faller_ett_pahittat_apinamn(forgranskare):
    grund = Vf.Grund(api=forgranskare.validator.index)
    avvikelser = Vf.granska("Lagen star i comp.WorldPosMatrix.", grund)
    assert [a.sort for a in avvikelser] == ["namn"]
    assert "WorldPositionMatrix" in avvikelser[0].skal


def test_verify_slapper_ett_riktigt_apinamn(forgranskare):
    grund = Vf.Grund(api=forgranskare.validator.index)
    assert not Vf.granska("Lagen star i comp.WorldPositionMatrix.", grund)


def test_verify_slapper_argumenten_till_ett_lyckat_anrop():
    """Bad modellen om en flytt på 500 mm och anropet gick igenom, så är
    500 mm ett tal den har rätt att skriva."""
    grund = _grund(argument={"position": [500.0, 0.0, 0.0]},
                   resultat={"set": True})
    assert not Vf.granska("Jag flyttade roboten 500 mm i x-led.", grund)


def test_verify_tar_inte_katalogens_tal_som_matning(forgranskare):
    """Ett namn ur katalogen finns. Ett TAL ur katalogen är ingen mätning."""
    grund = Vf.Grund(api=forgranskare.validator.index,
                     katalogindex=forgranskare.katalogindex)
    assert Vf.granska("Avstandet ar 0,45 m.", grund)
    assert not Vf.granska("Jag valde `ABB IRB 1200-5/0.9` ur katalogen.", grund)


def test_omskrivningskravet_pekar_ut_vad_som_inte_stammer():
    grund = _grund(resultat={"position": [812.0, 0.0, 0.0]})
    krav = Vf.omskrivningskrav(Vf.granska("Avstandet ar 450 mm.", grund))
    assert "450" in krav and "812" in krav


# ---- 7. ögongrinden ------------------------------------------------------

def test_oga_faller_dom_utan_korning():
    assert Og.granska("Ogat sager PASS.")[0].kod == "oga_utan_korning"


def test_oga_faller_mildrad_dom():
    assert Og.granska("Ogat gav i praktiken PASS.",
                      Fa.OGA_FAIL)[0].kod == "oga_mildrad"


def test_oga_slapper_en_korrekt_citerad_dom():
    assert not Og.granska("Ogat sa FAIL: detaljen hamnade utanfor malet.",
                          Fa.OGA_FAIL)


def test_oga_raknar_inconclusive_som_inte_godkant():
    assert Og.granska("Ogat sag inga fel, sa cellen ar godkand.",
                      Fa.OGA_OKLAR)[0].kod == "oga_mildrad"


def test_avhuggen_ogonrapport_ar_aldrig_ett_godkannande():
    rapport, skal = Og.las_dom(Fa.OGA_AVHUGGEN)
    assert rapport is None
    assert "truncated" in skal


def test_guld_kraver_guldgrindens_beslut():
    assert Og.granska("Cellen ar L1-guld.", Fa.OGA_PASS)[0].kod == "guld_utan_grind"
    assert not Og.granska("Cellen ar L1-guld.", Fa.OGA_PASS, Fa.GULD_JA)


# ---- 8. loopen -----------------------------------------------------------

def test_taken_ar_de_arvda_talen():
    """20_arv.md: tio rundor, stopp efter sex raka misslyckanden."""
    assert (L.MAX_RUNDOR, L.MAX_RAKA_MISSLYCKANDEN) == (10, 6)


def test_ett_verktygsfel_ensamt_avgor_inte_turen(korpus, forgranskare):
    modell = Mo.AttrappModell([
        Mo.anropa("get_transform", {"component": "IRB1200"}),
        Mo.sag("get_transform foll pa timeout, sa jag kunde inte mata nagot.")])
    kanal = Kn.Attrappkanal({"get_transform": [Kn.Faller("E_TIMEOUT")]})
    protokoll = L.Harness(modell=modell, kanal=kanal, korpus=korpus,
                          forgranskare=forgranskare).kor("Mat avstandet.")
    assert protokoll.utfall == "SLAPPT"
    assert protokoll.klar


def test_en_stoppad_tur_ar_aldrig_klar(korpus, forgranskare):
    modell = Mo.AttrappModell([Mo.Modellsvar(text="", anrop=())])
    protokoll = L.Harness(modell=modell, kanal=Kn.Attrappkanal(),
                          korpus=korpus,
                          forgranskare=forgranskare).kor("Gor nagot.")
    assert not protokoll.klar
    assert protokoll.slutsvar == ""


def test_omskrivning_som_inte_rattas_haller_inne_svaret(korpus, forgranskare):
    """Harnessen skriver aldrig ett svar åt modellen."""
    ljug = Mo.sag("Klart! Allt ar kopplat.")
    modell = Mo.AttrappModell([
        # Lasningen forst ar inget pynt: sedan M-53 avvisar turordningens
        # olast_scen ett scenandrande anrop mot en komponent som ingen
        # lasning i turen har returnerat, och da provas fel grind har.
        Mo.anropa("list_components"),
        Mo.anropa("connect", {"component": "IRB1200",
                              "interface": "BaseInterface",
                              "other_component": "Transportor",
                              "other_interface": "OutFeed"}),
        ljug, ljug, ljug])
    kanal = Kn.Attrappkanal({"list_components": [Fa.LISTSVAR],
                             "connect": [Kn.Faller("E_EXEC: VC nekade")]})
    protokoll = L.Harness(modell=modell, kanal=kanal, korpus=korpus,
                          forgranskare=forgranskare).kor("Koppla ihop dem.")
    assert protokoll.utfall.startswith("OMSKRIVNING:")
    assert not protokoll.klar
    assert protokoll.slutsvar == ""
    assert any(h.kod == "omskrivning_misslyckades" for h in protokoll.handelser)


def test_en_rattad_omskrivning_slapps_igenom(korpus, forgranskare):
    modell = Mo.AttrappModell([
        Mo.anropa("list_components"),
        Mo.anropa("connect", {"component": "IRB1200",
                              "interface": "BaseInterface",
                              "other_component": "Transportor",
                              "other_interface": "OutFeed"}),
        Mo.sag("Klart! Allt ar kopplat."),
        Mo.sag("connect foll: VC nekade kopplingen. Ingenting ar kopplat.")])
    kanal = Kn.Attrappkanal({"list_components": [Fa.LISTSVAR],
                             "connect": [Kn.Faller("E_EXEC: VC nekade")]})
    protokoll = L.Harness(modell=modell, kanal=kanal, korpus=korpus,
                          forgranskare=forgranskare).kor("Koppla ihop dem.")
    assert protokoll.klar
    assert protokoll.utfall.startswith("OMSKRIVNING:")
    assert "VC nekade" in protokoll.slutsvar


def test_omskrivningskravet_citerar_regeln_som_brots(korpus, forgranskare):
    """En modell som får veta att den bröt ARL-001 utan att få läsa ARL-001
    rättar gissningsvis — och den kapade prompten kan sakna regeln."""
    modell = Mo.AttrappModell([
        Mo.anropa("connect", {"component": "IRB1200",
                              "interface": "BaseInterface",
                              "other_component": "Transportor",
                              "other_interface": "OutFeed"}),
        Mo.sag("Klart! Allt ar kopplat."),
        Mo.sag("connect foll: VC nekade. Ingenting ar kopplat.")])
    kanal = Kn.Attrappkanal({"connect": [Kn.Faller("E_EXEC: VC nekade")]})
    L.Harness(modell=modell, kanal=kanal, korpus=korpus,
              forgranskare=forgranskare).kor("Koppla ihop dem.")
    grindtext = "\n".join(m.text for m in modell.sedda_historiker[-1]
                           if m.roll == "grind")
    assert "ARL-001" in grindtext
    assert korpus.regel_med_id("ARL-001").text in grindtext


def test_protokollet_bar_korpusens_fingeravtryck(korpus, forgranskare):
    modell = Mo.AttrappModell([Mo.sag("Ingenting att gora.")])
    protokoll = L.Harness(modell=modell, kanal=Kn.Attrappkanal(),
                          korpus=korpus,
                          forgranskare=forgranskare).kor("Vila.")
    assert protokoll.korpus_fingeravtryck == korpus.fingeravtryck()
    assert protokoll.systemprompt_tecken > 0


def test_avslaget_gar_tillbaka_till_modellen_i_klartext(korpus, forgranskare):
    modell = Mo.AttrappModell([Mo.anropa("move_robot", {"x": 1}),
                               Mo.sag("Jag kunde inte flytta roboten.")])
    L.Harness(modell=modell, kanal=Kn.Attrappkanal(), korpus=korpus,
              forgranskare=forgranskare).kor("Flytta roboten.")
    grindtext = "\n".join(m.text for m in modell.sedda_historiker[-1]
                          if m.roll == "grind")
    assert "Anropet kordes ALDRIG" in grindtext
    assert "move_robot" in grindtext


# ---- 9. kanalen ----------------------------------------------------------

def test_utforarkanalen_gor_ett_verktygsfel_till_ett_utfall():
    class Fallande(object):
        def utfor(self, namn, argument):
            raise V.OkantVerktyg("finns inte")

    utfall = Kn.Utforarkanal(Fallande()).utfor("x", {})
    assert not utfall.ok and "finns inte" in utfall.fel


def test_utforarkanalen_later_ett_natverksfel_bli_ett_kanalfel():
    """Ett fel modellen inte kan rätta får inte se ut som ett verktygsfel."""
    class Trasig(object):
        def utfor(self, namn, argument):
            raise OSError("connection refused")

    with pytest.raises(Fel.Kanalfel):
        Kn.Utforarkanal(Trasig()).utfor("x", {})


def test_attrappkanalen_svarar_med_fel_nar_manuset_ar_slut():
    """Ett tomt resultat hade sett ut som en lyckad körning utan mätvärden."""
    utfall = Kn.Attrappkanal({}).utfor("get_transform", {})
    assert not utfall.ok


# ---- 10. skuldkontroller -------------------------------------------------

def test_harnessen_bar_ingen_bar_todo():
    """S8: ingen TODO utan datum och ägare. Formen är TODO(datum, fas)."""
    for filnamn in sorted(os.listdir(HARNESSKATALOG)):
        if not filnamn.endswith(".py"):
            continue
        with open(os.path.join(HARNESSKATALOG, filnamn), encoding="utf-8") as f:
            text = f.read()
        for markor in ("TODO", "FIXME", "XXX"):
            if markor in text:
                assert "%s(" % markor in text, (filnamn, markor)


def test_harnessens_kallkod_bar_inga_homoglyfer():
    """En kyrillisk 'а' i en identifierare eller ett ord är osynlig i diffen.

    Fixturen som satte provet: ett 'а' (U+0430) smög in i fel.py under
    skrivningen och gick inte att se med ögat.
    """
    tillatna = set("åäöÅÄÖéÉüÜ–—°")
    for filnamn in sorted(os.listdir(HARNESSKATALOG)):
        if not filnamn.endswith(".py"):
            continue
        stig = os.path.join(HARNESSKATALOG, filnamn)
        with open(stig, encoding="utf-8") as f:
            for radnummer, rad in enumerate(f, 1):
                for tecken in rad:
                    assert ord(tecken) < 128 or tecken in tillatna, (
                        filnamn, radnummer, tecken, hex(ord(tecken)))


def test_varje_harnessmodul_gar_att_parsa_och_har_docstring():
    for filnamn in sorted(os.listdir(HARNESSKATALOG)):
        if not filnamn.endswith(".py"):
            continue
        with open(os.path.join(HARNESSKATALOG, filnamn), encoding="utf-8") as f:
            trad = ast.parse(f.read(), filename=filnamn)
        assert ast.get_docstring(trad), filnamn


def test_harnessen_oppnar_ingen_socket():
    """Vägen ut går genom kanal.py, som får en färdig utförare."""
    for filnamn in sorted(os.listdir(HARNESSKATALOG)):
        if not filnamn.endswith(".py"):
            continue
        with open(os.path.join(HARNESSKATALOG, filnamn), encoding="utf-8") as f:
            text = f.read()
        assert "import socket" not in text, filnamn
        assert "urllib" not in text, filnamn
        assert "requests" not in text, filnamn


def test_skrivgrinden_ar_bryggans_egen_och_ingen_kopia():
    """Harnessen bygger ingen andra validering: den anropar den som finns."""
    with open(os.path.join(HARNESSKATALOG, "forgranskning.py"),
              encoding="utf-8") as f:
        text = f.read()
    assert "import skrivgrind" in text
    assert skrivgrind.granska("comp.Name = 'x'").skriver
