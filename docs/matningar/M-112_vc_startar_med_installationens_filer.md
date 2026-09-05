# M-112 — VC startar med det installationen lade dit

**Datum:** 2026-09-05
**Rigg:** testprefixet `~/.wine-vc-test`, headless `:99`, VC Premium 4.10, Wine
**Stänger:** fas 10:s sista öppna punkt

## Punkten som stod öppen

`tests/protocol/fas10_paketering.md`, ordagrant:

> *"**Inte prövat, och det är fasens öppna punkt:** att **VC startar** med det
> som installationen lade dit. Fas 1:s och 2:s körningar mot VC gjordes mot en
> handinstallerad kopia, inte mot installationens."*

Allt annat i fas 10 var mätt — sökningen, installationen, idempotensen,
avinstallationen, 67 enhetsprov, och sedan `M-90` även en ren Linux-maskin.
Det som saknades var det sista ledet: att filerna inte bara ligger rätt utan
att **VC faktiskt laddar dem**.

## Sekvensen, i den ordningen

1. **Installera från nuvarande repo.**
   `python3 install/installera.py installera --mal <My Commands/Python 2/vc_assist>`
   → `nya: 0, uppdaterade: 1, oförändrade: 10, borttagna: 0`, och
   *"verifierat på plats: 11 filer parsar och kompilerar"*.
   Den ena uppdaterade var `oga_analys.py`, som drivit isär medan agenter
   arbetat i repot.
2. **Stoppa VC** med `wineserver -k` mot testprefixet. Noll VC-processer kvar,
   räknat på **binären** och inte på en textsträng (se nedan).
3. **Starta med `~/bin/vc-test.sh`.** Skriptet skrev
   `[SKARM] DISPLAY=:99 (dold)` och `[TESTPREFIX] /home/anton/.wine-vc-test`.
4. **Läsa bootloggen.**

## Vad bootloggen sa

```
09:57:24 OnAppInitialized
09:57:24 tillaggsmapp: C:\users\anton\Documents\Visual Components\4.10\My Commands\Python 2\vc_assist
09:57:24 loadCommand uri=file:///...\vc_assist\bridge_cmd.py
09:57:24 [cmd] kor startskript (44498 tecken)
09:57:24 [cmd] startskriptet kordes
09:57:24 [cmd] brygg-komponenten byggd, skriptet kompilerar
09:57:24 [cmd] OnStartStop-handlare registrerad
09:57:24 [cmd] startSimulation() atervande efter 0.007 s, IsRunning=True
09:57:24 bridge_cmd executed
```

Tolv nya rader, från 814 till 826. VC hittade mappen, laddade kommandot, körde
startskriptet och byggde bryggkomponenten.

## Att den lever, inte bara laddades

| | |
|---|---|
| `ping` tur och retur | **19,7 ms**, `ok=True` |
| `exec` `print(1+1)` | `ok=True`, stdout `2` |
| `exec` med JSON-kanal | `ok=True`, stdout `{"a": 1}` |

Och det starkaste beviset kom ur ett **fel**: en felskriven fråga gav ett
Python-spår ur VC med sökvägen
`C:\users\anton\Documents\...\My Commands\Python 2\vc_assist\pump.py`. Koden
kördes alltså ur installationens filer, inte ur någon annan kopia.

## Ett fel av mig, värt att skriva ned

Under förberedelsen rapporterade jag två gånger att en session startat VC på
operatörens skärm med `DISPLAY=:1`. **Det var falskt.** Min sökning matchade på
kommandoradens text, och strängen `VisualComponents.Engine` stod i mitt eget
skalkommando — sökningen hittade sig själv och rapporterade sin egen miljö.

Det är samma självmatchningsfälla som `pgrep -f`, som redan är antecknad, och
jag gick i den ändå. Rätt fråga är processens **binär**, inte dess
kommandorad: noll VC-processer fanns.

Falsklarmet ledde ändå till ett äkta fynd: `~/bin/vc-test.sh` **ärvde**
`DISPLAY`. Det dokumenterade sättet att starta VC följde inte invarianten
*"sätt DISPLAY explicit, ärv den ALDRIG"*. Skriptet sätter nu `:99` själv,
kräver `VC_TEST_DISPLAY` för ett synligt fönster, och vägrar starta om den
dolda skärmen saknas. Kopian ligger i `drift/` och sju prov håller de två lika.

## LIMITS

* **En körning, en maskin, en VC-version.** Wine 11.16, VC Premium 4.10,
  testprefixet. Säger ingenting om Windows (fas 13) eller om andra VC-versioner.
* **Tillägget kördes, scenen prövades inte.** Bryggan svarar och kör kod; att
  ögat, skrivgrinden och kön beter sig rätt efter en installation är prövat på
  annat håll och inte om här.
* **`avinstallera` kördes inte** i den här sekvensen. Att trädet blir
  byte-identiskt efteråt är mätt tidigare i fas 10, men inte i samma svep.
* **Installationen skedde med `--mal`**, alltså en utpekad sökväg. Automatiken
  som hittar mappen själv är mätt i `M-90` och i enhetsproven, men den här
  körningen prövade den inte.
