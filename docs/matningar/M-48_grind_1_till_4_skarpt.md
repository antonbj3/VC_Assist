# M-48 — grind 1–4 körda skarpt, och tre ställen där vår grind är strängare än kompilatorn

**Datum:** 2026-09-04 · STruC++ 0.6.6 (CLI) · API-index ur `vc_python_api.json`
**Fas:** 7, första halvan. Ögat ingår inte — det kräver att något flödar i
scenen, och det står öppet i M-34.
**Körs av:** `tests/protocol/kor_fas7_grindar.py`

## Vad som mättes

En stationskandidat — en press med givare, skyddad ljusridå och don — genom
grind 1 till 4 med **riktig kompilator och riktigt API-index**, ingen attrapp.
Plus tre av protokollets trasiga fall.

```
  HEL  passerade alla fyra
  T1   tagg utanfor kartan          falls
  T2   skrivning till skyddad       falls
  T7   tom kropp                    falls
```

## Vilken grind som faktiskt fäller vad

Protokollet `tests/protocol/fas7_stationen.md` gissade en grind per fall. Mätt
utfall är rikare, och på två punkter ett annat:

| Fall | Protokollet sa | Mätt |
|---|---|---|
| T1 tagg utanför kartan | grind 3 | **tre grindar**: grind 2 `ODEKLARERAD`, grind 3 `ORORD_SIGNAL`, och kompilatorn `Undeclared variable 'HITTEPA'` (kod 1) |
| T2 skrivning till skyddad | grind 2 | grind 2 `SAKERHET` och grind 3 `SKRIVEN_INGANG`. **Kompilatorn godkänner den.** |
| T7 tom kropp | *facit, inte grind 1–4* | grind 2 `SYNTAX` och grind 3 `OLASLIG`. **Kompilatorn godkänner den.** |

Två saker att läsa ur tabellen:

**Säkerhetsgränsen är helt vår.** T2 kompilerar utan anmärkning. Ingen extern
kontroll skulle ha sett den; om vår grind 2 inte hade funnits vore skrivningen
till ljusridån osynlig ända fram till ögat.

**T7-raden i protokollet var fel, och rättas.** Jag skrev att en tom kropp
måste fällas av facit eftersom den kompilerar. Den kompilerar mycket riktigt —
men den fälls ändå av grind 3, av ett skäl jag inte hade tänkt på: kartan
deklarerar signaler, och en kropp som inte rör dem får `ORORD_SIGNAL`. En tom
kropp är alltså inte osynlig för förgrindarna. Med en tom sträng som kropp blir
det just `ORORD_SIGNAL` två gånger; med ett ensamt `;` blir det `SYNTAX`.

Det ändrar inte att facit behöver en nollpunkt. Det ändrar var nollpunkten
ligger: den provar inte om en tom kropp kan passera, utan om ett program som
*rör* alla signaler men inte gör något meningsfullt kan passera.

## Kompilatorns beteende, mätt

| Fråga | Svar |
|---|---|
| Utgångskod vid lyckad kompilering | **0** |
| Utgångskod vid fel | **1** |
| Skrivs en utdatafil när den faller? | **nej** |

Utgångskoden är alltså läsbar och texten behöver inte tolkas. Det är värt att
skriva ned, därför att alternativet — att leta efter ordet "failed" i utdatan —
hade varit en grind som tolkar om observatörens svar (I1).

*(Mätfel av mig på vägen: första körningen läste `$?` efter ett rör och fick
`head`:s status, inte kompilatorns. Talet såg ut att vara 0 i båda fallen.
Mät mätmetoden innan du drar slutsatsen.)*

## Tre ställen där vårt ST-lager är strängare än STruC++

Ett svep över fjorton konstruktioner, var och en körd genom både vår `validera`
och den riktiga kompilatorn:

| Konstruktion | Vårt ST-lager | STruC++ |
|---|---|---|
| `;` ensamt | OLÄSLIG | OK |
| **`END_IF` utan avslutande `;`** | **OLÄSLIG** | **OK** |
| **`T#1s` jämförd mot `TIME()`** | **`OKANT_NAMN`** | **OK** |
| övriga elva (IF, CASE, WHILE, REPEAT, FOR, EXIT, hex, typad literal, kommentar, tom, tilldelning) | OK | OK |

**Tre av fjorton avviker**, och två av dem är ett riktigt problem.

`END_IF` utan semikolon och `TIME()` är båda sådant en modell rimligen skriver.
Vår grind skulle avvisa dem, modellen skulle få tillbaka ett fel som inte finns,
och reparationsslingan skulle brinna varv på att laga något som redan
fungerade. En falsk rödgrind är inte harmlös: den är dyr och den lär modellen
fel sak.

Det ensamma `;` är den ofarliga av de tre — IEC 61131-3 har ingen tom sats, så
vår stränghet är där troligen den rätta och kompilatorns tillåtande hållning
den lösa.

**Detta är inte lagat i den här mätningen.** Det är mätt, avgränsat och
namngivet, och lagningen hör till ST-lagret.

*Efterskrift (M-51):* fjorton var ett stickprov. Svepet över 185
konstruktioner hittade **55 avvikelser**, och de två riktiga felen här visade
sig vara klasser: `END_IF` utan semikolon var sju fall, `TIME()` var
trettiotvå saknade standardfunktioner. 36 är lagade. Det ensamma `;` står
kvar strängt, men av ett annat skäl än raden ovan ger — IEC 61131-3:s
satslista tillåter läst bokstavligt en tom sats. Se
`docs/matningar/M-51_svepet_over_st_lagret.md`.

## Grind 4 och regeln om noll namn

Första körningen rapporterade `granskningen kontrollerade noll namn` för
scenkoden, och fällde. Det var **rätt fällning på en verklig orsak**: min
scenkod var rotad i ett fritt `app`, och validatorn kan inte typa ett fritt
namn. Verktygsmallarna skriver aldrig så — de anropar `getApplication()` inline
(`verktyg/transport.py:164`). Med den formen kontrolleras **tre namn**, och ett
uppfunnet metodnamn ger **ett fel**.

Regeln infördes som en principsak — en grind som blir billig slutar mäta sin
egen storhet — och fångade en verklig blindfläck första gången den kördes.
Utan den hade grind 4 svarat GODKÄND på kod den inte hade tittat på.

## Vad som INTE är mätt

* **Ögat.** Grind 5 ingår inte. T3–T6 i protokollet kan inte prövas förrän
  något flödar i scenen (M-34).
* **Driftsättning.** CLI-vägen svarar bara på *går den att bygga?*. Den skriver
  varken `generated_debug.cpp` eller `debug-map.json`, och båda behövs för att
  ladda koden i OpenPLC.
* **Reproducerbarhet.** STruC++ ligger i en sessionskatalog, inte i repot, och
  npm-paketet som `paket.kompilera` kräver finns inte längre på maskinen. Grind
  1 går alltså att köra här och nu, men inte på en ren maskin utifrån repots
  egna instruktioner. Det är en skuld mot fas 10 och den är inte betald.
* **Flera stationer.** En station, tre trasiga fall.
