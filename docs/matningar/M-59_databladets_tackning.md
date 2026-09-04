# M-59 — databladets täckning: vad de 3201 komponenterna faktiskt bär

**Datum:** 2026-09-04 · hela biblioteket ur M-57, 3201 komponenter, 0 oläsbara
**Gäller:** `svc/vc_assist_svc/datablad.py` (ny), `katalogindex.py`
**Kompletterar:** M-55 (ingen massa i Python-API:t), M-57 (biblioteket),
M-58 (var fälten ligger)

Mätningen kördes över hela biblioteket, inte ett stickprov. Varje tal nedan har
nämnaren skriven bredvid sig.

Tabellerna i avsnitt 2 och 8 byggs av den kod som levereras, och går att köra om:

    cd svc && python3 -m vc_assist_svc.datablad

Ett enskilt datablad: `python3 -m vc_assist_svc.datablad --visa "IRB 6700"`,
med `--fullt` för den fulla formen.

---

## 1. Vad ett datablad är

Indexet svarar på **vad** som finns. Databladet svarar på **vilken** man ska
välja. Skillnaden är storheterna: antal axlar, ledgränser, räckvidd,
bandlängd, hastighet, monteringsgränssnitt.

Varje storhet bär `harkomst`, och den är ett fält — inte prosa:

| harkomst | betyder |
|---|---|
| `last` | stod ordagrant i metadatan; `kalla` säger var |
| `harledd` | räknad fram; `kalla` säger ur vad och med vilken formel |
| `saknas` | finns inte; `kalla` säger vad som letades efter |

---

## 2. Täckningen, storhet för storhet

Kolumnen **tillämplig** är nämnaren: hur många komponenter storheten alls hör
till familjen för. En robot har ingen bandhastighet, och det är inte ett hål i
datan — det är en fråga som inte har ett värde. De två svaren blandas aldrig.

| Storhet | tillämplig | läst | härledd | saknas |
|---|---:|---:|---:|---:|
| frihetsgrader | 2 275 | 2 201 | 37 | 37 |
| ledtyper | 2 275 | 2 238 | 0 | 37 |
| ledgränser | 2 275 | 2 206 | 0 | 69 |
| maxhastighet | 2 202 | 2 201 | 0 | 1 |
| maxacceleration | 2 202 | 2 201 | 0 | 1 |
| **räckvidd** | 2 202 | **0** | **1 693** | 509 |
| monteringsram | 2 202 | 2 202 | 0 | 0 |
| basram | 2 202 | 2 202 | 0 | 0 |
| styrenhet | 2 202 | 2 202 | 0 | 0 |
| kinematik | 2 202 | 2 201 | 0 | 1 |
| **nyttolast** | 2 275 | **426** | 0 | **1 849** |
| **egenvikt** | 3 201 | **0** | 0 | **3 201** |
| verktygslast | 2 202 | 46 | 0 | 2 156 |
| längd | 926 | 63 | 0 | 863 |
| bredd | 926 | 113 | 0 | 813 |
| höjd | 926 | 115 | 0 | 811 |
| hastighet | 227 | 115 | 0 | 112 |
| kapacitet | 227 | 89 | 0 | 138 |
| gränssnitt | 3 201 | 2 963 | 0 | 238 |
| monteringsgränssnitt | 73 | 73 | 0 | 0 |

**Läst mot härledd: 20 162 avlästa fält mot 1 730 härledda.** Bara två storheter
är någonsin härledda — räckvidden (1 693 av 1 693 härledda, aldrig läst) och
frihetsgraderna för de 37 verktyg som har leder men ingen robotstyrning som
listar dem.

Familjerna: **robot 2 202 · övrig 699 · transportör 227 · verktyg 73.**
Hela biblioteket byggs på **19 s**.

---

## 3. Vad som ärligt saknas

### Egenvikten finns inte. 0 av 3 201.

Ingen komponent bär sin egen massa. Tre fält ser ut som svaret:

| Fält | antal | vad det faktiskt är |
|---|---:|---|
| `WT_Weight` | 26 | *Werkstückträgerns* vikt — lastbäraren som **åker på** bandet. Bär `Quantity "Mass"`, så den ser ut som en egenvikt ända in i enheten |
| `Advanced::StructureWeight` | 11 | en **procentsats** (`Quantity "Percentage"`, värdet 0,6 i alla elva) för ytutnyttjande |
| `Radius` | 272 | ett **uttryck**, `0.5*sassd(145,180-J1,75)`, som ritar en cirkel i vyn |

De står i `FORKASTADE_FALT` i koden med skälet, så att nästa läsare inte hittar
dem igen och tror att hålet är lagat.

### Nyttolasten finns för 426 av 2 275, inte för alla

Det finns **inget gemensamt payload-fält**. Tre namn bär det, och tillsammans
täcker de mindre än en femtedel:

| Rotvariabel | träffar | Quantity |
|---|---:|---|
| `MaxLoad` | 341 | `Mass` |
| `Payload` | 124 | `Mass` i 81 av 124, inget alls i 43 |
| `MaxPayload` | 3 | `Mass` |

De 1 849 övriga får `saknas`. Frestelsen var att räkna fram ett tal — ur
modellnamnet, ur katalogen, ur en tabell — så att kolumnen ser ifylld ut. Ett
datablad där payload alltid står ifyllt ser komplett ut och ljuger snyggt.

### Räckvidden saknas för 509 robotar av 2 202

| Kinematiktyp | räckvidd gick | saknas |
|---|---:|---:|
| `rKinArticulated2` | 1 232 | 0 |
| `rKinScara2` | 407 | 0 |
| `rKinParallellogram` | 14 | 0 |
| `rPythonKinematics` | 40 | **506** |
| `rKinScara` (äldre) | 0 | 2 |

`rPythonKinematics` bär kinematiken som ett **Python-skript** i stället för som
namngivna länklängder. 40 av 546 lägger ändå sina mått i komponentens egna
variabler (`LinkLength1..5`, `JointOffset1..4`) och går att läsa. De övriga 506
har måtten inne i skriptkoden, och att tolka den koden vore en ny mätning.

### Massan, åt båda hållen (rättar M-55)

M-55 mätte att VC:s **Python-API** ger noll massa och noll tröghet. Filformatet
bär fälten `Mass`, `CenterOfGravity` och `Inertia` — men de sitter på
**verktygsramar**, inte på komponenten, och de är i praktiken tomma:

* 2 274 av 3 201 komponenter har minst en `Mass`-rad
* 392 av dem har ett värde skilt från noll
* **351 av de 392 har värdet `-1000`** — en negativ massa, alltså en sentinel
  för "ingen last satt". Den som läser raden rakt av får en robot med minus ett
  kilos verktygslast

Efter att noll och `-1000` räknats bort: **46 av 2 202 robotar** bär en
verktygslast. M-55:s fynd gäller alltså åt båda hållen — det finns ingen massa
att hämta, varken genom API:t eller ur filen.

### Ledgränser som är uttryck

**718 komponenter** har minst en ledgräns som är ett **uttryck** i stället för
ett tal, till exempel

    Axis2<-55.0?-9.000*Axis2-605.0:(Axis2<-45.0?-5.500*Axis2-412.5:-170.0)

— axel 3:s gräns beror på var axel 2 står. Uttrycket står kvar som uttryck i
databladet i stället för att räknas om till ett tal. Ett tal där skulle vara ett
påstående om ett arbetsområde ingen mätt.

---

## 4. Räckvidden: ett facit som ligger utanför koden

Räckvidden är den enda storhet som **alltid** är härledd, och därför den enda
som kan bli en tyst uppgradering från gissning till fakta. Den fick ett facit
som inte kommer ur formeln: **407 robotar bär tillverkarens egen räckvidd i sitt
modellnamn** — `KR 210 R2700` är 2 700 mm, `IRB 6700-300/2.60` är 2,60 m.

Tre formelvarianter mot 386 ledade armar:

| Formel | median | inom 5 % | inom 10 % |
|---|---:|---:|---:|
| `L12X+|L23|+|L34|+|L45|+|L56|` (alla länkar) | 1,086 | 22 | 276 |
| **`L12X+|L23|+|L34|+|L45|`** (utan flänslänken) | **1,001** | **379** | 381 |
| `L12X+|L23|+|L34|` (till handledscentrum) | 1,001 | 369 | 375 |

Att summera **alla** länkar ger åtta procent för långt, systematiskt — för
tillverkaren mäter till handledens centrum, inte till flänsen. Den valda formeln
lämnar flänslänken `L56` utanför och ligger då 0,1 % från tillverkarens eget tal
i median.

För de andra kinematiktyperna träffar formeln **exakt**:

| Typ | n | median | inom 5 % |
|---|---:|---:|---:|
| `rKinScara2` (`L12X+L23X`) | 11 | 1,000 | 11 |
| `rKinParallellogram` | 10 | 1,000 | 10 |

`KR 120 R3200 PA`: `JointOffset1 350 + LinkLength2 1350 + LinkLength3 1220 +
LinkLength4 280 = 3200`. Exakt R3200.

**Formeln är VALD mot facit**, och det står i koden. Ledgränserna är inte
inräknade, så talet är fortfarande en övre gräns — men en övre gräns som ligger
0,1 % fel i median, inte 8 %. 386 av de 1 232 ledade armarna ingick i provet;
för de övriga 846 är formeln en extrapolation.

---

## 5. Familjen läses ur strukturen, inte ur katalognamnet

M-58 visade att "kategori" i grunt läge är katalognamnet. Här är vad det kostar.
Familjen bestäms i stället av vilka `Functionality`-block komponenten bär.

| | katalognamnet | strukturen |
|---|---:|---:|
| robotar | 1 736 | **2 202** |
| transportörer | 45 | **227** |

**466 robotar ligger utanför katalogen `Robots`** — i `Archiv` (58), `Legacy`
(53), `KR_CYBERTECH_2` (21), `Advanced Motion` (21), `extra` (20), `Quantec-2`
(20), `ultra` (19), `Fortec-2` (17) och ett femtiotal till. Åt andra hållet är
katalogen ren: **0 komponenter i `Robots` är något annat än robotar.**

För transportörerna är felet fyrfaldigt: 45 i `Conveyors`, **182 utanför**.

En agent som söker robotar på katalognamnet missar alltså var fjärde robot och
fyra av fem transportörer.

---

## 6. Rotens variabelrymd, inte all text

`Length`, `Width` och `Height` finns i nästan varje komponent. De sitter till
överväldigande del i **geometriprimitiver** (`rPrimitiveBoxFeature`,
`rExtrudeFeature`), där de är en lådas mått. `Prorunner mk1` har namnet
`Length` **24 gånger** i sina 16 geometrilådor och **noll** gånger som
komponentens egen egenskap. `Height` står där 23 gånger, också noll i roten.

Databladet läser därför bara **rotnodens egen variabelrymd** — den användaren
ser i egenskapspanelen. Det befintliga `katalogindex._parametrar` gör inte det,
och en oscopad sökning efter `Height` ger bandets sista rullstöd och ser
likadan ut som ett svar.

Mätt i samma svep: `Item/Robot Pedestals/Robot enclosure with conveyor belt`
matchar `ConveyorLength` i råtexten men har **ingen** sådan rotvariabel.

---

## 7. Enheterna kommer ur filen

VC skriver `Quantity` bredvid de flesta tal. Avbildningen till enhet:

| Quantity | enhet |
|---|---|
| `Distance` | mm |
| `Angle` | grad |
| `Angular velocity` / `Angular acceleration` | grad/s, grad/s² |
| `Velocity` / `Speed` / `Acceleration` | mm/s, mm/s² |
| `Mass` | gram *(se nedan)* |
| `Time` / `Percentage` | s, % |

Där `Quantity` saknas — `ConveyorSpeed` i 100 av 116 — sägs det i källan, och
enheten tas då från VC:s världsenhet (M-33) i stället för att antas tyst.

### Massenheten är gram, och det är mätt

`MaxLoad` i `KR 20 R1810` är **20 000**. I `KR 12 R1810` är den **12 000**. I en
robot som heter `Education Robot System` och tar 3 kg är den **3 000**. ABB
`IRB 6620LX` med 70 kg bär `Payload 70000`. Modellnumret är kilo och fältet är
tusen gånger större — fältet är alltså i gram. Databladet räknar om till kilo
och säger i källan att det gjort det.

---

## 8. Tokenkostnaden

Två former. **Kort är standard.** Tecken per komponent, hela biblioteket:

| Form | min | median | p95 | max | medel |
|---|---:|---:|---:|---:|---:|
| kort text | 40 | **152** | 167 | 514 | 136 |
| kort JSON | 97 | **387** | 435 | 612 | 335 |
| full text | 273 | 914 | 1 179 | 1 591 | 864 |
| full JSON | 811 | 2 969 | 3 565 | 3 975 | 2 532 |

Bara robotar: kort text median **156**, kort JSON median **395**.

Tio robotar att välja mellan kostar alltså **1 560 tecken** som text och
**3 950** som JSON. Med `25_kontextbudget.md`:s antagande om 4 byte per token är
det **390 respektive 990 tokens**.

Post 8 i kontextbudgeten (de senaste verktygsresultaten) är 25 % av profilen. På
128 000 tokens är det 32 000 tokens ≈ 128 kB, alltså plats för ungefär **840
korta textdatablad** eller **330 korta JSON-datablad** — men bara **140** fulla
textdatablad.

Den korta JSON-formen bär `harkomst` men inte `kalla`. Källsträngarna var
**två tredjedelar** av tecknen: median gick från 795 till 387 när de togs bort.
Den mekaniska skillnaden mellan läst, härledd och saknas är fältet `harkomst`,
och det står kvar i båda formerna. Det är den skillnaden regeln handlar om.

---

## 9. Ordförrådet

Tjugo storheter, samma namn oavsett tillverkare, mot bibliotekets **2 665**
unika parameternamn (räknat med rotens och alla underblocks variabler; M-58:s
1 806 räknade en smalare uttagsform).

    frihetsgrader · ledtyper · ledgranser · maxhastighet · maxacceleration
    rackvidd · monteringsram · basram · styrenhet · kinematik
    nyttolast · egenvikt · verktygslast
    langd · bredd · hojd · hastighet · kapacitet
    granssnitt · monteringsgranssnitt

Avbildningen storhet → parameternamn, med träffar:

| Storhet | rotvariabler, i prioritetsordning | träffar |
|---|---|---:|
| nyttolast | `MaxLoad`, `MaxPayload`, `Payload` | 341 / 3 / 124 |
| längd | `ConveyorLength` | 63 |
| bredd | `ConveyorWidth` | 113 |
| höjd | `ConveyorHeight` | 115 |
| hastighet | `ConveyorSpeed` | 116 (varav 100 utan `Quantity`) |
| kapacitet | `Advanced::ConveyorCapacity`, `Advanced::Capacity_Section1` | 89 / 20 |

Resten läses ur strukturen i stället för ur en namngiven variabel:
frihetsgrader ur `rSimRobotController/JointMap`, ledgränser ur `Dof/MinLimit`
och `Dof/MaxLimit`, hastigheter ur `Dof/Properties/MaxSpeed`, monteringsram ur
`rSimRobotController/FlangeNode`, gränssnitt ur `Functionality "rSimInterface"`.

**Frihetsgrader räknas ur `JointMap`, inte ur antalet `Dof`-block.** En
IRB 6700 har åtta `Dof`-block — sex styrda axlar, en fast och två följare.
`Dof`-blocken skulle ge åtta.

---

## 10. Funktionsytan

Sökskiktet ägs av huvudtråden. Databladslagret lämnar den här ytan:

```python
from vc_assist_svc import datablad

datablad.las(sokvag, tillverkare="")     -> Datablad     # en .vcmx på disk
datablad.fran_text(text, sokvag, tillv)  -> Datablad     # en component.rsc
datablad.bygg(rot)                       -> ([Datablad], [olasliga])
datablad.tackning([Datablad])            -> {storhet: {tillamplig,last,harledd,saknas}}

blad.kort()        -> dict     # identitet + de storheter som avgör valet
blad.fullt()       -> dict     # familjens alla storheter, med källa
blad.kort_text()   -> str      # 152 tecken i median
blad.full_text()   -> str
blad["rackvidd"]   -> Varde    # Databladsfel om storheten inte hör till familjen
blad.har("rackvidd") -> bool

datablad.STORHETER            # ordförrådet: 20 namn -> (enhet, beskrivning)
datablad.FAMILJENS_STORHETER  # vilka storheter varje familj har
datablad.KORTA_STORHETER      # vilka som ryms i den korta formen
datablad.FORKASTADE_FALT      # fälten som ser ut som svaret och inte är det
```

`Varde` bär `storhet`, `varde`, `enhet`, `harkomst` och `kalla`. Konstruktorn
faller på ett värde utan källa, på `SAKNAS` med ett värde, och på en härkomst
som inte är en av de tre.

Att fråga efter en storhet som inte hör till familjen ger ett `Databladsfel`
med familjens lista — inte `saknas`. De två svaren betyder olika saker.

---

## 11. Förslag till `docs/spec/` (ägs av huvudtråden, inte ändrad här)

1. **`45_verktyg.md`:** ett katalogsökverktyg ska svara i den **korta** formen.
   Full form bara för en namngiven komponent.
2. **`25_kontextbudget.md`:** en komponentlista hör till post 8. Talen i
   avsnitt 8 ovan (152 tecken kort, 914 fullt) ersätter en gissning.
3. **`41_ogat_kontrakt.md`:** ett värde ur ett datablad som når en dom ska bära
   sin `harkomst`. En `harledd` räckvidd får inte döma som en `last`.
4. En spec-rad om att **familj läses ur strukturen**: katalognamnet missar 466
   robotar och 182 transportörer.

---

## 12. Vad som INTE är mätt

* **De 506 `rPythonKinematics`-robotarnas räckvidd.** Måtten finns i
  skriptkoden. Att tolka den är en egen mätning.
* **Om den valda räckviddsformeln håller för de 846 ledade armar som inte har
  räckvidden i namnet.** Provet var 386 av 1 232.
* **`Advanced::ConveyorCapacity` = 9999.** Värdet ser ut som en sentinel för
  "obegränsad" men är inte mätt som en. Det rapporteras som läst.
* **Ingen komponent är laddad i VC.** Att fälten går att läsa ur filen är inte
  samma sak som att VC ger samma tal när komponenten står i en scen. Det är
  M-57:s öppna rad och den står kvar.
* **Gränssnittens typer och riktningar.** Databladet ger namnen och skiljer
  värd från gäst; vad de kan kopplas till är inte läst.
