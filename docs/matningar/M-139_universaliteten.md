# M-139 — Universaliteten mätt: kombinationstabell över OS, Python, VC och Wine

**Datum:** 2026-09-05
**Rigg:** Samlade mätningar i repot (M-01, M-02, M-44, M-90, M-91, M-92, M-109, M-112, M-136); Linux x86-64, Windows 10 kupa, Wine 11.16, Docker CPython 2.7–3.13.
**Prövar:** Systemets universalitet över alla kombinationer av operativsystem, Python-version, VC-version och Wine. Varje cell klassas strikt som **mätt**, **oprövat** eller **går inte**. Inget "borde fungera".

## Bakgrund

Operatörens krav är att tillägget ska fungera *"med och utan Wine, på Windows och Linux — universellt"*. Fram till denna mätning har systemet byggts och provats primärt under Wine på Linux, medan Windows-vägen har analyserats logiskt (M-44) och Linux-distros och Python-versioner svepts (M-109).

Denna mätning sammanställer den kompletta matrisen över vad som faktiskt är bevisat, vad som ännu inte körts på en fysisk maskin, och vad som av arkitektoniska skäl är omöjligt.

## Kombinationstabellen

| Operativsystem | Python (Tjänst/Värd) | Python (VC Addon) | VC-version | Körmiljö | Status | Grund / Mätreferens |
|---|---|---|---|---|---|---|
| **Linux (glibc x64)** | 3.10–3.13 | 2.7 (Stackless) | VC 4.10 | Wine 11.16 | **mätt** | M-01, M-03, M-06, M-39, M-90, M-112 |
| **Linux (glibc x64)** | 3.9 | 2.7 (Stackless) | VC 4.10 | Wine 11.16 | **mätt** | M-109: installation lyckas, AST-verifiering saknar `sys.stdlib_module_names` |
| **Linux (glibc x64)** | ≤ 3.8 | — | — | — | **går inte** | End-of-life; stöds ej av underliggande beroenden |
| **Linux (glibc x64)** | 3.10–3.13 | 3.x | VC 5.0 | Wine | **oprövat** | Saknar VC 5.0 och licens; installationskroken märker `OPROVAD` |
| **Linux (glibc x64)** | 3.10–3.13 | — | VC ≤ 3.x | — | **går inte** | Saknar modernt API och add-on-arkitektur |
| **Linux (glibc x64)** | — | — | VC (nativ) | Utan Wine | **går inte** | Visual Components är en ren Windows-binär (`.exe`) |
| **Linux (musl / Alpine)** | 3.9–3.13 | 2.7 (test) | — | Utan VC | **mätt** | M-109: installation och verktygskedja fungerar |
| **Windows 10/11 x64** | 3.10–3.13 | 2.7 (Stackless) | VC 4.10 | Nativ | **oprövat** | M-44 & E1 har 16 mekaniserade provpunkter; väntar på maskinkörning |
| **Windows 10/11 x64** | 3.9 | 2.7 (Stackless) | VC 4.10 | Nativ | **oprövat** | M-44 protokollpunkter klara; ej körd mot levande VC |
| **Windows 10/11 x64** | 3.10–3.13 | 3.x | VC 5.0 | Nativ | **oprövat** | Saknar VC 5.0 installation |
| **Windows 10/11 x64** | 3.10–3.13 | 2.7 | VC 4.10 | OneDrive | **mätt** | M-91 (registerkupa) & E2 (OneDrive-sökning med expandvars & trasig fixtur) |
| **Windows ARM64** | 3.10–3.13 | — | VC 4.10 | Nativ | **går inte** | M-56 & install/verktygskedjan: utgivarens paket för ARM64 är x64-binär |
| **macOS (Darwin)** | 3.10–3.13 | — | VC | Utan Wine | **går inte** | Ingen VC-binär finns för macOS |

## Analys per axel

### 1. Visual Components-versioner
* **VC 4.10:** Den enda versionen med fullständig mätning i repot. Körs under Wine 11.16 med Stackless Python 2.7.1. Sökvägen `My Commands/Python 2/vc_assist/` är bevisad i M-01.
* **VC 5.0:** Oprövat. Koden har förberetts med stöd för `Python 3`-katalog och universella radslut, men ingen körning har skett mot VC 5.0.
* **VC ≤ 3.x:** Går inte. Saknar de API-strukturer och Python-krokar som VC Assist bygger på.

### 2. Python-versioner
* **CPython 3.10–3.13:** Mätt och verifierat fullt ut på Linux (M-90, M-109). Alla enhetsprov, verktyg och AST-analyser fungerar.
* **CPython 3.9:** Mätt (M-109). Installationen och körningen fungerar, men `sys.stdlib_module_names` saknas (tillkom i 3.10), varför enhetskontroller som kräver standardbiblioteksinspektion kräver 3.10+.
* **CPython ≤ 3.8:** Går inte. Versionerna är officiellt föråldrade och stöds ej. Tidigare påståenden i README om 3.7–3.8 var oprövade och har strukits (E5).
* **Tilläggets Python (VC-sidan):** Både 2.7 och 3.x stöds i `ext/`. Samtliga 11 filer i `ext/vc_addon/vc_assist` har kompilerats skarpt i CPython 2.7.18 och 3.13.11. Dubbelkompatibiliteten kontrolleras nu mekaniskt vid varje installation i `install/paket.py`.

### 3. Operativsystem och filsystem
* **Linux + Wine:** Den primära test- och mätmiljön. Fullständigt mätt i headless-läge.
* **Nativ Windows:** Oprövad för levande VC. Registerläsning (`User Shell Folders`) och OneDrive-expansion med `ntpath.expandvars` är verifierade mot attrappträd och diskkupa (M-91, E2). De 16 acceptanspunkterna är mekaniserade i `tests/protocol/kor_E1_windows_16punkter.py`.
* **Windows ARM64:** Går inte med nuvarande verktygskedja. Utgivarens paket `strucpp-win32-arm64.zip` innehåller felaktigt en PE32+ x86-64-binär (M-56).

## LIMITS

* **Ingen mätning har skett på en körande fysisk Windows-maskin.** Alla Windows-grenar är prövade via injicerade miljöer, statiska registerkupor eller attrappträd på Linux.
* **VC 5.0 förblir oprövat.** Skolans licensserver tillhandahåller endast licens för VC 4.10.
* **Headless-begränsning:** Samtliga mätningar med körande VC har skett i virtuell skärmbuffert (`DISPLAY=:99`). Grafisk rendering och UI-frysningar vid tung interaktion är inte mätta.
