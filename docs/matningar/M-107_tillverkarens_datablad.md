# M-107 — tillverkarens datablad som tredje källa: 21 komponenter av 3201 fick en enhet som inte är gissad

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_m107_bygg_korpus.py` (hämtningen och korpusen)
och `tests/protocol/kor_m107_berikningen.py` (svepet över biblioteket)
**Det som byggs och prövas:** `svc/vc_assist_svc/tillverkardatablad.py`,
korpusen i `data/tillverkardatablad/`, och fältet `katalogfalt` i
`svc/vc_assist_svc/komponentdatablad.py`
**Prövar:** `docs/spec/51_komponentdata.md` §2 och §4 — den tredje källan, som
specen kallade *specificerad här, inte byggd*.

## Frågan

M-85 mätte att bara **14,0 %** av bibliotekets 82 383 egenskaper deklarerar
vilken storhet de bär, och att `MaxPayload` står i katalogposten i **2 986 av
3 201** komponenter **utan enhet** — **628** av dem med värdet `0`.

Utan enhet kan ingen grind döma ett tal. `12,0` mot `180` är två tal, inte en
jämförelse. Frågan är vad tillverkarnas publicerade datablad kan lägga till,
och exakt hur långt det räcker.

## Populationen: två av tre komponenter är robotar

| | antal | andel |
|---|---|---|
| komponenter i biblioteket | 3 201 | |
| **robotar** (markör `rSimRobotController` i strukturen, samma som M-69) | **2 202** | **68,8 %** |
| transportörer | 227 | 7,1 % |
| verktyg | 73 | 2,3 % |
| ingen markör | 699 | 21,8 % |

Robotarna kommer från **79 tillverkare** och bär **2 175 distinkta
modellnamn**. De tio största: KUKA 380, Epson 180, ABB 177, Fanuc 173,
Mitsubishi Electric 158, Kawasaki 108, Denso 98, Comau 86, Stäubli 80,
Nachi 79.

Att robotarna är rätt klass att börja med bekräftas av deras egen täckning:
**2 196 av 2 202** deklarerar `MaxPayload` i katalogposten, och bara 54 av dem
har värdet 0. Talen finns. Enheterna gör det inte.

## Mekanismen: en enhet får bara komma ur ett citat

Varje hämtad uppgift bär tre saker — värdet, enheten och varifrån den kom — och
`Kalla` faller i konstruktorn på url, hämtdatum, sha256 eller citat som saknas.
Ett datablad utan källa är ett påstående.

Enhetsgrinden sitter i `Uppgift.__post_init__` och har **två lägen**:

**Ordagrant par.** Talet och enheten ska stå bredvid varandra i citatet.
`MaxPayload: 180` går inte att göra till `180 kg` genom att skriva dit `kg` —
citatet måste självt säga `180 kg`. ABB skriver `IRB 1200-5/0.9 901mm 5kg`, och
den raden bär sin egen enhet.

**Positionsläst kolumn.** Halva materialet skriver i stället en tabell där
enheten står i **rubriken**:

```
Robot variant       Handling capacity (kg)   Reach (m)
IRB 2600-20/1.65    20                       1.65
```

Enheten *står* i dokumentet — ABB har sagt kg. Det som är härlett är
*kopplingen*, via kolumnposition. Det är en svagare läsning, den kan läsa fel
kolumn, och den är därför ett eget läge med en egen grind: rubriken och raden
ska båda stå ordagrant i citatet, raden ska börja med modellnamnet (som stryks
innan talen räknas, för modellnamnet bär siffror), enheten på plats *i* bland
rubrikens parentesenheter ska vara vår, och talet på plats *i* bland radens tal
ska vara vårt. Varje svar skriver ut vilket läge det kom ur.

**Grinden fällde två fel i sin egen kod innan korpusen var byggd.**
`_talmonster` matchade inte `2.80 m` för värdet 2,8 — efterföljande nollor är
skrivsätt, inte precision, och ABB skriver både `2.00` och `3.15` i samma
tabell. Och utan vänsterspärr matchade `901 mm` inne i `1901 mm`, alltså ett
tal som inte står i texten. Båda står nu som fixturer i den gröna sviten.

## Korpusen: 28 modeller, 52 belagda uppgifter

Tolv dokument hämtade en gång från fem tillverkare, cachade under sin sha256.
Varje uppgift bär url, hämtdatum, sha256, ett ordagrant citat och ett utdrag på
±180 tecken.

| tillverkare | modeller | dokument |
|---|---|---|
| ABB | 19 | IRB 1200, 2600, 4600, 6700, 660, 360, 910SC |
| FANUC | 3 | LR Mate 200iD/7L, M-10iD/12, M-710iC/50 |
| Universal Robots | 3 | UR5e, UR10e, UR16e |
| KUKA | 2 | (inget dokument gick att nå) |
| Yaskawa | 1 | GP7/GP8 |

Grinden körs om **varje gång korpusen läses**: `Uppgift.fran_json` kör samma
`__post_init__`. En korpuspost som inte klarar enhetsgrinden går inte att läsa
in, bara att skriva.

## Svaret på frågan, tre tal

Svepet över alla 3 201 komponenter, 16,6 s med fyra processer:

| | `finns` | `enhet_saknas` | `saknas` |
|---|---|---|---|
| **nyttolast**, hela biblioteket | **21** | **2 965** | 215 |
| **räckvidd**, hela biblioteket | **19** | **2 542** | 640 |
| nyttolast, bara robotar (2 202) | 21 | 2 175 | 6 |
| räckvidd, bara robotar | 19 | 1 765 | 418 |

**21 komponenter av 3 201 fick en enhet med källa. 2 965 står kvar som
`enhet_saknas`.** Det är 0,66 procent, och talet ska stå så: mekanismen är
byggd och gör exakt vad den ska på de 28 modeller korpusen bär, men
*biblioteket är inte berikat*. Skillnaden mellan "mekanismen finns" och
"biblioteket är berikat" är två storleksordningar, och den skillnaden är ett
motbevis (nedan), inte en fotnot.

De 21: IRB 1200-5/0.9, 1200-7/0.7, 2600-12/1.65, 2600-12/1.85, 2600-20/1.65,
2600ID-15/1.85, 2600ID-8/2.0, 360-1/1600, 360-3/1130, 4600-20/2.50,
4600-40/2.55, 4600-45/2.05, 4600-60/2.05, 6700-150/3.20, 6700-205/2.80,
6700-235/2.65, LR Mate 200iD/7L, M-10iD/12, UR5e, UR10e, UR16e.

## Nollan: 628 komponenter, och ingen av dem påstår en nyttolast

`MaxPayload = 0` i **628** komponenter. Alla 628 svarar med `ENHET SAKNAS` och
orden *"ett ofyllt fält"*. **Noll** av dem skriver `0 kg`.

Ett tal M-85 inte hade: `Reach = 0` står i **1 115** komponenter — nästan dubbelt
så många. Noll av dem skriver `0 mm`.

Läget `enhet_saknas` bär **inget talvärde alls**, bara strängen `ordagrant`.
Det är avsiktligt: en float hade varit en märkning man kan glömma, medan ett
`Svar` utan tal inte går att räkna på av misstag. `svar.varde` är `None`,
`svar.jamforbar` är `False`, och `rymmer()` avstår med orden *"ett tal utan
enhet som jämförs med ett tal med enhet är ett fel som ser ut som ett svar"*.

## Fyndet: VC:s katalogfält och tillverkaren säger olika tal om samma robot

För de 25 komponenter som har ett datablad går de två källorna att ställa
bredvid varandra — och sex fält skiljer sig:

| komponent | fält | `model.xml` | tillverkarens datablad |
|---|---|---|---|
| UR10e | nyttolast | `12` | **12,5 kg** (Universal Robots) |
| IRB 1200-5/0.9 | räckvidd | `0` | **901 mm** (ABB) |
| IRB 1200-7/0.7 | räckvidd | `0` | **703 mm** (ABB) |
| IRB 2600ID-8/2.0 | räckvidd | `0` | **2,00 m** (ABB) |
| IRB 4600-20/2.50 | räckvidd | `2500` | **2,51 m** (ABB) |
| IRB 6700-235/2.65 | räckvidd | `0` | **2,65 m** (ABB) |

Fyra av dem är nollor som står där ett riktigt tal finns publicerat. UR10e är
skarpast: VC skriver 12 där tillverkaren skriver 12,5 kg, och en cell som
väljer robot efter last räknar då med ett halvt kilo för lite. Berikningen
låter tillverkarens tal vinna och **säger ingenting om motsägelsen** — det är
ett av de fem motbevisen.

Notera också vad tabellen INTE är: en jämförelse. Vänsterkolumnen är ett tal
utan enhet. Raden säger vad de två *skriver*, inte att de är jämförda.

## Bankens stämpel lovade en källa den inte bar

Bankens `katalog_index.json` har 15 robotposter med stämpeln
`PUBLICERAD_SPEC`, definierad som *"räckvidd, nyttolast och mått kommer ur
tillverkarens publicerade datablad för den namngivna modellen"*. **Ingen av dem
bär en URL eller ett hämtdatum.**

Ställda mot en citerad källa:

* **9 poster: samma tal i båda fälten.** IRB 1200-5/0.9, 1200-7/0.7,
  2600-20/1.65, 4600-60/2.05, 660-180/3.15, M-10iD/12, LR Mate 200iD/7L,
  UR10e, MOTOMAN GP8. Banken hade rätt — den kunde bara inte visa det.
* **IRB 6700-235/2.65: banken skriver 2 655 mm, ABB:s blad skriver 2,65 m.**
  Fem millimeter. Vilket som är rätt avgörs inte här; det som är mätt är att
  bankens tal inte står i den källa som går att nå.
* **IRB 360-1/1130: banken skriver 565 mm räckvidd.** ABB publicerar 1 130 mm
  under rubriken **Diameter**, inte Reach. 565 är 1130/2 — en **räkning** på ett
  publicerat tal, stämplad som ett publicerat tal. Korpusen bär därför
  `diameter: 1130 mm` som ett eget fält och `rackvidd: ej belagt`.
* **4 poster utan någon källa alls** (nedan).

## Vad som inte gick att belägga, och varför

`ej_belagda` är mätningens andra hälft. Ett fält som varken är belagt eller
förklarat är en lucka som ser ut som ett svar, och den gröna sviten har ett
prov som kräver att varje fält på varje modell är antingen belagt eller
försett med ett skäl.

| fält | belagt på | ej belagt på |
|---|---|---|
| nyttolast | 24 av 28 | 4 |
| räckvidd | 21 av 28 | 7 |
| repeterbarhet | 4 av 28 | 24 |
| diameter | 3 av 28 | 25 |
| **vikt** | **0 av 28** | 28 |

**Fyra modeller fick inte en enda belagd uppgift**, av tre olika skäl:

1. **KUKA KR 10 R1100 sixx** och **KR 210 R2700 extra** — tillverkaren har
   tagit bort båda generationerna ur sitt publika dokumentindex.
   Nedladdningscentralens API ger `totalResults: 0` för `extra`; för `sixx`
   finns tre datablad markerade `public: false` bakom en inloggning på
   `xpert.kuka.com`. Produktsidorna listar bara `-2`-generationen, som har
   2 701 mm mot extra-variantens 2 696 — alltså **inte utbytbara**. Att låna
   grannens tal vore precis det förbudet gäller.
2. **FANUC M-710iC/50** — dokumentet finns och talen står där, men
   textutdragningen flätar samman två stycken: raden lyder ordagrant
   `Max. load capacity Fig. 3.2at(a)wrist: to (e) 50 show kg the robot
   operating`, och räckvidden `Max. reach: 2050 mmspace. When installing`.
   Ett öga ser 50 kg och 2 050 mm. Grinden kan inte verifiera det, och då
   skrivs det inte.
3. **ABB IRB 910SC-3/0.55** — den enda posten där dokumentet finns, tabellen
   finns, och kolumngrinden ändå säger nej. Rubriken
   `Robot version Reach Payload (kg)*` bär **en** parentesenhet (kg) på plats 0,
   medan radens tal på plats 0 är räckvidden 0,55. ABB skriver ingen enhet vid
   *Reach*. Källan säger dessutom `Rated: 3, Max: 6` — två tal, och vilket VC:s
   `MaxPayload 3.0` avser går inte att läsa här.

**Vikt gick inte att belägga på en enda modell.** Alla fem tillverkarna anger
den som ett familjeintervall (`Peso robot da 412 a 435 kg`, `Weight 1250 - 1280
kg`) eller i en kolumn som utdragningen blandar med grannkolumnen. Ett
intervall över en familj är inte modellens vikt.

## Fail-closed, mätt och inte påstått

Under bygget svarade `https://www.abb.com/.../scara-robots/irb-910sc` med HTTP
404 och `library.e.abb.com`-URL:er med `?x-sign=` med 403. Båda **kastade** —
`hamta()` skriver ingen post och lämnar inget tomt fält efter sig. Utan den
regeln hade fältet tyst blivit `saknas` och berikningen sett ut att ha kört.
Samma sak för korpusen: en katalog som inte finns, en fil som inte går att
tolka eller en post som bryter mot enhetsgrinden är ett undantag, aldrig en tom
korpus.

Artighet mot andras servrar: 12 dokument hämtade, 22 MB, en gång var. Cachen
ligger i `data/tillverkardatablad/cache/` och är gitignorerad; de två första
grindlagren (talet bredvid enheten i citatet, citatet i utdraget) kör utan både
nät och cache, det tredje (utdraget i dokumentet, sha256 stämmer) kör i
byggskriptet.

## Fem motbevis, och de är röda

`tests/motbevis/test_tillverkardatablad_motbevis.py`:

1. **Enhetsgrinden mäter närhet, inte betydelse.** `IRB 360-1/1130 * 1 kg
   1130 mm` går att citera som en räckvidd fastän raden står under rubriken
   *Diameter*. I korpusen är fältet handsatt som ej belagt med just det skälet
   — ett omdöme i en tabell, inte en grind.
2. **`katalogsok.Traff.rad` fäster `mm` och `kg` vid samma enhetslösa
   katalogfält** och skriver `0 kg` för de 628 nollorna. Det är sökskiktet
   modellen faktiskt läser. En grind i det nya lagret skyddar inte det gamla.
3. **Bankens 15 `PUBLICERAD_SPEC`-poster bär ingen URL.**
4. **Täckningen: 2 965 komponenter står kvar utan enhet**, 4 av bankens 15
   robotar har ingen källa alls.
5. **En motsägelse mellan VC:s katalogfält och den citerade källan passerar
   tyst** — sex fält, uppräknade ovan.

## LIMITS

* **Korpusen täcker 28 modeller av bibliotekets 2 175 distinkta robotnamn**
  (1,3 %) och ger `finns` för 21 komponenter av 3 201 (0,66 %). Allt annat i
  det här dokumentet gäller den mekanism som bär de 28. Att kalla biblioteket
  berikat vore att mäta fel sak.
* **Enhetsgrinden kontrollerar att talet och enheten står bredvid varandra,
  inte att citatet svarar på rätt fråga.** En diameter går att citera som en
  räckvidd. Att det inte har hänt i den levererade korpusen är ett omdöme jag
  har fattat post för post, och det är inte samma sak som en grind.
* **Kolumnläsningen är positionell och därmed svagare än ett ordagrant par.**
  Fem av 52 uppgifter (alla IRB 2600) vilar på att rubrikens andra
  parentesenhet hör till radens andra tal. Grinden kontrollerar räkningen, inte
  att ABB:s tabell är uppställd som jag läser den. Varje sådant svar skriver ut
  `positionslast kolumn`.
* **Talen är läsningar av ETT dokument per modell, ofta ett säljblad.** ABB:s
  produktspecifikationer (3HAC-serien) är utförligare men ligger bakom
  signerade URL:er som ger 403; de två som gick att nå utan signatur användes.
  Ett annat dokument från samma tillverkare kan ha ett annat tal — IRB
  6700-235:s 2,65 m mot bankens 2 655 mm är förmodligen precis det.
* **Ingen käll-URL kontrolleras mot nätet efter hämtningen.** Ett datablad som
  revideras eller flyttas märks inte förrän `kor_m107_bygg_korpus.py` körs om,
  och korpusen bär inget utgångsdatum.
* **Den tredje grinden (utdraget står i dokumentet) kräver cachen**, som med
  flit inte ligger i repot. `verifiera(kraev_cache=False)` hoppar över den
  posten i stället för att fälla, och det betyder att en `git clone` inte kan
  köra hela kedjan utan att hämta om.
* **Enhetstabellen är kort med flit** (kg/g, mm/cm/m). En tumenhet i citatet —
  `12.5 kg (27.6 lbs)` — lagras aldrig, för omvandlingen är en räkning på ett
  tal och den hör inte hemma i källskiktet.
* **`nyttolast_kg` och `rackvidd_mm` heter fortfarande så**, i
  `komponentdatablad.py`, `katalogindex.py`, `katalogsok.py` och `datablad.py`.
  Ett variabelnamn som påstår en enhet källan aldrig deklarerade är samma
  felklass som ett utskrivet `0 kg`, bara svårare att se. M-107 lägger till
  `katalogfalt` med de ordagranna strängarna bredvid dem; den byter inte namn
  på någonting.
* **Ingen komponent har laddats i VC.** Att ABB publicerar 901 mm säger
  ingenting om vad VC:s modell av samma robot faktiskt når i simuleringen.
  Databladets tal är ett **tak för modellen**, aldrig ett driftvärde för
  instansen: två robotar av samma typ med olika verktyg har olika nyttolast
  kvar, och verktygets vikt är inte avräknad någonstans i det här lagret.
  `Domslut.text()` skriver ut den raden varje gång, och funktionen heter
  `rymmer()` och inte `racker()`.
* **Täckningstalen gäller ETT bibliotek** — VC 4.10:s eCatalog på den här
  maskinen, 3 201 komponenter. En annan installation med andra
  tillverkarpaket ger andra andelar.
