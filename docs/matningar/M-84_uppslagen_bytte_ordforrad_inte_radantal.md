# M-84 — uppslagen halverade koden och gav den 2,5 gånger fler API-namn

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_m82_scenkod.py` (samma domare som M-82)
**Verktyget som prövas:** `tests/protocol/stod/slaupp.py`
**Prövar:** M-83:s påstående, som fram till nu bara var ett resonemang.

## Frågan

M-83 avslutades med en slutsats som ingen mätt:

> *"Att ge modellen `lookup_api` och `search_api` är inte en bekvämlighet. Det är
> skillnaden mellan en scen som byggs och en som lämnas halv med ärliga
> kommentarer."*

Det är ett påstående om orsak, och det går att pröva: samma tre scener, samma
domare, samma instruktion — en körning **utan** uppslag (M-82) och en **med**.

## Uppställningen, och dess fel

Samma tre scener ur banken (T-90, S-03, L-05 — 3, 5 och 9 komponenter). Samma
brief. Skillnaden är `slaupp.py`, som svarar på tre frågor och ingenting annat:
exakt namn, fritextsökning, en typs hela yta. Att den inte svarar på något annat
är vad som gör jämförelsen giltig — en modell som kan läsa repot ser facit.

**Verktyget gick sönder mitt i körningen, och felet var mitt.** Två fel:

1. `KOD`-strängen formateras med `% REPO`. Jag skrev in ett `%d` utan att dubbla
   det, och `KOD % REPO` kastade `TypeError`. Lagat i `5ea7bba`, 05:29 — efter
   att agenten börjat.
2. Repots rot härleddes **tre nivåer upp ur filens egen plats**. Det är rätt för
   `tests/protocol/stod/`, men verktyget hade kopierats till en scratchpad, och
   därifrån pekade det på sessionskatalogen. Felet syntes som
   `No module named vc_assist_svc` ur en underprocess — långt från sin orsak.

Agenten körde därför en egen lagad kopia. Den anropar **samma tre handlers**
(`lookup_api`, `search_api`, `type_surface`) och läser repot på inget annat sätt;
det är verifierat med `diff`. Men två tal skiljer: kopian bad om **40** träffar
per sökning i stället för 12, och kapade listor vid 400 poster i stället för 12.

**Riktningen på det felet:** agenten såg **mer** per uppslag än det levererade
verktyget ger. Mätningen gäller alltså *uppslag med generösa gränser*, inte
exakt den tröskel som står i `slaupp.py` idag. Talen nedan är en övre gräns för
vad uppslag är värda, inte en mätning av den levererade inställningen.

## Utfallet

| | rader | namnkontroller | **distinkta namn** | uppfunna |
|---|---|---|---|---|
| M-82, utan uppslag | 691 | 584 | **13** | 0 |
| M-84, med uppslag | 332 | 237 | **32** | 0 |

Noll uppfunna namn i båda. Det var väntat — M-82 visade redan att modellen hellre
lämnar hål än gissar.

**Det som inte var väntat: körningen med uppslag skrev hälften så mycket kod.**

Läser man bara radantalet ser uppslagen ut att ha gjort modellen mindre
produktiv. Den läsningen är fel, och ordförrådet visar varför.

## Vad de 584 kontrollerna utan uppslag faktiskt var

```
    188 x  getApplication
    171 x  vcApplication.findComponent
     42 x  vcComponent.getProperty
     28 x  vcBehaviour.Name
     26 x  VC_ONETOONEINTERFACE
     26 x  vcComponent.findBehavioursByType
     21 x  vcProperty.Value
     17 x  vcApplication.load
     17 x  vcComponent.Name
     17 x  vcComponent.PositionMatrix
     13 x  vcBehaviour.connect
      9 x  vcComponent.WorldPositionMatrix
      9 x  vcMatrix.P
```

Tretton namn. **Två av dem är 61 % av alla kontroller.** Modellen skrev
`getApplication().findComponent(...)` om och om igen, inline, 188 gånger — inte
för att scenen krävde det, utan för att det var den enda idiom den var säker på.
De 691 raderna är till stor del ställningar runt ett mycket litet ordförråd.

Med uppslag: 32 namn, topp-två är 26 %, i snitt 7,4 användningar per namn mot
44,9. `getApplication` gick från **188 till 3** — bunden en gång per fil.

## De 24 namn som bara finns i körningen med uppslag

```
     16 x  VC_BOOLEANSIGNAL            5 x  vcComponent.createBehaviour
     13 x  vcApplication.connectComponents   5 x  vcHelpers.Robot.SignalMapIn
     17 x  vcComponent.saveState       3 x  vcComponent.findBehaviour
      6 x  VC_COMPONENTCONTAINER       3 x  vcApplication.getSimulation
      2 x  vcHelpers.Robot.GraspContainer    3 x  vcSimulation.reset
      2 x  vcComponent.createProperty  3 x  vcApplication.render
      2 x  VC_REALSIGNAL               1 x  vcComponent.attach
      1 x  vcHelpers.Robot.mountTool   1 x  vcComponent.ComponentChildren
      1 x  vcHelpers.Robot.getRobot    1 x  vcBehaviour.Capacity
      1 x  VC_ROBOTEXECUTOR            1 x  vcBehaviour.Statistics
      1 x  VC_STATISTICS               1 x  VC_INTEGER
      1 x  vcHelpers.Robot             1 x  VC_BOOLEAN
```

Och fem föll **bort**: `VC_ONETOONEINTERFACE`, `vcApplication.findComponent`,
`vcBehaviour.Name`, `vcComponent.WorldPositionMatrix`, `vcMatrix.P`. Det är
handrullad gränssnittsiteration som ersattes av `connectComponents` — den riktiga
metoden, som modellen utan uppslag inte visste fanns.

## M-82:s tre hål, prövade i koden och inte i rapporten

M-82 citerade modellens tre avstådda punkter. Alla tre finns nu i koden — jag har
letat efter dem i filerna, inte litat på agentens rapport:

| M-82 avstod från | i M-84:s kod |
|---|---|
| signalkopplingar (*"var inte säker nog på signal-API:t"*) | `VC_BOOLEANSIGNAL` 16 ×, `vcBehaviour.connect` 12 × i alla tre scenerna |
| `vcHelpers.Robot` (*"inte säker nog på hjälparens yta"*) | `getRobot`, `mountTool`, `GraspContainer`, `SignalMapIn` i L-05 |
| komponentbehållare för pallen | `VC_COMPONENTCONTAINER` 6 × i L-05 och S-03 |

## Vilka uppslag som ändrade koden

Mätningens hela poäng, ur agentens egen redovisning — inte *hur många* uppslag,
utan vilka som **ändrade** det skrivna:

* **`namn VC_BOOLSIGNAL` → SAKNAS**, förslag `VC_BOOLEANSIGNAL`. Typen heter
  `vcBoolSignal`, så det förkortade konstantnamnet var på väg in i **alla tre**
  filerna. Ett uppslag stoppade samma påhitt tre gånger.
* **`namn VC_PROCESSPOINTSENSOR` → SAKNAS.** Fotocellen skulle kopplas via den.
  Vägen övergavs i stället för att skrivas.
* **`yta vcContainer` visade `Components` som skrivskyddad [R].** Det ändrade vad
  modellen *påstår*: i stället för att uppfinna `container.add(pall)` skapas
  behållaren, pallen fästs med `attach`, och en anmärkning säger varför
  insättning vid byggtillfället inte går.
* **`sok PLC` och `sok OPC` → noll träffar.** T-90:s TON-defekt hör till
  PLC-projektet, inte till VC:s Python-API. Den dokumenterades som utanför
  räckvidd i stället för att fejkas.

De tre första är samma sort: ett uppslag som gav **SAKNAS** var mer värt än ett
som gav en träff. Verktygets nytta ligger lika mycket i vad det nekar.

## Vad som var osäkert även med uppslag

Indexet täcker API-symboler. Det täcker **inte** per-komponent-data, och där tog
uppslagen slut:

* Komponenternas egenskapsnamn (`ConveyorSpeed`, `StrokeTime`, `MaxPayload` …).
  Varje sättning är därför vaktad med `getProperty(...) != None`.
* `bank://`-URI:erna går inte att verifiera genom indexet.
* **Vilken** boolsk signal `findBehavioursByType(VC_BOOLEANSIGNAL)[0]` är på en
  given komponent. Indexet ger typen, inte komponentens signalnamngivning.
* `vcHelpers.Robot` kontra `Robot2` — båda dokumenterade med nästan identisk yta.

Det är precis den luckan katalogindexets djupläge (`component.rsc`) finns för.
Ett API-index och ett komponentindex svarar på olika frågor, och den här
mätningen visar var gränsen mellan dem går i praktiken.

## Vad domaren fick lära sig av mätningen

Talet **584 kontrollerade namn** gick inte att revidera: det var en egen räkning
som åtta ställen i `api_index.py` ökade för hand, utan att någonstans behålla
*vilka* namn som räknats. En sådan siffra kan inte provas mot någonting, och om
ett ställe ökat utan att pröva ett namn hade ingen sett det.

`Granskning.kontrollerade_namn` är nu en **härledd** egenskap: summan av
`sedda_namn`. De två kan inte längre säga olika saker. Hela den här mätningens
huvudresultat — 13 mot 32 — går inte att få fram ur den gamla räkningen.

## LIMITS

* **Tre scener, en modell, en körning per uppställning.** 13 mot 32 är en stor
  skillnad, men den är inte mätt över upprepningar och har inget spridningsmått.
* **Uppslagsgränserna skiljer sig från den levererade** (40/400 mot 12/12), i
  riktningen att agenten såg mer. Talen är en övre gräns.
* **Domaren dömer att namnet finns, inte att det används rätt.** Returvärden,
  argumentantal och enheter ligger utanför grind 4 — precis som i M-82. Ingen av
  de tre scenerna har körts i VC.
* **"Rader" räknar icke-tomma rader**, kommentarer inräknade. Fördelningen är
  572 kodrader / 119 kommentarrader utan uppslag mot 248 / 84 med — kvoten står
  sig, men radmåttet är trubbigt.
* **Ordförrådet är inte kvalitet.** Att röra fler delar av API:t är inte samma
  sak som att bygga en scen som fungerar. Den frågan äger ögat, och den är
  obesvarad för de här tre filerna.
