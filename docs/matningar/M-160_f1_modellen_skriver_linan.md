# M-160 — F1: modellen skriver linan, ögat talar tillbaka

**Datum:** 2026-09-05
**Rigg:** `tests/protocol/kor_F1_modellen_skriver_linan.py`
**Prövar:** `svc/vc_assist_svc/plc/reparation.py`, `modellklient.py`,
`claudeadapter.py`, `guldgrind.py`, `ext/vc_addon/vc_assist/oga_analys.py`
**Modell:** *inte vald ännu — se §5*

> **Läget 2026-09-05:** riggen är **byggd och prövad, inte körd.** Kvoten är
> slut på en modell och delas av tre sessioner på den andra, så det här
> dokumentet beskriver apparaten och vad den kommer att svara på. Talen fylls i
> när operatören valt modell. **En rad i den här filen som ser ut som ett
> resultat och inte har en körning bakom sig får inte skrivas.**

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
| `komposition` | minst 3 av 5 kompositionsfall lagade på ögats egna ord | ett fall räknas som lagat när det lagades i en **majoritet** av sina körningar |

Majoritetsregeln på kompositionssidan är A2:s: en enda lyckad körning kan vara
jitter. Rådata per körning ligger kvar i JSON:en, så en annan regel går att
räkna i efterhand utan att köra om.

Kompositionsarmen seedar varje fall med M-74:s egen K-kropp, kör den genom
ögat **en gång** (varv noll, som inte kostar av modellens fyra), och lägger
ögats tre rapporter ordagrant i modellens uppgift. En seed som ögat **släpper
igenom** rapporteras som `SEEDEN_FOLL_INTE` och räknas aldrig som lagad — då
var fixturen trasig, inte modellen duktig.

## 3. Vad som är prövat i dag, utan modell och utan VC

`tests/enhet/test_kor_F1_riggen.py`, 26 prov, gröna. Provet skrevs **före**
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

Fyra fixturer till: en transport utan `_neka_repot` avvisas, en klockkvot
utanför M-73:s brakett gör körningen OGILTIG i stället för fällande, en seed
som ögat släpper igenom räknas aldrig som lagad, och en torrkörning kan aldrig
ge ett grönt F1.

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
    K1..K4  lagat i 3 av 3 korningar, seeden foll i 3   LAGAT
    K5      lagat i 0 av 3 korningar, seeden foll i 3   -

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

## 4. Vad som INTE är mätt

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

## 5. Vad som återstår: exakt ett kommando

När operatören valt modell:

```
python3 tests/protocol/kor_F1_modellen_skriver_linan.py \
    --forfattare claude --modell sonnet \
    --strucpp <npm-paketet, den med dist/ och libs/> \
    --runtime-include <strucpp_runtime/include> \
    --upprepa 3 \
    --json docs/matningar/data/M-160_f1.json
```

Byt `--forfattare claude --modell sonnet` mot `--forfattare opencode --modell
<opencode-modell>` för den andra transporten. VC ska vara igång
(`~/bin/vc-test.sh`) och OpenPLC-runtimen svara på `--bas`.

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
ögonvarv), sedan `--arm komposition` (5 fall × 3 körningar × ≤5 ögonvarv). Ett
ögonvarv är ~2–3 minuter väggtid.

## 6. Om F1 blir rött

`KO_F §F1` säger det rakt ut, och det ska stå här också: **faller F1 är
produkten bänken, inte slingan.** Ett rött F1 är den billigaste sanning
projektet kan köpa, och riggen säger vilken halva som föll i stället för att
bara säga nej.

## LIMITS

* Riggen är **byggd och prövad, inte körd**. Allt i §3 är prövat utan modell
  och utan VC; allt i §1–2 är en beskrivning av apparaten, inte ett resultat.
* Den dyra vägen (VC, OpenPLC, ögat) är oprövad i den här riggen. Den är
  M-74:s `kor_en` ordagrant, men att F1 anropar den rätt är inte visat.
* Torrkörningens ögondomar är **inspelade**. De bevisar att räkningen,
  taket, låsningen och grönt-kriteriet fungerar — ingenting om vad ögat
  faktiskt säger om en modellskriven kropp.
* Ingen modell är vald, så inget tal här hör till någon modell.
* Ingenting om fler än två stationer, om längre körningar, eller om scenen
  under belastning. Det är F4–F7.
