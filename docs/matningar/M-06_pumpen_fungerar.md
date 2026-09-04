# M-06 — pumpen fungerar: vcScript.OnRun med delay()

**Datum:** 2026-09-04 · `~/.wine-vc-test` · VC Premium 4.10 · headless `:99`

## Vad som saknades

Skriptets källkod måste börja med **`from vcScript import *`**. Utan den raden
finns varken `delay()`, `getSimulation()` eller `getComponent()` i skriptets
scope, `OnRun` kastar `NameError` direkt, och **VC slukar felet tyst**.

Bekräftat i medföljande kod: `Commands/Wizards/SensorWizard.py` börjar varje
skriptmall med just den raden.

Detta är andra gången ett tyst fel kostat tid. Bryggan ska därför alltid
logga sin egen start, och skript ska alltid ha en egen felfångare.

## Hook-ordningen, mätt

```
OnReset → OnStart → OnRun (loop) → OnStop
```

## Takten, mätt

| Storhet | Värde |
|---|---|
| `delay(0.05)` i simuleringstid | **exakt 20,0 Hz**, stabilt över 560 varv |
| Väggklocka för 560 varv | under 0,01 s |
| `sim.run(30.0)` | 0,01 s väggklocka |
| `sim.SimSpeed` | var redan 1,0; att sätta den ändrade **ingenting** |

**Slutsats:** `sim.run()` anropad från Python kör alltid i maxfart.
Simuleringstiden är exakt styrbar, väggklockan är det inte.

## Vad det betyder

| Användning | Duger detta? |
|---|---|
| **Ögat** — provta ett förlopp | **Ja, utmärkt.** Exakt 20 Hz i simuleringstid, och mätningen går på bråkdelar av en sekund |
| **Bryggan** — betjäna begäran över väggklockstid | **Nej.** Pumpen lever bara medan `run()` pågår, och det är över på ett ögonblick |

## Öppet

Realtidspacing. Kandidat: `vcApplication.delayRealTime(sekunder)`, dokumenterad
som "executes a delay that halts a running simulation". Anropad inifrån skriptets
`OnRun` borde den pacea loopen mot väggklockan. **Oprövad.**

Alternativ om den inte bär: loopa `sim.run(0.05)` från kommandots modulnivå
och betjäna kön mellan anropen. Då måste det mätas att VC:s gränssnitt förblir
användbart.
