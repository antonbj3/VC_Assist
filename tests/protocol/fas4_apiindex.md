# FAS 4 ACCEPTANS — API-index och anropsvalidering

**beskriver:** `svc/vc_assist_svc/api_index.py`
**kontrakt:** `docs/spec/45_verktyg.md` ("Validering före körning"), `docs/spec/46_kunskapsindex.md`
**grind (70_faser.md):** *"Modellen kan inte anropa ett verktyg eller argument som
inte finns. Mätt över N försök: noll uppfunna namn."*

## Status: STÄNGD — 0 av 0 uppfunna namn i eget oberoende prov

## Indexet, mätt

| Storhet | Antal |
|---|---|
| typer | 204 |
| metoder | 966 |
| egenskaper | 1159 |
| händelser | 175 |
| konstanter | 709 |
| hjälpmoduler / medlemmar | 8 / 223 |
| typer med förälder | 92 |
| **symboler totalt** | **3444** |

Antalet typer, metoder, egenskaper och händelser stämmer med `10_matta_fakta.md`.

## Fel i VC:s egen dokumentation, funna under bygget

* **159 namn bär ett efterslapande blanksteg** i `api.xml` (`"vcProduct.getProperty "`).
  Ostrippade hade de gett lika många falsklarm.
* **34 "egenskaper" bär en parameterlista** i sitt `access`-fält — de är metoder
  som källan felklassat. Källans klassning behålls, parameterlistan flyttas till
  signaturen, och antalet rapporteras.
* JSON-filen saknar parametrar, returtyper och arv. Utan `api.xml` finns ingen
  typinferens.

## Mätning 2026-09-04 — oberoende av byggarens egen

Jag körde ett eget prov med kod jag själv skrivit, inklusive stycken som
**faktiskt körts mot VC** i fas 1 och 2.

| | Antal | Utfall |
|---|---|---|
| riktig kod | 7 | **0 falskt positiva** |
| uppfunna namn | 10 | **0 falskt negativa** |

De uppfunna namnen var medvetet rimliga: `setPosition`, `getComponentByName`,
`getWorldPosition`, `moveTo`, `BoundingBox`, `createRobot`, `setTranslation`,
`getJointValues`, `setSpeed`, `attachTo`. Alla fälldes.

Byggarens egen provsamling: 59 försök, 29 uppfunna och 30 riktiga, likaså
**0 och 0**. Avsett namn fanns i förslagslistan i 17 av 23 fall där ett sådant
finns.

## Vad validatorn vägrar gissa om

Tre saker kallas **OBESTÄMBART** i stället för godkänt eller fällt, och de
blockerar godkännandet:

1. dynamiska uppslag (`getattr` med beräknat namn)
2. bara funktionsnamn som ingen mätt källa känner
3. okänd egenskapsläsning på en typ som kan bära användardefinierade egenskaper

## Vad som INTE är prövat

* **En egen funktions parameter döms inte alls.** `def flytta(comp): comp.setPosition(...)`
  godkänns, eftersom parametern saknar deklarerad typ. Uttalat och testat.
* **Grova returtyper** — `findBehaviour` deklareras som `vcBehaviour` fast objektet
  ofta är en undertyp. Namn på undertyper släpps igenom med notering.
* Fasen är **inte** körd mot VC. Den behöver det inte: indexet kommer ur
  dokumentationen och validatorn är ren AST.
