# M-123 — nämnaren flyttade sig, och golvet med den

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen modell, ingen OpenPLC.
**Prövar:** Två spärrar i `tests/enhet/test_baslinje.py` föll samtidigt när
banken växte från 24 till 26 dömbara uppgifter. Spärrarna gjorde sitt jobb:
båda talen får röra sig, men bara om någon skriver ned varför.

## Vad som hände

`L-01` och `P-03` fick `facit_spar` och blev dömbara. Det räckte för att fälla
två prov som ingenting hade med varandra att göra.

## 1. Påståenderäkningen: (1634, 130, 132) → (1747, 140, 142)

Räkningen går ihop exakt, per uppgift:

| uppgift | punktkrav | invariantnamn | flanker |
|---|---|---|---|
| tidigare 24 | 1634 | 130 | 132 |
| `L-01` | +55 | +5 | +5 |
| `P-03` | +58 | +5 | +5 |
| **26 uppgifter** | **1747** | **140** | **142** |

Ingen befintlig uppgifts tal ändrades. Hela rörelsen är de två nya
uppgifternas egna påståenden, och därför är den laglig att skriva ned.

## 2. Golvet: `L-01` hamnar under nollprogrammet, `P-03` inte

Ett *nollprogram* är kod som inte gör någonting. Baslinjen ska slå det — en
baslinje som inte slår sitt eget golv mäter ingenting.

Mätt, uppfyllda påståenden:

| uppgift | nollprogram | baslinje | läge |
|---|---|---|---|
| `L-01` | 57 | 49 | **8 under** |
| `P-03` | 58 | 66 | 8 över |

`L-01` går alltså in i `BASLINJEN_UNDER_NOLLPROGRAMMET`, som växer från 10 till
11 av 26. `P-03` gör det inte.

## Det som inte stämmer i den befintliga förklaringen

Provets docstring förklarar inversionen så här: *"ett nollprogram uppfyller
varje punktkrav som säger att en utgång ska vara LÅG, och ju fler förreglingar
en uppgift bär desto fler sådana krav har den."*

Om det vore hela förklaringen skulle invariantantalet skilja de två grupperna.
Det gör det inte. Mätt över alla 26:

| | invarianter | läge |
|---|---|---|
| `C-06` | 72 | **under** |
| `P-06` | 63 | över |
| `S-06` | 63 | **under** |
| `A-07` | 64 | över |
| `S-01` | 18 | över |
| `A-03` | 13 | **under** |
| `T-05` | 17 | **under** |
| `T-04` | 20 | över |

De två grupperna överlappar helt i invariantantal. Elva under golvet spänner
13–72 invarianter; femton över spänner 18–64. Rikedom på förreglingar
**förklarar inte** vilka uppgifter som inverterar.

Vad som faktiskt gör det är omätt. Förklaringen i docstringen står kvar som en
rimlig delförklaring, men den är inte belagd, och den ska inte citeras som om
den vore det.

## Vad som står näst

Frågan "vilken egenskap hos en uppgift avgör om skalan inverterar" är öppen och
hör hemma i baslinjearbetet (`docs/uppdrag/KO_B_banken_i_skala.md`). Den är
värd att svara på: så länge elva av 26 uppgifter har en inverterad skala är
varje procenttal ur påståenderäkningen ett medelvärde över två olika mätningar
åt olika håll — precis den rad `M-62` redan skrev.
