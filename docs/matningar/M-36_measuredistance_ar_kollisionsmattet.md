# M-36 — `measureDistance` är kollisionsmåttet, inte detektorn

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Löser:** blockeraren i M-35, och därmed fas 5:s kollisionsled.

## Varför detektorn aldrig fyrade

`vcCollisionDetector.NodeListA` tar emot en **lista** — men tömmer den:

```
d.NodeListA = [komponent]   ->  las tillbaka: []   langd 0
d.NodeListA = komponent     ->  AttributeError: Attribute 'NodeListA' not found.
d.NodeListA = (komponent,)  ->  AttributeError: Attribute 'NodeListA' not found.
```

Ett enskilt objekt och en tupel **avvisas** med ett vilseledande fel som påstår
att egenskapen inte finns. En lista **accepteras** och innehållet kastas.

Detektorns nodlistor var alltså tomma hela tiden. Den svarade noll därför att
den inte hade något att jämföra — inte därför att kropparna inte överlappade.
Det förklarar varje rad i M-35, inklusive att `testMinimumDistance(5000.0)` gav
falskt för två kroppar 100 mm isär.

Prövat och avfärdat på vägen: detektor skapad som **layoutpost** via
`app.createLayoutItem(VC_LAYOUTITEM_IT_COLLISIONDETECTOR)` — hittas av
`findLayoutItem`, ligger alltså i layouten, och ger ändå noll. Läsning efter ett
simuleringssteg — noll. `rebuild()` före — noll.

## Vad som fungerar

`vcNode.measureDistance(annan)` — och `vcComponent` ärver hela nodytan.

Den returnerar en **tupel**: `(avstånd, punkt1, punkt2, vektor)`.

Två kuber om 1000 × 1000 × 1000 mm, A vid x = 0:

| B vid | avstånd | tolkning |
|---|---|---|
| 0 mm | **0.0** | helt i varandra |
| 100 mm | **0.0** | 900 mm överlapp |
| 1000 mm | **0.0** | kant i kant |
| 1500 mm | **500.0** | 500 mm glapp |
| 5000 mm | **4000.0** | 4000 mm glapp |

Exakt rätt i varje punkt, i millimeter (M-33).

## Fällan som gömde det i ett varv

Utan uppdatering emellan gav **alla fem** avstånden identiskt `4000.0`.
Geometrin utvärderas inte om inom samma körning — samma eftersläpning som
M-11 mätte för `WorldPositionMatrix`.

Mätningen kräver alltså:

```python
nod.PositionMatrix = m
nod.update()
sim.update()
avstand = a.measureDistance(b)[0]
```

Utan de två raderna svarar VC konsekvent och trovärdigt med ett gammalt tal.
Det är tredje gången samma eftersläpning bitit: världsmatrisen (M-11),
kollisionsdetektorns tomma lista, och nu geometrin.

## Följd

Kollisionsgrinden bygger på `measureDistance`, inte på `vcCollisionDetector`.

Avstånd `0.0` betyder **nuddar eller överlappar** — måttet skiljer inte de två.
För en grind som kräver noll kollisioner räcker det: allt som inte får röra
varandra ska ha ett avstånd **större än noll**, och layoutmotorn lämnar
marginaler ändå. Vill man veta *hur djupt* två kroppar tränger in i varandra
krävs något annat, och det är omätt.

Ögats `mindist`-provtagning bör byggas om från detektorn till `measureDistance`.
Den ändringen är **inte** gjord här.
