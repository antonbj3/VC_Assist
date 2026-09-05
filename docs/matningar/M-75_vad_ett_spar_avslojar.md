# M-75 — vad ett I/O-spår avslöjar om programmet det kom ur

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_m75_vad_ett_spar_avslojar.py`
**Gäller:** fas 18 i `docs/spec/70_faser.md`

## Varför mätningen behövdes

Fas 18 vilar på en premiss: ett inspelat I/O-spår från en körande linje har
redan bankens facitform, så en modell kan skriva ST som återger det. Fasen bär
fyra ärlighetskrav — men alla fyra var **hypoteser**. De var resonerade, inte
mätta.

Här kan de mätas, för vi har fall där svaret är känt: bankens uppgifter har både
en **referenslösning** och ett **spårfacit**. Vi kan alltså köra det kända
programmet, spela in spåret, och fråga vad spåret avslöjar om programmet det kom
ur.

Det är samma sak som en anläggning ger, med en avgörande skillnad: här vet vi
facit, så vi kan mäta vad som **inte** syns.

## Talen

| Uppgift | spårrader | signaler | lägen i steg­variabeln | IF | CASE | **villkorsgrenar** | rader per gren |
|---|---:|---:|---:|---:|---:|---:|---:|
| T-07 | 65 | 12 | 4 | 10 | 1 | **16** | 4,1 |
| H-04 | 68 | 20 | 9 | 14 | 1 | **25** | 2,7 |
| S-05 | 174 | 8 | **17** | 20 | 1 | **66** | 2,6 |
| L-05 | 98 | 17 | 5 | 10 | 1 | **17** | 5,8 |

**Programmets eget inre syns aldrig i spåret.** Stegvariabeln, de 16–66
villkorsgrenarna, timrarnas ackumulatorer — allt det är osynligt. En anläggning
ger sina kontaktdon och ingenting annat.

## Det avgörande talet: rader per gren

**Under sex spårrader per villkorsgren**, och för de två svåraste under tre.

Och detta är **bästa fallet**. Bankens spårfacit är *designat* för att pröva
logiken — åtta sekvenser som medvetet går igenom kallstart, larm, kvittens,
tidsövervakning och återstart. En verklig anläggning kör mest normalproduktion.
Ett dygns spår därifrån ger tusentals rader ur **samma** gren och noll ur de
andra.

Fas 18:s första krav sa: *"Ett spår visar bara vad som hände."* Talen ovan säger
hur lite det är, även när någon har ansträngt sig för att få med allt.

## Signaler som aldrig rör sig

| Uppgift | tysta signaler |
|---|---|
| T-07 | 1 av 12 — `SYS_AUTO` |
| H-04 | 2 av 20 — `AIR_OK`, `SYS_AUTO` |
| S-05 | 0 av 8 |
| L-05 | 1 av 17 — `AIR_OK` |

`SYS_AUTO` är automatlägesväljaren — den grindar **hela** stationen. I T-07 och
H-04 stod den still genom hela spåret. En rekonstruktion ur det spåret skulle
inte kunna veta att den finns i logiken alls, och det programmet skulle köra
lika glatt i handläge.

En signal som står still säger ingenting om vad den styr.

## Säkerhetsförreglingen syns nästan inte, i alla fyra

`EMG_OK` bytte värde **högst två gånger** i **var och en** av de fyra
uppgifterna. Detsamma gäller `AIR_OK`.

Det är inte en tillfällighet: en nödstoppskrets *ska* ligga sluten. Den bryter
när något är fel, och det händer sällan. Följden är att spåret bär n = 1 eller
n = 2 observationer av precis den signal som är farligast att gissa om.

Fas 18:s fjärde krav — **säkerhetsfunktioner rekonstrueras aldrig ur ett spår** —
stod som en principregel. Den är nu också en **datafråga**: datan finns inte
där.

## Vad detta betyder för fas 18

De fyra kraven står kvar, och två av dem är nu mätta i stället för resonerade:

1. *Ett spår visar bara vad som hände.* **Mätt**: under sex rader per gren, i
   ett facit som var byggt för att pröva logiken.
2. *Tider är observerade, inte specificerade.* **Mätt**: 2–4 utgångar per
   uppgift har högst två byten, alltså n = 1 puls.
3. *Korrelation är inte orsak.* Inte mätt här.
4. *Säkerhetsfunktioner rekonstrueras aldrig.* **Mätt**: `EMG_OK` ger n ≤ 2 i
   alla fyra.

Grinden i fas 18 måste därför räkna **täckning per gren**, inte per signal, och
vägra påstå något om en gren som spåret aldrig besökte.

## Vad som INTE är mätt

* **Bara fyra uppgifter**, och alla fyra är våra egna. En riktig anläggnings
  spår är inte mätt alls — vi har inget.
* **Grenräkningen är statisk.** Den räknar grenar i källan, inte vilka som
  **kördes**. Att mäta det kräver en instrumenterad tolk, och den finns inte.
  Talet "rader per gren" är alltså en övre gräns för hur mycket varje gren kan
  ha observerats, inte en mätning av täckning.
* **Ingen rekonstruktion är försökt.** Mätningen säger vad spåret innehåller,
  inte hur väl en modell skulle klara att skriva om programmet ur det. Det är
  nästa mätning.
* **Inre tillstånd räknas ur ett regex** över referensens `steg`-tilldelningar
  och CASE-etiketter. En stegvariabel med ett annat namn skulle inte hittas, och
  talet vore då noll — som skulle se ut som "programmet har inget inre".
