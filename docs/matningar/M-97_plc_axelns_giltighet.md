# M-97 — PLC-axelns giltighet: en körning vars hopfogning inte går att lita på fälls som obestämbar

**Datum:** 2026-09-05 08:33–08:45 · Linux 6.8 · VC Premium 4.10 under Wine
11.16, **headless `:99`**, testprefixet `~/.wine-vc-test` (VC-processen funnen
genom `/proc`-scan på kommandorad **och** miljö, aldrig `pgrep -f`)
**Mätt av:** `tests/protocol/kor_fas15_plcaxeln.py` (L3, mot en körande VC),
två körningar med olika störning; `tests/enhet/test_plc_axeln.py` (L1, 23
prov, tre trasiga fixturer och ett injicerat känt fel). Rådata i körningarnas
`--json`.
**Fas:** 15 (`docs/spec/70_faser.md`): *"Hopfogningens osäkerhet mätt, inte
antagen."* M-87 mätte osäkerheten. Den här mätningen bygger grinden som
**använder** den — och prövar grinden mot ett känt svar.
**Steg 0:** VC körde repots kod i båda körningarna.

## Förebilden, och frågan

Fas 8 (M-73) mätte klockkvoten i varje körning och gjorde en körning utanför
braketten **OGILTIG** — inte fällande, inte godkänd — för facits fönster
mätte då kopplingen mellan klockorna i stället för stationen. Incidenten som
tvingade fram det: en provsvit på samma maskin tog pumpens tid och tryckte
kvoten till 0,61.

Ögats motsvarighet: PLC-värdena läggs på fysikens tidsaxel med en
**hopfogning** vars osäkerhet är ett mätt tak per rad (`plc_hopfogning_s`,
M-87). Före den här mätningen bar serien taket, `LIMITS` skrev ut det, och
`PHASE`-domen använde det (M-87 §5). Men:

* `plc_gammal` sattes på **punktskattningen** av åldern. En rad med ålder
  0,10 s och tak 1,8 s (M-87 §6 mätte sådana i en frisk körning) räknades
  som färsk — fast dess sanna ålder lika gärna kunde vara 1,9 s.
* `sekvensdom` dömde stegens tid som om PLC-flankerna låg **exakt**. Ett steg
  0,1 s för sent blev `TOO_LATE` oavsett om flankens tak var 5 ms eller 5 s.
* Ingen körningsnivå fanns: ingenting sa *den här körningens PLC-axel går
  inte att lita på*.

## §1 Tre lager, var och en med en fixtur som föll

**Raden.** `plc_otackt(rad)`: åldern ligger inom färskhetsfönstret
`PLC_FARSK_S` (0,25 s) men `ålder + tak` går över det. Den sanna åldern
ligger i `[ålder − tak, ålder + tak]`; att värdet är färskt går bara att
styrka när `ålder + tak ≤ fönstret`. M-42 skrev regeln utan att bygga den:
*"vore osäkerheten i samma storleksordning som fönstret vore plc_gammal brus
och inte ett mått."* Otäckt är disjunkt från `plc_gammal` (ålder över
fönstret på egen hand) och från PRIOR (inget mätt tak alls) — tre olika
storheter, tre olika namn.

**Flanken.** `sekvensdom` dömer varje steg mot `osäkerhet = startflankens tak
+ stegflankens tak` (två inskott, två stämplar, felen läggs ihop):

| stegets läge mot fönstret | status |
|---|---|
| fönstret smalare än osäkerheten | **INCONCLUSIVE** — "fönstret är finare än hopfogningens osäkerhet" |
| inne i fönstret | OK |
| utanför med ≤ osäkerheten | **INCONCLUSIVE** — "kom 2,6 s efter starten, fönstret är 1,5–2,5 s, men osäkerheten är 0,12 s" |
| utanför med > osäkerheten | TOO_LATE / TOO_EARLY |
| kom aldrig i cykeln | MISSING — **oberoende av taket** |

Det är exakt PHASE-regeln från M-65 (`max < res → INCONCLUSIVE`; `max < |dt|
≤ max + res → INCONCLUSIVE`), överförd till stegen. En syntetisk serie utan
tak döms som förut: osäkerheten är då noll, och LIMITS säger PRIOR.

**Körningen.** `plc_axel(rader)` räknar andelen otäckta PLC-rader, och
`_dom` gör körningen **INCONCLUSIVE** — *"PLC-axeln går inte att lita på:
hopfogningens osäkerhet täcker färskhetsfönstret i N % av PLC-proven"* — när
andelen ligger över `PLC_AXEL_MAX_ANDEL`. Under braketten diskvalificeras de
otäckta flankerna var för sig (lagret ovan) i stället för att göra hela
körningen obestämbar: M-87 §5:s *"ögat hade blivit blint av att bli ärligt"*.

Fixturerna (`test_plc_axeln.py`), alla röda mot koden före:

| prov | vad som injiceras | svar före | svar nu |
|---|---|---|---|
| `…over_braketten_ar_obestambar_inte_pass` | `station_bra`, tak = fönstret på 20 % av raderna | PASS | **INCONCLUSIVE, "PLC-axeln"** |
| `…braketten_ar_det_som_faller` | samma, braketten muterad till 100 % | — | PASS (så det är braketten som fäller) |
| `…inom_hopfogningens_osakerhet_ar_INCONCLUSIVE_inte_TOO_LATE` | `station_forsent` (0,2–0,5 s sen), tak 0,30 s per flank | FAIL timing | **INCONCLUSIVE** |
| `…fel_storre_an_osakerheten_falls_anda` | samma, tak 0,05 s | FAIL | FAIL — grinden gör inte ögat snällt |
| `…MISSING_paverkas_inte_av_taket` | `station_utan_stopp`, tak 1,0 s på flankerna | FAIL sekvens | FAIL sekvens |
| `…fonster_finare_an_osakerheten_ger_inte_OK_ens_mitt_i_fonstret` | `station_bra`, tak 1,0 s på flankerna (osäkerhet 2,0 s, fönster 0,5–1,3 s) | **PASS** | **INCONCLUSIVE** |
| `…braketten_faller_ocksa_en_cell_som_annars_hade_fallts` | `station_forsent`, tak = fönstret på alla rader | FAIL | INCONCLUSIVE — OGILTIG är inte FAIL |

### Det injicerade kända svaret

Samma serie — `station_bra` där **ett** steg kommer 0,100 s för sent (stoppet
faller vid 2,6 s, fönstret är 1,5–2,5 s) — och det enda som ändras är taket
på flankraderna:

| tak per flank | osäkerhet (2 × tak) mot felet 0,100 s | dom |
|---|---|---|
| 0,005 s | 0,010 < 0,100 | **FAIL timing** |
| 0,049 s | 0,098 < 0,100 | **FAIL timing** |
| 0,060 s | 0,120 > 0,100 | **INCONCLUSIVE timing** |

Grinden byter svar exakt där summan av de två takens passerar felet. Det är
det som skiljer en grind från ett filter: den diskriminerar på storheten den
påstår sig mäta, med känd riktning på båda sidor.

**Vad den inte kan:** ett tak som *ljuger* — säger 0,005 s när hopfogningen
i själva verket var 0,3 s — fälls som ett verkligt fel.
`test_ett_tak_som_ljuger_ligger_utanfor_grindens_rackvidd` skriver den
gränsen i kod. Ögat har bara taket; att taket täcker är M-87:s mätning
(899 av 900 varv), inte den härs.

## §2 Frisk körning i VC: hur ser PLC-axeln ut när ingen stör?

30 s, ögat i 20 Hz, kopplare med 89 ms varv (M-39:s OpenPLC-varv,
efterliknat), bryggan och `Ogonkoppling` riktiga:

| | |
|---|---|
| prov / inskott / rader med PLC | 602 / 337 / 601 |
| `plc_gammal` / avbrott | 0 / 0 |
| ålder i raden | median 60,4 ms · p95 102,6 · max 150,1 |
| tak i raden | median **14,8 ms** · p95 27,3 · **max 805,8** |
| ålder + tak | median 75,8 ms · p95 121,2 · max 955,9 |
| **otäckta** | **4 av 601 = 0,7 %** (vid t = 15,15, 20,20, 25,15, 25,20 s) |
| utan tak (PRIOR) | 0 |
| pumpens `takt` per inskott | median 0,9596 · min 0,8559 · **max 2,0213** |
| `takt_spridning` | median 0,259 · **max 23,9** |
| kopplarens tur och retur | median 6,5 ms · p95 13,5 · max 53,8; 38 av 337 tak rättade i efterhand |

Talen bekräftar M-87 och lägger till fördelningen: **taket är 15 ms i median
och under 30 ms i 95 % av raderna**, men svansen når 0,8 s. Svansen kommer
inte från vägen (tur och retur max 54 ms) utan från **klockan**: enstaka
inskott såg `takt` 2,0 och `takt_spridning` 24 — pumpens 20-slagsfönster
efter en lång tick. Fyra rader av 601 blev otäckta av det. Det är den friska
nivån: **0,7 %**, och i M-88:s fyra PLC-drivna celler 0,3–0,6 %.

## §3 Störd körning, 300 ms: fälld — av den gamla regeln

Störningen är känd i storlek och tidpunkt: VC-processen får `SIGSTOP` i 300 ms
var tredje sekund (9 stopp, uppmätt längd median 300 ms, max 302). Väggklockan
går, simuleringstiden står, kopplarens tur och retur blockeras — fas 8:s
felklass, styrd.

| | frisk | störd 300 ms |
|---|---|---|
| `plc_gammal` | 0 | **118 av 600** |
| otäckta | 4 (0,7 %) | **34 (5,7 %)** — i kluster direkt efter stoppen (t = 3,10–3,25, 6,45–6,55, 9,70 …) |
| ålder | p95 103 ms · max 150 | p95 **343** · max 432 |
| tak | p95 27 ms · max 806 | p95 **5 430** · max **7 182** |
| `takt` min/max | 0,86 / 2,02 | **0,24 / 2,97** |
| kopplarens tur och retur max | 54 ms | **287 ms** |
| dom | INCONCLUSIVE (planen ställer ingen fråga) | **INCONCLUSIVE: "PLC-värdena var inte samtidiga: 119 PLC-prov var äldre än sitt eget prov"** |

Körningen fälldes — men av **`plc_gammal`**, inte av braketten: ett stopp på
300 ms är längre än färskhetsfönstret (250 ms), så åldern själv gick över
fönstret i 118 rader. De otäckta raderna (5,7 %) låg under braketten på 10 %.
Braketten var alltså inte den grind som fällde. En grind som aldrig fällt
något är en grind ingen har provat, så nästa körning störde **kortare än
fönstret**.

Den kända cellen `station_bra` (facit PASS) under samma störning (4 stopp
under cellens 15 s): frisk **PASS**; störd **INCONCLUSIVE** (21 rader gamla)
— varken PASS eller FAIL. Sekvens- och timingdomarna svarade PASS på sina
frågor i den störda körningen också, men `_dom` släppte dem inte förbi
axelfrågan.

## §4 Störd körning, 100 ms: kortare än fönstret

Samma rigg, stoppet 100 ms var tredje sekund (9 stopp, uppmätt 100 ms
jämnt), och därtill en tredje körning med **jitter**: 30 ms var 0,5 s
(56 stopp). Frisk referens togs om i varje körning.

| | frisk (körning 2) | störd 100 ms | frisk (körning 3) | jitter 30 ms × 56 |
|---|---|---|---|---|
| rader med PLC | 599 | 603 | 600 | 603 |
| `plc_gammal` | 0 | **4** | 0 | **0** |
| otäckta | **0 (0,0 %)** | 20 (3,3 %) | 6 (1,0 %) | 20 (3,3 %) |
| ålder max | 150 ms | **399** | 194 | 215 |
| tak median / p95 / max | 13,5 / 40 / 100 ms | 15,7 / 105 / **1 826** | 14,3 / 42 / 996 | 15,9 / 63 / 1 136 |
| `takt` min / max | 0,77 / 1,38 | **0,48 / 6,79** | 0,64 / 2,26 | 0,41 / 1,40 |
| dom (planen utan fråga) | — | INCONCLUSIVE: **4 PLC-prov äldre än sitt prov** | — | — (ingen fråga, ingen gammal) |
| **`station_bra` under störningen** | PASS | INCONCLUSIVE: 3 gamla | PASS | **INCONCLUSIVE: "timing: stegets tid ligger inom hopfogningens osäkerhet"** |

Två saker att läsa ur tabellen.

**Ett stopp på 100 ms gav åldrar på 399 ms.** Fönstret är 250 ms. Stoppet
självt är kortare, men VC **hinner ikapp** simuleringsklockan efter ett
stopp (pumpens `takt` sköt till 6,8), så radens `t` hoppar medan `t_las` står
kvar — och åldern hoppar med. Så `plc_gammal` fällde även 100 ms-körningen,
fyra rader.

**Jitterkörningen är den som prövar flanklagret.** 56 stopp om 30 ms gjorde
ingen rad gammal (max ålder 215 ms) men skakade taktfönstret (`takt`
0,41–1,40, spridning upp till 24,6) så att taket steg i 20 rader (3,3 %).
`station_bra` — facit **PASS**, och PASS i alla tre friska körningar — fick
under jittret **INCONCLUSIVE**: *"stegets tid ligger inom hopfogningens
osäkerhet"*. Sekvensen höll, ingen rad var gammal, och ändå vägrade ögat
säga PASS, för ett av stegen låg utanför sitt fönster med mindre än
flankernas sammanlagda tak. Det är flanklagret som fäller en **riktig**
VC-körning, på en cell vars facit är grönt, för att hopfogningen just då inte
bar domen. Före M-97 hade samma körning fått PASS eller TOO_LATE — bägge
lika fel.

Braketten på körningsnivå (10 %) nåddes **inte** i någon av de tre störda
körningarna (5,7, 3,3, 3,3 %). Se *Braketten* nedan.

## §5 Håller taket under störningen? Klämman (M-87:s metod)

Steg 4 kör M-87:s klämma — den sanna simuleringstiden i läsögonblicket kläms
mellan två simtidsavläsningar, en hård gräns utan antagande — med
störningen på. Första körningen (300 ms var 3 s) blev klar på 1,5 s och fick
**noll** stopp: den mäter alltså taket **ostört**, och det är en användbar
referens. Andra körningen fick en egen, tätare störning (100 ms var 0,7 s).

| | ostört (100 varv) | störd, 9 stopp om 100 ms (300 varv) |
|---|---|---|
| **säkert över taket** (hela klämman utanför) | **0 (0,0 %)** | **7 (2,3 %)** |
| möjligt över (klämman skär taket) | 7 (7,0 %) | 30 (10,0 %) |
| regressionen över taket | 0 | 5 (1,7 %) |
| tak median / max | 55 / 3 212 ms | 46 / 4 994 ms |
| klämmans bredd median / max | 25 ms | 25 / 170 ms |
| d (klämmans mitt) median · p05 · p95 | −11,8 · −33 · +5 ms | −10,6 · **−266** · +15 ms |
| d min / max | −51 / +22 ms | **−2 419** / **+84** ms |
| värsta överskridande av taket | +45 ms (bara "möjligt") | **+1 091 ms (säkert)** |
| takttermen `ålder · (kvot − takt)`, p95 / max | — | 46 / **2 306 ms** |

**Under störningen håller taket inte.** Sju varv av 300 låg helt utanför sitt
tak, som mest 1,09 s utanför. M-87:s "899 av 900" gällde en ostörd brygga; det
första stoppet av processen räckte för att bryta det. Orsaken syns i
takttermen: pumpens `takt` sköt till 6,8 när dess 20-slagsfönster fick ett
simuleringshopp på ett kort väggspann, och `ålder · takt` flyttade stämpeln
2,3 s. `takt_spridning` (M-87:s klockterm) skulle bära det och gjorde det i
293 varv av 300 — inte i sju.

Riktningen: de grova missarna är **negativa** — ögat trodde värdet var
*äldre* än det var, den konservativa sidan. Den positiva sidan nådde +84 ms.
Om något av de sju säkra överskridandena låg på den positiva sidan går inte
att avläsa ur körningens sammandrag (bara min/max per körning är sparade).

Det är skälet till att rad- och körningslagren behövs bredvid flanklagret:
flanklagret **litar på taket**, och taket bar inte under ett processtopp.
Raden (`plc_gammal`, otäckt) ser åldern och takets *storlek*, inte dess
sanning — men en körning där taket skjuter till sekunder är också en körning
där åldrarna och andelen otäckta skjuter, och det fångade båda störningarna.

## Braketten, och dess härkomst

`PLC_AXEL_MAX_ANDEL = 0,10` — *Satt av M-97.*

Referensen är nio VC-körningar i den här mätningen och M-88:

| | otäckta rader |
|---|---|
| friska (6: tre 30 s-körningar, `station_bra` × 3 i M-88/M-97) | **0,0 – 1,0 %** |
| störda (3: 300 ms, 100 ms, 30 ms-jitter) | **3,3 – 5,7 %** |

Braketten ligger tio gånger över den friska toppen och över varje störd
körning också. Den är alltså ett **bakstopp**, inte den grind som fällde: de
störda körningarna föll på `plc_gammal` (300 och 100 ms) och på flanklagret
(jitter) innan andelen nådde dit. Fas 8:s brakett låg *mellan* friskt och
stört (0,75 mot 0,98 friskt och 0,61 stört); en brakett mellan 1,0 och 3,3 %
hade fällt alla tre störda körningarna här — och hade med bara sex friska
punkter under sig, den högsta på 1,0 %, riskerat att göra en frisk körning
med två taktspikar extra obestämbar. M-87 §5:s varning väger tyngst så länge
de andra två lagren bevisligen fäller: *"ögat hade blivit blint av att bli
ärligt"*. Talet är satt, mätt mot vad som finns, och LIMITS säger vad det
inte har gjort.

## Vad rapporten bär, och vad den inte bär

`derived.timing.plc_axel` bär räkningen: rader med PLC, otäckta, andel, utan
tak, fördelningen av tak och ålder + tak, braketten och om den överskreds.
Domsraden bär skälet i klartext. `LIMITS RESOLUTION … join=` bär körningens
värsta tak som förut.

Grammatiken (EYES v2) har **ingen INCONCLUSIVE-form för `STEP`**. Ett steg
som är obestämbart skrivs därför inte som en `STEP`-rad (läsaren hade kastat);
det bärs av domsraden och av `derived.station.sekvens.osakra`, och `CYCLES
late=` räknar bara verkliga tidsbrott. En v3 med `STEP … INCONCLUSIVE` vore
rätt plats, och kräver versionshöjning i samma commit som alla läsare
(`41_ogat_kontrakt.md`). Det är en skuld, och den står här.

## LIMITS

* **Störningen är `SIGSTOP` på hela processen** — den stoppar VC:s
  simuleringsklocka *och* pumpen *och* bryggans mottagning samtidigt. En
  riktig störning (fas 8: en provsvit som tar CPU) saktar ner i stället för
  att stoppa, och träffar de tre olika hårt. Riktningen och storleksordningen
  är samma felklass; fördelningen är det inte nödvändigtvis.
* **Ingen riktig PLC.** Kopplarvarvet är efterliknat med en väntesats;
  ingen OPC UA-läsning gjordes. Åldrarna i §2 är efterliknelsens.
* **Vad taket täcker under störning** mäts i §5 med klämman, som är trubbig
  (15–25 ms bred ostört, bredare under stopp) och antar att simuleringstiden
  går rakt mot väggklockan mellan avläsningarna — under ett stopp gör den
  inte det. Klämmans "säker över taket" är fri från antagandet; regressionens
  tal är det inte.
* **Ett tak som ljuger ligger utanför grindens räckvidd** (§1). Grinden är
  bara så ärlig som `plc_hopfogning_s`, och att det taket täcker är M-87:s
  påstående, mätt i 899 av 900 varv.
* **Asymmetrin mellan `plc_gammal` och otäckt står kvar.** En enda gammal rad
  gör körningen INCONCLUSIVE (M-42:s regel, oförändrad); otäckta rader gör det
  först över braketten. Båda är samma slags osäkerhet. Om den strikta regeln
  är rätt eller om båda borde dela braketten är inte mätt — att lossa på en
  fail-closed-regel utan en mätning som visar att den är fel vore fel.
* **`STEP` har ingen INCONCLUSIVE-form** i grammatiken (ovan).
* **En maskin, en förmiddag, andra agenter på samma dator.** Två av de fyra
  otäckta raderna i den friska körningen kan lika gärna vara en annan agents
  provsvit som pumpens eget fönster; `taskset -c 0-11` band VC men inte
  klienten.
* **Windows** (fas 13).
