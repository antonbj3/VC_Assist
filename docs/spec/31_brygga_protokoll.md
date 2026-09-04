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

## Trådmodellen — det som får bryggan att inte frysa VC

**MÄTT-antagande som fas 1 ska bekräfta:** VC:s Python kör på applikationens tråd.

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

## Säkerhet

- Bindning endast till loopback.
- Delad hemlighet skrivs av bryggan vid start till en fil i VC:s användarmapp
  med restriktiva rättigheter. Tjänsten läser den. Fel token ⇒ `E_AUTH`,
  anslutningen stängs.
- Ingen sandlåda. `exec` kör godtycklig kod med VC:s rättigheter. Det är avsiktligt
  och samma val som källprojektet — därför är loopback-bindningen och kön
  de enda skydden, och de är obligatoriska.

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
