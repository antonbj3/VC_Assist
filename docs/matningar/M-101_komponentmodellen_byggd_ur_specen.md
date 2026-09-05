# M-101 — komponentmodellen byggd ur specen och prövad i riktig VC

**Datum:** 2026-09-05 · VC Premium 4.10 · Wine 11.16 · testprefixet
`~/.wine-vc-test`, headless `:99`
**Fas:** 20
**Körs av:** `tests/protocol/kor_fas20_modellen.py`
**beskriver:** `docs/spec/49_komponentmodellen.md` (avsnitt 7–11),
`svc/vc_assist_svc/komponentmodell.py`, `tests/enhet/test_komponentmodell.py`
**Föregångare:** [M-40](M-40_varfor_mataren_aldrig_fyrade.md) (två tysta
villkor), [M-41](M-41_produkten_flodar.md) (flödet),
[M-67](M-67_kopplingen_ar_logisk.md) (kopplingen flyttar ingenting)

ARBETET PÅGÅR. Fynd 1 och 2 är mätta. Talen för kedjan och de fyra trasiga
fixturerna skrivs in när körningen gått igenom.

## Frågan

`49_komponentmodellen.md` svarade på A–G i **text**. Vad en TRANSPORTÖR minst
behöver, vad som krävs för att `canConnect` blir sant, hur ett fält binds — allt
belagt eller mätt, ingenting byggt **ur** specen. En spec som aldrig byggts är
en hypotes med tabeller.

Fas 20 vänder riktningen: kravlistorna ligger som **data** i
`komponentmodell.py`, VC-koden **genereras ur dem**, och ett prov faller om
specens tabeller och modellens data glider isär — i båda riktningarna.

## Uppställningen

Kedjan är alla fyra klasserna i **ett** flöde, placerade så att ramarna
sammanfaller:

```
F20_Matare  ->  F20_Bana  ->  F20_Buffert  ->  F20_Sanka
 matare          transportör    buffert         sänka
 400 mm          2000 mm        1000 mm         400 mm
 Interval 3 s    400 mm/s       400 mm/s        Capacity 1e6
```

Utöver kedjan tolv komponenter till: per klass en **motpart**, en **trasig**
(ett krävt beteende utelämnat) och en **hel tvilling** på exakt samma plats i
världen. Sexton komponenter, elva kopplingsförsök, allt i ett startskript som
`bridge_cmd` kör före `startSimulation()` — beteenden som läggs till i en redan
körande simulering initieras aldrig (M-40 villkor 1).

## Fynd 1 — `ContentVisible` finns inte, och tog med sig hela startskriptet

`api.xml` dokumenterar `vcContainer.ContentVisible` (W): *"Sets the visibility
of components stored in the container."* Det beteende `VC_COMPONENTCONTAINER`
faktiskt ger — `vcSimContainer` — **bär den inte**:

```
NameError: Attribute or method 'ContentVisible' not found.
```

Det är VC:s `NameError`, inte Pythons `AttributeError` — samma fälla som M-40
beskrev för `Connectors`. Tilldelningen stod oskyddad i byggkoden, så
undantaget tog med sig **hela resten av startskriptet**: tre komponenter av
sexton byggdes, noll av elva kopplingar provades, och en hel VC-omstart gick
till spillo på en kosmetisk egenskap som ingen dom hängde på.

Två saker ändrades av det, och den andra är den viktiga:

1. `ContentVisible` är **inte längre ett krav** på sänkan. Ett krav som inte går
   att uppfylla är inget krav. Raden står i stället i specens avsnitt 11,
   *Vad mätningen har refuterat*, med sin källa och sitt utfall.
2. **Varje egenskapstilldelning går nu genom `_steg()`.** En egenskap som inte
   finns är ett mätvärde, aldrig ett haveri. Modellen hade redan den regeln för
   gränssnitten och inte för egenskaperna — och det var precis där den brast.

Tilldelningen står kvar i den genererade koden **som mätning**. Slutar den
falla har bindningen ändrats, och det vill vi se.

## Fynd 2 — en belagd rad är inte en mätt rad

`ContentVisible` bar märkningen **BELAGT** med ett ordagrant citat ur `api.xml`.
Citatet är riktigt. Påståendet är ändå falskt för det objekt vi faktiskt får,
därför att `api.xml` beskriver **typen** `vcContainer` medan py2-bindningens
instans är något annat. Märkningen BELAGT säger att en källa påstår något — inte
att VC gör det.

Det är inte ett skäl att sluta belägga. Det är ett skäl att låta varje belagd
rad som **styr ett bygge** bli mätt, och att bygget ska överleva att den inte
är det.

## Resultat: kedjan och de fyra trasiga fixturerna

*Väntar på körningen. Ingen siffra skrivs här förrän
`kor_fas20_modellen.py --starta-om` gått igenom.*

## LIMITS

* **Ingen upprepning.** Varje komponent byggs och mäts **en gång**, i en
  körning. Ingen spridning bakom något tal.
* **Ett fönster.** Flödet mäts över ett provfönster på ~36 s. En matare som
  slutar efter tjugo minuter hade sett hel ut här (samma begränsning som M-41).
* **Två av fem par är härledda, inte mätta.** `transportor -> transportor` och
  `matare -> sanka` står som "ja" i specens partabell därför att de följer av
  R5, inte därför att de byggts. Härkomstkolumnen säger det.
* **Matchningsregelns ordning är vår, inte VC:s.** `canConnect` ger ett enda
  `False` och säger aldrig vilket villkor som brast. R1–R9 är den ordning som
  gör felet begripligt; VC:s inre ordning är omätt.
* **R6, R7 och R8 är belagda, inte mätta.** Alla våra sektioner har exakt ett
  fält av samma typ, så fältordning och fälttyp kan inte skilja i den här
  uppställningen.
* **`DistanceTolerance` mäts bara vid förvalet** (1e9 mm). Vad ett satt värde
  gör är fortfarande omätt (öppen sedan M-67).
