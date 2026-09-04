# M-64 — vad användaren ser medan det arbetar, och de sju rapportytor som inte var till honom

**Datum:** 2026-09-04
**Körs av:** `python3 -m pytest tests/enhet/test_forlopp.py tests/enhet/test_forlopp_kallor.py -q`
**Bygger:** `svc/vc_assist_svc/forlopp/`
**Fas:** 17 i `docs/spec/70_faser.md` — den enda fas som riktar sig till någon
utanför bygget.

**Kravet, ordagrant:** *"Ja missa inget här nu i logiken hur allt ska hänga
ihop med plc, till user input och allting liksom, användaren vill förmodligen
också gärna kunna veta vad som händer också när saker arbetar."*

---

## 1. Glappet, som tal

Räknat på `973a550`, alltså före den här mätningens egen kod.

### 1.1 Rapportytorna

Systemet har sju ställen där en körning berättar hur det gick. Frågan fasen
ställer är inte om de finns, utan om någon av dem når **användaren medan
körningen pågår**. Ytan måste vara två saker samtidigt: läsbar för en
människa, och läsbar **före** slutet.

| Rapportyta | Ger text? | Går att läsa under körning? |
|---|---|---|
| `Kopplare.sammanfattning` | nej, `dict` | **ja** — anroparen kör `kor_varv()` själv |
| `Ogonkoppling.sammanfattning` | nej, `dict` | **ja** — drivs av kopplaren |
| `Stationsdom.text` | ja | nej — `granska_station()` returnerar vid slutet |
| `Reparationsprotokoll.text` | ja | nej — `Reparationsslinga.kor()` returnerar vid slutet |
| `plan.Protokoll.till_json` | nej, `dict` | nej — `Korare.kor()` returnerar vid slutet |
| `Turprotokoll.text` | ja | nej — `Harness.kor()` returnerar vid slutet |
| `guldgrind.Beslut.text` | ja | nej — ett anrop vid slutet |

| | antal |
|---|---:|
| rapportytor totalt | **7** |
| ger text en människa läser | 4 |
| går att läsa medan körningen pågår | 2 |
| **båda samtidigt** | **0** |

Noll av sju. Det är hela fasen i ett tal.

Talet har en förklaring som är värd att skriva ut: i `svc/` finns **noll**
återanrop, observatörer eller lyssnare. Sökningen på
`callback|observer|lyssnare|notify` ger två träffar, och båda är annat:
`observerad_dom` i verifieringen, och ordet `lyssnare` inuti en sträng med
genererad VC-kod. Varje rapportyta är därför per konstruktion terminal. Ingen
har byggt fel — ingen har byggt det alls.

### 1.2 Vad `27_operatorsflodet.md` lovar

Dokumentet är 308 rader och lovar en panel i detalj.

| Vad | Lovat | Byggt |
|---|---:|---:|
| grindar `F-G1`–`F-G11` | 11 | **0** nämnda i `tests/` |
| regler `F-1`–`F-9` | 9 | 0 mekaniserade |
| steg i §5:s genomlopp, vart och ett med ett fält operatören ser | 14 | — |

`26_appen.md` är 329 rader och specar ytan:

| Vad | Lovat | Byggt |
|---|---:|---:|
| grindar `A-G1`–`A-G10` | 10 | **0** nämnda i `tests/` |
| regler `A-1`–`A-9` | 9 | 0 mekaniserade |
| godkännanderegler `G-1`–`G-7` | 7 | delvis, i kön |
| panelens fält | 7 | se §3.3 |
| panelens adress `127.0.0.1:8902` | — | **0** träffar i kod |

`24_samtalsloopen.md` §7 kallar sin händelselista **sluten**:

| Vad | Lovat | Byggt |
|---|---:|---:|
| händelsenamn i den slutna listan | 17 | **2** finns som sträng i `svc/` eller `ext/` |
| `TYSTNADSTAK` | 5 s | **0** träffar i kod |

De två som fanns — `VERKTYG_FEL` och `OMSKRIVNING` — ligger i
`harness/loop.py:SORTER`, som är ett **annat** ordförråd med fem egna sorter
(`AVVISAD`, `VERKTYG_OK`, `STOPP`, `KLAR`, `VARNING`). Överlappningen är alltså
en tillfällighet i namnvalet, inte den specade listan.

### 1.3 Sammanfattat

Operatörsflödet är **specat och obyggt**. Det är inte halvbyggt: ingen av de
21 grindarna i de två dokumenten är nämnd i ett enda prov, och ingen av de 15
händelserna som saknades finns någonstans. Vad som finns är sju
rapportytor — och de rapporterar till oss.

---

## 2. Vad som byggdes

`svc/vc_assist_svc/forlopp/`, fyra moduler och 78 prov.

| Modul | Äger |
|---|---|
| `handelser.py` | lägena, den slutna händelselistan, ovissheten |
| `yta.py` | `Forlopp` — protokollet som förs MEDAN körningen pågår — och `rendera()` |
| `grind.py` | `granska()`, elva regler |
| `kallor.py` | hur kopplaren, stationsgrinden, reparationsslingan, ögonkopplingen, guldgrinden och planen matar förloppet |

### 2.1 Grinden dömer PARET, inte renderaren

`granska(forlopp, text)` tar två saker: vad som faktiskt hände, och den text
en renderare producerade. Den dömer texten mot protokollet.

Det är designens enda verkligt viktiga val, och skälet är att fasen är sist i
kön men inte sist i tiden. Ytan kommer att flyttas — till en terminal, till en
webbsida på `127.0.0.1:8902`, till något vi inte har tänkt på. En grind som
dömer *renderaren* skulle behöva skrivas om varje gång. En grind som dömer
*texten* fäller också en renderare som inte är skriven än.

Därför byggs ingen webbsida här. Det är inte försiktighet: ett fönster nu
låser ett beslut `26_appen.md` §7 uttryckligen lämnar öppet, och grinden
binder ändå ytan den dagen fönstret byggs.

### 2.2 Lägena är härledda, och FALLET är absorberande

Ett läge som går att **sätta** går att sätta fel. `Forlopp.lage` räknas fram
ur händelserna varje gång den läses, i den här ordningen:

    FALLET  >  AVBRUTET  >  KLART  >  VÄNTAR PÅ OPERATÖREN  >  TYST  >
    ARBETAR  >  EJ STARTAT

`FALLET` först, med flit. En körning som fallit och som sedan levererar ett
`SVAR` är inte klar — den är fallen med ett svar. Provet
`test_ett_svar_efter_ett_fall_gor_inte_korningen_klar` håller den ordningen.

Två lägen är värda var sitt ord.

**`VÄNTAR PÅ OPERATÖREN`** är inte arbete. En plan som står i
godkännandekön arbetar inte, och en visning som säger att den gör det låter
operatören vänta på sig själv.

**`TYST`** är inte heller arbete. Det betyder att systemet inte vet om något
arbetar, och det är ett ärligare besked än båda alternativen.

---

## 3. Formen, och vad den kostar

Formen är katalogsökningens (`M-60`), och det är inte en tillfällighet: båda
svarar på frågan *hur säger man något utan att se mer uttömmande ut än man är*.

1. **Rader, inte JSON.** Klammer bär ingen information för den som läser.
2. **Alltid "N totalt, visar M".** En visning som inte säger hur mycket den
   inte visade ser uttömmande ut.
3. **`saknas` är ett förstklassigt svar.** Ögat som inte kört står som
   `saknas`, aldrig som tomt och aldrig som noll.
4. **Ett fällt läge ser ut som fällt.** Fasens egen regel, och §3.2 nedan.

### 3.1 Mätt kostnad

| Läge | tecken | rader | andel om ovisshet | andel andras ord |
|---|---:|---:|---:|---:|
| `ARBETAR` | **1 362** | 31 | 44 % | 0 % |
| `FALLET` | **2 321** | 47 | 39 % | 12 % |
| `KLART` | **2 457** | 65 | 24 % | 26 % |
| `ARBETAR`, 204 händelser | **1 608** | 40 | — | — |

Sista raden är trimningen. Otrimmad hade samma körning kostat **8 481
tecken**; med taket `MAX_HANDELSERADER = 12` kostar den 1 608, och visningen
skriver ut att den dolde 192 rader.

Att mellan en fjärdedel och nästan halva ytan handlar om vad vi **inte** vet
är avsikten, inte ett mätfel. `50_grindar.md`: ögat är felfinnande, aldrig
bevis.

Ingen egen rad är bredare än **100 tecken**, så visningen ryms i ett normalt
terminalfönster utan att bryta rader själv. Någon annans ord räknas inte —
de skrivs ordagrant och får vara hur breda som helst. Provet
`test_ingen_egen_rad_ar_bredare_an_ett_terminalfonster` håller gränsen, och
den fällde tre rader när den skrevs.

### 3.2 Grindens ord trimmas aldrig

En händelse som bär någon annans ord — en grinds utdata, ögats domstext,
kopplarens felmening — trimmas aldrig bort, oavsett tak. Den skrivs dessutom
**rått**, utan indrag och utan radprefix, mellan två markörrader.

Det senare är ett medvetet fult val. Prefixar man varje rad med `| ` finns
grindens sträng inte längre i texten, och då går det inte att kontrollera att
den kom fram hel. `reparation.standardinramning` gjorde samma val av samma
skäl.

### 3.3 Vad ytan täcker av panelens sju fält

| # | Fält i `26_appen.md` §3 | Förloppsytan |
|---|---|---|
| 1 | Samtalet | **nej** — ytan bär uppdragets mening, inte historiken |
| 2 | Planen, status per steg | **ja** |
| 3 | Kön | **delvis** — `qid` och `desc`; koden visas inte |
| 4 | Kör nu, med förfluten tid | **ja** |
| 5 | Ögats dom, ordagrant | **ja** |
| 6 | Guldnivån | **ja** |
| 7 | Systemläget (brygga, port, RTT, förmåga) | **nej** — ytan känner inte bryggan |

Fyra av sju hela, ett halvt, två inte alls. De två som saknas kräver en
levande brygga och hör därför till samma mätning som `A-G4`.

---

## 4. Fyndet: ett hjärtslag som räknas som framsteg gör en död körning odödlig

`24_samtalsloopen.md` §7 kräver en hjärtslagshändelse när tystnaden
överskrider `TYSTNADSTAK`. Det som **inte** står där är vad hjärtslaget gör
med tystnadsmätningen.

Mätt: 600 hjärtslag, ett i sekunden, i en körning där ingenting annat händer.

| Räknas hjärtslaget som framsteg? | Läget säger ARBETAR i | Slutläge |
|---|---:|---|
| **nej** (vårt val) | **5 av 600** | `TYST` |
| ja | **600 av 600** | `ARBETAR` |

De fem är de fem första sekunderna, som ligger inom `TYSTNADSTAK = 5 s`. Där
är `ARBETAR` rätt svar.

I den andra raden nollställer varje puls tystnadsklockan, och körningen står
kvar på `ARBETAR` i all evighet. Det är exakt den snurrande symbol som
`26_appen.md` §5 punkt 3 förbjuder — bara att den snurrar på grund av en
mekanism som fanns till för att göra visningen ärligare.

Tystnaden mäts därför från den senaste **verkliga** händelsen, och
`HJARTSLAG` är inte en sådan. Grinden räknar dessutom om det själv i stället
för att fråga protokollet: det är just definitionen som kan vara fel, och en
grind som frågar den den dömer mäter till slut sig själv.

---

## 5. De tre trasiga fixturerna fasens grind kräver

Alla tre är skrivna som någon skulle skriva dem i god tro.

| Trasig renderare | Vad den gör | Utfall | Regler som bröts |
|---|---|---|---|
| **snurrar vidare** | frågar efter det pågående steget och skriver ut hur länge det pågått — utan att först fråga vilket läge körningen är i | **FÄLLD** | `Y1`, `Y2`, `Y4`, `Y11` |
| **skriver om grinden** | kortar lång grindutdata till första raden, normaliserar radbrytningar och byter fackspråket mot en vänlig mening | **FÄLLD** | `Y4` |
| **utelämnar ärligheten** | skriver ut ögats text **ordagrant** men utelämnar beskedet att `SECTION HONESTY` aldrig fanns | **FÄLLD** | `Y6` |

Den tredje är den lömskaste. Den ljuger inte om ett enda ord. Den utelämnar
bara att ärlighetsgrinden aldrig kört, och då ser domen ut som en dom.
Guldgrinden har samma regel och av samma skäl: en rapport utan `HONESTY` har
ingen ärlighetsgrind alls, och den såg ut som guld.

Två fixturer till hör hit, för de fångar fel som ingen renderare kan laga:

| Trasig källa | Vad den gör | Utfall |
|---|---|---|
| **sammanfattande källa** | kortar grindens utdata redan när förloppet förs | **FÄLLD** av `test_forlopp_kallor.py` |
| **slukat kopplarfel** | fångar `Kopplarfel` och låter förloppet stå kvar på `ARBETAR` | **FÄLLD**: `kor_kopplaren` gör fallet till en händelse |

Den sista är värd en rad. Grinden kan **inte** se den, för där ljuger inte
texten — protokollet ljuger. Skyddet är att fallet blir en händelse, och det
provas där i stället.

### 5.1 Reglerna

Elva, var och en med minst en trasig fixtur. Provet
`test_alla_regler_har_minst_en_trasig_fixtur` läser sin egen källa och faller
på en regel utan en.

| # | Regel |
|---|---|
| `Y1` | läget står först, ordagrant |
| `Y2` | ett stilla läge visar ingen pågåendemarkör |
| `Y3` | fallets skäl står ordagrant |
| `Y4` | varje främmande sträng når användaren tecken för tecken |
| `Y5` | avsnittet om vad systemet inte vet finns, och är aldrig tomt |
| `Y6` | en dom utan obligatorisk sektion visas inte som en dom |
| `Y7` | guld visas aldrig utan ögondom (regel A-6) |
| `Y8` | trimningen säger hur mycket den dolde |
| `Y9` | ett hjärtslag räknas aldrig som framsteg |
| `Y10` | ett arbetande läge namnger vad som pågår, och hur länge |
| `Y11` | en avslutad körning räknar stegen som aldrig kördes |

`Y6` kräver nu tre sektioner, inte två: `MOTION`, `HONESTY` och — sedan
`M-65` — `LIMITS`. Det är samma krav som visningens eget avsnitt *VET INTE*,
en våning ned: en rapport som inte säger vad ögat inte ser har inte sagt
allt.

`Y2` har en egen trasig fixtur åt andra hållet: en kompilatorrad som råkar
innehålla frasen `pågår sedan` får **inte** fälla visningen. En grinds egna
ord är inte visningens påstående, så grinden tar bort främmande ord innan den
letar efter sina egna.

---

## 6. Vad systemet inte vet, i två klasser

Skillnaden är inte kosmetisk: den ena går att beta av med en bättre körning,
den andra gör det aldrig.

**Utanför räckvidd**, fem poster, ordagrant efter `50_grindar.md`:
sensorstuds, ställdonsdynamik, fältbussjitter, degraderade lägen och verklig
hårdvara. De står i **varje** visning, också en som gick igenom. En körning
kan inte beta av dem.

Här hände något värt att skriva ned. Samma dygn, i en annan cell, lade `M-65`
till sektionen `LIMITS` i ögats kontrakt med kravet att rapporten ska bära en
`NOT_SIMULATED`-rad per post i `oga_kontrakt.EJ_SIMULERAT`. Den listan är
`sensor_bounce`, `actuator_dynamics`, `fieldbus_jitter`, `degraded_modes`,
`real_hardware` — **samma fem saker, i samma ordning**, härledda oberoende ur
samma stycke i `50_grindar.md`.

Två listor som ska vara samma lista går isär tyst, så de är nu bundna:
ögats eget namn står som andra kolumn i visningen, och
`test_rackvidden_ar_ogats_egen_lista` jämför tupeln mot `K.EJ_SIMULERAT`.
Bindningen visade sig direkt: `guldgrind.OBLIGATORISKA_SEKTIONER` växte från
två till tre sektioner mitt under arbetet, och provet
`test_sektionslistan_ar_guldgrindens` föll i samma minut.

**Ej prövat i den här körningen**, hämtat ur källornas egna skäl:

* stationsgrindens överhoppade grindar, med grindens eget skäl (`ej kord;
  deklarationsmatchning fallde forst`)
* reparationsslingans `ej_korda`
* ögonkopplingens fyra utfall ur `M-42` — inskott till ett stängt öga, värden
  utan tidsaxel, avbrott, och en klocka som gått bakåt
* ögats saknade sektioner, härledda ur domen
* steg som aldrig kördes, och — skilt från dem — steg som **påbörjades men
  aldrig fick ett utfall**

Den sista skillnaden kommer ur `24_samtalsloopen.md` §5: ett påbörjat steg kan
ha hunnit ha verkan innan körningen dog, och en omkörning skulle kunna ladda
in en komponent två gånger. De två får inte se likadana ut.

I en fallen körning blev det **9 poster ovisshet** mot **2 körda grindar**.
Avsnittet om vad vi inte vet är alltså längre än avsnittet om vad vi vet, och
det är rätt proportion så länge räckvidden ser ut som den gör.

---

## 7. Trösklarna

`MAX_HANDELSERADER = 12`. En händelserad är 40–90 tecken. Tolv rader håller
hela ytan under 2 400 tecken också i det dyraste läget, och trimningen säger
alltid hur många rader den dolde. Händelser som bär någon annans ord räknas
inte mot taket.

`TYSTNADSTAK_S = 5.0`, **PRELIMINÄR, sätts av M-28**. Talet är
`24_samtalsloopen.md` §7:s eget, och stämpeln är dokumentets egen. Detta är
första gången det finns i kod: före den här mätningen hade det noll träffar.

Tröskelskulden är orörd. Båda konstanterna bär härkomst på samma rad, och
`forlopp/` bidrar med **0** till `UTAN_HARKOMST`.

---

## 8. Förslag till specen

Specen är inte rörd. Följande är förslag.

**8.1 `24_samtalsloopen.md` §7 — två tillägg till den slutna listan.**
Listan kan inte säga två saker som fasen behöver.

* **att körningen SJÄLV föll.** `VERKTYG_FEL` är ett anrop som föll.
  `AVBRUTEN` är operatörens beslut. Kopplaren som ger upp efter tre raka fel
  (`M-39`) har ingen händelse alls. Föreslås: `FALLET`, med skälet ordagrant.
* **vad grind 1–4 sa.** `DOM` är ögat och `GULD` är guldgrinden. Grindarna
  före dem har ingen händelse, trots att `27_operatorsflodet.md` §5 steg 10
  lovar operatören *"fyra grindar med utfall"*. Föreslås: `GRIND`, med
  grindens egna ord.

Tilläggen ligger i `TILLAGDA_SORTER` och provas för sig, så att de syns i
stället för att glida in.

**8.2 `27_operatorsflodet.md` §9 — en grind som stänger fas 17.** De elva
`F-G`-grindarna handlar om installation, start och genomlopp. Ingen av dem
säger något om vad användaren ser medan det arbetar. Föreslås `F-G12`:

> Under en pågående körning går förloppsytan att läsa, och den fäller sin
> egen grind. Trasigt fall: en visning som påstår att en fallen körning
> arbetar, en som skriver om en grinds ord, och en som visar en dom vars
> ärlighetsgrind aldrig kört — alla tre måste falla.

**8.3 `26_appen.md` §3 — fält 5 och 6 har nu ett mekaniskt prov.** Regel A-5
kräver att fält 5 är byte-identiskt med ögats domstext och regel A-6 att fält
6 aldrig visas utan fält 5. Båda är nu mekaniserade som `Y4` och `Y7`, men
mot förloppsytan och inte mot en panel. Raden i A-G5 kan peka hit.

**8.4 En öppen fråga som hör till operatören.** `26_appen.md` §7 fråga 1 —
webbläsare eller terminal — är fortfarande öppen, och den här mätningen
besvarar den inte. Ytan är text just för att svaret ska kunna bli vilket som
helst.

---

## 9. Vad detta INTE bevisar

* **Ingen VC kördes.** Inget i den här mätningen har varit i närheten av
  Visual Components, en levande brygga eller en riktig OPC UA-server. Varje
  källa provas mot attrapper. Att `kor_kopplaren` fäller rätt när attrappen
  slutar svara säger ingenting om vad som händer när Wine, `wineserver` eller
  licensservern faller.
* **Ingen språkmodell kördes.** Reparationsslingan drivs av en manusmodell.
  Talen säger vad mekaniken gör, inte vad en modell gör.
* **Ingen operatör har läst ytan.** Att texten är läsbar är min bedömning,
  inte en mätning. Att 44 % av en arbetande vy handlar om ovisshet kan vara
  precis rätt eller uppenbart för mycket, och det avgörs av den som väntar,
  inte av mig.
* **Tystnadstaket är inte mätt.** 5 s kommer ur specen och specen kallar det
  preliminärt. Ingen mätning av modellagrets latens finns (`M-28`).
* **`MAX_HANDELSERADER = 12` är vald mot teckenkostnaden, inte mot
  läsbarheten.** Tolv rader kan vara för få för att förstå ett förlopp. Det
  vet vi inte.
* **Ytan är inte trådsäker och har ingen processgräns.** `Forlopp` förs av
  den som kör varvet, precis som kopplarens `Varv`. Ska en panel i en annan
  process läsa den behövs en serialisering som inte finns, och den dagen är
  det ett nytt beslut om vad som får trimmas på vägen.
* **De fem posterna utanför räckvidd är en avskrift, inte en mätning.** De
  står i `50_grindar.md` och är rimliga. Ingen har mätt att listan är
  fullständig, och den kan mycket väl sakna något.
* **Grinden ser inte ett protokoll som ljuger.** Den dömer texten mot
  protokollet. För en källa som redan tappat grindens ord innan förloppet
  fördes är varje visning "korrekt". Skyddet är att källorna provas var för
  sig, och det skyddet är lika brett som `kallor.py` är — inte bredare.
* **Fält 1 och 7 finns inte.** Samtalet och systemläget kräver en levande
  brygga. Ingen del av `A-G4` är därmed stängd.
* **Ingenting driver ytan än.** Den går att driva, och det är en annan sak än
  att den drivs. Noll moduler i `svc/` utanför `forlopp/` konstruerar ett
  `Forlopp`. De två som äger en körnings tidslinje — `harness/loop.py` och
  `plan/korning.py` — returnerar fortfarande sitt protokoll först när allt är
  över. Hålet står som `tests/motbevis/test_forloppet_har_ingen_forare_motbevis.py`,
  rött med flit, och lagas den dag någon står högst upp och anropar
  `forlopp.kallor`. Kopplaren och reparationsslingan ska **inte** laga det
  själva: att låta ett lägre lager känna presentationslagret vore att vända
  beroendet fel väg.
