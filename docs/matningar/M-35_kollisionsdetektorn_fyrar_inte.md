# M-35 — kollisionsdetektorn fyrar inte, och därför är fas 5 inte stängd

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Följd:** fyra gröna layouter är **inte** bevis. En grind som aldrig fällt
något mäter ingenting.

## Vad som byggdes

Blockgeometri fungerar (M-33). Fyra av layoutmotorns lösta scener byggdes i VC
med verklig geometri ur banken — transportband, givare, kassationslådor — och
placerades på de koordinater motorn räknat fram.

VC:s kollisionsdetektor sa **noll träffar** i alla fyra.

## Och sedan det trasiga fallet

Två objekt flyttades medvetet in i varandra. Detektorn sa **fortfarande noll**.

Därmed betyder de fyra gröna svaren ingenting. De hade sett likadana ut om
scenen bestått av tre lådor staplade på exakt samma koordinat.

## Vad som prövats, allt med samma utfall

Två kuber om 1000 × 1000 × 1000 mm, placerade **100 mm isär** — alltså 900 mm
överlapp i varje axel:

```
A_bound   [500.0, 500.0, 500.0]     geometrin finns och har ratt matt
A_center  [500.0, 500.0, 500.0]
```

| Uppställning | `testAllCollisions(0.0)` | `testComponentCollisions()` | `testNodeCollisions()` | `HitCount` |
|---|---|---|---|---|
| `NodeListA/B` = komponenter | False | False | False | 0 |
| `NodeListA/B` = `findNode(namn)` | False | — | False | 0 |
| med `rebuild()` före | False | False | — | 0 |
| med `sim.update()` före | False | — | — | 0 |

`findNode('A')` returnerar en **`vcComponent`** — komponenten är sin egen
rotnod, så de två uppställningarna är samma sak.

## Ett dokumentationsfel funnet på vägen

`api.xml` deklarerar `vcCollisionDetector.StopOnCollision` som en egenskap.
På objektet `sim.newCollisionDetector()` returnerar finns den **inte**:

```
AttributeError: Attribute 'StopOnCollision' not found.
```

Ögats provtagare satte den rakt av, med hänvisning till M-13. Den sättningen är
nu inlindad i `try`, men försöket är kvar — ett stopp river simuleringen och med
den pumpen, så den måste försökas när den finns.

## Trolig orsak, omätt

`vcCollisionDetector` ärver en layoutpost: den bär `IsPersistent`, `Name` och
`Type` med hänvisning till *Layout Item Constants*. En detektor skapad med
`sim.newCollisionDetector()` kan mycket väl vara **fristående** och behöva läggas
in i layouten innan den utvärderas — eller bara utvärderas medan simuleringen
stegar.

Det är en hypotes. Nästa mätning prövar den.

## Vad det betyder för fas 5

Grinden lyder *"N mållayouter byggda: noll kollisioner, alla gränssnitt
kopplade"*. Två av tre led är på plats:

| Led | Läge |
|---|---|
| mållayouter byggda i VC med verklig geometri | **klart** |
| noll kollisioner | **kan inte avgöras** — domaren svarar alltid noll |
| alla gränssnitt kopplade | kontaktnivån fungerar (M-17), gränssnittsnivån inte |

Fasen står alltså öppen, och den står öppen på en **mätt** orsak.

Acceptanskörningen `tests/protocol/kor_fas5_layout.py` räknar det trasiga fallet
som ett underkännande, så den kan inte bli grön förrän detektorn faktiskt fäller
ett överlapp. Det är hela poängen med att köra det trasiga fallet.

## Vad som INTE är mätt

* **Rätt observation, fel diagnos.** M-36 mätte orsaken: `NodeListA` tar emot en
  lista och **tömmer** den. Detektorn hade ingenting att jämföra. Varje rad i
  tabellen här mäter alltså en tom nodlista, inte en detektor som ser fel — och
  raden `testMinimumDistance(5000.0) → False` såg ut som ett svar om geometri.
* Hypotesen under *Trolig orsak, omätt* — att detektorn måste ligga i layouten —
  prövades i M-36 och var **fel**. En detektor skapad som layoutpost via
  `app.createLayoutItem` ger också noll.
* De fyra gröna layouterna mäter att fyra scener gick att **bygga**. De mäter
  ingenting om kollisioner, och texten säger det.
* Det trasiga fallet är **två kuber**, en uppställning, en förskjutning. Att
  detektorn skulle fungera för någon annan geometri är inte uteslutet av
  mätningen.
* `StopOnCollision`-fyndet gäller det objekt `sim.newCollisionDetector()`
  returnerar. Om egenskapen finns på en detektor skapad på annat sätt är inte
  mätt, och `try`-omslutningen i provtagaren är därför en gissning som lämnats
  kvar.
* Att fasen står öppen *"på en mätt orsak"* stämde inte när det skrevs: orsaken
  som angavs var fel, och den riktiga orsaken kom i nästa mätning.
