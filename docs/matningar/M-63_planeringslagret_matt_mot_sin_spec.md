# M-63 — planeringslagret mätt mot sin egen spec

**Datum:** 2026-09-04/05 · körs utan VC · fas 16 i `docs/spec/70_faser.md`
**Mäter:** `docs/spec/22_planeringslagret.md` (384 rader) mot
`svc/vc_assist_svc/plan/` (3 868 rader före, 7 847 efter)
**Stänger:** fas 16. Protokollet står i
`tests/protocol/fas16_planeringslagret.md`, proven i
`tests/enhet/test_bestallning.py`.
**Kör om mätningen:** `python3 tests/protocol/kor_m63_specglapp.py`

---

## 1. Talet först

Specen namnger sina egna krav: **30 kravkoder** (`K0`–`K29`), **8 grindar**
(`P1`–`P8`) och **12 felklasser** (`PL1`–`PL12`). Frågan var enkel att ställa:
hur många av dem nämns över huvud taget i koden eller i proven?

| | I specen | Nämndes i kod eller prov (före) |
|---|---:|---:|
| kravkoder `K` | 30 | **0** |
| felklasser `PL` | 12 | **0** |
| grindar `P` | 8 | **8** |

De åtta gröna var **falska**. `svc/vc_assist_svc/plan/byggplan.py` har en egen
lintkodlista som råkar heta `P1`–`P10`, och den betyder något helt annat:

| Kodens `P`-kod | Specens `P`-kod |
|---|---|
| `P1_OKANT_VERKTYG` | P1 Specfullständighet |
| `P2_ARGUMENTFEL` | P2 Specformslint |
| `P3_ROUTING_I_PLANEN` | P3 Katalogförankring |
| `P4_AVSTANGT_VERKTYG` | P4 Layoutdom, statisk |
| `P5_BINDNING` | P5 Layoutdom, mätt |
| `P6_INGEN_VERIFIERING` | P6 Plangraf |
| `P7_OBESVARAD_FRAGA` | P7 Efterkontrollstäckning |
| `P8_TOM_PLAN` | P8 Planens dom |

Åtta av åtta träffar, noll av åtta betydelser. Det är specens **egen** felklass
`PL11` — *"två halvor av samma begrepp som inte möts"* — och den fanns i vårt
eget planeringslager, i samma paket som beskrev regeln.

Efter det här arbetet: **14 av 30 kravkoder** och **4 av 12 felklasser** nämns i
kod eller prov. Talet är fortfarande lågt, och det ska det vara: en kod ska
skrivas in i koden när kravet faktiskt är mekaniserat, inte som en etikett.

## 2. Den finare mätningen: krav för krav

Grep säger bara om ett namn nämns. Den här tabellen är läst, inte räknad, och
varje rad pekar på fil och funktion.

| | Före | Efter |
|---|---:|---:|
| **uppfyllt** | 9 | **24** |
| **delvis** | 8 | 4 |
| **saknas** | 13 | 1 |
| ej tillämpligt | 0 | 1 |

### 2.1 Det som redan fanns, och som är bra

| Krav | Var |
|---|---|
| `K3` mjuka slots bär förval med motiv | `spec.Antagande` — motivet är ett formkrav, inte en artighet |
| `K14` `connect` tar aldrig koordinater | `spec.Koppling` har två fält och avvisar varje annan nyckel |
| `K15` beroenden är explicita | `graf.Uppgiftsgraf`, `G3_LASNING_UTAN_BEROENDE` |
| `K18` grafen är acyklisk | Tarjan, iterativt, med medlemmarna i felet |
| `K19` okänt verktyg är hårt fel | `byggplan.P1_OKANT_VERKTYG` |
| `K20` sekvensen härleds mekaniskt | Kahn med minsta id som kanoniskt val |
| `K21` `effect=write` går i kön | planen bär inget fält för läget, och läsningen avvisar nycklarna |
| `K24` planens facit är ögats sektioner | `verifiering.Krav` mot `bank/schema.py` |
| `K25` grinden parsar ögats utdata | `Verifieringskrav.doma` genom `oga_kontrakt.las` |

Det här är gediget arbete, och det är skälet till att resten gick att bygga på
en kväll i stället för på en vecka.

### 2.2 De sex hålen som gjorde lagret obrukbart

**H1. Villkorsspråket var prosa, och ingen läste det.**
`spec.Villkor` bar `(id, sort, text)` där `text` var meningar som
`"hogst 0 kollisioner i cellen"`. **Mätt: noll rader kod i hela repot läste
`Villkor.text`.** Fältet skrevs av `forfining._villkor_ur_bank` och lästes
aldrig. Det är felklassen `PL5` — efterkontroll utan konsument — som specen
skrev in efter att ha hittat den i *källprojektet*. Vi hade den själva.

**H2. Layoutporten hade ingen motor.**
`layoutport.py` beskrev ett kontrakt på 194 rader. **Mätt: den enda
implementationen i hela repot var en teststubb i `tests/enhet/test_plan.py`.**
Planeringslagret satte därför aldrig en enda koordinat, medan
`svc/vc_assist_svc/layout/` samtidigt bar 4 359 rader färdig lösare med rum,
kollision, relationer och fyra domar. Två halvor som inte möttes, igen.

**H3. Ingen härkomst på ett krav.**
Specen har `Antagande` med motiv, och förfiningen har regeln att allt som inte
står i begäran går genom `anta()` eller `fraga()`. Men **ett villkor i specen
bar inget fält som sa vilken av de två vägarna det kom in genom.** Ett uppfunnet
krav såg därför exakt likadant ut som ett krav operatören faktiskt ställde. Det
är den tysta nedgradering hela projektet är byggt för att undvika, och den satt
i det lager som skulle förhindra den.

**H4. Ingen processordning.**
Operatörens ord är *"villkor och ordning av processer"*. `graf.py` ordnar
**verktygsanropen**. Ordningen av processerna i cellen — mata in, spänna,
plocka, mata ut — fanns ingenstans. Den överlever bygget, den är det styrkoden
ska genomföra, och den var inte modellerad.

**H5. Ingen motsägelsegrind.**
Det fanns ingen kod som kunde svara på frågan *"kan de här kraven gälla
samtidigt?"*. En beställning som motsade sig själv blev en plan.

**H6. Ingen väg från fri text till ett krav.**
`forfining.ur_fritext` läste komponenter, mått och takt. Cellens yta,
gångstråket, räckvidden, relationerna och processordningen lästes inte alls —
de fanns inte som begrepp.

### 2.3 Vad som fortfarande saknas efter det här arbetet

| Krav | Vad som saknas | Varför det inte gjordes nu |
|---|---|---|
| `K10` | taket på fyra rättningsvarv | lösaren har i stället en **mätt** nodbudget och en rasterstege; se §5 och förslag F4 |

Fyra är delvis: `K11` (gångstråket är ett hårt slot och mäts av lösarens
`kollision.separation` — men inte ännu i en byggd VC-scen), `K12`
(`work_area` skrivs ut som `UNKNOWN` i layoutartefakten, men zonen som osynlig
kropp kräver celldatabladet, fas 4b), `K13` (kollisionsdomen är hård statiskt;
`collision_count` i VC kräver VC) och `K26` (grindordningen ÄR
`REJECT_FIX`-doktrinen — bygg aldrig en geometri som redan är fälld — men de
fyra namngivna routningslägena är inte modellerade).

`K27` (`SKIP_GATE` avstängd) är **ej tillämpligt**: det finns inget hopp att
stänga av, eftersom ingen grind hoppas över.

### 2.3.1 De två som stängdes sist, och som var specens egna huvudpunkter

**`K16` och `P7` — efterkontrollerna.** Specen skriver själv att källans
`post_condition` har *"noll konsumenter i hela repot"* och kallar det
*"den viktigaste luckan att stänga"*. `steg.Efterkontroll` är nu
`{verktyg, argument, vag, operator, forvantat}`: verktyget måste finnas och
vara **läsande** (`EK3`), vägen måste finnas i verktygets returns (`EK2`),
jämförelsen görs av `predikat.py` — samma kod som förvillkoren — och det
förväntade värdet får **aldrig** vara en bindning, för ett facit som räknas
fram ur körningen är inget facit (`EK4`, och det är källans
`L-SC-01_REJECT_SELF_REF`). Planeraren skriver dem själv:
`find_component` efter `load_component`, `get_transform` efter `set_transform`,
`interface_info` efter `connect`. **8 av 8 skrivande steg** i den planen har nu
en efterkontroll som kan falla.

**`K1` och `S1` — varje fråga säger vad den behövs till.** Frågorna är de tomma
slotsen i praktiken, och `BEHOVS_FOR` är en sluten tabell som binder varje
fråge-id till den grind eller det lösarsteg som inte kan köras utan svaret.
En fråga vars id ingen rad täcker är ett fel i **vår** kod — någon har lagt
till ett slot utan att säga vad det behövs till — och den fälls med
`S1_SLOT_UTAN_BEHOV` innan beställningen ens når operatören. Svepet i provet
går över hela banken och över sju fritextbeställningar, så en ny fråga utan
rad upptäcks där och inte hos honom.

**Artefakterna på disk.** *"Alla fyra är JSON på disk under
`bank/plans/<plan_id>/`"* — ingen av dem skrevs. `artefakter.py` skriver alla
fyra, och anropssekvensen bär en sha256 över sin egen kanoniska JSON. Tre
körningar av samma beställning ger **en** hash (`K22`), och `las_sekvens`
vägrar lämna ut en artefakt vars innehåll inte stämmer med hashen. Det stänger
också `K9`: varje tal i layoutartefakten bär `{value, method, gate}`, där
grinden är lösarens **egen oberoende** efterhandsgranskning.

### 2.4 Grindarna P1–P8, som de faktiskt står

| Grind | Läge | Vad som gjordes |
|---|---|---|
| P1 Specfullständighet | **grön** | blockerande frågor stoppar planen, och `fragerunda` bärs i artefakten med taket två |
| P2 Specformslint | **grön** | `VS1`–`VS7` mekaniserar S2, och `S1_SLOT_UTAN_BEHOV` mekaniserar S1: varje fråga säger vilken grind som inte kan köras utan svaret |
| P3 Katalogförankring | delvis | URI:er kommer ur indexet eller blir en fråga; databladet som artefakt saknas |
| P4 Layoutdom, statisk | **grön** | `layoutmotor.py` → `layout/losare.losa`, fail-closed |
| P5 Layoutdom, mätt i VC | saknas | kräver VC; hör till fas 5a |
| P6 Plangraf | **grön** | graf + register + determinism över tre körningar, med hashen i artefakten |
| P7 Efterkontrollstäckning | **grön** för de planer planeraren skriver | 8 av 8 skrivande steg har en post som kan falla; `EK1` fäller den som saknar |
| P8 Planens dom | saknas | kräver VC och ögat |

### 2.5 Felklasserna PL1–PL12

Nio av tolv fälls nu mekaniskt: `PL1` (tyst förval), `PL2` (uppfunnen URI
eller uppfunnet verktygsnamn), `PL3` (prosavillkor), `PL4` (efterkontroll som
inte kan falla — `EK4`), `PL5` (efterkontroll utan konsument), `PL6` (implicit
ordning), `PL7` (överlapp som byggdes ändå, statiskt), `PL9` (kontroll som
svarade `pass` utan sitt argument), `PL12` (koordinat i en koppling).

Tre är delvis: `PL8` (klassen läses ur katalogposten — men i **grunt** läge
kommer kategorin från katalognamnet, M-58), `PL10` (gångstråket mäts av
lösarens `kollision.separation`, inte ännu i VC) och `PL11` (jag hittade en och
lämnade den, se §7).

Ingen är kvar helt ofångad.

---

## 3. Vad som byggdes

Tio nya moduler i `svc/vc_assist_svc/plan/`, 3 221 rader, plus ändringar i sju
gamla (`steg.py` fick `Efterkontroll`, `byggplan.py` fyra `EK`-lintkoder,
`planering.py` skriver posterna, `forfining.py` läser fri text och tar emot
svar).

| Modul | Rader | Vad den gör |
|---|---:|---|
| `harkomst.py` | 194 | var ett krav kom ifrån, i en form som går att slå upp |
| `storheter.py` | 326 | den slutna listan av storheter ett villkor får handla om |
| `villkorssprak.py` | 379 | `Typvillkor`, `Relation`, `Prosakrav` med namngiven konsument |
| `processer.py` | 287 | processordningen, med samma cykelkrav som uppgiftsgrafen |
| `motsagelse.py` | 449 | fyra domar, och ingen av dem heter `MOJLIG` |
| `lasning.py` | 442 | fri text → krav, varje värde med sin ordagranna textbit |
| `layoutmotor.py` | 487 | adaptern till den lösare som redan fanns |
| `bestallning.py` | 290 | sju grindar i ordning; ett nej lämnar aldrig ut en plan |
| `artefakter.py` | 202 | de fyra artefakterna på disk, och hashen som binder sekvensen |
| `ordning.py` | 165 | cykler och kanonisk ordning, delad av graf och processer |

`tests/enhet/test_bestallning.py` (**180 prov**), nio nya prov i
`tests/enhet/test_plan.py` för efterkontrollerna, och
`tests/protocol/fas16_planeringslagret.md`.

### 3.1 Härkomsten är den bärande nyheten

Varje krav i en spec bär nu `Harkomst(kalla, belagg)`, och listan över källor är
sluten. **Det finns ingen källa som betyder "vi tyckte så".** Vill planeringen
välja ett värde åt operatören måste den skriva ett `Antagande` med motiv och
peka på det.

Den skarpaste kontrollen är `HK2_FALSK_BEGARAN`: ett krav som säger sig komma ur
begäran prövas med en **delsträngsmatchning på normaliserad text** mot
operatörens ord. Ett krav vi hittat på faller där. Kontrollen är mekanisk — inte
en modell som bedömer sig själv, vilket vore samma fel som `I11` förbjuder.

### 3.2 Två motsägelsegrindar, inte en

| | Symbolisk (`motsagelse.py`) | Geometrisk (`layoutmotor.py`) |
|---|---|---|
| svarar | **bevisar** omöjlighet | **lokaliserar** konflikten |
| kostar | mikrosekunder | upp till 4 s |
| ger | de två villkoren, med operatörens ord | en **minimal** mängd bindande relationer |
| gäller | alltid | det raster som söktes |

De ersätter inte varandra, och ordningen är inte kosmetisk. Se §5.

---

## 4. Räckvidden: samma fråga, två svar, och skillnaden är filen

Uppgiften pekade ut ett fall: *"Roboten ska nå både bandet och pallplatsen"*
plus *"cellen får vara högst 2×2 meter"* kan vara omöjligt, **och det avgörs av
robotens räckvidd**. Alltså mätte jag om räckvidden går att slå upp.

**Första mätningen, över hela biblioteket (3 201 komponenter, 8,1 s):**

```
robotar med ett reach-fält i component.rsc:     0 av 2169
komponenter med payload-fält:                   2 av 3201
komponenter med något dimensionsfält:        1 746 av 3201
robotnamn med ABB:s -<nyttolast>/<räckvidd>:  142 av 2169  (ABB 128, ROKAE 14)
```

Slutsatsen såg färdig ut: räckvidden finns inte, den måste komma ur begäran.

**Den slutsatsen var fel.** `component.rsc` är vad `katalogindex.py` läser.
Arkivet bär också `model.xml`, och `svc/vc_assist_svc/komponentfil.py` läser
`Reach` där:

```
robotar med Reach i model.xml:              1 434 av 2169   (66 %)
```

Samma fråga, samma 3 201 filer, **0 % eller 66 % beroende på vilken post i
zip-arkivet man öppnar.** Det är tredje gången i det här bygget som ett tal som
inte rörde sig visade sig vara ett bevis på att man tittade på fel ställe —
`M-34` (produkten fanns men flödade inte), `M-57` (biblioteket fanns hela
tiden), och nu den här. Jag fångade den på mig själv först när jag såg en annan
agents `layout/komponent.py` läsa fältet jag just skrivit att det inte fanns.

**Vad det betyder för koden:** ett datablad byggt ur `katalogindex.py` saknar
räckvidden; ett byggt ur `komponentfil.py` har den för två tredjedelar av
robotarna. `storheter.Faktarum` svarar därför `OKANT` **med båda talen i
skälet**, så att nästa läsare inte behöver göra om mätningen.

---

## 5. Rasterstegen: ett grovt raster kan ge ett falskt nej

Layoutlösaren söker i ett **raster** av lägen, inte i planet. Rasterstorleken är
en parameter, och den påverkar svaret — inte bara kostnaden. Jag svepte
81 körningar: 3 hallstorlekar × 3 räckvidder × 2–4 objekt × 3 raster.

**Fynd 1 — ett grovt raster gav den starkaste avvisningen, felaktigt.**

| Scen | 1000 mm | 500 mm | 250 mm |
|---|---|---|---|
| 3×3 m, 4 objekt, räckvidd 1650 | `RYMS_INTE` | `OVERBESTAMD` | **`LOST`** |

`RYMS_INTE` betyder *"objekten får inte plats i hallen ens utan en enda
relation"*. Det lät absolut, och det var fel: med finare steg fanns en lösning.

**Fynd 2 — ett fint raster gav ett sämre svar än ett grovt.**

| Scen | 1000 mm | 500 mm | 250 mm |
|---|---|---|---|
| 6×6 m, 4 objekt, räckvidd 2600 | `LOST` | `LOST` | `OBESTAMBART` |

Vid 250 mm tog nodbudgeten slut innan lägesutrymmet var genomsökt.

**Åtgärden:** `RASTERSTEGE_MM = (1000, 500, 250)`, grovt först. En **lösning**
som hittas står sig oavsett raster — lösaren granskar den med en oberoende
efterhandskontroll innan den kallas `LOST`. Ett **nej** provas om med finare
steg innan det lämnas ut, och det raster svaret gäller skrivs alltid ut.

Med stegen blir 3×3 m-scenen ovan `LOST` på 1,4 s i stället för ett falskt
`RYMS_INTE`.

## 6. Den billiga grinden slår den dyra, och ger ett bättre svar

Beställningen *"cellen får vara högst 2×2 meter"* med band, robot och pall:

| Grind | Svar | Kostnad |
|---|---|---|
| symboliskt ytbevis (`MK3_YTA`) | **`OMOJLIG`**, med de tre fotavtrycken och talen | mikrosekunder |
| layoutlösaren, 250 mm raster | `OBESTAMBART` — budgeten tog slut | 40 000 noder, 0,64 s |

Ytbeviset är en geometrisk nödvändighet: disjunkta ytor i en ruta kan inte
summera till mer än rutans yta. Bryts den finns **ingen** layout — inte "hittade
ingen". Att ställa den grinden före sökningen är alltså inte en optimering utan
ett sannare svar.

Det omvända gäller också, och står i protokollet: håller de härledda villkoren
säger de **ingenting** om huruvida en layout finns.

## 6.1 Hela banken genom grindkedjan: är grindarna för trånga?

En handplockad fixtur kan visa att en grind **faller**. Den kan inte visa att
grinden faller på **rätt** saker. Därför kördes alla 51 uppgifter i
`bank/uppgifter/` genom samma sju grindar.

| | Utan URI-karta | Med URI-karta |
|---|---:|---:|
| `BYGGBAR` | 0 | **46** |
| `OFULLSTANDIG` | 51 | 5 |
| `AVVISAD` | 0 | **0** |

Utan karta blir varje `bank://`-URI en blockerande fråga, och det är rätt svar:
vokabulären pekar inte på någon fil VC kan ladda, och en uppfunnen URI är ett
hårt fel (`I9`). Kartan finns för mätning och får aldrig köras.

De fem som inte blir byggbara är `A-90`, `P-90`, `S-90`, `S-91` och `T-90` — de
uppgifter banken själv fäller **före** ögat (grind 1–4). De bär därför ingen rad
ögat kan skriva, och en plan utan facit är en kandidat, aldrig en leverans. Det
är ett riktigt svar, inte en miss.

**Noll uppgifter föll på de tre nya grindarna** (härkomst, processordning,
motsägelse). Det är den mätning som visar att de inte är för trånga.

Vad banken gav grindarna att arbeta med:

```
typade villkor:                    176   (före: 0 — allt var prosa)
prosakrav med namngiven konsument: 125   (bankens förreglingar)
räckviddskrav:                      28   varav 28 med känt värde
mätta krav uppskjutna till efter bygget: 102  (2 per uppgift)
```

**Och en planterad läcka.** Uppgiften `A-01` är grön som den står. Höjs
`fysik.arbetsradie_mm` från 1 500 till 9 000 mm faller den:

```
BESKED AVVISAD · GRIND B3_MOTSAGELSE · MOTSAGELSE VALET_FALLER
MK2_VARDE_MOT_VILLKOR: del.robot.rackvidd_mm = 1650 mm (databladet for robot),
                       kravet var ge 9000 mm
    rackvidd: del.robot.rackvidd_mm ge 9000.0  [ur bank: A-01#fysik.arbetsradie_mm]
    atgard: kravet gar att uppfylla, men inte med den har komponenten.
            Byt komponent - eller mjuka upp kravet
```

Domen är `VALET_FALLER`, inte `OMOJLIG`, och det är hela poängen: en 9 000 mm
arbetsradie är fullt möjlig — bara inte med en IRB 2600. Botemedlet är en annan
robot, inte ett annat krav.

Samma kontroll finns sedan tidigare i `bank/schema.py` som lintkoden
`M23_ROBOT_KAPACITET`. Att två oberoende vägar ger samma svar på samma data är
ett svagt men äkta belägg för att ingen av dem räknar fel.

## 6.2 Att spela som operatören hittade fyra tysta bortfall

Alla proven var gröna. Sedan körde jag operatörens **egen** exempeltext ur
`27_operatorsflodet.md` genom lagret:

> *"Bygg en plockstation som klarar 400 detaljer i timmen, med ett
> inmatningsband, en robot och en utlastningslåda. Skriv PLC-koden."*

Svaret var `BESKED BYGGBAR` — med en plan på **tre steg och en komponent**.

**F1. Sammansatta ord kändes inte igen.** `_namner` matchade exakta tokens, så
`inmatningsband` var inte `band`. Ett sammansatt ord bestäms av sitt
**efterled**: ett inmatningsband är ett band. Prefix vore fel åt andra hållet,
och det stod redan i `ORDBOK`s egen kommentar — den hade läst `pallmagasin` som
`pall`. Båda riktningarna har nu en fixtur.

**F2. Ord som ingen kände igen försvann tyst.** `utlastningslåda` finns inte i
den slutna ordlistan, och den hoppades över utan ett ord. Nu läses
uppräkningen efter *"med"* för sig, och ett ord som ingen rad matchar blir en
**blockerande fråga**. Att bygga två tredjedelar av en cell är inte att bygga
den halvt; det är att bygga en annan cell.

**F3. Processorden matchades som delsträngar.** `inmatningsband` gav **både**
processen `inmatning` och processen `matning`. Beställningen fick två processer
den aldrig nämnde — och båda bar en härkomst som pekade rakt in i operatörens
text. **Belägget var äkta, tolkningen var påhittad.** Det är den obehagligaste
av de fyra, eftersom härkomstgrinden inte kan fånga den: orden *stod* där.
Ordgränser är grinden mot precis det.

**F4. Räckviddens hårda läsning gjorde nästan varje cell röd.**
`layout/relationer.py` säger själv att `InomRackvidd` har två läsningar:
`helt=True` (hela fotavtrycket inom radien — den hårda, och den enda som håller
när greppunkten inte är känd) och `helt=False` (någon del inom radien — rätt
för ett långt band där bara plockläget behöver nås). Jag valde den hårda, och
mätte sedan: en robot på 1 650 mm kan **inte** täcka ett 2 m långt band helt,
så varenda beställning med en transportör blev `AVVISAD`.

Ett falskt rött är den värsta sorten, för det ser ut som ett svar. Att i
stället tyst välja den mjuka läsningen vore lika fel: då lovar planen att
roboten når något den kanske inte når. Nu **räknas båda**, och skillnaden blir
en fråga med båda svaren i sig:

```
BESKED OFULLSTANDIG · GRIND B5_LAYOUT
INOM_RACKVIDD fixtur ligger helt inom robotens räckvidd från robot
FRAGA layout:rackviddens_lasning: ska roboten nå HELA robot -> fixtur, eller
      räcker det att den når en del av det?
      med den hårda läsningen finns ingen layout. Med den mjuka finns en
      (sökraster 1000 mm). Skillnaden är var greppunkten sitter, och det vet
      bara du.
```

Och statusen är `OFULLSTANDIG`, inte `AVVISAD`: **ingenting är bevisat
omöjligt — något är obestämt**, och det rättas av ett svar, inte av en ny
beställning.

Alla fyra hade passerat 141 gröna prov. Ingen av dem hade hittats av ett prov
till, eftersom jag skrev proven mot det jag byggt. Den enda som hittade dem var
att skriva som en människa skriver.

## 6.3 Samtalet: fråga, svar, plan

Efter §6.2:s rättelser gav operatörens exempeltext **två precisa frågor och
ingen plan**. Det är rätt svar, men utan ett sätt att **svara** är det en
återvändsgränd: han hade fått skriva om hela beställningen.

Mekaniken är en rad: `svar` är `{fraga_id: text}`, och svaren blir en del av
**begäran**, ordagrant. Det är hans ord lika mycket som den första meningen —
och det är också det enda som gör dem läsbara: samma mönster som läser
meningen läser svaret, och härkomsten pekar på text som faktiskt står där.

```
TUR 1  OFULLSTANDIG · B4_FRAGOR
       okant_ord:utlastningslada: vilken komponent i katalogen ar 'en utlastningslåda'?
       kopplingar: hur ska band, robot kopplas ihop med resten?

TUR 2  svar = {"okant_ord:utlastningslada": "en kassationslada",
               "kopplingar": "bandet matar roboten och roboten matar kassationsladan",
               "cellyta": "cellen ar 8x8 meter, gangstrak minst 800 mm"}
       BYGGBAR · 22 steg
```

**En fråga som ställs OM är en fråga som inte blev besvarad.** Löste svaret den
ställs den inte alls — den försvinner för att extraktorn hittade det den
behövde. Kommer den tillbaka gick svaret inte att läsa, och att då märka den
som besvarad hade gjort ett obrukbart svar till ett tyst ja. Regeln har ett eget
prov åt båda hållen.

`K4`s tak är två rundor, och `spec.fragerunda` bärs i artefakten. Källans
loopspärr läste den föregående turens **text** och matchade på en
svensk-engelsk fras (`orchestrator.py:783`); det ärvs inte.

## 6.4 Fasordningen sa att 14 skulle före 16. Höll skälet?

`70_faser.md` motiverar ordningen så här:

> **14 före 16.** Planeringslagret låter en språkmodell fatta fler beslut. Att
> utöka modellens frihet innan reglerna är mekaniserade är att lita på prosa i
> precis det läge där prosa är svagast.

Skälet är rätt i sak, men **lagret som det nu är byggt gör tvärtom**: det
innehåller ingen språkmodell alls. `bestall()` är deterministisk från text till
plan — samma beställning ger samma plan, byte för byte, och det är mätt
(`K22`). Det som förr var modellens omdöme är nu sju grindar.

Den fara fasordningen pekar på finns däremot kvar, och den har **flyttat**: den
dag en modell fyller specen i stället för `lasning.py` är det `Harkomst` som
avgör om den hittar på. `HK2_FALSK_BEGARAN` är precis den grinden — ett krav som
säger sig komma ur operatörens ord prövas mot orden, med en delsträngsmatchning
och inte med en bedömning. Den är byggd **för** en modell som ännu inte är
inkopplad, och den är den enda mekanism i lagret som fungerar lika bra oavsett
vem som skrev kravet.

Till saken hör också att `M-46`s tal har rört sig sedan det skrevs: korpusen i
`instruktioner/` bär i dag **37 `block` mot 9 `regel`** (mätt 2026-09-05, i en
annan agents arbete). Fas 14 är alltså närmare stängd än när fasordningen
skrevs.

## 7. En krock jag hittade och lämnade

Specens grindnamn `P1`–`P8` och `byggplan.LINTKODER`s `P1_`–`P8_` är två olika
namnrymder med åtta kolliderande namn (§1). Jag lämnade dem orörda, av två skäl:
att döpa om lintkoderna rör kod som fem andra agenter läser samtidigt, och
`docs/spec/` får jag inte skriva i. Förslaget står som **F1** nedan.

Mina egna koder har därför egna prefix: `HK` (härkomst), `VS`
(villkorsspråk), `MK` (motsägelse), `PO` (processordning), `B` (beställningens
grindkedja).

---

## 8. Förslag till `docs/spec/22_planeringslagret.md`

Jag får inte skriva i specen. Här är vad jag skulle ändra, med skäl.

**F1. Döp om grindarna eller lintkoderna.** Åtta namn betyder två saker. Ge
grindarna prefixet `PG` (planeringsgrind) eller lintkoderna `BP`
(byggplanslint). Detta är specens egen `PL11`.

**F2. K6 kan inte uttrycka en förregling.** Bankens 51 uppgifter bär
**125 förreglingar** av formen *"ingen robotrörelse när `EMG_OK` är låg"*
(98 unika). Det är ett **villkorat förbud**, inte en jämförelse, och trippeln
`{lhs, op, rhs}` kan inte bära det. Att tvinga in dem hade gett falska triplar;
att kasta dem hade tappat krav. De bärs nu som `Prosakrav` med en **namngiven
konsument** (grind 3 och ST-lagret). Specen bör antingen ta upp den formen eller
utvidga K6 med `{nar: villkor, forbjudet: handling}`.

**F3. Relationslistan saknar räckvidd.** Fas 16:s egen uppgift namnger *"roboten
ska nå både bandet och pallplatsen"* som sitt exempel, och §2:s relationslista
(`on_top_of` … `sequence`) har ingen sort för det. Vi lade till `nar`, som
översätts till `layout.relationer.InomRackvidd`.

**F4. K10:s "fyra varv" bör ersättas av det som faktiskt mäter.** Taket är
märkt `PRELIMINÄR`. Lösaren har i stället en **mätt** nodbudget
(`NODBUDGET = 40000`, mätt över 24 provscener) och nu en mätt rasterstege. Fyra
varv är ett tal utan mekanism i den lösare vi faktiskt har.

**F5. Skilj `OKANT` i två.** En storhet kan vara okänd för att datan saknas
(`del.robot.rackvidd_mm`) eller för att **scenen inte är byggd än**
(`scen.kollisioner`). Den första ska blockera, den andra ska bli planens
verifiering. Blandas de ihop blir varenda beställning okänd, och en grind som
alltid säger okänt har slutat mäta. Koden gör skillnaden;
`storheter.STATISK/MATT/DOM` är fälten.

**F6. Skriv in `VALET_FALLER` som en egen dom.** Skillnaden mellan *"kraven kan
inte gälla samtidigt"* och *"kraven går, men inte med den här komponenten"* är
**botemedlet**. Den ena rättas genom att ändra ett krav, den andra genom att
byta komponent. Ett svar som inte skiljer dem lämnar operatören att gissa.

**F9. Räckviddsrelationen behöver en tredje form: "vilken läsning?"**
`InomRackvidd` har två läsningar och specen nämner ingen av dem. Mätt: med den
hårda kan en robot på 1 650 mm inte nå ett 2 m långt band, så varje cell med en
transportör blev röd. Vi räknar nu båda och gör skillnaden till en fråga
(§6.2, F4). Specen bör säga att en relation får ha en **parameter som
operatören äger**, och att båda utfallen ska räknas innan frågan ställs.

**F8. `K23` har två halvor, och bara den ena är en ordningsregel.** *"Alla
`post`-anrop och all mätning som L3 behöver är `read` och får aldrig ligga i
kön"* är mekaniserat (`EK3`, plus att routingen ägs av utföraren, `I12`).
*"Läsande förfrågningar före skrivande"* som en **omsortering** av sekvensen
går däremot inte ihop med beroendeordningen: en efterkontroll efter ett
skrivande steg måste per definition komma efter det. Specen bör säga vilken av
de två den menar.

**F7. Databladet (K0, fas 4b) behöver en källa som faktiskt bär fälten.**
`footprint_mm` ur `BoundCenter` + `BoundDiagonal` finns **inte** i någon
komponentfil — det är en egenskap hos den *byggda* komponenten, inte hos filen
(M-61). Specen bör säga att fas 4b kräver en VC-körning per post, och vad den
kostar.

---

## 9. Vad den här mätningen INTE visar

**Att planen bygger rätt cell.** Grinden mäter att planen håller
verktygsregistret, bär sitt bevis och inte motsäger sig själv. Den mäter inte om
komponenten passar uppgiften. `P3` fångar en uppfunnen URI, inte en olämplig.

**Att koordinaterna går att köra.** Layoutmotorn lämnar ut koordinater bara när
varje ankare är **mätt** med `get_bounds` i VC. Alla prov här kör med
`strikt_ankare=False`, och **de koordinaterna får inte köras mot en riktig
scen**. Om origo sitter någon annanstans än i lådans mitt hamnar komponenten
fel, tyst. Det är fas 5a:s arbete (`P5`), inte det här protokollets.

**Att textläsningen förstår svenska.** `lasning.py` läser slutna mönster.
Beställningar formulerade utanför dem ger **färre** krav, inte fel krav — det
som inte lästes blir en fråga, och ett ord i komponentuppräkningen som ingen rad
känner igen blir en **blockerande** fråga (§6.2). **Hur ofta det händer är inte
mätt.** En sådan mätning kräver en samling verkliga beställningar, och den finns
inte: jag har prövat operatörens ena exempel och mina egna. Det är den största
oprövade ytan i det här arbetet, och §6.2 visar precis hur den ytan ser ut när
den brister.

**Att processlistan täcker en verklig cell.** `PROCESSORD` är 28 ord. En process
som inte står där blir ingen process alls, och beställningen tappar den halvan
utan att något blir rött. Listan bör växa med en mätning över riktiga
beställningar, inte med infall.

**Att `INGEN_MOTSAGELSE_FUNNEN` betyder att layouten går.** Det betyder att just
de kontrollerna inte föll. De härledda villkoren är nödvändiga, aldrig
tillräckliga, och lösarens nej gäller det raster som söktes.

**Att rasterstegen är rätt.** Tre steg är mätta över 81 körningar i **en**
scenfamilj (robot + band + pall + fixtur, kvadratiska hallar). Ett fjärde,
finare steg kan ändra svaret, och en avlång hall är inte prövad.

**Att bankvägen och fritextvägen ger samma detaljering.** De döms av samma
grindar, och hela banken är körd (§6.1): 46 av 51 blir `BYGGBAR`. Men bankens
uppgifter bär **inga cellmått, inga relationer och ingen processordning**, så
`B2` och den geometriska halvan av `B3` har ingenting att pröva där. De 46 gröna
säger alltså ingenting om de två grindarna. Det som saknas är en samling
beställningar som bär cellmått — och den finns inte.

**Att felen jag inte letade efter inte finns.** Mätningen jämförde spec mot kod.
Den letade inte efter fel i den kod som redan fanns, utöver det som föll ut på
vägen.

---

## 10. Det som fälls, och hur

De tre trasiga fall uppgiften krävde, körda:

```
$ python3 -m pytest tests/enhet/test_bestallning.py -q
180 passed
```

**En självmotsägande beställning:**

```
BESKED AVVISAD
GRIND B3_MOTSAGELSE
MK1_INTERVALL_TOMT: cell.bredd_mm maste vara bade minst 3000 mm och hogst
                    2000 mm; det finns inget sadant varde
    cell_bredd_3: cell.bredd_mm ge 3000.0  [ur din begaran: "minst 3 meter bred"]
    cell_bredd_1: cell.bredd_mm le 2000.0  [ur din begaran: "hogst 2x2 meter"]
    atgard: ta bort eller mjuka upp ett av de tva kraven
```

**En cyklisk processordning:**

```
BESKED AVVISAD
GRIND B2_PROCESSORDNING
PO1_CYKEL processerna malning, svetsning bildar en ring:
          malning -> svetsning -> malning
```

**Ett antaget krav som inte är märkt som antaget:**

```
BESKED AVVISAD
GRIND B1_HARKOMST
HK2_FALSK_BEGARAN villkoret uppfunnet sager sig komma ur begaran med orden
                  'hogst 1200 mm', men de orden star inte i begaran. Ett krav
                  vi hittat pa ska vara ett markt antagande, inte operatorens ord
```

Och den positiva riktningen, som gör de tre meningsfulla: samma väg ger
`BESKED BYGGBAR` med en 22-stegs plan, koordinater ur layoutlösaren,
processordningen `plockning -> packning` och 13 märkta antaganden.
