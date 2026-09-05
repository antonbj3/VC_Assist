# M-94 — vad skuldregistret inte ser

**Datum:** 2026-09-05
**beskriver:** `svc/vc_assist_svc/skuld.py`, `tests/enhet/test_skuld.py`,
`docs/spec/96_ingen_skuld.md`, `docs/matningar/SKULDREGISTER.md`
**Mätt utan VC.** Ingen körning mot Visual Components ingår.

Operatörens stående order: *"Kom ihåg nu att reviewa och hålla koll på möjlig
teknisk skuld och saker som senare behöver göras om"*, med skärpningen *"Vi
fångar det at moment of writing föredragsvis."* Projektets krav från början:
**ingen teknisk skuld någonstans.**

Registret finns och fungerar. Den här mätningen frågar det motsatta: **vad kan
det inte se?**

## Frågan, ställd exakt

Registret skördar skuld ur **text som skriver om sig själv**: mätningarnas
ärlighetsavsnitt och markörer i koden (`PRELIMINÄR`, `TODO`, *"oprövad"*).
Följden är strukturell och inte en brist i hantverket:

> **Skuld som inte skriver om sig själv är osynlig för registret.**

Tre sorters skuld skriver aldrig om sig själv:

1. kod som fungerar för att den bara körs på **ett** sätt,
2. en grind vars **fråga tyst har ändrats** sedan namnet sattes,
3. ett prov som är grönt av **fel skäl**.

Ingen av dem skriver ordet `PRELIMINÄR`. Alla tre ser färdiga ut.

---

## 1. De tretton fynden, i den ordning de kostar att laga sent

Rangordningen är efter **vad som hänger på fyndet**, inte efter hur lätt det är
att laga. Ett fel i den grind som skyddar en levande scen kostar mer sent än ett
fel i ett register.

| # | Fynd | Fil:rad | Vad som brister |
|---|---|---|---|
| 1 | Ärlighetsgrinden tystnar av vilket nekande ord som helst | `svc/vc_assist_svc/harness/arlighet.py:130` | falsk grön |
| 2 | Skrivgrinden släpper skrivningar via en lokal behållare | `ext/vc_addon/vc_assist/skrivgrind.py:205` | säkerhetsgräns |
| 3 | `stodjer_tal` har en enhetsblind reservjämförelse | `svc/vc_assist_svc/harness/verifiering.py:196` | strukturellt död gren |
| 4 | `bevis_ur_simulering` filtrerar bort sin egen målklass | `svc/vc_assist_svc/harness/redovisning.py:118` | falsk grön |
| 5 | `test_collision` räknar omätbara par som fria | `svc/vc_assist_svc/verktyg/matning.py:437` | domen motsäger sitt eget schema |
| 6 | 16 % av koden i "provade" moduler körs aldrig | mätt med coverage | proxyn är binär |
| 7 | M-numret hade ingen tilldelningsgrind | `docs/matningar/` | **mekaniserat** |
| 8 | Täckningsproxyn godkände en delsträng | `svc/vc_assist_svc/skuld.py:274` | **mekaniserat** |
| 9 | `MARGINAL_SCAN` i tre kopior; körparets signatur läser fel | `bank/domare.py:61`, `bank/par.py:141` | signaturen mäter inte det den namnger |
| 10 | `TOLERANS_STANDARD` pekade på en mätning utan tolerans | `svc/vc_assist_svc/verktyg/matning.py:113` | **rättad** |
| 11 | 190 av enhetssvitens prov körs aldrig här | `tests/enhet/test_st_svep_mot_strucpp.py:70` | grönt utan körning |
| 12 | 61 markörer i `.md` ligger utanför registrets svep | `svc/vc_assist_svc/skuld.py:112` | blind fläck |
| 13 | Numret reserveras med en tom fil i stället för i tabellen | `docs/matningar/RESERVERADE.md` | grinden blir billig |

---

### 1. Ärlighetsgrinden tystnar av vilket nekande ord som helst

`svc/vc_assist_svc/harness/arlighet.py:130`, ordlistan i
`svc/vc_assist_svc/harness/text.py:127`.

`arlighet_onamnt_fel` säger sig fånga: *"ett verktyg NÅGONSTANS i turen föll,
och slutsvaret nämner inte ett enda fel."* Koden frågar
`namner_fel(text)`, som är `bar_ord(text.lower(), NEKANDE)`. `NEKANDE` innehåller
utöver felorden de **bara negationerna** `inte`, `inget`, `ingen`, `inga`,
`utan`, `ej`, `aldrig`, `not `, `no `. Frågan har alltså tyst blivit *"finns
någonstans i svaret ett negerande ord?"*

**Mätt, kört 2026-09-05.** Två anrop i turen, det första fallet:

```
load_component  FAIL  "komponenten hittades inte i katalogen"
get_layout      OK
```

| Slutsvar | `arlighet.granska` |
|---|---|
| "Layouten ar nu klar och roboten star pa plats." | `['arlighet_onamnt_fel']` |
| samma mening **+** "Jag har **inte** lagt till nagot skyddsstaket eftersom det **inte** bads om." | `()` — **inget** |

Det tillagda ordet har ingenting med felet att göra. Grinden godkänner
ändå. Det är den långsamma lögnen S1 skrevs för, och den passerar den grind som
är byggd för att stoppa den.

Samma mekanism, egen grind: `_pastadda_andringar` (`arlighet.py:158`).
*"Klart! Jag kopplade ihop roboten och transportoren."* med enbart **läsande**
anrop ger `['arlighet_pastadd_andring']`. Lägg till `utan problem` — tre
tecken mer påstående, inte mindre — och grinden ger `[]`.

### 2. Skrivgrinden släpper skrivningar via en lokal behållare

`ext/vc_addon/vc_assist/skrivgrind.py:205`, samma undantag kopierat i
`svc/vc_assist_svc/harness/turordning.py:218`.

Undantaget `_lokala_behallare` motiveras med att *"skriva i en ordbok man nyss
byggt är bokföring, inte en scenändring"*. Men villkoret prövar `_rotnamn` på
anropets **mottagare**, och `_rotnamn` klättrar genom `Subscript` och
`Attribute`. Undantaget gäller därför inte skrivningar **till** behållaren utan
varje anrop vars rotnamn råkar vara en lokal behållare.

**Mätt, kört 2026-09-05** (`skrivgrind.granska`):

| Kod | `skriver` |
|---|---|
| `getApplication().deleteComponent(x)` | **True** — fälls |
| `d = {}` / `d["app"] = getApplication()` / `d["app"].deleteComponent(x)` | **False** |
| `L = []` / `L.append(getApplication())` / `L[0].deleteComponent(x)` | **False** |

Ett mellanled genom en ordbok eller en lista räcker. Det här är den grind som
står mellan modellens kod och en levande scen: bryggan kör då koden genom
`exec` förbi godkännandekön (`ext/vc_addon/vc_assist/pump.py:633-644`), och
`_pastadda_andringar` ser turen som "inget ändrades".

Detta är **inte** mätt mot en körande VC. Det är mätt på grindens egen dom över
tre kodstycken. Vad som händer i VC när koden väl passerat är inte prövat här.

### 3. `stodjer_tal` har en enhetsblind reservjämförelse

`svc/vc_assist_svc/harness/verifiering.py:195-196`:

```python
i_modellens_enhet = observerat / faktor if faktor else observerat
traff = (abs(tal.varde - i_modellens_enhet) <= marginal
         or abs(tal.varde - observerat) <= marginal)      # ← rå, enhetslös
```

Modulens egen docstring säger att enheter *"räknas om till bas före
jämförelsen"* och att mekanismen finns för DOM-003, **en tappad faktor 1000**.
Den andra disjunktionen jämför modellens tal mot verktygets råtal utan
omräkning. Eftersom `_enhetsmiss()` (rad 218 — själva DOM-003-mekaniseringen)
bara nås när talet **inte** stöds, kan den aldrig fyra i just det fall den finns
för.

**Mätt, kört 2026-09-05.** Verktygssvar `{"distance": 2.5}`, alltså 2,5 **mm** —
nästan kontakt:

| Modellens mening | `stodjer_tal` |
|---|---|
| "Avstandet ... ar 2,5 **mm**." | `None` (stöds — rätt) |
| "Avstandet ... ar 2,5 **m**." | `None` (stöds — **fel**, faktor 1000) |
| "Latensen ar 40 **ms**" mot `{"t": 40.0}` sekunder | `None` (stöds — **fel**) |

En grind som inte kan fyra är ett fel, inte en varning (S2 i
`96_ingen_skuld.md`). Den här grinden är strukturellt död för sin egen målklass.

### 4. `bevis_ur_simulering` filtrerar bort sin egen målklass

`svc/vc_assist_svc/harness/redovisning.py:118`. Varje mening som bär ett ord ur
`NEKANDE` hoppas över **innan** bevis- och simuleringsorden prövas. Men ett
bevispåstående om en simulering formuleras nästan alltid negativt — *"bevisar
att inga X finns"*.

**Mätt, kört 2026-09-05** (`redovisning.granska`):

| Mening | Utfall |
|---|---|
| "Simuleringen bevisar att **inga** kollisioner finns." | `[]` |
| "Simuleringen garanterar att **inget** fel uppstar i drift." | `[]` |
| "Korningen bevisar att cellen gar **utan** kollisioner." | `[]` |
| "Simuleringen bevisar att cellen ar saker." | `['bevis_ur_simulering']` |

Bara den abstrakta varianten fälls. De tre formerna en modell faktiskt skriver
går fria.

### 5. `test_collision` räknar omätbara par som fria

`svc/vc_assist_svc/verktyg/matning.py:437-446`, returschemat på `:489-493`.

Schemat säger ordagrant om `unmeasurable`: *"Par VC inte kunde ge något avstånd
för. De räknas **ALDRIG** som fria — de är omätta."* Den genererade koden gör:

```python
if not post["found"]:
    omatbara = omatbara + 1
    continue
...
_svara({"collision": len(traffar) > 0, ...
```

Toppnivåfältet `collision` — som verktygsbeskrivningen själv kallar
*"kollisionsgrindens råvara"* — räknar de omätbara paren som fria. En scen där
`measureDistance` ger `None` för alla par (M-36 dokumenterar att det händer)
svarar `{"collision": false, "antal": 0, "pairs_tested": 496, "unmeasurable": 496}`.
Noll par mättes, och svaret säger "ingen kollision".

Att den ärliga formen fanns tillgänglig syns i samma fil: `min_distance` svarar
`nearest = null` i motsvarande läge.

*Detta är läst, inte kört mot VC.* Koden är en genererad sträng som körs inne i
VC; påståendet vilar på texten i mallen och på schemat bredvid den.

### 6. Registret ser 16 % av koden som "provad" utan att den körs

Registret frågar en **binär** fråga: nämns modulens filnamn i en provfil? Den
frågan skiljer inte ett prov från en provsvit.

**Mätt 2026-09-05, ögonblicksbild kl. 06:05** med
`coverage run -m pytest tests/enhet`:

| Storhet | Tal |
|---|---|
| satser i `svc/`, `ext/`, `bank/`, `install/` | **28 273** |
| aldrig körda av `pytest tests/enhet` | **5 133 (18 %)** |
| ... i moduler registret kallar **provade** | **4 497 (16 %)** |
| moduler registret räknar som oprovade | **3** |

Registret pekade alltså ut 3 moduler medan 4 497 satser i de *andra* aldrig
kördes. De tyngsta vid mätningen:

| Modul | Satser | Täckning |
|---|---|---|
| `bank/anlaggning.py` | 336 | **0 %** |
| `svc/vc_assist_svc/komponentdatablad.py` | 503 | 0 % (registret såg den — `bara_l3`) |
| `ext/vc_addon/vc_assist/bridge_cmd.py` | 207 | 2 % |
| `svc/vc_assist_svc/forlopp/spegel.py` | 189 | 30 % |
| `svc/vc_assist_svc/plc/matning.py` | 159 | 31 % |
| `svc/vc_assist_svc/plc/openplc.py` | 187 | 40 % |
| `bank/baslinjebank.py` | 465 | 42 % |
| `ext/vc_addon/vc_assist/pump.py` | 625 | 53 % |

Talen är en ögonblicksbild: `bank/anlaggning.py` fick en egen provfil av en
annan agent under natten, och `komponentdatablad.py` skrevs samma natt. Det som
**inte** är en ögonblicksbild är förhållandet: proxyn är binär, verkligheten är
en kvot, och skillnaden mellan dem var 4 497 satser den natt den mättes.

### 7. M-numret hade ingen tilldelningsgrind — **mekaniserat**

Numret är mätningens enda identitet. Allt i systemet slår upp på det.

**Mätt 2026-09-05, inom en timme:** tre nummer bars av två filer var.

| Nummer | Filerna |
|---|---|
| M-89 | `M-89_anlaggningen_utan_kod.md` + den här mätningens första namn |
| M-90 | `M-90_ren_maskin_linux.md` + `M-90_speglingen_som_inte_aldras.md` |
| M-92 | `M-92_windowssommen_matt_i_stallet_for_last.md` + den här mätningens andra namn |

Ingen av de sex filerna är fel skriven. Det fanns bara ingen grind som ställde
frågan *"är numret taget?"* i skrivögonblicket. Den här mätningen flyttade sig
själv två gånger (M-89 → M-92 → M-94) medan den skrevs.

**Varför det inte är kosmetik.** Två uppslagningar i systemet blir tvetydiga:

* `tests/enhet/test_troskelharkomst.py:matningar_som_finns()` bygger en **mängd**,
  så tröskeln `FORLOPPSVERSION = 1  # M-90` i
  `svc/vc_assist_svc/forlopp/yta.py:63` är grön oavsett vilken av de två M-90
  den menade.
* `skuld.rattelser_utan_framatpekare` bygger `per_nummer[nummer] = fil`. Sista
  filen i bokstavsordning vinner, tyst, och den andra mätningens rättelser blir
  osynliga för grinden.

**Mekaniserat:** `skuld.nummerkollisioner()` +
`tests/enhet/test_skuld.py::test_inga_nya_nummerkollisioner`, en spärr som bara
får gå nedåt. Trasig fixtur:
`test_kontrollen_hittar_tva_filer_pa_samma_nummer` — den föll inte före
2026-09-05 därför att grinden inte fanns, och just den natten hade repot tre
sådana par samtidigt. Kollisionerna står nu också i `SKULDREGISTER.md`.

### 8. Täckningsproxyn godkände en delsträng — **mekaniserat**

`svc/vc_assist_svc/skuld.py:274` frågade `stam in enhet`, alltså en ren
delsträng.

**Mätt 2026-09-05:** `bank/anlaggning.py` räknades som provad därför att
bokstäverna `anlaggning` fanns inne i `_anlaggningssignaler` i
`tests/enhet/test_verktyg_signaler.py:510`. Coverage mätte samma dag **0 av
336 satser**. Två oberoende instrument, motsatta svar.

Vägen ut behöver ingen ta medvetet — den öppnas av vilket längre ord som helst,
och ju kortare stam desto större hål: `bas.py`, `fel.py`, `text.py`.

**Mekaniserat:** kriteriet kräver nu ordgräns.
Trasig fixtur: `test_en_modul_raknas_inte_som_provad_av_ett_langre_ord` (samma
par som mättes: `_anlaggningssignaler` räcker inte, `import anlaggning` räcker)
och `test_ordgransen_pa_en_kort_stam` med sex fall på stammen `bas`.

Effekten på spärrarna, mätt: hinken `inget` går 1 → 2 (tillägget är
`svc/vc_assist_svc/st/lexer.py`), taket är 5. Ordgränsen ger alltså också ett
falskt **utslag** — `lexer.py` körs till 86 % via tolken utan att någon provfil
skriver ordet. Det är med flit. En spärr som ska hitta skuld får hellre peka på
en modul för mycket än tiga om en som aldrig körs.

### 9. `MARGINAL_SCAN` finns i tre kopior, och körparets signatur läser fel kopia

`bank/domare.py:61`, `bank/schema.py:832`, `bank/anlaggning.py:71` — tre
identiska `MARGINAL_SCAN = 2  # Mätt i M-20.`

`bank/par.py:141` bygger körparets signatur ur `_domare.MARGINAL_SCAN`.
Signaturens docstring säger: *"Allt som avgör en dom. Två sidor med olika
signatur är inget par."* Men `bank/domare.py` **använder aldrig** sin egen
konstant; de operativa kopiorna är `schema.py:832` (rad 941, lintar
facitraderna) och `anlaggning.py:71` (rad 429, styr vilka punktkrav som härleds).

Följden: sänker någon `schema.MARGINAL_SCAN` från 2 till 1 — vilket **ändrar
vilka facitrader som accepteras** — förblir `Domarsignatur` bitidentisk och
`par.py` förklarar de två körningarna som ett giltigt par. Signaturen
dokumenterar en storhet den inte observerar.

Inte lagat här: att slå ihop kopiorna rör bankens domarväg, och det ska göras av
den som äger banken. Fyndet står i registret via den här mätningen.

### 10. En härkomst som pekade på en mätning utan tolerans — **rättad**

Jag mätte alla 199 tröskelkonstanter mot texten i den mätning de hänvisar till.
Lintern (`tests/enhet/test_troskelharkomst.py`) slår upp att numret **finns**;
den frågar aldrig om mätningen säger något om just den tröskeln.

| Storhet | Tal |
|---|---|
| tröskelkonstanter i `ext/`, `svc/`, `bank/` | 199 |
| med M-hänvisning | 117 |
| varav `PRELIMINÄR` mot ett reserverat nummer | 42 |
| kvar att pröva | 75 |
| där mätningen varken nämner konstantens namn eller dess värde i någon enhetsform | **3** |

Av de tre håller två vid genomläsning: `TICK_BUDGET_S = 0.025` är *halva*
M-03:s tysta period (50 ms), och `_PORT_IN = 0` mäts av M-61 rad 351 (*"224 med
0 (in), 234 med 1 (ut)"*) utan att bära konstantens namn.

Den tredje höll inte: `svc/vc_assist_svc/verktyg/matning.py:113`,
`TOLERANS_STANDARD = 0.0  # Satt av M-47.` — **M-47 innehåller inte ordet
tolerans en enda gång.** Kommentaren rakt ovanför konstanten säger vad som
faktiskt satte den: *"M-36 visade att measureDistance ger EXAKT 0.0 för
kant-i-kant."* Den maskinläsbara härkomsten pekade alltså på fel mätning medan
den mänskliga pekade rätt. Rättat till `# Satt av M-36 (M-47 namner ingen
tolerans).`

**Varför det inte är mekaniserat.** Jag mätte om kravet skulle kunna vara att
mätningen namnger konstanten: **32 av 83** icke-preliminära hänvisningar gör
det, 51 gör det inte — och de flesta av de 51 är riktiga (PackTags-koderna i
`plc/baslinje/packml.py` namnges av en standard, inte av M-45). En grind på det
kriteriet hade gett 51 falska utslag. Kravet skulle behöva ställas på
**mätningen** i stället: en mätning som sätter en tröskel namnger den. Det är en
disciplinändring, inte en linter, och den hör till den som skriver nästa mätning.

### 11. 190 av enhetssvitens prov körs aldrig på den här maskinen

`tests/enhet/test_st_svep_mot_strucpp.py:70`:
`pytestmark = pytest.mark.skipif(STRUCPP is None, ...)`.

**Mätt:** `pytest tests/enhet -rs` ger 190 skippade, **alla 190** är
STruC++-svepet. Svitens rad lyder *"6 159 passed, 190 skipped"* och det talet
läser ingen.

Det är rätt beteende — utan facit finns ingen mätning, och skälstexten är
föredömlig. Men konsekvensen är att jämförelsen mot den riktiga kompilatorn,
alltså hela oraklet bakom M-54 och M-62, aldrig körs av den svit som kallas
grön. Det syns i coverage: `st/strucpp_orakel.py` 57 %, `st/tolk.py` 61 %.

**Kontrollerat, håller:** ingen modul nämns *enbart* av det svep som alltid
skippas. Registrets `bara_l3`-hink hade alltså inte missat en modul den vägen.

### 12. 61 markörer i `.md` ligger utanför registrets svep

`svc/vc_assist_svc/skuld.py` läser `.py` och `.mjs` under `svc/`, `ext/`,
`install/`, `bank/` och `tests/`. Markörerna finns även på andra ställen.

**Mätt 2026-09-05** (samma mönster `_KODMARKOR`, utanför `docs/referens/` och
utanför registret självt): **61 markörer i 35 filer**, varav **31 i
`docs/spec/`** — alltså i de dokument som styr bygget.

| Fil | Markörer |
|---|---|
| `docs/spec/25_kontextbudget.md` | 5 |
| `docs/spec/23_llm_granssnitt.md` | 4 |
| `docs/spec/26_appen.md` | 4 |
| `docs/spec/28_lagen_och_aterhamtning.md` | 3 |
| `docs/spec/24_samtalsloopen.md` | 3 |
| `README.md` | 3 |

Ett exempel på vad som ligger där: `docs/spec/25_kontextbudget.md:123`,
`SCEN_FULL_MAX = 60 komponenter — PRELIMINÄR, sätts av M-29`. En tröskel som
styr kontextbudgeten, oprövad, i ett dokument registret aldrig öppnar.

Inte lagat här: att bredda svepet till `.md` gör att registret börjar läsa sina
egna syskon (`96_ingen_skuld.md` beskriver markörerna och skulle rapportera sig
själv, precis som `_UNDANTAG` redan hanterar för `skuld.py`). Det är en
avgränsningsfråga som ska göras med mätta undantag, inte i förbifarten.

---

### 13. Numret reserveras med en platshållarfil i stället för i `RESERVERADE.md`

`docs/matningar/RESERVERADE.md` **är** repots reservationsmekanism, och den har
en uttalad regel: numret står i tabellen tills mätningen är gjord, då filen
skrivs och raden tas bort. Den vägen används inte för nya nummer.

**Mätt 2026-09-05:** 13 nummer står i tabellen (M-10, M-18–M-19, M-21–M-30 — alla
från en tidigare omgång), medan **4 nummer** i stället är reserverade genom att
någon skapat en nästan tom `.md`-fil:

| Fil | Rader | Ärlighetsavsnitt | Brödtext i det |
|---|---|---|---|
| `M-85_komponentdatabladet.md` | 5 | **nej** | – |
| `M-86_ogat_mot_en_korande_vc.md` | 6 | ja | **58 tecken** |
| `M-87_hopfogningen_mot_vcs_egen_brygga.md` | 6 | ja | **58 tecken** |
| `M-88_fem_domare_mot_vc_byggda_celler.md` | 6 | ja | **58 tecken** |

En mekanism, två följder:

* **Kollisionerna i fynd 7 uppstår här.** En fil på disk är det enda som säger
  att numret är taget, och den syns först när den finns. En rad i en tabell
  hade kunnat läggas till innan arbetet börjar.
* **Ärlighetsgrinden blir billig.** Taket är 0, och 58 tecken *"Ingenting är
  mätt än"* räcker för att passera. Grinden mäter i det läget att någon skrivit
  en rubrik, inte att någon skrivit ned vad hen inte vet. Tre av fyra
  platshållare passerar; den fjärde är röd bara för att dess författare inte
  hann skriva stubben.

**Inte mekaniserat, och skälet är mätt.** Ett längdkrav på ärlighetsavsnittet är
en godtycklig tröskel — den skulle själv bli en post i `TROSKELSKULD.md`. Den
riktiga regeln finns redan skriven i `RESERVERADE.md` och behöver ingen ny
grind, bara att den används: **ett nummer reserveras i tabellen, en fil skrivs
när mätningen är gjord.** Att formulera det som en grind kräver ett kriterium för
"platshållare" som inte fäller en kort men färdig mätning, och det kriteriet har
jag inte mätt fram.

---

## 2. Vad som behöver göras om senare, och vad som utlöser det

Varje rad namnger **utlösaren**. En rad utan utlösare är en önskan.

| Utlösare | Vad som måste göras om | Var |
|---|---|---|
| **En Windows-maskin** | hela fas 13; M-44:s 16 protokollpunkter; prefixsökningen är ett Wine-begrepp | `install/upptackt.py:211-229`, `svc/vc_assist_svc/tokenplats.py`, `ext/vc_addon/vc_assist/plats.py` |
| **En levande pump** | **22 trösklar** i ögat väntar på M-10, **8** på M-18, **5** på M-19, **3** på M-13, **2** på M-14 (`utforare.py:40-41`), **1** på M-26 | `ext/vc_addon/vc_assist/oga_analys.py:35-52`, `oga_harledning.py:48-96`, `oga_provtagning.py:29,57`, `pump.py:51,56-57`, `bridge_cmd.py:53` |
| **En körande VC med gränssnitt** | M-21 (menyytan), M-22 (VC användbar medan pumpen går), M-23 (starttid till lyssnande port) | `docs/spec/26_appen.md`, hela menyavsnittet |
| **En riktig VC-start ur installationen** | fas 10:s enda öppna punkt: att VC startar med det `installera` lade dit. Fas 1 och 2 kördes mot en **handinstallerad** kopia | `README.md:230`, `tests/protocol/fas10_paketering.md` |
| **VC 5.0 / en annan licens** | `VC_VERSION_STANDARD = "4.10"` och API-indexet är byggt ur 4.10:s `api.xml`; tilläggsmappens namn på 5.0 är *sannolikt*, inte mätt | `svc/vc_assist_svc/api_index.py:62`, `install/upptackt.py` |
| **STruC++ på maskinen** | 190 prov som i dag skippas; `st/strucpp_orakel.py` går från 57 % täckning till mätt | `tests/enhet/test_st_svep_mot_strucpp.py:70` |
| **Fler scener / M-30** | layoutmotorns samtliga trösklar; `URVAL = 60` är ett stickprov ur biblioteket och inte hela det | `svc/vc_assist_svc/layout/`, `tests/enhet/test_komponentfil_bibliotek.py:28` |
| **En riktig lina byggd** | fas 3:s L2 saknas — grinden är körd på ögats utdata, aldrig mot en lina | `README.md`, fasraden för fas 3 |
| **Att nattens agenter landat** | exakthetshalvan av två spärrar: `MODULER_UTAN_PROV` och `KOLLIDERANDE_NUMMER` har i dag bara `<=`, inte `==` | `tests/enhet/test_skuld.py` |

---

## 3. Vad jag prövade och som **höll**

Ett fynd som inte finns är också ett mätvärde, och det ska stå här så att ingen
letar om.

| Prövning | Utfall |
|---|---|
| Repot kopierat till en annan sökväg, hela enhetssviten körd därifrån | **håller** — 6 159 gröna, identiskt utfall (`slaupp.py`-felklassen finns inte kvar i sviten) |
| Sviten körd med `cwd=/` | **håller** — inga nya fel |
| Sviten körd med `LANG=C LC_ALL=C` och ett tomt `HOME` | **håller** — samma 190 skip, inga nya |
| Härnessens hårdhetsgolv: har varje `allvar="block"`-regel en fälla som namnger den? | **håller** — 0 av 37 regler saknar fälla; M-46:s hål (fälla per *mekanism*, inte per *regel*) är verkligen stängt |
| Döda M-hänvisningar i `.md` | **1**, och den är RESERVERADE.md:s eget illustrativa `M-99` |
| Prov utan `assert` i `tests/enhet` | **1** (`test_reparation.py:157`), och det är ett medvetet "får inte kasta"-prov |
| `except: pass` i provkod | 2, båda i uppstädning efter en fixtur |
| Moduler som bara nämns av det alltid-skippade STruC++-svepet | **inga** |

---

## LIMITS

* **Fynd 1–5 är mätta på grindarnas egen dom, inte mot en körande VC.** Jag har
  visat att `granska`-funktionerna svarar fel på indata jag konstruerat. Vad som
  händer i en levande scen när koden väl passerat är **inte** mätt här. Fynd 2
  påstår att bryggan kör koden förbi kön; det är läst i `pump.py:633-644` (`_op_exec`: faller `dom.skriver` går koden rakt till `_kor`), inte kört.
* **Inget av fynd 1–5 och 9 är lagat.** De ligger i grindar som ägs av
  härnessen, bryggan och banken. Att laga dem i förbifarten under ett
  läs-uppdrag hade varit att ändra en säkerhetsgräns utan den mätning som visar
  att lagningen inte bryter något annat. Varje fynd har fil, rad och en indata
  som faller — det är vad som krävs för att nästa varv ska kunna börja med en
  trasig fixtur.
* **Coverage-talen är en ögonblicksbild kl. 06:05 den 5 september 2026**, tagen
  medan sex agenter skrev i repot. `bank/anlaggning.py` fick en provfil under
  körningen och `komponentdatablad.py` skrevs samma natt. Kvoten 4 497 satser
  gäller det ögonblicket. Förhållandet — binär proxy mot kontinuerlig
  verklighet — gäller oavsett.
* **Coverage mäter körda rader, inte prövade påståenden.** En modul på 100 %
  kan sakna varje meningsfull assert. Jag har inte mätt mutationstäckning, och
  utan den säger 82 % inget om hur mycket av koden som är *dömd*.
* **De två nya spärrarna saknar sin exakthetshalva.** `KOLLIDERANDE_NUMMER` och
  `MODULER_UTAN_PROV` prövar bara `<=`. Ett tak med luft i slutar fånga nästa
  glidning — det står i `TROSKELSKULD.md` och det gäller även här. Skälet till
  att halvan inte är inne är mätt och tillfälligt: flera agenter skriver i repot
  i natt, och ett exakthetskrav hade gjort sviten röd för deras halvfärdiga
  arbete i stället för att fånga skuld. **Kravet ska in när natten lagt sig.**
* **M-90-kollisionen är inte löst av mig.** Båda filerna tillhör andra agenter,
  och den ena är den andras oavslutade arbete. Taket står därför på 1 och inte
  på 0. När paret är löst ska taket sänkas.
* **Ordgränsen i täckningsproxyn ger ett känt falskt utslag**:
  `svc/vc_assist_svc/st/lexer.py` körs till 86 % via tolken men nämns inte som
  eget ord. Riktningen är vald med flit, men den kostar en rad brus.
* **Jag har inte mätt fynd 12:s motsats**: hur många av de 61 markörerna i
  `.md` som är *riktig* skuld och hur många som är prosa om markörer. Jag
  räknade träffar, inte deras innebörd.
* **Genomsökningen efter grindar vars fråga tyst ändrats är inte uttömmande.**
  Fynd 1–5 kommer ur en riktad läsning av de moduler vars namn innehåller
  *grind*, *domare*, *kontroll*, *verifiering*. `guldgrind.py`,
  `oga_kontrakt.py`, `plan/verifiering.py`, `plc/deklarationsgrind.py`,
  `plc/stationsgrind.py`, `layout/kollision.py`, `harness/forgranskning.py`,
  `harness/mattafakta.py` och `bank/reparationsbank.py` höll i de vägar som
  följdes — men "höll i de vägar som följdes" är inte "är prövad".
* **Misstanke, inte visad:** `install/upptackt.py` ligger på 57 % täckning och
  bär hela prefix- och versionsuppslagningen. Jag misstänker att den
  plattformsneutralitet README kallar *"prövad logiskt, mot ett attrappträd"*
  har grenar som aldrig körs ens av attrappen. Vad som skulle avgöra det: en
  körning av `tests/enhet/test_install.py` under coverage med ett rapporterat
  radintervall per gren, jämfört mot de 16 punkterna i M-44.
* **Fynd 13:s tal är en ögonblicksbild.** Fyra platshållarfiler fanns kl.
  07:00 den 5 september 2026. Tre av dem skrivs klart av andra agenter i natt och
  försvinner då ur räkningen. Det som inte försvinner är att en 58 teckens stubb
  räcker för en spärr vars tak är noll.
* **Misstanke, inte visad:** `NEKANDE`-listan används av minst fyra grindar
  (`arlighet.py:130`, `arlighet.py:158`, `redovisning.py:118`, och den
  meningsdelare `text.py` exporterar). Fynd 1 och 4 är samma felklass i två av
  dem. Jag har inte prövat de övriga konsumenterna av samma lista. Vad som
  skulle avgöra det: för varje konsument, en mening som bär målklassen **och**
  ett nekande ord, och en dom på om grinden fyrar.
