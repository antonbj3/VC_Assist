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

## Vad som INTE är mätt

* **Ett** fall: en trasig trippelcitering i en fil. Att `loadCommand` ger ett
  objekt och `execute()` inte kastar är mätt för ett syntaxfel i modulkroppen —
  inte för importfel, fel under körning, eller en modul som kastar i sin egen
  toppnivå.
* Grinden `tests/enhet/test_tillagg_syntax.py` parsar med **värdmaskinens
  Python 3**, medan VC kör Stackless Python 2.7. Provsviten kompenserar med
  mönstersökningar efter kända py2-fällor (`exec` med nästlad funktion,
  f-strängar), men den listan är skriven ur de fel vi råkat träffa på. En py2/py3-
  skillnad som ingen ännu gått på passerar grinden tyst.
* Kostnaden *"0,05 s"* är en körning på den här maskinen.
* *"Tre gånger nu har VC svalt ett fel tyst"* är en räkning av tre observerade
  fall. Hur ofta VC sväljer fel, och vilka klasser av fel som **inte** sväljs, är
  inte mätt — mätningen kan inte skilja "plattformen sväljer allt" från "vi råkade
  se tre".
* Slutsatsen att felet *"måste fångas på disk, före start"* är rätt för det här
  felet. Att grinden på disk fångar **alla** fel VC sväljer är inte visat, och
  kan inte visas av en grind som bara läser filerna.
