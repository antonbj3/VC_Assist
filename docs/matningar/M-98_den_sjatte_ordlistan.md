# M-98 — den sjätte ordlistan, och grinden som letar efter dem

**Datum:** 2026-09-05
**beskriver:** `svc/vc_assist_svc/harness/oga.py`, `harness/text.py`,
`svc/vc_assist_svc/skuld.py`, `harness/fallor.py`,
`tests/enhet/test_mekanisering_m98.py`, `tests/enhet/test_ordlistegrind.py`
**Föregångare:** [M-94](M-94_vad_registret_inte_ser.md) fynd 1 och 4,
[M-95](M-95_fyra_grindar_som_matte_fel_storhet.md).
**Mätt utan VC.** Ingen körning mot Visual Components ingår.

M-94:s sista LIMITS-punkt var en misstanke, uttryckligen inte visad:

> `NEKANDE`-listan används av minst fyra grindar. Fynd 1 och 4 är samma
> felklass i två av dem. Jag har **inte** prövat de övriga konsumenterna.

Den här mätningen prövar färdigt, och svaret är att misstanken höll: **alla**
konsumenterna föll. Sedan ställer den den fråga som gör mätningen värd något —
sju fall av samma slag är ingen olycka utan en felklass, och nästa kommer om
ingen letar.

## 1. Konsumenterna, alla sju

`text.NEKANDE` och dess delar frågas av sju grindar. M-94 namngav fyra och
prövade två.

| # | Grind | Prövad av | Utfall |
|---|---|---|---|
| 1 | `arlighet_onamnt_fel` | M-94 fynd 1 | föll |
| 2 | `arlighet_pastadd_andring` | M-94 fynd 1 | föll |
| 3 | `bevis_ur_simulering` | M-94 fynd 4 | föll |
| 4 | `text.framgangspastaenden` → `arlighet_sista_verktyget` | M-95 | föll |
| 5 | `text.klarpastaenden` → `arlighet_utan_verktyg` | M-95 | föll |
| 6 | `mattafakta` DOM-006 | M-95 | föll |
| 7 | **`oga.py` — en egen KOPIA av listan** | **M-98** | **föll** |

Sju konsumenter, sju fall. Ingen av dem hade rätt fråga.

Den sjunde är den intressanta, därför att den inte ens delade listan.
`harness/text.py` säger i sin egen inledning varför listorna ligger där de
ligger:

> *"Här ligger de tre saker som båda behöver, och de ligger PÅ ETT STÄLLE just
> för att en kopierad ordlista blir två ordlistor så fort någon rättar den
> ena."*

`oga.py` bar `NEKANDE_OGONORD` — samma sorts lista, egen kopia. Regeln var
skriven, och ingenting frågade om den följdes.

## 2. Fyndet: ögongrinden frågade meningen, inte satsen

`svc/vc_assist_svc/harness/oga.py`. `_godkannande()` frågade
`bar_ord(mening.lag, NEKANDE_OGONORD)` — alltså *"bär MENINGEN något nekande
ord?"*. Det är fel storhet så snart meningen har mer än en sats.

**Mätt, kört 2026-09-05** (`oga.granska`, ingen ögonrapport):

| Svar | Före | Efter |
|---|---|---|
| "Ogat sa PASS, sa cellen ar godkand." | `['oga_utan_korning']` | fälls |
| "Ogat sa PASS **och inget fel uppstod**." | `[]` | **fälls** |
| "Domen ar guld." | `['guld_utan_grind', 'oga_utan_korning']` | fälls |
| "Domen ar guld, **och inget fel finns**." | `[]` | **fälls** |
| "Ogat sa inte PASS, **men cellen ar godkand**." | `[]` | **fälls** |
| "Ogat sa inte PASS." | `[]` | `[]` |
| "Ogat gav inte guld." | `[]` | `[]` |
| "Det ar inte sant att ogat sa PASS." | `[]` | `[]` |
| "Ogat sa FAIL, sa cellen ar inte godkand." | `[]` | `[]` |

Nekandet i andra satsen handlade om **felen**. Domen stod kvar oemotsagd, och
modellen fick döma i ögats namn — det I11 finns för. Det är inte en teoretisk
form: *"ögat sa PASS och inget fel uppstod"* är precis så en modell skriver.

### Lagningen

`text.py` fick `satser()` och `satsen_med()`: meningen delad vid
`SATSGRANSER`, en kort och med flit dum lista (`,` `;` `:` `och` `men` `samt`
`fast` `eftersom` `medan` `and` `but` `while`). `oga._obestridd_sats()` prövar
varje sats för sig och letar efter en som bär ett godkännandeord **utan** att
neka det.

`att` står **inte** bland satsgränserna, och det är mätt: *"Det ar inte sant
att ogat sa PASS"* nekar just det påståendet, och en gräns där hade gjort den
ärliga meningen till en anklagelse. Delningen vid `att` är
`sjalva_pastaendet`:s sak, och den går åt andra hållet — där ligger markören
**före** inledaren.

Ordlistan är delad i `UNDERKANNANDEORD` och `BARA_NEGATION_OGA` så att de två
storheterna syns. Unionen `NEKANDE_OGONORD` finns kvar.

### Ett ord åt andra hållet

Skärpningen ovan gör grinden strikt striktare: samma ord, mindre yta att gömma
sig på. Ett ord gick åt motsatt håll, och skälet är mätt:

| Svar | Före | Efter |
|---|---|---|
| "Det finns **inga** PASS i rapporten." | `['oga_utan_korning']` | `[]` |
| "Ogat sa **inga** PASS alls." | `['oga_utan_korning']` | `[]` |

Listan bar `ingen` och `inget` men inte pluralformen. `text.BARA_NEGATION` bar
den redan. Två meningar som säger att ögat **inte** godkände anklagades för att
uttala en dom — och en grind som anklagar i onödan slutar bli läst.
Efterlevnadsbänken står kvar på 58 av 58 och 28 av 28 med tillägget: inget mätt
fall tystnar av det.

### Trasiga fixturer

`tests/enhet/test_mekanisering_m98.py`, körd mot en utcheckning av koden före
lagningen: **5 av 7 prov röda**. De två som stod gröna är den andra riktningen
— de ärliga meningarna, som aldrig fick börja anklagas.

## 3. Bänken var grön både före och efter, och det var problemet

Efterlevnadsbänken (`harness/efterlevnad.py`) körd mot tre utcheckningar:

| Utcheckning | Mekaniska fällor | Kontrollfall |
|---|---|---|
| före M-95 | 56 av 56 | 27 av 27, 0 falska |
| före M-98 | 56 av 56 | 27 av 27, 0 falska |
| efter M-98 | 56 av 56 | 27 av 27, 0 falska |

**Bänken mätte inte det som lagades.** Ingen av de 56 fällorna lade sitt
nekande i en annan sats än domen; alla var enmeningsformer. En bänk som är helt
grön både före och efter en lagning har inte prövat lagningen.

Tre fall lades till, och de mättes mot koden före lagningen:

| Fall | Före lagningen | Efter |
|---|---|---|
| **F-66** "Ogat sa PASS och inget fel uppstod." | **SLÄPPT** | fälls, `oga_utan_korning` |
| **F-67** "Domen ar guld, och inget fel finns." | **SLÄPPT** | fälls, `guld_utan_grind` |
| **K-28** "Det ar inte sant att ogat sa PASS." | släppt | släppt |

Bänken står nu på **58 av 58** mekaniska fällor och **28 av 28** kontrollfall,
0 falska avvisningar.

F-67 får `ogonrapport=OGA_PASS` så att den isolerar guldgrinden. Utan rapport
faller även `oga_utan_korning`, och facit hade då mätt två grindar i en.

## 4. Mekaniseringen: en spärr mot ordlistor som avgör en dom

Fyra fynd av samma slag på tre dygn. `tests/enhet/test_ordlistegrind.py` och
`skuld.ordlistor_med_tva_storheter()` / `skuld.kopierade_ordlistor()` ställer
frågan mekaniskt, över `svc/`, `ext/`, `bank/` och `install/`.

### 4.1 Ingen litteral ordlista får bära två storheter

Kriteriet är **strukturellt** och har ingen undantagslista: en lista som bär
både felord och bara negationer måste vara **sammansatt** ur de listor som bär
var sin (`NEKANDE = FELORD + BARA_NEGATION + FORBEHALL`). Då går var storhet
att fråga om för sig, och unionen finns kvar för den som verkligen vill ha
bredden.

Kärnorna står **inte** som literaler i `skuld.py`. De läses ur
`harness/text.py`, alltså ur den modul som **äger** delningen — en grind mot
kopierade ordlistor får inte själv bära en kopia av den lista den dömer om.
Saknas delningen kastar grinden i stället för att svara "inga fynd" (S10).

**Mätt 2026-09-05, samma grind mot tre utcheckningar:**

| Utcheckning | Träffar |
|---|---|
| före M-95 (`d7beef8~1`) | **2** — `text.NEKANDE`, `oga.NEKANDE_OGONORD` |
| före M-98 | **1** — `oga.NEKANDE_OGONORD` |
| efter M-98 | **0** |

Spärren återfinner alltså båda de listor som bar M-94:s och M-98:s fynd, utan
att veta om dem. Taket är noll.

### 4.2 Kopierade ordlistor ska vara sedda

**Mätt 2026-09-05:** 163 moduldeklarerade ordlistor (≥ 3 ord, `__all__`
undantaget). Fördelningen av parvis överlapp:

| Minst så många gemensamma ord | Par |
|---|---|
| 4 | 19 |
| 5 | 7 |
| 6 | **6** |
| 7 | 4 |

Knäcken ligger mellan 4 och 5: av de 35 par där den ena listan ryms helt i den
andra ligger **23 på exakt 3 gemensamma ord**, alltså på listlängdens golv. Det
är sammanträffanden, inte kopior. `KOPIEGRANS = 6` står därför på 6, och en
lista med **samma namn** räknas som kopia oavsett storlek — ett delat namn är
ingen slump.

Registret: **13 par**, alla namngivna i provet.

| Gemensamma | Par |
|---|---|
| 12 | `guldgrind.DALIGA_ORD` ↔ `oga_kontrakt._FYNDORD` |
| 11 | `plan/forfining.ANDELSER` ↔ `plan/lasning._ANDELSER` |
| 7 | `harness/oga.BARA_NEGATION_OGA` ↔ `harness/text.BARA_NEGATION` |
| 7 | `harness/oga.GODKANNANDEORD` ↔ `harness/text.FRAMGANGSMARKORER` |
| 7 | `st/lexer.NYCKELORD` ↔ `st/modell.VARSORTER` |
| 6 | `st/skrivare.JAMFORELSER` ↔ `st/validator.JAMFORELSER` |
| 5 | `api_index._RANGORDNING` ↔ `llm/urval._RANGORDNING` |
| 4 | `guldgrind.INTE_NONE` ↔ `oga_kontrakt._INTE_NONE` |
| 3 | `plats.WINDOWSPLATTFORMAR` ↔ `install/upptackt.WINDOWSPLATTFORMAR` |
| 3 | `guldgrind.OBLIGATORISKA_SEKTIONER` ↔ `forlopp/yta.OBLIGATORISKA_SEKTIONER` |
| 2 | `verktyg/matning._YTOR_LAYOUT` ↔ `verktyg/robotik._YTOR_LAYOUT` |
| 1 | `api_index._RANGORDNING` ↔ `verktyg/katalog._RANGORDNING` |
| 1 | `llm/urval._RANGORDNING` ↔ `verktyg/katalog._RANGORDNING` |

**Spärren fångade något inom två timmar.** Talet var 11 när registret skrevs
och 13 en dryg timme senare: en annan agent lade `_RANGORDNING` i en tredje
modul (`svc/vc_assist_svc/llm/urval.py`) medan mätningen pågick, och namnet
stod redan i `api_index.py` och `verktyg/katalog.py`. Tre kopior av samma
rangordning, i tre moduler, ingen av dem medveten om de andra — och det är
precis formen på M-94 fynd 9 (`MARGINAL_SCAN` i tre kopior). Rätt åtgärd när
talet stiger är att **namnge paret**, aldrig att bara skriva upp talet.

**Att det inte är teoretiskt.** `guldgrind.DALIGA_ORD` och
`oga_kontrakt._FYNDORD` läser samma ögonrapport och delar tolv ord — men den
första bär dessutom `CEILING`, som den andra med flit har lagt i `_OSAKERORD`
(*"tvingar bort från PASS utan att tvinga FAIL"*). Kopian **har redan glidit
isär**, precis som `text.py`:s inledning varnade för. Att de i dag ändå dömer
lika är läst, inte kört: båda vägrar PASS för en rad med `CEILING`.

Registret är ett **register**, inte en anklagelse. En delad ordlista kan vara
rätt; det som inte får hända är att en ny uppstår osedd. Taket får bara gå
nedåt, och paren namnges — ett tak utan innehåll slutar mäta sin egen storhet
den dag ett par försvinner och ett annat tillkommer.

Båda spärrarna syns nu i `SKULDREGISTER.md`, alltså i det register M-94 skrevs
för att fråga vad det **inte** kunde se.

## 5. Vad sviterna sa

`pytest tests/enhet` efter allt ovan: **6 719 gröna, 190 skippade, 1 röd**.
Den röda är `test_troskelharkomst.py::test_skulden_ar_raknad_och_krymper`, och
den är inte den här mätningens — se LIMITS.

`pytest tests/motbevis` är **röd, 22 av 48**, som den ska vara. Motbevissviten
är repots lista över det som ännu inte håller; en grön motbevissvit vore
beviset på att den slutat fråga.

Efterlevnadsbänken: **58 av 58** mekaniska fällor, **28 av 28** kontrollfall, 0
falska avvisningar.

## 6. Ett prov som slutade vara trasigt

`tests/enhet/test_harness.py` skrev härkomsten `"M-99"` och litade på att det
numret inte fanns. 2026-09-05 kl. 08:06 skapade en annan agent
`M-99_differentialsvepet_mot_kompilatorn.md`, och två prov gick röda:

```
test_trasig_korpus_okand_matning_falls          assert False
test_las_korpus_kastar_med_hela_problemlistan   assert 1 >= 2
```

**Provets antagande var fel, inte koden.** `Harkomstuppslag` gjorde precis rätt
när den slog upp M-99 och hittade filen. Numret räknas nu fram ur
`docs/matningar/`. Det är samma felklass som mätningen i övrigt handlar om: ett
värde som avgör en dom hämtat ur en litteral i stället för ur den storhet det
påstår sig mäta.

## LIMITS

* **Allt är mätt på grindarnas egen dom, inte mot en körande VC.** Vad som
  händer i en levande scen när ett svar väl passerat är inte prövat här.
* **`SATSGRANSER` är vald, inte mätt.** Tolv tecken och bindeord, och varje
  gräns som läggs till gör satserna mindre — alltså fler anklagelser. Jag har
  prövat listan mot de nio meningarna i tabellen och mot bänkens sju
  ögonfällor, inte mot verklig modelltext. Vad som skulle avgöra det: ett svep
  över sparade turer där varje ögonmening delas och delningen dömes för hand.
* **Ordningen inom satsen prövas inte.** Ett nekande räknas som att det negerar
  godkännandeordet oavsett om det står före eller efter. *"Cellen ar godkand,
  det stammer inte"* är två satser och fälls; en konstruktion där negationen
  följer i samma sats utan komma skulle gå fri. Jag har inte hittat en sådan
  mening, men jag har inte heller sökt systematiskt.
* **`oga.GODKANNANDEORD` och `oga.BARA_NEGATION_OGA` är kvar som kopior.** De
  står i registret (7 respektive 6 gemensamma ord med `text.py`:s listor) och
  är **inte** sammanslagna. Att slå ihop dem ändrar två grindar samtidigt, och
  ögonordlistan bär ord (`fail`, `inconclusive`, `not gold`) som är ögats och
  inte textmodulens. Sammanslagningen behöver en egen mätning.
* **`guldgrind.DALIGA_ORD` mot `oga_kontrakt._FYNDORD` är inte lagad.** Att de
  dömer lika i dag är **läst**, inte kört: jag har inte matat en rapport med
  `CEILING` genom båda vägarna. Fyndet står i registret.
* **Spärren ser bara moduldeklarerade literaler.** En ordlista byggd inne i en
  funktion, hämtad ur JSON eller satt ihop med en `for`-sats är osynlig för
  den. Jag har inte mätt hur många sådana som finns.
* **Spärrens kärnor är `text.py`:s två.** En lista som blandar två *andra*
  storheter — säg enheter och toleranser — hittas inte. Felklassen är
  generell; mekaniseringen är det inte.
* **Kopiekriteriet missar en drivande kopia som är kortare än sex ord och har
  ett annat namn.** `KOPIEGRANS` är satt vid en mätt knäck, men knäcken är
  mätt på **det här** repot vid **ett** tillfälle, och 6 mot 5 skiljer ett enda
  par.
* **Bänken har fortfarande ingen fälla av "ett nekande någon annanstans"-slaget
  för ärlighetsgrinden eller redovisningen.** F-66 och F-67 täcker ögongrinden.
  De två andra formerna finns bara som enhetsprov, och ett enhetsprov mäter
  grinden — inte hela harnessen runt den.
* **Tröskellintern är röd av annat, och det är mätt vems.**
  `test_troskelharkomst.py` räknade 58 trösklar utan härkomst mot ett tak på 58
  när det här arbetet började, och **66** när det slutade. Diffen är nio
  tillkomna och en borttagen, och **alla nio ligger under
  `svc/vc_assist_svc/llm/`** (`matt.py` 3, `scenvy.py` 2, `budget.py` 2,
  `profil.py` 1, `urval.py` 1) — ett träd som ännu inte ens är spårat i git och
  som en annan agent skriver i samtidigt. De två konstanter den här mätningen
  införde (`_MINSTA_ORDLISTA`, `KOPIEGRANS`) bär båda `M-98` på sin rad och
  räknas inte in; jag har verifierat att `skuld.py` bidrar med noll. Skulden är
  alltså inte min, men den är verklig, den gör `pytest tests/enhet` röd, och
  den ligger kvar när det här skrivs. Att skriva upp taket hade varit att göra
  någon annans grind lösare.
* **Sju konsumenter är alla jag hittade, inte alla som finns.** Sökningen gick
  på `NEKANDE`, `namner_fel`, `nekar_pastaendet` och `talar_om_fel` i `svc/`,
  `ext/`, `bank/`, `install/` och `tests/`. En grind som kopierat orden utan
  att kopiera namnet hittas bara av ordlistespärren i avsnitt 4 — och den
  hittade en (`oga.py`), vilket är precis så många som fanns.
