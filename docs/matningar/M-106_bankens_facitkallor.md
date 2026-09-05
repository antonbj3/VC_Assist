# M-106 — bankens facitkällor, mätta post för post

**Datum:** 2026-09-05
**Kontrakt:** `docs/spec/85_bankkontraktet.md` §2
**Grind:** `tests/protocol/kor_bankens_facit.py`
**beskriver:** `bank/uppgifter/*.json`, `bank/katalog_index.json`,
`tests/protocol/kor_bankens_facit.py`

## Frågan

Banken bar **51** uppgifter, varav **fyra** hade `facit_spar`. En uppgift utan
spårfacit går inte att döma mekaniskt idag — den är en prompt, inte en bänkpost.

Och ett spårfacit vars tal räknats fram av koden som ska dömas mäter ingenting.
`BENCH-4` stod grön i månader mot ett tautologiskt facit; talet var perfekt.

Två frågor:

1. Hur många uppgifter kan få ett spårfacit vars härkomst pekar **utanför**
   repots egen kod — och vad blir källan, post för post?
2. Går regeln att mekanisera?

## LIMITS

* **Tak: se avsnittet "Vad som INTE är mätt".** Talen nedan är räknade och
  citerade, inte körda mot en verklig anläggning. Ingen uppgift i banken är
  körd i Visual Components, så ögonfacit i `expect` är fortfarande oprövat.
* Spårfacit döms av `bank/domare.py` genom vår egen ST-tolk. Tolken är **inte**
  OpenPLC: samma facit genom OpenPLC kan ge ett annat svar, och den skillnaden
  är inte mätt (den står öppen sedan M-45).
* Paragrafnumren nedan är verifierade mot standardorganens egna
  innehållsförteckningar och mot fulltextadoptioner. **Kravtexterna** är i flera
  fall inte lästa i full text — där det gäller står det i uppgiftens eget
  `standard`-fält, ordagrant.
* **Referenslösningarna är inte prövade mot grind 1–4.** MÄTT 2026-09-05:
  samtliga 22 referenser fälls av `granska_station` på `ODEKLARERAD`, och det
  gäller lika mycket de fyra som fanns före det här arbetet. Skälet är att en
  `facit_spar.referens` skrivs för tolken, som får signalkartan separat, medan
  stationsgrinden väntar sig skelettet med sina deklarationer. Referensen är
  alltså bevisad **uppfyllbar**, inte bevisad **byggbar**: ingen av dem har gått
  genom STruC++. Att köra referenserna genom skelettet är en öppen punkt.
* **Facit och referens är skrivna av samma sorts modell som ska dömas.** Talen
  kommer utifrån — ur en paragraf, ett datablad eller en räkning ur scenens egna
  mått — men sekvenserna, invarianterna och flankräkningarna är formulerade av
  en språkmodell. Ett facit en modell inte kunde uttrycka finns inte i banken,
  och den snedvridningen är inte mätt.

---

## 1. Fyndet som kom först: de fyra befintliga facit sa inte varifrån de kom

Alla fyra spårfacit i banken bar `harkomst = "M-45"`. M-45 är mätningen av
bankens **täckning** — inte källan till ett enda tal. Grinden fällde alla fyra
vid första körningen.

Och en av dem citerade fel paragraf. `L-05` sa *"håll-för-att-köra enligt
IEC 60204-1 kapitel 9.2.5"*. Det stämmer i ingen utgåva:

| Utgåva | Var håll-för-att-köra faktiskt står |
|---|---|
| IEC 60204-1:**2005** | **9.2.6.1**, under 9.2.6 "Other control functions" |
| IEC 60204-1:**2016** | **9.2.3.7 "Hold-to-run control"** |

Hela 9.2.6 slogs 2016 in i 9.2.3 med rak förskjutning: 9.2.6.1→9.2.3.7,
9.2.6.2→9.2.3.8 (tvåhandsdon), 9.2.6.3→9.2.3.9 (enabling), 9.2.6.4→9.2.3.10.
Förskjutningen är bekräftad mot standardens egen tabell F.1.

Det är precis den sortens slarv som operatörens krav siktar på: *ett bart
standardnummer säger inte vad facit lutar sig mot, och ett paragrafnummer man
minns fel är värre än inget.*

Samma genomgång flyttade tre andra påståenden:

* `S-05` hänvisade till *"övergångsmatrisen i TR88.00.02 kapitel 6.1"*. I
  ANSI/ISA-TR88.00.02-**2022** ligger tillstånden i **4.3 "Defined states"**
  (tabell 1 och 2) och övergångarna i **4.5 "State transitions and state
  commands"**; 6.1 är *"Production Mode example"*. Numreringen **1..17** och
  kommandonumren **1..9** kunde **inte** verifieras mot primärkällan — ISA:s
  publika utdrag bär bara innehållsförteckningen. Uppgiften är skriven mot den
  numreringen, och facit säger nu rakt ut att den är obekräftad.
* `H-04` lutade sig på "bankens egen konvention" för handskakningen. Det står
  kvar — men nu uttryckligen som *bankens egen*, inte som en standard, och de
  paragrafer som faktiskt bär (manuell återställning, återstartsspärr i en
  robotcell) är utsatta.
* `T-07` hade tidsgränsen 2,0 s utan att säga att den är **deklarerad**. Den är
  det, och det står nu i härkomsten.

---

## 2. Grinden: `tests/protocol/kor_bankens_facit.py`

Sex frågor per uppgift, alla mekaniska:

| Kod | Vad den fäller |
|---|---|
| `HARKOMST_UTAN_KLASS` | härkomsten namnger ingen källklass (STANDARD, RAKNAD, DATABLAD, SPAR) |
| `STANDARD_UTAN_PARAGRAF` | kallar sig STANDARD men citerar inget paragrafnummer |
| `RAKNING_UTAN_RAKNING` | kallar sig RAKNAD men visar ingen räkning |
| `HARKOMST_UTAN_MATNING` / `HARKOMST_DOD_MATNING` | ingen mätning namngiven, eller en som inte finns på disk |
| `STANDARD_UTAN_UTGIVARE` | citerar en paragraf men ingen utgivare — numret går inte att slå upp |
| `OVERIFIERAD_PARAGRAF` | citerar en paragraf som inte står i det här dokumentets tabeller |
| `FACIT_UR_EGEN_KOD` | härkomsten pekar in i `svc/`, `bank/domare.py`, `tests/`, `plc/`, `st/tolk.py` |
| `KARNUTGANG_UTAN_SPAR` | en kärnutgång som inget krav, ingen invariant och ingen flankräkning rör |
| `KARNUTGANG_EJ_UTSIGNAL`, `SCENARIO_OKAND_SIGNAL`, `SPAR_OKAND_SIGNAL` | signalkartan går inte ihop med `core_outputs`, scenarierna eller spåret |
| `ANTAGANDE_UTAN_MOTIV` | ett antagande utan skäl |
| `TAL_UTAN_ENHET` | ett tal med enhet i namnet men utan enhet i värdet |
| `REFERENS_FALLER`, `MOTBEVIS_GAR_IGENOM`, `MOTBEVIS_FEL_BRIST` | facit går inte att uppfylla, eller inget motbevis faller på det det namnger |

**Sju trasiga fixturer** körs sist och måste falla. Utan dem är grinden en
förhoppning som fått ett filnamn.

`OVERIFIERAD_PARAGRAF` läser sin lista ur **det här dokumentets egna tabeller**,
inte ur en kopia i koden. Det är samma val som `bank/schema.py` gör när den
läser felklasserna ur specen: en kopia kan drifta från mätningen utan att någon
märker det. Vill man citera en ny paragraf måste man alltså först slå upp den
och skriva in den här.

### Grindens egen storhet, mätt

| Kontroll | Fällde vid första körningen |
|---|---|
| `HARKOMST_UTAN_KLASS` | **4 av 4** befintliga spårfacit |
| `TAL_UTAN_ENHET` | **0 av 139** antaganden |
| `KARNUTGANG_UTAN_SPAR` | **0 av 4** |
| `OVERIFIERAD_PARAGRAF` | **2 uppgifter** (`T-01`, `T-02`: "IEC 60204-1:2016 9.2.4", en paragraf som inte finns) |

Enhetsregeln fällde alltså ingenting den dagen den skrevs. Det står här därför
att en grind som inte mäter sin egen storhet slutar mäta: regeln är
framåtriktad, och M-85 är skälet till att den finns — VC:s egna komponentfiler
deklarerar `MaxPayload` **utan enhet** i 2 986 komponenter, 628 av dem med
värdet `0`, och bara 14 % av 82 383 egenskaper säger vilken storhet de bär.

En första version av regeln fällde tre värden av formen `"grind 2"` — den
räknade bara ord *efter* talet. Det är en grind som fyrar på rätt sak av fel
skäl, och den räknar nu ord på båda sidor om talet.

---

## 3. Facitkällan per uppgift

<!-- FYLLS I NÄR ALLA UPPGIFTER ÄR KLARA -->

---

## 4. Räkningarna, så de går att följa

Varje rad är räknad ur scenens egna mått. Talen står också i uppgifternas
`facit_spar.harkomst`, så en läsare kan följa dem utan att gå hit.

| Uppgift | Storhet | Räkningen | Utfall |
|---|---|---|---|
| `P-06`, `C-06` | navets massa | V = π/4 × 0,090² × 0,060 = 3,817·10⁻⁴ m³; × 7850 kg/m³ | **3,0 kg** |
| `P-06` | takt, en maskin | 95,0 s skärtid + 42,0 s betjäning | **137,0 s**, 26,3 st/h |
| `C-06` | takt, två maskiner | 137,0/2 = 68,5 s; 3600/68,5 | **52,6 st/h**, robot 61 % |
| `P-07` | plåtämnets massa | 0,250 × 0,180 × 0,002 m³ × 7850 kg/m³ | **0,71 kg** |
| `P-07` | säkerhetsavstånd | C = 8(30−14) = 128; T = 20+40+15+275 ms = 0,350 s; K=2000 → 828 mm > 500 → K=1600 → 1600×0,350+128 | **688 mm** |
| `P-07` | avstånd vid trög broms | 1600 × (0,020+0,040+0,015+0,320) + 128 | **760 mm** > 688 |
| `A-07` | konsolens massa | (0,30×0,20 + 0,30×0,08) m² × 0,006 m × 7850 kg/m³ | **4,0 kg** |
| `A-07` | bågtid | 4 fogar × 120 mm = 480 mm; 480/8 mm/s | **60,0 s** |
| `A-07` | cykel | 60,0 + 4×2,0 + 4×(0,8+1,5) + 4,0 | **81,2 s** av 85,0 |
| `A-08` | limflöde | A = π/4 × 3,0² = 7,0686 mm²; × 120 mm/s | **50,9 cm³/min** |
| `A-08` | strängtid och volym | 2(220+160) = 760 mm; 760/120; 760 × 7,0686 | **6,33 s**, 5,37 cm³ |
| `H-05` | överföringstid | 1000 mm / 400 mm/s | **2,5 s**, vakt 4,0 s |
| `S-06` | läckflöde vid gränsen | q = ΔP·V/Δt = 1,5 × 0,45 / 10,0 = 0,0675 mbar·l/s; × 59,22 | **4,0 cm³/min** |
| `S-06` | husets massa | 2(0,18×0,12 + 0,18×0,095 + 0,12×0,095) = 0,1002 m²; × 0,004 m × 2700 kg/m³ | **1,08 kg** + flänsar ≈ 1,35 kg |
| `S-07` | kartongdelning | 0,5 m/s ÷ (30/60 per s) | **1,00 m**, 2,0 s/kartong |
| `T-08` | uppehållstid i ugn | 12,0 m / 0,010 m/s | **1200 s = 20,0 min** |
| `T-08` | snabbaste tillåtna kedja | 12,0 m / (15 × 60 s) | **0,0133 m/s** |
| `T-09` | hissens restid | v²/2a = 0,32 m i vardera änden; 2×(0,8/1,0) + (3,6−0,64)/0,8 | **5,30 s**, vakt 7,0 s |
| `L-01` | lagermönster | 2×400 = 800 mm; 4×300 = 1200 mm; 8×0,40×0,30 = 0,96 m² = pallens area | **8 kolli**, 44,0 s/lager |
| `L-06` | kartongmönster | 4×95 = 380 ≤ 396; 3×95 = 285 ≤ 296 | **12 burkar**, 6 cykler à 4,0 s |
| `L-07` | filmvarv | stigning 500 × (1−0,5) = 250 mm; 1544/250 = 6,18 → 7 upp + 7 ned + 3 + 2 = 19 varv; 19/12 min | **95,0 s** |
| `T-01` | uppehåll mot gångtid | 120 mm / 500 mm/s = 0,24 s mot uppehållet 0,40 s | **0,16 s marginal** |
| `T-02` | cykelns delar | 0,35 s index + 0,90 s förslutning + 0,35 s hantering | **1,60 s**, 37,5/min |
| `T-04` | buffertlängd | 12 × 600 mm = 7200 mm; 7,2/0,4 m/s | **18,0 s**, 450/h vid 8,0 s |
| `T-05` | kortets passage | 233 mm / 350 mm/s | **0,666 s** |
| `S-01` | förhållning | 400/350 = 1,143 s; − 0,4 s slag = 0,743 s = 260 mm; 400/350 platser | **två besked i registret** |
| `A-03` | linans takt | max(26,0; 31,0) = 31,0 s; 3600/31,0 | **116,1 st/h**, väntan 5,0 s |
| `C-04` | säkert läge | 40 ms PLC + 25 ms relä + 120 ms grindslag = 185 ms mot kravet 300 ms | **115 ms marginal** |
| `H-01` | modulens passage | 180 mm / 300 mm/s | **0,60 s** |
| `P-03` | uttagets andel | 4,5 s av 28,0 s; kylning 11–14 s av 28,0 s | **16 %**, 39–50 % |

---

## 5. Standardparagraferna, och vad som INTE gick att verifiera

Paragrafnumren nedan är slagna upp mot standardorganens egna
innehållsförteckningsutdrag, mot IDT-adoptioner med öppen fulltext (JIS, EN) och
mot tillverkarvitböcker som citerar ordagrant. Där bara **numret** är bekräftat
och inte kravtexten står det, och det står också i uppgiftens eget
`standard`-fält — inte bara här.

| Standard | Paragraf | Rubrik | Används av |
|---|---|---|---|
| IEC 60204-1:2016 | 9.2.3.7 | "Hold-to-run control" | `L-05` |
| IEC 60204-1:2016 | 9.2.3.4.2 | "Emergency stop" | alla |
| IEC 60204-1:2016 | 9.2.2 | "Categories of stop functions" | `C-04` |
| IEC 60204-1:2016 | 9.2.3.5 | "Operating modes" | `L-05`, `C-06` |
| IEC 60204-1:2016 | 7.5 | "Protection against the effects of supply interruption or voltage reduction and subsequent restoration" | `C-04`, `T-07` |
| ISO 13850:2015 | 4.1.4 | "Disengagement (e.g. unlatching) of the emergency stop device" | flera |
| ISO 13855:2010 | 5.2 | "Minimum distance" (S = K·T + C) | `P-07` |
| ISO 13855:2010 | 6.2 / 6.2.3.1 | "Detection zone orthogonal to the direction of approach" / K- och C-värdena | `P-07` |
| IEC 62046:2018 | 5.7 | "Muting" | `P-07` |
| IEC 62046:2018 | 5.7.1 | "General" | `P-07` |
| IEC 62046:2018 | 5.7.2 | "Muting to allow access by persons" | `P-07` |
| IEC 62046:2018 | 5.7.3 | "Muting to allow access by materials" | `P-07` |
| IEC 62046:2018 | 5.7.4 | "Mute dependent override" | `P-07` |
| IEC 61131-3:2013 | 6.6.3.5 | "Standard function blocks" (R_TRIG 6.6.3.5.3 tab. 44, CTU 6.6.3.5.4 tab. 45, TON 6.6.3.5.5 tab. 46) | alla |
| ISO 10218-1:2011 | 5.6.2 | "Reduced speed control operation" (250 mm/s) | `A-07` |
| ISO 10218-2:2011 | 5.10.4.3 | "General requirements for interlocked movable guards" | `A-07` |
| ISO 10218-2:2011 | 5.6.3.4 / 5.6.3.4.2 | "Manual reset, start/restart and unexpected start-up" | `A-07`, `H-04` |
| ISO 14119:2013 | 4.3, 4.3.1 | "Principles of guard interlocking with guard locking" | `P-06` |
| ISO 14119:2013 | 5.7 | "Additional requirements on guard locking devices" | `P-06` |
| ISO 14119:2013 | 8.4 | "Release of guard locking device" | `P-06` |
| ISO 14119:2025 | 5.3, 6.6 | samma krav efter omnumreringen i EN ISO 14119:2025 (4.3→5.3, 5.7→6.6) | `P-06` |
| ISO 14119:2025 | 9.3 | samma krav efter omnumreringen (8.4→9.3) | `P-06` |
| ISO 23125:2015 | 5.2.3 | "Workpiece clamping conditions" | `P-06` |
| ISO 5817:2023 | klausul 5, tabell 1 | "Assessment of imperfections" (nivå B/C/D införs i klausul 1, definieras i 3.1) | `A-07` |
| ISO 3834-2:2021 | 14.3 | "Inspection and testing during welding" | `A-07` |
| ASTM E2930-13(2021) | — | "Standard Practice for Pressure Decay Leak Test Method" | `S-06` |
| GS1 General Specifications R26.0 | 5.12.3, tabell 5-43 | minsta symbolkvalitet 1,5 (C), notation 1.5/10/660 | `S-07` |
| ISO/IEC 15416:2016 | 6.3 | "Expression of symbol grade" (skala 4,0–0,0) | `S-07` |
| VDA 5050 3.0.0 | 6.2.2 tab. 3, 6.2.3.2 tab. 5, 6.6.9 tab. 12 | blockingType, pick/drop, actionStates | `H-05` |
| ISO 3691-4:2023 | 4.5, 4.8.2 | "Load handling", "Detection of persons in the path" | `H-05` |
| EUROMAP 67 v1.11 (2015) | 2.3.1 tab. 1, 2.3.2 tab. 2 | ZA7 "Mould open position", A3/C3 "Mould area free", A6 "Enable mould closure" | `P-03` |
| ANSI/ISA-TR88.00.02-2022 | 4.3, 4.5 | "Defined states", "State transitions and state commands" | `S-05` |
| ANSI/ISA-TR88.00.02-2022 | 6.1, 6.4 | "Production Mode example", "User-defined mode example" | `S-05` |
| TIGER Drylac Series 49, TDS 49-1000 v10-18 | "Cure parameters (substrate temperature versus curing time)" | 180 °C i 15–30 min objekttemperatur | `T-08` |

### Tal i facit som INTE är paragrafhänvisningar

Grinden `OVERIFIERAD_PARAGRAF` slår upp varje `<beteckning> <tal>`-par mot
tabellen ovan. Några tal i bankens facit ser ut som paragrafer utan att vara
det, och de står här så att grinden inte fäller dem — och så att en läsare ser
att de är genomgångna, inte bortglömda.

| Beteckning | Tal | Vad det faktiskt är |
|---|---|---|
| VDA 5050 | 3.0.0 | utgåvans versionsnummer |
| IEC 62046 | 2.0 | Ed. 2.0, utgåvan från 2026 som ersatte 2018 |
| GS1 | 26.0 | Release 26.0 av General Specifications |
| EUROMAP 67 | 1.11 | dokumentversionen, maj 2015 |
| ISA-TR88.00.02 | 88.00.01 | del av titeln ("an implementation example of ANSI/ISA-88.00.01") |
| IEC 60204-1 | 9.2.5, 9.2.6 | de FELAKTIGA numren, citerade i `L-05`:s härkomst just för att rättelsen ska gå att följa |

### Sju saker som INTE är verifierade, och som därför står utskrivna i facit

1. **ISO 3691-4:2023 kravtexterna i 4.5 och 4.8.2.** Klausulnummer och rubriker
   är bekräftade mot ISO:s eget utdrag; själva texterna ligger bakom betalvägg.
   `H-05`:s tidsgräns lutar sig därför på räkningen, inte på paragrafen.
2. **ISO 23125:2015 punkterna b) 2) och b) 3)** inne i 5.2.3. Klausulnumret och
   rubriken är säkra; punkternas ordalydelse är bekräftad via en *modifierad*
   nationell adoption, inte ur ISO-texten.
3. **PackML-numren 1..17 och CntrlCmd 1..9** (`S-05`). Konsekventa i alla
   sekundärkällor, obekräftade mot ISA:s primärtext.
4. **Muting-tidsgränsen** (`P-07`). De 4 s som cirkulerar står bara i den
   informativa bilagan D till IEC 62046:2018 — ingen normativ paragraf hittad.
5. **Bågtidsövervakning som standardkrav** (`A-07`). Strängen "arc time"
   förekommer noll gånger i ISO 3834-2:2021. 14.3 räknar upp ström, bågspänning
   och framföringshastighet — inte tiden — och tillåter dessutom "at suitable
   intervals **or** by continuous monitoring". Bågtidsvakten i `A-07` är
   stationens egen, räknad, och det står i facit.
6. **EUR-pallens måttstandard** (`L-01`). Måtten 1200 × 800 mm är
   standardmått; vilken paragraf som fastställer dem har inte slagits upp här,
   och facit lutar sig på geometrin i stället.
7. **Pressens bromstid 275 ms** (`P-07`). Den är ANTAGEN i katalogindexet.
   ISO 13855 räknar avståndet ur den **uppmätta** stopptiden — ett avstånd
   räknat ur en katalogsiffra är inget säkerhetsavstånd förrän stopptiden är
   uppmätt på den verkliga pressen. Därför finns `ST460_STP_TIME` som signal.

### Två utgåvevarningar som facit bär med sig

* **ISO 13855:2010 är ersatt av ISO 13855:2024**, som är omstrukturerad så att
  varken 5.2, 6.2 eller beteckningen C överlever. `P-07` citerar 2010-utgåvan
  och säger det.
* **IEC 62046:2018 drogs tillbaka 2026-07-28** och ersattes av
  IEC 62046:2026 Ed. 2.0, uttryckligen med omstrukturerade mutingkrav.
  **ISO 14119:2013** numreras om i EN ISO 14119:2025 (4.3→5.3, 5.7→6.6,
  8.4→9.3). **ISO 3691-4:2020 är ersatt av :2023.** Varje citat bär sitt årtal.

