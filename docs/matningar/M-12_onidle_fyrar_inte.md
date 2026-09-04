# M-12 — `vcApplication.OnIdle` fyrar inte

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless `:99`

## Frågan

M-04 slog fast att inget event fyrar när appen står stilla, och därför måste
pumpen bo i simuleringen (M-08). Det bär en följdkostnad som visat sig dyr:
kod som ändrar scenen **stoppar simuleringen**, och pumpens tasklet dödas i
samma ögonblick.

`vc_python_api.json` listar `OnIdle` bland `vcApplication`-händelserna. Om den
fyrar behöver pumpen ingen simulering alls, och hela följdkedjan faller bort.

## Mätt

Ett tillägg med `OnAppInitialized`, `OnStart`, `OnIdle`, `OnRender` och
`OnComponentAdded`, som loggar varje anrop. VC startad headless och lämnad
i fred i 90 sekunder.

```
1788535516.3710 OnStart nr 1
1788535529.7120 OnAppInitialized
```

**Två rader. Noll `OnIdle`. Noll `OnRender`.**

Kroken laddades bevisligen — `OnStart` och `OnAppInitialized` kom fram. Ändå
fyrade `OnIdle` inte en enda gång på 90 sekunder.

| Händelse | Fyrade |
|---|---|
| `OnStart` | ja, en gång |
| `OnAppInitialized` | ja, en gång, **13 s efter** `OnStart` |
| `OnIdle` | **nej** |
| `OnRender` | **nej** |
| `OnComponentAdded` | ingen komponent lades till under mätningen |

## Slutsats

Att en händelse står i dokumentationen betyder inte att den fyrar. `OnIdle`
går inte att använda som klocka, och M-04:s slutsats står kvar: pumpen måste
bo i simuleringen.

`OnRender` fyrade inte heller. Rimlig förklaring är att ingenting ritas i
headless-läge, men det är **omätt** — mätningen säger bara att den inte fyrade
här.

Ordningen `OnStart` före `OnAppInitialized`, med 13 sekunders mellanrum, är
värd att komma ihåg för allt som ska ligga tidigt i uppstarten.

## Vad som INTE är mätt

* Frånvaron är mätt över **90 sekunder**, i en körning, headless. En `OnIdle` som
  fyrar mer sällan än så hade gett exakt samma tomma logg. Mätningen kan inte
  skilja "fyrar aldrig" från "fyrar sällan".
* `OnRender` mättes bara headless. Texten säger själv att förklaringen — att
  ingenting ritas — är omätt, och provet med gränssnittet öppet är inte gjort
  (M-22 i `RESERVERADE.md`).
* Raden för `OnComponentAdded` är ingen mätning av händelsen. Provet innehöll
  inget som kunde fyra den, och det står i tabellen som en notering, inte som ett
  resultat.
* De 13 sekunderna mellan `OnStart` och `OnAppInitialized` kommer ur **en**
  uppstart. Om ordningen och mellanrummet håller över flera starter, eller på en
  annan maskin, är omätt — M-23 i `RESERVERADE.md` är reserverat för just
  uppstartstider och är inte gjort.
* Att kroken *"bevisligen laddades"* vilar på att två andra händelser kom fram.
  Att bindningen av just `OnIdle` lyckades är inte kontrollerat separat; ett
  namnfel i den bindningen hade gett samma logg.
* Slutsatsen *"att en händelse står i dokumentationen betyder inte att den fyrar"*
  är dragen ur ett fall. Hur många av `vc_python_api.json`:s händelser som är
  döda är inte mätt.
