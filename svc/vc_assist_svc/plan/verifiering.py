# -*- coding: utf-8 -*-
"""Vad planen ska BEVISA, uttryckt i ogats egen grammatik.

Regeln ar guldstegens: en plan utan verifiering ar en KANDIDAT, aldrig en
leverans (docs/spec/50_grindar.md). Darfor bar varje plan ett
Verifieringskrav, och kravet skrivs i de rader ogat faktiskt kan skriva -
inte i egen prosa. En rad som ogat aldrig kan producera ar ingen fordran, den
ar en onskan, och avvisas mekaniskt vid planeringen.

Mallformen ar bankens: talen byts mot '*', orden och ordningen star fast. Vi
later inte planen lasa tal den annu inte matt, men den far lasa VAD som ska
matas. Implementationen delas med bank/schema.py (se kallor.py) sa att en
facitrad i banken och ett verifieringskrav i en plan betyder samma sak.

Tre listor, och den tredje ar den viktigaste:

    rader        ska bevisas av DEN HAR planen
    forbjudna    far inte forekomma
    uppskjutna   bevisas INTE har, med skalet och vem som bevisar det

Utan den tredje listan skulle en plan kunna tappa ett krav genom att bara
inte namna det. Ett uppskjutet krav ar synligt; ett bortglomt ar inte det.

I1: grinden laser ogats dom, den raknar aldrig om ett matt. Doma() nedan
matcher rader och laser ogats verdict - den harleder ingenting.
"""
from __future__ import annotations

from .fel import Verifieringsfel
from .kallor import K, bankschema

# Ett skal kortare an sa har hinner inte saga vem som bevisar kravet i
# stallet. Samma matt som ett antagandes motiv, och av samma skal; talet ags
# av bank/schema.py.
MIN_SKAL_TECKEN = bankschema.MIN_MOTIV_TECKEN


class Krav(object):
    """En rad ogat maste ha skrivit (eller inte fatt skriva)."""

    __slots__ = ("sektion", "mall")

    def __init__(self, sektion, mall):
        self.sektion = sektion
        self.mall = mall
        fel = bankschema.granska_facitrad(sektion, mall)
        if fel:
            raise Verifieringsfel("kravet %r i %s: %s" % (mall, sektion, fel))

    def __repr__(self):
        return "Krav(%s, %r)" % (self.sektion, self.mall)

    def __eq__(self, annan):
        return (isinstance(annan, Krav) and annan.sektion == self.sektion
                and annan.mall == self.mall)

    def __hash__(self):
        return hash((self.sektion, self.mall))

    def matchar(self, rad):
        return bool(bankschema.mall_till_regex(self.mall).match(rad))

    def till_json(self):
        return {"sektion": self.sektion, "mall": self.mall}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("sektion", "mall"), "krav")
        return cls(data["sektion"], data["mall"])


class Uppskjutet(object):
    """Ett krav som den har planen INTE bevisar, med skalet utskrivet."""

    __slots__ = ("sektion", "mall", "skal")

    def __init__(self, sektion, mall, skal):
        self.sektion = sektion
        self.mall = mall
        self.skal = skal
        fel = bankschema.granska_facitrad(sektion, mall)
        if fel:
            raise Verifieringsfel("det uppskjutna kravet %r i %s: %s"
                                  % (mall, sektion, fel))
        if not isinstance(skal, str) or len(skal.strip()) < MIN_SKAL_TECKEN:
            raise Verifieringsfel(
                "det uppskjutna kravet %r saknar skal pa minst %d tecken; ett "
                "krav far skjutas upp, men inte tyst" % (mall, MIN_SKAL_TECKEN))

    def __repr__(self):
        return "Uppskjutet(%s, %r)" % (self.sektion, self.mall)

    def till_json(self):
        return {"sektion": self.sektion, "mall": self.mall, "skal": self.skal}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("sektion", "mall", "skal"), "uppskjutet krav")
        return cls(data["sektion"], data["mall"], data["skal"])


def _nycklar(data, vantade, vad):
    if not isinstance(data, dict):
        raise Verifieringsfel("%s: forvantade ett objekt, fick %s"
                              % (vad, type(data).__name__))
    saknade = sorted(set(vantade) - set(data))
    okanda = sorted(set(data) - set(vantade))
    if saknade or okanda:
        raise Verifieringsfel(
            "%s: saknade nycklar %s, okanda nycklar %s"
            % (vad, ", ".join(saknade) or "inga", ", ".join(okanda) or "inga"))
    return data


class Verifieringsdom(object):
    """Utfallet av att halla kravet mot en verklig ogonrapport."""

    __slots__ = ("observerad_dom", "saknade", "forbjudna_traffar", "fel")

    def __init__(self, observerad_dom=None, saknade=(), forbjudna_traffar=(),
                 fel=()):
        self.observerad_dom = observerad_dom
        self.saknade = list(saknade)
        self.forbjudna_traffar = list(forbjudna_traffar)
        self.fel = list(fel)

    @property
    def uppfyllt(self):
        return (not self.fel and not self.saknade
                and not self.forbjudna_traffar)

    def __repr__(self):
        return "Verifieringsdom(%s, %s)" % (
            self.observerad_dom, "uppfyllt" if self.uppfyllt else "brister")

    def text(self):
        if self.uppfyllt:
            return "ogat sa %s och alla krav ar uppfyllda" % self.observerad_dom
        delar = []
        if self.fel:
            delar.append("; ".join(self.fel))
        if self.saknade:
            delar.append("ogat skrev aldrig: %s"
                         % ", ".join("%s/%s" % (k.sektion, k.mall)
                                     for k in self.saknade))
        if self.forbjudna_traffar:
            delar.append("forbjudna rader forekom: %s"
                         % ", ".join(sorted(self.forbjudna_traffar)))
        return "; ".join(delar)


class Verifieringskrav(object):
    """Det planen ska bevisa nar den ar klar."""

    __slots__ = ("dom", "rader", "forbjudna", "uppskjutna")

    def __init__(self, dom="PASS", rader=(), forbjudna=(), uppskjutna=()):
        self.dom = dom
        self.rader = list(rader)
        self.forbjudna = list(forbjudna)
        self.uppskjutna = list(uppskjutna)
        if dom not in K.DOMAR:
            raise Verifieringsfel("domen %r ar inte en av %s"
                                  % (dom, ", ".join(K.DOMAR)))
        for lista, vad in ((self.rader, "rader"),
                           (self.forbjudna, "forbjudna")):
            for k in lista:
                if not isinstance(k, Krav):
                    raise Verifieringsfel("%s: %r ar inget Krav" % (vad, k))
        for u in self.uppskjutna:
            if not isinstance(u, Uppskjutet):
                raise Verifieringsfel("uppskjutna: %r ar inget Uppskjutet" % (u,))
        # Regel 5 i ogats kontrakt, och bankens lintkod M14: ett PASS som
        # KRAVER en hederlighetsovertradelse ar en sjalvmotsagelse. Ogats egen
        # las() vagrar lasa en sadan rapport, sa kravet kunde aldrig uppfyllas.
        if self.dom == "PASS":
            for k in self.rader:
                if k.sektion == "HONESTY" and "VIOLATION" in k.mall:
                    raise Verifieringsfel(
                        "kravet sager PASS men kraver raden %r; ogat skriver "
                        "aldrig ett PASS med en HONESTY-overtradelse" % (k.mall,))

    def __repr__(self):
        return "Verifieringskrav(%s, %d rader, %d uppskjutna)" % (
            self.dom, len(self.rader), len(self.uppskjutna))

    def uttalad(self):
        """En plan vars krav ar tomt ar en kandidat, aldrig en leverans."""
        return bool(self.rader)

    def sektioner(self):
        return sorted(set(k.sektion for k in self.rader))

    # -- domen -----------------------------------------------------------

    def doma(self, ogontext):
        """Haller kravet mot ogats EGEN utdata.

        Fail-closed: ingen rapport, en avhuggen rapport eller en okand version
        ar ett underkannande, aldrig ett tyst godkannande (I3).
        """
        if not ogontext or not str(ogontext).strip():
            return Verifieringsdom(
                fel=["ingen ogonrapport; tystnad ar aldrig ett godkannande"])
        try:
            rapport = K.las(ogontext)
        except K.Kontraktsfel as fel:
            return Verifieringsdom(fel=["%s: %s" % (fel.grinddom, fel)])

        dom = Verifieringsdom(observerad_dom=rapport.dom[0])
        if rapport.dom[0] != self.dom:
            dom.fel.append("ogat sa %s, kravet var %s (%s)"
                           % (rapport.dom[0], self.dom, rapport.dom[1]))

        per_sektion = {}
        for namn, rader in rapport.sektioner:
            per_sektion.setdefault(namn, []).extend(rader)

        for krav in self.rader:
            if not any(krav.matchar(r) for r in per_sektion.get(krav.sektion, [])):
                dom.saknade.append(krav)
        for forbud in self.forbjudna:
            for rad in per_sektion.get(forbud.sektion, []):
                if forbud.matchar(rad):
                    dom.forbjudna_traffar.append(rad)
        return dom

    # -- serialisering ---------------------------------------------------

    def till_json(self):
        return {"dom": self.dom,
                "rader": [k.till_json() for k in self.rader],
                "forbjudna": [k.till_json() for k in self.forbjudna],
                "uppskjutna": [u.till_json() for u in self.uppskjutna]}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("dom", "rader", "forbjudna", "uppskjutna"),
                 "verifieringskrav")
        return cls(data["dom"],
                   [Krav.fran_json(k) for k in data["rader"]],
                   [Krav.fran_json(k) for k in data["forbjudna"]],
                   [Uppskjutet.fran_json(u) for u in data["uppskjutna"]])
