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
