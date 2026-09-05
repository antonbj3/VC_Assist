# M-110 — tillförlitligheten i skala: flerskott, enskott och vart varven tar vägen

**Datum:** 2026-09-06
**Rigg:** Värdmaskinen, headless, modell via `claude`-CLI (`--modell sonnet`), Visual Components startas aldrig
**Prövar:** Operatörens krav *"100% reliable structured text, preferably oneshotted"* — M-96:s tal (0/20 enskott, 3/4 flerskott) vilade på 4 uppgifter; banken har nu 21 med `facit_spar`

## Armar (en commit per arm, namngiven --json per arm)

1. Flerskott: `kor_fas9_slingan.py --lage historik --json m110_flerskott_historik.json`
2. Enskott med regler: `--max-varv 1 --upprepa 5 --json m110_enskott_med_regler.json`
3. Enskott utan förhandsregler: `--max-varv 1 --upprepa 5 --utan-forhandsregler --json m110_enskott_utan_regler.json`
4. Takslagare med `--max-varv 8` (se §3 i uppdraget; `ABSOLUT_TAK` 20 höjs inte)

## Resultat

### Arm 1 (flerskott historik, Sonnet) — BLOCKERAD, ingen mätdata 2026-09-06

- Kommando: `python3 tests/protocol/kor_fas9_slingan.py --lage historik --json docs/matningar/m110_flerskott_historik.json` (exit 1).
- Utfall: **21 av 21 KORNINGSFEL**, `lost 0 av 21`, kostnad **0.000 USD**. Orsak: `Modellfel('claude gav slutkod 1: ')` på varje uppgift — repots enda modellklient är `claude -p` (`svc/vc_assist_svc/modellklient.py:71`) och CLI:t svarar `Not logged in · Please run /login` i denna miljö. Inget anrop nådde modellen; inget är mätt, inget är förbrukat.
- Alternativen är avvisade: `InspeladModell` är en inspelning (vore attrappstal, fail-closed gäller), Ollama finns som env-namn men ingen klient för den i repot — att bygga en ny klient mitt i mätningen vore att byta apparat (§4).
- Nästa steg kräver inloggat `claude` (operatörens miljö) eller besked om annan väg. Armarna 2–4 körs inte förrän arm 1 kan nå modellen — att bränna armar mot en död klient ger bara fler nollfiler.

### Arm 1b (flerskott historik, Muse Spark) — EGEN ARM, pilot 2/2 2026-09-06

- Apparat: `tests/protocol/kor_fas9_musespark.py` (OpencodeCLI + OpencodeModell, modell `opencode/muse-spark-1.3-contributor-free`). Samma promptbygge/grindar/JSON som sonnet-armen; spärren är treskiktad (tempkatalog utanför repot + inga bilagor/sökvägar + fail-closed på verktygshändelser). Svagare än Claudes flaggspärr — ett medvetet, dokumenterat avsteg.
- Transporttillägg (konstant i armen): "Svara med enbart kodens rader som vanlig text. Använd inga verktyg, läs inga filer, kör ingen kod."
- Kostnad: 0 USD (gratisnivå); i stället mäts tokens in/ut per uppgift.
- Pilot (`m110_pilot_musespark.json`): S-05 LÖST efter 2 varv (30 599/1 798 tok, 90 s), T-07 LÖST efter 2 varv (28 359/749 tok, 144 s). T-07 slog i taket (4 varv) på Sonnet i M-96 — på Muse Spark räckte 2. Inga verktygslarm (larmet hade gett KÖRNINGSFEL, inte tyst godkännande).
- Dessa tal jämförs ALDRIG med M-96:s Sonnet-tal.

## LIMITS

- Denna fil är under arbete; tal ovanför är preliminära tills varje arm anger bankens storlek vid körning (banken växer under dagen — cellagenten arbetar vidare).
- Vid körstart: 21 uppgifter med `facit_spar` (A-08 C-04 C-06 H-01 H-04 H-05 L-05 L-06 L-07 P-06 P-07 S-05 S-06 S-07 T-01 T-02 T-04 T-05 T-07 T-08 T-09) — en mer än session B:s lista (P-06 tillkom).
- n = 1 per uppgift räcker inte för förbättringspåståenden (se §4 i uppdraget); spridning kräver `--upprepa`.
- En modell, en promptformulering per arm — byts någotdera är det en ny mätning.
- Domen kommer ur vår ST-tolk, korsprövad mot STruC++ men inte mot OpenPLC.
- Körningar kostar pengar och kvot — ingen arm körs om av misstag; varje arm har egen --json.
