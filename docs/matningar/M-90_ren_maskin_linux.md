# M-90 — ren Linux-maskin: klona, installera, kör (och README motsade repot)

**Datum:** 2026-09-05
**Rigg:** `docker run --rm ubuntu:24.04`, ingenting förinstallerat
**Prövar:** fas 10:s grönt — *"Ren maskin: klona, installera, kör. Fungerar utan handpåläggning."*

## Varför en container räknas som en ren maskin

Fas 10 stod som **"byggd, oprövad på ren maskin"**. Den öppna punkten var inte
Windows utan något enklare: allt hade bara körts på maskinen där det byggdes,
där varje beroende redan råkar finnas. En tom `ubuntu:24.04` har varken `python3`
eller `git`. Det är den realistiska rena maskinen — och Ubuntus `python3` är
**minimal**, vilket är precis där ett "bara standardbiblioteket"-löfte brukar
brista.

## Vad som mättes

**1. Standardbiblioteket räcker — mätt två vägar.**

Alla moduler installationen och tillägget rör finns på en minimal `python3`
3.12.3: `json`, `hashlib`, `urllib.request`, `tarfile`, `zipfile`, `sqlite3`,
`lzma`, `ctypes`, `ssl`, `zlib`, `bz2`, `xml.etree.ElementTree`. **Saknas:
inget.**

Andra vägen, oberoende av den första: en AST-genomgång av allt under `install/`
som samlar varje `import` och drar bort `sys.stdlib_module_names` och repots
egna moduler. **Importer utanför stdlib och repot: inga.**

**2. `git clone` → `installera.py sok` → `installera --mal` fungerar.**

```
nya: 11   uppdaterade: 0   oforandrade: 0   borttagna: 0
verifierat pa plats: 11 filer parsar och kompilerar
returkod: 0
```

Körd en andra gång på oförändrad källa: **`nya: 0, uppdaterade: 0, oförändrade:
11`**. Installationen är idempotent, och det är mätt och inte antaget.

**3. Utan VC låtsas den inte lyckas.** `sok` på en maskin utan Visual Components
listar noll dokumentmappar, noll VC-mappar, returnerar **2**, och skriver ut
exakt kommandot användaren behöver i stället. Ett tyst noll-utfall hade varit
det farliga svaret här.

## Vad riggen INTE mätte, och varför

Första körningen dog på `fatal: detected dubious ownership in repository`. Det
är **riggens** fel, inte produktens: `/src` är en bindmontering ägd av uid 1000
medan containern kör som root. En riktig användare klonar från en fjärr. Rättat
med `safe.directory`, och skrivet här så att ingen läser det som ett fynd.

Ett andra prov av mig gav också skräp: en `grep` efter "3.x-konstruktioner"
matchade `%.3f"` och tolkade formatsträngar som f-strängar. Fyra falska träffar,
inget verkligt fynd. Py3-syntaxprovet med `dont_inherit=True` är det som gäller,
och det gav **inga fel** över alla 11 filerna.

## Fyndet: README motsade repot på sin egen förstasida

Under körningen läste jag README:s statustabell. Den sa:

```
| 6 | PLC-bandet       | **inte påbörjad** | Inget protokoll |
| 7 | ST för en station| **inte påbörjad** | Inget protokoll |
| 8 | Komposition      | **inte påbörjad** | Inget protokoll |
| 9 | Bänken           | **inte påbörjad** | Inget protokoll |
```

Alla fyra är stängda i `docs/spec/70_faser.md`, var och en med sina mätningar
(M-39; M-49/M-50; M-73/M-74; M-80). README saknade dessutom rad för fas 11–18
helt, och nämnde inte att `pytest` behövs för att köra proven — vilket den rena
maskinen visade direkt (`No module named pytest`).

**Skuldregistret kunde inte se det här.** Båda texterna är välskrivna och
innehåller ingen markör. Skuld som inte skriver om sig själv är osynlig för ett
mönster — den syns bara när **två källor ställs mot varandra.**

## Grinden, och att den hade mitt eget fel först

`tests/enhet/test_readme_faser.py` läser fastabellen ur båda filerna och fäller
när README säger *inte påbörjad* om en fas specen kallar **stängd** eller
**passerad**. Regeln är med flit ensidig: README får vara kortare än specen, men
inte mindre färdig.

Första versionen av mönstret tog också orden *klar* och *mätt*, och fällde då
fas 13 — vars rad säger *"Allt är byggt och mätt under Wine"*. Det är en
beskrivning av vad som mätts på **annat håll**, inte ett besked om att fasen är
klar. Grinden hade alltså exakt det fel den byggdes för att fånga: **ett mönster
som ser ut att matcha, aldrig prövat mot texten det ska läsa** — samma klass som
M-70 och M-66. Fas 13:s verkliga rad står nu som ett låst fall i provet.

Grinden föll på fyra rader före rättelsen och faller fortfarande om fas 6:s
gamla rad återinförs.

## LIMITS

* **Linux, en distribution, en Pythonversion.** `ubuntu:24.04` med python
  3.12.3. Säger ingenting om Windows (fas 13) eller om andra distributioner.
* **VC startades aldrig.** Fas 10:s kvarvarande öppna punkt — *att VC startar
  med det installationen lade dit* — är fortfarande oprövad och kräver ett
  testprefix med licens. Den här mätningen flyttar inte den punkten.
* **Verktygskedjan hämtades inte** i den rena maskinen. Nedladdningarna är
  30,3 MB för Linux-vägen (STruC++ 27,94 MB + npm-paketet 2,38 MB) med
  fastspikad hash, mätt i M-56 — men på den här maskinen, inte i containern.
* **Provsviten kördes inte** i containern, eftersom `pytest` inte finns där.
  Att den *skulle* gå igenom efter `pip install pytest` är alltså inte mätt.
* **Idempotensen är mätt över två körningar**, inte över en ändrad källa följd
  av en oförändrad. Att `uppdaterade` räknar rätt när en fil faktiskt ändrats
  är prövat i `tests/enhet/test_install.py`, inte här.
