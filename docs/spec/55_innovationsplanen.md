# 55 — Innovationsplanen: vad som bär, vad som är självreferens, vad produkten är, och vad vi slutar med

Skrivet 2026-09-05 efter ett dygn med 569 commits och 107 mätningar. Skälet
till dokumentet är att fynden pekar åt olika håll och att ingen längre
överblickar vilka som bär.

**Besluten här är mina.** Operatören kan riva vart och ett. Men varje beslut
står med det tal som satte det, så att den som river vet vad som ska mätas om.

Ingenting i det här dokumentet är byggt utom en mätning: `M-122`, som behövdes
för att avgöra §1.2 och §1.4 och som ändrade en slutsats operatören hade i
handen samma morgon.

---

## §1 Motsägelserna, och hur de löstes

### 1.1 "Spåret är golvet som alltid håller" (fas 18) mot "spåret är blint för en hel felklass" (M-115)

**Båda är sanna, om olika saker. Fas 18:s ord lovar för mycket.**

Fas 18 talar om **tillgänglighet**: när projektfil, källa och symboltabell är
borta finns spåret alltid kvar. Det är sant (M-114). M-115 talar om
**diskriminerande kraft**: ett spår med en puls kan inte skilja flankläsning
från nivåläsning. Också sant — och M-89 hade redan mätt samma sak i en annan
form: ur ett produktionsspår återfinns 3 av 28 förreglingar.

Men M-122 §3 gör M-115 snävare än den skrevs. Den riktiga F15-mutationen —
`trig.Q` byts mot nivåsignalen — körd på alla 26 referenser fångas av bankens
spårfacit på **12 av 12** materialflanker och **1 av 15** återställningsflanker.
Blindheten är inte spårets. Den är **stimulusens**: där någon skrev en sekvens
som håller signalen (två burkar i rad, fotocellen hög en hel sekvens,
återställningen hållen medan ett fel inträffar) faller nivåläsningen varje gång.

**Rättelse i fas 18:s rad:** *"spåret är alltid tillgängligt och aldrig
tillräckligt — det bär det linjen gjorde, inte det den skulle göra"*. Ordet
*golv* ska bort; ett golv man inte kan stå på är inget golv.

### 1.2 M-111 "31 av 68 fällplatser har aldrig fyrat" mot mutationen "fyrar många"

**Talen går ihop. De räknar olika enheter.** M-122 §4: 809 mutanter fyrar
**4 distinkta** av grind 2:s (nu) 76 fällplatser och **0** av de 35 som aldrig
fyrat. Mutationen räknar händelser; M-111 räknar platser. Grind 2 fäller alla
textskador och typfelen och **noll av 464 andra beteendeskador** — de går
genom lexerns `Syntaxfel`, inte genom validatorn.

Följd: grind 2:s otäckta platser är inte där beteendefelen bor. De är
prioriterade först den dag en modellkropp faktiskt träffar dem (§4 punkt 3).

### 1.3 Enskott mot flerskott — är enskott ens rätt variabel?

`54` §5 har rätt i att enskott inte får vara huvudtalet. Men den missar vad
den verkliga variabeln är.

Först de tal som finns och som ingen fört in i `70_faser.md`. Fas 9-raden
säger *"flerskott 3 av 4"*. M-110:s råfiler (Muse Spark, tak 4, 26 uppgifter
med spårfacit, `m110_flerskott_ms_{A,B,C}.json` + piloten) säger:

| varv till löst | 1 | 2 | 3 | 4 | slog i taket |
|---|---:|---:|---:|---:|---:|
| uppgifter | **4** | **9** | **6** | **4** | **3** (`C-04`, `L-06`, `H-01`) |

**Enskott 4 av 26. Inom taket 23 av 26. Medianvarv 2–3.** Med taket höjt till
8 löstes `C-04` (varv 3) och `L-06` (varv 4); `H-01` föll aldrig. Vad varv 1
föll på, över 24 uppgifter med varvdata: **17 på spårfacitet, 3 på grind 2
(`ARGUMENT`), 4 på ingenting.** Modellens första fel är beteende, inte text.

Regelbaslinjen (M-62, `bank/baslinjebank.py --slinga`, omkörd 2026-09-05)
löser **4 av 26** i varv 1 — exakt de fyra ursprungliga uppgifterna — och **0
av de 22 nya**. Varningen i `70_faser.md`, *"fyra av fyra är oavgjort mot en
mallkompilator"*, gäller alltså de fyra gamla och ingen av de nya.

Så här läses talen. Operatörens ord var *"100 % reliable structured text,
preferably oneshotted"*. Tillförlitlighet är kravet. Enskott är preferensen.
Och den variabel varken `54` eller M-110 skriver ut: **vad "löst" är dömt av.**
I M-110 är det grind 2 och 3 plus spårfacitet genom vår tolk. Inte STruC++
(`bygg_uppsattning` ger `Stationssteg` ingen kompilatorsökväg), inte OpenPLC,
inte VC. Facitet är klass 4 i `85` §2 — en människas (eller en modells)
förhandsskrivna sekvens.

**Beslut:** tre tal rapporteras alltid tillsammans — varv 1, inom taket, varv
till konvergens — **och en fjärde rad: facitklassen och motorn som dömde.**
Ett "23 av 26" utan raden *"tolk, klass 4"* är samma kategorifel som att jämföra
med LLM4PLC:s 72 %. Enskott stannar som kostnadsmått (`54` §2), inte som mål.

### 1.4 Fler motsägelser, hittade på vägen

| Påstående i repot | Vad som faktiskt gäller | Källa |
|---|---|---|
| `mut.txt`: 471 av 806 fångade, **14** av beteendelagret; *"beteendeskador fångas knappt alls"* | **718 av 809, 375 av beteendelagret.** 80 % av beteendeskadorna fångas av facitet. Det gamla talet går inte att reproducera; körskriptet finns inte. Mönstret 21 = 7 × 3 pekar på att referensernas egen rödhet (M-121) räknades som fångst | M-122 §1 |
| *"Två flankmutationer fångades av textlagret av fel skäl — tur, inte täckning"* | Sant för `FLANKENS_Q_TILL_SIGNAL` (68 typfel). Men `FLANK_TILL_NIVA` fångas **30 av 30 av beteendelagret**, och den gör inte det den heter — den stryker flanken. Den riktiga nivåoperatorn fanns inte i motorn | M-122 §3 |
| Fas 21: *"de 37 som saknar facit saknar exakt ett fält"* | 14 av de 37 är `broken`-varianter, avsiktligt trasiga. Återstående arbete är **23 svar**, inte 37 | `bank/uppgifter/*.json`, nyckelinventering |
| Fas 9: *"flerskott 3 av 4"* | 23 av 26 (M-110), aldrig infört i `70_faser.md`. M-110 är daterad 2026-09-06 för körningar gjorda 09-05 | M-110 råfiler |
| `00_index.md`: *"Alla dokument, i nummerordning"* | Spectabellen slutar vid `50`; mätningstabellen vid **M-34**. 72 mätningar och `51`–`54` står inte i indexet. Ser komplett ut | `00_index.md` |
| `tests/motbevis`: *"prov som SKA vara röda"* | **29 röda, 26 gröna.** 26 lagade hål vars prov aldrig flyttats till `tests/enhet` som README föreskriver | `pytest tests/motbevis`, slutkod 1 |
| `20_arv.md`: femton mekanismer *"Fungerar"*, dokumentindex *"0 byte"*, godkännandekö *"finns inte"* | Läsning av ett annat repo. Operatören säger att sådana läsningar inte är pålitliga. **Ingen rad är verifierad här.** Inget beslut i den här planen vilar på dem | operatörens varning |
| M-115: F15 är *"strukturellt osynlig för varje spårbaserad verifierare"* | Osynlig **per sekvens** där stimulus inte håller signalen; synlig i 13 av 30 fall i bankens egna facit | M-122 §3 |
| M-62: *"baslinjen löser 4 av 4"* | 4 av 26 i dag. Håller för de fyra den skrevs mot; 0 av 22 nya | omkörning 2026-09-05 |

Sista raden i `54` §6 — *skuld är det som felaktigt tros vara gjort* — gäller
alltså också `54`:s egna grannar: indexet, motbevisen och mutationstalet såg
alla färdiga ut.

---

## §2 Bärande mot självrefererande

Kriteriet är ett enda: **varifrån kommer facitet?**

* **V — verkligheten eller tredje part.** Facitet är något vi inte skrev: VC:s
  faktiska beteende, en kompilator (STruC++, OpenPLC), ett OS, en publicerad
  standard, ett datablad, en artikel i fulltext.
* **M — modellen är extern, domaren är vår.** En riktig språkmodell skrev
  koden; vår domare dömde den mot vårt facit.
* **B — blandad.** VC:s fysik är verklig, men fixturerna och ögat är våra.
* **A — artefakt mot sig själv.** Spec mot kod, register, täckning, attrapper,
  egna fixturer, egna referenser muterade och dömda av eget facit.

| klass | antal av 107 | vilka |
|---|---:|---|
| **V** | **61** | M-01–09, 11–17, 20, 32–42 (VC:s motor, pump, koppling, flöde); 44, 91, 92 (Windows/Wine); 48, 51, 54, 99, 108 (kompilatorer); 56, 71, 90, 109 (ren maskin, distros); 49, 55, 57–59, 61, 67, 72, 76, 85–87, 101, 112 (VC:s filer, bibliotek, scen, brygga); 106, 107, 118 (standarder, datablad); 113, 114, 116, 120 (litteratur, protokoll, DOK) |
| **M** | **6** | M-78, 80, 82, 84, 96, 110 |
| **B** | **6** | M-50, 73, 74, 88, 97, 115 |
| **A** | **34** | M-31, 45, 46, 47, 52, 53, 60, 62–66, 68–70, 75, 77, 79, 81, 83, 89, 93–95, 98, 100, 102–105, 111, 119, 121, **122** |

Tre saker att läsa ur tabellen, och de är hårdare än de ser ut.

**1. Ingen av de 107 mäter en fabrik.** V-klassen är stor, men den mäter
*plattformen* — VC, kompilatorer, vår installation — och *litteraturen*. Noll
mätningar rör en verklig PLC i drift, en verklig anläggnings spår, eller en
verklig användares arbetsdag. M-89 heter *"anläggningen utan kod"* och kör
bankens egna referenser. M-116 är det närmaste vi kommit en användare, och den
är DOK via sökmotorsyntes. Operatören har rätt: den vetenskap som bara mäter
oss själva är inte intressant, **och det gäller också min egen M-122.**

**2. A-klassen är inte värdelös, men den får aldrig bli ett produktpåstående.**
M-31, M-70, M-79, M-95 hittade var sin falska gröna innan den kostade en
körning. Det är hygien. Regeln blir: **ett A-tal står aldrig i ett påstående
om vad produkten kan.** Bara V, M och B får det.

**3. Det som faktiskt bär produktfrågan är sex B- och M-mätningar.** M-74
(fem kompositionsfel fällda bara i linan, grind 1–4 gröna i alla 18
körningar), M-88 (fyra av fem domare fäller VC-byggda celler ensamma), M-96
och M-110 (återkopplingen lyfter 0 av 20 till 23 av 26), M-73 (linan går),
M-97 (och PLC-axeln håller inte under processtopp). Allt annat är
förutsättningar för dem.

---

## §3 Vad produkten ÄR

Givet (M-116, DOK, hämtade sidor): Siemens och Rockwell levererar naturligt
språk → PLC-kod. KUKA levererar naturligt språk → cellayout. Ingen av dem
behöver oss för det.

Kandidaterna, och varför de faller eller står:

| kandidat | faller/står | skäl |
|---|---|---|
| Kodgenerering från text | **faller** | Siemens, Rockwell. Vår modell är dessutom bara modellen; vår del är grindarna |
| Layout från text | **faller** | KUKA. Och M-116 §2: layout är den snabba delen av arbetet redan i dag |
| Brownfield: kod ur anläggning | **faller** | M-114: ingen väg ger källkoden tillbaka. M-89: produktionsspår ger 3 av 28 |
| Export/hot-swap ur VC | **faller som produkt** | Ett format är ett löfte om att inte vara låst, inte ett värde i sig (`53`) |
| Appen/ytan | **faller** | Sju av femton delar obyggda; en yta är inte ett skäl att byta verktyg |
| Bänken | **står som instrument, inte som produkt** | M-120: ingen öppen bänk finns. Det är trovärdighet, inte funktion |
| **Domaren som talar tillbaka** | **står** | se nedan |

**Beslutet: produkten är domaren som talar tillbaka — en leverantörsneutral
verifieringsslinga för styrlogik mot en körande anläggningsmodell, där linan,
inte stationen, är nivån den dömer på.**

Vad det betyder konkret: kod (vår eller någon annans) → grindar → mjuk-PLC →
scen → ögat dömer mot ett förhandsskrivet facit → domens egna ord tillbaka till
den som skrev koden. Fas 8 är beviset att nivån är rätt: fem fel som **båda
stationerna passerade ensamma** och som bara linan ser (M-74). Det är vad
ingen av de tre leverantörerna säger sig göra, och vad den akademiska
litteraturen säger tar tiden (M-116 §2: *"software debugging is the main
consumer of time"* i driftsättningen). PLCopen XML ut (M-113) gör den
leverantörsneutral på riktigt: domen gäller ST, inte TIA eller Studio 5000.

**Var påståendet är tunt, utskrivet:**

* Ingen modell har någonsin skrivit en kompositionskropp. Alla sex i M-74 är
  handskrivna. Reparationsvarven är noll.
* En lina, en geometri, en takt vald så att stationerna möts.
* Ingen riktig PLC (kopplarvarvet är efterliknat, M-97), och PLC-axelns tak
  håller inte under processtopp.
* Genomflödesdomaren kan inte fällas av någon VC-byggd cell (M-88).
* Ögat är VC-bundet. Grovt ur radräkning: `verktyg/`, `ext/`, `layout/` ≈ 24
  000 av 66 000 rader.

Därför har beslutet en **falsifierare**, och det är satsning 1 i §5. Faller
den, är produkten inte slingan utan bänken.

---

## §4 Vad vi SLUTAR med

Ordnat efter hur mycket det kostat att fortsätta. "Sluta" betyder: ingen ny
timme förrän villkoret i sista kolumnen är uppfyllt.

| # | Vi slutar med | Varför | Återöppnas när |
|---|---|---|---|
| 1 | **Personatäckning och verktygstäckning som mål** (M-100, `47`, `48`) | 228 steg vi själva skrev; 63 % mäter vår fantasi. M-116: profilen med högst poäng missar sin verkliga smärta, licenshantering rörs av noll steg | en verklig användares arbetslista finns, eller en projektledare (M-116 §4) har intervjuats |
| 2 | **Formella metoder som grind** — STL/RTAMT, NuSMV, PLCverif (M-115, `50_grindar.md`) | Strukturellt blinda där felen bor (timers, F5/F7/F15); RTAMT 0.3.5 har två mätta tysta fel. Robusthetssignalen ρ får loggas, det är allt | aldrig som grind; som logg när ögat ändå räknar måttet |
| 3 | **Grind 2:s fällplatstäckning som mål** (M-111:s 35 platser) | M-122 §4: noll beteendeskador når dem; M-99: varje ny regel är en ny risk för falsk röd, och falska röda kostade nio av sexton domar i M-96 | en modellkropp i M-110:s `kroppar_per_varv` faktiskt träffar en av dem |
| 4 | **Datablad-berikning i bulk** (M-107: 21 av 3201) | En natt gav 0,7 %. Enheten behövs per uppgift, inte per bibliotek | en uppgift kräver ett tal som saknar enhet — då berikas den komponenten |
| 5 | **Lager 1–4 ut ur VC: HOOPS/FBX-export, URDF/USD-skrivare, fysik ur täthet** (`53` §4) | Geometrin var aldrig problemet (M-113). Ett format utan mottagare är en export av ingenting. PLCopen XML + receptet räcker för "inte låst" | en konkret andra simulator är vald och någon ska ladda något i den |
| 6 | **Fas 18 ur produktionsspår** | 3 av 28 förreglingar, 12 av 18 invarianter odömbara, `EMG_OK` aldrig 0 (M-89). Ett facit ur normaldrift är trubbigt och lovar mer än det bär | ett verkligt inspelat spår finns. Provspårsvägen (28 av 28) är däremot en facitgenerator för bänken och behålls där |
| 7 | **Robotprogrammets export** (lager 9, `.NET`) | Python når inte `.NET` (M-07, M-38). Blockerad, inte svår | en `.NET`-väg är mätt öppen |
| 8 | **Mutationsmotorns nuvarande operatorer som tal** | 64 av 91 överlevare är initierare; `FLANK_TILL_NIVA` gör inte det den heter (M-122 §2–3) | operatorerna är rättade (§5 satsning 2). Då blir talet meningsfullt |
| 9 | **Fönster, meny, panelens fält 1 och 3** (`26_appen.md` §6.1, sju obyggda) | En yta framför en slinga som ingen modell drivit genom linan är en prospekt. Bara felrapporten som fil byggs (satsning 6) | satsning 1 är grön |
| 10 | **Planeringslagret** (`plan/`, 7 906 rader, fas 16 passerad) | Det planerar byggen åt en slinga som ännu bygger en handskriven lina. Fryses, inte rivs | en modell bygger linan i satsning 1 och behöver planen |
| 11 | **Modelljämförelser** (Sonnet mot Muse Spark) | Två modeller, två promptar, två tal som aldrig får jämföras (M-110 säger det själv). En modell per påstående | aldrig som jämförelse; alltid en modell per tal |
| 12 | **Nya mätningar utan ett beslut de ändrar** | 107 M-filer på ett dygn, 72 utanför indexet, 26 gröna motbevis ingen flyttat. En mätning som inte ändrar ett beslut är arkivering | varje ny M-fil namnger i första stycket vilket beslut i det här dokumentet den kan riva |
| 13 | **Fas 13 Windows — parkeras, slutas inte** | Väntar på en maskin. Protokollet finns (M-44, 16 punkter) | maskinen finns |

Det som byggdes för att det gick och inte för att det behövdes, med namn:
`ray_cast`, `frame_owner_node`, `component_info` (M-100 §6); 67 av registrets
122 verktyg som `47` aldrig föreslog; tre scenexportvägar utredda för en
mottagare som inte finns.

---

## §5 Innovationsplanen

Ordningen är ordningen. Ingen satsning nedan startas före den ovanför har
sitt avgörande tal — utom 2 och 3, som är bänkarbete utan VC och kan köras
medan VC är upptagen.

### Satsning 1 — modellen skriver linan, ögat talar tillbaka

**Ger:** svaret på om produkten finns. Fas 8 och fas 9 har aldrig mötts: fas 8
har linan men handskriven kod; fas 9 har modellen men bara stationer och bara
tolken. Här körs M-74:s rigg (`kor_fas8_linan.py`, två stationer, delat don)
med **modellen** som författare och **ögats** dom i linan som återkoppling.

**Kostar:** VC-sessionen (ägs av en annan session i dag; schemaläggs). M-74:s
körningar tog 45 s uppvärmning + 80 s mätning + omstart, tre konfigurationer
per kropp. Uppskattning: tre upprepningar × upp till fyra varv × tre
konfigurationer ≈ 36 körningar ≈ 3–4 timmar VC. Modellvarv kostar 15–65 k
tokens in (M-110). En ny körfil som fogar `Reparationsslinga` till fas 8:s
rigg; ingen ny grind.

**Avgörs av:**
1. Linan blir `GOLD` inom taket fyra i **minst 2 av 3** upprepningar, från
   ögats ord ensamma.
2. De fem K-fallen ges till modellen som *"nuvarande kod + ögats dom"*: **minst
   3 av 5** lagas inom två varv, och lagningen passerar också de två
   enstationskörningarna (så att den inte lagade linan genom att bryta
   stationen).
3. Rött på 1 **eller** 2 ⇒ produkttesen i §3 faller. Då är produkten bänken
   (satsning 4 flyttar först) och slingan en intern grind.

**Ersätter:** fas 21:s huvudtal *"spårfacit för 20 av 51 genom hela kedjan"*
och alla enskott-A/B-körningar. Fas 21:s 23 återstående svar skrivs bara i den
mån satsning 2 kräver dem.

### Satsning 2 — domaren härdad där mätningarna pekar (utan VC)

**Ger:** ett facit som fångar det M-122 och M-88 visade att det missar, och en
mutationsmotor vars tal går att lita på.

**Kostar:** bänkredigering och tre små kodändringar. Tre punktkrav (`A-03`,
`S-01`, `S-07`); en sekvens "långsammare och två gånger" i fem uppgifter
(`A-03`, `H-04`, `L-07`, `P-03`, `S-07`); en sekvens "håll återställningen
medan ett fel inträffar" i de 14 uppgifter där `SYS_RESET` läses med flank;
`mutation.py`: undanta `VAR`-initierare, byt namn på `FLANK_TILL_NIVA`, lägg
till nivåoperatorn ur M-122 §3; en VC-byggd cell med process som svälter, så
att genomflödesdomaren kan fällas av något som inte är en fixtur (M-88 §4).

**Avgörs av:** kodradsöverlevare 27 → högst 12 (bara de osynliga kvar);
nivåmutanter som överlever 17 → högst 2 (`DONE`-handskakningarna får stå
kvar med skäl); genomflödesdomaren fäller en VC-byggd cell. Allt mäts med
`kor_m122_mutationsskikt.py` och M-88:s rigg.

**Ersätter:** `54` §4 "brus i ögat" som nästa steg (bruset kommer efter, §5
satsning 7) och all jakt på grind 2:s täckning.

### Satsning 3 — tredje motorn i slingan (utan VC)

**Ger:** att "löst" slutar betyda "vår tolk håller med vårt facit". OpenPLC
finns som tredje motor (M-108: 198/17/0). De 26 referenserna och de 23 sparade
modellkropparna (`kroppar_per_varv` i M-110:s JSON) körs genom STruC++-bygge
och OpenPLC mot samma facitpunkter, och domarna jämförs med tolkens.

**Kostar:** en körfil ovanpå `kor_openplc_*.py`; timmar av maskintid, ingen
VC. Ingen ny grind.

**Avgörs av:** 26 av 26 referenser: tolk och OpenPLC eniga på varje
kontrollpunkt. **Varje** modellkropp där tolken sa LÖST och OpenPLC inte gör
det är ett fynd som ändrar M-110:s tal — och ska göra det.

**Ersätter:** raden *"domen kommer ur vår ST-tolk, inte OpenPLC"* som stått i
LIMITS i M-45, M-96, M-106, M-110 och nu M-122. Fem gånger är en skuld, inte
en förbehållsrad.

### Satsning 4 — publicera bänken

**Ger:** den enda vägen ut ur "en bänk vi själva skrev mäter vår fantasi"
(`54` §1). M-120 §2: ingen bänk i fältet är körd av mer än ett lag mot samma
facit. Den som publicerar först definierar vad "korrekt" betyder.

**Kostar:** ett släppbart underträd — `bank/uppgifter` (26 med facit + 23
utan), `bank/domare.py`, tolken, `kor_m62`, `kor_m122`, ett format-dokument,
licens. Uppskattning några dagars städning. Risk att skriva ut: referenserna
måste med (de bevisar uppfyllbarhet), och en publicerad referens kan hamna i
en modells träningsdata — R-01 §1.5:s föroreningsspärr gäller nu åt andra
hållet och ska stå i README.

**Avgörs av:** en utomstående reproducerar M-62 (4 av 26) och M-122 (718 av
809) ur det publicerade utan att fråga oss.

**Ersätter:** fler A-klassmätningar av bänkens egen ärlighet (M-104–106-typ).
Extern granskning gör det arbetet billigare och bättre.

### Satsning 5 — receptet och PLCopen XML: "inte låst", och inget mer

**Ger:** operatörens krav på att inte vara låst, med det som redan är mätt
fungerande. `53` §5 första steget: skriv ut cellen ur en körande VC i bankens
eget format plus placeringar och kopplingslista; ST som PLCopen XML (M-113,
schemavaliderat, byte-identisk).

**Kostar:** en läsare mot VC:s scen (verktygen finns: M-86 läser hela scenen,
M-101 kopplar) och en skrivare; en VC-session. CAEX 3.0-uppgraderingen görs
bara om en mottagare kräver den.

**Avgörs av:** `53`:s eget trasiga fall — en cell som skrivs ut och läses in
ger samma `canConnect`-svar och samma materialflöde. Annars beskrev receptet
inte cellen.

**Ersätter:** hela lager 1–4-spåret (§4 punkt 5).

### Satsning 6 — felrapporten som fil, och förare till de fem ytorna

**Ger:** det enda ytarbete som är motiverat före satsning 1: `26_appen.md`
§6.1 "felrapporten som fil" och M-93 §8:s fem rapportytor utan förare. Utan
dem ser operatören loggar, alltså oss.

**Kostar:** litet. Ingen VC för bygget; **en** VC som verkligen dödas för
provet — M-103 LIMITS: ingen väg tillbaka har körts mot en VC som gick ned.

**Avgörs av:** de 17 Y-reglerna och 14 A-reglerna gröna mot en riktig död VC,
inte attrapper.

### Satsning 7 — senare, i ordning

* **Brus i ögat** (`54` §4) — efter 1–3. Sensorstuds, jitter, ställdonsfördröjning
  som injicerad signal; talet är celler gröna utan och röda med.
* **Fas 13 Windows** — när maskinen finns.
* **Fas 18** — när ett verkligt spår finns.
* **Fas 21:s 23 svar** — i takt med att satsning 2 kräver dem.

---

## §6 Rättelser i befintliga dokument som följer av §1

Skrivs av den som äger dokumentet; listas här så att de inte glöms.

1. `70_faser.md` fas 18: byt *"golvet som alltid håller"* mot *"alltid
   tillgängligt, aldrig tillräckligt"* (§1.1).
2. `70_faser.md` fas 9: 23 av 26 inom taket, 4 av 26 i varv 1, median 2–3,
   **dömt av tolk mot klass 4-facit** (§1.3). Fas 21: 23 svar, inte 37.
3. `54_felstallda_fragor.md` §5: lägg till den fjärde raden — facitklass och
   dömande motor (§1.3).
4. `docs/spec/00_index.md`: 72 mätningar och `51`–`55` saknas. Generera
   tabellen ur katalogen i stället för att föra den för hand — samma regel som
   `SKULDREGISTER.md` redan följer.
5. `tests/motbevis`: 26 gröna prov flyttas till `tests/enhet` enligt sin egen
   README, annars säger "SKA vara röda" inget.
6. `20_arv.md`: stämpla tabellen *OBEKRÄFTAD LÄSNING AV ANNAT REPO*. Ingen rad
   används som belägg.
7. `M-115`: LIMITS får raden *"gäller stimulus med en puls; M-122 §3 mäter 13
   av 30 fångade i bankens egna sekvenser"*.
8. `M-110`: datum, och en rad om vilka grindar varvet kör.

---

## §7 Det kortaste svaret

Kedjan finns och linan går. Grindarna är en textgrind och en beteendedomare, och
beteendedomaren är bättre än vi trodde i morse — 80 %, inte "knappt alls".
Nästan allt vi mätt mäter oss själva eller plattformen; ingenting mäter en
fabrik. Produkten är inte kodgeneratorn och inte layouten, för dem har andra.
Den är domaren som ser vad två stationer gör tillsammans och säger det till den
som skrev koden. Det är bevisat på handskriven kod och obevisat på en modells.
Satsning 1 avgör det. Allt annat väntar eller upphör.
