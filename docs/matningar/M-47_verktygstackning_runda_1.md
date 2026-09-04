# M-47 — verktygstäckningen mätt i tre listor, runda 1

**Datum:** 2026-09-04 · mätt utan VC, mot API-indexet och mot den byggda koden
**Rör:** `docs/spec/45_verktyg.md`, `47_verktygstackning.md`, `48_personaprofiler.md`,
`svc/vc_assist_svc/api_index.py`, `svc/vc_assist_svc/verktyg/`

## Vilken runda det här är

Det finns ingen tidigare `M-47_*_runda_*`-fil, så detta är **runda 1 av M-47**.
Det är däremot inte den första leveransen till verktygsbiblioteket: repot bär
sedan tidigare tre omgångar (scene + composition som de första 21, sedan fem
domäner i ett svep till 77, och robotdomänen som ett eget bygge). Skillnaden är
att ingen av dem **räknade om de tre listorna**. Det är vad numret M-47 äger
härefter.

---

## 1. De tre talen

De är tre olika storheter och får aldrig blandas ihop.

| # | Lista | Tal | Härkomst |
|---|---|---|---|
| 1 | vad användaren **vill** göra | **58 arbetssteg** i sex personaprofiler | `48_personaprofiler.md`, räknat på tabellraderna |
| 2 | vad API:t **tillåter** | **3 444 symboler**, uttryckta som **345 verktyg** | `ApiIndex.statistik()`; 345 = tabellraderna i `47` avsnitt 4 |
| 3 | vad vi **faktiskt byggt** | **119 verktyg skrivna, 95 exponerbara** | `verktyg.register.REGISTER` |

Talen är körda, inte uppskattade. Skripten är engångsräkningar; metoden står i
avsnitt 6 så att vem som helst kan göra om dem.

### 3:ans två tal, och varför de skiljer sig

`REGISTER` bär 95 verktyg efter den här rundan. Ytterligare **24 verktyg finns
skrivna och provade i `svc/vc_assist_svc/verktyg/robotik.py` men importeras
inte av `verktyg/__init__.py`**. De registrerar sig alltså aldrig, och
**modellen kan inte se ett enda av dem.** 2 600 rader robotverktyg är byggda
och osynliga. Det är inte ett fel jag rättar här — modulens egen docstring
säger att den cell som kopplar in den också bör lägga robotytorna i
`formaga.YTOR` — men det är den enskilt billigaste vinsten i hela biblioteket
och det ska sägas rakt ut: **119 skrivna, 95 nåbara, differensen 24 är ren
inkoppling.**

### Fördelningen efter den här rundan

| Domän | byggda verktyg | Domän | byggda verktyg |
|---|---|---|---|
| transport | 25 | measure | **7 (nya)** |
| signals | 21 | composition | 6 |
| robot | 24 (ej inkopplade) | knowledge | 4 |
| scene | 15 | catalog | 3 |
| simulation | **11 (nya)** | eyes | 3 |

---

## 2. Skillnad 1 → 2: vad användaren vill men API:t inte tillåter

**4 av 58 arbetssteg (7 procent) har ingen Python-API-yta alls.** De ska bli
ett ärligt nej i produkten, inte ett körningsfel i en cell klockan tre på
natten.

| Profil | Steg | Vad användaren vill | Varför det inte går | Vad hen ska få höra i stället |
|---|---|---|---|---|
| P1 | 2 | hitta en komponent i eCatalog | sökning på "catalog" i indexet ger **2 träffar**, båda `vcCommand.(Deprecated) rebuildECatalog`. eCatalog är en nättjänst bakom användarkonto | "Jag kan söka i det lokala katalogindexet med `search_catalog`, men inte i eCatalog. Den ligger bakom ditt konto i programmet." |
| P2 | 12 | exportera programmet till robotens eget språk | `IRobotConverter` är **.NET**. `VC_RRSROBOTCONTROLLER` och `VC_KRCCONNECTION` är bara beteendetypnamn | "Programmet stannar i VC. Exporten till KRL, RAPID eller motsvarande gör du i programmets egen post-processor." |
| P3 | 5 | koppla scenen mot PLC | sökning på "connectivity", "opc" och "plc" ger **0 träffar** i api.xml. Ytan finns bara i .NET (`IServerHandler`, `IOpcUAServer`), och VC är alltid **klient** | "Jag når signalerna i scenen men inte uppkopplingen. Koppla VC som OPC UA-klient i gränssnittet; jag arbetar mot OpenPLC-sidan." Verktyget `connectivity_status` svarar redan så. |
| P6 | 1 | importera CAD | i Python finns bara `vcCommand.(Deprecated) interactiveImportModel`. Läsaren är .NET: `VisualComponents.Create3D.ICADReader` | "Importera filen själv i programmet, så arbetar jag vidare på det som kommit in." |

**Två av de fyra har redan ett byggt svar** (`search_catalog`,
`connectivity_status`). Två har det inte, och det är rundans första
spec-förslag: se avsnitt 5.

### Två gränser till, som inte är egna arbetssteg men styr allt

- **Ingen ångerfunktion.** Sökning på "undo" ger **2 träffar**, varav en är
  `vcGeometryFeature.Uri`. Bara `vcApplication.clearUndo` finns, och den
  *tömmer* historiken. Följd: godkännandekön kan aldrig backa ett anrop, den
  måste hindra det i förväg. Det **stärker** I12.
- **Ingen fysikyta.** 21 `VC_PHYSICS*`-konstanter finns, men den enda
  medlemmen i hela API:t är `vcFeature.PhysicsCollider`. Ingen `vcPhysics*`-typ
  bland de 204.

---

## 3. Skillnad 2 → 3: vad API:t tillåter men vi inte byggt

Två mått, för att ett av dem ensamt ljuger.

### 3.1 Namndiffen: 290 av 345

| Före rundan | Efter rundan |
|---|---|
| 307 föreslagna verktygsnamn obyggda | **290 obyggda** |

Namndiffen **överskattar** luckan: 64 byggda verktyg bär namn som inte står i
specens tabeller alls (`signal_map_set_port` mot specens `signal_map_port`,
`connect_signals` mot `connect_signal`, `move_targets` mot `create_target` +
`add_target` + `clear_targets`). De gör arbetet, under andra namn.

### 3.2 Ytdiffen: 299 av 904 API-symboler rörda (33 procent)

Det skarpare måttet. Varje VC-symbol som `47` avsnitt 4 namnger i kolumnen
"Bygger på" söks i den byggda verktygskoden.

| Domän | symboler | rörda | % | | Domän | symboler | rörda | % |
|---|---|---|---|---|---|---|---|---|
| signal | 29 | 28 | **96** | | produkt | 53 | 21 | 39 |
| simulering | 20 | 16 | **80** (var 25) | | rörelsebana | 32 | 12 | 37 |
| komposition | 21 | 14 | 66 | | mätning | 42 | 10 | **23** (var **0**) |
| robot | 42 | 27 | 64 | | process | 66 | 15 | 22 |
| program | 59 | 37 | 62 | | statistik | 57 | 9 | 15 |
| flöde | 36 | 19 | 52 | | app | 37 | 5 | 13 |
| scen | 63 | 31 | 49 | | fordon | 26 | 3 | 11 |
| kinematik | 37 | 17 | 45 | | utseende | 33 | 3 | 9 |
| transportsystem | 21 | 9 | 42 | | geometri | 80 | 6 | 7 |
| matematik | 29 | 9 | 31 | | ui | 41 | 3 | 7 |
| | | | | | **vy** | **35** | **2** | **5** |
| | | | | | enheter | 19 | 1 | **5** |
| **summa** | | | | | | **904** | **299** | **33** |

**Före rundan var mätning noll procent.** Det var den enda bärande domänen som
var helt orörd, och det var den grind hela `50_grindar.md` vilar på.

---

## 4. Vad som byggdes i den här rundan, och varför just det

`47` avsnitt 6 lägger simulering och mätning i **runda 1** av femton, med
motivet "ögat och grinden får sin råvara först. Utan denna runda mäter resten
ingenting". Rundorna 2, 5, 8–11 var byggda. **Runda 1 var det inte.** De två
domäner specen själv rangordnar som ett och två bar noll verktyg.

**18 verktyg byggda**, i två nya domäner:

| Domän | Verktyg |
|---|---|
| `simulation` (11) | `sim_state`, `sim_run`, `sim_continue`, `sim_halt`, `sim_reset`, `sim_step`, `sim_speed`, `sim_warmup`, `set_fast_scheduling`, `sim_initial_state`, `sim_autohalt` |
| `measure` (7) | `measure_distance`, `min_distance`, `test_collision`, `collision_detector_status`, `path_distance`, `ray_cast`, `frame_owner_node` |

### 4.1 Två av specens verktyg byggdes INTE, av mätta skäl

**`install_script_behaviour`** (specens 4.3). M-13 mätte att ett skriptbeteende
**stoppar simuleringen och tar ned pumpen mitt i dess eget svar**, och bryggans
`skrivgrind.skapar_skriptbeteende()` avvisar varje mall som skapar ett. Ett
verktyg som bara kan misslyckas är en stubbe. Raden hör till gränsen i `47`
avsnitt 7, inte till byggordningen.

**De sju detektorverktygen** (`new_collision_detector`, `test_one_collision`,
`collision_hits`, `bbox_collision`, `collision_settings`,
`new_volume_detector`, `volume_hits`). M-35 och M-36:

- Detektorn svarade **noll träffar** även för två kuber om 1 000 mm som låg
  100 mm isär — 900 mm överlapp i varje axel. Även det trasiga fallet var
  grönt.
- Orsaken: `vcCollisionDetector.NodeListA` **tar emot en lista och tömmer
  den**. Läs tillbaka ger `[]`. Nodlistorna var tomma hela tiden.
- `StopOnCollision` saknas dessutom helt på objektet, trots att `api.xml`
  deklarerar den.

Sju verktyg på den ytan hade varit sju stubbar, och värre: sju stubbar som
svarar **"inga kollisioner"**. Det är precis den falska gröna M-35 fann.

I stället bygger `test_collision`, `measure_distance` och `min_distance` på
**`vcNode.measureDistance`**, som M-36 mätte som exakt rätt i alla fem prövade
lägen. Och vägen tillbaka står öppen och **mätt**:
`collision_detector_status` kör om M-36:s eget prov inne i den VC som faktiskt
svarar, sätter nodlistorna och läser tillbaka längden. Svarar den
`nodelist_holds: true` är M-36 motbevisad där, och då **ska** de sju byggas.
Ett prov i `tests/enhet/test_verktyg_simmatning.py` läser mätningsfilerna och
faller den dagen — en gräns som bara står i en docstring ruttnar tyst.

### 4.2 Två hål i bryggans egen skrivgrind, funna av rundans korsprov

| Anrop | Vad den gör | Vad grinden dömde |
|---|---|---|
| `sim.autoHalt()` | **stoppar** simuleringen | LÄSANDE — `halt` är ett prefix, men `autoHalt` börjar inte på det |
| `sim.continueRun()` | **startar** en stoppad simulering igen | LÄSANDE — `run` är ett prefix, men `continueRun` börjar inte på det |

Ett verktyg på någon av dem hade kunnat gå genom `exec`, **utan godkännande**,
och ta ned en pågående körning. Båda är nu hela ord i
`skrivgrind.MUTERANDE_PREFIX`, med motprov på att `autoScale`, `autoSize`,
`continueCheck`, `runtime` och `setupComplete` fortfarande går fria.

Det är samma klass som fyndet 2026-09-04 om `clone()`, och samma lärdom:
**en prefixlista över muterande namn har inget slut. Den växer ur korsprov,
och varje domän som byggs ska köra det.**

### 4.3 Tre mätverktyg är `write` fast de bara frågar

M-36 mätte att VC svarar med ett **gammalt tal** om geometrin inte uppdaterats
— fem olika lägen gav identiskt `4000.0`. Varje mätande mall kör därför
`nod.update()` och `sim.update()` först, och `skrivgrind` dömer `update()` som
skrivande. Deklarationen följer grinden, inte tvärtom (samma val som
`robotik.py` gjorde för `check_reach`). Alternativet — att läsa utan att
uppdatera — vore att bygga in M-36:s fälla i grindens råvara.

---

## 5. Prioriterad arbetslista: efter personabehov, inte efter byggkostnad

Mekaniskt räknat: varje API-symbol i profilernas kolumn "Kräver" som **inte**
finns i byggd kod tilldelas den domän vars tabell i `47` avsnitt 4 namnger den.
Talet är hur många av de 58 arbetsstegen domänen låser upp.

| Rang | Domän | steg | profiler | Nya verktyg | Varför just här |
|---|---|---|---|---|---|
| 1 | **vy** | 3 | P5 | 12 | **P5 har 1 av 8 steg täckta** — sämst av alla sex. Och `beginFrameGrab`/`executeFrameGrab` är **ögats andra kanal** (`40_ogat.md`), inte bara säljbilder. Ytan är 5 procent rörd |
| 2 | **statistik** | 4 | P4, P5 | 17 | P4:s steg 8–10 och P5:s steg 7. Det är siffrorna i offerten och flaskhalsdomen. 15 procent rörd |
| 3 | **scen, skrivsidan** | 7 | P1, P6 | 21 | flest arbetssteg av alla, men de är grunda: lager, mått, annotationer, nodträdets skrivsida, BOM |
| 4 | **utseende** | 2 | P1, P5 | 11 | P5 steg 4 och P1 steg 8. Liten domän, noll egna metoder, låser upp två profiler |
| 5 | **app** | 4 | P1, P4, P5, P6 | 12 | **rör flest profiler av alla.** Layoutidentitet, slumpfrö (jämförbara körningar), `vcHelpers.VcmFile` |
| 6 | **kinematik** | 3 | P2, P5 | 15 | `getConfigWarnings` är en **mekanisk räckviddsdom** — ingen gissning behövs. `calcMotionTime` är cykeltiden |
| 7 | **process + produkt** | 4 | P4 | 41 | P4:s ryggrad. Störst arbete, en profil |
| 8 | **geometri** | 2 | P6 | 25 | störst yta i hela API:t, minst spridning. Sist, precis som `47` säger |

### 5.1 Om `vy` och varför den flyttas fram sex placeringar

`47` avsnitt 5 rangordnar `vy` som **17 av 23** på ytmått. Efter den här
mätningen är den **1**. Skälet är att rangordningen i `47` väger yta tungt, och
den här mätningen väger **arbetssteg som är noll procent täckta**. P5:s steg 3,
5 och 6 — kameror, bildfångst, inspelning — är helt otäckta, och steg 5 är
dessutom det ögat provtar med. En domän som blockerar både en hel profil och
en grindkanal hör inte på plats 17.

### 5.2 Vad ingen av de 345 täcker

`vcHelpers.Robot.pick` och `.place` står i `47` avsnitt 2.3 som
"kodgenereringens genväg" och i P2 steg 9 ("grepp och släpp"), men **inget av
de 345 föreslagna verktygen namnger dem.** `pick`, `place`, `pickFromPallet`,
`placeInPattern` och `graspComponent` finns alla i indexet. P2:s steg 9 har
alltså varken verktyg eller föreslaget verktyg. Se spec-förslag 3.

---

## 6. Metod — så räknas talen om

Alla fyra räkningar är engångsskript. De står här i sin helhet som metod, inte
som kod i repot.

1. **Lista 2, grundtal:** `bygg_index().statistik()` →
   `typer 204 · metoder 966 · egenskaper 1159 · handelser 175 · konstanter 709 ·
   hjalpmoduler 8 · hjalpmedlemmar 223 · symboler_totalt 3444`.
2. **Lista 2, verktygstal:** varje tabellrad i `47` avsnitt 4 som börjar med
   `` `namn` `` → 345 unika namn, varav 21 märkta `✓` vid skrivningen.
3. **Lista 3:** `len(verktyg.register.REGISTER)` efter import av paketet, plus
   `robotik.py` importerad för hand.
4. **Ytdiffen:** varje `` `symbol` `` i kolumnen "Bygger på", kortad till sitt
   medlemsnamn, sökt som helt ord i `svc/vc_assist_svc/verktyg/*.py`.
5. **Lista 1 mot lista 3:** samma sökning, men på symbolerna i profilernas
   kolumn "Kräver". Ett steg räknas som **helt täckt** när alla dess symboler
   finns i byggd kod, **delvis** när minst en gör det.

### Vad de här måtten INTE säger

- Att en symbol står i byggd kod betyder att en mall **nämner** den, inte att
  anropet är **kört mot en levande VC**. Ingen av rundans 18 mallar har det.
- Ytdiffen ser bara de symboler `47` valde att namnge. Den mäter täckningen av
  **planen**, inte av API:t.
- Steg-täckningen ärver `48`:s kolumn "Kräver". Där den namnger fel yta blir
  måttet fel åt samma håll — se spec-förslag 2.

---

## 7. Vad som mättes fram som fel i specen

`docs/spec/` ägs av huvudtråden. Här står förslagen, inte ändringarna.

### Förslag 1 — `47` avsnitt 4.4: sju verktyg står på en yta som är mätt trasig

Tabellen i 4.4 föreslår `new_collision_detector`, `test_one_collision`,
`collision_hits`, `bbox_collision`, `collision_settings`,
`new_volume_detector` och `volume_hits` utan att nämna M-35 eller M-36, som
båda skrevs *efter* dokumentet. Sju rader föreslår alltså sju stubbar.
Förslag: flytta dem till avsnitt **7.2** ("möjligt men oprövat") med M-35 och
M-36 som skäl, och lägg `collision_detector_status` i 4.4 i stället, med
noteringen att raderna flyttas tillbaka den dag provet blir grönt.

Samma gäller `collision_settings`: `StopOnCollision` finns i `api.xml` men
**inte på objektet** (M-35). Det är en rad till avsnitt 7.2, inte till 4.4.

### Förslag 2 — `48` P1 steg 6 och 7 namnger fel mätyta

"Kräver" säger `vcCollisionDetector.testMinimumDistance` respektive
`testAllCollisions` + `getHitNodeA`. Efter M-36 är rätt yta
`vcNode.measureDistance`. Stegen är nu byggda (`min_distance`,
`test_collision`) men mäts som otäckta för att kolumnen pekar på den trasiga
ytan. Förslag: byt symbolerna, och skriv i kolumnen "Täckt idag" vilka verktyg
som gör det.

### Förslag 3 — `vcHelpers.Robot.pick` och `.place` saknar helt verktygsförslag

P2 steg 9 har varken byggt verktyg eller föreslaget verktyg. Förslag: en rad i
`47` avsnitt 4.6 — `helper_pick_place`, codegen, write, byggd på
`vcHelpers.Robot.pick`, `place`, `pickFromPallet`, `placeInPattern`,
`graspComponent`. Alla fem finns i indexet.

### Förslag 4 — `47` avsnitt 4.3 föreslår ett verktyg M-13 förbjuder

`install_script_behaviour` byggs aldrig. Förslag: flytta raden till avsnitt
**7.3** ("byggbart men avsiktligt inte föreslaget") med M-13 som skäl, bredvid
`vcScript.convertToByteCode` som redan står där av besläktad anledning.

### Förslag 5 — `formaga.YTOR` provar en yta som inte finns i API-indexet

`formaga.py` rad 28 provar `app.rayIntersect`. `ApiIndex.medlem("vcApplication",
"rayIntersect")` ger **tomt**. Antingen finns metoden i VC utan att stå i
någon av de fyra källfilerna, eller så provar förmågegrinden ett namn som
aldrig kan svara sant. Ingen av de två är avgjord här — den kräver en levande
VC. Förslag: en rad i `36_versioner.md` om att `YTOR` och API-indexet ska
korsprövas mot varandra, och tills det är mätt: `rayIntersect` får inte bära
någon `kraver`-rad.

### Förslag 6 — de 24 robotverktygen är osynliga

`robotik.py` importeras inte av `verktyg/__init__.py`. Modulens docstring
säger att den cell som kopplar in den också bör lägga robotytorna i
`formaga.YTOR`. Förslag: gör inkopplingen till en egen, liten runda —
det är 24 verktyg för ett par raders arbete plus förmågeytorna, och det är
den billigaste ökningen av lista 3 som finns.

### Förslag 7 — `47` avsnitt 8:s sammanfattning är inaktuell

Raden "Byggda verktyg 21 i 2 domäner" och "Totalt bibliotek 345" stämde vid
skrivningen. Nu är talen 95 i 9 domäner (119 i 10 skrivna), och specens 345
räknar inte in de 64 verktyg som byggts under andra namn. Förslag: låt raden
peka på M-47 i stället för på ett fruset tal, så ruttnar den inte igen.

---

## 8. Vad rundan lämnar efter sig

| Sak | Läge |
|---|---|
| Verktyg i registret | 77 → **95** |
| Domäner i registret | 7 → **9** |
| Domäner på noll procent yttäckning | 1 → **0** |
| Prov i `tests/enhet/test_verktyg_simmatning.py` | **506**, varav elva trasiga fixturer |
| Hål stängda i `skrivgrind.MUTERANDE_PREFIX` | **2** (`autoHalt`, `continueRun`) |
| Arbetssteg helt täckta av byggd kod | **18 av 58** |
| Arbetssteg utan Python-API alls | **4 av 58**, alla namngivna i avsnitt 2 |
| Kvar av specens föreslagna verktyg | **290 av 345** i namndiff, **605 av 904** API-symboler |

Och den rad som gäller varje runda härefter: **inget av rundans 18 verktyg har
körts mot en levande VC.** Provat är schemat, argumentvalideringen, routingen,
formågegrinden, korsprovet mot bryggans skrivgrind och korsprovet mot
API-indexet. Att VC svarar som källan säger är oprövat, och det står så här
för att det ska stå någonstans.
