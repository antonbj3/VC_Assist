# M-31 — tröskellintern var själv en falsk grön

**Datum:** 2026-09-04
**Funnen av:** motbevisningen (`docs/motbevis_2026_09_04.md`)

## Vad lintern påstod sig göra

`41_ogat_kontrakt.md`: *"En tröskel utan hänvisning är ett linterfel."*
`tests/enhet/test_troskelharkomst.py` skrevs för att hålla den regeln.

## Vad den faktiskt gjorde

| | |
|---|---|
| moduler den läste | **1** av tolv (`oga_analys.py`) |
| konstanter den prövade | **10** av 125 |
| kontrollerade den att M-numret fanns | **nej** — bara att formen `M-\d+` stod där |

## Mätt efter att lintern gjorts om

| Utfall | Antal |
|---|---|
| tröskelkonstanter totalt i `ext/`, `svc/`, `bank/` | **125** |
| med hänvisning till en mätning som **finns** | 19 |
| med hänvisning till en mätning som **inte finns** | **27** |
| utan någon hänvisning alls | **79** |

De döda hänvisningarna: **M-10 fjorton gånger, M-18 åtta, M-19 fem.** Ingen av
de tre existerade. M-10 var mitt eget löfte om ögats kalibrering, skrivet i
fjorton trösklar och aldrig infriat.

## Vad som ändrades

**En reservationsregistrering.** `docs/matningar/RESERVERADE.md` listar nummer
som är utlovade men inte gjorda, med vad de ska mäta och vad som väntar på dem.
En tröskel får peka på ett reserverat nummer — men bara tillsammans med ordet
`PRELIMINÄR`, och det kontrolleras.

**Specen räknas också som härkomst.** En portnummer och en grammatikversion är
inte trösklar; de är beslutade, och beslutet står i ett dokument. Lintern godtar
en referens till `NN_dokument.md` och kontrollerar att filen finns.

**En räknad spärr.** `docs/matningar/TROSKELSKULD.md` bär antalet konstanter
utan härkomst. Testet faller om antalet är **högre** — då har någon lagt till en
tröskel utan härkomst. Det faller också om antalet är **lägre**, med
uppmaningen att skriva ned det nya talet. Annars slutar spärren mäta sin egen
storhet.

**Nolltolerans där det avgörs.** `oga_analys`, `oga_provtagning`, `oga_kontrakt`,
`skrivgrind`, `pump` och `protokoll` får inte ha en enda tröskel utan härkomst.
Resten av trädet betar av sig genom spärren.

Skulden gick från 79 till **67** i samma svep, genom att skriva ut den härkomst
som faktiskt fanns men inte stod utskriven.

## Lärdomen

En grind som bara läser en modul av tolv mäter inte det den påstår. Och en
kontroll av **formen** på en hänvisning är inte en kontroll av att hänvisningen
betyder något — det är samma sorts fel som ett test som läser källkod som text
när det verkliga värdet är något annat.

Lintern hade varit grön i hela projektets livstid.
