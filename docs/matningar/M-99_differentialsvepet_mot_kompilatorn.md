# M-99 — differentialsvepet: fyra falska rödgrindar, fyra hål och en grind som hängde

**Datum:** 2026-09-05
**Körs av:** `tests/enhet/test_st_svep_mot_strucpp.py` (247 fall) och
`tests/enhet/test_st_syntax.py` (M-99-avsnittet)
**Facit:** STruC++ v0.6.6, kompilatorn i vår egen kedja
**Prövar:** hela `svc/vc_assist_svc/st/` — lexer, läsare, validator

## Frågan

`M-96` mätte vad en falsk rödgrind kostar. `T#3S` avvisades av vårt lager och
accepteras av kompilatorn; **nio av sexton grinddomar** i fas 9:s första
modelldrivna körning var det felet, och tre av fyra uppgifter slog i taket på
fyra varv. `M-51` hade svept 185 konstruktioner och ändå missat skiftläge.

Frågan här är vad mer M-51 missade. Metoden är densamma som avslöjade
skiftlägesfelet: generera konstruktionerna systematiskt i stället för att skriva
dem för hand, eftersom **en bugg som bara biter på det en människa inte råkar
skriva syns först när ingen människa sitter i slingan.**

## Vad som svepts

| axel | konstruktioner |
|---|---:|
| skiftläge (nyckelord, typnamn, FB-namn, funktionsnamn, blockparametrar, literalprefix, `TRUE`/`FALSE`, adresser, variabelnamn, `PROGRAM`/`VAR`/`STRUCT`/`AT`) | 149 |
| talformer (`1_000`, `1.0e3`, `1E3`, `-0`, `16#FF`, `2#1010`, `8#777`, ledande punkt, saknad decimal, ogiltiga baser) | 49 |
| tidsliteraler (skiftläge, `T#0s`, `T#-5s`, `TIME#1d2h3m4s5ms`, `LTIME#`, ogiltiga former) | 44 |
| blanksteg och radbrytningar (inuti `:=`, runt `..`, tabbar, CRLF, ensam CR, sidmatning, vertikaltabb, `END_ IF`) | 29 |
| uttrycksformer (`NOT NOT a`, djup parentesnästling, `a := b := c`, `;;`, tomma parenteser) | 29 |
| strängar (`$'`, `$N`, `$52`, `$"`, oavslutade, över radbrytning, `(*` inuti sträng) | 24 |
| kommentarer (nästlade `(* *)`, `//`, mitt i uttryck, mitt i tilldelning, pragma) | 23 |
| satsformer (tomma grenar, `ELSEIF`, `CONTINUE`, `GOTO`, `BY 0`) | 19 |
| deklarationsformer (fältinitierare, omvända gränser, namn som nyckelord, `NON_RETAIN`) | 18 |
| POU-ramen (`CONFIGURATION`, funktion utan returtilldelning, två program) | 10 |
| **summa** | **394** |
| adressmatris: sex storleksbokstäver × sexton typer | 96 |
| **totalt genom BÅDA lagren** | **490** |

Utöver det: **40 000 muterade källor** genom vårt lager ensamt. Där är facit
inte kompilatorn utan en invariant: `validera()` får aldrig lämna något annat än
en `Rapport`. Det svepet hittade det värsta fyndet i hela mätningen.

## Fynd per klass

| klass | antal | lagade |
|---|---:|---:|
| FALSK RÖDGRIND — vi fäller, kompilatorn accepterar, standarden ger kompilatorn rätt | 7 | 4 |
| HÅL — vi släpper igenom, kompilatorn fäller med rätta | 4 | 4 |
| STRÄNGARE — vi fäller med skäl, kompilatorn tiger | 11 nya | — |
| LÄTTARE — kompilatorversionens begränsning, inte vår | 7 nya | — |

### FALSKA RÖDGRINDAR — lagade

**1. Varje heltalstyps minsta värde gick inte att skriva.**
`iA := -32768;` avvisades med *"literalen 32768 ligger utanför INT
(-32768..32767)"*. Talet i meddelandet fanns inte i koden: unärt minus lämnade
literalvärdet orört, så intervallkontrollen prövade `32768` i stället för
`-32768`. Samma sak för `SINT#-128`, `DINT#-2147483648` och resten. STruC++
kompilerar formen. Lagat i `validator.typ_av`: minustecknet hör till literalen.

**2. Uttrycksdjupet mätte parserramar, inte nästling.**
Meddelandet sa *"uttrycket är djupare än 64 nivåer"*. Det **verkliga** taket låg
vid **åtta parenteser**: räknaren ökade en gång per prioritetsnivå i `NIVAER`, så
en parentes kostade åtta steg. En parameter som bar två storheter.

Det här är den dyraste formen av falsk rödgrind: en modell som får
*"djupare än 64 nivåer"* på `a := ((((((((b))))))));` har **ingen väg att laga
det**, för talet i meddelandet finns inte i koden. Lagat genom att räkna
nästlingsnivåer. Taket är nu mätt mot läsarens verkliga kapacitet — bisektion av
RecursionError med vakten avstängd ger **89 nivåer** vid `recursionlimit` 1000,
så 64 lämnar 25 nivåers marginal. Mätningen står som ett eget prov, inte som en
kommentar.

**3. Sidmatning och vertikaltabb.** `\x0b` och `\x0c` föll som *"oväntat
tecken"*; STruC++ bygger båda. De är ASCII, så lagrets **eget** skäl att avvisa
tecken — teckenkodningen genom OpenPLC och vidare ut som OPC UA-namn — gäller
dem inte, och `$P` i lexerns egen tabell är redan sidmatning. Lagat.

**4. En grind som kraschade i stället för att döma.** `ARRAY[10..1] OF INT` kom
ut ur `validera` som en **ofångad `ValueError`** ur typlagrets `__post_init__`.
`validera` fångar bara `Syntaxfel`. Domen var rätt — gränsen går baklänges — men
mekanismen var fel: en grind som kraschar lämnar ingen anmärkning åt någon att
laga, och den tar med sig hela `granska_station`.

### FALSKA RÖDGRINDAR — står kvar, med skäl

**5–6. Fältinitieraren**, `ARRAY[1..3] OF INT := [1, 2, 3]` och
upprepningsformen `[3(0)]`. Båda står i IEC 61131-3 och STruC++ bygger dem.
Läsaren läser startvärden som **ett uttryck** och har ingen nod för en
fältinitierare; lagningen rör modell, läsare, skrivare och typkontroll på en
gång och måste hålla genom tur-och-retur-provet.

Kostnaden på modellvägen är dessutom **mätt till noll**:
`skelett.granska_arbetsvariabler` släpper bara elementära typer och
standardfunktionsblocken, så modellen kan inte deklarera ett fält över huvud
taget — och resten av deklarationsdelen genererar kedjan själv. Formen kan bara
nås av kod som skrivs för hand eller av ett annat lager. Bokförd som skuld,
inte gömd.

**7. `CONFIGURATION` / `RESOURCE` / `TASK`.** Står i standarden, kompilatorn
bygger den. Lagrets domän är POU:er: konfigurationen runt dem genereras av
kedjan själv (`plc/skelett.py`), aldrig av modellen.

### HÅL — alla fyra lagade

**1. Adressens storleksbokstav mot den deklarerade typen: 80 av 96
kombinationer.** `q AT %QW1 : BOOL;` gick rakt igenom vårt lager. Det är ingen
typfråga inne i ST-koden utan en fråga om **var i bildtabellen** variabeln
ligger, och en BOOL på en ordadress läser och skriver fel antal byte i drift.

Tabellen är mätt, inte antagen — sex bokstäver × sexton typer genom kompilatorn:

| storlek | typer som bygger |
|---|---|
| `X` och utelämnad | BOOL |
| `B` | BYTE, SINT, USINT |
| `W` | WORD, INT, UINT |
| `D` | DWORD, DINT, UDINT, REAL |
| `L` | LWORD, LINT, ULINT, LREAL |

TIME saknas i varje rad: den har ingen adressbredd och byggde ingenstans. Efter
lagningen skiljer sig lagren i **0 av 96**.

**2. En decimalpunkt utan bråkdel.** `rA := 1.;` och `rA := 1.e3;` gick igenom
här och avvisades av kompilatorn. IEC 61131-3:s `real_literal` har både
heltalsdel och bråkdel.

**3. `VAR RETAIN CONSTANT`.** Kompilatorn: *"Variable cannot be both RETAIN and
CONSTANT"*. En konstant har inget tillstånd att behålla över en varmstart.

**4. En grind som HÄNGDE.** Det här hittade fuzzsvepet, inte kompilatorn.

`self._kika() in "_.#"` är **sant för den tomma strängen**, och `_kika()` lämnar
tom sträng vid källans slut. `BOOL#7` **utan avslutande radbrytning** snurrade
därför för evigt i lexern. `BOOL#7\n` föll rätt hela tiden — felet bet bara på
text utan radbrytning sist, och **det är precis vad ett kodstaket ur en modell
kan ge**. M-96 beskriver redan hur adaptern skalar av markdown-staket; det
lämnar text som kan sluta utan radbrytning.

En grind som hänger är värre än en som kraschar: den lämnar inte ens ett spår.
7 av 4 000 muterade källor träffade den. Efter lagningen: **0 hängningar och 0
kraschar på 40 000 muterade källor.** Provet kör i en egen process med
tidsgräns — ett hängprov i sviten hade inte gett ett rött prov, det hade gett ett
prov som aldrig svarar.

### STRÄNGARE — vi fäller, kompilatorn tiger, och vi har rätt

Elva nya rader, var och en med sitt skäl i `test_st_svep_mot_strucpp.py`:
`T#5s5s` (enheten två gånger), `T#1.5h30m` (decimaler i fel del), `T#5S10M`
(fel ordning, versal form), `iA := -32769` (utanför INT), sträng över en
radbrytning, kedjetilldelning `iA := iB := iC` (tilldelning är en **sats** i ST),
`ARRAY[10..1]`, tom kropp i en FUNCTION, tom gren i en CASE — plus de tre
falska rödgrindar som står kvar ovan.

Den tomma satsen förtjänar en egen rad. IEC 61131-3:s grammatik har `NIL` som en
sats, så `;` **är** härledbart och detta är formellt en falsk rödgrind. Beslutet
att ändå fälla den stod redan i M-51 med sitt skäl (en tom sats är vad som blir
kvar när en modell skriver en halv sats, och T7 i `fas7_stationen.md` är precis
den kroppen). Svepet ändrar inte beslutet men **mäter dess fotavtryck**: regeln
fäller också en tom CASE-gren och en FUNCTION vars hela kropp är `;`.

### LÄTTARE — kompilatorversionen är begränsningen, inte vi

Sju nya rader: `NOT NOT a` och `- -a` (IEC:s grammatik tar en unär operator per
uttryck och STruC++ håller på bokstaven — att härma det skulle göra oss
strängare än de kompilatorer modellen troligast sett, alltså **en ny falsk
rödgrind**), `iA < iB = TRUE`, `2.0 ** 3.0 ** 2.0` (högerassociativ kedja),
`1_000.5` (understreck i bråkdelen), `'a$"b'`, och `'a(*b'` — där STruC++ lexar
en kommentarstart **inuti en strängliteral**.

## Var svepet INTE hittade något

Det här är resultatet nästa person behöver mest, för det säger vad som är
uteslutet:

* **Skiftläge: 149 konstruktioner, noll nya avvikelser.** Nyckelord i fyra
  skiftlägesformer, tolv typnamn i tre, funktionsblocksnamn, funktionsnamn,
  blockparametrar (`ton1(in := ..., pt := ...)`, `ton1.q`), sju literalprefix,
  hexsiffror, `TRUE`/`FALSE`, elva adressformer, variabelnamn skrivna i annat
  skiftläge än deklarationen, `PROGRAM`/`VAR`/`TYPE`/`STRUCT`/`AT`/`ARRAY OF`
  i gemener. **Alla eniga.** M-96:s tidsliteral var ensam om det felet, och
  skiftlägesaxeln är nu utsvept på riktigt.
* **Kommentarer: 23 konstruktioner, noll avvikelser** utom kompilatorbuggen med
  `(*` inuti en sträng. Nästlade `(* (* *) *)` i tre nivåer, `//` mitt i ett
  uttryck, kommentar mitt i en tilldelning, pragma — alla eniga.
* **Blanksteg: 29 konstruktioner, noll kvarvarande avvikelser** efter
  sidmatning och vertikaltabb. CRLF, ensam CR, tabbar, radbrytning mitt i ett
  uttryck och mitt i ett villkor, blanksteg runt `..`, i index och i anrop —
  alla eniga. `END_ IF` med blanksteg faller i båda.
* **Fuzz: 40 000 muterade källor, noll kraschar och noll hängningar** efter
  lagningen.

## LIMITS

* **Facit är STruC++ v0.6.6, inte standarden.** Kompilatorn är varken en
  namnauktoritet (`HITTEPA(x)` passerar dess främmande; namnen prövas separat
  med `--build`) eller strängare än vi. Där de skiljer sig har domen fällts mot
  IEC 61131-3 så gott den går att läsa, och skälet står utskrivet per rad.
* **Ordalydelsen i standarden är inte verifierad mot en fysisk utgåva** för
  sidmatning och vertikaltabb som blanksteg, eller för `$"` i en enkelciterad
  sträng. Domen där vilar på kompilatorn plus lagrets egna uttalade skäl. Den
  som har utgåvan bör kontrollera de två raderna.
* **OpenPLC är fortfarande oprövad.** Kedjan dit kräver ett npm-paket som inte
  finns på maskinen (öppet sedan M-48). Två motorer som är överens är inte
  tre.
* **Fuzzen mäter EN invariant** — att `validera` lämnar en `Rapport` — inte att
  domen är rätt. Ett muterat program som felaktigt godkänns syns inte där.
* **Satsnästling är oskyddad.** Mätt: 326 nästlade `IF` innan RecursionError
  lämnar `validera` ofångad. Uttrycksdjupet har en vakt, satsdjupet har ingen.
  Ingen vakt lades till: 326 nivåer ligger långt utanför vad en modell
  producerar, och en vakt utan trasig fixtur i verkligt bruk är en gräns utan
  mätreferens. Skulden är bokförd här, inte lagad.
* **Tre falska rödgrindar står kvar** (fältinitieraren i två former,
  `CONFIGURATION`). De kostar reparationsvarv om en modell skriver dem.
* **Grannfallen är prövade per lagning, inte uttömmande.** `T#5X` och `T#5S10M`
  faller fortfarande, `-32769` faller fortfarande, ett icke-ASCII-tecken faller
  fortfarande — men ett svep är alltid ett stickprov ur en oändlig mängd.
* **Talet 394 är konstruktioner, inte täckning.** Axlarna valdes ur M-96:s
  uppdrag plus vad som verkade rimligt; ingen grammatiktäckning har räknats.
