# M-178 — Cykeltidstaket: kod som är riktig men inte hinner, och vem i kedjan som säger till

**Datum:** 2026-09-05
**Status:** KLART (kö A, punkt A11)
**Körs av:** `tests/protocol/kor_A11_cykeltidstaket.py` (`--tolk`, `--grindar`,
  `--runtime`). Permanenta fall i `tests/enhet/test_plc_cykeltak.py`
  (10 prov, gröna).
**Rigg:** OpenPLC Runtime v4.2.1 i `vcassist-openplc-v4` (REST 18443, OPC UA
  172.17.0.2:4840), STruC++ 0.6.6, node v22.22.0, PLC-uppgift `T#20ms`,
  OPC UA-plugin 10 ms. Containern kördes utan `SCHED_FIFO`-rättigheter
  (`sched_setscheduler failed: Operation not permitted` i runtimeloggen) —
  se LIMITS. `vcassist-openplc-m108` rördes inte.
  **Ingen modell körde i den här mätningen.**
**Facit:** OpenPLC Runtime v4:s **effektiva** cykeltid, mätt ur en pulsräknare
  i PLC-programmet självt (scan per väggsekund) och jämförd med PLC-uppgiftens
  deklarerade intervall `T#20ms`. Facit ligger alltså i den motor som prövas
  för allt utom talet: talet kommer ur PLC:n, inte ur vår klocka.
**Prövar:** `svc/vc_assist_svc/st/tolk.py`, `svc/vc_assist_svc/plc/`,
  `bank/domare.py`
**Rådata:** `docs/matningar/radata/m178_runtime.json` (sex nivåer med
  runtimens egna `timing_stats`, status och loggrader), `…/m178_ut.txt`,
  `…/m178_runtimelogg.txt` (257 rader ur runtimeloggen).

## Frågan

Cykeltiden är ett **tak**. En PLC-uppgift med `INTERVAL := T#20ms` ska vara
klar inom 20 ms; tar kroppen längre tid hinner den inte, och allt som hänger på
tiden — timers, flankräkning, taktnummer, en sekvens mot en annan station —
glider. Koden är fortfarande **riktig**. Den är bara för långsam för sitt eget
tak.

Frågan är inte om det går att skriva sådan kod. Frågan är om **någon i kedjan
säger till**. Gör ingen det kan en användare få kod som är grön i bänken och
missar sin deadline i verkligheten — och det är den dyraste sortens falska
grönt, för den syns först i cellen.

## 1. Svaret i en tabell

| led i kedjan | säger till om en för långsam kropp? |
|---|---|
| vår ST-tolk | **nej, per konstruktion** (§2) |
| vår validator, deklarationsgrind, industrigrind, stationsgrind, förhandsregler | **nej** — noll träffar på ordförrådet (§3) |
| matiec / STruC++ / OpenPLC:s g++ | **nej** — en riktig loop är riktig |
| `bank/domare.py` | **nej** — spåret döms på modellklockan |
| `bank/domare_openplc.py` | **indirekt och missvisande** (§5) |
| OpenPLC Runtime v4 | **JA, på tre sätt** (§4) |
| vår klient mot den runtimen | **nej — den läste loggen fel och lämnade alltid tomt** (§6) |

Sammanfattat: **kedjan har en röst, och vi hade tystat den med en rad kod.**

## 2. Tolken kan inte säga till, och det är en egenskap och inte en bugg

`Tolk.scan()` gör `self.tid_ms += self.scan_ms`. Det finns ingen annan tidskälla
i tolken. En kropp som tar tio millisekunder och en som tar en mikrosekund ger
alltså **exakt samma spår**, alltså exakt samma dom.

Visat i stället för påstått — samma kropp, växande arbetsmängd, ett scan:

| varv i kroppen | väggtid för scanet | tolkens klocka efteråt |
|---|---|---|
| 1 | 0,019 ms | 20,0 ms |
| 400 | 0,392 ms | 20,0 ms |
| 3 600 | 3,239 ms | 20,0 ms |
| 14 400 | 13,028 ms | 20,0 ms |

Väggtiden växer 685-faldigt. Modellklockan rör sig inte en tiondels
millisekund. Det står nu som ett permanent prov
(`test_tolkens_klocka_ar_oberoende_av_arbetet`), och provet fäller om någon
ger tolken en exekveringstid utan att mäta om det här.

## 3. Ingen grind i vår kedja nämner ens exekveringstid

Textsökning efter `cycle_time|cykeltid|exekveringstid|scan_time|overrun|deadline|budget_ms|wcet`
i de tio filer som ligger mellan modellens text och en körande PLC:

| fil | träffar |
|---|---|
| `st/validator.py`, `st/tolk.py` | 0 |
| `plc/deklarationsgrind.py`, `plc/industrigrind.py`, `plc/stationsgrind.py` | 0 |
| `plc/forhandsregler.py` | 0 |
| `plc/paket.py`, `plc/openplc.py` | 0 |
| `bank/domare.py` | 0 |
| `bank/domare_openplc.py` | 3 — alla **kommentarer** om provtagningens takt, ingen mätning |

En textsökning är en **undre gräns**: en grind kan mäta tid utan att använda
något av orden. Men en undre gräns på noll räcker för slutsatsen, för det
finns ingen grind att peka på. Taket står nu som ett prov som bara får krympa
(`test_ingen_grind_i_kedjan_mater_exekveringstid`): bygger någon en
cykeltidsgrind ska raden tas bort, inte höjas.

Det betyder också att `plc/forhandsregler.py`, som matar in regler i
systemprompten **innan** modellen skriver, aldrig säger ett ord om att koden
har ett tidsbudget. Modellen får inte veta kravet.

## 4. Vad OpenPLC gör, och vad den säger

Sex arbetsnivåer, samma program med en pulsräknare som skrivs först i varje
scan. Den effektiva cykeltiden är 3000 ms väggtid delat med antalet scan
räknaren hann i det fönstret — mätt **ur PLC:n**, inte ur vår klocka.

| nivå | varv/scan | **effektiv cykel** | runtimens `scan_time_avg` | `overruns` / `scan_count` | loggrader `scan overrun` |
|---|---|---|---|---|---|
| noll | 0 | **20,0 ms** | 0,002 ms | 0 / 300 | 0 |
| 1e6 | 1 000 000 | **20,0 ms** | 2,298 ms | 0 / 501 | 0 |
| 5e6 | 5 000 000 | **20,69 ms** | 11,864 ms | 400 / 477 | 1 |
| 1e7 | 10 000 000 | **40,0 ms** | 20,931 ms | 247 / 248 | 6 |
| 2e7 | 20 000 000 | **60,0 ms** | 36,298 ms | 163 / 164 | 7 |
| 1e8 | 100 000 000 | **250,0 ms** | 77,363 ms | 38 / 39 | 10 |

Tre saker läses rakt ur tabellen.

**(a) Den effektiva cykeln är kvantiserad till hela tick.** 20, 20, 40, 60,
250 — inte 21,3 eller 37,8. OpenPLC håller uppgiften på baskickets rutnät och
hoppar över tick när kroppen inte hinner. Runtimen säger det själv, ordagrant:

```
[WARNING] [task MAIN] scan overrun #N: body exceeds its 20 ms period —
          running at reduced rate, other tasks unaffected
```

För en logik som räknar tid i **scan** i stället för i millisekunder betyder
det att allt går exakt två eller tre gånger för långsamt — och ingenting i
koden ser annorlunda ut.

**(b) Överskridandet börjar långt före taket.** Vid 5e6 varv är kroppen
11,9 ms — under 20 — och ändå räknar runtimen **400 överskridanden av 477
scan**. Marginalen äts av schemaläggningens latens, inte av kroppen. En
tumregel som *"håll dig under halva cykeltiden"* är alltså inte en
försiktighetsmarginal utan ungefär där gränsen faktiskt går på den här riggen.

**(c) Runtimens egen `scan_time_avg` följer inte den effektiva cykeln.** Vid
1e7 stämmer de (20,9 ms kropp → 2 tick → 40 ms). Vid 2e7 borde 36,3 ms ge
2 tick (40 ms) men mätningen ur PLC:n säger 3 tick (60 ms), och vid 1e8 säger
`scan_time_avg` 77 ms medan den uppmätta cykeln är 250 ms — mer än tre gånger
mer. **Talet ur programmet självt är det som gäller**; `scan_time_avg`
underskattar under tung last, och hur mycket är inte hänfört (LIMITS).

**(d) Vid extrem last dödar en vakthund programmet.** I ett tidigare varv, med
en längre körning på samma nivå (1e8), gav runtimen:

```
[ERROR] Watchdog: No heartbeat detected - PLC program is unresponsive
[ERROR] The loaded PLC program may contain an infinite loop.
        Upload a corrected program to recover.
[INFO]  PLC State: ERROR
```

Alltså: en korrekt loop som bara är för långsam klassas till slut som en
**oändlig loop**, PLC:n går till `ERROR` och programmet måste laddas om.
Diagnosen är fel — det finns ingen oändlig loop — men larmet är rätt.

## 5. Vad vår egen domare gör med samma kod, och varför det är fel klass

`bank/domare_openplc.py` märker att något är fel, men säger fel sak.

I mätningens första varv gatades arbetet av en insignal `START` som facit skrev
vid t = 0. Vid 2e7 och 1e8 varv gav domaren då **Domsfel**:

```
sekvensen pulsraknaren: kanalfel efter sekvensen: START skrevs sist True men
lästes False; skrivvägen tappade värden; sidan kördes inte
```

Domaren klassade alltså en **för långsam lösning** som en **trasig rigg**. Det
är precis fel håll på A2:s gräns: ett körningsfel får aldrig maskeras som ett
underkännande — men ett underkännande får inte heller maskeras som ett
körningsfel. Koden var lösningens; kanalen var frisk.

Och när spåret väl går igenom (nivåerna med en oskriven ingång) fälls facit på
punktkrav — `UT skulle vara X men var Y` — utan ett ord om att PLC:n körde tre
gånger för långsamt. Domen är rätt och orsaken osynlig.

Det är inte en bugg i domaren; det är en storhet den inte mäter. Åtgärden är
liten och namngiven i §6.

## 6. Fyndet som gjorde resten möjligt: `logg()` läste fel nyckel

`OpenPlcV4.logg(rader, niva)` läste `data["logs"]`. `/api/runtime-logs` svarar
`{"runtime-logs": [{"id","level","message","timestamp"}, …]}`. Metoden har
alltså **alltid** lämnat en tom sträng — också i `starta_och_vanta`:s
felmeddelande (*"Senaste loggrader:"*) och i `domare_openplc`:s Domsfel, som
båda citerar den.

Två av projektets skarpaste observationer stod i den loggen och lästes aldrig:

* `[task MAIN] terminated by signal 8 — other tasks keep running` vid
  nolldivision (M-169 §4),
* `[task MAIN] scan overrun #N: body exceeds its 20 ms period` här.

Lagat, med tio permanenta prov i `tests/enhet/test_plc_cykeltak.py` — bland dem
den trasiga fixturen: runtimens **egen** svarsform, avskriven ordagrant ur en
körning, måste ge text. Provet var rött före lagningen.

**Åtgärden som återstår** är därför en rad, inte en förmåga: läs
`klient.logg(niva="WARNING")` och `klient.statistik()["tasks"][…]["overruns"]`
efter varje körning i `domare_openplc`, och fäll på
`scan overrun` / `terminated by signal` som en **Brist** med eget namn — inte
som ett Domsfel. Då blir *"koden hinner inte"* en dom om lösningen, vilket den
är. Den koden finns inte, och en mätning är inte en grind.

## LIMITS

* **En rigg, en plattform, utan realtidsrättigheter.** Containern får inte
  `SCHED_FIFO` (`sched_setscheduler failed: Operation not permitted`,
  `mlockall failed`), så både latens och överskridandetröskel är sämre än på
  en runtime med rätt rättigheter. Talen är därför en **övre** gräns för
  jitter och inte en egenskap hos OpenPLC i allmänhet. Maskinen delades
  dessutom med fyra andra sessioner.
* **`scan_time_avg` är inte hänförd.** Att runtimens egen siffra (77 ms)
  avviker från den uppmätta effektiva cykeln (250 ms) vid tyngsta nivån är
  observerat, inte förklarat. Ett medelvärde över ett annat fönster, en annan
  definition av "scan", eller ett prov taget mitt i uppstarten är alla möjliga
  och ingen av dem är utesluten.
* **`overruns` räknar inte "kropp > period".** Vid 5e6 är kroppen 11,9 ms och
  räknaren står på 400 av 477. Vad den räknar exakt är inte avgjort; att den
  räknar **något** som börjar långt före taket är det som är mätt.
* **Sex nivåer, en körning per nivå.** Ingen `n ≥ 3`. M-153 mätte
  OpenPLC-domaren till 7 % självinstabila enheter, och de här talen har ingen
  spridningsuppskattning alls. Skillnaderna mellan nivåerna (20 → 40 → 60 →
  250 ms) är dock mycket större än den variation som setts mellan varv (20,0
  mot 20,69 på samma nivå i två körningar).
* **Två fällor i mätaren blev själva mätningen.** (i) En karta **utan**
  insignaler ger `None` på varje utgång över OPC UA i varje prov (353 av 353):
  noderna finns men bär inget värde. (ii) En mappad ingång som **ingen sats
  läser** ger `BadInternalError` vid skrivning. Båda är kringgångna
  (`A11_TICK` finns, läses av en verkningslös rad, och skrivs aldrig av facit)
  och båda är oförklarade — de är egenskaper hos OpenPLC:s OPC UA-plugin och
  inte hos den kod som mäts.
* **Vakthunden är sedd en gång.** `Watchdog: No heartbeat detected` föll i ett
  tidigare, längre varv på nivå 1e8 och inte i det redovisade svepet.
  Tröskeln — hur långsam en kropp måste vara innan den klassas som en oändlig
  loop — är **inte** mätt.
* **Ingen körning i Visual Components.** Spårfacit ligger bredvid ögondomen,
  aldrig i stället för den (invariant I1).
