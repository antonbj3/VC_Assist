# M-99 — differentialsvepet: jakten på fler falska rödgrindar i ST-lagret

**Datum:** 2026-09-05
**Status:** PÅGÅENDE — talen fylls i när svepet är kört.
**Prövar:** `svc/vc_assist_svc/st/` mot STruC++ v0.6.6, axel för axel.

## Varför

`M-96` mätte att nio av sexton grinddomar i fas 9:s första modelldrivna körning
var en falsk rödgrind: `T#3S` avvisades av vårt lager men accepteras av
kompilatorn i vår egen kedja. `M-51` svepte 185 konstruktioner och missade ändå
skiftläge. Den här mätningen frågar vad mer M-51 missade.

## LIMITS

* **Mätningen är inte klar.** Ingenting nedanför den här raden är ännu ett tal.
* Facit är STruC++ v0.6.6, inte standarden och inte OpenPLC.
* STruC++ är ingen namnauktoritet: `HITTEPA(x)` passerar dess främmande.
