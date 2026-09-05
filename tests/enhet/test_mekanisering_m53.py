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
import re
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
from vc_assist_svc.harness import kodfallor as Kf         # noqa: E402
from vc_assist_svc.harness import loop as L               # noqa: E402
from vc_assist_svc.harness import modell as Mo            # noqa: E402
from vc_assist_svc.harness import mattafakta as Mf        # noqa: E402
from vc_assist_svc.harness import redovisning as Rd       # noqa: E402
from vc_assist_svc.harness import text as Tx              # noqa: E402
from vc_assist_svc.harness import turordning as T         # noqa: E402
from vc_assist_svc.harness import verifiering as Vf       # noqa: E402
from vc_assist_svc.harness import arlighet as A           # noqa: E402


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


# ---- 6. FAL-001: kvaternionen ar skalar-forst ---------------------------

def _svarsblock(kod, sprak="python"):
    return "Sa har:\n```%s\n%s```" % (sprak, kod)


@pytest.mark.parametrize("kod", [
    "q = m.getQuaternion()\nx, y, z, w = q.X, q.Y, q.Z, q.W\n",
    "q = m.getQuaternion()\nx = q.X\n",
    "q = m.getQuaternion()\nw = q.W\n",
    "q = m.getQuaternion()\nvridning = [q.X, q.Y, q.Z, q.W]\n",
    "vridning = (m.getQuaternion().X, m.getQuaternion().Y,\n"
    "            m.getQuaternion().Z, m.getQuaternion().W)\n",
])
def test_kvaternionen_last_i_namnordning_fangas(kod):
    """MATT M-11: q.X ar skalaren. Alla fem formerna ar samma miss."""
    skal = Kf.kvaternion_i_namnordning(kod)
    assert skal, kod
    assert "M-11" in skal[-1]


@pytest.mark.parametrize("kod", [
    "q = m.getQuaternion()\nskalar = q.X\nvektor = [q.Y, q.Z, q.W]\n",
    "q = m.getQuaternion()\nw = q.X\nx, y, z = q.Y, q.Z, q.W\n",
    "p = m.P\nx, y, z = p.X, p.Y, p.Z\n",
    "k = getApplication().findComponent('IRB1200')\nprint(k.Name)\n",
])
def test_ratt_avlasning_och_vanlig_kod_anklagas_inte(kod):
    """En vcVector som INTE ar en kvaternion far lasas i namnordning: det ar
    bara getQuaternion() som ar skalar-forst."""
    assert not Kf.kvaternion_i_namnordning(kod), kod


def test_kvaternionblocket_avvisas_av_hela_forgranskningen(forgranskare):
    dom = forgranskare.granska_svarstext(
        _svarsblock(Fa.KOD_KVATERNION_NAMNORDNING))
    assert not dom.slapps
    assert dom.avvisning.grind == "kvaternion"


def test_ratt_kvaternionblock_slapps_igenom(forgranskare):
    dom = forgranskare.granska_svarstext(_svarsblock(Fa.KOD_KVATERNION_RATT))
    assert dom.slapps


# ---- 7. FAL-006: all text in i VC ar bytestrangar -----------------------

def test_unicode_literals_fangas():
    skal = Kf.unicodetext("from __future__ import unicode_literals\nx = 1\n")
    assert skal
    assert "M-05" in skal[-1]


def test_u_prefixad_strang_fangas():
    assert Kf.unicodetext('k.Name = u"Robot"\n')


def test_verktygsmallarnas_egen_u_strang_anklagas_inte():
    """Var EGEN genererade kod skriver _s(u"..."), och det ar ratt gjort:
    _s lagger strangen i bytes innan den nar VC. En grind som anklagade den
    hade anklagat kodmallen."""
    assert not Kf.unicodetext('k = _komp(_s(u"IRB1200"))\n')


def test_hela_verktygsregistrets_mallar_passerar_bytestranggrinden():
    """Mattes om vid varje korning i stallet for att lita pa ett tal: alla
    kodgenererande mallar skriver _s(u"...") och ingen av dem far falla."""
    kollade = fallda = 0
    for namn, verktyg in sorted(V.REGISTER.items()):
        if verktyg.mode != "codegen":
            continue
        try:
            kod = _kod(namn, _standardargument(verktyg))
        except Exception:
            continue
        kollade += 1
        if Kf.unicodetext(kod):
            fallda += 1
    assert kollade >= 20
    assert fallda == 0


def _standardargument(verktyg):
    """Minsta giltiga argumentuppsattning ur schemat."""
    ut = {}
    for arg in verktyg.parameters.get("required", []):
        schema = verktyg.parameters["properties"][arg]
        typ = schema.get("type")
        if "enum" in schema:
            ut[arg] = schema["enum"][0]
        elif typ == "string":
            ut[arg] = "IRB1200"
        elif typ == "number":
            ut[arg] = 1.0
        elif typ == "integer":
            ut[arg] = 1
        elif typ == "boolean":
            ut[arg] = True
        elif typ == "array":
            ut[arg] = [0.0, 0.0, 0.0]
        else:
            ut[arg] = "IRB1200"
    return ut


# ---- 8. FAL-008: Python 2.7 inne i VC -----------------------------------

@pytest.mark.parametrize("kod", [
    'print(f"{k.Name}")\n',
    "if (n := 1) > 0:\n    pass\n",
    "x: int = 1\n",
    "def f(a, *, b):\n    return a\n",
    "def f(a: int) -> int:\n    return a\n",
    "def g():\n    yield from [1]\n",
])
def test_py3syntax_i_ett_vcblock_fangas(kod):
    skal = Kf.inte_python27(kod)
    assert skal, kod
    assert "Python 2.7" in skal[-1]


@pytest.mark.parametrize("kod", [
    'k = getApplication().findComponent("IRB1200")\nprint(k.Name)\n',
    "try:\n    x = 1\nexcept ValueError as e:\n    x = 0\n",
    'print("%s" % 1)\n',
])
def test_kod_som_gar_i_bade_2_och_3_anklagas_inte(kod):
    """except ... as e star med MED FLIT. FAL-008:s text sade fram till M-53
    att formen inte far finnas i tvasprakig kod; den ar giltig sedan Python
    2.6, och det ar den gamla formen except X, e som bara gar i tvaan."""
    assert not Kf.inte_python27(kod), kod


def test_kodfallsgrindarna_domer_i_dokumenterad_ordning():
    """Ett block som bar BADA felen klassas som kvaternion: det ger ett tal
    som ser rimligt ut, medan f-strangen bara vagrar kora."""
    kod = ('q = m.getQuaternion()\nx = q.X\nprint(f"{x}")\n')
    grind, skal = Kf.granska(kod)
    assert grind == "kvaternion"
    assert Kf.GRINDAR.index("kvaternion") < Kf.GRINDAR.index("py27")


# ---- 9. DOM-005 och DOM-006: vagar som ar matta till att inte finnas ----

@pytest.mark.parametrize("mening", [
    "Vi kan importera USD-filen direkt i VC.",
    "Nasta steg ar att exportera scenen till USD.",
    "Ladda in FBX-modellen i layouten.",
    "Satt upp VC som OPC UA-server mot PLC:n.",
    "VC kan agera OPC UA-server mot styrsystemet.",
])
def test_en_vag_som_inte_finns_avvisas(mening):
    assert Mf.granska(mening), mening


@pytest.mark.parametrize("mening", [
    "VC har ingen USD-lasare, sa den vagen finns inte.",
    "Jag exporterar layouten till FBX.",
    "PLC:n ar OPC UA-server och VC ansluter som klient.",
    "Konfigurera PLC:n som OPC UA-server.",
    "Vi laddar in husdjuret i scenen.",
    "Jag laddar komponenten ur katalogen.",
])
def test_riktiga_vagar_och_riktiga_besked_slapps_igenom(mening):
    """Den som HAR ratt far aldrig anklagas. 'husdjur' star med av ett matt
    skal: ordet bar 'usd', och med delstrangsmatchning blev ett husdjur en
    filformatsfraga."""
    assert not Mf.granska(mening), mening


def test_faktagrinden_gar_hela_vagen_genom_forgranskningen(forgranskare):
    dom = forgranskare.granska_svarstext(
        "Enklast ar att importera USD-filen direkt i VC.")
    assert not dom.slapps
    assert dom.avvisning.grind == Mf.GRIND
    assert "DOM-006" in " ".join(dom.avvisning.skal)


# ---- 10. DOM-003: enheten hor till talet -------------------------------

def test_ett_tal_i_fel_storleksordning_pekas_ut_som_enhetsmiss():
    """Foll fore M-53 med ett skal som inte hjalpte: 'inget verktygssvar bar
    det talet'. Talet var inte pahittat - enheten var tappad."""
    grund = Vf.Grund()
    grund.lagg_resultat("measure_distance", {}, {"distance": 812.0})
    tal = Tx.tal_i("Avstandet ar 0,812.")[0]
    skal = grund.stodjer_tal(tal)
    assert skal
    assert "DOM-003" in skal
    assert "MILLIMETER" in skal


def test_ett_pahittat_tal_far_fortfarande_det_vanliga_skalet():
    grund = Vf.Grund()
    grund.lagg_resultat("measure_distance", {}, {"distance": 812.0})
    tal = Tx.tal_i("Avstandet ar 137 mm.")[0]
    skal = grund.stodjer_tal(tal)
    assert skal
    assert "DOM-003" not in skal
    assert "narmaste varde" in skal


def test_ett_matt_i_meter_MED_enhet_stods_fortfarande():
    grund = Vf.Grund()
    grund.lagg_resultat("measure_distance", {}, {"distance": 2500.0})
    tal = Tx.tal_i("Avstandet ar 2,5 m.")[0]
    assert grund.stodjer_tal(tal) is None


# ---- 11. VRK-009 och SYS-003: redovisningen ----------------------------

class _Utfall(object):
    """Minsta utfallspost grinden behover. L1: inget kors."""

    def __init__(self, verktyg, resultat, ok=True, andrade=False):
        self.verktyg = verktyg
        self.resultat = resultat
        self.ok = ok
        self.andrade = andrade
        self.fel = ""


def test_en_klippt_lista_redovisad_som_helhet_fangas():
    utfall = [_Utfall("list_components", {"antal": 500, "avkortad": True})]
    anm = Rd.granska("Layouten innehaller 500 komponenter.", utfall)
    assert [a.kod for a in anm] == ["avkortat_som_helhet"]
    assert "VRK-009" in anm[0].skal


def test_en_klippt_lista_som_redovisas_som_klippt_slapps_igenom():
    utfall = [_Utfall("list_components", {"antal": 500, "avkortad": True})]
    assert not Rd.granska(
        "Listan ar avkortad vid 500 poster, sa layouten har minst 500 "
        "komponenter.", utfall)


def test_en_hel_lista_anklagas_aldrig():
    utfall = [_Utfall("list_components", {"antal": 2, "avkortad": False})]
    assert not Rd.granska("Layouten innehaller 2 komponenter.", utfall)


def test_simuleringen_som_bevis_fangas():
    anm = Rd.granska("Simuleringen gick igenom och cellen ar darmed bevisat "
                     "saker att driftsatta.", [])
    assert [a.kod for a in anm] == ["bevis_ur_simulering"]
    assert "SYS-003" in anm[0].skal


def test_ett_bevisord_utan_simuleringsord_anklagas_inte():
    """Det ar SIMULERINGENS rackvidd regeln handlar om. En matning far kallas
    ett bevis for det den matte."""
    assert not Rd.granska("Matningen bevisar att avstandet ar 812 mm.", [])


def test_bevispastaende_med_ett_orelaterat_nekande_ord_slipper_inte_igenom():
    """PROVETS ANTAGANDE VAR FEL, inte koden. Vand av M-95.

    Provet hette fore detta ..._slipper_igenom och beskrev luckan som "kand,
    at det ofarliga hallet". Antagandet var att nekandet ar det som skiljer
    den arliga meningen fran den falska, och att grinden darfor maste slappa
    VARJE mening som bar ett nekande ord.

    M-94 fynd 4 matte vad antagandet kostade: ett bevispastaende om en
    simulering formuleras nastan alltid negativt ("bevisar att inga
    kollisioner finns"), sa regeln filtrerade bort sin egen malklass och
    fallde bara den abstrakta form ingen modell skriver. Hallet var alltsa
    inte det ofarliga.

    Det som verkligen skiljer meningarna at ar VAD nekandet negerar. Grinden
    delar nu meningen vid det "att" som oppnar det bevisade: ett nekande i
    sjalva bevispastaendet gar fritt, ett nekande i innehallet gor det inte.
    Meningen nedan negerar ingenting i pastaendet - kollisionerna hor till
    korningen, och slutsatsen "alltsa ar cellen bevisat saker" star obestridd.
    """
    anm = Rd.granska("Simuleringen gick igenom utan kollisioner, alltsa "
                     "ar cellen bevisat saker.", [])
    assert [a.kod for a in anm] == ["bevis_ur_simulering"]
    # Den arliga meningen, som var provets egentliga arende, gar fortfarande fri.
    assert not Rd.granska("Simuleringen bevisar ingenting om verklig "
                          "hardvara.", [])


# ---- 12. ARL-008: forfluten tid bara om det kordes ---------------------

def test_pastadd_andring_efter_bara_lasningar_fangas():
    """M-46:s 'kvar, och inte lagat'. Foll fore M-53: turen slapptes."""
    utfall = [_Utfall("list_components", Fa.LISTSVAR),
              _Utfall("list_interfaces", Fa.INTERFACESVAR)]
    anm = A.granska("Jag kopplade ihop IRB1200 och Transportor.", utfall)
    assert [a.kod for a in anm] == ["arlighet_pastadd_andring"]
    assert "ARL-008" in anm[0].skal


def test_samma_pastaende_med_en_verklig_andring_slapps_igenom():
    utfall = [_Utfall("list_components", Fa.LISTSVAR),
              _Utfall("connect", Fa.KOPPLINGSSVAR, andrade=True)]
    assert not A.granska("Jag kopplade ihop IRB1200 och Transportor.", utfall)


def test_ett_tillstand_som_lasts_ur_scenen_anklagas_inte():
    """'ar kopplad' ar ingen pastadd handling. En grind som anklagade den
    hade gjort det omojligt att RAPPORTERA en koppling man last."""
    utfall = [_Utfall("list_interfaces", Fa.INTERFACESVAR)]
    assert not A.granska(
        "IRB1200 ar kopplad till Transportor enligt granssnittslistan.",
        utfall)


def test_en_andring_som_foll_stodjer_inte_pastaendet():
    utfall = [_Utfall("connect", None, ok=False, andrade=True)]
    anm = A.granska("Jag kopplade ihop dem.", utfall)
    assert any(a.kod == "arlighet_pastadd_andring" for a in anm)


def test_matverktyg_raknas_inte_som_andring_i_arligheten():
    """measure_distance ar deklarerat write men andrar ingenting (M-36), och
    faltet andrade kommer ur KODEN och inte ur effect. En modell som bara
    matit har inte kopplat nagot."""
    kod = _kod("measure_distance", {"component": "IRB1200",
                                    "other_component": "Transportor"})
    assert not T.andrar_scenen(kod)
    utfall = [_Utfall("measure_distance", {"distance": 812.0},
                      andrade=bool(T.andrar_scenen(kod)))]
    anm = A.granska("Jag flyttade roboten till plats.", utfall)
    assert [a.kod for a in anm] == ["arlighet_pastadd_andring"]


# ---- 13. VRK-003: relationer, aldrig koordinater -----------------------

def test_en_koordinat_pa_connect_avvisas_av_schemat(forgranskare):
    """Kopplingen ar RELATIONEN. Ett koordinatargument skulle flytta
    geometriraknandet fran VC:s plug and play till modellen."""
    dom = forgranskare.granska_anrop(Mo.Verktygsanrop(
        namn="connect", argument={"component": "IRB1200",
                                  "interface": "BaseInterface",
                                  "other_component": "Transportor",
                                  "other_interface": "OutFeed",
                                  "position": [500.0, 0.0, 0.0]}))
    assert not dom.slapps
    assert dom.avvisning.grind == "argument"
    assert "position" in " ".join(dom.avvisning.skal)


def test_connect_utan_koordinat_haller_schemat(forgranskare):
    dom = forgranskare.granska_anrop(Mo.Verktygsanrop(
        namn="connect", argument={"component": "IRB1200",
                                  "interface": "BaseInterface",
                                  "other_component": "Transportor",
                                  "other_interface": "OutFeed"}))
    assert dom.slapps


# ---- 14. ARB-004: mat efter andringen ----------------------------------

def test_ett_matt_taget_fore_flytten_stods_inte_langre():
    """Talet kommer ur ett RIKTIGT verktygssvar, sa verify-contract stodde
    det fram till M-53. MATT M-11: det beskriver laget fore flytten."""
    grund = Vf.Grund()
    grund.lagg_resultat("measure_distance", {}, {"distance": 812.0})
    tal = Tx.tal_i("Avstandet ar 812 mm.")[0]
    assert grund.stodjer_tal(tal) is None
    grund.ny_generation()
    grund.lagg_resultat("set_transform", {"position": [2500.0, 0.0, 0.0]},
                        {"set": True})
    skal = grund.stodjer_tal(tal)
    assert skal
    assert "ARB-004" in skal
    assert "M-11" in skal


def test_ett_matt_taget_efter_flytten_stods():
    grund = Vf.Grund()
    grund.ny_generation()
    grund.lagg_resultat("set_transform", {"position": [2500.0, 0.0, 0.0]},
                        {"set": True})
    grund.lagg_resultat("measure_distance", {}, {"distance": 812.0})
    tal = Tx.tal_i("Avstandet ar 812 mm.")[0]
    assert grund.stodjer_tal(tal) is None


def test_det_egna_flyttargumentet_hor_till_den_nya_generationen():
    """Bad modellen om en flytt till 2500 mm och anropet gick igenom, sa ar
    2500 ett tal den har ratt att skriva EFTERAT. Generationen hojs darfor
    fore resultatet laggs in."""
    grund = Vf.Grund()
    grund.ny_generation()
    grund.lagg_resultat("set_transform", {"position": [2500.0, 0.0, 0.0]},
                        {"set": True, "position": [2500.0, 0.0, 0.0]})
    tal = Tx.tal_i("Roboten star nu 2500 mm i x-led.")[0]
    assert grund.stodjer_tal(tal) is None


# ---- 15. ARL-007: den regel som SER mekaniserbar ut och inte ar det -----

def test_ett_harkomstkrav_i_samma_mening_hade_fallt_riktiga_kontrollfall():
    """MATNINGEN bakom att ARL-007 star kvar som bedd.

    Regeln kraver talet och dess kalla i SAMMA mening. Provet raknar om
    matningen vid varje korning i stallet for att lita pa ett tal: hur manga
    av bänkens KONTROLLFALL - alltsa korrekt beteende som inte far fallas -
    skulle en sadan grind avvisa? Ar svaret storre an noll gar regeln inte
    att mekanisera utan att korrekt beteende skrivs om for att passa
    grinden, och det ar att lata grinden byta fraga.
    """
    falska = []
    for falla in Fa.KONTROLLFALL:
        verktyg = set(falla.manus or {})
        for svar in falla.svar:
            if not svar.text:
                continue
            for tal in Tx.tal_i(svar.text):
                if not any(v in tal.mening.text for v in verktyg):
                    falska.append((falla.id, tal.mening.text))
    assert falska, ("ingen matmening alls i kontrollfallen - da mater provet "
                    "ingenting och ARL-007 bor provas om")
    assert len(falska) >= 2, falska


def test_de_ej_mekaniska_fallorna_tacker_varje_bedd_regel():
    """Varje regel som fortfarande ar bedd ska ha ett SKRIVET skal.

    EJ_MEKANISK ar harnessens arliga rackviddsredovisning. En bedd regel utan
    en sadan post ar en regel ingen har tagit stallning till - och det var
    precis lage SAK-003 lag i innan M-46 hittade den.
    """
    korpus = I.las_korpus()
    bedda = set(r.id for r in korpus.regler() if r.allvar == "regel")
    namnda = set()
    for falla in Fa.ALLA:
        if falla.facit != Fa.EJ_MEKANISK:
            continue
        namnda |= set(re.findall(r"\b[A-Z]{3}-\d{3}\b", falla.beskrivning))
    saknas = sorted(bedda - namnda)
    assert not saknas, (
        "bedda regler utan ett skrivet skal i nagon EJ_MEKANISK-falla: %s"
        % ", ".join(saknas))


# ---- 16. M-46:s fyra obevisade fynd ------------------------------------

def test_obevisat_1_monstercachen_far_inte_nyckla_pa_id():
    """BEVISAT av M-53. M-46 gissade och misslyckades framkalla krocken.

    CPython aterbrukar adresser ur sin frilista. Fore lagningen svarade
    grinden sa har:

        a = tuple(["alpha"]); bar_ord("alpha beta", a) -> "alpha"
        del a
        b = tuple(["gamma"]); bar_ord("alpha beta", b) -> "alpha"   FEL

    M-46:s forsok anvande TUPELLITERALER, och en literal ligger i
    funktionens co_consts och frigors darfor aldrig - det var hela skalet
    till att krocken inte gick att framkalla.
    """
    forst = tuple(["alpha"])
    assert Tx.bar_ord("alpha beta", forst) == "alpha"
    adress = id(forst)
    del forst
    sedan = tuple(["gamma"])
    assert Tx.bar_ord("alpha beta", sedan) is None, (
        "cachen svarade med en ANNAN ordlistas monster; adress ateranvand: %s"
        % (adress == id(sedan)))


def test_monstercachen_delar_monster_pa_innehall_och_skiljer_pa_olikt():
    a = tuple(["alfa", "beta"])
    b = tuple(["alfa", "beta"])
    assert a is not b
    assert Tx._monster(a) is Tx._monster(b)
    assert Tx._monster(a) is not Tx._monster(tuple(["gamma"]))


def test_obevisat_2_pumpvarningen_nar_modellen_och_anropet_efterat_stoppas(
        korpus, forgranskare):
    """M-46 kunde inte mata om varningen nar modellen. Den gor det.

    Halvan som fortfarande INTE gar att mata utan en levande brygga ar om
    modellen AGERAR pa varningen. Det som daremot ar avgjort sedan M-53 ar
    att anropet efter en pumpdodare inte langre kors alls.
    """
    modell = Mo.AttrappModell([
        Mo.anropa("save_layout", {"uri": "file:///tmp/a.vcmx"}),
        Mo.anropa("get_transform", LAS),
        Mo.sag("Sparad.")])
    kanal = Kn.Attrappkanal({"save_layout": [{"saved": True,
                                              "uri": "file:///tmp/a.vcmx"}],
                             "get_transform": [Fa.TRANSFORMSVAR]})
    protokoll = L.Harness(modell=modell, kanal=kanal, korpus=korpus,
                          forgranskare=forgranskare).kor("Spara layouten.")

    varningar = [h for h in protokoll.handelser if h.sort == "VARNING"]
    assert varningar, "ingen pumpvarning alls"
    assert "M-13" in varningar[0].text

    # Nadde den modellen? Historiken ar det modellen far se i nasta runda.
    sett = [m for h in modell.sedda_historiker for m in h
            if m.roll == "grind" and "M-13" in m.text]
    assert sett, "varningen lades i protokollet men nadde aldrig modellen"

    # Och anropet efter sparningen kordes inte.
    assert protokoll.utfall == "AVVISAD:efter_sparning"
    assert [u.verktyg for u in protokoll.utfallen] == ["save_layout"]


def test_obevisat_3_ett_andra_forsok_kan_lyckas_och_taket_tva_ar_darfor_ratt(
        korpus, forgranskare):
    """M-46 noterade att MAX_LIKA_ANROP=2 ar mildare an VRK-008:s ordalydelse
    och lat fragan sta oprovad.

    Sedan M-53 gar den att avgora, och svaret ar att taket tva ar RATT:
    forgranskningens dom ar inte langre en ren funktion av anropet, eftersom
    turordningsgrindarna laser turens tillstand. Ett IDENTISKT anrop som
    nyss avvisades kan alltsa lyckas efter en lasning emellan - och ett tak
    pa ett hade last modellen ute ur sin egen rattning.
    """
    kopplingen = Mo.anropa("connect", {"component": "IRB1200",
                                       "interface": "BaseInterface",
                                       "other_component": "Transportor",
                                       "other_interface": "OutFeed"})
    modell = Mo.AttrappModell([
        kopplingen,                       # avvisas: olast_scen
        Mo.anropa("list_components"),     # modellen rattar sig
        kopplingen,                       # SAMMA anrop, nu giltigt
        Mo.sag("Jag laste layouten och kopplade sedan ihop dem.")])
    kanal = Kn.Attrappkanal({"list_components": [Fa.LISTSVAR],
                             "connect": [Fa.KOPPLINGSSVAR]})
    protokoll = L.Harness(modell=modell, kanal=kanal, korpus=korpus,
                          forgranskare=forgranskare).kor("Koppla ihop dem.")
    assert [h.kod for h in protokoll.avvisningar] == ["olast_scen"]
    # Turens utfall bar den FORSTA avgorande handelsen, alltsa avvisningen -
    # men anropet kordes den andra gangen, och turen blev klar.
    assert protokoll.klar
    kopplingar = [u for u in protokoll.utfallen if u.verktyg == "connect"]
    assert len(kopplingar) == 1 and kopplingar[0].ok
    assert L.MAX_LIKA_ANROP >= 2


def test_obevisat_4_textlinten_ar_blind_och_importerna_provas_mot_en_lista():
    """M-46 skrev att socketprovet ar textbaserat och lat det sta oprovat.

    Forsta halvan visar blindheten pa en syntetisk kalla: den bar tre vagar
    ut och passerar alla tre textprov. Andra halvan ar lagningen, och den ar
    en VITLISTA i stallet for en svartlista - samma vandning som M-46:s fynd
    1 gjorde pa sprakmarkningen. Ett godkannande ur tystnad ar inget
    godkannande (I3).
    """
    smugglad = ("import http.client\n"
                "import asyncio\n"
                "s = __import__('soc' + 'ket')\n")
    assert "import socket" not in smugglad
    assert "urllib" not in smugglad
    assert "requests" not in smugglad

    tillatna = {
        "__future__", "ast", "dataclasses", "hashlib", "json", "os", "re",
        "sys", "types", "typing", "unicodedata",
        # Repots egna, ur ext/ och bank/. De nas via sys.path och ar inte
        # tredjepart.
        "skrivgrind", "oga_kontrakt", "lasare",
    }
    import ast as _ast
    katalog = os.path.join(_ROT, "svc", "vc_assist_svc", "harness")
    okanda = []
    for filnamn in sorted(os.listdir(katalog)):
        if not filnamn.endswith(".py"):
            continue
        with open(os.path.join(katalog, filnamn), encoding="utf-8") as f:
            trad = _ast.parse(f.read())
        for nod in _ast.walk(trad):
            namn = []
            if isinstance(nod, _ast.Import):
                namn = [a.name.split(".")[0] for a in nod.names]
            elif isinstance(nod, _ast.ImportFrom) and not nod.level:
                namn = [(nod.module or "").split(".")[0]]
            elif (isinstance(nod, _ast.Call)
                  and getattr(nod.func, "id", "") == "__import__"):
                okanda.append((filnamn, "__import__()"))
            for n in namn:
                if n and n not in tillatna:
                    okanda.append((filnamn, n))
    assert not okanda, (
        "harnessen importerar nagot som inte star pa vitlistan: %s" % okanda)
