# M-103 — återhämtningen som användaren ser den

**Datum:** 2026-09-05
**Körs av:** `python3 -m pytest tests/enhet/test_aterhamtning*.py -q` (88 gröna)
och `python3 tests/protocol/kor_fas23_anvandarlagret.py`
**Bygger:** `svc/vc_assist_svc/aterhamtning/` (2 396 rader)
**Fas:** 23 i `docs/spec/70_faser.md`
**beskriver:** `docs/spec/26_appen.md`, `docs/spec/27_operatorsflodet.md`,
`docs/spec/28_lagen_och_aterhamtning.md`,
`tests/protocol/fas23_anvandarlagret.md`
**Föregångare:** [M-64](M-64_vad_anvandaren_ser_medan_det_arbetar.md) och
[M-93](M-93_speglingen_som_inte_aldras.md) — fas 17 stängde ytan som visar vad
som händer **medan** en körning går.

**Vad användaren ser nu:**

```
PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil>
PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil> --loggar ~/
```

---

## 1. Glappet: sju lägen, noll härledningar

`28_lagen_och_aterhamtning.md` bar 355 rader om lägena och vägen tillbaka.
`26_appen.md` 329 om ytan. `27_operatorsflodet.md` 359 om vägen från en tom VC
till en verifierad cell. **Ingen av de tre hade en fas** — samma form som fas 16
hade innan den fick en, och som fas 19 hade i förrgår.

Mätt i `svc/` innan koden fanns:

| | antal |
|---|---:|
| lägen `28` specar | **7** |
| som någon kod i `svc/` kunde härleda | **0** |
| ställen som skilde `nere` från `frånkopplad` | **0** |
| moduler som räknade en avläsnings **ålder** mot läsarens klocka | **0** |
| ställen som läste `degraded` ur pumpens `ping`-svar | **0** |

`klient.py` kastar `BryggFel` och `OSError` uppåt. Den som fångar dem hade inget
ordförråd att svara med, och därför inget att visa någon.

---

## 2. Fyndet: den tredje nollade klockan

Samma fel har nu mätts **tre** gånger i det här systemet, med tre olika
mekanismer och exakt samma form: ett tal som skulle åldras gjorde det inte.

| # | Mekanism | Utfall | Mätning |
|---|---|---|---|
| 1 | ett hjärtslag räknades som framsteg | ARBETAR i **600 av 600** | M-64 |
| 2 | en läsare frös klockan vid bildens skrivtid | ARBETAR i **60 av 60** | M-93 |
| 3 | **en avläsning återanvändes efter att den blivit gammal** | LEVANDE i **60 av 60** | **M-103** |

Uppställningen är M-93:s, med samma nämnare så att de går att jämföra: en sond
frågade en gång, fick ett ja, och dog. Sextio avläsningar senare:

| Härledning | LEVANDE | OBESTÄMT |
|---|---:|---:|
| med avläsningens egen tid som "nu" | **60 av 60** | 0 |
| med **läsarens** klocka | **3 av 60** | **57 av 60** |

De tre jaen är avläsning 1, 2 och 3 — alltså de som ligger under `T_nere` = 3 s.
De är korrekta. Resten är gissningar som ser ut som svar.

**Regel L-0** i specen kommer ur det: åldern räknas mot den klocka som **läser**,
aldrig mot den som skrev.

---

## 3. Regel L-1:s premiss, mätt mot en riktig socket

`28_lagen_och_aterhamtning.md` §1.2 säger att en TCP-anslutning inte är ett
livstecken: bryggan accepterar **inuti `tick()`**, så en död pump lämnar ändå
kärnans lyssningskö att fullborda handskakningen. Påståendet stod som
**HÄRLEDD ur KOD@HEAD**. Det är nu mätt på den här värden.

En socket binder, lyssnar med backlog 128, och accepterar **aldrig**:

| | tal |
|---|---:|
| `connect()` lyckades | **20 av 20** |
| median för `connect()` | **0,12 ms** |
| `ping` fick svar genom samma socket | **0 av 20** |

Och det är precis skillnaden de två härledningarna gör:

| Härledning | säger ANSLUTEN |
|---|---:|
| en lyckad `connect()` räknas som liv | **20 av 20** |
| bara ett `ping`-svar räknas som liv | **0 av 20** |

**Vad det INTE säger:** mätningen gäller den här värdens kärna, i CPython, på
loopback. Att Wines winsock beter sig likadant är **oprövat** och står kvar som
**M-25**. Wine-halvan av frågan är alltså obetald; Linux-halvan är betald.

---

## 4. De fyra dödsfallen, och att de inte ser likadana ut

Operatörens fråga, ordagrant: *"vad händer när något dör mitt i? VC stängs under
en körning. Bryggan tappar sin socket. OpenPLC svarar inte. Modellen tar slut
mitt i en reparation."*

| Dödsfall | Läge | Orsak | Vägar | Något försöker? | Ytan |
|---|---|---|---:|---|---:|
| VC stängs under en körning | bryggan NERE | `vc_avslutades` | 1 | **nej** | 2 490 tecken |
| bryggan tappar sin socket | bryggan NERE | `socket_bruten` | 1 | **ja**, och det kan lyckas | 2 525 |
| OpenPLC svarar inte | OpenPLC NERE | `kopplaren_gav_upp` | 2 | **nej**, efter tredje raka felet | 2 298 |
| modellen tar slut mitt i en reparation | modellen NERE | `modellen_tog_slut` | 1 | **nej** | 1 872 |

Alla fyra passerar grinden. **Fyra olika orsaksblock, tre olika första rader**
(socketfallet delar `bryggan NERE` med VC-fallet, och skiljs på orsaken och på
att något faktiskt försöker).

### Kommer systemet tillbaka?

| Dödsfall | Automatisk väg | Kom tillbaka | Syns i ytan |
|---|---|---|---|
| VC stängs | — | nej | — |
| sockeln tappas | `anslut_igen` | **ja** | **ja** — *"lyckades"* och kvittots egna ord |
| OpenPLC tystnar | — | nej | — |
| modellen tar slut | — | nej | — |

**1 av 4.** Och det är inte en brist i bygget — det är vad som är sant. Tre av
fyra kräver en människa, och det farliga vore att låta dem se ut som något
annat.

---

## 5. Talet som gör regeln nödvändig

Av **18 orsaker** i tabellen:

| | antal |
|---|---:|
| har ett automatiskt försök alls | **3** |
| vars automatiska försök är **mätt** att kunna lyckas | **2** |
| kräver operatören | **15** |
| som lovar att **självstarten** kan lyckas | **0** |

Femton av arton gånger är det ärliga svaret *"Ingenting försöker igen"*. En yta
som ändå skriver *"vi försöker igen"* har alltså fel i 83 % av fallen — och den
är farligast just då, för den ber någon vänta på något som inte händer.

Nollan på sista raden är en **strukturell spärr**, inte en tillfällighet:
självstarten är den enda väg systemet går utan att fråga, och skulle någon orsak
stå som `kan lyckas` för den kunde ett okänt `keepalive` glida till ett löfte.
`test_ingen_orsak_lovar_att_sjalvstarten_kan_lyckas` håller regeln.

### Kanskapen har tre värden, och orden får inte ligga inuti varandra

Första formuleringen var `okänt om den kan lyckas`, och den bär `kan lyckas`
inuti sig. Grinden letar efter orden i en främmande renderares text — den hade
alltså svarat *ja* om en väg som stod som **okänd**, i precis det steg som finns
för att förhindra att ett okänt blir ett löfte. Felet fanns i tio minuter och
fångades av ett prov som råkade skriva `assert KAN_JA not in text`. Ordet är nu
`okänt om den hjälper`, och `test_ingen_kanskap_ar_delstrang_av_en_annan` håller
regeln.

Det är samma felklass som `en-parameter-som-bar-tva-storheter`: en delsträng är
en andra storhet som ingen deklarerade.

---

## 6. Grinden, och den tredje sortens lögn

Fas 17 fällde två: en **renderare** som skriver något annat än protokollet
säger, och en **läsare** som fryser klockan. Här finns en tredje, och den hör
återhämtningen till: en **härledning**.

Ett läge är en slutsats om en tystnad. Den som drar slutsatsen kan dra fel, och
tre fel ger alla samma svar — *ansluten* om något som inte svarar:

* räkna en lyckad `connect()` som liv,
* återanvända en avläsning som blivit gammal,
* låta en klocka som gått bakåt betyda att ingen tid gått.

Grinden räknar därför om varje delsystems läge **själv**, med `bild.lage_for`,
ur de råa avläsningarna och läsarens `nu`. Fjorton regler, `Å1`–`Å14`, var och en
med minst en trasig fixtur, och provet som håller det läser sin egen källa.

| | antal |
|---|---:|
| regler | **14** |
| trasiga fixturer i tabellen | **15** |
| regler utan trasig fixtur | **0** |
| prov | **88** |
| prov som kräver VC | **0** |

---

## 7. Hur stor del av ytan handlar om vad systemet inte vet

M-60:s form, mätt över de fyra dödsfallen:

| Dödsfall | tecken | varav ovisshet | andel |
|---|---:|---:|---:|
| VC stängs | 2 490 | 804 | **32,3 %** |
| sockeln tappas | 2 525 | 804 | **31,8 %** |
| OpenPLC tystnar | 2 298 | 804 | **35,0 %** |
| modellen tar slut | 1 872 | 804 | **42,9 %** |

De 804 tecknen är **permanenta**: raden `modal oppen` finns inte i koden, Wines
lyssningskö är oprövad, ingen väg är prövad på Windows, tidsgränserna är
preliminära, och ingen väg tillbaka har körts mot en VC som verkligen gick ned.
De står i **varje** visning, också en där allt svarar — de blir inte mindre
sanna av att det går bra just nu.

---

## 8. Stegen som hittar orsaken

`28_lagen_och_aterhamtning.md` §5.3 har sju frågor. De är nu körbara, och
markörerna de letar efter läses ur tilläggets egen källa —
`test_varje_markor_skrivs_av_tillagget` faller om en lograd byter namn.

Mot de fem tysta fällorna i `27_operatorsflodet.md` §3:

| Fälla | Orsak stegen ger | Rätt? | ja / nej / vet inte |
|---|---|---|---|
| fel `Python N`-nivå | `kroken_fyrade_inte` | **ja** | 2 / 5 / 0 |
| syntaxfel i modulen | `skriptet_kompilerar_inte` | **ja** | 4 / 3 / 0 |
| `OnRun` utan `vcScript` | `operatoren_stoppade` | **ja** | 6 / 1 / 0 |
| porten upptagen | `port_upptagen` | **ja** | 5 / 2 / 0 |
| loggen gick inte att läsa | **`okänd`** | **ja** | 0 / 0 / **7** |

Den sista raden är den viktiga. En obesvarad fråga **stoppar** stegen. Den
trasiga fixturen `_tom_strang_som_svar` — `except OSError: text = ""`, buggen i
sin vanligaste form — svarar i stället *"Tillägget startade aldrig"* med full
säkerhet, och skickar operatören att installera om ett tillägg som kan ha varit
helt i sin ordning.

---

## 9. Vad som ändrades i specen

| Dokument | Vad som tillkom |
|---|---|
| `26_appen.md` | §1.1.1: **DOK är inte belägg för att något fungerar** — hela menyytan står nu som **ANTAGET**, rad för rad, och `M-21` beskrivs som ett reserverat nummer, alltså ett löfte om en mätning. §3.0: vad varje fält gör **och aldrig gör**. §3.2: fält 7 när något inte svarar. §6.1: hela ytan uttömmande, med kolumnen *finns i koden i dag*. Reglerna A-10 till A-13, grindarna A-G11 till A-G13 |
| `27_operatorsflodet.md` | §4.5: vägen A1–A8 från att programmet öppnas till att panelen lever, med vad som kan gå fel i varje steg och en härkomst per rad. §5.1: vad som kan gå fel i vart och ett av genomloppets fjorton steg. Reglerna F-10 och F-11, grinden F-G13 |
| `28_lagen_och_aterhamtning.md` | §1.0: två lägen till, `OBESTÄMT` och `BLOCKERAD`, markerade som tillägg. §1.4: ordningen mellan delsystem. §1.5: att en avläsning åldras, med de tre mätningarna. §3.8: de fyra dödsfallen, vad systemet gör och vad det **säger**. §3.9: försökets kanskap. Reglerna L-0 och L-11 till L-14, grindarna Å-G11 till Å-G16 |
| `70_faser.md` | fas 23 |

---

## LIMITS

* **Ingen sond går av sig själv.** Ytan läser avläsningar som någon annan har
  gjort. Vem som gör dem, och med vilket mellanrum, är **inte bestämt** — och en
  yta utan sond visar `OBESTÄMT` för allt efter `T_nere`. Det är rätt svar, men
  det är inte ett system som övervakar sig självt.
* **Ingen väg tillbaka är körd mot en VC som verkligen gick ned.** Alla fyra
  dödsfallen är framprovocerade mot attrapper. Att `menyval2` faktiskt återställer
  bryggan efter en `app.save()` är **oprövat**, och står som `okänt om den
  hjälper` i tabellen — inte som ett ja.
* **Läget `BLOCKERAD` kan inte fyras.** Raden `modal oppen` finns inte i
  `ext/vc_addon/`. Läget är byggt och provat mot en syntetisk lograd, och skulle
  ingen någonsin skriva raden är läget död kod som ser ut som en förmåga. Det
  står i varje visning.
* **`connect()`-mätningen gäller den här värdens kärna**, inte Wines winsock och
  inte VC:s process. M-25 står kvar.
* **`T_ping` = 3,0 s och `T_nere` = 3,0 s är PRELIMINÄRA**, härledda ur M-03:s
  tur och retur (median 9,91 ms) och aldrig mätta mot en **död** brygga.
  `T_modal` = 300 s har **ingen** mätning alls — talet är valt så att en ruta en
  människa läser hinner stängas, och det är en gissning med ett skäl, inte ett
  mått.
* **`MAX_AVLASNINGSRADER` = 8** är satt efter formen i M-64, inte efter en
  mätning av vad en människa orkar läsa.
* **De 15 av 18 orsakerna som kräver operatören** är räknade ur tabellen, inte
  ur verkligheten. Tabellen är skriven ur specen och koden; en orsak som saknas
  i den finns inte i räkningen. `M-27` — svepet över vilka fler anrop som dödar
  pumpen — kan göra listan längre.
* **Ingen operatör har läst ytan.** Att den är läsbar är en bedömning, inte en
  mätning. Samma öppna punkt som fas 17 lämnade, oförändrad.
* **Kopplarens tre raka fel** är M-39:s tal, återanvänt. Att OpenPLC verkligen
  är dött efter tre misslyckade varv är inte mätt — det är ett tak, inte en
  diagnos.
* **Windows är oprövat.** `netstat`-vägen i `FRIGOR_PORTEN` är skriven och aldrig
  körd (M-44, I17).
