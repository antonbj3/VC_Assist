# FAS 10 ACCEPTANS — paketering

**beskriver:** `install/__init__.py`, `install/upptackt.py`, `install/paket.py`,
`install/installera.py`, `tests/enhet/test_install.py`, `README.md`
**grind (70_faser.md):** *"Ren maskin: klona, installera, kör. Fungerar utan
handpåläggning."*
**kontrakt:** `docs/spec/35_plattformar.md`, `docs/spec/36_versioner.md`

## Status: STÄNGD 2026-09-05 (M-112).

Den sista punkten — *att VC startar med det installationen lade dit* — är mätt.
Sekvensen var ren: installera från repot (`nya 0, uppdaterade 1, oförändrade
10`, elva filer verifierade på plats), stoppa VC, starta med `~/bin/vc-test.sh`
headless på `:99` i testprefixet, och läsa bootloggen.

Tolv nya rader: mappen hittad, `bridge_cmd.py` laddad, startskriptet kört,
bryggkomponenten byggd. Och den lever — `ping` tur och retur **19,7 ms**,
`exec print(1+1)` ger `2`. Ett felskrivet anrop gav dessutom ett Python-spår ur
VC med sökvägen till installationens `pump.py`, vilket är det starkaste beviset
på var koden kom ifrån.

## Förutsättning

- Repot klonat. Inget installerat, inget byggt, inga paket hämtade.
- Python 3 på värdmaskinen. Ingenting utanför standardbiblioteket.
- Visual Components behöver **inte** vara igång, och behöver inte finnas alls
  för att de här proven ska gå att köra.

## Vad installationen är

Tre moduler och ett kommando:

| Fil | Ansvar |
|---|---|
| `install/upptackt.py` | söker upp VC:s tilläggsmapp. Skriver ingenting |
| `install/paket.py` | kopierar, verifierar på plats, avinstallerar |
| `install/installera.py` | kommandoraden: `sok`, `installera`, `verifiera`, `avinstallera` |

Sökningen antar aldrig en sökväg. Den letar efter mönstret
`<dokumentrot>/<företag>/<version>/My Commands/<Python N>/` och rapporterar
vad den hittade — företagsnamnet och versionen är variabler i **VC:s egen**
konfiguration (`MyCommandsFolder` i `VisualComponents.Engine.exe.config`),
så de skrivs inte i kod.

## Steg

1. `python3 install/installera.py sok` — läs vad som hittades
2. `python3 install/installera.py installera` — nyaste versionen
3. `python3 install/installera.py verifiera` — filerna på plats, mot repots källa
4. Kör om steg 2 — ingenting ska skrivas
5. `python3 install/installera.py avinstallera`
6. Jämför mappträdet före steg 2 med efter steg 5, sha256 per fil
7. `python3 -m pytest tests/enhet/test_install.py -q`

## Mätning

**Utförd 2026-09-04**, Linux, Python 3.13.11 och 3.10.12, mot ett attrappträd
i `/tmp` (inte mot operatörens VC-prefix — VC kördes av operatören).

| Storhet | Enhet | **Mätt** |
|---|---|---|
| sökningen på operatörens maskin | s | **0,05** (3 körningar: 0,06 / 0,05 / 0,05) |
| — wine-prefix genomsökta | antal | **5** |
| — dokumentmappar funna | antal | **2** (efter symlänksupplösning; 4 prefix pekar på den ena) |
| — VC-mappar funna | antal | **4** (två 4.10, två 4.9) |
| — VC-installationer funna via `api.xml` | antal | **2**, båda `Python 2` |
| installation | s | **0,159** |
| — filer lagda | antal | **9** |
| — byte | B | **104 711** |
| ominstallation, oförändrad källa | s | **0,174**, varav **0 filer skrivna** |
| verifiering av befintlig installation | s | **0,097** |
| avinstallation | s | **0,060**, **10 filer borttagna** (9 + manifestet) |
| trädet efter avinstallation | sha256 per fil | **identiskt med före**, 0 skillnader |
| enhetsprov | antal / s | **67 / 3,5** (3 körningar: 3,61 / 3,54 / 3,48) |
| hela sviten efter tillägget | antal | **grön**, 0 nya fel. Vid mätningen 838 prov före och 904 efter; repot växer parallellt i andra celler, så räkna om |

**Ren maskin, delvis:** `install/` och `ext/` kopierades ensamma till en tom
mapp och installationen kördes därifrån. Den fungerade — inget beroende på
resten av repot, inget beroende utanför standardbiblioteket.

## Godkänt när

- [x] Sökningen hittar alla installerade versioner, inte bara en, och sorterar
      **4.10 före 4.9** (numeriskt, inte lexikaliskt)
- [x] Två wine-prefix som delar `Documents` via symlänk rapporteras som **en**
      mapp med båda prefixen som källa (M-02)
- [x] Tillägget hamnar under `My Commands/<Python N>/vc_assist/`, aldrig direkt
      under `My Commands` (M-01: då fyrar kroken aldrig)
- [x] Python-nivån **söks** på disk; härleds ur versionsnumret bara när ingen
      finns, och märks då `harledd`
- [x] En sökväg som inte är mätt märks `OPROVAD SOKVAG` i utskriften
- [x] Installationen verifierar filerna **på plats**: sha256 mot källan, plus
      att varje fil parsar och kompilerar (M-09)
- [x] Andra körningen skriver ingenting, inte ens mtime
- [x] Avinstallationen tar bort exakt manifestets filer och lämnar allt annat
- [x] Trädet före installation och efter avinstallation är byte-identiskt
- [ ] **VC startar med det installationen lade dit.** Inte kört: operatören
      använde VC under hela fasen, och `~/.wine-vc-test` fick inte röras.
      Detta är fasens enda återstående L3-steg på Linux.

## Trasiga fall som måste falla

En grind som aldrig fällt något är oprövad (95_testprotokoll.md). Var och en
av dessa har en fixtur i `tests/enhet/test_install.py` som **fäller**:

| Fall | Förväntat | Prov |
|---|---|---|
| syntaxfel i en källfil | `Verifieringsfel`, **måldisken orörd** | `test_trasig_kalla_faller_och_ror_inte_maldisken` |
| SKRIPT-mallen trasig fast filen parsar | fälls | `test_trasig_skriptmall_faller_aven_om_filen_parsar` |
| SKRIPT-mallen utan `from vcScript import *` | fälls (M-06) | `test_skriptmall_utan_vcScript_importen_faller` |
| `__init__.py` utan `OnAppInitialized` | fälls | `test_saknad_OnAppInitialized_faller` |
| f-sträng i en fil som ska till Python 2 | fälls | `test_f_strang_faller_pa_python2_men_inte_pa_python3` |
| målverifieringen faller efter kopiering | filerna tas bort igen | `test_misslyckad_malverifiering_stadar_undan_sig_sjalv` |
| skrivskyddad målmapp | läsbart fel som namnger mappen | `test_skrivskyddad_malmapp_ger_lasbart_fel` |
| oläsbar mapp under dokumentroten | **varning**, sökningen fortsätter | `test_olasbar_mapp_ger_varning_inte_krasch` |
| okänd version utan Python-nivå | `IngenNiva`, ingen gissning | `test_okand_version_utan_niva_kastar` |
| avinstallation utan manifest | vägrar, rör ingenting | `test_avinstallation_utan_manifest_vagrar_gissa` |
| främmande fil i tilläggsmappen | lämnas kvar, rapporteras | `test_avinstallationen_ror_inte_frammande_filer` |
| ändrad fil i en installation | `verifiera` ger slutkod 1 | `test_cli_verifiera_faller_pa_andrad_fil` |

Den viktigaste är rad 2. Det är felet ur M-09 exakt: filen parsar, VC:s
`loadCommand` returnerar ett objekt, `execute()` kastar ingenting, och
modulkroppen körs aldrig — tyst. Grinden måste se det **på disk**, för det
finns ingenting att läsa i loggen efteråt.

## Vad som INTE är prövat

* **Windows.** Ingen VC-installation på Windows finns här (kontrollerat,
  `35_plattformar.md`). Windows-vägen — registrets `Shell Folders\Personal`,
  `%USERPROFILE%`, OneDrive-omdirigering, `%ProgramFiles%` — är kodad och
  **logiskt** prövad med en injicerad Windows-miljö mot ett attrappträd.
  Det är en prövning av logiken, inte av Windows. Ingen rad i det här
  dokumentet är en mätning på Windows.
* **VC 5.0.** Skolans licensserver har 4.10. Att 5.0:s tilläggsmapp heter
  `Python 3` är `36_versioner.md`:s ord "sannolikt", inte en mätning.
  Installationen kan lägga tillägget där, och märker sökvägen `OPROVAD`.
  Att VC 5.0 sedan **laddar** det är helt oprövat.
* **VC laddar det installerade tillägget.** Se den tomma rutan ovan. Att
  filerna är på plats, har rätt sha256 och kompilerar är vad som prövats.
  Att VC startar bryggan ur dem är fas 1:s L3, och den kördes mot en
  handinstallerad kopia, inte mot installationens.
* **En verkligt ren maskin.** Provet ovan kopierade `install/` och `ext/` till
  en tom mapp. Ingen ny maskin och ingen ny klon av repot har prövats.
* **Python äldre än 3.10.12.** Koden använder inget nyare än `dataclasses`
  (3.7), men 3.7–3.9 är inte körda.

## Plattform

Linux ☑ *(sökning, installation, verifiering, avinstallation — mot attrappträd
och mot maskinens verkliga mappstruktur i läsläge)*
Windows ☐ **oprövad**
VC 4.10 ☑ *(sökvägen är den mätta i M-01)*   VC 5.0 ☐ **oprövad**


---

## Tillägg 2026-09-05: verktygskedjan hör till löftet

Protokollet ovan skrevs innan fas 12 fanns. Löftet *"klona, installera, kör"*
täcker sedan dess ett steg till: en maskin som klonar repot har varken STruC++
eller dess beroenden, och utan dem kan grind 1 inte köras.

`M-71` körde hela kedjan ur en `git clone` av HEAD:

| Steg | Utfall |
|---|---|
| hela enhetssviten ur klonen | 5751 gröna (7 röda, kända och namngivna) |
| **verktygskedjan från noll**, tom cache | **5,00 s** |
| fullt bygge med debugkarta | 0,5 s, alla fyra artefakterna |
| grind 1–4 skarpt | alla fall stämde |
| ST-svepet mot riktiga kompilatorn | 190 gröna, 25,4 s |
| installationens sökning | 0,07 s |
| bara `install/` + `ext/` i tom mapp | fungerar |

### Godkänt när — tillägg

- [x] En ren klon kan hämta hela verktygskedjan utan handpåläggning
- [x] Grind 1 kör efteråt, med alla fyra artefakterna
- [ ] **VC startar med det installationen lade dit** — oförändrat öppet
- [ ] **Node är inte fastspikat.** Kedjan använder maskinens `node`. En
      maskin utan node faller, och det är inte prövat vad felet säger
- [ ] **Inget offlineläge.** Hämtningen kräver GitHub och npm
