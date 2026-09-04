# M-38 — VC:s Python når inte OPC UA, men bryggan når signalerna

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Gäller:** fas 6, det led som stått öppet sedan PLC-halvan mättes (M-20).

## Det som inte går

VC:s Python-API har **noll** yta mot uppkoppling. Sökning i indexets 3444
symboler efter `opc`, `server`, `variable` och `subscri` ger bara falska
träffar — `vcTopology.CurveLoopCount` och liknande. Det bekräftar M-15.

Uppkopplingen finns bara i **.NET**:

```
VisualComponents.Connectivity.Core.dll
VisualComponents.Connectivity.OpcUA.dll   (dokumenterad i docs/referens/vc_dotnet/)
VisualComponents.Connectivity.BeckhoffAds.dll
Connectivity.Sharp7.dll                    (Siemens S7)
```

Och VC:s Python når inte .NET: `import clr` och `import System` ger båda
`ImportError` (M-07).

Följden är att **VC:s egen OPC UA-klient inte kan konfigureras programmatiskt.**
Den kräver gränssnittet, eller en layout där kopplingen redan är sparad.

## Det som går

Bryggan når scenens signaler direkt.

```
createBehaviour(VC_BOOLEANSIGNAL, 'ST010_CNV_RUN')   ->  vcBoolSignal
createBehaviour(VC_REALSIGNAL,    'ST010_CNV_SPEED') ->  vcRealSignal

skrivning:  s.Value = True        r.Value = 12.5
avlasning i en SEPARAT korning, over ett simuleringssteg:
            ST010_CNV_RUN   True
            ST010_CNV_SPEED 12.5
```

**Tur och retur genom bryggan: 39,5 ms** — skapa, skriva, och läsa tillbaka i en
annan körning.

Namnen är bankens egen konvention (`ST<nnn>_<DON>_<FUNKTION>`), så en
signalinventering ur scenen kan gå rakt in i PLC-deklarationerna (grind 3).

## Vad det betyder för arkitekturen

Den tänkta kedjan var:

```
genererad ST -> OpenPLC -> OPC UA -> VC:s OPC UA-klient -> scenen
```

Sista pilen är **omöjlig från Python**. Men kedjan går att sluta ändå, genom
tjänsten:

```
genererad ST -> OpenPLC -> OPC UA -> tjansten -> bryggan -> scenens signaler
```

Tjänsten läser och skriver PLC-variabler över OPC UA (mätt i M-20: tur och retur
exakt två scan, 40 ms vid 20 ms scanperiod, transportens egen kostnad 0,4 ms) och
läser och skriver scenens signaler över bryggan (39,5 ms).

Summan är cirka 80 ms per varv. Det är långsammare än VC:s inbyggda koppling
vore, men det är **mätt**, det går att bygga i dag, och det kräver varken
gränssnitt eller .NET.

## Vad som inte är avgjort

* Om VC:s inbyggda koppling går att få in via en **sparad layout** som redan
  bär den. Omätt, och det kräver att någon konfigurerar den i gränssnittet en
  gång.
* Om 80 ms räcker. Det beror på vad som ska styras: en transportör med 200 mm/s
  rör sig 16 mm på 80 ms. För en gripsekvens är det troligen gott om marginal,
  för en snabb sorterare är det troligen inte det. **Omätt** tills en riktig
  cell körs.
* Ögats krav att PLC-värden ligger på **samma tidsaxel** som fysiken. Med två
  hopp i kedjan bär varje avläsning en ålder, och den åldern måste provtas med.
  Ögats `Plckalla.skjut_in(varden, t)` tar redan emot en tidsstämpel.
