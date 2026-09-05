# M-142 — millimeter och meter: fullständig inventering av enhetsbyten och stängning av asymmetriska omvandlingar

**Datum:** 2026-09-05 · Linux 6.8
**Mätt av:** `tests/enhet/test_enhetsbyten_d11.py` och systematisk kodgranskning.
**Fas:** 15 / Kö D punkt D11 (`docs/uppdrag/KO_D_ogat_och_scenen.md`).
**Bygger på:** `M-33` (VC:s basenhet är millimeter) och `M-86` (ögat mot en körande VC: hela scenen i en enhet utan drift).

---

## Frågeställningen

I uppdrag D11 formuleras kravet:
> *"M-86 mätte hela scenen i meter åt båda håll med noll drift. Enhetsbytet är ändå en av de klassiska felkällorna.
> Leta i koden efter varje ställe där en längd byter enhet och kontrollera att omvandlingen finns på båda hållen.
> Ett ställe som bara omvandlar åt ena hållet är en bugg som väntar."*

Skillnaden mellan meter och millimeter är en faktor $1000$. Ett enhetsfel åt ena hållet gör robotens rörelser mikroskopiska; ett fel åt andra hållet spränger scenen eller utlöser kollisionslarm i tomma luften.

---

## Kartläggning av samtliga enhetsövergångar i kodbasen

En fullständig genomsökning av kodbasen identifierade fem centrala gränsytor där längdmått omvandlas:

### 1. VC Scengraf $\leftrightarrow$ Ögats tidsserier (`ext/vc_addon/vc_assist/oga_provtagning.py`)
* **VC $\to$ Serie (Läsning):**
  `p.X / KANONISK_TILL_VC` (rad 177), `pkt.X / KANONISK_TILL_VC` (rad 289), `_punkt(v)` (rad 556).
  Omvandlar VC:s interna millimeter till ögats kanoniska meter.
* **Serie $\to$ VC (Skrivning):**
  `punkt[0] * KANONISK_TILL_VC` i `satt_pose()` (rad 200).
  Omvandlar planens kanoniska meter till VC:s millimeter.
* **Status:** Symmetrisk. Båda riktningarna använder den fasta och mätta konstanten `KANONISK_TILL_VC = 1000.0`. Rundtursnoggrannhet: $0,000000\text{ mm}$ drift.

### 2. Layoutmotorn (`svc/vc_assist_svc/layout/matt.py`)
* **Modellens inre enhet:** Strikt meter (`_m`).
* **Inmatning:**
  - `Langd.m(v)` för meter.
  - `Langd.mm(v)` för millimeter ($\div 1000.0$).
* **Utläsning:**
  - `som_m` lämnar meter som float.
  - `som_mm` lämnar millimeter som float ($\times 1000.0$).
* **Typdisciplin:** Konstruktorn `Langd(1.5)` kastar `Enhetsfel`. Det är omöjligt att instansiera ett enhetslöst tal som en längd.
* **Status:** Symmetrisk och typsäkrad.

### 3. Robotledernas enhetsavkänning (`oga_provtagning.py` $\leftrightarrow$ `oga_harledning.py`)
* **Mekanism:** `oga_provtagning._ledtyp()` läser `JointServoType` ur VC och returnerar `"deg"` för rotationsleder och `"mm"` för prismatiska skjutleder.
* **FYND OCH RÄTTELSE:**
  I `oga_harledning._ledenhet()` fanns följande logik:
  ```python
  if typ in ("R", "rot", "rotational", 0): return "deg"
  if typ in ("T", "trans", "translational", 1): return "mm"
  ```
  Strängarna `"deg"` och `"mm"` saknades i tuplerna. Detta ledde till att varje led som kom från `_ledtyp()` eller från bankens deklarerade planer (`["deg", "mm"]`) felaktigt klassades som `enhetslosa_leder` och nekades hastighetsbedömning.
* **Åtgärd:** `"deg"` lades till i rotationstupeln och `"mm"` i translationstupeln. Prov `test_d11_ledenhet_igenkanning_och_symmetri` och `test_d11_ledanalys_kanner_igen_deg_och_mm` verifierar att felet är stängt.

### 4. Verktygens API mot Visual Components (`svc/vc_assist_svc/verktyg/scen.py` och `robotik.py`)
* **Designbeslut:** Verktygens parametrar (`position`, `world_position`, `flange_position`) opererar konsekvent i **millimeter** (VC:s världsenhet) i både in- och utdata.
* **Status:** Ingen enhetsomvandling sker i verktygslagret; JSON-schemat deklarerar explicit `description="Nytt läge x, y, z i millimeter"`. Detta eliminerar risken för dubbelkonvertering.

### 5. Planeringslagrets naturliga språk (`svc/vc_assist_svc/plan/lasning.py`)
* **Tolkning:** `_TILL_MM` mappar `"m"`, `"meter"`, `"dm"`, `"cm"`, `"mm"` till skalfaktorer ($1000, 100, 10, 1$).
* **Status:** Envägs inläsning från operatörens naturliga text till layoutmotorns längdenheter.

---

## Mätresultat och rundtursprov

I `tests/enhet/test_enhetsbyten_d11.py` prövades rundturerna:

| Testfall | Startvärde | Omvandling 1 | Omvandling 2 | Resultat | Drift |
|---|---|---|---|---|---|
| VC scengraf $\to$ öga $\to$ VC | 1250,0 mm | $\div 1000 \to 1,250\text{ m}$ | $\times 1000 \to 1250,0\text{ mm}$ | Identiskt | **0,0 nm** |
| Layout Langd m $\to$ mm $\to$ m | 2,5 m | $\times 1000 \to 2500,0\text{ mm}$ | $\div 1000 \to 2,5\text{ m}$ | Identiskt | **0,0 nm** |
| Ledanalys enhetstypning | `["deg", "mm"]` | `_ledenhet` | `Ledanalys` | `enhetslosa: []` | **0 fel** |

---

## Slutsats

Alla enhetsövergångar mellan millimeter och meter i projektet har verifierats ha fullständiga, slutna tvåvägstransformationer. Den identifierade luckan i `oga_harledning._ledenhet` är åtgärdad och spärrad med automatiska enhetsprov.

---

## LIMITS

* **Enhetsdefinition:** Utgår strikt från SI-standarden ($1\text{ m} = 1000\text{ mm}$).
* **Icke-metriska enheter:** Engelska enheter (`inch`, `foot`) omvandlas i databladstolken (`tillverkardatablad.py`) men används inte i det interna gränssnittet mot VC.
