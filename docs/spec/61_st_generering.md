# ST-genereringen

Vad modellen får skriva, vad den aldrig får skriva, och hur resultatet döms
utan att någon människa läser koden.

Detta dokument är det fas 7 byggs mot. Grindkedjan står i `50_grindar.md`,
uppsättningen i `60_plc.md`, modellens gränssnitt i `23_llm_granssnitt.md`.

## Formen: hål i ett skelett, aldrig en fri fil

Modellen får aldrig en tom sida. Den får ett skelett med deklarationerna
ifyllda ur signalkartan och skriver **bara kroppen**.

```
PROGRAM <station>
VAR                          <- genererat ur Signalkarta, aldrig av modellen
  Givare  AT %IX0.0 : BOOL;
  Don     AT %QX0.0 : BOOL;
  Vakt    : TON;
END_VAR
                             <- HÄR, och bara här, skriver modellen
END_PROGRAM
```

Skälet är mekaniskt, inte pedagogiskt. En modell som får skriva deklarationer
kan skriva en tagg som inte finns i scenen, och felet visar sig först som ett
värde som aldrig rör sig — den dyraste sortens fel, eftersom det ser ut som ett
logikfel. Genererade deklarationer tar bort hela felklassen i stället för att be
modellen vara noggrann. Grind 3 (`deklarationsgrind.py`) upprätthåller det:
varje symbol modellen rör måste finnas i kartan.

Följd: **ingen fri ST-fil accepteras**. En leverans som inte går att lägga
tillbaka i sitt skelett avvisas, oavsett hur bra den ser ut.

## Vad modellen får skriva

Sekvensen, timers och förreglingar mellan de deklarerade taggarna.

## Vad modellen aldrig får skriva

| Förbud | Upprätthålls av |
|---|---|
| variabeldeklarationer och taggnamn | skelettet + grind 3 |
| skrivning till en `skyddad` signal | signalkartans märkning, grind 2 (I15) |
| någonting i en säkerhetsfunktion | `50_grindar.md`, säkerhetsgränsen |
| direkt adressering förbi kartan (`%QX` i kroppen) | grind 2 |
| konstruktioner utan mätt stöd i STruC++ | grind 1 |

Säkerhetsgränsen är inte en stilregel. Nödstopp och ljusridåer ligger på
certifierad säkerhets-PLC, skrivna av människa. Genererad logik får ligga
bredvid och vara förreglad av den.

## Domen sker i tre lager, och bara det tredje befordrar

| Lager | Frågar | Kan svara |
|---|---|---|
| **kompilerar** | går den att bygga? | grind 1 |
| **beter sig** | gör den rätt sak i tiden? | grind 5, ögat |
| **är den fortfarande rätt tillsammans** | håller den när stationen står i en lina? | grind 6 |

En lösning som kompilerar är en **kandidat**, aldrig en leverans. Endast en
körning i VC befordrar kandidat till guld (`50_grindar.md`, guldstegen).

## Facit är en sekvens, inte en text

En benchuppgifts facit får inte vara "koden ska se ut så här". Två riktiga
lösningar kan se helt olika ut. Facit är i stället ett **spår**:

```
(insignaler vid t) ──► (förväntade utsignaler vid t + fördröjning)
```

Det körs mot en riktig PLC genom kedjan i `60_plc.md`, och döms av kopplarens
avlästa värden. Domaren jämför alltså två serier tal, inte två texter.

Fördröjningen måste bära en tolerans, och toleransen måste ha en mätreferens.
M-39 mätte genomslag på 109, 210 och 232 ms för **två** signaler genom hela
kedjan; ett facit får inte kräva snabbare svar än kedjan kan ge, och heller inte
vara så slappt att en tom lösning passerar.

## Varje bench behöver ett trasigt facit

En uppgiftssamling där allt är grönt mäter ingenting. Varje uppgift ska ha minst
en **medvetet trasig lösning** som ser rätt ut men bryter mot ett krav — till
exempel saknar tidsövervakning — och som domaren måste underkänna.

Det är samma doktrin som gäller i hela repot: ingen grind utan trasig fixtur. En
grind som aldrig har fällt något har aldrig blivit provad.

## Reparationsslingan

När en grind fäller får modellen **grindens egen utdata**, inte en omskrivning
av den. Kompilatorns felrad, statiska analysens regelbrott, ögats serie.

Doktrinen står i `50_grindar.md` och är motiverad av en mätt incident: en
omimplementerad positionsdom underkände 2 av 4 medan ögat visade 4 av 4. En
grind som tolkar om observatörens mått mäter till slut sig själv.

Slingan måste ha ett tak, och taket är en mätt storhet, inte ett tycke. En
modell som inte har lagat felet efter n varv lagar det sällan på varv n+1, och
en obegränsad slinga döljer att uppgiften är olöslig. Taket sätts av en mätning
och skrivs som en konstant med härkomst på samma rad.

## Vad som gör detta svårt, och var det brukar gå fel

* **Flanker.** En sekvens som läser en nivå där den borde läsa en flank fungerar
  i nio scan av tio. Den felklassen är osynlig för grind 1 och 2, och syns bara i
  ögats serie när flanken hamnar mellan två scan.
* **Timers som nollställs av sitt eget villkor.** Kompilerar, ser rätt ut, fäller
  aldrig.
* **Förregling som är skriven som en kommentar.** Två rörelser tillåts samtidigt
  eftersom villkoret bara står i prosa.
* **Återstart.** De flesta lösningar är rätt på första varvet och fel efter ett
  stopp mitt i sekvensen.

Benchen ska innehålla uppgifter som fäller på var och en av dessa, annars mäter
den om modellen kan skriva en if-sats.

## Vad som inte är avgjort

* Hur skelettet ska bäras mellan tjänsten och modellen — format och identitet.
* Om reparationsslingan ska få se tidigare försök eller starta rent varje varv.
  Båda har kända nackdelar och valet ska mätas, inte tyckas.
* Hur en uppgift med flera giltiga lösningar poängsätts när facit är ett spår.
