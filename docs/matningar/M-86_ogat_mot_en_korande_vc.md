# M-86 — ögat mot en körande VC: hela scenen, i en enhet, utan driv, och vad den kostar

**Datum:** 2026-09-05 08:08 · Linux 6.8 · VC Premium 4.10 under Wine 11.16,
**headless `:99`**, testprefixet `~/.wine-vc-test` (verifierat ur
`/proc/<pid>/environ`: `WINEPREFIX=/home/anton/.wine-vc-test`, `DISPLAY=:99`)
**Mätt av:** `tests/protocol/kor_fas15_scenen.py` (L3, mot en körande VC), en
körning; rådata i körningens `--json`.
**Fas:** 15 (`docs/spec/70_faser.md`) — punkterna P15-1, P15-2, P15-3 i
`tests/protocol/fas15_ogat_pa_djupet.md`.
**Steg 0:** VC körde repots kod (`installationsgrind`: `samma som repots
kalla: ja`, 11 filer, installerad 06:39). Utan den raden mäter en L3-körning
kod som inte längre finns (M-87 §0).

Fasens krav är operatörens: tidsserier över **alla objekts positioner**.
`42_ogat_utbyggt.md` §1 lovar att varje komponent i `app.Components` får sin
pose i varje prov. M-65 lagade enheten i den vägen — men i en **falsk** VC.
Här är samma tre punkter mätta i den riktiga.

---

## P15-1 — hela scenen, i en enhet: GRÖNT

Två komponenter byggda på x = 1000 mm och x = 1500 mm (VC:s världsenhet,
millimeter, M-33), genom kön (I12). Den första lästes som **roll**
(`plan["parts"]`), den andra som **bakgrund** (`scene`). 60 prov.

| Väg | VC säger (mm) | Serien säger (m) | |
|---|---|---|---|
| roll `F15_000` | `PositionMatrix` 1000,0 · `World` 1000,0 | `p = [1.0, 0.0, 0.0]` | OK |
| bakgrund `F15_001` | `PositionMatrix` 1500,0 · `World` 1500,0 | `p = [1.5, 0.0, 0.0]` | OK |

Båda vägarna ger meter. Ett fel med tusen åt något håll — det M-65 §2 fann i
den falska VC:n — finns inte i den riktiga.

### M-11 mätt igen, i samma tick

Provet läste `WorldPositionMatrix` **i samma köade körning** som skrivningen:

| | `PositionMatrix.P.X` | `World…P.X` före `sim.update()` | efter |
|---|---|---|---|
| samma tick som skrivningen | 1000,0 | **0,0** | 1000,0 |
| ett anrop senare | 1000,0 | 1000,0 | 1000,0 |

Världsmatrisen släpar exakt ett scenuppdatering, och släpet är **borta ett
anrop senare** — pumpen hann ticka emellan. Det är därför fas 8:s 1 mm-prov
såg falska pulser: den läste i samma tick. Provtagaren gör `sim.update()` per
prov och ser rätt värde; en rak `exec` gör det inte och svarar med ett gammalt
läge utan att säga något.

## P15-2 — en orörd komponents driv: GRÖNT, och noll

50 komponenter byggda, ingen rör sig, 60 s i 20 Hz → **1 151 prov, 62 objekt
i scenen** (49 mina i `scene` — den femtionde är rollen och utesluts därför ur
`scene`, 42 §1 — och 13 andras).

| | max | median |
|---|---|---|
| `brus_mm` per objekt | **0,000000** | 0,000000 |
| `vaglangd_mm` | 0,000000 | — |
| `forflyttning_mm` | 0,000000 | — |
| `stilla` | **True för 49 av 49** | |

Brus per objekt och minut: **0,000000 mm**. Nollan är nollan ned till seriens
kvantisering: `SCEN_DECIMALER = 6` i meter, alltså **1 µm**. En orörd
komponent i VC har en exakt konstant matris — det finns ingen fysik och ingen
drift att mäta. Det är talet M-10 ska sätta `ROR_SIG_MM` ur: golvet är
kvantiseringen, inte scenen.

**Bifynd:** ett av de tretton främmande objekten rörde sig — `ST8_Mall`, en
komponent ur en annan agents fas 8-linje i samma delade scen. Ögat såg den
utan att någon bett om det. Det är precis vad `scene` är till för: *"ett
objekt som ingen tänkte på finns ändå i serien när man i efterhand frågar
varför något gick fel."*

## P15-3 — VC:s egen kostnad för hela scenen: GRÖNT, sex rader, inget TAK

8 s per rad, 20 Hz, `scen: "all"`, budget `SCEN_BUDGET_MS = 5,0`:

| byggda | i scenen | i serien | prov | **medel ms/prov** | median | max | gles | TAK |
|---|---|---|---|---|---|---|---|---|
| 10 | 26 | 22 | 161 | 0,416 | 0,0 | 1,0 | 1 | nej |
| 50 | 66 | 62 | 162 | 0,290 | 0,0 | 1,0 | 1 | nej |
| 100 | 116 | 112 | 165 | 0,479 | 0,0 | 1,0 | 1 | nej |
| 200 | 216 | 212 | 169 | 0,722 | 1,0 | 2,0 | 1 | nej |
| 400 | 416 | 412 | 176 | 1,665 | 1,0 | 24,0 | 1 | nej |
| 800 | 816 | 812 | 195 | **3,492** | 3,0 | 26,0 | 1 | nej |

Medelvärdet är summan över alla avläsningar delat med antalet — det enda
talet som överlever klockans grovhet inne i VC:s Python 2.7 (`time.clock`
kvantiserar till ~1 ms; medianen 0,0 vid 10–100 komponenter är den
kvantiseringen, inte en kostnad på noll).

Kostnaden är linjär från 200 uppåt: ≈ **4,3 µs per komponent och prov** i VC
(3,49 ms / 812). Provtagarens egen kostnad utan VC var 2,3 µs (42 §1), så
VC:s `WorldPositionMatrix`-läsning är ungefär **lika dyr som all övrig
bokföring tillsammans** — inte "den tyngre halvan" som 42 §1 gissade, men
hälften. Med 5 ms budget räcker det till ≈ **1 150 komponenter** i full takt;
därefter glesar ögat scenen och säger det (`OVER_BUDGET`). Ingen
`TAK`-händelse under 200 komponenter — protokollets röda utfall — och ingen
över heller.

Max-värdena 24 och 26 ms vid 400 och 800 är enstaka avläsningar; de syns inte
i medianen på fönstret om 8 (`GLES_FONSTER`), så faktorn förblev 1. Det är
hysteresens avsikt.

Provtakten sjönk inte: 161–195 prov på 8 s är 20–24 Hz, och antalet **steg**
med komponenterna (fler avläsningar per sekund vid 800 än vid 10). Det är
pumpens adaptiva paus, inte ögat.

---

## Vad de tre punkterna säger om fasens grind

*"Tidsserie över varje objekt i scenen"*: mätt. 812 objekt i serien vid 812 i
scenen (bryggans egen komponent `VcAssistBridge` räknas med i båda). Alla i
meter, alla med `stilla`/`brus`/`vaglangd`, och ett främmande objekt som
rörde sig blev sett.

## LIMITS

* **En körning, en kväll, en maskin.** Talen i P15-3 har ingen spridning
  mellan körningar. Andra agenter körde på samma dator; VC var bunden till
  `taskset -c 0-11`, klienten inte.
* **Klockan inne i VC kvantiserar till ~1 ms.** Medel ur summan är rätt tal
  för kostnaden; **fördelningen** per avläsning (p95, svans) går inte att
  mäta med den klockan. Max-värdena 24/26 ms kan vara en avläsning på 24 ms
  eller flera på 1 ms som råkade summeras över en tick-gräns — det går inte
  att avgöra.
* **Nollan i P15-2 är nollan ned till 1 µm.** Sub-mikrometerdrift, om VC har
  någon, ligger under kvantiseringen. `ROR_SIG_MM` (M-10) kan sättas mot
  golvet 1 µm; det säger inget om en scen med fysik påslagen.
* **Bara tomma komponenter i P15-2 och P15-3** (utan geometri). Kostnaden för
  `WorldPositionMatrix` beror rimligen inte på geometrin, men det är inte
  mätt; P15-4/5 (M-88) har kroppar med geometri och mäter en annan sak.
* **`uppdatera_fore_last=False`-svepet** (protokollets separata kostnadsmätning
  utan `sim.update()`) är **inte kört**. Andelen av 4,3 µs som är
  `sim.update()` är därför okänd.
* **`ST8_Mall` rörde sig** i en annan agents scen — det är ett bifynd, inte
  en mätning av den scenen. Vad som drev den är inte utrett här.
* **Windows** (fas 13). Allt är mätt under Wine.
