# M-164 — baslinjen mot nollprogrammet i skala: 22 av 44 under, och två förklaringar som inte håller

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell, ingen OpenPLC.
**Prövar:** Två spärrar i `tests/enhet/test_baslinje.py` föll när banken växte
från 26 till 44 dömbara uppgifter. Båda talen får röra sig, men bara med en
härledning.

## 1. Nämnaren: (1747, 140, 142) → (2302, 182, 188)

Rörelsen har **två** orsaker, och det är hela poängen med att härleda den:

| | punktkrav | invariantnamn | flanker |
|---|---:|---:|---:|
| M-123:s 26 uppgifter | 1747 | 140 | 142 |
| **17 nya uppgifter med facit** | +439 | +42 | +46 |
| **21 befintliga som fått fler krav** | +116 | 0 | 0 |
| **44 uppgifter** | **2302** | **182** | **188** |

De 17 nya är kö B:s `facit_spar`-arbete: A-02, A-04, A-05, A-06, C-01, C-02,
C-03, C-05, H-02, H-03, L-02, L-03, L-04, P-01, P-02, P-04, P-05.

De 116 tillagda kraven i befintliga uppgifter är kö C:s stimuli — nya scenarier
som skrevs för att göra överlevande mutanter synliga. Störst: `S-07` +26,
`H-05`/`L-06`/`T-09` +13 vardera, `L-07` +10.

Att en befintlig uppgifts tal rör sig är precis vad spärren finns för att
fånga. Det gick att förklara; det är skillnaden mot att bara skriva om talet.

## 2. Golvet: 22 av 44 ligger under nollprogrammet

Listan `BASLINJEN_UNDER_NOLLPROGRAMMET` växer från 11 till 22. De elva nya:
`A-02`, `A-04`, `A-06`, `C-01`, `C-02`, `C-03`, `C-05`, `H-02`, `L-04`,
`P-02`, `P-05`.

## 3. Två förklaringar prövade, båda faller

**Förklaring 1, ur provets egen docstring:** *"ett nollprogram uppfyller varje
punktkrav som säger att en utgång ska vara LÅG, och ju fler förreglingar en
uppgift bär desto fler sådana krav har den."*

`M-123` mätte den på 26 uppgifter och fann att invariantantalet inte skiljer
grupperna. Med 44 står det fast.

**Förklaring 2, min egen, formulerad ur medianerna:** de under golvet har
kvoten invarianter/punktkrav 0,37, de över 0,54. Alltså skulle *balansen*
mellan de två sorternas krav avgöra, inte det absoluta antalet.

Prövad mekaniskt: den bästa tröskeln på kvoten (0,462) klassar **29 av 44
rätt — 66 %**, mot en grundnivå på 50 % när grupperna är 22 och 22. Femton
uppgifter hamnar fel, åtta över med låg kvot (`H-03` 0,17, `P-01` 0,22) och sju
under med hög (`C-06` 1,01, `P-07` 0,64).

Fördelningarna överlappar nästan helt. **Kvoten förklarar det inte heller.**

## 4. Vad som står kvar

Vilken egenskap hos en uppgift som avgör om skalan inverterar är **omätt**, nu
efter två prövade och fallna hypoteser. Så länge 22 av 44 har inverterad skala
är varje procenttal ur påståenderäkningen ett medelvärde över två mätningar åt
olika håll — samma rad `M-62` skrev.

Spärren står kvar och gör sitt jobb: den kräver att listan skrivs ned, inte att
den förstås. Men en lista som växer från 10 till 11 till 22 utan att någon vet
varför är på väg att bli en lista ingen läser.

## LIMITS

* **Båda hypoteserna prövades på samma 44 uppgifter som gav upphov till dem.**
  Kvottröskeln 0,462 är dessutom vald genom att söka den bästa på just den här
  datan — 66 % är alltså ett övre estimat, inte ett väntat utfall på ny data.
* **Baslinjen körs bara på `NIVA_SPEC`.** `NIVA_MAGER` och `NIVA_PROSA` är
  omätta här, och en uppgift kan mycket väl ligga över sitt golv på en nivå och
  under på en annan.
* **`uppfyllda` är ett antal, inte vilka.** Två domar med samma antal kan
  uppfylla helt olika påståenden. Jämförelsen säger vem som uppfyller *fler*,
  aldrig *vilka*.
* **Ingen tredje hypotes prövades.** Jag stannade vid två för att en tredje
  formulerad ur samma data hade haft samma svaghet.
* **De 17 nya uppgifternas facit skrevs av en annan session samma dag**, och de
  116 tillagda kraven av ytterligare en. Ingen av dem är oberoende granskad här.
