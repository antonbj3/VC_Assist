# M-124 — OpenPLC som tredje motor (kö A, punkt A1)

**Datum:** 2026-09-05
**Status:** PÅGÅENDE (reserverad)
**Körs av:** `tests/protocol/kor_A1_tredje_motorn.py` (planerad)
**Facit:** OpenPLC Runtime v4 (beteende) + matiec (typ) + IEC 61131-3 vid oenighet
**Prövar:** `svc/vc_assist_svc/st/` mot STruC++ 0.6.6, OpenPLC v4.2.1, matiec 0.1

## Frågan

M-99:s 490 konstruktioner genom OpenPLC:s runtime, trevägs (tolk, STruC++,
OpenPLC) plus matiec som typorakel. Utfall 3 — alla accepterar texten men
OpenPLC *beter sig* annorlunda — kräver körning, inte kompilering.

## Utfall

Ej mätt ännu.

## LIMITS

* **Inget i denna mätning är ännu mätt.** Filen är en reservation.
* **Facit är OpenPLC v4 + matiec i Docker, inte fysisk hårdvara.**
