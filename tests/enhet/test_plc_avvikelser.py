# -*- coding: utf-8 -*-
"""L1: avvikelserna mellan var ST-tolk och OpenPLC-kedjan, som permanenta fall.

Mönstret är `tests/enhet/test_st_svep_mot_strucpp.py`: varje konstruktion som
mätts gå isär får en egen rad här, med den uppmätta domen inskriven, så att en
förändring i någon av motorerna **fäller ett prov** i stället för att märkas
när någon råkar köra svepet igen.

Talen kommer ur **M-169** (kö A, punkt A8), körd av
`tests/protocol/kor_A8_avvikelserna.py`. Fyra områden där IEC 61131-3 antingen
tiger eller lämnar utfallet till implementationen:

* **heltalsspill** — matiec fäller det som går att räkna ut vid kompilering
  och släpper igenom exakt samma spill när det sker vid körning;
* **division med noll** — matiec fäller `10 / 0` men släpper `10 MOD 0`, och
  runtimen dödar PLC-uppgiften med SIGFPE;
* **TIME över dygnsgränsen** — TIME är en varaktighet utan gräns, men
  `TOD#25:00:00` och `D#2026-02-30` accepteras också;
* **strängar över deklarerad längd** — `STRING[n]` går inte att uttrycka i
  matiec alls, och en oanvänd sådan deklaration ger segmenteringsfel.

Standardkolumnen står som **oprövad paragraf** där repot inte kan citera
IEC 61131-3 (samma konvention som M-125). Ett "bör fungera" är inget belägg.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc import matiec as M          # noqa: E402
from vc_assist_svc.st import tolk as TK            # noqa: E402


def _matiec_finns():
    """matiec, eller ett uttalat skäl. Aldrig ett tyst grönt.

    Binären ligger normalt i `/tmp/opencode/matiec/` (M-165) och `/tmp` städas.
    Klienten faller tillbaka på `extrahera_ur_docker`, så ett missat prov här
    betyder att VARKEN binären ELLER dockeravbilden fanns — inte att grinden
    är trasig.
    """
    try:
        binar, lib = M.hitta_binar()
    except M.MatiecFel as fel:
        return None, str(fel)
    if not (os.path.isfile(binar) and os.path.isdir(lib)):
        return None, "matiec hittades på %r men filerna saknas" % (binar,)
    return binar, ""


_BINAR, _SKAL = _matiec_finns()
pytestmark = pytest.mark.skipif(
    _BINAR is None,
    reason=("matiec (iec2c) hittades inte, och den ÄR facit i det här provet. "
            "Sätt VC_ASSIST_MATIEC eller låt docker-avbilden "
            "wzy318/openplc:latest vara nåbar. Skäl: %s" % _SKAL))

KONFIGURATION = """
CONFIGURATION Conf
  RESOURCE Res ON PLC
    TASK T(INTERVAL := T#20ms, PRIORITY := 0);
    PROGRAM Inst WITH T : Main;
  END_RESOURCE
END_CONFIGURATION
"""


def program(dekl, kropp):
    return "PROGRAM Main\nVAR\n%s\nEND_VAR\n%s\nEND_PROGRAM\n" % (dekl, kropp)


def matiec_domer(dekl, kropp):
    """(accepterad, sammanslagen feltext) ur iec2c i strikt läge."""
    r = M.kompilera(program(dekl, kropp) + KONFIGURATION)
    return r.accepterad, " | ".join(m for _r, _k, m in r.fel)


def tolken_ger(dekl, kropp, las):
    """Tolkens värde efter ett scan, eller `Tolkfel`-texten."""
    try:
        t = TK.Tolk(program(dekl, kropp), {}, {})
        t.scan()
        return t.las(las)
    except TK.Tolkfel as fel:
        return TK.Tolkfel(str(fel))


# ============================================================ trasig fixtur

def test_trasig_fixtur_matiec_ar_strangare_an_tolken():
    """FIXTUREN FÖRE MEKANISMEN: `i : INT := 40000` skiljer motorerna.

    Tolken tar emot 40000 i en 16-bitars INT utan ett ord. matiec avvisar. Om
    det här provet blir grönt utan att skillnaden finns mäter hela filen
    ingenting.
    """
    ok, text = matiec_domer("  i : INT := 40000;", "  i := i;")
    assert ok is False, "matiec accepterade 40000 i en INT"
    assert "incompatible data type" in text.lower()
    assert tolken_ger("  i : INT := 40000;", "  i := i;", "I") == 40000


def test_kontrollfall_bada_godkanner():
    """Kontrollfallet åt andra hållet: `32766 + 1` ryms, båda godkänner.

    Utan ett fall som INTE divergerar mäter filen bara sin egen stränghet.
    """
    ok, _ = matiec_domer("  i : INT;", "  i := 32766 + 1;")
    assert ok is True
    assert tolken_ger("  i : INT;", "  i := 32766 + 1;", "I") == 32767


# ================================================================ heltalsspill

def test_spill_konstantvikning_falls_men_samma_spill_vid_korning_slipper():
    """M-169: matiec fäller `i := 32767 + 1` och släpper `i := i + 1`.

    Samma spill, samma typ, samma rad i standarden — och två olika domar,
    därför att den ena går att räkna ut vid kompilering. En användare som
    skriver konstanten får ett fel; en som skriver variabeln får -32768 i
    cellen.
    """
    ok_konst, text = matiec_domer("  i : INT;", "  i := 32767 + 1;")
    assert ok_konst is False
    assert "incompatible data types for ':='" in text.lower()

    ok_var, _ = matiec_domer("  i : INT := 32767;", "  i := i + 1;")
    assert ok_var is True

    # Tolken räknar i Pythons obegränsade heltal och ger samma svar i båda.
    assert tolken_ger("  i : INT;", "  i := 32767 + 1;", "I") == 32768
    assert tolken_ger("  i : INT := 32767;", "  i := i + 1;", "I") == 32768


def test_spill_uint_blir_negativt_i_tolken():
    """M-169: `u : UINT := 0; u := u - 1;` ger -1 i tolken.

    Ett negativt värde i en teckenlös typ. matiec godkänner texten; OpenPLC
    ger 65535. Tolken har ingen viddmodell alls (samma rot som M-125:s
    svepfall a09–a12).
    """
    ok, _ = matiec_domer("  u : UINT := 0;", "  u := u - 1;")
    assert ok is True
    assert tolken_ger("  u : UINT := 0;", "  u := u - 1;", "U") == -1


def test_spill_byte_plus_ett_falls_av_matiec_men_inte_av_oss():
    """M-169: `b : BYTE := 255; b := b + 1;` — matiec fäller '+' på BYTE.

    BYTE är en bitsträng, inte ett tal, och ADD är definierad över ANY_NUM.
    Vår tolk räknar 256 utan invändning.
    """
    ok, text = matiec_domer("  b : BYTE := 255;", "  b := b + 1;")
    assert ok is False
    assert "data type mismatch for '+'" in text.lower()
    assert tolken_ger("  b : BYTE := 255;", "  b := b + 1;", "B") == 256


# =========================================================== division med noll

def test_noll_division_med_literal_falls_men_mod_slipper():
    """M-169: matiec fäller `10 / 0` och släpper `10 MOD 0`.

    Asymmetri i samma kompilator, i samma sats, med samma nolldivisor. Domen
    över `/` kommer dessutom som ett TYPfel ('Data type mismatch'), inte som
    ett aritmetiskt — meddelandet pekar inte på nollan.
    """
    ok_div, text = matiec_domer("  i : INT;", "  i := 10 / 0;")
    assert ok_div is False
    assert "data type mismatch for '/'" in text.lower()

    ok_mod, _ = matiec_domer("  i : INT;", "  i := 10 MOD 0;")
    assert ok_mod is True, "matiec fäller numera MOD 0 — uppdatera M-169"


def test_noll_division_med_variabel_slipper_igenom_matiec():
    """M-169: `n : INT := 0; i := 10 / n;` kompilerar.

    Det är den farliga formen: nollan syns först vid körning, och då dör
    PLC-uppgiften med SIGFPE (M-169 §4, uppmätt i OpenPLC v4:s egen logg:
    `[task MAIN] terminated by signal 8 — other tasks keep running`).
    """
    ok, _ = matiec_domer("  i : INT; n : INT := 0;", "  i := 10 / n;")
    assert ok is True
    svar = tolken_ger("  i : INT; n : INT := 0;", "  i := 10 / n;", "I")
    assert isinstance(svar, TK.Tolkfel)
    assert "division by zero" in str(svar)


def test_noll_real_division_slipper_igenom_matiec_men_inte_tolken():
    """M-169: `1.0 / 0.0` kompilerar; tolken vägrar.

    OpenPLC ger `inf` (uppmätt, M-169 §4) och runtimen överlever. Vår tolk
    kastar Tolkfel och kan alltså inte ens uttrycka utfallet.
    """
    ok, _ = matiec_domer("  r : REAL;", "  r := 1.0 / 0.0;")
    assert ok is True
    svar = tolken_ger("  r : REAL;", "  r := 1.0 / 0.0;", "R")
    assert isinstance(svar, TK.Tolkfel)


# ==================================================== TIME över dygnsgränsen

@pytest.mark.parametrize("literal,ms", [
    ("T#25h", 90000000.0),
    ("T#1d1h", 90000000.0),
    ("T#100d", 8640000000.0),
])
def test_tid_over_dygnsgransen_ar_giltig_i_bada(literal, ms):
    """M-169: TIME är en VARAKTIGHET — den har ingen dygnsgräns.

    `T#100d` är 8 640 000 000 ms, alltså fyra gånger int32:s tak. Båda
    motorerna godkänner texten; OpenPLC sveper vid körning
    (M-125 t07: `TIME_TO_DINT(T#100d)` = 50 065 408).
    """
    ok, _ = matiec_domer("  t : TIME;", "  t := %s;" % literal)
    assert ok is True
    assert tolken_ger("  t : TIME;", "  t := %s;" % literal, "T") == ms


@pytest.mark.parametrize("dekl,sats", [
    ("  q : TOD;", "  q := TOD#25:00:00;"),
    ("  q : TOD;", "  q := TOD#12:99:00;"),
    ("  dd : DATE;", "  dd := D#2026-02-30;"),
])
def test_matiec_godkanner_klockslag_och_datum_som_inte_finns(dekl, sats):
    """M-169: matiec kontrollerar inte TOD:s och DATE:s VÄRDEOMRÅDE.

    `TOD#25:00:00` är en tid på dygnet som inte finns, `TOD#12:99:00` har 99
    minuter, och 30 februari finns inte. Alla tre kompilerar. Det är den enda
    plats där matiec är MILDARE än vår kedja i det här provet — vår läsare
    avvisar TOD- och DATE-literaler helt, och den strängheten är därför inte
    en läcka utan ett omfångsbeslut.
    """
    ok, _ = matiec_domer(dekl, sats)
    assert ok is True


def test_tolken_avvisar_tod_och_date_helt():
    """Motstycket: vår läsare kan inte TOD/DATE, och säger det."""
    svar = tolken_ger("  q : TOD;", "  q := TOD#25:00:00;", "Q")
    assert isinstance(svar, TK.Tolkfel)
    assert "TOD" in str(svar)


def test_tidsenheter_i_fel_ordning_falls_av_bada():
    """Kontrollfall: `T#5s10m` fälls i båda. Enheterna ska stå fallande."""
    ok, _ = matiec_domer("  t : TIME;", "  t := T#5s10m;")
    assert ok is False
    svar = tolken_ger("  t : TIME;", "  t := T#5s10m;", "T")
    assert isinstance(svar, TK.Tolkfel)


# ====================================== strängar över sin deklarerade längd

def test_string_med_langd_tappar_variabeln_ur_scope_i_matiec():
    """M-169: `s : STRING[4]` deklareras, och sedan finns inte `s`.

    Det är standardens egen form för en sträng med maxlängd. matiec parsar
    deklarationen men registrerar aldrig namnet, så första användningen ger
    'Variable not declared in this scope'. Frågan "vad händer med en sträng
    över sin deklarerade längd" går därför **inte att ställa** i
    OpenPLC-kedjan — det är svaret, och det är ett annat svar än ett värde.
    """
    ok, text = matiec_domer("  s : STRING[4];", "  s := 'abcd';")
    assert ok is False
    assert "not declared in this scope" in text.lower()


def test_string_med_langd_utan_bruk_ger_segmenteringsfel():
    """M-169: en OANVÄND `STRING[4]`-deklaration får iec2c att segfaulta.

    Deterministiskt: tre körningar, tre gånger returkod -11 och tom utdata.
    Vår klient klassar det fail-closed som AVVISAR med returkoden i texten —
    det är rätt riktning, men skälet är inte lösningens.
    """
    kod = program("  s : STRING[4];\n  i : INT;", "  i := 1;") + KONFIGURATION
    binar, lib = M.hitta_binar()
    import tempfile
    kat = tempfile.mkdtemp(prefix="a8_segv_")
    try:
        stfil = os.path.join(kat, "p.st")
        with open(stfil, "w", encoding="utf-8") as f:
            f.write(kod)
        k = subprocess.run([binar, "-f", "-I", lib, "-T", kat, stfil],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           cwd=kat, timeout=30)
        assert k.returncode == -11, (
            "iec2c gav returkod %s, inte SIGSEGV (-11). Har matiec bytts ut "
            "ska M-169 mätas om." % k.returncode)
    finally:
        import shutil
        shutil.rmtree(kat, ignore_errors=True)

    # Klienten översätter kraschen till ett fail-closed AVVISAR.
    r = M.kompilera(kod)
    assert r.accepterad is False
    assert any("-11" in m for _r, _k, m in r.fel)


def test_string_utan_langd_gar_igenom_och_tolken_har_ingen_grans():
    """M-169: `STRING` utan längd kompilerar, och tolken har ingen gräns alls.

    30 tecken i en `STRING` ger LEN = 30 i tolken. Att OpenPLC-kedjan har en
    egen maxlängd är inte mätt — TIME och STRING mappas inte till
    bildtabellen (`domare_openplc._karta_for_post`), så värdet går inte att
    läsa ut över OPC UA.
    """
    ok, _ = matiec_domer(
        "  s : STRING; n : INT;",
        "  s := '123456789012345678901234567890';\n  n := LEN(s);")
    assert ok is True
    assert tolken_ger(
        "  s : STRING; n : INT;",
        "  s := '123456789012345678901234567890';\n  n := LEN(s);", "N") == 30
