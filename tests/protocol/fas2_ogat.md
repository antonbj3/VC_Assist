# FAS 2 ACCEPTANS — ögat

**beskriver:** `ext/vc_addon/vc_assist/oga_provtagning.py`, `oga_analys.py`, `oga_kontrakt.py`
**kontrakt:** `docs/spec/40_ogat.md`, `docs/spec/41_ogat_kontrakt.md`
**grind (70_faser.md):** *"På en handbyggd bra och en handbyggd trasig cell: ögats dom
matchar facit i båda. Trasig cell **måste** fällas."*

## Utfall 2026-09-04 — mot en körande VC

Kört med `python3 tests/protocol/kor_fas2.py`. VC Premium 4.10 under Wine 11.16,
headless `:99`. Cellerna byggs i VC:s riktiga scengraf; ögat läser
`vcNode.WorldPositionMatrix` genom bryggan.

| Cell | Facit | Dom | Prov | Raden som avgjorde |
|---|---|---|---|---|
| `bra` | PASS | **PASS** | 190 | `GRIP FORMED t=0.950s` · `CARRY RIGID rot=0.0deg` · `PLACE IN_TARGET` |
| `fel_placerad` | FAIL | **FAIL** | 190 | `PLACE OFF_TARGET err=80.0mm` |
| `glider` | FAIL | **FAIL** | 190 | `CARRY SLIPPING rot=15.0deg` |
| `tappad` | FAIL | **FAIL** | 190 | `PLACE DROPPED` |
| `teleport` | FAIL | **FAIL** | 190 | `TELEPORT_TRANSFER VIOLATION dist=800.0mm` |

**5 av 5 enligt facit.**

Att `bra` får PASS är sitt eget prov: en domare som fäller allt klarar varje
fällningsprov och är ändå värdelös.

## Två saker som körningen bevisar utöver domarna

**Kvaternionen.** `glider` landade på **exakt 15,0 grader**, samma tal som den
syntetiska cellen bär. Det går bara ihop om omräkningen i M-11 stämmer — VC:s
kvaternion är skalär-först, och läst rakt av hade en orörd detalj blivit en
180-graders vridning. Cellen provar hela den vägen genom VC.

**Att cellen inte behöver ett drivskript.** Rörelsen drivs av **pumpen själv**
genom en bana. Skälet är mätt: `createBehaviour(VC_SCRIPT)` är den enda
operation som stoppar simuleringen och dödar pumpen (M-13).

## Vad som INTE är prövat

* **Kollision och minsta avstånd** är omätta i VC. `sim.newCollisionDetector()`
  finns i API-ytan men har aldrig anropats. Cellerna ovan bär ingen kollision.
* **Signaler, uppehåll och genomströmning** är prövade på syntetiska serier men
  inte i VC — cellerna har inga signalbeteenden.
* **Robotleder** (`vcServoController.Joints`) är helt oprövade.
* **Bilder** är inte provtagna alls. Det är enligt `40_ogat.md`, där bilder är
  uttryckligen en svagare och valfri signal.
* **Gränssnittet under last** — allt är kört headless.
* **Windows** — oprövat.

## Plattform
Linux ☑ *(Wine 11.16, VC Premium 4.10, headless)*   Windows ☐ **oprövad**
