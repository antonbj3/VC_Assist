# -*- coding: utf-8 -*-
"""L1: ST-validatorns tolv kontroller, båda riktningarna.

Regeln som styr filen: **varje kontroll har en trasig fixtur som måste
fällas, och en lagad fixtur som måste släppas igenom.** En grind som aldrig
fällt är oprövad (95_testprotokoll.md), och en grind som fäller allt är precis
lika värdelös som en som godkänner allt — båda ser bra ut om man bara räknar
fällningar.

Tabellen TRASIGA_FIXTURER är protokollets egen "trasig fixtur"-lista i körbar
form. Sista provet i filen kräver att den täcker varje kontroll som finns i
registret, så en ny kontroll utan trasig fixtur bryter bygget.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import (KONTROLLER, Deklaration, Literal, Namn,  # noqa: E402
                              Sekvens, Steg, Tilldelning, Varblock, bygg_text,
                              far_tilldelas, validera)
from vc_assist_svc.st import typer as T  # noqa: E402


def _pou(dekl, kropp, extra=""):
    return "PROGRAM P\n%sVAR\n%sEND_VAR\n%sEND_PROGRAM\n" % (extra, dekl, kropp)


# ---- de tolv kontrollerna, en trasig och en lagad fixtur var --------------

TRASIGA_FIXTURER = [
    ("BALANS",
     _pou(" a : INT;\n", " IF a = 1 THEN\n  a := 2;\n")),
    ("SYNTAX",
     _pou(" a : INT;\n", " a := ;\n")),
    ("TIDLITERAL",
     _pou(" ur : TON;\n", " ur(IN := TRUE, PT := T#500);\n")),
    ("ODEKLARERAD",
     _pou(" a : INT;\n", " a := b + 1;\n")),
    ("DUBBELDEKLARATION",
     _pou(" a : INT;\n a : BOOL;\n", " a := 1;\n")),
    ("OKANT_NAMN",
     _pou(" ur : TON;\n", " ur(IN := TRUE, PT := T#1s);\n b := ur.Klar;\n",
          extra="VAR_OUTPUT\n b : BOOL;\nEND_VAR\n")),
    ("ARGUMENT",
     _pou(" ur : TON;\n", " ur(IN := TRUE, PZ := T#1s);\n")),
    ("TYP",
     _pou(" a : INT;\n", " a := 1.5;\n")),
    ("RIKTNING",
     _pou(" a : INT;\n", " inn := 3;\n", extra="VAR_INPUT\n inn : INT;\nEND_VAR\n")),
    ("DUBBELSKRIVNING",
     _pou(" a : INT;\n",
          " IF a = 1 THEN\n  ut := TRUE;\n END_IF;\n"
          " IF a = 2 THEN\n  ut := FALSE;\n END_IF;\n",
          extra="VAR_OUTPUT\n ut : BOOL;\nEND_VAR\n")),
    ("OATKOMLIG",
     _pou(" a : INT;\n", " RETURN;\n a := 1;\n")),
    ("SAKERHET",
     _pou(" a : INT;\n", " nod := FALSE;\n",
          extra="VAR_INPUT\n nod AT %IX0.0 : BOOL; {SAKERHET}\nEND_VAR\n")),
]

LAGADE_FIXTURER = [
    ("BALANS",
     _pou(" a : INT;\n", " IF a = 1 THEN\n  a := 2;\n END_IF;\n")),
    ("SYNTAX",
     _pou(" a : INT;\n", " a := 1;\n")),
    ("TIDLITERAL",
     _pou(" ur : TON;\n", " ur(IN := TRUE, PT := T#500ms);\n")),
    ("ODEKLARERAD",
     _pou(" a : INT;\n b : INT;\n", " a := b + 1;\n")),
    ("DUBBELDEKLARATION",
     _pou(" a : INT;\n b : BOOL;\n", " a := 1;\n b := TRUE;\n")),
    ("OKANT_NAMN",
     _pou(" ur : TON;\n", " ur(IN := TRUE, PT := T#1s);\n b := ur.Q;\n",
          extra="VAR_OUTPUT\n b : BOOL;\nEND_VAR\n")),
    ("ARGUMENT",
     _pou(" ur : TON;\n", " ur(IN := TRUE, PT := T#1s);\n")),
    ("TYP",
     _pou(" a : REAL;\n", " a := 1.5;\n")),
    ("RIKTNING",
     _pou(" a : INT;\n", " a := inn;\n", extra="VAR_INPUT\n inn : INT;\nEND_VAR\n")),
    ("DUBBELSKRIVNING",
     _pou(" a : INT;\n",
          " IF a = 1 THEN\n  ut := TRUE;\n ELSIF a = 2 THEN\n  ut := FALSE;\n"
          " END_IF;\n",
          extra="VAR_OUTPUT\n ut : BOOL;\nEND_VAR\n")),
    ("OATKOMLIG",
     _pou(" a : INT;\n", " a := 1;\n RETURN;\n")),
    ("SAKERHET",
     _pou(" a : INT;\n", " IF nod THEN\n  a := 1;\n END_IF;\n",
          extra="VAR_INPUT\n nod AT %IX0.0 : BOOL; {SAKERHET}\nEND_VAR\n")),
]


@pytest.mark.parametrize("kod,kalla", TRASIGA_FIXTURER,
                         ids=[k for k, _ in TRASIGA_FIXTURER])
def test_trasig_fixtur_falls_av_ratt_kontroll(kod, kalla):
    r = validera(kalla)
    assert r.ok is False, "fixturen for %s slapptes igenom" % kod
    assert kod in r.koder(), "%s fastnade som %s: %s" % (kod, r.koder(), r)
    assert all(a.text for a in r.anmarkningar), "en dom maste saga VARFOR"


@pytest.mark.parametrize("kod,kalla", LAGADE_FIXTURER,
                         ids=[k for k, _ in LAGADE_FIXTURER])
def test_lagad_fixtur_slapps_igenom(kod, kalla):
    r = validera(kalla)
    assert r.ok is True, "den lagade fixturen for %s fastnade: %s" % (kod, r)


def test_varje_kontroll_i_registret_har_en_trasig_fixtur():
    """S2 i 96_ingen_skuld.md: en detektor som inte kan fyra är ett fel."""
    tackta = set(kod for kod, _kalla in TRASIGA_FIXTURER)
    assert tackta == set(KONTROLLER), (
        "kontroller utan trasig fixtur: %s" % sorted(set(KONTROLLER) - tackta))
    assert set(kod for kod, _k in LAGADE_FIXTURER) == set(KONTROLLER)


# ---- typreglerna ---------------------------------------------------------
#
# Vidgning är tillåten bara när den är bevisat förlustfri. REAL har 24 bitars
# mantissa (IEEE 754), så DINT ryms inte, och det är hela skillnaden mellan
# INT -> REAL och DINT -> REAL nedan.

TILLATNA = [
    ("INT", "INT"), ("DINT", "INT"), ("LINT", "DINT"), ("REAL", "INT"),
    ("LREAL", "DINT"), ("LREAL", "REAL"), ("DINT", "UINT"), ("WORD", "BYTE"),
]
FORBJUDNA = [
    ("INT", "DINT"), ("REAL", "DINT"), ("INT", "REAL"), ("BOOL", "INT"),
    ("INT", "BOOL"), ("TIME", "DINT"), ("DINT", "TIME"), ("BYTE", "WORD"),
    ("INT", "WORD"), ("WORD", "INT"),
]


@pytest.mark.parametrize("mal,kalla", TILLATNA)
def test_forlustfri_vidgning_ar_tillaten(mal, kalla):
    ok, skal = far_tilldelas(T.Elementar(mal), T.Elementar(kalla))
    assert ok is True, "%s := %s nekades: %s" % (mal, kalla, skal)


@pytest.mark.parametrize("mal,kalla", FORBJUDNA)
def test_konvertering_som_kan_tappa_data_nekas(mal, kalla):
    ok, skal = far_tilldelas(T.Elementar(mal), T.Elementar(kalla))
    assert ok is False, "%s := %s slapptes igenom" % (mal, kalla)
    assert skal


def test_heltalsliteral_utanfor_maltypens_intervall_falls():
    assert validera(_pou(" a : INT;\n", " a := 40000;\n")).koder() == ("TYP",)
    assert validera(_pou(" a : DINT;\n", " a := 40000;\n")).ok is True


def test_strang_som_kan_huggas_av_falls():
    assert validera(_pou(" a : STRING[4];\n", " a := 'abcdefg';\n")).koder() == ("TYP",)
    assert validera(_pou(" a : STRING[8];\n", " a := 'abcdefg';\n")).ok is True


def test_blandade_typer_i_uttryck_kraver_uttrycklig_konvertering():
    dekl = " a : REAL;\n b : DINT;\n"
    assert validera(_pou(dekl, " a := b * 2;\n")).koder() == ("TYP",)
    assert validera(_pou(dekl, " a := DINT_TO_REAL(b) * 2.0;\n")).ok is True


def test_tidsaritmetik_foljer_iec():
    dekl = " t : TIME;\n n : INT;\n"
    assert validera(_pou(dekl, " t := t + T#1s;\n")).ok is True
    assert validera(_pou(dekl, " t := t * n;\n")).ok is True
    assert validera(_pou(dekl, " t := t + n;\n")).koder() == ("TYP",)


def test_villkor_maste_vara_booleskt():
    assert validera(_pou(" a : INT;\n", " IF a THEN\n  a := 1;\n END_IF;\n")
                    ).koder() == ("TYP",)
    assert validera(_pou(" a : INT;\n", " IF a = 1 THEN\n  a := 1;\n END_IF;\n")
                    ).ok is True


def test_falt_kraver_ratt_antal_index_och_heltalsindex():
    dekl = " f : ARRAY [1..3] OF INT;\n i : INT;\n r : REAL;\n"
    assert validera(_pou(dekl, " f[1] := 2;\n")).ok is True
    assert validera(_pou(dekl, " f[i, 2] := 2;\n")).koder() == ("TYP",)
    assert validera(_pou(dekl, " f[r] := 2;\n")).koder() == ("TYP",)
    assert "TYP" in validera(_pou(dekl, " f[9] := 2;\n")).koder()


def test_egen_struktur_gar_att_lasa_och_okant_falt_falls():
    typdel = ("TYPE\n Recept : STRUCT\n  antal : INT;\n END_STRUCT;\nEND_TYPE\n\n")
    bra = typdel + _pou(" r : Recept;\n a : INT;\n", " a := r.antal;\n")
    fel = typdel + _pou(" r : Recept;\n a : INT;\n", " a := r.mangd;\n")
    assert validera(bra).ok is True, validera(bra)
    assert validera(fel).koder() == ("OKANT_NAMN",)


# ---- dubbelskrivning, gränsfallen ---------------------------------------

def _med_utgang(kropp):
    return _pou(" a : INT;\n", kropp, extra="VAR_OUTPUT\n ut : BOOL;\nEND_VAR\n")


def test_ovillkorlig_grundskrivning_plus_ett_undantag_ar_normal_kod():
    """`ut := FALSE;` följt av ett villkorat `ut := TRUE;` är avsiktligt och
    entydigt: sist skriven vinner, och ordningen syns i koden."""
    r = validera(_med_utgang(" ut := FALSE;\n IF a = 1 THEN\n  ut := TRUE;\n END_IF;\n"))
    assert r.ok is True, str(r)


def test_tva_villkorade_skrivningar_ar_dubbelskrivning():
    r = validera(_med_utgang(" IF a = 1 THEN\n  ut := TRUE;\n END_IF;\n"
                             " IF a = 2 THEN\n  ut := FALSE;\n END_IF;\n"))
    assert r.koder() == ("DUBBELSKRIVNING",)


def test_ovillkorlig_skrivning_efter_villkorad_falls_som_verkningslos():
    r = validera(_med_utgang(" IF a = 1 THEN\n  ut := TRUE;\n END_IF;\n"
                             " ut := FALSE;\n"))
    assert r.koder() == ("DUBBELSKRIVNING",)
    assert "verkningslos" in r.anmarkningar[0].text.replace("ö", "o")


def test_tva_ovillkorliga_skrivningar_falls():
    r = validera(_med_utgang(" ut := TRUE;\n ut := FALSE;\n"))
    assert r.koder() == ("DUBBELSKRIVNING",)


def test_grenar_som_utesluter_varandra_ar_ingen_dubbelskrivning():
    assert validera(_med_utgang(
        " IF a = 1 THEN\n  ut := TRUE;\n ELSE\n  ut := FALSE;\n END_IF;\n")).ok is True
    assert validera(_med_utgang(
        " CASE a OF\n 1:\n  ut := TRUE;\n 2:\n  ut := FALSE;\n"
        " ELSE\n  ut := FALSE;\n END_CASE;\n")).ok is True


def test_mellanlagring_som_inte_ar_utgang_raknas_inte():
    """Kontrollen letar efter den klassiska buggen 'två ställen driver samma
    utgång'. En arbetsvariabel som skrivs om är normal kod."""
    assert validera(_pou(" a : INT;\n b : INT;\n",
                         " a := 1;\n b := a;\n a := 2;\n b := a;\n")).ok is True


def test_utgang_via_signalkartan_raknas_ocksa():
    """En variabel med %Q-adress är en utgång även utan VAR_OUTPUT."""
    kalla = _pou(" a : INT;\n lampa AT %QX0.3 : BOOL;\n",
                 " IF a = 1 THEN\n  lampa := TRUE;\n END_IF;\n"
                 " IF a = 2 THEN\n  lampa := FALSE;\n END_IF;\n")
    assert validera(kalla).koder() == ("DUBBELSKRIVNING",)


def test_utgangsbindning_med_pil_raknas_som_skrivning():
    kalla = _pou(" a : INT;\n vippa : R_TRIG;\n",
                 " IF a = 2 THEN\n  ut := FALSE;\n END_IF;\n"
                 " vippa(CLK := a = 1, Q => ut);\n",
                 extra="VAR_OUTPUT\n ut : BOOL;\nEND_VAR\n")
    assert validera(kalla).koder() == ("DUBBELSKRIVNING",)


# ---- oåtkomlig kod -------------------------------------------------------

def test_kod_efter_exit_i_slinga_ar_oatkomlig():
    r = validera(_pou(" a : INT;\n",
                      " WHILE a < 3 DO\n  EXIT;\n  a := a + 1;\n END_WHILE;\n"))
    assert r.koder() == ("OATKOMLIG",)


def test_alltid_falskt_villkor_falls():
    assert validera(_pou(" a : INT;\n",
                         " IF FALSE THEN\n  a := 1;\n END_IF;\n")
                    ).koder() == ("OATKOMLIG",)
    assert validera(_pou(" a : INT;\n b : BOOL;\n",
                         " IF b THEN\n  a := 1;\n END_IF;\n")).ok is True


def test_gren_efter_alltid_sant_villkor_falls():
    r = validera(_pou(" a : INT;\n",
                      " IF TRUE THEN\n  a := 1;\n ELSE\n  a := 2;\n END_IF;\n"))
    assert r.koder() == ("OATKOMLIG",)


def test_dubblerad_case_etikett_falls_och_pekar_ut_den_tidigare_grenen():
    r = validera(_pou(" a : INT;\n b : INT;\n",
                      " CASE a OF\n 1..3:\n  b := 1;\n 2:\n  b := 2;\n"
                      " END_CASE;\n"))
    assert r.koder() == ("OATKOMLIG",)
    assert "2" in r.anmarkningar[0].text


def test_exit_utanfor_slinga_falls():
    assert validera(_pou(" a : INT;\n", " EXIT;\n")).koder() == ("SYNTAX",)


# ---- namn, anrop och riktning -------------------------------------------

def test_uppfunnen_funktion_ar_ett_hart_fel():
    """I9: uppfunnet API-namn är ett hårt fel, inte en varning."""
    assert validera(_pou(" a : INT;\n", " a := SUPERMAX(1, 2);\n")
                    ).koder() == ("OKANT_NAMN",)
    assert validera(_pou(" a : INT;\n", " a := MAX(1, 2);\n")).ok is True


def test_okand_blocktyp_i_deklarationen_falls():
    assert validera(_pou(" ur : TIMER_XYZ;\n", " a := 1;\n",
                         extra="VAR\n a : INT;\nEND_VAR\n")
                    ).koder() == ("OKANT_NAMN",)


def test_blocktypen_kan_inte_anropas_utan_instans():
    assert validera(_pou(" a : INT;\n", " TON(IN := TRUE, PT := T#1s);\n")
                    ).koder() == ("OKANT_NAMN",)


def test_blockinstans_i_uttryck_falls():
    r = validera(_pou(" ur : TON;\n b : BOOL;\n", " b := ur(IN := TRUE);\n"))
    assert r.koder() == ("TYP",)


def test_funktion_som_saknar_argument_falls():
    assert validera(_pou(" a : INT;\n", " a := MAX(1);\n")).koder() == ("ARGUMENT",)


def test_blandade_namngivna_och_positionella_argument_falls():
    assert "ARGUMENT" in validera(_pou(" ur : TON;\n",
                                       " ur(TRUE, PT := T#1s);\n")).koder()


def test_funktionsblock_i_samma_fil_gar_att_anropa():
    kalla = ("FUNCTION_BLOCK Kvitto\nVAR_INPUT\n inn : BOOL;\nEND_VAR\n"
             "VAR_OUTPUT\n ut : BOOL;\nEND_VAR\n ut := inn;\nEND_FUNCTION_BLOCK\n\n"
             "PROGRAM P\nVAR\n k : Kvitto;\n b : BOOL;\nEND_VAR\n"
             " k(inn := TRUE);\n b := k.ut;\nEND_PROGRAM\n")
    assert validera(kalla).ok is True, validera(kalla)


def test_okand_anslutning_pa_eget_funktionsblock_falls():
    kalla = ("FUNCTION_BLOCK Kvitto\nVAR_INPUT\n inn : BOOL;\nEND_VAR\n"
             "VAR_OUTPUT\n ut : BOOL;\nEND_VAR\n ut := inn;\nEND_FUNCTION_BLOCK\n\n"
             "PROGRAM P\nVAR\n k : Kvitto;\n b : BOOL;\nEND_VAR\n"
             " k(fel := TRUE);\n b := k.ut;\nEND_PROGRAM\n")
    assert validera(kalla).koder() == ("ARGUMENT",)


def test_skrivning_till_konstant_falls():
    assert validera("PROGRAM P\nVAR CONSTANT\n k : INT := 3;\nEND_VAR\n"
                    " k := 4;\nEND_PROGRAM\n").koder() == ("RIKTNING",)


def test_skrivning_till_styrvariabel_i_for_falls():
    r = validera(_pou(" i : INT;\n a : INT;\n",
                      " FOR i := 1 TO 3 DO\n  i := 9;\n END_FOR;\n a := i;\n"))
    assert r.koder() == ("RIKTNING",)


def test_lasning_av_sakerhetstagg_ar_tillaten_men_skrivning_inte():
    """I15: genererad logik får ligga bredvid säkerheten och vara förreglad av
    den. Läsa: ja. Skriva: aldrig."""
    extra = "VAR_INPUT\n nod AT %IX0.0 : BOOL; {SAKERHET}\nEND_VAR\n"
    assert validera(_pou(" a : INT;\n", " IF nod THEN\n  a := 1;\n END_IF;\n",
                         extra=extra)).ok is True
    assert "SAKERHET" in validera(_pou(" a : INT;\n", " nod := TRUE;\n",
                                       extra=extra)).koder()


def test_skyddade_namn_kan_ocksa_komma_utifran_signalkartan():
    kalla = ("VAR_GLOBAL\n ljusridan : BOOL;\nEND_VAR\n\n"
             + _pou(" a : INT;\n", " ljusridan := FALSE;\n"))
    assert validera(kalla).ok is True, "utan markning ar det en vanlig global"
    r = validera(kalla, skyddade=("ljusridan",))
    assert "SAKERHET" in r.koder()


def test_externa_namn_ur_signalkartan_raknas_som_deklarerade():
    kalla = _pou(" a : INT;\n", " a := givare;\n")
    assert validera(kalla).koder() == ("ODEKLARERAD",)
    assert validera(kalla, externa={"givare": T.Elementar("INT")}).ok is True


def test_extern_utgang_far_skrivas_och_dubbelskrivs_den_falls():
    """Deklarationsdelen kan ligga i en annan fil (I10). Då kommer namnen in
    som externa, och en extern utgång är fortfarande en utgång."""
    skriv = _pou(" a : INT;\n", " ventil := TRUE;\n")
    assert validera(skriv, externa={"ventil": T.BOOL},
                    utgangar=("ventil",)).ok is True
    dubbelt = _pou(" a : INT;\n",
                   " IF a = 1 THEN\n  ventil := TRUE;\n END_IF;\n"
                   " IF a = 2 THEN\n  ventil := FALSE;\n END_IF;\n")
    r = validera(dubbelt, externa={"ventil": T.BOOL}, utgangar=("ventil",))
    assert r.koder() == ("DUBBELSKRIVNING",)


# ---- den genererade sekvensen som positivkontroll ------------------------

def test_genererad_sekvens_passerar_alla_kontroller():
    dekl = (Varblock("VAR_INPUT", (
                Deklaration("nodstopp_ok", T.BOOL, adress="%IX0.0", skyddad=True),
                Deklaration("start", T.BOOL, adress="%IX0.1"),
                Deklaration("klar", T.BOOL, adress="%IX0.2"))),
            Varblock("VAR_OUTPUT", (
                Deklaration("motor", T.BOOL, adress="%QX0.0"),)))
    spec = Sekvens(
        namn="Station", nodstopp="nodstopp_ok", start=Namn("start"),
        deklarationer=dekl,
        steg=(Steg("kor", (Tilldelning(Namn("motor"), Literal("BOOL", "TRUE", True)),),
                   villkor=Namn("klar"), uppehall="T#200ms", tidsgrans="T#30s"),
              Steg("vila", (Tilldelning(Namn("motor"), Literal("BOOL", "FALSE", False)),),
                   uppehall="T#1s")))
    r = validera(bygg_text(spec))
    assert r.ok is True, str(r)


# ---- M-51: standardbiblioteket och de två typreglerna som var fel --------

def test_sel_lamnar_typen_hos_det_valda_inte_hos_valjaren():
    """SEL(G, IN0, IN1) valdes med en BOOL och lamnade INT. Resultattypen
    raknades over ALLA argument, sa BOOL och INT skulle hitta en gemensam
    typ — och `SEL(bA, iB, iC)` fick 'ingen gemensam typ' fastan bada de
    valda var INT. MATT i M-51: STruC++ bygger den utan anmarkning."""
    dekl = " g : BOOL;\n a : INT;\n b : INT;\n ut : INT;\n"
    assert validera(_pou(dekl, " ut := SEL(g, a, b);\n")).ok is True
    # ... och valjaren maste fortfarande vara BOOL
    assert "TYP" in validera(_pou(dekl, " ut := SEL(a, a, b);\n")).koder()


def test_mux_valjer_med_ett_heltal_och_lamnar_de_valdas_typ():
    dekl = " k : INT;\n ut : BOOL;\n"
    assert validera(_pou(dekl, " ut := MUX(k, TRUE, FALSE);\n")).ok is True
    dekl2 = " k : INT;\n a : INT;\n b : INT;\n c : INT;\n ut : INT;\n"
    assert validera(_pou(dekl2, " ut := MUX(k, a, b, c);\n")).ok is True


def test_variadisk_styrs_av_signaturen_och_inte_av_namnet():
    """Argumentkontrollen slog upp namnen "MIN" och "MAX" for att veta om
    fler argument var tillatna. Varje ny variadisk funktion blev da ett tyst
    argumentfel tills nagon kom ihag att fylla pa listan — MUX och CONCAT var
    precis sadana."""
    dekl = " a : INT;\n b : INT;\n c : INT;\n ut : INT;\n"
    assert validera(_pou(dekl, " ut := MIN(a, b, c);\n")).ok is True
    assert validera(_pou(dekl, " ut := ADD(a, b, c);\n")).ok is True
    # en ICKE-variadisk funktion far fortfarande inte fler argument
    assert "ARGUMENT" in validera(_pou(dekl, " ut := ABS(a, b);\n")).koder()


NYA_ANROP = [
    (" r : REAL;\n", " r := SQRT(r) + LN(r) + EXP(r) + SIN(r) + COS(r);\n"),
    (" r : REAL;\n", " r := ATAN2(r, 1.0);\n"),
    (" r : REAL;\n", " r := EXPT(r, 2.0);\n"),
    (" a : INT;\n", " a := EXPT(a, 2);\n"),
    (" a : INT;\n b : INT;\n", " a := DIV(SUB(b, 1), 2);\n"),
    (" a : INT;\n b : BOOL;\n", " b := GT(a, 3);\n"),
    (" a : INT;\n", " a := MOVE(a);\n"),
    (" s : STRING;\n", " s := CONCAT(LEFT(s, 2), RIGHT(s, 2));\n"),
    (" s : STRING;\n a : INT;\n", " a := FIND(s, 'x');\n"),
    (" s : STRING;\n", " s := MID(s, 2, 1);\n"),
    (" t : TIME;\n b : BOOL;\n", " b := t > TIME();\n"),
]


@pytest.mark.parametrize("dekl,kropp", NYA_ANROP,
                         ids=[k.strip() for _d, k in NYA_ANROP])
def test_standardfunktionerna_som_var_okanda_namn_slapps_igenom(dekl, kropp):
    """Var och en av dem svarade OKANT_NAMN forut, och OKANT_NAMN ar F2 —
    samma dom som ett uppfunnet API-namn. Modellen fick alltsa hora att en
    standardfunktion inte fanns.

    Namnen ar inte valda ur en lista utan MATTA: test_st_svep_mot_strucpp
    bygger ett program som anropar varenda post i biblioteket och kraver att
    g++ lankar det. STruC++:s framande racker inte som facit — den slapper
    igenom HITTEPA(x) utan anmarkning."""
    r = validera(_pou(dekl, kropp))
    assert r.ok is True, str(r)


def test_ett_uppfunnet_namn_ar_fortfarande_ett_hart_fel():
    """Biblioteket vaxte; I9 gjorde det inte. Utan den har raden hade
    utvidgningen kunnat vara en oppning i stallet for en lagning."""
    r = validera(_pou(" a : INT;\n", " a := HITTEPA(a);\n"))
    assert r.koder() == ("OKANT_NAMN",)


def test_exponentoperatorn_har_basens_typ_och_kraver_tal():
    assert validera(_pou(" r : REAL;\n", " r := 2.0 ** 2;\n")).ok is True
    assert validera(_pou(" a : INT;\n", " a := a ** 2;\n")).ok is True
    r = validera(_pou(" a : INT;\n b : BOOL;\n", " a := b ** 2;\n"))
    assert "TYP" in r.koder()


def test_baserad_literal_med_typprefix_kontrolleras_mot_typen():
    """Formen gick inte att lasa alls forut. Nu lases den — och da maste den
    ocksa kontrolleras, annars vore lagningen en oppning."""
    assert validera(_pou(" w : WORD;\n", " w := WORD#16#FF;\n")).ok is True
    assert "TYP" in validera(_pou(" a : INT;\n",
                                  " a := INT#16#FFFF;\n")).koder()


def test_tolken_kan_rakna_exponentoperatorn_validatorn_slapper_igenom():
    """De tva motorerna far inte glida isar pa en NY operator.

    `**` lades till i lasaren och validatorn av M-51. En operator som
    validatorn slapper igenom men tolken kastar Tolkfel pa ar ett hal i den
    andra motorn: banken skulle godkanna koden och sedan inte kunna doma den.
    """
    from vc_assist_svc.st import tolk as tolkmodul
    kalla = ("PROGRAM P\nVAR\n a : INT;\n r : REAL;\nEND_VAR\n"
             " a := 2 ** 5;\n r := 2.0 ** 0.5;\nEND_PROGRAM\n")
    assert validera(kalla).ok is True, str(validera(kalla))
    t = tolkmodul.Tolk(kalla)
    t.scan()
    assert t.las("a") == 32
    assert abs(t.las("r") - 1.4142135623730951) < 1e-12


# ---- dubbelskrivning: bevisbart ofarliga fall ------------------------------

def _prog(kropp):
    return ("PROGRAM P\nVAR\n    ut AT %QX0.0 : BOOL;\n"
            "    a AT %IX0.0 : BOOL;\n    b AT %IX0.1 : BOOL;\n"
            "    n AT %QW0 : INT;\nEND_VAR\n" + kropp + "END_PROGRAM\n")


def _koder(kropp):
    from vc_assist_svc.st.validator import validera
    return [x.kod for x in validera(_prog(kropp)).anmarkningar]


def test_tva_villkorade_skrivningar_av_SAMMA_literal_ar_inte_dubbelskrivning():
    """Regelns eget skal ar att ordningen avgor. Samma varde: ingen ordning.

    Det ar dessutom standardmonstret for en forregling - berakna, sedan tvinga -
    och bankens egen referens for L-05 skriver ST260_LFT_DOWN pa tva rader, bada
    gangerna FALSE. Den fallningen var en falsk rod.
    """
    kod = ("    IF a THEN ut := FALSE; END_IF;\n"
           "    IF b THEN ut := FALSE; END_IF;\n")
    assert "DUBBELSKRIVNING" not in _koder(kod)


def test_tva_villkorade_skrivningar_av_OLIKA_literaler_falls():
    """Den trasiga fixturen: har avgor radordningen, och det ar felet."""
    kod = ("    IF a THEN ut := TRUE; END_IF;\n"
           "    IF b THEN ut := FALSE; END_IF;\n")
    assert "DUBBELSKRIVNING" in _koder(kod)


def test_en_villkorad_skrivning_av_ett_UTTRYCK_falls_aven_mot_samma_uttryck():
    """Ett uttrycks varde beror pa tillstandet och gar inte att avgora har.

    Att slappa igenom tva likadana UTTRYCK hade varit att gissa att de ger
    samma svar - och det ar precis den sortens tysta antagande resten av
    bygget star emot.
    """
    kod = ("    IF a THEN ut := a AND b; END_IF;\n"
           "    IF b THEN ut := a AND b; END_IF;\n")
    assert "DUBBELSKRIVNING" in _koder(kod)


def test_tva_OVILLKORADE_skrivningar_falls_aven_med_samma_varde():
    """Har syns den forsta skrivningen aldrig, oavsett varde. Ett annat fel."""
    kod = "    ut := FALSE;\n    ut := FALSE;\n"
    assert "DUBBELSKRIVNING" in _koder(kod)


def test_samma_literal_i_olika_typer_ar_inte_samma_varde():
    """0 och FALSE ar inte samma literal; typen hor till vardet."""
    kod = ("    IF a THEN n := 0; END_IF;\n"
           "    IF b THEN n := 1; END_IF;\n")
    assert "DUBBELSKRIVNING" in _koder(kod)


# ---- _sekvens bar motsatsen till sitt eget faltnamn -------------------------
#
# `_sekvens` returnerar ett falt som `_sla_ihop_grenar` laser som VILLKORAD.
# Raden stod som `any(not p[0] ...)`, alltsa "minst ett bidrag ar OVILLKORAT" -
# tecknet var vant. En hopslagen gren ar villkorad bara om VARJE bidrag ar det.
#
# Foljden var att grinden hade fel at BADA hallen, och den falska GRONA ar den
# allvarliga: F7 finns for att fanga kapplopningar, och den slappte igenom en.

@pytest.mark.parametrize("namn,kropp,ska_falla", [
    ("IF/ELSE och sedan en villkorad overskrivning",
     "IF a THEN\n UT := TRUE;\nELSE\n UT := FALSE;\nEND_IF;\n"
     "IF c THEN\n UT := TRUE;\nEND_IF;\n", False),
    ("CASE/ELSE och sedan en villkorad overskrivning",
     "CASE b OF\n TRUE: UT := TRUE;\nELSE\n UT := FALSE;\nEND_CASE;\n"
     "IF c THEN\n UT := TRUE;\nEND_IF;\n", False),
    ("nastlade villkor i BADA grenarna, sedan en villkorad",
     "IF a THEN\n IF b THEN\n  UT := TRUE;\n END_IF;\n"
     "ELSE\n IF b THEN\n  UT := FALSE;\n END_IF;\nEND_IF;\n"
     "IF c THEN\n UT := TRUE;\nEND_IF;\n", True),
])
def test_hopslagna_grenars_villkorlighet(namn, kropp, ska_falla):
    """TRASIGA FIXTURER for det vanda tecknet.

    Rad 1 och 2 FALLDES fore rattelsen. "Berakna, sedan tvinga" ar det
    monster kodens egen kommentar kallar standardmonstret for en forregling -
    grinden fallde alltsa det idiom den ar skriven for att skydda.

    Rad 3 SLAPPTES fore rattelsen, och den ar den allvarliga. Med a=FALSE,
    b=TRUE och c=TRUE skrivs UT till FALSE och sedan till TRUE i samma scan.
    Det ar exakt den kapplopning F7 finns for.
    """
    kalla = _pou(" a : BOOL;\n b : BOOL;\n c : BOOL;\n UT AT %QX0.0 : BOOL;\n",
                 kropp)
    koder = [x.kod for x in validera(kalla).anmarkningar]
    assert ("DUBBELSKRIVNING" in koder) is ska_falla, namn
