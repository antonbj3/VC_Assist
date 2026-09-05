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

## Utfall

Ej mätt ännu. Fylls i per delmängd av svepet (committa inkrementellt).

## LIMITS

* **Inget i denna mätning är ännu mätt.** Filen är en reservation; alla tal ovan är plan, inte resultat.
* **Facit är OpenPLC v4 i Docker, inte fysisk PLC-hårdvara.** Fältbussjitter och hårdvaru-I/O ingår inte.
* **Tidsupplösning 20 ms.** Timers under en scancykel prövas inte.
