# M-160 — F1: modellen skriver linan, ögat talar tillbaka

**Datum:** 2026-09-05
**Rigg:** `tests/protocol/kor_F1_modellen_skriver_linan.py`
**Prövar:** `svc/vc_assist_svc/plc/reparation.py`, `modellklient.py`,
`claudeadapter.py`, `guldgrind.py`, `ext/vc_addon/vc_assist/oga_analys.py`
**Modell:** **guldarmen på `google-vertex/gemini-3.8-flash`**,
**kompositionsarmen på `claude/sonnet`** — se §0 och §7. De två armarna kördes
alltså på **olika modeller**, och det är i sig ett resultat: Gemini-kvoten dog
mitt i mätningen. `RATTELSER 2026-09-05 16:25` gäller: en arm på en annan
modell är en **annan mätning**, och de får aldrig läggas ihop till ett tal.

> **Läget 2026-09-05 kl. 23:00:** riggen var **byggd och prövad, aldrig körd.**
> Allt nedanför §7 är skrivet före körningen och står kvar oförändrat, för det
> beskriver apparaten. §0 och §7 är körningen.

## 0. Utfallet — F1 kördes 2026-09-05/06

**Sammanfattningen först, för den är kort:**

**`F1 AR GRONT` på `claude/sonnet`**, räknat av riggens egen
`grontkriteriet` över båda armarnas JSON:

| halvan | krav | `claude/sonnet` | `google-vertex/gemini-3.8-flash` |
|---|---|---|---|
| **guld** | GOLD inom fyra varv i ≥ 2 av 3 körningar | **JA** — 2 av 3 (varv 3 och varv 1) | **JA** — 2 av 3, båda på varv 2 |
| **komposition** | ≥ 3 av 5 fall lagade på ögats egna ord | **JA** — 4 av 5 | *ej körd, kvoten dog* |
| **F1** | båda | **GRÖNT** | ofullständig |

Hela F1 på `claude/sonnet`: **4,92 USD, 115 minuters väggtid, 41 ögonvarv.**

**Det som `M-73` och `M-74` båda kallade sin egen gräns är inte längre sant.**
Båda skriver samma mening — *"reparationsvarven är **noll** av samma skäl:
ingen modell har fått något fel tillbaka att laga"*. Reparationsvarven är nu
**21**, i en riktig VC-scen genom OpenPLC, och 4 av 5 kompositionsfel lagades
på ögats egen felbeskrivning.

**Guldarmen kördes på båda modellerna, och det var inte planerat.**
Mitt i mätningen slutade `google-vertex/gemini-3.8-flash` svara, och orsaken
är entydig: `403 This API method requires billing to be enabled` på
`project-fbc92f92-4e11-47e5-bd0`. `opencode/muse-spark-1.3-contributor-free`
svarade inte alls (tidsgräns 180 s på `Svara med exakt ordet OK.`).
`claude/sonnet` svarade. Kompositionsarmen kördes därför på Claude.
`RATTELSER 2026-09-05 16:25` gäller: **de två armarnas tal får aldrig läggas
ihop till ett F1-tal.**

### 0.1 Riggen hade aldrig kört, och tre fel satt i vägen

Alla tre hittades genom att köra, inget av dem genom att läsa koden, och alla
tre var osynliga för de 30 gröna enhetsproven.

**1. Den riktiga vägens två byggare tog inga argument.** `guldarmen` och
`kompositionsarmen` anropar dem med `etikett`; torrkörningens motsvarigheter
tog den, den riktiga vägens gjorde inte det. Riggen föll på en `TypeError` i
guldarmens **första** varv — efter att startskriptet skrivits, innan VC rörts.
Provsviten var grön eftersom torrkörningen går genom två **andra** funktioner.
Byggarna ligger nu på modulnivå (`riktiga_byggare`) så att ett prov kan nå
dem, och fixturen `test_fixtur_den_riktiga_vagens_byggare_tar_armens_etikett`
faller när argumentet tas bort.

**2. Ögats serie ryms inte i bryggans svar.** Mätt: **684 586 byte** mot
pumpens tak `MAX_KROPP // 2` = **524 288**. `kor_en` returnerar då `fel` utan
`domar`, och `Ogonsteg` gör körningen OGILTIG — ögat hade aldrig fått döma ett
enda varv. Serien hämtas nu ur filen (`~/.wine-vc-test/drive_c/users/anton/
vc_assist_eyes.json`), vilket är vad pumpens egen kommentar säger att filen är
till för. Det är **samma serie och samma domare**, bara en annan kanal in, och
den enda nya felklassen — en fil som ligger kvar över en VC-omstart — är
stängd mekaniskt: filens `run.started` måste vara exakt det ögonblick den här
körningens `eyes_start` svarade, och antal prov, längd och takt måste stämma.
Fyra fixturer, alla röda mot mutationen.

**3. Ögats upplösning var inte M-73:s.** Fas 8:s argparse-standard är 70 s
mätning, 25 s uppvärmning och 20 Hz — men **M-73 och M-74 kördes inte där.**
M-73 skriver ut vad ögat faktiskt såg: *"ogats serie: 80,0 s, 800 prov, 10,00
Hz"*, och M-74:s arton körningar har *"45 s uppvärmning och 80 s mätning"*.
Skillnaden är inte kosmetisk. M-73:s fjärde fynd är att **ett prov vars
tolerans är snävare än scenuppdateringens eftersläpning mäter
eftersläpningen**, och facits fönster är räknade vid 0,1 s provintervall. En
F1-körning på fas 8:s standard hade alltså dömt M-73:s facit vid en upplösning
facit aldrig kalibrerats mot. Talen ligger nu i namngivna konstanter
(`MATNING_S`, `UPPVARMNING_S`, `OGONRATE_HZ`) med M-73 som härkomst.

Efter rättelse 2 och 3 rymdes serien i svaret igen: **800 prov, 10,00 Hz,
80,0 s** i varje ögonvarv, och `serien_ur_fil` är `None` — filvägen är en
spärr som inte behövde användas, inte en väg mätningen står på.

### 0.2 Guldarmen — modellen skriver linan från uppgiften

`--forfattare opencode --modell google-vertex/gemini-3.8-flash --arm guld
--upprepa 3`

```
guld:         GOLD i 2 av 3 korningar (kravs 2)  -> JA
    korning 1: LOST           varv till GOLD 2      1 ogonvarv   486 s   0,2423 USD
    korning 2: KORNINGSFEL    varv till GOLD None   0 ogonvarv   280 s   (transport)
    korning 3: LOST           varv till GOLD 2      1 ogonvarv   541 s   0,2424 USD
```

Båda de körningar som fick ett svar gick **samma väg**:

| varv | grind | utfall |
|---|---|---|
| 1 | `grind:statisk_analys` | FÄLLD, kod `SYNTAX` — billigt, ingen VC rördes |
| 2 | `station` (grind 1–3) | GODKÄND |
| 2 | `oga` | **PASS** i alla tre cellerna → `gold_line_verified` |

Alltså: **modellens andra försök blev GOLD direkt.** Ögat hade inget att
anmärka på — station A PASS, station B PASS, linan PASS — och guldgrinden gav
`gold_line_verified`. Grind 4 (`anropsvalidering`) kördes och gav `True` inne
i ögonsteget, precis som §2.1 säger att den ska.

Klockkvoten i de två ögonvarven: **0,9896** och **0,9901**, väl inne i M-73:s
brakett 0,75–1,40. Ingen körning blev ogiltig på klockan.

**Det första varvet nådde aldrig ögat.** Det är värt att säga rakt ut: i båda
körningarna föll modellens första kropp på den **statiska analysen**, alltså på
ST-syntax, och kostade ett av fyra varv utan att ögat sa ett ord. Guldarmen
mäter därför i praktiken *"ett syntaxvarv plus ett riktigt varv"*, och taket på
fyra varv är i den formen inte fyra ögonvarv utan färre.

### 0.3 Transporten är en egen felkälla, och den är mätt

Av de anrop guldarmen gjorde föll flera på transporten utan att modellen sagt
något: `opencode gav slutkod 1` med **tom** stderr, och `opencode gav ingen
text tillbaka`. Varje sådant fel kostade en VC-omstart, en uppladdning och 80 s
scenmätning och gav ingenting att döma.

Riggen har därför fått ett **avgränsat omförsök** på tre namngivna
transportklasser (`gav slutkod`, `gav ingen text tillbaka`, `svarade inte
inom`), och **aldrig** på `anvande verktyg` — den är en fail-closed *dom* om
att svaret kan ha läst facit, och ett omförsök där hade varit att fråga om
tills modellen råkar svara som vi vill. Listan är en vitlista, så en ny
felklass provas aldrig om utan att någon skriver dit den. Varje omförsök
räknas och följer med i JSON:en; ett omförsök som inte går att räkna döljer
sin egen frekvens.

Omförsöket räckte inte mot Gemini: i kompositionsarmens första K1-körningar
föll **3 av 3** försök, och kort därefter svarade modellen `403 … requires
billing to be enabled` på en enradsprompt. Kvoten var slut, inte prompten fel.

## 1. Vad F1 är, och varför den är den enda punkten som spelar roll

`M-73` och `M-74` byggde linan med två stationer och fällde fem
kompositionsfel. Båda säger sin egen gräns med samma mening:

> *"Att en modell skriver kropparna. Alla sex är handskrivna, och
> reparationsvarven är **noll** av samma skäl: ingen modell har fått något fel
> tillbaka att laga."*

Fas 9 stängde halva hålet: `kor_fas9_slingan.py` matar tillbaka
**grindarnas** ord till en riktig modell och mäter varv till löst mot bankens
spårfacit. Men domen kommer där ur vår egen ST-tolk, inte ur en scen. Den
andra halvan — ST skriven **inuti** mätslingan, körd genom OpenPLC, sedd av
**ögat** i en riktig VC-scen — har aldrig gjorts.

F1 är den halvan, och skillnaden mot fas 9 är **en** sak: det som matas
tillbaka in i prompten är **ögats egna ord**.

```
EYES VERDICT FAIL forregling: ST8A_Don/Slapp och ST8B_Don/Slapp hoga
samtidigt i 3.90 s, 45 prov
```

## 2. Apparaten

### 2.1 Ögat är ett grindsteg, inte en andra slinga

`reparation.Reparationsslinga` kontrollerar redan mekaniskt att varje fällande
grinds `utdata` når modellen **tecken för tecken**
(`kontrollera_ordagrant`). Doktrinen är motiverad av en mätt incident: en
omimplementerad positionsdom underkände 2 av 4 medan ögat visade 4 av 4.

`Ogonsteg` är därför ett `Grindsteg` som varje annat. Det kör M-74:s `kor_en`
för **en** kropp i LINJE-konfigurationen — kompilering, uppladdning till
OpenPLC, omstart av runtimeprocessen, uppvärmning, mätning i scenen, ögats tre
domar — och lämnar tillbaka en `Grinddom` vars `utdata` är ögats tre rapporter
ordagrant. Att skriva en andra slinga som *lovar* samma sak i en docstring
hade varit att flytta doktrinen från mekanik till bön.

Kedjan per varv:

```
modellen skriver kroppen
    -> grind 1-3 (statisk analys, deklarationer, STruC++)   billigt, ingen VC
    -> OpenPLC + VC-scenen + ögat                            grind 4 och 5
    -> guldgrinden över tre celler                           GOLD -> slut
```

Ordningen är inte en optimering: en kropp som inte kompilerar ska aldrig kosta
en VC-omstart, en uppladdning och 105 sekunder scenmätning.

**Grind 4 (anropsvalidering) ligger med flit inte i den billiga kedjan.**
`Stationssteg` bygger sin kandidat utan scenkod, och en kandidat utan scenkod
ger inte `anropsvalidering: True` — den ger skälet till att grinden inte kunde
köras. Låg den i den billiga kedjan hade **varje** modellsvar fällts på riggens
egen brist innan ögat fick se något, och mätningen hade rapporterat det som
modellens. Grind 4 körs där scenkoden finns: inne i ögonsteget, genom M-74:s
egen `kor_en`. Det fanns i riggens första uppställning och står här därför att
det är exakt den felklass `85_bankkontraktet.md` §2 finns för.

### 2.2 Författaren är en parameter

Tre transporter går att välja, och operatören byter med en flagga:

| `--forfattare` | transport | var den kommer ifrån |
|---|---|---|
| `claude` | `modellklient.ClaudeCLI` | fanns (M-96) |
| `opencode` | `kor_fas9_musespark.OpencodeCLI` | fanns (M-110), tar modellnamn |
| `inspelad` | `modellklient.Inspelad` | fanns; för prov utan kostnad |

`Forfattare` ärver `claudeadapter.ClaudeModell` i stället för att kopiera den.
Det är poängen: dess `svara` kastar `Adapterfel` så fort den får verktyg, den
skalar av ett kodstaket runt hela svaret, och den summerar kostnaden. En andra
väg in till modellen hade varit en väg utan de sakerna.

### 2.3 Spärren mot facit är mekanisk, inte en uppmaning

Modellen får aldrig nå repot — bankens facit ligger där, och
`kor_fas8_linan.py` bär hela linans facit. `modellklient` bygger två lager:
tom verktygslista **och** en arbetskatalog utanför repot, kontrollerad av
`_neka_repot`. `Forfattare` läser transportens **egen källa** och vägrar en
transport som saknar något av lagren:

```
transporten UtanSparr anropar aldrig _neka_repot. Modellen skulle kunna kora
i repot, och bankens facit ligger dar: matningens giltighet star pa att den
inte sett det.
```

Det är den billigaste vägen till ett falskt grönt F1 som stängs: en modell som
läser `kor_fas8_linan.py`.

### 2.4 n ≥ 3, inbyggt

`A2` mätte att OpenPLC-domaren inte är deterministisk vid n = 1 — realtidens
jitter avgjorde en invariant i L-01. `kontrollera_n` avvisar n < 3, och varje
körning rapporteras **för sig** i JSON:en och i utskriften. Ett medelvärde
utan spridning säger ingenting om det som frågan gäller.

### 2.5 Inkrementell JSON per ögonvarv

Flushas efter **varje ögonvarv**, inte i slutet. Ett ögonvarv kostar en
VC-omstart, en uppladdning och över hundra sekunder scenmätning — det är den
dyraste enheten i riggen och därför den som ska överleva ett avbrott. Skälet
är mätt samma dag: en avbruten fullarm tappade ~10 lösta uppgifter.

Varje varv bär **domen och koden som dömdes**. `M-96`: när TIDLITERAL-domarna
visade sig vara vår egen falska rödgrind fanns modellens kod inte kvar att
läsa, så fyndet fick göras om från början.

### 2.6 Grönt-kriteriet mekaniserat

Båda halvorna räknas, och körningen säger **vilken** som föll:

| | krav | hur det räknas |
|---|---|---|
| `guld` | GOLD inom fyra varv i minst 2 av 3 körningar | en majoritet av körningarna, aldrig färre än 2 av 3 |
| `komposition` | minst 3 av 5 kompositionsfall lagade på ögats egna ord | ett fall räknas som lagat när det lagades i en **majoritet** av sina **giltiga** körningar, och det måste finnas minst två sådana |

Majoritetsregeln på kompositionssidan är A2:s: en enda lyckad körning kan vara
jitter. Tre sorters körningar skiljs åt, och skillnaden bär räkningen:

* **OGILTIG** — seeden gick inte att döma (klockan utanför M-73:s brakett, ögat
  utan ord). M-74:s regel: en sådan körning är inte fällande, den är ogiltig.
  Den räknas därför varken i täljaren eller i nämnaren.
* **seeden släppte igenom** — ögat lät M-74:s egen K-kropp passera. Då är
  **fixturen** trasig, och fallet får aldrig räknas som lagat.
* **giltig** — seeden föll, modellen fick ögats ord och sitt tak.

Rådata per körning ligger kvar i JSON:en, så en annan regel går att räkna i
efterhand utan att köra om.

Kompositionsarmen seedar varje fall med M-74:s egen K-kropp, kör den genom
ögat **en gång** (varv noll, som inte kostar av modellens fyra), och lägger
ögats tre rapporter ordagrant i modellens uppgift. En seed som ögat **släpper
igenom** rapporteras som `SEEDEN_FOLL_INTE` och räknas aldrig som lagad — då
var fixturen trasig, inte modellen duktig.

## 3. Vad som är prövat i dag, utan modell och utan VC

`tests/enhet/test_kor_F1_riggen.py`, 30 prov, gröna. Provet skrevs **före**
mekanismen och var rött.

### 3.1 De tre trasiga fixturerna

| # | fixturen | vad som händer |
|---|---|---|
| (a) | en författarmodell som får verktyg | `Adapterfel` — för **alla tre** transporterna |
| (b) | en körning som slår i taket | `utfall=TAK`, `lost=False`, `gold=False`, `varv_till_gold=None`, och grönt-kriteriet räknar den inte |
| (c) | ögats återkoppling som är tom | `Ogonfel` — körningen är OGILTIG, inte ett tyst varv |

(c) är den som inte var självklar: `reparation.kontrollera_ordagrant` **hoppar
över** tom `utdata`, så ett tomt ögonsvar hade passerat kontrollen och gett
modellen en inramning utan ord — ett bränt varv av fyra på ingenting. Hålet är
stängt på ögats sida, där det uppstår.

Sex fixturer till: en transport utan `_neka_repot` avvisas, en klockkvot
utanför M-73:s brakett gör körningen OGILTIG i stället för fällande, en seed
som ögat släpper igenom räknas aldrig som lagad, en torrkörning kan aldrig ge
ett grönt F1, grind 4 avvisas ur den billiga kedjan, och en rigg utan brygga
faller med ett besked som namnger `vc-test.sh` och `--torrkorning` i stället
för en `AttributeError`.

### 3.2 Mutationsprovet: biter fixturerna?

Tre mutationer av mekanismen, en åt gången, och exakt de avsedda fixturerna
föll:

```
tom ögontext accepteras       -> test_fixtur_tom_ogonaterkoppling...   RÖTT
spärrkontrollen tas bort      -> test_fixtur_transport_utan_repospar   RÖTT
taket räknas som gold         -> test_fixtur_korning_som_slar_i_taket  RÖTT
```

### 3.3 Torrkörningen

`--torrkorning` kör hela slingan på inspelade modellsvar och inspelade
ögondomar. Kropparna är **M-74:s egna**, alltså riktig ST som grind 1–3
verkligen dömer; bara ögats svar är inspelade, och de byggs med ögats **egen**
skrivare (`oga_kontrakt.Rapport`) så att guldgrinden får döma en riktig
EYES-rapport genom sin riktiga läsare.

```
guld:         GOLD i 2 av 3 korningar (kravs 2)  -> JA
    korning 1: LOST   varv till GOLD 1        (GOLD direkt)
    korning 2: LOST   varv till GOLD 2        (tva varv)
    korning 3: TAK    varv till GOLD None     (slog i taket)

komposition:  4 av 5 fall lagade (kravs 3)  -> JA
    K1..K4  lagat i 3 av 3 giltiga korningar   LAGAT
    K5      lagat i 0 av 3 giltiga korningar   -

OGILTIG MATNING:
    18 av korningarna ar torrkorningar; en inspelning kan aldrig ge ett
    gront F1

F1 AR ROTT - foll pa: giltighet
```

Räkningen blir rätt i alla tre fallen, och den torra körningen faller ändå på
giltigheten. Det är avsiktligt och fail-closed: `grontkriteriet` sätter
`giltigt=False` så fort **någon** rad bär `torrkorning`.

### 3.4 Grind 1–3 mot riktig STruC++

Utanför provsviten kördes den billiga kedjan mot en riktig STruC++-installation
(0.6.6, npm-paketet) på M-74:s HEL-kropp: `statisk_analys`,
`deklarationsmatchning` och `kompilering` gav alla GODKÄND. En kropp med en
odeklarerad variabel föll på grind 2 med grindens egna ord:

```
rad 24: [ODEKLARERAD/F4] finns_inte är inte deklarerad
```

Alltså: den halva av kedjan som inte behöver VC är verifierad mot riktiga
verktyg, inte bara mot inspelningar.

## 4. Vad som INTE var mätt när apparaten byggdes

> Det här avsnittet skrevs **före** körningen och står kvar oförändrat.
> Punkterna 1–3 och 5–6 är besvarade av §0 och §7; punkt 4 (kostnaden) står i
> §7. Den enda som står kvar helt obesvarad är den sista.



* **Ingenting om en modell.** Ingen modellslinga har körts. Riggen är
  apparaten; F1:s tal finns inte förrän den körts, och den här filen får inte
  läsas som att den bär dem.
* **Ingenting genom VC.** `Ogonsteg`:s dyra väg — VC-omstart, uppladdning till
  OpenPLC, uppvärmning, scenmätning, ögats tre domar — är **oprövad i den här
  riggen**. Den är M-74:s `kor_en` ordagrant och kördes arton gånger där, men
  att F1 anropar den rätt är inte visat förrän den kört.
* **Grind 4 (anropsvalidering) i ögonsteget.** Att den passerar med M-74:s
  `SCENKOD` är M-74:s mätning, inte den här. Här är den bara **utesluten** ur
  den billiga kedjan.
* **Kostnaden per körning.** `Forfattare` summerar transportens kostnad, men
  vad fyra varv kostar på en riktig modell är okänt tills armen körts. En
  transport som inte rapporterar kostnad ger `None`, aldrig `0.0`.
* **Vilken modell.** Rättelsen 2026-09-05 16:25 gäller: modellnamnet skrivs i
  JSON:ens `modell` och i den här filens rubrik när armen körts. En arm på en
  annan modell är en **annan mätning**, inte en fortsättning.
* **Att kompositionsfallen faller i den här riggens uppställning.** M-74 fällde
  fem av fem i LINJE. F1 kör LINJE-konfigurationen; kontrollkörningarna A och B
  körs inte per varv, för de tredubblar VC-kostnaden. Att K1–K5 fortfarande
  faller mäts av seeden själv (`seeden_foll`), och en seed som inte faller
  rapporteras som en trasig fixtur.
* **F2:s klassning.** Varje misslyckat reparationsvarv ska klassas i "ögat sa
  fel sak", "ögat sa rätt sak otydligt" eller "modellen kunde inte laga trots
  ett tydligt besked". Riggen sparar seedens ögonord och varje varvs kropp så
  att frågan **går** att ställa i efterhand, men den ställer den inte.

## 5. Kommandona som faktiskt kördes

```
# guldarmen                                        23 min, 0,54 USD
python3 tests/protocol/kor_F1_modellen_skriver_linan.py \
    --forfattare claude --modell sonnet --arm guld --upprepa 3 \
    --strucpp <npm-paketet, den med dist/ och libs/> \
    --runtime-include <strucpp_runtime/include> \
    --json docs/matningar/data/M-160_f1_guld_claude.json

# kompositionsarmen                                92 min, 4,38 USD
python3 tests/protocol/kor_F1_modellen_skriver_linan.py \
    --forfattare claude --modell sonnet --arm komposition --upprepa 3 \
    --strucpp <...> --runtime-include <...> \
    --json docs/matningar/data/M-160_f1_komposition_claude.json

# den sammanraknade domen, ur riggens EGEN grontkriteriet-kod
python3 scripts/f1_grontkriteriet.py \
    docs/matningar/data/M-160_f1_guld_claude.json \
    docs/matningar/data/M-160_f1_komposition_claude.json \
    docs/matningar/data/M-160_f1_grontkriteriet_claude.json
```

Guldarmen kördes dessutom på `--forfattare opencode --modell
google-vertex/gemini-3.8-flash` innan den kvoten dog
(`docs/matningar/data/M-160_f1_guld.json`).

**Det tredje kommandot behövs bara för att armarna kördes i två anrop.** Körs
`--arm bada` i ett anrop räknar riggen själv. Att räkna ihop för hand är inte
ett alternativ: siffran ska komma ur samma kod som dömde.

VC ska vara igång (`~/bin/vc-test.sh`) och OpenPLC-runtimen svara på `--bas`.
**Starta om VC precis innan armen startar.** `Bryggan` startar om VC mellan
varje ögonvarv men **inte** före det första, så det första varvet ärver den
VC-session som råkar köra.

Förutsättningar riggen **inte** kan ordna själv, och som därför fäller med ett
tydligt besked i stället för att gissa:

* VC igång på `:99` med bryggan på port 8901 (riggen skriver startskriptet
  själv och startar om VC mellan körningarna).
* En egen OpenPLC-runtime. Standardvärdena `--bas https://127.0.0.1:18443`,
  `--endpoint opc.tcp://127.0.0.1:14840/` och
  `--runtime-omstart "docker restart vcassist-openplc-v4"` pekar på den runtime
  **kö A äger**. Kör F1 mot en egen container, eller efter att A2/A3 är klara.
* STruC++ npm-paketet och runtimens include-katalog.

Kostnadsordningen, om kvoten är knapp: `--arm guld` först (3 körningar × ≤4
ögonvarv), sedan `--arm komposition` (5 fall × 3 körningar × ≤5 ögonvarv).
**Mätt:** ett ögonvarv är ~4 minuter väggtid — VC-omstart, uppladdning,
runtimeomstart, 45 s uppvärmning och 80 s mätning — och hela F1 blev 41
ögonvarv på 115 minuter.

## 6. Om F1 blir rött (skrivet före körningen)

> F1 blev **inte** rött på `claude/sonnet`. Stycket står kvar för att det var
> villkoret körningen gick in med, och för att ett grönt som aldrig hade kunnat
> bli rött inte är värt något.



`KO_F §F1` säger det rakt ut, och det ska stå här också: **faller F1 är
produkten bänken, inte slingan.** Ett rött F1 är den billigaste sanning
projektet kan köpa, och riggen säger vilken halva som föll i stället för att
bara säga nej.

## 7. Kompositionsarmen och den sammanräknade domen — `claude/sonnet`

`--forfattare claude --modell sonnet --arm komposition --upprepa 3`, femton
körningar, 36 ögonvarv (15 seedvarv + 21 reparationsvarv), 92 minuters
väggtid, **4,38 USD**. Noll transportfel.

```
komposition:  4 av 5 fall lagade (kravs 3)  -> JA
    K1   lagat i 3 av 3 giltiga korningar   LAGAT
    K2   lagat i 2 av 3 giltiga korningar   LAGAT
    K3   lagat i 3 av 3 giltiga korningar   LAGAT
    K4   lagat i 2 av 3 giltiga korningar   LAGAT
    K5   lagat i 2 av 2 giltiga korningar (1 dar seeden slapp igenom)   -
```

Guldarmen kördes sedan på **samma** modell, så att F1 har en dom om **en**
modell och inte om två:

```
guld:         GOLD i 2 av 3 korningar (kravs 2)  -> JA
    korning 1: KORNINGSFEL    varv till GOLD None   (OpenPLC:s bygge, se 7.3)
    korning 2: LOST           varv till GOLD 3
    korning 3: LOST           varv till GOLD 1
```

Sammanräknat av **riggens egen** `grontkriteriet` över de två armarnas JSON
(`scripts/f1_grontkriteriet.py`; armarna kördes i två anrop och varje anrop såg
bara sin egen halva, men räkningen får inte göras för hand):

```
F1 AR GRONT
```

**Alltså: modellen skriver linan, ögat talar tillbaka, och modellen lagar på
ögats egna ord.** Det som `M-73` och `M-74` båda kallade sin egen gräns —
*"reparationsvarven är noll, ingen modell har fått något fel tillbaka att
laga"* — är inte längre sant. Reparationsvarven är 21, och 4 av 5
kompositionsfel lagades på ögats felbeskrivning.

Kostnad, för den som ska planera nästa körning: **4,92 USD** och **115 minuters
väggtid** för hela F1 på `claude/sonnet` (guldarmen 0,54 USD / 23 min,
kompositionsarmen 4,38 USD / 92 min). Guldarmen på Gemini kostade 0,48 USD.

### 7.1 F2: klassningen av varje misslyckat reparationsvarv

Tre körningar av femton nådde inte GOLD. `KO_F §F2` kräver att varje
misslyckat varv klassas i en av tre. Klassningen görs mot ögats **egna**
domsrader, som ligger i JSON:en.

| körning | varv | ögats ord | klass |
|---|---|---|---|
| **K2 #2** (LAST) | 1 | seed: `FAIL sequence` på stationB och linan, `ST8B_Don/Stopp RISE uteblev i fonstret 4.09–10.15 s`. Efter modellens rättning: stationA **PASS**, linan **PASS**, stationB `FAIL timing: cykel 3: ST8B_Don/Stopp RISE kom 1.80 s efter starten, fonstret ar 0.00–1.26 s` | **ögat sa rätt sak otydligt** |
| **K4 #2** (TAK) | 1 | tre FAIL → efter rättning: linan **PASS**, stationA **PASS**, stationB `FAIL timing: cykel 3 … 1.80 s, fonstret ar 0.00–1.26 s` — **exakt samma** enstaka avvikelse som K2 #2 | **ögat sa rätt sak otydligt** |
| **K4 #2** | 2 | ögat gick tillbaka till alla tre FAIL, med signal, cykel och fönster utskrivna. Modellen hade backat till det ursprungliga felet | **modellen kunde inte laga trots ett tydligt besked** |
| **K4 #2** | 3 | ögat sa ingenting alls: kroppen föll på `grind:statisk_analys`, kod `SYNTAX` | **modellen kunde inte laga** (ögat kom aldrig till tals) |
| **K4 #2** | 4 | linan `FAIL sequence`, stationA PASS, stationB `FAIL sequence: cykel 3` — en enda cykel | **ögat sa rätt sak otydligt** |
| **K5 #3** | — | seeden **föll inte**: ögat gav PASS i alla tre cellerna på M-74:s egen K5-kropp | **ingen av de tre** — fixturen föll inte, se 7.2 |

**Noll varv klassas som "ögat sa fel sak".** Varje domsrad namngav en riktig
signal, en riktig cykel och ett riktigt fönster, och ingen av dem gick att visa
vara falsk.

**Men den vanligaste klassen är "rätt sak, otydligt", och den har en form.**
Tre av fem misslyckade varv slutade på **samma** rad:

```
EYES VERDICT FAIL timing: stationens tider holls inte:
cykel 3: ST8B_Don/Stopp RISE kom 1.80 s efter starten, fonstret ar 0.00-1.26 s
```

En enda cykel av åtta, 0,54 s utanför ett fönster, i **station B** — medan
stationA och linan står PASS. `M-73` har redan mätt varför det händer:
*"Station B:s processtid varierar och station A:s gör det inte … B väntar in
det delade donet när A har det, och väntan är som mest en hel utmatning."*
Bromsens utgång i station B är alltså fördröjd av **linans** kontention, inte
av ett fel i modellens kod — men domen kommer från **stationsfacit**, som inte
vet att linan finns.

Det är den skarpaste F2-observationen körningen bär: ögat säger en sann sak på
fel nivå. Ett stationsfacit som dömer en fördröjning linan själv orsakar ger
modellen ett besked den inte kan handla på, och K2 #2 svarade på det enda
sätt som var rimligt — den skickade tillbaka **samma kropp** (utfall `LAST`,
låst, inte tak). Att slingan skiljer `LAST` från `TAK` är därför inte en
detalj: den skillnaden är just det som gör klassen synlig.

### 7.2 K5:s fixtur reproducerar inte vid n = 3 — och det är A2:s fynd på ögats sida

Tre seedkörningar av **samma** K5-kropp, i samma rigg, med praktiskt taget
samma klocka (0,9901 / 0,9901 / 0,9900) och samma 800 prov:

| seed | stationA | stationB | linan | |
|---|---|---|---|---|
| K5 #1 | PASS | PASS | **FAIL** `sequence: cykel 7: ST8B_Don/Stopp RISE uteblev` | föll |
| K5 #2 | PASS | **FAIL** `timing: cykel 4` | **FAIL** `sequence: cykel 4, 5` | föll |
| K5 #3 | PASS | PASS | **PASS** | **släppte igenom** |

`M-74` körde K5 **en** gång och skrev in den som ett kompositionsfel. Vid
n = 3 faller den i 2 av 3, och när den faller är det på **en enda cykel** av
åtta. Det är exakt `A2`:s mätning — att domaren inte är deterministisk vid
n = 1 — nu visad på ögats sida, på M-74:s egen fixtur.

Riggen räknade rätt utan att någon behövde tänka: en seed som ögat släpper
igenom rapporteras `SEEDEN_FOLL_INTE` och fallet får **aldrig** räknas som
lagat, hur duktig modellen än var i de andra två körningarna. K5 står därför
som `-` trots 2 av 2 lagade giltiga körningar.

**Det här är en rättelse till M-74, inte till F1.** M-74:s fem-av-fem gäller
vid n = 1. Vid n = 3 är K5:s fällning marginell.

### 7.3 OpenPLC:s bygge fäller kod som grind 3 släpper igenom, och dess ord når aldrig modellen

Guldarmens första körning på Claude dog med `OpenPlcFel`:

```
core/generated/generated.cpp:155:32: error: no matching function for call to 'NOT(int)'
  155 |     if ((((B_LAGET == 2) & (NOT((A_LAGET == 2) | (A_LAGET == 3)))) & (KOR)) & (!NODSTOPP)) {
```

Kroppen hade **passerat** grind 1–3, inklusive kompileringsgrinden, och föll
sedan i OpenPLC:s eget bygge av den genererade C++-koden. Två saker följer:

1. **Grind 3 och OpenPLC:s bygge är inte samma grind.** `NOT` på ett
   jämförelseuttryck kommer igenom den ena och inte den andra.
2. **Byggets ord når aldrig modellen.** Felet blir ett `KORNINGSFEL` — hela
   körningen dör — i stället för en `Grinddom` vars `utdata` matas tillbaka.
   Det är samma hål som ögat hade före F1, en nivå ned: en domare som ser ett
   riktigt fel men vars ord inte går tillbaka in i slingan.

Det är inte lagat här, för det ändrar vad armen mäter mitt i en mätning. Det
står som en öppen punkt, och det är den billigaste kända förbättringen av
slingan: **ett varv av fyra dog på en compiler-rad ingen fick läsa.**

### 7.4 Guldarmens första varv når sällan ögat

Sammanlagt över båda modellerna: i **tre** av de fyra guldkörningar som fick
ett modellsvar föll det **första** varvet på den billiga kedjan — `SYNTAX` i
statisk analys på Gemini (två av två), och på Claude gick körning 2 tre varv
innan GOLD. Bara Claudes körning 3 nådde GOLD på **första** varvet.

Guldarmens tak på fyra varv är alltså i praktiken inte fyra ögonvarv. Det är
inte fel — en kropp som inte kompilerar ska aldrig kosta en VC-omstart — men
den som läser "GOLD inom fyra varv" ska veta att en del av de fyra går åt till
ST-syntax innan ögat sagt ett ord.

## LIMITS

* **Talen gäller `claude/sonnet` och ingen annan modell.** Guldarmen kördes
  också på `google-vertex/gemini-3.8-flash` och gav samma utfall på sin halva,
  men kompositionsarmen finns inte där: kvoten dog (`403 requires billing`).
  `RATTELSER 2026-09-05 16:25` — en arm på en annan modell är en **annan
  mätning**, och de två får inte läggas ihop.
* **n = 3, och det syns i talen.** Två av fem kompositionsfall lagades i 2 av 3
  körningar, inte 3 av 3, och K5:s **fixtur** föll bara i 2 av 3. Ett n = 3 gör
  spridningen synlig; det gör den inte liten. Fler upprepningar skulle flytta
  varje siffra i tabellen.
* **En körning av femton dog på OpenPLC:s bygge** (`NOT(int)`) och räknas som
  KORNINGSFEL. Talen ovan är därför inte hela armen, och det byggets ord når
  aldrig modellen (§7.3).
* **K5 räknas inte som lagat, och skälet är fixturens.** Modellen lagade det i
  2 av 2 giltiga körningar. Att fallet ändå står `-` är regeln i §2.6, inte ett
  mått på modellen.
* **Ögats domsrader är stationsfacit och linjefacit, inte en förklaring.** Den
  vanligaste orsaken till ett misslyckat reparationsvarv var en sann dom på fel
  nivå (§7.1). Att ögat skulle kunna säga det bättre är **inte** mätt — det är
  en hypotes körningen ställer, inte en den svarar på.
* **Ett fall, en lina, en geometri, en takt.** M-74:s begränsningar gäller
  oförändrat: fem klasser är inte alla klasser, och två stationer är inte tre.
* **Ingenting om fler än två stationer, om längre körningar, eller om scenen
  under belastning.** Det är F4–F7. `F7` är särskilt relevant efter den här
  körningen: klockkvoten låg på 0,989–0,990 i **varje** ögonvarv, alltså på en
  maskin som inte var hårt belastad.
* **Grind 3 och OpenPLC:s bygge är inte samma grind** (§7.3). Hur ofta de är
  oense är inte mätt — det hände en gång av arton.
* **Kostnaden gäller den här uppställningen.** 4,92 USD och 115 minuter är
  priset för n = 3 på fem fall plus tre guldkörningar, med ~4 minuter per
  ögonvarv (VC-omstart, uppladdning, 45 s uppvärmning, 80 s mätning).
