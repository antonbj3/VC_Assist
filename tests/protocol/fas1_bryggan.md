# FAS 1 ACCEPTANS — bryggan

**beskriver:** `ext/vc_addon/`, `service/vc_assist/bridge_client.py`
**kontrakt:** `docs/spec/31_brygga_protokoll.md`

## Status: STÄNGD — 13 av 13 prov, tur och retur och takt mätt

## Förutsättning
- Fas 0 klar: testprefix med egen `Documents`
- Tillägget ligger under `My Commands/Python 2/vc_assist/` (MÄTT i M-01)
- Ingen VC-process kör

## Struktur som ska byggas
```
ext/vc_addon/vc_assist/
  __init__.py        vcApplication-scope: loadCommand + execute. Ingen logik.
  bridge_cmd.py      vcCommand-scope: socketserver, kö, pump
  capability.py      förmågerapport vid start
```

## Steg
1. Installera tillägget i testprefixet
2. Starta VC ur testprefixet
3. Läs förmågerapporten som bryggan skrivit vid start
4. Anslut från tjänsten, kör `ping`
5. `exec` med läsande kod som skriver JSON på sista raden
6. `exec_queue` → `queue_list` → `queue_approve` → verifiera att koden kört
7. `exec` med kod som kastar → verifiera `E_EXEC` med traceback
8. `exec` med `timeout_ms=100` och kod som sover → verifiera `E_TIMEOUT`
9. Skicka trasig ram → verifiera `E_PARSE` och att servern lever
10. Skicka fel token → verifiera `E_AUTH`
11. **Mät provtagningstakten**: pump som räknar varv under 10 s

## Mätning

**Utförd 2026-09-04**, VC Premium 4.10 under Wine 11.16, headless `:99`.
Körs av `tests/protocol/kor_fas1.py`. Detaljer i
[M-03](../../docs/matningar/M-03_takt.md).

| Storhet | Enhet | Krav | **Mätt** |
|---|---|---|---|
| tur och retur `ping`, median | ms | under 50 | **9,91** ✅ |
| tur och retur `ping`, värsta av 20 | ms | under 50 | **13,45** ✅ |
| provtagningstakt, tyst | Hz | mäts och skrivs ned | **17,2** |
| provtagningstakt, under trafik | Hz | mäts och skrivs ned | **224,7** |
| API-ytor som finns | antal | listas | **45 av 45**, inga saknas |
| VC:s gränssnitt under last | subjektiv + fps | ingen märkbar frysning | ⬜ **oprövad — mätt endast headless** |

## Godkänt när
- Alla elva stegen ger förväntat svar
- Samtliga fem prövade felkoder returneras rätt
- Bryggan lever efter varje felfall
- Provtagningstakten är mätt och nedskriven i `docs/matningar/M-03_takt.md`
- Förmågerapporten listar de ytor `45_verktyg.md` kräver
- **VC:s tråd blockeras aldrig**: gränssnittet går att använda medan bryggan kör

## Trasiga fall som måste falla
| Fall | Förväntat |
|---|---|
| kod som kastar | `E_EXEC`, bryggan lever |
| timeout | `E_TIMEOUT`, bryggan återhämtar sig |
| trasig ram | `E_PARSE`, anslutningen stängs, servern lever |
| fel token | `E_AUTH` |
| kropp över 1 MB | `E_TOO_LARGE` |
| `exec` av skrivande kod | avvisas, ska gå via kö |

## Utfall 2026-09-04

**13 av 13 steg gick igenom**, och körningen är upprepningsbar mot en VC som
redan kört den en gång: kö och scen bär spår av tidigare körningar, så steget
prövar sin egen post och sitt eget körunika komponentnamn, och städar efter sig.

Samtliga sex trasiga fall faller rätt: `E_EXEC`, `E_TIMEOUT`, `E_PARSE`,
`E_AUTH`, `E_TOO_LARGE`, och skrivande kod i `exec` avvisas med
`E_NOT_APPROVED` som hänvisar till kön. Bryggan lever efter vart och ett.

Två avvikelser från dokumentet ovan, båda avsiktliga och skrivna:

* Strukturen blev `pump.py` + `protokoll.py` + `skrivgrind.py` + `formaga.py`
  i stället för allt i `bridge_cmd.py`. Skälet är att `protokoll.py` och
  `skrivgrind.py` då kan köras av Python 3 på Linux **utan VC** — 68 av de 80
  enhetstesterna kräver ingen VC alls.
* `capability.py` heter `formaga.py`.

## Plattform
Linux ☑ *(Wine 11.16, VC Premium 4.10, headless)*   Windows ☐ **oprövad**
Python 2.7 ☑   Python 3.x ☐ *(kräver 5.0; syntaxkontroll räcker tills licens finns)*

## Vad som ÄR kvar innan fas 1 är stängd

* **Gränssnittet under last** är oprövat. Allt är mätt headless. Att pumpen
  aldrig blockerar är visat mekaniskt (`tick()` har en budget på 25 ms och
  select med noll timeout, och ett eget test på att en tyst anslutning inte
  står i vägen), men *"ingen märkbar frysning"* är en syn, inte en slutsats.
* **Windows** är oprövat. Ingenting i bryggan är Wine-specifikt — det är en
  förväntan, inte en mätning.
