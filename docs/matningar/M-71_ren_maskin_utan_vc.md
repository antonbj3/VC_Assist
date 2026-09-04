# M-71 — hela kedjan ur en ren klon, utom det som kräver VC

**Datum:** 2026-09-05 · Python 3.13.11 · node v22.22.0 · Linux
**Fas:** 10. Kompletterar `tests/protocol/fas10_paketering.md`, som mätte
installationen men skrevs **innan** verktygskedjan fanns (fas 12, M-56).

## Vad fas 10 lovar

> *"Ren maskin: klona, installera, kör. Fungerar utan handpåläggning."*

Den mätningen gjordes 2026-09-04 för `install/`. Sedan dess har fas 12 lagt till
ett steg som löftet också måste täcka: **verktygskedjan**. En maskin som klonar
repot har varken STruC++ eller dess beroenden, och utan dem kan grind 1 inte
köras alls.

## Körningen

`git clone` av HEAD till en tom katalog, och sedan allting därifrån.

| Steg | Utfall |
|---|---|
| klonen | 393 filer, 23 MB |
| **hela enhetssviten ur klonen** | **5751 gröna**, 190 överhoppade, 7 röda |
| **verktygskedjan från noll**, tom cache, riktig nedladdning | **5,00 s** |
| fullt bygge med debugkarta ur klonen | **0,5 s**, alla fyra artefakterna |
| **grind 1–4 skarpt** (`kor_fas7_grindar.py`) | **alla fall stämde** |
| **ST-svepet mot riktiga kompilatorn** (190 prov) | **190 gröna, 25,4 s** |
| installationens sökning | **0,07 s**, hittade båda VC-installationerna |
| bara `install/` + `ext/` i en tom mapp | **fungerar** utan resten av repot |

De sju röda är kända och inte klonens fel: tröskelspärren väntar på mätningar
som andra agenter ännu inte skrivit, och skuldspärren står röd på en skuld som
är namngiven och under betalning (M-68). **Klonen är alltså exakt lika frisk som
arbetsträdet** — ingenting som behövs saknas i git.

## Det viktigaste talet är fem sekunder

Verktygskedjan hämtas, hashkontrolleras och installerar sina beroenden på
**fem sekunder** på en maskin som inte har någonting. Det inkluderar 30 MB
nedladdning, sha256 över två arkiv, uppackning och `npm ci` mot den vendorade
låsfilen.

Det gör skillnaden mellan ett löfte och en instruktion. Före fas 12 låg
kompilatorn i en sessionskatalog och grind 1 gick inte att köra alls på en ny
maskin (M-48).

## Vad som fortfarande INTE är prövat

* **Att VC startar med det installationen lade dit.** Det är fas 10:s enda
  återstående L3-steg på Linux, och det stod öppet redan i protokollet. Det
  kräver VC, och VC ägs just nu av fas 7-körningen.
* **Windows och macOS.** Manifestet bär posterna; ingen har kört dem. M-44 har
  16 numrerade protokollpunkter som väntar på en maskin, och M-56 fann att
  utgivarens ARM64-paket för Windows **är** x64-bygget.
* **En maskin utan node.** Kedjan kräver `node` och använder det som finns
  (här v22.22.0). Node är inte fastspikat, och det är en verklig lucka i
  "ren maskin"-löftet som M-56 redan skrev ned.
* **En maskin utan nät.** Hämtningen förutsätter åtkomst till GitHub och npm.
  Ett offlineläge finns inte.
* **En maskin utan docker.** OpenPLC-avbilden dras av docker, inte av oss.
  Ingen del av det här provet rörde OpenPLC.
* **Klonen är lokal.** `git clone --local` från samma disk, inte över nätet.
  Skillnaden bör vara noll för innehållet men är inte prövad.
