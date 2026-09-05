# M-121 — DUBBELSKRIVNING och TYP fällde 7 av 26 egna referenslösningar: referensen eller grinden?

**Datum:** 2026-09-05
**Rör:** `svc/vc_assist_svc/st/validator.py`, ny `svc/vc_assist_svc/st/uteslutning.py`,
`svc/vc_assist_svc/plc/forhandsregler.py`, fem bankreferenser
**Körs om av:** `python3 tests/protocol/kor_m121_uteslutning.py`
**Låst av:** `tests/enhet/test_referenser_mot_grindkedjan.py`, `tests/enhet/test_st_semantik.py`
**Bygger på:** `da2120b` (`_sekvens` bar motsatsen till sitt fältnamn), M-79, M-96

## Talet, bekräftat

26 referenser med spårfacit genom grind 2/3. **7 fälls**: A-07, C-06, L-05, P-06,
S-07, T-09 på `DUBBELSKRIVNING`; T-04 på `TYP`. Efteråt: **0 av 26.**

## Dom per fall

Frågan var per fall: kan de två skrivningarna köras i samma scan med olika
värden? Svaret är läst ur villkoren, inte gissat.

| Fall | Utgång(ar) | Vad grinden såg | Kan båda köras? | Dom | Åtgärd |
|---|---|---|---|---|---|
| **L-05** | LFT_DOWN 83 (TRUE) / 107 (FALSE) | två villkorade block, olika värden | **Nej.** 83 kräver `xAuto` = … `SYS_AUTO` …; 107 kräver `ST260_LFT_UP` = `xHand AND …` och `xHand` = … `NOT SYS_AUTO` …. Två mellanvariabler, ett steg var. | **grinden** | grinden följer mellanvariabler |
| **S-07** | PSH_REJ 113/121 (TRUE) / 145 (FALSE) | d:o | **Nej.** 113 ligger i `ELSE` till `IF NOT xDriftsklar`, och `xDriftsklar` kräver `AIR_OK`; 145 kräver `NOT AIR_OK`. Ett steg. | **grinden** | d:o |
| **P-06** | UNCLAMP 89/128, DOR_OPEN 81/129, CYC_START 113/135 | d:o | **Nej.** Samma ingång med och utan `NOT` i de två villkoren (`SPN_RUN`, `SPN_RUN`, `CHK_CLAMPED`). Inga mellanvariabler. | **grinden** | sökvägsvillkor |
| **P-06** | CHK_CLAMP 101 (TRUE) / 132 (FALSE) | d:o | **Nej i drift, men bara för att** `CHK_UNCLAMP` sätts i steg 1 och släcks i steg 2, och 101 ligger i steg 3. Det är stegmaskinens tillstånd, inget villkor i koden. | **referensen** | omskriven: `ST450_CHK_CLAMP := xSpann AND NOT ST450_CHK_UNCLAMP` |
| **T-09** | CNV_IN 80 / 134 | d:o | **Nej.** `LFT_BOT` mot `NOT LFT_BOT`. | **grinden** | sökvägsvillkor |
| **T-09** | LFT_UP 94/122, LFT_DOWN 77·106/123 | d:o | **Nej i drift**, men `IF LFT_UP AND LFT_DOWN` läser utgångarna *efter* att sekvensen skrivit dem, och att `LFT_DOWN` är falsk i steg 2 följer av steg 0:s skrivning en eller flera scan tidigare. Tillstånd. | **referensen** | omskriven: `LFT_UP := xUpp AND NOT xNer AND NOT xGrensle`, spegelvänt för DOWN |
| **A-07** | TBL_INDEX 127/147, ARC_ON 103/153, WIR_FEED 102/154 | d:o | **Nej i drift**: `ARC_ON` sätts i steg 2 och släcks i steg 4, 127 ligger i steg 6; `GAS_ON` sätts i steg 1, 103 ligger i steg 2. Tillstånd. | **referensen** | omskriven: `ARC_ON := xBage AND GAS_ON`, `TBL_INDEX := xIndex AND NOT ARC_ON AND LGT_CLEAR` |
| **C-06** | RB_START 77 (steg1=2) / 128 (steg2=3) | d:o | **Nej i drift**: `xRobot1`/`xRobot2` gör att högst en maskin är i steg 1–5. Tillstånd. | **referensen** | omskriven: `RB_START := xDrift AND (xStart1 OR xStart2)` |
| **T-04** | `4.0 * antal`, antal INT | `[TYP/F4] REAL och INT går inte ihop i *` | — | **referensen** | `4.0 * INT_TO_REAL(antal)` i referens och fyra motbevis |

"Nej i drift" är inte samma sak som "nej". Uteslutningen finns, men bara som
en följd av att stegen råkar vara olika — precis det F7-doktrinen förbjuder
(`forhandsregler.OGATS_REGLER["F7"]`: *skriv den ömsesidiga uteslutningen som
ett villkor i koden, inte som en följd av att stegen råkar vara olika*). De
referenserna bröt mot vår egen doktrin. Grinden hade rätt att fälla dem, och de
skrevs om till den form doktrinen kräver.

M-79 kallade L-05:s fällning "äkta" med motiveringen att rad 83 skriver TRUE
och "vilket värde som når rad 107 beror på vilken gren som togs". Den läsningen
stannade vid vad grinden såg. Grenen som skriver TRUE och grenen som skriver
FALSE kan inte tas i samma scan. **M-79:s dom över L-05 var fel.**

## Vad som gjordes med grinden: sökvägsvillkor och SAT, inte en svagare regel

Regeln försvagas inte. Två villkorade skrivningar med olika värden fälls
fortfarande — **om villkoren kan vara sanna samtidigt.** Det avgörs nu:

1. Varje skrivning bär sitt **sökvägsvillkor**: konjunktionen av omgivande
   `IF/ELSIF/ELSE`- och `CASE`-villkor.
2. Två lov ur olika satser med olika värden provas parvis: är
   `villkor_A AND villkor_B` satisfierbart? Liten SAT-sökning över atomerna.
3. Atomer är variabler och jämförelser, oberoende — en **överskattning** av
   vad som kan vara sant samtidigt, och en överskattning ger fler fällningar,
   aldrig färre. Två säkra undantag: `x = 3` och `x = 4` kan inte båda vara
   sanna; `x >= y` är `NOT (x < y)`, `<>` är `NOT =`, `<=` är `NOT >`.
4. **Rena mellanvariabler substitueras**: `xAuto := uttryck;` som ovillkorad
   sats, och `IF c THEN v := TRUE; ELSE v := FALSE; END_IF;` som `v := c`.
5. **Stabilitet** gör substitutionen sund: varje atom bär sin
   utvärderingsposition, och två förekomster av samma namn är samma atom bara
   om namnet inte tilldelas mellan positionerna. Annars två oberoende atomer,
   och uteslutningen går förlorad — hellre en fällning för mycket.

Den falska gröna som stabilitetsregeln hindrar, låst som fixtur:

```
xD := NOT xLarm;
IF g THEN xLarm := TRUE; END_IF;
IF xD THEN ut := TRUE; END_IF;      (* xLarm@1 *)
IF xLarm THEN ut := FALSE; END_IF;  (* xLarm@4 - ett annat varde *)
```

Naiv substitution: `NOT xLarm AND xLarm`, uteslutet. Verkligheten: med `g`
sant skrivs `ut` två gånger i samma scan. Grinden fäller.

Domen säger nu **vilka två rader** som kan kollidera och **ett vittne**:
*"skrivs på rad 83 och rad 107, och båda kan köras i samma scan (t.ex. nar
AIR_OK ar TRUE och …)"*. Före M-121 namngavs första raden i varje block.

## Priset i falska gröna — mätt, inte gissat

**Tre mätningar, alla i repot.**

### 1. Mutationer: den gröna referensen är en mätning

Tas uteslutningen bort ska grinden bli röd igen. Låst i
`test_referenser_mot_grindkedjan.py::test_mutationen_som_tar_bort_uteslutningen_falls`.

| Referens | Mutation | Grinden |
|---|---|---|
| L-05 | `xHand` utan `NOT SYS_AUTO` | röd |
| L-05 | `LFT_UP` ur `xAuto` i stället för `xHand` | röd |
| L-05 | förreglingen på knappen direkt, inte på `LFT_UP` | röd |
| S-07 | `xDriftsklar` utan `AIR_OK` | röd |
| S-07 | förreglingen på annan ingång | röd |
| P-06 | UNCLAMP-förreglingen på `CHK_CLAMPED` i stället för `SPN_RUN` | röd (UNCLAMP och DOR_OPEN) |
| T-09 | CNV_IN-förreglingen på `PEC_OUT` i stället för `LFT_BOT` | röd |
| A-07, C-06 | tillbaka till två villkorade block | röd |
| T-04 | tillbaka till `4.0 * antal` | röd (TYP) |

En mutation föll **inte**: P-06:s CYC_START-förregling flyttad till
`DOR_CLOSED`. Rätt — `DOR_CLOSED` står också i steg 5:s villkor, så paret är
fortfarande uteslutet.

### 2. M-96-korpusen: 25 modellskrivna kroppar, 13 → 10 domar

Kropparna ur fas 9:s första modelldrivna körning (sonnet, sparade i
`kroppar_per_varv`) ligger nu i `docs/matningar/m96_korpus_*.json`. Genom den
gamla grinden: **13** `DUBBELSKRIVNING`-domar. Genom den nya: **10**.

De tre som försvann, lästa för hand:

| Kropp | Utgång | Villkoren | Var domen falsk? |
|---|---|---|---|
| H-04 v1 | GRP_OPEN 67 / 110 | `NOT ST320_GRP_CLOSED` mot `ST320_GRP_CLOSED` (ingång) | **ja** |
| H-04 v4 | GRP_OPEN 84 / 117 | samma par | **ja** |
| T-07 v1 | IDX_START 52 / 75 | `CLP_CLOSED` mot `NOT CLP_CLOSED` (ingång) | **ja** |

Alla tre var falska röda i M-96, och modellen brände varv på dem. Inga falska
gröna tillkom: varje borttagen dom har en ingång som står med och utan `NOT`.

De tio som står kvar, klassade:

| Klass | Antal | Exempel | Kommentar |
|---|---:|---|---|
| **äkta överlapp** — båda kan köras, ordningen avgör | 5 | L-05 v1: RB_START 67 (sekvens, TRUE) / 115 (`IF xLarm`, FALSE); `xLarm` sätts på 97, 102, 109 emellan. fler_hist H-04: RB_START 81 (`IF ZON_FREE`) / 84 (`IF RB_DONE`) i samma steg. | regelns mål; avsiktlig prioritet räknas också hit — formen är den grinden begär bort |
| **tillstånd** — kräver stegmaskinens invariant | 2 | H-04 v4: `IF ST310_RB_START AND ST320_RB_START` efter sekvensen | samma klass som A-07/C-06; skrivs om |
| **dataflöde inom scan** — villkorlig tilldelning eller utgång läst efter skrivning | 3 | H-04 v1: vakten sätter `xLarm := TRUE`, sekvensens `ELSE` kräver `NOT xLarm`; L-05 v3: `LFT_DOWN := FALSE` ovillkorat, sedan `IF LFT_DOWN` | beviskraft finns i koden men kräver symbolisk värdeanalys av villkorliga tilldelningar — inte byggt, se LIMITS |

### 3. Kostnaden i tid och storlek

182 kroppar (26 referenser, deras motbevis, korpusen): grind 2/3 tar **5 ms
per kropp** totalt. 96 SAT-anrop, **högst 15 atomer**, median 11 (taket 24).
CASE-grenar: **högst 1 värde** per gren över 1 144 grenar (taket 16).
Substitutionsdjup: **högst 2** (L-01, L-05; taket 8). Taken står med dessa tal
som härkomst i `uteslutning.py`.

## Varför referenserna skrevs om, och varför det inte är att mäta grinden

Invändningen togs på allvar: att skriva om facit för att grinden är trubbig är
att mäta grinden i stället för modellen. Därför gjordes det i den ordningen:

1. **Först gjordes grinden vass** — allt som går att bevisa statiskt bevisas
   nu. Tre referenser (L-05, S-07, P-06 utom CHK_CLAMP, T-09 utom lyftet)
   blev gröna av det, oförändrade.
2. **Det som blev kvar var tillstånd**, och där är regeln inte trubbig utan
   rätt: uteslutningen syns inte i koden, bara i stegmaskinens spelning. Det är
   ordagrant vad OGATS_REGLER F7 förbjuder. Referenserna höll inte den standard
   vi kräver av modellen.
3. **Formen är bättre teknik, inte en förvrängning.** En utgång med ett
   skrivställe och förreglingen i samma uttryck läses på en rad, och den
   *återhämtar sig*: i A-07:s gamla form dödar en bruten ljusridå i steg 7
   `TBL_INDEX := FALSE`, sekvensen skriver aldrig om den, och cellen står i
   steg 7 utan larm tills driftsklar faller. I T-09 gör `xGrensle` under
   resan detsamma med lyftet. Den nya formen släpper när villkoret släpper.
   Modellen själv konvergerade på formen i M-79 utan att bli tillsagd.
4. **Beteendet bevisades stå kvar**: varje omskriven referens gick igenom
   spårfacit, matiec och STruC++ innan den skrevs
   (`test_referensen_gar_ocksa_igenom_sparfacit`). Diffen är en JSON-rad per
   fil; motbevisen är orörda.

Den tredje vägen — lära modellen formen — är också tagen:
`forhandsregler.REGLER["DUBBELSKRIVNING"]` säger nu vad grinden ser (uteslutande
ingångar, `steg = 1` mot `steg = 2`, rena mellanvariabler), vad den **inte** ser
(stegmaskinens tillstånd), och ger sekvens-plus-förregling-formen ordagrant.

## T-04: kompilatorn är facit — men vilken kompilator

`4.0 * antal` med `antal : INT`.

| Facit | Svar |
|---|---|
| IEC 61131-3:2003, **2.5.1.4** *Typing, overloading, and type conversion* | *"When the type of the result of a standard function defined in 2.5.1.5 is generic, then the actual types of all input variables of the same generic type shall be of the same type as the actual type of the function value in a given invocation of the function. If necessary, the type conversion functions defined in 2.5.1.5.1 can be used to meet this requirement."* — `*` är MUL över ANY_NUM: **inte tillåtet** utan konvertering. |
| IEC 61131-3:2013 | Figur 11–12 (6.6.1, s. 67–68) inför *"Supported implicit type conversions"* som implementörsfunktion — vad som stöds är upp till implementationen. Texten är inte i repot; bara innehållsförteckningen. |
| **matiec** (OpenPLC:s kompilator, `iec2c.exe` via wine) | `T-04.st:49-49..49-59: error: Data type mismatch for '*' expression.` — **avvisar.** Med `INT_TO_REAL(antal)`: accepterar. De 26 övriga referenserna kompilerar. |
| **STruC++** 0.6.6 | accepterar — men accepterar också `b := 4.0 * i` med `b : BOOL`, `i := r`, `b := i AND b`. Enda typfel den fäller är `t := i * 2` med `t : TIME`. **STruC++ är inget typfacit.** |

Leveransmålet är OpenPLC. Grinden hade rätt; referensen rättad. Hade jag lytt
uppgiftens "pröva mot STruC++" ensamt hade svaret blivit fel.

**Fynd i förbifarten:** tre av T-04:s fem motbevis
(`inflodet_oppnar_inte_igen_vid_11`, `kvitterar_nar_grinden_oppnar`,
`raknaren_nollstalls_av_stopp`) föll i kedjan **enbart** på det delade
typfelet. Med typfelet rättat går de igenom spårfacit. Deras namngivna brister
mäts inte av T-04:s spår. Bankägarens sak; står i LIMITS.

## Vad som INTE ändrades, och varför

* **Regelns tröskel.** Två villkorade block med olika värden vars villkor kan
  överlappa fälls precis som förut, också när prioriteten är avsiktlig
  (larmblocket sist). Att släppa det hade släppt de fem äkta överlappen i
  korpusen.
* **"Samma literal"-undantaget** står kvar; SAT-provet läggs ovanpå.
* **Fixturerna `a = 1` / `a = 2`.** Tre prov använde det paret som "två
  villkorade skrivningar". De är uteslutande, och grinden släpper dem nu med
  rätt. Paren byttes till `a = 1` / `b = 2`; det uteslutande paret är låst som
  eget prov, och samma par **med** `a := 2` inuti det första blocket är låst
  som fällande (stegmaskinen som går två steg på en scan).
* **Bankens övriga 19 referenser.** Orörda; alla gröna före och efter.
* **`tests/motbevis`**: 29 röda / 26 gröna före och efter, samma mängd.

## Kodställen

| Vad | Var |
|---|---|
| formler, atomer, substitution, stabilitet, SAT | `svc/vc_assist_svc/st/uteslutning.py` |
| lov och bidrag genom `_sekvens`/`_bidrag`/`_sla_ihop_grenar`, förordning och skrivpositioner, `_forsta_konflikt` | `svc/vc_assist_svc/st/validator.py` |
| förhandsregeln | `svc/vc_assist_svc/plc/forhandsregler.py` |
| 12 fixturer (6 som föll före, 6 falska gröna som ska falla), vittnesprovet, T-04-paret | `tests/enhet/test_st_semantik.py` |
| 26 referenser gröna, sju domar, mutationer, spårfacit | `tests/enhet/test_referenser_mot_grindkedjan.py` |
| omkörning | `tests/protocol/kor_m121_uteslutning.py` |

## LIMITS

* **Villkorliga tilldelningar följs inte.** `IF g THEN xLarm := TRUE; END_IF;`
  gör inte `xLarm` till `xLarm OR g` i analysen; namnet blir en fri atom. Tre
  av korpusens tio kvarvarande domar (klassen *dataflöde inom scan*) hade
  fallit bort med en symbolisk värdeanalys av BOOL-variabler över
  satslistan. Inte byggt: kostnaden i falska gröna är då inte längre
  uppenbart noll, och den mätningen är inte gjord.
* **Tillstånd över scan följs inte, med flit.** En modellkontroll (NuSMV
  finns i scratchpaden från tidigare) kunde bevisa A-07/C-06-formen. Det är
  inte grindens jobb, och F7-doktrinen kräver att uteslutningen står i koden.
* **Ogenomskinliga atomer.** Funktionsanrop i villkor, `CASE`-grenar med
  fler än 16 värden, slingor: "vet inte", faller som förut. Inga sådana i bank
  eller korpus (max 1 CASE-värde per gren), så gränsen är omätt i praktiken.
* **Jämförelser är oberoende atomer.** `x < 25.0` och `x > 35.0` räknas som
  förenliga. Sunt (fler fällningar), men en falsk röd av den sorten är möjlig;
  ingen sådan sågs i 182 kroppar.
* **IEC 61131-3:2013:s exakta klausulnummer** för implicit konvertering är
  läst ur innehållsförteckningen (6.6.1, figur 11–12, s. 67–68), inte ur
  texten. 2003-utgåvans 2.5.1.4 är citerad ur texten.
* **T-04:s motbevis**: tre av fem mäts inte av spårfacit (se ovan). Inte
  rättat här — det är bankens spår, inte grinden.
* **Korpusen är 25 kroppar från en modell (sonnet).** Klassningen av de tio
  kvarvarande är handläst av en person. 13 → 10 är ett tal på den korpusen,
  inte en förutsägelse om nästa modell.
* **Bankens baslinjeprov** (`test_baslinje.py`, två röda) var röda före M-121
  och beror på en ocommittad L-01-ändring av en annan skrivare; inte mitt.
* Tak 3 (MAX_ATOMER 24, MAX_ETIKETTVARDEN 16, MAX_SUBSTITUTIONSDJUP 8), alla
  med uppmätt marginal: 15, 1, 2.
