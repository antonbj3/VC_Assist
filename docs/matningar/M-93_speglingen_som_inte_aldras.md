# M-93 — speglingen som inte åldras, och de två som nu för protokollet

**Datum:** 2026-09-05
**Körs av:** `python3 -m pytest tests/enhet/test_forlopp.py tests/enhet/test_forlopp_kallor.py tests/enhet/test_forlopp_spegel.py tests/enhet/test_forlopp_forare.py -q` (131 gröna)
**Bygger:** `svc/vc_assist_svc/forlopp/spegel.py`, `forlopp/__main__.py`, och
förarna i `plan/korning.py` och `harness/loop.py`
**Fas:** 17 i `docs/spec/70_faser.md`
**Föregångare:** [M-64](M-64_vad_anvandaren_ser_medan_det_arbetar.md), som
byggde ytan och lämnade två hål med flit

**Vad användaren ser nu:**

```
PYTHONPATH=svc python3 -m vc_assist_svc.forlopp <spegelfil>
PYTHONPATH=svc python3 -m vc_assist_svc.forlopp <spegelfil> --folj 1.0
```

---

## 1. De två hålen M-64 lämnade, och vad de kostade

M-64 §9 skrev ut båda i klartext.

> **Ingenting driver ytan än.** Den går att driva, och det är en annan sak än
> att den drivs. Noll moduler i `svc/` utanför `forlopp/` konstruerar ett
> `Forlopp`.

> Ska en panel i en annan process läsa den behövs **en serialisering som inte
> finns**.

Tillsammans betydde de att ytan var byggd, provad, och osynlig. En mekanism
som finns men inte anropas är en bön med en implementation.

| | M-64 | nu |
|---|---:|---:|
| moduler i `svc/` utanför `forlopp/` som för ett `Forlopp` | **0** | **2** |
| av M-64:s sju rapportytor som når användaren under körningen | **0** | **2** |
| går ett förlopp att läsa ur en annan process? | nej | ja |
| regler över visningen, var och en med en trasig fixtur | 11 | **17** |
| prov | 82 | **131** |

De två förarna är de två som äger en körnings tidslinje:
`plan/korning.py::Korare.kor` och `harness/loop.py::Harness.kor`. Båda tar nu
`forlopp=` och för protokollet **medan** de kör.

De fem övriga rapportytorna har sin översättning byggd i `forlopp/kallor.py`
och provad — men **ingen modul i `svc/` anropar dem**. Det står som en
begränsning i §8, inte som ett halvt påstående här.

---

## 2. Fyndet: en bild som inte åldras är en död körning som ser levande ut

Serialiseringen bär en fara som inte fanns inne i processen, och den är värd
hela mätningen.

Ögonblicksbilden bär **skrivarens** tidsstämplar. En läsare som återskapar
förloppet med bildens eget `skrivet` som "nu" — vilket ser ut som omsorg, för
då mäts allt mot samma klocka — får tystnaden noll i varje avläsning.

Mätt på en fil skriven en gång och sedan aldrig mer, avläst en gång i minuten
i en timme:

| Läsarens klocka | avläsningar som säger ARBETAR |
|---|---:|
| bildens egen `skrivet` (frusen) | **60 av 60** |
| läsarens egen klocka | **0 av 60** |

Sextio av sextio. Skrivaren dog före den första avläsningen.

Det är samma odödliga körning M-64 mätte på hjärtslaget (600 av 600), med en
**annan mekanism**: den första nollade tystnadsklockan med en puls, den här
nollar den med ett filfält. Att en felklass återkommer i en ny mekanism är
skälet till att grinden måste räkna om storheten själv i stället för att fråga
det den dömer.

### 2.1 Varför förloppsytans egna regler inte kan fånga det

`granska` dömer texten mot protokollet, och det är precis rätt mot en
renderare som ljuger. Den frusna läsaren ljuger inte i texten: den bygger ett
**protokoll** som självt säger ARBETAR, och texten är korrekt mot det.

Mätt: i alla 60 avläsningarna ovan passerade `granska(forlopp, text)` utan
anmärkning. M-64 §9 förutsåg det ordagrant — *"Grinden ser inte ett protokoll
som ljuger"* — och det som var en not är nu en mekaniserad grind.

`granska_spegling` räknar därför om filens ålder **själv**, ur den råa bilden
och läsarens klocka, och läser läget ur **texten** i stället för att fråga
förloppet. Den fäller den frusna läsaren i alla 60 avläsningarna, på regel S2.

---

## 3. Tre lägen som inte fanns inne i processen

En körning i en process är antingen igång eller slut. En körning läst ur en
fil har tre lägen till, och alla tre är "vet inte":

| Vad som hänt | Vad visningen säger |
|---|---|
| filen är avhuggen, halvskriven eller talar en annan version | `LÄGE: OBESTÄMT`, med läsfelet ordagrant |
| filen står still och körningen är inte avslutad | läget härlett som vanligt, plus **skrivarens liv** som en uttalad ovisshet |
| filen är skriven i framtiden | `LÄGE: OBESTÄMT`; åldern går inte att räkna alls |

`OBESTÄMT` är nytt i `LAGEN` och ligger i `STILLA`, så en pågåendemarkör i det
läget fälls av Y2 som i alla andra stilla lägen.

**Att en avhuggen fil hade blivit `EJ STARTAT` är hela skälet till att läget
finns.** `EJ STARTAT` är ett lugnt besked. Ett läsfel som ser lugnt ut är den
falska grönen i sin renaste form, och det är I3 på visningens våning: tystnad
är aldrig ett godkännande.

En **avslutad** körning som står still är däremot helt i sin ordning — det
finns inget mer att skriva. En sparad körning från i går läses som `KLART`
eller `FALLET`, inte som obestämd. Skulle varje sparad körning bli obestämd
sa ordet ingenting.

---

## 4. LIMITS lyftes dit den läses (Y12)

Fasens svåraste krav är att `LIMITS` ska vara **lika synligt som utfallet**.
Efter M-64 var det halvt uppfyllt: en rapport UTAN sektionen fick ett eget
besked i visningen, men en rapport MED den lämnade ögats gränser där de stod —
på rad sexton av tjugofem i den råa rapporten, mellan en genomflödesrad och
domen. Y4 var nöjd: raderna nådde användaren tecken för tecken. Men en gräns
som bara går att hitta genom att läsa hela rapporten är inte lika synlig som
domen.

`Y12` är därför en regel om **placering**: ögats egna `SECTION LIMITS`-rader
ska stå efter `VET INTE:`, ordagrant, utöver att de står i rapporten. Grinden
prövar positionen i texten, inte att raden finns.

Vad det kostar och ger, samma körning med samma dom i två versioner:

| Ögonrapporten | ytan | andel om ovisshet |
|---|---:|---:|
| `EYES v1`, ingen `SECTION LIMITS` | 2 843 | 22 % |
| `EYES v2`, med `SECTION LIMITS` | 2 733 | **32 %** |

Den trasiga fixturen skriver ut rapporten hel och ordagrant och gör inget mer.
Ingen rad är omskriven, så Y4 håller — och `test_Y12_en_visning_som_bara_lamnar_granserna_i_rapporten_falls`
kräver uttryckligen att Y4 **inte** fyrar, så att provet mäter placeringen och
inte något annat.

---

## 5. De fem speglingsreglerna, och den trasiga fixtur var och en kommer ur

`REGLER = ("S1", "S2", "S3", "S4", "S5")` i `forlopp/spegel.py`. De ligger
**ovanpå** förloppsytans tolv; en spegling prövas mot alla sjutton.

| # | Regel | Trasig fixtur som fäller den |
|---|---|---|
| `S1` | en spegling som inte gick att läsa visas som OBESTÄMT, med felet ordagrant | en läsare som lämnar ett tomt förlopp när filen är borta — visningen blir `EJ STARTAT` |
| `S2` | ett arbetande läge kräver en **färsk** fil | `lasare_som_fryser_klockan` |
| `S3` | speglingen säger vilken fil den läste och hur gammal den är | en visning utan `SPEGLING:`-blocket — en inspelning som inte säger när den spelades in ser ut som nuet |
| `S4` | en pågående körning vars fil står still säger att ingen vet om skrivaren lever | en kosmetiskt lugn visning: säger TYST, men inte varför |
| `S5` | en fil skriven i framtiden är obestämd, aldrig arbetande | `alder = max(0, nu - skrivet)`, en rimlig sanering av ett omöjligt tal |

Var och en är **mätt**: stänger man av en regel i `spegel.py` faller exakt ett
prov, och alla fem provades så.

Fyra trasiga fixturer till, som ingen renderare och ingen läsare kan laga:

| Fixtur | Vad den gör | Utfall |
|---|---|---|
| **spegel som bara skriver på slutet** | skriver först när läget är avslutat | **FÄLLD**: filen visade ARBETAR i **0 av 2** avläsningar under körningen, och var obestämd däremellan |
| **bild utan räckvidden** | stryker `sensorstuds` ur ovissheterna | **FÄLLD** av läsaren. Y5 kräver posterna *ur protokollet*, så ett protokoll utan dem kräver ingenting |
| **okänd stegstatus / okänd händelsesort i bilden** | ett ord ingen gren känner igen | **FÄLLD**: bilden blir obestämd i stället för halvt läst |
| **kosmetiskt lugnt fall** | fallets skäl byts mot "Ett problem uppstod. Vi försöker igen." | **FÄLLD** av Y3 och Y4 |

---

## 6. Vad det kostar, i tal

### 6.1 Ytan

Samma körning i fyra lägen, med `M-60`:s form. Sökvägen står i visningen, så
talen gäller en 13 tecken lång sökväg (`/tmp/m/f.json`).

| Läge | förloppsytan | speglingen | rader | andel om ovisshet | skrivningar |
|---|---:|---:|---:|---:|---:|
| `ARBETAR` | 1 362 | **1 481** | 37 | 40 % | 5 |
| `FALLET` | 2 248 | **2 367** | 52 | 35 % | 8 |
| `KLART`, ögonrapport v1 | 2 843 | **2 962** | 77 | 22 % | 16 |
| `KLART`, ögonrapport v2 | 2 733 | **2 852** | 80 | 32 % | 16 |
| `OBESTÄMT` (filen borta) | — | **1 270** | 31 | — | — |

Speglingsblocket kostar **119 tecken** plus sökvägen, fyra till sex rader.
Mellan 22 % och 40 % av ytan handlar om vad systemet inte vet, och det är
avsikten.

Ingen **egen** rad är bredare än 100 tecken. Någon annans ord räknas inte, och
inte heller sökvägen: båda är givna utifrån.

### 6.2 Skrivningen växer med körningens längd

Hela bilden skrivs om vid varje händelse. Det gör kostnaden per händelse
linjär i antalet händelser, alltså **kvadratisk över en körning**.

| efter N händelser | skrivning | filen |
|---:|---:|---:|
| 10 | 0,17 ms | 1 952 byte |
| 100 | 0,18 ms | 10 863 byte |
| 500 | 0,66 ms | 50 811 byte |
| 1 000 | 1,34 ms | 100 751 byte |
| 2 000 | 2,96 ms | 201 628 byte |
| 4 000 | 6,19 ms | 403 176 byte |

En avläsning — läs, rendera, granska — kostar **10,9 ms** vid 403 kB, och
ytan är då fortfarande 1 569 tecken: trimningen håller *visningen* liten, inte
*filen*.

Inget tak är satt. Ett tak skulle behöva kasta händelser, och en händelse som
bär någon annans ord får inte kastas (Y4). Kostnaden står här i stället, mätt,
och §8 säger vad som inte är avgjort.

---

## 7. Riktig inspelad data: LIMITS finns inte i en enda sparad ögonrapport

Kravet i §4 gick att mäta mot data som redan låg på disk.

| | antal |
|---|---:|
| inspelade `EYES`-rapporter i `bank/uppgifter/*.json` | **9** |
| av dem som bär `SECTION LIMITS` | **0** |

Nio av nio är `EYES v1`. Sektionen kom med v2 (M-65), och guldgrinden kräver
den sedan dess — alltså är **ingen** av de nio guld, och en visning som ritar
ut deras dom som en dom har gjort systemet mindre ärligt, inte mer
tillgängligt.

Provet `test_varje_inspelad_ogonrapport_utan_LIMITS_sags_sakna_den` läser alla
nio ur banken, matar var och en genom ytan och kräver raden

    SEKTIONEN LIMITS SAKNAS I ÖGATS RAPPORT: den grinden har aldrig kört, så
    domen är inte ett godkännande.

samtidigt som rapporten själv står ordagrant i visningen, tecken för tecken.

### 7.1 `L-90`, hela vägen ut

`bank/uppgifter/L-90.json` bär en verklig körning från 2026-09-04: en riktig
kollision, en riktig FAIL. Genom spegeln, läst ur filen av en visare som bara
har en sökväg, ser användaren:

* `LÄGE: FALLET` på första raden,
* fallets skäl ordagrant,
* fyra grindar körda och noll fällda — och **grind 5 som fällde**, med ögats
  hela rapport rå mellan två markörrader, inklusive
  `COLLISION kolli_7 x pallkarm t=5.240s`,
* att `SECTION LIMITS` aldrig kört, så domen inte är ett godkännande,
* sex poster om vad systemet inte vet, varav fem som ingen körning kan beta av,
* och när bilden skrevs, samt hur gammal den är.

Ingen siffra i den visningen är omräknad. Ögats mått går ordagrant ut; det
enda visningen lägger till är beskedet om vilken grind som aldrig kört.

---

## 8. Vad detta INTE bevisar

* **Ingen VC kördes, ingen brygga, ingen språkmodell.** Varje källa provas mot
  attrapper. Att `Korare.kor` för protokollet rätt mot en tom utförare säger
  ingenting om vad som händer när Wine, `wineserver` eller licensservern
  faller. M-73 och M-74:s körningar lästes som text, inte som data: fas 8
  sparar inget maskinläsbart spår, så inget i den här mätningen har gått genom
  fas 8:s riktiga siffror.
* **Fem av sju rapportytor har fortfarande ingen förare.** Kopplaren,
  stationsgrinden, reparationsslingan, ögonkopplingen och guldgrinden har sin
  översättning byggd och provad i `forlopp/kallor.py`, och **noll** anropare i
  `svc/`. Halva M-64:s hål är alltså lagat, inte hela.
* **Ingen operatör har läst ytan.** Att den är läsbar är min bedömning. Att
  22–40 % av den handlar om ovisshet kan vara precis rätt eller uppenbart för
  mycket, och det avgörs av den som väntar.
* **Filen växer utan tak.** 4 000 händelser kostar 403 kB och 6,2 ms per
  skrivning, och kostnaden över en körning är kvadratisk. Vad som händer vid
  40 000 händelser är inte mätt, och inget tak är satt — det skulle kräva att
  händelser kastas, och en händelse som bär någon annans ord får inte kastas.
* **Två skrivare mot samma fil är oprövat.** `os.replace` gör varje enskild
  skrivning atomisk, men två körningar som speglar till samma sökväg skriver
  över varandra utan att någon märker det. Ingen låsning finns.
* **Klockan är väggklockan.** Åldern räknas mot `time.time()`, som kan hoppa
  vid en tidsjustering. En framåtjustering ser ut som en död skrivare
  (fail-closed, rätt håll), en bakåtjustering ger `OBESTÄMT` (också rätt håll)
  — men ingen av dem är **mätt** mot en riktig NTP-justering, och `CLOCK_MONOTONIC`
  duger inte, för den är inte jämförbar mellan två processer.
* **`TYSTNADSTAK_S = 5,0 s` är fortfarande preliminär** och sätts av M-28.
  Speglingen ärver den tröskeln rakt av: den avgör både när läget blir TYST
  och när en fil räknas som stillastående. Ett tak som är fel gör alltså två
  saker fel samtidigt.
* **Fält 1 och 7 i `26_appen.md` §3** — samtalet och systemläget — finns
  fortfarande inte. De kräver en levande brygga. `A-G4` är inte stängd.
* **Ingen webbsida är byggd.** Ytan är text, och `26_appen.md` §7 fråga 1 —
  webbläsare eller terminal — är fortfarande operatörens att svara på. Grinden
  dömer texten, så den binder ändå den panelen den dag den skrivs.
* **De fem posterna utanför räckvidd är en avskrift**, inte en mätning. De
  står i `50_grindar.md` och är rimliga. Ingen har mätt att listan är
  fullständig.
* **Windows är inte kört.** `os.replace` och `tempfile.mkstemp` beter sig
  annorlunda där när en läsare håller filen öppen. Plattform: Linux ☑
  Windows ☐.

## LIMITS

Punkterna i §8 är den fullständiga listan över vad mätningen inte visar. De
tre som väger tyngst:

* **fem av sju rapportytor har ingen förare** — halva M-64:s hål står kvar,
* **ingen riktig körning** har passerat den här koden: ingen VC, ingen brygga,
  ingen modell, och inget maskinläsbart spår ur fas 8,
* **ingen människa utanför bygget har läst ytan**, så att den är begriplig är
  en bedömning och inte ett mätvärde.
