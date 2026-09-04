# Samtalsloopen

Turordningen från operatörens mening till ett **bevisat** svar.

*beskriver:* `svc/vc_assist_svc/llm/loop.py` (obyggd), och binder mot det
byggda: `svc/vc_assist_svc/klient.py`, `verktyg/utforare.py`,
`verktyg/formagegrind.py`, `guldgrind.py`, `ext/vc_addon/vc_assist/pump.py`.

Detta dokument äger **mekaniken i en tur**. Det äger inte hur uppgiften bryts
ned — det gör `22_planeringslagret.md`. Det äger inte vad som får plats — det
gör `25_kontextbudget.md`. Det äger inte kontraktet mot modellen — det gör
`23_llm_granssnitt.md`.

---

## 1. Turen, steg för steg

Elva steg. Kolumnen längst till höger är den viktiga: **vad som händer när
steget faller**. Ett steg utan den kolumnen är ospecat.

| # | Steg | Gör | När det faller |
|---|---|---|---|
| 0 | **Meningen** | operatören skriver | — |
| 1 | **Läget** | `ping` mot bryggan: VC-version, `degraded`, `ko_vantande` | inget svar ⇒ `BRYGGA_NERE`, avsnitt 5. **Modellen anropas inte** |
| 2 | **Förmågan** | läs förmågerapporten, bygg `Urval` | ingen rapport ⇒ **alla verktyg av** (KOD@HEAD, `urval_ur_rapport(None)`). Turen blir ett lägesbesked, inte ett bygge |
| 3 | **Planen** | `22_planeringslagret.md` | se det dokumentet. Faller planen levereras dess eget skäl; ingen kod genereras |
| 4 | **Prompten** | `bygg_systemprompt()`, B1–B7 | saknat obligatoriskt block **kastar** (S1). Turen avbryts före modellanropet |
| 5 | **Urvalet** | verktygen som exponeras | tomt urval ⇒ som steg 2 |
| 6 | **Modellanropet** | adaptern, `23_llm_granssnitt.md` | tidsöverdrag eller leverantörsfel ⇒ **ett** omförsök, sedan `TAK_TID`. Aldrig tyst |
| 7 | **Verktygsanropen** | tabellen i avsnitt 2 | felnyckeln går tillbaka till modellen, rundan räknas. 6 raka ⇒ `TAK_FALL` |
| 8 | **Loopen** | tillbaka till 6 tills en stoppkod | stoppkoden levereras med sitt namn (`23`, avsnitt 6) |
| 9 | **Körningen** | `eyes_start` → simulering → `eyes_stop` → `oga_analys` → domstext | avsnitt 4 |
| 10 | **Domen** | `guldgrind.doma()` läser ögats **egen** text | `NOT GOLD` med skäl. Aldrig en omtolkning |
| 11 | **Svaret** | verify-contract, sedan honesty-rewrite, sedan leverans | `23`, avsnitt 4 och 5 |

**Ordningen i steg 11 är inte godtycklig.** Verify-contract kan skapa nya fall
(ett `MOTSAGD` påstående), och honesty-rewrite måste se dem. Kör man dem i
omvänd ordning kan ett svar passera honesty och sedan visa sig falskt utan att
någon grind ser det.

### Steg 9 kräver inte att modellen ber om det

En uppgift som säger "bygg och få det att fungera" **måste** köras.
Modellen får aldrig avsluta en byggnadstur med ett påstående om att det
fungerar utan att ögat har kört. *Mekanik:* om turens plan innehåller ett
byggsteg och ingen `eyes_stop` har skett, är turens högsta möjliga utfall
`candidate` — och `candidate` är aldrig leverans (`50_grindar.md`).

---

## 2. Ett verktygsanrop, i ordning

Detta är byggt och beskrivs som det är, inte som det borde vara.

| # | Led | Modul | Fall |
|---|---|---|---|
| 1 | Slå upp namnet | `utforare._verktyg` | `OkantVerktyg`, med antalet registrerade |
| 2 | Förmågegrinden | `Urval.krav` | `Avstangt`, med ytan som saknas |
| 3 | Validera argument | `validera_argument` | `Argumentfel` med **hela** problemlistan, inte det första felet |
| 4 | `mode=data` | handlaren i tjänsten | resultatet valideras mot `returns` |
| 4' | `mode=codegen` | handlaren returnerar en **kodsträng** | inte en sträng ⇒ `Svarsfel` |
| 5 | AST-validering | `api_index.Validator` — grind 4 | okänt VC-namn ⇒ anropet skickas aldrig |
| 6 | Läge ur `effect` | `op_for_effect` | `read → exec`, `write → exec_queue`. Enda stället |
| 7a | `exec` | bryggan kör direkt | sista raden på stdout inte JSON ⇒ `Svarsfel`. **Tystnad är aldrig ett godkännande** |
| 7b | `exec_queue` | posten köas, `qid` tillbaka | inget `qid` ⇒ `Svarsfel` |
| 8 | Godkännande | operatören, avsnitt 3 | `rejected` ⇒ fall med kod `KO_REJECTED` |
| 9 | Utfallet läses **ur kön** | `queue_list`, inte ur godkännandets svar | skälet är mätt: pumpen kan dö mitt i sitt eget svar (M-13) |
| 10 | Validera resultat | `validera_resultat` | `Svarsfel`. Ett svar som inte håller sin form är inget svar |

Led 5 ligger **före** led 6 med flit. En kodsträng med ett uppfunnet API-namn
ska aldrig nå bryggan — inte ens som en köad post som operatören sedan måste
avvisa.

---

## 3. Godkännandekön i en tur

`effect=write` betyder kö (I12). Kön är **inte** en formalitet: i källprojektet
har `pop_pending_patch` noll anropare och kön är död. Här har den en tömmare
från dag ett.

| Läge | Vad operatören ser | Vad tjänsten gör |
|---|---|---|
| `pending` | verktygets `beskriv_anrop()` — en rad, argumenten utskrivna | väntar. Stoppkod `VANTAR_GODKANNANDE` |
| `pending` med `dodar_pumpen` | samma rad **plus** varningen, **före** körningen | se nedan |
| `approved` | "körs" | pumpen betar av en post per varv |
| `done` | resultatet | valideras mot `returns` |
| `failed` | felet | fall, kod `KO_FAILED` |
| `interrupted` | "avbröts när pumpen dog" | fall, kod `KO_INTERRUPTED`. **Körs aldrig om automatiskt** |
| `rejected` | operatörens beslut | fall, kod `KO_REJECTED` |

### `dodar_pumpen` — varningen kommer före, inte efter

**MÄTT M-13:** två operationer stoppar simuleringen och därmed pumpen:
`createBehaviour(VC_SCRIPT, ...)` och `app.save(uri)`. Listan är inte härledd
ur en princip — den **växer av mätning** och kan växa igen.

Bryggan svarar därför på godkännandet direkt med `dodar_pumpen` och en
förklaring, och tjänstens utförare **slutar vänta** i stället för att gå i
timeout (KOD@HEAD, `utforare.godkann`). Operatören ser:

> Den här operationen stoppar simuleringen. Bryggan svarar inte förrän den
> startats om. Utfallet kan inte bekräftas.

Turen kan inte bli guld på en sådan post — utfallet är okänt, och okänt är
inte godkänt (I3).

### Automatiskt godkännande

Finns **endast** för bänkkörningar (`80_bank.md`) och stämplas i loggen med
`auto_approve: true`. En körning med den stämpeln får aldrig rapporteras som
ett operatörsverifierat resultat. Skälet är mätt i källan: alla riggar där
sätter `AUTO_APPROVE=true` och mekanismen slutade betyda något.

---

## 4. Körningen och domen

| Steg | Anrop | Not |
|---|---|---|
| 1 | `eyes_start` med provplanen | planen måste namnge minst ett spårat objekt, annars `E_ARGS` (KOD@HEAD) |
| 2 | simuleringen körs | pumpen provtar; **20,0 Hz mot väggklockan**, kvot simtid/väggtid **1,000** över 155 s (M-08) |
| 3 | `eyes_status` under tiden | ger `{aktiv, prov, t0}`. Detta är operatörens framstegssignal, avsnitt 7 |
| 4 | `eyes_stop` | serien följer med i svaret om den ryms under halva kroppstaket, annars bara sökvägen (KOD@HEAD) |
| 5 | `oga_analys.doma()` | ren funktion, körs **utanför** VC |
| 6 | domstexten | grammatiken i `41_ogat_kontrakt.md`, `EYES v1` |
| 7 | `guldgrind.doma()` | parsar ögats egen text, räknar aldrig om ett mått |

**Modellen är inte med i steg 5–7.** Den får domen efteråt, som text, enligt
`25_kontextbudget.md`.

Faller domen får modellen en **åtgärdbar** formulering, ur ögats egna rader:
`DWELL ST010 0.31s req=0.40s SHORT`, inte "sekvensen fel". Det är hela poängen
med att grinden läser ögats utdata i stället för att sammanfatta den.

---

## 5. Degraderade lägen

Bakgrunden är mätt i **M-13** och i **M-03**, **M-07**, **M-08**, **M-12**.
Sammanfattat: VC:s Python är kooperativ, det finns ingen tråd och ingen timer
som tickar (M-04, M-07, M-12), och pumpen lever bara medan simuleringen går
(M-08). Därför är "bryggan svarar inte" ett **normalt** läge som måste ha ett
beteende, inte ett undantag.

| Läge | Upptäcks av | Vad tjänsten gör | Vad operatören ser |
|---|---|---|---|
| **Bryggan nere** | anslutningen vägras, eller `ECONNRESET` | alla verktyg av. **Modellen anropas inte alls** för en byggförfrågan | "bryggan svarar inte på 127.0.0.1:8901. Startade VC med tillägget?" |
| **Ingen förmågerapport** | `capability` svarar inte | som ovan. Okänt = saknat (`36_versioner.md`) | listan över vad som inte kan prövas |
| **`degraded`** | `ping` bär flaggan | `queue_approve` är spärrad med `E_BUSY`; `exec` är **vägen ut**. Tjänsten kör **en** läsande `ping`-exec för att återställa, och säger att den gjorde det | "bryggan är osäker efter en timeout. Kör en läsning för att återställa" |
| **Simuleringen stoppad** | `sim` svarar `kor: false` | bryggan startar om den själv (`aterstart_simulering`, KOD@HEAD). Tjänsten väntar högst `KO_TIMEOUT_S` | "simuleringen stannade; bryggan startade om den (nr N)" |
| **Pumpen dog mitt i en post** | posten står `running` när pumpen kommer tillbaka | posten blir `interrupted`. **Aldrig omkörning automatiskt** | posten, dess `desc`, och frågan om den ska köras igen |
| **VC omstartad** | ny tokenfil, ny förmågerapport, tom kö | arbetsordern på disk är enda kontinuiteten. Scenen **läses om** före nästa skrivning | "VC startades om. Läser om scenen innan jag fortsätter" |
| **Porten upptagen vid start** | bind misslyckas | bryggan loggar **före** bindningen (KOD@HEAD, rättat efter M-13) | "port 8901 upptagen. **Linux:** `wineserver` lever kvar, kör `~/bin/vc-stoppa.sh`. **Windows:** `netstat -ano | findstr :8901` och avsluta PID:et" (Windows-ledet **OPRÖVAT**, M-44) |

### Regeln som binder ihop dem

**En `interrupted` post körs aldrig om av tjänsten.** Den kan ha hunnit ha
verkan innan pumpen dog, och en andra körning skulle kunna ladda in en
komponent två gånger eller flytta något två steg. Beslutet är operatörens, och
frågan ställs med postens `desc`-rad.

### Regeln efter en omstart

Efter en VC-omstart är varje påstående om scenen från före omstarten **inaktuellt**.
*Mekanik:* arbetsordern bär ett **scenfingeravtryck** (antal komponenter plus
hash av de sorterade namnen). Stämmer det inte mot en färsk `list_components`
tvingas en omläsning innan något skrivande verktyg får köras.

Kostnaden är en tur och retur: **median 9,91 ms** (M-03). Att läsa om är
billigare än att ha fel.

---

## 6. När arbetet är större än en tur

En tur slutar när modellen svarar utan verktygsanrop, eller när ett tak i
`23_llm_granssnitt.md` slår. Ett bygge är ofta större än så.

### Arbetsordern

Tillståndet ligger **inte** i samtalshistoriken. Det ligger i tre saker som
finns oberoende av modellen: **arbetsordern**, **scenen** och **kön**.

`arbetsorder.json` skrivs efter **varje** tur och bär:

| Fält | Innehåll |
|---|---|
| `order_id`, `uppgift` | operatörens ursprungliga mening |
| `steg` | planens noder ur `22_planeringslagret.md` (`id`, `action`, `tool`), med tillstånd per nod: `ej_pabörjad` \| `kord` \| `fallen` \| `avbruten` |
| `scenfingeravtryck` | antal komponenter + hash av sorterade namn |
| `ko` | `qid` och tillstånd för varje post turen skapade |
| `sista_dom` | ögats domsrad, ordagrant, eller `null` |
| `huvudbok` | en rad per verktygsanrop: `beskriv_anrop()`, utfall, kod |
| `stoppkod` | varför turen slutade |

**En tur som inte kunde skriva arbetsordern är en fallen tur.** Utan den finns
ingen väg tillbaka in i arbetet, och nästa tur skulle börja gissa.

### Hur nästa tur börjar

1. Läs arbetsordern.
2. Läs om läget (steg 1–2 i avsnitt 1).
3. Jämför scenfingeravtrycket. Avviker det: läs om scenen och notera avvikelsen
   i klartext för operatören — någon annan, eller operatören själv, har rört
   scenen.
4. Fortsätt på första steget som inte är klart.

Historiken från förra turen bärs **inte** vidare hel. Vad som bärs vidare står
i `25_kontextbudget.md`.

---

## 7. Vad operatören ser under tiden

**Tystnad i två minuter är ett gränssnittsfel.** Det är ett krav, och därför
har det ett tal.

| Krav | Värde | Härkomst |
|---|---|---|
| `TYSTNADSTAK` | **5 s** mellan händelser i operatörens flöde | *PRELIMINÄR, sätts av M-28.* Valt långt under operatörens gräns på två minuter, och långt över bryggans värsta tur och retur på **13,45 ms** (M-03) — så att ett överskridande alltid pekar på modellen eller på en körning, aldrig på bryggan |
| Vid överskridande | en hjärtslagshändelse med vad som pågår och hur länge | — |

Att talet ligger så långt från bryggans mätta tid är avsikten: gränsen ska
kunna peka ut sin egen orsak.

### Händelserna, sluten lista

| Händelse | Bär |
|---|---|
| `PLAN` | planens steg (`22_planeringslagret.md`) |
| `VERKTYG_START` | verktygsnamn + `beskriv_anrop()` |
| `VERKTYG_KLART` | verktygsnamn, ms |
| `VERKTYG_FEL` | verktygsnamn, **felnyckeln** |
| `KO_VANTAR` | `qid`, `desc`, och varningen om `dodar_pumpen` |
| `KO_GODKAND` / `KO_AVVISAD` | `qid` |
| `SIM_START` / `SIM_STOPP` | simuleringens läge |
| `OGAT_PROVTAR` | **provräkningen** ur `eyes_status` — den syns stiga |
| `DOM` | ögats domsrad, ordagrant |
| `GULD` | `guldgrind`-beslutets text |
| `SVAR` | det levererade svaret |
| `OMSKRIVNING` | att honesty-rewrite eller verify-contract slog till, och varför |
| `DEGRADERAD` | läget ur avsnitt 5 |
| `AVBRUTEN` | avsnitt 8 |
| `HJARTSLAG` | vad som pågår, och sedan hur länge |

Varje händelse bär tidsstämpel, `order_id` och stegnummer.

### Två regler om vad operatören ser

1. **Godkännanderaden är verktygets egen.** `beskriv_anrop()` är byggd för
   det (KOD@HEAD: "Operatoren godkanner pa den har texten"). Ingen
   omformulering, ingen sammanfattning — operatören godkänner exakt det som
   körs.
2. **En omskrivning döljs inte.** Slog honesty-rewrite eller verify-contract
   till ska operatören se att det skedde. En grind som arbetar i tysthet kan
   sluta arbeta utan att någon märker det.

---

## 8. Avbrott

Operatören avbryter mitt i ett bygge. Tre saker måste ha ett bestämt öde:
**kön**, **scenen**, **ögat**.

### Kön

| Posttillstånd vid avbrott | Vad som händer |
|---|---|
| `pending` | **avvisas** med `queue_reject`. Ingen post lämnas kvar |
| `approved`, ej körd | avvisas om den fortfarande går att avvisa; annars körs den och rapporteras |
| `running` | **kan inte avbrytas.** Se nedan |

**MÄTT:** `cancel` svarar `{"cancelled": false, "why": "exec kors synkront pa
VC:s trad och kan inte avbrytas"}` (KOD@HEAD, `pump._op_cancel`). Det är en
följd av att VC:s Python är kooperativ (M-07), inte en lucka i bryggan.

Avbrottet får alltså verkan **vid nästa post**, inte mitt i den som kör. Det
ska stå i klartext för operatören, inte döljas bakom en snurrande symbol.

### Scenen

Scenen rullas **inte** tillbaka automatiskt. Två skäl, båda mätta:

1. Det finns ingen transaktion i VC.
2. `app.save(uri)` **dödar pumpen** (M-13). Att spara ett tillstånd att
   återgå till är alltså inte gratis och inte tyst.

I stället skrivs en **avbrottsrapport**: vilka skrivande poster som blev `done`,
vilka som blev `interrupted`, vilka som avvisades. Operatören beslutar.
Återställning är en egen, uttalad begäran — aldrig något som sker av sig självt.

### Ögat

Provtar ögat ⇒ `eyes_stop` anropas alltid, även vid avbrott. Serien skrivs
inkrementellt var hundrade rad (KOD@HEAD, `SKRIV_VAR_N_RAD = 100`), så en
avbruten körning går ändå att läsa.

Domen för en avbruten körning är **aldrig `PASS`**. Den är `INCONCLUSIVE` med
skälet `avbruten av operatoren`, och `INCONCLUSIVE` räknas som inte godkänt
(regel 4 i `41_ogat_kontrakt.md`).

### Grinden mot avbrottet

Ett avbrottsprov i L3, med en trasig fixtur som **ska** falla:

```
FAS n ACCEPTANS — avbrott
  förutsättning:  en arbetsorder med minst tre skrivande poster, ögat aktivt
  steg:           1. starta bygget   2. avbryt när post 2 är running
  mätning:        köns tillstånd, ögats dom, arbetsorderns innehåll
  godkänt när:    noll poster i pending
                  posten som körde har state done eller interrupted, aldrig pending
                  ögats dom är INCONCLUSIVE, aldrig PASS
                  arbetsordern namnger varje post och dess tillstånd
  trasigt fall:   ett avbrott som lämnar en pending post ska fälla provet
  plattform:      Linux ☐   Windows ☐
```

---

## 9. Antaganden och öppna frågor

| # | Sak | Stämpel | Varför |
|---|---|---|---|
| 1 | `TYSTNADSTAK = 5 s` | **PRELIMINÄR** | ingen mätning av modellatens finns. M-28 |
| 2 | Att ett `ping` räcker för att lämna `degraded` | **ANTAGET** | koden säger att en lyckad körning räcker (KOD@HEAD), men att `ping` räknas som körning är inte mätt |
| 3 | Att arbetsordern på disk räcker som kontinuitet över en VC-omstart | **ANTAGET** | inte prövat. Provet hör till samma fas som avbrottsprovet |
| 4 | Att listan över pumpdödande operationer är två lång | **MÄTT men öppen** | M-13 säger uttryckligen att listan växer av mätning |
| 5 | Att avbrott alltid hinner före nästa post | **ANTAGET** | vid `PAUS_AKTIV = 0.005` betas kön av snabbt; en post kan hinna starta. Kostnaden är en extra körd post, aldrig en förlorad |

**Öppna frågor till operatören**

1. **Vad ska hända med en `interrupted` skrivande post?** Förslaget här är att
   den aldrig körs om automatiskt och att frågan ställs. Ett alternativ vore att
   varje skrivande verktyg deklarerar om det är idempotent, och att idempotenta
   poster körs om. Det senare är mer arbete och mer att ha fel om. Inget är
   bestämt.
2. **Ska ett avbrott försöka återställa scenen?** Här föreslås nej, av mätta
   skäl. Skulle operatören vilja ha återställning behöver vi en billig
   ögonblicksbild, och den enda vägen vi känner till — `app.save` — dödar
   pumpen.
3. **Hur mycket ska operatören se som standard?** Listan i avsnitt 7 är
   fullständig. Frågan är om `VERKTYG_START` och `VERKTYG_KLART` ska vara på
   som standard eller bara i ett utförligt läge.


---

## Två tillägg till den slutna händelselistan (M-64)

Listan kunde inte säga två saker som fas 17 behöver.

**`FALLET` — att körningen SJÄLV föll.** `VERKTYG_FEL` är ett anrop som föll.
`AVBRUTEN` är operatörens beslut. Kopplaren som ger upp efter tre raka fel
(`M-39`) hade **ingen händelse alls** — den viktigaste spärren i hela PLC-benet
var osynlig i operatörens flöde. Händelsen bär skälet **ordagrant**.

**`GRIND` — vad grind 1–4 sa.** `DOM` är ögat och `GULD` är guldgrinden.
Förgrindarna hade ingen händelse, trots att `27_operatorsflodet.md` §5 steg 10
lovar operatören *"fyra grindar med utfall"*. Händelsen bär grindens **egna
ord**, aldrig en omskrivning (I1).

Tilläggen ligger i `TILLAGDA_SORTER` och provas för sig, så att de **syns** i
stället för att glida in i en sluten lista.

## Läget härleds, det sätts aldrig

Ur `M-64`, och det är fasens hårdaste regel: `FALLET` är **absorberande**.
`VÄNTAR PÅ OPERATÖREN` och `TYST` är egna lägen, inte arbete.

Fyndet som motiverar det: **ett hjärtslag som räknas som framsteg gör en död
körning odödlig.** Mätt över 600 pulser där inget annat hände sa läget
`ARBETAR` i **600 av 600**. Med hjärtslaget skilt från framsteg: 5 av 600 — och
de fem är sekunderna inom tystnadstaket, där `ARBETAR` är rätt svar.
