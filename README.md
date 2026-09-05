# VC Assist

En LLM-assistent som bygger en produktionslina i **Visual Components**,
genererar styrkoden till en mjuk-PLC, kör den mot scenen, och låter **scenen**
avgöra om sekvensen och timingen fungerar.

Fältets styrkodsgeneratorer mäts mot blinda grindar: kompilatorn ser bara
syntax, och formell verifiering kan inte avgöra timersemantik. Tid och sekvens
är just där PLC-logiken bor, och där finns ingen domare. Simuleringen är den
domaren — den kör koden i tid mot en mekanik som beter sig.

Det som ska vara hundra procent är **det som släpps igenom**, inte det som
genereras. Ingenting levereras förrän ögat sagt att det fungerar i tid.

Systemdokumentet är [`SYSTEM.md`](SYSTEM.md). Hela specifikationen ligger under
[`docs/spec/`](docs/spec/), och varje mätning som något påstående vilar på
ligger under [`docs/matningar/`](docs/matningar/).

---

## Formen

```
tjänst (Python 3, utanför VC)  ──kodsträngar över TCP──►  brygga (inne i VC)
                               ◄──JSON-rad tillbaka──────
```

Kravet som tvingar formen: **VC har inget externt API**, och dess skript kör i
inbäddad Python 2.7 (4.x) eller 3.x (5.0). Agenten måste bo utanför. Allt
ovanför sömmen är generiskt, allt under är VC-specifikt.

| Mapp | Vad |
|---|---|
| `ext/vc_addon/vc_assist/` | tillägget som installeras **i** VC: bryggan, pumpen, ögats provtagning |
| `svc/vc_assist_svc/` | tjänsten som körs **utanför** VC: klient, verktyg, ST-lager, guldgrind, API-index |
| `install/` | installationen: hitta VC, lägg tillägget där, verifiera, ta bort |
| `bank/` | mätbänken: uppgifter och facit |
| `tests/enhet/` | prov som inte kräver VC |
| `tests/protocol/` | fasacceptans: vad som prövats, med mätta tal |
| `docs/` | spec, mätningar, drift, API-referens |

---

## Vad det kräver

| | Krav | Anmärkning |
|---|---|---|
| **Värdmaskin** | Python 3 | Endast standardbiblioteket för installationen. Körd på **3.13.11**, **3.12.3** och **3.10.12** |
| **För att köra proven** | `pytest` | Det enda som behöver installeras, och bara för `tests/`. Installationen och tillägget klarar sig utan |
| **Visual Components** | 4.10 Premium | Det är versionen allt är mätt på. Se tabellen längst ned om andra versioner |
| **Linux** | Wine ≥ 11.15, DXVK som d3d9 | Se [`docs/drift/linux_wine.md`](docs/drift/linux_wine.md). Under 11.15 dör licensmotorn på `bcrypt HashBlockLength` — mätt |
| **Windows** | inget utöver VC självt | **Oprövad väg.** Se nedan |
| **PLC-delen** (fas 6 och framåt) | OpenPLC v4 | Adressen är konfiguration, aldrig antagande. Kan ligga var som helst |

Ingen `pip install`. Ingen `requirements.txt`. Installationen och tillägget
använder bara standardbiblioteket, på båda plattformarna.

---

## Installera

```bash
git clone <repo> VC_Assist
cd VC_Assist

python3 install/installera.py sok          # visa vad som finns, skriv ingenting
python3 install/installera.py installera   # lägg tillägget i den nyaste VC:n
```

`sok` skriver ingenting till disk. Den listar varje dokumentmapp den hittade
och hur den hittade den, varje VC-version, vilka `Python N`-nivåer som finns,
och vilka VC-installationer som ligger på disken. Så här ser det ut på
maskinen där projektet byggs:

```
VC-mappar (4), nyaste forst:
  Visual Components 4.10
      /home/anton/Documents/Visual Components/4.10/My Commands
      Python-nivaer pa disk: Python 2
      Python 2/vc_assist: inte installerat
```

`installera` tar den **nyaste** versionen och rapporterar de övriga. Vill du
välja själv:

```bash
python3 install/installera.py installera --vc-version 4.9
python3 install/installera.py installera --alla
python3 install/installera.py installera --mal '<sökväg till .../My Commands/Python 2/vc_assist>'
```

Starta sedan VC. **Läs `vc_assist_boot.log`** i VC:s egen användarmapp (under
Wine: `<prefix>/drive_c/users/<du>/`). Står det ingenting där har tillägget
inte laddats — och VC säger ingenting själv om ett tillägg som inte gick att
ladda. Det är mätt tre gånger, se `docs/matningar/M-09_tyst_syntaxfel.md`.

### Vad installationen gör, och varför just så

**Den söker, den antar aldrig.** VC:s egen konfiguration lägger tilläggsmappen
på `%MYDOCUMENTS%\%COMPANY%\%VERSION_2%\My Commands` — företaget och versionen
är variabler i VC:s källa. Därför söks mönstret
`<dokumentrot>/<företag>/<version>/My Commands/<Python N>/`, och företagsnamnet
skrivs aldrig i kod.

**Nivån `Python N` är inte kosmetisk.** `My Commands/Python 2/vc_assist/`
fungerar på 4.10. `My Commands/vc_assist/` gör det **inte** — uppstartskroken
fyrar aldrig. Båda mätta i `M-01`. Nivån letas upp på disk; den härleds ur
versionsnumret bara när ingen finns, och märks då `harledd`.

**Både Windows och Wine.** På Windows söks `Shell Folders\Personal` i
registret (så en OneDrive-omdirigerad dokumentmapp hittas), `%USERPROFILE%`
och `%OneDrive%`. På Linux söks wine-prefix: `$WINEPREFIX`, `~/.wine`, och
varje `~/.wine*` som har en `drive_c`. Två prefix som delar `Documents` via
symlänk slås ihop till **en** mapp med båda prefixen som källa — annars tror
man att man installerar på två ställen och skriver på ett (`M-02`).

**Den verifierar efteråt.** Ett trasigt tillägg misslyckas inte bara tyst i
VC — det misslyckas medan anropen rapporterar att det gick bra (`M-09`).
Därför granskas filerna **på disk**: sha256 mot källan, varje fil parsas och
kompileras, `__init__.py` måste definiera `OnAppInitialized`, och skriptmallen
inne i `bridge_cmd.py` kompileras **efter formatering** — det ledet var det som
brast. Håller något inte tas det nyss skrivna bort igen, för ett halvt tillägg
i VC är värre än inget.

**Den är idempotent.** En oförändrad fil skrivs inte om, inte ens mtime.

### Avinstallera

```bash
python3 install/installera.py verifiera      # är den hel, och samma som repot?
python3 install/installera.py avinstallera
```

Installationen skriver ett manifest, `vc_assist_installation.json`, med sha256
per fil. Avinstallationen tar bort **exakt** det manifestet listar, plus den
bytekod VC:s Python lagt bredvid (`.pyc`, `__pycache__/`). Främmande filer i
mappen lämnas i fred och rapporteras, och då står mappen kvar för deras skull.
Finns inget manifest vägrar den — då vet den inte vilka filer som är dess egna,
och den gissar inte.

Mätt: mappträdet före installation och efter avinstallation är byte-identiskt,
sha256 per fil, noll skillnader.

---

## Köra

Efter installation, och med VC igång:

```bash
python3 tests/protocol/kor_fas1.py     # bryggans acceptans mot körande VC
python3 tests/protocol/kor_fas2.py     # ögats acceptans: fem celler mot facit
python3 tests/protocol/kor_fas5.py     # varje verktyg mot körande VC
```

Tjänstesidan talar med bryggan över TCP på `127.0.0.1:8901` med en token som
bryggan skriver vid start (`vc_assist_token` i VC:s användarmapp).
Protokollet står i [`docs/spec/31_brygga_protokoll.md`](docs/spec/31_brygga_protokoll.md).

### Prov

```bash
python3 -m pytest tests/enhet -q                    # allt som inte kräver VC
python3 -m pytest tests/enhet/test_install.py -q    # bara installationen
```

`tests/enhet/` kräver varken VC eller Wine. Det är ett arkitekturkrav, inte en
bekvämlighet: ögats härledning är en ren funktion över en serie, så den går att
pröva på syntetiska serier.

---

## Ärligt: vad som är prövat och vad som inte är det

Regeln i det här projektet är att varje påstående antingen är **mätt**, med
kommando eller filreferens, eller märkt **antaget**. Ett grönt påstående utan
mätning är precis det projektet är byggt för att undvika.

### Plattformar

| | Läge | Vad det betyder |
|---|---|---|
| **Linux + Wine 11.16** | **prövat** | VC Premium 4.10 startar, licens nås, bryggan lever, ögat mäter. Allt headless |
| **Windows** | **OPRÖVAT** | Ingen VC-installation på Windows finns här — kontrollerat. Koden är plattformsneutral och Windows-vägen är prövad **logiskt**, med en injicerad Windows-miljö mot ett attrappträd. Det är en prövning av logiken, inte av Windows. Ingen rad i det här repot är en mätning på Windows |
| **VC 4.10** | **prövat** | Tilläggets sökväg, uppstartskroken, API-ytan, pumpen — allt mätt på 4.10 |
| **VC 5.0** | **OPRÖVAT** | Skolans licensserver har 4.10, så 5.0 går inte att köra här. Att 5.0:s tilläggsmapp heter `Python 3` är sannolikt, inte mätt. Installationen kan lägga tillägget där och märker då sökvägen `OPROVAD` |
| **VC:s gränssnitt under last** | **OPRÖVAT** | Allt är kört headless. Att pumpen aldrig blockerar är visat mekaniskt, men "ingen märkbar frysning" är en syn, inte en slutsats |
| **Python 3.7–3.9** | **OPRÖVAT** | Koden använder inget nyare än `dataclasses` (3.7). Körd på 3.10.12 och 3.13.11 |

### Faser (`docs/spec/70_faser.md`)

Varje fas stängs av en mätt grind, inte av en demo. Protokollet med talen
ligger i `tests/protocol/`.

| # | Fas | Läge | Mätt |
|---|---|---|---|
| 0 | Eget testprefix | klar på Linux | `fas0_testprefix.md`. Ej tillämplig på Windows — prefix är ett Wine-begrepp |
| 1 | Bryggan | klar på Linux | `ping` tur och retur: median **9,91 ms**, värsta av 20 **13,45 ms**. Provtagning **17,2 Hz** tyst, **224,7 Hz** under trafik. 13 av 13 steg, 6 av 6 trasiga fall föll rätt |
| 2 | Ögat | klar på Linux | Fem celler byggda i VC:s riktiga scengraf: **5 av 5 enligt facit**. Den bra fick PASS, de fyra trasiga föll |
| 3 | Grinden | klar på Linux | Kört på ögats verkliga utdata ur VC: bara de gröna gav GOLD, alla fem gav NOT GOLD. Sju vägar in ger NOT GOLD, tystnad inräknad. L2 mot en riktig lina saknas — ingen lina byggd än |
| 4 | API-index | klar, kräver ej VC | **3444 symboler** ur `api.xml`. Oberoende prov: 7 riktiga kodstycken, **0 falskt positiva**; 10 uppfunna namn, **0 falskt negativa** |
| 5 | Verktygen mot VC | klar på Linux | Förmågerapport **46 av 46 ytor**. **20 anrop lyckades, 0 föll**, alla 21 verktyg prövade |
| 6 | PLC-bandet | klar på Linux | M-39: handskriven ST styr scenen genom OPC UA, slingan sluten. VC 4.10, Wine 11.16, OpenPLC v4, headless |
| 7 | ST för en station | klar på Linux | M-49, M-50: grind 1–5 gröna, ögat PASS, **L1-guld**. Fem trasiga fall fällda av ögat |
| 8 | Komposition | klar på Linux | M-73, M-74: två stationer på en lina, **guld i fem celler**. Fem kompositionsfel fällda i linan som båda enstationskörningarna släppte igenom |
| 9 | Bänken | **stängd** | M-96: slingan kör sig själv — bryggan mellan grind och modell var det enda som stod öppet. Enskott utan grindreglerna **0 av 20** (fem försök per uppgift); flerskott med grindens egna ord tillbaka **3 av 4** inom taket på fyra varv, varv 3/1/2, 1,32 USD. `M-52`:s tak prövat mot en riktig modell för första gången. Skalan är fas 21 |
| 10 | Paketering | **stängd** | M-90 (ren Linux-maskin) + M-112: VC startar med det installationen lade dit. Elva filer installerade och verifierade, bootloggen visar tillägget laddat, `ping` tur och retur **19,7 ms** genom installationens brygga |
| 11 | Klassisk baslinje | klar, kräver ej VC | M-62: en regelbaserad generator över **samma** bank och **samma** domare. Fas 9:s tal rapporteras alltid som par |
| 12 | Verktygskedjan i repot | klar på Linux | M-56: STruC++ v0.6.6, OpenPLC v4 och node v22.22.0 hämtas med fastspikad version och kontrollerad hash. Windows-vägen oprövad |
| 13 | Windows | **inte påbörjad** | Kräver en Windows-maskin. M-44:s 16 numrerade protokollpunkter väntar |
| 14 | Harnessens hårdhet | klar, kräver ej VC | M-53: från 17 av 46 mekaniserade regler till **37 av 46**, med ett golv som bara får gå uppåt |
| 15 | Ögat på djupet | mätt mot VC (M-86/87/88/97) | Hela scenen i serien, PLC på samma axel med mätt hopfogning, 4 av 5 domare fäller VC-byggda celler; genomflöde fail-closed men fälls bara syntetiskt |
| 16 | Planeringslagret | klar, kräver ej VC | M-63: en fritextbeställning blir en körbar byggplan, och en omöjlig beställning **avvisas** med vilket villkor som krockar |
| 17 | Vad användaren ser medan det arbetar | klar, kräver ej VC | M-64, M-93: förloppet går att läsa **medan** en körning pågår, och ur en annan process. 17 regler med var sin trasig fixtur. En läsare som fryser klockan sa ARBETAR i 60 av 60 avläsningar av en död körning, och fälls nu |
| 18 | Befintlig anläggning in | mätt (M-89) | 28 av 28 förreglingar återfinns ur ett provspår, 3 av 28 ur ett produktionsspår. Ingen riktig anläggning är inspelad |
| 19 | Personatäckningen | klar, kräver ej VC | M-100: sju arbetsprofiler, **228 arbetssteg**, 144 täckta av de 122 verktygen, 8 utanför räckvidd, 76 obyggda. Per profil 27 % till 89 %. Nämnaren är låst av ett golv: ett steg som tystnat bort ger rött trots högre procentsats |
| 20 | Komponentmodellen | klar på Linux | M-101: TRANSPORTÖR, MATARE, SÄNKA och BUFFERT byggda **ur specen** i riktig VC. **7 av 7** kopplingar där specen säger ja, **13 produkter** genom hela kedjan (mellanrum exakt 3,0000 s, rörelse 400,0000 mm/s), **4 av 4** trasiga fixturer fällda med det saknade beteendet namngivet. 199 prov utan VC |
| 22 | Modellagret | klar i L1 (M-102) | 207 riktiga verktygssvar och 95 riktiga turer: **0** anmärkningar på kapade svar, **0** bokföringsfel, urvalsträff **87 av 105** där varje missat anrop är skrivande, **22 av 22** nåbara övergångar besökta. 13 trasiga fall fällda i körningen, 4 till i enhetsproven |
| 23 | Användarlagret — vad användaren ser när något dött | klar, kräver ej VC | M-103: en härledning som fryser klockan sa LEVANDE i **60 av 60** avläsningar av en sond som dog — med läsarens klocka **3 av 60**. `connect()` mot en socket ingen accepterar lyckades **20 av 20**, `ping` svarade **0 av 20**. Av 18 orsaker har **3** ett automatiskt försök och **2** ett som kan lyckas: i **15 av 18** försöker ingenting igen, och ytan säger det. 14 regler, 88 prov |

### Fas 10 i detalj — det du just läser instruktionen till

Prövat, mätt 2026-09-04:

* sökningen: **0,05 s** över 5 wine-prefix, 2 dokumentmappar, 4 VC-mappar
* installation: **0,159 s**, 9 filer, 104 711 byte
* ominstallation av oförändrad källa: **0 filer skrivna**
* avinstallation: **0,060 s**, 10 filer borttagna, trädet **byte-identiskt** med före
* **67 enhetsprov** på installationen, **3,5 s**, varken VC eller Wine krävs
* hela sviten kördes efter tillägget: **inga nya fel**. Vid mätningen 838 prov före och 904 efter
* `install/` och `ext/` kopierade ensamma till en tom mapp: installationen
  fungerade därifrån — inget beroende på resten av repot

**Inte prövat, och det är fasens öppna punkt:** att **VC startar** med det som
installationen lade dit. Fas 1:s och 2:s körningar mot VC gjordes mot en
handinstallerad kopia, inte mot installationens. Att filerna är på plats, har
rätt sha256 och kompilerar är vad som är visat. Steget som saknas är en
VC-start ur ett testprefix efter en körning av `installera`.

### Räckvidd, i sak

Simuleringen saknar sensorstuds, ställdonsdynamik, fältbussjitter och verklig
hårdvara. Ögat är felfinnande, aldrig bevis. Och ingenting genererat rör en
säkerhetsfunktion: nödstopp och skyddskretsar ligger på certifierad
säkerhets-PLC, i begränsat variabelt språk, skrivet av människa.

---

## Kartan

| Dokument | Frågan det svarar på |
|---|---|
| [`SYSTEM.md`](SYSTEM.md) | Vad är det här, och varför kan det fungera? |
| [`docs/spec/10_matta_fakta.md`](docs/spec/10_matta_fakta.md) | Vad är mätt om VC, Wine och OpenPLC? |
| [`docs/spec/35_plattformar.md`](docs/spec/35_plattformar.md) | Vad krävs för att gå både på Windows och Wine? |
| [`docs/spec/36_versioner.md`](docs/spec/36_versioner.md) | Hur bär koden 4.10 och 5.0 samtidigt? |
| [`docs/spec/70_faser.md`](docs/spec/70_faser.md) | I vilken ordning byggs det, och vad stänger varje fas? |
| [`docs/spec/95_testprotokoll.md`](docs/spec/95_testprotokoll.md) | Hur prövas allt? |
| [`docs/spec/96_ingen_skuld.md`](docs/spec/96_ingen_skuld.md) | Vad får aldrig lämnas efter sig? |
| [`docs/drift/linux_wine.md`](docs/drift/linux_wine.md) | Vad krävs av Wine, och varför? |
| [`docs/matningar/`](docs/matningar/) | Varje enskild mätning, med datum och utfall |
| [`tests/protocol/`](tests/protocol/) | Fasacceptans: steg, mätning, godkänt när, trasigt fall |

Fullständig innehållsförteckning över specen: [`docs/spec/00_index.md`](docs/spec/00_index.md).
