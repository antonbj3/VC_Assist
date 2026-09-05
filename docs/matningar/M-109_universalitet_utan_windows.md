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

### 2. Pythonversionerna 3.9–3.13 + 2.7 (2026-09-06)

- Bilder: `python:3.9/3.10/3.11/3.12/3.13-slim` (debian-baserade), en i taget + `rm` efteråt. Disk höll sig 7,7G ledigt.
- Alla fem: `sok` exit **2** + `Ingen VC-mapp`-instruktion (1 träff), `installera --mal` exit 0 med `nya:11`, andra körningen `nya:0 uppdaterade:0 oforandrade:11`. Ingen version sticker ut.
- Stdlib väg (a) alla fem: samtliga 15 provmoduler **OK** (`json hashlib urllib.request tarfile zipfile sqlite3 lzma ctypes ssl zlib bz2 xml ElementTree dataclasses ast argparse`).
- Stdlib väg (b): 3.10–3.13 `externa: inga` (303/305/301/290 namn i `sys.stdlib_module_names`). **3.9 saknar `sys.stdlib_module_names`** (tillkom i 3.10; `AttributeError`) — M-90:s AST-metod går inte att köra ordagrant där. Produkten använder inte attributet (`grep` i `install/ tests/ 36_versioner.md` ger noll träffar), så installationen går ändå; mätmetoden behöver fallback (hårdkodad lista) på 3.9. Lägsta krav att skriva i README: installationen går på 3.9, verifieringsmetoden kräver 3.10+.
- `ntpath.expanduser`-sömmen (M-92) bekräftad skarpt: `HOME=/home/x + USERPROFILE=C:\\Users\\x` ger `C:\\Users\\x` på **alla** 3.9–3.13 men `/home/x` på `python:2.7-slim` (2.7.18). Sömmen finns kvar; `plats.py`:s USERPROFILE-först-ordning är fortsatt rätt val.
- Tilläggssidan 2.7: alla 11 `.py` i `ext/vc_addon/vc_assist` kompilerar med `compileall` + `py_compile(doraise=True)` på 2.7.18 (första försöket såg ut att falla men felet var riggens: skrivskyddad bindmontering, `.pyc` kunde inte skrivas bredvid källan — omkört mot `/tmp`-kopia: OK).

## LIMITS (halv mätning — avslutad här)

- **Mätt:** Alpine 3.20 (musl) + Python 3.9–3.13 + tilläggssida 2.7.18. Allt grönt; två fynd (3.9 saknar `sys.stdlib_module_names`; `ntpath.expanduser`-sömmen 2.7 vs 3.x bekräftad).
- **Omätt (kvar från ersatta uppdraget):** `debian:12`, `fedora:41`, `archlinux`, `ubuntu:22.04`; verktygskedjans sju hashposter (inkl. `linux-arm64`-emulering, `darwin-*` hash+storlek, win32-identiteten); node-versionsfästning; offline/halv-fil-fallet; nya `kor_plattformar_*.py`; fas 12/README-uppdatering.
- Uppdraget som beställde denna mätning ersattes 2026-09-05 09:18 (commit 4c1486b) av tillförlitlighet-i-skala. Filen behålls som fristående delresultat; numret återanvänds inte.
- Windows (fas 13) prövas inte — ingen Windows-maskin finns.
- Disk på värden var 99% full vid start (7,6–7,9G ledigt); bilder drogs en i taget och städades med `docker image rm` efteråt.
