# Ingen teknisk skuld

Reglerna nedan är inte allmänt tyckande. Var och en motsvarar **skuld jag mätte
i källprojektet**, och var och en har en mekanisk kontroll.

## Regler och deras mätta ursprung

**S1. En ofärdig väg kastar, den returnerar aldrig framgång.**
Mätt: `UsdPatchExecutor.set_property` är en stub som returnerar `True` utan att
göra något. En stub som ljuger om framgång är värre än ingen stub.
*Kontroll:* linter avvisar `return True` i en funktion vars kropp saknar verkan.

**S2. En detektor som inte kan fyra är ett fel, inte en varning.**
Mätt: `arm_collides_with_bin_walls` läser nycklar som händelsekällan aldrig sätter.
Grinden var strukturellt död och släppte alltid igenom.
*Kontroll:* varje grind måste ha en trasig fixtur som fäller den. Se `95_testprotokoll.md`.

**S3. Ingen kod utan konsument.**
Mätt: `pop_pending_patch` har noll anropare; kön töms aldrig. 33 av 270 skript
saknar extern referens.
*Kontroll:* `scripts/check_reachability.py` listar symboler och filer utan
referens. Ny föräldralös fil bryter bygget. Ingångspunkter deklareras i en manifestfil.

**S4. Ersatt kod tas bort, den etiketteras inte.**
Mätt: en enda fil har raderats under `scripts/` på 2843 commits. Positionsproxyn
förklarades ljuga men underhölls vidare. En hel domarbaserad QA-generation ligger
kvar och ser aktuell ut.
*Kontroll:* när något ersätts ska samma commit ta bort det ersatta. Kan det inte
tas bort ska det flyttas till `attic/` med en rad om varför.

**S5. Ett index som är tomt är inte ett index.**
Mätt: `rag_index.db` är 0 byte, ingen crawler finns, bara en mock-endpoint.
*Kontroll:* fas 4:s grind kräver ett minsta antal poster och att ett påhittat
namn ger tomt svar.

**S6. Ingen tröskel utan härkomst.**
Mätt: fyra tal i `scene_eyes` saknar motivering.
*Kontroll:* linter kräver en kommentar med mätreferens intill varje numerisk konstant
i analyskod.

**S7. Dokument som beskriver kod namnger filen och stämplas.**
Mätt: `README` ligger 71 dagar efter koden och påstår funktioner som inte finns.
*Kontroll:* varje dokument bär `beskriver:` med filsökvägar. En kontroll jämför
dokumentets datum mot filernas och varnar vid drift över 14 dagar.

**S8. Ingen TODO utan datum och ägare.**
*Kontroll:* linter avvisar bar `TODO`. Formen är `TODO(2026-09-04, fas 6): text`.

**S9. Inga tysta undantag.**
Mätt: ett `NameError` under ett brett `except` gjorde att en fix aldrig fyrade,
tyst, i källprojektet.
*Kontroll:* linter avvisar `except:` och `except Exception:` utan loggning eller
återkastning.

**S10. En rapport får aldrig kunna fälla domaren.**
Mätt: `nj` sätts bara i en gren men används i en annan; artikulationsfel plus en
viss attributkombination ger `NameError` som fäller hela analysen.
*Kontroll:* analysfunktionerna är rena och prövas på syntetiska serier med
saknade fält, L1.

## Vad som gäller vid tidspress

Skulden tas inte. Om något inte hinner bli klart **levereras det inte**, och
fasen står kvar som öppen. En öppen fas är ärlig. En stängd fas med en stub är
en lögn som kostar tre gånger mer senare.
