# M-77 — ett löfte utan namn går inte att kontrollera

**Datum:** 2026-09-05
**Ursprung:** ett sidofynd i `M-61`.

## Fyndet

En kommentar i `svc/vc_assist_svc/katalogindex.py` sa:

> *"…de dubbleras här för att katalogindexet inte ska bero på databladslagret,
> och **ett prov binder ihop de två listorna** så att de inte kan glida isär."*

Provet fanns inte. Kommentaren stod i över ett dygn och lovade en grind som
aldrig hade skrivits. Den hittades av en annan agents svep, inte av mig.

Det är en **falsk grön i kommentarsform**. Den som läser koden ser en garanti,
och garantin finns inte.

## Klassen är liten, och det tog två mätningar att se det

Första sökningen efter samma mönster gav **32 påståenden om att något provas, i
22 filer**, varav **27 utan att namnge ett prov**. Det såg ut som ett utbrett
problem.

Det var fel. Nästan alla 27 säger sådant som:

> *"signalytorna provas i stället PER OBJEKT i mallen, med `hasattr`"*

Det handlar om att **runtime prövar en API-yta**, inte om att en testfil finns.
Ordet *provas* bär två betydelser i det här repot, och min sökning mätte dem som
en.

Efter att formen smalnats till påståenden om att ett **prov** finns:
**3 träffar**, varav en är ett genererat felmeddelande (`'raise
ValueError("provet kraver tva olika komponenter")'`) och en pekar på specen.

**Den verkliga klassen är ett fall.**

## Att det hände inuti mätningen av sig självt

Jag höll på att bygga en spärr på talet 27. En spärr på ett tal som blandar två
storheter hade fällt tjugosju riktiga kommentarer och kallat det skuld.

Det är femte gången samma felklass mäts i det här bygget på ett dygn — `M-34`,
`M-57`, `M-69`, `M-76`, och nu detta — och den här gången inträffade den **inuti
mätningen av just den felklassen**.

Formen är alltid densamma: **ett tal som såg rimligt ut, från ett instrument
ingen provat mot ett känt svar.**

## Åtgärd

Ingen spärr. En klass med ett fall förtjänar en lagning, inte en grind — en
grind som aldrig fäller något är dekoration, och den här hade fällt fel saker.

Kommentaren **namnger nu provet**:

```
tests/enhet/test_katalogindex.py::test_familjemarkorerna_ar_identiska_med_databladets
```

och säger varför namnet står där. Regeln som följer är densamma som för
trösklar: *ett påstående om att något är kontrollerat ska peka ut var
kontrollen finns.* En tröskel utan mätreferens och ett löfte utan provnamn är
samma fel.

## Vad som INTE är mätt

* **Bara `.py`-filer** under `svc/`, `ext/`, `bank/` och `install/`. Löften i
  dokumentationen under `docs/` är inte genomsökta.
* **Bara löften om prov.** Kommentarer som påstår att något är *mätt* utan att
  namnge mätningen är en närbesläktad klass och är inte räknad — tröskellintern
  täcker konstanter, men inte prosa.
* **Om de tre träffarna är alla.** Mönstret är smalt nu, och ett smalt mönster
  missar det som är formulerat annorlunda. Det var precis felet i den första
  versionen, åt andra hållet.
