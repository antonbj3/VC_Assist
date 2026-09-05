# Skuldregistret

**Genererat**, aldrig fört för hand. Ett register någon måste komma ihåg att uppdatera är redan glömt, och den enda skuld som hamnar där är den man ändå kom ihåg.

Byggs med `python3 -m vc_assist_svc.skuld` ur två källor som båda skrivs samtidigt som arbetet: mätningarnas ärlighetsavsnitt och markörer i koden.

## Mätningar utan ärlighetsavsnitt: 0

## Mätningsnummer som fler än en fil gör anspråk på: 0

## Ordlistor som bär två storheter: 0

En lista som bär både felord och bara negationer svarar på frågan *bär texten något av de här orden?* — och det är inte den fråga någon grind ställer sig. Mätt tre gånger: M-94 fynd 1 och 4, M-98. Taket är noll, och kriteriet har ingen undantagslista: en lista som bär båda storheterna ska vara **sammansatt** ur de listor som bär var sin.

## Ordlistor som står i två filer: 12

`harness/text.py` säger det själv: *"de ligger PA ETT STALLE just for att en kopierad ordlista blir tva ordlistor sa fort nagon ratter den ena"*. Registret såg inte att regeln bröts. Listan nedan är ett **register**, inte en anklagelse: en delad ordlista kan vara rätt, men den måste vara sedd.

* 12 gemensamma — `svc/vc_assist_svc/guldgrind.py`.**DALIGA_ORD** ↔ `ext/vc_addon/vc_assist/oga_kontrakt.py`.**_FYNDORD**
* 11 gemensamma — `svc/vc_assist_svc/plan/forfining.py`.**ANDELSER** ↔ `svc/vc_assist_svc/plan/lasning.py`.**_ANDELSER**
* 7 gemensamma — `svc/vc_assist_svc/harness/oga.py`.**BARA_NEGATION_OGA** ↔ `svc/vc_assist_svc/harness/text.py`.**BARA_NEGATION**
* 7 gemensamma — `svc/vc_assist_svc/harness/oga.py`.**GODKANNANDEORD** ↔ `svc/vc_assist_svc/harness/text.py`.**FRAMGANGSMARKORER**
* 7 gemensamma — `svc/vc_assist_svc/st/lexer.py`.**NYCKELORD** ↔ `svc/vc_assist_svc/st/modell.py`.**VARSORTER**
* 6 gemensamma — `svc/vc_assist_svc/st/skrivare.py`.**JAMFORELSER** ↔ `svc/vc_assist_svc/st/validator.py`.**JAMFORELSER**
* 4 gemensamma — `svc/vc_assist_svc/guldgrind.py`.**INTE_NONE** ↔ `ext/vc_addon/vc_assist/oga_kontrakt.py`.**_INTE_NONE**
* 3 gemensamma — `ext/vc_addon/vc_assist/plats.py`.**WINDOWSPLATTFORMAR** ↔ `install/upptackt.py`.**WINDOWSPLATTFORMAR**
* 3 gemensamma — `svc/vc_assist_svc/guldgrind.py`.**OBLIGATORISKA_SEKTIONER** ↔ `svc/vc_assist_svc/forlopp/yta.py`.**OBLIGATORISKA_SEKTIONER**
* 2 gemensamma — `svc/vc_assist_svc/scenarbete/sparr.py`.**KALLOR** ↔ `svc/vc_assist_svc/plan/harkomst.py`.**KALLOR**
* 2 gemensamma — `svc/vc_assist_svc/verktyg/matning.py`.**_YTOR_LAYOUT** ↔ `svc/vc_assist_svc/verktyg/robotik.py`.**_YTOR_LAYOUT**
* 1 gemensamma — `svc/vc_assist_svc/api_index.py`.**_RANGORDNING** ↔ `svc/vc_assist_svc/verktyg/katalog.py`.**_RANGORDNING**

## Vad mätningarna säger att de inte vet: 983 punkter

### M-01_tillaggsmekanismen.md — Vad som INTE är mätt

* Allt är mätt i ett Wine-prefix på Linux mot VC Premium 4.10. Ingen rad är mätt
* Raden *"`threading` — importerbar"* säger att modulen går att importera. Att en
* `socket.bind("127.0.0.1", 8901)` är mätt som en **bindning**. Att någon utifrån
* Listan över verifierade API-ytor säger att namnen finns och svarade i
* "Trasiga tillägg misslyckas tyst"* vilar på **ett** avsiktligt syntaxtrasigt
* Scopeindelningen är prövad genom kroken `OnAppInitialized` och ett kommando.
* Sökvägsfyndet är mätt som "den ena vägen fyrar, den andra inte" i ett prefix.

### M-02_prefixisolering.md — Vad som INTE är mätt

* Exakt **en** utlänkad mapp är prövad: `Documents`. Regeln mätningen skriver ned
* Att omdirigeringen faktiskt **ger** isolering är inte efterprövat. Ingen mätning
* Påståendet att en kopia av prefixet delar `My Commands` med originalet är
* härlett** ur symlänken. Inget prefix kopierades och ingen delad fil
* Mätt under Wine 11.16 på den här maskinen. Att en färsk `wineboot` i en annan
* "Kontrollen ska ingå i fas 0:s acceptans"* är ett förslag i den här texten.

### M-03_takt.md — Vad som INTE är mätt

* Varje tal är **en** körning. 224,7 Hz, 17,2 Hz, medianen och värstafallet har
* Svarstiden är tjugo tur-och-retur från **en** klient över **en** anslutning på
* "Värsta av 20"* är värsta av tjugo. Tjugo punkter kan inte mäta en svans: en
* Att de ~8 ms per varv är `tick()`:s eget arbete är en **förklaring**, inte en
* Faslåsningen mellan pump och klient är sluten ur att medianen låg på 49,93 ms
* Talen är mätta mot Wines schemaläggare på den här maskinen, headless `:99`,
* Kostnaden för den adaptiva pumpens tomma varv är inte mätt. Den avfärdas med

### M-04_exekveringsmodellen.md — Öppen fråga, blockerande för fas 1

* Ingen av dem är prövad.** Fas 1 kan inte stängas förrän en av dem mätts.

### M-04_exekveringsmodellen.md — Vad som INTE är mätt

* Varje **Nej** i tabellen är en frånvaro mätt över ett ändligt fönster: 135 s
* Sökningen efter en generell timer är en **ordsökning** på nio namn i API:t.
* `OnIdle` prövades bunden, headless, med appen stilla. Om den fyrar med
* De tre kandidaterna under *Öppen fråga* är uppräknade, inte prövade. Ingen av
* `vcScript` beskrivs ur dokumentationen — `OnRun`, `delay`, `condition`,
* Allt är mätt headless på `:99` under Wine. Att VC med gränssnitt beter sig

### M-05_skrivningar_och_pump.md — Vad som INTE är mätt

* Bytesträngsfyndet är mätt på **fyra** anrop. Invarianten *"all text som skickas
* `_s()` är prövad i VC:s Stackless Python 2.7. Att den är en no-op på VC 5.0
* `sim.run(30.0)` på 0,04 s väggklocka är **en** körning i en scen utan arbete.
* Att `first_state()` aldrig anropas är mätt som frånvaro. **Varför** den inte
* Metodfelet i texten (fyra körningar felsökta på fel rad) är rättat i just det
* `dir()` på `vcScript` visade bara metoder medan `Script` gick att nå ändå.

### M-06_pumpen_fungerar.md — Vad som INTE är mätt

* De 560 varven och *"exakt 20,0 Hz"* är mätta i **simuleringstid**. Samma text
* Att `from vcScript import *` är **nödvändig** är mätt. Att den är tillräcklig
* Slutsatsen om `SimSpeed` (*"att sätta den ändrade ingenting"*) är dragen under
* Hook-ordningen `OnReset → OnStart → OnRun → OnStop` är avläst ur **en**
* `vcApplication.delayRealTime` står som kandidat och är märkt oprövad i texten.
* Bekräftelsen ur `Commands/Wizards/SensorWizard.py` är en läsning av

### M-07_motorn_ar_stackless.md — Vad som INTE är mätt

* Trådsvälten är mätt i **en** uppställning: en daemon-tråd som skriver var
* Mekanismen — *"VC:s egen meddelandeloop släpper inte GIL"* — är en förklaring
* "Noll varv, för alltid"* är inte en mätbar storhet. Mätningen varade så länge
* `import clr` och `import System` gav ImportError i **det här** scopet. Att .NET
* De 91 metoderna på applikationsobjektet är en `dir()`-räkning. Vilka som
* Versionssträngen är läst en gång i ett prefix. Att VC Premium 4.10 alltid bär

### M-08_vaggklockspumpen.md — Vad som INTE är mätt

* Kvoten 1,000 är mätt över **en** körning på 155 s, i en tom scen, med en pump
* "3 100 varv utan ett enda missat"* räknas ur skriptets **egen** räknare. Ett
* Driften *"under 0,01 s över 155 s"* är en körning på tre minuter. Om driften
* Att `SimSpeed` styr interaktiv uppspelning och inte satskörning är en
* förklaring** till M-06:s utfall. Den prövades inte här genom att sätta
* Att `sim.SimTime` läst ur kommandots scope stod kvar på 0,000 är mätt.
* Vad som händer med köade begäran när operatören stoppar simuleringen är
* Hela mätningen är gjord headless under Wine. Att `startSimulation()` beter sig

### M-09_tyst_syntaxfel.md — Vad som INTE är mätt

* Ett** fall: en trasig trippelcitering i en fil. Att `loadCommand` ger ett
* Grinden `tests/enhet/test_tillagg_syntax.py` parsar med **värdmaskinens
* Kostnaden *"0,05 s"* är en körning på den här maskinen.
* "Tre gånger nu har VC svalt ett fel tyst"* är en räkning av tre observerade
* Slutsatsen att felet *"måste fångas på disk, före start"* är rätt för det här

### M-100_personatackningen.md — LIMITS

* Stegen är oviktade.** Att spara en layout och att bygga ett helt
* `UI:`-markörer går att bevisa falska, inte sanna.** Grinden fäller en
* Ingenting kördes mot en levande VC.** Att ett verktyg står i registret
* Sju profiler är inte alla användare.** Underhållstekniker,
* Stegen är skrivna av mig, inte av en användare.** Ingen layoutplanerare
* `component_info`, `frame_owner_node` och `ray_cast` kan vara felaktigt
* Talet 4 % utanför räckvidd är sannolikt för lågt.** Det räknar bara de

### M-101_komponentmodellen_byggd_ur_specen.md — LIMITS

* Ingen upprepning.** Varje komponent byggs och mäts **en gång**, i en
* Ett fönster.** Flödet mäts över ett provfönster på ~36 s. En matare som
* Två av fem par är härledda, inte mätta.** `transportor -> transportor` och
* Matchningsregelns ordning är vår, inte VC:s.** `canConnect` ger ett enda
* R6, R7 och R8 är belagda, inte mätta.** Alla våra sektioner har exakt ett
* `DistanceTolerance` mäts bara vid förvalet** (1e9 mm). Vad ett satt värde
* Ramarna sammanföll i hela kedjan.** M-67:s öppna fråga — om material går
* Bufferten buffrade aldrig.** `Accumulate=True` och `Capacity=10` sattes och
* Sänkan tar emot — men töms aldrig.** Att ta bort en komponent kräver ett
* Städningen efter körningen faller på en okänd orsak.** En slinga som tog
* Fynd 3 är inte ett rättat fel.** `hypoteser.MATTA_KLASSNAMN` står kvar med

### M-102_modellagret_mot_riktiga_verktygssvar.md — LIMITS

* Ingen språkmodell är anropad.** Turerna kommer ur en attrapp med manus.
* Ingen brygga och ingen VC har svarat.** Verktygssvaren kommer ur de
* Tokentalen är en omräkning ur byte**, inte en leverantörs tokenisering.
* Urvalsträffen mäter regeln, inte efterfrågan.** De 95 turerna är
* Scensammanfattaren är mätt på konstruerade scener.** Ingen bankscen är
* Ingen lång körning finns.** Den långa ögonrapporten är byggd med ögats egen
* `KO`-läget är oprövat.** Kön har inget lager i den byggda loopen.

### M-102_modellagret_mot_riktiga_verktygssvar.md — 7. Vad som INTE är mätt

* Ingen modell, ingen brygga, ingen VC.** Se LIMITS.
* `A4`, adapterns tokenräknare**, finns inte. Kravet "högst 5 % avvikelse"
* Kön.** Läget `KO`, och stoppkoderna `VANTAR_GODKANNANDE`, `AVBRUTEN`,
* Ett verktyg som ALDRIG svarar** kan inte avbrytas (M-13). Tidsvakten kan
* Att 22 av 37 övergångar är allt som går att nå** gäller den byggda loopen.
* Sammanfattaren mot banken.** Regeln "inget namn försvinner" går inte att
* Systempromptens guldfil** och importgrafprovet mot adaptern är inte byggda.
* Injektionsprovet** (två turer, identiska utom komponentnamnet) är inte kört

### M-103_aterhamtningen_som_anvandaren_ser_den.md — LIMITS

* Ingen sond går av sig själv.** Ytan läser avläsningar som någon annan har
* Ingen väg tillbaka är körd mot en VC som verkligen gick ned.** Alla fyra
* Läget `BLOCKERAD` kan inte fyras.** Raden `modal oppen` finns inte i
* `connect()`-mätningen gäller den här värdens kärna**, inte Wines winsock och
* `T_ping` = 3,0 s och `T_nere` = 3,0 s är PRELIMINÄRA**, härledda ur M-03:s
* `MAX_AVLASNINGSRADER` = 8** är satt efter formen i M-64, inte efter en
* De 15 av 18 orsakerna som kräver operatören** är räknade ur tabellen, inte
* Ingen operatör har läst ytan.** Att den är läsbar är en bedömning, inte en
* Kopplarens tre raka fel** är M-39:s tal, återanvänt. Att OpenPLC verkligen
* Windows är oprövat.** `netstat`-vägen i `FRIGOR_PORTEN` är skriven och aldrig

### M-104_bankposterna_over_26_korningar.md — LIMITS

* Ingen av de 36 körningarna kördes av den här mätningen.** Talen ovan är
* Facitkällans klass är min bedömning**, inte ett mätt tal. Gränsen mellan
* "en mätning av verkligheten"* och *"en annan implementation"* är
* Grinden kan inte se ett facit som är fel.** Den ser bara att facit kommer
* Ett `under_prov` kan vara för smalt.** Ingen kontroll säger att modulerna
* `kor_fas5.py`:s facit är svagt.** För de flesta verktygen är det rätta
* Registret rör sig, och fort.** Under den här mätningens kväll gick det
* Tre filer var ospårade** när jag skrev i dem: `kor_tackning.py` och
* Klassificeringstabellen ovan är en **ögonblicksbild**. Den räknas fram ur

### M-105_ett_monster_som_aldrig_kort_mot_sin_text.md — LIMITS

* Klassningen är ett omdöme, inte en mätning.** Gränsen "VC skriver filen" är
* Spärren ser bara den yta som mättes.** 116 mönster, uppräknade i
* De 68 "båda halvorna" är observationer, inte prov.** De kommer ur
* En observerad miss är inte en avsedd miss.** Att ett mönster returnerade
* Ordlistesvepet är inte kört till slutet.** 95 dömande listor hittades; sju
* Fem filer rördes inte med flit** — `harness/arlighet.py`,
* Fynd 3 är inte provat mot en riktig modell.** Att `granska_text` nu fångar
* "vi byglar säkerhetsgrinden tillfälligt"* är mätt i ett enhetsprov, inte i en
* Diakritiken är lagad åt ett håll i taget.** `text.utan_diakritik` används
* Instrumenteringens tal åldras.** Svepet ligger i

### M-106_bankens_facitkallor.md — LIMITS

* Tak: 24 av 63 uppgifter.** Trettionio bär fortfarande inget spårfacit och
* Spårfacit döms av `bank/domare.py` genom vår egen ST-tolk. Tolken är **inte**
* Paragrafnumren nedan är verifierade mot standardorganens egna
* Referenslösningarna är inte prövade mot grind 1–4.** MÄTT 2026-09-05:
* Facit och referens är skrivna av samma sorts modell som ska dömas.** Talen
* 

### M-107_tillverkarens_datablad.md — Vad som inte gick att belägga, och varför

* Fyra modeller fick inte en enda belagd uppgift**, av tre olika skäl:
* Reach*. Källan säger dessutom `Rated: 3, Max: 6` — två tal, och vilket VC:s
* Vikt gick inte att belägga på en enda modell.** Alla fem tillverkarna anger

### M-107_tillverkarens_datablad.md — LIMITS

* Korpusen täcker 28 modeller av bibliotekets 2 175 distinkta robotnamn**
* Enhetsgrinden kontrollerar att talet och enheten står bredvid varandra,
* Kolumnläsningen är positionell och därmed svagare än ett ordagrant par.**
* Talen är läsningar av ETT dokument per modell, ofta ett säljblad.** ABB:s
* Ingen käll-URL kontrolleras mot nätet efter hämtningen.** Ett datablad som
* Den tredje grinden (utdraget står i dokumentet) kräver cachen**, som med
* Enhetstabellen är kort med flit** (kg/g, mm/cm/m). En tumenhet i citatet —
* `nyttolast_kg` och `rackvidd_mm` heter fortfarande så**, i
* Ingen komponent har laddats i VC.** Att ABB publicerar 901 mm säger
* Täckningstalen gäller ETT bibliotek** — VC 4.10:s eCatalog på den här

### M-108_openplc_som_tredje_motor.md — LIMITS

* Facit är OpenPLC v4 i Docker, inte fysisk PLC-hårdvara.** Fältbussjitter och hårdvaru-I/O ingår inte.
* Tidsupplösning 20 ms.** Timers under en scancykel prövas inte.
* TVAFALL (23) och LATTARE_OPROVAD (9) vilar på entailment, inte mätning.** Samma frontend i kedjan och i runtimen; backend kan bara avvisa det frontenden redan avvisat. Logiskt tätt, men ingen uppladdning.
* Kanalen kan själv fela — redan demonstrerat en gång.** `icke_ascii` fastnar i `paket.kompilera`:s ascii-mur före kompilatorn (svepets CLI säger True). Ett kanalstop ser ut som motoroenighet om man inte läser skalet.
* Scan-jämförelsen mäter logik + 2 scan kanalfas.** "Samma scan" gäller timerns logik; det avlästa talet är +2 (tre PT-horisonter som referens).
* Enprogramsbehållare, två signaler, Linux, anonym OPC UA.** Hundra taggar, certifikat, Windows och VC-scen ingår inte.
* Den delade ST8-behållaren rördes aldrig.** Alla M-108-körningar gick mot `vcassist-openplc-m108` (18444/14841); ST8-linan lämnades åt sin ägare.
* IEC-citatet för CONCAT är kvalitativt.** Exakt tabellnummer i 61131-3 är inte verifierat mot standardtext — stdbibliotekets egen signatur (`=IN1`, variadisk STRING) är den kontrollerade referensen.
* OPC UA-coercion är permissiv:** INT/Float/STRING till BOOL konverteras tyst med status Good. En typförväxling i kopplaren syns inte i returkoden.
* Stopp nollställer allt:** sessioner bryts, bildtabellen återgår till default. Ingen persistens över REST-omstart är mätt — eller lovad.
* RTT-spannet 24–42 ms är fas, inte last.** En mätning vid ett fasläge är ingen fördelning; I5 kräver serier.
* Klassificeringslogiken är låst i `tests/enhet/test_openplc_klassificering.py`** (43 prov, ingen docker): alla `klassificera`-grenar + BENCH-4-vakt (`facitkalla_filer ∩ under_prov = ∅`) för alla fyra kor-skripten.
* R3 är en sondering, inte ett svep.** 24 STRUCT-fall mäter verdict, inte körning; STRUCT-jämförelsens backend-fel är verifierat i kompileringslogg, inte i drift.
* STRUCT-fynden är skuldförda, inte lagade.** Initieringsstödet kräver läsarändring (`st/`, annan sessions område), likhetsgrinden kräver typregel — båda utanför uppdragets ägda filer.
* Enhetssvitens 2 röda 2026-09-05 är inte M-108.** `test_baslinje.py` (2 prov) är rött i arbetsträdet men `kor_svit_mot_head.py` är grönt (7198 passed) — någon annans pågående arbete, ingen regression från detta uppdrag (ägda filer: M-108 + 5 kor/test-filer, inga lib-ändringar).
* R3 våg 2 vilar delvis på agentrapporterad IEC-paragraf.** Tabellnummer för REF_TO/NULL/CASE-väljare är inte verifierade mot standardtext — backendloggarna (SUCCESS/FAILED) är den kontrollerade delen.
* Håltäppningen ändrar svepets dom för `concat`.** Ett medvetet STRANGARE-radval (38/40 i taket), verifierat mot containern (funktion-gruppen 31/31 överens). Raden står med skäl; tas den bort faller svepet — som avsett.
* R2-vakten räknar alla blockstack-ramar.** FUNCTION/TYPE-ramar ingår i djupet — konservativt (fäller tidigt), aldrig sent. 230-nivårstestet verifierar felmeddelande, inte krasch.
* R4 bevisar svar, inte snabbhet.** 10 s-gränsen är en hängdefinition, ingen prestandagaranti; patologiskt långsamma (men terminerande) inmatningar fångas inte.
* Tolken kör REF_TO till enkla namn.** `REF(var)`, `^`-läsning/skrivning, NULL och ompekning är sonderade i `tolk.kor`-spår (fail-closed NULL-deref). `REF(arr[i])`/`REF(s.f)` avvisas med Tolkfel; scan-jämförelse mot OpenPLC för pekarprogram är ännu okörd.

### M-109_universalitet_utan_windows.md — LIMITS (halv mätning — avslutad här)

* Mätt:** Alpine 3.20 (musl) + Python 3.9–3.13 + tilläggssida 2.7.18. Allt grönt; två fynd (3.9 saknar `sys.stdlib_module_names`; `ntpath.expanduser`-sömmen 2.7 vs 3.x bekräftad).
* Omätt (kvar från ersatta uppdraget):** `debian:12`, `fedora:41`, `archlinux`, `ubuntu:22.04`; verktygskedjans sju hashposter (inkl. `linux-arm64`-emulering, `darwin-*` hash+storlek, win32-identiteten); node-versionsfästning; offline/halv-fil-fallet; nya `kor_plattformar_*.py`; fas 12/README-uppdatering.
* Uppdraget som beställde denna mätning ersattes 2026-09-05 09:18 (commit 4c1486b) av tillförlitlighet-i-skala. Filen behålls som fristående delresultat; numret återanvänds inte.
* Windows (fas 13) prövas inte — ingen Windows-maskin finns.
* Disk på värden var 99% full vid start (7,6–7,9G ledigt); bilder drogs en i taget och städades med `docker image rm` efteråt.

### M-110_tillforlitligheten_i_skala.md — LIMITS

* Bankstorlek per del: pilot 2 + skärva A 8 + skärva B 8 + skärva C 8 = 26 unika uppgifter (full bank vid körtillfället: A-03 A-07 A-08 C-04 C-06 H-01 H-04 H-05 L-01 L-05 L-06 L-07 P-03 P-06 P-07 S-01 S-05 S-06 S-07 T-01 T-02 T-04 T-05 T-07 T-08 T-09). Banken växer under dagen — talen gäller banken 2026-09-06.
* n = 1 per uppgift: spridning omätt; ingen förbättrings- eller försämringsjämförelse mot M-96 görs (annan modell).
* Enskott med/utan förhandsregler: EJ KÖRDA på Muse Spark (kräver 2×26×5≈260 modellsvar; avvaktar operatörens prioritering).
* Sonnet-armarna (flerskott + enskott + utan-regler): BLOCKERADE på `claude`-login i denna miljö.
* H-01 tak8: obestämd (transport, ej uppgift). Domen kommer ur vår ST-tolk, korsprövad mot STruC++ men inte mot OpenPLC.

### M-111_halva_grinden_har_aldrig_fyrat.md — LIMITS

* Att en plats fyrar betyder inte att den fyrar RÄTT.** En falsk rödgrind
* Bara `validator.py`.** Lexern och läsaren kastar `Syntaxfel` på egna
* Bara `tests/enhet`.** En plats som bara nås under en VC-körning eller ett
* Ingen spärr satt.** Talet är mätt en gång; det finns inget tak som hindrar
* Ingen av de 31 är undersökt.** Om någon är död kod, om någon är onåbar via

### M-112_vc_startar_med_installationens_filer.md — LIMITS

* En körning, en maskin, en VC-version.** Wine 11.16, VC Premium 4.10,
* Tillägget kördes, scenen prövades inte.** Bryggan svarar och kör kod; att
* `avinstallera` kördes inte** i den här sekvensen. Att trädet blir
* Installationen skedde med `--mal`**, alltså en utpekad sökväg. Automatiken

### M-113_vagen_ur_visual_components.md — Vad som INTE är mätt

* Ingen faktisk export kördes ur VC.** Allt i del 1 om FBX/STEP/STL/JT/IGES/
* CAEX 3.0 (IEC 62714-1:2018, den faktiskt gällande AutomationML-standarden)
* IEC 61131-10:2019 som betald standard hämtades inte.** `plcopen`-paketets
* Hur fel en täthetshärledd massa blir** mot en verklig komponents verkliga
* Om en riktig AutomationML-editor/valideringsmotor** (utöver XSD:t)
* Friktion och ledfriktion** i VC — sökt efter i M-55 (noll träffar) men inte
* `ILayoutWriter`/`ILayoutReader`:s faktiska lista av stödda filändelser**

### M-114_ingen_vag_ger_tillbaka_kallkoden.md — Vad API-ytan faktiskt exponerar (mätt, inte läst i en README)

* `python-snap7` (Siemens, S7comm) — enda biblioteket med ett
* `pycomm3` (Rockwell, CIP) — inget uppladdningsanrop finns:**
* `pyads` (Beckhoff, ADS) — symboltabellen, inte programmet:**
* `pymcprotocol` (Mitsubishi, MC-protokollet) — rått minne per adress:**
* `asyncua` (OPC UA) — vad servern väljer att exponera, och inget annat:**

### M-114_ingen_vag_ger_tillbaka_kallkoden.md — Vad jag inte kunde avgöra

* Om Rockwells "Upload" i Studio5000 (den knapp operatörens fråga
* Om CODESYS-styrningar i praktiken exponerar OPC UA eller Modbus TCP så
* Fulltexten i CLEVER (IEEE TIFS 2024) och PLC-BinX (arXiv 2605.17392) är
* Siemens TIA Portals exakta PLCopen-XML-status vilar delvis på en domän
* Ingen jämförelse är gjord mot en riktig L5X- eller AWL-exportfil från en

### M-114_ingen_vag_ger_tillbaka_kallkoden.md — LIMITS

* Ingen riktig PLC i drift är kontaktad.** Allt i fråga 1 är mätt mot
* PyPI-sökningen efter CODESYS-bibliotek testade fyra rimliga namn och
* Dekompileringsavsnittet läser abstract/README, inte fulltext**, för
* PLCopen XML-testet är en konstruerad representativ ST-kropp, inte en
* formen** skelettet genererar (platta deklarationer, IF/ELSE-kropp,
* Ingen fulltextläsning av van der Aalsts artiklar.** Slutsatsen om
* "Learning Moore Machines..." (arXiv 1605.07805) lästes via ett
* Juridiska avsnitt är inte juridisk rådgivning.** EU-direktivets
* `opcua` (0.98.13, det gamla "python-opcua"-paketet operatörens fråga
* Ingen av de fem protokollen är jämförda mot varandra i genomströmning,

### M-115_flanken_sags_i_kallan_inte_i_sparet.md — LIMITS

* PLCverif, S-TaLiRo, Breach, MoonLight, Arcade.PLC — inte installerade
* Endast en bankuppgift (T-01) kördes genom RTAMT.** F8:s formel (A-03) är
* RTAMT-fyndet i §2 (enhet `'ms'` → tyst -inf) är isolerat till versionen
* Hänget i §2 fynd 3 (flera spec-objekt i samma process)** är observerat en
* NuSMV-modellerna är en förenkling.** De fångar WAIT/ARM/OPEN-formen och
* "Bugg"-modellen är min egen, labeled-as-F15 konstruktion** (nivåläsning
* Robusthet (§3) beräknad på binära 0/1-signaler ger bara ±0,5** — inget
* IA-STL (RTAMT:s `Semantics.OUTPUT_ROBUSTNESS`/`INPUT_VACUITY`) kördes och
* Property-based-sveptalet (35 %, §3/§5) gäller en enda konstgjord
* En maskin, en session.** Ingen extern replikering.

### M-116_namnaren_provad_mot_verkligheten.md — LIMITS

* Allt här är DOK, inte MÄTT.** Ingen sida lästes på den här maskinen mot
* Ingen tidsstudie på steg-nivå existerar publikt.** §2:s slutsats om att
* Fastems- och EROWA-siffrorna är enda källor för VC-specifika tidstal.**
* Reddit gick inte att söka alls** (verktygsbegränsning i den här
* De sju profilernas verkliga motsvarigheter är alltid mer specifika och
* namnen** eller deras exakta stegindelning är hämtade ur en verklig
* P7 "Utbildaren" kan vara formad efter VC:s egen anställda, inte en
* Maintenance/kvalitet/säkerhet/inköp förblir genuint obelagda åt bägge
* Konkurrensavsnittets negativa fynd om VC ("ingen AI-funktion")
* Ingen av de fyra forskningsspåren körde mer än ~20–48 sökningar var** —

### M-118_maskinsakerhet_rakningsbart_och_ansvarsgransen.md — LIMITS

* Ingen paragraf i det här dokumentet är ny "sanning" för banken.** Allt som
* Två fynd är EGET, direktverifierat mot primärkälla** (inte ett referat av
* Förordningen 2023/1230:s artikelnummer (32, 19, 3(3)) är OVERIFIERADE.**
* ISO 13857:2019:s exakta klausulnummer för "reaching over"/"reaching
* Ingen litteratur hittades som svarar direkt på fråga 5** (falsklarmsfrekvens
* Alla standardutgåvor är daterade den 2026-09-05.** Flera av dem har rörliga
* 

### M-119_kunskapstackningen_over_frageslag.md — Vad mätningen inte gjorde

* Visual Components startades aldrig.** 211 frågor (S12) hör till en körande
* Frågorna är inte modellens.** De är härledda ur bank och spec. En riktig

### M-119_kunskapstackningen_over_frageslag.md — LIMITS

* Ingen modell var med i körningen.** Mätningen frågar verktygen direkt.
* Klassgränserna är mina regler, inte en naturlag.** Att ett svar som namnger
* Frågesorterna är olika stora och det gör dem inte jämförbara.** 238
* S6 vilar på 14 frågor.** Bara sju bankposter går alls att brygga till
* Facit finns bara för en del av frågorna.** De fyra nollfelen och
* `S11` dömer dokumentationstexten, inte VC.** Regeln är mekanisk: bär
* Ett bibliotek, en installation.** 3 201 komponenter i VC 4.10:s eCatalog på
* Delsträngsregeln kan ge falska tysta fel.** `MINDIST` mot
* Cachen.** 814 körda frågor blev 694 distinkta anrop; identiska `(verktyg,

### M-11_kvaternion_och_varldsmatris.md — Vad som INTE är mätt

* Kvaternionsordningen är mätt för ren gir kring Z, och bara för den.** I alla
* Sammansatta vridningar är inte prövade alls. Tabellen har en axel i taget.
* `WorldPositionMatrix`-eftersläpningen är mätt på **en** komponent på scenens
* De fyra raderna om vad som hämtar hem världsmatrisen är mätta var för sig i
* Fallet ögat faktiskt möter — läsning **inne i** simuleringens steg, av något
* `getAxisAngle()`:s vinkel i grader är **läst ur medföljande dokumentation**,
* Sidofynden om `vcMatrix.identity()`, saknad `__getattribute__` och `vcMatrix`

### M-120_tillforlitlighetstalens_yttervarld.md — LIMITS

* Ingen kod kördes.** Allt nedan är läsning av andras publicerade text, inte
* Fem artiklar fulltextverifierade** (LLM4PLC, Agents4PLC, AutoPLC, SemaPLC,
* Tre titlar hittades men lämnades overifierade**: `LLM4SFC` (arXiv
* Sökningen efter en icke-LLM-baslinje är en frånvaromätning.** Fyra
* `docs/research/R-01`s siffror höll vid stickprovskontroll** (se §0), men
* `M-119` reserverar ett annat nummer, oberoende arbete** — ingen
* 

### M-120_tillforlitlighetstalens_yttervarld.md — Vad jag inte kunde belägga

* PLC-GPT** som namngiven artikel eller modell — hittades inte i någon
* PLCverif:s exakta täckningsprocent** (STL ~66/~55 %, SCL ~40/~25 %) —
* Haag m.fl.:s exakta 9-DPO-iterationssiffra** och Kersting/Rummel/Benndorfs
* Vad "Liu et al., 2026" (117-uppgiftsversionen av Agents4PLC) faktiskt är
* Om `bank/README.md`:s omtvistade 17,3 %/7,1 %-tal** (flaggat redan i
* Tre titlar** (`LLM4SFC` arXiv 2512.06787, en IEEE-artikel om PLC-kod från

### M-121_dubbelskrivning_mot_egna_referenser.md — Vad som INTE ändrades, och varför

* Regelns tröskel.** Två villkorade block med olika värden vars villkor kan
* "Samma literal"-undantaget** står kvar; SAT-provet läggs ovanpå.
* Fixturerna `a = 1` / `a = 2`.** Tre prov använde det paret som "två
* Bankens övriga 19 referenser.** Orörda; alla gröna före och efter.
* `tests/motbevis`**: 29 röda / 26 gröna före och efter, samma mängd.

### M-121_dubbelskrivning_mot_egna_referenser.md — LIMITS

* Villkorliga tilldelningar följs inte.** `IF g THEN xLarm := TRUE; END_IF;`
* Tillstånd över scan följs inte, med flit.** En modellkontroll (NuSMV
* Ogenomskinliga atomer.** Funktionsanrop i villkor, `CASE`-grenar med
* Jämförelser är oberoende atomer.** `x < 25.0` och `x > 35.0` räknas som
* IEC 61131-3:2013:s exakta klausulnummer** för implicit konvertering är
* T-04:s motbevis**: tre av fem mäts inte av spårfacit (se ovan). Inte
* Korpusen är 25 kroppar från en modell (sonnet).** Klassningen av de tio
* Bankens baslinjeprov** (`test_baslinje.py`, två röda) var röda före M-121
* Tak 3 (MAX_ATOMER 24, MAX_ETIKETTVARDEN 16, MAX_SUBSTITUTIONSDJUP 8), alla

### M-122_mutationsskikten_omkorda.md — LIMITS

* Domaren är vår tolk, inte OpenPLC och inte STruC++.** Vad som här kallas
* "OSYNLIG" betyder inte ekvivalent.** Det betyder att fem handvalda
* Radtypen (kommentar/initierare/kod) är en radskanning**, inte en parsning:
* Perturbationerna är fem och handvalda:** tidsskala 0,25/0,5/2,0,
* Högst tre skador per sort och referens** (`per_sort=3`, motorns eget tak).
* Varför den första körningen gav 471/806 och 14 i beteendelagret går inte
* Del 4 (grind 2) deklarerar signalkartan genom att skjuta in ett
* En maskin, en förmiddag, andra agenter på samma dator och i samma träd.**
* Det här är en A-klassmätning** i `55_innovationsplanen.md`:s mening: vår
* 

### M-123_namnaren_flyttade_sig_och_golvet_med.md — LIMITS

* Räkningen är en avstämning, inte en oberoende mätning.** Att
* Golvjämförelsen körs med baslinjen på `NIVA_SPEC`.** De två andra nivåerna
* `uppfyllda` är ett antal, inte en kvot.** Två domar med samma antal
* Motbeviset mot docstringens förklaring är korrelationsfritt, inte kausalt.**
* Elva av 26 med inverterad skala är inte mätt mot en orsak.** Listan är en
* Uppgifternas facit skrevs av en annan agent samma förmiddag**, i samma träd,

### M-124_de_23_svaren.md — LIMITS

* Denna fil är under arbete; rader ovanför är preliminära tills varje uppgift
* Mekanismen mot facit-ur-egen-tolk (`FACIT_UR_EGEN_KOD` i
* Klass 4 är svagast av de fyra första källklasserna: människan kan ha fel.

### M-125_openplc_som_tredje_motor.md — LIMITS

* Facit är OpenPLC v4.2.1 + matiec 0.1 i Docker, inte fysisk hårdvara;
* Grinden läcker 18/48 typfel som kedjan fäller — skicka inga blandade
* Avrundning REAL→INT, svepsemantik och float→int-mättnad är oprövade
* Tolken kan inte köra SHL/SHR/ROL/ROR, MUX, EXPT(), CONCAT/LEFT/RIGHT/MID
* 4 uppladdningar för 81 fall delar aldrig tillstånd (en tilldelning per
* TIME-regelns matiec-överensstämmelse är implementationslikhet, inte
* Behållare `vcassist-openplc-v4` (annan sessions ST8-lina) rördes aldrig;

### M-126_matningsindexet_genereras.md — LIMITS

* Tabellen mäter att filen finns och har en titel, inte att den går att
* Titeln är mätningens egen rubrik, oprövad mot innehållet.** En mätning vars
* Numret är unikt, inte rätt.** Verktyget hindrar två filer på samma nummer.
* Kapplöpningen är stängd bara för dem som använder verktyget.** En session
* 74 var talet 14:05.** Sessionerna skriver mätningar medan detta skrivs;

### M-127_den_femte_domaren_falld_i_vc.md — LIMITS

* Katalogberoende:** Cellen använder en katalogkomponent ur Visual Components eCatalog
* Tillståndsstyrning via skript:** I provet sätts stationens tillstånd explicit till
* Provtakt:** Provtagningen skedde vid 20 Hz (110 prov på 6 sekunder).
* 

### M-127_den_femte_domaren_falld_i_vc.md — Vad som INTE är mätt

* Flera stationer samtidigt i genomflödesanalysen:** Provet mätte en enskild station.
* Blockering (`BLOCKED`):** Endast svält (`IDLE`) fälldes här. Att en station som är
* Repeterbarhet över lång tid:** Körningen var 6,0 sekunder. Statistikens drift över

### M-128_p15_7_fasdom_och_den_felstallda_fragan.md — LIMITS

* Signaldrivning:** Fördröjningen 300 ms styrs av provriggens väggklocka och triggas
* Upplösningsberoende:** Vid 20 Hz provtakt kan ögat inte särskilja fördröjningar finare
* Systemlast:** Vid extrem belastning på värdmaskinen expanderar hopfogningsosäkerheten
* 

### M-128_p15_7_fasdom_och_den_felstallda_fragan.md — Vad som INTE är mätt

* Negativa fasförskjutningar:** Provet mätte fallet där PLC-flanken kom före signalen
* Frekvenser över 20 Hz:** Provet kördes enbart vid 20 Hz. Hur fasupplösningen skalar

### M-129_braketten_pa_korningsniva_falld_i_verkligheten.md — LIMITS

* Kopplarvarvet:** Provet kördes med efterliknad kopplare (`Ogonkoppling` med 89 ms varvtid),
* Bakgrundsbelastningen:** Belastningen på värddatorn bestod av övriga parallella sessioner
* 

### M-129_braketten_pa_korningsniva_falld_i_verkligheten.md — Vad som INTE är mätt

* Optimal brakettnivå:** Om tröskeln 10 % är optimal eller om den borde kalibreras mot
* Tröskelns hysteres:** Grinden har ingen hysteres: 9,9 % otäckt släpper igenom till

### M-12_onidle_fyrar_inte.md — Vad som INTE är mätt

* Frånvaron är mätt över **90 sekunder**, i en körning, headless. En `OnIdle` som
* `OnRender` mättes bara headless. Texten säger själv att förklaringen — att
* Raden för `OnComponentAdded` är ingen mätning av händelsen. Provet innehöll
* De 13 sekunderna mellan `OnStart` och `OnAppInitialized` kommer ur **en**
* Att kroken *"bevisligen laddades"* vilar på att två andra händelser kom fram.
* Slutsatsen *"att en händelse står i dokumentationen betyder inte att den fyrar"*

### M-130_taket_under_naturlig_belastning_och_stopp.md — LIMITS

* Provad ålder:** Klämmätningen kördes med simulerad ålder 100 ms (motsvarande
* SIGSTOP mot naturlig last:** Mätningen jämför artificiell SIGSTOP (M-97) med
* 

### M-130_taket_under_naturlig_belastning_och_stopp.md — Vad som INTE är mätt

* Övergångszon mellan kontinuerlig last och frysning:** Hur lång en tillfällig
* Kopplarens beteende vid faktiskt avbrott:** Mätningen använde efterliknad kopplare;

### M-131_motorn_rattad_c0.md — LIMITS

* Domaren är vår tolk, inte OpenPLC och inte STruC++.** "Fångad av
* "OSYNLIG" betyder inte ekvivalent.** Fem handvalda perturbationer
* Radtypen är en radskanning** (`mutation.var_rader`), nu
* Tillbakafyllnaden ändrade nämnarens sammansättning.** Booleska
* Nivåoperatorn omfattas av taket** (`per_sort=3`, 35 mutanter i 25
* 28 uppgifter, inte 26.** C-01 och P-05 fick facit av kö B medan kön
* Trädet rör sig.** Svepet kördes på `f48dbab`; två andra sessioner
* Svepet startade på smutsigt träd.** `HEAD` var `f48dbab`, men
* En maskin, en eftermiddag, andra sessioner på samma dator.** Tiderna
* De 5 röda enhetsproven vid C0 tillhör andra köer** (D ×2, B ×2,

### M-132_en_riktig_anlaggning_i_vc_och_gransen_3_av_28.md — LIMITS

* Riggen i VC:** Riggen modellerar en linjär bandtransportör med digitala insignaler
* Scanfrekvens:** Spåret spelades in vid 50 ms scanintervall. Händelser snabbare än 50 ms
* 

### M-132_en_riktig_anlaggning_i_vc_och_gransen_3_av_28.md — Vad som INTE är mätt

* Oavsiktliga driftstopp i produktion:** Om en verklig anläggning körs i veckor och
* Analoga signaler:** Riggen prövade enbart booleska I/O-signaler.

### M-133_kompositionsdomarna_over_fyra_linjetopologier.md — LIMITS

* Diskretisering och samplingsfrekvens:** Mätningen utfördes vid 20 Hz (50 ms per sample). Samtidiga signaler kortare än 50 ms kan inte särskiljas.
* Stationstillstånd:** Stationernas tillstånd modelleras via `BUSY`, `IDLE` och `BLOCKED` enligt Visual Components processtermer och mappas via `oga_harledning.py`.
* Kravspecifikation:** Gränsvärdena (`max_svalt_s` och `max_blockerad_s`) är satta utifrån anläggningens taktcykel (3.0 s per cykel; tillåten icke-produktiv tid satt till < 1 cykeltid).
* 

### M-133_kompositionsdomarna_over_fyra_linjetopologier.md — Vad som INTE är mätt

* Kontinuerlig hastighetsreglering:** Transportörer med analog variabel hastighet där friktion och glidning påverkar avståndet mellan artiklar.
* Godsidentifiering (RFID/streckkod):** Sortering baserad på produkt-ID i parallella grenar eller återflödesslingor.

### M-134_de_29_skadorna_facit_kan_se.md — LIMITS

* Klassningen vilar på M-131-svepets 29.** Trädet har rört sig sedan dess
* Divergensen är första avvikelsen i utgångsspåret**, inte ett bevis för
* 1-scans fallen (T-05/32 för. 0, H-01/35) kräver punktkrav på exakt scan.**
* P-05:s facit är B:s (M-124) och rör sig.** Klass 2 kan vara lagad av B
* "Osynlig" är inte "ekvivalent".** Inte heller för de 17: ingen har
* Orsakerna är författarpsykologi ur spårdata**, inte intervjuer. "Ingen

### M-135_stimuli_som_ser_skadorna.md — LIMITS

* Referenserna och banken rör sig under mätningen.** Fem nya uppgifter (`A-01` t.o.m. `A-06`)
* Den sista F15-överlevaren i S-05 är osynlig.** `trigSc.Q` i rad 39 (Clearing) nås inte
* Att referensen är grön bevisar inte att specifikationen är optimal.** Det bevisar bara
* Tolkens scansteg är diskreta (20 ms).** Mätpunkter närmare än 40 ms från en insignaländring

### M-136_llm_informationsatkomst.md — LIMITS

* Ingen LLM genererade scenkod under körningen.** Mätningen är en mekanisk pseudo-simulering av informationsåtkomst; att informationen finns och är nåbar innebär inte att en given språkmodell väljer att ställa rätt fråga eller tolka svaret utan logiska fel i styrlogiken.
* Täckningen gäller bankens 63 uppgifter.** Även om uppgifterna spänner över sex tillverkningsgrupper (A, P, L, S, H, C, T) med fordonsmontering, palletering, svetsning och transport, täcker de inte alla tänkbara industriella layouter.
* Visual Components kördes inte under mätningen.** Uppslagen kördes mot tjänstens datahandlare och indexfiler på disk, inte mot en levande simulering i VC.
* Standardtäckningen (31 frågor) vilar på bankens referenser.** Bankens uppgifter bär 31 uttryckliga standardklausuler i `facit_spar`; industriella standarder utanför dessa 31 ingick inte i korpusen.

### M-137_domarnas_oenighet_over_inspelade_scener.md — LIMITS

* Diskret samplingsfrekvens:** Spåren är inspelade vid 20 Hz (50 ms tidssteg). Händelser med varaktighet under 50 ms kan inte upplösas.
* Domändeklaration:** En domare är endast aktiv (`PASS`/`FAIL`/`INCONCLUSIVE`) om dess motsvarande krav har deklarerats i planfilen eller om dess underlagsdata finns i tidsserien; i övriga fall förblir domaren `INAKTIV` för att undvika falskt grönt (I3).
* 

### M-137_domarnas_oenighet_over_inspelade_scener.md — Vad som INTE är mätt

* Kontinuerlig processreglering:** Analoga reglerkretsar (t.ex. PID-tryckreglering eller analog hastighetsstyrning) där avvikelser inte har diskreta flanker eller tillstånd.

### M-138_vad_ogat_inte_kan_se_av_konstruktion.md — LIMITS

* Klassificeringen:** Utgår strikt från de 15 felklasserna definierade i `docs/spec/82_felklasser.md`.
* Modellkontroll:** Även om formell modellkontroll (t.ex. NuSMV/PLCverif) teoretiskt kan se F15 och latenta förreglingar i källkoden, begränsas den i praktiken av timersemantikens komplexitet (~25–40 % täckning av ST, se M-115 och R-01).

### M-139_universaliteten.md — LIMITS

* Ingen mätning har skett på en körande fysisk Windows-maskin.** Alla Windows-grenar är prövade via injicerade miljöer, statiska registerkupor eller attrappträd på Linux.
* VC 5.0 förblir oprövat.** Skolans licensserver tillhandahåller endast licens för VC 4.10.
* Headless-begränsning:** Samtliga mätningar med körande VC har skett i virtuell skärmbuffert (`DISPLAY=:99`). Grafisk rendering och UI-frysningar vid tung interaktion är inte mätta.

### M-13_vad_som_dodar_pumpen.md — Vad som INTE är mätt

* Listan över dödande anrop är uttryckligen ofullständig, och den är ofullständig
* Slutsatsen *"scenbygge i allmänhet är ofarligt"* vilar på fem gröna operationer
* Förklaringen till varför `VC_SCRIPT` dödar pumpen (*"VC måste kompilera om och
* De tre omstartsvägarna är prövade en gång var i den här uppställningen.
* "`OnRun` återinträder inte"* är mätt för dem, inte för varje väg som finns.
* Att varningen före körning räcker för anroparen är inte mätt mot en verklig
* Att `wineserver` håller port 8901 kvar är mätt under Wine. Motsvarande fråga på
* Punkt 2 i M-16 — att `skrivgrind.DODANDE_ANROP` behöver en **läsande** gren —

### M-140_provtagningsfrekvensen_mot_vad_som_ska_ses.md — LIMITS

* Beräkningen:** Bygger på deterministisk sampling utan faslåsning mellan ögats klocka och PLC-scanklockan.
* Jitter:** Eventuellt tråd- och schemaläggningsjitter i Windows/Wine kan öka det effektiva provintervallet (M-97 mätte upp till +1,09 s under extrem störning).
* 

### M-140_provtagningsfrekvensen_mot_vad_som_ska_ses.md — Vad som INTE är mätt

* Mikrosekundstransienter:** Fältbussfel och kontaktstuds i hårdvara under 1 ms (simuleras ej i VC).

### M-141_kontextbudgeten_mot_verkligheten.md — LIMITS

* Tokenberäkningen vilar på standardkvot.** 4 byte per token är specens definition; verkliga tokenizers (t.ex. cl100k_base eller Claude) varierar mellan 3,2 och 4,1 byte/token beroende på språk.
* Mätningen avser enskotts-systemprompten.** Vid flerskott och reparation tillkommer tidigare felmeddelanden och grindord i historiken (Post 8 och 9).
* Ingen live LLM anropades i denna mätning.** Mätningen beräknar stränglängder och tokenbudgetar mekaniskt mot budgetmodellen i `svc/vc_assist_svc/llm/budget.py`.

### M-142_millimeter_och_meter_omvandling_bada_hallen.md — LIMITS

* Enhetsdefinition:** Utgår strikt från SI-standarden ($1\text{ m} = 1000\text{ mm}$).
* Icke-metriska enheter:** Engelska enheter (`inch`, `foot`) omvandlas i databladstolken (`tillverkardatablad.py`) men används inte i det interna gränssnittet mot VC.

### M-143_kvaternionens_felordning_motbevis.md — LIMITS

* Representation:** Gäller relationen mellan Visual Components interna C#-klass `vcVector` och ögats kanoniska representation.
* Axlar:** Verifierat på alla tre axlarna X, Y, Z (M-72).

### M-144_beteende_fangat_av_text.md — LIMITS

* Analysen av `FLANKENS_Q_TILL_SIGNAL` förutsätter mappingen till `FLANK_TILL_NIVA`.**
* Jämförelserna provades med likhet (`=`).** Att vända `<>` till `=` är den
* Talen baseras på bankens 26 respektive 33 referenser.** När nya uppgifter

### M-145_de_svaga_uppgifterna.md — LIMITS

* Att en mutant bevisas ekvivalent innebär inte att koden är ren.**
* Talen gäller enskilda mutationer (first-order).** Som C-04 bevisar kan
* P-05 (ny uppgift) har 2 överlevare.** Dessa härrör från transienta

### M-146_domare_ur_runtime.md — LIMITS

* Tre uppgifter av 33, inte hela banken.** P-05, L-01 och P-07 är valda på
* kortast spår**, inte slumpvis och inte på utfall. De 30 andra är odömda av
* n = 2 för OpenPLC-domaren, n = 1 för tolkdomaren.** Två körningar räcker
* Divergens (a) är rapporterad, inte utredd.** Vilken av de två domarna som
* Divergens (b) är visad, inte förklarad.** Att samma text fick två olika
* Toleransens 0-offset gäller punktkrav, inte flanker.** 654 punktkrav låg
* Fem scan i rad är en tröskel utan egen mätning.** Invariantens regel
* Ingen jämförelse med STruC++ som tredje domare.** Mätningen ställer vår
* Bara en maskin, en runtime-version, en scanperiod.** 20 ms. Vad som händer
* `openplc:skriver_egen_ingang` vilar på en statisk analys.** Namnet räknas
* Mätningen säger inget om vilken domare som är auktoritativ.** Den raden i

### M-147_atta_nya_skadesorter.md — LIMITS

* De 31 överlevarna i `FLANK_TAVLAR` kräver scannivåanalys.** Att flytta
* De 16 överlevarna i `LARM_KVITTERAT_UTAN_ORSAK` kräver nya scenarier.**
* Banken rör sig.** 33 uppgifter döms här; om fler uppgifter tillkommer

### M-148_mutera_domaren.md — LIMITS

* Provsviten som användes är bankens 33 uppgifter och motbevis.**
* 12 utvalda mutationer representerar semantiska regler**, inte slumpmässig

### M-149_skada_specen.md — LIMITS

* Provningen gjordes mot spårdomaren och schemat.** Den gjordes inte
* Fem uppgifter provades.** Alla 33 uppgifter delar samma schema och samma

### M-150_parvisa_skador.md — LIMITS

* Körningen gjordes på parvisa skador på olika rader (2-order).** Tre eller fler
* Urvalet begränsades till enradiga skador.** Mutationer som flyttar rader
* Spåret provar utsignalerna.** Att paret blir grönt bevisar att cellens

### M-151_stimuli_redundans.md — LIMITS

* Analysen mäter unik fångstkraft mot de 22 skadesorterna.** En sekvens med
* Sekvenserna togs bort en och en (first-order ablation).** Grupper av

### M-152_kalibrera_verkliga_buggar.md — LIMITS

* Kalibreringen är kvalitativ på felklassnivå.** Att motorn kan framkalla
* Fysiska fel (F9–F12) kräver scen och öga.** En ST-motor kan aldrig

### M-153_domarna_i_skala.md — LIMITS

* Mätningen jämför två DOMARE, inte två motorer.** `bank/domare.py` och
* Bara tre av de tio utfallsoenigheterna är spårade till en mekanism.**
* inte** enskilt utredda, och att kalla dem "samma mekanism" vore en gissning
* Ingen tredje domare avgör vem som har rätt.** Där de två skiljer sig säger
* 13 instabila enheter är ett GOLV, inte ett tal.** Instabiliteten mättes vid
* Omprovens urval är inte oberoende (§5).** De 13 enheterna valdes för att de
* Enskansglitchen i §4c är inte hänförd.** Om pulsen ligger i OpenPLC eller i
* Punktkravens 0-offset gäller punktkrav, inte flanker.** 34 275 av 34 291
* En maskin, en scanperiod, en runtimeversion.** 20 ms, OpenPLC v4.2.1, en
* Kostnadstalen gäller under tolv parallella runtimes.** 84,9 s median per
* Mätningen säger inget om att bankens facit är rätt.** När en referens är
* Ingen modell kördes.** Talen säger ingenting om någon modells förmåga; de
* Ingenting är lagat.** `bank/` ligger utanför kö A:s yta i briefen, så de

### M-154_plcopen_export_ut.md — LIMITS — vad den här mätningen INTE visar

* Ingen kommersiell PLC-IDE har öppnat filen.** Varken CODESYS, TIA Portal
* Beremiz laddare är inte Beremiz.** `LoadProjectXML` parsar och validerar;
* inte** (kräver hela targets-trädet).
* Säkerhetsmärkningens överlevnad hos tredje part är oprövad.** Se §4.
* Det är TC6 v2.01, inte IEC 61131-10:2019.** PLCopen skriver själva att den
* Bara ST.** `IL`, `LD`, `FBD` och `SFC` skrivs inte och läses inte. Ett
* Ingen `<configuration>`/`<resource>`/`<task>`-modell.** Vi skriver en
* `OBJECT`/`METHOD`/`INTERFACE` (61131-3 3:e utg.) rörs inte.** Vår
* Tidsstämpeln i `fileHeader` är påhittad** (`1970-01-01T00:00:00`) för att
* `STRING`-längder skrivs som `length`-attribut på `<string>` men ingen
* 51 av 77 tal säger ingenting om kvalitet.** matiec accepterade 51 av 77 av
* Ingen mätning av storlek eller tid.** Filstorlekar, exporttider och hur de

### M-155_vad_som_oppnas_hos_tillverkaren.md — §5 — Vad som skulle krävas för att flytta varje OPRÖVAT till KÖRD

* 

### M-155_vad_som_oppnas_hos_tillverkaren.md — LIMITS — vad den här mätningen INTE visar

* Ingen kommersiell PLC-IDE kördes.** Noll av CODESYS, TIA Portal och
* "Öppnas i Beremiz laddare" är inte "öppnas i Beremiz".** Se §4, sista
* De negativa Siemens-fynden gäller de hämtade dokumenten**, inte hela
* `M-113`:s HOOPS/FBX-spår rörs inte här.** Den här punkten handlar om
* Ingen av tillverkarnas dokumentation anger vilken PLCopen-version de
* Ingen fil har gått **från** ett tillverkarverktyg **till** oss.** Vår
* Sökningen är en frånvaromätning.** Att en riktad sökning på

### M-156_specen_60_plc_mot_koden.md — LIMITS — vad den här inventeringen INTE visar

* Den mäter ingenting.** Inget prov kördes, ingen siffra producerades. Att en
* inte** att koden är riktig, prövad eller körd. Flera av de 26 vilar på
* Frånvaro av träff är inte frånvaro av kod.** De fyra ouppfyllda bygger på
* Meningsräkningen är min bedömning.** "31 meningar som påstår något om
* Avsnittet "Vad som inte är prövat" (rad 146-152) granskades inte.** Det är
* Ingen av de fyra ouppfyllda är lagad.** Inventeringen är listan, inte
* Bara `60_plc.md`.** `61_st_generering.md`, som rad 96 hänvisar till, är

### M-157_ren_maskin_hela_kedjan.md — LIMITS

* Visual Components kördes inte:** En ren Ubuntu-container kan inte köra Visual Components utan ett Wine-prefix och licensserver.
* Verktygskedjans fulla nedladdning (30 MB) kördes med `--lista`:** Full hämtning av binärerna prövas i M-56 och testas lokalt; i containern kördes endast manifest- och sha256-kontrollen för att spara disk och nätkvot.

### M-158_den_riktiga_f15_mutationen.md — LIMITS

* Körningen mäter spårdomaren mot vår ST-tolk.** A2:s OpenPLC-domare kör
* Den sista överlevaren i S-05 rad 39 är inte ekvivalent.** Den är observerbar
* Banken rör sig vidare.** Fler uppgifter från kö B förskjuter nämnaren ytterligare.

### M-159_larmet_tidsvakten_och_forreglingen.md — LIMITS

* Inkopplingen i kedjan är villkorad, och det är ett val.** `granska_station`
* Ingen modellkörning.** Grinden är prövad mot referenser, mutationer och
* Bara 56 av 254 deklarerade förreglingar döms.** Resten lämnas åt
* 115 obundna väntelägen döms inte.** Grinden ser dem och rapporterar dem;
* Regel 2 missar ett larm som latchas inne i stegmaskinen.** Kravet "utanför
* Feltillståndets två utlösare är tidsur och analog gräns.** En insignal som
* Larmutgången känns igen på uppgiftens egna ord** — namnet `SYS_ALARM` eller
* Ingen heltalsvärdesanalys.** En stegmaskin i `INT` som styr utgångar direkt
* Klartextparsern läser 50 av 150 interlockrader.** De 100 andra namnger
* De två fällda referenserna är inte rättade.** `bank/uppgifter` är kö B:s yta
* Domen är vår tolks modell av ST, inte OpenPLC:s.** Samma förbehåll som hela
* Antalet referenser växte under mätningen.** 33 vid första körningen, 38 vid

### M-15_skapbara_beteenden.md — Vad som INTE är mätt

* De 80 träffarna är mätta som *"`createBehaviour` returnerade ett objekt"*. Att
* De 164 som ger `None` är mätta som icke-skapbara **med ett argumentlöst anrop**
* Urvalet är de `VC_*`-konstanter som fanns i **skriptets** scope. Konstanter som
* Metodfelet är rättat för heltalsfiltret. Att det **nya** urvalet är komplett är
* Att svepet dödade bryggan i nästa körning står som omätt orsak. Mätningen
* `VC_TRANSPORT` som kandidat till `Ref<ComponentProcessor>` är märkt oprövad i
* Python-typen i högerkolumnen är läst av typnamnet på det returnerade objektet.

### M-160_f1_modellen_skriver_linan.md — 4. Vad som INTE är mätt

* Ingenting om en modell.** Ingen modellslinga har körts. Riggen är
* Ingenting genom VC.** `Ogonsteg`:s dyra väg — VC-omstart, uppladdning till
* Grind 4 (anropsvalidering) i ögonsteget.** Att den passerar med M-74:s
* Kostnaden per körning.** `Forfattare` summerar transportens kostnad, men
* Vilken modell.** Rättelsen 2026-09-05 16:25 gäller: modellnamnet skrivs i
* Att kompositionsfallen faller i den här riggens uppställning.** M-74 fällde
* F2:s klassning.** Varje misslyckat reparationsvarv ska klassas i "ögat sa

### M-160_f1_modellen_skriver_linan.md — LIMITS

* Riggen är **byggd och prövad, inte körd**. Allt i §3 är prövat utan modell
* Den dyra vägen (VC, OpenPLC, ögat) är oprövad i den här riggen. Den är
* Torrkörningens ögondomar är **inspelade**. De bevisar att räkningen,
* Ingen modell är vald, så inget tal här hör till någon modell.
* Ingenting om fler än två stationer, om längre körningar, eller om scenen

### M-161_komponentsoket_tva_hal.md — LIMITS

* Mätningen gäller bibliotekets 3 201 komponenter i VC 4.10 på denna maskin.
* 60 av de 75 frågorna bär antagna namn utan motsvarande tillverkarbeteckning.
* Sökningen provar statisk namnnormalisering och ersätter inte semantisk förståelse.

### M-162_fritext_om_befintlig_scen.md — LIMITS

* Skriv vad mätningen INTE visar. En mätning utan det här avsnittet fälls av

### M-163_forslag_nar_valet_faller.md — LIMITS

* Skriv vad mätningen INTE visar. En mätning utan det här avsnittet fälls av

### M-164_baslinjens_golv_i_skala.md — LIMITS

* Båda hypoteserna prövades på samma 44 uppgifter som gav upphov till dem.**
* Baslinjen körs bara på `NIVA_SPEC`.** `NIVA_MAGER` och `NIVA_PROSA` är
* `uppfyllda` är ett antal, inte vilka.** Två domar med samma antal kan
* Ingen tredje hypotes prövades.** Jag stannade vid två för att en tredje
* De 17 nya uppgifternas facit skrevs av en annan session samma dag**, och de

### M-16_canconnect_dodar_pumpen.md — Vad som INTE är mätt

* Slutsatsen i rubriken är motbevisad i M-37.** Orsaken var inte anropet utan
* Fyndet vilar på **en** körning, ett par komponenter, en bindning. Ingen
* Vilket av de två möjliga sluten som inträffade — dödad tasklet eller ett anrop
* Den generella följdsatsen *"ett läsande verktyg kan döda bryggan"* är dragen ur
* Punkt 2 i *Vad som ändras* är inte genomförd: `skrivgrind.DODANDE_ANROP` är
* Punkt 1 — att `can_connect` och `connect` inte får anropas mot ett gränssnitt
* Byggkedjans sex gröna steg är mätta en gång var, i samma körning som slutade

### M-20_plcbandet.md — 9. Vad som inte är mätt

* Visual Components.** Fas 6:s grind i `70_faser.md` heter "handskriven ST
* PLC-halvan** av bandet, från OPC UA-klient till scancykel och tillbaka.
* Windows.** Allt ovan är Linux (I17).
* Fler än två signaler.** Provstationen har en in och en ut. Hur
* Säkerhetslägen i OPC UA.** Bara `None/None` med anonym åtkomst är körd.
* Belastning.** Ingen mätning gjordes med samtidig trafik, och maskinen körde

### M-31_lintern_var_sjalv_en_falsk_gron.md — Vad som INTE är mätt

* Talet 125 kommer ur den ombyggda lintern, och den var inte prövad mot ett
* Vad som **räknas** som en tröskelkonstant är linterns egen definition. Ett tal
* Lintern kontrollerar att en hänvisad mätning **finns**. Att mätningen faktiskt
* Talen 79 och 67 är båda mätta med den **nya** lintern. Ingen av dem går att
* Vilka av de 125 trösklarna som är **fel** är inte mätt. Mätningen räknar
* De 27 döda hänvisningarna är räknade en gång. Att ingen ny död hänvisning kan

### M-32_mataren_och_komponentidentiteten.md — Vad som INTE är mätt

* Punkt 6 är fel, och rättelsen står bara som en ruta ovanför slutsatsen.**
* Talet *"72 simulerade sekunder → 0 produkter"* är mätt på en matare byggd i en
* redan körande** simulering. M-40 mätte att just det gör att en matare aldrig
* Att en programmatiskt skapad komponent saknar identitet är mätt för
* "En URI överlever inte en layoutrunda"* är mätt för **en** fil utanför en känd
* Hela bygg–spara–ladda-omvägen visade sig senare vara onödig: M-40 mätte att
* De två uppstartsluckorna (`vc_assist_startlayout.txt`,
* De två uppstartsfelen (dubbel pump ur en sparad layout, `__future__`-flaggor

### M-33_varldsenheten_ar_millimeter.md — Vad som INTE är mätt

* Kopplingen mellan enhetstabellen och `vcMatrix.P` görs via **en** kropp — en
* `findUnitFamily` gav `None` på varje prövat namn. Det är en frånvaro i en
* gissad namnlista**, inte en mätning av att familjen saknas — exakt samma form
* `vcMotionPath.Speed = 200.0` är ett **rimlighetsargument**, inte en mätning.
* Tyngdaccelerationens enhet är fortfarande omätt.** Texten lämnar frågan öppen,
* Bekräftelse mot ett objekt av **känd fysisk storlek ur en katalog** står som
* Att ändringen av cellernas mått till millimeter gör de fyra grindarna
* Mätt mot VC Premium 4.10. Att basenheten är densamma i andra VC-versioner, och

### M-34_produkten_finns_men_flodar_inte.md — Vad som INTE är mätt

* Varje rad i tabellen är **en** observation ur ett svep, inte en upprepad
* "Fyrar den automatiska matningen? **Nej**"* är mätt över 160 simulerade
* Slutsatsen i *Var det står* — att en bana kräver en transportstyrenhet, och att
* `testCapacity = False` på båda sidor även under drift står som *"betydelsen är
* Mätfelet är rättat för `len(app.Components)`. Var det talet användes på andra
* De fyra transportstyrenheterna prövades med ett argumentlöst `createBehaviour`,
* Att `VC_PYTHONTRANSPORTCONTROLLER` skapades *"utan att bryggan dog"* är mätt en

### M-35_kollisionsdetektorn_fyrar_inte.md — Vad som INTE är mätt

* Rätt observation, fel diagnos.** M-36 mätte orsaken: `NodeListA` tar emot en
* Hypotesen under *Trolig orsak, omätt* — att detektorn måste ligga i layouten —
* De fyra gröna layouterna mäter att fyra scener gick att **bygga**. De mäter
* Det trasiga fallet är **två kuber**, en uppställning, en förskjutning. Att
* `StopOnCollision`-fyndet gäller det objekt `sim.newCollisionDetector()`
* Att fasen står öppen *"på en mätt orsak"* stämde inte när det skrevs: orsaken

### M-36_measuredistance_ar_kollisionsmattet.md — Vad som INTE är mätt

* Måtten är tagna på **två axelinriktade kuber** som förskjuts längs **en** axel,
* Facit är räknat ur de positioner mätningen själv satte, och förutsätter M-33:s
* Måttet är mättat vid noll.** `0.0` betyder både "kant i kant" och "900 mm
* Uppdateringsreceptet `nod.update()` + `sim.update()` är mätt som nödvändigt
* tillsammans**. Vilket av de två anropen som gör jobbet, eller om båda behövs,
* Att de tre avfärdade vägarna (layoutpost, läsning efter ett simuleringssteg,
* Ombyggnaden av ögats `mindist`-provtagning från detektorn till `measureDistance`

### M-37_granssnitt_gar_att_koppla.md — Vad som INTE är mätt

* Receptet binder `Container`, `Port` och `PortName` i en loop över
* Receptet är kört **en gång**, på ett par komponenter byggda i samma körning.
* Kopplingen är mätt till `canConnect True`, `connect True`, `IsConnected True`.
* Rättelsen av M-16 pekar ut den ogiltiga bindningen som orsak. Det är slutet ur
* Kontaktvalet på `Type` i stället för index ärvs från M-17 och prövas inte om
* Att fas 5:s tredje led därmed *"är möjligt att uppfylla"* är en slutsats om

### M-38_vagen_mellan_plc_och_scen.md — Vad som inte är avgjort

* Om VC:s inbyggda koppling går att få in via en **sparad layout** som redan
* Om 80 ms räcker. Det beror på vad som ska styras: en transportör med 200 mm/s
* Ögats krav att PLC-värden ligger på **samma tidsaxel** som fysiken. Med två

### M-39_slingan_sluten.md — Vad som INTE är prövat

* Bara två signaler.** En verklig station har tiotals, och kopplarens varv
* Ingen rörelse i scenen.** Donet är en boolesk signal, inte en transportör
* Ingen tidsstämpling till ögat.** Kopplaren mäter sina egna led, men skjuter
* Windows.**

### M-40_varfor_mataren_aldrig_fyrade.md — Vad som INTE är mätt

* De tre linjerna är byggda och mätta **en gång** var, i ett startskript, i samma
* Villkoren är mätta som **nödvändiga**, ett i taget utelämnat. Att de tre
* Fönstren är korta. M41A mättes över 9,8 → 37,8 simulerade sekunder, alltså sju
* Att en bruten koppling **inte** går att laga under drift är mätt i ett fall:
* Det fjärde fallet (samma linje byggd i en körande simulering) är mätt **en**
* Bland de fyra motbevisade påståendena bärs ett av en parentes utan mätrad:
* "`Part` fungerar också — sätter man `Part` till en `.vcmd`-URI sätts
* Förklaringen till `create()`:s `None` — att den prövar sin egen behållares
* Ändringarna i `svc/vc_assist_svc/byggrecept/recept.py` provas av
* `DistanceTolerance = 1e9` avfärdar avståndet som orsak i **det** provet. Vilken

### M-41_produkten_flodar.md — Vad som inte är visat

* Produkten lämnar aldrig banan till något annat.** Banans utgångs­gränssnitt
* oprövat**.
* Inget skript, ingen station, ingen process.** Linjen är matare + bana. Det
* `Accumulate = True` är satt men aldrig belastad.** Ingen produkt har blivit
* Rörelsen är mätt i simulerad tid, inte i väggklockstid.** Serien är tagen

### M-42_plc_pa_ogats_tidsaxel.md — Vad som ligger utanför d, och som d inte påstår sig mäta

* PLC:ns egen skanfördröjning.** M-20 mätte den till 40,0 ms vid 20 ms
* Riggens brygga är snabbare än VC:s.** Här är tur och retur 5,2 ms median;

### M-42_plc_pa_ogats_tidsaxel.md — Vad som INTE är mätt

* Mot en levande VC.** Riggen mäter mekanismen, inte produktionsvägen.
* Epokfrågan är kringgången, inte besvarad.** Om VC:s `time.time()` under
* Flera kopplare mot samma öga.** Det sista inskottet vinner; ingen
* Windows.**

### M-44_windows_oprovat.md — Vad rättelserna medvetet INTE gör

* De ändrar **ingenting** i Wine-vägen. `valj_adressflagga` ger Wine samma
* De påstår inte att Windows fungerar. Varje ny gren är prövad som **gren**,
* 

### M-45_bankens_tackning.md — 8. Vad som INTE är prövat

* Ingen uppgift är körd i VC.** `last_run` är `null` för 51 av 51, och
* Ingen uppgift är körd i OpenPLC.** Tolken och runtimen är inte jämförda.
* Ingen uppgift är kompilerad av STruC++.** Referenslösningarna går genom
* 47 av 51 uppgifter har fortfarande inget spårfacit.** De fyra nya är ett
* Spårfacit är boolesk och heltalig logik.** Det finns ingen fysik i det:
* Referenslösningarna är skrivna av mig.** De bevisar att facit är uppfyllbart.
* Ingen baslinje.** `docs/spec/83_scenarier.md` kräver samma uppgifter körda
* Inget tal härifrån får jämföras med ett publicerat tal.** Nämnarna i fältet
* 

### M-46_harnessens_hardhet.md — 4. Fynd jag INTE hann bevisa — obevisade, behandla som gissningar

* OBEVISAT 1 — `text._monster` cachar på `id(markorer)`.** `text.py:137`
* OBEVISAT 2 — `_pumpvarningar` är en VARNING där M-13 säger död.**
* OBEVISAT 3 — `MAX_LIKA_ANROP = 2` mot VRK-008.** Regeln säger *"Upprepa
* OBEVISAT 4 — `test_harnessen_oppnar_ingen_socket` är textbaserat.** Den
* 

### M-47_verktygstackning_runda_1.md — Vad de här måtten INTE säger

* Att en symbol står i byggd kod betyder att en mall **nämner** den, inte att
* Ytdiffen ser bara de symboler `47` valde att namnge. Den mäter täckningen av
* planen**, inte av API:t.
* Steg-täckningen ärver `48`:s kolumn "Kräver". Där den namnger fel yta blir
* 

### M-48_grind_1_till_4_skarpt.md — Vad som INTE är mätt

* Ögat.** Grind 5 ingår inte. T3–T6 i protokollet kan inte prövas förrän
* Driftsättning.** CLI-vägen svarar bara på *går den att bygga?*. Den skriver
* Reproducerbarhet.** STruC++ ligger i en sessionskatalog, inte i repot, och
* Flera stationer.** En station, tre trasiga fall.

### M-49_stationen_arbetar.md — Vad som INTE är visat

* Nödstoppet.** Den skyddade ingången kan inte drivas från kopplaren och står
* Fasförhållandet mellan PLC-taggen och scenens signal.** Det kräver
* Nödstoppet igen:** att ST-koden gör rätt när `nodstopp` går hög är oprövat,
* Fler än en station.** Fas 8.
* Hur ofta det lyckas.** Ett grönt varv är inte en frekvens. Fas 9.
* Windows.**

### M-50_de_trasiga_fallen.md — Vad som INTE är prövat

* Att en modell skriver kropparna.** Alla sex är handskrivna. Fas 7 påstår
* Reparationsvarv.** Protokollet ber om antalet, och det är noll här av
* Nödstoppet.** `nodstopp` går inte att driva över OPC UA (M-49) och stod
* Fler trasiga fall än fem.** Felklasserna i protokollet är slut, men

### M-51_svepet_over_st_lagret.md — Vad som INTE är mätt

* Runtime-semantiken.** Svepet frågar *går det att bygga?*, aldrig *gör det
* Tolken.** `tolk.py` fick `**`, därför att en operator som validatorn
* Reproducerbarhet.** STruC++ ligger fortfarande i en sessionskatalog och inte
* Andra kompilatorer.** MATIEC/OpenPLC är inte svepta. Där kedjan skiljer sig

### M-53_fran_bedd_till_grind.md — 5. M-46:s fyra obevisade fynd

* Varför M-46 misslyckades är själva lärdomen:** försöket använde
* tupelliteraler**. En literal ligger i funktionens `co_consts` och frigörs
* anropet efter en pumpdödare körs inte alls** sedan `efter_sparning`.
* 

### M-54_tolken_mot_strucpp.md — Vad detta INTE bevisar

* Det är inte OpenPLC.** Oraklet är STruC++:s egen runtime. Två motorer som
* Tio konstruktioner är inte ST.** Svepet täcker det bankens facit lutar sig
* Ingenting om drift.** Scancykelns kanter i en riktig anläggning,

### M-55_export_till_usd_och_urdf.md — Vad som INTE är mätt

* Om GUI:t kan exportera** något av formaten via en insticksmodul. Sannolikt,
* Hur väl en egen exportör faktiskt skulle fungera.** Ovanstående säger att
* Vad `PolygonTable` innehåller i praktiken.** Symbolen finns; formen på
* Om VC 5.0 ändrar något.** Hela mätningen gäller 4.10.

### M-56_verktygskedjan_i_repot.md — Vad som INTE är mätt

* Att hämtningen fungerar på Windows eller macOS.** Manifestet har posterna;
* Att OpenPLC-digesten går att dra på en ren maskin.** Avbilden finns lokalt
* Node självt är inte fastspikat.** Kedjan kräver `node` på maskinen och
* Låsfilen är granskad en gång, av mig.** 478 poster är fler än någon läser

### M-57_biblioteket_fanns_hela_tiden.md — Vad som INTE är gjort

* Katalogverktygen använder fortfarande de 65 handskrivna posterna.** Indexet
* Ingen komponent ur biblioteket är laddad i VC.** Att filen finns och går att
* Gränssnitten är inte lästa.** Indexet räknar `rSimInterface`-förekomster
* Layoutlösaren har fortfarande aldrig sett en riktig komponent.**

### M-58_var_metadatan_ligger.md — Vad som INTE är mätt

* Om katalognamn och `Category` någonsin skiljer sig.** Att jämföra dem över
* Om `Name` någonsin ligger efter byte 181.** 300 av 3201 är ett stickprov.

### M-59_databladets_tackning.md — 12. Vad som INTE är mätt

* De 506 `rPythonKinematics`-robotarnas räckvidd.** Måtten finns i
* Om den valda räckviddsformeln håller för de 846 ledade armar som inte har
* `Advanced::ConveyorCapacity` = 9999.** Värdet ser ut som en sentinel för
* Ingen komponent är laddad i VC.** Att fälten går att läsa ur filen är inte
* Gränssnittens typer och riktningar.** Databladet ger namnen och skiljer

### M-60_vad_ett_katalogsvar_kostar.md — Vad som INTE är mätt

* Tokens, inte tecken.** Alla tal ovan är tecken. En tokenräknare för den
* Om tio rader räcker.** `MAX_RADER = 10` är satt på kostnad, inte på hur ofta
* Rangordningen.** Träffar sorteras på kortast namn först, vilket är rätt för
* "IRB 120"* mot *"IRB 120-3/0.6 LID"*. Om det är rätt regel i allmänhet är

### M-61_vad_en_komponentfil_bar.md — Vad som INTE är mätt

* Om `get_bounds` täcker hela komponenten.** Verktyget läser rotnodens
* Om en katalogkomponent alls går att ladda.** `app.load()` mot en `.vcmx` är
* Om lådan beror på ställningen och på parametrarna.** Sannolikt ja för båda,
* Om VC:s gränssnittsnamn är samma som filens.** Läsningen här är oprövad mot
* De 75 flödesfälten med port 2–6.**
* De 36 profiler som inte är snitt utan 3D-höljen.** Radien är största
* Vad en `Custom`-led är.** Den är den vanligaste ledtypen, 13 806 av
* Den sammansatta lådan för de 140 komponenter vars geometri har en helt
* Om `Name` någonsin ligger efter byte 181** — M-58:s öppna rad står kvar,
* Vilken av de fyra läsningarna av "kategori" som en agent ska få.** Den här
* Om delsträngssökningen efter familjemarkörer förblir ofarlig.** Noll
* Tre tolkare av samma format.** `datablad.py` läser rotens variabelrymd med

### M-62_baslinjen.md — 12. Vad som INTE är prövat

* Ingen språkmodell kördes.** Paret i avsnitt 1 är baslinjen mot sig själv på
* 33 av 37 genereringsuppgifter har inget spårfacit.** För dem säger
* Ingen uppgift är körd i VC.** Ögat har inte sett en enda av de 37
* Ingen uppgift är körd i OpenPLC.** Tolken och runtimen är fortfarande inte
* Grind 4 är inte körd, 0 av 37.** Baslinjen skriver ingen scenkod. En
* Grammatiken är skriven av mig, mot bankens egna rader.** Att den läser 134
* `mager` och `prosa` är svagare än de behöver vara.** En bättre I/O-listnivå
* Ablationen prövar fyra varianter, inte alla.** Att `S-05` klarar sig utan
* Reparationstabellen har två poster därför att bara två grindkoder pekar ut
* Tidsmätningen är tre körningar per nivå** på en maskin som samtidigt kör
* Orakeljämförelsen är mot STruC++, inte mot OpenPLC.** Noll avvikelser över
* Ablationen och kalibreringen körs bara på de fyra uppgifter som har
* Ingen mätning av vad baslinjen gör med en uppgift utanför banken.**
* 

### M-63_planeringslagret_matt_mot_sin_spec.md — 9. Vad den här mätningen INTE visar

* Att planen bygger rätt cell.** Grinden mäter att planen håller
* Att koordinaterna går att köra.** Layoutmotorn lämnar ut koordinater bara när
* Att textläsningen förstår svenska.** `lasning.py` läser slutna mönster.
* Att processlistan täcker en verklig cell.** `PROCESSORD` är 28 ord. En process
* Att `INGEN_MOTSAGELSE_FUNNEN` betyder att layouten går.** Det betyder att just
* Att rasterstegen är rätt.** Tre steg är mätta över 81 körningar i **en**
* Att bankvägen och fritextvägen ger samma detaljering.** De döms av samma
* Att samtalet håller för en riktig operatör.** Två turer räcker i provet, med
* inte mätt**, och det är samma oprövade yta som textläsningen — bara ett steg
* Att `get_transform` svarar med exakt de tal `set_transform` fick.**
* Att felen jag inte letade efter inte finns.** Mätningen jämförde spec mot kod.
* 

### M-64_vad_anvandaren_ser_medan_det_arbetar.md — 6. Vad systemet inte vet, i två klasser

* Utanför räckvidd**, fem poster, ordagrant efter `50_grindar.md`:
* Ej prövat i den här körningen**, hämtat ur källornas egna skäl:
* stationsgrindens överhoppade grindar, med grindens eget skäl (`ej kord;
* reparationsslingans `ej_korda`
* ögonkopplingens fyra utfall ur `M-42` — inskott till ett stängt öga, värden
* ögats saknade sektioner, härledda ur domen
* steg som aldrig kördes, och — skilt från dem — steg som **påbörjades men
* 

### M-64_vad_anvandaren_ser_medan_det_arbetar.md — 9. Vad detta INTE bevisar

* Ingen VC kördes.** Inget i den här mätningen har varit i närheten av
* Ingen språkmodell kördes.** Reparationsslingan drivs av en manusmodell.
* Ingen operatör har läst ytan.** Att texten är läsbar är min bedömning,
* Tystnadstaket är inte mätt.** 5 s kommer ur specen och specen kallar det
* `MAX_HANDELSERADER = 12` är vald mot teckenkostnaden, inte mot
* Ytan är inte trådsäker och har ingen processgräns.** `Forlopp` förs av
* De fem posterna utanför räckvidd är en avskrift, inte en mätning.** De
* Grinden ser inte ett protokoll som ljuger.** Den dömer texten mot
* Fält 1 och 7 finns inte.** Samtalet och systemläget kräver en levande
* Ingenting driver ytan än.** Den går att driva, och det är en annan sak än

### M-65_ogat_pa_djupet.md — Vad som INTE är mätt

* Ingenting är kört i VC.** Allt här är fixturer, syntetiska serier och
* Ögat är felfinnande, aldrig bevis.** Sensorstuds, ställdonsdynamik,
* Hopfogningens osäkerhet täcker inte PLC:ns egen skanfördröjning** (40 ms,
* Hopfogningen är mätt mot M-42:s rigg, inte mot VC:s brygga.** Riggens
* Upplösningsformeln är prövad mot slumpen, inte mot en verklig kopplare.**
* Läsintervallet är det ögat ser, inte kopplarens verkliga.** Läser
* `measureDistance` under en körande simulering** är oprövat: M-36 mätte
* Fem domare mot VC-byggda celler** (P15-8) är oprövat. Matrisen är mätt
* `aldrig_gripen` fälls av två skikt.** Grepp-domaren och kontraktets
* 35 av ögats 49 konstanter är fortfarande PRELIMINÄRA** (M-10, M-18, M-19).
* `41_ogat_kontrakt.md` beskriver v1** medan koden talar v2. Förslaget står
* Windows.**

### M-67_kopplingen_ar_logisk.md — Vad som INTE är visat

* Andra gränssnittstyper.** Provet använder `VC_ONETOONEINTERFACE` med ett
* Ett satt `DistanceTolerance`.** Avståndets roll är mätt bara vid förvalet.
* Vad som händer vid `disconnect()`.** Provet kopplar och river komponenterna;
* Om en produkt faktiskt går över kopplingen.** M-41 mätte flödet, men på en

### M-68_kod_utan_prov.md — Vad som INTE är mätt

* Om proven faktiskt provar något.** Kriteriet är grovt: nämns modulens
* Om de fem utan prov är farliga.** Radantal är inte risk. `layoutport.py` kan
* Protokollkörningarna själva.** Ingen av dem har prov, och det är rimligt —

### M-69_tre_svar_pa_hur_manga_robotar.md — Vad som INTE är mätt

* 699 komponenter har ingen familjemarkör alls.** De är varken robot,
* Om markörlistan är fullständig.** Sju markörer, tagna ur M-59. En komponent
* Ordningen mellan markörerna är oprövad.** Noll av 3201 bär både en
* Om `Category`-fältet någonsin är sannare än strukturen.** Antaget nej, inte

### M-70_arlighetsskulden_betald.md — Vad som INTE är mätt

* Om punkterna jag skrev är sanna.** 150 påståenden om vad 22 mätningar inte
* Om listan är komplett.** Jag skrev de hål jag såg. En mätning kan bära fler,
* De två mönstren jämförs på ett träd, inte på en mängd rubriker med känt
* Fyra ord är en gissning.** Grenen `vad ... inte` tillåter upp till fyra ord
* M-50 är kvar och är inte min.** Den är en halvskriven mätning
* Taket är satt i ett rörligt repo.** `UTAN_ARLIGHETSAVSNITT = 1` är exakt lika
* Ingenting är mätt i VC.** Hela det här arbetet är textarbete på disk. Ingen
* Sviten är grön, men inte stilla.** Mitt i arbetet var två prov röda och inte

### M-71_ren_maskin_utan_vc.md — Vad som fortfarande INTE är prövat

* Att VC startar med det installationen lade dit.** Det är fas 10:s enda
* Windows och macOS.** Manifestet bär posterna; ingen har kört dem. M-44 har
* En maskin utan node.** Kedjan kräver `node` och använder det som finns
* En maskin utan nät.** Hämtningen förutsätter åtkomst till GitHub och npm.
* En maskin utan docker.** OpenPLC-avbilden dras av docker, inte av oss.
* Klonen är lokal.** `git clone --local` från samma disk, inte över nätet.

### M-72_kvaternionens_ordning_pa_tre_axlar.md — Vad som INTE är mätt

* Bara rena rotationer.** Tre enaxliga fall. En sammansatt rotation kring två
* Inget tecken är prövat mot en känd riktning.** Provet visar vilken
* Bara `getQuaternion()`.** `setQuaternion()` är inte prövad, och att läsa
* Bara VC 4.10.**

### M-73_linan_arbetar.md — Vad som INTE är visat

* Fler än två stationer.** Allt här är mätt på två. Att en tredje station
* Att en modell skriver kropparna.** Alla ST-kroppar är handskrivna. Fas 8
* Nödstoppet.** Den `skyddad`-märkta ingången går inte att driva över OPC UA
* Genomströmningsgrinden.** Ögats `genomstromning` läser `vcStatistics`, och
* Långtidsjämvikt.** Serien är 80 s, alltså tio produkter. Att kön på bana 1
* Fasförhållandet PLC ↔ scen.** Kräver `--plc-inskott`, som är av av samma
* Ett objekt i scenen läses aldrig av.** Ögat rapporterar i varje körning
* Windows. Verklig hårdvara. Hur ofta det lyckas.**

### M-74_kompositionsfallen.md — Vad som INTE är visat

* Att listan över kompositionsfelklasser är komplett.** Fem klasser är
* Fler än två stationer.** Att en tredje station inte bär en klass av fel som
* Att felen fälls i en scen som inte är den här.** Fixturerna är fällda på
* en** lina, med **en** geometri och **en** takt. Takten är dessutom vald så
* Att en modell skriver kropparna.** Alla sex är handskrivna, och
* Mättnad nedströms som ett eget mått.** `K5` fälls på överlämningens
* Nödstoppet.** Den `skyddad`-märkta ingången går inte att driva över OPC UA
* Windows. Verklig hårdvara. Hur ofta det lyckas.**

### M-75_vad_ett_spar_avslojar.md — Vad som INTE är mätt

* Bara fyra uppgifter**, och alla fyra är våra egna. En riktig anläggnings
* Grenräkningen är statisk.** Den räknar grenar i källan, inte vilka som
* kördes**. Att mäta det kräver en instrumenterad tolk, och den finns inte.
* Ingen rekonstruktion är försökt.** Mätningen säger vad spåret innehåller,
* Inre tillstånd räknas ur ett regex** över referensens `steg`-tilldelningar

### M-76_katalogposten_fanns_hela_tiden.md — Vad som INTE är mätt

* Om de deklarerade fälten är sanna.** De är tillverkarens uppgift om sin egen
* De 645 utan `Reach`.** Vilka de är och varför fältet saknas är inte
* `Description` läses inte.** Den är hundratals ord bruksanvisning per
* `ModelType`, `Author`, `Website`, `Email`, `Modified`** läses inte heller.

### M-77_ett_lofte_utan_namn.md — Vad som INTE är mätt

* Bara `.py`-filer** under `svc/`, `ext/`, `bank/` och `install/`. Löften i
* Bara löften om prov.** Kommentarer som påstår att något är *mätt* utan att
* Om de tre träffarna är alla.** Mönstret är smalt nu, och ett smalt mönster

### M-78_modellen_mot_baslinjen.md — Vad talet INTE säger

* Inte att modeller är sämre än regelmotorer.** Det säger att *den här*
* Inte hur det går efter k varv.** Reparationsslingan finns (`M-52`) men
* Inte ett fel per klass i statistisk mening.** Fyra uppgifter, åtta
* Ingenting om andra modeller, andra promptar eller andra försök.**

### M-78_modellen_mot_baslinjen.md — Vad som INTE är mätt

* Bara de fyra uppgifter som har spårfacit.** Banken har 51.
* Inget reparationsvarv.** Det är den enskilt största luckan: hela poängen med
* Grind 4 kunde inte döma något.** Modellen ombads inte skriva scenkod, så
* Ingen körning i VC.** Domen kommer ur vår egen ST-tolk, korsprövad mot
* En enda modell, en enda prompt.** Formuleringen i uppgiftspaketet kan ha

### M-79_dubbelskrivningen_hade_ratt.md — Vad som INTE är mätt

* Bara fyra referenser.** Bankens 51 uppgifter har inte körts genom grind 2
* Om det finns fler falska röda i regeln.** Skärpningen täcker literaler.
* Om L-05:s referens borde ändras.** Den bryter mot vår egen grind 2, och det

### M-80_fas9_tre_tal.md — Vad talen betyder, och inte

* Oavgjort mot en mallkompilator**, och det ska sägas med de orden — `M-62`

### M-80_fas9_tre_tal.md — Vad som INTE är mätt

* Bara fyra uppgifter.** Banken har 51; fyra har spårfacit.
* n = 1 per uppgift, per varv.** Ingen upprepning, ingen spridning, inget
* Slingan drivs för hand.** Bryggan mellan grind och modell är ett
* Grind 4 dömde ingenting.** Modellen ombads inte skriva scenkod.
* Ingen körning i VC.** Domen kommer ur vår ST-tolk, korsprövad mot STruC++ i
* En modell, en prompt, en formulering.** Uppgiftspaketets ordval kan ha
* Ingenting om svårare uppgifter.** De fyra är de enda med spårfacit, och

### M-81_bankens_scen_provas_aldrig.md — Vad som INTE är mätt

* Om en modell klarar det.** Den här mätningen räknar vad som finns, inte vad
* Om verktygen räcker.** Fyra verktygstyper täcker uppgiften på papperet.
* Om scenerna går att bygga alls.** `fas5_riktiga_komponenter.md` är ett
* inte** står i filen — 0 lästa av 3201. En layout utan lådor är svår att
* Kopplingarnas form.** 196 kopplingar räknade ur `connections`-fältet; om

### M-82_modellen_uppfann_inga_namn.md — Vad grinden INTE dömde, och det är hälften av frågan

* "Jag är säker på att `load` finns på applikationen, men **inte** säker på att
* "`rotateAbsZ` — jag är säker på att metoden finns; **osäker på enheten**. Jag

### M-82_modellen_uppfann_inga_namn.md — Vad som INTE är mätt

* Om scenerna blir rätt.** Ingenting kördes i VC. Koden är giltig enligt
* Semantiken.** Se ovan: returvärden, enheter och argumentantal.
* Tre scener, en modell, en prompt.** Ingen upprepning.
* Vad som händer utan skrivinstruktionen.** Obestämbara-talet är noll under en
* Kopplingarna.** Modellen valde gränssnitt på namnmönster (`out` hos

### M-83_indexet_svarar_pa_sex_av_sju.md — Vad som INTE är mätt

* Om modellen hade använt verktygen.** Att svaret finns är inte att någon
* Om svaren hade ändrat koden.** Sex frågor besvarade betyder inte sex fel
* Bara sju frågor**, och de är de modellen **valde att nämna**. Vad den var
* Andra enheter än vinklar.** Att indexet saknar enhet för rotationer är mätt;

### M-84_uppslagen_bytte_ordforrad_inte_radantal.md — LIMITS

* Tre scener, en modell, en körning per uppställning.** 13 mot 32 är en stor
* Uppslagsgränserna skiljer sig från den levererade** (40/400 mot 12/12), i
* Domaren dömer att namnet finns, inte att det används rätt.** Returvärden,
* "Rader" räknar icke-tomma rader**, kommentarer inräknade. Fördelningen är
* Ordförrådet är inte kvalitet.** Att röra fler delar av API:t är inte samma

### M-85_komponentdatabladet.md — LIMITS

* Avbildningen rsc-typ → `VC_`-konstant är inte verifierad mot ett kört VC.**
* inte** att `VC_BOOLEANSIGNAL` är den konstant `findBehavioursByType` vill
* Signalordningen är filens, inte API:ets.** För de 310 komponenter som bär
* Ingen komponent har laddats i VC.** Att en egenskap heter `SpeedIn` i filen
* Enheterna är inte lösta, bara ärligt rapporterade.** 86 procent av
* Bryggan bank ↔ bibliotek finns inte.** 11 av 65, noll i de tre scener M-84
* Inget bibliotekstäckande egenskapsnamnindex byggs.** Frågan "vilka
* `vcHelpers.Robot` mot `Robot2` står öppet**, oförändrat sedan M-84.
* Täckningstalen gäller ETT bibliotek** — VC 4.10:s eCatalog-innehåll på den
* Fördelningarna som satte taken mättes med de gamla taken på plats.**

### M-86_ogat_mot_en_korande_vc.md — LIMITS

* En körning, en kväll, en maskin.** Talen i P15-3 har ingen spridning
* Klockan inne i VC kvantiserar till ~1 ms.** Medel ur summan är rätt tal
* Nollan i P15-2 är nollan ned till 1 µm.** Sub-mikrometerdrift, om VC har
* Bara tomma komponenter i P15-2 och P15-3** (utan geometri). Kostnaden för
* `uppdatera_fore_last=False`-svepet** (protokollets separata kostnadsmätning
* `ST8_Mall` rörde sig** i en annan agents scen — det är ett bifynd, inte
* Windows** (fas 13). Allt är mätt under Wine.

### M-87_hopfogningen_mot_vcs_egen_brygga.md — Vad som INTE är mätt

* Ingen riktig PLC.** Kopplarvarvet på 89 ms är M-39:s uppmätta OpenPLC-varv,
* efterliknat** med en väntesats. Ingen OPC UA-läsning gjordes. `las_s` mätt
* PLC:ns egen skanfördröjning (40 ms, M-20)** ligger **före** kopplarens
* Kartans egen osäkerhet är 15–25 ms** och den går inte att göra smalare med
* Regressionen antar att avläsningen sker mitt i sin tur och retur.** Sker
* Taket är inte bevisat täckande.** Ett varv av 900 låg utanför vid 400 ms
* Spridningens övertäckning (2,2× vid p95) är mätt i en driftpunkt**, med
* Rättelsen kan komma för sent.** Den skickas efter att värdet stämplats och
* Bara en maskin, en kväll, en scen.** Turen och returen mättes medan andra
* Windows** (fas 13).
* Flera kopplare mot samma öga** — M-42:s regel gäller fortfarande: sista

### M-88_fem_domare_mot_vc_byggda_celler.md — LIMITS

* PLC-värdena kommer från skriptet, inte från en PLC.** Vägen är den
* P15-7 (fasdom mot en riktig fördröjning i ett VC-skript) är inte kört.**
* Genomflödescellen i VC har ingen process.** Varianten med `State` satt
* Kollisionen är ett ytavstånd på 0,0 mm, inte en detektorträff.**
* Bandrivaren flyttar kropparna i steg om 50 ms** — ingen fysik, inga
* En scen som delas med andra agenter.** `saknade` bar en främmande
* Windows** (fas 13).

### M-89_anlaggningen_utan_kod.md — LIMITS

* Ingen riktig anläggning är inspelad.** Källan är bankens fyra
* informationsinnehållet i en I/O-inspelning*, inte hur en riktig linjes spår
* Fyra uppgifter, och alla fyra är våra egna.** Talen 28/28 och 3/28 har
* Modelledet är n = 1 per uppgift**, precis som fas 9:s. Fyra agenter på
* "Första försöket" är taget efter att jag rättat mitt eget misstag.** Jag
* Förbudet mot att öppna repot är en bön; kontamineringsmåttet är mätningen.**
* Provspårsledets modelltal säger ingenting om en riktig anläggning.** De fyra
* Härledningen ser bara boolska tvåsignalspar.** En förregling över tre
* Provspåret är inte sanningen heller.** "11 av 80 motbevisade" är ett
* undre* tal: de 69 återstående är inte bevisade, bara inte motbevisade av just
* Vilket fönster som är normalproduktion är valt av en människa.** Det är
* Upprepningen är syntetisk.** Produktionsspåret ×10 är samma stimulus tio
* `T3_UTAN_UNDERLAG` går att gå runt.** Kravet på nämnare gäller bara facit som
* Ingen jämförelse mot vägen "läsa uppladdningsformatet".** `70_faser.md`
* Domen är tolkens, inte en runtimes.** Samma förbehåll som hela bänken:
* Två av repots egna grindar är oense om `T#3S`.** Grind 1:s statiska analys
* Skelettets arbetsvariabelfack tar inte startvärden.**

### M-90_ren_maskin_linux.md — LIMITS

* Linux, en distribution, en Pythonversion.** `ubuntu:24.04` med python
* VC startades aldrig.** Fas 10:s kvarvarande öppna punkt — *att VC startar
* Verktygskedjan hämtades inte** i den rena maskinen. Nedladdningarna är
* Provsviten kördes inte** i containern, eftersom `pytest` inte finns där.
* Idempotensen är mätt över två körningar**, inte över en ändrad källa följd

### M-91_windowsregistret_mot_en_riktig_kupa.md — LIMITS

* Ingen omdirigering fanns att mäta.** Den här maskinen har `Documents` på
* Ingenting kördes på Windows.** Kupan lästes som en fil från Linux, med
* `winreg` självt är fortfarande aldrig kört.** Proven matar en attrapp. Att
* Ingen VC på den partitionen**, så ingenting säger något om fas 13:s
* En användare, en Windows-build** (19041, en-US). Säger inget om andra

### M-92_windowssommen_matt_i_stallet_for_last.md — LIMITS

* Ingen Windows-maskin.** Divergensen är mätt mellan två `ntpath` på Linux,
* `%OneDrive%`-rötterna är prövade som logik, inte mot en OneDrive.** Ingen
* Coverage mättes över `tests/enhet`**, inte över protokollsviten. Rader som
* `verktygskedjan.py` ligger på 58 %** och är inte åtgärdad. Den gör
* 2.7-grinden prövar syntax, inte semantik.** En fil som kompilerar i 2.7 kan

### M-93_speglingen_som_inte_aldras.md — 4. LIMITS lyftes dit den läses (Y12)

* 

### M-93_speglingen_som_inte_aldras.md — 8. Vad detta INTE bevisar

* Ingen VC kördes, ingen brygga, ingen språkmodell.** Varje källa provas mot
* Fem av sju rapportytor har fortfarande ingen förare.** Kopplaren,
* Ingen operatör har läst ytan.** Att den är läsbar är min bedömning. Att
* Filen växer utan tak.** 4 000 händelser kostar 403 kB och 6,2 ms per
* Två skrivare mot samma fil är oprövat.** `os.replace` gör varje enskild
* Klockan är väggklockan.** Åldern räknas mot `time.time()`, som kan hoppa
* `TYSTNADSTAK_S = 5,0 s` är fortfarande preliminär** och sätts av M-28.
* Fält 1 och 7 i `26_appen.md` §3** — samtalet och systemläget — finns
* Ingen webbsida är byggd.** Ytan är text, och `26_appen.md` §7 fråga 1 —
* De fem posterna utanför räckvidd är en avskrift**, inte en mätning. De
* Windows är inte kört.** `os.replace` och `tempfile.mkstemp` beter sig

### M-93_speglingen_som_inte_aldras.md — LIMITS

* fem av sju rapportytor har ingen förare** — halva M-64:s hål står kvar,
* ingen riktig körning** har passerat den här koden: ingen VC, ingen brygga,
* ingen människa utanför bygget har läst ytan**, så att den är begriplig är

### M-94_vad_registret_inte_ser.md — LIMITS

* Fynd 1–5 är mätta på grindarnas egen dom, inte mot en körande VC.** Jag har
* Inget av fynd 1–5 och 9 är lagat.** De ligger i grindar som ägs av
* Coverage-talen är en ögonblicksbild kl. 06:05 den 5 september 2026**, tagen
* Coverage mäter körda rader, inte prövade påståenden.** En modul på 100 %
* De två nya spärrarna saknar sin exakthetshalva.** `KOLLIDERANDE_NUMMER` och
* M-90-kollisionen är inte löst av mig.** Båda filerna tillhör andra agenter,
* Ordgränsen i täckningsproxyn ger ett känt falskt utslag**:
* Jag har inte mätt fynd 12:s motsats**: hur många av de 61 markörerna i
* Genomsökningen efter grindar vars fråga tyst ändrats är inte uttömmande.**
* grind*, *domare*, *kontroll*, *verifiering*. `guldgrind.py`,
* Misstanke, inte visad:** `install/upptackt.py` ligger på 57 % täckning och
* Fynd 13:s tal är en ögonblicksbild.** Fyra platshållarfiler fanns kl.
* Misstanke, inte visad:** `NEKANDE`-listan används av minst fyra grindar

### M-95_fyra_grindar_som_matte_fel_storhet.md — Fynd 5 — ett omätt par är inte ett fritt par

* Detta är läst och kört mot mallens kod, inte mot VC.* Koden är en genererad

### M-95_fyra_grindar_som_matte_fel_storhet.md — LIMITS

* Mätt på grindarnas egen dom, inte mot en körande VC.** Det som visas är att
* Fynd 5 är läst, inte kört i VC.** Påståendet vilar på mallens text och på
* `FELORD` fick sammansatta former** (`hittades inte`, `gick inte`, `kan
* `NEGERAD_BESTAMNING` prövas på ordet närmast före felordet**, alltså på
* Marginalen i `stodjer_tal` är oförändrad.** Fynd 3 rör vilken jämförelse
* Bänken skiljer inte på lagningarna.** 56 av 56 både före och efter betyder
* Fynd 2 och 9 ur M-94 ligger utanför.** Skrivgrinden lagades separat, och

### M-96_slingan_kor_sig_sjalv.md — LIMITS

* Fyra uppgifter, en modell, en promptformulering.** 6 av 20 är mätt, inte
* Effekten sitter i en enda uppgift.** S-05 bär fem av de sex lösta. Ett
* Armarna kördes efter varandra, inte parat.** Banken växte emellan (H-05
* T-07 slog i taket och orsaken är inte utredd.** Fyra varv, 0,605 USD, och
* antaget**.
* n = 1 per uppgift och läge.** Ingen upprepning, ingen spridning.
* Fyra uppgifter av 51** — bara de har spårfacit.
* En modell, en promptformulering.** Byts någotdera kan talen bli andra.
* Domen kommer ur vår ST-tolk**, korsprövad mot STruC++ men inte mot OpenPLC.
* Skiftlägessvepet är tretton konstruktioner på lexernivå**, inte hela

### M-97_plc_axelns_giltighet.md — LIMITS

* Störningen är `SIGSTOP` på hela processen** — den stoppar VC:s
* Ingen riktig PLC.** Kopplarvarvet är efterliknat med en väntesats;
* Vad taket täcker under störning** mäts i §5 med klämman, som är trubbig
* Ett tak som ljuger ligger utanför grindens räckvidd** (§1). Grinden är
* Asymmetrin mellan `plc_gammal` och otäckt står kvar.** En enda gammal rad
* `STEP` har ingen INCONCLUSIVE-form** i grammatiken (ovan).
* En maskin, en förmiddag, andra agenter på samma dator.** Två av de fyra
* Windows** (fas 13).

### M-98_den_sjatte_ordlistan.md — LIMITS

* Allt är mätt på grindarnas egen dom, inte mot en körande VC.** Vad som
* `SATSGRANSER` är vald, inte mätt.** Tolv tecken och bindeord, och varje
* Ordningen inom satsen prövas inte.** Ett nekande räknas som att det negerar
* `oga.GODKANNANDEORD` och `oga.BARA_NEGATION_OGA` är kvar som kopior.** De
* `guldgrind.DALIGA_ORD` mot `oga_kontrakt._FYNDORD` är inte lagad.** Att de
* Spärren ser bara moduldeklarerade literaler.** En ordlista byggd inne i en
* Spärrens kärnor är `text.py`:s två.** En lista som blandar två *andra*
* Kopiekriteriet missar en drivande kopia som är kortare än sex ord och har
* Bänken har fortfarande ingen fälla av "ett nekande någon annanstans"-slaget
* Tröskellintern är röd av annat, och det är mätt vems.**
* De tio andra röda är också andras, och namngivna.**
* Sju konsumenter är alla jag hittade, inte alla som finns.** Sökningen gick

### M-99_differentialsvepet_mot_kompilatorn.md — LIMITS

* Facit är STruC++ v0.6.6, inte standarden.** Kompilatorn är varken en
* Ordalydelsen i standarden är inte verifierad mot en fysisk utgåva** för
* OpenPLC är fortfarande oprövad.** Kedjan dit kräver ett npm-paket som inte
* Fuzzen mäter EN invariant** — att `validera` lämnar en `Rapport` — inte att
* Satsnästling är oskyddad.** Mätt: 326 nästlade `IF` innan RecursionError
* Tre falska rödgrindar står kvar** (fältinitieraren i två former,
* Grannfallen är prövade per lagning, inte uttömmande.** `T#5X` och `T#5S10M`
* Talet 394 är konstruktioner, inte täckning.** Axlarna valdes ur M-96:s

## Produktionsmoduler som ingen provfil nämner: 0 (0 rader)


## Produktionsmoduler som bara nämns av en L3-körning (kräver VC/OpenPLC, körs inte av `pytest tests/enhet`): 1 (135 rader)

* `svc/vc_assist_svc/plc/opcuakonfig.py` — 135 rader

## Markörer i koden: 145

### vc_assist_svc/processer.py

* vc_assist_svc/processer.py:175  `90_invarianter.md`: operatorens prefix ror vi aldrig med oprovad kod. Den

### vc_assist_svc/harness/efterlevnad.py

* vc_assist_svc/harness/efterlevnad.py:15  grind som SKULLE ha fallt star fortfarande oprovad.

### vc_assist_svc/harness/fallor.py

* vc_assist_svc/harness/fallor.py:24  trasig fixtur ar oprovad (S2 i 96_ingen_skuld.md, och 95_testprotokoll).
* vc_assist_svc/harness/fallor.py:994  "orden 'kvar, och inte lagat': arlighetsgrinden fragade "

### vc_assist_svc/llm/budget.py

* vc_assist_svc/llm/budget.py:16  trimning. En bokforing som bara provas at ena hallet ar oprovad.
* vc_assist_svc/llm/budget.py:72  "PRELIMINAR, M-29: ingen tokenrakning over verkliga turer finns"),
* vc_assist_svc/llm/budget.py:74  "PRELIMINAR, M-29"),
* vc_assist_svc/llm/budget.py:79  "PRELIMINAR, M-29"),
* vc_assist_svc/llm/budget.py:85  "PRELIMINAR, M-29; EDGE och MINDIST vaxer med forloppet"),
* vc_assist_svc/llm/budget.py:87  "PRELIMINAR, M-29"),
* vc_assist_svc/llm/budget.py:89  "PRELIMINAR, M-29"),
* vc_assist_svc/llm/budget.py:96  K_HELA_RESULTAT = 8         # PRELIMINAR, satts av M-29

### vc_assist_svc/llm/matt.py

* vc_assist_svc/llm/matt.py:52  # PRELIMINAR, satt av matning M-28 (adapterprovets punkt 4 i
* vc_assist_svc/llm/matt.py:54  MARGINAL_UPPSKATTAD = 0.05  # PRELIMINAR, satts av M-28

### vc_assist_svc/llm/scenvy.py

* vc_assist_svc/llm/scenvy.py:36  # PRELIMINAR, satts av matning M-29. Motivet ar matt: bankens storsta scen ar
* vc_assist_svc/llm/scenvy.py:40  SCEN_FULL_MAX = 60          # PRELIMINAR, satts av M-29; motivet M-45
* vc_assist_svc/llm/scenvy.py:42  # Samma sak per komponent. PRELIMINAR, matning M-29.
* vc_assist_svc/llm/scenvy.py:43  EGENSKAPER_FULL_MAX = 40    # PRELIMINAR, satts av M-29

### vc_assist_svc/llm/tur.py

* vc_assist_svc/llm/tur.py:328  # Vaggklockan for en hel tur. PRELIMINAR, satts av matning M-28. Vald over
* vc_assist_svc/llm/tur.py:331  VAGGKLOCKA_MAX_S = 180.0    # PRELIMINAR, satts av M-28

### vc_assist_svc/verktyg/formagegrind.py

* vc_assist_svc/verktyg/formagegrind.py:13  finns is None  -> av, "oprovad". Okant behandlas som saknat. Aldrig gissa.
* vc_assist_svc/verktyg/formagegrind.py:89  return False, ("ytan %s ar oprovad (%s) och raknas som saknad"

### vc_assist_svc/verktyg/robotik.py

* vc_assist_svc/verktyg/robotik.py:82  regression. Kvar som en uttalad oppen punkt.

### vc_assist_svc/verktyg/signaler.py

* vc_assist_svc/verktyg/signaler.py:114  list_signal_maps den inte, och det ar en oprovad kant.
* vc_assist_svc/verktyg/signaler.py:130  portmetoder och riktningen ar lasta ur api.xml och oprovade i drift. Att det
* vc_assist_svc/verktyg/signaler.py:133  skrivbordet och oprovad i VC, precis som I17 kraver att det uttalas.

### vc_assist_svc/verktyg/simulering.py

* vc_assist_svc/verktyg/simulering.py:20  tva rader ar dessutom oprovade av ett SKAL som star i kallan sjalv:

### vc_assist_svc/verktyg/utforare.py

* vc_assist_svc/verktyg/utforare.py:40  KO_POLL_S = 0.05            # PRELIMINAR. Satts av matning M-14.
* vc_assist_svc/verktyg/utforare.py:41  KO_TIMEOUT_S = 60.0         # PRELIMINAR. Satts av matning M-14.

### vc_assist_svc/aterhamtning/bild.py

* vc_assist_svc/aterhamtning/bild.py:51  T_PING_S = 3.0      # PRELIMINÄR. 28_lagen_och_aterhamtning.md §1.3, ur M-03.
* vc_assist_svc/aterhamtning/bild.py:52  T_NERE_S = 3.0      # PRELIMINÄR. 28_lagen_och_aterhamtning.md §1.3, ur M-03.
* vc_assist_svc/aterhamtning/bild.py:55  T_MODAL_S = 300.0   # PRELIMINÄR. 26_appen.md A-3, sätts av M-21.

### vc_assist_svc/aterhamtning/yta.py

* vc_assist_svc/aterhamtning/yta.py:50  MAX_AVLASNINGSRADER = 8     # PRELIMINÄR. Samma form som M-64. Satt av M-103.
* vc_assist_svc/aterhamtning/yta.py:138  d, "ingen avläsning gjord; om %s lever är inte prövat" % d,

### vc_assist_svc/plan/korning.py

* vc_assist_svc/plan/korning.py:254  # ut att ha provat nagot den inte provat, och det ar samma

### vc_assist_svc/layout/losare.py

* vc_assist_svc/layout/losare.py:374  oprovade = []
* vc_assist_svc/layout/losare.py:381  oprovade.append(r)
* vc_assist_svc/layout/losare.py:385  return tuple(kvar), tuple(oprovade)
* vc_assist_svc/layout/losare.py:466  konflikt, oprovade = _minimal_konflikt(scen, relationer, ordning, steg_m,
* vc_assist_svc/layout/losare.py:477  if oprovade:
* vc_assist_svc/layout/losare.py:480  % (len(oprovade),
* vc_assist_svc/layout/losare.py:481  ", ".join(r.kod for r in oprovade)))

### vc_assist_svc/forlopp/yta.py

* vc_assist_svc/forlopp/yta.py:56  TYSTNADSTAK_S = 5.0             # PRELIMINÄR. Satts av M-28.

### vc_addon/vc_assist/bridge_cmd.py

* vc_addon/vc_assist/bridge_cmd.py:53  OMSTART_MINSTA_MELLANRUM_S = 0.5    # PRELIMINAR. Satts av matning M-13.
* vc_addon/vc_assist/bridge_cmd.py:387  """Kontrollera VC-version vid start: oprovad version sager ifran (E10)."""
* vc_addon/vc_assist/bridge_cmd.py:398  _log("VARNING (E10): VC-version %s ar OPROVAD. Endast VC 4.10 ar matt i det har repot (M-01, M-139). Fortsatter i oprovat lage." % ver)
* vc_addon/vc_assist/bridge_cmd.py:399  return "oprovad"

### vc_addon/vc_assist/formaga.py

* vc_addon/vc_assist/formaga.py:95  oprovade = [y for y, d in ytor.items() if d["finns"] is None]
* vc_addon/vc_assist/formaga.py:99  vc_status = "matt" if str(vc_ver).startswith("4.10") else ("oprovad" if vc_ver else "okand")
* vc_addon/vc_assist/formaga.py:113  "oprovade": len(oprovade),
* vc_addon/vc_assist/formaga.py:116  "oprovade_ytor": sorted(oprovade),

### vc_addon/vc_assist/oga_analys.py

* vc_addon/vc_assist/oga_analys.py:39  GRIP_STABIL_MM = 2.0        # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:40  GRIP_RORELSE_MM = 5.0       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:41  GRIP_FONSTER_S = 0.25       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:42  TELEPORT_MAX_MM = 150.0     # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:43  CARRY_RIGID_DEG = 2.0       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:44  CARRY_MIN_SPAN_S = 0.5      # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:45  PLACE_TOL_MM = 25.0         # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:46  BLOWUP_VMAX_MS = 25.0       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:47  UNDERGROUND_MARGINAL_M = 0.005   # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:48  MIN_PROV = 10               # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:52  SCEN_OLAST_MAX_ANDEL = 0.25      # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:56  GENOMSTROMNING_MARGINAL_S = 0.0  # PRELIMINAR. Satts av matning M-19.

### vc_addon/vc_assist/oga_harledning.py

* vc_addon/vc_assist/oga_harledning.py:32  #   PRELIMINAR + M-nn   ett tal som ska MATAS. Numret star i
* vc_addon/vc_assist/oga_harledning.py:48  STILLA_TOTAL_MM = 1.0           # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:50  ROR_SIG_MM = 0.5                # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:52  SAMTIDIG_FONSTER_S = 0.10       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:56  FART_ANDRING_ANDEL = 0.35       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:59  FART_GOLV_MM_S = 20.0           # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:61  HOJD_ANDRING_MM = 50.0          # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:65  OOMBEDD_MM = 5.0                # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:69  LED_STILLA_DEG_S = 0.5          # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:70  LED_STILLA_MM_S = 0.5           # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:71  LED_GRANS_MARGINAL_DEG = 0.5    # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:72  LED_FOLJFEL_DEG = 1.0           # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:75  SING_LEDFART_DEG_S = 20.0       # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:76  SING_TCP_MM_S = 2.0             # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:77  SING_TCP_DEG_S = 2.0            # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:78  SING_MIN_S = 0.15               # PRELIMINAR. Satts av matning M-18.
* vc_addon/vc_assist/oga_harledning.py:81  SVALT_MIN_S = 1.0               # PRELIMINAR. Satts av matning M-19.
* vc_addon/vc_assist/oga_harledning.py:82  BLOCKERAD_MIN_S = 1.0           # PRELIMINAR. Satts av matning M-19.
* vc_addon/vc_assist/oga_harledning.py:84  FLASKHALS_ANDEL = 0.20          # PRELIMINAR. Satts av matning M-19.
* vc_addon/vc_assist/oga_harledning.py:91  UTSLUNGAD_MS = 3.0              # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:94  UTSLUNGAD_FLYG_MS = 1.5         # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:96  FRITT_FALL_TOL = 0.35           # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_harledning.py:1314  avhuggen sista cykel ar inte ett brott - den ar oprovad, och de tva far

### vc_addon/vc_assist/oga_provtagning.py

* vc_addon/vc_assist/oga_provtagning.py:29  SKRIV_VAR_N_RAD = 100       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_provtagning.py:57  PLC_FARSK_S = 0.25          # PRELIMINAR. Satts av matning M-19.

### vc_addon/vc_assist/plats.py

* vc_addon/vc_assist/plats.py:37  # Miljovariabler som slar all harledning. Finns for att en oprovad plattform

### vc_addon/vc_assist/pump.py

* vc_addon/vc_assist/pump.py:51  AKTIV_FONSTER_S = 2.0      # PRELIMINAR. Satts av matning M-26.
* vc_addon/vc_assist/pump.py:56  OMSTART_MINSTA_MELLANRUM_S = 1.0    # PRELIMINAR. Satts av matning M-13.
* vc_addon/vc_assist/pump.py:57  OMSTART_TAK_PER_MINUT = 20          # PRELIMINAR. Satts av matning M-13.
* vc_addon/vc_assist/pump.py:247  self.logg("formaga: %d av %d ytor finns, %d saknas, %d oprovade"
* vc_addon/vc_assist/pump.py:248  % (sm["finns"], sm["provade"], sm["saknas"], sm["oprovade"]))

### installera.py

* installera.py:56  return ("OPROVAD SOKVAG: %s + %s ar inte kord av oss. Kontrollera att "

### upptackt.py

* upptackt.py:93  # oprovad. ntpath.expandvars gor Windows-expansionen pa bada

### schema.py

* schema.py:835  # domaren måste fälla. Utan minst ett per spårfacit är grinden oprovad (regel

### enhet/test_api_index.py

* enhet/test_api_index.py:604  """docs/spec/95_testprotokoll.md: en grind utan trasig fixtur ar oprovad."""

### enhet/test_bestallning.py

* enhet/test_bestallning.py:14  slapper igenom det korrekta. En grind som bara provats at ena hallet ar oprovad
* enhet/test_bestallning.py:1170  oprovad - och en oprovad grind ar en forhoppning som har fatt ett namn.
* enhet/test_bestallning.py:1880  # (M-68 raknade den som helt oprovad.)

### enhet/test_dataverktyg.py

* enhet/test_dataverktyg.py:13  aldrig fallit ar oprovad (docs/spec/95_testprotokoll.md).

### enhet/test_formaga.py

* enhet/test_formaga.py:50  assert s["finns"] + s["saknas"] + s["oprovade"] == s["provade"] == len(F.YTOR)

### enhet/test_harness.py

* enhet/test_harness.py:964  """S8: ingen TODO utan datum och ägare. Formen är TODO(datum, fas)."""
* enhet/test_harness.py:970  for markor in ("TODO", "FIXME", "XXX"):

### enhet/test_install.py

* enhet/test_install.py:884  assert "OPROVAD SOKVAG" in ut, "5.0 + Python 3 ar inte kort av oss"

### enhet/test_kontextbudget.py

* enhet/test_kontextbudget.py:12  hallet ar oprovad, och det ar precis sa en tyst trimning overlever.

### enhet/test_layout.py

* enhet/test_layout.py:619  if "TODO" in rad and not re.search(r"TODO\(\d{4}-\d{2}-\d{2}", rad)]
* enhet/test_layout.py:620  assert not bara_todo, "bar TODO i %s: %r" % (fil, bara_todo[:2])

### enhet/test_mekanisering_m53.py

* enhet/test_mekanisering_m53.py:583  """M-46:s 'kvar, och inte lagat'. Foll fore M-53: turen slapptes."""
* enhet/test_mekanisering_m53.py:805  och lat fragan sta oprovad.

### enhet/test_oga_harledning.py

* enhet/test_oga_harledning.py:87  fel.append("%s:%d %s -> %s utan PRELIMINAR" % (rel, nr, namn, L._mnr(r)))

### enhet/test_personatackning.py

* enhet/test_personatackning.py:212  """En felkod utan fixtur ar oprovad - och just den sortens kod ar det

### enhet/test_plan.py

* enhet/test_plan.py:6  som bara provats at ena hallet ar oprovad (docs/spec/95_testprotokoll.md).
* enhet/test_plan.py:652  # fallt ar oprovad (docs/spec/95_testprotokoll.md, regel S2 i 96_ingen_skuld.md).

### enhet/test_plan_villkor.py

* enhet/test_plan_villkor.py:6  hallet ar oprovad (docs/spec/95_testprotokoll.md).
* enhet/test_plan_villkor.py:517  # En grind som aldrig fallt ar oprovad (docs/spec/95_testprotokoll.md).

### enhet/test_plc_industrigrind.py

* enhet/test_plc_industrigrind.py:303  # referens andrar sitt eget spar. Bristen ar rapporterad, inte lagad.

### enhet/test_processer.py

* enhet/test_processer.py:71  """`90_invarianter.md`: operatorens prefix ror vi aldrig med oprovad kod.

### enhet/test_readme_faser.py

* enhet/test_readme_faser.py:114  assert "inte prövat, och det är fasens öppna punkt" not in text.lower()

### enhet/test_scenarbete.py

* enhet/test_scenarbete.py:472  # Stegen är härledda ur mätta grindar; att rundtalet RÄCKER är inte prövat.

### enhet/test_troskelharkomst.py

* enhet/test_troskelharkomst.py:153  fel.append("%s:%d %s -> %s utan PRELIMINAR" % (rel, nr, namn, _mnr(r)))

### enhet/test_vc_start_skarmen.py

* enhet/test_vc_start_skarmen.py:86  """Operatorens eget prefix ~/.wine-vc ror vi aldrig med oprovad kod."""

### enhet/test_vc_versionskontroll.py

* enhet/test_vc_versionskontroll.py:26  """E10: VC 5.0 ska saga oprovad, inte krascha och inte latsas fungera."""
* enhet/test_vc_versionskontroll.py:30  assert rap["vc_version_status"] == "oprovad"
* enhet/test_vc_versionskontroll.py:37  assert rap["vc_version_status"] == "oprovad"

### enhet/test_verktyg.py

* enhet/test_verktyg.py:17  En grind som aldrig fallit ar oprovad.
* enhet/test_verktyg.py:558  assert "oprovad" in u.skal("clone_component")

### enhet/test_verktyg_robotik.py

* enhet/test_verktyg_robotik.py:791  assert "oprovad" in u.skal("add_frame")
* enhet/test_verktyg_robotik.py:1341  ropa pa RSL-slaktens egna metoder, for de ar oprovade och delvis

### enhet/test_verktyg_signaler.py

* enhet/test_verktyg_signaler.py:26  En grind som aldrig fallit ar oprovad.
* enhet/test_verktyg_signaler.py:885  assert "oprovad" in u.skal("signal_inventory")

### enhet/test_verktyg_simmatning.py

* enhet/test_verktyg_simmatning.py:20  En grind som aldrig fallit ar oprovad. Varje trasigt fall nedan bar en
* enhet/test_verktyg_simmatning.py:653  assert "oprovad" in u.skal("ray_cast")

### enhet/test_verktyg_transport.py

* enhet/test_verktyg_transport.py:27  pastadd (95_testprotokoll.md: en grind som aldrig fallit ar oprovad).
* enhet/test_verktyg_transport.py:554  assert "oprovad" in u.skal("station_statistics")

### protocol/kor_fas20_modellen.py

* protocol/kor_fas20_modellen.py:379  hans prefix rors aldrig av oprovad kod, och det galler ocksa att sla av

### protocol/kor_fas5.py

* protocol/kor_fas5.py:5  VC. Det ar precis den sortens oprovade yta dar dokumentationen och verkligheten
* protocol/kor_fas5.py:35  "verktyg utan forutsattningar redovisas som oprovade, aldrig som "
* protocol/kor_fas5.py:207  (", oprovade: " + ", ".join(saknas)) if saknas else ""))

### protocol/kor_kunskapstackning.py

* protocol/kor_kunskapstackning.py:472  kalla = sedda_api.get(namn) or ("M-84/M-85 oppen punkt: %s" % namn)

### motbevis/test_grindar_som_aldrig_fallt_motbevis.py

* motbevis/test_grindar_som_aldrig_fallt_motbevis.py:89  oprovade = [k for k in koder if not re.search(r"\b%s\b" % k, text)]
* motbevis/test_grindar_som_aldrig_fallt_motbevis.py:90  assert not oprovade, ("felkoder som inget enhetstest nämner: %s"
* motbevis/test_grindar_som_aldrig_fallt_motbevis.py:91  % ", ".join(oprovade))

### motbevis/test_troskelharkomst_motbevis.py

* motbevis/test_troskelharkomst_motbevis.py:64  Alla tio trösklar i ögat bär ordet PRELIMINAR och pekar på en mätning som

