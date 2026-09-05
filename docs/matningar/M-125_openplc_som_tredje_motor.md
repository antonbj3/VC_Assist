# M-125 — OpenPLC som tredje motor (kö A, punkt A1)

**Datum:** 2026-09-05
**Status:** KLART (steg 1: typdom + beteende; bankdomare = A2)
**Körs av:** `tests/protocol/kor_A1_beteende.py` (81 fall, exit 1 = 22 divergerar),
  `tests/enhet/test_plc_matiec.py` (33 prov), matiec-klient
  `svc/vc_assist_svc/plc/matiec.py`
**Facit:** OpenPLC Runtime v4.2.1 (beteende) + matiec 0.1 (typ) + IEC 61131-3
  vid oenighet
**Prövar:** `svc/vc_assist_svc/st/` mot STruC++ 0.6.6, OpenPLC v4.2.1, matiec 0.1

## Frågan

M-99:s konstruktioner genom OpenPLC:s runtime, trevägs (tolk, STruC++,
OpenPLC) plus matiec som typorakel. Utfall 3 — alla accepterar texten men
OpenPLC *beter sig* annorlunda — kräver körning, inte kompilering.

## Typdom: validatorn mot matiec (48 fall)

Metod: varje fall ett komplett `PROGRAM` med en sats, genom
`vc_assist_svc.st.validera` och `iec2c -f` (strikt läge, domen ur
felsträngarna, aldrig ur rc). Klient: `svc/vc_assist_svc/plc/matiec.py`
(sökordning `$VC_ASSIST_MATIEC`, `/tmp/opencode/matiec/iec2c`, extraktion
ur `wzy318/openplc:latest`; timeout, fail-closed). Grön svit
`tests/enhet/test_plc_matiec.py` 33 passed (trasig fixtur: `4.0 * antal`
fälls, `INT_TO_REAL`-formen passerar).

Utfall: OVERENS 28/48 (23 båda fäller, 5 båda släpper), MATIEC_STRANGARE
18/48, VI_STRANGARE 2/48.

Läckan (vi släpper, matiec fäller), exakt kod + matiecs meddelande:

| fall | kod | matiec svarar |
|---|---|---|
| DINT×INT `*,+,-,/` | `dA := dB * iA;` (INT/DINT) | `Data type mismatch for '*' …` (+,-,/ lika) |
| INT×REAL `+,-,/` | `rA := iA + rB;` | `Data type mismatch for '+' …` (-,/ lika) |
| LREAL×INT `+` | `lrA := lrB + iA;` | `Data type mismatch for '+' …` |
| INT<DINT `<` | `bA := iA < dA;` | `Data type mismatch for '<' …` |
| ADD/MAX/LIMIT blandat | `rA := ADD(iA, rB);` | `Unable to resolve which overloaded function 'ADD' …` (MAX/LIMIT lika) |
| INT/INT→REAL `:=` | `rA := iA / iB;` | `Incompatible data types for ':=' operation.` |
| SINT→INT, UINT→DINT | `iA := sA;` / `dA := uA;` | `Incompatible data types for ':=' operation.` |
| INT→LREAL, REAL→LREAL | `lrA := iA;` / `lrA := rA;` | `Incompatible data types for ':=' operation.` |
| ABS(INT)→REAL | `rA := ABS(iA);` | `Incompatible data types for ':=' operation.` |

Mönster: vår vidgning (INT→DINT/REAL/LREAL, UINT→DINT, REAL→LREAL,
`GEM`/`=IN`) släpper det matiec — identiska aktualtyper, ingen implicit
vidgning — fäller. IEC 61131-3:2003 §2.5.1.4 bär de generiska fallen
(samma aktualtyp krävs, konvertera uttryckligen — jfr M-121 §T-04); för de
rena `:=`-fallen är paragraf oprovad. Säker riktning (vi strängare, 2 fall):
`b := 1` och `i := TRUNC(r)` fälls av oss, släpps av matiec — grinden står
kvar tills kedjan mätts enhetligt.

## Beteende (utfall 3): tolk mot OpenPLC-körning

Skript `tests/protocol/kor_A1_beteende.py`: 81 konstruktioner, var och en
enskilt STruC++-kompilerad med egen mappad I/O, samma stimuli i tolk och
OpenPLC, kanarie + kanalkontroll per program. Egen verifiering: ett fullt
varv ger identiskt utfall (rc=1): **54 LIKA, 5 NÄRA, 22 DIVERGERAR**.

Trasig fixtur först (sågs RÖD före systematisering):
`o := REAL_TO_INT(1.5)` — tolken 1 (trunkering), OpenPLC 2 (`std::round`).

| familj | fall | tolk | OpenPLC | rätt |
|---|---|---|---|---|
| avrundning REAL→INT | c01–c05, c08–c10, c14, c23, i03 (`REAL_TO_INT/DINT`, `LREAL_TO_INT`) | trunkerar (1.5→1) | avrundar half-away (1.5→2) | OpenPLC; oprövad paragraf |
| bredd/svep | a09 `2147483647+1`→2147483648 | obegränsad Python-int | −2147483648 (svep) | OpenPLC (tabell 10); svep oprövad |
| | a10 `32767+1`, a22 min−1, a11 `100000·100000`→1410065408, a12 BYTE 255+1→0, i02, c16 `DINT_TO_INT(70000)`→4464 | dito | svep på vidden | dito |
| | b07 `NOT 16#00FF`→−256 | ingen breddmask | 65280 | OpenPLC (tabell 10) |
| | t07 `TIME_TO_DINT(T#100d)`→8640000000 | dito | 50065408 (int32-ms svep) | oprövad paragraf |
| mättnad | c24 `REAL_TO_INT(16777216.0)`→16777216 | dito | **32767** (mättar, wrapar inte) | oprövad paragraf |
| float32 | c25 `REAL_TO_DINT(16777217.0)`→16777217 | dito | 16777216 (REAL är 32 bit) | OpenPLC (tabell 10) |
| NÄRA ×5 | a03/a14/a16/a20/a21 (REAL-råvärden, diff ≤1e-6) | — | float32/float64-bredd | OpenPLC (tabell 10) |

Bevarade hypotesfel (förväntat formulerat före körning, fick annat):
c13 LIKA (STruC++ räknar literalen i double före smalning),
c24 (mättnad i stället för väntat svep), a02 (FALSE=FALSE).
MOD/heltalsdivision med negativa (a04–a08): LIKA — ingen divergens.
`1.0/3.0*3.0`: LIKA 1.0 — kandidat som inte divergerade.

## LIMITS

* Facit är OpenPLC v4.2.1 + matiec 0.1 i Docker, inte fysisk hårdvara;
  REAL = float32, TIME = int32 ms (båda mätta genom divergens, ej ur dokument).
* Grinden läcker 18/48 typfel som kedjan fäller — skicka inga blandade
  ANY_NUM-uttryck eller `:=`-vidgningar utan `X_TO_Y`-konvertering.
* Avrundning REAL→INT, svepsemantik och float→int-mättnad är oprövade
  paragrafer i repot (tabell 10 bär vidden, inte beteendet).
* Tolken kan inte köra SHL/SHR/ROL/ROR, MUX, EXPT(), CONCAT/LEFT/RIGHT/MID
  (Tolkfel) — ej prövade på utfall 3. TIME/STRING mappas inte till
  bildtabellen; prövade endast via BOOL/INT/DINT-sonder.
* 4 uppladdningar för 81 fall delar aldrig tillstånd (en tilldelning per
  utgång ur konstanter/indata, ingen återkoppling). Kört 3× med identiska
  domar; egen verifiering ett varv identiskt.
* TIME-regelns matiec-överensstämmelse är implementationslikhet, inte
  bevisad standardtäckning.
* Behållare `vcassist-openplc-v4` (annan sessions ST8-lina) rördes aldrig;
  allt kördes mot `vcassist-openplc-m108`.
