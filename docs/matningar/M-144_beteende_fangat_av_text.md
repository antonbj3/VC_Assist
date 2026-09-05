# M-144 — de 70 skadorna som fälldes av fel skäl: lyckträff mot dolt beteendefel

**Datum:** 2026-09-05
**Rigg:** Värdmaskinen, headless. Ingen VC, ingen OpenPLC, ingen modell.
Domaren är `bank/domare.dom` via ST-tolken. Data från M-122 (70 st över 26 uppgifter)
och M-135 (86 st över 33 uppgifter).
**Prövar:** Kö C punkt C4: gå igenom de skador där `vantat_lager="beteende"` men
utfallet blev fångat av textlagret (`tolkfel:*`). Skulle beteendelagret ha fångat
dem om textlagret inte fanns? Om nej — har beteendelagret ett dolt hål?

## Resultat

### §1 Fördelningen

I M-122 fanns **70** beteendeskador som fångades av textlagret. I M-135 (efter att
banken växte till 33 uppgifter) är de **86**:

| Sort | M-122 (26 uppg.) | M-135 (33 uppg.) | Orsak till textfällning |
|---|---:|---:|---|
| `FLANKENS_Q_TILL_SIGNAL` | 68 | 82 | Instansnamn utan `.Q` är inte deklarerat som variabel |
| `JAMFORELSE_VAND` | 2 | 4 | `<>` blev `>>` (syntaxfel) p.g.a. brist i regex-lookahead |
| **Totalt** | **70** | **86** | |

### §2 De 2 (nu 4) vända jämförelserna: Inget beteendehål

Varför textlagret fällde:
Motorns regex för `JAMFORELSE_VAND`:
```python
r"(?<![:<>])(<=|>=|<|>)(?!=)"
```
har negativ lookahead mot `=` (`(?!=)`), men saknade lookahead mot `>`.
När koden bar Structured Text-olikheten `<>` (`NOT EQUAL`) matchade mönstret
tecknet `<` och ersatte det med `>`, vilket förvandlade `<>` till `>>`.
Tolkens parser stannar: `väntade ett värde men fick '>'`.

**Skulle beteendelagret ha fångat dem om de var giltig kod?**
Vi provar den semantiska motsatsen till `<>`, nämligen likhet (`=`):
* `L-07` rad 28 (`ST550_TBL_REV <> nForraVarv` → `=`): **FÄLLS** direkt av beteendelagret på `pulsgivaren_tappas_tidsovervakning@8800ms:SYS_ALARM`.
* `S-05` rad 32 (`tillstand <> 8` → `=`): **FÄLLS** direkt av beteendelagret på `maskinfel_hojd_over_matomradet@1000ms:ST200_PML_STATE`.
* `P-05` rad 40 (`ST140_TOOL_ID <> 0` → `=`): **FÄLLS** direkt av beteendelagret på `normal_drift_med_byte@1100ms:ST140_TCH_BUSY`.

**Slutsats:** För jämförelserna finns **noll hål i beteendelagret**.
Textfällningen beror uteslutande på en grovhet i mutatorns regex. Hade koden
varit syntaktiskt giltig hade beteendelagret fångat 100 % av dem.

### §3 De 68 (nu 82) flankinstanserna: Ett massivt dolt hål (nu tätat)

Varför textlagret fällde:
`FLANKENS_Q_TILL_SIGNAL` ersätter `inst.Q` med `inst`.
I Structured Text är `inst` ett funktionsblocksnamn (`R_TRIG`), inte en variabel.
Tolkens körtid hittar inte namnet i variabelkartan och kastar `Tolkfel("odeklarerat namn 'inst'")`.

**Skulle beteendelagret ha fångat den om textlagret inte fanns?**
Koden `IF trig THEN` är oexekverbar i varje IEC 61131-3-motor. Frågan "skulle
beteendelagret fånga den" kan inte besvaras på den trasiga texten själv.

Men frågan kan och ska besvaras på **mutationens verkliga avsikt** (F15: att
läsa triggvillkoret på nivå i stället för på flank). Det är precis den typgiltiga
operatorn `FLANK_TILL_NIVA` (`inst.Q` byts mot instansens `CLK`-signal) som
infördes i C0.

När den typgiltiga operatorn kördes mot bankens facit (M-122 §3 och M-131):
* **13 stycken (43 %)** fångades av beteendelagret (alla gällde material och processgivare: fotocell, PackML-tillstånd, index hemma). Där sekvensen pulsar signalen skiljer nivå och flank av sig själv.
* **17 stycken (57 %)** **ÖVERLEVDE**. Beteendelagret var helt blint!
  Var och en av dessa 17 gällde `SYS_RESET` eller handskakningens `DONE`.

Att `FLANKENS_Q_TILL_SIGNAL` fångades 100 % av textlagret dolde alltså att
beteendelagret släppte igenom **57 % av de verkliga flankfelen**. Textgrinden
fungerade som en falsk trygghet.

### §4 Uppdelning och koppling till C2

| Kategori | Antal (M-122) | Antal (M-135) | Beteendelagrets status |
|---|---:|---:|---|
| **Beteendet hade också fångat den** | **15** | **17** | Täckt: 2 (4) jämförelser + 13 processflanker |
| **Beteendet är blint här (dolt hål)** | **17** | **21** | **HÅL**: Alla 17 SYS_RESET/DONE-flanker |
| Ren syntaxkrasch utan körtidsmening | 38 | 48 | Resten av `.Q`-ersättningarna på icke-processiga signaler |

De 17 dolda hålen överlämnades till C2:
I C2 konstruerades 16 nya stimuli (V1-mönstret med hållen återställning under fel,
V4-mönstret med nystart utan kvittens, och DONE-mönstret). Resultatet i M-135:
de 17 dolda hålen minskade från 17 (21 i M-131) till **1 enda överlevare** i hela banken.

## LIMITS

* **Analysen av `FLANKENS_Q_TILL_SIGNAL` förutsätter mappingen till `FLANK_TILL_NIVA`.**
  På den bokstavliga koden `inst` finns ingen körtidssemantik i ST; tolkningen att
  "avsikten var nivåläsning" kommer ur M-115 och M-122 §3, inte ur mutationens egen sträng.
* **Jämförelserna provades med likhet (`=`).** Att vända `<>` till `=` är den
  logiska negationen; att byta till `<` eller `>` är partiska inverteringar som
  inte undersökts separat.
* **Talen baseras på bankens 26 respektive 33 referenser.** När nya uppgifter
  läggs till kan nya dolda hål uppstå om författarna inte inkluderar de
  stimuliklasser som C2 etablerat.
