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

## 5. Vad som INTE är gjort

Berikningen ur tillverkarnas datablad är **specificerad här, inte byggd**.
Talen i §1 är mätta (`M-85`); allt i §2 om den tredje källan är en plan.

Och en gräns som gäller även när den är byggd: ett datablad gäller en
**modell**, inte en instans. Två robotar av samma typ med olika verktyg har
olika nyttolast kvar. Databladets tal är ett tak, aldrig ett driftvärde — ett
typskyltvärde är en anslutning, inte en förbrukning.
