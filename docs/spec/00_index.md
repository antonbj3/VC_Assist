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
| `60_plc.md` | PLC-benet |
| `70_faser.md` | Faser |
| `80_bank.md` | Bänken |
| `81_mallschema.md` | Mallschema |
| `82_felklasser.md` | Felklasser |
| `83_scenarier.md` | Scenariokatalogen |
| `90_invarianter.md` | Invarianter |
| `95_testprotokoll.md` | Test- och verifieringsprotokoll |
| `96_ingen_skuld.md` | Ingen teknisk skuld |

## Mätningar

Varje påstående i specen är antingen **MÄTT** med en hänvisning hit,
eller märkt **ANTAGET**. Inga tal utan härkomst — kontrollerat av
`tests/enhet/test_troskelharkomst.py`, som också kräver att numret
verkligen finns eller står i `RESERVERADE.md`.

| Nr | Vad som mättes |
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
