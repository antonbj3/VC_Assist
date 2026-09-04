# Arv från Isaac Assist

Källa: `~/projects/Omniverse_Nemotron_Ext`, gren `feat/foundation-build`, 2843 commits.
Läst i koden, inte i README.

## Den arkitektoniska sömmen — det viktigaste fyndet

Tjänsten talar **aldrig** med scenen direkt. Den skickar Python-kodsträngar över HTTP
till en RPC-server inne i applikationen, som kör dem på applikationens egen tråd,
en gång per bildruta, med stdout fångad.

**Allt ovanför sömmen är generiskt. Allt under är Kit och USD.**

Det är exakt den sömmen vi återskapar mot VC. Vi behöver tre saker:
en trådsäker kö till VC:s tråd, `exec` med stdout-fångst, och en JSON-rad sist som svarskanal.

## Vad som ärvs, och i vilket skick det är i källan

| Mekanism | Skick i Isaac Assist | Vad vi gör |
|---|---|---|
| Verktygsschema i OpenAI function-calling-form, som ren datalista | **Fungerar.** 448 verktyg | Ärvs rakt av, med VC:s egna namn |
| Delning i data-handlers och kodgeneratorer | **Fungerar.** ~200 av 448 är kodgeneratorer | Ärvs. VC:s modell är metodbaserad, så kodgrenen väger tyngre |
| Semantiskt verktygsurval per tur | **Fungerar.** 20–40 av 448 väljs; alla får inte plats i en prompt | Ärvs när verktygen blir många |
| Tvåfasvalidering av genererad kod före körning | **Fungerar.** 26 regelvalidatorer | Ärvs som mekanism, nya regler |
| Verktygsloop med tak | **Fungerar.** 10 rundor, stopp efter 6 raka misslyckanden | Ärvs |
| **Honesty-rewrite** | **Fungerar.** Påstår svaret framgång medan sista verktyget failade, tvingas omskrivning | Ärvs. Obligatorisk |
| **Verify-contract** | **Fungerar.** Plockar namn och tal ur modellens egen text och kontrollerar dem mot scenen | Ärvs. Starkaste idén i hela repot |
| Kanonmall + lint | **Fungerar.** 526 mallar, 1540 raders linter | Ärvs som bänkstruktur |
| **AST-validering av verktygsanrop mot schemat** | **Fungerar.** Parsar mallens kod, validerar varje kwarg och enum mot schemat | Ärvs. Detta är den starkaste anti-hallucinationen som faktiskt finns byggd |
| Capture/execute i två faser med sandlåda | **Fungerar** | Ärvs |
| Mallhämtning med tröskel **och** marginal mot tvåan | **Fungerar.** 0,45 respektive 0,20 | Ärvs |
| Guldstege L1/L2/kandidat | **Fungerar** som kontrakt | Ärvs |
| Ögat: tät tidsserie ur levande tillstånd | **Fungerar.** 10 Hz, härledd rörelsestatistik | Ärvs, mot VC:s API |
| Grinden parsar ögats egen utdata | **Fungerar.** Doktrin: mät aldrig om | Ärvs. Bärande |
| Hederlighetsgrindar mot omöjliga framgångar | **Fungerar** | Ärvs |
| Turordnings-diff mot vad som faktiskt ändrades | **Fungerar** | Ärvs |

## Vad som var specat men aldrig byggt — och som vi måste bygga

Detta är den viktigaste delen. Tre saker finns som välformad design i källan
men är tomma i praktiken. Två av dem är avgörande för oss.

**1. Dokumentindexet är tomt.** `workspace/rag_index.db` är **0 byte** och saknar
tabellen. Ingen crawler finns, bara en mock-endpoint. Målplattformens egna
biblioteksdokument är alltså aldrig indexerade.

Det är exakt den lucka som mätningen på GX Works3 pekar på: 38 procent kompilering
utan leverantörsdokumentation, 87 procent med. Vi har redan råvaran mätt och parsad:
204 typer, 966 metoder, 1159 egenskaper i `docs/referens/vc_api/vc_python_api.json`.
**Vi fyller indexet på riktigt.**

**2. Godkännandekön finns inte.** `pop_pending_patch` har noll anropare, och alla
riggar sätter `AUTO_APPROVE=true`. Proposalmodellen `PatchPlan`/`PatchAction` är
välformad men tillämpas aldrig; exekveraren är en stub som returnerar `True`.

För ett system som genererar **styrkod** är det inte valfritt. Vi bygger kön.

**3. Byggvägen är inte LLM-författad.** Projektets eget dokument
`LLM_TOOL_USE_SEQUENCE.md` säger rakt ut att produktionsloopen är
hard-instantiate: mallen förexekveras, formgrinden förkörs, byggverktygen filtreras
bort ur schemat, och modellens roll kollapsar till att rapportera ett förberäknat utfall.

Vi ska veta att det är så, och bestämma medvetet var på skalan vi lägger oss.

## Vad som inte bär över

Verktygsnamnen och kodgeneratorernas kroppar. Validatorreglerna, som är rena
USD-patologier. Systempromptens USD-regler. Scenkontextens prim-träd.
Snapshot via USDA-export.
