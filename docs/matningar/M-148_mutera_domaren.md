# M-148 — mutera domaren i stället för koden: vilka regler i bank/domare.py kan skadas utan att provsviten märker det

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell.
Testsvit: Alla 33 referenslösningar och motbevis i `bank/uppgifter/`.
**Prövar:** Kö C punkt C8: vänd på mutationstestningen — skada `bank/domare.py`
och undersök om provsviten fångar defekterna. En domare som fortfarande dömer
rätt med en skadad regel bär en regel som aldrig prövas eller som saknar verkan.
**Körs av:** `docs/matningar/radata/m148_mutera_domaren.py`.
Rådata: `docs/matningar/radata/m148_ut.txt`.

## Resultat

Tolv syntaktiskt och semantiskt meningsfulla mutationer applicerades på
kärnlogiken i `bank/domare.py`. Av 12 mutanter fångades **7 (58 %)** och
**5 (42 %)** överlevde utan att ett enda prov reagerade:

| Mutant i `bank/domare.py` | Regel | Utfall | Fällande prov / Orsak |
|---|---|---|---|
| `FLOAT_TOLERANS_NOLL` | `_lika`: `1e-9` → exakt `==` | **ÖVERLEVDE** | Bankens flyttal har bara exakta binära decimaler |
| `BOOL_STRIKT_STRUKEN` | `_lika`: bool-normalisering struken | **ÖVERLEVDE** | ST-tolken levererar redan äkta booleans |
| `PUNKTKRAV_TOLERANS_NOLL` | `dom`: `1e-9` tidstolerans struken | **ÖVERLEVDE** | Alla `t_ms` är heltal på scannätet |
| `INVARIANT_RAPPPORTERA_ALLA_SCAN` | `dom`: `inv_falld.add()` struken | **ÖVERLEVDE** | Sviten testar bara unika felkoder, inte frekvens |
| `FORGRIND_IGNORERAS` | `dom`: `forgrindsbrist` ignoreras | **ÖVERLEVDE** | Spårdomaren anropas alltid med `stationsdom=None` i enhetssviten |
| `SLUTTID_ETT_SCAN_TIDIGARE` | `dom`: `< slut_ms` i stället för `<=` | **FÅNGAD** | `A-02:underkand_skruv_dras_om_automatiskt` missar sista punktkravet |
| `INVARIANT_NAR_ANY` | Invariant-villkor: `all` → `any` | **FÅNGAD** | `C-06` referens fälls på tjuvtriggad luckinvariant |
| `INVARIANT_KRAVER_ANY` | Invariant-krav: `all` → `any` | **FÅNGAD** | `A-03:station_2_startar_pa_narvaron` motbevis fälls inte |
| `FLANK_STRYK_FRAN_MS` | Flankfönster: `fran_ms` borttagen | **FÅNGAD** | `A-01` referens fälls på flank före fönstret |
| `FLANK_RISE_TILL_NIVA` | Flankräkning `RISE`: `v and not p` → `v` | **FÅNGAD** | `A-01` referens fälls (nivå ger 75 flanker i stället för 1) |
| `FLANK_FALL_TILL_NIVA` | Flankräkning `FALL`: `p and not v` → `not v` | **FÅNGAD** | `A-05` referens fälls |
| `M106_OMEDELBAR_FORRA_UPPDATERING` | Uppdatera `forra` inne i loopen | **FÅNGAD** | `A-01` referens fälls (M-106:s regressionsgrind fungerar) |

### §1 Analys av de fem överlevarna (döda eller oprövade regler)

1. **`FLOAT_TOLERANS_NOLL` och `PUNKTKRAV_TOLERANS_NOLL`**:
   Båda toleranserna (`1e-9`) lades till defensivt för att hantera flyttalsavrundning.
   Att de överlever bevisar att bankens referenser och scenarier enbart använder
   enkla tal (t.ex. `120.0`, `0.5`, `30.0`) där IEEE 754 inte ger avrundningsbrus.
   Toleranserna skyddar mot framtida beräknade mått, men är död kod för bankens nuvarande 33 uppgifter.

2. **`INVARIANT_RAPPPORTERA_ALLA_SCAN`**:
   `inv_falld.add(inv["namn"])` ser till att samma invariant bara rapporteras
   en gång per sekvens i stället för i varje scan den är bruten.
   Att mutanten överlever beror på att `test_varje_motbevis_falls_pa_den_brist_det_namnger`
   enbart frågar `if k in d.koder` (mängdtillhörighet bland bristkoderna).
   Om samma brist rapporteras 1 gång eller 50 gånger ändrar varken `Dom.godkand`
   eller mängden unika bristkoder.

3. **`FORGRIND_IGNORERAS`**:
   Förgrindskontrollen (`stationsdom`) är en arkitektonisk länk till `vc_eyes`
   och statisk analys. I rena ST-körningar skickas den aldrig med. Den prövas
   i ett separat isolerat mocktest (`test_en_falld_forgrind_stoppar_spardomen`),
   men i bankens referens- och motbevissvit används den aldrig.

### §2 De fångade reglerna (kärnlogiken)

Kärnan i domaren är mycket hårt bevakad av motbevisen och referenserna:
* **Flankräknaren** (`RISE`/`FALL` och tidsfönster): 100 % fångstgrad. Ändras
  detekteringen från flank till nivå faller referenserna omedelbart på orimligt
  högt flankantal (t.ex. 75 scan på hög nivå tolkas som 75 flanker).
* **M-106-skyddet**: Att uppdatera föregående värde för tidigt (så att andra
  flankkravet i samma sekvens blir blind) fångas direkt av `A-01`.
* **Invarianter**: Logiska operatorer (`all` vs `any`) fångas direkt åt båda
  hållen — `all` i villkoret skyddar referensen från falska larm, `all` i kravet
  tvingar motbevisen att fällas.

## LIMITS

* **Provsviten som användes är bankens 33 uppgifter och motbevis.**
  Enhetstester med syntetiska mock-objekt (som `test_en_falld_forgrind_stoppar_spardomen`)
  ingick inte i svit-loopen för att mäta just vad bankens egna uppgifter fångar.
* **12 utvalda mutationer representerar semantiska regler**, inte slumpmässig
  AST-manipulation. De valdes för att pröva specifika paragrafer i domarkontraktet.
