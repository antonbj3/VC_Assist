# M-118 — Maskinsäkerhet: vad som är räknebart, och var ansvarsgränsen går

**Datum:** 2026-09-05
**Uppdrag:** research inför `docs/spec/52_regelbanken.md` (byggs INTE här — se dess
gräns: banken får NEKA och AVSTÅ, aldrig GODKÄNNA)
**beskriver:** `docs/spec/52_regelbanken.md`, `bank/uppgifter/P-07.json`,
`C-04.json`, `H-01.json`, `docs/matningar/M-106_bankens_facitkallor.md`
**Metod:** webbsökning + direkthämtning av primärkällor (EUR-Lex,
legislation.gov.uk, SICK:s egen driftinstruktion). Standarderna själva
(ISO/IEC-texterna) är upphovsrättsskyddade och lästes INTE i fulltext här —
bara det som är publikt citerbart (innehållsförteckningar, adopterade utdrag,
tredjehandsreferat) användes, och varje gång bara ett referat fanns säger
raden det.

## LIMITS

* **Ingen paragraf i det här dokumentet är ny "sanning" för banken.** Allt som
  redan var belagt i `M-106` (ISO 13855, IEC 60204-1, ISO 13850, ISO 10218:2011,
  IEC 62046, ISO 14119 m.fl.) återanvänds, inte räknas om. Det här dokumentet
  lägger till ISO 13857, ISO/TS 15066, ISO 13849-1, IEC 62061, de nya
  ISO 10218:2025-utgåvorna, juridiken och verktygsjämförelsen.
* **Två fynd är EGET, direktverifierat mot primärkälla** (inte ett referat av
  ett referat): (a) 2006/42/EG Annex I punkt 1:s ordalydelse, hämtad från BÅDE
  EUR-Lex-sökningen och legislation.gov.uk:s konsoliderade text, som konvergerar
  ordagrant — det är den enda platsen i det här dokumentet med två oberoende
  källor på exakt samma mening; (b) SICK Safety Designers egen
  driftinstruktion, hämtad som PDF och lästextad lokalt med `pdftotext` — se
  §4. Allt annat i det här dokumentet är ETT lager sekundärkälla (en
  sökmotorsammanfattning eller en tredjepartsblogg), och det står utskrivet
  var det gäller.
* **Förordningen 2023/1230:s artikelnummer (32, 19, 3(3)) är OVERIFIERADE.**
  De kommer ur en enda `WebFetch`-sammanfattning av EUR-Lex-sidan, inte ur en
  läsning jag själv gjort av lagtexten, och ett andra sökförsök gav ingen
  bekräftande ordagrann träff. Samma verktygsklass hallucinerade nyss
  "Artikel 23 i Annex I" för 2006/42/EG (Annex har inga artiklar) — ett fel
  som upptäcktes bara för att en andra källa fanns att jämföra med. Det fanns
  ingen andra källa för 2023/1230-artiklarna. **Slå upp dem mot EUR-Lex
  själv innan något av detta citeras som fakta i banken.**
* **ISO 13857:2019:s exakta klausulnummer för "reaching over"/"reaching
  through" är INTE verifierade.** Innehållet (en tabell, inte en formel) är
  bekräftat av tre oberoende sekundärkällor (ANSI-bloggen, Schmersal, Reer),
  men ISO:s egen förhandsvisning (`iso.org/obp/ui`) gav HTTP 403 och kunde inte
  läsas. Numret "Tabell 1" är citerat, klausulen som bär den är inte.
* **Ingen litteratur hittades som svarar direkt på fråga 5** (falsklarmsfrekvens
  i just ett säkerhetsREGELVERKTYG). Det närmaste, EEMUA 191, mäter något
  annat (repeterande DCS-processlarm, inte en engångsgrind vid designtillfället)
  — se §5, som säger det rakt ut i stället för att låtsas att analogin bär.
* **Alla standardutgåvor är daterade den 2026-09-05.** Flera av dem har rörliga
  mål (se §1 och §3b): ISO 13849-1:2015 tappar sin presumtion 2027-05-15,
  ISO 10218:2011 är redan ersatt av :2025-utgåvorna, och ISO/TS 15066:s status
  är omtvistad. Ett tal härifrån som citeras om ett år måste slås upp igen.

---

## 1. Vilka standardkrav är RÄKNEBARA?

Tre kategorier framträder — operatörens ramverk ("formel" vs "omdöme") missar
en mellankategori som redan bär hela bankens 24 dömbara uppgifter:

| Kategori | Vad den är | Exempel |
|---|---|---|
| **A. Formel med indata** | ett tal jämförs mot ett tröskeltal, räknat ur en sluten formel | `S = K·T + C` |
| **B. Invariant/sekvenskrav** | ett booleskt eller ordningsmässigt villkor på styrningens signaler — INGEN formel, men fullt mekaniskt dömbart | "återställningen får inte i sig starta om cellen" |
| **C. Omdöme** | kräver en människas bedömning av scenario, arkitektur eller lämplighet | vilken kategori (0/1/2) ett stopp SKA vara för just den här risken |

Bankens 24 dömbara uppgifter (`M-106`) bygger nästan uteslutande på **B**, inte
**A** — `SYS_RESET`-flankkravet, mutingens tvågivarkrav, håll-för-att-köra.
Det är värt att säga rakt ut: regelbankens idé (`52_regelbanken.md`) är skriven
mot kategori A (`S = K·T + C`), men den delen av banken som redan FUNGERAR
mekaniskt är till 90 % kategori B. En regelbank som bara letar efter formler
missar den största räknebara ytan som redan finns.

Per standard:

| Standard | Räknebart (A eller B) | Kräver omdöme (C) |
|---|---|---|
| **ISO 13855** (2010: §5.2/§6.2; **2024: omstrukturerad, se M-106 §5**) | A: `S = K·T + C`. Redan i `P-07`. | vilket K (2000 vs 1600) väljs beroende på beräknat S — det är en regel i standarden, inte omdöme, men villkorat |
| **ISO 13857:2019** | En TABELL (ej formel): horisontellt säkerhetsavstånd som funktion av skyddsstrukturens höjd och riskzonens höjd, samt separata tabeller för öppningar (spalt/rund/kvadrat). En tabell är lika mekaniskt dömbar som en formel — det är en styckvis funktion. **Exakt klausulnummer INTE verifierat här** (se LIMITS). | vilken tabellrad som gäller (åldersgrupp, öppningstyp) är ett förval i standarden, inte fritt omdöme — men KRÄVER att man vet öppningens exakta geometriklass |
| **ISO 10218-1/-2** | A: reducerad hastighet ≤250 mm/s (2011 §5.6.2, redan i `A-07`). B: manuell återställning får inte själv starta om (2011 §5.6.3.4/.2, redan i `A-07`/`H-04`); inbyggda rörliga skydd, allmänkrav (§5.10.4.3). **VIKTIGT FYND:** ISO 10218-1:2025 och ISO 10218-2:2025 gavs ut 2025-01-31 och ersätter 2011-utgåvorna banken citerar. Paragrafnumren är INTE ommappade här — exakt samma situation som ISO 13855:2010→2024 som `M-106` redan flaggat, fast för en standard banken redan lutar sig på. | vilken riskreducering (hastighet, avskärmning, PFL) som är lämplig för en given cell är en systemdesign-fråga |
| **ISO/TS 15066:2016** | A, den mest formelbärande av alla: kraft/tryck vid kontakt räknas ur robotens hastighet och EFFEKTIVA massa i kontaktpunkten (en kinematisk beräkning, INTE en katalogsiffra) mot en tabell i Annex A (29 kroppsregioner, max kraft/tryck) samt `E_max = f_max²/(2k)` för energiöverföring. **Status omtvistad**, se nedan. | KLASSIFICERINGEN transient/kvasi-statisk kontakt (finns en flyktväg eller är kroppsdelen infångad mot ett styvt föremål?) är ett scenario-omdöme, om än ett som i princip går att härleda ur cellens egen geometri |
| **IEC 60204-1:2016(+AMD1:2021)** | Nästan uteslutande **B**: nödstopp-återställning (§9.2.3.4.2, redan i banken), stoppkategorier 0/1/2 (§9.2.2), håll-för-att-köra (§9.2.3.7), spänningsbortfall (§7.5). Få äkta formler. | vilken stoppkategori som krävs FÖR en given risk är riskbedömningens jobb, inte standardens |
| **ISO 13849-1:2023** (ersatte :2015; :2015 tappar presumtion 2027-05-15) | A: PL härleds ur Kategori + DCavg + MTTFd + CCF via (förenklad metod eller) Tabell K.1; PFHd har publicerade formler per kategori. Det HÄR är standarden Sistema-verktyget (§4) helt och hållet mekaniserar. **Se §3b: en oberoende expertkälla hävdar att 2023-utgåvans nya "två standard-PLC"-arkitekturväg kan ge PFHd som skiljer >en tiopotens och PL som skiljer ≥1 nivå för SAMMA krets** — sekundärkälla, ej verifierad mot primärtexten, men om sann betyder det att en KORREKT citerad paragraf i den AKTUELLA utgåvan ändå kan ge en otvetydig siffra fel. | Kategorival, CCF-poäng (Annex F, checklista 65/100 poäng) är rena bedömningar, inga mätvärden |
| **IEC 62061:2021 (Ed. 2.0)** | A: samma PFHd-ram som 13849-1 men SIL-uttryckt; SIL3 kräver PFHd < 10⁻⁷. Numera teknikoberoende (el/hydraulik/pneumatik), inte bara elektrisk. | val av SIL-nivå för en given risk = omdöme; val av 13849-1 vs 62061 som väg = omdöme |

---

## 2. Var kommer indata ifrån? (byggt på 51_komponentdata.md:s tre-källors-ram)

Operatörens exempel (`T` i ISO 13855 måste mätas, inte hämtas ur katalog) är
redan bevisat i `P-07`/`M-106`: pressens bromstid 275 ms står som `ANTAGEN` i
katalogindexet, och just därför finns `ST460_STP_TIME` som en signal styrningen
måste läsa i drift — ett räknat avstånd ur en katalogsiffra är "inget
säkerhetsavstånd förrän stopptiden är uppmätt på den verkliga pressen"
(`P-07` facit_spar).

**Samma mönster återkommer, en nivå djupare, i ISO 13849-1 — och ingen i
banken har tittat dit än.** MTTFd räknas i standarden ofta ur ett `B10d`-värde
(antal cykler till 10 % dödliga fel, en katalogsiffra för komponenttypen) via

    MTTFd = B10d / (0,1 × nop)

där `nop` är det **genomsnittliga antalet manövreringar per år** — en storhet
som INTE står i katalogen. Den är antingen en konstruktionssiffra (deklarerad
i cellens egen cykeltid: `nop = drifttimmar/år × cykler/timme`, precis som
bankens egna `A-03`/`C-06`-räkningar redan gör ur cellens egna mått) eller,
om cellens verkliga drifttakt avviker från konstruktionsantagandet, ett tal
som måste **mätas** på den riktiga anläggningen för att `MTTFd` — och därmed
`PL` — ska stämma. Det är exakt samma struktur som `T` i ISO 13855: en
formel som ser färdig ut med en katalogsiffra, men som bär ett dolt
mätberoende en nivå in.

Fyra käll-kategorier, inte tre:

| Kategori | Exempel | Kan en regelbank hårdkoda den? |
|---|---|---|
| **Ur standarden själv** | ISO 13855 K-värden (2000/1600 mm/s), ISO/TS 15066 kraft/tryck-tabellen, C-formeln `8(d-14)` | Ja — det är en konstant i en publicerad text |
| **Ur komponentens datablad** | ljusridans upplösning `d`, en aktuators `B10d` | Ja, MEN bara med källa+enhet enligt `51_komponentdata.md` §2 — och bara giltig för TYPEN, inte den installerade individen |
| **Räknad ur cellens egna mått** | plåtämnets massa, robotens effektiva massa i kontaktpunkt (ISO/TS 15066), `nop` ur konstruktionens cykeltid | Ja, som en härledning — det ÄR vad "RÄKNAD" redan betyder i `85_bankkontraktet.md` §2 |
| **Uppmätt på den fysiska maskinen** | ISO 13855:s `T`, ISO 13849-1:s verkliga `nop` om den avviker från konstruktionsantagandet, IEC 62061:s reella insatstid | **Nej.** En regelbank kan bara AVSTÅ tills värdet finns, exakt som `52_regelbanken.md` §2 redan säger om `T` |

Slutsats: regeln "en enhet härleds aldrig ur ett värde" (`51_komponentdata.md`)
behöver ett syskon för säkerhetsberäkningar: **en katalogsiffra ärver aldrig
sin motparts verklighetsgrad.** `B10d` är verklig för komponenttypen; `PL` är
det bara om `nop` också är det.

---

## 3. Ansvarsgränsen

### 3a. Maskindirektivet 2006/42/EG — verifierat, ordagrant, mot primärkälla

**Annex I, "GENERAL PRINCIPLES", punkt 1** (bekräftat identiskt av EUR-Lex-
sökningen OCH legislation.gov.uk:s konsoliderade text — de enda två oberoende
källorna i det här dokumentet som möter varandra ordagrant):

> "The manufacturer of machinery or his authorised representative must ensure
> that a risk assessment is carried out in order to determine the health and
> safety requirements which apply to the machinery. The machinery must then
> be designed and constructed taking into account the results of the risk
> assessment."

Samma punkt beskriver den iterativa processen: bestäm maskinens gränser →
identifiera faror → uppskatta risker → utvärdera risker → eliminera/reducera.

**Det avgörande: skyldigheten ligger namngiven på "the manufacturer... or his
authorised representative."** Inget verktyg, ingen programvara, ingen
"regelbank" nämns eller kan nämnas som bärare av den plikten — plikten är
personlig/organisatorisk (tillverkaren, eller den som sätter ihop en cell och
därmed juridiskt BLIR tillverkare av den sammansatta maskinen). Ett
beräkningsverktyg kan vara **underlag** till bedömningen, aldrig bäraren av
den.

### 3b. Maskinförordningen (EU) 2023/1230 (gäller från 2027-01-20) — OVERIFIERAT lager

Enligt en enda `WebFetch`-sammanfattning av EUR-Lex (INTE dubbelkontrollerad,
se LIMITS):

* **Artikel 3(3)** ska definiera "safety component" som *"a physical or
  digital component, including software... which is designed or intended to
  fulfil a safety function"* — om ordagrant, betyder det att mjukvara som
  UTFÖR en säkerhetsfunktion kan vara en säkerhetskomponent i sig, oavsett om
  den är fristående programvara.
* **Artikel 19** ska säga att programvara som utför en säkerhetsfunktion och
  släpps på marknaden separat ska räknas som en säkerhetskomponent.
* **Artikel 32** ska upprepa riskbedömningsplikten och uttryckligen utvidga
  den till att omfatta **förutsebara framtida mjukvaruuppdateringar**.

**Dessa tre artikelnummer är inte verifierade här.** De ska slås upp mot
EUR-Lex primärtext (`CELEX:32023R1230`) innan de citeras i banken eller för
operatören som fakta — exakt den regel `52_regelbanken.md` §4 redan kräver
("en regel utan paragrafhänvisning får inte finnas i banken"), fast tillämpad
på juridiken i stället för tekniken.

**Om innehållet ändå stämmer** (det är konsekvent med flera oberoende
sekundärkällors sammanfattningar av förordningen i stort, bara inte med
artikelnumren specifikt) har det en skarp implikation för `52_regelbanken.md`:
en programvara som BÖRJAR PÅSTÅ att en layout är säker (ett "GODKÄNNER") rör
sig mot definitionen av en säkerhetskomponent som "designed or intended to
fulfil a safety function" — och skulle då kunna dras in i förordningens
CE-märknings- och bedömningskrav. En programvara som bara jämför ett angivet
tal mot en citerad tröskel, och ALDRIG uttalar sig om resultatet ("layouten
är säker"), ligger mycket längre från den definitionen — den utför aritmetik
på indata en människa tillhandahåller och tolkar, snarare än en
säkerhetsfunktion i sig. **Detta är en HYPOTES som kopplar juridiken till
bankens designval, inte något en domstol eller myndighet sagt om just det
här verktyget.** Ingen sådan vägledning hittades (se nedan).

### 3c. Rättsfall och vägledning om beräkningsverktyg — INGET HITTAT

Ingen sökning gav ett rättsfall eller en myndighetsvägledning som specifikt
gäller ett beräknings-/rådgivningsverktyg för maskinsäkerhet som hållits
ansvarigt för ett felaktigt säkerhetspåstående. Det enda konkreta rättsfallet
som kom upp (Therac-25, 1985–1987, sex patienter dödade/skadade av en
strålningsdos) är en ANNAN kategori: en inbäddad styrmjukvara som VAR en del
av maskinens egen säkerhetskrets (inga hårdvaruspärrar fanns), inte ett
fristående rådgivningsverktyg som körs vid designtillfället. Det är alltså
inte prejudikat för regelbankens situation, bara ett bevis på att
mjukvarufel i en säkerhetskrets kan vara dödliga.

Den allmänna produktansvarsjuridiken (sekundärkälla: Linklaters, IAPP) säger
att det är en **öppen juridisk fråga**, inte en avgjord, om ett mjukvarufel
räknas som ett "produktfel" enligt EU:s produktansvarsdirektiv när mjukvaran
är fristående (inte inbyggd i en fysisk produkt som säljs som en enhet). Det
här är alltså osäkert i grunden, och regelbankens NEKA/AVSTÅR-gräns är en
rimlig försiktighetsåtgärd mot exakt den osäkerheten — men det är INTE samma
sak som att gränsen gör verktyget juridiskt riskfritt. Ingen källa hittades
som säger att den gör det.

---

## 4. Finns verktyg redan? — deras egna formuleringar

### SICK Safety Designer — PRIMÄRKÄLLA, verifierad

Hämtad och lästextad direkt ur SICK:s egen driftinstruktion
(`operating_instructions_safety_designer...pdf`, avsnitt 2 "SAFETY INFORMATION"):

> "Safety Designer can be used to design, configure, commission, and diagnose
> safety-related devices or system configurations."
>
> "Only qualified safety personnel may use the configuration software to
> project plan, configure, commission, and diagnose safety-related devices,
> device groups or system configurations."
>
> "You need safety expertise to implement safety functions and select
> suitable products for that purpose. You need expert knowledge of the
> applicable standards and regulations."
>
> "You need suitable expertise and experience. **You must be able to assess
> if the machine is operating safely.**"

Det sista är den skarpaste formuleringen i hela den här utredningen: verktyget
lägger uttryckligen bedömningen "är maskinen säker" på **personen**, aldrig
på programvaran. Det säger sig självt vara ett konfigurationsverktyg, aldrig
en godkännandeinstans. Det är precis den meningen `52_regelbanken.md` borde
citera som förebild för sitt eget språk.

### Pilz PAScal — blandat lager

Tredjehandskälla (machinebuilding.net) beskriver PAScal som "a verification
calculator, not a design tool" som kräver att säkerhetskretsen redan är
KONSTRUERAD innan verktyget används — PAScal räknar inte fram en design, den
kontrollerar en. Samma källa citerar Pilz: de "cannot accept any liability for
omissions or incomplete information" och kräver "detailed understanding and
correct application of all relevant standards and directives."

Den enda text jag själv kunde läsa ur en primär Pilz-PDF (produktens readme)
var en GENERISK dokumentansvarsfriskrivning, inte en
beräkningsspecifik: *"We accept no responsibility for the validity, accuracy
and entirety of the text and graphics presented in this information."* — det
här gäller dokumentets innehåll i stort, inte specifikt beräkningsresultatet,
och ska INTE förväxlas med en säkerhetsspecifik ansvarsklausul. Jag hittade
inte PAScal:s faktiska in-app-disclaimer i ordagrann form.

### Sistema (IFA/DGUV) — sekundärkälla

Sistema beräknar PL enligt EN ISO 13849-1 ur användarens egna
arkitektur-/MTTFd-/DC-/CCF-indata — exakt den mekanism §1 beskriver för
ISO 13849-1, byggd som mjukvara. Enligt en sökmotorsammanfattning av IFA:s
egen licenstext (ej läst i primärform här):

> "Use of the SISTEMA software is at the user's own risk... no liability will
> be accepted for the software on any legal basis... except in cases of
> malicious or wrongful intent," och IFA/DGUV:s ansvar är begränsat till
> "wrongful intent and gross negligence."

### Mönstret, tre av tre

Ingen av de tre verktygen säger NÅGONSIN "din layout/maskin är säker."
Alla tre säger någon variant av: verktyget räknar/konfigurerar/verifierar mot
en namngiven standard, en kvalificerad person förblir ansvarig för att tolka
resultatet mot verkligheten. Det bekräftar — och skärper med ett citat —
`52_regelbanken.md` §1:s befintliga gräns. Det är inte en ny regel banken
behöver, det är bevis på att branschens starkaste aktörer redan valt samma
gräns, av samma skäl.

---

## 5. Kalibreringen — falsklarmsfrekvens

**Ingen litteratur hittades som svarar direkt på frågan** ("vad är en rimlig
NEKA-frekvens för ett designtida säkerhetsregelverktyg, innan användare slutar
lita på det"). Det närmaste publicerade, kvantifierade måttet är EEMUA 191
("Alarm Systems: A Guide to Design, Management and Procurement") — men det
mäter en ANNAN sak: repeterande DCS-processlarm i en kontrollrumsmiljö, inte
en engångsgrind som körs vid designtillfället på en layoutfil. Siffrorna
(sekundärkälla, EEMUA-dokumentet själv är bakom betalvägg):

* Genomsnittlig "hanterbar" larmfrekvens: **<1 larm per 10 minuter** (~6/timme)
  — bara ~25 % av verkliga kontrollrum i den studerade branschen nådde ens
  denna nivå.
* "Larmöversvämning" definieras som **>10 larm på 10 minuter** på en
  operatörsposition.
* Toppfrekvens efter en större störning: mål ≤10 larm de första 10 minuterna.

**Analogigapet måste sägas rakt ut:** en regelbank som NEKAR en layoutfil är
strukturellt inte samma sak som ett repeterande processlarm en operatör sitter
och bevakar i realtid. EEMUA:s siffror mäter uttröttning genom UPPREPNING;
regelbankens risk är snarare att ETT NEKANDE som visar sig fel (falskt) gör
att nästa nekande, veckor senare, ignoreras — en förtroendekurva, inte en
frekvenskurva. Ingen källa hittades som mäter DEN kurvan för ett
designverktyg av regelbankens typ.

Den allmänna "alarm fatigue"-litteraturen (industri- och patientsäkerhet,
huvudsakligen leverantörsbloggar och APSF, inte peer-reviewat för den här
domänen) bekräftar bara det kvalitativa mönstret som redan är känt: hög
falsklarmsfrekvens → avtrubbning → operatörer stänger av eller ignorerar
larmfunktionen. Det ger ingen siffra att kalibrera regelbanken mot.

**Vad som DÄREMOT redan går att mäta i det här repot:** `M-106` §6 visar att
med bara 24 av 63 uppgifter dömbara, "klarar" ett nollprogram redan 10 av de
24 mot sina egna punktkrav — inte för att nollprogrammet är säkert, utan för
att en förregling som aldrig prövas mot en verklig avvikelse ser grön ut av
brist på data. Samma mekanism skulle göra en regelbanks NEKA-frekvens
OMÄTBAR i dagsläget: med så få räknebara villkor (`ISO 13855` i en enda
uppgift) finns inget stickprov stort nog för att en NEKA/total-kvot ska
betyda något. **Förutsättningen för att svara på fråga 5 är fler dömbara
säkerhetsvillkor i banken — inte en till litteratursökning.**

---

## 6. Vad detta lägger till `52_regelbanken.md`

Specens gräns (NEKA/AVSTÅR, aldrig GODKÄNNER) är **INTE ändrad** här. Det som
läggs till är:

1. §1 (Den avgörande gränsen) får sitt starkaste externa stöd: SICK Safety
   Designers egen text — "you must be able to assess if the machine is
   operating safely" — lagd på operatören, aldrig på verktyget, i en
   marknadsledande produkt.
2. §2 (Parametrarna) får ett andra bevis på samma mönster som `T`: ISO 13849-1:s
   `nop` inne i `MTTFd = B10d/(0,1×nop)` — en katalogsiffra (`B10d`) som ändå
   kräver ett mätvärde en nivå in för att bli sann.
3. En ny räknebar yta identifierad: ISO/TS 15066 (kollaborativ kraft/tryck) är
   den mest formelbärande standarden av alla som undersökts, och dess
   ingångsvärden (robotens effektiva massa i kontaktpunkten) är RÄKNADE ur
   cellens egen geometri — samma källkategori som plåtämnets massa i `P-07`.
4. En rörlig-mål-varning till: `ISO 10218-1/-2:2011`, som banken redan citerar
   i `A-07` och `H-04`, är ersatt av :2025-utgåvorna. Ingen ommappning är gjord.
5. En allvarlig men overifierad varning: en oberoende expertkälla hävdar att
   `ISO 13849-1:2023`:s nya PLC-arkitekturväg kan ge motstridiga PFHd/PL för
   samma krets — om sant, är "citera paragrafen" en NÖDVÄNDIG men INTE
   TILLRÄCKLIG garanti mot ett fel resultat.

Inget av detta ändrar slutsatsen i `52_regelbanken.md` §5: det här är
fortfarande inte en säkerhetsbedömning, inte CE-underlag, och ersätter ingen
människa.
