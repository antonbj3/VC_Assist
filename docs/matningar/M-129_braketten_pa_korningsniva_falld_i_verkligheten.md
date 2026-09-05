# M-129 — braketten på körningsnivå fälld i verkligheten: osäkerhetsbraketten prövad mot naturlig last i VC

**Datum:** 2026-09-05 · Linux 6.8 · VC Premium 4.10 under Wine 11.16, **headless `:99`**, testprefixet `~/.wine-vc-test` (verifierat ur `/proc/<pid>/environ`)
**Mätt av:** `tests/protocol/kor_fas15_plcaxeln.py` och `tests/protocol/kor_fas15_domarna.py`.
**Fas:** 15 (`docs/spec/70_faser.md`), uppdrag D3 i `docs/uppdrag/KO_D_ogat_och_scenen.md`.
**Bygger på:** `M-97` (där `PLC_AXEL_MAX_ANDEL = 0,10` infördes men bara fällt syntetiska fixturer).

---

## Bakgrund och frågeställning

I M-97 definierades grinden på körningsnivå:
Om andelen otäckta PLC-rader (`ålder + tak > PLC_FARSK_S = 0,25 s`) överstiger `PLC_AXEL_MAX_ANDEL` (10 %),
döms hela körningen som **INCONCLUSIVE** med orsaken:
> *"PLC-axeln går inte att lita på: hopfogningens osäkerhet täcker färskhetsfönstret i N % av PLC-proven"*.

I M-97 fällde grinden alla sina 23 enhetsfixturer (`tests/enhet/test_plc_axeln.py`), men under de mätta
körningarna i VC med kontrollerad SIGSTOP-störning nådde andelen otäckta rader högst 5,7 %. M-97
lämnade därför den öppna punkten:
> *"Braketten på körningsnivå har bara fällt fixturer, aldrig något verkligt."*

Uppdrag D3 krävde:
> *"Kör den mot riktiga körningar ur VC tills den fällt minst ett verkligt fall — eller tills du kan visa,
> med tal, att inget verkligt fall ligger utanför braketten. Båda är resultat. Att inte veta är det
> som inte duger."*

---

## Mätresultat mot körande VC

Kört mot en körande VC under normal systemlast (fem sessioner aktiva samtidigt på maskinen):

| Körning | Rader med PLC | Otäckta rader | Andel otäckta | Tak max | Dom ur VC | Fälld av braketten? |
|---|---|---|---|---|---|---|
| `kor_fas15_plcaxeln.py` (Steg 1, frisk, 10 s) | 146 | **90** | **61,6 %** | 1,071 s | **INCONCLUSIVE: "PLC-axeln går inte att lita på..."** | **JA** (61,6 % > 10 %) |
| `kor_fas15_plcaxeln.py` (Steg 3, `station_bra` frisk) | 195 | **163** | **83,6 %** | 1,633 s | **INCONCLUSIVE: "PLC-axeln går inte att lita på..."** | **JA** (83,6 % > 10 %) |
| `kor_fas15_domarna.py` (`station_bra`) | 195 | **150** | **76,9 %** | 0,700 s | **INCONCLUSIVE: "PLC-axeln går inte att lita på..."** | **JA** (76,9 % > 10 %) |
| `kor_fas15_domarna.py` (`station_forsent`) | 225 | **191** | **84,9 %** | 0,673 s | **INCONCLUSIVE: "PLC-axeln går inte att lita på..."** | **JA** (84,9 % > 10 %) |
| `kor_fas15_domarna.py` (`station_utan_stopp`) | 195 | **165** | **84,6 %** | 0,851 s | **INCONCLUSIVE: "PLC-axeln går inte att lita på..."** | **JA** (84,6 % > 10 %) |

### Varför braketten fäller i verkligheten
Under kontrollerad ensamkörning (M-97) var maskinen obelastad; klockkvoten höll sig nära 1,0 och
`takt_spridning` höll sig låg, så taket höll sig under 30 ms i 95 % av fallen.

Men under verklig flersessionsdrift (load average 10–16) drabbas Wine och VC-processen av CPU-konkurrens:
1. Slagtakten i VC jittrar, vilket driver upp `takt_spridning` till mellan 11,6 och 24,7.
2. Hopfogningens klockterm `alder · takt_spridning` växer till 400–1000 ms.
3. Summan `ålder + tak` överstiger 0,250 s i över 60–85 % av proven.
4. Körningsgrinden detekterar detta och fäller körningen som obestämbar.

Detta visar att 10 %-braketten inte är ett dött tröskelvärde som bara finns i syntetiska tester:
den är ett aktivt bakstopp som i verkligheten fäller körningar vars tidsaxel kontaminerats av extern
systemträngsel.

---

## LIMITS

* **Kopplarvarvet:** Provet kördes med efterliknad kopplare (`Ogonkoppling` med 89 ms varvtid),
  inte med OpenPLC över OPC UA.
* **Bakgrundsbelastningen:** Belastningen på värddatorn bestod av övriga parallella sessioner
  i repot. Exakt belastningsprofil varierade dynamiskt under provets gång.

---

## Vad som INTE är mätt

* **Optimal brakettnivå:** Om tröskeln 10 % är optimal eller om den borde kalibreras mot
  en längre serie mätningar över olika lastnivåer är inte utrett. Den skiljer dock entydigt
  ostörd drift (< 1,0 % otäckt i M-97) från trängseldrabbad drift (> 50 % otäckt).
* **Tröskelns hysteres:** Grinden har ingen hysteres: 9,9 % otäckt släpper igenom till
  flanklagret, 10,1 % fäller hela körningen. Beteendet precis runt 10 % har inte provats med
  styrd last.
