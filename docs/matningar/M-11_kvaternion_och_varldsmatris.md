# M-11 — kvaternionens ordning, och världsmatrisens eftersläpning

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · mätt genom bryggan

Två fynd. Båda är av det slag som förgiftar allt tyst: inget klagar, talen ser
rimliga ut, och domen blir fel.

## 1. VC:s kvaternion är skalär-först

`vcMatrix.getQuaternion()` returnerar en `vcVector` med fyra egenskaper
`X, Y, Z, W`. Namnen inbjuder till att läsa dem som `(x, y, z, w)`. Det är fel.

Mätt genom att sätta en ren gir kring Z och läsa tillbaka ur den **lokala**
matrisen:

| Gir | `q.X` | `q.Y` | `q.Z` | `q.W` | cos(θ/2) | sin(θ/2) |
|---|---|---|---|---|---|---|
| 0° | 1,0000 | 0 | 0 | 0,0000 | 1,0000 | 0,0000 |
| 30° | 0,9659 | 0 | 0 | 0,2588 | 0,9659 | 0,2588 |
| 90° | 0,7071 | 0 | 0 | 0,7071 | 0,7071 | 0,7071 |
| 180° | 0,0000 | 0 | 0 | 1,0000 | 0,0000 | 1,0000 |

`q.X` följer **cos(θ/2)** — det är skalären. Vektordelen ligger i `(Y, Z, W)`.

```
(x, y, z, w) = (q.Y, q.Z, q.W, q.X)
```

Läser man rakt av blir varje vridningsvinkel fel. Vid 0° ger felläsningen
`(1,0,0,0)`, vilket tolkat som `(x,y,z,w)` är en **180-graders vridning** — så
en helt orörd detalj ser ut att ha vänt sig upp och ned. `CARRY SLIPPING`
skulle falla på varje körning, och orsaken hade sett ut att sitta i scenen.

Omräkningen ligger i `oga_provtagning._kvat()` med den här tabellen som skäl.

## 2. `WorldPositionMatrix` släpar ett scenuppdateringssteg

Mätt: sätt `comp.PositionMatrix` och läs omedelbart.

| Vad som lästes | Värde |
|---|---|
| `comp.PositionMatrix.P.X` direkt efter tilldelning | 52,5 |
| `comp.WorldPositionMatrix.P.X` direkt efter | **10,5** |
| efter `sim.update()` | 52,5 |

Tilldelningen tar alltså. Den **lokala** matrisen är omedelbart aktuell. Den
**globala** är det inte.

Vad som hämtar hem den, mätt var för sig i en egen körning:

| Anrop | Världsmatrisen efter |
|---|---|
| `app.render()` | oförändrad (10,5 medan lokal stod på 15,5) |
| `app.flush()` | oförändrad (10,5 medan lokal stod på 20,5) |
| ingenting, bara läs igen | oförändrad (10,5 medan lokal stod på 25,5) |
| **`sim.update()`** | **aktuell** |

Världsmatrisen stod alltså still under hela körningen och uppdaterades först
mellan körningar — av simuleringens eget steg.

### Vad det betyder för ögat

Ett öga som läser `WorldPositionMatrix` efter att ha flyttat något självt
läser gammal data. För provtagning av en simulering som rör sig av egen kraft
är frågan en annan — då sker läsningen inne i simuleringens steg — och den
frågan är **omätt** tills fas 2:s cell körs i VC.

Tills dess: provtagaren anropar `sim.update()` innan den läser, och det är
markerat i koden med hänvisning hit.

## Sidofynd

* `vcMatrix.identity()` kastar `TypeError: function takes exactly 1 argument
  (0 given)`. Bindningen räknar `self`. `setWPR(w, p, r)` fungerar.
* `vcMatrix` finns inte som globalt namn i exec-scopet.
* Matrisobjekt saknar `__getattribute__`; det är C-typer med egen
  attributuppslagning, så introspektion via `getattr` fungerar inte.
* `getAxisAngle()` returnerar en `vcVector` där `W` är vinkeln i **grader**
  enligt medföljande dokumentation.
