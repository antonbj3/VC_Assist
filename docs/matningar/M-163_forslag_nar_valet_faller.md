# M-163 — förslag när valet faller: vad grinden kan namnge, och var sökskiktet tar slut

**Datum:** 2026-09-05
**Rigg:** `docs/matningar/radata/m163_forslag.py` mot det installerade
biblioteket i `~/.wine-vc-test/.../Visual Components/4.10/Models/Components`
(3 201 komponenter, grunt index byggt på 0,8 s, noll olästa filer). Proven i
`tests/enhet/test_forslag_valet_faller.py` kör helt utan bibliotek, mot en
attrapp av sökskiktets publika yta. Kod: `svc/vc_assist_svc/plan/forslag.py`,
inkopplad i `plan/motsagelse.py` (grind 3) och `plan/bestallning.py`.
**Prövar:** kan motsägelsegrinden namnge de komponenter som faktiskt uppfyller
det krav den valda komponenten inte klarar — med talet som avgjorde och dess
härkomst — och vad händer när den inte kan?

## 1. Vad som stod där före

`motsagelse.py` har fyra domar och ingen heter "möjlig". `VALET_FALLER` betyder
per definition att villkoren **går** att uppfylla, bara inte med den valda
komponenten. Domen vet alltså redan att ett alternativ finns. Ändå sade den
bara vilken *sorts* åtgärd som behövdes:

```
atgard: kravet gar att uppfylla, men inte med den har komponenten.
        Byt komponent - eller mjuka upp kravet
```

Aldrig **vilken** maskin. Operatören fick domen och hela sökningen kvar — i ett
bibliotek på 3 201 komponenter, efter något som grinden redan hade talen för att
hitta.

## 2. Vad grinden svarar nu

Beställning: robot ska nå 2 050 mm, den valda når 1 650 mm. Ordagrann utdata
(`radata` avsnitt 5):

```
MOTSAGELSE VALET_FALLER
MK2_VARDE_MOT_VILLKOR: del.robot.rackvidd_mm = 1650 mm (databladet for robot),
                       kravet var ge 2050 mm
    atgard: kravet gar att uppfylla, men inte med den har komponenten. ...
    FORSLAG for del.robot.rackvidd_mm (rollen robot), kravet ar ge 2050 mm
    MINSTA SOM RACKER FORST: en komponent med dubbel rackvidd uppfyller samma
      krav men tar mer golv, och golvytan ar just det MK3 och MK4 mater. ...
    1. RV-35F (Mitsubishi Electric), rackvidden 2050 mm - uppfyller ge 2050 mm
       [ur RV-35F.vcmx]
    2. RV-50F (Mitsubishi Electric), rackvidden 2050 mm - uppfyller ge 2050 mm
       [ur RV-50F.vcmx]
    3. RV-70F (Mitsubishi Electric), rackvidden 2050 mm - uppfyller ge 2050 mm
       [ur RV-70F.vcmx]
    Sokvagarna ovan star under <bibliotek>/Mitsubishi Electric/Robots/
    Talet kommer ur sokskiktets falt rackvidd_mm, som ar katalogpostens
      deklarerade "Reach" (M-76 matte det i 80 % av biblioteket) ...
    391 av 513 traffar gick inte att rakna upp ... sa listan ar de minsta bland
      de 122 som gick - inte bevisat de minsta i hela biblioteket. Den forsta
      ar dock ett bevisat minimum: den traffar gransen exakt.
    Sokskiktet: 513 traffar pa kravet, 122 uppraknade, 391 kunde inte raknas upp.
```

Kostnaden: **24 sökfrågor, 4 ms**. Grind 3 kostade mikrosekunder förut och
kostar millisekunder nu; grind 5 (layoutmotorn) kostar upp till fyra sekunder
(M-63). Ordningen mellan dem är alltså orörd.

## 3. Sökskiktet räcker inte hela vägen, och det är mätt

Det här är fyndet som styrde hela konstruktionen. `katalogsok` vägrar med flit
lista en bred fråga: över `BRED_FRAGA` = 40 träffar lämnar den ett *sammandrag*
per tillverkare och **noll rader** (M-60). Det är rätt av sökskiktet — 513 rader
är inget svar — men det betyder att ett förslag inte kan räkna upp träffmängden.

| krav | träffar | rader | sammandrag |
|---|---|---|---|
| räckvidd ≥ 1 500 mm | 722 | 0 | ja, 37 tillverkare |
| räckvidd ≥ 2 050 mm | 513 | 0 | ja, 23 tillverkare |
| räckvidd ≥ 2 500 mm | 429 | 0 | ja, 18 tillverkare |
| räckvidd ≥ 3 200 mm | 114 | 0 | ja, 11 tillverkare |
| räckvidd ≥ 9 000 mm | 0 | 0 | nej |

Förslaget följer då sökskiktets **egen** uppmaning ("smalna av med
tillverkare") och frågar om per tillverkare. Det räcker en bit, inte hela vägen:

| krav | träffar | uppräknade | ej uppräknade | frågor | tid |
|---|---|---|---|---|---|
| ≥ 2 050 mm | 513 | 122 | 391 | 24 | 4 ms |
| ≥ 2 500 mm | 429 | 89 | 340 | 19 | 3 ms |
| ≥ 3 200 mm | 114 | 59 | 55 | 12 | 2 ms |

KUKA (179 träffar), Fanuc (89), ABB (75) och Kawasaki (52) är själva bredare än
40 och lämnar sammandrag också som enskilda tillverkare. **Följden för
ärligheten:** förslaget får aldrig påstå "de tre minsta i biblioteket". Det
säger "de minsta bland de 122 som gick att räkna upp" och skriver ut de 391 det
inte såg.

**Ett undantag går ändå att bevisa.** Träffar det minsta uppräknade värdet
gränsen exakt — 2 050 mm mot kravet `ge 2050` — kan ingen ouppräknad post ligga
lägre och ändå hålla kravet. Den första raden är då ett bevisat minimum trots
halv uppräkning, och grinden säger det.

## 4. Familjefiltret var en fälla

Det första naturliga draget är att filtrera på `familj="robot"`. Mätt:

```
index djupt:            False
sok(familj="robot"):    0 traffar av 3201 poster
```

Familjen fylls bara i ett **djupt** index — markören ligger vid median 14 215
byte och nås inte av den grunda läsningens 4 096 (M-69). Ett förslag som
filtrerat på familj hade alltså svarat *"ingenting i biblioteket räcker"* om ett
fullt bibliotek, vilket är exakt den tysta falska nollan hela projektet är byggt
mot. Frågan bär därför bara det numeriska kravet.

## 5. Vad ett förslag kostar i tecken

Taket `MAX_FORSLAG = 3` är **ställt, inte mätt** — uppdraget säger "högst en
handfull". Det som är mätt är vad raderna kostar (radata avsnitt 6):

| förslag | förslagsblocket | hela krocken |
|---|---|---|
| 0 | — | 784 tecken |
| 1 | 1 191 | 1 658 |
| 2 | 1 310 | 1 781 |
| 3 | 1 429 | 1 904 |
| 5 | 1 637 | 2 120 |
| 10 | 2 203 | 2 706 |

Fast kostnad 1 072 tecken (rubrik, sorteringsmotiv, fältkälla, förbehåll), 119
tecken per rad. Första utkastet kostade **231** tecken per rad: varje rad bar
hela katalogsökvägen, 130 tecken av dem identiska mellan raderna. Tre likadana
sökvägsprefix är inte tre härkomster — det är en härkomst och 260 tecken brus.
Roten skrivs nu en gång och raderna relativt den.

## 6. De trasiga fixturerna

Skrivna före mekanismen (`tests/enhet/test_forslag_valet_faller.py`, avsnitt F).

**F1 — inget i biblioteket räcker.** Krav 9 000 mm:

```
FORSLAG for del.robot.rackvidd_mm (rollen robot), kravet ar ge 9000 mm
0 av 3128 poster som sokskiktet visar (utfasade raknas inte) uppfyller
ge 9000 mm. 1430 av dem deklarerar rackvidden alls; resten bar inget tal och
far darfor aldrig foreslas. Kravet star kvar som uppfyllbart - biblioteket ar
inte varlden, och en komponent som klarar det kan finnas utanfor den har
installationen.
```

Domen står kvar på `VALET_FALLER`, inte `OMOJLIG`, och det är med flit:
biblioteket är inte världen. Svaret bär två tal med härkomst — 0 av 3 128 och
1 430 av 3 128 — i stället för en tom lista.

**F3/F4 — `OMOJLIG` och `OKANT` föreslår aldrig.** Spärren är strukturell:
förslagssteget körs först när hela domen är `VALET_FALLER`. Mätt i proven:
sökporten får **noll** frågor i båda fallen. Ett förslag under `OMOJLIG` hade
sagt åt operatören att felet ligger i valet när det ligger i kraven.

## 7. Att proven biter

Sex mutationer av mekanismen, var och en körd mot hela provfilen:

| mutation | fångad av |
|---|---|
| kravfiltret bortkopplat | `test_B5` (övre gräns) |
| poster utan tal släpps in som 0 | `test_B8` (grinden prövar själv talet) |
| domspärren bortkopplad | `test_F3` (OMOJLIG föreslår aldrig) |
| tomma tillverkarnyckeln behandlas som vanlig | `test_B9` |
| `MAX_FORSLAG` borttaget | `test_A3` |
| sorteringen omvänd | `test_A1`, `A4`, `A5` |

`test_A6` är det starkaste: varje föreslaget alternativ körs tillbaka genom
grinden och måste sluta falla. Ett förslag som inte självt håller kravet är
sämre än inget förslag — då har grinden skickat operatören på en andra vända.

## 8. Två observationer som inte var uppdraget

* **Nyttolasten når aldrig fram.** Katalogposten deklarerar `MaxPayload` i
  2 358 av 3 201 poster (93 % enligt M-76), `forfining._blad` skriver in den i
  databladet — och ingen storhet i det slutna språket läser den.
  `del.<roll>.massa_kg` är komponentens **egen** massa, inte vad den orkar
  lyfta. Ett nyttolastkrav går alltså inte att uttrycka i dag, och att koppla
  massakravet till `MaxPayload` vore att låta en parameter bära två storheter.
  Förslagsmodulen avstår därför med skälet utskrivet i stället för att gissa.
* **Räckvidden finns i 1 437 av 3 201 poster** i det grunda indexet (M-63 sa
  0 av 2 169 ur `component.rsc`; skillnaden är att katalogposten `model.xml`
  läses sedan M-76).

## LIMITS

* **Ett förslag är inte ett löfte om en byggbar plan.** Det påstår exakt en sak:
  komponenten uppfyller det villkor som föll. Passformen (MK4) och ytbeviset
  (MK3) mäter fotavtrycket, som härleds ur räckvidden med `ROBOTFOT_ANDEL =
  0,30` — ett antaget tal, inte ett mätt. En större robot kan alltså falla på
  ytan i stället. Ingen mätning här visar hur ofta det händer.
* **Minimaliteten är bevisad bara i randfallet.** När det minsta uppräknade
  värdet ligger *över* kravets gräns är "minst" ett påstående om de 122 som
  gick att räkna upp, inte om de 513. Talen står utskrivna, men de 391 är inte
  undersökta.
* **Bara räckvidden är sökbar.** Ett fallet val på längd, bredd, höjd, yta eller
  massa får ett skäl, aldrig ett namn. Det är inte en begränsning i den här
  koden utan i katalogposten (M-61: inga yttermått) och i sökskiktets filter.
* **Mätt på ett grunt index.** Ett djupt index (parametrar och familj) är inte
  prövat med förslagen. Det skulle göra familjefiltret användbart och därmed
  ändra både träffantalet och uppräkningsgraden — åt vilket håll är inte mätt.
* **Ingen mätning av nyttan.** Att förslagen är korrekta och spårbara är mätt.
  Att de leder operatören snabbare rätt än ett "byt komponent" är **inte** mätt,
  och kan inte mätas utan en operatör.
* **Sökskiktet lagades inte här.** Träffgraden i komponentsöket (M-161) ägs av
  ett annat spår. Den här mätningen kördes mot sökskiktet som det stod
  2026-09-05 kl. 20 och tog inte i `katalogsok.py` eller `katalogindex.py`.
* **Talet 3 är inte mätt.** `MAX_FORSLAG = 3` är ställt i uppdraget. Teckentabellen
  ovan säger vad andra tal hade kostat, inte vilket som är rätt.
