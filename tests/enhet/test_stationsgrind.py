# -*- coding: utf-8 -*-
"""L1: stationsgrinden som binder grind 1-4 till guldgrindens cell.

Ingen kompilator, inget natverk, ingen VC. Grind 1 ar darfor OUPPSATT i de
flesta prov, och det ar inget provfel - det ar precis det lage grinden maste
rapportera arligt i stallet for att tiga.

De trasiga fallen kommer ur tests/protocol/fas7_stationen.md: T1 (tagg som inte
finns i kartan), T2 (skrivning till en skyddad signal) och T7 (tom kropp).
T3-T6 hor till ogat och kan inte provas har; det ar hela skalet till att ogat
finns.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon"))

from vc_assist_svc import guldgrind as G                        # noqa: E402
from vc_assist_svc.plc import stationsgrind as S                # noqa: E402
from vc_assist_svc.plc.signalkarta import karta_av_rader        # noqa: E402


STATION = "Press"


def karta():
    return karta_av_rader(STATION, [
        ("Givare", "Puls", "givare", "BOOL", "TILL_PLC", "%IX0.0"),
        ("Don", "Svar", "don", "BOOL", "FRAN_PLC", "%QX0.0"),
    ])


def kalla(kropp):
    k = karta()
    return ("PROGRAM %s\n" % k.station) + k.deklarationstext() + kropp + "END_PROGRAM\n"


HEL_KROPP = "    don := givare;\n"


class FalskGranskning(object):
    """Formen api_index.Granskning har, sa provet slipper ett riktigt index."""

    def __init__(self, fel=(), obestambara=(), kontrollerade_namn=3):
        self.fel = list(fel)
        self.obestambara = list(obestambara)
        self.kontrollerade_namn = kontrollerade_namn

    @property
    def godkand(self):
        return not self.fel and not self.obestambara

    def rapport(self):
        return "FEL (%d)" % len(self.fel) if self.fel else "inga fel"


class FalsktIndex(object):
    def __init__(self, granskning=None):
        self.granskning = granskning or FalskGranskning()
        self.granskad = []

    def granska(self, kod):
        self.granskad.append(kod)
        return self.granskning


SCENKOD = "app.findComponent('Press')\n"


# ---- namnen maste vara guldgrindens ---------------------------------------

def test_grindnamnen_ar_exakt_guldgrindens():
    """Tva listor som ska vara samma lista gar isar tyst. Har gor de inte det."""
    assert sorted(S.KORORDNING) == sorted(G.FORGRINDAR)


# ---- den hela kandidaten --------------------------------------------------

def test_en_hel_kandidat_passerar_grind_2_3_och_4():
    dom = S.granska_station(
        S.Kandidat(STATION, kalla(HEL_KROPP), SCENKOD),
        karta(), index=FalsktIndex())
    assert dom.forgrindar[S.NAMN_STATISK] is True
    assert dom.forgrindar[S.NAMN_DEKLARATION] is True
    assert dom.forgrindar[S.NAMN_ANROP] is True


def test_utan_kompilator_ar_domen_anda_inte_ok():
    """Grind 1 oupsatt ar rott, inte gront i vantan pa besked (I3)."""
    dom = S.granska_station(
        S.Kandidat(STATION, kalla(HEL_KROPP), SCENKOD),
        karta(), index=FalsktIndex())
    assert dom.ok is False
    assert dom.forsta_fallande == S.NAMN_KOMPILERING
    assert "kompilatorn" in dom.forgrindar[S.NAMN_KOMPILERING]


# ---- T1: tagg som inte finns i kartan --------------------------------------

def test_T1_tagg_utanfor_kartan_falls_av_grind_3():
    k = karta()
    trasig = (("PROGRAM %s\n" % k.station) + k.deklarationstext()
              + "    don := givare AND uppfunnen;\n" + "END_PROGRAM\n")
    dom = S.granska_station(S.Kandidat(STATION, trasig, SCENKOD), k,
                            index=FalsktIndex())
    assert dom.ok is False
    assert dom.forsta_fallande in (S.NAMN_STATISK, S.NAMN_DEKLARATION)
    # Grindens EGNA ord ska finnas kvar, inte en omskrivning (I1).
    egen = dom.utdata[dom.forsta_fallande]
    assert "uppfunnen" in egen.lower()


# ---- T2: skrivning till en skyddad signal ----------------------------------

def test_T2_skrivning_till_skyddad_signal_falls():
    k = karta_av_rader(STATION, [
        ("Givare", "Puls", "givare", "BOOL", "TILL_PLC", "%IX0.0"),
        ("Ljusrida", "Fri", "ridafri", "BOOL", "TILL_PLC", "%IX0.1", True),
        ("Don", "Svar", "don", "BOOL", "FRAN_PLC", "%QX0.0"),
    ])
    trasig = (("PROGRAM %s\n" % k.station) + k.deklarationstext()
              + "    ridafri := TRUE;\n    don := givare;\n" + "END_PROGRAM\n")
    dom = S.granska_station(S.Kandidat(STATION, trasig, SCENKOD), k,
                            index=FalsktIndex())
    assert dom.ok is False
    assert dom.forsta_fallande in (S.NAMN_STATISK, S.NAMN_DEKLARATION)


# ---- T7: tom kropp ---------------------------------------------------------

def test_T7_tom_kropp_falls_och_ar_facitets_nollpunkt():
    """Passerar en tom kropp har facit ingen undre grans."""
    dom = S.granska_station(S.Kandidat(STATION, kalla("    ;\n"), SCENKOD),
                            karta(), index=FalsktIndex())
    assert dom.ok is False


# ---- grind 4:s tystnadslagen -----------------------------------------------

def test_ingen_scenkod_ar_inte_ett_godkannande():
    dom = S.granska_station(S.Kandidat(STATION, kalla(HEL_KROPP), None),
                            karta(), index=FalsktIndex())
    assert dom.forgrindar[S.NAMN_ANROP] is not True
    assert "scenkod" in dom.forgrindar[S.NAMN_ANROP]


def test_saknat_apiindex_ar_inte_ett_godkannande():
    dom = S.granska_station(S.Kandidat(STATION, kalla(HEL_KROPP), SCENKOD),
                            karta(), index=None)
    assert dom.forgrindar[S.NAMN_ANROP] is not True


def test_en_granskning_som_provade_noll_namn_ar_inte_gron():
    """En grind som blir billig slutar mata sin egen storhet."""
    index = FalsktIndex(FalskGranskning(kontrollerade_namn=0))
    dom = S.granska_station(S.Kandidat(STATION, kalla(HEL_KROPP), SCENKOD),
                            karta(), index=index)
    assert dom.forgrindar[S.NAMN_ANROP] is not True
    assert "noll namn" in dom.forgrindar[S.NAMN_ANROP]


def test_grind_4_falls_av_ett_uppfunnet_namn():
    index = FalsktIndex(FalskGranskning(fel=["okant namn app.hittepa"]))
    dom = S.granska_station(S.Kandidat(STATION, kalla(HEL_KROPP), SCENKOD),
                            karta(), index=index)
    assert dom.forgrindar[S.NAMN_ANROP] is not True
    assert dom.forsta_fallande == S.NAMN_ANROP


# ---- cellen guldgrinden laser ----------------------------------------------

def test_cellen_utan_ogonrapport_blir_inte_guld():
    """Grind 5 ar den som avgor. Fyra grona forgrindar racker inte."""
    dom = S.granska_station(S.Kandidat(STATION, kalla(HEL_KROPP), SCENKOD),
                            karta(), index=FalsktIndex())
    dom.forgrindar[S.NAMN_KOMPILERING] = True       # lat som om grind 1 kort
    cell = dom.till_cell("press-01", "press")
    ok, skal = G.Guldgrind({"press"}).doma_cell(cell)
    assert ok is False
    assert "ogonrapport" in skal


def test_en_fallande_forgrind_nar_hela_vagen_till_guldgrinden():
    dom = S.granska_station(S.Kandidat(STATION, kalla(HEL_KROPP), None),
                            karta(), index=FalsktIndex())
    cell = dom.till_cell("press-01", "press", eyes="strunt")
    ok, skal = G.Guldgrind({"press"}).doma_cell(cell)
    assert ok is False
    # Skalet ska namna den grind som faktiskt fallde, inte den forsta som
    # rakade sakna svar.
    assert S.NAMN_ANROP in skal


# ---- kandidaten maste galla kartans station --------------------------------

def test_fel_station_ar_ett_fel_inte_ett_underkannande():
    with pytest.raises(S.Stationsfel):
        S.granska_station(S.Kandidat("Annan", kalla(HEL_KROPP), SCENKOD),
                          karta(), index=FalsktIndex())


# ---- vagen fran ett ratt modellsvar ----------------------------------------

def test_ett_modellsvar_med_bara_kroppen_blir_en_kandidat():
    from vc_assist_svc.plc.skelett import Skelett
    k = karta()
    kand = S.Kandidat.fran_modellsvar(Skelett.av_karta(k), HEL_KROPP, SCENKOD)
    dom = S.granska_station(kand, k, index=FalsktIndex())
    assert dom.forgrindar[S.NAMN_DEKLARATION] is True


def test_ett_modellsvar_med_andrad_ram_blir_aldrig_en_kandidat():
    """Den ar inte en kropp med ett fel, den ar ett annat program."""
    from vc_assist_svc.plc.skelett import Skelett, Skelettfel
    k = karta()
    sk = Skelett.av_karta(k)
    manipulerat = sk.satt_in(HEL_KROPP).replace("%IX0.0", "%IX0.7")
    with pytest.raises(Skelettfel):
        S.Kandidat.fran_modellsvar(sk, manipulerat, SCENKOD)


def test_grind_3_domer_for_sig_sjalv_och_inte_for_grind_2():
    """En grind som faller utan att saga varfor ar ett trasigt besked.

    Grind3Rapport.ok ar KOMBINERAD - falsk ocksa nar bara grind 2 fallde. Laste
    stationsgrinden den som grind 3:s dom blev beskedet
    "deklarationsmatchning: 0 anmarkningar", och en modell som far det letar
    efter ett deklarationsfel som inte finns.

    Fixturen: en kropp med en dubbelskrivning. Grind 2 faller pa den; grind 3
    har ingenting att anmarka och ska saga GODKAND.
    """
    k = karta()
    kropp = "    don := givare;\n    don := givare;\n"
    dom = S.granska_station(S.Kandidat(STATION, kalla(kropp), SCENKOD), k,
                            index=FalsktIndex(), stanna_vid_forsta=False)
    assert dom.forgrindar[S.NAMN_STATISK] is not True, "grind 2 ska falla"
    assert dom.forgrindar[S.NAMN_DEKLARATION] is True, (
        "grind 3 har noll egna anmarkningar och ska saga GODKAND, inte "
        "underkanna for grind 2:s rakning: %r"
        % dom.forgrindar[S.NAMN_DEKLARATION])
