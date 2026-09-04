# M-50 — de trasiga fallen, och vad som fällde vad

**Datum:** 2026-09-04 · samma rigg som [M-49](M-49_stationen_arbetar.md)
**Körs av:** `tests/protocol/kor_fas7_station.py`
**Protokollet:** `tests/protocol/fas7_stationen.md`

Protokollet listar sju trasiga fall. T1, T2 och T7 fälldes skarpt i
[M-48](M-48_grind_1_till_4_skarpt.md). Den här mätningen tar de fyra som
protokollet säger att **ögat** ska fälla — T3, T4, T5, T6 — plus facitets
nollpunkt.

Kravet är hårt och står i protokollet:

> T3 till T6 måste fällas av **ögat**, inte av en tidigare grind. Om en statisk
> regel råkar fånga T3 är det inte ett bevis på att ögat fungerar, och fallet
> ska skrivas om tills bara ögat kan se det.

Körningen kör därför grind 1–4 på **varje** fall, även de som väntas falla, och
skriver ut varje grinds egen utdata. Ett fall som faller före ögat är inte ett
resultat — det är ett protokollbrott, och det syns i tabellen.

## Fallen, och vad som skiljer dem från den hela lösningen

Alla fem är **samma program** som `HEL` med **en** ändring. Ändringen görs med
`str.replace` och en `assert` som faller om raden bytt form — en trasig fixtur
som tyst blir hel igen är värre än ingen fixtur alls (mätt i M-41, där en
fixtur läkte sig själv).

| # | Ändringen | Varför den är osynlig för grind 1–4 |
|---|---|---|
| **T3** | `IF flank.Q THEN` → `IF givare THEN` | båda är giltig ST, båda rör bara deklarerade taggar, båda kompilerar. Skillnaden är en nivå mot en flank |
| **T4** | `tid(IN := TRUE, ...)` → `tid(IN := flank.Q, ...)` | `flank.Q` är hög en enda scan. Timern startas om av samma villkor som startade den och når aldrig `PT`. Kompilatorn har ingen åsikt om vilket uttryck som driver en `TON` |
| **T5** | `stopp := FALSE;` → `(* stopp := FALSE; *)` i steg 2, och `stopp := FALSE;` tillagt i steg 3 | förreglingen står som kommentar. Bromsen släpper en rad senare, så bromsen och utmatningen är höga **samtidigt** under hela utmatningspulsen |
| **T6** | `IF NOT kor` får `stopp := FALSE; laget := 0;` | "återställ till vila när linjen står" är en rimlig rad. Den gör rätt på varje varv utom det som avbryts mitt i sekvensen |
| **NOLL** | hela kroppen ersatt med två självtilldelningar som rör alla fem taggarna | facitets nollpunkt, rättad av M-48: en **tom** kropp fälls av grind 3 (`ORORD_SIGNAL`), men ett program som rör alla signaler utan att göra något passerar alla fyra förgrindarna |

## Två saker facit inte kunde, och som mätningen tvingade fram

### Ordningen ensam ser inte en station som gör om sitt arbete

Första versionen av facit krävde att stegen kom i rätt ordning inom sina
fönster. **T3 passerade den på fem cykler av sex.** Skälet är att en
ordningsdom tar den första flanken som passar och sedan slutar titta — en
station som gör om hela sitt arbete håller ordningen perfekt.

Mätt ur T3:s egen serie, cykel 0 (bromsens flanker, sekunder på ögats axel):

```
Stopp RISE 4.5   FALL 6.5      <- forsta stoppet, som facit ville ha det
Stopp RISE 6.9   FALL 12.0     <- och sa gor den om det
Stopp RISE 12.3  FALL 14.3
Stopp RISE 15.0  FALL 17.0
```

Fyra stopp på **samma** produkt. Facit fick därför en **räkning**: hur många
gånger en signal får gå hög under en cykel (`hogst` i `sekvensdom`). Med den
fälls T3 på **varje** cykel, med talet utskrivet.

### Bara stoppet räknas, inte utmatningen

Räkningen ville först gälla båda ställdonen. Då föll **den hela lösningen** —
och den föll på perturbationen, inte på stationen: en driftpaus mitt i
utmatningen släcker `slapp` och tänder den igen när linjen går, så en helt
riktig lösning matar ut två gånger på just den produkt pausen träffade.
Stoppet har inte det problemet — pausen rör det inte.

En grind som fäller den rätta lösningen på sin egen störning mäter störningen.

## Perturbationen måste landa inne i sekvensen

Driftväljaren `kor` slås av i 1,0 s, lika för alla sex körningarna. En
perturbation som bara det trasiga fallet fick hade mätt fallet, inte lösningen.

Första försöket lade pausen 1,0 s efter att **slingan** såg stoppet gå högt.
Slingan ser det först efter ett kopplarvarv, och det tar ett varv till innan
`kor` når PLC:n — så pausen landade när processtiden redan tagit slut, i
utmatningen i stället för i stoppet. Då är T6 inte skild från HEL, och
perturbationen prövar ingenting.

Pausen läggs nu i den **första stoppfas som börjar efter 25 s**, och den syns i
ögats serie (`ST7_Givare/Kor` är en spårad signal). I den godkända körningen:

```
driftvaljaren:            FALL 28.0 s   RISE 29.2 s
HEL cykel 2 (t0 = 27.1):  Stopp FALL 4.8 s   (ovriga nio cykler: 2.4 s)
```

Processtiden förlängdes alltså med precis pausen plus omstarten av `TON`:en,
och stationen fortsatte som förut på nästa produkt. Det är facit för `kor`: en
pausad linje får inte släppa en klämd produkt.

## Utfallet

Grind 1–4 kördes skarpt på **varje** fall. Alla fem passerade alla fyra — ingen
av dem föll före ögat, vilket är precis vad protokollet kräver.

| # | grind 1–4 | ögats dom | ögats egen orsak, ordagrant |
|---|---|---|---|
| **HEL** | alla GODKÄND | **PASS** | `allt inom marginal` |
| **T3** | alla GODKÄND | **FAIL** | `sekvens: stationens sekvens hölls inte: cykel 0: ST7_Don/Stopp gick hog 3 ganger, hogst 1 ar tillatet` (och likadant på 9 cykler av 9) |
| **T4** | alla GODKÄND | **INCONCLUSIVE** | `sekvensen gick inte att döma: ingen RISE-flank pa ST7_Givare/Puls: ingen cykel borjade ens` |
| **T5** | alla GODKÄND | **FAIL** | `forregling: förreglingen bröts` — överlapp **5,50 s** i 66 prov, första vid t = 0,4 s |
| **T6** | alla GODKÄND | **FAIL** | `sekvens: stationens sekvens hölls inte: cykel 2: ST7_Don/Slapp RISE uteblev i fonstret 1.20-6.24 s efter starten` |
| **NOLL** | alla GODKÄND | **FAIL** | `sekvens: stationens sekvens hölls inte: cykel 0: ST7_Don/Stopp RISE uteblev i fonstret 0.00-1.44 s efter starten` (och likadant på 10 cykler av 10) |

### T3 — nivån i stället för flanken

Nio dömda cykler, **nio brott**, alla på räkningen:

```
stopp per cykel:  3 3 3 3 3 3 3 3 4
```

Stationen gör om hela sitt arbete tre gånger på varje produkt. Ordningen håller
varje gång — det är antalet varv som är felet, och det var den insikten som
gav facit sin räkning.

### T4 — timern som startas av sin egen puls

Ögat säger `INCONCLUSIVE`, och skälet är starkare än det låter: **ingen cykel
började ens.** Serien säger varför, utan tolkning:

```
ST7_Don/Stopp    hög i 100,0 % av 1100 prov
ST7_Don/Slapp    hög i   0,0 % av 1100 prov
bromsklacken     y = 5,700 m hela körningen (utskjuten)
produkter i scenen: 1 (ST7_P02), i 110 s
```

Bromsen gick ut och släppte aldrig. Bandet stod, kön bakom växte utanför
fotocellen, och exakt en produkt fanns i scenen under hela mätningen. Det är
inte en obestämbar station — det är en död linje, och ögat säger det med sina
egna tal.

*(Utan uppvärmningen såg ögat T4:s första stopp och fällde den i stället på
`ST7_Don/Stopp FALL uteblev i fonstret 1.20-6.24 s`. Uppvärmningen behövs för
att den hela lösningen ska mätas i jämvikt, och priset är att T4:s dödläge
hinner inträffa innan mätningen börjar. Båda utfallen är fällningar, och båda
står här.)*

### T5 — förreglingen som kommentar

```
förregling ST7_Don/Stopp + ST7_Don/Slapp:
    överlapp 5,50 s i 66 prov, första vid t = 0,40 s, tak 0,10 s  ->  BROTT
```

Taket är seriens eget provintervall: ett överlapp som syns i ett enda prov kan
vara två flanker i samma prov. 66 prov kan det inte vara.

### T6 — rätt på första varvet

**Nio cykler av tio är perfekta.** Den tionde är den som avbröts:

```
driftväljaren:  FALL 30.4 s   RISE 31.6 s
cyk 1 t0=19.00  Stopp RISE 0.6  FALL 2.4  Slapp RISE 2.4  FALL 3.0  Puls FALL 4.2   OK
cyk 2 t0=29.20  Stopp RISE 0.6  FALL 1.8  Slapp RISE ---- MISSING                   BROTT
cyk 3 t0=39.10  Stopp RISE 0.6  FALL 2.4  Slapp RISE 2.4  FALL 3.0  Puls FALL 4.2   OK
```

Pausen kom 1,2 s in i cykel 2. Lösningen nollställde läget, släppte bromsen på
1,8 s i stället för 2,4 — och matade aldrig ut. Produkten passerade
obehandlad, och nästa varv gick som om ingenting hänt. **Exakt en cykel av tio
skiljer den från den hela lösningen**, och det är den cykel perturbationen
träffade.

Ingen förgrind kan se det. Raden `laget := 0;` i `IF NOT kor`-grenen är giltig
ST, rör bara deklarerade taggar, kompilerar, och är dessutom en rad en erfaren
konstruktör skriver av god vana.


### NOLL — facitets nollpunkt

`stopp := stopp AND (givare OR NOT givare);` och en rad till. Programmet rör
alla fem taggarna, skriver varje utgång exakt en gång, och gör ingenting.

```
ST7_Don/Stopp    hög i  0,0 % av 1101 prov
ST7_Don/Slapp    hög i  0,0 % av 1101 prov
ST7_Givare/Puls  hög i 32,2 % av 1101 prov   <- linjen gick, produkter kom
```

Tio cykler började — materialet flödade hela tiden — och **alla tio fälldes**
på att bromsen aldrig gick ut. Det är den nollpunkt M-48 flyttade hit: en tom
kropp fälls redan av grind 3, men det här programmet passerar alla fyra
förgrindarna och kan bara fällas av facit. Med det har facit en undre gräns,
och talen ovanför den betyder något.

## Vad körningen kostade

Sex fall, var och en: VC startas om, programmet kompileras och laddas i
OpenPLC, runtimeprocessen startas om, linjen värms 25 s, och ögat provtar
110 s.

```
kopplarvarv per fall:  367 mätta + 84 under uppvärmningen
varvtid:               median 44-48 ms, p95 59-65 ms, max 108-195 ms
ogats serie:           110,0 s, 1100 prov, 10,00 Hz
```

T5 är den enda som gav **konflikter i anläggningen**: 22 varv där både bromsen
och utmatningen begärdes samtidigt. Anläggningen låter bromsen vinna — en klämd
produkt får inte matas ut — och rapporterar konflikten i stället för att tiga.

## Vad som INTE är prövat

* **Att en modell skriver kropparna.** Alla sex är handskrivna. Fas 7 påstår
  att vägen finns, inte att en språkmodell hittar den; det är fas 9.
* **Reparationsvarv.** Protokollet ber om antalet, och det är noll här av
  samma skäl: ingen modell har fått något fel tillbaka att laga.
* **Nödstoppet.** `nodstopp` går inte att driva över OPC UA (M-49) och stod
  konstant `FALSE`. Vad ST-koden gör när den går hög är oprövat.
* **Fler trasiga fall än fem.** Felklasserna i protokollet är slut, men
  felklasserna i verkligheten är det inte.
