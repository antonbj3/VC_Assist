# -*- coding: utf-8 -*-
"""Ogats domskontrakt: skrivare OCH lasare i samma fil.

De far aldrig ga isar. Ligger de i samma fil kan de inte drifta ifran varandra
utan att ett test ser det, och grammatikens version star pa ett stalle.

Kalla: docs/spec/41_ogat_kontrakt.md. Andras grammatiken hojs EYES_VERSION och
grinden uppdateras i SAMMA commit.

Rent lager: ror varken VC eller natverk, kors av py2 inne i VC och py3 ute.
"""
from __future__ import absolute_import, division, print_function

import re

EYES_VERSION = 1

SEKTIONER = ("MOTION", "TIMING", "THROUGHPUT", "SAFETY", "HONESTY")
DOMAR = ("PASS", "FAIL", "INCONCLUSIVE")

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
    ("THROUGHPUT", "STATION"):
        r"^STATION (%(n)s) in=(%(i)s) out=(%(i)s) avg=(%(f)s)s min=(%(f)s)s max=(%(f)s)s$",
    ("SAFETY", "MINDIST"):
        r"^MINDIST (%(n)s) (%(f)s)mm t=(%(f)s)s$",
    ("SAFETY", "COLLISION"):
        r"^COLLISION (?:none|(%(n)s) x (%(n)s) t=(%(f)s)s)$",
    ("HONESTY", "TELEPORT_TRANSFER"):
        r"^TELEPORT_TRANSFER (OK|VIOLATION)(?: dist=(%(f)s)mm t=(%(f)s)s)?$",
    ("HONESTY", "BLOWUP"):
        r"^BLOWUP (OK|VIOLATION)(?: vmax=(%(f)s)m/s)?$",
    ("HONESTY", "UNDERGROUND"):
        r"^UNDERGROUND (OK|VIOLATION)(?: zmin=(%(f)s)m)?$",
    ("HONESTY", "NEVER_GRIPPED"):
        r"^NEVER_GRIPPED (OK|VIOLATION)$",
}
RADER = dict(((s, n), m % {"f": _F, "i": _I, "n": _N})
             for (s, n), m in RADER.items())

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
        if varde == "PASS" and self.overtradelser():
            # Regel 5 i kontraktet. Ett PASS med en overtradelse ar inte en
            # smaksak - det ar den sortens falska framgang hela ogat finns for.
            raise Kontraktsfel(
                "PASS med overtradelser i HONESTY: %s" % ", ".join(self.overtradelser()))
        self.dom = (varde, orsak)
        return self

    # ---- lasa -----------------------------------------------------------

    def overtradelser(self):
        ut = []
        for namn, rader in self.sektioner:
            if namn != "HONESTY":
                continue
            for r in rader:
                if " VIOLATION" in r:
                    ut.append(r.split(" ", 1)[0])
        return ut

    def godkand(self):
        """Fail-closed: bara ett rent PASS utan overtradelser ar godkant."""
        if self.dom is None:
            return False
        return self.dom[0] == "PASS" and not self.overtradelser()

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
    if version != EYES_VERSION:
        raise OkandVersion("ogat talar v%d, grinden kan v%d" % (version, EYES_VERSION))

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
    r.dom = (varde, orsak)
    return r
