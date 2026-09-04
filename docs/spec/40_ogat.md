# Ögat — vc_eyes

Ärver principen ur `scripts/qa/scene_eyes.py`: en tät tidsserie ur levande
tillstånd, med härledd statistik. **Bilder är en svagare signal och är valfria.**

## Vad som provtas per steg

| Fält | Källa i VC | Anm |
|---|---|---|
| `t` | `sim.SimTime` | simulerad tid, inte väggklocka |
| `part_p`, `part_q` | `vcNode.WorldPositionMatrix` → `vcMatrix.P`, `getQuaternion()` | per spårat objekt |
| `tool_p`, `tool_q` | samma, på verktygsnoden | |
| `joints` | `vcServoController.Joints` | per robot |
| `mind` | `collisionDetector.getMinimumDistanceDistance()` | per bevakat nodlistepar |
| `mindp1/p2` | `getMinimumDistancePoint1/2()` | var de är närmast varandra |
| `hit` | `getHitNodeA/B`, `getHitFeatureA/B` | vid träff |
| `sig` | signalvärden per bevakad signal | flanker härleds |
| `plc` | OPC UA-variabelvärden | **samma tidslinje som scenen** |
| `stat` | `vcStatistics` per station | ankomna, avgångna, medel, min, max |

Signalflanker och PLC-variabler på samma tidsaxel som fysiken är hela poängen.
Ett tidsfel blir då ett fasförhållande som går att läsa av.

## Vad som härleds

Ur pose över tid, utan att kräva kraftdata:

- **greppad**: detaljens pose i verktygets ram konstant
- **glider**: rotation i verktygsramen sedan greppets början
- **tappad**: koppling bryts, z faller, sluthöjd på fel nivå
- **aldrig tagen**: detaljen oförändrad i världen medan verktyget går därifrån
- **utslungad**: fart eller z utanför rimligt
- **rätt placerad**: slutpose inom målets bbox och satt

Ur signaler och PLC-variabler:

- **flanktider** per signal
- **kommenderat mot uppnått**: fördröjning mellan utsignal och verklig rörelsestart
- **uppehåll** per station
- **kapplöpning**: två utgångar höga inom samma scanfönster
- **svält och blockering**
- **cykeltid** per station och per produkt

## Domskontraktet

Samma form som källan: **fri text på stdout med fasta markörer**, JSON på disk.
Grinden parsar textmarkörerna. Ögat är den enda som fäller dom.

```
=== VC EYES ===
TEMPLATE: <namn>
DUR: <s>  SAMPLES: <n>  RATE: <hz>
--- MOTION
GRIP: <FORMED t=.. dist=..mm | NEVER FORMED>
CARRY: <RIGID .. deg | SLIPPING .. deg | INCONCLUSIVE span=..s>
PLACE: <IN TARGET | OFF BY ..mm | DROPPED z=..>
--- TIMING
EDGE <signal> t=.. <RISE|FALL>
LATENCY <signal>->motion: ..ms
DWELL <station>: ..s  (krav ..s)
RACE: <none | <sigA>,<sigB> within ..ms>
--- THROUGHPUT
STATION <namn>: in=.. out=.. avg=..s min=..s max=..s
--- SAFETY
MINDIST <par>: ..mm at t=..
COLLISION: <none | <nodA> x <nodB> at t=..>
--- HONESTY
TELEPORT_TRANSFER: <ok | VIOLATION dist=..mm at t=..>
BLOWUP: <ok | VIOLATION vmax=..>
UNDERGROUND: <ok | VIOLATION zmin=..>
=== VC EYES VERDICT: <PASS|FAIL> (<orsak>) ===
```

## Hederlighetsgrindar

Fångar fysiskt omöjliga framgångar. Ärvda i anda från `scene_observer.py`.

| Grind | Villkor | Fångar |
|---|---|---|
| `TELEPORT_TRANSFER` | avstånd verktyg–detalj i det ögonblick `transfer()` sker | **Kritisk i VC.** Standardgreppet är icke-fysiskt; utan den ser en miss ut som lyckad plockning |
| `BLOWUP` | maxfart över tröskel | numerisk explosion |
| `UNDERGROUND` | z under golvnivå | genomträngning |
| `NEVER_GRIPPED` | greppmängden tom hela körningen | tyst misslyckande |
| `DWELL_TOO_SHORT` | uppehåll under transportörens eftersläpning | den vanligaste tidsbuggen |

## Tröskelregel

**Varje tal bär den incident det kom ur.** Ingen tröskel skrivs in utan en
kommentar som namnger mätningen som satte den. Trösklar utan härkomst är
den enda kända svagheten i källans `scene_eyes` — fyra tal där saknar motivering.
Vi upprepar inte det.

Alla trösklar i första versionen märks `PRELIMINÄR` tills en mätning satt dem.
