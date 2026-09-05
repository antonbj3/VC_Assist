# -*- coding: utf-8 -*-
"""Ett verktygssvar som inte far plats - och de tre former det kan ljuga i.

FAS 22, den farligaste av de tre trasiga fallen: ETT KAPAT SVAR SOM SER HELT UT.

Felet ar redan gjort en gang i det har repot. `slaupp.py` skivade JSON-strangen
pa TECKEN och gav utdata som var lasbar for ett oga och oparsbar for allt
annat; provet som star kvar heter `test_slaupp.py::test_kapning_ger_giltig_json`
och skalet star i `komponentdatablad.py` ("Kapa pa ANTAL POSTER, aldrig mitt i
en struktur"). Den formen skriker atminstone. Den TYSTA formen - kapa och sedan
laga sluttecknen sa att strangen parsar igen - ar samma fel utan larmet, och
det ar den formen de tre fixturerna nedan bevisar att grinden faller.

  A  halva listan borta, `antal` OFORANDRAT, ingen `avkortad`  -> K2 ensam
  B  klippt pa tecken, oparsbar                                -> K1 ensam
  C  halva listan borta, `antal` RATTAT, ingen `avkortad`      -> K2 mot ravaran

C ar den tystaste: svaret ar internt konsistent. Bara en jamforelse med
ravaran fanger den, och det ar darfor lagret ALDRIG far kapa nagon annanstans
an i `kapning.kapa()`, dar ravaran finns kvar.

Korpusen ar riktig: 190 verktygssvar ur repots egna handlare.
"""
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), os.path.join(_ROT, "tests", "protocol",
                                                   "stod")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fas22_fixturer as FX                                    # noqa: E402
from vc_assist_svc import verktyg as V                         # noqa: E402
from vc_assist_svc.llm import kapning as K                     # noqa: E402
from vc_assist_svc.llm.fel import Kapfel                       # noqa: E402


@pytest.fixture(scope="module")
def korpus():
    par = FX.korpus()
    assert len(par) > 100, "korpusen ar bara %d svar" % len(par)
    return par


@pytest.fixture(scope="module")
def sjalvkontrollerbart(korpus):
    """Ett riktigt svar som bar SIN EGEN rakning (`antal` + en lista)."""
    for svar, schema in korpus:
        listor = [n for n in K.listfalt(schema)
                  if isinstance((svar.resultat or {}).get(n), list)]
        if (len(listor) == 1 and isinstance(svar.resultat, dict)
                and "antal" in svar.resultat
                and len(svar.resultat[listor[0]]) > 4):
            return svar, schema
    pytest.fail("inget sjalvkontrollerbart svar i korpusen")


# ---- de tre farliga formerna -------------------------------------------

def test_A_ett_kapat_svar_som_ser_helt_ut_falls(sjalvkontrollerbart):
    """TRASIG FIXTUR. Halva listan borta, svarets egen rakning kvar."""
    svar, schema = sjalvkontrollerbart
    trasigt = FX.ser_helt_ut(svar, schema)
    # Det parsar felfritt. Det ar hela poangen: felet syns inte pa formen.
    json.loads(trasigt.innehall_text())
    koder = [a.kod for a in K.granska(trasigt, schema)]
    assert K.K2_SER_HELT_UT in koder, koder


def test_B_ett_svar_klippt_pa_tecken_falls(sjalvkontrollerbart):
    """TRASIG FIXTUR. Formen slaupp.py en gang levererade."""
    svar, schema = sjalvkontrollerbart
    trasigt = FX.parsar_inte(svar)
    koder = [a.kod for a in K.granska(trasigt, schema)]
    assert koder == [K.K1_OGILTIG_JSON], koder


def test_C_ett_internt_konsistent_men_kort_svar_falls_mot_ravaran(
        sjalvkontrollerbart):
    """TRASIG FIXTUR. Den tystaste formen: ingenting i svaret sager nagot."""
    svar, schema = sjalvkontrollerbart
    trasigt = FX.helt_men_kort(svar, schema)
    assert K.granska(trasigt, schema) == [], (
        "fixturen ska vara internt konsistent - annars provar den fel sak")
    koder = [a.kod for a in K.granska_par(svar, trasigt, schema)]
    assert K.K2_SER_HELT_UT in koder, koder


def test_kontrollen_ett_helt_svar_anklagas_inte(korpus):
    """Andra riktningen. En grind som faller pa allt mater ingenting."""
    for svar, schema in korpus:
        assert K.granska(svar, schema) == [], svar.verktyg
        assert K.granska_par(svar, svar, schema) == [], svar.verktyg


# ---- kapningen sjalv ----------------------------------------------------

def test_varje_kapat_svar_parsar_och_sager_att_det_kapades(korpus):
    """Svepet over hela korpusen, med ett tak som tvingar fram en kapning."""
    kapade = 0
    for svar, schema in korpus:
        tak = max(200, svar.byte() // 3)
        kapad, notis = K.kapa(svar, tak, schema)
        if not notis.kapat:
            continue
        kapade += 1
        assert kapad.byte() <= tak or notis.hanvisning, notis.rad()
        json.loads(kapad.innehall_text())
        assert kapad.resultat.get(K.FALT_AVKORTAD) is True, svar.verktyg
        assert K.granska(kapad, schema) == [], svar.verktyg
        assert K.granska_par(svar, kapad, schema) == [], svar.verktyg
    assert kapade > 50, "bara %d svar kapades; taket bet inte" % kapade


def test_kapningen_tar_hela_poster_aldrig_delar_av_en(sjalvkontrollerbart):
    svar, schema = sjalvkontrollerbart
    namn = [n for n in K.listfalt(schema)
            if isinstance(svar.resultat.get(n), list)][0]
    fore = svar.resultat[namn]
    kapad, _n = K.kapa(svar, svar.byte() // 2, schema)
    efter = kapad.resultat[namn]
    assert efter == fore[:len(efter)], "posterna ar inte hela och i ordning"


def test_ett_svar_som_inte_ryms_ens_tomt_blir_en_hanvisning_aldrig_en_prefix(
        sjalvkontrollerbart):
    svar, schema = sjalvkontrollerbart
    kapad, notis = K.kapa(svar, 200, schema)
    assert notis.hanvisning
    assert kapad.resultat["for_stort"] is True
    assert kapad.resultat[K.FALT_AVKORTAD] is True
    assert "INGENTING av innehallet" in kapad.resultat[K.FALT_KAPRAD]
    json.loads(kapad.innehall_text())


def test_en_kapning_av_en_kapning_ar_ett_fel(sjalvkontrollerbart):
    """Tva led av grovhet ser likadana ut som ett, och forlusten gar da inte
    langre att mata. Samma mekanism som gor en cache farlig."""
    svar, schema = sjalvkontrollerbart
    kapad, _n = K.kapa(svar, svar.byte() // 2, schema)
    with pytest.raises(Kapfel) as info:
        K.kapa(kapad, 100, schema)
    assert "already a cut" in str(info.value)


# ---- delen som bar felet ------------------------------------------------

def test_ett_svar_som_sprangler_budgeten_tappar_inte_felet(sjalvkontrollerbart):
    """FAS 22:s tredje trasiga fall.

    Ett verktygssvar som spranger budgeten far inte tyst tappa den del som bar
    felet - det ar precis den delen som behovs. Skyddet ar STRUKTURELLT och
    inte en ordlista over faltnamn: felet ligger i KUVERTET, och kapningen ror
    bara innehallet.
    """
    svar, schema = sjalvkontrollerbart
    stort = K.Verktygssvar(
        verktyg=svar.verktyg, argument=dict(svar.argument), ok=False,
        resultat=svar.resultat, fel="E_EXEC: VC nekade kopplingen",
        felnyckel="%s/E_EXEC" % svar.verktyg)
    kapad, notis = K.kapa(stort, 300, schema)
    assert notis.kapat
    assert kapad.felnyckel == stort.felnyckel
    assert "E_EXEC: VC nekade kopplingen" in kapad.text()
    assert "FELNYCKEL: %s/E_EXEC" % svar.verktyg in kapad.text()
    assert K.granska_par(stort, kapad, schema) == []


def test_ett_falt_som_HETER_nagot_med_fel_i_ar_inte_ett_fel(
        sjalvkontrollerbart):
    """ORDLISTEPROVET for kapningen.

    Skyddet far inte leta felbarande falt med en ordlista over nyckelnamn.
    En sadan lista fyrar pa fel storhet sa fort ett verkligt falt heter
    `felmarginal_mm` eller en komponent heter `Felsokningsstation` - samma
    felklass som M-95 matte i NEKANDE-listan.

    Har ar bada med i ett svar som INTE foll. Kapningen ska behandla dem som
    vanlig data: de far trimmas bort med sin post, och svaret ar fortfarande
    inte ett fall.
    """
    schema = {"properties": {
        "components": {"type": "array"},
        "antal": {"type": "integer"},
        "avkortad": {"type": "boolean"}}}
    poster = [{"name": "Felsokningsstation%02d" % i, "felmarginal_mm": 0.5,
               "text": "x" * 200} for i in range(40)]
    svar = K.Verktygssvar(verktyg="list_components", argument={},
                          resultat={"components": poster, "antal": len(poster),
                                    "avkortad": False})
    kapad, notis = K.kapa(svar, svar.byte() // 4, schema)
    assert notis.kapat
    assert kapad.ok is True, "svaret foll aldrig; namnen ar data, inte en dom"
    assert kapad.felnyckel == ""
    assert K.granska(kapad, schema) == []
    assert len(kapad.resultat["components"]) < len(poster)


def test_faltet_antal_bar_tva_storheter_och_granskningen_vet_det():
    """MATT FYND (M-102), och samma felklass som en ordlista pa fel storhet.

    `antal` betyder olika saker i olika verktyg:

        list_components, search_api ...   antal = poster i listan
        search_installed_library         antal = traffar TOTALT, och `visade`
                                         ar hur manga som star i listan

    En granskning som laser `antal` som "poster i listan" anklagar det andra
    verktyget i onodan - och det ar den ofarliga riktningen. Den farliga ar
    den motsatta: en granskning kalibrerad pa search_installed_library skulle
    lasa `antal` som ett totaltal och da MISSA en verklig kapning i alla de
    andra verktygen.

    Provet halls at bada hallen: det riktiga svaret gar fritt, och samma svar
    med en verklig kapning i faller.
    """
    v = V.REGISTER["search_installed_library"]
    resultat = V.DATA_HANDLERS["search_installed_library"]({"query": "conveyor"})
    if not resultat.get("traffar"):
        pytest.skip("inget installerat bibliotek pa den har maskinen")
    assert resultat["antal"] != len(resultat["traffar"]), (
        "fixturen vilar pa att antal och listlangden skiljer sig i just det "
        "har verktyget; gor de inte det provar den ingenting")
    svar = K.Verktygssvar(verktyg="search_installed_library",
                          argument={"query": "conveyor"}, resultat=resultat)
    assert K.granska(svar, v.returns) == []

    riggat = json.loads(json.dumps(resultat))
    riggat["traffar"] = riggat["traffar"][:-1]      # en post tyst borta
    trasigt = K.Verktygssvar(verktyg="search_installed_library",
                             argument={"query": "conveyor"}, resultat=riggat)
    koder = [a.kod for a in K.granska(trasigt, v.returns)]
    assert K.K2_SER_HELT_UT in koder, koder


# ---- konventionen i registret -------------------------------------------

def _klippande_verktyg():
    """Verktyg vars GENERERADE kod klipper en lista vid MAX_POSTER."""
    import re
    kat = os.path.join(_ROT, "svc", "vc_assist_svc", "verktyg")
    ut = set()
    for f in sorted(os.listdir(kat)):
        if not f.endswith(".py"):
            continue
        with open(os.path.join(kat, f), encoding="utf-8") as fh:
            kod = fh.read()
        for m in re.finditer(
                r"def _kod_([a-z0-9_]+)\(argument\):(.*?)(?=\ndef |\n_lagg\(|\Z)",
                kod, re.S):
            if re.search(r"\btak\(", m.group(2)) or "MAX_POSTER" in m.group(2):
                ut.add(m.group(1))
    return ut


def test_inget_verktyg_klipper_utan_att_deklarera_avkortad():
    """En lista som klipps utan att svaret sager det ar ett kapat svar som ser
    helt ut - i verktygslagret i stallet for i kontexten.

    MATT 2026-09-05: 38 verktyg klipper, och alla 38 deklarerar `avkortad`.
    """
    klipper = _klippande_verktyg()
    assert klipper, "hittade inga klippande verktyg; monstret matchar inte"
    saknas = []
    for namn in sorted(klipper):
        v = V.REGISTER.get(namn)
        assert v is not None, ("konventionen _kod_<namn> haller inte for %s"
                               % namn)
        if "avkortad" not in ((v.returns or {}).get("properties") or {}):
            saknas.append(namn)
    assert not saknas, ("dessa verktyg klipper men sager det inte: %s"
                        % ", ".join(saknas))


def test_kontrollen_ett_verktyg_utan_avkortad_falls():
    """TRASIG FIXTUR for provet ovan: samma domare, ett riggat schema."""
    v = V.REGISTER["list_components"]
    riggat = {"properties": dict(
        (k, s) for k, s in (v.returns.get("properties") or {}).items()
        if k != "avkortad")}
    assert "avkortad" not in riggat["properties"]
    assert "components" in K.listfalt(riggat), (
        "fixturen maste fortfarande deklarera listan, annars provar den fel sak")
