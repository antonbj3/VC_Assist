# M-122 — mutationsmotorn omkörd: facitet fångar 80 % av beteendeskadorna, och det som överlever är initierare

**Datum:** 2026-09-05, kl 13:40–14:05
**Körs av:** `tests/protocol/kor_m122_mutationsskikt.py` (nytt; körningen bakom
`scratchpad/mut.txt` fanns inte på disk och gick inte att köra om)
**Rigg:** värdmaskinen, `nice 19`, fyra processer. **Ingen VC, ingen OpenPLC,
ingen STruC++, ingen modell.** Domaren är `bank/domare.dom` genom vår egen
ST-tolk — samma domare som reparationsslingan använder.
**Arbetsträdet vid körning:** HEAD `c5ce2f6`, `bank/uppgifter/L-01.json` och
`P-03.json` ändrade och ocommittade. Referenserna redigeras av en annan agent
medan detta skrivs (M-121); talen nedan är från körningen kl 14:03 och två
tidigare körningar samma timme gav 808 skador mot 809 och fem referenser med
grind 2-anmärkning mot noll. **Talen är alltså ett stickprov ur ett träd som
rör sig**, och det står i varje tabell.

## LIMITS

* **Domaren är vår tolk, inte OpenPLC och inte STruC++.** Vad som här kallas
  "fångad av beteendelagret" är fångad av det handskrivna spårfacitet körd i
  `st/tolk.py`. Samma skada genom OpenPLC kan ge annat svar (öppet sedan
  M-45).
* **"OSYNLIG" betyder inte ekvivalent.** Det betyder att fem handvalda
  perturbationer av facitets stimulus inte skilde mutant från referens.
  Ekvivalens är inte bevisad för någon av dem.
* **Radtypen (kommentar/initierare/kod) är en radskanning**, inte en parsning:
  en rad räknas som initierare om den ligger mellan `VAR` och `END_VAR`.
* **Perturbationerna är fem och handvalda:** tidsskala 0,25/0,5/2,0,
  sekvensen två gånger i rad, och booleska pulser hållna tre gånger så länge.
  En störning *under* en hållen signal (t.ex. ett fel medan återställningen
  hålls) är inte bland dem, och det är precis den som skulle synliggöra de 14
  `SYS_RESET`-mutanterna i §3.
* **Högst tre skador per sort och referens** (`per_sort=3`, motorns eget tak).
  Talen är per skada, inte per brytpunkt.
* **Varför den första körningen gav 471/806 och 14 i beteendelagret går inte
  att avgöra** — körskriptet finns inte. §1 ger en hypotes med ett mönster i
  siffrorna som stöd, inget mer.
* **Del 4 (grind 2) deklarerar signalkartan genom att skjuta in ett
  `VAR_INPUT`/`VAR_OUTPUT`-block** i referensen. Det är inte skelettets
  deklarationer; en referens kan bete sig annorlunda i `granska_station`.
* **En maskin, en förmiddag, andra agenter på samma dator och i samma träd.**
* **Det här är en A-klassmätning** i `55_innovationsplanen.md`:s mening: vår
  egen kod muterad, dömd av vårt eget facit. Den säger något om domarens
  känslighet, ingenting om huruvida facitet är rätt sak att vilja.

---

## §0 Frågan

Operatörens körning samma dag (`scratchpad/mut.txt`) gav:

> skador 806, fångade 471, släppta 335 — av vilket lager: text 457, beteende 14

och slutsatsen *"textskador fångas 100 %, beteendeskador knappt alls"*. Det
talet skulle styra ett beslut: om spårfacitet duger som beteendegrind. Ett tal
som styr ett beslut ska gå att räkna om ur sina delar (`54` §6). Skriptet
fanns inte. Så det räknades om, med den domare slingan faktiskt använder.

## §1 Reproduktionen: 718 av 809 fångade, 375 av beteendelagret

| | första körningen (`mut.txt`) | denna körning |
|---|---:|---:|
| skador | 806 | **809** |
| fångade | 471 (58 %) | **718 (89 %)** |
| fångade av textlagret (tolken vägrar) | 457 | **343** |
| fångade av beteendelagret (facit fäller) | **14** | **375** |
| överlevde | 335 | **91** |

Per sort, med lager och vad överlevarna är:

| sort | n | text | beteende | överlevde | skiljer på facitstimulus | synlig bara under perturbation | osynlig |
|---|---:|---:|---:|---:|---:|---:|---:|
| `AND_TILL_OR` | 77 | 0 | 67 | 10 | 2 | 5 | 3 |
| `OR_TILL_AND` | 35 | 0 | 31 | 4 | 0 | 2 | 2 |
| `NOT_STRUKEN` | 76 | 0 | 73 | 3 | 0 | 2 | 1 |
| `JAMFORELSE_VAND` | 57 | 2 | 54 | 1 | 0 | 0 | 1 |
| `SANT_TILL_FALSKT` | 76 | 0 | 63 | 13 | 3 | 2 | 8 |
| `FALSKT_TILL_SANT` | 78 | 0 | 21 | **57** | 6 | 0 | **51** |
| `TID_FORDUBBLAD` | 39 | 0 | 36 | 3 | 1 | 1 | 1 |
| `FLANK_TILL_NIVA` | 30 | 0 | **30** | 0 | | | |
| `FLANKENS_Q_TILL_SIGNAL` | 68 | **68** | 0 | 0 | | | |
| `END_IF_STRUKEN` | 78 | 78 | 0 | 0 | | | |
| `SEMIKOLON_STRUKET` | 78 | 78 | 0 | 0 | | | |
| `ICKE_ASCII` | 78 | 78 | 0 | 0 | | | |
| `TID_OGILTIG` | 39 | 39 | 0 | 0 | | | |

Av **466 beteendeskador** fångas **375 av facitet (80 %)**, **70 av textlagret**
(de 68 `FLANKENS_Q_TILL_SIGNAL` är typfel — instansen i stället för `.Q` — och
två vända jämförelser blev typfel) och **91 överlever**.

**Skillnaden mot första körningen förklaras inte av mig; den kan bara pekas
på.** I `mut.json` fångades `NOT_STRUKEN`, `AND_TILL_OR`, `SANT_TILL_FALSKT`
och `FALSKT_TILL_SANT` av **exakt 21 var**, alla av "text". 21 = 7 × 3: sju
uppgifter gånger motorns tak tre per sort. M-121 utreder just då **sju**
referenser som grind 2 fäller på `DUBBELSKRIVNING`/`TYP`. Hypotesen är att
den första körningen körde grind 2 före facitet och räknade referensens **egen**
rödhet som mutationens fångst — och att beteendelagret sedan aldrig nåddes för
dem. Det är en hypotes ur ett mönster. Den som hittar skriptet avgör den.

Det som **inte** är en hypotes: körningen här går att köra om, kod och tal står
i samma fil, och talet `beteende 14` är inte reproducerbart med den domare
slingan använder.

## §2 De 91 överlevarna: 64 är initierare, 27 är kodrader

| radtyp | skiljer på facitstimulus | synlig bara under perturbation | osynlig | summa |
|---|---:|---:|---:|---:|
| **initierare** (`x : BOOL := FALSE;` i `VAR`) | 9 | 0 | 55 | **64** |
| **kodrad** | 3 | 12 | 12 | **27** |
| kommentar | 0 | 0 | 0 | 0 |

`FALSKT_TILL_SANT` bär 57 av 91 överlevare, och 51 av dem är **initierare**:
ett startvärde som skrivs över i första scan. Det är inte ett hål i facitet, det
är en operator som muterar rader utan verkan. Motorn räknar dem som skador; de
är i bästa fall nio (de som skiljer på facitstimulus — ett `xLarm := FALSE`
som blivit `TRUE` och syns de första scanen innan något återställer det).

**Kodradsöverlevarna, 27 stycken, är hela den verkliga frågan.**

* **3 skiljer på facitets egen stimulus men passerar** — facitet har för få
  kontrollpunkter just där: `A-03` (`tpAck PT := T#500ms` fördubblad), `S-01`
  (`xVantarHem := (steg = 3) AND NOT …` → `OR`), `S-07` (`xKravOmstart := TRUE`
  → `FALSE`). Botemedlet är ett punktkrav till i tre uppgifter.
* **12 blir synliga bara under perturbation** — stimulus i facitet når inte
  raden. Vilken perturbation som ser dem: tidsskala ×2,0 **10 av 27**, sekvensen
  två gånger **10**, hållen puls **9**, tidsskala ×0,5 **2**, ×0,25 **1**.
  Sju av de tolv ligger i **`P-03`**. Botemedlet är en sekvens till i fem
  uppgifter (`A-03`, `H-04`, `L-07`, `P-03`, `S-07`), inte en ny grind.
* **12 är osynliga under allt som provats.** Exempel: `C-04` `IF steg < 0 OR
  steg > 7` → `AND` (en vakt som aldrig nås), `C-04` `xStopp := TRUE` i en
  gren facitet inte besöker. Troligen ekvivalenta eller döda under alla
  rimliga stimulus. Inte bevisat.

Det innebär, med nämnare: av 466 beteendeskador är **15** (3 + 12) sådana där
ett bättre facit hade fångat dem — **3,2 %**. Resten är fångade, initierare
eller onåbara.

## §3 Den saknade F15-operatorn: nivå i stället för flank

Motorns `FLANK_TILL_NIVA` heter så men gör något annat: den stryker anropet
`trig(CLK := x)`, så `trig.Q` står `FALSE` för evigt. Det är inte
`82_felklasser.md`:s F15 (*"villkoret läses på nivå i stället för på flank"*).
M-115 byggde den riktiga mutationen för hand på en leksaksmodell och bevisade
att ett spår med **en** puls inte kan se den.

Här görs den riktiga mutationen på alla 26 referenser: `inst.Q` byts mot
instansens CLK-signal.

| | |
|---:|---|
| nivåmutanter | **30**, i 24 uppgifter |
| fångade av facitet | **13** |
| överlevde | **17** |

Vilka som fångas och vilka som inte gör det är hela fyndet:

| flanken läser | fångade | överlevde |
|---|---:|---:|
| **material och process** (fotocell, pall, kolli, form öppen, PackML-kommando, index hemma, automatläge) | **12 av 12** | 0 |
| **återställningsknappen** `SYS_RESET` | 1 (`C-04`) | **14** |
| **handskakningens `DONE`** (`H-05`, `S-07`) | 0 | **2** |

**Bankens facit är inte blint för F15.** Där sekvensen håller signalen — två
burkar i rad (`S-01`), fotocellen hög en hel sekvens (`T-01
niva_ar_ingen_flank`), räknaren följer flanker (`T-04`) — faller nivåläsningen
varje gång. `C-04` fångar till och med återställningsknappen, för att dess
författare skrev sekvensen `kvitteringsknappen_star_kvar_hog`. De 14 andra
uppgifterna trycker på återställningen kort och släpper, och då är nivå och
flank samma sak.

M-115:s slutsats håller alltså i en snävare form än den skrevs: **ett spår är
blint för F15 exakt där stimulus inte håller signalen** — inte strukturellt,
utan per sekvens. Blindheten är stimulusens, och stimulus skrivs av en
människa. Ingen av de fem perturbationerna här (inte ens hållen puls ×3) gjorde
`SYS_RESET`-mutanterna synliga: att hålla knappen längre räcker inte, det
måste **hända något medan den hålls**. Det är en sekvens per uppgift, inte ett
verktyg.

## §4 Grind 2:s fällplatser: 809 mutanter fyrar 4 platser av 76

`M-111` sa: 31 av 68 fällplatser i `validator.py` har aldrig fyrat. Mutationen
"fyrar många". Går talen ihop?

| | |
|---:|---|
| fällplatser i `validator.py` i dag (M-111 omkörd 2026-09-05 13:55) | **76** (var 68; validatorn växte med M-108) |
| fyrade under hela `tests/enhet` | 41 |
| aldrig fyrade | **35** |
| mutanter som grind 2 fäller med en anmärkning referensen inte hade | **343 av 809** |
| **distinkta** fällplatser mutanterna fyrar | **4** (`TIDLITERAL:506`, `TYP:348`, `TYP:421`, `TYP:603`) |
| av de 35 aldrig fyrade som mutanterna når | **0** |

Grind 2 fäller alla fem textsorterna (273) och de 68 typfelen och två vända
jämförelser. **Noll av de 464 andra beteendeskadorna.** De 273 textfångsterna
går genom lexerns och läsarens `Syntaxfel` — inte genom en enda av
validatorns 76 fällplatser.

Talen motsäger alltså inte varandra. M-111 räknar **platser**, mutationen
**händelser**, och 809 händelser landar på fyra platser. Följden för
prioriteringen står i `55` §1.2: grind 2:s otäckta platser är inte där
beteendefelen bor, och mutation är inte vägen att nå dem.

## §5 Bifynd

* **Referenserna rör sig medan de mäts.** Kl 13:50 hade fem referenser
  (`A-07`, `C-06`, `P-06`, `T-09` `DUBBELSKRIVNING`; `T-04` `TYP`) en egen
  grind 2-anmärkning i den här riggen; kl 14:03 hade ingen det. M-121 äger
  frågan och har uppenbarligen lagat dem under tiden. Skrivs här bara som
  förklaring till att talen skiljer mellan körningar.
* **Två perturbationer bär nästan allt.** Tidsskala ×2,0 och sekvensen två
  gånger ser 10 av 12 stimulusluckor var; ×0,25 ser en. Ska en perturbation in
  i bänken är det "långsammare och två gånger", inte "tätare".

## §6 Vad det avgör

1. Spårfacitet **duger** som beteendegrind för de skador motorn gör: 80 %
   fångas, 3,2 % är facitets fel, resten motorns. Slutsatsen *"beteendeskador
   fångas knappt alls"* ska inte styra något.
2. Motorn behöver tre rättelser före nästa tal: initierare i `VAR` undantas
   från `FALSKT_TILL_SANT`/`SANT_TILL_FALSKT`; `FLANK_TILL_NIVA` byter namn
   till vad den gör (`FLANK_STRUKEN`); den riktiga nivåoperatorn ur §3 läggs
   till.
3. Facitets luckor är **lokaliserade**: tre punktkrav (`A-03`, `S-01`, `S-07`)
   och en sekvens i fem uppgifter (`A-03`, `H-04`, `L-07`, `P-03`, `S-07`),
   plus en "håll återställningen och låt ett fel hända"-sekvens där
   `SYS_RESET` läses med flank (14 uppgifter). Det är bänkarbete, inte
   verktygsarbete.
4. Grind 2:s 35 ofyrade platser nås inte av någon skada en modell rimligen
   gör i en referenskropp. De är inte prioriterade förrän en modellkropp
   faktiskt träffar dem.
