# M-133 — kompositionsdomarna över fyra nya linjetopologier: kaskadsvält, buffertblockering, sammanflödeskollision och slutet återflöde

**Datum:** 2026-09-05 · Linux 6.8
**Mätt av:** `tests/protocol/kor_D6_linjetopologier.py` och `tests/enhet/test_linjetopologier_d6.py`.
**Fas:** 15 / Kö D punkt D6 (`docs/uppdrag/KO_D_ogat_och_scenen.md`).
**Bygger på:** `M-74` (kompositionsfel i enkla tvåstationsceller), `M-88` (fem domare i VC-byggda celler) och `M-127` (genomflödesdomaren fälld i körande VC).

---

## Frågeställningen

I `M-74` och `M-88` prövades de fem domarna mot enkla en- och tvåstationsceller.
Uppdrag D6 ställer kravet att gå bortom den enkla linjen och pröva kompositionsdomarna
mot fyra fundamentala tillverkningstopologier:

1. **Seriell linje med tre stationer:** kaskadsvält och ackumulerad cykeltid ($A \to B \to C$).
2. **Linje med buffert:** buffertblockering och buffertsvält ($A \to \text{BUF} \to B$).
3. **Parallella grenar:** delning och sammanflöde med skiljedom ($\text{IN} \to G_1 \parallel G_2 \to \text{UT}$).
4. **Återflödeslinje / slinga:** omarbete, returflödeskrock och cirkulärt dödläge ($A \to B \to \text{RETUR} \to A$).

För varje topologi krävs:
- Definition av kompositionens invarianta krav (vad gör linjen hel som helhet?).
- Injicering av minst två distinkta kompositionsfel som kompositionsdomarna måste fälla.
- Bevis för varför lokal komponentspecifikation inte räcker för global hälsa.

---

## De fyra topologierna och deras invarianta krav

### 1. SERIELL_3 ($A \to B \to C$)
* **Topologi:** Tre stationer i serie med transportörer emellan.
* **Globala invarianter:**
  1. *Genomströmningskontinuitet:* Nedströms station $C$ får inte stå svulten mer än tillåten buffertmarginal (`max_svalt_s = 2.5 s`).
  2. *Resursdelning:* Ytterstationerna $A$ och $C$ delar ett gemensamt utmatningsdon/robot; de får inte aktivera utmatning samtidigt (`forregling: [a_slapp, c_slapp]`).
* **Injicerade kompositionsfel:**
  - `K_SER_1` (Kaskadsvält): Ett uppströms stopp vid $A$ propagerar genom $B$ och leder till att station $C$ svälter ut under hela mätningen (8.9 s svält). Fälls av **genomflödesdomaren**.
  - `K_SER_2` (Delad resurskollision): $A$ och $C$ anropar båda det delade donet samtidigt (0.60 s överlapp). Fälls av **sekvensdomaren**.

### 2. BUFFERT ($A \to \text{BUF} \to B$)
* **Topologi:** Två stationer med mellanliggande dynamisk buffert.
* **Globala invarianter:**
  1. *Avledningskapacitet:* Station $A$ får inte blockeras på grund av överfull buffert (`max_blockerad_s = 2.5 s`).
  2. *Matningsstabilitet:* Station $B$ får inte svältas på grund av utebliven tömning (`max_svalt_s = 2.5 s`).
* **Injicerade kompositionsfel:**
  - `K_BUF_1` (Buffertblockering): Mottagande station $B$ stoppar; bufferten fylls och blockerar $A$ under hela körningen (8.9 s blockering). Fälls av **genomflödesdomaren**.
  - `K_BUF_2` (Buffertsvält): Utmatningen ur bufferten hänger sig; station $B$ blir stående tom och overksam (8.9 s svält). Fälls av **genomflödesdomaren**.

### 3. PARALLELL ($\text{IN} \to G_1 \parallel G_2 \to \text{UT}$)
* **Topologi:** Inmatning förgrenas till parallella stationer $G_1$ och $G_2$, som därefter sammanstrålar på en gemensam uttransportör.
* **Globala invarianter:**
  1. *Kollisionsfritt sammanflöde:* Gren 1 och gren 2 får inte släppa produkter till sammanflödespunkten samtidigt (`forregling: [g1_slapp, g2_slapp]`).
  2. *Balans:* Ingen gren får svältas ut på grund av felaktig växelstyrning (`max_svalt_s = 2.5 s`).
* **Injicerade kompositionsfel:**
  - `K_PAR_1` (Sammanflödeskollision): Skiljedomen fallerar; båda grenarna öppnar sina utmatningsspärrar samtidigt mot samlingspunkten (0.60 s samtidig frigivning). Fälls av **sekvensdomaren**.
  - `K_PAR_2` (Grensvält / obalans): Inmatningsväxeln dirigerar allt gods till $G_1$; $G_2$ svälter helt (8.9 s svält). Fälls av **genomflödesdomaren**.

### 4. ATERFLODE ($A \to B \to \text{RETUR} \to A$)
* **Topologi:** Sluten krets där detaljer från station $B$ som kräver omarbete leds tillbaka till $A$:s inmatning via en returbana.
* **Globala invarianter:**
  1. *Inmatningsväxelns ömsesidiga uteslutning:* Nytt gods och omarbetat returgods får inte matas in samtidigt på den gemensamma inbanan (`forregling: [nytt_in, retur_in]`).
  2. *Cirkulär frihet (livelock/deadlock):* Returslingan får inte mättas så att stationerna blockerar varandra cirkulärt (`max_blockerad_s = 1.0 s`).
* **Injicerade kompositionsfel:**
  - `K_REC_1` (Återflödeskollision): Returgods anländer samtidigt som nytt gods släpps in; ingen förregling spärrar inflödet (0.60 s konflikt). Fälls av **sekvensdomaren**.
  - `K_REC_2` (Cirkulärt dödläge): Slingan mättas, $B$ kan inte bli av med detaljer och fastnar i permanent blockering (8.9 s blockering). Fälls av **genomflödesdomaren**.

---

## Mätresultat

Körning med 180 provpunkter per scenario (20 Hz, 3 cykler):

| Topologi | Fall | Utfall | Fällande domare | Registrerad orsak |
|---|---|---|---|---|
| **SERIELL_3** | `HEL` | **PASS** | — | Allt inom marginal |
| SERIELL_3 | `K_SER_1` | **FAIL** | genomflode | station C svalt 8.9 s (krav max 2.5 s) |
| SERIELL_3 | `K_SER_2` | **FAIL** | sekvens | förregling bröts: `plc:a_slapp` och `plc:c_slapp` höga samtidigt (0.60 s) |
| **BUFFERT** | `HEL` | **PASS** | — | Allt inom marginal |
| BUFFERT | `K_BUF_1` | **FAIL** | genomflode | station A blockerad 8.9 s (krav max 2.5 s) |
| BUFFERT | `K_BUF_2` | **FAIL** | genomflode | station B svalt 8.9 s (krav max 2.5 s) |
| **PARALLELL** | `HEL` | **PASS** | — | Allt inom marginal |
| PARALLELL | `K_PAR_1` | **FAIL** | sekvens | förregling bröts: `plc:g1_slapp` och `plc:g2_slapp` höga samtidigt (0.60 s) |
| PARALLELL | `K_PAR_2` | **FAIL** | genomflode | station G2 svalt 8.9 s (krav max 2.5 s) |
| **ATERFLODE** | `HEL` | **PASS** | — | Allt inom marginal |
| ATERFLODE | `K_REC_1` | **FAIL** | sekvens | förregling bröts: `plc:nytt_in` och `plc:retur_in` höga samtidigt (0.60 s) |
| ATERFLODE | `K_REC_2` | **FAIL** | genomflode | station B blockerad 8.9 s (krav max 1.0 s) |

Totalt: **4 av 4 friska konfigurationer ger PASS**; **8 av 8 kompositionsfel fälls distinkt** av antingen sekvens- eller genomflödesdomaren.

---

## Bevis: Varför lokal specifikation inte räcker för global hälsa

I enhets- och integrationstestning görs ofta antagandet att om varje station uppfyller sin lokala specifikation så fungerar anläggningen. Det prövades explicit i `test_lokal_spec_racker_inte_for_global_halsa()` för sammanflödeskollisionen `K_PAR_1`:

1. **Lokal stationsanalys för Gren 2 (`stat_g2`):**
   - Stationen cyklar som förväntat, bearbetar detaljer under 67 % av tiden (`svalt_s = 2.0 s <= 2.5 s`).
   - Inga lokala gränsvärden överträds.
   - Lokal dom: **`PASS`**.
2. **Global kompositionsanalys:**
   - Gren 1 cyklar också helt enligt sin lokala specifikation.
   - Men vid överlämning till samlingsbanan saknas ömsesidig uteslutning: `g1_slapp` och `g2_slapp` aktiveras samtidigt under 0.60 s.
   - Två produkter matas ut på samma fysiska utrymme samtidigt.
   - Global kompositionsdomare fäller: **`FAIL`** (`sekvens`).

Slutsats: **Kompositionsfel existerar uteslutande i snittet mellan komponenter.** Ingen komponent i `K_PAR_1`, `K_SER_2` eller `K_REC_1` har ett internt fel i sin lokala kod; felet uppstår i avsaknaden av en global koordineringsinvariant. Kompositionsdomare på helsystemnivå är därför oersättliga.

---

## LIMITS

* **Diskretisering och samplingsfrekvens:** Mätningen utfördes vid 20 Hz (50 ms per sample). Samtidiga signaler kortare än 50 ms kan inte särskiljas.
* **Stationstillstånd:** Stationernas tillstånd modelleras via `BUSY`, `IDLE` och `BLOCKED` enligt Visual Components processtermer och mappas via `oga_harledning.py`.
* **Kravspecifikation:** Gränsvärdena (`max_svalt_s` och `max_blockerad_s`) är satta utifrån anläggningens taktcykel (3.0 s per cykel; tillåten icke-produktiv tid satt till < 1 cykeltid).

---

## Vad som INTE är mätt

* **Kontinuerlig hastighetsreglering:** Transportörer med analog variabel hastighet där friktion och glidning påverkar avståndet mellan artiklar.
* **Godsidentifiering (RFID/streckkod):** Sortering baserad på produkt-ID i parallella grenar eller återflödesslingor.
