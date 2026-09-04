# FAS 5 OM — samma grind, riktiga komponenter

**Status: UTKAST. Körningen är INTE körd.** Den kräver en levande VC-instans,
och instansen ägs av en annan agent. Ingen rad nedan är ett resultat; varje rad
är en fråga med ett förutbestämt utfall.

**beskriver:** `svc/vc_assist_svc/komponentfil.py`,
`svc/vc_assist_svc/layout/komponent.py`, `svc/vc_assist_svc/layout/`
**kontrakt:** `docs/spec/70_faser.md` — *"N mållayouter byggda: noll
kollisioner, alla gränssnitt kopplade"*
**mätta förutsättningar:** [M-61](../../docs/matningar/M-61_vad_en_komponentfil_bar.md)

## Varför körningen finns

Fas 5 är stängd på 18 layouter, 117 objektpar och noll kollisioner. Det är
sant, och det är mätt av VC:s egen geometri. **Men allt var block.**

`provscener.py` säger det själv: maskinernas fotavtryck är ANTAGNA, och
robotens låda räknas som `0.30 × räckvidden`. Fas 5 bevisade alltså
mekanismen — skapa, placera, mäta avstånd, koppla gränssnitt. Den bevisade
inte att en riktig cell går att ställa upp, för den hade aldrig en riktig
komponent att ställa upp.

Den här körningen byter ut lådorna mot riktiga komponenter ur biblioteket och
ställer **samma** frågor. Urvalet är ett urval, och dess nämnare ska stå i
rapporten — biblioteket har 3201 komponenter och körningen prövar inte alla.

## Vad som redan är avgjort utan VC (M-61)

| Storhet | Ur filen |
|---|---|
| namn, kategori, tillverkare | **läst**, 3201 av 3201 |
| räckvidd | **läst** 1437, **härledd ur profilen** 225, **saknas** 1539 |
| gränssnittens namn, sektioner, ramar och fälttyper | **läst**, 11 563 st i 3062 komponenter |
| monteringsramarnas NAMN | **läst**, 9824 st i 3086 komponenter |
| monteringsramarnas LÄGE | **läst** 3036, **härlett** 121, **saknas** 6667 av 9824 |
| transportörens flödesordning | **läst** för 122 av 163 |
| transportörens flödesriktning som vektor | **saknas** för 303 av 324 ramar |
| omslutande volym | **saknas**, 0 av 3201 |

Den sista raden är hela skälet till att den här körningen behövs. Lådan finns
inte i filen; den måste komma ur VC.

## Steg 0 — förutsättningar

* Indexet byggt: `python3 svc/vc_assist_svc/katalogindex.py --djupt --ut <fil>`
* Varje vald komponent läst offline först:
  `python3 -m vc_assist_svc.komponentfil --fil <komponent>`. Vad filen säger
  ska stå bredvid vad VC säger, annars går skillnaden inte att se.
* Biblioteksroten **söks upp**, aldrig antas (`katalogindex.hitta`).
* VC uppe med bryggan, pumpen mätt levande (fas 1).
* Skrivgrinden på. `can_connect` dödade pumpen en gång (M-16) och står i
  `skrivgrind.DODANDE_ANROP` tills motsatsen är mätt.

## Steg 1 — går en katalogkomponent alls att ladda?

`load_component(uri="file:///.../<manufaktur>/<kategori>/<namn>.vcmx")`.

**Detta är oprövat.** M-57 säger det rakt ut: att filen finns och går att läsa
är inte samma sak som att `app.load()` ger en användbar komponent.

Urval: minst **fem per kategori** över de tio största kategorierna, plus de
åtta komponenter som saknar geometriposter helt.

| Utfall | Vad det betyder |
|---|---|
| alla laddar | vidare till steg 2 |
| några laddar inte | felen **listas per kategori**, inte per fil; en klass, inte en rad |
| ingen laddar | fas 5-om faller här, och M-61:s offline-läsning är allt vi har |

## Steg 2 — täcker `get_bounds` HELA komponenten?

**Körningens viktigaste fråga.** `get_bounds` läser `BoundCenter` och
`BoundDiagonal` på komponentens rotnod. En robot är en kedja av noder, och en
transportör är hundratals geometrier under en switch. Om rotnodens låda bara
täcker rotnodens EGEN geometri är varje låda i hela bygget för liten — och en
för liten låda ger noll kollisioner, alltså ett grönt svar som är fel.

Prov, per komponent:

1. `A = get_bounds(component)`
2. `B = ∪ get_bounds(component, node=n)` för varje nod ur `list_nodes`,
   flyttad till komponentens ram
3. jämför

| Utfall | Följd |
|---|---|
| `A ⊇ B` inom 1 mm | rotnodens låda duger, designen står |
| `A ⊂ B` | **rotnodens låda är fel storhet.** `Bounds` måste byggas ur nodunionen, och varje tidigare mätning med `get_bounds` ska räknas om |

Ett resultat där A och B är lika STORA men olika placerade är också ett fel,
och det ska skiljas från de två raderna ovan i stället för att avrundas in i
den ena.

## Steg 3 — beror lådan på ställningen?

Läs `get_bounds` på en robot, kör en led till halva sitt utslag med
`set_joints`, läs igen.

Förväntat: lådan ändras. M-61 visade att 29 405 leder finns i biblioteket och
att varje geometri i en robotarm sitter bakom ett uttryck.

**Om lådan ändras är "komponentens låda" inte en storhet utan en funktion**,
och då måste varje låda i bygget bära den ställning den lästes vid. Det är en
kolumn i `Bindning`, inte en fotnot.

Ställningen som ska användas i steg 6: **komponentens läge direkt efter
inladdning**, oförändrat, och det ska stå i utdatan.

## Steg 4 — beror lådan på parametrarna?

`set_property(component, "ConveyorLength", 2000)` på en transportör, läs
`get_bounds` före och efter.

Förväntat: ja. Då är slutsatsen att **lådan hör till instansen, inte till
katalogposten**, och att ett cachat mått måste nycklas på VCID *plus*
parametervärden — inte på VCID ensamt.

## Steg 5 — var ligger origo?

`get_bounds` ger `center` i nodens egen ram. Är `center` skilt från noll ligger
komponentens origo inte i lådans mitt.

`Ankare.ur_bounds` finns för just det, och `till_verktygsanrop(strikt=True)`
vägrar redan skriva ett anrop ur ett ANTAGET ankare. Steget mäter hur stor
förskjutningen faktiskt är, per kategori, så att det går att säga vad ett
antaget ankare hade kostat i millimeter.

## Steg 6 — samma 18 layouter, riktiga komponenter

För varje scen i `provscener.PROVSCENER`:

1. välj en riktig komponent per objekt ur katalogindexet
2. `load_component`, `get_bounds`, `Bounds.ur_svar`
3. `objekt_ur_komponent(fakta, bounds=...)` — bygger objektet med VC:s mått,
   komponentens egen kategori och räckvidden ur filen
4. `losa(scen, relationer)`
5. `till_verktygsanrop(scen, strikt=True, komponentnamn=...)` — **strikt**, för
   ankarna är nu MÄTTA
6. kör anropen, `update()` + `sim.update()`, mät med `measureDistance` (M-36)

| Krav | Utfall som räknas som grönt |
|---|---|
| noll kollisioner | varje par > 0 mm, utom de par scenen deklarerat som `Pa` |
| varje scen har ett svar | `LOST`, eller ett SKÄL. Aldrig tystnad |
| VC dömer, inte motorn | avstånden kommer ur `measureDistance` |

**En scen som inte längre går att lösa är inte ett fel i körningen.** Det är
resultatet. Fas 5:s gröna svar byggdes på lådor som var för små, och en scen
som faller när måtten blir riktiga är precis det den här körningen finns för
att hitta. Den ska redovisas som `RYMS_INTE med skäl`, med lådans mått bredvid
det antagna, inte som ett misslyckande.

## Steg 7 — heter gränssnitten samma sak i VC som i filen?

`list_interfaces(component)` mot `komponentfil.las(...).granssnittsnamn()`.

Det är en **grind på den offline-läsningen**, inte på VC. Skiljer sig namnen
har `komponentfil.py` läst fel, och då är M-61:s tal om 11 563 gränssnitt inte
värda något.

Krav: mängderna är **identiska**, inte överlappande. Ett extra namn i endera
riktningen är rött.

Samma prov för ramarna: `list_frames` mot `ramnamn()`.

## Steg 8 — går de föreslagna paren att koppla?

`kopplingsbara(a, b)` föreslår par ur två regler som är LÄSTA ur filerna:
flöde ut→in, och montering `Mount 1` → `Mount 0`. Att VC håller med går bara
att veta genom att fråga VC.

| Prov | Krav |
|---|---|
| varje föreslaget par | `can_connect` sant, `connect` sant, `IsConnected` sant |
| **par regeln avvisar** | `can_connect` FALSKT |

Den andra raden bär hela provet. En regel som bara prövas på par den själv
föreslår kan vara hur tillåtande som helst utan att någonsin bli röd.

Minst tre avvisade par ska prövas:

* två transportörers `InInterface` mot varandra (port 0 mot port 0)
* två robotars `Tool` mot varandra (`Mount 1` mot `Mount 1`)
* en robots `Tool` mot en transportörs `InInterface` (olika fälttyper)

`Container`-bindningen från M-37 gäller fortfarande: ett flödesfält utan sin
`Container` ger falskt utan att säga varför.

## Steg 9 — räckvidden och lederna

| Ur filen (M-61) | Ur VC | Krav |
|---|---|---|
| `Reach` / profilens största radie | `check_reach` | samma tal inom 10 mm |
| ledernas namn och gränser | `get_joints` | identiska namn, gränser inom 0,1 |

De 225 robotar där `Reach` är tomt eller noll men profilen ger ett tal är den
intressanta raden: håller profilen mot VC är hålet fyllt, och håller den inte
ska `rackvidd_ur_fakta` sluta härleda.

## Steg 10 — transportörens riktning

`flode_ur_fakta` läser **ordningen** (vilket gränssnitt tar emot, vilket lämnar
ifrån sig) men lämnar **riktningen** som `None`, för ramarnas läge är
parametriskt i 303 av 324 fall.

| Ur filen | Ur VC | Krav |
|---|---|---|
| `flode.in_granssnitt` / `ut_granssnitt` | `list_flow_connectors` | samma namn, samma roller |
| `flode.riktning_mm` = `None` | `get_transform` på ramarna via `list_frames` | VC ska ge ett läge där filen inte kan |

Den andra raden är den som betyder något: om VC svarar med ramlägen är
riktningen **hämtbar men inte läsbar**, och då hör den till `Bindning` vid
sidan av lådan — inte till filen.

## De trasiga fallen

Utan dem betyder ingen grön rad ovan någonting.

| Fall | Vad som ska hända |
|---|---|
| en komponent vars `get_bounds` inte lästs | `till_verktygsanrop(strikt=True)` **vägrar**, med namnet på komponenten. Den får inte hamna i origo |
| två komponenter medvetet inne i varandra | `measureDistance` faller, som i fas 5 |
| en layout som lådorna löste och de riktiga måtten inte löser | `RYMS_INTE` **med skäl**, inte en tyst placering |
| ett gränssnittspar regeln avvisar | `can_connect` falskt |
| en komponent som inte laddar | räknas som olaslig, körningen fortsätter, talet står i rapporten |

## Vad körningen INTE avgör

* **Windows.** Allt körs under Wine, som allt annat.
* **Att något flödar.** Gränssnitten kopplas; att en produkt vandrar igenom
  dem är fas 6 och 7.
* **Om lådan är rätt.** `get_bounds` är VC:s svar, och VC är domaren vi har.
  Att jämföra den med tillverkarens datablad är en annan mätning.
* **Alla 3201.** Körningen är ett urval. Nämnaren ska stå i rapporten.
