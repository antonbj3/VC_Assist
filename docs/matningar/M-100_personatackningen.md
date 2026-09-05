# M-100 — Personatäckningen: sju profiler, 228 arbetssteg, mätt mot registret

Fas 19. Körning: `python3 tests/protocol/kor_fas19_tackning.py`
(kräver inte VC). Protokoll: `tests/protocol/fas19_personatackningen.md`.
Nämnare: `docs/spec/48_personaprofiler.md`. Domare:
`svc/vc_assist_svc/personatackning.py`. Prov:
`tests/enhet/test_personatackning.py` (30 st).

Mätt 2026-09-05 mot **3444 API-symboler**, **10294 .NET-namn** och
**122 registrerade verktyg**.

---

## 1. Frågan, och varför den inte var ställd

`48_personaprofiler.md` sa själv att den var *"underlag för täckningsanalysen
i 47"*. Analysen hade aldrig körts. Båda filerna — 186 + 1024 rader — hade
ingen fas. Vi visste hur stor VC:s API-yta är (204 typer, 966 metoder), men
inte hur stor andel av **arbetet** verktygen täcker, för arbetet fanns bara
som prosa.

Skillnaden är inte akademisk. Ett verktyg per API-typ är en räkning av vad som
*går* att bygga. Ett verktyg per arbetssteg är en räkning av vad någon
*behöver*. De två talen pekar åt olika håll, och avsnitt 6 nedan visar hur
långt isär.

## 2. Talen

Sju profiler, 228 arbetssteg. **Nämnaren är alla steg** — ett steg vi inte
klarar står kvar som `saknas`.

| | Profil | Steg | Täckta | Utanför räckvidd | Obyggda | Andel av allt | Andel inom räckhåll |
|---|---|---|---|---|---|---|---|
| P1 | Layoutplaneraren | 37 | 23 | 1 | 13 | 62 % | 23/36 = 64 % |
| P2 | Robotprogrammeraren | 36 | 30 | 1 | 5 | 83 % | 30/35 = 86 % |
| P3 | Driftsättaren | 35 | 31 | 2 | 2 | 89 % | 31/33 = 94 % |
| P4 | Flödesingenjören | 37 | 25 | 1 | 11 | 68 % | 25/36 = 69 % |
| P5 | Lösningsarkitekten som säljer | 27 | 11 | 1 | 15 | 41 % | 11/26 = 42 % |
| P6 | Komponentbyggaren | 33 | 9 | 1 | 23 | 27 % | 9/32 = 28 % |
| P7 | Utbildaren | 23 | 15 | 1 | 7 | 65 % | 15/22 = 68 % |
| | **summa** | **228** | **144** | **8** | **76** | **63 %** | 144/220 = **65 %** |

`täckta + utanför + obyggda = steg` för varje rad. En räknare som inte
summerar till helheten mäter inte helheten.

**Läsningen, i klartext.** Driftsättningen är nästan färdig (89 %) därför att
signal-, simulerings- och mätdomänerna byggdes för bänken. Robotprogrammeraren
följer tätt (83 %). Den som ska **sälja** får hjälp med fyra av tio steg, och
den som ska **bygga en komponent** med knappt tre av tio. Bilder, film, vyer,
material, lager, mått och noter — hela presentationssidan — finns inte som ett
enda verktyg. Geometrisidan likaså.

## 3. Vad som ligger utanför räckvidd

Åtta steg av 228 (4 %). Det talet är lika viktigt som täckningen: det är
arbete användaren gör i programmet och som agenten **inte kan göra åt hen**.

| Profil | Markör | Steg | Belägg |
|---|---|---|---|
| P1 | `UI` | bläddra i eCatalog | ingen katalogyta i Python-API:t; bara `vcCommand.(Deprecated) rebuildECatalog` |
| P2 | `.NET` | exportera till robotens eget språk | `VisualComponents.Create3D.IRobotConverter`; sökning på `converter`/`postprocess` i indexet ger 0 |
| P3 | `.NET` | koppla scenen mot PLC:n | `Connectivity.Core.IServerHandler`, `Connectivity.OpcUA.IOpcUAServer`; `connectivity`/`plc` ger 0 träffar i indexet |
| P3 | `UI` | ställa in kopplingen i Connectivity-fliken | samma gräns, gränssnittssidan |
| P4 | `UI` | ställa in statistikpanelen | panelens egna inställningar |
| P5 | `.NET` | exportera animation till kundens verktyg | `IAnimationRecorder`, `IFBXRecorder` |
| P6 | `UI` | CAD-importens detaljnivå | dialogen; `ICADReader` bakom |
| P7 | `UI` | gå igenom menyerna med eleven | gränssnittet självt |

Alla åtta är **bevisade** utanför: `.NET`-namnen slås upp i
`docs/referens/vc_dotnet/*.xml` och måste samtidigt saknas i Python-indexet;
`UI`-namnen måste saknas i Python-indexet även med annat skiftläge.

## 4. Rättelsen grinden gjorde i sin egen källa

Den gamla `48` skrev om CAD-import: *".NET/UI (`ICADReader`), inte i
Python-API:t"*. **Det var fel.** `vcCommand.loadGeometryAsComponent` och
`vcCommand.loadLayoutToPosition` finns i indexet. Steget är alltså inom
räckhåll och bara obyggt, och det ligger nu i nämnaren i stället för utanför.

Det var precis den felklass fasen byggdes mot — ett steg lyft ur nämnaren på
ett antagande — och den fanns i grindens egen källa.

## 5. Utbildarens egna ytor: ett refuterat påstående

Den gamla `48` motiverade att utbildaren inte fick en egen profil med att hon
*"kräver inte en enda ytterligare API-yta"* utöver säljaren. Påståendet är nu
prövat mekaniskt: **P7 pekar på 25 API-namn, varav 15 inte finns i P5.**

`vcSimulation.setInitialState`, `restoreInitialState`, `update`, `halt`,
`SimTime`, `vcExecutor.callStatement`, `vcRoutine.Statements`,
`vcApplication.startJogging`, `messageBox`, `vcBoolSignal.Value`,
`vcSignal.Type`, `vcJoint.MinValue`, `MaxValue`, `vcNode.measureDistance`,
`vcApplication.Components`.

Påståendet är **falskt**. Att återställa efter en elev och att stega en rutin
är eget arbete, och det syns bara när profilen skrivs ut.

## 6. Byggd kapacitet ingen bad om

**6 av 122 verktyg (5 %)** pekas inte ut av något arbetssteg:

| Verktyg | Domän | Kommentar |
|---|---|---|
| `bench_task`, `bench_compare`, `eyes_report` | `eyes` | tjänar bänken och ögat, inte en VC-användare. Väntat |
| `component_info` | `scene` | överlappar `list_properties` + `get_transform` |
| `frame_owner_node` | `measure` | ingen profils steg frågar efter ramägaren |
| `ray_cast` | `measure` | ingen profils steg skjuter en stråle |

Tre av sex är alltså vår egen mätapparat och hör inte hemma i en persona. De
tre andra är verklig kapacitet utan uttalat behov. **Det är ett litet tal, och
det är den goda nyheten:** bygget har inte drivit iväg från arbetet.

Från andra hållet ser det värre ut. `47_verktygstackning.md` avsnitt 4 föreslog
345 verktygsnamn. **55 av dem finns i registret. 67 av registrets 122 verktyg
föreslogs aldrig.** Byggordningen i avsnitt 6 följdes alltså inte, och den har
inte skrivits om efteråt. Det står nu i `47` avsnitt 9.

## 7. Grinden, och vad som gör den svår att lura

En täckningssiffra är den lättaste grinden att göra meningslös: nämnaren kan
tyst krympa till det vi klarar. Fyra spärrar, alla mekaniska:

| Spärr | Fäller | Kod |
|---|---|---|
| Golv per profil | ett steg som tystnat bort | `NAMNAREN_KRYMPTE` |
| `KANDA_PROFILER` | en struken profil | `PROFIL_SAKNAS` |
| Löpande numrering | ett urklippt mittsteg | `TRASIG_NUMRERING` |
| `UI`/`.NET` prövas mot båda indexen | ett skriptbart steg som ställs utanför | `FALSK_UTANFOR` |

**Femton trasiga fall körs vid varje körning, var och en med sin egen kod**,
plus tre specer som ska avvisas redan i läsningen. Alla 18 föll rätt. En grön
kontrollfixtur körs först: går den inte igenom mäter fixturerna domaren i
stället för specen.

Fasens skarpaste prov är `test_ett_borttaget_steg_ger_rott_trots_hogre_procent`.
Det stryker ett **obyggt** steg ur P6 (profilen med lägst täckning, alltså där
frestelsen är störst), numrerar om resten så att inget hål syns, **mäter att
täckningen därmed steg från 9/33 = 27,3 % till 9/32 = 28,1 %** — och kräver
ändå ett rött. Provet passerar bara om båda sakerna är sanna samtidigt: att
siffran gick upp, och att grinden ändå fällde. Utan spärren hade raderingen
sett ut som framsteg.

Regeln som gör verktygens `effect` mekanisk: ett steg vars verkan är `ändrar`
kan inte täckas av enbart läsande verktyg (`FEL_VERKAN`). Omvänt är tillåtet —
`measure_distance` är deklarerad `write` för att den bygger en
kollisionsdetektor i scenen, och får därför täcka ett läsande steg.

## 8. Utfall

| | |
|---|---|
| Specen själv | 0 fällningar |
| Kontrollfixturen | grön |
| Trasiga fall fällda | 15 av 15 |
| Oläsbara specer avvisade | 3 av 3 |
| Enhetsprov | 30 av 30 |
| **Fas 19** | **GRÖN** |

---

## LIMITS

* **Stegen är oviktade.** Att spara en layout och att bygga ett helt
  processflöde räknas som ett steg var. 63 % är *andel arbetssteg*, inte
  andel arbete och absolut inte andel tid. Den som läser talet som "två
  tredjedelar av jobbet" läser in en viktning som inte är mätt, och som skulle
  kräva en tidsstudie vi inte har.
* **`UI:`-markörer går att bevisa falska, inte sanna.** Grinden fäller en
  `UI`-markör vars namn finns i Python-API:t, men en påhittad `UI:`-token
  passerar. Den öppna riktningen kan bara göra nämnaren **större**, aldrig
  mindre — men den är öppen.
* **Ingenting kördes mot en levande VC.** Att ett verktyg står i registret
  betyder att det är definierat, schemaprövat och (för fas 5:s 21) prövat mot
  bryggan. Det betyder **inte** att det gör rätt sak i just det arbetssteg
  profilen beskriver. Fasen mäter täckning, inte kvalitet. Ett steg som räknas
  täckt kan vara täckt av ett verktyg som fungerar dåligt.
* **Sju profiler är inte alla användare.** Underhållstekniker,
  säkerhetsansvarig, inköpare och kvalitetsingenjör finns inte i nämnaren.
  Golvet hindrar bara att de sju befintliga krymper; det säger ingenting om de
  som saknas. Talet 63 % är alltså ett tak för hur mycket vi kan påstå, inte
  ett mått på hela användningen.
* **Stegen är skrivna av mig, inte av en användare.** Ingen layoutplanerare
  har läst P1. Listorna är härledda ur API-ytan, VC:s egen dokumentation och
  projektets bänk — inte ur en observation av någon som arbetar. Det är den
  största enskilda osäkerheten i nämnaren, och den går bara att laga genom att
  fråga någon som gör arbetet.
* **`component_info`, `frame_owner_node` och `ray_cast` kan vara felaktigt
  oanvända.** De tre är verkliga verktyg som inget arbetssteg pekar på. Det
  kan lika gärna betyda att stegen saknas som att verktygen är onödiga —
  mätningen skiljer inte på de två.
* **Talet 4 % utanför räckvidd är sannolikt för lågt.** Det räknar bara de
  steg jag *skrev* som UI/.NET. Hela gränssnittsarbetet — att välja, panorera,
  zooma, dra, öppna paneler — är inte nedskrivet som arbetssteg alls.
