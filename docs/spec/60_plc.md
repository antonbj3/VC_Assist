# PLC-benet

## Uppsättning

| Del | Val | Motiv |
|---|---|---|
| Mjuk-PLC | **OpenPLC v4** (Autonomy Logic) | enda gratis som är OPC UA-**server** och har headless inladdning |
| Transport | OPC UA, `opc.tcp://<ip>:4840/openplc/opcua` | VC:s plugin är klient, PLC:n måste vara server |
| Inladdning | REST + JWT | `/api/login`, `/api/upload-file`, `/api/compilation-status`, `/api/start-plc` |
| Kompilator | `STruC++` CLI | fristående, Linux-binärer, körs som grind 1 |

**Avvisade:** OpenPLC v3 (ingen OPC UA), Beremiz (endast klient),
CODESYS (IDE är Windows), Modbus-brygga (onödig med v4).

## Deklarationer genereras, skrivs aldrig

Kedjan:

```
VC-scen ──► signalkarta ──► OPC UA-nodlista ──► ST VAR-block
```

Modellen får **aldrig** skriva variabeldeklarationer eller taggnamn. Den får en
färdig deklarationsdel och skriver bara sekvenslogiken. Det tar bort hela
felklassen "fel taggnamn" mekaniskt i stället för att be modellen vara noggrann.

Signalkartan hämtas ur scenen via komponenternas signaler. **Öppen fråga:**
hur mappningen mellan VC-signal och OPC UA-nod ska deklareras. Kandidater:
namnkonvention, eller en explicit mappfil per station. Avgörs i fas 6.

## Vad modellen får skriva

Endast kroppen i en station: sekvensen, timers, förreglingar mellan de
deklarerade taggarna. Ett skelett per station, med deklarationer ifyllda.

## Scan-cykeln

Modellen får inte en förklaring av scan-cykelsemantik. Den får **se** den:
PLC:ns variabelvärden loggas på samma tidslinje som scenen, så en flank som
missas mellan två scan blir synlig i serien.

## .NET-begränsningen

**MÄTT:** VC:s connectivity finns bara i .NET, inte i Python-API:t. Det ger två vägar:

1. **Via komponentsignaler** — Python sätter och läser komponenternas egna signaler,
   och VC:s connectivity-lager mappar dem mot OPC UA. Ingen .NET-kod behövs.
   **Föredras.** Prövas först.
2. **Eget .NET-plugin** om väg 1 inte räcker. Gränssnitten finns:
   `IPluginHandler`, `IServerHandler`, `IVariableGroupHandler`, `IValueTypeConverter`.

## Säkerhet

Se `50_grindar.md`. Kort: ingenting genererat i en säkerhetsfunktion.
