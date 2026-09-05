# Personaprofiler

Sju arbetsprofiler för **vem som använder Visual Components och vad de vill
åstadkomma**. Underlag för täckningsanalysen i `47_verktygstackning.md`, och
sedan fas 19 dessutom **nämnaren i en körbar grind**:
`tests/protocol/kor_fas19_tackning.py` läser den här filen, dömer varje rad mot
API-indexet och verktygsregistret, och rapporterar täckningen per profil.

beskriver: `svc/vc_assist_svc/personatackning.py`,
`svc/vc_assist_svc/api_index.py`, `svc/vc_assist_svc/verktyg/`,
`docs/referens/vc_api/`, `docs/referens/vc_dotnet/`

---

## Varför den här filen är en nämnare och inte en beskrivning

En täckningssiffra är lätt att göra meningslös. Om nämnaren får vara *"de steg
vi råkade skriva ned"* stiger talet av att man **slutar skriva steg**. Därför
gäller fyra regler, och alla fyra är mekaniserade i grinden:

1. **Alla steg står kvar.** Ett steg vi inte klarar tas aldrig bort; det får
   `saknas` i sista kolumnen och ligger kvar i nämnaren.
2. **Golv per profil.** Antalet arbetssteg får bara gå uppåt (`GOLV` i
   `personatackning.py`, satt av M-100). Ett steg som tystnat bort fäller på
   `NÄMNAREN_KRYMPTE` — inte på en högre procentsats.
3. **Profilerna är namngivna i koden.** En hel profil som stryks fäller på
   `PROFIL_SAKNAS`. Utan den regeln vore 100 % en radering bort.
4. **`UI` och `.NET` är den enda ärliga vägen ur nämnaren, och den är
   bevakad.** Ett steg får bara märkas utanför räckvidd om det pekar på ett
   namn som **inte** finns i Python-API:t — och `.NET`-namnet måste dessutom
   finnas i `docs/referens/vc_dotnet/`. Ett steg som märks `UI` men i själva
   verket är skriptbart fäller på `FALSK_UTANFÖR`.

## Vad kolumnerna betyder

| Kolumn | Innehåll |
|---|---|
| `#` | löpnummer, 1..N utan hål. Ett urklippt steg lämnar ett hål och fälls |
| Arbetssteg | vad användaren faktiskt gör |
| Verkan | `läser` eller `ändrar` — stegets verkan **på scenen**, inte verktygets |
| Kräver | vad steget vilar på, i fyra former (nedan) |
| Täckt av | verktygsnamn ur registret, eller `UI`, `.NET`, `saknas` |

Kolumnen **Kräver** bär fyra slag av poster, och var och en döms mekaniskt:

| Form | Betyder | Kontroll |
|---|---|---|
| `vcTyp.medlem` | VC:s Python-API | måste finnas i `api_index` (3444 symboler) |
| `.NET:Namn` | .NET-ytan, alltså ett plugin | måste finnas i `vc_dotnet/*.xml` **och inte** i Python-indexet |
| `UI:Namn` | bara i gränssnittet, ingen skriptyta | får **inte** finnas i Python-indexet, inte heller med annat skiftläge |
| `TJÄNST:modul` | tjänstens egen källa utanför VC | modulen måste finnas under `svc/vc_assist_svc/` |

Kolumnen **Verkan** är facit som verktygets deklarerade `effect` prövas mot.
Ett steg som `ändrar` scenen kan inte täckas av enbart läsande verktyg — det
är `FEL_VERKAN`. Omvänt är tillåtet: `measure_distance` är deklarerad `write`
därför att den bygger en kollisionsdetektor i scenen, och får därför täcka ett
läsande steg.

---

## P1 — Layoutplaneraren

Bygger en fabrikslayout av färdiga komponenter. Frågar *får det plats, krockar
det, hur långt är det mellan stationerna, vad kostar den här raden*.

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | öppna en sparad layout | ändrar | `vcApplication.load`, `vcApplication.LayoutUri` | saknas |
| 2 | börja från tomt bord | ändrar | `vcApplication.createLayout`, `vcApplication.clearWorld` | saknas |
| 3 | se vad som redan står i layouten | läser | `vcApplication.Components`, `vcComponent.Name` | `list_components` |
| 4 | slå upp en känd komponent på namn | läser | `vcApplication.findComponent` | `find_component` |
| 5 | bläddra i eCatalog efter något man inte kan namnet på | läser | `UI:eCatalog` | UI |
| 6 | söka i det installerade biblioteket på räckvidd och last | läser | `TJÄNST:katalogsok` | `search_installed_library`, `search_catalog` |
| 7 | se vad biblioteket alls innehåller, per tillverkare | läser | `TJÄNST:katalogindex` | `library_overview`, `catalog_categories` |
| 8 | läsa en katalogposts datablad innan den laddas in | läser | `TJÄNST:komponentdatablad` | `component_datasheet`, `catalog_item` |
| 9 | ladda in komponenten i layouten | ändrar | `vcApplication.load`, `vcComponent.Uri` | `load_component` |
| 10 | sätta läge och riktning på komponenten | ändrar | `vcNode.PositionMatrix`, `vcMatrix.setWPR` | `set_transform` |
| 11 | läsa var något står i världen | läser | `vcComponent.WorldPositionMatrix` | `get_transform` |
| 12 | snäppa mot en kant eller ett hörn i vyn | ändrar | `UI:Snap-verktyget`, `vcSnapCommand.SnapOnEdge` | saknas |
| 13 | fråga om två grannar går att koppla ihop | läser | `vcSimInterface.canConnect` | `can_connect` |
| 14 | koppla ihop med grannen | ändrar | `vcSimInterface.connect` | `connect` |
| 15 | se vilka gränssnitt en komponent bär | läser | `vcSimInterface.Sections`, `vcSimInterface.IsAbstract` | `list_interfaces`, `interface_info` |
| 16 | se vad som redan är hopkopplat i hela layouten | läser | `vcSimInterface.ConnectedComponents` | `list_connections` |
| 17 | koppla isär en felkopplad granne | ändrar | `vcSimInterface.disconnect` | `disconnect` |
| 18 | klona en station till en rad likadana | ändrar | `vcComponent.clone` | `clone_component` |
| 19 | mönstra ut klonerna med jämnt avstånd | ändrar | `vcMatrix.translateRel` | saknas |
| 20 | ta bort en komponent som inte ska vara kvar | ändrar | `vcApplication.deleteComponent` | `delete_component` |
| 21 | läsa komponentens omslutande låda för att veta hur stor den är | läser | `vcNode.BoundCenter`, `vcNode.BoundDiagonal` | `get_bounds` |
| 22 | mäta gångbredd mellan två kroppar | läser | `vcNode.measureDistance` | `measure_distance` |
| 23 | hitta vilken granne som ligger närmast en station | läser | `vcCollisionDetector.testMinimumDistance` | `min_distance` |
| 24 | kontrollera att kollisionsprovet alls fungerar i den här installationen | ändrar | `vcSimulation.newCollisionDetector` | `collision_detector_status` |
| 25 | kollisionskoll över hela layouten | ändrar | `vcCollisionDetector.testAllCollisions`, `vcCollisionDetector.getHitNodeA` | `test_collision` |
| 26 | låta simuleringen stanna av sig själv vid krock | ändrar | `vcCollisionDetector.StopOnCollision` | saknas |
| 27 | lägga stationer i lager och släcka ett lager | ändrar | `vcApplication.createLayer`, `vcLayer.Visibility` | saknas |
| 28 | dölja en komponent utan att ta bort den | ändrar | `vcNode.NodeVisible` | saknas |
| 29 | färgsätta zoner så layouten går att läsa | ändrar | `vcApplication.createMaterial`, `vcNode.NodeMaterial` | saknas |
| 30 | måttsätta layouten med ett mått som syns i bilden | ändrar | `vcApplication.createLayoutItem`, `vcDimension.Node1`, `vcDimension.Node2` | saknas |
| 31 | sätta en textnot vid en station | ändrar | `vcAnnotation.Text`, `vcAnnotation.LockToNode` | saknas |
| 32 | läsa en komponents egna parametrar | läser | `vcComponent.Properties` | `list_properties`, `get_property` |
| 33 | ändra en parameter, till exempel transportörens längd | ändrar | `vcComponent.getProperty`, `vcProperty.Value` | `set_property` |
| 34 | läsa stycklistan ur layouten | läser | `vcComponent.BOM`, `vcComponent.BOMname` | saknas |
| 35 | låsa en färdig station så ingen råkar flytta den | ändrar | `vcComponent.Locked` | saknas |
| 36 | spara layouten | ändrar | `vcApplication.save` | `save_layout` |
| 37 | paketera layouten med sina komponenter för att skicka den vidare | ändrar | `vcPackFolder.mapFolder`, `vcComponent.PackFolder` | saknas |

Det här är den profil de byggda verktygen ligger närmast. Det som fattas är
**presentationslagret** (lager, färg, mått, noter) och **katalogen inne i VC** —
bibliotekssökningen går via tjänstens eget index, inte via VC.

---

## P2 — Robotprogrammeraren

Lär en robot en bana, kontrollerar räckvidd och konfiguration, mäter cykeltid.

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | hitta layoutens robotar | läser | `vcComponent.findBehavioursByType`, `VC_ROBOTCONTROLLER` | `list_robots` |
| 2 | läsa robotens uppbyggnad: leder, fläns, rot | läser | `vcRobotController.JointCount`, `vcRobotController.FlangeNode`, `vcRobotController.RootNode` | `robot_info` |
| 3 | läsa ledernas gränser och maxfart | läser | `vcJoint.MinValue`, `vcJoint.MaxValue`, `vcJoint.MaxSpeed` | `robot_limits` |
| 4 | läsa styrenhetens kartesiska gränser | läser | `vcRobotController.MaxCartesianSpeed`, `vcRobotController.MaxAngularSpeed` | `robot_limits` |
| 5 | läsa ledvärdena just nu | läser | `vcRobotController.Joints`, `vcRobotController.getJointValue` | `get_joints` |
| 6 | läsa var verktygspunkten står i världen | läser | `vcToolFrame.PositionMatrix`, `vcRobotController.FlangeNode` | `get_tcp` |
| 7 | ställa roboten i en pose utan att simulera rörelsen | ändrar | `vcRobotController.moveImmediate` | `set_joints` |
| 8 | jogga fram till en pose för hand | ändrar | `vcApplication.startJogging`, `vcApplication.doJogging`, `vcApplication.stopJogging` | saknas |
| 9 | montera ett verktyg på flänsen | ändrar | `vcRobotController.addTool`, `vcToolContainer.addTool` | `add_frame` |
| 10 | lägga till en basram att programmera mot | ändrar | `vcRobotController.addBase`, `vcBaseContainer.addBase` | `add_frame` |
| 11 | lista verktygs- och basramar med sina lägen | läser | `vcRobotController.Tools`, `vcRobotController.Bases` | `list_frames` |
| 12 | ta bort en verktygsram som blev fel | ändrar | `vcRobotController.removeTool`, `vcRobotController.removeBase` | saknas |
| 13 | räkna fram var TCP:n hamnar för givna ledvärden | ändrar | `vcPythonKinematics.forwardKin`, `vcKinObject.JointValues` | `forward_kinematics` |
| 14 | fråga om roboten når en punkt | ändrar | `vcMotionTarget.getConfigWarnings`, `VC_MOTIONTARGET_KW_UNREACHABLE` | `check_reach` |
| 15 | se vilka konfigurationer punkten går att nå i | ändrar | `vcMotionTarget.ConfigCount`, `vcMotionTarget.RobotConfig` | `check_reach` |
| 16 | välja konfiguration och vridningsläge | ändrar | `vcMotionTarget.ConfigurationMode`, `vcMotionTarget.JointTurnMode` | `set_robot_config` |
| 17 | skapa en rutin i robotprogrammet | ändrar | `vcProgram.addRoutine` | `create_routine` |
| 18 | lista programmets rutiner | läser | `vcProgram.Routines`, `vcProgram.MainRoutine` | `list_routines` |
| 19 | lägga en rörelsesats i rutinen | ändrar | `vcRoutine.addStatement`, `VC_STATEMENT_LINMOTION` | `add_motion_statement` |
| 20 | lägga en grepp- eller släppsats | ändrar | `VC_STATEMENT_GRASP`, `VC_STATEMENT_RELEASE` | `add_statement` |
| 21 | vänta på en signal och sätta en signal i programmet | ändrar | `VC_STATEMENT_WAITSIGNAL`, `VC_STATEMENT_SETBIN` | `add_statement` |
| 22 | sätta hastighet och noggrannhet per sats | ändrar | `vcMotionTarget.CartesianSpeed`, `vcMotionTarget.AccuracyMethod` | `edit_statement` |
| 23 | läsa tillbaka satserna i en rutin | läser | `vcRoutine.Statements`, `vcStatement.Type` | `read_routine` |
| 24 | ändra en sats som redan finns | ändrar | `vcRoutine.getStatement` | `edit_statement` |
| 25 | ta bort en sats | ändrar | `vcRoutine.deleteStatement` | `delete_statement` |
| 26 | ta bort en hel rutin | ändrar | `vcProgram.deleteRoutine` | `delete_routine` |
| 27 | köra en rutin | ändrar | `vcExecutor.callRoutine` | `run_routine` |
| 28 | stega en sats i taget när något inte stämmer | ändrar | `vcExecutor.callStatement` | `step_statement` |
| 29 | se var programmet står just nu | läser | `vcExecutor.CurrentStatement` | `program_state` |
| 30 | bygga hela banan i ett svep och köra den | ändrar | `vcRobotController.addTarget`, `vcRobotController.clearTargets` | `move_targets` |
| 31 | köra roboten till ett enda mål | ändrar | `vcRobotController.moveTo`, `vcRobotController.moveRelTo` | `move_to` |
| 32 | mäta cykeltiden för banan | läser | `vcRobotController.calcMotionTime` | saknas |
| 33 | köra hela cellen och se att den inte krockar | ändrar | `vcSimulation.run`, `vcCollisionDetector.testAllCollisions` | `sim_run`, `test_collision` |
| 34 | använda VC:s färdiga plocka- och placera-recept | ändrar | `vcHelpers.Robot.pick`, `vcHelpers.Robot.place` | saknas |
| 35 | spela in en rutin ur handrörelser | ändrar | `vcHelpers.Robot.RecordRoutine` | saknas |
| 36 | exportera programmet till robotens eget språk | läser | `.NET:VisualComponents.Create3D.IRobotConverter` | .NET |

Den mest API-täta profilen. `vcHelpers.Robot` och `vcHelpers.Robot2` bär 55
färdiga medlemmar var för just det här arbetet, och ingen av dem är byggd som
verktyg — steg 34 och 35 är den billigaste kvarvarande vinsten i hela
registret.

---

## P3 — Driftsättaren (virtual commissioning)

Kopplar scenen till styrsystemet och letar tidsfel, sekvensfel och
förreglingar. Det här är den profil projektets egen bänk är byggd för
(`83_scenarier.md`).

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | inventera signalerna i hela cellen | läser | `vcComponent.Behaviours`, `VC_BOOLEANSIGNAL`, `vcSignal.Type` | `list_signals`, `signal_inventory` |
| 2 | se vilka signaltyper den här VC:n faktiskt bär | läser | `VC_INTEGERSIGNAL`, `VC_REALSIGNAL` | `signal_types` |
| 3 | läsa allt om en enskild signal | läser | `vcSignal.Type`, `vcSignal.Connections` | `signal_info` |
| 4 | läsa ett signalvärde om och om under ett försök | läser | `vcBoolSignal.Value` | `get_signal` |
| 5 | sätta ett signalvärde för hand | ändrar | `vcBoolSignal.Value` | `set_signal` |
| 6 | pulsa en signal så mottagaren fyrar | ändrar | `vcBoolSignal.signal` | `set_signal` |
| 7 | skapa en signal som saknas på en komponent | ändrar | `vcNode.createBehaviour`, `VC_STRINGSIGNAL` | `create_signal` |
| 8 | ta bort en signal som blev fel | ändrar | `vcBehaviour.delete` | `delete_signal` |
| 9 | koppla signal till signal, även mellan komponenter | ändrar | `vcSignal.connect` | `connect_signals` |
| 10 | koppla isär två signaler | ändrar | `vcSignal.disconnect` | `disconnect_signals` |
| 11 | se vad som är kopplat till vad i hela layouten | läser | `vcSignal.Connections` | `list_signal_connections` |
| 12 | skapa en signalkarta på en station | ändrar | `vcNode.createBehaviour`, `VC_BOOLEANSIGNALMAP` | `create_signal_map` |
| 13 | lista scenens signalkartor med riktning och portantal | läser | `vcBooleanSignalMap.Ports`, `vcBooleanSignalMap.PortCount` | `list_signal_maps` |
| 14 | läsa en karta port för port | läser | `vcBooleanSignalMap.getPortName` | `signal_map_info` |
| 15 | sätta vilken signal en port bär | ändrar | `vcBooleanSignalMap.setPortSignal`, `vcBooleanSignalMap.setPortName` | `signal_map_set_port` |
| 16 | tömma en port som inte ska användas | ändrar | `vcBooleanSignalMap.addPort` | `signal_map_clear_port` |
| 17 | sätta kartans riktning: in eller ut | ändrar | `vcBooleanSignalMap.Direction`, `vcBooleanSignalMap.trySetDirection` | `set_signal_map_direction` |
| 18 | fjärrkoppla två stationers kartor till varandra | ändrar | `vcBooleanSignalMap.getConnectedExternalSignals` | `signal_map_connect` |
| 19 | binda en egenskap till en signal med en adapter | ändrar | `vcBehaviour.Type`, `vcBehaviour.Properties` | `set_behaviour_property`, `list_property_adapters` |
| 20 | ta reda på vad som alls går att veta om uppkopplingen | läser | `TJÄNST:verktyg.signaler` | `connectivity_status` |
| 21 | koppla scenen mot PLC:n | ändrar | `.NET:VisualComponents.Connectivity.Core.IServerHandler`, `.NET:VisualComponents.Connectivity.OpcUA.IOpcUAServer` | .NET |
| 22 | ställa in kopplingen i Connectivity-fliken | ändrar | `UI:Connectivity-fliken` | UI |
| 23 | köra simuleringen ett bestämt antal sekunder | ändrar | `vcSimulation.run` | `sim_run` |
| 24 | fortsätta utan att nolla klockan | ändrar | `vcSimulation.continueRun` | `sim_continue` |
| 25 | stoppa omedelbart när något ser fel ut | ändrar | `vcSimulation.halt` | `sim_halt` |
| 26 | uppdatera scenen ett steg utan att köra | ändrar | `vcSimulation.update`, `vcApplication.render` | `sim_step` |
| 27 | läsa klockan och veta om det körs | läser | `vcSimulation.SimTime`, `vcSimulation.IsRunning` | `sim_state` |
| 28 | sänka farten för att se en flank i vyn | ändrar | `vcSimulation.SimSpeed` | `sim_speed` |
| 29 | följa en flank på samma tidsaxel som PLC:n | läser | `vcSignal.OnValueChange` | saknas |
| 30 | avbryta automatiskt när ingen komponent längre gör något | ändrar | `vcSimulation.autoHalt` | `sim_autohalt` |
| 31 | spara utgångsläget före ett försök | ändrar | `vcSimulation.setInitialState` | `sim_initial_state` |
| 32 | återställa till utgångsläget mellan två försök | ändrar | `vcSimulation.restoreInitialState`, `vcSimulation.reset` | `sim_initial_state`, `sim_reset` |
| 33 | stanna simuleringen automatiskt på krock | ändrar | `vcSimulation.OnCollision`, `vcCollisionDetector.StopOnCollision` | saknas |
| 34 | mäta hur långt en detalj kommit på transportören | läser | `vcComponent.getPathDistance` | `path_distance` |
| 35 | se var en givare sitter och vilken signal den driver | läser | `vcProcessPointSensor.Frame` | `list_path_sensors` |

**Steg 21 finns inte i Python-API:t.** Sökning på `connectivity`, `opc` och
`plc` i indexet ger noll träffar av rätt slag — beläggen står i
`47_verktygstackning.md` §7.1. Vägen dit är OpenPLC som OPC UA-server och VC:s
eget Connectivity-plugin, konfigurerat i gränssnittet (steg 22), precis som
`30_arkitektur.md` beskriver.

---

## P4 — Flödesingenjören / produktionsanalytikern

Kör produktionsflöde, mäter genomströmning, utnyttjande och flaskhalsar.

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | se vilka produkttyper processregulatorn känner | läser | `vcProductTypeManager.ProductTypes`, `vcProductType.ComponentUri` | `list_product_types` |
| 2 | läsa en produkttyp i detalj, med stycklista | läser | `vcProductType.ProductProperties`, `vcProductType.IsAssembly` | `product_type_info` |
| 3 | definiera en ny produkttyp | ändrar | `vcProductTypeManager.createProductType` | saknas |
| 4 | läsa hur produkter matas in idag | läser | `vcProductCreator.FeedMode`, `vcProductCreatorSingleMode.Interval` | `get_feeder_info` |
| 5 | sätta takten på produktinmatningen | ändrar | `vcProductCreatorSingleMode.Interval`, `vcProductCreatorSingleMode.Limit` | `set_product_feed` |
| 6 | mata en blandning enligt fördelning eller tabell | ändrar | `vcProductCreatorTableMode.addRow`, `vcProductCreatorDistributionMode.addProductEntry` | saknas |
| 7 | läsa komponentskaparnas takt och mall | läser | `vcComponentCreator.Interval`, `vcComponentCreator.TemplateComponent` | `get_component_creator_info` |
| 8 | sätta takten på en komponentskapare | ändrar | `vcComponentCreator.Interval`, `vcComponentCreator.Limit` | `set_component_feed` |
| 9 | se vilka flödesgrupper som finns | läser | `vcProcessFlowGroupManager.Groups` | `list_process_flow_groups` |
| 10 | skapa en flödesgrupp | ändrar | `vcProcessFlowGroupManager.createGroup` | saknas |
| 11 | bygga en sekvens av processgrupper | ändrar | `vcProcessFlowTable.createSequence`, `vcProcessSequence.addProcessGroup` | saknas |
| 12 | se vilka processer en station kan utföra | läser | `vcProcessExecutor.Processes` | `list_processes` |
| 13 | läsa stegen i en process med sina tider | läser | `vcProcessRoutine.Statements`, `VC_STATEMENT_WORK` | `list_process_statements` |
| 14 | lägga till en process på en station | ändrar | `vcProcessExecutor.addProcess` | saknas |
| 15 | skriva vad ett processteg gör | ändrar | `vcProcessRoutine.addStatement` | saknas |
| 16 | se hur produkterna kan ta sig vidare | läser | `vcFlow.Connectors`, `vcFlow.ConnectorCount` | `list_flow_connectors` |
| 17 | se transportnoderna och länkarna mellan dem | läser | `vcTransportNode.TransportLinks`, `vcTransportSystem.Links` | `list_transport_nodes` |
| 18 | skapa en transportlänk mellan två noder | ändrar | `vcTransportSystem.createTransportLink` | saknas |
| 19 | låta systemet räkna ut en väg | läser | `vcTransportSystem.findSolution` | saknas |
| 20 | läsa dirigeringsregeln i en korsning | läser | `vcRoutingRule.Connectors`, `vcRoutingRule.ConnectorCount` | `get_routing_rule` |
| 21 | peka ut vilken utgång nästa produkt ska ta | ändrar | `vcRoutingRule.setTarget` | `set_routing_target` |
| 22 | läsa transportörens parametrar: fart, längd, riktning | läser | `vcTransportController.Properties`, `vcProperty.Value` | `list_transport_parameters`, `get_transport_parameter` |
| 23 | ändra en transportörparameter | ändrar | `vcBehaviour.Properties`, `vcProperty.Value` | `set_transport_parameter` |
| 24 | läsa kapacitet och fyllnadsgrad i buffertar | läser | `vcRoutingRule.Capacity`, `vcRoutingRule.CapacityAvailable` | `get_capacity`, `transport_behaviour_info` |
| 25 | sätta hur mycket en buffert rymmer | ändrar | `vcRoutingRule.Capacity` | `set_capacity` |
| 26 | se vad som ligger i en buffert just nu | läser | `vcRoutingRule.Components`, `vcRoutingRule.ComponentCount` | `list_buffer_contents` |
| 27 | ställa uppvärmningstid och körlängd | ändrar | `vcSimulation.SimWarmupTime`, `vcSimulation.SimulationRunTime` | `sim_warmup` |
| 28 | slå på snabbschemaläggning för en lång körning | ändrar | `vcSimulation.setFastScheduling` | `set_fast_scheduling` |
| 29 | köra länge och låta det loopa | ändrar | `vcSimulation.run`, `vcSimulation.IsLooping` | `sim_run`, `sim_speed` |
| 30 | upprepa körningen med olika slumpfrö | ändrar | `vcApplication.getRandomSeed` | saknas |
| 31 | läsa genomströmning per station | läser | `vcStatistics.PartsEntered`, `vcStatistics.PartsExited` | `station_statistics` |
| 32 | läsa genomströmningen för hela layouten på en gång | läser | `vcStatistics.ComponentsAverageTime` | `layout_statistics` |
| 33 | läsa hur länge en station stod i varje tillstånd | läser | `vcStatistics.getPercentage`, `vcStatistics.BlockedPercentage` | `station_state_times` |
| 34 | läsa utnyttjandet över hela körningen | läser | `vcStatistics.Utilization`, `vcStatistics.IntervalUtilization` | `station_state_times` |
| 35 | rita ett diagram ur statistiken | ändrar | `vcStatisticsTab.createChart`, `vcStatisticsChart.addSeries` | saknas |
| 36 | publicera en rapport ur körningen | ändrar | `vcReport.publish` | saknas |
| 37 | ställa in statistikpanelen i gränssnittet | ändrar | `UI:Statistikpanelen` | UI |

Den här profilen har fortfarande **störst API-yta utan verktyg**: att skapa
produkttyper, processer och transportlänkar är oskrivet, och hela
diagram- och rapportsidan likaså. Läs-sidan är däremot byggd sedan
transportdomänen kom till.

---

## P5 — Lösningsarkitekten som säljer

Bygger ett trovärdigt förslag snabbt och visar det för en kund.

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | bygga layouten grovt av kataloginnehåll | ändrar | `vcApplication.load` | `load_component` |
| 2 | hitta rätt robot på räckvidd och last | läser | `TJÄNST:katalogsok` | `search_installed_library` |
| 3 | ställa komponenterna på plats | ändrar | `vcNode.PositionMatrix` | `set_transform` |
| 4 | koppla ihop stationerna så materialet flödar | ändrar | `vcSimInterface.connect` | `connect` |
| 5 | få det att röra sig | ändrar | `vcSimulation.run` | `sim_run` |
| 6 | låta det loopa medan kunden tittar | ändrar | `vcSimulation.IsLooping`, `vcSimulation.SimSpeed` | `sim_speed` |
| 7 | nollställa inför nästa visning | ändrar | `vcSimulation.reset` | `sim_reset` |
| 8 | sätta en kameravy att återvända till | ändrar | `vcApplication.createView`, `vcView.CameraMatrix` | saknas |
| 9 | byta till en sparad vy | ändrar | `vcApplication.useView`, `vcApplication.findView` | saknas |
| 10 | flytta kameran dit man vill ha den | ändrar | `vcCamera.Matrix`, `vcCamera.Coi` | saknas |
| 11 | sätta material och färg på det som ska synas | ändrar | `vcApplication.createMaterial`, `vcMaterial.Diffuse` | saknas |
| 12 | sätta ljus i scenen | ändrar | `vcApplication.createLight`, `vcLight.Intensity` | saknas |
| 13 | slå på skuggor för en snyggare bild | ändrar | `vcApplication.RenderShadows` | saknas |
| 14 | ta en stillbild ur vyn | ändrar | `vcApplication.beginFrameGrab`, `vcApplication.executeFrameGrab`, `vcApplication.endFrameGrab` | saknas |
| 15 | spara bilden till fil | ändrar | `vcApplication.saveBitmap` | saknas |
| 16 | spela in en film av körningen | ändrar | `vcApplication.RecordScreen`, `vcApplication.RecordingFileName`, `VC_RECORDER_VIDEO` | saknas |
| 17 | spela in en PDF med steg | ändrar | `vcApplication.PdfRecord`, `vcApplication.PdfFileName` | saknas |
| 18 | exportera en animation till kundens eget verktyg | ändrar | `.NET:VisualComponents.Create3D.IAnimationRecorder`, `.NET:VisualComponents.Create3D.IFBXRecorder` | .NET |
| 19 | hämta cykeltiden att sätta i offerten | läser | `vcRobotController.calcMotionTime` | saknas |
| 20 | hämta genomströmningen att sätta i offerten | läser | `vcStatistics.PartsExited` | `station_statistics`, `layout_statistics` |
| 21 | hämta utnyttjandet per station | läser | `vcStatistics.Utilization` | `station_state_times` |
| 22 | läsa stycklistan till prissättningen | läser | `vcComponent.BOM` | saknas |
| 23 | sätta en textnot som förklarar en station | ändrar | `vcAnnotation.Text` | saknas |
| 24 | måttsätta så kunden ser att det får plats | ändrar | `vcDimension.Node1`, `vcDimension.Node2` | saknas |
| 25 | visa att inget krockar | ändrar | `vcCollisionDetector.testAllCollisions` | `test_collision` |
| 26 | spara förslaget | ändrar | `vcApplication.save` | `save_layout` |
| 27 | paketera det som ska skickas till kunden | ändrar | `vcPackFolder.mapFolder` | saknas |

Steg 14 är dessutom **ögats** råvara (`40_ogat.md`): bildfångst är samma yta
oavsett om mottagaren är en kund eller en grind. Att den ytan är obyggd är
alltså en brist på två ställen samtidigt.

---

## P6 — Komponentbyggaren

Gör en egen komponent av en CAD-modell: geometri, nodträd, leder, gränssnitt,
beteenden, egenskaper. `geometri` är den enskilt största domänen i API:t
(23 typer, 145 metoder) och den har inget verktyg alls.

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | importera en CAD-fil | ändrar | `vcCommand.loadGeometryAsComponent`, `vcCommand.loadLayoutToPosition` | saknas |
| 2 | ställa in importens detaljnivå i dialogen | ändrar | `UI:CAD-importdialogen`, `.NET:VisualComponents.Create3D.ICADReader` | UI |
| 3 | se hur tung geometrin blev | läser | `vcTriangleSet.TriangleCount`, `vcTriangleSet.PointCount` | saknas |
| 4 | förenkla meshen | ändrar | `vcTriangleSet.decimate`, `vcTriangleSet.mergePoints` | saknas |
| 5 | göra ett hölje av en tung detalj | ändrar | `vcTriangleSet.convexHull` | saknas |
| 6 | läsa nodträdet som blev av importen | läser | `vcNode.Children`, `vcNode.Parent` | `list_nodes` |
| 7 | hitta en nod på namn | läser | `vcComponent.findNode` | `find_node` |
| 8 | skapa en ny nod i trädet | ändrar | `vcNode.createNode`, `VC_NODE_ADD_LAST_CHILD` | saknas |
| 9 | flytta en nod till rätt förälder | ändrar | `vcNode.attach` | saknas |
| 10 | sätta nodens läge i förhållande till föräldern | ändrar | `vcNode.PositionMatrix` | `set_transform` |
| 11 | göra noden till en led | ändrar | `vcNode.JointType`, `VC_JOINTTYPE_ROTATIONAL` | saknas |
| 12 | sätta ledens gränser och hastighet | ändrar | `vcJoint.MinValue`, `vcJoint.MaxValue`, `vcJoint.MaxSpeed` | saknas |
| 13 | binda leden till ett uttryck | ändrar | `vcNode.JointExpression`, `vcDof.VALUE` | saknas |
| 14 | lägga till ett servobeteende som driver leden | ändrar | `vcNode.createBehaviour`, `VC_SERVOCONTROLLER` | saknas |
| 15 | lägga till en komponentskapare eller en behållare | ändrar | `vcNode.createBehaviour`, `VC_COMPONENTCREATOR` | saknas |
| 16 | se vilka beteenden komponenten redan bär | läser | `vcComponent.Behaviours`, `vcBehaviour.Type` | `list_transport_behaviours` |
| 17 | skapa en egenskap användaren ska kunna ändra | ändrar | `vcComponent.createProperty` | saknas |
| 18 | läsa och sätta egenskapens värde | ändrar | `vcComponent.getProperty`, `vcProperty.Value` | `get_property`, `set_property` |
| 19 | lista komponentens egenskaper med typ | läser | `vcComponent.Properties` | `list_properties` |
| 20 | binda en egenskap till ett uttryck som bygger om geometrin | ändrar | `vcProperty.OnChanged`, `vcComponent.rebuild` | saknas |
| 21 | rita ett gränssnitt komponenten kan kopplas med | ändrar | `vcSimInterface.createSection`, `VC_ONETOONEINTERFACE` | saknas |
| 22 | lägga fält i gränssnittets sektion | ändrar | `vcSimInterfaceSection.createField` | saknas |
| 23 | sätta gränssnittets toleranser för plug and play | ändrar | `vcSimInterface.DistanceTolerance`, `vcSimInterface.AngleTolerance` | saknas |
| 24 | läsa tillbaka gränssnittet och pröva en koppling | läser | `vcSimInterface.canConnect` | `interface_info`, `can_connect` |
| 25 | sätta en fysikkollider på geometrin | ändrar | `vcFeature.PhysicsCollider`, `VC_PHYSICSCOLLIDER_PRECISE` | saknas |
| 26 | skriva ett skriptbeteende inne i komponenten | ändrar | `vcScript.Script`, `VC_PYTHONSCRIPT` | saknas |
| 27 | slå upp API-namnet innan skriptet skrivs | läser | `TJÄNST:api_index` | `lookup_api`, `search_api`, `type_surface`, `lookup_helper` |
| 28 | bygga om komponenten efter en ändring | ändrar | `vcComponent.rebuild` | saknas |
| 29 | göra komponenten unik så ändringen inte smittar | ändrar | `vcComponent.makeUnique`, `vcComponent.IsUnique` | saknas |
| 30 | höja revisionen | ändrar | `vcComponent.incrementRevision` | saknas |
| 31 | märka komponenten med författare, tillverkare och taggar | ändrar | `vcHelpers.VcmFile.Author`, `vcHelpers.VcmFile.Manufacturer`, `vcHelpers.VcmFile.Tags` | saknas |
| 32 | spara komponenten som `.vcm` | ändrar | `vcComponent.save`, `vcHelpers.VcmFile.write` | saknas |
| 33 | pröva den färdiga komponenten i en layout | ändrar | `vcApplication.load` | `load_component` |

**Rättelse mot den tidigare versionen av den här filen.** Steg 1 stod förr som
`.NET/UI, inte i Python-API:t`. Det är fel: `vcCommand.loadGeometryAsComponent`
finns i indexet. Steget är alltså inom
räckhåll och bara obyggt. Det var precis den sortens falska undantag fas 19:s
grind byggdes för att fälla, och den fällde det i sin egen källa.

---

## P7 — Utbildaren

Visar systemet för någon annan och låter dem prova. Delade förr rad med P5,
men bröts ut i fas 19: att **återställa efter en elev** och att **stega**
är egna arbetssteg som säljaren aldrig gör.

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | öppna en förberedd övningslayout | ändrar | `vcApplication.load` | saknas |
| 2 | visa vad som står i layouten | läser | `vcApplication.Components` | `list_components` |
| 3 | spara utgångsläget innan eleven rör något | ändrar | `vcSimulation.setInitialState` | `sim_initial_state` |
| 4 | köra en kort bit och stanna | ändrar | `vcSimulation.run`, `vcSimulation.halt` | `sim_run`, `sim_halt` |
| 5 | sänka farten så rörelsen går att följa | ändrar | `vcSimulation.SimSpeed` | `sim_speed` |
| 6 | stega scenen ett steg i taget | ändrar | `vcSimulation.update` | `sim_step` |
| 7 | läsa klockan för att visa takten | läser | `vcSimulation.SimTime` | `sim_state` |
| 8 | visa vad en signal gör genom att sätta den för hand | ändrar | `vcBoolSignal.Value` | `set_signal` |
| 9 | visa vilka signaler cellen har | läser | `vcSignal.Type` | `list_signals` |
| 10 | visa robotens leder och gränser | läser | `vcJoint.MinValue`, `vcJoint.MaxValue` | `robot_limits` |
| 11 | jogga roboten för hand för att visa arbetsrymden | ändrar | `vcApplication.startJogging` | saknas |
| 12 | visa en rutin sats för sats | läser | `vcRoutine.Statements` | `read_routine` |
| 13 | stega rutinen så eleven ser varje sats | ändrar | `vcExecutor.callStatement` | `step_statement` |
| 14 | låta eleven prova och sedan återställa allt | ändrar | `vcSimulation.restoreInitialState`, `vcSimulation.reset` | `sim_initial_state`, `sim_reset` |
| 15 | visa en krock med flit och peka på den | ändrar | `vcCollisionDetector.testAllCollisions` | `test_collision` |
| 16 | mäta ett avstånd inför klassen | läser | `vcNode.measureDistance` | `measure_distance` |
| 17 | skriva en förklarande not i scenen | ändrar | `vcAnnotation.Text` | saknas |
| 18 | visa ett meddelande i rutan | ändrar | `vcApplication.messageBox` | saknas |
| 19 | visa statistiken efter körningen | läser | `vcStatistics.Utilization` | `station_state_times` |
| 20 | spela in en genomgång att lämna ut | ändrar | `vcApplication.RecordScreen` | saknas |
| 21 | ta en bild till kursmaterialet | ändrar | `vcApplication.saveBitmap` | saknas |
| 22 | dela ut övningen som ett paket | ändrar | `vcPackFolder.mapFolder` | saknas |
| 23 | gå igenom gränssnittets menyer med eleven | läser | `UI:Menyfliksområdet` | UI |

Den gamla filen påstod att utbildaren *"kräver inte en enda ytterligare
API-yta"*. Det påståendet går nu att pröva mekaniskt, och grinden rapporterar
hur många av P7:s API-namn som **inte** finns i P5.

---

## Vad profilerna säger om byggordningen

| Domän | P1 | P2 | P3 | P4 | P5 | P6 | P7 | Antal profiler |
|---|---|---|---|---|---|---|---|---|
| scen | ●● | ● | ● | ● | ●● | ●● | ● | 7 |
| simulering | ● | ●● | ●● | ●● | ●● | · | ●● | 6 |
| mätning | ●● | ●● | ● | · | ● | ● | ● | 6 |
| komposition | ●● | · | ● | ● | ●● | ●● | · | 5 |
| robot + kinematik | · | ●● | ● | ● | ● | ● | ● | 6 |
| program | · | ●● | ● | ● | · | · | ● | 4 |
| signal | · | ● | ●● | ● | · | ● | ● | 5 |
| statistik | · | · | ● | ●● | ●● | · | ● | 4 |
| process + produkt | · | · | ● | ●● | ● | · | · | 3 |
| vy + utseende | ● | · | · | · | ●● | ● | ● | 4 |
| geometri | · | · | · | · | · | ●● | · | 1 |
| flöde + transport | ● | · | ● | ●● | ● | ● | · | 5 |

`●●` = profilen kan inte arbeta utan domänen. `●` = använder den.

Två avläsningar, och de pekar åt olika håll:

1. **Bredast nytta**: scen, simulering och mätning rör alla sju profiler.
2. **Störst orörd yta**: geometri, process, produkt och statistikens skrivsida.

Byggordningen i `47_verktygstackning.md` väger den första avläsningen tyngre i
de tidiga rundorna och den andra tyngre i de sena.

## Vad den här filen INTE säger

* **Stegen är inte viktade.** Att spara en layout och att bygga ett helt
  processflöde räknas som ett steg var. Täckningen är alltså ett antal steg,
  inte ett antal timmar, och den som läser talet som "andel av arbetet" läser
  in en viktning som inte är mätt.
* **`UI:`-markörerna är bara halvt kontrollerade.** Grinden kan bevisa att en
  `UI`-markör är **falsk** (namnet finns i Python-API:t), men den kan inte
  bevisa att den är **sann** — en påhittad `UI:`-token passerar. Den öppna
  riktningen är den ofarliga: den kan bara göra nämnaren större.
* **Profilerna är sju, inte alla.** En underhållstekniker, en
  säkerhetsansvarig och en inköpare finns inte här. Det är en verklig gräns i
  nämnaren, och den kan bara rättas genom att skriva fler profiler — golvet i
  `personatackning.py` hindrar bara att de befintliga krymper.
