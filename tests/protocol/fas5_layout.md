# FAS 5 ACCEPTANS — mållayouter i VC

**beskriver:** `svc/vc_assist_svc/layout/`, `svc/vc_assist_svc/verktyg/scen.py`
**kontrakt:** `docs/spec/70_faser.md` — *"N mållayouter byggda: noll kollisioner,
alla gränssnitt kopplade"*
**körs av:** `tests/protocol/kor_fas5_layout.py`

## Varför körningen finns

Layoutmotorn löser scenerna utanför VC och rapporterar noll överlapp över 24
provscener. Det är **dess egen** mätning, gjord med dess egen geometrimodell.

Den här körningen bygger samma layouter i VC med verklig blockgeometri och låter
**VC:s** kollisionsdetektor döma. En oberoende domare på samma fråga.

## Utfall 2026-09-04 — UNDERKÄNT

| Prov | Utfall |
|---|---|
| T-01 … T-04 byggda i VC, 3 objekt var | byggda |
| kollisioner rapporterade av VC | 0 i alla fyra |
| **trasigt fall: två objekt medvetet i varandra** | **0 kollisioner** |

Det trasiga fallet fäller körningen, och det ska det.

En detektor som svarar noll på ett 900 mm överlapp svarar noll på allt. De fyra
gröna raderna ovan är därför **inga bevis** — de hade sett likadana ut om alla
objekt stått på samma koordinat.

Detaljerna, och allt som prövats, står i
[M-35](../../docs/matningar/M-35_kollisionsdetektorn_fyrar_inte.md).

## Vad som ÄR visat

| Led | Läge | Belägg |
|---|---|---|
| komponenter med verklig geometri | **klart** | block med `Length`/`Width`/`Height`, bounds stämmer (M-33) |
| motorns koordinater applicerade i VC | **klart** | fyra scener byggda utan fel |
| noll kollisioner | **kan inte avgöras** | domaren fäller ingenting (M-35) |
| gränssnitt kopplade | **halvt** | kontaktnivå fungerar, gränssnittsnivå inte (M-17) |

## Nästa mätning

Hypotesen i M-35: `vcCollisionDetector` ärver en layoutpost och kan behöva
ligga **i** layouten för att utvärderas, eller bara utvärderas medan
simuleringen stegar. Pröva båda.

Fasen är **inte** stängd, och den står öppen på en mätt orsak i stället för på
en gissning.
