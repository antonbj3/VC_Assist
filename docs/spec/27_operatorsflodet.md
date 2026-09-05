# Operatörsflödet

**beskriver:** `install/installera.py`, `install/upptackt.py`, `install/paket.py`,
`ext/vc_addon/vc_assist/`, `svc/vc_assist_svc/`
**kontrakt:** `26_appen.md`, `31_brygga_protokoll.md`, `35_plattformar.md`,
`36_versioner.md`, `50_grindar.md`, `70_faser.md`

Hela vägen, från en tom VC till en levererad cell. Först när det går bra, sedan
när det inte gör det.

---

## 1. Förutsättningar

| Sak | Windows | Linux med Wine | Stämpel |
|---|---|---|---|
| Visual Components | 4.10 eller 5.0, med licens | samma | 4.10 **MÄTT**, 5.0 **oprövad** (`36_versioner.md`) |
| Python för tjänsten | 3.x på värden | 3.x på värden | |
| Wine | — | **≥ 11.15**, här 11.16 | **MÄTT**: under 11.15 dör licensmotorn på bcrypt `HashBlockLength`, 677005 |
| d3d9 | — | **DXVK** native | **MÄTT** |
| `d3dx9_43`, `d3dcompiler_43` | — | **native** | **MÄTT**: Wines egna ger svart 3D-vy och evig omritningsloop |
| Licens | leverantörens | här skolans licensserver via VPN, `~/bin/vpn-skolan.sh start` | **MÄTT** |
| OpenPLC v4 | valfri maskin, adressen är konfiguration | samma | |

Wine-raderna är **driftsnoteringar**, inte systemkrav (`35_plattformar.md`).
De hör hemma i `docs/drift/linux_wine.md` och upprepas här bara för att
operatörens första start går genom dem.

---

## 2. Installation

```
git clone <repo>
cd VC_Assist
python3 install/installera.py sok
python3 install/installera.py installera
python3 install/installera.py verifiera
```

`sok` skriver ingenting till disk. Den visar vilka VC-installationer, vilka
dokumentrötter och vilka `Python N`-nivåer som faktiskt finns.

### 2.1 Vad installationen gör, och varför varje steg finns

| Steg | Vad | Mätt skäl |
|---|---|---|
| 1 | Söker `<dokumentrot>/<företag>/<version>/My Commands` i stället för att skriva "Visual Components" i koden | VC:s egen config har både företag och version som **variabler** (`VisualComponents.Engine.exe.config`, `MyCommandsFolder`) |
| 2 | Väljer `Python N`-nivå efter vad som **finns på disk**, härleder bara när ingen finns, och märker då resultatet oprövat | **M-01**: `My Commands/Python 2/<paket>/__init__.py` fungerar, `My Commands/<paket>/__init__.py` gör det **inte** — kroken fyrar aldrig, utan ett ord |
| 3 | Löser upp `realpath` och rapporterar prefix som pekar på samma mapp | **M-02**: ett wine-prefix `Documents` är som standard en **symlänk** till värdens `~/Documents`. Två prefix delar då tillägg |
| 4 | Granskar källfilerna **före** kopiering: varje `.py` parsar, skriptmallen parsar **efter formatering**, mallen börjar med `from vcScript import *`, filer som skriver till VC har `_s()` | **M-09**: en trasig trippelcitering gjorde modulen okompilerbar och VC sa **ingenting** — `loadCommand` returnerade ett objekt och `execute()` kastade inte. **M-06**: utan `from vcScript import *` dör `OnRun` tyst. **M-05**: unicode in i VC:s py2-bindning ger `SystemError` |
| 5 | Granskar filerna **på plats** igen, med `sha256` per fil | en kopiering kan gå halvt |
| 6 | Skriver ett manifest, `vc_assist_installation.json`, med filnamn och summor | en avinstallation som gissar raderar för lite eller för mycket |
| 7 | Städar efter en misslyckad installation: tar bort exakt det den lade dit | S1: en ofärdig väg kastar, den lämnar aldrig något halvt |

### 2.2 Installationens grind

| # | Godkänt när |
|---|---|
| **F-G1** | `sok` listar minst en VC-mapp, och för varje mapp står det om sökvägen är **mätt** (4.x + `Python 2`) eller **härledd** |
| **F-G2** | `installera` skapar exakt de filer manifestet listar, och `verifiera` ger noll problem |
| **F-G3** | `avinstallera` lämnar mappen i det skick den hade före, och manifestet är borta |
| **F-G4** | Ett avsiktligt trasigt tillägg **avvisas av installationen**, inte av VC. Grinden kostar 0,05 s och kör utan VC (`tests/enhet/test_tillagg_syntax.py`) |

---

## 3. Första start — de fem tysta fällorna

Alla fem är mätta. Alla fem ser ut som att ingenting hände.

| # | Fälla | Vad operatören ser utan skydd | Skydd |
|---|---|---|---|
| 1 | Fel `Python N`-nivå | VC startar normalt. Inget tillägg. Ingen rad någonstans (**M-01**) | installationen väljer nivå ur disk, aldrig ur gissning; grön start §4 |
| 2 | Syntaxfel i tilläggets moduler | `loadCommand` returnerar ett objekt, `execute()` kastar inget, kroken loggar `executed`, modulkroppen körs **aldrig** (**M-09**) | granskning på disk före start, i båda riktningarna (källa och mål) |
| 3 | `OnRun` utan `from vcScript import *` | pumpen startar aldrig, felet slukas (**M-06**) | mallgranskning i installationen; bryggan loggar sin egen start |
| 4 | Port 8901 upptagen av en kvarlevande `wineserver` | bryggan binder inte, undantaget slukas i `OnRun`, **noll rader någonstans** (**M-13**, sidofynd) | loggen skrivs **före** bindningen (`Brygga.starta`); på Linux gör `~/bin/vc-stoppa.sh` `wineserver -k` och kontrollerar att porten är fri. På Windows finns ingen motsvarighet: `netstat -ano | findstr :8901`, avsluta PID:et. **OPRÖVAT** (M-44) |
| 5 | Ingen licens | VC startar inte, eller startar utan de förmågor tillägget behöver | förmågerapporten säger vilka ytor som finns; VPN startas av `vc.sh` innan VC |

**Regel F-1.** Tystnad är aldrig ett kvitto. Efter en start ska operatören
kunna se **tre filer**, och panelen ska visa dem.

---

## 4. Grön start

| Fil | Skrivs av | Betyder |
|---|---|---|
| `~/vc_assist_boot.log` | `__init__.py` och `bridge_cmd.py` | kroken fyrade, kommandot laddades, skriptet kompilerade |
| `~/vc_assist_formaga.json` | `formaga.skriv` genom bryggan | vilka API-ytor som finns i **denna** VC |
| `~/vc_assist_token` | `Brygga._skriv_token` | den delade hemligheten tjänsten läser |

Sökvägarna är KOD@HEAD (`pump.Brygga.__init__`, `bridge_cmd`). På Windows är
`~` användarens profil; under Wine ligger de i prefixets användarmapp.

| Storhet | Krav | Härkomst |
|---|---|---|
| Tid från VC:s processtart till att port 8901 lyssnar | **≤ 60 s** | **PRELIMINÄR.** M-12 mätte 13 s mellan `OnStart` och `OnAppInitialized`; resten är marginal. Sätts av **M-23** |
| `formaga.json` finns | ja | |
| Ytor som finns | **46 av 46** vid 4.10 | **MÄTT**, fas 5 |
| `ping` tur och retur, median | **< 50 ms** | **MÄTT 9,91 ms** (M-03) |

**Regel F-2.** Saknas någon av de tre filerna efter 60 s säger panelen exakt
vilken som saknas och vilken av de fem fällorna det pekar på. Den säger aldrig
bara *"kunde inte ansluta"*.

---

## 4.5 Från att programmet öppnas till att panelen lever

Grön start ovan säger vad som ska finnas på disk. Det här säger vad **operatören
gör**, i ordning, och vad han ser när steget inte går igenom. Varje rad har en
härkomst: **MÄTT**, **KOD@HEAD**, **DOK** eller **ANTAGET**.

| # | Steget | Vad som ska hända | Vad som kan gå fel | Vad han ser då | Stämpel |
|---|---|---|---|---|---|
| A1 | **Licens och VPN** | `~/bin/vpn-skolan.sh start` innan VC | VPN nere, eller fel produkt på licensservern | VC startar inte, eller startar utan förmågorna. Förmågerapporten namnger ytorna som saknas | **MÄTT** — licensserverns feature mismatch är ett eget fel, inte platsbrist |
| A2 | **Starta VC** | VC:s process startar, `OnAppInitialized` fyrar | fel `Python N`-nivå ⇒ inget tillägg, ingen rad någonstans | panelen säger vilken av de tre filerna som saknas och vilken av de fem fällorna det pekar på (regel F-2) | **MÄTT M-01** |
| A3 | **Tillägget laddas** | `loadCommand` + `bridge_cmd executed` + skriptet kompilerar | syntaxfel i modulen: `execute()` kastar inte, modulkroppen körs aldrig | stegen i `28_lagen...` §5.3 stannar på steg 2 eller 3 och visar loggens egen rad | **MÄTT M-09** |
| A4 | **Bryggan binder porten** | `startar pa …` följt av `lyssnar pa …` | porten hålls av en kvarlevande `wineserver` | *"Ingenting lyssnar på 127.0.0.1:8901."* + `vc-stoppa.sh` på Linux, `netstat -ano` på Windows | **MÄTT M-13** (sidofynd); Windows **OPRÖVAT** (M-44) |
| A5 | **Starta tjänsten** | operatören startar den via installationens genväg | tillägget får inte starta processer, så ingenting gör det åt honom | inget alls händer förrän han startar den. Det är en **ANTAGEN** väg, inte en byggd | **ANTAGET** — `35_plattformar.md` regel 4 förbjuder `subprocess` inifrån VC |
| A6 | **Öppna panelen** | `http://127.0.0.1:8902`, loopback endast | ingen webbläsare, eller adressen okänd | menyval 1 i VC visar adressen — men menyytan är **oprövad** (M-21) | **ANTAGET** — ytan är inte byggd, valet webbläsare/terminal är öppet |
| A7 | **Tjänsten läser tokenet** | `~/vc_assist_token`, omskrivet vid varje bryggstart | gammalt token ⇒ `E_AUTH` | *"Tokenet är från en tidigare VC-session."* Tjänsten läser om filen och försöker en gång till, och **säger att den gjorde det** | KOD@HEAD |
| A8 | **Första `ping`** | svar inom `T_ping`, RTT ~10 ms | anslutningen går att öppna men inget svar kommer | **inte** `ansluten`. En lyckad `connect()` är inget livstecken (regel L-1); läget blir `obestämt` tills något svarar | **MÄTT M-03** (RTT); L-1 **HÄRLEDD**, Wine-halvan oprövad (M-25) |

**Regel F-10.** Varje steg A1–A8 har ett eget besked. Ingen av dem får svara
*"kunde inte ansluta"*: det är sant om alla åtta och till hjälp i noll.

**Det som inte är byggt, och det står här och inte i en fotnot:** A5 och A6 är
**ANTAGNA**. Ingen genväg läggs av installationen i dag, och ingen panelyta
finns — varken webbsida eller terminalvy. Det som finns är texten de skulle ha
visat (`svc/vc_assist_svc/forlopp/` och `svc/vc_assist_svc/aterhamtning/`) och
grindarna som dömer den. Valet mellan webbläsare och terminal står öppet i
`26_appen.md` §7, och att bygga fönstret innan valet är gjort vore att göra
valet i förbifarten.

---

## 5. Ett fullständigt genomlopp

Turens mekanik — verktygsloopen, honesty-rewrite, verify-contract och den
slutna händelselistan — ligger i `23_llm_granssnitt.md` och
`24_samtalsloopen.md`. Planens form ligger i `22_planeringslagret.md`. Här
beskrivs vad **operatören** ser av det.

Operatören skriver, i panelen:

> *"Bygg en plockstation som klarar 400 detaljer i timmen, med ett inmatningsband,
> en robot och en utlastningslåda. Skriv PLC-koden."*

| # | Vad som händer | Vad operatören ser | Godkänner han? |
|---|---|---|---|
| 1 | Tjänsten läser förmågerapporten och slår av verktyg vars ytor saknas | fält 7: `förmåga 46 av 46` | nej |
| 2 | Modellen får verktygsschemat och uppgiften. Verktygsurvalet är semantiskt först när katalogen passerar ~100 verktyg | fält 1: modellens plan i klartext | nej |
| 3 | Modellen söker i **katalogindexet** och väljer komponenter. Uppfunnen URI är ett hårt fel (I9) | fält 2: valda komponenter med URI och källa | nej |
| 4 | Varje `effect=write`-verktyg genererar Python-kod som köas. Kön fylls, inget körs | fält 3: N väntande poster, var och en med `desc` och **hela koden** | **ja** — post för post, eller hela planen |
| 5 | Godkända poster körs av pumpen, en per varv | fält 4: `Kör nu: load_component — inmatningsband` | nej |
| 6 | Modellen anger **relationer**, aldrig koordinater. `canConnect` före `connect` (I8) | fält 2: kopplingarna som relationer | nej (kopplingarna är egna köposter) |
| 7 | Bygget kontrolleras geometriskt: minsta avstånd, inte bara träff | fält 2: minsta avstånd i mm per bevakat par | nej |
| 8 | Scenens signaler läses ut och blir signalkarta → OPC UA-noder → **färdiga VAR-block** | fält 2: signalkartan, taggnamn för taggnamn | nej |
| 9 | Modellen skriver **bara sekvenslogiken** i ett skelett med deklarationerna ifyllda (I10) | fält 1: den genererade ST-koden | nej |
| 10 | Grind 1–4: kompilering (`STruC++`), statisk analys, deklarationsmatchning, AST-validering mot verktygsschemat | fält 2: fyra grindar med utfall | nej |
| 11 | Koden laddas in i OpenPLC v4 över REST med JWT. VC ansluter som OPC UA-**klient** | fält 7: PLC-status | **ja** — inladdning är `effect=write` |
| 12 | Simuleringen körs. Ögat provtar och lägger PLC:ns variabler på **samma tidslinje** som scenens fysik | fält 7: takt i Hz, antal prov | nej |
| 13 | Ögat skriver sin dom. Grinden parsar den utan att tolka om något (I1) | fält 5: domstexten **ordagrant** | nej |
| 14 | Guldgrinden fäller sitt beslut | fält 6: `GOLD gold_verified_core` eller `NOT GOLD (skäl)` | nej |

**Hur operatören vet att det blev rätt:** han läser fält 5 och 6. Fält 5 är
ögats egna rader — `GRIP FORMED t=0.950s`, `CARRY RIGID rot=0.0deg`,
`PLACE IN_TARGET`, `TELEPORT_TRANSFER OK`. Fält 6 är grindens beslut med sitt
skäl. Ingen av dem är modellens ord.

Att detta fungerar är prövat på fem celler mot en körande VC: **5 av 5 enligt
facit**, och att den bra cellen fick PASS är sitt eget prov — en domare som
fäller allt klarar varje fällningsprov och är ändå värdelös
(`tests/protocol/fas2_ogat.md`).

---

### 5.1 Vad som kan gå fel i varje steg, och vad operatören ser

Tabellen ovan säger vad som händer när det går bra. Den här säger vad som
händer annars. Varje rad pekar på det ställe där felet hanteras, så att
ingenting hänger i luften.

| Steg | Felet | Vad operatören ser | Var det står |
|---|---|---|---|
| 1 | en förmåga saknas | verktyget **stängs av** och ytan namnges. Aldrig tyst mindre funktion | N-1, `36_versioner.md` |
| 2 | modellen svarar varken text eller anrop | uppdraget stannar; *"Modellen svarade varken text eller anrop."* Inget tomt varv körs | `28_lagen...` §3.8 fall 4 |
| 3 | katalogen har ingen matchande komponent | hårt stopp med en fråga, `NOT GOLD (komponent saknas)`. Ingen halv scen | §6.2, regel F-4 |
| 3 | modellen hittar på en URI | hårt fel (I9). Noll uppfunna URI:er är fas 4:s mätta grind | §9 F-G7 |
| 4 | kön full, 256 poster | `E_QUEUE_FULL`. Systemet slänger aldrig en post själv | `26_appen.md` G-7 |
| 4 | posten dödar pumpen | varningen står **före** godkännandet, och posten kan inte samgodkännas | `26_appen.md` G-1, G-2 |
| 5 | godkänd post körs inte inom 100 ms medan `kor=true` | `kö stillastående`, och `sim` kontrolleras en gång till | `28_lagen...` §3.3 |
| 5 | VC stängs mitt i | *"Visual Components avslutades."* Kön är borta med processen; posten står som `interrupted` vid nästa pumpstart | `28_lagen...` §3.8 fall 1 |
| 6 | `canConnect` är falskt | kopplingen köas inte. `can_connect` var **False i varje prövad uppställning** — sju stycken | **M-14** |
| 7 | två komponenter kolliderar | minsta avstånd per bevakat par, i mm. Inte "kollision: nej" | §5 steg 7 |
| 8 | signalkartan och scenen går isär | grind 3 fäller. Det är ett **systemfel**, inte ett modellfel, eftersom deklarationerna genereras | §6.4 |
| 9–10 | ST-koden kompilerar inte | kompilatorns egna rader, oförändrade, med radnummer | §6.4, I1 |
| 11 | OpenPLC svarar inte | kopplaren räknar raka fel och ger upp vid tredje. Efter det **försöker ingenting igen**, och det står med de orden | **MÄTT M-39**; `28_lagen...` §3.8 fall 3 |
| 12 | provtagningstakten faller under 15 Hz | körningen blir `INCONCLUSIVE`, aldrig `PASS` | `26_appen.md` A-8 |
| 12 | ett provtagningsfel kastas | `PROVTAGNINGSFEL` med traceback, `aktiv=False`, körningen `INCONCLUSIVE` | `28_lagen...` §3.5 |
| 13 | ögats rapport är avhuggen | ingen `EYES VERDICT`-rad ⇒ `NOT GOLD (truncated eyes output)`. Aldrig ett godkännande | §6.3 |
| 13 | ögats rapport saknar `SECTION HONESTY` | domen visas **inte** som en dom: en rapport utan sektionen har ingen ärlighetsgrind alls | N-2; fas 17 regel Y6 |
| 14 | guld utan ögondom | förbjudet. Fält 6 renderas aldrig utan fält 5 | `26_appen.md` A-6 |
| 1–14 | modellen tar slut mitt i en reparation | varvet blev aldrig klart, och **de grindar som skulle ha kört efter det kördes aldrig**. Utfallet är kandidat i bästa fall | `28_lagen...` §3.8 fall 4 |

**Regel F-11.** Ett steg som inte kördes får aldrig se ut som ett steg som höll.
Det är samma regel fas 17 mekaniserade som `Y11` — *en avslutad körning räknar
stegen som aldrig kördes* — och den gäller lika hårt när skälet till att steget
uteblev var att något dog.

---

## 6. Genomloppet när det inte går bra

### 6.1 Modellen missförstår

| Mekanism | Vad operatören ser | Ärvd ur |
|---|---|---|
| **Verify-contract** | tjänsten plockar namn och tal ur modellens egen text och kontrollerar dem mot scenen. Stämmer de inte visas skillnaden | `20_arv.md` |
| **Honesty-rewrite** | påstår svaret framgång medan sista verktyget föll, tvingas omskrivning | `20_arv.md` |
| **Tak på varv** | 10 rundor, stopp efter 6 raka misslyckanden | `20_arv.md` |

**Regel F-3.** Operatören får aldrig se ett påstående om scenen som inte
kontrollerats mot scenen. En modell som säger "griparen är monterad" utan att
scenen håller med visas som en **avvikelse**, inte som ett svar.

### 6.2 En komponent saknas i katalogen

Detta är **mätt** och det är allvarligt: testprefixet innehåller **noll
`.vcmx`-layouter och fem komponentfiler**. Det finns alltså inget lokalt
komponentbibliotek (`bank/katalog_index.json`, härkomstfältet;
`tests/protocol/fas5_verktygen.md`).

| Vad som händer | Vad operatören ser |
|---|---|
| `search_catalog` ger noll träffar | *"Katalogen innehåller ingen komponent som matchar 'transportör'. Indexet har N poster."* |
| Modellen får **inte** hitta på en URI (I9) | uppdraget stannar med `NOT GOLD (komponent saknas)`. Ingen halv scen byggs |
| Operatören kan peka ut en komponent själv | han anger URI eller drar in komponenten i VC manuellt, och systemet fortsätter mot den scen som faktiskt finns |

**Regel F-4.** Ett saknat bibliotek är ett **hårt stopp med en fråga**, aldrig
en gissning och aldrig en tyst nedgradering till något enklare.

Läget per verktyg, efter **M-14**:

| Verktyg | Läge | Härkomst |
|---|---|---|
| `list_interfaces`, `interface_info`, `disconnect` | prövade mot VC | **M-14** — gränssnitt går att skapa med `createBehaviour(VC_ONETOONEINTERFACE, ...)` |
| `can_connect` | **False i varje prövad uppställning** — sju stycken | **M-14** |
| `connect` | **oprövat.** Får inte redovisas som grönt | **M-14** |
| `load_component` | **oprövat** — noll `.vcmx` på disk | fas 5 |

M-14 bär också en metodlärdom som gäller hela panelen: en enstaka positiv
observation i en scen som bär kvarvarande tillstånd är ingen mätning. Panelen
får aldrig visa `kopplad` på ett `IsConnected` som inte reproducerats från ett
känt utgångsläge.

Panelen ska säga `oprövad` om de två sista tills en katalog finns.

### 6.3 Ögat fäller

| Vad ögat säger | Vad operatören ser i fält 5 | Vad modellen får tillbaka |
|---|---|---|
| Griparen stängde för tidigt | `GRIP NEVER_FORMED` | *"griparen stängde 0,4 s före detaljen var på plats"* |
| Detaljen gled | `CARRY SLIPPING rot=15.0deg` | vinkeln och när den började |
| Fel placering | `PLACE OFF_TARGET err=80.0mm` | felet i mm |
| Fysiskt omöjlig framgång | `TELEPORT_TRANSFER VIOLATION dist=800.0mm` | **överordnat**: klass `F12`, alltid, även om annat också var fel |
| Avhuggen rapport | ingen `EYES VERDICT`-rad | `NOT GOLD (truncated eyes output)` — aldrig ett godkännande |

**Regel F-5.** Åtgärdstexten till modellen namnger **storheten och talet**,
aldrig "sekvensen fel". Det är hela poängen med att ha en domare.

### 6.4 PLC-koden kompilerar inte

| Grind | Klass | Vad operatören ser |
|---|---|---|
| 1, `STruC++` | `F1` syntax | kompilatorns egna rader, oförändrade, med radnummer |
| 2, statisk analys | `F2` okänt namn | regeln som fällde, och **den incident regeln kom ur** |
| 3, deklarationsmatchning | `F3` fel tagg | taggen, och att den inte finns i signalkartan |
| 4, AST mot schemat | `F2` | argumentet eller enum-värdet som inte finns |

Grind 3 kan i praktiken inte fälla på ett stavfel: deklarationerna
**genereras** ur scenens signalkarta och modellen skriver dem aldrig (I10).
Fäller den ändå betyder det att signalkartan och koden gått isär, och det är
ett systemfel, inte ett modellfel.

### 6.5 Bryggan går ned mitt i

Två operationer stoppar simuleringen och dödar pumpen, och de är **mätta**:
`createBehaviour(VC_SCRIPT, ...)` och `app.save(uri)` (M-13). Vad som händer
och hur operatören tar sig tillbaka står i `28_lagen_och_aterhamtning.md`.

---

## 7. Manuell övertagning, och återlämning

Operatören äger VC. Systemet är en gäst där.

| Situation | Vad som gäller | Stämpel |
|---|---|---|
| Operatören arbetar i VC medan pumpen går | tillåtet. `tick()` har en budget på 25 ms och `select` med noll timeout, och rör aldrig en tråd | mekaniskt visat; **OPRÖVAD som upplevelse** — allt är mätt headless (fas 1, M-22) |
| Operatören stoppar simuleringen med play-knappen | **pumpen dör.** Den bor i simuleringen (M-08) | **MÄTT** |
| Operatören vill pausa systemet utan att döda det | han pausar i panelen: inga nya poster godkänns, kön står kvar, pumpen fortsätter ticka | tjänstens sida, fritt val |
| Operatören sparar layouten själv | pumpen dör, samma som `app.save()` genom bryggan | **MÄTT M-13** |
| Operatören vill ha tillbaka bryggan | menyval 2, `VC Assist — starta om bryggan`, eller `sim`-operationen `restart` från panelen | **MÄTT** — `sim.reset()` + `startSimulation()` från kommandots scope är den enda väg som fungerar |

**Regel F-6.** Systemet tar aldrig tillbaka kontrollen av sig självt utöver den
mätta självstarten: högst **20 omstarter per minut**, minst **1,0 s** mellan
dem, och därefter slår bryggan av sin egen självstart
(`pump.OMSTART_TAK_PER_MINUT`, `OMSTART_MINSTA_MELLANRUM_S`, båda PRELIMINÄRA
och satta av M-13). Sedan är det operatörens beslut.

**Regel F-7.** När operatören tagit över manuellt visar panelen `manuellt läge`
och kön står stilla. Systemet återupptar först när han säger till.

---

## 8. Vad som sparas mellan sessioner

| Sak | Var | Överlever VC-omstart | Stämpel |
|---|---|---|---|
| Godkännandekön | `Brygga.ko`, i minnet | **nej** | KOD@HEAD |
| Poster som stod i `running` när pumpen dog | markeras `interrupted` vid nästa pumpstart | ja, som markering | KOD@HEAD `_markera_avbrutna` |
| Uppskjutna ändringar (skriptbeteenden) | `~/vc_assist_uppskjutet.json` | **ja**, tillämpas vid nästa start **före** simuleringen | KOD@HEAD `_tillampa_uppskjutet` |
| Delad hemlighet | `~/vc_assist_token` | skrivs om vid **varje** bryggstart | KOD@HEAD — tjänsten måste läsa om filen efter varje VC-start |
| Förmågerapport | `~/vc_assist_formaga.json` | skrivs om vid varje start | KOD@HEAD |
| Bootlogg och brygglogg | `~/vc_assist_boot.log`, `~/vc_assist_brygga.log` | ja, de växer | KOD@HEAD |
| Ögats serie | `eyes.json` på disk, och i svaret när den ryms under halva `MAX_KROPP` | ja | KOD@HEAD `_op_eyes_stop` |
| Scenen | endast om `save_layout` körts — **och den dödar pumpen** | ja | **MÄTT M-13** |
| Uppdraget, planen, journalen | tjänstens sida, på disk | ja | **ska byggas**, se §10 |

**Regel F-8.** Panelen skriver i klartext vad som **inte** överlever: *"Kön
töms när VC startas om. N poster väntar just nu."* En operatör ska aldrig
upptäcka det efteråt.

**Regel F-9.** Planen och journalen ligger på **tjänstens** sida, på disk, per
uppdrag. Bäraren är **arbetsordern** (`24_samtalsloopen.md` §6), och journalen
är beslutsloggen som hänger på den. Det är enda skälet till att en halvfärdig plan kan tas upp igen efter
en VC-omstart (`28_lagen_och_aterhamtning.md` §4).

---

## 9. Flödets grindar

| # | Godkänt när |
|---|---|
| **F-G5** | Grön start: tre filer inom 60 s, och panelen namnger den som saknas |
| **F-G6** | Ett fullständigt genomlopp går från fritext till fält 6 utan handpåläggning, på en scen som finns |
| **F-G7** | Katalogmiss ger hårt stopp med fråga. Över N genereringar: **noll** uppfunna URI:er och **noll** uppfunna API-namn |
| **F-G8** | Varje åtgärdstext till modellen bär en storhet och ett tal ur ögat, inte en sammanfattning. Stickprov: 10 av 10 |
| **F-G9** | Manuell övertagning: operatören stoppar simuleringen, panelen visar `nere` med rätt orsak inom 3 s, menyval 2 ger en levande brygga igen |
| **F-G10** | Efter en VC-omstart mitt i en plan kan planen tas upp och slutföras, och journalen visar vilka poster som var `interrupted` |
| **F-G11** | Tjänsten läser om `vc_assist_token` efter varje VC-start och får aldrig `E_AUTH` av ett gammalt token |

Plattform: **Linux ☐ Windows ☐** per grind. Ingen är körd på Windows (I17).

---

## 10. Öppna frågor

Inget av detta är bestämt.

1. **Var uppdragets journal ligger.** Förslagsvis `~/.vc_assist/uppdrag/<id>/`
   med plan, kod, ögats rapporter och besluten. Ingen mapp är vald.
2. **Om ett uppdrag ska kunna pausas över en natt** och tas upp mot en annan
   VC-session, eller om en session är en session.
3. **Hur operatören pekar ut en komponent manuellt** när katalogen inte har
   den: URI i panelen, eller markering i VC och `getSelection`?
4. **Om panelen ska kunna visa VC:s Output-panel** (`app.getMessages`). Det
   vore billigt och nyttigt, men är oprövat (M-21).
5. **Ett riktigt komponentbibliotek.** Utan det är fas 5:s egentliga grind —
   *N mållayouter byggda, noll kollisioner, alla gränssnitt kopplade* — inte
   stängd, och §5 steg 3–7 är prövade endast på tomma komponenter.


---

## F-G12 — vad användaren ser medan det arbetar

De elva `F-G`-grindarna handlar om installation, start och genomlopp. Ingen av
dem säger något om vad användaren ser **under** en körning.

> **F-G12.** Under en pågående körning går förloppsytan att läsa, och den
> fäller sin egen grind. Trasiga fall som måste falla: en visning som påstår
> att en fallen körning arbetar, en som skriver om en grinds ord, och en som
> visar en dom vars ärlighetsgrind aldrig kört.

## Glappet som gav upphov till grinden

**MÄTT 2026-09-05 (M-64), före koden fanns:**

| | antal |
|---|---:|
| rapportytor i systemet | **7** |
| ger text en människa läser | 4 |
| går att läsa under körning | 2 |
| **båda samtidigt** | **0** |

Noll av sju. Förklaringen är enkel och strukturell: i `svc/` fanns **noll**
återanrop, observatörer eller lyssnare. Varje rapportyta var per konstruktion
terminal — den svarade när allt var klart.

Och det här dokumentets elva grindar var **specade och obyggda**, inte
halvbyggda: noll av `F-G1`–`F-G11` nämndes i något prov.

## Grinden dömer paret, inte renderaren

`forlopp/`-grinden dömer **protokollet och texten tillsammans**. Följden är att
den också fäller en webbsida som inte är skriven än.

Det är skälet till att ingen webbsida byggdes. En sådan låser det val
`26_appen.md` §7 fråga 1 lämnar öppet — webbläsare eller terminal — och grinden
binder ytan ändå. Ytan är text just för att svaret ska kunna bli vilket som
helst.

## Hålet som står öppet med flit

Ytan **går att driva**, men ingenting driver den. Noll moduler i `svc/` utanför
`forlopp/` konstruerar ett `Forlopp`. Det står rött i
`tests/motbevis/test_forloppet_har_ingen_forare_motbevis.py`.

Kopplaren och reparationsslingan ska **inte** laga det själva: att låta ett
lägre lager känna presentationslagret vore fel beroenderiktning. Vägen in går
genom `forlopp.kallor`, och den är byggd och provad.

---

## F-G13 — vad användaren ser när något dött

`F-G12` stänger ytan som visar vad som händer **medan** en körning går. Ingen
grind säger något om vad användaren ser **efteråt**, och det är den dyrare
halvan: en körning som lever kan berätta vad den gör, men ett delsystem som dog
kan inte berätta någonting alls.

> **F-G13.** När ett delsystem slutat svara säger ytan vad som dog, varför, om
> något försöker igen och vad operatören själv kan göra — och den fäller sin
> egen grind. Trasiga fall som måste falla: en härledning som räknar en gammal
> avläsning som ett svar, en som räknar en lyckad `connect()` som ett livstecken,
> en visning som lovar ett nytt försök när ingenting försöker, och ett läge som
> inte gick att avgöra som visas som grönt eller utelämnas.

### Glappet som gav upphov till grinden

**MÄTT 2026-09-05 (M-103), före koden fanns:**

| | antal |
|---|---:|
| lägen `28_lagen_och_aterhamtning.md` specar | **7** |
| som någon kod i `svc/` kunde härleda | **0** |
| ställen i `svc/` som skilde `nere` från `frånkopplad` | **0** |
| moduler som räknade en avläsnings ÅLDER mot läsarens klocka | **0** |

Sju lägen, noll härledningar. `svc/vc_assist_svc/klient.py` kastar `BryggFel`
och `OSError` uppåt, och den som fångar dem har inget ordförråd att svara med.
Ordet `degraded` fanns i pumpens `ping`-svar och lästes inte av någon.

### Vad grinden inte binder

Ytan är **text**, och valet mellan webbläsare och terminal (`26_appen.md` §7
fråga 1) står kvar öppet med flit. Grinden dömer paret avläsningar och text, och
fäller därför också en webbsida som inte är skriven än — utan en rad ny kod den
dagen den byggs.

### Hålen som står öppna

* **Ingen sond går av sig själv.** Ytan läser avläsningar; vem som gör dem, och
  hur ofta, är inte bestämt (`28_lagen...` §9 fråga 5).
* **Ingen väg tillbaka har körts mot en VC som verkligen gick ned.** Alla fyra
  dödsfallen är framprovocerade mot attrapper. Det står som en permanent
  ovisshet i varje visning, inte som en fotnot här.
* **Windows är oprövat**, hela vägen. `wineserver -k` finns inte där, och
  `netstat`-vägen är skriven men aldrig körd (M-44).
