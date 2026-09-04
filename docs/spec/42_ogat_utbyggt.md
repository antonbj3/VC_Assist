# Ögat, utbyggt

`40_ogat.md` säger vad som ska provtas och härledas. `41_ogat_kontrakt.md`
låser domsgrammatiken. Det här dokumentet säger vad ögat **kan i dag**, efter
utbyggnaden, vilka trösklar som ännu inte är mätta, vad som kräver en mätning i
en körande VC, och hur domsgrammatiken bör höjas till v2.

Grundregeln står fast: **ögat är den enda som fäller dom** (I1). Allt nytt här
nedan matar domen — inget av det tolkar om den.

## Filerna

| Fil | Var den kör | Vad den gör |
|---|---|---|
| `oga_provtagning.py` | py2.7 **inne i VC** | läser scenen, skriver serien |
| `oga_harledning.py` | py2.7 och py3 | **räkningarna**, samt scenens lagringsform |
| `oga_analys.py` | py3, i tjänsten | **policyn**: vilket tal som får fälla |
| `oga_kontrakt.py` | båda | domsgrammatiken, **oförändrad, v1** |

Arbetsdelningen mellan `oga_harledning` och `oga_analys` är avsiktlig och har
samma skäl som delningen provtagning/analys: en räkning som bara går att pröva
genom den dom den ska mata är inte prövad. Härledningarna prövas var för sig i
`tests/enhet/test_oga_harledning.py`, på konstruerade serier, utan att en dom
fälls.

Lagringsformen har **skrivare och läsare i samma fil**, precis som
domskontraktet. `koda_scen()` och `expandera()` kan inte drifta isär utan att
`test_delta_lagringen_ger_tillbaka_exakt_det_som_skrevs` ser det.

---

## 1. Hela scenen provtas

`parts` och `tools` i planen är från och med nu en **rolltilldelning** — vilka
objekt som ska tolkas som detalj och verktyg i greppanalysen — inte ett filter
för vad som läses. Varje komponent i `app.Components` får sin pose i varje
prov. Ett objekt som ingen tänkte på finns ändå i serien när man i efterhand
frågar varför något gick fel.

Rollerna ligger kvar i `parts`/`tools` och **utesluts** ur `scene`. Hade de
legat i båda hade samma objekt burit två serier, och en skillnad mellan dem
hade varit omöjlig att tolka.

### Lagringen

`scene` är delta-lagrad: bara det som ändrats sedan förra raden skrivs, och var
femtionde avläsning skrivs en full rad (`scenfull: true`) så en avbruten fil
ändå går att läsa. Poser kvantiseras till `SCEN_DECIMALER = 6` innan de jämförs,
så "oförändrad" är ett exakt villkor och inte ett ungefär.

**Mätt** (utan VC, `test_kostnaden_vaxer_med_antalet_komponenter`, samt en
separat körning): 300 komponenter, 200 rader, 3 rörliga objekt ger

| Form | Tecken |
|---|---|
| delta-lagrad | 128 765 |
| tät | 3 650 450 |
| **kvot** | **28,3×** |

### Läst, oläst och orörd — tre lägen, inte två

Det farligaste med en gles serie är att den ser ut som stillhet. Därför bär
varje rad `scenlast`, som säger om scenen **verkligen lästes** i det provet:

* objekt saknas i deltat på en **läst** rad → det **stod still**
* raden är **oläst** → objektets läge är **okänt**

`rorelseprofil()` returnerar därför `stilla = True | False | None`, och `None`
betyder okänt. `Analys._scen_obestambar()` gör en scen där mer än
`SCEN_OLAST_MAX_ANDEL` av proven saknar avläsning till **INCONCLUSIVE**, aldrig
till PASS. Cellen `utglesad_scen` bevisar det.

### Kostnaden mäts, den antas inte

Pumpens tick har en budget på 25 ms (`pump.TICK_BUDGET_S`, satt av M-03:s
taktmätning). Ögat får `SCEN_BUDGET_MS = 5.0` av den. Provtagaren **tidtar sin
egen scenavläsning** och glesar ut scenen först när den uppmätta medianen över
`GLES_FONSTER = 8` avläsningar ligger över budgeten. Varje ändring skrivs ner
med talet som orsakade den, i `data()["scen"]["handelser"]`:

```
{"t": 1.85, "fran": 1, "till": 2, "median_ms": 15.2, "budget_ms": 5.0,
 "orsak": "OVER_BUDGET"}
```

Faktorn halveras igen först när kostnaden ligger under **halva** budgeten
(hysteres — utan den pendlar faktorn kring gränsen och serien får en takt som
varken är den ena eller den andra). Vid `GLES_TAK = 64` slutar ögat glesa och
skriver i stället en `TAK`-händelse: över det är serien inget underlag längre.

**Rollerna, lederna, de bevakade paren, signalerna, PLC-taggarna och
statistiken provtas alltid i full takt.** Bara `scene` glesas.
`test_rollerna_provtas_i_full_takt_aven_nar_scenen_glesas` håller den regeln.

**Mätt** (provtagarens egen kostnad, py3, utan VC, median av 5 × 40 prov):

| Komponenter | ms per prov |
|---|---|
| 10 | 0,024 |
| 50 | 0,107 |
| 100 | 0,213 |
| 200 | 0,417 |
| 400 | 0,891 |
| 800 | 1,828 |
| 1600 | 3,892 |

Kostnaden är linjär, ≈ 2,3 µs per komponent och prov. Med 5 ms budget räcker
det till ≈ 2 100 komponenter. **Det talet är inte hela sanningen:** det som
mäts här är provtagarens egen kostnad, inte VC:s kostnad för att läsa
`WorldPositionMatrix` på varje komponent, och den senare är sannolikt den
tyngre halvan. Den mätningen saknar ännu ett nummer, se §10.

Analyssidan är också mätt: 300 komponenter × 1 200 rader tar 1,8 s att döma.
En simulerad timme i 20 Hz (72 000 rader) skulle i samma takt ta ≈ 110 s.

---

## 2. Vad som härleds ur hela scenen

| Härledning | Svarar på | Fälls av |
|---|---|---|
| `rorliga` / `stilla` / `okanda` | vad rörde sig, vad stod still, vad vet vi inte | — |
| `rorelseprofil` | väglängd, toppfart, riktningsbyten, z-spann, rörelseintervall | — |
| `forandringar` | **när** ett objekt bytte fart, riktning eller höjd | — |
| `samtidiga` | vilka objekt rörde sig samtidigt | råvara till kapplöpning |
| `sist_i_rorelse_fore(t)` | vad rörde sig sist innan något gick fel | — |
| `narhet` | vad var nära vad, och när | — |
| `oombedd_rorelse` | rörde sig något som ingen bad om | **FAIL** |
| `orort_trots_signal` | fick något en signal utan att röra sig | **FAIL** |
| `ledtider` | cykeltid **per produkt** | — |
| `utslungad` | slungades detaljen iväg | **FAIL** |
| `aldrig_tagen` | stod detaljen still medan verktyget jobbade | diagnos |

### `forandringar` — tre storheter, tre händelser

Fart, riktning och höjd är tre skilda saker. En sammanslagen "ändring" hade
varit ett tal som bär tre storheter, och då går det inte att svara på vilken av
dem som inträffade. Fartändringen mäts **relativt** (`FART_ANDRING_ANDEL` av
den större av de två farterna) med ett golv (`FART_GOLV_MM_S`) — en absolut
tröskel skulle bära en storhet på ett transportband och en helt annan på en
robotarm, och 35 % av nästan noll är brus.

### `narhet` är inte `MINDIST`

`MINDIST` i SAFETY är **ytavstånd** ur VC:s kollisionsdetektor. `narhet` är
avstånd mellan två objekts **origo** och säger ingenting om deras form. Två
storheter, två namn, aldrig samma rad. Narhetsräkningen kapas vid
`NARHET_MAX_PAR = 2000` par och **säger till** när den kapats.

### `oombedd_rorelse` returnerar `None`, inte `[]`, utan plan

Utan `plan["forvantat_rorliga"]` ställs frågan aldrig, och då är svaret
**ingen fråga ställd** — inte "inget fel". De två får aldrig se likadana ut.
Cellerna `oombedd_rorelse` och `oombedd_men_deklarerad` skiljer sig på **en rad
i planen**, inte i serien.

### `utslungad` mot `tappad` — den vågräta farten

Ett tapp är också fritt fall och passerar också 3 m/s på vägen ner. En
tidigare version av grinden mätte **total** fart och fällde cellen `tappad`
med orsaken "delen slungades iväg". Det som skiljer ett kast från ett tapp är
den **vågräta** rörelsemängden, ingenting annat, och det är den som mäts.
Fallkurvan mäts över flygfönstret — från det prov farten först överskrider
tröskeln till det prov den sjunker under flygfarten. En ännu tidigare version
tog den globala toppfarten som startpunkt, och eftersom en kastparabel går
fortast strax innan den tar mark hamnade fönstret **efter** kastet, där
accelerationen är noll. Den missade varje riktigt kast.

---

## 3. Robotleder

`vcServoController.Joints` per robot och tidssteg, plus `getJointTarget()` för
kommenderat värde.

| Härledning | Definition | Fälls av |
|---|---|---|
| rörelse / hastighet / acceleration | per led, ur ledvärdena över tid | — |
| `granser_nadda` | ledvärde inom `LED_GRANS_MARGINAL_DEG` från sin gräns | nej, om `over=False` |
| gräns **passerad** | ledvärde utanför `[MinValue, MaxValue]` | **FAIL** |
| `singularitet` | kinematisk urartning, se nedan | **FAIL** |
| `foljfel` | kommenderat mot uppnått, per led | **FAIL** |
| `stopp` | **vilken led som orsakade ett stopp** | nej |

### Att nå en gräns är inte att gå förbi den

Cellparet `robot_gransnara` (PASS) och `robot_ledgrans` (FAIL) håller den
skillnaden. Utan `robot_gransnara` vore gränsgrinden bara en avståndsmätning
med en fällning på slutet.

### Singularitet mäts som symptom, inte ur en robotmodell

Villkoret är: **lederna går fort medan verktyget knappt rör sig — varken i läge
eller i vridning**, i minst `SING_MIN_S`. Kravet på **vridningen** är det enda
som skiljer en singularitet från en ren omorientering kring verktygspunkten;
utan det är singularitetsgrinden bara en fartgrind med ett finare namn.
Cellparet `robot_singularitet` (FAIL) och `robot_omorientering` (PASS) är exakt
den skillnaden: samma snabba leder, olika verktygsvridning.

Utan en utpekad verktygspunkt (`plan["robot_tcp"]`) görs **ingen bedömning
alls** — härledningen svarar `obestambar`. En singularitetsdom utan verktygets
rörelse vore en gissning.

### Vilken led som orsakade ett stopp

Två orsaker, som aldrig blandas ihop:

* **`GRANS`** — en led stod på sin gräns när rörelsen upphörde. Beviset är
  ledvärdet, gränsvärdena och tidpunkten.
* **`BEGRANSANDE`** — ingen led stod på gräns; den led som slutade **sist**
  bestämde rörelsetiden. Beviset är dess sista fart och tidpunkt.

Ett stopp är **ingen defekt** — `robot_stopp_begransande` får PASS. Det
härledningen svarar på är vilken led som gjorde det.

### En ledfart utan känd enhet döms inte

`vcJoint` är antingen vridled (grader) eller skjutled (längdenhet). En fart som
inte vet sin enhet bär två storheter i ett tal. Går typen inte att läsa hamnar
leden i `enhetslosa_leder`, får `enhet: None`, och **ingen gradtröskel läggs på
den**. `MinValue` och `MaxValue` är dessutom **uttryck** i VC, inte tal; går
uttrycket inte att läsa som ett tal blir gränsen `None` och gränsgrinden tiger
för den leden. Ett gissat gränsvärde vore värre än inget.

---

## 4. Kollision och minsta avstånd på riktigt

`sim.newCollisionDetector()` fanns i API-ytan och var **aldrig anropad**. Nu
byggs en detektor per bevakat par ur planen:

```python
plan["mind"] = [{"namn": "gripper+fixtur",
                 "a": ["Robot/Finger"], "b": ["Fixtur/Vagg"],
                 "tolerans_mm": 100.0}]
```

Per prov läses `testMinimumDistance()`, `getMinimumDistanceDistance()` och
`getMinimumDistancePoint1/2()`. Vid träff läses `getHitNodeA/B` **och**
`getHitFeatureA/B` — vilken yta som träffade vilken. Ytorna ryms inte i v1:s
`COLLISION`-rad och ligger därför i `eyes.json` under
`derived.safety.kollision.feature_a/b`.

`StopOnCollision` sätts hårt till `False`: ett stopp river simuleringen och med
den pumpen (M-13), och då finns ingen som kan rapportera träffen.

Ett par utan nodlistor går inte att bygga en detektor av; det registreras i
`saknade` och paret får **ingen** `MINDIST`-rad. Ingen detektor är inget tyst
OK. Detsamma gäller om `newCollisionDetector()` kastar eller ger `None`.

**Isaac Assist saknar motsvarighet.** Här har vi ytavstånd med
kontaktpunkterna, träffande nod och träffande yta, på samma tidsaxel som
poserna och PLC-taggarna.

---

## 5. Statistik per station

`vcStatistics` per station: `ComponentsArrived`, `ComponentsDeparted`,
`ComponentsCurrent`, `State`, samt `Idle/Busy/Blocked/BreakPercentage`.

**Svält och blockering ser likadana ut i ett medelvärde:** stationen
producerar inte. Skillnaden är *varför*, och den ligger i tillståndet.

* **svält** — stationen är **ledig och tom**. Den väntar på arbete.
* **blockering** — stationen bär något den inte får lämna ifrån sig.

VC har ingen `VC_STATISTICS_STARVED`; systemtillstånden är `IDLE`, `BUSY`,
`BLOCKED`, `BREAK`, `BROKEN`, `REPAIR`, `RESERVED`, `SETUP`, `WARMUP`,
`UNKNOWN`. Svält härleds därför ur `IDLE` **och** tomhet.

`_flaskhals` pekar ut den station som står mest i vägen och **vilken av de två
orsakerna** det är.

### Ett mått utan krav är ett mått, inte en dom

Svält och blockering fäller bara mot ett **deklarerat**
`plan["genomstromning"] = {"max_svalt_s": ..., "max_blockerad_s": ...}`. Utan
krav finns inget facit att fälla mot, och då mäter ögat och tiger. Cellparet
`station_svalt` (FAIL) och `station_svalt_utan_krav` (PASS) är samma serie med
och utan krav.

---

## 6. PLC på samma tidsaxel

Det är hela poängen med ögat: när en PLC-variabel och en fysisk rörelse ligger
på samma tidsaxel blir ett tidsfel ett **läsbart fasförhållande**.

### Gränssnittet mot PLC-benet

`oga_provtagning.Plckalla` — **push, inte pull**:

```python
kalla = Plckalla()
kalla.skjut_in({"Start": True, "Klar": False}, t=sim.SimTime)   # utifrån
kalla.bryt("kopplaren gav upp efter 3 raka fel", t=sim.SimTime) # kontakten borta
```

Vägen dit går genom bryggans `plc_in` (`svc/vc_assist_svc/plc/ogonkoppling.py`).
Kopplaren skickar värdets **ålder**, inte dess tidpunkt: en varaktighet betyder
samma sak i båda processerna, en tidpunkt bara om klockorna delar epok — och
epoken överlever inte ett `sim.reset()`. Pumpen räknar om åldern till
simuleringstid med sin egen **mätta** takt (M-42; `sim.run()` går 2000 gånger
fortare än väggklockan, M-08).

En OPC UA-läsning inne i pumpens tick skulle äta av budgeten på 25 ms och kan
blockera på nätverket; då stannar både provtagningen och bryggan. Den externa
sidan (`svc/vc_assist_svc/plc/`) skjuter in sin senaste ögonblicksbild, och
provtagaren tar den som den är — **tillsammans med dess ålder**.

### Ålder är inte ett tillbehör

Varje rad bär `plc_alder_s`. Är värdet äldre än `PLC_FARSK_S` sätts
`plc_gammal`, och analysen dömer då **INCONCLUSIVE**: ett värde äldre än sitt
eget prov ligger inte på samma tidsaxel som fysiken, och då är fasförhållandet
inget mått. Ett värde utan tidsstämpel räknas alltid som gammalt.

Bortom `PLC_TYSTNAD_S` är talet inte längre ett värde utan ett minne. Då
**släpps** det: raden får `plc_avbrott` med skälet och `plc_gammal`, men inga
tal. En serie som visar inaktuella PLC-värden utan att märka dem är värre än en
som visar hål (M-42). Fyra utfall, aldrig två:

| Läge | Raden bär |
|---|---|
| färskt | `plc`, `plc_alder_s` |
| gammalt (`> PLC_FARSK_S`) | `plc`, `plc_alder_s`, `plc_gammal` |
| tyst (`> PLC_TYSTNAD_S`) | `plc_avbrott`, `plc_gammal` — **inga värden** |
| avbrutet (`bryt()`) | `plc_avbrott` med den yttre sidans egna ord |

De två sista finns för att kopplaren kan dö på två sätt. Den som lever men inte
får svar säger ifrån själv; den som dör tvärt hinner inte, och fångas av
tystnadstaket. Tystnad går inte att skilja från "inget nytt har hänt".
En tidsstämpel som ligger i **framtiden** (klockan har gått bakåt, `sim.reset()`)
klipps inte till ålder noll — det vore det färskaste värdet i hela serien.

### Formen i domstexten

PLC-taggar får prefixet `plc:` och skrivs som vanliga `EDGE`-rader. Grammatikens
`<signal>` är ett namn utan blanksteg, så prefixet ryms **utan att kontraktet
behöver ändras**. `LATENCY` och `RACE` fungerar likadant för dem.

`plan["plc_par"] = [("Start", "Robot/do_start")]` ger dessutom ett mätt
fasförhållande i `derived.timing.fas`: `dt_ms` och vem som kom först. Ingen
tröskel på fasen är deklarerad, så den **mäts och döms inte** — cellen
`plc_ur_fas` har 500 ms fasfel och får PASS.

---

## 7. Scenförståelse i ord

`Analys.berattelse()` ger en läsbar redogörelse ur tidsserien; `vad_pagar(t)`
svarar på operatörens fråga för en tidpunkt.

Redogörelsen ligger i `derived.berattelse`. Den är **aldrig domen** (I1) och
får inte innehålla orden PASS, FAIL, godkänd eller underkänd — det prövas av
`test_berattelsen_svarar_pa_vad_som_pagar_utan_att_falla_en_dom`. Grinden läser
domsraden, inte redogörelsen.

Den säger bland annat: hur många objekt som rörde sig och hur många som stod
still; vilka som **aldrig lästes av**; väglängd, toppfart, rörelsefönster och
riktningsbyten per rörligt objekt; mest samtidiga par; närmaste par och när;
när greppet bildades; per station in/ut/svält/blockering; flaskhalsen med
orsak; per robot lederna, stoppens orsak, nådda gränser och urartningar;
PLC-fasen; oombedd rörelse; don som fick en signal utan verkan; och om ögat
glesade ut provtagningen och med vilken faktor.

---

## 8. Domens rangordning

Ordningen är en rangordning. En osäkerhet får **aldrig** bli ett PASS.

1. `HONESTY`-överträdelse → **FAIL** (regel 5, kontraktet)
2. för få prov → INCONCLUSIVE
3. **scenen obestämbar** (utglesad eller oläst) → INCONCLUSIVE
4. **PLC-värdena inte samtidiga** → INCONCLUSIVE
5. greppet bildades aldrig → FAIL
6. kollision → FAIL
7. **oombedd rörelse** → FAIL
8. **utslungad detalj** → FAIL
9. **don som fick en signal men aldrig rörde sig** → FAIL
10. **ledgräns passerad → singularitet → följfel** → FAIL
11. **genomströmningskravet hållet inte** → FAIL
12. bärsträckan för kort → INCONCLUSIVE
13. glidning → FAIL
14. placeringen kunde inte dömas → INCONCLUSIVE
15. placeringen fel → FAIL
16. uppehållet för kort → FAIL

De nya raderna 3, 4, 7–11 ligger **efter** de gamla i samma ordning som förut
för allt de gamla cellerna rör, så fas 2:s fem celler får oförändrad dom
(`test_fas2_cellerna_far_samma_dom_genom_VC_vagen`).

---

## 9. Trösklar och deras härkomst

`tests/enhet/test_troskelharkomst.py` läser hela `ext/`, `svc/` och `bank/`,
slår upp varje `M-nn` mot `docs/matningar/` eller `RESERVERADE.md`, och kräver
**noll skuld** i de moduler som dömer. Samma linter lånas — inte skrivs om — av
`tests/enhet/test_oga_harledning.py` och tillämpas på `oga_harledning.py`, som
ännu inte står i linterns egen modullista.

Härkomsten är av **två slag**, och de blandas inte ihop:

* `PRELIMINÄR. Sätts av mätning M-nn.` — ett tal som ska **mätas**. Numret
  måste stå i `RESERVERADE.md` tills mätningen finns.
* `Beslut, motiverat i 42_ogat_utbyggt.md.` — ett tal som är **valt**. Ett tak,
  en kapning, en lagringsupplösning och en budgetandel är val, inte mätningar,
  men de ska ändå peka ut var valet gjordes. Skälet står nedan.

| Tröskel | Fil | Härkomst |
|---|---|---|
| `STILLA_TOTAL_MM`, `ROR_SIG_MM`, `SAMTIDIG_FONSTER_S`, `OOMBEDD_MM` | härledning | M-10 |
| `FART_ANDRING_ANDEL`, `FART_GOLV_MM_S`, `HOJD_ANDRING_MM` | härledning | M-10 |
| `UTSLUNGAD_MS`, `UTSLUNGAD_FLYG_MS`, `FRITT_FALL_TOL` | härledning | M-10 |
| `SCEN_OLAST_MAX_ANDEL` | analys | M-10 |
| `LED_STILLA_DEG_S`, `LED_STILLA_MM_S`, `LED_GRANS_MARGINAL_DEG`, `LED_FOLJFEL_DEG` | härledning | M-18 |
| `SING_LEDFART_DEG_S`, `SING_TCP_MM_S`, `SING_TCP_DEG_S`, `SING_MIN_S` | härledning | M-18 |
| `SVALT_MIN_S`, `BLOCKERAD_MIN_S`, `FLASKHALS_ANDEL` | härledning | M-19 |
| `PLC_FARSK_S` | provtagning | M-19 |
| `PLC_TYSTNAD_S`, `PLC_BAKAT_TOL_S` | provtagning | **MÄTT i M-42** |
| `TAKTFONSTER` | pump | **MÄTT i M-42** — simuleringstakten mäts, antas inte |
| `GENOMSTROMNING_MARGINAL_S` | analys | M-19 |
| `SCEN_DECIMALER`, `SCEN_FULL_VAR_N_RAD`, `NARHET_MAX_PAR` | härledning | beslut, §9.1 |
| `SCEN_BUDGET_MS`, `GLES_FONSTER`, `GLES_TAK`, `KOMPONENTLISTA_VAR_N_RAD` | provtagning | beslut, §9.1 |
| `VC_TILL_MM`, `KANONISK_TILL_VC` | provtagning | **MÄTT i M-33** — VC:s bas är millimeter |
| `G_MS2` | härledning | **omätt antagande, §9.2** |

M-10, M-18 och M-19 står redan i `docs/matningar/RESERVERADE.md` och deras
beskrivningar där täcker exakt det som pekar på dem härifrån. Utbyggnaden
lägger alltså **ingen** ny tröskelskuld och inget nytt dött mätningsnummer.

### 9.1 De beslutade talen, och varför de är valda så

| Tal | Värde | Skäl |
|---|---|---|
| `SCEN_DECIMALER` | 6 | kvantiseringen blir högst 0,5 µm, fem tiopotenser under `ROR_SIG_MM`. Provet `test_kvantiseringen_ligger_langt_under_varje_troskel_som_domer` räknar om det i stället för att lita på texten. |
| `SCEN_FULL_VAR_N_RAD` | 50 | vid 20 Hz: en full rad var 2,5 s. En avbruten fil förlorar då högst 2,5 s scenhistorik. |
| `NARHET_MAX_PAR` | 2000 | närhetsräkningen är O(par × rader); 2 000 par × 1 200 rader mättes till under två sekunder. Kapningen **rapporteras**, den sker aldrig tyst. |
| `SCEN_BUDGET_MS` | 5,0 | en femtedel av pumpens tick-budget på 25 ms (`pump.TICK_BUDGET_S`, satt ur M-03:s takt). Andelen är ett val; **budgeten** den delar är mätt. |
| `GLES_FONSTER` | 8 | en enda dyr avläsning är ett utslag, inte en takt. Åtta ger en median som inte styrs av ett enstaka värde. |
| `GLES_TAK` | 64 | vid 20 Hz och faktor 64 ses scenen var 3,2 s. Grövre än så är serien inget underlag, och då säger ögat det i stället för att glesa vidare. |
| `KOMPONENTLISTA_VAR_N_RAD` | 20 | vid 20 Hz: nya och borttagna komponenter syns inom en sekund. |

### 9.2 Världsenheten — MÄTT i M-33, inte längre ett antagande

`app.findUnit("mm")` har faktor **1,0**, `"m"` har 1000,0, `"cm"` 10,0 och
tum 25,4. Faktorn anger antal basenheter, alltså är **VC:s basenhet millimeter**.

Konstanten var tidigare EN, och bar då två storheter — precis den fälla som gör
att felet inte syns i det vanliga fallet: så länge både skrivning och läsning
går genom samma faktor blir domarna rätt medan varje absolut millimetertal är
fel med tusen.

Den är nu två:

| Konstant | Betydelse | Värde |
|---|---|---|
| `VC_TILL_MM` | VC:s världsenhet uttryckt i millimeter | **1,0** |
| `KANONISK_TILL_VC` | meter till VC:s världsenhet | **1000,0** |

Ögats serie räknar i **meter**, eftersom `oga_analys.py` multiplicerar med 1000
på sju ställen för att få millimeter. Provtagaren räknar därför om åt båda
hållen: `VcScen.pose()` och `_punkt()` delar med 1000 på vägen in, `satt_pose()`
multiplicerar med 1000 på vägen ut.

Korroborering utan att fråga enhetstabellen: `vcMotionPath.Speed` är 200,0 som
standard. I millimeter per sekund är det 12 m/min, en normal transportörs-
hastighet. I meter per sekund vore det 720 km/h.

Kvar som omätt: `G_MS2`. Är tyngdaccelerationen 9,81 eller 9810 i VC:s enheter?


### M-10 — ögats kalibrering mot handbyggda celler (reserverat)

Utöver det som redan står i `RESERVERADE.md` behöver M-10 nu också sätta:

1. `STILLA_TOTAL_MM` och `ROR_SIG_MM` ur en **stillastående** scen: hur mycket
   driver en orörd komponents `WorldPositionMatrix` av sig själv under en
   körning? Under den siffran är "rörelse" brus.
2. `OOMBEDD_MM` — hur mycket får ett objekt röra sig innan det är en händelse.
3. `SAMTIDIG_FONSTER_S` mot pumpens verkliga jitter (M-03: tyst regim 17,2 Hz,
   aktiv 224,7 Hz — samtidighetsfönstret får inte vara kortare än jittret).
4. `UTSLUNGAD_MS`, `UTSLUNGAD_FLYG_MS` och `FRITT_FALL_TOL` mot en riggad cell
   där en detalj verkligen kastas.
5. `SCEN_OLAST_MAX_ANDEL` — hur gles en serie får vara och ändå bära en dom.

### M-18 — robotledernas provtagning (reserverat)

1. Att `vcServoController.Joints` går att läsa varje pumpvarv utan att kosta
   för mycket.
2. Vad `vcJoint.MinValue`/`MaxValue` innehåller i en riktig robot — tal eller
   uttryck? Om uttryck: finns en väg att evaluera dem? I dag blir gränsen
   `None` och gränsgrinden tiger för den leden.
3. Vad `Dof.JointServoType` returnerar, **ordagrant**, för en vridled och en
   skjutled. `_ledtyp()` matchar i dag på strängformen (`ROT`, `TRANS`,
   `PRISM`) och ger `None` när den inte känner igen sig.
4. Ledfart och ledacceleration vid en känd rörelse, så `LED_STILLA_*`,
   `SING_LEDFART_DEG_S` och `SING_TCP_*` sätts mot verkliga tal.
5. En riggad singularitet i en riktig robot: håller symptomkriteriet, och
   fäller det inte en vanlig omorientering?

### M-19 — stationsstatistik och PLC-fas (reserverat)

1. Att `vcStatistics` går att **läsa** på en station. M-15 mätte att beteendet
   går att *skapa*; att `State`, `ComponentsArrived` och percentagen går att
   läsa är inte prövat.
2. Vilka `State`-värden som faktiskt förekommer, ordagrant. Härledningen
   jämför i dag mot `"IDLE"` och `"BLOCKED"` efter `str().upper()`.
3. `SVALT_MIN_S` och `BLOCKERAD_MIN_S` mot en verklig cell med känd
   genomströmning.
4. Fördröjningen mellan OPC UA-klientens läsning och simuleringstiden, så
   `PLC_FARSK_S` sätts mot ett mätt tal i stället för mot en fjärdedels sekund.
   M-42 mätte hopfogningens egen del av den (median −0,23 ms, spridning
   ±3,4 ms) mot attrapper. Det är ett **golv** för talet, inte talet: PLC:ns
   egen skanfördröjning (40 ms, M-20) ligger före stämpeln, och VC:s brygga är
   långsammare än riggens (9,9 mot 5,2 ms, M-03).

### Ett fjärde paket utan nummer — världsenheten och kollisionsdetektorn

1. **Vilken längdenhet** `vcMatrix.P` och `getMinimumDistanceDistance()`
   levererar. Sätt en komponent på ett känt avstånd och läs tillbaka. (§9.2)
2. VC:s tyngdacceleration i samma enhet.
3. Att `sim.newCollisionDetector()` går att anropa **utan att stoppa
   simuleringen**. M-13 säger uttryckligen att listan över dödande operationer
   inte är härledd ur någon princip utan växer av mätning — den här är oprövad,
   och den körs i pumpens tick.
4. Vad `NodeListA`/`NodeListB` faktiskt accepterar: en lista `vcNode`, ett
   `vcNodeList` (`VC_NODELIST` ur M-15), eller något annat.
5. Att `getHitFeatureA/B` ger något med ett `Name`.
6. VC:s **egen** kostnad för `comp.WorldPositionMatrix` per komponent, svept
   över 10–800 komponenter, och om `sim.update()` per prov (M-11) dominerar
   den. Provtagarens egen kostnad är mätt i §1; VC:s är inte, och den är
   sannolikt den tyngre halvan.

---

## 11. Ändringar utanför skrivstaketet som utbyggnaden behöver

Följande ligger utanför den här uppgiftens skrivstaket och är **inte gjorda**:

| Fil | Vad som behövs | Varför |
|---|---|---|
| `docs/matningar/RESERVERADE.md` | en rad för **världsenheten, tyngdkraften och kollisionsdetektorn** (nästa lediga nummer) | `LANGDENHET_TILL_MM` och `G_MS2` pekar i dag på det här dokumentet, vilket lintern godtar, men de är omätta antaganden och hör hemma bland de reserverade numren |
| `ext/vc_addon/vc_assist/formaga.py` | ytorna `sim.newCollisionDetector`, `sim.update`, `servo.Joints`, `stat.ComponentsArrived` i `YTOR` | 36_versioner.md: förmåga provas, version antas aldrig. Utan ytan i rapporten kan tjänsten inte slå av det som saknas, och en detektor som inte finns faller med `AttributeError` långt senare i stället för att slås av i förväg |
| `svc/vc_assist_svc/verktyg/ogonverktyg.py` | `KRAVER_RAPPORT` bör växa med `app.Components` | ögat provtar nu genom den ytan i varje prov |
| `tests/enhet/test_troskelharkomst.py` | `oga_harledning.py` in i modullistan i `test_ogats_och_bryggans_trosklar_bar_alla_harkomst` | tills dess körs samma linter, lånad, från `test_oga_harledning.py` |

---

## 12. Förslag: höj domsgrammatiken till **EYES v2**

Grammatiken är låst till v1 och har **inte** ändrats. Regel 3 i kontraktet
säger att en okänd `SECTION` ignoreras men att en okänd **rad** inuti en känd
sektion är ett fel — och `oga_kontrakt.SEKTIONER` är sluten, så en ny sektion
kan inte heller skrivas. De nya härledningarna når därför domen på två sätt
i dag:

1. de **fäller domen** med sin orsak i klartext på `EYES VERDICT`-raden, och
2. de ligger fullständigt i `eyes.json` under `derived`.

Det räcker för att inget ska gå förlorat, men det gör grindens läsning av ett
robotfel till en textsökning i domsorsaken. Det bör den inte behöva vara.

### Föreslagen v2

`EYES_VERSION = 2`, `SEKTIONER` utökas med `SCENE`, `ROBOT` och `PLC`, och
följande rader läggs till. Inga befintliga rader ändras, så en v1-rapport är en
giltig v2-rapport så när som på versionsraden.

```
SECTION SCENE
  OBJECTS total=<int> moving=<int> still=<int> unread=<int>
  THINNED factor=<int> <OK|CEILING> budget=<float>ms median=<float>ms
  UNCOMMANDED <none|<objekt> dist=<float>mm t=<float>s>
  IDLE_COMMANDED <none|<signal> -> <objekt> t=<float>s>
  PROXIMITY <a>+<b> <float>mm t=<float>s          # CENTRUMavstand
  LEADTIME <objekt> <float>s
  FLUNG <none|<objekt> <float>m/s t=<float>s>
SECTION ROBOT
  JOINTS <robot> n=<int> samples=<int>
  JOINT <robot> <int> unit=<deg|mm|unknown> range=<float>..<float> vmax=<float> amax=<float>
  LIMIT <robot> <int> <REACHED|EXCEEDED> value=<float> t=<float>s
  STOP <robot> <int> <LIMIT|BINDING|UNKNOWN> t=<float>s
  SINGULARITY <robot> <none|<float>s..<float>s jointrate=<float>>
  TRACKING <robot> <int> <REACHED|MISSED> err=<float> t=<float>s
SECTION PLC
  PHASE <tagg> -> <signal> <float>ms <PLC_FIRST|SIGNAL_FIRST>
  STALE <int> samples
SECTION THROUGHPUT
  STARVED <station> <float>s <float>%          # ny rad i en kand sektion
  BLOCKED <station> <float>s <float>%
  BOTTLENECK <none|<station> <starved|blocked> <float>%>
```

Regel 5 utökas: en `LIMIT ... EXCEEDED`, en `SINGULARITY` som inte är `none`,
en `UNCOMMANDED` som inte är `none` och en `FLUNG` som inte är `none` tvingar
`VERDICT FAIL`, precis som en `HONESTY`-överträdelse gör i dag.

`THINNED ... CEILING` och `STALE` med fler än noll prov tvingar
`VERDICT INCONCLUSIVE` om inget hårdare fällt först.

**Villkoret för att göra det:** grammatiken och grinden får aldrig gå isär, så
`oga_kontrakt.py` och varje läsare av den (`bank/lasare.py`,
`svc/vc_assist_svc/verktyg/ogonverktyg.py`, `svc/vc_assist_svc/guldgrind.py`)
höjs i **samma commit**, och `41_ogat_kontrakt.md` skrivs om till v2 med
v1 kvar som historik.

---

## 13. Cellerna

`tests/celler.py` har **41** celler, alla med facit:

* **20 fälls**, var och en av sin egen orsak
* **18 får PASS** — den andra riktningen för varje ny grind
* **3 blir INCONCLUSIVE** — fail-closed på för få prov, en utglesad scen och
  osamtidiga PLC-värden

`test_varje_cell_har_ett_facit` gör det omöjligt att lägga till en cell utan
att säga vad den ska ge (83_scenarier.md, regel 1).

### Båda riktningarna, par för par

| Grind | Fälls av | Fälls INTE av |
|---|---|---|
| oombedd rörelse | `oombedd_rorelse` | `oombedd_men_deklarerad` |
| scenen obestämbar | `utglesad_scen` | `bakgrund_stilla` |
| don utan verkan | `orort_trots_signal` | `band_ror_sig` |
| ledgräns | `robot_ledgrans` | `robot_gransnara` |
| singularitet | `robot_singularitet` | `robot_omorientering` |
| kommenderat/uppnått | `robot_foljfel` | `robot_foljer` |
| stoppets orsak | — (ingen dom) | `robot_stopp_begransande` |
| svält | `station_svalt` | `station_svalt_utan_krav` |
| blockering | `station_blockerad` | `station_upptagen` |
| PLC-ålder | `plc_gammal` | `plc_i_fas`, `plc_ur_fas` |
| minsta avstånd | `kollision_med_feature` | `mindist_nara` |
| utslungad | `utslungad` | `tappad` (är ett tapp, inte ett kast) |
| aldrig tagen | `aldrig_gripen` | `rord_men_aldrig_gripen` |
| delta-lagringen | — | `scen_deltalagrad` = `bakgrund_stilla` |
| placeringstoleransen | `utan_placeringstolerans` | `pa_placeringsgransen` |
| bärsträckans tröskel | — | `pa_barstrackans_grans` |

### Fyra mätta hål som stängdes

`tests/motbevis/test_ogat_honesty_motbevis.py` mätte med mutation att fyra av
ögats grindar kunde stängas av utan att ett enda prov föll. Utbyggnaden stänger
fyra av dem, och alla fyra genom **cellerna**, inte genom att mildra provet:

1. **BLOWUP kunde stängas av.** `explosion` hamnade också 94 000 mm fel, så
   cellen föll på placeringen och `BLOWUP VIOLATION`-raden skrevs ändå ut.
   Cellens mål ligger nu **där delen hamnar**, så farten är dess enda fel.
2. **Placeringsgränsen hade inget facit.** `>` och `>=` gav samma dom i hela
   banken. `pa_placeringsgransen` ligger exakt på toleransen — toleransen
   räknas ur seriens eget slutläge med samma räkning som analysen använder, så
   likheten är exakt och inte "nästan".
3. **Bärsträckans tröskel hade inget facit.** `pa_barstrackans_grans` har
   greppet vid t = 0,00 och släppet vid t = 0,50; båda tiderna är exakta i
   flyttal, så skillnaden är exakt `CARRY_MIN_SPAN_S`.
4. **`PLACE_TOL_MM` prövades av ingen.** Varje plan skickade sin egen
   `tol_mm`, så reservvärdet kunde sättas till 2,5 meter utan att en enda dom
   rördes. `utan_placeringstolerans` utelämnar `tol_mm` och hamnar 80 mm fel.

### Det hål som står kvar

`test_greppgrinden_och_never_gripped_ar_inte_samma_grind` faller fortfarande.
`aldrig_gripen` fälls både av `mh["grip"] is None` i `_dom` och av
`NEVER_GRIPPED VIOLATION` i HONESTY, samtidigt, så ingen av de två har ett prov
där den är den enda som kan fälla. Att skilja dem åt kräver att `NEVER_GRIPPED`
får en **annan** innebörd än "greppmängden var tom", och det är en ändring av en
v1-rad i HONESTY. Den hör hemma i v2-höjningen (§12), inte i en cell.

`rord_men_aldrig_gripen` gör hålet mindre utan att stänga det: den skiljer
diagnosen `aldrig_tagen` från grinden `NEVER_GRIPPED`, så de två *härledningarna*
har var sitt prov även om de två *fällningsvägarna* fortfarande samfaller.
