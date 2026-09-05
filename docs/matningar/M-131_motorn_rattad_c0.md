# M-131 — mutationsmotorns tre rättelser och det nya utgångstalet

**Datum:** 2026-09-05
**Rigg:** värdmaskinen, `nice 19`, fyra processer. Ingen VC, ingen OpenPLC,
ingen modell. Domaren är `bank/domare.dom` genom vår egen ST-tolk — samma
domare som reparationsslingan använder.
**Prövar:** kö C punkt C0: motorns tre rättelser (M-122 §6.2) plus en fjärde
som mätningen själv hittade — och det nya utgångstalet för hela kön.
**Körs av:** `tests/protocol/kor_m122_mutationsskikt.py` (uppdaterad: del 3
bor nu i motorn, radtyp använder motorns skanning). Rådata:
`docs/matningar/radata/m131_svep.json` (hela utfallet),
`docs/matningar/radata/m131_ut.txt` (utskriften).

## Resultat

### De fyra rättelserna

1. **Initierare i `VAR` undantas** från `SANT_TILL_FALSKT`/`FALSKT_TILL_SANT`
   (M-122 §6.2). Motorn hoppar över träffar på VAR-rader och tar nästa träff
   i stället, så taket per sort fortfarande fylls — med kodrader.
   Tidsconstanter i `VAR` undantas inte: ett `T#500ms` i deklarationen läses
   ofta utan att skrivas.
2. **`FLANK_TILL_NIVA` bytte namn till `FLANK_STRUKEN`** — det är vad den
   gör (stryker `trig(CLK := x)`-anropet; Q blir aldrig sant).
3. **Den riktiga nivåoperatorn heter nu `FLANK_TILL_NIVA`**: `inst.Q` byts
   mot instansens CLK-signal (M-122 §3, M-115). Instanser utan CLK i kartan
   hoppas över — TON/TOF utan CLK läser nivå ur IN-signalen, och det är ett
   annat fel.
4. **C0.4, uppmätt under C0.1:** skanningen ignorerar kommentarrader och
   kräver ordgräns. T-05 rad 18, T-08 rad 47 och P-03 rad 44 börjar alla på
   "var" mitt i en flerradig kommentar och svalde resten av filen, så att
   riktig kod undantogs; A-07 rad 129 ("varje ...") tände på `startswith`.
   Fortfarande en radskanning, ingen parsning — men den äter inte längre kod.

### Fixturen var röd före (disciplin: fixtur före mekanism)

`tests/enhet/test_mutation_c0.py` skrevs före rättelserna. Utskriften:

```
FAILED test_c0_initierare_i_var_undantas_fran_booleska_literaler
E  AssertionError: initierare i VAR raknades som skador:
    [('SANT_TILL_FALSKT', 4), ('FALSKT_TILL_SANT', 3)]
FAILED test_c0_flank_struken_heter_vad_den_gor
FAILED test_c0_flank_till_niva_ar_den_riktiga_f15
3 failed in 0.12s
```

C0.4-fixturen var röd ensam (`1 failed, 3 passed`) innan skanningen lagades.
Efteråt: `4 passed`. Full enhetssvit vid C0: 7404 gröna; 5 röda ligger i
andra köers ytor (D: `kor_fas18_vc_rigg` ×2; B: C-01/P-05-baslinje ×2;
tröskelhärkomst +1 från A/E:s nya konstanter) — ingen av dem rör mina filer.

### Det nya utgångstalet

Kört på träd `f48dbab`. B lade C-01 och P-05 med facit under tiden: **28**
dömbara uppgifter mot M-122:s 26.

| | M-122 (26 uppgifter) | M-131 (28 uppgifter) |
|---|---:|---:|
| skador | 809 | **899** |
| fångade | 718 (89 %) | **834 (93 %)** |
| överlevde | 91 (64 initierare + 27 kod) | **65 (alla 65 kod)** |
| beteende→beteende | 375 | **467** |
| beteende→text (lyckträffar) | 70 | **76** |
| text→text | 273 | **291** |

Borttaget brus: **63** booleska VAR-mutanter — alla 63 överlevde i M-122,
ingen fångades någonsin. Kontrollerat att ingen av de 63 var riktig kod som
svalts av ett fantomblock (0 av 63). Tillbakafyllnad: booleska kodmutanter
91 → 164, varav 19 överlever (7 `FALSKT_TILL_SANT` + 12 `SANT_TILL_FALSKT`).

Per sort (n, fångade av text/beteende, överlevde):

| sort | n | text | beteende | överlevde |
|---|---:|---:|---:|---:|
| `AND_TILL_OR` | 83 | 0 | 71 | 12 |
| `OR_TILL_AND` | 38 | 0 | 34 | 4 |
| `NOT_STRUKEN` | 82 | 0 | 78 | 4 |
| `JAMFORELSE_VAND` | 61 | 4 | 56 | 1 |
| `SANT_TILL_FALSKT` | 82 | 0 | 70 | 12 |
| `FALSKT_TILL_SANT` | 82 | 0 | 75 | 7 |
| `TID_FORDUBBLAD` | 42 | 0 | 38 | 4 |
| `FLANK_STRUKEN` | 31 | 0 | 31 | 0 |
| `FLANK_TILL_NIVA` (ny) | 35 | 0 | 14 | 21 |
| `FLANKENS_Q_TILL_SIGNAL` | 72 | 72 | 0 | 0 |
| `TID_OGILTIG` | 42 | 42 | 0 | 0 |
| `END_IF_STRUKEN` | 84 | 84 | 0 | 0 |
| `SEMIKOLON_STRUKET` | 84 | 84 | 0 | 0 |
| `ICKE_ASCII` | 81 | 81 | 0 | 0 |

Överlevarna: **14 skiljer på facitstimulus, 15 syns bara under perturbation,
36 osynliga.** Per uppgift i toppen: P-05: 8, P-03: 7, S-07: 6, A-03: 5,
H-05: 4, S-05: 4, C-01: 3, C-04: 3, H-04: 3.

Nivåoperatorn: 35 mutanter i 25 uppgifter, 14 fångade, 21 överlevde — varav
18 `SYS_RESET`, 2 handskaknings-`DONE` (H-05, S-07) och 1 `ST200_PML_SC`
(S-05, synlig bara under perturbation). M-122 §3 står kvar i större form:
facit ser nivåläsningen där sekvensen håller signalen, inte där den trycker
kort på återställningen.

Grind 2: 367 av 899 fångade, men bara **4 av 76 fällplatser**
(`TIDLITERAL:506`, `TYP:348`, `TYP:421`, `TYP:603`); 0 av M-111:s 35 aldrig
fyrade nådda. Av beteendesorterna fångar den exakt lyckträffarna (72
`FLANKENS_Q_TILL_SIGNAL` + 4 `JAMFORELSE_VAND`) och **0 av de 521 övriga**.
Referenser med egen anmärkning: inga (M-121:s fråga är lagad).

**Detta är utgångsläget för hela kön:** 93 %, 65 kodradsöverlevare, 14 + 15
som ett bättre facit kan nå. P-05 (ny, B:s facit från M-124) bär 7 av de 14
punktkraven — ett nytt facit utan kontrollpunkter, och C1:s första klass.

## LIMITS

* **Domaren är vår tolk, inte OpenPLC och inte STruC++.** "Fångad av
  beteendelagret" är fångad av det handskrivna spårfacitet kört i `st/tolk.py`
  (öppet sedan M-45). A-klassmätning: egen kod muterad, dömd av eget facit.
* **"OSYNLIG" betyder inte ekvivalent.** Fem handvalda perturbationer
  (tidsskala 0,25/0,5/2,0; sekvensen två gånger; puls hållen ×3) skilde inte
  mutant från referens. Ekvivalens är inte bevisad för någon av de 36.
* **Radtypen är en radskanning** (`mutation.var_rader`), nu
  kommentarsmedveten med ordgräns — fortfarande ingen parsning. Kvar som
  grovhet: `VAR`/`END_VAR` i stränglitteraler och block som aldrig stängs.
* **Tillbakafyllnaden ändrade nämnarens sammansättning.** Booleska
  kodmutanter gick 91 → 164; 19 av dem överlever. Jämförelsen M-122→M-131 är
  en omräkning med rättad motor, ingen rad-för-rad-differens.
* **Nivåoperatorn omfattas av taket** (`per_sort=3`, 35 mutanter i 25
  uppgifter). M-122 §3 körde utan tak (30 mutanter i 24 uppgifter).
* **28 uppgifter, inte 26.** C-01 och P-05 fick facit av kö B medan kön
  pågick (M-124). P-05:s 7 punktkravsluckor är ett nytt facit som ännu inte
  granskats — inte ett gammalt facit som försämrats.
* **Trädet rör sig.** Svepet kördes på `f48dbab`; två andra sessioner
  committade under körningen. En omkörning i morgon kan ge ±några mutanter.
* **En maskin, en eftermiddag, andra sessioner på samma dator.** Tiderna
  (23 s) är väggklocka under delad last, inte prestandatal.
* **De 5 röda enhetsproven vid C0 tillhör andra köer** (D ×2, B ×2,
  tröskelhärkomst ×1). Belägg: svitutskriften i arbetsytan; inget av dem
  nämner `mutation.py`, `kor_m122*` eller `test_mutation_c0.py`.
