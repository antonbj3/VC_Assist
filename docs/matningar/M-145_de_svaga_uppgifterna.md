# M-145 — de svaga uppgifterna efter C2: P-03, S-07, C-04 och beviset för ekvivalenta mutanter

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell, ingen OpenPLC.
Data från M-122 (före C2) och M-135 (efter C2).
**Prövar:** Kö C punkt C5: ta de fem (här sex) svagaste uppgifterna från M-122
(`P-03`, `S-07`, `C-04`, `H-04`, `H-05`, `A-03`), rapportera före- och eftertal,
och undersök varför de återstående överlever.

## Resultat

### §1 Före- och eftertal per uppgift

I M-122 bar toppen 37 överlevare över de sex svagaste uppgifterna.
Efter C0 (undantag av VAR-initierare och nivåoperator) och C2 (32 nya stimuli
och checkpoint-skärpningar) ser utfallet ut så här:

| Uppgift | M-122 (före) | M-135 (efter) | Minskning | Kommentar |
|---|---:|---:|---:|---|
| `P-03` | 10 överlevare (7 kod) | **1** överlevare (1 kod) | **-9 (-90 %)** | 6 s-vakten utövas av ny sekvens |
| `S-07` | 7 överlevare (3 kod) | **1** överlevare (1 kod) | **-6 (-86 %)** | 2-cykler, punktkrav och DONE-hållning |
| `H-04` | 5 överlevare (2 kod) | **0** överlevare (0 kod) | **-5 (-100 %)** | Helt ren: 0 överlevare kvar |
| `H-05` | 5 överlevare (1 kod) | **1** överlevare (1 kod) | **-4 (-80 %)** | DONE och 2-cykler lades till |
| `A-03` | 5 överlevare (3 kod) | **2** överlevare (2 kod) | **-3 (-60 %)** | Punktkrav på kvittenspuls + 2-cykler |
| `C-04` | 5 överlevare (3 kod) | **3** överlevare (3 kod) | **-2 (-40 %)** | 2 initierare borta; 3 bevisat ekvivalenta |
| **Summa topp 6** | **37 överlevare** | **8 överlevare** | **-29 (-78 %)** | |

Övriga tidigare svaga uppgifter som också städades i C2:
* `L-07`: från 3 överlevare till **0**.
* `T-07`: från 1 överlevare till **0**.
* `T-08`: från 2 överlevare till **0**.
* `T-09`: från 4 överlevare till **0**.
* `S-01`: från 4 överlevare till **1**.

### §2 P-03: Från 10 till 1

I M-122 stack `P-03` ut: sju skador syntes enbart under perturbation.
Orsaken som M-134 fann var att uppgiftens normaldrift tog 4,2 s och aldrig lät
tidvakten `tmrUttag` på 6,0 s löpa ut.
Sekvensen `roboten_fastnar_i_verktyget` (C2) håller `ST120_RB_BUSY` i 7,0 s.
Denna enda stimulus fällde direkt 6 av de 7 kodraderna:
* `TID_FORDUBBLAD` rad 30 (`T#6s` → `T#12s`)
* `SANT_TILL_FALSKT` rad 32 (`xUttagFel := TRUE`)
* `NOT_STRUKEN` rad 34 (förekomst 1)
* `AND_TILL_OR` rad 34
* `AND_TILL_OR` rad 38 (förekomst 0 och 1)

Den enda kvarvarande överlevaren i P-03 är `NOT_STRUKEN` rad 34 förekomst 0
(`NOT ST120_RB_BUSY` i återställningsvillkoret). Den kräver att återställning
sker med upptagen-signalen hög och verktyget stängt, vilket är förbjudet av
P-03:s egen säkerhetsinvariant `griparen_rustas_bara_mot_ett_oppet_verktyg`.
Överlevaren är alltså oexekverbar under uppgiftens egna säkerhetskrav.

### §3 C-04: Beviset för ekvivalenta mutanter

`C-04` hade 5 överlevare i M-122 ("alla 5 osynliga"). C0 tog bort 2 st
VAR-initierare. De återstående 3 överlevarna är:
1. `rad 47 OR_TILL_AND`: `IF steg < 0 OR steg > 7 THEN`
2. `rad 34 SANT_TILL_FALSKT`: `xStopp := TRUE`
3. `rad 35 SANT_TILL_FALSKT`: `xKravOmstart := TRUE`

Dessa tre är **matematiskt ekvivalenta mutanter** som ingen stimulus kan skilja från referensen:

#### Bevis för skada 1 (rad 47):
`steg` är en `INT` som sätts i initieringen till 0 och enbart tilldelas
konstanterna 0, 1, 2, 3, 4, 5, 6, 7 i ett `CASE`-block.
Villkoret `steg < 0 OR steg > 7` är defensiv programmering för ett tillstånd
som aldrig inträffar i programmet.
Mutanten `steg < 0 AND steg > 7` är logiskt omöjlig för varje heltal.
Både original och mutant utvärderas till `FALSE` i varje scan under alla stimuli.
Deras I/O-spår är identiska för evigt.

#### Bevis för skada 2 och 3 (rad 34 och 35):
I referensen gäller:
```pascal
IF NOT EMG_OK OR NOT ST420_LGT_CLEAR THEN
    xStopp := TRUE;
    xKravOmstart := TRUE;
END_IF;
```
Och i körvillkoret för cellen:
```pascal
xDriftsklar := EMG_OK AND ST420_LGT_CLEAR AND NOT xStopp
        AND NOT xKravOmstart AND NOT xLarm;
```
Både `xStopp` och `xKravOmstart` har exakt samma livscykel:
* Båda sätts till `TRUE` samtidigt när nödstopp bryts eller ljusridån bryts.
* Båda sätts till `FALSE` samtidigt när giltig kvitteringsflank kommer (`trigReset.Q`).
* Varken `xStopp` eller `xKravOmstart` läses NÅGON ANNANSTANS i hela programmet
  än på raderna 54–55, där de binds samman med `AND NOT xStopp AND NOT xKravOmstart`.

Om rad 34 muteras (`xStopp := FALSE`), sätts fortfarande `xKravOmstart := TRUE`.
I villkoret för `xDriftsklar` blir `NOT xKravOmstart` falskt, vilket tvingar
`xDriftsklar` till `FALSE`.
Om rad 35 muteras (`xKravOmstart := FALSE`), tvingar `xStopp` på samma sätt
`xDriftsklar` till `FALSE`.

De två variablerna **skuggar varandra fullständigt**. Att mutera den ena ändrar
ingenting i programmets beteende så länge den andra finns kvar.
För att se felet krävs en dubbel skada (C10: två skador samtidigt). Som enkla
skador är de bevisat ekvivalenta med referensen.

## LIMITS

* **Att en mutant bevisas ekvivalent innebär inte att koden är ren.**
  Att ha två flaggor (`xStopp` och `xKravOmstart`) som gör exakt samma sak är
  en form av defensiv redundans i referensen. Den gör koden tålig, men skapar
  mutanter som bänken omöjligen kan fälla utan att referensen förenklas.
* **Talen gäller enskilda mutationer (first-order).** Som C-04 bevisar kan
  två fel som var för sig är osynliga tillsammans skapa en mätbar avvikelse.
  Det är ämnet för C10 i överflödeskön.
* **P-05 (ny uppgift) har 2 överlevare.** Dessa härrör från transienta
  1-scans-luckor under verktygsbytet som inte kan checkpointas p.g.a. M33:s
  marginalkrav (mätt i M-135).
