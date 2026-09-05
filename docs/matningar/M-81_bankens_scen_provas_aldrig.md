# M-81 — bänken bär 282 komponenter som ingen körning har bett om

**Datum:** 2026-09-05
**Ursprung:** ett sidofynd i `M-78`/`M-80` — grind 4 svarade *"kandidaten bär
ingen scenkod att validera"* i varje uppgift, i båda varven.

## Fyndet

Fas 9:s körning mäter **halva** kedjan. Modellen ombeds skriva structured text
och ingenting annat, så anropsvalideringen — grind 4 — har aldrig dömt ett enda
verktygsanrop.

Det är inte ett fel i grinden. Den svarar korrekt fail-closed: *"kandidaten bär
ingen scenkod att validera"*. Men följden är att **verktygsbiblioteket aldrig
prövas av bänken**.

## Talen

| | |
|---|---:|
| uppgifter i banken | 51 |
| **uppgifter som bär en scen** | **51 av 51** |
| komponenter att placera, totalt | **282** |
| distinkta URI:er | 55 |
| kopplingar mellan komponenter | **196** |
| **URI:er som går att slå upp i katalogen** | **55 av 55** |

Vanligaste rollerna: robot 28, gripdon 26, band 16, fixtur 9, kamera 9,
närvarogivare 8.

Datan finns alltså, komplett och uppslagbar. Ingen har frågat efter den.

## Verktygen finns också

46 verktyg i domänerna `scene`, `composition` och `transport`. De som behövs för
just den här uppgiften:

| Vad scenen kräver | Verktyg |
|---|---|
| hämta komponenten ur en URI | `load_component` |
| placera den | `set_transform` |
| koppla ihop två | `can_connect`, `connect` |
| kontrollera resultatet | `list_components`, `list_connections`, `get_bounds` |

Bara två av 46 tar en URI (`load_component`, `save_layout`), vilket är rimligt —
resten arbetar på komponenter som redan finns i scenen.

## Vad det betyder

Registret har **121 verktyg**. Bänken mäter noll av dem.

Fas 9:s tal — 0 av 4, sedan 4 av 4 — säger alltså något om modellens förmåga att
skriva **PLC-logik**, och ingenting alls om dess förmåga att **bygga en scen**.
De två är olika färdigheter, och den andra är den som kräver att modellen inte
hittar på API-namn — vilket är hela skälet till att fas 4 byggde ett index över
3444 symboler och att grind 4 finns.

Det står nu i `tests/protocol/fas9_banken.md` under öppna punkter, men det
förtjänar sitt eget tal: **282 placeringar och 196 kopplingar väntar på en
körning som ber om dem.**

## Vad som INTE är mätt

* **Om en modell klarar det.** Den här mätningen räknar vad som finns, inte vad
  någon presterar. Ingen har bett en modell bygga en av de 51 scenerna.
* **Om verktygen räcker.** Fyra verktygstyper täcker uppgiften på papperet.
  Om `set_transform` ensam räcker för att placera ett gripdon på en robots
  verktygsfläns är inte prövat — `M-67` visade att kopplingen är logisk och
  inte flyttar något, så geometrin ligger på anroparen.
* **Om scenerna går att bygga alls.** `fas5_riktiga_komponenter.md` är ett
  utkast som aldrig körts, och `M-61` mätte att komponentens omslutande volym
  **inte** står i filen — 0 lästa av 3201. En layout utan lådor är svår att
  kollisionspröva.
* **Kopplingarnas form.** 196 kopplingar räknade ur `connections`-fältet; om
  varje sådan motsvarar exakt ett `connect`-anrop är inte undersökt.
