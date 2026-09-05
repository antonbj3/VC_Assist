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

(TODO — andel per uppgift, inte bara summor.)

## LIMITS

- Denna fil är under arbete; tal ovanför är preliminära tills varje arm anger bankens storlek vid körning (banken växer under dagen — cellagenten arbetar vidare).
- Vid körstart: 21 uppgifter med `facit_spar` (A-08 C-04 C-06 H-01 H-04 H-05 L-05 L-06 L-07 P-06 P-07 S-05 S-06 S-07 T-01 T-02 T-04 T-05 T-07 T-08 T-09) — en mer än session B:s lista (P-06 tillkom).
- n = 1 per uppgift räcker inte för förbättringspåståenden (se §4 i uppdraget); spridning kräver `--upprepa`.
- En modell, en promptformulering per arm — byts någotdera är det en ny mätning.
- Domen kommer ur vår ST-tolk, korsprövad mot STruC++ men inte mot OpenPLC.
- Körningar kostar pengar och kvot — ingen arm körs om av misstag; varje arm har egen --json.
