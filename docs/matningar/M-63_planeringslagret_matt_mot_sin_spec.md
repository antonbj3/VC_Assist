# M-63 — planeringslagret mätt mot sin egen spec

**Datum:** 2026-09-04 · körs utan VC · fas 16 i `docs/spec/70_faser.md`
**Mäter:** `docs/spec/22_planeringslagret.md` (384 rader) mot
`svc/vc_assist_svc/plan/` (3 868 rader före, 7 013 efter)
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

Efter det här arbetet: **8 av 30 kravkoder** och **4 av 12 felklasser** nämns i
kod eller prov. Talet är fortfarande lågt, och det ska det vara: en kod ska
skrivas in i koden när kravet faktiskt är mekaniserat, inte som en etikett.

## 2. Den finare mätningen: krav för krav

Grep säger bara om ett namn nämns. Den här tabellen är läst, inte räknad, och
varje rad pekar på fil och funktion.

| | Före | Efter |
|---|---:|---:|
| **uppfyllt** | 9 | **17** |
| **delvis** | 8 | 6 |
| **saknas** | 13 | 6 |
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
| `K1` | `needed_for` per spec-fält, lintkod `S1_SLOT_WITHOUT_NEED` | kräver att varje grind namnger sina indata; hör ihop med P1–P2 och är en egen runda |
| `K4` | `spec.clarify_round`, högst två frågerundor | det finns ingen samtalsloop att räkna rundor i (`24_samtalsloopen.md` är inte byggd) |
| `K10` | taket på fyra rättningsvarv | lösaren har i stället en **mätt** nodbudget och en rasterstege; se §5 och förslag F4 |
| `K12` | `work_area_mm` som osynlig kropp, `WORK_AREA_UNKNOWN` | kräver celldatabladet på disk (fas 4b), som inte finns |
| `K16` | `post` per steg: `{tool, args, op, expect}` | planen har en ögonkontroll i slutet, inte efterkontroller per steg. Det är `P7` och nästa runda |
| `K23` | läsande anrop före skrivande i kön | planens ordning är beroendeordning, inte effektordning |

`K27` (`SKIP_GATE` avstängd) är **ej tillämpligt**: det finns inget hopp att
stänga av, eftersom ingen grind hoppas över.

### 2.4 Grindarna P1–P8, som de faktiskt står

| Grind | Läge | Vad som gjordes |
|---|---|---|
| P1 Specfullständighet | delvis | blockerande frågor stoppar planen; `clarify_round` saknas |
| P2 Specformslint | delvis | `VS1`–`VS7` mekaniserar S2; S1 kräver `needed_for` |
| P3 Katalogförankring | delvis | URI:er kommer ur indexet eller blir en fråga; databladet som artefakt saknas |
| P4 Layoutdom, statisk | **grön** | `layoutmotor.py` → `layout/losare.losa`, fail-closed |
| P5 Layoutdom, mätt i VC | saknas | kräver VC; hör till fas 5a |
| P6 Plangraf | delvis | graf + register + determinism prövad över tre körningar; hashen i artefakten saknas |
| P7 Efterkontrollstäckning | saknas | se `K16` |
| P8 Planens dom | saknas | kräver VC och ögat |

### 2.5 Felklasserna PL1–PL12

Åtta av tolv fälls nu mekaniskt: `PL1` (tyst förval), `PL2` (uppfunnen URI
eller uppfunnet verktygsnamn), `PL3` (prosavillkor), `PL5` (efterkontroll utan
konsument), `PL6` (implicit ordning), `PL7` (överlapp som byggdes ändå,
statiskt), `PL9` (kontroll som svarade `pass` utan sitt argument), `PL12`
(koordinat i en koppling).

Tre är delvis: `PL8` (klassen läses ur katalogposten — men i **grunt** läge
kommer kategorin från katalognamnet, M-58), `PL10` (gångstråket mäts av
lösarens `kollision.separation`, inte ännu i VC) och `PL11` (jag hittade en och
lämnade den, se §7).

En fälls inte alls: `PL4` (efterkontroll som inte kan falla), eftersom `K16`
inte är byggt.

---

## 3. Vad som byggdes

Nio nya moduler i `svc/vc_assist_svc/plan/`, 2 863 rader, plus ändringar i sex
gamla.

| Modul | Rader | Vad den gör |
|---|---:|---|
| `harkomst.py` | 194 | var ett krav kom ifrån, i en form som går att slå upp |
| `storheter.py` | 326 | den slutna listan av storheter ett villkor får handla om |
| `villkorssprak.py` | 379 | `Typvillkor`, `Relation`, `Prosakrav` med namngiven konsument |
| `processer.py` | 287 | processordningen, med samma cykelkrav som uppgiftsgrafen |
| `motsagelse.py` | 449 | fyra domar, och ingen av dem heter `MOJLIG` |
| `lasning.py` | 387 | fri text → krav, varje värde med sin ordagranna textbit |
| `layoutmotor.py` | 392 | adaptern till den lösare som redan fanns |
| `bestallning.py` | 234 | sex grindar i ordning; ett nej lämnar aldrig ut en plan |
| `ordning.py` | 165 | cykler och kanonisk ordning, delad av graf och processer |

`tests/enhet/test_bestallning.py` (1 172 rader, **135 prov**) och
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
som inte lästes blir en fråga. **Hur ofta det händer är inte mätt.** En sådan
mätning kräver en samling verkliga beställningar, och den finns inte. Det är den
största oprövade ytan i det här arbetet.

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
grindar (det är provat), men bankens uppgifter bär inga cellmått, inga
relationer och ingen processordning — så tre av sex grindar har ingenting att
pröva där. Hur mycket av banken som blir `BYGGBAR` är **inte mätt**.

**Att felen jag inte letade efter inte finns.** Mätningen jämförde spec mot kod.
Den letade inte efter fel i den kod som redan fanns, utöver det som föll ut på
vägen.

---

## 10. Det som fälls, och hur

De tre trasiga fall uppgiften krävde, körda:

```
$ python3 -m pytest tests/enhet/test_bestallning.py -q
135 passed
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
