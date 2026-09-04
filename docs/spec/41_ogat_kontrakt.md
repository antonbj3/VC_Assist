# Ögats domskontrakt

Grinden parsar ögats utdata **byte för byte**. Därför ligger grammatiken fast här.
Ändras den ändras versionen, och grinden vägrar en okänd version.

## Grundregel

Ögat är den enda som fäller dom. Grinden tolkar aldrig om ett mått, den läser
ögats egen slutsats. Motiverat av en mätt incident i källprojektet där en
omimplementerad positionsdom underkände 2 av 4 medan ögat visade 4 av 4.

## Två utdata

| Vad | Var | För vem |
|---|---|---|
| Domstext | stdout | grinden |
| Full serie | `eyes.json` på disk | analys och felsökning |

Domstexten är auktoritativ. `eyes.json` är underlag, aldrig dom.

## Grammatik

Rader är `\n`-separerade. Ledande och avslutande blanksteg ignoreras.
Enheter är **alltid** utskrivna. Tal använder punkt som decimaltecken.

```
EYES v<int>
TEMPLATE <sträng>
RUN <iso8601> DUR <float>s SAMPLES <int> RATE <float>Hz
SECTION MOTION
  GRIP <FORMED|NEVER_FORMED> [t=<float>s dist=<float>mm]
  CARRY <RIGID|SLIPPING|INCONCLUSIVE> [rot=<float>deg span=<float>s]
  PLACE <IN_TARGET|OFF_TARGET|DROPPED> [err=<float>mm z=<float>m]
SECTION TIMING
  EDGE <signal> <RISE|FALL> t=<float>s
  LATENCY <signal> -> <mover> <float>ms
  DWELL <station> <float>s req=<float>s <OK|SHORT>
  RACE <none|<sigA>+<sigB> dt=<float>ms>
SECTION THROUGHPUT
  STATION <namn> in=<int> out=<int> avg=<float>s min=<float>s max=<float>s
SECTION SAFETY
  MINDIST <par> <float>mm t=<float>s
  COLLISION <none|<nodA> x <nodB> t=<float>s>
SECTION HONESTY
  TELEPORT_TRANSFER <OK|VIOLATION> [dist=<float>mm t=<float>s]
  BLOWUP <OK|VIOLATION> [vmax=<float>m/s]
  UNDERGROUND <OK|VIOLATION> [zmin=<float>m]
  NEVER_GRIPPED <OK|VIOLATION>
EYES VERDICT <PASS|FAIL|INCONCLUSIVE> <orsak utan radbrytning>
```

## Parsningsregler

1. Första raden **måste** vara `EYES v<int>`. Okänd version ⇒ grinden svarar
   `NOT GOLD (unknown eyes version)`. Aldrig gissa.
2. Sista raden **måste** börja med `EYES VERDICT`. Saknas den ⇒
   `NOT GOLD (truncated eyes output)`. En avhuggen rapport är aldrig ett godkännande.
3. Okänd `SECTION` ignoreras, men okänd rad **inuti** en känd sektion är ett fel.
   Ärvt skäl: en rapport som kraschar domaren kan dölja rött.
4. `INCONCLUSIVE` räknas som **inte godkänt**. Fail-closed.
5. Alla `VIOLATION` i `HONESTY` tvingar `VERDICT FAIL` oavsett övrigt.

## eyes.json

```json
{
  "v": 1,
  "template": "...",
  "run": { "started": "...", "dur_s": 0.0, "samples": 0, "rate_hz": 0.0 },
  "tracked": { "parts": ["..."], "tools": ["..."], "signals": ["..."], "pairs": [["a","b"]] },
  "rows": [
    { "t": 0.0,
      "parts": { "<namn>": { "p": [0,0,0], "q": [0,0,0,1] } },
      "tools": { "<namn>": { "p": [0,0,0], "q": [0,0,0,1] } },
      "joints": { "<robot>": [0.0] },
      "mind":  { "<par>": { "d_mm": 0.0, "p1": [0,0,0], "p2": [0,0,0] } },
      "sig":   { "<signal>": false },
      "plc":   { "<tagg>": false },
      "stat":  { "<station>": { "in": 0, "out": 0 } } }
  ],
  "derived": { },
  "verdict": { "value": "PASS", "reason": "..." }
}
```

`rows` skrivs inkrementellt var hundrade rad med `"partial": true`, så en avbruten
körning ändå går att läsa. Ärvt ur källan.

## Tröskelregel

Varje tröskel i den härledda analysen bär en kommentar med den mätning som satte den.
Format i koden:

```python
GRIP_DIST_MAX_MM = 150.0   # PRELIMINÄR. Sätts av mätning M-03.
```

En tröskel utan hänvisning är ett linterfel. Källprojektets `scene_eyes` har
fyra tal utan motivering; det är dess enda kända svaghet och vi upprepar den inte.

## Versionering

`EYES v1` är detta dokument. Varje ändring av grammatiken höjer versionen och
kräver att grinden uppdateras i samma commit. De två får aldrig gå isär.


---

# EYES v2 — gällande grammatik

Höjd 2026-09-05 av `M-65`. Grammatiken i koden är höjd i **samma commit** som
grinden och varje läsare (`oga_kontrakt.py`, `guldgrind.py`, `bank/schema.py`,
`harness/fallor.py`, `verktyg/ogonverktyg.py`), enligt kontraktets egen
versionsregel. Avsnitten ovan beskriver v1 och står kvar som historik.

**v1 är en delmängd av v2.** Ingen rad har ändrat form. Läsaren förstår båda.
Men grinden **kräver** `LIMITS`, så en v1-rapport är aldrig guld — det finns
ingen väg runt kravet genom att tala v1.

## Nya och ändrade sektioner

```
SECTION TIMING
  PHASE <tagg> -> <signal> dt=<f>ms tol=<f>ms res=<<f>ms|unknown> <OK|OUT_OF_TOL|INCONCLUSIVE>
SECTION SEQUENCE                            # skrivs bara när en sekvens deklarerats
  CYCLES judged=<i> broken=<i> late=<i> truncated=<i> req=<i>
  STEP <cykel> <signal> <RISE|FALL> <OK|MISSING|TOO_LATE|TOO_EARLY> [t=<f>s] win=<f>s..<f>s
  COUNT <cykel> <signal> n=<i> max=<i> <OK|EXCEEDED>
  INTERLOCK <a>+<b> <OK|BROKEN|INCONCLUSIVE> overlap=<f>s
SECTION THROUGHPUT
  STARVED <station> <f>s req=<f>s <OK|EXCEEDED>
  BLOCKED <station> <f>s req=<f>s <OK|EXCEEDED>
  BOTTLENECK <none|<station> <starved|blocked> <f>%>
SECTION SCENE                               # skrivs bara när scenen har objekt
  OBJECTS total=<i> moving=<i> still=<i> unread=<i>
  THINNED factor=<i> <OK|CEILING> budget=<f>ms median=<f>ms
  UNCOMMANDED <none|<objekt> dist=<f>mm t=<f>s>
  IDLE_COMMANDED <none|<signal> -> <objekt> t=<f>s>
  FLUNG <none|<objekt> <f>m/s t=<f>s>
SECTION LIMITS                              # GRINDEN KRÄVER DEN
  NOT_SIMULATED sensor_bounce
  NOT_SIMULATED actuator_dynamics
  NOT_SIMULATED fieldbus_jitter
  NOT_SIMULATED degraded_modes
  NOT_SIMULATED real_hardware
  RESOLUTION sample=<f>ms read=<<f>ms|unknown> join=<f>ms <RUN|PRIOR> phase=<<f>ms|unknown>
  EXCLUDED plc_scan <f>ms
```

`STEP` skrivs bara för steg som inte var OK. `UNCOMMANDED`, `IDLE_COMMANDED`
och `FLUNG` skrivs bara när frågan ställts — **ett `none` för en fråga ingen
ställt vore ett påstående**, inte en tystnad.

## LIMITS är obligatorisk, och varför

`50_grindar.md` säger att ögat är felfinnande, aldrig bevis: sensorstuds,
ställdonsdynamik, fältbussjitter, degraderade lägen och verklig hårdvara finns
inte i simuleringen. Fram till v2 stod det i specen och ingenstans i rapporten.

En räckviddsredovisning som bara finns i ett dokument gäller inte den enskilda
körningen. Nu bär varje rapport sina egna gränser, och `guldgrind.py` kräver
sektionen med `OBLIGATORISKA_SEKTIONER = MOTION, HONESTY, LIMITS`. Det är samma
resonemang som gav `HONESTY` dess krav: en regel är **tom** om sektionen inte
finns.

`RESOLUTION` bär `RUN` när upplösningen är mätt i körningen och `PRIOR` när den
är ett antagande. Skillnaden får inte gömmas.

## Regel 5, utökad

Ett `PASS` får inte stå bredvid: `VIOLATION`, `NEVER_FORMED`, `SLIPPING`,
`OFF_TARGET`, `DROPPED`, `SHORT`, `MISSING`, `TOO_LATE`, `TOO_EARLY`,
`EXCEEDED`, `BROKEN`, `OUT_OF_TOL`, eller `COLLISION` / `UNCOMMANDED` /
`IDLE_COMMANDED` / `FLUNG` som inte är `none`. Dessutom tvingar
`CARRY INCONCLUSIVE`, `THINNED CEILING`, `PHASE INCONCLUSIVE` och
`INTERLOCK INCONCLUSIVE` bort från `PASS`.

Skrivaren vägrar producera det, läsaren kastar om den ser det.

**Orden matchas som hela ord.** `LATE` ligger inne i `LATENCY`, och en
delsträngsmatchning hade fällt varje rapport som bär en latensrad. Det är
precis den sortens fel som ser ut som stränghet och i själva verket är ett
trasigt instrument.

## Fem domare, en trasig cell var

`Analys.DOMARE = sekvens, timing, grepp, kollision, genomflode`. Matrisen är
mätt: 12 celler × 5 domare ger **exakt en domare FAIL per cell**, och släcks en
domare blir exakt dess celler gröna. Ingen domare bär en annans cell.

Sekvens och timing var tidigare **en** domare. De är delade nu: `MISSING` är
sekvensens fel, `TOO_LATE` och `TOO_EARLY` är timingens.

## Fasupplösningen är max, inte summa

`max(L, S+J)` där L är låstiden, S provtagningssteget och J hopfogningen.
Monte Carlo: summan var upp till **70 % för lös**, medan max aldrig
överskreds och nåddes till 95–98 %.

En fas som deklarerar ett krav finare än upplösningen döms `INCONCLUSIVE`,
aldrig `PASS`. Mot en riktig kopplare (89 ms varv, `M-39`) är fasupplösningen
**≈ 89 ms** — och det är det viktigaste talet i hela mätningen, för det säger
vilka krav som över huvud taget går att döma.
