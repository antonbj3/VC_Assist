# M-113 — Vägen ut ur Visual Components till öppet format

**Datum:** 2026-09-05 · VC Premium 4.10 (installationen i `~/.wine-vc-test/`,
**VC startades ALDRIG** — allt om VC nedan är läst ur filer på disk) ·
`docs/referens/vc_api/vc_python_api.json`, `docs/referens/vc_dotnet/*.xml` ·
Python 3.13-venv i scratchpad, `plcopen` 1.0.1 (PyPI), `pyautomationml` 1.1.3
(PyPI), `lxml` (schemavalidering) · officiella scheman hämtade från
`raw.githubusercontent.com/beremiz/beremiz` (TC6 PLCopen XML) och
`raw.githubusercontent.com/amlModeling/amlMetaModel` (CAEX 2.15).

**Fråga:** hur kommer en scen UT ur Visual Components till ett öppet format —
för geometri/kinematik (Isaac Sim, Gazebo, MuJoCo, ROS) OCH för flöde/logik
(AutomationML, PLCopen XML)?

**Bygger på:** M-55 (VC:s Python-API har noll träffar för USD/URDF/glTF/OBJ/
COLLADA/STL/IGES/JT/3DXML, och noll för massa/tröghet), M-59 (filformatets
massfält sitter på verktygsramar och är i praktiken tomma), M-38 (VC:s Python
når aldrig .NET). Den här mätningen river inte upp de slutsatserna — den
**kompletterar dem på ett läge M-55 uttryckligen lämnade omätt**: "Om GUI:t kan
exportera något av formaten via en insticksmodul."

---

## 1. Vad exporterar VC 4.10 faktiskt?

Fyra oberoende bevisnivåer, i stigande styrka. Ingen av dem är att köra VC —
**VC startades inte**.

### 1a. Python-API:t (MÄTT, ur M-55, bekräftat på nytt)

Sökning i `vc_python_api.json`:s 3444 symboler ger **noll** träffar för `USD`,
`URDF`, `glTF/GLB`, `OBJ`, `COLLADA/DAE`, `STL`, `IGES`, `JT`, `3DXML`. `app.save`
skriver bara VC:s eget format. Detta gäller uteslutande vad **Python** kan göra,
och M-38/M-07 visar varför: VC:s importörer/exportörer bor i `.NET`, och
`import clr` / `import System` ger `ImportError` i VC:s Python.

### 1b. Ribbon-ikonerna i installationen (BELAGT — filnamn, ej klickat)

`Icons/`-mappen i installationen namnger de kommandon ribbon-menyn faktiskt
har knappar för:

| Ikonfil | Kommando |
|---|---|
| `rExportFBX.svg` | Exportera FBX |
| `rExportGeometry.svg`, `rgExportGeneral.svg`, `rgExport.svg` | Generell geometriexport |
| `rExportPDF.svg` | Exportera PDF |
| `rExportToBitmap.svg`, `rExportToVideo.svg` | Bild/video |
| `rImportFloorPlan.svg`, `rImportGeometry.svg`, `rgImport.svg` | Import av golvplan/geometri |
| `rExportProgram.svg` / `rImportProgram.svg` | Robotprogram |

Ett ikonnamn är ett påstående om en meny, inte om en fungerande exportör — men
`rExportFBX.svg` pekar mot ett SPECIFIKT format, inte en generisk knapp.

### 1c. De installerade DLL:erna (BELAGT — filnamn + version, ej körda)

`HoopsExchangePublish/`-mappen i installationen är **HOOPS Exchange** (Tech
Soft 3D), version `24.12_16` (2024.12, SP16) enligt filsuffixen. HOOPS Exchange
är ett licensierat CAD-interop-SDK. Läsar-DLL:er (mönster `<format>step3[01].dll`)
finns för CATIA, NX, Inventor, Solid Edge, SolidWorks, Creo, Revit, JT, IGES,
STEP, SAT/ACIS, Parasolid (XT), 3MF, VRML, U3D, DWG/DXF, MicroStation DGN,
VDA-FS. **Skrivar-DLL:er** (mönstret `w<format>.dll`, utan `step3x`-suffix) finns
för nio format:

| DLL | Format |
|---|---|
| `wstp.dll` | STEP |
| `wstl.dll` | STL |
| `wjt.dll` | JT |
| `wiges.dll` | IGES |
| `wsat.dll` | SAT (ACIS) |
| `wxt.dll` | Parasolid (XT) |
| `w3mf.dll` | 3MF |
| `wu3d.dll` | U3D |
| `wwrl.dll` | VRML |

Ingen `w`-prefixad DLL för glTF, USD, OBJ eller COLLADA/DAE finns i den här
installationen. Utöver HOOPS finns `libfbxsdk.dll` (Autodesks egna FBX-SDK) och
VC:s egna wrapprar `VisualComponents.FBX.dll`, `VisualComponents.HOOPS.dll`,
`VisualComponents.Revolution.DWGReader.dll`, `VisualComponents.Revolution.dxf.dll`.

### 1d. Den dokumenterade .NET-ytan (BELAGT — API-signatur, ej körd)

`docs/referens/vc_dotnet/Create3D.Shared.xml` dokumenterar en riktig, typad
gränssnittsmetod:

```
T:VisualComponents.Create3D.IFBXExporter — "Export to FBX interface."
M:IFBXExporter.Export(string filePath, FBXExportOptions options) -> bool
    "Exports with given options and saves it to the given path."
```

och en generisk exportplugin-arkitektur i `VisualComponents.Core.Interfaces.xml`:

```
T:VisualComponents.Core.ILayoutWriter
    "Provides support for being able to export to specific file format"
    M:GetSupportedExportFileExtensionInfo() -> FileExtensionInfo
    M:WriteFile(path, bool, FileExtensionInfo, int)
T:VisualComponents.Core.ILayoutReader — motsvarande för import
T:VisualComponents.Core.FileExtensionInfo
    "Provides information on each supported file extensions and their descriptions"
```

`IU3DRecorder.Export(Uri)` och `IPdfRecordExporter.Export(...)` är också
dokumenterade (3D-PDF: U3D inbäddat i PDF, samma mönster som Adobes 3D-PDF).
Inget dedikerat `IStepExporter`/`IIgesExporter`/`IJtExporter` finns i de sex
XML-filerna — STEP/IGES/JT/SAT/Parasolid/3MF/VRML går sannolikt via den
generiska `ILayoutWriter`-pluginen, en per HOOPS-backend, snarare än ett eget
gränssnitt per format.

### Slutsats för del 1

VC 4.10 kan **sannolikt** (BELAGT på tre oberoende sätt: ikon + DLL + dokumenterat
.NET-interface, men INTE MÄTT genom en faktisk körning) exportera FBX, och via
HOOPS Exchange troligen STEP, STL, JT, IGES, SAT, Parasolid, 3MF, U3D och VRML
— **allt via GUI:t eller .NET, aldrig via Python**. USD, glTF, OBJ, COLLADA,
URDF, SDF och MJCF finns **inte** i något av de fyra lagren. Massa, täthet,
tröghet, friktion finns **ingenstans** — bekräftat igen i sökningen (samma noll
som M-55/M-59).

Det här ändrar INTE M-55:s huvudslutsats (ingen väg till USD/URDF finns färdig)
men det **löser upp dess öppna fråga**: geometrilagret är troligen billigare än
"läs `vcTriangleSet.PolygonTable` och bygg en egen mesh-exportör" — om VC redan
kan skriva STEP eller STL via GUI:t, är den vägen ett GUI-klick eller ett
.NET-automatiseringsskript, inte en egen geometriexportör. **Detta är inte
verifierat genom en faktisk export** (VC kördes inte); det är fyra samstämmiga
bevis som pekar åt samma håll, inte en mätning av en producerad fil.

---

## 2. Vad kräver mottagarna, och vad bär VC?

Källor hämtade och citerade med URL nedan (WebFetch/WebSearch, 2026-09-05).

| Mottagare | Format | Kräver `<inertial>`/massa? | Auto-beräkning från geometri? |
|---|---|---|---|
| ROS/MoveIt | URDF | XSD: **nej**, `minOccurs="0"` på `<inertial>`, `<mass>`, `<inertia>` (källa: `ros/urdfdom` XSD på GitHub) — men verkliga konsumenter (Gazebo-import) hoppar synligt över länkar utan tröghet: `gazebosim/sdformat#199`, "URDF to SDF conversion ignores links without inertia" | Nej i URDF självt |
| Gazebo | SDF | Klassiskt: optional. Modern Gazebo Sim (`gz-sim` 9): `auto="true"` på `<inertial>` beräknar massa+tröghet **ur kollisionsgeometrin** + en `<density>` per kollision (källa: `gazebosim.org/api/sim/9/auto_inertia_calculation.html`) | **Ja** — kräver `<collision>`, annars `ELEMENT_MISSING`. Standardtäthet **1000 kg/m³** (vatten) om ingen anges |
| MuJoCo | MJCF | Nej — `<inertial>` är valfritt | **Ja** — kompilatorn räknar massa/tröghet ur `<geom>` + `density`-attribut. Standardtäthet **1000** (källa: MuJoCo XML-referens, bekräftad via community/dokumentation) |
| Isaac Sim | USD Physics | `UsdPhysicsMassAPI` är **valfri** | **Ja** — `UsdPhysicsCollisionAPI` + lokal täthet. "Density is assumed to be 1000.0 kg/m3 ... when no other density is specified" (källa: `openusd.org/release/api/usd_physics_page_front.html`). Om ingen kollisionsvolym alls: massa antas 1.0 |

**Den intressanta över-determinerade siffran:** tre oberoende ekosystem (Gazebo,
MuJoCo, USD Physics) konvergerar oberoende av varandra på **exakt samma
standardtäthet, 1000 kg/m³ (vatten)**, som fallback när ingen täthet anges.
Det är inte en slump — det är branschkonventionen för "jag vet inte, gissa
vatten" — men det betyder också att en oreflekterad auto-beräkning ger fel
massa för allt som inte är vattenfyllt: en robotbas i stål/aluminium med
håligheter skulle få en massa som är fel med en faktor på flera gånger.

### Vad detta betyder för VC:s gap

M-55/M-59 mätte att VC saknar massa, täthet OCH tröghetstensor helt. Den här
mätningen visar att **alla tre fysikmotorer redan har en väg runt just den
bristen** — förutsatt kollisionsgeometri (som VC HAR, `vcFeature.PhysicsCollider`
per M-55) plus **en enda skalär täthet per material**. Det krymper luckan från
"en fullständig massa- och 3×3-tröghetsdatabas per komponent" till "en
uppslagstabell med ungefär tio materialtätheter" (stål ≈ 7850, aluminium ≈ 2700,
ABS ≈ 1050 kg/m³, …) — en mätbart mindre uppgift.

**Det här är en hypotes, inte en mätning.** Att jämföra en täthetshärledd massa
mot en robots verkliga, publicerade massa (t.ex. ABB IRB2600 ≈ 284 kg) hade
krävt att extrahera en verklig volym ur VC:s geometri — vilket i sin tur hade
krävt att köra VC eller exportera en STEP-fil och volymberäkna den. Det ligger
utanför den här mätningens tillåtna yta (VC fick inte startas) och är **inte
gjort**. Storleken på felet en vattendensitet skulle ge på en ihålig
metallkomponent är därför okänd, bara garanterat **för hög**.

Sammanfattning per lager:

| Lager | VC bär | Mottagaren kräver | Gap |
|---|---|---|---|
| Geometri (mesh) | Ja — `vcTriangleSet`, och troligen STEP/STL/JT via GUI (del 1) | Ja, alla fyra | Litet — format finns redan eller är en HOOPS-konvertering bort |
| Kollisionsform | Ja — `VC_PHYSICSCOLLIDER_*` (M-55) | Ja, alla fyra | Litet |
| Kinematik/ledträd | Ja — `vcNode.Dof`, `.JointType`, `vcJoint.MinValue/MaxValue/...` (M-55) | Ja, alla fyra | Litet — kräver en egen skrivare, ingen ny datakälla |
| Massa/täthet/tröghet | **Nej — noll, bekräftat två gånger (M-55, M-59)** | Krävs av URDF-konsumenter i praktiken; auto-härledbar i SDF/MJCF/USD ur (kollisionsvolym × täthet) | Störst — men krymper till "en materialtäthet", inte "en full tröghetstensor", OM auto-beräkning godtas |
| Friktion, ledfriktion | Nej (M-55: noll träffar) | Krävs för realistisk kontaktdynamik | Öppet, inte undersökt här |

**Källor för del 2** (hämtade 2026-09-05):
- ros/urdfdom XSD: `raw.githubusercontent.com/ros/urdfdom/master/xsd/urdf.xsd`
- Gazebo auto-tröghet: `gazebosim.org/api/sim/9/auto_inertia_calculation.html`
- sdformat-issue om URDF utan tröghet: `github.com/gazebosim/sdformat/issues/199`
- MuJoCo XML-referens: `mujoco.readthedocs.io/en/stable/XMLreference.html` (+ community-bekräftelse av standardtäthet 1000)
- USD Physics: `openusd.org/release/api/usd_physics_page_front.html`

---

## 3. AutomationML och PLCopen XML — MÄTT, inte bara refererat

Två riktiga, publicerade Python-paket installerades och kördes mot bankens
egen data (task `S-06` för styrning, task `A-01` för scen).

### 3a. PLCopen XML — MÄTT, positivt resultat

**Paket:** `plcopen` 1.0.1 (PyPI, `pip show`: kräver `xsdata`), en dataclass-
modell av PLCopen TC6-schemat (namnrymd `http://www.plcopen.org/xml/tc6_0201`
— det schema PLCopen XML fick när det 2019 blev **IEC 61131-10**, bekräftat via
`plcopen.org/standards/logic/iec-61131-10/`).

**Görande:** genererade riktig ST för uppgift S-06 med bankens egen baslinje-
generator (`svc/vc_assist_svc/plc/baslinje/`, `Baslinje().generera(spec).kropp`,
1458 tecken), byggde ett `plcopen.project.Project` med en POU (`pouType=program`)
vars `input_vars`/`output_vars` kommer **rakt ur** `S-06.json`:s
`control.signals` (17 signaler), och la ST-texten i `body[0].st`.

**Första försöket** lade ST-texten som rå text direkt i `<ST>`-elementet.
Validering mot det **officiella** schemat (`TC6_XML_V10.xsd`/`tc6_xml_v201.xsd`,
hämtat från `raw.githubusercontent.com/beremiz/beremiz` — Beremiz är en riktig,
använd IEC 61131-3-IDE med öppen källkod som läser/skriver just det här
formatet) **föll**: `formattedText` kräver ett xhtml-barn (`<xhtml:p>`), inte
ren text. Det är precis den typen av fel en verklig mätning ska hitta —
adversären (schemat) tvingade fram rättelsen.

**Efter rättelsen** (ST-text i `AnyElement(qname="{http://www.w3.org/1999/xhtml}p", ...)`,
och borttagna tomma `<documentation/>`-element):

```
SCHEMA VALID (officiella tc6_xml_v201.xsd): True
ROUNDTRIP ST TEXT BYTE-IDENTICAL: True
signaler: 17 av 17, NAMN MATCH: True, TYP MATCH: True
```

Filen (`5371` byte) parsades tillbaka med `xsdata.XmlParser`, och ST-texten kom
tillbaka **byte-för-byte identisk** med det baslinjen genererade, alla 17
signalnamn och alla tre typer (`bool`/`int`/`real`) återgavs korrekt.

**Vad detta betyder:** `control.signals` + den genererade ST:n kan **redan i
dag**, med ett publicerat bibliotek (ingen egen parser), gå till ett riktigt,
schemavaliderat PLCopen XML-dokument — det format CODESYS, Beremiz och andra
verkliga PLC-IDE:er läser. Det är den **billigaste** av alla vägar som
undersökts i den här mätningen: en (1) korrigeringsrunda, noll ny infrastruktur.

**Vad som INTE är verifierat:** att den exakta TC6 v2.01-namnrymden är
byte-för-byte densamma som den betalversion av IEC 61131-10 (2019) som gäller
i dag — IEC:s standarddokument är bakom betalvägg och hämtades inte. För
**textuell ST**, som är allt banken genererar, är skillnaden sannolikt liten
(det är de grafiska språken — LD/FBD/SFC — som fått nya kodningsvarianter
enligt sökresultaten i del 4); det är inte kontrollerat.

### 3b. AutomationML/CAEX — MÄTT, positivt men mer arbete

**`pyautomationml` (PyAML) 1.1.3** installerades och undersöktes. Källkoden
(`pyautomationml.py`, `lxml.objectify`-baserad) visar att paketet är byggt av
CIIRC-ISI (Tjeckien) för ETT specifikt syfte: läsa AML-filer med **inbäddad
Python-kod** (`PythonPreamble`, `.fun`-eval) — peer-reviewat i en IEEE-artikel
(*PyAML: ... Python Code Injections*, IEEE Xplore 2021). Det är **inte** ett
generellt CAEX-skrivbibliotek, och det passar inte uppgiften att skriva
`scene.components` till AML. Detta är belagt genom att läsa källkoden, inte en
gissning ur READMEn.

I stället byggdes ett minimalt CAEX-dokument **direkt med `lxml`**, mot
schemat `CAEX_ClassModel_V2.15.xsd` (den fritt tillgängliga texten av CAEX 2.15,
2007-05-16, hämtad från `amlModeling/amlMetaModel` på GitHub — ett akademiskt
CAEX-modelleringsprojekt, inte AutomationML e.V:s egen sajt, som kräver
registrering). Uppgift A-01:s `scene.components` (7 poster: robot, gripdon,
fixtur, två matarbanor, två lägesgivare) och `scene.connections` (5 kopplingar)
mappades till:

```
CAEXFile > InstanceHierarchy > InternalElement "cell"
    > InternalElement (Name=role, RefBaseSystemUnitPath=uri)
        > Attribute Name="Count" > Value
        > ExternalInterface Name="ConnectionPoint" ID="if_<role>"
    > InternalLink (RefPartnerSideA/B = ExternalInterface-ID:er, en per connection)
```

```
SCHEMA VALID (officiella CAEX_ClassModel_V2.15.xsd): True
```

Alla 7 komponenter och alla 5 kopplingar validerade på **andra** försöket (det
första lade `InternalLink` fel — direkt under `InstanceHierarchy` i stället för
inne i ett `InternalElement`/`SystemUnitClassType`, vilket schemat inte
tillåter; XSD:t tvingade fram rätt struktur).

**Vad som INTE är verifierat:**
* Detta är CAEX **2.15** (2007). Nuvarande AutomationML-standard, IEC
  62714-1:2018 (2:a upplagan), bygger på **CAEX 3.0** (IEC 62424:2016) —
  bekräftat via sökning, inte hämtat och validerat här. Ett CAEX 3.0-schema
  finns fritt på `github.com/kit-sdq/AutomationML-CAEX-Metamodel` men hanns
  inte hämtas och provas i den här mätningen.
* `RefBaseClassPath="AutomationMLInterfaceClassLib/AutomationMLBaseInterface"`
  på `ExternalInterface` är en **platshållare** jag satte, inte en verifierad
  sökväg mot en riktig AutomationML-gränssnittsklassbibliotek-fil. XSD:t
  kontrollerar inte referensintegritet (det är bara `xs:string`), så filen är
  schema-giltig men **semantiskt ofullständig** — en verklig AML-konsument
  (t.ex. AMLEngine) skulle sannolikt vilja se `InterfaceClassLib`-definitionen
  som den sökvägen pekar på, och det saknas i den fil jag byggde.
* Om en riktig AutomationML-editor (t.ex. det arkiverade AMLEngine, eller en
  kommersiell editor) accepterar filen fullt ut, inte bara XSD-validatorn, är
  **omätt**.

### Vad AutomationML/PLCopen duger till för banken

Bägge formaten beskriver precis de fält banken redan har som **strukturerad
data**, inte prosa: `scene.components`/`scene.connections` → CAEX-topologi,
`control.signals` + genererad ST → PLCopen XML-logik. Ingen av dem bär
geometri (CAEX **refererar** till externa CAD-filer via
`RefBaseSystemUnitPath`/liknande, precis som `scene.components["uri"]` redan
gör mot katalogindexet) eller fysik (massa/tröghet) — de är rätt verktyg för
FLÖDE och LOGIK, exakt vad operatören frågade efter, och fel verktyg för
kinematik/dynamik, vilket inte är en brist utan definitionen av vad AML/PLCopen
är byggda för.

---

## 4. Vad kostar vägen ut? (grov ordning, billigast först)

1. **Logik: `control.signals` + genererad ST → PLCopen XML.** MÄTT klart i den
   här mätningen. Ett bibliotek (`plcopen` på PyPI), en (1) korrigeringsrunda,
   byte-exakt round trip, validerat mot det officiella schemat. **Billigast,
   och den enda av alla undersökta vägar som är en fullständig,
   schemavaliderad artefakt redan i dag.**
2. **Scen/topologi: `scene.components` + `scene.connections` → CAEX/
   AutomationML.** MÄTT (mot CAEX 2.15). Kräver egen XML-byggkod (inget färdigt
   skrivbibliotek fanns) och en uppgradering till CAEX 3.0 för att matcha
   nuvarande IEC 62714-1:2018 exakt — den senare biten ogjord. **Näst
   billigast.**
3. **Geometri: mesh till ett neutralt CAD-format.** INTE mätt genom körning,
   men BELAGT på tre sätt (ikon, DLL, dokumenterat `.NET`-interface) att VC:s
   GUI/`.NET` troligen redan kan skriva STEP/STL/JT/IGES/SAT/Parasolid/3MF/U3D
   via HOOPS Exchange, plus FBX via ett dokumenterat `IFBXExporter`. Kräver
   `.NET` (Python når det inte, M-07) — ett automatiseringsskript mot VC:s
   `.NET`-API eller ett manuellt GUI-steg. **Sannolikt billigt, overifierat.**
4. **Kinematik: ledträd/gränser → URDF/SDF/MJCF/USD.** Datan finns i Python-API:t
   (M-55: `vcNode.Dof`, `vcJoint.MinValue/MaxValue/...`), men ingen skrivare är
   byggd eller schemavaliderad här. **Medelkostnad** — ren skrivkod mot
   befintlig data, ingen ny mätning eller insamling krävs.
5. **Fysik: massa/täthet/tröghet.** VC bär **noll** av det, bekräftat två
   gånger (M-55, M-59). Alla tre undersökta fysikmotorer (Gazebo, MuJoCo, Isaac
   Sim/USD Physics) kan härleda massa+tröghet ur (kollisionsgeometri × en
   materialtäthet) — vilket krymper uppgiften till en täthetstabell snarare än
   en full massdatabas — men det är en **hypotes om en genväg**, inte en mätt
   noggrannhet. Att verifiera hur fel en vattentäthetsgissning blir mot en
   verklig robots publicerade massa är **inte gjort** och kräver att köra VC
   eller exportera geometri, vilket låg utanför den här mätningens tillåtna yta.
   **Dyrast, och den enda biten som kräver NY data (täthet per material), inte
   bara en skrivare mot data som redan finns.**

---

## Vad som INTE är mätt

* **Ingen faktisk export kördes ur VC.** Allt i del 1 om FBX/STEP/STL/JT/IGES/
  SAT/Parasolid/3MF/U3D/VRML är filnamns-, ikon- och API-signaturbevis
  (BELAGT), inte en producerad och öppnad fil (MÄTT). Instruktionen var
  uttrycklig: starta inte VC.
* **CAEX 3.0 (IEC 62714-1:2018, den faktiskt gällande AutomationML-standarden)
  provades inte.** Bara den fritt tillgängliga CAEX 2.15-texten (2007)
  validerades.
* **IEC 61131-10:2019 som betald standard hämtades inte.** `plcopen`-paketets
  TC6 v2.01-schema (fritt, Beremiz-hostat) användes som stand-in. Sannolikt
  rätt för textuell ST, overifierat för LD/FBD/SFC.
* **Hur fel en täthetshärledd massa blir** mot en verklig komponents verkliga
  massa. Behöver en volymberäkning ur VC:s geometri (STEP-export eller körd
  VC), utanför denna mätnings tillåtna yta.
* **Om en riktig AutomationML-editor/valideringsmotor** (utöver XSD:t)
  accepterar de byggda filerna. Bara `lxml.etree.XMLSchema` kördes.
* **Friktion och ledfriktion** i VC — sökt efter i M-55 (noll träffar) men inte
  fördjupat här mot mottagarnas krav.
* **`ILayoutWriter`/`ILayoutReader`:s faktiska lista av stödda filändelser**
  (`GetSupportedExportFileExtensionInfo()`) lästes bara som API-signatur, aldrig
  anropad — den exakta listan av format VC:s GUI verkligen erbjuder är därför
  fortfarande en slutledning ur DLL-namn, inte en avläst lista.
