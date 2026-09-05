# M-126 — mätningsindexet genereras, och två sessioner tog samma nummer inom 91 sekunder

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell, ingen OpenPLC.
**Prövar:** Operatörens stående krav *"Informationen måste vara lättillgänglig
för LLM"*, mätt på den fil en språkmodell läser först.

## 1. Sjuttiofyra mätningar var osynliga

`docs/spec/00_index.md` bar en **handskriven** tabell över mätningarna. Den
slutade vid `M-34`. Katalogen `docs/matningar/` bar samtidigt **108** filer.

| | |
|---|---|
| mätningar på disk | 108 |
| rader i indexets tabell | 34 |
| **osynliga i indexet** | **74** |

Indexet sa det om sig självt — *"Tabellen ovan är ofullständig … bör genereras
ur den"* — och ingen kö ägde raden.

`M-119` mätte samma brist från andra hållet: sex frågeslag av tretton svarade
ingenting, och grindreglerna svarade `0 av 31` fast svaret stod komplett på
disk. En fil som inte går att nå är, för den som slår upp, en fil som inte
finns.

## 2. Tabellen genereras nu

`svc/vc_assist_svc/matningsindex.py` läser katalogen och skriver tabellen
mellan två markörer i `00_index.md`. `tests/enhet/test_matningsindex.py` fäller
om filen på disk slutat stämma.

Två fel namnges i stället för att tigas om: en fil vars första rad inte är
`# M-NN — titel`, och två filer som gör anspråk på samma nummer.

**Fynd vid första körningen:** `M-121` skrev `# M-121:` med kolon där de andra
107 skrev em-streck. Den hade blivit titellös i tabellen. Rättad.

**Min egen bugg, fångad av en fixtur jag skrev efteråt:** numret lästes som
heltal och skrevs som `M-1`. Repot hänvisar till `M-01` på 25 ställen och till
`M-03` på 46 — tabellen hade gjort varje sådant uppslag till en miss. Etiketten
bärs nu som den står skriven.

## 3. Två sessioner tog M-124 inom 91 sekunder

Fem sessioner startade 14:25. Utfallet:

| fil | skapad | kö |
|---|---|---|
| `M-124_de_23_svaren.md` | 14:25:32 | B |
| `M-124_openplc_som_tredje_motor.md` | 14:27:03 | A |

Båda committade, båda med rubriken `# M-124 —`. Grinden var byggd tjugo minuter
tidigare och fällde det direkt.

**Orsaken är instruktionen, inte sessionerna.** `00_GEMENSAMT.md` sa *"numret
reserveras i ordning; kolla högsta numret först"*. Det är en regel någon ska
minnas, och med fem samtidiga skrivare är läs-sedan-skriv en kapplöpning per
konstruktion. Att båda gjorde rätt enligt instruktionen och ändå kolliderade är
beviset.

`scripts/nytt_matningsnummer.sh` reserverar numret **atomiskt** under samma lås
som `scripts/committa.sh`, och skapar filen med rätt rubrikform och ett
LIMITS-avsnitt. A:s fil flyttades till `M-125`; B hann först.

## LIMITS

* **Tabellen mäter att filen finns och har en titel, inte att den går att
  hitta.** Att en rad står i indexet är inte samma sak som att ett uppslag når
  den. `M-119` visade att ingen datahanterare öppnar `docs/spec/` vid körning
  över huvud taget — den bristen är **inte** lagad här, den ligger i kö E som
  E3b.
* **Titeln är mätningens egen rubrik, oprövad mot innehållet.** En mätning vars
  rubrik lovar något annat än brödtexten passerar.
* **Numret är unikt, inte rätt.** Verktyget hindrar två filer på samma nummer.
  Det hindrar inte att någon skriver ett nummer i en text som pekar på fel
  mätning.
* **Kapplöpningen är stängd bara för dem som använder verktyget.** En session
  som skapar filen för hand kolliderar fortfarande — men grinden fäller det
  då, i stället för att låta det ligga.
* **74 var talet 14:05.** Sessionerna skriver mätningar medan detta skrivs;
  antalet var 108 vid start, 110 en halvtimme senare.
