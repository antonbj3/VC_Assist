# M-76 — katalogposten fanns hela tiden, i en fil på två kilobyte

**Datum:** 2026-09-05 · biblioteket ur M-57, 3201 komponenter
**Rättar:** `M-58` (vad "kategori" är i grunt läge) och `M-59`:s slutsats om
räckvidden.
**Ursprung:** ett sidofynd i `M-63`, gjort av planeringslagrets mätning.

## Fyndet

En `.vcmx` bär **två** metadataposter, inte en:

| Post | storlek | innehåll |
|---|---:|---|
| `component.rsc` | 200–300 kB | komponentens inre: beteenden, gränssnitt, parametrar |
| **`model.xml`** | **2–3 kB** | **de deklarerade katalogfälten** |

Jag läste bara den första. Den andra fanns i **3201 av 3201** komponenter, och
hela biblioteket läses ur den på **0,5 sekunder**.

## Vad den deklarerar

| Fält | bärs av | andel |
|---|---:|---:|
| `VCID`, `ModelType`, `Name`, `Type`, `Manufacturer`, `Revision`, `IsDeprecated` | 3201 | **100 %** |
| `MaxPayload` | 2986 | 93 % |
| `Author` | 2866 | 90 % |
| `Tags` | 2790 | 87 % |
| **`Reach`** | **2556** | **80 %** |

`IsDeprecated = True` för **73** komponenter — utfasade av tillverkaren, och
serverade av oss utan att någon visste.

## Vad det rättar

**`M-58` sa:** *"i grunt läge kommer `kategori` från katalognamnet, inte ur
metadatans eget `Category`-fält — två olika storheter."* Det stämde för den
koden. Men `Type` är **deklarerad** i katalogposten, och ger samma tal som den
djupa läsningen: Robots 2169, Conveyors 163. Grunt läge läser nu det fältet, och
den varningen gäller inte längre.

**`M-59` sa:** räckvidden är *härledd* för 1693 robotar och *saknas* för 509,
med noll lästa. Formeln kalibrerades mot tillverkarnamnen och landade på median
1,001. Ett gott arbete — mot ett fält som fanns deklarerat i 2556 komponenter.

**Tillverkaren** kom ur katalogträdet. Nu ur `Manufacturer`, deklarerad i 100 %.

## Kostnaden vändes

| | före | efter |
|---|---:|---:|
| grunt index | 1,8 s | **0,8 s** |
| och bar då | namn, katalognamn som kategori och tillverkare | + VCID, deklarerad Type och Manufacturer, Reach, MaxPayload, Tags, Revision, utfasad |
| djupt index | 12,8 s | 12,8 s (familj, gränssnitt, parametrar) |

Det grunda indexet är alltså nu **rikare än det gamla djupa** på allt utom
familj, gränssnitt och parametrar — och sexton gånger snabbare.

## Vad agenten kan fråga nu

```
familj = robot, rackvidd >= 3000 mm, nyttolast >= 200 kg
  -> 128 traffar, 483 tecken, fordelade per tillverkare
     KUKA 52 · Fanuc 24 · ABB 21 · Kawasaki 14 · Hyundai 6 …
```

Ett fält som saknas slår bort komponenten ur filtret. Den har **inte** räckvidden
noll; den saknar fältet, och det är två olika saker.

## Fjärde gången samma felklass

`M-34` räknade fel lista tolv gånger. `M-57` sökte i installationskatalogen
medan biblioteket låg i Public Documents. `M-69` filtrerade på katalognamn i
stället för struktur. Och nu detta: tre deklarerade fält låg i en fil på två
kilobyte medan vi härledde två av dem ur länklängder och gissade det tredje ur
en mappstruktur.

Alla fyra har samma form. **Ett tal som såg rimligt ut, från ett ställe ingen
hade frågat om det var rätt ställe.**

Och det här hittades inte av mig, utan av planeringslagrets mätning som råkade
behöva räckvidden och öppnade en annan fil. Det är andra gången i natt en annan
mätning fångar ett fel i min egen kod. **Två oberoende räkningar av samma sak är
det enda som fångar en räkning som är konsekvent fel.**

## Vad som INTE är mätt

* **Om de deklarerade fälten är sanna.** De är tillverkarens uppgift om sin egen
  komponent. Ingen har jämfört `Reach` mot geometrin.
* **De 645 utan `Reach`.** Vilka de är och varför fältet saknas är inte
  undersökt. `M-59`:s härledning ur länklängder är fortfarande den enda vägen
  för dem — och den är kalibrerad mot modellnamn, inte mot mätning.
* **`Description` läses inte.** Den är hundratals ord bruksanvisning per
  komponent och skulle femdubbla indexet utan att hjälpa någon att välja.
* **`ModelType`, `Author`, `Website`, `Email`, `Modified`** läses inte heller.
  De kan bära något; ingen har frågat.
