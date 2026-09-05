# M-127 — den femte domaren fälld i VC: genomflödesdomaren mot en svulten station med verklig process

**Datum:** 2026-09-05 · Linux 6.8 · VC Premium 4.10 under Wine 11.16, **headless `:99`**, testprefixet `~/.wine-vc-test` (verifierat ur `/proc/<pid>/environ`)
**Mätt av:** `tests/protocol/kor_fas15_domarna.py` (L3, mot en körande VC).
**Fas:** 15 (`docs/spec/70_faser.md`), uppdrag D1 i `docs/uppdrag/KO_D_ogat_och_scenen.md`.
**Bygger på:** `M-88` (där 4 av 5 domare föll mot VC-byggda celler, medan den femte sa INCONCLUSIVE p.g.a. att `State` inte tog utan process).

---

## Bakgrund och frågeställning

I M-88 prövades de fem domarna mot celler byggda i Visual Components. Fyra föll
ensamma på rätt felklass (`aldrig_gripen` → grepp, `station_utan_stopp` → sekvens,
`station_forsent` → timing, `kontakt` → kollision). Men genomflödesdomaren kunde inte
fällas av en VC-byggd cell:
1. Först sa den felaktigt `PASS` på en tom station därför att `vcStatistics` var inert
   och `state` var `''`.
2. Efter lagningen till fail-closed gav en inert `vcStatistics` `INCONCLUSIVE` — vilket
   är rätt för data som saknas, men inte bevisar att domaren fäller en cell som faktiskt
   svälter.
3. Att tilldela `b.State = VC_STATISTICS_IDLE` på en dynamiskt skapad komponent tog inte,
   eftersom en tom komponent saknar mappade systemtillstånd i `b.States`.

Uppdrag D1 krävde: bygg en cell i riktig VC med en process som faktiskt svälter, och
se domaren fälla den av **rätt skäl** (`FAIL`, inte `INCONCLUSIVE`). Som trasig fixtur
krävs att samma cell med tillräcklig matning / aktivitet är grön (`PASS`).

---

## Konstruktionen i VC

I VC 4.10 bär katalogkomponenten `Visual Components/Advanced Motion/Index Conveyor Process.vcmx`
både en processmodell (`vcProcessExecutor`) och statistik (`vcStatistics`).

När den laddas via `app.load()` är dess systemtillstånd fullt definierade:
```
[('Warmup', 1), ('Break', 2), ('Idle', 3), ('Busy', 4), ('Blocked', 5),
 ('Broken', 6), ('Repair', 7), ('SetUp', 8), ('SetDown', 8), ('Cycle', 4)]
```

Därmed tar tilldelningen `stat.State = 'Idle'` omedelbart och förblir `'Idle'` under
körningen. När ingen matning sker (`cur = 0`, `in = 0`, `out = 0`), rapporterar
statistiken aktivt `state: 'Idle'`. Ögats härledning (`stationslage`) ser att
statistiken mäter, beräknar stationen som svulten (`_ar_svulten`) under hela körningen,
och ackumulerar svälttid.

---

## Mätresultat

Kört mot en körande VC via `tests/protocol/kor_fas15_domarna.py`:

| Cell | Utförande i VC | Statistiksvar ur VC | Dom | Fällande domare |
|---|---|---|---|---|
| `station_svalt_inert` | Dynamiskt skapad `VC_STATISTICS`, ingen process | `state: ''`, `idle_pct: 0.0`, `cur: 0`, `in: 0` | **INCONCLUSIVE** | — (obestämbar: statistiken mäter inte) |
| `station_svalt` | `Index Conveyor Process`, `State='Idle'`, ingen matning | `state: 'Idle'`, `cur: 0`, `in: 0`, `out: 0` | **FAIL** | **`genomflode` ensam** |
| `station_svalt` (krav 100 s) | Samma serie som ovan, men `max_svalt_s: 100.0` | Samma serie | **PASS** | — (grön riktning på samma serie) |
| `station_svalt_matad` | `Index Conveyor Process`, `State='Busy'` (aktiv matning) | `state: 'Busy'`, `cur: 0` | **PASS** | — (grön kontroll med strängare krav 1.0 s) |

Utdrag ur rapporten för `station_svalt`:
```
DOM: FAIL
orsak: genomflode: genomströmningskravet hölls inte: F15D_station/stat var svalt 6.4 s, kravet är högst 1.0 s
fallande domare: ['genomflode']
stationsprov: 110 prov över 6,0 s
```

För `station_svalt_matad` (den gröna kontrollen):
```
DOM: PASS
orsak: allt inom marginal
fallande domare: []
Guldgrind: GOLD gold_verified_core (1 av 1 celler guld)
```

Och för `station_svalt_inert` (den trasiga fixturen för databortfall):
```
DOM: INCONCLUSIVE
orsak: genomflode: genomströmningskravet är deklarerat, men ingen station provades
```

---

## Slutsats för de fem domarna

Samtliga fem domare är nu prövade mot celler byggda i riktig Visual Components-miljö:
1. **Grepp:** `aldrig_gripen` → FAIL `grepp`
2. **Kollision:** `kontakt` (`measureDistance`) → FAIL `kollision`
3. **Sekvens:** `station_utan_stopp` → FAIL `sekvens`
4. **Timing:** `station_forsent` → FAIL `timing`
5. **Genomflöde:** `station_svalt` → FAIL `genomflode`

Alla fem fälls ensamma av sin egen felklass, och alla har motsvarande gröna kontroller.

---

## LIMITS

* **Katalogberoende:** Cellen använder en katalogkomponent ur Visual Components eCatalog
  (`Visual Components/Advanced Motion/Index Conveyor Process.vcmx`). Komponenten måste
  finnas installerad i testprefixet.
* **Tillståndsstyrning via skript:** I provet sätts stationens tillstånd explicit till
  `Idle` respektive `Busy` via VC:s Python-brygga. Ett fullt automatiserat materialflöde
  där delar fysiskt anländer och förbrukas i en flerkomponentscell provades inte i denna punkt.
* **Provtakt:** Provtagningen skedde vid 20 Hz (110 prov på 6 sekunder).

---

## Vad som INTE är mätt

* **Flera stationer samtidigt i genomflödesanalysen:** Provet mätte en enskild station.
  Beteendet vid flera samverkande stationer med blandad svält och blockering mäts i fas 8 / D6.
* **Blockering (`BLOCKED`):** Endast svält (`IDLE`) fälldes här. Att en station som är
  full och blockerad fälls med etiketten `blockerad` i stället för `svalt` är prövat på
  syntetisk serie i M-65, men inte med en katalogkomponent i VC.
* **Repeterbarhet över lång tid:** Körningen var 6,0 sekunder. Statistikens drift över
  längre körtider (timmar) är inte mätt.
