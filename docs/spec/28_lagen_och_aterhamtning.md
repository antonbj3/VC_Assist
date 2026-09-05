# Lägen och återhämtning

**beskriver:** `ext/vc_addon/vc_assist/pump.py`, `svc/vc_assist_svc/klient.py`,
`svc/vc_assist_svc/verktyg/utforare.py`, `ext/vc_addon/vc_assist/bridge_cmd.py`
**kontrakt:** `26_appen.md`, `27_operatorsflodet.md`, `31_brygga_protokoll.md`,
`90_invarianter.md`, `96_ingen_skuld.md`

Tillstånden, övergångarna, och vägen tillbaka. Byggt på det som är mätt om vad
som dödar bryggan och vad som inte går att laga inifrån.

---

## 1. Lägena

Sju lägen. Fyra av dem är egenskaper hos ett levande system snarare än rena
tillstånd, och det står utskrivet — en tillståndsmaskin som låtsas vara platt
när den inte är det döljer fel.

| Läge | Betyder | Hur tjänsten vet | Stämpel |
|---|---|---|---|
| **frånkopplad** | ingen anslutning öppen. Startläge, och läget efter ett medvetet `shutdown` | ingen socket | |
| **ansluten** | bryggan svarade på `ping` | `ping` gav `ok=true` inom `T_ping` | KOD@HEAD `_op_ping` |
| **simulering igång** | pumpen tickar | `sim` gav `kor=true`; dessutom **implicit** — svarar bryggan alls så tickar pumpen | **MÄTT M-08** |
| **provtagning pågår** | ögat samlar prov | `eyes_status` gav `aktiv=true` | KOD@HEAD `_op_eyes_status` |
| **kö väntar** | minst en post är `pending` eller `approved` | `ping.ko_vantande > 0` | KOD@HEAD |
| **degraderad** | bryggans tillstånd är okänt efter en timeout | `ping.degraded = true` | KOD@HEAD |
| **nere** | bryggan svarar inte, och gjorde det nyss | inget `ping`-svar inom `T_nere` efter att ha varit ansluten | |

Ett åttonde, **underläge**: `utan självstart`. Bryggan har nått taket 20
omstarter per minut och har slagit av sin egen självstart
(`pump.begar_omstart`). Läses ur `sim` som `keepalive=false`.

### 1.0 Två lägen till, och varför de är tillagda

De sju ovan räcker inte för en **visning**, och de två som saknas står här i
stället för att glida in i listan. Samma val som `forlopp.handelser` gjorde med
`TILLAGDA_SORTER`: ett tillägg till en spec'ad lista ska synas.

| Läge | Betyder | Hur tjänsten vet | Stämpel |
|---|---|---|---|
| **obestämt** | frågan gick inte att besvara ur det underlag som finns. Det är inte ett fall och inte ett arbete | avläsningen är äldre än `T_nere`, ligger i framtiden, eller bär bara en lyckad `connect()` | KOD@HEAD `aterhamtning.bild.lage_for` |
| **blockerad** | bryggan svarar inte, och orsaken är känd och ofarlig: en modal ruta står öppen i VC | bryggloggens sista rad är `modal oppen` | **ANTAGET** — se varningen nedan |

`obestämt` är I3 på visningens våning: *tystnad är aldrig ett godkännande.* Utan
ett eget ord för det blir varje fråga som inte gick att besvara antingen ett
grönt eller ett utelämnande, och båda är falska.

`blockerad` finns därför att §3.6:s undantag kräver det. Specen säger att en
öppen statusruta inte får bli `nere`; utan ett eget ord blev den i stället
`ansluten`, vilket är en lögn åt andra hållet.

> **Varning, och den ska stå kvar tills den är åtgärdad.** Raden `modal oppen`
> **finns inte i koden.** `grep -n "modal" ext/vc_addon/vc_assist/*.py` ger noll
> träffar 2026-09-05. Läget `blockerad` kan alltså inte fyras i dag, och att
> `messageBox` över huvud taget blockerar pumpen är härlett ur M-07:s
> `time.sleep`, inte mätt på en ruta. Både raden och mätningen väntar på
> **M-21**. Ytan skriver ut det som en permanent ovisshet i varje visning
> (`aterhamtning.yta.RACKVIDDEN`), i stället för att låtsas ha förmågan.

Undantaget har dessutom en **gräns**, och den är ny: efter `T_modal` går det
inte längre att skilja en ruta som står öppen från en brygga som dog bakom den.
Läget blir då `obestämt`, inte `blockerad` och inte `nere`.

| Storhet | Värde | Härkomst |
|---|---|---|
| `T_modal` | 300 s | **PRELIMINÄR.** Ingen mätning finns; sätts av M-21. Talet är valt så att en ruta en människa faktiskt läser hinner stängas |

### 1.1 Ordningen när flera gäller samtidigt

Panelens fält 7 visar **ett** ord. Företräde, uppifrån och ned:

```
nere  >  degraderad  >  provtagning pågår  >  kö väntar
      >  simulering igång  >  ansluten  >  frånkopplad
```

`utan självstart` visas alltid som ett tillägg, aldrig i stället för.

### 1.2 En TCP-anslutning är inte ett livstecken

Bryggan accepterar anslutningar **inuti `tick()`** (`pump._acceptera`), och
`tick()` körs bara av pumpen. Är pumpen död gör kärnans lyssningskö att
`connect()` ändå lyckas — handskakningen fullbordas av operativsystemet, inte
av bryggan — men inget svar kommer någonsin.

**Regel L-1.** Läget avgörs av ett **`ping`-svar**, aldrig av att en anslutning
gick att öppna. En tjänst som räknar en lyckad `connect()` som liv rapporterar
`ansluten` om en död brygga.

*Stämpel:* HÄRLEDD ur KOD@HEAD (`accept()` sker i `tick()`). Att kärnans
backlog beter sig likadant genom Wines winsock är **oprövat** och mäts i
**M-25**.

### 1.3 Tidsgränser

| Storhet | Värde | Härkomst |
|---|---|---|
| `T_ping` | 3,0 s | **PRELIMINÄR.** Mätt tur och retur: median 9,91 ms, värsta av 20 = 13,45 ms (M-03). 3 s är ~220 gånger det värsta mätta |
| `T_nere` | 3,0 s efter första uteblivna `ping` | **PRELIMINÄR**, samma härkomst |
| Undantag | ingen övergång till `nere` medan bryggloggens sista rad är `modal oppen` | se §3.6 |
| Omstartsspärr | ≥ 1,0 s mellan omstarter, högst 20 per minut | **PRELIMINÄR**, satt av M-13 |

### 1.4 Ordningen mellan DELSYSTEM är en annan fråga

§1.1 ordnar flera samtidiga lägen hos **ett** delsystem. Tre saker kan sluta
svara oberoende av varandra — bryggan, OpenPLC och modellen — och vilken av
dem som ska stå överst är en annan fråga med ett annat svar:

```
NERE > OBESTÄMT > BLOCKERAD > DEGRADERAD > FRÅNKOPPLAD
     > KÖ VÄNTAR > PROVTAGNING PÅGÅR > SIMULERING IGÅNG > ANSLUTEN
```

`nere` står först och inte `obestämt`: en känd död är det användaren kan göra
något åt. **Ingenting göms av valet** — varje delsystem står med sitt eget läge
i sitt eget block, alltid (regel Å2 i fas 23:s grind).

De två ordningarna får inte slås ihop. De svarar på olika frågor, och en
gemensam ordning skulle göra en av dem fel.

### 1.5 En avläsning åldras, och det är det enda som skiljer den från ett svar

Ett läge är en **slutsats om en tystnad**, aldrig ett fält. Slutsatsen dras ur
den senaste avläsningen och **läsarens** klocka, och en avläsning äldre än
`T_nere` bär inget läge alls — varken ett grönt eller ett rött.

Skälet är mätt två gånger i det här systemet, med två olika mekanismer och
samma form: ett tal som skulle åldras gjorde det inte.

| Mekanism | Utfall | Källa |
|---|---|---|
| ett hjärtslag räknades som framsteg | ARBETAR i **600 av 600** avläsningar av en körning där ingenting hände | M-64 |
| en läsare frös klockan vid bildens egen skrivtid | ARBETAR i **60 av 60** avläsningar av en körning vars skrivare dog före den första | M-93 |
| en avläsning återanvändes efter att den blivit gammal | ANSLUTEN i **60 av 60**; med läsarens egen klocka **3 av 60** | **M-103** |

**Regel L-0.** Åldern räknas mot den klocka som **läser**, aldrig mot den som
skrev. En härledning som fryser klockan bygger ett läge som självt säger
ANSLUTEN, och då är texten korrekt mot ett läge som är fel.

---

## 2. Övergångarna

| Från | Till | Utlöses av | Stämpel |
|---|---|---|---|
| frånkopplad | ansluten | tjänsten läser `~/vc_assist_token`, ansluter, `ping` svarar | |
| frånkopplad | frånkopplad | token saknas, port lyssnar inte, eller fel token ⇒ `E_AUTH` | KOD@HEAD |
| ansluten | kö väntar | ett `effect=write`-verktyg gav `exec_queue` | KOD@HEAD, I12 |
| kö väntar | simulering igång | `queue_approve` kvitteras, pumpen betar av posten nästa varv | KOD@HEAD `_beta_av_kon` |
| ansluten | provtagning pågår | `eyes_start` med en plan som namnger minst ett spårat objekt | KOD@HEAD |
| provtagning pågår | ansluten | `eyes_stop` returnerar sökväg, antal prov och takt | KOD@HEAD |
| ansluten | degraderad | en `exec` överskred `timeout_ms` | KOD@HEAD `_kor` |
| degraderad | ansluten | **en lyckad `exec`**, och bara det | KOD@HEAD |
| degraderad | degraderad | `queue_approve` avvisas med `E_BUSY` | KOD@HEAD |
| ansluten | nere | koden stoppade simuleringen: `createBehaviour(VC_SCRIPT)` eller `app.save()` | **MÄTT M-13** |
| ansluten | nere | operatören tryckte stopp i VC | **MÄTT M-08** — pumpen bor i simuleringen |
| ansluten | nere | VC avslutades ⇒ `ECONNRESET` | `31_brygga_protokoll.md` |
| nere | ansluten | **endast** genom `sim.reset()` + `startSimulation()` från kommandots scope, eller en VC-omstart | **MÄTT M-13** |
| ansluten | ansluten, `utan självstart` | 20 omstarter på en minut | KOD@HEAD `begar_omstart` |
| valfritt | frånkopplad | `shutdown` | KOD@HEAD |

### 2.1 Övergången som inte finns

**Bryggan kan inte återuppliva sig själv.** Tre vägar prövades, alla mätta
(M-13):

| Väg | Utfall |
|---|---|
| `startSimulation()` i skriptets `OnStop` | simuleringen går igen, men `OnRun` **återinträder inte** |
| `reset()` + `startSimulation()` i `OnStop` | mekaniken fungerar, `OnRun` återinträder ändå inte; utan spärr blir det en omstartsstorm, mätt till tusentals varv i sekunden |
| `vcSimulation.OnStartStop` i kommandots scope | fyrar **inte** på det stopp en scenändring orsakar |

Det som **fungerar** är en handlare registrerad i **kommandots** scope — utanför
den tasklet som dör — som gör `reset()` + `startSimulation()`, och som fyras av
ett `startSimulation()` från `OnStop`. Den vägen är byggd
(`bridge_cmd._koppla_startstopp`) och den täcker de fall där skriptmiljön
**inte** monteras ned. Den täcker **inte** de två mätta dödande operationerna.

**Regel L-2.** För `createBehaviour(VC_SCRIPT)` och `app.save()` finns ingen
väg tillbaka utan operatören. Systemet ska säga det i förväg, inte upptäcka det
efteråt.

---

## 3. Återhämtning per läge

### 3.1 frånkopplad

| Orsak | Vad operatören ser | Vad han gör |
|---|---|---|
| Tokenfilen saknas | *"`~/vc_assist_token` finns inte. Bryggan har aldrig startat i den här VC-sessionen."* + de tre grön-start-filerna med bock eller kryss | följer `27_operatorsflodet.md` §3, de fem tysta fällorna |
| Porten lyssnar inte | *"Ingenting lyssnar på 127.0.0.1:8901."* | kontrollerar bootloggen; **Linux:** kör `vc-stoppa.sh` om en gammal `wineserver` håller porten (**MÄTT M-13**). **Windows:** ingen `wineserver` finns — processen som håller porten är en kvarlevande `VisualComponents.Engine.exe`, läs ut den med `netstat -ano | findstr :8901` och avsluta det PID:et. **OPRÖVAT på Windows** (M-44) |
| `E_AUTH` | *"Tokenet är från en tidigare VC-session."* | tjänsten läser om filen automatiskt och försöker en gång till; lyckas det sägs det, det tystas inte |

### 3.2 ansluten

Inget att återhämta. Panelen visar `tick`, `begäran`, RTT och förmåga.

### 3.3 kö väntar

| Fall | Åtgärd |
|---|---|
| Poster står `pending` och ingen godkänner | panelen visar hur länge, per post. Systemet gör ingenting av sig självt |
| En post är `approved` men inte körd inom 100 ms medan `kor=true` | panelen visar `kö stillastående` och kontrollerar `sim` en gång till. Är simuleringen igång och posten ändå stilla är det ett fel som ska rapporteras (§6) |
| Kön full, `E_QUEUE_FULL` | 256 väntande poster. Operatören avvisar eller godkänner; systemet slänger aldrig en post själv |

### 3.4 degraderad

Läget betyder att bryggans tillstånd är **okänt** efter en timeout, inte att
den är trasig.

| Regel | Innebörd |
|---|---|
| `exec` är **inte** spärrad | den är vägen ut. En spärr här kunde aldrig öppnas igen, eftersom bara en lyckad körning rensar flaggan. Rättelsen står i `31_brygga_protokoll.md` |
| `queue_approve` **är** spärrad, `E_BUSY` | bryggan gör inget följdriktigt medan dess tillstånd är okänt |
| Operatören ser | *"Bryggan är degraderad efter en timeout. En läsande körning återställer den."* och en knapp som kör en läsande `ping`/`exec` |

### 3.5 provtagning pågår

| Fall | Åtgärd |
|---|---|
| Ett provtagningsfel kastas | pumpen loggar `PROVTAGNINGSFEL` med traceback och sätter `provtagare.aktiv = False`. Körningen blir **INCONCLUSIVE**, aldrig PASS (I3) |
| Takten faller under 15 Hz | `INCONCLUSIVE` (`26_appen.md`, A-8) |
| Serien är för stor för svaret | `eyes.json` på disk är källan; svaret bär `for_stor_for_svaret` med antal byte |

### 3.6 nere

Detta är läget som kostar mest, och det som ska hanteras bäst.

**Före körningen** — den enda plats där det går att göra något:

| Operation | Bryggans svar | Vad operatören ser | Stämpel |
|---|---|---|---|
| `createBehaviour(VC_SCRIPT, ...)` | **avvisas** med `E_ARGS` | *"Koden skapar ett skriptbeteende. Det stoppar simuleringen och dödar bryggan utan väg tillbaka. Skjut upp den till nästa VC-start, eller tillåt tystnaden medvetet."* | **MÄTT M-13** |
| `app.save(uri)` | **tillåts**, men `dodar_pumpen` sätts på posten och varningen kommer **före** godkännandet | *"Koden stoppar simuleringen. Den KÖRS, men bryggan går ned och något utfall kommer aldrig. VC måste startas om."* | **MÄTT M-13** |

Skillnaden är avsiktlig: att lägga till ett skript är sällsynt och har en
uppskjuten väg; att spara en layout är en helt normal sak att vilja göra, och
att förbjuda den vore att ta bort en förmåga som behövs.

**Efter körningen:**

| Steg | Vad som ska hända |
|---|---|
| 1 | Tjänsten slutar **vänta** på ett utfall så snart kvittot bar `dodar_pumpen` (KOD@HEAD `utforare.godkann`). Den går aldrig i timeout på ett svar som inte kan skickas |
| 2 | Panelen visar `nere` **med orsak**: vilken post, vilket anrop, vilken rad, och vilken mätning som förklarar det (M-13) |
| 3 | Panelen visar de två vägarna tillbaka: menyval 2 i VC, eller en VC-omstart |
| 4 | Posten står kvar som `running` tills nästa pumpstart, då den markeras `interrupted` |
| 5 | Uppdraget pausas. Inga fler poster godkänns |

**Undantaget:** står bryggloggens sista rad på `modal oppen` säger panelen
*"en statusruta står öppen i VC — stäng den så svarar bryggan igen"* i stället
för `nere` (`26_appen.md`, A-3).

### 3.7 utan självstart

Bryggan har slagit av sin egen omstart efter 20 försök på en minut. Panelen
säger det rakt ut, med antalet, och pekar på menyval 2. Systemet försöker
**inte** igen av sig självt. En omstartsstorm är mätt till tusentals varv i
sekunden (M-13) och får aldrig upprepas.

---

### 3.8 När något dör mitt i — de fyra fallen, och vad användaren ser

De sju lägena ovan handlar om **bryggan**. Tre saker kan sluta svara under ett
uppdrag, och de har tre olika tystnader och tre olika vägar tillbaka. Att slå
ihop dem till *"systemet"* är att svara `nere` på frågan *vad är det som är
nere?*

| Delsystem | Vad den bär | Var läget läses |
|---|---|---|
| **bryggan** | VC, scenen, kön, ögat | `ping`, `sim` |
| **OpenPLC** | den körande PLC-koden, OPC UA-bandet | kopplarens varv |
| **modellen** | språkmodellen som skriver och reparerar | modellklientens svar |

Fyra dödsfall, och för vart och ett: vad systemet gör, och vad det **säger**.
Meningarna nedan är de som faktiskt står i ytan (`aterhamtning.lagen.ORSAKER`),
inte omskrivningar av dem.

| # | Vad som dör | Vad systemet gör | Vad användaren ser | Försöker något igen? | Stämpel |
|---|---|---|---|---|---|
| 1 | **VC stängs under en körning** | slutar vänta på ett utfall som inte kan komma; kön är borta med processen | *"Visual Components avslutades. Anslutningen bröts av att processen försvann."* + `ECONNRESET` ordagrant | **nej.** Enda vägen: starta om VC | `31_brygga_protokoll.md`, KOD@HEAD |
| 2 | **bryggan tappar sin socket** | ansluter om och pingar; **bara ett ping-svar** räknas som liv | *"Anslutningen till bryggan bröts, men bryggan svarar fortfarande. Bara vår ände tappade den."* | **ja**, och det kan lyckas: `klient.anslut` | KOD@HEAD |
| 3 | **OpenPLC svarar inte** | kopplaren räknar raka fel; vid tredje ger den upp och kastar `Kopplarfel` | först *"OpenPLC svarade inte inom tidsgränsen … ger upp vid tredje"*, sedan *"Kopplaren gav upp efter tre raka fel. Ingenting försöker igen, och det är avsiktligt"* | **nej efter tredje.** En slinga som mal vidare mot en död PLC ser ut att arbeta | **MÄTT M-39**, `kopplare.MAX_RAKA_FEL = 3` |
| 4 | **modellen tar slut mitt i en reparation** | varvet blir aldrig klart; grindarna efter det körs aldrig | *"Modellen slutade svara mitt i en reparation. Varvet blev aldrig klart, och de grindar som skulle ha kört efter det kördes aldrig."* | **nej.** Utfallet är kandidat i bästa fall, aldrig guld | KOD@HEAD `modellklient.Modellfel` |

**Regel L-11.** De fyra får inte se likadana ut. En yta som svarar samma sak på
alla fyra svarar ingenting på någon: den namnger inte saken, den döljer att tre
av fyra kräver en människa, och den ger operatören ingenting att göra.
*Mätbart:* fas 23 renderar alla fyra och jämför både första raden och
orsaksblocket (`test_de_fyra_dodsfallen_ser_olika_ut`).

**Regel L-12.** Skillnaden mellan fall 1 och fall 2 får kosta **en fråga till**.
Ett brutet rör säger inte i sig vilket av dem det var, och svaret avgör vilken
väg tillbaka användaren får. Frågan måste vara ett `ping` — en `connect()` som
lyckas mot en död pump skulle skriva *"bryggan svarar fortfarande"* om en brygga
som är stendöd (regel L-1).

### 3.9 Ett återhämtningsförsök, och om det kan lyckas

Det farligaste en yta kan säga till någon som väntar är *"Ett problem uppstod,
vi försöker igen"* när ingenting försöker igen. Meningen är värre än tystnad:
den ber användaren vänta på något som inte händer.

**Regel L-13.** Ett försök redovisas som pågående endast om det **finns i
protokollet** och **kan lyckas**. Vem som helst av de två som saknas gör
redovisningen till en lögn.

Kanskapen har **tre** värden, aldrig två:

| Värde | Betyder | Vad ytan får säga |
|---|---|---|
| `kan lyckas` | mätt eller KOD@HEAD att vägen leder tillbaka för just den orsaken | att försöket pågår |
| `kan inte lyckas` | mätt att den inte gör det | att försöket **inte** kan lyckas, med orsaken |
| `okänt om den hjälper` | ingen mätning finns | att vägen finns och att utfallet inte är mätt |

Ett `okänt` som skrivs som ett `ja` är ett löfte, och ett löfte till någon som
väntar på en död brygga är det dyraste vi kan ge. Ett `okänt` som skrivs som ett
`nej` slänger en väg som kanske fungerar.

Svaret avgörs på **ett** ställe, i en oskrivbar tabell
(`aterhamtning.lagen.KAN`, en `MappingProxyType`) — samma form som
`utforare.OP_FOR_EFFECT` och av samma skäl: en fråga som besvaras på två
ställen besvaras förr eller senare olika. Ett par som saknas i tabellen är
`okänt`, aldrig `ja` (fail-closed, I3).

Två spärrar utöver tabellen:

* **Självstarten kan aldrig lovas.** Ingen orsak har `kan lyckas` för
  `bryggans självstart`. Det är en strukturell spärr, inte en tillfällighet:
  självstarten är den enda väg systemet går utan att fråga, och ett okänt
  `keepalive` skulle annars kunna glida till ett löfte.
  *Mätbart:* `test_ingen_orsak_lovar_att_sjalvstarten_kan_lyckas`.
* **`utan självstart` gör varje självstartsförsök omöjligt**, oavsett orsak.
  Omstartsstormen är mätt till tusentals varv i sekunden (M-13), och spärren
  finns för att den aldrig ska upprepas.

**Regel L-14.** Kanskapen räknas om **vid varje visning**, inte en gång när
försöket började. Slår bryggan av sin självstart mitt i ett självstartsförsök
blir försöket omöjligt utan att någon rör det, och det får då inte räknas bland
de pågående. Det stryks inte heller — det står kvar med beskedet att det inte
längre kan lyckas. Att stryka det vore att dölja att vi väntade förgäves.

**Talet som gör regeln nödvändig:** av **18** orsaker har **3** en automatisk
väg alls, och bara **2** en som är mätt att kunna lyckas. I 15 av 18 fall
försöker ingenting igen — och ytan säger det med de orden.

---

## 4. En halvfärdig plan när VC startas om

| Sak | Vad som händer | Stämpel |
|---|---|---|
| Kön | **töms.** Den lever i `Brygga.ko`, i minnet | KOD@HEAD |
| Poster som stod i `running` | markeras `interrupted` vid nästa pumpstart, så de varken körs igen eller ser färdiga ut | KOD@HEAD `_markera_avbrutna` |
| Uppskjutna ändringar | tillämpas **vid uppstart, före `startSimulation()`**, där samma operation är ofarlig. De som misslyckas ligger kvar i filen | KOD@HEAD `_tillampa_uppskjutet` |
| Tokenet | skrivs om. Tjänsten måste läsa om filen | KOD@HEAD |
| Planen och journalen | ligger på tjänstens sida, på disk, per uppdrag, buren av **arbetsordern** (`24_samtalsloopen.md` §6) | **ska byggas** |
| Scenen | endast det som `save_layout` hann spara | **MÄTT M-13** |

**Regel L-3.** Vid återupptagning börjar tjänsten med att **läsa scenen**, inte
med att lita på planen. Planen säger vad som var tänkt; scenen säger vad som
finns. De kan gå isär på exakt det steg som avbröts.

Mekaniken är arbetsorderns **scenfingeravtryck** (`24_samtalsloopen.md` §5):
antal komponenter plus hash av de sorterade namnen. Stämmer det inte mot en
färsk `list_components` tvingas en omläsning innan något skrivande verktyg får
köras. Kostnaden är en tur och retur, median **9,91 ms** (M-03).

**Regel L-4.** En `interrupted` post körs aldrig om automatiskt. Den visas för
operatören med sin kod och sitt läge, och han bestämmer.

**Regel L-5.** Efter en omstart visar panelen en **skillnadslista**: planens
steg mot scenens innehåll, per komponent och per koppling. Det är samma
turordnings-diff som ärvs ur källprojektet (`20_arv.md`).

---

## 5. Loggning och spår

### 5.1 Var det skrivs

| Fil | Skrivs av | Innehåll |
|---|---|---|
| `~/vc_assist_boot.log` | `__init__.py`, `bridge_cmd.py` | uppstartskedjan: `OnAppInitialized`, `loadCommand`, kompilering av skriptmallen, `startSimulation` med tid, omstartshandlaren, uppskjutna poster |
| `~/vc_assist_brygga.log` | `pump.Brygga.logg` | bindning, anslutningar, köade och körda poster, `TICK-FEL`, `PROVTAGNINGSFEL`, omstarter, `modal oppen`/`modal stangd` |
| `~/vc_assist_formaga.json` | `formaga.skriv` | varje prövad yta med `finns`, typ eller undantagsnamn; summering; Python-version; exe-sökväg |
| `~/vc_assist_uppskjutet.json` | `Brygga._skjut_upp` | poster som väntar på nästa VC-start, med skäl |
| VC:s egen motorlogg | VC | licensrad, `DxViewError` |
| Arbetsordern och uppdragsjournalen | tjänsten | **ska byggas**, se §5.2 och `24_samtalsloopen.md` §6 |

**Regel L-6.** Bryggan loggar sin egen start **före** bindningen. Skälet är
mätt: en upptagen port gav ett undantag i `OnRun` som VC svalde, och bryggan
såg ut att aldrig ha startat — noll rader någonstans (M-13).

### 5.2 Uppdragsjournalen

En rad per händelse, på tjänstens sida, per uppdrag. Kraven kommer ur
`95_testprotokoll.md` ("Reproducerbarhet") och `82_felklasser.md` ("Ingen
klassning utan belägg").

| Fält | Varför |
|---|---|
| commit, VC-version, plattform (Wine-version eller Windows), prefix | ett tal utan den raden är inte ett resultat |
| uppdrags-id, tur, verktygsnamn, argument | spårbarhet till modellens beslut |
| `qid`, `sha256` av koden, operatörens val, tidpunkt | godkännandet är en handling som ska gå att visa i efterhand |
| `state` vid slutet: `done`/`failed`/`interrupted`/`rejected` | |
| sökväg till ögats rapport | domen ska gå att läsa om |
| grind, felkod och **den rad ur ögat eller loggen** som motiverar klassningen | `82_felklasser.md` regel 4 |

**Regel L-7.** Journalen skrivs **inkrementellt**. En avbruten körning ska
ändå gå att läsa. Samma princip som ögats `rows` med `"partial": true`.

### 5.3 Stegen som hittar orsaken

En stege, i ordning. Varje steg är billigare än nästa.

| # | Fråga | Var man tittar |
|---|---|---|
| 1 | Fyrade kroken? | `vc_assist_boot.log` — finns raden `OnAppInitialized`? |
| 2 | Laddades kommandot? | samma logg — `loadCommand uri=...` följt av `bridge_cmd executed`. **Varning:** raden `executed` kan komma även när modulkroppen aldrig kördes (M-09). Nästa rad avgör |
| 3 | Kompilerade skriptmallen? | samma logg — `brygg-komponenten byggd, skriptet kompilerar`, annars `SKRIPTET GAR INTE ATT KOMPILERA` med radnummer och tre rader kontext |
| 4 | Band bryggan porten? | `vc_assist_brygga.log` — `startar pa 127.0.0.1:8901` följt av `lyssnar`. Står bara den första raden är porten upptagen |
| 5 | Tickar pumpen? | samma logg — `pumpen igang`; och `ping` ger `tick` som växer |
| 6 | Dog den, och av vad? | sista raderna före tystnaden: `kord q<n> -> ...`, `simuleringen stoppad`, `ber om omstart`. Postens `desc` säger vilket verktyg det var |
| 7 | Var det en av de två mätta dödarna? | `dodar_pumpen` på posten, eller `createBehaviour(VC_SCRIPT)` i koden. Se M-13 |

**Regel L-8.** Panelen kör den här stegen själv när läget blir `nere` och visar
resultatet. Operatören ska inte behöva öppna en loggfil för att få veta varför.

---

## 6. Hur ett problem rapporteras vidare

En felrapport skapas som **en fil**, aldrig som en utgående begäran.

| Innehåll | Källa |
|---|---|
| Systemrad: commit, VC-version, plattform, prefix, protokollversion | journalen |
| Förmågerapporten i sin helhet | `vc_assist_formaga.json` |
| Sista N raderna ur båda loggarna | `vc_assist_boot.log`, `vc_assist_brygga.log` |
| Kön som den såg ut, med koden | `queue_list` med `with_code` |
| Ögats domstext och `eyes.json` om de finns | |
| Uppdragets journal | |
| Vad operatören försökte göra, i hans egna ord | panelen frågar |

**Regel L-9.** Rapporten skickas av **operatören**, inte av systemet. Ingen
telemetri, ingen automatisk uppladdning (`26_appen.md`, förbud 9).

**Regel L-10.** Varje fel som hittas ger **först** ett test som fäller på det,
sedan fixen. Testet blir kvar (`95_testprotokoll.md`, regressionsregeln).

---

## 7. Det som aldrig får hända

Sex saker. Var och en har en mekanisk kontroll, inte ett löfte.

| # | Får aldrig hända | Mekanisk kontroll |
|---|---|---|
| **N-1** | **Tyst nedgradering.** En saknad förmåga leder till att systemet gör något mindre utan att säga det | Förmågegrinden (`verktyg/formagegrind.py`) stänger av verktyget helt och namnger ytan. `36_versioner.md`: okänt behandlas som saknat, aldrig gissat. Test: en riggad rapport med en saknad yta ⇒ verktyget kastar `Avstangt`, kör inte |
| **N-2** | **En dom utan underlag.** Guld visas utan ögats domstext, eller en dom visas utan sin serie | `guldgrind` är fail-closed: okänd version, avhuggen rapport, saknad cell och tystnad är alla `NOT GOLD`. Panelen får inte rendera fält 6 utan fält 5. Test: guldfiler för PASS, FAIL, INCONCLUSIVE, okänd version och avhuggen rapport |
| **N-3** | **En ändring utan godkännande.** Skrivande kod når scenen utan att en människa sagt ja | Två oberoende linjer: `utforare.OP_FOR_EFFECT` (oskrivbar tabell, enda stället där ett läge väljs) och `skrivgrind.granska()` inne i bryggan, som avvisar skrivande `exec` med `E_NOT_APPROVED`. Test: antalet körda poster = antalet godkännanden i journalen, över en hel körning |
| **N-4** | **En post körs två gånger.** En avbruten post tas för `pending` och körs om | `_markera_avbrutna` sätter `interrupted`, ett läge som varken `queue_approve` eller pumpen plockar. Test: döda pumpen mitt i en post, starta om, kontrollera att posten inte körs |
| **N-5** | **`nere` utan orsak.** Panelen säger att bryggan är nere utan att säga varför | Stegen i §5.3 körs automatiskt. Test: fem framprovocerade nedgångar ger fem olika, korrekta orsaker |
| **N-6** | **Ett tyst undantag.** Ett fel slukas av ett brett `except` | S9: lintern avvisar `except:` och `except Exception:` utan loggning eller återkastning. `tick()`:s egen `except` loggar `TICK-FEL` med traceback — den finns för att en pump som dör tar hela tillägget med sig, och den är den enda tillåtna av sitt slag |

**N-1 är den farligaste.** Ett system som gör mindre än det påstår mäter fel i
tysthet, och felet syns först när någon litar på ett tal.

---

## 8. Grindarna

| # | Godkänt när |
|---|---|
| **Å-G1** | Alla sju lägen kan framprovoceras, och panelen visar rätt ord i alla sju |
| **Å-G2** | En död pump ger `nere` inom `T_nere`, **trots** att `connect()` lyckas (§1.2) |
| **Å-G3** | `degraderad` lämnas av en läsande `exec` och av ingenting annat; `queue_approve` ger `E_BUSY` under tiden |
| **Å-G4** | En `save_layout` varnar före godkännandet, tjänsten slutar vänta direkt, och panelen visar orsaken utan att operatören öppnar en logg |
| **Å-G5** | Ett `createBehaviour(VC_SCRIPT)` avvisas, och med `skjut_upp` tillämpas det vid nästa start och försvinner ur filen |
| **Å-G6** | En VC-omstart mitt i en plan ger: tom kö, `interrupted` på rätt post, skillnadslista plan mot scen, och ett uppdrag som går att slutföra |
| **Å-G7** | Stegen i §5.3 pekar ut rätt steg för alla fem tysta fällorna i `27_operatorsflodet.md` §3 |
| **Å-G8** | Felrapporten innehåller alla sju delarna i §6 och skapas utan en enda utgående uppkoppling |
| **Å-G9** | Var och en av N-1 till N-6 har ett test som **fäller** när skyddet tas bort. En grind utan trasig fixtur är oprövad (`95_testprotokoll.md`) |
| **Å-G10** | Omstartsspärren håller: en framprovocerad storm ger högst 20 omstarter på en minut och slutar i `utan självstart` |

### 8.1 Grindarna över VISNINGEN (fas 23)

Å-G1 till Å-G10 dömer **systemet**. De säger ingenting om vad användaren får
läsa om det, och det är en egen fråga med ett eget svar: en visning är en dom
om systemets tillstånd, ställd till den enda som inte kan kontrollera den.

| # | Godkänt när |
|---|---|
| **Å-G11** | Läget står först i visningen och **räknas om av grinden själv** ur de råa avläsningarna och läsarens klocka. En härledning som fryser klockan, räknar en lyckad `connect()` som liv, eller sanerar bort en negativ ålder fälls |
| **Å-G12** | Varje delsystem står med sitt läge. Ett `obestämt` får varken visas som grönt eller utelämnas |
| **Å-G13** | Ett läge som inte svarar bär en orsak, ordagrant — eller beskedet att orsaken inte gick att avgöra. *"Ett problem uppstod"* fälls |
| **Å-G14** | Ett försök redovisas som pågående endast om det finns i protokollet och kan lyckas. Står ingenting på tur säger visningen det med orden `Ingenting försöker igen` |
| **Å-G15** | Varje väg tillbaka bär sin kanskap och sin härkomst |
| **Å-G16** | Räckvidden — det återhämtningen aldrig kan veta — står i varje visning, också en där allt svarar |

Var och en av `Å1`–`Å14` i `svc/vc_assist_svc/aterhamtning/grind.py` har minst
en trasig fixtur, och provet som håller regeln läser sin egen källa. En grind
utan trasig fixtur är oprövad (`95_testprotokoll.md`).

Plattform: **Linux ☐ Windows ☐** per grind.

---

## 9. Öppna frågor och mätningar som saknas

| Mätning | Frågan | Blockerar |
|---|---|---|
| **M-25 — lyssningskön under Wine** | Lyckas `connect()` mot en död pump även genom Wines winsock, och hur länge? | Å-G2, och tidsgränserna i §1.3 |
| **M-26 — köns pollningströsklar** | `KO_POLL_S` och `KO_TIMEOUT_S`. Koden hänvisar till `M-14`, men det numret gick till en annan mätning — trösklarna står alltså utan härkomst (I2) | §3.3:s 100 ms-krav |
| **M-21** | Menyytan, och om en öppen `messageBox` stoppar pumpen och hur länge | §3.6:s undantag för `modal oppen` |
| **M-23** | Grön start, tid till lyssnande port över tio starter | `27_operatorsflodet.md` §4 |
| **M-27 — fler dödande anrop** | Listan över operationer som dödar pumpen är **inte** härledd ur en princip. Den växte från ett till två genom mätning och kan växa igen | `skrivgrind.DODANDE_ANROP`. Ett svep över de skrivande verktygen mot en levande pump behövs |
| **M-21, andra halvan** | Raden `modal oppen` finns inte i koden. Vem skriver den, och blockerar en `messageBox` verkligen pumpen? | läget `blockerad`, `T_modal`, hela §3.6:s undantag |
| **M-25, Linux-halvan betald** | `connect()` mot en lyssnande socket som ingen accepterar lyckades **20 av 20** i den här processen (M-103). Wine-halvan står kvar | regel L-1:s premiss på Linux |

Frågor till operatören. **Inget av detta är bestämt.**

1. **Ska en `save_layout` få köras alls under ett uppdrag**, eller ska den
   skjutas till slutet så att bryggan går ned först när arbetet är klart?
   Det senare vore billigare men tar bort en förmåga mitt i.
2. **Ska tjänsten få starta om VC** när läget är `nere`? Specen säger nej
   (I14, och VC:s start är operatörens beslut), men det är ett val, inte en
   naturlag.
3. **Hur länge journalen sparas**, och om ögats serier ska gallras. En
   `eyes.json` per körning växer.
4. **Om `utan självstart` ska kunna slås på igen från panelen** eller bara av
   en VC-omstart.
5. **Om sonden ska gå av sig själv**, och hur ofta. Ytan i
   `svc/vc_assist_svc/aterhamtning/` läser avläsningar som någon annan gjort;
   vem som gör dem, och med vilket mellanrum, är inte bestämt. En sond som går
   för sällan gör varje läge obestämt; en som går för ofta lägger trafik på en
   brygga som kanske redan har det svårt.
6. **Var systembilden ligger.** Speglingen skriver en fil, och sökvägen är i dag
   ett argument. Förslagsvis samma katalog som uppdragsjournalen
   (`27_operatorsflodet.md` §10 fråga 1). Ingen mapp är vald.
7. **Om två sonder mot samma fil ska tillåtas.** `os.replace` gör varje
   skrivning atomisk, men ingen låsning finns — samma öppna punkt fas 17 lämnade
   för förloppsfilen.
