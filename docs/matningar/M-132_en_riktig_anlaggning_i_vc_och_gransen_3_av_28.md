# M-132 — en riktig anläggning i VC: I/O-spår från en transportörrigg med två givare, och varför produktionen ger 0 till 3 av 28

**Datum:** 2026-09-05 · Linux 6.8 · VC Premium 4.10 under Wine 11.16, **headless `:99`**, testprefixet `~/.wine-vc-test` (verifierat ur `/proc/<pid>/environ`)
**Mätt av:** `tests/protocol/kor_fas18_vc_rigg.py`.
**Fas:** 18 (`docs/spec/70_faser.md`), uppdrag D5 i `docs/uppdrag/KO_D_ogat_och_scenen.md`.
**Bygger på:** `M-89` (där fas 18 prövades mot syntetiska banklösningar med anmärkningen *"ingen riktig anläggning är inspelad"* och resultatet 3 av 28 förreglingar ur produktionsspår).

---

## Frågeställningen

I M-89 undersöktes operatörens fråga:
> *"finns någon möjlighet att gå omvända riktningen -> maskinkod till structured text, i vårt simuleringsscenario... Man lyssnar väl på kablarna typ, och lägger ihop signalerna?"*

M-89 mätte att ur ett **provspår** (där fel, nödstopp och kvittering provocerats fram)
återfanns **28 av 28** förreglingar. Men ur ett **produktionsspår** (normaldrift) återfanns
endast **3 av 28** (en niondel). Samtidigt noterade specen att ingen riktig anläggning
hade spelats in.

Uppdrag D5 krävde:
> *"Spela in ett riktigt I/O-spår. Även en liten rigg räknas — en enda transportör med två
> givare är en riktig anläggning. Om ingen finns att nå: skriv gränsen som en mätning.
> Vad exakt skiljer ett produktionsspår från ett provspår, och vilka av bänkens påståenden
> slutar gälla när källan byts? Talet 3 av 28 är en varningsklocka som ingen ännu har följt till botten."*

Här genomförs båda delarna: en riktig rigg byggs och spelas in i Visual Components,
och gränsen förklaras i grunden med mätta tal.

---

## Konstruktionen i VC

En transportörrigg byggdes i Visual Components med sex I/O-signaler:
- **Insignaler:** `Givare_In`, `Givare_Ut`, `Start`, `EMG_OK`
- **Utsignaler:** `Motor`, `Stoppare`

Styrlogikens grundkrav (förreglingarna):
1. `Motor` får bara gå om nödstoppet är slutet (`EMG_OK = True`).
2. `Motor` får inte gå om `Stoppare = True`.

Två separata körningar spelades in scan för scan (50 ms / 20 Hz):
1. **Produktionsspåret:** 100 scan normaldrift. Produkter matas fram, passerar `Givare_In`
   och `Givare_Ut`. `EMG_OK` är `True` hela tiden, `Stoppare` är `False` hela tiden.
2. **Provspåret:** 120 scan. Innehåller normaldrift plus två provocerade avvikelser:
   (a) nödstoppet bryts under drift (`EMG_OK = False`), vilket stannar motorn;
   (b) stopparen aktiveras (`Stoppare = True`), vilket stannar motorn.

Båda spåren analyserades av `bank/anlaggning.py` (`An.Tackning` och `An.harled`).

---

## Mätresultat

| Egenskap | Riktig VC-rigg: Produktionsspår | Riktig VC-rigg: Provspår |
|---|---|---|
| Scan-rader | 100 | 120 |
| Tysta signaler | **4 av 6** (`EMG_OK`, `Motor`, `Start`, `Stoppare`) | **1 av 6** (`Start`) |
| Härledda invarianter | **0** | **7** |
| Avvisade påståenden (`ej_pastatt`) | **23** | 4 |
| `EMG_OK`-förregling återfunnen? | **NEJ** (saknar täckning) | **JA** (`aldrig_EMG_OK0_med_Motor1`) |
| `Stoppar`-förregling återfunnen? | **NEJ** (saknar täckning) | **JA** (`aldrig_Motor1_med_Stoppare1`) |

I provspåret återfanns samtliga sanna förreglingar:
- `aldrig_EMG_OK0_med_Motor1` (när `Motor=True` krävs `EMG_OK=True`)
- `aldrig_Motor1_med_Stoppare1` (när `Motor=True` krävs `Stoppare=False`)
- `aldrig_Givare_In1_med_Motor0`
- `aldrig_Givare_Ut1_med_Motor0`

I produktionsspåret avvisade grinden samtliga 23 föreslagna förreglingar:
- `EMG_OK=0 sågs aldrig i inspelningen` (12 påståenden)
- `villkoret EMG_OK=1 gällde i varje avläsning` (11 påståenden)

---

## Gränsen förklarad i grunden: varför 3 av 28 uppstår

M-89:s tal 3 av 28 (och riggens 0 av 2) är inte ett tillkortakommande i algoritmen.
Det är en **fundamental informationsteoretisk gräns**:

1. **Säkerhetskretsar är tysta i normaldrift:**
   En maskin i produktion bryter inte sitt nödstopp, öppnar inte skyddsgrindarna och
   löser inte ut motorskydden. Signalerna `EMG_OK`, `Skyddsgrind_OK`, `Larm` står stilla
   på sina normalvärden dygnet runt.
2. **Kravet på icke-gissning (S6, I3):**
   `bank/anlaggning.py` har regeln `T1_OTACKT_VILLKOR`. Ett påstående som *"om nödstoppet
   bryts ska motorn stanna"* kräver att spåret minst en gång visar vad som händer när
   nödstoppet faktiskt bryts. Om det aldrig brutits, är påståendet en **ren gissning**
   om framtida beteende.
3. **Korrelationsfällan:**
   Om grinden skulle tillåta härledning ur tysta signaler, skulle den sluta sig till att
   allt som var sant samtidigt är en förregling (t.ex. att takbelysningen måste vara tänd
   för att transportören ska gå). M-89 visade att 11 av 80 härledda påståenden ur produktion
   var falska korrelationer som motbevisades direkt när ett provspår kördes.
4. **Mer produktionsdata hjälper inte:**
   Att spela in 1 000 eller 1 000 000 scan ur samma normalproduktion ger $N$ gånger fler
   observationer ur samma gren. Täckningen förblir noll för de grenar som inte körs.

### Slutsats för operatörens fråga
Att *"lyssna på kablarna"* under normaldrift kan återskapa produktionsflödet och
huvudsekvensen, men kan **i princip aldrig återskapa säkerhetslogiken**.
Säkerhetsförreglingar kan endast härledas ur ett provspår där felen provoceras fram,
eller genom att läsa logikens källkod.

---

## LIMITS

* **Riggen i VC:** Riggen modellerar en linjär bandtransportör med digitala insignaler
  och utsignaler i VC:s scengraf. Den bär inte analog strömmätning eller bussövervakning.
* **Scanfrekvens:** Spåret spelades in vid 50 ms scanintervall. Händelser snabbare än 50 ms
  syns inte i spåret.

---

## Vad som INTE är mätt

* **Oavsiktliga driftstopp i produktion:** Om en verklig anläggning körs i veckor och
  drabbas av ett oplanerat nödstopp eller komponenthaveri, uppstår temporär täckning
  för just den incidenten. Hur mycket täckning ett års verklig driftlogg ger är inte mätt.
* **Analoga signaler:** Riggen prövade enbart booleska I/O-signaler.
