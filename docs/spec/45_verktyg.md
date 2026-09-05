# Verktygslagret

Form ärvd **KOD@HEAD** ur källprojektet: OpenAI function-calling-schema som ren
datalista, delad i två register.

## Två register

| Register | Handlaren returnerar | Exekvering |
|---|---|---|
| `DATA_HANDLERS` | ett färdigt resultat | anropas direkt i tjänsten |
| `CODE_GEN_HANDLERS` | en **sträng med Python 2.7-kod** | skickas till bryggan |

VC:s objektmodell är metodbaserad, inte attributsatt som USD. Därför väger
kodgenereringsgrenen tyngre här än i källan. Tumregel: allt som rör scenen är
kodgenerering; allt som rör index, katalog och kunskap är data.

## Obligatoriska fält per verktyg

Utöver OpenAI-schemats `name`, `description`, `parameters`:

| Fält | Värden | Används till |
|---|---|---|
| `effect` | `read` \| `write` | **avgör exekveringsläge**: `read` → `exec`, `write` → `exec_queue` |
| `mode` | `data` \| `codegen` | vilket register |
| `returns` | JSON-schema för resultatet | verify-contract och AST-validering |
| `since` | VC-version | versionsmedvetenhet |

Regeln `effect=write ⇒ kö` är mekanisk. Ingen enskild handlare får välja själv.

## Katalog

Härledd ur den mätta API-ytan i `docs/referens/vc_api/vc_python_api.json`
(204 typer, 966 metoder, 1159 egenskaper).

### scene — läsa och ändra scenen

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_components` | codegen | read | `app.Components` |
| `find_component` | codegen | read | `app.findComponent(name)` |
| `component_info` | codegen | read | `Uri`, `Category`, `Properties`, `VCID` |
| `load_component` | codegen | **write** | `app.load(uri)` |
| `clone_component` | codegen | **write** | `comp.clone()` |
| `delete_component` | codegen | **write** | `app.delete()` |
| `get_transform` | codegen | read | `node.WorldPositionMatrix` |
| `set_transform` | codegen | **write** | `node.PositionMatrix` |
| `get_bounds` | codegen | read | `BoundCenter`, `BoundDiagonal` |
| `list_nodes` | codegen | read | `node.Children` |
| `find_node` | codegen | read | `node.findNode()` |
| `get_property` / `set_property` | codegen | read / **write** | `comp.getProperty()` |
| `list_properties` | codegen | read | `comp.Properties` |
| `save_layout` | codegen | **write** | `app.save(uri)` |

### composition — plug and play

Den viktigaste gruppen. **Modellen anger relationer, VC räknar geometrin.**

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_interfaces` | codegen | read | `vcSimInterface` per komponent |
| `interface_info` | codegen | read | `Sections`, `IsAbstract`, toleranser |
| `can_connect` | codegen | read | `iface.canConnect(other)` |
| `connect` | codegen | **write** | `iface.connect(other)` |
| `disconnect` | codegen | **write** | `iface.disconnect()` |
| `list_connections` | codegen | read | `ConnectedComponents` |

`connect` får aldrig ta koordinater som argument. Kopplingen **är** relationen.

### catalog — vad som finns att spawna

| Verktyg | mode | effect |
|---|---|---|
| `search_catalog` | data | read |
| `catalog_item` | data | read |

Indexet byggs i fas 4 och bär per komponent: URI, namn, kategori, tillverkare,
**vilka gränssnitt den bär**, och egenskaper. Modellen får **bara** välja ur
träfflistan. Uppfunnen URI är ett hårt fel, inte en varning.

### signals

| Verktyg | mode | effect |
|---|---|---|
| `list_signals` | codegen | read |
| `get_signal` | codegen | read |
| `set_signal` | codegen | **write** |
| `watch_signal` | codegen | **write** |

### robot

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `list_robots` | codegen | read | |
| `get_joints` | codegen | read | `vcServoController.Joints` |
| `robot_limits` | codegen | read | max hastighet och acceleration |
| `create_target` | codegen | **write** | `ctrl.createTarget()` |
| `add_target` | codegen | **write** | `ctrl.addTarget()` |
| `clear_targets` | codegen | **write** | |
| `move_to` | codegen | **write** | `ctrl.moveTo()` |
| `add_tool` / `add_base` | codegen | **write** | |

### process

| Verktyg | mode | effect |
|---|---|---|
| `list_product_types` | codegen | read |
| `create_product_type` | codegen | **write** |
| `get_flow` / `set_flow_step` | codegen | read / **write** |
| `process_state` | codegen | read |

### simulation

| Verktyg | mode | effect |
|---|---|---|
| `sim_state` | codegen | read |
| `sim_run` / `sim_halt` / `sim_reset` | codegen | **write** |
| `sim_speed` | codegen | **write** |
| `set_fast_scheduling` | codegen | **write** |

### measure — grindarnas råvara

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `min_distance` | codegen | read | `getMinimumDistanceDistance` + båda punkter |
| `test_collision` | codegen | read | `testAllCollisions` |
| `measure_distance` | codegen | read | `node.measureDistance()` |
| `get_statistics` | codegen | read | `vcStatistics` |

### view

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `set_camera` | codegen | **write** | `vcCamera` |
| `create_view` / `use_view` | codegen | **write** | |
| `frame_grab` | codegen | **write** | `beginFrameGrab` + `executeFrameGrab` |
| `pixel_to_ray` | codegen | read | `camera.getRay()` |

### eyes

| Verktyg | mode | effect |
|---|---|---|
| `eyes_start` / `eyes_stop` | codegen | **write** |
| `eyes_report` | data | read |

### plc

| Verktyg | mode | effect |
|---|---|---|
| `plc_status` | data | read |
| `plc_read` / `plc_write` | data | read / **write** |
| `plc_compile` | data | read |
| `plc_deploy` | data | **write** |
| `signal_map` | data | read |

### selection — vad användaren pekar på

| Verktyg | mode | effect | Bygger på |
|---|---|---|---|
| `get_selection` | codegen | read | `app.SelectionManager.getSelection` |
| `scene_snapshot` | codegen | read | `app.Components`, `comp.Behaviours` |

Gruppen finns för **pekord**: *"byt det där gripdonet"*, *"snabba den här
linan"*. Registret bar 122 verktyg och noll som rörde markering, så en sådan
mening gick inte att lösa ut alls.

**Båda är `read`, och det är en grind och inte en konvention.** En fråga om vad
användaren pekar på får aldrig kunna flytta något; `markering.granska_domanen()`
kastar `Schemafel` om något verktyg i domänen deklareras `write`, och den körs
vid import.

`scene_snapshot` är avsedd att läsas **varje tur** i stället för att frågas
fram. Formen är ärvd ur Isaac Assist `stage_reader.get_stage_summary()`
(*"Suitable for injecting into every chat turn"*). Mätt i M-171: **102 tokens**
för en scen med 20 komponenter, mot ett tak på 1 200 (post 6 i
`25_kontextbudget.md`, 15 % av det minsta mätta fönstret).

**Sorten läses ur strukturen, aldrig ur namnet.** Familjen kommer ur
komponentens beteenden via `datablad.FAMILJEMARKORER`, och M-171 mätte att ett
beteendes `Type` i en körande scen *är* filformatets markörsträng
(`VC_ONEWAYPATH == 'rOneWayPath'`) — samma vokabulär, ingen översättning. En
komponent utan markör får **tom sort**, aldrig en gissad: M-69 mätte vad
namnhärledning kostar i katalogen, och M-171 fann samma fälla i en scen, där en
komponent som heter `Robot` inte bär någon robotstyrning.

Markeringen är ett **indicium, inte en auktoritet**. Vad som får göras med den
står i `svc/vc_assist_svc/scenarbete/markering.py`: den löser ut ett mål bara
när den stämmer med sorten meningen namnger, den smalnar av annars, och en
markering av annan sort är en **motsägelse** som ställer frågan — inte ett val.

### knowledge

| Verktyg | mode | effect |
|---|---|---|
| `lookup_api` | data | read |
| `lookup_helper` | data | read |
| `lookup_pattern` | data | read |

`lookup_api` slår mot det index som byggs ur `vc_python_api.json`. Svaret bär
den **exakta** signaturen och instruktionen att inte omformulera namnet.
Det är den enda mekanism i källprojektet som faktiskt motverkar uppfunna
API-namn, och där är den handskriven. Här genereras den ur mätt data.

## Antal och urval

När katalogen passerar ungefär hundra verktyg får de inte plats i en prompt.
Då ärvs semantiskt urval per tur ur källan: hämta topp N mot turens text,
plus en alltid-med-lista.

Under hundra: skicka alla. Enkelhet före maskineri tills mätningen kräver annat.

## Validering före körning

Två lager, båda ärvda:

1. **AST-validering mot schemat.** Anropsnamn, argumentnamn, enum-värden och
   nästlade nycklar kontrolleras mot verktygsschemat innan något körs.
   Detta är den starkaste anti-hallucinationen som finns byggd i källan.
2. **Regelgrindar på den genererade koden.** VC-specifika dödsfällor, till
   exempel `connect` med koordinater, `transfer` utan avståndskontroll,
   ändring av scenen medan simuleringen kör.

Regelbanken börjar tom och **varje regel ska bära den incident som skapade den**.
