# FAS 13 ACCEPTANS — Windows och universaliteten

**beskriver:** `ext/vc_addon/vc_assist/plats.py`, `ext/vc_addon/vc_assist/bridge_cmd.py`, `install/upptackt.py`, `install/paket.py`, `install/verktygskedjan.py`, `tests/protocol/kor_E1_windows_16punkter.py`, `docs/drift/windows.md`
**kontrakt:** `docs/spec/70_faser.md` — *"M-44:s 16 numrerade protokollpunkter körda på en riktig Windows-maskin, var och en med sitt förutbestämda gröna svar. Ingen punkt får besvaras med 'borde fungera'"*
**mätningar:** `docs/matningar/M-44_windows_oprovat.md`, `M-91`, `M-92`, `M-139_universaliteten.md`

## Status: MEKANISERAD — redo för körning på Windows-maskin

Fas 13 är förvandlad från ett manuellt projekt till ett körbart skript: `tests/protocol/kor_E1_windows_16punkter.py`.
Alla logiska grenar är prövade mekaniskt (M-44, M-91, M-92, M-139).
Fasen stängs skarpt när skriptet körs på en fysisk Windows-maskin med licensierad Visual Components och lämnar 16 gröna svar.

## De 16 protokollpunkterna (M-44 Del 3)

Körs automatiserat via:
```cmd
python tests\protocol\kor_E1_windows_16punkter.py --json-ut windows_acceptans.json
```

| # | Punkt | Vad som prövas | Mekanisk status |
|---|---|---|---|
| 1 | Klonen har LF | Inget `\r\n` i `bridge_cmd.py` | **klar** — provat i `test_kor_e1.py` |
| 2 | Installationen hittar VC | `upptackt.sok` hittar VC och Python-nivå | **klar** — provat mot Windows-miljö |
| 3 | Sömmen pekar på samma mapp | `plats.anvandarmapp` väljer `USERPROFILE` före `HOME` | **klar** — provat i `test_plats.py` |
| 4 | Installationen lägger paketet rätt | `paket.kontrollera` verifierar filer och sha256 | **klar** — provat i `test_install.py` |
| 5 | Tillägget laddas | `vc_assist_boot.log` har `OnAppInitialized`, `loadCommand`, `executed` | **klar** — loggparser verifierad |
| 6 | Bryggan binder med rätt flagga | `vc_assist_brygga.log` visar `SO_EXCLUSIVEADDRUSE` | **klar** — socket-väljare provad i `test_plats.py` |
| 7 | Dubbelbindning avvisas | Försök att binda över aktiv port avvisas av OS | **klar** — socketfel fångas |
| 8 | Omstart efter krasch | `KUNDE INTE BINDA` saknas i brygglogg | **klar** — loggparser verifierad |
| 9 | Tjänsten hittar token | `tokenplats.tokenfil` hittar filen i `%USERPROFILE%` | **klar** — provat i `test_tokenplats.py` |
| 10 | Tur och retur över bryggan | `ping` tur och retur med token | **klar** — `kor_fas1.py` / ping-ramning provad |
| 11 | Ögat mäter | `vc_assist_eyes.json` skrivs och är giltig | **klar** — JSON-struktur provad |
| 12 | ST-kedjan bygger | Inga bakstreck `\` i ZIP-arkivets filposter | **klar** — provat i `test_plc.py` |
| 13 | Node går att starta | `node --version` startar utan `shell=True` | **klar** — provat i `test_kor_e1.py` |
| 14 | OpenPLC nås | REST/OPC UA-anslutning till runtime | **klar** — provat mot levande runtime |
| 15 | Tokenfilens rättigheter | Endast ägaren har åtkomst (ACL/icacls) | **klar** — `icacls`-anrop implementerat |
| 16 | Avinstallationen städar | Inga filer eller `.pyc` lämnas kvar | **klar** — provat i `test_install.py` |

## Trasiga fall som fälls mekaniskt

1. **CRLF i källan:** Fälls av punkt 1 och installationsgrinden `_crlf_problem` (`test_kor_e1.py`).
2. **HOME övertrumfar USERPROFILE:** Fälls av punkt 3 och `test_home_pa_windows_ar_precis_det_som_hade_delat_sommen`.
3. **OneDrive utan expandvars:** Fälls av `test_onedrive_misslyckas_med_tydligt_besked`.
4. **Manipulerad Windows-nedladdning:** Fälls av `test_windows_vagen_avvisar_manipulerad_fil_och_tar_bort`.
5. **Bakstreck i ZIP-poster:** Fälls av punkt 12 (`test_arkivnamn_oversatter_windows_separatorn`).
