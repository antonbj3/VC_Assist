# M-41 — produkten matas fram av sig själv och åker: mätt i tal

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · testprefixet
`~/.wine-vc-test`, headless `:99`
**Bygger på:** [M-40](M-40_varfor_mataren_aldrig_fyrade.md), som mäter varför
det inte gick tidigare.

Fas 5:s sista led är stängt: en produkt uppstår **utan att någon ber om den**
och rör sig längs en transportör. Det som följer är talen, inte påståendet.

## Linjen

Byggd av receptet `flodeslinje` i `svc/vc_assist_svc/byggrecept/recept.py`,
kört ur `vc_assist_startskript.py` **före** `startSimulation()`:

```python
recept.generera("flodeslinje", {
    "name": "M42", "mall": "M42_Produkt",
    "intervall": 4.0, "grans": 100000,
    "hastighet": 250.0, "banlangd": 2500.0})
```

Vad VC svarade när bygget var klart:

```
matare              M42_Matare        bana            M42_Bana
creator             {enabled: True, interval: 4.0, limit: 100000,
                     part: '', template: 'M42_Produkt'}
path_length         2500.0            speed           250.0
matarens_lage       [0.0, 0.0, 0.0]   banans_lage     [400.0, 0.0, 0.0]
canConnect          True              connected       True
is_connected        True
```

Mallen `M42_Produkt` är ett block byggt programmatiskt i samma skript. Den har
`Uri = "vcid:"` och `VCID = ""` — **ingen katalogidentitet alls**, satt genom
`TemplateComponent`. `Part` är tom strängen.

## Att den skapas av sig själv

Fjorton avläsningar mellan simtid 11,910 och 38,370. Ingen av dem anropar
`create()`; alla är läsningar. Skapelsetiderna som dök upp i banans behållare:

```
CreationTime   4.0  8.0  12.0  16.0  20.0  24.0  28.0  32.0  36.0
skillnad            4.0  4.0   4.0   4.0   4.0   4.0   4.0   4.0
```

Nio produkter, exakt `Interval = 4.0` simulerade sekunder isär, åtta mellanrum
i rad utan avvikelse.

## Att den rör sig

En enskild produkt, den som skapades vid simtid 20,0, följd genom fem prov.
`banavstand` är `vcComponent.getPathDistance()`, `varld_x` är
`WorldPositionMatrix.P.X`:

| simtid | banavstånd (mm) | värld-x (mm) | `(t − 20) · 250` |
|---:|---:|---:|---:|
| 20,045 | 11,250 | 407,75 | 11,3 |
| 22,060 | 515,000 | 910,75 | 515,0 |
| 24,080 | 1020,000 | 1413,25 | 1020,0 |
| 26,100 | 1525,000 | 1920,25 | 1525,0 |
| 28,160 | 2040,000 | 2434,75 | 2040,0 |

Banavståndet följer `Speed · tid` på tredje decimalen. Värld-x ökar lika mycket
som banavståndet i varje steg, så det är komponenten i **världen** som flyttar
sig, inte bara ett räknarvärde i banan.

Över hela serien, alla par av på varandra följande prov för samma produkt:

```
hastighet ur 25 par:   min 250.0000 mm/s   max 250.0000 mm/s
```

`Speed` var satt till 250,0. Det är inte ett ungefär: spridningen är noll över
25 oberoende differenskvoter.

Produkten faller av i banans andra ände (`PathLength = 2500`, ingen utgång
kopplad) och försvinner ur scenen. Därför står `bana_antal` och växlar mellan
2 och 3 i serien i stället för att växa — det är utflödet, inte en förlorad
produkt.

## Den trasiga fixturen: två linjer som INTE ska flöda

Samma startskript, samma ögonblick, tre linjer sida vid sida (mätningen ligger
i M-40, talen upprepas här för att grinden ska gå att läsa på ett ställe).
Tolv prov, simtid 9,76 → 37,77:

| Linje | Skillnad mot A | `PathLength` | Produktobservationer | Skapelsetider |
|---|---|---:|---:|---|
| **M41A** | — | 3000,0 | **35** | 0, 5, 10, 15, 20, 25, 30, 35 |
| **M41B** | `path.update()` utelämnat | 0,0 | **0** | inga |
| **M41C** | gränssnitten inte kopplade | 3000,0 | **0** | inga |

Sju hela intervall utan en enda produkt i B och C, medan A matade i takt.
Grinden skiljer alltså det som flödar från det som inte gör det, och den gör
det på två olika sätt att vara trasig.

## Vad som inte är visat

* **Produkten lämnar aldrig banan till något annat.** Banans utgångs­gränssnitt
  finns och är bundet, men ingen sänka är kopplad till det. Produkten faller av
  i änden och tas bort. Ett led till — bana → bana, eller bana → sänka — är
  **oprövat**.
* **Inget skript, ingen station, ingen process.** Linjen är matare + bana. Det
  som fas 7 behöver ovanpå det är inte mätt här.
* **`Accumulate = True` är satt men aldrig belastad.** Ingen produkt har blivit
  blockerad av en annan i de här serierna.
* **Rörelsen är mätt i simulerad tid, inte i väggklockstid.** Serien är tagen
  genom bryggans kö, ett prov per anrop; simtiden i varje prov är läst i
  skriptets eget scope (M-08).
