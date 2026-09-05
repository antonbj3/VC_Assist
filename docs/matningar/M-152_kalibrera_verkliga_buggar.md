# M-152 — kalibrera mot verkliga buggar: hur mutationsmotorns 22 sorter täcker 82_felklasser och repots historiska fel

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell.
Underlag: `docs/spec/82_felklasser.md`, repots tidigare mätningar (`M-01` t.o.m. `M-147`).
**Prövar:** Kö C punkt C12: undersök om mutationsmotorns 22 skadesorter motsvarar
felklasser som faktiskt inträffat och definierats i projektet. En motor som
bara gör påhittade fel mäter vår fantasi, inte verkligheten.
**Körs av:** `docs/matningar/radata/m152_kalibrera_verkliga_buggar.py`.
Rådata: `docs/matningar/radata/m152_ut.txt`.

## Resultat

### §1 Täckning av 82_felklasser.md (100 % av kodklasserna)

I `82_felklasser.md` definieras 15 felklasser (`F1` t.o.m. `F15`).
Av dessa är åtta direkt applicerbara på Structured Text-kod. Alla åtta (100 %)
täcks av motorns 22 skadesorter:

| Felklass i 82 | Namn | Täckande skadesorter i motorn (22 totalt) | Verkan |
|---|---|---|---|
| `F1` | Syntax | `SEMIKOLON_STRUKET`, `END_IF_STRUKEN`, `ICKE_ASCII` | Koden kompilerar inte |
| `F2` | Okänt namn | `FLANKENS_Q_TILL_SIGNAL` | Funktionsblock används som variabel |
| `F4` | Deklaration / Typ | `TID_OGILTIG`, `JAMFORELSE_VAND` | Typfel och ogiltiga literaler |
| `F5` | Sekvens | `TILLSTAND_FASTNAR` | Tillstånd utan väg ut; steget avancerar inte |
| `F6` | Timing | `TID_FORDUBBLAD`, `TIMER_FORVAL_ANDRAS` | För kort uppehåll, för tidig start, ändrat förval |
| `F7` | Kapplöpning | `FLANK_TAVLAR` | Ordningskapplöpning inom samma scan |
| `F8` | Förregling | `AND_TILL_OR`, `OR_TILL_AND`, `NOT_STRUKEN`, `SANT_TILL_FALSKT`, `FALSKT_TILL_SANT`, `KVARHALLEN_UTGANG_STOPP`, `LARM_KVITTERAT_UTAN_ORSAK` | Saknad eller felaktig förregling; kvarhållen spänning |
| `F15` | Flank och latch | `FLANK_TILL_NIVA`, `FLANK_STRUKEN`, `RETENTIV_FORLORAD` | Nivå i stället för flank; förlorat tillståndsminne |

De resterande sju klasserna i specifikationen kan per konstruktion inte framkallas
ur ST-källkod, eftersom de beskriver omvärldsfaktorer och verktygsarkitektur:
* `F3 (Fel tagg)`: Tillhör signalkartan och I/O-mappningen (grind 3), inte källkoden.
* `F9 (Geometri)`, `F10 (Grepp)`, `F11 (Genomflöde)`, `F12 (Ohederlig)`: Fysikaliska
  effekter i Visual Components 3D-simulering som döms av ögat (`OGAT`), inte av koden.
* `F13 (Verktygsfel)`: Språkmodellens anrop i samtalsloopen.
* `F14 (Annat)`: Slaskklass som enligt sorteringsregel 3 ska hållas nära noll.

### §2 Kalibrering mot repots egna uppmätta haverier

Samtliga större PLC- och tolkfel som dokumenterats i projektets egna mätningar
reproduceras av en specifik skadesort:

| Mätning | Verklig bugg i repot | Motsvarande skadesort |
|---|---|---|
| `M-40` | Matningen fyrade aldrig p.g.a. tyst felaktigt förreglingsvillkor | `AND_TILL_OR`, `NOT_STRUKEN` |
| `M-54` | Kod som kompilatorn avvisade godkändes tyst av tolken | `TID_OGILTIG`, `SEMIKOLON_STRUKET` |
| `M-79` | Dubbelskrivning i referensens logik gav kvarhållen utgång | `KVARHALLEN_UTGANG_STOPP` |
| `M-106` | Dubbelflank på samma signal i samma scan läste uppdaterade värdet tyst | `FLANK_TAVLAR`, `FLANKENS_Q_TILL_SIGNAL` |
| `M-115` | Flank lästes på nivå; I/O-spåret blint vid enskott | `FLANK_TILL_NIVA` |
| `M-121` | Dubbelskrivning och typfel i referenslösningarna | `FALSKT_TILL_SANT`, `TID_OGILTIG` |

### §3 Slutsats

Mutationsmotorn mäter inte godtyckliga strängmanipulationer:
Den spänner 100 % av projektets koddefinierade felklasser (`F1`, `F2`, `F4`,
`F5`, `F6`, `F7`, `F8`, `F15`) och har direkt provats mot de sex verkliga
styr- och tolkhaverier som kostat projektet mest tid.

## LIMITS

* **Kalibreringen är kvalitativ på felklassnivå.** Att motorn kan framkalla
  ett fel ur klass `F7` innebär inte att alla tänkbara kapplöpningar i en PLC
  täcks — det visar att mekanismen för klassen finns och verifierats.
* **Fysiska fel (F9–F12) kräver scen och öga.** En ST-motor kan aldrig
  ersätta ögat för att upptäcka en tappad detalj eller kollision — den kan
  bara verifiera att signalerna som donet styrs med följer kontraktet.
