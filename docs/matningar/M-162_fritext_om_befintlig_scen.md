# M-162 — fri text om en befintlig scen: diagnos, ändring, optimering

**Datum:** 2026-09-05
**Rigg:** `tests/enhet/test_scenarbete.py` (27 prov, ingen VC, inget nätverk,
ingen modellkvot). Mätsvepet i §2 kördes med `PYTHONPATH=svc python3` mot
`plan/lasning.py`, `plan/forfining.py` och `verktyg/register.py` i repot.
**Prövar:** `svc/vc_assist_svc/scenarbete/{sparr,fragor,avsikt,diagnos}.py`

**beskriver:** `svc/vc_assist_svc/scenarbete/sparr.py`,
`svc/vc_assist_svc/scenarbete/fragor.py`,
`svc/vc_assist_svc/scenarbete/avsikt.py`,
`svc/vc_assist_svc/scenarbete/diagnos.py`,
`tests/enhet/test_scenarbete.py`

---

## Frågan

Fritextvägen fanns bara till att BYGGA något nytt. Vägen från en lös mening om
en scen som **redan står där** till att arbetet blir gjort fanns inte. Tre
intentioner, och de är inte samma sak:

1. **DIAGNOS** — *"varför svälter station 3?"* Ingen ändring.
2. **ÄNDRING** — *"byt det där gripdonet."* En bestämd operation.
3. **OPTIMERING** — *"snabba den här linan."* Ändra, mät om, jämför.

## Resultat

### 1. Vad som byggdes, och vad som inte gjorde det

| Intention | Läge | Var den bor |
|---|---|---|
| 1 DIAGNOS | **byggd**, hela vägen ur ögats rader | `diagnos.py` |
| 2 ÄNDRING | **grindarna byggda**; vägen ut går genom harnessen som vanligt | `sparr.py`, `avsikt.py` |
| 3 OPTIMERING | **inte byggd**, och avvisas med det skälet utskrivet | `avsikt.SKAL_OPTIMERING` |

Intention 3 faller inte igenom som en ändring. En optimering som utförs utan
ommätningen är en ändring utan facit, och `granska()` dömer den `OKANT` med
uppmaningen att dela meningen i en diagnos och en ändring.

### 2. Varför den gamla vägen inte gick att bygga vidare på

`plan/forfining.py:ur_fritext` beskrevs som "fri text till byggspec". Den är en
nyckelordsmatchare: `ORDBOK` är 32 hårdkodade svenska tupler. Tre mätningar:

| Vad | Mätt |
|---|---|
| ORDBOK-ord som träffar på det **svenska** ordet | **32 av 32** |
| … som träffar på den **engelska** motsvarigheten | **3 av 32** |
| De tre som klarar sig | `robot`, `press`, `klt` — lånord, inte förmåga |

**Och det farligaste fyndet: ordlistan faller inte stängt, den faller tyst
fel.** Ordlistans påstådda säkerhet är att den inte kan hitta på — saknas
ordet blir det en fråga. Den egenskapen **håller inte över språk**. Talet är
språkneutralt och läses; det svenska ord som ger talet sin *mening* tappas:

| Svenska | Läses som | Engelska | Läses som |
|---|---|---|---|
| `högst 2x2 m` | `le 2000` | `at most 2x2 m` | **`eq 2000`** |
| `max 2x2 m` | `le 2000` | `no more than 2x2 m` | **`eq 2000`** |
| `maximalt 2x2 m` | `le 2000` | `maximum 2x2 m` | **`eq 2000`** |
| `inom 2x2 m` | `le 2000` | `within 2x2 m` | **`eq 2000`** |

**4 av 4**: samma tal, ett annat krav, och **ingen fråga ställd**. En cell på
1500 mm uppfyller *"at most 2x2 m"* och bryter mot `eq 2000`. Det är inte en
saknad funktion — det är ett tyst felläst krav, alltså precis det
`forfining.py`:s egen docstring lovar att aldrig göra.

**Ordlistan är inte ens komplett för svenska.** `ANDELSER` i `lasning.py` bär
inte presens-r. Av 11 verbstammar i `PROCESSORD` läses **11 av 11** inte i sin
vanligaste form: *"en station som svetsar"* ger noll processer, *"svetsning"*
ger en. Samma för `plockar`, `monterar`, `skruvar`, `pressar`, `limmar`,
`målar`, `lackerar`, `packar`, `spänner`, `kontrollerar`.

### 3. Spärren, byggd före tolken

Garantin *"inget tyst val"* låg i att tolken var **oförmögen att gissa**. Den
flyttas till grinden, så att tolken får vara en språkmodell. Tre oberoende lås:

**LÄSSPÄRREN** — en diagnos rör aldrig scenen. Spärren är `Urval`, inte en
instruktion i en prompt. Mätt på registret:

| | Antal |
|---|---|
| Registrerade verktyg | **122** |
| `effect=read` — kvar på i en diagnos | **69** |
| `effect=write` — **avslagna** | **53** |

Tre lager, och de är oberoende: (1) `Urval.openai_verktyg()` exponerar aldrig
de 53 för modellen, (2) `Utforare.utfor()` kastar `Avstangt` på namnet ändå,
(3) bryggans `skrivgrind` avvisar skrivande kod. Frågan ställs till verktygets
**deklarerade `effect`** — samma fält som utförarens routingtabell läser (I12),
och oföränderligt efter registrering.

**HÄRKOMSTGRINDEN** — varje fält modellen producerar bär en härledning eller är
märkt som en fråga. Ingen tredje väg. Fyra källor (`begaran`, `scen`, `ogat`,
`fraga`), och ingen av dem betyder "vi tyckte så". Citat ur begäran prövas med
**samma** funktion som planeringslagret (`harkomst.normalisera`), så de två
lagren kan inte drifta isär om vad ett citat är. Utsagor om scenen delegeras
till `harness/verifiering.Grund`, som redan är turens facit och redan mätt i
fas 22.

**ENTYDIGHETEN** — flera kandidater i den lästa scenen är en FRÅGA, aldrig ett
val.

### 4. Fyra domar, och ingen heter "gör det"

Formen är ärvd ordagrant ur `plan/motsagelse.py`: `DIAGNOS`, `ANDRING`,
`FRAGA`, `OKANT`. `OKANT` är aldrig ett godkännande (I3) —
`sparr.far_utforas()` säger nej, och `urval_for_avsikt()` stänger **alla 122**
verktygen.

**Ordningsfel som mätningen fångade i mitt eget bygge:** första versionen
prövade existens före tvetydighet. *"Byt det där gripdonet"* dömdes då `OKANT`
("gripdon finns inte") i stället för `FRAGA` ("scenen har tre"). Fel besked:
operatören hade namngett något som finns tre gånger, inte något som inte finns.
Uppslagningen i scenen kommer nu först, och antalet träffar avgör domen.

### 5. Tre sorters "går inte att avgöra", med motsatta åtgärder

Ett `OKANT` utan sort döljer att åtgärderna är motsatta. Mätt på diagnosvägen:

| Sort | Vad som löser det | Diagnosfall |
|---|---|---|
| `OKANT_MATBART` | en mätning | ingen `STARVED`-rad — kör om med kravet deklarerat |
| `OKANT_ANNAN_SORT` | **inte** mer av samma mätning; en annan observabel | `BOTTLENECK` pekar på stationen själv — rapporten bär ingen topologi |
| `OKANT_OLOSLIGT` | frågan måste omformuleras | stationen finns inte i det som mättes |

### 6. Vem som får svara på en öppen fråga

Hämtat ur `sibling-project En fråga som
en **mätning** kan svara på får aldrig gå till operatören:

* `MATNING` — *"varför svälter station 3?"* Ögat kör den. Konstruktionen
  **kastar** om ingen sådan fråga namnger ett verktyg, och om något av de
  namngivna verktygen skriver — annars vore en "mätning" en väg runt lässpärren.
* `OPERATORSVAL` — *"vilket av de tre gripdonen menade du?"* Ingen mätning i
  världen avgör vad han menade.

Frågor grupperas i rundor om högst **4** (`MAX_FRAGOR_PER_RUNDA`), adopterat ur
`sibling-project/lib/negotiation_protocol.py`.

### 7. Budgeten är en summa, inte en tabell

"Compute i proportion till komplexiteten" blir annars två påhittade tal. Här
räknas budgeten ur de anrop turen **måste** göra, och varje steg bär den regel
som kräver det:

| Avsikt | Nödvändiga steg | Regeln bakom varje | Rundor |
|---|---|---|---|
| DIAGNOS (med mål) | 3 | I9 (läs scenen), I9 (läs målet), I1 (ögat fäller domen) | **4** |
| ÄNDRING | 4 | ARB-001 ×2, I12, **ARB-003/FAL-005 (M-09: VC sväljer fel tyst)** | **5** |

Plus en runda för slutsvaret (`24_samtalsloopen.md`). Taket är loopens eget
`MAX_RUNDOR = 10` (ärvt, `20_arv.md`).

Varje budget bär ett **`status`**-fält, formen lånad ur
`sibling-project `UPPNADD`
med namngiven bevis-körning, eller `HYPOTES` med `bevis: None`. Båda de byggda
avsikterna står i dag på **`HYPOTES`** — se LIMITS.

### 8. Grindarna är mutationsprövade

En grind som aldrig fällt är oprövad (S2). Varje grind neutraliserades i tur
och ordning och dess fixtur gick röd:

| Mutation | Fixtur som blev röd |
|---|---|
| lässpärren släpper igenom skrivverktyg | (a) diagnos som ändrar scenen — **2 prov röda** |
| entydigheten väljer första kandidaten | (b) tvetydig ändring |
| härkomstgrinden släpper fält utan härkomst | (c) ändring utan belägg |
| `far_utforas` släpper `OKANT` | OKANT stänger allt |
| diagnosen svarar "ingen svält" i stället för `OKANT` | tystnad som godkännande |

Återställd: **27 av 27 gröna**.

## LIMITS

* **Ingen språkmodell har körts genom den här vägen.** Modellkvoten är knapp
  och kö A har företräde (RATTELSER 2026-09-05 16:25/18:35). Allt som mätts är
  **grindarna** — spärren, härkomstkontrollen, entydigheten, diagnosen ur
  ögats rader — mot `AttrappModell` och `Attrappkanal`. Att en riktig modell
  producerar ett *avsiktspåstående* av rätt form är **oprövat**. Det är den
  enda kvarvarande frågan för intention 1.
* **Budgetens rundtal är HYPOTES, inte UPPNÅDD.** Stegen är härledda ur
  grindar som redan är mätta (I9, I1, M-09), men att 4 respektive 5 rundor
  **räcker** är inte prövat mot en enda skarp körning. `Budget.bevis` är
  `None`, och koden säger det själv.
* **`MAX_FRAGOR_PER_RUNDA = 4` är adopterat, inte mätt här.** Talet kommer ur
  `sibling-project/lib/negotiation_protocol.py`. Ingen mätning i det här repot
  säger att fyra är rätt.
* **Intention 3 (optimering) är inte byggd.** Den kräver en sluten slinga:
  ändra, kör om simuleringen, läsa ögat igen, jämföra mot ett facit från före.
  Ingen del av den finns.
* **Intention 2 är gindarna, inte vägen ut.** Att en ändring *får* utföras är
  mätt. Att den faktiskt utförs korrekt genom godkännandekön mot en levande VC
  är inte prövat här — den vägen är harnessens och mätt i fas 22.
* **Diagnosen läser en rapport, den startar ingen körning.** Finns ingen
  ögonrapport svarar den `OKANT_MATBART` och namnger vad som skulle mäta det.
  Att faktiskt köra ögat är inte automatiserat i den här vägen.
* **Scenläget matas in, det läses inte automatiskt.** `Scenlage` är
  (namn, typ)-par som någon annan hämtat med `list_components`. Kopplingen
  från ett verkligt verktygssvar till ett `Scenlage` är inte byggd.
* **Ordbokens språklås är mätt på 32 uppslagna svensk-engelska par**, valda av
  mig ur ORDBOK:s egna ord. Ett annat par-urval ger ett annat tal. Det som
  **inte** beror på urvalet är modifierarfyndet (`le` → `eq`), som är
  4 av 4 och en semantisk skillnad, inte en täckningssiffra.
* **Ingen mätning av hur ofta en verklig operatörsmening är tvetydig.** Att
  entydighetsgrinden fäller rätt är mätt; hur ofta den fäller i drift är det
  inte.
