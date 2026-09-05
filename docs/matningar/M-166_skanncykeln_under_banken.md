# M-166 — Skanncykeln under banken: ändrar cykeltiden domen?

**Datum:** 2026-09-05
**Status:** KLART (kö A, punkt A4)
**Körs av:** `tests/protocol/kor_A4_skanncykeln.py` (rent CPU-arbete: ingen
  rigg, ingen docker, ingen modell). Sammanställningen görs om ur rådatan med
  `--las docs/matningar/radata/m166_svep.jsonl`.
**Rigg:** vår ST-tolk (`svc/vc_assist_svc/st/tolk.py`) körd vid fem
  scanperioder. **Ingen modell körde i den här mätningen** — båda domarna
  dömer texter som redan står i banken; ingen modellkvot användes.
**Bankspegel:** commit `783b8c5`, `sha256(sha256sum bank/uppgifter/*.json)` =
  `5fa8b756…4ed2bed` (`docs/matningar/radata/m166_bankspegel_fore.txt`).
  **49 uppgifter med spårfacit, 217 enheter** (49 referenser + 168 motbevis).
  Banken växte med två uppgifter medan mätningen skrevs — se LIMITS.
**Facit:** IEC 61131-3:s skanncykel (läs in, kör, skriv ut, upprepa) körd vid
  fem perioder, plus ett handskrivet kontrollfall **utanför** banken vars dom
  bevisligen hänger på perioden. Referenspunkten 20 ms är M-20:s uppmätta
  scanperiod för OpenPLC Runtime v4.
**Prövar:** `bank/uppgifter` — är bankens `facit_spar` välställda oberoende av
  cykeltiden?
**Rådata:** `docs/matningar/radata/m166_svep.jsonl` (1085 domar, en rad per
  enhet och period), `…/m166_sammanstallning.json`, `…/m166_ut.txt`.

## Frågan

Kö A:s punkt A4 skrevs som *"vår tolk har ingen cykeltid"*. Det stämmer inte:
`tolk.py:SCAN_MS = 20.0` finns och är mätt i M-20, och `domare.py` skickar in
den i varje `Tolk`. Det som saknades var att **någon någonsin bytte den**.

Frågan är därför den rätta ändå, och den är inte akademisk: bankens spår står
i millisekunder, och ett spår med tider i millisekunder betyder olika saker
vid 5 ms och 100 ms cykel. Om domen ändras när perioden ändras är varje tal
projektet publicerat mätt på en tyst antagelse — 20 ms — som ingen uppgift
skriver ut och ingen användare kan garantera i sin egen anläggning.

## 1. Varför svepet inte fick vara en enkel omkörning

`bank/domare.py` läser punktkravet i **exakt** det scan vars klocka står på
`t_ms`:

```python
if abs(float(s["t_ms"]) - (nu - scan_ms)) > 1e-9: continue
```

Bankens tider är alla multiplar av 20 ms (mätt vid bankspegeln: gcd = 20 över
349 skilda `t_ms`, varav 156 inte är delbara med 40 och 119 inte med 100).
Byter man period till 40 eller 100 ms hamnar tusentals punktkrav **mellan** två
scan, och den raden hoppar då över kravet **utan ett ord**. En
naiv omkörning hade rapporterat "inga ändrade dom" — inte för att banken är
cykeloberoende, utan för att en tredjedel av facit tystnade. Det hade varit en
mätning av sitt eget rutnät.

Körningen använder därför en generaliserad läsregel som är **identisk** vid
20 ms och väldefinierad vid varje annan period:

> punktkravet vid `t_ms` läses efter det **första** scan vars klocka är ≥ `t_ms`.

Vid 20 ms är `ceil(t/20)·20 == t` för varje `t` i banken, alltså samma scan som
`domare.py` läser. Vid 100 ms är det det första scan som över huvud taget har
sett stimulit — vilket är precis vad en PLC med 100 ms cykel kan observera.
Riktningen är dessutom den milda: ett off-grid-krav läses **senare** än det
står skrivet, alltså med mer tid åt logiken, aldrig mindre.

### De två trasiga fallen, båda före mekanismen

1. **Självkontrollen.** Vid 20 ms måste den generaliserade domaren ge
   bit-identiskt utfall **och** identisk bristkodsmängd som `bank/domare.py`
   för varje enhet i banken. **217 enheter, 0 avvikelser.** Faller den, faller
   körningen innan den svepar — då hade svepet mätt harnessen, inte cykeln.
2. **Blindhetskontrollen.** Ett handskrivet fall utanför banken (`CYKELFALLET`
   i körningen: en TON med `PT := T#30ms` och krav vid 0, 20 och 60 ms) vars
   dom bevisligen hänger på perioden måste rapporteras som cykelberoende:

   | period | dom | bristkod |
   |---|---|---|
   | 5 ms | GODKÄND | |
   | 10 ms | GODKÄND | |
   | 20 ms | GODKÄND | |
   | 40 ms | UNDERKÄND | `vakten_loper_ut@20ms:LARM` |
   | 100 ms | UNDERKÄND | `flank:en_enda_larmflank`, `…@20ms:LARM` |

   Ett svep som ska få svara *"inga"* måste först ha visat att det kan svara
   *"några"*. Körningen vägrar (returkod ≠ 0) om kontrollfallet ger samma
   utfall vid varje period — det syns i praktiken: kör man `--scan 20` ensamt
   faller den med just det skälet.

## 2. Svaret: banken är **inte** cykeloberoende, men den är robust nedåt

217 enheter × 5 perioder = **1085 domar**. Alla enheter dömda vid alla fem
perioder; noll odömda.

| period | enheter som byter **utfall** | uppgifter berörda | enheter som byter bara **koder** |
|---|---|---|---|
| 5 ms | **1** | 1 | 7 |
| 10 ms | **1** | 1 | 8 |
| 20 ms | *(baslinje)* | | |
| 40 ms | **4** | 4 | 24 |
| 100 ms | **17** | 17 | 64 |

Per uppgift (bara de som rör sig; alla andra av de 49 står på noll i varje
kolumn):

| uppgift | 5 ms | 10 ms | 40 ms | 100 ms |
|---|---|---|---|---|
| A-01 | 0 | 0 | 0 | **1** |
| A-02 | **1** | **1** | 0 | **1** |
| A-06 | 0 | 0 | 0 | **1** |
| A-07 | 0 | 0 | 0 | **1** |
| A-08 | 0 | 0 | 0 | **1** |
| C-04 | 0 | 0 | **1** | **1** |
| H-01 | 0 | 0 | **1** | **1** |
| H-02 | 0 | 0 | 0 | **1** |
| L-01 | 0 | 0 | **1** | **1** |
| L-02 | 0 | 0 | 0 | **1** |
| L-04 | 0 | 0 | **1** | **1** |
| P-04 | 0 | 0 | 0 | **1** |
| P-07 | 0 | 0 | 0 | **1** |
| S-05 | 0 | 0 | 0 | **1** |
| S-06 | 0 | 0 | 0 | **1** |
| T-01 | 0 | 0 | 0 | **1** |
| T-02 | 0 | 0 | 0 | **1** |

**32 av 49 uppgifter (65 %) står stilla i hela svepet** — samma utfall och
samma bristkoder vid 5, 10, 20, 40 och 100 ms.

## 3. Riktningen är entydig, och det är det viktigaste talet

**Varje enda utfallsändring, i alla fyra perioderna, är en REFERENS som går
från GRÖN till RÖD. Inte ett enda motbevis blir grönt vid någon period.**

| period | referens GRÖN→RÖD | motbevis RÖD→GRÖN |
|---|---|---|
| 5 ms | 1 | **0** |
| 10 ms | 1 | **0** |
| 40 ms | 4 | **0** |
| 100 ms | 17 | **0** |

Det betyder två saker som inte är samma sak:

* **Banken har inget falskt grönt att förlora på cykeltiden.** Alla 168
  motbevis är röda vid alla fem perioderna. Att en användare kör 100 ms cykel
  gör inte att en trasig lösning slinker igenom.
* **Bankens referenser är kalibrerade mot 20 ms.** 17 av 49 referenser slutar
  hålla sitt eget facit vid 100 ms. Ett *"25 av 26"* ur banken är alltså ett
  tal om vad som händer vid 20 ms scanperiod, och det står ingenstans skrivet.

Riktningen är för övrigt densamma som M-153 §3 fann mellan de två domarna:
där var också alla tio utfallsoenigheter referenser som tolkdomaren släppte
och OpenPLC-domaren fällde. Två olika mätningar, samma asymmetri: **facit är
mjukt för motbevisen och hårt för referenserna.**

## 4. Varför: två skilda mekanismer, och bara den ena är rutnätet

De nya bristkoderna delas efter om deras `t_ms` låg **på** scanrutnätet eller
mellan två scan:

| period | nya bristkoder | on-grid | off-grid | flank | invariant |
|---|---|---|---|---|---|
| 5 ms | 67 | 66 | 0 | 1 | 0 |
| 10 ms | 76 | 75 | 0 | 1 | 0 |
| 40 ms | 72 | 39 | 30 | 3 | 0 |
| 100 ms | 465 | 176 | 254 | 31 | 4 |

Vid 5 och 10 ms är rutnätet en **förfining** av bankens 20 ms-rutnät: noll
off-grid-krav, noll kollapsade krav, noll flankfönster utan scanpunkt. Ändå
byter en referens dom. Den ändringen kan alltså inte skyllas på läsningen —
den är logikens.

### 4a. A-02: referensen läser en NIVÅ där den skulle ha läst en FLANK

A-02:s referens är den enda enhet som faller vid en **snabbare** cykel, och
orsaken är spårbar in i scanen. Stimulit och logiken:

* `ST240_SCR_DONE` går hög vid 2820 ms och låg vid **2960 ms** — en puls på
  140 ms.
* Momentgivaren är transient: `ST240_TRQ_VAL` är 17,0 vid 2820 och sätter sig
  på 21,5 först vid 2880. Referensen har därför ett *låsfönster*,
  `tmrLas(IN := xLas, PT := T#100ms)`, uttryckligen för att momentet ska
  hinna sätta sig innan det läses.
* Steg 2 avancerar på `IF ST240_SCR_DONE THEN` — en **nivå**, inte en flank.

Spårat, samma text, två perioder:

```
scan 20 ms:  t=2940 steg 3->1, drag=2      t=2960 steg 1->2, DONE redan LÅG
scan 10 ms:  t=2930 steg 3->1, drag=2      t=2940 steg 1->2
             t=2950 steg 2->3, drag=2  <-- DONE är fortfarande HÖG (faller 2960)
```

Vid 10 ms cykel hinner maskinen tillbaka till steg 2 **tio millisekunder
innan** pulsen faller, och räknar samma `DONE` en andra gång. Vid 20 ms cykel
kommer den dit exakt ett scan efter att pulsen föll. Referensen är alltså inte
riktig — den är **20 millisekunder från att vara fel**, och den marginalen är
hela dess korrekthet.

Det är läroboksexemplet på felklass F15 (flank och latch), det ligger i
bankens egen referenslösning, och det hittades inte av att någon läste koden
utan av att cykeltiden byttes. Det är också exakt den bugg punkt A10 ber om
en uppgift för — och den fanns alltså redan i banken.

### 4b. Vid 40 och 100 ms bär rutnätet mer än hälften

Vid 40 ms ligger 4768 av 13041 punktkrav (37 %) mellan två scan; vid 100 ms
1442 (11 %), och 18 krav kollapsar då i samma scan som ett annat krav. Vid
100 ms är 254 av 465 nya bristkoder off-grid, alltså krav som läses senare än
de står skrivna. Där går det **inte** att skilja "logiken hann inte" från
"punkten går inte att observera vid den här cykeln", och det ska inte tolkas
som att sjutton referenser är trasiga: det ska tolkas som att **sjutton av
bankens facit inte är välställda vid 100 ms cykel**.

Det är samma klass av fel som ett facit får när det skrivs i millisekunder mot
en enda period, och rätt botemedel är inte att flytta referenserna utan att
skriva in perioden i facit och kräva att spårets tider är multiplar av den.

## 5. Vad det betyder för bankens tal

`facit_spar` bär redan fältet `scan_ms`, och alla 49 uppgifter har `20`. Ingen
uppgift säger däremot i klartext att facit **förutsätter** perioden, och
`domare_openplc.py` fäller redan med Domsfel om `scan_ms ≠ 20` (rad 938) — den
har alltså vetat om beroendet hela tiden utan att det var mätt.

Efter den här mätningen står det som ett tal:

* varje bankdom är en dom **vid 20 ms scanperiod**;
* nedåt (10 och 5 ms) håller 48 av 49 uppgifter;
* uppåt håller 45 av 49 vid 40 ms och 32 av 49 vid 100 ms;
* och åt inget håll blir ett enda motbevis grönt.

## LIMITS

* **En motor.** Hela svepet är vår ST-tolk vid fem perioder. Att OpenPLC
  Runtime v4 rör sig likadant när `TASKINTERVALL` ändras är **inte mätt här**.
  Domarens kostnadskvot mellan motorerna är ~1700:1 (M-153 §1), och ett
  fullt svep genom OpenPLC vid tre perioder hade varit ~14 h × 3 seriellt.
  Vad som skulle behövas: `paket.TASKINTERVALL` som parameter genom
  `domare_openplc.program_for_st` (i dag ett defaultargument) och `SCAN_MS`
  som instansfält i stället för modulkonstant.
* **Perioderna är fem, inte ett kontinuum.** 5, 10, 20, 40 och 100 ms är
  valda som "OPC UA-pluginets takt", "M-20:s uppmätta", och två vanliga
  mjuk-PLC-perioder. Perioder som inte delar 20 ms jämnt (t.ex. 30 eller
  50 ms) är inte körda; de skulle ge fler off-grid-krav, inte färre.
* **Rutnätet mot logiken går inte att skilja vid 40 och 100 ms.** De 254
  off-grid-koderna vid 100 ms är inte hänförda var för sig. Vid 5 och 10 ms
  finns inga off-grid-krav alls, och där är slutsatsen ren.
* **Jitter är inte modellerat.** Tolken kör en exakt periodisk cykel. En
  riktig PLC har cykeltidsvariation, och M-153 §4c mätte att OpenPLC-domarens
  provtagning inte ens håller sin egen deklarerade takt (1,70 prov per scan
  där 2 var avsikten). Ett svep över *jitter* är en annan mätning än det här.
* **Banken är ett rörligt mål.** Kö B skrev in T-03 och T-06 medan den här
  mätningen kördes; svepet gjordes om mot spegeln ovan och gav samma tal
  (T-03 och T-06 står på noll i varje kolumn). L-04:s referens ändrades av
  M-167 kl. 20:28 och den här körningen läste den **efter** ändringen.
* **Läsregeln är min, inte `domare.py`:s.** Vid 20 ms är de bevisligen
  identiska (217 enheter, 0 avvikelser). Vid andra perioder är
  ceil-regeln ett val — det mildaste rimliga — och en annan regel (t.ex.
  närmaste scan, eller att helt hoppa över off-grid-krav) hade gett andra tal
  vid 40 och 100 ms. Vid 5 och 10 ms finns inget val att göra.
* **Ingen körning i Visual Components.** Spårfacit ligger bredvid ögondomen,
  aldrig i stället för den (invariant I1).
