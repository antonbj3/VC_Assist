# 56 — språket i koden, och planen för att reda ut det

Repot är skrivet på svenska. Det var ett val som aldrig fattades medvetet, och
kostnaden växer med varje timme. Den här filen säger vad som gäller tills den
är betald.

## Vad det kostar, mätt

| | |
|---|---|
| kod | 159 000 rader |
| dokumentation | 39 000 rader |
| **strängar som skrivs ut till en användare** | **560** |
| domsord ögat lämnar ifrån sig | 8 |

De 560 och de åtta är produktens **yta**. Resten ser bara vi.

Och svenskan läcker redan: `ORORD_SIGNAL`, `DUBBELSKRIVNING`, `VALET_FALLER`,
`SAKNAS`, `facit_spar` står i domar och felmeddelanden, inte bara i källkoden.
En användare möter dem.

## Den värsta blandningen är inte språk, det är storheter

Tre storheter läses alla som "en massa i kilo", och de betyder helt olika saker:

| storhet | vad det är |
|---|---|
| `egenvikt` | vad komponenten själv väger |
| `nyttolast` | vad den kan bära |
| `verktygslast` | gripdonets massa, som dras **från** nyttolasten |

Databladslagret håller dem isär — alla tre finns i `STORHETER`, och en robot
bär alla tre. **Villkorsspråket gör det inte:** `del.<roll>.massa_kg` är
komponentens egen massa, och ett nyttolastkrav går inte att uttrycka. `M-163`
mätte att `MaxPayload` deklareras i 2 358 av 3 201 katalogposter och aldrig når
grinden.

Att dimensionera en cell på robotens egenvikt i tron att det är dess bärförmåga
är inte ett stavfel. Det är fel robot på golvet.

**Regeln:** två storheter som delar enhet men inte betydelse får aldrig dela
namn, och aldrig fältnamn som skiljer sig med ett ord. Hellre `bar_last_kg` och
`egen_massa_kg` än `payload` och `mass`.

## Modellens tal eller den fysiska robotens

Samma fälla ett lager upp. `datablad.py` läser ur `.vcmx` — det är vad den
**simulerade** roboten gör. Tillverkarens datablad säger vad den **fysiska**
gör. De skiljer sig: `M-107` ställde 25 komponenter bredvid varandra och fann
sex fält som inte stämmer, bland dem UR10e där VC skriver `12` och Universal
Robots skriver `12,5 kg`.

Källtypen bärs redan per värde (`kalltyp`: `"model.xml"` eller `"tillverkarens
datablad"`). **Men motsägelsen avgörs tyst** — berikningen låter tillverkarens
tal vinna utan att säga att de sa olika. Det är ett öppet motbevis i `M-107`.

**Regeln:** ett tal ur modellen och ett tal ur ett datablad är två olika
storheter tills någon mätt att de är samma. Skiljer de sig ska båda visas med
sin källa, aldrig det ena tyst.

## Planen för språket, i ordning

**1. Ytan — de 560 strängarna och de åtta domsorden.** En dag, mekaniskt, och
hela skillnaden för en användare:

```
forregling → interlock      genomflode → throughput
sekvens    → sequence       geometri   → geometry
grepp      → grasp          hederlighet→ integrity
kapplopning→ race           timing     → timing
SAKNAS     → MISSING
```

**2. Identifierarna.** 159 000 rader låter ohanterligt, men sviten bär 7 800
prov och **den är kontrollen**. En mekanisk omdöpning med sviten som grind är
inte ett äventyr. Görs efter ytan, aldrig samtidigt.

**3. Dokumentationen sist, eller aldrig.** Där ligger resonemangen, och en
översättning tappar nyansen. Specindexet kan översättas; mätningarna är
arbetsjournaler och behöver det inte.

## Vad som gäller tills dess

* **Nya användarvända strängar skrivs på engelska.** Skulden ska inte växa.
* **Nya identifierare får vara svenska** så länge modulen de bor i är det —
  en halvöversatt fil är sämre än en konsekvent.
* **Ingen översättning medan flera sessioner skriver i samma filer.**
