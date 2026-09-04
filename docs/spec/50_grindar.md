# Grindkedjan

Doktrin ur källan, **KOD@HEAD**: grinden parsar observatörens egen utdata och
implementerar aldrig om måttet. Motiverad av en mätt incident där en omimplementerad
positionsdom underkände 2 av 4 medan ögat visade 4 av 4.

## Kedjan, i ordning

| # | Grind | Verktyg | Fångar | Fångar INTE |
|---|---|---|---|---|
| 1 | Kompilering | `STruC++` CLI | syntax, typer, okända symboler | allt om beteende |
| 2 | Statisk analys | egna regler | kända dödsfällor, stilbrott | om sekvensen är rätt |
| 3 | **Deklarationsmatchning** | egen | tagg som inte finns i scenens signalkarta | logikfel |
| 4 | Anropsvalidering | AST mot verktygsschemat | fel argument, fel enum, okänt verktyg | körningsfel |
| 5 | **Ögat** | `vc_eyes` | sekvens, timing, grepp, kollision, genomflöde | fältbuss, verklig hårdvara |
| 6 | Komposition | per station, sedan hela linan | fel som bara uppstår tillsammans | |
| 7 | Människa | granskning | allt ovan missar | |

Grind 3 är ny mot källan och är den billigaste vinsten: deklarationerna
**genereras** ur scenens signalkarta, så en tagg kan inte bli fel.

Grind 4 ärvs rakt av. Det är den starkaste anti-hallucination som faktiskt är
byggd i källan: lintern AST-parsar koden och validerar varje argument och
enum-värde mot schemat.

## Fail-closed

Okänd scenarioklass ⇒ **inte guld**. Ärvs från `eyes_gold_gate`.
Tystnad är aldrig ett godkännande.

## Guldstegen

Ärvd från `dataset_manifest.py`, **KOD@HEAD**:

| Nivå | Namn | Krav |
|---|---|---|
| L1 | `gold_verified_core` | en enskild station, ögat säger PASS |
| L2 | `gold_line_verified` | komposition, ögat säger PASS för **varje** station och för linan |
| — | `candidate` | endast resonemang, ingen körning. Aldrig leverans |

**Endast en körning i VC befordrar kandidat till guld.**

## Vad ingen grind fångar

Ärlighet om räckvidden: sensorstuds, ställdonsdynamik, fältbussjitter,
degraderade lägen och verklig hårdvara finns inte i simuleringen.
Ögat är felfinnande, aldrig bevis.

## Säkerhetsgränsen

**Ingen genererad kod rör en säkerhetsfunktion.** Nödstopp, ljusridåer och
allt under IEC 61508 eller ISO 13849 ligger på certifierad säkerhets-PLC,
skrivet i begränsat variabelt språk, av människa. Genererad logik får ligga
bredvid och vara förreglad av den. Detta är inte förhandlingsbart och
implementeras som en grind: taggar märkta säkerhet är skrivskyddade för agenten.
