# M-96 — slingan kör sig själv, och den avslöjade en falsk rödgrind

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_fas9_slingan.py`
**Prövar:** fas 9:s enda öppna punkt

## Punkten som stod öppen

`tests/protocol/fas9_banken.md`, ordagrant:

> *"Slingan drevs för hand. Bryggan mellan grind och modell är ett meddelande,
> inte ett API-anrop. Det finns ingen nyckel och ingen modellklient i repot.
> `M-52`:s tak på fyra varv är därmed oprövat med en riktig modell."*

De tre talen var mätta. Sättet de togs fram på var det inte.

## Bryggan

`Reparationsslinga.kor` har alltid tagit en `Modell` som inparameter. Det som
saknades var en modell att ge den — repot hade bara `AttrappModell`.

`claude -p` duger som transport och kräver **ingen API-nyckel i repot**: CLI:t
bär sin egen inloggning. Tre saker är invarianter, var och en med trasiga
fixturer:

1. **Modellen kan inte läsa facit.** Tom verktygslista *och* en arbetskatalog
   utanför repot. Flaggan är en flagga; sökvägen är ett andra lager. En katalog
   i repot avvisas med skälet utskrivet.
2. **Ett misslyckande ser aldrig ut som ett svar.** Tom text, `is_error`, fel
   `subtype`, nollskild slutkod, oparsbar utdata och tidsgräns kastar allihop.
   *"Modellen lagade ingenting"* och *"modellen svarade aldrig"* är två olika
   mätningar.
3. **Kostnaden följer med.** Ett tak på fyra varv säger ingenting om vad fyra
   varv kostar.

Saknas `claude` avslutar körningen med kod 2 i stället för att falla tillbaka på
en attrapp. Attrappens tal får aldrig rapporteras som en modells.

Adaptern ligger **utanför** `harness/`: `test_ingen_leverantor_namns_utanfor_oversattningen`
förbjuder varje leverantörsnamn där inne, och den regeln är samma oberoende
operatören vill ha mot programvara och licenser i stort. Grinden fällde mig när
jag lade den fel.

## Det första varvet gick till min egen kanal

Körning ett, H-04, varv 1: **`rad 33: [SYNTAX/F1] oväntat tecken '`'`**.

Modellen svarade i ett markdown-kodstaket och jag matade staketet till
ST-kompilatorn. Systemprompten säger redan *"Svara med enbart kroppens rader"* —
och en prompt är en bön. Modellen rättade sig själv i varv 2, så felet kostade
en fjärdedel av taket och var **mitt**, inte modellens.

Staketet tas nu bort, men **bara** när hela svaret är ett enda block. Finns det
flera är det tvetydigt vilket som är kroppen, och att välja åt modellen vore att
skriva dess svar. Då går texten fram orörd och grinden får döma — den har rätt
att säga nej, det har inte adaptern.

## Fyndet: nio av sexton grinddomar var vårt eget fel

Första hela körningen gav 1 av 4 lösta och 3 av 4 i taket. Innan det skrevs ned
lästes grindens egna ord. Felklasserna över alla varv:

| klass | antal |
|---|---:|
| `TIDLITERAL/F1` | **9** |
| `DUBBELSKRIVNING/F7` | 5 |
| `SYNTAX/F1` | 2 |

Nio av sexton var samma dom: `T#3.0S`, `T#3S`, `T#2.0S`, `T#2S` — *"går inte att
läsa som tid"*.

**IEC 61131-3 är skiftlägesokänsligt.** `lexer.py` läste prefixet `T#`/`TIME#`
med `re.I` men delregexen för tal och enhet utan. Halva literalen var alltså
skiftlägesokänslig och halva inte.

Domen ställdes **inte** mot min läsning av standarden utan mot kompilatorn i vår
egen kedja. STruC++ v0.6.6, nio former:

| literal | STruC++ | vår grind (före) |
|---|---|---|
| `T#3s` | accepterad | accepterad |
| `T#3S` | **accepterad** | **avvisad** |
| `T#3.0s` | accepterad | accepterad |
| `T#3.0S` | **accepterad** | **avvisad** |
| `T#500ms` | accepterad | accepterad |
| `T#500MS` | **accepterad** | **avvisad** |
| `t#3S` | **accepterad** | **avvisad** |
| `T#1h30m` | accepterad | accepterad |
| `T#1H30M` | **accepterad** | **avvisad** |

`test_st_svep_mot_strucpp.py` säger själv i sin docstring varför det är dyrt:

> *"en modell som får tillbaka ett fel som inte finns brinner reparationsvarv på
> att laga något som redan fungerade, och lär sig fel sak."*

Det stod skrivet sedan `M-51`, och det är precis vad som hände — nu mätt i varv
och i kronor. M-51:s svep på 185 konstruktioner täckte inte skiftläge.

**Automatiseringen är vad som avslöjade felet.** `M-80`:s handdrivna körning
nämner ingen `TIDLITERAL`: den som relaade skrev gemener av vana. En bugg som
bara biter på det en människa inte råkar skriva syns först när ingen människa
sitter i slingan.

## Var skiftlägesfelet INTE fanns

Tretton konstruktioner i gemener och versaler — `if/then`, `case/of`,
`while/do`, `for/to`, `and/or/not`, `true/false` — genom både vår tokeniserare
och STruC++. **Alla tretton eniga.** Tidsliteralen var ensam om felet i det
lagret.

## Talen

Alla mot den **lagade** grinden. Talen från de första körningarna publiceras
inte som fasens: de mättes med tidsliteralbuggen i grinden.

### Enskott — modellen får ett försök

Fem försök per uppgift, samma fyra uppgifter i båda armarna, samma transport.

| Uppgift | utan grindreglerna | **med** |
|---|---:|---:|
| H-04 | 0 av 5 | 0 av 5 |
| L-05 | 0 av 5 | **1 av 5** |
| S-05 | 0 av 5 | **5 av 5** |
| T-07 | 0 av 5 | 0 av 5 |
| **summa** | **0 av 20** | **6 av 20** |
| kostnad | 2,140 USD | 2,825 USD |

Utan reglerna: noll. Inte noll av fyra — noll av tjugo. En fast nolla, inte
brus.

**Med reglerna: 6 av 20, och fördelningen är hela poängen.** Effekten är inte
att alla uppgifter blir lite bättre. **S-05 går från 0 av 5 till 5 av 5** —
helt löst, varje gång. L-05 rör sig knappt. De andra två rör sig inte alls.

Det säger något en summa hade dolt: S-05 föll enbart på konventioner som ingen
sagt. Så fort de sades var uppgiften inte svår. H-04, H-05 och T-07 är svåra av
andra skäl, och för dem hjälper reglerna inte.

Varv till löst i alla sex fallen: **1**. Det är enskott, per definition.

*(Med-armen körde fem uppgifter — banken växte med H-05 mitt i, och den gav
0 av 5. Tabellen ovan jämför bara de fyra som kördes i båda armarna, annars
hade nämnarna skilt sig.)*

Felklasserna i enskott utan regler: `DUBBELSKRIVNING` i 3 av 4 uppgifter,
`SYNTAX` i 1. Ingen av dem är okunnighet om palleteringsceller. Båda är
konventioner grinden kräver och som ingen sagt.

### Flerskott — grindens egna ord tillbaka, tak fyra varv

`--lage historik`, alltså modellen ser sina tidigare försök och varje doms
egna ord.

| Uppgift | utfall | varv | kostnad |
|---|---|---:|---:|
| H-04 | **löst** | 3 | 0,296 USD |
| L-05 | **löst** | 1 | 0,134 USD |
| S-05 | **löst** | 2 | 0,287 USD |
| T-07 | slog i taket | 4 | 0,605 USD |
| | **3 av 4** | median **2** | **1,322 USD** |

Det är det tal som svarar mot kravet *"flerskott som fastnar på grindar och
görs om är fallback"*. Reserven fungerar, och den kostar en dryg dollar för
fyra industriceller.

**Taket på fyra varv är nu prövat mot en riktig modell**, vilket `M-52` aldrig
kunde. Det räckte i tre fall av fyra och slog i i det fjärde. Ett tak som
aldrig prövats är ett påstående; det här är ett mätt tal.

### Vad avståndet mellan 0 av 20 och 3 av 4 betyder

Skillnaden är inte modellens förmåga. Det är **återkopplingen**. Samma modell,
samma uppgifter, samma grindar — enda skillnaden är att den andra körningen får
se vad grinden sa.

Det säger var arbetet mot enskott ska ligga: allt som grinden vet ska sägas
**före** skrivningen, inte efter. `forhandsregler.py` gör det för grind 2, grind
3 och ögats nio klasser, genererat ur grindarnas egna tabeller. Effekten mäts
i en pågående körning.

## Efterkontroll: teckenfelet i DUBBELSKRIVNING förorenade INTE talen

En adversariell granskning av promptdesignen fann att `validator._sekvens` bar
**motsatsen till sitt eget fältnamn** — fältet heter *villkorad*, raden räknade
*ovillkorad*. Grinden hade därför fel åt båda hållen, och den falska **gröna**
var den allvarliga: en verklig F7-kapplöpning släpptes igenom.

Misstanken följde direkt: bar några av den här mätningens fem
`DUBBELSKRIVNING`-domar den falska röda? Då vore talen ovan förorenade, precis
som de första körningarna var av tidsliteralbuggen.

**De gör de inte.** Körningen sparar `kroppar_per_varv` — modellens egen kod,
inte bara domen — så frågan gick att avgöra utan ett enda nytt modellanrop.
Varje sparad kropp från alla fem körningarna kördes genom den **lagade**
grindkedjan:

| | |
|---|---:|
| varv där `DUBBELSKRIVNING` föll | **9** |
| faller fortfarande efter rättelsen | **9** |
| falska röda som försvann | **0** |

Talen står alltså kvar. Att `kroppar_per_varv` sparas är skälet att det gick
att avgöra på minuter i stället för att köras om — och den raden lades till just
efter att tidsliteralbuggen tvingade fram en omkörning från början.

## Tillägg 2026-09-05 (M-121)

Efterkontrollen ovan gällde teckenfelet i `_sekvens`. M-121 gick ett steg
längre och lät grinden pröva om två skrivningars villkor **kan** vara sanna i
samma scan (sökvägsvillkor + SAT, rena mellanvariabler substituerade). Genom
den grinden faller **3 av de 13** `DUBBELSKRIVNING`-domarna över den här
körningens sparade kroppar bort: H-04 varv 1 och 4 (`GRP_OPEN`, villkoren
`NOT ST320_GRP_CLOSED` mot `ST320_GRP_CLOSED`) och T-07 varv 1 (`IDX_START`,
`CLP_CLOSED` mot `NOT CLP_CLOSED`). De var falska röda, och modellen brände
varv på dem. Tio står kvar; klassningen står i M-121. Kropparna ligger nu i
`docs/matningar/m96_korpus_*.json` och körs om med
`tests/protocol/kor_m121_uteslutning.py`.

## LIMITS

* **Fyra uppgifter, en modell, en promptformulering.** 6 av 20 är mätt, inte
  antaget, men det är fyra celler av bankens 61. Fas 21 äger skalan.
* **Effekten sitter i en enda uppgift.** S-05 bär fem av de sex lösta. Ett
  annat urval av fyra uppgifter kunde gett 1 av 20 eller 10 av 20 med exakt
  samma regler. Det är den svagaste punkten i talet.
* **Armarna kördes efter varandra, inte parat.** Banken växte emellan (H-05
  tillkom), och tabellen jämför därför bara de fyra delade uppgifterna.
* **T-07 slog i taket och orsaken är inte utredd.** Fyra varv, 0,605 USD, och
  ingen dom lästes efteråt. Att det är uppgiften och inte grinden är
  **antaget**.
* **n = 1 per uppgift och läge.** Ingen upprepning, ingen spridning.
* **Fyra uppgifter av 51** — bara de har spårfacit.
* **En modell, en promptformulering.** Byts någotdera kan talen bli andra.
* **Domen kommer ur vår ST-tolk**, korsprövad mot STruC++ men inte mot OpenPLC.
* **Skiftlägessvepet är tretton konstruktioner på lexernivå**, inte hela
  grindkedjan och inte M-51:s 185.
