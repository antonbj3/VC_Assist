# Faser

Regel: **varje fas stängs av en mätt grind, inte av en demo.** Ingen fas
förklaras klar på en observation. Ärvt arbetssätt ur källprojektets
commit-konventioner, där mätning och motbevisning är egna leverabler.

| # | Fas | Levererar | Grind som stänger fasen |
|---|---|---|---|
| 0 | **Eget testprefix** | `~/.wine-vc-test`, klon av det fungerande, med VC + licens | VC startar i testprefixet och når licensservern. Operatörens prefix rörs aldrig av oprövad kod |
| 1 | **Bryggan** | `vc_assist/__init__.py` + `bridge.py`, TCP 8901 | Tur och retur från tjänsten: skickad kodsträng ger JSON-rad tillbaka. **Provtagningstakten mätt i Hz** |
| 2 | **Ögat** | `vc_eyes.py`, provtagning + analys + domstext | På en handbyggd bra och en handbyggd trasig cell: ögats dom matchar facit i båda. Trasig cell **måste** fällas |
| 3 | **Grinden** | `vc_eyes_gate.py` som parsar ögats utdata | Guld endast när varje cell passerar. Okänd klass ⇒ inte guld |
| 4 | **API-index** | sökbart index ur `vc_python_api.json` + AST-validering mot schemat | Modellen kan inte anropa ett verktyg eller argument som inte finns. Mätt över N försök: noll uppfunna namn |
| 5 | **Scenbygge** | katalogindex, spawn via URI, koppling via `canConnect`/`connect` | N mållayouter byggda: noll kollisioner, alla gränssnitt kopplade |
| 6 | **PLC-bandet** | OpenPLC v4, OPC UA, genererad signalkarta och deklarationer | Handskriven ST styr scenen genom OPC UA. Tur och retur mätt i ms |
| 7 | **ST för en station** | skelett + deklarationer genererade, modellen skriver sekvensen | Grind 1–5 gröna. Ögat säger PASS. **L1-guld** |
| 8 | **Komposition** | flera stationer | Guld per station, sedan guld för linan. **L2** |
| 9 | **Bänken** | scenariosamling med facit | Tre tal rapporterade: första försöket, efter k varv, fel per klass |
| 10 | **Paketering** | nedladdningsbart tillägg | Ren maskin: klona, installera, kör. Fungerar utan handpåläggning |

## Fas 0 är inte valfri

Skälet är mätt: en oprövad uppstartskrok i operatörens `My Commands` fällde
VC:s uppstart och gav ett blinkande svart fönster mitt i arbetet.
Ingen oprövad kod går in i det prefix operatören använder.

## Ordningen är inte godtycklig

Ögat före generatorn. Utan domare är resten en kodgenerator utan dom, och
då mäter vi ingenting. Källprojektets egen historia visar samma sak:
positionsproxyn fick ljuga i flera veckor tills ögat fanns att jämföra mot.
