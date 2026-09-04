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
| **`app.save(uri)`** | **inget utfall** | **nej** | **nej** |

`app.save()` upptäcktes senare samma kväll, under fas 5:s verktygsprov: den dödade
bryggan mitt i `save_layout`. Listan över dödande operationer är alltså **inte**
härledd ur någon princip — den växer av mätning, och kan växa igen.

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

## Vad bryggan gör i stället — två olika svar, av mätta skäl

De två operationerna behandlas **olika**, och skillnaden är avsiktlig.

| Operation | Bryggans svar | Varför |
|---|---|---|
| `createBehaviour(VC_SCRIPT)` | **avvisas** | sällsynt, och det finns en uppskjuten väg: koden skrivs till disk och tillämpas vid nästa VC-start, före simuleringen, där den är ofarlig |
| `app.save(uri)` | **tillåts, men varnas om FÖRE körning** | att spara en layout är en helt normal sak att vilja göra. Att förbjuda den vore att ta bort en förmåga som behövs |

Varningen måste komma **före** körningen. Efteråt finns ingen pump som kan svara,
och en anropare som väntar på ett utfall väntar för evigt. Godkännandet svarar
därför direkt med `dodar_pumpen` och en förklaring, och tjänstens utförare slutar
då vänta i stället för att gå i timeout.

Det här är också svaret på frågan om en framtida användare skulle gå på samma
mina: nej — men bara för att den hittades här och blev en grind.

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

## Vad som INTE är mätt

* **Listan över dödande anrop är uttryckligen ofullständig, och den är ofullständig
  än.** Sex operationer prövades, en gång var. `app.save()` upptäcktes samma kväll,
  `comp.save()` kom i M-32 och `sim.reset()` + `startSimulation()` i M-40. M-27 i
  `RESERVERADE.md` är reserverat för det svep som skulle göra listan hel, och det
  svepet är inte gjort.
* Slutsatsen *"scenbygge i allmänhet är ofarligt"* vilar på fem gröna operationer
  körda en gång var. M-15 skapade och rev 244 komponenter och bryggan dog i nästa
  körning med omätt orsak — mängden scenändringar är alltså en möjlig dödsorsak
  som fem enskilda anrop inte kan se.
* Förklaringen till varför `VC_SCRIPT` dödar pumpen (*"VC måste kompilera om och
  starta om skriptmiljön"*) är rimlig och omätt. Ingen mätning tittade på vad VC
  faktiskt gör.
* De tre omstartsvägarna är prövade en gång var i den här uppställningen.
  *"`OnRun` återinträder inte"* är mätt för dem, inte för varje väg som finns.
* Att varningen före körning räcker för anroparen är inte mätt mot en verklig
  anropare. Mekanismen är byggd, inte prövad i bruk.
* Att `wineserver` håller port 8901 kvar är mätt under Wine. Motsvarande fråga på
  Windows, där ingen wineserver finns, är oprövad (M-44).
* Punkt 2 i M-16 — att `skrivgrind.DODANDE_ANROP` behöver en **läsande** gren —
  är inte genomförd. Konstanten är fortfarande `("save",)`, så grinden ser bara
  ett av de mätta dödande anropen.
