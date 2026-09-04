# FAS 14 ACCEPTANS — harnessens hårdhet

**beskriver:** `svc/vc_assist_svc/harness/`, `instruktioner/`
**kontrakt:** `docs/spec/70_faser.md` — *"Kvoten mekaniserat/bett mätt om vid
varje körning, med ett golv som bara får gå uppåt. Varje mekanism har en trasig
fixtur som föll före den fanns. En regel som ärligt inte går att mekanisera står
som `EJ_MEKANISK` med skäl."*
**mätningar:** `M-46_harnessens_hardhet.md` (motståndargranskningen),
`M-53_fran_bedd_till_grind.md` (arbetet)
**spärren:** `tests/enhet/test_harnessens_hardhet_sparr.py`

## Status: PASSERAD

## Talet

En regel i en promptsträng är en bön. En regel som avvisar mekaniskt är en
grind. Kvoten mellan de två är harnessens enda ärliga mått på sig själv.

| | M-46 (före) | M-53 (efter) |
|---|---:|---:|
| **mekaniserade** (`allvar=block`, kod avvisar) | 17 → **16** | **37** |
| bedda (`allvar=regel`, prosa i systemprompten) | 29 → 30 | 9 |
| andel mekaniserad | 37 % → 35 % | **80 %** |

Talet 17 var **för högt** när det mättes. `SAK-003` var märkt `block` men ingen
rad kod kunde fälla den — en ren etikett. Det verkliga utgångsläget var 16.

## Per block, och varför summan inte räcker

| Block | M-46 | nu |
|---|---:|---:|
| `00_systemroll` | 0 av 3 | **2 av 3** |
| `10_arbetsordning` | 0 av 6 | **4 av 6** |
| `20_verktygsbruk` | 6 av 9 | **9 av 9** |
| `30_arlighet` | 5 av 8 | **6 av 8** |
| `40_sakerhetsgransen` | 4 av 5 | 4 av 5 |
| `50_domankunskap_vc` | 0 av 7 | **4 av 7** |
| `60_matta_fallor` | **2 av 8** | **8 av 8** |

Spärren räknar **varje block för sig**, inte bara summan. Skälet är mätt: när
helheten låg på 17 av 46 låg `60_matta_fallor` på 2 av 8 — och det är blocket om
fällor som ger tal som *ser rimliga ut*, alltså den dyraste felklassen. En summa
kan stå still medan det block som betyder mest tappar mark.

## De trasiga fallen

| Fall | Måste fällas | Prov |
|---|---|---|
| en regel märkt `block` utan mekanism | ja — etiketten är ingen grind | `test_en_tvingad_regel_namnger_sin_mekanism` |
| en bedd regel utan skrivet skäl | ja — den är en ingen provat att mekanisera | `test_en_bedd_regel_bar_ett_skrivet_skal` |
| golvet ligger under verkligheten | ja — ett golv med luft slutar fånga | `test_golvet_ar_inte_slappare_an_verkligheten` |
| ett block försvinner ur korpusen | ja | `test_inget_block_har_forsvunnit` |
| korpusen byter storlek | ja — talen gäller 46 regler och måste räknas om | `test_kvoten_gar_att_rakna_om_ur_korpusen_sjalv` |

Därutöver: M-53 mätte **varje** ny mekanism genom att stänga av den och köra om
bänken. Fixturerna kom då ut som `SLAPPT`. En mekanism vars fixtur inte faller
när mekanismen tas bort bevisar ingenting.

## Riktningen är motsatt de andra spärrarnas

Tröskelskulden och S5 räknar **skuld** och ska krympa. Den här räknar
**täckning** och ska växa. Gemensamt: talet får inte glida åt fel håll utan att
ett prov faller.

## De nio som ärligt inte går

`SYS-001`, `ARB-002`, `ARB-005`, `ARL-003`, `ARL-007`, `SAK-005`, `DOM-001`,
`DOM-002`, `DOM-007` — var och en med en `EJ_MEKANISK`-fälla och ett skrivet
skäl. `ARL-007` är **mätt** och inte påstådd: ett härkomstkrav i samma mening
hade fällt två av tre matmeningar i bänkens kontrollfall.

En regel som ärligt inte går att mekanisera är inte ett misslyckande. En regel
som **påstås** mekaniserad utan att vara det är det, och M-46 hittade exakt en
sådan.

## Vad fasen INTE påstår

* **Att 80 % är bra.** Talet har ingen extern jämförelse; det finns ingen känd
  mätning av samma sak hos någon annan. Det enda det säger är att det är mer än
  35 %.
* **Att en mekaniserad regel är rätt regel.** Spärren mäter om koden kan fälla
  regeln, inte om regeln är klok.
* **Att modellen följer de bedda nio.** Ingen mätning finns på hur ofta en bedd
  regel faktiskt hålls.
