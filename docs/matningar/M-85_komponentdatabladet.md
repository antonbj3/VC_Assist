# M-85 — databladet svarar för 3201 komponenter, men banken och biblioteket talar inte samma språk

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_m85_databladets_tackning.py` (täckningen)
och `tests/protocol/kor_m85_halen_ur_m84.py` (hålen)
**Det som byggs och prövas:** `svc/vc_assist_svc/komponentdatablad.py`,
verktyget `component_datasheet`, och frågorna `komponent` / `komponentsok` /
`bank` i `tests/protocol/stod/slaupp.py`
**Prövar:** de fyra osäkerheter M-84 namngav i sitt sista avsnitt.

## Frågan

M-84 mätte att API-uppslagen bytte modellens ordförråd från 13 till 32 namn,
och skrev sedan ut exakt var uppslagen tog slut:

> *Indexet täcker API-symboler. Det täcker inte per-komponent-data:
> komponenternas egenskapsnamn (`ConveyorSpeed`, `StrokeTime`, `MaxPayload` …),
> `bank://`-URI:erna, och VILKEN boolsk signal
> `findBehavioursByType(VC_BOOLEANSIGNAL)[0]` är på en given komponent.*

Fyra hål, alla namngivna. Den här mätningen frågar två saker: vad bär
`component.rsc` faktiskt, och hur många av de fyra hålen stängs.

## Var egenskaperna ligger, och varför det inte var självklart

`katalogindex._parametrar` söker med ett reguljärt uttryck i **hela** filtexten.
Dess egen docstring säger vad det ger: *"en LISTA OVER VAD SOM NAMNS, inte över
komponentens egenskaper"* — M-59 mätte att Prorunner mk1 bär namnet `Length` 24
gånger inne i sina 16 geometrilådor och noll gånger som egen egenskap.

Databladet läser i stället **strukturen**. Djupen är räknade med en
klammerräknare, inte antagna ur indraget — och det är inte en detalj: inne i
ett `Functionality`-block skriver VC:s serialiserare varje rad i kolumn 0,
medan `VariableSpace` drar in två steg per nivå. Ett radbaserat djupmått hade
gett fel svar utan att märkas.

```
Node "rSimResource"          djup 0
  Name "AccuVeyor AVh"       djup 1
  NodeClass { ... }          djup 1   GEOMETRIN — hoppas över i sin helhet
  Functionality "rOneWayPath" { ... }  djup 1   ett beteende, med sitt NAMN
  Category "Conveyors"       djup 1
  VariableSpace "" { ... }   djup 1   KOMPONENTENS EGNA EGENSKAPER
  Node "rSimLink" { ... }    djup 1   en led — och kedjan är NÄSTAD
```

Att hoppa över `NodeClass` är både det som gör läsningen korrekt och det som
gör den billig: 3201 komponenter på **16,7 s** med fyra processer, mot 12,8 s
för katalogindexets djupa läsning som ändå inte kan skilja lådan från
komponenten.

## Täckningen, ett tal per fält (3201 komponenter)

| | antal | andel |
|---|---|---|
| läsbara datablad | 3201 / 3201 | **100 %** |
| bär minst en EGEN egenskap | 3075 | 96,1 % |
| bär minst ett beteende | 3127 | 97,7 % |
| bär minst ett gränssnitt | 3002 | 93,8 % |
| bär minst en led | 2770 | 86,5 % |
| bär minst en signal | 568 | **17,7 %** |
| bär tillverkarens egen beskrivning | 2956 | 92,3 % |
| … därav med `### Key properties ###`-rubrik | 2482 | 77,5 % |

Räknat per **egenskap** i stället för per komponent — 82 383 egenskaper:

| fältet finns | antal | andel |
|---|---|---|
| standardvärde | 77 876 | 94,5 % |
| redigerbarhet i `Settings` | 76 964 | 93,4 % |
| tillåtna värden (`StepList`) | 12 884 | 15,6 % |
| **storhet (`Quantity`)** | **11 539** | **14,0 %** |

**Den sista raden är mätningens viktigaste.** Sex egenskaper av sju säger
ingenting om vilken storhet de bär. En transportör vars `SpeedIn` står på 820
säger inte om det är mm/s, m/min eller något annat — och VC:s världsenhet är
millimeter, vilket gör det frestande att fylla i. Databladet skriver därför
`storhet saknas` och lämnar talet naket. De 14 procent som **har** en
deklaration bär tolv olika storheter, alla ur källans egna ord: `Distance`
(2830 komponenter), `Angle` (643), `Mass` (451), `Time` (218), `Velocity`
(170), `Speed` (166), `Percentage` (138), `Angular velocity` (104),
`Frequency` (31), `Acceleration` (22), `Angular acceleration` (11), `Volume`
(3).

Att `Velocity` och `Speed` båda förekommer är inte vår inkonsekvens utan
källans: **AccuVeyor AVh bär båda i samma variabelrymd** —
`Control::OnInfeedActionSignalTrue` är `Speed` medan dess fyra syskon är
`Velocity`. Ett lager som normaliserat dem hade dolt att tillverkaren själv
inte är konsekvent.

Katalogposten (`model.xml`) deklarerar `MaxPayload` i 2986 av 3201 och `Reach`
i 2556 — men **utan enhet**. Filen skriver talet och ingenting mer. Databladet
skriver därför `MaxPayload (deklarerat fält i katalogposten, ENHET EJ
DEKLARERAD i filen): 25`. Att repots katalogskikt kallar dem mm och kg är en
tolkning som hör hemma där, inte här. Ett annat tal ur samma rad: 628 av de
2986 deklarerar `MaxPayload = 0`, och en nolla som skrivs ut som "0 kg" ser ut
som ett mätt värde.

## Beteendetypernas två namnrymder

Filen skriver `Functionality "rSimBoolSignal"`. Python-sidan heter
`VC_BOOLEANSIGNAL`. Ingen källa vi har — varken `api.xml`, `constants.xml`
eller komponentfilerna — skriver ut avbildningen mellan dem. Tabellen
`API_TYP` är därför delvis **härledd** (rsc-namnet normaliserar exakt till en
konstant som finns) och delvis **handsatt**, och varje post bär vilket den är.
Trettio poster täcker **29 128 av 31 403 beteendeförekomster (92,8 %)**;
biblioteket bär 44 distinkta typer och 14 av dem ger `saknas`.

**Grinden fällde mitt eget fel innan tabellen använts en enda gång.** Första
versionen innehöll `VC_PROCESS`, som inte står bland `constants.xml`:s 709
konstanter. Det är exakt den felklass M-84 mätte hos modellen, som var på väg
att skriva `VC_BOOLSIGNAL` i tre scenfiler innan ett uppslag stoppade den.
Sju nycklar till ströks: `rSimComponentContainer`, `rSimComponentSignal`,
`rSimMatrixSignal`, `rSimProcess`, `rSimRealSignal`, `rSimServoController`,
`rSimToolContainer` — de förekom i **noll av 3201** komponenter. Jag hade hittat
på filformatets namn ur Python-sidans, och ett namn som ingen fil bär går inte
att kontrollera. Det är precis därför det hade överlevt.

## De fyra hålen, frågade mot det levererade verktyget

Frågorna ställs som underprocesser mot `tests/protocol/stod/slaupp.py` — samma
väg en modell skulle gå.

### Hål 2: `bank://`-URI:erna — **STÄNGT**

`slaupp.py bank <uri>` slår upp URI:n i bankens eget index.
**15 av 15** URI:er i M-84:s tre scener verifierade. En påhittad URI ger
`found=false` med 15 **verkliga** alternativ, aldrig en gissad sökväg.

### Hål 1: egenskapsnamnen — **STÄNGT för biblioteket, men se nedan**

För de komponenter som går att slå upp svarar databladet med exakta namn:
**11 av 11**, mellan 21 och 47 egenskaper vardera. Biblioteket bär 2527
distinkta egenskapsnamn — det ordförråd modellen saknade.

M-84:s tre exempelnamn, sökta som egenskap över hela biblioteket:

| namn | finns som egen egenskap i |
|---|---|
| `ConveyorSpeed` | 118 av 3201 (3,7 %) |
| `MaxPayload` | 3 av 3201 (0,1 %) — det är ett **katalogfält**, inte en egenskap |
| `StrokeTime` | **0 av 3201** |

`StrokeTime` finns inte i biblioteket. Däremot namnger 344 komponenter något
med "stroke" i. Det är därför frågan måste ställas per komponent: svaret är
inte "ja" eller "nej" utan "på den här komponenten heter den X".

### Hål 3: vilken boolsk signal är `[0]` — **BESVARAT, och svaret var ett annat än väntat**

| | antal | andel |
|---|---|---|
| 0 boolska signaler | 2820 | **88,1 %** — `[0]` kastar `IndexError` |
| exakt 1 | 71 | 2,2 % — `[0]` är entydigt, och databladet säger namnet |
| fler än 1 | 310 | 9,7 % — ordningen är filens, inte API:ets |

**Alla elva robotar i provet bär noll boolska signaler.** De använder
`rSimBoolSignalMap` ("Inputs"/"Outputs"), inte enskilda signaler. M-84:s kod
skrev `VC_BOOLEANSIGNAL` 16 gånger; på en robot hade `[0]` kastat. Frågan
"vilken signal är `[0]`" hade alltså fel förutsättning för 88 procent av
biblioteket, och det är det svaret databladet ger — inte ett namn, utan att
raden inte kommer att köra.

För de 9,7 procent som bär flera säger databladet rent ut att ordningen i
filen inte är mätt mot API:ets, och hänvisar till `findBehaviour(namn)`.

### Hål 4: `vcHelpers.Robot` mot `Robot2` — **ÖPPET**

Båda finns, båda har 12 medlemmar. Frågan handlar om VC:s hjälpmoduler, inte om
en komponent, och databladet rör den inte. Den kräver ett kört VC.

## Fyndet ingen frågade efter: banken och biblioteket delar inte vokabulär

Steg ett i hål 1 var att slå upp scenernas komponenter i biblioteket. Det gick
inte:

```
0 av 15 bankposter i M-84:s tre scener går att slå upp i biblioteket
11 av 65 bankposter totalt går — alla elva är robotar
```

Bankens namn är svenska beskrivningar (`Bandtransportör, bandbredd 600 mm`,
`Pneumatisk stoppgrind`); bibliotekets är tillverkarnas modellnamn
(`IRB 1200-5/0.9`). De elva som brygger gör det bara efter att bankens
tillverkarprefix strukits: banken skriver `ABB IRB 1200-5/0.9`, biblioteket
`IRB 1200-5/0.9`.

Följden är skarp och den ska sägas rakt ut: **databladet stänger hål 1 och 3
för det installerade biblioteket, men inte för de scener M-84 faktiskt mätte.**
De byggdes av bankens 65 handskrivna poster, som inte har någon motsvarighet på
disk. Att kalla hålen stängda utan den raden hade varit att mäta fel sak och
kalla det framgång.

## Formen: kapning på antal poster

Varje avsnitt kapas på **p90 för sin egen fördelning** — nio komponenter av tio
kommer igenom hela, och den tionde får veta hur många rader som inte visades.
Ett gemensamt tak hade varit fel storhet:

| avsnitt | median | p90 | p99 | max | tak |
|---|---|---|---|---|---|
| egenskaper | 21 | 47 | 103 | 110 | **47** (p90) |
| beteenden | 11 | 12 | 20 | 59 | **20** (p99) |
| gränssnitt | 3 | 3 | 5 | 23 | **5** (p99) |
| leder | 6 | 17 | 71 | 88 | **17** (p90) |
| beskrivning, tecken | 1179 | 1179 | 1275 | 2083 | **1300** (>p99) |

Beteenden och gränssnitt får p99 och inte p90: det är just de listorna som bär
svaret på M-84:s öppna fråga, och skillnaden kostar under tusen tecken. Hela
databladet blir median **6496 tecken**, p99 9756, max 12 262.

Kapningen sker på ANTAL POSTER, aldrig på tecken. Det felet är redan gjort en
gång i det här repot — `slaupp.py` skivade JSON-strängen på tecken och gav
utdata som var läsbar för ett öga och oparsbar för allt annat. Provet som
bevakar det heter numera `test_slaupp.py::test_kapning_ger_giltig_json` och
gäller alla sex frågorna. (Den kommentar som påstod att provet redan fanns
skrevs innan provet gjorde det — samma sorts löfte utan namn som M-77 mätte.)

## Tre fel som proven fällde, och som annars inte hade synts

1. **`VC_PROCESS`** stod i typtabellen och finns inte. Fälldes av grinden mot
   `constants.xml`.
2. **Ledkedjan lästes platt.** `Axis2` ligger inne i `Axis1` i filen. En platt
   läsning av rotnodens direkta barn gav "0 leder" på en sexaxlig ABB-robot —
   ett trovärdigt tal, inte ett undantag, och alltså osynligt utan ett prov som
   räknar leder.
3. **`BOMdescription` bryter rader med bakstreck.** Utan `re.S` i
   argumentmönstret slutade AccuVeyor AVh:s beskrivning efter ett enda ord
   ("Ambaflex") och såg ut som en kort beskrivning i stället för en kapad.

## LIMITS

* **Avbildningen rsc-typ → `VC_`-konstant är inte verifierad mot ett kört VC.**
  Proven visar att varje konstant finns i `constants.xml`, att de härledda
  posterna verkligen härleds och att de handsatta inte gör det. De visar
  **inte** att `VC_BOOLEANSIGNAL` är den konstant `findBehavioursByType` vill
  ha för `rSimBoolSignal`. Sju handsatta poster är påståenden, och databladet
  pekar ut dem i sitt eget svar.
* **Signalordningen är filens, inte API:ets.** För de 310 komponenter som bär
  flera boolska signaler går `[0]` inte att avgöra härifrån. Att `[0]` kastar
  på de 2820 utan signaler är däremot en slutsats som inte beror på ordning.
* **Ingen komponent har laddats i VC.** Att en egenskap heter `SpeedIn` i filen
  är inte samma sak som att `comp.getProperty('SpeedIn')` ger den — VC kan
  skapa och byta namn på egenskaper vid laddning. Databladet är en läsning av
  filen på disk.
* **Enheterna är inte lösta, bara ärligt rapporterade.** 86 procent av
  egenskaperna saknar storhetsdeklaration, och databladet kan inte säga vad
  deras tal betyder. Det är en LÄST gräns, inte en löst fråga.
* **Bryggan bank ↔ bibliotek finns inte.** 11 av 65, noll i de tre scener M-84
  mätte. Tills den finns svarar databladet inte på frågor om de komponenter
  bankens uppgifter faktiskt använder.
* **Inget bibliotekstäckande egenskapsnamnindex byggs.** Frågan "vilka
  komponenter har en egenskap som heter något med *speed*" går inte att ställa
  billigt: en genomläsning kostar 16,7 s med fyra processer, och tjänsten
  bygger sitt index lat i EN process. `search_installed_library`:s
  `has_parameter` finns men söker i hela filen och får med geometrin (M-59).
* **`vcHelpers.Robot` mot `Robot2` står öppet**, oförändrat sedan M-84.
* **Täckningstalen gäller ETT bibliotek** — VC 4.10:s eCatalog-innehåll på den
  här maskinen, 3201 komponenter från 149 tillverkare. En annan installation
  med andra tillverkarpaket kan ha andra andelar.
* **Fördelningarna som satte taken mättes med de gamla taken på plats.**
  Talen för egenskaper, beteenden, gränssnitt och leder är oberoende av taken,
  men "hela databladets tecken" är det inte: 6496/9756/12 262 gäller de
  levererade taken och skulle växa med högre.
