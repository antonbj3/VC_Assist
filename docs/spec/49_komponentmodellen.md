# 49 — Komponentmodellen: hur en komponent kan koppla ihop sig

Status: **mätt, och byggd ur specen**. Första versionen härleddes ur
dokumentationen 2026-09-04 medan operatören mätte; samma kväll kördes recepten
i VC 4.10. Sedan dess har M-40, M-41 och M-67 mätt kopplingen och flödet, och
**fas 20** (M-101) byggde de fyra minsta uppsättningarna ur den här texten och
prövade dem i en körande VC.

Avsnitt 0–6 är den härledda modellen med sina mätningar. **Avsnitt 7–10 är
modellen som data** — `svc/vc_assist_svc/komponentmodell.py` — och
`tests/enhet/test_komponentmodell.py` faller om texten och koden glider isär.
Läs 7–10 först om du ska bygga något; 0–6 är hur vi kom fram till det.

Varje påstående bär en av tre märkningar:

| Märkning | Betyder |
|---|---|
| **BELAGT** | står ordagrant i en källfil under `docs/referens/`; citatet och filen står vid påståendet |
| **MÄTT** | mätt av operatören i en körande VC 4.10 (uppdraget 2026-09-04 punkt 1–9, eller kvällens receptkörning) |
| **HYPOTES** | härledd ur källorna, inte prövad. Rangordnad: rang 1 prövas först |

Hypoteserna har id (A1, B7 …) och ligger som **data** i
`svc/vc_assist_svc/byggrecept/hypoteser.py`. Recepten i `recept.py` provar dem
i rangordning vid körning och bokför utfallet per id i svaret (`forsok`).
Testet `tests/enhet/test_byggrecept.py` faller om ett id i koden saknas här
eller om ett VC-namn i en hypotes inte finns i `api_index` (eller i den
deklarerade listan av mätta klassnamn, `MATTA_KLASSNAMN`).

Källförkortningar: `api.xml` = `docs/referens/vc_api/api.xml` (Python-API:t,
samma innehåll som `vc_python_api.json`), `constants.xml` =
`docs/referens/vc_api/constants.xml`, `Create3D` =
`docs/referens/vc_dotnet/Create3D.Shared.xml` (.NET-lagret bakom Python).

---

## 0. Det korta svaret

**Gränssnittskopplingen fungerar.** `a.OutInterface.connect(b.InInterface)`
ger `canConnect True`, `connect True` och `IsConnected True` (**MÄTT M-40**,
bekräftad i **M-67**). Kontaktnivån (`ut.connect(inn)` mellan två
`vcConnector`) fungerar också (**B5, MÄTT**) — men den behövs inte längre.

**Det som stängde vägen var bindningsordningen, inte en saknad förmåga.**
Ett flödesfält bär **två** referenser: `Container` (beteendet) och `Port`
(kontakten i det, som ett **heltal** — B3). Recepten satte `Port` först och
`Container` sedan, och `Container`-tilldelningen **nollställer `Port` till
-1**. Ett fält med `Port = -1` ger `canConnect False`, tyst. Binds `Container`
**först** står `Port` kvar och kopplingen går. Det är **E6, belagd** (M-40),
och därmed är B7 avgjord: `Container` tar beteendet som objekt.

**Kopplingen flyttar ingenting** (**MÄTT M-67**): noll millimeter, noll
vridning, även i en koppling som lyckas. Layoutlösaren äger geometrin.

**Materialet rör sig** när tre villkor hålls samtidigt, och alla tre är tysta
när de bryts (**MÄTT M-40/M-41**): beteendena måste finnas när simuleringen
**startar**, banans ramar måste vara **ombyggda** (`rebuild()`), och
banbeteendet måste ha **uppdaterats** efter att `Path` satts — annars är
`PathLength` 0.0 och banan tar inte emot något.

Kedjan som byggs, per komponent:

```
vcComponent (nod)
 ├─ RootFeature
 │   ├─ VC_BLOCK   "Kropp"      geometri, valfri
 │   ├─ VC_FRAME   "PathIn"     ram: var banan börjar och var in-sektionen sitter
 │   └─ VC_FRAME   "PathOut"    ram: var banan slutar och var ut-sektionen sitter
 ├─ VC_ONEWAYPATH  "Path"       vcMotionPath = vcFlow + vcContainer; Path = [PathIn, PathOut]
 │     Connectors: Input (index 0, typ 1), Output (index 1, typ 2)   ← C1 MÄTT
 ├─ VC_ONETOONEINTERFACE "InInterface"
 │   └─ Section "InInterface"  Frame = PathIn
 │       └─ VC_FLOWFIELD "Flow"   Name, Container, Port, PortName    ← B00 MÄTT
 │             Port      = Input-kontaktens Index   (heltal, B3 MÄTT ok)
 │             PortName  = Input-kontaktens Name     (B10, provas)
 │             Container = banan                     (B7 → B8 → B9, provas)
 └─ VC_ONETOONEINTERFACE "OutInterface"   … Output-kontakten
```

Koppling som **fungerar och är målet**:
`bana1.OutInterface.connect(bana2.InInterface)` (väg E0, MÄTT M-40).
Reservvägen `bana1.Path.Output.connect(bana2.Path.Input)` (väg B5) fungerar
också, men kopplar bara kontakterna — gränssnitten förblir `IsConnected False`
och plug-and-play blir aldrig av.

---

## 1. Byggstenarna, med belägg

### 1.1 Nod, komponent, feature

| Begrepp | Python | Belägg |
|---|---|---|
| Komponent | `vcComponent`, ärver `vcNode` | api.xml, `vcComponent` `<parents>vcNode</parents>` (rad 4358) |
| Skapa tom komponent | `app.createComponent()` | api.xml `vcApplication.createComponent`: *"Creates a new component at the 3D world origin, and then returns the new component."* **MÄTT** fungerar |
| Feature-träd | `node.RootFeature` | api.xml `vcNode.RootFeature`: *"Gets the root feature of node."* |
| Ny feature | `feature.createFeature(type, name)` | api.xml `vcFeature.createFeature`: *"Adds a new feature of a given type and name as a child of this feature. See Feature Constants for more information."* **MÄTT** (VC_BLOCK, VC_FRAME) |
| Ram | `VC_FRAME` → `vcFrameFeature` (ärver `vcFeature`) | constants.xml `VC_FRAME`; Create3D `FeatureType.Frame`: *"Frame object"*; `IFrameFeature`: *"The Frame feature describes a position and orientation in the 3D world. Frames are used as "glue" between the physical and the simulation world, for instance to outline conveyor paths."* |
| Placera feature | `feature.PositionMatrix` (RW) | api.xml `vcFeature.PositionMatrix`: *"Defines the position matrix of this feature relative to its parent feature's coordinate system."* |
| Beteende | `node.createBehaviour(type, name)` | api.xml `vcNode.createBehaviour`: *"Creates a new behavior of a given type and name in node. See Behavior Constants for more information."* |

**BELAGT om konstanterna:** `constants.xml` är en platt lista med 709 namn
och **inga beskrivningar** (filen består av `<CONSTANTS>` följt av namnen).
Vad en konstant betyder går bara att läsa ur .NET-uppräkningarna med samma
namn: `BehaviorType`, `SimInterfaceFieldType`, `ConnectorType`,
`FeatureType` i Create3D. Därför citeras .NET-filerna för semantik fast
koden är Python.

**MÄTT om klassnamnen:** py2-bindningen rapporterar egna klassnamn
(`type(b).__name__`) som **inte** är api.xml:s typnamn: `VC_ONEWAYPATH` →
`vcOneWayPath`, `VC_COMPONENTCONTAINER` → `vcSimContainer`,
`VC_COMPONENTCREATOR` → `rResourceCreator`, `VC_ONEDIRECTIONALPATH` →
`vcMovementPath`, `VC_CONTAINERFILLER` → `vcContainerFiller`, `VC_TRANSPORT`
→ `vcTransport`. Indexets typer (`vcMotionPath`, `vcContainer`,
`vcComponentCreator`) är dokumentationens namn på samma objekt. Listan står
i `hypoteser.MATTA_KLASSNAMN`.

### 1.2 Flöde, behållare, kontakt

| Begrepp | Python | Belägg |
|---|---|---|
| Flödesbeteende | `vcFlow`: `Connectors`, `ConnectorCount`, `CapacityAvailable` | api.xml `vcFlow.Connectors`: *"Gets a list of connectors in flow object."*; Create3D `IFlowBehavior`: *"A base interface for behaviors supporting material flow."* |
| Behållare | `vcContainer` (ärver `vcFlow`): `Capacity`, `Components`, `ComponentCount`, `ContentVisible` | api.xml `vcContainer.Capacity`: *"Defines the maximum number of components that can be stored in the container at any given time."*; `ContentVisible` (W): *"Sets the visibility of components stored in the container."* |
| Bana | `vcMotionPath` ärver **både** `vcFlow` och `vcContainer` | api.xml `vcMotionPath` `<parents>vcBehaviour vcFlow vcContainer</parents>` (rad 7894); `vcComponent.Container`: *"Container refers to a behavior that can store components, for example a One Way Path."* |
| Banans väg | `Path` = ordnad lista ramar | api.xml `vcMotionPath.Path`: *"Defines an ordered list of Frame features referenced as waypoints of path. If set, path is calculated based on its interpolation mode."* **MÄTT**: `Path = [ram_in, ram_ut]` tas emot |
| Kontakt | `vcConnector`: `Type`, `Index`, `Connection` (RW), `connect()` | api.xml `vcConnector.Type`: *"Defines the connector's type. That is, whether the connector is an Input, Output or Input/Output type port."*; `Connection`: *"Defines connector that the connector is connected to in a component. If no connection, the value is None."*; `connect`: *"Connects the connector to a given connector. If no argument is given, this method will remove all connections of the connector."* |
| Kontakttyper | `VC_CONNECTOR_INPUT` (**MÄTT** = 1), `VC_CONNECTOR_OUTPUT` (**MÄTT** = 2), `VC_CONNECTOR_INPUT_OUTPUT` | constants.xml; Create3D `ConnectorType.Input`: *"Connector used to accept material flow."*, `Output`: *"Connector used as output."* |
| Kontakter per beteende | **MÄTT**: bana, behållare, transport, filler, riktad bana: Input index 0, Output index 1. **Skaparen (`rResourceCreator`): Output index 0, Input index 1 — omvänd ordning.** | sondera_falt 2026-09-04. Därför: välj **alltid på `Type`**, aldrig på index (C1) |
| Kontakt mot kontakt | `ut.connect(inn)` över komponentgränsen | **MÄTT fungerar** (B5): `ut.Connection` = nästa banas Input. Create3D `ISimConnector.Connect` *"Thrown when connector is not in this component"* gäller inte Python-bindningen. |
| Vad en kontakt är till för | | Create3D `ISimConnector`: *"Interface defining a connection port. Used to implement material flow between containers."* |
| Överföring i kod | `comp.transfer(behaviour, port)` | api.xml `vcComponent.transfer`: *"A given behavior must be or derive from vcFlow and you should check for available capacity."* |

### 1.3 Gränssnitt, sektion, fält

| Begrepp | Python | Belägg |
|---|---|---|
| Gränssnitt | `VC_ONETOONEINTERFACE` → `vcSimInterface` | **MÄTT** (punkt 1); Create3D `BehaviorType.OneToOneInterface` |
| Sektion | `iface.createSection(name)` → `vcSimInterfaceSection` | api.xml: *"Adds a new section of a given name to interface, and then returns the new section."* **MÄTT** (punkt 2): utan argument returnerar bindningen `None`. Stämmer med Create3D `ISimInterface.CreateSection`: *"Thrown when name is null or empty"* — py2-bindningen sväljer .NET-undantaget och ger `None`. |
| Sektionens ram | `section.Frame` (RW, `vcFeature`) | api.xml: *"If belonging to physical interface, defines the Frame feature referenced as the location of section."*; Create3D `ISimInterfaceSection.Frame`: *"Thrown when feature is not of type IFrameFeature."* **MÄTT**: tilldelning av en `VC_FRAME`-feature går utan fel (C3 ok) |
| Fält | `section.createField(type, name)` → `vcSimInterfaceField` | api.xml: *"Creates a new field of a given type and name in section, and then returns the new field. See Interface Constants for more information."* **MÄTT** (punkt 3). |
| Fältets yta i Python | `Index`, `Name`, `Properties`, `Section`, `Type` — **inget annat** | api.xml `vcSimInterfaceField` (fem egenskaper, inga metoder) |
| Fältordning | | api.xml `vcSimInterfaceField.Index`: *"Important: The order of fields in a section is evaluated when establishing a connection between sections. For example, sections may have compatible fields but cannot connect because the order of fields differ in each section."* |
| Fälttyper | `VC_FLOWFIELD`, `VC_TRANSPORTFIELD`, `VC_SIGNALFIELD`, `VC_HIERARCHYFIELD`, `VC_PROCESSORFIELD`, `VC_ATTACHMENTFIELD`, `VC_ACTIONFIELD`, `VC_INTEGERCOMPATIBILITYFIELD`, `VC_RSLFIELD`, `VC_BASEEXPORTFIELD`, `VC_JOINTEXPORTFIELD`, `VC_TOOLEXPORTFIELD` | constants.xml; Create3D `SimInterfaceFieldType`: *"Interface field types. These correspond to classes inheriting from ISimInterfaceField interface."* |
| Abstrakt / fysiskt | `IsAbstract` (RW) | api.xml: *"Defines if interface supports remote connections."*; Create3D `ISimInterface.IsLogical`: *"Determines if this is logical (i.e. not connectable by plug and play)."* |
| Toleranser | `DistanceTolerance`, `AngleTolerance` | api.xml `DistanceTolerance`: *"Defines the distance at which the interface snaps to an available connection, thereby completing Plug and Play."* **MÄTT** (punkt 9): 1e9 mm och 360° på ett nytt gränssnitt — tolerans är inte hindret. |
| Koppla | `canConnect(other)`, `connect(other[, retain_offset])` | api.xml `canConnect`: *"Returns True if a given interface can connect to the interface; otherwise, returns False."* **MÄTT False** med Port bundet, Container obundet (E0) |
| Koppla allt | `app.connectComponents(c1, c2)` | api.xml: *"Connects all matching interfaces between two given components. If a physical connection requires repositioning then comp2 is snapped to comp1."* **MÄTT False** i samma läge (G0) |

### 1.4 Vad fälten bär — .NET (BELAGT) och Python (MÄTT)

**B0 — BELAGT** (Create3D): varje fältklass bär en typad referens.
**B00 — MÄTT** (`sondera_falt`): Python visar dem som egenskaper på fältet.

| Fälttyp | .NET-referens (Create3D) | Python-egenskaper (MÄTT) | Typ-nr (MÄTT) |
|---|---|---|---|
| Flow | `ISimInterfaceFlowField.Port : ISimConnector` — *"Field for connecting two connectors and facilitating a material flow between component containers."* `Port`: *"the instance … that will be connected when the interface will be connected."* | `Name, Container, Port, PortName` | — |
| Transport | *"Field for connecting containers/behaviors."* (hela beskrivningen) | `Name, Transport, Connection` | 9 |
| Signal | `Signal` — *"Field for connecting signal behaviors."* | `Name, Signal, Connection` | 2 |
| Hierarchy | `Frame`, `Node`, `IsParent` — *"If this field is the parent, the opposite side needs to be the child and vice versa."* | `Name, Node, Frame, Parent` | 1 |
| Processor | `Path`, `Sensor`, `IsParent` — *"A parent field utilizes a path behavior. A child field utilizes a sensor behavior."* | `Name, Path, Sensor, Parent` | 10 |
| Action | *"Field for connecting containers and plug&playing components."* | `Name, Actions, Connection` | 8 |
| IntegerCompatibility | | `Name, Value` | 7 |
| Rsl | | `Name, Publisher, Publish, Subscribe` | 3 |
| BaseExport / JointExport / ToolExport | | `Name, BaseList, Export` / `Name, Controller, Export` / `Name, ToolList, Export` | 6 / 4 / 5 |

Mönstret bekräftas: **beteende + port**. Flödesfältet = `Container` +
`Port`(+`PortName`); transportfältet = `Transport` + `Connection`;
signalfältet = `Signal` + `Connection`. `Connection`/`Port` är portindex
(E4, styrkt av att `Port` tar ett heltal, B3). Parfälten bär `Parent`.

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
  flow input"*. Matchningsmaskineriet **vet** vilket gränssnitt som är
  utflöde och vilket som är inflöde — det kan bara komma från kontaktens
  `Type`, och kontakten nås via `Container` + `Port`.

---

## 2. Svaren A–G

### A. Vad är en "ComponentProcessor"?

**A0 — MÄTT.** Strängen `ComponentProcessor` förekommer **noll** gånger i alla
tio källfiler. Internt namn ur kärnan som läcker ut genom `vcProperty.Type`.

**A1 — HYPOTES, rang 1, styrkt av B00.** ComponentProcessor är kärnans
basklass för beteenden som *hanterar* komponenter (`vcFlow`/`vcContainer`-
familjen). Transport-fältets `Transport` — och flödesfältets `Container` —
pekar på ett sådant beteende; `Connection`/`Port` är portindex i det. Att
`Port` tar ett heltal (B3) och att skaparen rapporteras som
`rResourceCreator` (ett "r"-prefix, kärnans namnrymd) pekar samma väg.

**A2 — HYPOTES, rang 2.** ComponentProcessor = `vcTransport`
(`VC_TRANSPORT`, `BehaviorType.TransportProtocol`). Passar ordet men inte
mönstret: flödesfältet har samma tvådelning utan att heta Transport.

Om `SystemError: error return without exception set`: CPython:s generiska
fel när en C-sättare returnerar NULL utan undantag. Skiljer inte "fel typ"
från "ingen sättare". På `Port` gav fel typ i stället ett *riktigt* fel
(`RuntimeError: Expected integer value.`) — så bindningen **har** typade
sättare; `Ref`-sättaren är den som svarar med `SystemError`.

### B. Hur binds ett fält?

**B0/B00** — se 1.4. Bindningen går via `vcProperty.Value` på fältets
egenskaper; det finns ingen Ref-vcProperty och ingen sättmetod.

| Id | Status | Egenskap | Värde | Utfall |
|---|---|---|---|---|
| **B1** | MÄTT | `Port` | `vcConnector`-objekt | `RuntimeError: Expected integer value.` |
| **B2** | MÄTT | `Port` | beteendet | `RuntimeError: Expected integer value.` |
| **B3** | **MÄTT OK** | `Port` | kontaktens `Index` (heltal) | tas emot, läses tillbaka. Recepten binder `Port` så, utan stege. |
| **B4** | bortlagd | | namn som bytesträng | Port tar heltal; Name gav SystemError på Transport (punkt 5) |
| **B5** | **MÄTT OK** | — | `ut.connect(inn)` mellan `vcConnector` i två komponenter | kopplar; `ut.Connection` = nästa banas Input. Gränssnitten förblir okopplade (`IsConnected` False) — flöde utan PnP |
| **B7** | HYPOTES rang 1 | `Container` | beteendet som objekt | aldrig mätt på `Container`; på `Transport` gav vcMotionPath SystemError (punkt 5) |
| **B8** | HYPOTES rang 2 | `Container` | beteendets index i `comp.Behaviours` (heltal) | samma mönster som `Port` |
| **B9** | HYPOTES rang 3 | `Container` | beteendets `Name` (bytesträng) | gav SystemError på Transport; provas sist |
| **B10** | HYPOTES rang 4 | `PortName` | kontaktens `Name` | oberoende strängbindning; sätts alltid utöver `Port` |
| **B6** | HYPOTES sist | — | GUI en gång + `comp.save` | om B7–B9 alla faller går `Container` inte att sätta från Python |

`_bind` i recepten: `Port = Index` (B3), `PortName = Name` (B10), sedan
`Container` enligt B7 → B8 → B9 tills ett värde fastnar. Svaret bär
`properties_before`/`properties_after` per fält och `bound_properties`.

### C. Minsta uppsättning för en TRANSPORTÖR

**C0 — BELAGT.** `vcMotionPath` ärver `vcFlow` **och** `vcContainer`.
**C1 — MÄTT.** Alla flödesbeteenden bär Input+Output från start; skaparen i
omvänd indexordning. Välj på `Type`. **C2** motbevisad.
**C3 — MÄTT bygger utan fel** (två gränssnitt, sektioner med Frame, fält):
`createComponent` → två `VC_FRAME` → `VC_ONEWAYPATH` (`Path`, `Speed`) → två
`VC_ONETOONEINTERFACE` med sektion + `VC_FLOWFIELD "Flow"`. Om detta räcker
för E0 avgörs av `Container` (E6).

### D. MATARE, SÄNKA, BUFFERT

**D0 — BELAGT/MÄTT.** `VC_CONTAINER` och `VC_CONVEYORTRANSPORTCONTROLLER` är
inte beteendetyper (`BehaviorType` saknar dem); `VC_COMPONENTCONTAINER` ger
`vcSimContainer` med Input/Output.

**D1 — HYPOTES, delvis MÄTT.** `VC_COMPONENTCREATOR` (`rResourceCreator`)
byggs utan fel med `TemplateComponent` = komponent i scenen. **MÄTT: noll
produkter på 6 s simtid.** Två skäl som receptet nu stänger:
* **D5** — `Limit` sattes aldrig (receptet satte den bara om `grans` gavs).
  Nu sätts `Limit` alltid (standard 1000000) och `Interval`, `Limit`,
  `TemplateComponent`/`Part`, `Enabled` läses tillbaka i svaret (`creator`,
  med `interval_tog`/`limit_tog`/`template_tog`).
* **D6** — utkontakten var okopplad: `koppla Matare → Bana1` föll på
  receptets beteendeuppslag (`findBehaviour("Path")` på mataren), inte på
  VC. `BlockingOptimization`: *"the creator will not check for capacity
  rather listen for event"* — en skapare utan kopplad utgång väntar. Nu
  väljer `koppla` kontakt över **alla** beteenden på `Type`.

**D2 — HYPOTES (sänka).** `VC_COMPONENTCONTAINER`, `ContentVisible=False`,
stor `Capacity`, in-gränssnitt. Byggs utan fel (MÄTT). Den *lagrar*; att ta
bort kräver skriptbeteende (M-13). **D3** `VC_CONTAINERFILLER`: okänd
semantik, bär Input/Output (MÄTT), inget recept bygger på den.
**D4 — HYPOTES (buffert).** Bana med `Accumulate=True`, `Capacity=N`.

### E. Vad krävs för att `canConnect` blir sant?

**E0 — BELAGT + MÄTT.** .NET: sektion mot sektion, fältordning, inte redan
kopplad. **MÄTT**: med `Port` bundet och `Container = None` på båda sidor är
`canConnect` **False** och `connectComponents` **False**.

| Id | Rang | Hypotes |
|---|---|---|
| **E1** | 1 | Kompatibla när båda flödesfälten är fullt bundna och portarna har motsatt `Type` (Output mot Input). Riktningen bor i kontakten; ut-sidan = fält vars port är `VC_CONNECTOR_OUTPUT` (typ 2). |
| **E2** | 2 | Obundet fält matchar aldrig. Första nio mätningarna: inget bundet. Kvällen: `Port` bundet, `Container` inte — fortfarande False. |
| **E6** | — | `canConnect` kräver `Container` bundet; `Port` ensamt räcker inte. Belagd om E0 blir sant först efter B7/B8. Det är **nästa mätning**. |
| **E3** | 3 | Fältnamnen måste vara lika (recepten: `Flow` på båda sidor). |
| **E4** | 4 | `Connection`/`Port` = portindex — styrkt av B3. |
| **E5** | 5 | Fysiskt gränssnitt utan `Frame` matchar inte; abstrakt behöver ingen ram. Recepten sätter Frame (C3 ok). |

### F. Behövs en geometrisk ram, och hur skapas den?

**F0 — BELAGT/MÄTT.** `Section.Frame` = `VC_FRAME`-feature under
`RootFeature`, placerad via `PositionMatrix`. Tilldelningen går (C3 ok).
**F1/F2 — HYPOTES.** Ut-ramen vriden 180° kring Z (F1, receptens standard)
eller ovriden (F2, `vrid_ut = 0`). Avgörs i 3D-vyn först när E0 fungerar —
B5 flyttar ingenting.

### G. Går det via Python?

**G0 — BELAGT/MÄTT.** Alla namn finns på Python-ytan; `connectComponents`
gav False i samma läge som E0.
**G1 — nu tudelat:**
* **Materialflöde mellan egenbyggda komponenter: JA, MÄTT** (B5). Det
  räcker för att en linje ska kunna transportera — om skaparen producerar
  (D5/D6), vilket `las_flode` avgör.
* **Plug-and-play på gränssnittsnivå: öppet.** Hänger på `Container`
  (B7–B9). Faller alla tre är det GUI en gång + `comp.save` (B6).

---

## 3. Recepten

`svc/vc_assist_svc/byggrecept/` — `generera(namn, argument)`. Alla utom
`las_flode` är skrivande (`EFFEKT`). Svaret bär `forsok:
[{hypotes, utfall, fel|resultat}]`.

| Recept | Bygger / läser | Provar |
|---|---|---|
| `sondera_falt` | ett fält av varje typ, ett beteende av varje flödestyp; dumpar egenskaper och kontakter; tar bort (`behall` sparar) | B00, C1, D0 |
| `transportor` | bana med in-/ut-gränssnitt; `falttyp`, `abstrakt`, `vrid_ut`, `geometri` | C3, **B3 + B10 + B7→B8→B9**, E5, F0 |
| `buffert` | samma med `Accumulate`, `Capacity` | D4 |
| `matare` | skapare + ut-gränssnitt; `mall` (komponent i scenen) eller `del_uri`; `intervall`, `grans` (standard 1000000); **läser tillbaka** `creator` | D1, D5 |
| `sanka` | osynlig behållare + in-gränssnitt | D2 |
| `koppla` | `a` → `b`: E0 (`canConnect`+`connect`) → G0 (`connectComponents`) → B5 (kontakt mot kontakt). Kontakter väljs över **alla** beteenden på `Type`, okopplad före kopplad; `beteende_a/b` är valfria **filter**. Svaret bär `connectors` (vald ut/in med index) | E0, G0, B5, C1 |
| `las_flode` | **LÄSANDE.** simtid, antal komponenter, per komponent: världsläge, behållare (och vems), banavstånd, `CreationTime`; per lagrande beteende: antal och innehåll | — kör före och efter en simulering; skillnaden är svaret |

---

## 4. Mätprotokoll — nästa körning

1. `transportor Bana1`, `transportor Bana2`. Läs `forsok`: vilket av
   **B7/B8/B9** fick `ok` med `Value ≠ None`? Läs
   `interfaces[*].properties_after` — står `Container` bundet?
2. `koppla {"a":"Bana1","b":"Bana2"}`.
   * `via: "E0"` → **E6 belagd**, PnP fungerar; titta i 3D-vyn (F1/F2).
   * `via: "B5"` med B7–B9 alla `fel` → `Container` går inte att sätta från
     Python: **B6**. Flödet fungerar ändå.
   * `via: "B5"` med något B7–B9 `ok` → `Container` tog men matchar inte:
     läs `properties_after` på båda sidor; prova `"abstrakt": true` (E5) och
     `"falttyp": "transport"`.
3. `transportor Mall` (produkten), `matare {"name":"Matare","mall":"Mall"}`
   — läs `creator.limit_tog`, `interval_tog`, `template_tog` (D5).
   `sanka Sanka`. `koppla Matare→Bana1`, `koppla Bana1→Bana2`,
   `koppla Bana2→Sanka` — läs `connectors` i varje svar (D6).
4. `las_flode {}` — **före**. Simulera ≥ 2×`intervall`. `las_flode {}` —
   **efter.** Jämför `component_count`, `containers[*].count`,
   `components[*].creation_time > 0`, `position`. Tills en rad skiljer sig
   är linjen en ritning.

Skriv utfallen tillbaka som MÄTT i `hypoteser.py` och här.

---

## 5. Allt som är MÄTT, och vad modellen gör av det

| Mätning | Utfall | I modellen |
|---|---|---|
| punkt 1–3 | interface, section(name), field skapas | 1.3 |
| punkt 2 | `createSection()` utan namn → `None` | bindningen ger `None` där .NET kastar |
| punkt 4 | transportfält: `Name, Transport=None, Connection=1` | beteende + portindex (A1/E4) |
| punkt 5 | `Transport` typ `Ref<ComponentProcessor>`; objekt/namn/nod → SystemError; `None` ok | Ref-sättaren svarar SystemError; jfr B1 som fick ett riktigt typfel |
| punkt 6 | `VC_CONTAINER`, `VC_CONVEYORTRANSPORTCONTROLLER` → `None` | D0 |
| punkt 7 | `canConnect` False, nio uppställningar, inget bundet | E2 |
| punkt 9 | toleranser 1e9 / 360° | inte hindret |
| sondera_falt | fältens egenskaper per typ (1.4); alla flödesbeteenden har Input/Output; skaparen omvänd ordning | B00, C1, D0 |
| transportor ×2 | byggs; B1 fel, B2 fel, **B3 ok**, C3 ok | Port = heltal |
| koppla Bana1→Bana2 | E0 fel (`canConnect` False), G0 fel, **B5 ok** ("Input"); `IsConnected` False | flöde utan PnP; Container obundet (E6) |
| linje | Mall, Matare, Sanka byggs; koppla Matare→Bana1 och Bana2→Sanka föll på receptets `findBehaviour("Path")` | receptfel, lagat (koppla väljer över alla beteenden) |
| simulering 6 s | 6 komponenter före och efter, **noll skapade** | D5 (Limit osatt) och/eller D6 (utgång okopplad); `las_flode` mäter nästa gång |

---

## 6. Hur en cell faktiskt hänger ihop

Operatörens fråga: *"jag antar att saker står på varandra, och ofta i förhållande
till varandra … vet som sagt inte hur celler och sånt brukar byggas upp."*

Den frågan är inte perifer. Kompositionslagret bygger i dag som om alla lägen
vore fria, och det är fel i minst fyra avseenden.

### Fyra sätt saker står i förhållande till varandra

**Golvet.** Det mesta står på z = 0. En transportör har ben, en robot en sockel.
Höjden är sällan fri — den bestäms av vad som ska nås, inte av var det finns
plats.

**Monteringsramar.** Ett grepdon skruvas fast på robotens verktygsfläns, inte
*i närheten av* den. **MÄTT** i en `.vcmx` (M-57:s bibliotek): metadatan bär
`BaseFrame "rSimBaseFrame"` med `Frame "tool1"`, `Frame "tool2"` och
`Node "mountplate"`, plus `Mass`, `CenterOfGravity` och `Inertia` per ram.
API:t bär `vcHelpers.Robot.mountTool` och `unmountTool` — montering är alltså
en förstklassig operation, inte en positionsberäkning.

**Gränssnitt som bär både flöde och geometri.** Två transportörer kopplas ände
mot ände. Utgången på den ena *är* ingången på den andra, och det är inte bara
en logisk relation.

**Räckvidden styr layouten, inte tvärtom.** Roboten måste nå både plockpunkten
och släpppunkten. I en riktig cell är det sällan möbleringen som bestämmer var
roboten står — det är räckvidden som bestämmer var allt annat får stå. Vår
layoutlösare har ingen räckviddsmodell alls.

### Den öppna frågan som avgör designen

**Positionerar `connect()` komponenterna, eller kopplar den bara logiskt?**

Ingen mätning svarar. Skillnaden är inte en detalj:

| Om kopplingen är **logisk** | Om VC **snäpper** |
|---|---|
| layoutlösaren äger geometrin och måste räkna ut varje läge | lösaren placerar **en** av delarna och låter VC göra resten |
| en felräkning ger två delar som är kopplade men står isär | två räkningar slåss om samma läge |

Vi bygger i dag som om svaret vore det vänstra, utan att veta.

Mätningen är skriven: `tests/protocol/kor_m67_kopplingens_geometri.py`. Den
bygger två komponenter med gränssnitt på kända, åtskilda och vridna lägen,
läser världsläget, kopplar, och läser igen. Trasigt fall: två utgångar som inte
går att koppla får **inte** flytta något.

### Vad som INTE är mätt

* **Om `connect()` flyttar.** Körningen finns, den är inte körd (VC upptagen).
* **Om monteringsramarna går att nå från Python.** `Frame` finns i metadatan och
  52 `Frame`-symboler finns i API:t, men ingen har hämtat en ram ur en laddad
  komponent och satt något på den.
* **Räckvidd.** Ingen komponent i biblioteket bär ett `Reach`-fält (M-57: inget
  gemensamt schema). Räckvidd måste härledas ur länklängder, och en härledd
  räckvidd är en modellparameter som ska bära sin härledning.
* **Vad som får stå på vad.** Ingen mätning säger om VC har någon uppfattning om
  bärighet, staplingsordning eller golvkontakt. Sannolikt inte — VC saknar massa
  och tröghet helt (M-55) — men det är inte prövat.

---

## 7. Minsta uppsättningen per klass — utskriven

Avsnitt 7–11 är **inte prosa**. De är `svc/vc_assist_svc/komponentmodell.py`
skrivet som tabell, och `tests/enhet/test_komponentmodell.py` faller om en
enda rad här skiljer sig från modellen — i **båda** riktningarna. Specen kan
alltså varken beskriva en modell som inte finns eller bära kvar ett krav
modellen har strukit. Det var precis det fas 20 fanns till för att avskaffa.

Så läses en rad. **Krav** är vad som byggs och vad det heter i VC. **Slag**
är beteende, ram, gränssnitt eller egenskap — beteenden och gränssnitt skapas
med `createBehaviour`, ramar med `createFeature`, egenskaper sätts.
**Härkomst** bär ett av tre märken: **MÄTT** med mätningens nummer, **BELAGT**
med källan, **HYPOTES** när ingendera finns. Ett krav utan märke är ett
antagande i mätningskläder, och testet faller på ett sådant.

Sista kolumnen — **vad som händer om det fattas** — är den som gör listan till
en grind i stället för en beskrivning. Den är också domarens text:
`granska()` skriver ut exakt den meningen när kravet saknas i en byggd
komponent. Ett fel som bara säger "gick inte" är ingen grind.

### 7.1 TRANSPORTÖR

*TRANSPORTÖR: tar emot i ena änden, lämnar i den andra*

En transportör är den enda av de fyra som bär **både** en ingång
och en utgång, och därför den enda som kan stå mitt i en kedja.

| Krav | Slag | Konstant | Härkomst | Vad som händer om det fattas |
|---|---|---|---|---|
| `Path` | beteende | `VC_ONEWAYPATH` | BELAGT api.xml vcMotionPath <parents>vcBehaviour vcFlow vcContainer</parents>; MÄTT C0/C3 | beteendet Path (VC_ONEWAYPATH) saknas: utan det finns ingen vcConnector att binda flödesfältets Port till, Container står kvar på None, och canConnect blir False utan att VC säger ett ord (MÄTT M-40, E6) |
| `PathIn` | ram | `VC_FRAME` | MÄTT M-40 villkor 1: utan rebuild() står ramens verkliga läge kvar i nodens ursprung och PathLength blir 0.0 | ramen PathIn (VC_FRAME) saknas: sektionen får ingen Frame, och en bana utan två åtskilda ramar får PathLength 0.0 — den tar inte emot något och matningen uppströms tystnar (MÄTT M-40, linje M41B) |
| `PathOut` | ram | `VC_FRAME` | MÄTT M-40 villkor 1: utan rebuild() står ramens verkliga läge kvar i nodens ursprung och PathLength blir 0.0 | ramen PathOut (VC_FRAME) saknas: sektionen får ingen Frame, och en bana utan två åtskilda ramar får PathLength 0.0 — den tar inte emot något och matningen uppströms tystnar (MÄTT M-40, linje M41B) |
| `InInterface` | granssnitt | `VC_ONETOONEINTERFACE` | MÄTT punkt 1-3 (interface, section och field skapas); BELAGT Create3D BehaviorType.OneToOneInterface | gränssnittet InInterface (VC_ONETOONEINTERFACE) saknas: utan det finns ingenting att anropa canConnect PÅ: findBehaviour ger None och kopplingen kan inte ens efterfrågas (MÄTT M-40: koppla-receptet föll på exakt det) |
| `OutInterface` | granssnitt | `VC_ONETOONEINTERFACE` | MÄTT punkt 1-3 (interface, section och field skapas); BELAGT Create3D BehaviorType.OneToOneInterface | gränssnittet OutInterface (VC_ONETOONEINTERFACE) saknas: utan det finns ingenting att anropa canConnect PÅ: findBehaviour ger None och kopplingen kan inte ens efterfrågas (MÄTT M-40: koppla-receptet föll på exakt det) |
| `Path` | egenskap | -- | MÄTT: Path = [ram_in, ram_ut] tas emot | egenskapen Path är tom: PathLength blir 0.0 och banan bär ingenting |
| `update()` | egenskap | -- | MÄTT M-40 villkor 2: p.Path satt ger PathLength 0.0; p.update() ger 3000.0 | update() utelämnad: PathLength är 0.0 fast ramarna står 3000 mm isär, banan tar inte emot något och mataren uppströms producerar noll (MÄTT M-40, linje M41B: 0 produkter på 7 intervall) |
| `Speed` | egenskap | -- | MÄTT M-41: uppmätt rörelse 250.0000 mm/s mot Speed 250.0, spridning 0.0000 | Speed osatt: förvalet gäller, och vilket det är har ingen mätt |

Parbarhet: **in: matare, transportor, buffert**; **ut: transportor, buffert, sanka**.

Trasig fixtur: `bygg("transportor", namn, utelamna="bana")` bygger allt utom `Path` (`VC_ONEWAYPATH`). Allt annat står kvar — ramarna, gränssnittet, sektionen och fältet — så skillnaden mot den hela uppsättningen är **exakt ett krav**.

### 7.2 MATARE

*MATARE: skapar komponenter och lämnar dem nedströms*

En matare har ingen ingång. `rResourceCreator` bär Output på index **0**
och Input på index **1** — omvänd ordning mot banan (MÄTT C1). Därför väljs
kontakten alltid på `Type`, aldrig på index; ett indexval hade varit grönt på
banan och tyst fel här.

| Krav | Slag | Konstant | Härkomst | Vad som händer om det fattas |
|---|---|---|---|---|
| `Creator` | beteende | `VC_COMPONENTCREATOR` | MÄTT D1/D5 (2026-09-04); py2-bindningen rapporterar klassen som rResourceCreator | beteendet Creator (VC_COMPONENTCREATOR) saknas: ingenting produceras, och utan det finns ingen vcConnector att binda flödesfältets Port till, Container står kvar på None, och canConnect blir False utan att VC säger ett ord (MÄTT M-40, E6) |
| `Out` | ram | `VC_FRAME` | MÄTT M-40 villkor 1: utan rebuild() står ramens verkliga läge kvar i nodens ursprung och PathLength blir 0.0 | ramen Out (VC_FRAME) saknas: sektionen får ingen Frame, och en bana utan två åtskilda ramar får PathLength 0.0 — den tar inte emot något och matningen uppströms tystnar (MÄTT M-40, linje M41B) |
| `OutInterface` | granssnitt | `VC_ONETOONEINTERFACE` | MÄTT punkt 1-3 (interface, section och field skapas); BELAGT Create3D BehaviorType.OneToOneInterface | gränssnittet OutInterface (VC_ONETOONEINTERFACE) saknas: utan det finns ingenting att anropa canConnect PÅ: findBehaviour ger None och kopplingen kan inte ens efterfrågas (MÄTT M-40: koppla-receptet föll på exakt det) |
| `TemplateComponent` | egenskap | -- | MÄTT M-40: tar en komponent som STÅR i scenen, även en utan URI och utan VCID; Part behöver inte peka på en lösbar URI | TemplateComponent osatt: skaparen har ingenting att kopiera |
| `Interval` | egenskap | -- | MÄTT M-41: åtta mellanrum, alla exakt 4.000 s mot Interval 4.0 | Interval osatt: förvalet gäller och takten är inte mätt |
| `Limit` | egenskap | -- | MÄTT M-40/D5: Limit osatt gav noll produkter på 6 s; Limit=10 slutade tyst vid t=50 och såg då ut precis som en trasig matare | Limit osatt: mataren stannar tyst när förvalet nås, och en stannad matare ser exakt ut som en trasig |
| `Enabled` | egenskap | -- | MÄTT M-40: Enabled rapporterades True i alla tre linjerna | Enabled=False: ingenting produceras |

Parbarhet: **in: — (en matare tar inte emot)**; **ut: transportor, buffert, sanka**.

Trasig fixtur: `bygg("matare", namn, utelamna="skapare")` bygger allt utom `Creator` (`VC_COMPONENTCREATOR`). Allt annat står kvar — ramarna, gränssnittet, sektionen och fältet — så skillnaden mot den hela uppsättningen är **exakt ett krav**.

### 7.3 SÄNKA

*SÄNKA: tar emot komponenter och behåller dem*

En sänka **lagrar**; den tar inte bort. Att ta bort kräver ett
skriptbeteende, och ett skriptbeteende stoppar bryggan (M-13). Kapaciteten är
därför satt högt i stället. `ContentVisible` stod här tills M-101 mätte att
egenskapen inte finns — se avsnitt 11.

| Krav | Slag | Konstant | Härkomst | Vad som händer om det fattas |
|---|---|---|---|---|
| `Sink` | beteende | `VC_COMPONENTCONTAINER` | MÄTT D0/D2 (2026-09-04): VC_CONTAINER ger None, VC_COMPONENTCONTAINER ger vcSimContainer | beteendet Sink (VC_COMPONENTCONTAINER) saknas: det finns ingenstans att ta emot, och utan det finns ingen vcConnector att binda flödesfältets Port till, Container står kvar på None, och canConnect blir False utan att VC säger ett ord (MÄTT M-40, E6) |
| `In` | ram | `VC_FRAME` | MÄTT M-40 villkor 1: utan rebuild() står ramens verkliga läge kvar i nodens ursprung och PathLength blir 0.0 | ramen In (VC_FRAME) saknas: sektionen får ingen Frame, och en bana utan två åtskilda ramar får PathLength 0.0 — den tar inte emot något och matningen uppströms tystnar (MÄTT M-40, linje M41B) |
| `InInterface` | granssnitt | `VC_ONETOONEINTERFACE` | MÄTT punkt 1-3 (interface, section och field skapas); BELAGT Create3D BehaviorType.OneToOneInterface | gränssnittet InInterface (VC_ONETOONEINTERFACE) saknas: utan det finns ingenting att anropa canConnect PÅ: findBehaviour ger None och kopplingen kan inte ens efterfrågas (MÄTT M-40: koppla-receptet föll på exakt det) |
| `Capacity` | egenskap | -- | BELAGT api.xml vcContainer.Capacity: "the maximum number of components that can be stored in the container at any given time" | Capacity för låg: sänkan blir full och stoppar linjen uppströms |

Parbarhet: **in: matare, transportor, buffert**; **ut: — (en sänka lämnar inte ifrån sig)**.

Trasig fixtur: `bygg("sanka", namn, utelamna="behallare")` bygger allt utom `Sink` (`VC_COMPONENTCONTAINER`). Allt annat står kvar — ramarna, gränssnittet, sektionen och fältet — så skillnaden mot den hela uppsättningen är **exakt ett krav**.

### 7.4 BUFFERT

*BUFFERT: en bana som HÅLLER KVAR N komponenter*

En buffert är en transportör plus två egenskaper. Kravlistan är
därför transportörens, med `Accumulate` och `Capacity` tillagda — och båda är
**HYPOTES**: ingen mätning har ställt `Accumulate=True` mot `False` på samma bana.

| Krav | Slag | Konstant | Härkomst | Vad som händer om det fattas |
|---|---|---|---|---|
| `Path` | beteende | `VC_ONEWAYPATH` | BELAGT api.xml vcMotionPath <parents>vcBehaviour vcFlow vcContainer</parents>; MÄTT C0/C3 | beteendet Path (VC_ONEWAYPATH) saknas: utan det finns ingen vcConnector att binda flödesfältets Port till, Container står kvar på None, och canConnect blir False utan att VC säger ett ord (MÄTT M-40, E6) |
| `PathIn` | ram | `VC_FRAME` | MÄTT M-40 villkor 1: utan rebuild() står ramens verkliga läge kvar i nodens ursprung och PathLength blir 0.0 | ramen PathIn (VC_FRAME) saknas: sektionen får ingen Frame, och en bana utan två åtskilda ramar får PathLength 0.0 — den tar inte emot något och matningen uppströms tystnar (MÄTT M-40, linje M41B) |
| `PathOut` | ram | `VC_FRAME` | MÄTT M-40 villkor 1: utan rebuild() står ramens verkliga läge kvar i nodens ursprung och PathLength blir 0.0 | ramen PathOut (VC_FRAME) saknas: sektionen får ingen Frame, och en bana utan två åtskilda ramar får PathLength 0.0 — den tar inte emot något och matningen uppströms tystnar (MÄTT M-40, linje M41B) |
| `InInterface` | granssnitt | `VC_ONETOONEINTERFACE` | MÄTT punkt 1-3 (interface, section och field skapas); BELAGT Create3D BehaviorType.OneToOneInterface | gränssnittet InInterface (VC_ONETOONEINTERFACE) saknas: utan det finns ingenting att anropa canConnect PÅ: findBehaviour ger None och kopplingen kan inte ens efterfrågas (MÄTT M-40: koppla-receptet föll på exakt det) |
| `OutInterface` | granssnitt | `VC_ONETOONEINTERFACE` | MÄTT punkt 1-3 (interface, section och field skapas); BELAGT Create3D BehaviorType.OneToOneInterface | gränssnittet OutInterface (VC_ONETOONEINTERFACE) saknas: utan det finns ingenting att anropa canConnect PÅ: findBehaviour ger None och kopplingen kan inte ens efterfrågas (MÄTT M-40: koppla-receptet föll på exakt det) |
| `Path` | egenskap | -- | MÄTT: Path = [ram_in, ram_ut] tas emot | egenskapen Path är tom: PathLength blir 0.0 och banan bär ingenting |
| `update()` | egenskap | -- | MÄTT M-40 villkor 2: p.Path satt ger PathLength 0.0; p.update() ger 3000.0 | update() utelämnad: PathLength är 0.0 fast ramarna står 3000 mm isär, banan tar inte emot något och mataren uppströms producerar noll (MÄTT M-40, linje M41B: 0 produkter på 7 intervall) |
| `Speed` | egenskap | -- | MÄTT M-41: uppmätt rörelse 250.0000 mm/s mot Speed 250.0, spridning 0.0000 | Speed osatt: förvalet gäller, och vilket det är har ingen mätt |
| `Accumulate` | egenskap | -- | HYPOTES D4: aldrig mätt med Accumulate=False mot True på samma bana | Accumulate=False: komponenterna passerar utan att köa sig, och buffert blir samma sak som transportör |
| `Capacity` | egenskap | -- | HYPOTES D4: kapacitetens verkan är aldrig mätt | Capacity osatt: förvalet gäller, och hur många platser en bana har som förval är inte mätt |

Parbarhet: **in: matare, transportor, buffert**; **ut: transportor, buffert, sanka**.

Trasig fixtur: `bygg("buffert", namn, utelamna="bana")` bygger allt utom `Path` (`VC_ONEWAYPATH`). Allt annat står kvar — ramarna, gränssnittet, sektionen och fältet — så skillnaden mot den hela uppsättningen är **exakt ett krav**.

---

## 8. Matchningsregeln för `canConnect`, fullständigt

Det här är svaret på fråga E, utskrivet. Nio rader, i den ordning **vi**
prövar dem.

**Ordningen är vår, inte VC:s.** `canConnect` returnerar ett enda `False`
och säger aldrig vilket villkor som brast. VC:s inre ordning är därför
**inte mätt**, och att skriva vår ordning som om den vore VC:s hade varit
ett antagande i mätningskläder. Vad ordningen däremot är: den ordning som
gör felet begripligt — grövsta bristen först, så att svaret pekar på roten
och inte på en följd.

**Alla fel i tabellen är tysta.** Ingen av raderna ger ett undantag, en logg
eller ett falskt returvärde någon annanstans. Det är hela skälet till att
`komponentmodell.granska()` finns: domen måste vara vår, för VC lämnar ingen.

**R1** — båda sidor har ett beteende med gränssnittets namn, och det beteendet är ett simuleringsgränssnitt (bär canConnect)

* Härkomst: MÄTT M-40: koppla-receptet föll på findBehaviour som gav None
* Felet: gränssnittet saknas — frågan går inte att ställa, och "gick inte" vore tvetydigt

**R2** — flödesfältets Container pekar på ett beteende (inte None)

* Härkomst: MÄTT E0/E6 2026-09-04: med Port bundet och Container=None på båda sidor är canConnect False och connectComponents False
* Felet: canConnect returnerar False. VC säger INGENTING — ingen exception, ingen logg, inget falskt returvärde någon annanstans

**R3** — flödesfältets Port är ett heltal >= 0

* Härkomst: MÄTT M-40: Port = -1 ger canConnect False; MÄTT B3: Port tar ett heltal (kontaktens Index), inte ett vcConnector-objekt
* Felet: canConnect returnerar False, tyst. Ett fält med Port = -1 ser i övrigt färdigbundet ut

**R4** — bindningsordningen är Container FÖRE Port

* Härkomst: MÄTT M-40: Port satt först, sedan Container satt — Port är nu -1
* Felet: Port nollställs till -1 av Container-tilldelningen. Kopplingen faller på R3, av ett skäl som inte syns på raden där felet ser ut att vara

**R5** — ut-sidans kontakt är VC_CONNECTOR_OUTPUT och in-sidans VC_CONNECTOR_INPUT

* Härkomst: MÄTT M-67: ut mot ut ger canConnect False, connect False, IsConnected False — och flyttar ingenting
* Felet: canConnect returnerar False. Riktningen bor i kontakten, inte i gränssnittets namn: ett gränssnitt som HETER OutInterface men bär en Input-kontakt matchar som ingång

**R6** — båda sektionernas fält har samma typ (VC_FLOWFIELD mot VC_FLOWFIELD)

* Härkomst: BELAGT Create3D ISimInterfaceSection.IsCompatibleWith: "True if connection between these sections is possible"
* Felet: canConnect returnerar False. Aldrig mätt med BLANDADE fälttyper — regeln är belagd, inte mätt

**R7** — fälten står i samma ORDNING i båda sektionerna

* Härkomst: BELAGT api.xml vcSimInterfaceField.Index: "sections may have compatible fields but cannot connect because the order of fields differ in each section"
* Felet: canConnect returnerar False. Aldrig mätt hos oss: alla våra sektioner har exakt ett fält, så ordningen kan inte skilja

**R8** — ett VC_ONETOONEINTERFACE är inte redan kopplat

* Härkomst: BELAGT Create3D ISimInterface.Connect: "Thrown when interface cannot be connected (it is one to one interface and already connected ...)"
* Felet: connect kastar i .NET. I Python-bindningen är utfallet INTE mätt — vi vet inte om det blir False eller ett undantag

**R9** — avståndet mellan gränssnitten spelar INGEN roll vid förvald DistanceTolerance

* Härkomst: MÄTT M-67: canConnect True med 1670 mm mellan komponenterna; MÄTT punkt 9: förvalet är 1e9 mm och 360 grader
* Felet: — ingen regel att brista mot. Raden står här därför att M-40:s formulering "canConnect är en geometrisk fråga" är SKÄRPT av M-67: det som fällde var ett fält med Port = -1, inte avståndet

Två rader förtjänar en anmärkning.

**R4 är inte en stilfråga.** Bindningsordningen `Container` före `Port` är
mätt (M-40): sätts `Port` först och `Container` sedan står `Port` på `-1`
efteråt, och kopplingen faller på R3 — av ett skäl som inte syns på raden där
felet ser ut att sitta. `komponentmodell._bind` binder i rätt ordning, och
`test_bindningsordningen_star_i_koden` håller den där.

**R9 är ingen regel, utan en skärpning.** M-40 kallade `canConnect` "en
geometrisk fråga". M-67 mätte `canConnect = True` med 1670 mm mellan
komponenterna. Båda stämmer: i M-40:s fall var det ett fält med `Port = -1`
som fällde, inte avståndet. Vid förvald `DistanceTolerance` (1e9 mm) gatear
geometrin ingenting. Vad ett **satt** `DistanceTolerance` gör är fortfarande
omätt.

---

## 9. Vilka par som ska gå ihop

Riktningen bor i kontakten, inte i namnet: ut-sidan är den vars fält pekar på
en `VC_CONNECTOR_OUTPUT`.

| Ut-sida | In-sida | Ska gå ihop | Härkomst | Skäl |
|---|---|---|---|---|
| `matare` | `transportor` | **ja** (`matare -> transportor`) | MÄTT M-101 (kedjans första led) | ut-sidan bär Output, in-sidan Input |
| `transportor` | `buffert` | **ja** (`transportor -> buffert`) | MÄTT M-101 (kedjans andra led) | ut-sidan bär Output, in-sidan Input |
| `buffert` | `sanka` | **ja** (`buffert -> sanka`) | MÄTT M-101 (kedjans tredje led) | ut-sidan bär Output, in-sidan Input |
| `transportor` | `transportor` | **ja** (`transportor -> transportor`) | HYPOTES: följer av R5, aldrig byggt som par i M-101 | ut-sidan bär Output, in-sidan Input |
| `matare` | `sanka` | **ja** (`matare -> sanka`) | HYPOTES: följer av R5, aldrig byggt som par i M-101 | ut-sidan bär Output, in-sidan Input |
| `matare` | `matare` | **nej** (`matare -> matare`) | MÄTT M-67 (ut mot ut) / härlett ur R5 | båda sidor bär VC_CONNECTOR_OUTPUT; MÄTT M-67: ut mot ut ger canConnect False |
| `sanka` | `sanka` | **nej** (`sanka -> sanka`) | MÄTT M-67 (ut mot ut) / härlett ur R5 | båda sidor bär VC_CONNECTOR_INPUT |
| `sanka` | `matare` | **nej** (`sanka -> matare`) | MÄTT M-67 (ut mot ut) / härlett ur R5 | sänkan har ingen utgång och mataren ingen ingång |

---

## 10. De trasiga fixturerna — fasens poäng

En kravlista som aldrig prövats **utelämnad** är en åsikt. Därför bygger
modellen fyra komponenter till, en per klass, där exakt ett krav saknas:

| Klass | Utelämnat krav | Konstant | Vad domaren ska svara |
|---|---|---|---|
| `transportor` | `bana` | `VC_ONEWAYPATH` | namnger `Path` och säger varför kopplingen är omöjlig |
| `matare` | `skapare` | `VC_COMPONENTCREATOR` | namnger `Creator` och säger varför kopplingen är omöjlig |
| `sanka` | `behallare` | `VC_COMPONENTCONTAINER` | namnger `Sink` och säger varför kopplingen är omöjlig |
| `buffert` | `bana` | `VC_ONEWAYPATH` | namnger `Path` och säger varför kopplingen är omöjlig |

Grinden har två halvor, och båda måste hålla:

1. **VC säger nej.** `canConnect` mot en riktig, hel motpart måste vara
   `False`. Är den `True` är kravet inget krav, och kravlistan ljuger.
2. **Vi säger varför.** `granska()` måste namnge det utelämnade beteendet.
   Ett fel som bara säger "gick inte" duger inte.

Kontrollen är parvis: samma motpart provas först mot den trasiga komponenten
(ska ge `False`) och sedan mot en hel tvilling på **samma plats i världen**
(ska ge `True`). Då är skillnaden mellan de två utfallen exakt det utelämnade
kravet — inte geometrin, inte motparten, inte ordningen.

En femte trasig fixtur bor i domaren i stället för i scenen: en bana vars
`PathLength` är `0.0`. Beteendet **finns**, fältet är bundet, och ändå bär
banan ingenting — ramarna byggdes aldrig om, eller `update()` kördes aldrig
efter att `Path` sattes (MÄTT M-40, linje M41B: noll produkter på sju
intervall). `granska()` fäller den, för en domare som bara räknade beteenden
hade sagt grönt om en linje som står still.

---

## 11. Vad mätningen har refuterat

En rad i en källa är inte en mätning. De här stod som belagda och VC svarade
nej.

**`ContentVisible`** — M-101

* Påstods: BELAGT api.xml vcContainer.ContentVisible (W): "Sets the visibility of components stored in the container."
* Utfall: finns INTE på det beteende VC_COMPONENTCONTAINER faktiskt ger (vcSimContainer). Tilldelningen svarar "NameError: Attribute or method 'ContentVisible' not found." — alltså VC:s NameError, inte Pythons AttributeError (samma fälla som M-40 beskrev för Connectors). api.xml dokumenterar egenskapen på typen vcContainer; py2-bindningens instans bär den inte. En BELAGD rad är inte en mätt rad.

Lärdomen är generell och kostade tretton komponenter: en egenskap som inte
finns kastar `NameError` i VC:s bindning, och en oskyddad tilldelning tar med
sig **hela resten av startskriptet**. Därför går varje egenskapstilldelning i
`komponentmodell` genom `_steg()`: en egenskap som inte finns är ett mätvärde,
aldrig ett haveri.
