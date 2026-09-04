# Planeringslagret

Kravspecifikation för lagret mellan operatörens begäran och verktygsanropen.
Ärvda mekanismer och deras skick i källan står i `21_arv_placering.md`;
här står bara **kraven**. Varje krav har en bokstavskod och en grind som
stänger det. Trösklar utan mätning är märkta `PRELIMINÄR` enligt I2.

## Plats i arkitekturen

```
operatörens text
      │
      ▼
┌── PLANERINGSLAGRET ────────────────────────────────────────┐
│  1. DETALJERING   begäran ──► SPEC        (frågor, slots)  │
│  2. LAYOUT        spec    ──► PLACERING   (relationer→mått)│
│  3. PLANERING     spec    ──► PLAN        (uppgiftsgraf)   │
│  4. SEKVENSERING  plan    ──► ANROPSSEKVENS                │
└────────────────────────────┬───────────────────────────────┘
                             ▼
                   verktygslagret (45_verktyg.md)
                             ▼
                   bryggan ──► VC ──► ögat ──► grindarna
```

Lagret **kör ingenting**. Det producerar fyra artefakter på disk och lämnar
dem till verktygslagret. Det är hela poängen: en plan som bara finns i en
prompt går inte att granska, versionera eller mäta mot.

## De fyra artefakterna

| Artefakt | Vad den är | Vem skriver | Vem läser |
|---|---|---|---|
| `SPEC` | ordersedeln: vad som ska byggas, med alla nödvändiga variabler ifyllda | modellen, ur begäran + operatörens svar | layout, plan |
| `LAYOUT` | var varje station står, med härkomst per tal | placeringslösaren | plan, ögat, grindarna |
| `PLAN` | uppgiftsgraf: steg, beroenden, villkor, efterkontroller | modellen, ur spec | sekvenseraren, grindarna |
| `ANROPSSEKVENS` | den topologiskt ordnade listan av verktygsanrop | sekvenseraren, **mekaniskt** | verktygslagret |

Alla fyra är JSON på disk under `bank/plans/<plan_id>/`. Ingen artefakt får
existera enbart som text i en modellprompt.

## Femte artefakten: celldatabladet

Utan detta går ingenting att lägga ut. Ärvt ur `composition_hints.json`
(`21_arv_placering.md`) men fyllt ur VC:s egen katalog.

Per katalogpost, i `bank/celler/<uri>.json`:

| Fält | Källa i VC | Regel |
|---|---|---|
| `uri` | katalogindexet | nyckel |
| `category` | `comp.Category` | **klassen läses här, aldrig ur namnet** |
| `footprint_mm` | `BoundCenter` + `BoundDiagonal` | axelriktad, i komponentens egen ram |
| `height_mm` | samma | |
| `interfaces` | `vcSimInterface` per komponent | ersätter källans `input_ports`/`output_ports` |
| `flow_dir` | härledd ur gränssnittens lägen | vilken väg materialet går |
| `work_area_mm` | **manuell, per post** | operatörsyta och serviceutrymme. Saknas ⇒ `null`, inte 0 |
| `exclusive` | lista | resurser som inte får delas (t.ex. en robotcontroller) |
| `measured_at` | tidsstämpel + VC-version | |

**K0.** Ett datablad utan `footprint_mm` är okänt. En okänd cell får inte
placeras. `null` är inte noll.

## 1. Detaljering — begäran blir spec

Ärvd form: den behovsstyrda frågeställaren i `scripts/qa/grounded_clarifier.py`
(deterministisk, frågar **exakt** de variabler en kontroll inte kan köras utan)
kombinerad med den produktionskopplade `chat/negotiator.py` (en LLM-runda,
fail-open, en tur). Vi ärver **strukturen från den första** och **placeringen i
turordningen från den andra**.

**K1. Slotlistan är härledd, inte gissad.** Varje spec-fält bär `needed_for`:
vilken grind eller vilket lösarsteg som inte kan köras utan det. Ett fält utan
`needed_for` får inte finnas i schemat.
*Grind:* lintregeln `S1_SLOT_WITHOUT_NEED`.

**K2. Hårda slots är fail-closed.** Källans klarifiering är fail-open
(`orchestrator.py:815`: alla fel ⇒ fortsätt utan att fråga). Det ärvs **inte**.
Ett tomt hårt slot ⇒ planering avbryts, planen får status `INCOMPLETE`, ingen
verktygssekvens produceras.
*Grind:* `P1`.

**K3. Mjuka slots får ett förval med utskriven härkomst.** Förval skrivs som
`{value, source: "default", motiv}` och listas i svaret till operatören.
Ett tyst förval är samma fel som ett tal utan härkomst.

**K4. En frågerunda per tur.** Källan har en loopspärr som läser den föregående
turens text (`orchestrator.py:783`, matchar på en svensk-engelsk fras). Det är
skört. Vi bär i stället ett fält `spec.clarify_round` i artefakten.
*Grind:* `clarify_round ≤ 2` per plan, annars avbryt och rapportera vad som
saknas.

**K5. Modellen får inte fylla ett slot den inte har underlag för.** URI, antal
och mått hämtas ur katalogen och databladen. Uppfunnen URI är hårt fel (I9).

### Spec-schemat

| Fält | Typ | Regel |
|---|---|---|
| `spec_id` | sträng | |
| `request` | sträng | operatörens ord, ordagrant, oredigerade |
| `goal` | sträng | modellens omformulering, en mening |
| `stations` | lista | `{ role, uri, count, qty_source }`. `uri` ur katalogindexet |
| `flow` | lista | `{ from_role, to_role, product }` — **materialets väg, aldrig koordinater** |
| `constraints` | lista | typade villkor, se nedan |
| `area` | objekt | `{ bounds_mm, aisle_min_mm, origin }` eller `null` |
| `control` | objekt | signaler, sekvens, förreglingar (form ur `81_mallschema.md`) |
| `expect` | objekt | facit. **Skrivs före planen** (I4) |
| `slots_open` | lista | ofyllda hårda slots. Icke-tom ⇒ `INCOMPLETE` |
| `clarify_round` | heltal | |

## 2. Villkorsspråket

Det enda stället i källan där ett villkor uttrycks maskinläsbart är
`Relation`-typen (`multimodal/types.py:310`) med `severity: hard|soft` och
`category: PHYSICS|SAFETY|SEQUENCE|PROXIMITY|TIMING`, samt cykelkontrollen på
`sequence`-kanter (`multimodal/validate.py:296`). Allt annat är prosa: i
`spec_generator.py` skrivs villkor som `"If found, import the STEP geometry"`
— text som ingen kod kan utvärdera.

**K6. Villkorsspråket är slutet.** Ett villkor är en trippel
`{lhs, op, rhs}` där `lhs` är en **namngiven storhet** ur en sluten lista, `op`
ur `{eq, ne, lt, le, gt, ge, in, exists}` och `rhs` ett tal, en sträng eller en
lista. Fri text i ett villkor är ett lintfel, inte en varning.
*Grind:* `S2_PROSE_CONDITION`.

### Storheterna som får stå i ett villkor

| Grupp | Exempel | Varifrån värdet kommer |
|---|---|---|
| spec-fält | `spec.stations.robot.count` | specen |
| datablad | `cell.footprint_mm.x` | celldatabladet |
| mätt scen | `scene.min_distance(a,b)` | `min_distance` (läsande verktyg) |
| mätt scen | `scene.collision_count` | `test_collision` |
| stegresultat | `step.S3.ok` | föregående stegs utfall |
| ögats dom | `eyes.PLACE`, `eyes.COLLISION` | ögats utdata, parsad |

**K7. Ett villkor får aldrig läsa modellens egen text.** Modellens påstående är
inte en storhet. Detta är samma regel som I11, flyttad ned i planeringslagret.

### Relationer i layouten

Samma typlista som källan, med samma hårda/mjuka gradering:

`on_top_of`, `above`, `inside`, `contains`, `supports`, `beside`,
`feeds`, `handoff`, `sequence`

**K8. Geometriska relationer verifieras geometriskt; semantiska verifieras av
ögat.** `feeds`, `handoff` och `sequence` markeras `skipped` i den statiska
domen (så gör källan, `static_eyes.py:419`) och går i stället in i planens
beroendekanter och ögats tidsserie.

## 3. Layout — spec blir placering

**Modellen anger relationer och ytkrav. Lösaren räknar koordinater. VC:s
gränssnitt räknar snäppningen.** (I8.)

### Lösarens tre steg

| Steg | Vad | Ärvt ur |
|---|---|---|
| L1 **grovutläggning** | stationer läggs i banor längs flödesaxeln, en markör per bana; markören går fram `footprint + aisle_min` | `composer.compute_layout_offsets` — utökad från en rad till banor |
| L2 **relationsuppfyllnad** | varje hård relation räknas om till en koordinat: `on_top_of` ur bbox-aritmetik, `beside` ur spel, `inside` ur behållarens innermått | `place_on_top_of`, `compute_stack_placement`, `_verify_relations` |
| L3 **mätning och rättning** | scenen byggs, `test_collision` och `min_distance` körs, överträdelser rättas med "blås upp med kroppsradien, putta längs minsta inträngning" | utputtningen i `canonical_instantiator.py:1045` |

**K9. Ingen koordinat lämnar lösaren omätt.** Varje tal i `LAYOUT` bär
`{value, method, gate}` där `gate` är den kontroll som godkände det. Ett tal
utan grind är ett lintfel.
*Detta är samma doktrin som `10_matta_fakta.md`: siffrans härkomst hör till siffran.*

**K10. Rättningen har ett tak.** L3 kör högst **fyra** varv. Femte varvet ⇒
`LAYOUT_UNSOLVED`, planen stannar, operatören får överträdelselistan med
förslag per station. `PRELIMINÄR` — taket ska sättas av en mätning över
scenariobänken i fas 9.

**K11. Passagemåttet är en mätning, inte en ritning.** Ett gångstråk är
uppfyllt när `min_distance` mellan två fotavtrycksväggar ≥ `aisle_min_mm`.
Källan har ingen sådan storhet alls; vi har `getMinimumDistanceDistance` och
båda närmaste punkter, så måttet är billigt och exakt.
`aisle_min_mm` har **inget förval**. Saknas det i specen är det ett hårt slot (K2).

**K12. Arbetsutrymme respekteras som en osynlig kropp.** `work_area_mm` ur
databladet blir en zon som ingen annan stations fotavtryck får skära. Är
`work_area_mm` `null` för en station rapporteras det som `WORK_AREA_UNKNOWN`
i layoutens utdata — det får inte tyst tolkas som noll.

**K13. Kollisionsdomen är hård.** Källan kör sin överlappskontroll vid varje
bygge men blockerar aldrig (`canonical_instantiator.py:1191`, "Advisory — never
blocks"). Hos oss: `collision_count > 0` efter L3 ⇒ planen får inte gå vidare
till körning. `expect.max_collisions` i `81_mallschema.md` är normalt 0.

**K14. Ett `connect` får aldrig ta koordinater.** Där ett gränssnitt finns är
snäppningen VC:s ansvar och lösaren skriver ingen position för den kopplingen.
*Grind:* `M5_COORDS_IN_CONNECTION` i mallintern, samma regel här.

### Layout-artefaktens form

```json
{
  "layout_id": "...",
  "frame": "world",
  "unit": "mm",
  "stations": [
    { "role": "infeed",
      "uri": "...",
      "anchor": { "value": [0, 0, 0], "method": "L1_lane_cursor", "gate": "P4" },
      "yaw_deg": { "value": 0, "method": "L2_flow_align", "gate": "P4" },
      "footprint_mm": [ ... ],
      "work_area": "UNKNOWN" }
  ],
  "relations_resolved": [ ... ],
  "measurements": { "min_pair_distance_mm": 0, "collision_count": 0,
                    "aisle_min_measured_mm": 0 },
  "unsolved": []
}
```

## 4. Plan — spec blir uppgiftsgraf

Källan har **ingen** enhetlig planstruktur. `PatchAction.order` / `depends_on`
finns som schema i `planner/models.py:21` men fylls aldrig med riktiga
beroenden och hela paketet har noll anropare. `workflow.py:51` har faser i
en rak lista utan grenar. `spec_generator.py:55` har `n`, `expected_tool` och
`post_condition` — och `post_condition` har **noll konsumenter i hela repot**.

Det sista är den viktigaste luckan att stänga: källan skriver efterkontroller
som prosa som ingen kontrollerar.

### Nodschemat

| Fält | Typ | Regel |
|---|---|---|
| `id` | sträng | unik i planen |
| `action` | sträng | en imperativ mening, för människan |
| `tool` | sträng | **måste finnas i verktygsregistret** |
| `args` | objekt | valideras mot verktygsschemat med AST-validering (grind 4) |
| `depends_on` | lista av `id` | explicita kanter, aldrig implicit ordning |
| `when` | villkor eller `null` | villkorsspråket enligt K6 |
| `post` | lista | **mätbara** efterkontroller, se K16 |
| `on_fail` | `abort` \| `retry:<n>` \| `branch:<id>` | |
| `effect` | `read` \| `write` | ärvs ur verktygskatalogen, får inte anges för hand |

**K15. Beroenden är explicita.** Listordning ger ingen ordning. En plan utan
`depends_on` någonstans och med fler än ett steg är misstänkt och lintas.

**K16. Varje `post` är ett verktygsanrop plus en jämförelse.** Formen är
`{tool, args, op, expect}`. Prosa i `post` är ett hårt fel.
Detta är rättelsen av källans döda `post_condition`.
*Grind:* `S3_UNVERIFIABLE_POST`.

**K17. Ett `post` får inte läsa sitt eget stegs utdata.** Ärvt skärpt ur
`lint_canonical_templates.py:1128` (`L-SC-01_REJECT_SELF_REF`), där ett facit
med `cube_path == target_path` gjorde grinden trivialt sann. Efterkontrollen
ska kunna falla.

**K18. Grafen är acyklisk.** Cykelkontroll med DFS på `depends_on`, samma form
som källans kontroll på `sequence`-kanter (`validate.py:296`).
*Grind:* `S4_PLAN_CYCLE`.

**K19. Okänt verktyg är hårt fel.** Källans `gap_analyzer.py` graderar i
`matched / partial / missing` och skickar en anteckning vidare — planen körs
ändå. Hos oss: `missing` ⇒ planen avvisas. `partial` ⇒ planen avvisas med
förslaget utskrivet. Detta är samma regel som I9, tillämpad på planen.

## 5. Sekvensering — plan blir anrop

**K20. Sekvensen härleds mekaniskt.** Topologisk sortering av `depends_on`,
med `id` som stabil sekundärnyckel så att samma plan alltid ger samma sekvens.
Modellen deltar inte i detta steg.

**K21. `effect=write` går i kön.** Ingen väg runt (I12). Sekvenseraren sätter
läget ur verktygskatalogen; ett steg som försöker sätta det själv är ett fel.

**K22. Determinism är mätt.** Samma spec ⇒ samma anropssekvens, byte för byte,
över tre körningar. Ett hashvärde av sekvensen skrivs i artefakten.
*Grind:* `P6`.

**K23. Läsande förfrågningar före skrivande.** Alla `post`-anrop och all
mätning som L3 behöver är `read` och får aldrig ligga i kön.

## 6. Kopplingen till ögats dom

Planeringslagret producerar två saker som ögat och grindarna ska kunna läsa.

**K24. Planens facit är ögats sektioner.** `spec.expect.must_pass` namnger
sektioner ur domskontraktet i `40_ogat.md` (`MOTION`, `TIMING`, `THROUGHPUT`,
`SAFETY`, `HONESTY`). Planen är inte grön förrän ögat säger `PASS` **och**
varje namngiven sektion är grön.

**K25. Grinden parsar ögats utdata, planen räknar inte om något.** I1, oförändrad.

**K26. Routning mellan billig och dyr dom.** Ärvd rakt ur
`multimodal/dual_verify.py:153`:

| Statisk dom | Handling | Regel |
|---|---|---|
| någon hård kontroll `fail` | `REJECT_FIX` | bygg **aldrig** en geometri som redan är fälld |
| räckvidd `uncertain` | `PROBE_REACH` | ett billigt IK-prov i VC före full körning |
| allt `pass`, ingen kalibrering | `RUN_GATE` | full körning. **Förvalet** |
| allt `pass`, kalibrering finns | `SKIP_GATE` | endast för de kontroller vars falsk-godkänt-frekvens är **mätt** |

**K27. `SKIP_GATE` är avstängd tills en mätning öppnar den.** Källan skriver
det själv i sin motivering: hoppet aktiveras aldrig okalibrerat. Vi skriver in
det som en spärr, inte som en avsikt.

**K28. Tre domar, inte två.** `pass` / `fail` / `uncertain`. `uncertain`
betyder "dyrare prov krävs" och är **aldrig** ett godkännande (I3).
Fail-open-stubbarna i källan (`verifier_registry.py:421` och `:471` returnerar
`pass` när argumentet saknas) ärvs inte; en kontroll utan sitt argument
returnerar `uncertain`.

**K29. Varje statisk fällning bär ett förslag.** Formen ärvs ur `static_eyes`:
`{action, path, constraint, suggest_position, human}`. En fällning utan
maskinläsbart förslag är halv, eftersom nästa varv då måste gissa.

## 7. Grindkedjan för planeringslagret

Ligger före grind 1 i `50_grindar.md` och matar in i den.

| # | Grind | Vad den mäter | Tröskel | Fångar inte |
|---|---|---|---|---|
| P1 | Specfullständighet | `slots_open` tom, `clarify_round ≤ 2` | hårt | om värdet är *rätt* |
| P2 | Specformslint | S1–S2, samt att `expect` bär minst ett mätbart krav | hårt | om facit är relevant |
| P3 | Katalogförankring | varje `uri` finns i katalogindexet; varje station har ett datablad med `footprint_mm` | 0 uppfunna URI:er över N försök | om komponenten passar uppgiften |
| P4 | Layoutdom, statisk | överlapp, relationer, ytbegränsning, arbetsutrymme — allt före bygge | 0 hårda `fail` | allt som bara syns i rörelse |
| P5 | Layoutdom, mätt | `test_collision` = 0 och `min_distance` ≥ `aisle_min_mm` i den byggda scenen | hårt | dynamisk kollision under körning |
| P6 | Plangraf | S3–S4, K19, plus determinism: tre sekvenseringar ger samma hash | hårt | om planen löser uppgiften |
| P7 | Efterkontrollstäckning | varje `write`-steg har minst ett `post` som kan falla | 100 % | om kontrollen mäter rätt sak |
| P8 | Planens dom | ögat säger `PASS` och varje sektion i `must_pass` är grön | hårt | fältbuss och verklig hårdvara |

**P4 är fasgränsen.** En layout som inte klarar P4 får inte byggas i VC.
Det är den enda grinden i kedjan som sparar en hel körning.

## 8. Felklasser som lagret ska fånga

Kompletterar `82_felklasser.md`. Var och en fick sin klass ur en läst mekanism
eller en läst lucka i källan.

| Kod | Klass | Härkomst |
|---|---|---|
| `PL1` | Ofylld hård variabel som tyst fick ett förval | källans klarifiering är fail-open |
| `PL2` | Uppfunnen URI eller uppfunnet verktygsnamn i planen | `gap_analyzer` graderar men stoppar inte |
| `PL3` | Prosavillkor som ingen kan utvärdera | `spec_generator`s `"If found, …"` |
| `PL4` | Efterkontroll som inte kan falla | `L-SC-01_REJECT_SELF_REF` |
| `PL5` | Efterkontroll utan konsument | källans `post_condition`, noll konsumenter |
| `PL6` | Implicit ordning: steg som fungerar bara i listordning | `workflow.py`s raka faslista |
| `PL7` | Överlapp som byggdes ändå | "Advisory — never blocks" |
| `PL8` | Klass gissad ur namn i stället för läst ur katalogen | `_SCENERY`-delsträngarna |
| `PL9` | Kontroll som svarade `pass` utan sitt argument | de två stubbarna i `verifier_registry` |
| `PL10` | Passage som ingen mätte | ingen sådan storhet finns i källan |
| `PL11` | Två halvor av samma begrepp som inte möts | `Relation` mot `layout["relations"]` |
| `PL12` | Koordinat i en koppling som gränssnittet skulle ha räknat | I8 |

## 9. Faser

Läggs in mellan fas 4 och fas 5 i `70_faser.md`.

| # | Fas | Levererar | Grind som stänger |
|---|---|---|---|
| 4b | **Databladen** | `bank/celler/*.json` ur katalogen, `footprint_mm` mätt i VC | P3 grön över hela katalogindexet. Andel poster med `work_area_mm` rapporterad, inte gissad |
| 4c | **Spec och frågeställare** | schema, lint, slotlista med `needed_for` | P1–P2. Tio vaga begäranden ger rätt frågor och inga andra |
| 4d | **Planeraren** | plangraf, villkorsspråk, sekvenserare | P6–P7. Determinism mätt över tre körningar |
| 5a | **Placeringslösaren** | L1–L3, layoutartefakt | P4 grön statiskt, sedan **P5 mätt i VC** på N mållayouter: noll kollisioner, passagemåttet uppfyllt |

**Fas 5a ersätter inte fas 5**; den är dess första hälft. Fas 5 stängs som
förut när alla gränssnitt är kopplade.

## 10. Vad som medvetet inte ligger i version 1

Ärlighet om räckvidden, i samma anda som `50_grindar.md`.

- **Ingen optimering.** Lösaren söker en **giltig** layout, inte en kort
  transportsträcka eller ett högt flöde. Optimering kräver ett mål, och ett
  mål kräver en mätning vi ännu inte har.
- **Ingen omplanering under körning.** Planen fastställs före första
  skrivande anropet. Ändras förutsättningarna görs en ny plan.
- **Ingen automatisk hallgeometri.** Väggar, pelare och portar kommer in som
  komponenter ur katalogen eller som `area.bounds_mm`, inte ur en ritning.
- **Ingen parallell process i grafen.** `depends_on` uttrycker ordning; att två
  steg *kan* köras samtidigt uttrycks inte, eftersom bryggan ändå kör ett
  anrop i taget mot VC:s tråd.
- **Ingen ergonomi- eller utrymningsdom.** `work_area_mm` reserverar yta.
  Att bedöma om ytan räcker för en människa är inte simuleringens uppgift och
  gränsar till `50_grindar.md`:s säkerhetsgräns.
