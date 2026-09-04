# M-60 — vad ett katalogsvar kostar, och varför en bred fråga inte får en lista

**Datum:** 2026-09-04 · indexet ur M-57, djupt läge
**Byggd av:** `svc/vc_assist_svc/katalogsok.py`
**Kravet:** operatören, ordagrant — *"Informationen måste vara lättillgänglig
för LLM, kom ihåg det."*

## Problemet i ett tal

| | tecken |
|---|---:|
| hela indexet som fil | **4 285 371** |
| översikten över hela katalogen | **600** |
| ett svar på en smal fråga | 226–527 |
| ett fullt datablad för en komponent | 1 011 |

Ett korrekt index som kostar 4,3 miljoner tecken att läsa är oanvändbart för en
agent. Den läser det inte — den gissar i stället, vilket är precis vad indexet
skulle förhindra. **Korrekt räcker inte. Det måste också vara billigt.**

## Mätt kostnad per frågetyp

| Fråga | träffar | visade | tecken |
|---|---:|---:|---:|
| `namn ~ "IRB 6700"` | 15 | 10 | **527** |
| `tillverkare=Qimarox, kategori=Conveyors` | 4 | 4 | **226** |
| `kategori=Robots` | 2169 | **0** | **654** |
| hela katalogen | 3201 | **0** | **652** |
| `namn ~ "finns-inte-alls"` | 0 | 0 | **39** |

Notera raderna där `visade = 0`. En fråga som träffar 2169 komponenter får
**inte** en lista. Att rada upp dem vore att bränna agentens kontext på det den
inte frågade efter. Svaret blir i stället fördelningen per tillverkare och en
uppmaning att smalna av — 654 tecken i stället för uppskattningsvis 100 000.

Det är samma doktrin som `25_kontextbudget.md` ställer på trimning: **ingen
bortprioritering är tyst.** Svaret säger alltid hur många träffar som fanns och
hur många som visades.

## Tre regler formen följer

1. **En träfflista är rader, inte JSON.** Ett fast antal fält per rad.
   Klammer och citattecken är tecken som inte bär information.
2. **En bred fråga får ett sammandrag.** Gränsen är `BRED_FRAGA = 40`.
3. **Ett fält datan inte bär säger `saknas`.** Aldrig noll, aldrig tomt, aldrig
   utelämnat. Ett utelämnat fält läses som noll av både människor och modeller,
   och då har indexet ljugit tyst.

## Trösklarna

`MAX_RADER = 10`: en rad är 40–70 tecken, så tio rader är under 700 — i
storleksordningen ett par hundra tokens, vilket ryms i posten *verktygsresultat*
(`25_kontextbudget.md`, post 8, 25 % av budgeten) utan att tränga ut något.

`BRED_FRAGA = 40`: över det är en lista meningslös oavsett tak. Agenten har
frågat för brett, och det är den upplysningen den behöver — inte fyrtio rader.

## Varför ingen databas, mätt och inte principiellt

3201 poster är litet. En linjär genomsökning tar millisekunder. En databas
förtjänar sin plats när datan ska överleva processen, delas mellan processer,
eller inte får plats i minnet; inget av det gäller.

En grafdatabas skulle inte göra något billigare heller — den skulle flytta samma
påse parametrar till en annan lagringsform. Det **grafformade** problemet är
vilka komponenter som går att koppla ihop, och 3201 noder är litet nog att hålla
i minnet.

Det svåra är inte lagringen utan **ordförrådet**: 1806 unika parameternamn utan
gemensamt schema (M-57). En agent som frågar efter ett grepdon för 5 kg hittar
inget `Payload`-fält, för det finns inte. Det löses av en mätt avbildning från
storhet till parameternamn — databladslagret — inte av en databas.

## Vad som INTE är mätt

* **Tokens, inte tecken.** Alla tal ovan är tecken. En tokenräknare för den
  faktiska modellen är inte körd; tumregeln fyra tecken per token är en
  tumregel.
* **Om tio rader räcker.** `MAX_RADER = 10` är satt på kostnad, inte på hur ofta
  en agent behöver den elfte.
* **Rangordningen.** Träffar sorteras på kortast namn först, vilket är rätt för
  *"IRB 120"* mot *"IRB 120-3/0.6 LID"*. Om det är rätt regel i allmänhet är
  inte mätt.
