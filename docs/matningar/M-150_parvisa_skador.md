# M-150 — två skador samtidigt: hur ofta parvisa fel tar ut varandra och blir osynliga

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell.
Provade uppgifter: `P-03`, `C-04`, `S-07`, `A-03`, `S-01`, `P-05`.
**Prövar:** Kö C punkt C10: andra ordningens mutationstestning (parvisa skador).
Kör par av skador på uppgifter med många mutanter och räkna hur ofta paret
är osynligt (godkänt av domaren) fast båda delarna fälls var för sig.
**Körs av:** `docs/matningar/radata/m150_parvisa_skador.py`.
Rådata: `docs/matningar/radata/m150_ut.txt`.

## Resultat

### §1 Uppmätt utfall över 1 360 par

För sex uppgifter valdes alla enradiga beteendeskador som bevisligen fångas
individuellt av spårfacit (18–29 skador per uppgift). Alla unika par av
sådana skador på skilda rader kombinerades i koden och dömdes av domaren:

| Uppgift | Individuellt fångade skador | Par testade | Par som tog ut varandra | Felfrekvens (utsläckning) |
|---|---:|---:|---:|---:|
| `P-03` | 19 | 166 | 0 | 0,00 % |
| `C-04` | 25 | 288 | **1** | **0,35 %** |
| `S-07` | 29 | 393 | 0 | 0,00 % |
| `A-03` | 18 | 148 | 0 | 0,00 % |
| `S-01` | 20 | 181 | 0 | 0,00 % |
| `P-05` | 20 | 184 | **1** | **0,54 %** |
| **Totalt** | **131** | **1 360** | **2** | **0,147 %** |

**Huvudfynd:**
1. **I 99,85 % av fallen avslöjas paret:** En enskild domare som fångar två fel
   var för sig fångar nästan alltid kombinationen av dem.
2. **Utsläckning sker i 0,15 % av fallen (2 av 1 360):** Två fel som var för
   sig gör koden röd kan samverka så att koden blir 100 % grön under alla facitsekvenser.

### §2 De två utsläckningsmekanismerna

Båda fallen uppvisar exakt samma strukturella mönster: **samtidig polaritetsinvertering
av en intern boolesk variabels producent och konsument**.

#### Fall 1: `C-04` (rad 25 + rad 54)
* **Originalkod:**
  ```pascal
  25:     xStopp := FALSE;
  ...
  54: xDriftsklar := EMG_OK AND ST420_LGT_CLEAR AND NOT xStopp ...;
  ```
* **Skada 1 (rad 25, `FALSKT_TILL_SANT`):** `xStopp := TRUE;`.
  Individuellt: `xStopp` sätts hög vid kvittering, vilket gör `NOT xStopp` låg i
  beräkningen av `xDriftsklar`. Maskinen startar aldrig. **Fälls.**
* **Skada 2 (rad 54, `NOT_STRUKEN`):** `... AND xStopp ...`.
  Individuellt: `xDriftsklar` kräver att `xStopp` är sann, men efter kvittering
  är `xStopp` falsk. Maskinen startar aldrig. **Fälls.**
* **Kombinationen (Skada 1 + Skada 2):**
  Rad 25 sätter `xStopp := TRUE`. Rad 54 kräver `AND xStopp`.
  Eftersom `xStopp` sattes hög utvärderas rad 54 till sann! `xDriftsklar` blir hög
  i exakt samma scan som i referensen. Signalen `xStopp` bytte roll från
  aktiv-hög-stopp till aktiv-låg-körning, och domaren ser ingen avvikelse!

#### Fall 2: `P-05` (rad 26 + rad 28)
* **Originalkod:**
  ```pascal
  26: xDriftsklar := EMG_OK AND AIR_OK AND NOT xLasFel;
  ...
  28: IF NOT xDriftsklar THEN
  ```
* **Skada 1 (rad 26, `NOT_STRUKEN`):** `... AND xLasFel;`.
  Individuellt: `xDriftsklar` blir hög bara vid låsfel. **Fälls.**
* **Skada 2 (rad 28, `NOT_STRUKEN`):** `IF xDriftsklar THEN`.
  Individuellt: stoppgrenen körs vid normaldrift i stället för vid fel. **Fälls.**
* **Kombinationen (Skada 1 + Skada 2):**
  `xDriftsklar` inverteras i tilldelningen (rad 26), och inverteras tillbaka i
  villkoret (rad 28). Dubbel negation: stoppgrenen körs fortfarande vid `xLasFel`,
  och maskinen körs normalt när felet är borta.

## LIMITS

* **Körningen gjordes på parvisa skador på olika rader (2-order).** Tre eller fler
  samtidiga fel (higher-order mutations) har inte provats p.g.a. kombinatorisk explosion.
* **Urvalet begränsades till enradiga skador.** Mutationer som flyttar rader
  (som `FLANK_TAVLAR`) ingick inte i kombinationsgeneratorn för att garantera
  stabil radmatchning.
* **Spåret provar utsignalerna.** Att paret blir grönt bevisar att cellens
  observerbara I/O-beteende är identiskt under alla sekvenser, trots att de
  interna tillståndsvariablerna har bytt polaritet.
