# M-177 — räckvidden känns igen på variablerna, inte på blocktypen

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen. 3 204 `.vcmx` i testprefixet, ingen VC startad.
**Prövar:** `M-59` mätte att räckvidden är **läst i noll fall, härledd i 1 693
och saknas i 509** av 2 202 robotar. Frågan som ledde hit var operatörens:
*"om det är en 3D-modell som kan animeras, måste väl räckvidden finnas?"*

## Frågan var rätt ställd

Om en robot går att animera finns dess länklängder och ledgränser i modellen.
Och tabellen i `M-59` säger det själv: **ledgränser lästa i 2 206 av 2 275**,
**kinematik i 2 201 av 2 202**. Strukturen finns nästan överallt.

Att räckvidden ändå saknades i 509 var alltså inte ett hål i datan.

## Orsaken: en enda, och den var vår

Reproducerat över hela biblioteket:

```
saknas 509 —  506  rPythonKinematics utan länklängder i blocket eller roten
                2  rKinScara utan länklängder
                1  inget kinematikblock alls
```

`_rackvidd` valde formel på blockets **typnamn**. Den artikulerade grenen kördes
bara när typen hette `rKinArticulated2`. En robot som definierar sin kinematik i
ett Python-skript heter `rPythonKinematics` — och föll till en tredje gren som
letar `JointOffset1`/`LinkLength2` och inte hittar något.

Men de behåller kedjans namn. `xArm7` och `MS005N` bär `L12X`, `L23X`, `L23Z`,
`L34X`, `L34Z`, `L45Z` — exakt de variabler den artikulerade formeln använder.

**Mätt före lagningen:** av de 509 bär **143** både `L12X` och `L23Z`.

## Efter

| | före | efter |
|---|---:|---:|
| härledd | 1 693 | **1 835** |
| saknas | 509 | **367** |

**142 robotar** fick tillbaka ett tal som fanns hela tiden. Täckningen går från
76,9 % till 83,3 % av alla robotar.

Kvar står 367: **293 utan L-namn alls** — en genuint annan kedjeform — och 73
med namnen bara delvis. De förblir `SAKNAS`, och det är rätt.

Formeln är oförändrad. Det enda som ändrades är hur kedjan känns igen: på sina
variabler i stället för på blockets typnamn. Källsträngen namnger nu blocktypen
talet kom ur, så en `rPythonKinematics`-härledning inte utger sig för att vara
en `rKinArticulated2`.

## LIMITS

* **En robot mindre än de 143 förutsagda.** Utfallet blev 142. Skillnaden är
  inte utredd; en komponent faller på något annat villkor i kedjan.
* **Talet är fortfarande en övre gräns.** Ledgränserna är inte inräknade — en
  arm vars led 3 inte kan sträckas helt når kortare än summan. Det stod redan i
  `M-59` och ändras inte här.
* **Formeln är validerad mot 386 modellnamn** (`M-59`, median 1,001), och de
  var alla `rKinArticulated2`. Att den håller lika bra för de 142 nya är
  **oprövat** — deras modellnamn bär inte alltid ett mått att jämföra mot.
* **De 293 utan L-namn är inte undersökta.** Att de har en annan kedjeform är
  läst ur att namnen saknas, inte ur att någon tittat på vilken form de har.
* **Ingen VC startades.** Allt är läst ur filerna på disk.
