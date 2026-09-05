# Plattformar — Windows och Wine

Kravet: tillägget ska fungera **både** på en vanlig Windows-installation av
Visual Components och under Wine på Linux. Wine är ett deployment-fall,
inte en förutsättning.

## Vad som är identiskt

VC:s inbäddade Python 2.7 och hela dess API är samma på båda.
Tilläggsmekanismen `OnAppInitialized()` under `My Commands` är samma.
`executeFrameGrab`, kollisionsdetektorn, `vcSimInterface`, statistiken:
samma. **Ingen av ögats eller bryggans funktioner beror på Wine.**

## Regler för VC-sidan (bryggan och ögat)

Dessa gäller all kod som körs inne i VC:

1. **Inga hårdkodade sökvägar.** Använd `getApplicationPath()` och VC:s egna
   mappinställningar. Aldrig `C:\...` i kod, aldrig `/home/...`.
2. **`os.path.join` överallt.** Aldrig strängkonkatenering med `\` eller `/`.
3. **TCP på localhost som transport.** Inte unix-socket, inte namngiven pipe.
   TCP beter sig likadant på båda.
4. **Ingen `subprocess` mot skalkommandon.** Skalet skiljer sig.
5. **Radslut och teckenkodning explicit** vid filskrivning. UTF-8, `newline` satt.
6. **Ingen import utanför VC:s medföljande Python 2.7-standardbibliotek.**
   Inga paket som måste installeras i värdmiljön.

Bryggan ska vara så liten att den inte kan bli plattformsberoende.
All logik ligger utanför, i tjänsten.

## Regler för tjänsten (Python 3, utanför VC)

Körs som värdprocess på Linux eller som Windows-process. Måste vara neutral:

- `pathlib` genomgående
- inga POSIX-antaganden om rättigheter eller processhantering
- konfigurerbar adress till både bryggan och OPC UA-servern; inget hårdkodat

## Vad som är Wine-specifikt och därför ligger i en bilaga, inte i kärnan

Detta är **driftsnoteringar för Linux**, inte systemkrav:

| Sak | Gäller | Källa |
|---|---|---|
| Wine ≥ 11.15 | annars dör licensmotorn på bcrypt `HashBlockLength` | MÄTT |
| DXVK som d3d9 | wined3d nekar den ytförfrågan `D3DImage` kräver | MÄTT |
| `d3dx9_43` och `d3dcompiler_43` som native | annars svart 3D-vy och omritningsloop | MÄTT |
| `taskset` mot P-kärnor | prestanda | MÄTT |

På Windows gäller inget av det. Detta flyttas till `docs/drift/linux_wine.md`.
Driftsinstruktioner för Windows finns i `docs/drift/windows.md`.

## OpenPLC på båda

OPC UA-ändpunkten är en URL och OpenPLC kan ligga var som helst:
i Docker på Linux, i Docker Desktop på Windows, eller på en annan maskin.
**Adressen är konfiguration, aldrig antagande.** Samma för REST-ändpunkten.

## Verifiering — ärligt om räckvidden (M-44, M-139)

| Plattform | Status | Verifierat hur |
|---|---|---|
| **Linux + Wine 11.16** | **mätt** | Fullständig körmätning mot körande VC 4.10 (M-01, M-112). Headless (:99) |
| **Linux (Alpine/musl)** | **mätt** | Installation och verktygskedja fungerar i ren container (M-109) |
| **Windows native x64** | **oprövat** | 16 mekaniserade acceptanspunkter i `tests/protocol/kor_E1_windows_16punkter.py` (M-44). Väntar på maskinkörning |
| **Windows + OneDrive** | **mätt** | Registerläsning och `ntpath.expandvars` verifierad mot diskkupa (M-91, E2) |
| **Windows ARM64** | **går inte** | Utgivarens paket `strucpp-win32-arm64.zip` är en x64-binär (M-56) |

Windows-vägen specificeras och kodas plattformsneutralt, och dess 16 acceptanspunkter
är fullständigt mekaniserade i `tests/protocol/kor_E1_windows_16punkter.py`.
Ingen fas får kallas "klar på Windows" förrän skriptet körts grönt på en levande Windows-maskin.

## Konsekvens för grindarna

Varje fas som stänger med en mätt grind ska köras på **båda** plattformarna
innan fasen räknas som klar. Tills Windows-körningen finns är fasen
"klar på Linux, oprövad på Windows" (M-139).
