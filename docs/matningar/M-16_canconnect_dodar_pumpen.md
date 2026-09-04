# M-16 — `canConnect` dödar pumpen

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Följd:** ett **läsande** verktyg kan döda bryggan. Det trodde vi inte var möjligt.

## Vägen fram

M-14 lämnade `connect` oprövat: `canConnect` var falskt i sju uppställningar.
Fältets bindning var nyckeln. Ett transportfälts `Transport`-egenskap har typen
`Ref<ComponentProcessor>`, och den tar **inte** en `vcMotionPath`, ett namn eller
en nod — alla tre ger `SystemError`.

`VC_TRANSPORT` skapar en `vcTransport` (M-15). Den tar den:

```
6 bind transport   done   {"satt": "<vcTransport object at 0x...>"}
```

Därmed går hela kedjan att bygga, steg för steg, alla gröna:

| Steg | Utfall |
|---|---|
| skapa komponent | done |
| `createBehaviour(VC_TRANSPORT, "Transport")` | done, `vcTransport` |
| `createBehaviour(VC_ONETOONEINTERFACE, "Iface")` | done, `vcSimInterface` |
| `createSection("Sec")` | done |
| `createField(VC_TRANSPORTFIELD, "Transport")` | done |
| binda fältet till transporten | **done** |

## Fyndet

Med två sådana komponenter byggda — den ena `Connection=1`, den andra `2` —
dödar **enbart anropet `ia.canConnect(ib)`** pumpen.

```
bygg TrA                 done   {"byggd": "TrA"}
bygg TrB                 done   {"byggd": "TrB"}
las granssnitten         done   {"A_sektioner": 1, "A_falt": 1, "A_abstrakt": false}
ENBART canConnect        BRYGGAN DOG
```

Koden i sista posten var tre rader: slå upp båda gränssnitten, anropa
`canConnect`, skriv ut. Uppslagen ensamma gick igenom i posten före.

Bryggloggen slutar mitt i:

```
koad q4: ENBART canConnect
godkand q4, kors av pumpen
```

Ingen `kord q4`. Ingen `simuleringen stoppad`. **Ingen rad alls efteråt.**

## Varför det är värre än M-13

M-13:s två fall — `createBehaviour(VC_SCRIPT)` och `app.save()` — **stoppar**
simuleringen, och skriptets `OnStop` hinner logga det. Det går att upptäcka och
varna för i förväg.

Här stannar allt utan ett ord. Antingen dödas tasklet:en utan att `OnStop` körs,
eller så hänger anropet för alltid inne i VC:s C-lager. Det är omätt vilket.

Och `can_connect` är deklarerat **`effect="read"`**. Ett läsande verktyg går
förbi godkännandekön, direkt till `exec`. Antagandet att läsande kod är ofarlig
håller alltså inte.

## Vad som ändras

1. `can_connect` och `connect` får inte anropas mot ett gränssnitt vars fält är
   bundna, förrän orsaken är mätt. Verktygen ska bära varningen.
2. Klassen "anrop som dödar pumpen" kan inte längre avgränsas till skrivande kod.
   `skrivgrind.DODANDE_ANROP` behöver en läsande gren.
3. Fas 5:s grind — alla gränssnitt kopplade — är fortfarande stängd, men nu av en
   **mätt orsak** i stället för av en tom katalog.

## Öppet

* Hänger anropet eller dör tasklet:en? Går att skilja åt genom att mäta om
  VC-processen svarar på annat efteråt.
* Går det bättre med en riktig katalogkomponent, där fälten är modellerade av VC
  själv i stället för av oss? **Omätt**, och det är den intressanta frågan.
* Är det bindningen som är fel, snarare än `canConnect`? Ett fält bundet till en
  processor som inte hör till samma komponentmodell kan mycket väl vara ogiltigt
  på ett sätt VC inte kontrollerar.
