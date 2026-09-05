# M-114 — ingen av vägarna in ger tillbaka källkoden

**Datum:** 2026-09-05
**Typ:** RESEARCH, inte bygge. Inget i repot är ändrat. Alla kommandon nedan
kördes i en engångsmiljö (`/tmp/.../scratchpad/plc_libs`, `.../plcopen`),
inte i repots venv, och är inte committade.
**Gäller:** fas 18 i `docs/spec/70_faser.md`, det öppna stycket *"Två vägar
in"* och den öppna punkten i `M-89`: *"Vilka tillverkarformat som faktiskt
bär symbolnamn och logik är fortfarande omätt mot riktiga filer."*
**Bygger på, upprepar inte:** `M-75` (vad ett spår avslöjar — 28/28 mot 3/28,
under 6 spårrader/gren) och `M-89` (`bank/anlaggning.py` — täckningsgrinden,
28/28 ur provspår mot 3/28 ur produktion, 3/4 modeller uppfyller facit ur
provspår, 0/2 ur produktion mot människans facit). De talen upprepas inte
här. Den här mätningen svarar på fyra frågor M-89 lämnade öppna, inte på
samma fråga igen.

## Svaret i klartext

Operatören frågade två saker. Det första — *"lyssnar man på kablarna och
lägger ihop signalerna"* — är redan mätt: **ja, det räcker längre än man
tror, men bara till det linjen faktiskt gjorde medan man lyssnade** (M-89).

Det andra — *"maskinkod till structured text"* — har nu tre separat mätta
svar, och de säger samma sak på tre olika sätt:

1. **Läsa en levande PLC över nätverket** (S7comm, CIP, ADS, MC-protokollet)
   ger **variabelnamn och värden**. Ingen av de fyra biblioteken jag
   installerade och undersökte har en enda metod som returnerar programlogik.
   Siemens är delvis ett undantag — se nedan — men det den ger är
   **kompilerad bytekod, inte ST**.
2. **Dekompilering** av den bytekoden finns som forskning, inte som verktyg
   man pekar och kör. Det bästa akademiska arbetet (ICSREF, NDSS 2019)
   producerar en kontrollflödesgraf och en disassemblering — inte IEC
   61131-3-källkod. Det nyaste arbetet (CLEVER, IEEE TIFS 2024) *hävdar* sig
   rekonstruera källkod, men variabelnamnen i den rekonstruktionen är
   härledda av verktyget, inte de ursprungliga. Kommentarer försvinner vid
   kompilering och kommer inte tillbaka av något verktyg jag hittat.
3. **PLCopen XML** duger mekaniskt som mellanformat för vår genererade ST —
   jag byggde och validerade en fil mot det riktiga schemat — men det är en
   väg mellan *ingenjörsverktyg*, inte en väg ur en körande anläggning: ingen
   av de fyra protokollen ovan skickar eller tar emot PLCopen XML.

**Den sammanfattande bilden:** tre dörrar in, och ingen av dem är källkoden.
Spåret ger beteende. Protokollet ger variabler. Bytekoden ger struktur.
Namnen och kommentarerna — det en människa skrev för att en annan människa
skulle förstå programmet — finns bara på ett ställe: i originalet. Om det är
borttappat kommer de inte tillbaka någon väg.

---

## Fråga 1 — vad går att läsa ur en PLC i drift?

### Metod

Fyra bibliotek installerades från PyPI i en tom venv (`python3 -m venv`,
Python 3.13.11) 2026-09-05 och undersöktes med `dir()`/`inspect.signature`
mot den *installerade koden*, inte mot dokumentation:

```
pip install python-snap7 pycomm3 pyads asyncua pymcprotocol
```

| paket | version (PyPI, 2026-09-05) | protokoll | fabrikat |
|---|---|---|---|
| `python-snap7` | 3.1.2 | S7comm | Siemens |
| `pycomm3` | 1.2.16 | EtherNet/IP (CIP) | Rockwell/Allen-Bradley |
| `pyads` | 3.6.0 | ADS/AMS | Beckhoff |
| `asyncua` | 2.0.1 | OPC UA (IEC 62541) | fabrikatoberoende |
| `pymcprotocol` | 0.3.0 | MC-protokollet | Mitsubishi |

Ingen CODESYS-motsvarighet hittades: `pycodesys`, `codesys-python`,
`python-codesys`, `codesyscontrol` gav alla **HTTP 404** mot
`pypi.org/pypi/<namn>/json` (2026-09-05). Det är ett indicium, inte ett
bevis — ett paket under ett annat namn kan finnas — men det stämmer med att
CODESYS' eget gateway-protokoll är fabrikatets interna transport, inte en
publicerad enhetsprotokollspecifikation som S7comm, ADS, CIP eller
MC-protokollet.

### Vad API-ytan faktiskt exponerar (mätt, inte läst i en README)

**`python-snap7` (Siemens, S7comm) — enda biblioteket med ett
uppladdningsanrop:**

```
full_upload(block_type, block_num) -> (buffer, size)   # START_UPLOAD/UPLOAD/END_UPLOAD
upload(block_num) -> bytearray
list_blocks() / list_blocks_of_type() / get_block_info()
download(data, block_num)   # skriva tillbaka
```

`full_upload`s egen docstring: *"Upload a block from PLC with header and
footer info... The whole block (including header and footer) is copied into
the user buffer."* Det här är samma sak `70_faser.md` redan skrev om
Siemens: **bytekod, inte text.** `get_block_info` ger metadata (typ,
storlek, checksumma, språkflagga) — inte namn, inte kommentarer.

**`pycomm3` (Rockwell, CIP) — inget uppladdningsanrop finns:**

```
LogixDriver: get_tag_list, get_tag_info, read, write, get_plc_info,
             get_plc_time, get_module_info
```

Ingen metod heter `upload`, `get_routine`, `get_program` eller liknande.
CIP-taggdatabasen (namn, typ, aktuellt värde) är allt som är nåbart via det
öppna protokollet. Studio5000s "Upload"-knapp som operatören kan tänkas
tänka på är en *annan*, odokumenterad kanal mellan Rockwells egen mjukvara
och processorn — inte CIP, och inte något `pycomm3` implementerar.

**`pyads` (Beckhoff, ADS) — symboltabellen, inte programmet:**

```
get_all_symbols, get_symbol, read_by_name, read_structure_by_name,
write_by_name, add_device_notification
```

ADS ger symbolnamn (inklusive STRUCT-layout) och värden — mer strukturerad
information än CIP eller MC-protokollet ger, men fortfarande data, inte
POU-källa.

**`pymcprotocol` (Mitsubishi, MC-protokollet) — rått minne per adress:**

```
batchread_bitunits/wordunits, randomread/write, remote_run/stop/reset/pause
```

Adresser som `D100`, `M0` — inga symbolnamn alls om inte enheten själv
mappar dem, och inget programanrop.

**`asyncua` (OPC UA) — vad servern väljer att exponera, och inget annat:**

```
browse_nodes, get_node, read_values, import_xml/export_xml
```

OPC UA är ett informationsmodellprotokoll: adressrymden är helt och hållet
det PLC-tillverkarens OPC UA-server har valt att publicera. En PLC:s OPC
UA-server mappar praktiskt taget alltid till **variabler** — det är precis
vad M-89:s inspelning (via `svc/vc_assist_svc/st/tolk.py`, samma form en OPC
UA-prenumeration skulle ge) redan visade i siffror.

Repo-anteckning: OPC UA-vägen är redan i drift här — `M-108` kör OpenPLC
Runtime v4.2.1 och läser tillbaka värden över
`opc.tcp://172.17.0.3:4840/openplc/opcua`. Det är samma sorts yta som mättes
ovan, mot vår egen runtime i stället för en tillverkares.

### Officiellt dokumenterat protokoll, eller reverse-engineerat?

Det här skiljer sig påtagligt mellan fabrikaten och avgör hur säker marken
är, oavsett vad man läser ut:

| fabrikat | protokoll officiellt dokumenterat av tillverkaren? | källa |
|---|---|---|
| Beckhoff | **Ja** — ADS/AMS-specifikationen ligger publikt i Beckhoffs eget informationssystem, och Beckhoff driver själva `github.com/beckhoff/ads` | infosys.beckhoff.com/content/1033/tcadscommon; github.com/Beckhoff/ADS |
| Mitsubishi | **Ja** — "MELSEC Communication Protocol Reference Manual" (SH-080008) är en publikt nedladdningsbar PDF från Mitsubishi Electric | dl.mitsubishielectric.com/dl/fa/document/manual/plc/sh080008/sh080008ab.pdf |
| Rockwell/ODVA | **Ja, som öppen standard** — EtherNet/IP och CIP är ODVA:s publicerade specifikationer, inte Rockwells interna protokoll | ODVA (allmänt känt, ej hämtat i den här mätningen — se LIMITS) |
| Siemens | **Nej** — S7comm har ingen officiell Siemens-specifikation. Allt den öppna ekosystemet vet kommer från reverse engineering: Snap7 (Davide Nardella), Wireshark-dissektorn, `libnodave` | github.com/SCADACS/snap7; sökresultat 2026-09-05 |
| CODESYS | **Nej, och inget brett bibliotek finns** — inget PyPI-paket under rimliga namn (se ovan) | egen pip/pypi-sökning 2026-09-05 |

Konsekvensen är juridisk, inte bara teknisk: att prata CIP, ADS eller
MC-protokollet är att implementera en publicerad specifikation — samma sorts
handling som att implementera HTTP. Att prata S7comm är att använda en
tredje parts reverse-engineerade protokollimplementation. Det är
**vanligt och väletablerat** (Snap7 har funnits sedan 2013 och används
brett industriellt), men det vilar inte på samma dokumenterade grund.

### Går att göra / lagligt / utan tillverkarens licens — tre olika frågor

* **Går att göra, utan tillverkarens verktyg:** ja för alla fem, för
  variabelnivån. Mätt ovan för fyra av fem via faktiskt installerbara
  bibliotek. CODESYS saknar motsvarande öppna bibliotek men OPC UA (om
  aktiverat på styrningen) eller ett fältbussprotokoll (Modbus TCP,
  Profinet) fungerar ändå, precis som `70_faser.md` redan föreslår.
* **Går att göra lagligt:** för de öppet specificerade protokollen (ADS,
  MC-protokollet, CIP) finns ingen reverse-engineering-fråga alls — man
  implementerar en publicerad spec. För S7comm är frågan
  reverse-engineering av ett *protokoll* via klientimplementation, vilket är
  en annan juridisk kategori än att dekompilera *en tillverkares
  körbara mjukvara* (se fråga 2). Jag har inte funnit och letar inte här
  efter en juridisk dom som avgör saken för Sverige/EU specifikt.
* **Utan tillverkarens licens:** samtliga fem kräver **ingen** Siemens/
  Rockwell/Beckhoff/Mitsubishi/CODESYS-programvara eller -licens för att
  läsa variabler. Det som eventuellt krävs är att skyddsnivån på PLC:n
  tillåter läsning (S7-1200/1500: "PUT/GET" måste vara aktiverat i CPU:ns
  skyddsinställningar — annars svarar S7comm-anrop med fel, oavsett bibliotek).
  Det är inte en licensfråga utan en åtkomstinställning satt av den som
  programmerade anläggningen.

---

## Fråga 2 — dekompilering: vad är verkligt, vad är önsketänkande?

Repots eget påstående (`70_faser.md`): *"Maskinkod går inte tillbaka till
structured text. STruC++ kompilerar bara åt ena hållet, och dekompilering är
inte vägen."* Den här mätningen provocerar det påståendet mot det starkaste
jag kunde hitta, i stället för att bara upprepa det.

### Det starkaste som finns, mätt mot primärkällan — inte mot en sammanfattning

| verktyg / arbete | år | vad det FAKTISKT producerar (kontrollerat mot README/abstract, inte en sammanfattningssida) | källa |
|---|---|---|---|
| **ICSREF** (Keliris & Maniatakos) | NDSS 2019 | **SVG-grafer och disassembleringslistor.** Egen README, hämtad direkt: *"generates... SVG graphs"* med *"hyperlinks to the disassembly listings of each function."* Ingen IEC 61131-3-källa. Ingen nämnd återvinning av variabel-, symbol- eller POU-namn. Bara CODESYS **v2**, inte v3. | github.com/momalab/ICSREF, README.rst hämtad 2026-09-05 |
| **CLEVER** ("From Control Application to Control Logic") | IEEE TIFS 2024, vol 19, s. 8685–8700 | Påstår sig **rekonstruera källkod** via en egen mellanrepresentation (IR) och en *heuristisk* dataflödesanalys för variabelberoenden, följt av "sequential parsing" för källkodsrekonstruktion. Ordet **heuristisk** är författarnas eget — variabelnamnen i utdatan är verktygets gissningar, inte de tappade originalen. | dl.acm.org/doi/abs/10.1109/TIFS.2024.3402117 (abstrakt, ej fulltext läst här) |
| **PLC-BinX** | arXiv 2605.17392 (2026) | **Funktionsnivå-semantisk representation**, uttryckligen INTE IEC 61131-3-källkod. Stödjer CODESYS v3, "GEB", OpenPLC v2/v3. Ingen ST/ladder-utdata alls — två nedströmsuppgifter (verktygskedje- och funktionalitetsprediktion), inte kodåtervinning. | arxiv.org/pdf/2605.17392 |
| **CLIK on PLCs** (Kalle et al.) | BAR/NDSS 2019 | Delar upp kontrollogik i konfigurations-, kod- och databelock. Allmän decompiler-litteratur som artikeln bygger på är entydig: *"much semantic information, including... function names, variable names, and comments, is discarded during compilation because the target machine does not need such information."* | ndss-symposium.org/wp-content/uploads/bar2019_74_Kalle_paper.pdf |
| Siemens själva, om sitt eget format | — | TIA Portals egen dokumentation: vid uppladdning av ett online-program **"all network comments, rung comments, instruction descriptions, and block titles"** går förlorade. S7-300/400 stödjer **ingen** kommentaråtervinning alls. | docs.tia.siemens.cloud (uppladdningssidan, sökresultat 2026-09-05 — se LIMITS om källkvalitet) |

### Var gränsen faktiskt går

Tre nivåer, och alla verktyg jag hittat landar på samma sida av alla tre
gränserna:

1. **Struktur (kontrollflöde, blockindelning): återvinningsbar.** Det är
   vad ICSREF, CLEVER och PLC-BinX alla gör, med olika grad av automation.
2. **Variabelnamn: INTE återvinningsbara som de ursprungliga.** De
   kompilerade blocken bär adresser (`%IX0.0`, DB-offset), inte namn.
   CLEVER *genererar* namn heuristiskt; det är gissningar med samma
   epistemiska status som en dekompilerares `v1`, `v2` i vanlig
   mjukvarudekompilering (samma väletablerade fenomen — se DIRE,
   "Meaningful variable names for decompiled code", ICPC 2018 — sökt men
   inte läst i detalj här, allmänt känd litteratur om binärdekompilering).
3. **Kommentarer: aldrig återvinningsbara, hos någon tillverkare eller
   något verktyg jag hittat.** De kompileras bort och det finns ingen
   binär plats de kunde ha legat kvar i. Siemens egen dokumentation säger
   samma sak om sitt eget format.

**Slutsats om repots påstående:** det håller, och det håller *starkare* än
formuleringen i `70_faser.md` antydde. Det är inte bara att "STruC++
kompilerar åt ett håll" — det är att **hela forskningsfronten**, inklusive
det senaste arbetet från 2026, landar på strukturell återvinning och
uttryckligen INTE på namn eller kommentarer. Ingen av källorna jag hittat
hävdar motsatsen. Det gör påståendet till en B-gradad negativ slutsats:
sökningen var bred (fem verktyg/artiklar, tre decennier av
decompiler-litteratur i botten), gränsen är konsekvent över alla, och jag
har inte hittat ett enda motexempel — men jag har inte läst någon
fulltextartikel i sin helhet (se LIMITS), bara abstract/README mot
primärkälla.

### matiec / OpenPLC / Beremiz specifikt

Ingen av dessa har en dekompileringsväg. matiec, STruC++ (som repot
faktiskt använder — `M-56`, `M-108`) och OpenPLC:s C-kompileringssteg är
alla **ST/IL/LD/FBD/SFC → C → binär**, en riktning. Ingen av dem har ett
"reverse"-läge. Det är samma slutsats repot redan hade, nu bekräftad mot
verktygens egen dokumentation i stället för bara logiskt härledd.

---

## Fråga 3 — vad räcker ett spår till, jämfört med källkoden?

`M-75` och `M-89` mätte det här på repots egna fyra bankuppgifter — de
talen upprepas inte. Den här sektionen söker **extern förankring**: säger
den publicerade litteraturen om spec mining / process mining / automatinlärning
samma sak, oberoende av vår bänk?

### Process mining har exakt samma spänning, med egna namn på den

van der Aalsts fyra kvalitetsdimensioner för processupptäckt (*Quality
Dimensions in Process Discovery*, 2012; *Foundations of Process Discovery*)
är:

| dimension | vad den mäter | motsvarighet i fas 18 |
|---|---|---|
| **fitness** | modellen tillåter det loggen visade | vårt härledda facit uppfyller inspelningen (M-89: referensen klarar sitt eget spår, 4/4 uppgifter) |
| **precision** | modellen tillåter INTE beteende helt orelaterat till loggen | — |
| **generalization** | modellen generaliserar exempelbeteendet, inte bara radräknar loggen | **exakt M-89:s täthetsfynd**: ett facit som bara läser vid ändringar (för glest) missar defekten; ett facit taget som exakt tidskrav (för strikt) överbestämmer. Båda är fel på samma axel — generaliseringsgraden |
| **simplicity** | så enkel som möjligt | — |

Litteraturens egen formulering av riskerna: *"underfitting is the problem
that the model over-generalizes... allows for behaviors very different from
what was seen in the log"* och omvänt en modell som är *overfitting* — *"an
algorithm that simply enumerates the event log is useless."* Det sista är
ordagrant samma sak M-89 mätte som "täthetsfyndet" och "det motsatta felet":
ett för glest facit (underfitting mot verkligheten — accepterar det som
inte borde accepteras) och ett för strikt facit (overfitting mot just den
inspelade anläggningens timing).

**Det här är en äkta extern förankring, inte en tautologi**: process
mining-fältet uppfann sina fyra dimensioner för ett helt annat
tillämpningsområde (affärsprocesser ur transaktionsloggar) och långt innan
den här bänken fanns. Att fas 18 självständigt landade på samma spänning
(för glest kontra för strikt) är over-determination — två oberoende vägar
till samma slutsats.

Källa: van der Aalst, *"On the Role of Fitness, Precision, Generalization
and Simplicity in Process Discovery"*, Springer 2012 (link.springer.com/
chapter/10.1007/978-3-642-33606-5_19); van der Aalst, *"Foundations of
Process Discovery"* (vdaalst.com/publications/p1330.pdf) — abstrakt/
sammanfattning läst via sökning 2026-09-05, ej fulltext.

### Automatinlärning ur I/O-spår säger samma sak om täckning, med sitt eget språk

*"Learning Moore Machines from Input-Output Traces"* (arXiv 1605.07805,
2016) — hämtad och läst (sammanfattad av verktyg, se LIMITS) 2026-09-05:
den inlärda maskinen speglar **bara observerat beteende**. Tillstånd och
transitioner som aldrig syntes i spåren förblir okända för den inlärda
modellen — ingen formell fullständighetsgaranti oberoende av spårens
kvalitet. Det är samma påstående som fas 18:s första ärlighetskrav
("ett spår visar bara vad som hände") och `M-89`:s mätta 12 av 18
otäckta invarianter, uttryckt i automatinlärningens eget ramverk (Moore-
maskiner, inte tillståndsdiagram med grenar) i stället för vårt.

En nyare artikel i samma fåra, specifikt om PLC:er: *"Learning Automata of
PLCs in Production Lines Using LSTM"* (arXiv 2503.00631, 2025) — hittad i
sökningen, **inte läst här** (tidsbudget); den existerar som ett skäl att
tro att fältet redan försöker göra precis det operatören frågade om, men
ingen slutsats dras ur den i den här mätningen.

### Vad detta lägger till fas 18, utöver M-75/M-89

Inget nytt tal. Det nya är att täckningsregeln inte är en uppfinning för
den här bänken — den är en instans av ett runt 50 år gammalt, brett
studerat problem (k-tail går tillbaka till 1972, nämnt i sökresultaten) som
två helt olika forskningsfält (process mining, automatinlärning) oberoende
av varandra har byggt formella ramverk kring. Det är over-determination för
fas 18:s fjärde krav, inte en ny mätning av det.

---

## Fråga 4 — duger PLCopen XML (IEC 61131-10) som mellanformat?

### Vem skriver det, vem läser det — mätt mot verktygens egna repos, inte mot marknadsföring

| verktyg | status, mätt/källa |
|---|---|
| **Beremiz** | PLCopen XML (TC6-schemat) är Beremiz **eget interna projektformat** — inte export/import, utan hur projekt sparas på disk. Bekräftat i `beremiz/beremiz`-repot: `plcopen/tc6_xml_v201.xsd` finns där, och en verklig projektfil (`plcopen/Standard_Function_Blocks.xml`, hämtad direkt) validerar mot det schemat (mätt nedan). |
| **OpenPLC** | v2/v3:s editor bygger på Beremiz och ärver samma format. Källa: forumtråd av utvecklaren själv (`BenKissBox`, OpenPLC-forumet, inlägg 2021, uppdaterat 2021-05-13): *"the XML file format used within OpenPLC (and Beremiz...) has become a full IEC standard... published under IEC61131-10 norm."* — sekundärkälla (forumpost), inte primär standarddokumentation, men skriven av den som byggde formatet in i verktyget. |
| **CODESYS** | 3.5 exporterar via *Project → Export → PLCopenXML*, med tillverkarspecifika `addData`-tillägg. Nämnt i flera oberoende sökträffar, inte verifierat mot en riktig CODESYS-installation här (ingen licens/instans tillgänglig). |
| **TwinCAT 3 (Beckhoff)** | Har import/export av PLCopen XML via kontextmeny, enligt Beckhofs egen infosys-sida (`infosys.beckhoff.com/content/1033/tc3_plc_intro/2526208651.html`) — sidan nämnd i sökträff, inte fulltextläst här. |
| **Siemens TIA Portal** | Stödjer **inte** PLCopen TC6-XML. Egen proprietär SimaticML via TIA Openness API. Källa: flera sökträffar samstämmiga, men flera drar från samma lågkvalitetsdomän (se LIMITS) — grad **C**, inte mätt mot en riktig TIA-installation. |
| **Vår egen kedja** (`svc/vc_assist_svc/plc/openplc.py`) | **Använder PLCopen XML inte alls.** Grep över `svc/vc_assist_svc/plc/*.py` och `svc/vc_assist_svc/st/*.py` för `xml`/`XML`/`plcopen` gav **noll träffar**. Kedjan är ST-text → STruC++ → ZIP → OpenPLC v4:s REST `/api/upload-file`, rakt förbi Beremiz-editorlagret och dess XML-format helt. |

### Testet jag faktiskt körde, inte bara läste om

Jag byggde en representativ ST-kropp i skelettets egen deklarationsform
(`namn : TYP;`, ingen startvärdestilldelning — samma begränsning `M-89`
mätte i `svc/vc_assist_svc/plc/skelett.py`) och slog in den i ett minimalt
PLCopen-projekt med Pythons `xml.etree`:

```python
# fyra variabler: SYS_AUTO, EMG_OK (input, BOOL), ST260_RB_START (output, BOOL),
# tmrAck (local, TON — funktionsblocksinstans som <derived name="TON"/>)
# ST-kropp: IF SYS_AUTO AND EMG_OK THEN ... END_IF;  (representativ, inte extraherad ur en riktig lösning — se LIMITS)
```

Validerat med `lxml.etree.XMLSchema` mot **det riktiga schemat**
(`beremiz/beremiz@effe6529e45f`, filen `plcopen/tc6_xml_v201.xsd`, hämtad
2026-09-05, filen själv senast ändrad i det repot 2012-09-07 — 14 år
oförändrad, alltså en stabil målyta):

| fil | VALID mot `tc6_xml_v201.xsd`? |
|---|---|
| Beremiz' egen `Standard_Function_Blocks.xml` (kontrollfall — måste vara sann annars är testet ovärt) | **True** |
| min första wrapper, utan `<fileHeader>`/`<contentHeader>` | **False** — `SCHEMAV_ELEMENT_CONTENT`, saknat obligatoriskt element |
| min andra wrapper, med header-elementen tillagda | **True** |

Och ett rundturstest: ST-texten extraherad ur den validerade XML-filen är
**byte-för-byte identisk** med det jag stoppade in
(`p_el.text == original` → `True`).

**Det här är en mekanism, inte bara ett påstående:** ST i PLCopen XML ligger
som klartext i ett `<body><ST><xhtml:p>...</xhtml:p></ST></body>`-element
(bekräftat i den riktiga Beremiz-filen, inte bara i mitt eget bygge), inte
som ett kompilerat eller graf-serialiserat mellanformat. Det är därför
ingen information går förlorad: PLCopen XML bär **källtext**, inte bytekod,
så asymmetrin i fråga 2 (namn och kommentarer försvinner vid kompilering)
gäller inte här. En kommentar `(* ... *)` i ST-kroppen skulle ligga kvar
ordagrant, eftersom hela raden är text, inte parsead.

### Svaret

**Mekaniskt: ja**, vår genererade ST (flata deklarationer av elementära
typer plus funktionsblocksinstanser, en ST-sats-kropp) uttrycks utan
förlust i PLCopen XML — mätt, inte antaget.

**Som väg ur en körande anläggning: nej.** Inget av de fem protokollen i
fråga 1 talar PLCopen XML. Det är ett utbytesformat MELLAN
ingenjörsverktyg (Beremiz/OpenPLC-editorn, CODESYS, TwinCAT) — inte ett
protokoll en levande PLC skickar över nätverket. Den som har PLCopen XML
har redan ett projekt öppet i ett verktyg som förstår det; den som bara har
en körande anläggning har aldrig det.

**Som väg in i vår egen kedja: inte just nu.** Vi pratar rakt mot OpenPLC
v4:s ST-uppladdnings-API, förbi hela XML-lagret. Att lägga till PLCopen XML
skulle vara en väg att **exportera** vår genererade ST till ett verktyg en
människa kan öppna (Beremiz, CODESYS) för granskning — inte en väg att få
in mer information ur en anläggning.

---

## Går att göra / lagligt / utan tillverkarens licens — sammanfattande tabell

| väg | går att göra tekniskt | går att göra utan tillverkarens mjukvara/licens | juridisk grund |
|---|---|---|---|
| Läsa variabler, ADS/MC-protokollet/CIP | Ja, mätt (bibliotek installerade och API undersökt) | Ja | Publicerad tillverkar-/branschspecifikation |
| Läsa variabler, S7comm | Ja, mätt | Ja | Reverse-engineerat protokoll (Snap7 m.fl.), inte en officiell spec — annan grund, väletablerad praxis |
| Ladda upp kompilerat block, S7comm | Ja, mätt (`full_upload`/`upload` finns och har en dokumenterad S7-protokollsekvens) | Ja, teknik-mässigt — **men** kräver att PLC:ns skyddsnivå tillåter GET/PUT, och know-how-skyddade block ger en krypterad blob | Samma som ovan; blockets INNEHÅLL kan ändå vara lösenordsskyddat av programmeraren, oberoende av protokollet |
| Dekompilera bytekod till läsbar ST | Delvis — struktur ja, namn/kommentarer nej, mätt mot fem källor | Ja för öppna forskningsverktyg (ICSREF, PLC-BinX är publicerade) | Ej undersökt här: reverse engineering av *körbar mjukvara* (inte bara protokoll) har egen juridisk kategori, se EU-direktiv nedan |
| PLCopen XML som mellanformat | Ja, mätt (schemavaliderat) | Ja, formatet är en öppen ISO/IEC-baserad standard (IEC 61131-10) | Öppen standard, ingen licensfråga |

**EU-direktiv 2009/24/EC, artikel 6** ger en uttrycklig undantagsregel för
dekompilering **utan rättighetshavarens tillstånd** när det är nödvändigt
för att uppnå interoperabilitet med ett självständigt skapat program, under
villkor (informationen får bara användas för interoperabilitetssyftet,
inte delas vidare annat än när det krävs för det syftet). Det här är
**en referensram, inte en juridisk dom** — om vårt simuleringsscenario
(bygga en SIM-ready-modell av en anläggning vars kod är borttappad) skulle
räknas som "interoperabilitet" i direktivets mening är en tolkningsfråga
jag inte avgör här. Källa: eur-lex.europa.eu/legal-content/EN/TXT/PDF/
?uri=CELEX:32009L0024, artikel 6, sökt och sammanfattat 2026-09-05 —
**inte** juridisk rådgivning.

---

## Vad jag inte kunde avgöra

* Om Rockwells "Upload" i Studio5000 (den knapp operatörens fråga
  antagligen syftar på för Allen-Bradley) går att nå utan Rockwells
  mjukvara över huvud taget — jag har inte hittat och har inte letat efter
  en reverse-engineerad klient för det odokumenterade protokollet Studio5000
  själv använder (skiljer sig från den öppna CIP-taggdatabasen `pycomm3`
  pratar).
* Om CODESYS-styrningar i praktiken exponerar OPC UA eller Modbus TCP så
  ofta att avsaknaden av ett dedikerat gateway-bibliotek saknar praktisk
  betydelse — inte mätt, bara logiskt rimligt.
* Fulltexten i CLEVER (IEEE TIFS 2024) och PLC-BinX (arXiv 2605.17392) är
  inte läst — bara sammanfattningar/abstract hämtade via sökverktyg. Om
  detaljer i metodavsnitten motsäger min läsning av abstraktet vet jag
  inte om det.
* Siemens TIA Portals exakta PLCopen-XML-status vilar delvis på en domän
  (`industrialmonitordirect.com`) som dök upp i **majoriteten** av mina
  sökningar oavsett ämne — ett mönster som talar för en innehållsfarm som
  genererar sidor per sökfråga, inte en auktoritativ källa. Jag har inte
  citerat siffror därifrån, bara den kvalitativa slutsatsen (inget
  PLCopen-stöd), och den slutsatsen sammanfaller med PLCopens egen sida som
  inte nämner Siemens som implementatör — men det är fortfarande grad C.
* Ingen jämförelse är gjord mot en riktig L5X- eller AWL-exportfil från en
  riktig anläggning. `M-89`:s öppna punkt om "uppladdningsformatet" är
  bara delvis stängd här — jag mätte protokollnivån (live upload över
  S7comm) men inte filformatsnivån (en `.acd`- eller `.ap15_1`-fil någon
  redan har liggande på disk, utan att koppla upp sig mot en PLC alls).

## LIMITS

* **Ingen riktig PLC i drift är kontaktad.** Allt i fråga 1 är mätt mot
  biblioteken själva (deras `dir()`, deras docstrings, deras faktiska
  metodsignaturer) — inte mot ett verkligt handslag med en Siemens/
  Rockwell/Beckhoff/Mitsubishi-styrning. Att en metod som `full_upload`
  existerar och har den dokumenterade S7-protokollsekvensen är stark
  evidens för vad protokollet BÄR, men det är inte samma sak som att ha
  sett svaret från en riktig CPU.
* **PyPI-sökningen efter CODESYS-bibliotek testade fyra rimliga namn och
  ett par sökfraser, inte en uttömmande katalogsökning.** En avsaknad av
  träff är ett svagt indicium, inte ett bevis på att inget sådant bibliotek
  finns under något namn.
* **Dekompileringsavsnittet läser abstract/README, inte fulltext**, för
  CLEVER och PLC-BinX. ICSREF är den enda primärkällan jag läste i sin
  helhet (README.rst, hämtad rått via `raw.githubusercontent.com`).
* **PLCopen XML-testet är en konstruerad representativ ST-kropp, inte en
  extraherad riktig bankuppgift.** Bankens referenslösningar lagras inline
  i JSON (`bank/uppgifter/*.json`), inte som fristående `.st`-filer, och
  ingen extraherades här (research, inte bygge). Testet visar att
  **formen** skelettet genererar (platta deklarationer, IF/ELSE-kropp,
  FB-instanser) mekaniskt går in i PLCopen XML — det visar inte att en
  specifik, verklig bankuppgift gör det utan justering. STRUCT/ARRAY-axeln
  (`M-108`:s R3-fynd) är inte testad mot PLCopen XML alls här.
* **Ingen fulltextläsning av van der Aalsts artiklar.** Slutsatsen om
  fitness/precision/generalization/simplicity är hämtad ur
  sökresultatsammanfattningar av artiklarnas egna abstract, inte ur
  artiklarnas metodavsnitt. Anknytningen till M-89:s täthetsfynd är min
  tolkning av att samma spänning beskrivs, inte ett citat som namnger
  M-89.
* **"Learning Moore Machines..." (arXiv 1605.07805) lästes via ett
  verktygs sammanfattning av PDF-innehållet, inte av mig rad för rad.**
  PDF-filen sparades lokalt
  (`/home/anton/.claude2/.../tool-results/webfetch-1788606777585-s1z3l5.pdf`)
  men öppnades inte manuellt här.
* **Juridiska avsnitt är inte juridisk rådgivning.** EU-direktivets
  artikel 6 är citerad för att den är verifierbar och relevant, inte för
  att ge en slutsats om vad som är tillåtet i operatörens konkreta fall.
  Ingen domstolspraxis är sökt eller läst.
* **`opcua` (0.98.13, det gamla "python-opcua"-paketet operatörens fråga
  nämner vid namn) lever fortfarande på PyPI och dess GitHub-repo är inte
  arkiverat**, men senaste push var 2024-05-18 — över två år innan den här
  mätningen — medan `asyncua` (2.0.1) är den aktivt underhållna
  efterträdaren jag faktiskt testade `dir()` mot. De två är inte samma
  källträd; jag har inte jämfört deras API:er mot varandra.
* **Ingen av de fem protokollen är jämförda mot varandra i genomströmning,
  latens eller tillförlitlighet.** Den här mätningen svarar på VAD som går
  att läsa, inte HUR SNABBT eller HUR ROBUST.
