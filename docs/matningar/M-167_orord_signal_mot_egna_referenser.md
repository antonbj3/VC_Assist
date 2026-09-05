# M-167 — ORORD_SIGNAL fällde 13 signaler i 9 egna referenser: referensen eller kartan?

**Datum:** 2026-09-05
**Rigg:** `bank/domare.py` (ST-tolken, 20 ms scan), grind 2/3 via
`R.Stationssteg` i `bank/reparationsbank.py`, hela banken läst med
`bank.reparationsbank.uppgifter_med_sparfacit()`
**Prövar:** `bank/uppgifter/{C-02,C-03,C-05,H-03,L-02,L-03,L-04,P-01,P-02}.json`
**Låst av:** `tests/enhet/test_referenser_mot_grindkedjan.py`
(`DOMAR_M167`, `STIMULI_M167`, `C03_FIXTURSEKVENSER`)
**Bygger på:** M-121 (samma prov, grind 2), M-96 (nio av sexton grinddomar var
vår egen bugg), M-48 (grind 3:s koder)

## Talet, bekräftat

Vid mätningens start bar banken **44 uppgifter med spårfacit**. Nio av dem
fälldes av grind 3 på `ORORD_SIGNAL`, tillsammans **13 signaler**. Efteråt:
**0 av 9**, och varje referens går fortfarande igenom sitt eget spårfacit med
**0 brister**.

| Uppgift | Signaler | Grind 2/3 före | Grind 2/3 efter | Spårfacit före | Spårfacit efter |
|---|---|---|---|---|---|
| C-02 | ST400_LNE_CNT | `ORORD_SIGNAL` | ren | 0 brister, 9 502 scan | 0 brister, 9 502 scan |
| C-03 | ST410_PRD_CNT | `ORORD_SIGNAL` | ren | 0 brister, 473 scan | 0 brister, **1 835 scan** |
| C-05 | ST430_PRD_CNT, ST440_RWK_CNT, ST440_RWK_QUE | `ORORD_SIGNAL` ×3 | ren | 0 brister, 298 scan | 0 brister, 298 scan |
| H-03 | ST330_AGV_WGT | `ORORD_SIGNAL` | ren | 0 brister, 167 scan | 0 brister, 167 scan |
| L-02 | ST160_VAC_OK, ST160_PLT_HGT | `ORORD_SIGNAL` ×2 | ren | 0 brister, 197 scan | 0 brister, 197 scan |
| L-03 | ST170_VAC_OK | `ORORD_SIGNAL` | ren | 0 brister, 47 scan | 0 brister, 47 scan |
| L-04 | ST180_MAG_RDY | `ORORD_SIGNAL` | ren | 0 brister, 13 757 scan | 0 brister, 13 757 scan |
| P-01 | ST100_RB_BUSY | `ORORD_SIGNAL` | ren | 0 brister, 167 scan | 0 brister, 167 scan |
| P-02 | ST110_RB_BUSY, ST110_VAC_OK | `ORORD_SIGNAL` ×2 | ren | 0 brister, 37 scan | 0 brister, 37 scan |

C-03:s scantal växer därför att uppgiften fick **två nya spårsekvenser** — se
§C-03. Alla 9 uppgifters motbevis faller före och efter på exakt de koder de
namnger (`test_varje_motbevis_falls_pa_den_brist_det_namnger`).

**Uppdraget sa fem signaler** (`ST400_LNE_CNT`, `ST410_PRD_CNT`,
`ST430_PRD_CNT`, `ST440_RWK_QUE`, `ST330_AGV_WGT`). Grinden namnger **13**:
till dem kommer `ST440_RWK_CNT`, `ST160_VAC_OK`, `ST160_PLT_HGT`,
`ST170_VAC_OK`, `ST180_MAG_RDY`, `ST100_RB_BUSY`, `ST110_RB_BUSY` och
`ST110_VAC_OK`. Halva materialet var alltså inte räknare utan **bekräftelser** —
vakuumvakter, robotens upptagetsignal, magasinets klarsignal.

## Domen: 13 av 13 är REFERENSEN. Ingen är kartans, ingen är grindens.

Frågan per fall var uppdragets: är referensen ofullständig, eller deklarerar
kartan något uppgiften inte behöver? Svaret är läst ur uppgiftens egna fält och
ur **klassens koherens över hela banken**, inte ur en läsning av ett fall.

| Fall | Signal | Står i `control.sequence`/`interlocks` | Har gränsvärde-scenario | Redan driven av eget spår | Dom |
|---|---|---|---|---|---|
| C-02 | ST400_LNE_CNT | ja | `cnt_lag`, `cnt_hog` | nej | **referensen** |
| C-03 | ST410_PRD_CNT | ja | `cnt_lag`, `cnt_hog` | nej | **referensen** |
| C-05 | ST430_PRD_CNT | ja (+ interlock) | `cnt_lag`, `cnt_hog` | nej | **referensen** |
| C-05 | ST440_RWK_CNT | ja | `rwk_lag`, `rwk_hog` | nej | **referensen** |
| C-05 | ST440_RWK_QUE | nej | `que_lag`, `que_hog` | nej | **referensen** |
| H-03 | ST330_AGV_WGT | nej | `cnt_lag`, `cnt_hog` | **ja** (0,0 kg vid t=0) | **referensen** |
| L-02 | ST160_PLT_HGT | nej | `hgt_lag`, `hgt_hog` | **ja** (200,0 mm vid t=0) | **referensen** |
| L-02 | ST160_VAC_OK | nej | nej | **ja** (TRUE vid t=0) | **referensen** |
| L-03 | ST170_VAC_OK | nej | nej | nej | **referensen** |
| L-04 | ST180_MAG_RDY | ja | nej | **ja** (FALSE@0, TRUE@89 100) | **referensen** |
| P-01 | ST100_RB_BUSY | ja | nej | nej | **referensen** |
| P-02 | ST110_RB_BUSY | ja | nej | nej | **referensen** |
| P-02 | ST110_VAC_OK | nej | nej | nej | **referensen** |

### De fyra mätningarna som avgör, inte tycker

**1. Ett gränsvärde-scenario är per konstruktion en stimulans på en scenägd
mätare.** Alla **50** `gransvarde_lag`/`gransvarde_hog`-scenarier i banken
ligger på signaler med `dir: in`, och alla på `int` eller `real`. **Noll** på en
utgång. Det avgör C-05:s riktningsfråga: uppgiftstexten säger *"räkna i
ST430_PRD_CNT"*, men kartan säger `in`. Vore räknaren styrningens egen kunde
scenariot `cnt_hog` — *"ST430_PRD_CNT stiger till 320 på en timme"* — inte
inträffa, och styrningen kunde inte "larma" om sin egen glömska. `in` är rätt;
"räkna i" betyder *låt räknas i*, och styrningens uppgift är att **övervaka**
räknaren. Ingen riktning ändrades.

**2. Klassen "scenägd mätare med gränsvärde-scenario" är koherent — referensen
var undantaget.** Över banken: **143** signaler bär ett scenario
(gränsvärde eller vändning); **136** rörs av sin referens, **7** inte. De sju är
exakt C-02:s, C-03:s, C-05:s tre, H-03:s och L-02:s mätare. Smalare: av **50**
scenägda `int`/`real`-mätare med gränsvärde-scenario läses **43**; de 7 olästa
är samma sju. Det är inte en karta som deklarerar för mycket — det är sju
referenser som skrev av 43 syskons form utan att göra det syskonen gör.

**3. "Signalen står bara i kartan" är INGET bevis för att uppgiften inte
behöver den.** **58** signaler i banken står *enbart* i `control.signals` — inte
i prompten, inte i sekvensen, inte i förreglingarna, inte i något scenario. Av
dem läses **55 (95 %)** av sin egen referens. De tre olästa är L-02:s, L-03:s
och P-02:s `VAC_OK`. Argumentet "signalen nämns ingen annanstans, alltså ska den
bort ur kartan" faller på sin egen statistik: i banken är kartan just den plats
där en signal *bara* står, och referensen den plats där den används.

**4. Vakuumvakten är universell i kartan och nästan universell i koden.** **8 av
8** uppgifter med en `*_VAC_ON`-utgång har också en `*_VAC_OK`-ingång — undantagslöst,
för en vakuumgripare har en vakuumvakt. **5 av 8** referenser läser den (L-01,
L-05, L-06, P-01, P-03). Att stryka signalen ur L-02:s, L-03:s och P-02:s karta
vore att påstå att just deras gripdon saknar vakt. Kartan är den koherenta.

### Det starkaste enskilda beviset: fyra av tretton var redan stimulerade

För **H-03** (`ST330_AGV_WGT`), **L-02** (`ST160_PLT_HGT` och `ST160_VAC_OK`)
och **L-04** (`ST180_MAG_RDY`) *satte spårfacit redan signalen* — L-04 till och
med med rätt tidpunkt (`ST180_MAG_RDY := TRUE` vid 89 100 ms, precis efter att
`ST180_MAG_REQ` gått hög vid 16 kollin). Facitförfattaren hade byggt
stimulansen. Referensförfattaren konsumerade den aldrig. En karta som
deklarerar för mycket ser inte ut så; en ofullständig lösning gör det.

## Vad referenserna gör nu, och varifrån varje tal kommer

Formen är bankens egen: en **ren mellanvariabel** som väger den scenägda
signalen mot vad styrningen själv vet, och en åtgärd som *spärrar* — inte en
flagga som ingen läser. Härkomsten för varje tröskel står på **samma rad** som
tilldelningen, i ST-koden.

| Uppgift | Vad koden gör | Talens härkomst |
|---|---|---|
| **C-02** | `enheterKlara` räknar `ST400_STA_DONE`-flanker. `ST400_LNE_CNT` får ligga högst **en** enhet efter (den som är på väg ut på utbanan) och aldrig före. Vid räknefel går `ST370_HS_REQ` inte hög — linan släpper inga fler enheter och ackumulerar uppströms. | "en enhet på väg ut" ur linans egen topologi; scenarierna `cnt_hog` (två per cykel) och `cnt_lag` (står på 0) |
| **C-03** | `ST410_PRD_CNT` får bara röra sig när `ST410_CNV_RUN` är hög, och **måste** röra sig inom **24,0 s** medan bandet går. Annars `ST410_STA_STOP` och stopp. | halv takt = 5,0 kartonger/min = 12,0 s per kartong; två sådana takter = 24,0 s, så en lucka i flödet inte larmar. Båda ur uppgiftens egna tal |
| **C-05** | `godkanda`, `utskjutna`, `kvitterade` och `koLangd` är styrningens egen bokföring. De tre scenräknarna får ligga högst en karta efter, aldrig före, och kön aldrig över **10**. Vid räknefel startas ingen ny karta. | 10 = omarbetningsplatsens tio platser (scenariot `que_hog`: kön når 14) |
| **H-03** | Vågcellen vägs mot `ST330_LOD_CNT`: last under `LOD_CNT × 22,0 − 11,0` kg är ett kolli som hamnat bredvid flaket; över **100,0** kg lastas inget mer och `ST330_HS_DONE` hålls låg. | 22,0 kg = kollits vikt ur `antaganden`; 11,0 kg = halva kollivikten; 100,0 kg = AGV:ns högsta last ur scenariot `cnt_hog` |
| **L-02** | `ST160_PLT_HGT` mot lagerräknaren: under `144,0 + (LYR_NO−1) × 200,0` mm eller över **750,0** mm spärras avlägget. `ST160_VAC_OK` krävs innan roboten rör sig; ejektorn går ändå, så undertrycket hinner byggas. | 144 mm EUR-pall (STANDARDMÅTT), 200 mm kollihöjd, 3 mm mellanlägg → färdig pall 144 + 3×200 + 2×3 = **750 mm**. Scenariot `hgt_lag` räknar självt fram 547 mm för lager 2 med samma tal |
| **L-03** | `ST170_VAC_OK` krävs innan hämtrörelsen startar. | — |
| **L-04** | Växlingen startar först när `ST180_MAG_RDY` säger att en tom pall står klar. | uppgiftens sekvenssteg *"vänta på ST180_MAG_RDY medan palleteringen fortsätter"* |
| **P-01** | `ST100_RB_DONE` godtas bara efter att `ST100_RB_BUSY` kvitterat starten. | uppgiftens *"släpp aldrig på robotens lägesignal ensam"* |
| **P-02** | Plocket räknas som gjort bara om robotprogrammet startade (`ST110_RB_BUSY`) **och** sugkoppen fick grepp (`ST110_VAC_OK`). | sekvensen *"sätt ST110_RB_PICK hög och vänta på ST110_RB_BUSY"* |

## En grön referens är ingen mätning: fjorton stimuli som fäller den

`test_stimulansen_som_signalen_lastes_for_faller_referensen` tvingar signalen
till scenariots eget värde genom hela sekvensen och kräver att referensen
**faller**. En läsning som ingen stimulans kan fälla är dekoration.

| Uppgift | Stimulans | Referensen |
|---|---|---|
| C-02 | `ST400_LNE_CNT = 2` (räknaren före stationen) | röd — `ST370_HS_REQ` går aldrig hög |
| C-05 | `ST430_PRD_CNT = 5` | röd — ingen ny karta startas |
| C-05 | `ST440_RWK_CNT = 5` | röd |
| C-05 | `ST440_RWK_QUE = 14` (scenariots eget tal) | röd |
| H-03 | `ST330_AGV_WGT = 0,0` (scenariot `cnt_lag`) | röd — spärras vid kolli 2, precis där scenariot säger |
| H-03 | `ST330_AGV_WGT = 132,0` (scenariot `cnt_hog`) | röd — spärras redan vid kolli 1 |
| L-02 | `ST160_PLT_HGT = 100,0` | röd |
| L-02 | `ST160_PLT_HGT = 1250,0` (scenariot `hgt_hog`) | röd |
| L-02 | `ST160_VAC_OK = FALSE` | röd |
| L-03 | `ST170_VAC_OK = FALSE` | röd |
| L-04 | `ST180_MAG_RDY = FALSE` | röd |
| P-01 | `ST100_RB_BUSY = FALSE` | röd |
| P-02 | `ST110_RB_BUSY = FALSE` | röd |
| P-02 | `ST110_VAC_OK = FALSE` | röd |

### C-03: räknaren går inte att fälla med ett konstant värde

C-03:s villkor är inte ett värde utan ett **förlopp** — räknaren ska stå still
*medan bandet går*, eller röra sig *medan bandet står*. Ingen konstant fäller
det. Fixturen blev därför två nya spårsekvenser i banken:

* `raknaren_star_still_medan_bandet_gar` — full takt, `ST410_PRD_CNT` rör sig
  aldrig. Krav vid 20 000 ms: linan går **ännu**; krav vid 26 000 ms:
  `ST410_STA_STOP` hög och bandet stopp. Tvåsidig: den fäller lika gärna en
  lösning som stannar i förtid.
* `raknaren_stiger_medan_bandet_star` — räknaren stiger med tre kartonger under
  formatbytet. Krav vid 1 200 ms: `ST410_STA_STOP` hög.

**Den gamla C-03-referensen (commit `955d250`) faller på båda**, med 4 brister.
Fixturen är alltså prövad röd före mekanismen.

## Vad som INTE ändrades

* **Ingen signalkarta.** Ingen signal ströks, ingen riktning ändrades, ingen
  signal lades till. Alla 13 fall gick åt andra hållet.
* **Ingen grinddom var fel.** M-96 mätte att nio av sexton `DUBBELSKRIVNING`-domar
  en gång var vår egen bugg, och M-121 rättade grinden i fem av sju fall.
  Här är utfallet det motsatta: `ORORD_SIGNAL` fällde 13 av 13 med rätt. Det är
  värt att säga rakt ut, eftersom förväntningen efter M-96 och M-121 var att
  minst några skulle vara grindens.
* **Inget larmutgång tillkom.** Fyra av uppgifterna (C-02, C-05, H-03, L-02) har
  scenarier som säger *"styrningen ska larma"* men **ingen larmsignal i kartan**
  (jämför H-05, L-05, L-06 som har `SYS_ALARM`). Åtgärden är därför den
  förregling uppgiften faktiskt har utgångar för — linan slutar släppa
  material. Att lägga till `SYS_ALARM` i fyra kartor är ett eget beslut och
  bankägarens; det står i LIMITS.
* **Spårfacitens punktkrav, invarianter och flanker.** Bara `satt`-värden
  tillkom, och bara i steg som redan hade `satt` (utom P-01/P-02 där ett nytt
  rent stimulanssteg lades in vid 400 ms, 200 ms före närmaste krav — marginalen
  är 2 scan = 40 ms).

## Fyndet i förbifarten: klassen återskapas medan vi lagar den

Under mätningens gång växte banken från **44 till 49** uppgifter med spårfacit.
De fem nya (**S-02, S-03, S-04, T-03, T-06**) bär **nio** nya orörda signaler
och fäller samma prov. De är en annan kös mark och rördes inte, men domen är
redan mätt med samma metod:

| Uppgift | Signal | Vad uppgiften själv säger | Trolig dom |
|---|---|---|---|
| S-02 | `AIR_OK` | står i `interlocks`: *"ingen utskjutning när AIR_OK är låg"* | referensen — **en förregling som inte finns i koden** |
| S-03 | `AIR_OK` | d:o | referensen — d:o |
| S-02 | `ST200_ENC_POS` | `control.sequence` + `gransvarde_lag/hog` | referensen |
| S-04 | `ST220_ENC_POS` | d:o | referensen |
| T-03 | `ST030_MRG_GAP` | `gransvarde_lag/hog` | referensen |
| T-06 | `ST060_LNE_RATE` | `gransvarde_lag/hog` | referensen |
| T-06 | `ST060_PEC_END`, `ST070_PEC_END` | bara i kartan | referensen (samma klass som `VAC_OK`) |
| S-02 | `ST200_SCN_TRIG` | **utgång** i `control.sequence` som koden aldrig skriver | referensen — det är `ODRIVEN_UTGANG`-formen |

Två av dem, `AIR_OK` i S-02 och S-03, är **förreglingar uppgiften uttryckligen
kräver och koden inte har**. Det är den allvarligaste enskilda posten i hela
mätningen, och den ligger utanför min yta.

Att de fem hann committas röda är i sig mätt: provet var redan rött för mina
nio, och **en röd svit döljer nya röda**. Fixen är inte fler filar utan att
provet är grönt — det är först då nästa instans syns samma dag den skrivs.

## Kodställen

| Vad | Var |
|---|---|
| grind 3:s `ORORD_SIGNAL` | `svc/vc_assist_svc/plc/deklarationsgrind.py` (`KONTROLLER_PLC`, riktning 2) |
| de nio referenserna och deras spår | `bank/uppgifter/{C-02,C-03,C-05,H-03,L-02,L-03,L-04,P-01,P-02}.json` |
| domar, 14 stimuli, C-03:s två fixtursekvenser | `tests/enhet/test_referenser_mot_grindkedjan.py` |
| omkörning av hela banken | `python3 -m pytest tests/enhet/test_referenser_mot_grindkedjan.py` |

## LIMITS

* **Domen är mätt på klassens koherens, inte på anläggningsritningar.** Att
  8 av 8 vakuumgripare i banken har en vakuumvakt är ett tal om **banken**, inte
  om verkligheten. Ett gripdon utan vakt finns; hade L-02:s scen varit ett
  sådant hade domen där varit "kartan". Ingen scenkälla utanför
  `bank/uppgifter/*.json` konsulterades — bankens kartor byggs av
  `karta_ur_uppgift()` ur `control.signals` och är, med filens egna ord, "inte
  mätta mot någon verklig scen".
* **Fyra kartor saknar larmutgång.** C-02, C-05, H-03 och L-02 har scenarier som
  kräver *"styrningen ska larma"* utan att kartan har något att larma med.
  Åtgärden är förregling, inte larm. Om bankägaren vill ha larmet mätbart ska
  `SYS_ALARM` in i de fyra kartorna — det är en kartändring och den är **inte**
  gjord här.
* **L-02:s undre höjdgräns är prövad vid lager 1, inte vid lager 2.** Scenariot
  `hgt_lag` (350 mm när lager 2 är färdigt, mot förväntade 547 mm) kräver att
  spåret når `ST160_LYR_NO = 3`; `normal_lager_med_mellanlagg` slutar vid
  lager 2. Gränsen är riktig per konstruktion (`144 + 2×200 = 544 > 350`) men
  den **halvan är inte körd**. Fixturen som körs är höjd 100,0 mm vid lager 1.
* **C-02:s undre gräns är inte fälld av en stimulans.** Spåret släpper igenom
  exakt **en** enhet, och en räknare som ligger en enhet efter är tillåten. För
  att fälla den halvan krävs ett spår med minst två enheter. Den övre halvan
  (räknaren före stationen) är körd och röd.
* **Kollivikten 22,0 kg i H-03 är ett ANTAGANDE**, uppgiftens eget. Tröskeln
  ärver antagandets osäkerhet: en verklig cell där kollivikten varierar mer än
  ±11 kg skulle larma falskt. Det står i uppgiftens `antaganden` och är inte
  mätt av någon.
* **P-01:s och P-02:s `RB_BUSY`-latch fångar inte en robot som fastnar.**
  P-03 har en 6,0 s tidsövervakning på `ST120_RB_BUSY` och en egen spårsekvens
  för det; P-01 och P-02 har varken scenario eller spår för fallet, så ingen
  tidsövervakning lades till. Låset är "DONE utan BUSY", inte "BUSY som aldrig
  faller".
* **Ingen vakuumtidsövervakning i L-02/L-03.** L-01 har `tmrVac` och sekvensen
  `vakuumet_kommer_aldrig`; L-02 och L-03 har ingen sådan sekvens, så väntan på
  `VAC_OK` är obegränsad. Fångas inte av något prov och är inte byggt.
* **De fem nya uppgifternas domar i §Fyndet är LÄSTA, inte körda.** De är
  klassade med samma fältmetod (`sequence`/`interlocks`/scenario/klasskoherens)
  men ingen referens är omskriven och ingen stimulans är körd på dem. De är
  hypoteser för den kö som äger dem.
* **Spårfacit ändrades på de nio.** 15 `satt`-värden tillkom (plus två nya
  sekvenser i C-03). Det är en ändring av facit, inte bara av lösningen, och den
  är motiverad fall för fall ovan: fyra av signalerna drevs redan, resten drivs
  nu därför att ett spår som aldrig rör en ingång inte kan mäta vad koden gör
  med den. Ingen `krav`-rad, invariant eller flank ändrades, och samtliga
  motbevis faller fortfarande på exakt sina namngivna koder.
