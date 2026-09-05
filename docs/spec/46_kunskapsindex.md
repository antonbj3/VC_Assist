# Kunskapsindexet

Detta är den mekanism som hindrar modellen från att hitta på API-anrop.
I källprojektet är den **specad men tom**: `workspace/rag_index.db` är 0 byte,
ingen crawler finns, bara en mock-endpoint. Här är den primär och byggs på riktigt.

Motiv, mätt utanför projektet: kompileringsgrad 38 procent utan sökning i
leverantörens egen dokumentation, 87 procent med.

## Fyra index, olika sorter

| Index | Innehåll | Form | Byggs av |
|---|---|---|---|
| **API** | VC:s Python-API, exakt | SQLite: namntabell + FTS5 | `vc_python_api.json`, mätt |
| **Hjälpare** | `vcHelpers`-modulerna | samma | `helpers.xml`, `constants.xml` |
| **Katalog** | eCatalog-komponenter | SQLite | genomsökning, fas 4 |
| **Mönster** | kod som bevisligen fungerat | JSONL | skördas ur gröna körningar |

Ingen embedding i API-vägen. Exakt namnuppslag och nyckelordssökning räcker och
är deterministiskt. Embedding används först när katalogen kräver semantisk sökning.

## API-indexets tabeller

```sql
CREATE TABLE api_symbol (
  id INTEGER PRIMARY KEY,
  kind        TEXT NOT NULL,   -- type | method | property | event
  type_name   TEXT NOT NULL,
  name        TEXT NOT NULL,
  signature   TEXT,
  value_type  TEXT,
  access      TEXT,            -- R | RW
  description TEXT,
  vc_version  TEXT NOT NULL    -- "4.10"
);
CREATE UNIQUE INDEX ux_symbol ON api_symbol(vc_version, type_name, kind, name);
CREATE VIRTUAL TABLE api_fts USING fts5(type_name, name, description, content='api_symbol');
```

Byggs av `scripts/build_api_index.py` ur den redan parsade `vc_python_api.json`.
Idempotent: samma indata ger samma databas.

## Tre frågeformer

| Verktyg | Fråga | Svar |
|---|---|---|
| `lookup_api` | exakt namn, till exempel `vcRobotController.moveTo` | signatur, typ, beskrivning, åtkomst |
| `search_api` | fri text, till exempel "minsta avstånd mellan noder" | topp N symboler med relevans |
| `type_surface` | ett typnamn | alla metoder, egenskaper och events på typen |

Svaret från `lookup_api` bär alltid raden:

> Använd namnet exakt som det står. Omformulera det inte.

Ärvt ordagrant ur källans deprecations-index, som är den enda anti-hallucination
som faktiskt är byggd där.

## Fällindexet

Handskrivet, en rad per känd fälla. **Varje rad bär den incident som skapade den.**

```json
{ "id": "TRAP-001",
  "keywords": ["connect", "koordinat", "placering"],
  "rule": "connect() tar aldrig koordinater. Kopplingen ar relationen.",
  "incident": "spec 45_verktyg: modellen far inte rakna geometri",
  "severity": "block" }
```

`severity: block` gör regeln till en grind i validatorn, inte bara en varning.

## Mönsterlagret

Kod som passerat **hela** grindkedjan och fått guld skördas som mönster:
uppgiftstext, kod, vilket scenario, vilken guldnivå. Ärvt ur källan.

Regel: **endast guld skördas.** En kandidat som inte körts i VC får aldrig bli
ett mönster. Annars sprider sig fel.

## Versionsmedvetenhet

Varje symbol bär `vc_version`. Frågor filtreras på den version som körs, avläst
ur installationens egen sökväg. VC 5.0 har Python 3 och delvis annat API;
indexet ska kunna bära båda utan att blanda.

## Reparationer och informationsåtkomst i skala (E3, E4, E13)

Mätt i **M-119** och stängt i **M-136**:

1. **Saknat värde vs noll (E3a):** En nolla i räckvidd eller nyttolast tolkas aldrig som ett mätvärde utan som saknat (`None` / `SAKNAS`).
2. **Specifikationer i uppslag (E3b):** `docs/spec/41_ogat_kontrakt.md` och `docs/spec/50_grindar.md` indexeras vid körning så att grindregler (`RACE`, `MINDIST`, `EDGE` m.fl.) nås i rätt domän.
3. **Fullständiga uppgifter och signalkarta (E3c):** `bench_task` levererar samtliga 23 fält och styrsignaler ur `bank/uppgifter/` är sökbara i `search_catalog`.
4. **Konstantbeskrivningar (E3d):** Samtliga 709 konstanter bär semantisk beskrivning baserad på typfamilj.
5. **Ordsegmentsgräns (E3e):** Rangen `delstrang_namn` kräver ordsegmentsgräns; interna delsträngar klassas `delstrang_inuti_ord` för att undvika falska namnträffar.
6. **Ärvda medlemmar:** Uppslag namnger efterfrågad typ och deklarerar arv tydligt utan instruktionsmotsägelse.
7. **Lokal extraktion (E13):** `install/extraktor.py` extraherar API-dokumentationen direkt ur användarens lokala `Auto Complete/`-mapp, och utgivningsgrinden förbjuder att leverantörsdokumentation distribueras i repot.

## Fas 4:s grind mot detta dokument

1. Indexet innehåller minst de mätta 204 typerna, 966 metoderna och 1159 egenskaperna
2. `lookup_api` på ett känt namn ger exakt signatur
3. `lookup_api` på ett **påhittat** namn ger tomt svar, aldrig en gissning
4. Över N genereringar: **noll** anrop till symboler som inte finns i indexet
