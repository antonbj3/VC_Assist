# M-73 — linan arbetar: två stationer, ett delat don, och guld i tre celler

**Datum:** 2026-09-05 · VC Premium 4.10 · Wine 11.16 · testprefixet
`~/.wine-vc-test`, headless `:99` · OpenPLC v4.2.1 · STruC++ 0.6.6
**Fas:** 8, första halvan. Kompositionsfallen ligger i
[M-74](M-74_kompositionsfallen.md).
**Körs av:** `tests/protocol/kor_fas8_linan.py`
**Protokollet:** `tests/protocol/fas8_linan.md`

## Vad som byggdes

En lina med **två** stationer, byggd ovanpå flödeslinjen från
[M-41](M-41_produkten_flodar.md):

```
matare (8,0 s)  ->  ST8_Bana1 (3000 mm)  ->  ST8_Bana2 (3000 mm)  ->  av i änden
                    station A, d = 2400        station B, d = 1400
```

* en **fotocell** per station, ±150 mm kring sitt banavstånd,
* en **broms** som stoppar sin egen bana, och en **bromsklack** som går ut och
  in — det enda objekt PLC:n kommenderar som ögat kan se röra sig,
* ett **delat utmatningsdon** som båda stationerna kommenderar,
* en signalkarta med åtta taggar, varav en `skyddad`.

Sekvensen per station, deklarerad **före** lösningarna skrevs: produkten når
fotocellen → bromsen ut inom transporttiden → processtiden 2 s → bromsen
släpper och utmatningen går 1,5 s → produkten lämnar stationen. Och för
**linan**: varje produkt station A lämnar ifrån sig ska nå station B och
klämmas där inom överlämningstiden, och stationerna får aldrig begära det
delade donet samtidigt.

## Två saker i scenen som ingen tidigare mätning hade svarat på

Båda står som öppna punkter i tidigare mätningar, och fas 8 kunde inte byggas
utan svaren.

### En produkt går över kopplingen bana → bana

`M-41` skrev: *"Produkten lämnar aldrig banan till något annat … Ett led till
— bana → bana, eller bana → sänka — är **oprövat**."* `M-67` skrev: *"Om en
produkt faktiskt går över kopplingen … är **inte** mätt — kopplingen är
logisk, men transporten kan mycket väl kräva att ramarna sammanfaller."*

Två banor byggdes i serie, den andra placerad så att dess in-ram sammanfaller
med den förstas ut-ram, och kopplade genom receptet `koppla` (väg `E0`,
`canConnect` → `connect`). Elva produkter följdes över kopplingen på 77 s:

```
overgang t=12.68  bana 1 -> bana 2   (banavstandet raknas om: 2914 -> 169)
overgang t=18.82  bana 1 -> bana 2
overgang t=24.96  bana 1 -> bana 2
...  elva overgangar, ingen forlorad produkt
```

Banavståndet räknas om mot den nya banan, och `WorldPositionMatrix.P.X`
fortsätter växa utan hopp. **Transporten kräver alltså inte mer än att ramarna
sammanfaller** — vilket är precis vad `M-40`:s villkor 3 redan krävde för att
kopplingen alls skulle gå att göra.

### En stoppad nedströmsbana ackumulerar uppströms

`M-41` noterade: *"`Accumulate = True` är satt men aldrig belastad. Ingen
produkt har blivit blockerad av en annan i de här serierna."*

Bana 2 stoppades i 20 s medan bana 1 fortsatte gå. Kön som byggdes upp vid
kopplingen, läst som banavstånd på bana 1:

```
t=55.92  bana1-kon: 2826.8  2480.4  2134.0  1787.6   ... 480.0
         parvis avstand:  346.4  346.4  346.4
```

Fyra produkter i rad, **exakt 346,4 mm isär** tre gånger i följd. Den produkt
som ligger först stannar 173 mm före banans slut, och de bakomvarande lägger
sig på ett fast avstånd. Mottrycket är alltså verkligt, det fortplantar sig
uppströms, och avståndet i kön är en **mätt** storhet — inte en gissning.

Det spelar roll för fas 8 därför att det är den enda mekanism i riggen som
kopplar stationerna **fysiskt**: en station som håller sin bana håller också
tillbaka den föregåendes utflöde.

## Den delade utmataren — fas 8:s nya fysik, deklarerad före lösningarna

Stationerna delar **ett** utmatningsdon. Anläggningen (som bor i tjänsten, av
skälen i `M-49`) gör tre saker med det, och alla tre är deklarerade i koden
före något dömdes:

1. begär bara en station donet får den det, och dess bana går i 600 mm/s,
2. begär **båda** det samtidigt får **ingen** det, båda banorna står kvar
   stilla, och donet står still,
3. konflikten **rapporteras**, den tigs inte — samma hållning som M-49:s
   bromskonflikt.

Det är den enda plats i linan där två stationer kan slåss om något, och den
finns där med flit: utan en delad resurs finns det inget kompositionsfel av
den klassen att fånga.

## Fasens kontrakt, punkt för punkt

`docs/spec/70_faser.md` för fas 8: *"Flera stationer. Guld per station, sedan
guld för linan. **L2**"*.

| Kravet | Utfall |
|---|---|
| Grind 1 kompilering | GODKÄND i alla tre konfigurationerna (STruC++ 0.6.6) |
| Grind 2 statisk analys | GODKÄND |
| Grind 3 deklarationsmatchning | GODKÄND |
| Grind 4 anropsvalidering | GODKÄND (5 namn kontrollerade) |
| Grind 5 ögat, station A ensam | **PASS** |
| Grind 5 ögat, station B ensam | **PASS** |
| Grind 5 ögat, båda i linan | **PASS** för station A, **PASS** för station B, **PASS** för linan |
| Guld per station | **GOLD gold_verified_core** (2 av 2 celler) |
| Guld för linan | **GOLD gold_verified_core** (3 av 3 celler) |

## Vad ögat sa

**PASS i alla tre cellerna.** Nio hela cykler dömda per cell, en avhuggen (den
sista, vars fönster inte ryms i serien och som därför är oprövad, inte
godkänd).

```
linan     PASS  allt inom marginal   cykler domda=9 brott=0 tidsbrott=0 avhuggna=1
stationA  PASS  allt inom marginal   cykler domda=9 brott=0 tidsbrott=0 avhuggna=1
stationB  PASS  allt inom marginal   cykler domda=9 brott=0 tidsbrott=0 avhuggna=1
forregling ST8A_Don/Slapp + ST8B_Don/Slapp   overlapp 0.000 s i 0 prov
forregling ST8A_Don/Stopp + ST8A_Don/Slapp   overlapp 0.000 s i 0 prov
forregling ST8B_Don/Stopp + ST8B_Don/Slapp   overlapp 0.000 s i 0 prov
```

**Noll konflikter om det delade donet** över 267 kopplarvarv.

### Talen ur linans egen serie

```
station A   takt mellan produkter   8,1  8,1  7,8  9,0  7,2  7,8  8,1  8,1  7,8 s
            processtid              1,7  1,8  1,8  1,8  2,4  1,8  1,8  1,8  1,8  1,8 s
            utmatning               1,2  1,2  1,2  1,2  0,9  1,2  1,2  1,2  1,2  1,2 s
station B   processtid              2,1  1,6  2,1  1,8  2,4  2,7  1,9  1,8  1,8  2,4 s
            utmatning               0,9  1,2  0,9  1,2  0,9  0,9  1,2  1,2  1,2  0,9 s
overlamning A slapp FALL -> B puls RISE
                                    5,7  5,4  5,7  5,1  5,4  5,7  6,0  5,7  5,1 s
```

Tre saker är värda att läsa i de raderna.

**Takten är matarens.** 7,2–9,0 s mot matarens 8,0 s, och spridningen är
ögats provintervall (0,1 s) plus kopplarvarvet (median 55 ms, p95 71 ms) plus
driftpausen i en av cyklerna.

**Överlämningen stämmer med geometrin.** Facit räknade 5,45 s ur banornas
längder och farter, utan att titta på någon körning; det uppmätta ligger på
5,1–6,0 s.

**Station B:s processtid varierar och station A:s gör det inte.** Det är
linjevillkoret som syns: B väntar in det delade donet när A har det, och
väntan är som mest en hel utmatning. A:s processtid är 1,8 s i nio cykler av
tio; B:s är 1,6–2,7 s. Skillnaden mellan de två stationernas fönster i facit
är alltså inte en uppmjukning för B — den är linans konstruktion, och den
syns i talen.

## De två klockorna, mätta om i den här riggen

`M-49` mätte kvoten simuleringstid/väggtid till 1,000 i tre driftpunkter sedan
den dyra pollningen tagits bort. Fas 8:s fönster är snävare än fas 7:s
(`KLOCKA_LAG` 0,75 och `KLOCKA_HOG` 1,40 mot 0,6 och 1,6), och den snävheten
är köpt: körningen mäter kvoten i **varje** körning och skriver ut den.

```
LINJE  0,9895      A  0,9893      B  0,9840
```

## Riggen kostar

```
kopplarvarv:        417 (150 under uppvarmningen, 267 under matningen)
varvtid:            median 55 ms   p95 71 ms   max 228 ms   n=267
anlaggningssteg:    417
ogats serie:        80,0 s, 800 prov, 10,00 Hz
```

## Fem fel i riggen som bara en körning kunde hitta

Alla fem är rättade i koden, och alla fem hittades genom att köra linan och
läsa serien — inte genom att läsa koden.

### 1. `WorldPositionMatrix` släpar, och ett tätt prov gör det till en falsk puls

Anläggningen måste veta vilken bana en produkt står på. Första versionen
frågade om världens x stämde med hypotesen "bana 2" på mindre än 1 mm. Men
`WorldPositionMatrix` släpar ett scenuppdateringssteg (`M-11`) medan
`getPathDistance` är färsk, och ett dygnsfärskt banavstånd mot ett steg gammalt
x gav fel svar med jämna mellanrum. En produkt på **bana 2** vid banavstånd
2400 blev då en produkt på **bana 1** vid banavstånd 2400 — alltså mitt i
station A:s givarfönster — och gav en puls där ingen produkt fanns.

Rättelsen är att fråga efter **differensen** `x − d` i stället: den är
matarlängden på bana 1 och matarlängden plus banlängden på bana 2, alltså 3000
mm isär. En eftersläpning på ett steg är 12 mm.

*Lärdomen är M-11:s, för femte gången, men på en ny storhet: ett prov vars
tolerans är snävare än eftersläpningen mäter eftersläpningen.*

### 2. Facits steg måste stå i fysikens ordning, inte i berättelsens

Facit listade `Slapp FALL` före `Puls FALL`, därför att det är så man berättar
det: stationen matar ut, sedan lämnar produkten. Men utmatningen är 1,5 s och
produkten är ute ur givarfönstret efter 0,44 s. En ordningsdom söker varje steg
**efter** det föregående, så `Puls FALL` — som redan hade inträffat — dömdes
som uteblivet, på varje cykel, för en station som gjorde allt rätt.

### 3. En OPC UA-läsning i taget tillverkar sitt eget förreglingsbrott

Kopplaren läste en tagg i taget. Just när en station går från broms till
utmatning hämtas då `stopp` ur ett scan och `slapp` ur nästa: båda svarar
`TRUE`, kopplaren skriver båda höga i scenen, och ögat mäter ett
förreglingsbrott på 0,10 s som PLC:n aldrig gjorde.

```
ST8A_Don/Stopp och ST8A_Don/Slapp var hoga samtidigt i 0.10 s (fran t=31.10 s)
```

En samlad läsning (`read_values`) kan servern besvara ur **ett** tillstånd, och
brottet försvann. Det är samma klass av fel som M-49:s: **mätinstrumentet låg i
mätvägen**, och det som mättes var instrumentet.

### 4. Ett villkor som läser den andra stationens UTGÅNG släpper igenom precis
det det skulle hindra

Första turordningen på det delade donet var `IF b_tid.Q AND NOT a_slapp`. Den
höll inte. Skälet är att `a_laget := 2` och `a_slapp := TRUE` sker i **olika
scan**: beslutet att ta donet fattas i CASE-satsen, men ställdonet sätts först
när nästa scan kör det nya läget. Båda stationerna såg alltså ett lågt `slapp`
i samma scan, båda steg in i utmatningsläget, och i nästa scan gick båda
utgångarna höga samtidigt:

```
36.10 ST8A_Don/Slapp RISE      36.10 ST8B_Don/Slapp RISE
37.30 ST8A_Don/Slapp FALL      37.30 ST8B_Don/Slapp FALL
```

Villkoret frågar nu efter den andra stationens **läge** (`b_laget <> 2`), som
sätts i samma scan som beslutet. Då avgör scanordningen: station A:s block körs
först, stiger in i läget, och station B ser det redan i samma scan.

*Ett villkor som frågar efter FÖLJDEN av ett beslut i stället för efter
beslutet självt släpper igenom precis den samtidighet det skulle hindra.*

### 5. Perturbationen mätte riggens brist, inte lösningens

Driftväljaren `kor` slås av i 1,0 s, lika för alla fall (arvet från `M-50`).
Första versionen lät banorna gå medan väljaren stod av — och då gled en produkt
förbi station B, som inte fick arbeta. Stationens facit föll på det, med rätta,
men felet var riggens: **en lina vars driftväljare står av står stilla.**
Anläggningen stannar nu båda banorna när `kor` är låg.

Samtidigt togs timernollställningen bort ur pausgrenen. Med den blev den
perturberade cykeln pausen **plus en hel processtid** längre, och varje fönster
i facit hade fått vidgas med lika mycket — vilket hade svalt just de marginaler
kompositionsfelen lever i. En TON som inte anropas står kvar där den står.

### Och en sjätte: glappet mellan uppvärmningen och mätningen

Uppvärmningen och mätningen delade först inte kopplare. Under bytet kördes inga
anläggningssteg, banorna behöll sin sista fart, och linans takt hoppade: de två
första cyklerna i serien blev 5,1 s i stället för 8,1 s, och linjefacit föll på
dem. Samma kopplare värmer och mäter nu.

## Vad som INTE är visat

* **Fler än två stationer.** Allt här är mätt på två. Att en tredje station
  inte introducerar en klass av fel som två inte har är **oprövat**.
* **Att en modell skriver kropparna.** Alla ST-kroppar är handskrivna. Fas 8
  påstår att kompositionen går att döma, inte att en språkmodell hittar den.
  Reparationsvarv: **noll**, av samma skäl.
* **Nödstoppet.** Den `skyddad`-märkta ingången går inte att driva över OPC UA
  (`BadInternalError`, M-49) och stod konstant `FALSE`.
* **Genomströmningsgrinden.** Ögats `genomstromning` läser `vcStatistics`, och
  den vägen är inte prövad här: linans stationer är banor och klackar, inte
  processnoder. Svält och blockering döms därför på **sekvensen**, inte på
  stationsstatistiken. Vad som händer om man deklarerar ett
  genomströmningskrav utan att prova någon station står i `M-74`.
* **Långtidsjämvikt.** Serien är 80 s, alltså tio produkter. Att kön på bana 1
  inte växer långsamt över en timme är inte mätt.
* **Fasförhållandet PLC ↔ scen.** Kräver `--plc-inskott`, som är av av samma
  skäl som i fas 7 (M-49).
* **Windows. Verklig hårdvara. Hur ofta det lyckas.**
