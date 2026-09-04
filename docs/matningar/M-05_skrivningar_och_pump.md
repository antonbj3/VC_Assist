# M-05 — varför varje skrivning fallerade, och var pumpen står

**Datum:** 2026-09-04 · `~/.wine-vc-test` · VC Premium 4.10 · headless `:99`

## Huvudfyndet: VC:s Python 2.7-bindning tar bara bytesträngar

**Varje skrivning av en sträng kastade `SystemError: error return without
exception set`.** Läsningar och metodanrop fungerade.

Orsaken är `from __future__ import unicode_literals`, som gör varje
strängliteral till `unicode`. VC:s py2-bindning accepterar bara `str`.

| Anrop | Med unicode | Med bytesträng |
|---|---|---|
| `comp.Name = "x"` | SystemError | **OK** |
| `beh.Script = kod` | SystemError | **OK** |
| `prop.Value = kod` | SystemError | **OK** |
| `createBehaviour(VC_SCRIPT, "n")` | OK ändå | OK |

### Lösningen, dubbelkompatibel

```python
def _s(x):
    try:
        if isinstance(x, unicode):      # finns bara i py2
            return x.encode("utf-8")
    except NameError:
        pass
    return x
```

**All text som skickas in i VC:s API ska gå genom `_s()`.** Det är en
invariant, inte en detalj. På VC 5.0 med Python 3 är `_s()` en no-op, så
samma kod bär båda.

## Andra mätta fakta

| Fynd | Värde |
|---|---|
| `app.createComponent()` | fungerar vid uppstart, inga argument |
| `comp.createBehaviour(VC_SCRIPT, namn)` | returnerar `vcScript` |
| `vcScript` i `dir()` | **endast metoder**, inga egenskaper. `Script` nås som attribut men syns inte i `dir()` |
| `app.CurrentContext.Id` vid uppstart | `Configure` |
| `sim.run(30.0)` | **0,04 s väggklocka för 30 simulerade sekunder.** Kör synkront i maxfart och återvänder |
| `sim.IsRunning` efter `run()` | `False` — anropet är blockerande, inte asynkront |
| `sim.reset()` | fungerar |
| `cmd.execute()` i uppstartskroken | kör **modulnivån**, men `first_state()` anropas aldrig |

## Metodfel jag gjorde, värt att skriva ned

Jag felsökte fel rad i fyra körningar. Tracebacken pekade på rad 76 och jag
antog att det var `createComponent()`. Det var `comp.Name = ...` på nästa rad.
**Läs raden, lita inte på antagandet om vad som står där.**

## Öppet, blockerar fas 1

`OnRun` i skriptet **körs inte**. `OnStop` fyrar, så skriptet är laddat och
dess funktioner är anropbara. Reset före run ändrade inget.

Kandidater att mäta härnäst:
1. Logga vilka hookar som faktiskt fyrar: `OnStart`, `OnReset`, `OnRun`, `OnSimulationUpdate`
2. Om `OnRun` kräver att komponenten deltar i simuleringen på något sätt
3. Om `autoHalt` stoppar simuleringen innan skriptet hinner starta
4. Om skriptfel slukas tyst, och hur man får ut dem (`useTracing`, `output`, `flush` finns på `vcScript`)

Punkt 4 är trolig och billig: `vcScript` har `useTracing` och `output`.
