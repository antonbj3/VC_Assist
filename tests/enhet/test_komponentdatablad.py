# -*- coding: utf-8 -*-
"""L1 for komponentdatabladet. Ingen VC, inget riktigt bibliotek.

Komponenterna attrapperas som riktiga .vcmx: zip-arkiv med en component.rsc i
VC:s eget textformat och en model.xml. Det som provas ar LASNINGEN och FORMEN,
inte att just den har maskinen har ett bibliotek installerat.

Varje grind har en TRASIG FIXTUR. En grind vars fel ingen har visat gar inte
att skilja fran en grind som alltid sager ja, och tre av felen nedan ar fel
den har modulen faktiskt gjorde under bygget:

  * `VC_PROCESS` stod i API_TYP och finns inte bland constants.xml:s 709.
  * Ledkedjan lastes platt, och en sexaxlig ABB-robot rapporterades ha noll
    leder - ett trovardigt tal, inte ett undantag.
  * `BOMdescription` bryter rader med bakstreck, och strangen slutade efter
    ett ord.
"""
import json
import os
import re
import sys
import zipfile

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import komponentdatablad as KD                 # noqa: E402

_CONSTANTS = os.path.join(_ROT, "docs", "referens", "vc_api", "constants.xml")


# --- attrapper ---------------------------------------------------------------

# En komponent med allt databladet ska kunna lasa: en geometrivariabel som
# INTE ar komponentens (M-59:s fella), en egenskap med storhet, en utan, en
# med tillatna varden, tva boolska signaler, ett granssnitt och en ledkedja
# som ar NASTAD.
RSC = '''VCMD0028041000000000COMPONENT
Node "rSimResource"
{
ProductFamily VisualComponentsBase
Name "Provbandet"
Id 1
NodeClass
{
Id 1
Feature "rGeoFeature"
{
Name "Lada"
VariableSpace
{
  Variable "rTVariable<rDouble>"
  {
    Name "Length"
    Value 1234
    Settings
    {
      VISIBLE
      EDITABLE_DISCONNECTED
    }
  }
}
}
}
Functionality "rSimStatistics"
{
Id 1
Name "Statistics"
}
Functionality "rOneWayPath"
{
Id 2
Name "Path"
Capacity 10
Speed 500
}
Functionality "rSimBoolSignal"
{
Id 3
Name "StartSignal"
AutomaticReset 1
}
Functionality "rSimBoolSignal"
{
Id 4
Name "StopSignal"
AutomaticReset 0
}
Functionality "rSimInterface"
{
Id 5
Name "InInterface"
Section
{
Name "Section"
Fields
{
rSimFlowField
{
Name "FlowIn"
Func "Path"
}
}
}
}
Functionality "rKinScara2"
{
Id 6
Name "Kinematik"
}
VCID 11111111-2222-3333-4444-555555555555
Revision 3
BOMdescription  "Ett band som bryter sin beskrivning med bakstreck mitt i or\\
det och fortsatter pa nasta rad."
Category  "Conveyors"
VariableSpace ""
{
  Variable "rTVariable<rBool>"
  {
    Name "Visible"
    Value 1
    Settings
    {
      VISIBLE
    }
  }
  Variable "rTVariable<rDouble>"
  {
    Name "ConveyorSpeed"
    Value 820
    Settings
    {
      VISIBLE
      EDITABLE_DISCONNECTED
    }
  }
  Variable "rTVariable<rDouble>"
  {
    Name "ConveyorWidth"
    Value 140
    Settings
    {
      VISIBLE
      EDITABLE_DISCONNECTED
    }
    Quantity "Distance" "VectorQuantity"
    {
      Groups
      {
      }
    }
  }
  Variable "rTStepVariable<rString>"
  {
    Name "OnLimit"
    Value "Stop"
    Settings
    {
      VISIBLE
    }
    StepList
    {
      Step
      {
        Value "Stop"
        Enabled 1
      }
      Step
      {
        Value "Continue"
        Enabled 1
      }
    }
  }
  Variable "rTPointerListVariable<Component>"
  {
    Name "Grannar"
    Value
    {
    }
    Settings
    {
      VISIBLE
    }
  }
}
Node "rSimLink"
{
Name "Axis1"
Id 2
NodeClass
{
Id 2
}
Dof  "Rotational"
{
Name "Axis1"
Properties
{
  Variable "rTVariable<rDouble>"
  {
    Name "MaxSpeed"
    Value 288
    Settings
    {
      VISIBLE
    }
  }
}
MinLimit
{
  Expression "-170"
}
MaxLimit
{
  Expression "170"
}
}
Node "rSimLink"
{
Name "Axis2"
Id 3
NodeClass
{
Id 3
}
Dof  "Rotational"
{
Name "Axis2"
Properties
{
}
MinLimit
{
  Expression "-100"
}
MaxLimit
{
  Expression "135"
}
}
}
}
}
'''

MODELXML = '''<?xml version="1.0" encoding="utf-8"?>
<VcModel>
  <Properties>
    <Property name="VCID">11111111-2222-3333-4444-555555555555</Property>
    <Property name="Name">Provbandet</Property>
    <Property name="Description">Ett provband.

### Key properties ###
ConveyorSpeed = bandets hastighet</Property>
    <Property name="Type">Conveyors</Property>
    <Property name="Manufacturer">Provfabriken</Property>
    <Property name="MaxPayload">25</Property>
    <Property name="Tags">Band</Property>
    <Property name="Revision">3</Property>
    <Property name="IsDeprecated">False</Property>
  </Properties>
</VcModel>
'''


def _vcmx(sokvag, rsc=RSC, modelxml=MODELXML):
    with zipfile.ZipFile(sokvag, "w") as z:
        z.writestr("component.rsc", rsc)
        if modelxml is not None:
            z.writestr("model.xml", modelxml)
    return str(sokvag)


@pytest.fixture()
def blad(tmp_path):
    return KD.las(_vcmx(tmp_path / "prov.vcmx"))


# --- avbildningen rsc-typ -> VC_-konstant ------------------------------------

def _kanda_konstanter():
    ut = set()
    with open(_CONSTANTS, encoding="utf-8-sig") as f:
        for rad in f:
            r = rad.strip()
            if r.startswith("VC_"):
                ut.add(r)
    return ut


def test_constants_xml_gar_att_lasa_och_bar_de_709_konstanterna():
    """Referensen som grinden nedan mater mot maste sjalv vara vid liv.

    En grind vars facit tyst blir tomt slutar mata och borjar saga ja.
    """
    assert len(_kanda_konstanter()) > 600


def test_varje_konstant_i_tabellen_finns_i_constants_xml():
    kanda = _kanda_konstanter()
    saknade = sorted(v for v, _h in KD.API_TYP.values() if v not in kanda)
    assert saknade == [], (
        "API_TYP namner konstanter som inte finns i VC:s egen constants.xml: %s"
        % saknade)


def test_grinden_faller_en_konstant_som_inte_finns():
    """TRASIG FIXTUR for provet ovan, och felet ar ETT JAG GJORDE.

    Forsta versionen av API_TYP innehöll `VC_PROCESS`, som inte star bland
    constants.xml:s 709 konstanter. Utan det har provet hade den raden legat
    kvar och hamnat i varje datablad som bar en rSimProcess.
    """
    kanda = _kanda_konstanter()
    trasig = dict(KD.API_TYP)
    trasig["rHittepa"] = ("VC_PROCESS", KD.HARLEDD)
    saknade = sorted(v for v, _h in trasig.values() if v not in kanda)
    assert saknade == ["VC_PROCESS"]


def test_harledda_avbildningar_harleds_verkligen():
    fel = sorted(t for t, (v, h) in KD.API_TYP.items()
                 if h == KD.HARLEDD and KD.harled_konstant(t) != v)
    assert fel == [], ("dessa star som HARLEDD men faller inte ut ur "
                       "harled_konstant(): %s" % fel)


def test_handsatta_avbildningar_harleds_inte():
    """En handsatt post som GAR att harleda ar felmarkt, och det doljer att
    tabellen bar farre pastaenden an den ser ut att gora."""
    fel = sorted(t for t, (v, h) in KD.API_TYP.items()
                 if h == KD.HANDSATT and KD.harled_konstant(t) == v)
    assert fel == [], ("dessa star som HANDSATT men harleds mekaniskt: %s" % fel)


def test_grinden_faller_en_felmarkt_post():
    """TRASIG FIXTUR: `rOneWayPath -> VC_ONEWAYPATH` harleds, sa den far inte
    sta som handsatt."""
    trasig = {"rOneWayPath": ("VC_ONEWAYPATH", KD.HANDSATT)}
    fel = [t for t, (v, h) in trasig.items()
           if h == KD.HANDSATT and KD.harled_konstant(t) == v]
    assert fel == ["rOneWayPath"]


def test_en_okand_beteendetyp_ger_tomt_och_inte_en_gissning():
    assert KD.api_konstant("rKinScara2") == ""
    assert KD.api_harkomst("rKinScara2") == ""
    assert KD.api_konstant("rHittepaFunktionalitet") == ""


# --- egenskaperna: komponentens EGNA, inte geometrins ------------------------

def test_geometrins_variabler_hamnar_inte_bland_egenskaperna(blad):
    """M-59:s fella, som trasig fixtur.

    Attrappen bar `Length = 1234` inne i en rGeoFeature - alltsa i en LADA och
    inte pa komponenten. katalogindex._parametrar soker i hela texten och
    plockar upp den; databladet laser rotens variabelrymd och ska inte.
    """
    namn = [e.namn for e in blad.egenskaper]
    assert "Length" not in namn
    assert "ConveyorSpeed" in namn
    # Och det ar samma text som lurar den gamla lasningen:
    from vc_assist_svc import katalogindex
    assert "Length" in katalogindex._parametrar(RSC)


def test_visible_raknas_inte_som_en_egen_egenskap(blad):
    """`Visible` star i praktiskt taget varje rotvariabelrymd och sager
    darfor ingenting om NAGON komponent."""
    assert "Visible" not in [e.namn for e in blad.egenskaper]


def test_egenskapen_bar_typ_standardvarde_och_tillatna_varden(blad):
    e = blad.egenskap("OnLimit")
    assert e is not None
    assert e.typ == "rString"
    assert e.deklarerad_typ() == "rTStepVariable<rString>"
    assert e.varde == "Stop"
    assert e.steg == ["Stop", "Continue"]


def test_en_pekarlista_syns_som_en_lista(blad):
    assert blad.egenskap("Grannar").deklarerad_typ() == \
        "rTPointerListVariable<Component>"


# --- enheter: sags, harleds aldrig -------------------------------------------

def test_en_egenskap_utan_quantity_far_ingen_enhet(blad):
    """ConveyorSpeed ar 820 och bar INGEN Quantity i attrappen.

    Att VC:s varldsenhet ar millimeter far inte gora 820 till "820 mm/s".
    """
    e = blad.egenskap("ConveyorSpeed")
    assert e.kvantitet == ""
    rad = e.rad()
    assert "storhet saknas" in rad
    for enhet in ("mm", "m/s", "kg", "grader", "deg", "sek"):
        assert enhet not in rad.replace("saknas", ""), \
            "en enhet dok upp ur ett talvarde: %s" % rad


def test_en_egenskap_med_quantity_bar_storheten_ordagrant(blad):
    e = blad.egenskap("ConveyorWidth")
    assert e.kvantitet == "Distance"
    assert "storhet Distance" in e.rad()


def test_maxpayload_skrivs_utan_pahangd_enhet(blad):
    """model.xml deklarerar TALET 25 och inget mer - inget "kg" star i filen."""
    assert blad.nyttolast_kg == 25.0
    t = KD.text(blad)
    rad = [r for r in t.splitlines() if r.startswith("MaxPayload")][0]
    assert "ENHET EJ DEKLARERAD" in rad
    assert rad.rstrip().endswith("25")


def test_ett_saknat_katalogfalt_ar_none_och_inte_noll(tmp_path):
    """Reach star inte i attrappens model.xml. En komponent utan angiven
    rackvidd har inte rackvidden noll."""
    b = KD.las(_vcmx(tmp_path / "utan.vcmx"))
    assert b.rackvidd_mm is None
    assert "Reach (deklarerat falt i katalogposten, ENHET EJ DEKLARERAD i " \
           "filen): saknas" in KD.text(b)


# --- signalerna: M-84:s oppna fraga ------------------------------------------

def test_signalerna_star_vid_namn_i_filens_ordning(blad):
    assert [s.namn for s in blad.signaler()] == ["StartSignal", "StopSignal"]


def test_med_flera_boolska_signaler_sags_att_index_noll_inte_gar_att_veta(blad):
    t = KD.text(blad)
    assert 'findBehavioursByType(VC_BOOLEANSIGNAL) ger 2 stycken' in t
    assert "VILKEN som ar [0] gar INTE att lasa ur filen" in t
    assert "findBehaviour(namn)" in t


def test_med_exakt_en_boolsk_signal_ar_index_noll_entydigt(tmp_path):
    """Trasig fixtur at andra hallet: tas den ena signalen bort ar svaret
    entydigt, och da SKA databladet saga namnet i stallet for att svamla."""
    rsc = RSC.replace('''Functionality "rSimBoolSignal"
{
Id 4
Name "StopSignal"
AutomaticReset 0
}
''', "")
    b = KD.las(_vcmx(tmp_path / "en.vcmx", rsc=rsc))
    t = KD.text(b)
    assert 'findBehavioursByType(VC_BOOLEANSIGNAL)[0] ar "StartSignal"' in t
    assert "VILKEN som ar [0] gar INTE" not in t


def test_utan_boolska_signaler_sags_det_rent_ut(tmp_path):
    rsc = re.sub(r'Functionality "rSimBoolSignal"\n\{.*?\n\}\n', "", RSC,
                 flags=re.S)
    b = KD.las(_vcmx(tmp_path / "inga.vcmx", rsc=rsc))
    assert b.signaler_av_typ("rSimBoolSignal") == []
    assert "SIGNALER: saknas" in KD.text(b)


# --- beteenden, granssnitt, leder --------------------------------------------

def test_beteendena_star_vid_namn_med_sina_nyckelfalt(blad):
    path = [b for b in blad.beteenden if b.namn == "Path"][0]
    assert path.typ == "rOneWayPath"
    assert path.api_typ == "VC_ONEWAYPATH"
    assert path.falt == {"Capacity": "10", "Speed": "500"}


def test_granssnittet_sager_vad_det_bar(blad):
    g = [x for x in blad.granssnitt if x.namn == "InInterface"][0]
    assert g.api_typ == "VC_ONETOONEINTERFACE"
    assert "FlowIn:rSimFlowField" in g.rad()


def test_den_nastade_ledkedjan_ger_ALLA_leder(blad):
    """TRASIG FIXTUR for ett fel jag gjorde: kedjan ar nastad i filen.

    Axis2 ligger INNE i Axis1. En platt lasning av rotnodens direkta barn ser
    exakt en lank och svarar "1 led" pa en tvaaxlig maskin - ett trovardigt
    tal, inte ett undantag, och alltsa osynligt utan det har provet.
    """
    assert [l.namn for l in blad.leder] == ["Axis1", "Axis2"]
    a1 = blad.leder[0]
    assert (a1.dof, a1.min_grans, a1.max_grans) == ("Rotational", "-170", "170")
    assert a1.max_hastighet == "288"
    # Axis2 saknar MaxSpeed i attrappen och ska da saga saknas, inte noll.
    assert blad.leder[1].max_hastighet == ""
    assert "maxhastighet saknas" in blad.leder[1].rad()


def test_ledens_granser_far_ingen_enhet(blad):
    """En rotationsled i grader och en linjarled i millimeter ser likadana ut
    i filen, och det ska de gora i databladet ocksa."""
    rad = blad.leder[0].rad()
    assert "-170" in rad and "170" in rad
    assert "grader" not in rad and "mm" not in rad and "deg" not in rad


# --- strangar och trasiga filer ----------------------------------------------

def test_en_strang_med_bakstreck_radbrytning_lases_hel(blad):
    """TRASIG FIXTUR for ett fel jag gjorde: `\\` sist pa raden ar formatets
    radfortsattning. Utan re.S i _ARG slutade beskrivningen efter ett ord."""
    assert "fortsatter pa nasta rad" in blad.beskrivning
    assert "\\" not in blad.beskrivning


def test_en_fil_utan_component_rsc_ger_fel_och_inte_ett_tomt_datablad(tmp_path):
    sokvag = tmp_path / "tom.vcmx"
    with zipfile.ZipFile(sokvag, "w") as z:
        z.writestr("model.xml", MODELXML)
    with pytest.raises(KD.Databladfel):
        KD.las(str(sokvag))


def test_en_fil_som_inte_ar_ett_arkiv_ger_fel(tmp_path):
    sokvag = tmp_path / "skrap.vcmx"
    sokvag.write_bytes(b"det har ar inte en zip")
    with pytest.raises(KD.Databladfel):
        KD.las(str(sokvag))


def test_utan_model_xml_sags_vilka_falt_som_inte_gick_att_lasa(tmp_path):
    b = KD.las(_vcmx(tmp_path / "utan_katalogpost.vcmx", modelxml=None))
    assert any("model.xml" in x for x in b.olasta)
    assert "EJ LASTA FALT" in KD.text(b)
    assert b.nyttolast_kg is None


def test_obalanserade_klamrar_ger_fel_och_inte_halva_svar():
    with pytest.raises(KD.Databladfel):
        KD.las_text('Node "rSimResource"\n{\nName "halv"\n')


# --- formen: kapning pa ANTAL POSTER -----------------------------------------

def test_kapningen_sker_pa_antal_poster_och_sager_hur_manga(blad):
    t = KD.text(blad, max_egenskaper=2)
    rader = t.splitlines()
    i = rader.index("EGENSKAPER (det getProperty(namn) slar upp) (4 st):")
    assert rader[i + 1].strip().startswith("ConveyorSpeed")
    assert rader[i + 2].strip().startswith("ConveyorWidth")
    assert "... 2 till, ej visade" in rader[i + 3]
    # Ingen rad ar halv: varje visad egenskapsrad bar alla sina falt.
    for rad in rader[i + 1:i + 3]:
        assert "standard " in rad and "storhet " in rad


def test_ett_helt_avsnitt_som_saknas_sags_saknas(tmp_path):
    rsc = re.sub(r'VariableSpace ""\n\{.*?\n\}\n', "", RSC, flags=re.S)
    b = KD.las(_vcmx(tmp_path / "nakna.vcmx", rsc=rsc))
    assert b.egenskaper == []
    assert "EGENSKAPER (det getProperty(namn) slar upp): saknas" in KD.text(b)


def test_taken_star_i_koden_och_har_sin_matning():
    """En troskel utan matreferens ar en gissning med ett tal framfor sig."""
    kalla = open(os.path.join(_ROT, "svc", "vc_assist_svc",
                              "komponentdatablad.py"), encoding="utf-8").read()
    for namn in ("MAX_EGENSKAPER", "MAX_BETEENDEN", "MAX_GRANSSNITT",
                 "MAX_LEDER", "MAX_BESKRIVNING"):
        rad = [r for r in kalla.splitlines() if r.startswith(namn + " =")][0]
        assert "M-85" in rad, "%s saknar matreferens: %s" % (namn, rad)


def test_handsatta_avbildningar_pekas_ut_i_svaret(blad):
    """Den som laser ska kunna se vilka avbildningar som ar pastaenden."""
    t = KD.text(blad)
    assert "AVBILDNINGAR SOM AR PASTAENDEN" in t
    assert "rSimBoolSignal -> VC_BOOLEANSIGNAL" in t


def test_beteendetyper_utan_avbildning_namns(blad):
    t = KD.text(blad)
    assert "BETEENDETYPER UTAN KAND API-KONSTANT" in t
    assert "rKinScara2" in t


def test_nolla_i_model_xml_blir_saknas_inte_noll():
    """Trasig fixtur for E3a: _tal('0') och _tal(0.0) maste ge None."""
    assert KD._tal("0") is None
    assert KD._tal("0.0") is None
    assert KD._tal(0) is None
    assert KD._tal(0.0) is None
    assert KD._tal(None) is None
    assert KD._tal("703") == 703.0
