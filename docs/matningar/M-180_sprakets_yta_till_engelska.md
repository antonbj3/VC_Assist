# M-180 — steg 1 i språkplanen: produktens yta till engelska

**Datum:** 2026-09-05
**Rigg:** `tests/enhet` (7 949 prov, pytest 9.0.2, `-p no:randomly`), körd till fil
och läst med separat returkod — aldrig genom ett rör.
**Prövar:** att `docs/spec/56_sprakplanen.md` steg 1 — de användarvända
strängarna och ögats domsord — går att flytta till engelska utan att ett enda
prov blir rött som inte redan var det.

## Vad steg 1 omfattade, mätt före arbetet

| storhet | tal |
|---|---|
| användarvända strängar enligt språkplanens egen grep (`svc/ ext/ install/`) | **564** |
| **samma kategori mätt med AST i stället för grep** | **664** |
| domsordsförekomster i kod, prov och bank (kontraktstoken) | **46** |
| varav förekomster som bytte text | **34** |
| varav identitet (`timing` → `timing`) | **12** |

564, inte 560: språkplanens tal är från innan modulerna växte. Grep:en är
oförändrad, talet är räknat om.

**Och grep:en undermätte ytan med 100 strängar.** Se §4 — det är mätningens
viktigaste fynd.

## 1. Domsorden — ett kontrakt, inte text

Ögats domsrad ser ut så här, och grinden läser den byte för byte:

```
EYES VERDICT FAIL forregling: ST260_STA_BUSY steg 7.45 s fore ST250_STA_DONE
```

Producenten är `ext/vc_addon/vc_assist/oga_analys.py` (`Analys._dom`).
Konsumenterna är bankens `expect.reason_contains` — läst av `bank/lasare.py`
rad 118, `res.orsak_stammer = e["reason_contains"] in rapport.dom[1]` — bankens
åtta `broken`-fixturer, och sex provfiler. Byts ett ord på ett ställe och inte
på alla går det sönder **tyst**: ett facit slutar stämma utan att en rad
kraschar.

**Alla 46 förekomster flyttade i EN commit** (`1b55ee5`), med prov och fixturer.

| ord | → | förekomster | var |
|---|---|---|---|
| `forregling` | `interlock` | 9 | producent 1, prov 6, bank 2 |
| `grepp` | `grasp` | 7 | producent 5, prov 1, bank 1 |
| `genomflode` | `throughput` | 6 | producent 2, prov 2, bank 2 |
| `sekvens` | `sequence` | 5 | producent 1, prov 2, bank 2 |
| `kapplopning` | `race` | 4 | producent 1, prov 1, bank 2 |
| `hederlighet` | `integrity` | 2 | producent 1, bank 1 |
| `geometri` | `geometry` | 1 | bank 1 |
| `timing` | `timing` | 12 | identitet — ingen text ändrades |

Bankens åtta `broken`-fixturer bär exakt ett domsord var (`A-91` förregling,
`T-91` sekvens, `P-91` grepp, `H-90` kapplöpning, `C-90` genomflöde, `L-90`
geometri, `P-92` hederlighet, `T-92` timing). Fyra bar ordet också i
`reason_contains`; de fyra flyttade med.

**Kontraktsdokumentet behövde inte flytta, och det är en brist.**
`docs/spec/41_ogat_kontrakt.md` skriver domsraden som
`EYES VERDICT <PASS|FAIL|INCONCLUSIVE> <orsak utan radbrytning>` — orsaken är
fritext i grammatiken, och de åtta orden står ingenstans i specen. Vokabulären
är alltså ett **oskrivet** kontrakt som bara lever i producenten, i banken och
i `M-65 §4`. Det gick att byta utan att röra specen, vilket är precis varför en
sådan koppling är farlig.

## 2. De 564 (respektive 664) strängarna

Flyttade modul för modul, i små commits, av elva parallella skrivare med samma
ordlista och samma grind. Varje skrivare körde de provfiler som rör sin modul
före och efter och jämförde antalet röda.

| | |
|---|---|
| commits med `sprak steg 1` i meddelandet | **108** |
| filer rörda | **121** (82 källfiler, 32 provfiler, 7 bankfiler) |
| provpåståenden som behövde flytta med | ~45 |

## 3. Röda prov

| | röda |
|---|---|
| före allt arbete (`master` @ `e55afd8`) | **8** |
| efter | **5** |

De åtta röda före var inte mina, och de fem efter är en delmängd av dem:

* `test_referenser_mot_grindkedjan.py` × 5 (`S-02`, `S-03`, `S-04`, `T-03`,
  `T-06`) — röda före, röda efter, orörda av mig.
* `test_bankkontrakt.py::test_ingen_forraldralos_korning` och
  `test_baslinje.py` × 2 blev gröna under passet, av **andra sessioners**
  commits (`174b7f9` BANKPOST för `kor_markering`, `d613d68` baslinjens två
  spärrar). Inte min förtjänst, och de räknas inte som ett resultat här.

Antalet röda ökade alltså inte. `tests/motbevis` är röd som avsett och rördes
inte.

## 4. Fyndet: språkplanens grep undermätte ytan med 18 %

Språkplanen räknar de användarvända strängarna med

```
grep -rhoE 'print\(["\x27][^"\x27]{8,}|raise [A-Za-zÅÄÖåäö]*[Ff]el\(["\x27][^"\x27]{8,}'
```

Den matchar bara när citattecknet står **direkt** efter parentesen. Ett anrop
skrivet så här är osynligt för den:

```python
raise Bildfel(
    "okänt delsystem %r; listan är sluten (%s)" % (namn, kanda))
```

Samma sorts meddelande, samma användare, samma kategori. Mätt med `ast` i
stället för `grep` är kategorin **664 strängar, inte 564**. De 100 extra hade
blivit svenska öar mitt i moduler som annars är engelska — precis den
halvöversättning språkplanen själv säger är sämre än ingen.

De stängdes i ett andra svep (`sprak steg 1 (efterslackning)`, 24 commits).
**Efter det: 0 av 664 är svenska.** Kvarvarande svenska ord inuti annars
engelska meddelanden är fältnamn och enumvärden som med flit står kvar
ordagrant (`mode finns`, `mode saknas`, `harkomst SAKNAS`, `vad`, `varde`,
`motiv`, `kalla`, `enhet`) — de är identifierare i strängform.

**Regeln som följer:** ett tal som mäter en yta ska mätas med samma
strukturkännedom som ytan har. En regex över källtext räknar formatering; en
AST räknar anrop. Skillnaden var 100 strängar, och den syntes inte i talet.

## LIMITS

**Vad som INTE är översatt, och varför.** En halvöversatt yta som ingen skrivit
ner är sämre än en svensk.

* **Ögats domsrad är fortfarande halvsvensk.** Bara *domarordet* flyttade.
  * Orsakstexten efter kolonet är oförändrad svenska:
    `interlock: förreglingen bröts`, `throughput: genomströmningskravet hölls
    inte`, `grasp: delen gled i greppet`. Prosan ligger utanför både de 664
    (den byggs av `_orsak`, inte av ett `raise`) och utanför de åtta orden.
  * Ögat lämnar ifrån sig **tre domsord till** som inte står i språkplanens
    lista av åtta: `kollision:`, `scen:` och `robot:` (`oga_analys.py`
    rad 1261, 1263–1267, 1270). De är orörda. `kollision` och `geometri` är
    dessutom **samma domare i två vokabulärer** — koden skriver `kollision:`,
    bankens `L-90` skrev `geometri:` och skriver nu `geometry:`. Den
    tvetydigheten fanns före det här arbetet och står kvar.
* **Domskoderna är orörda, med flit.** `ORORD_SIGNAL`
  (`plc/deklarationsgrind.py`, `plc/baslinje/__init__.py`), `DUBBELSKRIVNING`
  (`st/validator.py`), `VALET_FALLER` (`plan/motsagelse.py`,
  `plan/bestallning.py`), `SAKNAD_TIDSVAKT` (`plc/industrigrind.py`) och
  `E_TIMEOUT` (`klient.py`, `ext/.../protokoll.py`). De **visas** för en
  användare, i rader som `rad 75: [DUBBELSKRIVNING/F7] …`, men de är
  identifierare i strängform som andra grindar och prov matchar på ordagrant
  (`tests/enhet/test_baslinje.py` rad 689, `plc/baslinje/morfologi.py`,
  `test_brygga.py`). De hör till steg 2.
* **`SAKNAS` flyttade bara där den är en visningsplatshållare.** Ändrad till
  `MISSING` i `katalogsok.py`, `komponentdatablad.py` och `forlopp/yta.py` —
  tre ställen där konstanten bara finns för att fylla ett tomt fält i renderad
  text. Versalerna är avsiktliga: `MISSING` läses som en statusmarkör, inte som
  engelsk prosa i en svensk mening.
  Kvar står den där `SAKNAS` är en **medlem i en svensk enum**, för att en enum
  med en engelsk och tre svenska medlemmar är sämre än en konsekvent svensk,
  och för att värdet ligger i data som andra läser:
  `datablad.LAST/HARLEDD/SAKNAS`, `komponentfil.Harkomst`,
  `tillverkardatablad.FINNS/SAKNAS/ENHET_SAKNAS`,
  `scenarbete/markering.UTFALL`, `personatackning.OBYGGT`. Kvar står också
  `"saknas"` som **operator i villkorsspråket** (`plan/predikat.py
  OPERATORER`) och som JSON-nyckel i räkningar (`t["nyttolast"]["saknas"]`) —
  det är protokoll, inte text.
* **Rubrik- och renderingskonstanterna är kvar på svenska.** `forlopp/yta.py`
  och `forlopp/spegel.py` bär `ÖGATS DOM (grind 5)`, `GRINDAR`, `GULDBESLUT`,
  `SEKTIONEN %s SAKNAS I ÖGATS RAPPORT`; `komponentdatablad.py` och
  `katalogsok.py` bär `tillverkare:`, `kategori:`, `storhet`. **Följden är
  synlig:** raden lyder nu `GRINDAR: MISSING — ingen grind har kört`. Det är en
  mätt konsekvens, inte ett förbiseende — rubrikerna är en egen yta som
  språkplanens grep inte fångar, och hela förloppsvyn bör tas i ett stycke.
* **Ordlistorna i `harness/` är mätinstrument, inte utskrifter.**
  `GODKANNANDEORD`, `NEKANDE_OGONORD`, `UNDERKANNANDEORD`,
  `FRAMGANGSMARKORER`, `text.NEKANDE`, `SAKERHETSMARKORER` matchar mot
  **modellens svenska text**. Översätts de slutar de mäta. De hör till samma
  dag som prompterna byter språk, inte till den här.
* **Bankens uppgiftstexter, prompter och facit är orörda.** 63 uppgifter i
  `bank/uppgifter/*.json` bär svenska `prompt`, `goal`, `orsak`,
  `vad_som_ar_fel` och `standard`. Bara de åtta `broken`-artefakternas domsord
  och fyra `reason_contains` flyttade. Ett facit på ett annat språk är en annan
  uppgift.
* **Identifierare, kommentarer, docstrings, specar och mätningar är orörda.**
  Det är steg 2 och 3 i `56_sprakplanen.md`, och de får inte göras samtidigt.
* **Mätningen säger ingenting om att översättningarna är *bra*.** Den säger att
  de inte bröt något prov och att inget svenskt ord står kvar i kategorin. En
  sträng kan vara grammatiskt engelsk och ändå säga fel sak; det fångas bara av
  en läsare.
* **`M-65 §4` och `M-50` beskriver domsraden med de gamla svenska orden.** De är
  arbetsjournaler och skrivs inte om, men den som läser dem ska veta att
  vokabulären är bytt efter dem.
* **En bieffekt av delat repo, mätt under passet:** `scripts/committa.sh` stagar
  hela den sökväg den får. När en annan session hade osparade ändringar i
  `svc/vc_assist_svc/datablad.py` samtidigt som strängarna där flyttades, följde
  deras arbete med i commit `8db39e9`. Ingenting gick förlorat, men
  committmeddelandet beskriver inte allt commiten bär. Låset skyddar indexet,
  inte innehållet.
