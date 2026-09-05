# M-101 — komponentmodellen byggd ur specen och prövad i riktig VC

**Datum:** 2026-09-05 · VC Premium 4.10 · Wine 11.16 · testprefixet
`~/.wine-vc-test`, headless `:99`
**Fas:** 20
**Körs av:** `tests/protocol/kor_fas20_modellen.py`
**beskriver:** `docs/spec/49_komponentmodellen.md` (avsnitt 7–11),
`svc/vc_assist_svc/komponentmodell.py`, `tests/enhet/test_komponentmodell.py`
**Föregångare:** [M-40](M-40_varfor_mataren_aldrig_fyrade.md) (två tysta
villkor), [M-41](M-41_produkten_flodar.md) (flödet),
[M-67](M-67_kopplingen_ar_logisk.md) (kopplingen flyttar ingenting)

**Grön.** Fyra minsta uppsättningar byggda ur specen, elva kopplingsförsök,
och materialet rör sig hela vägen igenom — 13 produkter, 2 + 1 + 10, räkningen
går ihop.

Tre påståenden föll på vägen: ett ur `api.xml` (`ContentVisible`), ett ur den
här specens eget **MÄTT**-märke (klassnamnen) och en läsning av M-40
(`Port = -1`). Att bygga ur en spec är det som hittar dem; att läsa den är det
inte.

## Frågan

`49_komponentmodellen.md` svarade på A–G i **text**. Vad en TRANSPORTÖR minst
behöver, vad som krävs för att `canConnect` blir sant, hur ett fält binds — allt
belagt eller mätt, ingenting byggt **ur** specen. En spec som aldrig byggts är
en hypotes med tabeller.

Fas 20 vänder riktningen: kravlistorna ligger som **data** i
`komponentmodell.py`, VC-koden **genereras ur dem**, och ett prov faller om
specens tabeller och modellens data glider isär — i båda riktningarna.

## Uppställningen

Kedjan är alla fyra klasserna i **ett** flöde, placerade så att ramarna
sammanfaller:

```
F20_Matare  ->  F20_Bana  ->  F20_Buffert  ->  F20_Sanka
 matare          transportör    buffert         sänka
 400 mm          2000 mm        1000 mm         400 mm
 Interval 3 s    400 mm/s       400 mm/s        Capacity 1e6
```

Utöver kedjan tolv komponenter till: per klass en **motpart**, en **trasig**
(ett krävt beteende utelämnat) och en **hel tvilling** på exakt samma plats i
världen. Sexton komponenter, elva kopplingsförsök, allt i ett startskript som
`bridge_cmd` kör före `startSimulation()` — beteenden som läggs till i en redan
körande simulering initieras aldrig (M-40 villkor 1).

## Fynd 1 — `ContentVisible` finns inte, och tog med sig hela startskriptet

`api.xml` dokumenterar `vcContainer.ContentVisible` (W): *"Sets the visibility
of components stored in the container."* Det beteende `VC_COMPONENTCONTAINER`
faktiskt ger — `vcSimContainer` — **bär den inte**:

```
NameError: Attribute or method 'ContentVisible' not found.
```

Det är VC:s `NameError`, inte Pythons `AttributeError` — samma fälla som M-40
beskrev för `Connectors`. Tilldelningen stod oskyddad i byggkoden, så
undantaget tog med sig **hela resten av startskriptet**: tre komponenter av
sexton byggdes, noll av elva kopplingar provades, och en hel VC-omstart gick
till spillo på en kosmetisk egenskap som ingen dom hängde på.

Två saker ändrades av det, och den andra är den viktiga:

1. `ContentVisible` är **inte längre ett krav** på sänkan. Ett krav som inte går
   att uppfylla är inget krav. Raden står i stället i specens avsnitt 11,
   *Vad mätningen har refuterat*, med sin källa och sitt utfall.
2. **Varje egenskapstilldelning går nu genom `_steg()`.** En egenskap som inte
   finns är ett mätvärde, aldrig ett haveri. Modellen hade redan den regeln för
   gränssnitten och inte för egenskaperna — och det var precis där den brast.

Tilldelningen står kvar i den genererade koden **som mätning**. Slutar den
falla har bindningen ändrats, och det vill vi se.

## Fynd 2 — en belagd rad är inte en mätt rad

`ContentVisible` bar märkningen **BELAGT** med ett ordagrant citat ur `api.xml`.
Citatet är riktigt. Påståendet är ändå falskt för det objekt vi faktiskt får,
därför att `api.xml` beskriver **typen** `vcContainer` medan py2-bindningens
instans är något annat. Märkningen BELAGT säger att en källa påstår något — inte
att VC gör det.

Det är inte ett skäl att sluta belägga. Det är ett skäl att låta varje belagd
rad som **styr ett bygge** bli mätt, och att bygget ska överleva att den inte
är det.

## Resultat: kedjan och de fyra trasiga fixturerna

Körningen `kor_fas20_modellen.py --starta-om --prov 18`, 2026-09-05 08:47.
Sexton komponenter i ett startskript, `startSimulation()` efteråt.

### 1. De fyra minsta uppsättningarna

Alla fyra byggda ur specen, alla fyra **HELA** enligt `granska()`. Värdena är
lästa **tillbaka** ur VC, inte de vi skickade:

| Komponent | Klass | Beteenden VC gav | Återläst |
|---|---|---|---|
| `F20_Matare` | matare | `Creator`, `OutInterface` | `Interval` 3.0, `Limit` 1000000, `Enabled` True, `TemplateComponent` `F20_Produkt` |
| `F20_Bana` | transportör | `Path`, `InInterface`, `OutInterface` | **`PathLength` 2000.0**, `Speed` 400.0, `Accumulate` False, `Capacity` 999999 |
| `F20_Buffert` | buffert | `Path`, `InInterface`, `OutInterface` | **`PathLength` 1000.0**, `Speed` 400.0, `Accumulate` True, `Capacity` 10 |
| `F20_Sanka` | sänka | `Sink`, `InInterface` | `Capacity` 1000000 |

`Capacity` 999999 på transportören är VC:s **förval** — vi satte den aldrig.

### 2. Kopplingarna: 7 av 7 där specen säger ja

| Koppling | `canConnect` | `connect` | `IsConnected` |
|---|---|---|---|
| `kedja: matare -> transportor` | **True** | True | True |
| `kedja: transportor -> buffert` | **True** | True | True |
| `kedja: buffert -> sanka` | **True** | True | True |
| `hel: transportor`, `hel: matare`, `hel: sanka`, `hel: buffert` | **True** (4 av 4) | True | True |

Bindningarna, lästa tillbaka ur fälten, visar varför **C1 inte är en detalj**:

| Gränssnitt | `Container` | `Port` | kontaktens `Type` |
|---|---|---|---|
| `F20_Matare.OutInterface` | `vcComponentCreator` | **0** | 2 (Output) |
| `F20_Bana.InInterface` | `vcMotionPath` | 0 | 1 (Input) |
| `F20_Bana.OutInterface` | `vcMotionPath` | **1** | 2 (Output) |
| `F20_Sanka.InInterface` | `vcComponentContainer` | 0 | 1 (Input) |

Skaparens **utgång** ligger på index 0, banans på index 1. Ett val på index i
stället för på `Type` hade varit grönt på banan och tyst fel på mataren — precis
det C1 varnade för, nu sett i samma körning.

### 3. De fyra trasiga fixturerna: 4 av 4 fälls, med namn

Varje par är samma motpart mot först den trasiga och sedan en hel tvilling **på
samma plats i världen**. Skillnaden mellan de två utfallen är därför exakt det
utelämnade beteendet.

| Klass | Utelämnat | trasig `canConnect` | hel tvilling `canConnect` | `granska()` namnger | regel som brast |
|---|---|---|---|---|---|
| transportör | `Path` (`VC_ONEWAYPATH`) | **False** | **True** | `['Path']` | **R2** |
| matare | `Creator` (`VC_COMPONENTCREATOR`) | **False** | **True** | `['Creator']` | **R2** |
| sänka | `Sink` (`VC_COMPONENTCONTAINER`) | **False** | **True** | `['Sink']` | **R2** |
| buffert | `Path` (`VC_ONEWAYPATH`) | **False** | **True** | `['Path']` | **R2** |

`connect()` anropades aldrig på de trasiga — `canConnect` var falskt, och
körningen frågar innan den kopplar. VC sade ingenting utöver `False`: ingen
exception, ingen logg. Meningen som namnger beteendet är **vår**, ur specens
egen kravlista.

Matchningsregeln kördes på **verklig VC-data**, inte på en provfixtur:
`varfor_inte()` fick de två gränssnittens återlästa fältbindningar och pekade i
alla fyra fallen på **R2** — `Container = None`.

### 4. Rör sig material igenom? Ja, hela vägen

Provfönster 34,8 simulerade sekunder (simtid 1,57 → 36,32), 18 avläsningar.

* **13 produkter skapade**, vid t = 0, 3, 6, … 36 s. Alla tolv mellanrum
  **exakt 3,0000 s** mot `Interval` 3.0.
* **Rörelsen: 400,0000 – 400,0000 mm/s** över 17 mätta par, mot `Speed` 400.0.
  Spridning 0,0000.
* **Materialet når hela kedjan.** Vid sista avläsningen: 2 på banan
  (banavstånd 1326,0 och 126,0 mm), 1 i bufferten (526,0 mm), **10 i sänkan**.
* **Räkningen går ihop: 2 + 1 + 10 = 13**, samma antal som skapades. Ingen
  produkt försvann, ingen dubblerades.
* Sänkans innehåll växer monotont över de arton avläsningarna:
  0, 0, 0, 1, 1, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8, 9, 9, 10.

Det sista är svaret på en fråga M-67 lämnade öppen och som ingen mätning haft:
**en `VC_COMPONENTCONTAINER` tar faktiskt emot material genom ett kopplat
`vcSimInterface`.** Den lagrar; produkternas `getPathDistance()` är `-1.0`
därinne, för de ligger inte på någon bana längre.

## Fynd 3 — en `MÄTT`-rad i specen reproducerade inte

Spec 49 §1.1 bar raden *"MÄTT om klassnamnen: py2-bindningen rapporterar egna
klassnamn som **inte** är api.xml:s typnamn"*, med sex exempel. Mätt om, på två
oberoende vägar (returvärdet från `createBehaviour` och samma beteende hämtat
ur `k.Behaviours`), i samma VC 4.10 och samma prefix:

| Konstant | raden sade | **MÄTT M-101** |
|---|---|---|
| `VC_ONEWAYPATH` | `vcOneWayPath` | **`vcMotionPath`** |
| `VC_COMPONENTCONTAINER` | `vcSimContainer` | **`vcComponentContainer`** |
| `VC_COMPONENTCREATOR` | `rResourceCreator` | **`vcComponentCreator`** |
| `VC_ONEDIRECTIONALPATH` | `vcMovementPath` | **`vcOneDirectionalPath`** |
| `VC_CONTAINERFILLER` | `vcContainerFiller` | **`vcFlow`** |
| `VC_TRANSPORT` | `vcTransport` | `vcTransport` |

Fem av sex skiljer sig. `type(b).__name__` ger alltså **api.xml:s** namn.

Vad som mättes 2026-09-04 vet jag inte, och jag påstår inte att ingenting
mättes — men det som står är inte vad VC svarar i dag, på den maskinen, i det
prefixet. **Följden är en grind som mäter mot en felaktig lista:**
`byggrecept/hypoteser.MATTA_KLASSNAMN` håller namn VC inte producerar, och
`tests/enhet/test_byggrecept.py` dömer VC-namn mot den. Listan ligger utanför
fas 20:s filer och är **inte rättad här** — den är flaggad, här och i specen.

## Fynd 4 — `Port = 0` är förvalet, inte `-1`

M-40 skrev *"Ett fält med `Port = -1` ger `canConnect() == False`"*, och det
stämmer. Men ett **nyskapat** `VC_FLOWFIELD` bär `Port = 0`, inte `-1` — mätt
på alla sex obundna gränssnitt i de trasiga fixturerna: `Container = None`,
`Port = 0`.

`-1` är vad `Port` **blir** när `Container` sätts efter `Port` (M-40:s
ordningsfynd). Det är inte vad ett obundet fält bär.

Det spelar roll för domaren. Ett prov som bara läste `Port` hade sagt "bundet"
om ett fält som pekar på port 0 i **inget** beteende — grönt om en komponent VC
vägrar koppla. Det är därför **R2 (`Container`) står före R3 (`Port`)** i
matchningsregeln, och det är R2 som fäller alla fyra trasiga fixturerna.

## LIMITS

* **Ingen upprepning.** Varje komponent byggs och mäts **en gång**, i en
  körning. Ingen spridning bakom något tal.
* **Ett fönster.** Flödet mäts över ett provfönster på ~36 s. En matare som
  slutar efter tjugo minuter hade sett hel ut här (samma begränsning som M-41).
* **Två av fem par är härledda, inte mätta.** `transportor -> transportor` och
  `matare -> sanka` står som "ja" i specens partabell därför att de följer av
  R5, inte därför att de byggts. Härkomstkolumnen säger det.
* **Matchningsregelns ordning är vår, inte VC:s.** `canConnect` ger ett enda
  `False` och säger aldrig vilket villkor som brast. R1–R9 är den ordning som
  gör felet begripligt; VC:s inre ordning är omätt.
* **R6, R7 och R8 är belagda, inte mätta.** Alla våra sektioner har exakt ett
  fält av samma typ, så fältordning och fälttyp kan inte skilja i den här
  uppställningen.
* **`DistanceTolerance` mäts bara vid förvalet** (1e9 mm). Vad ett satt värde
  gör är fortfarande omätt (öppen sedan M-67).
* **Ramarna sammanföll i hela kedjan.** M-67:s öppna fråga — om material går
  över en koppling vars ramar ligger **isär** — är fortfarande obesvarad. Den
  här körningen byggde med sammanfallande ramar med flit, så den kan inte svara.
* **Bufferten buffrade aldrig.** `Accumulate=True` och `Capacity=10` sattes och
  lästes tillbaka, men bufferten höll som mest **1** komponent: flödet var
  aldrig så snabbt att en kö uppstod. Att `Accumulate` gör något är därmed
  fortfarande **HYPOTES D4**.
* **Sänkan tar emot — men töms aldrig.** Att ta bort en komponent kräver ett
  skriptbeteende (M-13). Vad som händer när `Capacity` nås är omätt.
* **Städningen efter körningen faller på en okänd orsak.** En slinga som tog
  bort varje `F20_`-komponent svarade `failed` ur kön efter 31 ms, efter att ha
  hunnit ta bort några. Samma borttagningar, **en per anrop**, gick igenom för
  alla tolv. Körningen använder nu formen som är mätt att fungera, och
  rapporterar vad som **faktiskt** är kvar efteråt. Orsaken är inte utredd.
* **Fynd 3 är inte ett rättat fel.** `hypoteser.MATTA_KLASSNAMN` står kvar med
  namn VC inte producerar. Filen ligger utanför fas 20 och en annan agent kan
  ha den öppen.
