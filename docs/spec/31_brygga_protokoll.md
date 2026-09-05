# Bryggans protokoll

Kontrakt mellan tjänsten (Python 3, utanför) och bryggan (Python 2.7, inne i VC).
Båda sidor skrivs mot **detta dokument**, inte mot varandra.

## Transport

| Egenskap | Värde |
|---|---|
| Protokoll | TCP |
| Bindning | `127.0.0.1` **endast**. Aldrig `0.0.0.0` |
| Port | 8901, konfigurerbar |
| Kodning | UTF-8 |
| Livslängd | långlivad anslutning, flera anrop per anslutning |

Motiv för TCP i stället för unix-socket eller namngiven pipe: identiskt beteende
på Windows och Wine. Se `35_plattformar.md`.

## Ramning

Längdprefix, inte radbrytning, eftersom nyttolasten innehåller kod med radbrytningar.

```
<8 hexsiffror, gemener, längd i byte av kroppen><LF><kropp>
```

Exempel: `0000004b\n{"v":1,"id":"a1","op":"ping"}`

Längden avser **kroppen** i byte efter UTF-8-kodning, inte tecken.
Maxlängd kropp: `1048576` byte. Överskridande ⇒ `E_TOO_LARGE` och anslutningen stängs.

## Begäran

```json
{
  "v": 1,
  "id": "<unik sträng, klienten sätter>",
  "token": "<delad hemlighet>",
  "op": "<operation>",
  "args": { }
}
```

`v` är protokollversion. Bryggan avvisar okänd version med `E_VERSION`.

## Svar

```json
{
  "v": 1,
  "id": "<samma som begäran>",
  "ok": true,
  "result": { },
  "stdout": "",
  "stderr": "",
  "elapsed_ms": 0
}
```

Vid fel:

```json
{
  "v": 1,
  "id": "...",
  "ok": false,
  "error": { "code": "E_EXEC", "message": "...", "traceback": "..." },
  "stdout": "",
  "stderr": "",
  "elapsed_ms": 0
}
```

`id` kopplar svar till fråga. Svar får komma i annan ordning än frågorna.

## Operationer

| `op` | Verkan | Läge |
|---|---|---|
| `ping` | livstecken, returnerar VC-version och protokollversion | direkt |
| `exec` | kör kodsträng på VC:s tråd | direkt, **endast läsande** |
| `exec_queue` | lägger kodsträng i godkännandekön | kö |
| `queue_list` | listar väntande poster | direkt |
| `queue_approve` | godkänner post med id | kö |
| `queue_reject` | avvisar post med id | kö |
| `cancel` | avbryter pågående `exec` om möjligt | direkt |
| `eyes_start` | startar provtagning | kö |
| `eyes_stop` | stoppar och returnerar sökväg till rapport | direkt |
| `plc_in` | skjuter in kopplarens PLC-ögonblicksbild i ögats tidsserie | direkt |
| `shutdown` | stänger bryggan | kö |

### `exec` och `exec_queue`

```json
"args": {
  "code": "<python 2.7-källkod>",
  "desc": "<kort beskrivning, visas i kön>",
  "timeout_ms": 5000
}
```

Svaret bär det som koden skrivit på stdout i `stdout`, och **resultatet** tas
ur **sista raden på stdout om den är giltig JSON**. Är den inte det blir
`result` null och `stdout` bär allt. Det är samma svarskanal som källprojektet
använder, och skälet är att koden körs med `exec` utan returvärde.

## Trådmodellen — OGILTIG, se M-04

> **VARNING 2026-09-04.** Avsnittet nedan bygger på ett antagande som är
> **motbevisat** i `docs/matningar/M-04_exekveringsmodellen.md`:
> bakgrundstrådar körs inte i VC:s Python, och inget event fyrar när appen
> står stilla. VC:s Python är kooperativ och simuleringsdriven.
> Ersättningskandidat är `vcScript.OnRun` med `delay()`. Skrivs om när
> den öppna frågan i M-04 är mätt.

**MOTBEVISAT antagande:** VC:s Python kör på applikationens tråd.

Därför:

1. Socketservern kör på en **bakgrundstråd**. Den rör aldrig VC:s API.
2. Inkommande `exec` läggs i en trådsäker kö.
3. En pump som körs på **VC:s egen tråd** plockar en post per varv och kör den.
4. Resultatet läggs i en svarskö som bakgrundstråden skickar tillbaka.

Bryggan får **aldrig** blockera VC:s tråd i väntan på nätverk, och aldrig
röra VC:s API från bakgrundstråden.

`timeout_ms` gäller från det att posten plockas ur kön. Överskridande ger
`E_TIMEOUT`, men koden kan inte avbrytas mitt i — det noteras i svaret och
bryggan markerar sig som `degraded` tills nästa lyckade körning.

## Godkännandekön

Allt som **ändrar** något går genom kön. Kön har en tömmare från dag ett.

Källprojektets kö har noll anropare till `pop_pending_patch` och är i praktiken
död; standardläget där köar poster som aldrig körs. Vi upprepar inte det:
**fas 1 stängs inte förrän en post kan köas, listas, godkännas och köras.**

Post i kön:

```json
{ "qid": "...", "desc": "...", "code": "...", "requested_at": "...", "state": "pending|approved|rejected|done|failed" }
```

## Säkerhet och tokenbeslut (E14)

### Formellt beslut om autentisering och tokenhantering

1. **Sluten loopback-bindning:**
   Bryggan binder **uteslutande** till `127.0.0.1` (`pump.py:203`). Bindning till `0.0.0.0` eller externa nätverksgränssnitt är strikt förbjuden. Ingen extern maskin kan nå porten.

2. **Session-unik slumpmässig token:**
   Konstanten `plats.TOKEN = "vc_assist_token"` är **filnamnet**, inte token-strängen. Vid varje uppstart genererar bryggan en ny, kryptografiskt säker 24-byte (48 hexadecimala tecken) token via `os.urandom(24)` (`pump.py:221-227`). Inga fasta hemligheter eller standardtokens accepteras.

3. **Filplacering och rättigheter:**
   Tokenfilen skrivs i användarens privata profilmapp (`plats.anvandarmapp()`, `%USERPROFILE%` på Windows, `$HOME` på POSIX). Filen skapas med restriktiva rättigheter (`os.chmod(self.tokenfil, 0o600)`), vilket innebär att endast processer som körs under samma användarkonto kan läsa den.

4. **Bindning före token-skrivning (M-44, F3):**
   `Brygga.starta()` binder socketen **före** tokenfilen skrivs. Detta förhindrar att en andra brygginstans i samma process (t.ex. ur en sparad komponent) skriver över en levande bryggas token och gör den onåbar med `E_AUTH`.

5. **Omedelbar avstängning vid fel:**
   En begäran med felaktig eller saknad token avvisas omedelbart med felkod `E_AUTH`, och TCP-anslutningen stängs utan exekvering.

6. **Ingen godtycklig skrivning utan kö (I12):**
   Läsande anrop körs via `exec`, medan alla tillståndsförändrande och skrivande operationer tvingas genom godkännandekön (`exec_queue` och `queue_approve`). Detta ger djupförsvar även om en lokal process på samma användarkonto skulle läsa tokenfilen.

## Felkoder

| Kod | Betyder |
|---|---|
| `E_VERSION` | okänd protokollversion |
| `E_AUTH` | fel eller saknad token |
| `E_PARSE` | trasig ramning eller JSON |
| `E_TOO_LARGE` | kropp över maxlängd |
| `E_UNKNOWN_OP` | okänd operation |
| `E_ARGS` | felaktiga argument |
| `E_EXEC` | undantag i koden; `traceback` bifogas |
| `E_TIMEOUT` | överskriden `timeout_ms` |
| `E_QUEUE_FULL` | kön full |
| `E_NOT_APPROVED` | försök att köra en icke godkänd post |
| `E_BUSY` | bryggan i `degraded` efter timeout |

## Beteende när VC stängs

Bryggan ska överleva att en layout stängs och en ny öppnas. Den ska **inte**
överleva att VC avslutas; tjänsten ska då få `ECONNRESET` och gå till
`disconnected` utan att krascha.

## Fas 1:s grind mot detta dokument

1. `ping` ger svar med VC-version
2. `exec` med läsande kod ger JSON på sista raden och rätt `id`
3. `exec_queue` → `queue_list` → `queue_approve` → körning sker
4. Fel kod ger `E_EXEC` med traceback, och bryggan lever vidare
5. `timeout_ms` överskrids ⇒ `E_TIMEOUT`, och bryggan återhämtar sig
6. **Provtagningstakten mätt i Hz och nedskriven**

## Trådmodellen är ersatt (M-07, M-08)

Avsnittet som märktes OGILTIG efter M-04 har nu både en mätt mekanism och en
giltig modell i sitt ställe.

Motorn är **Stackless Python 2.7.1**. Bakgrundstrådar får CPU enbart medan
huvudtråden står i ett anrop som släpper GIL; VC:s meddelandeloop släpper den
aldrig. Se [M-07](../matningar/M-07_motorn_ar_stackless.md).

Bryggan är i stället ett `VC_SCRIPT`-beteende vars `OnRun` är pumpen, driven av
`app.startSimulation()`. Mätt takt **20,0 Hz mot väggklockan**, kvot
simuleringstid/väggtid **1,000** över 155 sekunder och 3 100 varv. Se
[M-08](../matningar/M-08_vaggklockspumpen.md).

Allt som rör VC sker på huvudtråden inne i `OnRun`. Begäran köas, pumpen betar
av kön. Ingen tråd, ingen timer, ingen .NET.

## Rättelse: var `E_BUSY` ligger (2026-09-04)

Ordagrant följd blev spärren ett låst läge. `degraded` lämnas bara av en
**lyckad körning**, så en spärr på `exec` kan aldrig öppnas igen.

Rättelse: `exec` spärras **inte** av `degraded` — den är vägen ut. Spärren
ligger på `queue_approve`, alltså på det som ändrar något. Betydelsen är
kvar: bryggan gör inget följdriktigt medan dess tillstånd är okänt, men
operatören har alltid en läsande körning som återställer den.

`ping` bär `degraded` i sitt svar så tjänsten kan visa läget.
