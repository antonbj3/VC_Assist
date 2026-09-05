# 51 — Komponentdata: vad VC:s filer ger, och var resten kommer ifrån

`M-85` mätte hela biblioteket: **3 201 komponenter, 82 383 egenskaper**. Slutsatsen
delar sig rent på mitten.

**Strukturen är välfylld.** 100 % av databladen går att läsa. 96,1 % bär egna
egenskaper, 97,7 % beteenden, 93,8 % gränssnitt, 86,5 % leder. Standardvärde
finns på 94,5 % av egenskaperna.

**Semantiken är det inte.** Bara **14,0 %** av egenskaperna deklarerar vilken
**storhet** de bär.

Det här dokumentet säger vad som följer av det.

---

## 1. Regeln: en enhet härleds aldrig ur ett värde

En transportör vars `SpeedIn` står på `820` säger inte om det är mm/s, m/min
eller något annat. VC:s världsenhet är millimeter, så en gissning åt fel håll
blir ett fel på faktor 60 — och det ser rimligt ut i båda riktningarna.

Databladet skriver därför `storhet saknas` och lämnar talet naket. Det är
avsiktligt och får inte "förbättras": ett tal med påhittad enhet är farligare
än ett tal utan, eftersom det ser färdigt ut.

Samma regel med ett skarpare fall: `MaxPayload` står i katalogposten i **2 986
av 3 201** komponenter, **utan enhet**, och **628 av dem har värdet `0`**. En
nolla utan enhet är inte en nyttolast på noll kilo. Det är ett ofyllt fält.
Skrivs den ut som "0 kg" har vi tillverkat ett faktum.

---

## 2. De tre källorna, och vad var och en får svara på

| Källa | Vad den ger | Vad den INTE ger |
|---|---|---|
| `model.xml` i `.vcmx` | katalogfält: familj, tillverkare, `MaxPayload`, `Reach` | enheter, giltighetsintervall |
| `component.rsc` | egenskaper med namn, typ, standardvärde; beteenden; gränssnitt; leder | storhet i 86 % av fallen |
| **tillverkarens publicerade datablad** | nyttolast, räckvidd, repeterbarhet, hastighet — **med enhet** | vad komponenten heter invändigt i VC |

De två första är VC:s. Den tredje är utanför, och den är **enda** vägen till en
enhet som inte är gissad.

En hämtad uppgift bär alltid tre saker: **värdet, enheten, och varifrån den
kom**. En siffras härkomst hör till siffran. Ett datablad utan källa är ett
påstående.

---

## 3. Vad enheter gör möjligt, och det är hela poängen

Utan enhet kan ingen grind döma ett tal. Med enhet kan den:

* avvisa en cell där nyttolasten överskrider robotens — `12,0 kg` mot
  `180 kg` är en jämförelse; `12,0` mot `180` är två tal.
* avvisa en räckvidd som inte når — bänkens `arbetsradie_mm` mot databladets
  `Reach`.
* räkna ett facit ur geometri, vilket är den näst starkaste facitkällan i
  `85_bankkontraktet.md` §2.

Det tredje är kopplingen till bänken: **industriexempel som ska vara korrekta
behöver komponenter med riktiga tal.**

---

## 4. Vad som händer när en uppgift saknas

Fail-closed, och skillnaden mellan de tre lägena är inte kosmetisk:

| Läge | Vad det betyder | Vad som får hända |
|---|---|---|
| `finns` | värde och enhet, med källa | grinden får döma på det |
| `saknas` | fältet finns inte i någon källa | grinden **avstår**, och säger att den avstår |
| `enhet_saknas` | värdet finns, enheten inte | talet får visas **ordagrant**, aldrig jämföras |

Det tredje läget är det som glöms. Ett tal utan enhet som jämförs med ett tal
med enhet är ett fel som ser ut som ett svar.

---

## 5. Vad berikningen ger, och var den tar slut

Berikningen är **byggd** (`M-107`): `svc/vc_assist_svc/tillverkardatablad.py`
och korpusen i `data/tillverkardatablad/`. De tre lägena i §4 är tre lägen i
koden, och skillnaden bärs av konstruktorer:

* `finns` kräver värde, enhet **och** källa. En `Kalla` utan url, hämtdatum,
  sha256 och ordagrant citat går inte att bygga.
* `enhet_saknas` bär **inget talvärde alls**, bara strängen `ordagrant`. Det är
  poängen: `svar.varde` är `None`, så det finns inget tal att räkna på av
  misstag. En float hade varit en märkning man kan glömma.
* `saknas` måste säga vad som letades efter.

Enheten kan aldrig härledas ur värdet. Talet och enheten ska stå **bredvid
varandra i ett ordagrant citat** ur den hämtade källan — `MaxPayload: 180` går
inte att göra till `180 kg` genom att skriva dit `kg`. För tabeller vars enhet
står i rubriken (`Handling capacity (kg)`) finns ett andra, svagare läge vars
koppling kontrolleras positionellt mot både rubrik och rad, och varje sådant
svar skriver ut att det är positionsläst.

Jämförelsen heter `rymmer()` och inte `racker()`, och den **avstår** så snart
någon sida inte är `finns`.

### Vad talen blev

| | `finns` | `enhet_saknas` | `saknas` |
|---|---|---|---|
| nyttolast, 3 201 komponenter | **21** | **2 965** | 215 |
| räckvidd | 19 | 2 542 | 640 |

Korpusen bär 28 modeller och 52 belagda uppgifter ur tolv dokument från fem
tillverkare. Biblioteket har 2 202 robotar och 2 175 distinkta modellnamn.
**Mekanismen finns; biblioteket är inte berikat**, och skillnaden är två
storleksordningar.

Alla 628 komponenter med `MaxPayload = 0` svarar `ENHET SAKNAS … ett ofyllt
fält`. Ingen skriver `0 kg`. Samma sak för de 1 115 med `Reach = 0`.

### Vad som INTE är gjort

* **Täckningen.** 0,66 % av biblioteket har en enhet med källa.
* **`katalogsok.Traff.rad` fäster fortfarande `mm` och `kg`** vid samma
  enhetslösa katalogfält, och skriver `0 kg` för de 628 nollorna. Grinden i det
  nya lagret skyddar inte sökskiktet, och det är sökskiktet modellen läser.
* **Bankens 15 `PUBLICERAD_SPEC`-poster bär ingen URL.** Stämpeln lovar
  tillverkarens publicerade datablad; posten bär bara talet.
* **Sex fält där VC:s katalogfält motsäger den citerade källan passerar tyst**
  — bland dem `UR10e` med `MaxPayload 12` mot Universal Robots 12,5 kg.
* **Enhetsgrinden mäter närhet, inte betydelse.** En diameter går att citera
  som en räckvidd; att det inte har hänt är ett omdöme, inte en grind.

De fem står som röda prov i
`tests/motbevis/test_tillverkardatablad_motbevis.py`.

### Gränsen som gäller även nu när det är byggt

Ett datablad gäller en **modell**, inte en instans. Två robotar av samma typ
med olika verktyg har olika nyttolast kvar. Databladets tal är ett tak, aldrig
ett driftvärde — ett typskyltvärde är en anslutning, inte en förbrukning.
`Domslut.text()` skriver ut den raden i varje dom.
