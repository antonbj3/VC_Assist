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
    # Versalerna. IEC 61131-3 ar skiftlagesokansligt, och STruC++ v0.6.6 -
    # kompilatorn i var egen kedja - accepterar alla fem (MATT, M-96).
    # Grinden avvisade dem tidigare: prefixregexen bar re.I men delregexen
    # gjorde det inte, sa halva literalen var skiftlagesokanslig.
    #
    # Det kostade riktiga varv. I fas 9:s forsta modelldrivna korning var NIO
    # av sexton grinddomar den har falska rodgrinden, och tre av fyra uppgifter
    # slog i taket. Provfilen test_st_svep_mot_strucpp.py sager sjalv varfor
    # det ar dyrt: en modell som far ett fel som inte finns lagar nagot som
    # redan fungerade och lar sig fel sak.
    ("T#3S", 3000.0),
    ("T#3.0S", 3000.0),
    ("T#500MS", 500.0),
    ("t#3S", 3000.0),
    ("T#1H30M", 5400000.0),
    ("TIME#2S", 2000.0),
]

OGILTIGA_TIDER = [
    "T#500",        # ingen enhet
    "T#5s10m",      # fel ordning
    "T#1s1s",       # samma enhet två gånger
    "T#1.5h30m",    # decimal i annat än minsta delen
    "T#",           # tomt
    "T#5x",         # okänd enhet
    "T#5X",         # okand enhet, versal - rattelsen far inte oppna for den
    "T#5S10M",      # fel ordning, versalt: normaliseringen far inte tappa domen
    "T#1S1S",       # samma enhet tva ganger, versalt
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


# ======================================================================
# M-99: differentialsvepet mot STruC++ 0.6.6
#
# Sex falska rodgrindar och tre hal, alla matta genom att kora samma
# konstruktion genom bade vart lager och kompilatorn i var egen kedja.
# Varje lagning har bade sitt giltiga fall OCH sin ogiltiga granne, sa att
# rattelsen inte oppnar en lucka i stallet.
# ======================================================================

# ---- 1. INT:s minsta varde gick inte att skriva ------------------------

HELTALSGRANSER = [
    ("INT", "-32768", True), ("INT", "32767", True),
    ("INT", "-32769", False), ("INT", "32768", False),
    ("SINT", "-128", True), ("SINT", "127", True),
    ("SINT", "-129", False), ("SINT", "128", False),
    ("DINT", "-2147483648", True), ("DINT", "2147483647", True),
    ("DINT", "-2147483649", False), ("DINT", "2147483648", False),
]


@pytest.mark.parametrize("typ,text,vantat", HELTALSGRANSER,
                         ids=["%s_%s" % (t, x) for t, x, _v in HELTALSGRANSER])
def test_negativ_literal_provas_mot_omradet_med_sitt_tecken(typ, text, vantat):
    """FALSK RODGRIND, matt i M-99.

    `iA := -32768;` avvisades med *"literalen 32768 ligger utanfor INT
    (-32768..32767)"*. Talet i meddelandet fanns inte i koden: unart minus
    lamnade literalvardet orort, sa intervallkontrollen provade 32768 i
    stallet for -32768. Varje heltalstyps MINSTA varde var darmed omojligt
    att skriva som literal, och STruC++ 0.6.6 kompilerar formen.

    Grannarna i tabellen ar det som far rattelsen att inte bli en lucka:
    -32769 och 32768 ska fortfarande falla.
    """
    kalla = ("PROGRAM P\nVAR\n v : %s;\nEND_VAR\n v := %s;\nEND_PROGRAM\n"
             % (typ, text))
    r = validera(kalla)
    assert r.ok is vantat, "%s := %s gav %s" % (typ, text, r)


# ---- 2. uttrycksdjupet matte parserramar, inte nastling ---------------

def _parenteser(n):
    return ("PROGRAM P\nVAR\n a, b : INT;\nEND_VAR\n a := %sb%s;\n"
            "END_PROGRAM\n" % ("(" * n, ")" * n))


def test_uttrycksdjupet_ar_nastlingsnivaer_inte_parserramar():
    """FALSK RODGRIND, matt i M-99.

    Meddelandet sa *"uttrycket ar djupare an 64 nivaer"*, men raknaren okade
    en gang per prioritetsniva i NIVAER. En parentes kostade darfor atta steg
    och det VERKLIGA taket lag vid atta parenteser. En modell som far det
    felet pa `a := ((((((((b))))))));` har ingen vag att laga det: talet i
    meddelandet finns inte i koden.
    """
    from vc_assist_svc.st.lasare import MAX_DJUP
    assert validera(_parenteser(8)).ok is True, "atta parenteser ska ga"
    assert validera(_parenteser(MAX_DJUP - 2)).ok is True
    r = validera(_parenteser(MAX_DJUP + 5))
    assert r.ok is False, "taket slutade falla"
    assert "djupare" in str(r)


def test_lasarens_djuptak_ligger_under_uppmatt_kapacitet():
    """TRASIG FIXTUR for taket ovan: mat kapaciteten i stallet for att tro pa den.

    Ett tak utan matreferens ar en gissning. Har stangs vakten av och
    RecursionError bisekeras fram, sa MAX_DJUP alltid kan jamforas med det
    djup lasaren faktiskt bar. MATT 2026-09-05 vid recursionlimit 1000: 89
    nastlingsnivaer bar, den 90:e foll.
    """
    from vc_assist_svc.st import lasare as L
    tidigare = L.MAX_DJUP
    L.MAX_DJUP = 10 ** 9
    try:
        lo, hi = 1, 400
        while lo < hi:
            mitt = (lo + hi + 1) // 2
            try:
                L.las(_parenteser(mitt))
                lo = mitt
            except RecursionError:
                hi = mitt - 1
            except Exception:
                hi = mitt - 1
    finally:
        L.MAX_DJUP = tidigare
    assert lo > tidigare, (
        "MAX_DJUP=%d men lasaren bar bara %d nivaer; taket skyddar inte mot "
        "RecursionError langre" % (tidigare, lo))
    assert lo < 400, "bisektionen tog aldrig slut - matningen ar inte en matning"


# ---- 3. en grind som kraschar i stallet for att doma -------------------

def test_en_baklanges_faltgrans_ger_en_anmarkning_inte_ett_undantag():
    """FALSK RODGRIND av varsta sorten, matt i M-99.

    `ARRAY[10..1] OF INT` kom ut ur `validera` som en OFANGAD ValueError ur
    typlagrets `__post_init__`. `validera` fangar bara Syntaxfel, sa grinden
    KRASCHADE i stallet for att doma - och en grind som kraschar lamnar
    ingen anmarkning at nagon att laga.
    """
    r = validera("PROGRAM P\nVAR\n a : ARRAY[10..1] OF INT;\nEND_VAR\n"
                 " a[1] := 1;\nEND_PROGRAM\n")
    assert r.ok is False
    assert "baklanges" in str(r).lower() or "baklänges" in str(r).lower()
    # grannen: en gilltig grans far inte ha slutat fungera
    assert validera("PROGRAM P\nVAR\n a : ARRAY[1..10] OF INT;\nEND_VAR\n"
                    " a[1] := 1;\nEND_PROGRAM\n").ok is True
    assert validera("PROGRAM P\nVAR\n a : ARRAY[-5..5] OF INT;\nEND_VAR\n"
                    " a[1] := 1;\nEND_PROGRAM\n").ok is True


# ---- 4. en grind som HANGER lamnar inte ens ett spar -------------------

def test_en_kalla_som_slutar_mitt_i_en_prefixad_literal_hanger_inte():
    """HAL, matt i M-99, och det farligaste fyndet i svepet.

    `self._kika() in "_.#"` ar SANT for den tomma strangen, och `_kika()`
    lamnar tom strang vid kallans slut. `BOOL#7` UTAN avslutande radbrytning
    snurrade darfor for evigt i lexern. `BOOL#7\\n` foll ratt hela tiden, sa
    felet bet bara pa text utan radbrytning sist - och det ar precis vad ett
    kodstaket ur en modell kan ge.

    Provet kors i en EGEN process med tidsgrans. Ett hang i sviten sjalv hade
    inte gett ett rott prov, det hade gett ett prov som aldrig svarar.
    """
    import subprocess
    kod = (
        "import sys; sys.path.insert(0, %r)\n"
        "from vc_assist_svc.st import tokenisera\n"
        "from vc_assist_svc.st import Syntaxfel\n"
        "for text in ('BOOL#7', 'X#', 'T#', 'WORD#16#FF', 'INT#5', 'T#5s'):\n"
        "    try:\n"
        "        tokenisera(text)\n"
        "    except Syntaxfel:\n"
        "        pass\n"
        "print('KLAR')\n" % os.path.join(_ROT, "svc"))
    klar = subprocess.run([sys.executable, "-c", kod], timeout=30,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert klar.returncode == 0, klar.stdout.decode("utf-8", "replace")
    assert b"KLAR" in klar.stdout


# ---- 5. adressens storleksbokstav mot typen ---------------------------

ADRESSPAR_SOM_BYGGER = [
    ("%IX0.0", "BOOL"), ("%QX0.1", "BOOL"), ("%I0.0", "BOOL"),
    ("%IB2", "BYTE"), ("%IB2", "SINT"), ("%IB2", "USINT"),
    ("%IW1", "WORD"), ("%IW1", "INT"), ("%QW1", "UINT"),
    ("%MD4", "DWORD"), ("%MD4", "DINT"), ("%MD4", "UDINT"), ("%MD4", "REAL"),
    ("%ML0", "LWORD"), ("%ML0", "LINT"), ("%ML0", "ULINT"), ("%ML0", "LREAL"),
]

ADRESSPAR_SOM_INTE_BYGGER = [
    ("%QW1", "BOOL"), ("%IX0.0", "INT"), ("%MD4", "BOOL"), ("%IB2", "INT"),
    ("%ML0", "REAL"), ("%IW1", "DINT"), ("%IX0.0", "TIME"), ("%IW1", "TIME"),
    ("%I0.0", "INT"),
]


def _med_adress(adress, typ):
    return ("PROGRAM P\nVAR\n v AT %s : %s;\n q : BOOL;\nEND_VAR\n"
            " q := q;\nEND_PROGRAM\n" % (adress, typ))


@pytest.mark.parametrize("adress,typ", ADRESSPAR_SOM_BYGGER,
                         ids=["%s_%s" % (a, t) for a, t in ADRESSPAR_SOM_BYGGER])
def test_adressens_storlek_slapper_igenom_de_typer_kompilatorn_bygger(adress, typ):
    """HAL, matt i M-99: 80 av 96 kombinationer.

    Sex storleksbokstaver x sexton typer gick genom STruC++ 0.6.6. Den byggde
    16 par och avvisade 80 - vart lager slappte igenom alla 96. `q AT %QW1 :
    BOOL;` ar ingen typfraga inne i ST-koden utan en fraga om VAR i
    bildtabellen variabeln ligger, och en BOOL pa en ordadress laser och
    skriver fel antal byte i drift.
    """
    r = validera(_med_adress(adress, typ))
    assert r.ok is True, "%s : %s avvisas nu: %s" % (adress, typ, r)


@pytest.mark.parametrize("adress,typ", ADRESSPAR_SOM_INTE_BYGGER,
                         ids=["%s_%s" % (a, t) for a, t in ADRESSPAR_SOM_INTE_BYGGER])
def test_adressens_storlek_faller_de_typer_kompilatorn_avvisar(adress, typ):
    """Grannarna till provet ovan: halet far inte oppnas igen."""
    r = validera(_med_adress(adress, typ))
    assert r.ok is False, "%s : %s slapps igenom igen" % (adress, typ)
    assert "storleken" in str(r)


# ---- 6. sidmatning och vertikaltabb ar blanksteg ----------------------

def test_ascii_styrtecken_skiljer_tokens_at_men_icke_ascii_faller_anda():
    """FALSK RODGRIND, matt i M-99.

    Vertikaltabb (0x0B) och sidmatning (0x0C) foll som *"ovantat tecken"*
    medan STruC++ 0.6.6 bygger bada. De ar ASCII, sa lagrets EGET skal att
    avvisa tecken - teckenkodningen genom OpenPLC och vidare ut som OPC
    UA-namn - galler dem inte.

    Grannen ar hela skalet att regeln finns: ett verkligt icke-ASCII-tecken
    ska fortfarande falla.
    """
    for tecken in ("\x0b", "\x0c", "\t"):
        kalla = ("PROGRAM P\nVAR\n a, b : BOOL;\nEND_VAR\n a := b;%s\n b := a;\n"
                 "END_PROGRAM\n" % tecken)
        assert validera(kalla).ok is True, "%r avvisas" % tecken
    for tecken in ("å", "Ä", "–"):
        kalla = ("PROGRAM P\nVAR\n a, b : BOOL;\nEND_VAR\n a := b; // %s\n"
                 "END_PROGRAM\n" % tecken)
        r = validera(kalla)
        assert r.ok is False, "%r slapps igenom" % tecken
        assert "ASCII" in str(r)


# ---- 7. en decimalpunkt utan brakdel ---------------------------------

REALFORMER = [
    ("1.0", True), ("1.5e3", True), ("1.0E-3", True), ("0.0", True),
    ("1.", False), ("1.e3", False),
]


@pytest.mark.parametrize("text,vantat", REALFORMER,
                         ids=[t for t, _v in REALFORMER])
def test_decimalpunkten_kraver_minst_en_siffra_efter_sig(text, vantat):
    """HAL, matt i M-99. IEC 61131-3:s real_literal har bade en heltalsdel och
    en brakdel; `1.` och `1.e3` har ingen brakdel. Bada slapptes igenom har
    och avvisades av STruC++ 0.6.6 - ett hal at det hall dar felet syns forst
    i bygget."""
    kalla = ("PROGRAM P\nVAR\n r : REAL;\nEND_VAR\n r := %s;\nEND_PROGRAM\n"
             % text)
    assert validera(kalla).ok is vantat


def test_omradesprickorna_ar_ororda_av_decimalregeln():
    """Grannen: `1..5` ar tva prickar, inte en decimalpunkt utan siffra."""
    assert validera("PROGRAM P\nVAR\n a : INT;\n b : BOOL;\nEND_VAR\n"
                    " CASE a OF\n  1..5: b := TRUE;\n END_CASE;\n"
                    "END_PROGRAM\n").ok is True
    assert validera("PROGRAM P\nVAR\n a : ARRAY[1..10] OF INT;\nEND_VAR\n"
                    " a[1] := 1;\nEND_PROGRAM\n").ok is True


# ---- 8. RETAIN och CONSTANT pa samma block ----------------------------

KVALIFICERARPAR = [
    ("VAR CONSTANT", True), ("VAR RETAIN", True), ("VAR NON_RETAIN", True),
    ("VAR RETAIN CONSTANT", False), ("VAR CONSTANT RETAIN", False),
    ("VAR NON_RETAIN CONSTANT", False),
]


@pytest.mark.parametrize("block,vantat", KVALIFICERARPAR,
                         ids=[b.replace(" ", "_") for b, _v in KVALIFICERARPAR])
def test_retain_och_constant_gar_inte_ihop(block, vantat):
    """HAL, matt i M-99: STruC++ 0.6.6 sager *"Variable cannot be both RETAIN
    and CONSTANT"*; vart lager slappte igenom formen. En konstant har inget
    tillstand att behalla over en varmstart."""
    kalla = ("PROGRAM P\n%s\n G : INT := 1;\nEND_VAR\nVAR\n a : INT;\nEND_VAR\n"
             " a := G;\nEND_PROGRAM\n" % block)
    assert validera(kalla).ok is vantat
