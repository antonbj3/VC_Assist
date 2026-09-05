# M-146 — En domare som domer ur OpenPLC-runtime, inte ur var egen ST-tolk

**Datum:** 2026-09-05
**Status:** KLART (kö A, punkt A2)
**Körs av:** `tests/protocol/kor_A2_domare_openplc.py` (kräver openplc +
  strucpp), `tests/enhet/test_bank_domare_openplc.py` (33 prov, ingen runtime)
**Rigg:** OpenPLC Runtime v4.2.1,
  `ghcr.io/autonomy-logic/openplc-runtime@sha256:40726c99…bc1435`, containern
  `vcassist-openplc-v4` (REST `https://127.0.0.1:18443`, OPC UA
  `opc.tcp://172.17.0.2:4840/openplc/opcua`). STruC++ 0.6.6 (npm-paketet),
  node v22.22.0, asyncua 1.1.8. PLC-uppgift `T#20ms`, OPC UA-plugin 10 ms.
  Den andra runtimen på maskinen (`vcassist-openplc-m108`, 14841/18444) hör
  till M-108/M-125 och rördes inte.
**Facit:** bankens spårfacit (människoskrivet före körningen — laglig källa 4 i
  `85_bankkontraktet.md` §2) dömt genom OpenPLC Runtime v4.2.1 (laglig
  källa 1)
**Prövar:** `bank/domare_openplc.py`
**Rådata:** `docs/matningar/radata/m146_kor1.json` (14 texter, före fyndet i
  §4 c) och `docs/matningar/radata/m146_kor2.json` (samma 14, efter). Varje
  rad bär båda domarnas utfall, bristkoder och den uppmätta offsetfördelningen.

## Frågan

`docs/spec/85_bankkontraktet.md` §2 förbjuder att ett facit kommer ur koden som
döms. `bank/domare.py` dömer bankens spårfacit genom **vår egen ST-tolk**, så
tolken är både den som prövas och den som dömer. `M-110` skrev det rakt ut:
*"Domen kommer ur vår ST-tolk, inte ur OpenPLC."* Så länge det står så är varje
tillförlitlighetstal projektet har mätt av det som prövas.

A2 är att bygga den andra domaren: samma domarmekanik, annan motor under.

## 1. Vad som kör

`bank/domare_openplc.py` (938 rader) dömer en ST-lösning genom att kompilera
den med STruC++, ladda upp den till OpenPLC, starta PLC:n, köra bankens
stimuli över OPC UA i realtid och döma samma `facit_spar` som `domare.py`.
`Dom`, `Brist`, `Domsfel` och `forgrindsbrist` **importeras** ur `domare.py`
och dupliceras aldrig.

Kostnad, mätt: **29 s för P-05** (3 sekvenser, 6,5 s spår), **45 s för L-01**
(5 sekvenser, 9,4 s spår), **60 s för P-07** (7 sekvenser, 10,8 s spår). Det
mesta är inte spåret utan bygget och omstarten mellan sekvenserna: en omstart
per sekvens, för att `domare.py` bygger en ny Tolk per sekvens och de två
domarna annars hade dömt olika storheter (sekvenser var för sig mot sekvenser
i följd).

## 2. Trasig fixtur — skriven och sedd röd FÖRE mekanismen

Kravet: en lösning **vår tolk godkänner** och **OpenPLC vägrar kompilera** ska
bli RÖD, inte grön och inte ett körningsfel maskerat som ett underkännande.

Fyra kandidater prövades genom hela kedjan innan grinden kopplades in. Alla
fyra texterna är P-05:s referens med ett tillägg, och alla fyra är GRÖNA hos
`bank/domare.py`:

| Kandidat | vår tolk | STruC++ frontend | OpenPLC (g++) | start |
|---|---|---|---|---|
| referensen orörd (kontroll) | GRÖN | OK | SUCCESS | RUNNING |
| `template : BOOL` (C++-nyckelord som IEC-identifierare) | GRÖN | OK | SUCCESS | RUNNING |
| `operator : INT` (C++-nyckelord som IEC-identifierare) | GRÖN | OK | SUCCESS | RUNNING |
| **dubblerad CASE-etikett** | **GRÖN** | **OK** | **FAILED, exit 1** | — |

Kompilatorns egna ord, ordagrant ur runtimens bygglogg:

```
[ERROR] core/generated/generated.cpp:190:13: error: duplicate case value
[ERROR] make: *** [scripts/Makefile.strucpp:178: build/generated.o] Error 1
```

**Bifynd:** `template` och `operator` som IEC-identifierare bygger utan
anmärkning. STruC++ manglar alltså variabelnamn på vägen till C++. Det var en
kandidat vi trodde skulle falla och som inte gjorde det; den står här för att
en förkastad hypotes är billigare att skriva ned än att pröva om.

Fixturen är RÖD hos den nya domaren med rätt kod och kompilatorns egna ord:

```
P-05: UNDERKAND, 1 brister
  openplc:kompilerar_inte
      OpenPLC vägrade kompilera lösningen (FAILED, exit 1). Kompilatorns egna ord:
      [ERROR] core/generated/generated.cpp:190:13: error: duplicate case value
```

Två enklare varianter av fixturen förkastades samma dag för att de ändrade
**beteendet** och inte bara kompilerbarheten — då hade fixturen mätt fel
storhet. Bara etikettraden med tom kropp gjorde P-05, L-01, P-07 och T-01
röda på punktkrav (vår tolk tar första träffen, och en tom gren före den
riktiga slukade den); etikettraden plus en enda rad ur nästa gren kapade ett
`IF` mitt i och gav tolkfel. Den variant som står kvar kopierar **hela** den
första CASE-grenen in före den sista etiketten och är mätt grön i vår tolk på
åtta uppgifter (P-05, L-01, P-07, T-01, A-05, T-05, L-06, L-07).

## 3. Referenserna är gröna i båda domarna

Tre uppgifter med `facit_spar` vars referens `domare.py` godkänner, valda på
kortast realtid i spåret:

| Uppgift | sekvenser | spår | `domare.py` | OpenPLC-domaren |
|---|---|---|---|---|
| P-05 | 3 | 6,5 s | GODKÄND | **GODKÄND** |
| L-01 | 5 | 9,4 s | GODKÄND | **GODKÄND** |
| P-07 | 7 | 10,8 s | GODKÄND | **GODKÄND** |

3 av 3. Ingen av dem var grön i första försöket, och skälet var domaren och
inte motorerna — se §5.

## 4. Var de två domarna är oense (14 texter, två körningar)

Referenserna plus varje uppgifts motbevis, alla dömda i **båda** domarna:
14 texter, körda två gånger genom OpenPLC-domaren (den andra efter fyndet i
punkt c). I den andra körningen är utfallet (GODKÄND/UNDERKÄND) detsamma i
**14 av 14** och bristkoderna identiska i **12 av 14**.

**a) P-05 `startar_pa_ogiltigt_tool_id` — vår tolk fäller en flank till.**
Stabilt i båda körningarna. Vår tolk lägger `flank:antal_starter` (2 RISE
väntade) ovanpå de sju koder båda ger; OpenPLC-domaren räknar det väntade
antalet flanker. Motbeviset fälls på sin namngivna brist i båda domarna. Vår
tolks extra flankdom är kandidat till en **falsk rödgrind** av `M-96`:s sort
— men den är inte utredd här, och står som öppen.

**b) L-01 `vakuumet_slapps_pa_hojd` — samma text, två olika svar från samma
domare.** I körning 1 fällde OpenPLC-domaren
`invariant:vakuumet_halls_tills_kollit_star_an` bara i sekvensen
`atta_kollin_ett_lager`; i körning 2 fällde den den i **båda** sekvenserna,
precis som vår tolk. Ingenting i domarens logik ändrades mellan körningarna
som rör invarianter.

Det är den viktigaste raden i hela mätningen, och den handlar inte om
motorerna utan om domaren: **OpenPLC-domaren är inte deterministisk vid
n = 1.** Invariantregeln fäller först efter fem scan i rad, alltså 100 ms, och
brottet i `ny_pall_nollstaller_rakningen` ligger så nära den gränsen att
realtidens jitter avgör. En uppgift som är grön i en körning av en är inte
grön — vilket är exakt vad kö A:s punkt A3 säger om formen, och nu finns
siffran som visar varför.

**c) P-07 `ridans_signal_tvingas_hog_i_koden` — ett fynd som ändrade koden.**
Motbeviset tvingar ljusridåns **ingång** hög i programmet. Vid återläsningen
ser domaren något annat än den skrev — exakt samma symptom som en kanal som
tappar värden — och gav därför först ett **Domsfel**, alltså ingen dom alls,
fast lösningen var den som var fel. Skillnaden avgörs statiskt: ligger namnet
bland lösningens egna tilldelningar (`deklarationsgrind.bruk`) är det
lösningens fel. Ny bristkod `openplc:skriver_egen_ingang`:

```
P-07: UNDERKAND, 1 brister
  openplc:skriver_egen_ingang
      ST460_LGT_CLEAR tilldelas i lösningen och skrevs över: vi satte False,
      PLC:n läste tillbaka True. En ingång ägs av bildtabellen, inte av
      programmet (I15/grind 2, dubbelskrivning).
```

Vår tolk fäller samma motbevis med tio koder, varav sju `tolkfel:*`. De två
domarna är alltså **överens om utfallet och oense om skälet** — och den nya
domarens skäl är det som gäller i en riktig PLC.

En strukturell följd, mätt över hela banken: OpenPLC-domaren kan **aldrig**
lämna en `tolkfel:*`-kod, för den kör inte vår tolk. Ett motbevis vars
`faller_pa` namnger en sådan kod kan alltså inte "fällas på rätt brist" av
den nya domaren, hur rätt den än har. Det gäller **1 av bankens 152
motbevis** (just det här), så priset är litet — men A3:s jämförelse måste
räkna det, inte tiga om det.

## 5. Toleransen mot sin egen mätning

`TOLERANS_SCAN` = 4 scan = 80 ms, härledd: 2 scan PLC-svarstid (`M-20`, ärvd
ur `domare.MARGINAL_SCAN`) + 2 scan kanalfas (`M-108`, Δ +2 konstant över 1,
50 och 200 scans horisont i nio mätningar).

Domaren mäter sin egen tolerans: för varje punktkrav lämnas hur många scan
efter `t_ms` det väntade värdet först syntes. **654 punktkrav över 14 texter,
alla vid offset 0 scan — i båda körningarna.** Toleransen behövdes alltså aldrig för punktkraven i
den här körningen. Den är inte överflödig — den bär flankfönstren och
invarianternas fem-scans-regel — men på punktkravssidan är den ren marginal,
och det talet ska stå så och inte antas.

Två domarfel hittades genom att referensen inte blev grön, och båda var
domarens och inte motorernas:

* **Insättningspausen svalde den första flanken.** Sekvensens `t=0`-stimuli
  skrevs före en insättningspaus, så PLC:n hann svara innan klockan startade.
  P-05:s referens föll på `flank:antal_starter` med 1 av 2 RISE. `t=0` skrivs
  nu i körslingans första varv, som alla andra steg.
* **`stop-plc` svarar innan omställningen är klar.** Ett `start-plc` i glappet
  svarar **BUSY**, inte OK, och domaren föll mellan sekvens 1 och 2 med ett
  Domsfel som såg ut som en trasig runtime men var vår egen kapplöpning.

## 6. Ett körningsfel blir ett Domsfel, aldrig en dom

Gränsen går inte mellan "det gick bra" och "det gick illa" utan mellan **ett
påstående om lösningen** och **ett påstående om maskinen**.

Dom (UNDERKÄND, Brist): `openplc:kompilerar_inte` (STruC++ eller OpenPLC:s
g++ kördes och sa nej om texten), `openplc:startar_inte` (EMPTY efter start,
alltså .so:n laddades aldrig), `openplc:signal_omdeklarerad`,
`openplc:skriver_egen_ingang`, plus `domare.py`:s egna koder för punktkrav,
invarianter och flanker.

Domsfel (ingen dom alls): riggen saknas (STruC++, runtime-headers, `node`),
kompilatorn gick inte att köra, OpenPLC svarar inte, uppladdningen når inte
fram, bygget står kvar i COMPILING, runtimen når inte RUNNING, OPC UA-servern
går inte att nå, kanalen faller, en sekvens svarar inte inom sitt tak,
uppgiften saknar facit eller bär en signal utan bildtabellplats.

Mätt live mot en port där ingenting lyssnar:

```
fixtur riggen_nere: DOMSFEL -> HALLER
  nådde inte OpenPLC på https://127.0.0.1:18299: [Errno 111] Connection refused
```

Skillnaden bärs i koden av `plc/paket.Kompilatorfel`, en ny underklass till
`Byggfel`. Före den var *"kompilatorn saknas"* och *"koden kompilerar inte"*
samma undantag, och en trasig rigg hade blivit en tyst underkänd lösning.

## 7. Provet som går på en ren maskin

`tests/enhet/test_bank_domare_openplc.py`: **33 prov, 0,36 s, ingen docker,
ingen STruC++, ingen PLC.** REST-lagret, bygget och körningen är attrapper;
det som prövas är domarmekaniken — kartläggningen, programbygget, gränsen
mellan Dom och Domsfel, och spårdomen. Runtimens **egna ord** ur
fixturkörningen spelas upp av attrappen, så samma sak fälls på en maskin utan
runtime.

Bankens **33 uppgifter med spårfacit går alla att mappa** till bildtabellen
(bara bool/int/real i dag). En uppgift med TIME, STRING, STRUCT, ARRAY eller
en FB-instans som signal ger Domsfel, inte en dom.

## LIMITS

* **Tre uppgifter av 33, inte hela banken.** P-05, L-01 och P-07 är valda på
  **kortast spår**, inte slumpvis och inte på utfall. De 30 andra är odömda av
  OpenPLC-domaren, och de tre är inte ett stickprov på de 33. Hela banken genom
  båda domarna är punkt A3.
* **n = 2 för OpenPLC-domaren, n = 1 för tolkdomaren.** Två körningar räcker
  för att VISA att variansen finns (§4 b) men inte för att kvantifiera den. Hur
  ofta en uppgift byter dom mellan körningar är omätt, och det är A3:s tal.
  Maskinen delades under körningarna med tre andra sessioner och operatörens
  skrivbord; jittret är alltså verkligt men inte kontrollerat.
* **Divergens (a) är rapporterad, inte utredd.** Vilken av de två domarna som
  har rätt om `flank:antal_starter` i P-05:s motbevis är inte avgjort här.
  Det kräver att flankspåret läses ut ur båda, och det är gjort först i A3.
* **Divergens (b) är visad, inte förklarad.** Att samma text fick två olika
  kodmängder ur samma domare är mätt. VAR i kedjan jittret uppstår — PLC:ns
  scan, pluginets 10 ms-synk, OPC UA-anropets längd eller vår provtagning —
  är inte mätt, och de fyra går inte att skilja åt ur den här datan.
* **Toleransens 0-offset gäller punktkrav, inte flanker.** 654 punktkrav låg
  alla på offset 0. Flankernas och invarianternas fördelning under toleransen
  är **inte** mätt, och divergens (b) visar att just där finns skillnaden.
* **Fem scan i rad är en tröskel utan egen mätning.** Invariantens regel
  (fäller först efter >TOLERANS_SCAN scan i rad) är härledd ur M-20 + M-108,
  inte mätt mot ett facit över invariantbrott av känd längd. Den kan vara för
  slapp, och divergens (b) är den första indikationen på det.
* **Ingen jämförelse med STruC++ som tredje domare.** Mätningen ställer vår
  tolk mot OpenPLC. Var matiec eller STruC++ står vid en oenighet är M-125:s
  fråga, inte den här.
* **Bara en maskin, en runtime-version, en scanperiod.** 20 ms. Vad som händer
  vid 10 eller 100 ms scan är punkt A4 och är oprövat här — och `facit_spar`
  med annan `scan_ms` avvisas med Domsfel i stället för att tolkas om.
* **`openplc:skriver_egen_ingang` vilar på en statisk analys.** Namnet räknas
  som lösningens om `deklarationsgrind.bruk` ser en tilldelning till det. En
  skrivning genom en `FUNCTION_BLOCK`-utparameter i en annan POU skulle
  klassas som kanalfel, alltså Domsfel. Fail-closed, men inte fullständigt.
* **Mätningen säger inget om vilken domare som är auktoritativ.** Den raden i
  `85_bankkontraktet.md` hör till A3 och är inte skriven här.
