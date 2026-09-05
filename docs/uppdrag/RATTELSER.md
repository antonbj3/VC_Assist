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
