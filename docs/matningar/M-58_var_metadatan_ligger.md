# M-58 — var i metadatan fälten ligger, och vad "kategori" faktiskt är i grunt läge

**Datum:** 2026-09-04 · 300 slumpade komponenter ur biblioteket (M-57)
**Gäller:** `svc/vc_assist_svc/katalogindex.py`

## Mätningen

Byteoffset för de två fält indexet läser, över 300 slumpade komponenter:

| Fält | min | median | p95 | max |
|---|---:|---:|---:|---:|
| `Name` | 62 | **181** | 181 | **181** |
| `Category` | 4 871 | **142 724** | 323 376 | 4 849 128 |

| Huvudläsning | `Name` inom | `Category` inom |
|---:|---:|---:|
| 2 048 B | 100 % | 0 % |
| 4 096 B | **100 %** | 0 % |
| 8 192 B | 100 % | 3 % |
| 32 768 B | 100 % | 26 % |

`Category` saknades i **noll** av 300 — den finns alltid, men den ligger långt in.

## Två följder

### `_HUVUD = 4096` har nu en grund

Namnet ligger som mest vid byte 181. 4096 ger tjugo gångers marginal utan att
kosta något: metadatan är 200–300 kB per komponent, så en huvudläsning är under
två procent av filen. Talet var förut en gissning som såg rimlig ut.

### "Kategori" i grunt läge är KATALOGNAMNET, inte metadatans fält

> **RÄTTAD av M-76.** Slutsatsen nedan gällde koden som fanns då, och den var
> riktig för den. Men den byggde på ett antagande ingen prövade: att
> `component.rsc` var komponentens enda metadatapost.
>
> Det finns en till. `model.xml` är **2–3 kB**, finns i **3201 av 3201**
> komponenter, och **deklarerar** `Type`, `Manufacturer`, `Reach`, `MaxPayload`
> och `IsDeprecated`. Grunt läge läser den nu, och kategorin kommer därför ur
> ett deklarerat fält — samma tal som den djupa läsningen ger, till en
> sextondel av kostnaden.
>
> Mätningen av var `Name` och `Category` ligger i `component.rsc` står kvar och
> är oförändrad. Det som föll är slutsatsen som drogs av den.

Det är den viktiga raden. Grunt läge läser 4 096 byte och når därför **aldrig**
`Category`. Fältet i indexet fylls i stället från katalogen komponenten låg i
(`ABB/Robots/` → `Robots`).

De två sammanfaller ofta, och det är precis därför felet är farligt: allt ser
rätt ut tills en tillverkare lägger sina komponenter i en katalog som heter
något annat än vad komponenten själv säger att den är.

Två fält som *nästan* alltid är lika är två fält, inte ett. Indexet säger nu
vilket av dem det bär, i stället för att låta läsaren tro att det är
komponentens egen uppgift.

Djupt läge läser hela metadatan och tar då fältets **eget** värde. Skillnaden
mellan lägena är alltså inte bara hastighet — det är två olika storheter, och
den som jämför dem jämför äpplen med päron.

## Formatversionen

`FORMAT = 1` är indexfilens version. Den finns av samma skäl som signalkartans:
ett format utan version går inte att ändra utan att tyst omtolka gamla filer,
och en tyst omtolkning är värre än ett fel. Version 1 är den form som beskrivs
här: `namn`, `tillverkare`, `kategori`, `sokvag`, `storlek`, och i djupt läge
`granssnitt` och `parametrar`.

## Vad som INTE är mätt

* **Om katalognamn och `Category` någonsin skiljer sig.** Att jämföra dem över
  hela biblioteket kräver ett djupt svep, och det är inte gjort. Tills det är
  gjort ska de behandlas som två fält.
* **Om `Name` någonsin ligger efter byte 181.** 300 av 3201 är ett stickprov.
  Marginalen till 4 096 är stor, men det är en marginal och inte ett bevis.
