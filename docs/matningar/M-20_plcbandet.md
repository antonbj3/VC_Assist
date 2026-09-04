# M-20 — PLC-bandet: vad som faktiskt går att köra, och hur snabbt

**Datum:** 2026-09-04 · Ubuntu, kärna 6.8, 13600K · Docker version 29.1.3 · nätverk uppe
**beskriver:** `svc/vc_assist_svc/plc/`, `tests/enhet/test_plc.py`,
`tests/protocol/fas6_plcbandet.md`
**Kört av:** `python3 -m vc_assist_svc.plc.matning` samt de curl-anrop som citeras nedan.

Kort svar: **kedjan går hela vägen.** Genererad ST kompileras av STruC++,
laddas in i en OpenPLC v4-runtime över REST/JWT, och en OPC UA-klient kan
skriva en insignal och läsa svaret på utgången. Tur och retur, median över
3 × 120 mätningar med 20 ms scanperiod: **40,0 ms**. Visual Components ingår
**inte** i mätningen — se "Vad som inte är mätt".

---

## 1. Vad som redan fanns på maskinen

```
$ docker ps -a
de5a5f84a09c  wzy318/openplc  "./start_openplc.sh"  7 months ago
              Exited (137) 3 months ago  0.0.0.0:502->502/tcp, 0.0.0.0:8080->8080/tcp
$ docker images | grep -i openplc
fdamador/openplc:latest   852MB
wzy318/openplc:latest    1.03GB
```

Uppgiften sa "operatören har OpenPLC i Docker med Modbus TCP på 502 och
webbgränssnitt på 8080". Portmappningen stämmer. **Men versionen gör det inte.**

```
$ docker history wzy318/openplc:latest | tail -3
<missing>  3 years ago  RUN /bin/sh -c ./install.sh docker  850MB
$ docker run --rm --network none --entrypoint /bin/sh wzy318/openplc -c \
    'grep -ril "opcua\|opc_ua\|open62541\|freeopcua" /workdir ...'
   (ingen träff)
$ ... head -20 /workdir/webserver/webserver.py
   import flask, flask_login, serial.tools.list_ports, ...
```

Bilden är tre år gammal och innehåller `webserver.py`, `iec2c`, `dnp3.cfg`:
det är **OpenPLC v3**. Noll förekomster av OPC UA i hela filsystemet.
Behållaren har varit stoppad i tre månader och **rördes aldrig** under den här
mätningen.

**Slutsats:** `docs/spec/60_plc.md` bygger på OpenPLC v4. Det som fanns
installerat var v3, och v3 är ingen OPC UA-server. Antagandet var alltså inte
uppfyllt på den här maskinen.

## 2. Var v4 finns, och vad den kostade i disk

Det finns inget `autonomylogic`-namespace på Docker Hub (`HTTP 404`), och
`thiagoralves/openplc_v3` finns inte heller som hubb-repo. Källan är
`Autonomy-Logic/openplc-runtime` på GitHub, och en **färdigbyggd** avbildning
ligger på GHCR. Storleken mättes **före** nedladdning, eftersom disken låg på
9,9 G ledigt av 647 G:

```
$ docker manifest inspect ghcr.io/autonomy-logic/openplc-runtime@sha256:12a6...
   lager: 7   komprimerad summa: 0,36 GB
$ docker pull ghcr.io/autonomy-logic/openplc-runtime:latest
$ docker image inspect ... --format '{{.Size}}'
967472727            (923 MiB uppackat)
```

Ledigt före: **9,9 G**. Efter: **8,8 G**. Att bygga imagen ur källkod
(`Dockerfile` → `install.sh`, apt + cmake + fem plugin-venvs) valdes bort just
för att den vägen inte gick att storleksuppskatta i förväg.

Att ta bort den igen: `docker rmi ghcr.io/autonomy-logic/openplc-runtime:latest`
(967 MB). Behållaren `vcassist-openplc-v4` är stoppad, inte borttagen, så att
mätningen går att göra om utan att ladda ned något.

## 3. REST/JWT — mätt ändpunkt för ändpunkt

Runtimen kör på HTTPS 8443 med ett självsignerat certifikat den genererar vid
start. Behållaren publicerades på `127.0.0.1:18443` och `127.0.0.1:14840`.

| Anrop | Svar |
|---|---|
| `GET /api/version` | `{"version":"v4.2.1"}` — **utan inloggning** |
| `GET /api/capabilities` | `{"minEditorVersion":"4.1.0","projectSnapshot":true,...}` |
| `POST /api/login` openplc/openplc, admin/openplc, ... | `401 "Wrong username or password"` |
| `POST /api/create-user` | `201 {"id":1,"msg":"User created","role":"admin"}` |
| `POST /api/login` vcassist/vcassist | `200 access_token` (325 tecken) |
| `GET /api/status?include_stats=true` | `{"status":"STATUS:EMPTY",...}` |
| `GET /api/ping` | `{"status":"PING:OK"}` |
| `GET /api/compilation-status` | `{"exit_code":null,"logs":[],"status":"IDLE"}` |
| `POST /api/upload-file` (multipart, fält `file`) | `{"CompilationStatus":"COMPILING","UploadFileFail":""}` |
| `GET /api/start-plc` | `{"status":"START:OK"}` |

**Säkerhetsfynd, inte ett sidospår.** En färsk runtime har **noll** användare:

```
$ docker exec ... sqlite3 /run/runtime/restapi.db "select * from users"
   (tom)
```

Första `POST /api/create-user` kräver ingen inloggning och ger **admin**.
Runtimen är alltså osäkrad tills någon tar kontot. Det får aldrig exponeras
utanför loopback utan att kontot skapats först.

## 4. Vad projektarkivet måste innehålla

Runtimen tar inte emot ST. Den tar emot **redan genererad C++** och bygger en
`.so`. Varje krav nedan hittades genom att filen saknades och bygget föll med
det citerade felet.

| Fil | Vad som händer utan den |
|---|---|
| `generated.hpp` + minst en `.cpp` | `[ERROR] Missing required source files` |
| `defines.h` med `PROGRAM_MD5` | `make: *** No rule to make target 'core/generated/defines.h'` |
| `generated_debug.cpp` | bygget lyckas, men `.so`:n vägrar laddas: `undefined symbol: _ZN7strucpp5debug17debug_array_countE` |
| `strucpp_runtime/include/` | headers vendoras inte i runtimen, de följer med varje uppladdning |
| `conf/opcua.json` | `[INFO] No conf directory found in core/generated, disabling all plugins` |

Med `conf/opcua.json` på plats: `[DEBUG] Final state - opcua: enabled=True`,
`[INFO] Plugin summary: 1/5 enabled`.

Den tredje raden är den dyraste: `START:OK` kom tillbaka som om allt gick bra,
och först i runtimeloggen syntes att `.so`:n aldrig laddades. Därför läser
`OpenPlcV4.starta_och_vanta()` alltid tillbaka tillståndet, och fäller på
`EMPTY`.

## 5. STruC++ finns, men CLI:t skriver bara halva bygget

`strucpp-linux-x64.tar.gz` v0.6.6 (27,9 MB, uppackad 74 MB binär) laddades ned
från `Autonomy-Logic/STruCpp`. Den kompilerar vår genererade ST:

```
$ strucpp prov.st -o out.cpp
Compiling prov.st...  Output written to out.cpp  Header written to out.hpp
Compilation successful!
```

Men den skriver **aldrig** `generated_debug.cpp` eller `debug-map.json`.
`grep -n "debugTableCpp\|debugMap" dist/node/cli.js` ger noll träffar; båda
produceras av `compile()` i `dist/index.js` och kastas bort av CLI:t. Utan dem
går programmet inte att ladda (punkt 4) och OPC UA-noderna går inte att binda
(punkt 6). Därför kör `svc/vc_assist_svc/plc/strucpp_bygg.mjs` kompilatorns
eget API i stället för dess CLI. Samma kompilator, samma anrop som editorn gör.

Lokaliserade adresser översätts så här (mätt genom att kompilera sju
deklarationer och läsa `locatedVars[]`):

```
{ Input,  Bit,   0, 0 }   // A AT %IX0.0
{ Input,  Bit,   1, 3 }   // B AT %IX1.3
{ Input,  Byte,  2, 0 }   // C AT %IB2
{ Input,  Word,  1, 0 }   // D AT %IW1
{ Output, DWord, 2, 0 }   // E AT %QD2
```

Indexet är alltså **per storleksklass**, inte ett byteoffset. Det stämmer mot
runtimens bildtabeller, `core/src/plc_app/image_tables.h`:
`bool_input[1024][8]`, `byte_input[1024]`, `int_input[1024]`,
`dint_input[1024]`, `lint_input[1024]` — skilda fält. Två adresser i olika
storleksklasser delar därför inte minne, och `BUFFER_SIZE` = 1024 är
indexgränsen. Båda talen står som konstanter i `signalkarta.py` med den här
raden som härkomst.

## 6. OPC UA-noderna: namnet är fritt, adressen är det inte

Det här var den öppna frågan i `60_plc.md` ("namnkonvention eller mappfil?").
Svaret ur koden:

* Det finns **ingen** `%IX0.0`-tolkning och **ingen** symboluppslagning i hela
  pluginkatalogen. `node_id` och `browse_name` är fri text ur `opcua.json`.
* Kopplingen till PLC-minnet är heltalsparet `(arr, elem)`:
  `address_space.py:274` `self.variable_nodes[(var.arr, var.elem)] = var_node`,
  och `opcua_memory.py` säger rakt ut att pluginet är variabelpositions-agnostiskt
  och bara vidarebefordrar paret.
* Paret finns bara i kompilatorns `debug-map.json`:
  `{"arrayIdx":0,"elemIdx":1,"path":"INST0.UT","type":"BOOL","size":1}`.

Alltså: **namnet genereras** (`PLC.<station>.<tagg>`, av `opcuakonfig.nodid`),
**adressen slås upp** i kompilatorns karta. Gissar man paret pekar noden på fel
variabel utan att något klagar.

Browsning av den körande servern bekräftar formen:

```
NodeId=ns=2;s=PLC.Matstation.matin   BrowseName=2:matin
NodeId=ns=2;s=PLC.Matstation.matut   BrowseName=2:matut
namespace array: ['http://opcfoundation.org/UA/', 'urn:freeopcua:python:server', 'urn:openplc:opcua']
```

Punkterna i identifieraren skapar ingen trädstruktur; noderna hänger platt
under Objects.

### Konfigurationsfilens hårda krav (mätt genom att ta bort ett fält i taget)

| Borttaget | Laddarens svar |
|---|---|
| `format_version` eller värdet 1 | `Unsupported opcua.json format_version 0 (this runtime requires >= 2)` |
| `size` på en variabel | `Missing required field in simple variable: 'size'` |
| hela `users` | `Missing required section in OPC-UA config: 'users'` (tom lista är OK) |
| `protocol` ≠ `"OPC-UA"` | `Invalid protocol for plugin #1` |

Och om filen saknas helt: `Configuration file not found` → `load_config()`
returnerar `None` → servern startar inte. `get_default_config()` finns i
`config.py` men har **noll anropare**; den är död kod.

### Två fällor i endpointen

1. `endpoint_url` är också **bindningsadress**. Mallens `localhost` binder till
   127.0.0.1 *inne i behållaren* och går aldrig att nå utifrån.
2. `0.0.0.0` skrivs om till behållarens hostnamn (`60dbe9704183`), som värden
   inte kan slå upp. Orsaken är att pluginets `get_local_ip()` filtrerar bort
   hela 172.16.0.0/12 — behållarens enda riktiga adress.

Vi sätter därför behållarens IP rakt av: `opc.tcp://172.17.0.2:4840/openplc/opcua`.

### Anonym åtkomst

Med `users: []` mappas en anonym klient till rollen **engineer**
(`user_manager.py:544-553`), alltså full skrivrätt. Det enda som då skiljer en
läsbar nod från en skrivbar är rättigheterna per variabel. Därför sätter
`opcuakonfig.py` `r` för **alla tre rollerna** på varje utgång och varje
säkerhetsmärkt tagg: en klient som kan skriva PLC:ns utgångar styr scenen förbi
PLC:n, och då mäter ögat en sekvens som PLC:n aldrig körde.

## 7. Tre fynd som kostade tid och som är värda att skriva ned

**`asyncua.sync` hängde.** Den synkrona klienten blev stående i
`connect()` mot den här servern: 5 minuter 29 sekunder väggklocka, **0 sekunder
CPU**, processen fick tas bort för hand. Samma server, samma URL, med den
asynkrona klienten: **ansluten på 6,7 ms**. Mätningen kör därför asyncio direkt.

**`{SAKERHET}` går inte igenom kompilatorn.** ST-lagrets skrivare sätter
pragmat på en säkerhetsmärkt deklaration (I15). STruC++ 0.6.6 känner inte igen
IEC:s pragmaklamrar:

```
unexpected character: ->{<- at offset: 52, skipped 1 characters.
```

Märket hör till grind 2 och 3, inte till kodgenereringen, så
`paket.for_kompilator()` skalar av exakt den strängen på vägen till
kompilatorn. Deklarationer, adresser och kropp är i övrigt tecken för tecken
desamma.

**`RUNNING` kommer före OPC UA-servern.** Runtimen rapporterar RUNNING och
startar sedan pluginet: 1,5 s glapp i loggen mellan `PLC State: RUNNING` och
`OPC-UA server started`. Ansluter man i glappet får man `ConnectionRefused`,
vilket ser ut som att servern inte finns. Mätharnessen försöker om.

## 8. Tur och retur

**Metod.** Programmet är genomsläpp — `matut := matin;` — och deklarationerna
kommer ur signalkartan. En mätning: skriv insignalen över OPC UA, läs
utsignalen i en tät slinga tills den följt med, stoppa klockan. Varje mätning
växlar värde, annars hade PLC:n redan haft rätt svar på utgången. Tio varv
uppvärmning räknas inte (I5). Tre oberoende serier à 120 mätningar per
inställning.

**Golvet först.** En ensam läsning, 200 stycken, för att veta hur mycket av
tiden som är klienten och nätet:

| Scanperiod | Golv median | Golv p95 | Golv max |
|---|---|---|---|
| 10 ms | 0,41 ms | 0,89 ms | 2,29 ms |
| 20 ms | 0,40 ms | 0,53 ms | 3,00 ms |
| 50 ms | 0,57 ms | 0,69 ms | 0,99 ms |

En OPC UA-läsning kostar en halv millisekund. Tur och retur-talen nedan är
alltså PLC:ns, inte transportens.

**Tur och retur, tre serier per inställning:**

| Scanperiod | Serie | Median | Medel | p95 | Min | Max | s |
|---|---|---|---|---|---|---|---|
| **10 ms** | 1 | 20,00 | 20,00 | 20,48 | 18,91 | 21,39 | 0,31 |
| | 2 | 19,98 | 20,00 | 21,41 | 13,80 | 25,02 | 1,06 |
| | 3 | 19,94 | 20,00 | 20,54 | 17,35 | 22,51 | 0,47 |
| **20 ms** | 1 | 40,02 | 40,00 | 40,47 | 36,05 | 43,67 | 0,59 |
| | 2 | 39,98 | 40,00 | 40,62 | 32,89 | 47,05 | 1,31 |
| | 3 | 40,00 | 40,00 | 40,89 | 35,44 | 44,22 | 0,88 |
| **50 ms** | 1 | 100,03 | 100,00 | 100,89 | 95,47 | 103,69 | 0,89 |
| | 2 | 99,97 | 100,00 | 100,77 | 97,05 | 103,04 | 0,69 |
| | 3 | 99,99 | 100,00 | 100,99 | 96,38 | 103,14 | 0,67 |

Alla tal i millisekunder. n = 120 per serie, 1080 mätningar totalt.

**Talet är två scan, exakt.** 10 → 20,0. 20 → 40,0. 50 → 100,0. Medelvärdet
ligger på 20,00 / 40,00 / 100,00 med tre värdesiffror i varje serie. Det är
inte en slump som råkar bli snygg: skrivningen landar i bildtabellen mellan två
scan och måste vänta ut en hel period innan PLC:n läser den, och svaret måste
vänta ut nästa innan det syns. Samma faslåsning som M-03 mätte på bryggan, med
samma signatur: medianen ligger på en hel period, inte på en halv.

Spridningen är liten (s ≤ 1,3 ms) och svansen kort. De enstaka låga värdena —
13,8 ms vid 10 ms period — är varv där skrivningen råkade landa strax före en
scan. Pluginets synkloop på 10 ms syns inte i talet: den ligger under
scanperioden i alla tre fallen och är därför aldrig den långsammaste länken.

**Praktisk konsekvens:** väljer man scanperioden väljer man svarstiden.
`paket.TASKINTERVALL` står på 20 ms, vilket är editorns egen standardperiod och
den period hela tabellen ovan vilar på.

## 9. Vad som inte är mätt

* **Visual Components.** Fas 6:s grind i `70_faser.md` heter "handskriven ST
  styr scenen genom OPC UA". Scenen ingår inte här: VC kördes av operatören
  under hela arbetet och fick inte startas en andra gång. Det som är mätt är
  **PLC-halvan** av bandet, från OPC UA-klient till scancykel och tillbaka.
  Om VC:s connectivity-plugin klarar den annonserade endpointen, hur många
  variabler den orkar med, och vad hela kedjans svarstid blir med scenen i
  andra änden är **oprövat**.
* **Windows.** Allt ovan är Linux (I17).
* **Fler än två signaler.** Provstationen har en in och en ut. Hur
  svarstiden beter sig med hundra taggar är inte mätt.
* **Säkerhetslägen i OPC UA.** Bara `None/None` med anonym åtkomst är körd.
  Certifikat och `Basic256Sha256` är oprövat.
* **Belastning.** Ingen mätning gjordes med samtidig trafik, och maskinen körde
  operatörens VC parallellt.

## 10. Diskräkning

| | Före | Efter |
|---|---|---|
| Ledigt på `/` | 9,9 G | 11 G |

Nettot är positivt därför att annat frigjordes under tiden; vår egen
förbrukning var **cirka 1,1 G** för v4-avbildningen och behållarens skrivlager,
plus 864 MB i sessionens scratchpad (STruC++, npm-beroenden, byggkataloger)
som inte ligger i repot. Operatörens v3-behållare och båda v3-avbildningarna är
orörda.
