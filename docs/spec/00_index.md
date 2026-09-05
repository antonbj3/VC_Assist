# Specifikation — innehåll

Alla dokument, i nummerordning. Uppdaterad 2026-09-04.

| Dok | Innehåll |
|---|---|
| `01_kalldisciplin.md` | Källdisciplin |
| `10_matta_fakta.md` | Mätta fakta |
| `20_arv.md` | Arv från Isaac Assist |
| `21_arv_placering.md` | Arv för placering och kollisionshantering |
| `22_planeringslagret.md` | Planeringslagret |
| `23_llm_granssnitt.md` | Språkmodellgränssnittet |
| `24_samtalsloopen.md` | Samtalsloopen |
| `25_kontextbudget.md` | Kontextbudgeten |
| `26_appen.md` | Appen |
| `27_operatorsflodet.md` | Operatörsflödet |
| `28_lagen_och_aterhamtning.md` | Lägen och återhämtning |
| `30_arkitektur.md` | Arkitektur |
| `31_brygga_protokoll.md` | Bryggans protokoll |
| `35_plattformar.md` | Plattformar — Windows och Wine |
| `36_versioner.md` | Versionsstöd — universalitet |
| `40_ogat.md` | Ögat — vc_eyes |
| `41_ogat_kontrakt.md` | Ögats domskontrakt |
| `42_ogat_utbyggt.md` | Ögat, utbyggt |
| `45_verktyg.md` | Verktygslagret |
| `46_kunskapsindex.md` | Kunskapsindexet |
| `47_verktygstackning.md` | Täckningsanalys — hela API-ytan mot ett verktygsbibliotek |
| `48_personaprofiler.md` | Personaprofiler |
| `49_komponentmodellen.md` | 49 — Komponentmodellen: hur en komponent kan koppla ihop sig |
| `50_grindar.md` | Grindkedjan |
| `51_komponentdata.md` | Komponentdata |
| `52_regelbanken.md` | Regelbanken |
| `53_utvagen.md` | Utvägen — flytta receptet, inte scenen |
| `54_felstallda_fragor.md` | Fem frågor vi svarat på utan att pröva om de var rätt |
| `55_innovationsplanen.md` | Innovationsplanen — vad som bär, vad produkten är, vad vi slutar med |
| `60_plc.md` | PLC-benet |
| `61_st_generering.md` | Vad modellen får skriva, och hur det döms |
| `70_faser.md` | Faser |
| `80_bank.md` | Bänken |
| `81_mallschema.md` | Mallschema |
| `82_felklasser.md` | Felklasser |
| `83_scenarier.md` | Scenariokatalogen |
| `90_invarianter.md` | Invarianter |
| `95_testprotokoll.md` | Test- och verifieringsprotokoll |
| `96_ingen_skuld.md` | Ingen teknisk skuld |

## Mätningar

Tabellen är **genererad** ur `docs/matningar/`, aldrig förd för hand.
Bygg om den med `PYTHONPATH=svc python3 -m vc_assist_svc.matningsindex`.
Ett prov fäller om filen på disk slutat stämma.

<!-- MATNINGSTABELL: genererad, rör inte för hand -->

| Fil | Vad den mätte |
|---|---|
| `M-01_tillaggsmekanismen.md` | M-01 — tilläggsmekanismen, mätt |
| `M-02_prefixisolering.md` | M-02 — testprefixets isolering, mätt |
| `M-03_takt.md` | M-03 — bryggans takt och svarstid |
| `M-04_exekveringsmodellen.md` | M-04 — VC:s exekveringsmodell, och varför bryggan måste byggas om |
| `M-05_skrivningar_och_pump.md` | M-05 — varför varje skrivning fallerade, och var pumpen står |
| `M-06_pumpen_fungerar.md` | M-06 — pumpen fungerar: vcScript.OnRun med delay() |
| `M-07_motorn_ar_stackless.md` | M-07 — motorn är Stackless Python, och trådmodellen är mätt död |
| `M-08_vaggklockspumpen.md` | M-08 — väggklockspumpen: `app.startSimulation()` |
| `M-09_tyst_syntaxfel.md` | M-09 — VC sväljer ett syntaxfel i kommandomodulen helt |
| `M-11_kvaternion_och_varldsmatris.md` | M-11 — kvaternionens ordning, och världsmatrisens eftersläpning |
| `M-12_onidle_fyrar_inte.md` | M-12 — `vcApplication.OnIdle` fyrar inte |
| `M-13_vad_som_dodar_pumpen.md` | M-13 — exakt en operation dödar pumpen |
| `M-14_granssnitt_gar_att_skapa_men_inte_koppla.md` | M-14 — gränssnitt går att skapa, men inte att koppla ihop |
| `M-15_skapbara_beteenden.md` | M-15 — vilka beteenden som faktiskt går att skapa |
| `M-16_canconnect_dodar_pumpen.md` | M-16 — `canConnect` dödar pumpen |
| `M-17_kontaktkoppling_fungerar.md` | M-17 — komponenter går att koppla ihop, på kontaktnivå |
| `M-20_plcbandet.md` | M-20 — PLC-bandet: vad som faktiskt går att köra, och hur snabbt |
| `M-31_lintern_var_sjalv_en_falsk_gron.md` | M-31 — tröskellintern var själv en falsk grön |
| `M-32_mataren_och_komponentidentiteten.md` | M-32 — komponentidentitet, uppstartsordning, och en matare som inte matar |
| `M-33_varldsenheten_ar_millimeter.md` | M-33 — VC:s basenhet är millimeter |
| `M-34_produkten_finns_men_flodar_inte.md` | M-34 — produkten finns; jag mätte på fel lista |
| `M-35_kollisionsdetektorn_fyrar_inte.md` | M-35 — kollisionsdetektorn fyrar inte, och därför är fas 5 inte stängd |
| `M-36_measuredistance_ar_kollisionsmattet.md` | M-36 — `measureDistance` är kollisionsmåttet, inte detektorn |
| `M-37_granssnitt_gar_att_koppla.md` | M-37 — gränssnitt går att koppla; `Container` var den saknade bindningen |
| `M-38_vagen_mellan_plc_och_scen.md` | M-38 — VC:s Python når inte OPC UA, men bryggan når signalerna |
| `M-39_slingan_sluten.md` | M-39 — handskriven ST styr scenen; slingan sluten och mätt |
| `M-40_varfor_mataren_aldrig_fyrade.md` | M-40 — varför matningen aldrig fyrade: två tysta villkor, inte ett |
| `M-41_produkten_flodar.md` | M-41 — produkten matas fram av sig själv och åker: mätt i tal |
| `M-42_plc_pa_ogats_tidsaxel.md` | M-42 — PLC:ns värden på ögats tidsaxel: klockvalet, fördröjningen, och hålet |
| `M-44_windows_oprovat.md` | M-44 — Windows: vad som rättades, och vad som fortfarande är oprövat |
| `M-45_bankens_tackning.md` | M-45 — bankens täckning: hur många uppgifter har ett facit en domare kan läsa |
| `M-46_harnessens_hardhet.md` | M-46 — Härdar harnessen något, eller är den ställning? |
| `M-47_verktygstackning_runda_1.md` | M-47 — verktygstäckningen mätt i tre listor, runda 1 |
| `M-48_grind_1_till_4_skarpt.md` | M-48 — grind 1–4 körda skarpt, och tre ställen där vår grind är strängare än kompilatorn |
| `M-49_stationen_arbetar.md` | M-49 — stationen arbetar, och mätinstrumentet som låg i mätvägen |
| `M-50_de_trasiga_fallen.md` | M-50 — de trasiga fallen, och vad som fällde vad |
| `M-51_svepet_over_st_lagret.md` | M-51 — 185 ST-konstruktioner genom båda grindarna: 55 avvek, 36 var falska rödgrindar |
| `M-52_reparationsslingan.md` | M-52 — reparationsslingan i två lägen, och taket som slutade löna sig vid fyra |
| `M-53_fran_bedd_till_grind.md` | M-53 — Från bedd till grind |
| `M-54_tolken_mot_strucpp.md` | M-54 — tolken mot en andra motor, och en grind som sa GODKÄND om kod som inte går att bygga |
| `M-55_export_till_usd_och_urdf.md` | M-55 — VC kan inte exportera till USD eller URDF, men bär halva datan |
| `M-56_verktygskedjan_i_repot.md` | M-56 — verktygskedjan går att hämta ur repot, och två hål på vägen dit |
| `M-57_biblioteket_fanns_hela_tiden.md` | M-57 — komponentbiblioteket fanns hela tiden; jag mätte på fel ställe |
| `M-58_var_metadatan_ligger.md` | M-58 — var i metadatan fälten ligger, och vad "kategori" faktiskt är i grunt läge |
| `M-59_databladets_tackning.md` | M-59 — databladets täckning: vad de 3201 komponenterna faktiskt bär |
| `M-60_vad_ett_katalogsvar_kostar.md` | M-60 — vad ett katalogsvar kostar, och varför en bred fråga inte får en lista |
| `M-61_vad_en_komponentfil_bar.md` | M-61 — vad en komponentfil bär, och varför den omslutande volymen inte står i den |
| `M-62_baslinjen.md` | M-62 — baslinjen: vad en klassisk generator klarar på samma bank, med samma domare |
| `M-63_planeringslagret_matt_mot_sin_spec.md` | M-63 — planeringslagret mätt mot sin egen spec |
| `M-64_vad_anvandaren_ser_medan_det_arbetar.md` | M-64 — vad användaren ser medan det arbetar, och de sju rapportytor som inte var till honom |
| `M-65_ogat_pa_djupet.md` | M-65 — ögat på djupet: glappet, fem domare, och vad ögat inte ser |
| `M-66_skuldregistret.md` | M-66 — teknisk skuld fångad när den skrivs, inte vid en senare granskning |
| `M-67_kopplingen_ar_logisk.md` | M-67 — kopplingen är logisk: den flyttar ingenting |
| `M-68_kod_utan_prov.md` | M-68 — 2656 rader produktionskod som inget enhetsprov rör |
| `M-69_tre_svar_pa_hur_manga_robotar.md` | M-69 — tre olika svar på "hur många robotar", och bara ett är sant |
| `M-70_arlighetsskulden_betald.md` | M-70 — ärlighetsskulden betald, och mönstret som räknade fel på sig självt |
| `M-71_ren_maskin_utan_vc.md` | M-71 — hela kedjan ur en ren klon, utom det som kräver VC |
| `M-72_kvaternionens_ordning_pa_tre_axlar.md` | M-72 — kvaternionens ordning avgjord på alla tre axlarna |
| `M-73_linan_arbetar.md` | M-73 — linan arbetar: två stationer, ett delat don, och guld i tre celler |
| `M-74_kompositionsfallen.md` | M-74 — kompositionsfallen: fel som bara finns när stationerna står tillsammans |
| `M-75_vad_ett_spar_avslojar.md` | M-75 — vad ett I/O-spår avslöjar om programmet det kom ur |
| `M-76_katalogposten_fanns_hela_tiden.md` | M-76 — katalogposten fanns hela tiden, i en fil på två kilobyte |
| `M-77_ett_lofte_utan_namn.md` | M-77 — ett löfte utan namn går inte att kontrollera |
| `M-78_modellen_mot_baslinjen.md` | M-78 — modellen mot baslinjen: 0 av 4 mot 4 av 4 |
| `M-79_dubbelskrivningen_hade_ratt.md` | M-79 — dubbelskrivningsregeln skärptes, och visade sig ha haft rätt |
| `M-80_fas9_tre_tal.md` | M-80 — fas 9:s tre tal: 0 av 4, sedan 4 av 4 efter ett varv |
| `M-81_bankens_scen_provas_aldrig.md` | M-81 — bänken bär 282 komponenter som ingen körning har bett om |
| `M-82_modellen_uppfann_inga_namn.md` | M-82 — noll uppfunna VC-namn över 584 kontrollerade |
| `M-83_indexet_svarar_pa_sex_av_sju.md` | M-83 — indexet kunde ha svarat på sex av modellens sju frågor. Den sjunde kan ingen. |
| `M-84_uppslagen_bytte_ordforrad_inte_radantal.md` | M-84 — uppslagen halverade koden och gav den 2,5 gånger fler API-namn |
| `M-85_komponentdatabladet.md` | M-85 — databladet svarar för 3201 komponenter, men banken och biblioteket talar inte samma språk |
| `M-86_ogat_mot_en_korande_vc.md` | M-86 — ögat mot en körande VC: hela scenen, i en enhet, utan driv, och vad den kostar |
| `M-87_hopfogningen_mot_vcs_egen_brygga.md` | M-87 — hopfogningen mot VC:s egen brygga: två klockor, tre fel, ett tak som inte höll |
| `M-88_fem_domare_mot_vc_byggda_celler.md` | M-88 — fem domare mot VC-byggda celler: fyra föll rätt, den femte sa PASS på en svulten station |
| `M-89_anlaggningen_utan_kod.md` | M-89 — vad ett inspelat I/O-spår från en befintlig anläggning räcker till |
| `M-90_ren_maskin_linux.md` | M-90 — ren Linux-maskin: klona, installera, kör (och README motsade repot) |
| `M-91_windowsregistret_mot_en_riktig_kupa.md` | M-91 — installeraren läste fel registernyckel, mätt mot en riktig Windows-kupa |
| `M-92_windowssommen_matt_i_stallet_for_last.md` | M-92 — sömmen mellan VC:s 2.7 och tjänstens 3.x, mätt i stället för läst |
| `M-93_speglingen_som_inte_aldras.md` | M-93 — speglingen som inte åldras, och de två som nu för protokollet |
| `M-94_vad_registret_inte_ser.md` | M-94 — vad skuldregistret inte ser |
| `M-95_fyra_grindar_som_matte_fel_storhet.md` | M-95 — fyra grindar som mätte fel storhet |
| `M-96_slingan_kor_sig_sjalv.md` | M-96 — slingan kör sig själv, och den avslöjade en falsk rödgrind |
| `M-97_plc_axelns_giltighet.md` | M-97 — PLC-axelns giltighet: en körning vars hopfogning inte går att lita på fälls som obestämbar |
| `M-98_den_sjatte_ordlistan.md` | M-98 — den sjätte ordlistan, och grinden som letar efter dem |
| `M-99_differentialsvepet_mot_kompilatorn.md` | M-99 — differentialsvepet: fyra falska rödgrindar, fyra hål och en grind som hängde |
| `M-100_personatackningen.md` | M-100 — Personatäckningen: sju profiler, 228 arbetssteg, mätt mot registret |
| `M-101_komponentmodellen_byggd_ur_specen.md` | M-101 — komponentmodellen byggd ur specen och prövad i riktig VC |
| `M-102_modellagret_mot_riktiga_verktygssvar.md` | M-102 — modellagret mätt mot riktiga verktygssvar |
| `M-103_aterhamtningen_som_anvandaren_ser_den.md` | M-103 — återhämtningen som användaren ser den |
| `M-104_bankposterna_over_26_korningar.md` | M-104 — bänkposterna över repots körningar |
| `M-105_ett_monster_som_aldrig_kort_mot_sin_text.md` | M-105 — ett mönster som aldrig körts mot texten det ska läsa |
| `M-106_bankens_facitkallor.md` | M-106 — bankens facitkällor, mätta post för post |
| `M-107_tillverkarens_datablad.md` | M-107 — tillverkarens datablad som tredje källa: 21 komponenter av 3201 fick en enhet som inte är gissad |
| `M-108_openplc_som_tredje_motor.md` | M-108 — OpenPLC som tredje motor |
| `M-109_universalitet_utan_windows.md` | M-109 — universalitet utan Windows: fem distros, fem Pythons, sju hashar, kapat nät |
| `M-110_tillforlitligheten_i_skala.md` | M-110 — tillförlitligheten i skala: flerskott, enskott och vart varven tar vägen |
| `M-111_halva_grinden_har_aldrig_fyrat.md` | M-111 — 31 av grind 2:s 68 fällplatser har aldrig fyrat |
| `M-112_vc_startar_med_installationens_filer.md` | M-112 — VC startar med det installationen lade dit |
| `M-113_vagen_ur_visual_components.md` | M-113 — Vägen ut ur Visual Components till öppet format |
| `M-114_ingen_vag_ger_tillbaka_kallkoden.md` | M-114 — ingen av vägarna in ger tillbaka källkoden |
| `M-115_flanken_sags_i_kallan_inte_i_sparet.md` | M-115 — flanken syns i källan, inte i spåret: STL, RTAMT och NuSMV mot vårt eget öga |
| `M-116_namnaren_provad_mot_verkligheten.md` | M-116 — Nämnaren provad mot verkligheten |
| `M-118_maskinsakerhet_rakningsbart_och_ansvarsgransen.md` | M-118 — Maskinsäkerhet: vad som är räknebart, och var ansvarsgränsen går |
| `M-119_kunskapstackningen_over_frageslag.md` | M-119 — modellen hittar nästan alla NAMN och nästan ingen BETYDELSE |
| `M-120_tillforlitlighetstalens_yttervarld.md` | M-120 — betyder våra tillförlitlighetstal något jämfört med omvärlden? |
| `M-121_dubbelskrivning_mot_egna_referenser.md` | M-121 — DUBBELSKRIVNING och TYP fällde 7 av 26 egna referenslösningar: referensen eller grinden? |
| `M-122_mutationsskikten_omkorda.md` | M-122 — mutationsmotorn omkörd: facitet fångar 80 % av beteendeskadorna, och det som överlever är initierare |
| `M-123_namnaren_flyttade_sig_och_golvet_med.md` | M-123 — nämnaren flyttade sig, och golvet med den |
| `M-124_de_23_svaren.md` | M-124 — de 23 svaren: facit_spar för bankens sista tredjedel |
| `M-125_openplc_som_tredje_motor.md` | M-125 — OpenPLC som tredje motor (kö A, punkt A1) |
| `M-126_matningsindexet_genereras.md` | M-126 — mätningsindexet genereras, och två sessioner tog samma nummer inom 91 sekunder |
| `M-127_den_femte_domaren_falld_i_vc.md` | M-127 — den femte domaren fälld i VC: genomflödesdomaren mot en svulten station med verklig process |
| `M-128_p15_7_fasdom_och_den_felstallda_fragan.md` | M-128 — P15-7 körd: fasdom mot en känd fördröjning i VC, och varför frågan var fel ställd |
| `M-129_braketten_pa_korningsniva_falld_i_verkligheten.md` | M-129 — braketten på körningsnivå fälld i verkligheten: osäkerhetsbraketten prövad mot naturlig last i VC |
| `M-130_taket_under_naturlig_belastning_och_stopp.md` | M-130 — taket under naturlig belastning och processtopp: två frågor ur D4 besvarade med mätning |
| `M-131_motorn_rattad_c0.md` | M-131 — mutationsmotorns tre rättelser och det nya utgångstalet |
| `M-132_en_riktig_anlaggning_i_vc_och_gransen_3_av_28.md` | M-132 — en riktig anläggning i VC: I/O-spår från en transportörrigg med två givare, och varför produktionen ger 0 till 3 av 28 |
| `M-133_kompositionsdomarna_over_fyra_linjetopologier.md` | M-133 — kompositionsdomarna över fyra nya linjetopologier: kaskadsvält, buffertblockering, sammanflödeskollision och slutet återflöde |
| `M-134_de_29_skadorna_facit_kan_se.md` | M-134 — de skador facit kan se: klassning med saknat påstående och orsak |
| `M-135_stimuli_som_ser_skadorna.md` | M-135 — stimuli som ser skadorna: C2-punktkrav, sekvenser och grind |
| `M-136_llm_informationsatkomst.md` | M-136 — LLM-informationstäckning i skala över 50 bankuppgifter |
| `M-137_domarnas_oenighet_over_inspelade_scener.md` | M-137 — domarnas oenighet över inspelade scener: 74 spår visar att ingen domare är en kopia av en annan |
| `M-138_vad_ogat_inte_kan_se_av_konstruktion.md` | M-138 — vad ögat inte kan se, av konstruktion: produktens ärliga gräns över felklasserna F1–F15 |
| `M-139_universaliteten.md` | M-139 — Universaliteten mätt: kombinationstabell över OS, Python, VC och Wine |
| `M-140_provtagningsfrekvensen_mot_vad_som_ska_ses.md` | M-140 — provtagningsfrekvensen mot vad som ska ses: 11 bankuppgifter ogiltiga vid 17,2 Hz tyst provtagning, full täckning vid 224,7 Hz trafik |
| `M-141_kontextbudgeten_mot_verkligheten.md` | M-141 — Kontextbudgeten mot verkligheten: förhandsreglerna i systemprompten |
| `M-142_millimeter_och_meter_omvandling_bada_hallen.md` | M-142 — millimeter och meter: fullständig inventering av enhetsbyten och stängning av asymmetriska omvandlingar |

<!-- SLUT MATNINGSTABELL -->

## Acceptansprotokoll

En fas är klar först när dess protokoll i `tests/protocol/` är kört
och grönt, inklusive de trasiga fallen.

* `tests/protocol/fas0_testprefix.md`
* `tests/protocol/fas10_paketering.md`
* `tests/protocol/fas1_bryggan.md`
* `tests/protocol/fas2_ogat.md`
* `tests/protocol/fas3_grinden.md`
* `tests/protocol/fas4_apiindex.md`
* `tests/protocol/fas5_verktygen.md`
* `tests/protocol/fas6_plcbandet.md`

Systemdokumentet ligger i repots rot: `SYSTEM.md`.
