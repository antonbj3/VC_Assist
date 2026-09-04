# M-40 — varför matningen aldrig fyrade: två tysta villkor, inte ett

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · testprefixet
`~/.wine-vc-test`, headless `:99`
**Fas:** 5→7. Blockeraren i M-34 är **löst**. Flödet mäts i
[M-41](M-41_produkten_flodar.md).

## Frågan

M-34 lämnade två tal: `Interval` fyrade aldrig på 160 simulerade sekunder, och
banans behållare var tom. Den här mätningen tar reda på varför.

## Svaret, kort

En `vcComponentCreator` fyrar bara när **båda** dessa håller samtidigt:

1. **Beteendena finns när simuleringen startar.** En matare byggd i en redan
   körande simulering fyrar aldrig, hur rätt den än är kopplad.
2. **Nedströms bana har en verklig längd.** `vcMotionPath.PathLength` är
   `0.0` tills två saker gjorts, och en bana med längd noll tar inte emot
   någonting — så mataren har ingenstans att lämna ifrån sig och producerar
   inte.

Båda är **tysta**. Ingen av dem ger ett fel, ett undantag eller ett falskt
returvärde någonstans. Mätaren står bara still.

## Det kontrollerade provet

Tre linjer byggda i **samma** startskript, alltså alla **före**
`startSimulation()`, alla med samma matare (`Interval = 5.0`, `Limit = 100000`,
`TemplateComponent` = samma blockkomponent) och samma bana (3000 mm, 200 mm/s):

| Linje | Skillnad | `PathLength` vid start | Produkter under 9,8 → 37,8 simulerade sekunder |
|---|---|---|---|
| **M41A** | inget utelämnat | **3000.0** | **8** (skapade vid t = 0, 5, 10, 15, 20, 25, 30, 35) |
| **M41B** | `path.update()` utelämnat | 0.0 | **0** |
| **M41C** | gränssnitten inte kopplade | 3000.0 | **0** |

Sju hela intervall gick i B och C utan att en enda produkt uppstod. Alla tre
matare rapporterade `Enabled = True`, `Interval = 5.0`, `Limit = 100000` och en
`TemplateComponent` med rätt namn hela tiden.

Det fjärde fallet, mätt separat: samma linje byggd i en **körande** simulering,
med `PathLength = 3000.0` och `IsConnected = True` — **noll** produkter från
simtid 62,7 till 96,9 (sju intervall). Samma kod, annat ögonblick, annat utfall.

## Villkor 1: ramarna byggs inte om av sig själva

`vcFeature.PositionMatrix` är RW och tar emot värdet direkt. Men ramens
**verkliga** läge gör det inte:

```
ram = k.RootFeature.createFeature(VC_FRAME, "PathOut")
m = ram.PositionMatrix; m.P = vcVector.new(3000.0, 0.0, 700.0)
ram.PositionMatrix = m

                              PositionMatrix   NodePositionMatrix   FramePositionMatrix
efter tilldelningen           3000,0,700       0,0,0                0,0,0
efter ram.rebuild()           3000,0,700       3000,0,700           3000,0,700
```

`OriginalFramePositionMatrix` visade 3000 hela tiden — den läser den *begärda*
posen, inte den byggda. Att läsa den i stället för `NodePositionMatrix` hade
gett ett grönt svar på en ram som ligger i origo.

Två ramar som båda ligger i nodens origo ger `PathLength = 0.0`, och det var
precis vad M-34:s bana hade.

## Villkor 2: banan räknar inte om sin längd förrän beteendet uppdaterats

Även med ramarna ombyggda:

```
p.Path = [ram_in, ram_ut]      # två ramar, 3000 mm isär, verkligt läge
p.PathLength                   ->  0.0
p.update()
p.PathLength                   ->  3000.0
```

`komponent.update()` och `sim.update()` räcker **inte** — det är
`vcBehaviour.update()` på banbeteendet självt som gör det. Det här är M-11:s
eftersläpning för fjärde gången, men på en storhet ingen tidigare mätt.

## Villkor 3: utgången måste vara kopplad — och det är geometri

`vcSimInterface.canConnect` är en **geometrisk** fråga. Med matarens ut-ram i
origo (ombyggnaden utelämnad) och banans in-ram i origo, båda felaktigt, svarade
`canConnect` ändå `False`. Med ramarna ombyggda och banan placerad så att
banans `PathIn` ligger exakt där matarens `Out` står:

```
canConnect  True     connect  True     IsConnected  True
```

`DistanceTolerance` var `1e9`, så avståndet var inte det som fällde — det var
ett fält med `Port = -1`, se nedan.

## Bindningsordningen: `Container` **före** `Port`

Byggreceptens `_bind` satte flödesfältets `Port` först och `Container` sist.
Resultatet, läst tillbaka ur VC:

```
Port satt till kontaktens Index (0)      ->  0
PortName satt till "Output"              ->  "Output"
Container satt till beteendet            ->  Port ar nu -1
```

Ett fält med `Port = -1` ger `canConnect() == False`. Ingenting sägs. Sätts
`Container` **först** står `Port` kvar på `0` och kopplingen går. `recept._bind`
binder nu i den ordningen.

## Vad som är MOTBEVISAT

**"`Part` måste peka på en URI som går att lösa."** Nej. `TemplateComponent`
tar en komponent som står i scenen, även en byggd programmatiskt med
`Uri = "vcid:"` och `VCID = ""`. Hela M-32:s bygg–spara–ladda-omväg behövs
inte för att få en mall. (`Part` fungerar också: sätter man `Part` till en
`.vcmd`-URI sätts `TemplateComponent` automatiskt till den laddade komponenten.)

**"Produkten måste stoppas in via en `TransportIn`-port."** Nej. Ingen produkt
stoppades in för hand i M-41. Den kopplade `vcOneToOneInterface` räcker.

**"Simuleringen äger inte komponenten förrän den ligger i `app.Components`."**
Nej — de automatiskt skapade produkterna **ligger** i `app.Components` (fyra
komponenter blev sju), och de ligger samtidigt i banans behållare. M-34:s
mätfel var att titta där innan något fanns, inte att listan var fel.

**"En skapare som inte har någonstans att lämna ifrån sig vägrar skapa."**
Det här stämmer — men det är bara halva svaret, och att stanna vid det hade
gett en kopplad linje som fortfarande inte matade (linje M41B).

## Vad som är BEKRÄFTAT och nyanserat

`Limit` stoppar mataren tyst när den nåtts. En matare med `Limit = 10` slutade
producera vid simtid 50 och såg då exakt ut som en trasig matare. Höjdes
`Limit` till 100000 under drift återupptog den nästa intervall (första nya
produkten vid t = 140,065 efter att gränsen höjts vid t = 135,065).

**Den fällan tog jag nästan.** Jag kopplade loss gränssnittet vid t = 73,5,
såg noll produkter i 25 s och var på väg att skriva "utgången är nödvändig".
Mataren hade redan slagit i `Limit` vid t = 50. Provet gjordes om med
`Limit = 100000`: bortkopplat vid t = 161,0 → noll produkter till t = 186,1;
återkopplat vid t = 186,2 → **fortfarande** noll till t = 211,3. Utgången är
alltså nödvändig, och en bruten koppling går **inte** att laga under drift —
mataren tar inte upp takten igen när kopplingen kommer tillbaka.

## Kringfynd som kostade tid

**VC kastar `NameError`, inte `AttributeError`.** Ett saknat attribut ger
`NameError: Attribute or method 'Connectors' not found.` Receptens
`except AttributeError` fångade därför ingenting, och hela `koppla`-receptet
föll på det första gränssnittet i beteendelistan.

**Det heter `RootFeature`, inte `FeatureRoot`.** M-34 skrev fel namn.
`vcFeature.getFeature()` tar dessutom inga argument i den här bindningen —
barnen nås via `RootFeature.Children`.

**`sim`-operationens `do: "restart"` dödar bryggan.** `sim.reset()` +
`startSimulation()` inifrån pumpen gav `simuleringen stoppad` /
`ber om omstart (nr 1) via OnStartStop` i bryggloggen och sedan tystnad;
porten stod kvar som `LISTEN` men ingenting svarade. Listan i M-13 växer med
en rad till, och den enda väg som fungerar är en omstart av VC med
`vc_assist_startskript.py` på plats.

**`vcComponentCreator.create()` är inte samma sak som den automatiska
matningen.** I den fungerande linjen returnerade `create()` `None` medan
`Interval` fyrade helt regelbundet. `create()` prövar sin egen behållares
kapacitet (`Connectors[0].testCapacity()` var `False` i varje mätning, även när
linjen matade). Ett `None` från `create()` säger alltså **ingenting** om
huruvida mataren fungerar.

## Vad som ändrades i produkten

`svc/vc_assist_svc/byggrecept/recept.py`:

* `_ram` gör `f.rebuild()` efter placeringen.
* `_bind` binder `Container` före `Port`/`PortName`.
* `_transportor_rader` gör `bana.update()` efter att `Path` satts.
* `_alla_kontakter` fångar `NameError` lika väl som `AttributeError`.
* nytt recept **`flodeslinje`**: matare + bana, placerade så att ramarna möts
  och kopplade — de tre villkoren i ett anrop.

L1-prov utan VC: `tests/enhet/test_byggrecept.py`.

## Vad som INTE är mätt

* De tre linjerna är byggda och mätta **en gång** var, i ett startskript, i samma
  körning. Ingen upprepning och ingen spridning bakom något av talen.
* Villkoren är mätta som **nödvändiga**, ett i taget utelämnat. Att de tre
  tillsammans är **tillräckliga** är visat för en uppställning — en matare, en
  bana på 3000 mm, 200 mm/s, en produkt. Ett fjärde tyst villkor som råkade vara
  uppfyllt i alla tre linjerna hade inte synts.
* Fönstren är korta. M41A mättes över 9,8 → 37,8 simulerade sekunder, alltså sju
  intervall och åtta produkter. En matare som fyrar oregelbundet över längre tid,
  eller slutar efter tjugo minuter, hade sett hel ut här.
* Att en bruten koppling **inte** går att laga under drift är mätt i ett fall:
  bortkopplad vid t = 161,0, återkopplad vid t = 186,2, noll produkter till
  t = 211,3 — 25 s, fem intervall. Om mataren tar upp takten efter längre tid,
  efter en reset eller efter en omstart är inte mätt.
* Det fjärde fallet (samma linje byggd i en körande simulering) är mätt **en**
  gång, från simtid 62,7 till 96,9. Slutsatsen *"fyrar aldrig"* är alltså
  "fyrade inte på sju intervall".
* Bland de fyra motbevisade påståendena bärs ett av en parentes utan mätrad:
  *"`Part` fungerar också — sätter man `Part` till en `.vcmd`-URI sätts
  `TemplateComponent` automatiskt"*. Det redovisas inte som en mätning någonstans
  i texten.
* Förklaringen till `create()`:s `None` — att den prövar sin egen behållares
  kapacitet — är en tolkning. `testCapacity` var `False` i varje mätning, även
  när linjen matade, och vad den storheten mäter är fortfarande omätt (M-34).
* Ändringarna i `svc/vc_assist_svc/byggrecept/recept.py` provas av
  `tests/enhet/test_byggrecept.py`, **utan VC**. I VC är bara receptet
  `flödeslinje` kört, en gång. De fyra övriga punkterna i listan är prövade som
  kod, inte som verkan.
* `DistanceTolerance = 1e9` avfärdar avståndet som orsak i **det** provet. Vilken
  geometrisk tolerans som gäller vid ett normalt värde är inte mätt, och
  `canConnect` beskrivs ändå som en geometrisk fråga.
