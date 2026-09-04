# M-32 — komponentidentitet, uppstartsordning, och en matare som inte matar

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Fas:** 5. Blockeraren är kvar, men den är nu **mätt** i stället för antagen.

## Kedjan, i den ordning den föll ut

### 1. En programmatiskt skapad komponent har ingen identitet

```
app.createComponent()  ->  Uri = "vcid:"   VCID = ""
```

Den går alltså inte att referera. Och `vcComponentCreator.Part` är av typen
**URI** — mataren kan bara peka på något som har en.

Sätter man `Part` till ett namn, en `vcid://`-sträng eller komponentens egen
tomma URI tar egenskapen tyst emot värdet och behåller `''`. Inget fel.

### 2. `comp.save(uri)` ger identitet — och dödar bryggan

`Produkt.vcmd`, 5025 byte, skrevs till disk. Laddad tillbaka:

```
Uri  = file:///C:\users\anton\egna_komponenter\Produkt.vcmd
VCID = 40fc7ea5-80a7-4956-8eda-32fe734e3f70
```

**Bygg → spara → ladda ger en komponent med riktig identitet.** Det är
katalogmekanismen, helt i vår kontroll, och den är svaret på att den lokala
eCatalog-mappen är tom.

`comp.save()` stoppar simuleringen och dödar pumpen, precis som `app.save()`
(M-13). Listan över dödande anrop växer med mätning, inte med principer.

### 3. En URI överlever inte en layoutrunda

`Part` satt till `file:///C:/.../Produkt.vcmd`, layouten sparad och laddad:

```
Part = "file:///"
```

Bara schemat kvar. VC kan inte lösa upp en fil utanför en känd katalogrot vid
inläsning, och lämnar då ingenting kvar att felsöka på.

### 4. Ett beteende i en redan körande simulering initieras aldrig

Därför fick tillägget två nya luckor, båda **före** `startSimulation()`:

| Fil i användarmappen | Vad den gör |
|---|---|
| `vc_assist_startlayout.txt` | en URI som laddas innan bryggan byggs |
| `vc_assist_startskript.py` | kod som kör efter laddningen, före simuleringen |

Startskriptet finns för punkt 3: sökvägen måste sättas om efter varje laddning.

### 5. Två fel som uppstartsordningen avslöjade

**En sparad layout bar med sig brygg-komponenten.** Vid laddning startade en
andra pump i samma process. Den hann skriva över den levande bryggans token och
föll sedan på bindningen — så den **levande** bryggan blev onåbar med `E_AUTH`,
utan ett ord i sin egen logg.

Två rättelser: bindningen sker nu **före** token skrivs, så en brygga som inte
fick porten aldrig rör filen. Och uppstarten rensar gamla brygg-komponenter ur
en laddad layout.

**`exec` ärver `__future__`-flaggor från den anropande modulen.** `bridge_cmd.py`
har `unicode_literals`, så varje strängliteral i startskriptet blev unicode — och
VC:s py2-bindning svarar `SystemError` på unicode (M-05).

Det förklarar också varför varje köad kodsnutt har behövt `str()` runt varenda
sträng. Alla tre `exec`-ställen kompilerar nu med `dont_inherit=True`.

### 6. Och ändå: mataren matar inte — **RÄTTAD, se M-34**

> **Rättelse 2026-09-04.** Slutsatsen nedan är **fel**. Mataren skapar mycket
> väl produkter; de hamnar i beteendets egen behållare, inte bland scenens
> toppnivåkomponenter. Jag mätte `len(app.Components)` — fel lista, tolv
> gånger i rad. Se [M-34](M-34_produkten_finns_men_flodar_inte.md).


Med allt ovan rätt — mataren finns när simuleringen startar, `Enabled=True`,
`Interval=1.0`, `Limit=5`, och `Part` bär en URI som **bevisligen går att ladda**:

```
load med Partens exakta varde  ->  "Produkt"   (2 -> 3 komponenter)
sk.create()                    ->  None        (2 -> 2 komponenter)
72 simulerade sekunder         ->  0 produkter, 0 i skaparens innehall
```

URI:n är alltså inte felet. Skaparen är inte avstängd. Den producerar bara inte.

## Öppet, och den mest sannolika förklaringen

`vcComponentCreator` har en **utkontakt** (mätt i M-17: `Output`, index 0, typ 2)
som inte är kopplad till någonting. En skapare som inte har någonstans att lämna
ifrån sig kan mycket väl vägra skapa — det är så en blockerad station beter sig.

Nästa mätning är alltså: koppla skaparens utkontakt till en bana med
`vcConnector.connect()` (som **fungerar**, M-17) och mät om produkter uppstår.

Det som återstår för fas 5 är därmed ett enda led, och det ledet är utpekat.

## Vad som INTE är mätt

* **Punkt 6 är fel, och rättelsen står bara som en ruta ovanför slutsatsen.**
  Texten under rutan (*"Skaparen är inte avstängd. Den producerar bara inte."*)
  står kvar oförändrad och läses fel av den som hoppar över rutan. Mätfelet var
  `len(app.Components)` — fel lista, tolv körningar i rad (M-34).
* Talet *"72 simulerade sekunder → 0 produkter"* är mätt på en matare byggd i en
  **redan körande** simulering. M-40 mätte att just det gör att en matare aldrig
  fyrar. Talet mätte alltså uppstartsordningen, inte mataren, och det gick inte
  att se på talet.
* Att en programmatiskt skapad komponent saknar identitet är mätt för
  `app.createComponent()`. Andra vägar att skapa en komponent är inte prövade.
* *"En URI överlever inte en layoutrunda"* är mätt för **en** fil utanför en känd
  katalogrot, en gång. En fil **innanför** en känd rot är inte prövad — och det är
  precis den uppställning textens egen förklaring pekar ut som skillnaden.
* Hela bygg–spara–ladda-omvägen visade sig senare vara onödig: M-40 mätte att
  `TemplateComponent` tar en komponent som står i scenen, även en med
  `Uri = "vcid:"`. Den här mätningen prövade aldrig den enklare vägen.
* De två uppstartsluckorna (`vc_assist_startlayout.txt`,
  `vc_assist_startskript.py`) beskrivs som byggda. Att de fungerar är mätt i
  M-40, inte här.
* De två uppstartsfelen (dubbel pump ur en sparad layout, `__future__`-flaggor
  genom `exec`) är rättade. Att rättelserna håller är inte mätt med ett prov som
  faller utan dem.
