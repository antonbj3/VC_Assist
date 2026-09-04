# R-01 — LLM-genererad ST och mjuk-PLC på Linux

**Destillat av:** en researchkörning 2026-09-04 med fyra parallella webbagenter
(A: kan LLM skriva ST, B: verifiering och säkerhet, C: mjuk-PLC på Linux,
D: Modbus→OPC UA-bryggor). Rå utdata 504 kB, aldrig läst av någon förrän nu.

**Stämpel:** allt här är **DOK** enligt `docs/spec/01_kalldisciplin.md`. Ingenting
är kört på den här maskinen. Ett DOK-påstående får aldrig ensamt bli ett
designbeslut, och den regeln gäller varje rad nedan.

**Vad som kastades:** ungefär två tredjedelar. Hela avsnitt C (jämförelse av
mjuk-PLC) och hela avsnitt D (Modbus-bryggor) är redan avgjorda och **mätta** i
det här repot — `docs/spec/60_plc.md`, `M-20`, `M-38`, `M-39`. Researchen kom
fram till samma val vi redan gjort, och två av dess agenter var dessutom oense
om huvudfrågan (se nedan). Den delen ändrar ingenting. Även säkerhetsgränsen och
"simuleringen är felsökare, aldrig bevis" står redan i `docs/spec/50_grindar.md`.

Det som återstår ändrar däremot bänken och fas 7 på elva punkter, varav en är
en ny felklass som två av huvudtrådens egna dokument redan lutar sig mot utan
att kunna namnge den.

---

## 1. Vad detta ändrar i bygget

### 1.1 Bänkens huvudtal får inte vara kompileringsgrad

Fältet har mätt fel storhet i tre år. SemaPLC (aug 2026) mätte samma metoder
statiskt och dynamiskt: statiska poäng skiljde baslinjerna med ~4 poäng,
körningspoäng med 9. Slutsatsen är att allt som mättes statiskt före 2026 inte
mätte det man trodde.

Vår bänk mäter redan genom ögat, alltså dynamiskt. Det som saknas är att det
står **utskrivet varför**, så att ingen senare frestas rapportera "andel som
kompilerar" som huvudtal för att det är billigt att mäta.

→ `docs/spec/80_bank.md`, avsnittet "Tal vi rapporterar". Förslag i §5.

### 1.2 Ingen modellkontroll läggs in i grindkedjan

Frestelsen finns: LLM4PLC och Agents4PLC lutar sig båda på nuXmv, och det låter
starkt. Två mätta skäl att låta bli i fas 7:

* PLCverif täcker **~40 % respektive ~25 %** av SCL/ST som språk (CERN, se
  tabellen). Ingen verktygskedja täcker full ST.
* SemaPLC rapporterar att uppgifter som bär en TON-timer gav **noll avgörbara
  utfall** under formell verifiering. Tidsfel passerar alltså den grinden tyst.

Grindkedjan i `docs/spec/50_grindar.md` har redan ingen modellkontroll. Skälet
är bara inte nedskrivet, och ett oskrivet skäl bjuder in ett återfall.

→ `docs/spec/50_grindar.md`. Förslag i §5.

### 1.3 Timing och kapplöpning får bara dömas av ögat

Följer av 1.2. `F6` timing och `F7` kapplöpning fälls i dag av ögat, vilket är
rätt. Regeln ska stå som en regel och inte som en tillfällighet: **ingen statisk
grind får någonsin få domsrätt över `F6` eller `F7`.** Det är precis där de
publicerade verifierarna går blinda.

→ `docs/spec/82_felklasser.md`.

### 1.4 Flank och latch är fältets omätta hål, och vi står redan i det

Researchagenten sökte uttryckligen efter mätningar på `R_TRIG`/`F_TRIG` och
SR/RS-latchfel i LLM-litteraturen och fann **inga**. Felmoden är folklore hos
praktiker, inte data i något arbete.

**Klassen är redan bärande i två dokument, men saknar kod.**
`docs/spec/61_st_generering.md` listar "Flanker" först bland det som brukar gå
fel och konstaterar att felklassen är osynlig för grind 1 och 2.
`tests/protocol/fas7_stationen.md` gör den till trasigt fall **T3**,
"nivåläsning där en flank krävs", och kräver att den fälls av ögat och av
ingenting annat. Fas 7 ska alltså rapportera vilken grind som fällde — men det
finns ingen felklass att rapportera *vad* som var fel.

Vår bank har redan materialet. Mätt med
`python3 -c` över `bank/uppgifter/*.json` 2026-09-04: **nio** uppgifter bär
flank- eller nivåresonemang i `orsak` eller `failure_modes` — `T-01`, `T-03`,
`T-04`, `T-06`, `T-91`, `S-01`, `S-03`, `L-04`, `A-06`. `T-01`:s hela `orsak` är
ordagrant "kommenderas öppen på fotocellens nivå i stället för på dess stigande
flank".

Men de nio är utspridda på fyra felklasser (`F5`, `F6`, `F7`, `F8`). Klassen
går därför inte att rapportera, och det enda tal ingen annan har går förlorat i
våra egna kolumner.

**Förslaget är en ny felklass, inte nya uppgifter.** Uppgifterna finns.

→ `docs/spec/82_felklasser.md` + omtaggning av nio poster i `bank/uppgifter/`.

### 1.5 Föroreningsspärr: ingen bänkuppgift får härstamma ur OSCAT

OSCAT är både träningskorpus och testmängd i LLM4PLC, AutoPLC och Haag m.fl.
Kontamineringen är strukturell, inte hypotetisk. LLM4PLC tränar på 596
OSCAT-filer och testar på 40 undanhållna ur samma bibliotek.

Vår bank är byggd ur VC-scener och branschpraxis och rör inte OSCAT. Det är en
verklig fördel, och den är värd noll om den inte skyddas av en regel. Med
operatörens krav — *"industrirealistiska måste vara precis industrirealistiska"*
— är detta den enda punkt där vi objektivt står över fältet i dag.

→ `docs/spec/80_bank.md` + en lintregel.

### 1.6 Modellen får aldrig skriva sitt eget facit

Koziolek m.fl. (ABB) lät GPT-4 generera testfall för ST och körde dem på riktigt
genom MatIEC + GCC + en egen mjuk-PLC. Resultat: **0–50 % korrekta assertions**
på enkla funktionsblock, mestadels felaktiga på komplexa, och **sämst just på
block med timers och tillstånd**.

Det är den bästa publicerade mätningen av hur bra en språkmodell bedömer sin egen
PLC-kod, och svaret är dålig. Regeln "facit skrivs före försöket" (`M6` i
`docs/spec/81_mallschema.md`) har därmed en mätt motivering i stället för en
princip. Skärpningen som saknas: facit får inte heller skrivas av samma modell
som senare ska lösa uppgiften.

### 1.7 Det finns ingen extern baslinje. Ingen alls.

Detta är det viktigaste för hur fas 9 får formuleras.

* **Ingen** har publicerat kedjan LLM → mjuk-PLC → 3D-simulering → återkoppling
  → reviderad kod. Det närmaste är SemaPLC, som kör koden men mot I/O-scenarier,
  inte mot en anläggningsmodell.
* **Ingen leverantör** — Siemens, Beckhoff, CODESYS, Rockwell — publicerar en
  enda korrekthetssiffra.
* Alla akademiska tal är självrapporterade på egenbyggda mängder och aldrig
  oberoende replikerade.

Två följder, och båda är obekväma:

1. **"Vi utklassar alla lösningar" går inte att belägga med ett jämförande tal.**
   Det finns inget publicerat tal som mäter samma sak som vårt. Att skriva
   "vi når X % mot LLM4PLC:s 72 %" vore samma kategorifel som en gång redan
   fångats i det här projektet: ett benchmarktal ur ett annat upplägg använt som
   om det vore vårt mål. `docs/spec/90_invarianter.md` I7 säger redan detta.
   Den ärliga formuleringen är att **vi mäter något ingen har mätt**, och att
   den enda giltiga jämförelsen är vår egen klassiska baslinje under samma
   budget — den som redan står i `docs/spec/83_scenarier.md`.
2. **Ingen har rapporterat felmoderna åt oss.** Fas 7 kommer att hitta
   felklasser som inte står i `82_felklasser.md`. Mätningen som stänger fas 7
   bör därför ha ett eget fält för nyfunna klasser, i stället för att pressa in
   dem i `F14`.

### 1.8 Nämnaren skrivs alltid ut

Agents4PLC:s hela lättmängd är **16 uppgifter**. En uppgift är 6,25
procentenheter. Deras tal har en decimal.

Vår bank har 47 uppgifter (mätt: `ls bank/uppgifter/*.json | wc -l`,
2026-09-04), varav tre felklasser bärs av exakt en uppgift var — `F12`, `F13`,
`F14`, redan noterat i `bank/README.md`. En andel per felklass för dem är ett
tal utan innebörd.

Regeln som räcker, och som inte kräver någon tröskel: **varje andel redovisas
med nämnaren utskriven, "k av n".** Då syns tunnheten av sig själv.

### 1.9 Säkerhetsgränsens motivering kan skärpas, gränsen står

`docs/spec/50_grindar.md` säger redan rätt sak. Researchen tillför tre saker:

* Varför gränsen håller: fritt formulerad ST är en FVL-artefakt. Den faller på
  **LVL-kravet, V-modellkravet och spårbarhetskravet samtidigt** — IEC 61508-3 /
  61511 kräver säkerhetslogik i begränsat variabelt språk, och ISO 13849-1:s
  SRASW-krav gäller bara om koden skrivs i ett sådant.
* **EU:s maskinförordning 2023/1230 träffar inte det här.** Bilaga I gäller
  säkerhetskomponenter med självutvecklande ML-beteende som *utför*
  säkerhetsfunktionen i drift, med anmält organ, från 20 jan 2027. Statiskt
  genererad kod fryst vid bygget omfattas inte. Om någon någon gång åberopar
  förordningen som skäl för vår gräns är det fel skäl. Skälet är 61508 och 13849.
* **Ingen leverantör, inget standardorgan och inget anmält organ förbjuder
  uttryckligen AI-genererad kod i säkerhetsfunktioner.** Frånvaron är fyndet.
  Förbudet är strukturellt, inte skrivet. Vår gräns är alltså strängare än
  bokstaven, och det ska den vara.

### 1.10 Reparationsslingans tak: vad andra behövde, och varför det inte är vårt

`docs/spec/61_st_generering.md` säger att slingans tak ska vara en mätt storhet
och skrivas som en konstant med härkomst på samma rad. Researchen ger **inte**
det talet, och kan inte ge det. Den ger två upplysningar som ändå är värda att
ha innan mätningen görs:

* Haag m.fl. körde **9 DPO-iterationer** för att ta kompileringen från 7 % till
  ~70 %. Det är träning, inte en reparationsslinga per uppgift, och siffran är
  inte överförbar.
* SemaPLC:s körningsgrindade slinga kostade **34,1 modellanrop per uppgift** mot
  baslinjernas 6,9. Att grinda på körning i stället för på statiska mått kostade
  alltså ungefär fem gånger så många anrop.

Följden för fas 7 är budgetmässig, inte normativ: en slinga som grindar på ögat
kommer att kosta betydligt mer per uppgift än en som grindar på kompilatorn, och
den kostnaden ska planeras in. Invariant I7 gäller: **34,1 är inte vårt tak.**
Vårt tak sätts av vår egen mätning av var reparationskurvan planar ut.

### 1.11 Att facit är ett spår och inte en text har stöd

`docs/spec/61_st_generering.md` slår fast att facit är ett spår av in- och
utsignaler i tiden, inte en förlagetext, eftersom två riktiga lösningar kan se
helt olika ut. Det är samma val som SemaPLC gjorde, och deras mätning visar vad
valet är värt: statiska mått skilde metoderna med ~4 poäng, spårjämförelse med
9. Beslutet var redan taget här. Det har nu en extern mätning bakom sig.

---

## 2. Mätbara påståenden med härkomst

Kolumnen **Belägg** säger hur den här körningen fick talet: `hämtad` = artikeln
eller sidan lästes, `sökträff` = talet kommer ur en sökresultatsammanfattning.

| Påstående | Vem mätte | På vad, med vilket facit | Tal | Belägg |
|---|---|---|---|---|
| Kompilerbar ST från LLM före och efter reparationsloop | Fakih m.fl., UC Irvine + Siemens Technology, ICSE-SEIP 2024, arXiv 2401.05443 | pass@1 över 40 undanhållna OSCAT-filer (596 tränings-, 40 testfiler). Facit = **kompilering**, inte beteende | **47 % → 72 %** | hämtad |
| Expertbedömd korrekthet, samma arbete | samma | blindad panel, skala 1–10, antal bedömare ej angivet | 2,25 → 7,75 (GPT-4); 2,25 → 6,5 (Llama-34B) | hämtad |
| Multiagent + formell verifiering, GPT-4o | Liu m.fl., Zhejiang, arXiv 2410.14209 | egen benchmark 23 uppgifter (16 lätta, 7 medel). Facit = pass, och *verifierbar* via nuXmv genom PLCverif | lätt **50,0 % pass / 68,8 % verifierbar**; medel **28,6 % / 42,9 %** | hämtad |
| Upplösningen i samma benchmark | samma | 16 uppgifter i lättmängden | 1 uppgift = **6,25 procentenheter** | hämtad |
| Kompileringsgrad mot verklig leverantörs-IDE | Yang m.fl., Beihang + Siemens Kina, arXiv 2412.02410 | 914 uppgifter (OSCAT 718, Siemens LGF 151, tävling 45). Facit = **enbart kompilering** | AutoPLC **92,90 % OSCAT / 92,72 % LGF**, mot GPT-4o 35,47 / 8,61 | hämtad |
| Korrekthet i samma arbete | samma | 65 mänskliga bedömningar, 5 bedömare | korrekthet 4,18/5, säkerhet 4,53/5 | hämtad |
| Kompilering *och* semantik samtidigt | Haag m.fl., arXiv 2410.22159 | Phi-3-medium-14B, DPO med RuSTy-kompilator och GPT-4 som semantikdomare, 200 utvärderingsintentioner (100 OSCAT, 100 APPS-konverterade) | kompilering **7 % → ~70 %**, semantik **~45 %**, **gemensamt ~39 %** | hämtad |
| Dynamiskt beteende mot baslinjer | SemaPLC, Midea AIRC / KUKA / SJTU / ZJU, aug 2026, arXiv 2608.18565 | projektspår, 65 uppgifter ur verkliga anläggningar. Facit = körning med tvingade insignaler och spårjämförelse | **52,2** mot baslinjer **22,4–31,4** | hämtad |
| Verifierad pass, funktionsspår | samma | 117 POU-uppgifter | **72,6 %**, +8,8 pp över Agents4PLC | hämtad |
| Statiskt mått skiljer inte metoder åt | samma | samma baslinjer mätta båda sätten | statiskt ~**4** poängs spridning, körning ~**9** | hämtad |
| Formell verifiering kan inte avgöra timers | samma, tabell 5 | uppgifter som bär TON | **noll avgörbara utfall** | hämtad |
| Kostnaden för körningsgrindningen | samma | modellanrop per uppgift | **34,1** mot 6,9 | hämtad |
| RAG:s effekt på kompilering, annan leverantör | Kersting, Rummel (Mitsubishi Electric Europe), Benndorf (Fraunhofer IOSB-INA), arXiv 2511.09122 | GX Works3 / iQ-R, 100 frågor per konfiguration. Facit = kompilering | GPT-5+RAG **87 %**, GPT-4.1+RAG 73 %, GPT-4.1 utan RAG **38 %** | hämtad |
| Språktäckning i formell verifiering | CERN, PLCverif, arXiv 2203.17253 | andel av språket som verktyget översätter | STL ~66 % / ~55 %, **SCL ~40 % / ~25 %** | hämtad |
| Tillståndsexplosion | samma | numeriska variabler | en 16-bitars int = 2¹⁶ tillstånd | hämtad |
| LLM-skrivna testassertions | Koziolek m.fl. (ABB), arXiv 2405.01874 | 10 funktionsblock ur OSCAT (upp till 200 rader), 5–10 testfall per block, körda genom MatIEC → GCC → egen mjuk-PLC, täckning via GCOV | **0–50 % korrekta assertions** på enkla fall, mestadels felaktiga på komplexa; sämst med timers och tillstånd | hämtad |
| Grafisk logik ur kravtext | Spec2Control (ABB), arXiv 2510.04519 | 10 styrnarrativ, 65 testfall, ABB:s egna verktyg. Facit = kopplingsnoggrannhet, **ingen körning, ingen anläggningsmodell** | 98,6 % kopplingsnoggrannhet, 94–96 % arbetsbesparing | hämtad, endast sammanfattning |
| Hallucinerade funktioner hos en leverantör | Fabian Bause, Beckhoff, företagets egen nyhetssida | uttalande, ingen mätning | rörelsefunktioner "som inte alls finns" | hämtad |

**Om ett tal ovan förs vidare någon annanstans i repot ska hela raden följa med,
inte bara talet.** Var och en av dem mäter något annat än vad vi mäter.

---

## 3. Vad som INTE går att lita på

| Vad | Varför det inte bär |
|---|---|
| **"17,3 % fel vid gränsöverskridande mot 7,1 % vid normaldrift (SemaPLC)"** i `bank/README.md:43`, `bank/schema.py:122` och `tests/enhet/test_bank.py:215` | Den här körningen läste SemaPLC:s resultat och fann **inte** de talen. Den återgav 72,6 %, 52,2 mot 22,4–31,4, kostnaden 34,1 och TON-fyndet — men ingenting om 17,3 eller 7,1. Frånvaro är inte motbevis. Men flaggan i `docs/motbevis_2026_09_04.md` §5c står kvar, och nu med en andra källkontroll som inte hittade talet heller. **Designregeln (gränsscenarier i varje uppgift) är rätt oavsett.** Talet ska antingen beläggas mot artikeln eller strykas som motiv och ersättas med SemaPLC:s faktiska fynd, som pekar åt samma håll. |
| Alla korrekthetstal från leverantörer | Det finns inga. Siemens Industrial Copilot, Beckhoff TwinCAT Chat/CoAgent, CODESYS AI + MCP-server och Rockwell FactoryTalk Copilot publicerar **noll** mätetal och lägger uttryckligen korrekthetsansvaret på ingenjören. Allt annat som cirkulerar om dem är marknadsföring. |
| "72 %", "92,9 %", "87 %" som mått på om koden *fungerar* | Alla tre är kompileringsgrad. Ingen av dem säger något om beteende. |
| Varje tal i tabellen som jämförelse med varandra | Olika mängder, olika facit, olika svårighet, aldrig oberoende replikerade. De ligger i samma tabell för att de är fältet, inte för att de är jämförbara. |
| Alla siffror mätta på OSCAT | OSCAT är samtidigt träningskorpus i flera av arbetena. Kontaminering, strukturell. |
| Denna körnings egen slutsats om OpenPLC v4:s OPC UA-server | **Två av dess agenter var oense.** Den ena läste `OPCUA_PLUGIN_FEATURES.md` och ett fungerande exempel och sa server; den andra sa "endast planerat". Frågan är avgjord av **vår egen mätning**, inte av researchen: `M-20` och `M-39` körde faktiskt mot `opc.tcp://…/openplc/opcua`. Det är ett rent exempel på att en webbsökning inte är en mätning. |
| CODESYS-detaljerna (pris, MCP-server, containerstöd) | Sidan svarade 429 vid hämtning; talen kommer ur sökträffar. Spelar ingen roll för oss, vi har valt bort CODESYS. |
| Arcade.PLC och ESBMC-PLC | Endast titlar lästes. Inga påståenden att bygga på. |
| CERN:s ICALEPCS-tal om statisk analys i stor skala | Artikeln finns, textlagret gick inte att läsa. Inga tal. |
| Praktikercitat från PLCtalk-forumet | Tråden svarar 403 vid hämtning. Andrahandsuppgift. |
| Hela avsnitt D, Modbus→OPC UA-bryggor | Sakligt oanvändbart för oss. Bygger på premissen att OpenPLC saknar OPC UA, vilket `M-20` motbevisade på den här maskinen. Node-RED, `serhmarch/modbusua`, Softing, Ignition Edge, `python-snap7` — allt är dött material så länge v4 står. |
| "Kör Ignition Edge dag ett för att bevisa att VC:s klient ansluter" | Rådet är rimligt i sig och helt inaktuellt. `M-38` mätte att VC:s Python-API har **noll** yta mot uppkoppling, och slingan sluts genom tjänsten, inte genom VC:s egen OPC UA-klient. |

---

## 4. Prior art vi bör härma eller undvika

### Härma

* **SemaPLC:s grundhållning.** Kör koden och jämför spår. Det är samma val som
  vårt öga redan gör. Deras egen formulering är att körning, inte statisk
  poängsättning, är det trogna provet. Vi är rätt ute och bör säga varför.
* **LLM4PLC:s ordning.** Grammatik och kompilator före allt annat, och
  reparationsloop mot kompilatorns egen utdata. Vår grind 1 är samma sak.
* **AutoPLC:s deklarationshantering.** De hämtar API-fall och rekommenderar
  funktionsblock i stället för att låta modellen minnas dem. Vår grind 3 går
  längre: deklarationerna **genereras** ur signalkartan och modellen får inte
  skriva dem alls. Vi är strängare, och det är rätt riktning.
* **Koziolek: kör testerna på riktigt.** MatIEC → GCC → mjuk-PLC → GCOV. Att
  faktiskt exekvera är vad som skiljer en mätning från en gissning.
* **Att redovisa antalet uppgifter bredvid procenten.** Agents4PLC gör det, och
  det är enda skälet att deras tal går att bedöma alls.

### Undvika

* **Att mäta på OSCAT.** Både kontaminerat och fel domän: bibliotek av
  funktionsblock, inte stationslogik mot en anläggning.
* **Att göra formell verifiering till en grind för ST.** Täckningen är ~25 %,
  och det som faller utanför är precis timers och scancykelsemantik — det
  svåraste i PLC-kod. En grind som går blind exakt där felen bor är värre än
  ingen grind, för den ger en falsk grön.
* **Att rapportera kompileringsgrad som huvudtal.** Det är fältets systemfel.
* **Agents4PLC:s "closed-loop".** Ordet betyder formell verifiering hos dem.
  Ingen simulering, ingen fysik, ingen anläggningsmodell. Om vi använder ordet
  ska vi mena hela vägen ut i scenen och tillbaka.
* **Spec2Control-formen.** Höga tal (98,6 %) på ett mått — kopplingsnoggrannhet —
  som mäts utan att något körs. Det är den frestelse vår bänk finns för att stå
  emot.
* **Leverantörernas kommunikationsform.** Fyra stora företag levererar
  kodgenererande copiloter utan ett enda publicerat mätetal. Vi ska inte likna
  dem.

### Öppen fråga, inte ett beslut

Researchen nämner `vc-thirdparty/vcengine-automation` (VcEngine-Runner: kör en
simulering en angiven tid på maxfart och skriver utdata till fil) som möjlig
drivrutin för satsvisa körningar. Det förekommer ingenstans i repot i dag
(`grep -rn vcengine` ger noll träffar, 2026-09-04). Fas 9 behöver 47 uppgifter
× minst 3 körningar, och hur de körs är obesvarat. **Detta är en kandidat att
undersöka, inte ett val.** Påståendet är obekräftat och kommer ur en sökträff.

---

## 5. Föreslagna spec-tillägg

Specen ägs av huvudtråden. Nedan är förslag, formulerade så att de går att
klistra in. Ingenting av detta är infört.

### 5.1 `docs/spec/82_felklasser.md` — ny felklass

```diff
 | `F5` | Sekvens | stegen sker i fel ordning | **ögat**, TIMING |
+| `F15` | Flank och latch | villkoret läses på nivå i stället för på flank, eller ett tillstånd hålls inte kvar när villkoret försvinner | **ögat**, TIMING |
```

Och under **Sorteringsregler**, ny punkt:

```diff
+5. **`F6` och `F7` får aldrig fällas av en statisk grind.** Formell
+   verifiering av ST kan inte avgöra timersemantik: SemaPLC (arXiv 2608.18565)
+   rapporterar noll avgörbara utfall för TON-bärande uppgifter, och PLCverif
+   täcker ~25 % av ST (arXiv 2203.17253). Se `docs/research/R-01`. En statisk
+   dom över timing vore en falsk grön i den ände där felen faktiskt bor.
+
+6. **`F15` är nyare än de andra klasserna och finns av ett skäl.** Ingen
+   publicerad LLM-utvärdering mäter flank- eller latchfel (R-01 §1.4).
+   `61_st_generering.md` och `tests/protocol/fas7_stationen.md` (trasigt fall
+   T3) bygger båda på klassen utan att kunna namnge den. Nio
+   bankuppgifter bär redan materialet men är i dag taggade `F5`, `F6`, `F7`
+   eller `F8`, så klassen går inte att rapportera. Omtaggning av `T-01`,
+   `T-03`, `T-04`, `T-06`, `T-91`, `S-01`, `S-03`, `L-04` och `A-06` gör den
+   mätbar utan en enda ny uppgift.
```

### 5.2 `docs/spec/50_grindar.md` — varför kedjan slutar där den slutar

Efter tabellen "Kedjan, i ordning":

```diff
+## Varför ingen modellkontroll
+
+Kedjan har medvetet ingen grind för formell verifiering, trots att LLM4PLC och
+Agents4PLC båda bygger på nuXmv. Två skäl, båda med källa i
+`docs/research/R-01`:
+
+* PLCverif täcker **~40 % respektive ~25 %** av SCL och ST som språk (CERN,
+  arXiv 2203.17253). Inget verktyg täcker full ST.
+* Uppgifter som bär en TON-timer gav **noll avgörbara utfall** under formell
+  verifiering (SemaPLC, arXiv 2608.18565).
+
+En grind som går blind precis där PLC-kod är svårast producerar falska gröna.
+Den kostnaden är högre än nyttan. Om en modellkontroll någon gång läggs till
+ska den vara en **upplysning bredvid domen**, aldrig en grind, och aldrig med
+domsrätt över `F6` eller `F7`.
```

Och under **Säkerhetsgränsen**:

```diff
+Varför gränsen håller, och vad den *inte* vilar på: fritt formulerad ST är en
+FVL-artefakt och faller på LVL-kravet, V-modellkravet och spårbarhetskravet
+samtidigt (IEC 61508-3 / 61511, ISO 13849-1). Den vilar däremot **inte** på
+EU:s maskinförordning 2023/1230, vars bilaga I gäller säkerhetskomponenter med
+självutvecklande beteende i drift, inte statiskt genererad kod fryst vid
+bygget. Ingen leverantör och inget standardorgan förbjuder uttryckligen
+AI-genererad kod i en säkerhetsfunktion; förbudet är strukturellt, inte
+skrivet. Vår gräns är alltså strängare än bokstaven, med avsikt.
+Se `docs/research/R-01`.
```

### 5.3 `docs/spec/80_bank.md` — tre tillägg

Under **Tal vi rapporterar**:

```diff
+**Huvudtalet är dynamiskt, aldrig statiskt.** Andel som kompilerar rapporteras
+aldrig som bänkens resultat. Skälet är mätt av andra: statiska poäng skiljde
+baslinjer med ~4 poäng medan körningspoäng skilde dem med 9 (SemaPLC, arXiv
+2608.18565, se `docs/research/R-01`). Kompileringsgrad får finnas som
+diagnostik under `F1`, aldrig som rubrik.
+
+**Varje andel skrivs med sin nämnare, "k av n".** Agents4PLC redovisar en
+decimal på en mängd där en uppgift är 6,25 procentenheter. Tre av våra
+felklasser bärs i dag av en uppgift var. Nämnaren gör tunnheten synlig utan
+att någon tröskel behöver hittas på.
```

Under **Baslinjen som ska slås**:

```diff
+**Det finns ingen extern baslinje.** Ingen har publicerat kedjan LLM →
+mjuk-PLC → 3D-simulering → återkoppling → reviderad kod, och ingen leverantör
+publicerar korrekthetstal (`docs/research/R-01` §1.7). Inget publicerat tal
+mäter det vi mäter. Att ställa vårt tal mot LLM4PLC:s 72 % eller AutoPLC:s
+92,9 % vore ett kategorifel — de talen är kompileringsgrad på OSCAT. Invariant
+I7 gäller: andras tal är inte gränser för våra. Den enda giltiga jämförelsen
+är vår egen klassiska baslinje under samma budget.
```

Ny rubrik, efter **Facit**:

```diff
+## Föroreningsspärr
+
+Ingen bänkuppgift får härledas ur OSCAT, ur Agents4PLC:s benchmark eller ur
+AutoPLC:s 914-uppgiftsmängd. Skälet är mätt: OSCAT är samtidigt träningskorpus
+och testmängd i LLM4PLC, AutoPLC och Haag m.fl. (`docs/research/R-01`).
+En uppgift modellen kan ha sett i träningen mäter minne, inte förmåga.
+
+Banken är byggd ur VC-scener och branschpraxis och är därmed ren av
+konstruktion. Det är den enda punkt där vi i dag objektivt står över fältet,
+och det gäller bara så länge regeln hålls.
```

### 5.4 `docs/spec/81_mallschema.md` — facit och författare

Under **Lintregler**, efter `M6`:

```diff
+`M6` har en mätt motivering och inte bara en princip: när GPT-4 fick skriva
+testfall för ST och de kördes på riktigt var **0–50 % av assertions korrekta**
+på enkla funktionsblock och mestadels felaktiga på komplexa, sämst på block
+med timers och tillstånd (Koziolek m.fl., arXiv 2405.01874, se
+`docs/research/R-01`). En modell som bedömer sin egen PLC-kod är en dålig
+domare. Därav också skärpningen: **facit får inte skrivas av samma modell som
+ska lösa uppgiften.**
```

### 5.5 `docs/spec/70_faser.md` — fas 7:s mätning

```diff
 | 7 | **ST för en station** | skelett + deklarationer genererade, modellen skriver sekvensen | Grind 1–5 gröna. Ögat säger PASS. **L1-guld** |
```

Tillägg under tabellen:

```diff
+## Fas 7 mäter också det vi inte visste att vi skulle mäta
+
+Ingen har publicerat den här loopen (`docs/research/R-01` §1.7). Det betyder
+att ingen har rapporterat felmoderna åt oss. Mätningen som stänger fas 7 ska
+därför bära ett eget avsnitt för **felklasser som inte fanns i
+`82_felklasser.md` när fasen började**. De hör inte hemma i `F14`, som enligt
+`82_felklasser.md` regel 3 ska vara nära noll och inte fyllas på.
```

`tests/protocol/fas7_stationen.md` kräver redan att körningen rapporterar vilken
grind som fällde och antalet reparationsvarv. Tillägget är att den också ska
kunna säga att en fällning inte passade i någon känd klass.

### 5.6 `docs/spec/00_index.md` — registrera katalogen

```diff
+## Research
+
+| Dok | Innehåll |
+|---|---|
+| `docs/research/R-01_llm_st_och_softplc.md` | LLM-genererad ST och mjuk-PLC — publicerat läge, med härkomst per tal |
+
+Allt i `docs/research/` är **DOK**. Ingenting där är mätt på den här maskinen,
+och ingenting där får ensamt bli ett designbeslut.
```

---

## 6. Bank: ingenting gick att extrahera direkt

Researchen innehåller **inga** användbara ST-testfall, benchmarkuppgifter eller
facit. Den namnger benchmarkmängder — OSCAT 718 uppgifter, Agents4PLC 23,
AutoPLC 914, SemaPLC 117 + 65 — men återger inte en enda uppgiftstext, inte en
rad ST och inget facit. Ingen ny fil lades därför i `bank/uppgifter/`.

Det är rätt utfall och inte en brist. Enligt §1.5 vore en uppgift kopierad ur
OSCAT eller Agents4PLC dessutom **förbjuden** i vår bank.

Det enda banken behöver ur researchen är omtaggningen i §5.1, och den kräver
noll nya uppgifter.

---

## 7. Var den råa utdatan finns

`/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/tasks/a929c970fa7dd500d.output`
— 504 kB JSONL-transkript, 174 rader. Slutrapporterna ligger på rad 167, 170 och
173 (samma rapport skriven om tre gånger när bakgrundsnotiser kom in; versionerna
motsäger varandra på ett ställe, AutoPLC 92,90 mot 92,7 %). De fyra
underagenternas rapporter, som bär beläggen, ligger i syskonfilerna
`aee21290ee21a6071` (A), `a900184ba972b9028` (B), `ad18619cec107ca08` (C) och
`aef71537c50584885` (D). Katalogen är tillfällig och överlever inte en omstart.
