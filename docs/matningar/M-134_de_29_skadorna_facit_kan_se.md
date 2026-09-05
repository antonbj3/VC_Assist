# M-134 — de skador facit kan se: klassning med saknat påstående och orsak

**Datum:** 2026-09-05
**Rigg:** värdmaskinen, ingen VC/modell/OpenPLC. Domaren är `bank/domare.dom`
genom vår egen ST-tolk. Data: M-131-svepet (`radata/m131_svep.json`).
**Prövar:** kö C punkt C1: för var och en av de överlevare ett bättre facit
hade fångat — vilket påstående som saknas, och varför det aldrig skrevs.

## Resultat

M-131 gav 65 kodradsöverlevare: 14 skiljer på facitstimulus, 15 syns bara
under perturbation, 36 osynliga. Kön skrevs mot "de 15"; det nya talet är
**29 åtgärdbara** (14 + 15) — 24 unika rader — plus SYS_RESET-klassen ur
nivåoperatorn. Tillväxten sedan M-122 är mätt: P-05:s nya facit (7),
tillbakafyllnadens booleska kodmutanter (12 nya överlevare) och två nya
uppgifter i nämnaren.

Metod: varje mutant återbyggd ur `skador()` och körd mot referensspåret;
första/sista divergerande scan, signal och värden noterade. Där två
förekomster delar rad valdes rätt kandidat med domaren själv: T-05 rad 32
förekomst 0 överlever (1 scans avvikelse), förekomst 1 fälls korrekt på
`takten_12_sekunder@10800ms:ST050_STA_BUSY` — domaren fungerar, facit saknar
punkten.

### Klass 1 — checkpoint-gleshet: facit ser skillnaden men har ingen punkt där

| uppgift | skada | divergens | saknat påstående |
|---|---|---|---|
| A-03 | `TID_FORDUBBLAD` rad 30 (tpAck 500→1000 ms) | ACK_RST sann 25 scan för länge (29540–30020 ms) | punktkrav `en_enhet_genom_bada_stationerna@29600ms:ST260_ACK_RST=False` |
| S-01 | `AND_TILL_OR` rad 34 (xVantarHem) | CNV_RUN falsk 17 scan (2120–2440 ms) | punktkrav `utskjutaren_star_kvar_ute@2200ms:ST190_CNV_RUN=True` |
| S-07 | `SANT_TILL_FALSKT` rad 24 (xKravOmstart) | CNV_RUN sann 20 scan (1220–1600 ms) | punktkrav `nodstopp_kraver_kvittens@1400ms:ST510_CNV_RUN=False` |
| T-05 | `AND_TILL_OR` rad 32 för. 0 | CNV_RUN 1 scan fel (t~6020 ms) | punktkrav på exakt scan — eller uttalat att sub-scan-avvikelser inte checkpointas |
| H-01 | `FALSKT_TILL_SANT` rad 35 (xDriftsklar) | HS_REQ sann 1 scan (t~13540 ms) | punktkrav på exakt scan ~13540 ms |
| P-07 | `FLANK_TILL_NIVA` rad 46 (trigReset.Q→SYS_RESET) | CNV_RUN sann 4 scan (140–200 ms) | punktkrav `stopptiden_for_kort@160ms:ST460_CNV_RUN=False` — eller hellre Klass 6-stimulus |

Orsak (gemensam): författaren sätter punkter där scenariot händer, inte där
det slutar. A-03 kontrollerar att kvittensen *kommer* (29200: sann) aldrig hur
länge den *varar*; S-01 har 1120 ms lucka (1480→2600) där 1 s-vakten hinner
löpa; S-07:s nodstopp-sekvens kontrollerar skrivarens utgångar men aldrig
transporten/omstarten den är till för (CNV_RUN helt ocheckad i hela sekvensen);
T-05/H-01 är 1-scans avvikelser som glider mellan 60 ms isär stående punkter.

### Klass 2 — nytt tunt facit: P-05 (8 rader → 3 saknade påståenden)

| rader | divergens | saknat påstående |
|---|---|---|
| 21 (T#3s→T#6s), 22 (NOT), 23 (TRUE→FALSE), 26 (AND→OR ×2), 30 (FALSE→TRUE) | TCH_BUSY falsk→sann 49 scan (3060–4020 ms) i `locked_uteblir_ger_stopp` | punktkrav `locked_uteblir_ger_stopp@3100ms:ST140_TCH_BUSY=False` |
| 38 (TRUE→FALSE) | TCH_LOCK sann→falsk scan 1 (t~20 ms) i `normal_drift_med_byte` | punktkrav `normal_drift_med_byte@20ms:ST140_TCH_LOCK=True` |
| 41 (TRUE→FALSE) | TCH_BUSY sann→falsk scan 52 (t~1040 ms) i `normal_drift_med_byte` | punktkrav `normal_drift_med_byte@1040ms:ST140_TCH_BUSY=True` |

Orsak: B:s nya facit (M-124) driver felområdet i 49 scan utan ett enda krav
efter t=100 (`t=4000` kontrollerar bara RB_START). Facit skissat tunt på
felvägarna — samråd med B i C2, det är deras fält som rör sig.

### Klass 3 — andra varvet: tillstånd bärs över sekvensgränsen

| uppgift | skada | divergens (under upprepa2) | saknad stimulus |
|---|---|---|---|
| A-03 | `AND_TILL_OR` rad 56 (båda för.) | REL_OPEN fel 1380 scan (andra passagen av `ingen_dubbelslapp`) | sekvens med två hela cykler i samma körning |
| H-04 | `OR_TILL_AND` rad 46 | RB_START fel 211 scan (andra `kvittensen_uteblir`) | andra fulla överlämningen i samma körning |
| H-05 | `SANT_TILL_FALSKT` rad 36 (xLarm) | SYS_ALARM fel 41 scan (andra `normal_overlamning`) | felet måste återkomma — larmvakten syns först andra gången |
| L-07 | `SANT_TILL_FALSKT` rad 30 (xVarvRor) | TBL_RUN fel 65 scan (andra `pulsgivaren_tappas`) | två varv i rad (nForraVarv bär tillstånd över varvet) |
| S-07 | `OR_TILL_AND` rad 44 (räknar-reset) | CNV_RUN fel 185 scan (andra `tre_underkanda`) | tredje felet i andra omgången |

Orsak: facitförfattaren tänker "en sekvens = ett förlopp" och kör varje
sekvens en gång. Låsningar, larm och räknare nollställs aldrig mellan
passager — felet kräver två fulla cykler. A-03:s sekvens innehåller redan
halvannan enhet ("en ny enhet kommer in ... innan station 2 kvitterat") men
mutanten behöver den andra *hela* cykeln.

### Klass 4 — vakten får aldrig löpa ut: P-03 (4 rader)

Raderna 30 (T#6s→T#12s), 32 (`xUttagFel`), 34 (reset-villkoret, tre
förekomster) och 38 (`xDriftsklar`, två förekomster) divergerar alla i samma
fönster: RB_CLEAR fel 70–250 scan under x2.0/hall3 i `lang_kylning_och_ett_uttag`
(BUSY utsträckt så att 6 s-vakten löper), plus 11 scan under upprepa2 i
`nodstopp_och_handlage` för rad 38.

Saknad stimulus (en för alla fyra): roboten fastnar — BUSY hög mer än 6 s så
att `tmrUttag` löper ut och `xUttagFel` sätts; därefter prövas sättning,
nollställning och driftsklarhet.

Orsak: stimulusenvelopen valdes ur normaldrift ("uttaget tar 4,2 s" i
uppgiftens scenario) och når aldrig vaktens 6 s. Ingen tänkte "kör felet" —
sju av P-03:s överlevare är samma lucka sedd ur sju vinklar.

### Klass 5 — hållen signal (2 rader; H-05/36 syns även under hall3 och avgörs i C2)

| uppgift | skada | divergens (under hall3) | saknad stimulus |
|---|---|---|---|
| S-05 | `FLANK_TILL_NIVA` rad 46 (trigSc.Q→ST200_PML_SC) | CNV_RUN fel 165 scan i `hel_produktionscykel` | håll fotocellen hög medan något händer (M-122 §3) |
| P-06 | `SANT_TILL_FALSKT` rad 30 (chuck-larmet) | CNV_RUN fel 481 scan i `en_detalj_normalcykel` | håll spindel/chuck-signalen så att larmet ska stå |

Orsak: facit trycker och släpper; nivå och flank är samma sak så länge ingen
håller signalen. Samma klass som M-122 §3 fann för hand — nu med tre rader
till. (Exakt vilken signal som ska hållas i P-06/H-05 spikas i C2.)

### Klass 6 — kort tryck på SYS_RESET (17 rader)

16 osynliga nivåmutanter (`A-07`, `A-08`, `C-06`, `H-04`, `H-05`, `L-05`,
`L-06` ×2, `L-07`, `P-06`, `S-06`, `S-07` ×2, `T-07`, `T-08`, `T-09`) plus
P-07 rad 46 som synligt specialfall (4 scans avvikelse, Klass 1).
Saknad stimulus: "håll återställningen och låt ett fel hända"-sekvens i de
16 uppgifterna (M-122 §6.3). Orsak: facit trycker kort och släpper — och att
hålla knappen längre räcker inte (M-122 §3): det måste hända något medan den
hålls.

### Gräns: 17 övriga osynliga (utanför C1/C2)

36 osynliga minus 19 nivå: 17 rader som ingen av de fem perturbationerna
skiljer från referensen (flest `AND_TILL_OR`/`SANT_TILL_FALSKT`/`NOT_STRUKEN`;
t.ex. C-04:s vakt `steg < 0 OR steg > 7` → `AND`, M-122 §2). Troligen
ekvivalenta eller döda under rimlig stimulus — mätt, inte bevisat. En
stimulus som bara fäller en sådan mutant är ett facit i förklädnad (C2:s
första fälla), så de får ingen stimulus här. Parvisa skador (C10) eller
verkliga buggar (C12) kan återkomma till dem.

## LIMITS

* **Klassningen vilar på M-131-svepets 29.** Trädet har rört sig sedan dess
  (D: M-132/M-133, E: OneDrive). En omkörning kan flytta enstaka rader mellan
  klasserna; klasserna själva är strukturella.
* **Divergensen är första avvikelsen i utgångsspåret**, inte ett bevis för
  att det saknade påståendet fångar mutanten — det prövas i C2, mutant för
  mutant, med referensen grön som villkor.
* **1-scans fallen (T-05/32 för. 0, H-01/35) kräver punktkrav på exakt scan.**
  Mekaniskt möjligt; om det är värt det avgör C2 — facits marginaldoktrin
  (MARGINAL_SCAN=2, M-20) handlar om svarslatens, inte om glitchfrånvaro,
  men punkttäthet på scannivå är spröd av andra skäl.
* **P-05:s facit är B:s (M-124) och rör sig.** Klass 2 kan vara lagad av B
  innan C2 kommer dit — då stryks raderna mot B:s commit, inte mot min åsikt.
* **"Osynlig" är inte "ekvivalent".** Inte heller för de 17: ingen har
  bevisats ekvivalent med referensen.
* **Orsakerna är författarpsykologi ur spårdata**, inte intervjuer. "Ingen
  tänkte X" betyder: inget spår i banken gör X. C-04 (den enda som håller
  återställningen: `kvitteringsknappen_star_kvar_hog`) är motexemplet som
  visar att det går.
