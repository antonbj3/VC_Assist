# M-176 — Flanken över skanngränsen: samma R_TRIG två gånger i samma scan, på båda motorerna

**Datum:** 2026-09-05
**Status:** KLART (kö A, punkt A10)
**Körs av:** `tests/protocol/kor_A10_flanken.py` (`--n 3`)
**Rigg:** vår ST-tolk (`bank/domare.py`) och OpenPLC Runtime v4.2.1 i
  `vcassist-openplc-v4` (REST 18443, OPC UA 172.17.0.2:4840) genom
  `bank/domare_openplc.py`; STruC++ 0.6.6, node v22.22.0, PLC-uppgift `T#20ms`,
  OPC UA-plugin 10 ms. `vcassist-openplc-m108` rördes inte.
  **Ingen modell körde i den här mätningen.**
**Facit:** två handskrivna uppgifter i bankens form med facit räknat för hand
  **före** körningen (laglig källa 4 i `docs/spec/85_bankkontraktet.md` §2),
  dömda genom OpenPLC Runtime v4 (laglig källa 1). Facit ligger i körningen
  och aldrig i någon av motorerna.
**Prövar:** `svc/vc_assist_svc/st/tolk.py` och `bank/domare.py` mot OpenPLC v4
**Rådata:** `docs/matningar/radata/m176_svep.jsonl` (15 körningar: 5 enheter ×
  3 varv × 2 motorer), `…/m176_sammanstallning.json`, `…/m176_ut.txt`

## Frågan

`R_TRIG` har ett minne som uppdateras **vid anropet**. Anropas samma instans
två gånger i samma scan är `Q` sann efter det första anropet och falsk efter
det andra: den första läsaren konsumerar flanken och den andra får ingenting.
Vem av två konsumenter som får den avgörs alltså av **satsordningen**, inte av
logiken.

Samma sak i sin andra form: `IF fel THEN larm := TRUE; END_IF;` följt av
`IF kvittens THEN larm := FALSE; END_IF;` är reset-dominant. Byter man de två
satserna blir den set-dominant. Båda raderna är riktiga var för sig; det är
ordningen som avgör om ett kvarstående fel går att kvittera bort.

Projektet hade inte prövat något av det en enda gång. Punkt A10 bygger en
uppgift där ordningen spelar roll och kör den på båda motorerna.

## 1. Uppgifterna

Två uppgifter, skrivna i bankens form. De ligger i körningen och **inte** i
`bank/uppgifter/` därför att banken ägs av en annan kö och växer just nu; de
går att lyfta in rakt av.

### A10-FLANK — en instans, två konsumenter

Fyra tryck på `KNAPP` (hög 200 ms, låg 200 ms, fyra gånger). Båda räknarna ska
stå på 2 vid 800 ms och på 4 vid 1800 ms.

| enhet | konstruktion |
|---|---|
| **referens** | `detA` och `detB` — **en detektor per konsument** |
| motbevis `…_a_forst` | **en** instans, anropad två gånger; A läser först |
| motbevis `…_b_forst` | samma fel speglat; B läser först |

De två motbevisen skiljer sig **bara** i ordningen mellan de två `IF`-satserna.

### A10-DOMINANS — kvittens på ett kvarstående fel

`FEL` går hög vid 200 ms och står kvar. `KVITT` går hög vid 600 ms och står
kvar. Ett kvarstående fel får inte gå att kvittera bort: `UT_LARM` ska stå hög
vid 400, 1000 och 1400 ms.

| enhet | konstruktion |
|---|---|
| **referens** | kvittensen först, larmet sist → **SET dominerar** |
| motbevis | samma två satser ombytta → **RESET dominerar** |

Skillnaden är **durabel** — den håller i hundratals scan så länge båda
villkoren står höga — och beror alltså inte på att två stimuli ska landa i
samma scan. Det är avsiktligt: `M-153 §4c` mätte att OpenPLC-domarens
provtagning ger 1,70 prov per 20 ms scan och därför **inte** kan återge ett
enskansfenomen tillförlitligt. En uppgift byggd på en enskans-sammanträffning
hade mätt provtagningen.

## 2. Svaret: motorerna är fullständigt eniga

5 enheter × 3 varv × 2 domare = **30 domar**, alla dömda, inga Domsfel.

| enhet | tolken | OpenPLC v4 |
|---|---|---|
| A10-FLANK / referens | GODKÄND | GODKÄND |
| A10-FLANK / `en_instans_tva_anrop_a_forst` | UNDERKÄND | UNDERKÄND |
| A10-FLANK / `en_instans_tva_anrop_b_forst` | UNDERKÄND | UNDERKÄND |
| A10-DOMINANS / referens | GODKÄND | GODKÄND |
| A10-DOMINANS / `kvittensen_slacker_ett_kvarstaende_fel` | UNDERKÄND | UNDERKÄND |

* **utfallsoenighet: 0 av 5**
* **kodoenighet: 0 av 5**
* **självinstabilitet: 0 av 5 i båda domarna** över tre varv

Det sista är värt en rad för sig. `M-153` mätte OpenPLC-domaren till 7,0 %
självinstabila enheter (13 av 185) över bankens spår, som är sekunder till
minuter långa. De här två uppgifterna har spår på 1,8 respektive 1,4 sekunder
och var stabila i alla tre varv. Det är inte ett motbevis mot M-153 — urvalet
är fem enheter — men det pekar åt samma håll som M-153 §4b: instabiliteten
sitter i sekvensens längd och start, inte i konstruktionen.

## 3. Spegelkontrollen: ordningen bär bristen, i båda motorerna

Det bärande resultatet är inte att motbevisen faller, utan **vad** de faller
på. De två texterna skiljer sig bara i satsordningen, och båda motorerna
placerar bristen på motsatt utgång:

| motbevis | tolkens bristkoder | OpenPLC:s bristkoder |
|---|---|---|
| `…_a_forst` (A läser först) | `…@800ms:UT_B`, `…@1800ms:UT_B` | **samma två** |
| `…_b_forst` (B läser först) | `…@800ms:UT_A`, `…@1800ms:UT_A` | **samma två** |

Och värdena är identiska i båda motorerna:

```
tolken   UT_B skulle vara 4 men var 0.
OpenPLC  UT_B skulle vara 4 men var 0 inom 4 scan efter 1800 ms.
```

**Noll, inte en.** Den andra konsumenten ser aldrig en enda av de fyra
flankerna — inte "ibland", inte "en av fyra". Minnet uppdateras i det andra
anropet innan `Q` hinner läsas, varje gång, i båda motorerna.

För A10-DOMINANS är svaret lika entydigt: `UT_LARM` var **0** vid både
1000 ms och 1400 ms i båda motorerna. En operator som håller kvittensknappen
intryckt släcker larmet trots att felet står kvar — och båda motorerna säger
det med samma ord.

## 4. Vad det betyder

**För tilltron till bänken:** det här är den skarpaste enskilda konstruktionen
i felklass F15 (flank och latch), och de två motorerna är eniga om den, ner på
bristkod och värde. Där tolken dömer F15 dömer den alltså inte en semantik som
bara den har. Det är ett svar på M-110:s *"domen kommer ur vår ST-tolk, inte
ur OpenPLC"* för just den här klassen — och bara för den.

**För banken:** buggen finns redan i bankens egen referens. `M-166 §4a` fann
att A-02:s referenslösning läser `ST240_SCR_DONE` som en **nivå** i stället för
en flank, och att den bara håller vid 20 ms scanperiod därför att maskinen
råkar komma tillbaka till steg 2 exakt ett scan efter att pulsen föll. Vid
10 ms cykel konsumeras samma puls två gånger. A10:s uppgift och M-166:s fynd
är samma klass, hittade på två oberoende sätt: den ena genom att bygga en
uppgift för den, den andra genom att byta cykeltid.

**För förhandsreglerna:** `plc/forhandsregler.py` matar in regler i
systemprompten innan modellen skriver. En regel — *"en `R_TRIG`-instans får
läsas av exakt en konsument; behöver två delar samma flank ska var och en ha
sin egen instans"* — kostar en textrad och tar bort hela klassen innan den
skrivs. Regeln finns inte i dag.

## LIMITS

* **Två uppgifter, fem enheter.** Det är en konstruktionsprövning, inte en
  statistik. Att motorerna är eniga här säger ingenting om hur ofta de är
  eniga i bankens bredd; det talet är M-153:s (107 av 184 enheter helt eniga).
* **Enskansfenomen är inte prövade.** En puls smalare än ett scan, och två
  stimuli som ska landa i **samma** scan, går inte att skriva över OPC UA med
  den här riggen: provtagningen ger 1,70 prov per scan (M-153 §4c) och
  skrivningen har ingen scan-upplösning alls. Uppgifterna är därför byggda så
  att skillnaden är durabel över många scan. Den smala pulsen är en annan
  mätning och den kräver en annan rigg.
* **`R_TRIG` i en egen POU är inte prövad.** Tolken kör inga egna
  funktionsblock (`Tolkfel: tolken kör inte egna funktionsblock`), så formen
  *"flankdetektorn ligger i ett eget FB som anropas två gånger"* går inte att
  jämföra i dag.
* **Ordningen inuti ett scan är prövad; ordningen mellan två TASKS är inte.**
  OpenPLC kör här en enda uppgift (`MAIN`). Två uppgifter med olika intervall
  som delar en flankdetektor är en annan och värre fråga.
* **Uppgifterna ligger inte i banken.** De är skrivna i bankens form men bor i
  körningen; ingen bankgrind räknar dem, och `SPARFACIT_GOLV` är oförändrat.
* **Ingen körning i Visual Components.** Spårfacit ligger bredvid ögondomen,
  aldrig i stället för den (invariant I1).
