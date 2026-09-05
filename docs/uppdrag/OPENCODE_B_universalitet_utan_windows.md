# Uppdrag B — universaliteten, allt utom Windows

Repo: `~/projects/VC_Assist`. Läs `docs/spec/00_index.md` först.

## Vad projektet lovar, och vad som är mätt

`README.md`: *"Ingen `pip install`. Ingen `requirements.txt`. Installationen och
tillägget använder bara standardbiblioteket, **på båda plattformarna**."*
`docs/spec/36_versioner.md` heter *"Versionsstöd — universalitet"*.

`M-90` prövade det på **en** ren maskin: en tom `ubuntu:24.04` utan `python3`
och utan `git`. Klona → `installera.py sok` → `installera --mal` fungerade,
elva filer verifierade på plats, ominstallation skrev noll, och en AST-genomgång
gav noll importer utanför standardbiblioteket.

Det är en distribution och en Pythonversion. Löftet gäller alla.

**Windows går inte att pröva** — det finns ingen Windows-maskin. Fas 13 står
öppen med det skälet och är inte ditt uppdrag. Allt annat går.

## Uppgiften

**1. Sprid distributionerna.** `debian:12`, `fedora:41`, `alpine:3.20`,
`archlinux`, `ubuntu:22.04`. Alpine är den intressanta: musl i stället för
glibc, och `python3` där saknar saker som är med på andra håll. För varje:
går klonen, går `sok`, går `installera --mal`, och är ominstallationen
idempotent?

**2. Sprid Pythonversionerna.** `python:3.9` till `python:3.13`, plus
`python:2.7` för tilläggets sida. `M-92` mätte att `ntpath.expanduser` svarar
**olika** i 2.7.18 och 3.13.11 när både `HOME` och `USERPROFILE` är satta — den
sömmen finns kvar och kan bita på fler ställen.

**3. Mät standardbiblioteket, inte bara påstå det.** `M-90` gjorde det två
vägar: varje modul importerad på en minimal `python3`, och en AST-genomgång av
`install/` som drar bort `sys.stdlib_module_names` och repots egna. Gör om
båda på varje bild. En modul som finns på Debian men inte på Alpine bryter
löftet utan att någon märker det.

**4. Verktygskedjan på var och en.** `install/verktygskedjan.py` hämtar
STruC++, OpenPLC och node med fastspikad version och kontrollerad hash.
Manifestet bär **sju** poster: `linux-x64`, `linux-arm64`, `darwin-x64`,
`darwin-arm64`, `win32-x64`, `win32-arm64`, `npm`. Bara `linux-x64` är
prövad (`M-56`). Prova `linux-arm64` under emulering om maskinen klarar det,
och **verifiera hashen på var och en du kan ladda** — hashen är löftet, inte
nedladdningen.

En sak står redan i koden och ska prövas, inte tros: `win32-arm64` och
`win32-x64` har **samma sha256 och samma storlek** i v0.6.6. De är
byte-identiska. Bekräfta det, eller motbevisa det.

**5. Node är inte versionsfäst.** Det står som en öppen punkt. Avgör vad som
händer med en annan nodversion än den `M-56` mätte, och fäst den om det behövs.

**6. Offline.** Det finns inget offlineläge. Vad händer när nätet är borta
mitt i en hämtning? En halv fil med rätt namn och fel hash är det farliga
utfallet. Prova det — kapa nedladdningen och se att hashkontrollen fäller och
att filen tas bort.

## Trasiga fall som måste falla

* En **manipulerad nedladdning** måste avvisas på hashen. Fixturen finns
  redan i andan i `M-56` — bygg den skarpt: byt en byte, kräv rött.
* En **halv fil** efter ett avbrutet nät får aldrig lämnas kvar och aldrig
  räknas som hämtad.
* `installera.py sok` på en maskin **utan** VC ska ge slutkod 2 och säga vad
  man ska göra — aldrig en tyst nolla. (Det är mätt på Ubuntu, kräv det på
  alla.)
* En distribution där en stdlib-modul saknas måste ge ett **namngivet** fel,
  inte en `ImportError` långt inne i en underprocess. `M-91` fann precis den
  formen: felet kom som `No module named vc_assist_svc` ur en underprocess,
  långt från sin orsak.

## Ofrånkomliga regler

* **Ingen stub som returnerar framgång. Ingen tröskel utan mätreferens. Ingen
  grind utan trasig fixtur.**
* Committa i **små steg**, scopat per fil: `git commit -q --only -m "$MSG" -- <sökväg>`.
  Kör **ALDRIG** `git reset` eller `git stash` utan sökväg — repot är delat med
  upp till tolv skrivare.
* `pytest | tail` ger **tails** returkod, inte pytests. Skriv till fil, läs
  `$?` separat.
* `tests/motbevis` **SKA vara röda**. Grön svit: `python3 -m pytest tests/enhet`.
* Är arbetsträdet rött: `python3 tests/protocol/kor_svit_mot_head.py` kör
  sviten i en ren `git worktree` av HEAD. Grönt där = det röda är någon annans
  pågående arbete.
* **Disken är trång.** Kolla `df -h /` innan du drar avbilder, städa med
  `docker image rm` efteråt, och fyll aldrig disken — operatören arbetar på
  samma maskin.
* Kör allt headless. Starta **inte** Visual Components; andra sessioner äger
  den. Rör **ALDRIG** `~/.wine-vc` — det är operatörens prefix.

## Filer du äger

`install/`, `tests/enhet/test_install.py`, `tests/enhet/test_verktygskedjan.py`,
`docs/spec/35_plattformar.md`, `docs/spec/36_versioner.md`, nya
`tests/protocol/kor_plattformar_*.py`. **Rör inte** `svc/vc_assist_svc/`
annat än om en mätning tvingar dig, och kolla då `git log -5 --oneline` på
filen först.

## Leverans

`docs/matningar/M-NN_<namn>.md` — ta ett **ledigt** nummer, kolla
`ls docs/matningar/` precis innan, och **skapa filen med en `## LIMITS`-stubb
direkt**. En tom reservationsfil fäller ärlighetsspärren för alla andra. Spärr
mot dubbla nummer, tak 0.

Uppdatera fas 12:s rad i `docs/spec/70_faser.md` och README:s fastabell när
något stängs — det finns en grind (`tests/enhet/test_readme_faser.py`) som
fäller om README säger mindre färdigt än specen.

Varje mätning slutar med `## LIMITS`. En siffras härkomst hör till siffran.

Rapportera: vilka distributioner och Pythonversioner som klarade sig, vilka som
inte gjorde det och varför, hashutfallet per manifestpost, och vad som fortfarande
bara är prövat på en maskin.
