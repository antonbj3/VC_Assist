# M-151 — hur många stimuli behövs egentligen: sekvensvis ablationsanalys över bankens facit

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell.
Provade uppgifter: `P-03`, `S-07`, `C-04`, `A-03`, `H-04`, `H-05`, `L-07`, `S-01`, `T-05` (67 sekvenser totalt).
**Prövar:** Kö C punkt C11: ta bort sekvenser en i taget och mät om fångstgraden
påverkas. De sekvenser som inte ändrar något har 0 unika fångster mot mutationsmotorn —
och avslöjar antingen att de är dekoration eller att de prövar storheter som
mutationsmotorn inte modellerar.
**Körs av:** `docs/matningar/radata/m151_stimuli_redundans.py`.
Rådata: `docs/matningar/radata/m151_ut.txt`.

## Resultat

### §1 Uppmätt utfall över 67 sekvenser

Var och en av de 67 sekvenserna i de nio uppgifterna togs bort separat.
Antalet mutanter (av motorns 22 skadesorter) som slipper igenom när just den
sekvensen saknas definierar sekvensens unika fångstkraft:

| Uppgift | Sekvenser totalt | Nödvändiga (unika fångster > 0) | Redundanta (0 unika fångster) | Andel redundanta |
|---|---:|---:|---:|---:|
| `P-03` | 6 | 1 (`roboten_fastnar`) | 5 | 83,3 % |
| `S-07` | 11 | 5 | 6 | 54,5 % |
| `C-04` | 6 | 3 | 3 | 50,0 % |
| `A-03` | 7 | 3 | 4 | 57,1 % |
| `H-04` | 8 | 5 | 3 | 37,5 % |
| `H-05` | 10 | 5 | 5 | 50,0 % |
| `L-07` | 8 | 4 | 4 | 50,0 % |
| `S-01` | 6 | 2 | 4 | 66,7 % |
| `T-05` | 5 | 2 | 3 | 60,0 % |
| **Totalt** | **67** | **31 (46,3 %)** | **36 (53,7 %)** | **53,7 %** |

**Huvudfynd:**
1. **Mer än hälften (53,7 %) av sekvenserna har 0 unika fångster:**
   Om dessa 36 sekvenser raderas från banken är fångstgraden mot de 22 skadesorterna
   exakt identisk.
2. **C2-sekvenserna är 100 % nödvändiga:**
   Alla nya sekvenser konstruerade i C2 (`roboten_fastnar_i_verktyget`,
   `nystart_utan_kvittens_star_still`, `tva_enheter_tatt_i_rad`, `done_hallen_hog`)
   visade sig ha unika fångster (1 till 6 per sekvens). Ingen C2-sekvens är redundant.

### §2 Varför 54 % av sekvenserna är redundanta mot mutatorn

Det finns två distinkta orsaker:

1. **Strukturell subsumtion (äkta redundans i facit):**
   Normaldriftssekvenser (`normal`, `en_godkand_kartong`, `kallstart_utan_burk`,
   `takten_12_sekunder`) har nästan genomgående 0 unika fångster.
   Skälet är att varje kodrad som krävs för normaldrift också utövas under
   de mer krävande fel- och stoppsekvenserna. Om ett fel gör att normaldriften
   inte fungerar faller även felscenarierna på samma uteblivna rörelse.
   Normaldriften är diagnostiskt redundant gentemot felscenarierna.

2. **Domänskillnad mellan mutator och testfall (skenbar redundans):**
   Sekvenser som prövar analoga avvikelser i omvärlden (t.ex. `betyget_under_kravet`
   i S-07, `gripkraft_over_gransen` i H-04, `verktyget_ar_for_varmt` i P-03)
   saknar unika fångster mot kodmutatorn.
   Orsaken är inte att sekvenserna är onödiga för anläggningen, utan att
   mutationsmotorns operatorer muterar programkod — de muterar inte omvärldens
   signaler. En sekvens som provar vad som händer när analog insignal överskrids
   fångar bara kodmutationer om styrprogrammet har unik kod reserverad enbart
   för det gränsvärdet (t.ex. `betyget_over_skalans_tak` som fäller 2 unika mutanter).

## LIMITS

* **Analysen mäter unik fångstkraft mot de 22 skadesorterna.** En sekvens med
  0 unika fångster kan fortfarande vara värdefull som regressionsskydd mot andra,
  framtida felklasser eller vid manuell felsökning.
* **Sekvenserna togs bort en och en (first-order ablation).** Grupper av
  sekvenser som tillsammans subsumerar varandra undersöktes inte i kombination.
