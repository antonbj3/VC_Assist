# Tröskelskuld — konstanter utan härkomst

Mätt 2026-09-04. Varje tal här är en konstant som styr en dom utan att namnge
vad som satte den. `41_ogat_kontrakt.md` kallar det ett linterfel, och det är
det — men lintern täckte bara en modul av tolv, så skulden var osynlig.

Listan är en **spärr som bara får gå åt ett håll.** Testet
`tests/enhet/test_troskelharkomst.py` läser talet nedan och faller om det
verkliga antalet är högre. Blir det lägre faller testet också, med
uppmaningen att skriva ned det nya talet — annars ruttnar spärren.

## Nuvarande skuld

    UTAN_HARKOMST = 58

Av 125 tröskelkonstanter i `ext/`, `svc/` och `bank/`.

## Varför den inte nollas i ett svep

Att klistra på en hänvisning som inte betyder något vore precis det fel
mätningen hittade. Varje tal ska antingen få en riktig mätning, ett reserverat
nummer i `RESERVERADE.md`, eller strykas för att det inte styr någon dom.

## Ordning

1. `ext/vc_addon/vc_assist/` — koden som kör inne i VC och som ögat dömer med
2. `svc/vc_assist_svc/plc/` — grind 3 och signalkartan
3. `svc/vc_assist_svc/layout/` — väntar på M-30
4. resten
