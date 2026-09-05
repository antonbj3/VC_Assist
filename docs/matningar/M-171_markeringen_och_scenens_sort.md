# M-171 — Markeringen headless, och scenens sort ur strukturen

**Datum:** 2026-09-05
**Rigg:** Körande VC Premium 4.10 i testprefixet `~/.wine-vc-test` under Wine,
`DISPLAY=:99` (Xvfb 1920x1080, ingen fysisk skärm), bryggan på port 8901.
Tjänstesidan: `tests/protocol/kor_markering.py` och `tests/enhet/test_markering.py`
(32 prov, ingen VC).
**Prövar:** `svc/vc_assist_svc/verktyg/markering.py`,
`svc/vc_assist_svc/scenarbete/markering.py`,
`svc/vc_assist_svc/scenarbete/avsikt.py` (AV1b, AV3b, AV4),
`ext/vc_addon/vc_assist/formaga.py`

**beskriver:** `svc/vc_assist_svc/verktyg/markering.py`,
`svc/vc_assist_svc/scenarbete/markering.py`,
`svc/vc_assist_svc/scenarbete/avsikt.py`,
`tests/enhet/test_markering.py`, `tests/protocol/kor_markering.py`

**Rådata:** `docs/matningar/radata/m171_markeringen.json`

---

## Frågan

*"Byt det där gripdonet."* Ett pekord — deixis. Registret bar **122 verktyg och
noll** som rörde markering eller urval, så systemet kunde inte se vad
användaren pekade på. Tre frågor, i ordning:

1. Finns markeringsytan, och **fungerar den headless**? Utan vy kanske ingen
   markering finns, och då är hela vägen värdelös i den rigg vi kör i.
2. Går scenens **sort** att läsa ur strukturen i stället för ur namnet?
3. Hur mycket löser markeringen faktiskt ut — och löser den någonsin ut **fel**?

## Resultat

### 1. Markeringen fungerar headless, och GUI:t delar lagret med API:t

| Fråga | Mätt |
|---|---|
| `app.SelectionManager` finns | **ja**, typ `vcSelectionManager` |
| Vad den bär | **fyra** anrop: `clear`, `getSelection`, `setSelection`, `setGeometrySelectEnabled` |
| `app.CurrentSelection` | **None** |
| `app.Selections` | **None** (iteration ger `TypeError`) |
| `getSelection(VC_SELECTION_COMPONENT)` headless | svarar, returnerar en riktig `list` |
| `setSelection(komp)` → `getSelection` | **round-trip håller**: ett objekt, en lista, och `append`-argumentet |
| `clear()` | tömmer; scenen återställd |

`api.xml` dokumenterar tre av de fyra anropen — och gör det i `<properties>`,
inte i `<methods>`, vilket är varför en läsning av indexet kan ge intrycket att
`vcSelectionManager` är tom. `setGeometrySelectEnabled` står inte alls.

**De deprekerade vägarna är döda headless, och VC säger det själv.** I VC:s eget
Output-fönster står, oombett:

> `Selections property is deprecated in version 4.0. Use SelectionManager instead.`

Därför kräver verktygen ytan `app.SelectionManager`, som lades till i
`formaga.YTOR` — inte den redan befintliga `app.getSelection`, som finns men är
den deprekerade grannen.

**GUI:t och API:t är ETT lager.** Frågan går inte att ställa med en musklick utan
att riskera en annan sessions scen (PnP-läget var aktivt; en klick med minsta
rörelse *flyttar* en komponent). Den gick att ställa åt andra hållet, och det är
lika bindande: `setSelection(ST8A_Don)` genom bryggan fick VC:s egen panel att
byta från tom `Properties` till `Component Properties → ST8A_Don` med hela
egenskapsredigeraren, och ribbonens `Attach` att bli aktiv. `clear()` gav en
**pixelidentisk** återgång. Det verktyget läser är alltså det panelen visar.

### 2. Sorten går att läsa ur strukturen — och behöver ingen översättningstabell

Ett beteendes `Type` i en körande scen är **exakt filformatets markörsträng**:

```
VC_ONEWAYPATH        == 'rOneWayPath'
VC_ROBOTCONTROLLER   == 'rSimRobotController'
VC_TOOLCONTAINER     == 'rToolContainer'
VC_CAPACITYCONTROLLER == 'rSimCapacityBlock'
VC_BOOLEANSIGNAL     == 'rSimBoolSignal'
```

`komponentdatablad.API_TYP` byggdes på premissen att filformatet och
Python-sidan är **två namnrymder** vars avbildning ingen källa skriver ut, och
lämnade i M-85:s LIMITS den öppna punkten att avbildningen inte är *prövad*. Den
punkten är nu stängd: det är **en** namnrymd. `VC_`-namnet är ett alias vars
värde är rsc-strängen. Alla `HANDSATT`-raderna som gick att prova stämmer,
inklusive `rSimBoolSignal → VC_BOOLEANSIGNAL`, och `rSimCapacityBlock` — som
saknades i tabellen — heter `VC_CAPACITYCONTROLLER`.

Följden för det här bygget: `datablad.FAMILJEMARKORER` gäller **oförändrat** mot
en levande scen. Ingen tredje kopia av listan behövdes; verktyget skriver in
markörerna som literaler ur den befintliga.

**Namnet ljuger, i just den här scenen.** Provscenen bär en komponent som heter
`Robot`. Den bär **en boolsignal och ingen robotstyrning**. En namnhärledning
hade kallat den robot; strukturen säger okänd sort. Det är M-69:s fel gjort i
en scen i stället för i katalogen, och det är därför sorten aldrig får gissas.

### 3. Identiteten: `is` hade gett en flagga som alltid var falsk

| Fråga | Mätt |
|---|---|
| Två läsningar av samma komponent, `a[0] is b[0]` | **False** |
| `a[0] == b[0]` | **True** |
| hashbar, och hash-träff över två läsningar | **True** |
| `b[0] in a` | **True** |
| Unika namn? | **nej**: `ST8_Mall` ×4, `Name` ×2 |
| `VCID` | **tom sträng** för alla sessionsbyggda |

Markeringen paras därför ihop med scenen genom en ordbok **på komponent­objektet**.
`is` hade gett `selected: false` för allt, tyst. Namnet hade gett `true` för alla
fyra `ST8_Mall` när en var markerad. Provet i levande VC visar rätt utfall: av
fyra likanamnade är noll markerade, och exakt en `ST8_Bana` av två.

### 4. Ögonblicksbilden: 102 tokens för en 20-komponentsscen

Verktyget `scene_snapshot` kördes mot den levande scenen (20 komponenter, 2
markerade, **4 ms**). Bilden:

```
SCEN 20 komponenter, 2 markerade [scene_snapshot]
okand: ST8_Mall x4, ST8_Matare, ST8A_Givare, ST8B_Givare, ST8_Linje, ST8A_Don,
       ST8B_Don, ST8_BromsA, ST8_BromsB, ST8_Utmatare, VcAssistBridge, Name x2,
       Robot, P15_7_kropp
transportor: ST8_Bana, ST8_Bana2
MARKERAT: ST8_Bana (transportor), ST8A_Don (okand)
```

| Mått | Värde |
|---|---|
| byte | **304** |
| tecken | **304** |
| tokens | **102** (76 ur byte, 102 ur tecken, spridning 25,5 %) |
| tak | **1 200** (`markering.TAK_TOKENS`) |
| ryms | **ja**, med 11,5 gångers marginal |

Taket är härlett, inte valt: bilden **är** scenvyn, och scenvyn är post 6 i
`25_kontextbudget.md` med tak 15 % av kontextfönstret. Det minsta fönster
projektet har mätt mot är 8 000 tokens (M-141), och 15 % av 8 000 är 1 200.

Vid taket räcker bilden till ungefär 240 komponenter i den här scenens
namnlängd. Över det krymper `text()` i tre steg — namnlistan går först,
räkningen per sort står kvar, och `MARKERAT` går sist, därför att det är den
raden pekordet faktiskt behöver. Att den degraderingen håller taket är provat
med en konstruerad 400-komponentsscen.

### 5. Hur mycket löser markeringen ut — och löser den ut fel?

Korsprov över två scener (den levande, och brevets tre gripdon), varje sort med
minst två komponenter, varje realistiskt markeringsläge. **15 tvetydiga fall:**

| Utfall | Antal | Vad som händer |
|---|---|---|
| `AVGJORD` | **3** | markeringen löste ut målet, med belägg |
| `SMALNAD` | **6** | färre kandidater, frågan står kvar |
| `MOTSAGELSE` | **2** | annan sort markerad — frågan ställs, nu med båda sidor namngivna |
| `SAKNAS` | **3** | ingenting markerat; frågan ställs precis som förut |
| `OVIDKOMMANDE` | **1** | markeringens sort gick inte att avgöra; bär ingen upplysning |
| **säkerhetsbrott** | **0** | inget fall löste ut fel |

Säkerhetsprovet är tre krav på **varje** utlöst rad: det utlösta målet är
markerat, det är av den sort meningen namngav, och det bär ett belägg som namner
komponenten. Ingen rad bröt något av dem, och ingen `FRAGA` fick fler kandidater
än meningen gav.

De 3 utlösta är alla `en av kandidaterna markerad`. De 2 motsägelserna är fall
där en naiv "markeringen vinner"-implementation hade **bytt fel komponent** —
`ST210_BAND` när operatören sa gripdon. Den implementationen står som
`NAIV_UPPLOSNING` i provfilen, och varje sådant prov jämför mot den, så
skillnaden är mekaniskt bevakad i stället för beskriven.

### 6. Sorten vidgar uppslaget, och det var nödvändigt

I scenen `ST210_gripdon`, `GRP_A`, `Gripper_2F_85` träffar delsträngen "gripdon"
**en av tre**. Före AV3b löste den ut just den — alltså valde ett av tre gripdon
därför att någon råkat döpa det på svenska. Sorten är inte språkbunden, och
unionen kan bara **lägga till** kandidater, så vidgningen kan inte dölja en
träff — den gör en tvetydighet **synlig** som förut var ett tyst val. Ett
uttryckligt komponentnamn avgör fortfarande ensamt.

### 7. Ett fynd på vägen: `sparr._stods_av_grunden` kunde inte fyra

Belägget för att markeringen avgjorde går genom `sparr.Scenharkomst.granska`
med källan `scen`. Den vägen **kastade `TypeError` vid varje anrop med en riktig
grund**: `Namnpastaende(namn=..., mening=...)` anropades utan det obligatoriska
`sort`. Kontrollen för källorna `scen` och `ogat` var alltså strukturellt död,
och `granska()` lovar i sin egen docstring att aldrig kasta (S10). Felet syntes
inte därför att proven bara körde `grund=None`, som returnerar tidigare.

Det är S2:s felklass — *en detektor som inte kan fyra är ett fel, inte en
varning* — och exakt den skuld `96_ingen_skuld.md` mättes fram ur. Rättat med
`sort="citerat"`, och provat åt båda hållen: belägget styrks av en grund som
bär `get_selection`-svaret, och fälls med `SH3_OSTODD_SCENUTSAGA` utan.

## LIMITS

* **Ingen fysisk musklick är prövad.** Att GUI:t och API:t delar lager är mätt
  åt hållet API → GUI (panelen följde med, pixelidentisk återgång vid `clear`).
  Att en *användares klick i vyn* skriver till samma `SelectionManager` är
  därmed starkt indicerat men inte direkt mätt. Klicken utfördes inte därför att
  riggen delas: VC stod i PnP-läge, där en klick med minsta pekarrörelse flyttar
  en komponent i en annan sessions scen. Det är ett medvetet val av vad som inte
  fick riskeras, inte ett hinder i verktyget.
* **Tokentalet är en uppskattning, inte en tokenisering.** 102 tokens kommer ur
  `llm/matt.py`, som tar det största av 4 byte/token och 3,0 tecken/token. Båda
  talen är ANTAGNA (`25_kontextbudget.md` avsnitt 7). Spridningen mellan dem är
  **25,5 %** på just den här texten, vilket är stort — bilden är kort och
  ASCII-tät, alltså precis den sorts text där de två antagandena är som mest
  oense. Ingen leverantörs tokenisering har räknat den.
* **En scen, en sortfördelning.** Den levande scenen bar bara `transportor` av
  de tre familjerna; `robot` och `verktyg` finns bara i den konstruerade scenen.
  Att markörerna `rSimRobotController` och `rToolContainer` verkligen faller ut
  som familj i en *levande* scen är alltså **inte** mätt — bara att mekanismen
  läser `b.Type` rätt, och att `rOneWayPath` gör det.
* **Fallbankens 15 fall är konstruerade, inte insamlade.** De är ett korsprov
  över markeringslägen, inte ett stickprov ur verkliga meningar. Kvoten 3 av 15
  säger alltså hur mekanismen beter sig över lägena — **inte** hur ofta en
  operatör har rätt sak markerad. Det talet kräver en operatör och finns inte.
* **`malsort` är modellens tolkning och prövas aldrig mot meningen.** Att
  "gripdon" betyder `verktyg` är en utsaga grinden inte kan belägga — den kan
  bara kontrollera att sorten finns i den slutna listan och jämföra den med
  markeringen. En modell som konsekvent säger fel sort får konsekvent
  `MOTSAGELSE`, vilket är säkert men inte användbart. Ingen mätning här visar
  hur ofta en modell träffar rätt sort.
* **Tre familjer är hela vokabulären.** `datablad.FAMILJEMARKORER` känner
  `robot`, `transportor` och `verktyg`. Allt annat — givare, bromsar, matare,
  fixturer — blir `okand`, och i den levande scenen är det **18 av 20**. Sorten
  bär alltså lite information i just den scenen, och att utöka markörlistan är
  ett eget arbete som inte gjordes här.
* **Snapshotten läses inte av loopen än.** Verktygen finns, bilden finns och
  `avsikt.granska` tar emot en markering. Att `harness/loop.py` faktiskt
  injicerar bilden varje tur är **inte** byggt, och därmed är kedjan från
  operatörens klick till modellens kontext inte sluten i drift.
* **Prestandan är mätt en gång.** 4 ms för 20 komponenter, i en scen utan
  laddade katalogkomponenter. Hur `scene_snapshot` beter sig på en scen med
  hundratals komponenter och djupa beteendeträd är inte mätt; `_sort()` går
  igenom varje beteende på varje komponent.
