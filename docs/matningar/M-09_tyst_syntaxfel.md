# M-09 — VC sväljer ett syntaxfel i kommandomodulen helt

**Datum:** 2026-09-04 · VC Premium 4.10

## Vad som hände

En trasig trippelcitering i `bridge_cmd.py`: jag lade en `"""`-docstring inuti
skriptmallen, som själv är en `"""`-sträng. Modulen blev syntaktiskt trasig.

VC:s svar på det:

```
16:37:17 OnAppInitialized
16:37:17 loadCommand uri=file:///C:\...\vc_assist\bridge_cmd.py
16:37:17 bridge_cmd executed
```

`loadCommand` returnerade ett **objekt** (inte `None`), `cmd.execute()` kastade
**inget**, och min egen krok loggade `executed`. Modulkroppen kördes aldrig —
noll `[cmd]`-rader. Ingen dialogruta, ingen post i utdatafönstret, ingenting.

Det är en skarpare form av M-01: ett trasigt tillägg misslyckas inte bara tyst,
det misslyckas medan anropen **rapporterar att det gick bra**.

## Vad det betyder för arbetssättet

Ett tyst fel som ser lyckat ut kan inte upptäckas genom att läsa loggen — det
finns ingenting att läsa. Det måste fångas på disk, före start.

Grinden är `tests/enhet/test_tillagg_syntax.py`, och den provar tre saker:

1. varje fil i tillägget parsar
2. skriptmallen parsar **efter formatering** — den är en sträng i en sträng,
   och det var just det ledet som brast
3. mallen börjar med `from vcScript import *` (M-06) och filer som skriver till
   VC har `_s()` (M-05)

Den kostar 0,05 s och kör utan VC.

## Metodlärdomen

Tre gånger nu har VC svalt ett fel tyst: det trasiga tillägget i M-01, `OnRun`
utan `vcScript`-importen i M-06, och det här. Mönstret är inte tre olyckor utan
en egenskap hos plattformen. Allt som laddas in i VC ska därför provas utanför
VC först, och bryggan loggar sin egen start så att tystnad går att skilja från
att ingenting hände.
