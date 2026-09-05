# 53 — Utvägen: vad som måste flytta, och varför "exportera scenen" är fel fråga

Operatörens mål: *"en större helhet där man inte är låst till programvara och
licenser"*, och på sikt en **hot-swap** bort från Visual Components.

Den vanliga formuleringen är *"kan vi exportera scenen till USD?"*. Den frågan
går att besvara med ja eller nej och båda svaren är oanvändbara. Det här
dokumentet ställer om den.

---

## 1. En cell är nio lager, inte ett

| # | Lager | Vad det är | Var det finns i dag | Svårighet |
|---|---|---|---|---|
| 1 | **Geometri** | ytorna man ser | `.vcmx`, och VC:s egna exportvägar | låg |
| 2 | **Placering** | var sakerna står | `PositionMatrix`, kvaternionens ordning **mätt** (`M-72`) | låg |
| 3 | **Kinematik** | leder, gränser, axlar | `vcJoint`; 86,5 % av biblioteket bär leder (`M-85`) | medel |
| 4 | **Fysik** | massa, tröghet | `Mass` deklarerad i **451 av 3 201** (14 %). Tröghet: inte mätt | hög |
| 5 | **Koppling** | vad som matar vad | vår egen komponentmodell (`M-101`), `canConnect` 7 av 7 | **inget format bär det** |
| 6 | **Beteende** | `Path`, `Creator`, `Sink`, `Container` | VC:s egna, mätta i `49_komponentmodellen.md` | **inget format bär det** |
| 7 | **Signaler** | I/O med riktning och typ | bankens `control.signals` | AutomationML kan bära det |
| 8 | **Styrlogik** | den genererade ST:n | vår, IEC 61131-3 | PLCopen XML |
| 9 | **Robotprogram** | rutiner i robotens språk | byggbart i Python, **exporten ligger i `.NET`** (`48` steg 36) | blockerad |

**Lager 1–3 är den lätta halvan, och det är den enda halva "exportera till USD"
handlar om.** Lager 5–8 är där vårt värde ligger, och inget 3D-format bär dem.
USD vet inte att det här transportbandet matar den där bufferten.

---

## 2. Omställningen: flytta inte scenen, flytta receptet

En scen är en **rendering** av en cell. Cellen själv är kortare och mer
värdefull:

> vilka komponenter, var de står, hur de kopplas, vilka signaler de har, och
> vilken styrkod som kör dem.

Det är fem saker, och **fyra av dem har vi redan i ett neutralt format.**
Bankens uppgiftsfiler bär dem i dag:

```json
"scene":   {"components": [{"role": "robot", "uri": "bank://robot/abb_irb_660_180_3150", "count": 1}, …]}
"control": {"signals": [{"name": "ST260_PRT_PRS", "dir": "in", "type": "bool", "comment": "…"}, …]}
"fysik":   {"detalj": {"l_mm": 400, "b_mm": 300, "h_mm": 250, "massa_kg": 12.0}, "arbetsradie_mm": 2800.0}
```

Det är inte en bänkfil som råkar likna en cellbeskrivning. **Det är en
cellbeskrivning som vi råkat använda som bänkfil.** Den saknar bara lager 2
(exakta placeringar) och lager 5 (kopplingslistan), och båda går att läsa ur en
körande VC med verktyg vi redan har.

En simulator som kan ladda komponenterna kan bygga om cellen ur receptet. Den
behöver aldrig se VC:s scen.

---

## 3. Den verkliga kostnaden: `bank://` är en identitet utan värde utanför VC

`bank://robot/abb_irb_660_180_3150` betyder något bara för den som har just den
komponenten. För en hot-swap krävs en **avbildning** från VC:s katalog till
målets bibliotek, och det är utvägens dyraste del — inte filformatet.

Tre vägar, i fallande styrka:

1. **Samma fysiska maskin, andra filen.** En ABB IRB 660-180/3150 finns i ABB:s
   egna CAD- och URDF-paket. Avbildningen går på **tillverkare + modell**, och
   `M-107` byggde redan skiktet som knyter en komponent till tillverkarens
   datablad.
2. **Funktionell ersättning.** Målet har ingen IRB 660 men en robot med
   tillräcklig räckvidd och nyttolast. Kräver att båda talen bär **enhet** —
   och `M-85` mätte att bara 14 % av egenskaperna gör det. Det är samma hål som
   `51_komponentdata.md` beskriver.
3. **Primitiv ersättning.** En låda med rätt mått och massa. Duger för
   flödesstudier, inte för räckvidd eller kollision.

**Utan lager 4 och enheterna i lager 3 kollapsar väg 1 och 2 till väg 3.**

---

## 4. Tre format, för ett räcker inte

| Lager | Format | Läge, **mätt i `M-113`** |
|---|---|---|
| 8, styrlogiken | **PLCopen XML** (IEC 61131-10) | **klart i princip.** S-06:s genererade ST byggd till ett TC6-projekt och **validerad mot det officiella schemat**, ST-texten byte-identisk igenom, 17 av 17 signalnamn och typer bevarade |
| 5 och 7, koppling och signaler | **AutomationML** (CAEX) | **validerar.** A-01:s sju komponenter och fem kopplingar byggda som CAEX 2.15 och validerade mot `CAEX_ClassModel_V2.15.xsd`. **Men** gällande AutomationML (IEC 62714-1:2018) är CAEX **3.0** — inte prövat |
| 1, geometrin | **STEP, STL, JT, IGES, SAT, Parasolid, 3MF, U3D, VRML, FBX** | VC har **HOOPS Exchange 2024.12** i installationen med nio skrivar-DLL:er, plus Autodesks FBX-SDK och ett dokumenterat `IFBXExporter.Export`. **Belagt ur filer och .NET-referens, inte kört** |
| 1–4 mot en fysikmotor | **USD, URDF, SDF, MJCF** | ingen skrivare finns i VC. Måste byggas |

**USD var fel gissning.** Det finns ingen USD-väg ur VC — men det finns nio
neutrala CAD-format som redan ligger i installationen. Geometrin var alltså
aldrig problemet.

Att det krävs tre format är inte ett misslyckande. Det är att en cell inte är en
modell utan tre: **en kropp, en anläggning och ett program.**

### Fysiken krympte till ett tal per material

Lager 4 såg ut som den hårda väggen: VC bär massa i bara 14 % av biblioteket och
ingen tröghet alls.

`M-113` mätte att **Gazebo, MuJoCo och Isaac Sim oberoende konvergerar på samma
reservlösning**: räkna massa och tröghet ur **kollisionsgeometrin** gånger en
densitet, med förvalet **1000 kg/m³** (vatten) när ingen anges. VC har
kollisionsformer (`M-55`) men noll densitet någonstans.

Problemet är alltså inte en tröghetsdatabas. Det är **ett densitetstal per
material** — och det är en helt annan storleksordning arbete.

Förbehåll som hör till: att reservlösningen ger *rätt* massa är **inte mätt**
mot någon verklig maskins kända vikt. Den krymper problemet, den löser det inte.

---

## 5. Ordningen, och varför den är den här

**Först receptet.** Skriv ut cellen ur en körande VC i det format banken redan
använder, utökat med placeringar och kopplingslista. Kräver ingen ny standard,
ingen ny beroendekedja, och ger omedelbart något: en cell som går att
återskapa. **Trasigt fall:** en cell som skrivs ut och läses in igen måste ge
samma `canConnect`-svar och samma materialflöde — annars beskrev receptet inte
cellen.

**Sedan avbildningen.** Knyt `bank://`-identiteterna till tillverkare och modell
med enhet och källa. `M-107` har börjat; 21 komponenter har en enhet med källa
och 2 965 står som `enhet_saknas`.

**Sist formaten** — men de är billigare än väntat. PLCopen XML och CAEX är
mätta som fungerande i `M-113`, och geometrin ligger redan i VC:s egen HOOPS-
och FBX-installation. Serialiseringen är alltså **inte** flaskhalsen; receptet
och avbildningen är det. Byggs formaten först blir de en export av något vi
inte kan beskriva.

---

## 6. Vad detta INTE är

Det är **inte** en väg att köra VC:s scen i Isaac Sim. Beteendelagret (5–6) har
ingen motsvarighet där, och en transportör i VC är inte en transportör i USD —
det är en yta med en Path-komponent som VC:s motor tolkar.

Och det löser inte lager 9: robotprogrammets export ligger i `.NET`, utanför
Python-API:t. Går den inte att nå är den vägen ut lika stängd som scenexporten,
och det står som en öppen punkt tills någon mätt den.

Ingenting i det här dokumentet är byggt. Det beskriver ordningen och de tre
kostnaderna, så att det som byggs börjar i rätt ände.
