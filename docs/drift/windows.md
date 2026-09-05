# Drift: Windows

Instruktioner och driftsrutiner för Visual Components Assist på Windows (E14, M-44).

## 1. Krav och förutsättningar

* **Operativsystem:** Windows 10 eller 11 x64 (ej ARM64, se M-56).
* **Visual Components:** 4.10 Premium (VC 5.0 stöds i installationsstrukturen men är oprövat).
* **Python:** CPython 3.10–3.13 installerat och tillgängligt på `PATH`.
* **Node.js:** Node.js ≥ 18 och `npm` på `PATH` för STruC++ PLC-kompilatorn.
* **OpenPLC:** OpenPLC Runtime v4 körs i Docker Desktop eller WSL2 (`http://127.0.0.1:8080`).

## 2. Installation och verifiering

```cmd
git clone <repo> VC_Assist
cd VC_Assist
python install\installera.py sok
python install\installera.py installera
python install\installera.py verifiera
```

Om dokumentmappen är omdirigerad till OneDrive hittar installeraren sökvägen via
Windows-registret (`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders\Personal`).

## 3. Acceptansprovkörning (Fas 13)

Kör de 16 mekaniserade acceptanspunkterna utan manuell tolkning:

```cmd
python tests\protocol\kor_E1_windows_16punkter.py --json-ut windows_resultat.json
```

Varje punkt rapporteras som `GRON`, `ROD` eller `HOPPAD` med tydligt skäl.

## 4. Säkerhet och processhantering

* **Portbindning:** Bryggan lyssnar uteslutande på `127.0.0.1:8901` (`SO_EXCLUSIVEADDRUSE`).
* **Tokenfil:** Skrivs till `%USERPROFILE%\vc_assist_token` vid start med 24-byte slumpmässig kryptografisk token.
  Åtkomsten skyddas av användarkontots ACL:er och loopback-begränsningen.
* **Stoppa låst brygga/VC:**
  Om port 8901 är upptagen eller VC hängt sig, avsluta processen via Aktivitetshanteraren eller i kommandotolken:
  ```cmd
  taskkill /F /IM VisualComponents.Engine.exe
  ```
