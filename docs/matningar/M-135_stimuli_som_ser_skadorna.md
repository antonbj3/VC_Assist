# M-135 — stimuli som ser skadorna: C2-punktkrav, sekvenser och grind

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, `nice 19`, headless. Ingen VC, ingen OpenPLC, ingen modell.
Domaren är `bank/domare.dom` via ST-tolken.
**Prövar:** Kö C punkt C2: konstruera stimuli som gör de i M-134 klassade skadorna
synliga för domaren, verifierade genom en grind som avvisar stimuli som fäller
referensen eller förtunnar befintliga prov.
**Körs av:** `tests/protocol/kor_C2_stimuli.py` (32 stimuli verifierade),
`tests/protocol/kor_m122_mutationsskikt.py` (svepet omkört).
Rådata: `docs/matningar/radata/m135_svep.json`, `docs/matningar/radata/m135_ut.txt`.

## Resultat

### Grinden och de trasiga fallen (disciplin: fixtur före mekanism)

En stimulus får aldrig vara ett facit i förklädnad:
1. Referensen måste förbli 100 % grön under stimulansen.
2. Stimulansen måste fälla varje mutant den är byggd för.
3. En ersatt sekvens får aldrig ta bort ett gammalt steg eller krav (grinden får inte bli billig).

`tests/enhet/test_mutation_c2.py` skrevs före grinden i `kor_C2_stimuli.py` och
prövade de tre trasiga fallen:
* `DARLIG`: en stimulus som kräver felaktigt värde mot referensen avvisades mekaniskt.
* `BLIND`: en stimulus som inte fäller mutanten avvisades mekaniskt.
* `FORTUNNAD`: en sekvensersättning som tar bort tidigare kontrollerade steg avvisades mekaniskt.
* `M33`: M33-regeln i `bank/schema.py` (minst 2 scan, 40 ms marginal mellan insignaländring och punktkrav) fällde två tidiga utkast (t.ex. vid t=2200 i S-01 och t=1040 i P-05) tills mätpunkterna flyttades till giltiga scannät.

### Konstruerade stimuli per klass ur M-134

Totalt 32 stimuli i `kor_C2_stimuli.py` över 14 uppgifter:

1. **Klass 1 & 2 (Punktkrav i befintliga sekvenser):**
   8 punktkrav tillagda i befintliga sekvenser (`A-03` ×2, `S-01`, `S-07`, `T-05`, `H-01`, `P-07`, `P-05` ×6).
   Fångar 12 `SKILLNAD_PA_FACITSTIMULUS`-mutanter som tidigare passerade i glest provade tidsfönster.
2. **Klass 3 (Två-cykel-replay):**
   5 nya sekvenser (`tva_enheter_tatt_i_rad` i `A-03`, `tva_overlamningar_i_rad` i `H-04` och `H-05`, `tva_varv_i_rad` i `L-07`, `underkanda_i_tva_omgangar` i `S-07`).
   Fångar 6 överlevare som krävde att tillstånd och räknare bar över cykelgränsen.
3. **Klass 4 (Vakten får löpa ut):**
   Sekvensen `roboten_fastnar_i_verktyget` i `P-03`. Fångar 6 av P-03:s 7 tidigare överlevare genom att hålla `ST120_RB_BUSY` över 6,0 s.
4. **Klass 5 (Hållen signal):**
   `fotocellen_hallen_hog` i `S-05` och `chucken_slapper_medan_spindeln_gar` i `P-06`. Fångar 2 överlevare.
5. **Klass 6 (Flank mot nivå på SYS_RESET och DONE):**
   * V1-mönstret (7 uppgifter: `A-07`, `A-08`, `C-06`, `P-06`, `S-06`, `T-07`, `T-08`): `kvittensen_hallen_medan_felet_kommer`.
   * V4-mönstret (7 uppgifter: `H-04`, `H-05`, `L-05`, `L-06`, `L-07`, `S-07`, `T-09`): `nystart_utan_kvittens_star_still`.
   * DONE-mönstret (2 uppgifter: `H-05`, `S-07`): `done_hallen_hog`.
   Fångar 20 av 21 `FLANK_TILL_NIVA`-överlevare!

### Det nya totalutfallet

Under arbetets gång växte banken från 28 till 33 dömbara uppgifter (kö B lade till `A-01`, `A-02`, `A-04`, `A-05`, `A-06`).
Svepet omfattar nu 33 referenser och 1054 mutanter:

| Mätning | Uppgifter | Mutanter | Fångade | Överlevde | Fångstgrad | F15 (`FLANK_TILL_NIVA`) överlevare |
|---|---:|---:|---:|---:|---:|---:|
| M-122 | 26 | 809 | 718 | 91 | 89 % | 17 av 30 (manuellt) |
| M-131 (C0) | 28 | 899 | 834 | 65 | 93 % | 21 av 35 |
| **M-135 (C2)** | **33** | **1054** | **1010** | **44** | **95,8 %** | **1 av 36** |

De svagaste uppgifterna som åtgärdades:
* `P-03`: överlevare minskade från 7 till 1 (96 % fångst).
* `S-07`: överlevare minskade från 6 till 1 (98 % fångst).
* `A-03`: överlevare minskade från 5 till 2 (95 % fångst).
* `H-04`, `L-07`, `T-07`, `T-08`, `T-09`: **0 överlevare**.

Nivåoperatorn `FLANK_TILL_NIVA`:
Från 21 överlevare i M-131 till **1 enda överlevare** (`S-05:ST200_PML_SC`, som är osynlig under alla testade stimuli).

Alla 33 referenser förblir 100 % godkända av sitt eget facit.

## LIMITS

* **Referenserna och banken rör sig under mätningen.** Fem nya uppgifter (`A-01` t.o.m. `A-06`)
  tillkom från kö B medan mätningen gjordes, vilket lade till 155 mutanter och 23 överlevare
  i de nya uppgifterna som inte omfattades av C2-arbetet.
* **Den sista F15-överlevaren i S-05 är osynlig.** `trigSc.Q` i rad 39 (Clearing) nås inte
  av en hållen nivå eftersom tillståndsmaskinen aldrig går till Clearing utan ett föregående fel.
* **Att referensen är grön bevisar inte att specifikationen är optimal.** Det bevisar bara
  att den nya stimulansen inte motsäger referenslösningen och att mutanten avviker observerbart.
* **Tolkens scansteg är diskreta (20 ms).** Mätpunkter närmare än 40 ms från en insignaländring
  är förbjudna enligt M33, vilket gör att transienta glitchar på 1 scan förblir odetekterbara
  som punktkrav om de inte fångas av invarianter eller flankräkning.
