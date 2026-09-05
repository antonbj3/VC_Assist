# M-120 — betyder våra tillförlitlighetstal något jämfört med omvärlden?

**Datum:** 2026-09-05
**Typ:** kartläggning (DOK), ingen egen körning på den här maskinen.
**Bygger på:** `docs/research/R-01_llm_st_och_softplc.md` (2026-09-04, fyra
webbagenter, aldrig primärkällsverifierad) + denna körnings egen
primärkällskontroll av nio artiklar: fem `arXiv`-PDF:er hämtade och
textextraherade lokalt med `pdftotext`, resten kontrollerade via abstract-hämtning
och sökträffar. Rådata: `/tmp/claude-1000/.../scratchpad/plc_research/*.txt`
(overlever inte omstart — siffrorna nedan är destillatet).

## LIMITS

* **Ingen kod kördes.** Allt nedan är läsning av andras publicerade text, inte
  en mätning på vår maskin. Det är precis den distinktion `docs/spec/01_kalldisciplin.md`
  kallar DOK.
* **Fem artiklar fulltextverifierade** (LLM4PLC, Agents4PLC, AutoPLC, SemaPLC,
  PLCverif-abstract) genom att hämta PDF:en och köra `pdftotext -layout`,
  sedan `grep` mot exakta tal. Fyra till (Koziolek 2024, Spec2Control,
  Kersting/Rummel/Benndorf, ChatGPT-for-PLC/DCS 2023) kontrollerades bara mot
  abstract/sökträff, inte hela texten — deras siffror ovan är svagare belagda
  och märkta så i tabellen.
* **Tre titlar hittades men lämnades overifierade**: `LLM4SFC` (arXiv
  2512.06787), en IEEE-artikel "Generating PLC Code with Universal Large
  Language Models" (paywall, `WebFetch` fick tomt innehåll) och en tysk
  ResearchGate-post "ChatPLC". Ingen av de tre bidrar ett enda tal här.
* **Sökningen efter en icke-LLM-baslinje är en frånvaromätning.** Fyra
  riktade sökningar plus tre baslinjeavsnitt lästa i fulltext (AutoPLC §III-D,
  SemaPLC §5.3, LLM4PLC hela resultatdelen) hittade noll. Frånvaro av träff är
  inte bevis att ingen finns någonstans — bara att den inte syns för den här
  sökinsatsen.
* **`docs/research/R-01`s siffror höll vid stickprovskontroll** (se §0), men
  två av dess påståenden korrigeras här: Agents4PLC:s bänkstorlek och
  SemaPLC:s baslinjeidentitet (se §2 och §4).
* **`M-119` reserverar ett annat nummer, oberoende arbete** — ingen
  numerkrock, ingen innehållsöverlappning.

---

## §0 — Vad som redan var mätt, och vad den här körningen lade till

`docs/spec/70_faser.md` rad för fas 11 (**PASSERAD, M-62**) säger redan:

> *"`R-01`: ingen har publicerat vår loop, ingen leverantör publicerar ett
> korrekthetstal, och varje akademiskt tal är kompileringsgrad på en annan
> uppgiftsmängd. Att ställa vårt tal mot LLM4PLC:s 72 % vore samma kategorifel
> operatören redan fångat en gång."*

Den slutsatsen står kvar. Vad den här körningen gjorde utöver `R-01`:

1. Hämtade fem artiklars faktiska PDF och läste tabellerna i klartext i
   stället för att lita på en sammanfattning av en sammanfattning.
2. Hittade att **Agents4PLC:s bänk har två olika storlekar i omlopp** — 23
   uppgifter i den version `AutoPLC` och `R-01` citerar, 117 i den version
   `SemaPLC` citerar som "Liu et al., 2026" (se §2).
3. Namngav **exakt vilka tre metoder** som utgör SemaPLC:s "baslinjer 22,4–31,4"
   — `R-01` kände bara till intervallet, inte namnen (se §4).
4. Hittade en primärkälla som **säger rakt ut** att en av de tre stora
   arbetena inte har släppt sin uppgiftsmängd (LLM4PLC — se §2), vilket är ett
   starkare belägg för "ingen öppen bänk" än `R-01`s formulering.
5. La till två artiklar `R-01` inte nämnde (Koziolek/Gruener/Ashiwal 2023,
   den tidigaste i fältet; samt Spec2Control i egen rätt, inte bara som
   SemaPLC:s källa för sina 65 uppgifter).

---

## §1 — Publicerade arbeten, med nämnare och domare utskrivna

| Arbete | Författare · år · status | Uppgiftsmängd (n) | Domare | Vad talet **faktiskt** mäter | Huvudtal | Belägg |
|---|---|---|---|---|---|---|
| **ChatGPT for PLC/DCS Control Logic Generation** | Koziolek, Gruener, Ashiwal (ABB) · maj 2023 · `arXiv:2305.15809`, **förtryck** | 100 promptar, 10 kategorier | mänsklig genomläsning, ingen kompilator, ingen körning | om texten *ser ut* som giltig ST och modellen resonerar vettigt — rent kvalitativt | inget procenttal alls | abstract |
| **LLM4PLC** | Fakih, Dharmaji, Moghaddas, Quiros Araya, Ogundare, Al Faruque (UC Irvine + Siemens Technology) · `arXiv:2401.05443` · **ICSE-SEIP 2024, granskad industrispår** | **40** dedikerade testfiler (tränat på 596 OSCAT-prover, LoRA) | egen kompilator/grammatikkontroll + nuXmv-verifierare; kvalitet av expertpanel (antal bedömare ospecificerat) | **kompilerar/verifieras**, inte beteende i drift | 47 % → 72 % pass rate; kvalitet 2,25→7,75/10 (GPT-4) | **fulltext**, `llm4plc.txt` |
| **Agents4PLC** (2024-versionen) | Liu, Zeng, Wang, Peng, Wang m.fl. (Zhejiang) · `arXiv:2410.14209` · **förtryck**, ingen venue funnen | **23** uppgifter (16 lätta, 7 medel) | formell verifiering via nuXmv/PLCverif mot handskrivna properties | **verifierbarhet mot en property**, inte fritt beteende | lätt 50,0 % pass / 68,8 % verifierbar; medel 28,6 % / 42,9 % | **fulltext**, `agents4plc.txt` |
| **AutoPLC** | Yang, Wu, Zhang, Zhang, Liu, Lian, Ren, Tian, Che (Beihang + Siemens Kina) · `arXiv:2412.02410` · **förtryck** | **914** (OSCAT 718 + Siemens LGF 151 + tävling 45) | egen kompilering mot Siemens TIA Portal / CODESYS, direkt mot leverantörens IDE | **kompilerar i en riktig IDE**, inte beteende | OSCAT 92,90 %, LGF 92,72 %, mot GPT-4o 35,47 %/8,61 % | **fulltext**, `autoplc.txt` |
| **Koziolek m.fl., LLM-genererade testfall** | Koziolek, Ashiwal, Bandyopadhyay, K R (ABB) · `arXiv:2405.01874` · maj 2024 · **förtryck** | 10 OSCAT-funktionsblock, 5–10 testfall/block | egen körning: MatIEC → GCC → egen mjuk-PLC, täckning via GCOV | **om modellens EGNA testfall/assertions är korrekta**, en helt annan fråga än om modellens PLC-KOD är korrekt | 0–50 % korrekta assertions, sämst på timers/tillstånd | abstract |
| **Haag m.fl., DPO-träning** | `arXiv:2410.22159` · **förtryck** | Phi-3-medium-14B, 200 utvärderingsintentioner (100 OSCAT, 100 APPS→ST) | RuSTy-kompilator + GPT-4 som semantikdomare | kompilering **och** en LLM som dömer en annan LLM:s semantik — dubbel modellberoende | kompilering 7 %→~70 %, semantik ~45 %, gemensamt ~39 % | abstract/sökträff (ej fulltextläst denna gång) |
| **Spec2Control** | Koziolek m.fl. (ABB) · `arXiv:2510.04519` · okt 2025 · **förtryck** | 10 anläggningsnarrativ, **65** testfall | ABB:s eget verktyg dömer kopplingsnoggrannhet — **ingen körning, ingen anläggningsmodell** | om rätt styrstrategi/larm kopplas till rätt punkt i en ritning, inte om det fungerar i drift | strategidetektion 100 % (GPT-5), koppling 98,6 %, larm 97,1 % | sökträff |
| **Kersting, Rummel, Benndorf (Mitsubishi Electric Europe + Fraunhofer)** | `arXiv:2511.09122` · nov 2025 · **förtryck** | 100 frågor per konfiguration, GX Works3/iQ-R | kompilering i leverantörens egen IDE | kompilerar, inte beteende | GPT-5+RAG 87 %, GPT-4.1+RAG 73 %, GPT-4.1 utan RAG 38 % | sökträff (ej fulltextläst) |
| **PLCverif (CERN)** | Lopez-Miguel, Tournier, Fernandez Adiego · **ICALEPCS 2021, granskad**, `arXiv:2203.17253` (postprint 2022) | — (verktygsstatusartikel, inget benchmark) | verktyget är självt domaren i andra arbeten | språktäckning för formell verifiering, inte en kodgenereringsmätning | STL ~66/~55 %, SCL ~40/~25 % (siffrorna kom ur `R-01`, ej återfunna i denna körnings abstract-hämtning — **ej fulltextverifierade nu**) | abstract, siffror overifierade denna gång |
| **SemaPLC** | Tu, Wang, Zhou, Zhou, Zhu, Chen, Chen, Zhou, Zhou, Yang, Mou, Zhang, Xu (Midea AIRC/KUKA/SJTU/ZJU) · `arXiv:2608.18565` · aug 2026 · **förtryck**, öppen kod (MIT) på GitHub | **117** POU-uppgifter (Agents4PLC-bänken, 2026-versionen, 43 av 117 reparerade av PLC-ingenjörer efter granskning) + **65** projektuppgifter (Spec2Control-bänken) | tre lager: kompilering, statisk assertion-matchning (textmönster, **ingen körning**), **dynamiskt beteende** = riktig runtime, upp till sex scenarier, spårjämförelse mot facit | det enda talet i hela tabellen som mäter **beteende i drift**, inte bara kompilering | funktion: 72,6 % medel (bäst 82,1 % GPT-5.5) mot starkaste baslinje 63,9 %; projekt dynamiskt beteende: 52,2 mot baslinjer 22,4–31,4 | **fulltext**, `semaplc.txt` |

**Nämnaren-disciplinen tillämpad:** varje "%" ovan har sin denominator i samma
cell. Ingen procent utan sin nämnare finns i den här tabellen; om en saknas i
en källa (Spec2Control, Kersting) står "sökträff" i belägg-kolumnen som
varningsflagga.

---

## §2 — Finns en öppen bänk som fler än ett lag kört mot?

**Nej, med ett viktigt tillägg `R-01` inte hade:** primärkällan säger det rakt
ut. AutoPLC-artikeln, §I (fulltext, `autoplc.txt` rad 82–86):

> *"Fakih et al. [11] evaluate their approach on a small subset of the OSCAT
> IEC 61131-3 library (i.e., 40 samples) […] Liu et al. [34] develop a custom
> benchmark tailored to ST-specific features, but only 23 programming tasks
> are publicly released."*

Och tidigare i samma stycke om LLM4PLC specifikt: deras dataset
**"did not release their datasets, limiting transparency and reproducibility"**
(rad 84). Det är den starkaste tillgängliga bekräftelsen: en av de tre stora
arbetena har enligt en konkurrerande grupp inte ens släppt sin uppgiftsmängd.

**Fyndet som inte fanns i `R-01`: samma bänk bär två olika storlekar.**
Agents4PLC citeras som **23 uppgifter, "publicly released"** i AutoPLC-artikeln
(inlämnad dec 2024, reviderad aug 2025) — men SemaPLC (inlämnad aug 2026)
citerar **"the Agents4PLC benchmark (Liu et al., 2026)"** med **117** uppgifter,
varav "PLC-ingenjörer granskade och reparerade 43 av 117" defekta properties.
Det är alltså inte samma frusna facit: bänken har växt eller bytt version
mellan de två citeringarna, och ingen av de två artiklarna jag läste säger
uttryckligen vilken relation 23-versionen har till 117-versionen (om det är
en utökning, en omarbetning, eller en annan artikel av samma författare med
samma namn). **Overifierat: exakt vad "Liu et al., 2026" är för publikation.**

AutoPLC:s egen 914-uppgiftsbänk är den mest öppna som hittades — "we release a
replication package containing the benchmark, source code, and experimental
results" (`github.com/cangkui/AutoPLC`) — men **ingen annan artikel i den här
kartläggningen har kört mot den**. SemaPLC körde AutoPLC:s **verktyg** som
baslinje mot SemaPLC:s **egen** bänk (117+65), inte mot AutoPLC:s 914 uppgifter.
Så även den mest öppna bänken i fältet saknar ett andra lag som kört mot den.

**Slutsats: ingen bänk i det här fältet är körd av mer än ett oberoende lag
mot samma facit.** Det närmaste är SemaPLC, som återimplementerade och körde
om tre andra publicerade verktyg (LLM4PLC, AutoPLC, Agents4PLC) mot en gemensam
uppsättning — men det är ett lag som testar tre andras verktyg, inte tre lag
som testar mot samma låsta facit. En genuint öppen, community-delad
PLC-kodgenereringsbänk (i stil med HumanEval för Python) hittades **inte**;
en bred sökning efter delade kodgenereringsbänkar (HumanEval, MBPP, APPS,
LiveCodeBench, DS-1000) bekräftar att PLC/ST helt saknas från den listan.

---

## §3 — Vad mäter beteende, inte kompilering?

**SemaPLC:s "dynamic behavior"-mått är det enda i tabellen ovan som är nära
vårt öga**, och det går att säga exakt hur, ur fulltexten (`semaplc.txt`
rad 341–345):

> *"Dynamic behavior D compares sampled runtime traces: candidate and
> reference run in identical harnesses on a live runtime under up to six
> scenarios T. Each scenario scores the fraction of core output ports whose
> traces agree with the reference's, exactly for booleans and numerics; D is
> the mean scenario score. […] a compilation, deployment, timeout, or
> missing-trace failure on either side scores 0."*

Det vill säga: verklig runtime, verkliga in/utsignalspår, jämfört med ett
facitspår, nollpoäng om det inte ens kör. Det är **spårjämförelse**, samma
grundval som `docs/spec/61_st_generering.md` redan valt för oss (facit = spår,
inte text) — men deras spår kommer ur **upp till sex syntetiska scenarier per
uppgift**, inte en 3D-anläggningsmodell. Det finns ingen fysik, ingen scen,
ingen kollisionsdomare i det de kallar "dynamic". Vårt öga (`M-86`–`M-88`) dömer
mot en körande VC-scen med objektspositioner över tid — ett strängare och
bredare facit än sex I/O-scenarier, men **samma familj av idé**: kör koden,
jämför spår, döm inte på text.

Ingen annan artikel i tabellen har ett körande beteendemått. Spec2Control är
explicit **utan** körning ("no execution, no plant model" står bokstavligen i
sökträffen). Koziolek 2024 kör kod, men dömer modellens **egna testfall**, inte
om PLC-koden gör rätt sak mot ett oberoende facit — en annan fråga helt.

---

## §4 — Vår baslinjes ställning: gör andra en icke-LLM-baslinje?

**Nej — inte i något av de nio arbeten som lästs här, och det gick att slå
fast namngivet, inte bara som ett intervall.**

`R-01` visste bara att SemaPLC:s baslinjer låg på 22,4–31,4 utan att veta vilka
de var. Den här körningen läste tabell 1 och 2 i SemaPLC:s fulltext
(`semaplc.txt` rad 327–332, 391–397):

> *"Baselines are the three strongest published systems from Related Work […]:
> LLM4PLC (Fakih et al., 2024); AutoPLC (Yang et al., 2025) […]; and
> Agents4PLC (Liu et al., 2026), a faithful reimplementation."*

**Alla tre är språkmodellsberoende metoder.** SemaPLC:s "baslinje" betyder
"den näst bästa LLM-pipelinen", inte "utan språkmodell". Samma mönster upprepas
i AutoPLC:s eget baslinjeavsnitt (`autoplc.txt` rad 345–348): *"We compare
AutoPLC against state-of-the-art baselines, including LLM4PLC, Agents4PLC,
MapCoder, and several widely-used general LLMs."* MapCoder är en generell
LLM-kodagent. Ingen rad, i något av de tre baslinjeavsnitt som lästes i
fulltext, nämner en regelbaserad, mall-baserad eller på annat sätt
språkmodellsfri generator.

Fyra riktade sökningar (klassisk baslinje, regelbaserad baslinje,
"template-based"/"without a language model" i PLC-ST-sammanhang, öppen
kodgenereringsbänk i allmänhet) gav ingen enda träff på en publicerad
PLC-kodgenereringsstudie med en modellfri baslinje.

**Detta är en frånvaromätning, inte ett bevis om hela fältet** (LIMITS ovan).
Men den är forcerad på tre oberoende ställen (LLM4PLC:s egna jämförelser,
AutoPLC:s baslinjeavsnitt, SemaPLC:s baslinjeavsnitt) och faller noll gånger.
`M-62`s ärlighet — en generator utan en enda modellparameter, körd mot samma
domare, samma bank, samma budget — är **inom det underlag som gicks igenom
här** den enda av sitt slag. Den ärliga formuleringen: **"vi hittade ingen,
efter att ha läst tre baslinjeavsnitt i fulltext" är starkare än "det finns
ingen"**, och det är den mening som ska stå i varje vidare referens till det
här fyndet.

---

## §5 — Vad skulle krävas för att våra tal ska gå att jämföra?

Tre konkreta vägar, i stigande kostnad:

1. **Kör vår loop mot Spec2Control:s 65 uppgifter (eller Agents4PLC:s
   117-uppgiftsversion).** Kostnad: uppgifterna är i ABB:s
   styrnarrativ-format/Agents4PLC:s POU-format, inte vårt `bank/uppgifter/*.json`
   — en översättningsinsats per uppgift, och en risk att formatet inte bär
   samma villkorstyper som vår bank kräver (flank/latch, tidsvakt). Ingen av
   bänkarna är släppta i det format vi kan köra direkt (se `§2`, LIMITS).
   **Föroreningsspärren i `R-01` §1.5 gäller**: dessa uppgifter får inte tas in
   i vår egen bank, bara köras som ett externt facit vid sidan om.
2. **Ge en av deras metoder (AutoPLC, öppen kod) vår bank att köra på.**
   Kostnad: deras verktyg är byggt mot Siemens TIA Portal/CODESYS, inte
   STruC++/OpenPLC. Att koppla in det kräver antingen en av de vendor-IDE:erna
   (Windows, licens) eller en anpassning av deras verktyg mot vår
   kompilatorkedja — en icke-trivial port, inte en konfigurationsändring.
3. **Publicera vår bank + domare som en tredje öppen ingång**, i linje med
   fyndet i `§2` att ingen sådan finns. Det är den enda av de tre vägarna som
   inte kräver att vi böjer oss efter någon annans format, och den enda som
   adresserar `§2`s huvudfynd direkt: **det finns fortfarande ingen bänk någon
   utomstående kan köra mot oss med.** Kostnad: att skriva ett släppbart
   facit-format och en körbar harness för utomstående — en substantiell insats,
   men den enda som ger en jämförelse där **vi** inte är den part som anpassar
   sig till en annan bänks svagheter (t.ex. Agents4PLC:s 43 av 117 defekta
   properties, upptäckta av SemaPLC:s egen granskning).

Ingen av de tre är gjord. Alla tre kostar mer än en eftermiddag.

---

## Vad jag inte kunde belägga

* **PLC-GPT** som namngiven artikel eller modell — hittades inte i någon
  sökning. Antingen existerar den under ett annat namn, är för ny för
  sökindexet, eller finns inte som publicerat arbete.
* **PLCverif:s exakta täckningsprocent** (STL ~66/~55 %, SCL ~40/~25 %) —
  `R-01` anger dessa, men den här körningens egen abstract-hämtning av
  `arXiv:2203.17253` återgav dem inte. Inte motbevisat, bara overifierat på
  nytt.
* **Haag m.fl.:s exakta 9-DPO-iterationssiffra** och Kersting/Rummel/Benndorfs
  procenttal — bara sökträffar denna gång, ingen fulltext.
* **Vad "Liu et al., 2026" (117-uppgiftsversionen av Agents4PLC) faktiskt är
  för publikation** — journalversion, ny artikel, eller en uppdaterad
  arXiv-revision jag inte hittade.
* **Om `bank/README.md`:s omtvistade 17,3 %/7,1 %-tal** (flaggat redan i
  `R-01` §3) går att belägga — inte omprövat här, ligger utanför den här
  frågan.
* **Tre titlar** (`LLM4SFC` arXiv 2512.06787, en IEEE-artikel om PLC-kod från
  "universella" LLM, en tysk ChatPLC-post) — hittade men aldrig öppnade.
  Kan innehålla en icke-LLM-baslinje eller en öppen bänk; overifierat åt
  båda hållen.

## Den viktigaste raden

**Vårt tal är inte jämförbart med något enda tal i tabellen ovan — varken
LLM4PLC:s 72 %, AutoPLC:s 92,9 % eller SemaPLC:s 52,2 — av samma skäl `R-01`
redan gav: olika uppgiftsmängd, olika domare, olika n.** Det enda som ÄR
jämförbart är en **struktur**, inte ett tal: SemaPLC mäter sin egen
"harness-effekt" som skillnaden mellan en bar modell och modellen med hela
verifieringsloopen (Table 1, `bare` mot `full`) — precis den form `M-96`
redan har, `0 av 20` mot `6 av 20` (utan grindregler mot med), och `M-52`s
`3 av 4` i flerskott. Ingen av dem delar en enda uppgift, en enda domare eller
en enda modell med SemaPLC. Men **båda mäter samma sak i grunden: hur mycket
en verifieringsloop tillför över en bar modell** — och det är den enda giltiga
meningen där orden "liknar SemaPLC" får skrivas, aldrig framför ett procenttal.
