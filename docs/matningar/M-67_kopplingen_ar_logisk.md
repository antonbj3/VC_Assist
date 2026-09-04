# M-67 — kopplingen är logisk: den flyttar ingenting

**Datum:** 2026-09-05 · VC Premium 4.10 · Wine 11.16 · testprefixet
`~/.wine-vc-test`, headless `:99`
**Körs av:** `tests/protocol/kor_m67_kopplingens_geometri.py`
**Avgör:** kompositionslagrets design

## Frågan

Positionerar en `vcSimInterface.connect()` komponenterna, eller kopplar den bara
logiskt? Antingen räknar layoutlösaren ut varje läge själv, eller så snäpper VC
ihop delarna — och då ska vi låta bli att räkna. Två helt olika program, och
ingen mätning hade svarat.

## Svaret

**Kopplingen flyttar ingenting.** Två komponenter byggdes på kända, åtskilda
lägen, kopplades, och lästes av igen — med `sim.update()` före varje avläsning,
eftersom `WorldPositionMatrix` släpar ett scenuppdateringssteg (M-11).

```
M67ok    canConnect=True   connect=True   IsConnected=True
         A  (0.0,    0.0,   0.0)  ->  (0.0,    0.0,   0.0)     flyttad 0.000 mm, vred sig 0.00000
         B  (1500.0, 700.0, 250.0) -> (1500.0, 700.0, 250.0)   flyttad 0.000 mm, vred sig 0.00000
```

Noll millimeter, noll vridning, i en koppling som **lyckades** och där
`IsConnected` blev sant. Följden för kompositionslagret:

> Layoutlösaren äger geometrin. Den måste räkna ut varje läge själv — VC hjälper
> inte till, och det finns ingen risk att två räkningar slåss om samma läge.

## Det trasiga fallet: en misslyckad koppling flyttar heller ingenting

Två **utgångar** mot varandra går inte att koppla. Det farliga hade varit en
koppling som misslyckas och ändå flyttar något — då ser scenen byggd ut fast
den inte är det.

```
M67fel   canConnect=False  connect=False  IsConnected=False
         A  flyttad 0.000 mm    B  flyttad 0.000 mm
```

Ingenting rörde sig. Fallet är alltså inte bara "gick inte att koppla" — det är
"gick inte att koppla **och lämnade scenen orörd**".

## Två saker på vägen som är värda att skriva ned

**`vcMatrix` har ingen `setP`.** Provet skrevs med `m.setP(x, y, z)` och VC
svarade `NameError: Attribute or method 'setP' not found.` Ett absolut läge
sätts som byggrecepten redan gör det, med `translateAbs` — som är **relativ i
absoluta axlar** (M-11) — alltså som skillnaden mot nuvarande läge:

```python
m = c.PositionMatrix
m.translateAbs(x - m.P.X, y - m.P.Y, z - m.P.Z)
c.PositionMatrix = m
```

**`canConnect` var sant trots 1670 mm mellan komponenterna.** M-40 beskrev
`canConnect` som "en geometrisk fråga", och det stämde i M-40:s eget fall — men
där var orsaken ett fält med `Port = -1`, inte avståndet. Här ligger
gränssnitten 1500 mm isär i x, 700 i y och 250 i z, och `canConnect` svarar
ändå `True`. Med `DistanceTolerance` på sitt förvalda `1e9` gatear avståndet
alltså ingenting; det som avgör är fältbindningen och kontakttypen.

Det är en **skärpning av M-40**, inte en motsägelse: `canConnect` är en fråga om
gränssnittens *innehåll*, och avståndet räknas bara när toleransen sätts.

## Vad som INTE är visat

* **Andra gränssnittstyper.** Provet använder `VC_ONETOONEINTERFACE` med ett
  `VC_FLOWFIELD` över en `VC_ONEWAYPATH`. Om någon annan fälttyp snäpper är
  oprövat.
* **Ett satt `DistanceTolerance`.** Avståndets roll är mätt bara vid förvalet.
* **Vad som händer vid `disconnect()`.** Provet kopplar och river komponenterna;
  det mäter aldrig om en frånkoppling flyttar något.
* **Om en produkt faktiskt går över kopplingen.** M-41 mätte flödet, men på en
  linje som var byggd för att ramarna skulle mötas. Att flödet fungerar även när
  gränssnitten ligger 1670 mm isär är **inte** mätt — kopplingen är logisk, men
  transporten kan mycket väl kräva att ramarna sammanfaller.
