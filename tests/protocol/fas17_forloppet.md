# FAS 17 ACCEPTANS — vad användaren ser medan det arbetar

**beskriver:** `svc/vc_assist_svc/forlopp/`
**kontrakt:** `docs/spec/24_samtalsloopen.md` §7, `docs/spec/26_appen.md` §3,
`docs/spec/27_operatorsflodet.md`, `docs/spec/50_grindar.md`
**mätning:** `docs/matningar/M-64_vad_anvandaren_ser_medan_det_arbetar.md`
och `docs/matningar/M-93_speglingen_som_inte_aldras.md`
**grind (`70_faser.md`):** *"Medan en körning pågår kan användaren se vad som
händer, vilken grind som fällde och varför, och vad systemet INTE vet. Trasigt
fall: ett fällt läge får aldrig se ut som ett arbetande."*

## Status: STÄNGD 2026-09-05 (M-93). Kvarvarande hål i sista avsnittet.

## Körs med

```
python3 -m pytest tests/enhet/test_forlopp.py tests/enhet/test_forlopp_kallor.py \
                 tests/enhet/test_forlopp_spegel.py tests/enhet/test_forlopp_forare.py -q
```

Och ytan en människa läser:

```
PYTHONPATH=svc python3 -m vc_assist_svc.forlopp <spegelfil>
PYTHONPATH=svc python3 -m vc_assist_svc.forlopp <spegelfil> --folj 1.0
```

Ingen VC, ingen brygga, ingen OPC UA-server, ingen språkmodell. Varje källa
provas mot attrapper, och det står som en begränsning i M-64 §9 och M-93 §8.

## Vad som prövas

| # | Krav ur grinden | Hur det mäts |
|---|---|---|
| 1 | Förloppet går att läsa **medan** körningen pågår | `test_ytan_gar_att_lasa_mellan_tva_varv`: kopplaren kör fem varv, ytan läses efter vart och ett, och de fem avläsningarna skiljer sig |
| 2 | Vilken grind som fällde, och varför | `test_en_fallen_stationsgrind_ger_grindens_egna_ord_ordagrant`: `Stationsdom.utdata` jämförs tecken för tecken mot visningen |
| 3 | Vad systemet inte vet | `test_rackvidden_star_i_varje_visning_ocksa_en_som_gick_igenom`: `50_grindar.md`:s fem poster står i varje läge, också `KLART` |
| 4 | **Ett fällt läge ser aldrig ut som ett arbetande** | tre trasiga renderare, plus en trasig LÄSARE, nedan |
| 5 | Ytan drivs, den går inte bara att driva | `test_forlopp_forare.py`: `Korare.kor` och `Harness.kor` körs på riktigt och måste lämna ett läsbart förlopp efter sig |
| 6 | Ytan går att läsa ur en ANNAN process | `test_speglingen_gar_att_lasa_MELLAN_tva_steg` och `test_planens_korare_for_forloppet_MEDAN_planen_kor`: läsningen sker inne i ett verktygsanrop och delar ingenting med föraren utom en sökväg |
| 7 | En inspelad körning ser ut som en inspelning, inte som nuet | `S3`, och `test_en_avslutad_korning_star_still_utan_att_bli_ovisss` |
| 8 | **LIMITS är lika synligt som utfallet** | `Y12`: ögats egna `SECTION LIMITS`-rader står ordagrant EFTER `VET INTE:`, inte bara på rad sexton av rapporten. Andelen av ytan som handlar om ovisshet går från 22 % till 32 % när rapporten bär sektionen |

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

### Speglingens fem, som bara den råa filen kan svara på (M-93)

`granska` dömer texten mot protokollet och fäller varje renderare som ljuger.
Den kan inte fälla en **läsare** som ljuger: en läsare som fryser klockan
bygger ett protokoll som självt säger ARBETAR, och texten är då korrekt mot
ett protokoll som är fel. `granska_spegling` räknar därför om filens ålder
själv, ur bilden och läsarens klocka.

| Fixtur | Vad den gör | Utfall | Regel |
|---|---|---|---|
| `lasare_som_fryser_klockan` | återskapar förloppet med bildens egen `skrivet` som "nu" | **FÄLLD**, alla 60 avläsningarna | `S2` |
| tomt förlopp vid läsfel | visar en avhuggen eller saknad fil som `EJ STARTAT` | **FÄLLD** | `S1` |
| visning utan speglingsblock | säger inte vilken fil den läste eller hur gammal den är | **FÄLLD** | `S3` |
| kosmetiskt lugn visning | säger TYST men inte att ingen vet om skrivaren lever | **FÄLLD** | `S4` |
| `alder = max(0, nu - skrivet)` | sanerar bort en fil skriven i framtiden | **FÄLLD** | `S5` |
| spegel som bara skriver på slutet | skriver först när läget är avslutat | **FÄLLD**: ARBETAR i 0 av 2 avläsningar under körningen |  |
| bild utan räckvidden | stryker `sensorstuds` ur ovissheterna | **FÄLLD** av läsaren |  |
| okänd stegstatus eller händelsesort i bilden | ett ord ingen gren känner igen | **FÄLLD**: obestämd i stället för halvt läst |  |
| kosmetiskt lugnt fall | fallets skäl byts mot "Ett problem uppstod" | **FÄLLD** | `Y3`, `Y4` |
| gränserna bara i rapporten | skriver ut ögats rapport hel och ordagrant, och inget mer | **FÄLLD** (och Y4 fyrar inte) | `Y12` |

Utöver dessa har varje regel `Y1`–`Y12` och `S1`–`S5` minst en egen trasig
fixtur, och `test_alla_regler_har_minst_en_trasig_fixtur` respektive
`test_alla_speglingsregler_har_minst_en_trasig_fixtur` läser sin egen källa och
faller på en regel som saknar en. Mätt: stängs en S-regel av faller exakt ett
prov, och alla fem provades så.

## Utfall 2026-09-05

```
133 prov gröna i de fyra forlopp-filerna
17 regler (Y1-Y12 + S1-S5), var och en med minst en trasig fixtur
2 forare i svc/ utanfor forlopp/ (var 0)
9 av 9 inspelade ogonrapporter i banken saknar SECTION LIMITS, och visningen
  sager det om var och en
0 av 133 kraver VC
```

Kostnaden i tecken, i `M-60`:s form (spegling inräknad, 13 tecken sökväg):
1 481 arbetande, 2 367 fallen, 2 962 klar med en v1-rapport, 2 852 klar med en
v2-rapport, 1 270 obestämd. Mellan 22 % och 40 % av ytan handlar om vad
systemet inte vet.

## Vad protokollet INTE stänger

* **Fem av sju rapportytor har ingen förare.** Kopplaren, stationsgrinden,
  reparationsslingan, ögonkopplingen och guldgrinden har sin översättning
  byggd och provad i `forlopp/kallor.py`, och noll anropare i `svc/`.
* **Filen växer utan tak.** 4 000 händelser kostar 403 kB och 6,2 ms per
  skrivning; kostnaden över en körning är kvadratisk (M-93 §6.2).
* **Två skrivare mot samma fil är oprövat.** `os.replace` gör varje skrivning
  atomisk, men ingen låsning finns.
* **Fält 1 och 7** i `26_appen.md` §3 — samtalet och systemläget — kräver en
  levande brygga och finns inte. `A-G4` är därmed inte stängd.
* **Ingen operatör har läst ytan.** Att den är läsbar är en bedömning, inte
  en mätning.
* Plattform: **Linux ☑ Windows ☐**. Speglingen rör nu filsystemet, så
  Windows-raden är inte längre formell: `os.replace` och `tempfile.mkstemp`
  beter sig annorlunda där när en läsare håller filen öppen.
