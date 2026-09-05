# M-154 — Exporten ut: PLCopen XML, och vad som overlever sin egen import

**Datum:** 2026-09-05 · kö A, punkt A5
**Rigg:** ren Linux, ingen VC, ingen OpenPLC-runtime. Python 3.13, `lxml` 6.0.2.
Externa domare: det officiella `tc6_xml_v201.xsd` (hämtat ur Beremiz, sha256 i
`svc/vc_assist_svc/plc/plcopen_schema/HARKOMST.md`), **Beremiz egen laddare**
(`plcopen.plcopen.LoadProjectXML`, hämtad från `beremiz/beremiz@master`, körd
på den här maskinen utan wxPython) och **matiec** (`/tmp/opencode/matiec/iec2c`,
OpenPLC:s egen kompilator, samma binär som `M-121`).
**Prövar:** `svc/vc_assist_svc/plc/plcopen.py` (ny),
`tests/enhet/test_plc_plcopen.py` (139 prov),
`docs/matningar/radata/m154_svep.py` → `m154_ut.txt`.
**Bygger på, upprepar inte:** `M-113` (PLCopen XML som **möjlig** väg ut, mätt
med ST-texten som en klump), `M-114` (vägen in ger inte tillbaka källkoden),
`M-121` (matiec-vägen), `M-62` (baslinjegeneratorn som gav de 63 programmen).

---

## Resultat

En export finns, den är fail-closed, och den är prövad mot tre domare som
ingen av dem är vår egen jämförelse.

| Vad | Tal | Domare |
|---|---|---|
| fall totalt | **77** (63 bankprogram + 14 konstruktioner) | — |
| ST-lagrets **egen** tur och retur höll | 77 av 77 | `las(skriv_enhet(e)) == e` |
| PLCopen tur och retur höll | **77 av 77** | modelljämförelse |
| giltiga mot officiella `tc6_xml_v201.xsd` | **77 av 77** | `lxml.etree.XMLSchema` |
| godtagna av **Beremiz egen laddare** | **77 av 77** | tredje parts kod |
| **matiec:** samma dom före och efter turen | **77 av 77** | OpenPLC:s kompilator |
| matiec accepterade originalet | 51 av 77 | (nämnaren för raden ovan) |

Den sista raden är den som gör den näst sista värd något. Hade matiec sagt ja
till allt vore "samma dom" en tautologi. Den säger nej till 26 av 77 — och till
exakt samma 26 efter turen och retur.

### Vad "tur och retur" betyder här, och varför M-113:s tal inte räcker

`M-113` la hela ST-källan som **en textklump** i `<ST>` och fick den tillbaka
byte-identisk. Det beviset är svagare än det ser ut: en textklump som kommer
tillbaka oförändrad visar att XML-lagret inte tappade tecken, ingenting annat.
Deklarationerna, adresserna, kvalificerarna och säkerhetsmärkningen fanns
aldrig i dokumentet, och därför fanns det heller ingenting där som kunde tappas.

Här bor deklarationerna i `<interface>` som riktiga `<variable>`-element med
`address`, `constant`/`retain` och typträd, och `<ST>` bär bara satserna. Det
provas mekaniskt (`test_kroppen_ligger_i_st_elementet_inte_deklarationerna`:
`END_VAR` får inte förekomma i `<ST>`-texten). Kravet är
**`Enhet` → XML → `Enhet`, och de två ska vara lika**, inte att en sträng
kommer tillbaka.

---

## §1 — De utpekade kandidaterna: timers, flanker och CASE

Uppdraget pekade ut tre troliga förlustkandidater. **Ingen av de tre förlorade
något.** Talen, ur `m154_ut.txt` och ur bankens 63 program:

| Konstruktion | Förekomster i bankens 63 program | Överlever |
|---|---|---|
| `CASE` (inkl. områden `1..4, 7` och nästlade) | 42 program | ja |
| `R_TRIG` | 20 program | ja |
| `TON` | 9 program | ja |
| `F_TRIG` | 2 program | ja |
| `TP`, `TOF` | **0 program** | ja, men bara i handbyggd fixtur (`timer_tp_tof`) |

**Rättelse i mätningen, gjord innan den publicerades.** Första räkningen sökte
efter delsträngar i ST-texten och gav `TP: 11 program`. Den var fel: `TP`
matchade taggnamn (`..._STP_...`), inte en timerinstans. Talen ovan är räknade
på det **lästa trädet** — `Fall`-noder för `CASE`, `Blocktyp`-deklarationer för
blocken — och `TP` och `TOF` finns inte i banken alls. Att skillnaden är fyra
rader kod och elva program är precis varför en delsträngsräkning inte duger
som nämnare.

Skälet till att timerinstansen klarar sig är värt att skriva ut, för det var
den plats felet var mest troligt: **PLCopen skiljer inte på en blockinstans och
en strukturvariabel.** Både `vakt : TON;` och `p : Punkt;` blir
`<derived name="..."/>`. Vår modell skiljer dem (`Blocktyp` mot `Strukturtyp`),
och skillnaden avgör vad `vakt.Q` betyder.

Importen gissar inte. Den skriver ut ST-text ur XML:en och låter projektets
**egen läsare** avgöra — och läsaren avgör med samma regel som för en
handskriven fil: namnet är en blockinstans om det står i standardbiblioteket
eller om det finns ett `FUNCTION_BLOCK` med det namnet i samma fil. Båda
uppgifterna finns i dokumentet. Det provas åt båda hållen
(`egen_struct` och `eget_funktionsblock` i fixturlistan), och muteringsprovet
`test_grinden_ser_att_en_typ_byts` byter `TON` mot `TOF` i den färdiga filen
och kräver att grinden ser skillnaden.

Att mellansteget är ST-text är inte en genväg utan samma väg ett riktigt
verktyg tar: Beremiz genererar ST ur sitt `plc.xml` innan matiec får se det.

---

## §2 — Det som INTE överlever

### 2a. Kvalificerarordningen (den enda riktiga ST-konstruktionen)

`VAR NON_RETAIN CONSTANT` blir två attribut på samma element:

```xml
<localVars constant="true" nonretain="true">
```

XML-attribut har ingen ordning. Importen kan därför bara återskapa dem i **en**
ordning, och den är `VAR CONSTANT NON_RETAIN`. Exporten **fäller**:

```
ExportFel: exporten överlevde inte sin egen import:
  P: blockhuvudet 'VAR NON_RETAIN CONSTANT' mot 'VAR CONSTANT NON_RETAIN'
```

Trasig fixtur: `test_kvalificerarordningen_falls`. Samma block i den ordning
importen kan återskapa går igenom, så provet mäter ordningen och inte
kvalificerarna.

**Att fälla är rätt svar och inte överdrivet.** Vi vet inte om mottagaren bryr
sig om ordningen, och en fil som kommer tillbaka omkastad är inte bevisligen
samma program. Att tysta det hade varit att flytta osäkerheten till någon
annans importör.

### 2b. Tre modellkonstruktioner som inte går att skriva som ST

Modellen kan bära mer än ST-texten kan uttrycka. Alla tre fälls:

| Konstruktion | Varför den inte överlever | Prov |
|---|---|---|
| en kommentar som bär `*)` | ST-kommentaren tar slut mitt i | `test_kommentar_med_kommentarslut_falls` |
| en kommentar med blanksteg i kanten | lexern strippar kanterna (`text[2:-2].strip()`) | `test_kommentar_som_inte_ar_stripad_falls` |
| icke-ASCII någonstans | genererad ST ska vara ren ASCII hela vägen ut | `test_icke_ascii_falls` |

De två första fälls av **turen och retur själv** — grinden fyrar, ingen
särskild regel behövs. Den tredje fälls av en uttrycklig ASCII-kontroll, för
den skulle ha överlevt turen och retur och ändå varit fel: teckenkodningen
efter oss äger vi inte.

### 2c. En väntad förlust som inte fanns

`test_flerradig_kommentar_falls` skrevs som en trasig fixtur — jag antog att en
kommentar med radbrytning skulle komma tillbaka stympad. **Den gör den inte.**
Lexern tar hela `(* ... *)` som en token. Provet står kvar under namnet
`test_flerradig_kommentar_overlever_anda` med omvänt påstående. En gissning som
mätningen kullkastade är ett resultat, inte ett misstag att sopa undan.

---

## §3 — Är grinden överhuvudtaget känslig?

Att alla 77 fall gick igenom på **första** försöket är ett misstänkt resultat.
En tur och retur som alltid säger LIKA mäter ingenting.

Därför muteras den **färdiga filen** — samma grepp som `M-148` (mutera domaren
i stället för koden) — och grinden måste se skillnaden. Sex mutationer, sex
träffar:

| Mutation av filen | Grinden ser | Prov |
|---|---|---|
| `address="%IX0.0"` tas bort | `ST100_ESTOP.adress: '%IX0.0' mot None` | `test_grinden_ser_att_adressen_forsvinner` |
| `<addData>` (säkerhetsmärkningen) tas bort | `...skyddad: True mot False` | `test_grinden_ser_att_sakerhetsmarkningen_forsvinner` |
| `<documentation>` tas bort | `...kommentar: '...' mot None` | `test_grinden_ser_att_kommentaren_forsvinner` |
| `retain="true"` tas bort | `blockhuvudet 'VAR RETAIN' mot 'VAR'` | `test_grinden_ser_att_kvalificeraren_forsvinner` |
| ST-texten töms | `kroppen kom inte tillbaka likadan` | `test_grinden_ser_att_kroppen_tommas` |
| `<derived name="TON">` → `TOF` | `vakt.typ: Blocktyp('TON') mot Blocktyp('TOF')` | `test_grinden_ser_att_en_typ_byts` |

Fyra av importens felvägar har egna fixturer också: trasig XML, fel namnrymd,
okänd `pouType`, och en kropp skriven i `IL` i stället för `ST`. Ingen av dem
får svara med en tom `Enhet`.

---

## §4 — Säkerhetsmärkningen har ingen plats i standarden

`Deklaration.skyddad` är bäraren av invariant I15 (*agenten får läsa, aldrig
skriva*). PLCopen har **ingen** motsvarighet. Den skrivs därför i `addData`
under vår egen namnrymd:

```xml
<addData><data name="http://vc-assist.invalid/plcopen/sakerhet"
                handleUnknown="preserve">
  <sakerhet xmlns="http://vc-assist.invalid/plcopen/sakerhet" skyddad="true"/>
</data></addData>
```

`handleUnknown="preserve"` är enligt schemats egen text *"Recommended processor
handling"* — en **rekommendation**, inte en garanti. Vår tur och retur bevarar
märkningen och grinden fäller om den försvinner (§3). Att ett främmande verktyg
gör det är **oprövat och kan inte lovas**. Det står i LIMITS, och det är den
enskilt viktigaste begränsningen i hela mätningen: en säkerhetsmärkning som
tyst faller bort på vägen ut är precis den sortens tysta nedgradering
`50_grindar.md` finns för.

---

## §5 — Ett främmande verktyg åt andra hållet

Vår **importör** provades också på riktiga PLCopen-filer som inte kommer från
oss — Beremiz egna testprojekt:

| Fil | Utfall |
|---|---|
| `tests/projects/plc_sdk_minimal/plc.xml` (1 590 byte) | **läses**: 1 POU, 1 sats |
| `tests/projects/iec61131_lang_test/plc.xml` (152 831 byte) | **avvisas med skäl**: `<dataType name='array_type_0'> har en baseType som inte är en <struct>` |

Den andra filen är gränsen ritad i tal. Den har **14 POU:er**, och deras
kroppar är `ST` 5, `FBD` 4, `LD` 3, `SFC` 1, `IL` 1 — alltså **9 av 14 i
grafiska språk vårt ST-lager inte har någon modell för alls**. Dess
`<dataTypes>` har fyra poster: två `struct`, en `array` och en `DINT`-alias.
Vårt ST-lager har bara `STRUCT` i `TYPE ... END_TYPE`.

Importören svarar med ett namngivet fel och inte med en halvläst `Enhet`. Det
är rätt utfall: en importör som tyst hoppar över det den inte förstår ger
användaren en fil som ser komplett ut och saknar hälften.

---

## §6 — Ett tillverkarkrav vi råkade uppfylla

CODESYS egen dokumentation för `Import PLCopenXML` skriver:

> *"The PLCopenXML model does not allow VAR_GLOBAL and VAR_GLOBAL CONSTANT to
> have blocks in the same variable list. If both should be exported, then the
> variables have to be previously divided into two separate variable lists."*
> — `content.helpme-codesys.com/.../_cds_cmd_import_plcopenxml.html`, hämtad
> 2026-09-05 (se `M-155`)

Vår exportör skriver **ett `<globalVars>`-element per `Varblock`**, så kravet
är uppfyllt av konstruktion. Kontrollerat på fixturen
`globala_och_ovriga_varsorter`, som har just det paret:

```
antal <globalVars ...>: 2
   <globalVars>
   <globalVars constant="true">
```

Det är inte ett bevis att CODESYS öppnar filen — se `M-155` för vad som är
belagt och vad som är oprövat. Det är ett belagt krav som filen möter.

---

## LIMITS — vad den här mätningen INTE visar

* **Ingen kommersiell PLC-IDE har öppnat filen.** Varken CODESYS, TIA Portal
  eller TwinCAT kördes; ingen licens och ingen Windowsmaskin fanns i den här
  körningen. Vad som är belagt om dem står i `M-155`, och det är
  tillverkardokumentation, inte en öppnad fil.
* **Beremiz laddare är inte Beremiz.** `LoadProjectXML` parsar och validerar;
  den bygger inte projektet och genererar ingen kod. Att filen laddas är inte
  detsamma som att Beremiz kan kompilera den. `Beremiz_cli.py --build` kördes
  **inte** (kräver hela targets-trädet).
* **Säkerhetsmärkningens överlevnad hos tredje part är oprövad.** Se §4.
  `handleUnknown="preserve"` är en rekommendation i schemat.
* **Det är TC6 v2.01, inte IEC 61131-10:2019.** PLCopen skriver själva att den
  nya versionen *"is not compatible to previous versions of PLCopen XML"*
  (`M-155` §0). Ingenting här säger något om 61131-10.
* **Bara ST.** `IL`, `LD`, `FBD` och `SFC` skrivs inte och läses inte. Ett
  verktyg som exporterar en stege till oss får ett namngivet fel, inte en
  översättning.
* **Ingen `<configuration>`/`<resource>`/`<task>`-modell.** Vi skriver en
  `<configuration>` bara när det finns `VAR_GLOBAL`, och aldrig någon
  `<resource>`, `<task>` eller `<pouInstance>`. Ett verktyg som väntar sig en
  körbar konfiguration får ett projekt utan en sådan. Vår `Enhet` har inget
  sådant begrepp, så det finns ingenting att förlora — men det finns heller
  ingenting att ärva för mottagaren.
* **`OBJECT`/`METHOD`/`INTERFACE` (61131-3 3:e utg.) rörs inte.** Vår
  `Pou`-modell har PROGRAM, FUNCTION_BLOCK och FUNCTION, inget mer.
* **Tidsstämpeln i `fileHeader` är påhittad** (`1970-01-01T00:00:00`) för att
  utdata ska vara deterministisk. Den som vill ha en äkta tid skickar in den.
* **`STRING`-längder skrivs som `length`-attribut på `<string>` men ingen
  mottagare har prövats på det.**
* **51 av 77 tal säger ingenting om kvalitet.** matiec accepterade 51 av 77 av
  BASLINJEGENERATORNS program; att 26 föll är en egenskap hos generatorn
  (`M-62`), inte hos exporten. Talet står här bara som nämnare till "samma dom
  före och efter".
* **Ingen mätning av storlek eller tid.** Filstorlekar, exporttider och hur de
  växer med programstorlek är inte mätta.
