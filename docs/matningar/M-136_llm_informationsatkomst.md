# M-136 — LLM-informationstäckning i skala över 50 bankuppgifter

**Datum:** 2026-09-05
**Rigg:** Linux x86_64, Python 3.13.11, bankens 63 uppgifter i `bank/uppgifter/*.json`
**Körs av:** `tests/protocol/kor_E4_llm_tackning.py`
**Underlag:** `docs/matningar/m136_llm_tackning.json`
**Prövar:** Om en språkmodell kan hitta och nå den information som krävs för att bygga cellen och skriva PLC-koden över 50+ verkliga uppgifter — mätt i täckning och ordförrådsbredd, inte bara volym.

## Bakgrund och frågeställning

Operatörens uttryckliga krav: *"Informationen måste vara lättillgänglig för LLM"*. Kravet handlar inte bara om att datan existerar på disk, utan att den går att slå upp och använda: litet och precist ordförråd, deklarerade enheter och tydlig härkomst.

`M-84` visade att API-uppslag förändrade modellens ordförråd från 13 till 32 distinkta API-namn och halverade kodvolymen. `M-119` mätte 1 025 frågor och avslöjade att sex frågeslag svarade noll. Efter reparationerna i E3 (nollor som saknas, grindregler ur `docs/spec/`, kompletta fält i `bench_task`, konstanter och delsträngsgränser) prövar denna mätning om informationstäckningen håller i full skala över 63 bankuppgifter.

## Metod: Pseudo-simulering i skala

För var och en av bankens 63 uppgifter kartläggs de informationsbehov som krävs:
1. **Uppgiftens grunddata:** (`bench_task`) — mål, prompt, toleranser, sekvens, styrsignaler och fysikaliska parametrar.
2. **Scenens komponenter:** (`catalog_item` / `search_catalog`) — URI, roll, mått och enheter.
3. **Styrsignalkartan:** (`search_catalog`) — signalnamn, riktning (`in`/`out`), typ (`bool`, `int`, `real`).
4. **Grindregler och rapportmönster:** (`search_api`) — de obligatoriska raderna (`expect.lines`) och sektionerna (`must_pass`), t.ex. `RACE`, `MINDIST`, `DWELL`, `EDGE`.
5. **Standardhänvisningar:** (`search_api`) — normkrav (t.ex. ISO 13850, IEC 60204-1, IEC 61131-3).
6. **Anti-hallucination (SAKNAS-värde):** Test av kända fällor (`VC_BOOLSIGNAL`, `setPosition`, `getComponentByName`, `vcRobot`, `canConect`) för att bekräfta att verktygen ger ärliga nej (`found=False`).

## Resultat

Totalt undersöktes **1 720 informationskrav** över alla **63 bankuppgifter**.

| Kategori | Antal krav | Besvarade (SVAR) | Täckningsgrad |
|---|---|---|---|
| `bench_task` (uppgift, control, fysik) | 63 | 63 | **100,0 %** |
| `komponenter` (scenens komponenter & URI) | 366 | 366 | **100,0 %** |
| `signaler` (OPC UA-styrsignalkartan) | 668 | 668 | **100,0 %** |
| `grindregler` (ögonkontrakt och sektioner) | 592 | 592 | **100,0 %** |
| `standarder` (klausuler och normreferenser) | 31 | 31 | **100,0 %** |
| **Totalt** | **1 720** | **1 720** | **100,0 %** |

### Ordförrådsbredd

Mätningen bekräftar M-84:s tes: mängdmått (antal anrop) är missvisande; det avgörande är **ordförrådets bredd**.
* **555 distinkta symboler och namn** nåddes och användes under körningen (komponent-URI:er, signalnamn, rapportnyckelord, standarder).
* Detta är en mångfaldig ökning jämfört med baslinjen (13 symboler) och fas 4 (32 symboler).

### Värdet av SAKNAS (Anti-hallucination)

5 av 5 kända fällor avvisades med `found=False`:
* `VC_BOOLSIGNAL` -> `found=False` (korrekt förslag: `VC_BOOLEANSIGNAL`)
* `setPosition` -> `found=False` (korrekt förslag: `PositionMatrix`)
* `getComponentByName` -> `found=False` (korrekt förslag: `findComponent`)
* `vcRobot` -> `found=False` (korrekt förslag: `vcRobotController`)
* `canConect` -> `found=False` (korrekt förslag: `canConnect`)

Ingen av fällorna producerade en falsk positiv eller hallucinerad signatur.

## LIMITS

* **Ingen LLM genererade scenkod under körningen.** Mätningen är en mekanisk pseudo-simulering av informationsåtkomst; att informationen finns och är nåbar innebär inte att en given språkmodell väljer att ställa rätt fråga eller tolka svaret utan logiska fel i styrlogiken.
* **Täckningen gäller bankens 63 uppgifter.** Även om uppgifterna spänner över sex tillverkningsgrupper (A, P, L, S, H, C, T) med fordonsmontering, palletering, svetsning och transport, täcker de inte alla tänkbara industriella layouter.
* **Visual Components kördes inte under mätningen.** Uppslagen kördes mot tjänstens datahandlare och indexfiler på disk, inte mot en levande simulering i VC.
* **Standardtäckningen (31 frågor) vilar på bankens referenser.** Bankens uppgifter bär 31 uttryckliga standardklausuler i `facit_spar`; industriella standarder utanför dessa 31 ingick inte i korpusen.
