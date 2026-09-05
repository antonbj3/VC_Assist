# Rättelser — läs den här innan du börjar på en ny punkt

Köerna skrevs innan mätningarna var färdiga. När ett tal visar sig vara fel
rättas det här, med datum och tid, i stället för att tigas ihjäl. Din brief kan
alltså ha ändrats sedan du läste den.

**Sista raden är den färskaste. Läs nedifrån.**

---

## 2026-09-05 14:30 — alla köer: reservera mätningsnummer med verktyget

Den gamla instruktionen sa *"kolla högsta numret först"*. Det är läs-sedan-skriv,
alltså en kapplöpning när fem skriver samtidigt. **Kö A och kö B tog båda M-124
inom 91 sekunder från start**, båda enligt instruktionen.

Använd i stället:

```
scripts/nytt_matningsnummer.sh <kort_namn> "<titel>"
```

Den tar samma lås som `scripts/committa.sh`, reserverar numret atomiskt och
skapar filen med rätt rubrikform (`# M-NN — titel`, em-streck, inte kolon) och
ett LIMITS-avsnitt. Skriv aldrig filen för hand.

## 2026-09-05 14:30 — kö A: din mätning heter M-125, inte M-124

Kö B hann 91 sekunder före dig på nummer 124. Din fil flyttades till
`docs/matningar/M-125_openplc_som_tredje_motor.md` och innehållet följde med.
Skriver du till det gamla namnet skapar du en ny kollision.

## 2026-09-05 14:45 — kö C: punkt C5 bar tal från före rättelsen

**Det här var busywork, och det var mitt fel.** C5 bad dig skriva om
scenarierna för "de fem svagaste uppgifterna" utifrån en per-uppgift-tabell
(`P-03 10 överlevande, varav 7 under perturbation`). De talen kom från
mutationskörningen **före** `M-122`:s rättelse, och de flesta av de överlevarna
är initierare — rader som skrivs över innan någon läser dem. Du hade lagat
skador som inte finns.

C5 är omskriven mot `M-122 §2`, som namnger både uppgifterna och botemedlen:
tre behöver ett punktkrav till (`A-03`, `S-01`, `S-07`), tolv behöver en
sekvens till i fem uppgifter (`A-03`, `H-04`, `L-07`, `P-03`, `S-07`), och tolv
är troligen ekvivalenta — men **inte bevisat**, och att avgöra det är arbetet.

C7 var *"säkra mätningen ur /tmp"*. Den är gjord; `M-122` ligger i repot. C7 är
utbytt mot `M-122 §3`: den riktiga F15-mutationen fångas **12 av 12** när
flanken läser material och process, men **1 av 15** när den läser en
återställning. Blindheten är stimulusens, inte spårets.

## 2026-09-05 16:25 — modellkvoten är slut på Muse Spark 1.3; B2 och B3 parkeras

Bara Gemini 3.8 finns kvar, och den ska gå dit den ändrar mest.

**Kö B: kör inte B2 och B3 förrän operatören säger till.** De behöver ~380
modellsvar för n≥3 över banken, och deras syfte är att **mäta en modell** — en
körning på Gemini 3.8 ger ett tal om Gemini 3.8. Att lägga en knapp kvot på att
mäta den knappa modellen är fel växling. Fortsätt i stället med **B1** (de 23
facit — författande, nästan inga modellanrop), **B6b** och **B7**. Kön går
vidare utan att kosta kvot.

**Kö A har företräde till kvoten** tills A2 och A3 är klara. Där är modellen en
arbetare och resultatet är kod som blir kvar: en domare som dömer genom OpenPLC
i stället för genom vår egen ST-tolk. Så länge den inte finns är varje
tillförlitlighetstal projektet har mätt av det som prövas — den tautologi
`85_bankkontraktet.md` förbjuder. Det är den enda punkten som ändrar vad alla
andra siffror betyder.

**Gäller alla som kör en bänkarm:** skriv ut vilken modell armen körde på, i
mätningens rubrik och i dess JSON. `M-110`:s tal är Muse Spark 1.3. En arm på
en annan modell är en **annan mätning**, inte en fortsättning, och de två får
aldrig jämföras utan att skillnaden står skriven.

## 2026-09-05 18:35 — kö B: parkeringen av B2 och B3 är HÄVD

Operatören har beslutat att B ska gå klart på den Gemini-kvot som återstår.
Rättelsen 16:25 gäller alltså inte längre.

**Men ordningen spelar roll, för kvoten är ändlig.** Ta punkterna så här:

1. **B1 först** — 16 av 23 facit återstår (A-01…A-06 är skrivna). Det är
   författande, nästan inga modellanrop, och det är basen allt annat vilar på.
2. **B6b och B7** — revisioner, inga modellanrop.
3. **B2 och B3 sist**, med den kvot som då är kvar. Kör hellre färre uppgifter
   med **n ≥ 3** än alla 63 med n = 1. Ett tal utan spridning säger ingenting
   om tillförlitlighet, och tillförlitlighet är hela frågan. Flusha JSON efter
   varje uppgift — en avbruten körning har tappat tio lösta uppgifter i det
   här projektet förut.

**Kravet som står kvar oförändrat:** skriv ut vilken modell armen körde på, i
mätningens rubrik och i dess JSON. `M-110`:s tal är Muse Spark 1.3. En arm på
Gemini är en **annan mätning**, inte en fortsättning, och de två får aldrig
jämföras utan att skillnaden står skriven.
