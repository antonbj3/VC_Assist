# M-74 — kompositionsfallen: fel som bara finns när stationerna står tillsammans

**Datum:** 2026-09-05 · samma rigg som [M-73](M-73_linan_arbetar.md)
**Körs av:** `tests/protocol/kor_fas8_linan.py`
**Protokollet:** `tests/protocol/fas8_linan.md`

## Definitionen, och varför båda halvorna krävs

Ett **kompositionsfel** är ett fel som

1. **fälls** av ögat när båda stationernas block kör i samma program, och
2. **inte fälls** när stationerna körs var för sig.

Ett fall som ögat fäller också i en station för sig är inget kompositionsfel —
det är ett fas 7-fel, och de är redan mätta (`M-50`). Ett fall som ingen fäller
är inget fel alls. Körningen kör därför **varje** program i tre
konfigurationer, med egen signalkarta, egen kompilering och egen uppladdning:

```
LINJE   bada stationernas block i samma PLC-program
A       bara station A:s block          <- exakt fas 7:s upps~tallning
B       bara station B:s block
```

## Fallen, och vad som skiljer dem från den hela lösningen

Var och en är **en** ändring. Diffen mot den hela lösningen är körningens egen
utdata (`reduktionen()` och kroppsjämförelsen), inte en beskrivning:

```
K1  INSTANS  -        CASE b_laget OF                +        CASE a_laget OF
                      (och b_laget -> a_laget pa fyra rader till)
K2  INSTANS  -        b_flank(CLK := b_givare);      +        a_flank(CLK := b_givare);
                      -            IF b_flank.Q THEN +            IF a_flank.Q THEN
K3  VILLKOR  -   IF a_tid.Q AND b_laget <> 2 THEN    +   IF a_tid.Q THEN
                 -   IF b_tid.Q AND a_laget <> 2 THEN     +   IF b_tid.Q THEN
K4  VILLKOR  -            a_stopp := TRUE;           +            a_stopp := NOT b_slapp;
                 -            b_stopp := TRUE;            +            b_stopp := NOT a_slapp;
K5  VILLKOR  -   IF a_tid.Q AND b_laget <> 2 THEN
                 +   IF a_tid.Q AND b_laget <> 2 AND NOT b_givare THEN
```

| # | Ändringen i ord | Klassen den hör till |
|---|---|---|
| **K1** | station B:s block räknar i station A:s tillståndsvariabel | två stationer tar samma resurs — programmets |
| **K2** | station B:s block anropar station A:s flankdetektor | en station svälter: den tappar sina starter |
| **K3** | turordningen på det delade utmatningsdonet borttagen | två stationer tar samma resurs — den fysiska |
| **K4** | förreglingen skriven för linan i stället för per station | en förregling som håller inom en station men bryts mellan två |
| **K5** | station A släpper inte förrän station B:s zon är tom | en station blockerar nästa: mättnad nedströms |

### Två sorters ändringar, och skillnaden bär halva beviset

**INSTANS** (K1, K2) låter stationerna dela en arbetsvariabel. Texten är
**densamma** i alla tre konfigurationerna: enstationskörningen kör fallets egen
kod, och delningen har då bara en delägare — `a_laget` är i station B:s ensamma
program bara ett annat namn på `b_laget`.

**VILLKOR** (K3, K4, K5) rör ett villkor eller en rad som namnger den **andra**
stationens signal eller läge. I en enstationskonfiguration har den ingen
referent, och kroppen reduceras då **tecken för tecken** till den hela
lösningens. Körningen kontrollerar det mekaniskt:

```
K1  INSTANS  A=lika  B=EGEN TEXT
K2  INSTANS  A=lika  B=EGEN TEXT
K3  VILLKOR  A=lika  B=lika
K4  VILLKOR  A=lika  B=lika
K5  VILLKOR  A=lika  B=lika
```

`lika` betyder att fallets ST-kropp för den konfigurationen är identisk med den
hela lösningens. Det är halva beviset, och det är den starkare halvan: **det
som inte går att skriva med en station kan inte fällas i en.** Den andra halvan
är att köra dem ändå, och det gjordes.

## Utfallet

Sex fall i tre konfigurationer, alltså **arton körningar**, var och en med egen
VC-omstart, egen signalkarta, egen kompilering, egen uppladdning till OpenPLC,
omstart av runtimeprocessen, 45 s uppvärmning och 80 s mätning. Tre av dem
kördes om, och skälen står nedan: två för att perturbationen inte nådde
enstationskörningen av station B, och en för att klockan låg utanför
braketten.

| # | LINJE: station A | LINJE: station B | LINJE: linan | A ensam | B ensam | |
|---|---|---|---|---|---|---|
| **HEL** | PASS | PASS | **PASS** | PASS | PASS | — |
| **K1** | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | PASS | PASS | **KOMPOSITIONSFEL** |
| **K2** | PASS | **FAIL** | **FAIL** | PASS | PASS | **KOMPOSITIONSFEL** |
| **K3** | **FAIL** | **FAIL** | **FAIL** | PASS | PASS | **KOMPOSITIONSFEL** |
| **K4** | **FAIL** | **FAIL** | **FAIL** | PASS | PASS | **KOMPOSITIONSFEL** |
| **K5** | PASS | PASS | **FAIL** | PASS | PASS | **KOMPOSITIONSFEL** |

**Fem av fem.** Varje fall fälldes i linan och passerade i båda
enstationskörningarna. Inget av dem föll före ögat: grind 1–4 var GODKÄND i
**alla arton körningarna**, vilket är protokollets hårda krav — en statisk
regel som råkar fånga ett kompositionsfel vore inget bevis på att ögat ser
det.

Guldgrinden över den hela lösningens fem celler:

```
GOLD gold_verified_core (5 av 5 celler gav PASS)
```

Fem celler, för kontraktet är två påståenden och inte ett: station A ensam,
station B ensam, och i linan station A, station B och linan.

Det är också värt att läsa tabellen åt andra hållet. **Tio
enstationskörningar, tio PASS.** En domare som fäller allt klarar varje
fällningsprov och är ändå värdelös; här tiger den i exakt de fall där den ska
tiga, och den tiger på program som i linan är sönder.

### K1 — delad tillståndsvariabel: linan dör

```
ST8A_Givare/Puls   hög i 100,0 % av 800 prov      RISE-flanker: 0
ST8A_Don/Stopp     hög i   0,0 %                  RISE-flanker: 0
ST8A_Don/Slapp     hög i 100,0 %                  RISE-flanker: 0
ST8B_Givare/Puls   hög i   0,0 %                  RISE-flanker: 0
ST8B_Don/Stopp     hög i 100,0 %                  RISE-flanker: 0
ST8B_Don/Slapp     hög i   0,0 %                  RISE-flanker: 0
```

Inte en enda flank på 80 s. Station A står låst i utmatningsläget, station B i
bromsläget, och de två läsarna av samma variabel håller varandra där: A skriver
`a_laget := 2`, B läser samma variabel och skriver `a_laget := 1`, och nästa
scan börjar om. Bana 2 står stilla, kön växer bakåt över kopplingen och fyller
bana 1 ända upp i station A:s givarfönster — som därför är högt i **100 %** av
proven. Det är mottrycket ur `M-73`, nu som symptom i stället för som mätning.

Ögat säger `INCONCLUSIVE` med orden *"ingen RISE-flank på ST8A_Givare/Puls:
ingen cykel började ens"*. Det är samma dom som fas 7 gav `T4`, och den betyder
samma sak: det här är inte en obestämbar station, det är en **död lina**, och
ögat säger det med sina egna tal.

Ensam är station B:s program identiskt i beteende — `a_laget` är då bara ett
annat namn på `b_laget`, det finns ingen andra läsare, och stationen ger PASS.

### K2 — delad flankdetektor: en station svälter medan material passerar

```
ST8A_Givare/Puls   36 %   8 RISE      ST8B_Givare/Puls   18 %   8 RISE
ST8A_Don/Stopp     24 %   8 RISE      ST8B_Don/Stopp      0 %   0 RISE
ST8A_Don/Slapp     14 %   7 RISE      ST8B_Don/Slapp      0 %   0 RISE
```

**Åtta produkter passerade station B:s fotocell, och B:s broms gick inte ut en
enda gång.** Station A arbetade oberört och fick PASS på alla sina cykler.

Mekaniken: en `R_TRIG` som anropas två gånger per scan med olika `CLK` ger vid
det andra anropet `Q = CLK AND NOT (den första CLK:n)`. Station A:s givare är
hög en stor del av takten, så station B:s flank blir aldrig sann. Ensam anropas
detektorn en gång per scan och är då en riktig flank — det är exakt fas 7:s
HEL-kropp, och den ger PASS.

Det är den renaste formen av *en station som svälter*: materialet kommer, men
stationen får aldrig veta om det.

### K3 — den delade utmataren utan turordning: förreglingen inom håller, den mellan bryts

```
station A:s egen forregling   ST8A_Don/Stopp + ST8A_Don/Slapp   overlapp 0,00 s i  0 prov   OK
station B:s egen forregling   ST8B_Don/Stopp + ST8B_Don/Slapp   overlapp 0,00 s i  0 prov   OK
linans forregling             ST8A_Don/Slapp + ST8B_Don/Slapp   overlapp 3,90 s i 45 prov   BROTT
konflikter i anlaggningen:    15   (den hela losningen: 0)
```

Tre rader ur samma serie, och de säger hela fas 8 i tre tal: **inuti** varje
station är förreglingen perfekt, **mellan** stationerna bryts den i 3,90 s. Och
anläggningen räknade 15 varv där båda stationerna begärde samma don — mot noll
i den hela lösningen.

Följden syns i fysiken: när ingen får donet står båda banorna kvar, och
utmatningen som aldrig kom ger `ST8A_Don/Slapp FALL uteblev` på flera cykler i
båda stationerna.

### K4 — förreglingen skriven för linan: den håller inom och bryts mellan

```
station A:s egen forregling   overlapp 0,00 s i 0 prov   OK
station B:s egen forregling   overlapp 0,00 s i 0 prov   OK
cykel 1: ST8A_Don/Stopp FALL kom redan 1,20 s efter starten, fonstret ar 1,50-6,86 s
cykel 1: ST8B_Givare/Puls RISE kom redan 3,60 s efter starten, fonstret ar 4,09-8,89 s
cykel 3: ST8B_Givare/Puls RISE kom redan 3,30 s efter starten
```

Raden `a_stopp := NOT b_slapp` är, läst inom station A, en fullgod förregling:
bromsen och stationens egen utmatning kan fortfarande aldrig vara höga
samtidigt, och ögat mäter 0,00 s överlapp i **båda** stationerna. Men bromsen
släpper nu också när den **andra** stationen matar ut, och då går produkten
ifrån stationen mitt i processen — 1,20 s in i en process som ska vara 2,0 s.

Att produkten går för tidigt syns sedan nedströms: den når station B **3,3–3,6
s** efter överlämningen i stället för de 4,09–8,89 s som geometrin medger. Det
är en produkt som lämnar station 1 innan station 2 är redo, mätt i sekunder på
mottagarsidan.

### K5 — station A väntar på station B:s zon: bara linan ser det

Det är det renaste fallet i hela mätningen, och det som bäst visar varför fas 8
behövde ett eget facit för **linan**:

```
LINJE   station A  PASS   allt inom marginal
LINJE   station B  PASS   allt inom marginal
LINJE   linan      FAIL   cykel 5: ST8B_Givare/Puls RISE uteblev i fonstret 4,09-8,89 s
                          cykel 6: ST8B_Givare/Puls gick hog 2 ganger, hogst 1 ar tillatet
```

**Båda stationerna gör allt rätt. Linan gör det inte.** Varje station håller
sin egen ordning, sina egna fönster och sin egen förregling — men
överlämningen mellan dem gör det inte: en produkt uteblir i sitt fönster, och
i nästa cykel kommer två.

Mättnaden syns i bromsens gångtid: station A:s broms är ute i **35 %** av
proven mot **23 %** i den hela lösningen. A står och väntar in station B:s zon,
bandet står stilla längre, och kön uppströms växer. Med två stationsfacit och
inget linjefacit hade den här körningen varit grön.

## Vad mätningen tvingade fram i grinden

### Perturbationen måste nå också enstationskörningen

Driftpausen armades först på **station A:s** broms. I konfigurationen `B`
finns den inte, och pausen kom därför aldrig: kontrollkörningen var mildare än
linjekörningen, och en fixtur som passerar en mildare prövning har inte
passerat prövningen. Pausen armas nu på vilken som helst av stationernas
bromsar, och `HEL/A` och `HEL/B` kördes om med den. Båda gav PASS igen — men
nu på samma störning som linan fick.

### En körning vars klocka låg utanför braketten är ogiltig, inte fällande

`K2`:s första linjekörning fick klockkvoten **0,6131** mot braketten
0,75–1,40. Orsaken var vår egen: en provsvit kördes samtidigt på samma maskin
och tog pumpens tid. Facits fönster är skalade med braketten, så utanför den
mäter de kopplingen mellan klockorna i stället för stationen — med kvoten 0,61
syns en 2-sekunderstimer som 1,22 s på ögats axel, och en **riktig** station
faller då på `TOO_EARLY`.

Protokollet lovade grinden; den fanns inte. Nu finns den: körningen svarar
`OGILTIG` och fallet kördes om. Omkörningen, med kvoten 0,9896, gav **samma
dom** — station A PASS, station B FAIL, linan FAIL. Felet var alltså verkligt
och inte ett klockutslag, men det visste ingen förrän det mättes om.

### Ett genomströmningskrav utan en enda provad station gav PASS

Fas 8 ville mäta mättnad nedströms med ögats `genomstromning`-grind och mätte
i stället grinden själv. En plan som deklarerar ett krav mot en serie **utan
stationsprov** fick:

```
DOM: ('PASS', 'allt inom marginal')
genomflode-domaren: {'utfall': 'PASS', 'skal': [], 'fynd': {'brott': []}}
```

Grinden såg ett krav, hittade inga brott — för det fanns inga stationer att
hitta brott hos — och godkände. Det är farligast just där: `stat` kräver ett
`vcStatistics`-beteende i scenen, och saknas det tiger provtagningen utan att
säga ifrån. Grinden svarar nu `INCONCLUSIVE`, och den nya cellen
`station_krav_utan_prov` i `tests/celler.py` är dess nollpunkt.

### Ett konflikttal som strukturellt aldrig kunde bli annat än noll

Körningen rapporterade `anlaggning.konflikter`, hämtat ur den köade postens
svar. Den posten hämtas med en **lätt** fråga som inte tar med resultatet —
annars serialiserar `queue_list` hela kön med varje posts svar (`M-49`). Talet
var alltså noll i varje körning, också i `K3` där båda stationerna verkligen
begärde donet samtidigt 15 gånger. Ett mått som ser mätt ut och inte kan bli
annat än grönt är värre än inget mått. Konflikterna räknas nu i slingan, ur
kopplarens egna värden, och `K3` ger 15 mot den hela lösningens 0.

## Vad som INTE är visat

* **Att listan över kompositionsfelklasser är komplett.** Fem klasser är
  fällda. Felklasserna i verkligheten är inte slut — det här är fem sätt att
  vara sönder, inte alla.
* **Fler än två stationer.** Att en tredje station inte bär en klass av fel som
  två inte har är **oprövat**.
* **Att felen fälls i en scen som inte är den här.** Fixturerna är fällda på
  **en** lina, med **en** geometri och **en** takt. Takten är dessutom vald så
  att stationernas faser möts (`M-73`); en lina vars takt är längre än båda
  stationernas upptagenhet står aldrig på varandra, och där hade K3 inte haft
  någon samtidighet att bryta mot.
* **Att en modell skriver kropparna.** Alla sex är handskrivna, och
  reparationsvarven är **noll** av samma skäl: ingen modell har fått något fel
  tillbaka att laga. Det är fas 9.
* **Mättnad nedströms som ett eget mått.** `K5` fälls på överlämningens
  sekvens och på bromsens gångtid, inte på ett genomströmningstal. Ögats
  `genomstromning`-grind kräver `vcStatistics`, och den vägen är inte prövad
  här.
* **Nödstoppet.** Den `skyddad`-märkta ingången går inte att driva över OPC UA
  (`M-49`) och stod konstant `FALSE` i alla femton körningarna.
* **Windows. Verklig hårdvara. Hur ofta det lyckas.**
