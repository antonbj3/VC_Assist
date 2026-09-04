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
