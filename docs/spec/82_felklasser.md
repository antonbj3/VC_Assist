# Felklasser

Bänken rapporterar "fel per klass". Klasserna måste vara så definierade att två
personer sorterar samma fel likadant. Annars är talet meningslöst.

## Klasser

| Kod | Namn | Definition | Fångas av |
|---|---|---|---|
| `F1` | Syntax | koden kompilerar inte | grind 1, `STruC++` |
| `F2` | Okänt namn | funktionsblock, verktyg eller argument som inte finns | grind 2 och 4 |
| `F3` | Fel tagg | taggnamn som inte finns i signalkartan | grind 3 |
| `F4` | Deklaration | typ- eller riktningsfel i variabeldeklaration | grind 1 och 3 |
| `F5` | Sekvens | stegen sker i fel ordning | **ögat**, TIMING |
| `F6` | Timing | rätt ordning men fel tid: för kort uppehåll, för tidig start | **ögat**, DWELL och LATENCY |
| `F7` | Kapplöpning | två utgångar höga i samma scanfönster | **ögat**, RACE |
| `F8` | Förregling | saknad eller felaktig förregling mellan stationer | ögat, komposition |
| `F9` | Geometri | kollision, för kort clearance, otillräcklig räckvidd | ögat, SAFETY |
| `F10` | Grepp | miss, glidning, tappad detalj | ögat, MOTION |
| `F11` | Genomflöde | kör men når inte kapacitetsmålet | ögat, THROUGHPUT |
| `F12` | Ohederlig | passerar bara därför att något omöjligt skedde | ögat, HONESTY |
| `F13` | Verktygsfel | agenten anropade rätt verktyg fel, eller gav upp | loggen |
| `F14` | Annat | passar ingen klass | — |
| `F15` | Flank och latch | villkoret läses på nivå i stället för på flank, eller ett tillstånd hålls inte kvar när villkoret försvinner | **ögat**, TIMING; spårfacit, flankräkning |

## Sorteringsregler

1. **Första grinden som fäller bestämmer klassen.** Ett fel som både har fel
   taggnamn och fel sekvens räknas som `F3`, eftersom grind 3 fäller först.
2. `F12` är **överordnad**. En körning med en hederlighetsöverträdelse räknas
   alltid som `F12`, även om något annat också var fel. Skälet: en ohederlig
   grön är farligare än ett rött.
3. `F14` ska vara nära noll. Växer den är taxonomin fel och ska revideras,
   inte fyllas på.
4. Varje rapporterat fel bär **grind, kod och den rad ur ögat eller loggen**
   som motiverar klassningen. Ingen klassning utan belägg.
5. **`F6` och `F7` får aldrig fällas av en statisk grind.** Formell verifiering
   av ST kan inte avgöra timersemantik: SemaPLC (arXiv 2608.18565) rapporterar
   noll avgörbara utfall för TON-bärande uppgifter, och PLCverif täcker ~25 %
   av ST (arXiv 2203.17253). Se `docs/research/R-01`. En statisk dom över
   timing vore en falsk grön i den ände där felen faktiskt bor.
6. **`F15` är nyare än de andra klasserna och finns av ett skäl.** Ingen
   publicerad LLM-utvärdering mäter flank- eller latchfel (R-01 §1.4).
   `61_st_generering.md` och `tests/protocol/fas7_stationen.md` (trasigt fall
   T3) bygger båda på klassen utan att kunna namnge den. Nio bankuppgifter bar
   redan materialet men var taggade `F5`, `F6`, `F7` eller `F8`, så klassen
   gick inte att rapportera. Omtaggningen är gjord av M-45 och kostade ingen ny
   uppgift.
