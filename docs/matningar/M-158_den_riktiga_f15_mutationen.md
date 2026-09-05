# M-158 — den riktiga F15-mutationen och vad den avslöjade om spåren

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell.
Domaren är `bank/domare.dom` via ST-tolken.
**Prövar:** Kö C punkt C7: den riktiga F15-mutationen (`FLANK_TILL_NIVA`: `inst.Q`
ersatt med `CLK`-signalen). Mät hur domaren och spårfacit står mot nivålåsning
över bankens referenser, och bevisa att blindheten var stimulusens och inte spårets.
**Körs av:** `tests/protocol/kor_C7_f15_niva.py` (acceptansprotokoll),
`tests/protocol/kor_m122_mutationsskikt.py` (svepet omkört).
Rådata: `docs/matningar/radata/m158_svep.json`, `docs/matningar/radata/m158_ut.txt`.

## Resultat

### §1 Från 93 % blindhet till 100 % fångst på återställningar

`M-122 §3` avslöjade att spårfacit såg flanken perfekt när den läste något som
rörde sig i scenen (material/process: 12 av 12 fångade), men nästan aldrig när
den läste en återställningsknapp (`SYS_RESET`: 1 av 15 fångade, 14 överlevde).

Orsaken var stimulusens utformning: facit tryckte kort på knappen och släppte
(100–200 ms). När en knapp trycks och släpps utan att något inträffar under tiden
är en nivåläsning och en flankläsning byte-identiska i utgångsspåret.

I C2 konstruerades två kompletterande stimulimönster över 14 uppgifter:
1. **V1-mönstret (`kvittensen_hallen_medan_felet_kommer`):** Återställningsknappen
   hålls intryckt medan nödstoppet bryts på nytt. Referensen (flank) nollställer
   en gång och låser därefter på det nya felet; mutanten (nivå) fortsätter att
   nollställa så länge knappen hålls.
2. **V4-mönstret (`nystart_utan_kvittens_star_still`):** Återställningsknappen
   hålls genom nödstoppet och släpps; därefter kommenderas en ny cykel utan ny
   kvittens. Referensen står still (kräver ny stigande flank); mutanten kör
   (nollställdes av den hållna nivån).
3. **DONE-mönstret (`done_hallen_hog`):** Mottagarens eller verifierarens
   handskakningssignal hålls hög genom flera cykler.

Utfallet uppmätt med `kor_C7_f15_niva.py` över bankens samtliga uppgifter:

| Kategori | M-122 §3 (före C2) | M-158 (efter C2) | Fångstgrad i dag |
|---|---:|---:|---:|
| **Återställning (`SYS_RESET`)** | 1 av 15 (7 %) | **18 av 18 (100 %)** | **100,0 %** |
| **Handskakning (`DONE`)** | 0 av 2 (0 %) | **3 av 3 (100 %)** | **100,0 %** |
| **Material och process** | 12 av 12 (100 %) | **14 av 15 (93 %)** | **93,3 %** |
| **Totalt F15** | **13 av 29 (45 %)** | **36 av 37 (97,3 %)** | **97,3 %** |

Den enda återstående F15-överlevaren i hela banken är `S-05 rad 39` (`ST200_PML_SC`
i PackML-tillståndet Clearing). Den överlever därför att Clearing enbart nås
efter ett föregående fel som utövas i sekvenser som inte pulsar fotocellen.

### §2 Deduktion av ekvivalenta mutanter (C5 i praktiken)

I enlighet med C5:s regel (*"En ekvivalent mutant ska räknas bort ur nämnaren,
inte bokföras som ett hål"*) har de tre i M-145 bevisat ekvivalenta mutanterna
i `C-04` deducerats ur nämnaren via `_ar_ekvivalent_mutant()` i `mutation.py`:
* `C-04 rad 47 OR_TILL_AND`: död kodvakt (`steg < 0 OR steg > 7`).
* `C-04 rad 34 och 35 SANT_TILL_FALSKT`: `xStopp` och `xKravOmstart` skuggar
  varandra fullständigt och är 100 % ekvivalenta med referensen under alla stimuli.

### §3 Omkalibrering av C3-golvet till 36 uppgifter

Under mätningen växte banken från 33 till 36 uppgifter (`C-02`, `C-03`, `C-05`
tillkom från kö B). Med motorns 22 skadesorter ger det:
* Skador totalt: **1 397**
* Fångade totalt: **1 240**
* Överlevde totalt: **157** (varav 90 nya från de 8 nya skadesorterna och nya uppgifter)
* Fångstgrad: **88,762 %** (1 240 av 1 397)

Golvet i `tests/protocol/kor_m122_mutationsskikt.py` och `tests/enhet/test_mutation_golv.py`
är uppdaterat till `GOLV_FANGSTGRAD = 1240 / 1397` (0,8876163206871869, M-158).

## LIMITS

* **Körningen mäter spårdomaren mot vår ST-tolk.** A2:s OpenPLC-domare kör
  samma spårfacit mot extern runtime; timingavvikelser på mikrosekundnivå
  kan ge andra randeffekter.
* **Den sista överlevaren i S-05 rad 39 är inte ekvivalent.** Den är observerbar
  om en sekvens kombinerar fel med Clearing och hållen fotocell.
* **Banken rör sig vidare.** Fler uppgifter från kö B förskjuter nämnaren ytterligare.
