# Appen

**beskriver:** `ext/vc_addon/vc_assist/`, `svc/vc_assist_svc/`, `install/`
**kontrakt:** `30_arkitektur.md`, `31_brygga_protokoll.md`, `36_versioner.md`,
`45_verktyg.md`, `50_grindar.md`, `90_invarianter.md`

Detta dokument specar **produkten**: vad operatören ser, var han skriver, vad
som visas medan systemet arbetar, och hur han godkänner. Allt annat i specen
beskriver maskineriet. Detta beskriver ytan.

Regeln från `01_kalldisciplin.md` gäller: varje påstående är **MÄTT**,
**KOD@HEAD**, **DOK** eller **ANTAGET**. Ytan bygger på färre mätningar än
resten av systemet, och det står utskrivet var.

## Vad produkten är

Ett tillägg till Visual Components som hämtas från GitHub. Operatören ber i
naturligt språk om att en fabriksscen byggs och att PLC-kod i strukturerad text
genereras. Systemet bevisar själv att resultatet fungerar genom att köra
simuleringen och låta ögat döma den.

Paketet är **ett**, men processerna är **två**:

| Halva | Var den kör | Vad den bär | Ändras |
|---|---|---|---|
| **Tillägget** | inne i VC, VC:s egen Python (2.7 på 4.x, 3.x på 5.0) | bryggan, pumpen, ögat, menyytan | ska aldrig behöva ändras |
| **Tjänsten** | utanför VC, Python 3 på värden | samtalet, modellen, verktygen, grindarna, panelen | här sker all utveckling |

Detta är samma söm som i `30_arkitektur.md`. Den är inte ett internt val — den
är tvingad: VC har inget externt API, och VC:s Python är kooperativ och
simuleringsdriven (M-04, M-07, M-08).

---

## 1. Ytan inne i VC

### 1.1 Rättelse: menyytan är DOK, inte MÄTT

Förmågerapporten är mätt till **46 av 46 ytor** (fas 5, `tests/protocol/fas5_verktygen.md`).
`addMenuItem` och `createMenuItem` är **inte** bland dem. `formaga.py:YTOR`
innehåller noll menyrader — kontrollerat.

| Yta | Stämpel | Härkomst |
|---|---|---|
| `app.messageBox` | **MÄTT** | `formaga.py:YTOR`, 46 av 46 finns (fas 5) |
| `app.getApplicationPath` | **MÄTT** | samma |
| `app.addMenuItem(menu, caption, position, command)` | **DOK** | `docs/referens/vc_api/api.xml` |
| `app.addMenuButton` | **DOK** | samma |
| `app.removeMenuItem(handle)` | **DOK** | samma |
| `app.createMenuItem` | **DOK, utfasad** | api.xml säger uttryckligen "Deprecated. Use addMenuItem()" |
| `VC_MENU_ADDONS` m.fl. 18 menykonstanter | **DOK** | `constants.xml`, rad 309–326 |
| `app.getMessages` / `app.clearMessages` (Output-panelen) | **DOK** | api.xml |
| `app.PythonActionPanel`, `cmd.executeInActionPanel` | **DOK** | api.xml |
| `app.ProgressStatus` / `ProgressValue` | **DOK** | api.xml |

**Motsägelse i VC:s egen dokumentation**, värd att skriva ned: `addMenuItem`
deklareras med `<type>Boolean</type>` medan beskrivningen säger *"Each call
returns an integer that is a handle for the new menu item. Use that value in
removeMenuItem()"*. Koden får därför **aldrig** anta returtypen. Den ska logga
`type(...)` och värdet, och avinstallation av menyvalet ska tåla båda formerna.

**Konsekvens:** menyytan får inte byggas som om den vore mätt. Den mäts i
**M-21** (avsnitt 7), och tills dess är varje menykrav nedan märkt `OPRÖVAD`.

### 1.1.1 DOK är inte belägg för att något FUNGERAR — hela menyytan är ANTAGEN

Raderna ovan står som **DOK**, och det ordet betyder exakt en sak: *VC:s eget
dokument påstår det.* Det är inte samma sak som att vi har sett det hända, och
skillnaden är inte akademisk i just det här systemet — `api.xml` motsäger sig
självt om `addMenuItem`s returtyp på samma rad som den beskriver den.

**Därför gäller följande, och det ska stå i klartext och inte utläsas:**

| Påstående | Vad vi vet | Stämpel |
|---|---|---|
| namnen `addMenuItem`, `addMenuButton`, `removeMenuItem` finns i api.xml | dokumentet säger det | **DOK** |
| ett anrop registrerar ett **synligt** menyval i 4.10 | ingenting | **ANTAGET** |
| anropet returnerar ett handtag som går att avregistrera | dokumentet säger två olika saker | **ANTAGET** |
| menykommandot **fyrar** när valet klickas | ingenting | **ANTAGET** |
| `print()` från kommandot landar i Output-panelen | dokumentet säger det | **ANTAGET** |
| en öppen `messageBox` stoppar pumpen, och hur länge | `time.sleep(1.0)` från kommandots scope tog 1,000 s och VC stod still | **HÄRLEDD ur M-07**, inte mätt på en ruta |
| raden `modal oppen` skrivs före rutan öppnas | `grep -n "modal" ext/vc_addon/vc_assist/*.py` ger **noll träffar** 2026-09-05 | **EJ BYGGD** |

`M-21` är ett **reserverat nummer** i `docs/matningar/RESERVERADE.md`. Ett
reserverat nummer är ett löfte om en mätning, inte en mätning — och en spec som
låter ett sådant nummer stå som härkomst har bytt ut ett belägg mot en avsikt.
Varje rad i §1.3 nedan ska därför läsas som **ANTAGET**, inte som `OPRÖVAD` i
betydelsen *"nästan klart"*.

Följden syns i återhämtningsytan: läget `blockerad` — det som ska säga *"en
statusruta står öppen i VC"* i stället för `nere` — **kan inte fyras i dag**,
eftersom raden det läser inte skrivs. Ytan skriver ut den begränsningen i varje
visning (`aterhamtning.yta.RACKVIDDEN`) i stället för att låtsas ha förmågan.
Det är billigare att säga att en förmåga saknas än att upptäcka det när någon
litar på den.

Skälet att kräva mätning och inte lita på dokumentet är samma tre gånger
mätta egenskap: **VC sväljer fel tyst** (M-01, M-06, M-09). Ett menyval som
inte registreras säger ingenting någonstans.

### 1.2 Var tillägget kommer in

| Sak | Värde | Stämpel |
|---|---|---|
| Meny | `VC_MENU_ADDONS` (Add-Ons) | DOK |
| Reservordning om `VC_MENU_ADDONS` inte tas | `"Add-Ons"` som sträng, sedan `VC_MENU_HOME` | ANTAGET — api.xml tillåter både konstant och sträng-id |
| Rubrik | `VC Assist` | vårt val |
| Registrering sker i | `__init__.py`, `vcApplication`-scope | **MÄTT M-01** — `__init__.py` kan registrera kommandon och lägga menyval men **inte** röra appen |
| Kommandona laddas med | `loadCommand(namn, uri)` | **MÄTT M-01** |

Att registreringen måste ligga i `__init__.py` och verkan i ett kommando är
inte en stilfråga. `getApplication()` finns inte i `__init__.py` (M-01).

### 1.3 Menyvalen — exakt tre

Fler är fel. Varje menyval kostar ett kommando som ska laddas, verifieras och
avregistreras, och varje kommando som körs står på **VC:s huvudtråd**, där
pumpen bor (M-07, M-08).

| # | Etikett | Vad det gör | VC:s tråd | Stämpel |
|---|---|---|---|---|
| 1 | `VC Assist — status` | öppnar en `messageBox` med en **ögonblicksbild**: port, lyssnar ja/nej, tick, antal begäran, kö (väntande/totalt), `degraded`, förmåga *n* av *m*, VC-version, panelens adress | blockeras medan rutan står öppen | OPRÖVAD (M-21) |
| 2 | `VC Assist — starta om bryggan` | `sim.reset()` + `app.startSimulation()` från kommandots scope | ~ millisekunder | vägen är **MÄTT M-13** (`_koppla_startstopp`, `_op_sim do=restart`) |
| 3 | `VC Assist — uppskjutna ändringar` | visar antal poster i `~/vc_assist_uppskjutet.json` och att de tillämpas vid nästa VC-start | ~ millisekunder | filen och tillämpningen är **KOD@HEAD** (`bridge_cmd._tillampa_uppskjutet`) |

**Regel A-1.** Inget menyval får utföra arbete som ändrar scenen. Menyn är
status och återhämtning, aldrig produktion. Produktion går genom kön.

**Regel A-2.** Ett menyval får hålla VC:s tråd i högst **200 ms** utöver den tid
en modal ruta står öppen. Mätbart: kommandot loggar `t0`/`t1` i
`~/vc_assist_boot.log`, och grinden läser differensen.

**Regel A-3, mätt skäl.** Medan menyval 1:s ruta står öppen **svarar bryggan
inte**. `time.sleep(1.0)` från kommandots scope tog 1,000 s väggklocka och VC
stod still under tiden (M-07). Därför skriver kommandot raden
`modal oppen` till bryggloggen **före** rutan öppnas och `modal stangd` efter.
Tjänsten läser den raden när kontakten tystnar och säger *"en statusruta står
öppen i VC"* i stället för *"bryggan är nere"*. Se `28_lagen_och_aterhamtning.md`.

### 1.4 Vad ytan inne i VC inte får vara

**Ingen panel som måste ritas om.** `OnIdle` fyrade **noll** gånger på 90 s och
`OnRender` likaså (M-12). Det finns alltså ingen klocka i gränssnittet. En
levande panel inne i VC skulle bara kunna ritas om av pumpen — och pumpen dör
när en layout sparas eller ett skriptbeteende skapas (M-13). Panelen skulle
alltså frysa exakt i det ögonblick operatören behöver den.

`PythonActionPanel` och `executeInActionPanel` är **inte förbjudna**, de är
**oprövade**. De får byggas den dag M-21 visar att de kan uppdateras utan en
händelseklocka. Tills dess är de inte en väg.

---

## 2. Var samtalet förs

Detta är produktens enskilt viktigaste designbeslut, och det avgörs av
mätningar, inte av smak.

| Plats | För | Emot — mätt |
|---|---|---|
| Modal ruta i VC (`messageBox`, `genVarSpaceDialog`) | nära scenen, VC:s eget utseende | blockerar huvudtråden ⇒ pumpen tickar inte ⇒ bryggan svarar inte (M-07). Fritext och historik ryms inte i en meddelanderuta |
| Actionpanel i VC (`PythonActionPanel`) | inbyggd panelyta | ingen mätt uppdateringskälla: `OnIdle` och `OnRender` fyrar inte (M-12). Skulle behöva pumpen som klocka, och pumpen dör vid `app.save()` och `createBehaviour(VC_SCRIPT)` (M-13) — alltså blind när det gäller |
| **Utanför VC, tjänstens egen panel** | överlever att bryggan dör och kan visa **varför**; rör aldrig VC:s tråd; bär fritext, historik, kod och diffar; samma yta på Windows och Wine | två fönster; operatören måste veta var panelen finns |

**Beslut: samtalet förs utanför VC.** Inne i VC finns bara status och vägen
tillbaka.

| Egenskap | Värde | Stämpel |
|---|---|---|
| Adress | `http://127.0.0.1:8902` — loopback **endast**, aldrig `0.0.0.0` | port ur `30_arkitektur.md` |
| Yta | lokal websida som tjänsten serverar | ANTAGET: operatören har en webbläsare. Alternativ, om inte: en terminalyta med samma sju fält |
| Startas av | operatören, via genvägen installationen lägger | **ANTAGET.** Tillägget får inte starta processer: `35_plattformar.md` regel 4 förbjuder `subprocess` mot skalkommandon inifrån VC, och skalet skiljer sig mellan Windows och Wine |
| Adressen visas i | menyval 1 (statusrutan) | så att operatören aldrig behöver leta |

**Regel A-4.** Panelen är ensam om att ta emot fritext. Ingenting i VC frågar
operatören något.

---

## 3. Panelens sju fält

Panelen har sju fält och inga fler. Ordningen är den som ögat läser den i.

| # | Fält | Innehåll | Källa | Uppdateras |
|---|---|---|---|---|
| 1 | **Samtalet** | operatörens begäran, modellens svar, hela historiken för uppdraget | tjänsten | vid varje tur |
| 2 | **Planen** | stegen, verktyget per steg, status per steg (väntar / kör / klar / föll) | tjänstens utförare | vid varje verktygsanrop |
| 3 | **Kön** | väntande poster: `qid`, `desc`, genererad kod, `effect`, varningar | `queue_list` | ≤ 1 s |
| 4 | **Kör nu** | verktygsnamn, beskrivning, förfluten tid | `Utforare` + `queue_list` | ≤ 1 s |
| 5 | **Ögats dom** | domstexten **ordagrant**, som ögat skrev den | `eyes_stop` → `oga_kontrakt` | vid körningens slut |
| 6 | **Guldnivån** | `L1` / `L2` / `candidate` / `NOT GOLD` med skäl | `guldgrind.Beslut.text()` | vid grindens beslut |
| 7 | **Systemläget** | bryggans läge, port, tick, begäran, RTT, förmåga *n* av *m*, VC-version, prefix, protokollversion | `ping`, `capability`, `sim` | ≤ 2 s |

Fälten matas av den **slutna händelselistan** i `24_samtalsloopen.md` §7
(`PLAN`, `VERKTYG_START`, `KO_VANTAR`, `OGAT_PROVTAR`, `DOM`, `GULD` …) och av
`TYSTNADSTAK`-regeln där. Panelen hittar inte på egna händelser.

**Regel A-5 (I1).** Fält 5 visar ögats **egna byte**. Panelen får inte
sammanfatta, formatera om, färglägga per tal eller översätta domen.
*Mätbart:* ett test jämför panelens fält 5 byte för byte med `eyes.json`
`verdict` + domstexten. Skillnad ⇒ rött.

**Regel A-6.** Fält 6 visar aldrig guld utan fält 5. En guldnivå utan en dom
under sig är en dom utan underlag och är förbjuden
(`28_lagen_och_aterhamtning.md`, N-2).

**Regel A-7.** Fält 7 visar `degraded` som ett eget ord, inte som en färg.
`degraded` betyder att bryggans tillstånd är okänt efter en timeout, och att
`queue_approve` är spärrad tills en läsande `exec` lyckats
(KOD@HEAD, `pump.py:_op_exec`, `_op_queue_approve`).

### 3.0 Vad varje fält gör, och vad det ALDRIG gör

Ett fält som inte har en gräns växer tills det gör allt och betyder inget.

| # | Fältet gör | Fältet gör aldrig |
|---|---|---|
| 1 | visar samtalet i den ordning det fördes | tolkar om modellens ord, eller döljer en omskrivning (`OMSKRIVNING` är en egen händelse) |
| 2 | visar planens steg med status per steg | räknar ett steg som kördes aldrig som ett som höll (fas 17, `Y11`) |
| 3 | visar kön med **hela** koden och varningen | dölja `dodar_pumpen`, eller tillåta samgodkännande av en post som bär den |
| 4 | visar verktygsnamn och **förfluten tid** | visa en gissad procent eller en snurrande symbol (förbud 3) |
| 5 | visar ögats dom **ordagrant** | sammanfatta, färglägga per tal, eller översätta (I1, regel A-5) |
| 6 | visar guldnivån med skäl | visa guld utan fält 5 under sig (regel A-6, N-2) |
| 7 | visar systemläget som **ett ord** plus underläge | visa `ansluten` på något som inte svarat, eller `degraded` som en färg (regel A-7, L-1) |

### 3.2 Fält 7 när något inte svarar

Fält 7 är det enda fältet som måste säga något vettigt när resten av systemet
är borta. Det bär därför fyra saker, i den ordningen, och de är specade i
`28_lagen_och_aterhamtning.md` §3.8 och §3.9:

| Del | Vad den säger | Regel |
|---|---|---|
| **läget** | ett ord per delsystem — bryggan, OpenPLC, modellen — och det värsta överst | Å-G11, Å-G12 |
| **orsaken** | varför, i en fristående mening, med felets egna ord under sig | Å-G13 |
| **återhämtningen** | vad som försöker, eller `Ingenting försöker igen` | Å-G14 |
| **vägarna tillbaka** | var och en med sin kanskap och sin härkomst | Å-G15 |

**Regel A-10.** Fält 7 visar `obestämt` som ett eget ord. Ett läge som inte gick
att avgöra får varken visas som grönt eller utelämnas — I3 på visningens våning.

**Regel A-11.** Fält 7 säger hur **gammal** avläsningen är. Åldern räknas mot
panelens egen klocka, aldrig mot den som skrev avläsningen. En bild som inte
åldras är en död körning som ser levande ut, och formen är mätt tre gånger:
600 av 600 (M-64), 60 av 60 (M-93), 60 av 60 (M-103).

**Regel A-12.** Panelen får aldrig skriva *"Ett problem uppstod, vi försöker
igen"*. Står ordet försök i panelen finns försöket i protokollet och det kan
lyckas. *Mätbart:* regel `Å6` i `aterhamtning/grind.py`, med
`renderare_som_lovar_nytt_forsok` som trasig fixtur.

### 3.1 Takten under provtagning

Under en mätning visar fält 7 dessutom **provtagningstakten i Hz**. Talen som
finns att jämföra mot är mätta:

| Regim | Mätt takt | Källa |
|---|---|---|
| Pumpen tyst | 17,2 Hz | M-03 |
| Pumpen under trafik | 224,7 Hz | M-03 |
| Ögats provtagning i simulerad tid | 20,0 Hz, 3 100 varv utan missat | M-08 |

**Regel A-8.** Faller den uppmätta takten under **15 Hz** under en pågående
provtagning markeras körningen `INCONCLUSIVE`, inte `PASS`.
*PRELIMINÄR:* tröskeln kommer ur M-03:s tysta takt 17,2 Hz minus marginal och
ska sättas av en egen mätning.

---

## 4. Godkännandeflödet

Allt som ändrar något går genom kön. Regeln är mekanisk: `effect=write ⇒ kö`
(I12), och den avgörs på ett enda ställe i tjänsten
(`utforare.OP_FOR_EFFECT`, en oskrivbar `MappingProxyType`). Bryggan har en
andra, oberoende linje: `pump._op_exec` kör `skrivgrind.granska()` och avvisar
skrivande kod med `E_NOT_APPROVED` även om tjänsten skulle råda fel.

### 4.1 En post i kön

Fälten är KOD@HEAD ur `pump.Post`:

| Fält | Betyder |
|---|---|
| `qid` | postens id, `q<n>` |
| `desc` | kort beskrivning, den operatören läser |
| `code` | den genererade Python-koden, i sin helhet |
| `requested_at` | när den köades |
| `state` | `pending` → `approved` → `running` → `done` \| `failed`; eller `rejected`; eller `interrupted` |
| `dodar_pumpen` | lista med skäl, om koden stoppar simuleringen (M-13) |

`interrupted` är inte kosmetik: en post som stod i `running` när pumpen dog fick
aldrig ett utfall, och den får varken se ut som `pending` (då kunde den köras en
andra gång) eller som `done` (den blev aldrig färdig). `pump._markera_avbrutna`
sätter den vid nästa pumpstart.

### 4.2 Vad operatören ser och gör

För varje väntande post visar panelen: `desc`, verktygsnamnet, **hela koden**,
och — om den finns — varningen `dodar_pumpen` med sin förklaring.

Tre knappar: **Godkänn**, **Avvisa**, **Godkänn hela planen**.

| Regel | Innebörd | Mätbar kontroll |
|---|---|---|
| **G-1** | En post med `dodar_pumpen` får aldrig ingå i *Godkänn hela planen*. Den godkänns ensam, med varningen synlig | test: en plan med en `save_layout` bland tio poster kan inte samgodkännas |
| **G-2** | Varningen visas **före** godkännandet. Efteråt finns ingen pump som kan svara, och den som väntar på ett utfall väntar för evigt (M-13) | test: varningens text finns i panelen innan knappen är tryckbar |
| **G-3** | Ingen väg i panelen godkänner automatiskt. Undantaget är bänkkörningar, och de stämplas `auto_approve: true` i loggen och får aldrig rapporteras som operatörsverifierade (`24_samtalsloopen.md` §3) | en körning utan den stämpeln har lika många godkännanden i journalen som körda poster |
| **G-4** | Varje beslut journalförs: `qid`, tid, val, `sha256` av koden, operatörens identitet | journalen i `28_lagen_och_aterhamtning.md` §5 |
| **G-5** | Kön är **minne, inte disk**. Den lever i `Brygga.ko` och töms när VC startas om | panelen skriver ut det i klartext bredvid kön |
| **G-6** | Ett godkännande **kvitteras**; koden körs av pumpen. Utfallet läses ur `queue_list`, aldrig ur godkännandets svar | KOD@HEAD `pump._op_queue_approve`, `klient.godkann_och_vanta` |
| **G-7** | Kön rymmer 256 väntande poster. Fler ger `E_QUEUE_FULL` | KOD@HEAD `pump.MAX_KO` |

### 4.3 Vad som händer efter ett godkännande

Godkännandet sätter `state=approved`. Pumpen betar av **en godkänd post per
varv** (`_beta_av_kon`). Med pumpen i aktivt fönster (5 ms paus, mätt 224,7 Hz
under trafik, M-03) ska körningen ha startat inom **100 ms**.

**Regel A-9.** Startar den inte inom 100 ms medan `sim` säger `kor=True`, visar
panelen `kö stillastående` och pekar på §3 i `28_lagen_och_aterhamtning.md`.
*PRELIMINÄR:* 100 ms är M-03:s aktiva period 4,5 ms med rundlig marginal; ska
sättas av **M-26**.

*Anmärkning:* `utforare.py` skriver `PRELIMINAR. Satts av matning M-14` intill
`KO_POLL_S` och `KO_TIMEOUT_S`. Det numret gick sedan till en helt annan
mätning (gränssnitt går att skapa men inte koppla). Trösklarna står alltså utan
härkomst och bryter I2 tills **M-26** finns. Koden ska rättas i samma commit
som mätningen.

---

## 5. Vad som INTE ska finnas

En app blir dålig av det man lägger till. Följande är förbjudet, och varje rad
har ett skäl.

| # | Får inte finnas | Skäl |
|---|---|---|
| 1 | Chattfönster inne i 3D-vyn | vyn är D3D9 via `D3DImage` (mätt); vi ritar inte i den, och en yta där är beroende av renderaren |
| 2 | Automatiskt godkännande i någon form | I12, och källprojektets mätta fel: alla riggar satte `AUTO_APPROVE=true` och kön blev död (20_arv) |
| 3 | Framstegsindikator som inte har en mätt storhet bakom sig | en spinner som snurrar under en död pump ljuger. Fält 4 visar förfluten tid, aldrig en gissad procent |
| 4 | Egen 3D-vy, egen renderare, egen scenvisare i panelen | VC **är** visaren. En andra vy skulle behöva sin egen sanning om scenen |
| 5 | Inbyggd språkmodell i VC-processen | inget får importeras utanför VC:s medföljande standardbibliotek (`35_plattformar.md` regel 6) |
| 6 | Inställningar operatören måste ställa in för att det ska fungera | förmåga provas, version antas aldrig (`36_versioner.md`). Adresser är konfiguration; beteenden är det inte |
| 7 | Modala rutor under en körning | de blockerar pumpen (M-07). Menyval 1 är den enda modalen, och den öppnas bara av operatören |
| 8 | "Åtgärda åt mig"-knapp som går förbi kön | en ändring utan godkännande är N-3 i `28_lagen_och_aterhamtning.md` |
| 9 | Utgående nätverkstrafik som inte operatören bett om | ingen telemetri, ingen uppladdning av layouter, ingen felrapport som skickas av sig själv. Rapport skapas som **fil** och skickas av operatören |
| 10 | En bakgrundstjänst som startar VC eller startar om VC | I14: ingen oprövad kod i operatörens prefix, och VC:s start är operatörens beslut |
| 11 | Ett andra ställe att godkänna på | två köer blir noll köer. Panelen är enda platsen |
| 12 | Nedgradering när en förmåga saknas | `36_versioner.md`: en saknad förmåga kastar ett fel som namnger förmågan. Aldrig tyst mindre funktion |
| 13 | Egna trösklar i panelen som färglägger ögats tal | I1. Panelen läser domen, den dömer inte |
| 14 | Skrivning till operatörens arbetsprefix från oprövad kod | I14, mätt skäl i `70_faser.md` fas 0 |

---

## 6. Appens grindar

Varje rad är mätbar och körs utan handpåläggning.

| # | Grind | Godkänt när |
|---|---|---|
| **A-G1** | Menyvalen registreras | Efter en start finns exakt tre menyval, varje `addMenuItem` returnerade ett värde som loggats med typ, och antalet rader `menyval registrerat` i bootloggen är 3 |
| **A-G2** | Menyvalet håller inte tråden | `t1 - t0` per menykommando **< 200 ms**, utom den tid en modal står öppen, avläst i bootloggen |
| **A-G3** | Modalen är synlig för tjänsten | Bryggloggen bär `modal oppen` före och `modal stangd` efter varje statusruta; tjänsten säger "statusruta öppen", inte "nere" |
| **A-G4** | Panelen når alla sju fält | Ett skript öppnar panelen mot en levande brygga och läser ut alla sju fälten; inget är tomt utom fält 5–6 före första körningen |
| **A-G5** | Domen är oförändrad | Fält 5 är byte-identiskt med ögats domstext |
| **A-G6** | Ingen skrivning utan godkännande | Över en hel körning: antalet scenändrande `exec`-anrop = 0, och antalet körda poster = antalet godkännanden i journalen |
| **A-G7** | Ingen automatik i operatörens väg | Panelen har ingen kodväg som godkänner utan ett klick. Bänkens undantag är stämplat `auto_approve: true` och en stämplad körning kan inte rapporteras som operatörsverifierad (`24_samtalsloopen.md` §3) |
| **A-G8** | Varning före körning | En plan som innehåller `save_layout` visar `dodar_pumpen`-varningen i panelen innan knappen blir tryckbar, och kan inte samgodkännas |
| **A-G9** | Kön överlever inte en omstart, och det sägs | Efter VC-omstart är kön tom och panelen har skrivit det i klartext |
| **A-G10** | Ingen utgående trafik | En körning med hela grindkedjan öppnar noll uppkopplingar utanför loopback och konfigurerade ändpunkter (OpenPLC, modelleverantören) |
| **A-G11** | Fält 7 skiljer på liv och en öppen socket | En brygga vars pump är död ger aldrig `ansluten`, trots att `connect()` lyckas. **Mätt 20 av 20** mot en lyssnande socket ingen accepterar (M-103); Wine-halvan oprövad (M-25) |
| **A-G12** | Fält 7 åldras | En avläsning äldre än `T_nere` bär inget läge. En härledning som fryser klockan fälls av grinden, inte av en granskare |
| **A-G13** | Panelen lovar aldrig ett försök som inte finns | Över alla 18 orsaker: ordet försök står i ytan endast när ett försök som kan lyckas står i protokollet |

Fasregeln i `95_testprotokoll.md` gäller: **Linux ☐ Windows ☐** ifylls var för
sig. Ingen av appgrindarna är körd på Windows.

---

## 6.1 Ytans delar, uttömmande — och vilka som finns i koden i dag

En spec som beskriver en yta utan att säga vilka delar som är **byggda** är en
prospekt. Tabellen är hela ytan, ingenting utelämnat.

| Del | Vad den gör | Finns i koden? | Stämpel |
|---|---|---|---|
| Menyval 1, status | ögonblicksbild i en `messageBox` | **nej** | ANTAGET (M-21) |
| Menyval 2, starta om bryggan | `sim.reset()` + `startSimulation()` från kommandots scope | vägen ja (`bridge_cmd._koppla_startstopp`), menyvalet **nej** | vägen **MÄTT M-13** |
| Menyval 3, uppskjutna ändringar | räknar poster i `~/vc_assist_uppskjutet.json` | filen och tillämpningen ja, menyvalet **nej** | KOD@HEAD |
| Raden `modal oppen` / `modal stangd` | låter tjänsten skilja en öppen ruta från en död brygga | **nej** | EJ BYGGD |
| Panelens fält 1, samtalet | historiken för uppdraget | **nej** | kräver en levande brygga |
| Panelens fält 2, planen | steg med status per steg | **ja**, som text: `forlopp.yta` | fas 17, M-64/M-93 |
| Panelens fält 3, kön | väntande poster med hela koden | **nej** | KOD@HEAD på bryggsidan (`queue_list`) |
| Panelens fält 4, kör nu | verktyg och förfluten tid | **ja**, som text: `forlopp.yta` | fas 17 |
| Panelens fält 5, ögats dom | domstexten ordagrant | **ja**, som text, med grind `Y4`/`Y12` | fas 17 |
| Panelens fält 6, guldnivån | `guldgrind.Beslut.text()` | **ja**, som text, med grind `Y7` | fas 17 |
| Panelens fält 7, systemläget | läge, orsak, återhämtning, vägar tillbaka | **ja**, som text: `aterhamtning.yta` | fas 23, M-103 |
| Visaren för ett pågående förlopp | `python3 -m vc_assist_svc.forlopp <fil>` | **ja** | fas 17 |
| Visaren för ett dött delsystem | `python3 -m vc_assist_svc.aterhamtning <fil>` | **ja** | fas 23 |
| Fönstret som visar texterna | webbsida eller terminalvy | **nej, med flit** | valet är öppet, §7 fråga 1 |
| Felrapporten som fil | de sju delarna i `28_lagen...` §6 | **nej** | ska byggas |

**Regel A-13.** Raden *"finns i koden"* i tabellen ovan ska stämma mot repot vid
varje läsning. En spec som säger *ja* om något som inte finns är farligare än
ingen spec: den flyttar upptäckten till den dag någon litar på förmågan.

---

## 7. Öppna frågor och mätningar som saknas

Numren 14 och 15 är tagna av mätningar som redan finns
(`M-14_granssnitt_gar_att_skapa_men_inte_koppla.md`,
`M-15_skapbara_beteenden.md`), och 16 är anspråkstaget i `23_llm_granssnitt.md`.
Det som begärs här börjar därför på 21.

| Mätning | Frågan | Blockerar |
|---|---|---|
| **M-21 — menyytan** | Registrerar `addMenuItem(VC_MENU_ADDONS, ...)` ett synligt val i 4.10? Vad returnerar den, Boolean eller handtag? Fyrar kommandot? Landar `print()` i Output-panelen? Stannar pumpen medan en `messageBox` står öppen, och hur länge? | A-G1, A-G2, A-G3, hela §1.3 |
| **M-22 — gränssnittet under last** | Går VC att använda medan pumpen går och en provtagning pågår? Bild­frekvens och subjektiv frysning, **inte** headless | fas 1 är öppen på just den raden; hela premissen att operatören kan arbeta parallellt |
| **M-23 — grön start** | Hur lång tid från VC:s processtart till att port 8901 lyssnar, mätt över tio starter? | `27_operatorsflodet.md` §4:s tidsgräns är PRELIMINÄR tills detta finns |
| **M-24 — panelen på Windows** | Fungerar upptäckt, installation, panel och brygga på en Windows-installation av VC? | I17: allt är "klar på Linux, oprövad på Windows" |
| **M-26 — köns pollningströsklar** | Hur snabbt betas en godkänd post av, och hur länge är det rimligt att vänta? | `KO_POLL_S`, `KO_TIMEOUT_S`, och A-9:s 100 ms |
| **M-21, delen om tystnaden** | Vem skriver raden `modal oppen`, och stoppar en `messageBox` verkligen pumpen? Utan den raden kan läget `blockerad` inte fyras, och en öppen statusruta går inte att skilja från en död brygga | `28_lagen_och_aterhamtning.md` §1.0, §3.6:s undantag, `T_modal` |

Frågor som hör till operatören, inte till en mätning:

1. **Webbläsare eller terminal** som panelens yta? Specen antar webbläsare på
   loopback och namnger terminalen som alternativ. Inget är bestämt.
2. **Hur tjänsten startas.** Tillägget får inte starta processer. Ska
   installationen lägga en genväg, en tjänst, eller ska operatören starta den
   själv varje gång?
3. **Flera VC samtidigt.** Porten 8901 är en per maskin. Ska ett andra VC få
   en egen port automatiskt, eller ska det vara ett tydligt fel?
