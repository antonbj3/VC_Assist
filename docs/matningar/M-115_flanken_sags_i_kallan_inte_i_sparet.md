# M-115 — flanken syns i källan, inte i spåret: STL, RTAMT och NuSMV mot vårt eget öga

**Datum:** 2026-09-05
**Mätt av:** en forskningsagent, på den här maskinen. Verktyg installerade och
körda i den här sessionen (se §0). Ingen kod i repot ändrad; detta är en
läsande/mätande utflykt, inte ett bygge.
**Underlag:** `docs/spec/40_ogat.md`, `41_ogat_kontrakt.md`, `82_felklasser.md`,
`docs/matningar/M-86`, `M-88`, `M-97`, `docs/research/R-01_llm_st_och_softplc.md`,
`bank/uppgifter/T-01.json` och `A-03.json` (`facit_spar`).

**Frågan:** uppfinner vi om formell körningsverifiering? **Svar, med siffra:**
delvis. STL täcker tre av våra elva felklasser rent (F6, F9, F12), en fjärde
delvis (F8, med en räkneutökning), och missar strukturellt de två klasser där
vårt eget öga redan är starkast (F11:s aggregat, F15:s flank/latch) — av ett
skäl som den här mätningen bevisar mekaniskt, inte bara citerar: F15 sitter i
**källans interna tillstånd**, inte i det observerbara I/O-spåret, och ett
spårbaserat verktyg (RTAMT/STL, vårt öga) kan per konstruktion aldrig se det.
En modellkontrollant (NuXmv/NuSMV) kan, för att den kör mot källan — men bara
om formeln är rätt formulerad, vilket visade sig vara svårare än väntat även
för en tvåvariabels leksaksmodell (§4).

`82_felklasser.md` regel 5–6 och R-01 §1.2–1.4 har redan avgjort att ingen
statisk grind får döma `F6`/`F7`, med belägg ur SemaPLC (arXiv 2608.18565) och
PLCverif (arXiv 2203.17253). Den här mätningen **relitigerar inte** det
beslutet — den kör motsvarande experiment själv, på vårt eget bankmaterial,
för att se om slutsatsen håller på egen mätning, och lägger till hur STL och
en modellkontrollant konkret hade sett ut om vi provat.

---

## §0 Verktyg installerade, med härkomst

| Verktyg | Version | Källa | Hämtat |
|---|---|---|---|
| `rtamt` | 0.3.5 | PyPI, `pip install rtamt` | 2026-09-05 |
| `antlr4-python3-runtime` | 4.7 (rtamt:s hårda pin) | PyPI | 2026-09-05 |
| NuSMV | 2.6.0 (byggd 2015-10-14) | `https://nusmv.fbk.eu/distrib/NuSMV-2.6.0-linux64.tar.gz` | 2026-09-05, HTTP 200 |

**Miljöfynd, mätt inte antaget:** maskinens systempython är 3.13. `rtamt`
0.3.5 går **inte** att importera där — `antlr4-python3-runtime==4.7` gör
`from typing.io import TextIO`, och `typing.io` är borttaget i Python ≥3.12.
Fixen (mätt): ett venv på `python3.10` (redan installerat på maskinen som
`/usr/bin/python3.10`) importerar rent. Detta är en verktygsgräns, inte en
gissning — repot bör inte anta att `pip install rtamt` fungerar i valfri
Python-miljö.

Allt nedan kör i det venv:t. Rådata och skript (session-lokala, överlever
inte en omstart, i linje med M-86:s motsvarande fotnot):
`/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/scratchpad/stl_t01_v2.py`,
`gate_correct.smv`, `gate_buggy.smv`.

---

## §1 Går F5–F15 att skriva som STL? Fyra ja, en delvis, två nej — mätt

### F6 (timing) — JA, och mätt tre olika sätt (se §2–§4)

`T-01.json`:s `facit_spar` är ordagrant en STL-bounded-response-formel klädd
i prosa: *"0,38 s efter flanken är uppehållskravet 0,40 s inte uppfyllt"*,
*"0,46 s efter flanken har uppehållet 0,40 s löpt ut och grinden ska ha
öppnat"*. Med `rise(x)` = stigande flank av `x`:

```
φ_F6 := G( rise(ST010_PEC_PART) →
             ( G[0,0.40)( ¬ST010_STP_OPEN )  ∧  F[0.40,0.90)( ST010_STP_OPEN ) ) )
```

Detta är **precis** vad RTAMT:s `always[...]`/`eventually[...]` gör. Se §2 för
körningen mot det riktiga spåret, och §3/§4 för varför den här formeln, trots
att den är rätt skriven, ändå ger fel svar på en tätare bana.

### F9 (geometri/clearance) — JA, robusthet är den naturliga storheten

M-88 §1 mätte `MINDIST` kontinuerligt: 3000,0 mm → 0,0 mm i steg om 76,9 mm,
kontakt vid **exakt** det prov ytorna möttes. Det *är* en STL-robusthetssignal
utan omväg:

```
φ_F9 := G( mind(A,B) > D_min )        ρ(t) = mind(t) − D_min
```

M-88:s egen tabell ger båda sidor gratis: `station_bra`-parets 21 kuber gav
`ρ = 2000 − D_min` (konstant, robust PASS), kollisionsparet gav `ρ(2.00s) =
0 − D_min < 0` (robust FAIL, marginal exakt noll vid kontaktögonblicket). Vårt
öga räknar redan ut `mind`; det saknar bara att skriva ut `ρ` bredvid `PASS`.

### F12 (ohederlig) — JA, redan latent i 40_ogat.md:s egen prosa

`BLOWUP`, `UNDERGROUND` och `TELEPORT_TRANSFER` är redan, ordagrant, tre
avgränsade STL-formler skrivna som svensk prosa i `40_ogat.md`:

```
φ_BLOWUP      := G( v(t) ≤ V_MAX )
φ_UNDERGROUND := G( z(t) ≥ Z_GOLV )
φ_TELEPORT    := G( transfer_event(t) → dist(verktyg,del)(t) ≤ D_GRIP_MAX )
```

Detta är den enklaste klassen: ingen aggregation, inget dolt tillstånd, ett
enda villkor vid en känd instans eller över hela spåret. Kostnaden att skriva
om dessa tre som riktig STL är låg — de är redan formulerade så.

### F8 (förregling) — JA för en enda invariant, delvis för räkning

`A-03.json`:s `facit_spar.invarianter` bär en färdig STL-formel ordagrant:

```json
{"namn": "grinden_stangd_nar_station_2_inte_ar_klar", "sekvens": "*",
 "nar": {"ST260_STA_RDY": false}, "kraver": {"ST250_REL_OPEN": false}}
```

```
φ_F8 := G( ¬ST260_STA_RDY → ¬ST250_REL_OPEN )
```

Ren `G(a→b)`, textbok-STL. Men samma fil har `flanker`-invarianter som kräver
**räkning**: `"en_oppning_per_enhet"` kräver exakt **1** stigande flank av
`ST250_REL_OPEN` i fönstret 0–57000 ms; `"grinden_oppnar_om..."` kräver exakt
**2**. Vanlig STL har ingen räkneoperator — `F[0,57000](rise(x))` säger "minst
en gång", aldrig "exakt en gång". Att uttrycka `antal == N` kräver antingen en
hjälpräknare utanför formeln (exakt det jag byggde i §4:s `since_open`) eller
en räkneutökning av STL (t.ex. frysta variabler/count-STL, inte i RTAMT 0.3.5).
**Delvis ja**: villkoret går att uttrycka, men inte i ren STL utan
förbehandling.

### F11 (genomflöde) — NEJ för aggregatet, JA för den avgränsade delen

`STARVED`/`BLOCKED` med ett tak (`max_svalt_s`, se M-88 §4) är en vanlig
"stays"-formel: `G( idle → G[0,max_svalt_s]( idle ) )` — det håller. Men
`genomströmning`, `medel`/`min`/`max` per station (M-86:s `stat`-fält) är ett
**medelvärde över hela körningen**, inte ett fönstrat villkor. Plain STL har
ingen aggregationsoperator (inget `average`, inget `sum`); det kräver antingen
efterbehandling utanför formeln (vilket `oga_harledning.py` redan gör) eller
en STL-utökning (t.ex. "Frequency STL"/genomsnittsoperatorer, inte i RTAMT
0.3.5, inte undersökt djupare här). **Nej** för huvudtalet, av en strukturell
anledning, inte en implementationslucka.

### F15 (flank/latch) — NEJ, bevisat mekaniskt i §2–§4, inte antaget

Se §2 (RTAMT ser det inte på bankens eget spår), §3 (ens en smartare formel
ser det inte), §4 (NuSMV ser det, men bara för att den har källan). Det här
är huvudfyndet i mätningen och får ett eget avsnitt nedan.

---

## §2 RTAMT mot ett riktigt spår ur banken — vad som faktiskt hände

`T-01.json` → `facit_spar.sekvenser[0]` (`en_burk_en_oppning`): en burk bryter
`ST010_PEC_PART` 400–600 ms, grinden ska hålla stängd till 780 ms och vara
öppen senast 860 ms (facitets egna kontrollpunkter, `scan_ms=20`).

Jag byggde **två** styrningar i Python, båda återgivna av **facit_spar** vid
de fem kontrollpunkterna (alla `OK` mot båda):

* **korrekt**: en flanklast tillståndsmaskin `WAIT→ARM→OPEN→WAIT`. En flank
  accepteras bara från `WAIT`; `ARM`/`OPEN` har ingen gren som lyssnar på en
  ny flank (busy-spärren är inbyggd i själva övergångsrelationen).
* **F15-bugg**: villkoret läses om **varje scan** från den senaste flanken
  (`sist_flank_t := t vid varje stigande flank, oavsett läge`; `grind :=
  0.40 ≤ (t−sist_flank_t) < 0.90`) — den exakta ordalydelsen i
  `82_felklasser.md`: *"villkoret läses på nivå i stället för på flank"*.

**Fynd 1.** På T-01:s egna, riktiga bankspår är de **byte-för-byte
identiska** (`gate_correct == gate_buggy` → `True`, 91 av 91 prov). RTAMT
(φ_F6 från §1, `always[0:19](gate<0.5) and eventually[20:44](gate>0.5)`)
ger **samma robusthet för båda: ρ(0) = 0,5, HÅLLER.** En bank med en burk per
spår kan strukturellt inte skilja korrekt kod från denna F15-klass, oavsett
hur bra STL-formeln är skriven. Det är ordagrant vad `T-01.json`:s egen
`orsak`-text redan säger ("så länge bandet är tomt ser det ut rätt") — nu
bevisat på det faktiska spårfacitet, inte bara påstått.

**Fynd 2, verktygsfel i RTAMT 0.3.5 (mätt, inte gissat).** Med
`set_sampling_period(dt, 'ms', tol)` ger **varje** intervallbunden operator
(`eventually[a:b]` med `a>0`) **-inf på varje tidpunkt**, tyst, utan fel —
oavsett det numeriska värdet på `dt`. Isolerat: samma formel, samma data,
`set_sampling_period(1, 's', tol)` med tidsaxeln som råa heltalsindex (0,1,2,…)
i stället för millisekunder ger rätt svar. Enhetsträngen `'ms'` är alltså
trasig i den här versionen, oavsett numeriskt värde — testat med `1`, `20`,
`0.02`. En användare som (rimligt!) skriver sin sampling-period i samma enhet
som PLC:ns `scan_ms` (vilket hela vårt schema gör, `bank/schema.py`) får ett
**tyst, permanent FAIL** utan varningstext.
**Fynd 3.** Att skapa flera `StlDiscreteTimeOfflineSpecification()`-objekt i
en loop i **samma** process fick en körning att hänga (99,9 % CPU, avbruten
efter >2 min) på en kombination som fungerade felfritt fristående — sannolikt
delat/globalt AST-tillstånd mellan instanser. Åtgärdat genom att köra varje
evaluering i en egen subprocess (se skriptet). Ej djupare felsökt — utanför
den här mätningens budget, men reproducerbart.

---

## §3 En smartare formel, forcerad — och fortfarande blind

Enligt watertight-disciplinen: en formel som missar ska inte bara noteras som
"ärlig negativ", den ska forceras mot sin bästa variant. Jag byggde ett
**adversariellt spår** (inte i banken): två burkar tätt, flank 2 vid 700 ms
(300 ms efter flank 1). Där **är** `gate_correct != gate_buggy` (verifierat
elementvis).

**Naiv formel (φ_F6 rakt av) ger fel svar, åt fel håll.** RTAMT: `ρ = −0,5`
(BRYTS) för den **korrekta** styrningen — för att den, med rätta, ignorerar
flank 2 medan den är upptagen, vilket bryter en formel som naivt kräver
"stäng-sen-öppna runt VARJE flank". Samma formel ger `ρ = +0,5` (HÅLLER) för
**bugg**-styrningen, som lydigt startar en ny räkning på varje flank. **STL
och koden är omvänt rätt/fel mot varandra** på just den detalj vi ville testa.

**En smartare, avstudsad formel — fortfarande blind.** Jag byggde en
"debounced" variant: en flank räknas bara om ingen tidigare flank skett inom
900 ms (`fresh_rise := rise ∧ ¬once[1:45](rise)`, ett rent
observerbart-signal-uttryck, RTAMT:s `once`-operator). Den fixar §3:s första
problem (den korrekta styrningen HÅLLER nu, `ρ=+0,5`) — men **bugg-styrningen
HÅLLER också, `ρ=+0,5`.** Flank 2 blir vakuöst ignorerad i formeln, precis den
flank där skillnaden bor. Att göra formeln mer överseende för att sluta
straffa korrekt kod suddade samtidigt bort det enda den skulle upptäcka.

**Kvantifierat, inte bara ett stickprov.** Ett svep över mellanrummet mellan
två flankar, 20–2000 ms i steg om 20 ms (100 punkter): styrningarna
**divergerar i 35 av 100 (35 %)**, i ett sammanhängande band **220–900 ms**.
T-01:s eget spår motsvarar mellanrum = oändligt (en enda burk) — långt utanför
bandet. En enda handplockad facit-burk missar hela den divergerande zonen med
säkerhet, inte av otur.

---

## §4 NuSMV: vad ett bevis kan som ett spår inte kan — mätt på vår egen modell

Jag byggde `gate_correct.smv` och `gate_buggy.smv`: samma två styrningar som
§2–§3, men som SMV-tillståndsmaskiner med `pec` som en **fri** insignal —
NuSMV prövar **varje möjlig sekvens** av `pec` över tiden via BDD-baserad
modellkontroll, inte två handplockade spår.

**Korrekt modell, tre säkerhetsegenskaper, alla BEVISADE (oändlig
insignalrymd, inte testad, bevisad):**

```
NuSMV> G (gate -> cnt <= 24)                                          -- is true
NuSMV> G (gate_open_start -> since_open >= 44)                        -- is true
NuSMV> G ((state=ARM & 0<cnt<19 & pec & !prev_pec) -> X(cnt > 0))     -- is true
```

**Bugg-modellen, samma tre formler:**

```
NuSMV> G (gate -> timer >= 20)                                        -- is true
NuSMV> G (gate_open_start -> since_open >= 44)                        -- is true   ← ÖVERRASKNING
NuSMV> G ((0<timer<20 & pec & !prev_pec) -> X(timer > 0))             -- is FALSE
```

Två fynd, båda mätta:

1. **Mitt första försök till en "interlock"-egenskap (rad 2, mellanrum ≥44
   steg mellan två öppningar) höll för BÅDA modellerna.** Den var för trubbig
   — max uppnåeligt mellanrum i buggens egen konstruktion råkar landa exakt
   på gränsen 44, inte under den. Att formulera *rätt* egenskap för en
   flank/latch-defekt är alltså svårt även för en tvåvariabels leksak, inte
   bara en integrationsdetalj. Det är samma svårighetsgrad SemaPLC mätte i
   stort (R-01: noll avgörbara utfall på TON-uppgifter) — nu reproducerad i
   mekanismen, på egen hand, inte bara citerad.
2. **Rad 3, den kausala formeln** ("en flank mitt i en pågående räkning får
   aldrig nollställa den") **höll bevisligen för korrekt-modellen och föll
   med ett maskinfunnet motexempel för bugg-modellen** — en minimal
   tvåstegsloop (flank, ett steg, flank igen, räknaren nollställs). Det är
   exakt F15 i `82_felklasser.md`:s egna ord, nu ett NuSMV-motexempel i
   stället för ett påstående.

**Gränsen mellan prövning och bevis, konkret:** rad 3 refererar `cnt`/`timer`
— **interna** variabler som aldrig lämnar styrningen som I/O. RTAMT (och vårt
öga) ser bara `ST010_PEC_PART`/`ST010_STP_OPEN`; de kan aldrig skriva den
formeln, oavsett hur smart formeln är (§3 bevisade det empiriskt: den bästa
rent observerbara formeln jag kunde konstruera var antingen fel riktning eller
vakuös). En modellkontrollant som kör mot **källan** kan referera intern
räknartillstånd och bevisa frånvaron **för hela indatarymden, för alltid**.
Priset: den måste ha källan (eller en trogen tillståndsöversättning av den),
och — enligt R-01/CERN — PLCverif täcker i praktiken bara ~25–40 % av ST som
språk och ger noll avgörbara utfall på TON-bärande uppgifter (arXiv 2203.17253,
2608.18565, redan citerat i `82_felklasser.md` regel 5). Min egen NuSMV-modell
här är handöversatt, inte genererad av PLCverif — jag har inte installerat
PLCverif själv den här sessionen (se LIMITS). Men den bekräftar R-01:s citerade
gräns på mekanismnivå, med ett eget experiment: **även en trivial, tvåvariabel
källa krävde flera försök att formulera rätt egenskap för.** Skala det till en
riktig station med flera timers och stationsövergripande förreglingar (som
A-03:s riktiga referenskod) och svårigheten växer, inte krymper.

---

## §5 Property-based testing — redan gjort ovan, kvantifierat

§3:s svep *är* property-based testing i miniatyr: generera indata (flankarnas
mellanrum) i stället för att lita på ett enda handskrivet facit, och testa mot
banken egna deklarerade invarianter (`en_oppning_per_enhet`, se §1). Resultatet
(35 % av ett 20–2000 ms-svep divergerar, i ett samlat band) är precis den
sortens fynd `Hypothesis`/`QuickCheck`-linjen finns för: en genererad
motpart hittar en defekt som **noll** av bankens 47 fasta uppgifter skulle ha
hittat, eftersom ingen av dem har två närliggande händelser i samma spår
(mätt tidigare i R-01 §1.4: nio uppgifter bär flank/nivå-resonemang, men i
prosa/facit, inte som en genererad svepdimension).

**Vad det hade kostat att lägga till:** inte ett nytt beroende. Bankens
`facit_spar.invarianter`/`flanker` är redan deklarativa (se A-03 ovan) och
läses redan av `bank/schema.py` och `oga_harledning.py`. En generator som
perturberar **mellanrummet mellan händelser** i en uppgifts scen (inte hela
scenen) och kör om **samma redan kodade invariant-check** är en tilläggsfunktion
ovanpå befintlig kod, inte ett nytt verktyg. Kostnaden är att skriva
generatorn och välja vilka uppgifter (de F7/F8/F15-taggade, ~9 st per R-01
§1.4) som ska svepas — en avgränsad, redan identifierad delmängd.

---

## Den viktigaste raden

**Vad vi borde ha använt i stället, och vad det hade kostat:**

* **För F6/F9/F12 (avgränsad respons, avstånd, ett ögonblicksvillkor):** vi
  borde logga en **robusthetssignal** (ρ = mått − tröskel) i `eyes.json`:s
  `derived`-del, bredvid domen — inte byta ut PASS/FAIL/INCONCLUSIVE-meningen
  operatören läser, bara berika underlaget. Kostnad: låg. RTAMT själv (pip,
  gratis) behöver **inte** bli en driftberoende — dess formler är enkla nog
  att räkna om för hand i `oga_harledning.py`, vilket redan görs
  (M-97:s `max(L, S+J)` ÄR redan en handkodad bounded-response-check, samma
  form som φ_F6). Att adoptera RTAMT som bibliotek kräver att fästa Python
  ≤3.11 (§0) och känna till två mätta verktygsfel (§2) — en hanterbar men
  reell kostnad, inte gratis.
* **För F8:s enkla förreglingsinvarianter:** samma sak, låg kostnad, samma
  motivering.
* **För F5/F7/F15 (sekvens, kapplöpning, flank/latch):** **inget vi undersökt
  ersätter ögat.** STL kan inte räkna (F8:s `flanker`, F11:s medelvärden) och
  kan strukturellt inte se F15 (§2–§4, tre oberoende bevis). En
  modellkontrollant KAN se F15 — men bara med källan, bara med rätt formulerad
  egenskap (§4 visade att det inte är trivialt ens i en leksaksmodell), och
  bara inom PLCverifs mätta ~25–40 % ST-täckning. Priset för att byta till
  modellkontroll som grind vore alltså: bygga en ST→SMV-översättare (inte
  gjord här; jag översatte för hand), acceptera att den går blind på just
  TON/latch-uppgifterna (R-01), och ändå behålla ögat för allt den missar.
  Det är inte ett byte, det är ett tillägg med en smal, redan uppmätt nytta.
* **Den enskilt billigaste förbättringen, mätt här:** property-based-svep
  ovanpå redan deklarativa `facit_spar.invarianter`/`flanker` (§5). Ingen ny
  beroendekedja, en avgränsad uppgiftsmängd (~9 st), och den hittade på tio
  minuter en defektklass (F15, spacing 220–900 ms) som varken en fast
  bankuppgift, en naiv STL-formel eller en "smartare" STL-formel såg.

**Slutsats till frågan i rubriken:** nej, vi uppfinner inte om formell
körningsverifiering i stort — F5/F7/F15 (och F11:s aggregat) ligger utanför
vad STL/RTAMT och (rimligt använd) modellkontroll täcker, av strukturella skäl
mätta här, inte av att vi missat ett färdigt verktyg. Men vi har heller inte
skrivit ut robusthetssignalen för F6/F9/F12 där den är gratis, och vi har inte
utnyttjat att våra egna `facit_spar.invarianter` redan är precis deklarativa
nog för genererad indata. Båda är billiga, avgränsade förbättringar ovanpå
det som finns — inte en ombyggnad.

---

## LIMITS

* **PLCverif, S-TaLiRo, Breach, MoonLight, Arcade.PLC — inte installerade
  eller körda denna session.** PLCverif är ett fullt CERN Eclipse-RCP-verktyg;
  R-01 (DOK, `docs/research/R-01`) citerar dess mätta ST-täckning (~25–40 %,
  arXiv 2203.17253) och SemaPLC:s TON-fynd (arXiv 2608.18565), men ingen av
  siffrorna är verifierad på den här maskinen av mig. Min NuSMV-modell är en
  handöversättning av T-01:s logik, **inte** genererad av PLCverif ur riktig
  ST — den visar mekanismen (proof vs. trace), inte PLCverifs faktiska
  täckning på vår bank.
* **Endast en bankuppgift (T-01) kördes genom RTAMT.** F8:s formel (A-03) är
  skriven och motiverad ur bankens egen `facit_spar`, men inte körd genom
  RTAMT här — A-03:s `facit_spar` har inte samma enkla enstegs-tidsserie som
  T-01:s, och att bygga om den till ett körbart spår låg utanför budgeten.
* **RTAMT-fyndet i §2 (enhet `'ms'` → tyst -inf) är isolerat till versionen
  0.3.5 och till `StlDiscreteTimeOfflineSpecification`.** Online-varianten,
  dense-time-varianten och senare RTAMT-versioner är inte testade. Rotorsaken
  (parsningen av intervallgränser mot deklarerad enhet) är inte spårad i
  källkoden, bara isolerad genom uteslutning (fyra kombinationer testade).
* **Hänget i §2 fynd 3 (flera spec-objekt i samma process)** är observerat en
  gång, inte reproducerat systematiskt. Kan vara en specifik kombination av
  enheter (`'h'`/`'min'` misstänks, ej bekräftat — processen dödades efter
  2 min utan färdig uteslutning).
* **NuSMV-modellerna är en förenkling.** De fångar WAIT/ARM/OPEN-formen och
  nivå-kontra-flank-mekanismen, men inte T-01:s fulla I/O (t.ex.
  `ST010_CNV_RUN`, `ST010_STP_OPENED`) och inte A-03:s tvåstationslogik. De
  är byggda för att bevisa/motbevisa EN mekanism rent, inte för att vara en
  fullständig modell av någon bankuppgift.
* **"Bugg"-modellen är min egen, labeled-as-F15 konstruktion** (nivåläsning
  utan busy-spärr), inte en extraherad bugg ur en riktig LLM-genererad
  lösning. Den matchar `82_felklasser.md`:s definition ordagrant och T-01:s
  `orsak`-text kvalitativt, men är inte bevisat vara den vanligaste formen
  F15 tar i praktiken — det vet vi inte, eftersom R-01 §1.4 redan konstaterade
  att ingen publicerad LLM-utvärdering mäter flank/latch-fel alls.
* **Robusthet (§3) beräknad på binära 0/1-signaler ger bara ±0,5** — inget
  rikt värde. Ett verkligt robusthetsprov (kontinuerlig storhet, t.ex. F9:s
  `mind`) är inte kört genom RTAMT här, bara räknat för hand ur M-88:s redan
  publicerade tal.
* **IA-STL (RTAMT:s `Semantics.OUTPUT_ROBUSTNESS`/`INPUT_VACUITY`) kördes och
  gav rätt svar mot bibliotekets eget testfall** (`[[0,20.0],[1,inf],[2,inf],
  [3,4.0],[4,inf]]`, verifierat). Men den mäter **ansvarsfördelning mellan
  deklarerade in- och utvariabler**, inte mättidsosäkerhet. Den är **inte**
  samma sak som M-97:s `plc_hopfogning_s`-intervall, och jag hittade ingen
  färdig STL-semantik i RTAMT 0.3.5 för just den typen av osäkerhet — det
  förblir en öppen fråga, inte ett nej.
* **Property-based-sveptalet (35 %, §3/§5) gäller en enda konstgjord
  parameter** (mellanrum mellan två flankar, 20–2000 ms) **på en enda,
  handbyggd modell.** Det generaliserar inte till andra F15-mönster eller
  andra uppgifter utan ny mätning.
* **En maskin, en session.** Ingen extern replikering.
