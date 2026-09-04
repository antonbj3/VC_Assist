# FAS 3 ACCEPTANS — guldgrinden

**beskriver:** `svc/vc_assist_svc/guldgrind.py`
**kontrakt:** `docs/spec/50_grindar.md`, `docs/spec/41_ogat_kontrakt.md`
**grind (70_faser.md):** *"Guld endast när varje cell passerar. Okänd klass ⇒ inte guld."*

## Status: STÄNGD — 11 fail-closed-vägar provade

## Doktrinen den lyder under

Grinden **parsar ögats egen utdata och implementerar aldrig om måttet.**
Motivet är en mätt incident i källprojektet där en omimplementerad positionsdom
underkände 2 av 4 medan ögat visade 4 av 4.

Det har en konsekvens som ser konstig ut tills man förstår skälet: en rapport
med `PLACE IN_TARGET err=999.0mm` och `VERDICT PASS` **ger guld**. Talet är
ögats sak att döma; toleransen kan vara cellens. Grinden mäter ingenting.

Undantaget är **självmotsägelse**. Säger rapporten `PASS` men bär en rad med
`OFF_TARGET`, `SLIPPING`, `DROPPED`, `NEVER_FORMED`, `SHORT`, `VIOLATION` eller
en kollision som inte är `none`, så faller den. Det är inte en ommätning — det
är ögats egna kategoriska **ord**, lästa mot dess egen slutsats.

## Fail-closed, prövat på varje väg in

| Väg in | Utfall | Test |
|---|---|---|
| tom lista | NOT GOLD | ingenting att döma är inget godkännande |
| okänd scenarioklass | NOT GOLD | ärvt ur `eyes_gold_gate` |
| ingen ögonrapport | NOT GOLD | tystnad är aldrig ett godkännande |
| avhuggen rapport | NOT GOLD (truncated) | |
| okänd ögonversion | NOT GOLD (unknown eyes version) | aldrig gissa |
| `FAIL` | NOT GOLD | |
| `INCONCLUSIVE` | NOT GOLD | |
| en förgrind **ej körd** | NOT GOLD | fyra egna prov, ett per grind |
| en förgrind **röd** | NOT GOLD | fyra egna prov |
| en av tre celler faller | NOT GOLD **för alla** | |
| alla stationer gröna, linan faller | NOT GOLD | |

## Utfall 2026-09-04 — mot ögats verkliga utdata från VC

Kört som sista steget i `tests/protocol/kor_fas2.py`, alltså på rapporter som
kommer ur en riktig VC-körning, inte ur konstruerade strängar.

```
bara de grona (1 st): GOLD gold_verified_core (1 av 1 celler gav PASS)
alla 5 cellerna:      NOT GOLD (fel_placerad: ogat sa FAIL ...; glider: ...; tappad: ...)
```

Guldet ges alltså bara när varje cell passerar, och underkännandet namnger vilka
celler som föll och varför.

## Guldstegen

| Nivå | Krav | Prövad |
|---|---|---|
| `gold_verified_core` (L1) | en station, ögat säger PASS | ☑ mot VC |
| `gold_line_verified` (L2) | varje station **och** linan | ☑ enhetstest, ☐ mot VC (ingen lina byggd än) |
| `candidate` | endast resonemang | levereras aldrig |

## Vad som INTE är prövat

* **L2 mot en riktig lina** — ingen flerstationslina är byggd i VC än (fas 8).
* **Förgrindarna 1–4 är prövade som gränssnitt, inte som mätning.** Grinden
  kräver att de rapporterat grönt; att de själva mäter rätt hör till deras egna
  protokoll.
* **Säkerhetsgränsen** (`50_grindar.md`) är byggd i ST-lagrets `{SAKERHET}`-kontroll
  men inte kopplad till guldgrinden.
