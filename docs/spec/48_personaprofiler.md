# Personaprofiler

Sex förenklade profiler för **vem som använder Visual Components och vad de
vill åstadkomma**. Underlag för täckningsanalysen i `47_verktygstackning.md`,
inte en marknadsbeskrivning.

Regeln som styrde urvalet: **en profil får bara bära arbetssteg som går att
peka ut i den mätta API-ytan.** Varje rad i kolumnen "Kräver" är ett namn ur
`docs/referens/vc_api/` som kontrollerats mot indexet i
`svc/vc_assist_svc/api_index.py`. Ett arbetssteg utan API-yta står kvar i
profilen men märks **UI** eller **.NET**, för det säger något viktigt: det är
arbete användaren gör i programmet och som agenten inte kan göra åt hen.

Kolumnen "Täckt idag" hänvisar till de 21 verktyg som är byggda
(`svc/vc_assist_svc/verktyg/`, domänerna `scene` 15 och `composition` 6).

---

## P1 — Layoutplaneraren

Bygger en fabrikslayout av färdiga komponenter. Frågar "får det plats,
krockar det, hur långt är det mellan stationerna".

| # | Steg | Kräver | Täckt idag |
|---|---|---|---|
| 1 | öppna eller börja en layout | `vcApplication.load`, `vcApplication.createLayout`, `vcApplication.clearWorld` | delvis |
| 2 | hitta en komponent i katalogen | **saknas i Python-API:t** (se `47`, gränsen) | nej |
| 3 | placera komponenten | `vcApplication.load`, `vcNode.PositionMatrix` | `load_component`, `set_transform` |
| 4 | koppla ihop med grannen | `vcSimInterface.canConnect`, `vcSimInterface.connect` | `can_connect`, `connect` |
| 5 | mönstra ut, klona rader | `vcComponent.clone`, `vcMatrix.translateRel` | `clone_component` |
| 6 | mäta avstånd och gångar | `vcNode.measureDistance`, `vcCollisionDetector.testMinimumDistance` | nej |
| 7 | kollisionskoll | `vcCollisionDetector.testAllCollisions`, `getHitNodeA` | nej |
| 8 | lager, färg, synlighet | `vcApplication.createLayer`, `vcLayer.Visibility`, `vcNode.NodeVisible` | nej |
| 9 | måttsätta och kommentera | `vcApplication.createLayoutItem`, `vcDimension.Node1`, `vcAnnotation.Text` | nej |
| 10 | spara och rapportera stycklista | `vcApplication.save`, `vcComponent.BOM`, `vcComponent.BOMname` | `save_layout` |

Detta är den profil de 21 byggda verktygen ligger närmast. Det som fattas
mest är mätningen (steg 6–7) och katalogen (steg 2).

---

## P2 — Robotprogrammeraren

Lär en robot en bana, kontrollerar räckvidd och konfiguration, mäter cykeltid.

| # | Steg | Kräver | Täckt idag |
|---|---|---|---|
| 1 | hitta roboten och dess styrenhet | `vcComponent.findBehavioursByType`, `VC_ROBOTCONTROLLER` | `find_component` |
| 2 | läsa leder och gränser | `vcRobotController.Joints`, `vcJoint.MaxValue`, `vcJoint.MaxSpeed` | nej |
| 3 | sätta verktyg och bas | `vcRobotController.addTool`, `addBase`, `vcToolFrame.PositionMatrix` | nej |
| 4 | jogga fram till en pose | `vcApplication.startJogging`, `vcServoController.moveJoint` | nej |
| 5 | skapa ett mål | `vcRobotController.createTarget`, `vcMotionTarget.Target` | nej |
| 6 | pröva räckvidd och singularitet | `vcMotionTarget.getConfigWarnings`, `VC_MOTIONTARGET_KW_UNREACHABLE`, `vcKinObject.Solutions` | nej |
| 7 | lägga in satser i en rutin | `vcProgram.addRoutine`, `vcRoutine.addStatement`, `VC_STATEMENT_LINMOTION` | nej |
| 8 | sätta hastighet och nogrannhet per sats | `vcMotionTarget.AccuracyMethod`, `CartesianSpeed`, `JointSpeedFactor` | nej |
| 9 | grepp och släpp | `vcHelpers.Robot.pick`, `vcHelpers.Robot.place`, `VC_STATEMENT_GRASP` | nej |
| 10 | mäta cykeltid | `vcRobotController.calcMotionTime`, `vcMotionStatement.CycleTime` | nej |
| 11 | köra och se att det inte krockar | `vcSimulation.run`, `vcCollisionDetector.testAllCollisions` | nej |
| 12 | exportera till robotens eget språk | **.NET** (`IRobotConverter`), inte i Python-API:t | nej |

Den mest API-täta profilen. `vcHelpers.Robot` och `vcHelpers.Robot2` bär
55 färdiga medlemmar var för just detta arbete — plocka, placera, montera
verktyg, spela in rutiner.

---

## P3 — Driftsättningsingenjören (virtual commissioning)

Kopplar scenen till styrsystemet och letar tidsfel, sekvensfel och förreglingar.

| # | Steg | Kräver | Täckt idag |
|---|---|---|---|
| 1 | inventera signaler i cellen | `vcComponent.Behaviours`, `VC_BOOLEANSIGNAL`, `vcSignal.Type` | nej |
| 2 | läsa och sätta signalvärde | `vcBoolSignal.Value`, `vcBoolSignal.signal` | nej |
| 3 | koppla signal till signal | `vcSignal.connect`, `vcSignal.Connections` | nej |
| 4 | läsa signalkartan mot omvärlden | `vcBooleanSignalMap.Ports`, `getConnectedExternalSignals`, `getPortName` | nej |
| 5 | koppla mot PLC | **.NET** (`VisualComponents.Connectivity.Core.IServerHandler`, `Connectivity.OpcUA.IOpcUAServer`). VC är alltid **klient** | nej — går via `plc`-domänen och OpenPLC |
| 6 | köra och följa flanker på samma tidsaxel | `vcSimulation.SimTime`, `vcSignal.OnValueChange`, `vcSimulation.update` | nej |
| 7 | avbryta på krock | `vcCollisionDetector.StopOnCollision`, `vcSimulation.autoHalt` | nej |
| 8 | återställa till utgångsläge mellan försök | `vcSimulation.setInitialState`, `restoreInitialState`, `vcSimulation.reset` | nej |

Detta är den profil som projektets egen bänk (`83_scenarier.md`) är byggd
för. **Steg 5 finns inte i Python-API:t** — sökning på "connectivity",
"opc" och "plc" i indexet ger noll träffar. Vägen dit är OpenPLC som
OPC UA-server och VC:s eget Connectivity-plugin, konfigurerat i
gränssnittet, precis som `30_arkitektur.md` redan beskriver.

---

## P4 — Simuleringsingenjören / produktionsanalytikern

Kör produktionsflöde, mäter genomströmning, utnyttjande och flaskhalsar.

| # | Steg | Kräver | Täckt idag |
|---|---|---|---|
| 1 | definiera produkttyper | `vcProductTypeManager.createProductType`, `vcProductType.ComponentUri` | nej |
| 2 | sätta upp inflöde | `vcProductCreator.FeedMode`, `vcProductCreatorTableMode.addRow`, `vcProductCreatorDistributionMode.addProductEntry` | nej |
| 3 | bygga processflöde | `vcProcessFlowGroupManager.createGroup`, `vcProcessFlowTable.createSequence`, `vcProcessSequence.addProcessGroup` | nej |
| 4 | beskriva vad varje station gör | `vcProcessExecutor.addProcess`, `vcProcessRoutine.addStatement`, `VC_STATEMENT_WORK` | nej |
| 5 | koppla ihop transporterna | `vcTransportSystem.createTransportLink`, `findSolution` | nej |
| 6 | ställa uppvärmning och körlängd | `vcSimulation.SimWarmupTime`, `vcSimulation.SimulationRunTime`, `setFastScheduling` | nej |
| 7 | köra snabbt, många gånger | `vcSimulation.run`, `vcSimulation.IsLooping`, `vcApplication.getRandomSeed` | nej |
| 8 | läsa utnyttjande per station | `vcStatistics.Utilization`, `getPercentage`, `BlockedPercentage` | nej |
| 9 | läsa genomströmning | `vcStatistics.PartsEntered`, `PartsExited`, `ComponentsAverageTime` | nej |
| 10 | rita diagram och rapport | `vcStatisticsTab.createChart`, `vcStatisticsChart.addSeries`, `vcReport.publish` | nej |

Detta är den profil som har **störst API-yta helt utan verktyg idag**:
domänerna `process` (24 typer), `produkt` (20 typer) och `statistik`
(7 typer, 65 metoder) är orörda.

---

## P5 — Lösningsarkitekten som säljer

Bygger ett trovärdigt förslag snabbt och visar det. Utbildaren delar den
här profilen helt — hen behöver samma bilder, vyer och inspelningar och
kräver inte en enda ytterligare API-yta, därför är hen ingen egen profil.

| # | Steg | Kräver | Täckt idag |
|---|---|---|---|
| 1 | bygga layouten grovt | samma som P1 | delvis |
| 2 | få den att röra sig | `vcSimulation.run`, `vcProductCreator.FeedMode` | nej |
| 3 | sätta kameror och vyer | `vcApplication.createView`, `vcApplication.useView`, `vcCamera.Matrix` | nej |
| 4 | material och ljus | `vcApplication.createMaterial`, `vcMaterial.Diffuse`, `vcApplication.createLight` | nej |
| 5 | ta bilder | `vcApplication.beginFrameGrab`, `executeFrameGrab` | nej |
| 6 | spela in film eller PDF | `vcApplication.RecordScreen`, `RecordingFileName`, `PdfRecord`, `VC_RECORDER_VIDEO` | nej |
| 7 | siffror att sätta i offerten | `vcStatistics.Utilization`, `vcRobotController.calcMotionTime` | nej |
| 8 | leverera paketet | `vcApplication.save`, `vcPackFolder.mapFolder` | `save_layout` |

Steg 5 är dessutom **ögats** råvara (`40_ogat.md`): bildfångst är samma yta
oavsett om mottagaren är en kund eller en grind.

---

## P6 — Komponentbyggaren

Gör en egen komponent av en CAD-modell: geometri, leder, gränssnitt,
beteenden, egenskaper.

| # | Steg | Kräver | Täckt idag |
|---|---|---|---|
| 1 | importera CAD | **.NET/UI** (`VisualComponents.Create3D.ICADReader`), inte i Python-API:t | nej |
| 2 | rensa och förenkla mesh | `vcTriangleSet.decimate`, `mergePoints`, `convexHull` | nej |
| 3 | bygga nodträd | `vcNode.createNode`, `vcNode.attach`, `VC_NODE_ADD_LAST_CHILD` | delvis (`list_nodes`, `find_node`) |
| 4 | sätta leder | `vcNode.JointType`, `VC_JOINTTYPE_ROTATIONAL`, `vcDof.VALUE`, `vcJoint.MinValue` | nej |
| 5 | lägga till beteenden | `vcNode.createBehaviour`, `VC_SERVOCONTROLLER`, `VC_COMPONENTCREATOR` | nej |
| 6 | skapa egenskaper och uttryck | `vcComponent.createProperty`, `vcProperty.Value`, `vcNode.JointExpression` | `get_property`, `set_property`, `list_properties` |
| 7 | rita gränssnitt | `vcSimInterface.createSection`, `vcSimInterfaceSection.createField`, `VC_ONETOONEINTERFACE` | delvis (`list_interfaces`, `interface_info`) |
| 8 | fysikkollider | `vcFeature.PhysicsCollider`, `VC_PHYSICSCOLLIDER_PRECISE` | nej |
| 9 | bygga om och göra unik | `vcComponent.rebuild`, `makeUnique`, `incrementRevision` | nej |
| 10 | märka och spara som .vcm | `vcHelpers.VcmFile.Author`, `Manufacturer`, `Tags`, `write`, `vcComponent.save` | nej |

Profilen är motiverad av mätning: `geometri` är den **enskilt största**
domänen i API:t (23 typer, 145 metoder, 132 egenskaper) och den har inget
verktyg alls idag.

---

## Vad profilerna säger om byggordningen

| Domän | P1 | P2 | P3 | P4 | P5 | P6 | Antal profiler |
|---|---|---|---|---|---|---|---|
| scen | ●● | ● | ● | ● | ●● | ●● | 6 |
| simulering | ● | ●● | ●● | ●● | ●● | · | 5 |
| mätning | ●● | ●● | ● | · | · | ● | 4 |
| komposition | ●● | · | ● | ● | ● | ●● | 5 |
| robot + kinematik | · | ●● | ● | ● | · | ● | 4 |
| program | · | ●● | ● | ● | · | · | 3 |
| signal | · | ● | ●● | ● | · | ● | 4 |
| statistik | · | · | ● | ●● | ●● | · | 3 |
| process + produkt | · | · | ● | ●● | ● | · | 3 |
| vy + utseende | ● | · | · | · | ●● | ● | 3 |
| geometri | · | · | · | · | · | ●● | 1 |
| flöde + transport | ● | · | ● | ●● | ● | · | 4 |

`●●` = profilen kan inte arbeta utan domänen. `●` = använder den.

Två avläsningar, och de pekar åt olika håll:

1. **Bredast nytta**: scen, simulering, mätning och komposition rör alla sex
   profiler. Två av fyra är byggda.
2. **Störst orörd yta**: process, produkt, statistik och geometri. De bär
   tillsammans 74 av 204 typer och rör tre av sex profiler var.

Byggordningen i `47_verktygstackning.md` väger den första avläsningen
tyngre i de tidiga rundorna och den andra tyngre i de sena.
