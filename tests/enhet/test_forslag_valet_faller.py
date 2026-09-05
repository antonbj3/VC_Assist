# -*- coding: utf-8 -*-
"""L1 for FORSLAGEN: nar valet faller ska grinden namna vad som gar i stallet.

Grinden i `plan/motsagelse.py` har fyra domar, och `VALET_FALLER` betyder per
DEFINITION att villkoren gar att uppfylla - bara inte med den komponent som
valts. Domen vet alltsa redan att ett alternativ finns. Fore det har provet sa
den bara vilken SORTS atgard som behovdes ("byt komponent"), aldrig VILKEN
maskin. Ett besked som inte namner nagot att byta till lamnar hela arbetet kvar
hos operatoren.

FYRA REGLER SOM PROVEN HALLER GRINDEN TILL

  1. Aldrig ett namn utan skal. Varje forslag bar TALET som avgjorde, dess
     enhet och varifran talet kom.
  2. Hogst en handfull. En lista pa 200 robotar ar samma fel som att inte
     svara, och sorteringsordningen ska ha ett motiv som star skrivet.
  3. Inget forslag nar grinden inte vet. Saknas talet i katalogen ar svaret att
     det saknas - `OKANT` ar aldrig ett godkannande (I3).
  4. `OMOJLIG` foreslar ALDRIG en komponent. Ar kraven motsagelsefulla i sig
     hjalper ingen maskin, och ett forslag dar hade lurat anvandaren att tro
     att problemet ligger i komponentvalet.

TRASIG FIXTUR FORE MEKANISMEN: `test_F1...` och `test_F2...` ar biblioteket dar
INGENTING racker och biblioteket dar talet saknas. De ska ge ett nej med skal,
aldrig en gissning, och de skrevs fore koden de provar.

INGET LEVANDE BIBLIOTEK KRAVS. Sokskiktet ar en attrapp som speglar
`katalogsok.Katalog.sok`:s publika yta, inklusive dess regel att en BRED fraga
far ett sammandrag och INGA rader (M-60). Just den regeln ar det som gor
uppraakningen svar, och den provas darfor har i stallet for att upptackas i
drift.

Kors utan VC, utan bibliotek och utan natverk.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.plan import forslag as FO                 # noqa: E402
from vc_assist_svc.plan import motsagelse as MO              # noqa: E402
from vc_assist_svc.plan import storheter as ST               # noqa: E402
from vc_assist_svc.plan import villkorssprak as VS           # noqa: E402
from vc_assist_svc.plan.harkomst import Harkomst             # noqa: E402
from vc_assist_svc.plan.spec import (Del, DetaljeradSpec,    # noqa: E402
                                     Grundbegaran, Omrade)


# ======================================================================
# ATTRAPPEN: sokskiktets publika yta, i minnet
# ======================================================================

class Traff(object):
    """Samma falt som katalogsok.Traff, sa langt forslaget laser dem."""

    def __init__(self, namn, tillverkare="", rackvidd_mm=None,
                 nyttolast_kg=None, sokvag="", utfasad=False, familj="",
                 kategori=""):
        self.namn = namn
        self.tillverkare = tillverkare
        self.rackvidd_mm = rackvidd_mm
        self.nyttolast_kg = nyttolast_kg
        self.sokvag = sokvag or ("C:/lib/%s.vcmx" % namn.replace(" ", "_"))
        self.utfasad = utfasad
        self.familj = familj
        self.kategori = kategori


class Svar(object):
    def __init__(self, totalt, traffar, sammandrag=None):
        self.totalt = totalt
        self.traffar = list(traffar)
        self.sammandrag = sammandrag


class Attrappsok(object):
    """`sok()` med katalogsok.Katalog:s kontrakt, over en handfull poster.

    BRED ar attrappens motsvarighet till katalogsok.BRED_FRAGA (40, satt av
    M-60): over sa manga traffar lamnar sokskiktet ett SAMMANDRAG per
    tillverkare och INGA rader. Attrappen bar talet som en parameter for att
    provet ska kunna stalla en bred fraga utan att behova 40 poster.
    """

    def __init__(self, poster, bred=40):
        self.poster = list(poster)
        self.bred = bred
        self.fragor = []            # varje anrop, for rakning i provet

    def sok(self, fraga="", tillverkare="", kategori="", har_parameter="",
            familj="", min_rackvidd_mm=None, min_nyttolast_kg=None,
            med_utfasade=False, max_rader=10):
        self.fragor.append({"fraga": fraga, "tillverkare": tillverkare,
                            "min_rackvidd_mm": min_rackvidd_mm})
        ut = []
        for t in self.poster:
            if t.utfasad and not med_utfasade:
                continue
            if min_rackvidd_mm is not None:
                # En komponent utan angiven rackvidd har inte rackvidden noll.
                if t.rackvidd_mm is None or t.rackvidd_mm < min_rackvidd_mm:
                    continue
            if min_nyttolast_kg is not None:
                if t.nyttolast_kg is None or t.nyttolast_kg < min_nyttolast_kg:
                    continue
            if fraga and fraga.lower() not in t.namn.lower():
                continue
            if tillverkare and tillverkare.lower() != t.tillverkare.lower():
                continue
            if familj and familj.lower() != t.familj.lower():
                continue
            ut.append(t)
        ut.sort(key=lambda t: (len(t.namn), t.tillverkare, t.namn))
        if len(ut) > self.bred:
            fordelning = {}
            for t in ut:
                fordelning[t.tillverkare] = fordelning.get(t.tillverkare, 0) + 1
            return Svar(len(ut), [], fordelning)
        return Svar(len(ut), ut[:max(int(max_rader), 1)], None)


# ======================================================================
# GEMENSAMT: en bestallning vars robot inte racker
# ======================================================================

def _harkomst(belagg):
    return Harkomst("begaran", belagg)


def _spec(rackvidd_krav=2050.0, cell=(6000.0, 6000.0)):
    """En cell med en robot, och ett rackviddskrav roboten inte klarar."""
    begaran = Grundbegaran(
        "prov", "Bygg en cell med en robot. Roboten ska na bade bandet och "
        "pallplatsen, %g mm. Cellen ar %g x %g mm."
        % (rackvidd_krav, cell[0], cell[1]), "operator")
    delar = [Del("robot", "file:///vald_robot.vcm", 1, "robot",
                 [500.0, 500.0, 1400.0], 272.0)]
    villkor = [VS.Typvillkor(
        "rackvidd", "geometri", "del.robot.rackvidd_mm", "ge", rackvidd_krav,
        _harkomst("Roboten ska na bade bandet och pallplatsen"),
        "roboten maste na %g mm" % rackvidd_krav)]
    omrade = Omrade(cell[0], cell[1], 3000.0, 200.0,
                    _harkomst("Cellen ar %g x %g mm" % (cell[0], cell[1])))
    return DetaljeradSpec("prov", begaran, delar=delar, villkor=villkor,
                          omrade=omrade)


def _dom(sokport, rackvidd_krav=2050.0, vald_rackvidd=1650.0, cell=(6000.0, 6000.0),
         extra_villkor=(), datablad=None):
    spec = _spec(rackvidd_krav, cell)
    for v in extra_villkor:
        spec.villkor.append(v)
    blad = {"robot": {"rackvidd_mm": vald_rackvidd}}
    if datablad:
        blad = datablad
    return MO.granska(spec.villkor, ST.Faktarum(spec, blad), spec,
                      sokport=sokport)


def _forslaget(dom):
    for k in dom.krockar:
        if k.forslag is not None:
            return k.forslag
    return None


# En liten robotbank. Talen ar attrappens egna, inte biblioteket - provet ska
# vara gront ocksa pa en maskin utan Visual Components.
def _bank():
    return [
        Traff("IRB 1200-5/0.9", "ABB", rackvidd_mm=901.0),
        Traff("IRB 2600-12/1.65", "ABB", rackvidd_mm=1650.0),
        Traff("IRB 4600-60/2.05", "ABB", rackvidd_mm=2050.0),
        Traff("IRB 6700-150/3.20", "ABB", rackvidd_mm=3200.0),
        Traff("KR 16 R2010", "KUKA", rackvidd_mm=2013.0),
        Traff("KR 60-3", "KUKA", rackvidd_mm=2429.0),
        Traff("M-20iD/25", "Fanuc", rackvidd_mm=1831.0),
        Traff("R-2000iC/165F", "Fanuc", rackvidd_mm=2655.0),
        # Utan deklarerad rackvidd. Far ALDRIG foreslas: ett falt som saknas
        # ar inte noll, och ett namn utan tal ar en gissning.
        Traff("Okand robot", "Nachi", rackvidd_mm=None),
    ]


# ======================================================================
# F. DE TRASIGA FIXTURERNA - skrivna fore mekanismen
# ======================================================================

def test_F1_ingen_komponent_i_biblioteket_racker_ger_VALET_FALLER_utan_forslag():
    """Kravet, ordagrant ur uppdraget: en bestallning dar ingen komponent i
    biblioteket racker maste ge VALET_FALLER UTAN forslag och saga varfor -
    inte tomt, inte pahittat.

    Domen ar kvar pa VALET_FALLER och inte OMOJLIG, och det ar med flit:
    biblioteket ar inte varlden. En robot som nar 9 000 mm finns, den ar bara
    inte installerad har.
    """
    port = Attrappsok(_bank())
    dom = _dom(port, rackvidd_krav=9000.0)
    assert dom.dom == MO.VALET_FALLER
    f = _forslaget(dom)
    assert f is not None, "grinden sa ingenting om vad som gar i stallet"
    assert f.alternativ == []
    text = f.text()
    assert "9000" in text
    # Skalet ska bara TAL: hur manga som provades och hur manga som bar faltet.
    assert "0 av" in text
    assert "bar" in text or "deklarerar" in text
    # ... och det far aldrig lata som att kravet ar omojligt.
    assert "omojlig" not in text.lower()


def test_F2_en_komponent_utan_talet_foreslas_aldrig():
    """Regel 3: saknas rackvidden i katalogen ar svaret att den saknas.

    Attrappen bar en post utan rackvidd. Den uppfyller inget krav - den vet
    inte om den gor det - och far darfor aldrig sta i en forslagslista.
    """
    port = Attrappsok(_bank())
    dom = _dom(port, rackvidd_krav=2050.0)
    f = _forslaget(dom)
    assert f is not None and f.alternativ
    assert all(a.tal is not None for a in f.alternativ)
    assert "Okand robot" not in f.text()


def test_F3_OMOJLIG_foreslar_aldrig_en_komponent():
    """Regel 4. Ar kraven motsagelsefulla i sig hjalper ingen maskin."""
    spec = _spec()
    spec.villkor.append(VS.Typvillkor(
        "smal", "geometri", "cell.bredd_mm", "le", 2000.0,
        _harkomst("hogst 2x2 meter"), "hogst 2 m bred"))
    spec.villkor.append(VS.Typvillkor(
        "bred", "geometri", "cell.bredd_mm", "ge", 3000.0,
        _harkomst("minst 3 meter bred"), "minst 3 m bred"))
    port = Attrappsok(_bank())
    dom = MO.granska(spec.villkor,
                     ST.Faktarum(spec, {"robot": {"rackvidd_mm": 1650.0}}),
                     spec, sokport=port)
    assert dom.dom == MO.OMOJLIG
    assert all(k.forslag is None for k in dom.krockar), \
        "en omojlig bestallning fick ett komponentforslag"
    assert port.fragor == [], "grinden sokte i katalogen for en OMOJLIG dom"


def test_F4_OKANT_foreslar_aldrig_en_komponent():
    """Regel 3: OKANT ar aldrig ett godkannande, och aldrig ett forslag."""
    spec = _spec()
    port = Attrappsok(_bank())
    dom = MO.granska(spec.villkor, ST.Faktarum(spec, {}), spec, sokport=port)
    assert dom.dom == MO.OKANT
    assert all(k.forslag is None for k in dom.krockar)
    assert port.fragor == []


# ======================================================================
# A. FORSLAGET SJALVT
# ======================================================================

def test_A1_valet_som_faller_far_namngivna_alternativ():
    port = Attrappsok(_bank())
    dom = _dom(port, rackvidd_krav=2050.0)
    assert dom.dom == MO.VALET_FALLER
    f = _forslaget(dom)
    assert f is not None and f.alternativ
    namn = [a.namn for a in f.alternativ]
    assert "IRB 4600-60/2.05" in namn


def test_A2_varje_forslag_bar_talet_som_avgjorde_och_dess_harkomst():
    """Regel 1, ordagrant: 'IRB 4600-60/2.05, rackvidd 2 050 mm, ur
    katalogposten' - aldrig ett namn utan skal."""
    port = Attrappsok(_bank())
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    for a in f.alternativ:
        assert a.tal is not None
        assert a.enhet == "mm"
        assert a.kalla, "forslaget %s bar ingen harkomst till sitt tal" % a.namn
        rad = a.rad()
        assert a.namn in rad
        assert "%g" % a.tal in rad
        assert "mm" in rad
        assert "ge 2050" in rad or "ge 2050 mm" in rad


def test_A3_hogst_en_handfull_forslag():
    """Regel 2. En lista pa 200 ar samma fel som att inte svara."""
    manga = [Traff("R%03d" % i, "ABB", rackvidd_mm=2100.0 + i)
             for i in range(30)]
    port = Attrappsok(manga)
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    assert 0 < len(f.alternativ) <= FO.MAX_FORSLAG
    assert FO.MAX_FORSLAG <= 5, "en 'handfull' ar inte tio"


def test_A4_ordningen_ar_minsta_som_racker_och_motivet_star_skrivet():
    port = Attrappsok(_bank())
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    tal = [a.tal for a in f.alternativ]
    assert tal == sorted(tal), "forslagen kom inte i vaxande ordning"
    assert tal[0] == 2050.0
    assert len(f.ordningsmotiv) >= 40, "sorteringen bar inget skrivet motiv"
    assert f.ordningsmotiv in f.text()


def test_A5_forslaget_syns_i_den_text_operatoren_far():
    port = Attrappsok(_bank())
    dom = _dom(port, rackvidd_krav=2050.0)
    text = dom.text()
    assert "IRB 4600-60/2.05" in text
    assert "MOTSAGELSE VALET_FALLER" in text


def test_A6_ett_foreslaget_alternativ_passerar_faktiskt_grinden():
    """Det starkaste provet: byt in forslaget och kor om.

    Ett forslag som inte sjalvt haller kravet ar samre an inget forslag - da
    har grinden skickat operatoren pa en andra vanda.
    """
    port = Attrappsok(_bank())
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    for a in f.alternativ:
        om = _dom(port, rackvidd_krav=2050.0, vald_rackvidd=a.tal)
        assert om.dom != MO.VALET_FALLER, \
            "forslaget %s holl inte kravet det foreslogs for" % a.namn


def test_A7_samma_bestallning_ger_samma_forslag_tre_ganger():
    rader = []
    for _ in range(3):
        port = Attrappsok(_bank())
        rader.append([a.rad() for a in _forslaget(_dom(port)).alternativ])
    assert rader[0] == rader[1] == rader[2]


# ======================================================================
# B. NAR SOKSKIKTET INTE RACKER TILL
# ======================================================================

def test_B1_utan_sokskikt_soks_ingenting_och_det_star_utskrivet():
    """En grind som inte kordes far aldrig se ut som en grind som gick."""
    dom = _dom(None, rackvidd_krav=2050.0)
    assert dom.dom == MO.VALET_FALLER
    assert _forslaget(dom) is None
    assert any(kod == "FORSLAG" for kod, _skal in dom.hoppade), dom.text()
    assert "EJ PROVAD FORSLAG" in dom.text()


def test_B2_en_bred_fraga_ger_ett_sammandrag_och_det_redovisas():
    """M-60:s regel motad: over BRED_FRAGA traffar lamnar sokskiktet inga
    rader alls. Forslaget smalnar da av per tillverkare, precis som sokskiktet
    sjalvt uppmanar - och redovisar vad som INTE gick att rakna upp."""
    poster = ([Traff("ABB-%03d" % i, "ABB", rackvidd_mm=2100.0 + i)
               for i in range(30)]
              + [Traff("KUKA-%03d" % i, "KUKA", rackvidd_mm=2200.0 + i)
                 for i in range(25)])
    port = Attrappsok(poster, bred=40)
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    assert f.totalt == 55
    assert f.alternativ, "sammandraget lamnade grinden helt stum"
    assert len(port.fragor) >= 3, "grinden smalnade aldrig av fragan"
    assert "55" in f.text()


def test_B3_det_som_inte_gick_att_rakna_upp_star_utskrivet():
    """Aterstar en tillverkare som sjalv ar for bred stryks den inte tyst."""
    poster = ([Traff("ABB-%03d" % i, "ABB", rackvidd_mm=2100.0 + i)
               for i in range(30)]
              + [Traff("KUKA-%03d" % i, "KUKA", rackvidd_mm=2200.0 + i)
                 for i in range(25)])
    port = Attrappsok(poster, bred=20)
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    assert f.ej_uppraknade == 55
    assert f.alternativ == []
    assert "55" in f.text()
    # Och det far inte lata som ett tomt bibliotek.
    assert "0 av" not in f.text()


def test_B4_en_storhet_sokskiktet_inte_bar_ger_ett_skal_inte_ett_forslag():
    """`del.<roll>.massa_kg` ar komponentens EGEN massa. Sokskiktet bar
    nyttolast (MaxPayload). Att soka pa den for ett massakrav vore att lata en
    parameter bara tva storheter."""
    spec = _spec()
    spec.villkor.append(VS.Typvillkor(
        "massa", "geometri", "del.robot.massa_kg", "le", 100.0,
        _harkomst("roboten far vaga hogst 100 kg"), "hogst 100 kg"))
    port = Attrappsok(_bank())
    dom = MO.granska(spec.villkor,
                     ST.Faktarum(spec, {"robot": {"rackvidd_mm": 1650.0,
                                                  "massa_kg": 272.0}}),
                     spec, sokport=port)
    assert dom.dom == MO.VALET_FALLER
    massakrock = [k for k in dom.krockar if k.storhet == "del.robot.massa_kg"]
    assert massakrock, dom.text()
    f = massakrock[0].forslag
    assert f is not None and f.alternativ == []
    assert "nyttolast" in f.text().lower()


def test_B5_en_ovre_grans_pa_samma_storhet_haller_i_forslaget():
    """Faller kravet nedat och en annan rad satter ett tak ska forslaget
    ligga mellan dem - annars foreslar grinden nagot som faller pa nasta rad."""
    spec = _spec(2050.0)
    spec.villkor.append(VS.Typvillkor(
        "tak", "geometri", "del.robot.rackvidd_mm", "le", 2500.0,
        _harkomst("roboten far inte na utanfor cellen"),
        "hogst 2500 mm rackvidd"))
    port = Attrappsok(_bank())
    dom = MO.granska(spec.villkor,
                     ST.Faktarum(spec, {"robot": {"rackvidd_mm": 1650.0}}),
                     spec, sokport=port)
    f = _forslaget(dom)
    assert f is not None and f.alternativ
    for a in f.alternativ:
        assert 2050.0 <= a.tal <= 2500.0, a.rad()
    assert "2500" in f.text()


def test_B6_ett_sokskikt_som_kastar_faller_inte_grinden():
    """Grinden ar en grind. Gar sokskiktet sonder ska domen sta kvar och
    felet skrivas ut - aldrig ett undantag ur en dom."""

    class Trasig(object):
        def sok(self, **kv):
            raise RuntimeError("indexet gick inte att lasa")

    dom = _dom(Trasig(), rackvidd_krav=2050.0)
    assert dom.dom == MO.VALET_FALLER
    f = _forslaget(dom)
    assert f is not None and f.alternativ == []
    assert "indexet gick inte att lasa" in f.text()


class Slarvigtsok(Attrappsok):
    """Ett sokskikt som struntar i det numeriska filtret.

    Den finns for att grinden inte ska LITA pa sokskiktets filter for ett
    pastaende den gor SJALV. Forslagsraden sager "rackvidd 2 050 mm"; da maste
    grinden ha last talet och provat det, inte antagit att nagon annan gjorde
    det. Det ar samma disciplin som att en dom aldrig far vila pa ett facit ur
    den kod som doms.
    """

    def sok(self, **kv):
        kv.pop("min_rackvidd_mm", None)
        return Attrappsok.sok(self, **kv)


def test_B8_grinden_provar_sjalv_talet_den_skriver_ut():
    port = Slarvigtsok(_bank())
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    assert f is not None and f.alternativ
    for a in f.alternativ:
        assert a.tal >= 2050.0, "grinden slappte igenom %s pa %g mm" % (
            a.namn, a.tal)
    # Posten utan tal ska raknas, inte tigas ihjal.
    assert f.ej_uppraknade == 0
    assert "saknade talet" in f.text()
    assert "Okand robot" not in f.text()


def test_B9_poster_utan_tillverkare_raknas_en_gang_och_inte_som_hela_mangden():
    """Ett tomt tillverkarfilter ar inget filter alls i sokskiktet. Smalnas
    fragan av pa en tom nyckel kommer hela mangden tillbaka, och da hade det
    som inte gick att rakna upp raknats en gang for mycket."""
    poster = ([Traff("A-%03d" % i, "ABB", rackvidd_mm=2100.0 + i)
               for i in range(30)]
              + [Traff("X-%03d" % i, "", rackvidd_mm=2200.0 + i)
                 for i in range(25)])
    port = Attrappsok(poster, bred=40)
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    assert f.totalt == 55
    assert f.ej_uppraknade == 25, f.text()
    assert f.uppraknade == 30


def test_B7_utfasade_komponenter_foreslas_inte():
    bank = _bank() + [Traff("Gammal 2100", "ABB", rackvidd_mm=2060.0,
                            utfasad=True)]
    port = Attrappsok(bank)
    f = _forslaget(_dom(port, rackvidd_krav=2050.0))
    assert "Gammal 2100" not in f.text()


# ======================================================================
# C. HELA VAGEN - grind 3 i bestallningskedjan
# ======================================================================

def test_C1_beskedet_ur_grind_3_bar_forslagen():
    """Kopplingen ar ingenting vard om den inte nar operatorens besked."""
    from vc_assist_svc.plan import bestallning as B

    spec = _spec(2050.0)
    besked = B.doma(spec, {"robot": {"rackvidd_mm": 1650.0}},
                    sokport=Attrappsok(_bank()))
    assert besked.status == B.AVVISAD
    assert besked.grind == "B3_MOTSAGELSE"
    text = "\n".join(t for _kod, t in besked.problem)
    assert "IRB 4600-60/2.05" in text
    assert "2050 mm" in text


def test_C2_samma_besked_utan_sokskikt_sager_att_det_inte_sokte():
    from vc_assist_svc.plan import bestallning as B

    spec = _spec(2050.0)
    besked = B.doma(spec, {"robot": {"rackvidd_mm": 1650.0}})
    assert besked.status == B.AVVISAD
    assert any("EJ PROVAD FORSLAG" in r for r in besked.rader()), \
        "\n".join(besked.rader())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
