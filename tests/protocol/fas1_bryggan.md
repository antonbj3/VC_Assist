# FAS 1 ACCEPTANS — bryggan

**beskriver:** `ext/vc_addon/`, `service/vc_assist/bridge_client.py`
**kontrakt:** `docs/spec/31_brygga_protokoll.md`

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
| Storhet | Enhet | Krav |
|---|---|---|
| tur och retur `ping` | ms | under 50 |
| provtagningstakt | Hz | **mäts och skrivs ned**, inget krav satt än |
| VC:s gränssnitt under last | subjektiv + fps | ingen märkbar frysning |

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

## Plattform
Linux ☐   Windows ☐
Python 2.7 ☐   Python 3.x ☐ *(kräver 5.0; syntaxkontroll räcker tills licens finns)*
