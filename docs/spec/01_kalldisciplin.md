# Källdisciplin

Utvecklingstakten i källprojektet är hög och dokumenten hinner inte med.
Mätt: `README.md` ligger 71 dagar efter HEAD, `Docs/` (versalt D) 85 dagar,
och `LLM_TOOL_USE_SEQUENCE.md` skrevs 10 juni med **en enda commit** medan
orkestreraren den beskriver rördes 20 juni.

## Regel

Varje påstående i den här specen bär en av tre stämplar:

| Stämpel | Betyder | Krav |
|---|---|---|
| **KOD@HEAD** | Verifierat i källkod vid aktuell commit | fil + rad |
| **MÄTT** | Kört eller läst på den här maskinen | kommandot som gav svaret |
| **DOK** | Kommer ur ett dokument | filnamn, datum, antal commits |

**Ett DOK-påstående får aldrig ensamt bli ett designbeslut.** Det ska
antingen bekräftas mot kod och stämplas om till KOD@HEAD, eller stå kvar
märkt DOK med sitt datum så att läsaren ser att det är obekräftat.

## Dokumentens ålder i källprojektet (mätt, HEAD = 2026-06-25)

| Dokument | Senast rörd | Commits | Bedömning |
|---|---|---|---|
| `docs/notes/LLM_FLOW_SIMULATION_PROTOCOL.md` | 2026-06-17 | 7 | färskast |
| `docs/notes/LLM_TOOL_USE_SEQUENCE.md` | 2026-06-10 | 1 | skriven en gång, aldrig reviderad |
| `docs/notes/MASTER_EXECUTION_PLAN.md` | 2026-06-10 | 4 | |
| `docs/specs/2026-05-15-canonical-flow-standardization-spec.md` | 2026-05-17 | 2 | gitignorerad, följer inte med repot |
| `README.md` | 2026-04-15 | 11 | **71 dagar efter koden.** Påstår torrkörningsdialoger som inte finns |
| `Docs/06_PATCH_PLANNER.md`, `Docs/07_APPROVAL_ENGINE.md` | 2026-04-01 | 1 | **85 dagar.** Äldre produktgeneration |

## Omprövade påståenden

| Påstående | Stämpel | Utfall |
|---|---|---|
| Tjänsten talar aldrig direkt med scenen, utan via kodsträngar över HTTP | KOD@HEAD | `kit_tools.py:66-91`, `kit_rpc.py` |
| 448 verktyg i OpenAI-schema | MÄTT | `grep -c '"type": "function"'` |
| Dokumentindexet är tomt | MÄTT | `workspace/rag_index.db` = 0 byte |
| Godkännandekön töms aldrig | KOD@HEAD | `pop_pending_patch`, noll anropare |
| `AUTO_APPROVE` default | KOD@HEAD | `kit_tools.py:75` — default **`"false"`**. Rättar tidigare påstående |
| Byggverktygen filtreras bort efter instantiering | KOD@HEAD | `canonical_instantiator.py:74`, `orchestrator.py:1186-1190` |
| "Produktionsloopen är hard-instantiate, LLM rapporterar bara" | DOK 2026-06-10 (1 commit) | **mekanismen** är bekräftad i kod; **tolkningen** står kvar som DOK |
