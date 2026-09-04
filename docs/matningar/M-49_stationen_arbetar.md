# M-49 — stationen som arbetar, och de två klockorna som inte går lika

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · testprefixet
`~/.wine-vc-test`, headless `:99` · OpenPLC v4.2.1 · STruC++ 0.6.6
**Fas:** 7, andra halvan. Grind 1–4 mättes i
[M-48](M-48_grind_1_till_4_skarpt.md); här kommer ögat.
**Körs av:** `tests/protocol/kor_fas7_station.py`
**De trasiga fallen ligger i:** [M-50](M-50_de_trasiga_fallen.md)

## Vad som byggdes

En station på flödeslinjen från [M-41](M-41_produkten_flodar.md): en matare som
skapar en produkt var tionde sekund och en 3000 mm bana som för den framåt i
250 mm/s. Ovanpå det:

* en **fotocell** vid banavstånd 1200 mm, ±400 mm,
* en **broms** som stoppar bandet och en **utmatning** som kör det snabbt,
* en **bromsklack** som går ut och in — det enda objekt PLC:n kommenderar och
  som ögat kan se röra sig,
* en signalkarta med fem taggar, varav en `skyddad`.

Sekvensen som ST-koden ska åstadkomma, deklarerad **före** lösningarna skrevs:
produkten når fotocellen → bromsen ut inom transporttiden → processtiden 2 s →
bromsen släpper → utmatningen 0,5 s → produkten lämnar stationen. Och: bromsen
och utmatningen får aldrig vara höga samtidigt.

## Två saker som simuleras av tjänsten, och varför

**Fotocellen och ställdonen bor i tjänsten, inte i VC.** Det är inte en genväg
utan följden av tre mätningar:

| Vägen in i VC | Utfall |
|---|---|
| `VC_SCRIPT`-beteende som läser signalen och rör banan | **stoppar simuleringen och dödar bryggan** (M-13) |
| `VC_COMPONENTPATHSENSOR` | går att skapa, men är en bar `vcBehaviour` utan mätt Python-yta (M-15); oprövat räknas som saknat (I3) |
| `VC_PROPERTYSIGNALADAPTER` | inte bland de 80 skapbara i M-15:s svep |

Anläggningen kör därför som kod inne i VC genom godkännandekön, en gång per
varv: den läser produkternas **verkliga** banavstånd (`getPathDistance`, samma
mått som M-41 mätte rörelsen med), sätter fotocellens signal, läser PLC:ns
utgångar ur scenen och skriver bandets **verkliga** fart. Ingen sekvenslogik
bor där — den bor i PLC:n, där den ska prövas.

**Bandet stannar på riktigt.** Mätt direkt, före allt annat:

```
speed 250.0  ->  banavstand 130.0  131.3  135.0  (rör sig)
Path.Speed = 0.0
speed   0.0  ->  banavstand 140.0  140.0  140.0  140.0  (står still)
Path.Speed = 250.0
speed 250.0  ->  banavstand 143.8  146.3  148.8  151.3  (rör sig igen)
```

`vcMotionPath.Speed` är alltså ett ställdon som går att skriva under körning,
och produkten står still när den är noll.

## Anläggningssteget kostar 27 ms

Nittio steg genom godkännandekön, mätt i väggklocka:

```
anlaggningssteg:  median 27.0 ms   p95 38.3 ms   max 47.8 ms   n=90
```

## Tre fel i kedjan som hittades genom att köra den

### 1. `START:OK` på en körande PLC byter inte program

M-20 mätte att `START:OK` är ett kvitto på begäran, inte på körning. Det här är
den andra halvan: **`RUNNING` betyder inte att det är ditt program som kör.**

Uppladdningen lyckades, bygget lyckades (`SUCCESS`, exit 0), `conf/opcua.json`
kopierades med stationens fem noder — och OPC UA-servern svarade fortfarande
med förra körningens adressrum:

```
noder: ['Locations', 'Server', 'Aliases', 'matin', 'matut']
```

`matin`/`matut` är M-39:s program. Kopplaren läste då `None` för varje tagg,
skrev ingenting, och slingan såg ut att arbeta medan stationen aldrig fick en
enda insignal. **Ingenting sa ifrån.**

Att stoppa PLC:n före uppladdningen räckte inte heller:

```
stoppar: OK -> TRANSITIONING
kompilering: SUCCESS
startar: RUNNING
noder: [..., 'matin', 'matut']        <- fortfarande de gamla
```

Först en omstart av **hela runtimeprocessen** bytte adressrummet:

```
docker restart vcassist-openplc-v4
noder: ['Locations', 'Server', 'Aliases', 'givare', 'kor', 'nodstopp', 'stopp', 'slapp']
```

OPC UA-pluginet läser alltså sin konfiguration när processen startar, inte när
PLC:n startar. Körningen startar därför om runtimen efter varje uppladdning,
och `UaKanal.anslut()` **kräver** att varje tagg i kartan finns som nod innan
slingan får börja. En kopplare som svarar `None` tyst är värre än en som faller.

### 2. En skyddad ingång går inte att driva över OPC UA

`opcuakonfig.variabel` ger en `skyddad` tagg endast läsrättigheter. En
`WriteRequest` mot den svarar `BadInternalError`, och kopplaren gav upp efter
tre raka fel — M-39:s spärr gjorde precis sitt jobb:

```
Kopplarfel: kopplaren gav upp efter 3 raka fel; sista: BadInternalError
```

Det är rätt beteende och rätt gräns: säkerhetskedjan hör inte till den
genererade logiken (I15), den bor på en certifierad säkerhets-PLC som logiken
får ligga bredvid. Körningen driver därför inte `nodstopp` — den läses av
ST-koden och står konstant `FALSE` i scenen. **Det är en oprövad kant**, och
den står i "vad som inte är visat" nedan.

### 3. Kopplarens eget inskott i ögat är för sent

Kopplaren skjuter in PLC-värdena i ögats serie **efter** scenskrivningen
(`kopplare.kor_varv`). När pumpen är belastad kan en köad scenskrivning ta
sekunder, och värdet landar då i serien med den åldern:

```
t=   5.90 alder=0.2952
t=   5.95 alder=7.1723  ingen ny ogonblicksbild pa 7.17 s
```

Slingan läser och skjuter in själv i stället, direkt efter varandra, och säger
ifrån med `bryt()` när kopplaren ger upp.

## De två klockorna — och att glappet var vårt eget

PLC:ns timers räknar i **väggklocka**. Ögats serie är stämplad i
**simuleringstid**. Med bryggan obelastad är kvoten 1,000 (M-08). Under
körningen var den det inte, och det syntes rakt igenom på stationens
processtid: **samma `T#2s` i PLC:n mättes till mellan 0,30 s och 4,55 s på
ögats axel** — en faktor 15 inom och mellan körningar.

Mätt, tio sekunder i taget, medan slingan gick:

| Vad bryggan gjorde | simtid / väggtid |
|---|---:|
| ingenting | 1,000 |
| ett anläggningssteg så fort det går (53 varv/10 s) | **0,080** |
| ett anläggningssteg + 150 ms paus (29 varv/10 s) | **1,907** |

Den första slutsatsen var fel: att slingan i sig är för dyr och att fasen
därför inte kan mäta tid. **Orsaken var vår egen pollning.**

`Klient.godkann_och_vanta` frågar `queue_list` tills posten fått ett utfall.
`_op_queue_list` serialiserar **hela kön, med varje posts kod och svar**, och
kön växer med en post per varv. Varje fråga blev alltså dyrare än den förra,
och frågorna kom flera gånger per varv. Till slut föll den helt:

```
BryggFel: E_TOO_LARGE: svaret ar storre an 1048576 byte     (kö: 1533 poster)
```

Det är två fel i ett: kön är obegränsad, och `queue_list` har ingen väg att
fråga om **en** post. Slingan frågar nu utan kod och utan svar
(`with_code=False, with_result=False`), och startar om VC mellan fallen så att
kön börjar tom. Med det mättes kvoten i tre driftpunkter i rad:

```
varvtid 0,30  tathet 0,10  ->  sim 45,4 / vagg 45,4 = 1,000   (378 ms/varv, 359 inskott)
varvtid 0,60  tathet 0,15  ->  sim 45,4 / vagg 45,5 = 1,000   (689 ms/varv, 264 inskott)
varvtid 1,00  tathet 0,20  ->  sim 46,0 / vagg 46,0 = 1,000   (1096 ms/varv, 209 inskott)
```

**1,000 i alla tre.** Simuleringen går i realtid med slingan sluten, och
fönstren i facit kunde därför göras snäva (`KLOCKA_LAG = 0,6`,
`KLOCKA_HOG = 1,6`) i stället för att spänna en faktor 15.

Lärdomen är inte att pollningen var slarvig. Den är att **mätinstrumentet låg
i mätvägen**: frågan "är du klar?" kostade mer än arbetet den väntade på, och
kostnaden växte med körningens längd. En körning som blir långsammare ju
längre den går mäter till slut sin egen pollning.

## Skärmen: ett ärvt `DISPLAY` är inte ett standardvärde

Den första omstarten av VC använde `os.environ.get("DISPLAY", ":99")`. Miljön
bar `:1` — operatörens skärm — och VC startade där, mätt ur processen:

```
pid 650400  DISPLAY=:1
```

Raden ser ut som ett standardvärde och är det inte: den ärver, och det som
ärvs är precis det som är fel. Körningen sätter nu skärmen uttryckligen och
**läser tillbaka** den ur `/proc/<pid>/environ` efter start; hamnar den fel
avbryts körningen. Processlistan går inte längre genom `pgrep -f`, som träffar
sin egen sökning.

Efter rättelsen, avläst ur processen:

```
pid 654662  WINEPREFIX=/home/anton/.wine-vc-test  DISPLAY=:99
```

## Vad som INTE är visat

* **Nödstoppet.** Den skyddade ingången kan inte drivas från kopplaren och står
  konstant `FALSE`. Att ST-koden gör rätt när den går hög är oprövat.
* **Att simuleringen kan gå i realtid med slingan sluten.** Kvoten mättes till
  0,08–1,9 beroende på last. Ingen konfiguration hittades där den står stilla
  på 1,0 medan slingan går.
* **Fler än en station.** Fas 8.
* **Hur ofta det lyckas.** Ett grönt varv är inte en frekvens. Fas 9.
* **Windows.**
