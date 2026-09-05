# M-116 — Nämnaren provad mot verkligheten

**Datum:** 2026-09-05. **Metod:** fyra parallella researchagenter (webbsökning
+ sidhämtning, ingen VC startad, ingen kod ändrad) plus egna
stickprovskontroller (samma sökningar körda oberoende, se §2). **Stämpel:**
**allt i det här dokumentet är DOK** enligt `docs/spec/01_kalldisciplin.md` —
ingenting är kört på den här maskinen mot en levande VC. Ett DOK-påstående får
aldrig ensamt bli ett designbeslut; det gäller varje rad nedan.

**Frågan:** `docs/matningar/M-100_personatackningen.md` mätte 63 % täckning av
228 arbetssteg över sju personaprofiler (`docs/spec/48_personaprofiler.md`).
M-100:s egen LIMITS-sektion sa rakt ut: *"Stegen är skrivna av mig, inte av en
användare... den största enskilda osäkerheten i nämnaren."* Det här dokumentet
är det första försöket att pröva den osäkerheten mot faktiskt publicerat
material: vem använder VC, vad tar tid, vad går fel, vilka personor saknas,
och vem mer bygger AI mot samma yta.

**Källkvalitet, rakt ut:** visualcomponents.com, forum.visualcomponents.com
och Capterra blockerade nästan all direkt sidhämtning (HTTP 403 / bot-vägg).
De flesta citat nedan kommer därför via sökmotorns egen textsyntes av sidan,
inte en rå läsning av sidan här. Där jag lyckades hämta en sida direkt
(Siemens, Rockwell, KUKA, ABB, EDAG, MDPI, TechCrunch) är det markerat
**hämtad**. Två av Fastems-siffrorna kontrollerade jag själv oberoende av
forskningsagenten (två separata sökningar, samma exakta citat kom tillbaka
båda gångerna) — det höjer tilltron till att citatet är äkta, men båda vägarna
går via samma sökmotorindex, inte en oberoende råläsning. Ingen siffra nedan
är stämplad högre än så.

---

## 1. Vem använder Visual Components, och till vad

**Riktiga namngivna roller ur VC:s egna kundcase** (alla: vendor case study,
inget publiceringsdatum synligt på sidan, hämtat via sökmotorsyntes,
2026-09-05):

| Företag | Namngiven roll | Vad de gjorde | URL |
|---|---|---|---|
| Sandvik | Markus Juntunen, **Production Development Engineer** | testade svetsräckvidd, standardiserade svetsprofiler via OLP | visualcomponents.com/case-studies/sandvik-boosts-welding-automation... |
| Ponsse | Asko Haataja, **Head of Robotics Team**; Heikki Selkälä, **Production Development Manager** | robotcellsprogrammering, 10 dagar → 1 dag (se §3) | visualcomponents.com/case-studies/ponsse-drives-forest-machine... |
| Denso Manufacturing Czech | Jaroslav Živnůstka **Digital Twin Trainee**, František Manlig **TIE Specialist**, Michal Humpolák **Technology Supervisor**, Vilém Bartoň **Production Engineering Section Manager** | läcktestgenomströmning | visualcomponents.com/case-studies/denso-manufacturing-czech... |
| Vaisala | Lorenzo Riggi, **Senior Automation Engineer** | simulerade ett mobilrobot-logistikcenter | visualcomponents.com/case-studies/vaisala-optimized... |
| KOCH Steuerungstechnik | Georg Schepers, **Commercial Director for Technical Sales**; Christian Koch, **Owner** | modulär anläggningsdesign, sälj | visualcomponents.com/case-studies/koch-steuerungstechnik... |

**Läsningen:** ingen av dessa titlar matchar de sju profilnamnen ord för ord.
De ligger nära (Production Development Engineer ≈ P4, Senior Automation
Engineer ≈ P1, Commercial Director for Technical Sales ≈ P5) men är alltid
**mer specifika och mer chefstunga** än profilnamnen. Ingen enda källa
använder frasen "robot programmer", "layout planner" eller "flow engineer".

**Capterra-recensenters egna titlar** (capterra.com/p/188853/Visual-Components/reviews/,
datum ej bekräftade, tredjeparts recensionssajt, **låg-medel tillit** — sidan
gick inte att hämta rått, bara via sökmotorsammanfattning): Manufacturing
Engineer, Project Manager (två oberoende recensenter), Head of project
managers, Principal Staff Automation Engineer, Automation Execution GM,
Simulation Engineer, Lean Production Engineer, Product Manager, Researcher.

**Den viktigaste enskilda upptäckten i det här avsnittet: "Project Manager"
förekommer FYRA gånger oberoende av varandra** — Wärtsilä-caset (Tero
Kujamäki, Project Manager for Marine Solutions), MAG-caset (Marcel Deess,
Project Manager Digital Factory/Automation) och två Capterra-recensenter. Det
är fler oberoende träffar än något av de sju befintliga profilnamnen fick.
**Ingen av de sju profilerna är en projektledare.** Se §5.

**Forumets kategoristruktur** (forum.visualcomponents.com, hämtat
2026-09-05, medel tillit — kategorinamn bekräftade, roller/datum inte):
Layout Configuration, Component Modeling, Process Modeling, Robot
Programming, .Net/Python Add-on Programming, eCat Updates, Webinars. Det
här är **uppgiftstyper, inte titlar** — men de täcker P1/P2/P4/P6 rimligt väl
och har ingen egen kategori för driftsättning (P3) eller sälj (P5), vilket
antingen betyder att de kategorierna inte finns som communityaktivitet eller
att de går under "General Questions".

**Varning om cirkularitet i den egna källan.** VC:s egen jobbannons för
**"Application Engineer (Simulation Expert)"** och **"OLP Application
Engineer"** (linkedin.com/jobs, VC:s eget bolag, hämtat 2026-09-05) beskriver
exakt P7:s uppdrag — "ensure that customers can use the products
successfully", "user trainings" — men det är **VC:s egen anställda**, inte en
kundroll. Om `48_personaprofiler.md` skrevs med VC:s egen dokumentation som
källa (vilket `47_verktygstackning.md` uttryckligen anger som en av källorna)
är det möjligt att P7 "Utbildaren" är formad efter VC:s supportpersonal,
inte efter en observerad kund. De akademiska fallen (Ohio Northern
University, se nedan) visar att människan i den rollen normalt är **en
professor**, inte en titulerad "tränare".

**Tredjeparts jobbannons som faktiskt namnger VC** (det enda hittade,
ziprecruiter.com, EDAG, hämtat 2026-09-05, medel tillit): "Senior Virtual
Commissioning Engineer" listar Visual Components som ett av fem likvärdiga
verktyg (jämte Process Simulate, DELMIA, Emulate3D, ISG-virtuos). Det är den
**enda** externa (icke-VC) jobbannonsen som nämner VC vid namn i hela
sökbudgeten. **P3:s profilnamn "Driftsättaren" är alltså det bäst belagda av
de sju**, eftersom det är det enda som matchar en riktig, extern titel.

**Akademi:** Ohio Northern University kör en simuleringskurs för
tredje/fjärdeårsstudenter i tillverkningsteknik sedan 2002 med
layoutdesign som slutprojekt (visualcomponents.com/blog, VC-publicerad källa,
ej oberoende bekräftad). En peer-reviewed konferensartikel om att integrera
VC i en robotikkurs existerar (ResearchGate, titel bekräftad, fulltext ej
läst).

**Kunde inte beläggas alls:** underhållstekniker, kvalitetsingenjör,
säkerhetsingenjör som VC-användare — noll träffar åt något håll (varken
bekräftande eller motbevisande). Vem som **betalar** licensen utöver ett
enda litet-bolags-exempel (KOCH: ägaren själv namngiven bredvid säljroll) —
generell B2B-köpteori (economic buyer ≠ end user) hittades men inget
VC-specifikt belägg för vem som sitter på den rollen hos en medelstor kund.

---

## 2. Vad tar tid

**Fastems-caset** (visualcomponents.com/case-studies/fastems-2/, inget datum
synligt, kund citerad: Mika Laitinen, Sales Manager Robotics — **dubbelkontrollerat: samma exakta citat kom tillbaka i tre oberoende
sökningar**, min egen plus forskningsagentens, men alla tre via
sökmotorsyntes av samma sida, aldrig en råläsning — medel tillit):

> "Robot programming time was reduced from an average of **3–4 days to only
> 2–3 hours**." — "Robotic cell setup... **5–10 days of manual programming
> work to 2 days**." — "we are able to do **90 % of programming in
> simulation**."

**EROWA-caset** (samma domän, medel tillit, ej oberoende dubbelkollad): en
statisk 3D-layout tar **~30 minuter**; med animerad robotrörelse **~4
timmar**.

**Den akademiska ankaren, tre oberoende publiceringar som pekar på samma
tal över 17 år:**

- Reinhart & Wünsch (2007), *Production Engineering* 1:371–379, citerar
  VDW-data: driftsättning tar **upp till 25 % av total projekttid**, och
  **upp till 60 % av driftsättningstiden** (≈15 % av total projekttid) går
  åt att **rätta felaktig styrmjukvara**. link.springer.com/article/10.1007/s11740-007-0066-0
  — fulltext bakom betalvägg, siffran känd via upprepade citeringar, medel
  tillit på magnituden, ingen tillit på metodiken (enkätunderlag? enstaka
  fall? tysk maskinbyggarbransch specifikt?).
- MDPI, aug 2024, **hämtad direkt**: "the commissioning phase can take up
  to 25 percent of the total project time" och **"software debugging is the
  main consumer of time in this phase"**. mdpi.com/2504-4494/8/4/165 — samma
  underliggande 2007-siffra återupprepad, inte en ny oberoende mätning.
- Raffaeli et al. (2022), MDPI *Applied Sciences* 12(6):3164, **hämtad
  direkt**: mäter 30 % cykeltidsminskning (101s → 71s) genom
  sekvensoptimering i en virtuell cell — mäter cykeltid, inte
  ingenjörstid, och ger **ingen** uppdelning per aktivitet trots att det är
  precis den typen av artikel som borde ha en.

**Rockwell/Emulate3D, ECM Technologies-caset** (rockwellautomation.com,
hämtad direkt, 2024-02-01, kundcase): 50 % kortare drifttsättningstid på en
Mexico-anläggning; upp till 5 månaders ledtidsvinst på ett annat projekt
genom parallell PLC-kodfelsökning via digital tvilling i stället för
sekventiell felsökning efter installation.

**Vad det säger, med resonemang, inte känsla:**

1. Varje siffra med en hård publicerad förbättring (Fastems, EROWA,
   Ponsse "10 dagar → 1 dag") handlar om **layout och robotbaneprogrammering
   som blir snabbt** — minuter till timmar, dagar till timmar.
2. **Ingen** publicerad siffra, varken från VC eller konkurrent, handlar om
   att **felsökning/signalintegration** blir snabbt. Ingen sådan
   före/efter-siffra hittades trots riktad sökning i hela forskningsbudgeten.
3. Den akademiska litteraturen säger tvärtom att felsökning av
   styrmjukvara är **"the main consumer of time"** i just den fas (P3,
   driftsättning) som M-100 mätte till 89 % täckning — högst av alla sju
   profiler.
4. **Slutsats, med angiven riktning men utan angiven multiplikator** (ingen
   tids-och-rörelsestudie på den granulariteten existerar publikt — det är i
   sig ett fynd): layout- och robotprogrammeringssteg (P1, P2 — 73 av 228
   steg) är sannolikt **överrepresenterade** i nämnaren relativt hur lite
   kalendertid de äter. Signalintegration/felsökning/idrifttagning
   (fördelat tunt över P3 och P4) är sannolikt **underrepresenterat** —
   inte för att de saknar steg, utan för att den verkliga aktiviteten
   ("felsök varför en signal kommer 4 sekunder sent") inte går att skriva
   som ett diskret steg alls. Se §7 för den konkreta kopplingen till
   specifika stegnummer.

---

## 3. Vad går fel

**Licensiering — bekräftat både externt och internt.** Externt: minst tre
oberoende forumtrådar om att licensservern slutar fungera eller inte går att
aktivera (forum.visualcomponents.com/t/floating-license-server-not-working-anymore/2326
m.fl., datum ej bekräftade, medel tillit) plus en Capterra-recensent
("Tomaž K.", Lean Production Engineer): "not possible to manage the time
when the application is available to users." **Internt, redan MÄTT i det
här repot:** `docs/spec/27_operatorsflodet.md:116` —
*"licensserverns feature mismatch är ett eget fel, inte platsbrist"* — och
memory-noten `vc-feature-mismatch` beskriver samma sak: fel
produkt/version på servern, inte fulla platser. **Det här är den starkast
belagda felklassen i hela dokumentet**, eftersom extern och intern källa
oberoende landar på samma sak. **Noll av 228 steg rör licensiering.**

**OPC UA / PLC-signalintegration — återkommande, 2018–2024+.** Minst fem
oberoende forumtrådar (forum.visualcomponents.com, medel tillit på datum,
hög tillit på existens/art): signaluppdateringslatens som skalar dåligt med
antal variabler (~20 ms vid 15–20 booleaner, 4–5 sekunder vid ~200
variabler — en tråd, ej oberoende bekräftad), struct/array-datatyper som
inte går att läsa över OPC UA, och en S7-1500-anslutning som slutade
fungera efter veckors drift utan kodändring. Det här ligger rakt i P3:s
domän — den profil M-100 mätte till 89 % täckning.

**Prestanda/krascher på stora scener — återkommande, flera versioner.**
Minst sex oberoende forumtrådar 2018–2024 (VC 4.2 kraschar vid filöppning,
VC 4.8 "very slow", lagg i VR-visaren vid stora layouter), korroborerat av en
oberoende Capterra-klagan om UI-svarstid vid fliknavigering. **Ingen av 228
steg nämner detta** — det är en verktygskvalitetsfråga, inte ett
arbetssteg, men det är obestridligen **"vad som tar tid"** för en verklig
användare.

**Kostnad och inlärningskurva** (Capterra, flera oberoende recensenter):
"the most expensive software ever purchased [in 45 years]"; "difficult to
get used to despite several days' training"; "quite complicated to set up
a big line."

**Robotkontrollerns precision — leverantörens egen reservation.**
VC:s egen blogg/FAQ (visualcomponents.com, medel-hög tillit — det är ett
medgivande mot eget intresse, starkare bevisklass än ett användarklagomål):
VC använder en **generisk** robotkontroller för cykeltidsuppskattning som
**"does not match the precision of ABB's actual virtual controller"**, och
rekommenderar en separat betald anslutning till robottillverkarens egen
virtuella styrenhet för millisekundnoggrannhet (svetsning, plockning).
**Kopplar direkt till P2 steg 32** ("mäta cykeltiden för banan", i dag
`saknas`/obyggd i M-100): även om verktyget byggs ger det ett tal reality
kan komma att underkänna för precisionsarbete, om det inte deklarerar vilken
kontrollermodell talet vilar på.

**Versionskompatibilitet — en enskild men konkret tråd** (dec 2024): modell
byggd i 4.8 Premium fungerar inte rätt i 4.10 Premium. En källa, räknas
inte som "återkommande" men är verklig och namngiven.

**Kunde inte beläggas:** ett konkret, namngivet fall där ett exporterat
robotprogram betedde sig fel på en riktig robot (bara den generella
precisionsreservationen ovan, ingen incidentrapport). Reddit gick inte att
söka alls (verktygsbegränsning, inte ett negativt fynd). G2/TrustRadius/
Gartner Peer Insights hade ingen hittbar VC-recensionssida.

---

## 4. Saknade profiler

**Bäst belagd ny persona: Projektledaren.** Fyra oberoende träffar (§1) mot
noll för någon av de andra kandidaterna. Uppgifterna en projektledare skulle
vilja ha — budget mot BOM, tidslinje mot leveransdatum, "hur ligger vi till"
— finns **inte** som egna steg i P5 (sälj), som bara har kostnadsrelaterade
steg riktade mot en offert, inte mot ett löpande projekt.

**Underhållstekniker, kvalitetsingenjör, säkerhetsingenjör.** Genuint
obelagda åt bägge håll — inte "de finns inte", utan "sökbudgeten hittade
ingenting, varken bekräftande eller avfärdande." Det ska stå kvar som en
öppen fråga, inte tystas ner till ett nej.

**Inköpare/IT-licensadmin.** Indirekt stöd: VC:s eget "Accounts dashboard"
för att "assign, revoke, and monitor licenses" (tredjepartslistning, låg
tillit, ej verifierat mot VC:s egen sida som blockerade hämtning) antyder en
roll skild från den dagliga användaren. Det är precis den roll som skulle
äga licensfelsklassen i §3.

---

## 5. Konkurrensen — påstått mot levererat

| Aktör | Produkt | Genererar den faktiskt (kod/layout)? | Status | Belägg |
|---|---|---|---|---|
| Visual Components | — | — | **Ingen AI-funktion hittad t.o.m. v5.1 (juni 2026)** | egen bloggindex + versionshistorik, medel tillit (403 på direkthämtning) |
| KUKA | iiQWorks.Copilot | **Ja — naturligt språk → cellayout** (placera robotar, transportörer, stängsel) | **Levererad**, sidan säger själv "in the coming months... expanding" | kuka.com, **hämtad direkt** — **närmaste direkta konkurrenten till hela projektets ambition** |
| Siemens | Engineering Copilot (TIA Portal) | Ja — genererar SCL-kod från naturligt språk | **Levererad sedan sommaren 2024** | siemens.com, **hämtad direkt**, egen produktsida |
| Rockwell | FactoryTalk Design Studio Copilot | Ja — genererar ladder-logik | **Levererad**, egen dokumentationssida (starkaste bevisklassen i tabellen) | rockwellautomation.com, **hämtad direkt** |
| Siemens | Plant Simulation Copilot | Nej — dokumentations-Q&A och vägledning | Levererad dec 2025, sidan säger själv "initial capabilities" | siemens blog, **hämtad direkt** |
| ABB | RobotStudio AI Assistant | Nej — vägledning ur manualbibliotek | Levererad sept 2025 | abb.com + therobotreport.com, **hämtad direkt** |
| Dassault DELMIA | "AI-assisted" robotik/bearbetning | Oklart | **Overifierat** — bara sökmotorsyntes, ingen råläsning | låg tillit, flaggat explicit |
| Startups (Forge IO PLC Copilot, Formic) | PLC-kod / cellayout från lidar | Påstått | **Overifierat** — enkällig, ingen tredjepartsbekräftelse | låg tillit |
| Akademi | Agents4PLC, LLM4PLC, m.fl. | Ja, som forskningsprototyp | Ej produkt | arXiv, flera 2024–2026 |

**Läsningen:** VC själv har inte byggt en konkurrerande AI-funktion (medel
tillit på den negativa slutsatsen — sidorna blockerade hämtning). Men **KUKA
levererar redan exakt den kapacitet det här projektets P1-ambition siktar
mot** (naturligt språk → cellayout), på en annan plattform. Och **Siemens
och Rockwell levererar redan** motsvarigheten till bankens ST-generering,
med egna dokumentationssidor — den starkaste bevisklassen i hela tabellen,
inte bara en presskommuniké.

---

## 6. Vilka av M-100:s 228 steg verkligheten inte känner igen — den viktigaste raden

Ingen extern källa publicerar en steg-för-steg-lista att jämföra rad för
rad mot `48_personaprofiler.md`, så det här är inte en direkt matchning.
Det är däremot en **riktad** slutsats ur §2–§4, och den pekar konsekvent åt
samma håll:

1. **P3 (driftsättaren, 35 steg, 89 % täckt — högst av alla sju) missar sin
   egen kärnsmärta.** Den mest återkommande, flerårigt belagda verkliga
   svårigheten i exakt den här domänen — OPC UA-latens som skalar fel,
   struct/array-begränsningar, tysta anslutningsavbrott — finns **inte**
   som ett enda steg bland P3:s 35. Steg 1–20 (signalinventering,
   signalkartor) är byggda och täckta; steget "diagnostisera varför en
   signal kommer fyra sekunder sent vid skalning" existerar inte i
   nämnaren över huvud taget. 89 % är sant för de steg som räknades, men de
   stegen är inte där den verkliga smärtan bor.
2. **P2 steg 32** ("mäta cykeltiden för banan", i dag `saknas`) är formulerat
   som om ett tal räcker. Leverantörens egen reservation (§3) säger att
   talet är fel för precisionsarbete utan robottillverkarens egen virtuella
   styrenhet — steget behöver en till dimension ("... och ange om talet är
   validerat mot en riktig styrenhet"), inte bara byggas som skrivet.
3. **Licensiering, prestanda/skalbarhet vid stora scener, och
   versionskompatibilitet vid filöppning är helt frånvarande ur alla 228
   steg**, trots att alla tre är återkommande, flerårigt belagda
   användarproblem — och licensieringsklassen är dessutom redan **MÄTT**
   internt i det här projektet (`27_operatorsflodet.md:116`). Det är inte
   en persona som saknas för dessa (de drabbar alla sju), det är en hel
   **kategori av arbetssteg** — "kontrollera att den här VC-installationen
   har förmågan innan du bygger på den", "återhämta dig efter en trasig
   licensserver", "öppna en gammal fil utan att den tystnar" — som
   `48_personaprofiler.md` aldrig skrev.
4. **P1 och P2 (73 av 228 steg, 32 % av hela nämnaren) beskriver den del av
   arbetet som §2:s siffror visar är snabbast i verkligheten** (minuter till
   låga timmar per Fastems/EROWA). Det gör dem inte fel som steg, men det
   betyker att 63 %-talet sannolikt lutar mot att vara **generöst** som ett
   mått på verklig tidstäckning, inte snålt — precis den riktning M-100:s
   egen LIMITS-rad varnade för utan att kunna säga åt vilket håll.
5. **En åttonde persona saknas med starkare belägg än de fyra M-100 redan
   namngav som öppna** (underhåll, kvalitet, säkerhet, inköp): projektledaren
   (§4), fyra oberoende träffar mot noll.

---

## LIMITS

* **Allt här är DOK, inte MÄTT.** Ingen sida lästes på den här maskinen mot
  en levande VC; nästan ingen sida gick ens att hämta rått (403 på
  visualcomponents.com, forum.visualcomponents.com, Capterra). Merparten av
  citaten kommer via en sökmotors egen textsyntes av sidan, inte en
  verifierad råtext. Det är en svagare bevisklass än den här kodbasens
  vanliga MÄTT/KOD@HEAD-stämplar, och ska behandlas så av nästa läsare.
* **Ingen tidsstudie på steg-nivå existerar publikt.** §2:s slutsats om att
  P1/P2 är överrepresenterade och P3/P4:s felsökning underrepresenterad är
  en **riktning**, härledd ur att (a) alla publicerade förbättringssiffror
  gäller layout/programmering och (b) den akademiska litteraturen säger att
  felsökning dominerar driftsättningstid. Ingen multiplikator, ingen
  procentsats för själva snedvridningen kan anges — det vore att gissa en
  siffra ingen har mätt.
* **Fastems- och EROWA-siffrorna är enda källor för VC-specifika tidstal.**
  Båda är leverantörens egna kundcase, sannolikt bästa-fall-exempel, inte
  medelvärden över ett typiskt projekt. Fastems-citatet dubbelkontrollerades
  över tre sökningar med identiskt ordval, vilket sänker risken för
  hallucination men inte höjer det till en oberoende källa — alla tre vägar
  går via samma underliggande sida.
* **Reddit gick inte att söka alls** (verktygsbegränsning i den här
  sessionen, inte ett negativt sökresultat). eng-tips.com, G2, TrustRadius
  och Gartner Peer Insights gav noll träffar för Visual Components
  specifikt — okänt om det beror på att diskussionen inte finns där eller
  att den inte var sökbar med den här budgeten.
* **De sju profilernas verkliga motsvarigheter är alltid mer specifika och
  mer chefstunga än profilnamnen** (§1). Ingen enskild titel matchade något
  profilnamn ord för ord. Det är svagt stöd för att strukturen (sju
  arbetsinriktningar) är rimlig, men inget stöd för att just de sju
  **namnen** eller deras exakta stegindelning är hämtade ur en verklig
  observation.
* **P7 "Utbildaren" kan vara formad efter VC:s egen anställda, inte en
  kund.** Den enda exakta titelmatchningen ("Application Engineer") är
  VC:s eget jobb, inte en kundroll. Det är en anmärkning om hur nämnaren
  troligen skrevs, inte ett bevisat fel i den.
* **Maintenance/kvalitet/säkerhet/inköp förblir genuint obelagda åt bägge
  håll.** Den här körningen varken bekräftar eller avfärdar att de
  personorna är verkliga VC-användare — sökbudgeten (~20 sökningar per spår)
  var inte uttömmande.
* **Konkurrensavsnittets negativa fynd om VC ("ingen AI-funktion")
  vilar på blockerad direktåtkomst till VC:s egna sidor.** Rekommenderat
  nästa steg om det blir designrelevant: fråga VC:s egen kontaktperson
  eller logga in på forumet/roadmapen direkt, i stället för att lita på den
  här sökningen som facit.
* **Ingen av de fyra forskningsspåren körde mer än ~20–48 sökningar var** —
  det är en avsiktligt sparsam budget (LEAN), inte en uttömmande genomgång
  av vare sig forumet, recensionssajterna eller konkurrentlandskapet.
