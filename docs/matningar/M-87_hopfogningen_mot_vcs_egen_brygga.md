# M-87 — hopfogningen mot VC:s egen brygga: två klockor, tre fel, ett tak som inte höll

**Datum:** 2026-09-05 · Linux 6.8 · VC Premium 4.10 under Wine 11.16, **headless
`:99`**, testprefixet `~/.wine-vc-test` (verifierat ur `/proc/<pid>/environ`)
**Mätt av:** `tests/protocol/kor_fas15_hopfogning.py` (L3, mot en körande VC) och
`tests/enhet/test_hopfogningens_tak.py` (L1, mot M-42:s rigg)
**Rådata:** en körning, 30 s klockmätning, 150 varv per ålderssteg, 30 s
upplösningskörning. Kommandot står i filens docstring.
**Fas:** 15 (`docs/spec/70_faser.md`) — punkt P15-6 i
`tests/protocol/fas15_ogat_pa_djupet.md`.

Fasens grind kräver att *"hopfogningens osäkerhet är mätt, inte antagen"*.
M-42 och M-65 mätte den mot en **attrapprigg**. M-65 skrev själv ut hålet:
*"Hopfogningen är mätt mot M-42:s rigg, inte mot VC:s brygga."* Den här
mätningen stänger det, och fann att taket inte höll.

---

## §0 Först: VC körde inte repots kod

Den första körningen gav en serie helt **utan** `plc_hopfogning_s`. Talet fanns
i repots `pump.py` sedan M-65. Installationen i VC:s användarmapp låg kvar från
2026-09-04 22:27, och **5 av 11 filer var äldre än repot**:

| Fil | Samma som repot |
|---|---|
| `pump.py`, `oga_provtagning.py`, `oga_harledning.py`, `oga_analys.py`, `oga_kontrakt.py` | **nej** |
| `bridge_cmd.py`, `formaga.py`, `plats.py`, `protokoll.py`, `skrivgrind.py`, `__init__.py` | ja |

Ingenting kraschade. Ingen rad saknades i protokollet. Mätningen hade fått ett
tal — talet för den gamla koden. `install/installera.py verifiera` kunde redan
svara på frågan (`samma som repots kalla: NEJ`); den var bara aldrig ställd före
en mätning.

Därför finns nu `tests/protocol/stod/installationsgrind.py`, och varje
L3-körning börjar med **STEG 0**: kör VC repots kod? Svaret ligger i utdatans
`installationen_ar_repots`, och körningen vägrar starta utan `--anda`.

---

## §1 De två klockorna, mätta i en körande VC

Kopplarens ålder mäts i **väggklocka**. Ögats serie är stämplad i
**simuleringstid**. Kvoten mellan dem är inte en etta av självklarhet; den mäts
på två oberoende sätt i samma körning:

| Storhet | Hur den mäts | Värde |
|---|---|---|
| lång kvot | minsta kvadrat över 742 klämda simtidsavläsningar under 30 s | **1,00000** simsekunder per väggsekund |
| regressionens residual | punkternas avstånd till sin egen linje | median 2,15 ms, p95 4,91, max 7,65 |
| pumpens `takt()` | pumpens egen kvot över 20 slag — **den som räknar om åldern** | median 0,9896 · p05 0,9223 · p95 1,0920 · **min 0,8636 · max 1,1585** |

Klockorna går alltså lika fort. **Pumpens mätning av det gör de inte.**
`takt()` svängde ±13 % kring en sanning som låg still på 1,000, och i en
tidigare körning nådde den 1,397 och 0,754. Enstaka utslag upp mot 2,6 syntes i
felutslagen (§3).

Orsaken är fönstrets längd. `TAKTFONSTER = 20` slag; med aktiv pump slår den var
5:e ms, så fönstret spänner ~0,1 s. Simuleringstiden går dessutom i **steg om
5 ms** — mätt separat vid 0,53 ms minsta avläsningsintervall; de distinkta
sprången var 0,005, 0,010, 0,015, 0,030, 0,040 s och aldrig något däremellan.
Kvoten läser bara fönstrets två ändpunkter, och ligger de på var sin sida av ett
steg är kvoten fel med steget delat med fönstrets väggspann — 0,005/0,1 = **5 %
av ett enda steg**, innan jittret räknats.

## §2 Vägen: tur och retur genom bryggan

150 varv, med ögat provtagande:

| Anrop | median | p95 | max |
|---|---|---|---|
| `ping` | 9,55 ms | 14,38 | 17,74 |
| `plc_in` | 10,18 ms | 14,61 | 20,35 |

M-03 mätte VC:s brygga till 9,9 ms; det stämmer. `HOPFOGNING_PRIOR_S` = 13,45 ms
(M-03:s värsta tur och retur) ligger mellan median och max, alltså rimligt som
prior — men priorn behövs inte längre i en VC-körning: seriens `hopfogning_kalla`
blev **RUN** i 604 av 604 rader med PLC-värden.

## §3 d — hopfogningsfelet, mätt mot VC

`d = (ögats stämpel) − (den sanna simuleringstiden i läsögonblicket)`.

Den sanna tiden är inte känd exakt. Den **kläms** mellan två simtidsavläsningar,
en före och en efter läsögonblicket. Simuleringstiden växer monotont, så klämman
är en **hård gräns** — den kräver inget antagande. Bredden (15–25 ms) är kartans
egen osäkerhet och redovisas i varje rad. Regressionen ur §1 ger en tätare
punktskattning, till priset av ett antagande (att simuleringstiden går rakt mot
väggklockan). **Båda redovisas.**

Åldern sveps, för stämpeln är `simtid − ålder · takt` och ett fel i takten
skalar rakt med åldern. Kopplaren är den riktiga `Ogonkoppling`, inte en
efterlikning: det är dess `rtt_tak()` som både kompenserar åldern och blir
seriens tak.

**FÖRE åtgärden** (taket = kopplarens tur och retur, som M-42/M-65 satte det):

| ålder | d median (klämmans mitt) | takets median | över taket, **klämman** | över taket, regressionen | värsta överskridande |
|---|---|---|---|---|---|
| 0 ms | −12,9 ms | 13,50 ms | 0,0 % | 8,7 % | +15,0 ms |
| 25 ms | −9,0 | 13,14 | 0,0 % | 14,7 % | +61,6 |
| 50 ms | −10,4 | 14,37 | **2,7 %** | 32,0 % | +51,2 |
| 100 ms | −9,9 | 13,99 | **8,0 %** | 31,3 % | +88,1 |
| 200 ms | −5,9 | 14,05 | **8,7 %** | 30,7 % | +155,5 |
| 400 ms | −8,4 | 14,22 | **30,7 %** | 54,7 % | **+647,0** |

*"Över taket, klämman"* räknar bara varv där **hela** klämman ligger utanför
taket — en klämma som skär taket är inget bevis åt något håll och får inte
räknas som ett. Det är det antagandefria talet.

Takttermens storlek, räknad per varv ur svarets egen `takt` mot den långa
kvoten, steg linjärt med åldern precis som förutsagt: p95 1,06 ms vid ålder 0,
32,1 ms vid 400 ms, med enstaka utslag på 654 ms (`takt` ≈ 2,6).

**Slutsats:** taket bar **vägen**, inte **klockan**. Det är två storheter, och
den ena skalar med åldern medan den andra inte gör det. En kopplare med M-39:s
89 ms varv har en ålder på tiondels sekunden, inte på noll.

### Det tredje felet: taket är en backspegel

`rtt_tak()` är max av de **åtta föregående** turerna. Blir just den här rundan
längre än alla åtta bär taket inte sin egen runda. Med en **styrd hicka** i
riggen (pumpen sover 80 ms vart tionde slag) blev det mätbart i stället för
sällsynt:

| | |
|---|---|
| varv över det **skickade** taket | **10,0 %** |
| värsta överskridande | **+69,5 ms** |
| riktning | **positiv** — ögat trodde värdet var **färskare** än det var |
| varv över max(skickat tak, rundans egen tur och retur) | **0,0 %** |

Det förklarar M-65:s dokumenterade slumpfallning
(`test_hopfogningens_tak_bar_felet_ocksa_vid_VCs_tur_och_retur[0.005]`, *"orsaken
är okänd"*). Den återskapades här: 12 riktade riggkörningar à 200 varv gav
överskridanden i 2 av 12 (1–2 varv av 200, +1,1 och +3,3 ms) och 0 av 16 i nästa
omgång. En sällsynt slumpfallning är värre än en vanlig — den lär den som ser
den att bortse från provet. Nu är den styrd, och den har ett prov.

## §4 Åtgärden: taket får tre termer i stället för en

Alla tre är **mätta**, ingen är antagen.

| Term | Vad den bär | Var den mäts |
|---|---|---|
| `vagen_s` | kopplarens tur och retur | `Ogonkoppling.rtt_tak()`, oförändrad (M-42) |
| `klockan_s` | `alder · takt_spridning` | `pump.Brygga.takt_spridning()`, **ny** |
| rättelsen | rundans **egen** tur och retur, skickad i efterhand | `Ogonkoppling.skjut_in` → `Plckalla.hoj_hopfogning`, **ny** |

`takt_spridning()` mäter takten mot sig själv på två sätt, och det största
gäller:

1. **spridningen mellan delfönster** — fönstret delas i fyra, var och en är en
   egen mätning av samma kvot, och det de inte är överens om är vad mätningen
   inte vet. Ett delfönster är kortare och därför brusigare än helheten, så
   max-avvikelsen övertäcker helhetens eget fel. Den termen ser **slumpen**.
2. **hur krokigt fönstret är** — punkternas största avvikelse från fönstrets
   egen räta linje, gånger två, delat med väggspannet. Simuleringstiden går i
   steg (§1) och kvoten läser bara ändpunkterna; ligger de på var sin sida av ett
   steg är felet **systematiskt**, och alla fyra delfönster kan vara helt överens
   och ändå ligga fel åt samma håll. Den termen ser **kvantiseringen**.

Mätt i samma VC-körning, 742 avläsningar:

| | median | p95 | max |
|---|---|---|---|
| `takt_spridning` | 0,2309 | 0,6070 | 1,3954 |
| taktens **verkliga** avstånd till den långa kvoten | — | 0,1047 | 0,1585 |

Spridningen övertäcker alltså det verkliga felet med ungefär 2,2× vid p95. Det
är avsiktligt och åt rätt håll: en för lös gräns gör en fasdom mer INCONCLUSIVE
än den behöver vara, en för tät gör den till ett falskt PASS.

Rättelsen är en begäran **utan värden men med ett tak**. Taket får bara växa —
en snabb runda som sänkte det hade tvättat bort en långsam rundas osäkerhet, och
en osäkerhet som går att tvätta bort är ingen osäkerhet.

**EFTER åtgärden**, samma körning, samma metod:

| ålder | takets median | över taket, **klämman** | över taket, regressionen |
|---|---|---|---|
| 0 ms | 17,65 ms | **0,0 %** | 2,0 % |
| 25 ms | 23,26 | **0,0 %** | 0,7 % |
| 50 ms | 29,35 | **0,0 %** | 0,0 % |
| 100 ms | 39,11 | **0,0 %** | 0,0 % |
| 200 ms | 70,35 | **0,0 %** | 0,0 % |
| 400 ms | 112,14 | **0,0 %** | 0,0 % |

30,7 % → 0,0 % vid 400 ms ålder. I en av tre efterkörningar stod ett enda varv
av 150 kvar utanför vid 400 ms (0,7 %, d ≈ −0,9 s vid en takt som tappade
fotfästet helt). Taket är alltså inte bevisat täckande — det är **mätt
täckande i 899 av 900 varv**, och det är skillnad.

## §5 Upplösningen hör till FLANKEN, inte till körningen

`upplosning()` tar **max** över raderna. Det är rätt tal för `LIMITS`-raden —
den ska säga hur illa det stod till som värst — och fel tal för en dom. Med de
nya termerna svängde takets värde inom **samma körning** från 17 ms till
1 829 ms, och seriens max hade då gjort varenda fasdom obestämbar. Ögat hade
blivit blint av att bli ärligt.

`plcflanker()` bär därför radens eget `plc_hopfogning_s`, och `fasforhallande()`
dömer varje flank mot `max(las_s, prov_s + flankens eget tak)`. De två talen bär
olika namn i utdatan: `LIMITS RESOLUTION ... join=/phase=` är körningens värsta,
`PHASE ... res=` är flankens egen.

Trasig fixtur:
`test_ett_enda_daligt_ogonblick_gor_inte_hela_korningen_obestambar` — en serie
där en rad bär 1 000 ms och flankens rad 10 ms får **OK** mot ett krav på
100 ms; flyttas det dåliga ögonblicket till flankens egen rad blir svaret
**INCONCLUSIVE** med res > 1 000 ms.

## §6 Upplösningen ur en riktig körning

30 s, ögat i 20 Hz, kopplare med 89 ms varv (M-39:s uppmätta OpenPLC-varv,
efterliknat — se LIMITS):

| | |
|---|---|
| prov | 605 |
| inskott | 337 |
| rader med PLC-värde | 604 |
| rader märkta gamla | 0 |
| rader med **mätt** tak (`RUN`, inte `PRIOR`) | **604 av 604** |
| PLC-värdets ålder i serien | median 60,2 ms, max 208,6 ms |
| `prov_s` | 50,0 ms |
| `las_s` (mätt ur seriens egna lästider) | 90,1 ms |
| `hopfogning_s` (körningens värsta) | 1 828,6 ms |
| `fas_s` = max(L, S+J) | 1 878,6 ms |

P15-6:s gröna svar — `hopfogning_kalla == "RUN"` — är alltså uppnått: taket kom
hela vägen genom `plc_in` och ligger i varje rad. `PRIOR` (rött enligt
protokollet) förekom inte en enda gång.

---

## Vad som INTE är mätt

* **Ingen riktig PLC.** Kopplarvarvet på 89 ms är M-39:s uppmätta OpenPLC-varv,
  **efterliknat** med en väntesats. Ingen OPC UA-läsning gjordes. `las_s` mätt
  till 90,1 ms är alltså efterliknelsens varv, inte en PLC:s.
* **PLC:ns egen skanfördröjning (40 ms, M-20)** ligger **före** kopplarens
  läsning och ingår inte i något av talen här. Rapporten skriver det som
  `EXCLUDED plc_scan 40.0ms`. Fältbussens väg mellan PLC och I/O är inte heller
  mätt.
* **Kartans egen osäkerhet är 15–25 ms** och den går inte att göra smalare med
  den här metoden: att veta simuleringstiden vid ett väggögonblick kostar en
  tur och retur. Klämmans siffror är därför trubbiga; regressionens är tätare
  men bygger på att simuleringstiden går rakt mot väggklockan.
* **Regressionen antar att avläsningen sker mitt i sin tur och retur.** Sker
  den systematiskt senare är hela kartan förskjuten med upp till en halv tur
  och retur (~5 ms). Det går inte att avgöra utan en klocka båda sidor delar.
  Klämman är fri från det antagandet; de två skattningarna skiljer sig med
  4–5 ms, vilket är i den storleksordningen.
* **Taket är inte bevisat täckande.** Ett varv av 900 låg utanför vid 400 ms
  ålder. Vad som hände i just det varvet är inte utrett.
* **Spridningens övertäckning (2,2× vid p95) är mätt i en driftpunkt**, med
  ögat provtagande i 20 Hz och pumpen i aktiv regim. Med `sim.run()` (M-08:
  2000× väggklockan) är kvoten en helt annan storhet, och spridningen är inte
  mätt där.
* **Rättelsen kan komma för sent.** Den skickas efter att värdet stämplats och
  tar en tur och retur (~10 ms). Provtagaren går i 20 Hz, så en rad som
  provtas i mellanrummet bär det för lilla taket. Hur ofta det händer är inte
  mätt.
* **Bara en maskin, en kväll, en scen.** Turen och returen mättes medan andra
  agenter körde på samma dator; `taskset -c 0-11` band VC men inte klienten.
* **Windows** (fas 13).
* **Flera kopplare mot samma öga** — M-42:s regel gäller fortfarande: sista
  inskottet vinner.
