# M-147 — åtta nya skadesorter: industriella felklasser och hur domaren står mot dem

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell, ingen OpenPLC.
Domaren är `bank/domare.dom` via ST-tolken.
**Prövar:** Kö C punkt C6: bygg åtta nya skadesorter som motsvarar verkliga
driftfel i en PLC, verifiera med trasig fixtur, kör om hela svepet och analysera
de nya hålen i domaren.
**Körs av:** `tests/protocol/kor_m122_mutationsskikt.py` (svepet omkört).
Rådata: `docs/matningar/radata/m147_svep.json`, `docs/matningar/radata/m147_ut.txt`.

## Resultat

### §1 De åtta nya skadesorterna

Varje sort byggdes i `svc/vc_assist_svc/plc/mutation.py`:
1. `FLANK_TAVLAR`: `trig(CLK := ...)` flyttas till slutet av programmet, så att
   kroppen läser `.Q` från föregående scan i stället för att utvärdera först
   (ordningskapplöpning inom samma scan).
2. `TILLSTAND_FASTNAR`: tillståndsövergång (`steg := N;`) stryks, så att
   tillståndsmaskinen fastnar i det aktuella steget utan väg ut.
3. `KVARHALLEN_UTGANG_STOPP`: utgångsnollställning (`OUT := FALSE;`) vid fel
   eller stopp stryks, så att utgången förblir dragen.
4. `LARM_KVITTERAT_UTAN_ORSAK`: säkerhetsvillkor i kvitteringen (`AND EMG_OK`,
   `AND AIR_OK`) stryks, så att larmet kvitteras fast felet består.
5. `TIMER_FORVAL_ANDRAS`: förvalet förkortas till 10 ms under drift, vilket
   simulerar att förvalet ändras/minskas medan timern går.
6. `DIVISION_MED_NOLL`: division `/ expr` i aritmetiska uttryck ersätts med `/ 0.0`.
7. `ARRAY_INDEX_UTANFOR`: arrayindex `arr[i]` ersätts med `arr[i + 100]`.
8. `RETENTIV_FORLORAD`: `VAR RETAIN` ersätts med `VAR`.

### §2 Fixtur före mekanism (disciplin)

`tests/enhet/test_mutation_c6.py` skrevs mot en syntetisk fixtur `KROPP_FIXTUR`
före implementationen. Utskrift före:
```
FAILED test_c6_flank_tavlar
FAILED test_c6_tillstand_fastnar
FAILED test_c6_kvarhallen_utgang_stopp
FAILED test_c6_larm_kvitterat_utan_orsak
FAILED test_c6_timer_forval_andras
FAILED test_c6_division_med_noll
FAILED test_c6_array_index_utanfor
FAILED test_c6_retentiv_forlorad
8 failed in 0.10s
```
Efter implementation i `mutation.py`: `8 passed in 0.08s`.

### §3 Svepet omkört över alla 33 referenser

| Mått | M-135 (14 sorter) | M-147 (22 sorter) | Ändring |
|---|---:|---:|---:|
| Skador totalt | 1054 | **1307** | +253 |
| Fångade totalt | 1010 (95,8 %) | **1174 (89,8 %)** | +164 |
| Överlevde totalt | 44 | **133** | **+89 nya hål** |
| Fångade av beteendelagret | 580 | **744** | +164 |
| Fångade av textlagret | 430 | 430 | ±0 |

Som KO_C förutsade: **fångstgraden föll från 95,8 % till 89,8 %**.
Detta är ett genuint framsteg, inte ett misslyckande: den breddade motorn
avslöjade 89 nya hål i bankens domare som den tidigare tunna motorn inte kunde se.

### §4 Utfallet per ny sort

| Ny sort | Skador | Fångade | Överlevde | Utfall och domarhål |
|---|---:|---:|---:|---|
| `FLANK_TAVLAR` | 32 | 1 (3 %) | **31** | **Massivt hål**: 28 av 31 överlevare skiljer på facitstimulus men domaren saknar mätpunkter under det scan där kapplöpningen sker. |
| `KVARHALLEN_UTGANG_STOPP` | 71 | 45 (63 %) | **26** | Facit kontrollerar att maskinen stoppar, men inte att *varje* enskild utgång är nollställd. 22 är helt osynliga under befintliga stimuli. |
| `LARM_KVITTERAT_UTAN_ORSAK` | 16 | 0 (0 %) | **16** | **100 % hål**: Inget scenario i banken provar att kvittera medan nödstoppet eller luften fortfarande är bruten! |
| `TILLSTAND_FASTNAR` | 84 | 69 (82 %) | 15 | God täckning (82 %), 15 överlever där scenariot avslutas innan stegets verkan förväntas. |
| `TIMER_FORVAL_ANDRAS` | 50 | 49 (98 %) | 1 | Mycket stark täckning (98 %). |
| `DIVISION_MED_NOLL` | 0 | 0 | 0 | 0 mål i bankens 33 referenser (se nedan). |
| `ARRAY_INDEX_UTANFOR` | 0 | 0 | 0 | 0 mål i bankens 33 referenser (se nedan). |
| `RETENTIV_FORLORAD` | 0 | 0 | 0 | 0 mål i bankens 33 referenser (se nedan). |

### §5 Fyndet om bankens Structured Text

Tre av de åtta sorterna gav noll mutanter i banken:
Ingen av de 33 industriella referenslösningarna i banken använder:
* Aritmetisk flyttalsdivision (`/` förekommer bara i kommentarer och signalnamn som A3/C3).
* Fält/vektorer (`ARRAY`).
* Retentiva variabler (`VAR RETAIN`).

Detta är ett fullgott resultat i KO_C:s mening: frågan hur domaren hanterar
array- och divisionsfel på den befintliga banken var fel ställd, eftersom
bankens uppgifter är diskreta sekvens- och förreglingsstyrningar.
Mekanismen för alla tre är implementerad och verifierad i enhetssviten mot
syntetisk kod, redo om banken utökas med beräkningsuppgifter.

### §6 Omkalibrering av C3-golvet

I enlighet med M-123-principen (när nämnaren flyttas omkalibreras golvet till
det faktiskt uppmätta värdet):
* `GOLV_SKADOR = 1307`
* `GOLV_FANGADE = 1174`
* `GOLV_FANGSTGRAD = 1174 / 1307` (0,8982402448355011, d.v.s. 89,824 %)
Både `kor_m122_mutationsskikt.py` och `tests/enhet/test_mutation_golv.py`
är uppdaterade och gröna mot detta nya golv.

## LIMITS

* **De 31 överlevarna i `FLANK_TAVLAR` kräver scannivåanalys.** Att flytta
  anropet sist i skannet ger 1 scans fördröjning i flankens avkänning.
  M33:s marginalkrav (minst 2 scan) gör att punktkrav inte kan fånga dessa
  utan att förlita sig på tillståndsföljder eller invarianter.
* **De 16 överlevarna i `LARM_KVITTERAT_UTAN_ORSAK` kräver nya scenarier.**
  För att avslöja att kvittering godtas utan återställt nödstopp måste en
  stimulus trycka på reset medan `EMG_OK=False` och kräva att `SYS_ALARM`
  förblir sant. Detta är framtida bänkarbete.
* **Banken rör sig.** 33 uppgifter döms här; om fler uppgifter tillkommer
  från kö B kommer nämnaren att förskjutas igen.
