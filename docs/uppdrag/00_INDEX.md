# Fem köer, fem sessioner, tio timmar

Läs **`00_GEMENSAMT.md`** först, oavsett vilken kö du fått. Det som står där
gäller alla fem: commit-låset, disciplinerna, VC-reglerna, maskinen.

| Kö | Fil | Vad den avgör |
|---|---|---|
| **A** | `KO_A_motorn_pa_riktigt.md` | Att domen kommer ur den motor som faktiskt kör, inte ur vår egen tolk. Skanncykeln. Exporten ut. |
| **B** | `KO_B_banken_i_skala.md` | De 37 saknade svaren, enskott över skalan med spridning, och baslinjen parad med varje tal. |
| **C** | `KO_C_de_91_overlevande.md` | De 91 skador bänken inte ser — varav 67 osynliga även under störning. Marginalen under varje tillförlitlighetstal vi har. |
| **D** | `KO_D_ogat_och_scenen.md` | Den femte domaren, fälld av en riktig cell. Taket under belastning. Fler linor än en. |
| **E** | `KO_E_universalitet_och_llm.md` | Windows utan en Windows-maskin, det tysta OneDrive-felet, och om en LLM hittar det den behöver. |

## Var ni krockar, och vad som gäller då

* **A och B delar `bank/domare.py`.** A bygger en andra domare bredvid den
  befintliga; B rör den befintliga bara efter samråd. Domaren är gemensam yta.
* **B och C delar `bank/uppgifter/*.json`.** B skriver `facit_spar` på de 37;
  C skriver `scenarios` på de svagaste. Olika fält, samma filer — committa
  ofta och smått, så blir sammanslagningen billig.
* **C och D delar frågan om vad en domare ser.** C mäter det med mutationer,
  D med riktiga VC-celler. Läs varandras mätningar.
* **D är den enda som startar VC.** De andra fyra rör aldrig ett wine-prefix.

## Två äldre briefer

`OPENCODE_A_openplc_som_tredje_motor.md` och
`OPENCODE_B_tillforlitligheten_i_skala.md` är **ersatta** av `KO_A` och `KO_B`.
De står kvar för sin bakgrund — KO_A och KO_B upprepar inte den.

## Det som gäller alla fem, i en mening

Ett resultat som visar att frågan var fel ställd är ett fullgott resultat. Ett
svar på en fel ställd fråga är det inte.
