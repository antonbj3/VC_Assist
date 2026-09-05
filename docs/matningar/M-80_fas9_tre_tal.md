# M-80 — fas 9:s tre tal: 0 av 4, sedan 4 av 4 efter ett varv

**Datum:** 2026-09-05
**Körs av:** `tests/protocol/kor_fas9_modellen.py`
**Bygger på:** `M-78` (första försöket), `M-62` (baslinjen)
**Paret:** samma domare på båda sidor, signatur `897805bef1f9`, facit
`6a9efd257e1b`, scan 20,0 ms, marginal 2 scan.

## Kontraktet

`docs/spec/70_faser.md`, fas 9:

> Tre tal rapporterade: **första försöket**, **efter k varv**, **fel per klass**.

## Talen

| | modellen | baslinjen |
|---|---:|---:|
| **första försöket** | **0 av 4** | **4 av 4** |
| **efter 1 reparationsvarv** | **4 av 4** | — |
| kostnad per uppgift | ett modellsvar + ett återkopplingsvarv | under 1 ms, noll tokens |

**Fel per klass, första försöket** (fyra uppgifter, nämnaren är fyra):

| Klass | antal |
|---|---:|
| `DUBBELSKRIVNING` (grind 2, F7) | 14 fördelade på 3 av 4 uppgifter |
| invariantbrott i facit | 2 av 4 — `ingen_klamma_utan_tryckluft`, `ingen_rorelse_med_brutet_nodstopp` |
| punktkrav i facit | 6 avläsningar |
| grind 1, grind 3 | **noll** i alla fyra |

Efter reparationsvarvet: **noll i varje klass**.

## Vad slingan faktiskt gjorde

Modellen fick **grindarnas och facitets egna ord, ordagrant** — ingen
sammanfattning, ingen tolkning. Den skrev om alla fyra.

Det den ändrade, i dess egna ord:

* **Strukturen.** Den byggde om tre stationer efter den enda som redan var grön:
  *"allt räknas i arbetsvariabler, och varje utgång skrivs exakt en gång, längst
  ner."*
* **T-07.** Ett hårt villkor för tryckluftsbortfall — och en ny arbetsvariabel
  för att den fixen inte skulle skapa ett falsklarm när trycket kommer tillbaka.
* **H-04.** *"Jag hade dragit tillbaka robotarna men låtit begäran ligga kvar —
  då står mottagaren och väntar på en överlämning ingen längre driver."*
* **S-05.** Tog bort sin spärr på `CLEAR`; facit vill se felet som `ABORTING`,
  inte som ett bortkastat kommando.
* **L-05.** Vakuumet släpper nu när trycket går ur fönstret, i stället för att
  hålla.

## Modellen kunde peka ut var den gissade

Efter varv 1 lämnade den **tretton uttalade gissningar**. Efter varv 2 sa den
vilka som föll:

> *"**Fel, nummer 3** — 'vad som händer med greppet vid larm'. … Mitt resonemang
> var 'en pausad linje får inte släppa en detalj den håller'. Det jag missade är
> att den regeln handlar om en **paus**, inte om ett **fel**. Vid ett fel är
> fortsatt kommendering värre än att tappa detaljen — och en pneumatisk klamma
> utan tryck håller ändå ingenting, så kommandot ljuger bara för logiken."*

Och den var ärlig om vad ett uteblivet fel betyder:

> *"Nummer 2, 5, 7, 8, 9, 10, 11, 12 och 13 fick ingen anmärkning. Det betyder
> att de inte fälldes — **inte att de provades**."*

## En konfunderare som uteslöts

Jag skärpte `DUBBELSKRIVNING`-regeln (`M-79`) **mellan** de två varven. Om
skärpningen hade gjort varv 2 grönt vore talet värdelöst.

Kontrollerat mekaniskt: i alla fyra lösningarna skrivs **ingen utgång mer än en
gång**. Regeln kan inte fyra när det bara finns en skrivning, så skärpningen är
utan betydelse för utfallet.

## Vad talen betyder, och inte

**Oavgjort mot en mallkompilator**, och det ska sägas med de orden — `M-62`
satte den ribban innan modellen kört.

Men de två sidorna är inte likvärdiga i övrigt:

| | baslinjen | modellen |
|---|---|---|
| löser i varv 1 | ja | nej |
| kostnad | under 1 ms, noll tokens | två modellsvar |
| generaliserar utanför bankens format | **nej** — den läser `control.sequence` som ett kontrollerat språk och ger upp på 132 av 266 sekvensrader | okänt |
| kan säga var den gissade | nej | **ja**, och gissningarna träffade |

Det sista är den enda egenskapen där skillnaden är kvalitativ och inte bara ett
tal.

## Vad som INTE är mätt

* **Bara fyra uppgifter.** Banken har 51; fyra har spårfacit.
* **n = 1 per uppgift, per varv.** Ingen upprepning, ingen spridning, inget
  konfidensintervall. Ett annat försök kan ge ett annat tal.
* **Slingan drivs för hand.** Bryggan mellan grind och modell är ett
  meddelande, inte ett API-anrop. `M-52`:s tak på fyra varv är alltså inte
  prövat med en riktig modell — vi behövde ett.
* **Grind 4 dömde ingenting.** Modellen ombads inte skriva scenkod.
* **Ingen körning i VC.** Domen kommer ur vår ST-tolk, korsprövad mot STruC++ i
  `M-54` men inte mot OpenPLC.
* **En modell, en prompt, en formulering.** Uppgiftspaketets ordval kan ha
  bidragit till varje fel i varv 1, och ingen alternativ formulering är prövad.
* **Ingenting om svårare uppgifter.** De fyra är de enda med spårfacit, och
  `M-62 §6` pekar ut var bänken behöver bli mer diskriminerande.
