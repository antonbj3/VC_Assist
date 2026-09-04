# FAS 16 ACCEPTANS — planeringslagret

**beskriver:** `svc/vc_assist_svc/plan/`
**kontrakt:** `docs/spec/22_planeringslagret.md`, `docs/spec/70_faser.md` fas 16
**mätning:** `docs/matningar/M-63_planeringslagret_matt_mot_sin_spec.md`
**körs av:** `tests/enhet/test_bestallning.py` (L1 — ingen VC, ingen OpenPLC,
ingen kompilator)

## Status 2026-09-05: **grön i L1**

**180 prov** i `tests/enhet/test_bestallning.py`, plus nio i `test_plan.py` för
efterkontrollerna. Alla trasiga fall nedan fälls, och varje grind i
`bestallning.GRINDAR` har en fixtur som faller på just den.

Kör: `python3 -m pytest tests/enhet/test_bestallning.py -q`

Vad protokollet **inte** bevisar står i avsnitt F, och det som kräver VC
(`P5`, `P8`) hör till fas 5a och fas 7–8.

## Grinden, ordagrant

> En grundbeställning i fritext blir en detaljerad, körbar byggplan med villkor
> och processordning — och planen **avvisas** när den är omöjlig, i stället för
> att byggas halvt. Trasigt fall: en beställning som motsäger sig själv måste
> fällas med vilket villkor som krockar.

Två halvor, och den andra är den svåra. En planerare som alltid producerar en
plan är värdelös: den producerar en plan också för det omöjliga, och då upptäcks
felet först när något går sönder i scenen.

## Vad protokollet kräver av formen

**En grind utan trasig fixtur är ingen grind.** Varje punkt nedan prövas åt
**båda** hållen: att kontrollen faller på ett verkligt fel, och att den släpper
igenom det korrekta. En kontroll som bara provats åt ena hållet är oprövad
(`docs/spec/95_testprotokoll.md`).

**Ett nej lämnar aldrig ut en plan.** `Besked.__init__` kastar om status inte är
`BYGGBAR` och en plan följer med. Det är en form, inte en överenskommelse: en
halv plan ser körbar ut, och det är farligare än inget svar (I3).

---

## A. Den positiva riktningen — fri text blir en körbar plan

| # | Vad som körs | Grönt svar |
|---|---|---|
| A1 | `bestall(<plockcellstexten>, katalog, motor)` | `BESKED BYGGBAR` |
| A2 | planen bär steg | ≥ 20 steg, varav ≥ 8 skrivande |
| A3 | planen håller verktygsregistret | `plan.granska() == []` |
| A4 | ordningen är deterministisk | tre sekvenseringar ger samma lista |
| A5 | processordningen är utskriven | `plockning -> packning` |
| A6 | koordinaterna kommer ur layoutmotorn | ≥ 1 `set_transform`-steg |
| A7 | varje antagande är märkt | `spec.antaganden` ≥ 10, alla med motiv |
| A8 | inga öppna blockerande frågor | `blockerande_fragor() == []` |
| A10 | varje skrivande steg har en efterkontroll som kan falla | 8 av 8 |
| A11 | de fyra artefakterna skrivs på disk | `spec/layout/plan/anropssekvens.json` |
| A12 | sekvensen är densamma byte för byte | en hash över tre körningar |
| A13 | två turer räcker: fråga, svar, plan | `OFULLSTANDIG` → `BYGGBAR` |

Beställningstexten är operatörens, ordagrant, och står i provfilen.

## B. De sex grindarna, i ordning

`bestallning.GRINDAR` är en sluten lista. En grind som inte står där körs inte,
och en grind som står där utan att köra är ett fel i sig.

| Grind | Faller på | Trasig fixtur |
|---|---|---|
| `B0_FRAGERUNDOR` | fler än två frågerundor (K4) | T10 |
| `B1_HARKOMST` | ett krav vars härkomst inte går att slå upp | **T3** nedan |
| `B2_PROCESSORDNING` | cykel, okänd process, självordning | **T2** nedan |
| `B3_MOTSAGELSE` | villkor som inte kan gälla samtidigt | **T1** nedan |
| `B4_FRAGOR` | en blockerande fråga är obesvarad, eller en fråga som inte säger vad den behövs till | T5, T11 |
| `B5_LAYOUT` | ingen placering uppfyller alla relationer | **T4** nedan |
| `B6_PLANEN` | stegen håller inte verktygsregistret | T6 |

---

## C. DE TRASIGA FALLEN

De här är protokollets kärna. Var och en **måste** fällas, och var och en måste
fällas med **vad** som krockar — inte med "planen är ogiltig".

### T1. Beställningen motsäger sig själv (fas 16:s namngivna trasiga fall)

> *"Bygg en cell. Cellen får vara högst 2x2 meter och minst 3 meter bred."*

**Krav på svaret:**
* status `AVVISAD`, grind `B3_MOTSAGELSE`
* koden `MK1_INTERVALL_TOMT`
* **båda** villkoren namnges, med **operatörens egna ord** som belägg:
  `"hogst 2x2 meter"` och `"minst 3 meter bred"`
* en åtgärd står utskriven

Det räcker alltså inte att den fälls. Fälls den utan att namnge de två raderna
kan operatören inte rätta något, och grinden har inte gjort sitt.

### T2. Processordningen är cyklisk

> *"Bygg en cell. Först svetsning, sedan målning. Målning före svetsning."*

**Krav på svaret:**
* status `AVVISAD`, grind `B2_PROCESSORDNING`
* koden `PO1_CYKEL`
* **vilka steg som bildar ringen** står i texten: `malning`, `svetsning`
* ringen skrivs som en väg tillbaka till sig själv:
  `malning -> svetsning -> malning`

En cykel får aldrig bli en oändlig loop, och "planen är ogiltig" är inget svar.

### T3. Ett antaget krav som inte är märkt som antaget

Ett villkor konstrueras med `Harkomst("begaran", "hogst 1200 mm")` mot en
beställning där de orden **inte står**.

**Krav på svaret:**
* status `AVVISAD`, grind `B1_HARKOMST`
* koden `HK2_FALSK_BEGARAN`
* texten namnger både kravet och de påstådda orden

Det här är hela skyddet mot att detaljeringen hittar på krav användaren aldrig
ställde. Kontrollen är en delsträngsmatchning på normaliserad text — inte en
åsikt, och inte en modell som bedömer sig själv.

**Motprovet hör till fixturen:** samma villkor med ett belägg som **står** i
beställningen släpps igenom. En härkomstgrind som fäller allt mäter ingenting.

### T4. Geometrin gör kravet omöjligt

En robot med 900 mm räckvidd ska nå ett 2 000 mm långt band, helt.

**Krav på svaret:**
* status `AVVISAD`, grind `B5_LAYOUT`
* layoutmotorns egen dom bärs igenom: `OVERBESTAMD`
* den **minimala** mängden relationer som binder namnges: `INOM_RACKVIDD`
* sökrastret står utskrivet i skälet

Skillnaden mot T1 är botemedlet: T1 rättas genom att ändra ett krav, T4 genom
att flytta, byta komponent eller vidga cellen.

### T5. Ett hårt slot är tomt

En beställning som namnger komponenter men inte hur de ska kopplas ihop.

**Krav på svaret:** status `OFULLSTANDIG`, och frågan namnger vilka roller som
saknar koppling. **Ingen plan lämnas ut.** Topologin gissas aldrig — ordningen
orden råkade stå i texten är inget belägg för vad som ska sitta ihop.

### T6. En storhet som inte går att slå upp

Ett villkor kräver att robotens räckvidd är minst 2 500 mm, och räckvidden
saknas i både begäran, katalogen och databladet.

**Krav på svaret:** status `OFULLSTANDIG`, koden `B3_OKAND_STORHET`.
**Aldrig `BYGGBAR`.** Källprojektets stubbar svarade `pass` när argumentet
saknades (`verifier_registry.py:421` och `:471`); det ärvs inte.

### T7. Prosa i ett villkor

`Typvillkor(..., storhet="roboten ska vara snabb", ...)` konstrueras.

**Krav på svaret:** `Specfel` med `VS2_OKAND_STORHET`. Villkorsspråket är
slutet (K6): fri text i ett villkor är ett lintfel, inte en varning.

### T8. Ett prosakrav utan konsument

`Prosakrav(..., konsument="")` konstrueras.

**Krav på svaret:** `Specfel` med `VS5_PROSAKRAV_UTAN_KONSUMENT`.
Detta är felklassen `PL5` — efterkontroll utan konsument — och den fanns i vårt
eget planeringslager innan M-63: `spec.Villkor.text` lästes av **noll** rader
kod i hela repot.

### T9b. En efterkontroll som inte kan falla

Fyra former prövas, var och en med sin egen fixtur i `test_plan.py`:

| Kod | Trasig fixtur |
|---|---|
| `EK1_WRITE_UTAN_POST` | ett `load_component` utan efterkontroll |
| `EK2_POST_HALLER_INTE` | en post som läser en väg verktyget aldrig svarar med |
| `EK3_POST_SKRIVER` | en post som anropar `delete_component` |
| `EK4_POST_KAN_INTE_FALLA` | `finns` på ett fält som står i verktygets `required` |

Plus: ett förväntat värde som är en **bindning** går inte ens att konstruera —
ett facit som räknas fram ur körningen är inget facit
(`L-SC-01_REJECT_SELF_REF`).

### T9c. En artefakt som ändrats efter att den skrevs

En byte ändras i `anropssekvens.json` efter skrivningen.

**Krav på svaret:** `Planfel` på hashen. En artefakt som ändrats är inte den
artefakt planen godkändes som, och att läsa den som om den vore det är precis
den tysta nedgradering lagret finns för att undvika.

### T9. Ett nej som lämnar ut en plan

`Besked(AVVISAD, spec, plan)` konstrueras.

**Krav på svaret:** `Planfel`. Utan den formen kan en avvisad beställning ändå
byggas, och då är hela grinden en rekommendation.

### T11. En fråga som inte säger vad den behövs till

En `Fraga` med ett id som ingen rad i `BEHOVS_FOR` täcker läggs i specen.

**Krav på svaret:** status `AVVISAD`, koden `S1_SLOT_UTAN_BEHOV`.
Det är `K1`: ett fält utan `needed_for` får inte finnas i schemat. Felet ligger
i **vår** kod — någon har lagt till ett slot utan att säga vad det behövs till —
och det ska fällas innan beställningen når operatören.

**Svepet hör till fixturen:** samma prov kör hela banken och sju
fritextbeställningar och kräver att *varje* fråga som faktiskt ställs har en
rad. En tabell som bara täcker det man kom ihåg mäter ingenting.

### T10. En tredje frågerunda

Samma beställning ställs med `fragerunda=3`.

**Krav på svaret:** status `OFULLSTANDIG`, grind `B0_FRAGERUNDOR`, koderna
`B0_FOR_MANGA_RUNDOR` och `B0_SAKNAS` — det senare listar vad som fortfarande
saknas. En loop som frågar i evighet är inte en klarifiering; den är ett sätt
att aldrig behöva svara.

**Motprovet:** två rundor är tillåtna.

---

## D. Motsägelsegrindens fyra domar

Ingen av dem heter `MOJLIG`, och det är avsikten.

| Dom | Betyder | Prov |
|---|---|---|
| `OMOJLIG` | bevisat: villkoren kan inte alla gälla | T1, ytbeviset, passformen |
| `VALET_FALLER` | kraven går, men inte med den komponenten | katalogräckvidd < krav |
| `OKANT` | en **statisk** storhet saknar värde | T6 |
| `INGEN_MOTSAGELSE_FUNNEN` | de körda kontrollerna föll inte | A1 |

**`INGEN_MOTSAGELSE_FUNNEN` är inget godkännande av geometrin.** Det säger att
just de kontrollerna inte fällde. Layoutmotorn söker i ett raster och säger
själv att den inte påstår matematisk omöjlighet.

En storhet som är okänd **för att scenen inte är byggd än** (`scen.kollisioner`,
`scen.min_avstand_mm`) blockerar inte — den hamnar i `att_mata` och blir planens
verifiering. Att blanda ihop de två hade gjort varenda beställning okänd, och en
grind som alltid säger okänt har slutat mäta.

## E. De härledda villkoren är nödvändiga, aldrig tillräckliga

| Kod | Bevis |
|---|---|
| `MK4_PASSAR_EJ` | en rektangel `l x b` ryms i `B x D` bara om `(l<=B och b<=D)` eller `(l<=D och b<=B)` |
| `MK3_YTA` | disjunkta ytor i en ruta kan inte summera till mer än rutans yta; med gångstråk `g` blåses varje fotavtryck upp med `g/2` per sida och ryms då inom `(B+g) x (D+g)` |

Bryts en av dem finns **ingen** layout. Håller de båda säger de **ingenting** om
huruvida en layout finns. Protokollet kräver därför att båda riktningarna
provas: ett fall som bryter beviset och ett som inte gör det.

---

## F. Vad protokollet INTE bevisar

* **Att planen bygger rätt cell.** Grinden mäter att planen håller, inte att
  den löser uppgiften. `plan.granska()` fångar ett okänt verktyg, inte ett
  olämpligt.
* **Att koordinaterna är körbara.** Layoutmotorn lämnar ut koordinater bara när
  varje ankare är **mätt** med `get_bounds` i VC. I L1 finns ingen VC, så
  proven kör med `strikt_ankare=False`, och de koordinaterna får inte köras mot
  en riktig scen. Det är fas 5a:s arbete (P5), inte det här protokollets.
* **Att textläsningen förstår svenska.** `lasning.py` läser slutna mönster.
  En beställning formulerad utanför dem ger färre krav, inte fel krav — och det
  som inte lästes blir en fråga. Hur ofta det händer är **inte mätt**.
* **Att processlistan är komplett.** `PROCESSORD` är en sluten lista på 28 ord.
  En process som inte står där blir ingen process alls.
* **Att layoutmotorns nej är matematiskt.** `OVERBESTAMD` gäller det raster som
  söktes. Rasterstegen är mätt (M-63, 81 körningar), men ett fjärde, finare
  steg kan ändra svaret.

## G. Körning

```
python3 -m pytest tests/enhet/test_bestallning.py -q
```

Kräver varken VC, OpenPLC eller kompilator. Kör på en ren maskin.
