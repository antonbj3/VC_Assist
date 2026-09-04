# M-33 — VC:s basenhet är millimeter

**Datum:** 2026-09-04 · VC Premium 4.10
**Varför den gjordes:** ögats utbyggnad pekade ut `LANGDENHET_TILL_MM` som den
farligaste omätta konstanten i hela projektet. Stämmer den inte är varje
millimetertal fel med faktor tusen, åt ett håll som ser rimligt ut.

## Mätt

`app.findUnit(namn)` för elva kandidatnamn:

| Anrop | Namn | Faktor |
|---|---|---|
| `findUnit("mm")` | millimetres | **1.0** |
| `findUnit("cm")` | centimetres | 10.0 |
| `findUnit("m")` | metres | **1000.0** |
| `findUnit("in")` | inches | 25.4 |

Faktorn anger hur många **basenheter** enheten är. Millimeter har faktor 1,0.
**Basenheten är alltså millimeter.**

`findUnitFamily` gav `None` på alla prövade namn (`Length`, `Distance`,
`Default`, …); familjens namn är okänt och lyckades inte gissas.

## Bekräftat med en kropp av känd storlek

Den första versionen av den här mätningen kallade slutsatsen en **stark
slutledning**, eftersom enhetstabellen inte säger vad `vcMatrix.P` använder.
Det behövde inte förbli så.

`komponent.RootFeature.createFeature(VC_BLOCK, namn)` skapar en `vcFeature` med
egenskaperna `Length`, `Width`, `Height`. Satta till en **EUR-pall** — 1200 ×
800 × 144 — svarar VC:

```
BoundCenter    [600.0, 400.0,  72.0]
BoundDiagonal  [600.0, 400.0,  72.0]
```

Exakt hälften av varje mått, i samma enhet som sattes. Tillsammans med
enhetstabellens `mm = 1.0` är världsenheten därmed **mätt**, inte härledd.

Tredje oberoende korroboreringen: `vcMotionPath.Speed` är 200,0 som standard.
I mm/s är det 12 m/min, en normal transportörshastighet. I m/s vore det
720 km/h.

Dokumentationen säger fortfarande ingenting: `vcMatrix.P` beskrivs som
*"Defines Position vector"* utan enhet.

## Ett falskt spår som är värt att skriva ned

Jag sökte först efter ordet `meters` i `api.xml` och fick **2214 träffar**, mot
två för `millimeter`. Det såg ut som ett svar.

Det var **"parameters"**.

En ordräkning utan sammanhang är inte en mätning. Jag var en rad ifrån att
skriva ned motsatsen till det som gäller.

## Följd för ögat

Cellerna i `tests/celler.py` räknar i meter — en detalj på `z = 0.75` avser
750 mm. Är världen i millimeter blev cellen en tusendel så stor som avsett.

Domarna blev ändå **rätt**, eftersom bandrivaren skrev och ögat läste i samma
skala: `dist=800.0mm` i teleportcellen kom ur att banan satte 0,8 och ögat
multiplicerade med 1000. Självkonsistent, och därför osynligt.

Men varje **absolut** millimetertal ögat rapporterar mot en riktig VC-scen blir
fel med tusen, och det gäller `TELEPORT_TRANSFER`, `PLACE`, `MINDIST` och
`UNDERGROUND` — alltså fyra av ögats grindar.

`LANGDENHET_TILL_MM` ska vara **1.0**, inte 1000, och cellernas mått ska
uttryckas i millimeter.

## Öppet

* Bekräfta med ett objekt av känd fysisk storlek när en katalog finns.
* Samma fråga för tyngdaccelerationen: är `G` 9,81 m/s² eller 9810 mm/s²?
  Ögats fallhastighetsgrindar hänger på det.
