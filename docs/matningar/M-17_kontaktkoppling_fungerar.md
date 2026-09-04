# M-17 — komponenter går att koppla ihop, på kontaktnivå

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Löser:** den blockerare M-14 och M-16 lämnade öppen.

## Vad som var fel i M-14 och M-16

Jag band **fel fält till fel sak.**

Ett `VC_TRANSPORTFIELD` har egenskaperna `Name, Transport, Connection`, där
`Transport` är en `Ref<ComponentProcessor>`. Jag band den till en `vcMotionPath`
(gav `SystemError`) och sedan till en `vcTransport` (gick igenom) — och då
**dödade `canConnect` bryggan utan ett ord** (M-16).

Ett `VC_FLOWFIELD` har i stället egenskaperna **`Name, Container, Port, PortName`**.
Det binder alltså en *behållare* och en *kontakt*, inte en processor.

Och beteendena bär kontakter. Mätt genom en sond över alla fälttyper och alla
flödesbeteenden:

| Beteende | Kontakter |
|---|---|
| `vcOneWayPath` | `Input` (index 0, typ 1), `Output` (index 1, typ 2) |
| `vcSimContainer` | `Input` (0, typ 1), `Output` (1, typ 2) |
| `vcTransport` | `Input` (0, typ 1), `Output` (1, typ 2) |
| `vcContainerFiller` | `Input` (0, typ 1), `Output` (1, typ 2) |
| `rResourceCreator` | **`Output` (0, typ 2)**, `Input` (1, typ 1) |
| `vcMovementPath` | `Input` (0, typ 1), `Output` (1, typ 2) |

Typ 1 är in, typ 2 är ut. Notera att resursskaparen har dem i **omvänd ordning** —
ett index som antas i stället för att läsas ur `Type` blir fel just där.

## Vad som fungerar

Två transportörer byggda ur receptet — komponent, `VC_ONEWAYPATH`, två
gränssnitt med sektioner och flödesfält bundna via heltalsindex — och kopplade:

```
koppla ihop dem      done      via=B5
{"connected": true, "via": "B5", "a_is_connected": false, "a_connected_to": []}
```

**`B5` är kontakt mot kontakt**, alltså `vcConnector.connect()` mellan
beteendenas portar, utan att gå via gränssnitten.

## Vad som fortfarande inte fungerar

| Väg | Utfall |
|---|---|
| `iface.canConnect(other)` + `connect` (E0) | `canConnect` är **False** |
| `app.connectComponents(a, b)` (G0) | returnerar **False** |
| **`vcConnector.connect()` mellan portar (B5)** | **fungerar** |

Att `a_is_connected` är `false` efteråt är väntat: det är *gränssnittens*
tillstånd, och de är inte kopplade. Kopplingen ligger på kontakterna.

Och en viktig sidoeffekt: `canConnect` **kraschade inte** den här gången.
Kraschen i M-16 kom alltså ur den felaktiga transportbindningen, inte ur
anropet självt. M-16:s slutsats att ett läsande verktyg kan döda bryggan står
kvar — men orsaken var en ogiltig bindning som VC inte kontrollerade.

## Vad som återstår innan en linje lever

En linje byggdes: mall, matare (`VC_COMPONENTCREATOR`), två banor, sänka
(`VC_COMPONENTCONTAINER`). Banorna kopplades. Matare och sänka gjorde det inte —
receptet letar efter ett beteende som inte finns på dem, trots att sonden visar
att de **har** kontakter.

Simuleringen kördes 6 sekunder (69,4 → 75,5 s simuleringstid). Antalet
komponenter stod stilla på 6. **Inga produkter skapades.**

Kvar att mäta:
1. rätt beteendeuppslag för matare och sänka vid kontaktkoppling
2. matarens inställningar: `Interval`, `Limit`, `TemplateComponent`
3. om en produkt faktiskt vandrar längs banan när allt är kopplat

Det tredje är det enda som räknas. Tills en produkt rört sig är linjen en
ritning, inte en linje.
