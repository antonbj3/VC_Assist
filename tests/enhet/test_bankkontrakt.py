# -*- coding: utf-8 -*-
"""L0: bankkontraktet. Varje korning har en post, och varje post gar att falla.

`docs/spec/85_bankkontraktet.md`. Registret ar korningarnas EGNA deklarationer
(`BANKPOST` i varje `tests/protocol/kor_*.py`), lasta med AST.

Tva sparrar gor registret komplett AV KONSTRUKTION, och bada far bara ga at
ett hall:

  * **Ingen forraldralos korning.** En kor_*.py utan post ar en matning ingen
    vet om. `TAK_ODEKLARERADE` ar vad som faktiskt lamnades.
  * **Ingen post utan korning.** En post vars `under_prov` eller
    `facitkalla_filer` pekar pa en fil som inte finns ar ett pastaende utan
    tackning.

Och den barande kontrollen: `facitkalla_filer` far aldrig ligga inuti
`under_prov`. BENCH-4 stod gron i manader mot ett facit som raknades fram av
samma algoritm som domdes. Talet var perfekt och matte ingenting.

Tre listor nedan namnger det som INTE ar i ordning i dag. De ar inte
undantag - de ar skulden, med namn, och tak som bara far krympa. En tom lista
med ett tak pa noll ar det enda slutlaget.
"""
import ast
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import bankkontrakt as BK                      # noqa: E402

PROTOKOLL = os.path.join(_ROT, "tests", "protocol")
MATNINGAR = os.path.join(_ROT, "docs", "matningar")

# ---------------------------------------------------------------- sparrarna
#
# Satta 2026-09-05 (M-104) till det som FAKTISKT lamnades. Ett tak som satts
# hogre an det matta ar ett tak som inte mater nagot.

TAK_ODEKLARERADE = 0

# Korningen vars facit raknas fram av modulen den domer. Det ar BENCH-4:s form
# och den star har med namn i stallet for att skrivas bort.
TAUTOLOGISKA = {
    "kor_m85_databladets_tackning.py":
        "tackningen lases ut ur biblioteket av komponentdatablad.py sjalv - "
        "ett falt parsern missar rapporteras som ett falt filen inte bar, och "
        "ingen oberoende lasare av samma component.rsc finns i korningen",
}

# Korningar som mater utan att doma. De har inget som MASTE falla, och det ar
# deklarerat i posten med ordet SAKNAS i stallet for en formulering som ser ut
# som en grind.
UTAN_TRASIGT_FALL = {
    "kor_m63_specglapp.py": "raknar specens koder, domer inte",
    "kor_m75_vad_ett_spar_avslojar.py": "raknar vad ett spar avslojar, domer inte",
}

_MNUMMER = re.compile(r"^M-(\d+)$")


def registret():
    return BK.granska_registret(PROTOKOLL)


def _inuti(fil, under_prov):
    """Ligger `fil` i eller under nagon post i `under_prov`?

    Exakt likhet racker inte: `under_prov` far peka pa en katalog, och ett
    facit som lases ur en fil DARINNE ar lika tautologiskt som ett som lases
    ur modulen sjalv.
    """
    for m in under_prov:
        if fil == m:
            return m
        if fil.startswith(m.rstrip("/") + "/"):
            return m
        if m.startswith(fil.rstrip("/") + "/"):
            return m
    return None


def tautologiska(poster):
    """{korning: den delade filen} for varje post vars facit kommer ur koden."""
    ut = {}
    for p in poster:
        for f in p.facitkalla_filer:
            delad = _inuti(f, p.under_prov)
            if delad:
                ut[p.korning] = delad
    return ut


def saknade_filer(post):
    return [f for f in tuple(post.under_prov) + tuple(post.facitkalla_filer)
            if not os.path.exists(os.path.join(_ROT, f))]


# --------------------------------------------------------- registret i dag

def test_ingen_forraldralos_korning():
    """Varje kor_*.py maste ha en BANKPOST. Taket far bara krympa."""
    dom = registret()
    assert len(dom.odeklarerade) <= TAK_ODEKLARERADE, (
        "%d odeklarerade korningar, taket ar %d: %s\n"
        "Lagg en modulniva-BANKPOST overst i korningen (se "
        "docs/spec/85_bankkontraktet.md). En korning utan post ar en matning "
        "ingen vet om."
        % (len(dom.odeklarerade), TAK_ODEKLARERADE, ", ".join(dom.odeklarerade)))


def test_ingen_post_utan_korning():
    """Varje post maste peka pa filer som finns."""
    dom = registret()
    brister = []
    for p in dom.poster:
        for f in saknade_filer(p):
            brister.append("%s: %s finns inte" % (p.korning, f))
    assert not brister, "\n".join(brister)


def test_posterna_ar_giltiga():
    """Obligatoriska falt, kanda krav och pastaenden som gar att motbevisa.

    Den enda bristen som far sta kvar ar den tautologiska facitkallan, och
    den star namngiven i TAUTOLOGISKA.
    """
    dom = registret()
    kvar = [b for b in dom.brister
            if not any(b.startswith(k + ":") for k in TAUTOLOGISKA)]
    assert not kvar, "\n".join(kvar)


def test_facitkallan_ligger_utanfor_koden_som_provas():
    """DEN BARANDE KONTROLLEN, och den ar mekanisk.

    Ett facit ur samma algoritm som doms mater ingenting. Listan ar taket:
    en NY tautologisk post faller provet, och en lagad post ska tas bort ur
    TAUTOLOGISKA sa att taket krymper.
    """
    funna = tautologiska(registret().poster)
    nya = sorted(set(funna) - set(TAUTOLOGISKA))
    assert not nya, (
        "nya korningar vars facit kommer ur koden de domer: %s\n"
        "Peka ut ett facit UTANFOR under_prov (en annan implementation, en "
        "matning av verkligheten, geometri ur scenens egna matt, en manniskas "
        "facit skrivet fore korningen, eller en tidigare matning med "
        "M-nummer)." % ", ".join(nya))
    lagade = sorted(set(TAUTOLOGISKA) - set(funna))
    assert not lagade, (
        "%s star kvar i TAUTOLOGISKA men har inte langre facit ur koden den "
        "domer - ta bort raden sa att taket krymper" % ", ".join(lagade))


def test_varje_post_bar_ett_trasigt_fall():
    """En grind utan trasig fixtur ar en forhoppning som fatt ett filnamn.

    En korning som bara mater far deklarera det med ordet SAKNAS, men da star
    den har med namn och taket far bara krympa.
    """
    utan = {}
    for p in registret().poster:
        if any(t.startswith("SAKNAS") for t in p.trasiga_fall):
            utan[p.korning] = p.trasiga_fall[0]
    nya = sorted(set(utan) - set(UTAN_TRASIGT_FALL))
    assert not nya, ("nya korningar utan trasigt fall: %s" % ", ".join(nya))
    lagade = sorted(set(UTAN_TRASIGT_FALL) - set(utan))
    assert not lagade, ("%s bar nu ett trasigt fall - ta bort raden ur "
                        "UTAN_TRASIGT_FALL" % ", ".join(lagade))


def test_ingen_okand_facitkalla():
    """En korning vars facit ingen kan peka ut ar en korning ingen kan lita pa."""
    okanda = [p.korning for p in registret().poster
              if p.facitkalla.upper().startswith(("OKAND", "OKÄND"))]
    assert not okanda, (
        "%s saknar facitkalla. En korning utan utpekat facit mater att koden "
        "kor, inte att den har ratt." % ", ".join(okanda))


def test_matningarna_finns():
    """Ett M-nummer som varken ar en fil eller reserverat ar ett linterfel."""
    filer = os.listdir(MATNINGAR)
    with open(os.path.join(MATNINGAR, "RESERVERADE.md"), encoding="utf-8") as f:
        reserverade = set(re.findall(r"\bM-\d+\b", f.read()))
    saknas = []
    for p in registret().poster:
        for m in p.matningar:
            assert _MNUMMER.match(m), "%s: %r ar inget M-nummer" % (p.korning, m)
            if any(x.startswith(m + "_") for x in filer) or m in reserverade:
                continue
            saknas.append("%s: %s finns varken i docs/matningar/ eller "
                          "RESERVERADE.md" % (p.korning, m))
    assert not saknas, "\n".join(saknas)


def antal_deklarationer(sokvag):
    """Hur manga modulniva-BANKPOST filen har. Fler an en ar en tyst dom."""
    trad = ast.parse(open(sokvag, encoding="utf-8").read(), filename=sokvag)
    n = 0
    for sats in trad.body:
        if isinstance(sats, ast.Assign):
            n += sum(1 for m in sats.targets
                     if isinstance(m, ast.Name) and m.id == "BANKPOST")
    return n


def test_ingen_korning_deklarerar_tva_poster():
    """Tva BANKPOST i samma fil ar tva pastaenden dar ett laser.

    `las_bankpost` tar den FORSTA; python kor den SISTA. Hande 2026-09-05:
    tva agenter deklarerade samma korning, och den ena posten blev osynlig
    utan att nagot blev rott.
    """
    dubbla = []
    for f in sorted(os.listdir(PROTOKOLL)):
        if f.startswith("kor_") and f.endswith(".py"):
            n = antal_deklarationer(os.path.join(PROTOKOLL, f))
            if n > 1:
                dubbla.append("%s: %d BANKPOST" % (f, n))
    assert not dubbla, "\n".join(dubbla)


def test_fixtur_tva_poster_i_samma_fil_syns(tmp_path):
    fil = tmp_path / "kor_dubbel.py"
    fil.write_text("BANKPOST = %r\nBANKPOST = %r\n" % (_post(), _post()),
                   encoding="utf-8")
    assert antal_deklarationer(str(fil)) == 2


def test_kor_allt_har_en_post():
    """Den aggregerade korningen ar sjalv en post - annars star den utanfor."""
    poster = dict((p.korning, p) for p in registret().poster)
    assert "kor_allt.py" in poster
    assert poster["kor_allt.py"].under_prov


def test_deklarationen_lases_utan_import():
    """Posten lases ur filen, aldrig genom import.

    Flera korningar satter sys.path, oppnar filer eller startar processer
    redan pa modulniva. En lasning som importerar hade kort dem.
    """
    kalla = open(os.path.join(_ROT, "svc", "vc_assist_svc", "bankkontrakt.py"),
                 encoding="utf-8").read()
    trad = ast.parse(kalla)
    importerade = set()
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Import):
            importerade |= set(a.name for a in nod.names)
        elif isinstance(nod, ast.ImportFrom):
            importerade.add(nod.module or "")
    assert "importlib" not in importerade
    assert "__import__" not in kalla and "exec(" not in kalla


# ------------------------------------------------------- de trasiga fallen
#
# Grinden provas med poster som MASTE fallas. Utan dem mater proven ovan att
# koden kor, inte att den domer.

def _post(**andra):
    d = {"pastar": "en formaga som gar att motbevisa i en hel mening",
         "under_prov": ("svc/vc_assist_svc/klient.py",),
         "facit": "det ratta svaret",
         "facitkalla": "en annan implementation",
         "facitkalla_filer": ("docs/spec/85_bankkontraktet.md",),
         "trasiga_fall": ("nagot som maste fallas",),
         "kraver": ("inget",),
         "matningar": ()}
    d.update(andra)
    return d


def test_fixtur_hel_post_gar_igenom():
    """Kontrollen: den hela posten far INTE falla, annars mater fixturerna
    att granskningen sager nej till allt."""
    _p, brister = BK.granska_post("kor_x.py", _post())
    assert brister == []


def test_fixtur_facitkalla_inuti_under_prov_falls():
    _p, brister = BK.granska_post("kor_x.py", _post(
        facitkalla_filer=("svc/vc_assist_svc/klient.py",)))
    assert any("facitkallan ligger i koden som provas" in b for b in brister), brister


def test_fixtur_facitkalla_i_katalog_under_prov_falls():
    """Prefixfallet: under_prov far peka pa en katalog."""
    post = BK.Bankpost(korning="kor_x.py",
                       under_prov=("svc/vc_assist_svc/layout/",),
                       facitkalla_filer=("svc/vc_assist_svc/layout/matt.py",))
    assert tautologiska([post]) == {"kor_x.py": "svc/vc_assist_svc/layout/"}


def test_fixtur_post_utan_trasiga_fall_falls():
    _p, brister = BK.granska_post("kor_x.py", _post(trasiga_fall=()))
    assert any("trasiga_fall saknas" in b for b in brister), brister


def test_fixtur_pastar_som_etikett_falls():
    _p, brister = BK.granska_post("kor_x.py", _post(pastar="ogats grind"))
    assert any("etikett" in b for b in brister), brister


def test_fixtur_okant_krav_falls():
    _p, brister = BK.granska_post("kor_x.py", _post(kraver=("kubernetes",)))
    assert any("okant krav" in b for b in brister), brister


def test_fixtur_post_utan_facit_falls():
    for falt in ("facit", "facitkalla", "under_prov"):
        _p, brister = BK.granska_post("kor_x.py", _post(**{falt: ()}))
        assert any(falt + " saknas" in b for b in brister), (falt, brister)


def test_fixtur_post_som_pekar_pa_fil_som_inte_finns_falls():
    post = BK.Bankpost(korning="kor_x.py",
                       under_prov=("svc/vc_assist_svc/finns_inte.py",),
                       facitkalla_filer=("docs/spec/85_bankkontraktet.md",))
    assert saknade_filer(post) == ["svc/vc_assist_svc/finns_inte.py"]


def test_fixtur_odeklarerad_korning_syns(tmp_path):
    """En korning utan BANKPOST maste hamna bland de odeklarerade."""
    (tmp_path / "kor_utan.py").write_text('"""utan post."""\nX = 1\n',
                                          encoding="utf-8")
    (tmp_path / "kor_med.py").write_text(
        '"""med post."""\nBANKPOST = %r\n' % (_post(),), encoding="utf-8")
    dom = BK.granska_registret(str(tmp_path))
    assert dom.odeklarerade == ["kor_utan.py"]
    assert [p.korning for p in dom.poster] == ["kor_med.py"]


def test_fixtur_hopp_ar_aldrig_ett_godkannande():
    """En post vars krav inte ar uppfyllda hamnar bland de hoppade, med skal."""
    poster = [BK.Bankpost(korning="a.py", kraver=("inget",)),
              BK.Bankpost(korning="b.py", kraver=("vc", "strucpp"))]
    har, hoppas = BK.korbara(poster, ["strucpp"])
    assert [p.korning for p in har] == ["a.py"]
    assert hoppas[0][0].korning == "b.py" and hoppas[0][1] == "vc"


@pytest.mark.parametrize("kod", ["BANKPOST = 17", "BANKPOST = namn",
                                 "X = {'pastar': 'nej'}"])
def test_fixtur_trasig_deklaration_ar_ingen_post(tmp_path, kod):
    """Allt som inte ar en literal dict raknas som ODEKLARERAD, aldrig som en
    tom post som slinker igenom."""
    (tmp_path / "kor_trasig.py").write_text(kod + "\n", encoding="utf-8")
    dom = BK.granska_registret(str(tmp_path))
    assert dom.odeklarerade == ["kor_trasig.py"]
