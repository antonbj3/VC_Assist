# M-03 — bryggans takt och svarstid

**Datum:** 2026-09-04 · `~/.wine-vc-test` · VC Premium 4.10 · Wine 11.16 · headless `:99`
**Mätt av:** `tests/protocol/kor_fas1.py`, steg 13 och 14.

## Två regimer, inte en takt

Pumpen har två lägen. Ett medelvärde över ett blandat fönster är ingen takt —
det är två takter i samma tal. Därför mäts de var för sig.

| Regim | Inställd paus | **Mätt takt** | Period |
|---|---|---|---|
| Under trafik | `delay(0.005)` | **224,7 Hz** | 4,5 ms |
| Tyst | `delay(0.05)` | **17,2 Hz** | 58 ms |

Den tysta takten ligger under de 20 Hz pausen anger. Skillnaden, ~8 ms per
varv, är `tick()`:s eget arbete: `select`, städning och loggning ligger utanför
pausen. Talet som gäller är det mätta, inte det inställda.

Den första mätningen gav 60,97 Hz. Det talet var korrekt räknat och ändå
missvisande — det var 2 s aktiv regim och 8 s tyst i samma kvot.

## Svarstid, tur och retur

| | Första mätningen | Efter den adaptiva pumpen |
|---|---|---|
| Median | 49,93 ms | **9,91 ms** |
| Värsta av 20 | 61,25 ms | **13,45 ms** |

Kravet i `tests/protocol/fas1_bryggan.md` är under 50 ms. Den första mätningen
låg alltså precis på gränsen, och inte av slump.

### Varför medianen låg på nästan exakt en hel period

En klient skickar sin nästa begäran direkt efter att ha fått föregående svar.
Svaret skickas i ett pumpslag. Alltså landar nästa begäran **strax efter** ett
slag och måste vänta nästan en hel period — inte en halv, som en slumpmässig
ankomst skulle ge. Pumpen och klienten faslåser varandra.

Det syns inte i ett medelvärde och det går inte att räkna sig till ur
pumpfrekvensen. Det syntes i att medianen låg på 49,93 ms när perioden var
50 ms.

## Åtgärden

Pumpen är adaptiv: `PAUS_TOM = 0.05`, `PAUS_AKTIV = 0.005`, och det aktiva
fönstret hålls öppet i 2 s efter senaste trafik — även av en ny anslutning,
så första begäran på en färsk anslutning inte betalar hela perioden.

Kostnaden är simulerad tid som går åt till tomma varv under aktiva fönster.
Med `startSimulation()` är simulerad tid samma sak som väggklockstid (M-08),
så det förbrukar inget som en mätning behöver.
