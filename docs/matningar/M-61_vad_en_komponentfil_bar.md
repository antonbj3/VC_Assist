# M-61 — vad en komponentfil bär, och varför den omslutande volymen inte står i den

**Datum:** 2026-09-04/05 · VC Premium 4.10 · testprefixet `~/.wine-vc-test`
**Nämnare:** **3201 komponentfiler**, 149 tillverkare, **0 oläsbara** — hela
biblioteket ur M-57, inte ett urval.
**Mätt med:** `python3 -m vc_assist_svc.komponentfil --svep`, alltså med koden
som levereras. **Ingen VC har rörts.**

## Talen först

| Storhet | läst | härledd | saknas | av |
|---|---:|---:|---:|---:|
| **komponentens omslutande volym** | **0** | **0** | **3201** | 3201 |
| namn, kategori, tillverkare | 3201 | 0 | 0 | 3201 |
| räckvidd | 1437 | 225 | 1539 | 3201 |
| nyttolast (`MaxPayload` > 0) | 2358 | 0 | 843 | 3201 |
| gränssnittens **namn** | 11 563 | 0 | 0 | 11 563 |
| — av dem med minst ett fält | 9 167 | 0 | 2 396 | 11 563 |
| — av dem med en ram | 9 318 | 0 | 2 245 | 11 563 |
| komponenter som bär minst ett gränssnitt | 3062 | 0 | 139 | 3201 |
| monteringsramarnas **namn** | 9824 | 0 | 0 | 9824 |
| monteringsramarnas **läge** | 3036 | 121 | 6667 | 9824 |
| ledernas **typ** | 29 405 | 0 | 0 | 29 405 |
| — ledens namn | 27 726 | 0 | 1 679 | 29 405 |
| — båda ledgränserna | 23 355 | 0 | 6 050 | 29 405 |
| geometriblobbens **egen** låda | 0 | 67 907 | 11 128 | 79 035 |

Första raden är hela mätningen. **Ingen av de 3201 filerna bär komponentens
omslutande volym.** Det är inte slarv, och nästa avsnitt säger varför.

De 225 härledda räckvidderna kräver att geometrin läses. Läses filen utan
geometri säger svaret `saknas` med skälet **"rackviddsprofilen är INTE LÄST"**
— ett annat svar än "det finns ingen profil", och skillnaden står i klartext i
stället för att döljas i samma ord.

Mätningen körs om med:

    python3 -m vc_assist_svc.komponentfil --svep --ut <fil>     # hela svepet
    python3 -m vc_assist_svc.komponentfil --fil <komponent>     # en fil

Biblioteksroten söks upp, aldrig antas (`katalogindex.hitta`). Hittas ingen
skrivs listan över vad som provades.

## Varför lådan inte finns i filen

Den är ingen egenskap hos filen. Den är en egenskap hos den **byggda**
komponenten, vid en viss parameteruppsättning och en viss ställning.

| Vad som styr var geometrin hamnar | antal | av |
|---|---:|---:|
| transformer med ett **uttryck** över komponentens parametrar | **32 221** | 39 171 |
| — av dem som *också* bär en färdig matris | 5 369 | 32 221 |
| transformer med tomt uttryck och ingen matris | 4 230 | 39 171 |
| geometriposter bakom en **switch** (syns bara ibland) | 17 901 | 79 035 |
| geometriposter under minst ett okänt led i kedjan | 48 516 | 79 035 |
| geometriposter med helt **konstant** kedja | 12 618 | 79 035 |
| komponenter där **all** geometri har konstant kedja | **140** | 3201 |
| leder (robotens låda beror på ställningen) | 29 405 | — |

**82 procent av bibliotekets transformer är uttryck**, och fyra femtedelar av
dem bär inte ens en färdig matris vid sidan om. Att räkna fram lådan ur filen
är därför att värdefästa VC:s uttrycksspråk, tolka dess switch-semantik och
lösa dess kinematik — alltså att bygga om VC:s bygge, utan något facit att
pröva bygget mot.

Och även den som gjorde det skulle sakna geometri. Av bibliotekets 79 035
geometriposter pekar **5886, i 234 komponenter, på en fil UTANFÖR arkivet** —
på författarens egen maskin
(`file:///C:/Users/HannuKe1/OneDrive+-+KUKA+AG/Documents/...`). Ytterligare
2096 bär ingen URI alls. Den geometrin finns inte att räkna på, oavsett hur
väl man värdefäster uttrycken.

## Tre ställen jag letade, och vad som inte fanns

**1. `model.xml`.** Varje arkiv bär en liten XML-fil med komponentens egna
uppgifter. Över alla 3201 finns exakt **tjugo** egenskapsnamn, och inget av
dem är ett mått:

| Egenskap | i % av 3201 |
|---|---:|
| `VCID`, `ModelType`, `Name`, `Type`, `Manufacturer`, `Revision`, `DetailedRevision`, `IsDeprecated` | 100,0 |
| `MaxPayload` | 93,3 |
| `Description` | 92,3 |
| `Author` | 89,5 |
| `Tags` | 87,2 |
| `Reach` | 79,9 |
| `ImageUri`, `ThumbnailUri`, `Modified` | ~50 |
| `Website`, `Email` | 20,7 / 9,6 |

**2. `component.rsc`.** Ett svep efter bboxliknande ord över alla 3201 gav
träffar som alla föll när jag läste sammanhanget — och att läsa sammanhanget
var hela skillnaden:

| Ordet | filer | vad träffen faktiskt var |
|---|---:|---|
| `Extent` | 171 | parametern **`Extention`**, en länks utskjut |
| `Envelope` | 1684 | switchen **`ShowEnvelope`** och geometrin `EnvelopeProfile`, alltså visningen av räckviddshöljet |
| `Dimensions` | 78 | **kommentarer i inbäddad Python** ("remove all known dimensions") |
| `AABb`, `bboX`, `bBOX` … | ~30 | delsträngar i `AuthoringHash`, alltså hexadecimalt brus |

En skiftlägesokänslig sökning som inte läser sammanhanget hade rapporterat
"bounding box finns i 1855 filer". Den hade varit helt fel.

**3. VC:s egen eCatalog-databas.** `eCatalog_4.10.2.sdf`, 28 MB — den katalog
programmet självt söker i. Metoden är grov, en strängsökning i binärfilen, och
den redovisas som sådan: de enda storhetsnamn som alls förekommer är `Reach`
(6003 gånger), `Size` (2) och `MaxPayload` (1). Ingen låda, ingen
utsträckning, inget fotavtryck. **VC cachar den alltså inte heller** — vilket
är väntat om den räknas när komponenten byggs.

## Vad som däremot går att läsa, och vad det kostar

| Läsning | 3201 filer |
|---|---:|
| bara `model.xml` | **0,63 s** |
| `component.rsc` grunt, 4 096 byte (M-58) | 1,8 s |
| `component.rsc` helt | 7,3 s |
| helt + gränssnitt, ramar, leder | 125 s |
| helt + alla 79 035 geometriblobbar | ~11 min |

### Detta stänger M-58:s öppna fråga

M-58 mätte att `Category` i `component.rsc` ligger vid **median byte 142 724**
och därför aldrig nås i grunt läge, så att `kategori` i det grunta indexet
kommer från **katalognamnet**. Frågan som lämnades öppen var: *skiljer sig de
två någonsin?*

Ja. **651 av 3201 — en av fem.**

| katalognamn | komponentens egen `Type` | antal |
|---|---|---:|
| `Archiv` | Robots | 58 |
| `Legacy` | Robots | 53 |
| `Series-2` | Robot Workpiece Positioners | 25 |
| `Deprecated` | Robot Workpiece Positioners | 20 |
| `extra`, `ultra`, `sixx` | Robots | 55 |
| `TS 1`, `TS 2` | Conveyors | 35 |

"Archiv", "Legacy", "extra", "ultra", "sixx" och "TS 1" är mappnamn, inte
kategorier. Och kategorin behöver inte längre gissas: den står i `model.xml`,
omkring byte 400 i en 1,5 kB-post, **3201 av 3201 på 0,63 sekunder**, och där
är den komponentens egen.

## Räckvidden: ett fält och en profil

`Reach` i `model.xml`:

| | antal | av 3201 |
|---|---:|---:|
| positivt tal | 1437 | 44,9 % |
| **noll** | 1119 | 35,0 % |
| saknas helt | 645 | 20,1 % |

För de 2169 robotarna: 1434 positiva, 312 nollor, 423 utan fältet. **735
robotar har alltså ingen räckvidd i sitt eget datablad.**

Men 702 komponenter — alla robotar — bär arkivposten `envelopeprofile`:
robotens **räckviddsprofil**, en polylinje i ett lodrätt snitt genom
arbetsvolymen, i millimeter. Alla 702 går att avkoda, och **225 av de 735
hålen fylls av den.**

### Avkodningen är korsprövad, inte gissad

Profilen ligger i **två format** under samma postnamn:

* **3DS-varianten**, 505 filer: chunk `0x8001`, punkter som `float64`
* **textvarianten**, 197 filer: rader med punkter och kanter
* summa 702, och alla 702 avkodas

Av de 505 3DS-filerna hittas chunken genom trädgången i 498. I **7** går
trädgången sönder — objektet `TRACE` bär två oförklarade byte mellan sina barn
— och där måste chunken bytesökas. Då avgör en **exakt längdmatchning** om
fyndet duger: strukturen ska ta slut precis där nyttolasten tar slut. Utan det
kravet läses brus som geometri. De sju bär dessutom en tredje layout inne i
chunken (en enda polylinje i stället för segment), och deras radier stämmer
med `Reach` inom 4 mm i sex fall av sju.

Beviset för att avkodningen är rätt kommer utifrån:

| Prov | Utfall |
|---|---|
| ABB CRB 1100-4/0.475: profilens radie mot `Reach` | **475,0 mm mot 475** |
| profil mot `Reach` där båda finns (n = 477) | median **−0,59 mm**; \|d\| ≤ 1 mm i 208, ≤ 10 mm i 399, ≤ 50 mm i 437 |
| ABB IRB 120, `Reach` saknas | profilen ger **579,8 mm**; ABB publicerar 580 |
| ABB IRB 6640-235/2.55, `Reach` = 0 | profilen ger **2547,4 mm**; namnet säger 2,55 m |
| Kawasaki FD50N | profilen ger **2101,0 mm**; `Reach` säger 2104 |

### Och profilen ligger inte alltid i samma plan

Detta var det tredje övertrampet i mitt eget svep, och det syntes bara för att
jag räknade om hela biblioteket.

Radien lästes först som största `|x|`. Det stämmer för ABB, Fanuc, KUKA och de
flesta andra: 652 av 702 profiler ligger i **XZ**-planet. Men **14 profiler,
alla Kawasaki, ligger i YZ-planet**, och för dem gav `|x|` räckvidden
**1 · 10⁻¹³ mm** — ett tal som ser ut som noll och som inget prov på en
ABB-robot kan upptäcka, för där är y noll.

Radien är avståndet från den **lodräta axeln**, `hypot(x, y)`. Efter
rättelsen har ingen profil längre en radie under 1 mm, och Kawasaki FD50N
träffar sitt eget `Reach` på 3 mm.

Klassningen av planet är mätt och inte gissad: den mindre av `max|x|` och
`max|y|` är antingen **under 0,66 mm** (666 profiler, för de flesta 10⁻¹⁴,
alltså flyttalsbrus) eller **över 3,1 mm** (36 profiler, upp till 1099,8 mm).
Gapet är en faktor fem, och `_PLANTOLERANS_MM = 1,0` ligger mitt i det.

De 36 är inte en restpost: de är verkliga **3D-höljen** och inte snitt —
kartesiska aktuatorer vars arbetsrymd är en låda, och robotar som ritats med
hela svepet. Radien är rätt även för dem; "profil" är fel ord.

| Profilens plan | antal |
|---|---:|
| XZ | 652 |
| YZ | **14** |
| varken (3D-hölje) | 36 |

Profilen hittar också fel i VC:s egen data: `IRB 6700-270/2.70 LID` har
`Reach = 270`, alltså nyttolasten i räckviddens fält. Profilen säger 2715,9 mm
och namnet säger 2,70 m.

### Ordningen mellan de två

`rackvidd_ur_fakta` tar det **deklarerade** fältet först och profilen bara när
fältet är tomt eller noll. Skälet: fältet är tillverkarens uppgift, profilen är
geometrins. Där båda finns stämmer de. Svaret bär sin härkomst, så den som
jämför två tal vet vilket av dem han läser.

## Nyttolasten finns — men inte där `datablad.py` letar

`MaxPayload` i `model.xml`: **2358 positiva, 628 nollor, 215 saknade** av 3201.

Att fältet är riktigt går att pröva utan VC, för ABB skriver nyttolasten i
modellnamnet: `IRB 6700-150/3.20` betyder 150 kg och 3,20 m.

> **117 av 117** ABB IRB-robotar med den namnformen har `MaxPayload` exakt lika
> med talet i namnet.

Samma prov på räckvidden: av samma 117 stämmer `Reach` med namnet i 79, är noll
i 18, saknas i 16 och avviker i 4 — varav två är min egen namnläsning (`145`
betyder 1,45 m), en skiljer 50 mm, och en är fältförväxlingen ovan.

Tre tal på samma fråga, och de mäter tre olika ställen:

| Var | Nyttolast finns i | Källa |
|---|---:|---|
| `component.rsc`, rotvariabelrymden | **426 av 2275** | M-59:s tabell |
| samma, enligt `datablad.py`:s inledning | **0 av 3201** | modulens docstring |
| `model.xml` | **2358 av 3201** | den här mätningen, validerad 117 av 117 |

Den mellersta raden är stale. `datablad.py` skriver i sin inledning att
*"nyttolast (payload) finns INTE i någon av de 3201 filerna"*, men modulens
egen mätning M-59 säger 426 och modulens `saknas`-text säger korrekt "ingen av
rotvariablerna". Den blanka meningen i docstringen står kvar och kan läsas som
att fältet inte finns någonstans.

Det är samma felklass som M-34 och M-57: ett tal som inte rör sig är inget
bevis på att ingenting finns. `datablad.py` ägs av M-59 och rörs inte härifrån;
raden står här så att den som äger den kan rätta den.

## Gränssnitten: det en låda inte har

| | antal |
|---|---:|
| gränssnitt | 11 563 i 3062 komponenter |
| gränssnitt **utan namn** | **0** |
| unika gränssnittsnamn | 442 |
| unika sektionsnamn | 181 |
| unika ramnamn | 1703 |

Fälttyperna — det som avgör vad som går att koppla till vad:

| Fälttyp | antal |
|---|---:|
| `rSimHierarchyField` | 16 877 |
| `rSimJointExportField` | 11 024 |
| `rSimToolExportField` | 4 449 |
| `rSimBaseExportField` | 2 222 |
| `rSimFlowField` | 533 |
| `rSimSignalField` | 339 |
| `rSimProcessorField` | 207 |
| `rSimRslField` | 20 |

`rSimHierarchyField` bär `Mount`: **9548 med 1** (monteras PÅ något) och **7329
med 0** (tar emot). `rSimFlowField` bär `Port`: 224 med 0 (in), 234 med 1 (ut)
och 75 med 2 till 6 — grenar och samlingar.

Alla 11 563 gränssnitt har ett namn, men **2396 har inget fält alls** och 2245
ingen ram. Ett gränssnitt utan fält går inte att para ihop med något genom de
två reglerna nedan, och det ska stå i talet i stället för att döljas i
summan. 4858 av 11 563 är dessutom `Abstract` — mallar som VC fyller i vid
anslutning, inte färdiga uttag.

Det ger två **kandidatregler**, lästa ur datan och inte uppfunna:

1. flöde: port 1 i A mot port 0 i B
2. montering: `Mount 1` i A mot `Mount 0` i B, med minst en gemensam fälttyp

De 75 flödesfälten med port 2–6 täcks **inte** av regel 1, och det står i
koden. Ett par som inte föreslås är inte ett par som är omöjligt.

Om VC håller med går bara att veta genom att fråga VC, och `canConnect` dödade
pumpen en gång (M-16). Frågan ligger därför i
`tests/protocol/fas5_riktiga_komponenter.md` steg 8, med tre par som regeln
**avvisar** och som måste svara falskt — annars mäter grinden ingenting.

### Lederna

29 405 rörliga leder (`Dof` skild från `Fixed`). Typerna är inte två utan tolv:

| Typ | antal | | Typ | antal |
|---|---:|---|---|---:|
| `Custom` | 13 806 | | `RZ` | 710 |
| `Rotational` | 9 991 | | `RY` | 449 |
| `RotationalFollower` | 2 545 | | `TX` | 204 |
| `Translational` | 1 025 | | `TY` | 162 |
| `TranslationalFollower` | 305 | | `TZ` | 98 |
| | | | `RX`, `Dummy` | 110 |

**1679 leder saknar namn** och **6050 saknar minst en av sina två gränser.** En
läsare som antar att varje led är namngiven och begränsad får ett tomt fält att
se ut som noll grader.

## Transportörens längd och riktning

Uppdraget nämner dem särskilt, och svaret är delat på samma sätt som resten.

**Ordningen går att läsa.** Av 163 transportörer bär **122** både ett
flödesfält med port 0 och ett med port 1 — alltså en ingång och en utgång, med
namn och med den ram de sitter på. 41 bär inget flödesfält alls.

**Riktningen som en vektor gör det nästan aldrig.** Av de 324 ramar som
flödesfälten pekar på går **21** att läsa och **303** inte. Ekobals
`Roller Conveyor DPN` säger varför, ordagrant ur filen:

    Start  ->  Tx(-FrontExtension)
    End    ->  Tx(BaseLength-200+BackExtension-4)

In- och utpunkten sitter där komponentens parametrar sätter dem. Utan att
värdefästa uttrycken finns ingen vektor, och att peka riktningen längs
komponentens X vore en gissning som ser komplett ut.

**Längden är inte heller ett fält.** 139 av 163 transportörer har minst en
rotvariabel med `Quantity "Distance"`, men namnen är inte ett schema:

| Rotvariabel med `Quantity "Distance"` | antal av 163 |
|---|---:|
| `ConveyorHeight` | 109 |
| `ConveyorWidth` | 108 |
| `ConveyorLength` | **60** |
| `Advanced::SegmentSize` | 44 |
| `ConveyorRadius` | 21 |
| `Length_iWT`, `UnitLength`, `PalletLength` … | 10–14 var |

`ConveyorLength` finns i 60 av 163. `PalletLength` finns också, och den är
pallens längd, inte bandets. En regel som letar efter "något som heter Length"
hade tagit fel på dem. Rotvariablerna hör till `datablad.py` (M-59), som läser
just rotens variabelrymd och inget annat; den här modulen rör dem inte.

`layout/komponent.flode_ur_fakta()` lämnar därför **ordningen** som ett läst
värde och **riktningen** som `None` med uttrycket som skäl.

## Ramarnas läge, och ett övertramp jag fångade i mitt eget svep

Ramarnas **namn** går att läsa: 9824 av 9824. Deras **läge** är en annan sak.

Första versionen av kedjegången svarade "ramen ligger i origo" för varje ram
utan transformer ovanför sig. Svepet sade då att **7521 av 9824 lägen var
lästa**, alltså 87 procent — ett vackert tal, och fel. Ramar inne i en barnnod
fick ett läge de inte hade, för nodens eget läge står inte i filen.

Regeln är nu: ett läge är läst bara när **hela** kedjan från komponentens rot
ned till ramen är konstant. Tre saker gör den okänd, och alla tre är vanliga:

* ett uttryck (32 221 transformer, 19 892 nodoffset)
* en rörlig led (29 405 stycken)
* en nod utan `Offset` — där antagandet "enhetsmatris" är just den sortens
  gissning som nästan alltid stämmer

Efter rättelsen: **3036 lästa, 121 härledda, 6667 saknas** av 9824.

De 3036 lästa är ramar som inte har någonting ovanför sig och därför ligger i
komponentens **eget origo**. Det håller mot ett oberoende fall: 2046 av 2169
robotar har sin `RootFrame` där, och en robots basram ligger i dess origo.

Provet `test_en_ram_under_en_NOD_utan_offset_ger_saknas` står kvar som den
trasiga fixtur som fäller övertrampet om någon gör om det.

### Ett andra övertramp, i samma svep

`Expression ""` — en tom sträng — finns i **6950 av 39 171** transformer. Första
mätningen räknade dem som uttryck och fick då "39 171 av 39 171", ett tal som
såg starkt ut och var sjutton procent för högt. En tom sträng är ingen
parametrisk del. Provet `test_ett_TOMT_uttryck_ar_inget_uttryck` håller
skillnaden.

Det rätta talet är **32 221 av 39 171**, och slutsatsen står kvar: lådan går
inte att räkna fram ur filen.

Det tredje övertrampet — profilens plan — står under räckvidden. Alla tre har
samma form: en regel som stämmer för det vanliga fallet, och ett tal som ser
starkt ut tills man räknar om hela biblioteket i stället för ett stickprov.
Det är därför svepet går över alla 3201 och inte över trehundra.

## Geometrin går att läsa — men blobbens ram är inte komponentens

Geometriblobbarna är **Autodesk 3DS**. Samma chunktaggar (`0x4D4D` huvud,
`0x4110` hörnlista), så hörnen läses utan VC.

| Geometripostens URI | antal | av 79 035 |
|---|---:|---:|
| pekar på en post i arkivet | 71 053 | 89,9 % |
| pekar **utanför** arkivet (234 komponenter) | 5 886 | 7,4 % |
| ingen URI alls | 2 096 | 2,7 % |
| **ger en låda i sin egen ram** | **67 907** | **85,9 %** |

De som inte ger en låda är punktmoln (`VCPointCloud`), spårkurvor, textformade
profiler och de geometrier som ligger utanför arkivet.

### Att hörnen läses rätt är prövat, inte antaget

Ett hörntal som läses på fel plats ger ändå tal, och de talen ser ut som mått.
Provet som inte går att lura: **triangellistan `0x4120` ligger i en annan
chunk än hörnlistan `0x4110`** och pekar in i den med index. Läses hörnlistan
med fel offset eller fel längd hamnar index utanför.

> Över 300 slumpade komponenter: **71 903 meshar, 24 446 704 trianglar, noll
> index utanför sin egen hörnlista.**

Provet finns kvar som `tds_kontroll()`, med en trasig fixtur i L1 och en
körning över urvalet i L2.

Blobbens låda är en annan storhet än komponentens, och frestelsen att blanda
ihop dem är störst när komponenten har **en enda** blobb. Provet
`test_ingen_lada_uppstar_ens_nar_geometrin_ar_en_enda_blobb` finns för det.

## Vad detta betyder för layoutlösaren

`provscener.py` räknar i dag robotens fotplatta som `0.30 × räckvidden`, märkt
ANTAGET. Fas 5 stängdes på lådor byggda så.

Bryggan är `svc/vc_assist_svc/layout/komponent.py`:

* `objekt_ur_komponent(fakta)` utan låda **kastar `Saknasfel`**, med namnet på
  komponenten och på det som fattas. Den bygger aldrig ett rätblock.
* med `Bounds.ur_svar(get_bounds(...))` blir det ett `Objekt` med VC:s mått,
  ett **MÄTT** ankare, komponentens **egen** kategori och räckvidden ur filen.
* `Bounds` bär också `avlast_vid` — i vilken **ställning** och vid vilka
  **parametervärden** lådan lästes. Lådan är en funktion av båda, så två lådor
  utan sitt tillstånd går inte att jämföra. Tomt betyder "inte noterat", och
  `saknade_matt` säger det.
* `till_verktygsanrop(strikt=True)` — som redan vägrar skriva anrop ur ett
  antaget ankare — släpper då igenom. Det är dörren som öppnas.

Provet `test_lador_ryms_men_de_riktiga_matten_gor_det_inte` ställer de två
bredvid varandra i samma 6 × 1,2 m korridor: den gissade lådan (600 mm) ger
`LOST`, den riktiga (1400 mm) ger `RYMS_INTE`.

## Prov

| Nivå | Fil | Antal |
|---|---|---:|
| L1, attrapperade `.vcmx` | `tests/enhet/test_komponentfil.py` | 44 |
| L1, bryggan | `tests/enhet/test_layout_komponent.py` | 23 |
| L2, det verkliga biblioteket (hoppas över om det saknas) | `tests/enhet/test_komponentfil_bibliotek.py` | 6 |

Trasiga fixturer, tolv stycken: en profil i YZ-planet som ska ge samma radie
som en i XZ, en komponent vars mått saknas, en avhuggen
3DS-blobb, en triangel som pekar utanför sin hörnlista, en profil som inte går
att avkoda, en profilnyttolast som inte går jämnt ut, en tom profil, en ram
under en nod utan `Offset`, ett tomt uttryck utan matris, ett band med bara en
ingång, en cell där en av tre komponenter saknar sin låda — och en layout som
lådorna löser och de riktiga måtten inte löser.

Till dem kommer tre par som `kopplingsbara` ska **avvisa**: två robotar som
båda vill monteras på något, två transportöringångar mot varandra, och en
nodhänvisning inne i ett gränssnitt som inte får räknas som en nod.

## Vad som INTE är mätt

* **Om `get_bounds` täcker hela komponenten.** Verktyget läser rotnodens
  `BoundCenter` och `BoundDiagonal`. Om en robots rotnod bara bär sin egen
  geometri är varje låda i bygget för liten — och en för liten låda ger noll
  kollisioner, alltså ett grönt svar som är fel. Det är fas 5-omkörningens
  steg 2 och dess viktigaste fråga.
* **Om en katalogkomponent alls går att ladda.** `app.load()` mot en `.vcmx` är
  oprövat (M-57), och den här mätningen ändrar inte på det.
* **Om lådan beror på ställningen och på parametrarna.** Sannolikt ja för båda,
  men sannolikt är inte mätt.
* **Om VC:s gränssnittsnamn är samma som filens.** Läsningen här är oprövad mot
  `list_interfaces`.
* **De 75 flödesfälten med port 2–6.**
* **De 36 profiler som inte är snitt utan 3D-höljen.** Radien är största
  avståndet från axeln även för dem, men om VC kallar det talet räckvidd är
  inte prövat.
* **Vad en `Custom`-led är.** Den är den vanligaste ledtypen, 13 806 av
  29 405, och den här mätningen läser bara dess namn och gränser.
* **Den sammansatta lådan för de 140 komponenter vars geometri har en helt
  konstant kedja.** Den *går* att räkna fram — men den går inte att pröva mot
  något utan VC, och en oprövad låda som ser ut som en mätt är precis den
  falska green fas 5 stängdes på. Den erbjuds därför inte. Talet 140 av 3201
  står här så att den som vill lyfta frågan vet hur stor den är.
* **Om `Name` någonsin ligger efter byte 181** — M-58:s öppna rad står kvar,
  men den spelar mindre roll nu: namnet läses ur `model.xml`.
* **Två tolkare av samma format.** `datablad.py` läser rotens variabelrymd med
  en radbaserad tolk som med flit hoppar över `Feature`-block; den här modulen
  läser just de blocken och behöver en teckenbaserad tolk, för biblioteket bär
  `Frame { Name "x" }` på en rad. De löser olika uppgifter, men två tolkare av
  ett format är skuld tills någon mätt att en av dem räcker.
