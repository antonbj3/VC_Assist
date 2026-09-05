# M-111 — 31 av grind 2:s 68 fällplatser har aldrig fyrat

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_fallplatstackning.py`
**Prövar:** om "ett par per kontroll" är täckning

## Frågan

`tests/enhet/test_st_semantik.py` bär **tolv par** — en källa som faller på en
viss kod och en som går igenom. En adversariell granskning av promptdesignen
invände att det låter som täckning men inte är det, och föreslog att enheten
inte är *kod* utan **fällplats**: det ställe i koden där grinden faktiskt
fäller.

Frågan går att avgöra. Räkna platserna ur källan, spela in vilka som fyrar när
hela enhetssviten körs, och jämför.

## Talen

| | |
|---|---:|
| ställen i `validator.py` där grind 2 kan falla | **68** |
| fyrade minst en gång under hela `tests/enhet` | **37** (54 %) |
| **fyrade aldrig** | **31** |

Fördelat per kod, och den är inte jämn:

| kod | otäckta | av |
|---|---:|---:|
| `TYP` | **22** | 34 |
| `OKANT_NAMN` | 4 | 9 |
| `ARGUMENT` | 2 | 6 |
| `SYNTAX` | 2 | 4 |
| `OATKOMLIG` | 1 | 5 |

**Två tredjedelar av typkontrollen har aldrig körts.** `NOT` mot fel typ,
minustecken mot något som inte är ett tal, `CASE`-etikett med fel typ — inget
prov i sviten har någonsin nått dem.

## Vad det säger om par-designen

Tolv par täcker tolv **koder**. Koderna fördelar sig över 68 platser, och
`TYP` ensam har 34. Ett `TYP`-par provar alltså **en av trettiofyra** och säger
ingenting om de övriga trettiotre.

Par är alltså rätt sorts sak — de kan inte ljuga, för de körs — men fel **enhet**.
Granskarens invändning håller, mätt.

## Varför det är mer än en täckningssiffra

Natten 2026-09-04/05 hittades i samma lager: **sju falska rödgrindar** och fyra
hål (`M-99`), en tidsliteral som avvisade `T#3S` fast kompilatorn accepterar
den (`M-96`), och en `DUBBELSKRIVNING`-grind som bar **motsatsen till sitt eget
fältnamn** — fel åt båda hållen, där den falska gröna släppte igenom precis den
kapplöpning regeln finns för.

**Alla dessa fel satt i platser som FYRAR.** De hittades för att någon körde
dem. De 31 som aldrig fyrar är omätt mark: vi vet inte om de är riktiga, falska
eller döda.

En fällplats som aldrig fyrat är en fällplats ingen provat. Det är samma sak
som `M-105` mätte en nivå ned — av 100 mönster som avgör en dom hade 28 bara
halva sin bevisning och fyra ingen alls — och samma sak som `M-70` fann i
`_ARLIGHET`, där åtta av elva grenar var döda i månader.

## Hur den mäter

Platserna räknas med **AST**, inte med `grep` — en regex över källan hade varit
felklassen själv. Inspelningen lindar `Granskning.fel` och läser anroparens
radnummer ur `sys._getframe(1)`, alltså själva fällplatsen och inte raden i
ST-källan. Sedan körs hela enhetssviten i samma process.

Fail-closed: noll fyrade platser ger slutkod 2. En täckning ur noll
observationer är ingen mätning.

## LIMITS

* **Att en plats fyrar betyder inte att den fyrar RÄTT.** En falsk rödgrind
  fyrar precis som en äkta — `M-99` hittade sju bland dem som fyrar. Talet 37
  är alltså inte 37 prövade platser, bara 37 nådda.
* **Bara `validator.py`.** Lexern och läsaren kastar `Syntaxfel` på egna
  ställen som inte räknas här. Grind 1, 3, 4 och ögat är helt utanför.
* **Bara `tests/enhet`.** En plats som bara nås under en VC-körning eller ett
  STruC++-svep räknas som otäckt, och några av de 31 kan vara det.
* **Ingen spärr satt.** Talet är mätt en gång; det finns inget tak som hindrar
  det från att sjunka. Att sätta ett kräver att man först avgör vilka av de 31
  som är rimliga att nå — 34 `TYP`-platser är inte 34 lika viktiga platser.
* **Ingen av de 31 är undersökt.** Om någon är död kod, om någon är onåbar via
  skelettet, eller om någon bär ett fel — det är inte mätt. Listan står i
  körningens utdata.
