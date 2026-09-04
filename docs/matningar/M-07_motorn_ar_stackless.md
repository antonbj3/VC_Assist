# M-07 — motorn är Stackless Python, och trådmodellen är mätt död

**Datum:** 2026-09-04 · `~/.wine-vc-test` · VC Premium 4.10 · headless `:99`

## Motorn

```
sys.version     2.7.1 Stackless 3.1b3 060516 (python-2.71:87602, Nov 12 2025) [MSC v.1942 64 bit]
sys.executable  C:\...\Visual Components Premium 4.10\VisualComponents.Engine.exe
sys.platform    win32
```

**Stackless Python 2.7.1**, inbyggd i motorn. Det förklarar hela `delay()`/
`condition()`/`triggerCondition()`-modellen: den är byggd på Stackless tasklets,
inte på trådar. Ett skript som står i `delay()` är en avschemalagd tasklet som
simuleringsklockan väcker.

`import clr`, `import System` → **ImportError**. Det är alltså *inte* IronPython,
och det finns inga .NET-timers att luta sig mot. `ctypes` finns.

## Trådar: mätt död, nu med mekanism

M-04 sa att bakgrundstrådar aldrig schemaläggs. Det stämde, men mekanismen
saknades. Mätt nu:

En daemon-tråd startades och skrev en rad var 0,25 s. Huvudtråden gick
omedelbart in i `time.sleep(1.0)`.

| Skede | Vad tråden gjorde |
|---|---|
| Medan huvudtråden sov 1,0 s | **fem varv**, exakt 0,25 s isär — tråden levde |
| Efter att kommandot återvänt | **noll varv**, för alltid |

VC-processen levde vidare hela tiden (fyra processer kvar i mätningen).
Tråden dog alltså inte — den **svälter**.

**Slutsats:** en bakgrundstråd får CPU enbart medan huvudtråden står i ett
anrop som släpper GIL. VC:s egen meddelandeloop släpper den inte.

Därmed är trådmodellen i `31_brygga_protokoll.md` slutgiltigt ogiltig, och
allt arbete måste ske på huvudtråden när VC anropar in i Python.

## Sidofynd

`time.sleep(1.0)` från kommandot tog **1,000 s väggklocka**. Huvudtråden kan
alltså blockera i verklig tid — men då står VC still.

Applikationsobjektet har 91 metoder. De som betyder något för bryggan:
`startSimulation`, `stopSimulation`, `resetSimulation`, `render`, `flush`,
`delayRealTime`, `getPythonDllPath`, `rayCast`, `rayIntersect`.
