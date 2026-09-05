# M-124 — de 23 svaren: facit_spar för bankens sista tredjedel

**Datum:** 2026-09-06 (kö B, punkt B1)
**Prövar:** att varje uppgift utan facit får ett klass-4-facit (människa, ur
uppgiftens egna `scenarios`/`expect`, skrivet före körning) som går igenom
`kor_bankens_facit` utan brister, och att varje referens går grön genom
grindkedjan + matiec + STruC++ + spårfacit (M-121:s ordning).

## Facit

(TODO — en rad per uppgift: källklass, referensens grindstatus, matiec/STruC++.)

## LIMITS

- Denna fil är under arbete; rader ovanför är preliminära tills varje uppgift
  anger härkomst (scenarios+expect-ID:n den är skriven ur).
- Mekanismen mot facit-ur-egen-tolk (`FACIT_UR_EGEN_KOD` i
  `tests/protocol/kor_bankens_facit.py`, låst av
  `test_facit_ur_var_egen_tolk_falls`) fanns före mätningen och är grön
  (19/19 i `test_bankens_facit.py` 2026-09-06) — den är förutsättning, inte resultat.
- Klass 4 är svagast av de fyra första källklasserna: människan kan ha fel.
  Motvikten är att referensen måste gå grön genom grindkedjan och båda
  kompilatorerna.
