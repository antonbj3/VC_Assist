# -*- coding: utf-8 -*-
"""Ordlistegrinden: en spärr mot ordlistor som avgör en dom (M-98).

Tre gånger har samma felklass mätts, och varje gång i en ny grind:

  M-94 fynd 1  `text.NEKANDE` tystade ärlighetsgrinden av vilket nekande ord
               som helst — "Layouten ar klar" fälldes, "Layouten ar klar utan
               problem" gick fri.
  M-94 fynd 4  samma lista filtrerade bort `bevis_ur_simulering`:s egen
               målklass: "Simuleringen bevisar att inga kollisioner finns".
  M-98         en KOPIA av listan i `oga.py` tystade ögongrinden: "Ogat sa
               PASS och inget fel uppstod" gav tomt.

Tre av samma sort är inte tre olyckor, det är en felklass. Den här filen
mekaniserar frågan i två spärrar:

  1. **Ingen litteral ordlista får bära två storheter.** En lista som bär
     både felord och bara negationer måste vara SAMMANSATT ur de listor som
     bär var sin. Taket är noll, och kriteriet har ingen undantagslista.
  2. **Kopierade ordlistor ska vara sedda.** `harness/text.py` säger själv
     varför listorna ligger på ett ställe; registret såg inte att regeln
     bröts. Taket får bara gå nedåt.

Trasiga fixturer nedan: varje spärr har ett träd där den fäller, byggt ur den
verkliga listan som föll — `oga.py`:s `NEKANDE_OGONORD` som den stod före
M-98, ord för ord.
"""
import os
import shutil
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import skuld as S                     # noqa: E402
from vc_assist_svc.harness import text as Tx             # noqa: E402

# Taket för kopierade ordlistor. MÄTT 2026-09-05 (M-98). Spärren får bara gå
# NEDÅT — en ny kopia är en ny plats där två listor kan glida isär utan att
# någon ser det.
#
# Talet gick 11 → 13 inom två timmar efter att spärren skrevs: en annan agent
# lade `_RANGORDNING` i en tredje modul (`llm/urval.py`), och namnet stod
# redan i `api_index.py` och `verktyg/katalog.py`. Det är spärren som fungerar,
# inte spärren som är trasig — och den rätta åtgärden när talet stiger är att
# NAMNGE paret i KOPIOR nedan, aldrig att bara skriva upp talet.
KOPIOR_TAK = 13

# Paren som mätningen namnger. Står här och inte bara som ett tal, därför att
# ett tak utan innehåll slutar mäta sin egen storhet: den dag ett par
# försvinner och ett nytt tillkommer står talet stilla.
KOPIOR = (
    ("svc/vc_assist_svc/guldgrind.py", "DALIGA_ORD",
     "ext/vc_addon/vc_assist/oga_kontrakt.py", "_FYNDORD"),
    ("svc/vc_assist_svc/plan/forfining.py", "ANDELSER",
     "svc/vc_assist_svc/plan/lasning.py", "_ANDELSER"),
    ("svc/vc_assist_svc/harness/oga.py", "GODKANNANDEORD",
     "svc/vc_assist_svc/harness/text.py", "FRAMGANGSMARKORER"),
    ("svc/vc_assist_svc/st/lexer.py", "NYCKELORD",
     "svc/vc_assist_svc/st/modell.py", "VARSORTER"),
    ("svc/vc_assist_svc/harness/oga.py", "BARA_NEGATION_OGA",
     "svc/vc_assist_svc/harness/text.py", "BARA_NEGATION"),
    ("svc/vc_assist_svc/st/skrivare.py", "JAMFORELSER",
     "svc/vc_assist_svc/st/validator.py", "JAMFORELSER"),
    ("svc/vc_assist_svc/guldgrind.py", "INTE_NONE",
     "ext/vc_addon/vc_assist/oga_kontrakt.py", "_INTE_NONE"),
    ("ext/vc_addon/vc_assist/plats.py", "WINDOWSPLATTFORMAR",
     "install/upptackt.py", "WINDOWSPLATTFORMAR"),
    ("svc/vc_assist_svc/guldgrind.py", "OBLIGATORISKA_SEKTIONER",
     "svc/vc_assist_svc/forlopp/yta.py", "OBLIGATORISKA_SEKTIONER"),
    ("svc/vc_assist_svc/verktyg/matning.py", "_YTOR_LAYOUT",
     "svc/vc_assist_svc/verktyg/robotik.py", "_YTOR_LAYOUT"),
    ("svc/vc_assist_svc/api_index.py", "_RANGORDNING",
     "svc/vc_assist_svc/verktyg/katalog.py", "_RANGORDNING"),
    # Tredje kopian av samma namn, tillkommen 2026-09-05 medan spärren skrevs.
    ("svc/vc_assist_svc/api_index.py", "_RANGORDNING",
     "svc/vc_assist_svc/llm/urval.py", "_RANGORDNING"),
    ("svc/vc_assist_svc/llm/urval.py", "_RANGORDNING",
     "svc/vc_assist_svc/verktyg/katalog.py", "_RANGORDNING"),
)

# Ordlistan som den stod i oga.py före M-98, ord för ord. Den är fixturen:
# grinden ska fälla exakt den, och den är hämtad ur repots egen historia och
# inte hittad på.
NEKANDE_OGONORD_FORE_M98 = (
    '("fail", "inconclusive", "inte", "icke", "ingen", "inget",\n'
    ' "not gold", "underkand", "underk\\u00e4nd", "rott", "r\\u00f6tt",\n'
    ' "avbrots", "avbr\\u00f6ts", "utan att", "aldrig", "saknas",\n'
    ' "not ", "no ")')


def _trad(tmp_path, moduler):
    """Ett litet träd med en riktig harness/text.py och modulerna ovanpå.

    text.py kopieras och skrivs inte om: grinden hämtar sina två storheter ur
    den modul som äger delningen, och en fixtur som skrev en egen text.py
    hade mätt fixturens ordlista i stället för repots.
    """
    rot = tmp_path / "trad"
    harness = rot / "svc" / "vc_assist_svc" / "harness"
    harness.mkdir(parents=True)
    shutil.copy(os.path.join(_ROT, "svc", "vc_assist_svc", "harness",
                             "text.py"), str(harness / "text.py"))
    for namn, innehall in moduler.items():
        stig = rot / "svc" / namn
        stig.parent.mkdir(parents=True, exist_ok=True)
        stig.write_text(innehall, encoding="utf-8")
    return str(rot)


# ---- 1. spärren mot en lista som bär två storheter -----------------------

def test_kontrollen_faller_ordlistan_som_foll(tmp_path):
    """TRASIG FIXTUR: `oga.NEKANDE_OGONORD` som den stod före M-98.

    Listan bar "saknas", "avbrots" och "avbröts" (felord ur text.FELORD) i
    samma tupel som "inte", "ingen" och "aldrig" (bara negationer).
    Ögongrinden frågade unionen och tystnade av vilket av dem som helst.

    "fail" och "inconclusive" står INTE bland felorden här, och det är rätt:
    kärnorna är text.py:s, och den listan känner "failed", inte "fail". Ett
    enda ord ur var storhet räcker för att listan ska bära två storheter.
    """
    rot = _trad(tmp_path, {"grind.py": "NEKANDE_OGONORD = %s\n"
                                       % NEKANDE_OGONORD_FORE_M98})
    traffar = S.ordlistor_med_tva_storheter(rot)
    assert len(traffar) == 1, traffar
    fil, _rad, namn, felord, negationer = traffar[0]
    assert namn == "NEKANDE_OGONORD"
    assert fil.replace(os.sep, "/") == "svc/grind.py"
    assert felord == ["avbrots", "avbröts", "saknas"]
    assert "inte" in negationer and "aldrig" in negationer


def test_samma_lista_sammansatt_gar_fri(tmp_path):
    """Den andra riktningen, och hela lagningen: samma ord, men delade.

    Kriteriet är strukturellt. En sammansatt lista BÄR sina delar öppet, och
    då går var storhet att fråga om för sig — vilket är precis vad
    `_obestridd_sats` och `nekar_pastaendet` gör i dag.
    """
    kod = ('UNDERKANNANDEORD = ("fail", "inconclusive", "not gold",\n'
           '                    "underkand", "avbrots", "saknas")\n'
           'BARA_NEGATION_OGA = ("inte", "icke", "ingen", "inget",\n'
           '                     "utan att", "aldrig", "not ", "no ")\n'
           'NEKANDE_OGONORD = UNDERKANNANDEORD + BARA_NEGATION_OGA\n')
    rot = _trad(tmp_path, {"grind.py": kod})
    assert S.ordlistor_med_tva_storheter(rot) == []


def test_en_lista_med_bara_en_storhet_anklagas_inte(tmp_path):
    """En ren felordlista och en ren negationslista är precis vad spärren
    vill se, och ingen av dem får bli ett fynd."""
    rot = _trad(tmp_path, {
        "fel.py": 'FELORD_HAR = ("fail", "error", "timeout", "saknas")\n',
        "neg.py": 'NEG_HAR = ("inte", "ingen", "inget", "aldrig")\n'})
    assert S.ordlistor_med_tva_storheter(rot) == []


def test_grinden_kastar_nar_karnorna_inte_gar_att_hitta(tmp_path):
    """S10: en grind vars indata försvunnit ska säga det, aldrig svara
    "inga fynd". Utan delningen i text.py finns ingen storhet att mäta mot."""
    rot = tmp_path / "utan_text"
    (rot / "svc").mkdir(parents=True)
    (rot / "svc" / "grind.py").write_text(
        "NEKANDE = %s\n" % NEKANDE_OGONORD_FORE_M98, encoding="utf-8")
    with pytest.raises(ValueError) as info:
        S.ordlistor_med_tva_storheter(str(rot))
    assert "FELORD" in str(info.value)


def test_karnorna_kommer_ur_texts_egen_delning():
    """Grinden får inte bära en kopia av den lista den dömer om — då hade den
    mätt sin egen avskrift. Kärnorna ska vara text.py:s, ord för ord."""
    felord, negationer = S._karnorna(S.ordlistor(_ROT))
    assert felord == frozenset(o.strip().lower() for o in Tx.FELORD)
    assert negationer == frozenset(o.strip().lower() for o in Tx.BARA_NEGATION)


def test_ingen_ordlista_i_repot_bar_tva_storheter():
    """SPÄRREN. Taket är noll och har ingen undantagslista.

    MÄTT 2026-09-05 med samma grind mot tre utcheckningar:
      före M-95   2 träffar (`text.NEKANDE`, `oga.NEKANDE_OGONORD`)
      före M-98   1 träff  (`oga.NEKANDE_OGONORD`)
      efter M-98  0
    """
    traffar = S.ordlistor_med_tva_storheter(_ROT)
    assert not traffar, "\n".join(
        "%s:%d %s — felord %s, negationer %s"
        % (f, r, n, ", ".join(fe), ", ".join(ne))
        for f, r, n, fe, ne in traffar)


# ---- 2. registret över kopierade ordlistor -------------------------------

def test_kontrollen_hittar_en_kopierad_ordlista(tmp_path):
    """TRASIG FIXTUR för kopieregistret: samma lista i två filer."""
    lista = ('("plocka", "placera", "flytta", "koppla", "spara", "starta",\n'
             '  "stoppa")\n')
    rot = _trad(tmp_path, {"a.py": "HANDLINGAR = %s" % lista,
                           "b.py": "STEG = %s" % lista})
    par = S.kopierade_ordlistor(rot)
    assert len(par) == 1, par
    assert sorted((par[0][1], par[0][3])) == ["HANDLINGAR", "STEG"]
    assert par[0][4] == 7


def test_ett_femordigt_sammantraffande_ar_ingen_kopia(tmp_path):
    """Den andra riktningen, och gränsens mätreferens.

    Fördelningen av parvis överlapp över repots 163 ordlistor går 19 par vid
    ≥4, 7 vid ≥5, 6 vid ≥6 och 4 vid ≥7 (mätt 2026-09-05). Knäcken ligger
    mellan 4 och 5, och gränsen står på 6 så att ett femordigt
    sammanträffande inte blir ett fynd.
    """
    rot = _trad(tmp_path, {
        "a.py": 'A = ("ett", "tva", "tre", "fyra", "fem", "sex")\n',
        "b.py": 'B = ("ett", "tva", "tre", "fyra", "fem", "sju")\n'})
    assert S.kopierade_ordlistor(rot) == []


def test_samma_namn_raknas_som_kopia_oavsett_storlek(tmp_path):
    """Ett delat namn är ingen slump. `WINDOWSPLATTFORMAR` står i två filer
    med tre ord, och det är en kopia även om den är kort."""
    rot = _trad(tmp_path, {
        "a.py": 'PLATTFORMAR = ("win32", "cygwin", "msys")\n',
        "b.py": '_PLATTFORMAR = ("win32", "linux", "darwin")\n'})
    par = S.kopierade_ordlistor(rot)
    assert len(par) == 1, par
    assert par[0][4] == 1


def test_exportlistan_ar_ingen_ordlista(tmp_path):
    """`__all__` är Pythons exportlista och dömer ingenting. Utan undantaget
    stod den ensam för 43 av de identiska paren i repot (mätt 2026-09-05)."""
    rot = _trad(tmp_path, {
        "a.py": '__all__ = ["a", "b", "c", "d", "e", "f", "g"]\n',
        "b.py": '__all__ = ["a", "b", "c", "d", "e", "f", "g"]\n'})
    assert S.kopierade_ordlistor(rot) == []


def test_inga_nya_kopierade_ordlistor():
    """SPÄRREN, och den får bara gå nedåt.

    En delad ordlista kan vara rätt. Det som inte får hända är att en ny
    uppstår utan att någon ser den: `harness/text.py` säger själv att
    listorna ligger på ett ställe just för att en kopia blir två listor så
    snart någon rättar den ena, och `oga.py` bröt den regeln utan att något
    frågade.
    """
    par = S.kopierade_ordlistor(_ROT)
    assert len(par) <= KOPIOR_TAK, "\n".join(
        "%s.%s <-> %s.%s (%d gemensamma)" % p for p in par)


def test_de_namngivna_paren_star_kvar():
    """Ett tak utan innehåll slutar mäta sin egen storhet: försvinner ett par
    och tillkommer ett annat står talet stilla. Paren namnges därför."""
    funna = set((a, na, b, nb) for a, na, b, nb, _n in
                S.kopierade_ordlistor(_ROT))
    nya = sorted(funna - set(KOPIOR))
    assert not nya, "\n".join("%s.%s <-> %s.%s" % p for p in nya)


def test_den_kopia_som_redan_glidit_isar_star_i_registret():
    """Att kopieregistret inte är teoretiskt, mätt.

    `guldgrind.DALIGA_ORD` och `oga_kontrakt._FYNDORD` läser samma
    ögonrapport och delar tolv ord — men den första bär dessutom `CEILING`,
    som den andra med flit lagt i `_OSAKERORD`. Kopian HAR glidit isär.
    """
    par = dict(((a, na, b, nb), n) for a, na, b, nb, n
               in S.kopierade_ordlistor(_ROT))
    assert par.get(("svc/vc_assist_svc/guldgrind.py", "DALIGA_ORD",
                    "ext/vc_addon/vc_assist/oga_kontrakt.py",
                    "_FYNDORD")) == 12
