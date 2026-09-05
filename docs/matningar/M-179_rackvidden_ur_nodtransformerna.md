# M-179 — räckvidden ur den kinematiska kedjans nodtransformer

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen. 3 201 `.vcmx` i testprefixet, 2 202 robotar. Ingen VC
startad; allt är läst ur filerna på disk.
**Prövar:** `M-59` (formeln, facit, täckningen) och `M-177` (kedjan känns igen
på variablerna, inte på blocktypen). Frågan: går räckvidden att härleda ur
kedjans **nodtransformer** i stället för ur namngivna variabler, och hur mycket
stänger det?

---

## 1. Varför transformerna

`_rackvidd` läste **namn**: `L12X`, `L23Z`, `LinkLength2`. Två mätningar i rad
har gått åt till att flytta den gränsen — `M-59` fann 509 robotar utan
räckvidd, `M-177` tog 142 av dem genom att känna igen kedjan på variablerna i
stället för på blockets typnamn. Kvar stod **367**, och 293 av dem har inga
L-namn alls.

Kedjan själv står i filen oberoende av vad någon döpt sina variabler till.
Varje led är en `Node "rSimLink"` med ett `Offset`, och offsetens
translationsdel **är** länklängden:

    Node "rSimLink" { Name "Axis2"
      Dof "Rotational" { Name "Axis2" ... AxisType 1 }
      Offset { Expression "Tz(Kinematics::L01Z).Tx(Kinematics::L12X)..." } }

Hela bibliotekets offsetuttryck ryms i elva operatorer — `Tx/Ty/Tz`,
`Rx/Ry/Rz`, `Sx/Sy/Sz`, `Identity()`, `Set(16 tal)` — med rena tal, symboler
och enkel aritmetik som argument. **2 201 av 2 202 robotar** bär sådana uttryck.

## 2. Storheten är inte summan av alla translationer

Att summera kedjans translationer rakt av ger **median 1,27** mot tillverkarens
egna tal — tjugosju procent för långt, systematiskt. Räckvidden är avståndet
från **led 1:s axel** ut till **handledscentrum**, och två delar av summan hör
inte dit:

* Den del av första länken som ligger **längs led 1:s axel** (pelarens höjd,
  `L01Z` = 830 mm i en IRB 6700) vrider sig inte ut från axeln. Samma sak gäller
  vidare så länge lederna dittills är parallella med led 1 — precis fallet
  SCARA, där både `L01Z` och andra länkens Z-del ska bort.
* **Sista länken** räknas bara till den del som ligger vinkelrätt mot sista
  ledens axel. Handledscentrum är den punkt sista leden inte flyttar; resten är
  flänsförskjutning. Det är samma fynd som `M-59` gjorde med namn (`L56` utanför
  formeln), men uttryckt geometriskt i stället för på ett variabelnamn.

Tre varianter över hela biblioteket, mot de 405 modellnamnen:

| Vad som summeras | median | inom 5 % |
|---|---:|---:|
| alla translationer | 1,269 | 2 av 405 |
| minus delen längs led 1:s axel | 1,084 | 50 av 405 |
| **och sista länken vinkelrätt mot sista ledens axel** | **1,0006** | **399 av 405** |

Att skillnaden mellan raderna är åtta respektive tjugosju procent är hela
skälet till att den här härledningen inte är "summera kedjan".

### Parallellitetsgränsen är mätt, inte vald

Regeln behöver veta om två ledaxlar är parallella. Av bibliotekets **4 254
axelpar** ligger **4 245** antingen över `1-1e-9` eller under `1e-9` i |cos| —
fördelningen är tvåtoppig med ett tomrum emellan, och bara **9** par ligger
däremellan. Varje tröskel mellan `1e-9` och `1e-3` ger alltså samma svar för
4 245 av 4 254 paren. Koden sätter `1e-6`.

## 3. Transformvägen mot den befintliga formeln

**1 783 robotar** får ett tal ur båda vägarna.

| | n | median | p5 | p95 | inom 5 % | inom 10 % |
|---|---:|---:|---:|---:|---:|---:|
| transform / variabel | 1 783 | **1,0000** | 1,000 | 1,157 | 1 634 (92 %) | 1 655 (93 %) |
| — `rKinArticulated2` | 1 217 | 1,0000 | 1,000 | 1,006 | 1 197 (98 %) | 1 207 (99 %) |
| — `rKinScara2` | 404 | 1,0000 | 1,000 | 1,000 | 395 (98 %) | 399 (99 %) |
| — `rKinParallellogram` | 14 | 1,0000 | 1,000 | 1,000 | 14 (100 %) | 14 (100 %) |
| — `rPythonKinematics` | 148 | 1,188 | 1,000 | 1,470 | 28 (19 %) | 35 (24 %) |

Spridningen sitter alltså **helt** i `rPythonKinematics` — de robotar vars
kinematik är ett skript, och där variabelvägen kör den sista, minst prövade
grenen (`JointOffset1` + `LinkLength2..4`).

### Vilken av dem har rätt när de skiljer sig?

`model.xml` deklarerar ett `Reach`-fält i **2 556 av 3 201** komponenter
(`M-76`) — ett facit som varken kommer ur formeln eller ur transformerna.
Av de **149** robotar där vägarna skiljer sig mer än fem procent:

* **variabelvägen närmare i 86**, transformvägen närmare i 47, 16 utan domare.

Så **den befintliga formeln har företräde där båda kan svara**, och det står i
`_rackvidd`:s docstring med talen. Transformvägen fyller bara luckorna. De
grövsta fallen åt båda hållen:

| robot | variabelvägen | transformvägen | `model.xml` Reach |
|---|---:|---:|---:|
| `CP180L` | 3 277 | 1 715 | 3 255 |
| `M-410iC/500` (i luckan) | — | 3 143 | 3 143 |
| `MD400N` | 1 425 | **3 183** | 3 142 |
| `FD50N` | 1 100 | **2 104** | 2 104 |

## 4. Mot tillverkarens eget tal i modellnamnet

`M-59`:s metod, reproducerad: modellnamnet ur `model.xml` (deklarerat i 100 %),
två namnformer — KUKA:s `R<mm>` (275 robotar) och ABB:s
`-<nyttolast>/<räckvidd i meter>` (130). **405 robotar**, mot `M-59`:s 407.

| | n | median | inom 5 % | inom 10 % |
|---|---:|---:|---:|---:|
| variabelvägen | 393 | **1,0008** | 387 (98 %) | 388 (99 %) |
| transformvägen | 405 | **1,0006** | 399 (99 %) | 400 (99 %) |
| — samma delmängd, variabelvägen | 393 | 1,0008 | 387 (98 %) | 388 (99 %) |
| — samma delmängd, transformvägen | 393 | **1,0008** | **387 (98 %)** | 388 (99 %) |
| — bara `rKinArticulated2`, variabelvägen | 372 | 1,0008 | 366 (98 %) | 367 (99 %) |
| — bara `rKinArticulated2`, transformvägen | 372 | 1,0008 | 366 (98 %) | 367 (99 %) |

**På samma robotar ger de två vägarna samma tal mot facit — post för post.**
Transformvägen är alltså inte sämre mot det facit `M-59` valde formeln på, och
den svarar för tolv robotar till.

### Ett tredje facit, oberoende av båda

`model.xml`:s `Reach`, 1 434 robotar med ett värde > 0:

| | n | median | inom 5 % | inom 10 % |
|---|---:|---:|---:|---:|
| variabelvägen | 1 243 | 1,0000 | 1 045 (84 %) | 1 136 (91 %) |
| transformvägen | 1 312 | 1,0002 | 1 091 (83 %) | 1 165 (89 %) |
| — bara transformvägen (nya tal) | 98 | 1,0005 | 59 (60 %) | 65 (66 %) |

De **98 nya talen** har alltså median 1,0005 mot tillverkarens deklarerade
Reach, men bara 60 % inom fem procent — svansen är bredare än för de robotar
formeln redan täckte. Det står i LIMITS.

## 5. Täckningen efteråt

| | `M-59` | `M-177` | **nu** |
|---|---:|---:|---:|
| härledd ur variabler | 1 693 | 1 835 | 1 835 |
| härledd ur nodtransformer | — | — | **158** |
| **härledd totalt** | 1 693 | 1 835 | **1 993** |
| saknas | 509 | 367 | **209** |
| andel av 2 202 robotar | 76,9 % | 83,3 % | **90,5 %** |

**158 av de 367 stängs.** Alla 158 är `rPythonKinematics` (156) eller den äldre
`rKinScara` (2) — alltså precis de som inte lägger sina mått i namngivna
variabler. Hela biblioteket byggs fortfarande på **18,1 s** (`M-59`: 19 s).

### De 209 som står kvar, och varför

| n | skäl | exempel |
|---:|---|---|
| 79 | kedjans **första led är skjutande** — räckvidden är då dess slaglängd, en ledgräns, och ledgränser räknas inte in | `APM4220 XPlanar Mover`, `DELTA RL4-1200-6kg`, `Hornet 565` |
| 64 | kedjan går genom en **följarled** — en parallell mekanism har ingen serie att summera | `YF002N`, `YF003N`, `YS002N`, `iX3-565` |
| 36 | **färre än tre styrda leder** på vägen till flänsen | `Quattro 800H`, `CR_UGD4_R` |
| 17 | en nodtransform går inte att lösa: `JointZeroOffset3` är själv ett **uttryck** (`"ColumnHeight-350"`) | `Gudel CP 3`, `Gudel FP 1` |
| 10 | en nod i kedjan **bär ingen transform** — vägen går genom en inbäddad delkomponent | `IRB 14000`, `IRB 5500-25` |
| 1 | citattecken inuti uttrycket klipper strängläsaren (`Mounting=="Cabinet"`) | `duAro2` |
| 1 | ingen nodväg från rotnoden till flänsnoden | `Quick Changer Tool Side` |
| 1 | translationerna summerar till noll | `RPE` |

### De 99 `Arm1`/`Arm2`/`Arm3`-komponenterna bär talet — men det är inte räckvidden

Uppdraget pekade på dem: `YF002N` har `Node "rSimLink"` med `Name "Arm1"`, och
`130` står i transformen. Det stämmer — men **de är deltarobotar**. Summan längs
en arm från roten till flänsen är

    base 0 + Arm1 130 + leg_right_1_1 256 + platform_1 500 + platform_4 85
    + mountplate 65 = 1036,1 mm

och tillverkarens `Reach` i `model.xml` är **600** (arbetsområdets radie är 300 i
komponentens egna variabler). `130` är axelavståndet ut till en armfästning, inte
en räckvidd. Talet finns i kedjan; det är bara inte den storheten. Därför är de
`SAKNAS` och det är rätt svar — samma disciplin som `M-59` höll för nyttolasten.

## 6. Källsträngen säger vilken väg talet kom ur

Båda vägarna är `HARLEDD` och båda ger millimeter, så `harkomst` skiljer dem
inte. Två markörer står ordagrant i `kalla`:

    VAG_VARIABLER   = "ur namngivna lanklangdsvariabler"
    VAG_TRANSFORMER = "ur den kinematiska kedjans nodtransformer"

`datablad.harledningsvag(varde)` läser ut vilken det var och **faller** på ett
härlett värde vars källa inte säger det, precis som `Varde`-konstruktorn faller
på ett värde utan källa. `datablad.rackviddens_vagar(blad)` räknar biblioteket
per väg och går genom samma grind — så en framtida ändring som skriver en
omärkt källsträng fälls i en läsväg, inte bara i ett prov.

## 7. Vad det kostade i tecken

Källsträngarna blev längre, och `M-59` mätte att de är två tredjedelar av ett
datablads tecken. Mätt om med den levererade koden, hela biblioteket:

| Form | `M-59` median | nu |
|---|---:|---:|
| kort text | 152 | **154** |
| kort JSON | 387 | **390** |
| full text | 914 | **1 046** |
| full JSON | 2 969 | **3 090** |

**Den korta formen är oförändrad i praktiken** — den bär `harkomst` men inte
`kalla`, precis som `M-59` beskrev. Den fulla formen kostar 14 % mer, och det är
priset för att källan säger vilken väg talet kom ur. Hela biblioteket byggs på
18,2 s.

## 8. Trasiga fixturer, skrivna och sedda röda före mekanismen

Alla i `tests/enhet/test_datablad.py`, mot en riktig `.vcmx` byggd av
`robot_rsc(kedja=KEDJA)` — samma IRB 6700-kedja som kinematikblocket, fast som
nästlade `rSimLink`-noder med `Offset`, så att de två vägarna går att ställa mot
varandra på **samma** robot.

| prov | vad det fäller |
|---|---|
| `test_TRASIG_kedja_med_saknad_nodtransform_ger_SAKNAS_inte_delsumma` | Axis4 utan `Offset` → `SAKNAS` med noden namngiven. Delsumman 1 495 mm får inte levereras. |
| `test_TRASIG_variabelharledd_rackvidd_byter_inte_tyst_till_transformvagen` | kedjan säger 3 723,9, kinematikblocket 2 723,9 → svaret ska vara 2 723,9 **och** källan säga `VAG_VARIABLER` |
| `test_TRASIG_transformharledd_rackvidd_utan_vag_i_kallan_falls` | `harledningsvag()` på en omärkt källa → `Databladsfel` |
| `test_kedjan_genom_en_foljarled_ger_SAKNAS_inte_en_armlangdssumma` | följarled i kedjan → `SAKNAS`, inte en armlängdssumma |

Sex prov skrevs, sex var röda före mekanismen, 58 av 58 gröna efter.

---

## LIMITS

* **Talet är fortfarande en övre gräns.** Ledgränserna är inte inräknade —
  en arm vars led 3 inte kan sträckas helt når kortare än summan. Det stod i
  `M-59`, det stod i `M-177`, och det ändras inte här. Det gäller båda vägarna.
* **De 98 nya talen som har en domare träffar sämre än de gamla.** 60 % inom
  fem procent mot `model.xml`:s `Reach`, mot 84 % för de robotar variabelvägen
  redan täckte. Medianen är 1,0005, men svansen är bredare. Ett nytt tal ur
  transformvägen är alltså inte lika säkert som ett gammalt ur formeln, och den
  som väger två robotar mot varandra bör läsa `kalla` för att se vilken väg
  talet kom ur.
* **60 av de 158 nya talen har ingen domare alls.** De har varken räckvidden i
  modellnamnet eller ett `Reach` i `model.xml`. För dem är transformvägen en
  extrapolation från de 98 som gick att pröva — samma slags öppen rad som
  `M-59`:s 846 oprövade ledade armar.
* **`AxisType` läses bara för 0/1/2.** Värdena 5 och 6 förekommer (556 robotar
  har ett av dem på led 1) och vad de betyder är inte mätt. De behandlas som
  **okänd** axel, inte som en gissad. För led 1 tas då VC:s komponentuppaxel Z
  i stället, och det är ett antagande om modelleringen, inte en avläsning.
  `Dof "Custom"` (237 robotar) deklarerar ingen axel alls.
* **`sssad`, `sassd`, `cosd`-i-skala och de andra räknefunktionerna är inte
  implementerade** utom `sind/cosd/tand/atand/atan2d`. De förekommer i ett
  tjugotal offsetuttryck i hela biblioteket och ger `SAKNAS` när de står på
  kedjans väg. Ingen av de 209 kvarvarande faller på just det.
* **De 79 med skjutande första led är inte undersökta var för sig.** Att de är
  deltarobotar och planarmotorer är läst ur namnen och ur att summan blir noll,
  inte ur att någon följt deras kinematik.
* **De 17 Gudel-portalerna skulle kunna lösas** med rekursiv uttrycksutvärdering
  (`JointZeroOffset3 = "ColumnHeight-350"`). Det är medvetet inte gjort: en
  portals räckvidd **är** dess slaglängd, alltså en ledgräns, och att stänga dem
  hade gett ett tal som inte är räckvidden.
* **Ingen komponent är laddad i VC.** Att kedjan går att följa i filen är inte
  samma sak som att VC ger samma tal när komponenten står i en scen. Det är
  `M-57`:s öppna rad och den står kvar.
* **`model.xml`:s `Reach` är använt som facit, inte som källa.** Databladet
  läser fortfarande inte fältet, och räckvidden är därför alltjämt `HARLEDD` i
  1 993 fall och `LAST` i noll — trots att 1 434 robotar bär ett deklarerat tal.
  Att göra det fältet till en `LAST`-källa är en egen ändring med en egen
  mätning; `M-76` har redan visat att fältet finns.
