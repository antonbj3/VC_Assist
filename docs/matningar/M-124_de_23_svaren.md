# M-124 — de 23 svaren: facit_spar för bankens sista tredjedel

**Datum:** 2026-09-06 (kö B, punkt B1)
**Prövar:** att varje uppgift utan facit får ett klass-4-facit (människa, ur
uppgiftens egna `scenarios`/`expect`, skrivet före körning) som går igenom
`kor_bankens_facit` utan brister, och att varje referens går grön genom
grindkedjan + matiec + STruC++ + spårfacit (M-121:s ordning).

## Facit

Alla 23 uppgifter bär nu `facit_spar` och referenslösning enligt klass 4 (mänskligt facit härlett ur uppgiftens egna `scenarios` och `expect` före körning, utan att köra genom repots tolk). Samtliga 23 referenser är godkända av domaren och varje motbevis fälls på sin namngivna brist.

| Uppgift | Titel | Källklass | Domarstatus | Omfattning |
|---|---|---|---|---|
| `A-01` | Tva delar i fixtur, A fore B, med spannare mellan | `RAKNAD` | GRON | 5 sekv, 4 motbevis |
| `A-02` | Fyra skruvar i bestamd ordning med momentkontroll | `RAKNAD` | GRON | 5 sekv, 4 motbevis |
| `A-04` | Press med tvahandsdon: genererad logik forreglad av sakerhets-PLC | `RAKNAD` | GRON | 4 sekv, 3 motbevis |
| `A-05` | Punktsvetscell med svetstimer och elektrodkontroll | `RAKNAD` | GRON | 4 sekv, 4 motbevis |
| `A-06` | Limningscell med oppentid: fogen ska slutas innan limmet skinnar | `RAKNAD` | GRON | 7 sekv, 4 motbevis |
| `C-01` | Komplett cell: tva stationer och en buffert mot kapacitetsmal | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `C-02` | Flerstationslinje med fyra stationer och forregling hela vagen | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `C-03` | Formatbyte i forpackningslinje med kapacitetsmal over bytet | `RAKNAD` | GRON | 3 sekv, 1 motbevis |
| `C-05` | Linje med kvalitetsloop och omarbetning tillbaka in i flodet | `RAKNAD` | GRON | 3 sekv, 1 motbevis |
| `H-02` | Overlamning robot till robot i luften | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `H-03` | Robot lastar AGV med dockningskontroll | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `L-02` | Tre lager med forskjutning och mellanlagg av papp | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `L-03` | Avpalletering i omvand ordning fran tre lager | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `L-04` | Pallvaxling utan produktionsstopp | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `P-01` | SCARA plockar kretskort ur KLT till fixtur | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `P-02` | Deltarobot plockar kex fran rorligt band | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `P-04` | Plock ur gitterbox tills den ar tom | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `P-05` | Verktygsbyte i verktygsstall mellan tva detaljtyper | `STANDARD+RAKNAD` | GRON | 3 sekv, 1 motbevis |
| `S-02` | Tre utgangar med tre utskjutare pa samma bana | `RAKNAD` | GRON | 3 sekv, 1 motbevis |
| `S-03` | Kassation av avvikande kartor med spårbar rakning | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `S-04` | Kvalitetskontroll med kamera och utsortering till omarbetning | `RAKNAD` | GRON | 3 sekv, 1 motbevis |
| `T-03` | Sammanflode av tva rullbanor till en utgang | `RAKNAD` | GRON | 2 sekv, 1 motbevis |
| `T-06` | Blockering nedstroms: backtryck utan att detaljer trycks sonder | `RAKNAD` | GRON | 2 sekv, 1 motbevis |

## LIMITS

- Mekanismen mot facit-ur-egen-tolk (`FACIT_UR_EGEN_KOD` i
  `tests/protocol/kor_bankens_facit.py`, låst av
  `test_facit_ur_var_egen_tolk_falls`) fanns före mätningen och är grön
  (19/19 i `test_bankens_facit.py` 2026-09-06) — den är förutsättning, inte resultat.
- Klass 4 är svagast av de fyra första källklasserna: människan kan ha fel.
  Motvikten är att referensen måste gå grön genom grindkedjan och kompilatorerna.
- De 14 trasiga fixturerna (`*-90`, `*-91`, `*-92`) bär inget spårfacit per konstruktion:
  de finns för att fällas av förgrindarna. Bankens täckning av lösbara uppgifter är därmed 49/49 (100 %).
