# -*- coding: utf-8 -*-
"""M-53: de trasiga fixturerna for reglerna som var BEDDA innan.

M-46 raknade harnessens hardhet och fick 17 mekaniserade regler mot 29 bedda.
En bedd regel ar en rad prosa i systemprompten; en mekaniserad regel avvisas
av kod. Varje prov i den har filen ar den trasiga fixturen for EN sadan
flyttning, och varje prov foll fore sin mekanism.

Provfilen ar egen och inte ett tillagg till test_harnesshardhet.py, av samma
skal som M-46 skrev sin egen: en matning ska ga att kora for sig, och tva
matningar som blandas i en fil gar inte langre att skilja at.

Varje avsnitt har BADA riktningarna. En grind som bara provas i den fallande
riktningen mater sin egen benagenhet att neka.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

from vc_assist_svc import verktyg as V                    # noqa: E402
from vc_assist_svc.harness import fallor as Fa            # noqa: E402
from vc_assist_svc.harness import forgranskning as Fg     # noqa: E402
from vc_assist_svc.harness import instruktioner as I      # noqa: E402
from vc_assist_svc.harness import kanal as Kn             # noqa: E402
from vc_assist_svc.harness import loop as L               # noqa: E402
from vc_assist_svc.harness import modell as Mo            # noqa: E402
from vc_assist_svc.harness import turordning as T         # noqa: E402


@pytest.fixture(scope="module")
def forgranskare():
    return Fg.Forgranskare()


@pytest.fixture(scope="module")
def korpus():
    return I.las_korpus()


def _kor(korpus, forgranskare, svar, manus, uppgift="Gor det."):
    """Kor en hel tur genom den RIKTIGA harnessen mot en attrappvarld."""
    harness = L.Harness(modell=Mo.AttrappModell(list(svar)),
                        kanal=Kn.Attrappkanal(manus),
                        korpus=korpus, forgranskare=forgranskare)
    return harness.kor(uppgift)


def _kod(namn, argument):
    """Den kod verktyget verkligen genererar for de har argumenten."""
    verktyg = V.REGISTER[namn]
    return V.CODE_GEN_HANDLERS[namn](V.validera_argument(verktyg, argument))


SATT = {"component": "IRB1200", "position": [2500.0, 0.0, 0.0]}
LAS = {"component": "IRB1200"}
SATT_SVAR = {"set": True, "component": "IRB1200",
             "position": [2500.0, 0.0, 0.0]}


# ---- 1. koden lases, inte verktygsnamnet --------------------------------

def test_set_transform_flyttar_och_get_transform_laser_varldsmatrisen():
    """Grunden under slapande_matris: bada svaren kommer ur mallarnas kod.

    En grind som i stallet bar en lista over verktygsnamn hade slutat galla
    dagen nagon lade till ett verktyg till som flyttar nagot.
    """
    assert T.flyttar(_kod("set_transform", SATT))
    assert not T.uppdaterar(_kod("set_transform", SATT))
    assert T.laser_varldsmatrisen(_kod("get_transform", LAS))
    assert not T.uppdaterar(_kod("get_transform", LAS))


def test_matmallen_uppdaterar_innan_den_mater():
    """M-36: matmallarna kor _farsk(), alltsa n.update() + sim.update()."""
    kod = _kod("measure_distance", {"component": "IRB1200",
                                    "other_component": "Transportor"})
    assert T.uppdaterar(kod)
    assert not T.andrar_scenen(kod), (
        "en matning andrar ingenting; raknades den som en andring skulle "
        "kravet pa aterlasning bli omojligt att uppfylla")


def test_lasande_mallar_andrar_ingenting_och_skrivande_gor_det():
    assert not T.andrar_scenen(_kod("list_components", {}))
    assert not T.andrar_scenen(_kod("get_transform", LAS))
    assert T.andrar_scenen(_kod("set_transform", SATT))
    assert T.andrar_scenen(_kod("connect", {"component": "IRB1200",
                                            "interface": "BaseInterface",
                                            "other_component": "Transportor",
                                            "other_interface": "OutFeed"}))


def test_komponentargumenten_betyder_en_befintlig_komponent():
    """olast_scen vilar pa att component och other_component alltid pekar pa
    nagot som redan MASTE finnas. Ett nytt verktyg som later namnen betyda en
    komponent som ska SKAPAS ska falla har i stallet for att tyst oppna ett
    hal i grinden."""
    for verktyg, arg in T.komponentargument(V.REGISTER):
        schema = V.REGISTER[verktyg].parameters["properties"][arg]
        text = schema.get("description", "").lower()
        assert schema.get("type") == "string", (verktyg, arg)
        assert "komponent" in text, (verktyg, arg, text)
        for nyskapande in ("nya ", "nytt ", "ny komponent", "som ska skapas"):
            assert nyskapande not in text, (verktyg, arg, nyskapande)


# ---- 2. ARB-006 och FAL-004: anropet efter sparningen -------------------

def test_anrop_efter_sparning_avvisas(korpus, forgranskare):
    """Foll fore M-53: bada anropen kordes och turen slapptes igenom.

    MATT M-13: app.save() stoppar simuleringen och bryggan svarar inte
    efterat, sa det andra anropet forsvinner utan att nagon far veta det.
    """
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("save_layout", {"uri": "file:///tmp/a.vcmx"}),
                      Mo.anropa("get_transform", LAS),
                      Mo.sag("Sparad och kontrollerad.")],
                     {"save_layout": [{"saved": True,
                                       "uri": "file:///tmp/a.vcmx"}],
                      "get_transform": [Fa.TRANSFORMSVAR]})
    assert protokoll.utfall == "AVVISAD:efter_sparning"
    assert "M-13" in protokoll.avvisningar[0].text
    assert "ARB-006" in protokoll.avvisningar[0].text


def test_sparningen_sist_i_turen_slapps_igenom(korpus, forgranskare):
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("list_components"),
                      Mo.anropa("save_layout", {"uri": "file:///tmp/a.vcmx"}),
                      Mo.sag("Jag laste layouten och sparade den sist.")],
                     {"list_components": [Fa.LISTSVAR],
                      "save_layout": [{"saved": True,
                                       "uri": "file:///tmp/a.vcmx"}]})
    assert protokoll.utfall == "SLAPPT"


# ---- 3. FAL-002 och ARB-004: varldsmatrisen efter en flytt --------------

def test_varldsmatrisen_last_direkt_efter_en_flytt_avvisas(korpus,
                                                           forgranskare):
    """Foll fore M-53, och fallan F-38 stod markt EJ_MEKANISK med skalet att
    grinden inte kan veta om sim.update() kordes emellan. Den vet: den ser
    turens ordning och den genererade koden."""
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("list_components"),
                      Mo.anropa("set_transform", SATT),
                      Mo.anropa("get_transform", LAS),
                      Mo.sag("Roboten star nu 812 mm fran origo.")],
                     {"list_components": [Fa.LISTSVAR],
                      "set_transform": [SATT_SVAR],
                      "get_transform": [Fa.TRANSFORMSVAR]})
    assert protokoll.utfall == "AVVISAD:slapande_matris"
    assert "M-11" in protokoll.avvisningar[0].text


def test_ett_matt_avstand_efter_en_flytt_slapps_igenom(korpus, forgranskare):
    """Kontrollriktningen. Matmallen uppdaterar sjalv (M-36), sa den ger ett
    farskt varde och far inte fallas - annars finns ingen tillaten vag till
    ett matt efter en andring."""
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("list_components"),
                      Mo.anropa("set_transform", SATT),
                      Mo.anropa("measure_distance",
                                {"component": "IRB1200",
                                 "other_component": "Transportor"}),
                      Mo.sag("Avstandet ar 812 mm, matt med "
                             "measure_distance efter flytten.")],
                     {"list_components": [Fa.LISTSVAR],
                      "set_transform": [SATT_SVAR],
                      "measure_distance": [{"found": True, "distance": 812.0,
                                            "a": "IRB1200",
                                            "b": "Transportor",
                                            "touching": False,
                                            "tolerance": 0.0}]})
    assert protokoll.utfall == "SLAPPT"


def test_ett_simuleringssteg_mellan_flytt_och_lasning_slapper_igenom():
    """sim_step raknar om scenen, sa varldsmatrisen ar aktuell igen."""
    lage = T.Turlage()
    lage.lagg("list_components", _kod("list_components", {}), True,
              Fa.LISTSVAR)
    lage.lagg("set_transform", _kod("set_transform", SATT), True, SATT_SVAR)
    assert lage.slapande
    lage.lagg("sim_step", _kod("sim_step", {"render": False}), True,
              {"sim_time": 0.1})
    assert not lage.slapande
    dom = lage.domer(V.REGISTER["get_transform"], LAS,
                     _kod("get_transform", LAS))
    assert not dom.nekas


# ---- 4. ARB-003 och FAL-005: kedjade skrivningar ------------------------

def test_tva_skrivningar_utan_aterlasning_avvisas(korpus, forgranskare):
    """MATT M-09: VC svaljer fel tyst. Ett anrop som inte kastade ar inget
    bevis pa att atgarden tog."""
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("list_components"),
                      Mo.anropa("set_transform", SATT),
                      Mo.anropa("connect", {"component": "IRB1200",
                                            "interface": "BaseInterface",
                                            "other_component": "Transportor",
                                            "other_interface": "OutFeed"}),
                      Mo.sag("Bada andringarna ar gjorda.")],
                     {"list_components": [Fa.LISTSVAR],
                      "set_transform": [SATT_SVAR],
                      "connect": [Fa.KOPPLINGSSVAR]})
    assert protokoll.utfall == "AVVISAD:olast_skrivning"
    assert "M-09" in protokoll.avvisningar[0].text


def test_en_aterlasning_mellan_skrivningarna_slapper_igenom(korpus,
                                                            forgranskare):
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("list_components"),
                      Mo.anropa("set_transform", SATT),
                      Mo.anropa("list_components"),
                      Mo.anropa("connect", {"component": "IRB1200",
                                            "interface": "BaseInterface",
                                            "other_component": "Transportor",
                                            "other_interface": "OutFeed"}),
                      Mo.sag("Jag flyttade roboten, laste tillbaka och "
                             "kopplade den sedan.")],
                     {"list_components": [Fa.LISTSVAR, Fa.LISTSVAR],
                      "set_transform": [SATT_SVAR],
                      "connect": [Fa.KOPPLINGSSVAR]})
    assert protokoll.utfall == "SLAPPT"


def test_en_skrivning_som_foll_kraver_ingen_aterlasning():
    """Ett anrop som foll andrade ingenting, och far darfor inte kravas
    tillbakalast. En grind som krav det hade last modellen ute ur sin egen
    rattning."""
    lage = T.Turlage()
    lage.lagg("list_components", _kod("list_components", {}), True,
              Fa.LISTSVAR)
    lage.lagg("set_transform", _kod("set_transform", SATT), False, None)
    assert not lage.olasta
    dom = lage.domer(V.REGISTER["set_transform"], SATT,
                     _kod("set_transform", SATT))
    assert not dom.nekas


# ---- 5. ARB-001: las scenen innan du andrar den -------------------------

def test_en_koppling_utan_en_enda_lasning_avvisas(korpus, forgranskare):
    """Namnen later rimliga och star i uppgiften, men ingen lasning i turen
    har visat att de finns. Modellen far bara valja ur det som finns (I9)."""
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("connect", {"component": "IRB1200",
                                            "interface": "BaseInterface",
                                            "other_component": "Transportor",
                                            "other_interface": "OutFeed"}),
                      Mo.sag("Kopplingen ar gjord.")],
                     {"connect": [Fa.KOPPLINGSSVAR]},
                     uppgift="Koppla IRB1200 till Transportor.")
    assert protokoll.utfall == "AVVISAD:olast_scen"
    assert "ARB-001" in protokoll.avvisningar[0].text


def test_en_lasning_forst_racker(korpus, forgranskare):
    protokoll = _kor(korpus, forgranskare,
                     [Mo.anropa("list_components"),
                      Mo.anropa("connect", {"component": "IRB1200",
                                            "interface": "BaseInterface",
                                            "other_component": "Transportor",
                                            "other_interface": "OutFeed"}),
                      Mo.sag("Jag laste layouten och kopplade dem sedan.")],
                     {"list_components": [Fa.LISTSVAR],
                      "connect": [Fa.KOPPLINGSSVAR]})
    assert protokoll.utfall == "SLAPPT"


def test_ett_dataverktygs_svar_ar_ingen_lasning_av_scenen():
    """Ett data-verktyg nar aldrig scenen. En trafflista ur katalogen sager
    att en komponent finns pa disk, inte att den star i den har layouten."""
    lage = T.Turlage()
    lage.lagg("search_catalog", "", True,
              {"traffar": [{"namn": "IRB1200", "uri": "bank://robot/x"}]})
    assert "irb1200" not in lage.lasta_namn
