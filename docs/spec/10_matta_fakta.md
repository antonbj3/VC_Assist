# Mätta fakta

Regel: varje rad här är **mätt** i den här maskinen eller läst i en primärkälla.
Antaganden står under egen rubrik och är märkta.

## Visual Components 4.10 Premium

| Fakta | Värde | Härkomst |
|---|---|---|
| Python-API:ts storlek | 204 typer, 966 metoder, 1159 egenskaper, 175 events | `Python 2/Auto Complete/api.xml`, parsad till `docs/referens/vc_api/vc_python_api.json` |
| Inbäddad Python | 2.7 (`python27.dll`) | `Python 2/python27.dll` |
| Tilläggsmekanism | mapp med `__init__.py` som definierar `OnAppInitialized()`; VC anropar den vid uppstart | `Python 2/Commands/LayoutTools/__init__.py` |
| Var tillägg installeras | `%MYDOCUMENTS%\%COMPANY%\%VERSION_2%\My Commands` | `VisualComponents.Engine.exe.config`, nyckel `MyCommandsFolder` |
| Bildfångst | `app.executeFrameGrab(uri)` sparar bildruta till fil; format/storlek via `beginFrameGrab()` | api.xml |
| Bild→scen | `vcCamera.getRay()` ger stråle ur bildkoordinat | api.xml |
| Poser | `vcNode.PositionMatrix`, `WorldPositionMatrix`, `InverseWorldPositionMatrix`, `BoundCenter`, `BoundDiagonal` | api.xml |
| Kollision | `vcCollisionDetector`: minsta avstånd, båda närmaste punkter, träffad nod OCH feature, bbox-test, `Tolerance` | api.xml |
| Robot | `vcRobotController` (baser, verktyg, kinematik, hastighets/accelerationsgränser), `vcServoController` (leder), `vcPythonKinematics` | api.xml |
| Simulering | `SimTime`, `IsRunning`, `SimSpeed`, `run/halt/autoHalt/reset/update`, `setFastScheduling`, `newCollisionDetector`, `newVolumeDetector` | api.xml |
| Statistik | ankomna, avgångna, aktuella, medel-, min-, maxtid, `States`, `SystemStates` | api.xml |
| Komposition | `vcSimInterface`: `canConnect()`, `connect()`, avstånds- och vinkeltolerans | api.xml |
| Renderare | D3D9 (`VisualComponents.D3D9Renderer.dll`), minst Pixel Shader 2.0 | binäranalys |
| 3D-vyn i WPF | `System.Windows.Interop.D3DImage`, delad D3D9Ex-yta (ej HwndHost) | `UX.Viewport.dll` |
| USD | **finns inte**, varken läsare eller skrivare | strängsökning i samtliga binärer |
| FBX | endast export | `VisualComponents.FBX.dll` |
| OPC UA-roll | **klient**, aldrig server | `VisualComponents.Connectivity.OpcUA.xml`, `IOpcUAServer` = "a server connection" |
| Connectivity i Python | **finns inte** — endast .NET | sökning i api.xml |
| Connectivity-plugins | 17 st: OPC UA, Siemens S7, Beckhoff ADS, SIMIT, WinMOD, ABB, Fanuc, Yaskawa, Kawasaki, UR, Stäubli, Doosan, Omron m.fl. | filnamn i installationen |
| Egen protokoll-plugin | möjlig: `IPluginHandler`, `IServerHandler`, `IVariableGroupHandler`, `IValueTypeConverter` | `Connectivity.Core.xml` |
| Modbus | **saknas** (endast inuti Doosans robotbibliotek) | strängsökning i samtliga DLL:er |

## Wine-miljön

| Fakta | Värde | Härkomst |
|---|---|---|
| Wine som krävs | **≥ 11.15**. Under det saknar bcrypt `HashBlockLength` och licensmotorn dör med 677005 DLL_LOADING_ERROR | jämförelse av `dlls/bcrypt/bcrypt_main.c` mellan 11.0 och 11.15 |
| Installerad | wine-devel 11.16 i `/opt/wine-devel` | apt |
| D3D9-väg | **DXVK krävs**. wined3d nekar `CheckDeviceFormat(X8R8G8B8, RENDERTARGET\|DYNAMIC, SURFACE)` med 0x8876086A och ger delad yta med handle=0 | eget P/Invoke-testprogram, båda vägarna |
| Shader-bibliotek | `d3dx9_43` och `d3dcompiler_43` **måste** vara native. Wines egna ger svart 3D-vy och evig omritningsloop | `WINEDEBUG=+loaddll` visade builtin trots app-lokala filer; 66 → 0 renderingsfel efter fix |

## OpenPLC

| Fakta | Värde | Härkomst |
|---|---|---|
| v4 OPC UA-server | **ja**, `opc.tcp://<ip>:4840/openplc/opcua`, None till Basic256Sha256, roller viewer/operator/engineer, per nod läs/skriv, cykeltid 100 ms | Autonomy Logics egen dokumentation, verifierad direkt |
| v4 inladdning | REST med JWT: `/api/login`, `/api/upload-file`, `/api/compilation-status`, `/api/start-plc` | samma |
| v3 | ingen OPC UA. Modbus TCP 502 | källkod och forumtråd |
| ST-kompilator | `STruC++`, fristående CLI med Linux-binärer | Autonomy Logic, GitHub |

## Antaganden (ej mätta)

- Att ett Python-kommando i VC kan öppna en socket och köra en tråd. **Sonden som skulle visa detta fällde VC:s uppstart och är inte omkörd.**
- Provtagningstakten som går att nå per simuleringssteg.
- Om ledhastigheter finns direkt eller måste deriveras ur lägen.
- Exakt layout på `program.zip` som OpenPLC:s editor producerar.
