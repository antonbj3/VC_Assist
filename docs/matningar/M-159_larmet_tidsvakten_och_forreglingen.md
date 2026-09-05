# M-159 — grind 3b: tidsvakt, larmutgang och forregling mot bankens 38 referenser

**Datum:** 2026-09-05
**Rigg:** `svc/vc_assist_svc/plc/industrigrind.py` (ny), inkopplad i
`svc/vc_assist_svc/plc/stationsgrind.py`, reglerna in i
`svc/vc_assist_svc/plc/forhandsregler.py`
**Låst av:** `tests/enhet/test_plc_industrigrind.py` (63 prov)
**Körs om av:** samma provfil; `-k referensen` ger banktabellen
**Punkt:** A7 i `docs/uppdrag/KO_A_motorn_pa_riktigt.md`
**Bygger på:** `M-89` (hålet), `M-96` (priset i falska röda), `M-121`
(uteslutningen och formen), `M-111` (en grind som blir billig)

## Frågan

`M-89` mätte projektets skarpaste hål och skrev det i en mening:

> *En inspelad normalproduktion ger ett program som återger inspelningen och
> ändå saknar tidsövervakningen, larmen och förreglingarna.*

Ur produktionsspåret blev det **0 av 2** mot människans facit. Bristerna var
inte logikfel — koden kompilerade, taggarna fanns i kartan, ingen utgång skrevs
två gånger, och den återgav spåret. Det som fattades var det som gör kod
*industriell*: en station som fastnar står tyst för evigt, ett fel har ingen
larmutgång, två aktuatorer som kan kollidera saknar förregling.

Grind 1–3 fångar inget av det. Ögat fångar det bara om stimulit råkar provocera
just det tillståndet, och `M-89` mätte att ett produktionsspår aldrig gör det:
`EMG_OK` gick **aldrig** till 0 i något av fyra spår.

A7 var att bygga grinden och att mata in reglerna i systemprompten, så att
modellen får veta kravet **innan** den skriver.

## Svaret i tre tal

| | |
|---|---:|
| Bankens referenser genom grind 3b | **2 fällda av 38** |
| Båda fällningarna | **verkliga brister**, samma klass |
| Falska rödgrindar kvar efter avgörandet per fall | **0** |

De två är `A-07` och `C-06`, och de bär exakt samma brist. Domen per fall står i
§3, och den är låst i `KANDA_BRISTER` i provfilen så att en referens som lagas
gör provet rött tills raden tas bort.

## 1. Vad grinden gör

Tre kontroller, egen kodtabell (`KONTROLLER_INDUSTRI`), samma form som grind 2
och grind 3.

| kod | fäller | felklass |
|---|---|---|
| `SAKNAD_TIDSVAKT` | väntan på en kvittensingång som uppgiften kräver tidsövervakad, utan någon tidsgräns i koden | — |
| `TYST_FELTILLSTAND` | latchat feltillstånd som aldrig når en utgång, i en uppgift som har en larmutgång | — |
| `SAKNAD_FORREGLING` | förregling uppgiften deklarerar men koden inte skriver som villkor på donet | `F8` |

**Felklassvalet är inte slarv.** `docs/spec/82_felklasser.md` sorteringsregel 5
säger att `F6` och `F7` **aldrig** får fällas av en statisk grind, därför att
statisk analys inte kan avgöra timersemantik. Den regeln bryts inte: grinden
dömer inte *om* en tid är rätt, den dömer om det finns någon tidsgräns alls, och
frånvaro är avgörbar utan semantik. `SAKNAD_FORREGLING` får `F8` — samma läsning
som `bank/reparationsbank.SPARKLASS` redan gör för spårfacits invarianter. De två
andra har ingen klass i tabellen och får `felklass=None` i stället för att
stoppas in i `F14`, precis som `st.fel.KONTROLLER` redan gjort för `OATKOMLIG`
och `SAKERHET`. Det är en öppen fråga till specen, inte ett hål i grinden — alla
tre fäller ändå.

**Kraven läses ur uppgiften, inte ur en handskriven lista.** Samma skäl som
`forhandsregler.py`: en handskriven ordlista glider isär från koden. Källorna är
uppgiftens egna fält, alla fyra människoskrivna och därmed lagliga enligt
`85_bankkontraktet.md` §2:

| fält | vad grinden tar ur det |
|---|---|
| `failure_modes` | vilka väntningar uppgiften **själv** kräver tidsövervakade |
| `control.signals` | vilka utgångar som är larmutgångar |
| `control.interlocks` | uppgiftens förreglingar i klartext |
| `facit_spar.invarianter` | samma förreglingar maskinläsbara (+ kontrapositionen) |

## 2. Trasig fixtur före mekanismen, och ett grönt kontrollfall bredvid

Provfilen skrevs före modulen och var röd (`ImportError`). Varje regel har en
trasig fixtur **och** ett grönt kontrollfall — utan det andra ser en grind som
avvisar allt lika bra ut som en som fångar rätt sak.

| regel | trasig fixtur (röd) | kontrollfall (grön) |
|---|---|---|
| tidsvakt | vänteläget på `ST900_IDX_DONE` utan tidsur | samma kod med `tmrIdx(IN := ST900_IDX_START AND NOT ST900_IDX_DONE, PT := T#2s)` och `IF tmrIdx.Q THEN xLarm := TRUE` |
| tidsvakt | tidsur på **fel** signal (`PRT_PRS`/`CLP_CLOSED`) | — |
| tidsvakt | `PT := T#0s` | — |
| tidsvakt | tidsur vars `Q` ingen läser | — |
| larmutgång | `SYS_ALARM := FALSE;` medan `xLarm` latchas | `SYS_ALARM := xLarm;` |
| larmutgång | `SYS_ALARM := NOT xLarm;` — en spärr är ingen larmväg | d:o |
| förregling | `ST900_IDX_START := xIndex;` | `ST900_IDX_START := xIndex AND ST900_CLP_CLOSED;` |
| förregling | — | förreglingen genom en **ren mellanvariabel** (`xSpant := ST900_CLP_CLOSED`) släpps igenom, samma doktrin som M-121 |

**Och mot riktig kod.** En grön referens är bara en mätning om mutationen som
tar bort skyddet blir röd igen (M-121:s form). Fem mutationer, alla röda:

| referens | mutation | kod |
|---|---|---|
| A-04 | `ST270_PRS_DOWN` utan `AND ST270_SAF_OK` | `SAKNAD_FORREGLING` |
| A-05 | `ST280_WLD_START` utan `AND ST280_GUN_CLOSED` | `SAKNAD_FORREGLING` |
| A-05 | `ST280_GUN_CLOSE` utan `AND ST280_PRT_PRS` | `SAKNAD_FORREGLING` |
| T-07 | tidsuret flyttat från `ST050_IDX_START` till `ST050_CNV_RUN` | `SAKNAD_TIDSVAKT` |
| T-07 | `SYS_ALARM := xLarm` → `SYS_ALARM := FALSE` | `TYST_FELTILLSTAND` |

## 3. Domen per fall: de två som fälldes

| fall | vad grinden säger | dom | vad som krävs |
|---|---|---|---|
| **A-07** | `ST470_ARC_ON` kan vara hög när `ST470_CLP_CLOSED` är låg | **verklig brist** | `ST470_ARC_ON := xBage AND ST470_GAS_ON` saknar `AND ST470_CLP_CLOSED`. Uppgiftens **egen** interlockrad kräver det ordagrant: *"ST470_ARC_ON far aldrig sta hog nar ST470_CLP_CLOSED ar lag"*. Sekvensen kontrollerar spännarnas lägesgivare i steg 2; släpper spännaren mitt i svetsen brinner bågen vidare. |
| **C-06** | `ST560_RB_START` kan vara hög när `ST560_DOR_OPENED` och `ST570_DOR_OPENED` är låga | **verklig brist** | `ST560_RB_START := xDrift AND (xStart1 OR xStart2)` saknar `AND (ST560_DOR_OPENED OR ST570_DOR_OPENED)`. Luckans lägesgivare prövas i steg 1 och släpps sedan; faller den medan roboten är inne i maskinen står startsignalen kvar. Uppgiftens facit har invarianten `roboten_gar_aldrig_mot_en_stangd_lucka`, och dess `failure_modes` namnger felet: *"betjaningscykeln startas pa luckans kommando i stallet for pa dess lagesgivare"*. |

Båda är samma klass, och det är M-121:s klass en gång till: **förreglingen
hålls bara av att sekvensen kontrollerade villkoret i ett tidigare steg.**
Skillnaden mot M-121 är vilken sida som är osäker — där var det stegmaskinens
tillstånd, här är det att en **ingång kan ändra sig mitt i steget**. Det är
`M-89`:s eget exempel i klartext: *klämman släpper mitt i indexet.*

**Referenserna är inte rättade här.** `bank/uppgifter` är kö B:s yta, och en
ändrad referens ändrar sitt eget spår. Bristen är rapporterad och låst som
`KANDA_BRISTER`; blir en av dem grön går provet rött tills raden tas bort.

## 4. Fem gånger var grinden själv fel, och hur det syntes

Det här avsnittet är det viktigaste, därför att `M-96` mätte priset: **nio av
sexton grinddomar i fas 9:s första modelldrivna körning var vår egen bugg**, och
tre av fyra uppgifter slog i taket på grund av det. Varje rad nedan är en
fällning som **såg riktig ut** och som bankkörningen avslöjade.

| # | vad grinden sa | fällde | verklig orsak | fällda referenser före → efter |
|---|---|---|---|---:|
| 1 | ingen förregling | allt | villkorliga tilldelningar följdes inte — `xBage` blev en fri atom, så `EMG_OK` kunde vara låg med bågen tänd | 29 → 23 |
| 2 | ingen tidsvakt | A-08, L-06 | uret stod på **kommandot** (`IN := ST480_RB_START`), inte på kvittensen. Det är den vanligaste industriella formen | — |
| 3 | tyst feltillstånd | A-06, A-07, A-08 m.fl. | varje **sekvenskommando** såg ut som ett feltillstånd, därför att ett väntesteg ofta står på ett tidsur | — |
| 4 | tyst feltillstånd | 9 referenser | `xLarm` når `SYS_ALARM` — men läsningen skedde på det **utvecklade värdet**, där namnet `xLarm` inte längre finns | 14 → 12 |
| 5 | omvänd förregling | S-07, T-04 | klartextparsern läste *"far aldrig ga hog **innan** B ar hog"* som *"B hög är förbjudet"* | 12 → … |

Efter rättelserna: **2 av 38**, och de två är verkliga.

**Instrumentet mot ett känt svar.** Klartextparsern över `control.interlocks` är
prövad mot samma uppgifters `facit_spar.invarianter` — samma förreglingar i
maskinläsbar form. Det är det enda som skiljer en läst rad från en gissad:

| | |
|---|---:|
| interlockrader i banken | 150 |
| rader parsern läser | 50 |
| av dem: **stämmer** med en formell invariant (identisk eller kontraposition) | **46** |
| av dem: **omvänd** mot en formell invariant | **0** |
| av dem: ingen formell motsvarighet att jämföra mot | 4 |

De 100 olästa raderna kastas inte — de rapporteras rad för rad i
`Grind3bRapport.oklara`. En grind som slänger det den inte förstod ser större ut
än den är.

## 5. Varför grinden INTE kräver en tidsvakt på allt

Det här var uppdragets svåraste fråga, och svaret är mätt.

Grinden räknar **varje** väntesteg: ett stegvillkor som håller cellen kvar tills
en ingång svarar. Över bankens 38 referenser:

| | |
|---|---:|
| väntelägen totalt | **165** |
| av dem utan någon tidsgräns | **115** |
| referenser med minst ett obundet vänteläge | **29 av 38** |

**En grind som krävde en tidsvakt på varje vänteläge hade alltså fällt 29 av 38
referenser på 115 ställen.** Det är inte en grind, det är en falsk rödgrind som
bränner ett reparationsvarv per uppgift — `M-96`:s mätta scenario, i skala.

Grinden fäller därför bara den väntan **uppgiften själv** pekar ut. Källan är
`failure_modes`-rader som säger att en väntan saknar tidsgräns:

| uppgift | raden | ingången |
|---|---|---|
| A-07 | *"cellen vantar pa ST470_ARC_OK utan tidsgrans, sa ett tandfel lamnar gas och trad pa"* | `ST470_ARC_OK` |
| A-08 | *"ST480_RB_DONE vantas in utan tidsgrans, sa en stannad robot lamnas med ventilen oppen"* | `ST480_RB_DONE` |
| H-04 | *"ingen kvittensvakt: uteblir ST310_HSK_ACK star cellen tyst"* | `ST310_HSK_ACK` |
| L-06 | *"ST540_RB_DONE vantas in utan tidsgrans"* | `ST540_RB_DONE` |
| T-07 | *"styrningen vantar pa ST050_IDX_DONE utan tidsgrans, sa en fastnad matare star kvar tyst"* | `ST050_IDX_DONE` |

Alla fem uppfylls av sina referenser. **Fem `failure_modes`-rader till** säger
samma sak men namnger ingen signal (*"lyftbordets andlage vantas in utan
tidsgrans"*, A-06, H-05, L-05, L-07, T-09); de blir `oklara` och rapporteras i
klartext i stället för att gissas.

Skillnaden mellan *det grinden fäller* och *det grinden ser* står alltså i
utdatan (`matt["vantelagen"]` / `matt["vantelagen_obundna"]`), inte i en
kommentar. Det är `M-111`:s doktrin: en grind som blir billig slutar mäta sin
egen storhet.

**Vad det kostar i missade fel:** 115 obundna väntelägen som grinden ser men
inte dömer. Talet är kö B:s beslutsunderlag — varje sådan väntan som verkligen
ska övervakas hör hemma i uppgiftens `failure_modes`, och då fäller grinden den.

## 6. Vad som fick byggas: värdeanalysen M-121 lämnade obyggd

`M-121`:s LIMITS: *"Villkorliga tilldelningar följs inte. `IF g THEN xLarm :=
TRUE; END_IF;` gör inte `xLarm` till `xLarm OR g` i analysen; namnet blir en fri
atom. … Inte byggt: kostnaden i falska gröna är då inte längre uppenbart noll."*

Utan den går ingen förreglingsdom att ställa. Bankens referenser skriver
`IF NOT xDriftsklar THEN don := FALSE;` och sedan `don := xKommando AND …`, så
sambandet mellan `EMG_OK` och donet går genom en **villkorad** tilldelning. Rad 1
i tabellen ovan är exakt det: **29 av 33 referenser** fälldes utan den.

Analysen vecklar därför ut varje BOOL till dess värde när scannen är klar:

    v_0 = v_före_scannen                              (fri atom)
    v_i = (villkor_i AND uttryck_i) OR (NOT villkor_i AND v_{i-1})

Atomerna är oberoende — samma överskattning som `uteslutning.py`, och en
överskattning ger **fler** fällningar, aldrig färre. Kostnaden i falska gröna är
alltså fortfarande uppenbart noll åt det hållet; det som tillkommer är
precision, inte tillåtelse.

### Tak, med uppmätt marginal

| tak | värde | uppmätt maximum över bankens 38 referenser |
|---|---:|---:|
| `MAX_ATOMER` (SAT) | 96 | **29** |
| `MAX_VARDEDJUP` | 12 | — |
| `MAX_NODER` | 20 000 | — |

Hela banken genom grind 3b tar **0,4 s**.

### Vad grinden avsiktligt inte dömer, och varför

Tre gränser, alla med sitt skäl, alla rapporterade i `oklara` per fall:

1. **Villkoret är en utgång, inte en ingång.** *"ST560_DOR_OPEN och
   ST570_DOR_OPEN får aldrig stå höga samtidigt"* är en **sekvensegenskap**: båda
   styrs av samma program, och att de aldrig sammanfaller följer av
   stegmaskinen. Det kan en statisk grind inte avgöra — samma skäl som
   `82_felklasser.md` sorteringsregel 5 ger. En **ingång** är en annan sak: den
   kan ändra sig mitt i ett steg, och då räcker inte sekvensens garanti.
2. **Utgången skrivs inne i stegmaskinen.** Frågan är då inte *"står förreglingen
   i uttrycket"* utan *"kan stegmaskinen nå det läget"*. Grinden dömer bara
   utgångar med **ett enda, ovillkorat skrivställe** — den form M-121 redan
   kräver av både modell och referens.
3. **Utgången drivs av ett skrivet heltalsvärde.** `S-05`:s
   `ST200_CNV_RUN := tillstand = 6` med en PackML-tillståndsmaskin i `INT`.
   Värdeanalysen viker boolska tilldelningar, inte heltalstilldelningar, så
   svaret vore *"vet inte"* — och vet-inte får inte bli en dom.

Talen: **254 deklarerade förreglingar**, varav **56** (utgång, villkor)-par
faktiskt döms och **265** par lämnas åt körningsdomaren med sitt skäl utskrivet.

## 7. Reglerna in i systemprompten

Tre nya rader i `forhandsregler.REGLER`, lästa ur `KONTROLLER_INDUSTRI` på samma
väg som grind 2:s och grind 3:s. Ingen andra väg in i prompten byggdes.

Mekaniken som håller ihop dem är redan provad och gäller nu de tre också:

* `saknade_regler()` — en kod utan regel är en **fälla**: grinden fäller på något
  modellen aldrig fick veta, och första försöket kan inte bli rätt av annat än
  tur. Provet är rött om någon lägger till en kontroll utan regel.
* `foraldralosa_regler()` — en instruktion utan grind bakom sig är en bön som ser
  ut som en regel.

Reglerna säger formen, inte bara förbudet: tidsuret med `IN` på kommandot och
kvittensen, `SYS_ALARM := xLarm;`, och `ST050_IDX_START := xIndex AND
ST050_CLP_CLOSED;`.

## 7b. Inkopplingen i grindkedjan

`stationsgrind.granska_station(..., krav=...)` kör grind 3b direkt efter grind
2/3 — billigast först, samma skäl som resten av körordningen. Nyckeln
`industriell_form` ligger **utanför** `KORORDNING`, och `Stationsdom.ok` räknar
in den bara när den körts. Att den saknas är inget underkännande: den kräver en
uppgift att läsa kraven ur, och den som inte lämnar en har inte hoppat över en
grind utan aldrig haft den.

En rättelse följde med: `forsta_fallande` letade i `KORORDNING` och returnerade
den första **saknade** grinden före den som faktiskt föll. Fäller grind 3b och
grind 4 därför aldrig körs blev svaret *"anropsvalidering"* — den första grinden
som råkade stå tom. Det är samma fel `till_cell` redan hade rättat en gång, och
det är rättat på samma sätt: skälet ska namnge orsaken.

## 8. Tabellen per uppgift

`tidsvaktkrav` = väntningar uppgiften själv kräver övervakade. `provade par` =
(utgång, villkor)-par grinden faktiskt dömde. `obundna` = väntelägen utan
tidsgräns (mätning, inte dom).

| uppgift | tidsvaktkrav | larmutg | förreglingar | provade par | feltillstånd | väntelägen | obundna | dom |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A-01 | 0 | 0 | 4 | 3 | 0 | 7 | 4 | - |
| A-02 | 0 | 1 | 8 | 3 | 0 | 0 | 0 | - |
| A-03 | 0 | 0 | 3 | 2 | 0 | 4 | 4 | - |
| A-04 | 0 | 0 | 5 | 3 | 0 | 5 | 5 | - |
| A-05 | 0 | 0 | 6 | 7 | 0 | 7 | 5 | - |
| A-06 | 0 | 1 | 5 | 4 | 0 | 7 | 4 | - |
| A-07 | 1 | 1 | 13 | 7 | 1 | 6 | 4 | **SAKNAD_FORREGLING** |
| A-08 | 1 | 1 | 11 | 1 | 2 | 5 | 4 | - |
| C-01 | 0 | 0 | 3 | 4 | 2 | 0 | 0 | - |
| C-02 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | - |
| C-03 | 0 | 0 | 4 | 0 | 0 | 6 | 5 | - |
| C-04 | 0 | 1 | 7 | 2 | 1 | 4 | 4 | - |
| C-05 | 0 | 0 | 4 | 0 | 0 | 3 | 2 | - |
| C-06 | 0 | 1 | 11 | 2 | 1 | 7 | 7 | **SAKNAD_FORREGLING** |
| H-01 | 0 | 0 | 8 | 0 | 0 | 5 | 4 | - |
| H-02 | 0 | 0 | 3 | 0 | 0 | 6 | 5 | - |
| H-03 | 0 | 0 | 3 | 0 | 0 | 8 | 8 | - |
| H-04 | 1 | 1 | 7 | 0 | 1 | 8 | 2 | - |
| H-05 | 0 | 1 | 8 | 2 | 1 | 3 | 1 | - |
| L-01 | 0 | 0 | 9 | 0 | 1 | 3 | 0 | - |
| L-05 | 0 | 1 | 7 | 2 | 1 | 4 | 3 | - |
| L-06 | 1 | 1 | 8 | 0 | 1 | 6 | 5 | - |
| L-07 | 0 | 1 | 12 | 0 | 1 | 9 | 3 | - |
| P-03 | 0 | 0 | 9 | 0 | 1 | 3 | 1 | - |
| P-05 | 0 | 0 | 4 | 0 | 0 | 7 | 7 | - |
| P-06 | 0 | 1 | 12 | 0 | 1 | 7 | 6 | - |
| P-07 | 0 | 1 | 8 | 3 | 1 | 3 | 3 | - |
| S-01 | 0 | 0 | 5 | 3 | 1 | 3 | 0 | - |
| S-05 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | - |
| S-06 | 0 | 1 | 12 | 0 | 1 | 5 | 3 | - |
| S-07 | 0 | 1 | 7 | 0 | 0 | 8 | 5 | - |
| T-01 | 0 | 0 | 4 | 0 | 0 | 1 | 1 | - |
| T-02 | 0 | 0 | 5 | 0 | 1 | 2 | 0 | - |
| T-04 | 0 | 0 | 6 | 1 | 1 | 2 | 2 | - |
| T-05 | 0 | 1 | 5 | 0 | 1 | 2 | 0 | - |
| T-07 | 1 | 1 | 7 | 0 | 1 | 4 | 3 | - |
| T-08 | 0 | 1 | 5 | 3 | 1 | 0 | 0 | - |
| T-09 | 0 | 1 | 7 | 4 | 1 | 5 | 5 | - |

**24 latchade feltillstånd** hittades över banken; alla når en utgång. **20 av
38** uppgifter har en larmutgång alls — i de övriga 18 är regel 2 avstängd, och
det står i `matt["larmutgangar"]` så att en tom kontroll inte ser ut som ett
godkännande.

## LIMITS

* **Inkopplingen i kedjan är villkorad, och det är ett val.** `granska_station`
  tar ett nytt, valfritt `krav`; utan det är domen **bit för bit** densamma som
  förut och nyckeln `industriell_form` finns inte. Skälet är mätt, inte
  befarat: guldgrinden räknar *"alla fyra körda och alla fyra True"*, så en
  femte nyckel i `KORORDNING` hade gjort varje befintlig cell röd över en natt
  medan tre andra sessioner mäter kedjan. Priset är att **ingen befintlig
  bänkarm kör grind 3b** förrän någon lämnar ett `Krav` — bänken (`bank/`,
  `tests/protocol/kor_fas9_modellen.py`) gör det inte i dag, och den ändringen
  ligger utanför den här ytan.
* **Ingen modellkörning.** Grinden är prövad mot referenser, mutationer och
  handskrivna fixturer — **inte** mot modellskriven kod. `M-121` kunde ställa
  sin regel mot M-96-korpusens 25 modellkroppar; motsvarande korpus för de här
  tre reglerna finns inte, så talet "hur ofta fäller den modellen, och hur ofta
  med rätt" är **omätt**. Det är den enda mätningen som avgör om reglerna i
  prompten faktiskt flyttar första försöket.
* **Bara 56 av 254 deklarerade förreglingar döms.** Resten lämnas åt
  körningsdomaren med sitt skäl (§6). Täckningen växer av sig själv när koden
  skrivs i den form M-121 kräver — men i dag är det **22 %**.
* **115 obundna väntelägen döms inte.** Grinden ser dem och rapporterar dem;
  bara de fem uppgiften själv pekar ut fälls. En vänteläge som verkligen ska
  övervakas men inte står i `failure_modes` går igenom.
* **Regel 2 missar ett larm som latchas inne i stegmaskinen.** Kravet "utanför
  stegmaskinen" finns för att sekvenskommandon annars ser ut som feltillstånd
  (§4 rad 3). Priset är att en modell som latchar sitt larm i en CASE-gren
  slipper undan.
* **Feltillståndets två utlösare är tidsur och analog gräns.** En insignal som
  går låg räknas som ett *tillstånd* (nödstopp, handläge), inte ett fel. Ett
  latchat fel som utlöses på något tredje sätt syns inte för grinden.
* **Larmutgången känns igen på uppgiftens egna ord** — namnet `SYS_ALARM` eller
  kommentaren *"samlingslarm"* / *"stationen stoppad"*. Ordlistan är avsiktligt
  snäv (delsträngen "larm" träffar också `stampelarm` i L-07 och hade gjort
  regel 2 till en falsk **grön**), men den är en ordlista, och en uppgift med
  annan vokabulär får ingen larmutgång igenkänd.
* **Ingen heltalsvärdesanalys.** En stegmaskin i `INT` som styr utgångar direkt
  (`S-05`) kan grinden inte följa. Den säger det i stället för att gissa.
* **Klartextparsern läser 50 av 150 interlockrader.** De 100 andra namnger
  antingen bara en signal (*"ingen robotrorelse nar EMG_OK ar lag"* — donet står
  i prosa) eller ingen alls. Recall är alltså **33 %**; precisionen mot de
  formella invarianterna är 46/46, men den nämnaren är bara de rader där en
  formell invariant finns att jämföra mot.
* **De två fällda referenserna är inte rättade.** `bank/uppgifter` är kö B:s yta
  och en ändrad referens ändrar sitt eget spår. Domen står här och i
  `KANDA_BRISTER`; åtgärden är kö B:s.
* **Domen är vår tolks modell av ST, inte OpenPLC:s.** Samma förbehåll som hela
  bänken. Grind 3b läser med `st/lasare.py` och resonerar om värden i vår egen
  semantik; `M-146`:s runtime-domare är en annan väg.
* **Antalet referenser växte under mätningen.** 33 vid första körningen, 38 vid
  den sista — kö B skriver facit parallellt. Talet "2 fällda" höll genom hela
  tillväxten, men tabellen är ett ögonblick.
