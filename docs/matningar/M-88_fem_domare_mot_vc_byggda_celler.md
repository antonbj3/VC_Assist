# M-88 — fem domare mot VC-byggda celler: fyra föll rätt, den femte sa PASS på en svulten station

**Datum:** 2026-09-05 08:30 och [[TID2]] · Linux 6.8 · VC Premium 4.10 under
Wine 11.16, **headless `:99`**, testprefixet `~/.wine-vc-test` (verifierat ur
`/proc/<pid>/environ`)
**Mätt av:** `tests/protocol/kor_fas15_domarna.py` (L3, mot en körande VC),
två körningar; rådata i körningarnas `--json`. Fixturen ur fyndet:
`tests/enhet/test_stationsstatistik_som_inte_mater.py` (L1).
**Fas:** 15 (`docs/spec/70_faser.md`) — punkterna P15-4, P15-5, P15-8, P15-9 i
`tests/protocol/fas15_ogat_pa_djupet.md`.
**Steg 0:** VC körde repots kod i båda körningarna (`installationsgrind`:
`samma som repots kalla: ja`). Första försöket vägrade — jag hade ändrat
`oga_harledning.py` i repot efter installationen — och VC installerades om
och startades om innan något mättes. Grinden gjorde exakt det den finns för.

Fasens grind: *"domar som fäller på sekvens, timing, grepp, kollision och
genomflöde — var och en med en trasig cell som måste fällas."* M-65 mätte
matrisen på **syntetiska** serier. Här byggs cellerna i VC:s riktiga scengraf,
PLC-värdena går genom den riktiga bryggan och den riktiga `Ogonkoppling`, och
domen tas på det VC verkligen svarade.

---

## §1 P15-4 — `measureDistance` under en körande simulering: GRÖNT

Två kuber om 1000 mm med riktig geometri (`VC_BLOCK`). Den ena körs av
bandrivaren från 4000 mm till 1000 mm mellan origon; kubernas ytor möts vid
exakt 1000 mm. Paret bevakat med `mind`.

| | |
|---|---|
| metod | `measureDistance` (M-36; detektorn är avförd) |
| prov med `mind` | 100, **40 distinkta avståndsvärden** |
| avstånd | 3000,0 mm → 0,0 mm, i steg om 76,9 mm |
| prov där avståndet inte ökade | **100,0 %** |
| `kontakt` blev sant | i 61 prov, **första gången vid t = 2,00 s med origoavstånd 1000,0 mm** |

Det är rött enligt protokollet om avståndet står still (M-36:s fälla: ett
gammalt värde varje prov) eller om 0,0 kommer först efter att överlappet
passerat. Inget av det hände: avståndet följde banan prov för prov, och
kontakten kom i **det** prov ytorna nådde varandra — inte vid noll mellan
origon.

**Domen på VC:s egen serie:** `FAIL kollision: kollision mellan F15D_A och
F15D_B: kontakt mellan F15D_A och F15D_B vid t=2.00 s (minsta avstand 0,0
mm)`. Fällande domare: **`kollision` ensam**. Det är cellen `kontakt` (M-65)
byggd i VC.

## §2 P15-5 — kostnaden per prov, och den gröna riktningen: GRÖNT

21 kuber 3000 mm isär (2000 mm ytavstånd), 8 s per rad:

| bevakade par | prov | rate_hz | pumpens slag/s | dom | kollision |
|---|---|---|---|---|---|
| 1 | 161 | 20,0 | 197,4 | PASS | **PASS** |
| 5 | 160 | 20,0 | 193,8 | PASS | PASS |
| 20 | 165 | 20,0 | 188,7 | PASS | PASS |

Provtakten höll 20 Hz i alla tre; pumpens slagtakt sjönk 197 → 189 slag/s
med 20 par, alltså **≈ 0,2 ms per par och slag**. `TICK_BUDGET_S` (25 ms) är
långt borta. `MINDIST` gav 2000,0 mm för varje par — rätt ytavstånd.

Raden med **kollision = PASS** är inte dekoration: utan den bevisar §1
ingenting, för en domare som fäller allt klarar också §1.

## §3 P15-8 — cellerna i VC, första körningen

Varje cell byggs ur `tests/celler.py` som bana och PLC-schema; kropparna
skapas i VC, bandrivaren flyttar dem, `Plcdrivare` skjuter in cellens
PLC-värden på **rätt simuleringstid** genom `Ogonkoppling` (mätt ålder, mätt
tak, M-87). Stationscellerna bär `broms` som roll — pumpen kräver minst ett
spårat objekt, och `Stationsbygge` har just den.

| cell | dom i VC | fällande domare | väntat | PLC-axeln (M-97) |
|---|---|---|---|---|
| `station_bra` | **PASS** | — | PASS (grön kontroll) | 1 av 298 otäckta (0,3 %), tak max 0,498 s |
| `aldrig_gripen` | FAIL | **grepp** | grepp | — (ingen PLC) |
| `station_utan_stopp` | FAIL | **sekvens** | sekvens | 1 av 299 (0,3 %), tak max 0,588 s |
| `station_forsent` | FAIL | **timing** | timing | 2 av 359 (0,6 %), tak max 0,511 s |
| `kontakt` (§1) | FAIL | **kollision** | kollision | — |
| `station_svalt` | **PASS** | **ingen** | genomflöde | — |

Fyra av fem domare föll rätt, ensamma, på celler byggda i VC — och den gröna
kontrollen fick PASS. `station_forsent`:s orsak namnger exakt det steg cellen
förskjuter: *"cykel 0: plc:stopp FALL kom 3.00 s efter starten, fonstret ar
1.50-2.50 s"*. Den femte raden är fyndet.

## §4 Fyndet: genomflödesdomaren sa PASS på en svulten station

Cellen: en komponent med ett **riktigt** `vcStatistics`-beteende
(`createBehaviour(VC_STATISTICS, 'stat')` — skapbart enligt M-15, och
skrivgrinden släpper det: det är inget skriptbeteende, M-13). Ingen produkt
når den. Kravet: `genomstromning = {"max_svalt_s": 1.0}`. Körningen: 6 s.
Facit ur M-65: **FAIL genomflöde**.

Svaret: **PASS, "allt inom marginal"**, `svalt 0 s`, 120 stationsprov.

Varje stationsprov såg exakt så här ut, körningen igenom:

```
{'blocked_pct': 0.0, 'broken_pct': 0.0, 'busy_pct': 0.0, 'cur': 0,
 'idle_pct': 0.0, 'in': 0, 'out': 0, 'state': ''}
```

VC:s statistik på en komponent **utan process** rapporterar ett tomt
tillståndsnamn och noll i varje procent. `_ar_svulten` läste `''` som ett
tillståndsnamn — ett som inte är `IDLE` — och svarade *inte svulten*.
Stationen var ledig och tom i sex sekunder, och ögat sa att allt var inom
marginal. Ett falskt grönt, på den enda av de fem domarna som inte hade
någon VC-byggd cell före den här mätningen.

Orsaken är inte VC:s. Ett `vcStatistics`-beteende får sitt tillstånd av
komponentens **process** (`stats.State = VC_STATISTICS_IDLE` i ett
processkript). Utan process finns inget tillstånd, och statistiken **mäter
inte** — den är inte "ledig", den är inert. Ögat kunde inte skilja de två,
och valde fel sida.

### Åtgärden: en statistik som aldrig mätt är obestämbar

`oga_harledning.stationslage` markerar nu en station **obestämbar** när ingen
rad i serien visar något — inget tillståndsnamn, ingen produkt in eller ut,
ingen procent över noll (`_mater`). En tom sträng räknas som **frånvaro** av
ett tillstånd (`_tillstand`), inte som ett namn. Genomflödesdomaren tar då
M-74:s väg: kravet är deklarerat men ingen station provades → **INCONCLUSIVE**,
inte PASS och inte FAIL.

Fixturen är VC:s rad ordagrant:
`test_den_inerta_statistiken_ur_VC_ger_INCONCLUSIVE_inte_PASS`. Den föll
mot koden före lagningen. Grannproven håller de andra riktningarna: med
`state: "IDLE"` på samma rad är stationen svulten och **fälls**; med kravet
100 s på samma serie **PASS**; en statistik som börjar mäta mitt i körningen
räknas från och med då; och ett tomt namn med `idle_pct` 100 % avgörs på
procenten, inte på namnet.

### Andra körningen: två varianter i VC

[[SVALT2]]

## §5 P15-9 — LIMITS i ögats riktiga utdata, och guldgrinden mot den: GRÖNT

Varje rapport ur VC bar `SECTION LIMITS` med **fem `NOT_SIMULATED`-rader**,
en `RESOLUTION`-rad med **`RUN`** och en `EXCLUDED plc_scan 40.0ms`-rad.
`station_bra`:s: `RESOLUTION sample=50.0ms read=50.1ms join=497.70ms RUN
phase=547.7ms` — `join` är körningens *värsta* tak (M-87 §5), inte flankens.

Guldgrinden, samma rapporter:

| cell | med LIMITS | **utan** LIMITS (sektionen bortklippt) |
|---|---|---|
| `station_bra` | GOLD | **NOT GOLD** (*rapporten saknar sektionen LIMITS, sa den grinden har aldrig kort*) |
| `station_svalt` (körning 1, PASS) | GOLD | NOT GOLD (samma skäl) |
| `aldrig_gripen`, `station_forsent`, `station_utan_stopp` | NOT GOLD (*ogat sa FAIL*) | NOT GOLD (saknar LIMITS) |

Sektionen bort → guld bort, för alla fem. (Första körningen skrev
"LIMITS-rader 0" i sin egen sammanräkning: raderna är indenterade i
rapporten och räknades på oskalad rad. Räkningen är lagad; grindens svar var
rätt hela tiden.)

## §6 Ett bifynd i `saknade`

Varje serie bar `{"spec": "app.Components", "varfor": "en komponent saknar
Name: ReferenceError"}`. En komponent i den delade scenen (andra agenters
`ST8_*`-linje) svarade `ReferenceError` på `.Name` — sannolikt en komponent
som tagits bort men ännu refereras. Ögat skrev det i `saknade` och fortsatte;
det kraschade inte, och det tystade inte fyndet. Vilken komponent det är
har jag inte utrett.

## LIMITS

* **PLC-värdena kommer från skriptet, inte från en PLC.** Vägen är den
  riktiga (`Ogonkoppling` → `plc_in` → `Plckalla`, mätt ålder, mätt tak) men
  källan är cellens schema. Ingen OPC UA-läsning gjordes (M-39:s kopplare är
  inte inkopplad i den här mätningen).
* **P15-7 (fasdom mot en riktig fördröjning i ett VC-skript) är inte kört.**
  Det kräver ett skriptbeteende, och `createBehaviour(VC_SCRIPT)` dödar pumpen
  (M-13). Fasdomen är mätt syntetiskt (M-65 §3) och upplösningen mot VC
  (M-87 §6), men ingen `PHASE`-rad har fällts mot en VC-signal med känd
  fördröjning.
* **Genomflödescellen i VC har ingen process.** Varianten med `State` satt
  till `VC_STATISTICS_IDLE` efterliknar vad en process gör; den mäter inte en
  riktig stations svält utan att statistiken svarar rätt när tillståndet
  finns. En station med riktig process, produkter som kommer och går, och
  `ComponentsArrived` som räknar upp — är inte byggd. Blockering (`BLOCKED`)
  är inte prövad i VC alls.
* **Kollisionen är ett ytavstånd på 0,0 mm, inte en detektorträff.**
  `getHitFeatureA/B` (vilken yta) finns bara ur detektorn, och den är avförd
  (M-36). `COLLISION`-raden bär noderna, inte ytorna.
* **Bandrivaren flyttar kropparna i steg om 50 ms** — ingen fysik, inga
  mellanlägen. Kontaktögonblicket har därför upplösningen ett prov.
* **En scen som delas med andra agenter.** `saknade` bar en främmande
  komponent utan `Name` i varje serie; PLC-axelns tak nådde 0,5–0,6 s i
  enstaka rader (M-97 visar att sådana toppar hör till pumpens takt-fönster,
  inte till cellerna).
* **Windows** (fas 13).
