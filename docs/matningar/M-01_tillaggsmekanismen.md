# M-01 — tilläggsmekanismen, mätt

**Datum:** 2026-09-04 · **Prefix:** `~/.wine-vc-test` · **VC:** Premium 4.10 · **Wine:** 11.16

## Frågan
Hur laddas ett tillägg, i vilket scope kör det, och går det att öppna en socket därifrån?

## Utfall

| Fynd | Värde |
|---|---|
| Sökväg som fungerar | `My Commands/Python 2/<paket>/__init__.py` |
| Sökväg som **inte** fungerar | `My Commands/<paket>/__init__.py` — kroken fyrar aldrig |
| Uppstartskrok | `OnAppInitialized()` fyrar |
| `getApplicationPath()` | ger paketets egen mapp som `file:///`-URI |
| `loadCommand(namn, uri)` | fungerar från kroken |
| `cmd.execute()` | fungerar från kroken — kommandot kör vid uppstart |
| `getApplication()` i `__init__.py` | **finns inte** (`vcApplication`-scope) |
| `getApplication()` i kommandot | **finns** (`vcCommand`-scope), returnerar `vcApplication` |
| `socket.bind("127.0.0.1", 8901)` inifrån VC | **OK** |
| `threading` | importerbar |

## Två scope

| Fil | Scope | Kan |
|---|---|---|
| `__init__.py` | `from vcApplication import *` | registrera kommandon, lägga menyval. **Inte** röra appen |
| kommandot | `from vcCommand import *` | `getApplication()` och hela API:t |

Konsekvens: bryggan kan inte bo i `__init__.py`. Den bor i ett kommando som
`__init__.py` laddar och startar.

## Verifierade API-ytor i kommandots scope
`findComponent`, `load`, `render`, `executeFrameGrab`, `beginFrameGrab`,
`findCamera`, `createView`, `getSimulation`, `Components`, `Simulation`

## Rättelser till specen
1. Metoden heter **`getSimulation()`**. `findSimulation` finns inte.
2. Tilläggets sökväg har nivån `Python 2` som jag saknade.

## Rättelse till en tidigare slutsats
Jag påstod att min sond fällde VC och orsakade ett blinkande fönster.
**Falskt.** Sonden låg på en sökväg där kroken aldrig fyrar, och kunde inte
ha kört. Ett avsiktligt syntaxtrasigt tillägg prövades separat: VC startade
normalt och nämnde det inte i loggen. **Trasiga tillägg misslyckas tyst.**

Konsekvens för designen: bryggan måste **själv** logga att den startat,
eftersom VC inte säger något om den inte gör det.

## Vad som INTE är mätt

* Allt är mätt i ett Wine-prefix på Linux mot VC Premium 4.10. Ingen rad är mätt
  på Windows och ingen på någon annan VC-version — M-44 slår fast att ingen
  mätning i hela repot är gjord på Windows.
* Raden *"`threading` — importerbar"* säger att modulen går att importera. Att en
  tråd som startas får CPU är en annan storhet, och den är motsatt: M-04 och M-07
  mätte att bakgrundstrådar svälter så fort kommandot återvänt. Raden ser ut som
  ett grönt svar på den fråga trådmodellen i `31_brygga_protokoll.md` byggdes på,
  och var det inte.
* `socket.bind("127.0.0.1", 8901)` är mätt som en **bindning**. Att någon utifrån
  kan ansluta, skicka och få svar mättes inte här.
* Listan över verifierade API-ytor säger att namnen finns och svarade i
  kommandots scope. Den säger ingenting om vad de returnerar, om svaren är rätta,
  eller om anropen är ofarliga — `app.save` finns på samma objekt och dödar
  pumpen (M-13).
* *"Trasiga tillägg misslyckas tyst"* vilar på **ett** avsiktligt syntaxtrasigt
  tillägg, en gång. Andra sätt att vara trasig — importfel, fel under körning,
  en modul som kastar i sin toppnivå — är inte prövade här.
* Scopeindelningen är prövad genom kroken `OnAppInitialized` och ett kommando.
  Att `getApplication()` saknas i **alla** `vcApplication`-krokar är inte mätt.
* Sökvägsfyndet är mätt som "den ena vägen fyrar, den andra inte" i ett prefix.
  Om `Python 2`-nivån heter något annat i en annan VC-version är oprövat.
