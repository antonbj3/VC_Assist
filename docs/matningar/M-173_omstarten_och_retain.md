# M-173 — Omstarten mitt i spåret: RETAIN, varmstart och vad banken förutsätter

**Datum:** 2026-09-05
**Status:** KLART (kö A, punkt A9)
**Körs av:** `tests/protocol/kor_A9_omstarten.py` (rent CPU-arbete: ingen rigg,
  ingen docker, ingen modell). Omstartsbegreppet ligger i
  `svc/vc_assist_svc/st/tolk.py` (`varmstart()`, `kallstart()`).
**Rigg:** vår ST-tolk vid 20 ms scanperiod (M-20). Domarmekaniken är
  `kor_A4_skanncykeln.dom_vid_scan` — **samma funktion** som M-166 använde,
  med `omstart_ms` satt; ingen andra kopia av domaren.
  **Ingen modell körde i den här mätningen.**
**Bankspegel:** commit `5c2970c`, `sha256(sha256sum bank/uppgifter/*.json)` =
  `a498b803…b2631e5`. **49 uppgifter med spårfacit, 217 enheter**
  (49 referenser + 168 motbevis).
**Facit:** IEC 61131-3:s omstartsbegrepp — vid en **varm** start behåller
  variabler deklarerade `RETAIN` sitt värde och allt annat får sitt
  initialvärde; vid en **kall** start återställs också de retentiva. Facit för
  själva mekanismen är en handskriven fixtur **utanför** banken där den enda
  skillnaden mellan två lösningar är kvalificeraren `RETAIN`.
**Prövar:** `bank/uppgifter` och `svc/vc_assist_svc/st/tolk.py`
**Rådata:** `docs/matningar/radata/m173_svep.jsonl` (1085 domar),
  `…/m173_sammanstallning.json`, `…/m173_ut.txt`,
  `…/m173_bankspegel_fore.txt`.

## Frågan

`RETAIN` betyder att ett värde överlever en varmstart. Kvalificeraren fanns i
vårt lager på tre ställen — lexern (`lexer.py`), modellen
(`modell.KVALIFICERARE`) och validatorn (som fäller `VAR RETAIN CONSTANT`,
M-99) — men **ingenstans i körningen**. Tolken hade inget omstartsbegrepp
alls. `VAR RETAIN` var alltså en etikett utan verkan: en uppgift kunde inte
skilja en variabel som överlever strömavbrottet från en som inte gör det, och
ingen lösning kunde prövas mot det som händer varje gång någon slår av och på.

## 1. Vad som byggdes

`Tolk.varmstart()` och `Tolk.kallstart()`, 58 rader i `tolk.py`. Två saker som
**inte** nollställs, båda med skäl:

* **Insignalerna.** Fältet ändras inte av att PLC:n startar om — givaren står
  kvar där den står och bildtabellen läses om från den vid nästa scan. Att
  nollställa dem hade mätt *"alla givare försvann"* i stället för
  *"styrningen startade om"*.
* **Klockan.** Spåret är ett förlopp i verkligheten, och verkligheten pausar
  inte. Antalet omstarter räknas i `Tolk.omstarter`.

Funktionsblocksinstanser (`TON`, `R_TRIG`, `CTU` …) nollställs som allt annat
om de inte står i ett `RETAIN`-block. Det är inte en detalj: en flankdetektor
som minns sitt föregående värde över en omstart hade sett en flank som aldrig
hände — och en som **inte** minns ger en spökflank på första scanet om
insignalen står hög. Båda är riktiga PLC-fenomen; den senare är den som gäller
efter en varmstart, och den syns i mätningen.

### De tre trasiga fallen, alla gröna i körningen

**RETAIN-fixturen** ligger utanför banken: en stationsräknare som ska släppa
en pall efter fyra detaljer, med pulser vid 100, 300, 700 och 900 ms och en
varmstart vid 500 ms. Två texter, **en enda skillnad** — `VAR RETAIN` mot
`VAR`:

| text | dom över varmstarten | varför |
|---|---|---|
| `VAR RETAIN antal` | **GODKÄND** | räknaren står på 2 över omstarten, når 4 |
| `VAR antal` | **UNDERKÄND** `…@900ms:PLT_FULL` | räknaren nollas, når 2 |
| `VAR RETAIN antal`, **kallstart** | **UNDERKÄND** `…@900ms:PLT_FULL` | också de retentiva återställs |

Ger de samma dom är omstartsbegreppet en attrapp, och körningen vägrar svepa.
Den tredje raden är lika nödvändig som de två första: en "varmstart" som beter
sig som en kallstart är inget omstartsbegrepp.

**Självkontrollen** (ärvd ur M-166): utan omstart måste harnessen ge
bit-identiskt utfall och bristkodsmängd som `bank/domare.py` för varje enhet.
217 enheter, 0 avvikelser.

## 2. Första talet: **noll av 217**

**Ingen enda lösning i banken deklarerar RETAIN.** Inte en referens, inte ett
motbevis. Räknat ur ST-texten med läsaren och inte med en textsökning — ordet
kan stå i en kommentar.

Det betyder att varje state-maskin, varje räknare, varje latch och varje
larmminne i banken är **flyktigt**. Efter ett strömavbrott står stationen i
steg 0 med en detalj i gripdonet och ingen kod som vet om det.

## 3. Andra talet: **48 av 49 referenser faller på en varmstart**

Omstarten läggs vid 25 %, 50 % och 75 % av varje sekvens längd (snappad till
scanrutnätet), en omstart per sekvens.

| omstartsläge | enheter som byter utfall | uppgifter |
|---|---|---|
| 25 % in i sekvensen | **45** | 45 |
| 50 % in i sekvensen | **48** | 48 |
| 75 % in i sekvensen | **47** | 47 |
| 50 %, **kallstart** | **48** | 48 |

**Riktningen är entydig och densamma som i M-166:** varje enda ändring är en
**referens som går GRÖN → RÖD**. Inte ett enda av de 168 motbevisen ändrar
dom vid något läge.

Och den skarpaste formen av samma tal:

> **Noll av 49 referenser överlever en omstart i alla tre lägena.**

De fem som klarar sig i något enskilt läge — P-01 (bara vid 50 %), P-02 och
S-03 (vid 25 % och 75 %), S-02 och S-04 (bara vid 25 %) — klarar sig därför
att omstarten råkade landa där ingen stat behövdes, inte därför att koden
tål den. P-01:s tal illustrerar det: `UNDERKÄND` vid 200 ms, `GODKÄND` vid
400 ms, `UNDERKÄND` vid 600 ms. Det är tur, och tur går inte att leverera.

## 4. Tredje talet: **varmstart = kallstart i hela banken**

Varm och kall omstart vid samma tidpunkt gav **identiskt utfall och identiska
bristkoder i alla 217 enheter**. Noll skillnad.

Det är inte en tautologi utan en mekanisk kontroll av tal 1: eftersom ingen
lösning deklarerar `RETAIN` finns det ingenting för varmstarten att bevara,
och de två restarterna **måste** då sammanfalla. Att de gör det säger att
`RETAIN`-vägen inte är påslagen av misstag för icke-retentiva variabler.
Fixturens tre rader i §1 säger att den ändå är påslagen när den ska.

## 5. Vad talet betyder — och vad det inte betyder

**Det betyder inte att bankens referenser är dåliga lösningar.** Bankens
uppgifter frågar inte efter omstartstålighet. Ingen uppgiftstext nämner
strömavbrott, ingen `facit_spar` innehåller en omstart, och ingen förhandsregel
i `plc/forhandsregler.py` berättar för modellen att retentivitet är ett krav.
En lösning som inte får kravet kan inte klandras för att sakna det.

**Det betyder att banken mäter en storhet den inte skriver ut.** Varje tal
projektet har om tillförlitlighet är mätt på spår **utan avbrott**. Den
verkliga anläggningen har avbrott — det är därför `RETAIN` finns i standarden
— och för den frågan är bänkens svar i dag *"48 av 49 faller"*, alltså inget
svar alls.

Tre saker följer, i storleksordning:

1. **Den billigaste:** `plc/forhandsregler.py` matar redan in regler i
   systemprompten före modellen skriver. En regel om vad som ska vara
   retentivt (räknare, taktnummer, larmlatchar, steg i en förloppskedja)
   kostar en textrad och ändrar vad modellen skriver, inte vad vi mäter
   efteråt.
2. **Den riktiga:** en uppgift i banken vars `facit_spar` **innehåller** en
   omstart, med referens och motbevis. RETAIN-fixturen i körningen är skriven
   i bankens form och går att lyfta in rakt av — den ligger utanför
   `bank/uppgifter/` bara för att banken ägs av en annan kö och växer just nu.
3. **Den dyra:** OpenPLC-domaren har inget omstartsbegrepp heller. En riktig
   omstart mitt i ett spår är `stop-plc` + `start-plc` mitt i sekvensen, och
   `domare_openplc._stoppa`/`_starta` finns redan — men vad OpenPLC v4 gör med
   `RETAIN` över en varmstart är **inte mätt** (se LIMITS).

## LIMITS

* **En motor.** Hela svepet är vår ST-tolk. Att OpenPLC v4 implementerar
  `RETAIN` över en varmstart, och att STruC++ över huvud taget översätter
  kvalificeraren, är **inte mätt här**. Utan det är tolkens omstartsbegrepp en
  modell av standarden, inte en mätning av kedjan. Det är den enskilt största
  bristen i den här mätningen.
* **Omstarten är momentan.** Ingen tid går åt till att starta om, och inga
  utgångar går genom ett mellanläge. En riktig varmstart tar sekunder, och
  under dem är utgångarna nollställda — vilket i sig kan fälla en invariant
  som den här mätningen aldrig ser.
* **En omstart per sekvens, i tre lägen.** Två omstarter i rad, en omstart
  mitt i en flankräkning, eller en omstart under en TON-nedräkning är inte
  mätta var för sig.
* **`RETAIN` läses bara på `VAR`-blockets kvalificerare.** `VAR_GLOBAL RETAIN`,
  `RETAIN` på en enskild deklaration och `NON_RETAIN` är inte prövade;
  bankens noll RETAIN gör skillnaden oobserverbar i det här svepet.
* **Facit är oförändrat.** Bankens `facit_spar` är skrivna utan omstart, så
  ett rött utfall betyder *"referensen håller inte facit efter en omstart"* —
  inte *"referensen är fel"*. Vilken av de två som ska ändras är ett
  bankbeslut och inte ett mätresultat.
* **Ingen körning i Visual Components.** Spårfacit ligger bredvid ögondomen,
  aldrig i stället för den (invariant I1).
