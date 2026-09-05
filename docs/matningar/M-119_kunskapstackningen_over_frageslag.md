# M-119 — modellen hittar nästan alla NAMN och nästan ingen BETYDELSE

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_kunskapstackning.py`
**Det som prövas:** `tests/protocol/stod/slaupp.py` och det den når —
`api_index.py`, `katalogsok.py`, `katalogindex.py`, `komponentdatablad.py`,
`verktyg/kunskap.py`
**Prövar:** om M-84:s, M-85:s och M-96:s tre hörn generaliserar

## Frågan

Tre mätningar har provat uppslagen, var och en i sitt hörn.

`M-84`: en modell som skrev scenkod **utan** uppslag använde 13 distinkta
API-namn, där `getApplication` och `findComponent` ensamma var 61 % av alla
kontroller. Med uppslag: 32 namn, `getApplication` från 188 anrop till 3. Och
de mest värdefulla uppslagen var de som svarade **SAKNAS** — `VC_BOOLSIGNAL`
var på väg in i tre filer eftersom *typen* heter `vcBoolSignal`.

`M-85`: databladet läser 3 201 komponenter, men bara **14 %** av 82 383
egenskaper deklarerar vilken storhet de bär.

`M-96`: 0 av 20 utan grindregler, 6 av 20 med — och hela effekten satt i **en**
uppgift.

Ingen har frågat brett. Den här mätningen gör det: **finns svaret på plats, för
varje sorts fråga modellen faktiskt ställer?**

## Korpusen: 1 025 frågor, härledda och inte hittade på

Varje fråga går att spåra till en rad i en fil som skrevs före verktyget.
Härledningen står i `harled()` och är mekanisk — den läser filerna, den
formulerar ingenting fritt.

| Källa | Vad som lästes | Blev |
|---|---|---|
| `docs/spec/48_personaprofiler.md` | 228 arbetssteg, kolumnen **Kräver** | 238 API-namn (S1), 63 typer (S2), 21 konstanter (S3) |
| `bank/uppgifter/*.json` (63 st) | `scene.components[].uri` | 75 `bank://`-URI:er (S4), 75 biblioteksfrågor (S5) |
| `bank/katalog_index.json` | fältnamnen `rackvidd_mm`, `nyttolast_kg`, `anslag_s` … | 68 måttfrågor (S8) + 14 enhetsfrågor (S6) |
| `bank/uppgifter/*.json` | `control.signals` (454 distinkta) | 94 signalfrågor (S7) |
| `bank/uppgifter/*.json` | ISO/IEC/EN/VDA-referenser i hela texten | 23 standardfrågor (S9) |
| `bank/uppgifter/*.json` | `expect.lines`, `forbidden_lines`, `gate`, `must_pass` | 31 grindfrågor (S10) |
| `M-84` och `M-85`:s öppna punkter | de namn de skrev ut som osäkra | 20 gränsfallsfrågor (S11) |
| `bank/uppgifter/*.json` | `scenarios` som inte är normaldrift | 211 frågor som **KRÄVER VC** (S12) |

`UI:`-, `.NET:`- och `TJÄNST:`-posterna i Kräver-kolumnen är inte frågor till
ett VC-uppslag och ställdes inte.

Två steg i korpusen beror på svaren och inte bara på filerna, därför att en
modell också gör så:

* **omtaget.** Bankens namn bär tillverkarprefixet (`ABB IRB 1200-5/0.9`),
  bibliotekets gör det inte (`IRB 1200-5/0.9`) — det är M-85:s mätning. Varje
  biblioteksfråga som gav noll träffar ställdes en gång till utan första ordet.
* **databladet.** S6 frågar om **den komponent omtaget fann**, inte om bankens
  namn. Verktygets egen notering säger det: *"Sök med search_installed_library
  först."*

## De fyra klasserna, och regeln som avgör var gränsen går

| Klass | När | Antal |
|---|---|---|
| **SVAR** | frågan besvaras, med värde **och** härkomst | 407 |
| **HALVT** | något kommer tillbaka, men utan enhet, utan källa eller tvetydigt | 98 |
| **SAKNAS** | verktyget säger ärligt att det inte vet | 303 |
| **TYST FEL** | svaret **ser ut** som ett svar och är det inte | **6** |
| KRÄVER VC | frågan går inte att besvara utan en körande VC | 211 |

Varje klassning bär ett **regelnamn** (`R3_ANNAT_NAMN_AN_FRAGAT`,
`R52_NOLLA_UTAN_ENHET` …) som står i JSON-filen bredvid frågan, så att en
enskild dom går att slå upp och bestrida. Tre av reglerna är de som gör
mätningen till något annat än en träffräkning:

* **Ett tal utan deklarerad enhet är inget SVAR.** Databladet skriver själv
  `storhet saknas` och `ENHET EJ DEKLARERAD` — det är ärligt, men för den som
  frågade efter en storhet är raden halv.
* **En NOLLA utan enhet är ett tyst fel.** Den ser ut som ett mätt värde.
* **En delsträngsträff i ett namn är inte en namnträff.** `RACE` träffar
  `traceOn` därför att "race" står inne i "trace". Verktyget deklarerar själv
  var träffen kom ifrån (`rang`), och domen läser den deklarationen i stället
  för att gissa.

## Täckningen per frågesort

M-96 visade varför summan är fel storhet: den dolde att hela effekten satt i en
uppgift. Summan här är **50,0 % SVAR av 814 körda frågor**, och den siffran
säger ingenting. Fördelningen säger allt:

| # | Frågesort | frågor | SVAR | HALVT | SAKNAS | TYST | andel SVAR |
|---|---|---|---|---|---|---|---|
| S2 | Typens hela yta | 63 | 63 | 0 | 0 | 0 | **100 %** |
| S4 | `bank://`-URI:er | 75 | 75 | 0 | 0 | 0 | **100 %** |
| S1 | API-namn och signatur | 238 | 201 | 37 | 0 | 0 | **84,5 %** |
| S11 | VC:s beteende, dokumenterat | 20 | 13 | 7 | 0 | 0 | 65,0 % |
| S8 | Geometri och mått (banken) | 68 | 38 | 10 | 20 | 0 | 55,9 % |
| S8b | … samma, andra försöket | 20 | 10 | 1 | 7 | **2** | 50,0 % |
| S5b | Komponenten i biblioteket, omtag | 72 | 7 | 0 | 65 | 0 | 9,7 % |
| S3 | Konstantnamn (`VC_*`) | 21 | **0** | 21 | 0 | 0 | **0 %** |
| S5 | Komponenten i biblioteket | 75 | **0** | 0 | 75 | 0 | **0 %** |
| S6 | Egenskapernas enheter | 14 | **0** | 12 | 0 | **2** | **0 %** |
| S7 | Signalkartans namn och riktning | 94 | **0** | 0 | 94 | 0 | **0 %** |
| S9 | Standardhänvisningar | 23 | **0** | 0 | 23 | 0 | **0 %** |
| S10 | Grindarnas regler | 31 | **0** | 10 | 19 | **2** | **0 %** |
| S12 | VC:s beteende, kräver VC | 211 | — | — | — | — | kördes inte |

**Sex frågeslag av tretton har noll svar.** Det är inte en jämn femtioprocentig
täckning; det är två skarpa halvor.

### Vad de gröna sorterna faktiskt gör

`S2` och `S4` är helt gröna, och båda av samma skäl: de svarar på **finns
den, och vad heter den**. `S1` ligger på 84,5 % och de 37 halva är
informativa:

| varför halvt | antal |
|---|---|
| svaret namnger en **annan typ** än den frågade (ärvd medlem) | **26** |
| namnet finns men **ingenting säger vad det gör** | 6 |
| metod utan parameterlista | 5 |

De 26 är samma form varje gång: `vcComponent.findBehavioursByType` besvaras med
`vcNode.findBehavioursByType`, `vcRobotController.Joints` med
`vcServoController.Joints`, `vcRoutine.addStatement` med `vcScope.addStatement`.
Arvet är korrekt — men svaret säger inte att medlemmen är **ärvd**, och samma
svar avslutas med raden *"Använd namnet exakt som det står. Omformulera det
inte."* En modell som lyder bokstavligt skriver `vcNode.findBehavioursByType(...)`.

### Sorten som är noll från början till slut: konstanterna

`S3` är 0 av 21, alla av samma skäl, och orsaken är strukturell:

| symbolslag | antal | utan beskrivning |
|---|---|---|
| egenskap | 1 178 | 0 (0 %) |
| metod | 1 170 | 76 (6,5 %) |
| **konstant** | **709** | **709 (100 %)** |
| typ | 212 | 212 (100 %) |
| händelse | 175 | 175 (100 %) |

**Indexet bär 709 konstanter och inte en enda beskrivning av vad någon av dem
betyder.** `VC_BOOLEANSIGNAL`, `VC_STATEMENT_WAITSIGNAL`, `VC_ONETOONEINTERFACE`
— namnet bekräftas, betydelsen finns inte. Det är exakt den symbolklass M-84
mätte som den mest värdefulla: det uppslag som stoppade `VC_BOOLSIGNAL` i tre
filer svarade **SAKNAS**, och det var värdefullt just för att det var ett
nej. Ett *ja* på ett konstantnamn bär däremot ingenting alls.

## De sex tysta felen, med namn

| id | fråga | vad verktyget svarade |
|---|---|---|
| `S8-009b` | Hur stor är räckvidden för ABB IRB 1200-7/0.7? | `rackvidd_mm = 0` — tillverkarens datablad säger **703 mm** |
| `S8-015b` | Hur stor är räckvidden för ABB IRB 1200-5/0.9? | `rackvidd_mm = 0` — tillverkarens datablad säger **901 mm** |
| `S6-009` | Vilken egenskap bär räckvidden på IRB 1200-7/0.7? | `Reach (… ENHET EJ DEKLARERAD …): 0` |
| `S6-013` | Vilken egenskap bär räckvidden på IRB 1200-5/0.9? | `Reach (… ENHET EJ DEKLARERAD …): 0` |
| `S10-006` | Vad betyder raden `RACE` i sektionen TIMING? | `vcHelpers.Robot.traceOff`, `traceOn`, `Robot2.traceOff`, `Robot2.traceOn` — fyra träffar med rang `delstrang_namn`, därför att "race" står inne i "trace" |
| `S10-008` | Vad betyder raden `MINDIST` i sektionen SAFETY? | `vcCurveData.getCurveMinDistance` |

Två saker skiljer de här sex från de 303 som svarade SAKNAS. De ser ut som
svar. Och de har alla ett **facit utanför verktyget**: bankens katalogindex
stämplat `PUBLICERAD_SPEC` (tillverkarens publicerade datablad) för de fyra
första, och ögats egen grammatik i `docs/spec/41_ogat_kontrakt.md` för de två
sista.

**Nollan är inte ett stickprov.** Räknat över hela det installerade
biblioteket, 3 201 komponenter:

| fält | ett värde | **NOLLA** | `None` (ärligt saknat) |
|---|---|---|---|
| `rackvidd_mm` | 1 437 (44,9 %) | **1 119 (35,0 %)** | 645 (20,1 %) |
| `nyttolast_kg` | 2 358 (73,7 %) | **628 (19,6 %)** | 215 (6,7 %) |

De 628 är samma 628 som `M-107` mätte oberoende (`MaxPayload = 0`). Att två
mätningar med olika kod ger samma tal är det närmaste en bekräftelse den här
körningen kommer.

Och raden som gör det till ett hål och inte ett faktum: **koden kan redan
uttrycka "saknas"** — 645 poster bär `None` för `rackvidd_mm`. Nollan är alltså
inte en gräns i formatet, den är en förlorad skillnad i läsningen.

## Sorterna som är tomma därför att ingen väg leder dit

Tre frågeslag — 148 frågor — får **noll** svar, och skälet är inte att svaret
inte finns:

| sort | frågor | finns svaret på disk? | var |
|---|---|---|---|
| S10 grindregler | 31 | **ja, fullständigt** | `docs/spec/41_ogat_kontrakt.md` bär hela grammatiken **med enheter** |
| S9 standarder | 23 | **ja, på paragrafnivå** | `facit_spar.standard` i **26 av 63** bankuppgifter |
| S7 signalkartan | 94 | delvis | `control.signals` i varje bankuppgift (namn, riktning, typ) |

Två mätta orsaker:

1. **Inget av tjänstens 14 dataverktyg läser `docs/spec/`.** De enda
   dokumentkataloger någon handlare öppnar vid körning är
   `docs/referens/vc_api/` (api_index.py rad 137) och
   `docs/referens/vc_dotnet/` (signaler.py rad 386). Specen — där ögats
   grammatik och grindarnas regler står — är oåtkomlig för ett uppslag.
2. **`bench_task` lämnar 9 av bankuppgiftens 23 fält utanför sitt svar:**
   `control`, `fysik`, `antaganden`, `scenarios`, `failure_modes`, `orsak`,
   `facit_spar`, `verified_status`, `last_run`. Signalkartan, måtten och
   standardparagraferna ligger alla i den listan.

Att `slaupp.py` bara når **7 av tjänstens 14** dataverktyg spelar mindre roll än
det ser ut: `type_surface` svarar redan på `vcHelpers.Robot` med 55 medlemmar,
så M-84:s fjärde öppna punkt (`Robot` mot `Robot2`) är inte stängd av en ny
väg utan av en fråga som redan finns.

**En rättelse mot min egen första läsning:** `lookup_helper` returnerar
`antal: 0` utan `found` när modulnamnet är `Robot` i stället för
`vcHelpers.Robot`, och det såg ut som ett tyst fel. Det är det inte längs den
riktiga vägen — `verktyg/schema.py` avvisar argumentet mot ett `enum` **innan**
handlaren körs. Bara en anropare som går förbi utföraren ser nollan.

## De tre dyraste hålen

Rangordnade efter M-84:s mall: ett hål som får modellen att **skriva fel kod**
är dyrare än ett som får den att **avstå**. De 303 SAKNAS är därför billiga —
de är verktyget som gör sitt jobb.

### 1. Nollan som ser ut som ett mått — 35 % av biblioteket

En modell väljer robot på räckvidd. `rackvidd_mm = 0` betyder antingen "denna
robot når ingenting" (och modellen väljer bort en robot som räcker) eller, om
den läser det som saknat, att den gissar. Båda skriver fel kod, och ingenting i
svaret varnar. Fältet bär redan `None` i 645 poster, så skillnaden mellan
**noll** och **okänt** finns i formatet och tappas i läsningen. Det är det
billigaste hålet att stänga och det dyraste att lämna.

### 2. 709 konstanter utan en enda betydelse — hela frågeslaget är noll

Indexet kan säga att `VC_BOOLEANSIGNAL` finns. Det kan inte säga vad den är
till för, vilken metod den hör till eller vad som händer när komponenten inte
bär någon signal av den typen. M-85 mätte att **88,1 %** av biblioteket bär noll
boolska signaler — `findBehavioursByType(VC_BOOLEANSIGNAL)[0]` kastar
`IndexError` på nio komponenter av tio. M-84:s modell skrev den raden 16
gånger. Uppslaget bekräftade namnet varje gång och kunde inte säga något om
raden.

### 3. Grindens egna rader besvaras ur fel källa

`S10` är 0 av 31, men tio av dem är inte tysta nej: åtta får API-träffar i en
annan domän (`PLACE` → `vcHelpers.Robot.place`, `COLLISION` →
`vcCollisionDetector`, `MOTION` → `MotionTime`) och två är rena
delsträngsfel (`RACE` → `traceOn`, `MINDIST` → `getCurveMinDistance`). Modellen
frågar vad cellen måste **skriva ut** för att grinden ska släppa den, och får
tillbaka VC:s API. Svaret ligger färdigt i `41_ogat_kontrakt.md`, rad för rad,
med enheter utskrivna. Ingen väg går dit.

## Vad mätningen inte gjorde

* **Visual Components startades aldrig.** 211 frågor (S12) hör till en körande
  scen och rördes inte.
* **Frågorna är inte modellens.** De är härledda ur bank och spec. En riktig
  modell ställer några av dem, ställer andra i annan ordning, och ställer
  frågor ingen fil förutsåg.

## LIMITS

* **Ingen modell var med i körningen.** Mätningen frågar verktygen direkt.
  Att en fråga får SVAR är inte samma sak som att en modell hade ställt den,
  förstått svaret eller skrivit rätt kod av det. M-84 mätte den delen; den här
  mäter bara om svaret finns att hämta.
* **Klassgränserna är mina regler, inte en naturlag.** Att ett svar som namnger
  en ärvd medlem är HALVT och inte SVAR är ett val; det är motiverat av att
  verktyget samtidigt säger "använd namnet exakt som det står", men en annan
  läsare kan kalla de 26 gröna. Varje dom bär sitt regelnamn i JSON-filen just
  därför.
* **Frågesorterna är olika stora och det gör dem inte jämförbara.** 238
  API-namn mot 14 enhetsfrågor. Andelen inom en sort är jämförbar över tid;
  andelarna mellan sorter är det inte.
* **S6 vilar på 14 frågor.** Bara sju bankposter går alls att brygga till
  biblioteket (efter omtaget), och bara de bär både `rackvidd_mm` och
  `nyttolast_kg`. Talet 0 % SVAR för enheterna är riktigt men tunt — det som
  bär den slutsatsen är i stället M-85:s 86 % utan storhetsdeklaration över
  82 383 egenskaper och den biblioteksvida nollräkningen ovan.
* **Facit finns bara för en del av frågorna.** De fyra nollfelen och
  avvikelsen mot `KR 10 R1100 sixx` (biblioteket 1 100 mm, banken 1 101 mm) är
  prövade mot bankens `PUBLICERAD_SPEC`. För resten är facit att svaret bär
  värde **och** härkomst — en formkontroll, inte en sanningskontroll. Ett
  verktyg som svarar självsäkert och fel på ett API-namn hade räknats som SVAR.
* **`S11` dömer dokumentationstexten, inte VC.** Regeln är mekanisk: bär
  beskrivningen en villkorssats (`if`, `otherwise`, `returns None`, `empty
  list`)? Sju av 20 gör det inte. Att de tretton andra gör det bevisar inte att
  texten stämmer med hur VC 4.10 faktiskt beter sig.
* **Ett bibliotek, en installation.** 3 201 komponenter i VC 4.10:s eCatalog på
  den här maskinen. Andelarna 35,0 % och 19,6 % gäller den.
* **Delsträngsregeln kan ge falska tysta fel.** `MINDIST` mot
  `getCurveMinDistance` är en riktig träff i sak — det är ett minimiavstånd —
  men frågan gällde ögats rapportrad, och verktyget säger inte att det svarar om
  något annat. Jag klassar den som tyst fel därför att svaret inte bär den
  skillnaden, inte därför att symbolen är fel.
* **Cachen.** 814 körda frågor blev 694 distinkta anrop; identiska `(verktyg,
  argument)`-par kördes en gång. Verktyget läser bara filer på disk, så svaret
  är detsamma — men tidsmätningen per fråga gäller det första anropet, inte
  medelvärdet.
