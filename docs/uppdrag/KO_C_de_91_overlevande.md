# Kö C — de 91 skador bänken inte ser

Läs `docs/uppdrag/00_GEMENSAMT.md` först.

## Din yta

`svc/vc_assist_svc/plc/mutation.py`, `bank/domare.py`, `bank/uppgifter/*.json`
(bara fältet `scenarios`, och bara efter C2), `tests/protocol/kor_C*`,
`tests/enhet/test_mutation_*`, `docs/spec/83_scenarier.md`,
`docs/spec/82_felklasser.md`, dina egna `docs/matningar/M-1xx`.

## Läget, mätt

Mutationsmotorn skadar en referenslösning på ett känt sätt och frågar om
bänken fångar det. Facit är skadan själv. Körningen 2026-09-05:

```
skador 808   fångade 717   överlevde 91
```

91 skador går rakt igenom. Bänken säger grönt om kod som är trasig på ett sätt
vi själva har skrivit in. Fördelningen är det viktiga:

```
klass: OSYNLIG 67 · SYNLIG_BARA_UNDER_PERTURBATION 12 · SKILLNAD_PÅ_FACITSTIMULUS 12
```

**67 skador är osynliga även under störning.** Ingen stimulus vi har får dem
att visa sig. Och en sort dominerar:

```
FALSKT_TILL_SANT   78 skador   21 fångade   57 överlevde   varav 51 OSYNLIGA
```

Att byta ett `FALSE` mot ett `TRUE` överlever i två fall av tre.

## Vad det betyder, sagt rakt

Varje tillförlitlighetstal projektet har — `M-96`:s, `M-110`:s "25 av 26" —
är mätt med en domare som inte ser den här klassen fel. Talen är alltså
optimistiska med en okänd marginal, och den marginalen är den här kön.

Det här är inte en fråga om att förbättra en siffra. Det är frågan om siffran
mäter det den påstår.

---

## C1 — varför är `FALSKT_TILL_SANT` osynlig

Innan du bygger något: ta reda på varför.

Arbetshypotesen är att ett `FALSE` som byts till `TRUE` bara syns om något
**läser** variabeln innan något annat skriver den — och att bankens stimuli
nästan aldrig gör det. Initialvärden hinner skrivas över innan de observeras.

Pröva hypotesen. Om den håller är åtgärden inte fler mutationer utan andra
stimuli. Om den inte håller har du hittat något bättre.

**Levererar:** `M-1NN` som för varje av de 51 osynliga säger *varför* just den
är osynlig, i en av ett litet antal namngivna klasser. En lista på 51 rader
utan klassindelning är inte ett svar.

## C2 — stimuli som gör dem synliga

För varje klass ur C1: konstruera en stimulus som får skadan att visa sig.
Lägg in den som ett nytt `scenario` på uppgifterna det gäller.

Två fällor, båda mätta i det här projektet:

* **Ett scenario som bara fäller mutanten är ingen stimulus, det är ett
  facit i förklädnad.** Referenslösningen måste fortfarande vara grön.
  Kontrollera det varje gång.
* **Grinden får inte bli billig.** Om du lägger till ett scenario som fäller
  mutanten genom att göra uppgiften lättare har du flyttat problemet, inte
  löst det.

**Trasig fixtur:** ett scenario som fäller både mutanten och referensen ska
avvisas av mekanismen, inte accepteras.

## C3 — mutationspoängen som grind med golv

När C2 höjt fångstgraden: mekanisera den. `fångade / skador` blir en grind med
ett **golv som bara får gå uppåt** — samma spärr som `M-53` la på harnessens
hårdhet och som tröskelskulden har.

Golvet sätts till det uppmätta värdet, aldrig till ett runt tal.

## C4 — lagret som fångar av fel skäl

```
fångade per (väntat → lager): (beteende→beteende) 374 · (text→text) 273 · (beteende→text) 70
```

Sjuttio skador som skulle ha fällts av **beteendet** fälldes av **texten**.
Det är tur, inte konstruktion: en textgrind som råkar snubbla på en
beteendebugg fångar den bara så länge texten råkar se ut som den gör.

Gå igenom de 70. För var och en: skulle beteendelagret ha fångat den om
textlagret inte fanns? Om nej — beteendelagret har ett hål som just nu är
dolt bakom en slump.

**Levererar:** `M-1NN` med de 70 uppdelade i "beteendet hade också fångat den"
och "beteendet är blint här". Den andra listan är arbete för C2.

## C5 — P-03 och de andra svaga uppgifterna

Per uppgift ser överlevarna ut så här i toppen:

```
P-03   10 överlevande   varav 7 syns bara under perturbation
S-07    7 överlevande   varav 3 skiljer på facitstimulus
C-04    5 överlevande   alla 5 osynliga
H-04    5     H-05    5     A-03    5
```

`P-03` sticker ut: sju av tio skador syns bara om man rubbar stimulusen. Det
är en uppgift vars scenarier inte utövar sin egen lösning.

Ta de fem svagaste uppgifterna och skriv om deras `scenarios` tills
överlevarna syns. Rapportera före- och eftertal per uppgift.

## C6 — mutationsmotorn är för tunn för industriell ST

Tretton skadesorter täcker inte vad som faktiskt går fel i en PLC. Sorterna som
saknas, och som var och en motsvarar ett verkligt driftfel:

* **flanken som tävlar** — `R_TRIG` som läses i fel ordning inom samma skann
* **retentiv mot icke-retentiv** — en variabel som tappar sitt värde vid
  omstart, eller behåller det när den inte borde
* **timerns förval ur en variabel** — förvalet ändras medan timern går
* **tillståndsmaskin som fastnar** — ett tillstånd utan väg ut
* **arrayindex utanför gränsen**
* **division med noll**
* **kvarhållen utgång vid stopp** — utgången nollställs inte när cykeln bryts
* **larm som kvitteras utan att orsaken försvunnit**

Bygg dem. Var och en ska ha ett känt facit — skadan själv — och en referens
som fortfarande är grön.

Kör om hela svepet efteråt. Om fångstgraden faller är det ett riktigt fynd,
inte ett misslyckande: du har hittat fler hål i domaren.

## C7 — säkra mätningen

`m122`-körningens utdata ligger i en scratchpad under `/tmp`. Den är inte i
repot, och disken var full i morse. Flytta mätningen in i
`docs/matningar/` och committa den. En mätning som bara finns i `/tmp` finns
inte.

## Om du blir klar

`docs/spec/82_felklasser.md` räknar upp felklasserna. Jämför dem mot
mutationsmotorns sorter: varje felklass som ingen mutation kan framkalla är en
klass vi påstår oss hantera utan att ha prövat det.
