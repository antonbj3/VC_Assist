# Bänken

Fas 9 i `docs/spec/70_faser.md`. En samling bänkuppgifter med facit, en läsare
som kan svara på frågor om samlingen, och ett schema som avvisar en uppgift
utan facit.

beskriver: `bank/schema.py`, `bank/lasare.py`, `bank/katalog_index.json`,
`bank/uppgifter/*.json`, `tests/enhet/test_bank.py`

```
python3 bank/lasare.py                 # hela rapporten: grupper, svårighet, täckning
python3 bank/lasare.py --klass F7      # vilka uppgifter täcker kapplöpning
python3 bank/lasare.py --uppgift T-01  # en uppgift som JSON
python3 -m pytest tests/enhet/test_bank.py -q
```

## Varför JSON och inte YAML

`json` ligger i standardbiblioteket, `pyyaml` gör det inte. Uppgifterna ska
kunna läsas av tre parter: läsaren här i python 3, tjänsten, och på sikt
VC-sidans python 2.7, som enligt `docs/spec/90_invarianter.md` I16 bara får
använda medföljande standardbibliotek. Ett format som kräver ett beroende hade
brutit den invarianten på den ena av tre parter. Till det kommer att en
JSON-fil per uppgift ger ett `task_id` som matchar filnamnet, vilket är
lintregel `M2` ur `docs/spec/81_mallschema.md`, och en diff per uppgift i
stället för en diff i en samlingsfil.

Kostnaden är att JSON inte har kommentarer. Den bärs av fälten `orsak` och
`antaganden`, som är obligatoriska och står i posten själv.

## En uppgift

Kärnfälten är de ur `docs/spec/81_mallschema.md`. Utöver dem bär varje uppgift:

| Fält | Vad det är | Varför |
|---|---|---|
| `bransch` | en av tio branscher | banken ska mäta sin egen spridning; tolv varianter av samma plockcell ser ut som fyrtio uppgifter men mäter en sak |
| `orsak` | den verkliga driftsättningsmiss uppgiften speglar, minst 100 tecken | "uppehållet är kortare än transportörens eftersläpning" är en bugg; "delen hamnar fel" är en genrebeskrivning |
| `prompt` | uppgiftstexten språkmodellen får se | måttet i mm, tiden i s och signalnamnen står här, inte i en fotnot |
| `antaganden` | varje tal som inte går att grunda i publicerad praxis, med motiv | ett märkt antagande är hederligt, ett omärkt påhittat tal är slarv |
| `fysik` | detaljens mått och massa, och den arbetsradie uppgiften kräver | låter lintern pröva robotvalet mot katalogens publicerade modelldata |
| `stege` | steg på svårighetsstegen | svårighetsgraden härleds ur steget i stället för att gissas per uppgift |
| `scenarios` | normaldrift, gränsöverskridande per analog insignal, vändningsfall | **motivet är omskrivet, se nedan.** Ett facit som bara kör normalfallet mäter nästan ingenting |
| `core_outputs` | de utgångar en spårjämförelse ska väga | poängen "andel portar vars spår stämmer" är odefinierad utan dem |
| `variant_av`, `broken` | medvetet trasig variant och dess artefakt | regel S2: varje grind måste ha en fixtur som fäller den |

`arbetsradie_mm` är den största radie en robot i uppgiften måste nå. För
uppgifter utan robot är den cellens största horisontella spann, och lintern
använder den då inte till något.

## Facit

Facit ligger i `expect` och är skrivet i ögats faktiska grammatik. Grammatiken
kopieras inte hit; `bank/schema.py` importerar `oga_kontrakt` ur
`ext/vc_addon/vc_assist/` och validerar varje facitrad mot den. En kopia hade
kunnat drifta utan att något märkte det.

En facitrad är en rad ur grammatiken där varje tal får bytas mot `*`:

```json
{"section": "TIMING", "template": "DWELL ST010 *s req=0.4s OK"}
```

`*` betyder "vilket tal som helst". Vi låser ordningen och orden, inte de
mätvärden vi ännu inte mätt. Lintern bevisar att mallen kan uppstå ur ögats
mönster genom att sätta in konkreta tal och matcha mot `oga_kontrakt.RADER`;
`tests/enhet/test_bank.py` går ett steg längre och låter ögats egen
`Rapport.rad()` ta emot raden.

`expect.gate` säger vilken grind som ska fälla uppgiften:

* `OGAT` — grind 5. Då krävs `verdict`, minst en `lines`-rad, och för en
  fällning en `reason_contains`.
* `G1` till `G4` — grindarna före ögat. Då finns ingen ögondom att jämföra mot,
  och facit är i stället `gate_code`, alltså felklassen ur
  `docs/spec/82_felklasser.md`.

De medvetet trasiga varianterna bär sin artefakt i `broken`. För en variant
vars facit ligger på ögat är artefakten en fullständig ögonrapport, och den
läses av kontraktet i testet. Facit för en variant får därför ha exakta tal:
det är avläsningen av en fixtur, inte en förutsägelse om en okörd körning.

## Spårfacit

Tillagt av **M-45**. Ögonfacit i `expect` dömer *scenen* efter en körning i VC.
Spårfacit i `facit_spar` dömer *styrlogiken* mot insignalerna över tid, och går
att döma i dag — utan VC, utan OpenPLC, utan nät. De ligger bredvid varandra;
ögat fäller domen om scenen (invariant I1), spåret om logiken.

Fältet är **frivilligt**: en uppgift utan det går igenom lintern oförändrad, och
en uppgift som har det går igenom även om fältet tas bort. M-106 gav spårfacit
till tio av de 47 uppgifter som saknade det och tog dessutom in tolv nya.

```
python3 bank/domare.py --uppgift T-07               # referens + alla motbevis
python3 bank/domare.py --uppgift S-05 --st min.st   # döm en egen lösning
python3 -m pytest tests/enhet/test_domare.py -q
```

### Formen

| Fält | Vad det är |
|---|---|
| `harkomst` | **källklassen, härledningen och mätningen** — se nedan |
| `standard` | den publicerade tillståndsmodell eller standard facit lutar sig mot |
| `scan_ms` | scanperioden spåret körs med. 20 ms, mätt i M-20 |
| `referens` | en lösning som uppfyller facit; beviset att facit går att nå |
| `sekvenser` | (t_ms, insignaler → förväntade utsignaler) i tidsordning |
| `invarianter` | "närhelst X gäller ska Y gälla", prövat i varje scan |
| `flanker` | antalet flanker på en utgång inom ett fönster |
| `motbevis` | lösningar som ser riktiga ut och som domaren MÅSTE fälla |

Tre sorters påstående, alla mekaniska: **punktkrav**, **invariant**,
**flankräkning**. Flankräkningen är den enda mekaniska domen över felklass
`F15`, flank och latch.

### Härkomsten: fyra källklasser, och paragrafen ska citeras

Tillagt av **M-106**. `harkomst` börjar med en **källklass** och bär den
härledning som klassen lovar. Fyra klasser är lagliga, och de är
`docs/spec/85_bankkontraktet.md` §2:s egna källor i bankens ordförråd:

| Klass | Vad den lovar | Vad grinden kräver |
|---|---|---|
| `STANDARD:` | en paragraf i en publicerad standard | utgivare **och** paragrafnummer, och paragrafen ska stå i M-106:s tabell |
| `RAKNAD:` | geometri eller fysik ur scenens egna mått | räkningen skriven ut, med likhetstecken |
| `DATABLAD:` | en tillverkares publicerade datablad | modellen namngiven och vad som hämtats |
| `SPAR:` | ett inspelat I/O-spår från en riktig anläggning | var spåret kommer ifrån |

Klasserna får kombineras: `STANDARD+RAKNAD: ...`. Härkomsten ska dessutom
namnge en **mätning** (`M-`nummer) som finns i `docs/matningar/`.

Två saker är förbjudna, och båda fälls mekaniskt av
`tests/protocol/kor_bankens_facit.py`:

* **Facit ur koden som döms.** Härkomsten får aldrig peka in i `svc/`,
  `bank/domare.py`, `tests/` eller `plc/`. Kör aldrig referensen för att se vad
  den ger och skriv sedan ned det som facit — det är BENCH-4, en grind som stod
  grön i månader mot ett tal räknat av samma algoritm som dömdes.
* **Ett paragrafnummer ingen slagit upp.** MÄTT 2026-09-05: två uppgifter bar
  "IEC 60204-1:2016 9.2.4", en paragraf som inte finns. Grinden slår därför upp
  varje citat mot tabellerna i `docs/matningar/M-106_bankens_facitkallor.md`,
  där paragraferna faktiskt kontrollerades mot standardorganens
  innehållsförteckningar. Vill du citera en ny paragraf: slå upp den och skriv
  in den i M-106 först.

Och kärnutgångarna: **varje namn i `core_outputs` måste röras av spårfacit** —
i ett punktkrav, en invariant eller en flankräkning. En utgång som ingen
sekvens nämner är inte dömd.

### Marginalregeln

Ett punktkrav måste ligga minst **två scan** efter den senaste ändringen av en
insignal i samma sekvens. Talet är mätt i M-20: PLC:ns egen svarstid är exakt
två scan. Under den marginalen skiljer facit inte längre på "implementationen
svarar ett scan senare" och "implementationen gör fel", och bänken mäter kodstil
i stället för styrlogik. Lintern avvisar på `M33_SPARFACIT`.

Av samma skäl anges varje tidsövervakning som ett **fönster** i uppgiftstexten,
och facit prövar båda ändarna. En för kort tidsvakt stoppar linjen på normal
drift och är lika mycket ett fel som en vakt som saknas.

### Referens och motbevis

Ett facit ingen kan uppfylla fäller alla och ser ut som en svår bänk. Ett facit
som inget fäller mäter ingenting. Därför krävs båda:

* `referens` uppfyller facit. Provas av `test_referenslosningen_uppfyller_sitt_eget_facit`.
* varje post i `motbevis` bär `faller_pa`: exakt de brister domaren ska fälla
  den på. Ett motbevis som fälls av fel skäl är ingen fixtur, det är en slump.

Referensen får aldrig hamna i `prompt`; lintern och ett prov jämför texterna.
**Modellen skriver aldrig sitt eget facit** — Koziolek m.fl. (arXiv 2405.01874)
mätte 0–50 % korrekta assertions när en modell fick generera dem, sämst på
timers.

### Motorn

`svc/vc_assist_svc/st/tolk.py` kör ST-programmet scan för scan över repots egen
ST-läsare. Den är **inte** OpenPLC och **inte** STruC++, och den ersätter ingen
grind. Att jämföra samma spår genom tolken och genom OpenPLC v4 över OPC UA är
en egen mätning som M-45 lämnar öppen.

`bank/domare.py` bygger ingen egen grindkedja: den tar emot en `Stationsdom` ur
`svc/vc_assist_svc/plc/stationsgrind.py` och citerar den fällande grindens egna
ord ordagrant, utan att köra spåret.

## Numreringen

`task_id` följer `^(T|P|L|S|A|H|C)-\d{2}$` ur specen. Löpnummer från 90 och
uppåt är medvetet trasiga varianter. Det är det enda utrymmet mönstret ger, och
det gör varianterna läsbara utan ett eget fält i filnamnet.

## Svårighetsgraden

Steget i `stege` är ett svårighetsankare, valt efter styrlogikens komplexitet,
inte en ämnesetikett. Progressionen är den beprövade undervisningsordningen:

```
start_stopp_transportor(1) · set_reset(1) · nivareglering(2)
sortering_hojd_enkel(2) · sortering_hojd_avancerad(3) · separeringsstation(3)
palletering(4) · plock_placera_tre_axlar(4) · produktionslinje(5) · hiss(5)
```

Två uppgifter på samma steg får därmed samma tal, och stegen är faktiskt
stigande. Alla svårighetsgrader bär stämpeln `DEKLARERAD`. Enligt regel 4 i
`docs/spec/83_scenarier.md` sätts svårighetsgraden efter att den mätts, och
ingenting är mätt ännu. Stämpeln blir `MATT` först när `last_run` finns, och
lintern avvisar `MATT` utan den.

## Talen och deras härkomst

`bank/katalog_index.json` bär komponenterna. Varje post är stämplad:

| Stämpel | Betyder |
|---|---|
| `PUBLICERAD_SPEC` | räckvidd, nyttolast och axelantal ur tillverkarens publicerade datablad för den namngivna modellen |
| `STANDARDMATT` | måttet är en standard: EUR-pall 1200x800x144, VDA KLT 4147, gitterbox |
| `ANTAGEN` | bankens antagande; motivet står i posten |

Robotarna är verkliga modeller med verkliga tal: ABB IRB 1200-5/0.9 (901 mm,
5 kg), IRB 660-180/3.15 (3150 mm, 180 kg), FANUC M-10iD/12 (1441 mm, 12 kg),
KUKA KR 10 R1100 (1101 mm, 10 kg) och så vidare. Lintern jämför varje uppgifts
`fysik.detalj.massa_kg` plus det tyngsta gripdonet mot robotens nyttolast, och
`fysik.arbetsradie_mm` mot dess räckvidd (`M23_ROBOT_KAPACITET`). Det är den
mekaniska kontrollen mot slarvet "fem kilo last och tre meter räckvidd i samma
uppgift". Två uppgifter fick byta robot när kontrollen fyrade första gången.

Grepptider, transportörhastigheter, takttider och toleranser ligger i de spann
branschen brukar ligga i — vakuumgripare 0,1 till 0,3 s anslag, tvåbackad
pneumatisk 0,2 till 0,5 s, ackumulerande rullbana 6 till 30 m/min,
bandtransportör 0,2 till 1,2 m/s, monteringstakt 8 till 60 s, palletering 4
till 15 s per kolli, fixturtolerans 0,1 till 1 mm, palltolerans 5 till 20 mm.
Vart och ett av dem är valt inom sitt spann och inte mätt, och det står i
uppgiftens `antaganden`.

## Komponent-URI:erna

`scene.components[].uri` använder schemat `bank://`. Det är avsiktligt inte en
VC-URI. **MÄTT 2026-09-04:** VC-installationen innehåller noll `.vcmx`-layouter
och fem komponentfiler. Det finns alltså inget lokalt scenarkiv att peka på, och
en påhittad eCatalog-URI hade sett ut som en mätning. Banken bär därför sin egen
vokabulär och binds till det riktiga katalogindexet i fas 5.

Av samma mätning följer att `scene.layout_uri` alltid är `null`, och lintern
avvisar allt annat (`M24_LAYOUT_URI`). Allt i banken är självbärande i text.

## Kedjan uppgifterna är sanna i

VC har ingen inbyggd ST-motor. VC Premium är en OPC UA-**klient** som mappar
simuleringsvariabler mot en server. Kedjan är:

```
genererad ST -> OpenPLC Runtime v4 -> OPC UA -> VC-scenen -> spår ut
```

Signalerna i varje signalkarta är alltså OPC UA-variabler. Varje `prompt`
avslutas med den upplysningen, och lintern kräver att den står där
(`M29_KEDJA`).

## Signalnamnen

En genomförd konvention i hela banken:

```
ST<nnn>_<DON>_<FUNKTION>      ST010_CNV_RUN, ST020_RB_START, ST020_GRP_CLOSED
<ANLÄGGNINGSSIGNAL>           EMG_OK, AIR_OK, SAFE_DOOR_CLOSED, LIGHT_CURTAIN_OK,
                              SYS_AUTO, SYS_RESET, SYS_ALARM
```

Grind 3 i `docs/spec/50_grindar.md` matchar deklarationer mot signalkartan. Är
namnen inte disciplinerade i banken går grinden inte att pröva mot den.
Handskakningar är fyra signaler — begäran, kvittens, klar, återställning — och
för grupp H är det ett linterkrav (`M25_HANDSKAKNING`).

## Lintkoder

`M1` till `M12` ägs av `docs/spec/81_mallschema.md`. `M13` och uppåt är bankens
egna tillägg:

| Kod | Fel |
|---|---|
| `M13_LINE_NOT_IN_GRAMMAR` | facitrad finns inte i ögats grammatik |
| `M14_PASS_WITH_VIOLATION` | facit säger PASS men kräver en HONESTY-överträdelse |
| `M15_GATE_FACIT` | facit stämmer inte med den grind som ska fälla |
| `M16_VARIANT_WITHOUT_ARTIFACT` | trasig variant utan artefakt att fälla |
| `M17_DIFFICULTY` | svårighetsgrad utanför 1-5 eller utan stämpel |
| `M18_PROMPT` | uppgiftstexten saknas eller är för kort för att vara konkret |
| `M19_UNKNOWN_ROLE` | koppling pekar på en roll som inte finns i scenen |
| `M20_GROUP_MISMATCH` | grupp stämmer inte med prefixet i `task_id` |
| `M21_VARIANT_TARGET` | `variant_av` pekar på fel sorts uppgift |
| `M22_SIGNAL_NAME` | signalnamnet följer inte konventionen |
| `M23_ROBOT_KAPACITET` | roboten räcker inte till uppgiftens last eller radie |
| `M24_LAYOUT_URI` | uppgiften lutar sig mot ett layoutarkiv som inte finns |
| `M25_HANDSKAKNING` | överlämning utan fullständig handskakning |
| `M26_BRANSCH` | okänd eller saknad bransch |
| `M27_ORSAK` | uppgiften säger inte vilken verklig driftsättningsmiss den speglar |
| `M28_ANTAGANDE` | ett tal utan härkomst och utan märkt antagande |
| `M29_KEDJA` | uppgiftstexten nämner inte kedjan över OPC UA |
| `M30_SCENARIER` | gränsscenarierna är ofullständiga |
| `M31_KARNUTGANGAR` | kärnutgångarna för spårjämförelse saknas eller är inte utgångar |
| `M32_STEGE` | svårighetsgraden stämmer inte med steget |
| `M33_SPARFACIT` | spårfacit går inte att döma mekaniskt |

Varje kod har en trasig fixtur i `tests/enhet/test_bank.py` som fäller den, och
ett prov som visar att en giltig uppgift släpps igenom. En linter som avvisar
allt klarar annars alla prov.

## Ett spår från en befintlig anläggning

Tillagt av **M-89**, fas 18. `bank/anlaggning.py` går åt andra hållet: i stället
för att skriva ett facit och pröva en lösning mot det, tar den ett **inspelat
I/O-spår** och härleder ett facit ur det. Det är den väg operatören pekade ut —
*"Man lyssnar väl på kablarna typ, och lägger ihop signalerna?"* — och den finns
därför att originalkoden ofta är borttappad.

```
python3 tests/protocol/kor_fas18_anlaggning.py
python3 tests/protocol/kor_fas18_anlaggning.py --brief <katalog>
python3 -m pytest tests/enhet/test_anlaggning.py -q
```

Formen är densamma som `facit_spar`, så `bank/domare.py` dömer den oförändrad
genom sitt `spar`-argument. Ingen ny domare skrivs.

Två fält bankens schema inte känner följer med, och det är avsiktligt:

| Fält | Vad det är |
|---|---|
| `tackning` | vilka värden varje signal antog och hur många gånger den bytte |
| `underlag` | nämnaren bakom varje härlett påstående: `n_rader`, `n_episoder`, `n_avsnitt` |

Ett härlett facit är **inte** en bankuppgift. En bankuppgift bär en
referenslösning som bevisar att facit går att uppfylla; en anläggning har ingen
källkod att lämna ifrån sig. Det som bär uppfyllbarheten i stället är
inspelningen själv: varje påstående är en avläsning som redan har hänt.

### Grinden: täckning innan påstående

`anlaggning.granska(facit, spar)` fäller varje påstående inspelningen inte bär.

| Kod | Fel |
|---|---|
| `T1_OTACKT_VILLKOR` | invariantens villkor förekom aldrig i spåret |
| `T2_OKAND_SIGNAL` | påståendet läser en signal spåret inte har |
| `T3_UTAN_UNDERLAG` | ett härlett påstående utan sin nämnare |
| `T4_OTACKT_KRAV` | kravet vill ha ett värde signalen aldrig antog |

Kravet på nämnare gäller bara facit som stämplat sig som härlett. Ett
**handskrivet** facit har sin härkomst i en publicerad standard — `IEC 60204-1`
säger att en nödstoppskrets kräver manuell återställning, och det påståendet står
upp utan en enda observation.

`T1` är fasens viktigaste grind. Ett stillastående nödstopp som ingen tryckt på
under inspelningen säger ingenting om vad som händer när någon gör det. **Mätt i
M-89:** `EMG_OK` gick aldrig till 0 i något av de fyra produktionsspåren, och 12
av bankens 18 handskrivna invarianter går inte att döma ur ett sådant spår — men
**0 av 18** ur ett provspår, så grinden vägrar inte allt.

## Spårjämförelse

`lasare.spar_poang(referens, kandidat, karnutgangar)` jämför flankspåren per
utgångsport och ger andelen kärnutgångar vars spår stämmer. Toleransen är
50 ms, valt som tio gånger det scanfönster om 5 ms vi räknar med i OpenPLC — ett
antagande tills fas 6 mätt tur och retur över OPC UA. Ett kandidatsvar som inte
går att läsa som en ögonrapport ger noll: kompilerings-, deploy- och
tidsöverdragsfel är inte delvis rätt.

Måttet ligger **bredvid** ögondomen, aldrig i stället för den. Ögat fäller domen
(invariant I1); spårpoängen är en gradering av hur nära ett fällt försök låg.

## Vad som är tunt

* **47 av 51 uppgifter saknar spårfacit.** De fyra som har det (`T-07`, `H-04`,
  `S-05`, `L-05`) är ett mönster att växa på, inte en färdig bank. M-45 §8.
* Ingen uppgift är körd. `verified_status` är `unverified` överallt och
  `last_run` är `null`. Svårighetsgraderna är därför deklarerade, inte mätta.
* Tre felklasser har exakt en uppgift var: `F12` ohederlig, `F13` verktygsfel
  och `F14` annat. Det är avsiktligt för `F14`, som ska vara nära noll, men
  tunt för `F12` och `F13`.
* Branschtäckningen är ojämn: fordonsmontering och livsmedelsförpackning har
  tretton uppgifter var, medan plastformsprutning, svetsning och limning har en
  var.
* Kategoritaxonomin i Koziolek och ABB (arXiv 2305.15809) har tio
  representativa kategorier. Jag har inte den listan ordagrant och kan därför
  inte påstå att banken täcker den. Det som mäts i stället är de sju grupperna,
  de tio branscherna och de tio stegen på svårighetsstegen, och alla tre är
  fyllda. Om listan tas fram bör täckningen mätas om mot den.
* Baslinjen i `docs/spec/83_scenarier.md` — samma uppgifter körda med en
  klassisk metod under samma budget — är inte byggd. Banken bär facit och
  frågor; jämförelsen är ett eget arbete.

## Om talet som stod här förut

Kolumnen `scenarios` motiverades tidigare med *"felfrekvensen är 17,3 % vid
gränsöverskridande mot 7,1 % vid normaldrift (SemaPLC, arXiv 2608.18565)"*.

**Talet är struket.** Två oberoende källkontroller har försökt slå upp det i
SemaPLC och ingen har hittat det: motbevisningen 2026-09-04 (§5c) och
research-destillatet `docs/research/R-01`. Den andra körningen läste artikelns
resultat och återgav 72,6 %, 52,2 mot 22,4–31,4, kostnaden 34,1 modellanrop och
TON-fyndet — men ingenting om 17,3 eller 7,1.

Frånvaro är inte motbevis, och talet kan finnas någonstans. Men ett tal som två
sökningar inte kan belägga får inte bära ett designbeslut. Det är exakt den
felklass som redan fångats en gång i det här projektet: ett benchmarktal från
ett annat sammanhang som användes som om det vore vårt.

**Regeln står kvar oförändrad**, och den behöver inte talet. En uppgift vars
facit bara kör normaldrift provar inte gränserna, och det är gränserna som
fäller PLC-logik: en jämförelse som är `>` där den skulle vara `>=`, en larmnivå
som aldrig nås, ett vändningsfall som ingen körde. Skälet är mekaniskt och
behöver ingen extern siffra.
