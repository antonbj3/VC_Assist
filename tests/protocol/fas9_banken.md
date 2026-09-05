# FAS 9 ACCEPTANS — bänken

**beskriver:** `bank/`, `svc/vc_assist_svc/plc/baslinje/`, `bank/domare.py`,
`bank/par.py`, `svc/vc_assist_svc/plc/reparation.py`
**kontrakt:** `docs/spec/70_faser.md` — *"Tre tal rapporterade: första försöket,
efter k varv, fel per klass"*
**körs av:** `tests/protocol/kor_fas9_modellen.py` (modellsidan),
`bank/baslinjebank.py` (baslinjen)
**mätningar:** `M-45` (bankens täckning), `M-62` (baslinjen), `M-78` (första
försöket), `M-80` (alla tre talen)

## Status: DE TRE TALEN ÄR MÄTTA. Fasen står ÖPPEN på hur de togs fram.

## Talen

| | modellen | baslinjen |
|---|---:|---:|
| **första försöket** | **0 av 4** | **4 av 4** |
| **efter ett reparationsvarv** | **4 av 4** | — |

**Fel per klass, första försöket** (nämnaren är fyra uppgifter):

| Klass | antal |
|---|---:|
| `DUBBELSKRIVNING`, grind 2 | 14 på 3 av 4 |
| invariantbrott i facit | 2 av 4 |
| punktkrav i facit | 6 avläsningar |
| grind 1, grind 3 | **noll** |

## Paret är kontrollerat, inte påstått

`bank/par.py` **kastar** om sidorna dömts av olika domare. Signaturen binder
scanperiod, marginal, grindlista, sha256 över hela domarkedjans källkod och över
facit. En jämförelse mellan två domare mäter domaren, inte de två sidorna.

Baslinjesidan **körs i samma anrop** i stället för att citeras ur en mätning. Ett
citerat tal kan ha dömts av en annan domare än det jämförs med.

## Giltigheten: att modellen inte såg facit

Ett förbud i en prompt är en bön. Körningen **mäter** det:

| Uppgift | kodlikhet | längsta gemensamma sträng | delade egna namn |
|---|---:|---:|---|
| H-04 | 5,8 % | 39 tecken | **inga** |
| L-05 | 8,2 % | 18 | **inga** |
| S-05 | 5,8 % | 6 | **inga** |
| T-07 | 9,0 % | 18 | **inga** |

Det tredje måttet är det bärande. **Variabelnamn är ett fritt val** — två
lösningar som delar `tmrIndex` har inte kommit på det var för sig. Noll delade
namn i alla fyra.

Den längsta gemensamma strängen, 39 tecken, är
`(CLK := SYS_RESET); IF NOT EMG_OK THEN` — en flankdetektor på återställning
följd av en nödstoppskontroll. Två ingenjörer skriver den likadant.

Kommentarer räknas bort. De är prosa på samma språk och skulle dränka mätningen
i ord som *att* och *bara* — mätt, i den första versionen av kontrollen.

## Trasiga fall som måste falla

| Fall | Måste avvisas | Var |
|---|---|---|
| två sidor dömda med olika scanperiod | ja — `Parfel` | `tests/enhet/test_baslinje.py` |
| ett svar vars ram är ändrad | ja — `Skelettfel`, aldrig en kandidat | `tests/enhet/test_skelett.py` |
| en arbetsvariabel med adress, eller med en signals namn | ja | `tests/enhet/test_skelett.py` |
| ett svar som liknar referensen | **varning i körningen**, och talen förklaras opålitliga | `kor_fas9_modellen.py` |
| ett program som styr ingenting | fälls av facit — men passerar grind 1–3 och 252 av 349 påståenden (`M-62`) | `bank/baslinjebank.py` |

Den sista raden är fasens viktigaste varning: **ett procenttal ur en
påståenderäkning får aldrig bli huvudtalet.** Golvet är högt.

## Varför fasen står öppen

* **Slingan drevs för hand.** Bryggan mellan grind och modell är ett meddelande,
  inte ett API-anrop. Det finns ingen nyckel och ingen modellklient i repot.
  `M-52`:s tak på fyra varv är därmed oprövat med en riktig modell — vi behövde
  ett.
* **Fyra uppgifter av 51.** Bara de fyra har spårfacit.
* **n = 1 per uppgift och varv.** Ingen upprepning, ingen spridning.
* **Grind 4 dömde ingenting.** Modellen ombads inte skriva scenkod.
* **Ingen körning i VC.** Domen kommer ur vår ST-tolk, korsprövad mot STruC++ i
  `M-54` men inte mot OpenPLC.
* **En modell, en prompt.** Formuleringen kan ha bidragit till varje fel i varv
  1, och ingen alternativ formulering är prövad.

## Vad som får sägas om talen

**Oavgjort mot en mallkompilator**, med de orden. `M-62` satte ribban innan
modellen kört, och den höll.

Sidorna är inte likvärdiga i övrigt: baslinjen löser i varv 1 till noll tokens,
men ger upp på 132 av 266 sekvensrader utanför bankens eget format. Modellen
behövde ett varv — och kunde säga **var** den gissade, och två av dess tretton
utpekade gissningar var precis de som föll.
