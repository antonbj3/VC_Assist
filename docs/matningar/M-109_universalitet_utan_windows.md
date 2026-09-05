# M-109 — universalitet utan Windows: fem distros, fem Pythons, sju hashar, kapat nät

**Datum:** 2026-09-06
**Rigg:** Docker på Ubuntu 22.04 (x86_64), headless, `df -h /` före varje pull, `docker image rm` efter varje bild
**Prövar:** README-löftet "bara standardbiblioteket, på båda plattformarna" + fas 12:s "fastspikad version och kontrollerad hash"

## Metod (samma på varje bild)

Per bild: klona (bindmontering + `safe.directory`), `sok` utan VC (kräv exit 2 + instruktion),
`installera --mal` till fejkad mall, verifiera filer på plats, kör om (kräv `nya:0/uppdaterade:0`),
två stdlib-vägar: (a) import av varje `install/`-modul på bildens minimala python3,
(b) AST-genomgång minus `sys.stdlib_module_names` minus egna.

## Resultat

### 1. Alpine först — musl bryter INTE löftet (2026-09-06)

- Bild: `alpine:3.20` (digest `sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc`, amd64). `python3` saknas i basen; installerat via `apk add --no-cache python3 git` → `Python 3.12.13 [GCC 13.2.1]` (musl).
- `sok` utan VC: exit **2**, noll dokumentmappar / noll VC-mappar + utskrift av exakt `--mal`-kommando. Kravet (aldrig tyst nolla) håller på musl.
- `installera --mal /tmp/vc/My\ Commands/Python\ 2/vc_assist`: exit 0, `nya:11 uppdaterade:0 oforandrade:0`, `verifierat pa plats: 11 filer parsar och kompilerar`. Andra körningen: `nya:0 uppdaterade:0 oforandrade:11` — idempotent.
- Stdlib väg (a): `json hashlib urllib.request tarfile zipfile sqlite3 lzma ctypes ssl zlib bz2 xml.etree.ElementTree dataclasses ast argparse` — alla **OK**, inget saknas (Alpine-`python3` är komplett här).
- Stdlib väg (b): AST över `/src/install/*.py` ger importerna `argparse ast dataclasses datetime hashlib json ntpath os re shutil subprocess sys tarfile urllib winreg zipfile + __future__/install`. Minus `sys.stdlib_module_names` (innehåller `winreg` även på Linux) minus egna (`install paket upptackt installera verktygskedjan`): **inga externa**. (`install` är repots eget paket; min första körning listade det som externt för att egna-mängden var för snäv — korrigerat här.)
- Slutsats: dagens viktigaste fynd är positivt — den enda bild som kunde bryta löftet på riktigt gör det inte.

## LIMITS

- Denna fil är under arbete; siffror ovanför är preliminära tills varje delsektion anger härkomst (bilddigest + `python3 --version`).
- Windows (fas 13) prövas inte — ingen Windows-maskin finns.
- `darwin-*` verifieras endast som hash+storlek utan Mac.
- `linux-arm64` prövas endast under emulering om värden klarar det, annars hash+storlek.
- Disk på värden var 99% full vid start (7,8G ledigt); bilder dras en i taget och städas efteråt.
