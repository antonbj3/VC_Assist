# M-56 — verktygskedjan går att hämta ur repot, och två hål på vägen dit

**Datum:** 2026-09-04 · STruC++ v0.6.6 · OpenPLC Runtime v4 · node v22.22.0
**Fas:** 12. Skulden kommer ur `M-48`.
**Byggd av:** `install/verktygskedjan.py`

## Skulden som betalades

`M-48` skrev: *"STruC++ ligger i en sessionskatalog, inte i repot, och
npm-paketet som `paket.kompilera` kräver finns inte längre på maskinen. Grind 1
går att köra här och nu, men inte på en ren maskin utifrån repots egna
instruktioner."*

Fas 10 lovar *"Ren maskin: klona, installera, kör"*. Ett löfte som vilar på en
katalog som försvinner när sessionen tar slut är inget löfte.

## Kedjan, fastspikad

| Post | sha256 (början) | byte |
|---|---|---|
| `strucpp-0.6.6.tgz` (npm) | `64baa588a70a8d36` | 2 382 939 |
| `strucpp-linux-x64.tar.gz` | `24e0a8108ebbdf43` | 27 938 622 |
| `strucpp-linux-arm64.tar.gz` | `7dcc1b78f297c092` | 27 449 063 |
| `strucpp-win32-x64.zip` | `13ea67232f1e7023` | 22 256 729 |
| `strucpp-win32-arm64.zip` | `13ea67232f1e7023` | 22 256 729 |
| `strucpp-darwin-x64.zip` | `2257c960bfcb355c` | 23 816 569 |
| `strucpp-darwin-arm64.zip` | `65c49874b56f2553` | 22 636 388 |

OpenPLC låses till en **digest**, inte en tagg:
`ghcr.io/autonomy-logic/openplc-runtime@sha256:40726c99d041…`. En tagg är inget
löfte.

En fil som inte stämmer **tas bort** och hämtningen faller. Att lämna kvar en
fil som inte stämmer är att bjuda in nästa körning att använda den.

## Hål 1 — de två Windows-paketen är samma fil

`strucpp-win32-arm64.zip` och `strucpp-win32-x64.zip` har **samma sha256 och
samma storlek**. Nedladdade och jämförda med `cmp`: **byte-identiska**. Och
innehållet:

```
strucpp/strucpp.exe: PE32+ executable (console) x86-64, for MS Windows
```

ARM64-paketet är x64-bygget. Det är utgivarens fel, inte vårt, men det träffar
**fas 13** rakt: en Windows-maskin på ARM skulle hämta något som inte kan köra.

Posten står kvar i manifestet **med en varning som alltid skrivs ut**, i stället
för att tyst utelämnas. En utelämnad post ser ut som ett format vi inte stödjer,
och det är en annan sak än ett paket som är fel.

Ett prov låser fyndet: slutar de vara identiska är det en **ny mätning**, och då
ska varningen bort — men som ett medvetet beslut, inte som en tyst glidning.

## Hål 2 — beroendet var ett intervall, inte ett nummer

npm-paketet levereras **utan `package-lock.json`** och deklarerar

```json
"dependencies": { "chevrotain": "^11.0.0" }
```

Ett `npm install` mot det intervallet hämtar vad som råkar vara senast. Då är
hela hashkontrollen ovan meningslös — kedjan byter egenskaper under oss ändå,
och en mätning från förra veckan slutar gälla utan att någon märker det.

Utan `node_modules` faller kompilatorn dessutom **mitt i ett bygge**, långt
efter att hämtningen sagt sig ha lyckats:

```
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'chevrotain'
    imported from .../dist/frontend/parser.js
```

Låsfilen är därför skapad en gång och **vendorad i repot** som
`install/strucpp-0.6.6-package-lock.json`. `npm ci` läser den och kontrollerar
varje paket mot dess integritetshash: **478 poster, 477 med hash**.

`--ignore-scripts` är inte pynt. Paketets `prepare`-skript kör `husky`, som
faller här — och som i vilket fall inte ska få köra godtycklig kod under en
installation.

Med `--omit=dev`: **7 paket, 5,0 MB, 394 ms.**

## Beviset

Rent träd, ingenting kvar från tidigare körningar:

```
python3 install/verktygskedjan.py --cache <cache> --mal <mal>
  → npm + linux-x64 hämtade och kontrollerade
  → npm ci (låst, utan skript)
  → strucpp_paket: <mal>/npm/package
```

och därefter, ur den katalogen:

```
paket.kompilera(...)  →  OK, 2 lov
  debug-map.json  defines.h  generated.cpp  generated.hpp
  generated_debug.cpp  program.st
```

Alla fyra artefakterna. Det är de som gör skillnaden mellan att kunna översätta
och att kunna **ladda** koden i OpenPLC: utan `generated_debug.cpp` bygger .so:n
men vägrar laddas, och utan `debug-map.json` hittar OPC UA-pluginet inte paret
(arr, elem).

## Vad som INTE är mätt

* **Att hämtningen fungerar på Windows eller macOS.** Manifestet har posterna;
  ingen har kört dem. Det hör till fas 13.
* **Att OpenPLC-digesten går att dra på en ren maskin.** Avbilden finns lokalt
  sedan tidigare.
* **Node självt är inte fastspikat.** Kedjan kräver `node` på maskinen och
  använder det som finns (här v22.22.0). Att spika fast node också är möjligt
  men inte gjort, och det är en verklig lucka i "ren maskin"-löftet.
* **Låsfilen är granskad en gång, av mig.** 478 poster är fler än någon läser
  rad för rad. Det den ger är att kedjan inte **ändrar sig**, inte att varje
  post är oskyldig.
