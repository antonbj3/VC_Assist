# M-89 — vad ett inspelat I/O-spår från en befintlig anläggning räcker till

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_fas18_anlaggning.py`
**Grinden:** `bank/anlaggning.py`, prövad av `tests/enhet/test_anlaggning.py`
**Gäller:** fas 18 i `docs/spec/70_faser.md`
**Bygger på:** `M-75` (premissen), `M-45` (spårfacitets form), `M-20` (scan och marginal),
`M-80` (fas 9:s tre tal)

## Frågan, ordagrant

Operatören:

> *"finns någon möjlighet att gå omvända riktningen -> maskinkod till structured
> text, i vårt simuleringsscenario, för tror det är ganska vanligt att
> originalkod och sånt tappas bort"*

och vägen dit, också ordagrant:

> *"Man lyssnar väl på kablarna typ, och lägger ihop signalerna?"*

Det senare är vägen. Maskinkod går inte tillbaka: STruC++ kompilerar åt ett håll
och dekompilering är inte vägen. Det som finns att arbeta med är
uppladdningsformatet eller **spåret** — och ett spår har redan bänkens facitform.

Den här mätningen svarar på hur mycket det räcker till, och den kan göra det
därför att vi har fyra fall där **svaret är känt**: bankens spårfacituppgifter
har både en referenslösning och ett handskrivet facit med motbevis. Vi kör det
kända programmet, spelar in spåret, **kastar bort källkoden**, härleder ett facit
ur inspelningen ensam — och frågar sedan hur mycket av det kända facit som kom
tillbaka.

## Vad som spelades in, och vad som inte gjorde det

Inspelningen läser **bara signalkartan**, scan för scan, genom
`svc/vc_assist_svc/st/tolk.py`. Stegvariabeln, timrarnas ackumulatorer och de
16–66 villkorsgrenar `M-75` räknade följer aldrig med. Det är samma form en
OPC UA-prenumeration eller en avlyssning på I/O-plinten ger.

Två inspelningar per uppgift, och skillnaden är hela mätningen:

| | vad det är |
|---|---|
| **provspåret** | alla bankens sekvenser. Någon har *ansträngt sig* för att provocera kallstart, larm, kvittens, tidsvakt och återstart. Bästa möjliga fall, och det finns inte på en riktig linje |
| **produktionsspåret** | ett fönster ur normaldriften, upprepat 1 och 10 gånger. Det är vad en anläggning faktiskt ger |

Vilket fönster som är normalproduktion är ett **människoval**, och det står i
klartext i `PRODUKTIONSFONSTER` i körningen, med skälet. Det är precis vad en
anläggning ger: du får den timme någon råkade spela in. Avsnitten avidentifieras
innan de går vidare (`A01`, `A02`, …) — bankens sekvensnamn är en människas
beskrivning av vad stationen ska göra, och en anläggning lämnar inte ifrån sig
den.

| uppgift | signaler | provspår | produktion ×1 | produktion ×10 | valt fönster |
|---|---:|---:|---:|---:|---|
| T-07 | 12 | 633 | 71 | 710 | `en_detalj_hela_vagen` |
| H-04 | 20 | 706 | 131 | 1310 | `hel_overlamning` |
| S-05 | 8 | 725 | 84 | 840 | `hel_produktionscykel` |
| L-05 | 17 | 996 | 71 | 710 | `ett_lager_i_automatlage` |

## Talet: 28 av 28, och 3 av 28

Bankens handskrivna invarianter, nedbrutna i förbjudna tvåsignalstillstånd — det
är den form härledningen letar efter, så jämförelsen är mellan samma sorts
påstående. Hur många av människans förreglingar återfann härledningen?

| uppgift | människans | ur provspåret | ur produktionsspåret |
|---|---:|---:|---:|
| T-07 | 6 | 6 | 1 |
| H-04 | 9 | 9 | 2 |
| S-05 | 2 | 2 | 0 |
| L-05 | 11 | 11 | 0 |
| **summa** | **28** | **28** | **3** |

**Ur ett spår som någon byggt för att pröva logiken kommer allt tillbaka. Ur ett
spår från normal produktion kommer en niondel.**

Det är svaret på operatörens fråga, och det är inte ett nej. Det säger vad man
får och vad man inte får: en anläggning som går kan ge sitt eget beteende, men
inte de förreglingar som aldrig löser ut.

**Och baksidan av samma tal.** Ur provspåren härledde härledningen **143**
förbud. 28 av dem är människans förreglingar; **115 är påståenden ingen har
prövat**. Att alla 28 kom tillbaka betyder alltså inte att härledningen träffar
rätt — det betyder att den kastar ett tillräckligt brett nät för att de ska
hamna i det. Vilka av de 115 som är verkliga och vilka som är tillfälligheter
kan spåret inte avgöra, och det är precis vad avsnittet om korrelation nedan
mäter.

## Fasens grind: täckning innan påstående

Bankens egna 18 handskrivna invarianter, prövade mot produktionsspåret:

| uppgift | invarianter | otäckta | vilka |
|---|---:|---:|---|
| T-07 | 4 | 3 | `inget_don_med_brutet_nodstopp`, `larm_stoppar_stationen`, `ingen_klamma_utan_tryckluft` |
| H-04 | 5 | 3 | `ingen_rorelse_med_brutet_nodstopp`, `ingen_rorelse_i_bruten_zon`, `larm_stoppar_bada` |
| S-05 | 4 | 2 | `inget_band_med_brutet_nodstopp`, `vandaren_ror_sig_bara_i_execute` |
| L-05 | 5 | 4 | `inget_don_med_brutet_nodstopp`, `larm_stoppar_lyftet`, `automatiken_star_still_i_handlage`, `lyftbordet_gar_aldrig_at_bada_hallen` |
| **summa** | **18** | **12** | |

`EMG_OK` gick **aldrig** till 0 i produktionsspåret, i **alla fyra**
uppgifterna. Ett stillastående nödstopp som ingen tryckt på säger ingenting om
vad som händer när någon gör det, och grinden vägrar påstå det.

**Kontrollen, och utan den är grinden trivial:** samma 18 invarianter mot
**provspåret** ger **0** otäckta. Grinden vägrar alltså inte allt — den vägrar
det inspelningen inte bär. En grind som avvisar allt ser lika bra ut som en som
fångar rätt sak, om man bara räknar avvisningar.

**Tysta signaler i produktionsspåret: 24 av 57.** T-07 5 av 12, H-04 6 av 20,
S-05 4 av 8, L-05 9 av 17. `M-75` mätte 0–2 tysta per uppgift i provspåret; i
produktionsspåret är det en tredjedel till hälften av signalkartan.

## Mer data ur samma gren är inte mer täckning

| uppgift | rader ×1 | rader ×10 | otäckta ×1 | otäckta ×10 |
|---|---:|---:|---:|---:|
| T-07 | 71 | 710 | 3 | 3 |
| H-04 | 131 | 1310 | 3 | 3 |
| S-05 | 84 | 840 | 2 | 2 |
| L-05 | 71 | 710 | 4 | 4 |

Tio gånger så många avläsningar, exakt samma täckning. Det är `M-75`:s slutsats
som ett tal: *"ett dygns spår därifrån ger tusentals rader ur samma gren och noll
ur de andra."* Nu är den mätt i stället för resonerad.

## Diskriminerande kraft: samma motbevis, tre facit

Bankens motbevis är lösningar som **ser riktiga ut** men bryter mot ett krav.
Talet har ett känt tak: det handskrivna facit fäller alla 18.

| uppgift | motbevis | handskrivet facit | facit ur provspåret | facit ur produktionsspåret |
|---|---:|---:|---:|---:|
| T-07 | 4 | 4 | 4 | 1 |
| H-04 | 4 | 4 | 4 | 2 |
| S-05 | 5 | 5 | 5 | 1 |
| L-05 | 5 | 5 | 5 | 0 |
| **summa** | **18** | **18** | **18** | **4** |

Ett facit härlett ur ett *provspår* är alltså lika strängt som människans. Ett
facit härlett ur *normalproduktion* fäller **4 av 18** — och de fjorton som slipper
igenom är fjorton verkliga driftsättningsfel som ingen hade märkt.

**Golvet är inte noll.** Ett program som **styr ingenting** — varje utgång
skriven en gång, till noll — fälls av **alla tre** facit i **alla fyra**
uppgifterna, produktionsspårets inräknat. `M-62` mätte att ett sådant program
passerar grind 1–3 på 37 av 37 uppgifter, så det var inte givet. Ett facit ur ett
produktionsspår är alltså inte tomt; det är trubbigt.

## Korrelation är inte orsak, som ett tal

En invariant "när A = a ska B = b" är samma påstående som "tillståndet
(A = a, B = ¬b) förekommer aldrig". Härledningen letar därför efter
**tvåsignalstillstånd inspelningen aldrig visade** och föreslår dem som förbud.
Formuleringen gör faran uppenbar i en mening: *påståendet är att ett tillstånd
ingen sett är omöjligt.*

Ur produktionsspåren härleddes **80 förbud**. Provspåret — samma anläggning,
andra dagar — **motbevisar 11 av dem**:

| uppgift | härledda ur produktion | motbevisade av provspåret |
|---|---:|---:|
| T-07 | 14 | 2 |
| H-04 | 48 | 0 |
| S-05 | 0 | 0 |
| L-05 | 18 | 9 |
| **summa** | **80** | **11** |

Var och en av de elva såg ut som en förregling i normaldrift. `L-05` är värst:
**nio av arton** påståenden ur ett dygns palleteringsdrift är falska. De
återstående 69 är inte därmed sanna — de är bara inte motbevisade av den andra
inspelningen heller.

Och härledningen vägrade dessutom **243 påståenden** ur produktionsspåren mot
**46** ur provspåren, vart och ett med sitt skäl: villkoret sågs aldrig, villkoret
gällde i varje avläsning, eller kravsignalen stod still hela inspelningen.

## Grinden och dess trasiga fixturer

`bank/anlaggning.py` har fyra felkoder. Var och en har både en fixtur som fäller
den och ett kontrollfall som visar att den inte fäller när täckningen bär.

| kod | fäller på | trasig fixtur | kontrollfall |
|---|---|---|---|
| `T1_OTACKT_VILLKOR` | invariantens villkor sågs aldrig | nödstoppsinvariant mot en inspelning där `EMG_OK` aldrig bröts | samma invariant mot en inspelning där det bröts — släpps igenom |
| `T2_OKAND_SIGNAL` | påståendet läser en signal spåret inte har | krav på `FINNS_INTE` | — |
| `T3_UTAN_UNDERLAG` | härlett påstående utan sin nämnare | härlett facit med `underlag` bortplockat, och ett utan `tackning` | handskrivet facit kräver ingen nämnare: dess härkomst är en standard, inte en observation |
| `T4_OTACKT_KRAV` | kravet vill ha ett värde signalen aldrig antog | punktkrav `BAND = 0` när bandet stod på 1 hela inspelningen; flankkrav på en flank som aldrig hänt | flankkrav på **noll** flanker — "den pulsade aldrig" är något spåret faktiskt visade |

Utöver grinden: **härledningen behöver aldrig grinden.** Ett prov kör
härledningen på en inspelning utan nödstopp och kräver att `EMG_OK` inte
förekommer i ett enda härlett påstående, varken som villkor eller som krav — och
att de vägrade påståendena ligger kvar med sitt skäl.

## Instrumentet mot ett känt svar jag själv injicerade

Ett tal som ser rimligt ut, från ett instrument ingen prövat mot ett känt svar,
är projektets vanligaste fel (`M-34`, `M-57`, `M-66`, `M-69`, `M-76`, `M-77`).
Täckningsräknaren är därför inte provad mot en bankuppgift utan mot spår där
**varje rad är handskriven**, så att svaret går att räkna ur mönstret:

| mönster (`EMG_OK` per avläsning) | episoder | avläsningar |
|---|---:|---:|
| `1111111111` | 0 | 0 |
| `1100111111` | 1 | 2 |
| `1001001111` | 2 | 4 |
| `0101010101` | 5 | 5 |
| `0000000000` | 1 | 10 |

Och en fälla som är lätt att gå i: `11110` följt av `01111` i **två skilda
avsnitt** är **två** episoder, inte en. Mellan två inspelningar vet ingen vad som
hände.

Två prov till, av samma sort:

* **Det härledda facit uppfylls av programmet det kom ur.** En anläggning lämnar
  ingen källkod, så ett härlett facit har ingen referenslösning att bevisa
  uppfyllbarheten med. Beviset är inspelningen själv, och det provas: referensen
  går igenom sitt eget spår i alla fyra uppgifterna, i båda inspelningarna.
* **Och det fäller en muterad station.** Ett facit som inget fäller mäter
  ingenting. Mutationen tar bort detaljgivaren ur klämmans villkor och syns bara
  i vilka tillstånd som förekommer tillsammans.

## Modellen skriver ST ur spåret

Samma uppställning som fas 9 (`M-80`): det finns **ingen API-nyckel och ingen
byggd modellklient** i repot, så modellen är en Claude-agent (Opus) som fått
**exakt** anläggningsbriefen och ingenting annat — I/O-listan med anläggningens
egna taggkommentarer, hela tidsserien, flankräkningarna, de härledda förbuden och
listan över vad inspelningen inte kunde säga. Uttryckligt förbud mot att öppna
repot. En agent per uppgift, utan kontakt med varandra. **Stickprov n = 1 per
uppgift.**

Skelettet, förgrindarna, domaren och kontamineringsmåttet är fas 9:s, ordagrant —
`tests/protocol/kor_fas18_anlaggning.py` importerar `kor_fas9_modellen.py` och
använder dess funktioner. Det enda som är utbytt är **vilket facit domaren får**.

### Ur provspåret: fyra uppgifter

| uppgift | första försöket mot spårfacit | efter ett reparationsvarv | mot bankens **handskrivna** facit |
|---|---|---|---|
| T-07 | underkänd — `tolkfel` | underkänd — 4 avläsningar i **en** tidpunkt | **godkänd** |
| H-04 | **godkänd** | **godkänd** | **godkänd** |
| S-05 | **godkänd** | **godkänd** | **godkänd** |
| L-05 | underkänd — 3 avläsningar | reparationsvarvet levererades inte | underkänd — `nodstopp_kraver_kvittens` |
| **summa** | **2 av 4** | **2 av 4** | **3 av 4** |

**Tre av fyra lösningar skrivna ur ett provspår uppfyller människans facit.** Det
är det positiva resultatet, och det är inte litet: ingen av de fyra agenterna såg
en uppgiftstext, en referenslösning eller en enda handskriven invariant.

De två som inte gjorde det säger var för sig något eget:

* **T-07:s första försök** föll på ett enda tecken — ett `å` i en kommentar. ST
  måste vara ren ASCII, så tolken stannade på raden och styrlogiken kom aldrig
  att prövas. Det säger ingenting om spåret. Efter reparationsvarvet uppfyller
  den människans facit och faller bara på spårets egen övertolkning av timingen
  (nästa avsnitt).
* **L-05** gick igenom spårfacit i sin första glesa form och föll på människans,
  på `nodstopp_kraver_kvittens@1800ms:ST260_RB_START` — en robot som startade om
  efter nödstopp utan kvittens. Det var täthetsfyndet, och det står nedan.
  Agenten hann inte leverera ett reparationsvarv innan mätningen skrevs; talet
  ovan är alltså dess första försök också i den kolumnen.

### Ur produktionsspåret: fasens svar i en rad

Två uppgifter till, med samma uppställning men en brief härledd ur
**produktionsspåret** — det en anläggning faktiskt ger.

| uppgift | mot facit ur produktionsspåret | mot bankens handskrivna facit | avläsningar som inte stämde |
|---|---|---|---:|
| T-07 | **godkänd** | **UNDERKÄND** | 11 |
| S-05 | **godkänd** | **UNDERKÄND** | 25 |

**Ett program som återger inspelningen, och som ändå har fel om anläggningen.**
Det är fas 18:s hela fråga besvarad i en rad, med ett tal bakom.

Vad T-07:s elva avläsningar var: ingen tidsövervakning av indexet
(`index_fastnar_tidsovervakning`, fyra avläsningar), inget larm när klämman
släpper mitt i ett index (två), ingen kontroll av att lägesgivaren ligger inom
arbetsområdet (fyra), och fel beteende när tryckluften kommer tillbaka (en).
Var och en är ett verkligt driftsättningsfel. S-05:s tjugofem täcker hela
HOLD/SUSPEND-grenen, maskinfelsgrenen och sorteringen — allt som PackML-cykeln
aldrig gick igenom under inspelningen.

Modellernas egna ord om vad de gissade är samstämmiga, och de pekar rakt på
samma sak. Ur T-07:s produktionsbrief:

> *"Allt felbeteende. `EMG_OK`, `AIR_OK` och `SYS_AUTO` rörde sig aldrig,
> `SYS_ALARM` aldrig heller. Vad som händer vid nödstopp, tryckluftsfall eller
> manuellt läge … är helt oobserverat."*

och

> *"`ST050_IDX_POS` är död information. Encodervärdet stod på 120 mm hela dagen
> och rörde sig inte ens under indexet. … Min kod använder det inte."*

Ur S-05:s:

> *"Höjdgivarens roll. `ST200_HGT_MM` stod still på 80 mm hela inspelningen och
> `DIV_OPEN` rörde sig aldrig. Kassationsvillkoret, dess tröskel, dess riktning
> och när i cykeln det mäts är helt oåtkomligt. … Att gissa 'kassera över X mm'
> hade varit en påhittad siffra utan härkomst."*

Grind 2 fångade samma sak mekaniskt: båda produktionslösningarna fick
`ORORD_SIGNAL` — en signal i kartan som koden aldrig rör.

### Täthetsfyndet: ett facit som bara läser av vid ändringar ljuger genom tystnad

Den första versionen av härledningen lade ett punktkrav bara där
**utsignalvektorn ändrade sig**. Med den formen gick L-05:s lösning igenom det
härledda facit och föll på bankens handskrivna, på
`nodstopp_kraver_kvittens@1800ms:ST260_RB_START` — en robot som startade om efter
nödstopp utan kvittens.

Felet låg inte i logiken utan i facit: mellan två ändringar i inspelningen stod
det tyst, och där fick koden göra vad den ville. En inspelning **är** varje rad.
Med avläsning på varje rad fäller det härledda facit samma defekt, på
`A11@1440ms:ST260_RB_START` och tolv rader till — alltså exakt den avvikelse
människans facit hittade.

`bank/anlaggning.TATHETER` bär båda formerna, och
`test_tathet_andringar_ar_glesare_och_slapper_igenom_mer` håller dem isär med en
station som släpper klämman för tidigt: samma flankantal, samma värden i båda
ändringspunkterna, fel däremellan. Den täta formen fäller den; den glesa inte.

### Och det motsatta felet: ett härlett facit ÖVERbestämmer

T-07:s reparerade lösning gick igenom **bankens handskrivna facit** och föll på
**spårets**, på fyra avläsningar i en enda tidpunkt: `A03@2600ms`. Där hade
inspelningen ännu inget larm; modellens tidsvakt hade redan löst ut.

Skillnaden är **ett scan, 20 ms**. Bankens facit ställer tidsövervakningen som
ett **fönster** — vakten ska falla mellan 1,9 och 2,4 s, och båda ändarna prövas
(`bank/README.md`, marginalregeln). Inspelningen känner inget fönster. Den vet
bara att just den här anläggningen larmade efter 1,98 s, och ett facit härlett ur
den gör det talet till ett krav.

Det är samma mynt som täckningen, andra sidan:

* **För svagt** där spåret aldrig gick — larmgrenen, nödstoppet, tidsvakten.
* **För starkt** där det gick — anläggningens egen implementationstiming blir
  ett krav på varje framtida lösning.

En omskrivning som lägger vakten på 2,1 s är riktig teknik och fälls av
spårfacit. Det ska stå med de orden när ett sådant facit används: det är en
**regressionsgrind mot den anläggning som spelades in**, inte en kravspecifikation.

### Kontaminering: såg modellen referensen den aldrig fick se?

Fas 9:s eget mått, ordagrant samma kod. Variabelnamn är ett fritt val: två
lösningar som delar `tmrIndex` har inte kommit på det var för sig.

| uppgift | likhet | längsta gemensamma sträng | delade egna namn |
|---|---:|---:|---|
| T-07 | 10,1 % | 13 tecken | inga |
| H-04 | 7,9 % | 17 | `STEG`, `TMRACK` |
| S-05 | 6,9 % | 30 | `TRIGSC` |
| L-05 | 6,6 % | 8 | inga |
| T-07 (produktion) | 8,5 % | 10 | inga |
| S-05 (produktion) | 6,3 % | 3 | inga |

Fas 9:s varning fyrar på **varje** delat namn, och den fyrade här på två
lösningar. De tre namnen är `steg`, `tmrAck` och `trigSc` — steg, timer för
kvittens och triggern på `ST200_PML_SC`. Det är konvergent namngivning på en
handfull tecken, och likheten i övrigt ligger på **6,3 till 10,1 %** mot fas 9:s
varningsgräns 35 %. Talen står här i sin helhet så att den som vill döma
annorlunda kan göra det.

### Vad förgrindarna sa

Grind 1 (kompilering genom STruC++) **kunde inte köras** — kompilatorn är inte
uppsatt på den här maskinen, och det är `M-48`:s och fas 12:s öppna punkt, inte
den här mätningens. Grind 4 svarar att kandidaten inte bär någon scenkod att
validera, vilket är rätt: uppgiften var att skriva PLC-logik, inte scenbygge.
Grind 2 gav `ORORD_SIGNAL` på de två produktionslösningarna och `TIDLITERAL` på
två av provspårslösningarna (`T#3S` med versal enhet).

## Vad detta betyder för fas 18

Fasens fyra ärlighetskrav ur `70_faser.md` står kvar, och tre av dem är nu mätta
i stället för resonerade:

1. *Ett spår visar bara vad som hände.* **Mätt:** 12 av 18 handskrivna
   invarianter går inte att döma ur ett produktionsspår, och 3 av 28 förreglingar
   återfinns.
2. *Tider är observerade, inte specificerade.* **Mätt i M-75**, och här bär varje
   härlett påstående sin nämnare (`n_rader`, `n_episoder`, `n_avsnitt`).
3. *Korrelation är inte orsak.* **Mätt:** 11 av 80 härledda förbud motbevisas av
   en annan inspelning av samma anläggning.
4. *Säkerhetsfunktioner rekonstrueras aldrig ur ett spår.* **Mätt:** `EMG_OK`
   gick aldrig till 0 i något av de fyra produktionsspåren, och grinden fäller
   varje facit som ändå dömer det läget.

Och ett femte krav som mätningen själv lade till: **ett härlett facit måste läsa
av varje inspelad rad, inte bara ändringarna.** Ett facit som står tyst mellan
två ändringar ljuger genom tystnad, och det släppte igenom en robot som startade
om efter nödstopp utan kvittens.

Svaret till operatören, i klartext: **ja, man kan lyssna på kablarna, och det
räcker längre än man tror — men bara till det linjen faktiskt gjorde medan man
lyssnade.** En inspelad normalproduktion ger ett program som återger
inspelningen och ändå saknar tidsövervakningen, larmen och förreglingarna. Det
som fattas går inte att räkna fram ur mer data av samma sort; det måste
provoceras fram, eller komma någon annanstans ifrån.

## LIMITS

* **Ingen riktig anläggning är inspelad.** Källan är bankens fyra
  referenslösningar körda genom repots egen tolk. Det som mäts är därför
  *informationsinnehållet i en I/O-inspelning*, inte hur en riktig linjes spår
  ser ut. En verklig inspelning bär dessutom brus, tappade paket, ojämn
  provtagning och signaler som inte hör till stationen — inget av det finns här.
  `M-75` sa samma sak och det står kvar: **vi har inget spår från en riktig
  anläggning.**
* **Fyra uppgifter, och alla fyra är våra egna.** Talen 28/28 och 3/28 har
  nämnaren fyra.
* **Modelledet är n = 1 per uppgift**, precis som fas 9:s. Fyra agenter på
  provspårsbriefen och **bara två** på produktionsbriefen. Talen 11 och 25 är två
  observationer, inte en fördelning.
* **"Första försöket" är taget efter att jag rättat mitt eget misstag.** Jag
  skrev i den första instruktionen att arbetsvariabler får ha startvärde
  (`namn : TYP := 0;`). Det gör de inte — skelettet läser bara `namn : TYP;` —
  och tre av fyra svar avvisades på formen. Jag rättade instruktionen och lät dem
  skriva om **deklarationsraderna**, inte logiken, innan första domen räknades.
  Det var ett instrumentfel, inte ett modellfel, men det betyder att talet "2 av
  4" är taget efter ett formsteg som fas 9:s tal inte hade.
* **Förbudet mot att öppna repot är en bön; kontamineringsmåttet är mätningen.**
  Agenterna hade filsystemsåtkomst och kunde i princip ha läst facit. Det som
  talar emot det är talen ovan — 6,3 till 10,1 % likhet och tre delade namn på
  sex lösningar — inte förbudet.
* **Provspårsledets modelltal säger ingenting om en riktig anläggning.** De fyra
  agenterna fick en brief härledd ur ett spår där någon medvetet provocerat
  kallstart, larm, kvittens, tidsvakt och återstart. Det finns inte på en linje
  som går. Det tal som svarar på operatörens fråga är produktionsledet — och det
  är 0 av 2 mot människans facit.
* **Härledningen ser bara boolska tvåsignalspar.** En förregling över tre
  signaler, över ett analogt tröskelvärde eller över en tid finns inte i
  påståendefamiljen. Det är därför S-05:s "människans" bara är 2 av 4 invarianter
  — resten har `INT`-villkor (PackML-tillståndet) som nedbrytningen inte når.
  Talet "återfunna" är alltså en undre gräns för vad en rikare härledning skulle
  kunna nå, och den rikare härledningen finns inte.
* **Provspåret är inte sanningen heller.** "11 av 80 motbevisade" är ett
  *undre* tal: de 69 återstående är inte bevisade, bara inte motbevisade av just
  den andra inspelningen.
* **Vilket fönster som är normalproduktion är valt av en människa.** Det är
  medvetet och står i körningen, men det betyder att talen 3/28 och 4/18 hänger
  på det valet. Ett annat fönster ger andra tal.
* **Upprepningen är syntetisk.** Produktionsspåret ×10 är samma stimulus tio
  gånger, inte tio verkliga takter med små variationer. Det räcker för att visa
  att täckningen inte växer, men det underskattar hur mycket en riktig
  produktionsdag ändå varierar.
* **`T3_UTAN_UNDERLAG` går att gå runt.** Kravet på nämnare gäller bara facit som
  stämplat sig som härlett (`harledd: True`), och `harled` sätter alltid den
  stämpeln. Ett facit som härleds ur ett spår utanför den vägen och låter bli att
  stämpla sig slipper kravet. Grinden fångar oärlighet i formen, inte i uppsåtet.
* **Ingen jämförelse mot vägen "läsa uppladdningsformatet".** `70_faser.md`
  beskriver två vägar in. Bara spåret är mätt. Vilka tillverkarformat som
  faktiskt bär symbolnamn och logik är fortfarande **omätt mot riktiga filer**.
* **Domen är tolkens, inte en runtimes.** Samma förbehåll som hela bänken:
  `bank/domare.py` kör spåret genom repots ST-tolk. Att jämföra samma spår genom
  tolken och genom OpenPLC v4 över OPC UA är `M-45`:s öppna punkt och den står
  kvar.
* **Två av repots egna grindar är oense om `T#3S`.** Grind 1:s statiska analys
  fäller `T#3S` med *"'3S' går inte att läsa som tid; enheterna är d h m s ms us
  ns"*, medan `st/tolk.py` uttryckligen försöker om med små bokstäver därför att
  MATIEC — som OpenPLC bygger på — är skiftlägesokänslig. En modell som skriver
  versal enhet får alltså en anmärkning av den ena grinden och godkänt av den
  andra. Upptäckt här, inte lagat här.
* **Skelettets arbetsvariabelfack tar inte startvärden.**
  `svc/vc_assist_svc/plc/skelett.py` läser bara formen `namn : TYP;`, medan
  IEC 61131-3 tillåter `namn : TYP := start;`. Det är en verklig inskränkning som
  den här körningen råkade på, och den är inte lagad här.
