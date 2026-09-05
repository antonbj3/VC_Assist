# M-105 — ett mönster som aldrig körts mot texten det ska läsa

**Status: RESERVERAD 2026-09-05.** Numret är taget i skrivögonblicket för att
två agenter inte ska skriva samma M-nummer. Mätningen pågår.

## Frågan

Tre fel på en natt hade samma form: en matchare som aldrig körts mot texten
den ska läsa. `skuld.py:_ARLIGHET` var ASCII mot svensk text (M-70),
`st/lexer.py:_TIDSDEL` saknade `re.I` (M-96), `harness/text.py:NEKANDE` är en
ordlista som fyrar på fel storhet (M-94 fynd 1). Hur många fler finns?

## LIMITS

* Ingenting är mätt ännu. Talen nedan skrivs när mätningen är körd.
