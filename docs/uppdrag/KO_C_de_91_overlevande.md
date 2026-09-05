# Kö C — de 91 skador bänken inte ser

Läs `docs/uppdrag/00_GEMENSAMT.md` först.

## Din yta

`svc/vc_assist_svc/plc/mutation.py`, `bank/domare.py`, `bank/uppgifter/*.json`
(bara fältet `scenarios`, och bara efter C2), `tests/protocol/kor_C*`,
`tests/enhet/test_mutation_*`, `docs/spec/83_scenarier.md`,
`docs/spec/82_felklasser.md`, dina egna `docs/matningar/M-1xx`.

## Läget, mätt — och rättat samma dag

**Läs `docs/matningar/M-122_mutationsskikten_omkorda.md` innan du gör något
annat.** En tidigare körning gav ett tal som såg ut som en blind bänk. Det höll
inte. Så här ser det ut när mätningen är omkörd med slingans egen domare:

```
skador 809   fångade 718 (89 %)   överlevde 91
av 466 beteendeskador: 375 fångade av facitet (80 %), 70 av textlagret
```

Och överlevarna är inte vad de såg ut att vara:

```
91 överlevare = 64 initierare + 27 kodrader
```

**64 av 91 är initierare** — `x : BOOL := FALSE;` inne i `VAR`, en rad som
skrivs över innan någon läser den. Att byta den mot `TRUE` ändrar ingenting, och
att bänken inte ser det är **motorns fel, inte bänkens**. `FALSKT_TILL_SANT`
bär 57 av 91 överlevare och 51 av dem är just initierare.

Av de 27 kodraderna hade ett bättre facit fångat **15**. Det är **3,2 %** av
beteendeskadorna. Det är bänkens verkliga hål, och det är litet.

**Vad du ska ta med dig:** talet 91 mätte till största delen vår egen
mutationsmotor. Ett tal som mäter mätaren i stället för det mätta är precis den
fälla projektet är strängast mot. Bygg inte tio timmar ovanpå det igen — börja
med C0.

## Det verkligt stora fyndet, som inte handlar om överlevarna

`M-122 §4`: **809 mutanter fyrar 4 av grind 2:s 76 fällplatser.** Grind 2 —
den statiska analysen — fäller **noll av 464 beteendeskador**.

Det betyder att ett helt grindsteg i kedjan inte bidrar med någonting mot
beteendefel. Det är en större sak än de 91, och den har ingen punkt i någon
annan kö. Den är C6 och C7 nedan.

## C0 — motorns tre rättelser, före allt annat

`M-122` namnger dem. Gör dem först; varje tal före dem är ovärderligt.

1. **Initierare i `VAR` undantas.** En rad mellan `VAR` och `END_VAR` som sätter
   ett startvärde är inte en skada värd att räkna — den skrivs över innan den
   läses. 64 av 91 överlevare försvinner med den enda ändringen.
2. Radtypen avgörs idag av en **radskanning**, inte en parsning: en rad räknas
   som initierare om den ligger mellan `VAR` och `END_VAR`. Det är grovt och
   det ska sägas i utdatan så länge det står kvar.
3. `M-122` LIMITS namnger den tredje. Läs den där, inte här.

Kör om svepet efteråt. **Det nya talet är utgångsläget för hela kön** — och
det är sannolikt betydligt bättre än 89 %, vilket är ett bra resultat, inte ett
antiklimax.

**Trasig fixtur:** en mutation av en initierare ska efter rättelsen inte längre
räknas som en skada alls, och provet ska fälla om den kommer tillbaka.

## C1 — de 15 som är bänkens verkliga hål

Efter C0 återstår kärnan: 27 kodradsskador överlever, och ett bättre facit hade
fångat **15** av dem.

Femton är få nog att gå igenom en och en. För var och en: vilket påstående i
uppgiftens `facit_spar` saknas, och varför skrevs det inte? Om samma orsak
återkommer har du hittat en systematisk lucka i hur facit skrivs — och den är
värd mer än de femton fallen.

**Levererar:** `M-1NN` med femton rader, var och en med uppgift, skada, det
saknade påståendet och orsaken. Inte en lista på femton utan en klassning.

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

---

## Överflöd — när de sju punkterna är slut

**C8. Mutera domaren i stället för koden.** Vänd på det: skada `bank/domare.py`
och se om provsviten fångar det. En domare som fortfarande dömer rätt med en
skadad regel har en regel som aldrig används.

**C9. Skada specen.** Ändra ett krav i en uppgifts `expect` och kontrollera att
referenslösningen då blir röd. Om den förblir grön prövar uppgiften inte det
kravet — och kravet står i specen utan att någonsin mätas.

**C10. Två skador samtidigt.** Alla 808 skador är enskilda. I verkligheten
kommer fel i par, och två fel kan ta ut varandra så att utfallet ser rätt ut.
Kör par av skador på de uppgifter som har flest överlevare och räkna hur ofta
paret är osynligt fast båda delarna var synliga var för sig.

**C11. Hur många stimuli behövs egentligen.** Om fångstgraden är lika hög med
hälften av scenarierna är hälften av dem dekoration. Svep: ta bort scenarier ett
i taget och mät. De scenarier som inte ändrar något kan strykas — eller så
avslöjar de att bänken inte mäter det de var till för.

**C12. Kalibrera mot verkliga buggar.** Mutationerna är påhittade fel. Leta i
`docs/spec/82_felklasser.md` och i projektets egna mätningar efter fel som
faktiskt inträffat, och kontrollera att mutationsmotorn kan framkalla var och
en. En motor som bara gör fel vi hittat på mäter vår fantasi, inte verkligheten.
