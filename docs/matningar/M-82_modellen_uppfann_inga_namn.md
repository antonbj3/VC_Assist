# M-82 — noll uppfunna VC-namn över 584 kontrollerade

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_m82_scenkod.py`
**Prövar:** fas 4:s löfte, för första gången mot en modell.

## Frågan

`docs/spec/70_faser.md`, fas 4:

> *"Modellen kan inte anropa ett verktyg eller argument som inte finns. Mätt
> över N försök: **noll uppfunna namn**."*

Den mätningen gjordes mot **våra egna verktygsmallar**. En mall som är skriven av
oss och prövad av oss uppfinner inga namn — det är inte samma sak som att en
modell inte gör det. `M-81` fann att grind 4 aldrig dömt en rad kod som en modell
skrivit.

## Uppställningen

En Claude-agent fick tre scener ur banken — 3, 5 och 9 komponenter, med roller,
katalog-URI:er, verkliga mått och kopplingslistor — och ombads skriva den Python
som bygger dem i VC. Den fick **inte** öppna repot eller API-indexet. Den fick
veta vad VC:s egen dokumentation säger: att `getApplication()`,
`getSimulation()` och `getComponent()` finns i namnrymden.

Sedan dömde `api_index.Validator` varje VC-namn mot indexets 3444 symboler.

## Utfallet

| Scen | rader | kontrollerade namn | **fel** | obestämbara |
|---|---:|---:|---:|---:|
| T-90 | 132 | 108 | **0** | 0 |
| S-03 | 206 | 176 | **0** | 0 |
| L-05 | 353 | 300 | **0** | 0 |
| **summa** | **691** | **584** | **0** | **0** |

**Noll uppfunna namn över 584 kontrollerade.** Fas 4:s löfte håller också mot en
modell.

## Modellen namngav sina egna gissningar, och alla fanns

Den lämnade en osäkerhetslista utan att veta hur den gått. Varje namn den var
osäker på slogs upp:

| Namnet den tvekade om | i indexet |
|---|---|
| `vcApplication.load` | finns |
| `VC_ONETOONEINTERFACE` (gissad stavning) | **finns** |
| `vcNode.findBehavioursByType` | finns |
| `vcMatrix.rotateAbsZ` | finns |
| `connect` | finns på flera typer |

## Vad grinden INTE dömde, och det är hälften av frågan

Grinden svarar på om ett namn **finns**. Den svarar inte på om det används rätt.
Modellens egna osäkerheter är just av den andra sorten:

* *"Jag är säker på att `load` finns på applikationen, men **inte** säker på att
  den returnerar den laddade komponenten."*
* *"`rotateAbsZ` — jag är säker på att metoden finns; **osäker på enheten**. Jag
  har skrivit grader. Är den i radianer blir tre komponenter felvridna."*

Returvärden, argumentantal och enheter ligger utanför grind 4. En scen byggd av
kod med noll uppfunna namn kan alltså ändå bli fel — och den enda som kan se det
är ögat.

## Två saker som gjorde nollan möjlig, och båda är confounders

**1. Jag talade om hur man skriver kod validatorn kan följa.** Instruktionen sa:
*"Skriv kedjan rakt ut. `getApplication().findComponent("X").Name` går att följa;
`_hamta("X").Name` gör det inte."* Modellen följde det, och därför är
obestämbara **noll**. Utan den instruktionen hade en del av de 584 hamnat i
obestämbart i stället för kontrollerat — och obestämbart är **inte** ett
godkännande (I3), men det är heller inget bevis på ett påhitt.

Talet mäter alltså en modell som fått veta hur den ska skriva. Det är den
realistiska uppställningen — i produkten får den systemprompten — men det är
inte en modell utan hjälp.

**2. Modellen vägrade fylla hål med rimliga namn.** Ur dess rapport:

> *"Ingen `vcHelpers.Robot`. … jag var inte säker nog på hjälparens yta för att
> skriva dekorativ kod med den."*
> *"Inga signalkopplingar. … jag var inte säker nog på signal-API:t och kunde
> inte veta signalnamnen."*
> *"Ingen komponentbehållare för `lyftbord -> pall`. Jag misstänker att pallen
> egentligen ska greppas av en container-behaviour, men var inte säker nog på
> konstant- och metodnamn."*

Den lämnade kommentarer om vad som saknades i stället för att gissa. **Nollan
kommer alltså delvis av vad modellen lät bli att skriva**, inte bara av vad den
skrev rätt. Det är rätt beteende — men det betyder att talet mäter både kunnande
och återhållsamhet, och de två går inte att skilja åt här.

## Vad som INTE är mätt

* **Om scenerna blir rätt.** Ingenting kördes i VC. Koden är giltig enligt
  indexet, inte prövad mot en scen.
* **Semantiken.** Se ovan: returvärden, enheter och argumentantal.
* **Tre scener, en modell, en prompt.** Ingen upprepning.
* **Vad som händer utan skrivinstruktionen.** Obestämbara-talet är noll under en
  instruktion som var utformad för att göra det möjligt att kontrollera. Utan
  den är talet okänt.
* **Kopplingarna.** Modellen valde gränssnitt på namnmönster (`out` hos
  avsändaren, `in` hos mottagaren) eftersom den inte kände bankens katalogdelar.
  Om det är rätt väg är inte prövat — `M-67` visade att kopplingen är logisk och
  inte flyttar något, så geometrin ligger ändå på anroparen.
