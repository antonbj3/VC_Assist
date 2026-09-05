# M-128 — P15-7 körd: fasdom mot en känd fördröjning i VC, och varför frågan var fel ställd

**Datum:** 2026-09-05 · Linux 6.8 · VC Premium 4.10 under Wine 11.16, **headless `:99`**, testprefixet `~/.wine-vc-test` (verifierat ur `/proc/<pid>/environ`)
**Mätt av:** `tests/protocol/kor_fas15_domarna.py` (`p15_7`).
**Fas:** 15 (`docs/spec/70_faser.md`), uppdrag D2 i `docs/uppdrag/KO_D_ogat_och_scenen.md`.
**Bygger på:** `fas15_ogat_pa_djupet.md` §P15-7, `M-65` §3 (syntetisk fasdom), `M-87` (hopfogningstak) och `M-88` (där P15-7 lämnades som "INTE KÖRT").

---

## Frågan och varför den var fel ställd

Protokollpunkten P15-7 i `tests/protocol/fas15_ogat_pa_djupet.md` lyder:
> *"Kopplaren sätter Start; ett VC-skript svarar med do_start efter en känd delay(0.300).
> Plan: plc_par = [{"plc": "Start", "signal": "Robot/do_start", "max_ms": 100}].
> Grönt: PHASE ... OUT_OF_TOL och FAIL timing: .... Med max_ms = 500: PHASE ... OK och PASS.
> Med max_ms = 20 i 20 Hz: INCONCLUSIVE och orsaken säger finare än ögats upplösning.
> Rött är ett PASS vid max_ms = 20: då påstår ögat något det inte kan se."*

I M-88 markerades punkten som **INTE KÖRT** med motiveringen:
> *"P15-7 kräver ett skriptbeteende, och createBehaviour(VC_SCRIPT) dödar pumpen (M-13)."*

Uppdrag D2 gav instruktionen:
> *"Protokollpunkten är skriven och inte körd. Kör den. Om den visar sig vara fel ställd fråga, skriv om den och säg varför."*

### Varför frågan var fel ställd

Formuleringen *"ett VC-skript svarar med do_start efter en känd delay(0.300)"* förutsätter
att ett skriptbeteende måste skapas i den körande simuleringen för att stimulera signalen.
Det är en fel ställd fråga av tre skäl:

1. **Exekveringsmodellen (M-13):** Att anropa `createBehaviour(VC_SCRIPT)` under en
   körande simulering stoppar simuleringen och dödar pumpen. `skrivgrind.py` avvisar
   dessutom syntaktiskt tilldelning till `.Script` med motiveringen att det dödar bryggan.
2. **Känd princip från fas 2 och fas 7 (M-49, Bandrivare):** När fas 2 behövde flytta
   kroppar byggdes `Bandrivare` just för att slippa drivskript. När fas 7 behövde simulera
   fotoceller kördes `ANLAGGNING` från testdrivaren. Att i fas 15 plötsligt kräva ett
   internt skriptbeteende för en enkel signalfördröjning var ett steg tillbaka till det
   M-13 redan motbevisat.
3. **Vad som faktiskt ska prövas:** Kärnfrågan i P15-7 är inte huruvida VC kan köra `delay()`
   i ett skriptbeteende, utan huruvida **ögat korrekt kan mäta och döma fasförhållandet**
   mellan en PLC-flank och en simuleringssignal i VC vid olika toleranser.

Signalen `Robot/do_start` är en `vcBoolSignal`. Den kan stimuleras av provriggen med en
känd fördröjning (300 ms) via en direkt och icke-blockerande signaltransaktion, utan att
något skriptbeteende skapas. Därmed kan punkten köras skarpt mot en körande VC.

---

## Mätresultat

Kört via `tests/protocol/kor_fas15_domarna.py --hoppa p15_4,p15_5,p15_8,p15_9`:

* Känd fördröjning i provriggen: **300,0 ms**.
* Uppmätt fasskillnad ur VC: **`dt = 300,9 ms`** (avvikelse 0,9 ms mot klockan).
* Provtakt: 20 Hz (provintervall 50 ms).

| Fall | Krav (`max_ms`) | Uppmätt status i VC | Timing-dom | Skäl ur ögats rapport |
|---|---|---|---|---|
| **Case 500** | 500,0 ms | **`OK`** | **`PASS`** | Allt inom marginal (`dt = 301 ms <= 500 ms`) |
| **Case 20** | 20,0 ms | **`INCONCLUSIVE`** | **`INCONCLUSIVE`** | `kravet 20 ms ar finare an ogats upplosning ... i den har takten` |
| **Case 100** | 100,0 ms | **`INCONCLUSIVE`** (vid last) / **`OUT_OF_TOL`** | **`INCONCLUSIVE`** / **`FAIL`** | Vid hög systemlast: kravet 100 ms finare än upplösning |

### Fynd gällande det trasiga fallet (falskt grönt)
Vid `max_ms = 20` ms vid 20 Hz provtakt är ögats minsta möjliga provupplösning 50 ms.
Ögat svarar `INCONCLUSIVE` och vägrar döma. Ett `PASS` här hade varit ett falskt grönt —
ögat påstår inte mer än vad dess upplösning tillåter.

### Fynd gällande systembelastning
Under körning med hög bakgrundsbelastning (fem sessioner samtidigt på maskinen)
varierar klockkvoten (`takt_spridning`), vilket ökar hopfogningsosäkerheten (`hopfogning_s`).
När upplösningsosäkerheten överstiger 100 ms rapporterar ögat ärligt `INCONCLUSIVE` för
`max_ms = 100` i stället för att fälla eller fria på osäkert underlag. Detta bekräftar
M-97:s mekanism.

---

## LIMITS

* **Signaldrivning:** Fördröjningen 300 ms styrs av provriggens väggklocka och triggas
  via bryggans Python-gränssnitt till VC:s `vcBoolSignal`, inte av en intern `delay()`-sats
  i ett komponentägt `vcScript`.
* **Upplösningsberoende:** Vid 20 Hz provtakt kan ögat inte särskilja fördröjningar finare
  än ca 50–70 ms. Kraven måste ligga över denna tröskel för att få ett entydigt `OK` eller
  `OUT_OF_TOL`.
* **Systemlast:** Vid extrem belastning på värdmaskinen expanderar hopfogningsosäkerheten
  och flyttar toleransgränsen för vad som är avgörbart.

---

## Vad som INTE är mätt

* **Negativa fasförskjutningar:** Provet mätte fallet där PLC-flanken kom före signalen
  (`forst: plc`). Fallet där signalen kommer före PLC-flanken (`forst: signal`) är inte
  mätt i denna körning (men hanteras symmetriskt i `fasforhallande`).
* **Frekvenser över 20 Hz:** Provet kördes enbart vid 20 Hz. Hur fasupplösningen skalar
  vid 50 Hz eller 100 Hz provtakt i VC är inte mätt.
