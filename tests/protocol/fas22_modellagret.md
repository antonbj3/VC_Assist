# FAS 22 ACCEPTANS — modellagret

**beskriver:** `svc/vc_assist_svc/llm/`
**kontrakt:** `docs/spec/23_llm_granssnitt.md`, `docs/spec/24_samtalsloopen.md`,
`docs/spec/25_kontextbudget.md`, `docs/spec/70_faser.md` fas 22
**mätning:** `docs/matningar/M-102_modellagret_mot_riktiga_verktygssvar.md`
**körs av:** `tests/protocol/kor_fas22_modellagret.py` plus
`tests/enhet/test_kontextbudget.py`, `test_verktygssvarets_kapning.py`,
`test_ogontrimning.py` och `test_modellturen.py`
(L1 — ingen VC, ingen brygga, ingen språkmodell)

## Status 2026-09-05: **grön i L1**

**97 prov** i de fyra enhetsfilerna, plus acceptanskörningen med **13 trasiga
fall**. Alla fälls, och var och en med sin egen kod.

Kör:

```
python3 tests/protocol/kor_fas22_modellagret.py
python3 -m pytest tests/enhet/test_kontextbudget.py \
                 tests/enhet/test_verktygssvarets_kapning.py \
                 tests/enhet/test_ogontrimning.py \
                 tests/enhet/test_modellturen.py -q
```

Vad protokollet **inte** bevisar står i avsnitt F.

## Grinden, ordagrant

> Budgetens verkliga beteende mätt över **riktiga** verktygssvar ur repot, och
> loopens tillstånd genom en attrapp som svarar fel med flit. Trasiga fall:
> ett kapat svar som **ser helt ut** måste fällas; tystnad från modellen får
> **aldrig** bli ett godkänt slutsvar; ett verktygssvar som spränger budgeten
> får inte tyst tappa den del som bar felet.

Tre halvor, och den tredje är den svåra. De två första går att se. Den tredje
är den som ser ut som ett svar ända tills någon jämför med råvaran.

## Vad protokollet kräver av formen

**En grind utan trasig fixtur är ingen grind.** Varje punkt nedan prövas åt
**båda** hållen: att kontrollen faller på ett verkligt fel, och att den släpper
igenom det korrekta. En kontroll som bara provats åt ena hållet är oprövad
(`docs/spec/95_testprotokoll.md`).

**Korpusen växer med banken.** Talen nedan är mätta 2026-09-05 med 51
bankuppgifter i `bank/uppgifter/`. Läggs en uppgift till växer korpusen, och
talen ska då läsas om — proven kräver storleksordningar (`> 100` svar,
`> 50` kapade), aldrig ett exakt antal.

**Korpusen är riktig.** 207 verktygssvar kommer ur repots egna
`DATA_HANDLERS`, anropade med argument som också kommer ur repot: katalogens 65
URI:er, bankens 51 uppgifter, API-indexets typnamn, hjälpmodulernas egen
uppräkning. Nio ögonrapporter är bankens egna. 95 turer är
efterlevnadsbankens.

---

## A. Talen körningen rapporterar

| # | Tal | Utfall 2026-09-05 |
|---|---|---|
| A1 | Registrerade verktyg, schemats storlek | **122** verktyg (53 skrivande), **98 324 byte**, medel **805 byte** |
| A2 | Fönster som postens 10 %-tak skulle kräva | **327 750 tokens** för hela schemat, **47 920** för enbart alltid-med-listan |
| A3 | Riktiga verktygssvar | **207**, minsta **294 B**, median **2 388 B**, största **67 911 B** |
| A4 | Svar som bär sin egen räkning | **19 av 207** |
| A5 | Kapade svar per fönster | 8 000 → **45**, 32 000 → **19**, 128 000 → **0**, 200 000 → **0** |
| A6 | Anmärkningar på kapade svar | **0** vid varje fönster |
| A7 | Anmärkningar på **hela** svar (kontrollen) | **0 av 207** |
| A8 | Urvalsträff över 95 turer | **87 av 105** anrop, urvalets medelstorlek **39 av 122** |
| A9 | Missade **läsande** anrop | **0** (kravet) |
| A10 | Missade **skrivande** anrop | **15** — alla, och det är fyndet |
| A11 | Turer som gick en väg utanför tillståndsmaskinen | **0 av 95** |
| A12 | Bokföringsfel i budgeten över 95 turer | **0** |
| A13 | Tillståndsmaskinens täckning | **22 av 22** nåbara övergångar, **7 av 8** lägen |
| A14 | Ögonrapporter, lång rapport | **9 606 → 1 169 byte**, 2 noteringar utanför blocket |
| A15 | Den naiva ordlistan mot vår | naiv skulle trimma **15** rader; vår behåller fynden |

Talen A8–A10 är fasens skarpaste: **varje läsande anrop täcks, och varje
anrop som missas är skrivande.** Det är inte en svaghet i rangordningen utan
en egenskap hos indata — uppgifterna är svenska och verktygsnamnen engelska.
Ett skrivande verktyg kommer ur **planen**, inte ur en gissning.

---

## B. DE TRASIGA FALLEN

De här är protokollets kärna. Var och en **måste** fällas, och var och en måste
fällas med **sin egen kod** — inte med "något är fel".

| # | Fall | Kod | Vad det bevisar |
|---|---|---|---|
| T1 | Ett kapat svar som **ser helt ut** | `K2_SER_HELT_UT` | halva listan borta, svarets egen räkning kvar. Parsar felfritt |
| T2 | Ett svar klippt **på tecken** | `K1_OGILTIG_JSON` | läsbart för ett öga, oparsbart för allt annat |
| T3 | Ett internt konsistent men kort svar | `K2` mot råvaran | den tystaste formen: bara jämförelsen med råvaran fäller den |
| T4 | Ett för stort svar som tappade felet | `K4_FEL_TAPPAT` | det är precis den delen som behövs |
| T5 | Tystnad märkt som klar | `T3_TYST_GODKANNANDE` | tystnad är aldrig ett godkännande (I3) |
| T6 | En trimning utan händelse | `B1_TYST_TRIMNING` | innehållet ändrades utan att någon skrev ned det |
| T7 | En händelse utan trimning | `B2_HANDELSE_UTAN_TRIMNING` | bokföring utan verklighet — grinden prövas åt båda hållen |
| T8 | En budget under det skyddade | `Budgetfel` | ett fel, aldrig en tyst trimning (S1) |
| T9 | En omskriven domsrad | `O4_OMSKRIVEN_RAD` | en sammanfattning får aldrig bli ett andra omdöme |
| T10 | En bortklippt `HONESTY`-sektion | `O3_SKYDDAD_SEKTION` | dess frånvaro går inte att skilja från att den aldrig kördes |
| T11 | Den minsta `MINDIST`-raden bortkapad | `O2_FYND_BORTA` | raden bär just den storhet sektionen finns för |
| T12 | Ett namn turen behöver, sammanfattat bort | `S1_NAMN_BORTA` | en miss ändrar regel 1; den är ingen ratt att skruva på |
| T13 | `avkortad` svald i en sammanfattning | `S2_AVKORTAD_SVALD` | att svälja `avkortad` är att göra fail-closed till fail-open |

### T14–T17: fällda av enhetsproven, inte av körningen

| # | Fall | Var |
|---|---|---|
| T14 | En modellprofil utan ett fält | `Profilfel` som namnger fältet **och vad det används till**, ett prov per fält |
| T15 | Ett otolkbart modellsvar | ett omförsök, sedan `SVARSFEL`. Utan vakten tar adapterns undantag hela turen med sig |
| T16 | Ett verktyg som inte finns | `AVVISAD` före körning; kanalen får **noll** anrop |
| T17 | Ett verktyg som svarar efter sitt tak | `TAK_TID`, aldrig ett `ok`. Klockan är injicerad — ett prov som mäter en tidsgräns genom att sova mäter schemaläggaren |

---

## C. ORDLISTEPROVET

Det här är fasens egen spärr mot den felklass repot mätt fyra gånger
(`M-94` två gånger, `M-95`, `M-98`): **en ordlista som fyrar på fel storhet.**

Trimningen av ögats rapport är den enda plats i modellagret där en ordlista
avgör något: *är raden "OK" nog för att få försvinna?* Tre riktiga former där
den naiva domaren (`"OK" in rad`) har fel:

| Rad | Naiv domare | Vår domare |
|---|---|---|
| `MINDIST OK_ROBOT+STANGSEL 412.000mm t=1.200s` | "OK" ⇒ trimma | raden har **ingen dom**; MINDIST bär ett avstånd. Trimmas bara som observation, och den **minsta** står alltid kvar |
| `STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s` | "OK" ⇒ trimma | domen är `MISSING`. Det är ett **fynd**, och hela sektionen går fram |
| `EDGE ST100_STA_DONE RISE t=0.500s` | ingen träff | ingen dom, inget fynd ⇒ får trimmas, med första och sista raden kvar |

**Mekaniken:** statusen läses ur **grammatikens egen alternativgrupp**
(`oga_kontrakt.RADER`), inte ur en delsträngssökning. Domsordförrådet kommer ur
kontraktet (`_FYNDORD`, `_OSAKERORD`) plus de fem godkännandeorden i
`25_kontextbudget.md`. Grupper som `(RISE|FALL)` och `(RUN|PRIOR)` ser ut som
domsgrupper men är det inte, därför att orden inte står i ordförrådet.

**Motprovet hör till fixturen:** provet påstår inte bara att vår domare har
rätt — det kräver att den **naiva** domaren fyrar, på båda raderna. Utan det
vore regeln bara ett påstående.

Samma disciplin gäller kapningens skydd av feldelen: det är **strukturellt**
(felet ligger i kuvertet) och inte en ordlista över fältnamn. Provet
`test_ett_falt_som_HETER_nagot_med_fel_i_ar_inte_ett_fel` håller det på plats
med ett fält som heter `felmarginal_mm` och en komponent som heter
`Felsokningsstation`.

Och en tredje: `test_faltet_antal_bar_tva_storheter_och_granskningen_vet_det`.
Fältet `antal` betyder "poster i listan" i de flesta verktyg och "träffar
totalt" i `search_installed_library`. En kontroll kalibrerad på det ena missar
en verklig kapning i det andra.

---

## D. Vad varje modul svarar för

| Modul | Äger | Trasigt fall |
|---|---|---|
| `llm/matt.py` | storleken i byte, tecken och tokens, och de två antagandena | budgeten tar det **högsta** talet; en uppskattad räknare får marginal |
| `llm/profil.py` | modellprofilens slutna yta | ett saknat fält kastar och namnger vad det används till |
| `llm/urval.py` | vilka verktyg som exponeras | ett läsande anrop utanför regeln fäller provet |
| `llm/kapning.py` | ett svar som inte får plats | T1–T4 |
| `llm/ogontrim.py` | ögats rapport, ordagrant | T9–T11, plus ordlisteprovet |
| `llm/scenvy.py` | scenen, hel eller sammanfattad | T12–T13 |
| `llm/budget.py` | posterna, taken, trimordningen | T6–T8 |
| `llm/tur.py` | turens lägen och stoppkoder | T5, T15–T17 |
| `llm/delar.py` | limmet mellan turen och budgeten | huvudboksraden skrivs av tjänsten, aldrig av modellen |

---

## E. Det som fas 22 mätte och som ändrade specen

1. **Verktygsschemat får inte plats under sitt eget tak.**
   `23_llm_granssnitt.md` skrev *"Urvalsmaskineriet byggs alltså inte nu"* vid
   21 verktyg och 2 %. Registret bär 122 och kvoten är 19 %. Urvalet byggdes.
2. **Repot bar två olika omräkningar till tokens** — 4 byte/token i specen och
   3,0 tecken/token i koden — och de är inte samma storhet för svensk text.
3. **`antal` bär två storheter** i verktygsregistret.
4. **Bara 19 av 207 svar kan kontrolleras utan råvaran.** Följden är en regel:
   kapning sker bara där råvaran finns kvar.
5. **Alla missade anrop är skrivande.** Fritextrangordningen kan inte hitta dem;
   planen deklarerar dem.
6. **Kön har inget lager i loopen.** Fyra övergångar och två stoppkoder är
   därför obyggda, och det står som skuld med skäl i stället för som en tyst
   lucka.

---

## F. Vad protokollet INTE bevisar

* **Ingen språkmodell är anropad.** Turerna kommer ur en attrapp med manus.
  Talen mäter mekanismerna, inte en modells beteende.
* **Ingen brygga och ingen VC har svarat.** De kodgenererande verktygens
  svarsform kommer ur deras **deklarerade** `returns`, inte ur en körning.
* **Tokentalen är en omräkning ur byte.** Ingen leverantörs tokenisering har
  räknat vår text. Båda antagandena är märkta.
* **Ingen lång körning finns.** Den långa ögonrapporten är byggd med ögats egen
  skrivare. Att `EDGE` och `MINDIST` växer som antaget är antaget.
* **Scensammanfattaren är mätt på konstruerade scener.** Ingen bankscen är över
  gränsen — den största är 9 komponenter.
* **Urvalsträffen mäter regeln, inte efterfrågan.** De 95 turerna är
  efterlevnadsbankens, byggda för att pröva grindarna.
* **`KO`-läget är oprövat**, och `AVBRUTEN`, `BRYGGA_NERE`, `TAK_TOKEN` och
  `VANTAR_GODKANNANDE` har ingen kodväg som kan sätta dem.

## G. Körning

```
python3 tests/protocol/kor_fas22_modellagret.py --json /tmp/fas22.json
```

Kräver varken VC, OpenPLC, brygga eller nätverk. Kör på en ren maskin.
