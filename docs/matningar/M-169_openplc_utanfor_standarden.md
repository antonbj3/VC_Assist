# M-169 — Vad OpenPLC-kedjan gör som IEC 61131-3 inte säger: spill, nolldivision, TIME över dygnet, strängar

**Datum:** 2026-09-05
**Status:** KLART (kö A, punkt A8)
**Körs av:** `tests/protocol/kor_A8_avvikelserna.py` (29 fall mot matiec och
  tolken, `--json`), samma skript med `--runtime` för de fem proberna genom
  OpenPLC Runtime v4. Permanenta fall i `tests/enhet/test_plc_avvikelser.py`
  (19 prov, gröna).
**Rigg:** matiec 0.1 (`iec2c`, ur `wzy318/openplc:latest`) i strikt läge
  (`-f`, inga avslappnande flaggor); vår ST-tolk; OpenPLC Runtime v4.2.1 i
  `vcassist-openplc-v4` (REST 18443, OPC UA 172.17.0.2:4840), STruC++ 0.6.6,
  node v22.22.0, PLC-uppgift `T#20ms`. `vcassist-openplc-m108` rördes inte.
  **Ingen modell körde i den här mätningen.**
**Facit:** matiec — OpenPLC:s egen IEC 61131-3-kompilator, skriven av någon
  annan — plus OpenPLC Runtime v4:s eget beteende. Där standarden inte kan
  citeras står raden som **oprövad paragraf**; repot har ingen kopia av
  IEC 61131-3 och ett "bör fungera" är inget belägg (samma konvention som
  M-125).
**Prövar:** `svc/vc_assist_svc/st/tolk.py` och `…/st/validator.py`
**Rådata:** `docs/matningar/radata/m169_avvikelser.json`, `…_ut.txt`,
  `…_runtime_spill.json`, `…_runtime_noll.json`, `…_runtime_noll3.json`
  (+ `_ut.txt` till var och en).

## Frågan

Varje motor har sina egna avvikelser. Fyra områden där standarden antingen
tiger eller lämnar utfallet till implementationen, och där vår tolk därför kan
stå ensam med en semantik ingen riktig motor har: **heltalsspill, division med
noll, TIME-aritmetik över dygnsgränsen och strängar över deklarerad längd.**

De två trasiga fallen, båda före mekanismen och båda gröna i körningen:

* `i : INT := 40000;` **måste** klassas MATIEC_STRÄNGARE. Blir det ÖVERENS
  mäter jämförelsen inte motorerna.
* `i := 32766 + 1;` **måste** klassas ÖVERENS. Ett svep utan ett fall som inte
  divergerar mäter bara sin egen stränghet.

## 1. Sammanräkningen: 29 fall

| klass | antal | vad det betyder |
|---|---|---|
| ÖVERENS | 13 | båda accepterar, eller båda avvisar |
| VI_STRÄNGARE | 9 | tolken avvisar, matiec släpper igenom |
| MATIEC_STRÄNGARE | 3 | matiec avvisar, tolken släpper igenom |
| EJ_JÄMFÖRBAR | 4 | matiec kan inte **uttrycka** konstruktionen (`STRING[n]`) |

`EJ_JÄMFÖRBAR` är ingen mellanform och ingen artighet: när kompilatorn inte
kan uttrycka konstruktionen är "vem är strängast" fel fråga, och att räkna den
som ÖVERENS eller som en oenighet hade båda varit fel.

**ÖVERENS betyder ÖVERENS OM TEXTEN, aldrig om värdet.** Sju av de tretton
ÖVERENS-raderna är spill- och TIME-fall där båda accepterar och sedan räknar
**olika** — det mäts i §4 och i M-125.

## 2. Heltalsspill: samma spill, två domar, och det beror på var det står

| konstruktion | matiec | tolken | OpenPLC (körning) |
|---|---|---|---|
| `i : INT := 40000;` | **AVVISAR** `Initial value has incompatible data type` | tar emot 40000 | — |
| `i := 32767 + 1;` | **AVVISAR** `Incompatible data types for ':=' operation` | 32768 | — |
| `i : INT := 32767; i := i + 1;` | ACCEPTERAR | 32768 | **−32768** (mätt §4) |
| `d : DINT := 2147483647; d := d + 1;` | ACCEPTERAR | 2147483648 | −2147483648 (M-125 a09) |
| `s : SINT := 127; s := s + 1;` | ACCEPTERAR | 128 | — |
| `u : UINT := 0; u := u - 1;` | ACCEPTERAR | **−1** | 65535 (M-125-familjen) |
| `b : BYTE := 255; b := b + 1;` | **AVVISAR** `Data type mismatch for '+' expression` | 256 | — |

Två saker att stanna vid.

**Samma spill fälls eller släpps beroende på om det går att räkna ut vid
kompilering.** `i := 32767 + 1` avvisas; `i := i + 1` med `i = 32767`
accepteras. Samma typ, samma vidd, samma överskridande. Skillnaden är bara att
konstantvikningen ser det ena. En användare som skriver konstanten får ett
kompileringsfel; en som skriver variabeln får `−32768` ut i cellen.

**`u : UINT := 0; u := u - 1` ger `−1` i vår tolk** — ett negativt värde i en
teckenlös typ. Tolken räknar i Pythons obegränsade heltal och har ingen
viddmodell alls. Det är samma rot som M-125:s svepfall a09–a12, och det står
nu som ett permanent prov.

**`BYTE + 1` fälls av matiec** därför att BYTE är en bitsträng och inte ett
tal; `ADD` är definierad över ANY_NUM. Vår tolk räknar 256 utan invändning.
Det är en läcka i vår riktning, och den är ny mot M-125:s typsvep.

## 3. Division med noll: matiec fäller `/` men släpper `MOD`

| konstruktion | matiec | tolken |
|---|---|---|
| `i := 10 / 0;` | **AVVISAR** `Data type mismatch for '/' expression` | Tolkfel |
| `i := 10 MOD 0;` | **ACCEPTERAR** | Tolkfel |
| `n : INT := 0; i := 10 / n;` | ACCEPTERAR | Tolkfel |
| `n : INT := 0; i := 10 MOD n;` | ACCEPTERAR | Tolkfel |
| `r := 1.0 / 0.0;` | ACCEPTERAR | Tolkfel |
| `z : REAL := 0.0; r := 1.0 / z;` | ACCEPTERAR | Tolkfel |
| `z : REAL := 0.0; r := z / z;` | ACCEPTERAR | Tolkfel |

Tre observationer:

* **Asymmetrin i samma kompilator.** `10 / 0` fälls, `10 MOD 0` inte. Samma
  sats, samma nolldivisor, olika dom.
* **Domen över `/ 0` kommer som ett TYPfel.** `Data type mismatch for '/'
  expression` nämner inte nollan. En användare som får det meddelandet letar
  efter en typkonvertering.
* **Vår tolk kan inte uttrycka utfallet alls.** Den kastar `Tolkfel` på varje
  nolldivision, också `1.0 / 0.0`, där en riktig motor ger `inf`. Det gör att
  bänken aldrig kan döma ett spår som passerar en nolldivision — den får ett
  `tolkfel:*` i stället för ett värde.

## 4. Den tredje kolumnen: vad som faktiskt HÄNDER i runtimen

matiec är typauktoritet, men den är inte kompilatorn i vår kedja — den är
`ST → STruC++ → OpenPLC v4`. Att matiec accepterar en text säger därför
ingenting om vad som händer när den körs. Fem prober, var och en en syntetisk
uppgift **utanför banken** vars facit begär tolkens värde, så att ett rött
utfall bär OpenPLC:s eget värde i sin egen bristtext.

| probe | tolken | OpenPLC v4 | runtimen efteråt |
|---|---|---|---|
| `O_SPILL := iMax + 1` (`iMax : INT := 32767`) | 32768 | **−32768** | levde |
| `O_REAL := rStor * rStor` (`rStor : REAL := 1.0E20`) | 1e40 (float64) | **inf** | levde |
| `O_RDIV := rEtt / rNoll` (REAL) | Tolkfel | **inf** | levde |
| `O_DIV := 111; O_DIV := iTio / iNoll; O_EFTER := 222` | Tolkfel | O_DIV **111**, O_EFTER **0** | se nedan |
| `n := n + 1; O_HB := n; IF TRIG THEN iSkrap := iTio / iNoll; …` | Tolkfel | O_HB **fryst på 304** vid både 200 och 400 ms | PLC-uppgiften **död** |

### Vad de två sista proberna visar, steg för steg

Den fjärde proben skriver en sentinel (`111`) **före** divisionen och en
markör (`222`) **efter** den. Utfallet — `O_DIV = 111`, `O_EFTER = 0` — säger
att scanet nådde fram till divisionen, skrev sentinelen, och **aldrig kom
förbi**.

Den femte proben avgör om slingan lever vidare: en pulsräknare skrivs **före**
divisionen, varje scan. Den stod på **304 vid både 200 ms och 400 ms**. Alltså
räknar den inte. **Hela PLC-uppgiften är död efter den första nolldivisionen.**

Under tiden:

* OPC UA-kanalen svarade på varje läsning, alla 40 proven;
* bildtabellen gick att läsa och skriva;
* domarens kanalkontroll före och efter sekvensen passerade;
* varje utgång stod kvar på sitt sista värde;
* REST-API:et rapporterade `RUNNING` — statusen blev `STOPPED` först när
  domaren själv stoppade PLC:n efteråt.

**En död PLC som ser ut som en levande.** Utgångarna fryser i det läge de råkade
ha; en ventil som var öppen förblir öppen.

### Var det ändå står skrivet — och vem som inte läser det

OpenPLC:s **egen runtimelogg** säger det, varje gång, ordagrant:

```
[2026-09-05 18:43:01] [ERROR] [task MAIN] terminated by signal 8 — other tasks keep running
[2026-09-05 18:43:02] [INFO] PLC State: TRANSITIONING_TO_STOP     <- vår egen stop-plc
```

Signal 8 är SIGFPE. Raden kom i alla tre nolldivisionskörningarna och saknades
i REAL-körningen (som gav `inf` utan att krascha).

Kedjan har alltså **ett** ställe som säger till, och ingen läser det:

| led | vad det säger om en nolldivision |
|---|---|
| vår ST-tolk | `Tolkfel: division med noll` — men bara om **tolken** kör koden |
| vår validator / grind 2–3 | tyst |
| matiec | fäller `10 / 0`, tiger om `10 / n` |
| STruC++ | tyst |
| OpenPLC:s g++ | tyst |
| OpenPLC:s REST-status | `RUNNING` |
| OpenPLC:s **runtimelogg** | `[ERROR] [task MAIN] terminated by signal 8` |
| `bank/domare_openplc.py` | ser bara frysta värden — dömer koden RÖD på fel grund |

`svc/vc_assist_svc/plc/openplc.py` har redan metoden `logg(rader, niva)`.
Skulden är alltså en rad kod, inte en saknad förmåga: **ingen grind läser
runtimeloggen efter en körning.** Det är den enda konkreta åtgärden ur den här
mätningen, och den hör hemma i `plc/stationsgrind.py`-kedjan.

## 5. TIME över dygnsgränsen: TIME har ingen dygnsgräns — men TOD har ingen kontroll

| konstruktion | matiec | tolken |
|---|---|---|
| `t := T#25h;` | ACCEPTERAR | 90 000 000 ms |
| `t := T#1d1h;` | ACCEPTERAR | 90 000 000 ms (identiskt) |
| `t := T#100d;` | ACCEPTERAR | 8 640 000 000 ms |
| `t := T#23h + T#2h;` | ACCEPTERAR | 90 000 000 ms |
| `d := TIME_TO_DINT(T#25d);` | ACCEPTERAR | 2 160 000 000 (ryms i DINT) |
| `t := T#5s10m;` | AVVISAR | Tolkfel (kontrollfall, båda fäller) |
| `q := TOD#25:00:00;` | **ACCEPTERAR** | läsaren avvisar TOD helt |
| `q := TOD#12:99:00;` | **ACCEPTERAR** | dito |
| `dd := D#2026-02-30;` | **ACCEPTERAR** | läsaren avvisar DATE helt |

TIME är en **varaktighet**, inte ett klockslag: det finns ingen dygnsgräns att
gå över, och `T#25h` är precis lika giltigt som `T#1d1h`. Frågan i punkt A8
var alltså delvis fel ställd — det finns ingen dygnsmodul i TIME. Det som
**däremot** finns är två andra saker:

1. **Svepet i bredden, inte i dygnet.** `T#100d` = 8 640 000 000 ms ligger
   fyra gånger över int32:s tak. M-125 t07 mätte utfallet: `TIME_TO_DINT(T#100d)`
   ger **50 065 408** i OpenPLC och 8 640 000 000 i vår tolk. Gränsen ligger
   vid ca 24,85 dygn, inte vid ett.
2. **TOD och DATE har inget värdeområde alls i matiec.** `TOD#25:00:00` är ett
   klockslag som inte finns, `TOD#12:99:00` har 99 minuter, och 30 februari
   finns inte — alla tre kompilerar. Det är den enda punkten i mätningen där
   matiec är **mildare** än vår kedja, och bara för att vår läsare avvisar
   TOD- och DATE-literaler helt. Den strängheten är alltså inget skydd; den är
   ett omfångsbeslut som råkar peka rätt.

## 6. Strängar över deklarerad längd: frågan går inte att ställa

| konstruktion | matiec | tolken |
|---|---|---|
| `s : STRING[4]; s := 'abcd';` | **AVVISAR** `Variable not declared in this scope` | `'abcd'` |
| `s : STRING[4] := 'abcdefgh';` | **AVVISAR** dito | `'abcdefgh'` |
| `s : STRING[4]; s := 'abcdefgh'; n := LEN(s);` | **AVVISAR** dito | `8` |
| `s : STRING[4]; i : INT; i := 1;` (s oanvänd) | **SEGMENTERINGSFEL**, returkod −11 | 1 |
| `s : STRING; …30 tecken…; n := LEN(s);` | ACCEPTERAR | `30` |

`STRING[n]` är standardens egen form för en sträng med maxlängd `n`. matiec
parsar deklarationen men **registrerar aldrig namnet**: första användningen
ger `Variable not declared in this scope`, alltså ett felmeddelande som pekar
på användningen och inte på deklarationen. Och deklareras en `STRING[n]` som
aldrig används **kraschar kompilatorn** — deterministiskt, tre körningar av
tre, returkod −11 (SIGSEGV) med tom utdata.

Slutsatsen är därför inte ett värde utan en gräns: **frågan "vad händer med en
sträng över sin deklarerade längd" går inte att ställa i OpenPLC-kedjan**, för
en sträng med deklarerad längd går inte att skriva. Vår tolk har i sin tur
ingen längdmodell alls — `STRING[4]` tar emot åtta tecken och `LEN` svarar 8.

Vår matiec-klient klassar segfaulten fail-closed som AVVISAR med returkoden i
texten. Det är rätt riktning av fel skäl, och det står nu som ett permanent
prov så att en utbytt matiec fäller det.

## 7. Vad som blev permanent

`tests/enhet/test_plc_avvikelser.py`, 19 prov, gröna. Ett prov per uppmätt
avvikelse plus de två trasiga fallen. Filen hoppar över sig själv med ett
uttalat skäl om matiec varken finns i `/tmp/opencode/matiec/`, i
`$VC_ASSIST_MATIEC` eller går att packa upp ur dockeravbilden — ett svep utan
facit får aldrig se grönt ut.

## LIMITS

* **Standardkolumnen är oprövad.** Repot har ingen kopia av IEC 61131-3.
  Varje rad om vad standarden *säger* står som oprövad paragraf. Det som är
  mätt är vad matiec, STruC++/OpenPLC och vår tolk **gör**.
* **Runtimekolumnen är fem prober, inte 29.** TIME och STRING mappas inte till
  bildtabellen (`domare_openplc._karta_for_post`), så deras körningsvärden går
  inte att läsa ut över OPC UA. SINT och UINT går inte att uttrycka som
  bankens signaltyper (tolken tar bara `bool`/`int`/`real`), så deras svep är
  övertagna ur M-125 och inte mätta om här.
* **Nolldivisionens verkan är mätt på en (1) runtime och en (1) plattform:**
  OpenPLC v4.2.1, x86-64, i docker utan `SCHED_FIFO`-rättigheter (loggen visar
  `sched_setscheduler failed`). Att en annan PLC gör något annat med SIGFPE är
  troligt och inte mätt.
* **`O_HB` fryst på 304** visar att slingan står still, inte **var** den står.
  Om PLC-tråden är död eller fångad i en signalhanterare är inte avgjort ur
  den här datan; OpenPLC:s egen formulering är *"other tasks keep running"*.
* **Ingen grind är byggd.** Mätningen pekar ut åtgärden (läs `klient.logg()`
  efter varje körning och fäll på `terminated by signal`), men den koden
  finns inte, och en mätning är inte en grind.
* **Ingen körning i Visual Components.** Spårfacit ligger bredvid ögondomen,
  aldrig i stället för den (invariant I1).
