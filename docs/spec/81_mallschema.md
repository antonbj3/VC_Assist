# Mallschema

Ett scenario är en JSON-fil. `task_id` **måste** matcha filnamnet.
Lintern avvisar på regelkod, aldrig med fritext. Struktur ärvd ur källprojektets
kanonmallar, innehåll nytt.

## Fält

### Kärna, obligatoriskt för alla

| Fält | Typ | Regel |
|---|---|---|
| `task_id` | sträng | `^(T\|P\|L\|S\|A\|H\|C)-\d{2}$`, matchar filnamnet |
| `title` | sträng | kort, en rad |
| `goal` | sträng | vad som ska uppnås, i klartext |
| `targets_class` | lista | felklasser ur `82_felklasser.md` som scenariot är byggt att fånga |
| `difficulty` | heltal 1–5 | |
| `failure_modes` | lista av strängar | kända sätt att lyckas fel |

### Scen

| Fält | Typ | Regel |
|---|---|---|
| `scene.components` | lista | varje post: `{ role, uri, count }`. `uri` **måste** finnas i katalogindexet |
| `scene.connections` | lista | `{ from_role, to_role }`. **Aldrig koordinater** |
| `scene.layout_uri` | sträng eller null | förbyggd layout om scenen inte byggs av agenten |

### Styrning

| Fält | Typ | Regel |
|---|---|---|
| `control.signals` | lista | `{ name, dir: in\|out, type: bool\|int\|real, comment }` |
| `control.sequence` | lista | avsedd ordning i klartext, ett steg per rad |
| `control.timing` | objekt | `{ dwell_s: {station: float}, cycle_s: float, tolerance_s: float }` |
| `control.interlocks` | lista | förreglingar som måste hålla |

### Facit

| Fält | Typ | Regel |
|---|---|---|
| `expect.throughput_per_h` | float eller null | mål vid stationär drift |
| `expect.runs` | heltal | antal oberoende körningar, minst 3 |
| `expect.warmup_s` | float | uppvärmning som inte räknas |
| `expect.must_pass` | lista | ögats sektioner som måste vara gröna |
| `expect.max_collisions` | heltal | normalt 0 |
| `expect.min_clearance_mm` | float | |

### Status

| Fält | Typ |
|---|---|
| `verified_status` | `unverified` \| `L1` \| `L2` |
| `last_run` | objekt eller null |

## Lintregler

| Kod | Fel |
|---|---|
| `M1_MISSING_FIELD` | obligatoriskt fält saknas |
| `M2_ID_MISMATCH` | `task_id` matchar inte filnamnet |
| `M3_ID_PATTERN` | `task_id` bryter mönstret |
| `M4_UNKNOWN_URI` | komponent-URI finns inte i katalogindexet |
| `M5_COORDS_IN_CONNECTION` | koordinater i `scene.connections` |
| `M6_NO_FACIT` | `expect` saknar mätbart krav |
| `M7_RUNS_TOO_FEW` | `expect.runs` under 3 |
| `M8_UNKNOWN_CLASS` | `targets_class` innehåller okänd felklass |
| `M9_SIGNAL_DIR` | signal utan `dir` eller med okänd riktning |
| `M10_TIMING_NO_TOLERANCE` | tidskrav utan tolerans |
| `M11_EMPTY_SEQUENCE` | `control.sequence` tom |
| `M12_STATUS_WITHOUT_RUN` | `verified_status` över `unverified` utan `last_run` |

`M5` och `M6` är de bärande. `M5` skyddar principen att modellen anger relationer
och VC räknar geometrin. `M6` skyddar regeln att facit skrivs före försöket.
