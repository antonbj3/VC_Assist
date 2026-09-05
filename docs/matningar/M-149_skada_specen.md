# M-149 — skada specen: krav i expect som referenslösningen inte provar

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell.
Provade uppgifter: `A-03`, `P-03`, `S-07`, `C-04`, `T-04`.
**Prövar:** Kö C punkt C9: skada kraven i uppgiftens `expect` och kontrollera
om referenslösningen då blir röd. Om den förblir grön prövar uppgiften inte det
kravet — och kravet står i specifikationen utan att någonsin mätas.
**Körs av:** `docs/matningar/radata/m149_skada_specen.py`.
Rådata: `docs/matningar/radata/m149_ut.txt`.

## Resultat

### §1 Uppmätt utfall: 50 % av spec-skadorna är helt osynliga

Sex olika skador i `expect` provades systematiskt över fem uppgifter (30 tester totalt).
För varje skada provades dels om spårdomaren (`domare.dom`) fäller referensen,
dels om schemavalideraren (`schema.validera`) avvisar uppgiften:

| Skada i `expect` | Avsikt | Spårdomare | Schemavaliderare | Slutresultat |
|---|---|:---:|:---:|---|
| `THROUGHPUT_ORIMLIG` | `throughput_per_h = 999999.0` | **GRÖN** | **GRÖN** | **Kravet mäts aldrig** |
| `MIN_CLEARANCE_5M` | `min_clearance_mm = 5000.0` | **GRÖN** | **GRÖN** | **Kravet mäts aldrig** |
| `MUST_PASS_EMPTY` | `must_pass = []` | **GRÖN** | **GRÖN** | **Kravet mäts aldrig** |
| `MAX_COLLISIONS_MINUS` | `max_collisions = -1` | **GRÖN** | **RÖD** | Fälls av schemat (strukturellt) |
| `FORBIDDEN_LINE_WILDCARD`| `forbidden_lines = [{"template": "*"}]` | **GRÖN** | **RÖD** | Fälls av schemat (strukturellt) |
| `VERDICT_FAIL` | `verdict = "FAIL"` | **GRÖN** | **RÖD** | Fälls av schemat (strukturellt) |

**Huvudfyndet:**
1. **Spårdomaren reagerar i 0 av 30 fall (0 %):** Referenslösningen förblir
   100 % grön mot varje tänkbar ändring i `expect`. `domare.dom` läser inte
   fältet `expect` över huvud taget.
2. **Schemat fångar bara metakontroller:** Ogiltiga negativa tal och wildcard-regler
   avvisas av `schema.validera`, men rimliga numeriska värden accepteras villkorslöst.
3. **De tre fysiska kraven (`throughput`, `clearance`, `must_pass`) är helt omätta:**
   Att kräva en miljon detaljer per timme eller fem meters fritt avstånd i en
   kompakt robotcell ändrar varken schemats eller domarens dom.

### §2 Varför kravet står i specen utan att mätas

Orsaken är arkitekturell och bekräftar KO_C:s frågeställning:
* `expect` är specifikationen för ögonrapporten (`OGAT`) i en simulerad Visual
  Components-scen. Den tolkas av `svc/vc_assist_svc/plan/forfining.py` och
  `ogonverktyg.py` när VC körs (vilket enbart kö D gör).
* Bänkens ST-verifiering kör enbart `facit_spar` genom tolkens virtuella scan.
* Kapacitet (`throughput_per_h`) och geometri (`min_clearance_mm`) i `expect`
  är därför **helt frikopplade från PLC-styrlogiken**.
* För en utvecklare eller språkmodell som läser uppgiften ser `expect` ut som
  ett kontrakt, men för PLC-bänken är det ren dekoration.

Ett krav som står i specen utan att mätas är en form av teknisk skuld (regel S6 och S7).
Om kapacitet ska krävas av ST-koden måste takten uttryckas som tidsintervall
mellan signaler i `facit_spar.sekvenser` (så som `T-05` och `A-03` gör med sina
scancykler) — inte som ett passivt heltal i `expect`.

## LIMITS

* **Provningen gjordes mot spårdomaren och schemat.** Den gjordes inte
  i en körande Visual Components-simulering (ögonrapport). I en verklig VC-körning
  skulle `min_clearance_mm: 5000.0` fällas av ögat om scenen inte har 5 meter fritt utrymme.
* **Fem uppgifter provades.** Alla 33 uppgifter delar samma schema och samma
  spårdomare, så resultatet generaliserar strikt till hela banken.
