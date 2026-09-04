# M-04 — VC:s exekveringsmodell, och varför bryggan måste byggas om

**Datum:** 2026-09-04 · `~/.wine-vc-test` · VC Premium 4.10 · headless `:99`

## Tre mätningar, ett resultat

| Fråga | Utfall |
|---|---|
| Fyrar `OnRender` när appen står stilla? | **Nej.** En gång, sedan inget på 135 s (M-03) |
| Fyrar `OnIdle`? | **Nej.** Bunden utan fel, noll anrop. Dessutom märkt föråldrad |
| Körs en **bakgrundstråd** startad ur ett kommando? | **Nej.** Tråden startades men skrev aldrig något på 105 s |
| Finns en generell timer i API:t? | **Nej.** Sökning på timer, schedule, dispatch, invoke, async, defer, tick, poll gav noll |

Anrop från huvudtråden fungerar: `Components`, `getSimulation`, `SimTime`,
`findCamera`, `load` svarade alla korrekt.

## Slutsats

**Trådmodellen i `31_brygga_protokoll.md` är ogiltig.** Den förutsatte en
socketserver på bakgrundstråd plus en pump på VC:s tråd. Ingen av delarna finns.

VC:s Python är **kooperativ och simuleringsdriven**, inte trådad. All
schemaläggning i API:t hänger på simuleringstid:
`vcScript.delay`, `condition`, `triggerCondition`, `OnSimulationUpdate`,
`vcApplication.delayRealTime`.

## Kandidaten

`vcScript` är ett beteendeskript på en komponent, med en egen exekveringskontext
som VC pumpar:

| Del | Vad den ger |
|---|---|
| `OnRun` | huvudprogram som VC kör som en korutin |
| `delay(t)` | lämnar tillbaka kontrollen, blockerar inte gränssnittet |
| `condition(f, timeout)` | väntar tills ett villkor håller |
| `suspendRun` / `resumeRun` | pausa och återuppta |
| `OnSignal` | fyrar när en kopplad signal ändras |
| `OnSimulationUpdate` | per uppdatering |

En dold hjälpkomponent med ett sådant skript, vars `OnRun` loopar
`while True: delay(0.05); dränera kön`, är en **äkta pump**.

## Öppen fråga, blockerande för fas 1

`vcScript` körs **under simulering**. Hur betjänas en begäran när simuleringen
står stilla? Kandidater att mäta:

1. `sim.update()` anropad utifrån — fyrar den `OnSimulationUpdate`?
2. Köra simuleringen kontinuerligt i en tom hjälpscen, och pausa den vid
   scenändringar
3. `condition()` med lång timeout som väntar på en fil eller en signal

**Ingen av dem är prövad.** Fas 1 kan inte stängas förrän en av dem mätts.

## Vad detta säger om metoden

Jag specade en trådmodell utan att ha prövat att trådar över huvud taget körs.
Det var ett antagande förklätt till design. Att fas 1:s grind krävde en **mätt**
takt var det som avslöjade det, och det gjorde det innan bryggan var skriven.
