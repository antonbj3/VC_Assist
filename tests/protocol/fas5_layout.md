# FAS 5 ACCEPTANS — mållayouter i VC

**beskriver:** `svc/vc_assist_svc/layout/`, `ext/vc_addon/vc_assist/`
**kontrakt:** `docs/spec/70_faser.md` — *"N mållayouter byggda: noll kollisioner,
alla gränssnitt kopplade"*
**körs av:** `tests/protocol/kor_fas5_layout.py`

## Status: STÄNGD — 20 av 20, 117 objektpar, noll kollisioner.
Se `fas5_riktiga_komponenter.md`: allt var BLOCK (M-57)

## Varför körningen finns

Layoutmotorn löser scenerna utanför VC och rapporterar noll överlapp över 24
provscener. Det är **dess egen** mätning, gjord med dess egen geometrimodell.

Den här körningen bygger samma layouter i VC med verklig blockgeometri och låter
**VC:s egen geometri** döma, genom `vcNode.measureDistance`. En oberoende
domare på samma fråga.

## Utfall 2026-09-04 — 19 av 19 prov

| Scen | objekt | par | minsta avstånd | anm |
|---|---|---|---|---|
| `T-01` | 3 | 3 | 2829 mm |  |
| `T-02` | 3 | 3 | 1399 mm |  |
| `T-03` | 3 | 3 | 2500 mm |  |
| `T-04` | 3 | 3 | 3701 mm |  |
| `P-01` | 3 | 3 | 526 mm |  |
| `P-02` | 3 | 3 | 1075 mm |  |
| `P-04` | 4 | 6 | 510 mm |  |
| `L-01` | 7 | 21 | 44 mm |  |
| `L-02` | 4 | 6 | 0 mm | stapel |
| `L-03` | 4 | 6 | 1689 mm |  |
| `S-01` | 4 | 6 | 2334 mm |  |
| `S-02` | 4 | 6 | 1500 mm |  |
| `A-01` | 5 | 10 | 470 mm |  |
| `A-03` | 3 | 3 | 4901 mm |  |
| `H-01` | 3 | 3 | 1443 mm |  |
| `C-01` | 8 | 28 | 1851 mm |  |
| `T-01-pelare` | 3 | 3 | 2829 mm |  |
| `TRAVERS` | 2 | 1 | 2309 mm |  |

**117 objektpar mätta, noll kollisioner.** Minsta uppmätta frigång över alla
scener: **0 mm** (L-01). Största: **4901 mm**.

## Det trasiga fallet

Två objekt flyttades medvetet in i varandra. Det fälls: `band+fotocell`.

Utan den raden vore de gröna resultaten ovan värdelösa — precis det som hände i
den första versionen av den här körningen, där kollisionsdetektorn svarade noll
på allt (M-35).

## Ett undantag som kommer ur scenen själv

L-02 är *"två mellanlägg staplade på EUR-pall"*. Två av dess kroppar **nuddar**,
och avståndet är 0,0 mm.

Det är rätt svar. Scenens egna relationer säger `lager_2 står på lager_1`, och en
stapel är ingen kollision. Undantaget läses ur scenens deklarerade `Pa`-relationer
— allt som **inte** är deklarerat stödjande måste ha avstånd större än noll.

Den första versionen fällde L-02, och grinden mätte då fel storhet.

## Mätta förutsättningar

| Vad | Var |
|---|---|
| världen är i millimeter | M-33 |
| block med `Length`/`Width`/`Height` ger verklig geometri | M-33 |
| `vcCollisionDetector` duger **inte** — dess nodlistor töms tyst | M-35, M-36 |
| `measureDistance` kräver `update()` + `sim.update()` mellan flytt och mätning | M-36 |

## Gränssnitt på gränssnittsnivå

Tre par byggda och kopplade i samma körning: `canConnect` sant, `connect` sant,
`IsConnected` sant, och `ConnectedComponent` pekar på rätt granne.

Den saknade bindningen var **`Container`** — flödesfältets referens till sitt
flödesbeteende. Alla tidigare försök band bara `Port`, så fältet pekade på en
port i ingenting och `canConnect` svarade falskt utan att säga varför. Se
[M-37](../../docs/matningar/M-37_granssnitt_gar_att_koppla.md).

## Fas 5 är STÄNGD

| Led i grinden | Läge |
|---|---|
| N mållayouter byggda i VC | **klart**, 18 scener, 117 objektpar |
| noll kollisioner | **klart**, mätt av VC:s egen geometri |
| alla gränssnitt kopplade | **klart**, på gränssnittsnivå |
| trasigt fall fäller | **klart**, `band+fotocell` |

**20 av 20 prov.**

## Vad som fortfarande INTE är prövat

* **Windows.** Allt är kört under Wine.
* **Riktiga katalogkomponenter.** Alla kroppar är block vi byggt själva. En
  transportör ur eCatalog kan bete sig annorlunda.
* **Att något flödar genom kopplingen.** Gränssnitten är kopplade; att en
  produkt vandrar igenom dem är fas 6 och 7, och är öppet (M-34).
