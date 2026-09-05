# FAS 8 ACCEPTANS — kompositionen

**beskriver:** flera stationer i samma PLC-program, `svc/vc_assist_svc/plc/`, ögat
**kontrakt:** `docs/spec/70_faser.md` — *"Flera stationer. Guld per station,
sedan guld för linan. **L2**"*
**körs av:** `tests/protocol/kor_fas8_linan.py`

**Status: FYLLS I NÄR KÖRNINGEN ÄR KLAR.**

## Vad fasen påstår, och vad den inte påstår

Fas 7 visade att vägen finns för **en** station: skelett, deklarationer,
sekvens, kompilering, uppladdning, en scen som rör sig, och ett öga som dömer
(M-49, M-50). Fas 8 påstår något annat och smalare:

> Två stationer i samma program, på samma lina, håller **var för sig** sitt
> eget facit **och** linans, och de fel som bara uppstår när de står
> tillsammans blir fällda.

Det som **inte** påstås: ingenting om tre eller fler stationer, ingenting om
hur ofta en modell lyckas skriva dem (fas 9), ingenting om Windows, ingenting
om verklig hårdvara.

## Definitionen som hela fasen står på

Ett **kompositionsfel** är ett fel som

1. **fälls** av ögat när båda stationernas block kör i samma program, och
2. **inte fälls** när stationerna körs var för sig.

Båda halvorna krävs. Ett fall som ögat fäller också i en station för sig är
inget kompositionsfel — det är ett fas 7-fel, och de är redan mätta. Ett fall
som ingen fäller är inget fel alls.

Körningen kör därför **varje** program i tre konfigurationer:

| Konfiguration | Vad som ligger i PLC-programmet | Vad ögat dömer |
|---|---|---|
| `LINJE` | båda stationernas block | station A:s facit, station B:s facit **och** linans |
| `A` | bara station A:s block, egen signalkarta, egen uppladdning | station A:s facit |
| `B` | bara station B:s block | station B:s facit |

Enstationskonfigurationen är alltså **exakt fas 7:s uppställning**: ett
program, en station, ett facit.

## Linan

```
matare -> ST8_Bana1 [station A] -> ST8_Bana2 [station B] -> av i änden
```

Två banor i serie, en fotocell och en bromsklack per station, och **ett delat
utmatningsdon** som båda stationerna kommenderar. Det delade donet är fas 8:s
enda nya fysik och det är deklarerat i anläggningen före lösningarna: begär
båda det samtidigt kan det inte tjäna bägge, ingen av dem får det, båda
banorna står kvar stilla, och konflikten rapporteras i stället för att tigas.

Två saker om scenen som ingen tidigare mätning hade svarat på och som fas 8
därför mätte först (M-73):

* **En produkt går över kopplingen bana → bana.** `M-41` lämnade det oprövat
  (*"ett led till — bana → bana, eller bana → sänka — är oprövat"*) och `M-67`
  likaså (*"om en produkt faktiskt går över kopplingen är inte mätt"*).
* **En stoppad nedströmsbana ackumulerar uppströms.** `M-41` hade `Accumulate
  = True` satt men aldrig belastad.

## Grindarna som ska vara gröna

Samma kedja som i fas 7, med samma krav, körd på **varje** konfiguration:

| # | Grind | Vad körningen ska visa |
|---|---|---|
| 1 | Kompilering | STruC++ bygger den genererade ST-koden utan fel |
| 2 | Statisk analys | inga kända dödsfällor, ingen skrivning till `skyddad` tagg |
| 3 | Deklarationsmatchning | varje symbol modellen rörde finns i signalkartan |
| 4 | Anropsvalidering | inga uppfunna verktygsnamn eller argument |
| 5 | Ögat | **tre** domar: station A, station B, linan |

## De trasiga fallen

Var och en är **en** ändring mot den hela lösningen, och var och en ska fällas
i `LINJE` och passera i `A` och `B`.

| # | Ändringen | Klassen den hör till | Ska fällas på |
|---|---|---|---|
| K1 | station B:s block räknar i station A:s `a_laget` | två stationer tar samma resurs (programmets) | stationsfacit |
| K2 | station B:s block anropar station A:s `a_flank` | en station svälter — den tappar sina starter | stationsfacit |
| K3 | turordningen på det delade utmatningsdonet borttagen | två stationer tar samma resurs (den fysiska) | linjefacit, förreglingen |
| K4 | förreglingen skriven för linan i stället för per station | en förregling som håller inom en station men bryts mellan två | stationsfacit |
| K5 | station A väntar på att station B:s zon är tom | en station blockerar nästa — mättnad nedströms | stationsfacit eller linjefacit |

### Två sorters ändringar, och skillnaden bär beviset

**INSTANS** (K1, K2) låter stationerna dela en arbetsvariabel. Texten är
**densamma** i alla tre konfigurationerna — enstationskörningen kör fallets
egen kod, och delningen har då bara en delägare.

**VILLKOR** (K3, K4, K5) rör ett villkor eller en rad som namnger den **andra**
stationens signal eller läge. I en enstationskonfiguration har den ingen
referent, och kroppen reduceras då tecken för tecken till den hela lösningens.
Körningen kontrollerar reduktionen **mekaniskt** (`reduktionen()`) och skriver
ut den. Det är halva beviset: det som inte går att skriva med en station kan
inte fällas i en.

## Ärlighetskravet på körningen

Samma som i fas 7, med ett tillägg:

* varje grinds **egen** utdata, aldrig en omskrivning
* per fall: domen i alla tre konfigurationerna, och om det är ett
  kompositionsfel enligt definitionen ovan
* ett fall som fälls **också** i en enstationskörning ska rapporteras som
  **inget kompositionsfel**, inte tystas
* klockkvoten (simuleringstid / väggtid) mätt i varje körning, för facits
  fönster är snäva och de är snäva därför att kvoten är 1

## Vad fasen inte kommer att ha prövat

* **Fler än två stationer.**
* **Att en modell skriver kropparna.** Alla är handskrivna, som i fas 7.
* **Nödstoppet.** Den skyddade ingången går inte att driva över OPC UA (M-49).
* **Windows, verklig hårdvara, frekvens.**
