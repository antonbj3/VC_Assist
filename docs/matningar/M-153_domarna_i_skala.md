# M-153 — Hela banken genom båda domarna: var de är oense, och hur oense de är med sig själva

**Datum:** 2026-09-05
**Status:** KLART (kö A, punkt A3)
**Körs av:** `tests/protocol/kor_A3_domarna_i_skala.py` (svep + sammanställning;
  sammanställningen kräver ingen rigg). Proben i §4 är
  `docs/matningar/radata/m153_flankprob.py`.
**Rigg:** tolv OpenPLC Runtime v4.2.1 i docker,
  `ghcr.io/autonomy-logic/openplc-runtime@sha256:40726c99…bc1435`, containrarna
  `vcassist-openplc-a3-1…12` (REST 18451–18462, OPC UA 172.17.0.4–15:4840).
  Proberna kördes mot `vcassist-openplc-v4` (18443). STruC++ 0.6.6, node
  v22.22.0, asyncua 1.1.8. PLC-uppgift `T#20ms`, OPC UA-plugin 10 ms.
  `vcassist-openplc-m108` (14841/18444) rördes inte — den hör till M-108/M-125.
  **Ingen modell körde i den här mätningen.** Båda domarna dömer texter som
  redan står i banken; ingen modellkvot användes.
**Facit:** bankens spårfacit — punktkrav, invarianter och flankräkning, skrivna
  av en människa före körningen (laglig källa 4 i `85_bankkontraktet.md` §2).
  Samma facit läses av båda domarna; det som jämförs är **domarna**, inte facit.
**Prövar:** `bank/domare.py` mot `bank/domare_openplc.py`
**Rådata:** `docs/matningar/radata/m153_svep.jsonl` (1110 körningar, en rad per
  körning), `docs/matningar/radata/m153_sammanstallning.json` (per enhet och
  varv), `docs/matningar/radata/m153_ut.txt` (körningens egen utskrift),
  `docs/matningar/radata/m153_flankprob_ut.txt` (proberna i §4 och
  provtagningstakten i §5),
  `docs/matningar/radata/m153_omprov_parallellt.jsonl` och
  `…_omprov_seriellt.jsonl` (de två kontrollarmarna i §5, 78 körningar var).
  Sammanställningen görs om med
  `python3 tests/protocol/kor_A3_domarna_i_skala.py --sammanstall
  docs/matningar/radata/m153_svep.jsonl --n 3 --tabell`.

## Frågan

`M-146` (punkt A2) byggde den andra domaren och dömde **14 texter** ur tre
uppgifter. Den fann en sak som styr hela den här mätningens form: *samma text
gav två olika svar ur samma domare.* OpenPLC-domaren är alltså inte
deterministisk vid n = 1, och n ≥ 3 är därmed ett krav och inte en förfining.

A3 är hela banken genom båda domarna, och tre tal som är lätta att blanda ihop
och som därför räknas var för sig:

* **(a) utfallsoenighet** — domarna säger olika sak om GRÖN/RÖD.
* **(b) kodoenighet** — samma utfall, olika bristkoder.
* **(c) självinstabilitet** — *en* domare ger olika svar på samma text mellan
  körningar.

## 1. Vad som kördes

**185 enheter** (bankens 33 uppgifter med spårfacit: 33 referenser + 152
motbevis) × **2 domare** × **3 varv** = **1110 körningar**. Ingen enhet är
utelämnad, och ingen är mätt med färre än tre varv: **0 omätta**.

| | |
|---|---|
| körningar | 1110 (555 per domare) |
| enheter | 185 (33 referenser, 152 motbevis) |
| enheter mätta vid n = 3 | 185 |
| enheter jämförbara (ingen Domsfel) | 184 |
| väggtid | 1 h 17 min på 12 parallella runtimes |
| OpenPLC-domaren, median per körning | **84,9 s** |
| samma arbete seriellt | ca **14,6 h** |
| tolkdomaren, median per körning | **0,050 s** |

Kostnadskvoten mellan domarna är alltså ungefär **1 700 : 1**. Det är inte en
bisak: den avgör om en domare kan köras per reparationsvarv eller bara i ett
svep.

Varje körning flushades till JSONL med `fsync` innan nästa startade, och svepet
kan återupptas. Det behövdes: en arbetare tappade OPC UA-kanalen i sin sista
körning (§7), och omstarten skrev en dubblett som sammanställningen räknar bort
och rapporterar i klartext i stället för att tyst göra n = 4 för en enhet.

## 2. De tre talen

| tal | antal | av |
|---|---|---|
| **(a) utfallsoenighet** — domarna oense om GRÖN/RÖD | **10** | 184 jämförbara enheter |
| **(b) kodoenighet** — samma utfall, olika bristkoder | **55** | 184 jämförbara enheter |
| **(c) självinstabilitet, OpenPLC-domaren** | **13** | 185 enheter |
| — varav instabiliteten byter UTFALL, inte bara koder | **4** | 185 enheter |
| **(c) självinstabilitet, tolkdomaren** | **0** | 185 enheter |

De 184 jämförbara enheterna delar sig utan rest:

| | enheter |
|---|---|
| helt eniga (samma utfall, samma bristkoder, båda stabila) | **107** |
| (a) oense om utfall | 10 |
| (b) eniga om utfall, oense om koder | 55 |
| (c) OpenPLC-domaren oense med sig själv (ingen jämförelse går att göra) | 12 |
| *(den trettonde instabila enheten är den odömda i §7 och ligger utanför de 184)* | |
| summa | 184 |

Alltså: **de två domarna ger samma svar på 107 av 184 enheter (58 %)**. På
motbevisen är kvoten 87 av 151.

Två saker till att läsa rakt ur tabellen:

* **Tolkdomaren är exakt reproducerbar.** 555 körningar, 185 enheter, noll
  vacklande koder. Den är deterministisk, och det är mätt och inte antaget.
* **OpenPLC-domaren vacklar på 13 av 185 enheter (7,0 %)**, och på 4 av dem
  ändras själva domen. `M-146`:s fynd är alltså inte ett engångsfall utan en
  egenskap, och den träffar var fjortonde enhet.

Per uppgift, aldrig som ett medelvärde (`--tabell` ur samma körning):

| uppgift | enheter | (a) utfall | (b) koder | (c) openplc oense m sig själv | (c) tolk | odömda |
|---|---|---|---|---|---|---|
| A-01 | 5 | 1 | 3 | 1 | 0 | 0 |
| A-02 | 5 | 0 | 0 | 0 | 0 | 0 |
| A-03 | 4 | 0 | 0 | 0 | 0 | 0 |
| A-04 | 4 | 0 | 0 | 0 | 0 | 0 |
| A-05 | 5 | 1 | 3 | 0 | 0 | 0 |
| A-06 | 5 | 0 | 0 | 0 | 0 | 0 |
| A-07 | 8 | 1 | 7 | 0 | 0 | 0 |
| A-08 | 7 | 0 | 0 | 0 | 0 | 0 |
| C-01 | 2 | 0 | 0 | 1 | 0 | 1 |
| C-04 | 6 | 1 | 4 | 0 | 0 | 0 |
| C-06 | 7 | 0 | 1 | 0 | 0 | 0 |
| H-01 | 6 | 1 | 5 | 0 | 0 | 0 |
| H-04 | 5 | 0 | 0 | 0 | 0 | 0 |
| H-05 | 6 | 0 | 0 | 0 | 0 | 0 |
| L-01 | 6 | 0 | 0 | 1 | 0 | 0 |
| L-05 | 6 | 0 | 0 | 0 | 0 | 0 |
| L-06 | 6 | 0 | 1 | 0 | 0 | 0 |
| L-07 | 7 | 0 | 0 | 2 | 0 | 0 |
| P-03 | 6 | 1 | 5 | 0 | 0 | 0 |
| P-05 | 2 | 0 | 1 | 1 | 0 | 0 |
| P-06 | 7 | 1 | 6 | 0 | 0 | 0 |
| P-07 | 6 | 0 | 1 | 2 | 0 | 0 |
| S-01 | 5 | 0 | 0 | 2 | 0 | 0 |
| S-05 | 6 | 1 | 5 | 0 | 0 | 0 |
| S-06 | 6 | 0 | 1 | 0 | 0 | 0 |
| S-07 | 6 | 0 | 0 | 0 | 0 | 0 |
| T-01 | 6 | 0 | 2 | 0 | 0 | 0 |
| T-02 | 6 | 1 | 4 | 0 | 0 | 0 |
| T-04 | 6 | 0 | 0 | 2 | 0 | 0 |
| T-05 | 6 | 0 | 1 | 1 | 0 | 0 |
| T-07 | 5 | 0 | 0 | 0 | 0 | 0 |
| T-08 | 6 | 1 | 5 | 0 | 0 | 0 |
| T-09 | 6 | 0 | 0 | 0 | 0 | 0 |

## 3. Oenigheten går åt ETT håll, och den träffar referenserna

**Alla tio utfallsoenigheter är referenslösningar, och i alla tio säger
tolkdomaren GRÖN och OpenPLC-domaren RÖD.** Inte en enda gång tvärtom.

| referens | vad OpenPLC-domaren fäller på |
|---|---|
| A-01 | `flank:b_programmet_startas_efter_spannaren` |
| A-05 | `flank:ingen_punkt_ovanfor_frasningsgransen` |
| A-07 | tre `flank:*` |
| C-04 | en `flank:*` + två `invariant:*` |
| H-01 | två `flank:*` + tolv punktkrav |
| P-03 | två `flank:*` |
| P-06 | `flank:ingen_luckoppning_fore_kvittens` |
| S-05 | två `flank:*` + 34 punktkrav |
| T-02 | `flank:inget_index_utanfor_temperaturfonstret` |
| T-08 | ett enda punktkrav: `en_detalj_genom_ugnen@1300ms:ST520_PRT_CNT` |

Nio av de tio fälls alltså på minst en `flank:*`. Den tionde, T-08, fälls på ett
enda punktkrav — och det kravet är en flankräkning i räknarform:

```
ST520_PRT_CNT skulle vara 0 men var 1 inom 4 scan efter 1300 ms.
fotocellen ut raknar ned; ugnen ar tom igen och det ar inget larm
```

Räknaren står på ett där ugnen ska vara tom: en flank för mycket eller en
nedräkning för lite. Vilken av dem är **inte** spårat.

Räknar man in de tre referenser vars OpenPLC-dom **vacklar** mellan varven
(P-05, S-01, T-04, alla GRÖN–RÖD–GRÖN) står det så här:

* tolkdomaren: **33 av 33** referenser gröna i alla tre varv.
* OpenPLC-domaren: **20 av 33**.

Motbevisen ser helt annorlunda ut. **151 av 152 är röda i båda domarna i alla
tre varv** (den 152:a är den odömda i §7). Inget motbevis är grönt hos någon av
domarna, och inget är rött hos den ena och grönt hos den andra. Bankens
motbevis håller alltså i båda motorerna; det är referenserna som skiljer dem åt.

Kodoenighetens riktning är lika ensidig. Räknat över de 55 enheterna:

| kodslag | bara hos tolkdomaren | bara hos OpenPLC-domaren |
|---|---|---|
| punktkrav | 36 | **237** |
| `flank:*` | 14 | **56** |
| `invariant:*` | 24 | 5 |
| `tolkfel:*` | 7 | 0 (strukturellt omöjligt, §6) |

OpenPLC-domaren fäller alltså **fler** brister än tolkdomaren i nästan varje
kodslag. Att det gäller punktkrav är särskilt värt en tanke, för
OpenPLC-domarens punktkravsregel är den **mildare** av de två (den godtar
värdet inom 4 scan, tolken kräver exakt scan). En mildare regel som ändå fäller
sju gånger fler punktkrav betyder att spåren har gått isär före punkten, inte
att punkten lästes strängare.

## 4. Varför: två mekanismer i domaren, och en tredje som inte går att hänföra

Att `flank:*` bär oenigheten var svaret på *var*. Proben
(`docs/matningar/radata/m153_flankprob.py`) svarar på *varför*: den kör en
signal genom båda domarnas egna slingor och skriver ut vid vilka millisekunder
var och en ser flanken, bredvid facits fönster. Tre saker föll ut. De två
första (§4a, §4b) ligger **i domarmekaniken** och är inga oenigheter mellan
motorerna alls; den tredje (§4c) går inte att hänföra på den här datan, och
varför den inte går att hänföra är i sig mätt.

### 4a. Toleransen töjer flankfönstret åt ett håll

`domare.py` räknar flanker i fönstret `[fran_ms, till_ms]`.
`domare_openplc.py` räknar i `[fran_ms, till_ms + TOLERANS_SCAN·SCAN_MS]`, med
motiveringen (M-146) att *kanalen bara kan försena, aldrig tidigarelägga*. Det
är riktigt om kravet är "**minst** N flanker". Bankens `antal` är en
**likhet**, och då gör en ensidig töjning bara en sak: den drar in flanker som
ligger utanför fönstret.

Mätt på A-07:s referens, sekvensen `kallstart_utan_sjalvstart`:

```
TOLK  ST470_CLP_CLOSE RISE vid [500.0]
OPLC  ST470_CLP_CLOSE RISE vid [540.0]
FACIT ingen_spanning_fore_kvittens: RISE antal=0 fonster [0, 480] ms;
      openplc-domaren laser [0, 560.0]
```

Motorerna är **överens**: spännaren kommenderas efter fönstret. Kanalen lade på
40 ms (två scan, precis M-20:s uppmätta svarstid). Toleransen lade på 80 ms.
Skillnaden — 40 ms — är hela oenigheten. Facit säger "noll flanker före
480 ms", båda motorerna håller det, och bara domaren säger nej.

Det är formen `en-parameter-som-bar-tva-storheter`: `TOLERANS_SCAN` bär både
*"en sen flank ska ändå räknas"* och *"en flank efter fönstret ska inte
räknas"*, och de två drar åt olika håll.

### 4b. De två domarna ger logiken olika STARTVILLKOR

`domare_openplc._kor_sekvens` gör så här före varje sekvens: nollställer alla
insignaler, **sover 150 ms** (`SETTLE_S`), läser tillbaka och kontrollerar
kanalen, och startar sedan klockan. PLC:n har alltså kört minst 150 ms — sju
scan — med alla ingångar tvingade till noll innan spåret börjar. Och sekvensens
`t=0`-stimuli skrivs i körslingans **första varv**, varefter provet tas
omedelbart; logiken har inte hunnit svara (M-20: två scan) förrän vid scan 2.

`domare.py` startar i stället en ny `Tolk`, sätter `t=0`-stimuli och kör ett
scan. Vid dess scan 0 har logiken **redan** sett stimulit.

Två spår som börjar i olika tillstånd. Allt logiken gör under
noll-ingångs-förspelet hör till OpenPLC-domarens startvillkor och finns inte
alls i tolkens. Det syns åt båda hållen:

**En flank för mycket.** P-03:s referens fälls på två `flank:… antal=1`-krav:

```
TOLK  ST120_RB_CLEAR RISE vid [18000.0]
RA    forsta 6 rasamplen: [(2.3,False),(13.3,False),(24.4,False),
                           (35.4,True),(46.5,True),(57.6,True)]
OPLC  ST120_RB_CLEAR RISE vid [20.0, 18040.0]
```

Utgången är verkligen låg de första två scanen och går hög efter ~35 ms — precis
svarstiden. Det är en riktig flank i en riktig PLC. Tolken kan inte se den:
dess "föregående värde" sätts efter första scanet, och övergången finns inte i
modellen. `antal=1` blir 2.

**En flank för lite.** C-04:s referens fälls på det motsatta —
`ST420_STA_SAFE skulle ha 1 RISE-flank(er) mellan 0 och 600 ms …, hade 0`.
Signalen var redan hög vid scan 0, för logiken hann bekräfta säkert läge under
förspelet. Flanken hände; den hände bara före klockan.

**Och samma startvillkor fäller invarianter.** C-04:s två övriga brister lyder
ordagrant *"vid t=0 ms gällde ST420\_STA\_SAFE=1 men inte ST420\_GRP\_CLOSE=1
i 5 scan i rad"* och likadant för `ST420_STA_STEP=4`. Villkoret är alltså
uppfyllt från allra första scanet — ur förspelet — medan kravet ännu inte hunnit
bli sant. Tolken, vars invariantregel är den **strängare** (den fäller på
första scanet, OpenPLC-domaren först efter fem i rad), säger GRÖN, för i dess
spår gäller villkoret aldrig så tidigt.

Det är värt att stanna vid: **den strängare regeln fäller inte, och den mildare
gör det.** Skillnaden ligger inte i regeln utan i vad som står i spårets första
scan, och det är därför den inte går att kompensera bort med en tolerans.

Ingen av de två läsningarna är felaktig. De ställer **olika frågor** om
sekvensens början, och facit skrevs mot den ena.

### 4c. Den intermittenta enskansglitchen — och att provtagningen inte håller sin egen takt

T-04:s referens är GRÖN–RÖD–GRÖN. Proben, körd **fjorton gånger på samma
text**, fångade skillnaden **två** gånger:

```
varv 1: OPLC RISE [20.0, 22440.0]           FALL [19740.0]        -> 1 FALL, GRON
varv 2: OPLC RISE [20.0, 1040.0, 22440.0]   FALL [1020.0, 19740.0] -> 2 FALL, ROD
```

En puls på **ett scan** vid ~1 020 ms som tolken inte har och som inte alltid
finns. Och provtagningen som ska fånga den håller inte sin deklarerade takt:

```
POLL  n=2001 prov, median 11,77 ms, p95 12,07 ms, max 15,63 ms
      (POLL_S = 10 ms, 1,70 prov per 20 ms scan)
```

`domare_openplc.POLL_S` är satt till 10 ms med motiveringen *"~2 prover per
scan vid 20 ms"*. Uppmätt under den här körningen: **1,70**. En puls som är ett
scan bred ligger då under två prov per period, alltså under den gräns där den
går att återge säkert — och en flank som finns i en körning och inte i nästa är
precis vad undersampling ser ut som. Om glitchen är motorns eller domarens går
**inte** att avgöra ur den här datan; att provtagningen inte räcker för att
avgöra det är däremot mätt.

### 4d. Toleransen mot sin egen mätning, i skala

`TOLERANS_SCAN` = 4 scan = 80 ms är härledd som 2 (M-20, PLC:ns svarstid) + 2
(M-108, kanalfas). OpenPLC-domaren mäter själv hur många scan efter `t_ms` det
väntade värdet först syntes. Över alla 555 OpenPLC-körningar:

| offset | punktkrav |
|---|---|
| 0 scan | 34 275 |
| 1 scan | 9 |
| 2 scan | 7 |
| 3 scan | 0 |
| 4 scan | 0 |
| **summa** | **34 291** |

`M-146` mätte 654 punktkrav, alla på offset 0, och kunde därför inte säga om
toleransen behövdes alls. Nu vet vi: den behövdes **16 gånger av 34 291**
(0,05 %) och **aldrig mer än 2 scan**. De två scan som behövs är M-20:s
svarstid; M-108:s kanalfas syns inte alls i punktkraven.

Det talet hör ihop med §4a. Halva toleransen — de två scan kanalfas — är inte
observerad på punktkravssidan, och den är ändå med och töjer **varje**
flankfönster med 80 ms. Ett mått som är ren marginal där det mäts och en
felkälla där det inte mäts är samma parameter använd till två storheter.

## 5. Är instabiliteten maskinens last eller domarens?

Svepet kördes med tolv arbetare på en maskin som delas med tre andra sessioner
och operatörens skrivbord. Den rimliga invändningen är att instabiliteten är min
egen parallellitet. Den prövades med **två omprov av samma 13 enheter**, båda
med n = 3, och de jämförs med varandra och inte med svepet (urvalet är inte
oberoende — se LIMITS):

| omprov | last | instabila igen |
|---|---|---|
| 12 arbetare | samma som svepet | **4 av 13** |
| 1 arbetare | ingen annan A3-last | **4 av 13** |

Samma tal — och **inte en enda enhet vacklade i båda omproven**. Det parallella
tog L-01:s och S-01:s motbevis, L-07/`klippet…` och S-01:s referens; det
seriella tog L-07/`pallen…`, P-07/`aterstallt…`, T-05:s motbevis och T-04:s
referens. Fyra av tretton i båda armarna, med tom skärning: det ser ut som en
slumpprocess med ungefär konstant intensitet, inte som något lasten driver.

Provtagningstakten pekar åt samma håll. Samma text, samma signal:

| last | median mellan prov | prov per 20 ms scan |
|---|---|---|
| 12 arbetare | 11,77 ms | 1,70 |
| ingen A3-last | 11,75 ms | 1,70 |

De 1,75 ms över `POLL_S` är alltså inte maskinens belastning utan
OPC UA-batchläsningen själv. **Instabiliteten är domarens och motorns egen, inte
riggens.** Att `T-04/referens` bytte dom (GRÖN–RÖD–GRÖN) även i det seriella
omprovet är den skarpaste enskilda observationen: en ensam runtime på en
obelastad maskin ger fortfarande två olika domar om samma text.

## 6. Det strukturella undantaget: `tolkfel:*`

OpenPLC-domaren kan **aldrig** lämna en `tolkfel:*`-kod, för den kör inte vår
tolk. Ett motbevis vars `faller_pa` namnger en sådan kod kan därför inte fällas
"på rätt brist" av den nya domaren, hur rätt den än har.

Räknat om ur banken i den här körningen, inte övertaget från M-146:
**1 av 152 motbevis** — `P-07/ridans_signal_tvingas_hog_i_koden`, som pekar ut
`tolkfel:kallstart_utan_sjalvstart`. Talet stämmer med M-146.

Motbevis som fälldes på sin **namngivna** brist i alla tre varv:

* tolkdomaren: **152 av 152**.
* OpenPLC-domaren: **145 av 152**. Av de sju är **en** det strukturella
  undantaget ovan, **en** är den odömda i §7, och fem är H-01 (fyra) och S-05
  (en) — samma två uppgifter vars referenser också är röda hos OpenPLC-domaren.
  Där har spåret gått isär före den namngivna bristen, så motbeviset fälls på
  något annat först. Det är rätt utfall (rött) av fel skäl, och det räknas här
  som en miss och inte som en träff.

Kodoenigheter som består **enbart** av `tolkfel:*`: **0 av 55**. Undantaget är
alltså litet i praktiken — men det är räknat, inte bortglömt.

## 7. Ett körningsfel är fortfarande aldrig en dom

En av 555 OpenPLC-körningar (**0,18 %**) gav Domsfel:
`C-01/motbevis:oppnar_inlopp_aven_nar_bufferten_ar_full`, varv 3, med
kompilatorns och kanalens egna ord:

```
sekvensen enhet_genom_cellen: batchläsningen av 11 signaler föll:
Connection is closed; sidan kördes inte
```

Enheten räknas därför som **odömd** och ingår varken i (a) eller (b). Den blev
inte grön, den blev inte röd, och den blev framför allt inte tyst. Att
gränsen höll under 555 riktiga körningar är A2:s trasiga fixtur prövad i skala.

*(En fjärde körning av samma enhet gjordes av misstag när svepet avslutades och
gav UNDERKÄND. Den är räknad som dubblett och ingår inte i talen — tre varv är
tre varv.)*

## 8. Raden i bankkontraktet

`M-146` avstod medvetet från raden: två körningar visar varians, inte vem som
har rätt. Med n = 3 över hela banken finns underlaget, och **raden gick att
skriva** — men inte som *"OpenPLC-domaren vinner"*. Den står nu som §6 i
`docs/spec/85_bankkontraktet.md`, och skälet att den inte kunde bli enklare är
det här:

* Kontraktets §2 diskvalificerar tolkdomaren som **auktoritet**: den dömer
  genom det som prövas. Det talar för OpenPLC-domaren, och det talet står
  fast.
* Men den här mätningen hittade **inte en enda oenighet som gick tillbaka på
  att motorerna gör olika saker.** Nio av tio utfallsoenigheter fälls på
  `flank:*`, den tionde på en flankräknare, och de tre mekanismer som är
  spårade (§4a, §4b, §4c) ligger alla i domarmekaniken. Där reglerna skiljer
  sig är den ena domaren inte "rätt" — de svarar på olika frågor, och att välja
  vinnare hade gjort en defekt till en dom.
* Och en auktoritet som ger två olika svar på samma text är ingen auktoritet:
  13 av 185 enheter vacklade, 4 av dem bytte utfall, och omprovet visar att det
  inte är riggens fel (§5).

Raden blev därför en regel i tre led plus ett villkor. Det andra ledet — *"är
reglerna desamma gäller OpenPLC-domaren"* — vilar uttryckligen på §2 och på
`M-125`, **inte** på M-153: den här mätningen fann inget sådant fall och kan
alltså inte belägga ledet, bara låta bli att motsäga det. Det står så i
kontraktet också, för ett led utan belägg som ser ut som ett med är värre än
inget led.

Det som INTE gick att skriva, och som därför inte står någonstans: vilken av de
två som har rätt om A-01, A-05, C-04, H-01, P-03, P-06, S-05, T-02 och T-08.
Nästa punkt är att laga de två defekterna i §4a och §4b och köra om svepet; det
talet blir då *"hur mycket skiljer sig domarna när de ställer samma fråga"*, och
det är först det talet som är bänkens felstapel.

## LIMITS

* **Mätningen jämför två DOMARE, inte två motorer.** `bank/domare.py` och
  `bank/domare_openplc.py` läser samma facit men ställer inte samma fråga om
  det. Tre regelskillnader är utpekade och mätta (§4a flankfönstret, §4b
  uppstartsscanet, §6 `tolkfel:*`). Om det finns fler regelskillnader som den
  här banken inte råkar reta vet jag inte. Att kalla talen "hur mycket vår tolk
  och OpenPLC skiljer sig" vore fel: de flesta oenigheterna går tillbaka på
  domarmekaniken, inte på motorerna.
* **Bara tre av de tio utfallsoenigheterna är spårade till en mekanism.**
  A-07 (§4a), P-03 och C-04 (§4b) är mätta hela vägen. A-01, A-05, H-01, P-06,
  S-05, T-02 och T-08 fälls på samma kodslag och har samma form, men de är
  **inte** enskilt utredda, och att kalla dem "samma mekanism" vore en gissning
  som ser ut som en mätning.
* **Ingen tredje domare avgör vem som har rätt.** Där de två skiljer sig säger
  mätningen VEM som säger VAD, inte vem som har rätt. §4a är det enda ställe
  där rättvisan är avgjord — och där har facit rätt och OpenPLC-domarens
  fönster fel. T-08:s ensamma punktkrav (`ST520_PRT_CNT`), C-04:s två
  invarianter och S-05:s 34 punktkrav är rapporterade och **inte utredda**.
* **13 instabila enheter är ett GOLV, inte ett tal.** Instabiliteten mättes vid
  n = 3. En enhet som vacklar i en körning av tjugo ser stabil ut vid n = 3.
  Hur talet växer med n är omätt.
* **Omprovens urval är inte oberoende (§5).** De 13 enheterna valdes för att de
  redan visat sig instabila. Regression mot medelvärdet gör att färre visar sig
  instabila vid omprov även utan någon skillnad i last. Därför jämförs de två
  armarna **med varandra**, aldrig med svepet — och även den jämförelsen har
  bara 13 enheter under sig.
* **Enskansglitchen i §4c är inte hänförd.** Om pulsen ligger i OpenPLC eller i
  vår provtagning går inte att avgöra ur den här datan. Att provtagningen är
  för gles för att avgöra det (1,70 prov per 20 ms scan, mot de 2 som
  `POLL_S = 10 ms` antar) är däremot mätt.
* **Punktkravens 0-offset gäller punktkrav, inte flanker.** 34 275 av 34 291
  punktkrav låg på offset 0 och inget över 2 scan. Flankernas och
  invarianternas fördelning **under** toleransen är fortfarande omätt, och §4a
  visar att det är just där skillnaden bor.
* **En maskin, en scanperiod, en runtimeversion.** 20 ms, OpenPLC v4.2.1, en
  maskin som under hela svepet delades med tre andra sessioner, Visual
  Components och operatörens skrivbord. Vad talen blir vid 10 eller 100 ms scan
  är punkt A4 och är oprövat här.
* **Kostnadstalen gäller under tolv parallella runtimes.** 84,9 s median per
  OpenPLC-körning är mätt under den lasten. En ensam runtime är snabbare (mätt
  samma dag: P-05:s referens 24,6 s ensam mot 29,1 s under last), så
  "14,6 h seriellt" är en övre uppskattning och inte en mätning.
* **Mätningen säger inget om att bankens facit är rätt.** När en referens är
  röd hos OpenPLC-domaren kan felet ligga hos referensen, hos domaren eller hos
  facit. §4a visar ett fall där det är domaren. De övriga är inte avgjorda, och
  ingen av dem får läsas som att referensen är trasig.
* **Ingen modell kördes.** Talen säger ingenting om någon modells förmåga; de
  säger vad två domare gör med texter som redan står i banken.
* **Ingenting är lagat.** `bank/` ligger utanför kö A:s yta i briefen, så de
  två utpekade defekterna i §4a och §4b är **rapporterade och inte rättade**.
  Talen i den här mätningen gäller domarna som A2 lämnade dem.
