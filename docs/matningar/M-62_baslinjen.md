# M-62 — baslinjen: vad en klassisk generator klarar på samma bank, med samma domare

**Datum:** 2026-09-05 · python 3, **ingen språkmodell**, ingen VC, ingen OpenPLC,
inget nät. STruC++ 0.6.6 kördes för grind 1.

**Frågan:** fas 9 ska rapportera tre tal — klarade första försöket, klarade
efter k varv, fel per klass. `docs/research/R-01_llm_st_och_softplc.md` visade
att inget publicerat tal går att jämföra dem med: ingen har publicerat vår
loop, ingen leverantör publicerar ett korrekthetstal, och varje akademiskt tal
är kompileringsgrad på en annan uppgiftsmängd. `docs/spec/70_faser.md` fas 11
drar slutsatsen: **fas 9:s tal får aldrig publiceras ensamt.** Vad klarar en
regelbaserad generator utan språkmodell på samma uppgifter, dömd av samma
domare?

**Svaret, och det är obekvämt: 4 av 4.** Baslinjen löser varje uppgift i banken
som har ett spårfacit, på första försöket, på under en millisekund per uppgift,
med noll tokens och noll nätanrop. Den kompilerar 37 av 37 genereringsuppgifter med
STruC++ och uppfyller 349 av 349 mekaniska påståenden.

Det talet är inte ett beröm av klassiska metoder. Det är en mätning av **vad
bänken i dag mäter**, och slutsatsen står i avsnitt 6.

---

## 1. Talen

Kört 2026-09-05 med `python3 bank/baslinjebank.py --strucpp <cli> --slinga
--par --tid`. Domarsignatur: scan 20,0 ms, marginal 2 scan, grindar
[statisk_analys, deklarationsmatchning], kod `f265c53e8433`, facit
`6a9efd257e1b`.

### Nämnarna, först

| Storhet | k av n |
|---|---|
| uppgifter i banken | 51 |
| **genereringsuppgifter** (allt utom de 14 medvetet trasiga varianterna) | **37 av 51** |
| uppgifter med spårfacit, alltså dömbara på logiken | **4 av 37** |
| punktkrav | 190 |
| invariantinstanser (18 definitioner, prövade per sekvens) | 149 |
| flankkrav | 10 |
| **mekaniska påståenden totalt** | **349** |
| signaler i genereringsuppgifternas kartor | 390 |

### Huvudtabellen

Tre nivåer av indata, samma generator, samma domare. `spec+driv+las` är samma
generator med de två grindtillfredsställande växlarna på (avsnitt 4).

| nivå | grind 2 | grind 3 | grind 1 (STruC++) | spårfacit | påståenden |
|---|---|---|---|---|---|
| `mager` — bara I/O-listan | 37 av 37 | 0 av 37 | 37 av 37 | **0 av 4** | 277 av 349 |
| `prosa` — I/O-listan + uppgiftstextens egna listor | 37 av 37 | 1 av 37 | 37 av 37 | **0 av 4** | 321 av 349 |
| `spec` — I/O-listan + `control.sequence` och `control.interlocks` | 37 av 37 | 4 av 37 | 37 av 37 | **4 av 4** | **349 av 349** |
| `spec+driv+las` | 37 av 37 | 37 av 37 | 37 av 37 | 4 av 4 | 349 av 349 |
| **golvet:** ett program som styr ingenting | 37 av 37 | 37 av 37 | 37 av 37 | **0 av 4** | **252 av 349** |

**Grind 4, anropsvalidering: 0 av 37 körda.** Baslinjen skriver ingen scenkod,
och en grind som inte kunde köras är aldrig ett godkännande (I3). Talet står
med som noll och inte som frånvaro.

### Per uppgift och påståendeform

| uppgift | nivå | dom | punktkrav | invarianter | flanker |
|---|---|---|---|---|---|
| `T-07` | mager | underkänd | 26 av 39 | 30 av 32 | 2 av 2 |
| `T-07` | prosa | underkänd | 36 av 39 | 32 av 32 | 2 av 2 |
| `T-07` | **spec** | **GODKÄND** | 39 av 39 | 32 av 32 | 2 av 2 |
| `H-04` | mager | underkänd | 24 av 35 | 24 av 30 | 2 av 2 |
| `H-04` | prosa | underkänd | 29 av 35 | 29 av 30 | 2 av 2 |
| `H-04` | **spec** | **GODKÄND** | 35 av 35 | 30 av 30 | 2 av 2 |
| `S-05` | mager | underkänd | 48 av 63 | 32 av 32 | 1 av 3 |
| `S-05` | prosa | underkänd | 58 av 63 | 32 av 32 | 1 av 3 |
| `S-05` | **spec** | **GODKÄND** | 63 av 63 | 32 av 32 | 3 av 3 |
| `L-05` | mager | underkänd | 36 av 53 | 51 av 55 | 1 av 3 |
| `L-05` | prosa | underkänd | 43 av 53 | 55 av 55 | 2 av 3 |
| `L-05` | **spec** | **GODKÄND** | 53 av 53 | 55 av 55 | 3 av 3 |

### Fel per klass

Klassningen är `bank/reparationsbank.py`:s `SPARKLASS` — samma avbildning från
spårfacitkod till felklass som M-52 använder, och den är oförändrad här.

| nivå | `F5` sekvens | `F8` förregling | `F15` flank och latch |
|---|---|---|---|
| `mager` | 4 av 4 | 3 av 4 | 2 av 4 |
| `prosa` | 4 av 4 | 1 av 4 | 2 av 4 |
| `spec` | 0 av 4 | 0 av 4 | 0 av 4 |

`F6` och `F7` förekommer inte, och får inte göra det: sorteringsregel 5 i
`docs/spec/82_felklasser.md` säger att en statisk grind aldrig får fälla på
dem, och spårfacit ligger inte i ögat.

### Kostnad

| Storhet | Värde |
|---|---|
| tokens | 0 |
| nätanrop | 0 |
| genereringstid, nivå `spec` | 20,6 och 35,3 ms för 37 uppgifter i två körningar, **0,6–1,0 ms per uppgift** |
| genereringstid, nivå `mager` | 7,5 och 14,0 ms för 37 uppgifter, 0,2–0,4 ms per uppgift |
| byte-identisk kod vid omkörning | 37 av 37, på varje nivå |

Tidstalen är två körningar på en maskin som samtidigt kör ett skrivbord. De är
en storleksordning och inget precisionstal, och de behöver ingen precision:
de ska ställas mot ett modellanrop som tar sekunder.

---

## 2. Golvet, och varför varje påståendetal måste läsas mot det

`bank/baslinjebank.py:nollprogram` skriver varje utgång till sitt nollvärde en
gång och läser varje ingång en gång. Den styr ingenting alls.

**Den går igenom grind 1, grind 2 och grind 3 på 37 av 37 uppgifter utan en
enda anmärkning** — kompileringen mätt med STruC++ 0.6.6 och `--build`, alltså
inklusive C++-bygget — och den uppfyller **252 av 349** mekaniska påståenden,
72 %.

Skälet är enkelt när man ser det: en stor del av bankens punktkrav är
**negativa**. "Bandet ska stå", "ingenting får vara kommenderat", "ett
återställt nödstopp är ingen startorder". Ett program som aldrig kommenderar
något uppfyller dem alla, av precis fel skäl.

Följden är hård och gäller lika mycket vårt eget kommande tal:

> **En kompileringsgrad mäter inte om koden styr någonting.** Det är R-01:s
> slutsats, och den är nu mätt i vår egen bänk i stället för citerad ur någon
> annans.

Nollprogrammet är också provets trasiga fixtur: `tests/enhet/test_baslinje.py`
kräver att domaren fäller det på alla fyra uppgifterna. Gör den inte det är
varje påståendetal här meningslöst.

### Skalan, hela vägen

De arton motbevisen i banken är människoskrivna och var och en ett verkligt
driftsättningsfel — en station som startar av sig själv när någon drar upp
nödstoppsdonet, en håll-för-att-köra som latchas.

| Vad | dömd | påståenden |
|---|---|---|
| referenslösningarna | 4 av 4 GODKÄND | 349 av 349 |
| baslinjen, nivå `spec` | 4 av 4 GODKÄND | 349 av 349 |
| **de 18 motbevisen** | **0 av 18 GODKÄND** | **1522 av 1605 (94,8 %)** |
| nollprogrammet | 0 av 4 GODKÄND | 252 av 349 (72,2 %) |

**Ett procenttal ur en påståenderäkning får aldrig bli bänkens huvudtal.** En
farlig lösning får 95 %. Ett program som gör ingenting får 72 %. Bara den
binära domen per uppgift skiljer dem åt. Raden är mekaniserad i
`test_pastaendeskalan_skiljer_inte_pa_farligt_och_riktigt`.

---

## 3. Vad baslinjen är

Tre lager, alla klassiska, inget av dem statistiskt.

### 3.1 Morfologin (`baslinje/morfologi.py`)

En driftsättares I/O-lista bär en konvention, och konventionen bär mening. Ett
kommando heter `..._CLOSE` och dess ändlägesgivare `..._CLOSED`; ett index
startas med `..._START` och kvitteras med `..._DONE`; ett vakuum slås på med
`..._ON` och bekräftas av `..._OK`. Det är samma regel som Rockwells PlantPAx
och Siemens PCS7 bygger sina enhetsmallar på.

Suffixtabellen är avläst ur **hela** bankens 51 uppgifter, inte ur de fyra som
bär spårfacit. Att härleda den ur de dömbara uppgifterna hade varit att bygga
generatorn mot domaren.

| Storhet | k av n |
|---|---|
| signaler i genereringsuppgifternas kartor | 390 |
| booleska stationsutgångar | 140 |
| **utgångar som paras ihop med en kvittens** | **55 av 140** |
| driftutgångar (`..._RUN`, går medan stationen går) | 14 av 140 |
| statusflaggor utan kvittens (`..._DONE`, `..._FULL`, `..._BUSY`) | 71 av 140 |

De 71 är inte ett fel i morfologin: en `ST040_BUF_FULL` *är* en statusflagga.
Men de är 71 utgångar som namnet inte säger något om hur de ska drivas, och det
är baslinjens första verkliga gräns.

### 3.2 Det kontrollerade språket (`baslinje/sprak.py`)

`control.sequence` och `control.interlocks` är skrivna i en kontrollerad
svenska med en liten och sluten verbrepertoar: *satt X hog*, *nollstall X*,
*vanta pa X*, *vid X:*, *starta vakten T s pa X*, *lat X folja Y*. En
mönsterläsare över en sluten grammatik är vad ett kravtabellsverktyg gör, och
det har funnits i branschen längre än språkmodellerna.

**Varje rad som inte går att läsa räknas.** En parser som tyst hoppar över det
den inte förstår ser ut att förstå allt.

### 3.3 Ramen och mallarna (`baslinje/generator.py`, `baslinje/packml.py`)

Varje station får en standardram: driftsvillkor ur nödstopp, tryckluft och
automatläge; latchat larm; kvitterad omstart på stigande flank; tidsövervakning
som TON; gränsvärdeslarm på mätsignaler; förreglingar som larmkällor. Stegkedjan
läggs i en `CASE` med ett **återgångssteg** som kräver att varje kommenderat
don har släppt — GRAFCET:s initialvillkor, och den enda regel som gör
singuleringen rätt (felklass `F15`).

Bär kartan en PackML-station — ett heltalstillstånd ut, ett heltalskommando in
och en State Complete-bit — instansieras i stället ISA-TR88.00.02:s
tillståndsmaskin, 17 tillstånd och 9 kommandon. Dispatchen sker på
**signalformen**, aldrig på uppgiftens nummer, och det provas mekaniskt: ingen
uppgifts-id förekommer i generatorns källkod.

---

## 4. Två växlar som är avstängda med flit

Grind 3 kräver att **varje** signal i kartan rörs och att **varje** utgång
drivs. Det går att klara utan att styra någonting: skriv `X := FALSE` en gång
och läs de oanvända ingångarna in i en diagnosbit.

De två växlarna `driv_obundna` och `las_obundna` gör precis det, och de är
**av som standard**. Skillnaden mäts:

| nivå | grind 3 |
|---|---|
| `spec` | 4 av 37 |
| `spec+driv+las` | 37 av 37 |

33 av 37 uppgifter går alltså från fälld till godkänd på grind 3 **utan att en
enda rad styrlogik ändras**. Det är grindtillfredsställelse och inte styrning,
och därför står det som en egen rad och aldrig i huvudtabellen. En grind som
blir billig slutar mäta sin egen storhet.

---

## 5. Ablationen: vilken del av indata bär resultatet

Ett tal som säger "4 av 4" säger inte varför. Ablationen tar bort en del av
indata i taget och kör om domen.

| uppgift | hel spec | ramen ensam | omvänd sekvens | utan förreglingar | utan uppgiftstext |
|---|---|---|---|---|---|
| `T-07` | **GODKÄND** | underkänd 62/73 | underkänd 61/73 | underkänd 69/73 | underkänd 69/73 |
| `H-04` | **GODKÄND** | underkänd 57/67 | underkänd 57/67 | underkänd 65/67 | underkänd 65/67 |
| `L-05` | **GODKÄND** | underkänd 93/111 | underkänd 95/111 | GODKÄND 111/111 | underkänd 107/111 |
| `S-05` | **GODKÄND** | **GODKÄND 98/98** | **GODKÄND 98/98** | underkänd 91/98 | underkänd 86/98 |

Tre avläsningar:

1. **Ordningen i specen bär resultatet.** Vänds sekvensen bak och fram faller
   3 av 4. Standardramen ensam räcker inte, och "4 av 4" är alltså inte ett tal
   om ramen.
2. **`S-05` löses av mallen ensam.** Uppgiften *är* en publicerad standard, och
   ett mallbibliotek är den klassiska metodens svar på en standard. Det är
   ärligt, och det är ett resultat i sig: **på en standarduppgift vinner
   avskriften av standarden.**
3. **Uppgiftstexten bär gränsvärdena.** Utan den faller alla fyra: `0 till
   300 mm`, `40 till 260 N`, `40 till 85 kPa`, `0 till 250 mm` står i prosan
   och inte i I/O-listan.

---

## 5b. Är "4 av 4" bara vår egen tolks åsikt?

Domen kommer från `svc/vc_assist_svc/st/tolk.py`. Har tolken fel om
ST-semantiken har facit fel, och då mäter bänken vår egen missuppfattning med
stor precision. `M-45` skrev in det som en öppen punkt: *samma spår genom
tolken och genom en annan motor, med skillnaden per signal och per scan
redovisad.*

Den mätningen är nu gjord för baslinjens kod.
`tests/protocol/kor_m62_baslinjen_mot_strucpp.py` bygger varje program med
STruC++ 0.6.6 till en körbar REPL och driver den med **samma spår, scan för
scan, på samma 20 ms cykel** som tolken. Varje utsignal läses varje scan — inte
bara där facit tittar, eftersom en jämförelse som bara tittar där facit tittar
bara hittar de skillnader facit redan letar efter.

| Storhet | k av n |
|---|---|
| sekvenser körda genom båda motorerna | 33 av 33 |
| scan jämförda | 3 060 |
| **signalavläsningar jämförda** | **15 354** |
| **avvikelser** | **0** |

Två oberoende implementationer av ST-semantiken ger alltså samma spår för
baslinjens kod, på varje avläst signal i varje scan. **Det bevisar ingenting om
OpenPLC:s runtime** — den leden av M-45:s öppna punkt är fortfarande obetald —
men det tar bort möjligheten att 4 av 4 är en artefakt av vår egen tolk.

---

## 6. Vad det här betyder för fas 9

Det finns två läsningar av "4 av 4", och bara den ena håller.

**Läsning A: klassiska metoder räcker, och en språkmodell behövs inte.** Den
faller på nivå `mager`: med bara I/O-listan klarar samma generator **0 av 4**.
Den faller också på avsnitt 7: över hela banken läser generatorn 89 av 265
sekvensrader.

**Läsning B: bankens fyra dömbara uppgifter specificerar sin egen lösning så
fullständigt att en översättning räcker.** Det är den läsning ablationen
stöder. `control.sequence` för `T-07` är åtta rader som namnger varje tagg och
varje handling i tur och ordning. Att göra ST av dem är en kompilering, inte en
konstruktion.

Ablationens rad *"ramen ensam"* är beviset, och den är redan mätt: **tas den
uppräknade sekvensen bort löser baslinjen 1 av 4**, och den enda som återstår
är `S-05`, som är en publicerad standard med ett mallbibliotek. Skillnaden
mellan 4 av 4 och 1 av 4 är alltså exakt vad `control.sequence` bär.

Följden för fas 9 är rak och obekväm:

> **Ett fas 9-tal på de här fyra uppgifterna måste läsas mot 4 av 4.** En modell
> som får 4 av 4 har hunnit ifatt en mallkompilator som kostar 0,56 ms och noll
> tokens. Den har inte visat att den kan något mer.

Bänken blir diskriminerande först när uppgifter slutar räkna upp sin egen
sekvens — när sekvensen måste **härledas** ur målet, fysiken och standarden i
stället för att stå i klartext. Det är inte en kritik av M-45:s fyra uppgifter;
de byggdes för att göra facit dömbart, och det lyckades. Det är en beställning
till nästa omgång uppgifter, och den bör bära:

* ett mål utan stegordning ("mata en detalj per formsprutcykel, aldrig två"),
* ett fel som bara syns i en gränssituation som texten inte pekar ut,
* ett krav som följer av en standard uppgiften inte citerar,
* en datastruktur uppgiften inte namnger (ett skiftregister, en kö).

Punkt fyra är den billigaste att lägga till och den som skiljer mest: se
avsnitt 7.2.

---

## 7. Var baslinjen ger upp

Det här är mätningens mest användbara del. Varje rad är ett ställe där en
språkmodell måste vara bättre för att vara värd sin kostnad.

### 7.1 Läsningen tar slut

Generatorns egen redovisning, med nämnare, över alla 37 genereringsuppgifter:

| nivå | lästa sekvensrader | lästa förreglingar | bundna utgångar | rörda ingångar |
|---|---|---|---|---|
| `mager` | 82 av 83¹ | 0 av 0¹ | 69 av 157 | 143 av 227 |
| `prosa` | 12 av 16² | 4 av 46² | 24 av 157 | 81 av 227 |
| `spec` | **89 av 265** | **52 av 111** | **56 av 157** | 130 av 227 |

¹ Nivån `mager` läser ingen text alls. Dess 83 "rader" är den stegkedja
morfologin själv härleder ur kartan, och nämnaren mäter alltså generatorns egen
utdata och inte uppgiftens. Raden står med för fullständighetens skull.

² Nivån `prosa` läser uppgiftstextens numrerade lista och punktkrav. **Bara 3
av 37 promptar bär en numrerad lista** (`T-07`, `H-04`, `L-05`), och de är tre
av de fyra uppgifter som har spårfacit. Nivåns tal mäter alltså tre uppgifter
och inte trettiosju.

Per uppgiftsgrupp, nivå `spec`:

| grupp | uppgifter | lästa rader | bundna utgångar | rörda ingångar |
|---|---|---|---|---|
| `T` transport | 7 | 27 av 48 | 16 av 23 | 27 av 37 |
| `L` palletering | 5 | 17 av 35 | 11 av 24 | 22 av 34 |
| `P` plock | 5 | 13 av 34 | 6 av 16 | 16 av 35 |
| `H` överlämning | 4 | 11 av 31 | 8 av 19 | 20 av 32 |
| `A` montering | 6 | 9 av 43 | 1 av 26 | 22 av 35 |
| `S` sortering | 5 | 6 av 38 | 9 av 19 | 14 av 26 |
| `C` cell | 5 | 6 av 36 | 5 av 30 | 9 av 28 |

`A` och `C` är sämst, och det är inte slumpen: monteringsuppgifterna beskriver
arbetsmoment med en varaktighet ("arbeta 26,0 s") och cellerna beskriver
kapacitet över en simulerad timme. Ingen av de två har en form i det
kontrollerade språket, och ingen av dem går att härleda ur ett taggnamn.

### 7.2 Fem klasser som ingen regel når

1. **Datastrukturer uppgiften inte namnger.** *"for skiftregistret framat med
   ST190_ENC_POS, inte med tiden"*. Det beskriver en kö med lägesindex.
   Baslinjen har ingen regel som bygger datastrukturer, och raden hamnar bland
   de olästa. Samma sak för `P-02`:s kotade positionskö och `L-01`:s
   mönsterberäkning.
2. **Arbetsmoment med varaktighet.** *"satt ST250_STA_BUSY hog och arbeta
   26,0 s"*. Tiden är läsbar, men "arbeta" är inget verb i grammatiken, och
   generatorn vet inte att en `..._BUSY` ska stå hög under den.
3. **Kapacitet.** `C`-gruppen mäter genomflöde över en simulerad timme
   (felklass `F11`). Det finns ingen regel från ett kapacitetsmål till en kod.
4. **Statusflaggor utan kvittens.** 71 av 140 booleska utgångar. `..._DONE`,
   `..._FULL`, `..._STARVED`. Vad som ska driva dem står i prosan, ofta som ett
   villkor över ett tillstånd generatorn inte har.
5. **Allt som kräver en avvägning.** *"vakuumet far inte slappas over hojd,
   bara nar kollit star an mot underlaget"* — regeln är entydig för en
   människa och har ingen tagg att hänga på.

### 7.3 Reparationen: en kod som pekar på en tid pekar inte på en rad

Baslinjen är deterministisk. Andra varvet ger samma kropp, och slingan låser
(`UTFALL_LAST`) — det är ett eget utfall och ärligare än att låtsas reparera.
Den enda klassiska reparationen är att läsa grindens **egen kodmärkning** och
ändra generatorns inställning, som en lintdriven fixare. Tabellen `ATGARDER`
har exakt två poster, och det är inte en förenkling:

| Grindkod | Åtgärd | Varför en regel finns |
|---|---|---|
| `ORORD_SIGNAL` | slå på `las_obundna` | grinden pekar ut en FORM: en signal som inte rörs |
| `ODRIVEN_UTGANG` | slå på `driv_obundna` | likaså |
| `invariant:...`, `flank:...`, `<sekvens>@<tid>ms:<signal>` | **ingen** | domen namnger ett symptom i tiden |

Slingan, körd genom `plc/reparation.py` med baslinjen som `Modell`, 4 uppgifter
× 3 nivåer × 2 lägen × 2 ramlägen:

| nivå | ram | utfall | varv |
|---|---|---|---|
| `spec` | båda | **LOST** 4 av 4 | 1 |
| `prosa` | `minimal` | LAST 4 av 4 | 2–3 |
| `prosa` | `maximal` | LAST 4 av 4 | 2–3 |
| `mager` | `minimal` | LAST 4 av 4 | 3 |
| `mager` | `maximal` | LAST 4 av 4 | 3 |

`rent` och `historik` ger **identiska** utfall i alla 48 körningarna. Det är
väntat och inte ett fel: baslinjen är minneslös per konstruktion, så de två
lägena visar den ingenting den kan använda olika. M-52:s skillnad mellan lägena
är en egenskap hos en modell med minne, inte hos slingan.

Med ramläget `maximal` når slingan hela vägen fram till spårfacit, och då står
koderna utan regel utskrivna. De är alla av samma sort:

```
T-07  index_fastnar_tidsovervakning@3000ms:SYS_ALARM
T-07  kallstart_kraver_kvittens@200ms:ST050_CNV_RUN
H-04  invariant:greppordningen_haller@hel_overlamning
H-04  hel_overlamning@1000ms:ST320_RB_START
L-05  invariant:handkorningen_ar_spardd_i_automatlage@ett_lager_i_automatlage
L-05  handkorning_ar_hall_for_att_kora@500ms:ST260_LFT_UP
```

Varje dom är riktig och åtgärdbar för en människa — tidsvakten saknas,
greppordningen är omkastad, handkörningen körs i automatläge. Men det finns
ingen mekanisk avbildning från *"SYS_ALARM var 0 vid 3000 ms"* till *"lägg till
en TON"*. **Det är den skarpaste gränsen mellan en regelbaserad reparatör och en
språkmodell**, och den är nu mätt i stället för antagen: 0 av 6 sådana koder
har en regel.

### 7.4 Ramens styvhet är produktens, inte baslinjens

Skelettets `VAR`-block är låst när slingan startar: `61_st_generering.md` säger
att modellen aldrig skriver deklarationer. Följden mättes här. En reparation som
behöver en **ny arbetsvariabel** — en timer, en flankdetektor, en diagnosbit —
går inte att göra inifrån slingan, och grind 2 fäller nästa varv på
`ODEKLARERAD`.

De två ramlägena skiljer storheterna åt: `minimal` bygger ramen ur första
svaret (slingans verkliga villkor), `maximal` ur generatorns hela
arbetsuppsättning. Skillnaden är mätbar och stor: på `minimal` slutar **16 av 24
slingor** i `ODEKLARERAD` — en kod som inte handlar om styrlogik alls utan om
att reparationen behövde en variabel ramen inte hade. På `maximal` försvinner
den koden helt, slingan når spårfacit, och utfallet blir ändå `LAST`.

Med andra ord: på `minimal` mäter slingan ramens styvhet. Först på `maximal`
mäter den metoden.

**Det här gäller en språkmodell precis lika hårt**, och det är ett fynd om
produkten och inte om baslinjen: en modell som inser att den behöver en TON kan
inte deklarera den. Antingen måste ramen bära varje tänkbar arbetsvariabel i
förväg, eller så måste slingan tillåta ett deklarationsförslag som grind 3
prövar separat. Frågan hör till den som äger `61_st_generering.md`.

---

## 8. Två buggar som mätningen hittade i sig själv

Båda hittades av att köra grindarna på generatorns egen utdata, och båda är
fixade och provade.

1. **Återgångsvillkoret byggdes efter typgallringen.** Generatorn strök
   direktiv vars villkor läste en heltalssignal som en boolesk term — men
   återgångssteget byggdes senare och slapp förbi. Resultatet var `IF NOT
   ST200_SCN_DEST THEN` på en `INT`. **Vår egen grind 2 fällde den, men först
   efter att STruC++ hade gjort det**, och koden hade sett färdig ut ända fram
   till kompilatorn. En kvittens som inte är boolesk kan inte betyda "donet har
   släppt".
2. **`SYS_RESET` föll ur redovisningen** därför att den räknades som
   systemsignal och inte som ingång. Grind 3 skiljer inte på de två: båda ligger
   i kartan och båda måste röras. En uppgift utan kvittenskrav kunde alltså
   fällas på `ORORD_SIGNAL` utan att generatorn hade sagt ett ord om det i sin
   egen rapport — en tyst skuld i just den lista som finns för att inte vara
   tyst.

Ett tredje fynd är inte en bugg utan en observation som hör hemma i
`61_st_generering.md`: **det kontrollerade språket i `control.sequence` är
maskinöversättningsbart, och prompttexten är det nästan.** Bara 3 av 37
promptar bär en numrerad lista (`T-07`, `H-04`, `L-05`), och det är just tre av
de fyra uppgifter som har spårfacit. Nivån `prosa` mäter alltså tre uppgifter
och inte trettiosju, och det står här så att ingen läser dess 321 av 349 som ett
tal om banken.

---

## 9. Parregeln, mekaniserad

`docs/spec/70_faser.md` fas 11 säger att fas 9:s tal alltid rapporteras som par.
`bank/par.py` gör regeln mekanisk. En `Domarsignatur` binder ihop allt som
avgör en dom:

* tolkens scanperiod och domarens marginal,
* vilka grindar som faktiskt kördes,
* en sha256 över **hela domarkedjans källkod** — `domare.py`, `tolk.py`,
  `lasare.py`, `lexer.py`, `stdbibliotek.py`, `validator.py`,
  `deklarationsgrind.py` och `stationsgrind.py`,
* en sha256 över de dömda uppgifternas facit,
* uppgiftslistan.

Skiljer sig något av det **avvisas paret**. Det går inte att slå av. Trasig
fixtur: `tests/enhet/test_baslinje.py` prövar alla sex fälten var för sig och
kräver att `para()` kastar. Skälet är den mätta incidenten hela grinddoktrinen
vilar på: en omimplementerad positionsdom underkände 2 av 4 medan ögat visade
4 av 4. En jämförelse mellan två domare mäter domaren.

Talet i avsnitt 1 är skrivet som ett par mellan `mager` och `spec+driv+las`,
och det är inte det par fas 9 ska publicera. Det paret har ännu bara en sida.

---

## 10. Slår baslinjen oss någonstans?

Frågan går inte att besvara ännu, och det ska sägas rakt ut: **fas 9 har inte
körts, så det finns ingen andra sida.** Vad som går att säga är var ribban
ligger, och den ligger högt:

| Uppgiftsklass | Baslinjens tal | Vad en modell måste slå |
|---|---|---|
| uppgifter med utskriven sekvens (`T-07`, `H-04`, `L-05`) | 3 av 3, varv 1 | 3 av 3, varv 1 |
| uppgift som är en publicerad standard (`S-05`) | 1 av 1, varv 1 | 1 av 1, varv 1 |
| grind 1 kompilering över hela banken | 37 av 37 | 37 av 37 |
| sekvensrader ur den strukturerade specen | 89 av 265 | **här finns luften** |
| förreglingsrader | 52 av 111 | **här finns luften** |
| utgångar med en drivande regel | 56 av 157 | **här finns luften** |
| reparation ur en spårfacitdom | 0 regler | **här finns luften** |

Om fas 9 rapporterar 4 av 4 på spårfacituppgifterna är resultatet **oavgjort mot
en mallkompilator**, och det ska rapporteras med de orden. De fyra sista raderna
är de enda ställen där en modell i dag kan visa något en regel inte kan.

---

## 11. Trösklar som M-62 sätter

| Konstant | Fil | Värde | Skäl |
|---|---|---|---|
| `STANDARDVAKT_S` | `baslinje/generator.py` | 30,0 s | **satt, inte mätt.** Tiden en tidsövervakning får när uppgiften inte anger någon. Medvetet hög: en vakt som faller för tidigt stoppar linjen på normal drift, och det är lika allvarligt som en vakt som saknas (M-45:s fönsterregel). En generator som gissar ska gissa åt det håll som inte stoppar produktionen |
| `MINSTA_STAM` | `baslinje/generator.py` | 3 tecken | satt. Kortaste ordstam som inte matchar halva ordlistan när en vakts eget namn (`lyftvakten` → `lyft`) slås upp i signalernas kommentarer. Används bara när uppgiften inte namnger vaktens signal, och varje sådan uppslagning skrivs ut som ett antagande i generatorns rapport |
| `HASHTECKEN` | `bank/par.py` | 12 | enbart läsbarhet i utskriften. Jämförelsen sker alltid på hela sha256:an |

PackML-numren i `baslinje/packml.py` är inte trösklar utan standardvärden;
härkomsten på varje rad är `PackTags v3.0, verifierad i M-45` — M-45 verifierade
numreringen i tre oberoende källor (Beckhoffs `E_PMLState`, Omrons
implementationsguide och OPC 30050 v1.01).

---

## 12. Vad som INTE är prövat

Det här avsnittet är längre än det bekväma, med flit.

* **Ingen språkmodell kördes.** Paret i avsnitt 1 är baslinjen mot sig själv på
  två indatanivåer. Fas 9:s sida finns inte, och inget tal härifrån är en
  jämförelse mot en modell.
* **33 av 37 genereringsuppgifter har inget spårfacit.** För dem säger
  mätningen bara att koden kompilerar och matchar kartan — alltså precis det
  mått avsnitt 2 visar är innehållslöst. Baslinjens verkliga tal är 4 av 4 på en
  nämnare av 4, inte på 37.
* **Ingen uppgift är körd i VC.** Ögat har inte sett en enda av de 37
  programmen. Spårfacit dömer ST-semantiken; scenen är odömd, och invariant I1
  säger att det är ögat som fäller domen om scenen.
* **Ingen uppgift är körd i OpenPLC.** Tolken och runtimen är fortfarande inte
  jämförda. Grind 1 säger att koden byggs av STruC++, inte att OpenPLC gör
  samma sak med den.
* **Grind 4 är inte körd, 0 av 37.** Baslinjen skriver ingen scenkod. En
  jämförelse mot en modell som gör det jämför inte samma sak.
* **Grammatiken är skriven av mig, mot bankens egna rader.** Att den läser 89 av
  265 rader är ett mått på just den grammatikens räckvidd, och en annan läsare
  hade fått ett annat tal. Vad talet däremot inte kan vara är för högt: varje
  oläst rad är räknad, och `tests/enhet/test_baslinje.py` provar att en oläsbar
  rad hamnar i listan i stället för att försvinna.
* **`mager` och `prosa` är svagare än de behöver vara.** En bättre I/O-listnivå
  skulle kunna läsa signalernas kommentarer, och en bättre prosanivå skulle
  kunna läsa löptext och inte bara listor. Talen 0 av 4 för de två nivåerna är
  alltså inte "vad en klassisk metod kan" utan "vad den här klassiska metoden
  kan med den indatan".
* **Ablationen prövar fyra varianter, inte alla.** Att `S-05` klarar sig utan
  sekvens visar att mallen räcker där; det visar inte att mallen är rätt
  implementerad i någon annan mening än att facit håller.
* **Reparationstabellen har två poster därför att bara två grindkoder pekar ut
  en form.** Att en tredje inte finns är ett påstående om de grindar som körs i
  dag, inte om alla möjliga grindar.
* **Tidsmätningen är en enda körning per nivå** på en maskin som samtidigt kör
  ett skrivbord. 0,56 ms per uppgift är en storleksordning, inte ett
  precisionstal, och den behöver ingen precision: den ska jämföras med ett
  modellanrop som tar sekunder.
* **Ingen mätning av vad baslinjen gör med en uppgift utanför banken.**
  Morfologin är avläst ur den här bankens namnkonvention. En verklig anläggning
  med ett annat taggformat kan ge noll parade don, och då faller hela
  stegkedjan bort.

---

## 13. Hur man kör det

```
python3 -m pytest tests/enhet/test_baslinje.py -q     # L1, 66 prov
python3 bank/baslinjebank.py                          # talen, utan grind 1
python3 bank/baslinjebank.py --strucpp <cli>          # med grind 1
python3 bank/baslinjebank.py --kalibrering            # skalan i avsnitt 2
python3 bank/baslinjebank.py --ablation               # avsnitt 5
python3 bank/baslinjebank.py --slinga --par --tid     # avsnitt 7.3, 9 och 1
python3 bank/baslinjebank.py --uppgift T-07 --niva spec
```

Hela mätningen utom grind 1 kör på under fem sekunder, utan VC, utan OpenPLC
och utan nät. Grind 1 kräver STruC++ 0.6.6, som `python3 install/verktygskedjan.py`
hämtar med fastspikad version och kontrollerad hash.

**beskriver:** `svc/vc_assist_svc/plc/baslinje/`, `bank/baslinjebank.py`,
`bank/par.py`, `tests/enhet/test_baslinje.py`
