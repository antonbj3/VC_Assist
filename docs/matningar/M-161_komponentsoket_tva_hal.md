# M-161 — komponentsökets nolla var två hål: 60 vokabulärfrågor och 15 formatfrågor

**Datum:** 2026-09-05
**Rigg:** `tests/protocol/kor_m161_komponentsoket.py` (delningen, de skalade
fixturerna och omkörningen av M-119:s korpus),
`tests/enhet/test_katalogsok_normalisering.py` (de trasiga fallen som L1)
**Det som prövas:** `svc/vc_assist_svc/katalogsok.py`,
`svc/vc_assist_svc/verktyg/katalog.py`, `svc/vc_assist_svc/katalogindex.py`,
`tests/protocol/stod/slaupp.py`
**Prövar:** om `M-119`:s `S5_bibliotek` — **0 % SVAR av 75**, det största
kända hålet i uppslagen — är ett fel eller flera, och hur stor del av det som
går att laga i söket

## 0. Först: var indexdatan faktiskt kommer ifrån

Frågan ställdes för att `katalogindex.bygg(<repots rot>)` ger **0 poster**, och
det såg ut som att indexet på 3 201 komponenter byggdes ur något annat än det
koden säger.

Det gör det inte. `bygg()` går igenom en **biblioteksrot** och letar `.vcmx`;
repots rot innehåller inga sådana filer, så noll är rätt svar på fel fråga.
Roten letas upp av `katalogindex.hitta()`, och **`hitta()` returnerar rötter,
inte filer**. På den här maskinen finns exakt en:

```
/home/anton/.wine-vc-test/drive_c/users/Public/Documents/
        Visual Components/4.10/Models/Components
    hittad via: wine: Public/Documents, version 4.10
```

Mätt i den katalogen, den här körningen:

| | |
|---|---|
| filer totalt under roten | **3 201** |
| därav `.vcmx` | **3 201** (inga andra filer alls) |
| poster ur `bygg(rot, djupt=True)` | **3 201** |
| olästa filer (`olasliga`) | **0** |
| tid, djupt läge | **8,0 s** |
| familj ur strukturen | robot 2 202, transportör 227, verktyg 73, ingen markör 699 |

Att `Fynd.antal` är `0` i det `hitta()` lämnar ifrån sig är inte ett tomt
bibliotek: fältet fylls aldrig i av `hitta()`, som bara letar upp rötter.
**Ett `len(hitta()) == 1` är en rot, inte en komponent.** Det talet är den
enda fällan i vägen hit, och den är värd att skriva ut, för den ser ut som ett
hundrafalt fel.

Kontrollen som gör läsningen trovärdig kommer utifrån: en oberoende räkning av
`rSimRobotController` i `component.rsc` över samma katalog ger **2 202**, och
det är exakt vad familjemarkören i det djupa indexet ger. Två läsningar med
olika kod som ger samma tal är det närmaste en bekräftelse den här körningen
kommer.

Verktygsvägen bygger indexet **latt, en gång per process**
(`verktyg/katalog.py::_bibliotek`). `slaupp.py` startar en ny process per
fråga, och det är därför ett enda `komponentsok` kostar omkring nio sekunder —
`M-119` mätte 9,878 s för sitt första.

## 1. Delningen, och regeln som avgör den

De 75 frågorna delas av ett fält banken redan bär, `stampel`, som skrevs innan
sökverktyget fanns och som **inte beror på något sökresultat**. Det är hela
poängen: klassen avgörs av frågan, aldrig av svaret.

| stämpel | vad namnet är | antal | klass |
|---|---|---|---|
| `ANTAGEN` | bankförfattarens egen svenska funktionsbeskrivning — *"Induktiv närvarogivare"*, *"Bandtransportör, bandbredd 400 mm"* | **60** | **1 — vokabulärglapp** |
| `PUBLICERAD_SPEC` | en tillverkares publicerade modellbeteckning — *"ABB IRB 2600-20/1.65"* | **10** | **2 — formatglapp** |
| `STANDARDMATT` | en standards beteckning — *"VDA KLT 4147"*, *"EUR-pall"*, *"Gitterbox"* | **5** | **2 — formatglapp** |

**60 klass 1, 15 klass 2.** Det är delningen, och den är halva svaret: de 60
har ingen modellbeteckning att normalisera, och de 15 har ingenting med
vokabulär att göra.

## 2. Klass 2, en rad per fråga

Frågan är inte *"kan söket hitta den"* utan *"finns den att hitta"*. Åtta av
femton finns, sju gör det inte, och de sju får aldrig bli en träff.

| id | banken skriver | biblioteket bär | |
|---|---|---|---|
| S5-001 | ABB IRB 2600-20/1.65 | `IRB 2600-20/1.65` | finns |
| S5-006 | FANUC M-10iD/12 | `M-10iD/12` | finns |
| S5-022 | FANUC LR Mate 200iD/7L | `LR Mate 200iD/7L` | finns |
| S5-025 | KUKA KR 10 R1100 sixx | `KR 10 R1100 sixx` (+3 varianter) | finns |
| S5-035 | ABB IRB 1200-7/0.7 | `IRB 1200-7/0.7`, `… Gen2` | finns |
| S5-036 | ABB IRB 4600-60/2.05 | `IRB 4600-60/2.05` | finns |
| S5-051 | ABB IRB 1200-5/0.9 | `IRB 1200-5/0.9`, `… Gen2` | finns |
| S5-055 | ABB IRB 910SC-3/0.55 **SCARA** | `IRB 910SC-3/0.55` | finns, med ett efterled för mycket i frågan |
| S5-043 | ABB IRB 660-180/3.15 | bara `IRB 660` | **finns inte** |
| S5-056 | ABB IRB 360-1/1130 FlexPicker | bara `IRB 360-3/1130`, `IRB 360-1/1600` | **finns inte** |
| S5-032 | VDA KLT 4147 | — | **finns inte** |
| S5-041 | VDA KLT 6280 | — | **finns inte** |
| S5-075 | VDA KLT 6147 | — | **finns inte** |
| S5-044 | EUR-pall | — | **finns inte** |
| S5-060 | Gitterbox | — | **finns inte** |

De två raderna i mitten är de farligaste i hela mätningen. `IRB 660` **ligger
i biblioteket** och `IRB 360-3/1130` gör det också — de är grannar, inte
komponenten. Ett sök som görs mer tillåtande glider dit, och då har nollan
bytts mot något värre än en nolla.

## 3. Vad varje normaliseringsnivå ger — och vad den inte ger

Fyra nivåer, mätta mot det riktiga biblioteket med de 75 riktiga frågorna:

| nivå | vad den gör | frågor med ≥1 träff |
|---|---|---|
| 1 | rak delsträng, skiftlägesokänslig (**dagens**) | **0 av 75** |
| 2 | + skiljetecken, mellanslag och skiftläge borttagna | **0 av 75** |
| 3 | + ett ledande tillverkarnamn läst som **tillverkare** | **7 av 75** |
| 4 | + efterställda rena bokstavsord släppta | **8 av 75** |

**Nivå 2 ger exakt noll.** Hypotesen att felet är `-` mot `_` mot `/` är alltså
fel för det här biblioteket: banken och biblioteket skriver beteckningen
**tecken för tecken lika**, ända ner till snedstrecket och punkten. Det enda
som skiljer är **förleden och efterleden**.

Att nivå 2 ändå levereras har ett eget mätt skäl, och det är inte den här
banken. Samma 3 201 biblioteksnamn omstavade — mellanslag, `-` och `/` utbytta
mot `_`, mot `-`, och mot ingenting alls — hittas av den **raka** delsträngen i
612, 1 403 respektive 508 fall av 3 201; av den **normaliserade** i **3 201 av
3 201**, och i inget av de 7 080 fallen saknades den riktiga komponenten bland
träffarna. 81 procent av dem gav dessutom **en enda** träff. Nivån betalar sig
den dag ett bibliotek eller en modell stavar `IRB2600_20_165`; på det här
biblioteket kostar den ingenting och ger ingenting.

## 4. Lagningen: en stege, inte en union

Nivåerna är ordnade från strängast till lösast, och **en lösare nivå körs bara
när den strängare gav noll träffar**. Det är inte en stilfråga, det är den
mätta skillnaden mellan en lagning och en breddning:

* Som en **union** breddar den skiljeteckenslösa matchningen **74 av 3 201**
  självfrågor (2,31 %) och antalet träffar totalt med 1,35 %. `C4` börjar då
  hitta `EC-400`, `S5` hittar `E2S 551S`, `SR3` hittar `WCPS-R-30`.
* Som en **stege** är breddningen noll av konstruktion: nivån når aldrig en
  fråga som redan träffade.

Det gäller också tillverkarledet. `ABB` blir ett **filter** och inte ett
bortstruket ord — en beteckning som bärs av en annan tillverkare träffar inte.
Och innanför tillverkaren provas den raka delsträngen före den normaliserade,
av exakt samma skäl som ordningen mellan nivå 1 och 2.

En spärr är mätt och inte gissad. Tillverkarledet får bara strykas när minst
**två** tecken står kvar av beteckningen (`MIN_BETECKNING`). Utan spärren är
`KUKA 1` ett jokertecken över hela KUKA:s sortiment, för biblioteket bär åtta
komponenter som heter `0` … `7`. Talet står i sitt eget avsnitt nedan, med
felfrekvensen som satte det.

Det söket **säger** är en del av lagningen. Svaret bär ett nytt fält,
`lasning`, som skriver ut vad verktyget tolkade om — att ett förled lästes som
tillverkare, och vilket efterställt ord som släpptes. Ingen bortprioritering
är tyst; en träff som kom av att en del av frågan kastades får inte se ut som
en träff på frågan.

## 5. De trasiga fixturerna, i skala — och de fällde mig

Grinden skrevs före mekanismen och var **röd i nio prov** innan koden fanns.
Men ett handplacerat fall är en förhoppning; risken här är statistisk, så
fixturerna körs över hela biblioteket.

| fixtur | frågor | träffar | krav |
|---|---|---|---|
| varje sifferblock i namnet utbytt mot `9997` | **2 935** | **0** | noll |
| rätt komponentnamn med **fel** tillverkarled framför | **3 201** | **0** | noll |
| rätt komponentnamn med **rätt** tillverkarled (motprovet) | **3 201** | 3 180 hittade sig själva, 2 721 som ensam träff | ≠ noll |

**Den andra fixturen föll, och den föll på min egen mekanism.** Första
versionen av efterledsrungan gav

```
INOVANCE TS 5 - Rotate Unit  ->  IR-TS5-55Z15S-INT
   läst som: "INOVANCE" som tillverkare; "Rotate Unit" släpptes ur namnet
```

Båda de beskrivande orden föll, stubben blev `ts5`, och `ts5` ligger inne i
normaliserade `irts555z15sint`. En komponent som inte har med frågan att göra,
levererad som en säker ensam träff. Det är precis det fel uppdraget förbjöd,
och ingenting utom en fixtur i skala hade sett det: `Rotate Unit` är inget
efterled någon hade hittat på att prova.

Regeln som lagade det är allmän och inte ett undantag för just den raden:
**två lättnader får inte staplas.** Att kasta en del av frågan är redan en
lättnad; att samtidigt strunta i skiljetecknen gör stubben till något annat än
en beteckning. Efterledsrungan matchar därför **rakt** och aldrig normaliserat.
`ts 5 -` matchar ingenting; `IRB 910SC-3/0.55` matchar sig själv, så den enda
vinsten står kvar och `IRB 360-1/1130 FlexPicker` står kvar på noll.

Fixturen är dessutom **deterministisk**: den drar sin felaktiga tillverkare med
`zlib.crc32` och inte med `hash()`, som saltas per process. Första körningen
gav noll och andra gav ett, utan att en rad kod ändrats — en grind som inte är
reproducerbar mäter inte sin egen storhet.

Sju fall ur den riktiga mätningen står som L1 i
`tests/enhet/test_katalogsok_normalisering.py` och måste ge **noll** även
efteråt: `ABB IRB 660-180/3.15` får inte bli `IRB 660`, `ABB IRB 360-1/1130
FlexPicker` får inte bli `IRB 360-3/1130`, `VDA KLT 4147` inte bli något alls,
`Bandtransportör, bandbredd 400 mm` inte heller, `KUKA IRB 1200-5/0.9` inte
matcha på fel tillverkare, `ABB IRB 9997-99/9.99` inte på formen, och
`INOVANCE TS 5 - Rotate Unit` inte på en stubbe.

## 6. Klass 1: varför den inte ska lösas i söket

Frestelsen är ett alias-skikt: `Bandtransportör` → `Belt Conveyor`,
`Vakuumgripare` → `Vacuum Gripper`. Tre mätta skäl talar emot, och det tredje
är det som avgör.

**Ett.** Ett handskrivet synonymregister har ingen laglig facitkälla.
`85_bankkontraktet.md` §2 räknar upp fem, och ett register jag själv skriver
mot det bibliotek det ska dömas på är den sjätte — den förbjudna. Banken
stämplar dessutom själv de 60 posterna `ANTAGEN`: **banken påstår inte att
komponenten finns.** Att binda ett antaget namn till en riktig produkt är att
uppfinna en koppling som ingen av de två sidorna deklarerar.

**Två.** En sond med 60 handskrivna engelska ord — vilket är precis vad ett
alias-skikt *är* — hittar något namn för 30 av 60. Hälften. Och sonden träffar
falska vänner: `press` ger sex `KR … press`, som är KUKA-**robotar** för
presskötsel; `bin` ger `controller box`; `lift` ger `Forklift AGV`. Där
kopplingen alls går att kontrollera mekaniskt — bankens `kategori` mot
bibliotekets `familj`, vilket bara 18 av de 60 posterna medger — motsäger
1 av 13 sondträffar bankpostens egen kategori.

**Tre, och det här är skälet.** De två vokabulären beskriver **inte samma
storheter**. De 60 klass-1-posterna bär tillsammans **31 olika mätta fält**,
och de flesta är **tider**: `anslag_s`, `spanntid_s`, `svarstid_ms`,
`presstid_s`, `bedomningstid_ms`, `indexeringstid_s`. Bibliotekets
katalogpost deklarerar **två** fält, `Reach` och `MaxPayload`. **Exakt 1 av de
60** bankposterna bär ett fält biblioteket överhuvudtaget deklarerar
(`nyttolast_kg`), och noll bär `rackvidd_mm`. Ett alias-skikt hade alltså
bryggat **orden** och ändå inte **storheterna** — och `M-85` har redan mätt att
86 % av bibliotekets 82 383 egenskaper inte ens deklarerar vilken storhet de
bär. Namnbryggan hade lett till ett datablad som inte kan svara på frågan.

Det söket kan göra ärligt är att sluta svara `0 träffar` och ingenting mer.
Noll träffar på ett namn säger nu att biblioteket namnger komponenter med
tillverkarnas produktnamn, pekar på `family`, `manufacturer`, `min_reach_mm`
och `library_overview` — och skriver ut att svaret **inte** säger att
komponenten saknas, bara att namnet inte finns. Det är samma hållning som
`catalog_item`, som svarar `found=false` med **verkliga** alternativ i stället
för en gissad sökväg. Det ändrar inget tal i den här mätningen, och det ska
det inte heller: ett `SAKNAS` förblir ett `SAKNAS`.

## 7. Före och efter, samma korpus och samma domare

`M-119`:s hela frågekorpus kördes en gång till, längs samma väg (underprocess
mot `slaupp.py`) och genom samma domarregler. **Men repot är inte detsamma.**
Kö E:s commit `c0caa6d` — *"E3: reparationer enligt M-119"* — landade mellan de
två körningarna och stängde fem av `M-119`:s andra hål. Talen nedan är därför
två sessioners arbete, och raden om vilken som är vems står under tabellen.
Att skriva ut den är inte artighet; en mätning som tar åt sig av en annans
lagning mäter fel sak.

| frågeslag | körda före → efter | SVAR före | SVAR efter |
|---|---|---|---|
| `S1_api_namn` | 238 → 238 | 201 (84,5 %) | 230 (96,6 %) |
| `S2_typyta` | 63 → 63 | 63 (100 %) | 63 (100 %) |
| `S3_konstant` | 21 → 21 | 0 (0 %) | 21 (100 %) |
| `S4_bank_uri` | 75 → 75 | 75 (100 %) | 75 (100 %) |
| **`S5_bibliotek`** | 75 → 75 | **0 (0 %)** | **8 (10,7 %)** |
| `S5b_omtag` | 72 → 64 | 7 (9,7 %) | 0 (0 %) |
| `S6_egenskap` | 14 → 16 | 0 (0 %) | 0 (0 %) |
| `S7_signalkarta` | 94 → 94 | 0 (0 %) | 94 (100 %) |
| **`S8_geometri`** | 68 → 68 | **38 (55,9 %)** | **50 (73,5 %)** |
| `S8b_omtag` | 20 → 7 | 10 (50,0 %) | 0 (0 %) |
| `S9_standard` | 23 → 23 | 0 (0 %) | 23 (100 %) |
| `S10_grindregel` | 31 → 31 | 0 (0 %) | 27 (87,1 %) |
| `S11_vc_dok` | 20 → 20 | 13 (65,0 %) | 13 (65,0 %) |

### Vem gjorde vad, räknat per fråga som bytte klass

Varje fråga som bytte klass bär både sin gamla och sin nya regel, så
uppdelningen är mekanisk och inte en fördelning på känsla:

| bytet | antal | av |
|---|---|---|
| `S5` `R41_BIBLIOTEK_TOMT` → `R46_BIBLIOTEKSTRAFF` | **8** | **den här lagningen** |
| `S8` `R41_BIBLIOTEK_TOMT` → `R44_VARDE_MOT_SPEC` | **12** | **den här lagningen** |
| `S8` `R41_BIBLIOTEK_TOMT` → `R47_AVVIKER_FRAN_SPEC` | **1** | **den här lagningen** (`KR 10 R1100 sixx`: biblioteket 1 100 mm, banken 1 101) |
| `S7` `R26_FRITEXT_TOM` → `R28_FRITEXT_TRAFF` | 94 | kö E, `c0caa6d` |
| `S1` `R3_ANNAT_NAMN_AN_FRAGAT` / `R5` → `R8` | 29 | kö E |
| `S10` fyra regler → `R32_SOKTRAFF` | 27 | kö E |
| `S9` `R30_SOK_TOM` → `R32_SOKTRAFF` | 23 | kö E |
| `S3` `R5_UTAN_BESKRIVNING` → `R8` | 21 | kö E |
| `S6`/`S8b` `NOLLA` → `UTAN_STORHET` / `AVVIKER` | 4 | kö E (`E3a`: noll blir `None`) |

**Alla sex tysta fel `M-119` namngav är borta, och inget av dem är mitt.**
Fyra stängdes av `E3a` — nollan skrivs nu som `None` — och två av kö E:s
`S10`-väg. Det som är den här lagningens är `S5` och `S8`, och ingenting annat.

### Talet frågan gällde, per bankpost av 75

Nämnaren måste vara densamma åt båda hållen, och det är den bara om man räknar
per bankpost. `S5b` går inte att jämföra som procent — dess korpus *är* `S5`:s
misslyckanden.

| | före | efter |
|---|---|---|
| bankposter besvarade på **första** försöket | **0 av 75 (0 %)** | **8 av 75 (10,7 %)** |
| … efter omtaget också | 7 av 75 (9,3 %) | **8 av 75 (10,7 %)** |
| omtag som alls behövde ställas (`S5b`) | 72 | 64 |
| tysta fel i hela korpusen | 6 | **0** |

Det ser ut som en liten flytt och det är den, och den är rätt stor. **Taket är
8.** Femton av de 75 är beteckningar; sju av de femton finns inte i
biblioteket i någon stavning. `8 av 75` är alltså **8 av de 8 som gick att
hämta hem** — och de sju som inte finns svarar fortfarande `SAKNAS`, vilket är
det enda rätta svaret. Resten av nollan, 60 frågor, är inte ett söksfel.

Omtaget hämtar numera hem **noll**. Det är inte en försämring: alla sju det
tidigare hittade kommer nu på första försöket, plus en till. Ett andra försök
som inte behöver ställas är ett verktyg som svarade första gången.

## 8. Restrisken, räknad uttömmande

Spärren `MIN_BETECKNING = 2` och stegets ordning tar bort det mesta, men inte
allt, och resten ska stå med ett tal. Frågan ställdes uttömmande: **varje**
komponentnamn i biblioteket, med **varje** av de 148 andra tillverkarna som
förled — 472 564 frågor som alla ska ge noll.

| | |
|---|---|
| par som spärren stoppar innan de körs (beteckning < 2 tecken) | 1 184 |
| … deras felfrekvens om spärren tas bort | **55,7 %** |
| provade par | 472 564 |
| **falska träffar** | **85** (0,018 %) |

Fördelat på beteckningens längd: 19 av 592 vid två tecken, 15 av 4 144 vid
tre, 23 av 17 908 vid fyra, och därefter under 0,03 % genomgående. Det är inte
en tröskel som kan sättas bort — det är delsträngssökningens egen natur, som
verktyget deklarerar i sin parameterbeskrivning. Det som gör den nåbar här är
att förledet ströks, och det är därför förledet är ett **filter** och inte ett
bortkastat ord: utan filtret hade samma mätning gett fyra tiopotenser mer.

## LIMITS

* **Ett bibliotek, en bank, en installation.** VC 4.10:s eCatalog på den här
  maskinen: 3 201 komponenter, 149 tillverkare. Slutsatsen *"skiljetecken ger
  noll"* gäller det här paret av bank och bibliotek. Ett annat bibliotek, eller
  en modell som stavar `IRB2600_20_165`, faller på nivå 1 och tas av nivå 2 —
  och det är hela skälet till att nivå 2 levereras trots att den ger noll här.
* **`S5b` går inte att jämföra som procent.** Omtagskorpusen definieras av
  vilka `S5`-frågor som föll: färre fall ger färre omtag. `9,7 % av 72` och
  talet efteråt har olika nämnare. Det jämförbara talet är per bankpost av 75,
  och det är det som står i tabellen.
* **`S6` är härledd ur `S5`:s träffar** och växer därför när `S5` hittar mer.
  Dess frågor är inte samma frågor som `M-119` ställde, och andelen där mäter
  en annan sak efteråt än före.
* **Domaren är `M-119`:s, oförändrad.** Det är avsiktligt — annars vore före
  och efter inte jämförbara — men den bär sin egen lösa regel:
  `_samma_komponent` godtar ömsesidig delsträng från sex tecken, och hade
  godtagit `IRB 260` som svar på `ABB IRB 2600-20/1.65` om söket lämnat den.
  Söket gör inte det, och det är söket som är grinden. Domaren är det inte.
* **Restrisken är avgränsad, inte noll.** 85 av 472 564 par (0,018 %). Talet
  gäller den adversariella korpusen "rätt namn, fel tillverkarled"; den säger
  inget om hur ofta en modell faktiskt skriver ett fel tillverkarled.
* **"Finns inte i biblioteket" är ett påstående om NAMN.** `VDA KLT 4147` kan
  ligga där under ett namn min läsning inte känner igen. Jag har sökt i namn,
  i tillverkarfältet och i etiketterna — inte i geometri, inte i beskrivningar.
* **De 60 sondorden är mina.** Talet *"30 av 60 får någon träff"* är ett
  påstående, inte en mätning: det är ett **tak** för vad ett alias-skikt kunde
  nå, inte ett mått på hur många av dem som är rätt komponent. Kontrollen mot
  bankens kategori mot bibliotekets familj täcker bara 18 av de 60, för de
  övriga kategorierna har ingen motsvarighet i familjefältet.
* **Ingen modell var med.** Samma gräns som `M-119`: att en fråga får ett svar
  är inte att en modell hade ställt den, förstått svaret eller skrivit rätt kod
  av det.
* **Visual Components startades aldrig.** Biblioteket läses från disk. Att en
  fil heter `IRB 1200-5/0.9` är inte samma sak som att `findComponent` hittar
  den under det namnet i en körande VC — `M-85`:s gräns står oförändrad.
* **Efterledsrungan fyrar för EN fråga av 75.** Den hämtar hem `S5-055` och
  ingenting annat i den här korpusen. Dess spärr — minst ett sifferbärande ord
  måste stå kvar — är det som håller `FlexPicker` från att glida till en
  granne, och den spärren är provad, inte argumenterad.
* **Klassdelningen vilar på bankens `stampel`.** En felstämplad post hamnar i
  fel klass. De 15 klass-2-namnen är dessutom lästa med ögat och är alla
  riktiga beteckningar, och de 60 läser alla som svenska beskrivningar — men
  regeln är stämpeln, inte mitt öga.
* **Det uttömmande talet i §8 kommer inte ur den levererade koden.** 472 564
  sökningar genom `Katalog.sok` är för dyrt, så predikatet är omskrivet mot
  förberäknade normaliserade namn. Det är samma storhet, mätt med ett
  snabbare instrument, och därmed ett svagare instrument: en avvikelse mellan
  de två skulle inte synas. Talet som kommer ur den levererade koden är
  fixturens 3 201 par, och det är noll.
* **Efterledsrungans uttömmande bidrag är inte uppräknat.** §8:s 85 gäller
  tillverkarrungan. Efterledsrungan matchar rakt och kan bara träffa där en rak
  delsträng gör det, men jag har inte kört alla 472 564 paren genom den — den
  täcks av de 3 201 deterministiska paren och av det fall den redan fällts på.
* **Motprovets 3 180 av 3 201 är generöst räknat.** En fråga som ger över 40
  träffar besvaras med ett sammandrag i stället för rader (`BRED_FRAGA`, M-60),
  och de räknas som "hittade sig själv" utan att komponenten stod i svaret.
  De 2 721 som gav **en enda** träff är det hårda talet.
* **En annan skrivare la en LIMITS-stubb i den här filen medan den skrevs.**
  Tre rader, ersatta av det här avsnittet. Det är ytindelningens fel och inte
  låsets: låset skyddar indexet, inte innehållet.
* **Nollraden vid noll träffar ändrar inget tal.** Den gör svaret användbart,
  inte sant: ett `SAKNAS` är fortfarande ett `SAKNAS`, och det är avsikten.
