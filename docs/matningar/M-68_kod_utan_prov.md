# M-68 — 2656 rader produktionskod som inget enhetsprov rör

**Datum:** 2026-09-05
**Anledning:** operatörens krav att fånga teknisk skuld när den skrivs (M-66,
regel S5 i `96_ingen_skuld.md`). Registret fångade ärlighetsavsnitt och
kodmarkörer. Det fångade inte kod som ingen provar.

## Talen

| Hink | moduler | rader |
|---|---:|---:|
| **inget prov alls** — ingen provfil nämner modulen | **5** | **1229** |
| **bara L3** — nämns bara av en körning under `tests/protocol/` | **3** | **1427** |

Skillnaden är inte kosmetisk. En körning under `tests/protocol/` kräver levande
VC, OpenPLC eller kompilator och körs **inte** av `pytest tests/enhet`. En modul
i den hinken går alltså inte att kontrollera på en ren maskin — vilket är precis
vad fas 10 lovar att man ska kunna.

### Inget prov alls

| Modul | rader |
|---|---:|
| `svc/vc_assist_svc/layout/vc_utdata.py` | 143 |
| `svc/vc_assist_svc/plan/layoutport.py` | 194 |
| `svc/vc_assist_svc/plan/villkorssprak.py` | 379 |
| `svc/vc_assist_svc/plc/baslinje/morfologi.py` | 288 |
| `svc/vc_assist_svc/plc/baslinje/packml.py` | 225 |

De tre sista skrevs i natt av agenter som fortfarande arbetar; deras prov kan
mycket väl landa inom kort. De två första är äldre och har ingen sådan ursäkt:
`vc_utdata.py` anropas av tre produktionsmoduler och `layoutport.py` av två.

### Bara L3

| Modul | rader |
|---|---:|
| `svc/vc_assist_svc/komponentfil.py` | 957 |
| `svc/vc_assist_svc/plan/processer.py` | 287 |
| `svc/vc_assist_svc/plc/opcuakonfig.py` | 135 |

## Lagat i samma andetag

`svc/vc_assist_svc/st/strucpp_orakel.py` (255 rader) låg i L3-hinken. Den är
**min egen** från samma kväll, och det är värt att notera: jag skrev en modul
som är hela grunden för M-54:s andra motor och gav den inget prov som går att
köra utan kompilator.

Nu 29 prov i `tests/enhet/test_strucpp_orakel.py`, som provar tolkningen av
orakelts utdata — den del som gör en avvikelse till en avvikelse. Fyra av dem är
trasiga fixturer: ett steg som saknar sitt svar, fel antal körningar, en okänd
variabel som REPL:en rapporterar och sedan fortsätter förbi, och en saknad
kompilator.

Det viktigaste av dem: **ett orakel som tiger får aldrig se ut som ett orakel som
höll med.** Utan det provet hade ett uteblivet svar tolkats som "ingen avvikelse".

## Spärren

`tests/enhet/test_skuld.py` bär nu båda talen som tak som bara får gå nedåt.

**Vad spärren INTE har, och varför:** tröskelskulden har ett dubbelriktat krav —
taket får inte heller ligga *över* verkligheten, för ett tak med luft i slutar
fånga. Den halvan är medvetet **inte** införd i natt, eftersom sex agenter
arbetar i repot samtidigt och lägger till moduler vars prov kommer strax efter.
Ett exakthetskrav i natt hade gjort sviten röd för deras halvfärdiga arbete i
stället för att fånga skuld.

Att kravet inte är inne är i sig en skuld, och den står här så att den inte
glöms bort.

## Vad som INTE är mätt

* **Om proven faktiskt provar något.** Kriteriet är grovt: nämns modulens
  filnamn i provtexten? En modul som nämns i en import men aldrig anropas
  räknas som provad. Ett finare mått — täckning per rad — är inte kört.
* **Om de fem utan prov är farliga.** Radantal är inte risk. `layoutport.py` kan
  vara trivial och `vc_utdata.py` full av kanter; ingen har läst dem med den
  frågan.
* **Protokollkörningarna själva.** Ingen av dem har prov, och det är rimligt —
  de *är* prov. Men det betyder att ett fel i en körning inte fångas av något.
