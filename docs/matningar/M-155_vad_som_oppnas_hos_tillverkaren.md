# M-155 — Vad som faktiskt oppnas hos en tillverkare: CODESYS, TIA Portal, TwinCAT

**Datum:** 2026-09-05 · kö A, punkt A6
**Typ:** DOK + en (1) körd import. Ingen kommersiell PLC-IDE kördes.
**Rigg:** ren Linux utan Windows och utan någon tillverkarlicens. Primärkällor
hämtade med `curl`/WebFetch 2026-09-05 och sparade som text; rådata i
sessionens scratchpad (`a6_research/`, överlever inte omstart — citaten nedan
är destillatet, med URL och filnamn per rad).
**Bygger på, upprepar inte:** `M-113` (HOOPS/FBX-exportörerna i VC, belagda i
DLL/ikon/.NET men EJ körda; PLCopen XML som möjlig väg ut), `M-114` (vägen in),
`M-154` (vår egen exportör och dess tur och retur).
**Formen är `M-120`:s:** fulltext eller inget. Varje rad bär sin belägg-styrka.

---

## Beläggsklasserna, och vad de betyder

| Klass | Betyder |
|---|---|
| **KÖRD** | en fil producerades här och öppnades av mottagarens egen kod på den här maskinen |
| **TILLVERKARDOK** | ordagrant citat ur tillverkarens **egen** dokumentation, med URL |
| **TILLVERKARDOK-NEG** | maskinkontrollerad **frånvaro** i tillverkarens egen dokumentation |
| **OPRÖVAT** | ingen av ovanstående. Raden säger vad som exakt saknas för att pröva den |
| **SPÅR** | ett påstående som finns men vars källa inte är tillverkaren. Aldrig ett bevis |

Forum, bloggar, Wikipedia och modellminne har inte använts som belägg någonstans
i den här mätningen.

---

## §0 — Fyndet som styr allt annat: två oförenliga "PLCopen XML"

PLCopen skriver **själva** att den standardiserade efterföljaren inte är
bakåtkompatibel:

> *"With the release of the 3rd edition of IEC 61131-3 in 2013, a major overhaul
> was needed to include the changes and extensions like object oriented
> features. This work was done within the IEC committee based on the work of
> PLCopen TC6 – XML and resulted in IEC 61131-10 PLC open XML exchange format.
> **This new version is not compatible to previous versions of PLCopen XML.**"*

Och versionslinjen:

> *"The PLCopen technical document XML formats for IEC 61131-3 was first
> released in 2005. Version 2.0 followed in 2008 … An update with some minor
> changes, version 2.01, was published in 2009."*

**Belägg:** TILLVERKARDOK (utgivaren av formatet självt).
`plcopen.org/download_file/view/02701805-7b7e-499a-bcf8-38f3e9ae8e32/`, PDF
hämtad 2026-09-05, textextraherad med `pdftotext -layout`
(`plcopen_iec61131-10_announcement.pdf` / `.txt`, 2 sidor).

**Vad det gör med `M-113`.** `M-113` skrev: *"Sannolikt rätt för textuell ST,
overifierat"* om att TC6 v2.01 skulle vara nära IEC 61131-10:2019. Det
antagandet är **inte längre neutralt** — utgivaren säger uttryckligen att de är
inkompatibla. Vilken av de två en given IDE läser är därför en egen fråga per
verktyg, och ingen av de tre tillverkarna nedan nämner "IEC 61131-10" med ett
ord.

Vår export skriver **TC6 v2.01** (`M-154`). Det är versionen alla tre
undersökta verktyg dokumenterar, och den enda vars schema är fritt tillgängligt.

---

## §1 — CODESYS (V3 / 3.5)

| Påstående | Klass | Belägg |
|---|---|---|
| Import av PLCopen XML finns, som ett menykommando | **TILLVERKARDOK** | *"The command opens a dialog for importing objects from an XML file in PLCopen format."* — `content.helpme-codesys.com/en/CODESYS Development System/_cds_cmd_import_plcopenxml.html` |
| Export av PLCopen XML finns | **TILLVERKARDOK** | *"The command opens a dialog for exporting objects from a project to an XML file PLCopen format."* — `_cds_cmd_export_plcopenxml.html` |
| PLCopen XML är **inte** CODESYS eget projektformat | **TILLVERKARDOK** | *"CODESYS XML format (\*.export): This format is fully compatible with the CODESYS project format."* mot *"PLCopen XML format (\*.xml): You can use this format for exchanging information between programs…"* — `_cds_project_export_import.html` |
| Stödet är ett **delmängdsstöd** | **TILLVERKARDOK** | *"100% compatibility cannot be guaranteed"* — samma sida |
| `VAR_GLOBAL` och `VAR_GLOBAL CONSTANT` får **inte** ligga i samma variabellista | **TILLVERKARDOK** | *"The PLCopenXML model does not allow VAR_GLOBAL and VAR_GLOBAL CONSTANT to have blocks in the same variable list. If both should be exported, then the variables have to be previously divided into two separate variable lists."* — import- och exportsidan, båda |
| Vilken **version** av PLCopen XML CODESYS läser/skriver | **OPRÖVAT** | Saknas: en export ur en licensierad CODESYS 3.5 (Windows) att inspektera namnrymden i, eller en tillverkarsida som namnger versionen. Riktad sökning på `help.codesys.com` efter "IEC 61131-10" gav noll träffar |
| Att **vår** fil öppnas i CODESYS | **OPRÖVAT** | Saknas: CODESYS Development System på Windows (eller under Wine, oprövat) plus en licens. Filen finns färdig — `M-154` — och vad som saknas är en maskin att öppna den på |

**Den fjärde raden är den enda som redan är prövad mot vår export.**
Vår exportör skriver ett `<globalVars>`-element per `Varblock`, alltså två
separata listor för `VAR_GLOBAL` och `VAR_GLOBAL CONSTANT` (`M-154` §6,
kontrollerat i tal). Kravet är alltså uppfyllt av konstruktion. Det gör **inte**
att filen bevisligen öppnas — det gör att just den kända fällan är undviken.

---

## §2 — Beckhoff TwinCAT 3

| Påstående | Klass | Belägg |
|---|---|---|
| Import av PLCopen XML finns, i PLC-projektets kontextmeny | **TILLVERKARDOK** | *"The command opens a dialog for importing objects from an XML file in PLCopen format."* — `infosys.beckhoff.com/content/1033/tc3_userinterface/2531232139.html` |
| Export av PLCopen XML finns | **TILLVERKARDOK** | *"The command opens a dialog for exporting objects of a project into an XML file in PLCopen format."* — `.../tc3_userinterface/2531226763.html` |
| PLCopenXML är ett av **tre** projektutbytesformat, och det enda för utbyte med andra program | **TILLVERKARDOK** | *"PLCopenXML (\*.xml) — You can use this format to exchange information with other programs (for example program editors or documentation tools)."* — `.../tc3_plc_intro/2526208651.html` |
| Stödet är ett **delmängdsstöd** | **TILLVERKARDOK** | *"100% compatibility is therefore not ensured"* — samma sida |
| TwinCAT skriver dessutom **deklarationsdelens klartext** i filen vid export | **TILLVERKARDOK** | *"Formatting and comments are retained. TwinCAT also writes the plain text of the exported declaration part to the PLCopenXML file."* — `.../tc3_plc_intro/2533249163.html` ("Dialog Options - PLCopenXML", menyväg `TwinCAT > PLC Environment > PLCopenXML`) |
| Vilken **version** av PLCopen XML, och build-specifika skillnader (t.ex. 3.1 build 4024) | **OPRÖVAT** | Saknas: en tillverkarsida som namnger versionen; riktad sökning gav bara allmän installationsdokumentation |
| `.tpy` / `.tmc` och deras relation till PLCopenXML | **OPRÖVAT** | Saknas: infosys-sidorna om TMC/TPY-schemat, ej hämtade i den här körningen |
| Att **vår** fil öppnas i TwinCAT | **OPRÖVAT** | Saknas: Windows med Visual Studio + TwinCAT 3 XAE och licens |

Den femte raden är intressant för oss åt andra hållet: TwinCAT lägger
deklarationernas **klartext** i filen utöver `<interface>`. En fil som kommer
från TwinCAT bär alltså information vår importör inte läser — och vår importör
avvisar inte den, eftersom den bor i `addData` (schemat tillåter det). Vad
TwinCAT gör med en fil som **saknar** den klartexten är **oprövat**.

---

## §3 — Siemens TIA Portal

Här är svaret ett annat, och det är ett negativt fynd med maskinkontroll.

| Påstående | Klass | Belägg |
|---|---|---|
| TIA Portals Openness-manual nämner **inte** PLCopen med ett ord | **TILLVERKARDOK-NEG** | `grep -ci "plcopen"` = **0** i 86 298 rader ur `TIAPortalOpenness_enUS_en-US.pdf` (*"Openness: API for automation of engineering workflows — System Manual, 11/2023"*), hämtad från Siemens egen CDN `cache.industry.siemens.com/dl/files/886/109826886/att_1163875/v1/` |
| Samma manual nämner "61131" **en** gång, och inte om utbytesformatet | **TILLVERKARDOK-NEG** | 1 träff, *"…datatypes other than IEC 61131 datatypes…"*, en generisk språkreferens |
| Siemens eget XML-utbytesformat heter **Simatic ML** | **TILLVERKARDOK** | *"Exporting Simatic ML files. The Siemens.Engineering.dll assemblies V16, V17 and V18 will create Simatic ML files of TIA Portal version V19."* — samma manual |
| Textvägen in heter **external source file** och tar exakt fyra format | **TILLVERKARDOK** | *"The following formats are supported: STL / SCL / DB / UDT"* och *"An exception is thrown if you specify a file extension other than \*.AWL, \*.SCL, \*.DB or \*.UDT."* — samma manual, §5.11 "External Sources", namnrymd `Siemens.Engineering.SW.ExternalSources` |
| En external source är **ren text** | **TILLVERKARDOK** | *"…exports all blocks and with all their dependencies … as ASCII text into the provided source file."* — samma manual, §5.11.3.18 |
| Vad en `.scl`-källfil är | **TILLVERKARDOK** (klassisk STEP 7, ej TIA-märkt) | *"Its central purpose is the creation and editing of source files for STEP 7 programs. In a source file you can write one or more program blocks."* — `SCLV4_e.pdf`, ordernr `6ES7811-1CA02-8BA0`, `cache.industry.siemens.com` |
| GUI-menyvägen "Insert external source file" i TIA Portal | **SPÅR, ej belagt** | Siemens supportdokument 79168964 gick **inte** att hämta: Akamai svarade HTTP 403 mot `curl`, WebFetch fick ett JS-skal, och `web.archive.org` har noll ögonblicksbilder. Kräver en JS-kapabel eller inloggad hämtare |
| Att TIA Portal kan importera PLCopen XML överhuvudtaget | **OPRÖVAT** | Manualen (11/2023) nämner det aldrig. Det är inte samma sak som ett bevisat nej: en nyare TIA-version (V19/V20) kan ha lagt till det efter den manualen, och det är inte kontrollerat |
| Att vår ST skulle gå in som `.scl` | **OPRÖVAT** | Saknas två saker: (1) TIA Portal med licens, (2) en mätning av avståndet mellan IEC 61131-3 ST och Siemens SCL-dialekt. Ingen av dem finns här, och att gissa vore precis det påstående punkten förbjuder |

**Sammanfattat för Siemens:** vägen in i TIA Portal går enligt tillverkarens
egen manual genom **Siemens egna format** — Simatic ML via Openness, eller en
`.scl`/`.awl`/`.db`/`.udt`-källfil som ren text. PLCopen XML nämns inte. Det är
ett starkt negativt fynd (86 298 rader, noll träffar), men det gäller **den
manualen**, inte hela produkten.

---

## §4 — Det som faktiskt öppnades, på den här maskinen

Ett verktyg accepterade våra filer, och det är inte något av de tre ovan.

| Påstående | Klass | Tal |
|---|---|---|
| **Beremiz egen laddare** (`plcopen.plcopen.LoadProjectXML`) godtar våra filer | **KÖRD** | **77 av 77** (63 bankprogram + 14 konstruktioner) |
| Laddaren läser våra deklarationer, adresser och blockinstanser | **KÖRD** | `ST100_ESTOP address=%IX0.0 typ=BOOL`, `vakt typ=derived TON`, och ST-kroppen ordagrant tillbaka ur trädet |
| Laddaren **säger nej** när filen är trasig | **KÖRD** | tre mutationer, tre avslag: `pouType="hittepa"` (*"is not an element of the set"*), ett okänt element i `<pou>`, ett omdöpt `<body>` |
| Vår importör läser Beremiz **egen** projektfil | **KÖRD** | `plc_sdk_minimal/plc.xml` (1 590 byte): 1 POU, 1 sats |
| Vår importör avvisar Beremiz stora språktestfil, med skäl | **KÖRD** | `iec61131_lang_test/plc.xml`: `<dataType name='array_type_0'>` är ingen `<struct>`. Filens 14 POU:er är `ST` 5, `FBD` 4, `LD` 3, `SFC` 1, `IL` 1 |
| `OpenPLC_Editor` är en **fork av Beremiz** och bär samma XSD-filer | **KÖRD** (GitHub-API) | `thiagoralves/editor`: `"fork": true`, `parent: beremiz/beremiz`, gren `openplc-master`; dess `plcopen/plcopen.py` skiljer **1 byte** från Beremiz |
| Beremiz `plc.xml` **är** ett TC6 v2.01-dokument | **KÖRD** | `<project xmlns="http://www.plcopen.org/xml/tc6_0201" …>` i den hämtade filen; samma `targetNamespace` i `tc6_xml_v201.xsd` |

Den tredje raden är den som gör de två första värda något. En laddare som
aldrig sagt nej mäter ingenting.

**Att den fjärde och sjätte raden hänger ihop är hela poängen för produkten.**
OpenPLC Editor — verktyget i vår egen kedja (`docs/spec/60_plc.md`) — är
Beremiz med en byte skillnad i just den modul som läser PLCopen XML. Att
Beremiz laddare godtar våra 77 filer är alltså det starkaste tillgängliga
belägget för att **OpenPLC Editor** gör det också. Men det är en slutledning ur
en identisk källfil, **inte** en körning av OpenPLC Editor: den är oprövad.

**Vad "godtas av laddaren" INTE betyder:** `LoadProjectXML` parsar och
validerar. Den bygger inte projektet, genererar ingen ST och kompilerar
ingenting. `Beremiz_cli.py --build` kördes inte.

---

## §5 — Vad som skulle krävas för att flytta varje OPRÖVAT till KÖRD

Det här är listan att beställa, inte en ursäkt.

| Vad | Vad som exakt saknas | Kostnad |
|---|---|---|
| CODESYS öppnar filen | CODESYS Development System 3.5 på Windows (Wine oprövat) + licens. Ingen kod behöver skrivas — filen finns | en maskin, en licens |
| TwinCAT öppnar filen | Windows + Visual Studio + TwinCAT 3 XAE + licens | en maskin, en licens |
| TIA Portal, PLCopen alls | en nyare TIA-manual (V19/V20) att `grep`:a, eller TIA Portal med licens | en PDF eller en licens |
| TIA Portal via `.scl` | en mätning av avståndet IEC-ST ↔ Siemens SCL, plus en licens | en egen mätning |
| OpenPLC Editor öppnar filen | `OpenPLC_Editor` klonad och startad (wxPython krävs för GUI:t; forken har inget CLI-bygge som Beremiz) | en klon, ~1 GB |
| Beremiz **bygger** projektet | `Beremiz_cli.py --build` med hela targets-trädet och matiec | en trimmad installation |
| Versionen CODESYS/TwinCAT emitterar | **en enda exporterad `.xml` från något av verktygen.** Det är den billigaste mätningen i hela tabellen: en fil räcker | en fil från någon som har verktyget |

Den sista raden är värd att skicka vidare: **en (1) PLCopenXML-fil exporterad ur
en riktig CODESYS eller TwinCAT** skulle avgöra versionsfrågan för båda
verktygen och gå att köra genom vår importör direkt. Den kostar ingen licens
här — bara att någon som har verktyget trycker på "Export".

---

## LIMITS — vad den här mätningen INTE visar

* **Ingen kommersiell PLC-IDE kördes.** Noll av CODESYS, TIA Portal och
  TwinCAT startades. Allt om dem är tillverkardokumentation, inte en öppnad fil.
  Ett menykommando som är dokumenterat är ett löfte, inte ett bevis.
* **"Öppnas i Beremiz laddare" är inte "öppnas i Beremiz".** Se §4, sista
  stycket.
* **De negativa Siemens-fynden gäller de hämtade dokumenten**, inte hela
  produkten. Noll träffar i en manual från 11/2023 är inte noll träffar i
  produkten V20.
* **`M-113`:s HOOPS/FBX-spår rörs inte här.** Den här punkten handlar om
  logikvägen (PLCopen XML), inte geometrivägen. Vad VC:s egna exportörer gör är
  fortfarande belagt i DLL/ikon/.NET och fortfarande **inte kört** (`M-113`).
* **Ingen av tillverkarnas dokumentation anger vilken PLCopen-version de
  läser.** Att alla tre bara skriver "PLCopen format" är ett fynd i sig, men det
  betyder att §0:s inkompatibilitet inte går att placera per verktyg.
* **Ingen fil har gått **från** ett tillverkarverktyg **till** oss.** Vår
  importör har bara prövats på Beremiz-filer och våra egna.
* **Sökningen är en frånvaromätning.** Att en riktad sökning på
  `help.codesys.com` inte hittade "IEC 61131-10" är inte bevis att det inte
  står någonstans hos CODESYS — bara att det inte syns för den här sökinsatsen.
