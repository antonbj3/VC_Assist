# M-165 — matiecs kompileringstid över banken: max 0,087 s, och binären ligger i /tmp

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. matiec ur `wzy318/openplc:latest`, uppackad av
`plc/matiec.extrahera_ur_docker`. Ingen VC, ingen modell.
**Prövar:** `plc/matiec.STANDARD_TIDSGRANS = 30.0` saknade mätreferens och föll
tröskelgrinden. En tröskel utan mätning är en gissning som ser ut som kunskap.

## Talen

44 referenslösningar ur banken, kompilerade en gång var, noll undantag:

| | sekunder |
|---|---:|
| median | 0,066 |
| medel | 0,067 |
| p95 | 0,074 |
| **max** | **0,087** (`P-06`) |

Tidsgränsen 30 s är **340 gånger** det långsammaste observerade. Den är alltså
inte en prestandagräns utan en spärr mot att en hängd process håller en körning
för evigt — och det är en rimlig roll för den, men den ska stå skriven som det.

## Fyndet på köpet: binären ligger i /tmp

`hitta_binar()` returnerade `/tmp/opencode/matiec/iec2c`. matiec är sedan M-121
**typauktoriteten** i projektet — den avgjorde T-04:s typfel där STruC++
accepterade, och M-125 byggde hela A1 på den.

`/tmp` städas vid omstart och av systemets egen städning. Nästa gång det händer
faller tredje motorn, och felet kommer att se ut som något annat: `hitta_binar`
kastar, och det som syns är en trasig grind, inte en saknad fil.

Det här är inte lagat här. `extrahera_ur_docker` kan packa upp den igen, så
felet är återställbart — men det ska inte behöva upptäckas genom att en mätning
plötsligt inte går att köra.

## LIMITS

* **En körning per referens, ingen upprepning.** Spridningen är alltså omätt;
  talen är en enda mätpunkt per uppgift.
* **Bara bankens referenser.** De är korta och skrivna av människa. En
  modellskriven kropp med djupare nästling kan ta längre tid, och det är inte
  mätt. 340 gångers marginal gör det osannolikt att det spelar roll.
* **Maskinen delades** med tre opencode-sessioner, flera agenter och Visual
  Components under mätningen. Talen är alltså om något för höga, inte för låga.
* **Ingen kompilering föll.** Tider för kod som matiec *avvisar* är inte mätta,
  och en kompilator kan mycket väl vara långsammare på fel än på rätt.
