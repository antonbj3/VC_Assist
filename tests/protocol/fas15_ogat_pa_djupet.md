# FAS 15 ACCEPTANS — ögat på djupet

**beskriver:** `ext/vc_addon/vc_assist/oga_provtagning.py`, `oga_harledning.py`, `oga_analys.py`, `oga_kontrakt.py`, `svc/vc_assist_svc/guldgrind.py`, `svc/vc_assist_svc/plc/ogonkoppling.py`
**kontrakt:** `docs/spec/40_ogat.md`, `docs/spec/42_ogat_utbyggt.md`, `docs/matningar/M-65_ogat_pa_djupet.md` (v2-grammatiken)
**grind (70_faser.md):** *"Tidsserie över varje objekt i scenen, PLC-värdena på
samma axel, och domar som fäller på sekvens, timing, grepp, kollision och
genomflöde — var och en med en trasig cell som måste fällas. Hopfogningens
osäkerhet mätt, inte antagen."*
**körs av:** `tests/protocol/kor_fas15_scenen.py` (P15-1..3, M-86),
`kor_fas15_hopfogning.py` (P15-6, M-87), `kor_fas15_domarna.py` (P15-4/5/8/9,
M-88), `kor_fas15_plcaxeln.py` (M-97: hopfogningens giltighet, känd störning)

**Status: KÖRT 2026-09-05 mot en körande VC** (testprefixet, headless `:99`,
`installationsgrind` grön i varje körning). Utfall per punkt nedan; talen
står i M-86, M-87, M-88 och M-97.

| punkt | utfall | mätning |
|---|---|---|
| P15-1 hela scenen i en enhet | **GRÖNT** — roll 1,0 m, bakgrund 1,5 m; världsmatrisen släpade i samma tick (M-11) | M-86 |
| P15-2 en orörd komponents driv | **GRÖNT** — 49 av 49 stilla, brus 0,000000 mm (golv 1 µm) | M-86 |
| P15-3 VC:s kostnad för hela scenen | **GRÖNT** — sex rader, inget TAK; 4,3 µs per komponent och prov | M-86 |
| P15-4 `measureDistance` under körning | **GRÖNT** — monotont 3000 → 0,0 mm, kontakt vid 1000 mm origoavstånd; dom FAIL kollision ensam | M-88 |
| P15-5 kostnad per bevakat par | **GRÖNT** — 20 Hz höll vid 20 par; ≈ 0,2 ms per par och slag; kollision PASS på avstånd | M-88 |
| P15-6 PLC-flanken, upplösningen `RUN` | **GRÖNT** — `RUN` i 604 av 604; taket fick två termer till | M-87 |
| P15-7 fasdom mot en VC-fördröjning | **INTE KÖRT** — kräver ett skriptbeteende (M-13) | — |
| P15-8 fem trasiga celler i VC | **4 av 5** — grepp, sekvens, timing, kollision fälls ensamma; `station_bra` PASS. Genomflöde: inert statistik gav **PASS** (falskt grönt, lagat → INCONCLUSIVE); ingen VC-byggd cell fälls, `State` går inte att sätta utan process | M-88 |
| P15-9 LIMITS i riktig utdata | **GRÖNT** — 7 rader, `RUN`; utan sektionen NOT GOLD för alla | M-88 |
| P15-10 ögat säger PASS om något det inte kan se | **FUNNET TVÅ GÅNGER, på riktigt** — inert `vcStatistics` (M-88 §4) och steg dömda utan flankens tak (M-97 §1); båda har nu fixturer som föll | M-88, M-97 |
| hopfogningens giltighet (fas 8:s OGILTIG) | **BYGGT OCH PRÖVAT** — rad/flank/körning; jitter-störning fällde `station_bra` till INCONCLUSIVE i VC; taket håller inte under processtopp (7 av 300) | M-97 |

Originaltexten nedan är protokollets utkast från M-65 och står kvar som det
förutbestämda facit punkterna dömdes mot.

---

## Vad fasen påstår

Att ögat förstår vad som pågår i en scen: varje objekts läge över tid, PLC:ns
värden på samma tidsaxel, fem domare som var och en fäller sin egen felklass,
och en rapport som säger vad ögat **inte** ser. Och att allt det håller i en
riktig VC-scen, inte bara i syntetiska serier.

Notera vad som inte påstås: ingenting om att ögat ser sensorstuds,
ställdonsdynamik, fältbussjitter eller degraderade lägen. De finns inte i
simuleringen, och rapportens `LIMITS`-sektion säger det.

## Förutsättningar

* VC i testprefixet (`~/.wine-vc-test`, fas 0), bryggan igång (fas 1).
* Kopplaren mot OpenPLC över OPC UA (fas 6, M-39), så PLC-värden verkligen
  skjuts in i ögat med sin ålder.
* En cell med minst 50 komponenter. Ett bakgrundsobjekt räcker inte för P15-3.

## Punkterna

Varje punkt har ett förutbestämt grönt svar. En punkt som besvaras med "borde
fungera" är inte körd.

### P15-1 — hela scenen, i en enhet

Lägg en komponent på x = 1000 mm. Läs den som roll (`plan["parts"]`) och som
bakgrund (`scene`). **Grönt:** båda serierna visar `p[0] == 1.0` (meter).
Fel med tusen åt något håll är rött. (M-65 §2 mätte att bakgrunden låg i
millimeter i en falsk VC; VC:s riktiga `WorldPositionMatrix` är inte prövad.)

### P15-2 — en orörd komponents driv

Kör 60 s med en scen där ingenting rör sig. **Grönt:** varje bakgrundsobjekt
får `stilla = True`, `vaglangd_mm == 0` och `brus_mm` skrivs ned. Talet
`brus_mm` per objekt och minut är det M-10 ska sätta `ROR_SIG_MM` ur — det
skrivs in i M-10, inte här.

### P15-3 — VC:s egen kostnad för hela scenen

Svep 10, 50, 100, 200, 400, 800 komponenter. Läs `data()["scen"]["kostnad_ms"]`
(median och max per prov). **Grönt:** en tabell med sex rader. Rött är
en glesningshändelse med orsak `TAK` under 200 komponenter — då räcker inte
5 ms-budgeten till en normal cell, och `SCEN_BUDGET_MS` måste omprövas mot
`pump.TICK_BUDGET_S`. Notera separat om `sim.update()` per prov dominerar
(kör samma svep med `uppdatera_fore_last=False` och jämför; utan
`sim.update()` är matrisen inaktuell, M-11, så den körningen är BARA en
kostnadsmätning).

### P15-4 — `measureDistance` under en körande simulering

Två kuber om 1000 mm, den ena driven av bandrivaren mot den andra. Bevaka
paret. **Grönt:** `mind["d_mm"]` sjunker monotont till 0,0 och `kontakt` blir
sant i det prov kropparna nuddar; ögats dom är `FAIL kollision: ...` och
rapporten bär `COLLISION A x B t=...`. Rött: samma tal varje prov (då krävs
`nod.update()` på fler noder än paret, M-36), eller 0,0 först efter att
överlappet passerat.

### P15-5 — `measureDistance`:s kostnad per prov

Samma cell, 1, 5 och 20 bevakade par. Läs pumpens tick-tid. **Grönt:** en
tabell; rött är en tick-tid över `TICK_BUDGET_S` (25 ms) vid 5 par.

### P15-6 — PLC-flanken på läsningens tid, mot en riktig kopplare

Kopplaren skriver `Start` hög. Ögats `EDGE plc:Start RISE t=` ska ligga
**före** provet där värdet syns, med `t_prov − t == plc_alder_s`. Läs
`derived.timing.upplosning`: **grönt** är `las_s` nära kopplarens varvtid
(M-39: 89 ms median) och `hopfogning_kalla == "RUN"` med
`hopfogning_s` nära kopplarens `rtt_tak` (M-03: ~10–13 ms). `PRIOR` här är
rött — då kom taket inte fram genom `plc_in`.

### P15-7 — fasdom mot en riktig fördröjning

Kopplaren sätter `Start`; ett VC-skript svarar med `do_start` efter en känd
`delay(0.300)`. Plan: `plc_par = [{"plc": "Start", "signal": "Robot/do_start",
"max_ms": 100}]`. **Grönt:** `PHASE ... OUT_OF_TOL` och `FAIL timing: ...`.
Med `max_ms = 500`: `PHASE ... OK` och PASS. Med `max_ms = 20` i 20 Hz:
`INCONCLUSIVE` och orsaken säger *finare än ögats upplösning*. Rött är ett
PASS vid `max_ms = 20`: då påstår ögat något det inte kan se.

### P15-8 — fem trasiga celler i VC

Bygg de fem cellerna ur `tests/celler.py` i VC:s scengraf (samma väg som
`kor_fas2.py`): `station_utan_stopp`, `station_forsent`, `aldrig_gripen`,
`kontakt`, `station_svalt`. **Grönt:** var och en får `FAIL` med rätt
domare först i domsraden (`sekvens:`, `timing:`, `grepp:`, `kollision:`,
`genomflode:`), och `derived.domar` visar exakt en domare på `FAIL`.
Två domare på FAIL för samma cell är rött — då provar cellen inte det den
tror.

### P15-9 — LIMITS i ögats riktiga utdata

För varje körning ovan: rapporten bär `SECTION LIMITS` med fem
`NOT_SIMULATED`-rader, en `RESOLUTION`-rad med `RUN` och en `EXCLUDED
plc_scan`-rad. Guldgrinden ger `NOT GOLD (... LIMITS ...)` om sektionen tas
bort ur texten. **Grönt:** båda.

### P15-10 — det trasiga fallet: ögat säger PASS om något det inte kan se

Ta cellen från P15-7 med `max_ms = 20`. Ändra tillfälligt
`fasforhallande` så den dömer utan upplösning. **Rött ska bli synligt:**
`PHASE ... OK` och PASS för ett krav ögat inte kan skilja från noll. Återställ.
Punkten finns för att grinden ska ha fällt minst en gång innan den kallas
grind.

## Vad som INTE prövas här

* Windows (fas 13).
* Flera kopplare mot samma öga (M-42: sista inskottet vinner).
* `ROBOT`-sektionen i grammatiken (finns inte; robotfynd fäller domen i
  klartext och ligger i `derived.robotar`).
* Trösklarna M-10, M-18, M-19 — de sätts av sina egna mätningar, inte av
  detta protokoll. P15-2 och P15-3 ger dem underlag.

## Plattform
Linux ☑ *(kört 2026-09-05, M-86/M-87/M-88/M-97; P15-7 inte kört)*   Windows ☐ **oprövad**
