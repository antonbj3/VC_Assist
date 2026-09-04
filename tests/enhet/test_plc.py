# -*- coding: utf-8 -*-
"""L1: signalkartan, grind 3, paketeringen och REST-klientens rena delar.

Inget här startar docker, öppnar en socket eller rör ett filsystem utanför
pytests tmp_path. Det är ett arkitekturkrav (95_testprotokoll.md: L0-L2 måste
gå att köra utan VC), och det gäller PLC-benet lika mycket: allt som kräver en
körande runtime hör till tests/protocol/fas6_plcbandet.md.

Regeln som styr filen är samma som för ST-lagret: **varje kontroll har en
trasig fixtur som måste fällas.** Sista provet kräver att tabellen täcker varje
kod i registret, så en ny kontroll utan trasigt fall bryter bygget (S2).
"""
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc import (Adress, Byggfel, Debugkarta,  # noqa: E402
                               FRAN_PLC, Grind3Rapport, KONTROLLER_PLC,
                               KartFel, Signal, Signalkarta, TILL_PLC, bruk,
                               granska, karta_av_rader, konfiguration,
                               konfigurationstext, las_adress, nodid,
                               skriv_arkiv, variabel)
from vc_assist_svc.plc import openplc as O  # noqa: E402
from vc_assist_svc.plc import paket as P  # noqa: E402
from vc_assist_svc.st import typer as T  # noqa: E402


# ---- fixturer ------------------------------------------------------------

def enkel_karta(station="Station1"):
    return karta_av_rader(station, [
        ("Givare", "Nara", "detektor", "BOOL", "TILL_PLC", "%IX0.0"),
        ("Band", "Drift", "band_pa", "BOOL", "FRAN_PLC", "%QX0.0"),
    ])


def pou(karta, kropp):
    return ("PROGRAM %s\n" % karta.station) + karta.deklarationstext() \
        + kropp + "END_PROGRAM\n"


# ---- adresser ------------------------------------------------------------

GILTIGA_ADRESSER = [
    ("%IX0.0", "I", "X", 0, 0),
    ("%QX1023.7", "Q", "X", 1023, 7),
    ("%IB12", "I", "B", 12, None),
    ("%QW3", "Q", "W", 3, None),
    ("%QD0", "Q", "D", 0, None),
    ("%IL7", "I", "L", 7, None),
]

OGILTIGA_ADRESSER = [
    "IX0.0",        # inget procenttecken
    "%MX0.0",       # märkminne hör inte till en signalkarta
    "%IX0",         # bitadress utan bitindex
    "%IB0.1",       # bitindex på något som inte är en bit
    "%IX0.8",       # bitindex utanför bool_input[..][8]
    "%IX1024.0",    # index utanför BUFFER_SIZE
    "%IZ0",         # okänd storleksbokstav
    "",
]


@pytest.mark.parametrize("text,omrade,storlek,index,bit", GILTIGA_ADRESSER)
def test_giltig_adress_delas_i_sina_fyra_delar(text, omrade, storlek, index, bit):
    a = las_adress(text)
    assert (a.omrade, a.storlek, a.index, a.bit) == (omrade, storlek, index, bit)
    assert a.text() == text


@pytest.mark.parametrize("text", OGILTIGA_ADRESSER)
def test_ogiltig_adress_fals(text):
    with pytest.raises(KartFel):
        las_adress(text)


def test_platsen_skiljer_pa_storleksklasser():
    # MÄTT (image_tables.h): byte_input och int_input är skilda fält, så %IB0
    # och %IW0 delar inte minne. Två adresser krockar bara om alla fyra delar
    # är lika.
    assert las_adress("%IB0").plats() != las_adress("%IW0").plats()
    assert las_adress("%IX0.0").plats() != las_adress("%IX0.1").plats()
    assert las_adress("%IW3").plats() == las_adress("%IW3").plats()


# ---- signalen ------------------------------------------------------------

def test_signal_med_ratt_omrade_och_bredd_gar_igenom():
    s = karta_av_rader("S", [("K", "Sig", "t", "INT", "TILL_PLC", "%IW2")]).signaler[0]
    assert s.typ == T.Elementar("INT")
    assert not s.ar_utgang


OGILTIGA_SIGNALER = [
    # (skäl, rad)
    ("utsignal i %I", ("K", "S", "t", "BOOL", "FRAN_PLC", "%IX0.0")),
    ("insignal i %Q", ("K", "S", "t", "BOOL", "TILL_PLC", "%QX0.0")),
    ("BOOL på ordbredd", ("K", "S", "t", "BOOL", "TILL_PLC", "%IW0")),
    ("INT på bitbredd", ("K", "S", "t", "INT", "TILL_PLC", "%IX0.0")),
    ("REAL på ordbredd", ("K", "S", "t", "REAL", "TILL_PLC", "%IW0")),
    ("okänd riktning", ("K", "S", "t", "BOOL", "UPP", "%IX0.0")),
    ("taggnamn med bindestreck", ("K", "S", "t-1", "BOOL", "TILL_PLC", "%IX0.0")),
    ("taggnamn som börjar med siffra", ("K", "S", "1t", "BOOL", "TILL_PLC", "%IX0.0")),
    ("icke-elementär typ", ("K", "S", "t", "TON", "TILL_PLC", "%IX0.0")),
    ("icke-ASCII i komponent", ("Kå", "S", "t", "BOOL", "TILL_PLC", "%IX0.0")),
]


@pytest.mark.parametrize("skal,rad", OGILTIGA_SIGNALER,
                         ids=[s for s, _ in OGILTIGA_SIGNALER])
def test_ogiltig_signal_fals(skal, rad):
    with pytest.raises(KartFel):
        karta_av_rader("S", [rad])


def test_dubbel_tagg_fals_aven_i_annat_skiftlage():
    with pytest.raises(KartFel):
        karta_av_rader("S", [("K", "A", "ut", "BOOL", "FRAN_PLC", "%QX0.0"),
                             ("K", "B", "UT", "BOOL", "FRAN_PLC", "%QX0.1")])


def test_dubbel_adress_fals():
    with pytest.raises(KartFel):
        karta_av_rader("S", [("K", "A", "a", "BOOL", "FRAN_PLC", "%QX0.0"),
                             ("K", "B", "b", "BOOL", "FRAN_PLC", "%QX0.0")])


def test_dubbel_scensignal_fals():
    with pytest.raises(KartFel):
        karta_av_rader("S", [("K", "A", "a", "BOOL", "FRAN_PLC", "%QX0.0"),
                             ("K", "A", "b", "BOOL", "FRAN_PLC", "%QX0.1")])


def test_tomt_stationsnamn_fals():
    with pytest.raises(KartFel):
        Signalkarta("", ())


# ---- genererade deklarationer -------------------------------------------

GULD_DEKLARATIONER = """\
VAR
    detektor AT %IX0.0 : BOOL; (* Givare.Nara *)
    band_pa AT %QX0.0 : BOOL; (* Band.Drift *)
END_VAR
"""


def test_deklarationstexten_ar_ett_kontrakt():
    # Guldfil: samma karta ger byte-identisk text. En text som ändrar sig av
    # sig själv mäter ingenting (95_testprotokoll.md).
    assert enkel_karta().deklarationstext() == GULD_DEKLARATIONER


def test_deklarationstexten_ar_deterministisk_over_upprepade_anrop():
    k = enkel_karta()
    assert k.deklarationstext() == k.deklarationstext()


def test_skyddad_signal_far_sakerhetsmarke():
    k = karta_av_rader("S", [("K", "E", "nod_ok", "BOOL", "TILL_PLC",
                              "%IX0.7", True)])
    assert "{SAKERHET}" in k.deklarationstext()
    assert k.skyddade() == ("nod_ok",)


def test_utgangar_och_ingangar_delas_efter_riktning():
    k = enkel_karta()
    assert k.utgangar() == ("band_pa",)
    assert k.ingangar() == ("detektor",)


def test_programmet_lagger_kartans_block_forst():
    p = enkel_karta().program()
    assert p.block[0].deklarationer[0].namn == "detektor"
    assert p.sort == "PROGRAM"


# ---- JSON ----------------------------------------------------------------

def test_json_tur_och_retur():
    k = enkel_karta()
    igen = Signalkarta.las_text(k.text())
    assert igen == k
    assert igen.text() == k.text()


def test_json_fil_tur_och_retur(tmp_path):
    k = enkel_karta()
    fil = str(tmp_path / "karta.json")
    k.skriv_fil(fil)
    assert Signalkarta.las_fil(fil) == k


def test_okant_falt_i_json_avvisas():
    data = enkel_karta().till_json()
    data["signaler"][0]["riktnig"] = "TILL_PLC"      # stavfel
    with pytest.raises(KartFel):
        Signalkarta.fran_json(data)


def test_fel_formatversion_avvisas():
    data = enkel_karta().till_json()
    data["format"] = 99
    with pytest.raises(KartFel):
        Signalkarta.fran_json(data)


def test_trasig_json_avvisas():
    with pytest.raises(KartFel):
        Signalkarta.las_text("{ inte json")


# ---- grind 3: den gröna vägen -------------------------------------------

def test_grind3_slapper_igenom_kod_som_foljer_kartan():
    k = enkel_karta()
    dom = granska(pou(k, "    band_pa := detektor;\n"), k)
    assert dom.ok, str(dom)
    assert dom.anmarkningar == ()
    assert dom.st_rapport.ok


def test_grind3_slapper_utgang_som_skrivs_i_en_gren():
    k = enkel_karta()
    kropp = ("    IF detektor THEN\n        band_pa := TRUE;\n"
             "    ELSE\n        band_pa := FALSE;\n    END_IF;\n")
    assert granska(pou(k, kropp), k).ok


def test_grind3_ser_utgang_som_skrivs_via_utbindning():
    # Q => band_pa räknas som en skrivning, inte som en läsning.
    k = enkel_karta()
    kod = ("PROGRAM Station1\nVAR\n"
           "    detektor AT %IX0.0 : BOOL;\n"
           "    band_pa AT %QX0.0 : BOOL;\n"
           "    ur : TON;\nEND_VAR\n"
           "    ur(IN := detektor, PT := T#1s, Q => band_pa);\n"
           "END_PROGRAM\n")
    dom = granska(kod, k)
    assert dom.ok, str(dom)


def test_bruk_skiljer_last_fran_skrivet():
    k = enkel_karta()
    from vc_assist_svc.st import las
    p = las(pou(k, "    band_pa := detektor;\n")).pouer[0]
    lasta, skrivna = bruk(p)
    assert "DETEKTOR" in lasta and "DETEKTOR" not in skrivna
    assert "BAND_PA" in skrivna


# ---- grind 3: de trasiga fixturerna --------------------------------------
#
# En grind som aldrig fällt är oprövad (96_ingen_skuld.md, S2). Varje kod i
# KONTROLLER_PLC har en rad här, och sista provet kräver att tabellen är
# fullständig.

def _karta_med_ororad():
    return enkel_karta()


TRASIGA_FIXTURER = [
    # (kod, karta, källa)
    ("OLASLIG", enkel_karta(),
     "PROGRAM Station1\nVAR\n    a : INT\nEND_VAR\nEND_PROGRAM\n"),
    ("SAKNAD_POU", enkel_karta(),
     "PROGRAM NagonAnnan\nVAR\n    a : INT;\nEND_VAR\n    a := 1;\nEND_PROGRAM\n"),
    ("OKARTLAGD_TAGG", enkel_karta(),
     "PROGRAM Station1\nVAR\n"
     "    detektor AT %IX0.0 : BOOL;\n"
     "    band_pa AT %QX0.0 : BOOL;\n"
     "    gripare AT %QX0.5 : BOOL;\nEND_VAR\n"
     "    band_pa := detektor;\n    gripare := detektor;\nEND_PROGRAM\n"),
    ("SAKNAD_DEKLARATION", enkel_karta(),
     "PROGRAM Station1\nVAR\n"
     "    detektor AT %IX0.0 : BOOL;\n"
     "    hjalp : BOOL;\nEND_VAR\n"
     "    hjalp := detektor;\nEND_PROGRAM\n"),
    ("AVVIKANDE_DEKLARATION", enkel_karta(),
     "PROGRAM Station1\nVAR\n"
     "    detektor AT %IX0.0 : BOOL;\n"
     "    band_pa AT %QX0.3 : BOOL;\nEND_VAR\n"
     "    band_pa := detektor;\nEND_PROGRAM\n"),
    ("ORORD_SIGNAL", enkel_karta(),
     "PROGRAM Station1\nVAR\n"
     "    detektor AT %IX0.0 : BOOL;\n"
     "    band_pa AT %QX0.0 : BOOL;\nEND_VAR\n"
     "    band_pa := TRUE;\nEND_PROGRAM\n"),
    ("SKRIVEN_INGANG", enkel_karta(),
     "PROGRAM Station1\nVAR\n"
     "    detektor AT %IX0.0 : BOOL;\n"
     "    band_pa AT %QX0.0 : BOOL;\nEND_VAR\n"
     "    detektor := TRUE;\n    band_pa := detektor;\nEND_PROGRAM\n"),
    ("ODRIVEN_UTGANG", enkel_karta(),
     "PROGRAM Station1\nVAR\n"
     "    detektor AT %IX0.0 : BOOL;\n"
     "    band_pa AT %QX0.0 : BOOL;\n"
     "    hjalp : BOOL;\nEND_VAR\n"
     "    hjalp := detektor AND band_pa;\nEND_PROGRAM\n"),
]


@pytest.mark.parametrize("kod,karta,kalla", TRASIGA_FIXTURER,
                         ids=[k for k, _, _ in TRASIGA_FIXTURER])
def test_trasig_fixtur_falls_av_ratt_kontroll(kod, karta, kalla):
    dom = granska(kalla, karta)
    assert not dom.ok
    assert kod in dom.koder(), "väntade %s, fick %s" % (kod, dom.koder())


@pytest.mark.parametrize("kod,karta,kalla", TRASIGA_FIXTURER,
                         ids=[k for k, _, _ in TRASIGA_FIXTURER])
def test_varje_anmarkning_bar_sin_felklass(kod, karta, kalla):
    for a in granska(kalla, karta).anmarkningar:
        assert a.kod in KONTROLLER_PLC
        assert a.felklass in ("F1", "F3", "F4", None)
        assert str(a).startswith("rad ")


def test_registret_har_en_trasig_fixtur_per_kontroll():
    tackta = set(k for k, _, _ in TRASIGA_FIXTURER)
    assert tackta == set(KONTROLLER_PLC), \
        "utan trasig fixtur: %s" % (set(KONTROLLER_PLC) - tackta)


def test_avvikande_typ_falls():
    k = enkel_karta()
    kod = ("PROGRAM Station1\nVAR\n"
           "    detektor AT %IX0.0 : BOOL;\n"
           "    band_pa AT %QW0 : INT;\n"
           "    hjalp : BOOL;\nEND_VAR\n"
           "    band_pa := 1;\n    hjalp := detektor;\nEND_PROGRAM\n")
    assert "AVVIKANDE_DEKLARATION" in granska(kod, k).koder()


def test_saknat_sakerhetsmarke_falls():
    k = karta_av_rader("Station1", [
        ("Nod", "Ok", "nod_ok", "BOOL", "TILL_PLC", "%IX0.7", True),
        ("Band", "Drift", "band_pa", "BOOL", "FRAN_PLC", "%QX0.0")])
    kod = ("PROGRAM Station1\nVAR\n"
           "    nod_ok AT %IX0.7 : BOOL;\n"
           "    band_pa AT %QX0.0 : BOOL;\nEND_VAR\n"
           "    band_pa := nod_ok;\nEND_PROGRAM\n")
    assert "AVVIKANDE_DEKLARATION" in granska(kod, k).koder()


def test_grind2_far_kartans_skyddade_taggar():
    # Skrivning till en säkerhetsmärkt tagg ska fällas av ST-lagrets
    # SAKERHET-kontroll, som bara kan veta vilka taggarna är om kartan
    # lämnar dem. Grind 3 räknar inte om det måttet (I1).
    k = karta_av_rader("Station1", [
        ("Nod", "Ok", "nod_ok", "BOOL", "TILL_PLC", "%IX0.7", True),
        ("Band", "Drift", "band_pa", "BOOL", "FRAN_PLC", "%QX0.0")])
    kod = ("PROGRAM Station1\nVAR\n"
           "    nod_ok AT %IX0.7 : BOOL; {SAKERHET}\n"
           "    band_pa AT %QX0.0 : BOOL;\nEND_VAR\n"
           "    nod_ok := TRUE;\n    band_pa := nod_ok;\nEND_PROGRAM\n")
    dom = granska(kod, k)
    assert not dom.ok
    assert "SAKERHET" in dom.st_rapport.koder()


def test_grind3_kan_kora_utan_grind2():
    k = enkel_karta()
    dom = granska(pou(k, "    band_pa := detektor;\n"), k, aven_grind2=False)
    assert dom.ok
    assert dom.st_rapport is None


# ---- debugkartan ---------------------------------------------------------

DEBUGKARTA = {
    "version": 2, "md5": "abc",
    "leaves": [
        {"arrayIdx": 0, "elemIdx": 0, "path": "INST0.DETEKTOR",
         "type": "BOOL", "size": 1},
        {"arrayIdx": 0, "elemIdx": 1, "path": "INST0.BAND_PA",
         "type": "BOOL", "size": 1},
    ],
}


def test_debugkartan_slar_upp_tagg_oavsett_skiftlage():
    dk = Debugkarta.fran_json(DEBUGKARTA)
    lov = dk.for_tagg("band_pa")
    assert (lov.arr, lov.elem, lov.storlek) == (0, 1, 1)


def test_debugkartan_kastar_pa_okand_tagg():
    dk = Debugkarta.fran_json(DEBUGKARTA)
    with pytest.raises(Byggfel):
        dk.for_tagg("finns_inte")


def test_debugkarta_utan_leaves_avvisas():
    with pytest.raises(Byggfel):
        Debugkarta.fran_json({"version": 2})


# ---- OPC UA-konfigurationen ---------------------------------------------

def test_nodid_ar_platt_och_genererat():
    assert nodid("Station1", "band_pa") == "PLC.Station1.band_pa"


def test_konfigurationen_har_en_variabel_per_signal():
    k = enkel_karta()
    dk = Debugkarta.fran_json(DEBUGKARTA)
    konf = konfiguration(k, dk, "opc.tcp://127.0.0.1:4840/openplc/opcua")
    variabler = konf[0]["config"]["address_space"]["variables"]
    assert [v["browse_name"] for v in variabler] == ["detektor", "band_pa"]
    assert konf[0]["config"]["format_version"] == 2
    assert konf[0]["protocol"] == "OPC-UA"
    assert konf[0]["config"]["users"] == []


def test_utgang_ar_skrivskyddad_for_klienten():
    # En OPC UA-klient som kan skriva PLC:ns utgång styr scenen förbi PLC:n,
    # och då mäter ögat en sekvens som PLC:n aldrig körde.
    k = enkel_karta()
    dk = Debugkarta.fran_json(DEBUGKARTA)
    variabler = konfiguration(k, dk, "opc.tcp://x:4840/y")[0]["config"]["address_space"]["variables"]
    ut = [v for v in variabler if v["browse_name"] == "band_pa"][0]
    inn = [v for v in variabler if v["browse_name"] == "detektor"][0]
    assert set(ut["permissions"].values()) == {"r"}
    assert inn["permissions"]["engineer"] == "rw"


def test_skyddad_ingang_ar_skrivskyddad():
    k = karta_av_rader("Station1", [
        ("Nod", "Ok", "nod_ok", "BOOL", "TILL_PLC", "%IX0.7", True)])
    dk = Debugkarta.fran_json({"version": 2, "md5": "", "leaves": [
        {"arrayIdx": 0, "elemIdx": 0, "path": "INST0.NOD_OK",
         "type": "BOOL", "size": 1}]})
    v = konfiguration(k, dk, "opc.tcp://x:4840/y")[0]["config"]["address_space"]["variables"][0]
    assert set(v["permissions"].values()) == {"r"}


def test_typkonflikt_mellan_karta_och_kompilator_falls():
    k = enkel_karta()
    trasig = {"version": 2, "md5": "", "leaves": [
        {"arrayIdx": 0, "elemIdx": 0, "path": "INST0.DETEKTOR",
         "type": "INT", "size": 2},
        {"arrayIdx": 0, "elemIdx": 1, "path": "INST0.BAND_PA",
         "type": "BOOL", "size": 1}]}
    with pytest.raises(Byggfel):
        konfiguration(k, Debugkarta.fran_json(trasig), "opc.tcp://x:4840/y")


def test_tom_karta_ger_ingen_konfiguration():
    with pytest.raises(Byggfel):
        konfiguration(Signalkarta("S", ()), Debugkarta.fran_json(DEBUGKARTA),
                      "opc.tcp://x:4840/y")


# ---- paketet -------------------------------------------------------------

def test_konfigurationstexten_bar_instans_och_intervall():
    text = konfigurationstext("Station1")
    assert "PROGRAM Inst0 WITH Main : Station1;" in text
    assert P.TASKINTERVALL in text


def _lagg(katalog, namn, innehall="x"):
    full = os.path.join(katalog, namn)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(innehall)


def test_arkivet_kraver_de_tre_filerna_runtimen_kontrollerar(tmp_path):
    katalog = str(tmp_path)
    _lagg(katalog, "generated.cpp")
    zipvag = os.path.join(katalog, "projekt.zip")
    # Mätt: utan generated.hpp avbryter compile.sh, utan generated_debug.cpp
    # laddas .so:n inte, utan defines.h hittar make inget mål.
    with pytest.raises(Byggfel):
        skriv_arkiv(katalog, zipvag)
    _lagg(katalog, "generated.hpp")
    with pytest.raises(Byggfel):
        skriv_arkiv(katalog, zipvag)
    _lagg(katalog, "generated_debug.cpp")
    with pytest.raises(Byggfel):
        skriv_arkiv(katalog, zipvag)
    _lagg(katalog, "defines.h")
    poster = skriv_arkiv(katalog, zipvag)
    assert "generated.hpp" in poster and "defines.h" in poster


def test_arkivet_utelamnar_byggets_egna_filer(tmp_path):
    katalog = str(tmp_path)
    for namn in ("generated.cpp", "generated.hpp", "generated_debug.cpp",
                 "defines.h", "debug-map.json", "program.st"):
        _lagg(katalog, namn)
    _lagg(katalog, os.path.join("conf", "opcua.json"), "[]")
    poster = skriv_arkiv(katalog, os.path.join(katalog, "projekt.zip"))
    assert "debug-map.json" not in poster
    assert "program.st" not in poster
    assert os.path.join("conf", "opcua.json") in poster


def test_kompilera_utan_strucpp_paket_falls(tmp_path):
    with pytest.raises(Byggfel):
        P.kompilera("PROGRAM P\nEND_PROGRAM\n", str(tmp_path / "ut"),
                    str(tmp_path / "finns-inte"))


# ---- REST-klientens rena delar ------------------------------------------

@pytest.mark.parametrize("in_,ut", [
    ("STATUS:RUNNING", "RUNNING"),
    ("START:OK", "OK"),
    ("PING:OK", "OK"),
    ("RUNNING", "RUNNING"),
    ("", ""),
    (None, ""),
])
def test_prefixet_skalas_av_runtimens_svar(in_, ut):
    assert O._efter_kolon(in_) == ut


def test_osignerat_certifikat_kraver_uttryckligt_val():
    # Runtimen genererar ett självsignerat certifikat. Att strunta i
    # verifieringen får aldrig vara det tysta standardvalet.
    strikt = O.OpenPlcV4("https://x", "a", "b")
    slapp = O.OpenPlcV4("https://x", "a", "b", tillat_osignerat=True)
    assert strikt._ssl.verify_mode != slapp._ssl.verify_mode


def test_klienten_kastar_nar_adressen_inte_gar_att_na():
    # Ingen nätverkstrafik: porten är stängd, felet kommer ur anslutningen.
    k = O.OpenPlcV4("https://127.0.0.1:1", "a", "b", tillat_osignerat=True,
                    tidsgrans=1.0)
    with pytest.raises(O.OpenPlcFel):
        k.version()


def test_sakerhetspragmat_skalas_av_pa_vagen_till_kompilatorn():
    # MÄTT: STruC++ 0.6.6 avvisar IEC-pragmaklamrar med
    # "unexpected character: ->{<-". Märket hör till grind 2 och 3, inte till
    # kodgenereringen, så det skalas av — och bara exakt den strängen.
    k = karta_av_rader("S", [("Nod", "Ok", "nod_ok", "BOOL", "TILL_PLC",
                              "%IX0.7", True)])
    text = k.deklarationstext()
    assert "{SAKERHET}" in text
    assert "{" not in P.for_kompilator(text)
    # Allt annat står kvar, tecken för tecken.
    assert "nod_ok AT %IX0.7 : BOOL;" in P.for_kompilator(text)


def test_for_kompilator_ror_inte_kod_utan_pragma():
    text = enkel_karta().deklarationstext()
    assert P.for_kompilator(text) == text
