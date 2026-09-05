# M-168 — Motbevis som faller på fel sak: revision av bankens och svitens motbevis

**Datum:** 2026-09-05
**Rigg:**
**Prövar:**

# M-168 — Motbevis som faller på fel sak: revision av bankens och svitens motbevis

**Datum:** 2026-09-05 (kö B, punkt B6b)
**Rigg:** pytest 9.0.2 på Python 3.13.11, Ubuntu Linux
**Prövar:**
1. Att bankens motbevis i `bank/uppgifter/*.json` (168 stycken över 49 uppgifter med spårfacit) faller på sina egna deklarerade brister och inte på delade typfel eller oavsiktliga syntaxfel.
2. Varför proven i `tests/motbevis/` fördelar sig på 28 röda och 30 gröna (26 gröna när uppdraget skrevs, 4 tillkomna vid D12/M-143).

## Resultat

### 1. Bankens 168 motbevis

Alla 168 motbevis över bankens 49 uppgifter med spårfacit har reviderats mot `domare.dom(post, mb["st"])`.

- **168 av 168 motbevis fälls.** Inget motbevis går igenom spårfacitet ostraffat.
- **168 av 168 motbevis träffar samtliga koder i `faller_pa`.** Inget motbevis missar sin deklarerade brist.
- **T-04-felet är åtgärdat:** M-121 noterade att tre av T-04:s motbevis föll på typfelet `4.0 * antal` (REAL och INT). I commit `6a93b96` korrigerades detta med `INT_TO_REAL(antal)` i både referensen och de fyra motbevisen. Med typfelet borta fälls alla fem motbevis i T-04 på sina respektive funktionella brister (`raknaren_foljer_flanker`, `overlast_stoppar_inflodet`, `invariant:ingen_kvittens_med_bruten_fotocell`, etc.).
- **En avsiktlig tolkfelsfällning i P-07:** `ridans_signal_tvingas_hog_i_koden` skriver till insignalen `ST460_LGT_CLEAR := TRUE`. Detta fälls av tolkens skydd mot insignalskrivning (`tolkfel:kallstart_utan_sjalvstart`), vilket är exakt vad motbevisets `faller_pa` deklarerar.

### 2. Sviten `tests/motbevis`: 28 röda och 30 gröna

Vid körning av `pytest tests/motbevis` erhålls **28 FAILED** (röda) och **30 PASSED** (gröna). De 30 gröna proven fördelar sig i tre tydliga kategorier:

1. **Hålet är lagat (14 prov):**
   - `test_guldgrind_motbevis.py` (4 prov): Alla 4 prov (`test_en_rapport_utan_en_enda_matning_ar_inte_guld`, `test_en_rapport_utan_HONESTY_sektionen_ar_inte_guld`, `test_en_korning_med_for_fa_prov_ar_inte_guld`, `test_facit_grinden_ger_fortfarande_guld_at_en_riktig_rapport`) är gröna därför att `svc/vc_assist_svc/guldgrind.py` har lagats för att neka rapporter utan mätningar eller ärlighetssektion. Proven bevisar att hålet är tilltäppt och hör hemma i `tests/enhet/` som regressionsprov.
   - `test_skrivgrind_motbevis.py` (8 prov): Dunder-anrop (`__setattr__`, `__setitem__`, `__delitem__`) samt variabla skriptbeteenden i `createBehaviour` fångas nu av `skrivgrind.py`. Endast `shutil.rmtree` och `os.truncate` kvarstår som röda motbevis.
   - `test_dokument_mot_verklighet_motbevis.py::test_readme_beskriver_ett_repo_med_kod_i` (1 prov): README har uppdaterats och innehåller inte längre "Ingen kod byggd ännu".
   - `test_tillverkardatablad_motbevis.py::test_en_nolla_utan_enhet_skrivs_inte_ut_som_0_kg_nagonstans_i_repot` (1 prov): Inga bara nollor skrivs ut som 0 kg längre.

2. **Skrivna som positiva påståenden / verifierade mekanismer (10 prov):**
   - `test_kvaternion_felordning_motbevis.py` (3 prov): Tillkom i uppdrag D12 (M-143). Proven kontrollerar att felaktig kvaternionordning faktiskt fälls i ögat och av kodfallsgrinden FAL-001. Proven assertar `rap_fel.dom[0] == "FAIL"` och `len(skal) > 0`, vilket gör testet grönt när grinden fungerar.
   - `test_grindar_som_aldrig_fallt_motbevis.py` (2 prov): `test_E_QUEUE_FULL_gar_att_utlosa` och `test_kon_svarar_E_QUEUE_FULL_nar_den_ar_full` bevisar att kön faktiskt svarar med `E_QUEUE_FULL`.
   - `test_ogat_honesty_motbevis.py` (4 prov): `test_placeringsgransen_ar_bestamd_av_minst_en_cell`, `test_barstrackans_troskel_ar_bestamd_av_minst_en_cell`, `test_en_rapport_utan_dom_ar_inte_godkand`, `test_blowupgrinden_faller_en_cell_som_bara_bryter_mot_farten`.
   - `test_troskelharkomst_motbevis.py::test_place_tol_mm_provas_av_minst_ett_prov` (1 prov).

3. **Cellisolering bekräftad (2 prov):**
   - `test_ogat_honesty_motbevis.py::test_en_trasig_cell_bryter_mot_exakt_en_felklass[explosion]` och `[aldrig_gripen]`: Bekräftar att dessa två trasiga celler nu isolerar sin felklass utan att smitta andra klasser.

4. **Kompileringsgrind utan VC (1 prov):**
   - `test_textgrindar_motbevis.py::test_kompileringsgrinden_gar_att_prova_utan_att_starta_vc`.

De gröna proven är alltså inte "döda" prov; de är **lagade sårbarheter** och **positiva fixturer** som bevisar att grindarna biter. Enligt `tests/motbevis/README.md` ska de lagade proven successivt lyftas till `tests/enhet/` så att `tests/motbevis/` förbehålls de 28 kvarvarande öppna motbevisen.

## LIMITS

- Revisionen av bankens 168 motbevis kontrollerar att de fälls av vår egen ST-tolk (`domare.py`) och att deras felkoder matchar deras syften. Den prövar inte huruvida OpenPLC Runtime v4 skulle producera samma felkoder under fysisk simulering.
- Att flytta de 30 gröna proven från `tests/motbevis/` till `tests/enhet/` ingår inte i kö B:s mandat (det ändrar svitstrukturen för andra köer som delar repot). Mätningen dokumenterar endast orsakerna bakom utfallen.
