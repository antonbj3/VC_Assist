# FAS 23 ACCEPTANS — vad användaren ser när något har dött

**beskriver:** `svc/vc_assist_svc/aterhamtning/`
**kontrakt:** `docs/spec/26_appen.md` §3.0–3.2, `docs/spec/27_operatorsflodet.md`
§4.5 och §5.1, `docs/spec/28_lagen_och_aterhamtning.md`, `docs/spec/50_grindar.md`
**mätning:** `docs/matningar/M-103_aterhamtningen_som_anvandaren_ser_den.md`
**föregångare:** `tests/protocol/fas17_forloppet.md` — fas 17 stängde ytan som
visar vad som händer **medan** en körning går. Den här tar vid där körningen dog.
**grind (`70_faser.md`):** *"När ett delsystem slutat svara säger ytan vad som
dog, varför, om något försöker igen och vad operatören själv kan göra — och den
fäller sin egen grind."*

## Status: STÄNGD 2026-09-05 (M-103). Kvarvarande hål i sista avsnittet.

## Körs med

```
python3 -m pytest tests/enhet/test_aterhamtning.py \
                 tests/enhet/test_aterhamtning_grind.py \
                 tests/enhet/test_aterhamtning_stegen.py \
                 tests/enhet/test_aterhamtning_dodsfall.py -q
python3 tests/protocol/kor_fas23_anvandarlagret.py
python3 tests/protocol/kor_fas23_anvandarlagret.py --visa
```

Och ytan en människa läser:

```
PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil>
PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil> --loggar ~/
PYTHONPATH=svc python3 -m vc_assist_svc.aterhamtning <bildfil> --folj 1.0
```

Ingen VC, ingen brygga, ingen OpenPLC, ingen språkmodell. **En sak är inte en
attrapp:** `connect()` mot en lyssnande socket som ingen accepterar körs mot en
riktig socket i processen. Det är premissen bakom regel L-1, och den vore
värdelös som attrapp.

## Vad som INTE görs om från fas 17

Speglingen är fas 17:s. `forlopp.spegel.Spegel` tar vilket objekt som helst med
`till_json`, skriver atomiskt med `os.replace`, och är redan provad —
`Systembild` använder den oförändrad. Rubriken `VET INTE:` och frasen
`pågår sedan` importeras ur `forlopp` i stället för att skrivas av: två ytor
som säger samma sak med olika ord är två ordförråd, och det ena kommer att
glida.

Det som **är** nytt är vad som kan ljuga. Fas 17 fäller en **renderare** och en
**läsare**. Här finns en tredje: en **härledning**. Ett läge är en slutsats om
en tystnad, och den som drar slutsatsen kan dra fel.

## Vad som prövas

| # | Krav ur grinden | Hur det mäts |
|---|---|---|
| 1 | Läget är HÄRLETT ur avläsningarna och **läsarens** klocka | `granska` anropar `bild.lage_for` själv i stället för att fråga den som visar; `Å1` jämför mot första raden |
| 2 | En lyckad `connect()` är inget livstecken | `test_connect_lyckas_mot_en_socket_ingen_accepterar` mot en riktig socket: 20 av 20 anslöt, 0 av 20 svarade |
| 3 | En gammal avläsning bär inget läge | `test_en_harledning_som_fryser_klockan_sager_ansluten_i_60_av_60` |
| 4 | Vad som dog, varför, och vad operatören gör | de fyra dödsfallen, var och en med orsak, vägar och kanskap |
| 5 | **Ingenting försöker igen — om ingenting försöker igen** | `Å6` och `Å8`, med `renderare_som_lovar_nytt_forsok` som fixtur |
| 6 | Ett omöjligt försök redovisas aldrig som pågående | mekaniserat i `Systembild.borja_forsok` (kastar) OCH i grinden (`Å6`), två oberoende linjer |
| 7 | Ett obestämt läge är obestämt | `Å1`, `Å12`, och den obestämda visningens egen gren |
| 8 | Orsaken hittas ur loggarna, och en obesvarad fråga stoppar stegen | `test_aterhamtning_stegen.py`, sju frågor, tre tal |
| 9 | Ytan går att läsa ur en ANNAN process | `test_ytan_gar_att_lasa_ur_en_annan_process_och_aldras_mot_lasarens_klocka` |
| 10 | Räckvidden står i varje visning, också en grön | `Å10`, och `test_en_gron_yta_bar_rackvidden_anda` |

## De trasiga fallen — alla måste falla

| Fixtur | Vad den gör | Utfall | Regel |
|---|---|---|---|
| `harledning_som_fryser_klockan` | räknar åldern med avläsningens egen tid som "nu" | **FÄLLD**, och den säger LEVANDE i 60 av 60 | `Å1` |
| `harledning_som_raknar_connect_som_liv` | en lyckad `connect()` blir ANSLUTEN | **FÄLLD** | `Å1` |
| `renderare_med_fel_lage` | skriver ett annat läge än avläsningarna bär | **FÄLLD** | `Å1` |
| `renderare_som_utelamnar_ett_delsystem` | tar bort raden för OpenPLC | **FÄLLD** | `Å2` |
| `renderare_som_snurrar_vidare` | skriver `pågår sedan` i ett dött läge | **FÄLLD** | `Å3` |
| `renderare_utan_orsak` | byter orsaken mot *"Ett problem uppstod."* | **FÄLLD** | `Å4` |
| `renderare_som_skriver_om_felet` | byter sondens ord mot en vänlig mening | **FÄLLD** | `Å5` |
| `renderare_som_lovar_nytt_forsok` | *"Ett problem uppstod, vi försöker igen"* medan ingenting försöker | **FÄLLD** | `Å6` |
| ett självstartsförsök efter `utan självstart` | kanskapen frös som `okänt` och är nu `kan inte lyckas` | **FÄLLD** om det räknas bland de pågående | `Å6`, `Å12` |
| `renderare_utan_kanskap` | listar vägarna utan att säga om de kan lyckas | **FÄLLD** | `Å7` |
| `renderare_som_tiger_om_att_inget_forsoker` | utelämnar `Ingenting försöker igen` | **FÄLLD** | `Å8` |
| `renderare_som_doljer_avlasningar` | trimmar utan att säga hur mycket | **FÄLLD** | `Å9` |
| `renderare_utan_rackvidd` | stryker avsnittet om vad systemet inte vet | **FÄLLD** | `Å10` |
| `renderare_utan_stegen` | bryggan är nere och stegen körs inte | **FÄLLD** | `Å11` |
| `renderare_som_tiger_om_utan_sjalvstart` | nämner inte att självstarten är avslagen | **FÄLLD** | `Å12` |
| `renderare_utan_alder` | *"avläst nyligen"* i stället för talet | **FÄLLD** | `Å13` |
| `renderare_med_lang_rad` | en egen rad över 100 tecken | **FÄLLD** | `Å14` |
| en avhuggen systembild visad som `FRÅNKOPPLAD` | ett läsfel som ser ut som en lugn början | **FÄLLD** | `Å1` |
| `Avlasning(svarade=False, fel="")` | en tystnad utan ord | **KASTAR** i protokollet |  |
| `borja_forsok(SJALVSTART, SPARAD_LAYOUT)` | ett försök som inte kan lyckas | **KASTAR** i protokollet |  |
| `avsluta_forsok(lyckades=False, ordagrant="")` | ett misslyckande utan ord | **KASTAR** i protokollet |  |
| `_tom_strang_som_svar` | en oläsbar logg blir `""` i stället för `None` | **FÄLLD**: stegen pekar ut *"Tillägget startade aldrig"* med full säkerhet, där den ärliga säger vet inte |  |
| en bild som saknar nycklar, eller talar version 99 | läsaren gissar sig genom formatet | **KASTAR**, blir OBESTÄMT i visningen |  |

`test_alla_regler_har_minst_en_trasig_fixtur` läser sin egen källa och faller på
en regel som saknar en. En grind utan trasig fixtur är oprövad
(`95_testprotokoll.md`).

## Utfall 2026-09-05

```
88 prov gröna i de fyra aterhamtning-filerna
14 regler (Å1-Å14), var och en med minst en trasig fixtur
9 lägen (specens sju + OBESTÄMT + BLOCKERAD), 18 orsaker, 10 vägar tillbaka
0 av 88 kräver VC
```

| Mätning | Tal |
|---|---|
| härledning med frusen klocka säger LEVANDE | **60 av 60** avläsningar av en sond som dog efter den första |
| samma bild, med läsarens klocka | **3 av 60** LEVANDE, **57 av 60** OBESTÄMT |
| `connect()` mot en socket ingen accepterar | **20 av 20** lyckades, median **0,12 ms** |
| `ping` genom samma socket | **0 av 20** svarade |
| orsaker med ett automatiskt försök | **3 av 18** |
| orsaker vars automatiska försök är mätt att kunna lyckas | **2 av 18** |
| orsaker som lovar att självstarten kan lyckas | **0 av 18** (strukturell spärr) |
| dödsfall där systemet kom tillbaka av sig självt | **1 av 4** — och återkomsten syns i ytan |
| andel av ytan som handlar om vad systemet inte vet | **31,8 % – 42,9 %** |
| stegen mot de fem tysta fällorna | **5 av 5 rätt orsak**, och den olästa loggen ger `okänd`, inte en gissning |

## Vad protokollet INTE stänger

* **Ingen sond går av sig själv.** Ytan läser avläsningar som någon annan gjort.
  Vem, och hur ofta, är inte bestämt (`28_lagen_och_aterhamtning.md` §9 fråga 5).
* **Ingen väg tillbaka är körd mot en VC som verkligen gick ned.** Alla fyra
  dödsfallen är framprovocerade mot attrapper. Det står som en permanent
  ovisshet i **varje** visning, inte bara här.
* **Läget `BLOCKERAD` kan inte fyras.** Raden `modal oppen` finns inte i koden
  (`26_appen.md` §1.1.1). Väntar på M-21.
* **Wines lyssningskö är oprövad.** Mätningen av `connect()` gäller den här
  värdens kärna, inte Wines winsock (M-25).
* **`T_ping`, `T_nere` och `T_modal` är PRELIMINÄRA.** De två första är härledda
  ur M-03:s tur och retur och aldrig mätta mot en död brygga; den tredje har
  ingen mätning alls.
* **Ingen operatör har läst ytan.** Att den är läsbar är en bedömning, inte en
  mätning — samma öppna punkt som fas 17 lämnade.
* Plattform: **Linux ☑ Windows ☐**. Socketmätningen är kärnberoende, och
  `netstat`-vägen i `FRIGOR_PORTEN` är skriven men aldrig körd (M-44).
