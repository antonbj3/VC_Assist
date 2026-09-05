# M-130 — taket under naturlig belastning och processtopp: två frågor ur D4 besvarade med mätning

**Datum:** 2026-09-05 · Linux 6.8 · VC Premium 4.10 under Wine 11.16, **headless `:99`**, testprefixet `~/.wine-vc-test` (verifierat ur `/proc/<pid>/environ`)
**Mätt av:** `tests/protocol/kor_fas15_hopfogning.py` (`steg3_d`) och `kor_fas15_plcaxeln.py`.
**Fas:** 15 (`docs/spec/70_faser.md`), uppdrag D4 i `docs/uppdrag/KO_D_ogat_och_scenen.md`.
**Bygger på:** `M-97` (där 7 av 300 avläsningar under SIGSTOP spräckte hopfogningstaket med +1,09 s).

---

## Frågeställningen

I M-97 mättes att hopfogningens tak spricker under ett processtopp framkallat med `SIGSTOP`:
7 av 300 avläsningar låg utanför taket, som mest +1,09 s.

Uppdrag D4 ställde två frågor:
1. *Håller taket om störningen är en riktig belastning i stället för SIGSTOP?*
   (Fem sessioner kör på samma maskin, load average 10–16.)
2. *Vad gör ögat när taket spricker?*
   Om svaret är "rapporterar ett värde ändå" är tidsdomar under belastning opålitliga.

---

## Mätning 1: Håller taket under naturlig belastning?

M-87:s klämma (`kor_fas15_hopfogning.py::steg3_d`) kördes i 300 varv mot en körande VC
med 100 ms ålder, **utan artificiell SIGSTOP**, under den naturliga bakgrundsbelastningen
från maskinens övriga fyra parallella sessioner:

| Storhet | Ostörd körning (M-97 §5, 100 varv) | SIGSTOP 100 ms var 0,7 s (M-97 §5, 300 varv) | **Naturlig belastning (denna mätning, 300 varv)** |
|---|---|---|---|
| **Säkert över taket** | 0 (0,0 %) | **7 (2,3 %)** | **0 (0,0 %)** |
| Möjlig över (klämman skär taket) | 7 (7,0 %) | 30 (10,0 %) | **0 (0,0 %)** |
| Regressionen över taket | 0 (0,0 %) | 5 (1,7 %) | **0 (0,0 %)** |
| Tak median / max | 55 / 3 212 ms | 46 / 4 994 ms | **1 313 ms / 3 561 ms** |
| Klämmans bredd median / max | 25 / 25 ms | 25 / 170 ms | **20 ms / 135 ms** |
| Värsta överskridande av taket | +45 ms (möjlig) | **+1 091 ms (säkert)** | **−387,5 ms (marginal kvar överallt)** |
| $d$ (klämmans mitt) min / max | −51 / +22 ms | −2 419 / +84 ms | **−193,0 / +66,8 ms** |
| Takttermen median / max | — / — | 46 / 2 306 ms | **−8,1 ms / 169,1 ms** |

### Slutsats för fråga 1
**Ja, taket håller under naturlig belastning.**
Under naturlig CPU-trängsel fördelas preemptionen kontinuerligt över tid.
Pumpens klockterm `alder · takt_spridning` expanderar taket dynamiskt i takt med
att slagtakten jittrar (median tak stiger från 55 ms till 1313 ms).
Eftersom taket anpassar sig efter den uppmätta klockspridningen, ryms alla 300 avläsningars
faktiska fel ($d \in [-193, +67]$ ms) med god marginal inom taket.

Det som spräckte taket i M-97 var just **`SIGSTOP`**: en total processfrysning skapar
en stegformad diskontinuitet som inte syns i regressionsfönstrets delfönster förrän
stoppet redan inträffat.

---

## Mätning 2: Vad gör ögat när taket spricker eller osäkerheten växer?

Uppdragets varning var: *"Om svaret är 'rapporterar ett värde ändå', är varje tidsdom
under belastning opålitlig utan att någon märker det."*

Mätningarna i M-97, M-128 och M-129 visar exakt vad ögat gör. Det tiger inte ihjäl
osäkerheten, utan fångar den i tre explicita lager:

1. **På radnivå (`plc_otackt`):**
   När taket expanderar så att `ålder + tak > 0,250 s` (färskhetsfönstret) flaggas raden
   som `otackt: True`. Värdet räknas inte som färskt.
2. **På flanknivå (`_fasdom`, `sekvensdom`):**
   Flankens upplösningsosäkerhet sätts till `res_ms = max(las_s, prov_s + tak)`.
   Om ett toleranskrav är finare än denna osäkerhet (`max_ms < res_ms`) dömer ögat
   **`INCONCLUSIVE`** med klartexten:
   > *"kravet X ms är finare än ögats upplösning Y ms i den här takten"*.
   Ögat vägrar utfärda vare sig `PASS` eller `FAIL` på otillräcklig upplösning.
3. **På körningsnivå (`plc_axel`, braketten):**
   Om andelen otäckta rader överstiger 10 %, fälls hela körningen till **`INCONCLUSIVE`**:
   > *"PLC-axeln går inte att lita på: hopfogningens osäkerhet täcker färskhetsfönstret i N % av PLC-proven"*.
   Detta fällde `station_bra` i M-129 (84 % otäckt under belastning) trots att cellens logik var felfri.
4. **I utdatan och rapporterna:**
   Rapporten bär `SECTION LIMITS` med:
   `RESOLUTION sample=50.0ms read=...ms join=...ms phase=...ms`.
   Körningens värsta tak (`join`) och osäkerhet skrivs ut ordagrant.

Ögat rapporterar alltså **inte** ett opålitligt värde som om inget hänt:
det markerar osäkerheten, sänker domens avgörbarhet till `INCONCLUSIVE`, och varnar
användaren i utdatan.

---

## LIMITS

* **Provad ålder:** Klämmätningen kördes med simulerad ålder 100 ms (motsvarande
  en kopplare med 89 ms OpenPLC-varv).
* **SIGSTOP mot naturlig last:** Mätningen jämför artificiell SIGSTOP (M-97) med
  reell CPU-trängsel från Linux-schemaläggaren vid load 10–16. Andra typer av
  störningar (t.ex. nätverksbortfall, minnesbrist) har andra profiler.

---

## Vad som INTE är mätt

* **Övergångszon mellan kontinuerlig last och frysning:** Hur lång en tillfällig
  preemption-paus kan vara (t.ex. 10 ms, 50 ms, 100 ms) innan taket börjar spricka
  likt SIGSTOP har inte svepts systematiskt.
* **Kopplarens beteende vid faktiskt avbrott:** Mätningen använde efterliknad kopplare;
  OpenPLC v4:s OPC UA-server under samma systemlast mättes inte samtidigt.
