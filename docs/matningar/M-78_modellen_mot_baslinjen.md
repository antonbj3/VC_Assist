# M-78 — modellen mot baslinjen: 0 av 4 mot 4 av 4

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_fas9_modellen.py`
**Paret:** samma domare, kontrollerad signatur — scan 20,0 ms, marginal 2 scan,
grindar `[spar]`, domarkod `f265c53e8433`, facit `6a9efd257e1b`.

## Vad modellen var, och varför det står först

Det finns **ingen API-nyckel och ingen byggd modellklient** i repot. Modellen är
därför en Claude-agent som fick **exakt** det slingan ger — uppgiftens text, dess
signaler, sekvens, förreglingar och tider, plus skelettet — med uttryckligt
förbud mot att öppna repot där facit och referenslösningar ligger. Agenten
bekräftar att den inte öppnade det.

Det är en verklig modell och en verklig mätning. Den är **inte automatiserad,
inte upprepad, och utan reparationsslinga**: ett skott per uppgift, n = 1.

## Talet

| Sida | klarade |
|---|---:|
| baslinjen (regelmotor, `M-62` nivå `spec`) | **4 av 4** |
| modellen (Claude-agent, n = 1, inget reparationsvarv) | **0 av 4** |

**En regelmotor slog modellen på alla fyra uppgifterna.**

## Vad som faktiskt gick fel

Alla fyra **kompilerade** — grind 1 med riktig STruC++ 0.6.6 gav grönt på
samtliga. Grind 3 gav noll anmärkningar. Modellen skrev alltså giltig ST mot
rätt taggar.

**Grind 2 fällde tre av fyra på `DUBBELSKRIVNING`** — 6, 5 och 3 anmärkningar.
Samma utgång skrivs på två ställen i samma scan. Det är felklass F7, och det är
inte ett skönhetsfel: vilken skrivning som vinner beror på radordningen.

Och facit fällde alla fyra:

| Uppgift | vad spåret visade |
|---|---|
| **T-07** | `invariant: ingen_klamma_utan_tryckluft` — klamman stod kvar kommenderad när tryckluften föll |
| **H-04** | `invariant: ingen_rorelse_med_brutet_nodstopp` — rörelse med nödstoppet brutet |
| **L-05** | vakuumet släppte och sög fast vid fel tidpunkt (1100 ms) |
| **S-05** | fel PackML-tillstånd vid 1500 ms efter ett maskinfel |

**Två av fyra är invariantbrott, och båda rör en säkerhets- eller
förreglingsfunktion.** Det är den dyraste sortens fel: koden gör sitt arbete
rätt i normaldrift och fel precis när något går sönder.

## Modellen namngav själv områdena den föll på

Det mest anmärkningsvärda i körningen står inte i talen. Modellen lämnade
**tretton uttalade gissningar** utan att veta hur den gått, och de träffar
utfallet:

* Gissning 1: *"`AIR_OK` … nämns inte en enda gång i uppgiftstexten för de två
  stationerna. Jag tog med den i driftvillkoret. **Detta är min enskilt största
  risk.**"*
* Gissning 3: *"Vad som händer med greppet vid larm. T-07 håller kvar klamman …
  Vill domaren se alla utsignaler låga vid larm är detta fel."*

T-07 föll på just det: klamman hölls kvar när tryckluften föll.

En modell som kan peka ut var den gissade är **mer** användbar än en som svarar
med samma säkerhet överallt — även när den har fel. Det är också ett argument
för reparationsslingan: de här gissningarna är precis vad en grinddom hade
kunnat avgöra.

## Vad talet INTE säger

* **Inte att modeller är sämre än regelmotorer.** Det säger att *den här*
  modellen, i *ett* försök, utan reparationsvarv, förlorade mot en regelmotor
  som är byggd för **just den här bankens konventioner**. Baslinjen läser
  `control.sequence` och `control.interlocks` som ett kontrollerat språk; den är
  en mallkompilator för bankens eget format.
* **Inte hur det går efter k varv.** Reparationsslingan finns (`M-52`) men
  kräver en modell som svarar automatiskt, och någon sådan finns inte i repot.
  Varje fel ovan är ett fel en grind kunde ha rapporterat tillbaka.
* **Inte ett fel per klass i statistisk mening.** Fyra uppgifter, åtta
  bristkoder. Nämnaren är fyra.
* **Ingenting om andra modeller, andra promptar eller andra försök.**

## Vad mätningen bekräftar

`M-62` skrev: *"Rapporterar fas 9 fyra av fyra är det oavgjort mot en
mallkompilator, och det ska stå med de orden."*

Vi rapporterar noll av fyra. Ribban var satt före körningen, av den andra sidan,
och den höll.

## Vad som INTE är mätt

* **Bara de fyra uppgifter som har spårfacit.** Banken har 51.
* **Inget reparationsvarv.** Det är den enskilt största luckan: hela poängen med
  grindkedjan är att felen går tillbaka till modellen, och det ledet är inte
  prövat med en riktig modell.
* **Grind 4 kunde inte döma något.** Modellen ombads inte skriva scenkod, så
  anropsvalideringen svarade *"kandidaten bär ingen scenkod att validera"* —
  korrekt fail-closed, men fasen mäter alltså bara ST-halvan.
* **Ingen körning i VC.** Domen kommer ur vår egen ST-tolk, korsprövad mot
  STruC++ i `M-54` men inte mot OpenPLC.
* **En enda modell, en enda prompt.** Formuleringen i uppgiftspaketet kan ha
  bidragit till varje fel ovan, och ingen alternativ formulering är prövad.
