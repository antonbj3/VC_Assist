# M-34 — produkten finns; jag mätte på fel lista

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Fas:** 5. Blockeraren är flyttad, och ett mätfel av mig är rättat.

## Mätfelet först

Jag har i tolv körningar mätt "skapades någon produkt?" som

```python
len(list(app.Components))
```

och fått samma tal före och efter. Slutsatsen blev *"mataren matar inte"*, och
den skrevs in i M-32.

Den var fel. En produkt som en `vcComponentCreator` skapar ligger i
**beteendets egen behållare**, inte bland scenens toppnivåkomponenter:

```
create()              ->  vcComponent
namn                      "Produkt"
uri                       vcid:40fc7ea5-80a7-4956-8eda-32fe734e3f70
app_Components            ["Bana", "Matare", "VcAssistBridge"]     <- oförändrad
skaparens_innehall        ["Produkt"]                              <- HÄR
```

VCID:t är samma som den sparade `Produkt.vcmd` fick (M-32). Mataren skapar
alltså en riktig instans av vår egenbyggda komponent.

Instrumentet mätte fel storhet, och svarade konsekvent och trovärdigt fel tolv
gånger i rad. Ett tal som inte rör sig är inte ett bevis på att ingenting händer
— det kan lika gärna vara ett bevis på att man tittar på fel ställe.

## Vad som därmed är mätt

| Fråga | Svar |
|---|---|
| Kan en egenbyggd komponent bli en produkt? | **Ja.** Bygg → spara → ladda → `Part`-URI → `create()` |
| Skapar `create()` något? | **Ja**, en `vcComponent` med rätt VCID |
| Var hamnar den? | i skaparens egen behållare |
| Fyrar den automatiska matningen (`Interval`)? | ~~**Nej.** Behållaren är tom över 160 simulerade sekunder~~ **RÄTTAD, se nedan** |
| Flödar produkten vidare till banan? | ~~**Nej.** Banans behållare är tom~~ **RÄTTAD, se nedan** |

> **RÄTTELSE 2026-09-05.** De två sista raderna är falska som allmänna svar.
>
> `M-40` mätte att en matare fyrar när **båda** dessa håller: beteendena finns
> när simuleringen startar, och nedströms bana har en verklig längd
> (`PathLength > 0`, vilket kräver `bana.update()`). Båda är tysta — ingendera
> ger fel, undantag eller falskt returvärde någonstans.
>
> Den här mätningens matare byggdes i en **körande** simulering, alltså precis
> det villkor som gör att en matare aldrig fyrar. Raderna mätte
> **uppställningen**, inte mataren.
>
> `M-41` visade sedan flödet i tal: nio produkter, exakt 4,000 s isär, åtta
> mellanrum i rad, hastighet 250,0000 mm/s med spridning 0,0000 över 25
> differenskvoter.
>
> Rättelsen stod sedan tidigare i filens ärlighetsavsnitt längst ned. Den står
> nu **vid påståendet**, eftersom en läsare som stannar vid tabellen annars får
> fel svar — samma fel som fas 6:s rubrik gjorde i ett dygn.

## Kringliggande mätningar från samma svep

**Kontaktkopplingen sitter.** `ut.Connection = Input`, `inn.Connection = Output`
mellan skaparens utgång och banans ingång. `vcConnector` har **ingen**
`IsConnected` — kopplingen läses ur `Connection`, som är `None` när fri.

**`testCapacity` är `False` på båda sidor**, även under drift, trots
`Capacity = 999999`. `testConnectedCapacity` är däremot `True` på de fria
kontakterna. Betydelsen är omätt.

**En bana behöver ramar.** `vcMotionPath.Path` är
`List<Ref<FrameFeature>>` och är tom vid skapandet. Ramar går att skapa:
`komponent.FeatureRoot.createFeature(VC_FRAME, namn)` ger en `vcFrameFeature`,
och listan går att sätta med `p.Value = [ram1, ram2]`.

**Bara en av fyra transportstyrenheter går att skapa:**

| Konstant | Utfall |
|---|---|
| `VC_CONVEYORTRANSPORTCONTROLLER` | `None` |
| `VC_INTERPOLATINGTRANSPORTCONTROLLER` | `None` |
| `VC_TRANSPORTCONTROLLER` | `None` |
| **`VC_PYTHONTRANSPORTCONTROLLER`** | **`vcPythonTransportController`** |

Den skapades utan att bryggan dog, till skillnad från `VC_SCRIPT` (M-13).

**`vcMotionPath.Speed` är 200.0 som standard.** I millimeter per sekund är det
12 m/min, en normal transportörshastighet. I meter per sekund vore det 720 km/h.
Ännu en bekräftelse på M-33: världen är i millimeter.

## Var det står

En produkt kan **skapas** programmatiskt. Den kan ännu inte fås att **flöda**.

Den återstående misstanken är att en bana behöver en transportstyrenhet för att
bära något, och att bara den pythonbaserade går att skapa — vilket betyder att
en fungerande transportör kräver att vi skriver dess styrlogik själva.

Det är prövbart i uppstartsskriptet, där ett beteende är ofarligt att lägga till.

## Vad som INTE är mätt

* Varje rad i tabellen är **en** observation ur ett svep, inte en upprepad
  mätning.
* *"Fyrar den automatiska matningen? **Nej**"* är mätt över 160 simulerade
  sekunder på en matare byggd i en **körande** simulering. M-40 mätte att just
  det villkoret gör att en matare aldrig fyrar. Svaret gällde uppställningen, inte
  mataren — och mätfelet i den här filens egen ingress hade alltså en tvilling i
  dess viktigaste tabellrad.
* Slutsatsen i *Var det står* — att en bana kräver en transportstyrenhet, och att
  vi därför måste skriva styrlogiken själva — är en **misstanke**. Den håller inte:
  M-40 fick linjen att mata genom att bygga beteendena före start, bygga om
  ramarna och anropa `bana.update()`. Ingen transportstyrenhet skrevs.
* `testCapacity = False` på båda sidor även under drift står som *"betydelsen är
  omätt"*, och den är omätt än. M-40 mätte bara att `create()`:s `None` inte säger
  något om mataren, inte vad `testCapacity` mäter.
* Mätfelet är rättat för `len(app.Components)`. Var det talet användes på andra
  ställen är inte genomsökt — tolv körningar hann bygga slutsatser på det, och
  bara M-32:s punkt 6 är utpekad som rättad.
* De fyra transportstyrenheterna prövades med ett argumentlöst `createBehaviour`,
  en gång var. Samma begränsning som M-15: `None` betyder "inte skapbar så här",
  inte "finns inte".
* Att `VC_PYTHONTRANSPORTCONTROLLER` skapades *"utan att bryggan dog"* är mätt en
  gång. M-13:s lista över dödande anrop växer med mätning, inte med principer.
