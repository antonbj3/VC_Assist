# M-13 — exakt en operation dödar pumpen

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless `:99`

## Mätt

Sex operationer körda genom bryggans kö mot en levande simulering, i följd,
med kontroll av `IsRunning` och att bryggan svarar efteråt:

| Operation | Utfall | Simuleringen går efteråt | Bryggan svarar |
|---|---|---|---|
| `app.createComponent()` + namn | done | ja | ja |
| flytta via `PositionMatrix` | done | ja | ja |
| `createProperty(VC_REAL, ...)` | done | ja | ja |
| `createBehaviour(VC_BOOLEANSIGNAL, ...)` | done | ja | ja |
| `app.deleteComponent(c)` | done | ja | ja |
| **`createBehaviour(VC_SCRIPT, ...)`** | **inget utfall** | **nej** | **nej** |

Scenbygge i allmänhet är alltså **ofarligt**. Det är att lägga till ett
**skriptbeteende** som stoppar simuleringen — rimligt, eftersom VC måste
kompilera om och starta om skriptmiljön.

Det var värt att mäta: jag antog först att varje scenändring dödade pumpen och
byggde tre olika omstartsmekanismer mot fel problem.

## Varför en omstart inte räcker

Pumpen är ett `VC_SCRIPT`:s `OnRun` (M-08). När simuleringen stoppar dödas dess
tasklet omedelbart — allt efter `exec`-raden körs aldrig, inte ens svaret
skickas. Tre vägar prövade, alla mätta:

| Väg | Utfall |
|---|---|
| `startSimulation()` i `OnStop` | simuleringen går igen, men `OnRun` återinträder **inte** — start utan reset återupptar bara |
| `reset()` + `startSimulation()` i `OnStop` | mekaniken fungerar (`IsRunning` False → True) men `OnRun` återinträder ändå inte; utan spärr blir det en omstartsstorm, mätt till tusentals varv i sekunden |
| `vcSimulation.OnStartStop`-handlare i kommandots scope | fyrar **inte** på det stopp en scenändring orsakar; den fyrade bara som svar på ett eget `startSimulation()`, och inte heller det gick att upprepa |

Slutsatsen är att skriptmiljöns nedmontering inte går att rida ut inifrån.

## Vad bryggan gör i stället

Den **vägrar** koden och säger varför, i stället för att dö tyst mitt i sitt
eget svar. Ett uttryckligt `tillat_skriptbeteende` finns för den som ändå vill,
och då är tystnaden ett medvetet val.

Följden för fas 2: cellens rörelse drivs av **pumpen själv**, inte av ett eget
drivskript. Det behövs inget nytt skriptbeteende alls.

## Sidofynd, båda värda att komma ihåg

* Att döda `VisualComponents.Engine.exe` räcker inte mellan körningar:
  **wineserver lever kvar och håller port 8901**, och nästa start misslyckas
  med en upptagen port. `~/bin/vc-stoppa.sh` gör `wineserver -k` och
  kontrollerar att porten är fri.
* `Brygga.starta()` loggade tidigare **efter** bindningen. En upptagen port gav
  då ett undantag i `OnRun` som VC svalde, och bryggan såg ut att aldrig ha
  startat — noll rader någonstans. Loggen skrivs nu först.
