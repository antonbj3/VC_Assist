# M-37 — gränssnitt går att koppla; `Container` var den saknade bindningen

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Löser:** det som stått öppet sedan M-14, genom M-16 och M-17.

## Receptet, mätt

```python
komp  = app.createComponent()
stig  = komp.createBehaviour(VC_ONEWAYPATH, 'Stig')        # flödesbeteendet
ifc   = komp.createBehaviour(VC_ONETOONEINTERFACE, 'Flow')
sek   = ifc.createSection('Sec')
falt  = sek.createField(VC_FLOWFIELD, 'Flode')

kontakt = [k for k in stig.Connectors if k.Type == VC_CONNECTOR_OUTPUT][0]
for p in falt.Properties:
    if p.Name == 'Container':   p.Value = stig            # <- den saknade
    elif p.Name == 'Port':      p.Value = kontakt.Index
    elif p.Name == 'PortName':  p.Value = str(kontakt.Name)
```

Den ena sidan binder sin **utkontakt**, den andra sin **inkontakt**. Sedan:

```
canConnect    True
connect       True
IsConnected   True
ConnectedComponent  "FlowB"
```

## Vad som saknades i alla tidigare försök

Flödesfältet bär fyra egenskaper: `Name`, `Container`, `Port`, `PortName`.

M-17 mätte att `Port` tar ett **heltal** — kontaktens `Index`, inte ett
kontaktobjekt. Det stämde, och band bara `Port`.

**`Container` bands aldrig.** Fältet pekade alltså på port 1 i *ingenting*, och
`canConnect` svarade falskt utan att säga varför. Nio uppställningar prövades i
M-14, alla med obundet `Container`, och alla föll av samma osynliga skäl.

Kontakten ska väljas på `Type` (`VC_CONNECTOR_OUTPUT` respektive
`VC_CONNECTOR_INPUT`), aldrig på index: `rResourceCreator` bär dem i omvänd
ordning mot alla andra (M-17).

## Rättelse av M-16

M-16 skrev att `canConnect` **dödar pumpen**. Det gjorde den, men orsaken var
inte anropet. Det var en ogiltig bindning: `Transport`-fältets
`Ref<ComponentProcessor>` bunden till en `vcTransport` som inte hörde till samma
komponentmodell. Med ett korrekt bundet **flödesfält** kraschar `canConnect`
inte alls.

Slutsatsen i M-16 att ett läsande verktyg kan döda bryggan står ändå kvar — den
är mätt. Men den gäller vid trasig bindning, inte generellt.

## Följd för fas 5

Grindens tredje led — *alla gränssnitt kopplade* — är därmed möjligt att
uppfylla, och det på gränssnittsnivå, inte bara på kontaktnivå.
