# M-45 — bankens täckning: hur många uppgifter har ett facit en domare kan läsa

**Datum:** 2026-09-04 · python 3, inget VC, ingen OpenPLC, ingen STruC++
**Frågan:** bänken har 47 uppgifter. Hur många av dem kan man **döma en
inlämnad lösning på** i dag?

**Svaret:** noll av 47.

Det är hela poängen med mätningen, och siffran skrivs ut därför att den är
pinsam. Banken var inte tom på facit. Den var full av facit som ingen kunde
köra.

---

## 1. Vad som fanns, räknat

Räknat 2026-09-04 över `bank/uppgifter/*.json` med `bank/lasare.py`.

| Storhet | k av n |
|---|---|
| uppgifter i banken | 47 |
| uppgifter vars facit ligger på ögat (`expect.gate = OGAT`) | 42 av 47 |
| uppgifter vars facit ligger på en förgrind (`G1`–`G4`) | 5 av 47 |
| uppgifter med `last_run` | **0 av 47** |
| uppgifter med `verified_status` över `unverified` | **0 av 47** |
| uppgifter vars facit binder insignaler till utsignaler över tid | **0 av 47** |

Nämnaren står med i varje rad med flit. En bänk vars minsta mängd är sju
uppgifter rör sig i steg om fjorton procentenheter, och ett tal utan nämnare
döljer det.

### Vad de 42 ögonuppgifternas facit faktiskt är

`expect.lines` är rader ur ögats grammatik med `*` där talen ska stå:

```json
{"section": "TIMING", "template": "DWELL ST010 *s req=0.4s OK"}
```

Det är ett riktigt facit — men det är ett facit **om en ögonrapport**. För att
hålla en lösning mot det krävs: en byggd scen i Visual Components, en körning,
och en ögonrapport ur den körningen. Ingen uppgift har någon av delarna. Alla 47
har `last_run: null`.

Facit är alltså skrivet före försöket, precis som regeln kräver, men det finns
ingen väg från en inlämnad ST-fil till en dom.

### Vad som ändå gick att döma mekaniskt, och varför det inte räknas

Nio av de fjorton medvetet trasiga varianterna bär en färdigskriven ögonrapport
i `broken.artefakt`. `lasare.Uppgift.jamfor()` håller facit mot den, och det
fungerar: **9 av 9** uppfyller sitt facit i dag, mätt.

Men det som prövas är att facitraderna finns i en text jag själv skrivit i samma
fil. Det är en fixtur som håller sin egen mall. Det bevisar att jämförelsen
fungerar. Det säger ingenting om en lösning någon lämnat in.

Fyra varianter bär i stället en ST-artefakt med en förgrindskod som facit.
Mätt vad koden i repot gör med dem i dag:

| Uppgift | Grind | Facit | Vad som händer nu |
|---|---|---|---|
| `T-90` | G1 | `F1` | ST-läsaren fäller den på syntax — men läsaren är inte STruC++ |
| `A-90` | G1 | `F4` | parsas; validatorn ger 6 anmärkningar, ingen av dem är grind 1 |
| `P-90` | G2 | `F2` | parsas; validatorn ger 9 anmärkningar, `OKANT_NAMN` bland dem |
| `S-90` | G3 | `F3` | parsas; deklarationsgrinden behöver en signalkarta som banken inte bär |

Grind 1 är `STruC++` och är inte körd här. Att läsaren också råkar fälla `T-90`
är en proxy, inte grinden.

**Summan: 0 av 47 uppgifter kunde döma en inlämnad lösning.**

---

## 2. Vad som saknades, uttryckt som en storhet

Bänken hade en facitform, och den mätte **scenen**: gick produkten fram, kolliderade
något, nåddes takten. Den formen är rätt och ska inte bort — ögat fäller domen om
scenen (invariant I1).

Men den saknade den facitform som en driftsättare använder på skrivbordet innan
någon släpper in en robot i cellen: **håller styrlogiken sitt kontrakt mot
insignalerna över tid?** Den storheten går att döma utan VC, utan scen och utan
robot, och det är den som avgör om en station går att driftsätta.

Skillnaden är inte akademisk. Litteraturen (destillerad i
`docs/research/R-01_llm_st_och_softplc.md`) mäter samma sak: statiska poäng
skiljer metoder med några få poäng, körningspoäng med mer än det dubbla.
Kompileringsgrad är uttömd som mått. Det som separerar är att köra.

---

## 3. Vad "industrirealistisk" måste betyda, och vad det kostade

En station som en driftsättare accepterar har sju saker som de 47 uppgifterna
beskrev i prosa men aldrig prövade mekaniskt:

1. en driftsordning
2. ett latchat larmläge
3. ett nödstopp som bara får läsas, aldrig implementeras
4. en **kvitterad** återstartsekvens
5. en handkörning som är håll-för-att-köra
6. en tidsövervakning som fäller när något fastnar
7. en förregling som hindrar två rörelser samtidigt

Punkt 4 är den som skiljer en bänkuppgift från en driftsatt station, och den
har ett publicerat facit:

> **ISO 13850:2015, 4.1.4:** *"The disengagement of the device shall not restart
> the machinery but only permit restarting."*
> **ISO 13850:2015, 4.1.1.2:** *"The reset shall not initiate machine start up."*
> **IEC 60204-1 Ed. 6.0 (2016), 9.2.3.4:** *"The reset of the command shall not
> restart the machinery but only permit restarting."*

Klausulnumren är verifierade i en egen källkontroll 2026-09-04. Notera att
nödstoppet i 2016-utgåvan av IEC 60204-1 ligger i **9.2.3.4**, inte i 9.2.5.4.2
som i den utgångna femte utgåvan; den förväxlingen är lätt att göra och står här
för att ingen ska göra den igen.

Punkt 3 är inte förhandlingsbar och är redan lag i repot
(`docs/spec/50_grindar.md`, säkerhetsgränsen): **ingen genererad kod rör en
säkerhetsfunktion.** Alla nya uppgifter läser `EMG_OK` och är förreglade av den.
Ingen av dem implementerar den.

---

## 4. Utvidgningen: spårfacit

Ett nytt, **frivilligt** fält `facit_spar` i uppgiftsposten. Bakåtkompatibelt:
de 47 gamla uppgifterna saknar det och går igenom lintern oförändrade. Det
prövas av `tests/enhet/test_bank.py` som fortsatt läser hela banken.

Spårfacit ligger **bredvid** ögonfacit, aldrig i stället för det. De dömer olika
storheter: ögat dömer scenen, spåret dömer logiken.

### Tre sorters påstående, alla mekaniska

**Punktkrav** — vid tiden *t*, med de här insignalerna, ska utsignalerna ha
precis de här värdena.

```json
{"t_ms": 1800, "satt": {}, "krav": {"ST050_CNV_RUN": false},
 "varfor": "att nodstoppsdonet dras upp ar ingen startorder"}
```

**Invariant** — närhelst villkoret gäller ska kravet gälla, prövat i varje scan.
Det är förreglingens form:

```json
{"namn": "inget_index_utan_klamma",
 "nar": {"ST050_IDX_START": true}, "kraver": {"ST050_CLP_CLOSED": true}}
```

**Flankräkning** — antalet flanker på en utgång inom ett fönster. Det är
singuleringens form, och den **enda mekaniska domen över felklass `F15`**:

```json
{"namn": "ett_index_per_detalj", "signal": "ST050_IDX_START",
 "typ": "RISE", "fran_ms": 0, "till_ms": 1400, "antal": 1}
```

### Marginalregeln, som är en mätning och inte en smaksak

Ett punktkrav måste ligga minst **två scan** efter den senaste ändringen av en
insignal i samma sekvens. Lintern (`M33_SPARFACIT`) avvisar annars uppgiften,
och `tests/enhet/test_domare.py` mäter det över hela banken.

Två scan är inte gissat: `M-20` mätte PLC:ns egen svarstid till **exakt två
scan, 40,0 ms vid 20 ms scanperiod**. Under den marginalen skiljer facit inte
längre på "implementationen svarar ett scan senare" och "implementationen gör
fel", och bänken mäter kodstil i stället för styrlogik.

Av samma skäl anges varje tidsövervakning som ett **fönster** i uppgiftstexten:
"vakten ska falla tidigast 1,9 s och senast 2,4 s efter flanken". Facit prövar
båda ändarna. En för kort tidsvakt stoppar linjen på normal drift, och det är
lika mycket ett fel som en tidsvakt som saknas.

### Referens och motbevis: facit måste vara både uppfyllbart och fällande

Varje spårfacit bär två saker till:

* en **referenslösning** som uppfyller det. Ett facit ingen kan uppfylla fäller
  alla och ser ut som en svår bänk. Referensen är beviset att facit går att nå.
* minst ett **motbevis**: en lösning som ser riktig ut men bryter mot ett krav,
  med en lista över exakt vilka brister domaren ska fälla den på. Ett motbevis
  som fälls av fel skäl är ingen fixtur, det är en slump.

Referensen får aldrig hamna i `prompt`. Lintern och ett prov jämför texterna.

**Modellen skriver aldrig sitt eget facit.** Skälet är mätt av någon annan:
Koziolek m.fl. (arXiv 2405.01874) lät en modell generera testfall till
OSCAT-block och fick 0–50 % korrekta assertions, sämst på just timers.

---

## 5. Domaren: en ST-tolk, inte en modellkontroll

`svc/vc_assist_svc/st/tolk.py` kör ett ST-`PROGRAM` scan för scan i minnet, över
AST:t från repots egen ST-läsare. Den kör med **20 ms scanperiod**, samma som
`M-20` mätte och samma som OpenPLC Runtime v4 använder som fallback.

Standardfunktionsblocken följer IEC 61131-3 och provas mot standardens egna
tidsdiagram, inte mot sig själva:

* `TON`: `Q` hög när `IN` varit hög i `PT`; **`ET` nollställs när `IN` faller**,
  den fryser inte.
* `TOF`: `Q` följer `IN` upp direkt och släpper `PT` efter fallet.
* `TP`: pulsen går inte att trigga om under sin gång.
* `R_TRIG`/`F_TRIG`: `Q` hög i exakt ett scan.
* `SR` är **set-dominant** (`S1`), `RS` är **reset-dominant** (`R1`). Den
  dominanta ingången bär siffran 1.

Tolken fäller dessutom tre saker en kompilator släpper igenom:

* en skrivning till en **insignal** — en logik som sätter sin egen givare mäter
  ingenting
* ett odeklarerat namn
* en oändlig loop, med ett tak i stället för en hängd pytest

### Varför en tolk och inte formell verifiering

Grindkedjan i `docs/spec/50_grindar.md` har ingen modellkontroll, och den ska
inte få någon. Skälet står nu utskrivet i specen: PLCverif täcker ~25 % av ST,
och SemaPLC rapporterar **noll avgörbara utfall** för uppgifter som bär en
`TON`. Tidsfel passerar den grinden tyst — och tidsfel är precis vad den här
bänken mäter.

### Vad tolken INTE är

Den är **inte** OpenPLC och **inte** STruC++. Två motorer på samma facit kan
drifta isär.

Det ska mätas när kedjan står: samma spår genom tolken och genom OpenPLC v4 över
OPC UA, med skillnaden per signal och per scan redovisad. Kedjan är byggd och
mätt (`M-20`, `M-39`: kopplarvarv 89,11 ms median, PLC:ns svar exakt två scan).
Tills den mätningen finns är tolkens dom en dom om **ST-semantiken**, inte om
runtimen, och det står i modulens huvud.

En känd skillnad är redan hittad: `bank/schema.py`:s tidsliteralläsare avvisar
`T#400MS` med versaler, medan IEC 61131-3:s egna exempel innehåller både
`t#14.7s` och `TIME#25h_15m` — prefixet och enheterna är skiftlägesokänsliga.
Tolken försöker därför en gång till med gemener innan den fäller, så att den
inte underkänner kod som runtimen accepterar. ST-lagrets validator är oförändrad;
den frågan hör till den som äger `svc/vc_assist_svc/st/lexer.py`.

### Domaren bygger ingen egen grindkedja

`bank/domare.py` tar emot en `Stationsdom` ur
`svc/vc_assist_svc/plc/stationsgrind.py`. Har någon av grind 1–4 fällt returneras
**den grindens egna ord, ordagrant**, och spåret körs inte alls. Det är invariant
I1 och sorteringsregel 1 i `docs/spec/82_felklasser.md`: första grinden som fäller
bestämmer klassen, och en grind som skriver om en annan grinds svar mäter till
slut sig själv.

---

## 6. Vad som byggdes, räknat

Fyra nya uppgifter, alla med spårfacit, referenslösning och motbevis.

| Uppgift | Station | Vad den prövar | Standard facit lutar sig mot |
|---|---|---|---|
| `T-07` | indexerad matare | tidsövervakning, latchat larm, kvitterad omstart, förregling mot klämman | ISO 13850:2015 4.1.4, IEC 61131-3 `TON` |
| `H-04` | överlämning robot→robot | fyrsignalshandskakning, kvittensvakt, ömsesidig uteslutning, greppordning | bankens handskakningskonvention, IEC 60204-1 |
| `S-05` | PackML-tillståndsmaskin | alla 17 tillstånd, 9 kommandon, vägen ut ur `ABORTED`, drift endast i `EXECUTE` | **ISA-TR88.00.02 (PackML), Production Mode** |
| `L-05` | palletering med lyftbord | håll-för-att-köra, lägesväljare, ömsesidig uteslutning, lyftvakt | IEC 60204-1 håll-för-att-köra, ISO 13850:2015 |

| Storhet | k av n |
|---|---|
| uppgifter i banken efter M-45 | 51 |
| uppgifter med spårfacit | 4 av 51 |
| spårsekvenser | 33 |
| punktkrav (enskilda signalvärden) | 190 |
| invarianter | 18 |
| flankkrav | 10 |
| **mekaniska påståenden totalt** | **218** |
| motbevis | 18 |
| motbevis som domaren fäller, på just den brist de namnger | **18 av 18** |
| scan som körs när hela banken döms | 3 071 (61,4 s simulerad tid) |

Hela domen körs i `python3 -m pytest tests/enhet/test_domare.py -q` på under två
sekunder, utan VC, utan OpenPLC och utan nät.

### PackML-facit, och varför det är ett bra facit

`S-05` lutar sig på ISA-TR88.00.02 därför att övergångarna är entydigt
definierade. Numreringen är verifierad i tre oberoende källor (Beckhoffs
`E_PMLState` med kommentaren *"states according to PackTags v3.0"*, Omrons
implementationsguide, och OPC 30050 v1.01):

```
 1 Clearing   2 Stopped    3 Starting     4 Idle        5 Suspended  6 Execute
 7 Stopping   8 Aborting   9 Aborted     10 Holding    11 Held      12 Unholding
13 Suspending 14 Unsuspending 15 Resetting 16 Completing 17 Complete
```

Kommandona är `CntrlCmd` 1–9: Reset, Start, Stop, Hold, Unhold, Suspend,
Unsuspend, Abort, Clear. **"Complete" är inget kommando** — övergången
`Execute → Completing` sker på State Complete.

Tre regler ur matrisen som facit prövar särskilt, och som en genväg alltid
bryter mot:

* **`ABORT` får inte genvägas till `STOPPED`.** Den går till `ABORTING`, och
  först på State Complete till `ABORTED`. `ABORT` är giltigt i 15 av 17
  tillstånd — alla utom `ABORTING` och `ABORTED`.
* **Enda vägen ut ur `ABORTED` är `CLEAR`.** `RESET` och `STOP` gör ingenting
  där. TR88: *"The machine can only exit the ABORTED state after an explicit
  CLEAR command, subsequently to manual intervention."*
* **`HOLD` och `SUSPEND` är olika grenar.** `HOLDING` är ett **internt**
  villkor, `SUSPENDING` ett **externt** (svält eller blockering). Slås de ihop
  hamnar OEE-räkningen på fel konto.

En sak i uppgiften avviker medvetet från PackTags: `ST200_PML_STATE` är
deklarerad `int` därför att bankens signaltyper är `bool`, `int` och `real`. I
PackTags är `Status.StateCurrent` en `DINT`, och i OPC UA en `Int32`. Det står
här så att ingen tror att banken påstår något annat.

### Motbevisen är riktiga driftsättningsmissar, inte påhitt

De 18 motbevisen är alla kod som ser riktig ut och går igenom en normalkörning.
Fyra exempel:

* `automatisk_omstart_efter_nodstopp` (`T-07`) — driftsvillkoret är
  `EMG_OK AND AIR_OK AND SYS_AUTO` utan omstartskvittens. Stationen startar i
  samma scan som någon drar upp nödstoppsdonet, med en operatör kvar i cellen.
  Fälls på `nodstopp_utan_automatisk_omstart@1800ms:ST050_CNV_RUN`.
* `larmet_slapper_av_sig_sjalvt` (`T-07`) — `SYS_ALARM` speglar tidsvaktens
  utgång i stället för att latchas. När vakten faller nollställs kommandot,
  vakten släpper, och larmet försvinner inom ett scan. Det är felklass `F15`.
* `slapper_pa_lagesbekraftelsen` (`H-04`) — avlämnaren öppnar sitt gripdon när
  mottagaren står i läge, inte när den bekräftat greppet. Går igenom varje gång
  gripdonet råkar hinna stänga först.
* `handkorningen_latchas` (`L-05`) — håll-för-att-köra blir en latchad rörelse.
  Fungerar i en provkörning där operatören håller knappen hela vägen, och blir
  farligt första gången hen släpper.

---

## 7. Felklassen som saknades: `F15` flank och latch

Ur `docs/research/R-01_llm_st_och_softplc.md` §1.4: **ingen publicerad
LLM-utvärdering mäter flank- eller latchfel.** Två av repots egna dokument lutar
sig redan på klassen utan att kunna namnge den —
`docs/spec/61_st_generering.md` sätter "flanker" först bland det som brukar gå
fel, och `tests/protocol/fas7_stationen.md` gör "nivåläsning där en flank krävs"
till trasigt fall T3.

Nio bankuppgifter bar redan materialet men var taggade `F5`, `F6`, `F7` eller
`F8`, så det enda tal ingen annan har gick förlorat i våra egna kolumner.

`F15` är därför tillagd i `docs/spec/82_felklasser.md` och nio uppgifter är
omtaggade — `T-01`, `T-03`, `T-04`, `T-06`, `T-91`, `S-01`, `S-03`, `L-04`,
`A-06` — plus de två nya `T-07` och `L-05`. **11 av 51** uppgifter bär klassen,
varav en (`T-91`) är en trasig variant som fäller den. Ingen ny uppgift behövdes.

Flankräkningen i spårfacit är den mekaniska domen över `F15`. Ett motbevis som
kommenderar på nivå i stället för på flank ger två flanker där facit kräver en,
och fälls på talet.

---

## 8. Vad som INTE är prövat

Detta avsnitt är längre än det bekväma, med flit.

* **Ingen uppgift är körd i VC.** `last_run` är `null` för 51 av 51, och
  `verified_status` är `unverified` för 51 av 51. Svårighetsgraderna är
  `DEKLARERAD`, inte `MATT`.
* **Ingen uppgift är körd i OpenPLC.** Tolken och runtimen är inte jämförda.
  Det är den mätning som ska följa på den här.
* **Ingen uppgift är kompilerad av STruC++.** Referenslösningarna går genom
  repots ST-läsare och tolk. Att de kompilerar är ett rimligt antagande, inte en
  mätning. Grind 1 är inte körd.
* **47 av 51 uppgifter har fortfarande inget spårfacit.** De fyra nya är ett
  mönster att växa på, inte en färdig bank. Ordningen bör vara grupp för grupp,
  och varje ny uppgift kostar ungefär lika mycket som en av de fyra.
* **Spårfacit är boolesk och heltalig logik.** Det finns ingen fysik i det:
  ingen transportör som faktiskt går, ingen detalj som färdas. Den storheten hör
  till ögat, och den mätningen är fortfarande obetald.
* **Referenslösningarna är skrivna av mig.** De bevisar att facit är uppfyllbart.
  De bevisar inte att facit är det *enda* rimliga sättet att lösa uppgiften, och
  en lösning som är riktig på ett annat sätt måste släppas igenom. Marginalregeln
  och fönstren kring tidsvakterna finns för det. Om en riktig lösning ändå fälls
  är det facit som är fel, inte lösningen.
* **Ingen baslinje.** `docs/spec/83_scenarier.md` kräver samma uppgifter körda
  med en klassisk metod under samma budget. Den jämförelsen är inte byggd, och
  utan den är varje tal härifrån bara ett tal.
* **Inget tal härifrån får jämföras med ett publicerat tal.** Nämnarna i fältet
  är 3, 10, 21, 23, 25, 40, 65, 100, 117, 200, 420, 914 och 2 390, och måtten
  mäter olika saker: kompilering hos LLM4PLC, modellkontroll hos Agents4PLC,
  leverantörskompilering hos AutoPLC, spårjämförelse hos SemaPLC. Vår 218
  mekaniska påståenden över 4 uppgifter är inte jämförbar med någon av dem, och
  ska inte presenteras som om den vore.

---

## 9. Trösklar som M-45 sätter

| Konstant | Fil | Värde | Skäl |
|---|---|---|---|
| `SCAN_MS` | `st/tolk.py` | 20,0 ms | **mätt i M-20**: PLC:ns svarstid är exakt två scan, 40,0 ms vid 20 ms scanperiod. Samma tal är OpenPLC v4:s fallback-tick |
| `MARGINAL_SCAN` | `bank/domare.py`, `bank/schema.py` | 2 scan | **mätt i M-20**: den tid kedjan bevisligen tar. Under den mäter facit kodstil |
| `MAX_LOOPVARV` | `st/tolk.py` | 10 000 | satt. Ingen uppgift i banken har en loop över hundra varv; taket ska falla långt innan pytest ser ut att hänga |
| `MAX_SCAN` | `st/tolk.py` | 100 000 | satt. Bänkens längsta spår är 996 scan; taket ligger två tiopotenser över |
| `MIN_MOTBEVIS` | `bank/schema.py` | 1 | regel S2 i `docs/spec/96_ingen_skuld.md`: ingen grind utan trasig fixtur |

---

## 10. Hur man kör det

```
python3 -m pytest tests/enhet/test_domare.py -q     # hela domen, utan VC
python3 bank/domare.py --uppgift T-07               # referens + alla motbevis
python3 bank/domare.py --uppgift S-05 --st min.st   # döm en egen lösning
python3 bank/lasare.py                              # täckning per felklass
```
