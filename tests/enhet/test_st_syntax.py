# -*- coding: utf-8 -*-
"""L1: ST-lagrets form. Lexer, läsare, skrivare, sekvensbyggare.

Ingen VC, ingen PLC, ingen fil på disk: allt här är rena funktioner över text
och modell (95_testprotokoll.md, L0-L2 måste gå att köra utan VC).

Två krav som resten av lagret vilar på provas här:

* **Determinism.** Samma modell ger byte-identisk text. Utdata är ett kontrakt.
* **Tur och retur.** skriv(läs(skriv(m))) == skriv(m). Skrivaren och läsaren
  ligger i samma lager och får inte drifta isär; provet är det enda som märker
  om de gör det.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.st import (KONTROLLER, Deklaration, Literal, Namn,  # noqa: E402
                              Pou, Sekvens, SekvensFel, SkrivFel, Steg,
                              Syntaxfel, Tilldelning, Varblock, bygg,
                              bygg_text, las, skriv_enhet, skriv_pou,
                              tokenisera, tolka_tidliteral, validera)
from vc_assist_svc.st import typer as T  # noqa: E402


# ---- TIME-literaler ------------------------------------------------------
#
# Reglerna kommer ur IEC 61131-3: minst en del, enheterna i fallande
# signifikans, ingen enhet två gånger, decimaler bara i den minsta delen.

GILTIGA_TIDER = [
    ("T#500ms", 500.0),
    ("T#0s", 0.0),
    ("TIME#1d2h3m4s5ms", 93784005.0),
    ("t#-2h", -7200000.0),
    ("T#1.5h", 5400000.0),
    ("T#1_000ms", 1000.0),
    ("T#10us", 0.01),
]

OGILTIGA_TIDER = [
    "T#500",        # ingen enhet
    "T#5s10m",      # fel ordning
    "T#1s1s",       # samma enhet två gånger
    "T#1.5h30m",    # decimal i annat än minsta delen
    "T#",           # tomt
    "T#5x",         # okänd enhet
]


@pytest.mark.parametrize("text,ms", GILTIGA_TIDER)
def test_giltig_tidliteral_las_med_ratt_varde(text, ms):
    ok, varde, skal = tolka_tidliteral(text)
    assert ok, skal
    assert varde == pytest.approx(ms)


@pytest.mark.parametrize("text", OGILTIGA_TIDER)
def test_ogiltig_tidliteral_falls_och_sager_varfor(text):
    ok, _varde, skal = tolka_tidliteral(text)
    assert ok is False
    assert skal, "en dom måste kunna säga VARFÖR"


@pytest.mark.parametrize("text", OGILTIGA_TIDER)
def test_ogiltig_tidliteral_falls_av_validatorn(text):
    kalla = ("PROGRAM P\nVAR\n ur : TON;\nEND_VAR\n"
             " ur(IN := TRUE, PT := %s);\nEND_PROGRAM\n" % text)
    r = validera(kalla)
    assert r.ok is False
    assert "TIDLITERAL" in r.koder() or "SYNTAX" in r.koder()


def test_giltiga_tidliteraler_slipper_igenom_validatorn():
    for text, _ms in GILTIGA_TIDER:
        kalla = ("PROGRAM P\nVAR\n ur : TON;\nEND_VAR\n"
                 " ur(IN := TRUE, PT := %s);\nEND_PROGRAM\n" % text)
        assert validera(kalla).ok is True, text


# ---- lexern --------------------------------------------------------------

def test_nyckelord_ar_skiftlageso_kanslig():
    sorter = [t.sort for t in tokenisera("if x then y := 1; end_if;")]
    assert sorter[0] == "NYCKELORD" and "IDENT" in sorter


def test_direktadress_ar_en_enda_token():
    tk = [t for t in tokenisera("q AT %QX0.1 : BOOL;") if t.sort == "ADRESS"]
    assert [t.text for t in tk] == ["%QX0.1"]


def test_kommentarer_far_vara_nastlade():
    tk = tokenisera("(* yttre (* inre *) kvar *) x")
    assert [t.sort for t in tk] == ["KOMMENTAR", "IDENT", "SLUT"]


def test_baserade_literaler_far_ratt_varde():
    varden = [t.varde for t in tokenisera("16#FF 2#1010 8#17") if t.sort == "HELTAL"]
    assert varden == [255, 10, 15]


def test_strangens_dollarsekvenser_avkodas():
    t = tokenisera("'a$$b$'c$0D'")[0]
    assert t.varde == "a$b'c\r"


def test_icke_ascii_i_kallan_avvisas():
    """Genererad ST ska gå genom STruC++, OpenPLC och vidare som OPC UA-namn.
    Teckenkodningen där äger vi inte."""
    with pytest.raises(Syntaxfel):
        tokenisera("x := 'kaffeträd';")


@pytest.mark.parametrize("kalla", ["(* aldrig stangd", "x := 'oavslutad;", "{pragma"])
def test_oavslutade_konstruktioner_kastar(kalla):
    with pytest.raises(Syntaxfel):
        tokenisera(kalla)


# ---- balans --------------------------------------------------------------

OBALANSERADE = [
    ("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n IF a = 1 THEN\n a := 2;\nEND_PROGRAM\n",
     "IF"),
    ("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n WHILE a < 3 DO\n a := a + 1;\n"
     "END_IF;\nEND_PROGRAM\n", "WHILE"),
    ("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n CASE a OF\n 1:\n a := 2;\n"
     "END_PROGRAM\n", "CASE"),
    ("PROGRAM P\nVAR\n a : INT;\n a := 1;\nEND_PROGRAM\n", "VAR"),
]


@pytest.mark.parametrize("kalla,block", OBALANSERADE)
def test_obalanserat_block_falls_och_namner_blocket(kalla, block):
    r = validera(kalla)
    assert r.ok is False
    assert r.koder()[0] in ("BALANS", "SYNTAX")
    assert block in r.anmarkningar[0].text, r.anmarkningar[0].text


def test_fel_avslutare_pekar_ut_bade_avslutaren_och_det_oppna_blocket():
    kalla = ("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n"
             " IF a = 1 THEN\n  a := 2;\n END_WHILE;\nEND_PROGRAM\n")
    r = validera(kalla)
    assert r.ok is False
    assert r.anmarkningar[0].kod == "BALANS"
    assert "END_WHILE" in r.anmarkningar[0].text
    assert "IF" in r.anmarkningar[0].text


def test_tva_else_i_samma_if_falls():
    kalla = ("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n"
             " IF a = 1 THEN\n  a := 2;\n ELSE\n  a := 3;\n ELSE\n  a := 4;\n"
             " END_IF;\nEND_PROGRAM\n")
    r = validera(kalla)
    assert r.ok is False
    assert "BALANS" in r.koder()


def test_balanserade_block_slipper_igenom():
    kalla = ("PROGRAM P\nVAR\n a : INT;\n b : BOOL;\nEND_VAR\n"
             " IF a = 1 THEN\n"
             "  WHILE a < 3 DO\n   a := a + 1;\n  END_WHILE;\n"
             " ELSIF a = 2 THEN\n"
             "  CASE a OF\n  1, 3..5:\n   a := 0;\n  ELSE\n   a := 1;\n"
             "  END_CASE;\n"
             " ELSE\n"
             "  FOR a := 1 TO 10 BY 2 DO\n   b := TRUE;\n  END_FOR;\n"
             "  REPEAT\n   a := a - 1;\n  UNTIL a < 0\n  END_REPEAT;\n"
             " END_IF;\nEND_PROGRAM\n")
    r = validera(kalla)
    assert r.ok is True, str(r)


def test_ofullstandig_sats_faller_som_syntax():
    r = validera("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n a := ;\nEND_PROGRAM\n")
    assert r.ok is False
    assert r.koder() == ("SYNTAX",)


def test_kalla_utan_pou_ar_inte_godkand():
    """Fail-closed (I3): tomt är inte felfritt, det är ingen leverans."""
    assert validera("").ok is False
    assert validera("(* bara en kommentar *)\n").ok is False


# ---- skrivaren -----------------------------------------------------------

KORPUS = [
    "PROGRAM Tom\nEND_PROGRAM\n",
    ("PROGRAM P\nVAR_INPUT RETAIN\n a : INT := 3;\nEND_VAR\n"
     "VAR CONSTANT\n k : REAL := 1.5;\nEND_VAR\n b := a;\nEND_PROGRAM\n"),
    ("TYPE\n    Recept : STRUCT\n        antal : INT := 3;\n"
     "        namn : STRING[20];\n    END_STRUCT;\nEND_TYPE\n"),
    ("FUNCTION_BLOCK Kvitto\nVAR_INPUT\n inn : BOOL;\nEND_VAR\n"
     "VAR_OUTPUT\n ut : BOOL;\nEND_VAR\n ut := inn;\nEND_FUNCTION_BLOCK\n"),
    ("FUNCTION Dubbla : INT\nVAR_INPUT\n x : INT;\nEND_VAR\n"
     " Dubbla := x * 2;\nEND_FUNCTION\n"),
    ("PROGRAM P\nVAR\n f : ARRAY [1..3, 0..2] OF REAL;\n i : INT;\nEND_VAR\n"
     " f[1, 0] := 1.0;\n (* en kommentar mitt i *)\n"
     " f[i, 1] := f[1, 0] - (2.0 - 3.0) * 4.0;\nEND_PROGRAM\n"),
]


@pytest.mark.parametrize("kalla", KORPUS)
def test_tur_och_retur_genom_lasare_och_skrivare(kalla):
    en_gang = skriv_enhet(las(kalla))
    tva_ganger = skriv_enhet(las(en_gang))
    assert en_gang == tva_ganger


@pytest.mark.parametrize("kalla", KORPUS)
def test_skrivaren_ar_deterministisk(kalla):
    modell = las(kalla)
    assert skriv_enhet(modell) == skriv_enhet(modell)


def test_skrivaren_lagger_inte_till_blanksteg_i_slutet_av_raderna():
    text = skriv_enhet(las(KORPUS[5]))
    assert all(rad == rad.rstrip() for rad in text.split("\n"))
    assert text.endswith("\n")


def test_indraget_ar_fyra_blanksteg_per_niva():
    text = skriv_enhet(las("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n"
                           " IF a = 1 THEN\n a := 2;\n END_IF;\nEND_PROGRAM\n"))
    assert "\n    IF a = 1 THEN\n        a := 2;\n    END_IF;\n" in text


def test_jamforelser_under_and_parentesteras_for_lasbarhet():
    text = skriv_enhet(las("PROGRAM P\nVAR\n a : INT;\n b : BOOL;\nEND_VAR\n"
                           " b := a = 1 AND NOT b;\nEND_PROGRAM\n"))
    assert "b := (a = 1) AND NOT b;" in text


def test_skrivaren_vagrar_icke_ascii():
    pou = Pou("PROGRAM", "P", (Varblock("VAR", (
        Deklaration("a", T.Elementar("INT"), kommentar="hö"),)),))
    with pytest.raises(SkrivFel):
        skriv_pou(pou)


def test_skrivaren_vagrar_en_modell_den_inte_kan_skriva():
    class EgenSats(object):
        rad = 1

    pou = Pou("PROGRAM", "P", (), (EgenSats(),))
    with pytest.raises(SkrivFel):
        skriv_pou(pou)


# ---- sekvensbyggaren -----------------------------------------------------

def _deklarationer():
    return (Varblock("VAR_INPUT", (
                Deklaration("nodstopp_ok", T.BOOL, adress="%IX0.0", skyddad=True),
                Deklaration("start", T.BOOL, adress="%IX0.1"),
                Deklaration("pa_plats", T.BOOL, adress="%IX0.2"))),
            Varblock("VAR_OUTPUT", (
                Deklaration("band", T.BOOL, adress="%QX0.0"),
                Deklaration("gripare", T.BOOL, adress="%QX0.1"))))


def _sant():
    return Literal("BOOL", "TRUE", True)


def _falskt():
    return Literal("BOOL", "FALSE", False)


def _spec(**andringar):
    grund = dict(
        namn="Plockstation",
        nodstopp="nodstopp_ok",
        start=Namn("start"),
        deklarationer=_deklarationer(),
        steg=(Steg("mata", (Tilldelning(Namn("band"), _sant()),),
                   villkor=Namn("pa_plats"), tidsgrans="T#10s"),
              Steg("grip", (Tilldelning(Namn("band"), _falskt()),
                            Tilldelning(Namn("gripare"), _sant())),
                   uppehall="T#500ms")))
    grund.update(andringar)
    return Sekvens(**grund)


def test_sekvensen_som_byggs_ar_godkand_av_validatorn():
    """Positivkontrollen. Byggarens utdata måste passera alla tolv kontroller,
    annars är byggaren och validatorn oense om vad korrekt ST är."""
    r = validera(bygg_text(_spec()))
    assert r.ok is True, str(r)


def test_sekvensen_ar_deterministisk():
    assert bygg_text(_spec()) == bygg_text(_spec())


def test_timrarna_anropas_utanfor_case():
    """En TON som inte anropas behåller sitt Q. Anropas den bara i sitt eget
    steg släpper nästa besök igenom direkt — det är felet raden finns mot."""
    text = bygg_text(_spec())
    anrop = text.index("grans_mata(IN := steg = 10")
    fall = text.index("CASE steg OF")
    assert anrop < fall
    assert "ur_grip(IN := steg = 20, PT := T#500ms);" in text


def test_nodstoppsgrenen_nollar_varje_utgang_som_stegen_satter():
    text = bygg_text(_spec())
    gren = text.split("IF NOT nodstopp_ok THEN")[1].split("ELSE")[0]
    assert "steg := 0;" in gren
    assert "band := FALSE;" in gren
    assert "gripare := FALSE;" in gren


def test_stegen_numreras_i_tior_med_vila_pa_noll_och_felsteg_hogt():
    text = bygg_text(_spec())
    etiketter = [rad.strip() for rad in text.split("\n")]
    for etikett in ("0:", "10:", "20:", "900:"):
        assert etikett in etiketter, etikett


def test_sista_steget_gar_tillbaka_till_vila():
    text = bygg_text(_spec())
    sista = text.split("        20:")[1]
    assert "steg := 0;" in sista


def test_tidsgransen_ger_larm_och_felsteg():
    text = bygg_text(_spec())
    assert "ELSIF grans_mata.Q THEN" in text
    assert "larm := TRUE;" in text
    assert "steg := 900;" in text


def test_steg_utan_vag_ut_vagras():
    with pytest.raises(SekvensFel):
        bygg(_spec(steg=(Steg("hanger", (Tilldelning(Namn("band"), _sant()),)),)))


def test_ogiltig_tid_i_steget_vagras_vid_bygget():
    with pytest.raises(SekvensFel):
        bygg(_spec(steg=(Steg("mata", (), uppehall="T#500"),)))


def test_steg_som_skriver_till_okand_tagg_vagras():
    """Taggar kommer ur signalkartan (I10). Ett namn som inte finns där är
    hittat på, och det är ett hårt fel."""
    with pytest.raises(SekvensFel):
        bygg(_spec(steg=(Steg("mata", (Tilldelning(Namn("pahittad"), _sant()),),
                              villkor=Namn("pa_plats")),)))


def test_steg_som_skriver_till_sakerhetstagg_vagras():
    """I15: ingen genererad kod i en säkerhetsfunktion."""
    with pytest.raises(SekvensFel):
        bygg(_spec(steg=(Steg("mata",
                              (Tilldelning(Namn("nodstopp_ok"), _falskt()),),
                              villkor=Namn("pa_plats")),)))


def test_okant_nodstoppsnamn_vagras():
    with pytest.raises(SekvensFel):
        bygg(_spec(nodstopp="finns_inte"))


def test_timernamn_som_krockar_med_signalkartan_vagras():
    dekl = _deklarationer() + (Varblock("VAR", (
        Deklaration("ur_mata", T.BOOL),)),)
    with pytest.raises(SekvensFel):
        bygg(_spec(deklarationer=dekl,
                   steg=(Steg("mata", (), uppehall="T#1s"),)))


def test_sekvensen_gar_att_lasa_tillbaka_och_skrivs_likadant():
    text = bygg_text(_spec())
    assert skriv_enhet(las(text)) == text


# ---- kontrollregistret ---------------------------------------------------

def test_varje_kontroll_bar_sin_felklass_eller_en_uttalad_lucka():
    """82_felklasser.md äger klasserna. En kontroll utan klass ska stå som
    None, inte tryckas in i F14 — specen säger att F14 ska hållas nära noll."""
    kanda = {"F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10",
             "F11", "F12", "F13", "F14"}
    for kod, (klass, vad) in KONTROLLER.items():
        assert vad, kod
        assert klass is None or klass in kanda, kod
    utan = [k for k, (klass, _v) in KONTROLLER.items() if klass is None]
    assert set(utan) == {"OATKOMLIG", "SAKERHET"}


# ---- M-51: formerna som var falska rödgrindar ----------------------------
#
# Svepet i tests/enhet/test_st_svep_mot_strucpp.py mäter dem mot den riktiga
# kompilatorn. De här proven kostar ingen kompilator och fäller lika säkert;
# svepet svarar på VARFÖR formen ska accepteras, de här på ATT den gör det.

SEMIKOLONFRIA_BLOCK = [
    ("END_IF", " IF a = 1 THEN\n  a := 2;\n END_IF\n"),
    ("END_CASE", " CASE a OF\n  1: a := 2;\n END_CASE\n"),
    ("END_WHILE", " WHILE a < 3 DO\n  a := a + 1;\n END_WHILE\n"),
    ("END_REPEAT", " REPEAT\n  a := a + 1;\n UNTIL a > 3\n END_REPEAT\n"),
    ("END_FOR", " FOR a := 1 TO 3 DO\n  b := b + 1;\n END_FOR\n"),
]


@pytest.mark.parametrize("slutord,kropp", SEMIKOLONFRIA_BLOCK,
                         ids=[s for s, _k in SEMIKOLONFRIA_BLOCK])
def test_semikolon_efter_blockslut_ar_valfritt(slutord, kropp):
    """MÄTT i M-51: STruC++ 0.6.6 bygger alla fem både med och utan
    semikolon. Vårt lager svarade OLÄSLIG på formen utan, och grind 2 och 3
    kör före grind 1 — så kompilatorn fick aldrig se koden."""
    kalla = "PROGRAM P\nVAR\n a : INT;\n b : INT;\nEND_VAR\n%sEND_PROGRAM\n" % kropp
    r = validera(kalla)
    assert r.ok is True, "%s utan semikolon: %s" % (slutord, r)
    med = kalla.replace(slutord + "\n", slutord + ";\n")
    assert validera(med).ok is True, "%s MED semikolon slutade fungera" % slutord


def test_semikolon_far_avsluta_men_ar_aldrig_en_sats():
    """Regeln som blev kvar när semikolonet gjordes valfritt.

    Ett ensamt `;` i satsläge fälls fortfarande. T7 i fas7_stationen.md är
    precis den kroppen, och M-48 mätte att grind 3 fäller den."""
    assert validera("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n ;\nEND_PROGRAM\n").ok is False
    # ... men ett semikolon PÅ END_VAR:s egen rad hör till deklarationsblocket
    assert validera("PROGRAM P\nVAR\n a : INT;\nEND_VAR;\n a := 1;\n"
                    "END_PROGRAM\n").ok is True


def test_end_var_raden_ater_inte_upp_kroppens_forsta_tecken():
    """Fällan som uppstod när semikolonet gjordes valfritt: END_VAR åt upp
    kroppens ensamma `;`, och ett program utan innehåll blev godkänt."""
    r = validera("PROGRAM P\nVAR\n a : INT;\nEND_VAR\n ;\nEND_PROGRAM\n")
    assert r.ok is False
    assert "SYNTAX" in r.koder()


BASERADE_LITERALER = [
    ("WORD#16#FF", 255), ("INT#16#7F", 127), ("BYTE#2#1010", 10),
    ("DWORD#8#777", 511), ("16#FF", 255), ("INT#5", 5), ("INT#-5", -5),
]


@pytest.mark.parametrize("text,varde", BASERADE_LITERALER,
                         ids=[t for t, _v in BASERADE_LITERALER])
def test_typprefix_far_folias_av_en_bas(text, varde):
    """`WORD#16#FF` är EN literal. Kroppsscanningen släppte inte in `#`, så
    basdelen blev ett oväntat tecken och hela filen OLÄSLIG. MÄTT i M-51."""
    tokens = [t for t in tokenisera("x := %s;" % text) if t.sort == "HELTAL"]
    assert len(tokens) == 1, "literalen delades upp: %s" % text
    assert tokens[0].varde == varde


def test_en_bas_som_inte_finns_sager_samma_sak_i_bada_formerna():
    """Basvalideringen delas nu av `16#FF` och `WORD#16#FF`. Två kopior av
    samma regel driftar isär; en kopia gör det inte."""
    for text in ("x := 3#12;", "x := INT#3#12;"):
        with pytest.raises(Syntaxfel) as fel:
            tokenisera(text)
        assert "bas" in str(fel.value)


EXPONENTFORMER = [
    ("a ** b", "a ** b"),
    ("a ** b ** c", "a ** b ** c"),
    ("(a ** b) ** c", "(a ** b) ** c"),
    ("-a ** b", "-a ** b"),
    ("(-a) ** b", "(-a) ** b"),
    ("a * b ** c", "a * b ** c"),
    ("(a * b) ** c", "(a * b) ** c"),
    ("a + b ** c", "a + b ** c"),
]


@pytest.mark.parametrize("in_text,ut_text", EXPONENTFORMER,
                         ids=[i for i, _u in EXPONENTFORMER])
def test_exponentoperatorn_binder_och_skrivs_tillbaka_likadant(in_text, ut_text):
    """`**` är IEC 61131-3:s exponentoperator. Den binder hårdare än unärt
    minus och är högerassociativ — båda tvärtemot allt i NIVAER, vilket är
    skälet att den ligger utanför tabellen.

    Provet är tur-och-retur: parenteserna som skrivs ut måste ge samma träd
    tillbaka, annars har läsaren och skrivaren skilda uppfattningar om vad
    `a ** b ** c` betyder."""
    kalla = ("PROGRAM P\nVAR\n a, b, c, r : REAL;\nEND_VAR\n r := %s;\n"
             "END_PROGRAM\n" % in_text)
    text = skriv_enhet(las(kalla))
    assert " r := %s;" % ut_text in text, text
    assert skriv_enhet(las(text)) == text
