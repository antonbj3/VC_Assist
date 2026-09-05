# M-156 — INVENTERING: docs/spec/60_plc.md mening for mening mot koden (A12)

**Datum:** 2026-09-05 · kö A, punkt A12
**Typ:** **INVENTERING, inte mätning.** Ingenting är kört för att producera ett
tal här. Metoden är: läs `docs/spec/60_plc.md` mening för mening, och för varje
mening som gör ett påstående om koden, leta upp koden som uppfyller den. De
meningar där sökningen inte hittade någon kod står nedan, med filnamn och
radnummer **där den borde ha stått**. Det är en lista att arbeta av, inte ett
resultat att citera.
**Rigg:** `grep`/läsning i arbetsträdet vid commit `daf4578`. Ingen körning,
inget prov, inget verktyg startat.
**Prövar:** ingenting. Se LIMITS.

---

## Metod, och vad som räknas som "ingen kod uppfyller"

Specen är 152 rader. Rubriker, tabellhuvuden, rättelseboxar och citat av
tidigare versioner räknas inte — de gör inga påståenden om nuvarande kod.
Kvar blir **31 meningar** som påstår något om vad koden gör.

En mening räknas som **UPPFYLLD** när det finns kod som gör det den säger, och
den koden går att peka ut med fil och rad. Den räknas som **OUPPFYLLD** när
sökningen inte hittade någon sådan kod. Den räknas som **DELVIS** när koden
finns på ett ställe men saknas där meningen får en att tro att den finns.

Sökningen är inte ett bevis på frånvaro. Se LIMITS.

**Utfall: 26 uppfyllda, 1 delvis, 4 ouppfyllda.**

---

## De fyra ouppfyllda, och den enda delvis

### O-1 — `60_plc.md:20-21` · "läs den ur uppsättningen"

> *"Porten är containerns mappning, inte en egenskap hos OpenPLC — hårdkoda den
> inte, läs den ur uppsättningen."*

**Det finns ingen uppsättning att läsa den ur.** Ingen modul i repot håller
PLC-benets konfiguration. Porten står som ett literalt standardvärde på sex
ställen och som ett miljövariabelfall på ett:

| Var den står i dag | Rad | Form |
|---|---|---|
| `tests/protocol/kor_allt.py` | 179 | `default=14840` |
| `tests/protocol/kor_fas6_slinga.py` | 147 | `default="opc.tcp://127.0.0.1:14840/"` |
| `tests/protocol/kor_fas7_station.py` | 1130, 1133 | `default="https://127.0.0.1:18443"`, `default="opc.tcp://127.0.0.1:14840/"` |
| `tests/protocol/kor_fas8_linan.py` | 1554, 1557 | samma två |
| `svc/vc_assist_svc/plc/matning.py` | 306 | i argparse-hjälptexten |
| `bank/domare_openplc.py` | 229 | `os.environ.get("VC_ASSIST_OPENPLC_BAS", "https://127.0.0.1:18443")` |

**Där den borde ha uppfyllts:** `svc/vc_assist_svc/plc/__init__.py:23-28`
exporterar `konfiguration`, `nodid` och `variabel` ur `opcuakonfig` — men
`opcuakonfig.konfiguration` är OPC UA-**serverns** konfigurationsfil, inte
vår uppsättning av var servern finns. Det saknas alltså en modul
`svc/vc_assist_svc/plc/uppsattning.py` (eller motsvarande) som de sju
ställena ovan läser ur.

**Notera formen:** den senast skrivna av de sju (`bank/domare_openplc.py:229`,
kö A:s A2-arbete samma dag) är också den enda som går att styra utifrån. Den
är den form de andra sex borde ha.

---

### O-2 — `60_plc.md:37,44-45` · "Slingan sluts … i tjänsten"

> *"Slingan sluts i stället **utanför VC**, i tjänsten"* och
> *"Kopplaren är `svc/vc_assist_svc/plc/kopplare.py`. Den kör i CPython 3 i
> tjänsten och äger båda sidorna av varvet."*

`Kopplare` finns och är prövad. Men **ingen tjänstekod konstruerar en.**

* `svc/vc_assist_svc/plc/__init__.py:23-28` exporterar `signalkarta`,
  `deklarationsgrind`, `opcuakonfig`, `openplc`, `paket` och `matiec` — men
  **inte** `kopplare`. Modulen går bara att nå med en fullständig sökväg.
* `svc/vc_assist_svc/forlopp/kallor.py:149` (`kor_kopplaren`) **kör** en
  kopplare den får inskickad, men bygger aldrig en.
* De enda ställen där en `Kopplare` byggs med en riktig OPC UA-klient och en
  riktig brygga är acceptansskripten:
  `tests/protocol/kor_fas6_slinga.py:171`, `kor_fas7_station.py`,
  `kor_fas8_linan.py`. Alla andra 12 konstruktionsställen är enhetsprov med
  attrapper (`tests/enhet/test_kopplare.py`, `test_forlopp_kallor.py`).
* `service/vc_assist/` är en **tom katalog** — `git ls-files service` ger noll
  filer.

**Där den borde ha uppfyllts:** `service/vc_assist/` (ingången som skulle
bygga och driva slingan) och `svc/vc_assist_svc/plc/__init__.py:23` (exporten).

Meningen är alltså sann om var koden **bor** och osann om var den **körs**:
slingan sluts i ett acceptansskript, inte i en tjänst.

---

### O-3 — `60_plc.md:12` · "vår kopplare är klient"

> *"| Transport | OPC UA | PLC:n är server, vår kopplare är klient |"*

Den enda OPC UA-klienten i repot ligger i
`svc/vc_assist_svc/plc/matning.py:72-84` (`asyncua`), och **paketets egen
dokumentation säger att den inte är tjänstelager**:

> *"Allt i det här lagret använder endast standardbiblioteket. Undantaget är
> `matning.py`, som är en mätharness och inte tjänstelager; den beror på
> asyncua och exporteras inte härifrån."*
> — `svc/vc_assist_svc/plc/__init__.py:16-19`

`Kopplare.__init__` (`kopplare.py:93`) tar `ua` som ett injicerat objekt och
kräver bara två metoder, `las` och `skriv`. Det är en bra gräns — men den
betyder att den klient meningen påstår att vi har bor i mätharnessen, inte i
tjänsten.

**Där den borde ha uppfyllts:** `svc/vc_assist_svc/plc/` saknar en
klientmodul som `plc/__init__.py` kan exportera. O-2 och O-3 är samma hål sett
från två håll.

---

### O-4 — `60_plc.md:89` · "VC-scen ──► signalkarta"

> ```
> VC-scen ──► signalkarta ──► OPC UA-nodlista ──► ST VAR-block
> ```

Tre av fyra pilar finns. **Den första har ingen kod.** Ingenting i repot bygger
en `Signalkarta` ur en VC-scen. Alla producenter:

| Producent | Rad | Källa |
|---|---|---|
| `bank/reparationsbank.py:83` `karta_ur_uppgift` | 83-111 | bankuppgiftens `control.signals` (JSON) |
| `bank/domare_openplc.py:363` | 363 | samma väg |
| `svc/vc_assist_svc/plc/signalkarta.py:396,414,422` | `fran_json`, `las_text`, `las_fil` | en fil någon redan skrivit |
| `svc/vc_assist_svc/plc/matning.py:134` `provkarta` | 134 | handskrivna rader i en mätharness |
| `svc/vc_assist_svc/harness/fallor.py:173` | 173 | en provfixtur |
| `scripts/gemini_verify/probe_*.py:26-27` | 26, 27 | handskrivna rader |

Ögat kan läsa scenen (`ext/vc_addon/vc_assist/`), och kartan kan skrivas till
och läsas ur JSON. Det som saknas är ledet däremellan: ingenting går från
en avsökt scen till en `Signalkarta`.

**Där den borde ha uppfyllts:** `svc/vc_assist_svc/plc/signalkarta.py` (en
`karta_ur_scen`-väg vid sidan av `karta_av_rader:434`), eller
`svc/vc_assist_svc/plc/ogonkoppling.py`. Konsekvensen är konkret: varje karta
projektet har använt kommer ur en uppgiftsfil eller en handskriven rad, aldrig
ur en scen — och därför är felklassen *"kartan och scenen är osams"* aldrig
prövad på riktig data.

---

### D-1 — `60_plc.md:14` · "Kompilator `STruC++` CLI — körs som grind 1"

Grind 1 finns och anropar den (`svc/vc_assist_svc/plc/stationsgrind.py:207-239`,
`_grind_1`), och kedjan för att bygga den finns
(`svc/vc_assist_svc/plc/strucpp_bygg.mjs`,
`install/strucpp-0.6.6-package-lock.json`). Men binären ligger **inte** i repot,
`plc/` i roten är tom, och `which strucpp` ger inget på den här maskinen.
Meningen är därför sann om koden och falsk om en ren klon: grind 1 hoppas över.
Det är känd skuld sedan `M-48` och står redan i skuldregistret — den tas upp
här bara för att den är en av de 31 meningarna, inte som ett nytt fynd.

---

## Åt andra hållet: kod specen inte nämner

Inte en del av A12:s fråga, men det upptäcktes under samma genomläsning och
hör till samma inventering.

| Vad koden har | Var | Vad specen säger |
|---|---|---|
| **matiec** som andra kompilator och typfacit | `svc/vc_assist_svc/plc/matiec.py` (hela filen), satt av `M-121` | nämns inte med ett ord; tabellen på rad 14 har bara STruC++ |
| **PLCopen XML-export** | `svc/vc_assist_svc/plc/plcopen.py`, `M-154` | nämns inte; specen har ingen väg ut alls |
| **Industrigrinden** (tidsvakt/larm/förregling) | `svc/vc_assist_svc/plc/industrigrind.py` (annan session, samma dag) | nämns inte |
| **`Ogonkoppling`** och kompensationsfönstret | `svc/vc_assist_svc/plc/ogonkoppling.py`, `M-42` | rad 125-137 beskriver kravet men namnger aldrig modulen |

`M-121` gjorde matiec till typauktoritet där de två kompilatorerna är oense.
Att tabellen på rad 14 fortfarande bara namnger STruC++ är den enskilt mest
missvisande raden i dokumentet — den säger vilket verktyg som dömer, och den
säger fel verktyg.

---

## De 26 uppfyllda, i korthet

Listas för att nämnaren ska finnas. En lista över hål utan sitt antal är ett
tal utan nämnare. Raderna är **16** och täcker de **26** meningarna: några
meningar hör ihop och uppfylls av samma kod, och de står då på en rad.

| Specrad | Uppfylls av |
|---|---|
| 11 (OpenPLC v4, headless inladdning) | `plc/openplc.py:12-19,166` |
| 13 (REST + JWT, fyra ändpunkter) | `plc/openplc.py:12-19` — alla fyra namngivna |
| 46 (scenskrivning genom kön, aldrig `exec`, I12) | `plc/kopplare.py:160-171` (`brygga.koa` + `godkann_och_vanta`) |
| 59-63 (explicit deklaration, inte namnkonvention) | `plc/signalkarta.py:293` |
| 69-74 (kartans sex fält) | `plc/signalkarta.py:183-201` — alla sex finns |
| 76-78 (sex avvisningar vid konstruktion) | `plc/signalkarta.py:203-237` — alla sex |
| 79-80 (tre avvisningar på kartnivå) | `plc/signalkarta.py:299-326` — alla tre |
| 82-84 (fail-closed, kopplaren har ingen gren för trasiga signaler) | `plc/kopplare.py` saknar en sådan gren |
| 92-94 (modellen skriver aldrig deklarationer) | `plc/skelett.py:223` (`plocka_ur`, ramjämförelse tecken för tecken) |
| 100-101 (fyra led, varje led tidtas) | `plc/kopplare.py:46-75,180-201` — fyra `*_ms`-fält |
| 116-117 (tre raka fel, lyckat varv nollställer) | `plc/kopplare.py:38,199,204-211` |
| 119-123 (spärren finns och fäller slingan) | `plc/kopplare.py:204-211` (`Kopplarfel`) |
| 125-126 (avbrottet märks i ögats serie) | `plc/kopplare.py:216-229` (`_till_ogat` → `bryt`) |
| 130-132 (PLC-värden på scenens tidslinje) | `plc/ogonkoppling.py` (hela) |
| 134-137 (gemensam tidsaxel, mätt osäkerhet) | `plc/ogonkoppling.py:40-46` (`KOMPENSATIONSFONSTER`, satt av M-42) |
| 141-144 (`skyddad` kontrolleras mekaniskt) | `harness/sakerhet.py:255-300,341-371` (SAK-003), `signalkarta.py:347` |

---

## LIMITS — vad den här inventeringen INTE visar

* **Den mäter ingenting.** Inget prov kördes, ingen siffra producerades. Att en
  mening står som UPPFYLLD betyder att kod hittades som gör det den säger —
  **inte** att koden är riktig, prövad eller körd. Flera av de 26 vilar på
  prov som inte kördes om här.
* **Frånvaro av träff är inte frånvaro av kod.** De fyra ouppfyllda bygger på
  `grep` över `svc/`, `bank/`, `ext/`, `install/`, `scripts/` och `tests/`.
  Finns koden under ett namn jag inte sökte på står den fel i listan. Varje
  O-rad namnger vad som söktes så att det går att motbevisa.
* **Meningsräkningen är min bedömning.** "31 meningar som påstår något om
  koden" bygger på att jag räknade bort rubriker, tabellhuvuden,
  rättelseboxar och citat. En annan läsare får ett annat tal. Nämnaren är
  därför ungefärlig; täljaren (4 ouppfyllda) är det som betyder något.
* **Avsnittet "Vad som inte är prövat" (rad 146-152) granskades inte.** Det är
  specens egna förbehåll, inte påståenden om kod. Att flera av dem kan ha
  blivit prövade sedan de skrevs (`M-73`, `M-132`, `M-140`) är **inte**
  kontrollerat här och kan göra avsnittet inaktuellt åt det farliga hållet —
  ett förbehåll som står kvar efter att det upphört gäller får ett verkligt
  hål att se ut som ett känt.
* **Ingen av de fyra ouppfyllda är lagad.** Inventeringen är listan, inte
  arbetet.
* **Bara `60_plc.md`.** `61_st_generering.md`, som rad 96 hänvisar till, är
  inte läst mot koden.
