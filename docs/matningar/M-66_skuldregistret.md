# M-66 — teknisk skuld fångad när den skrivs, inte vid en senare granskning

**Datum:** 2026-09-05
**Kravet:** operatören — *"Kom ihåg nu att reviewa och hålla koll på möjlig
teknisk skuld och saker som senare behöver göras om"*, och skärpningen: *"Vi
fångar det at moment of writing föredragsvis."*
**Byggt:** `svc/vc_assist_svc/skuld.py`, `docs/matningar/SKULDREGISTER.md`

## Varför registret genereras och inte förs

Ett register någon måste komma ihåg att uppdatera är redan glömt. Den enda
skuld som hamnar i ett sådant register är den man ändå kom ihåg — alltså inte
den farliga.

Registret förs därför inte. Det **skördas** ur två källor som båda skrivs i
samma andetag som arbetet:

1. **Mätningarnas ärlighetsavsnitt** — *"Vad som INTE är mätt"*, *"Vad som inte
   är prövat"*, *"Vad detta INTE bevisar"* och deras syskon.
2. **Markörer i koden** — `PRELIMINÄR`, `TODO`, *"inte lagat"*, *"öppen punkt"*,
   *"oprövad"*.

Följden är att skulden inte kan glida ifrån verkligheten. Ändrar någon en
mätning ändras registret nästa gång det byggs, och **tar någon bort ett
ärlighetsavsnitt syns det som en minskning** som spärren faller på.

## Talen

| | |
|---|---:|
| punkter ur mätningarnas ärlighetsavsnitt | **74** |
| avsnitt de kom ur | 21 |
| markörer i koden | **100** |
| filer med markörer | 36 |
| **mätningar utan ärlighetsavsnitt** | **24 av 44** |

## Det obekväma talet är det sista

24 av 44 mätningar säger ingenting om vad de **inte** visar.

Nästan alla är skrivna före M-44 — disciplinen satte sig under arbetets gång,
och de tidiga mätningarna bär den inte. M-01 till M-16, M-31 till M-37, M-40.
Två är sena och borde vetat bättre: M-44 och M-47 har ärlighetsinnehåll men
under rubriker mönstret inte känner igen.

En mätning utan ett sådant avsnitt är inte en mätning utan skuld. Det är en
mätning vars skuld ingen har skrivit ned. Det är samma resonemang som
guldgrindens krav på `HONESTY`: regeln är **tom** om sektionen inte finns, och
en rapport utan den såg en gång ut som guld.

Talet är en **spärr som bara får gå nedåt** (`tests/enhet/test_skuld.py`), och
den är dubbelriktad på samma sätt som tröskelskulden: taket får inte heller
ligga *över* verkligheten, för ett tak med luft i slutar fånga nästa glidning.

## Ett mätfel i själva mätningen, värt att skriva ned

Första mönstret hittade 27 mätningar utan avsnitt. En bredare `grep` sa 30 av 43
**hade** ett. De två var oense, och det var mönstret som hade fel: rubrikerna
bär ofta ett nummer först — `## 9. Vad som inte är mätt`, `### F9. Sådant som är
kontrollerat` — och en regex som kräver att rubriken börjar med ordet missar dem
tyst.

Efter rättelsen: 74 punkter i stället för 50, och 24 i stället för 27. Alltså
såg fyra ärliga mätningar ut som slarviga, och 24 punkter försvann ur registret.

En grind som mäter fel storhet rapporterar med full trovärdighet. Det är fjärde
gången samma felklass dyker upp i det här bygget (M-34, M-57, `pgrep -f` som
matchade sin egen sökning, och nu det här), och alla fyra hade samma form: **ett
tal som såg rimligt ut, från ett instrument ingen hade provat mot ett känt
svar.**

## Vad som INTE är mätt

* **Om punkterna är *sanna*.** Registret samlar vad vi skrivit att vi inte vet.
  Det kontrollerar inte att listan är fullständig — en skuld ingen skrev ned
  finns inte i något register.
* **Om markörerna i koden är aktuella.** 100 markörer i 36 filer; hur många som
  redan är åtgärdade men vars kommentar står kvar är inte räknat.
* **Ingen prioritering.** Registret är en sammanställning, inte en plan. Att
  bedöma vad som ska göras först är ett annat arbete och ska inte smyga in här.
* **Kodmarkörerna söks bara i `.py` och `.mjs`.** Markdown under `docs/` gås
  inte igenom annat än mätningarna.
