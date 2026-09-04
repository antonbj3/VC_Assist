# M-15 — vilka beteenden som faktiskt går att skapa

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Metod:** varje `VC_*`-konstant i skriptets scope prövades med
`comp.createBehaviour(konstant, "b")` på en **egen färsk komponent**, som revs
efteråt. 244 konstanter prövade.

## Ett metodfel först, som är värt mer än resultatet

Första svepet prövade fel 244 konstanter. Jag filtrerade på `isinstance(v, int)`
i tron att konstanterna var heltal. **Alla 429 heltalskonstanter kastade
`ReferenceError`** — och det såg ut som ett resultat.

VC:s beteendetyper är inte heltal. De är egna objekt (`VC_ONETOONEINTERFACE`
serialiseras som `rSimInterface`). De låg i den hög mitt filter hoppade över.

Ett svep som ger noll träffar på 429 prov är inte en mätning av frånvaro. Det är
oftare ett fel i urvalet.

## Resultat: 80 av 244 går att skapa

| Utfall | Antal |
|---|---|
| skapar ett beteende | **80** |
| returnerar `None` | 164 |
| kastar | 0 |

De 164 som ger `None` är lägen, flaggor, satstyper och egenskapstyper — alltså
konstanter som inte är beteendetyper. `createBehaviour` **kastar inte** på dem;
den returnerar tyst `None`. Kod som inte kontrollerar returvärdet får därför ett
`AttributeError` långt senare, på en helt annan rad.

### transport och flode (15)

| Konstant | Python-typ |
|---|---|
| `VC_BUCKETPATH` | `vcContainer` |
| `VC_CAPACITYCONTROLLER` | `vcCapacityController` |
| `VC_COMPONENTFLOWPROXY` | `vcComponentFlowProxy` |
| `VC_COMPONENTPATHSENSOR` | `vcBehaviour` |
| `VC_ONEDIRECTIONALPATH` | `vcOneDirectionalPath` |
| `VC_ONEWAYPATH` | `vcMotionPath` |
| `VC_PHYSICSPATH` | `vcContainer` |
| `VC_POSITIONPATH` | `vcBehaviour` |
| `VC_PYTHONTRANSPORTCONTROLLER` | `vcPythonTransportController` |
| `VC_ROUTINGRULE` | `vcRoutingRule` |
| `VC_TRANSPORT` | `vcTransport` |
| `VC_TRANSPORTNODE` | `vcTransportNode` |
| `VC_TWODIRECTIONALPATH` | `vcTwoDirectionalPath` |
| `VC_TWOWAYPATH` | `vcMotionPath` |
| `VC_VEHICLE` | `vcSimVehicle` |

### behallare och skapare (8)

| Konstant | Python-typ |
|---|---|
| `VC_BASECONTAINER` | `vcBaseContainer` |
| `VC_COMPONENTCONTAINER` | `vcComponentContainer` |
| `VC_COMPONENTCREATOR` | `vcComponentCreator` |
| `VC_CONTAINERFILLER` | `vcFlow` |
| `VC_PATTERNCONTAINER` | `vcPatternContainer` |
| `VC_PHYSICSCONTAINERII` | `vcComponentContainer` |
| `VC_PRODUCTCREATOR` | `vcProductCreator` |
| `VC_TOOLCONTAINER` | `vcToolContainer` |

### robotik (16)

| Konstant | Python-typ |
|---|---|
| `VC_ARTICULATEDKINEMATICS` | `vcBehaviour` |
| `VC_ARTICULATEDKINEMATICS2` | `vcBehaviour` |
| `VC_CARTESIANKINEMATICS` | `vcBehaviour` |
| `VC_COMPONENTGRABBER` | `vcBehaviour` |
| `VC_DELTAKINEMATICS` | `vcBehaviour` |
| `VC_JOGINFO` | `vcJogInfo` |
| `VC_KINEMATICS` | `vcKinematics` |
| `VC_PARALLELLOGRAMKINEMATICS` | `vcBehaviour` |
| `VC_PYTHONKINEMATICS` | `vcKinematics` |
| `VC_ROBOTCONTROLLER` | `vcRobotController` |
| `VC_ROBOTEXECUTOR` | `vcExecutor` |
| `VC_RRSROBOTCONTROLLER` | `vcRrsRobotController` |
| `VC_RSLEXECUTOR` | `vcRslProgramExecutor` |
| `VC_SCARAKINEMATICS` | `vcBehaviour` |
| `VC_SCARAKINEMATICS2` | `vcBehaviour` |
| `VC_SERVOCONTROLLER` | `vcServoController` |

### signaler (10)

| Konstant | Python-typ |
|---|---|
| `VC_BEHAVIOURSIGNAL` | `vcSignal` |
| `VC_BOOLEANSIGNAL` | `vcBoolSignal` |
| `VC_BOOLEANSIGNALMAP` | `vcBooleanSignalMap` |
| `VC_COMPONENTSIGNAL` | `vcComponentSignal` |
| `VC_FRAMESIGNAL` | `vcSignal` |
| `VC_INTEGERSIGNAL` | `vcIntegerSignal` |
| `VC_MATRIXSIGNAL` | `vcMatrixSignal` |
| `VC_REALSIGNAL` | `vcRealSignal` |
| `VC_REALSIGNALMAP` | `vcBehaviour` |
| `VC_STRINGSIGNAL` | `vcStringSignal` |

### granssnitt (2)

| Konstant | Python-typ |
|---|---|
| `VC_ONETOMANYINTERFACE` | `vcSimInterface` |
| `VC_ONETOONEINTERFACE` | `vcSimInterface` |

### process (7)

| Konstant | Python-typ |
|---|---|
| `VC_ACTIONCONTAINER` | `vcActionContainer` |
| `VC_PROCESSCONTROLLER` | `vcProcessController` |
| `VC_PROCESSEXECUTOR` | `vcProcessExecutor` |
| `VC_PROCESSPOINT` | `vcProcessPointSensor` |
| `VC_PROCESSRESOURCEBROKER` | `vcBehaviour` |
| `VC_PYTHONPROCESSHANDLER` | `vcPythonProcessHandler` |
| `VC_PYTHON_PROCESS_HANDLER` | `vcPythonProcessHandler` |

### sensorer (3)

| Konstant | Python-typ |
|---|---|
| `VC_LIDARSENSOR` | `vcBehaviour` |
| `VC_RAYCASTSENSOR` | `vcBehaviour` |
| `VC_VOLUMESENSOR` | `vcBehaviour` |

### fysik (8)

| Konstant | Python-typ |
|---|---|
| `VC_PHYSICSCONTACTMODIFIER` | `vcBehaviour` |
| `VC_PHYSICSENTITY` | `vcBehaviour` |
| `VC_PHYSICSJOINTD6` | `vcBehaviour` |
| `VC_PHYSICSJOINTDISTANCE` | `vcBehaviour` |
| `VC_PHYSICSJOINTPOINTONLINE` | `vcBehaviour` |
| `VC_PHYSICSJOINTPOINTONPLANE` | `vcBehaviour` |
| `VC_PHYSICSJOINTPRISMATIC` | `vcBehaviour` |
| `VC_PHYSICSJOINTREVOLUTE` | `vcBehaviour` |

### ovrigt (11)

| Konstant | Python-typ |
|---|---|
| `VC_BOOLEANPROPERTYCREATOR` | `vcFlow` |
| `VC_DOCUMENTLINK` | `vcBehaviour` |
| `VC_INTEGERPROPERTYCREATOR` | `vcFlow` |
| `VC_NODELIST` | `vcNodeList` |
| `VC_NOTE` | `vcBehaviour` |
| `VC_PARTICLESYSTEM` | `vcBehaviour` |
| `VC_PYTHONSCRIPT` | `vcScript` |
| `VC_REALPROPERTYCREATOR` | `vcFlow` |
| `VC_SCRIPT` | `vcScript` |
| `VC_STATISTICS` | `vcStatistics` |
| `VC_STRINGPROPERTYCREATOR` | `vcFlow` |

## Vad det betyder

Det här är grunden för verktygsbiblioteket. Varje domän vi ska bygga —
transport, robotik, signaler, process, sensorer — har nu en **mätt** lista över
vad som existerar, i stället för en gissning ur dokumentationen.

Särskilt: `VC_TRANSPORT` ger en `vcTransport`, och det är den mest lovande
kandidaten till den `Ref<ComponentProcessor>` som ett transportfält vill bindas
till (M-14). Oprövat än.

`VC_CONVEYORTRANSPORTCONTROLLER`, `VC_INTERPOLATINGTRANSPORTCONTROLLER`,
`VC_TRANSPORTCONTROLLER`, `VC_CONTAINER` och `VC_FLOW` ger alla `None` — de går
alltså **inte** att skapa direkt, trots att de heter som beteenden.

## Sidofynd

Svepet skapade och rev 244 komponenter i följd. Bryggan dog under nästa körning.
Orsaken är omätt, men mängden scenändringar är den rimliga misstanken, och den
hör ihop med M-13: vissa scenoperationer stoppar simuleringen.

## Vad som INTE är mätt

* De 80 träffarna är mätta som *"`createBehaviour` returnerade ett objekt"*. Att
  ett enda av de 80 beteendena **fungerar** i en simulering är inte prövat här.
* De 164 som ger `None` är mätta som icke-skapbara **med ett argumentlöst anrop**
  på en färsk komponent. Att någon av dem går att skapa på annat sätt är inte
  uteslutet, och `VC_TRANSPORTCONTROLLER` hör till dem som därför avfärdades.
* Urvalet är de `VC_*`-konstanter som fanns i **skriptets** scope. Konstanter som
  bara finns i andra scope ingår inte, och M-01 mätte att scopen skiljer sig.
  Talet 244 är alltså 244 av ett okänt totalantal.
* Metodfelet är rättat för heltalsfiltret. Att det **nya** urvalet är komplett är
  inte visat — samma fråga som fällde det första svepet är inte ställd om det
  andra, och ett svep som ger noll träffar är oftare ett fel i urvalet.
* Att svepet dödade bryggan i nästa körning står som omätt orsak. Mätningen
  skiljer inte 244 skapade komponenter från 244 raderade, och inte heller något
  av de 80 skapade beteendenas egna biverkningar, som ingen har mätt.
* `VC_TRANSPORT` som kandidat till `Ref<ComponentProcessor>` är märkt oprövad i
  texten. M-16 prövade den, och bindningen visade sig ogiltig (M-37) — kandidaten
  var alltså fel, och det syntes inte förrän två mätningar senare.
* Python-typen i högerkolumnen är läst av typnamnet på det returnerade objektet.
  Att `vcBehaviour` för femton av träffarna betyder samma sak i alla femton fall
  är inte mätt.
