# 52 — Regelbanken: standarder som geometriska villkor

## Vad idén är

En standard säger ofta något **räknebart** om var saker får stå. `ISO 13855`
ger säkerhetsavståndet till en ljusridå som

    S = K · T + C

där `K` är närmandehastigheten, `T` maskinens totala stopptid och `C` ett
inträngningsdjup som beror på detektionsförmågan.

Layouten säger var saker **faktiskt** står. Skillnaden mellan de två är
aritmetik, och aritmetik går att grinda.

Vi gör redan en bit av det utan att kalla det så: `P-07` i banken bär ett
säkerhetsavstånd räknat enligt `ISO 13855`, `C-04` och `H-01` bär krav ur
`IEC 60204-1`, och `50_grindar.md` hänvisar till `ISO 13849`.

---

## 1. Den avgörande gränsen: banken får NEKA, aldrig godkänna

En layoutrådgivare som säger *"det här är säkert"* är farlig, och den skulle
dessutom bryta mot en regel projektet redan har: **ingenting genererat rör en
säkerhetsfunktion.** Nödstopp och skyddskretsar ligger på certifierad
säkerhets-PLC, i begränsat variabelt språk, skrivet av människa.

Regelbanken lyder samma asymmetri:

| Utfall | Tillåtet | Vad det betyder |
|---|---|---|
| **NEKAR** | ja | avståndet är kortare än formeln ger för de angivna parametrarna |
| **AVSTÅR** | ja | en parameter saknas eller är inte mätt |
| **GODKÄNNER** | **nej** | banken säger aldrig att en cell är säker |

Skälet är detsamma som för säkerhetsordlistan i `harness/sakerhet.py`: en
heuristik som **stoppar** är godtagbar, en som **släpper igenom** är det inte.
Skillnaden är att här är konsekvensen en människa vid en maskin.

---

## 2. Parametrarna är inte katalogdata, och det är hela svårigheten

`S = K · T + C` ser ut att gå att räkna ur en komponentkatalog. Den gör det
inte.

* `K` är en normerad närmandehastighet ur standarden — den kan banken bära.
* `C` följer av ljusridåns detektionsförmåga, som **står i dess datablad**.
* `T` är maskinens **uppmätta totala stopptid**, inklusive ställdon, ventiler
  och styrsystemets svarstid. Den står inte i någon katalog. Den mäts på den
  fysiska maskinen, och den ändrar sig när maskinen slits.

Ett `T` med ett rimligt förvalsvärde är exakt det farliga: talet ser färdigt
ut. `51_komponentdata.md` har redan regeln — **en enhet härleds aldrig ur ett
värde** — och den gäller här med skärpa: **ett säkerhetsavstånd räknas aldrig
ur ett antaget `T`.** Saknas det, avstår banken och säger vilken parameter som
fattas.

Mätt sammanhang: `M-85` fann att bara **14 %** av bibliotekets 82 383
egenskaper deklarerar vilken storhet de bär, och att `MaxPayload` står utan
enhet i 2 986 komponenter varav 628 med värdet `0`. Katalogen är alltså inte
en källa man räknar säkerhet ur.

---

## 3. Varför det ändå är värt att bygga

**Facitkällan är den starkaste som finns.** `85_bankkontraktet.md` §2 rangordnar
facitkällor, och en standardparagraf står överst — före geometri, före en
människas facit. En regel ur `ISO 13855` är inte vår åsikt; den är citerbar,
och den ändrar sig inte för att vår kod ändrar sig.

**Och den fångar fel som kostar riktigt.** Ett för kort säkerhetsavstånd är
inte ett fel som syns i en simulering — cellen fungerar, produkten kommer ut,
takttiden hålls. Det är först vid ett verkligt tillbud det märks. En grind som
räknar avståndet ser det medan layouten fortfarande är en fil.

---

## 4. Vad grönt betyder, om detta blir en fas

Varje regel i banken bär: standardens nummer, **paragrafen**, formeln,
parametrarna med var och en av dem märkt `mätt` / `ur datablad` / `ur
standarden` / `SAKNAS`, och vad felet blir när villkoret inte håller.

* En cell vars avstånd är kortare än formeln ger **måste fällas**, och felet
  ska namnge paragrafen och de tal som gick in.
* En cell där en parameter saknas ska ge **AVSTÅR**, aldrig ett godkännande
  och aldrig ett gissat tal.
* En regel utan paragrafhänvisning får inte finnas i banken. `T-01` bar en
  gång `9.2.4`, ett **påhittat** paragrafnummer, och rättades till `9.2.3.4.2`
  — ett nummer som ser rätt ut är inte ett nummer.

**Trasiga fall:** en layout som klarar avståndet med en millimeter, en som
missar med en millimeter, en där `T` saknas, och en regel vars paragraf inte
går att slå upp.

---

## 5. Vad detta INTE är

Det är **inte** en säkerhetsbedömning, inte en riskanalys enligt `ISO 12100`,
och inte ett underlag för CE-märkning. Det är en aritmetisk kontroll av ett
fåtal räknebara villkor, och den ersätter ingen människa.

Ingenting i den här specen är byggt. Den beskriver en idé och den gräns som
avgör om idén är bra eller farlig.

---

## 6. Vad research bekräftat (M-118) och lagt till

`M-118` gick igenom `ISO 13857`, `ISO 10218-1/-2`, `ISO/TS 15066`,
`ISO 13849-1`, `IEC 62061`, juridiken (2006/42/EG, 2023/1230) och tre
befintliga verktyg (SICK Safety Designer, Pilz PAScal, Sistema/IFA). Fem
punkter, i fallande styrka:

1. **Gränsen i §1 har externt stöd, ordagrant.** SICK Safety Designers egen
   driftinstruktion säger till användaren: *"You need suitable expertise and
   experience. You must be able to assess if the machine is operating
   safely."* Bedömningen ligger på personen, aldrig på verktyget — i en
   marknadsledande produkt, inte bara i vår egen försiktighet.
2. **§2:s mönster (`T` mäts, katalogen räcker inte) återkommer en nivå in i
   `ISO 13849-1`:** `MTTFd = B10d / (0,1 × nop)`, där `nop` (manövreringar
   per år) inte står i katalogen och antingen härleds ur cellens egen
   drifttakt eller måste mätas om den verkliga takten avviker. En
   katalogsiffra ärver aldrig sin motparts verklighetsgrad.
3. **En ny formelbärande yta:** `ISO/TS 15066` (kollaborativ kraft/tryck) är
   den mest räknebara standarden av alla undersökta — kraft/tryck räknas ur
   robotens EFFEKTIVA massa i kontaktpunkten, en geometrisk härledning, mot en
   tabell i standardens Annex A. Dess status är dock omtvistad: innehållet
   ska vara upptaget i `ISO 10218-2:2025`, ej bekräftat mot primärkälla.
4. **Rörligt mål, ett till:** `ISO 10218-1/-2:2011` (banken citerar dem i
   `A-07`, `H-04`) är ersatt av **:2025**-utgåvorna (utgivna 2025-01-31).
   Ingen paragrafommappning är gjord.
5. **Juridiken pekar åt samma håll som §1, men artikelnumren i
   2023/1230 är overifierade** (en enda, ej dubbelkontrollerad källa) — se
   `M-118` §3b innan de citeras som fakta. Det som ÄR verifierat, ordagrant
   och mot primärkälla: 2006/42/EG Annex I punkt 1 lägger riskbedömningsplikten
   på "the manufacturer... or his authorised representative", aldrig på ett
   verktyg.

Fullständigt (inklusive vad som INTE gick att belägga): `docs/matningar/M-118_maskinsakerhet_rakningsbart_och_ansvarsgransen.md`.
