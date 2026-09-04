# M-72 — kvaternionens ordning avgjord på alla tre axlarna

**Datum:** 2026-09-05 · VC Premium 4.10 · testprefixet, headless `:99`
**Körs av:** `tests/protocol/kor_m72_kvaternionens_ordning.py`
**Anledning:** `M-70` fann att `M-11` mätte på **en enda axel**.

## Tvivlet

`M-11` slog fast att VC ger kvaternionen skalär-först:

```
(x, y, z, w) = (q.Y, q.Z, q.W, q.X)
```

och `ext/vc_addon/vc_assist/oga_provtagning.kvat_fran_vc` står på den tabellen.

Men mätningen gjordes på **ren gir kring Z**. I varje mätpunkt där är
`q.Y = 0` och `q.Z = 0` — alltså exakt de två komponenter tabellen flyttar till
x och y. Datan visade att `q.X` bär skalären och att Z-komponenten hamnar i
`q.W`. Den sa **ingenting** om vilken av `q.Y` och `q.Z` som är x respektive y.

Ett fel där är inte kosmetiskt: en orörd detalj blir en vridning, och ögats
`CARRY SLIPPING` faller på varje körning med en orsak som ser ut att sitta i
scenen.

## Provet

Tre **rena** rotationer, en per axel, med **tre olika vinklar**. Olika vinklar
är inte pynt: med samma vinkel på alla tre går en förväxling mellan två axlar
inte att se, eftersom talen då är identiska.

Facit räknas ur matematiken, inte ur VC. För en rotation θ kring enhetsaxeln
(aₓ, a_y, a_z) gäller skalär-först:

```
q = (cos(θ/2), aₓ·sin(θ/2), a_y·sin(θ/2), a_z·sin(θ/2))
```

Att i stället fråga VC vad VC tycker hade gett ja.

## Utfallet

| Rotation | q.X | q.Y | q.Z | q.W |
|---|---:|---:|---:|---:|
| 30° kring **X** | **0,965926** | **0,258819** | 0,000000 | 0,000000 |
| 50° kring **Y** | **0,906308** | 0,000000 | **0,422618** | 0,000000 |
| 70° kring **Z** | **0,819152** | 0,000000 | 0,000000 | **0,573576** |

cos 15° = 0,965926 · sin 15° = 0,258819
cos 25° = 0,906308 · sin 25° = 0,422618
cos 35° = 0,819152 · sin 35° = 0,573576

Varje rad har exakt två komponenter skilda från noll, och båda stämmer med
facit på nio decimaler.

| | ligger i |
|---|---|
| skalären | `q.X` — samma i alla tre |
| världsaxel **X** | `q.Y` |
| världsaxel **Y** | `q.Z` |
| världsaxel **Z** | `q.W` |

**`M-11`:s tabell är bekräftad på alla tre axlarna.** `kvat_fran_vc` står på
rätt tabell, och slutsatsen vilar inte längre på en axel som inte kunde skilja
fallen åt.

## Två saker mätningen gjorde synliga på vägen

**`vcMatrix` ligger inte i bryggans exec-globaler.** `print(vcMatrix)` ger
`NameError`. Modulen måste importeras — `import vcMatrix` — och den har exakt
ett namn, `new()`. Det stod ingenstans.

**Bryggan tolkar utskriven JSON och lägger den i `result`.** Blir det ingen
JSON står texten kvar i `stdout`. Min första avläsning tog bara `stdout` och
fick tom sträng, alltså *"inget svar"* när svaret faktiskt hade kommit fram —
ett tyst mätfel av precis den sort som fångats fyra gånger tidigare i natt.
Körningen läser nu båda vägarna, i den ordningen.

## Vad som INTE är mätt

* **Bara rena rotationer.** Tre enaxliga fall. En sammansatt rotation kring två
  axlar samtidigt är inte prövad, och det är där en teckenkonvention kan skilja
  sig utan att synas här.
* **Inget tecken är prövat mot en känd riktning.** Provet visar vilken
  komponent som bär vilken axel, inte om rotationen går medurs eller moturs
  enligt någon utomstående konvention.
* **Bara `getQuaternion()`.** `setQuaternion()` är inte prövad, och att läsa
  rätt garanterar inte att skriva rätt.
* **Bara VC 4.10.**
