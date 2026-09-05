# Kontextbudgeten

Det ingen brukar speca och alla drabbas av: hur mycket som får plats, vad som
prioriteras bort först, och hur en stor scen och en lång körning kokas ned utan
att något viktigt tyst försvinner.

*beskriver:* `svc/vc_assist_svc/llm/budget.py`, `llm/kapning.py`,
`llm/ogontrim.py`, `llm/scenvy.py`, `llm/matt.py`, `llm/delar.py` (**byggda**,
fas 22), och binder mot det byggda sedan tidigare: `verktyg/kodmall.py`
(`MAX_POSTER`), `ext/vc_addon/vc_assist/protokoll.py` (`MAX_KROPP`),
`ext/vc_addon/vc_assist/oga_kontrakt.py`,
`ext/vc_addon/vc_assist/oga_provtagning.py`,
`svc/vc_assist_svc/harness/sammansattning.py`.

*grind:* `tests/protocol/kor_fas22_modellagret.py`, plus
`tests/enhet/test_kontextbudget.py`, `test_verktygssvarets_kapning.py` och
`test_ogontrimning.py`.

## Hur ett påstående i det här dokumentet ska läsas

Varje tal och varje regel bär en **härkomst**, och stämplarna är fyra:

| Stämpel | Betyder |
|---|---|
| **MÄTT** | ett tal ur en körning, med mätningens nummer |
| **KOD@HEAD** | står så i koden just nu, med fil och namn |
| **BELAGT** | följer av en annan spec eller en invariant, med hänvisning |
| **ANTAGET** / **PRELIMINÄR** | valt, inte mätt — med vem som ska mäta det |

**Ett antagande utan märkning är det som gör en spec farlig.** Ett omärkt tal
läses som ett mätt tal, och den som bygger vidare bygger på ingenting.

---

## Grundreglerna

**1. Budgeten hålls före anropet, genom att räkna — aldrig genom att fånga ett
fel från leverantören.** BELAGT (M-09): ett överskridande som upptäcks av
motparten är samma felklass som ett tyst syntaxfel i VC — systemet såg ut att
göra något och gjorde ingenting.

**2. Ingen trimning är tyst.** Varje bortprioritering ger en händelse `TRIMMAD`
i operatörens flöde (`24_samtalsloopen.md`, avsnitt 8) med vilken post som
trimmades och hur mycket. En trimning som ingen ser är en ändrad fråga som
grinden inte vet om.

**3. Bokföringen prövas åt båda hållen.** `budget.granska()` faller både på en
trimning utan händelse (`B1_TYST_TRIMNING`) och på en händelse utan trimning
(`B2_HANDELSE_UTAN_TRIMNING`). En bokföring som bara prövas åt ena hållet är
oprövad — och det är precis så en tyst trimning överlever.

**4. Fail-closed.** Ryms inte det skyddade kastas `Budgetfel`. Hellre inget
anrop än ett anrop där signalkartan eller ögats dom tystnat (S1).

---

## 1. Vad som får plats

Hela budgeten är `profil.kontext_tokens` ur modellprofilen
(`23_llm_granssnitt.md`). Andelarna nedan gäller den, oavsett hur stor den är.
KOD@HEAD: tabellen är `budget.POSTER`, och den är sluten.

| # | Post | Tak, andel | Får trimmas |
|---|---|---|---|
| 1 | Systemprompt B1–B3, B5–B7 | 5 % | **nej** |
| 2 | B4, avstängda verktyg med skäl | 1 % | ja, ned till en räknare |
| 3 | Verktygsschemat | 10 % | ja, via urval (`23`, avsnitt 3) |
| 4 | Uppgiften och planens aktuella steg | 5 % | **nej** |
| 5 | Signalkartan och deklarationsdelen, när turen skriver ST | 10 % | **nej** |
| 6 | Scenvyn | 15 % | ja, sammanfattas — avsnitt 5 |
| 7 | Ögats dom och rader | 10 % | ja, men bara hela rader utan fynd — avsnitt 6 |
| 8 | De senaste K verktygsresultaten | 25 % | ja, äldst först, sedan kapning — avsnitt 4 |
| 9 | Huvudboken över äldre anrop | 5 % | ja, äldst först |
| — | **Marginal för modellens svar** | resten, minst 14 % | — |

Summan av taken är 86 %. De återstående 14 % är svarsmarginal och får aldrig
ätas upp — ett svar som klipps mitt i en mening är en avhuggen rapport, och en
avhuggen rapport är aldrig ett godkännande (`41_ogat_kontrakt.md`, regel 2).
*Mekanik:* `profil.MINSTA_SVARSMARGINAL = 0.14`, och en profil vars
`svar_tokens_max` är större än marginalen avvisas vid start.

### Var talen kommer ifrån

| Post | Härkomst |
|---|---|
| 1 | **MÄTT 2026-09-05 (M-141)**: Systemprompten med alla förhandsregler (`forhandsregler.py`) är **1 735 tokens** (6 929 tecken). Den kräver ett kontextfönster på minst **34 700 tokens** för att rymmas inom 5 %-allokeringen. I fönster ≤ 32k överskrids budgeten (vid 8k med 424,2 %), och vid trunkering bakifrån trängs ögats hederlighets- och säkerhetsregler (F12, F15) ut först |
| 3 | **MÄTT 2026-09-05 (M-102)**: **122** registrerade verktyg ger **98 324 byte** OpenAI-schema, medel **805 byte**. Det är ungefär **32 775 tokens**, och postens tak på 10 % skulle alltså kräva ett fönster på **327 750 tokens**. Ingen profil vi känner har det. **Taket är därmed inte uppnåeligt utan urval** — se avsnitt 3 |
| 5 | **MÄTT (M-45)**: bankens största signalkarta är **13 signaler** (`bank/uppgifter/C-02.json`). Deklarationsdelen är alltså liten i alla scenarier vi har. Taket är satt för operatörens egna, större anläggningar |
| 6 | **MÄTT (M-45)**: bankens största scen är **9 komponenter**. Även här är taket satt för verkligheten utanför banken |
| 8 | **MÄTT 2026-09-05 (M-102)** över **207 riktiga verktygssvar** ur repots egna handlare: minsta **294 byte**, median **2 388 byte**, största **67 911 byte** (`type_surface` på `vcApplication`). Vid ett fönster på 8 000 tokens kapas **45 av 207**, vid 32 000 kapas **19**, vid 128 000 och 200 000 **noll** |
| 2, 4, 7, 9 | **PRELIMINÄRA.** Sätts av **M-29** |

### Vad ett token är i det här dokumentet, och varför det är två tal

**MÄTT FYND (M-102):** repot bar två olika omräkningar mellan text och tokens,
i två lager som inte kände varandra:

| Var | Antagande |
|---|---|
| det här dokumentet | **4 byte** per token |
| `harness/sammansattning.py` | **3,0 tecken** per token |

De är **inte samma storhet.** Byte och tecken skiljer sig så fort texten inte
är ren ASCII, och vår text är svensk: varje å, ä och ö är två byte i UTF-8. Ett
tak satt i byte och ett tak satt i tecken säger alltså olika saker om samma
sträng, och den som satte det ena trodde sig ha satt det andra.

*Mekanik (KOD@HEAD, `llm/matt.py`):* lagret mäter **båda**, räknar om genom
båda antagandena och **tar det högsta talet**. Fail-closed: underskattas tokens
skickas en begäran som inte får plats, och det är just det fel motparten
upptäcker åt oss. `Matt.spridning` rapporterar hur långt isär de två ligger —
läs det som *så mycket av det här talet är antagande*.

Båda talen är **ANTAGNA**. Ingen leverantörs tokenisering har räknat vår text,
och att läsa in en tokenisering vore att läsa in en leverantör (L1 i
`23_llm_granssnitt.md`). En profil som säger `tokenraknare = "uppskattad"` får
dessutom en marginal pålagd (`matt.MARGINAL_UPPSKATTAD = 5 %`, PRELIMINÄR,
M-28).

---

## 2. Vad som prioriteras bort, och i vilken ordning

Sluten, numrerad ordning. Trimningen går uppifrån och ned tills budgeten håller.
KOD@HEAD: `budget.TRIMSTEG`.

| Steg | Vad som går bort | Ersätts av |
|---|---|---|
| 1 | Huvudbokens äldsta rader, men **aldrig de fem senaste** | inget |
| 2 | Det äldsta hela verktygsresultatet | en huvudboksrad: `beskriv_anrop()` + utfall + kod |
| 3 | B4, listan över avstängda verktyg | `N verktyg avstangda; fraga om nagot saknas` |
| 4 | Ögats rader i sektioner där **ingen** rad bär ett fynd | en rad **utanför** ögats block, avsnitt 6 |
| 5 | Scenvyn kokas hårdare | avsnitt 5 |
| 6 | Verktygsschemat | semantiskt urval, `23` avsnitt 3 |
| 7 | Det **kvarvarande** verktygsresultatet kapas på poster | samma svar med `avkortad: true` och en rad om hur mycket — avsnitt 4 |
| 8 | Räcker det fortfarande inte | **turen delas** — `24_samtalsloopen.md`, avsnitt 7 |

**Steg 7 är nytt i fas 22, och det är ett svar på en fråga specen inte hade.**
Den gamla ordningen hoppade från "släpp det äldsta resultatet" direkt till
"dela turen", och lämnade därmed frågan *vad händer när ETT verktygssvar är
större än hela sin post?* obesvarad. Ett lager som inte svarar på den frågan
gör i praktiken det tystaste valet: skickar ändå, och låter motparten kapa.
Steg 7 kapar i stället **på poster**, högljutt, och aldrig på tecken.

### Vad som aldrig trimmas

| Aldrig bort | Skäl |
|---|---|
| B1–B3, B5–B7 | vad systemet är, vad modellen inte får, vilket läge maskinen är i. Utan B5 resonerar modellen om en brygga som kanske ligger nere |
| Uppgiftstexten och planens aktuella steg | det turen ska göra |
| Signalkartan när turen skriver ST | tas den bort **hittar modellen på taggnamn**. Det är precis felklassen `F3`, och den är mekaniskt borttagen bara så länge kartan finns i prompten (I10) |
| Ögats **domsrad**, `EYES v<n>`, `TEMPLATE`, `RUN` | I1 |
| Varje ögonrad som bär ett **fynd** | det är åtgärdsunderlaget |
| Hela `HONESTY`-sektionen | dess frånvaro går inte att skilja från att den aldrig kördes |
| Hela `LIMITS`-sektionen | vad ögat **inte** ser. Grinden kräver sektionen (M-65 §6) och fas 17:s regel `Y12` kräver raderna i klartext |
| Den rad som bär en sektions **ytterläge** | en `MINDIST`-rad är ett avstånd; trimmas den minsta bort har man tappat just den storhet raden finns för att bära |
| Felnycklarna för turens fallna anrop | honesty-rewrite kräver dem (`23`, avsnitt 4) |
| `fel` och `felnyckel` i ett verktygssvar | avsnitt 4 |

*Mekanik:* skyddet ligger i **kod** och inte bara i data. `budget.Del.skyddad`
och `POSTER[...].far_trimmas` läses av varje trimsteg, och `budget.granska()`
faller med `B3_SKYDDAD_TRIMMAD` om en skyddad del ändå ändrats.

Steg 8 är det ärliga svaret när ingenting mer får trimmas. **Turen delas hellre
än att något ur listan ovan offras.**

### Grinden mot trimningen

L1, utan modell (`tests/enhet/test_kontextbudget.py`):

1. En konstruerad tur som med råge överskrider budgeten trimmas i exakt den
   ordning tabellen anger. Provet läser stegnumren ur `TRIMMAD`-händelserna och
   kräver att de är stigande.
2. Ingen post ur "aldrig bort" försvinner, oavsett hur trång budgeten är.
3. En budget som är så liten att även den skyddade delen inte ryms ger ett
   **fel**, inte en tyst trimning (S1). Trasig fixtur som **ska** fälla:
   ett fönster på 140 tokens där det skyddade är 133 och budgeten 121.
4. Varje trimning ger exakt en `TRIMMAD`-händelse. Både noll händelser med
   trimmat innehåll **och** en händelse utan trimning fäller provet.
5. **MÄTT (M-102):** över bankens 95 turer, med ett fönster på 32 000 tokens,
   gav trimningen **95 skemabeskärningar** och **40 resultatkapningar**, och
   **noll** turer behövde delas. Noll bokföringsfel.

---

## 3. Verktygsschemat: taket som inte längre går att hålla utan urval

**MÄTT 2026-09-05 (M-102).** Talet i den här tabellen är hela skälet till att
urvalsmaskineriet byggdes i fas 22 i stället för "den dag det behövs":

| Storhet | Vid specens skrivning | MÄTT 2026-09-05 |
|---|---|---|
| Registrerade verktyg | 21 | **122** |
| Varav `effect=write` | 8 | **53** |
| Verktygsschema, totalt | 11 074 byte | **98 324 byte** |
| Medel per verktyg | 527 byte | **805 byte** |
| Fönster som krävs för postens 10 %-tak | ~90 000 tokens | **327 750 tokens** |

`23_llm_granssnitt.md` skrev *"Urvalsmaskineriet byggs alltså inte nu"* vid en
kvot på 2 %. Kvoten är i dag **19 %** på ett fönster om 128 000 tokens.
**Båda** villkoren i specens egen tröskel är brutna: 122 > 100 verktyg, och
19 % > 10 % av fönstret.

Och ett tal till, som är det som binder i praktiken: **alltid-med-listan** —
de verktyg utan vilka modellen inte kan ta reda på var den är — är 28 verktyg
och **4 792 tokens**. Den ensam kräver ett fönster på **47 920 tokens** för att
rymmas under 10 %. Under det fönstret är posten över sitt tak från första
turen, och det är då den ärliga slutsatsen är att **taket är fel, inte urvalet**.

*Öppen punkt:* andelen 10 % är PRELIMINÄR (M-29) och den är satt mot en
verktygskatalog som var en sjättedel så stor. Talet ska mätas om, inte skruvas
på tills det ser grönt ut.

---

## 4. När ett enda verktygssvar är större än sin post

Det här avsnittet är fas 22:s tyngsta tillägg, och det finns därför att
frågan tidigare stod som **öppen fråga 3** i det här dokumentet.

### Den farliga formen är inte ett saknat svar

Den farliga formen är **ett kapat svar som ser helt ut.** Inte ett svar som
saknas, inte ett fel — ett svar där halva innehållet är borta och ingenting i
svaret säger det. Modellen läser då en halv scen som om den vore hela och drar
en slutsats om det som inte kom med.

**BELAGT, och redan gjort en gång i det här repot:** `slaupp.py` skivade
JSON-strängen på **tecken** och gav utdata som var läsbar för ett öga och
oparsbar för allt annat. Provet står kvar
(`tests/enhet/test_slaupp.py::test_kapning_ger_giltig_json`) och skälet står i
`komponentdatablad.py`: *"Kapa på ANTAL POSTER, aldrig mitt i en struktur."*

Den varianten skriker åtminstone. Den **tysta** varianten — kapa på tecken och
sedan laga sluttecknen så att strängen parsar igen — är samma fel utan larmet.

### Tre regler, och de är mekaniska

**R1. Kapa på POSTER, aldrig på tecken.** Vilka fält som är listor läses ur
verktygets **deklarerade** `returns`-schema (KOD@HEAD, `kapning.listfalt`),
inte ur en gissning om nycklarna. Det som inte är en deklarerad lista rör
kapningen aldrig. Största listan töms först, en hel post i taget.

**R2. Varje kapning säger hur mycket.** Det kapade svaret bär `avkortad: true`,
`utelamnade` per fält och en rad i klartext som säger att det var
**kontextbudgeten** och inte verktyget som kapade. Ett svar som inte säger vad
det utelämnade ser uttömmande ut, och det är samma tysta lögn som ett utelämnat
fält.

**R3. Det som bar felet kapas aldrig.** `fel` och `felnyckel` ligger i
**kuvertet** (`kapning.Verktygssvar`), inte i innehållet, och kapningen rör
bara innehållet.

Regel 3 är **strukturell med flit.** Ett alternativ hade varit att leta
felbärande fält med en **ordlista** över nyckelnamn (`fel`, `error`,
`avkortad`). En sådan lista fyrar på fel storhet så fort ett verkligt fält
heter `felmarginal_mm` eller en komponent heter `Felsokningsstation` — och det
är exakt den felklass `M-95` mätte i ärlighetsgrindens `NEKANDE`-lista. Provet
`test_ett_falt_som_HETER_nagot_med_fel_i_ar_inte_ett_fel` håller regeln på
plats.

### När inte ens ett tomt svar ryms

Då skickas en **hänvisning**, aldrig en prefix:

```
{"for_stort": true, "byte": 67911, "tak_byte": 6000, "avkortad": true,
 "kaprad": "svaret fran type_surface ar 67911 byte och kontextens tak ar
            6000. INGENTING av innehallet skickades. Gor ett smalare anrop."}
```

En prefix av en JSON-struktur är den farliga formen. En hänvisning säger i
klartext att ingenting av innehållet kom med, och det är ett svar modellen kan
handla på: smalna av anropet. **MÄTT (M-102):** vid ett fönster på 8 000 tokens
blev **1 av 207** riktiga svar en hänvisning; de övriga 44 kapade rymdes efter
kapning.

### Ingen kapning av en kapning

`kapning.kapa()` kastar `Kapfel` om det som ska kapas redan är en kapning. Två
led av grovhet ser likadana ut som ett led, och förlusten går inte längre att
mäta. Det är samma mekanism som gör en cache farlig — tidsvinsten och
kvalitetsförlusten kommer ur samma steg, och bara det ena syns.

### De fyra mekaniska kontrollerna

`kapning.granska()` prövar ett svar för sig, `granska_par()` prövar det mot
råvaran:

| Kod | Faller på |
|---|---|
| `K1_OGILTIG_JSON` | innehållet går inte att parsa tillbaka |
| `K2_SER_HELT_UT` | svarets **egen** räkning stämmer inte med listans längd, eller det som skickades är mindre än råvaran utan att säga det |
| `K3_TYST_KAPNING` | `avkortad` är satt men svaret säger inte hur mycket |
| `K4_FEL_TAPPAT` | råvaran bar ett fel och det som skickades gör det inte |
| `K5_KAPNING_AV_KAPNING` | källan är själv en kapning |

### Fältet `antal` bär två storheter — MÄTT FYND

Vid mätningen över de 207 riktiga svaren föll granskningen på ett riktigt
verktyg, och felet låg i **granskningen**:

| Verktyg | `antal` betyder |
|---|---|
| `list_components`, `search_api`, `list_interfaces`, … | hur många poster som står i listan |
| `search_installed_library` | hur många träffar som **finns**; `visade` är hur många som står i listan |

Samma namn bär alltså två storheter. En kontroll som läser `antal` som den ena
anklagar det andra verktyget i onödan — och en kontroll kalibrerad åt det andra
hållet skulle **missa en verklig kapning** i alla de övriga verktygen. Det är
det vanliga fallet som döljer felet.

*Mekanik:* granskningen läser `visade` när det finns och `antal` annars, och
uppdelningen står utskriven i koden i stället för gissad
(KOD@HEAD, `kapning.FALT_VISADE`). Provet
`test_faltet_antal_bar_tva_storheter_och_granskningen_vet_det` håller båda
riktningarna.

*Öppen punkt (skuld):* två konventioner för samma fältnamn i samma register är
en glidning som borde lagas i verktygslagret, inte hanteras i läsaren. Det är
inte gjort.

### Hur mycket av ett svar går ens att kontrollera?

**MÄTT (M-102):** av 207 riktiga svar bär **19** sin egen räkning (ett enda
deklarerat listfält plus `antal`/`visade`). För de övriga **188** går en
kapning **inte** att upptäcka ur svaret ensamt — bara genom jämförelse med
råvaran.

Följden är en regel: **kapning sker bara i `kapning.kapa()`, där råvaran finns
kvar.** Ett lager som kapar någon annanstans kan inte bevisa att det inte ljög.

### Grinden

1. Svep över alla 207 riktiga svar med ett tak som tvingar fram en kapning:
   varje kapat svar ska parsa, bära `avkortad: true` och passera både
   `granska` och `granska_par`. **MÄTT: 0 anmärkningar.**
2. Kontrollen åt andra hållet: inget **helt** svar får anmärkas. **MÄTT: 0 av
   207.**
3. Tre trasiga fixturer, var och en med sin kod: `A` halva listan borta med
   räkningen kvar (`K2`), `B` klippt på tecken (`K1`), `C` internt konsistent
   men kort (`K2` mot råvaran).
4. Ett för stort svar som **föll** måste behålla `FELNYCKEL`-raden och feltexten.

---

## 5. Scendata när scenen är stor

### Varför `MAX_POSTER = 500` finns, och vad den inte löser

**KOD@HEAD**, `verktyg/kodmall.py`: bryggans kropp får vara högst
`MAX_KROPP = 1 048 576` byte (`protokoll.py`, ur `31_brygga_protokoll.md`). En
post ur `list_components` är omkring 200 byte JSON, så 500 poster blir cirka
100 kB — en tiondel av taket, med marginal för att posterna växer.

Verktyget svarar **alltid** `"avkortad": true` när det klipper, så en för låg
gräns syns i svaret i stället för att tyst försvinna (I3).

**MÄTT 2026-09-05 (M-102):** **38** av registrets verktyg klipper en lista i
sin genererade kod, och **alla 38** deklarerar `avkortad` i sitt
`returns`-schema. Noll verktyg klipper utan att säga det. Provet
`test_inget_verktyg_klipper_utan_att_deklarera_avkortad` håller talet, och det
har en trasig fixtur: samma domare mot ett schema utan `avkortad`.

**Det taket är transportens, inte kontextens.** 500 komponenter à 200 byte är
cirka 100 kB, alltså ungefär **25 000 tokens** (*ANTAGET* 4 byte/token). På en
profil med 128 000 tokens är det 20 % — mer än hela scenvyns tak på 15 %, och
det för en enda listning. Kontexten behöver alltså en **strängare** gräns än
transporten.

### Den strängare gränsen

| Storhet | Värde | Härkomst |
|---|---|---|
| `SCEN_FULL_MAX` | **60 komponenter** | *PRELIMINÄR, sätts av M-29.* Valt så att **ingen** bankuppgift någonsin sammanfattas: bankens största scen är 9 komponenter (MÄTT över 51 uppgifter, M-45). En bänk som mäter sammanfattaren i stället för modellen mäter fel sak |
| `EGENSKAPER_FULL_MAX` | **40 egenskaper per komponent** | *PRELIMINÄR, M-29* |

Under gränsen: **hela listan går fram**, ordagrant som verktyget lämnade den.
*Mekanik:* `scenvy.sammanfatta()` returnerar då **samma objekt**, så att en
kontroll kan se skillnad på "sammanfattad" och "gick fram hel".

### Över gränsen: sammanfattningens form

Fyra regler, i ordning.

1. **Arbetsmängden går fram hel.** Varje komponent som planens aktuella steg
   namnger, plus varje komponent som är kopplad till någon av dem
   (`list_connections`). De namnen ska modellen kunna använda som argument.
2. **Resten blir räkningar per kategori.** `Category` finns redan i
   `list_components` svar (KOD@HEAD, `_KOMPONENTPOST`). Räkningarna täcker
   **alla** komponenter, också de visade, så att summan är scenens storlek.
3. **En rad säger vad som utelämnades och efter vilken regel:**
   `N av M komponenter visas: planens och deras kopplade. Anvand
   find_component for de ovriga. Kallan ar <kalla_id>.`
4. **`avkortad` propageras ordagrant.** Sa verktyget att listan klipptes ska
   modellen se det, och sammanfattningen lägger till att scenen kan innehålla
   fler komponenter än den såg. Att svälja `avkortad` i en sammanfattning vore
   att göra fail-closed till fail-open.

### Regeln som gör sammanfattningen ofarlig

**Ett namn som turen behöver får aldrig sammanfattas bort.** Sker det hittar
modellen på ett namn, och det är exakt den felklass hela kunskapsindexet finns
för att stänga (I9, `46_kunskapsindex.md`).

Därför är regel 1 formulerad som en **skyldighet mot planen**, inte som en
relevansbedömning. Sammanfattaren bedömer ingenting — den läser komponentnamnen
ur plannodernas `args` (`22_planeringslagret.md`, nodschemat) och följer
kopplingsgrafen **ett** steg därifrån. Ett steg och inte två, därför att
"kopplad till planens komponenter" är en mekanisk fråga medan "relevant för
planen" inte är det.

### Ingen sammanfattning av en sammanfattning

Varje sammanfattning bär `ur_kalla` för det **råa** verktygsresultat den kom ur.
En sammanfattning vars källa är en annan sammanfattning kastar
(KOD@HEAD, `scenvy.sammanfatta`). Skälet är detsamma som för kapningen: två led
av grovhet ser likadana ut som ett led.

### Grinden

| Kod | Faller på |
|---|---|
| `S1_NAMN_BORTA` | ett namn turen använder saknas i den sammanfattade vyn |
| `S2_AVKORTAD_SVALD` | verktyget sa `avkortad` och vyn gör det inte |
| `S3_KATEGORIER_SUMMERAR_INTE` | räkningarna summerar inte till scenens storlek |
| `S4_SAMMANFATTNING_AV_SAMMANFATTNING` | källan är själv en sammanfattning |
| `S5_UTAN_RAD` | vyn säger inte vad som utelämnades |

Trasig fixtur: en scen med **200** komponenter där planen namnger 3. Provet
kräver att de 3 plus deras kopplade finns hela, att raden om utelämnandet
finns, och att kategorierna summerar till 200.

*Öppen punkt:* över bankens 51 uppgifter går regeln **inte** att mäta, därför
att ingen bankscen är över gränsen — den största är 9 komponenter. Talet
"noll fall där ett namn saknades" är alltså mätt på konstruerade scener, inte
på banken. Det står här som skuld, inte som ett tal.

---

## 6. Ögats tidsserie till modellen

### Den bärande regeln

**Domen är auktoritativ. En sammanfattning får aldrig bli ett andra omdöme.**

Därför: det modellen ser av ögat är **ögats egen text, ordagrant**. Ingen
omformulering, ingen omräkning, ingen omsortering, ingen avrundning.
Grinden gör likadant (`guldgrind.py`: parsar ögats utdata, räknar aldrig om ett
mått), och skälet är en mätt incident i källprojektet där en omimplementerad
positionsdom underkände 2 av 4 medan ögat visade 4 av 4 (I1).

*Mekanik:* `ogontrim` arbetar på **originalets rader** och plockar bort hela
rader. Den renderar aldrig om rapporten. Att läsa och rendera om vore redan en
omskrivning: `oga_kontrakt.Rapport.text()` formaterar `RUN`-raden med sin egen
precision, och en rapport som gått genom en omrendering är inte längre
ordagrant ögats.

### Serien går aldrig till modellen

| Storhet | Värde | Följd |
|---|---|---|
| Provtakt | **20,0 Hz**, kvot simtid/väggtid 1,000 (M-08) | — |
| `C-01`, uppvärmning | **300 s** (MÄTT, `bank/uppgifter/C-01.json`) | 6 000 rader bara i uppvärmningen |
| `C-01`, mätfönster | en simulerad timme | **72 000 rader** |
| En rad i `eyes.json` | poser, leder, minimiavstånd, signaler, PLC-variabler, statistik | tiotals megabyte för en full körning |

Redan bryggan vet detta: `eyes_stop` lägger med serien i svaret bara när den
ryms under **halva** kroppstaket, alltså 524 288 byte, annars går bara sökvägen
(KOD@HEAD, `pump._op_eyes_stop`).

Serien är alltså **underlag för felsökning**, aldrig kontext. Att lägga rader i
prompten vore dessutom att bjuda in modellen att bilda ett andra omdöme om en
dom som redan är fälld (I11).

### När ögats rapport ändå är för lång

Rapporttexten är begränsad till sin form, utom i sektioner som växer med
förloppet: `TIMING` (en `EDGE`-rad per flank), `SAFETY` (en `MINDIST`-rad per
bevakat par) och i v2 även `SEQUENCE` (en `STEP`-rad per steg och cykel).

Trimningen har fyra regler och de är hårda:

1. **Endast hela rader tas bort**, aldrig delar av en rad.
2. **Endast rader ur sektioner där ingen rad bär ett fynd.** En sektion med en
   enda avvikelse går fram hel.
3. **Första och sista raden i varje radgrupp står kvar**, plus den rad som bär
   gruppens ytterläge när en sådan är deklarerad. I dag är `MINDIST` den enda:
   raden är ett avstånd i millimeter, och det minsta avståndet är hela skälet
   att sektionen finns. Trimmas den bort ser det som står kvar ut som en
   tryggare körning än den var.
4. **Noteringen läggs utanför ögats block**, som en rad tjänsten själv skriver:
   `198 EDGE-rader utelamnade ur SECTION TIMING, alla utan fynd; 2 star kvar`.

Regel 4 är inte kosmetisk. Ögats grammatik läses byte för byte, och en
inskjuten rad **inuti** blocket skulle göra rapporten oläsbar för läsaren i
`oga_kontrakt.las()` — den kastar `Kontraktsfel` på ett okänt nyckelord i en
känd sektion. En sammanfattning som gör domen oläsbar är värre än ingen
sammanfattning.

### Hur "är raden OK?" avgörs — och varför inte med en ordlista

Det här är den enda plats i modellagret där en ordlista avgör något, och därför
är den skriven som den är.

Den naiva vägen är `"OK" in rad`. Den fyrar på **fel storhet** i minst tre
verkliga former:

| Rad | Vad den naiva domaren gör |
|---|---|
| `MINDIST OK_ROBOT+STANGSEL 412.000mm t=1.200s` | "OK" ligger i ett **parnamn**; raden har ingen dom alls. Domaren trimmar en säkerhetsrad |
| `STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s` | "OK" ligger i ett **signalnamn** och radens dom är `MISSING`. Domaren trimmar ett **fynd** |
| `EDGE ST100_STA_DONE RISE t=0.500s` | raden bär ingen dom men är heller inget fynd — den **får** trimmas, och då ska tidsspannet finnas kvar |

Det är samma felklass som `M-94`, `M-95` och `M-98` mätte tre gånger i
harnessens `NEKANDE`-lista: **en lista som bär två storheter döljer felet i det
vanliga fallet.**

*Mekanik:* lagret frågar **grammatiken**. `oga_kontrakt.RADER` har ett mönster
per radsort, och i de mönster som bär en dom ligger domen i en egen
alternativgrupp. `ogontrim.status()` läser **den gruppen** ur mönstrets egen
matchning. Vilka ord som är domsord kommer också ur kontraktet (`_FYNDORD`,
`_OSAKERORD`) plus de fem godkännandeorden nedan. Ingen ny handskriven ordlista
införs.

En rad **utan** domsgrupp har ingen dom, och svaret är då "vet inte" — vilket
är fail-closed: en rad utan känd dom räknas aldrig som godkänd när frågan är
*får den tas bort som OK?*. Och grupper som `(RISE|FALL)` eller `(RUN|PRIOR)`
ser ut som domsgrupper men är det inte, därför att orden inte står i
kontraktets domsordförråd.

De fem värden som betyder "inget att åtgärda": `OK`, `none`, `IN_TARGET`,
`RIGID`, `FORMED`.

### Vad som aldrig tas bort ur ögats text

| Aldrig bort |
|---|
| `EYES v<n>`, `TEMPLATE` och `RUN` |
| `EYES VERDICT`-raden |
| Varje rad vars dom **inte** är ett av de fem godkännandevärdena |
| Hela `HONESTY`-sektionen, även när allt är OK |
| Hela `LIMITS`-sektionen |
| Raden som bär en sektions ytterläge |

`HONESTY` står kvar hel därför att dess frånvaro inte går att skilja från att
den aldrig kördes, och en hederlighetsgrind som ser ut att ha kört utan att ha
gjort det är den farligaste sortens tystnad (S2). `LIMITS` står kvar därför att
den säger vad ögat **inte** ser; en rapport utan den är aldrig guld (M-65 §6).

### När modellen behöver mer än ögat säger

Då är svaret **inte** att lämna ut rader. Svaret är att utöka ögats grammatik
och höja `EYES_VERSION`, med grinden uppdaterad i samma commit
(`41_ogat_kontrakt.md`). Ögat säger det ögat kan säga; behöver vi mer ska ögat
mäta det, inte modellen räkna ut det.

### Grinden

| Kod | Faller på |
|---|---|
| `O1_DOM_BORTA` | domsraden eller huvudraden saknas |
| `O2_FYND_BORTA` | en rad med ett fynd, eller en sektions ytterlägesrad, togs bort |
| `O3_SKYDDAD_SEKTION` | något ur `HONESTY` eller `LIMITS` togs bort |
| `O4_OMSKRIVEN_RAD` | en rad står i det skickade men inte i ögats egen text |
| `O5_NOTIS_I_BLOCKET` | en notering lades inuti blocket |
| `O6_OLASBAR` | det skickade går inte längre att läsa som en ögonrapport |

**MÄTT (M-102):** bankens **nio** riktiga ögonrapporter är 443–868 byte och
trimmas inte alls under ett tak på 10 000 byte. En lång rapport (200 `EDGE` och
40 `MINDIST`) går från **9 606 till 1 169 byte**, med två noteringar utanför
blocket, och den minsta `MINDIST`-raden står kvar. Den naiva domaren skulle ha
trimmat **15** rader som vår domare behåller.

*Öppen punkt:* ingen lång körning är gjord. Den långa rapporten är byggd med
ögats egen skrivare, inte mätt ur en simulering. Att `EDGE` och `MINDIST` växer
som antaget är alltså **ANTAGET**.

---

## 7. Långa körningar utan att historiken sväller

### Historiken är inte tillståndet

Tillståndet ligger i arbetsordern, scenen och kön (`24_samtalsloopen.md`,
avsnitt 7). Historiken är en **bekvämlighet** och får därför kastas.

### Inom en tur: rullande fönster

| Storhet | Värde | Härkomst |
|---|---|---|
| `K_HELA_RESULTAT` | **8** verktygsanrop med sitt fulla resultat | Valt mot `RUNDOR_MAX = 10` (`23`, avsnitt 6) med två rundors marginal: i en **normal** tur kastas alltså ingenting alls, och trimningen börjar först i turer som redan slagit i sitt eget tak. *PRELIMINÄR i övrigt, M-29* |
| `HUVUDBOK_MINST` | **5** rader | 25:s egen steg 1: huvudbokens fem senaste rader trimmas aldrig |

Äldre anrop ersätts av en **huvudboksrad**, skriven av tjänsten:

```
list_components(name_contains='ST010')  ->  ok, 4 poster
connect(component='CNV1', interface='Out', other='STP1', other_interface='In')  ->  FEL composition/E_EXEC
```

Raden byggs ur `Verktyg.beskriv_anrop()` (KOD@HEAD) plus utfallet. Den är
**append-only** och skrivs aldrig om — en omskriven huvudbok är ett andra
omdöme om vad som hände.

### Mellan turer: nästan ingenting bärs vidare

| Bärs vidare | Bärs inte vidare |
|---|---|
| Arbetsordern | Modellens tidigare svarstexter |
| Huvudboken | Modellens resonemang |
| Scenfingeravtrycket | Gamla verktygsresultat |
| Senaste ögondom, ordagrant | Ögats serie |

Allt som inte bärs vidare **läses om ur sin auktoritet**. Det är billigt: tur
och retur mot bryggan har median **9,91 ms** och värsta av 20 på **13,45 ms**
(M-03). Att läsa om scenen kostar millisekunder; att resonera om en gammal scen
kostar en felaktig leverans.

### Budgetrapporten per tur

Varje tur loggar hur budgeten faktiskt gick åt. KOD@HEAD: `budget.Plan.rapport()`.

| Fält | Varför |
|---|---|
| tokens per post 1–9 i tabellen i avsnitt 1 | annars går taken inte att sätta |
| **vilka poster som ligger över sitt tak** | det är detta som *binder* |
| antal `TRIMMAD`-händelser, per post | visar vilket tak som binder i praktiken |
| om turen delades, och vid vilket steg | kostnaden för ett för litet tak |
| tokens totalt in | bänkens tal, `80_bank.md` |

**Ett lager utan den rapporten går inte att ställa in.** Talen i avsnitt 1 är
preliminära just därför att rapporten ännu inte körts mot en riktig modell;
M-29 är den mätning som gör dem till mätta tal.

---

## 8. Sammanfattning: de sex regler som bär

1. **Räkna före, aldrig fånga efter.** Budgeten hålls med adapterns egen
   räknare (A4 i `23_llm_granssnitt.md`), och med det **högsta** av de två
   tokenantagandena.
2. **Ingen tyst trimning.** Varje bortprioritering syns för operatören, och
   bokföringen prövas åt båda hållen.
3. **Kapa på poster, aldrig på tecken.** Ett kapat svar som ser helt ut är
   farligare än ett svar som saknas.
4. **Det som bar felet kapas aldrig.** Skyddet är strukturellt, inte en
   ordlista över fältnamn.
5. **En sammanfattning är aldrig en dom.** Ögats text går fram ordagrant, och
   noteringar läggs utanför dess block.
6. **En sammanfattning görs bara ur rådata.** Aldrig ur en annan
   sammanfattning.

---

## 9. Antaganden och öppna frågor

| # | Sak | Stämpel | Varför |
|---|---|---|---|
| 1 | 4 byte per token | **ANTAGET** | ingen leverantörs räknare är körd på vår text. Budgeten tar därför det högsta av 4 byte/token och 3,0 tecken/token. Ersätts av A4 och M-29 |
| 2 | 3,0 tecken per token | **ANTAGET** | samma sak, och de två är inte samma storhet (avsnitt 1) |
| 3 | Andelarna 1 %, 5 %, 10 %, 15 %, 25 % | **PRELIMINÄRA** | ingen tur med en riktig modell är mätt. Post 3:s andel är dessutom **bevisat för liten** för dagens register (avsnitt 3) |
| 4 | `SCEN_FULL_MAX = 60` | **PRELIMINÄR** | motivet är mätt (banken har som mest 9 komponenter), men gränsens läge är inte |
| 5 | `K_HELA_RESULTAT = 8` | **PRELIMINÄR** | motivet är `RUNDOR_MAX = 10`, inte en mätning av vad modellen behöver minnas |
| 6 | Att en post ur `list_components` är ~200 byte | **KOD@HEAD som antagande** | talet står i `kodmall.py` som grund för `MAX_POSTER`, men är inte mätt över en verklig scen |
| 7 | Att ögats rapporttext alltid ryms under 10 % | **ANTAGET** | `EDGE`, `MINDIST` och `STEP` växer med förloppet och **ingen lång körning är gjord** |
| 8 | Att scensammanfattaren aldrig tappar ett namn | **MÄTT PÅ KONSTRUERADE SCENER** | ingen bankscen är över gränsen, så regeln kan inte mätas på banken |
| 9 | Att `avkortad` räcker som signal | **DELVIS MÄTT** | 38 av 38 klippande verktyg deklarerar den, men bara 19 av 207 svar bär sin egen räkning; för de övriga krävs råvaran |

**Öppna frågor till operatören**

Inget är bestämt i någon av dem.

1. **Ska modellen se sina egna tidigare svar ordagrant, eller bara huvudboken?**
   Förslaget här är huvudboken, av två skäl: den är kort, och den är skriven av
   tjänsten och kan därför inte bära ett tidigare påstående vidare som om det
   vore bekräftat. Kostnaden är att modellen tappar sin egen formulering mellan
   turer.
2. **Hur stor scen ska systemet klara innan sammanfattning slår till?**
   `SCEN_FULL_MAX = 60` är valt mot banken. Vet operatören ungefär hur stora
   hans egna layouter är blir talet mätt i stället för antaget.
3. **Vad ska verktygsschemats tak vara?** 10 % går inte att hålla med 122
   verktyg. Två vägar finns: höja taket (och äta av något annat), eller låta
   urvalet vara hårdare än 40 verktyg. Här föreslås urvalet, därför att ett
   verktyg modellen inte ser kan den fråga efter, medan en tappad signalkarta
   inte går att fråga efter.
