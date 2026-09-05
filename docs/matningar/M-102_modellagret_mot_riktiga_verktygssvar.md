# M-102 — modellagret mätt mot riktiga verktygssvar

**Datum:** 2026-09-05
**Status:** PÅGÅENDE — numret är reserverat i skrivögonblicket, talen fylls i när
svepet är kört.
**Prövar:** `svc/vc_assist_svc/llm/` (kontextbudgeten, verktygssvarets kapning,
ögontrimningen, turens tillståndsmaskin) mot repots **egna** verktygssvar och
mot harnessens riktiga tur.

## Varför

`23_llm_granssnitt.md`, `24_samtalsloopen.md` och `25_kontextbudget.md` är
1 292 rader spec utan en fas som bygger dem — samma form som fas 16 hade innan
den fick en. Talen i specarna är dessutom från en tidpunkt då registret bar 21
verktyg.

## LIMITS

* **Mätningen är inte klar.** Ingenting nedanför den här raden är ännu ett tal.
* Ingen språkmodell och ingen leverantör är anropad. Allt mäts mot repots egna
  data och mot en attrapp med manus.
* Ingen brygga och ingen VC är igång. Verktygssvaren kommer ur de handlare som
  svarar utan brygga; de kodgenererande verktygens svarsform kommer ur deras
  **deklarerade** `returns`, inte ur en körning.
* Tokenräkningen är en omräkning ur byte, inte en leverantörs tokenisering.
