# M-51 — 185 ST-konstruktioner genom båda grindarna: 55 avvek, 36 var falska rödgrindar

**Datum:** 2026-09-04 · STruC++ 0.6.6 (CLI + `--build`) · vårt ST-lager i `svc/vc_assist_svc/st/`
**Körs av:** `tests/enhet/test_st_svep_mot_strucpp.py` (hoppar över sig självt när kompilatorn saknas)

## Talet först

| | konstruktioner |
|---|---|
| svepta | **185** |
| avvek FÖRE lagningen | **55** — 53 vi avvisar/kompilatorn bygger, 2 vi godkänner/kompilatorn bygger inte |
| lagade | **36** |
| avviker EFTER lagningen | **19**, var och en med ett nedskrivet skäl |

De 19 som står kvar: **14** är avsiktlig stränghet — det är hela skälet att
grind 2 och 3 finns. **3** är äkta falska rödgrindar som medvetet inte lagas.
**2** är fall där vi är trognare IEC 61131-3 än kompilatorn.

M-48 mätte fjorton konstruktioner och hittade tre avvikelser. Fjorton var ett
stickprov. Av de tre var två riktiga fel, och båda satt i klasser som visade
sig vara mycket större än en rad var: `END_IF` utan semikolon var sju fall, och
`TIME()` var femton saknade standardfunktioner.

## Varför en falsk rödgrind är dyr just här

`stationsgrind.granska_station` kör grind 2 och 3 — vårt eget ST-lager — **före**
grind 1, och med `stanna_vid_forsta` (förvalet i drift) returnerar den innan
kompilatorn ens startas. En falsk röd betyder alltså inte "modellen får ett
förvirrande meddelande". Den betyder att kompilatorn aldrig får se koden, och
att modellen får tillbaka ett fel som inte finns i kedjan.

Samma ordning gör den motsatta riktningen mildare än den låter: en falsk grön i
vårt lager fångas av grind 1 i samma anrop. Det är skälet till att de två
kvarvarande falska grönorna inte lagas — se nedan.

## Mätmetoden, och var den nästan ljög

Varje konstruktion skrivs som ett helt program och körs genom två oberoende
svar: `st.validera(kalla)` och `strucpp <in.st> -o <ut.cpp>` (0 = byggde,
1 = föll, mätt i M-48).

**Frontenden är ingen namnauktoritet.** Första svepet sa att `NOW()`, `MUX`,
`CONCAT` och trettiotvå andra namn "finns", därför att STruC++:s frontend
kompilerar `iA := HITTEPA(iB);` **utan en enda anmärkning**. Namnet faller
först när `--build` låter g++ se den genererade C++:en:

```
b.cpp:43:10: error: 'HITTEPA' was not declared in this scope
```

Med det skarpare facit visade sig `NOW()` inte finnas, medan alla andra
kandidater gjorde det. Ett svep som bara kört frontenden hade alltså skrivit in
ett namn i standardbiblioteket som aldrig går att bygga — en falsk grön
tillverkad av en mätning som såg grön ut. *(Mät mätmetoden innan du drar
slutsatsen. Samma fälla som M-48:s `$?` efter ett rör.)*

**Kompilatorn är inte strängare än oss.** Den godkänner `iA := rA` utan
konvertering, `arr[99]` i ett `ARRAY[1..10]`, `T#5s10m` med enheterna i fel
ordning, och `EXIT` utanför alla slingor. Fjorton av de nitton kvarvarande
avvikelserna är av det slaget, och de räknas inte som fel — de räknas som
grindens existensberättigande. M-48 sa samma sak om säkerhetsgränsen; svepet
visar att den observationen gäller mycket bredare än T2.

**Ett gemensamt deklarationsblock kan förgifta hela svepet.** Första körningen
rapporterade 91 av 131 avvikande. Alla 91 hade samma orsak: blocket deklarerade
`sA : STRING[20]`, och den formen bygger inte i STruC++ 0.6.6, så varje fall föll
på deklarationen i stället för på sin egen konstruktion. En fixtur som är
gemensam för hela svepet är också en enda felkälla för hela svepet.

## Vad som svepts

185 konstruktioner i tio grupper: satsformer (IF, CASE, WHILE, REPEAT, FOR,
EXIT, RETURN), semikolonvarianter efter varje blockslut, literalformer (tid,
datum, sträng, typad, hex/oktal/binär, exponent, understreck), operatorer och
prioritet, samtliga standardfunktionsblock (TON, TOF, TP, R_TRIG, F_TRIG, CTU,
CTD, CTUD, SR, RS), standardfunktioner, kommentar- och pragmaformer,
deklarationsformer (fält, struktur, egen FB, egen funktion, AT-adress,
VAR_GLOBAL, VAR_TEMP, RETAIN, CONSTANT, VAR_IN_OUT), skiftläge och blanksteg,
samt 31 former som **ska** falla — jakten på falska grönor. Fördelningen: sats 19, semikolon 7, literal 22, operator 15, block 13, funktion 31, kommentar 6, deklaration 14, form 27, trasig 31.

## De fem klasserna som lagades

| fall i svepet | Klass | Vad som var fel |
|---|---|---|
| 20 | **saknade standardfunktioner** | 32 namn: `MUX`, `MOVE`, `EXPT`, `LN`, `LOG`, `EXP`, `SIN`, `COS`, `TAN`, `ASIN`, `ACOS`, `ATAN`, `ATAN2`, `ADD`, `SUB`, `MUL`, `DIV`, `GT`, `GE`, `EQ`, `NE`, `LT`, `LE`, `CONCAT`, `LEFT`, `RIGHT`, `MID`, `INSERT`, `DELETE`, `REPLACE`, `FIND`, `TIME`. Samtliga gav `OKANT_NAMN`, som är F2 — samma dom som ett uppfunnet API-namn. |
| 7 | **semikolon efter blockslut** | `END_IF`, `END_CASE`, `END_WHILE`, `END_REPEAT`, `END_FOR` och `END_VAR` utan avslutande `;`. Kompilatorn bygger alla sex. Läsaren krävde semikolonet. |
| 4 | **exponentoperatorn `**`** | IEC 61131-3:s `**` fanns inte i lexern. `rA := rB ** 2.0;` var OLÄSLIG. |
| 3 | **baserad literal med typprefix** | `WORD#16#FF`, `INT#16#7F`, `BYTE#2#1010`. Kroppsscanningen släppte inte in `#`, så basdelen blev ett oväntat tecken. |
| 2 | **SEL:s resultattyp** | Den gemensamma typen räknades över *alla* argument, väljaren inräknad. `SEL(bA, iB, iC)` fick "argumenten har ingen gemensam typ" fastän båda de valda var INT. |
| **36** | | |

Två fynd på vägen som inte stod på listan men som hörde till samma rot:

* **Variadiskt styrdes av namnet.** Argumentkontrollen slog upp strängarna
  `"MIN"` och `"MAX"` för att avgöra om fler argument var tillåtna. Varje ny
  variadisk funktion blev därmed ett tyst argumentfel tills någon kom ihåg att
  fylla på listan — `MUX`, `ADD`, `CONCAT` och jämförelserna var precis sådana.
  Flaggan sitter nu på signaturen.
* **Två kopior av basvalideringen.** `16#FF` och `WORD#16#FF` validerade basen
  på var sitt håll. De delar nu en funktion, så de inte kan svara olika.

Alla trettiosex lagade fall är också bundna av billiga prov utan kompilator:
`test_st_syntax.py` (semikolon, `**`, baserade literaler) och
`test_st_semantik.py` (SEL, MUX, variadiskt, de nya namnen, `**`:s typregel).
Var och en av dem är körd mot ST-lagret **som det såg ut före lagningen** och
föll där.

## De tre falska rödgrindarna som medvetet står kvar

**`;` ensamt som sats.** Regeln som blev kvar är: *ett semikolon avslutar
något, det är aldrig en sats.* Efter de fem blockslutet och efter `END_VAR` är
det valfritt; ensamt fälls det. Skälet är inte att standarden förbjuder det —
IEC 61131-3:s satslista tillåter läst bokstavligt en tom sats, så M-48:s
motivering ("IEC har ingen tom sats") är svagare än den ser ut. Skälet är att en
tom sats inte bär någon mening i genererad kod, medan den är precis vad som blir
kvar när en modell skriver en halv sats. T7 i `tests/protocol/fas7_stationen.md`
är den kroppen, och kör man `kor_fas7_grindar.py` fälls den fortfarande av
grind 3 med `SYNTAX` — oförändrat mot M-48.

*En fälla på vägen:* när semikolonet gjordes valfritt efter `END_VAR` åt
END_VAR-raden upp kroppens ensamma `;`, och ett program utan innehåll blev
plötsligt godkänt. Nu räknas bara ett semikolon på **END_VAR:s egen rad** till
deklarationsblocket. Det finns ett prov för just den fällan.

**`DATE#` och `TOD#`.** Typlagret har ingen DATE- eller TIME_OF_DAY-typ. Att
släppa in literalen utan att kunna typa den hade betytt att den passerar
okontrollerad — en falsk grön i stället för en falsk röd. Att lägga till typerna
skulle dessutom auto-generera `DATE_TO_*`-konverteringar som ingen har mätt.
Meddelandet säger redan rakt ut att lagret inte stödjer formen, vilket är en
ärlig omfångsuppgift och inte ett påstående om att koden är fel.

## De två fallen där vi är trognare IEC än kompilatorn

**`T#-2h`.** Giltig IEC 61131-3, och vårt lager räknar den rätt
(−7 200 000 ms). STruC++ 0.6.6 lexar inte `#-` alls:
`unexpected character: ->#<-`. Formen `-T#2h` bygger däremot.

**`STRING[20]`.** Giltig IEC 61131-3, och vårt typlager använder längden till en
verklig kontroll (`'abcdefg'` ryms inte i `STRING[4]`). STruC++ 0.6.6 kan inte
deklarera den alls.

Ingen av dem lagas. Att skriva in kompilatorns begränsning i vårt lager binder
oss till **en version** av ett verktyg som ligger utanför repot, och för
`STRING[n]` skulle det dessutom kasta bort en fungerande längdkontroll. Båda
fångas av grind 1 i samma anrop som grind 2 och 3, så ingen av dem kan lämna
stationsdomen som en grön. Priset är att modellen får kompilatorns meddelande i
stället för vårt, och det priset är litet nog att betala.

Båda är **fastbundna**: svepprovet kräver att de fortsätter avvika åt exakt det
hållet. Bygger en framtida STruC++ dem, blir provet rött och raden ska bort.

## Vad som INTE är mätt

* **Runtime-semantiken.** Svepet frågar *går det att bygga?*, aldrig *gör det
  rätt sak?*. Den frågan är M-54:s (`strucpp_orakel.py`).
* **Tolken.** `tolk.py` fick `**`, därför att en operator som validatorn
  släpper igenom men den andra motorn inte kan räkna är ett hål i motorn, inte
  ett omfångsbeslut. De 32 nya funktionsnamnen fick den **inte**: den svarar
  `tolken kan inte räkna funktionen X` och det är fail-closed och ärligt, men
  det betyder att en bänkuppgift som använder `SIN()` nu passerar validatorn och
  faller i tolken i stället för tvärtom. Skulden är namngiven, inte betald.
* **Reproducerbarhet.** STruC++ ligger fortfarande i en sessionskatalog och inte
  i repot (öppen skuld sedan M-48). Provet söker den i `VC_ASSIST_STRUCPP` och
  sedan i PATH, och hoppar över sig självt med ett uttalat skäl när den saknas.
  Det är ärligt, men det betyder också att svepet **inte** körs i ett vanligt
  `pytest tests/enhet` på en ren maskin.
* **Andra kompilatorer.** MATIEC/OpenPLC är inte svepta. Där kedjan skiljer sig
  från STruC++ vet vi ingenting.

## Så körs det

```
VC_ASSIST_STRUCPP=/sokvag/till/strucpp python3 -m pytest \
    tests/enhet/test_st_svep_mot_strucpp.py -q
```

190 prov, ~22 s med fyra parallella kompilatorstarter. Utan variabeln: 190
överhoppade med skälet utskrivet.
