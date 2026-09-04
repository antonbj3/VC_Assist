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

Alla fem är **samma program** som `HEL` med **en** ändring. Ändringen görs med
`str.replace` och en `assert` som faller om raden bytt form — en trasig fixtur
som tyst blir hel igen är värre än ingen fixtur alls (mätt i M-41, där en
fixtur läkte sig själv).

| # | Ändringen | Varför den är osynlig för grind 1–4 |
|---|---|---|
| **T3** | `IF flank.Q THEN` → `IF givare THEN` | båda är giltig ST, båda rör bara deklarerade taggar, båda kompilerar. Skillnaden är en nivå mot en flank |
| **T4** | `tid(IN := TRUE, ...)` → `tid(IN := flank.Q, ...)` | `flank.Q` är hög en enda scan. Timern startas om av samma villkor som startade den och når aldrig `PT`. Kompilatorn har ingen åsikt om vilket uttryck som driver en `TON` |
| **T5** | `stopp := FALSE;` → `(* stopp := FALSE; *)` i steg 2, och `stopp := FALSE;` tillagt i steg 3 | förreglingen står som kommentar. Bromsen släpper en rad senare, så bromsen och utmatningen är höga **samtidigt** under hela utmatningspulsen |
| **T6** | `IF NOT kor` får `stopp := FALSE; laget := 0;` | "återställ till vila när linjen står" är en rimlig rad. Den gör rätt på varje varv utom det som avbryts mitt i sekvensen |
| **NOLL** | hela kroppen ersatt med två självtilldelningar som rör alla fem taggarna | facitets nollpunkt, rättad av M-48: en **tom** kropp fälls av grind 3 (`ORORD_SIGNAL`), men ett program som rör alla signaler utan att göra något passerar alla fyra förgrindarna |

## Två saker facit inte kunde, och som mätningen tvingade fram

### Ordningen ensam ser inte en station som gör om sitt arbete

Första versionen av facit krävde att stegen kom i rätt ordning inom sina
fönster. **T3 passerade den på fem cykler av sex.** Skälet är att en
ordningsdom tar den första flanken som passar och sedan slutar titta — en
station som gör om hela sitt arbete håller ordningen perfekt.

Mätt ur T3:s egen serie, cykel 0 (bromsens flanker, sekunder på ögats axel):

```
Stopp RISE 4.5   FALL 6.5      <- forsta stoppet, som facit ville ha det
Stopp RISE 6.9   FALL 12.0     <- och sa gor den om det
Stopp RISE 12.3  FALL 14.3
Stopp RISE 15.0  FALL 17.0
```

Fyra stopp på **samma** produkt. Facit fick därför en **räkning**: hur många
gånger en signal får gå hög under en cykel (`hogst` i `sekvensdom`). Med den
fälls T3 på **varje** cykel, med talet utskrivet.

### Bara stoppet räknas, inte utmatningen

Räkningen ville först gälla båda ställdonen. Då föll **den hela lösningen** —
och den föll på perturbationen, inte på stationen: en driftpaus mitt i
utmatningen släcker `slapp` och tänder den igen när linjen går, så en helt
riktig lösning matar ut två gånger på just den produkt pausen träffade.
Stoppet har inte det problemet — pausen rör det inte.

En grind som fäller den rätta lösningen på sin egen störning mäter störningen.

## Perturbationen måste landa inne i sekvensen

Driftväljaren `kor` slås av i 1,0 s, lika för alla sex körningarna. En
perturbation som bara det trasiga fallet fick hade mätt fallet, inte lösningen.

Första försöket lade pausen 1,0 s efter att **slingan** såg stoppet gå högt.
Slingan ser det först efter ett kopplarvarv, och det tar ett varv till innan
`kor` når PLC:n — så pausen landade när processtiden redan tagit slut, i
utmatningen i stället för i stoppet. Då är T6 inte skild från HEL, och
perturbationen prövar ingenting.

Pausen läggs nu i den **första stoppfas som börjar efter 25 s**, och den syns i
ögats serie (`ST7_Givare/Kor` är en spårad signal). I den godkända körningen:

```
driftvaljarens flanker:  RISE 0.2 s   FALL 32.3 s   RISE 33.6 s
HEL cykel 3 (t0 = 31.1):  Stopp FALL 5.1 s   (ovriga cykler: 2.5-2.6 s)
```

Processtiden förlängdes alltså med precis pausen, och stationen fortsatte.
Det är facit för `kor`: en pausad linje får inte släppa en klämd produkt.

## Utfallet

*(fylls i av körningen)*
