# -*- coding: utf-8 -*-
"""L1 for komponentfilen. Ingen VC, inget riktigt bibliotek.

Provet handlar om EN fraga: vad bar filen, och vad bar den inte? Tva av
fixturerna ar med avsikt TRASIGA - en komponent utan matt och en profil som
inte gar att avkoda - for en grind som bara ser hela filer matar ingenting.
"""
import os
import struct
import sys
import zipfile

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.dirname(__file__))

import attrapp_vcmx as A                                          # noqa: E402
from vc_assist_svc import komponentfil as K                       # noqa: E402


# ---------------------------------------------------------------------------
# tolkaren av component.rsc
# ---------------------------------------------------------------------------

def test_features_nastlas_i_varandra_och_tradet_bar_djupet():
    """En transform BAR sina barn. En platt lista hade tappat kedjan."""
    text = A.rsc("X", A.GEO_I_UTTRYCK % {"namn": "g", "uri": "geo-1"})
    rot = K.tolka_rsc(text)
    transform = list(rot.alla("Feature", "rTransformFeature"))
    assert len(transform) == 1
    inne = list(transform[0].alla("Feature", "rGeoFeature"))
    assert len(inne) == 1, "geometrin ligger UNDER transformen, inte bredvid"


def test_ett_block_pa_en_rad_tolkas():
    """Biblioteket bar `Frame { Name "x" }` pa EN rad. Radbaserat tolkande
    missar det, och en tolkare som missar fyra fall av 3201 ar inte klar."""
    rot = K.tolka_rsc('Node "a"\n{\nFrame { Name "F1" }\n}\n')
    ram = list(rot.alla("Frame"))
    assert ram and ram[0].forsta("Name").arg1 == "F1"


def test_strang_med_citattecken_och_radfortsattning():
    text = ('Node "a"\n{\nTransform\n{\n  Expression "Tx(1).Ty(P==\\"Top\\\n'
            'Left\\")"\n}\n}\n')
    rot = K.tolka_rsc(text)
    e = list(rot.alla("Expression"))[0]
    assert e.arg1 == 'Tx(1).Ty(P=="TopLeft")'


def test_klamrar_inne_i_en_strang_oppnar_inget_block():
    rot = K.tolka_rsc('Node "a"\n{\nScript "def f():\n  x = {1: 2}\n"\nId 3\n}\n')
    assert rot.forsta("Node").forsta("Id").arg1 == "3"


# ---------------------------------------------------------------------------
# model.xml: uppgifterna som gar att lasa billigt
# ---------------------------------------------------------------------------

def _enkel(tmp_path, namn="Prov", **egen):
    egenskaper = {"Name": namn, "Type": "Conveyors", "Manufacturer": "Acme",
                  "IsDeprecated": "False"}
    egenskaper.update(egen)
    return A.skriv(tmp_path / (namn + ".vcmx"), A.modelxml(**egenskaper),
                   A.rsc(namn))


def test_namn_kategori_tillverkare_lases_ur_model_xml(tmp_path):
    f = K.las(_enkel(tmp_path, "Band 1", Reach="0", MaxPayload="1500"))
    assert (f.namn, f.kategori, f.tillverkare) == ("Band 1", "Conveyors", "Acme")
    assert f.nyttolast_kg == 1500.0


def test_kategorin_ar_komponentens_egen_inte_katalogens(tmp_path):
    """M-58:s falla, mekaniserad. Grunt lage i katalogindexet tar kategorin ur
    KATALOGNAMNET; model.xml bar komponentens EGET Type. Nar de sar isar ska
    komponentens eget vinna, och det ska ga att prova."""
    katalog = tmp_path / "ABB" / "Robots"
    katalog.mkdir(parents=True)
    sokvag = A.skriv(katalog / "band.vcmx",
                     A.modelxml(Name="Band", Type="Conveyors",
                                Manufacturer="ABB"), A.rsc("Band"))
    assert os.path.basename(os.path.dirname(sokvag)) == "Robots"
    assert K.las(sokvag).kategori == "Conveyors"


def test_utan_model_xml_ar_det_ingen_komponent(tmp_path):
    sokvag = str(tmp_path / "trasig.vcmx")
    with zipfile.ZipFile(sokvag, "w") as z:
        z.writestr("component.rsc", A.rsc("X"))
    with pytest.raises(K.Filfel):
        K.las(sokvag)


def test_en_fil_som_inte_ar_ett_zip_arkiv(tmp_path):
    sokvag = tmp_path / "skrap.vcmx"
    sokvag.write_bytes(b"det har ar ingen zip")
    with pytest.raises(K.Filfel):
        K.las(str(sokvag))


def test_saknad_fil_ar_ett_fel_inte_ett_tomt_svar(tmp_path):
    with pytest.raises(K.Filfel):
        K.las(str(tmp_path / "finns-inte.vcmx"))


# ---------------------------------------------------------------------------
# TRASIG FIXTUR 1: komponenten vars matt saknas
# ---------------------------------------------------------------------------

def test_en_komponent_utan_matt_ger_saknas_inte_ett_gissat_ratblock(tmp_path):
    """Den viktigaste raden i hela provet.

    Filen bar geometri, gransssnitt och ett namn - allt utom den omslutande
    volymen. Lasaren far INTE svara med en lada, varken en nollada eller en
    som raknats ur nagot annat matt.
    """
    sokvag = A.skriv(
        tmp_path / "utan_matt.vcmx",
        A.modelxml(Name="Utan matt", Type="Machines", Manufacturer="Acme"),
        A.rsc("Utan matt", A.GEO_KONSTANT % {"namn": "g", "uri": "geo-1"}),
        {"geo-1": A.tds_geometri(A.lada_horn(1000.0, 500.0, 800.0))})
    f = K.las(sokvag, djupt=True, geometri=True)
    assert f.lada is None
    assert f.lada_harkomst == K.Harkomst.SAKNAS
    assert "get_bounds" in f.lada_skal
    # geometrins EGEN lada finns - men det ar en annan storhet an komponentens
    assert f.geometri[0].lada.storlek_mm == (1000.0, 500.0, 800.0)
    assert f.geometri[0].lada.harkomst == K.Harkomst.HARLEDD


def test_ingen_lada_uppstar_ens_nar_geometrin_ar_en_enda_blobb(tmp_path):
    """Frestelsen: en komponent med EN geometri ser ut att ha en sjalvklar
    lada. Den har det inte - blobbens ram ar inte komponentens."""
    sokvag = A.skriv(
        tmp_path / "en_blobb.vcmx",
        A.modelxml(Name="En", Type="Machines", Manufacturer="Acme"),
        A.rsc("En", A.GEO_KONSTANT % {"namn": "g", "uri": "geo-1"}),
        {"geo-1": A.tds_geometri(A.lada_horn(100.0, 100.0, 100.0))})
    assert K.las(sokvag, djupt=True, geometri=True).lada is None


# ---------------------------------------------------------------------------
# geometrin: 3DS
# ---------------------------------------------------------------------------

def test_hornlistan_lases_och_ger_blobbens_egen_lada(tmp_path):
    horn = [(-10.0, -20.0, 0.0), (30.0, 5.0, 60.0)]
    sokvag = A.skriv(tmp_path / "g.vcmx",
                     A.modelxml(Name="G", Type="Machines", Manufacturer="A"),
                     A.rsc("G", A.GEO_KONSTANT % {"namn": "g", "uri": "geo-1"}),
                     {"geo-1": A.tds_geometri(horn)})
    g = K.las(sokvag, djupt=True, geometri=True).geometri[0]
    assert g.lada.min_mm == (-10.0, -20.0, 0.0)
    assert g.lada.max_mm == (30.0, 5.0, 60.0)
    assert g.horn == 2


def test_strukturprovet_godkanner_en_hel_blobb():
    horn = A.lada_horn(100.0, 100.0, 100.0)
    blobb = A.tds_geometri(horn, trianglar=[(0, 1, 2), (5, 6, 7)])
    assert K.tds_kontroll(blobb) == (1, 0)


def test_strukturprovet_faller_pa_ett_index_utanfor_hornlistan():
    """TRASIG FIXTUR: en triangel som pekar pa ett horn som inte finns.

    Index och koordinater ligger i OLIKA chunkar, sa provet gar inte att lura
    genom att lasa fel: en felavlast hornlista ger index utanfor. Over 300
    slumpade komponenter var 71 903 av 71 903 meshar hela (M-61).
    """
    horn = A.lada_horn(100.0, 100.0, 100.0)      # atta horn
    blobb = A.tds_geometri(horn, trianglar=[(0, 1, 2), (5, 6, 99)])
    assert K.tds_kontroll(blobb) == (1, 1)


def test_strukturprovet_pa_nagot_som_inte_ar_3ds():
    assert K.tds_kontroll(b"inte 3ds") == (0, 0)


def test_en_blobb_som_inte_ar_3ds_ger_ingen_lada(tmp_path):
    sokvag = A.skriv(tmp_path / "g.vcmx",
                     A.modelxml(Name="G", Type="Machines", Manufacturer="A"),
                     A.rsc("G", A.GEO_KONSTANT % {"namn": "g", "uri": "geo-1"}),
                     {"geo-1": b"detta ar inte 3ds"})
    g = K.las(sokvag, djupt=True, geometri=True).geometri[0]
    assert g.lada is None and g.horn == 0


def test_en_avhuggen_3ds_blobb_ger_ingen_lada(tmp_path):
    """TRASIG FIXTUR: chunkstorleken lovar mer an filen bar."""
    hel = A.tds_geometri(A.lada_horn(100.0, 100.0, 100.0))
    sokvag = A.skriv(tmp_path / "g.vcmx",
                     A.modelxml(Name="G", Type="Machines", Manufacturer="A"),
                     A.rsc("G", A.GEO_KONSTANT % {"namn": "g", "uri": "geo-1"}),
                     {"geo-1": hel[:len(hel) // 2]})
    g = K.las(sokvag, djupt=True, geometri=True).geometri[0]
    assert g.lada is None, "en halv fil far inte ge en hel lada"


def test_geometrins_placering_klassas_som_konstant_uttryck_eller_villkorad(tmp_path):
    kropp = (A.GEO_KONSTANT % {"namn": "fast", "uri": "geo-1"}
             + A.GEO_I_UTTRYCK % {"namn": "rorlig", "uri": "geo-2"})
    sokvag = A.skriv(tmp_path / "p.vcmx",
                     A.modelxml(Name="P", Type="Machines", Manufacturer="A"),
                     A.rsc("P", kropp),
                     {"geo-1": A.tds_geometri([(0.0, 0.0, 0.0)]),
                      "geo-2": A.tds_geometri([(1.0, 1.0, 1.0)])})
    lagen = {g.namn: g.placering for g in
             K.las(sokvag, djupt=True).geometri}
    assert lagen == {"fast": K.Geometri.KONSTANT,
                     "rorlig": K.Geometri.UTTRYCK}


# ---------------------------------------------------------------------------
# rackviddsprofilen: BADA formaten
# ---------------------------------------------------------------------------

def test_profilen_i_3ds_varianten_ger_radien(tmp_path):
    segment = [((-475.0, 0.0, 482.0), (-190.0, 0.0, 481.0)),
               ((-190.0, 0.0, 481.0), (475.0, 0.0, 100.0))]
    sokvag = A.skriv(tmp_path / "r.vcmx",
                     A.modelxml(Name="R", Type="Robots", Manufacturer="A"),
                     A.rsc("R"), {"envelopeprofile": A.tds_envelope(segment)})
    p = K.las(sokvag, djupt=True, geometri=True).profil
    assert p is not None and len(p) == 2
    assert p.radie_mm == 475.0
    assert p.z_mm == (100.0, 482.0)


def test_profilen_i_textvarianten_ger_samma_slags_svar(tmp_path):
    punkter = [(0.0, 0.0, 870.0), (579.8, 0.0, 273.1), (0.0, 0.0, -112.0)]
    sokvag = A.skriv(tmp_path / "r.vcmx",
                     A.modelxml(Name="R", Type="Robots", Manufacturer="A"),
                     A.rsc("R"), {"envelopeprofile": A.text_envelope(punkter)})
    p = K.las(sokvag, djupt=True, geometri=True).profil
    assert p is not None
    assert abs(p.radie_mm - 579.8) < 1e-6
    assert p.z_mm == (-112.0, 870.0)


def test_profilen_i_polylinjevarianten_ger_radien(tmp_path):
    """Sju av 702 filer bar en ANDRA layout i samma chunk. En lasare som bara
    kan den vanliga svarar `saknas` for dem, och det svaret ar inte fel - men
    det ar sju robotar som inte behovde vara tomma."""
    punkter = [(0.0, 0.0, 917.4), (656.8, 0.0, 300.0), (0.0, 0.0, -333.3)]
    sokvag = A.skriv(tmp_path / "r.vcmx",
                     A.modelxml(Name="R", Type="Robots", Manufacturer="A"),
                     A.rsc("R"),
                     {"envelopeprofile": A.tds_envelope_polylinje(punkter)})
    p = K.las(sokvag, djupt=True, geometri=True).profil
    assert p is not None and abs(p.radie_mm - 656.8) < 1e-6


def test_profilen_hittas_aven_nar_tradgangen_gar_sonder(tmp_path):
    """De sju filerna bar tva oforklarade byte efter objektnamnet. Tradgangen
    stannar dar; bytesokningen tar over, och den exakta langdmatchningen ar
    det som gor att fyndet gar att lita pa."""
    punkter = [(0.0, 0.0, 917.4), (656.8, 0.0, 300.0), (0.0, 0.0, -333.3)]
    sokvag = A.skriv(tmp_path / "r.vcmx",
                     A.modelxml(Name="R", Type="Robots", Manufacturer="A"),
                     A.rsc("R"),
                     {"envelopeprofile": A.tds_envelope_polylinje(
                         punkter, skrap_efter_namn=b"\x02\x00")})
    p = K.las(sokvag, djupt=True, geometri=True).profil
    assert p is not None and abs(p.radie_mm - 656.8) < 1e-6


def test_en_nyttolast_som_inte_gar_jamnt_ut_kastas():
    """TRASIG FIXTUR: chunken lovar fler punkter an den bar. Den exakta
    langdmatchningen ar hela skyddet mot att lasa brus som en polylinje."""
    hel = A.tds_envelope_polylinje([(0.0, 0.0, 1.0), (2.0, 0.0, 3.0),
                                    (4.0, 0.0, 5.0)])
    assert K.tds_profil(hel[:-24]) is None


def test_en_profil_som_inte_gar_att_avkoda_ger_none(tmp_path):
    """TRASIG FIXTUR: posten finns men innehallet ar skrap.

    Utan den har raden hade en tom profil kunnat bli radien 0,0 - alltsa en
    robot som pastas na noll millimeter, vilket ser ut som en matning.
    """
    sokvag = A.skriv(tmp_path / "r.vcmx",
                     A.modelxml(Name="R", Type="Robots", Manufacturer="A"),
                     A.rsc("R"), {"envelopeprofile": b"\x01\x02\x03 skrap"})
    assert K.las(sokvag, djupt=True, geometri=True).profil is None


def test_en_tom_profil_gar_inte_att_bygga():
    """TRASIG FIXTUR: noll punkter skulle ge radien 0,0 - en robot som pastas
    na noll millimeter. Ingen profil ar ett battre svar an en tom."""
    with pytest.raises(K.Filfel):
        K.Rackviddsprofil([])
    with pytest.raises(K.Filfel):
        K.Rackviddsprofil([()])


def test_textprofilen_provas_inte_pa_binart_innehall():
    assert K.text_profil(A.tds_envelope([((1.0, 0.0, 2.0), (3.0, 0.0, 4.0))])) is None


# ---------------------------------------------------------------------------
# granssnitten, ramarna och lederna
# ---------------------------------------------------------------------------

def _band(tmp_path, namn="Band"):
    kropp = (A.GRANSSNITT_FLODE % {"namn": "InInterface", "ram": "Start",
                                   "faltnamn": "FlowIn", "port": 0}
             + A.GRANSSNITT_FLODE % {"namn": "OutInterface", "ram": "End",
                                     "faltnamn": "FlowOut", "port": 1}
             + A.RAM_UTTRYCK % {"namn": "Start", "uttryck": "0"}
             + A.RAM_UTTRYCK % {"namn": "End", "uttryck": "ConveyorLength"})
    return A.skriv(tmp_path / (namn + ".vcmx"),
                   A.modelxml(Name=namn, Type="Conveyors", Manufacturer="A"),
                   A.rsc(namn, kropp))


def test_granssnitten_bar_namn_ram_falttyp_och_port(tmp_path):
    f = K.las(_band(tmp_path), djupt=True)
    namn = {g.namn: g for g in f.granssnitt}
    assert set(namn) == {"InInterface", "OutInterface"}
    assert namn["InInterface"].ramar == ("Start",)
    assert namn["InInterface"].portar == (0,)
    assert namn["OutInterface"].portar == (1,)
    assert namn["OutInterface"].falttyper == ("rSimFlowField",)


def test_ramarnas_NAMN_lases_men_deras_LAGE_saknas_nar_kedjan_ar_ett_uttryck(tmp_path):
    f = K.las(_band(tmp_path), djupt=True)
    assert set(f.ramnamn()) == {"Start", "End"}
    for r in f.ramar:
        assert r.lage_mm is None
        assert r.harkomst == K.Harkomst.SAKNAS
    assert any(r.uttryck == "Tx(ConveyorLength)" for r in f.ramar), \
        "skalet till att laget saknas ska sta i klartext"


def test_en_ram_med_en_fast_matris_lases(tmp_path):
    sokvag = A.skriv(tmp_path / "m.vcmx",
                     A.modelxml(Name="M", Type="Machines", Manufacturer="A"),
                     A.rsc("M", A.RAM_MATRIS % {"namn": "Bas", "x": 10.0,
                                                "y": -20.0, "z": 30.0}))
    ram = K.las(sokvag, djupt=True).ramar[0]
    assert ram.namn == "Bas"
    assert ram.lage_mm == (10.0, -20.0, 30.0)
    assert ram.harkomst == K.Harkomst.LAST


def test_ett_TOMT_uttryck_ar_inget_uttryck(tmp_path):
    """VC skriver `Expression ""` i 6950 av 39 171 transformer.

    Forsta matningen raknade dem som uttryck och fick da 39 171 av 39 171 -
    ett tal som saag starkt ut och var sjutton procent for hogt. En tom
    strang ar ingen parametrisk del, och nar matrisen star bredvid gar laget
    att rakna fram.
    """
    kropp = A.TRANSFORM_TOMT_UTTRYCK_MED_MATRIS % {
        "namn": "T", "x": 100.0, "y": 0.0, "z": 50.0,
        "kropp": A.RAM_BAR % {"namn": "Inne"}}
    sokvag = A.skriv(tmp_path / "t.vcmx",
                     A.modelxml(Name="T", Type="Machines", Manufacturer="A"),
                     A.rsc("T", kropp))
    ram = K.las(sokvag, djupt=True).ramar[0]
    assert ram.harkomst == K.Harkomst.HARLEDD
    assert ram.lage_mm == (100.0, 0.0, 50.0)


def test_ett_tomt_uttryck_UTAN_matris_ar_okant_inte_enhetsmatrisen(tmp_path):
    """TRASIG FIXTUR: att en transform utan bade uttryck och matris ar
    enhetsmatrisen ar troligt och oprovat. Troligt racker inte."""
    kropp = A.TRANSFORM_TOMT_UTTRYCK_UTAN_MATRIS % {
        "namn": "T", "kropp": A.RAM_BAR % {"namn": "Inne"}}
    sokvag = A.skriv(tmp_path / "t.vcmx",
                     A.modelxml(Name="T", Type="Machines", Manufacturer="A"),
                     A.rsc("T", kropp))
    ram = K.las(sokvag, djupt=True).ramar[0]
    assert ram.harkomst == K.Harkomst.SAKNAS


def test_en_nodhanvisning_i_ett_granssnitt_ar_ingen_nod(tmp_path):
    """`Node "mountplate"` inne i ett hierarkifalt ar en HANVISNING. Raknas
    den som en nod later den varje ram efter sig se okand ut."""
    kropp = (A.GRANSSNITT_MONTERING % {"namn": "Tool", "ram": "FlangeFrame",
                                       "mount": 1, "nod": "mountplate"}
             + A.RAM_BAR % {"namn": "Bas"})
    sokvag = A.skriv(tmp_path / "n.vcmx",
                     A.modelxml(Name="N", Type="Robots", Manufacturer="A"),
                     A.rsc("N", kropp))
    ram = {r.namn: r for r in K.las(sokvag, djupt=True).ramar}["Bas"]
    assert ram.harkomst == K.Harkomst.LAST


def test_en_ram_under_en_NOD_utan_offset_ger_saknas(tmp_path):
    """TRASIG FIXTUR, och den fangade ett verkligt overtramp.

    Forsta versionen svarade "ramen ligger i origo" for varje ram utan
    transformer ovanfor sig - aven for ramar som satt inne i en barnnod, dar
    nodens EGET lage inte star i filen. Det ar 7521 av 9824 ramar som fick ett
    lage de inte hade. Att en nod utan Offset skulle vara enhetsmatrisen ar en
    gissning, och en gissning som nastan alltid stammer ar precis den sorten.
    """
    inne = A.RAM_MATRIS % {"namn": "Inne", "x": 5.0, "y": 0.0, "z": 0.0}
    kropp = (A.RAM_MATRIS % {"namn": "Ute", "x": 1.0, "y": 2.0, "z": 3.0}
             + A.NOD_UTAN_OFFSET % {"nod": "Lank", "kropp": inne})
    sokvag = A.skriv(tmp_path / "n.vcmx",
                     A.modelxml(Name="N", Type="Machines", Manufacturer="A"),
                     A.rsc("N", kropp))
    ramar = {r.namn: r for r in K.las(sokvag, djupt=True).ramar}
    assert ramar["Ute"].harkomst == K.Harkomst.LAST
    assert ramar["Ute"].lage_mm == (1.0, 2.0, 3.0)
    assert ramar["Inne"].harkomst == K.Harkomst.SAKNAS
    assert ramar["Inne"].lage_mm is None
    assert "utan Offset" in (ramar["Inne"].uttryck or "")


def test_en_ram_under_en_nod_med_uttrycksoffset_ger_saknas(tmp_path):
    inne = A.RAM_MATRIS % {"namn": "Inne", "x": 5.0, "y": 0.0, "z": 0.0}
    kropp = A.NOD_MED_UTTRYCK % {"nod": "Lank", "kropp": inne}
    sokvag = A.skriv(tmp_path / "n.vcmx",
                     A.modelxml(Name="N", Type="Machines", Manufacturer="A"),
                     A.rsc("N", kropp))
    ram = K.las(sokvag, djupt=True).ramar[0]
    assert ram.harkomst == K.Harkomst.SAKNAS
    assert ram.uttryck == "Tx(BaseLength)"


def test_en_ram_utan_nagot_ovanfor_sig_ligger_i_komponentens_origo(tmp_path):
    kropp = 'Feature "rFrameFeature"\n{\nName "Bas"\n\nVisible 1\n}\n'
    sokvag = A.skriv(tmp_path / "n.vcmx",
                     A.modelxml(Name="N", Type="Machines", Manufacturer="A"),
                     A.rsc("N", kropp))
    ram = K.las(sokvag, djupt=True).ramar[0]
    assert ram.harkomst == K.Harkomst.LAST
    assert ram.lage_mm == (0.0, 0.0, 0.0)


def test_geometri_under_en_nod_utan_offset_ar_inte_konstant(tmp_path):
    inne = A.GEO_KONSTANT % {"namn": "inne", "uri": "geo-1"}
    kropp = A.NOD_UTAN_OFFSET % {"nod": "Lank", "kropp": inne}
    sokvag = A.skriv(tmp_path / "g.vcmx",
                     A.modelxml(Name="G", Type="Machines", Manufacturer="A"),
                     A.rsc("G", kropp),
                     {"geo-1": A.tds_geometri([(0.0, 0.0, 0.0)])})
    g = K.las(sokvag, djupt=True).geometri[0]
    assert g.placering == K.Geometri.UTTRYCK


def test_lederna_bar_namn_typ_och_granser(tmp_path):
    kropp = (A.LED % {"namn": "Axis1", "sort": "Rotational",
                      "min": -230.0, "max": 230.0}
             + A.LED % {"namn": "Axis2", "sort": "Translational",
                        "min": 0.0, "max": 1200.0})
    sokvag = A.skriv(tmp_path / "r.vcmx",
                     A.modelxml(Name="R", Type="Robots", Manufacturer="A"),
                     A.rsc("R", kropp))
    leder = {l.namn: l for l in K.las(sokvag, djupt=True).leder}
    assert set(leder) == {"Axis1", "Axis2"}
    assert leder["Axis1"].sort == "Rotational"
    assert (leder["Axis2"].min_varde, leder["Axis2"].max_varde) == (0.0, 1200.0)


def test_grunt_lage_laser_inte_component_rsc(tmp_path):
    f = K.las(_band(tmp_path), djupt=False)
    assert f.namn == "Band" and f.kategori == "Conveyors"
    assert f.granssnitt == () and f.ramar == () and f.geometri == ()
    assert f.djupt is False


def test_svepet_skriver_ut_sin_namnare(tmp_path):
    filer = [_band(tmp_path, "B1"), _band(tmp_path, "B2")]
    r = K.svep(filer, geometri=True)
    assert r["namnare"] == 2 and r["lasta"] == 2
    assert r["lada_saknas"] == 2 and r["lada_last"] == 0
    assert r["granssnitt_totalt"] == 4


def test_svepet_raknar_en_olaslig_fil_i_stallet_for_att_tiga_bort_den(tmp_path):
    trasig = tmp_path / "trasig.vcmx"
    trasig.write_bytes(b"inte en zip")
    r = K.svep([_band(tmp_path), str(trasig)])
    assert r["namnare"] == 2 and r["lasta"] == 1
    assert len(r["olasliga"]) == 1
