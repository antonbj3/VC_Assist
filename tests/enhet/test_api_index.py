# -*- coding: utf-8 -*-
"""L0/L1 for fas 4: API-indexet och AST-validatorn.

Grinden star i docs/spec/46_kunskapsindex.md och docs/spec/70_faser.md:

  1. indexet bar minst de matta 204 typerna, 966 metoderna, 1159 egenskaperna
  2. ett kant namn ger exakt signatur
  3. ett pahittat namn ger TOMT svar, aldrig en gissning
  4. over N forsok: NOLL uppfunna namn slipper igenom

Punkt 4 ar matningen langst ner. Provsamlingen ar tudelad: kodstrangar med
KANDA uppfunna namn (typiska hallucinationer mot VC:s API) och kodstrangar
byggda av riktiga namn. Falskt positiva och falskt negativa rapporteras som
TAL, inte som omdomen.

Kor: cd ~/projects/VC_Assist && python3 -m pytest tests/enhet/test_api_index.py -q
"""
import os
import sys

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "svc")))

from vc_assist_svc.api_index import (          # noqa: E402
    FORSLAG_AVSTAND_TAK, INSTRUKTION, MAX_FORSLAG, NARAMISS_AVSTAND,
    ApiIndex, Validator, avstand, bygg_index, bygg_validator)


@pytest.fixture(scope="module")
def index():
    return bygg_index()


@pytest.fixture(scope="module")
def validator(index):
    return Validator(index)


# --------------------------------------------------------------- provsamling
#
# Varje post: id, kod, det uppfunna namnet, det namn modellen uppenbart menade
# (eller None nar det inte finns nagot), klassen, och den TYP namnet slas upp
# pa (None for konstanter, typnamn och hjalpmoduler):
#
#   stavfel     en fordarvning av ett riktigt namn (inklusive fel skiftlage)
#   annat_api   ett namn som ar riktigt i NAGON annan 3D-/simuleringsyta
#   uppfunnen   helt pahittat, utan forlaga
#
# Alla uppfunna namn ar kontrollerade mot indexet av
# test_de_uppfunna_namnen_finns_verkligen_inte.

UPPFUNNA = [
    ("app.getComponentByName", """
app = getApplication()
comp = app.getComponentByName("Conveyor")
""", "getComponentByName", "findComponent", "annat_api", "vcApplication"),

    ("comp.setPosition", """
app = getApplication()
comp = app.findComponent("Robot")
comp.setPosition(1000.0, 0.0, 0.0)
""", "setPosition", "PositionMatrix", "annat_api", "vcComponent"),

    ("comp.getPosition", """
app = getApplication()
comp = app.findComponent("Robot")
p = comp.getPosition()
""", "getPosition", "WorldPositionMatrix", "annat_api", "vcComponent"),

    ("app.getComponents", """
app = getApplication()
for comp in app.getComponents():
    pass
""", "getComponents", "Components", "annat_api", "vcApplication"),

    ("app.removeComponent", """
app = getApplication()
comp = app.findComponent("Conveyor")
app.removeComponent(comp)
""", "removeComponent", "deleteComponent", "annat_api", "vcApplication"),

    ("sim.start", """
app = getApplication()
sim = app.Simulation
sim.start()
""", "start", "run", "annat_api", "vcSimulation"),

    ("sim.stop", """
app = getApplication()
sim = app.Simulation
sim.stop()
""", "stop", "halt", "annat_api", "vcSimulation"),

    ("ctrl.moveToTarget", """
app = getApplication()
comp = app.findComponent("Robot")
ctrl = comp.findBehaviour("Controller")
t = ctrl.createTarget()
ctrl.moveToTarget(t)
""", "moveToTarget", "moveTo", "annat_api", "vcBehaviour"),

    ("servo.setSpeed", """
app = getApplication()
comp = app.findComponent("Robot")
servo = comp.findBehaviour("ServoController")
servo.setSpeed(500.0)
""", "setSpeed", "Speed", "annat_api", "vcBehaviour"),

    ("iface.connectTo", """
app = getApplication()
a = app.findComponent("Conveyor")
b = app.findComponent("Robot")
ia = a.findBehaviour("Interface")
ib = b.findBehaviour("Interface")
ia.connectTo(ib)
""", "connectTo", "connect", "annat_api", "vcBehaviour"),

    ("iface.isConnected", """
app = getApplication()
comp = app.findComponent("Conveyor")
iface = comp.findBehaviour("Interface")
if iface.isConnected():
    pass
""", "isConnected", "IsConnected", "stavfel", "vcBehaviour"),

    ("node.getChildren", """
app = getApplication()
comp = app.findComponent("Conveyor")
for n in comp.getChildren():
    pass
""", "getChildren", "Children", "annat_api", "vcComponent"),

    ("node.getName", """
app = getApplication()
comp = app.findComponent("Conveyor")
namn = comp.getName()
""", "getName", "Name", "annat_api", "vcComponent"),

    ("comp.PostionMatrix", """
app = getApplication()
comp = app.findComponent("Conveyor")
m = comp.PostionMatrix
""", "PostionMatrix", "PositionMatrix", "stavfel", "vcComponent"),

    ("sim.SimSped", """
app = getApplication()
sim = app.Simulation
sim.SimSped = 10.0
""", "SimSped", "SimSpeed", "stavfel", "vcSimulation"),

    ("det.testCollision", """
app = getApplication()
sim = app.Simulation
det = sim.newCollisionDetector()
if det.testCollision():
    pass
""", "testCollision", "testAllCollisions", "annat_api", "vcCollisionDetector"),

    ("det.getMinimumDistance", """
app = getApplication()
sim = app.Simulation
det = sim.newCollisionDetector()
d = det.getMinimumDistance()
""", "getMinimumDistance", "getMinimumDistanceDistance", "annat_api",
     "vcCollisionDetector"),

    ("app.loadComponent", """
app = getApplication()
comp = app.loadComponent("C:/lib/conveyor.vcm")
""", "loadComponent", "load", "annat_api", "vcApplication"),

    ("prop.setValue", """
app = getApplication()
comp = app.findComponent("Conveyor")
p = comp.getProperty("Speed")
p.setValue(500.0)
""", "setValue", "Value", "annat_api", "vcProperty"),

    ("comp.getPropety", """
app = getApplication()
comp = app.findComponent("Conveyor")
p = comp.getPropety("Speed")
""", "getPropety", "getProperty", "stavfel", "vcComponent"),

    ("iface.canConect", """
app = getApplication()
a = app.findComponent("Conveyor")
b = app.findComponent("Robot")
ia = a.findBehaviour("Interface")
ib = b.findBehaviour("Interface")
if ia.canConect(ib):
    pass
""", "canConect", "canConnect", "stavfel", "vcBehaviour"),

    ("VC_SIMULATION_RUNNING", """
app = getApplication()
sim = app.Simulation
if sim.IsRunning == VC_SIMULATION_RUNNING:
    pass
""", "VC_SIMULATION_RUNNING", None, "uppfunnen", None),

    ("vcHelpers.Conveyor", """
from vcHelpers.Conveyor import *
""", "vcHelpers.Conveyor", None, "uppfunnen", None),

    ("vcRobot", """
app = getApplication()
comp = app.findComponent("Robot")
if isinstance(comp, vcRobot):
    pass
""", "vcRobot", "vcRobotController", "uppfunnen", None),

    ("robot.pickPart", """
from vcHelpers.Robot import *
robot = getRobot(getComponent())
robot.pickPart("Part")
""", "pickPart", None, "uppfunnen", "vcHelpers.Robot"),

    ("comp.Position", """
app = getApplication()
comp = app.findComponent("Conveyor")
p = comp.Position
""", "Position", "PositionMatrix", "uppfunnen", "vcComponent"),

    ("app.Components.count", """
app = getApplication()
n = app.Components.getCount()
""", "getCount", None, "uppfunnen", None),

    ("hake OnComponentAdded", """
def OnComponentAdded(component):
    lada = component.getBoundingBox()
""", "getBoundingBox", None, "uppfunnen", "vcComponent"),

    ("hake OnSignal", """
def OnSignal(signal):
    v = signal.getValue()
""", "getValue", "Value", "annat_api", "vcSignal"),
]

KORREKTA = [
    ("lista komponenter", """
app = getApplication()
for comp in app.Components:
    namn = comp.Name
"""),
    ("hitta och flytta", """
app = getApplication()
comp = app.findComponent("Conveyor")
m = comp.PositionMatrix
comp.PositionMatrix = m
"""),
    ("ladda och klona", """
app = getApplication()
comp = app.load("C:/lib/conveyor.vcm")
kopia = comp.clone()
"""),
    ("radera", """
app = getApplication()
comp = app.findComponent("Conveyor")
app.deleteComponent(comp)
"""),
    ("nodtrad", """
app = getApplication()
comp = app.findComponent("Conveyor")
for nod in comp.Children:
    m = nod.WorldPositionMatrix
"""),
    ("las egenskap", """
app = getApplication()
comp = app.findComponent("Conveyor")
p = comp.getProperty("ConveyorSpeed")
v = p.Value
"""),
    ("skapa egenskap", """
app = getApplication()
comp = app.findComponent("Conveyor")
p = comp.createProperty(VC_REAL, "Takt")
p.Value = 2.5
"""),
    ("egenskapslista", """
app = getApplication()
comp = app.findComponent("Conveyor")
namn = [p.Name for p in comp.Properties]
"""),
    ("koppla granssnitt", """
app = getApplication()
a = app.findComponent("Conveyor")
b = app.findComponent("Robot")
ia = a.findBehaviour("Interface")
ib = b.findBehaviour("Interface")
if ia.canConnect(ib):
    ia.connect(ib)
"""),
    ("koppla isar", """
app = getApplication()
a = app.findComponent("Conveyor")
ia = a.findBehaviour("Interface")
ia.disconnect()
"""),
    ("simuleringen", """
app = getApplication()
sim = app.Simulation
sim.reset()
sim.run()
sim.halt()
"""),
    ("simuleringstakt", """
app = getApplication()
sim = app.Simulation
sim.SimSpeed = 10.0
t = sim.SimTime
"""),
    ("robotbana", """
app = getApplication()
comp = app.findComponent("Robot")
ctrl = comp.findBehaviour("Controller")
mal = ctrl.createTarget()
ctrl.addTarget(mal)
ctrl.moveTo(mal)
"""),
    ("robotgranser", """
app = getApplication()
comp = app.findComponent("Robot")
ctrl = comp.findBehaviour("Controller")
v = ctrl.MaxCartesianSpeed
a = ctrl.MaxCartesianAccel
"""),
    ("servoleder", """
app = getApplication()
comp = app.findComponent("Robot")
servo = comp.findBehaviour("ServoController")
for i in range(servo.JointCount):
    v = servo.getJointValue(i)
"""),
    ("kollisionsprov", """
app = getApplication()
sim = app.Simulation
det = sim.newCollisionDetector()
det.Active = True
if det.testAllCollisions():
    n = det.HitCount
"""),
    ("minsta avstand", """
app = getApplication()
sim = app.Simulation
det = sim.newCollisionDetector()
d = det.getMinimumDistanceDistance()
p1 = det.getMinimumDistancePoint1()
"""),
    ("bildfangst", """
app = getApplication()
app.beginFrameGrab("png", 1280, 720)
app.executeFrameGrab("C:/ut/bild.png")
app.endFrameGrab()
"""),
    ("kamerastrale", """
app = getApplication()
kamera = app.findCamera("Main")
stralen = kamera.getRay(0.5, 0.5)
"""),
    ("vyer", """
app = getApplication()
vy = app.createView("Ovanifran")
app.useView("Ovanifran")
"""),
    ("spara layout", """
app = getApplication()
app.save("C:/ut/layout.vcmx", True)
"""),
    ("statistik", """
app = getApplication()
sim = app.Simulation
comp = app.findComponent("Conveyor")
stat = comp.findBehaviour("Statistics")
p = stat.BusyPercentage
"""),
    ("hjalpare robot", """
from vcHelpers.Robot import *
robot = getRobot(getComponent())
leder = robot.Joints
robot.Speed = 500.0
"""),
    ("hjalpare urval", """
from vcHelpers.Selection import *
for comp in getSelectedComponents():
    namn = comp.Name
"""),
    ("signalvarde", """
app = getApplication()
comp = app.findComponent("Conveyor")
signal = comp.findBehaviour("StartSignal")
signal.Value = True
"""),
    ("efterslapande blanksteg i kallan", """
app = getApplication()
sim = app.Simulation
ctrl = sim.ProcessController
"""),
    ("matning mellan noder", """
app = getApplication()
a = app.findComponent("Conveyor")
b = app.findComponent("Robot")
d = a.measureDistance([a, b])
"""),
    ("mata scenen ur skriptet", """
komponent = getComponent()
sim = getSimulation()
utlosare = getTrigger()
namn = komponent.Name
"""),
    ("hake OnComponentAdded", """
def OnComponentAdded(component):
    namn = component.Name
    m = component.WorldPositionMatrix
"""),
    ("hake OnSignal", """
def OnSignal(signal):
    if signal.Value:
        namn = signal.Name
"""),
]


# ------------------------------------------------------------------- indexet


def test_indexet_bar_de_matta_talen(index):
    """docs/spec/10_matta_fakta.md: 204 typer, 966 metoder, 1159 egenskaper."""
    s = index.statistik()
    assert s["typer"] == 204
    assert s["metoder"] == 966
    assert s["egenskaper"] == 1159
    assert s["handelser"] == 175
    assert s["konstanter"] == 709
    assert s["hjalpmoduler"] == 8


def test_kant_namn_ger_exakt_signatur(index):
    (symbol,) = index.slag_upp("vcRobotController.moveTo")
    assert symbol.sort == "metod"
    assert symbol.signatur == ("vcMotionTarget target or vcMatrix matrix,"
                               " [Enumeration target_mode]")
    assert symbol.vardetyp == "None"
    assert symbol.kalla == "vc_python_api.json"
    assert symbol.berikad_av == "api.xml"


def test_svaret_bar_instruktionen_ordagrant(index):
    (symbol,) = index.slag_upp("vcApplication.findComponent")
    svar = symbol.svar()
    assert INSTRUKTION in svar
    assert "String name" in svar


def test_traffen_bar_sin_harkomst_klass_och_fil(index):
    traffar = index.sok("findComponent")
    assert traffar
    harkomst = traffar[0].harkomst
    assert "vcApplication" in harkomst
    assert "vc_python_api.json" in harkomst
    assert "4.10" in harkomst


def test_pahittat_namn_ger_tomt_svar_aldrig_en_gissning(index):
    """docs/spec/46, punkt 3. Forslag ar en EGEN fraga, aldrig en del av svaret."""
    assert index.slag_upp("vcComponent.setPosition") == []
    assert index.slag_upp("getComponentByName") == []
    assert index.slag_upp("vcRobot") == []
    assert index.slag_upp("vcRobot.moveTo") == []


def test_soket_tal_delstrang_och_skiftlage(index):
    namn = [t.symbol.namn for t in index.sok("FINDcomponent", grans=5)]
    assert "findComponent" in namn
    delstrang = [t.symbol.namn for t in index.sok("mponent", grans=50)]
    assert "findComponent" in delstrang
    assert index.sok("") == []


def test_soket_rangordnar_exakt_fore_delstrang(index):
    traffar = index.sok("Components", grans=10)
    assert traffar[0].rang == "exakt"
    assert traffar[0].poang >= traffar[-1].poang


def test_soket_hittar_pa_beskrivning(index):
    traffar = index.sok("minimum distance", grans=20)
    namn = set(t.symbol.namn for t in traffar)
    assert "getMinimumDistanceDistance" in namn


def test_arvet_ger_medlemmar_fran_foraldern(index):
    """vcComponent arver vcNode i api.xml; Name ligger pa vcNode."""
    assert index.medlem("vcComponent", "Name")
    assert "vcNode" in index.arvskedja("vcComponent")
    assert not index._medlemmar["vcComponent"].get("Name")


def test_efterslapande_blanksteg_i_kallan_ar_strippade(index):
    """Matt: 84 egenskaps- och 56 metodnamn i api.xml bar ett slutblanksteg."""
    assert index.statistik()["strippade_namn"] > 0
    assert index.medlem("vcSimulation", "ProcessController")
    assert index.medlem("vcProduct", "getProperty")


def test_egenskaper_med_parameterlista_ar_raknade(index):
    """Kallan felklassar 34 metoder som egenskaper. Namnen far inte tappas."""
    assert index.statistik()["egenskaper_med_parameterlista"] == 34
    (symbol,) = index.slag_upp("vcCurveData.getCurveLength")
    assert symbol.signatur == "Integer curve"


def test_typytan_bar_bade_egna_och_arvda_medlemmar(index):
    yta = index.typytan("vcComponent")
    assert "clone" in yta            # egen metod
    assert "Name" in yta             # arvd fran vcNode
    assert "PositionMatrix" in yta   # arvd fran vcNode
    assert len(yta) > len(index.typytan("vcNode")) - 1


def test_undertyperna_gar_att_fraga_efter(index):
    assert "vcSimInterface" in index.subtyper("vcBehaviour")
    assert index.medlem_i_subtyp("vcBehaviour", "canConnect")
    assert index.medlem_i_subtyp("vcBehaviour", "detFinnsInteAlls") == []


def test_samma_namn_pa_flera_typer_gar_att_lista(index):
    agare = set(s.typ_namn for s in index.symboler_med_namn("getProperty"))
    assert "vcComponent" in agare and "vcAction" in agare


def test_saknad_kalla_kastar_i_stallet_for_att_ge_ett_halvt_index(tmp_path):
    """S1: en ofardig vag kastar, den returnerar aldrig framgang."""
    with pytest.raises(IOError):
        ApiIndex(katalog=str(tmp_path))


def test_bygg_validator_ger_en_kord_validator():
    """Tjanstens ingang: ett anrop ska racka."""
    v = bygg_validator()
    assert v.granska("app = getApplication()\nn = app.Components\n").godkand


def test_avstandet_ar_noll_pa_lika_och_symmetriskt():
    assert avstand("moveTo", "moveTo") == 0
    assert avstand("moveTo", "MOVETO") == 0        # skiftlagesokansligt
    assert avstand("a", "abc") == avstand("abc", "a") == 2


def test_narmaste_hittar_stavfelet(index):
    forslag = index.narmaste("PostionMatrix", typ_namn="vcComponent")
    assert forslag[0][0] == "vcComponent.PositionMatrix"
    assert forslag[0][1] == 1


def test_de_uppfunna_namnen_finns_verkligen_inte(index):
    """Provsamlingen ar bara vard nagot om namnen faktiskt saknas dar de slas upp."""
    kvar = []
    for prov_id, _kod, namn, _avsett, _klass, typ in UPPFUNNA:
        bart = namn.rpartition(".")[2]
        if typ is not None:
            # Namnet far finnas pa NAGON annan typ (start finns pa
            # vcActionContainer); det som ska saknas ar traffen dar koden slar
            # upp det, arv och undertyper inrakade.
            if index.medlem(typ, bart) or index.medlem_i_subtyp(typ, bart):
                kvar.append(prov_id)
        elif index.slag_upp(bart) or namn in index.hjalpmoduler:
            kvar.append(prov_id)
    assert kvar == []


# ----------------------------------------------------------------- validatorn


def test_validatorn_slapper_igenom_riktig_kod(validator):
    g = validator.granska(KORREKTA[0][1])
    assert g.godkand, g.rapport()


def test_okant_namn_ar_ett_fel_med_forslag(validator):
    """Stavfelet PostionMatrix ska falla OCH peka pa det riktiga namnet."""
    g = validator.granska("""
app = getApplication()
comp = app.findComponent("Conveyor")
m = comp.PostionMatrix
""")
    assert not g.godkand
    (fel,) = g.fel
    assert fel.sort == "okant_medlemsnamn"
    assert fel.namn == "vcComponent.PostionMatrix"
    assert fel.forslag[0] == ("vcComponent.PositionMatrix", 1)


def test_utan_nara_namn_ges_inget_forslag_alls(index):
    """Ett forslag bortom taket ar en gissning. Tom lista ar det arliga svaret."""
    assert index.narmaste("qqqqqqqqqqqqqqqqqqqq") == []
    assert index.narmaste("zzzzzzzzzzzzzzzzzz", typ_namn="vcComponent") == []


def test_grinden_faller_pa_trasig_fixtur(validator):
    """docs/spec/95_testprotokoll.md: en grind utan trasig fixtur ar oprovad."""
    g = validator.granska("""
app = getApplication()
comp = app.findComponent("X")
comp.teleportTo(0, 0, 0)
""")
    assert not g.godkand
    assert any(f.namn == "vcComponent.teleportTo" for f in g.fel)


def test_dynamiskt_uppslag_ar_obestambart_inte_godkant(validator):
    """Det gar inte att doma statiskt, och da sager validatorn det."""
    g = validator.granska("""
app = getApplication()
comp = app.findComponent("X")
namn = "PositionMatrix"
m = getattr(comp, namn)
""")
    assert not g.godkand
    assert not g.fel
    (obestambar,) = g.obestambara
    assert obestambar.sort == "dynamiskt_uppslag"


def test_getattr_med_strangkonstant_gar_att_doma(validator):
    god = validator.granska("""
app = getApplication()
comp = app.findComponent("X")
m = getattr(comp, "PositionMatrix")
""")
    assert god.godkand, god.rapport()
    ond = validator.granska("""
app = getApplication()
comp = app.findComponent("X")
m = getattr(comp, "getPosition")
""")
    assert not ond.godkand


def test_okand_modulfunktion_ar_obestambar_inte_ett_pastaende(validator):
    """vcScript:s modulfunktioner star inte i nagon matt kalla."""
    g = validator.granska("getSelectedComponent()")
    assert not g.godkand
    assert not g.fel
    assert g.obestambara[0].sort == "okand_modulfunktion"


def test_python2_print_ger_fel_inte_godkannande(validator):
    """VC 4.10 kor Python 2.7; validatorn parsar med 3 och sager det rakt ut."""
    g = validator.granska('print "hej"\n')
    assert not g.godkand
    (fel,) = g.fel
    assert fel.sort == "ej_parsbar"
    assert "Python 2" in fel.text


def test_uppfunnen_konstant_fangas(validator):
    g = validator.granska(UPPFUNNA[21][1])
    assert not g.godkand
    assert any(f.sort == "okand_konstant" for f in g.fel)


def test_uppfunnen_hjalpmodul_fangas(validator):
    g = validator.granska("from vcHelpers.Conveyor import *\n")
    assert not g.godkand
    (fel,) = g.fel
    assert fel.sort == "okand_hjalpmodul"


def test_uppfunnen_typ_fangas(validator):
    g = validator.granska("""
app = getApplication()
comp = app.findComponent("R")
if isinstance(comp, vcRobot):
    pass
""")
    assert not g.godkand
    assert any(f.sort == "okand_typ" for f in g.fel)


def test_nedcastning_slapps_igenom_med_notering(validator):
    """findBehaviour deklareras som vcBehaviour men ger en undertyp."""
    g = validator.granska(KORREKTA[12][1])
    assert g.godkand, g.rapport()
    assert any("undertyp" in n for n in g.noteringar)


def test_python_egna_namn_domes_inte(validator):
    """Validatorn domer VC-namn. str.split ar inte dess bord."""
    g = validator.granska("""
app = getApplication()
comp = app.findComponent("X")
delar = comp.Name.split("_")
""")
    assert g.godkand, g.rapport()


def test_haken_far_typade_parametrar_ur_handelsen(validator):
    """def OnComponentAdded(component) -- api.xml deklarerar vcComponent."""
    ond = validator.granska("""
def OnComponentAdded(component):
    component.setPosition(0.0, 0.0, 0.0)
""")
    assert not ond.godkand
    assert ond.fel[0].namn == "vcComponent.setPosition"

    god = validator.granska("""
def OnComponentAdded(component):
    namn = component.Name
""")
    assert god.godkand, god.rapport()


def test_egen_funktions_parameter_domes_inte_alls(validator):
    """Den kvarvarande blinda flacken, uttalad i stallet for gomd.

    En parameter till en EGEN funktion har ingen deklarerad typ och ingen
    kalla att jamfora mot, sa uppslag pa den domes inte. Ett uppfunnet namn
    dar slipper igenom. Att stanga det kraver att anropsstallets argumenttyper
    propageras in i kroppen -- inte byggt, och darfor inte pastatt.
    """
    g = validator.granska("""
def flytta(comp):
    comp.setPosition(0.0, 0.0, 0.0)
""")
    assert g.godkand
    assert g.kontrollerade_namn == 0


# ------------------------------------------------------------------ matningen


def _mat(validator):
    """Kor hela provsamlingen och returnera de rena talen."""
    falskt_negativa = []      # uppfunnet namn som slapptes igenom
    falskt_positiva = []      # riktig kod som inte godkandes
    som_fel = 0
    som_obestambart = 0
    forslag_traff = 0
    forslag_mojliga = 0
    forslag_rang = []

    for prov_id, kod, namn, avsett, _klass, _typ in UPPFUNNA:
        g = validator.granska(kod)
        if g.godkand:
            falskt_negativa.append(prov_id)
            continue
        bart = namn.rpartition(".")[2]
        traffade_namnet = any(f.namn.rpartition(".")[2] == bart for f in g.fel)
        if traffade_namnet:
            som_fel += 1
        elif any(o.namn.rpartition(".")[2] == bart for o in g.obestambara):
            som_obestambart += 1
        if avsett is not None and traffade_namnet:
            forslag_mojliga += 1
            for fel in g.fel:
                if fel.namn.rpartition(".")[2] != bart:
                    continue
                namnen = [n.rpartition(".")[2] for n, _d in fel.forslag]
                if avsett in namnen:
                    forslag_traff += 1
                    forslag_rang.append(namnen.index(avsett) + 1)

    for prov_id, kod in KORREKTA:
        g = validator.granska(kod)
        if not g.godkand:
            falskt_positiva.append((prov_id, g.rapport()))

    return {
        "forsok": len(UPPFUNNA) + len(KORREKTA),
        "uppfunna": len(UPPFUNNA),
        "korrekta": len(KORREKTA),
        "falskt_negativa": falskt_negativa,
        "falskt_positiva": falskt_positiva,
        "fangade_som_fel": som_fel,
        "fangade_som_obestambart": som_obestambart,
        "forslag_traff": forslag_traff,
        "forslag_mojliga": forslag_mojliga,
        "forslag_rang": forslag_rang,
    }


@pytest.fixture(scope="module")
def matning(validator):
    return _mat(validator)


def test_matt_noll_uppfunna_namn_slipper_igenom(matning):
    """Fasens grind: "Matt over N forsok: noll uppfunna namn"."""
    assert matning["falskt_negativa"] == [], (
        "%d av %d uppfunna namn godkandes: %s"
        % (len(matning["falskt_negativa"]), matning["uppfunna"],
           matning["falskt_negativa"]))


def test_matt_noll_falskt_positiva(matning):
    """Riktig kod far inte fallas. En grind som fyrar pa allt mater ingenting."""
    assert matning["falskt_positiva"] == [], "\n".join(
        "%s:\n%s" % (namn, rapport)
        for namn, rapport in matning["falskt_positiva"])


def test_varje_uppfunnet_namn_pekades_ut_med_namn(matning):
    """Det racker inte att koden fallas -- namnet ska namnges."""
    assert (matning["fangade_som_fel"] + matning["fangade_som_obestambart"]
            == matning["uppfunna"])


def test_forslagstrosklarna_kommer_ur_provsamlingen(index):
    """docs/spec/41_ogat_kontrakt.md: ingen troskel utan sin matning."""
    def traffar(antal, tak):
        traff = []
        for _id, _kod, namn, avsett, _klass, typ in UPPFUNNA:
            if not avsett:
                continue
            bart = namn.rpartition(".")[2]
            forslag = index.narmaste(bart, typ_namn=typ, antal=antal, tak=tak)
            if avsett in [n.rpartition(".")[2] for n, _d in forslag]:
                traff.append((avstand(bart, avsett), _id))
        return traff

    # FORSLAG_AVSTAND_TAK: langsta avstand som anda hamnar i listan, och att
    # ett storre tak inte ger en enda traff till.
    inom = traffar(MAX_FORSLAG, tak=99)
    assert max(d for d, _ in inom) == FORSLAG_AVSTAND_TAK
    assert len(traffar(MAX_FORSLAG, FORSLAG_AVSTAND_TAK)) == len(inom)

    # MAX_FORSLAG: brytpunkten over de 23 fall som har ett avsett namn.
    med_avsett = sum(1 for x in UPPFUNNA if x[3])
    assert med_avsett == 24
    assert len(traffar(3, 99)) == 14
    assert len(traffar(5, 99)) == 18
    assert len(traffar(7, 99)) == 20
    assert len(traffar(10, 99)) == 20
    assert MAX_FORSLAG == 5

    # NARAMISS_AVSTAND: stavfelsklassens storsta avstand.
    stavfel = [avstand(namn.rpartition(".")[2], avsett)
               for _id, _kod, namn, avsett, klass, _typ in UPPFUNNA
               if klass == "stavfel" and avsett]
    assert max(stavfel) == NARAMISS_AVSTAND


def test_forslaget_rymmer_det_avsedda_namnet(matning):
    """MAX_FORSLAG ar satt av var i listan det avsedda namnet hamnar."""
    assert matning["forslag_rang"]
    assert max(matning["forslag_rang"]) <= MAX_FORSLAG


def test_matningen_ar_stor_nog_for_att_betyda_nagot(matning):
    """Uppdraget: minst 20 uppfunna och minst 20 korrekta."""
    assert matning["uppfunna"] >= 20
    assert matning["korrekta"] >= 20


def test_rapportera_talen(matning, capsys):
    """Skriver ut matningen sa att den gar att lasa i -q -s."""
    with capsys.disabled():
        print("\nFAS 4 MATNING over %d forsok:" % matning["forsok"])
        print("  uppfunna kodstrangar:        %d" % matning["uppfunna"])
        print("  korrekta kodstrangar:        %d" % matning["korrekta"])
        print("  falskt negativa (slapptes):  %d" % len(matning["falskt_negativa"]))
        print("  falskt positiva (fastnade):  %d" % len(matning["falskt_positiva"]))
        print("  fangade som FEL:             %d" % matning["fangade_som_fel"])
        print("  fangade som OBESTAMBART:     %d" % matning["fangade_som_obestambart"])
        print("  avsett namn i forslagen:     %d av %d"
              % (matning["forslag_traff"], matning["forslag_mojliga"]))
