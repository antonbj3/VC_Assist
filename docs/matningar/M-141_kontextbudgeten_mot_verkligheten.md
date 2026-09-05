# M-141 — Kontextbudgeten mot verkligheten: förhandsreglerna i systemprompten

**Datum:** 2026-09-05
**Rigg:** `svc/vc_assist_svc/plc/forhandsregler.py`, `reparation.py`, `llm/budget.py`, `docs/spec/25_kontextbudget.md`.
**Körs av:** `tests/protocol/kor_E11_kontextbudget.py`
**Underlag:** `docs/matningar/m141_kontextbudget.json`
**Prövar:** Hur stor systemprompten med alla förhandsregler blir i verkligheten, om den ryms inom 5 %-allokeringen i `docs/spec/25_kontextbudget.md`, och vad som trängs ut först i mindre kontextfönster.

## Bakgrund och frågeställning

`docs/spec/25_kontextbudget.md` tilldelar **5 %** av modellens totala kontextfönster till Post 1 (systemprompt) och stipulerar att den **inte får trimmas** (`far_trimmas = False`). Samtidigt genererar `forhandsregler.py` regler från tre källor för att möjliggöra enskottsframgång:
1. Grind 2 (ST-lagrets AST- och syntaxregler)
2. Grind 3 (signalkartans regler)
3. Ögats körningsregler (F1, F5, F8, F12, F15)

Frågan är: **Hur stor blir systemprompten i verkligheten, och vid vilken fönsterstorlek spräcks budgeten så att grindar faller tyst?**

## Resultat

### 1. Storlek och sektionsuppdelning

Systemprompten `reparation.SYSTEMPROMPT` omfattar **6 929 tecken (6 943 bytes)**. Vid en standardomräkning på 4 byte/token motsvarar detta **1 735 tokens** (eller 2 309 tokens vid 3 tecken/token).

| Sektion | Tecken | Bytes | Tokens (@4B/tok) | Andel av prompten |
|---|---|---|---|---|
| `grundprompt` (roll & format) | 200 | 202 | 50 | 2,9 % |
| `grind_2_st` (syntax, typer, balans) | 3 409 | 3 416 | 854 | 49,2 % |
| `grind_3_signalkarta` (OPC UA, riktning) | 1 323 | 1 325 | 330 | 19,1 % |
| `ogat_process_sakerhet` (F1–F15) | 1 865 | 1 868 | 467 | 26,9 % |
| **Totalt** | **6 929** | **6 943** | **1 735** | **100,0 %** |

### 2. Budgetanalys över olika kontextfönster

`25_kontextbudget.md` tilldelar exakt 5 % till systemprompten.

| Kontextfönster | Allokerad budget (5 %) | Faktiskt behov | Belastning | Utfall |
|---|---|---|---|---|
| **8 192 tokens** (8k) | 409 tokens | 1 735 tokens | **424,2 %** | **ÖVERSKRIDEN** (+1 326 tok) |
| **16 384 tokens** (16k) | 819 tokens | 1 735 tokens | **211,8 %** | **ÖVERSKRIDEN** (+916 tok) |
| **32 768 tokens** (32k) | 1 638 tokens | 1 735 tokens | **105,9 %** | **ÖVERSKRIDEN** (+97 tok) |
| **65 536 tokens** (64k) | 3 276 tokens | 1 735 tokens | 53,0 % | Ryms |
| **131 072 tokens** (128k) | 6 553 tokens | 1 735 tokens | 26,5 % | Ryms |
| **200 000 tokens** (200k) | 10 000 tokens | 1 735 tokens | 17,3 % | Ryms |

**Kritisk brytpunkt:** Systemprompten kräver ett fönster på minst **34 700 tokens** för att rymmas inom sin 5 %-budget. I alla mindre fönster kastar `budget.py` antingen `Budgetfel` eller så trängs innehåll ut.

### 3. Vad som ryker först (Utträngningsordningen)

I `forhandsregler.text()` placeras reglerna i ordningen:
1. Grind 2 (ST-syntax och AST-balans)
2. Grind 3 (signalkarta och variabler)
3. **Ögat (process, flöde och maskinsäkerhet)**

Om prompten trunkeras bakifrån eller trängs ut av uppgiftstext och verktygssvar är det **ögats regler som försvinner först**:
* `F12` (hederlighet: sätt aldrig klarsignal utan rörelse)
* `F15` (signalflank vs nivå: återställning på nivå startar om okontrollerat, larm på flank släpper)

Detta innebär att de allvarligaste felen (säkerhetsbrister och falska godkännanden) är de första modellen lämnas ovetande om när fönstret krymper.

### 4. Slutsatser och åtgärder

1. För modeller med ≤ 32k kontextfönster kan inte alla förhandsregler skickas villkorslöst i systemprompten utan att spräcka 5 %-taket.
2. Sektionsordningen bör inverteras eller prioriteras så att säkerhets- och hederlighetsregler (`F12`, `F15`) placeras överst, inte nederst.
3. Dynamiskt regelurval baserat på uppgiftens egenskaper (t.ex. inkludera F15 endast när uppgiften bär återställningsknapp eller flankberoende) är nödvändigt för små modeller.

## LIMITS

* **Tokenberäkningen vilar på standardkvot.** 4 byte per token är specens definition; verkliga tokenizers (t.ex. cl100k_base eller Claude) varierar mellan 3,2 och 4,1 byte/token beroende på språk.
* **Mätningen avser enskotts-systemprompten.** Vid flerskott och reparation tillkommer tidigare felmeddelanden och grindord i historiken (Post 8 och 9).
* **Ingen live LLM anropades i denna mätning.** Mätningen beräknar stränglängder och tokenbudgetar mekaniskt mot budgetmodellen i `svc/vc_assist_svc/llm/budget.py`.
