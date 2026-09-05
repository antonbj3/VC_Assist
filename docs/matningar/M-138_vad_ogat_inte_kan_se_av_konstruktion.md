# M-138 — vad ögat inte kan se, av konstruktion: produktens ärliga gräns över felklasserna F1–F15

**Datum:** 2026-09-05 · Linux 6.8
**Mätt av:** `tests/enhet/test_vad_ogat_inte_kan_se_d9.py` och granskning mot `docs/spec/82_felklasser.md`.
**Fas:** 15 / Kö D punkt D9 (`docs/uppdrag/KO_D_ogat_och_scenen.md`).
**Bygger på:** `M-115` (flanken syns i källan, inte i spåret: STL och NuSMV mot ögat), `M-89` (28/28 provspår vs 3/28 produktionsspår) och `M-132` (transportörrigg och gränsen för tysta säkerhetskretsar).

---

## Frågeställningen

I uppdrag D9 ställs kravet:
> *"Vad ögat inte kan se, av konstruktion. M-115 visade att F15 är strukturellt osynlig för spårbaserad verifiering. Gör listan färdig: vilka av felklasserna i docs/spec/82_felklasser.md går principiellt inte att se i ett spår, hur mycket man än förbättrar domarna? Den listan är produktens ärliga gräns och hör hemma i README."*

Ögat (den spårbaserade analysen i `oga_analys.py` och dess fem domare) är bänkens starkaste dynamiska instrument. Men ett spår är en projektion: det visar vad som faktiskt hände i simuleringen under ett givet tidsfönster med givna stimuli. Det visar inte källkodens statiska struktur, dess latenta tillstånd eller vad som *skulle ha hänt* om ett outlöst fel inträffat.

Här kartläggs samtliga femton felklasser (F1–F15) från `82_felklasser.md` mot deras principiella observerbarhet i ett tidsseriespår.

---

## Klassificering av F1–F15 mot spårobserverbarhet

| Kod | Klassnamn | Synlig i spår? | Principiellt hinder (varför ögat förblir blint) | Fångas av i stället |
|---|---|---|---|---|
| **F1** | Syntax | **NEJ (strukturellt)** | Koden kompilerar inte. Ingen exekvering kan starta och inget spår kan skapas. | Grind 1 (`STruC++`) |
| **F2** | Okänt namn | **NEJ (strukturellt)** | Okänt funktionsblock eller variabelnamn. Fäller vid länkning/parsning innan spår genereras. | Grind 2 och 4 (AST- och symbolindex) |
| **F3** | Fel tagg | **NEJ (strukturellt)** | Namnet saknas i signalkartan. Signalen kopplas aldrig till bussen och lämnar antingen noll avläsningar eller tystnad. | Grind 3 (signalkartan) |
| **F4** | Deklaration | **NEJ (strukturellt)** | Typ- eller riktningsfel (t.ex. skriva till en `VAR_INPUT`). Spåret ser bara datavärdet, inte dess typdefinition eller minneskontrakt. | Grind 1 och 3 |
| **F5** | Sekvens | **JA** | Tidsordningen mellan logiska händelser och signalflanker registreras direkt på tidsaxeln. | Ögat (`sekvensdomaren`) |
| **F6** | Timing | **JA** | Fördröjningar, uppehåll (`dwell`) och stegtider mäts direkt mot klockan. | Ögat (`timingdomaren`) |
| **F7** | Kapplöpning | **JA** | Två utgångar som aktiveras inom samma scanfönster syns i spårets I/O-vektorer. | Ögat (`timingdomaren`, RACE) |
| **F8** | Förregling | **BETINGAT** | **Syns vid provspår**, men är **osynlig i normaldrift** om villkoret aldrig bryts (t.ex. nödstopp/skyddsgrind, M-89/M-132). | Ögat vid felprovokation; Källkodsgranskning |
| **F9** | Geometri | **JA** | 3D-positioner och avstånd mellan kroppar mäts kontinuerligt via `measureDistance`. | Ögat (`kollisionsdomaren`) |
| **F10** | Grepp | **JA** | Detaljens bana i förhållande till verktyget, glidning och avläggningsavvikelse mäts i scengrafen. | Ögat (`greppdomaren`) |
| **F11** | Genomflöde | **JA** | Stationernas tillstånd (`BUSY`/`IDLE`/`BLOCKED`), cykeltider och ackumulerad volym mäts i serien. | Ögat (`genomflödesdomaren`) |
| **F12** | Ohederlig | **JA** | Fysiska anomalier (teleportation, explosion, rörelse under golvet) fälls mot fysikaliska invarianter. | Ögat (`hederlighetsgrindar`) |
| **F13** | Verktygsfel | **NEJ (metanivå)** | Felet ligger i LLM-agentens verktygsanrop och prompt-interaktion, inte i den simulerade anläggningen. | Tjänstelagrets samtalslogg |
| **F14** | Annat | **OBESTÄMT** | Oklassificerade restfel. | Manuell granskning |
| **F15** | Flank/latch | **NEJ (strukturellt, M-115)** | Koden reagerar felaktigt på nivå i stället för flank (t.ex. saknar `R_TRIG`), eller tappar ett internt minnestillstånd. Under normala detaljavstånd ger felaktig och korrekt kod **byte-för-byte identiska I/O-spår**. Felet bor i källans interna tillståndsmaskin, som ett yttre spår saknar insyn i. | Källkodsanalys, formell modellkontroll (NuSMV) eller property-based stimuli |

---

## De fyra fundamentala gränserna för spårbaserad verifiering

Analysen visar att begränsningarna inte beror på algoritmiska tillkortakommanden i ögat, utan på **fyra fundamentala barriärer**:

1. **Den statiska barriären (F1, F2, F3, F4):**
   Ett spår förutsätter att ett program exekverar. Syntaxfel och typfel tillhör källkodens grammatik. De kan per definition aldrig upptäckas dynamiskt utan kräver kompilator och AST-analysator.
2. **Den interna tillståndsbarriären (F15):**
   M-115 bevisade mekaniskt att ett externt spår inte kan skilja nivåavkänning från flankavkänning så länge stimuli anländer med normala mellanrum. Interna tillstånd (funktionsblockens instansdata, timers, interna variabler) exponeras inte på bussen.
3. **Stimulibarriären och tysta kretsar (F8 i normaldrift):**
   M-89 och M-132 bevisade att ett produktionsspår ger 0 till 3 av 28 förreglingar. Säkerhetskretsar (nödstopp, ljusbommar, skyddsdörrar) är tysta under normal drift. Ett spår kan aldrig bevisa förekomsten av en förregling som aldrig utlösts i spåret.
4. **Metabarriären (F13):**
   Agentens interaktion med simuleringsverktygen (felaktiga API-parametrar, JSON-formateringsfel, avbrutna turer) sker i styrgränssnittet utanför simuleringen.

---

## Slutsats för produkten och README

Ögat är nödvändigt men inte tillräckligt. Ett godkännande (`PASS`) från ögats fem domare garanterar att **det observerade förloppet var felfritt under det provade scenariot**. Det är inte — och kan aldrig bli — ett formellt bevis för att programmet är fritt från latenta tillståndsfel (F15), saknade säkerhetsförreglingar (F8) eller statiska brister (F1–F4).

Denna distinktion införs i `README.md` under avsnittet *"Räckvidd, i sak"*.

---

## LIMITS

* **Klassificeringen:** Utgår strikt från de 15 felklasserna definierade i `docs/spec/82_felklasser.md`.
* **Modellkontroll:** Även om formell modellkontroll (t.ex. NuSMV/PLCverif) teoretiskt kan se F15 och latenta förreglingar i källkoden, begränsas den i praktiken av timersemantikens komplexitet (~25–40 % täckning av ST, se M-115 och R-01).
