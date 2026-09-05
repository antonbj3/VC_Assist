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

(TODO — fylls per bild i ordningen Alpine → Python → övriga → kedja → offline.)

## LIMITS

- Denna fil är under arbete; siffror ovanför är preliminära tills varje delsektion anger härkomst (bilddigest + `python3 --version`).
- Windows (fas 13) prövas inte — ingen Windows-maskin finns.
- `darwin-*` verifieras endast som hash+storlek utan Mac.
- `linux-arm64` prövas endast under emulering om värden klarar det, annars hash+storlek.
- Disk på värden var 99% full vid start (7,8G ledigt); bilder dras en i taget och städas efteråt.
