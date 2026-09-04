# -*- coding: utf-8 -*-
"""Ogats domskontrakt: skrivare OCH lasare i samma fil.

De far aldrig ga isar. Ligger de i samma fil kan de inte drifta ifran varandra
utan att ett test ser det, och grammatikens version star pa ett stalle.

Kalla: docs/spec/41_ogat_kontrakt.md (v1) och docs/matningar/M-65 §6 (v2, som
spec-forslag tills 41_ogat_kontrakt.md skrivs om). Andras grammatiken hojs
EYES_VERSION och grinden uppdateras i SAMMA commit.

v2 (M-65, fas 15) lagger till TRE sektioner och rader i tva av de gamla. Inga
befintliga rader andras, sa en v1-rapport lases fortfarande - men grinden
kraver LIMITS, sa en v1-rapport ar aldrig guld langre. Det ar avsikten: en
rapport som inte sager vad ogat INTE ser har inte sagt allt.

  SEQUENCE   stegen, deras ordning och rakning, forreglingen
  SCENE      hela scenen: vad rorde sig, glesningen, oombedd rorelse, kast
  LIMITS     vad ogat inte ser - upplosningen, det som ar uteslutet, och det
             som inte finns i simuleringen. GRINDEN KRAVER DEN.
  TIMING     + PHASE: PLC-flank mot VC-flank, domd mot krav OCH upplosning
  THROUGHPUT + STARVED, BLOCKED, BOTTLENECK

Rent lager: ror varken VC eller natverk, kors av py2 inne i VC och py3 ute.
"""
from __future__ import absolute_import, division, print_function

import re

EYES_VERSION = 2    # Grammatikens version. v1: 41_ogat_kontrakt.md, v2: M-65 §6.
# Versioner lasaren forstar. v1 ar en delmangd av v2 (inga rader andrade), sa
# en aldre rapport lases; grinden avgor sedan om den racker.
LASBARA_VERSIONER = (1, 2)

SEKTIONER = ("MOTION", "TIMING", "SEQUENCE", "THROUGHPUT", "SAFETY", "SCENE",
             "HONESTY", "LIMITS")
DOMAR = ("PASS", "FAIL", "INCONCLUSIVE")

# Det som INTE finns i simuleringen, och som ogat darfor aldrig kan se
# (50_grindar.md, "Vad ingen grind fangar"). Varje namn ska sta som en
# NOT_SIMULATED-rad i LIMITS; grinden laser namnen, inte antalet.
EJ_SIMULERAT = ("sensor_bounce", "actuator_dynamics", "fieldbus_jitter",
                "degraded_modes", "real_hardware")

_F = r"-?\d+(?:\.\d+)?"          # flyttal, punkt som decimaltecken
_I = r"-?\d+"
_N = r"\S+"                      # ett namn utan blanksteg

# (sektion, nyckelord) -> monster for HELA raden.
RADER = {
    ("MOTION", "GRIP"):
        r"^GRIP (FORMED|NEVER_FORMED)(?: t=(%(f)s)s dist=(%(f)s)mm)?$",
    ("MOTION", "CARRY"):
        r"^CARRY (RIGID|SLIPPING|INCONCLUSIVE)(?: rot=(%(f)s)deg span=(%(f)s)s)?$",
    ("MOTION", "PLACE"):
        r"^PLACE (IN_TARGET|OFF_TARGET|DROPPED)(?: err=(%(f)s)mm z=(%(f)s)m)?$",
    ("TIMING", "EDGE"):
        r"^EDGE (%(n)s) (RISE|FALL) t=(%(f)s)s$",
    ("TIMING", "LATENCY"):
        r"^LATENCY (%(n)s) -> (%(n)s) (%(f)s)ms$",
    ("TIMING", "DWELL"):
        r"^DWELL (%(n)s) (%(f)s)s req=(%(f)s)s (OK|SHORT)$",
    ("TIMING", "RACE"):
        r"^RACE (?:none|(%(n)s)\+(%(n)s) dt=(%(f)s)ms)$",
    # v2: PLC-flank mot VC-flank, domd mot kravet OCH mot ogats upplosning.
    ("TIMING", "PHASE"):
        r"^PHASE (%(n)s) -> (%(n)s) dt=(%(f)s)ms tol=(%(f)s)ms "
        r"res=(?:(%(f)s)ms|unknown) (OK|OUT_OF_TOL|INCONCLUSIVE)$",
    # v2: stationens sekvens.
    ("SEQUENCE", "CYCLES"):
        r"^CYCLES judged=(%(i)s) broken=(%(i)s) late=(%(i)s) truncated=(%(i)s) "
        r"req=(%(i)s)$",
    ("SEQUENCE", "STEP"):
        r"^STEP (%(i)s) (%(n)s) (RISE|FALL) (OK|MISSING|TOO_LATE|TOO_EARLY)"
        r"(?: t=(%(f)s)s)? win=(%(f)s)s\.\.(%(f)s)s$",
    ("SEQUENCE", "COUNT"):
        r"^COUNT (%(i)s) (%(n)s) n=(%(i)s) max=(%(i)s) (OK|EXCEEDED)$",
    ("SEQUENCE", "INTERLOCK"):
        r"^INTERLOCK (%(n)s)\+(%(n)s) (OK|BROKEN|INCONCLUSIVE) overlap=(%(f)s)s$",
    ("THROUGHPUT", "STATION"):
        r"^STATION (%(n)s) in=(%(i)s) out=(%(i)s) avg=(%(f)s)s min=(%(f)s)s max=(%(f)s)s$",
    # v2: svalt och blockering mot ett DEKLARERAT krav, och flaskhalsen.
    ("THROUGHPUT", "STARVED"):
        r"^STARVED (%(n)s) (%(f)s)s req=(%(f)s)s (OK|EXCEEDED)$",
    ("THROUGHPUT", "BLOCKED"):
        r"^BLOCKED (%(n)s) (%(f)s)s req=(%(f)s)s (OK|EXCEEDED)$",
    ("THROUGHPUT", "BOTTLENECK"):
        r"^BOTTLENECK (?:none|(%(n)s) (starved|blocked) (%(f)s)%%)$",
    ("SAFETY", "MINDIST"):
        r"^MINDIST (%(n)s) (%(f)s)mm t=(%(f)s)s$",
    ("SAFETY", "COLLISION"):
        r"^COLLISION (?:none|(%(n)s) x (%(n)s) t=(%(f)s)s)$",
    # v2: hela scenen.
    ("SCENE", "OBJECTS"):
        r"^OBJECTS total=(%(i)s) moving=(%(i)s) still=(%(i)s) unread=(%(i)s)$",
    ("SCENE", "THINNED"):
        r"^THINNED factor=(%(i)s) (OK|CEILING) budget=(%(f)s)ms median=(%(f)s)ms$",
    ("SCENE", "UNCOMMANDED"):
        r"^UNCOMMANDED (?:none|(%(n)s) dist=(%(f)s)mm t=(%(f)s)s)$",
    ("SCENE", "IDLE_COMMANDED"):
        r"^IDLE_COMMANDED (?:none|(%(n)s) -> (%(n)s) t=(%(f)s)s)$",
    ("SCENE", "FLUNG"):
        r"^FLUNG (?:none|(%(n)s) (%(f)s)m/s t=(%(f)s)s)$",
    ("HONESTY", "TELEPORT_TRANSFER"):
        r"^TELEPORT_TRANSFER (OK|VIOLATION)(?: dist=(%(f)s)mm t=(%(f)s)s)?$",
    ("HONESTY", "BLOWUP"):
        r"^BLOWUP (OK|VIOLATION)(?: vmax=(%(f)s)m/s)?$",
    ("HONESTY", "UNDERGROUND"):
        r"^UNDERGROUND (OK|VIOLATION)(?: zmin=(%(f)s)m)?$",
    ("HONESTY", "NEVER_GRIPPED"):
        r"^NEVER_GRIPPED (OK|VIOLATION)$",
    # v2: vad ogat inte ser. Grinden kraver sektionen, varje namn i
    # EJ_SIMULERAT och en RESOLUTION-rad.
    ("LIMITS", "NOT_SIMULATED"):
        r"^NOT_SIMULATED (%(n)s)$",
    ("LIMITS", "RESOLUTION"):
        r"^RESOLUTION sample=(%(f)s)ms read=(?:(%(f)s)ms|unknown) "
        r"join=(%(f)s)ms (RUN|PRIOR) phase=(?:(%(f)s)ms|unknown)$",
    ("LIMITS", "EXCLUDED"):
        r"^EXCLUDED (%(n)s) (%(f)s)ms$",
}
RADER = dict(((s, n), m % {"f": _F, "i": _I, "n": _N})
             for (s, n), m in RADER.items())

# Regel 5, utokad i v2: rader som TVINGAR domen bort fran PASS. En rad med ett
# av orden nedan som nast sista/andra ord ar ett fynd, och ett PASS bredvid
# ett fynd ar precis den falska framgang ogat finns for. Orden ar ORD, inte
# matt: kontraktet laser dem, det raknar inte om nagot.
#
#   FAIL tvingas av: HONESTY VIOLATION (v1), GRIP NEVER_FORMED, CARRY
#   SLIPPING, PLACE OFF_TARGET/DROPPED, DWELL SHORT, STEP MISSING/TOO_LATE/
#   TOO_EARLY, COUNT EXCEEDED, INTERLOCK BROKEN, PHASE OUT_OF_TOL,
#   STARVED/BLOCKED EXCEEDED, och UNCOMMANDED/IDLE_COMMANDED/FLUNG/COLLISION
#   som inte ar none.
#   INTE PASS (INCONCLUSIVE eller FAIL) tvingas av: CARRY INCONCLUSIVE,
#   THINNED CEILING, PHASE INCONCLUSIVE, INTERLOCK INCONCLUSIVE.
#
# I v1 gallde bara HONESTY; grinden fick fanga resten som sjalvmotsagelser.
# MATT (M-65 §6): ingen rapport i banken, i harnessen eller i proven bar ett
# PASS bredvid nagot av orden, sa utokningen andrar ingen befintlig dom.
_FYNDORD = ("VIOLATION", "NEVER_FORMED", "SLIPPING", "OFF_TARGET", "DROPPED",
            "SHORT", "MISSING", "TOO_LATE", "TOO_EARLY", "EXCEEDED", "BROKEN",
            "OUT_OF_TOL")
_OSAKERORD = ("CEILING", "INCONCLUSIVE")
_INTE_NONE = ("UNCOMMANDED", "IDLE_COMMANDED", "FLUNG", "COLLISION")
# Sektioner dar orden ovan galler: alla utom LIMITS, som inte bar domsord.
_TVINGANDE_SEKTIONER = ("MOTION", "TIMING", "SEQUENCE", "THROUGHPUT", "SAFETY",
                        "SCENE", "HONESTY")

_HUVUD = re.compile(r"^EYES v(\d+)$")
_TEMPLATE = re.compile(r"^TEMPLATE (.+)$")
_RUN = re.compile(r"^RUN (\S+) DUR (%s)s SAMPLES (%s) RATE (%s)Hz$" % (_F, _I, _F))
_SEKTION = re.compile(r"^SECTION (\S+)$")
_DOM = re.compile(r"^EYES VERDICT (PASS|FAIL|INCONCLUSIVE) (.*)$")


class Kontraktsfel(Exception):
    """Ogats utdata foljer inte grammatiken. Bar en grinddom i .grinddom."""

    grinddom = "NOT GOLD (malformed eyes output)"


class OkandVersion(Kontraktsfel):
    grinddom = "NOT GOLD (unknown eyes version)"


class Avhuggen(Kontraktsfel):
    grinddom = "NOT GOLD (truncated eyes output)"


def _ord(rad):
    return rad.split()


def _fynd(rad):
    """Nyckelordet om raden ar ett fynd som tvingar FAIL, annars None."""
    ord_ = _ord(rad)
    if not ord_:
        return None
    if ord_[0] in _INTE_NONE:
        return ord_[0] if len(ord_) > 1 and ord_[1] != "none" else None
    if any(o in _FYNDORD for o in ord_[1:]):
        return ord_[0]
    return None


def _osaker(rad):
    """Nyckelordet om raden tvingar bort fran PASS utan att tvinga FAIL."""
    ord_ = _ord(rad)
    if len(ord_) > 1 and any(o in _OSAKERORD for o in ord_[1:]):
        return ord_[0]
    return None


class Rapport(object):
    def __init__(self, template, started, dur_s, samples, rate_hz,
                 version=EYES_VERSION):
        self.version = version
        self.template = template
        self.started = started
        self.dur_s = dur_s
        self.samples = samples
        self.rate_hz = rate_hz
        self.sektioner = []          # [(namn, [radstrang])]
        self.dom = None              # (varde, orsak)
        self.okanda_sektioner = []

    # ---- bygga ----------------------------------------------------------

    def sektion(self, namn):
        if namn not in SEKTIONER:
            raise Kontraktsfel("okand sektion %r; kanda ar %s"
                               % (namn, ", ".join(SEKTIONER)))
        self.sektioner.append((namn, []))
        return self

    def rad(self, text):
        if not self.sektioner:
            raise Kontraktsfel("rad utanfor sektion: %r" % (text,))
        namn, rader = self.sektioner[-1]
        text = text.strip()
        nyckel = text.split(" ", 1)[0]
        monster = RADER.get((namn, nyckel))
        if monster is None:
            raise Kontraktsfel("okant nyckelord %r i sektionen %s" % (nyckel, namn))
        if not re.match(monster, text):
            raise Kontraktsfel("raden foljer inte monstret for %s/%s: %r"
                               % (namn, nyckel, text))
        rader.append(text)
        return self

    def satt_dom(self, varde, orsak):
        if varde not in DOMAR:
            raise Kontraktsfel("okand dom %r" % (varde,))
        if "\n" in orsak:
            raise Kontraktsfel("orsaken far inte innehalla radbrytning")
        if varde == "PASS":
            # Regel 5 i kontraktet. Ett PASS med en overtradelse ar inte en
            # smaksak - det ar den sortens falska framgang hela ogat finns for.
            if self.overtradelser():
                raise Kontraktsfel(
                    "PASS med overtradelser i HONESTY: %s" % ", ".join(self.overtradelser()))
            if self.tvingande():
                raise Kontraktsfel(
                    "PASS bredvid fynd som tvingar domen: %s"
                    % ", ".join(self.tvingande()))
        self.dom = (varde, orsak)
        return self

    # ---- lasa -----------------------------------------------------------

    def overtradelser(self):
        """HONESTY-raderna med VIOLATION. v1:s regel 5, oforandrad."""
        ut = []
        for namn, rader in self.sektioner:
            if namn != "HONESTY":
                continue
            for r in rader:
                if " VIOLATION" in r:
                    ut.append(r.split(" ", 1)[0])
        return ut

    def tvingande(self):
        """Alla rader som forbjuder PASS: overtradelser, fynd och osakerheter.

        Returnerar nyckelorden. En tom lista betyder att inget i rapportens
        egna rader motsager ett PASS - inte att rapporten ar ett PASS.
        """
        ut = []
        for namn, rader in self.sektioner:
            if namn not in _TVINGANDE_SEKTIONER:
                continue
            for r in rader:
                f = _fynd(r) or _osaker(r)
                if f:
                    ut.append(f)
        return ut

    def fynd(self):
        """Bara det som tvingar FAIL (inte osakerheterna)."""
        ut = []
        for namn, rader in self.sektioner:
            if namn not in _TVINGANDE_SEKTIONER:
                continue
            for r in rader:
                f = _fynd(r)
                if f:
                    ut.append(f)
        return ut

    def godkand(self):
        """Fail-closed: bara ett rent PASS utan fynd ar godkant."""
        if self.dom is None:
            return False
        return self.dom[0] == "PASS" and not self.tvingande()

    def rader_i(self, sektion):
        ut = []
        for namn, rader in self.sektioner:
            if namn == sektion:
                ut.extend(rader)
        return ut

    def text(self):
        if self.dom is None:
            raise Kontraktsfel("rapporten saknar dom; en rapport utan dom far inte skrivas")
        ut = ["EYES v%d" % self.version,
              "TEMPLATE %s" % self.template,
              "RUN %s DUR %.3fs SAMPLES %d RATE %.2fHz"
              % (self.started, self.dur_s, self.samples, self.rate_hz)]
        for namn, rader in self.sektioner:
            ut.append("SECTION %s" % namn)
            for r in rader:
                ut.append("  " + r)
        ut.append("EYES VERDICT %s %s" % self.dom)
        return "\n".join(ut) + "\n"


def las(text):
    """Text -> Rapport. Strikt. Kastar Kontraktsfel med en grinddom i sig."""
    rader = [r.strip() for r in text.splitlines()]
    rader = [r for r in rader if r != ""]
    if not rader:
        raise Avhuggen("tom utdata")

    m = _HUVUD.match(rader[0])
    if not m:
        raise OkandVersion("forsta raden ar inte 'EYES v<int>': %r" % (rader[0],))
    version = int(m.group(1))
    if version not in LASBARA_VERSIONER:
        raise OkandVersion("ogat talar v%d, grinden kan v%s"
                           % (version, "/".join(str(v) for v in LASBARA_VERSIONER)))

    if not rader[-1].startswith("EYES VERDICT"):
        raise Avhuggen("sista raden ar inte 'EYES VERDICT ...': %r" % (rader[-1],))

    if len(rader) < 3 or not _TEMPLATE.match(rader[1]):
        raise Kontraktsfel("rad 2 ar inte 'TEMPLATE <strang>'")
    template = _TEMPLATE.match(rader[1]).group(1)

    mr = _RUN.match(rader[2])
    if not mr:
        raise Kontraktsfel("rad 3 ar inte en giltig RUN-rad: %r" % (rader[2],))

    r = Rapport(template, mr.group(1), float(mr.group(2)), int(mr.group(3)),
                float(mr.group(4)), version=version)

    aktiv = None
    hoppar_over = False
    for rad in rader[3:-1]:
        ms = _SEKTION.match(rad)
        if ms:
            namn = ms.group(1)
            if namn in SEKTIONER:
                r.sektion(namn)
                aktiv = namn
                hoppar_over = False
            else:
                # Regel 3: en OKAND sektion ignoreras, sa ett aldre grind kan
                # lasa en nyare rapport. Okand rad INUTI en kand sektion ar
                # daremot ett fel - en rapport som kraschar domaren kan dolja rott.
                r.okanda_sektioner.append(namn)
                aktiv = None
                hoppar_over = True
            continue
        if hoppar_over:
            continue
        if aktiv is None:
            raise Kontraktsfel("rad utanfor sektion: %r" % (rad,))
        r.rad(rad)

    md = _DOM.match(rader[-1])
    if not md:
        raise Kontraktsfel("domsraden foljer inte grammatiken: %r" % (rader[-1],))
    varde, orsak = md.group(1), md.group(2)
    if varde == "PASS" and r.overtradelser():
        # Kommer den motsagelsen in utifran domer vi INTE om den till PASS.
        raise Kontraktsfel(
            "PASS trots overtradelser i HONESTY (%s); regel 5 i kontraktet"
            % ", ".join(r.overtradelser()))
    if varde == "PASS" and r.tvingande():
        raise Kontraktsfel(
            "PASS trots fynd som tvingar domen (%s); regel 5 i kontraktet, v2"
            % ", ".join(r.tvingande()))
    r.dom = (varde, orsak)
    return r
