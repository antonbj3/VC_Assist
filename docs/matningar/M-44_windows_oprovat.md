# M-44 — Windows: vad som rättades, och vad som fortfarande är oprövat

**Datum:** 2026-09-04 · **Utfört på:** Linux (Wine 11.16) · **Windows-maskin:** fanns inte

## Vad den här mätningen mäter

Frånvaro. Kravet är *"ska fungera med och utan wine"*, *"windows dator eller
linux dator"*, *"universal och täcka alla"*. Hela projektet är byggt och mätt på
Linux med Visual Components under Wine. **Ingen rad i det här repot är en
mätning på Windows.** De flesta VC-användare kör Windows, så Windows är den
sannolikaste driftmiljön och den enda vi inte har rört.

Det som gick att göra härifrån är två saker, och bara två:

1. **Läsa koden** efter allt som antar Linux eller Wine, och rätta det som går
   att rätta utan en Windows-maskin.
2. **Pröva Windows-grenarna på Linux** genom att attrappera plattformen —
   `sys.platform`, miljövariablerna, separatorn, socketmodulen. Det prövar att
   grenen finns och väljer det den säger att den väljer. Det är **inte** en
   mätning på Windows, och står ingenstans som en.

Ingenting nedan säger att någonting fungerar på Windows.

---

## Del 1 — vad som var trasigt, med fil och rad

Numren är radnumren före rättelsen där rättelsen flyttat koden.

### F1. Tilläggsmappen hittas bara genom ett obegränsat `os.walk` över `~/Documents`

`ext/vc_addon/vc_assist/bridge_cmd.py:54–66` (`_tillaggsmapp`) läste
`VC_ASSIST_DIR` och krävde `os.path.isdir` på värdet. Men `__init__.py:34` satte
variabeln till `getApplicationPath()`, och **M-01 mätte att den ger en
`file:///`-URI**, inte en sökväg. `os.path.isdir("file:///C:/...")` är alltid
falskt, på båda plattformarna. Alltså föll funktionen *alltid* ned i
reservvägen: `os.walk(os.path.join(expanduser("~"), "Documents"))`.

Det fungerar under Wine därför att prefixets `Documents` är en symlänk till
värdens `~/Documents` (M-02). På Windows gäller inget av det:

* Är Dokument omdirigerad till OneDrive — normalfallet på en företags-Windows —
  finns `%USERPROFILE%\Documents` antingen inte alls eller som en tom rest. Då
  returnerar `_tillaggsmapp()` `None`, och `_starta()` (`bridge_cmd.py:384`)
  loggar *"hittade inte tillaggsmappen; bryggan startar inte"* och slutar.
  **Hela systemet är dött på den maskinen, efter en rad i en loggfil.**
* Är den inte omdirigerad går ett obegränsat `os.walk` över en OneDrive-synkad
  dokumentmapp — vid VC:s uppstart, på huvudtråden, där ingenting annat hinner
  gå, och där molnplatshållare kan tvingas ner från nätet.

Vår egen `install/upptackt.py` kan redan svaret (registrets `Shell
Folders\Personal`, `%OneDrive%`). Tillägget kunde det inte.

### F2. `expanduser("~")` betyder olika saker på de två sidorna av sömmen

Åtta ställen räknade ut `os.path.expanduser("~")` var för sig:
`pump.py:118,120,122,124`, `bridge_cmd.py:29,61,224,259,260`,
`oga_provtagning.py:596`, `__init__.py:18`.

Python 2.7:s `ntpath.expanduser` läser **`HOME` först** och faller tillbaka på
`USERPROFILE`. Python 3.8 och senare tog bort `HOME`-ledet helt (bpo-36264) och
läser `USERPROFILE` direkt. Bryggan kör i VC:s Python 2.7; tjänsten kör Python
3.13. Är `HOME` satt på Windows — Git for Windows, Cygwin, MSYS och en del
Java- och Emacs-installationer sätter den — skriver bryggan sin token i en mapp
tjänsten aldrig tittar i. Utfallet är `E_AUTH` eller `FileNotFoundError`, utan
att någon logg säger varför.

Skillnaden mellan de två standardbiblioteken är läst ur källan, inte gissad.
Att den biter på en verklig Windows-maskin är oprövat (punkt 3 nedan).

### F3. `SO_REUSEADDR` betyder inte samma sak på Windows

`ext/vc_addon/vc_assist/pump.py:201` satte `SO_REUSEADDR` villkorslöst.

* På Linux (och på Wines winsock, som är Linux under) tillåter flaggan bindning
  över en port i `TIME_WAIT`, men **inte** över en levande lyssnare.
* På riktig Windows tillåter `SO_REUSEADDR` en andra socket att binda samma
  adress medan den första **lyssnar**. Bindningen lyckas, och vilken socket som
  får en inkommande anslutning är inte definierat.

Bryggan hänger på den första semantiken. `Brygga.starta` binder **före** den
skriver tokenfilen, och kommentaren på `pump.py:206–212` säger varför: en andra
brygga i samma process — till exempel ur en sparad layout som bär med sig
brygg-komponenten — skrev över den levande bryggans token och föll sedan på
bindningen, varpå den levande blev onåbar med `E_AUTH`. På Windows skulle den
andra bindningen **lyckas**. Skyddet är då borta, och felet är tillbaka.

### F4. ZIP-posterna får bakstreck på Windows

`svc/vc_assist_svc/plc/paket.py:274`: `z.write(os.path.join(katalog, rel), rel)`
där `rel = os.path.relpath(full, katalog)`.

`zipfile.ZipInfo.from_file` gör **inte** om `os.sep` till `/` — den kör
`normpath` och kapar inledande separatorer, ingenting mer (verifierat mot
CPython 3.13:s källa; provet `test_zipfile_gor_INTE_oversattningen_at_oss`
visar det). ZIP-formatet kräver `/` (APPNOTE 4.4.17.1). På Windows blir posten
alltså `strucpp_runtime\include\foo.h`. Uppackad i runtimens Linux-container
blir det **en fil vars namn innehåller bakstreck**, i arkivets rot — inte en
katalog. `scripts/compile.sh` hittar då inga headers, och bygget faller på
`Missing required source files`.

Det här är det enda fyndet där utfallet på Windows går att härleda utan att
köra: det följer ur ZIP-formatet och ur CPython:s källa.

### F5. Genererade textfiler skrevs i textläge utan `newline`

`svc/vc_assist_svc/plc/paket.py:182` skrev `program.st` med
`open(..., "w", encoding="ascii")`. På Windows översätter textläget varje `\n`
till `\r\n`. Raden efter räknar `md5 = hashlib.md5(kompilatortext.encode(...))`
över strängen i minnet — alltså över LF-text. `PROGRAM_MD5` i `defines.h` hade
då beskrivit en text som aldrig funnits på disk. Samma sak för `defines.h`
(rad 202), `conf/opcua.json` (rad 241) och `signalkarta.py:414`.

Om STruC++ 0.6.6 också stör sig på `\r` är oprövat; `newline="\n"` gör frågan
ointressant.

### F6. Radsluten i repot självt

Repot hade ingen `.gitattributes`. Git for Windows installeras med
`core.autocrlf=true` som standard, så en klon på Windows skriver **CRLF** i
arbetsträdet. `install/paket.py` kopierar tilläggets filer byte för byte
(`shutil.copyfile`, jämförelse med sha256), så CRLF följer rakt in i VC.

Det farliga ledet är `bridge_cmd.py:SKRIPT`: en trippelciterad sträng vars
*värde* då bär `\r\n`, och som skickas till VC som skriptkällkod. Python 2:s
`compile()` tar bara `\n` — universella radslut i `compile()` kom först i
Python 3.2.

Och vår egen grind hade sagt grönt: `install/paket.py:granska_pythonfiler`
kompilerar med värdmaskinens Python 3, som accepterar CRLF utan ett ord.
En trasig installation hade rapporterat att den gick bra.

### F7. Fyra provskript bar en Linux-sökväg som standardvärde

`tests/protocol/kor_fas1.py:251`, `kor_fas2.py:121`, `kor_fas5.py:98`,
`kor_fas5_layout.py:201`, `kor_fas6_slinga.py:113`:

```
default=os.path.expanduser("~/.wine-vc-test/drive_c/users/anton/vc_assist_token")
```

Tre antaganden i en sträng: att det finns ett wine-prefix, att det heter
`.wine-vc-test`, och att användaren heter `anton`. Alla tre är falska på
Windows.

### F8. Operatörsdokumentationen gav en Wine-only-åtgärd

`docs/spec/24_samtalsloopen.md:154`, `27_operatorsflodet.md:76` och
`28_lagen_och_aterhamtning.md:120` säger åt operatören att köra
`~/bin/vc-stoppa.sh` (som gör `wineserver -k`) när porten är upptagen. På
Windows finns ingen `wineserver` och inget sådant skript. Texten är i specen,
inte i Linux-bilagan.

### F9. Sådant som är kontrollerat och som INTE var trasigt

* `127.0.0.1` används genomgående, aldrig `0.0.0.0` (`pump.py:203`,
  `klient.py:52`, provskripten). TCP på loopback beter sig likadant. Oförändrat.
* Inga `pgrep`, `pkill`, `os.kill`, `SIGSTOP`, `subprocess(shell=True)` eller
  `sh -c` i någon kodfil. `subprocess` förekommer på exakt ett ställe
  (`plc/paket.py:188`, `node`) och i ett testverktyg, båda som argumentlistor.
  `harness/forgranskning.py:81` har `subprocess` som ett **förbjudet** namn.
* Inga otillåtna Windows-filnamnstecken konstrueras: alla filnamn är
  konstanter, och `utkatalog`/`zipvag` kommer utifrån.
* `install/upptackt.py` och `install/paket.py` var redan Windows-medvetna
  (registrets `Personal`, `%OneDrive%`, `os.path.join` genomgående, injicerbar
  `Miljo`). Den delen är genomarbetad, och den här mätningen rör den bara med
  CRLF-grinden.
* OpenPLC nås över en URL som är ett konstruktorargument (`openplc.py:90`),
  aldrig en konstant. Var runtimen kör är konfiguration.

---

## Del 2 — vad som rättades, och hur rättelsen är prövad

Alla prov kör på Linux, utan VC. Totalt **74 nya prov**
(`tests/enhet/test_plats.py` 44, `test_tokenplats.py` 15, tillägg i
`test_install.py` 3 och `test_plc.py` 3, plus parametriseringar).

| Fynd | Rättelse | Prövad hur |
|---|---|---|
| F1 | Ny `ext/vc_addon/vc_assist/plats.py`. `tillaggsmapp()` provar `VC_ASSIST_DIR` som sökväg, sedan som `file:///`-URI, sedan en **djupbegränsad** sökning under *alla* dokumentmappar som finns — inklusive `%OneDrive%\Documents`. `__init__.py` översätter URI:n och lägger mappen på `sys.path` innan `bridge_cmd.py` laddas | attrappträd i `tmp_path`: paketet läggs i OneDrive-grenen och hittas med `plattform="win32"`; `test_windows_sokningen_hittar_i_onedrive` |
| F1 | Djupgräns `MAXDJUP = 6`, härledd ur M-01:s sökväg (`<företag>/<version>/My Commands/Python N/vc_assist/pump.py`), inte satt på känsla | `test_djupgransen_slapper_igenom_M01_men_stoppar_djupare` bygger trädet på tre djup och kräver träff på ≤6 och **ingen** träff djupare |
| F2 | `plats.anvandarmapp()` med en **uttalad** ordning: `VC_ASSIST_HEM`, sedan `USERPROFILE` (Windows), sedan `HOMEDRIVE`+`HOMEPATH`, sedan `HOME` (posix), sist `expanduser`. Alla åtta ställena går genom den | fem injicerade miljöer, däribland Windows **med** `HOME` satt och `HOME != USERPROFILE`; `test_home_pa_windows_ar_precis_det_som_hade_delat_sommen` |
| F2 | `__init__.py` och `bridge_cmd.py` kör före `sys.path` finns och bär därför uppstartskopior av samma logik | `test_uppstartskopian_i_init_svarar_som_plats` plockar ut funktionerna med `ast` och kör dem mot `plats` över samma tabell URI:er och miljöer. Glider de isär faller provet |
| F3 | `pump.valj_adressflagga()`: `SO_EXCLUSIVEADDRUSE` på **riktig** Windows, `SO_REUSEADDR` på Linux **och under Wine**. Wine detekteras på `ntdll.wine_get_version`. Wines beteende är därmed bit för bit oförändrat — det är det enda som är mätt | falsk socketmodul och falsk `ctypes`: fyra prov, ett per gren, plus ett som kräver att den riktiga modulen på den här maskinen ger `SO_REUSEADDR` |
| F4 | `plc/paket.py:arkivnamn()`, separatorerna som argument. Postnamnen är alltid `/` | `test_arkivnamn_oversatter_windows_separatorn` injicerar `sep="\\"`; `test_zipfile_gor_INTE_oversattningen_at_oss` visar varför funktionen behövs |
| F5 | `newline="\n"` på `program.st`, `defines.h`, `conf/opcua.json` och signalkartan | befintliga PLC-prov (91) går igenom; filerna är nu byte-identiska med det md5:n räknas över |
| F6 | `.gitattributes` med `* text=auto eol=lf` (och `docs/referens/** -text`, VC:s egna CRLF-filer lämnas i fred). Dessutom **ny grind** i `install/paket.py`: en källfil med CRLF stoppar installationen | `test_crlf_i_kallan_faller` gör en CRLF-kopia, visar först att **värdmaskinens Python 3 kompilerar den utan ett ord**, och kräver sedan att grinden fäller. `test_crlf_stoppar_installationen_och_ror_inte_maldisken` kräver att måldisken är orörd. `test_ensamt_cr_utan_lf_ar_inte_crlf` hindrar grinden från att bli för bred |
| F7 | Ny `svc/vc_assist_svc/tokenplats.py`. Söker: `VC_ASSIST_TOKEN`, sedan `plats.anvandarmapp()` på Windows, sedan varje wine-prefix `drive_c/users/<du>` på Linux. Senast skriven vinner. Provskripten har inget standardvärde längre | 15 prov, båda plattformarna injicerade: OneDrive-fri Windows-profil, Windows **med** `HOME` satt, två wine-prefix där det nyare vinner, `Public` som hoppas över, och en trasig fixtur där `VC_ASSIST_TOKEN` pekar fel och en giltig token ligger bredvid — den får **inte** användas |
| F8 | Windows-ledet inskrivet i de tre spec-raderna, märkt **OPRÖVAT** | ingen automatisk grind; det är text |

Nya konstanter med härkomst: `plats.MAXDJUP = 6`.
`python3 -m pytest tests/enhet/test_troskelharkomst.py -q` går igenom.

### Vad rättelserna medvetet INTE gör

* De ändrar **ingenting** i Wine-vägen. `valj_adressflagga` ger Wine samma
  flagga som förut, `anvandarmapp` ger under Wine samma svar som `expanduser`
  gav (`USERPROFILE` = `C:\users\<du>`), och sökningen efter tilläggsmappen
  behåller den gamla vägen som sista utväg. Det som är mätt får inte röras av
  en rättelse för något som inte är mätt.
* De påstår inte att Windows fungerar. Varje ny gren är prövad som **gren**,
  mot en attrapp. Se listan nedan.

---

## Del 3 — det som bara kan avgöras på en Windows-maskin

Ett körbart provprotokoll. Varje punkt: exakt vad någon ska köra, och exakt
vilket svar som betyder grönt. Ingen punkt får kryssas av på något annat sätt.

**Förutsättning:** Windows med Visual Components installerat och licensierat,
Python 3.9+ på `PATH`, repot klonat.

1. **Klonen har LF.** Kör i en **ny** klon:
   `python -c "print(b'\r\n' in open('ext/vc_addon/vc_assist/bridge_cmd.py','rb').read())"`
   **Grönt:** `False`. Rött betyder att `.gitattributes` inte slog igenom;
   klona om med `git clone --config core.autocrlf=false`.

2. **Installationen hittar VC.** `python install\installera.py sok`
   **Grönt:** minst en rad under *"VC-mappar"* med en verklig sökväg under
   Dokument, och `Python-nivaer pa disk` som inte är `ingen`. Slutkod 0.
   **Detta är punkten som avgör F1** — står det `(ingen)` är dokumentmappen
   omdirigerad på ett sätt vi inte hittar, och inget nedanför går att köra.

3. **Sömmen pekar på samma mapp.** Kör med `HOME` satt till något annat än
   `USERPROFILE` (det svåra fallet, F2):
   `set HOME=C:\msys64\home\%USERNAME%` och sedan
   `python -c "import sys;sys.path.insert(0,'ext/vc_addon/vc_assist');import plats;print(plats.anvandarmapp())"`
   **Grönt:** utskriften är `%USERPROFILE%`, inte `%HOME%`.
   Kör sedan samma sak i VC:s egen Python 2.7 (steg 5 skriver loggen som visar
   var bryggan faktiskt la sina filer). **Grönt:** samma mapp i båda.

4. **Installationen lägger paketet rätt.** `python install\installera.py installera`
   **Grönt:** `verifierat pa plats: N filer parsar och kompilerar`, slutkod 0,
   och raden `MATT: exakt den har sokvagen ar kord i VC 4.10 (M-01)` om VC är
   4.x. Står det `OPROVAD SOKVAG` är det VC 5.x, och då är även Python-nivån
   oprövad (`Python 3`, omätt enligt `36_versioner.md`).

5. **Tillägget laddas.** Starta VC. Öppna `%USERPROFILE%\vc_assist_boot.log`.
   **Grönt:** raderna `OnAppInitialized`, `tillaggsmapp: <verklig sökväg> (ur
   file:///...)`, `loadCommand uri=...`, `bridge_cmd executed`, och från
   kommandot `tillaggsmapp: <sökväg> (VC_ASSIST_DIR som file:///-URI)`.
   **Detta är beviset för F1.** Står det `(sokning under dokumentmapparna)` har
   URI-översättningen inte hållit — fungerar ändå, men noteras.
   Finns loggfilen inte alls har tillägget inte laddats, och VC säger inget
   själv (M-01, M-09).

6. **Bryggan binder, och med rätt flagga.** Öppna
   `%USERPROFILE%\vc_assist_brygga.log`. **Grönt:** `adressflagga:
   SO_EXCLUSIVEADDRUSE` följt av `lyssnar pa 127.0.0.1:8901`.
   Står det `SO_REUSEADDR` har Wine-detektionen sagt fel på en riktig
   Windows-maskin, och F3 är öppet igen.
   Står det `ingen (Windows utan SO_EXCLUSIVEADDRUSE)` saknar den Pythonen
   konstanten — notera vilken Python-version.

7. **Dubbelbindning avvisas.** Med VC igång, kör:
   `python -c "import socket;s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',8901));print('BAND — HÅLET FINNS')"`
   **Grönt:** `OSError`/`WinError 10048`. Skrivs `BAND` ut kan vem som helst
   kapa bryggans port, och tokenskyddet i `Brygga.starta` är verkningslöst.
   Det här är det enda provet som mäter F3:s verkliga storhet.

8. **Omstart efter krasch.** Döda VC hårt (Aktivitetshanteraren), starta om
   direkt, läs brygg-loggen. **Grönt:** `lyssnar pa 127.0.0.1:8901` inom en
   minut. Rött (`KUNDE INTE BINDA`) betyder att `SO_EXCLUSIVEADDRUSE` inte
   släpper förbi en socket i `TIME_WAIT` — då behöver punkt 6 tänkas om, och
   det är den enda kända risken rättelsen i F3 själv för med sig.

9. **Tjänsten hittar token.**
   `python -c "import sys;sys.path.insert(0,'svc');from vc_assist_svc.tokenplats import tokenfil;print(tokenfil())"`
   **Grönt:** en sökväg under `%USERPROFILE%`, och filen är den VC nyss skrev
   (jämför tidsstämpel). Rött ger ett `TokenSaknas` som räknar upp exakt vilka
   ställen som provades — läs listan innan något annat.

10. **Tur och retur över bryggan.**
    `python tests\protocol\kor_fas1.py`
    **Grönt:** samma slutrad som på Linux — alla elva steg och de sex trasiga
    fallen. Delresultat räknas inte; ett halvt fas 1 är inte fas 1.

11. **Ögat mäter.** `python tests\protocol\kor_fas2.py`
    **Grönt:** `vc_assist_eyes.json` skrivs i `%USERPROFILE%`, och provtakten
    ligger inom samma band som M-03 mätte på Linux. Ligger takten utanför är
    det en **ny mätning**, inte ett fel — Windows schemaläggare är inte Wines,
    och pumpens tal (`PAUS_TOM`, `PAUS_AKTIV`, `TICK_BUDGET_S`) är mätta under
    Wine.

12. **ST-kedjan bygger.** Med Node på `PATH`:
    `python -c "import sys;sys.path.insert(0,'svc');from vc_assist_svc.plc import paket"` och kör
    `paket.bygg_projekt(...)` mot ett strucpp-paket.
    **Grönt:** `projekt.zip` skapas, och
    `python -c "import zipfile;print([n for n in zipfile.ZipFile('projekt.zip').namelist() if '\\\\' in n])"`
    skriver `[]`. **Detta är beviset för F4.** En icke-tom lista betyder att
    arkivet är obrukbart för runtimen.

13. **`node` går att starta.** Om punkt 12 faller med
    `kunde inte starta node` — kontrollera om Node ligger som `node.cmd`
    i stället för `node.exe`. `subprocess` utan `shell=True` startar inte
    `.cmd`-filer på Windows. **Grönt:** punkt 12 kör igenom; annars ska
    `node`-argumentet peka på `node.exe` med full sökväg.

14. **OpenPLC nås.** Runtimen kan ligga i Docker Desktop, i WSL2 eller på en
    annan maskin. `python tests\protocol\kor_fas6_slinga.py --plc <bas-URL>`
    **Grönt:** samma slutrad som på Linux.
    Notera: körs runtimen i WSL2 eller i Docker Desktop är `127.0.0.1` från
    VC:s sida **inte** samma värd som runtimens `127.0.0.1`. OPC UA-endpointen
    är både annonserad och bunden adress (`opcuakonfig.py:94`), så en adress
    som fungerar på Linux kan behöva bytas här.

15. **Tokenfilens rättigheter.** `pump.py` gör `os.chmod(tokenfil, 0o600)`.
    På Windows sätter `chmod` bara skrivskyddsflaggan; åtkomsten styrs av
    ACL:er. Kör `icacls %USERPROFILE%\vc_assist_token`.
    **Grönt:** ingen rad ger andra användare läsrätt. Gör den det bärs skyddet
    enbart av loopback-bindningen, och det ska stå i drift-dokumentationen.

16. **Avinstallationen städar.** `python install\installera.py avinstallera`
    **Grönt:** `borttagna filer: N`, `LAMNADE KVAR` saknas, och mappen är borta.
    Python 2 lägger `pump.pyc` bredvid `pump.py`; kontrollera att inga
    `.pyc`-filer står kvar.

Punkterna 1–2 och 5 avgör om något alls går. 6–7 avgör F3. 12 avgör F4.
3 och 9 avgör F2.

---

## Vad jag bedömer går sönder först, och varför

**1. Tilläggsmappen (F1, protokollpunkt 2 och 5.)** Det är det enda felet som
är *tyst och totalt*: VC säger ingenting om ett tillägg som inte laddas (M-01),
och den gamla koden gav upp efter en enda lograd. Sannolikheten är hög därför
att OneDrive-omdirigering av Dokument är standard på en företags-Windows och
inte ett kantfall. Rättelsen gör svaret bredare, men den är prövad mot ett
attrappträd — inte mot en riktig OneDrive med molnplatshållare, som beter sig
annorlunda i `os.listdir` och `os.path.isdir`.

**2. ZIP-posterna (F4, punkt 12.)** Det här är det enda fyndet där jag kan
härleda utfallet utan att köra: ZIP-formatet kräver `/`, CPython gör inte om
det, och runtimen packar upp på Linux. Det hade fallit första gången någon
byggde ett projekt från Windows. Rättelsen är prövad med separatorn injicerad,
vilket täcker just den omvandlingen — men inte hela vägen genom en verklig
körning.

**3. Portkapningen (F3, punkt 7.)** Låg sannolikhet att den syns i vardagen,
hög kostnad när den gör det: felet ser ut som `E_AUTH` från en brygga som
uppenbart lever, och det var precis det felet som en gång kostade mest att
hitta. Rättelsen är den av de fem som bär mest egen risk — punkt 8 finns just
för att fånga att `SO_EXCLUSIVEADDRUSE` inte gör en omstart efter krasch värre.

**4. Ögats tal (punkt 11.)** Inte ett fel, men det som är mest sannolikt att
mäta *annorlunda*. `PAUS_TOM`, `PAUS_AKTIV`, `TICK_BUDGET_S` och hela M-03 är
mätta mot Wines schemaläggare på den här maskinen. Går de isär på Windows är
det en ny mätning som ska skrivas, inte en tröskel som ska justeras.

---

## Räckvidd

`docs/spec/35_plattformar.md` säger: *"Varje fas som stänger med en mätt grind
ska köras på båda plattformarna innan fasen räknas som klar."* Det står kvar
oförändrat. Ingen fas är stängd på Windows.

M-24 i `RESERVERADE.md` — *"Hela vägen på Windows"* — är fortfarande oreserverad
av den här mätningen och obesvarad. M-44 är listan över vad M-24 ska pröva.
