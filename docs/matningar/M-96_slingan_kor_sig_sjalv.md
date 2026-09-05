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

*(Fylls i när körningarna mot den lagade grinden är klara. De första talen —
1 av 4 lösta, 3 av 4 i taket, 1,045 USD — är mätta med den TRASIGA grinden och
publiceras inte som fasens tal.)*

## LIMITS

* **Talen mot den lagade grinden är inte klara än.** Det som står ovan är
  mekanismen och fyndet, inte fasens utfall.
* **n = 1 per uppgift och läge.** Ingen upprepning, ingen spridning.
* **Fyra uppgifter av 51** — bara de har spårfacit.
* **En modell, en promptformulering.** Byts någotdera kan talen bli andra.
* **Domen kommer ur vår ST-tolk**, korsprövad mot STruC++ men inte mot OpenPLC.
* **Skiftlägessvepet är tretton konstruktioner på lexernivå**, inte hela
  grindkedjan och inte M-51:s 185.
