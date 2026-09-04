# Skuldregistret

**Genererat**, aldrig fört för hand. Ett register någon måste komma ihåg att uppdatera är redan glömt, och den enda skuld som hamnar där är den man ändå kom ihåg.

Byggs med `python3 -m vc_assist_svc.skuld` ur två källor som båda skrivs samtidigt som arbetet: mätningarnas ärlighetsavsnitt och markörer i koden.

## Mätningar utan ärlighetsavsnitt: 16

En mätning utan ett sådant avsnitt är inte en mätning utan skuld — det är en mätning vars skuld ingen har skrivit ned.

* `M-11_kvaternion_och_varldsmatris.md`
* `M-12_onidle_fyrar_inte.md`
* `M-13_vad_som_dodar_pumpen.md`
* `M-15_skapbara_beteenden.md`
* `M-16_canconnect_dodar_pumpen.md`
* `M-31_lintern_var_sjalv_en_falsk_gron.md`
* `M-32_mataren_och_komponentidentiteten.md`
* `M-33_varldsenheten_ar_millimeter.md`
* `M-34_produkten_finns_men_flodar_inte.md`
* `M-35_kollisionsdetektorn_fyrar_inte.md`
* `M-36_measuredistance_ar_kollisionsmattet.md`
* `M-37_granssnitt_gar_att_koppla.md`
* `M-40_varfor_mataren_aldrig_fyrade.md`
* `M-44_windows_oprovat.md`
* `M-47_verktygstackning_runda_1.md`
* `M-50_de_trasiga_fallen.md`

## Vad mätningarna säger att de inte vet: 171 punkter

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

### M-20_plcbandet.md — 9. Vad som inte är mätt

* Visual Components.** Fas 6:s grind i `70_faser.md` heter "handskriven ST
* PLC-halvan** av bandet, från OPC UA-klient till scancykel och tillbaka.
* Windows.** Allt ovan är Linux (I17).
* Fler än två signaler.** Provstationen har en in och en ut. Hur
* Säkerhetslägen i OPC UA.** Bara `None/None` med anonym åtkomst är körd.
* Belastning.** Ingen mätning gjordes med samtidig trafik, och maskinen körde

### M-38_vagen_mellan_plc_och_scen.md — Vad som inte är avgjort

* Om VC:s inbyggda koppling går att få in via en **sparad layout** som redan
* Om 80 ms räcker. Det beror på vad som ska styras: en transportör med 200 mm/s
* Ögats krav att PLC-värden ligger på **samma tidsaxel** som fysiken. Med två

### M-39_slingan_sluten.md — Vad som INTE är prövat

* Bara två signaler.** En verklig station har tiotals, och kopplarens varv
* Ingen rörelse i scenen.** Donet är en boolesk signal, inte en transportör
* Ingen tidsstämpling till ögat.** Kopplaren mäter sina egna led, men skjuter
* Windows.**

### M-41_produkten_flodar.md — Vad som inte är visat

* Produkten lämnar aldrig banan till något annat.** Banans utgångs­gränssnitt
* oprövat**.
* Inget skript, ingen station, ingen process.** Linjen är matare + bana. Det
* `Accumulate = True` är satt men aldrig belastad.** Ingen produkt har blivit
* Rörelsen är mätt i simulerad tid, inte i väggklockstid.** Serien är tagen

### M-42_plc_pa_ogats_tidsaxel.md — Vad som INTE är mätt

* Mot en levande VC.** Riggen mäter mekanismen, inte produktionsvägen.
* Epokfrågan är kringgången, inte besvarad.** Om VC:s `time.time()` under
* Flera kopplare mot samma öga.** Det sista inskottet vinner; ingen
* Windows.**

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

### M-48_grind_1_till_4_skarpt.md — Vad som INTE är mätt

* Ögat.** Grind 5 ingår inte. T3–T6 i protokollet kan inte prövas förrän
* Driftsättning.** CLI-vägen svarar bara på *går den att bygga?*. Den skriver
* Reproducerbarhet.** STruC++ ligger i en sessionskatalog, inte i repot, och
* Flera stationer.** En station, tre trasiga fall.

### M-49_stationen_arbetar.md — Vad som INTE är visat

* Nödstoppet.** Den skyddade ingången kan inte drivas från kopplaren och står
* Att simuleringen kan gå i realtid med slingan sluten.** Kvoten mättes till
* Fler än en station.** Fas 8.
* Hur ofta det lyckas.** Ett grönt varv är inte en frekvens. Fas 9.
* Windows.**

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

### M-71_ren_maskin_utan_vc.md — Vad som fortfarande INTE är prövat

* Att VC startar med det installationen lade dit.** Det är fas 10:s enda
* Windows och macOS.** Manifestet bär posterna; ingen har kört dem. M-44 har
* En maskin utan node.** Kedjan kräver `node` och använder det som finns
* En maskin utan nät.** Hämtningen förutsätter åtkomst till GitHub och npm.
* En maskin utan docker.** OpenPLC-avbilden dras av docker, inte av oss.
* Klonen är lokal.** `git clone --local` från samma disk, inte över nätet.

## Produktionsmoduler som ingen provfil nämner: 3 (786 rader)

* `svc/vc_assist_svc/layout/vc_utdata.py` — 143 rader
* `svc/vc_assist_svc/plan/layoutport.py` — 264 rader
* `svc/vc_assist_svc/plan/villkorssprak.py` — 379 rader

## Produktionsmoduler som bara nämns av en L3-körning (kräver VC/OpenPLC, körs inte av `pytest tests/enhet`): 3 (656 rader)

* `svc/vc_assist_svc/plan/bestallning.py` — 234 rader
* `svc/vc_assist_svc/plan/processer.py` — 287 rader
* `svc/vc_assist_svc/plc/opcuakonfig.py` — 135 rader

## Markörer i koden: 101

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

