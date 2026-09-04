# M-52 — reparationsslingan i två lägen, och taket som slutade löna sig vid fyra

**Datum:** 2026-09-04
**Körs av:** `python3 bank/reparationsbank.py` · `tests/enhet/test_reparation.py`
**Bygger:** `svc/vc_assist_svc/plc/reparation.py`, `bank/reparationsbank.py`

> **Modelledet är ATTRAPPERAT. Ingen språkmodell kördes.**
> Det som mäts är slingans mekanik, med en deterministisk attrappmodell som gör
> bankens egna, människoskrivna fel. Varje tal nedan gäller den mekaniken. Inget
> tal nedan är en förutsägelse om en riktig modell, och ingenting här får
> läsas som att en modell provats.

## Talen

Fyra bankuppgifter har spårfacit (H-04, L-05, S-05, T-07). De bär tillsammans
**18 motbevis**, alla skrivna av en människa före försöket. Varje körning ger
slingan en repertoar av försök ur just den uppgiftens material, och samma
repertoar körs i båda lägena. **82 slingor per läge, 164 totalt.**

| Läge | Löste | Låst | Nådde taket | Varv till löst |
|---|---|---|---|---|
| **rent** (skelett + senaste grinddomen) | **43 av 82** | 31 av 82 | 8 av 82 | 13 på varv 3, 30 på varv 4 |
| **med historik** (även tidigare försök) | **57 av 82** | 5 av 82 | 20 av 82 | 13 på varv 3, 44 på varv 4 |

**25 av 82 körningar är olösliga**, och det är hela L-05 (se nedan). Räknat
bara på det som går att lösa:

| Läge | Löste av de lösbara |
|---|---|
| rent | **43 av 57** |
| med historik | **57 av 57** |

### Fel per klass

Klasserna är `docs/spec/82_felklasser.md`. Talet är antalet **varv** som fälldes
på klassen; ett varv kan bära flera klasser.

| Läge | F3 | F4 | F5 | F7 | F8 | F15 | dömda varv |
|---|---|---|---|---|---|---|---|
| rent | 7 | 82 | 103 | 74 | 39 | 18 | 315 |
| med historik | 7 | 82 | 103 | 86 | 39 | 18 | 315 |

Enda skillnaden är F7, och den är L-05:s: historikläget kommer längre in i en
uppgift som ändå inte går att lösa, och hinner därför fällas fler gånger på
samma sak.

### Per uppgift

| Uppgift | rent | med historik |
|---|---|---|
| T-07 | 10 av 16 | 16 av 16 |
| S-05 | 19 av 25 | 25 av 25 |
| H-04 | 14 av 16 | 16 av 16 |
| L-05 | 0 av 25 | 0 av 25 |

## Är skillnaden större än bruset?

**Det finns inget brus.** Attrappen och grindarna är rena funktioner: två
körningar av samma manus ger samma protokoll, tecken för tecken. Det provas
mekaniskt (`test_en_korning_ger_samma_tal_tva_ganger`). Skillnaden 43 mot 57 av
57 är alltså en **exakt räkning**, inte en skattning med en spridning omkring
sig.

Det är också mätningens största begränsning, och den ska stå här och inte i en
fotnot: en riktig modell samplar, och skulle ha en spridning som ingen har mätt.
Talen ovan säger vad som händer i det **deterministiska gränsfallet**, och det
gränsfallet är just det som gör rentläget svagt. Se nästa avsnitt.

## Varför rentläget missar exakt de 14 det missar

Mekanismen är inte en åsikt om modeller, den är en egenskap hos rena funktioner.

En grind är en ren funktion av kroppen. Ett minneslöst läge visar modellen
skelettet och **en** grinddom. Kommer samma grinddom tillbaka två varv i rad är
modellens indata identisk, och en deterministisk modell svarar då likadant. Då
är slingan låst, för alltid, oavsett hur högt taket står.

Det inträffar när två olika fel bär **samma felklassignatur**. Det är mätt på
bankens material, inte antaget:

| Uppgift | Distinkta felklassignaturer bland motbevisen | Repertoarer med kollision |
|---|---|---|
| T-07 | 2 (`F5`; `F5+F8`) | 6 av 16 |
| S-05 | 3 (`F5`; `F5+F15`; `F5+F8+F15`) | 6 av 25 |
| H-04 | 3 (`F5`; `F5+F8`; `F3`) | 2 av 16 |
| L-05 | 2 (`F7`; `F5+F8`) | 12 av 25 |
| **summa** | **som mest 3 per uppgift** | **26 av 82** |

Bland de 57 lösbara körningarna bär **14** en kollision. Rentläget löser
43 av 57 och missar 14. **Det är samma 14.** Historikläget ser att det redan
provat den kroppen och tar nästa, och löser därför alla 57.

Attrappen är dessutom en **maximalt kompetent** minneslös reparatör: den har en
orakeltabell från felklassignatur till exakt rätt nästa försök, byggd genom att
köra repertoaren i förväg. En riktig modell har ingen sådan tabell. Talet
43 av 57 är alltså en **övre gräns** för vad ett rent läge kan klara på det här
materialet, inte ett typiskt utfall.

## Vad historikläget kostar

Samma manus, samma grindar, samma tak:

| Läge | Tecken ut till modellen, i snitt per slinga |
|---|---|
| rent | 17 792 |
| med historik | 34 530 |

Historikläget skickar **1,94 gånger** så mycket text för att lösa 14 fler av 57.
Det är den kända nackdelen `61_st_generering.md` talar om, nu med ett tal på
sig. Kontextbudgeten står i `docs/spec/25_kontextbudget.md`; den här mätningen
har inte prövat vad som kapas när historiken inte får plats.

## Taket: fyra varv, och varför det inte är ett tycke

Samma 82 repertoarer, samma två lägen, bara taket ändrat:

| Tak | rent löste | historik löste |
|---|---|---|
| 2 | 0 av 82 | 0 av 82 |
| 3 | 13 av 82 | 13 av 82 |
| **4** | **43 av 82** | **57 av 82** |
| 5 | 43 av 82 | 57 av 82 |
| 6 | 43 av 82 | 57 av 82 |
| 8 | 43 av 82 | 57 av 82 |

**Att höja taket från 4 till 8 löste noll ytterligare körningar, i båda lägena.**
De körningar som stod öppna efter varv 4 gick inte vidare — de skickade tillbaka
en kropp de redan skickat, och blev `LAST` i stället för `TAK`. Varv 5 till 8
producerade alltså inte en enda ny dom.

Det stämmer med räkningen ovan: en uppgift i banken bär som mest **tre**
distinkta felklassignaturer bland sina motbevis, plus deklarationsklassen — fyra
olika domar totalt. Ett femte varv har ingen femte dom att svara på.

    MAX_VARV = 4  # Satt av M-52.

Vad talet INTE säger: att fyra varv räcker för en riktig modell på ett rikare
material. Det säger att på den här banken, med den här grindkedjan, slutade
reparationerna löna sig efter varv fyra, och att varje varv därefter upprepade
sig själv.

`ABSOLUT_TAK = 20` är inte mätt som ett riktigt antal varv. Den finns för att
ett tak som får vara godtyckligt stort är samma sak som inget tak, och den är
satt till fem gånger `MAX_VARV` så att en mätning som vill svepa över taket
ryms.

## Två fynd som inte var frågan, men som mätningen fällde

### L-05:s egen referenslösning fälls av grind 2

Alla 25 L-05-körningar är olösliga, och skälet är inte slingan:

```
EJ GODKAND
  rad 107: [DUBBELSKRIVNING/F7] utgången ST260_LFT_DOWN skrivs på rad 65 och
  rad 107, och båda kan köras i samma scan; lägg ihop villkoren till en enda
  skrivning
```

Rad 65 ligger i `CASE steg OF 0:` och rad 107 i en fristående `IF ST260_LFT_UP`.
Båda skriver `FALSE`, så **spårfacit godkänner referensen** — domaren kör koden
och ser rätt spår. Grind 2 fäller den ändå, på en dödsfällsregel som inte frågar
efter värdet.

Det betyder att bankens referenslösning för L-05 **inte är en giltig kandidat i
grindkedjan**. Ingen slinga kan lösa uppgiften, därför att facit självt inte
passerar. Det syntes bara därför att slingan har ett tak; en obegränsad slinga
hade snurrat i stället för att visa det.

`bank/domare.py:dom_referens` kör i dag bara spårfacit. Två grindar är oense om
samma kod och ingenting fångade det.

### Första grinden som fäller byter klass på ett motbevis

H-04:s motbevis `gripkraften_provas_inte` fälls av **spårfacit på F5** när
domaren körs ensam, men av **grind 3 på F3** när hela kedjan körs: koden rör
aldrig `ST320_GRP_FRC`, och en orörd signal i kartan är grind 3:s fall.

Det är sorteringsregel 1 i `82_felklasser.md` som fungerar precis som den ska
(första grinden som fäller bestämmer klassen). Men det betyder att ett motbevis
klassas olika beroende på vilken kedja som körs, och bänkens "fel per klass" är
alltså inte jämförbar mellan `bank/domare.py` ensam och hela grindkedjan.

## Vad som INTE kördes

| Grind | Varför inte |
|---|---|
| grind 1, kompilering | `kompilatorn ar inte uppsatt; grind 1 kunde inte kora` |
| grind 4, anropsvalidering | `API-indexet saknas; grinden kunde inte kora` |
| grind 5, ögat | kräver en körning i VC |

Skälen ovan är grindarnas **egna ord**, och de står i varje protokoll
(`Reparationsprotokoll.ej_korda`). Ingen av dem räknas som ett godkännande
(I3). Slingans utfall `LOST` betyder därför **kandidat**, aldrig guld:
`Reparationsprotokoll.niva` returnerar `"kandidat"` och kan inte returnera något
annat. Endast en körning i VC befordrar (`50_grindar.md`).

De grindar som faktiskt dömde var **grind 2, grind 3, skelettets ramgrind och
bankens spårfacit**.

## Läckagekontrollen

En slinga som konvergerar därför att facit ligger i prompten mäter avskrift.
Kontrollen körs över alla fyra uppgifter före varje bänkkörning och räknar rader
ur referensens **kropp**, utan kommentarer, längre än 25 tecken, som står i den
text modellen får (uppgiftstext **plus** skelett).

**Mätt: 0 rader av 4 uppgifter.** Kontrollen har en trasig fixtur: en planterad
rad hittas (`test_lackagekontrollen_hittar_en_planterad_lacka`).

**Men en kanal är öppen, och den ska stå här.** Skelettets
`extra_deklarationer` — arbetsvariablerna `steg`, `tmrIndex`, `trigReset` och de
andra — är i banken **hämtade ur referenslösningens VAR-block**. Enligt
`61_st_generering.md` hör arbetsvariabler till ramen och inte till modellen, så
det är formellt rätt. Men banken har ingen annan källa till dem än facit, och en
modell som får veta att stationen behöver precis en `TON` och precis en `R_TRIG`
har fått veta något om lösningen. Läckkontrollen ovan täcker inte det.

## Vad som mekaniserades, och vad som fortfarande bara är bett

Tre doktriner ur `50_grindar.md` och `61_st_generering.md` är nu grindar med
trasiga fixturer i `tests/enhet/test_reparation.py` (41 prov):

| Doktrin | Mekanism | Trasig fixtur |
|---|---|---|
| grindens egna ord, ordagrant | `kontrollera_ordagrant` jämför tecken för tecken | en inramning som skriver om domen; **och** en som bara normaliserar radbrytningarna |
| slingan har ett tak | konstruktorn avvisar `None`, `0`, `-1`, icke-heltal och tal över `ABSOLUT_TAK` | alla fem former |
| ett varv utan förändring är låst, inte tak | kroppen jämförs mot **alla** tidigare varv | samma kropp två varv i rad; och cykeln A, B, A |

Jämförelsen mot alla tidigare varv, inte bara föregående, är inte kosmetik: en
cykel A–B–A är lika låst som en upprepning, och en jämförelse mot bara
föregående varv hade sluppit igenom den.

## Spec-förslag (`docs/spec/` ägs av huvudtråden — inget är ändrat)

1. **`61_st_generering.md`, "Vad som inte är avgjort":** den första punkten kan
   stängas. Förslag till formulering: *"Slingan visar modellen sina tidigare
   försök. Mätt i M-52: minneslöst läge löste 43 av 57 lösbara körningar,
   historikläget 57 av 57, och de 14 som skilde dem åt var exakt de vars två fel
   bar samma felklassignatur — en minneslös reparatör kan inte svara olika på
   samma dom. Priset är 1,94 gånger mer text till modellen."*
2. **`82_felklasser.md`:** spårfacits tre påståendeformer bör få en egen rad i
   tabellen. F15 står redan där ("spårfacit, flankräkning"); punktkrav och
   invariant gör det inte. Den här mätningen läser punktkrav som **F5** och
   invariant som **F8**, och det är vår läsning, inte specens ord.
3. **`80_bank.md` eller `61_st_generering.md`:** en uppgifts referenslösning bör
   krävas passera grind 2 och 3, inte bara spårfacit. L-05 visar varför.
4. **`61_st_generering.md`, skelettavsnittet:** arbetsvariablernas ursprung bör
   namnges. I dag kommer de ur referenslösningen, och det är en kanal från facit
   till prompten som ingen kontroll täcker.
5. Andra öppna punkten (hur en uppgift med flera giltiga lösningar poängsätts)
   är **inte** mätt här och står kvar.

## Så här körs mätningen om

```
python3 bank/reparationsbank.py               # standardtaket
python3 bank/reparationsbank.py --tak 8       # svepet över taket
python3 bank/reparationsbank.py --uppgift T-07
python3 -m pytest tests/enhet/test_reparation.py -q
```
