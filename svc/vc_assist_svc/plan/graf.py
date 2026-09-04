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
namna VILKA steg som ingar. Darfor letas starkt sammanhangande komponenter med
Tarjans algoritm och rapporteras med sina medlemmar; ordning() vagrar sedan
lamna en halv ordning.

ORDNINGEN AR DETERMINISTISK. Samma graf ger samma ordning varje gang, oavsett
i vilken ordning stegen rakade laggas in. Utan det gar en korning inte att
jamfora med nasta, och da ar en jamforelse mellan tva korningar vardelos.
Mekanismen: Kahns algoritm dar det MINSTA id:t bland de korbara alltid valjs.
Det ar ett kanoniskt val, inte ett godtyckligt.
"""
from __future__ import annotations

from .fel import Graffel, Specfel
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
            raise Specfel("uppgiftsgrafen", problem)

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
            raise Specfel("uppgiftsgrafen", ["inget steg heter %r" % (steg_id,)])
        return self._steg[steg_id]

    def id_lista(self):
        return sorted(self._steg)

    # -- kanter -----------------------------------------------------------

    def _kanter(self):
        """{id: sorterade beroenden som faktiskt finns}."""
        return dict((i, tuple(sorted(b for b in s.beroenden if b in self._steg)))
                    for i, s in self._steg.items())

    def okanda_beroenden(self):
        ut = []
        for i in sorted(self._steg):
            for b in sorted(self._steg[i].beroenden):
                if b not in self._steg:
                    ut.append((i, b))
        return ut

    # -- cykler -----------------------------------------------------------

    def cykler(self):
        """Varje ring av steg som beror pa varandra, med sina medlemmar.

        Tarjan, iterativt: en djup graf far inte kunna sla i rekursionstaket
        och gora en cykelrapport till ett RecursionError.
        """
        kanter = self._kanter()
        index = {}
        laglank = {}
        pa_stacken = set()
        stack = []
        raknare = [0]
        ut = []

        for start in sorted(self._steg):
            if start in index:
                continue
            arbete = [(start, 0)]
            while arbete:
                nod, i = arbete[-1]
                if i == 0:
                    index[nod] = laglank[nod] = raknare[0]
                    raknare[0] += 1
                    stack.append(nod)
                    pa_stacken.add(nod)
                grannar = kanter[nod]
                if i < len(grannar):
                    arbete[-1] = (nod, i + 1)
                    granne = grannar[i]
                    if granne not in index:
                        arbete.append((granne, 0))
                    elif granne in pa_stacken:
                        laglank[nod] = min(laglank[nod], index[granne])
                    continue
                arbete.pop()
                if arbete:
                    forlader = arbete[-1][0]
                    laglank[forlader] = min(laglank[forlader], laglank[nod])
                if laglank[nod] == index[nod]:
                    komponent = []
                    while True:
                        m = stack.pop()
                        pa_stacken.discard(m)
                        komponent.append(m)
                        if m == nod:
                            break
                    if len(komponent) > 1:
                        ut.append(sorted(komponent))
        return sorted(ut)

    # -- ordning ----------------------------------------------------------

    def ordning(self):
        """Den deterministiska topologiska ordningen.

        Kastar Graffel med cyklerna i sig om grafen inte gar att ordna. En
        halv ordning ar farligare an inget svar: den ser korbar ut.
        """
        okanda = self.okanda_beroenden()
        if okanda:
            raise Graffel("grafen gar inte att ordna: %s"
                          % "; ".join("%s beror pa %s som inte finns" % (i, b)
                                      for i, b in okanda))
        kanter = self._kanter()
        kvar = dict((i, set(b)) for i, b in kanter.items())
        ut = []
        while True:
            korbara = sorted(i for i, b in kvar.items() if not b)
            if not korbara:
                break
            # Det MINSTA id:t forst. Kanoniskt val -> samma ordning varje gang.
            valt = korbara[0]
            ut.append(valt)
            del kvar[valt]
            for beroenden in kvar.values():
                beroenden.discard(valt)
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
        ordnade = self.ordning()
        niva = {}
        for i in ordnade:
            beroenden = [b for b in self._steg[i].beroenden if b in self._steg]
            niva[i] = 0 if not beroenden else 1 + max(niva[b] for b in beroenden)
        ut = []
        for i in ordnade:
            while len(ut) <= niva[i]:
                ut.append([])
            ut[niva[i]].append(i)
        return [sorted(lag) for lag in ut]

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
        kanter = self._kanter()
        sedda = set()
        stack = [fran]
        while stack:
            nod = stack.pop()
            for b in kanter.get(nod, ()):
                if b == till:
                    return True
                if b not in sedda:
                    sedda.add(b)
                    stack.append(b)
        return False

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
            raise Specfel("uppgiftsgraf", ["forvantade en lista steg, fick %s"
                                           % type(data).__name__])
        return cls([Steg.fran_json(d) for d in data])
