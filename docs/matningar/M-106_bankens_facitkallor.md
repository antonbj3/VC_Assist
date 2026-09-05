# M-106 — bankens facitkällor, mätta post för post

**Datum:** 2026-09-05
**Kontrakt:** `docs/spec/85_bankkontraktet.md` §2
**Grind:** `tests/protocol/kor_bankens_facit.py`
**beskriver:** `bank/uppgifter/*.json`, `bank/katalog_index.json`,
`tests/protocol/kor_bankens_facit.py`

## Frågan

Banken bar **51** uppgifter, varav **fyra** hade `facit_spar`. En uppgift utan
spårfacit går inte att döma mekaniskt idag — den är en prompt, inte en bänkpost.

Och ett spårfacit vars tal räknats fram av koden som ska dömas mäter ingenting.
`BENCH-4` stod grön i månader mot ett tautologiskt facit; talet var perfekt.

Två frågor:

1. Hur många uppgifter kan få ett spårfacit vars härkomst pekar **utanför**
   repots egen kod — och vad blir källan, post för post?
2. Går regeln att mekanisera?

## LIMITS

* **Tak: se avsnittet "Vad som INTE är mätt".** Talen nedan är räknade och
  citerade, inte körda mot en verklig anläggning. Ingen uppgift i banken är
  körd i Visual Components, så ögonfacit i `expect` är fortfarande oprövat.
* Spårfacit döms av `bank/domare.py` genom vår egen ST-tolk. Tolken är **inte**
  OpenPLC: samma facit genom OpenPLC kan ge ett annat svar, och den skillnaden
  är inte mätt (den står öppen sedan M-45).
* Paragrafnumren nedan är verifierade mot standardorganens egna
  innehållsförteckningar och mot fulltextadoptioner. **Kravtexterna** är i flera
  fall inte lästa i full text — där det gäller står det i uppgiftens eget
  `standard`-fält, ordagrant.

---

## 1. Fyndet som kom först: de fyra befintliga facit sa inte varifrån de kom

Alla fyra spårfacit i banken bar `harkomst = "M-45"`. M-45 är mätningen av
bankens **täckning** — inte källan till ett enda tal. Grinden fällde alla fyra
vid första körningen.

Och en av dem citerade fel paragraf. `L-05` sa *"håll-för-att-köra enligt
IEC 60204-1 kapitel 9.2.5"*. Det stämmer i ingen utgåva:

| Utgåva | Var håll-för-att-köra faktiskt står |
|---|---|
| IEC 60204-1:**2005** | **9.2.6.1**, under 9.2.6 "Other control functions" |
| IEC 60204-1:**2016** | **9.2.3.7 "Hold-to-run control"** |

Hela 9.2.6 slogs 2016 in i 9.2.3 med rak förskjutning: 9.2.6.1→9.2.3.7,
9.2.6.2→9.2.3.8 (tvåhandsdon), 9.2.6.3→9.2.3.9 (enabling), 9.2.6.4→9.2.3.10.
Förskjutningen är bekräftad mot standardens egen tabell F.1.

Det är precis den sortens slarv som operatörens krav siktar på: *ett bart
standardnummer säger inte vad facit lutar sig mot, och ett paragrafnummer man
minns fel är värre än inget.*

Samma genomgång flyttade tre andra påståenden:

* `S-05` hänvisade till *"övergångsmatrisen i TR88.00.02 kapitel 6.1"*. I
  ANSI/ISA-TR88.00.02-**2022** ligger tillstånden i **4.3 "Defined states"**
  (tabell 1 och 2) och övergångarna i **4.5 "State transitions and state
  commands"**; 6.1 är *"Production Mode example"*. Numreringen **1..17** och
  kommandonumren **1..9** kunde **inte** verifieras mot primärkällan — ISA:s
  publika utdrag bär bara innehållsförteckningen. Uppgiften är skriven mot den
  numreringen, och facit säger nu rakt ut att den är obekräftad.
* `H-04` lutade sig på "bankens egen konvention" för handskakningen. Det står
  kvar — men nu uttryckligen som *bankens egen*, inte som en standard, och de
  paragrafer som faktiskt bär (manuell återställning, återstartsspärr i en
  robotcell) är utsatta.
* `T-07` hade tidsgränsen 2,0 s utan att säga att den är **deklarerad**. Den är
  det, och det står nu i härkomsten.

---

## 2. Grinden: `tests/protocol/kor_bankens_facit.py`

Fem frågor per uppgift, alla mekaniska:

| Kod | Vad den fäller |
|---|---|
| `HARKOMST_UTAN_KLASS` | härkomsten namnger ingen källklass (STANDARD, RAKNAD, DATABLAD, SPAR) |
| `STANDARD_UTAN_PARAGRAF` | kallar sig STANDARD men citerar inget paragrafnummer |
| `RAKNING_UTAN_RAKNING` | kallar sig RAKNAD men visar ingen räkning |
| `HARKOMST_UTAN_MATNING` / `HARKOMST_DOD_MATNING` | ingen mätning namngiven, eller en som inte finns på disk |
| `FACIT_UR_EGEN_KOD` | härkomsten pekar in i `svc/`, `bank/domare.py`, `tests/`, `plc/`, `st/tolk.py` |
| `KARNUTGANG_UTAN_SPAR` | en kärnutgång som inget krav, ingen invariant och ingen flankräkning rör |
| `KARNUTGANG_EJ_UTSIGNAL`, `SCENARIO_OKAND_SIGNAL`, `SPAR_OKAND_SIGNAL` | signalkartan går inte ihop med `core_outputs`, scenarierna eller spåret |
| `ANTAGANDE_UTAN_MOTIV` | ett antagande utan skäl |
| `TAL_UTAN_ENHET` | ett tal med enhet i namnet men utan enhet i värdet |
| `REFERENS_FALLER`, `MOTBEVIS_GAR_IGENOM`, `MOTBEVIS_FEL_BRIST` | facit går inte att uppfylla, eller inget motbevis faller på det det namnger |

**Fyra trasiga fixturer** körs sist och måste falla. Utan dem är grinden en
förhoppning som fått ett filnamn.

### Grindens egen storhet, mätt

| Kontroll | Fällde vid första körningen |
|---|---|
| `HARKOMST_UTAN_KLASS` | **4 av 4** befintliga spårfacit |
| `TAL_UTAN_ENHET` | **0 av 139** antaganden |
| `KARNUTGANG_UTAN_SPAR` | **0 av 4** |

Enhetsregeln fällde alltså ingenting den dagen den skrevs. Det står här därför
att en grind som inte mäter sin egen storhet slutar mäta: regeln är
framåtriktad, och M-85 är skälet till att den finns — VC:s egna komponentfiler
deklarerar `MaxPayload` **utan enhet** i 2 986 komponenter, 628 av dem med
värdet `0`, och bara 14 % av 82 383 egenskaper säger vilken storhet de bär.

En första version av regeln fällde tre värden av formen `"grind 2"` — den
räknade bara ord *efter* talet. Det är en grind som fyrar på rätt sak av fel
skäl, och den räknar nu ord på båda sidor om talet.

---

## 3. Facitkällan per uppgift

<!-- FYLLS I NÄR ALLA UPPGIFTER ÄR KLARA -->

---

## 4. Räkningarna, så de går att följa

<!-- FYLLS I -->

---

## 5. Vad som INTE är mätt

<!-- FYLLS I -->
