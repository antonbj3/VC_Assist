# Skuldregistret

**Genererat**, aldrig fört för hand. Ett register någon måste komma ihåg att uppdatera är redan glömt, och den enda skuld som hamnar där är den man ändå kom ihåg.

Byggs med `python3 -m vc_assist_svc.skuld` ur två källor som båda skrivs samtidigt som arbetet: mätningarnas ärlighetsavsnitt och markörer i koden.

## Mätningar utan ärlighetsavsnitt: 0

## Vad mätningarna säger att de inte vet: 330 punkter

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
* Om `Name` någonsin ligger efter byte 181** — M-58:s öppna rad står kvar,
* Två tolkare av samma format.** `datablad.py` läser rotens variabelrymd med

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

## Produktionsmoduler som ingen provfil nämner: 1 (143 rader)

* `svc/vc_assist_svc/layout/vc_utdata.py` — 143 rader

## Produktionsmoduler som bara nämns av en L3-körning (kräver VC/OpenPLC, körs inte av `pytest tests/enhet`): 1 (135 rader)

* `svc/vc_assist_svc/plc/opcuakonfig.py` — 135 rader

## Markörer i koden: 103

### vc_assist_svc/harness/efterlevnad.py

* vc_assist_svc/harness/efterlevnad.py:15  grind som SKULLE ha fallt star fortfarande oprovad.

### vc_assist_svc/harness/fallor.py

* vc_assist_svc/harness/fallor.py:24  trasig fixtur ar oprovad (S2 i 96_ingen_skuld.md, och 95_testprotokoll).
* vc_assist_svc/harness/fallor.py:970  "orden 'kvar, och inte lagat': arlighetsgrinden fragade "

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

### vc_assist_svc/layout/losare.py

* vc_assist_svc/layout/losare.py:374  oprovade = []
* vc_assist_svc/layout/losare.py:381  oprovade.append(r)
* vc_assist_svc/layout/losare.py:385  return tuple(kvar), tuple(oprovade)
* vc_assist_svc/layout/losare.py:466  konflikt, oprovade = _minimal_konflikt(scen, relationer, ordning, steg_m,
* vc_assist_svc/layout/losare.py:477  if oprovade:
* vc_assist_svc/layout/losare.py:480  % (len(oprovade),
* vc_assist_svc/layout/losare.py:481  ", ".join(r.kod for r in oprovade)))

### vc_assist_svc/forlopp/yta.py

* vc_assist_svc/forlopp/yta.py:55  TYSTNADSTAK_S = 5.0             # PRELIMINÄR. Satts av M-28.

### vc_addon/vc_assist/bridge_cmd.py

* vc_addon/vc_assist/bridge_cmd.py:53  OMSTART_MINSTA_MELLANRUM_S = 0.5    # PRELIMINAR. Satts av matning M-13.

### vc_addon/vc_assist/formaga.py

* vc_addon/vc_assist/formaga.py:95  oprovade = [y for y, d in ytor.items() if d["finns"] is None]
* vc_addon/vc_assist/formaga.py:107  "oprovade": len(oprovade),
* vc_addon/vc_assist/formaga.py:110  "oprovade_ytor": sorted(oprovade),

### vc_addon/vc_assist/oga_analys.py

* vc_addon/vc_assist/oga_analys.py:35  GRIP_STABIL_MM = 2.0        # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:36  GRIP_RORELSE_MM = 5.0       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:37  GRIP_FONSTER_S = 0.25       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:38  TELEPORT_MAX_MM = 150.0     # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:39  CARRY_RIGID_DEG = 2.0       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:40  CARRY_MIN_SPAN_S = 0.5      # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:41  PLACE_TOL_MM = 25.0         # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:42  BLOWUP_VMAX_MS = 25.0       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:43  UNDERGROUND_MARGINAL_M = 0.005   # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:44  MIN_PROV = 10               # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:48  SCEN_OLAST_MAX_ANDEL = 0.25      # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_analys.py:52  GENOMSTROMNING_MARGINAL_S = 0.0  # PRELIMINAR. Satts av matning M-19.

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
* vc_addon/vc_assist/oga_harledning.py:1135  avhuggen sista cykel ar inte ett brott - den ar oprovad, och de tva far

### vc_addon/vc_assist/oga_provtagning.py

* vc_addon/vc_assist/oga_provtagning.py:29  SKRIV_VAR_N_RAD = 100       # PRELIMINAR. Satts av matning M-10.
* vc_addon/vc_assist/oga_provtagning.py:57  PLC_FARSK_S = 0.25          # PRELIMINAR. Satts av matning M-19.

### vc_addon/vc_assist/plats.py

* vc_addon/vc_assist/plats.py:37  # Miljovariabler som slar all harledning. Finns for att en oprovad plattform

### vc_addon/vc_assist/pump.py

* vc_addon/vc_assist/pump.py:51  AKTIV_FONSTER_S = 2.0      # PRELIMINAR. Satts av matning M-26.
* vc_addon/vc_assist/pump.py:56  OMSTART_MINSTA_MELLANRUM_S = 1.0    # PRELIMINAR. Satts av matning M-13.
* vc_addon/vc_assist/pump.py:57  OMSTART_TAK_PER_MINUT = 20          # PRELIMINAR. Satts av matning M-13.
* vc_addon/vc_assist/pump.py:241  self.logg("formaga: %d av %d ytor finns, %d saknas, %d oprovade"
* vc_addon/vc_assist/pump.py:242  % (sm["finns"], sm["provade"], sm["saknas"], sm["oprovade"]))

### installera.py

* installera.py:56  return ("OPROVAD SOKVAG: %s + %s ar inte kord av oss. Kontrollera att "

### schema.py

* schema.py:835  # domaren måste fälla. Utan minst ett per spårfacit är grinden oprovad (regel

### enhet/test_api_index.py

* enhet/test_api_index.py:604  """docs/spec/95_testprotokoll.md: en grind utan trasig fixtur ar oprovad."""

### enhet/test_bestallning.py

* enhet/test_bestallning.py:14  slapper igenom det korrekta. En grind som bara provats at ena hallet ar oprovad
* enhet/test_bestallning.py:1163  oprovad - och en oprovad grind ar en forhoppning som har fatt ett namn.

### enhet/test_dataverktyg.py

* enhet/test_dataverktyg.py:13  aldrig fallit ar oprovad (docs/spec/95_testprotokoll.md).

### enhet/test_formaga.py

* enhet/test_formaga.py:50  assert s["finns"] + s["saknas"] + s["oprovade"] == s["provade"] == len(F.YTOR)

### enhet/test_harness.py

* enhet/test_harness.py:936  """S8: ingen TODO utan datum och ägare. Formen är TODO(datum, fas)."""
* enhet/test_harness.py:942  for markor in ("TODO", "FIXME", "XXX"):

### enhet/test_install.py

* enhet/test_install.py:884  assert "OPROVAD SOKVAG" in ut, "5.0 + Python 3 ar inte kort av oss"

### enhet/test_layout.py

* enhet/test_layout.py:619  if "TODO" in rad and not re.search(r"TODO\(\d{4}-\d{2}-\d{2}", rad)]
* enhet/test_layout.py:620  assert not bara_todo, "bar TODO i %s: %r" % (fil, bara_todo[:2])

### enhet/test_mekanisering_m53.py

* enhet/test_mekanisering_m53.py:568  """M-46:s 'kvar, och inte lagat'. Foll fore M-53: turen slapptes."""
* enhet/test_mekanisering_m53.py:790  och lat fragan sta oprovad.

### enhet/test_oga_harledning.py

* enhet/test_oga_harledning.py:87  fel.append("%s:%d %s -> %s utan PRELIMINAR" % (rel, nr, namn, L._mnr(r)))

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
* enhet/test_verktyg.py:556  assert "oprovad" in u.skal("clone_component")

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

