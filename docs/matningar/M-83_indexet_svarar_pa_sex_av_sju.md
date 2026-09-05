# M-83 — indexet kunde ha svarat på sex av modellens sju frågor. Den sjunde kan ingen.

**Datum:** 2026-09-05
**Bygger på:** `M-82` (modellen skrev 691 rader scenkod, noll uppfunna namn)

## Frågan

`M-82` lämnade modellens egen osäkerhetslista. Vi har verktyg byggda för precis
sådana frågor — `lookup_api` och `search_api`. Modellen fick dem inte.

**Hur många av dess gissningar hade indexet kunnat besvara?**

## Svaret: sex av sju

| Modellens fråga | Indexets svar |
|---|---|
| returnerar `load` komponenten? tar den fler argument? | signatur `String uri`, typ `vcComponent`, *"If loading is successful, **returns the component**; otherwise returns None"* |
| heter det `findBehavioursByType`? | ja — signatur `Enumeration type`, typ `List of vcBehaviour` |
| returnerar `getProperty` `None` för okänd egenskap? | *"Returns a property matching a given name; **otherwise returns None**"* |
| argumentformen för `translateAbs`? | `Real x, Real y, Real z` |
| returtypen för `vcMatrix.new`? | `vcMatrix` |
| finns `VC_ONETOONEINTERFACE`? | ja |
| **`rotateAbsZ` — grader eller radianer?** | **inget svar** |

Fem av svaren är ordagranna citat ur VC:s egen dokumentation. Modellen gissade
rätt på alla sex — men den **visste inte** att den gjorde det, och det är
skillnaden.

## Den sjunde kan indexet inte svara på, och ingen annan heller

Nio `rotate`-metoder i API:t. **Ingen av dem nämner grader eller radianer.**

```
rotateAbsX   Rotates the matrix around X-axis in absolute coordinate system.
rotateAbsZ   Rotates the matrix around Z-axis in absolute coordinate system.
rotateRelV   Rotates the matrix around an axis defined by a given vector …
```

Indexet bär **existens och typer**. Aldrig enheter.

Och en enhetsförväxling är tyst: modellen skrev `rotateAbsZ(90.0)` och sa själv
*"är den i radianer blir tre komponenter felvridna"*. Grind 4 hade inte sett
det. Ögat hade — men bara om någon kört scenen.

Svaret finns ändå, empiriskt: `M-72` mätte `rotateAbsZ(70.0)` och fick
`q.W = 0,573576 = sin 35°`. **Grader.** Det talet kom ur en körning, inte ur ett
index.

## Grind 4 är sträng, och nu är det provat

`M-82`:s nolla är bara värd något om grinden hade fällt ett påhitt. Fyra trasiga
fixturer, alla fällda (`tests/enhet/test_api_index.py`):

| Fall | Utfall |
|---|---|
| påhittat namn på ett **listelement** ur `findBehavioursByType` | fälls — elementtypen `vcBehaviour` följer med |
| **riktigt** namn på **fel typ** (`connect` på `vcComponent`) | fälls — den svåraste sorten, namnet står ju i indexet |
| påhittad **konstant** (`VC_HITTEPA`) | fälls |
| den riktiga kedjan | godkänns, och kontrollerar minst fyra namn |

Den andra raden är den som gör grinden värd något. En grind som bara slår upp
namn hade sagt grönt.

## Följden

Modellen som skrev scenkoden lämnade tre saker ogjorda för att den inte vågade
gissa: signalkopplingar, `vcHelpers.Robot` och en container-behaviour för
pallen. **Fem av dess sex besvarade frågor gällde saker den ändå gissade rätt
på** — men de tre ogjorda hade sannolikt också gått att slå upp.

Att ge modellen `lookup_api` och `search_api` är alltså inte en bekvämlighet.
Det är skillnaden mellan en scen som byggs och en som lämnas halv med ärliga
kommentarer.

> **Prövat i M-84, och slutsatsen håller — men inte på det sätt som stod här.**
> Med uppslag skrev modellen **hälften** så mycket kod. Skillnaden syns inte i
> mängd utan i ordförråd: 13 distinkta API-namn utan uppslag mot 32 med, där två
> namn ensamma stod för 61 % av alla kontroller i körningen utan. Alla tre
> ogjorda punkterna gjordes. Meningen ovan var alltså rätt i sak och skulle ha
> mätts fel av det mått den inbjuder till.

## Ett mätfel av mig, för fjärde gången samma form

Första körningen läste svarets nycklar som `traff` och `post`. Verktyget svarar i
`symbols`. Alla sju kom tillbaka som **"INGEN TRÄFF"**, och jag var nära att
skriva att uppslagsverktyget var trasigt för namn validatorn just hade
bekräftat.

Det är samma form som M-34, M-57, M-69, M-76 och M-77: **ett svar som såg
entydigt ut, från ett instrument jag inte hade prövat mot ett känt fall.** Att
det var sjätte gången gjorde det inte lättare att se — det som räddade
mätningen var att talet motsade något jag redan visste.

## Vad som INTE är mätt

* **Om modellen hade använt verktygen.** Att svaret finns är inte att någon
  frågar. En modell med tillgång till `lookup_api` kan låta bli att slå upp.
* **Om svaren hade ändrat koden.** Sex frågor besvarade betyder inte sex fel
  undvikna — modellen gissade ju rätt på alla sex.
* **Bara sju frågor**, och de är de modellen **valde att nämna**. Vad den var
  osäker på utan att säga det är okänt, och det är den intressantare mängden.
* **Andra enheter än vinklar.** Att indexet saknar enhet för rotationer är mätt;
  om det saknar enhet överallt är inte undersökt.
