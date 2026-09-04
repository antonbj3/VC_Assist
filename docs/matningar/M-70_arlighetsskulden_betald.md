# M-70 — ärlighetsskulden betald, och mönstret som räknade fel på sig självt

**Datum:** 2026-09-04
**Kravet:** S5 i `docs/spec/96_ingen_skuld.md` — varje mätning bär ett avsnitt om
vad den **inte** visar. Skälet står i [M-66](M-66_skuldregistret.md).
**Rör:** 22 mätningar, `svc/vc_assist_svc/skuld.py`, `tests/enhet/test_skuld.py`,
`docs/matningar/SKULDREGISTER.md`

## Talen

| | Före | Efter |
|---|---:|---:|
| mätningar utan ärlighetsavsnitt | **26** | **1** |
| punkter i registret ur mätningarnas ärlighetsavsnitt | 114 | **319** |
| avsnitt de kommer ur | 33 | 61 |
| mätningar totalt | 51 | 53 |

Före-talen är mätta på trädet vid commit `ce16a00`. Efter-talen är mätta när
registret byggdes om i den commit som lägger den här filen. **De två raderna om
punkter och avsnitt rör sig av sig själva** — sex andra agenter skriver mätningar
i repot samtidigt, totalen växte från 51 till 53 under arbetet, och en del av
punktökningen är deras. Raden som är min att svara för är den översta.

**Mitt eget bidrag, räknat separat:** 22 mätningar fick ett avsnitt
*"Vad som INTE är mätt"* skrivet åt sig, med **150 punkter** tillsammans.
Ytterligare **8 punkter** ur M-44 och M-47 kom in i registret utan att en enda
rad skrevs i de filerna — de stod redan där, och mönstret var blint för dem.

## Det första fyndet är att spärren mätte fel storhet

Uppgiften löd *"24 av 48 mätningar saknar ett sådant avsnitt"*, och två av dem —
M-44 och M-47 — sades ha ärlighetsinnehåll under rubriker mönstret inte känner
igen. Det stämde. Men det var inte två.

Mätt på **samma träd** (`ce16a00`), med de två mönstren:

| Mönster | Mätningar utan ärlighetsavsnitt |
|---|---:|
| det som stod i `skuld.py` | **26** av 51 |
| efter lagningen | **22** av 51 |

Fyra mätningar sade vad de inte visade och räknades ändå som tysta: **M-04**
(*"Öppen fråga, blockerande för fas 1"*), **M-35** (*"Trolig orsak, omätt"*),
**M-44** (*"Räckvidd"*, *"Vad rättelserna medvetet INTE gör"*) och **M-47**
(*"Vad de här måtten INTE säger"*).

### Varför

`_ARLIGHET` är skriven i ASCII, som all kod i det här repot. Mätningarna är
skrivna i riktig svenska. Alltså kunde `rackvidd` aldrig matcha `Räckvidd`,
`oppna fragor` aldrig `Öppna frågor`, `begransningar` aldrig `Begränsningar`,
`forbehall` aldrig `Förbehåll` och `oprovat` aldrig `Oprövat`.

Räknat över repots 432 rubriker: **elva grenar i mönstret, tre som någonsin
fyrade.**

| Gren | Träffar i repot |
|---|---:|
| `vad ... inte ...` | 24 |
| `vad som (fortfarande) inte ...` | 22 |
| `obevisad` | 2 |
| `fynd jag inte` | 1 |
| `oprovat` · `rackvidd` · `forbehall` · `begransningar` · `oppna punkter/fragor` · `kvar att gora` · `vad som ligger utanfor` | **0 var** |

De åtta döda grenarna var inte döda av slump. Två av dem — `rattelserna` och
`rackvidd` — är tillagda **just för att fånga M-44**, och en tredje — `de har` —
**just för att fånga M-47**. Ingen av dem fångade sin fil. `de har` bar dessutom
ett andra fel: rubriken lyder *"Vad de här måtten INTE säger"*, och ordet
`måtten` står mellan ordlistan och `INTE`, så grenen hade missat även en
translittererad rubrik.

Det är **femte gången** samma felklass mäts i det här bygget: M-34 (fel lista
räknad tolv gånger), M-57 (biblioteket fanns hela tiden), `pgrep -f` som matchade
sin egen sökning, M-66 (mönstret som missade numrerade rubriker) och nu det här.
Fjärde och femte gången är **samma regex**, lagad två gånger, båda gångerna för
att den aldrig kördes mot texten den skulle läsa.

### Lagningen

Rubriken normaliseras med NFKD innan den prövas, och den handskrivna ordlistan
`(detta|de har|lintern|tolken|rattelserna|jag)` är ersatt av upp till fyra
godtyckliga ord mellan *Vad* och *inte*. Ingen text är duplicerad i M-44 eller
M-47.

Grinden har nu en **trasig fixtur för sig själv**: tio rubriker hämtade ur repot,
som alla tio föll före lagningen, plus fem negativa. En bar rubrik `## Öppet`
står med flit på fel sida — *"Öppet API"* är en lika rimlig rubrik, och en gren
som fyrar på allt mäter ingenting.

## De allvarligaste hålen i de gamla mätningarna

Fem fynd, i fallande ordning efter vad de kostar om de står kvar.

### 1. M-11: kvaternionsordningen är mätt för en axel, och just den axeln säger inget om de två som kastas om

M-11 slår fast `(x, y, z, w) = (q.Y, q.Z, q.W, q.X)` och kallar felläsningen
förgiftande. Tabellen är mätt för **ren gir kring Z**, fyra vinklar. I varenda
mätpunkt är `q.Y = 0` och `q.Z = 0` — och det är precis de två komponenter
omkastningen flyttar till `x` och `y`.

Datan visar två saker: att `q.X` bär skalären, och att Z-axelns komponent hamnar
i `q.W`. Den visar **ingenting** om vilken av `q.Y` och `q.Z` som är `x`
respektive `y`. En ren nick och en ren roll hade avgjort det på två rader.
Omräkningen sitter i `oga_provtagning._kvat()` med den här tabellen som skäl.

### 2. M-31: talet 125 kom ur ett instrument som inte var prövat mot ett känt svar — i en mätning om ett instrument som inte var prövat mot ett känt svar

M-31 river en linter som bara läste en modul av tolv, bygger om den, och
rapporterar **125 tröskelkonstanter**. Det talet är den nya linterns eget svar,
och den nya lintern var inte prövad mot ett facit.

M-46 gjorde det provet senare, med en AST-genomgång: regexen var blind för
`_TROSKEL`, exponentform (`1e-9`), indragna rader, uttryck (`0.5 * 10`), anrop
(`int(5)`), ordböcker, typannoteringar och två tilldelningar på en rad. Skulden
visade sig inte vara större — den enda verkliga träffen var
`verifiering._FLYTTALSMARGINAL` — men M-31 kunde inte veta det. Mätningen bytte
ett omätt instrument mot ett annat omätt instrument och skrev ned svaret.

Talen 79 och 67 är dessutom **båda** mätta med den nya lintern, så
*"skulden gick från 79 till 67"* mäter en omskrivning, inte en förbättring.

### 3. M-37: det gröna receptet band i den ordning VC råkade räkna upp

M-37 löser det som stått öppet sedan M-14 och visar ett recept som ger
`canConnect True`. Receptet sätter `Container`, `Port` och `PortName` i en
`for`-loop över `falt.Properties` — alltså i den ordning VC råkar räkna upp dem.

M-40 mätte senare att **ordningen är avgörande**: sätts `Container` efter `Port`
blir `Port` till `-1` och `canConnect` svarar falskt utan ett ord. Att M-37 blev
grön säger alltså inte att receptet är ordningssäkert. Det säger att
uppräkningsordningen råkade duga den gången.

M-37:s rättelse av M-16 har samma form: den pekar ut en ogiltig bindning som
orsak till en krasch, men slutet är draget ur att ett **annat** recept fungerar.
Ingen mätning har återskapat kraschen och tagit bort bindningen som enda ändring.

### 4. M-34 rättar ett mätfel och bär ett till i sin huvudtabell

M-34 är mätningen som upptäckte att `len(app.Components)` var fel lista, räknad
tolv gånger. I samma tabell står raden *"Fyrar den automatiska matningen
(`Interval`)? **Nej.** Behållaren är tom över 160 simulerade sekunder."*

Den mätningen är gjord på en matare byggd i en **redan körande** simulering. M-40
mätte att just det gör att en matare aldrig fyrar, hur rätt den än är kopplad.
Talet mätte alltså uppstartsordningen, inte mataren — och det gick inte att se
på talet, precis som det inte gick att se på tolvan.

Samma mätnings slutsats i *Var det står* — att en bana kräver en
transportstyrenhet och att vi därför måste skriva styrlogiken själva — håller
inte. M-40 fick linjen att mata utan att någon transportstyrenhet skrevs.

### 5. Rader som ser ut som mätningar av en storhet men är mätningar av en annan

* **M-01:** *"`threading` — importerbar"*. Det mäter att modulen går att
  importera. Trådmodellen i `31_brygga_protokoll.md` byggdes på raden, och
  M-04 och M-07 mätte sedan att bakgrundstrådar **svälter**.
* **M-06:** slutsatsen att `SimSpeed` *"inte gjorde något"* är dragen under
  `sim.run()`. M-08 mätte att `SimSpeed` styr den **interaktiva** uppspelningen.
  Fel körsätt prövades, och slutsatsen skrevs om egenskapen i allmänhet.
* **M-35:** *"kollisionsdetektorn fyrar inte"* är rätt observation och fel
  diagnos. M-36 mätte att `NodeListA` tar emot en lista och **tömmer** den.
  Varje rad i M-35:s tabell mäter en tom nodlista, inte geometri.
* **M-16:** rubriken *"`canConnect` dödar pumpen"* är motbevisad i M-37 och står
  kvar oförändrad i brödtexten. Motbeviset står nu i ärlighetsavsnittet.
* **M-33:** världsenheten är mätt. **Tyngdaccelerationens** enhet är det inte, och
  `ext/vc_addon/vc_assist/oga_harledning.py` bär än i dag
  `G_MS2 = 9.81  # OMATT ANTAGANDE`. Ögats fallhastighetsgrindar hänger på det.

## Vad som gjordes med M-44 och M-47

Ingenting i filerna. De sade redan vad de inte visade — M-44 under *"Räckvidd"*
och *"Vad rättelserna medvetet INTE gör"*, M-47 under *"Vad de här måtten INTE
säger"* — och att skriva ett nytt avsnitt hade varit att duplicera text för att
blidka en trasig mätare. Mönstret lagades i stället, och de åtta punkterna kom
in i registret.

## Vad som INTE är mätt

* **Om punkterna jag skrev är sanna.** 150 påståenden om vad 22 mätningar inte
  visar är lästa ur mätningarnas egen text och ur de mätningar som kom efter dem.
  Ingen av dem är prövad mot VC. En punkt som säger *"detta är inte mätt"* kan
  vara fel på två sätt: saken kan vara mätt någon annanstans, eller vara mätt och
  sedan motbevisad.
* **Om listan är komplett.** Jag skrev de hål jag såg. En mätning kan bära fler,
  och de allvarligaste är per definition de ingen har formulerat. Registret mäter
  vad vi har skrivit ned, aldrig vad som finns.
* **De två mönstren jämförs på ett träd, inte på en mängd rubriker med känt
  facit.** Att det nya mönstret godkänner åtta rubriker till är kontrollerat för
  hand, rubrik för rubrik. Att det inte godkänner något som **inte** är ett
  ärlighetsavsnitt är prövat mot fem negativa fall — det är en fixtur, inte ett
  svep. Gränsen mot en bar rubrik `## Öppet` är dragen av mig, inte mätt.
* **Fyra ord är en gissning.** Grenen `vad ... inte` tillåter upp till fyra ord
  emellan. Fyra räcker för varje rubrik som finns i repot i dag. Talet är valt så,
  inte mätt fram, och en rubrik med fem ord emellan faller tyst.
* **M-50 är kvar och är inte min.** Den är en halvskriven mätning
  (*"Utfallet — fylls i av körningen"*) som en annan agent redigerade i
  arbetsträdet medan jag arbetade. Att skriva ett ärlighetsavsnitt i någon annans
  ofärdiga fil hade riskerat att plantera ett påstående som var falskt en timme
  senare. Skulden är alltså **inte** noll, den är **ett**, och den ettan har en
  ägare.
* **Taket är satt i ett rörligt repo.** `UTAN_ARLIGHETSAVSNITT = 1` är exakt lika
  med verkligheten när det skrevs. Under arbetet sänkte en annan agent samma tal
  två gånger (till 16 och sedan till 11) medan mina commits landade — spärren har
  alltså redan visat att den kan följa fel storhet när flera händer räknar samma
  sak. Nästa mätning som skrivs utan ärlighetsavsnitt gör provet rött, och det är
  meningen.
* **Ingenting är mätt i VC.** Hela det här arbetet är textarbete på disk. Ingen
  VC-instans har rörts, och ingen av de gamla mätningarna är körd om.
* **Sviten är grön, men inte stilla.** Mitt i arbetet var två prov röda och inte
  mina — `test_layout.py::test_varje_publikt_namn_har_en_konsument` och
  `test_troskelharkomst.py::test_ingen_troskel_pekar_pa_en_matning_som_inte_finns`
  (fem trösklar pekade på M-62 och M-63, som inte fanns då). Vid sista körningen
  var båda gröna igen, för att andra agenter hade landat sitt arbete. Ett grönt
  slutläge i ett repo där sex händer skriver samtidigt säger alltså något om
  ögonblicket, inte om att ingenting är trasigt: `tests/enhet/test_plan.py` och
  `test_plan_villkor.py` går fortfarande inte att samla in
  (`ImportError: cannot import name 'Villkor'`) och är uteslutna ur körningen.
