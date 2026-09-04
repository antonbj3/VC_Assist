# Kontextbudgeten

Det ingen brukar speca och alla drabbas av: hur mycket som får plats, vad som
prioriteras bort först, och hur en stor scen och en lång körning kokas ned utan
att något viktigt tyst försvinner.

*beskriver:* `svc/vc_assist_svc/llm/budget.py` (obyggd), och binder mot det
byggda: `verktyg/kodmall.py` (`MAX_POSTER`), `ext/vc_addon/vc_assist/protokoll.py`
(`MAX_KROPP`), `ext/vc_addon/vc_assist/oga_kontrakt.py`,
`ext/vc_addon/vc_assist/oga_provtagning.py`.

## Grundregeln

**Budgeten hålls före anropet, genom att räkna — aldrig genom att fånga ett fel
från leverantören.** Ett överskridande som upptäcks av motparten är samma
felklass som ett tyst syntaxfel i VC (M-09): systemet såg ut att göra något och
gjorde ingenting.

**Och: ingen trimning är tyst.** Varje bortprioritering ger en händelse
`TRIMMAD` i operatörens flöde (`24_samtalsloopen.md`, avsnitt 7) med vilken post
som trimmades och hur mycket. En trimning som ingen ser är en ändrad fråga som
grinden inte vet om.

---

## 1. Vad som får plats

Hela budgeten är `profil.kontext_tokens` ur modellprofilen
(`23_llm_granssnitt.md`). Andelarna nedan gäller den, oavsett hur stor den är.

| # | Post | Tak, andel | Får trimmas |
|---|---|---|---|
| 1 | Systemprompt B1–B3, B5–B7 | 5 % | **nej** |
| 2 | B4, avstängda verktyg med skäl | 1 % | ja, ned till en räknare |
| 3 | Verktygsschemat | 10 % | ja, via urval (`23`, avsnitt 3) |
| 4 | Uppgiften och planens aktuella steg | 5 % | **nej** |
| 5 | Signalkartan och deklarationsdelen, när turen skriver ST | 10 % | **nej** |
| 6 | Scenvyn | 15 % | ja, sammanfattas — avsnitt 3 |
| 7 | Ögats dom och rader | 10 % | ja, men bara hela OK-rader — avsnitt 4 |
| 8 | De senaste K verktygsresultaten | 25 % | ja, äldst först |
| 9 | Huvudboken över äldre anrop | 5 % | ja, äldst först |
| — | **Marginal för modellens svar** | resten, minst 14 % | — |

### Var talen kommer ifrån

| Post | Härkomst |
|---|---|
| 3 | **MÄTT**: 21 registrerade verktyg ger 11 074 byte OpenAI-schema, medel 527 byte. Hela katalogen i `45_verktyg.md` plus `46_kunskapsindex.md` är omkring 70 verktyg ⇒ ~37 kB ⇒ ~9 000 tokens (*ANTAGET* 4 byte/token). På en profil med 128 000 tokens är det 7 %, alltså under taket med marginal |
| 5 | **MÄTT**: bankens största signalkarta är **13 signaler** (`bank/uppgifter/C-02.json`). Deklarationsdelen är alltså liten i alla scenarier vi har. Taket är satt för operatörens egna, större anläggningar |
| 6 | **MÄTT**: bankens största scen är **9 komponenter** (`C-02`). Även här är taket satt för verkligheten utanför banken |
| 1, 2, 4, 7, 8, 9 | **PRELIMINÄRA.** Ingen tokenräkning över verkliga turer finns. Sätts av **M-29** |

Summan av taken är 86 %. De återstående 14 % är svarsmarginal och får aldrig
ätas upp — ett svar som klipps mitt i en mening är en avhuggen rapport, och en
avhuggen rapport är aldrig ett godkännande (`41_ogat_kontrakt.md`, regel 2).

---

## 2. Vad som prioriteras bort, och i vilken ordning

Sluten, numrerad ordning. Trimningen går uppifrån och ned tills budgeten håller.

| Steg | Vad som går bort | Ersätts av |
|---|---|---|
| 1 | Huvudbokens äldsta rader, men **aldrig de fem senaste** | inget |
| 2 | Det äldsta hela verktygsresultatet | en huvudboksrad: `beskriv_anrop()` + utfall + kod |
| 3 | B4, listan över avstängda verktyg | `N verktyg avstangda; fraga om nagot saknas` |
| 4 | Ögats rader i sektioner där **varje** rad är OK | en rad **utanför** ögats block, avsnitt 4 |
| 5 | Scenvyn kokas hårdare | avsnitt 3 |
| 6 | Verktygsschemat | semantiskt urval, `23` avsnitt 3 |
| 7 | Räcker det fortfarande inte | **turen delas** — `24_samtalsloopen.md`, avsnitt 6 |

### Vad som aldrig trimmas

| Aldrig bort | Skäl |
|---|---|
| B1–B3, B5–B7 | vad systemet är, vad modellen inte får, vilket läge maskinen är i. Utan B5 resonerar modellen om en brygga som kanske ligger nere |
| Uppgiftstexten och planens aktuella steg | det turen ska göra |
| Signalkartan när turen skriver ST | tas den bort **hittar modellen på taggnamn**. Det är precis felklassen `F3`, och den är mekaniskt borttagen bara så länge kartan finns i prompten (I10) |
| Ögats **domsrad** | I1 |
| Varje ögonrad som **inte** är OK | det är åtgärdsunderlaget |
| Felnycklarna för turens fallna anrop | honesty-rewrite kräver dem (`23`, avsnitt 4) |

Steg 7 är det ärliga svaret när ingenting mer får trimmas. **Turen delas hellre
än att något ur listan ovan offras.**

### Grinden mot trimningen

L1, utan modell:

1. En konstruerad tur som med råge överskrider budgeten trimmas i exakt den
   ordning tabellen anger. Provet läser ordningen ur `TRIMMAD`-händelserna.
2. Ingen post ur "aldrig bort" försvinner, oavsett hur trång budgeten är.
3. En budget som är så liten att även den skyddade delen inte ryms ger ett
   **fel**, inte en tyst trimning (S1). Det är en trasig fixtur som **ska** fälla.
4. Varje trimning ger exakt en `TRIMMAD`-händelse. Noll händelser med trimmat
   innehåll fäller provet.

---

## 3. Scendata när scenen är stor

### Varför `MAX_POSTER = 500` finns, och vad den inte löser

**KOD@HEAD**, `verktyg/kodmall.py`: bryggans kropp får vara högst
`MAX_KROPP = 1 048 576` byte (`protokoll.py`, ur `31_brygga_protokoll.md`). En
post ur `list_components` är omkring 200 byte JSON, så 500 poster blir cirka
100 kB — en tiondel av taket, med marginal för att posterna växer.

Verktyget svarar **alltid** `"avkortad": true` när det klipper, så en för låg
gräns syns i svaret i stället för att tyst försvinna (I3).

**Det taket är transportens, inte kontextens.** 500 komponenter à 200 byte är
cirka 100 kB, alltså ungefär **25 000 tokens** (*ANTAGET* 4 byte/token). På en
profil med 128 000 tokens är det 20 % — mer än hela scenvyns tak på 15 %, och
det för en enda listning. Kontexten behöver alltså en **strängare** gräns än
transporten.

### Den strängare gränsen

| Storhet | Värde | Härkomst |
|---|---|---|
| `SCEN_FULL_MAX` | **60 komponenter** | *PRELIMINÄR, sätts av M-29.* Valt så att **ingen** bankuppgift någonsin sammanfattas: bankens största scen är 9 komponenter (MÄTT över 47 uppgifter). En bänk som mäter sammanfattaren i stället för modellen mäter fel sak |
| `EGENSKAPER_FULL_MAX` | **40 egenskaper per komponent** | *PRELIMINÄR, M-29* |

Under gränsen: **hela listan går fram**, ordagrant som verktyget lämnade den.

### Över gränsen: sammanfattningens form

Fyra regler, i ordning.

1. **Arbetsmängden går fram hel.** Varje komponent som planens aktuella steg
   namnger, plus varje komponent som är kopplad till någon av dem
   (`list_connections`). De namnen ska modellen kunna använda som argument.
2. **Resten blir räkningar per kategori.** `Category` finns redan i
   `list_components` svar (KOD@HEAD, `_KOMPONENTPOST`).
3. **En rad säger vad som utelämnades och efter vilken regel:**
   `N av M komponenter visas: planens och deras kopplade. Anvand
   find_component for de ovriga.`
4. **`avkortad` propageras ordagrant.** Sa verktyget att listan klipptes ska
   modellen se det. Att svälja `avkortad` i en sammanfattning vore att göra
   fail-closed till fail-open.

### Regeln som gör sammanfattningen ofarlig

**Ett namn som turen behöver får aldrig sammanfattas bort.** Sker det hittar
modellen på ett namn, och det är exakt den felklass hela kunskapsindexet finns
för att stänga (I9, `46_kunskapsindex.md`).

Därför är regel 1 formulerad som en **skyldighet mot planen**, inte som en
relevansbedömning. Sammanfattaren bedömer ingenting — den läser komponentnamnen
ur plannodernas `args` (`22_planeringslagret.md`, nodschemat) och följer
kopplingsgrafen därifrån.

### Ingen sammanfattning av en sammanfattning

Varje sammanfattning bär `kalla_id` för det **råa** verktygsresultat den kom ur.
En sammanfattning vars källa är en annan sammanfattning är ett linterfel.

Skälet: två led av grovhet ser likadant ut som ett led, och förlusten går inte
längre att mäta. Det är samma mekanism som gör en cache farlig — tidsvinsten
och kvalitetsförlusten kommer ur samma steg, och bara det ena syns.

### Grinden

1. Över bankens 47 uppgifter: **noll** fall där ett namn som turen använde
   saknades i den sammanfattade scenvyn. En miss ändrar regel 1; den är inte en
   ratt att skruva på.
2. Trasig fixtur: en scen med 200 komponenter där planen namnger 3. Provet
   kräver att de 3 plus deras kopplade finns hela, att raden om utelämnandet
   finns, och att kategorierna summerar till 200.
3. `avkortad: true` från verktyget måste synas i det som skickades. En fixtur
   där det sväljs ska fälla.

---

## 4. Ögats tidsserie till modellen

### Den bärande regeln

**Domen är auktoritativ. En sammanfattning får aldrig bli ett andra omdöme.**

Därför: det modellen ser av ögat är **ögats egen text, ordagrant**. Ingen
omformulering, ingen omräkning, ingen omsortering, ingen avrundning.
Grinden gör likadant (`guldgrind.py`: parsar ögats utdata, räknar aldrig om ett
mått), och skälet är en mätt incident i källprojektet där en omimplementerad
positionsdom underkände 2 av 4 medan ögat visade 4 av 4 (I1).

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

Rapporttexten är begränsad till sin form, utom i två sektioner som växer med
förloppet: `TIMING` (en `EDGE`-rad per flank) och `SAFETY` (en `MINDIST`-rad per
bevakat par).

Trimningen har tre regler och de är hårda:

1. **Endast hela rader tas bort**, aldrig delar av en rad.
2. **Endast rader ur sektioner där varje rad är OK.** En sektion med en enda
   avvikelse går fram hel.
3. **Noteringen läggs utanför ögats block**, som en rad tjänsten själv skriver:
   `12 EDGE-rader utelamnade, alla OK.`

Regel 3 är inte kosmetisk. Ögats grammatik läses byte för byte, och en
inskjuten rad **inuti** blocket skulle göra rapporten oläsbar för läsaren i
`oga_kontrakt.las()` — den kastar `Kontraktsfel` på ett okänt nyckelord i en
känd sektion. En sammanfattning som gör domen oläsbar är värre än ingen
sammanfattning.

### Vad som aldrig tas bort ur ögats text

| Aldrig bort |
|---|
| `EYES v<n>`-raden |
| `EYES VERDICT`-raden |
| Varje rad som **inte** är `OK` / `none` / `IN_TARGET` / `RIGID` / `FORMED` |
| Hela `HONESTY`-sektionen, även när allt är OK |

`HONESTY` står kvar hel därför att dess frånvaro inte går att skilja från att
den aldrig kördes, och en hederlighetsgrind som ser ut att ha kört utan att ha
gjort det är den farligaste sortens tystnad (S2).

### När modellen behöver mer än ögat säger

Då är svaret **inte** att lämna ut rader. Svaret är att utöka ögats grammatik
och höja `EYES_VERSION`, med grinden uppdaterad i samma commit
(`41_ogat_kontrakt.md`). Ögat säger det ögat kan säga; behöver vi mer ska ögat
mäta det, inte modellen räkna ut det.

### Grinden

1. **Byte-för-byte-provet.** Ta en känd ögonrapport med FAIL. Kör
   sammanfattningen. Kontrollera mekaniskt att domsraden och varje icke-OK-rad
   finns ordagrant i det som skickades. Saknas något: turen avbryts, inget
   skickas.
2. Trasig fixtur: en sammanfattare som formulerar om domsraden ska fälla provet.
3. En rapport där `HONESTY` trimmats bort ska fälla provet.
4. Ingen `eyes.json`-rad får förekomma i något utgående meddelande.
   *Kontroll:* provet söker efter seriens nyckelord (`"rows"`, `"mind"`,
   `"joints"`) i begäran.

---

## 5. Långa körningar utan att historiken sväller

### Historiken är inte tillståndet

Tillståndet ligger i arbetsordern, scenen och kön (`24_samtalsloopen.md`,
avsnitt 6). Historiken är en **bekvämlighet** och får därför kastas.

### Inom en tur: rullande fönster

| Storhet | Värde | Härkomst |
|---|---|---|
| `K_HELA_RESULTAT` | **8** verktygsanrop med sitt fulla resultat | Valt mot `RUNDOR_MAX = 10` (`23`, avsnitt 6) med två rundors marginal: i en **normal** tur kastas alltså ingenting alls, och trimningen börjar först i turer som redan slagit i sitt eget tak. *PRELIMINÄR i övrigt, M-29* |

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

Varje tur loggar hur budgeten faktiskt gick åt:

| Fält | Varför |
|---|---|
| tokens per post 1–9 i tabellen i avsnitt 1 | annars går taken inte att sätta |
| antal `TRIMMAD`-händelser, per post | visar vilket tak som binder |
| om turen delades, och vid vilket steg | kostnaden för ett för litet tak |
| tokens totalt in och ut | bänkens tal, `80_bank.md` |

**Ett lager utan den rapporten går inte att ställa in.** Talen i avsnitt 1 är
preliminära just därför att rapporten ännu inte finns; M-29 är den mätning som
gör dem till mätta tal.

---

## 6. Sammanfattning: de fyra regler som bär

1. **Räkna före, aldrig fånga efter.** Budgeten hålls med adapterns egen
   räknare (A4 i `23_llm_granssnitt.md`).
2. **Ingen tyst trimning.** Varje bortprioritering syns för operatören.
3. **En sammanfattning är aldrig en dom.** Ögats text går fram ordagrant, och
   noteringar läggs utanför dess block.
4. **En sammanfattning görs bara ur rådata.** Aldrig ur en annan
   sammanfattning.

---

## 7. Antaganden och öppna frågor

| # | Sak | Stämpel | Varför |
|---|---|---|---|
| 1 | 4 byte per token | **ANTAGET** | ingen räknare körd på vår text. Varje härledd tokensiffra i dokumentet bär det antagandet. Ersätts av A4 och M-29 |
| 2 | Andelarna 1 %, 5 %, 10 %, 15 %, 25 % | **PRELIMINÄRA** | ingen tur är mätt. De är valda så att de tre mätta posterna (verktygsschema, signalkarta, scen) ryms med marginal |
| 3 | `SCEN_FULL_MAX = 60` | **PRELIMINÄR** | motivet är mätt (banken har som mest 9 komponenter), men gränsens läge är inte |
| 4 | `K_HELA_RESULTAT = 8` | **PRELIMINÄR** | motivet är `RUNDOR_MAX = 10`, inte en mätning av vad modellen behöver minnas |
| 5 | Att en post ur `list_components` är ~200 byte | **KOD@HEAD som antagande** | talet står i `kodmall.py` som grund för `MAX_POSTER`, men är inte mätt över en verklig scen |
| 6 | Att ögats rapporttext alltid ryms under 10 % | **ANTAGET** | `EDGE` och `MINDIST` växer med förloppet och ingen lång körning är gjord |

**Öppna frågor till operatören**

1. **Ska modellen se sina egna tidigare svar ordagrant, eller bara huvudboken?**
   Förslaget här är huvudboken, av två skäl: den är kort, och den är skriven av
   tjänsten och kan därför inte bära ett tidigare påstående vidare som om det
   vore bekräftat. Kostnaden är att modellen tappar sin egen formulering mellan
   turer. Inget är bestämt.
2. **Hur stor scen ska systemet klara innan sammanfattning slår till?**
   `SCEN_FULL_MAX = 60` är valt mot banken. Vet operatören ungefär hur stora
   hans egna layouter är blir talet mätt i stället för antaget.
3. **Ska ett enskilt verktygsresultat som ensamt spränger sitt tak klippas, eller
   ska turen delas?** Här föreslås att verktyget själv klipper med `avkortad`,
   som det redan gör, och att tjänsten lägger en rad om det. Alternativet — att
   dela turen — är ärligare men dyrare.
