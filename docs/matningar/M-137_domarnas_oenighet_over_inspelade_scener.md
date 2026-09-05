# M-137 — domarnas oenighet över inspelade scener: 74 spår visar att ingen domare är en kopia av en annan

**Datum:** 2026-09-05 · Linux 6.8
**Mätt av:** `tests/protocol/kor_D8_domarna_oense.py` och `tests/enhet/test_domarna_oense_d8.py`.
**Fas:** 15 / Kö D punkt D8 (`docs/uppdrag/KO_D_ogat_och_scenen.md`).
**Bygger på:** `M-65` (ögat på djupet, syntetiska serier), `M-88` (fem domare i VC-byggda celler) och `M-133` (kompositionsdomarna över fyra linjetopologier).

---

## Frågeställningen

I uppdrag D8 formuleras en grundläggande sats för mätbänken:
> *"Projektet har spår från tidigare VC-körningar. Kör alla fem domarna mot varje inspelat spår och räkna hur ofta de är oense. Två domare som alltid säger samma sak är en domare."*

Om två verifieringsinstrument alltid lämnar samma utfall på alla ingångsdata är ett av dem redundant och tillför ingen ny information. För att alla fem domarna i Visual Components Assist (`sekvens`, `timing`, `grepp`, `kollision`, `genomflode`) ska motivera sin existens måste det visas att:
1. Inget par av domare har 0 % oenighet över det samlade scenmaterialet.
2. Varje domare fäller felklasser som de övriga fyra domarna godkänner.

---

## Datamaterial och metod

Samtliga tillgängliga inspelade tidsserier och scener kördes genom `oga_analys.doma()`:
1. **56 bankspår ur `tests/celler.py`:** Standardiserade scenarier som isolerar rörelsefel, tidsavvikelser, sekvensbrist, förreglingsbrott och kollisioner.
2. **12 topologispår ur `tests/protocol/kor_D6_linjetopologier.py`:** Seriell linje, buffert, parallella grenar och återflöde i både hel drift och under kompositionsfel.
3. **6 fullspektrumspår ur `bygg_integrerad_scen()`:** En komplett robotcell med verktyg, gripare, PLC, förregling, tidsfönster, säkerhetsavstånd och stationsstatistik, körd i frisk drift (`HEL`) samt med ett isolerat fel per domän.

Totalt analyserades **74 distinkta spår**.

---

## Mätresultat

### Domarnas totala utfallsfördelning

| Domare | PASS | FAIL | INCONCLUSIVE | INAKTIV (ej frågad) |
|---|---|---|---|---|
| **sekvens** | 14 | 8 | 1 | 51 |
| **timing** | 12 | 5 | 2 | 55 |
| **grepp** | 44 | 8 | 1 | 21 |
| **kollision** | 6 | 4 | 0 | 64 |
| **genomflode** | 13 | 8 | 1 | 52 |

### Parvis oenighetsmatris för alla 10 domarpar

För varje par av domare $(J_1, J_2)$ räknas antalet spår där båda domarna var aktiva, hur många gånger de var eniga (`PASS == PASS`, `FAIL == FAIL`, `INCONCLUSIVE == INCONCLUSIVE`), hur många gånger de var oense, samt separabiliteten (hur många fall som fälls av den ena men inte den andra):

| Domarpar | Aktiva | Eniga | Oense | Oense % | Separabilitet |
|---|---|---|---|---|---|
| **sekvens vs timing** | 14 | 7 | **7** | **50,0 %** | sekvens fäller 4, timing fäller 2 |
| **sekvens vs grepp** | 6 | 4 | **2** | **33,3 %** | sekvens fäller 1, grepp fäller 1 |
| **sekvens vs kollision** | 6 | 4 | **2** | **33,3 %** | sekvens fäller 1, kollision fäller 1 |
| **sekvens vs genomflode** | 15 | 7 | **8** | **53,3 %** | sekvens fäller 4, genomflode fäller 4 |
| **timing vs grepp** | 11 | 5 | **6** | **54,5 %** | timing fäller 3, grepp fäller 1 |
| **timing vs kollision** | 6 | 4 | **2** | **33,3 %** | timing fäller 1, kollision fäller 1 |
| **timing vs genomflode** | 6 | 4 | **2** | **33,3 %** | timing fäller 1, genomflode fäller 1 |
| **grepp vs kollision** | 10 | 5 | **5** | **50,0 %** | grepp fäller 1, kollision fäller 4 |
| **grepp vs genomflode** | 10 | 5 | **5** | **50,0 %** | grepp fäller 1, genomflode fäller 3 |
| **kollision vs genomflode** | 6 | 4 | **2** | **33,3 %** | kollision fäller 1, genomflode fäller 1 |

---

## Slutsatser och teoremets bekräftelse

1. **Noll par med 0 % oenighet:**
   Inget domarpar har 0 % oenighet. Oenighetsgraden i snittet där båda är aktiva ligger mellan **33,3 % och 54,5 %**.
2. **Ömsesidig separabilitet:**
   För varje enskilt par $(J_1, J_2)$ finns det minst ett spår där $J_1$ fäller medan $J_2$ godkänner, och minst ett spår där $J_2$ fäller medan $J_1$ godkänner.
3. **Fullspektrum-isolering:**
   I en anläggning där alla fem kraven övervakas samtidigt:
   - Ett sekvensbrott (bruten förregling) fälls uteslutande av `sekvens` (övriga fyra ger `PASS`).
   - Ett tidsbrott (fördröjd flankankomst) fälls uteslutande av `timing` (övriga fyra ger `PASS`).
   - Ett mekaniskt greppfel (tappad detalj) fälls uteslutande av `grepp` (övriga fyra ger `PASS`).
   - En fysisk kollision (kontakt $d = 0$) fälls uteslutande av `kollision` (övriga fyra ger `PASS`).
   - En processtörning (svält) fälls uteslutande av `genomflode` (övriga fyra ger `PASS`).
   Detta innebär en oenighetsgrad på exakt **80,0 %** (4 mot 1) vid varje isolerat systemfel.

**Slutsats:** De fem domarna utgör fem matematiskt och funktionellt ortogonala inspektionsaxlar. Ingen domare är en kopia av en annan.

---

## LIMITS

* **Diskret samplingsfrekvens:** Spåren är inspelade vid 20 Hz (50 ms tidssteg). Händelser med varaktighet under 50 ms kan inte upplösas.
* **Domändeklaration:** En domare är endast aktiv (`PASS`/`FAIL`/`INCONCLUSIVE`) om dess motsvarande krav har deklarerats i planfilen eller om dess underlagsdata finns i tidsserien; i övriga fall förblir domaren `INAKTIV` för att undvika falskt grönt (I3).

---

## Vad som INTE är mätt

* **Kontinuerlig processreglering:** Analoga reglerkretsar (t.ex. PID-tryckreglering eller analog hastighetsstyrning) där avvikelser inte har diskreta flanker eller tillstånd.
