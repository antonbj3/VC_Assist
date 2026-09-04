# FAS 17 ACCEPTANS — vad användaren ser medan det arbetar

**beskriver:** `svc/vc_assist_svc/forlopp/`
**kontrakt:** `docs/spec/24_samtalsloopen.md` §7, `docs/spec/26_appen.md` §3,
`docs/spec/27_operatorsflodet.md`, `docs/spec/50_grindar.md`
**mätning:** `docs/matningar/M-64_vad_anvandaren_ser_medan_det_arbetar.md`
**grind (`70_faser.md`):** *"Medan en körning pågår kan användaren se vad som
händer, vilken grind som fällde och varför, och vad systemet INTE vet. Trasigt
fall: ett fällt läge får aldrig se ut som ett arbetande."*

## Körs med

```
python3 -m pytest tests/enhet/test_forlopp.py tests/enhet/test_forlopp_kallor.py -q
```

Ingen VC, ingen brygga, ingen OPC UA-server, ingen språkmodell. Varje källa
provas mot attrapper, och det står som en begränsning i M-64 §9.

## Vad som prövas

| # | Krav ur grinden | Hur det mäts |
|---|---|---|
| 1 | Förloppet går att läsa **medan** körningen pågår | `test_ytan_gar_att_lasa_mellan_tva_varv`: kopplaren kör fem varv, ytan läses efter vart och ett, och de fem avläsningarna skiljer sig |
| 2 | Vilken grind som fällde, och varför | `test_en_fallen_stationsgrind_ger_grindens_egna_ord_ordagrant`: `Stationsdom.utdata` jämförs tecken för tecken mot visningen |
| 3 | Vad systemet inte vet | `test_rackvidden_star_i_varje_visning_ocksa_en_som_gick_igenom`: `50_grindar.md`:s fem poster står i varje läge, också `KLART` |
| 4 | **Ett fällt läge ser aldrig ut som ett arbetande** | tre trasiga renderare, nedan |

## De trasiga fallen — alla måste falla

| Fixtur | Vad den gör | Utfall | Regler |
|---|---|---|---|
| `renderare_som_snurrar_vidare` | frågar efter det pågående steget och skriver ut hur länge det pågått utan att först fråga vilket läge körningen är i | **FÄLLD** | Y1, Y2, Y4, Y11 |
| `renderare_som_skriver_om_grinden` | kortar grindens utdata, normaliserar radbrytningar och byter fackspråket mot en vänlig mening | **FÄLLD** | Y4 |
| `renderare_utan_arlighetsbesked` | skriver ut ögats text ordagrant men utelämnar beskedet att `SECTION HONESTY` aldrig fanns | **FÄLLD** | Y6 |
| `sammanfattande_kalla` | kortar grindens utdata redan när förloppet förs, alltså före varje renderare | **FÄLLD** av källprovet |
| slukat `Kopplarfel` | fångar undantaget och låter förloppet stå kvar på `ARBETAR` | **FÄLLD**: `kor_kopplaren` gör fallet till en händelse |
| hjärtslag som framsteg | `EJ_FRAMSTEG = ()`; 600 pulser utan att något händer | **FÄLLD** av Y9 |
| okänd planstatus | en status ingen gren känner igen, som annars blivit osynlig | **FÄLLD** av `Forloppsfel` |
| en rad över 100 tecken | visningens egen rad, inte någon annans | **FÄLLD** av breddprovet |

Utöver dessa har varje regel `Y1`–`Y11` minst en egen trasig fixtur, och
`test_alla_regler_har_minst_en_trasig_fixtur` läser sin egen källa och faller
på en regel som saknar en.

## Utfall 2026-09-04

```
79 prov gröna i tests/enhet/test_forlopp.py + test_forlopp_kallor.py
11 regler, var och en med minst en trasig fixtur
0 av 79 kräver VC
```

Kostnaden i tecken, i `M-60`:s form: 1 362 arbetande, 2 321 fallen, 2 457
klar. Mellan 24 % och 44 % av ytan handlar om vad systemet inte vet.

## Vad protokollet INTE stänger

* **Ingenting driver ytan än.** Noll moduler i `svc/` utanför `forlopp/`
  konstruerar ett `Forlopp`. Hålet står rött med flit i
  `tests/motbevis/test_forloppet_har_ingen_forare_motbevis.py`.
* **Fält 1 och 7** i `26_appen.md` §3 — samtalet och systemläget — kräver en
  levande brygga och finns inte. `A-G4` är därmed inte stängd.
* **Ingen operatör har läst ytan.** Att den är läsbar är en bedömning, inte
  en mätning.
* Plattform: **Linux ☑ Windows ☐**. Provet rör varken filsystem eller
  process, så Windows-raden är formell — men den är inte körd.
