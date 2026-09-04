# 49 — Komponentmodellen: hur en komponent kan koppla ihop sig

Status: **härledd ur dokumentationen, inte mätt**. Skriven 2026-09-04 medan
operatören mäter i den enda VC-instansen. Varje påstående bär en av tre
märkningar:

| Märkning | Betyder |
|---|---|
| **BELAGT** | står ordagrant i en källfil under `docs/referens/`; citatet och filen står vid påståendet |
| **MÄTT** | mätt av operatören i en körande VC 4.10 (uppdraget 2026-09-04, punkt 1–9) |
| **HYPOTES** | härledd ur källorna, inte prövad. Rangordnad: rang 1 prövas först |

Hypoteserna har id (A1, B2 …) och ligger som **data** i
`svc/vc_assist_svc/byggrecept/hypoteser.py`. Recepten i `recept.py` provar dem
i rangordning vid körning och bokför utfallet per id i svaret. Testet
`tests/enhet/test_byggrecept.py` faller om ett id i koden saknas här eller om
ett VC-namn i en hypotes inte finns i `api_index`.

Källförkortningar: `api.xml` = `docs/referens/vc_api/api.xml` (Python-API:t,
samma innehåll som `vc_python_api.json`), `constants.xml` =
`docs/referens/vc_api/constants.xml`, `Create3D` =
`docs/referens/vc_dotnet/Create3D.Shared.xml` (.NET-lagret bakom Python).

---

## 0. Det korta svaret

Det som saknats är inte ett beteende utan en **bindning**. Ett gränssnitt
kopplar inte komponenter — det kopplar det som dess **fält pekar på**. Ett
flödesfält pekar på en **kontakt** (`vcConnector`) i ett flödesbeteende, och
en koppling av två gränssnitt kopplar ut-kontakten i den ena banan till
in-kontakten i den andra. Ett fält vars referens är `None` pekar på ingenting,
och två ingenting kan inte matcha. Det är hypotes **E2** för varför
`canConnect` gav False i alla nio mätta uppställningar, och det styrs av om
referensen alls går att sätta från Python (fråga B).

Kedjan som ska byggas, per komponent:

```
vcComponent (nod)
 ├─ RootFeature
 │   ├─ VC_BLOCK   "Kropp"      geometri, valfri
 │   ├─ VC_FRAME   "PathIn"     ram: var banan börjar och var in-sektionen sitter
 │   └─ VC_FRAME   "PathOut"    ram: var banan slutar och var ut-sektionen sitter
 ├─ VC_ONEWAYPATH  "Path"       vcMotionPath = vcFlow + vcContainer; Path = [PathIn, PathOut]
 │     Connectors: [Input-kontakt, Output-kontakt]       ← hypotes C1
 ├─ VC_ONETOONEINTERFACE "InInterface"
 │   └─ Section "InInterface"  Frame = PathIn
 │       └─ VC_FLOWFIELD "Flow"  Port → Input-kontakten   ← bindningen, fråga B
 └─ VC_ONETOONEINTERFACE "OutInterface"
     └─ Section "OutInterface" Frame = PathOut
         └─ VC_FLOWFIELD "Flow"  Port → Output-kontakten
```

Koppling: `bana1.OutInterface.connect(bana2.InInterface)`, eller
`app.connectComponents(bana1, bana2)`.

---

## 1. Byggstenarna, med belägg

### 1.1 Nod, komponent, feature

| Begrepp | Python | Belägg |
|---|---|---|
| Komponent | `vcComponent`, ärver `vcNode` | api.xml, `vcComponent` `<parents>vcNode</parents>` |
| Skapa tom komponent | `app.createComponent()` | api.xml `vcApplication.createComponent`: *"Creates a new component at the 3D world origin, and then returns the new component."* |
| Feature-träd | `node.RootFeature` | api.xml `vcNode.RootFeature`: *"Gets the root feature of node."* |
| Ny feature | `feature.createFeature(type, name)` | api.xml `vcFeature.createFeature`: *"Adds a new feature of a given type and name as a child of this feature. See Feature Constants for more information."* |
| Ram | `VC_FRAME` → `vcFrameFeature` (ärver `vcFeature`) | constants.xml `VC_FRAME`; Create3D `FeatureType.Frame`: *"Frame object"*; `IFrameFeature`: *"The Frame feature describes a position and orientation in the 3D world. Frames are used as "glue" between the physical and the simulation world, for instance to outline conveyor paths."* |
| Placera feature | `feature.PositionMatrix` (RW) | api.xml `vcFeature.PositionMatrix`: *"Defines the position matrix of this feature relative to its parent feature's coordinate system."* |
| Beteende | `node.createBehaviour(type, name)` | api.xml `vcNode.createBehaviour`: *"Creates a new behavior of a given type and name in node. See Behavior Constants for more information."* |

**BELAGT om konstanterna:** `constants.xml` är en platt lista med 709 namn
och **inga beskrivningar** (filen består av `<CONSTANTS>` följt av namnen).
Vad en konstant betyder går bara att läsa ur .NET-uppräkningarna med samma
namn: `BehaviorType`, `SimInterfaceFieldType`, `ConnectorType`,
`FeatureType` i Create3D. Det är därför .NET-filerna citeras för semantik
fast koden är Python.

### 1.2 Flöde, behållare, kontakt

| Begrepp | Python | Belägg |
|---|---|---|
| Flödesbeteende | `vcFlow`: `Connectors`, `ConnectorCount`, `CapacityAvailable` | api.xml `vcFlow.Connectors`: *"Gets a list of connectors in flow object."*; Create3D `IFlowBehavior`: *"A base interface for behaviors supporting material flow."* |
| Behållare | `vcContainer` (ärver `vcFlow`): `Capacity`, `Components`, `ContentVisible` | api.xml `vcContainer.Capacity`: *"Defines the maximum number of components that can be stored in the container at any given time."*; `ContentVisible` (W): *"Sets the visibility of components stored in the container."* |
| Bana | `vcMotionPath` ärver **både** `vcFlow` och `vcContainer` | api.xml `vcMotionPath` `<parents>vcBehaviour vcFlow vcContainer</parents>` (rad 7894); `vcComponent.Container`: *"Container refers to a behavior that can store components, for example a One Way Path."* |
| Banans väg | `Path` = ordnad lista ramar | api.xml `vcMotionPath.Path`: *"Defines an ordered list of Frame features referenced as waypoints of path. If set, path is calculated based on its interpolation mode."* |
| Kontakt | `vcConnector`: `Type`, `Index`, `Connection` (RW), `connect()` | api.xml `vcConnector.Type`: *"Defines the connector's type. That is, whether the connector is an Input, Output or Input/Output type port."*; `Connection`: *"Defines connector that the connector is connected to in a component. If no connection, the value is None."*; `connect`: *"Connects the connector to a given connector. If no argument is given, this method will remove all connections of the connector."* |
| Kontakttyper | `VC_CONNECTOR_INPUT`, `VC_CONNECTOR_OUTPUT`, `VC_CONNECTOR_INPUT_OUTPUT` | constants.xml; Create3D `ConnectorType.Input`: *"Connector used to accept material flow."*, `Output`: *"Connector used as output."* |
| Vad en kontakt är till för | | Create3D `ISimConnector`: *"Interface defining a connection port. Used to implement material flow between containers."* |
| Överföring i kod | `comp.transfer(behaviour, port)` | api.xml `vcComponent.transfer`: *"A given behavior must be or derive from vcFlow and you should check for available capacity."* |

### 1.3 Gränssnitt, sektion, fält

| Begrepp | Python | Belägg |
|---|---|---|
| Gränssnitt | `VC_ONETOONEINTERFACE` → `vcSimInterface` | **MÄTT** (punkt 1); Create3D `BehaviorType.OneToOneInterface` |
| Sektion | `iface.createSection(name)` → `vcSimInterfaceSection` | api.xml: *"Adds a new section of a given name to interface, and then returns the new section."* **MÄTT** (punkt 2): utan argument returnerar bindningen `None`. Stämmer med Create3D `ISimInterface.CreateSection`: *"Thrown when name is null or empty"* — py2-bindningen sväljer .NET-undantaget och ger `None`. |
| Sektionens ram | `section.Frame` (RW, `vcFeature`) | api.xml: *"If belonging to physical interface, defines the Frame feature referenced as the location of section."*; Create3D `ISimInterfaceSection.Frame`: *"Thrown when feature is not of type IFrameFeature."* |
| Fält | `section.createField(type, name)` → `vcSimInterfaceField` | api.xml: *"Creates a new field of a given type and name in section, and then returns the new field. See Interface Constants for more information."* **MÄTT** (punkt 3). |
| Fältets yta i Python | `Index`, `Name`, `Properties`, `Section`, `Type` — **inget annat** | api.xml `vcSimInterfaceField` (fem egenskaper, inga metoder) |
| Fältordning | | api.xml `vcSimInterfaceField.Index`: *"Important: The order of fields in a section is evaluated when establishing a connection between sections. For example, sections may have compatible fields but cannot connect because the order of fields differ in each section."* |
| Fälttyper | `VC_FLOWFIELD`, `VC_TRANSPORTFIELD`, `VC_SIGNALFIELD`, `VC_HIERARCHYFIELD`, `VC_PROCESSORFIELD`, `VC_ATTACHMENTFIELD`, `VC_ACTIONFIELD`, `VC_INTEGERCOMPATIBILITYFIELD`, `VC_RSLFIELD`, `VC_BASEEXPORTFIELD`, `VC_JOINTEXPORTFIELD`, `VC_TOOLEXPORTFIELD` | constants.xml; Create3D `SimInterfaceFieldType`: *"Interface field types. These correspond to classes inheriting from ISimInterfaceField interface."* med medlemmarna Flow, Transport, Signal, Hierarchy, Processor, Attachment, Action, IntegerCompatibility, Rsl, BaseExport, JointExport, ToolExport |
| Abstrakt / fysiskt | `IsAbstract` (RW) | api.xml: *"Defines if interface supports remote connections."*; Create3D `ISimInterface.IsLogical`: *"Determines if this is logical (i.e. not connectable by plug and play)."* |
| Toleranser | `DistanceTolerance`, `AngleTolerance` | api.xml `DistanceTolerance`: *"Defines the distance at which the interface snaps to an available connection, thereby completing Plug and Play."* **MÄTT** (punkt 9): 1e9 mm och 360° på ett nytt gränssnitt — tolerans är inte hindret. |
| Koppla | `canConnect(other)`, `connect(other[, retain_offset])` | api.xml `canConnect`: *"Returns True if a given interface can connect to the interface; otherwise, returns False."* |
| Koppla allt | `app.connectComponents(c1, c2)` | api.xml: *"Connects all matching interfaces between two given components. If a physical connection requires repositioning then comp2 is snapped to comp1."* |

### 1.4 Vad varje fälttyp pekar på — bara synligt i .NET

**BELAGT** (Create3D). Detta är kärnan i hela problemet: i .NET bär varje
fältklass en **typad referens**; i Python syns bara `Properties`.

| .NET-fält | Referens | Citat |
|---|---|---|
| `ISimInterfaceFlowField` | `Port` : `ISimConnector` | *"Field for connecting two connectors and facilitating a material flow between component containers."* `Port`: *"Gets or sets the instance of [ISimConnector] that will be connected when the interface will be connected."* |
| `ISimInterfaceTransportField` | (odokumenterad) | *"Field for connecting containers/behaviors."* — hela beskrivningen |
| `ISimInterfaceSignalField` | `Signal` | *"Field for connecting signal behaviors."* |
| `ISimInterfaceHierarchyField` | `Frame`, `Node`, `IsParent` | *"Field for connecting components hierarchically."* `IsParent`: *"If this field is the parent, the opposite side needs to be the child and vice versa."* |
| `ISimInterfaceProcessorField` | `Path`, `Sensor`, `IsParent` | *"Field for connecting process points to motion paths."* `IsParent`: *"A parent field utilizes a path behavior. A child field utilizes a sensor behavior."* |
| `ISimInterfaceAttachmentField` | `Frame`, `Node`, `IsParent` | *"Field for hierarchically attaching physical objects … mostly for physical cable attachments."* |

Mönstret: flera fälttyper är **par med roller** (parent/child, Output/Input).
Två sidor matchar när rollerna är motsatta.

### 1.5 Vad matchning betyder i .NET

**BELAGT** (Create3D):

* `ISimInterface.Connect`: *"Thrown when interface cannot be connected (it is
  one to one interface and already connected or interfaces do not match)."*
* `ISimInterface.IsCompatibleWith`: *"Checks if the given [interface] is
  compatible with this interface."*
* `ISimInterface.FindMatchingSections`: *"Finds the first [section] that
  matches the given section … Returns null if no matching sections are
  found."*
* `ISimInterfaceSection.IsCompatibleWith`: *"True if connection between these
  sections is possible. This does not check if the sections are already
  connected or not."*
* `AutoPlugFlowDirection.Downstream`: *"Connect only to the components
  defining an material flow output"*; `Upstream`: *"… defining an material
  flow input"*. Matchningsmaskineriet **vet** alltså vilket gränssnitt som är
  utflöde och vilket som är inflöde. Den kunskapen kan bara komma från
  kontaktens `Type`.

Pythons `canConnect` är rimligen `IsCompatibleWith` plus "inte redan
kopplad" (HYPOTES, men ingen annan .NET-metod passar signaturen).

---

## 2. Svaren A–G

### A. Vad är en "ComponentProcessor"?

**A0 — MÄTT.** Strängen `ComponentProcessor` förekommer **noll** gånger i alla
tio källfiler (`grep -c` över `docs/referens/vc_api/*` och
`docs/referens/vc_dotnet/*`, 2026-09-04). Ingen Python-typ, ingen
VC_-konstant och ingen .NET-typ bär det namnet. Det är ett **internt** namn
ur kärnan som läcker ut genom `vcProperty.Type`.

**A1 — HYPOTES, rang 1.** ComponentProcessor är kärnans basklass för
beteenden som *hanterar* komponenter — det som Python visar som
`vcFlow`/`vcContainer`-familjen (banor, behållare, skapare,
transportprotokoll). Transport-fältets `Transport` pekar på ett sådant
beteende och `Connection` är **portindex** i det.
Stöd: `ISimInterfaceTransportField` = *"Field for connecting
containers/behaviors"*, `ISimConnector` = *"material flow between
containers"*, `vcConnector.Index` = *"the position of the connector in its
behavior's list of connectors"*.
Följd: en `vcMotionPath` **är** då en ComponentProcessor, och mätning 5
(`SystemError` vid tilldelning) betyder inte "fel klass" utan att
**py2-bindningen saknar sättare för Ref-typade egenskaper**. Se B.

**A2 — HYPOTES, rang 2.** ComponentProcessor = transportprotokollet
`vcTransport` (`VC_TRANSPORT`, `BehaviorType.TransportProtocol`: *"A
transportation sender and target behaviour used to customize and standardize
transportation process"*). Passar ordet "Transport" i fältnamnet, men
protokollet hör till robot-/resurstransport, inte bana-till-bana.

Om `SystemError: error return without exception set`: det är CPython:s
generiska fel när en C-funktion returnerar NULL utan att sätta ett undantag
(Python-semantik, inte VC-dok). Typiskt för en sättare som saknar gren för
det värde den fick. Det skiljer **inte** mellan "fel typ" och "ingen sättare
alls" — det är exakt det B1 mäter.

### B. Hur binds ett fält till sin processor?

**B0 — BELAGT.** Se tabell 1.4. Python-ytan för `vcSimInterfaceField` är
`Index, Name, Properties, Section, Type` — inga sätt-metoder. Det finns ingen
Ref-variant av `vcProperty` i api.xml (`vcProperty.Type` hänvisar till
*Property Constants*: `VC_REAL`, `VC_STRING`, `VC_URI`, `VC_BOOLEAN`,
`VC_INTEGER` … ingen `VC_OBJECT`/`VC_REF`). Bindningen kan därför **bara** gå
via `vcProperty.Value` på fältets egenskap, om den går via Python alls.
Sektionens `Frame` är däremot en **typad** RW-egenskap (`vcFeature`) — där
finns en Python-väg för en referens, och den är inte mätt ännu.

Provordning (recepten kör alla fyra i följd tills ett värde fastnar):

| Id | Rang | Prova | Varför |
|---|---|---|---|
| **B1** | 1 | `p.Value = kontakt` — en `vcConnector` på **flödesfältets** `Port` | Den enda typ .NET säger att fältet vill ha. Mätning 5 gjordes på **Transport**-fältet med en `vcMotionPath` — en annan referenstyp på ett annat fält. |
| **B2** | 2 | `p.Value = beteendet` (banan) och sedan `Connection = kontaktens Index` | A1: Transport-fältet = beteende + portindex |
| **B3** | 3 | `p.Value = kontaktens Index` (heltal) | Om bindningen adresserar kontakten per index |
| **B4** | 4 | `p.Value = kontaktens Name` (bytesträng) | Redan MÄTT till SystemError på Transport-fältet; kvar bara för flödesfältet |
| **B5** | 5 | Hoppa över gränssnittet: `ut.connect(inn)` / `ut.Connection = inn` | api.xml `vcConnector.connect` och `Connection` (RW) sätter ingen komponentgräns. **Risk**: Create3D `ISimConnector.Connect`: *"Thrown when connector is not in this component."* Ger flöde utan gränssnitt; ingen snappning, ingen PnP i GUI:t. |
| **B6** | 6 | Sätt fälten **en gång i GUI:t**, `comp.save(uri)`, sedan `app.load` + `clone` | Om B1–B5 faller går bindningen inte via Python. |

Egenskapen `Connection = 1` (mätning 4): **E4 — HYPOTES**: portindex i det
bundna beteendet (A1). Alternativ: en riktnings-/rolluppräkning. Sonden
(recept `sondera_falt`) dumpar `Name/Type/Value` för **alla tolv** fälttyper
så att detta går att läsa av i en körning: om `VC_HIERARCHYFIELD` visar en
egenskap som motsvarar `IsParent` och `VC_FLOWFIELD` visar `Port`, faller
tolkningen ut direkt.

### C. Minsta uppsättning för en TRANSPORTÖR

**C0 — BELAGT.** `vcMotionPath` ärver `vcFlow` **och** `vcContainer`
(api.xml `<parents>`). En bana tar emot (`CapacityAvailable`, `Connectors`),
lagrar (`Capacity`, `Components`) och lämnar. Vägen är `Path`, en ordnad
lista `VC_FRAME`-features.

**C3 — HYPOTES.** Minsta uppsättning, i byggordning:

1. `app.createComponent()`; `k.Name = …`
2. `k.RootFeature.createFeature(VC_FRAME, "PathIn")` vid x=0 och
   `…(VC_FRAME, "PathOut")` vid x=längd — ramarna är både banans ändpunkter
   och sektionernas lägen (F0)
3. `k.createBehaviour(VC_ONEWAYPATH, "Path")`; `Path = [PathIn, PathOut]`;
   `Speed`
4. `k.createBehaviour(VC_ONETOONEINTERFACE, "InInterface")`;
   `createSection("InInterface")`; `Frame = PathIn`;
   `createField(VC_FLOWFIELD, "Flow")`; bind till **Input**-kontakten (B)
5. samma för `"OutInterface"` med `PathOut` och **Output**-kontakten

Inga sensorer, ingen styrning, ingen signal: `VC_CONVEYORTRANSPORTCONTROLLER`
hör till processmodelleringens transportsystem (`vcTransportController`,
`vcTransportNode`, `vcTransportLink`) och till frågan om resurser, inte
till bana-mot-bana-flöde. Den är dessutom **inte** en beteendetyp (D0).

**C1 — HYPOTES, rang 1.** En nyskapad `VC_ONEWAYPATH` bär redan kontakter:
en `VC_CONNECTOR_INPUT` och en `VC_CONNECTOR_OUTPUT`. Recepten väljer
kontakt **på `Type`, aldrig på index**, och rapporterar `ConnectorCount`
och varje kontakts namn, index och typ.
**C2 — HYPOTES, rang 2.** Banan får inga kontakter. Då finns ingen
Python-väg att skapa dem: `createConnector` finns bara på
`vcComponentFlowProxy` (api.xml), och Create3D
`IFlowBehavior.CreateConnector` *"Thrown if this behavior does not support
dynamic connectors"*. Utfallet syns i `"connectors": []` i svaret.

### D. MATARE och SÄNKA (och buffert)

**D0 — BELAGT.** Create3D:s `BehaviorType` räknar upp bl.a.
`ComponentContainer`, `OneWayPath`, `OneDirectionalPath`,
`ComponentCreator`, `ContainerFiller`, `ComponentFlowProxy`,
`OneToOneInterface`, `TransportProtocol` — men **inte** `Container` och
**inte** `ConveyorTransportController`. Det förklarar mätning 6:
`VC_CONTAINER` och `VC_CONVEYORTRANSPORTCONTROLLER` gav `None` för att de
inte är beteendetyper. Behållaren heter `VC_COMPONENTCONTAINER`.

**D1 — HYPOTES (matare).** `VC_COMPONENTCREATOR` → `vcComponentCreator`
(ärver `vcFlow` **och** `vcContainer`, api.xml). Ställ `Interval` (*"the
interval (in seconds) for creating components"*), valfritt `Limit`, och
mallen: `TemplateComponent` = en komponent i scenen **eller** `Part` = URI
(*"Either this property or Part can be used to define the template component
of creator."*). Katalogen är mätt tom, så mallen byggs själv i scenen (t.ex.
ett block) och ges som `mall`. Ett ut-gränssnitt binds till skaparens
Output-kontakt. Att skaparen själv skjuter ut när kapacitet finns stöds av
`BlockingOptimization`: *"If True, the creator will not check for capacity
rather listen for event."*

**D2 — HYPOTES (sänka).** `VC_COMPONENTCONTAINER` med stor `Capacity` och
`ContentVisible = False`, plus ett in-gränssnitt bundet till
Input-kontakten. **Ärligt:** den *lagrar*. Att *ta bort* produkter kräver ett
skriptbeteende (`VC_PYTHONSCRIPT`), och det stoppar bryggans simulering
(M-13; `skrivgrind.skapar_skriptbeteende` avvisar det). Så länge bryggan är
vägen in är sänkan en osynlig behållare, inte en förstörare. Testet
`test_trasig_fixtur_skriptsanka_fastnar` visar att en skriptsänka fastnar i
grinden.

**D3 — HYPOTES, rang 2.** `VC_CONTAINERFILLER` (`vcFlow`) kan vara matare
eller sänka; källorna säger bara *"container filler flow behavior"*. Sonden
skapar en och rapporterar dess kontakter; inget recept bygger på den.

**D4 — HYPOTES (buffert).** En `VC_ONEWAYPATH` med `Accumulate = True` och
`Capacity = N` är ett buffertmagasin med N platser (`Accumulate`: *"components
on the path stop moving when they encounter a blocked component"*). Ingen
egen behållare behövs; receptet `buffert` är `transportor` med de två
egenskaperna satta.

### E. Vad krävs för att `canConnect` blir sant?

**E0 — BELAGT.** Se 1.5: sektion matchas mot sektion, fältens ordning
utvärderas, en one-to-one som redan är kopplad matchar inte.

| Id | Rang | Hypotes |
|---|---|---|
| **E1** | 1 | Två flödesfält är kompatibla när **båda har bunden `Port`** och portarna har **motsatt `Type`**: Output mot Input. Riktningen bor i kontaktens `Type`, inte i fältet. **Ut-sidan** är gränssnittet vars fält pekar på en `VC_CONNECTOR_OUTPUT`; **in-sidan** det vars fält pekar på en `VC_CONNECTOR_INPUT`. Stöd: `AutoPlugFlowDirection` (1.5). |
| **E2** | 2 | Ett fält utan bunden referens matchar aldrig. Alla nio mätta uppställningar hade obundna fält (`Transport = None`) — därför False överallt, oberoende av sektioner, `IsAbstract` och fälttyp. |
| **E3** | 3 | Fältens **namn** måste vara lika på båda sidor. Recepten ger båda sidor namnet `Flow` så att variabeln är eliminerad. |
| **E4** | 4 | `Connection = 1` är portindex (A1). |
| **E5** | 5 | Ett fysiskt gränssnitt (`IsAbstract = False`) vars sektion saknar `Frame` matchar inte. Med `IsAbstract = True` behövs ingen ram (Create3D `IsLogical`: *"not connectable by plug and play"*). Mätning 7 provade båda lägena utan bundna fält, så E5 är inte utesluten men inte ensam orsak. |

Vad `Connection`-egenskapens värde betyder är alltså **inte belagt**. Sonden
avgör det.

### F. Behövs en geometrisk ram, och hur skapas den?

**F0 — BELAGT.** För ett **fysiskt** gränssnitt: ja. `Section.Frame` är
`vcFeature` (RW), *"If belonging to physical interface, defines the Frame
feature referenced as the location of section"*, och .NET kräver
`IFrameFeature`. Skapas med `node.RootFeature.createFeature(VC_FRAME, namn)`
och placeras genom `feature.PositionMatrix` (`vcMatrix`; `P` för läge,
`rotateRelZ` för vridning — samma väg som `set_transform` i `scen.py`).

**F1 — HYPOTES, rang 1.** Vid koppling läggs sektionsramarna på varandra och
comp2 snappas till comp1 (`connectComponents`: *"comp2 is snapped to
comp1"*). Ut-ramen bör då vara vriden **180° kring Z** så att nästa bana
fortsätter i samma riktning. Recepten gör det (`vrid_ut = 180`).
**F2 — HYPOTES, rang 2.** Ramarna läggs på varandra utan vridning; sätt
`vrid_ut = 0`. Utfallet syns direkt i 3D-vyn: ligger bana 2 bakåt över bana 1
är F1 fel.

Abstrakt gränssnitt (`IsAbstract = True`): ingen ram behövs (E5). Recepten
tar `abstrakt = True` som alternativ för att skilja ramfrågan från
bindningsfrågan.

### G. Går det via Python?

**G0 — BELAGT.** Varje steg utom bindningen finns namngivet på Python-ytan:
`createComponent`, `createBehaviour`, `createFeature(VC_FRAME)`,
`PositionMatrix`, `Path`, `createSection`, `createField`, `Properties`,
`IsAbstract`, `Frame`, `canConnect`, `connect`, `connectComponents`. Alla
namn i recepten är kontrollerade mot `api_index` (test).

**G1 — HYPOTES.** Det **går** via Python om B1 (eller B2) håller.
Om B1–B4 alla ger `SystemError` eller lämnar `Value = None`, då är
slutsatsen rak: **py2-bindningen kan inte sätta fältreferenser, och
komponenter som kopplar ihop sig går inte att bygga helt i Python.** Kvar är
då två vägar, och båda ligger utanför det uppdraget bad om:

* **B5** — kontakt mot kontakt utan gränssnitt. Ger materialflöde om
  Python-bindningen tillåter kopplingen över komponentgränsen (.NET-doken
  antyder att den inte gör det). Ingen snappning, ingen PnP.
* **B6** — bygg *en* komponent av varje slag i GUI:t (Modeling-fliken:
  Interface → Section → Flow-fält → välj Port), `comp.save(uri)`, och låt
  recepten ladda och klona. En handfull minuter i GUI:t, en gång. Det är den
  ärliga vägen om bindningen är stängd.

"Ladda ur katalogen" är ingen väg: katalogen är mätt tom.

---

## 3. Recepten

`svc/vc_assist_svc/byggrecept/` — `generera(namn, argument)` ger Python
2.7/3.x-kod för bryggan (skrivande → `exec_queue`). Varje svar bär listan
`forsok`: `{"hypotes": id, "utfall": "ok"|"fel", ...}` per steg.

| Recept | Bygger | Provar |
|---|---|---|
| `sondera_falt` | skrapkomponent, ett fält av **varje** typ, ett beteende av varje flödestyp; dumpar egenskaper och kontakter; tar bort komponenten (`behall` för att spara) | B0 (fältens egenskaper), C1/C2 (kontakter), D0 (vilka konstanter ger beteenden), A1/E4 (vad Transport-fältet bär) |
| `transportor` | bana med in- och ut-gränssnitt; `falttyp = flow` (rang 1) eller `transport`; `abstrakt`, `vrid_ut`, `geometri` | C3, B1–B4, E5, F0 |
| `buffert` | samma med `Accumulate` och `Capacity = kapacitet` | D4 |
| `matare` | skapare med ut-gränssnitt; `mall` (komponent i scenen) eller `del_uri` | D1, B1–B4 |
| `sanka` | osynlig behållare med in-gränssnitt | D2, B1–B4 |
| `koppla` | ut-gränssnittet i `a` mot in-gränssnittet i `b`; provar i ordning `canConnect`+`connect` (E0), `connectComponents` (G0), kontakt mot kontakt (B5) | E0–E2, G0, B5 |

Recepten är **inte** registrerade i verktygsregistret: de är mätinstrument
för den här specen. Registrering är ett eget beslut när de är mätta.

---

## 4. Mätprotokoll — i vilken ordning operatören prövar

1. **`sondera_falt {}`.** Läs `fields[*].properties`: finns `Port` på
   `VC_FLOWFIELD`? Vad heter och bär `VC_HIERARCHYFIELD`:s egenskaper (finns
   något som ser ut som `IsParent`)? Läs `behaviours[*].connectors`: har
   `VC_ONEWAYPATH` två kontakter med typerna `VC_CONNECTOR_INPUT`/`OUTPUT`
   (C1) eller inga (C2)? Ger `VC_CONTAINER` fortfarande `None` (D0)?
2. **`transportor {"name": "Bana1"}`** och **`{"name": "Bana2"}`.** Läs
   `forsok`: vilket B-id fick `"utfall": "ok"` med `Value ≠ None`? Läs
   `interfaces[*].properties_after`.
   * B1 ok → bindningen går via Python. Gå till 3.
   * bara B2 ok → A1 stämmer; kontrollera att E4 (`Connection`) också gick.
   * alla fel → kör igen med `"falttyp": "transport"`; sedan
     `"abstrakt": true` för att skilja E5 från B. Alla fel igen → G1:
     Python räcker inte; välj B6.
3. **`koppla {"a": "Bana1", "b": "Bana2"}`.** `"via": "E0"` = gränssnitten
   kopplade själva (målet). `"via": "G0"` = VC matchade men vår
   `canConnect`-uppställning var fel (läs `forsok[0].fel`). `"via": "B5"` =
   flöde utan gränssnitt. `"connected": false` → läs varje `fel`.
   Titta i 3D-vyn: fortsätter Bana2 i Bana1:s riktning (F1) eller ligger den
   bakåt (F2 → kör om med `"vrid_ut": 0`)?
4. **`matare`** (med `mall` = en byggd produktkomponent), **`sanka`**,
   **`koppla`** mot banan; starta simuleringen; läs `Statistics`/
   `ComponentCount` på sänkan.
5. **`buffert`** mellan två banor.

Varje körning är en mätning av flera hypoteser samtidigt. Skriv utfallen
tillbaka som **MÄTT** i `hypoteser.py` (status) och här, i stället för att
lägga till nya rader: en hypotes som mätts är antingen belagd eller borta.

---

## 5. Det som är MÄTT (uppdraget 2026-09-04, punkt 1–9), som modellen måste förklara

| # | Mätt | Förklaring i modellen |
|---|---|---|
| 1–3 | `createBehaviour(VC_ONETOONEINTERFACE)`, `createSection(name)`, `createField(VC_TRANSPORTFIELD, name)` fungerar | BELAGT-kedjan i 1.3 |
| 2 | `createSection()` utan namn ger `None` | .NET kastar (*"name is null or empty"*); bindningen ger `None` i stället |
| 4 | Transport-fältet bär `Name`, `Transport = None`, `Connection = 1` | 1.4: fältet är beteende + port (A1/E4); obundet (E2) |
| 5 | `Transport` har typen `Ref<ComponentProcessor>`; bana/namn/nod ger `SystemError`; `None` fungerar | A0–A2; B1 avgör om det är typen eller sättaren |
| 6 | `VC_CONTAINER`, `VC_CONVEYORTRANSPORTCONTROLLER` ger `None` | D0: inte beteendetyper |
| 7 | `canConnect` False i alla uppställningar | E2: inget fält var bundet |
| 8 | fältordning utvärderas; `Section.Frame` hör till fysiskt gränssnitt | E0, F0 |
| 9 | toleranser 1e9 mm / 360° | tolerans är inte hindret; det är bindningen |
