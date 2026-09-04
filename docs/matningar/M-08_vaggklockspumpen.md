# M-08 — väggklockspumpen: `app.startSimulation()`

**Datum:** 2026-09-04 · `~/.wine-vc-test` · VC Premium 4.10 · headless `:99`
**Status:** löser den blockerare som stått öppen sedan M-04.

## Frågan

M-06: `sim.run(t)` kör i maxfart, `SimSpeed` påverkar ingenting.
M-07: trådar svälter. Bryggan hade ingen källa som tickar i verklig tid.

Kvar stod `app.startSimulation()` — gränssnittets play-knapp.

## Mätt

```
16:20:26 startSimulation() atervande efter 0.008 s
16:20:26 direkt efter: IsRunning=True SimTime=0.000
```

Den **återvänder** — till skillnad från `sim.run()`, som blockerar tills
förloppet är slut. Simuleringen fortsätter i bakgrunden.

Skriptets `OnRun` med `delay(0.05)`, mätt över 155 sekunder:

```
1788531628.945 ONRUN START
1788531629.952 n=20   sim=1.00   wall=1.01   kvot=0.994
1788531630.952 n=40   sim=2.00   wall=2.01   kvot=0.997
...
1788531780.945 n=3040 sim=152.00 wall=152.00 kvot=1.000
1788531783.948 n=3100 sim=155.00 wall=155.00 kvot=1.000
```

| Storhet | Värde |
|---|---|
| Takt | **20,0 Hz**, 3 100 varv utan ett enda missat |
| Simuleringstid mot väggklocka | **kvot 1,000** efter inkörning |
| Drift över 155 s | under 0,01 s |

## De två körsätten, som nu är åtskilda

| Anrop | Beteende | Användning |
|---|---|---|
| `sim.run(t)` | blockerar, maxfart, 20 simulerade sekunder på 0,01 s | **Ögat** — provta ett förlopp så fort det går |
| `app.startSimulation()` | återvänder direkt, realtid, `IsRunning=True` | **Bryggan** — betjäna begäran i väggklockstid |

Det förklarar också varför `SimSpeed` inte gjorde något i M-06: den styr
den interaktiva uppspelningen, inte satskörningen.

## Bryggans modell, nu giltig

Bryggan är ett `VC_SCRIPT`-beteende på en dold komponent. `OnRun` är pumpen.
Allt som rör VC sker där, på huvudtråden. Begäran läggs i kö, pumpen betar av
kön 20 gånger i sekunden. Ingen tråd, ingen timer, ingen .NET.

## Öppet

`sim.SimTime` läst från **kommandots** scope stod kvar på 0,000 medan skriptets
eget scope samtidigt läste 1,00 och uppåt. `IsRunning` var däremot korrekt i
båda. Simuleringstid ska därför läsas i skriptets scope. Orsaken är omätt.

Pumpen lever bara medan simuleringen går. Vad som händer med köade begäran när
operatören stoppar simuleringen är obestämt och hör till fas 1:s protokoll.

## Vad som INTE är mätt

* Kvoten 1,000 är mätt över **en** körning på 155 s, i en tom scen, med en pump
  som inte betjänade någon begäran. Under last — köade anrop, scenändringar,
  ögats provtagning — är kvoten omätt.
* *"3 100 varv utan ett enda missat"* räknas ur skriptets **egen** räknare. Ett
  varv som skriptet självt hoppade över hade inte synts i den räkningen; det
  finns ingen oberoende klocka som räknar varven.
* Driften *"under 0,01 s över 155 s"* är en körning på tre minuter. Om driften
  växer över en timme eller ett dygn är inte mätt.
* Att `SimSpeed` styr interaktiv uppspelning och inte satskörning är en
  **förklaring** till M-06:s utfall. Den prövades inte här genom att sätta
  `SimSpeed` under en `startSimulation()`.
* Att `sim.SimTime` läst ur kommandots scope stod kvar på 0,000 är mätt.
  Orsaken står som omätt i texten och är det fortfarande, så regeln *"läs
  simuleringstid i skriptets scope"* är en åtgärd utan känd mekanism.
* Vad som händer med köade begäran när operatören stoppar simuleringen är
  obestämt och inte mätt. Det står i texten och lämnades till fas 1:s protokoll.
* Hela mätningen är gjord headless under Wine. Att `startSimulation()` beter sig
  likadant med gränssnittet öppet, där uppspelningen faktiskt ritas, är oprövat
  (M-22 i `RESERVERADE.md`).
