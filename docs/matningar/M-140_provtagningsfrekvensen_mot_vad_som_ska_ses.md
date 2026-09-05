# M-140 — provtagningsfrekvensen mot vad som ska ses: 11 bankuppgifter ogiltiga vid 17,2 Hz tyst provtagning, full täckning vid 224,7 Hz trafik

**Datum:** 2026-09-05 · Linux 6.8
**Mätt av:** `tests/protocol/kor_D10_provtagningsfrekvens.py` och `tests/enhet/test_provtagningsfrekvens_d10.py`.
**Fas:** 15 / Kö D punkt D10 (`docs/uppdrag/KO_D_ogat_och_scenen.md`).
**Bygger på:** `M-03` (takt: 17,2 Hz tyst och 224,7 Hz under trafik), `M-86` (ögat mot en körande VC) och `M-97` (PLC-axelns giltighet).

---

## Frågeställningen

I uppdrag D10 ställs frågan:
> *"Ögat provtar 17,2 Hz tyst och 224,7 Hz under trafik. En rörelse som är klar på 30 ms syns inte vid 17 Hz.
> Räkna, per domare, vilken snabbaste händelse den kan se — och jämför mot vad bankens uppgifter faktiskt kräver.
> Om någon uppgift kräver mer än ögat ger, är den uppgiftens dom ogiltig."*

En verifieringsdom är matematiskt meningslös om mätinstrumentets samplingsfrekvens understiger förloppets dynamik (Nyquist-Shannons samplingssats). Här beräknas upplösningsgränsen per domare, och bankens samtliga uppgifter granskas för att identifiera vilka domar som är ogiltiga i tyst regim.

---

## Ögats tidsupplösning per domare och regim

Ur `M-03` är två regimer uppmätta:
- **Tyst regim:** $f = 17,2\text{ Hz} \implies \Delta t = 58,14\text{ ms}$ (`delay(0.05)`).
- **Standardprovtagning:** $f = 20,0\text{ Hz} \implies \Delta t = 50,00\text{ ms}$.
- **Aktiv trafikregim:** $f = 224,7\text{ Hz} \implies \Delta t = 4,45\text{ ms}$ (`delay(0.005)`).

| Domare | Observerad händelse | Tyst regim (17,2 Hz) | Standard (20,0 Hz) | Trafik (224,7 Hz) | Begränsande mekanism |
|---|---|---|---|---|---|
| **sekvens** | Kortaste detekterbara puls | **58,1 ms** | 50,0 ms | **4,45 ms** | Minst 1 sample krävs för att se ett tillståndsbyte. |
| **timing** | Minsta upplösbara tidsfönster | **116,3 ms** | 100,0 ms | **8,90 ms** | Fönster $< 2\Delta t$ ger osäkerhet (`INCONCLUSIVE`, M-97). |
| **grepp** | Kortaste godkända bärsträcka | 500,0 ms | 500,0 ms | 500,0 ms | Fast logiskt golv `CARRY_MIN_SPAN_S = 0.50 s` i `oga_analys.py`. |
| **kollision** | Kortaste zonpassage utan tunnling | **58,1 ms** | 50,0 ms | **4,45 ms** | Passagetid $t = d/v$ måste överstiga $\Delta t$ för att $d=0$ ska registreras. |
| **genomflode** | Upplösning på ackumulerad tid | 58,1 ms | 50,0 ms | 4,45 ms | `vcStatistics` mäts internt; ögat läser av med perioden $\Delta t$. |

---

## Bankens tidskrav jämfört mot ögats upplösning

Samtliga 63 uppgifter i `bank/uppgifter/` analyserades:
- Samtliga uppgifter med explicit PLC-styrning har en scancykel på **20,0 ms** (50 Hz).
- Minsta tidssteg ($\Delta t_{\text{min}}$) mellan två händelser i banken är **20,0 ms** (ett PLC-scan).
- **11 av 63 uppgifter (17,5 %)** har händelser eller villkor som ändras snabbare än 58,1 ms:

| Uppgift | Kortaste $\Delta t$ | PLC scan | Utfall vid 17,2 Hz (58,1 ms) | Utfall vid 224,7 Hz (4,45 ms) |
|---|---|---|---|---|
| `A-02.json` | 20,0 ms | 20 ms | **OGILTIG** (puls missas i 65,6 % av fallen) | **GILTIG** (4,5 samples per puls) |
| `A-04.json` | 40,0 ms | 20 ms | **OGILTIG** (mindre än 1 sample-intervall) | **GILTIG** (9,0 samples per puls) |
| `A-08.json` | 40,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `H-01.json` | 20,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `L-01.json` | 20,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `S-01.json` | 20,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `S-05.json` | 40,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `S-06.json` | 40,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `S-07.json` | 20,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `T-01.json` | 20,0 ms | 20 ms | **OGILTIG** | **GILTIG** |
| `T-02.json` | 40,0 ms | 20 ms | **OGILTIG** | **GILTIG** |

*Övriga 52 uppgifter har antingen förlopp långsammare än 58 ms eller saknar tidsstyrda flanker.*

---

## Slutsatser

1. **Den tysta regimens gräns:**
   Vid 17,2 Hz provtagning kan ögat inte tillförlitligt döma signaler med varaktighet under 58,1 ms. En 20 ms puls missas med sannolikhet $1 - \frac{20}{58,14} \approx 65,6\,\%$. Alla domar rörande sekvens och timing för de 11 snabba bankuppgifterna är därför **ogiltiga** vid tyst provtagning.
2. **Trafikregimens fullständiga giltighet:**
   Vid 224,7 Hz aktiv provtagning ($\Delta t = 4,45\text{ ms}$) ryms minst 4,5 provpunkter i varje 20 ms PLC-scan. Noll uppgifter i banken kräver snabbare upplösning än 4,45 ms. Samtliga 63 bankuppgifters domar är därmed **fullt giltiga** under aktiv trafikprovtagning.
3. **Praktisk regel:**
   Verifikationsprov som involverar snabba 20 ms flanker (särskilt klasserna `A`, `H`, `L`, `S`, `T`) får aldrig köras i tyst regim utan måste alltid tvinga pumpen till aktiv trafikregim (`delay(0.005)` / 224,7 Hz).

---

## LIMITS

* **Beräkningen:** Bygger på deterministisk sampling utan faslåsning mellan ögats klocka och PLC-scanklockan.
* **Jitter:** Eventuellt tråd- och schemaläggningsjitter i Windows/Wine kan öka det effektiva provintervallet (M-97 mätte upp till +1,09 s under extrem störning).

---

## Vad som INTE är mätt

* **Mikrosekundstransienter:** Fältbussfel och kontaktstuds i hårdvara under 1 ms (simuleras ej i VC).
