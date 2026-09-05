# M-108 — OpenPLC som tredje motor

**Datum:** 2026-09-05
**Status:** PÅGÅENDE (reserverad, steg 0)
**Körs av:** `tests/protocol/kor_openplc_*.py` (planerad, finns ej ännu)
**Facit:** OpenPLC Runtime v4 (`ghcr.io/autonomy-logic/openplc-runtime`, digest låst i `install/verktygskedjan.py`) + IEC 61131-3 vid oenighet
**Prövar:** `svc/vc_assist_svc/plc/openplc.py`, `svc/vc_assist_svc/plc/paket.py` mot `svc/vc_assist_svc/st/` (tolk) och STruC++ 0.6.6

## Frågan

Kedjan är `ST → STruC++ → OpenPLC v4 → OPC UA → VC`. Två led är korsprövade
(247 permanenta fall i `tests/enhet/test_st_svep_mot_strucpp.py`, M-99). Det tredje
ledet — det som faktiskt kör i produkten — är oprövat. Uppdraget kör de 247 fallen
genom OpenPLC, klassar utfallen (STRÄNGARE / FALSK RÖDGRIND / HÅL) och jämför
scan för scan, inte bara kompilering (TON `PT := T#4s` ska lösa på samma scan).

## Grindar för steg 1 (skärpta 2026-09-05)

* **Klart =** en variabel läst tillbaka över OPC UA med **ändrat värde**.
  Container igång eller program laddat räcker inte.
* **30 min:** startar inte containern → byt spår direkt.
* **2 h:** hårt stopp oavsett hur nära.
* Vad som än stoppar skrivs i denna mätning innan bytet.

## Steg 1 — utfall (2026-09-05, KLART)

Egen behållare `vcassist-openplc-m108` (`ghcr.io/autonomy-logic/openplc-runtime:latest`,
`127.0.0.1:18444:8443`, `127.0.0.1:14841:4840`, IP `172.17.0.3`) — den delade
`vcassist-openplc-v4` (ST8-lina, annan sessions program) rördes inte.

Kedja körd med `svc/vc_assist_svc/plc/matning.kor` (serier=1, per_serie=5):
grind 3 grön → STruC++ 0.6.6 via `strucpp_bygg.mjs` (4 artefakter) → REST-upload →
`SUCCESS` → `RUNNING` → OPC UA `opc.tcp://172.17.0.3:4840/openplc/opcua`.

| mått | värde |
|---|---|
| runtime | v4.2.1, `RUNNING` |
| golv (1 läsning, n=200) | median 0,26 ms |
| tur och retur (n=5) | median 39,76 ms, min 37,00, max 40,27 |
| förväntat (M-20, 2 scan à 20 ms) | 40,0 ms |

Slutkriteriet uppfyllt: utsignalen följde insignalen i 5/5 mätningar —
variablerna ändrades, inte bara startade. Talet stämmer med M-20 (40,0 ms).

## Steg 2 — 247 fallen genom OpenPLC (2026-09-05, KLART)

Kört av `tests/protocol/kor_openplc_svepet.py` mot egen behållare
(`vcassist-openplc-m108`, v4.2.1). Lager A lokalt (validera + compile-API,
247 fall på 38 s), lager B som 215 uppladdningar i tre delmängder
(0/3, 1/3, 2/3 — commit efter varje). Trasig fixtur: saboterad C++ gav
FAILED som väntat (`--trasig-fixtur` grön).

| klass | antal | innebörd |
|---|---:|---|
| OVERENS | 195 | vi och OpenPLC säger samma sak (varav 8 där backend avvisar det frontenden släpper — se steg 3) |
| STRANGARE_BEKRAFTAD | 19 | vi fäller, OpenPLC accepterar, raden finns i STRANGARE |
| NYTT_HAL | 1 | `concat` — vi släpper, OpenPLC vägrar |
| TVAFALL | 23 | båda motor 1+2 avvisar, inget att ladda upp (ingen utebliven körning) |
| LATTARE_OPROVAD | 9 | frontenden avvisar före backend; runtimens dom entailed, inte mätt |
| EJ_KORD | 0 | — |

STRANGARE_BEKRAFTAD (19): bool_far_int, case_utan_grenar, datum_literal,
dekl_faltinitiering, dekl_faltinitiering_upprepning, dint_far_lint,
index_utanfor_granser, int_far_real, jamfor_bool_med_int, literal_over_int,
pou_tom_kropp_i_funktion, sats_tom_gren_i_case, tal_int_over_omradet_negativt,
tid_decimal_i_fel_del, tid_dubbel_enhet, tid_fel_ordning,
tid_pa_dagen_literal, tom_sats_semikolon, uttryck_kedjetilldelning.
Bland dem båda R1-formerna för fältinitiering (`[1,2,3]`, `[3(0)]`):
koden bygger och kör i OpenPLC — bekräftat att det är vår begränsning,
inte kedjans. Modellvägskostnaden förblir noll (skelettet släpper inga
fält), så R1-frågan står kvar oförändrad.

## Steg 3 — skiljedom (2026-09-05)

**`concat`: NYTT_HAL, standarden ger oss rätt.** `sA := CONCAT('a','b')`
passerar vårt lager och STruC++:s frontend (svepet: OVERENS), men OpenPLC:s
backend faller: `mismatched types 'const IECString<MaxLen>' and
'const char [2]'` — mallhärledning kräver minst ett IECString-argument.
Enkeltciterade literaler är giltiga STRING i IEC 61131-3 och CONCAT tar
STRING, så koden är giltig; felet är en STruC++-backendbegränsning
(samma familj som LATTARE, men upptäckt först i runtimebygget).
Avgränsning mätt samma dag: `CONCAT(sA,'b')` och `CONCAT('a',sA)` bygger
(SUCCESS) — bara literal–literal faller. Allvarligt därför att grind 1
bara kör frontenden (stationsgrind.py: CLI eller compile-API, aldrig g++):
hålet passerar alla grindar och felar först i scenen.

**8 STRANGARE-rader: frontenden tiger, backend faller.** okant_argumentnamn,
okant_falt_pa_block, blocktyp_anropad_direkt, blockinstans_i_uttryck,
exit_utanfor_slinga, strang_over_radbrytning, dekl_falt_omvand_grans
(`std::array<..., 18446744073709551608>` — omvända gränser blir
2^64-skalig array i C++), pou_konfigurationsblock (enkel CONFIGURATION
utan min dubblett faller också — ingen harnessartefakt). Vårt avvisande
står (fail-closed korrekt: koden kan inte köra), men M-99-tabellens
motivering "kompilatorn accepterar" behöver fotnoten "frontenden —
backend avvisar". Ingen åtgärd i vårt lager.

**BENCH-4-not under arbetet:** `kor_openplc_svepet.py` deklarerade först
facit genom `plc/openplc.py` — samma modul som stod i `under_prov`.
Lagat: `under_prov` är `st/`, kanalen är harness, facitkällan är det
externa programmet (tom `facitkalla_filer`). Se `docs/spec/85_bankkontraktet.md` §2.

## Steg 4 — scan för scan (2026-09-05, KLART)

Kört av `tests/protocol/kor_openplc_scan.py` (5 program, egen behållare).
Tolkens cykel 20.0 ms bekräftad lika före körning.

| program | tolken | OpenPLC (3 rep) | dom |
|---|---|---|---|
| SCAN_GENOM, 4 vippor | u följer g | 35–42 ms per följd, 4/4 | överens |
| SCAN_TON4S, PT=T#4s | trigg scan 200 | 202, 202, 202 | överens (se kanalnot) |
| SCAN_TON1S, PT=T#1s | trigg scan 50 | 52, 52, 52 | överens (se kanalnot) |
| SCAN_TON20MS, PT=T#20ms | trigg scan 1 | 3, 3, 3 | överens (se kanalnot) |
| SCAN_RTRIG, 60 ms puls | exakt 1 hög scan | 3–4 höga avläsningar à 5 ms (≈1 scan) | överens |

**Kanalnot (mätningen som bär "samma scan"):** Δ +2 scan är konstant över
1/50/200 scans horisont (3 rep vardera). En logikförskjutning hade skalat
eller varit noll; ett konstant +2 oberoende av PT är skriv→tabell (≤1,
plugin-synk 10 ms) + tabell→läsning (≤1 + 5 ms poll). Timerns logik löser
på samma scan (200=200); kanalen lägger 2 scan fas. Nio mätningar, noll
undantag.

## LIMITS

* **Facit är OpenPLC v4 i Docker, inte fysisk PLC-hårdvara.** Fältbussjitter och hårdvaru-I/O ingår inte.
* **Tidsupplösning 20 ms.** Timers under en scancykel prövas inte.
* **TVAFALL (23) och LATTARE_OPROVAD (9) vilar på entailment, inte mätning.** Samma frontend i kedjan och i runtimen; backend kan bara avvisa det frontenden redan avvisat. Logiskt tätt, men ingen uppladdning.
* **Kanalen kan själv fela — redan demonstrerat en gång.** `icke_ascii` fastnar i `paket.kompilera`:s ascii-mur före kompilatorn (svepets CLI säger True). Ett kanalstop ser ut som motoroenighet om man inte läser skalet.
* **Scan-jämförelsen mäter logik + 2 scan kanalfas.** "Samma scan" gäller timerns logik; det avlästa talet är +2 (tre PT-horisonter som referens).
* **Enprogramsbehållare, två signaler, Linux, anonym OPC UA.** Hundra taggar, certifikat, Windows och VC-scen ingår inte.
* **Den delade ST8-behållaren rördes aldrig.** Alla M-108-körningar gick mot `vcassist-openplc-m108` (18444/14841); ST8-linan lämnades åt sin ägare.
* **IEC-citatet för CONCAT är kvalitativt.** Exakt tabellnummer i 61131-3 är inte verifierat mot standardtext — stdbibliotekets egen signatur (`=IN1`, variadisk STRING) är den kontrollerade referensen.
