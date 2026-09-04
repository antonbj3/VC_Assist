# M-42 — PLC:ns värden på ögats tidsaxel: klockvalet, fördröjningen, och hålet

**Datum:** 2026-09-04 · Linux 6.8 · CPython 3.13.11 · **utan VC, utan PLC, utan nät**
**Mätt av:** `tests/enhet/test_ogonkoppling.py` (17 prov, körs med `pytest -s`)
**Stänger:** M-39:s öppna rad *"Ingen tidsstämpling till ögat. Ögat har
gränssnittet (`Plckalla.skjut_in`), kopplaren använder det inte."*

## Frågan

Ögat samplar scenen inne i VC och stämplar varje rad i **simuleringstid**.
Kopplaren läser PLC:n i tjänsten och räknar i **väggklocka**. De tickar i olika
takt, på olika sidor av processgränsen. En tidsstämpel från den ena betyder
inte samma sak som en från den andra — och hela poängen med ögat är att en
PLC-flank och en fysisk rörelse ska gå att lägga bredvid varandra.

## Riggen

Allt utom de två ändarna är den riktiga koden:

```
Kopplare -> Ogonkoppling -> Klient -> sockel -> Brygga.tick() -> Provtagare
   ^                                                                 ^
 falsk OPC UA, falsk scenbrygga                                 falsk scen
```

Pumpen drivs av en tråd i stället för VC:s `OnRun` (samma grepp som
`test_brygga.py`; på Linux svälter trådar inte som i VC, M-07) och matas med en
**styrbar simuleringsklocka**. Det är riggens hela värde: förhållandet mellan
simuleringstid och väggklocka går att sätta till 1, till 10, att låta gå i
språng, och att nolla mitt i — precis det VC gör med `app.startSimulation()`,
`sim.run()` och `sim.reset()`.

## 1. Klockvalet: simuleringstiden, och bron är en varaktighet

**Den gemensamma klockan är simuleringstiden.** Två skäl, båda med tal:

1. Ögats serie är redan stämplad i den: `rad["t"] = simtid - t0`. Fysiken i
   scenen rör sig i simuleringstid, inte i väggklockstid.
2. De två klockorna är **inte** samma sak, och skillnaden är inte liten.
   M-08 mätte kvoten till **1,000** med `app.startSimulation()` — men samma
   mätning visade `sim.run(t)` köra **20 simulerade sekunder på 0,01 s**, en
   kvot på 2000. Ögat använder båda körsätten.

Bron mellan klockorna är därför en **varaktighet, aldrig en tidpunkt**:
kopplaren skickar värdets ÅLDER i sin egen klocka, och pumpen räknar om den
till simuleringstid med sin egen mätta takt.

En varaktighet behöver ingen delad epok. En tidpunkt gör det — och epoken
överlever inte ett `sim.reset()`, som bryggan själv gör efter varje
scenändring. Ett värde stämplat med en absolut tid hade efter en omstart legat
i framtiden och blivit **det färskaste värdet i hela serien**.

Prov: `test_aldern_raknas_i_simuleringstid_inte_i_vaggklockstid` kör riggen med
takten 10. Pumpen mäter takten till 10 (±0,5), en ålder på **0,2
väggsekunder** blir **2,0 simulerade sekunder**, och raden får ett hål.
Räknat i väggklocka hade samma värde sett färskt ut i en serie där två
sekunder redan gått.

### Takten mäts, den antas inte

`Brygga.takt()` räknar simulerade sekunder per väggklockssekund ur pumpens egna
tick-par. Takten går in **multiplikativt** i varje ålder, så ett taktfel på
10 % är ett åldersfel på 10 %. Fönstrets längd är därför en mätning:

| Fönster | Värsta taktfel | Medelfel | Släpar efter |
|---|---|---|---|
| 2 par | **0,971** | 0,046 | 5 ms |
| 5 par | 0,233 | 0,043 | 20 ms |
| 10 par | 0,095 | 0,033 | 45 ms |
| **20 par** | **0,044** | 0,023 | 95 ms |
| 40 par | 0,024 | 0,009 | 195 ms |

(Simuleringstiden går i språng om 5 ms i den här mätningen. Det är inte ett
påhitt: M-08:s logg visar `sim=1.00` på exakt 20 varv med `delay(0.05)`,
alltså ett helt delay-kvantum per varv.)

**Två par är inte en takt** — värsta fallet ligger på 97 % fel, alltså nästan
en faktor två. Vid 20 par är felet 4,4 %, vilket flyttar en ålder på 0,25 s med
högst 11 ms. `TAKTFONSTER = 20`.

Går takten inte att mäta alls (ingen simulering, eller klockan just nollad) blir
tidsstämpeln `None`, och ögat räknar värdet som gammalt. Fail-closed:
`test_utan_matt_takt_far_vardet_ingen_tidsaxel_och_raknas_som_gammalt`.

## 2. Fördröjningen d, och att den lutade åt fel håll

`d` = skillnaden mellan den simuleringstid ögat stämplar värdet med och den
simuleringstid värdet **faktiskt lästes** vid. Riggens simuleringsklocka är en
känd funktion av väggklockan, så den sanna tidpunkten är känd — det är därför
felet går att mäta alls.

```
d < 0   ögat tror värdet är äldre än det är    (konservativt)
d > 0   ögat tror värdet är färskare än det är (farliga hållet)
```

**200 varv, takt 1,0000:**

| | median | p05 | p95 | min | max |
|---|---|---|---|---|---|
| d **utan** kompensation | **+5,09 ms** | — | +5,13 ms | — | +7,58 ms |
| d **med** kompensation | **−0,23 ms** | −3,37 ms | −0,13 ms | −8,32 ms | +1,83 ms |
| kopplarvarvet, tur och retur | 5,22 ms | — | 5,67 ms | — | 10,09 ms |

Första raden är fyndet: **hopfogningen lutade systematiskt åt det farliga
hållet**, +5,1 ms i median över tre oberoende körningar (+5,08, +5,09, +5,11).
Talet är inte nätverket — det är väntan på pumpens nästa slag. Åldern mäts när
inskottet skickas, och värdet stämplas när pumpen nästa gång vaknar.

Vägen ut går inte att tidta utan en klocka båda sidor delar. Men den är per
definition aldrig längre än en hel tur och retur, och den mäter vi. Därför
skickar `Ogonkoppling.skjut_in` åldern som

```
alder = (nu - t_las) + rtt_tak()        # rtt_tak = max av de 8 senaste turerna
```

Efter det ligger medianen på **−0,23 ms**, alltså på den konservativa sidan.
Systematiken har bytt tecken. Jitteret är kvar och påstås inte bort: **2,5 %**
av varven hamnar ändå över noll, som mest +1,8 ms.

**Osäkerheten i hopfogningen** är alltså ±3,4 ms (p05–p95 med kompensation), med
enstaka utfall ut till −8,3/+1,8 ms. Mot färskhetsfönstret `PLC_FARSK_S = 0,25 s`
är det under 4 %. Vore osäkerheten i samma storleksordning som fönstret vore
`plc_gammal` brus och inte ett mått.

### Vad som ligger utanför d, och som d inte påstår sig mäta

* **PLC:ns egen skanfördröjning.** M-20 mätte den till 40,0 ms vid 20 ms
  skanperiod. Den ligger FÖRE kopplarens läsning, alltså före stämpeln, och
  ingår inte i `plc_alder_s`. Serien säger hur gammalt värdet är räknat från
  läsningen — inte från insignalens flank i PLC:n.
* **Riggens brygga är snabbare än VC:s.** Här är tur och retur 5,2 ms median;
  M-03 mätte den mot VC till 9,9 ms. Talen ovan mäter *mekanismen*, inte
  produktionsvägen. Kompensationen skalar dock med det mätta värdet: en
  långsammare brygga ger ett större `rtt_tak()` av sig själv.

## 3. Tappad kontakt: två mekanismer, för att det finns två sätt att dö

En serie som visar inaktuella PLC-värden utan att märka dem är värre än en som
visar hål. Kopplaren kan dö på två sätt, och de kräver olika svar.

**a) Kopplaren lever men får inget svar.** Den säger ifrån själv. Redan det
FÖRSTA fallna varvet skickar `bryt("kopplarvarv N foll: ...")`, och när den ger
upp efter tre raka fel (`MAX_RAKA_FEL`, M-39) skickar den ett sista
`bryt("kopplaren gav upp efter 3 raka fel; ...")` **innan** `Kopplarfel`
kastas. Ögat släpper då värdena: raden får `plc_avbrott` med skälet och
`plc_gammal`, och **inga** tal.

Prov: `test_kopplaren_som_ger_upp_sager_det_till_serien_och_slapper_vardena`.
Ett färskt värde som visades i raden före är borta ur raden efter. Och
`test_ett_varv_som_lyckas_igen_tar_tillbaka_vardena`: avbrottet är inte ett
dödsbud — en återkommen kopplare syns som återkommen, annars vore hålet lika
osant som de gamla talen.

**b) Kopplaren dör tvärt och hinner inte säga någonting.** Tystnad går inte att
skilja från "inget nytt har hänt", så ögat har ett eget tak. Mätt utfall efter
det sista inskottet:

| Ålder | Vad raden visar |
|---|---|
| < 0,25 s (`PLC_FARSK_S`) | värdet, med `plc_alder_s` |
| 0,25–0,50 s | värdet, med `plc_gammal` — analysen dömer INCONCLUSIVE |
| **> 0,50 s** (`PLC_TYSTNAD_S`) | **inget värde alls**: `plc_avbrott` + `plc_gammal` |

Mätt: sista visade värdet 0,490 s gammalt, första hålet vid 0,500 s. Taket slår
på taket och ingen annanstans.

**c) Klockan flyttar sig bakåt.** `sim.reset()` nollar simuleringstiden.
Stämpeln ligger då i framtiden. Åldern klipps INTE till noll — det vore det
färskaste värdet i serien. Raden får `plc_avbrott: "tidsstampeln ligger N s i
framtiden; klockan har gatt bakat"`. Pumpen kastar samtidigt sitt taktfönster,
så takten inte räknas över hoppet (`test_pumpen_kastar_taktfonstret...`).

**d) Inskottet kommer inte fram.** Ögat får aldrig fälla kopplarens varv — men
felet tigs inte ihjäl: `Varv.oga_fel` och `sammanfattning()["ogafel"]` bär det,
och serien lämnas åt sitt tystnadstak i (b).

**e) Ögat provtar inte.** Bryggan svarar `{"oga": false, "lagrat": false,
"skal": "ogat provtar inte"}`. Ingen falsk framgång: ett värde som inte
lagrades får inte se ut som ett som gjorde det.

## Trösklar som mätningen sätter

| Konstant | Fil | Värde | Skäl |
|---|---|---|---|
| `PLC_TYSTNAD_S` | `oga_provtagning.py` | 0,50 s | Måste ligga över de ~315 ms tre raka fallna varv tar (M-39: p95 105 ms/varv × `MAX_RAKA_FEL` 3), annars slår taket på en kopplare som lever och är på väg att säga ifrån själv. Marginalen upp till 0,5 s är 185 ms. Mätt utfall: hålet kommer 0,500 s efter sista inskottet. |
| `PLC_BAKAT_TOL_S` | `oga_provtagning.py` | 0,001 s | Skiljer avrundningsbrus från en klocka som gått bakåt. Seriens tider avrundas till 4 decimaler (1e-4 s), så tröskeln ligger en tiopotens över bruset; ett verkligt `sim.reset()` hoppar hela den gångna simuleringstiden, i mätningen 0,3–1,1 s, alltså tre tiopotenser över tröskeln. |
| `TAKTFONSTER` | `pump.py` | 20 par | Tabellen i avsnitt 1: 2 par ger 97 % taktfel, 20 par 4,4 %, och 40 par bara 2,4 % till priset av att släpa 195 ms efter ett regimbyte. |
| `KOMPENSATIONSFONSTER` | `ogonkoppling.py` | 8 turer | Kompensationen är `max` av fönstret. Det ska rymma en hicka utan att bära med sig en gammal: 8 turer är ~40 ms av kopplarens historik i riggen, ~80 ms mot VC:s brygga (M-03). Med det ligger 97,5 % av varven på den konservativa sidan. |

## Vad som INTE är mätt

* **Mot en levande VC.** Riggen mäter mekanismen, inte produktionsvägen.
  `PLC_FARSK_S` står kvar som PRELIMINÄR med **M-19** som ägare: den ska sättas
  mot fördröjningen mellan en verklig OPC UA-läsning och simuleringstiden i
  VC. Den här mätningen är ett golv för det talet, inte talet.
* **Epokfrågan är kringgången, inte besvarad.** Om VC:s `time.time()` under
  Wine delar epok med tjänstens är fortfarande omätt. Konstruktionen behöver
  inte veta det — den skickar varaktigheter — och det är därför frågan får stå
  öppen.
* **Flera kopplare mot samma öga.** Det sista inskottet vinner; ingen
  sammanslagning är byggd och ingen är prövad.
* **Windows.**
