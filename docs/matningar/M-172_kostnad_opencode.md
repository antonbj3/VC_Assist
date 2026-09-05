# M-172 — Kostnaden som aldrig mattes: opencode rapporterar kostnad i step_finish

**Datum:** 2026-09-05
**Rigg:**
**Prövar:**

# M-172 — Kostnaden som aldrig mättes: opencode rapporterar kostnad i step_finish

**Datum:** 2026-09-05 (kö B, punkt B5)
**Rigg:** opencode run --format json
**Prövar:** Huruvida `opencode`:s JSON-utdata rapporterar ett kostnadsfält (`cost`), eller om kostnaden måste sättas till `None` för icke-mätta modeller.

## Resultat

Mätning mot `opencode run --format json` med modell visar att JSON-strömmen avger händelser av typen `step_finish`:

```json
{"type":"step_finish","timestamp":1788634031260,"sessionID":"...","part":{"id":"...","reason":"stop","type":"step-finish","tokens":{"total":11527,"input":11331,"output":2,"reasoning":194,"cache":{"write":0,"read":0}},"cost":0.00923325}}
```

- Fältet `part.cost` finns och rapporterar anropets faktiska kostnad i USD som ett flyttal (i testanropet: `0.00923325` USD).
- Repots modellklient uppdateras därför att läsa `info.get("cost")`. Om fältet saknas eller modellen är gratis sätts `cost_usd = 0.0` om mätt, eller `None` om fältet saknas helt.

## LIMITS

* Mätningen gjordes mot `google-vertex/gemini-3.8-flash`. Modeller på gratisnivå (t.ex. Muse Spark contributor free) kan returnera `cost: 0` eller utelämna fältet.
* Tokens och kostnader summeras per anrop i slingan. Eventuell nätverksoverhead och lokala beräkningskostnader ingår inte i API-kostnaden.
