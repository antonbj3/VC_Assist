# Skuldregistret

**Genererat**, aldrig fört för hand. Ett register någon måste komma ihåg att uppdatera är redan glömt, och den enda skuld som hamnar där är den man ändå kom ihåg.

Byggs med `python3 -m vc_assist_svc.skuld` ur två källor som båda skrivs samtidigt som arbetet: mätningarnas ärlighetsavsnitt och markörer i koden.

## Mätningar utan ärlighetsavsnitt: 0

## Mätningsnummer som fler än en fil gör anspråk på: 0

## Ordlistor som bär två storheter: 0

En lista som bär både felord och bara negationer svarar på frågan *bär texten något av de här orden?* — och det är inte den fråga någon grind ställer sig. Mätt tre gånger: M-94 fynd 1 och 4, M-98. Taket är noll, och kriteriet har ingen undantagslista: en lista som bär båda storheterna ska vara **sammansatt** ur de listor som bär var sin.

## Ordlistor som står i två filer: 13

`harness/text.py` säger det själv: *"de ligger PA ETT STALLE just for att en kopierad ordlista blir tva ordlistor sa fort nagon ratter den ena"*. Registret såg inte att regeln bröts. Listan nedan är ett **register**, inte en anklagelse: en delad ordlista kan vara rätt, men den måste vara sedd.

* 12 gemensamma — `svc/vc_assist_svc/guldgrind.py`.**DALIGA_ORD** ↔ `ext/vc_addon/vc_assist/oga_kontrakt.py`.**_FYNDORD**
* 11 gemensamma — `svc/vc_assist_svc/plan/forfining.py`.**ANDELSER** ↔ `svc/vc_assist_svc/plan/lasning.py`.**_ANDELSER**
* 7 gemensamma — `svc/vc_assist_svc/harness/oga.py`.**BARA_NEGATION_OGA** ↔ `svc/vc_assist_svc/harness/text.py`.**BARA_NEGATION**
* 7 gemensamma — `svc/vc_assist_svc/harness/oga.py`.**GODKANNANDEORD** ↔ `svc/vc_assist_svc/harness/text.py`.**FRAMGANGSMARKORER**
* 7 gemensamma — `svc/vc_assist_svc/st/lexer.py`.**NYCKELORD** ↔ `svc/vc_assist_svc/st/modell.py`.**VARSORTER**
* 6 gemensamma — `svc/vc_assist_svc/st/skrivare.py`.**JAMFORELSER** ↔ `svc/vc_assist_svc/st/validator.py`.**JAMFORELSER**
* 5 gemensamma — `svc/vc_assist_svc/api_index.py`.**_RANGORDNING** ↔ `svc/vc_assist_svc/llm/urval.py`.**_RANGORDNING**
* 4 gemensamma — `svc/vc_assist_svc/guldgrind.py`.**INTE_NONE** ↔ `ext/vc_addon/vc_assist/oga_kontrakt.py`.**_INTE_NONE**
* 3 gemensamma — `ext/vc_addon/vc_assist/plats.py`.**WINDOWSPLATTFORMAR** ↔ `install/upptackt.py`.**WINDOWSPLATTFORMAR**
* 3 gemensamma — `svc/vc_assist_svc/guldgrind.py`.**OBLIGATORISKA_SEKTIONER** ↔ `svc/vc_assist_svc/forlopp/yta.py`.**OBLIGATORISKA_SEKTIONER**
* 2 gemensamma — `svc/vc_assist_svc/verktyg/matning.py`.**_YTOR_LAYOUT** ↔ `svc/vc_assist_svc/verktyg/robotik.py`.**_YTOR_LAYOUT**
* 1 gemensamma — `svc/vc_assist_svc/api_index.py`.**_RANGORDNING** ↔ `svc/vc_assist_svc/verktyg/katalog.py`.**_RANGORDNING**
* 1 gemensamma — `svc/vc_assist_svc/llm/urval.py`.**_RANGORDNING** ↔ `svc/vc_assist_svc/verktyg/katalog.py`.**_RANGORDNING**

## Vad mätningarna säger att de inte vet: 543 punkter

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

* Ingenting är mätt än. Den här filen är en reservation av numret, inte ett

### M-101_komponentmodellen_byggd_ur_specen.md — LIMITS

* Ingenting är mätt än.** Filen finns för att numret ska vara taget i
* Tak: **0** påståenden. Inget här får citeras förrän körningen finns.

### M-102_modellagret_mot_riktiga_verktygssvar.md — LIMITS

* Mätningen är inte klar.** Ingenting nedanför den här raden är ännu ett tal.
* Ingen språkmodell och ingen leverantör är anropad. Allt mäts mot repots egna
* Ingen brygga och ingen VC är igång. Verktygssvaren kommer ur de handlare som
* deklarerade** `returns`, inte ur en körning.
* Tokenräkningen är en omräkning ur byte, inte en leverantörs tokenisering.

### M-103_aterhamtningen_som_anvandaren_ser_den.md — LIMITS

* Ingenting är mätt än.** Filen finns för att numret ska vara taget i
* Tak: **0** påståenden. Inget här får citeras förrän körningen finns.

### M-104_bankposterna_over_26_korningar.md — LIMITS

* Ingenting är mätt än.** Tak: **0** påståenden. Inget här får citeras

### M-105_ett_monster_som_aldrig_kort_mot_sin_text.md — LIMITS

* Ingenting är mätt ännu. Talen nedan skrivs när mätningen är körd.

### M-106_bankens_facitkallor.md — LIMITS

* Ingenting är mätt ännu. Talen nedan skrivs när mätningen är körd. Tak: 0.

### M-107_tillverkarens_datablad.md — LIMITS

* Ingenting är mätt ännu. Talen nedan skrivs när mätningen är körd. Tak: 0.

### M-11_kvaternion_och_varldsmatris.md — Vad som INTE är mätt

* Kvaternionsordningen är mätt för ren gir kring Z, och bara för den.** I alla
* Sammansatta vridningar är inte prövade alls. Tabellen har en axel i taget.
* `WorldPositionMatrix`-eftersläpningen är mätt på **en** komponent på scenens
* De fyra raderna om vad som hämtar hem världsmatrisen är mätta var för sig i
* Fallet ögat faktiskt möter — läsning **inne i** simuleringens steg, av något
* `getAxisAngle()`:s vinkel i grader är **läst ur medföljande dokumentation**,
* Sidofynden om `vcMatrix.identity()`, saknad `__getattribute__` och `vcMatrix`

### M-12_onidle_fyrar_inte.md — Vad som INTE är mätt

* Frånvaron är mätt över **90 sekunder**, i en körning, headless. En `OnIdle` som
* `OnRender` mättes bara headless. Texten säger själv att förklaringen — att
* Raden för `OnComponentAdded` är ingen mätning av händelsen. Provet innehöll
* De 13 sekunderna mellan `OnStart` och `OnAppInitialized` kommer ur **en**
* Att kroken *"bevisligen laddades"* vilar på att två andra händelser kom fram.
* Slutsatsen *"att en händelse står i dokumentationen betyder inte att den fyrar"*

### M-13_vad_som_dodar_pumpen.md — Vad som INTE är mätt

* Listan över dödande anrop är uttryckligen ofullständig, och den är ofullständig
* Slutsatsen *"scenbygge i allmänhet är ofarligt"* vilar på fem gröna operationer
* Förklaringen till varför `VC_SCRIPT` dödar pumpen (*"VC måste kompilera om och
* De tre omstartsvägarna är prövade en gång var i den här uppställningen.
* "`OnRun` återinträder inte"* är mätt för dem, inte för varje väg som finns.
* Att varningen före körning räcker för anroparen är inte mätt mot en verklig
* Att `wineserver` håller port 8901 kvar är mätt under Wine. Motsvarande fråga på
* Punkt 2 i M-16 — att `skrivgrind.DODANDE_ANROP` behöver en **läsande** gren —

### M-15_skapbara_beteenden.md — Vad som INTE är mätt

* De 80 träffarna är mätta som *"`createBehaviour` returnerade ett objekt"*. Att
* De 164 som ger `None` är mätta som icke-skapbara **med ett argumentlöst anrop**
* Urvalet är de `VC_*`-konstanter som fanns i **skriptets** scope. Konstanter som
* Metodfelet är rättat för heltalsfiltret. Att det **nya** urvalet är komplett är
* Att svepet dödade bryggan i nästa körning står som omätt orsak. Mätningen
* `VC_TRANSPORT` som kandidat till `Ref<ComponentProcessor>` är märkt oprövad i
* Python-typen i högerkolumnen är läst av typnamnet på det returnerade objektet.

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

* Mätningen är inte gjord än — filen reserverar bara numret.

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

* Talen mot den lagade grinden är inte klara än.** Det som står ovan är
* n = 1 per uppgift och läge.** Ingen upprepning, ingen spridning.
* Fyra uppgifter av 51** — bara de har spårfacit.
* En modell, en promptformulering.** Byts någotdera kan talen bli andra.
* Domen kommer ur vår ST-tolk**, korsprövad mot STruC++ men inte mot OpenPLC.
* Skiftlägessvepet är tretton konstruktioner på lexernivå**, inte hela

### M-97_plc_axelns_giltighet.md — LIMITS

* Mätningen är inte gjord än — filen reserverar bara numret.

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
* Tröskellintern är röd av annat.** `test_troskelharkomst.py` räknar 63
* Sju konsumenter är alla jag hittade, inte alla som finns.** Sökningen gick

### M-99_differentialsvepet_mot_kompilatorn.md — LIMITS

* Mätningen är inte klar.** Ingenting nedanför den här raden är ännu ett tal.
* Facit är STruC++ v0.6.6, inte standarden och inte OpenPLC.
* STruC++ är ingen namnauktoritet: `HITTEPA(x)` passerar dess främmande.

## Produktionsmoduler som ingen provfil nämner: 3 (778 rader)

* `svc/vc_assist_svc/bankkontrakt.py` — 173 rader
* `svc/vc_assist_svc/llm/ogontrim.py` — 432 rader
* `svc/vc_assist_svc/llm/scenvy.py` — 173 rader

## Produktionsmoduler som bara nämns av en L3-körning (kräver VC/OpenPLC, körs inte av `pytest tests/enhet`): 2 (218 rader)

* `svc/vc_assist_svc/forlopp/__main__.py` — 83 rader
* `svc/vc_assist_svc/plc/opcuakonfig.py` — 135 rader

## Markörer i koden: 123

### vc_assist_svc/harness/efterlevnad.py

* vc_assist_svc/harness/efterlevnad.py:15  grind som SKULLE ha fallt star fortfarande oprovad.

### vc_assist_svc/harness/fallor.py

* vc_assist_svc/harness/fallor.py:24  trasig fixtur ar oprovad (S2 i 96_ingen_skuld.md, och 95_testprotokoll).
* vc_assist_svc/harness/fallor.py:994  "orden 'kvar, och inte lagat': arlighetsgrinden fragade "

### vc_assist_svc/llm/budget.py

* vc_assist_svc/llm/budget.py:16  trimning. En bokforing som bara provas at ena hallet ar oprovad.
* vc_assist_svc/llm/budget.py:73  "PRELIMINAR, M-29: ingen tokenrakning over verkliga turer finns"),
* vc_assist_svc/llm/budget.py:75  "PRELIMINAR, M-29"),
* vc_assist_svc/llm/budget.py:80  "PRELIMINAR, M-29"),
* vc_assist_svc/llm/budget.py:86  "PRELIMINAR, M-29; EDGE och MINDIST vaxer med forloppet"),
* vc_assist_svc/llm/budget.py:88  "PRELIMINAR, M-29"),
* vc_assist_svc/llm/budget.py:90  "PRELIMINAR, M-29"),

### vc_assist_svc/llm/matt.py

* vc_assist_svc/llm/matt.py:52  # PRELIMINAR, satt av matning M-28 (adapterprovets punkt 4 i

### vc_assist_svc/llm/scenvy.py

* vc_assist_svc/llm/scenvy.py:36  # PRELIMINAR, satts av matning M-29. Motivet ar matt: bankens storsta scen ar
* vc_assist_svc/llm/scenvy.py:42  # Samma sak per komponent. PRELIMINAR, matning M-29.

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
* vc_assist_svc/aterhamtning/yta.py:131  d, "ingen avläsning gjord; om %s lever är inte prövat" % d,

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

### vc_addon/vc_assist/formaga.py

* vc_addon/vc_assist/formaga.py:95  oprovade = [y for y, d in ytor.items() if d["finns"] is None]
* vc_addon/vc_assist/formaga.py:107  "oprovade": len(oprovade),
* vc_addon/vc_assist/formaga.py:110  "oprovade_ytor": sorted(oprovade),

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
* vc_addon/vc_assist/oga_analys.py:80  PLC_AXEL_MAX_ANDEL = 0.10        # PRELIMINAR. Satts av matning M-97.

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
* vc_addon/vc_assist/oga_harledning.py:1275  avhuggen sista cykel ar inte ett brott - den ar oprovad, och de tva far

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
* enhet/test_bestallning.py:1875  # (M-68 raknade den som helt oprovad.)

### enhet/test_dataverktyg.py

* enhet/test_dataverktyg.py:13  aldrig fallit ar oprovad (docs/spec/95_testprotokoll.md).

### enhet/test_formaga.py

* enhet/test_formaga.py:50  assert s["finns"] + s["saknas"] + s["oprovade"] == s["provade"] == len(F.YTOR)

### enhet/test_harness.py

* enhet/test_harness.py:964  """S8: ingen TODO utan datum och ägare. Formen är TODO(datum, fas)."""
* enhet/test_harness.py:970  for markor in ("TODO", "FIXME", "XXX"):

### enhet/test_install.py

* enhet/test_install.py:884  assert "OPROVAD SOKVAG" in ut, "5.0 + Python 3 ar inte kort av oss"

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

### enhet/test_troskelharkomst.py

* enhet/test_troskelharkomst.py:153  fel.append("%s:%d %s -> %s utan PRELIMINAR" % (rel, nr, namn, _mnr(r)))

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

### protocol/kor_fas5.py

* protocol/kor_fas5.py:5  VC. Det ar precis den sortens oprovade yta dar dokumentationen och verkligheten
* protocol/kor_fas5.py:172  (", oprovade: " + ", ".join(saknas)) if saknas else ""))

### motbevis/test_grindar_som_aldrig_fallt_motbevis.py

* motbevis/test_grindar_som_aldrig_fallt_motbevis.py:89  oprovade = [k for k in koder if not re.search(r"\b%s\b" % k, text)]
* motbevis/test_grindar_som_aldrig_fallt_motbevis.py:90  assert not oprovade, ("felkoder som inget enhetstest nämner: %s"
* motbevis/test_grindar_som_aldrig_fallt_motbevis.py:91  % ", ".join(oprovade))

### motbevis/test_troskelharkomst_motbevis.py

* motbevis/test_troskelharkomst_motbevis.py:64  Alla tio trösklar i ögat bär ordet PRELIMINAR och pekar på en mätning som

