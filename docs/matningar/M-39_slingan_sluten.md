# M-39 — handskriven ST styr scenen; slingan sluten och mätt

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · OpenPLC v4 · headless
**Stänger:** fas 6:s grind — *"Handskriven ST styr scenen genom OPC UA. Tur och
retur mätt i ms."*

## Kedjan som mättes

M-20 mätte PLC-halvan. M-38 mätte att VC:s Python **inte** når OPC UA, men att
bryggan når scenens signaler. Den här mätningen sluter slingan genom tjänsten:

```
scenens givarsignal  ->  kopplaren  ->  OPC UA  ->  PLC:ns logik
                     <-  kopplaren  <-  OPC UA  <-
scenens donsignal
```

Programmet är handskrivet structured text, kompilerat av STruC++ och kört av
OpenPLC v4:

```
PROGRAM ST010
VAR
    matin AT %IX0.0 : BOOL; (* Matgivare.Puls *)
    matut AT %QX0.0 : BOOL; (* Matdon.Svar *)
END_VAR
    matut := matin;
END_PROGRAM
```

Signalkartan bär kopplingen: `matin` hör till scenens `Matgivare.Puls`,
`matut` till `Matdon.Svar`. Riktningen kommer ur kartan, aldrig ur en gissning.

## Utfall

| Givaren sattes till | Donet följde efter på | kopplarvarv |
|---|---|---|
| True | 109.3 ms | 1 |
| False | 210.3 ms | 2 |
| True | 231.7 ms | 2 |

**Kopplarens varv:** 5 körda, 5 lyckade, median **89.11 ms**, p95 **104.85 ms**,
spann 78.64–104.85 ms.

Ett varv gör fyra saker: läser scenens givare genom bryggan, skriver PLC:ns
ingång över OPC UA, läser PLC:ns utgång, och skriver scenens don genom
godkännandekön. Varje led tidtas för sig.

## Var tiden ligger

| Led | Mätt |
|---|---|
| PLC:ns egen svarstid | exakt två scan, 40,0 ms vid 20 ms scanperiod (M-20) |
| OPC UA-transportens egen kostnad | 0,4 ms (M-20) |
| bryggan, tur och retur | 9,9 ms median (M-03), 39,5 ms för skriv-och-läs-tillbaka (M-38) |
| **hela varvet** | **89.11 ms median** |

Genomslaget från scenen till scenen tar ett till två kopplarvarv, alltså
ungefär 110–230 ms. Det är långsammare än en inbyggd koppling vore, och det är
priset för att VC:s egen OPC UA-klient inte går att nå från Python (M-38).

## Det trasiga fallet

PLC-anslutningen stängdes mitt i slingan. Kopplaren **gav upp efter tre raka
fel** i stället för att fortsätta skriva gamla värden till scenen:

```
Kopplarfel: kopplaren gav upp efter 3 raka fel
```

Utan den spärren hade slingan sett ut att arbeta medan scenen matades med
inaktuella värden — och ögat hade dömt på dem.

## Trösklar

| Konstant | Värde | Skäl |
|---|---|---|
| `MAX_RAKA_FEL` | 3 | två varv räcker inte för att skilja en tillfällig hicka från en död PLC; tre gör det, och kostar högst tre varv innan larmet |
| `OPCUA_TIDSGRANS_S` | 5,0 | tio gånger det längsta uppmätta varvet (104.85 ms), så en tidsgräns aldrig löser ut på normal drift |

## Vad som INTE är prövat

* **Bara två signaler.** En verklig station har tiotals, och kopplarens varv
  växer med antalet — varje led är ett bryggeanrop.
* **Ingen rörelse i scenen.** Donet är en boolesk signal, inte en transportör
  som faktiskt går. Att en produkt vandrar är fas 7, och blockeras av M-34.
* **Ingen tidsstämpling till ögat.** Kopplaren mäter sina egna led, men skjuter
  ännu inte in PLC-värden i ögats tidsserie. Ögat har gränssnittet
  (`Plckalla.skjut_in`), kopplaren använder det inte.
* **Windows.**
