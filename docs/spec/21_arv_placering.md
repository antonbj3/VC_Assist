# Arv för placering och kollisionshantering

Källa: `~/projects/Omniverse_Nemotron_Ext`, gren `feat/foundation-build`.
Allt nedan är läst **i koden**, med fil och rad. Fortsättning på `20_arv.md`,
som täcker sömmen, verktygsformen, validering och ögat. Här står bara det som
rör **var saker hamnar** och **vad som händer när de hamnar i varandra**.

## Huvudfyndet, i klartext

**Isaac Assist bestämmer i allmänhet inte var saker ska stå. Det kontrollerar
var de hamnade.**

Placeringen författas av språkmodellen. I `scene_blueprints.py:1343` står hela
den spatiala instruktionen som **prosa i en promptsträng**:

> "Ensure objects don't overlap, items sit ON surfaces (not floating),
> robots have 1m clearance."

Modellen svarar med `position [x,y,z]` per objekt. Sedan kommer en
kontrollkedja. Det är alltså sant, som operatören sa, att språkmodeller kan
placera saker i rummet — men i källan gör de det **utan geometriskt underlag**,
och hela ingenjörsarbetet ligger i vad som kontrollerar dem efteråt.

Det finns exakt **tre** ställen där koden *räknar fram* en position, och
**ett** där den *rättar* en:

| # | Vad | Fil | Storhet |
|---|---|---|---|
| 1 | ovanpå-aritmetik ur bbox | `handlers/robot.py:7397` | en relation |
| 2 | mönsterplacering (kolumn / RxC-rutnät / donut) | `handlers/scene_authoring.py:5604` | N poser i ett mönster |
| 3 | cellutläggning längs en axel | `chat/composer.py:261` | hela celler |
| 4 | putt ut ur hinder vid spawn | `chat/canonical_instantiator.py:1045–1071` | en robotbas |

Ingen av dem söker fri yta. Det finns **ingen** ledig-yta-sökning, ingen
beläggningskarta för layout, ingen packning, ingen omplacering vid konflikt.
Ord som `free_space`, `find_free`, `candidate_position` finns inte i repot;
den enda `generate_occupancy_map` som finns (`handlers/robot.py:4573`) är en
2D-raycastkarta för AMR-navigering, inte för att lägga ut en fabrik.

## Arvstabellen

| Mekanism i Isaac Assist | Fil (rad) | Vad den gör | Skick | Översättning till VC |
|---|---|---|---|---|
| **`place_on_top_of`** | `handlers/robot.py:7397` | "X ovanpå Y" → koordinat. Läser målets **världs**-bbox-topp och källans **otransformerade lokala** bottenplan, sätter `z = top + clearance − src_bottom`. Kommentaren i koden dokumenterar buggen som gav mekanismen: `ComputeLocalBound` innehåller primens egen translate och sänkte en sfär en halv meter | **BYGGD**, registrerad, går genom kön | **Ärvs rakt av.** VC: `BoundCenter` + `BoundDiagonal` ger samma två tal. Detta är mönstret för hela relationsfamiljen: modellen säger relationen, koden räknar talet |
| **`compute_stack_placement`** | `handlers/scene_authoring.py:5604` | N poser ur ett mönster: `column`, `grid_RxC`, `donut_RxC`, med `spacing`, `layer_rotation_deg`, `anchor='top'\|'inside_floor'`. Kan köra **utan** scen om `bbox` skickas in (planeringstid) | **BYGGD** | **Ärvs.** Palletering och magasin är samma sak i VC. `bbox`-grenen är den viktiga: mönstret räknas ur katalogens mått **innan** något laddas |
| **`compute_layout_offsets`** | `chat/composer.py:261` | Den enda utläggaren för hela celler. Löper en markör längs en axel: varje cells fotavtrycks-min läggs på markören, markören går fram `throw_pad + clearance`. `throw_pad=2.5 m` är **mätt**: en avrullad kub landade ~2,3 m bortom bandänden, alltså utanför fotavtrycket | **BYGGD**, anropas från `canonical_instantiator.py:1287` och sex QA-skript | **Ärvs som princip, inte som kod.** En 1D-markör är rätt form för en lina. Talet 2,5 m är Isaacs fysik och gäller inte oss — men **regeln** att fotavtrycket inte räcker som separationsmått gäller överallt |
| **`template_footprint`** + `composition_hints.json` | `chat/composer.py` + `workspace/composition_hints.json`, genererad av `scripts/qa/gen_composition_hints.py` | Per mall: `footprint{x:[lo,hi], y:[lo,hi], known}`, `input_ports`, `output_ports`, `exclusive_resources`, `namespacing_safe`, `n_objects` | **BYGGD**, fil finns med data | **Ärvs — och är det viktigaste enskilda arvet här.** Ett **celldatablad** per station gör utläggning möjlig. I VC blir portarna `vcSimInterface`-gränssnitt, vilket är starkare än en sökväg |
| **`precondition_check`** | `chat/composer.py:291` | Vägrar bygga innan något byggts: namnrymdsflykt (mall bakar absoluta sökvägar → tyst prim-krock), samtidig exklusiv resurs (cuRobo-planerarlås), positionsliknande kwarg utanför `POSITION_KWARGS` (namnrymdas men **inte** offsettas → hamnar tyst i origo) | **BYGGD**, anropas från `canonical_instantiator.py:1279` | **Ärvs som mekanismklass.** VC:s motsvarigheter: två komponenter med samma namn, två stationer som delar en exklusiv resurs, en koordinat i ett `connect`-anrop |
| **`static_eyes.run(layout)`** | `multimodal/static_eyes.py:181` | Geometrisk domare **utan** fysik och **utan** att bygga scenen. Kontroller: `reach:shell`, `occlusion`, `interpenetration` (3D-AABB), `fit`, `drop_in_container`, `support`, `relation:*`, `footprint`. Varje fällning bär ett maskinläsbart `fix` med `action`, `constraint` och ofta `suggest_position` | **BYGGD**, registrerad som verktyg (`multimodal_handlers.py:673`, `tool_schemas.py:10176`) | **Ärvs — starkaste placeringsidén i repot.** En billig geometrisk dom före dyr körning, som svarar med ett **förslag**, inte bara ett nej |
| **Tregradig dom** | `static_eyes.py:60–70` | `pass / fail / warn / uncertain / skipped` med konfidens per status. `uncertain` finns för att en radiell räckviddsformel inte kan döma det icke-konvexa golvet | **BYGGD** | **Ärvs.** `uncertain` är det ärliga tredje svaret som `40_ogat.md` saknar. Det ska betyda "dyrare prov krävs", aldrig "godkänt" |
| **`dual_verify.decide`** | `multimodal/dual_verify.py:153` | Statisk rapport → nästa handling: `REJECT_FIX` (bygg aldrig en trasig geometri), `PROBE_REACH` (ett billigt prov), `RUN_GATE`, `SKIP_GATE` **endast** mot mätt kalibrering. Utan kalibrering aktiveras hoppet aldrig | **BYGGD** | **Ärvs rakt av.** Detta är kopplingen "billig dom → dyr dom" som `50_grindar.md` behöver mellan grind 4 och grind 5 |
| **`_verify_relations`** | `static_eyes.py:412` | Verifierar **deklarerad avsikt**, inte gissad geometri: `on_top_of`, `supports`, `above`, `inside`, `contains`, `beside` (med `value` = tillåtet spel, förval 0,30 m). `feeds`/`handoff`/`sequence` markeras uttryckligen `skipped` — semantiska, inte geometriska. `hard` fäller, `soft` varnar | **BYGGD** i static_eyes | **Ärvs.** Skillnaden deklarerad–gissad är precis vår I8: modellen anger relationen, VC räknar geometrin, grinden kontrollerar relationen |
| **`Relation`-typen** | `multimodal/types.py:310` | `{type, from_id, to_id, category(PHYSICS\|SAFETY\|SEQUENCE\|PROXIMITY\|TIMING), reason, severity(hard\|soft), value}` | **BYGGD som schema.** Se brottet nedan | **Ärvs som schema.** Kategorierna passar oss oförändrade |
| **`overlap_check`** | `qa/overlap_check.py`, anropas `canonical_instantiator.py:1196` | Kit-sidig parvis AABB på dynamiska kroppar i **författat** läge + robotbas mot statiska kollisionskroppar. Tolerans 2 cm. Icke-förstörande: ingen tidslinje startas | **BYGGD**, körs vid **varje** bygge — men **enbart rådgivande**, blockerar aldrig | Ärvs som **läge i kedjan** (direkt efter bygge, före körning). **Rådgivande-läget ärvs inte** — se felen nedan |
| **`overlap_box` / `overlap_sphere`** | `handlers/sensors.py:1047, 1093` | Äkta PhysX-scenfråga: vilka kollisionskroppar skär denna låda | **BYGGD** | **Ärvs, och blir bättre.** VC har `testAllCollisions` och `getMinimumDistanceDistance` med båda närmaste punkter. Se "Där vi är starkare" |
| **Utputtning ur hinder** | `canonical_instantiator.py:1045–1071` | Den enda faktiska kollisionsrättningen vid bygge: blås upp hindrets fotavtryck med armradien (0,32 m), putta basen ut längs **axeln med minst inträngning**, plus 0,12 m marginal | **BYGGD men hårdkodad** till UR10 + cuRobo + `Cube`-hinder | **Mekanismen ärvs, koden inte.** "Blås upp med kroppsradien, putta längs minsta inträngning" är rätt regel. Den ska vara generell och gälla varje komponent, inte en robotfamilj |
| **`validate_scene_blueprint`** | `handlers/diagnostics.py:5359` | Statisk kontroll av modellens egen layout: saknade fält, orimlig skala, svävande objekt (mot **högsta stödytan**, inte bara golvet), AABB-överlapp arbetsstycke mot arbetsstycke, räckvidd, nyttolast | **BYGGD**, registrerad `diagnostics.py:6514` | Ärvs som **kontrollista**. Men klassificeringen ärvs inte — se felen |
| **`L-SC-01_REJECT_SELF_REF`** | `scripts/lint_canonical_templates.py:1128` | Avvisar mallar där `cube_path == target_path`: facit blir då trivialt sant ("kuben ligger i sig själv") | **BYGGD** | **Ärvs och skärps.** Rakt in i `81_mallschema.md` som lintregel: ett facit som inte kan falla är inget facit |
| Räckviddstabeller | `static_eyes.py:34`, `diagnostics.py:5520`, `qa/template_position_auditor.py:42`, `handlers/resolve.py` | Robotfamilj → räckvidd i meter | **BYGGD men fyrdubblerad**, med **motstridiga tal**: UR10 anges 1,300 i static_eyes och 1,30 i diagnostics men 1,20 i `template_position_auditor.py` | **Ärvs som varning, inte som data.** VC har `robot_limits` och verklig kinematik. Ett hårdkodat tal är den fällan vi redan känner: en storhet med två värden döljer felet i det vanliga fallet |

## Vad som är specat men dött

| Mekanism | Fil | Läge |
|---|---|---|
| `BlueprintValidator` (fyra kontroller, bl.a. AABB-överlapp mot en objektpalett) | `multimodal/sub_phase_72c_blueprint_validator.py:94` | **Noll produktionsanropare.** Endast tester, plus ett omnämnande i en docstring |
| `spec_to_blueprint` | `multimodal/spec_to_blueprint.py:15` | **Noll anropare** utanför `tests/test_spec_blueprint_roundtrip.py` |
| `grid_to_world` / `world_to_grid` | `handlers/robot.py:1690` | Ligger inne i en `if False:`-gren (`robot.py:1662`). Oåtkomlig kod |
| `_check_footprint_within_bounds` | `multimodal/verifier_registry.py:421` | **Stubb som returnerar `pass`** när argumentet saknas |
| `_check_human_safety_zone` | `multimodal/verifier_registry.py:471` | Samma: **stubb som returnerar `pass`** |
| `prims_to_layout_spec`, `voice`/`sketch`/`photo`-modaliteterna | `multimodal/` | Exporterade, testade, noll anropare. `__init__.py` säger det själv |

## Fyra fel vi ärver om vi inte bestämmer oss

**1. Klassificering på namn.** `validate_scene_blueprint` avgör vad ett objekt
**är** genom delsträngar i dess namn: `_SCENERY` (`diagnostics.py:5572`) listar
`"table"`, `"bin"`, `"franka"`, `"ur10"`, `"conveyor"`… Ett objekt som heter
"Bord2" i stället för "Table2" byter klass och därmed dom. Samma trick i
`static_eyes` (`PALETTE`-kategori) och i `eyes_gold_gate._class`, som gissar
scenarioklass ur `goal`-textens ord — med två inlagda rättelser i kommentaren
för att "pallet" i en stackmalls text ledde fel.

VC ger oss `Category`, `Uri` och `Properties` per komponent, mätt i
`vc_python_api.json`. **Klassen läses ur katalogen, aldrig ur namnet.**
En komponent utan katalogklass är okänd, och okänd är inte grön.

**2. Fail-open i domaren.** Två av registrets kontroller returnerar `pass` när
de saknar sitt argument. En kontroll som säger ja när den inte vet är värre än
ingen kontroll, eftersom den räknas som grön i en summa. Detta är rakt emot
vår I3 och ärvs **inte**.

**3. Rådgivande överlapp.** `overlap_check` körs vid varje bygge men
`canonical_instantiator.py:1191` säger uttryckligen "Advisory — never blocks".
En scen som spawnar inuti sig själv byggs alltså ändå. Hos oss är
kollisionsdomen ett **hårt** villkor före körning (`50_grindar.md`, `83_scenarier.md`).

**4. Två halvor som inte möts.** `Relation`-typen i `types.py:310` valideras i
`validate.py:296` (bl.a. cykelkontroll på `sequence`-kanter). `static_eyes`
verifierar relationer geometriskt — men läser dem ur `layout["relations"]`
(`static_eyes.py:394`), en **annan** datastruktur. Ingenting i repot översätter
`LayoutSpec.constraints` till `layout["relations"]`. Två välbyggda halvor, ingen
brygga. Vi bygger relationen som **en** struktur, med **en** ägare.

## Vad som inte bär över, och varför

**USD-specifika beräkningar.** `UsdGeom.BBoxCache`, `ComputeWorldBound`,
`ComputeUntransformedBound`, `XformOp`-ordningen, `Gf.Vec3d`. VC:s scengraf är
`vcNode` med `PositionMatrix` och `WorldPositionMatrix`, och gränsen läses som
`BoundCenter` + `BoundDiagonal`. *Aritmetiken* är densamma; anropen är det inte.

**PhysX.** `overlap_box`, `RigidBodyAPI`, `kinematicEnabled`, settle,
interpenetration som ger "fysikutkastning". VC:s standardtransport är
icke-fysisk: `transfer()` flyttar en komponent mellan behållare utan
kraftberäkning. Därför finns inte felklassen "spawn-överlapp exploderar" hos
oss — men det betyder också att **ingen fysik rättar en dålig placering
åt oss**. I Isaac gömde settle ibland ett fel; i VC står felet kvar.

**Räckvidd som sfär.** `_reach_radius` och `_project_to_sphere`
(`static_eyes.py:490`) approximerar arbetsrymden som en boll, med en
`uncertain`-remsa på 0,10 m för att formeln inte klarar det icke-konvexa
golvet. VC har verklig kinematik: `vcServoController.Joints`, `robot_limits`,
`ctrl.createTarget()` och `moveTo()`. Sfären får därför bara vara ett **billigt
förfilter**, aldrig domen. Domen är ett IK-anrop.

**Namnrymdsoffsetten.** `namespace_and_offset_calls` och `POSITION_KWARGS`
finns för att USD-mallar bakar absoluta prim-sökvägar. VC har `clone()` och
egna komponentinstanser, så hela klassen "namnrymdsflykt" ser annorlunda ut.
Regeln som överlever är den bakomliggande: **en cell ska gå att flytta i ett
enda tal**, annars går den inte att lägga ut.

## Där vi är starkare än källan

Detta är det som gör att vi inte behöver ärva de svagaste delarna.

| Storhet | Isaac Assist | VC |
|---|---|---|
| Avstånd mellan två kroppar | ingen — approximeras med AABB-marginal | `getMinimumDistanceDistance()` **plus** båda närmaste punkter (`40_ogat.md`) |
| Kollision | PhysX-scenfråga, kräver kollisionsscheman på plats | `testAllCollisions()` i scengrafen |
| Vad en komponent är | delsträng i namnet | `Category` + `Uri` ur katalogindexet |
| Grannskapsplacering | koordinat, kontrollerad efteråt | `iface.canConnect()` / `connect()` — geometrin **räknas av VC** |
| Robotens räckvidd | hårdkodad sfärradie, tre motstridiga tabeller | verklig kinematik och `robot_limits` |

Slutsats: **passagemått och fritt utrymme, som saknas helt i källan, är
billigare för oss än för dem.** Ett gångstråk är ett mätt minsta avstånd mellan
två fotavtryck, och `min_distance` ger det talet direkt.

## Vad vi måste bygga själva

Ingenting av detta finns i källan. Det är listat här så att `22_planeringslagret.md`
kan ta emot det som krav.

1. **Fri yta.** Ingen sökning efter en ledig plats existerar.
2. **Passagemått och gångstråk.** Ordet finns inte i repot. Inga `aisle`,
   `walkway`, `corridor`, `egress`, `keepout`.
3. **Arbetsutrymme runt en station.** Operatörsyta, luckriktning, serviceutrymme.
4. **Konfliktlösning.** Vid överlapp finns ett `fix`-förslag per objekt, men
   ingen omplacering som tar hänsyn till alla andra samtidigt.
5. **Ankarpunkter och rutnät.** Ingen golvruta, inga hallväggar, inget origo
   som betyder något. `cell_bounds` finns i `static_eyes` men fylls av ingen.
6. **Två celler mot varandra.** `compute_layout_offsets` lägger celler på **en**
   rad. En hall är två dimensioner.

## Prioritetsordning för arvet

| Ordning | Vad | Motiv |
|---|---|---|
| 1 | Celldatabladet (fotavtryck + portar + exklusiva resurser) | Utan det kan ingenting läggas ut |
| 2 | Relationer som deklarerad avsikt, verifierade geometriskt | Bär vår I8 |
| 3 | `static_eyes`-formen: billig geometrisk dom med maskinläsbart `fix` | Sparar varje dyr körning som ändå skulle falla |
| 4 | `dual_verify.decide` som routning mellan billig och dyr dom | Gör grindkedjan i `50_grindar.md` kostnadsmedveten |
| 5 | `place_on_top_of` och `compute_stack_placement` | Två färdiga relationsräknare |
| 6 | `precondition_check` som vägransläge före bygge | Fångar det som annars blir tyst |
