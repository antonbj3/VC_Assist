# M-110 — tillförlitligheten i skala: flerskott, enskott och vart varven tar vägen

**Datum:** 2026-09-06
**Rigg:** Värdmaskinen, headless, modell via `claude`-CLI (`--modell sonnet`), Visual Components startas aldrig
**Prövar:** Operatörens krav *"100% reliable structured text, preferably oneshotted"* — M-96:s tal (0/20 enskott, 3/4 flerskott) vilade på 4 uppgifter; banken har nu 21 med `facit_spar`

## Armar (en commit per arm, namngiven --json per arm)

1. Flerskott Sonnet: `--lage historik --json m110_flerskott_historik.json` — BLOCKERAD (claude ej inloggad).
2. Flerskott Muse Spark: HELA BANKEN (26) körd — skärvor A/B/C + pilot, se tabell. Banken växte 21→26 under dagen (A-03 A-07 L-01 P-03 S-01 tillkom) — varje JSON bär `bank_vid_start`.
3. Enskott med/utan regler (Muse Spark): EJ KÖRDA — beslutas av operatören (motivering i LIMITS).
4. Takslagare `--max-varv 8`: KLAR för L-06, C-04; H-01 obestämd (2 försök: timeout + verktygslarm).

## Resultat

### Arm 1 (flerskott historik, Sonnet) — BLOCKERAD, ingen mätdata 2026-09-06

- Kommando: `python3 tests/protocol/kor_fas9_slingan.py --lage historik --json docs/matningar/m110_flerskott_historik.json` (exit 1).
- Utfall: **21 av 21 KORNINGSFEL**, `lost 0 av 21`, kostnad **0.000 USD**. Orsak: `Modellfel('claude gav slutkod 1: ')` på varje uppgift — repots enda modellklient är `claude -p` (`svc/vc_assist_svc/modellklient.py:71`) och CLI:t svarar `Not logged in · Please run /login` i denna miljö. Inget anrop nådde modellen; inget är mätt, inget är förbrukat.

### Arm 1b: apparat (Muse Spark via `opencode run`)

- Apparat: `tests/protocol/kor_fas9_musespark.py` (OpencodeCLI + OpencodeModell, modell `opencode/muse-spark-1.3-contributor-free`). Samma promptbygge/grindar/JSON som sonnet-armen; spärren är treskiktad (tempkatalog utanför repot + inga bilagor/sökvägar + fail-closed på verktygshändelser). Svagare än Claudes flaggspärr — ett medvetet, dokumenterat avsteg.
- Transporttillägg (konstant i armen): "Svara med enbart kodens rader som vanlig text. Använd inga verktyg, läs inga filer, kör ingen kod."
- Kostnad: 0 USD (gratisnivå); i stället mäts tokens in/ut per uppgift.
- Pilot (`m110_pilot_musespark.json`): S-05 LÖST efter 2 varv (30 599/1 798 tok, 90 s), T-07 LÖST efter 2 varv (28 359/749 tok, 144 s). T-07 slog i taket (4 varv) på Sonnet i M-96 — på Muse Spark räckte 2. Inga verktygslarm (larmet hade gett KÖRNINGSFEL, inte tyst godkännande).
- Lärdom från avbruten fullarm samma dag: `kor_fas9_slingan.py`-familjen skrev JSON först i slutet — en avbruten körning tappade ~10 lösta uppgifter. `kor_fas9_musespark.py` flushar nu JSON efter varje uppgift och skriver `bank_vid_start` (banken växer under dagen).
- Dessa tal jämförs ALDRIG med M-96:s Sonnet-tal.

### Arm 1b: flerskott historik, Muse Spark — 25 av 26 LÖST (2026-09-06)

Bästa utfall per uppgift (tak 4 om inget annat står). Källa per rad står i JSON:en.

| uppgift | utfall | varv | tokens in/ut | s | källa |
|---|---|---|---|---|---|
| A-03 | LÖST | 2 | 29 891/1 352 | 254 | ms_A |
| A-07 | LÖST | 3 | 47 925/3 055 | 311 | ms_A |
| A-08 | LÖST | 3 | 47 194/1 802 | 283 | ms_A |
| C-04 | LÖST | 3 | 55 077/2 145 | 364 | tak8 (TAK-4 i ms_A, se §2) |
| C-06 | LÖST | 1 | 1 677/1 183 | 125 | ms_A |
| H-01 | TAK | 4 | 49 248/2 152 | 1 024 | full2 (tak8 obestämd, se §2) |
| H-04 | LÖST | 1 | 14 162/654 | 84 | ms_A |
| H-05 | LÖST | 1 | 14 015/468 | 196 | ms_A |
| L-01 | LÖST | 4 | 59 821/2 551 | 329 | ms_B |
| L-05 | LÖST | 2 | 28 817/895 | 150 | ms_B |
| L-06 | LÖST | 4 | 64 088/2 849 | 399 | tak8 (TAK-4 i ms_B, se §2) |
| L-07 | LÖST | 1 | 14 249/623 | 149 | ms_B |
| P-03 | LÖST | 2 | 29 996/1 317 | 249 | ms_B |
| P-06 | LÖST | 4 | 63 820/2 526 | 407 | ms_B |
| P-07 | LÖST | 3 | 48 175/1 508 | 388 | ms_B |
| S-01 | LÖST | 4 | 63 320/3 303 | 360 | ms_B |
| S-05 | LÖST | 2 | 30 599/1 798 | 90 | pilot |
| S-06 | LÖST | 2 | 30 900/2 339 | 287 | ms_C |
| S-07 | LÖST | 3 | 48 337/2 175 | 202 | ms_C |
| T-01 | LÖST | 2 | 15 920/780 | 179 | ms_C |
| T-02 | LÖST | 3 | 46 416/1 870 | 703 | ms_C |
| T-04 | LÖST | 3 | 44 556/1 699 | 317 | ms_C |
| T-05 | LÖST | 2 | 31 284/1 080 | 323 | ms_C |
| T-07 | LÖST | 2 | 28 359/749 | 144 | pilot (slog i taket på Sonnet i M-96) |
| T-08 | LÖST | 4 | 63 585/1 334 | 310 | ms_C |
| T-09 | LÖST | 2 | 29 219/1 016 | 128 | ms_C |

Summerat (bästa försöken): **25 av 26 LÖST (96%)**, varvfördelning {1:4, 2:9, 3:7, 4:5}, **median 2 varv**. Tokens ≈ 950k in / 41k ut, kostnad 0 USD (gratisnivå), modellsekunder ≈ 6 700 s (~1,9 h). Ingen uppgift behövde mer än 4 varv när den väl löste sig.

### §2: vart tog takslagens varv vägen (3 uppgifter, 12 varv lästa)

- **L-06** (TAK-4 i ms_B, löst i 4 med tak 8): v1 fel FB-ingång (`RESET` i st f `R` — verklig brist, grindens fällning korrekt), v2 12 brister (framsteg), v3 6 brister (framsteg), v4 6 brister kvar efter omstrukturering (stagnation — bytte guards utan effekt).
- **C-04** (TAK-4 i ms_A, löst i 3 med tak 8): 41→15→7→5 brister — monotont framsteg, alla verklig brist (kallstart-kvittering, nödstopp-steg). Taket var slut på varv, inte fastlåsning.
- **H-01** (TAK-4 i full2): v1 6 brister (verklig), v2 6→13 regression (oscillation — lagningen bröt mer), v3 13→8 (framsteg), v4 BALANS-fel `END_PROGRAM` som avslutar ett IF (format — programskelettet, samma felklass som M-96:s `ä`).
- **Uppdragets viktigaste tal: 1 av 12 takvarv (8%) var format eller falsk rödgrind — 1 format (H-01 v4), 0 falska rödgrindar.** Resten: 9 verklig brist med framsteg, 1 stagnation, 1 oscillation. Till skillnad från M-96:s T-07 (2 av 4 varv till ett `ä`) är vägen till enskott här INTE kort via formatgrindar — bristerna är i huvudsak verkliga. Formatgenomgång över ALLA armens domar (sök efter staket/ASCII/F1-formatmarkörer): 0 träffar utöver H-01 v4.

### §3: hur många varv behövs egentligen

- C-04: löst efter **3** (tak 8). L-06: löst efter **4**. Inget behövde 5–8.
- H-01: **obestämd** — 2 tak8-försök föll på transporten (timeout 600 s; verktygslarm), inte på uppgiften. `ABSOLUT_TAK` (20) är orört.
- Taket 4 räckte i 23 av 25 lösta direkt; 2 behövde omtag med samma tak (C-04, L-06 löstes i nystartade försök ≤4). Ingen evidens för att tak >4 systematiskt behövs — men n=1 per uppgift, spridningen är omätt.

### Transportflagnande: H-01 (eget fynd)

H-01 krävde 8 slingförsök: 3 tomma modellsvar, 2 timeouter (600 s), 1 verktygslarm, 2 genomförda (varv1-sond TAK-1; full2 TAK-4). Direktsond med exakt samma fråga gav 1 176 tecken ST utan fel — felet är intermittent, inte uppgiftsspecifikt innehåll. Övriga 25 uppgifter gick första försöket (utom C-04: 1 tomt svar, sedan TAK-4, sedan löst). Verktygslarmet på H-01 visar att sparren håller fail-closed: KÖRNINGSFEL i klartext, aldrig tyst godkännande.

## LIMITS

- Bankstorlek per del: pilot 2 + skärva A 8 + skärva B 8 + skärva C 8 = 26 unika uppgifter (full bank vid körtillfället: A-03 A-07 A-08 C-04 C-06 H-01 H-04 H-05 L-01 L-05 L-06 L-07 P-03 P-06 P-07 S-01 S-05 S-06 S-07 T-01 T-02 T-04 T-05 T-07 T-08 T-09). Banken växer under dagen — talen gäller banken 2026-09-06.
- n = 1 per uppgift: spridning omätt; ingen förbättrings- eller försämringsjämförelse mot M-96 görs (annan modell).
- Enskott med/utan förhandsregler: EJ KÖRDA på Muse Spark (kräver 2×26×5≈260 modellsvar; avvaktar operatörens prioritering).
- Sonnet-armarna (flerskott + enskott + utan-regler): BLOCKERADE på `claude`-login i denna miljö.
- H-01 tak8: obestämd (transport, ej uppgift). Domen kommer ur vår ST-tolk, korsprövad mot STruC++ men inte mot OpenPLC.
