# Faser

Regel: **varje fas stängs av en mätt grind, inte av en demo.** Ingen fas
förklaras klar på en observation. Ärvt arbetssätt ur källprojektets
commit-konventioner, där mätning och motbevisning är egna leverabler.

Planen är i två delar, och skillnaden är viktig.

**Uppstartsstegen (0–10)** svarar på frågan *finns kedjan?* Den bygger vägen
från en tom VC till ett nedladdningsbart tillägg som genererar PLC-kod. Den
frågan är nästan besvarad.

**Djupstegen (11–17)** svarar på frågan *är det bra?* Den frågan är knappt
påbörjad, och den är den som avgör om det här blir ett verktyg någon vill
använda. Operatörens krav — *"vi ska bygga världens bästa app"*, *"inget
slarv"*, *"missa ingenting"* — bor där, inte i uppstartsstegen.

---

## Uppstartsstegen

| # | Fas | Levererar | Grind som stänger fasen | Läge |
|---|---|---|---|---|
| 0 | **Eget testprefix** | `~/.wine-vc-test`, klon av det fungerande, med VC + licens | VC startar i testprefixet och når licensservern. Operatörens prefix rörs aldrig av oprövad kod | **stängd** |
| 1 | **Bryggan** | `vc_assist/__init__.py` + `bridge.py`, TCP 8901 | Tur och retur från tjänsten: skickad kodsträng ger JSON-rad tillbaka. **Provtagningstakten mätt i Hz** | **stängd** |
| 2 | **Ögat** | `vc_eyes.py`, provtagning + analys + domstext | På en handbyggd bra och en handbyggd trasig cell: ögats dom matchar facit i båda. Trasig cell **måste** fällas | **stängd** |
| 3 | **Grinden** | `vc_eyes_gate.py` som parsar ögats utdata | Guld endast när varje cell passerar. Okänd klass ⇒ inte guld | **stängd** |
| 4 | **API-index** | sökbart index ur `vc_python_api.json` + AST-validering mot schemat | Modellen kan inte anropa ett verktyg eller argument som inte finns. Mätt över N försök: noll uppfunna namn | **stängd** |
| 5 | **Scenbygge** | katalogindex, spawn via URI, koppling via `canConnect`/`connect` | N mållayouter byggda: noll kollisioner, alla gränssnitt kopplade | **stängd** |
| 6 | **PLC-bandet** | OpenPLC v4, OPC UA, genererad signalkarta och deklarationer | Handskriven ST styr scenen genom OPC UA. Tur och retur mätt i ms | **stängd** (M-39) |
| 7 | **ST för en station** | skelett + deklarationer genererade, modellen skriver sekvensen | Grind 1–5 gröna. Ögat säger PASS. **L1-guld** | **STÄNGD** (M-49, M-50): grind 1–5 gröna, ögat PASS, L1-guld; fem trasiga fall fällda av ögat |
| 8 | **Komposition** | flera stationer | Guld per station, sedan guld för linan. **L2** | **STÄNGD** (M-73, M-74): två stationer på en lina, guld i fem celler, och fem trasiga fall som ögat fäller i linan och släpper igenom i båda enstationskörningarna |
| 9 | **Bänken** | scenariosamling med facit | Tre tal rapporterade: första försöket, efter k varv, fel per klass | **alla tre talen mätta** (M-80): första försöket 0 av 4, efter ett reparationsvarv 4 av 4, baslinjen 4 av 4 i varv 1. Slingan drevs för hand |
| 10 | **Paketering** | nedladdningsbart tillägg | Ren maskin: klona, installera, kör. Fungerar utan handpåläggning. **Kräver fas 12** | **ren Linux-maskin prövad** (M-90): tom ubuntu:24.04, klona → `sok` → `installera --mal` fungerar, 11 filer verifierade på plats, ominstallation skriver 0. Noll importer utanför standardbiblioteket. Kvar: att VC startar med det installationen lade dit |

## Fas 0 är inte valfri

Skälet är mätt: en oprövad uppstartskrok i operatörens `My Commands` fällde
VC:s uppstart och gav ett blinkande svart fönster mitt i arbetet.
Ingen oprövad kod går in i det prefix operatören använder.

## Ordningen är inte godtycklig

Ögat före generatorn. Utan domare är resten en kodgenerator utan dom, och
då mäter vi ingenting. Källprojektets egen historia visar samma sak:
positionsproxyn fick ljuga i flera veckor tills ögat fanns att jämföra mot.

---

## Djupstegen

Var och en av dessa är tillagd därför att en **mätning** visade att den
behövdes. Ingen av dem är en idé; varje rad pekar på talet som föranledde den.

| # | Fas | Varför den finns | Grind som stänger fasen |
|---|---|---|---|
| 11 | **Klassisk baslinje** (PASSERAD, M-62) | `R-01`: ingen har publicerat vår loop, ingen leverantör publicerar ett korrekthetstal, och varje akademiskt tal är kompileringsgrad på en annan uppgiftsmängd. Att ställa vårt tal mot LLM4PLC:s 72 % vore samma kategorifel operatören redan fångat en gång | En regelbaserad generator utan språkmodell körd över **samma** bank med **samma** domare. Fas 9:s tal rapporteras alltid som par: vårt mot baslinjens. Ett tal utan baslinje publiceras inte |
| 12 | **Verktygskedjan i repot** (Linux passerad, M-56) | `M-48`: STruC++ ligger i en sessionskatalog, och npm-paketet som `paket.kompilera` kräver finns inte längre på maskinen. Grind 1 går att köra här och nu, men **inte på en ren maskin utifrån repots egna instruktioner** | Ett skript i repot hämtar STruC++, OpenPLC v4 och node, med **fastspikad version och kontrollerad hash**, och grind 1 kör efteråt. Trasigt fall: en manipulerad nedladdning måste avvisas på hashen |
| 13 | **Windows** | `M-44`: nio fynd med fil och rad, varav ett tyst och totalt — tilläggsmappen hittas inte när Dokument ligger i OneDrive, och hela systemet dör efter en lograd. Allt är byggt och mätt under Wine | M-44:s **16 numrerade protokollpunkter** körda på en riktig Windows-maskin, var och en med sitt förutbestämda gröna svar. Ingen punkt får besvaras med "borde fungera" |
| 14 | **Harnessens hårdhet** (PASSERAD, M-53) | `M-46`: **17 av 46 regler är mekaniserade, 29 är bara bedda**. Blocket om mätta fällor är sämst, 2 av 8 — och det är fällor som ger tal som *ser rimliga ut* | Kvoten mekaniserat/bett mätt om vid varje körning, med ett **golv som bara får gå uppåt** (samma spärr som tröskelskulden). Varje mekanism har en trasig fixtur som föll före den fanns. En regel som ärligt inte går att mekanisera står som `EJ_MEKANISK` med skäl |
| 15 | **Ögat på djupet** (MÄTT mot VC, M-86/M-87/M-88/M-97) | Operatörens krav: *"programmatiskt kunna förstå vad som pågår i en scen … detta måste bli riktigt jävla bra"*, och tidsserier över **alla objekts positioner**. `M-42` lade PLC-värdena på ögats tidsaxel; resten av `42_ogat_utbyggt.md` är ospecificerat i faser | Tidsserie över varje objekt i scenen, PLC-värdena på samma axel, och domar som fäller på sekvens, timing, grepp, kollision och genomflöde — var och en med en trasig cell som måste fällas. Hopfogningens osäkerhet mätt, inte antagen. **Mätt i en körande VC (2026-09-05):** `M-86` hela scenen i meter båda vägarna, 812 objekt i serien, noll driv, 4,3 µs per komponent och prov; `M-87` hopfogningens tak mätt mot VC:s brygga, `RUN` i 604 av 604; `M-88` **4 av 5** domare fäller VC-byggda celler ensamma (grepp, sekvens, timing, kollision) med `station_bra` PASS som kontroll — genomflödesdomaren sa **PASS på en svulten station** (inert `vcStatistics`, `state ''`), lagat till INCONCLUSIVE med VC-raden som fixtur, men **ingen VC-byggd cell fäller den** (`State` går inte att sätta utan process); `M-97` fas 8:s OGILTIG för PLC-axeln i tre lager, känd SIGSTOP-störning: jitter fällde `station_bra` till INCONCLUSIVE, taket **håller inte under processtopp** (7 av 300, +1,09 s). **Öppet:** ingen riktig PLC (kopplarvarvet efterliknat), P15-7 inte kört, genomflöde fälls bara syntetiskt, braketten på körningsnivå har bara fällt fixturer |
| 16 | **Planeringslagret** (PASSERAD, M-63) | Operatörens krav, ordagrant: *"Man ska kunna sätta upp instruktioner, bygga denna scen, med dessa, med villkor och ordning av processer osv, där spec ska kunna detaljeras från grundrequest"*. `22_planeringslagret.md` är 384 rader spec utan en fas som bygger den | En grundbeställning i fritext blir en detaljerad, körbar byggplan med villkor och processordning — och planen **avvisas** när den är omöjlig, i stället för att byggas halvt. Trasigt fall: en beställning som motsäger sig själv måste fällas med vilket villkor som krockar |
| 18 | **Befintlig anläggning in** (MÄTT, M-89; premissen M-75) | Operatörens fråga, och ett verkligt driftproblem: originalkoden är ofta borttappad. Två vägar in, och den ena är nästan gratis — ett **inspelat I/O-spår** från en riktig linje har redan bänkens facitform | Ett spår från en befintlig anläggning blir ett facit, en modell skriver ST som återger det, och domaren dömer med samma mekanik som i fas 9. Trasigt fall: ett spår som aldrig visat ett läge får **inte** ge ett facit som påstår något om det läget. **MÄTT (M-89)**: härledningen i `bank/anlaggning.py` bär täckning per påstående, domen faller genom `bank/domare.py` oförändrad, och grinden har fyra felkoder med var sin trasig fixtur och var sitt kontrollfall. Talen: **28 av 28** av människans förreglingar återfinns ur ett provspår, **3 av 28** ur ett produktionsspår; **12 av 18** handskrivna invarianter går inte att döma ur produktionsspåret och **0 av 18** ur provspåret; `EMG_OK` gick aldrig till 0 i något av de fyra produktionsspåren. Modellen: fyra Claude-agenter fick BARA inspelningen och skrev ST; **3 av 4** uppfyller bankens handskrivna facit. Ur ett **produktionsspår** blir samma siffra **0 av 2** — koden återger inspelningen och saknar ändå tidsvakten, larmen och förreglingarna. **Öppet: ingen riktig anläggning är inspelad** — källan är bankens egna referenslösningar, och vägen "läsa uppladdningsformatet" är omätt |
| 17 | **Vad användaren ser** (PASSERAD, M-64 + M-93) | Operatörens krav: *"användaren vill förmodligen också gärna kunna veta vad som händer också när saker arbetar"*. Hela systemet rapporterade till loggar och mätfiler, alltså till oss, inte till användaren | Medan en körning pågår kan användaren se vad som händer, vilken grind som fällde och varför, och vad systemet **inte** vet. Trasigt fall: ett fällt läge får aldrig se ut som ett arbetande. **Stängd:** `M-64` byggde ytan; nu sjutton regler med var sin trasig fixtur, varav `Y12` kräver att ögats egna `SECTION LIMITS`-rader står i avsnittet om vad systemet inte vet och inte bara inne i rapporten; `M-93` gav den två förare som för protokollet medan de kör och en spegling som går att läsa ur en annan process — och som **åldras mot läsarens klocka**. En läsare som fryser klockan sa ARBETAR i 60 av 60 avläsningar av en död körning, och fälls nu av S2. Kvar (M-93 §8): fem av sju rapportytor saknar förare, och ingen VC, brygga eller modell har passerat koden |

## Vad baslinjen mätte, och varför det ändrar hur fas 9 måste läsas

`M-62` byggde den regelbaserade baslinjen och mätte tre saker som gör fas 9:s
tal svårare att tolka än de såg ut att vara.

**Golvet är högt.** Ett program som **styr ingenting** passerar grind 1, 2 och 3
på **37 av 37** uppgifter och uppfyller **252 av 349** mekaniska påståenden. De
arton människoskrivna motbeviseni — vart och ett ett verkligt
driftsättningsfel — får **94,8 %**.

Följden är en regel: **ett procenttal ur en påståenderäkning får aldrig bli
huvudtalet.** Det mäter till största delen att programmet är ett program.

**Baslinjen löser 4 av 4 spårfacituppgifter** på sin bästa nivå, i **varv 1**,
med noll `F1`, `F2` och `F4`. Ribban ligger alltså där. Rapporterar fas 9 fyra
av fyra är det **oavgjort mot en mallkompilator**, och det ska stå med de orden.

**Talet är inte vår egen tolks åsikt.** Baslinjens kod kördes genom STruC++:s
byggda binär, scan för scan: 33 sekvenser, 3060 scan, 15 354 signalavläsningar,
**noll avvikelser**. Det betalar halva `M-45`:s öppna punkt; OpenPLC-halvan står
kvar.

**Där en modell kan visa något en regel inte kan** — flera parallella aktörer,
datastrukturer, grenar, kapacitet — finns i dag **inget facit som kan döma
det**. Bänken är alltså inte diskriminerande på just de ställen som skulle
avgöra frågan, och `M-62 §6` pekar ut de fem billigaste uppgifterna att ge
spårfacit.

## Varför djupstegen ligger i den ordningen

**11 och 12 före 9 och 10.** Ett bänktal utan baslinje går inte att tolka, och
en paketering som inte kan hämta sin egen verktygskedja är inte paketerad. De
två är förutsättningar, inte förbättringar.

**13 kan köras när som helst** — den väntar bara på en Windows-maskin. Den är
skriven som ett protokoll just därför: den dagen maskinen finns ska ingen behöva
tänka ut vad som ska provas.

**14 före 16.** Planeringslagret låter en språkmodell fatta fler beslut. Att
utöka modellens frihet innan reglerna är mekaniserade är att lita på prosa i
precis det läge där prosa är svagast.

**17 sist, men inte minst.** Den är den enda fasen som riktar sig till någon
utanför det här bygget.

**18 är den enda fasen som inte handlar om att generera något nytt.** Den
handlar om att förstå en anläggning som redan går.

### Två vägar in, och spåret är den enklare

**Läsa koden.** Tillverkarens uppladdningsformat — L5X, AWL, SCL, en
projektfil. Hur mycket det bär skiljer sig kraftigt: Rockwell lagrar hela
projektet med symbolnamn, Siemens S7-300/400 ger bytekod som ligger nära STL men
utan kommentarer, nyare optimerade block ger mindre, och CODESYS bär källan bara
om någon kryssat i rutan. Vilka format som faktiskt går att läsa ska **mätas mot
riktiga filer** innan fasen lovar något.

**Lyssna på signalerna.** Ett inspelat I/O-spår från den körande linjen — ur den
befintliga PLC:ns OPC UA-server om den har en, annars fältbussen (Profinet,
EtherNet/IP, Modbus TCP) eller en parallell avlyssning på I/O-plinten.

Den andra vägen är nästan gratis för oss, och skälet är formen. Vad man får när
man lyssnar är inte koden utan **beteendet**: vilka utsignaler som följde på
vilka insignaler, och när. Det är exakt bänkens facitform
(`61_st_generering.md`): *(insignaler vid t) → (förväntade utsignaler vid
t + fördröjning)*. En inspelad timme **är** ett facit, utan översättning. Loopen
sluts med delar som redan finns: tolken, domaren, ögat.

### Fyra saker som måste stå i fasens grind, annars blir den ett falskt grönt

1. **Ett spår visar bara vad som hände.** Larmhanteringen som aldrig löste ut,
   nödstoppssekvensen ingen provade, återstarten efter ett fel som inte
   inträffade — allt osynligt. Man rekonstruerar normaldriften och tror man har
   logiken. Grinden måste därför räkna **vilka lägen spåret faktiskt besökte**
   och vägra påstå något om resten. Det är samma krav som `bank/README.md`
   ställer på gränsscenarier, och av samma skäl.
2. **Tider är observerade, inte specificerade.** En 100 ms-timer går inte att
   skilja från en 120 ms-timer utan tillräckligt många upprepningar, och en
   timer som löst ut en gång är ett stickprov med n = 1. Varje härledd tid ska
   bära sin nämnare.
3. **Korrelation är inte orsak.** Två utsignaler som alltid följs åt kan ha ett
   gemensamt villkor eller inget samband alls.
4. **Säkerhetsfunktioner rekonstrueras aldrig ur ett spår.** Det är inte en
   försiktighetsregel utan gränsen i `50_grindar.md`.

### Och förbehållet som inte får glömmas bort

**Maskinkod går inte tillbaka till structured text.** STruC++ kompilerar bara åt
ena hållet, och dekompilering är inte vägen. Det som finns att arbeta med är
uppladdningsformatet eller spåret — aldrig binären.

## Vad som ännu inte har en fas, och varför

* **Verktygsbiblioteket** växer i rundor (`M-47`: 33 % av API-ytan rörd, 4 av
  58 arbetssteg utan Python-yta alls). Rundorna har ingen slutpunkt att stänga,
  så det är ett löpande arbete och inte en fas. Täckningstalet rapporteras vid
  varje runda.
* **Robotytorna i `formaga.YTOR`** kräver först en mekanism som skriver om
  förmågerapporten när scenen ändras. Skälet står i `verktyg/robotik.py`.
* **Fler PLC-fabrikat.** Beckhoff ADS och S7 finns som .NET-dll:er i VC, men vår
  väg går utanför VC:s uppkopplingslager. Ingen efterfrågan är mätt.

## Djupstegen 19–22: kapaciteten, inte kedjan

Steg 0–10 svarade på *finns kedjan?*. Steg 11–18 på *är den bra?*. De här fyra
svarar på en tredje fråga som ingen fas ställt: **räcker den till det användaren
faktiskt gör?**

Anledningen att de skrivs nu är mätt, inte anad. Åtta specdokument på
sammanlagt ~3 600 rader hade **ingen fas alls** — samma form som fas 16 hade
innan den fick en (*"384 rader spec utan en fas som bygger den"*). De fyra
tyngsta av dem står nedan; fas 22 ensam tar tre av de åtta (`23`, `24` och
`25`, tillsammans 1 292 rader).

En sak till som fas 19–22 visade, och som gäller alla fyra: **en spec utan fas
åldras utan att någon ser det.** Fas 19 fann att täckningsanalysen aldrig körts,
fas 20 att ingenting var byggt ur komponentmodellen, och fas 22 att
`23_llm_granssnitt.md` räknade 21 verktyg medan registret bar 122. Ingen av de
tre glidningarna syntes i något test, därför att ingen grind läste specen.

| # | Fas | Varför den finns, med belägg | Grönt |
|---|---|---|---|
| 19 | **Personatäckningen** (STÄNGD, M-100) | `48_personaprofiler.md` och `47_verktygstackning.md` hade ingen fas. `48` sa själv att den var *"underlag för täckningsanalysen i 47"* — och den analysen hade aldrig körts som en grind | **STÄNGD** (M-100): `48` skriven uttömmande till **sju profiler och 228 arbetssteg**, var och en med verkan, API-krav och besked om täckning. **144 täckta, 8 utanför räckvidd (`UI`/`.NET`, bevisade mot båda indexen), 76 obyggda** — per profil 27 % (komponentbyggaren) till 89 % (driftsättaren). `tests/protocol/kor_fas19_tackning.py` fäller **15 trasiga fall** med var sin kod plus 3 oläsbara specer, och nämnaren är låst av ett golv per profil: ett steg som tystnat bort ger rött trots att procentsatsen stiger |
| 20 | **Komponentmodellen** | `49_komponentmodellen.md` svarar på vad som krävs för att `canConnect` blir sant, och vilken minsta uppsättning en TRANSPORTÖR, MATARE, SÄNKA och BUFFERT behöver. Allt var belagt eller mätt **i text** — ingenting byggt ur specen | De fyra minsta uppsättningarna byggda **ur specen**, i riktig VC: `canConnect` sant mellan rätt par, och material som verkligen rör sig igenom. Trasigt fall: en komponent som saknar ett av specens krävda beteenden får **inte** kunna kopplas — och felet ska säga vilket beteende som fattas. **STÄNGD** (M-101): fyra uppsättningar byggda ur specen och HELA enligt modellens egen granskning, **7 av 7** `canConnect` sanna där specen säger ja, **13 produkter** genom hela kedjan (mellanrum exakt 3,0000 s, rörelse 400,0000 mm/s, 2+1+10 = 13), och **4 av 4** trasiga fixturer fällda — var och en mot en hel tvilling på samma plats, med det saknade beteendet namngivet. Tre påståenden refuterades på vägen, ett av dem specens eget **MÄTT** om klassnamnen |
| 21 | **Bänken i skala** | `M-80` mätte fyra uppgifter. Banken bär **51**, och 47 av dem har inget spårfacit. Fas 8 byggde **en** lina med två stationer. Ett tal ur fyra uppgifter säger lite om kapacitet, och n = 1 per uppgift säger ingenting om spridning | Spårfacit för minst 20 av bankens 51 uppgifter, körda genom hela kedjan mot riktig VC och OpenPLC, med **upprepning** så spridningen går att rapportera. Trasigt fall: ett facit som härletts ur samma tolk som dömer det måste avvisas — facit hör utanför koden som prövas |
| 22 | **Modellagret** (STÄNGD, M-102) | `23_llm_granssnitt.md`, `24_samtalsloopen.md` och `25_kontextbudget.md` var **1 292 rader** spec om hur en språkmodell ska tala med systemet, och **ingen av de tre hade en fas** — samma form som fas 16 hade innan den fick en. Och specen hade åldrats mätbart: den räknade **21** verktyg och 11 074 byte schema, medan registret bär **122** och **98 324 byte**. Det tal som gjorde fasen akut är kvoten: verktygsschemat är **19 %** av ett fönster på 128 000 tokens mot postens tak på 10 % — den tröskel specen själv satte för när urvalet måste byggas är alltså **passerad** | **STÄNGD** (M-102): budgeten mätt över **207 riktiga verktygssvar** ur repots egna handlare och **95 riktiga turer** ur efterlevnadsbanken. Talen: **0** anmärkningar på kapade svar vid fyra fönsterstorlekar, **0** bokföringsfel, **0** turer utanför tillståndsmaskinen, urvalsträff **87 av 105** anrop där **varje missat anrop är skrivande** och varje läsande täcks, och **22 av 22** nåbara övergångar besökta. `tests/protocol/kor_fas22_modellagret.py` fäller **13 trasiga fall** med var sin kod, och fyra till fälls av enhetsproven. De tre namngivna: ett kapat svar som **ser helt ut** fälls av `K2_SER_HELT_UT`, tystnad som märkts klar av `T3_TYST_GODKANNANDE`, och ett för stort svar som tappat felet av `K4_FEL_TAPPAT` |

## Fas 23: användarlagret — vad användaren ser när något har dött

Fas 17 svarade på *vad händer medan det arbetar?* Den här svarar på den fråga
som kommer direkt efter, och som ingen fas rört: **vad ser användaren när något
har dött, och kommer systemet tillbaka?**

De två är inte samma fråga, och skillnaden är hela fasen. En körning som lever
kan berätta vad den gör — dess egna händelser bär svaret. Ett delsystem som dog
kan inte berätta någonting alls. Det som finns att tolka är en **tystnad**, och
tystnad kan bara tolkas av någon annan än den som tystnade.

| # | Fas | Varför den finns, med belägg | Grönt |
|---|---|---|---|
| 23 | **Användarlagret** (STÄNGD, M-103) | `26_appen.md`, `27_operatorsflodet.md` och `28_lagen_och_aterhamtning.md` bar 1 043 rader spec om vad användaren möter — och **ingen av de tre hade en fas**, samma form som fas 16 och 19. Mätt före koden fanns: `28` specar **sju lägen**, och **noll** av dem gick att härleda ur någon kod i `svc/`. Ordet `degraded` stod i pumpens `ping`-svar och lästes av ingen. Noll moduler räknade en avläsnings **ålder** mot läsarens klocka — den mekanism fas 17 mätte som ARBETAR i 60 av 60 | När ett delsystem slutat svara säger ytan **vad** som dog, **varför**, om något försöker igen och vad operatören själv kan göra — och den fäller sin egen grind. Trasiga fall som måste falla: en härledning som räknar en gammal avläsning som ett svar, en som räknar en lyckad `connect()` som ett livstecken, en visning som lovar ett nytt försök när ingenting försöker, och ett läge som inte gick att avgöra som visas som grönt eller tyst utelämnas. **STÄNGD (M-103):** `svc/vc_assist_svc/aterhamtning/` med **14 regler**, var och en med minst en trasig fixtur, **88 prov** utan VC. Talen: en härledning som fryser klockan sa LEVANDE i **60 av 60** avläsningar av en sond som dog efter den första — med läsarens egen klocka **3 av 60**. `connect()` mot en lyssnande socket som ingen accepterar lyckades **20 av 20**, median 0,12 ms, och `ping` svarade **0 av 20** (regel L-1:s premiss, mätt på Linux; Wine står kvar i M-25). Av **18 orsaker** har **3** ett automatiskt försök och **2** ett som är mätt att kunna lyckas — i **15 av 18** försöker ingenting igen, och ytan säger det med de orden. Mellan **31,8 %** och **42,9 %** av ytan handlar om vad systemet inte vet |

### Varför en visning behöver en egen grind

En visning är en dom om systemets tillstånd, ställd till den enda som inte kan
kontrollera den. Vi som bygger kan läsa loggen; användaren kan bara läsa ytan.
En yta som säger fel har därför en värre asymmetri än en logg som säger fel.

Fas 17 fällde två sorters lögn: en **renderare** som skriver något annat än
protokollet säger, och en **läsare** som fryser klockan. Fas 23 lägger till en
tredje, och den är den som hör återhämtningen till: en **härledning**. Ett läge
är en slutsats om en tystnad, och den som drar slutsatsen kan dra fel — räkna en
lyckad `connect()` som liv, återanvända en avläsning som blivit gammal, eller
låta en klocka som gått bakåt betyda att ingen tid gått. Alla tre ger samma
svar: *ansluten* om något som inte svarar.

Grinden räknar därför om varje delsystems läge **själv**, ur de råa
avläsningarna och läsarens klocka. En grind som frågar den den dömer mäter till
slut sig själv.

### De tre trasiga fallen som fasen finns för

1. **Ett dött läge får aldrig se ut som ett arbetande** — och inte heller som
   *"Ett problem uppstod, vi försöker igen"* när ingenting försöker igen. Den
   meningen är värre än tystnad: den ber användaren vänta på något som inte
   händer.
2. **Ett återhämtningsförsök som inte kan lyckas får inte rapporteras som
   pågående.** Kanskapen har tre värden, aldrig två, och den räknas om vid
   varje visning — slår bryggan av sin självstart mitt i ett självstartsförsök
   blir försöket omöjligt utan att någon rör det.
3. **Ett tillstånd som inte gick att avgöra ska stå som `obestämt`** — aldrig
   som grönt, aldrig tyst utelämnat (fail-closed, I3).

### Vad fasen INTE stänger

* **Ingen sond går av sig själv.** Ytan läser avläsningar; vem som gör dem och
  hur ofta är inte bestämt (`28_lagen_och_aterhamtning.md` §9 fråga 5).
* **Ingen väg tillbaka har körts mot en VC som verkligen gick ned.** Alla fyra
  dödsfallen är framprovocerade mot attrapper, och det står som en permanent
  ovisshet i **varje** visning — inte som en fotnot i ett protokoll.
* **Läget `blockerad` kan inte fyras.** Raden `modal oppen` är spec'ad i
  `26_appen.md` A-3 och finns inte i koden. Väntar på **M-21**.
* **Windows är oprövat**, hela vägen (M-44, I17).

## Regeln som gäller alla faser, också de nya

En fas är klar först när dess acceptansprotokoll i `tests/protocol/` är **körd
och grön, inklusive de trasiga fallen**. Ett protokoll utan trasiga fall är
ingen grind — det är en förhoppning som har fått ett filnamn.
