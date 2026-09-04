# M-54 — tolken mot en andra motor, och en grind som sa GODKÄND om kod som inte går att bygga

**Datum:** 2026-09-04 · STruC++ 0.6.6 (CLI, `--build`) · vår egen `st/tolk.py`
**Körs av:** `tests/protocol/kor_m54_tolk_mot_strucpp.py`
**Svarar på:** frågan `tolk.py` ställer i sin egen docstring och som `M-45 §8`
lämnade öppen — *två motorer på samma facit kan drifta isär, och det ska mätas.*

## Varför mätningen behövdes

Bänkens facit döms av vår egen ST-tolk. Har tolken fel om semantiken har facit
fel, och då mäter bänken **vår egen missuppfattning med stor precision**. Ett
facit som döms av samma motor som producerade det är tautologiskt.

Kedjan till OpenPLC kräver ett npm-paket som inte längre finns på maskinen
(M-48). Men STruC++ kan bygga ett ST-program till en **körbar med REPL**:

```
strucpp <in.st> -o <ut.cpp> --build
```

Den tar `set <PROGRAM>.<VAR> <värde>`, `run <N>` och `get`, och kör med **20 ms
cykel — samma period som `tolk.SCAN_MS`**. Perioden avläses ur binärens egen
startrad och **jämförs** mot tolkens; skiljer de sig avbryts jämförelsen, för
två spår på olika tidsrutnät mäter rutnätet och inte semantiken.

## Utfallet

**10 av 10 fall överens**, efter en rättelse som beskrivs nedan.

| Fall | Vad det provar |
|---|---|
| TON fördröjer och håller | timern slår om på exakt femte scan (100 ms / 20 ms) |
| TOF håller kvar | efterfördröjningen |
| R_TRIG bara ett scan | flanken är ett scan bred, inte två |
| F_TRIG på fallande | |
| CTU räknar flanker | räknaren räknar flanker och nollställs |
| latch med SR och kvittens | dominans och kvittering |
| IF, CASE och räknare | sekvensen genom en tillståndsvariabel |
| **TON som nollställs av sitt eget villkor** | fas 7:s T4 — båda motorerna visar att den aldrig faller |
| heltalsaritmetik och jämförelser | prioritet, heltalsdivision |
| REAL och blandad aritmetik | |

Spåren körs i **en** process. En binär per steg hade nollställt
funktionsblockens minne mellan stegen, och då hade varje timer och varje flank
mätt fel sak.

## Fyndet: `RESET` — tre lager, tre olika svar

CTU-fallet skrevs först med `c(CU := i, RESET := r, PV := 3)`. Det avslöjade
att de tre lagren gav tre olika svar på samma text:

| Lager | Svar på `RESET` |
|---|---|
| **vår tolk** | **accepterade tyst** — läser nollställningen ur `R`, så reset föll bort och räknaren räknade vidare |
| **STruC++, enbart översättning** | **utgångskod 0**, texten *"Compilation successful!"* |
| **STruC++, fullt bygge** | **utgångskod 1**: `class strucpp::CTU has no member named RESET` |

IEC 61131-3 kallar CTU:s nollställning `R`. `RESET` är fel namn, och ingen
runtime har den semantik tolken visade.

Två saker faller ut, och båda är lagade.

### 1. Tolken avvisar nu okända ingångar

Ett argument som ingen läser är inte en detalj — det är ett **tyst bortfall
mitt i det facit ska mäta**. Tolken bär nu ingångslistorna för alla tio
standardblocken och fäller på ett namn som inte står där.

Trasig fixtur: `tests/enhet/test_tolk.py`, `RESET` avvisas, `R` går igenom och
nollställer på riktigt.

### 2. Grind 1 bygger nu fullt, och skälet är mätt

`paket.granska_kompilering` körde bara översättningen. Den hade alltså sagt
**GODKÄND** om ett program som ingen PLC kan köra.

Kostnaden för att göra grinden ärlig, tre körningar vardera:

| | körning 1 | 2 | 3 |
|---|---|---|---|
| enbart översättning | 0,32 s | 0,34 s | 0,32 s |
| **fullt bygge** | 1,97 s | 2,02 s | 1,99 s |

Sex gånger dyrare. **1,7 sekunder** extra per kandidat är billigare än ett
reparationsvarv mot en modell, och oändligt mycket billigare än ett falskt
godkänt program. `fullt_bygge=True` är därför standard.

## Vad detta INTE bevisar

* **Det är inte OpenPLC.** Oraklet är STruC++:s egen runtime. Två motorer som
  är överens kan båda skilja sig från OpenPLC v4, och den jämförelsen kräver
  npm-paketet som saknas (M-48, fas 12).
* **Tio konstruktioner är inte ST.** Svepet täcker det bankens facit lutar sig
  mot i dag. Det säger ingenting om det som inte provades.
* **Ingenting om drift.** Scancykelns kanter i en riktig anläggning,
  fältbussjitter och degraderade lägen finns inte i någon av motorerna.

## Sidoanmärkning som hör till fas 12

Att en fullt giltig ST-text kan översättas med utgångskod 0 och sedan inte gå
att bygga är en egenskap hos STruC++ 0.6.6, inte hos oss. Den är värd att bära
med sig: **kompilatorns "Compilation successful!" är ett svar på en annan fråga
än den vi ställer.**
