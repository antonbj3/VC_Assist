# Täckningsanalys — hela API-ytan mot ett verktygsbibliotek

`45_verktyg.md` beskriver **formen** på verktygslagret. Det här dokumentet
beskriver **omfånget**: hur stor VC:s API-yta är, hur den delar sig i domäner,
vad ett verktyg per domän skulle heta och bygga på, i vilken ordning det ska
byggas, och — lika viktigt — **vad som inte går att bygga alls**.

Måttet: källprojektet bär 448 verktyg (`20_arv.md`). Vi bär 21.

beskriver: `svc/vc_assist_svc/api_index.py`, `svc/vc_assist_svc/verktyg/`,
`docs/referens/vc_api/`, `docs/referens/vc_dotnet/`

---

## 1. Metod — varifrån varje tal kommer

Ingen siffra i det här dokumentet är uppskattad. Alla kommer ur körningar mot
`svc/vc_assist_svc/api_index.py`, som i sin tur läser
`docs/referens/vc_api/vc_python_api.json`, `api.xml`, `constants.xml` och
`helpers.xml`.

**Grundtalen**, ur `ApiIndex.statistik()`:

```python
import sys; sys.path.insert(0, "svc")
from vc_assist_svc.api_index import bygg_index
print(bygg_index().statistik())
```

```
typer 204 · metoder 966 · egenskaper 1159 · handelser 175 · konstanter 709
hjalpmoduler 8 · hjalpmedlemmar 223 · symboler_totalt 3444
```

**Per domän** räknas så här, och regeln är mekanisk:

1. Varje av de 204 typerna tilldelas **exakt en** domän. Kartan är
   handskriven men kontrollerad: skriptet kastar om en typ står i två domäner,
   om en typ i kartan inte finns i indexet, eller om någon av de 204 saknar
   domän.
2. Medlemmar räknas som **egendeklarerade**, inte ärvda. `typytan()` räknar in
   arv och skulle dubbelräkna `vcBehaviour.delete` över 20 beteendetyper.
   Därför räknas ur `ApiIndex.symboler` på `typ_namn`.
3. Kontrollen att indelningen är fullständig är att summan **måste** bli
   204 / 966 / 1159 / 175. Den gör det. En domänindelning som inte summerar
   till helheten mäter inte helheten.

Skriptet ligger inte i repot — det är en engångsräkning, och dess enda
resultat är tabellen nedan. Den som vill räkna om kan återskapa det ur
kartan i avsnitt 4: domännamnen och typlistorna står där.

**Verifiering av föreslagna verktyg.** Varje namn i kolumnen "Bygger på" är
slaget upp med `ApiIndex.slag_upp()` respektive `ApiIndex.medlem()`. Vid
skrivningen fälldes bland annat `vcApplication.exportLayoutAsGeometry`
(finns bara på `vcCommand`) och `VC_LAYOUTITEM_IT_REPORT` (heter
`_REPORTBOM`, `_REPORTCHART`, `_REPORTIMAGE`). **Uppfunna namn är den enda
felklass det här dokumentet självt kan lida av, och den kontrollen är körd.**

---

## 2. Mätta tal per domän

23 domäner. Sorterade på API-yta (metoder + egenskaper).

| Domän | typer | metoder | egenskaper | händelser | byggda verktyg |
|---|---|---|---|---|---|
| geometri | 23 | 145 | 132 | 1 | 0 |
| scen | 14 | 67 | 121 | 4 | **15** |
| process | 24 | 84 | 94 | 38 | 0 |
| program | 19 | 79 | 99 | 15 | 0 |
| ui | 10 | 81 | 83 | 14 | 0 |
| app | 8 | 91 | 67 | 11 | 0 |
| produkt | 20 | 49 | 80 | 11 | 0 |
| statistik | 7 | 65 | 49 | 2 | 0 |
| kinematik | 6 | 33 | 59 | 17 | 0 |
| robot | 9 | 31 | 56 | 3 | 0 |
| mätning | 4 | 30 | 35 | 1 | 0 |
| rörelsebana | 8 | 18 | 44 | 2 | 0 |
| flöde | 11 | 21 | 38 | 7 | 0 |
| montering | 6 | 25 | 25 | 11 | 0 |
| signal | 10 | 27 | 19 | 4 | 0 |
| transportsystem | 5 | 14 | 29 | 11 | 0 |
| enheter | 5 | 14 | 26 | 0 | 0 |
| matematik | 2 | 38 | 2 | 0 | 0 |
| simulering | 2 | 23 | 17 | 15 | 0 |
| utseende | 4 | 0 | 34 | 0 | 0 |
| komposition | 3 | 9 | 23 | 4 | **6** |
| fordon | 1 | 20 | 9 | 4 | 0 |
| vy | 3 | 2 | 18 | 0 | 0 |
| **summa** | **204** | **966** | **1159** | **175** | **21** |

Två domäner av 23 är påbörjade. De bär 17 av 204 typer och 76 av 966 metoder.
**Täckningen är alltså 8 procent av typerna, mätt.**

### 2.1 `vcApplication` är den enda typen som spänner över allt

79 metoder, 54 egenskaper, 11 händelser — 144 medlemmar, mer än var tjugonde
symbol i hela API:t. Den räknas i domänen `app` ovan, men det döljer att den
i praktiken är ingången till nio domäner. Medlemsvis fördelning, samma
mekaniska kontroll (varje medlem i exakt en domän, summan måste bli 144):

| Domän som `vcApplication`-medlemmen tjänar | antal |
|---|---|
| ui (menyer, urval, kommandon, meddelanden) | 30 |
| vy (kameror, vyer, bildfångst, inspelning, klippplan) | 27 |
| app (identitet, sökvägar, kontext, livscykelhändelser) | 27 |
| scen (komponenter, layout, ladda, spara) | 21 |
| utseende (material, ljus, lager) | 12 |
| enheter (kvantiteter, enhetsgrupper, enhetsfamiljer) | 12 |
| simulering (start, stopp, realtid, slumpfrö) | 10 |
| robot (joggning, rayCast) | 4 |
| komposition (`connectComponents`) | 1 |
| **summa** | **144** |

Följden för verktygsbygget: `app` är inte en domän man bygger *sist*. Den är
en yta man skär igenom nio gånger.

### 2.2 Konstanterna säger var den typade ytan slutar

709 konstanter. Uppdelade på form:

| Form | Antal | Vad de är |
|---|---|---|
| `VC_NAMN_VARDE` (understreck) | 558 | uppräkningsvärden till en parameter eller egenskap |
| `VC_NAMN` (ett ord) | 151 | **typnamn** till `createBehaviour`, `createFeature`, `createProperty`, `createLayoutItem` |

Av de 151 enordskonstanterna motsvarar **46** en typ som finns bland de 204.
**105 gör det inte.** Det är den viktigaste enskilda gränsen i hela API:t och
den återkommer i avsnitt 6: `VC_PHYSICSENTITY`, `VC_PHYSICSJOINTREVOLUTE`,
`VC_LIDARSENSOR`, `VC_RAYCASTSENSOR`, `VC_PARTICLESYSTEM`,
`VC_COMPONENTGRABBER`, `VC_CONVEYORTRANSPORTCONTROLLER`,
`VC_ARTICULATEDKINEMATICS`, `VC_EXTRUDE`, `VC_REVOLVE`, `VC_CONE` och 94 till
går att **skapa** men objektet man får tillbaka är typat som `vcBehaviour`
eller `vcFeature`. All inställning sker genom `getProperty()` och `Properties`.

Det betyder inte att de är oåtkomliga. Det betyder att verktyget för dem
måste vara **egenskapsdrivet**, och att `41_ogat_kontrakt.md`-disciplinen
gäller: verktyget får inte påstå att det satt något det inte kan läsa
tillbaka.

De största uppräkningsgrupperna, som är råvara för enum-fält i
verktygsschemat: `VC_STATEMENT` 80, `VC_MATERIAL` 31, `VC_MOTIONTARGET` 23,
`VC_PATH` 19, `VC_MENU` 18, `VC_MESSAGE` 18, `VC_LAYOUTITEM` 14,
`VC_SHIFTSTATE` 14, `VC_EVENT` 13.

`VC_STATEMENT`-gruppens 80 värden är hela satsvokabulären för både
robotprogram och processprogram. Ett enda verktyg (`list_statement_types`)
gör den sökbar; utan den kommer modellen att hitta på satsnamn.

### 2.3 Hjälpmodulerna är färdiga kodmönster

8 moduler, 223 medlemmar. De är inte en parallell yta utan **färdiga recept
ovanpå den**, och de är kodgenereringens genväg:

| Modul | Medlemmar | Vad den ger |
|---|---|---|
| `vcHelpers.Robot`, `vcHelpers.Robot2` | 55 var | `pick`, `place`, `pickFromPallet`, `placeInPattern`, `mountTool`, `graspComponent`, `linearMoveToMtx`, `RecordRoutine` |
| `vcHelpers.Selection` | 51 | `getSelectedComponents`, `getGivenComponentsNodes`, `filterTypes` — 51 sätt att svara på "vad är valt" |
| `vcHelpers.Application1` | 19 | dialoger, egenskapspaneler, förloppsmeddelanden |
| `vcHelpers.VcmFile` | 16 | komponentmetadata: `Author`, `Manufacturer`, `Tags`, `write` |
| `vcHelpers.Math` | 14 | trekantslösare `sasa`/`sssa`, `trapezoid`, `matrixExpr` |
| `vcHelpers.Output` | 12 | `info()`, `warning()`, `error()` bundna till egenskaper |
| `vcHelpers.Solver` | 1 | `findLocalMinimum` |

---

## 3. Verktygsformen som gäller i hela katalogen

Ärvd rakt ur `45_verktyg.md`, upprepad här för att tabellerna ska gå att läsa
utan att bläddra:

- `mode` = `data` när svaret kan ges av tjänsten utan att VC kör (index,
  katalog, kunskap, konstantlistor). `codegen` när det rör scenen.
- `effect` = `read` eller `write`. **`write` ⇒ godkännandekö** (I12), mekaniskt.
- Varje verktyg deklarerar `kraver`, alltså vilka ytor i `formaga.YTOR` det rör.
  Saknas ytan i den VC som kör exponeras verktyget inte alls (`36_versioner.md`).

Tumregel som håller genom alla 23 domäner: **läsverktyg är billiga, skrivverktyg
är dyra.** Ett läsverktyg behöver bara en JSON-form. Ett skrivverktyg behöver
dessutom en regelgrind och en verify-kontroll, för det kan ha ändrat scenen fel.

---

## 4. Domängenomgången

För varje domän: typerna som utgör den, vad ett bibliotek behöver, och
tabellen med föreslagna verktyg. Verktyg som **redan är byggda** står med
`✓`. Kolumnen "Bygger på" är kontrollerad mot indexet.

### 4.1 scen — 14 typer, 67 metoder, 121 egenskaper

Typer: `vcComponent`, `vcNode`, `vcLayout`, `vcLayoutItem`, `vcNodeList`,
`vcProperty`, `vcPropertyListValue`, `vcLayoutPropertyList`,
`vcLayoutSchemaPropertyList`, `vcLayoutPackFolder`, `vcPackFolder`,
`vcBehaviour`, `vcAnnotation`, `vc3DIcon`.

Byggt: 15 verktyg. Det som saknas är nodträdets **skrivsida** (skapa noder,
fästa dem, bygga om) och egenskapernas **metadata** (typ, kvantitet, gränser),
som är det modellen behöver för att inte skriva ett tal i fel enhet.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_components` ✓ | codegen | read | `vcApplication.Components` |
| `find_component` ✓ | codegen | read | `vcApplication.findComponent` |
| `component_info` ✓ | codegen | read | `vcComponent.Uri`, `Category`, `VCID` |
| `load_component` ✓ | codegen | write | `vcApplication.load` |
| `clone_component` ✓ | codegen | write | `vcComponent.clone` |
| `delete_component` ✓ | codegen | write | `vcApplication.deleteComponent` |
| `get_transform` ✓ | codegen | read | `vcNode.WorldPositionMatrix` |
| `set_transform` ✓ | codegen | write | `vcNode.PositionMatrix` |
| `get_bounds` ✓ | codegen | read | `vcNode.BoundCenter`, `BoundDiagonal` |
| `list_nodes` ✓ | codegen | read | `vcNode.Children` |
| `find_node` ✓ | codegen | read | `vcComponent.findNode` |
| `get_property` ✓ | codegen | read | `vcComponent.getProperty` |
| `set_property` ✓ | codegen | write | `vcComponent.getProperty`, `vcProperty.Value` |
| `list_properties` ✓ | codegen | read | `vcComponent.Properties` |
| `save_layout` ✓ | codegen | write | `vcApplication.save` |
| `create_component` | codegen | write | `vcApplication.createComponent`, `vcComponent.Name` |
| `clear_world` | codegen | write | `vcApplication.clearWorld`, `vcApplication.clearUndo` |
| `create_node` | codegen | write | `vcNode.createNode`, `VC_NODE_ADD_LAST_CHILD` |
| `attach_node` | codegen | write | `vcNode.attach`, `VC_NODE_INSERT_AFTER_SIBLING` |
| `node_tree` | codegen | read | `vcNode.Children`, `vcNode.Parent`, `vcNode.Type` |
| `set_visibility` | codegen | write | `vcNode.NodeVisible`, `vcNode.Visible` |
| `create_property` | codegen | write | `vcComponent.createProperty`, `VC_REAL`, `VC_STRING` |
| `delete_property` | codegen | write | `vcComponent.deleteProperty` |
| `property_info` | codegen | read | `vcProperty.Type`, `Quantity`, `Unit`, `MinValue`, `MaxValue`, `IsVisible` |
| `property_list_values` | codegen | read | `vcProperty.ListValues`, `ListValueCount`, `StepValues` |
| `list_behaviours` | codegen | read | `vcComponent.Behaviours`, `vcBehaviour.Type` |
| `find_behaviour_by_type` | codegen | read | `vcComponent.findBehavioursByType`, `getBehavioursByType` |
| `create_behaviour` | codegen | write | `vcNode.createBehaviour` |
| `delete_behaviour` | codegen | write | `vcBehaviour.delete`, `vcBehaviour.Enabled` |
| `local_to_world` | codegen | read | `vcComponent.localToWorld`, `worldToLocal` |
| `component_bom` | codegen | read | `vcComponent.BOM`, `BOMname`, `BOMdescription` |
| `lock_component` | codegen | write | `vcComponent.Locked` |
| `rebuild_component` | codegen | write | `vcComponent.rebuild`, `makeUnique`, `IsUnique` |
| `save_component` | codegen | write | `vcComponent.save`, `vcComponent.incrementRevision` |
| `list_layout_items` | codegen | read | `vcApplication.LayoutItems`, `findLayoutItem`, `vcLayoutItem.Type` |
| `create_annotation` | codegen | write | `vcApplication.createLayoutItem`, `vcAnnotation.Text`, `LockToNode` |

**15 byggda + 21 nya = 36.**

### 4.2 komposition — 3 typer, 9 metoder, 23 egenskaper

Typer: `vcSimInterface`, `vcSimInterfaceField`, `vcSimInterfaceSection`.

Byggt: 6 verktyg. Den lilla ytan bär den viktigaste invarianten i hela
projektet (I8: modellen anger relationer, aldrig koordinater). Det som saknas
är **skapandesidan**, som komponentbyggaren behöver.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_interfaces` ✓ | codegen | read | `vcComponent.Behaviours`, `vcSimInterface.Name` |
| `interface_info` ✓ | codegen | read | `vcSimInterface.Sections`, `IsAbstract` |
| `can_connect` ✓ | codegen | read | `vcSimInterface.canConnect` |
| `connect` ✓ | codegen | write | `vcSimInterface.connect` |
| `disconnect` ✓ | codegen | write | `vcSimInterface.disconnect` |
| `list_connections` ✓ | codegen | read | `vcSimInterface.ConnectedComponents` |
| `create_interface` | codegen | write | `vcNode.createBehaviour`, `VC_ONETOONEINTERFACE`, `VC_ONETOMANYINTERFACE` |
| `create_section` | codegen | write | `vcSimInterface.createSection`, `vcSimInterfaceSection.createField` |
| `list_sections` | codegen | read | `vcSimInterface.Sections`, `vcSimInterfaceSection.Fields`, `vcSimInterfaceField.Type` |
| `interface_tolerances` | codegen | write | `vcSimInterface.DistanceTolerance`, `AngleTolerance` |
| `connect_components` | codegen | write | `vcApplication.connectComponents` |
| `connection_graph` | codegen | read | `vcSimInterface.ConnectedSections`, `IsConnected`, `ConnectedFromSections` |

**6 byggda + 6 nya = 12.**

### 4.3 simulering — 2 typer, 23 metoder, 17 egenskaper, 15 händelser

Typer: `vcSimulation`, `vcScript`.

Liten yta, störst hävstång. Fyra av sex profiler kan inte arbeta utan den, och
**ögat kan inte provta utan den** (`40_ogat.md` läser `sim.SimTime`).

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `sim_state` | codegen | read | `vcSimulation.SimTime`, `IsRunning`, `SimSpeed` |
| `sim_run` | codegen | write | `vcSimulation.run` |
| `sim_halt` | codegen | write | `vcSimulation.halt` |
| `sim_reset` | codegen | write | `vcSimulation.reset` |
| `sim_continue` | codegen | write | `vcSimulation.continueRun` |
| `sim_speed` | codegen | write | `vcSimulation.SimSpeed`, `IsLooping` |
| `set_fast_scheduling` | codegen | write | `vcSimulation.setFastScheduling` |
| `sim_warmup` | codegen | write | `vcSimulation.SimWarmupTime`, `SimulationRunTime` |
| `sim_step` | codegen | write | `vcSimulation.update`, `vcApplication.render` |
| `sim_initial_state` | codegen | write | `vcSimulation.setInitialState`, `restoreInitialState` |
| `sim_autohalt` | codegen | write | `vcSimulation.autoHalt`, `vcSimulation.OnStartStop` |
| `install_script_behaviour` | codegen | write | `vcScript.Script`, `vcScript.OnSimulationUpdate`, `VC_PYTHONSCRIPT` |

**12 nya.**

### 4.4 mätning — 4 typer, 30 metoder, 35 egenskaper

Typer: `vcCollisionDetector`, `vcVolumeDetector`, `vcSweptVolume`, `vcDimension`.

Grindarnas råvara (`50_grindar.md`). Ingen dom kan fällas utan den här domänen.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `new_collision_detector` | codegen | write | `vcSimulation.newCollisionDetector`, `vcCollisionDetector.NodeListA`, `NodeListB` |
| `test_collision` | codegen | read | `vcCollisionDetector.testAllCollisions` |
| `test_one_collision` | codegen | read | `vcCollisionDetector.testOneCollision`, `testNodeCollisions` |
| `collision_hits` | codegen | read | `vcCollisionDetector.getHitNodeA`, `getHitNodeB`, `getHitFeatureA`, `HitCount` |
| `min_distance` | codegen | read | `vcCollisionDetector.testMinimumDistance`, `getMinimumDistanceDistance`, `getMinimumDistancePoint1`, `getMinimumDistancePoint2` |
| `bbox_collision` | codegen | read | `vcCollisionDetector.testAllBBoxCollisions`, `testBBoxComponentCollisions`, `getBBoxGeometry` |
| `collision_settings` | codegen | write | `vcCollisionDetector.Tolerance`, `StopOnCollision`, `IgnoreDifferentComponents`, `IgnoreClosestNodes` |
| `measure_distance` | codegen | read | `vcNode.measureDistance` |
| `path_distance` | codegen | read | `vcComponent.getPathDistance` |
| `ray_cast` | codegen | read | `vcApplication.rayCast` |
| `new_volume_detector` | codegen | write | `vcSimulation.newVolumeDetector`, `vcVolumeDetector.Corner1`, `Corner2`, `NodeList` |
| `volume_hits` | codegen | read | `vcVolumeDetector.testAllCollisions`, `getHitNode`, `HitCount` |
| `swept_volume` | codegen | write | `vcSweptVolume.begin`, `next`, `end`, `store`, `InputNodeList`, `Method`, `VC_SWEPT_LOFTING` |
| `create_dimension` | codegen | write | `vcApplication.createLayoutItem`, `VC_LAYOUTITEM_IT_DIMENSION`, `vcDimension.Node1`, `Node2`, `Dimension` |
| `frame_owner_node` | codegen | read | `vcApplication.detectFrameOwnerNode` |

**15 nya.**

### 4.5 signal — 10 typer, 27 metoder, 19 egenskaper

Typer: `vcSignal`, `vcBoolSignal`, `vcIntegerSignal`, `vcRealSignal`,
`vcStringSignal`, `vcMatrixSignal`, `vcComponentSignal`, `vcBooleanSignalMap`,
`vcIntergerSignalMap`, `vcStringSignalMap`.

Bärande för P3. Signalkartan (`vcBooleanSignalMap`) är dessutom **den enda
mekaniska källan till PLC-deklarationerna** (I10: modellen skriver aldrig
deklarationer — de genereras ur scenens signalkarta).

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_signals` | codegen | read | `vcComponent.Behaviours`, `vcSignal.Type`, `VC_BOOLEANSIGNAL`, `VC_REALSIGNAL` |
| `get_signal` | codegen | read | `vcBoolSignal.Value` |
| `set_signal` | codegen | write | `vcBoolSignal.Value` |
| `pulse_signal` | codegen | write | `vcBoolSignal.signal`, `vcBoolSignal.AutomaticReset` |
| `create_signal` | codegen | write | `vcNode.createBehaviour`, `VC_INTEGERSIGNAL`, `VC_STRINGSIGNAL` |
| `connect_signal` | codegen | write | `vcSignal.connect` |
| `disconnect_signal` | codegen | write | `vcSignal.disconnect` |
| `signal_connections` | codegen | read | `vcSignal.Connections` |
| `list_signal_maps` | codegen | read | `vcBooleanSignalMap.Ports`, `PortCount`, `VC_BOOLEANSIGNALMAP` |
| `signal_map_port` | codegen | write | `vcBooleanSignalMap.getPortName`, `setPortName`, `setPortSignal`, `addPort` |
| `signal_map_io` | codegen | read | `vcBooleanSignalMap.input`, `output`, `Direction`, `trySetDirection` |
| `signal_map_external` | codegen | read | `vcBooleanSignalMap.getConnectedExternalSignals`, `getAllConnectedPorts`, `getConnectedExternalPorts` |
| `watch_signal` | codegen | write | `vcSignal.OnValueChange`, `vcBooleanSignalMap.OnSignalTrigger` |

**13 nya.**

### 4.6 robot — 9 typer, 31 metoder, 56 egenskaper

Typer: `vcRobotController`, `vcServoController`, `vcJoint`, `vcDof`,
`vcToolContainer`, `vcToolFrame`, `vcBaseContainer`, `vcBaseFrame`, `vcJogInfo`.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_robots` | codegen | read | `vcComponent.findBehavioursByType`, `VC_ROBOTCONTROLLER` |
| `robot_info` | codegen | read | `vcRobotController.JointCount`, `Kinematics`, `FlangeNode`, `RootNode` |
| `get_joints` | codegen | read | `vcRobotController.Joints`, `getJointValue` |
| `joint_limits` | codegen | read | `vcJoint.MinValue`, `MaxValue`, `MaxSpeed`, `MaxAcceleration`, `MaxDeceleration` |
| `robot_limits` | codegen | read | `vcRobotController.MaxCartesianSpeed`, `MaxCartesianAccel`, `MaxAngularSpeed`, `MaxAngularAccel` |
| `set_robot_speed` | codegen | write | `vcRobotController.Speed`, `MaxCartesianSpeed` |
| `move_joint` | codegen | write | `vcServoController.moveJoint` |
| `move_joints` | codegen | write | `vcRobotController.moveImmediate` |
| `set_joint_target` | codegen | write | `vcRobotController.setJointTarget`, `getJointTarget` |
| `list_tools` | codegen | read | `vcRobotController.Tools`, `vcToolFrame.PositionMatrix`, `vcToolFrame.Node` |
| `add_tool` | codegen | write | `vcRobotController.addTool`, `vcToolContainer.addTool` |
| `remove_tool` | codegen | write | `vcRobotController.removeTool`, `vcToolContainer.removeTool` |
| `list_bases` | codegen | read | `vcRobotController.Bases`, `vcBaseFrame.PositionMatrix`, `vcBaseFrame.Node` |
| `add_base` | codegen | write | `vcRobotController.addBase`, `vcBaseContainer.addBase` |
| `flange_offset` | codegen | write | `vcRobotController.FlangeOffset`, `RootOffset` |
| `jog_robot` | codegen | write | `vcApplication.startJogging`, `doJogging`, `stopJogging` |
| `robot_heartbeat` | codegen | write | `vcRobotController.UseHeartbeat`, `HeartbeatTime`, `OnHeartbeat` |
| `create_joint` | codegen | write | `vcRobotController.createJoint`, `vcJoint.Type`, `VC_JOINTTYPE_ROTATIONAL` |
| `track_world_frame` | codegen | write | `vcRobotController.TrackWorldFrameMode`, `VC_TRACKWORLDFRAME_TRACKBASE` |

**19 nya.**

### 4.7 kinematik — 6 typer, 33 metoder, 59 egenskaper, 17 händelser

Typer: `vcKinObject`, `vcJacobian`, `vcPythonKinematics`,
`vcMotionInterpolator`, `vcMotionTarget`, `vcPositionFrame`.

Här ligger svaret på robotprogrammerarens viktigaste fråga: **når den dit,
och i vilken konfiguration?** `vcMotionTarget.getConfigWarnings` plus
`VC_MOTIONTARGET_KW_UNREACHABLE` / `_KW_SINGULAR` / `_KW_JOINTLIMIT` är den
mekaniska domen — ingen gissning behövs.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `create_target` | codegen | write | `vcRobotController.createTarget`, `vcMotionTarget.Target` |
| `target_info` | codegen | read | `vcMotionTarget.JointValues`, `RobotConfig`, `MotionType`, `ConfigCount` |
| `set_target_motion` | codegen | write | `vcMotionTarget.MotionType`, `VC_MOTIONTARGET_MT_LINEAR`, `AccuracyMethod`, `AccuracyValue` |
| `add_target` | codegen | write | `vcRobotController.addTarget`, `VC_MOTIONTARGET_TM_NORMAL` |
| `clear_targets` | codegen | write | `vcRobotController.clearTargets` |
| `reachability` | codegen | read | `vcMotionTarget.getConfigWarnings`, `getConfigWarning`, `VC_MOTIONTARGET_KW_UNREACHABLE` |
| `inverse_kin` | codegen | read | `vcKinObject.createJacobian`, `vcJacobian.inverse`, `vcJacobian.PositionalTolerance` |
| `forward_kin` | codegen | read | `vcPythonKinematics.forwardKin`, `vcKinObject.JointValues` |
| `solution_status` | codegen | read | `vcKinObject.Solutions`, `VC_SOLUTION_SINGULARITY`, `VC_SOLUTION_JOINT_LIMIT` |
| `config_names` | codegen | read | `vcMotionTarget.ConfigurationMode`, `vcHelpers.Robot.getConfigNames` |
| `move_to` | codegen | write | `vcRobotController.moveTo` |
| `move_rel_to` | codegen | write | `vcRobotController.moveRelTo` |
| `cycle_time` | codegen | read | `vcRobotController.calcMotionTime`, `vcMotionInterpolator.getCycleTimeAtTarget` |
| `interpolate_path` | codegen | read | `vcRobotController.createMotionInterpolator`, `vcMotionInterpolator.interpolate`, `Targets` |
| `target_frames` | codegen | read | `vcMotionTarget.getWorldToRobotTool`, `getRobotRootToRobotFlange`, `getSimWorldToRobotWorld` |
| `teach_position` | codegen | write | `vcPositionFrame.setJoints`, `PositionInWorld`, `Configuration` |

**16 nya.**

### 4.8 program — 19 typer, 79 metoder, 99 egenskaper

Typer: `vcProgram`, `vcRoutine`, `vcScope`, `vcStatement`, `vcMotionStatement`,
`vcPositionStatement`, `vcPathStatement`, `vcIfStatement`, `vcElseIfScope`,
`vcCaseScope`, `vcSwitchCaseStatement`, `vcScopeStatement`, `vcScriptStatement`,
`vcExecutor`, `vcRslProgramExecutor`, `vcRslRoutine`, `vcRslStatement`,
`vcRslMotionStatement`, `vcRslProcessStatement`.

Den domän där **genererad kod möter genererad kod**: agenten skriver Python som
bygger ett robotprogram. `VC_STATEMENT`-gruppens 80 värden är vokabulären.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_statement_types` | **data** | read | `constants.xml`, gruppen `VC_STATEMENT_LINMOTION` … (80 värden) |
| `list_programs` | codegen | read | `vcComponent.findBehavioursByType`, `VC_ROBOTEXECUTOR`, `vcExecutor.Program` |
| `program_info` | codegen | read | `vcProgram.Routines`, `MainRoutine`, `vcProgram.Name` |
| `add_routine` | codegen | write | `vcProgram.addRoutine` |
| `delete_routine` | codegen | write | `vcProgram.deleteRoutine`, `findRoutine` |
| `list_statements` | codegen | read | `vcRoutine.Statements`, `vcStatement.Type`, `vcStatement.Name` |
| `add_statement` | codegen | write | `vcRoutine.addStatement`, `VC_STATEMENT_DELAY`, `VC_STATEMENT_WAITSIGNAL` |
| `delete_statement` | codegen | write | `vcRoutine.deleteStatement`, `vcRoutine.clear` |
| `statement_property` | codegen | write | `vcStatement.getProperty`, `vcStatement.createProperty` |
| `add_motion_statement` | codegen | write | `vcRoutine.addStatement`, `VC_STATEMENT_LINMOTION`, `VC_STATEMENT_PTPMOTION` |
| `motion_positions` | codegen | read | `vcMotionStatement.Positions`, `createPosition`, `vcPositionFrame.PositionInReference` |
| `set_motion_frames` | codegen | write | `vcMotionStatement.Base`, `Tool`, `ExternalTCP` |
| `statement_cycle_time` | codegen | read | `vcMotionStatement.CycleTime` |
| `add_if_statement` | codegen | write | `vcIfStatement.ThenScope`, `ElseScope`, `addElseIfScope`, `Condition` |
| `add_switch_case` | codegen | write | `vcSwitchCaseStatement.addCase`, `vcCaseScope.CaseCondition`, `VC_STATEMENT_SWITCHCASE` |
| `scope_statements` | codegen | read | `vcScope.Statements`, `vcScope.addStatement`, `vcScopeStatement.Scope` |
| `path_statement` | codegen | write | `vcPathStatement.Positions`, `clearPositions`, `beginBatchUpdate`, `endBatchUpdate` |
| `path_schema` | codegen | write | `vcPathStatement.getSchemaValue`, `setSchemaValues`, `getSchemaSize`, `addSchemaProperties` |
| `executor_state` | codegen | read | `vcExecutor.CurrentStatement`, `IsLooping`, `IsEnabled` |
| `call_routine` | codegen | write | `vcExecutor.callRoutine`, `callStatement` |
| `executor_io` | codegen | write | `vcExecutor.DigitalInputSignals`, `DigitalOutputSignals`, `trySetDigitalInputSignals`, `setOutput` |
| `rsl_program` | codegen | write | `vcRslProgramExecutor.newProgram`, `createSubRoutine`, `vcRslRoutine.createStatement` |
| `rsl_statements` | codegen | read | `vcRslRoutine.Statements`, `vcRslMotionStatement.MotionType`, `vcRslStatement.Type` |
| `script_statement` | codegen | write | `vcScriptStatement.signalOut`, `vcScriptStatement.getExecutor`, `VC_STATEMENT_SCRIPT` |

**24 nya.**

### 4.9 rörelsebana — 8 typer, 18 metoder, 44 egenskaper

Typer: `vcMotionPath`, `vcPathObject`, `vcPathObjectNode`,
`vcPathObjectActionNode`, `vcPathObjectMotionNode`, `vcPathObjectParameterNode`,
`vcPathObjectReferenceNode`, `vcPathObjectSegment`.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_motion_paths` | codegen | read | `vcComponent.findBehavioursByType`, `VC_ONEWAYPATH`, `VC_TWOWAYPATH` |
| `path_info` | codegen | read | `vcMotionPath.PathLength`, `SegmentSize`, `Direction`, `PathAxis`, `VC_PATH_AXIS_AUTOMATIC` |
| `set_path_speed` | codegen | write | `vcMotionPath.Speed`, `Acceleration`, `Deceleration` |
| `path_capacity` | codegen | read | `vcMotionPath.Capacity`, `ComponentCount`, `SpaceUtilization`, `Accumulate` |
| `path_sensors` | codegen | read | `vcMotionPath.Sensors`, `vcProcessPointSensor.TriggerAt`, `ProcessAt` |
| `create_path_sensor` | codegen | write | `vcNode.createBehaviour`, `VC_COMPONENTPATHSENSOR`, `vcProcessPointSensor.BoolSignal` |
| `path_scheduling` | codegen | write | `vcMotionPath.FastScheduling`, `Interpolation`, `VC_INTERPOLATION_TRAVEL` |
| `create_path_object` | codegen | write | `vcApplication.createLayoutItem`, `VC_LAYOUTITEM_IT_PATHOBJECT`, `vcPathObject.createNode` |
| `path_object_nodes` | codegen | read | `vcPathObject.getNodes`, `vcPathObjectMotionNode.PositionMatrix`, `VC_PATHOBJECT_NT_MOTION` |
| `path_object_segments` | codegen | write | `vcPathObject.createSegment`, `vcPathObjectSegment.BeginLogicalDistance` |

**10 nya.**

### 4.10 flöde — 11 typer, 21 metoder, 38 egenskaper

Typer: `vcFlow`, `vcContainer`, `vcConnector`, `vcComponentCreator`,
`vcComponentFlowProxy`, `vcPatternContainer`, `vcRoutingRule`, `vcTransport`,
`vcTransportController`, `vcInterpolatingTransportController`,
`vcPythonTransportController`.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_flow_behaviours` | codegen | read | `vcComponent.Behaviours`, `vcFlow.Connectors`, `VC_COMPONENTCREATOR` |
| `container_state` | codegen | read | `vcContainer.Components`, `Capacity`, `ComponentCount`, `CapacityAvailable` |
| `set_container_capacity` | codegen | write | `vcContainer.Capacity`, `vcContainer.ContentVisible` |
| `list_connectors` | codegen | read | `vcFlow.Connectors`, `vcConnector.Name`, `vcConnector.Connection` |
| `connect_flow` | codegen | write | `vcConnector.connect` |
| `test_capacity` | codegen | read | `vcConnector.testCapacity`, `testConnectedCapacity` |
| `transfer_component` | codegen | write | `vcComponent.transfer`, `transferNonBlocking` |
| `component_creator` | codegen | write | `vcComponentCreator.create`, `Interval`, `Limit`, `TemplateComponent`, `PartPooling` |
| `flow_proxy` | codegen | write | `vcComponentFlowProxy.createConnector`, `connectInternally`, `getInternalConnector` |
| `routing_rule` | codegen | write | `vcRoutingRule.setTarget`, `processRoute`, `RuleComponent`, `VC_ROUTING_OWNER` |
| `transport_controller_info` | codegen | read | `vcTransportController.Type`, `VC_CONVEYORTRANSPORTCONTROLLER`, `vcInterpolatingTransportController.Components` |
| `python_transport_controller` | codegen | write | `vcPythonTransportController.OnBeginTransport`, `workDone`, `WorkPositionMatrix` |
| `pattern_container` | codegen | read | `vcPatternContainer.Components`, `vcPatternContainer.fill` |
| `transport_info` | codegen | read | `vcComponent.getTransportInfo`, `vcTransport.setTargetInfo`, `VC_TRANSPORTOUTTYPE_TRANSPORTNODE` |

**14 nya.**

### 4.11 transportsystem — 5 typer, 14 metoder, 29 egenskaper

Typer: `vcTransportSystem`, `vcTransportNode`, `vcTransportLink`,
`vcTransportSolution`, `vcTransportTarget`.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_transport_nodes` | codegen | read | `vcTransportSystem.Nodes`, `vcTransportNode.Name`, `Frame` |
| `list_transport_links` | codegen | read | `vcTransportSystem.Links`, `vcTransportLink.Source`, `Destination`, `Implementer` |
| `create_transport_link` | codegen | write | `vcTransportSystem.createTransportLink` |
| `delete_transport_link` | codegen | write | `vcTransportSystem.deleteTransportLink` |
| `find_solution` | codegen | read | `vcTransportSystem.findSolution`, `vcTransportSolution.Links`, `getNextLink` |
| `links_between` | codegen | read | `vcTransportSystem.findAllLinksBetweenNodeSets` |
| `transport_node_info` | codegen | read | `vcTransportNode.TransportLinks`, `ProcessExecutor`, `TriggerAt`, `ResetAt` |
| `transport_target` | codegen | write | `vcTransportNode.createTransportTarget`, `vcTransportTarget.ProductPosition` |
| `begin_transport_out` | codegen | write | `vcTransportNode.beginTransportOut` |
| `transport_controllers` | codegen | read | `vcTransportSystem.Controllers`, `vcProcessController.TransportSystem` |

**10 nya.**

### 4.12 fordon — 1 typ, 20 metoder, 9 egenskaper

Typ: `vcSimVehicle`. En enda typ, men 20 metoder: hela AGV-planeringen.
Anmärkningsvärt är att den bär **förhandsberäkning** — `calculatePositionAt`,
`calculateSpeedAt`, `calculateDecisionTimeToStopAt` — alltså svar på "var är
den om 4 sekunder" **utan att köra simuleringen**. Det är ovanligt i det här
API:t och värt ett eget verktyg.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_vehicles` | codegen | read | `vcComponent.findBehavioursByType`, `VC_VEHICLE`, `vcSimVehicle.Name` |
| `vehicle_limits` | codegen | write | `vcSimVehicle.MaxSpeed`, `Acceleration`, `Deceleration`, `DecisionTime` |
| `add_control_point` | codegen | write | `vcSimVehicle.addControlPoint`, `addOrientationPoint` |
| `vehicle_plan` | codegen | read | `vcSimVehicle.PathLength`, `TotalTime`, `getControlPointDistance` |
| `replan` | codegen | write | `vcSimVehicle.rePlan`, `clearMove`, `clearPassedPoints` |
| `vehicle_position_at` | codegen | read | `vcSimVehicle.calculatePositionAt`, `calculateSpeedAt`, `calculateTravelWithTime` |
| `stop_distance` | codegen | read | `vcSimVehicle.calculateDecisionTimeToStopAt`, `calculateFinishedTimeToStopAt`, `resetStopAtDistance` |
| `wagons` | codegen | write | `vcSimVehicle.attachWagonAtTheEnd`, `detachAllWagons` |
| `rotate_in_place` | codegen | write | `vcSimVehicle.rotateInPlace`, `offsetPath`, `calculateOffsetPathLength` |

**9 nya.**
### 4.13 process — 24 typer, 84 metoder, 94 egenskaper, 38 händelser

Typer: `vcProcessController`, `vcProcessExecutor`, `vcProcessManager`,
`vcProcessGroup`, `vcProcessRoutine`, `vcProcessSequence`, `vcProcessSequence2`,
`vcProcessFlowStep`, `vcProcessFlowGroup`, `vcProcessFlowGroupManager`,
`vcProcessFlowState`, `vcProcessFlowTable`, `vcProcessFlowTable2`,
`vcProcessIfStatement`, `vcProcessWhileStatement`, `vcProcessPointSensor`,
`vcFlowStepProcessConnfiguration`, `vcSequenceProcessConfiguration`,
`vcNextProcessFlowInfo`, `vcFeedOptionFlowInfo`, `vcPythonProcessHandler`,
`vcRslProcessHandler`, `vcActionContainer`, `vcAction`.

**Flest typer av alla domäner och flest händelser (38).** Det är Process
Modeling — VC:s eget språk för vad som händer med en produkt. Två generationer
finns parallellt i API:t (`vcProcessFlowTable` / `vcProcessSequence` mot
`vcProcessFlowTable2` / `vcProcessSequence2`); verktygen måste läsa vilken som
är i bruk, inte anta.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `process_controller` | codegen | read | `vcProcessController.ProcessManager`, `FlowGroupManager`, `ProductTypeManager`, `TransportSystem` |
| `list_process_groups` | codegen | read | `vcProcessManager.ProcessGroups`, `vcProcessGroup.ProcessId`, `Implementations` |
| `find_process_group` | codegen | read | `vcProcessManager.findProcessGroup`, `changeGroupId` |
| `list_flow_groups` | codegen | read | `vcProcessFlowGroupManager.Groups`, `vcProcessFlowGroup.ProductTypes` |
| `create_flow_group` | codegen | write | `vcProcessFlowGroupManager.createGroup`, `deleteGroup`, `findGroup` |
| `move_product_type` | codegen | write | `vcProcessFlowGroupManager.moveProductType` |
| `list_sequences` | codegen | read | `vcProcessFlowTable.Sequences`, `vcProcessSequence.ProcessGroups`, `TargetGroup` |
| `create_sequence` | codegen | write | `vcProcessFlowTable.createSequence`, `copySequenceFrom`, `deleteSequence` |
| `sequence_steps` | codegen | write | `vcProcessSequence.addProcessGroup`, `insertProcessGroup`, `removeProcessGroup`, `setProcessGroup` |
| `flow_table2` | codegen | read | `vcProcessFlowTable2.Sequences`, `vcProcessSequence2.FlowSteps`, `getNextProcessOptions` |
| `create_flow_step` | codegen | write | `vcProcessSequence2.createStepFrom`, `vcProcessFlowStep.ProcessMode`, `VC_PROCESSMODE_ALLINANYORDER` |
| `flow_step_config` | codegen | write | `vcProcessFlowStep.ProcessConfigurations`, `vcFlowStepProcessConnfiguration.IsOptional`, `vcSequenceProcessConfiguration.MaxVisitCount` |
| `list_processes` | codegen | read | `vcProcessExecutor.Processes`, `vcProcessExecutor.ProcessHandlers` |
| `add_process` | codegen | write | `vcProcessExecutor.addProcess`, `deleteProcess` |
| `process_routine` | codegen | write | `vcProcessRoutine.addStatement`, `vcProcessRoutine.Statements`, `Requirements` |
| `process_statement_flow` | codegen | write | `vcProcessIfStatement.Condition`, `vcProcessWhileStatement.Scope`, `VC_STATEMENT_PROCESSIF` |
| `process_transport_statements` | codegen | write | `vcProcessRoutine.addStatement`, `VC_STATEMENT_TRANSPORTIN`, `VC_STATEMENT_TRANSPORTOUT`, `VC_STATEMENT_WORK` |
| `process_state` | codegen | read | `vcProduct.CurrentProcessFlowState`, `vcProcessFlowState.FlowStep`, `vcProcessFlowState.Routine` |
| `process_point_sensor` | codegen | write | `vcProcessPointSensor.ProcessAt`, `TriggerAt`, `setValue`, `VC_PROCESSPOINT_STOP_COMPONENT` |
| `process_failure` | codegen | write | `vcProcessPointSensor.startFailure`, `stopFailure` |
| `python_process_handler` | codegen | write | `vcPythonProcessHandler.Script`, `OnStatementExecute`, `triggerCondition` |
| `list_actions` | codegen | read | `vcActionContainer.Actions`, `vcAction.Name`, `vcAction.Receiver` |
| `reserve_resource` | codegen | write | `vcActionContainer.reserve`, `release`, `getResources` |
| `send_action` | codegen | write | `vcActionContainer.createAction`, `vcAction.send`, `vcAction.Message` |

**24 nya.**

### 4.14 produkt — 20 typer, 49 metoder, 80 egenskaper

Typer: `vcProduct`, `vcProductType`, `vcProductTypeManager`, `vcProductFilter`,
`vcProductTypeFilter`, `vcConfigurableProductTypeFilter`, `vcProductCreator`,
`vcProductCreatorBatchMode`, `vcProductCreatorDistributionMode`,
`vcProductCreatorFeedBatch`, `vcProductCreatorSingleMode`,
`vcProductCreatorTableMode`, `vcProductCreatorTableRow`,
`vcDistributionModeProductLineEntry`, `vcProductFeed`, `vcProductFeedInfo`,
`vcProductNeed`, `vcProductNeedInfo`, `vcProductMatcher`,
`vcProductNeedFeedMatch`.

Fyra inflödeslägen med var sin typ (enkel, batch, fördelning, tabell). Ett
verktyg per läge, inte ett generellt — parametrarna är olika storheter och
`en-parameter-som-bär-två-storheter`-fällan är just den här.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_product_types` | codegen | read | `vcProductTypeManager.ProductTypes`, `vcProductType.Name`, `ComponentUri` |
| `create_product_type` | codegen | write | `vcProductTypeManager.createProductType` |
| `delete_product_type` | codegen | write | `vcProductTypeManager.deleteProductType`, `findProductType` |
| `product_type_properties` | codegen | write | `vcProductType.ProductProperties`, `createProductProperty`, `ComponentProperties`, `createComponentProperty` |
| `product_type_origin` | codegen | write | `vcProductType.OriginFrame`, `vcProductType.FlowGroup` |
| `list_products` | codegen | read | `vcProduct.ProductType`, `vcProduct.Component`, `vcProduct.WorldPositionMatrix` |
| `product_state` | codegen | read | `vcProduct.CurrentProcessFlowState`, `LastEnteredNode`, `TransportSolution` |
| `change_product_type` | codegen | write | `vcProduct.changeType`, `VC_STATEMENT_CHANGEPRODUCTTYPE` |
| `product_creator_mode` | codegen | write | `vcProductCreator.FeedMode`, `ApplyProductTypeOrigin`, `VC_DISTRIBUTION_FEED_MODE` |
| `single_feed` | codegen | write | `vcProductCreatorSingleMode.Part`, `Interval`, `Limit` |
| `batch_feed` | codegen | write | `vcProductCreatorBatchMode.createBatch`, `BatchInterval`, `Loop`, `ProductBatches` |
| `distribution_feed` | codegen | write | `vcProductCreatorDistributionMode.addProductEntry`, `RandomStream`, `vcDistributionModeProductLineEntry.Probability` |
| `table_feed` | codegen | write | `vcProductCreatorTableMode.addRow`, `readRowsFromFile`, `File`, `RowCount` |
| `feed_batch` | codegen | write | `vcProductCreatorFeedBatch.Part`, `Interval`, `Limit` |
| `product_filter` | codegen | read | `vcProductTypeFilter.AcceptAllProductTypes`, `vcProductFilter.acceptsProduct` |
| `matcher_state` | codegen | read | `vcProductMatcher.PendingFeeds`, `PendingNeeds`, `PendingFeedsCount` |
| `add_need` | codegen | write | `vcProductMatcher.addNeed`, `vcProductNeed.TargetNode`, `NeedMatchType`, `VC_MATCH_MODE_INDEPENDENT` |
| `add_feed` | codegen | write | `vcProductMatcher.addFeed`, `vcProductFeed.SourceNode`, `NextProcessGroupId` |
| `match_state` | codegen | read | `vcProductNeedFeedMatch.State`, `MatchedFeed`, `MatchedNeed`, `VC_MATCH_STATE_FINALIZED` |

**19 nya.**

### 4.15 montering — 6 typer, 25 metoder, 25 egenskaper

Typer: `vcAssemblyProductType`, `vcAssemblyStep`, `vcAssemblyPattern`,
`vcAssemblyPatternItem`, `vcAssemblyPatternManager`, `vcAssemblyPatternSlot`.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_assembly_steps` | codegen | read | `vcAssemblyProductType.AssemblySteps`, `RootStep`, `vcAssemblyStep.ChildSteps` |
| `create_assembly_step` | codegen | write | `vcAssemblyProductType.createStepTo`, `cloneStepFrom` |
| `move_assembly_step` | codegen | write | `vcAssemblyProductType.moveStepTo`, `deleteStep`, `vcAssemblyStep.moveChildStep` |
| `step_frames` | codegen | write | `vcAssemblyStep.RelativeFrame`, `AbsoluteFrame` |
| `step_parameters` | codegen | write | `vcAssemblyStep.createProcessParameter`, `getProcessParameter`, `ProcessParameters` |
| `list_patterns` | codegen | read | `vcAssemblyPatternManager.Patterns`, `vcAssemblyPattern.Slots` |
| `create_pattern` | codegen | write | `vcAssemblyPatternManager.createPattern`, `clonePattern`, `findPattern`, `vcAssemblyPattern.createSlot` |
| `pattern_slot` | codegen | write | `vcAssemblyPatternSlot.Position`, `Item`, `OrderIndex`, `vcAssemblyPatternItem.DefaultProductType` |
| `assembly_step_check` | codegen | read | `vcAssemblyProductType.canBeAddedTo`, `canBeMovedTo`, `VC_ASSEMBLYSTEPSELECTIONMODE_FIRSTEMPTY` |

**9 nya.**

### 4.16 statistik — 7 typer, 65 metoder, 49 egenskaper

Typer: `vcStatistics`, `vcStatisticsChart`, `vcStatisticsDashboard`,
`vcStatisticsManager`, `vcStatisticsSeries`, `vcStatisticsTab`, `vcReport`.

`vcStatistics` ensam bär 53 metoder. Det är analytikerns hela svarsyta, och
den delar sig i tre storheter som **aldrig får blandas i ett verktyg**:
tillståndstider (`getPercentage`), delräkning (`Parts*`) och
komponentgenomströmning (`Components*`). De mäter olika saker och har olika
nollpunkt.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_statistics` | codegen | read | `vcComponent.findBehavioursByType`, `VC_STATISTICS`, `vcStatistics.Name` |
| `station_stats` | codegen | read | `vcStatistics.ComponentsArrived`, `ComponentsDeparted`, `ComponentsAverageTime`, `ComponentsCurrent` |
| `state_percentages` | codegen | read | `vcStatistics.getPercentage`, `Utilization`, `BusyPercentage`, `IdlePercentage`, `BlockedPercentage` |
| `state_times` | codegen | read | `vcStatistics.getTime`, `TotalStateTime`, `AverageActivePeriodTime` |
| `interval_stats` | codegen | read | `vcStatistics.IntervalUtilization`, `IntervalBusyPercentage`, `getIntervalPercentage` |
| `system_states` | codegen | read | `vcStatistics.SystemStates`, `getSystemPercentage`, `getSystemTime`, `VC_STATISTICS_BLOCKED` |
| `part_stats` | codegen | read | `vcStatistics.PartsEntered`, `PartsExited`, `PartsAverageTime`, `PartsMaxCount`, `PartsUtilization` |
| `warmup` | codegen | write | `vcStatistics.warmupCompleted`, `vcSimulation.SimWarmupTime`, `VC_STATISTICS_WARMUP` |
| `sampling_interval` | codegen | write | `vcStatisticsManager.SamplingInterval`, `vcStatisticsDashboard.StatisticsInterval` |
| `list_dashboards` | codegen | read | `vcApplication.Dashboard`, `vcStatisticsDashboard.Tabs`, `vcStatisticsTab.Charts` |
| `create_tab` | codegen | write | `vcStatisticsDashboard.createTab`, `deleteTab` |
| `create_chart` | codegen | write | `vcStatisticsTab.createChart`, `vcStatisticsChart.ChartType`, `VC_CHARTTYPE_BAR` |
| `add_series` | codegen | write | `vcStatisticsChart.addSeries`, `vcStatisticsSeries.Expression`, `Property`, `Sources` |
| `chart_data` | codegen | read | `vcStatisticsChart.DataRows`, `SamplingInterval`, `RecordAccumulatedValues` |
| `clear_chart` | codegen | write | `vcStatisticsChart.clearData`, `clearSeries`, `deleteSeries` |
| `create_report` | codegen | write | `vcApplication.createLayoutItem`, `VC_LAYOUTITEM_IT_REPORTCHART`, `vcReport.publish`, `VC_REPORT_GANTTCHART` |
| `flow_events` | codegen | write | `vcStatistics.OnFlowChange`, `OnStateChange`, `flowEnter`, `flowLeave` |

**17 nya.**

### 4.17 geometri — 23 typer, 145 metoder, 132 egenskaper

Typer: `vcGeometrySet`, `vcGeometryContainer`, `vcTriangleSet`, `vcPolygonSet`,
`vcPolygon`, `vcPolygonPoint`, `vcPointSet`, `vcPoint`, `vcLineSet`,
`vcCompactLineSet`, `vcLine`, `vcLinePoint`, `vcText2DSet`, `vcText3DSet`,
`vcFrameSet`, `vcFrameSetVisualization`, `vcTopology`, `vcCurveData`, `vcEdge`,
`vcPrimative`, `vcFeature`, `vcFrameFeature`, `vcGeometryFeature`.

**Störst av alla domäner.** `vcTopology` ensam bär 48 metoder — en riktig
BREP-yta med ytor, kurvor, NURBS-kontrollpunkter och skärningar. Det gör
mycket möjligt som inte syns i marknadsföringen: mäta en yta, projicera en
kurva på den, hitta skärningen mellan två ytor.

Varning som hör till domänen: `vcCurveData`:s 19 medlemmar står i källan som
*egenskaper* trots att de bär parameterlistor. Indexet räknar dem som källan
gör och lägger parameterlistan i signaturen
(`statistik()["egenskaper_med_parameterlista"]` = 34). Ett verktyg här får
inte anta att `getCurveLength` går att läsa som ett attribut.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_features` | codegen | read | `vcComponent.RootFeature`, `vcFeature.Children`, `vcFeature.Type` |
| `create_feature` | codegen | write | `vcFeature.createFeature`, `VC_EXTRUDE`, `VC_REVOLVE`, `VC_CONE`, `VC_CYLINDER` |
| `feature_transform` | codegen | write | `vcFeature.PositionMatrix`, `NodePositionMatrix`, `vcFrameFeature.FramePositionMatrix` |
| `rebuild_feature` | codegen | write | `vcFeature.rebuild`, `collapse`, `attach`, `clone` |
| `geometry_info` | codegen | read | `vcGeometryFeature.Geometry`, `vcGeometryContainer.GeometrySets`, `GeometrySetCount` |
| `tesselation` | codegen | write | `vcGeometryFeature.TesselationQuality`, `CreaseAngle`, `ShowBackfaces` |
| `list_geometry_sets` | codegen | read | `vcGeometryContainer.getGeometrySet`, `vcGeometrySet.Type`, `Material`, `BoundCenter` |
| `triangle_stats` | codegen | read | `vcTriangleSet.TriangleCount`, `PointCount`, `getTriangle`, `getPointPositions` |
| `mesh_decimate` | codegen | write | `vcTriangleSet.decimate`, `mergePoints`, `subdivide` |
| `convex_hull` | codegen | write | `vcTriangleSet.convexHull`, `vcTriangleSet.decompose`, `VC_CONVEXHULL` |
| `closest_point` | codegen | read | `vcTriangleSet.getClosestPointAndNormal`, `getPointIndexesWithin` |
| `create_triangle_set` | codegen | write | `vcGeometryContainer.createGeometrySet`, `VC_TRIANGLESET`, `vcTriangleSet.addPoint`, `addTriangle` |
| `polygon_set` | codegen | write | `vcPolygonSet.createPolygon`, `triangulate`, `filterDuplicatePolygons` |
| `point_set` | codegen | write | `vcPointSet.addPoint`, `updatePointColor`, `PointSize` |
| `line_set` | codegen | write | `vcLineSet.createLine`, `vcCompactLineSet.addLine`, `vcLineSet.LineWidth` |
| `text_set` | codegen | write | `vcText3DSet.Text`, `vcText2DSet.getTextWidth`, `vcText2DSet.OffsetX` |
| `frame_set` | codegen | write | `vcFrameSet.createFrame`, `setFrame`, `getFrame`, `FrameCount` |
| `frame_visualization` | codegen | write | `vcFrameSetVisualization.FramesVisible`, `FrameDisplayMode`, `NamesVisible` |
| `topology_info` | codegen | read | `vcTopology.brepAvailable`, `FaceCount`, `CurveCount`, `getFaceType` |
| `face_geometry` | codegen | read | `vcTopology.getFaceNormal`, `getFacePoint`, `getFaceBound`, `isFaceLinear` |
| `curve_geometry` | codegen | read | `vcTopology.getCurveLength`, `getCurvePositions`, `isCurveCircular` |
| `surface_intersections` | codegen | read | `vcTopology.getSurfaceIntersections`, `getFacePlaneIntersections`, `projectCurve` |
| `create_face` | codegen | write | `vcTopology.createPlanarFace`, `createNurbsFace`, `createCurveLoop`, `trimFace` |
| `curve_data` | codegen | read | `vcCurveData.getCurveLength`, `getCurvePositions`, `createCurvePolyLine` |
| `physics_collider` | codegen | write | `vcFeature.PhysicsCollider`, `VC_PHYSICSCOLLIDER_BOX`, `VC_PHYSICSCOLLIDER_PRECISE` |

**25 nya.**

### 4.18 vy — 3 typer, 2 metoder, 18 egenskaper

Typer: `vcCamera`, `vcView`, `vcViewAnimation`. Plus 27 `vcApplication`-medlemmar
(avsnitt 2.1) — den verkliga ytan är alltså mycket större än de tre typernas.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `get_camera` | codegen | read | `vcApplication.findCamera`, `vcCamera.Eye`, `Coi`, `Matrix` |
| `set_camera` | codegen | write | `vcCamera.Matrix`, `Eye`, `Coi`, `ClipNear`, `ClipFar` |
| `list_views` | codegen | read | `vcApplication.Views`, `vcView.CameraMatrix`, `CameraFovy` |
| `create_view` | codegen | write | `vcApplication.createView`, `vcView.CameraMatrix`, `CameraIsOrtho` |
| `use_view` | codegen | write | `vcApplication.useView`, `findView`, `deleteView` |
| `shading_mode` | codegen | write | `vcView.ShadingRender`, `ShadingEdge`, `vcView.Flags` |
| `frame_grab` | codegen | write | `vcApplication.beginFrameGrab`, `executeFrameGrab`, `endFrameGrab` |
| `pixel_to_ray` | codegen | read | `vcCamera.getRay`, `vcApplication.rayCast` |
| `clip_plane` | codegen | write | `vcApplication.setClipPlane`, `setClipPlaneEnabled` |
| `record_video` | codegen | write | `vcApplication.RecordScreen`, `RecordingFileName`, `RecordingFrameRate`, `VC_RECORDER_VIDEO` |
| `record_pdf` | codegen | write | `vcApplication.PdfRecord`, `PdfFileName`, `PdfStepSize`, `VC_RECORDER_PDF` |
| `view_animation` | codegen | write | `vcViewAnimation.Program`, `getProgram`, `VC_LAYOUTITEM_IT_VIEWANIMATION` |

**12 nya.**

### 4.19 utseende — 4 typer, 0 metoder, 34 egenskaper

Typer: `vcMaterial`, `vcLight`, `vcLayer`, `vcBitMap`.

Den enda domänen med **noll egna metoder**. Allt görs genom
`vcApplication`-medlemmarna (12 st) och egenskapsskrivningar.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_materials` | codegen | read | `vcApplication.Materials`, `vcMaterial.Name`, `Diffuse` |
| `create_material` | codegen | write | `vcApplication.createMaterial`, `addMaterial`, `vcMaterial.Diffuse`, `Ambient`, `Specular` |
| `set_node_material` | codegen | write | `vcNode.NodeMaterial`, `vcComponent.Material`, `MaterialInheritance` |
| `material_opacity` | codegen | write | `vcMaterial.Opacity`, `OpacityType`, `Shininess`, `VC_MATERIAL_TRANSPARENCY_CONSTANT` |
| `material_texture` | codegen | write | `vcMaterial.Texture`, `TextureMapping`, `vcApplication.loadBitmap` |
| `list_layers` | codegen | read | `vcApplication.Layers`, `vcLayer.Name`, `vcLayer.Visibility` |
| `create_layer` | codegen | write | `vcApplication.createLayer`, `findLayer`, `deleteLayer` |
| `assign_layer` | codegen | write | `vcGeometrySet.Layer`, `vc3DIcon.Layer` |
| `list_lights` | codegen | read | `vcApplication.Lights`, `vcLight.Type`, `Position`, `Intensity` |
| `create_light` | codegen | write | `vcApplication.createLight`, `vcLight.SpotAngle`, `Direction`, `VC_LIGHT_SPOT` |
| `shadows` | codegen | write | `vcApplication.RenderShadows`, `vcMaterial.RenderOrder` |

**11 nya.**

### 4.20 matematik — 2 typer, 38 metoder

Typer: `vcMatrix` (29 metoder), `vcVector` (9).

Ingen scenåtkomst alls — ren räkning. Ändå bärande, för I8 säger att modellen
anger relationer och inte koordinater: de här verktygen finns för att **räkna
om det VC svarat**, inte för att sätta poser för hand.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `make_matrix` | codegen | read | `vcMatrix.new`, `setWPR`, `setEuler`, `setQuaternion` |
| `matrix_decompose` | codegen | read | `vcMatrix.getWPR`, `getEuler`, `getQuaternion`, `getAxisAngle`, `vcMatrix.P` |
| `matrix_transform` | codegen | read | `vcMatrix.translateRel`, `translateAbs`, `rotateRelZ`, `rotateAbsV` |
| `matrix_invert` | codegen | read | `vcMatrix.invert`, `identity`, `uniform` |
| `matrix_scale` | codegen | read | `vcMatrix.scaleAbs`, `scaleRel` |
| `vector_ops` | codegen | read | `vcVector.new`, `vcVector.X`, `length`, `normalize`, `angle` |
| `relative_pose` | codegen | read | `vcComponent.worldToLocal`, `localToWorld`, `vcNode.InverseWorldPositionMatrix` |
| `helper_math` | codegen | read | `vcHelpers.Math.sasa`, `sssa`, `trapezoid`, `matrixExpr` |

**8 nya.**

### 4.21 enheter — 5 typer, 14 metoder, 26 egenskaper

Typer: `vcScalarQuantity`, `vcVectorQuantity`, `vcUnit`, `vcUnitFamily`,
`vcUnitGroup`.

Liten domän med oproportionerlig betydelse: den är **skyddet mot att modellen
skriver ett tal i fel enhet**. `vcProperty.Quantity` och `vcProperty.Unit`
säger vad ett egenskapsvärde faktiskt betyder, och utan dem är varje
`set_property` ett tal utan storhet.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_quantities` | codegen | read | `vcApplication.Quantities`, `vcScalarQuantity.FullName`, `Category` |
| `create_quantity` | codegen | write | `vcApplication.createQuantity`, `vcScalarQuantity.createChildQuantity` |
| `list_unit_groups` | codegen | read | `vcApplication.UnitGroups`, `vcUnitGroup.Units`, `vcUnit.Suffix`, `vcUnit.Factor` |
| `convert_unit` | codegen | read | `vcUnit.convertToCanonical`, `convertFromCanonical`, `getRelativeMagnitude` |
| `property_unit` | codegen | write | `vcProperty.Quantity`, `vcProperty.Unit`, `setUnitMagnitude`, `Magnitude` |
| `unit_family` | codegen | write | `vcApplication.createUnitFamily`, `vcUnitFamily.addGroup`, `containsGroup` |

**6 nya.**

### 4.22 ui — 10 typer, 81 metoder, 83 egenskaper

Typer: `vcCommand`, `vcSelectCommand`, `vcSnapCommand`, `vcTopologyPick`,
`vcTranslateCommand`, `vcInteractiveCommand`, `vcCommandEvent`,
`vcCommandPanelAction`, `vcSelection`, `vcSelectionManager`.

Två saker i en. Det ena är **urvalet** — vad användaren har markerat — och det
är agentens billigaste sätt att veta vad frågan handlar om. Det andra är
**kommandolagret**: `vcApplication.findCommand` plus `vcCommand.execute` når
programmets egna kommandon från Python, vilket är den enda vägen till några
funktioner som annars vore rent manuella.

Kolumnen "Bygger på" här bär en varning: 18 av `vcCommand`:s 68 metoder är
märkta `(Deprecated)` redan i källan. Verktyg får inte byggas på dem.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_commands` | codegen | read | `vcApplication.getCommands`, `findCommand`, `vcCommand.Name`, `IsModelingCommand` |
| `execute_command` | codegen | write | `vcCommand.execute`, `vcCommand.Properties`, `vcCommand.getProperty` |
| `load_command` | codegen | write | `vcApplication.loadCommand`, `cancelCommand`, `deleteCommand` |
| `get_selection` | codegen | read | `vcApplication.getSelection`, `vcSelection.Objects`, `getItem`, `Count`, `VC_SELECTION_COMPONENT` |
| `set_selection` | codegen | write | `vcSelection.addItem`, `removeItem`, `clear`, `beginUpdate`, `endUpdate` |
| `selection_helpers` | codegen | read | `vcHelpers.Selection.getSelectedComponents`, `getSelectedNodes`, `filterTypes` |
| `message_box` | codegen | write | `vcApplication.messageBox`, `VC_MESSAGE_TYPE_WARNING`, `VC_MESSAGE_BUTTONS_OKCANCEL` |
| `app_messages` | codegen | read | `vcApplication.getMessages`, `clearMessages`, `vcHelpers.Output.info()` |
| `progress` | codegen | write | `vcApplication.ProgressStatus`, `ProgressValue`, `vcHelpers.Application1.progressMessage` |
| `snap_target` | codegen | read | `vcSnapCommand.TargetMatrix`, `TargetNode`, `SnapOnFrame`, `TargetAvailable` |
| `topology_pick` | codegen | read | `vcTopologyPick.TargetCurves`, `TargetSurfaceIndex`, `TargetPosition` |
| `workflow` | codegen | write | `vcApplication.Workflow`, `vcWorkflow.createConfig`, `vcWorkflowConfig.addItem`, `vcWorkflowItem.Action` |

**12 nya.**

### 4.23 app — 8 typer, 91 metoder, 67 egenskaper

Typer: `vcApplication`, `vcContext`, `vcAuthorContext`, `vcTeachContext`,
`vcEventReturnData`, `vcWorkflow`, `vcWorkflowConfig`, `vcWorkflowItem`.

Kontexterna (`VC_CONTEXT_TEACH`, `_AUTHOR`, `_PROCESS`, `_DRAWING`,
`_CONFIGURE`) är programmets lägen. `vcTeachContext.ActiveRobot` och
`ActiveRoutine` svarar på "vilken robot arbetar användaren med just nu" —
en fråga agenten annars måste gissa sig till.

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `app_info` | codegen | read | `vcApplication.ProductName`, `ProductVersion`, `ProductClass`, `getApplicationPath`, `getPythonDllPath` |
| `layout_info` | codegen | read | `vcApplication.LayoutPath`, `LayoutUri`, `LayoutModified` |
| `load_layout` | codegen | write | `vcApplication.load`, `createLayout`, `ResetSimulationAtLoading` |
| `save_layout_as` | codegen | write | `vcApplication.save`, `vcCommand.saveLayoutToUri` |
| `set_context` | codegen | write | `vcApplication.setContext`, `CurrentContext`, `Contexts`, `VC_CONTEXT_TEACH` |
| `teach_context` | codegen | read | `vcApplication.TeachContext`, `vcTeachContext.ActiveRobot`, `ActiveRoutine`, `setActiveStatement` |
| `author_context` | codegen | read | `vcApplication.AuthorContext`, `vcAuthorContext.ActiveComponent`, `setActiveFeature` |
| `random_seed` | codegen | read | `vcApplication.getRandomSeed`, `vcProperty.RandomStream` |
| `real_time` | codegen | write | `vcApplication.RealTime`, `RealTimeMode`, `delayRealTime` |
| `pack_folder` | codegen | write | `vcPackFolder.mapFolder`, `remapFolder`, `rollbackFolder`, `VC_PACK_FOLDER_MAPPED` |
| `vcm_metadata` | codegen | write | `vcHelpers.VcmFile.Author`, `Manufacturer`, `Tags`, `write` |
| `capability_report` | **data** | read | `ext/vc_addon/vc_assist/formaga.py` (46 mätta ytor) |

**12 nya.**
---

## 5. Rangordning — vad domänen är värd

Tre storheter vägs, och de är avsiktligt olika:

- **Yta**: metoder + egenskaper, mätt (avsnitt 2).
- **Profiler**: hur många av de sex i `48_personaprofiler.md` som rör domänen,
  och hur många som **inte kan arbeta utan** den (`●●`).
- **Grindvärde**: om domänen är råvara för en dom. `50_grindar.md` och
  `40_ogat.md` kan inte fälla något utan mätning och simulering.

| Rang | Domän | Yta | Profiler (varav ●●) | Grindvärde | Motiv i en mening |
|---|---|---|---|---|---|
| 1 | simulering | 40 | 5 (4) | **bärande** | ögat provtar på `SimTime`; utan den finns ingen tidsaxel |
| 2 | mätning | 65 | 4 (2) | **bärande** | grinden parsar avstånd och träffar; utan den finns ingen dom |
| 3 | scen | 188 | 6 (3) | hög | allt annat pekar på en komponent eller en nod |
| 4 | signal | 46 | 4 (1) | hög | enda mekaniska källan till PLC-deklarationer (I10) |
| 5 | robot | 87 | 4 (1) | hög | P2 kan inte ta ett steg utan den |
| 6 | kinematik | 92 | 4 (1) | hög | `getConfigWarnings` är en mekanisk räckviddsdom |
| 7 | program | 178 | 3 (1) | medel | P2:s leverabel; 80 satstyper |
| 8 | process | 178 | 3 (1) | medel | P4:s leverabel; flest typer och händelser |
| 9 | produkt | 129 | 3 (1) | medel | inflöde och produkttyper, P4:s ingång |
| 10 | flöde | 59 | 4 (1) | medel | transportbanden i varje cell |
| 11 | transportsystem | 43 | 2 (1) | medel | ruttlösningen mellan stationer |
| 12 | statistik | 114 | 3 (2) | medel | P4:s och P5:s svar; siffrorna i offerten |
| 13 | komposition | 32 | 5 (2) | hög | liten yta, bär I8 |
| 14 | rörelsebana | 62 | 2 (0) | medel | bandens egen fysik |
| 15 | enheter | 40 | — | hög | skyddet mot tal utan storhet |
| 16 | matematik | 40 | — | medel | räknar om VC:s egna svar |
| 17 | vy | 20 (+27) | 3 (1) | hög | bildfångst är ögats andra kanal |
| 18 | montering | 50 | 1 (0) | låg | endast produkter med struktur |
| 19 | fordon | 29 | 1 (0) | låg | endast AGV-layouter |
| 20 | utseende | 34 | 3 (0) | låg | syns men avgör inget |
| 21 | ui | 164 | — | medel | urvalet säger vad frågan handlar om |
| 22 | app | 158 | — | medel | identitet, kontext, förmågeprövning |
| 23 | geometri | 277 | 1 (1) | låg | störst yta, minst spridning |

Den viktigaste avläsningen: **geometri är störst och rankas sist.** En stor
API-yta är inte samma sak som ett stort behov. Motsatt: simulering är näst
minst och rankas först, för att allt som ska dömas måste kunna köras.
Rangordningen mäter nytta, inte omfång.

---

## 6. Byggordning — 15 rundor

324 nya verktyg. Rundorna är 16–25 stora, vilket är den storlek som ryms i en
cell med bibehållen grind: varje runda ska stänga med prov på varje verktyg
och minst en trasig fixtur per skrivverktyg (`95_testprotokoll.md`).

| Runda | Innehåll | Antal | Varför just här |
|---|---|---|---|
| 1 | simulering 12 + mätning 8 (kollision, avstånd, ray) | 20 | ögat och grinden får sin råvara först. Utan denna runda mäter resten ingenting |
| 2 | mätning 7 (bbox, volym, svept, mått) + signal 13 + statistik 2 (`warmup`, `flow_events`) | 22 | stänger mätsidan och öppnar signalvägen mot PLC |
| 3 | scen 21 + ui 3 (`get_selection`, `set_selection`, `selection_helpers`) | 24 | färdigställer den domän som redan är påbörjad; urvalet hör till scenens läsning |
| 4 | komposition 6 + enheter 6 + matematik 8 | 20 | tre små domäner som alla är skydd: relationer (I8), storheter, omräkning |
| 5 | robot 19 | 19 | P2 kan börja arbeta |
| 6 | kinematik 16 | 16 | räckvidd och konfiguration blir mekaniskt avgjorda |
| 7 | program 24 | 24 | P2:s leverabel. Kräver runda 5–6 |
| 8 | process 24 | 24 | P4:s ryggrad. Flest typer i hela API:t |
| 9 | produkt 19 | 19 | inflödet som processen konsumerar |
| 10 | montering 9 + rörelsebana 10 | 19 | produkter med struktur, och banorna de åker på |
| 11 | transportsystem 10 + flöde 14 | 24 | sluter materialflödet mellan stationer |
| 12 | fordon 9 + statistik 15 | 24 | AGV och analytikerns hela svarsyta |
| 13 | vy 12 + ui 9 (kommandon, dialoger, snap) | 21 | P5 kan leverera bilder och film |
| 14 | utseende 11 + app 12 | 23 | det som gör en leverans presentabel, och kontextfrågorna |
| 15 | geometri 25 | 25 | störst, men bara P6 blockeras av att den saknas |

**Efter runda 3 passerar katalogen 100 verktyg.** Då slår regeln i
`45_verktyg.md` in: semantiskt urval per tur i stället för att skicka alla.
Den mekanismen måste alltså vara byggd **före runda 4**, inte efter runda 15.
Det är den enda ordningsberoende punkt i planen som inte är en domän.

### Vad som redan ligger utanför den här räkningen

Fyra domäner i `45_verktyg.md` bygger inte på VC:s API och räknas inte i de
324: `catalog` (data, bank-indexet), `knowledge` (data, API-indexet), `plc`
(data, OpenPLC) och `eyes`. De byggs i egna celler och har egna källor.

---

## 7. Gränserna — vad som inte går att bygga, och varför

Regeln: **ett verktyg som inte kan byggas ska stå här med skäl, inte utelämnas
tyst.** Varje rad är mätt med en sökning i indexet eller i `.NET`-dokumenten.

### 7.1 Finns inte i Python-API:t alls

| Önskat verktyg | Vad mätningen säger | Vad som finns i stället |
|---|---|---|
| `catalog_browse`, `catalog_download` | sökning på "catalog" i indexet ger **2 träffar**, båda `vcCommand.(Deprecated) rebuildECatalog`. eCatalog är en nättjänst bakom användarkonto | `search_catalog` som **data**-verktyg över `bank/katalog_index.json` |
| `connect_opcua`, `plc_bind_variable` | sökning på "connectivity", "opc" och "plc" ger **0 träffar** i api.xml. Connectivity finns bara i .NET (`IServerHandler`, `IOpcUAServer`) | VC konfigureras som OPC UA-**klient** i gränssnittet; agenten arbetar mot OpenPLC-sidan (`60_plc.md`) |
| `import_cad` | i Python finns bara `vcCommand.(Deprecated) interactiveImportModel`. CAD-läsaren är .NET: `VisualComponents.Create3D.ICADReader`, `HiddenPartsImport`, `ImportSummaryMessage` | manuell import; agenten arbetar på det som redan är inne |
| `export_fbx` | `VisualComponents.Create3D.IFBXExporter` är .NET. Mätt i `10_matta_fakta.md`: FBX är dessutom **endast export** | `vcApplication.save` till VC:s eget format |
| `export_robot_program` | `IRobotConverter` är .NET. `VC_RRSROBOTCONTROLLER` och `VC_KRCCONNECTION` är bara beteendetypnamn | inget. Programmet stannar i VC |
| `create_drawing_view` | `VC_CONTEXT_DRAWING`, `VC_SELECTION_DRAWINGVIEW` och `vcApplication.DrawingContext` finns, men **ingen `vcDrawing`-typ**. 2D-ritningen har ingen typad Python-yta | `record_pdf` |
| `undo`, `redo` | sökning på "undo" ger **2 träffar**, varav en är `vcGeometryFeature.Uri`. Endast `vcApplication.clearUndo` finns — den *tömmer* historiken | inget. **Följd: godkännandekön kan inte backa ett anrop, den måste hindra det i förväg.** Det stärker I12 i stället för att försvaga den |
| `set_rigid_body`, `add_physics_joint` | 21 `VC_PHYSICS*`-konstanter finns, men enda medlemmen i hela API:t är `vcFeature.PhysicsCollider`. Ingen `vcPhysics*`-typ bland de 204 | `physics_collider` (egenskapen) plus egenskapsdrivet arbete via `createBehaviour(VC_PHYSICSENTITY, ...)` |
| `human_task`, `ergonomics_score`, `energy_report`, `cost_report`, `shift_calendar`, `mtbf` | sökning på "human", "worker", "ergonom", "energy", "calendar" och "mtbf" ger **0 träffar var**. "cost" ger 1, och den är `vcSweptVolume.DecompositionQuality` | inget. Det arbete Works-biblioteket gör med människor är komponenter och egenskaper, inte API |
| paneler, flikar, dockning i gränssnittet | `UX.Shared.xml` bär 2454 medlemmar och är .NET/WPF | `vcApplication.addMenuItem`, `addUxSite`, `vcHelpers.Application1` — menyer och dialoger, inte paneler |

### 7.2 Möjligt men oprövat — får inte byggas som om det vore känt

| Verktyg | Osäkerheten |
|---|---|
| `import_geometry` | `vcCommand.loadGeometryAsComponent` **finns**, men källan anger dess signatur som `unknown`. Ett verktyg får byggas först när anropet är provat i en körande VC, annars är det en stub som ljuger (S1) |
| `export_layout_geometry` | `vcCommand.exportLayoutAsGeometry` finns men tar inga argument — sannolikt interaktiv. Samma krav: prövas först |
| allt som bygger på de **105** konstanter utan typ | objektet kommer tillbaka som `vcBehaviour` eller `vcFeature`. Verktyget kan sätta egenskaper men kan inte typkontrollera dem. Fail-closed (I3): säg att värdet sattes bara om det går att läsa tillbaka |
| `vcCurveData`-verktygen | 19 medlemmar står i källan som *egenskaper* med parameterlistor. Klassningen är källans fel, inte vår — anropsformen måste provas |

### 7.3 Sådant som är byggbart men avsiktligt inte föreslås

- **De 18 `(Deprecated)`-metoderna på `vcCommand`.** De finns i indexet och
  skulle gå att anropa. Ett verktyg på en metod som leverantören själv märkt
  som avvecklad är skuld vid födseln (S4).
- **`vcApplication.clearWorld` utan skydd.** Verktyget föreslås, men det hör
  till den strängaste klassen i godkännandekön: det raderar hela layouten.
- **`vcScript.convertToByteCode`.** Kompilering av genererad kod till bytekod
  gömmer källan för granskning. Går emot hela godkännandetanken.

### 7.4 Den lokala bristen som inte är API:ts fel

**MÄTT 2026-09-04 i testprefixet: noll `.vcmx`-layouter och fem
komponentfiler på disk** (`svc/vc_assist_svc/verktyg/katalog.py`). Det gör att
`load_component` inte kan bevisas mot något riktigt bibliotek här, och att
varje bänkuppgift som förutsätter en katalog är blockerad på en nättjänst.

Det motverkas av att `vcApplication.createComponent` finns: en komponent går
att bygga från noll, med `createNode`, `createBehaviour` och
`createGeometrySet`. En bänk som bygger sina egna komponenter är oberoende av
katalogen. **Det är den vägen som ska prövas först**, inte ett väntande på
kontoåtkomst.

---

## 8. Summering

| Tal | Värde | Härkomst |
|---|---|---|
| Domäner | 23 | indelning av de 204 typerna, summan kontrollerad |
| Typer / metoder / egenskaper / händelser | 204 / 966 / 1159 / 175 | `ApiIndex.statistik()` |
| Konstanter | 709, varav 151 typnamn och 105 utan motsvarande typ | räknat på namnform |
| Byggda verktyg | 21 i 2 domäner | `verktyg.register.domaner()` |
| Föreslagna nya verktyg | **324 i 23 domäner** | räknat på tabellraderna i avsnitt 4 |
| Totalt bibliotek | **345** | 21 + 324 |
| Rundor | 15, om 16–25 verktyg | avsnitt 6 |
| Verktyg som är omöjliga | 11 namngivna klasser | avsnitt 7.1 |
| Verktyg som är möjliga men oprövade | 4 klasser | avsnitt 7.2 |

Jämförelsen med källprojektet: 448 verktyg mot 345. Skillnaden är inte
ambition utan yta. Källan hade USD, där varje attribut är en egen väg in.
VC:s modell är metodbaserad, och en metod som `vcRoutine.addStatement` täcker
80 satstyper med ett enda verktyg plus en enum. **Ett mindre bibliotek som
täcker samma arbete är inte en mindre leverans.**

Sista raden, och den gäller varje runda: varje verktyg i det här dokumentet
namnger ytor som är kontrollerade mot indexet vid skrivningen. Det är inte
samma sak som att de är **provade i en körande VC**. Det görs runda för runda,
mot `formaga.py`, och ett verktyg vars yta saknas i den VC som kör exponeras
inte alls.
