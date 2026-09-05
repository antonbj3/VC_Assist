# -*- coding: utf-8 -*-
"""Uppgiftsgrafen: villkor och ordning.

Fyra former, och alla fyra maste finnas for att en byggordning ska ga att
uttrycka:

    beroenden       A fore B
    forvillkor      steget kors bara om nagot galler (predikat.py)
    alternativ      antingen A eller B
    parallellitet   far koras samtidigt

Tva krav ar hardare an de later:

CYKLER SKA UPPTACKAS. En cykel far aldrig bli en oandlig loop, och felet ska
namna VILKA steg som ingar. ordning() vagrar sedan lamna en halv ordning.

ORDNINGEN AR DETERMINISTISK. Samma graf ger samma ordning varje gang, oavsett
i vilken ordning stegen rakade laggas in. Utan det gar en korning inte att
jamfora med nasta, och da ar en jamforelse mellan tva korningar vardelos.

BADA SVAREN RAKNAS I ordning.py, som ocksa processordningen i processer.py
anvander. Samma matematik far inte skrivas tva ganger: tva implementationer av
samma kontroll ar tva OLIKA kontroller sa fort nagon ratter den ena.
"""
from __future__ import annotations

from .fel import Graffel, Specfel
from .ordning import (cykler as _cykler, kanonisk_ordning, lager as _lager,
                      nabar as _nabar, okanda_kanter)
from .steg import Steg

LINTKODER = {
    "G1_OKANT_BEROENDE": "steget beror pa ett steg som inte finns",
    "G2_CYKEL": "stegen beror pa varandra i en ring",
    "G3_LASNING_UTAN_BEROENDE": "steget laser ett annat stegs svar utan att "
                                "bero pa det",
    "G4_ALTERNATIV_ENSAM": "alternativgrupp med farre an tva steg",
    "G5_ALTERNATIV_BEROENDE": "ett alternativ beror pa sitt eget alternativ",
    "G6_PARALLELL_MOTSAGELSE": "steg som forklarats samtidiga har en "
                               "beroendevag mellan sig",
    "G7_PARALLELL_ENSAM": "parallellgrupp med farre an tva steg",
}


class Uppgiftsgraf(object):
    """Stegen och deras ordning. Bar ingen kannedom om verktygsregistret."""

    __slots__ = ("_steg", "_ordnade_id")

    def __init__(self, steg):
        self._steg = {}
        self._ordnade_id = []
        problem = []
        for s in steg:
            if not isinstance(s, Steg):
                problem.append("%r ar inget Steg" % (s,))
                continue
            if s.id in self._steg:
                problem.append("dubblerat steg-id %r" % (s.id,))
                continue
            self._steg[s.id] = s
            self._ordnade_id.append(s.id)
        if problem:
            raise Specfel("the task graph", problem)

    def __len__(self):
        return len(self._steg)

    def __iter__(self):
        """Stegen i den ordning de lades in. For ordningen: ordning()."""
        return (self._steg[i] for i in self._ordnade_id)

    def __contains__(self, steg_id):
        return steg_id in self._steg

    def __repr__(self):
        return "Uppgiftsgraf(%d steg)" % len(self._steg)

    def steg(self, steg_id):
        if steg_id not in self._steg:
            raise Specfel("the task graph", ["no step is named %r" % (steg_id,)])
        return self._steg[steg_id]

    # -- kanter -----------------------------------------------------------

    def _kanter(self):
        """{id: sorterade beroenden som faktiskt finns}."""
        return dict((i, tuple(sorted(b for b in s.beroenden if b in self._steg)))
                    for i, s in self._steg.items())

    def _alla_kanter(self):
        """{id: beroenden som deklarerats, aven de som inte finns}."""
        return dict((i, tuple(s.beroenden)) for i, s in self._steg.items())

    def okanda_beroenden(self):
        return okanda_kanter(self._alla_kanter())

    # -- cykler -----------------------------------------------------------

    def cykler(self):
        """Varje ring av steg som beror pa varandra, med sina medlemmar.

        Raknas i ordning.py, iterativt: en djup graf far inte kunna sla i
        rekursionstaket och gora en cykelrapport till ett RecursionError.
        """
        return _cykler(self._kanter())

    # -- ordning ----------------------------------------------------------

    def ordning(self):
        """Den deterministiska topologiska ordningen.

        Kastar Graffel med cyklerna i sig om grafen inte gar att ordna. En
        halv ordning ar farligare an inget svar: den ser korbar ut.
        """
        okanda = self.okanda_beroenden()
        if okanda:
            raise Graffel("the graph cannot be ordered: %s"
                          % "; ".join("%s depends on %s which does not exist" % (i, b)
                                      for i, b in okanda))
        # Det MINSTA id:t forst. Kanoniskt val -> samma ordning varje gang.
        ut, kvar = kanonisk_ordning(self._kanter())
        if kvar:
            cykler = self.cykler()
            raise Graffel(
                "grafen har %d cykel(er) och gar inte att ordna: %s"
                % (len(cykler), "; ".join(" -> ".join(c) for c in cykler)),
                cykler)
        return ut

    def lager(self):
        """Stegen i lager. Steg i samma lager har inga beroenden mellan sig.

        Det ar den ovre gransen for hur brett en samtidig utforare skulle
        kunna kora planen. Koraren i korning.py kor sekventiellt (se dess
        docstring), sa talet ar ett matt pa planen, inte pa korningen.
        """
        return _lager(self._kanter(), self.ordning())

    def bredd(self):
        """Bredaste lagret. 1 betyder en helt sekventiell plan."""
        lag = self.lager()
        return max(len(l) for l in lag) if lag else 0

    # -- grupper ----------------------------------------------------------

    def _grupper(self, falt):
        ut = {}
        for i in sorted(self._steg):
            namn = getattr(self._steg[i], falt)
            if namn:
                ut.setdefault(namn, []).append(i)
        return ut

    def alternativgrupper(self):
        return self._grupper("alternativ_grupp")

    def parallellgrupper(self):
        return self._grupper("parallell_grupp")

    def nabar(self, fran, till):
        """Finns en beroendevag fran 'till' till 'fran'? (dvs. en ordning)."""
        return _nabar(self._kanter(), fran, till)

    # -- granskning -------------------------------------------------------

    def problem(self):
        """[(lintkod, text)]. Tom lista = grafen haller.

        Kastar aldrig: en granskning som kraschar pa en trasig graf sager
        ingenting om vad som var trasigt (S10).
        """
        ut = []
        for i, b in self.okanda_beroenden():
            ut.append(("G1_OKANT_BEROENDE",
                       "steget %s beror pa %s som inte finns i planen" % (i, b)))
        for cykel in self.cykler():
            ut.append(("G2_CYKEL",
                       "cykel mellan %s" % " -> ".join(cykel)))
        for i in sorted(self._steg):
            s = self._steg[i]
            for lask in s.lasta_steg():
                if lask not in self._steg:
                    ut.append(("G1_OKANT_BEROENDE",
                               "steget %s laser svaret fran %s som inte finns"
                               % (i, lask)))
                elif lask not in s.beroenden:
                    ut.append(("G3_LASNING_UTAN_BEROENDE",
                               "steget %s laser svaret fran %s men beror inte "
                               "pa det; ordningen vore inte garanterad"
                               % (i, lask)))
        for namn, medlemmar in sorted(self.alternativgrupper().items()):
            if len(medlemmar) < 2:
                ut.append(("G4_ALTERNATIV_ENSAM",
                           "alternativgruppen %s har bara %s; ett alternativ "
                           "utan alternativ ar ett vanligt steg"
                           % (namn, ", ".join(medlemmar))))
            for a in medlemmar:
                for b in medlemmar:
                    if a != b and b in self._steg[a].beroenden:
                        ut.append(("G5_ALTERNATIV_BEROENDE",
                                   "alternativet %s beror pa alternativet %s i "
                                   "samma grupp %s" % (a, b, namn)))
        for namn, medlemmar in sorted(self.parallellgrupper().items()):
            if len(medlemmar) < 2:
                ut.append(("G7_PARALLELL_ENSAM",
                           "parallellgruppen %s har bara %s; en deklaration om "
                           "samtidighet med ett enda steg mater ingenting"
                           % (namn, ", ".join(medlemmar))))
            if not self.cykler():
                for n, a in enumerate(medlemmar):
                    for b in medlemmar[n + 1:]:
                        if self.nabar(a, b) or self.nabar(b, a):
                            ut.append((
                                "G6_PARALLELL_MOTSAGELSE",
                                "%s och %s ligger i parallellgruppen %s men det "
                                "finns en beroendevag mellan dem; de kan inte "
                                "koras samtidigt" % (a, b, namn)))
        return ut

    # -- serialisering ----------------------------------------------------

    def till_json(self):
        return [self._steg[i].till_json() for i in self._ordnade_id]

    @classmethod
    def fran_json(cls, data):
        if not isinstance(data, list):
            raise Specfel("task graph", ["expected a list of steps, got %s"
                                           % type(data).__name__])
        return cls([Steg.fran_json(d) for d in data])
