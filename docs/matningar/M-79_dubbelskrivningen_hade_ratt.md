# M-79 — dubbelskrivningsregeln skärptes, och visade sig ha haft rätt

**Datum:** 2026-09-05
**Rör:** `svc/vc_assist_svc/st/validator.py`, grind 2, felklass `F7`
**Rättar:** en slutsats i `M-62`.

## Varför jag ifrågasatte regeln

`M-78` mätte att modellen fälldes på `DUBBELSKRIVNING` i tre av fyra uppgifter —
6, 5 och 3 anmärkningar. Modellens mönster var *"sekvensen sätter utgången, ett
hårt förreglingsblock nedanför nollar den"*.

Det är ett vedertaget verkstadsidiom: **beräkna, sedan tvinga**. Att fälla det
såg ut som en falsk röd av samma slag som `M-51` fann tre av i ST-lagrets form.

Regelns eget skäl är att *ordningen avgör vilken skrivning som vinner*. Skriver
båda **samma** värde finns ingen ordning att få fel.

## Skärpningen

Två **villkorade** skrivningar av samma **literal** fälls inte längre. Allt
annat fälls som förut:

| Fall | fälls? |
|---|---|
| två villkorade, samma literal (`FALSE` och `FALSE`) | **nej** — ny regel |
| två villkorade, olika literaler (`TRUE` och `FALSE`) | ja |
| två villkorade, samma **uttryck** (`a AND b` två gånger) | ja — ett uttrycks värde beror på tillståndet och går inte att avgöra statiskt |
| två **ovillkorade**, samma värde | ja — den första syns aldrig, ett annat fel |
| olika typer (`0` mot `1`) | ja |

Fem prov, fyra av dem trasiga fixturer. Värdet bärs nu genom hela
grensammanslagningen, och **faller bort till `None` så snart två grenar skriver
olika** — då är värdet inte längre bevisbart.

## Och sedan sa mätningen emot mig

`M-62` skrev om bankens egen referens för L-05:

> *"L-05:s egen referenslösning fälls av grind 2 (`DUBBELSKRIVNING`, F7:
> `ST260_LFT_DOWN` skrivs på rad 65 och 107). Spårfacit godkänner den — **båda
> skrivningarna sätter FALSE** — men grind 2 fäller ändå."*

Med den skärpta regeln skulle den fällningen försvinna. **Den gjorde den inte.**

Instrumenterat, vad grinden faktiskt ser:

```
[(True, 63, None), (True, 105, ('', False))]
```

Den andra skrivningen är `FALSE`. Den **första** har värdet `None` — därför att
raden på 63 ligger i en struktur som på rad 81 skriver **`TRUE`** till samma
utgång. Vilket värde som når rad 105 beror alltså på vilken gren som togs, och
då avgör ordningen.

**Regeln hade rätt.** M-62:s läsning tittade på de två radnumren i
felmeddelandet och missade den tredje raden som gör dem oförenliga.

## Vad det säger om båda

Skärpningen är ändå en förbättring: den tar bort en klass av falska röda som
finns, och den gör regelns dom precis i stället för bred. En grind ska fälla det
som faktiskt är fel.

Men den fällning jag misstänkte var falsk var **äkta**, och den enda som
undersökte den ordentligt var instrumenteringen. Att läsa ett felmeddelande är
inte att mäta vad grinden såg.

Och modellen höll med regeln utan att veta något om det här. Ur dess rapport
efter varv 2:

> *"Det är inte en stilanmärkning — det är en mätning av hur många utgångar vars
> värde avgörs av radordning."*

Den byggde om alla fyra efter den enda som redan var grön: allt räknas i
arbetsvariabler, och **varje utgång skrivs exakt en gång, längst ner**.

## Vad som INTE är mätt

* **Bara fyra referenser.** Bankens 51 uppgifter har inte körts genom grind 2
  med sina signaler deklarerade; de fyra med spårfacit är de enda som prövats.
* **Om det finns fler falska röda i regeln.** Skärpningen täcker literaler.
  Två skrivningar av samma *variabel* (`ut := x;` två gånger) fälls fortfarande,
  och om det är rätt är inte undersökt.
* **Om L-05:s referens borde ändras.** Den bryter mot vår egen grind 2, och det
  gör uppgiften olöslig i den fulla kedjan. Att rätta ett facit är bänkens
  beslut, inte grindens.
