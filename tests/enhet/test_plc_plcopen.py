# -*- coding: utf-8 -*-
"""L1: exporten UT till PLCopen XML, och grinden som kraver att den overlever
sin egen import.

`M-114` matte vagen IN i ett befintligt styrsystem: ingen av vagarna ger
tillbaka kallkoden. `M-113` matte att `control.signals` plus en genererad
kropp GAR att lagga i ett schemavaliderat PLCopen-dokument -- men den lade ST:n
som en textklump i `<ST>` och lasre den tillbaka som text. En textklump som
kommer tillbaka byte-identisk bevisar att XML-lagret inte tappade tecken. Den
bevisar ingenting om deklarationerna, adresserna, kvalificerarna eller
sakerhetsmarkningen, for de var aldrig med.

Det har provet stalller det hardare kravet: **modellen ut, modellen tillbaka.**
`Enhet` -> XML -> `Enhet`, och de tva ska vara lika. Radnumren bar ingen
jamforelse (`modell._rad`), sa likhet ar strukturell.

## Ordningen i filen ar mätordningen, inte en godtycklig

1. **Kontrollen forst.** Varje fixtur provas ocksa genom ST-lagrets EGEN tur
   och retur (`las(skriv_enhet(e)) == e`). Gar den inte igenom dar ar felet
   inte PLCopens, och da far provet inte anklaga PLCopen. Att mata matmetoden
   innan man anklagar objektet ar hela skalet att kontrollen star forst.
2. **Konstruktionerna.** Timers, flanker och CASE ar de utpekade kandidaterna,
   men de ar inte de enda: lokaliserade adresser, `{SAKERHET}`-pragmat,
   CONSTANT/RETAIN, egna STRUCT-typer, egna funktionsblock, VAR_TEMP/
   VAR_EXTERNAL/VAR_IN_OUT och faltinitierare provas ocksa.
3. **Banken.** Alla 63 uppgifter genom baslinjegeneratorn, ett riktigt program
   per uppgift. En handskriven fixtur ar ett stickprov; banken ar datan.

## TRASIGA FIXTURER (rott innan mekanismen fanns)

* `test_kvalificerarordningen_falls` -- den enda RIKTIGA ST-konstruktion i
  hela matningen som inte overlever: `VAR NON_RETAIN CONSTANT` blir tva
  XML-attribut, och attribut har ingen ordning. Den kommer tillbaka som
  `VAR CONSTANT NON_RETAIN` och maste **fallas**.
* `test_kommentar_med_kommentarslut_falls` och
  `test_kommentar_som_inte_ar_stripad_falls` -- en `Deklaration.kommentar` som
  bar `*)` eller blanksteg i kanten gar att bygga i modellen men inte att
  skriva som en ST-kommentar.
* `test_icke_ascii_falls`, `test_okand_typ_falls`, `test_tom_enhet_falls` --
  det exportoren inte kan avbilda far inte bli en tyst fil.
* `test_trasig_xml_falls`, `test_fel_namnrymd_falls`,
  `test_okand_pousort_i_filen_falls`, `test_annat_kroppssprak_an_st_falls` --
  importen far inte svara med en tom `Enhet` pa en fil den inte forstod.
* Avsnitt 5b muterar den FARDIGA filen -- tar bort adressen, kommentaren,
  sakerhetsmarkningen, kvalificeraren och kroppen -- och kraver att grinden
  ser skillnaden. Utan de proven vore ett `LIKA` pa 63 bankprogram inget
  bevis; en tur och retur som alltid sager LIKA mater ingenting.

Alla var roda innan `plc/plcopen.py` fanns. En av dem skrevs som en trasig
fixtur och blev gron: en FLERRADIG kommentar overlever, tvartemot vad jag
antog. Provet star kvar med omvant pastaende under sitt eget namn.

beskriver: svc/vc_assist_svc/plc/plcopen.py
"""
import os
import sys
from xml.sax.saxutils import escape as _escape

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.st import las, skriv_enhet                    # noqa: E402
from vc_assist_svc.st import modell as M                         # noqa: E402
from vc_assist_svc.st import typer as T                          # noqa: E402
from vc_assist_svc.plc import plcopen as PX                      # noqa: E402


# ---- konstruktionerna ----------------------------------------------------
#
# Varje post ar (namn, ST-kalla). De skrivs som ST-text och lases in med
# projektets egen lasare, sa att fixturen ar en RIKTIG konstruktion och inte en
# handbyggd modell som ingen kompilator har sett.

KONSTRUKTIONER = [
    ("timer_ton", """
PROGRAM Press
VAR
    ST100_CNV_RUN AT %QX0.0 : BOOL; (* plc.ST100_CNV_RUN *)
    ST100_PEC_PART AT %IX0.0 : BOOL; (* plc.ST100_PEC_PART *)
    vakt : TON;
END_VAR
    vakt(IN := ST100_PEC_PART, PT := T#5s);
    IF vakt.Q THEN
        ST100_CNV_RUN := FALSE;
    END_IF;
END_PROGRAM
"""),
    ("timer_tp_tof", """
PROGRAM Puls
VAR
    p : TP;
    f : TOF;
    ut AT %QX0.0 : BOOL;
    in1 AT %IX0.0 : BOOL;
END_VAR
    p(IN := in1, PT := T#200ms);
    f(IN := p.Q, PT := T#1s500ms);
    ut := f.Q;
END_PROGRAM
"""),
    ("flank_r_trig", """
PROGRAM Flank
VAR
    fl : R_TRIG;
    ned : F_TRIG;
    givare AT %IX0.0 : BOOL;
    rakning : INT := 0;
END_VAR
    fl(CLK := givare);
    ned(CLK := givare);
    IF fl.Q THEN
        rakning := rakning + 1;
    ELSIF ned.Q THEN
        rakning := rakning - 1;
    END_IF;
END_PROGRAM
"""),
    ("case_med_omraden", """
PROGRAM Steg
VAR
    steg : INT := 0;
    ut AT %QX0.0 : BOOL;
END_VAR
    CASE steg OF
        0:
            ut := FALSE;
            steg := 1;
        1..4, 7:
            ut := TRUE;
        10:
            steg := 0;
    ELSE
        steg := 0;
    END_CASE;
END_PROGRAM
"""),
    ("case_i_case", """
PROGRAM Nast
VAR
    a : INT;
    b : INT;
    ut AT %QX0.0 : BOOL;
END_VAR
    CASE a OF
        0:
            CASE b OF
                0:
                    ut := TRUE;
            ELSE
                ut := FALSE;
            END_CASE;
    END_CASE;
END_PROGRAM
"""),
    ("lokaliserad_och_skyddad", """
PROGRAM Sakert
VAR
    ST100_ESTOP AT %IX0.0 : BOOL; {SAKERHET} (* nodstoppskretsen *)
    ST100_TRYCK AT %IW0 : INT;
    ST100_FLODE AT %ID1 : REAL;
    ST100_VLV AT %QX0.1 : BOOL; (* plc.ST100_VLV *)
END_VAR
    ST100_VLV := ST100_ESTOP;
END_PROGRAM
"""),
    ("kvalificerare", """
PROGRAM Kval
VAR CONSTANT
    TAK : INT := 100;
END_VAR
VAR RETAIN
    raknare : DINT := 0;
END_VAR
VAR NON_RETAIN
    tillfallig : REAL := 0.0;
END_VAR
VAR
    ut AT %QW0 : INT;
END_VAR
    raknare := raknare + 1;
    ut := TAK;
END_PROGRAM
"""),
    ("egen_struct", """
TYPE
    Punkt : STRUCT
        x : REAL := 0.0;
        y : REAL;
        giltig : BOOL := FALSE; (* satt av mataren *)
    END_STRUCT;
    Ram : STRUCT
        lo : INT := -5;
        hi : INT := 5;
    END_STRUCT;
END_TYPE

PROGRAM Geo
VAR
    p : Punkt;
    r : Ram;
    ut AT %QD0 : REAL;
END_VAR
    ut := p.x;
END_PROGRAM
"""),
    ("eget_funktionsblock", """
FUNCTION_BLOCK Kvitto
VAR_INPUT
    begar : BOOL;
    svar : BOOL;
END_VAR
VAR_OUTPUT
    klar : BOOL;
END_VAR
VAR
    lage : INT := 0;
END_VAR
    IF begar AND svar THEN
        lage := 1;
    END_IF;
    klar := lage = 1;
END_FUNCTION_BLOCK

PROGRAM Linje
VAR
    k : Kvitto;
    a AT %IX0.0 : BOOL;
    b AT %IX0.1 : BOOL;
    ut AT %QX0.0 : BOOL;
END_VAR
    k(begar := a, svar := b);
    ut := k.klar;
END_PROGRAM
"""),
    ("funktion_med_returtyp", """
FUNCTION Dubbla : INT
VAR_INPUT
    v : INT;
END_VAR
    Dubbla := v * 2;
END_FUNCTION

PROGRAM Anv
VAR
    ut AT %QW0 : INT;
    v : INT := 3;
END_VAR
    ut := Dubbla(v);
END_PROGRAM
"""),
    ("falt_och_faltinit", """
PROGRAM Falt
VAR
    matning : ARRAY [0..4] OF INT := [3(0), 1, 2];
    ruta : ARRAY [1..2, 1..3] OF REAL;
    text : STRING[20] := 'klar';
    ut AT %QW0 : INT;
END_VAR
    ut := matning[0];
END_PROGRAM
"""),
    ("globala_och_ovriga_varsorter", """
VAR_GLOBAL
    LARM : BOOL := FALSE;
END_VAR

VAR_GLOBAL CONSTANT
    VERSION : INT := 4;
END_VAR

FUNCTION_BLOCK Del
VAR_INPUT
    i1 : BOOL;
END_VAR
VAR_OUTPUT
    o1 : BOOL;
END_VAR
VAR_IN_OUT
    delad : INT;
END_VAR
VAR_TEMP
    tmp : BOOL;
END_VAR
VAR_EXTERNAL
    LARM : BOOL;
END_VAR
    tmp := i1 AND NOT LARM;
    o1 := tmp;
    delad := delad + 1;
END_FUNCTION_BLOCK
"""),
    ("slingor_och_kommentarer", """
PROGRAM Slingor
VAR
    i : INT;
    summa : DINT := 0;
    ut AT %QD0 : DINT;
END_VAR
    (* rakna ihop tio steg *)
    FOR i := 0 TO 9 BY 1 DO
        summa := summa + 1;
    END_FOR;
    WHILE summa > 100 DO
        summa := summa - 1;
    END_WHILE;
    REPEAT
        summa := summa + 1;
    UNTIL summa >= 0
    END_REPEAT;
    (* och lagg ut det *)
    ut := summa;
END_PROGRAM
"""),
    ("uttrycksformer", """
PROGRAM Uttryck
VAR
    a : REAL := 1.5;
    b : REAL;
    i : INT := INT#5;
    t : TIME := T#1h30m;
    s : STRING := 'ett ord';
    fl : BOOL;
END_VAR
    b := -a ** 2.0 + (a - 1.0) * 3.0;
    fl := NOT (i > 2) AND (i <= 10) OR (i <> 0);
    b := REAL_TO_LREAL(a) * 1.0;
END_PROGRAM
"""),
]


def _las(kalla):
    return las(kalla.strip() + "\n")


# ---- 1. kontrollen: ST-lagrets egen tur och retur ------------------------

@pytest.mark.parametrize("namn,kalla", KONSTRUKTIONER,
                         ids=[n for n, _ in KONSTRUKTIONER])
def test_kontroll_st_lagrets_egen_tur_och_retur(namn, kalla):
    """Kontroll, inte mätning. Gar den har inte igenom ar felet i ST-lagret och
    inte i PLCopen-exporten, och da far nasta prov inte anklaga exporten."""
    e = _las(kalla)
    assert las(skriv_enhet(e)) == e


# ---- 2. mätningen: PLCopen ut och in -------------------------------------

@pytest.mark.parametrize("namn,kalla", KONSTRUKTIONER,
                         ids=[n for n, _ in KONSTRUKTIONER])
def test_konstruktionen_overlever_sin_egen_import(namn, kalla):
    e = _las(kalla)
    xml = PX.skriv_projekt(e, projektnamn=namn)
    tillbaka = PX.las_projekt(xml)
    assert PX.avvikelser(e, tillbaka) == ()
    assert tillbaka == e


@pytest.mark.parametrize("namn,kalla", KONSTRUKTIONER,
                         ids=[n for n, _ in KONSTRUKTIONER])
def test_exportera_ar_stangd_om_turen_inte_haller(namn, kalla):
    """`exportera` gor turen och retur sjalv och faller om den inte holl.
    Ett XML som inte kommer tillbaka ar ingen export."""
    e = _las(kalla)
    xml = PX.exportera(e, projektnamn=namn)
    assert xml.startswith("<?xml")
    assert PX.las_projekt(xml) == e


# ---- 3. trasiga fixturer: exporten MASTE falla ---------------------------

def test_kommentar_med_kommentarslut_falls():
    """En kommentar som bar `*)` gar att bygga i modellen men inte att skriva
    som ST. Exporten far inte skriva en fil som kommer tillbaka stympad."""
    e = M.Enhet(pouer=(M.Pou("PROGRAM", "P", block=(
        M.Varblock("VAR", (M.Deklaration("a", T.Elementar("BOOL"),
                                         kommentar="slutar har *) och fortsatter"),)),
    )),))
    with pytest.raises(PX.ExportFel):
        PX.exportera(e)


def test_flerradig_kommentar_overlever_anda():
    """VANTAD FORLUST SOM INTE FANNS. Fixturen skrevs som en trasig fixtur --
    en kommentar med radbrytning trodde jag skulle komma tillbaka stympad.
    Den gor det inte: lexern tar hela `(* ... *)` som EN token och strippar
    bara kanterna. Provet star kvar med omvant pastaende, for en gissning som
    matningen kullkastade ar ett resultat och inte ett misstag att sopa undan."""
    e = M.Enhet(pouer=(M.Pou("PROGRAM", "P", block=(
        M.Varblock("VAR", (M.Deklaration("a", T.Elementar("BOOL"),
                                         kommentar="forsta raden\nandra raden"),)),
    )),))
    assert PX.las_projekt(PX.exportera(e)) == e


def test_kvalificerarordningen_falls():
    """TRASIG FIXTUR, och den enda RIKTIGA konstruktion i mätningen som inte
    overlever. `VAR NON_RETAIN CONSTANT` blir attributen `constant` och
    `nonretain` pa samma element, och XML-attribut har ingen ordning. Importen
    kan darfor bara aterskapa dem i EN ordning, och den ar inte kallans.

    Att fälla ar ratt svar: en fil som kommer tillbaka med kvalificerarna
    omkastade ar inte samma program for en lasare som bryr sig om ordningen,
    och vi vet inte om mottagaren gor det."""
    kalla = """
PROGRAM P
VAR NON_RETAIN CONSTANT
    a : INT := 1;
END_VAR
    a := a;
END_PROGRAM
"""
    e = _las(kalla)
    assert las(skriv_enhet(e)) == e          # kontroll: ST-lagret klarar den
    with pytest.raises(PX.ExportFel) as fel:
        PX.exportera(e)
    assert "NON_RETAIN CONSTANT" in str(fel.value)
    # och samma block i den ordning importen kan aterskapa GAR igenom
    e2 = _las(kalla.replace("NON_RETAIN CONSTANT", "CONSTANT NON_RETAIN"))
    assert PX.las_projekt(PX.exportera(e2)) == e2


def test_kommentar_som_inte_ar_stripad_falls():
    """Lexern strippar en kommentars kanter (`text[2:-2].strip()`). En modell
    med blanksteg i kanten kommer darfor tillbaka utan dem. Det ar en verklig
    skillnad och den ska fallas, inte tystas."""
    e = M.Enhet(pouer=(M.Pou("PROGRAM", "P", block=(
        M.Varblock("VAR", (M.Deklaration("a", T.Elementar("BOOL"),
                                         kommentar="  kant  "),)),
    )),))
    with pytest.raises(PX.ExportFel):
        PX.exportera(e)


def test_icke_ascii_falls():
    """Genererad ST ska vara ren ASCII hela vagen ut (skrivarens krav). En
    export som slapper igenom en umlaut har flyttat problemet till PLC:n."""
    e = M.Enhet(pouer=(M.Pou("PROGRAM", "P", block=(
        M.Varblock("VAR", (M.Deklaration("a", T.Elementar("BOOL"),
                                         kommentar="matare foer haal"),)),
    )),))
    e2 = M.Enhet(pouer=(M.Pou("PROGRAM", "P", block=(
        M.Varblock("VAR", (M.Deklaration("a", T.Elementar("BOOL"),
                                         kommentar=u"mätare"),)),
    )),))
    PX.exportera(e)                       # ren ASCII gar igenom
    with pytest.raises(PX.ExportFel):
        PX.exportera(e2)


def test_okand_typ_falls():
    class EgenTyp(T.Typ):
        def st(self):
            return "EGEN"

    e = M.Enhet(pouer=(M.Pou("PROGRAM", "P", block=(
        M.Varblock("VAR", (M.Deklaration("a", EgenTyp()),)),
    )),))
    with pytest.raises(PX.ExportFel):
        PX.skriv_projekt(e)


def test_tom_enhet_falls():
    """Ett projekt utan en enda POU ar inget projekt. Ett tomt dokument som
    valideras mot schemat ser ut som en lyckad export."""
    with pytest.raises(PX.ExportFel):
        PX.skriv_projekt(M.Enhet())


# ---- 4. trasiga fixturer: importen MASTE falla ---------------------------

def test_trasig_xml_falls():
    with pytest.raises(PX.Importfel):
        PX.las_projekt("<project>ej stangd")


def test_fel_namnrymd_falls():
    xml = PX.skriv_projekt(_las(KONSTRUKTIONER[0][1]))
    fel = xml.replace(PX.NS_PLCOPEN, "http://example.invalid/inte-plcopen")
    with pytest.raises(PX.Importfel):
        PX.las_projekt(fel)


def test_okand_pousort_i_filen_falls():
    xml = PX.skriv_projekt(_las(KONSTRUKTIONER[0][1]))
    fel = xml.replace('pouType="program"', 'pouType="hittepa"')
    with pytest.raises(PX.Importfel):
        PX.las_projekt(fel)


def test_annat_kroppssprak_an_st_falls():
    """PLCopen bar LD, FBD, IL och SFC ocksa. Vi kan bara ST, och en importor
    som svarar med en tom kropp pa en LD-fil ljuger."""
    xml = PX.skriv_projekt(_las(KONSTRUKTIONER[0][1]))
    fel = xml.replace("<ST>", "<IL>").replace("</ST>", "</IL>")
    with pytest.raises(PX.Importfel):
        PX.las_projekt(fel)


# ---- 5. det som faktiskt star i filen ------------------------------------

def test_adress_och_sakerhetsmarkning_star_i_xml():
    """Adressen har en plats i standarden (`address`); sakerhetsmarkningen har
    ingen och bor i `addData`. Bada ska SYNAS i filen -- en markning som bara
    finns i vart huvud gar inte att kontrollera."""
    e = _las(KONSTRUKTIONER[5][1])
    xml = PX.skriv_projekt(e)
    assert 'address="%IX0.0"' in xml
    assert PX.NS_SAKERHET in xml


def test_kroppen_ligger_i_st_elementet_inte_deklarationerna():
    """M-113 la HELA ST-texten i `<ST>`. Da provas ingenting av
    deklarationslagret. Kravet ar att deklarationerna bor i `<interface>` och
    att `<ST>` bara bar satserna."""
    e = _las(KONSTRUKTIONER[0][1])
    xml = PX.skriv_projekt(e)
    st_text = PX.kroppstext(xml, "Press")
    assert "END_VAR" not in st_text
    assert "vakt(IN := ST100_PEC_PART, PT := T#5s);" in st_text
    assert '<variable name="vakt"' in xml
    assert '<derived name="TON"' in xml


# ---- 5b. ar grinden overhuvudtaget kanslig? ------------------------------
#
# Att alla 63 bankprogram och tretton av fjorton konstruktioner gick igenom pa
# forsta forsoket ar ett misstankt resultat. En tur och retur som ALLTID sager
# LIKA mater ingenting. Darfor muteras FILEN -- ett attribut eller ett element
# tas bort ur den fardiga XML:en -- och grinden maste se skillnaden. Det ar
# samma grepp som M-148: mutera domaren i stallet for koden.

def _mutera(xml, fran, till):
    assert fran in xml, "mutationen bet inte: %r finns inte i filen" % fran
    return xml.replace(fran, till, 1)


def test_grinden_ser_att_adressen_forsvinner():
    e = _las(KONSTRUKTIONER[5][1])                  # lokaliserad_och_skyddad
    xml = PX.skriv_projekt(e)
    stympad = _mutera(xml, 'address="%IX0.0"', "")
    tillbaka = PX.las_projekt(stympad)
    assert tillbaka != e
    assert any("adress" in rad for rad in PX.avvikelser(e, tillbaka))


def test_grinden_ser_att_sakerhetsmarkningen_forsvinner():
    """Den viktigaste av de fyra. `skyddad` ar invariant I15:s barare, och den
    har INGEN plats i PLCopen -- den bor i `addData`. Om grinden inte sag att
    den forsvann vore exporten en tyst nedgradering av en sakerhetsmarkning."""
    e = _las(KONSTRUKTIONER[5][1])
    xml = PX.skriv_projekt(e)
    i = xml.index("<addData>")
    j = xml.index("</addData>") + len("</addData>")
    stympad = xml[:i] + xml[j:]
    tillbaka = PX.las_projekt(stympad)
    assert tillbaka != e
    assert any("skyddad" in rad for rad in PX.avvikelser(e, tillbaka))


def test_grinden_ser_att_kommentaren_forsvinner():
    e = _las(KONSTRUKTIONER[5][1])
    xml = PX.skriv_projekt(e)
    i = xml.index("<documentation>")
    j = xml.index("</documentation>") + len("</documentation>")
    stympad = xml[:i] + xml[j:]
    tillbaka = PX.las_projekt(stympad)
    assert tillbaka != e
    assert any("kommentar" in rad for rad in PX.avvikelser(e, tillbaka))


def test_grinden_ser_att_kvalificeraren_forsvinner():
    e = _las(KONSTRUKTIONER[6][1])                  # kvalificerare
    xml = PX.skriv_projekt(e)
    stympad = _mutera(xml, 'retain="true"', "")
    tillbaka = PX.las_projekt(stympad)
    assert tillbaka != e
    assert any("blockhuvudet" in rad for rad in PX.avvikelser(e, tillbaka))


def test_grinden_ser_att_kroppen_tommas():
    e = _las(KONSTRUKTIONER[0][1])                  # timer_ton
    xml = PX.skriv_projekt(e)
    kropp = PX.kroppstext(xml, "Press")
    stympad = xml.replace(_escape(kropp), "")
    tillbaka = PX.las_projekt(stympad)
    assert tillbaka != e
    assert any("kroppen" in rad for rad in PX.avvikelser(e, tillbaka))


def test_grinden_ser_att_en_typ_byts():
    e = _las(KONSTRUKTIONER[0][1])
    xml = PX.skriv_projekt(e)
    bytt = _mutera(xml, '<derived name="TON" />', '<derived name="TOF" />')
    tillbaka = PX.las_projekt(bytt)
    assert tillbaka != e
    assert any("typ" in rad for rad in PX.avvikelser(e, tillbaka))


def test_exporten_ar_deterministisk():
    """Samma modell ger byte-identisk fil, varje gang. Modulens docstring
    lovar det (tidsstampeln ar en fast strang och inte `now()`), och ett lofte
    utan prov ar en bon. En guldfil som andrar sig av sig sjalv mater
    ingenting."""
    for namn, kalla in KONSTRUKTIONER:
        a = PX.skriv_projekt(_las(kalla), projektnamn=namn)
        b = PX.skriv_projekt(_las(kalla), projektnamn=namn)
        assert a == b, namn
        assert PX.TIDSSTAMPEL_STANDARD in a


# ---- 6. schemat: en domare utanfor var egen kod --------------------------

def _lxml_eller_hoppa():
    try:
        import lxml.etree                                     # noqa: F401
    except ImportError:
        pytest.skip("lxml saknas; schemavalidering kraver den. Ett prov som "
                    "tyst gar igenom utan validator ar ett falskt gront.")


@pytest.mark.parametrize("namn,kalla", KONSTRUKTIONER,
                         ids=[n for n, _ in KONSTRUKTIONER])
def test_filen_validerar_mot_det_officiella_schemat(namn, kalla):
    _lxml_eller_hoppa()
    xml = PX.skriv_projekt(_las(kalla), projektnamn=namn)
    assert PX.validera_schema(xml) == ()


def test_schemat_faller_ett_trasigt_dokument():
    """En validator som aldrig sagt nej ar inte provad."""
    _lxml_eller_hoppa()
    xml = PX.skriv_projekt(_las(KONSTRUKTIONER[0][1]))
    fel = xml.replace('pouType="program"', 'pouType="hittepa"')
    assert PX.validera_schema(fel) != ()


# ---- 7. banken: 63 riktiga program ---------------------------------------

def _bankbyggen():
    import baslinjebank as BB
    from vc_assist_svc.plc.baslinje import Baslinje
    b = Baslinje()
    ut = []
    for post in BB.las_uppgifter():
        ut.append((post.get("task_id"), BB.bygg(post, b).st_kalla))
    return ut


_BANK = _bankbyggen()


@pytest.mark.parametrize("task_id,kalla", _BANK, ids=[t for t, _ in _BANK])
def test_bankens_program_overlever_exporten(task_id, kalla):
    e = las(kalla)
    xml = PX.exportera(e, projektnamn=task_id)
    assert PX.las_projekt(xml) == e
