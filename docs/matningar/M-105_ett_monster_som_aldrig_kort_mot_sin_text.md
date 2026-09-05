# M-105 — ett mönster som aldrig körts mot texten det ska läsa

Mätt 2026-09-05.

Kod: `svc/vc_assist_svc/monsterbevis.py`, `tests/enhet/test_monsterbevis.py`,
`scripts/monsterbevis_svep.py`.

## Frågan

Tre fel på en natt hade samma form.

* `skuld.py:_ARLIGHET` var skriven i ASCII mot svensk text. Åtta av elva grenar
  kunde aldrig matcha någonting, och två av dem hade lagts till just för att
  fånga M-44 och M-47 — och fångade ingendera. (M-70)
* `st/lexer.py:_TIDSDEL` saknade `re.I` medan prefixregexen bredvid hade den.
  `T#3s` gick igenom, `T#3S` avvisades. IEC 61131-3 är skiftlägesokänsligt.
  Nio av sexton grinddomar i fas 9:s första modelldrivna körning var den
  falska rödgrinden. (M-96)
* `harness/text.py:NEKANDE` är ingen regex utan en ordlista, och den fyrade på
  fel storhet: vilket nekande ord som helst i texten tystade ärlighetsgrinden.
  (M-94 fynd 1)

Det gemensamma är **inte** att de är regexar. Det är att de är **matchare som
aldrig körts mot texten de ska läsa**. Frågan: hur många fler finns?

## Hur ytan delades

116 mönster på modulnivå (`^_?[A-Z][A-Z_0-9]* = re.compile`) under `svc/` och
`ext/`, lästa med `ast` och inte med grep — en regex över källan hade varit
precis den felklass mätningen finns för att mäta.

Gränsen mellan de två klasserna går vid **textens producent**, och den är
statbar i en mening:

| klass | vem skriver texten | vad blir en miss |
|---|---|---|
| **tolkar** | Visual Components självt: `.rsc`, `.vcmx`, dess XML | ett fält som **SAKNAS** — "den som får tomt vet att frågan inte gick att besvara" |
| **avgör en dom** | en människa, en språkmodell, ett främmande verktygs utdata, eller vårt eget protokoll | en anmärkning, ett fel, ett godkännande eller ett rapporterat tal — **tyst** |

**16 tolkar** — och det är exakt fyra filer: `datablad.py`,
`komponentfil.py`, `komponentdatablad.py`, `katalogindex.py`. Alla fyra är
läsare över VC:s egna filformat.

**100 avgör en dom.** Klassningen med motivering per fil ligger i
`monsterbevis.py`, inte i den här texten, så att spärren och mätningen inte kan
glida isär.

## Hur bevisningen mättes

Två halvor krävs, och de mäter olika saker:

* **fyrar** — ett prov som visar att mönstret träffar något det *ska* fånga
* **fyrar inte** — ett prov som visar att det *inte* träffar något det inte ska

Ett mönster som fyrar på allt mäter lika lite som ett som aldrig fyrar.

Svepet: varje kompilerat mönster byttes mot en genomskinlig omslagare som
räknade träff och miss, och hela `tests/enhet` kördes (6452 prov vid
mättillfället). Utfallet över de 100 som avgör en dom:

| | antal |
|---|---|
| båda halvorna observerade | **68** |
| bara den ena | **28** |
| ingen alls | **4** |

De 4 som aldrig kördes över huvud taget är personatäckningens fyra mönster
(`personatackning.py`), som gör ett specdokument till ett rapporterat tal.

Fem mönster i `plc/baslinje/sprak.py` anropades hundratals gånger utan att
någonsin matcha: `_M_HALL`, `_M_HANDLING_OCH_HALL`, `_M_HANDLING_PA_FLANK`,
`_M_RAKNA`, `_M_UPPEHALL`. Alla fem visade sig fungera när de matades med rätt
text — bankens 404 rader använder bara aldrig de formerna. `_VCTYP` och
`_VCKONST` i ärlighetsgrindens textlager fyrade noll gånger på 149 anrop, av
samma skäl.

## Varför spärren räknar prov och inte observationer

Instrumenteringen säger var man ska sikta. Den är **inget bevis**. Att ett
mönster returnerade en träff under sviten visar att det *anropades*, inte att
någon *kontrollerade svaret*, och observationen försvinner den dag det
orelaterade provet skrivs om. Ett prov som namnger både en sträng som **måste**
matcha och en som **inte får** det är det enda som överlever en refaktorering.

Spärren räknar därför tvåsidiga prov i `BEVIS`-tabellen, och varje sträng där
körs mot det **levande** kompilerade mönstret med den metod koden faktiskt
använder.

## Vad som lagades

Sju fynd, var och en med en trasig fixtur som föll mot koden **före**
lagningen. Den röda körningen: 10 fallande fixturer, 6 gröna kontrollfall.

**1. Mätningskoden gick förbi M-99.** `harness/instruktioner.py:_MATNING` var
`^M-(\d{2})$`. Repot skrev M-100 den 2026-09-04. En beteenderegel med
härkomsten `M-100` föll igenom till filkontrollen och anmärktes som "varken en
fil eller en mätningskod" — en falsk anmärkning i den grind som granskar
modellens egna beteenderegler. Provet går nu över **alla** mätningar på disk,
så det åldras inte om med numret igen.

**2. Korsreferensen var skriven i ASCII mot svensk regeltext.**
`_KORSREFERENSER` bar `"som namnts"` och jämfördes mot ett rent
`text.lower()`. **46 av 46** regeltexter i `instruktioner/` innehåller å, ä
eller ö. Grenen kunde aldrig fyra på den enda stavning en riktig regel
använder. Samma felklass som M-70.

**3. Säkerhetsordlistan hade ett hål i sina tvillingar.**
`harness/sakerhet.py:SAKERHETSORD` är genomgående parad
(`nodstopp`/`nödstopp`, `ljusrida`/`ljusridå`) — utom för `sakerhetsplc` och
`sakerhetsgrind`, som saknade sina. Meningen *"vi byglar säkerhetsgrinden
tillfälligt"* gick rakt igenom en **säkerhets**grind. Lagningen är inte två nya
poster: en handskriven tvillinglista glömmer nästa ord också. Båda sidor
avdiakritiseras nu.

**4. Den lokaliserade adressen lästes i ett enda skiftläge.**
`plc/signalkarta.py:_ADRESS` saknade `re.I` medan `_typ_av_text` i **samma
fil** redan gjorde `.upper()` på typen och `plc/skelett.py:_HAR_ADRESS` redan
bar `re.I`. `%qx0.0` är en giltig IEC 61131-3-adress och avvisades. Enbart
`re.I` hade varit **värre än felet**: `%qx0.0` och `%QX0.0` hade blivit två
skilda `Adress`-värden och `plats()` hade sagt att de inte krockar. Området och
storleken normaliseras därför till versaler.

**5. Förfiningen läste operatörens mått i ett enda skiftläge.**
`plan/forfining.py:_MM`, `_TAKT` och `_CYKEL` saknade `re.I` medan
syskonmodulen `plan/lasning.py` — som läser **samma text** — bär `re.I` på
varenda mönster. `_CYKEL` fyrade dessutom noll gånger i hela sviten, och den
vanligaste svenska formen `"12 sek per cykel"` gick igenom som otolkad. Här
krävde lagningen ett steg till: enheten jämfördes mot `("minut", "min")` i
gemener, så `re.I` **utan** `.lower()` hade gjort 120 burkar i minuten till 120
i timmen — ett tyst fel som är värre än det ursprungliga, där talet aldrig
lästes alls.

**6. Ett mönster utan `re.I` bland trettio som har det.**
`plc/baslinje/sprak.py:_T_UTGANG` var det enda mönstret i modulen utan `re.I`.
Alla sjutton `_M_*`, alla åtta `_F_*` och de tre `_I_*` bär den, och alla läser
samma uppgiftstext. Jämförelsen av `tecken` görs nu i gemener, av samma skäl
som i fynd 5.

**7. Sex ordlistposter som aldrig kunde träffa.** `plan/lasning.py` jämför
alltid mot `harkomst.normalisera(...)`, som byter å och prickar mot ASCII.
Posterna `"högst"`, `"arbetsområde"`, `"lång"`, `"längd"`, `"hög"`, `"höjd"`
kunde därför aldrig träffa. Utfallet var ofarligt — ASCII-tvillingen fanns i
alla sex fallen — men det är samma falska trygghet som kostade M-70 åtta döda
grenar. Posterna är borttagna, och en grind kräver nu att varje post står i
jämförelseform.

## Ordlistorna

Ett andra svep över modulnivå-listor av strängar (tupler, frozenset, dict) gav
**268 listor**, varav **95 konsulteras när en dom fälls** och 173 är data
(JSON-schemafragment, felkodskataloger, parservitlistor, enhetstabeller).

**52 av de 95 matchas mot fri text** — modellens svar, operatörens begäran,
markdown-spec, korpusens regeltexter. Det är där felklassen sitter, och fynd
2, 3 och 7 ovan kommer därifrån.

Ytterligare tre saker svepet såg och som **inte** är lagade här (se LIMITS):

* `harness/text.py:NEKANDE` och `FORBEHALL` har **noll anropare** kvar i
  `svc/` och `ext/`. Förebilden för hela mätningen är alltså själv den felklass
  den mäter — men filen är en annan cells pågående arbete (M-94/M-95:s
  delning), och rörs inte här.
* `harness/loop.py:STOPPREGLER` och
  `plc/baslinje/morfologi.py:STATUSSUFFIX` läses aldrig.
* Hela `plc/baslinje/sprak.py` är skriven i ASCII utan avdiakritisering. Idag
  ofarligt — **noll** av 404 rader i `bank/uppgifter/*.json` bär å ä ö — men
  ingenting håller det sant. En rad som skriver `"är låg"` eller `"övervakningen"`
  hamnar i `olasta`, och det talet rapporteras.

## Spärren

`tests/enhet/test_monsterbevis.py`, samma form som `test_skuld.py` och
`TROSKELSKULD.md`:

    UTAN_BEVIS = 58

58 av de 100 mönster som avgör en dom saknar tvåsidig bevisning. 42 har den nu.
Talet får **bara gå nedåt**, och ett tak som ligger över verkligheten faller
också — annars ruttnar spärren.

Taket är inte satt till noll, och det är med flit. Att skriva 58 prov i blindo
hade varit att uppfinna vad mönstren *ska* läsa i stället för att ta reda på
det, och det är precis den skuld spärren finns för.

Spärren biter på tre sätt, provat:

* tas ett bevis bort går talet till 59 och taket faller
* tas den ena halvan bort listas mönstret som halvbevisat och faller
* tas `re.I` bort ur `signalkarta._ADRESS` igen faller bevisen med
  *"skulle fyra på `'%qx0.0'` men gjorde det inte"*

## LIMITS

* **Klassningen är ett omdöme, inte en mätning.** Gränsen "VC skriver filen" är
  statbar, men `katalogindex._NAMN` bygger fält som ett söklager sedan svarar
  "finns inte" på. Att den domen är sökningens och inte mönstrets är ett
  ställningstagande. Faller det, flyttas fem mönster från *tolkar* till *avgör
  en dom* och taket stiger med upp till fem.
* **Spärren ser bara den yta som mättes.** 116 mönster, uppräknade i
  `monsterbevis.py`. Elva nya mönster tillkom i tre andra moduler
  (`aterhamtning/grind.py`, `llm/`, `tillverkardatablad.py`) medan mätningen
  pågick, och de är varken klassade eller bevisade. Skälet står i modulen: en
  spärr som räknar allt som finns just nu blir röd av en annan cells arbete i
  stället för av sitt eget, och en spärr som blir röd av fel sak slutar läsas.
  `monsterbevis.nytt_sedan_matningen()` listar dem, men inget prov faller på
  dem. Det är spärrens kända hål.
* **De 68 "båda halvorna" är observationer, inte prov.** De kommer ur
  instrumenteringen av sviten, och de räknas därför **inte** som bevisning i
  spärren. Talet 58 är alltså inte "58 omätta mönster" utan "58 utan ett prov
  som namnger vad de ska och inte ska läsa".
* **En observerad miss är inte en avsedd miss.** Att ett mönster returnerade
  "ingen träff" under sviten visar att det kördes mot något det inte fångade —
  inte att just den raden var ett fall det *skulle* avstå från.
* **Ordlistesvepet är inte kört till slutet.** 95 dömande listor hittades; sju
  granskades i källan och tre lagades. De 88 övriga är oprövade, och ingen av
  dem har en tvåsidig bevisning. Spärren räknar dem inte.
* **Fem filer rördes inte med flit** — `harness/arlighet.py`,
  `harness/redovisning.py`, `harness/verifiering.py`, `harness/oga.py`,
  `verktyg/matning.py` — därför att en annan cell arbetade i dem samtidigt.
  `harness/verifiering.py:_TAL_I_STRANG` är klassad som dömande och räknas i
  taket, men saknar prov.
* **Fynd 3 är inte provat mot en riktig modell.** Att `granska_text` nu fångar
  *"vi byglar säkerhetsgrinden tillfälligt"* är mätt i ett enhetsprov, inte i en
  körning där en språkmodell faktiskt föreslår det.
* **Diakritiken är lagad åt ett håll i taget.** `text.utan_diakritik` används
  nu av `sakerhet.py` och `instruktioner.py`. Fyra andra egna
  avdiakritiseringar finns kvar i repot (`skuld.py`, `text.normalisera`,
  `verktyg/katalog.py`, `personatackning.py`). De är inte sammanslagna.
* **Instrumenteringens tal åldras.** Svepet ligger i
  `scripts/monsterbevis_svep.py` och går att köra om, men talen 68/28/4 gäller
  sviten som den såg ut 2026-09-05 (6452 prov). Sviten växte till 6936 under
  samma dygn av parallellt arbete, och siffrorna är inte omkörda efter det.
