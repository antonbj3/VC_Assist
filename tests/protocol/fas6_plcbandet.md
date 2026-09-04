# FAS 6 ACCEPTANS — PLC-bandet

**beskriver:** `svc/vc_assist_svc/plc/`
**kontrakt:** `docs/spec/60_plc.md`, grind 3 i `docs/spec/50_grindar.md`
**L1:** `tests/enhet/test_plc.py` (88 prov, ingen docker, inget nät)
**L3:** `python3 -m vc_assist_svc.plc.matning`
**mätning:** `docs/matningar/M-20_plcbandet.md`

## Fasens grind, ordagrant ur 70_faser.md

> Handskriven ST styr scenen genom OPC UA. Tur och retur mätt i ms.

**Status: HALVA GRINDEN ÄR PASSERAD.** Tur och retur är mätt: 40,0 ms median
över 3 × 120 mätningar vid 20 ms scanperiod, och svarstiden är exakt två scan
vid tre olika perioder. Men **scenen ingår inte**: Visual Components kördes av
operatören under hela arbetet och fick inte startas en andra gång. Det som är
prövat är kedjan OPC UA-klient → plugin → bildtabell → scancykel → tillbaka.
Ledet VC-plugin → scen är **oprövat**. Fasen står därför **öppen**.

## Det som är prövat, och hur

### L1 — utan docker, utan nät

```
cd ~/projects/VC_Assist && python3 -m pytest tests/enhet/test_plc.py -q
```

Täcker signalkartans regler, de genererade deklarationerna som guldfil, JSON
tur och retur, grind 3 i båda riktningarna, debugkartan, OPC UA-konfigurationen
och REST-klientens rena delar. Ingen socket öppnas.

### Trasiga fixturer — kravet ur 95_testprotokoll.md

Varje kontroll i `KONTROLLER_PLC` har en fixtur som **måste** fällas, och
`test_registret_har_en_trasig_fixtur_per_kontroll` bryter bygget om en ny
kontroll saknar sin. Tabellen:

| Kontroll | Klass | Trasig fixtur |
|---|---|---|
| `OLASLIG` | F1 | ST som inte går att läsa; grind 3 dömer då inte, den fäller |
| `SAKNAD_POU` | F3 | POU:n heter något annat än kartans station |
| `OKARTLAGD_TAGG` | F3 | `gripare AT %QX0.5` som kartan inte känner |
| `SAKNAD_DEKLARATION` | F3 | kartans `band_pa` deklareras inte |
| `AVVIKANDE_DEKLARATION` | F4 | rätt namn, fel adress / fel typ / fel skyddsmärkning |
| `ORORD_SIGNAL` | F3 | `detektor` deklarerad men aldrig läst |
| `SKRIVEN_INGANG` | F4 | koden skriver en insignal som scenen äger |
| `ODRIVEN_UTGANG` | F3 | en utgång koden bara läser |

Grind 3 räknar **inte** om grind 2. Odeklarerade namn, typfel och
dubbelskrivning är ST-lagrets kontroller, och deras dom bärs vidare oförvanskad
i `Grind3Rapport.st_rapport` (invariant I1). Det grind 3 tillför är det enda
grind 2 inte kan veta: vad scenen har för signaler.

### L3 — mot en körande runtime

Kräver docker och nät. Kör **inte** i enhetssviten.

```
docker run -d --name vcassist-openplc-v4 \
    -p 127.0.0.1:18443:8443 -p 127.0.0.1:14840:4840 \
    ghcr.io/autonomy-logic/openplc-runtime:latest
IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
     vcassist-openplc-v4)
PYTHONPATH=svc python3 -m vc_assist_svc.plc.matning \
    --bas https://127.0.0.1:18443 \
    --strucpp <uppackad strucpp-npm-katalog> \
    --runtime-include <strucpp>/runtime/include \
    --byggkatalog /tmp/bygge \
    --endpoint "opc.tcp://$IP:4840/openplc/opcua" \
    --intervall T#20ms
```

Harnessen gör hela kedjan i ordning: grind 3 på POU-texten, kompilering med
STruC++, paketering, uppladdning över REST/JWT, start med tillståndskontroll,
och därefter mätningen.

**Godkänt betyder:**

1. `granska()` säger grönt på provprogrammet — annars byggs ingenting.
2. Kompileringen ger fyra artefakter, inte två (`generated_debug.cpp` och
   `debug-map.json` ingår).
3. `/api/status` säger `RUNNING` efter start. `START:OK` räcker inte: det är
   ett kvitto på begäran, och en runtime som inte kunde ladda `.so`:n svarar
   `START:OK` och går sedan till `EMPTY`.
4. OPC UA-servern svarar på den endpoint konfigurationen angav.
5. Utsignalen följer insignalen inom 1 s i **varje** mätning; en enda miss
   fäller körningen.

**Vad som är godkänt i tal:** medianen ska ligga på två scanperioder
(± en period), och golvet — en ensam läsning — ska ligga under 5 ms. Båda
kraven kommer ur M-20:s mätning och inte ur en förhoppning.

### Trasig fixtur för L3

Ladda upp ett arkiv utan `generated_debug.cpp`. Bygget ska lyckas och starten
ska **fällas** av `starta_och_vanta()` med runtimeloggens
`undefined symbol: ..debug_array_count` i felmeddelandet. Det är den fixtur som
visade att `START:OK` inte är ett godkännande, och den ska fortsätta fälla.
`skriv_arkiv()` vägrar numera bygga ett sådant arkiv, så fixturen byggs för
hand.

## Förutsättningar som inte följer med repot

| Del | Var den kommer ifrån | Storlek |
|---|---|---|
| OpenPLC v4.2.1 | `ghcr.io/autonomy-logic/openplc-runtime:latest` | 967 MB |
| STruC++ 0.6.6 | `Autonomy-Logic/STruCpp`, `strucpp-0.6.6.tgz` (npm-paketet, inte CLI-binären) | 2,4 MB + beroenden |
| `asyncua` | endast för mätharnessen, aldrig för tjänstelagret | pip |

Att npm-paketet och inte den fristående CLI-binären används är mätt och
motiverat i M-20 punkt 5: CLI:t skriver inte debugtabellen, och utan den laddas
programmet inte.

## Vad fasen ännu inte har

* **Scenen.** VC:s OPC UA-klient är aldrig ansluten till den här servern. Utan
  det ledet är fasens egen formulering inte uppfylld.
* **Windows** (I17).
* **Fler än två signaler**, och därmed inget om hur svarstiden beter sig med en
  hel station.
* **Säkerhetslägen.** Bara anonymt och osäkrat är kört.
* **En handskriven sekvens.** Provprogrammet är ett genomsläpp med flit; en
  riktig stegkedja hör till fas 7.
