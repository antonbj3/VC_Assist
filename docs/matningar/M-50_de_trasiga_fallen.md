# M-50 — de trasiga fallen, och vad som fällde vad

**Datum:** 2026-09-04 · samma rigg som [M-49](M-49_stationen_arbetar.md)
**Körs av:** `tests/protocol/kor_fas7_station.py`
**Protokollet:** `tests/protocol/fas7_stationen.md`

Protokollet listar sju trasiga fall. T1, T2 och T7 fälldes skarpt i
[M-48](M-48_grind_1_till_4_skarpt.md). Den här mätningen tar de fyra som
protokollet säger att **ögat** ska fälla — T3, T4, T5, T6 — plus facitets
nollpunkt.

Kravet är hårt och står i protokollet:

> T3 till T6 måste fällas av **ögat**, inte av en tidigare grind. Om en statisk
> regel råkar fånga T3 är det inte ett bevis på att ögat fungerar, och fallet
> ska skrivas om tills bara ögat kan se det.

Körningen kör därför grind 1–4 på **varje** fall, även de som väntas falla, och
skriver ut varje grinds egen utdata. Ett fall som faller före ögat är inte ett
resultat — det är ett protokollbrott, och det syns i tabellen.

## Fallen, och vad som skiljer dem från den hela lösningen

Alla fem är **samma program** som `HEL` med **en** ändring. Ändringen görs i
koden med `str.replace` och en `assert` som faller om raden bytt form — en
trasig fixtur som tyst blir hel igen är värre än ingen fixtur alls (mätt i
M-41, där en fixtur läkte sig själv).

| # | Ändringen | Varför den är osynlig för grind 1–4 |
|---|---|---|
| **T3** | `IF flank.Q THEN` → `IF givare THEN` | båda är giltig ST, båda rör bara deklarerade taggar, båda kompilerar. Skillnaden är en nivå mot en flank, och den syns först när produkten fortfarande står kvar på fotocellen efter utmatningen |
| **T4** | `tid(IN := TRUE, ...)` → `tid(IN := flank.Q, ...)` | `flank.Q` är hög en enda scan. Timern startas alltså om av samma villkor som startade den, och når aldrig `PT`. Kompilatorn har ingen åsikt om vilket uttryck som driver en `TON` |
| **T5** | `stopp := FALSE;` → `(* stopp := FALSE; *)` i steg 2, och `stopp := FALSE;` tillagt i steg 3 | förreglingen står som kommentar. Bromsen släpper en rad senare, så bromsen och utmatningen är höga **samtidigt** under hela utmatningspulsen. Ingen deklaration bryts |
| **T6** | `IF NOT kor` lägger till `stopp := FALSE; laget := 0;` | "återställ till vila när linjen står" är en helt rimlig rad. Den gör rätt på varje varv utom det som avbryts mitt i sekvensen |
| **NOLL** | hela kroppen ersatt med två självtilldelningar som rör alla fem taggarna | facitets nollpunkt, rättad av M-48: en **tom** kropp fälls av grind 3 (`ORORD_SIGNAL`), men ett program som rör alla signaler utan att göra något passerar alla fyra förgrindarna |

## Perturbationen får alla fall, inte bara T6

Driftväljaren `kor` slås av i **1,0 s**, 1,0 s in i den andra stoppfasen — lika
för alla sex körningarna. En perturbation som bara det trasiga fallet fick hade
mätt fallet, inte lösningen.

Facit för `kor`: en pausad linje får inte släppa en klämd produkt. `HEL` håller
därför `stopp` och sitt läge under pausen och räknar om processtiden när
linjen går igen. `T6` nollställer i stället läget, och tappar produkten som
stod i stationen.

*(Resultattabellen fylls i av körningen; se nedan.)*
