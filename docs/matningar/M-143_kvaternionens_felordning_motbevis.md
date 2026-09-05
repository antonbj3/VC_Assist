# M-143 — kvaternionens felordning: trasig fixtur mot ögat och FAL-001 bevisar att (q.Y, q.Z, q.W, q.X) är strikt nödvändig

**Datum:** 2026-09-05 · Linux 6.8
**Mätt av:** `tests/motbevis/test_kvaternion_felordning_motbevis.py`.
**Fas:** 15 / Kö D punkt D12 (`docs/uppdrag/KO_D_ogat_och_scenen.md`).
**Bygger på:** `M-11` (kvaternionens ordning och världsmatrisens eftersläpning) och `M-72` (kvaternionens ordning avgjord på alla tre axlarna).

---

## Frågeställningen

I uppdrag D12 formuleras kravet:
> *"Kvaternionen. Skalär först, (x,y,z,w) = (q.Y,q.Z,q.W,q.X) — mätt i M-72.
> Kontrollera varje ställe i koden som rör rotationer mot den regeln, och
> skriv en trasig fixtur som fäller den vanliga felordningen."*

Visual Components `vcMatrix.getQuaternion()` returnerar en `vcVector` där `q.X` är skalären $w = \cos(\theta/2)$ och vektordelen $(x, y, z)$ ligger i $(q.Y, q.Z, q.W)$. Den naiva tolkningen — att läsa fälten i namnordning som $(x, y, z, w) = (q.X, q.Y, q.Z, q.W)$ — är en av de vanligaste fällorna för både mänskliga programmerare och språkmodeller.

Här kontrolleras samtliga rotationsställen i koden mot regeln, och en trasig fixtur visar att felordningen ofelbart fälls av både ögat och kodfallsgrinden.

---

## Kodgranskning: alla rotationspunkter i repot

1. **Ögats provtagare (`ext/vc_addon/vc_assist/oga_provtagning.py`):**
   - Funktion `kvat_fran_vc(vcvektor)` (rad 70):
     `return [vcvektor.Y, vcvektor.Z, vcvektor.W, vcvektor.X]`
   - Både `pose()` (rad 180) och `poser_alla()` (rad 292) anropar `kvat_fran_vc`.
   - Resultatet lagras i tidsserien som kanonisk kvaternion $[x, y, z, w]$ med skalären sist.
2. **Ögats härledning och analys (`oga_harledning.py` och `oga_analys.py`):**
   - `q_konjugat(q)`: `(-x, -y, -z, w)`
   - `q_mult(a, b)`: Hamiltonprodukt med skalären $w$ på index 3.
   - `q_rotera(q, v)`: Vektorrotation via Rodrigues formel med $w$ som skalär.
   - `q_vinkel_deg(q)`: $2 \arccos(|q[3]|) \cdot \frac{180}{\pi}$.
   - Samtliga fyra funktioner förutsätter kanoniskt format $(x, y, z, w)$.
3. **Statisk kodfallsgrind (`svc/vc_assist_svc/harness/kodfallor.py`):**
   - Grind `FAL-001` (`kvaternion_i_namnordning`):
     Inspekterar AST för genererad Python-kod. Fäller varje tilldelning eller tupeluppackning där `q.X` knyts till variabeln `x` eller där fälten plockas i ordningen $(X, Y, Z, W)$.

---

## Den trasiga fixturen och mätresultat

I `tests/motbevis/test_kvaternion_felordning_motbevis.py` konstruerades motbevisen:

### 1. Ren rotation och vinkelfel
För en stillastående detalj ($\theta = 0^\circ$) ger VC vektorn `(1.0, 0.0, 0.0, 0.0)`.
- **Korrekt avbildning (`kvat_fran_vc`):** $[0.0, 0.0, 0.0, 1.0] \implies \theta = 0,000^\circ$.
- **Felordning (namnordning):** $[1.0, 0.0, 0.0, 0.0] \implies w = 0 \implies \theta = 2\arccos(0) = \mathbf{180,000^\circ}$.
En helt orörd detalj uppmäts alltså som att den slagit runt ett halvt varv i rymden.

### 2. Ögats reaktion under roterande robottransport
En robot bär en detalj och roterar verktyget $90^\circ$ kring Z under förflyttningen, med detaljen hållen vid en fast offset ($100\text{ mm}$ från TCP):
- **Korrekt ordning:** Detaljens offset roterar med verktyget. I verktygets lokala koordinatsystem är detaljen helt stillastående ($0\text{ mm}$ relativ förskjutning, $< 5\text{ mm}$ tröskel).
  $\implies$ **`PASS`** (`allt inom marginal`).
- **Trasig fixtur (felordning):** Eftersom kvaternionen tolkas fel roteras inte offsetvektorn korrekt; detaljen uppmäts glida $141\text{ mm}$ i verktygets ram. Ögat konstaterar att ett stabilt grepp aldrig etablerades.
  $\implies$ **`FAIL`** (`grepp: hederlighetsgrind fälld: greppet bildades aldrig`).

### 3. Statisk fällning av felordning (FAL-001)
Fem typiska felaktiga mönster prövades mot `kvaternion_i_namnordning`:
1. `x, y, z, w = q.X, q.Y, q.Z, q.W` $\implies$ **AVVISAD**
2. `x = q.X` $\implies$ **AVVISAD**
3. `w = q.W` $\implies$ **AVVISAD**
4. `vridning = [q.X, q.Y, q.Z, q.W]` $\implies$ **AVVISAD**
5. `x = nod.WorldPositionMatrix.getQuaternion().X` $\implies$ **AVVISAD**

Samtliga fem fälldes med hänvisning till M-11 och regeln om skalär först. Korrekt kod (`w = q.X`, `x, y, z = q.Y, q.Z, q.W`) släpptes igenom med 0 anmärkningar.

---

## Slutsats

Regeln $(x, y, z, w) = (q.Y, q.Z, q.W, q.X)$ är inte en godtycklig konvention utan en matematisk nödvändighet för att ögat ska fungera mot Visual Components. Den trasiga fixturen bevisar att den vanliga felordningen ofelbart fälls i både dynamisk analys och statisk förgranskning.

---

## LIMITS

* **Representation:** Gäller relationen mellan Visual Components interna C#-klass `vcVector` och ögats kanoniska representation.
* **Axlar:** Verifierat på alla tre axlarna X, Y, Z (M-72).
