# M-65 — ögat på djupet: glappet, fem domare, och vad ögat inte ser

**Datum:** 2026-09-04 · Linux 6.8 · CPython 3.13 · **utan VC** (fixturer och
syntetiska serier; M-42:s rigg för hopfogningen)
**Mätt av:** `tests/enhet/test_oga_pa_djupet.py` (talen nedan skrivs ut med
`pytest -s`), `tests/enhet/test_oga_analys.py`, `tests/enhet/test_guldgrind.py`
**Fas:** 15 (`docs/spec/70_faser.md`). Protokollet mot VC är ett utkast och är
**inte kört**: `tests/protocol/fas15_ogat_pa_djupet.md`.

Operatörens krav, ordagrant: *"programmatiskt kunna förstå vad som pågår i en
scen … detta måste bli riktigt jävla bra"*, och tidsserier över *"alla objekts
positioner"*.

## §1 Glappet, som tal

`42_ogat_utbyggt.md` (677 rader) beskriver ögat efter en utbyggnad som ingen
fas var satt att bygga. Jag räknade dess löften mot koden och proven — 30
mekaniskt prövbara löften, prövade med samma skript som tabellen nedan kom ur.

| | Löften | Uppfyllda | Saknas |
|---|---|---|---|
| före M-65 | 30 | **13** | 17 |
| efter M-65 | 30 | **19** | 11 |

"Före" är lägre än vad en avläsning av koden ger (17), för två löften var
uppfyllda till formen och fel i sak: hela scenen provtogs, men i **fel enhet**
(§2), och kollisionen byggde på en detektor som M-36 mätt till **falsk noll**
(§5). Ett löfte som är byggt på en mekanism som ljuger är inte uppfyllt.

Det som saknades och nu finns (6):

| § i 42 | Löfte | Vad M-65 gjorde |
|---|---|---|
| 1 | hela scenen i seriens enhet | `poser_alla` delar med 1000 som `pose` (§2) |
| 4 | kollision som mäter | `measureDistance`, kontakt = 0,0 (§5) |
| 6 | fasen **döms** | `plc_par` med `max_ms`, mot upplösningen (§3) |
| 12 | EYES v2 | `SEQUENCE`, `SCENE`, `LIMITS`, `PHASE`, `STARVED/BLOCKED` (§6) |
| 70 | fem domare med var sin trasiga cell | domartabell + matris (§4) |
| 70 | hopfogningens osäkerhet mätt och **buren** i serien | `plc_hopfogning_s` (§3) |

Det som fortfarande saknas (11):

| § | Löfte | Varför det står kvar |
|---|---|---|
| 1 | VC:s egen kostnad för `WorldPositionMatrix` per komponent | kräver VC — P15-3 |
| 3, 5, 9 | M-10, M-18, M-19 mätta | 35 av ögats 49 konstanter är PRELIMINÄRA; de sätts mot VC, inte mot fixturer |
| 9.2 | `G_MS2` mätt | omätt antagande; kräver VC |
| 11 | RESERVERADE-rad för tyngdkraft och detektor | inte lagd (M-33 stängde världsenheten; detektorn är avförd av M-36) |
| 11 | `formaga.YTOR` med `newCollisionDetector`, `servo.Joints`, `ComponentsArrived` | `formaga.py` väntar på robotik-mekanismen (70_faser, "Robotytorna") |
| 11 | `ogonverktyg.KRAVER_RAPPORT` bär `app.Components` | **gjort** i M-65 — räknas som uppfyllt ovan |
| 11 | `oga_harledning.py` i linterns modullista | **gjort** i M-65 — räknas som uppfyllt ovan |
| 12 | `ROBOT`-sektion | robotfynd fäller domen i klartext och ligger i `derived.robotar`; raderna är inte skrivna |
| 13 | `test_greppgrinden_och_never_gripped_ar_inte_samma_grind` grön | hålet står kvar, och nu med namn: `aldrig_gripen` tvingas av kontraktets regel 5 **och** fälls av grepp-domaren (§4) |

Två av de elva är alltså gjorda men bokförs här för att tabellen ska gå att
räkna om. Netto: **9 riktiga hål**, varav 5 kräver VC.

Banken: **55 celler** med facit (spec §13 sa 41), varav 6 nya i M-65:
`fas_utanfor_tolerans`, `fas_inom_tolerans`, `fas_inom_upplosningen`,
`fas_finare_an_upplosningen`, `kontakt`, samt fas 7-agentens
`station_gor_om_arbetet` som landade i samma arbetsträd.

## §2 Enheten i scenserien — fel med 1000

`VcScen.pose()` delade VC:s millimeter med `KANONISK_TILL_VC` på vägen in.
`VcScen.poser_alla()` gjorde det inte. Samma VC-läge, 1000 mm, läst två vägar:

| Väg | Värde i serien |
|---|---|
| som roll (`pose`) | 1,0 |
| som bakgrund (`poser_alla`) | **1000,0** |

Analysen multiplicerar med 1000 för att få millimeter. Varje bakgrundsobjekts
rörelse blev alltså **tusen gånger för stor**. Ett stillage som drev 0,5 mm
fram och tillbaka i 40 prov fick 19 500 mm väg och föll som *oombedd rörelse*.
Osynligt i varje syntetisk cell — de skriver meter direkt — och osynligt i
fas 2:s VC-körning, som bara läste roller. Det är M-33:s fälla en gång till:
en parameter som bär två storheter döljer felet i det vanliga fallet.
Provet `test_vcscen_laser_hela_komponentlistan...` hade dessutom **läst in
felet** som facit (`[3, 0, 0]`).

Lagat, och en följd som kom fram i samma prov: **brus integrerade till väg.**
`rorelseprofil` summerade varje steg, också de under `ROR_SIG_MM`. Ett objekt
som jittrar 0,5 mm åt vartannat håll i 201 prov fick 100 mm väg och räknades
som rörligt. Nu:

| Storhet | Vad den räknar |
|---|---|
| `vaglangd_mm` | bara steg **över** `ROR_SIG_MM` |
| `brus_mm` | steg under golvet, summerade för sig |
| `forflyttning_mm` | nettot, första till sista läge |

Stilla = ingen väg över golvet **och** inget netto. Jitter integrerar till
noll; en långsam drift på 0,1 mm/prov har ingen väg över golvet men 19,9 mm
netto på 200 prov, och den är en rörelse. Båda riktningarna har fixturer.

En gränsobservation: 3000,5/1000 − 3,0 är 0,5000000000001 i flyttal. En
fixtur som ligger *exakt* på `ROR_SIG_MM` avgörs av avrundningen, inte av
scenen. Fixturerna ligger därför tydligt under.

## §3 Hopfogningens osäkerhet och upplösningen

### PLC-flanken låg på provets tid

En PLC-tagg som syns hög i provet vid t = 1,00 med `plc_alder_s = 0,20` lästes
hög vid **0,80**. `plcflanker` lade flanken på 1,00. Biasen är **exakt
åldern**, upp till `PLC_FARSK_S` = 250 ms, alltid åt samma håll: PLC:n såg
senare ut än den var. Den syntetiska cellen `plc_i_fas` bar 100 ms fas med
10 ms ålder; det sanna talet är 110, och provet är omskrivet med skälet.
Flanken bär nu `t` (läsningen), `t_prov` och `alder_s`.

### Hopfogningens tak bär felet — 400 av 400 varv

M-42 mätte fördröjningen *d* (ögats stämpel mot den sanna lästiden) mot en
rigg med 5,2 ms tur och retur. VC:s brygga är 9,9 ms (M-03). Riggens pump
fick sova 10 ms per slag, och samma tal mättes om, 200 varv per rad:

| Paus | d median | d p05 | d p95 | d min/max | rtt median/max | taket i serien (median/max) | \|d\| > taket |
|---|---|---|---|---|---|---|---|
| 5 ms | −0,30 ms | −0,50 | −0,24 | −0,92 / −0,21 | 5,24 / 5,83 ms | 5,30 / 5,80 ms | **0,0 %** |
| 10 ms | −0,34 ms | −0,49 | −0,27 | −0,58 / −0,22 | 10,26 / 10,54 ms | 10,30 / 10,50 ms | **0,0 %** |

Kopplarens `rtt_tak()` (max av de 8 senaste turerna, M-42) skickas nu som
`hopfogning_s` genom `plc_in`, räknas om till simuleringssekunder i pumpen
och landar i varje rad som `plc_hopfogning_s`. Det är ett **mätt** tal per
körning, och felet låg inom det i varje varv, åt båda hållen. När serien
saknar det (äldre serier, syntetiska celler) används priorn
`HOPFOGNING_PRIOR_S = 13,45 ms` — VC:s värsta uppmätta tur och retur
(M-03) — och rapporten säger `PRIOR` i stället för `RUN`.

### Upplösningen: max(L, S+J), inte summan

En fasskillnad PLC-flank mot VC-flank har tre felkällor: provintervallet S
(VC-flanken ses i nästa prov), läsintervallet L (PLC-flanken ses i nästa
läsning) och hopfogningen J (stämpeln är konservativ upp till J). Felet är
e_prov − e_las + j, alltså inom (−L, S+J). Gränsen är **max(L, S+J)**.

Monte Carlo, 5 000 slumpade flanker per rad:

| S | L | J | max fel | max(L, S+J) | summan S+L+J | p95 |
|---|---|---|---|---|---|---|
| 50 ms | 5 ms | 3 ms | 52,4 ms | **53,0** | 58,0 | 46,5 |
| 50 ms | 89 ms | 12 ms | 85,2 ms | **89,0** | 151,0 | 61,9 |
| 20 ms | 89 ms | 12 ms | 85,7 ms | **89,0** | 121,0 | 70,0 |
| 100 ms | 50 ms | 0 | 98,4 ms | **100,0** | 150,0 | 78,1 |

Första versionen av formeln var summan. Den var också en gräns, men vid
M-39:s kopplarvarv (89 ms) sade den 151 ms där felet aldrig passerade 89.
Den nya gränsen nås till 95–98 %. En lös gräns gör varje fasdom mer
INCONCLUSIVE än den behöver vara; en för tät vore ett falskt PASS. Provet
kräver båda: aldrig överskriden, minst 90 % nådd.

L räknas ur serien själv: medianavståndet mellan distinkta lästider
(`t − plc_alder_s`). Ser ögat bara en läsning per prov är L = S — konservativt.
Med en enda läsning är L okänd, och då är upplösningen okänd och fasen
INCONCLUSIVE.

**Det talet är det viktigaste i mätningen:** mot en riktig kopplare (89 ms
varv, M-39) i 20 Hz är ögats fasupplösning **≈ 89 ms**. Ett fasfel under det
går inte att skilja från noll. En fasdom med ett krav finare än så är ett
påstående om något ögat inte kan se — och det säger nu ögat självt, som
`INCONCLUSIVE`, inte som PASS.

### Fasdomen

`plan["plc_par"] = [{"plc": "Start", "signal": "grip_out", "max_ms": 100}]`:

| Villkor | Utfall |
|---|---|
| \|dt\| ≤ max | OK |
| max < \|dt\| ≤ max + res | INCONCLUSIVE — inom ögats egen osäkerhet |
| \|dt\| > max + res | OUT_OF_TOL → **FAIL timing** |
| max < res | INCONCLUSIVE — kravet är finare än ögat, oavsett dt |

Fyra celler, samma serie, en rad i planen ändrad: `fas_utanfor_tolerans`
(510 ms mot 100, FAIL), `fas_inom_tolerans` (110 mot 300, PASS),
`fas_inom_upplosningen` (110 mot 100 med res 63, INCONCLUSIVE),
`fas_finare_an_upplosningen` (0 ms mot 20, INCONCLUSIVE). Den fjärde är den
trasiga fixturen för hela idén: utan upplösningen hade den fått PASS.

## §4 Fem domare, fem trasiga celler

`Analys.DOMARE = ("sekvens", "timing", "grepp", "kollision", "genomflode")`.
Varje domare läser bara sitt eget underlag och svarar `PASS`, `FAIL`,
`INCONCLUSIVE` eller `None` (ingen fråga ställd — aldrig ett PASS). `_dom`
rangordnar ur tabellen; tabellen ligger i `derived.domar`.

Sekvens och timing var **en** domare förut: ett steg utanför sitt fönster
räknades som uteblivet. Nu: `MISSING` (steget kom aldrig innan nästa cykel
började) är sekvensens fel; `TOO_LATE`/`TOO_EARLY` (steget kom, i rätt
ordning, vid fel tid) är timingens. `station_forsent` byter därmed domare —
domen är FAIL som förut, men av rätt skäl. `station_slapper_aldrig` visade
sig bära båda: stoppet släppte för sent **och** släppsignalen uteblev.

Matrisen (rad = trasig cell, kolumn = domare; `F` = FAIL, `·` = PASS eller
ingen fråga):

| Cell | sekvens | timing | grepp | kollision | genomflöde |
|---|---|---|---|---|---|
| `station_utan_stopp` | **F** | · | · | · | · |
| `station_forregling_bruten` | **F** | · | · | · | · |
| `station_forsent` | · | **F** | · | · | · |
| `fas_utanfor_tolerans` | · | **F** | · | · | · |
| `kort_uppehall` | · | **F** | · | · | · |
| `aldrig_gripen` | · | · | **F** | · | · |
| `glider` | · | · | **F** | · | · |
| `fel_placerad` | · | · | **F** | · | · |
| `kontakt` | · | · | · | **F** | · |
| `kollision` | · | · | · | **F** | · |
| `station_svalt` | · | · | · | · | **F** |
| `station_blockerad` | · | · | · | · | **F** |

12 celler, 12 gånger exakt en domare. Domsraden börjar med domarens namn
(`sekvens:`, `forregling:`, `timing:`, `kapplopning:`, `grepp:`,
`kollision:`, `genomflode:`) — samma ord banken redan använder i
`reason_contains`.

**Mutation.** Släcks en domare (svarar `None`) ska exakt dess celler sluta
falla i analysens egen dom, och de andra domarnas celler falla som förut.
Mätt: 5 av 5 domare bär sina egna celler. Ett undantag, uttalat:
`aldrig_gripen` fälls också av kontraktets regel 5 (`NEVER_GRIPPED
VIOLATION`) — det är spec §13:s "hål som står kvar", och matrisen döljer det
inte: cellen är märkt `TVINGADE_AV_HONESTY`, och kravet är att varje domare
har minst en cell som **bara** den bär (grepp har `glider` och
`fel_placerad`).

**Två skikt.** Sedan v2 (§6) vägrar kontraktet ett PASS bredvid `STEP
MISSING`, `STARVED EXCEEDED`, `PHASE OUT_OF_TOL` och de andra fyndorden. En
släckt domare ger då ett `Kontraktsfel` i stället för ett PASS. Det provas
för sig: domaren i ett prov, kontraktet i ett annat. Raderna är ögats egna
ord, och domsraden kan inte tiga ihjäl dem.

**Kapplöpning** (`RACE`) mättes förut men fällde ingenting — `_dom` läste
aldrig raden, och guldgrindens ordlista saknade den. Nu hör den till
timing-domaren och tvingar FAIL i kontraktet. Banken (H-90) väntade sig redan
`FAIL kapplopning: ...`.

**Ingen fråga ställd** avgörs nu över alla fem: en plan som varken deklarerar
grepp, sekvens, tidskrav, bevakat par eller genomflödeskrav får
INCONCLUSIVE. Förut räckte grepp eller sekvens; en cell med bara ett
uppehållskrav blev INCONCLUSIVE när grepp-domaren släcktes, fastän timing
hade en fråga.

## §5 Kollisionsmåttet är `measureDistance`

M-36 mätte att `vcCollisionDetector` tömmer sina nodlistor och svarar noll
träffar vid 900 mm överlapp, och att `vcNode.measureDistance` svarar exakt
rätt i millimeter — 0,0 vid nudd **och** vid överlapp. Ögats `mindist` byggde
på detektorn. Nu: `plan["mind"]`-par mäts med `measureDistance` över alla
nodpar a×b, minsta värdet vinner, och raden bär `kontakt` (d ≤ 0) och
`metod`. Detektorn finns kvar bara som ett uttalat val
(`plan["mind_metod"] = "detektor"`). M-36:s fem punkter (0, 100, 1000, 1500,
5000 mm → 0, 0, 0, 500, 4000) går genom provtagaren i
`test_minsta_avstandet_mats_med_measureDistance_i_M36s_tabell`.

Analysen härleder `COLLISION a x b t=` ur första provet med `d_mm ≤ 0` när
ingen detektorträff finns. Ett bevakat par är ett par som inte får röra
varandra — måttet skiljer inte nudd från överlapp, och det står i koden.
`nod.update()` anropas före mätningen (M-36); vad det kostar per prov är
omätt, P15-5.

## §6 EYES v2 — spec-förslag för `41_ogat_kontrakt.md`

`docs/spec/` rörs inte av den här mätningen. Grammatiken i koden är höjd till
v2 i **samma commit** som grinden och varje läsare (`oga_kontrakt.py`,
`guldgrind.py`, `bank/schema.py` via `K.SEKTIONER`, `harness/fallor.py`,
`verktyg/ogonverktyg.py`), enligt kontraktets egen versionsregel.
`41_ogat_kontrakt.md` beskriver v1 tills någon med skrivrätt skriver om den;
förslaget står här.

**Läsaren förstår v1 och v2.** v1 är en delmängd: inga rader ändrade. Men
grinden kräver `LIMITS`, så en v1-rapport är aldrig guld — det finns ingen
väg runt kravet genom att tala v1.

```
EYES v2
...
SECTION TIMING
  PHASE <tagg> -> <signal> dt=<f>ms tol=<f>ms res=<<f>ms|unknown> <OK|OUT_OF_TOL|INCONCLUSIVE>
SECTION SEQUENCE                            # skrivs bara när en sekvens deklarerats
  CYCLES judged=<i> broken=<i> late=<i> truncated=<i> req=<i>
  STEP <cykel> <signal> <RISE|FALL> <OK|MISSING|TOO_LATE|TOO_EARLY> [t=<f>s] win=<f>s..<f>s
  COUNT <cykel> <signal> n=<i> max=<i> <OK|EXCEEDED>
  INTERLOCK <a>+<b> <OK|BROKEN|INCONCLUSIVE> overlap=<f>s
SECTION THROUGHPUT
  STARVED <station> <f>s req=<f>s <OK|EXCEEDED>
  BLOCKED <station> <f>s req=<f>s <OK|EXCEEDED>
  BOTTLENECK <none|<station> <starved|blocked> <f>%>
SECTION SCENE                               # skrivs bara när scenen har objekt
  OBJECTS total=<i> moving=<i> still=<i> unread=<i>
  THINNED factor=<i> <OK|CEILING> budget=<f>ms median=<f>ms
  UNCOMMANDED <none|<objekt> dist=<f>mm t=<f>s>
  IDLE_COMMANDED <none|<signal> -> <objekt> t=<f>s>
  FLUNG <none|<objekt> <f>m/s t=<f>s>
SECTION LIMITS                              # GRINDEN KRÄVER DEN
  NOT_SIMULATED sensor_bounce
  NOT_SIMULATED actuator_dynamics
  NOT_SIMULATED fieldbus_jitter
  NOT_SIMULATED degraded_modes
  NOT_SIMULATED real_hardware
  RESOLUTION sample=<f>ms read=<<f>ms|unknown> join=<f>ms <RUN|PRIOR> phase=<<f>ms|unknown>
  EXCLUDED plc_scan <f>ms
EYES VERDICT ...
```

`STEP` skrivs bara för steg som inte var OK; `UNCOMMANDED`, `IDLE_COMMANDED`
och `FLUNG` bara när frågan ställts (en `none` för en fråga ingen ställt vore
ett påstående).

**Regel 5, utökad.** Ett PASS får inte stå bredvid: `VIOLATION`,
`NEVER_FORMED`, `SLIPPING`, `OFF_TARGET`, `DROPPED`, `SHORT`, `MISSING`,
`TOO_LATE`, `TOO_EARLY`, `EXCEEDED`, `BROKEN`, `OUT_OF_TOL`, eller
`COLLISION`/`UNCOMMANDED`/`IDLE_COMMANDED`/`FLUNG` som inte är `none`.
`CARRY INCONCLUSIVE`, `THINNED CEILING`, `PHASE INCONCLUSIVE` och
`INTERLOCK INCONCLUSIVE` tvingar bort från PASS. Skrivaren vägrar, läsaren
kastar. Mätt: ingen rapport i banken, harnessen eller proven bar ett PASS
bredvid något av orden, så inget befintligt facit rördes.

**Grinden** (`guldgrind.py`): `OBLIGATORISKA_SEKTIONER = MOTION, HONESTY,
LIMITS`; LIMITS måste bära varje namn i `K.EJ_SIMULERAT` och en
`RESOLUTION`-rad. Orden matchas som **hela ord** — `LATE` ligger inne i
`LATENCY`, och en delsträngsmatchning hade fällt varje rapport med en
latensrad. Trasig fixtur: samma rapport som ger guld, utan LIMITS → NOT GOLD;
med LIMITS men utan `fieldbus_jitter` → NOT GOLD med namnet i skälet.

**Kvar från §12 i 42:** `ROBOT`-sektionen. Robotfynd fäller domen i klartext
(`robot: ...`) och ligger i `derived.robotar`.

## §7 Vad det kostade

Sviten före: 5 434 gröna, 23 röda (alla i `tests/motbevis/` utom andra
agenters M-59/M-63/M-64-referenser i tröskellintern). Efter: **5 845 gröna,
30 röda**. Diffen är sju röda, och **ingen av dem är ögats**: tre i en ny
motbevisfil om förloppet (`test_forloppet_har_ingen_forare_motbevis`), en i
layoutmodulen (`layoutport.py` ändrad i en annan agents arbetsträd), två i
S5-spärren för ärlighetsavsnitt (25 mätningar mot taket 24 — M-65 bär sitt
avsnitt; den 25:e är en annan agents nya mätning) och tröskelskuldens tak
(85 konstanter utan härkomst mot 59, ingen i ögats moduler).
`test_ogat_honesty_motbevis::test_greppgrinden_och_never_gripped...` står kvar
röd med avsikt (§4). Ögats egna prov: **+411 gröna**, varav 52 i
`test_oga_pa_djupet.py`.

Konstanter: två nya i `oga_analys.py`, båda med härkomst på samma rad
(`HOPFOGNING_PRIOR_S` M-65 §3 / M-03, `PLC_SKAN_S` M-20). Tröskelskulden
är oförändrad på 59 för ögats del; `oga_harledning.py` står nu i linterns
modullista med noll skuld.

## Vad som INTE är mätt

* **Ingenting är kört i VC.** Allt här är fixturer, syntetiska serier och
  M-42:s rigg. VC-instansen ägs av fas 7-agenten. Vad som kräver VC står i
  `tests/protocol/fas15_ogat_pa_djupet.md` (tio punkter), och det protokollet
  är inte kört.
* **Ögat är felfinnande, aldrig bevis.** Sensorstuds, ställdonsdynamik,
  fältbussjitter, degraderade lägen och verklig hårdvara finns inte i
  simuleringen. Ett PASS säger att ögat inte såg något fel i det som
  simulerades, i den upplösning serien hade — inte att anläggningen
  fungerar. Det står nu i varje rapport, i `LIMITS`, och grinden kräver det.
* **Hopfogningens osäkerhet täcker inte PLC:ns egen skanfördröjning** (40 ms,
  M-20), som ligger före kopplarens läsning, och inte fältbussens väg mellan
  PLC och I/O. Åldern räknas från läsningen, inte från insignalens flank.
  Rapporten skriver det som `EXCLUDED plc_scan 40.0ms`.
* **Hopfogningen är mätt mot M-42:s rigg, inte mot VC:s brygga.** Riggens
  pump fick sova 10 ms per slag för att likna VC:s 9,9 ms tur och retur
  (M-03); det är en efterlikning, inte VC. Priorn 13,45 ms är M-03:s värsta
  tur och retur, inte ett mätt tak mot VC.
* **Upplösningsformeln är prövad mot slumpen, inte mot en verklig kopplare.**
  Monte Carlo antar jämnt fördelade läs- och provfaser. En kopplare som
  faslåser mot pumpen (M-03 mätte just det) ger en annan fördelning; gränsen
  håller ändå eftersom den är ett max, men tätheten kan bli lägre.
* **Läsintervallet är det ögat ser, inte kopplarens verkliga.** Läser
  kopplaren oftare än ögat provtar syns bara en läsning per prov; upplösningen
  blir då konservativ, aldrig för fin.
* **`measureDistance` under en körande simulering** är oprövat: M-36 mätte
  det i ett stillastående exec-anrop. Om `nod.update()` per prov räcker, och
  vad det kostar med 20 par, står i P15-4 och P15-5.
* **Fem domare mot VC-byggda celler** (P15-8) är oprövat. Matrisen är mätt
  på syntetiska serier.
* **`aldrig_gripen` fälls av två skikt.** Grepp-domaren och kontraktets
  NEVER_GRIPPED faller samma cell. Grepp-domaren har egna celler (`glider`,
  `fel_placerad`), men NEVER_GRIPPED har ingen cell där den är ensam.
* **35 av ögats 49 konstanter är fortfarande PRELIMINÄRA** (M-10, M-18, M-19).
  M-65 sätter inga av dem; den lägger till två med härkomst.
* **`41_ogat_kontrakt.md` beskriver v1** medan koden talar v2. Förslaget står
  i §6; dokumentet ägs inte av den här mätningen.
* **Windows.**
