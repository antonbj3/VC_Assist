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

## Steg 2 — utfall

Ej mätt ännu. Fylls i per delmängd av svepet (committa inkrementellt).

## LIMITS

* **Inget i denna mätning är ännu mätt.** Filen är en reservation; alla tal ovan är plan, inte resultat.
* **Facit är OpenPLC v4 i Docker, inte fysisk PLC-hårdvara.** Fältbussjitter och hårdvaru-I/O ingår inte.
* **Tidsupplösning 20 ms.** Timers under en scancykel prövas inte.
