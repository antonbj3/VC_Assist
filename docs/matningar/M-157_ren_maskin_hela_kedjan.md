# M-157 — Ren maskin: hela installationskedjan från klon till prov i ren container

**Datum:** 2026-09-05
**Rigg:** Ren `docker run --rm ubuntu:24.04`-container utan förinstallerade paket; CPython 3.12.3.
**Prövar:** E8 / Fas 10 — Hela kedjan steg för steg enligt README på en ren maskin utan förkunskap.

## Metod och körning

En tom `ubuntu:24.04`-container startades. Inga miljövariabler, inga förinstallerade moduler eller cachekataloger fanns.
Stegen från README kördes i exakt den ordning en ny användare möter dem:

1. **Systemberoenden:**
   `apt-get update && apt-get install -y python3 git`
   Verifierat att `python3` (3.12.3 minimal) har samtliga stdlib-moduler som krävs: `json`, `hashlib`, `urllib.request`, `tarfile`, `zipfile`, `sqlite3`, `lzma`, `ctypes`, `ssl`, `zlib`, `bz2`, `xml.etree.ElementTree`.

2. **Kloning:**
   `git clone <repo> VC_Assist && cd VC_Assist`
   Lyckades utan anmärkning.

3. **Upptäcktsfas (`sok`):**
   `python3 install/installera.py sok`
   På en maskin utan förinstallerad Visual Components hittas noll mappar. Skriptet returnerar **exitkod 2** (inte 0 eller tyst fel) och skriver ut exakt hur användaren anger målet manuellt:
   `python3 install/installera.py installera --mal '<Documents>/Visual Components/<version>/My Commands/Python 2/vc_assist'`

4. **Installation med målangivelse:**
   `python3 install/installera.py installera --mal '/tmp/test_vc/Visual Components/4.10/My Commands/Python 2/vc_assist'`
   Resultat:
   ```
   nya: 11   uppdaterade: 0   oforandrade: 0   borttagna: 0
   verifierat pa plats: 11 filer parsar och kompilerar
   slutkod: 0
   ```
   Alla 11 tilläggsfiler kopierades, granskades på disk och klarade syntax- och importkontrollen.

5. **Verifiering på plats:**
   `python3 install/installera.py verifiera --mal '/tmp/test_vc/Visual Components/4.10/My Commands/Python 2/vc_assist'`
   Resultat:
   ```
   installerad: 2026-09-05
   filer: 11
   samma som repots kalla: ja
   alla filer parsar och kompilerar
   ```

6. **Avinstallation och städning:**
   `python3 install/installera.py avinstallera --mal '/tmp/test_vc/Visual Components/4.10/My Commands/Python 2/vc_assist'`
   Resultat: Samtliga 11 filer och manifest togs bort, och alla tomma överordnade mappar upp till målets bas raderades. Mappträdet återställdes fullständigt.

7. **Verktygskedjans manifest:**
   `python3 install/verktygskedjan.py --lista`
   Visar alla sju plattformsartefakter med fastspikad sha256 samt OpenPLC:s låsta digest.

## Fynd och rättelser

1. **README saknade verktygskedjan:**
   README beskrev tilläggsinstallationen men utelämnade hur användaren hämtar STruC++ och OpenPLC. Åtgärdat i E12: ett eget delavsnitt för `install/verktygskedjan.py` lades till.
2. **Node.js-beroende för STruC++:**
   STruC++:s AST-steg (`npm ci`) kräver Node.js ≥ 18 och npm. Detta saknades i "Vad det kräver" och lades till i E12.
3. **Idempotens:**
   Körd en andra gång på samma mål rapporterar installationen `nya: 0, uppdaterade: 0, oforandrade: 11`. Inga filer skrivs om i onödan.

## LIMITS

* **Visual Components kördes inte:** En ren Ubuntu-container kan inte köra Visual Components utan ett Wine-prefix och licensserver.
* **Verktygskedjans fulla nedladdning (30 MB) kördes med `--lista`:** Full hämtning av binärerna prövas i M-56 och testas lokalt; i containern kördes endast manifest- och sha256-kontrollen för att spara disk och nätkvot.
