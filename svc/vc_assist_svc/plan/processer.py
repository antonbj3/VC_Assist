# -*- coding: utf-8 -*-
"""Processordningen: vad som ska handa i cellen, och i vilken ordning.

Operatorens krav, ordagrant: "Man ska kunna satta upp instruktioner, bygga
denna scen, med dessa, med villkor och ORDNING AV PROCESSER osv".

TVA ORDNINGAR SOM INTE AR SAMMA SAK, OCH SOM BLANDATS IHOP

    byggordningen   i vilken ordning VERKTYGEN anropas for att fa scenen pa
                    plats. Den bor i graf.py och ar redan byggd.
    processordningen  i vilken ordning CELLEN gor sitt arbete: mata in, spanna,
                    plocka, svetsa, mata ut. Den overlever bygget, den ar det
                    styrkoden ska genomfora, och den ar det operatoren beskriver
                    nar han bestaller.

De tva har olika livslangd och olika lasare. Byggordningen ar slut nar scenen
star. Processordningen ar da precis vad fas 7 och 8 ska skriva ST for. Att
uttrycka den andra som den forsta hade last processerna vid de verktygsanrop
som rakade bygga dem - och en cykel bland processerna hade da synts som ett
byggfel, om den hade synts alls.

CYKELKRAVET AR HARDARE AN DET LATER

En cykel ska fallas MED VILKA PROCESSER SOM BILDAR DEN, aldrig med "planen ar
ogiltig". "Malning fore svetsning" plus "svetsning fore malning" ar ett
begripligt misstag i en bestallning; svaret maste vara lika begripligt.
Rakningen delas med uppgiftsgrafen (ordning.py), sa en ring som fangas i det
ena lagret inte kan passera i det andra.

Endast standardbiblioteket.
"""
from __future__ import annotations

from .fel import Graffel, Specfel
from .harkomst import Harkomst
from .ordning import cykler, kanonisk_ordning, okanda_kanter

LINTKODER = {
    "PO1_CYKEL": "processerna beror pa varandra i en ring",
    "PO2_OKAND_PROCESS": "ett ordningskrav pekar pa en process som inte finns",
    "PO3_DUBBEL_PROCESS": "tva processer bar samma id",
    "PO4_SJALVORDNING": "en process ska ske fore sig sjalv",
    "PO5_OKAND_ROLL": "processen utfors av en roll som inte finns bland delarna",
    "PO6_DUBBELT_ORDNINGSKRAV": "samma ordningskrav star tva ganger",
}


def _text(varde, falt, problem, minst=1):
    if not isinstance(varde, str) or len(varde.strip()) < minst:
        problem.append("%s: kravs text pa minst %d tecken, fick %r"
                       % (falt, minst, varde))


class Process(object):
    """Ett arbetsmoment cellen ska utfora."""

    __slots__ = ("id", "vad", "roll", "harkomst")

    def __init__(self, id, vad, roll=None, harkomst=None):
        self.id = id
        self.vad = vad
        self.roll = roll
        self.harkomst = harkomst
        problem = []
        _text(id, "id", problem)
        _text(vad, "vad", problem)
        if roll is not None:
            _text(roll, "roll", problem)
        if not isinstance(harkomst, Harkomst):
            problem.append("processen bar ingen harkomst; en process ingen "
                           "bett om ar en process vi hittat pa")
        if problem:
            raise Specfel("processen %r" % (id,), problem)

    def __repr__(self):
        return "Process(%s)" % self.id

    def rad(self):
        vem = " (%s)" % self.roll if self.roll else ""
        return "%s: %s%s [%s]" % (self.id, self.vad, vem, self.harkomst.text())

    def till_json(self):
        return {"id": self.id, "vad": self.vad, "roll": self.roll,
                "harkomst": self.harkomst.till_json()}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("id", "vad", "roll", "harkomst"), "process")
        return cls(data["id"], data["vad"], data["roll"],
                   Harkomst.fran_json(data["harkomst"]))


class Ordningskrav(object):
    """'fore' ska vara klar innan 'efter' far borja."""

    __slots__ = ("fore", "efter", "harkomst")

    def __init__(self, fore, efter, harkomst=None):
        self.fore = fore
        self.efter = efter
        self.harkomst = harkomst
        problem = []
        _text(fore, "fore", problem)
        _text(efter, "efter", problem)
        if not isinstance(harkomst, Harkomst):
            problem.append("ordningskravet bar ingen harkomst")
        if problem:
            raise Specfel("ordningskravet %s fore %s" % (fore, efter), problem)

    def __repr__(self):
        return "Ordningskrav(%s fore %s)" % (self.fore, self.efter)

    @property
    def id(self):
        return "ord:%s>%s" % (self.fore, self.efter)

    def rad(self):
        return "%s fore %s [%s]" % (self.fore, self.efter,
                                    self.harkomst.text())

    def till_json(self):
        return {"fore": self.fore, "efter": self.efter,
                "harkomst": self.harkomst.till_json()}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("fore", "efter", "harkomst"), "ordningskrav")
        return cls(data["fore"], data["efter"],
                   Harkomst.fran_json(data["harkomst"]))


def _nycklar(data, vantade, vad):
    if not isinstance(data, dict):
        raise Specfel(vad, ["forvantade ett objekt, fick %s"
                            % type(data).__name__])
    saknade = sorted(set(vantade) - set(data))
    okanda = sorted(set(data) - set(vantade))
    if saknade or okanda:
        raise Specfel(vad, ["nyckeln %r saknas" % n for n in saknade]
                      + ["okand nyckel %r" % n for n in okanda])
    return data


class Processordning(object):
    """Processerna och deras inbordes ordning, med samma cykelkrav som grafen."""

    __slots__ = ("processer", "krav")

    def __init__(self, processer=(), krav=()):
        self.processer = list(processer)
        self.krav = list(krav)
        problem = []
        for p in self.processer:
            if not isinstance(p, Process):
                problem.append("%r ar ingen Process" % (p,))
        for k in self.krav:
            if not isinstance(k, Ordningskrav):
                problem.append("%r ar inget Ordningskrav" % (k,))
        if problem:
            raise Specfel("processordningen", problem)

    def __len__(self):
        return len(self.processer)

    def __iter__(self):
        return iter(self.processer)

    def __repr__(self):
        return "Processordning(%d processer, %d ordningskrav)" % (
            len(self.processer), len(self.krav))

    def ids(self):
        return [p.id for p in self.processer]

    def process(self, id):
        for p in self.processer:
            if p.id == id:
                return p
        raise Specfel("processordningen", ["ingen process heter %r" % (id,)])

    # -- kanterna ---------------------------------------------------------

    def kanter(self, bara_kanda=True):
        """{process: de processer som ska vara klara fore den}."""
        kanda = set(self.ids())
        ut = dict((i, set()) for i in kanda)
        for k in self.krav:
            if k.efter not in ut:
                if bara_kanda:
                    continue
                ut.setdefault(k.efter, set())
            ut[k.efter].add(k.fore)
        if bara_kanda:
            return dict((n, tuple(sorted(b for b in v if b in kanda)))
                        for n, v in ut.items())
        return dict((n, tuple(sorted(v))) for n, v in ut.items())

    def cykler(self):
        """Varje ring, med sina processer. Samma rakning som uppgiftsgrafen."""
        return cykler(self.kanter())

    def ordning(self):
        """Den deterministiska ordningen. Kastar Graffel med cyklerna i sig.

        Kanoniskt val: minsta id bland de korbara. Samma bestallning ska ge
        samma processordning varje gang, annars gar tva korningar inte att
        jamfora (K20, samma regel som sekvenseraren).
        """
        problem = self.problem()
        hinder = [t for kod, t in problem
                  if kod in ("PO1_CYKEL", "PO2_OKAND_PROCESS",
                             "PO3_DUBBEL_PROCESS", "PO4_SJALVORDNING")]
        if hinder:
            raise Graffel(
                "processordningen gar inte att ordna: %s" % "; ".join(hinder),
                self.cykler())
        ordnade, kvar = kanonisk_ordning(self.kanter())
        if kvar:
            ringar = self.cykler()
            raise Graffel(
                "processordningen har %d cykel(er): %s"
                % (len(ringar), "; ".join(" -> ".join(c) for c in ringar)),
                ringar)
        return ordnade

    # -- granskningen -----------------------------------------------------

    def problem(self, roller=None):
        """[(lintkod, text)]. Tom lista = ordningen haller. Kastar aldrig."""
        ut = []
        sedda = {}
        for p in self.processer:
            sedda[p.id] = sedda.get(p.id, 0) + 1
        for id_ in sorted(sedda):
            if sedda[id_] > 1:
                ut.append(("PO3_DUBBEL_PROCESS",
                           "processen %r finns %d ganger; id ar namn"
                           % (id_, sedda[id_])))
        kanda = set(sedda)
        sedda_krav = set()
        for k in self.krav:
            if k.fore == k.efter:
                ut.append(("PO4_SJALVORDNING",
                           "%s ska ske fore sig sjalv" % k.fore))
            for sida, id_ in (("fore", k.fore), ("efter", k.efter)):
                if id_ not in kanda:
                    ut.append(("PO2_OKAND_PROCESS",
                               "ordningskravet %s pekar med %s pa %r, som inte "
                               "ar en process i specen; specen bar %s"
                               % (k.id, sida, id_,
                                  ", ".join(sorted(kanda)) or "inga processer")))
            if k.id in sedda_krav:
                ut.append(("PO6_DUBBELT_ORDNINGSKRAV",
                           "ordningskravet %s star mer an en gang" % k.id))
            sedda_krav.add(k.id)
        for ring in self.cykler():
            ut.append(("PO1_CYKEL",
                       "processerna %s bildar en ring: %s. En ordning som "
                       "gar tillbaka till sig sjalv gar inte att kora, och "
                       "vilka steg som bildar ringen ar hela svaret"
                       % (", ".join(ring),
                          " -> ".join(list(ring) + [ring[0]]))))
        if roller is not None:
            kanda_roller = set(roller)
            for p in self.processer:
                if p.roll is not None and p.roll not in kanda_roller:
                    ut.append(("PO5_OKAND_ROLL",
                               "processen %s utfors av rollen %r som inte finns "
                               "bland delarna (%s)"
                               % (p.id, p.roll,
                                  ", ".join(sorted(kanda_roller)) or "inga")))
        return ut

    def okanda_krav(self):
        return okanda_kanter(self.kanter(bara_kanda=False))

    # -- serialisering ----------------------------------------------------

    def till_json(self):
        return {"processer": [p.till_json() for p in self.processer],
                "krav": [k.till_json() for k in self.krav]}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("processer", "krav"), "processordning")
        return cls([Process.fran_json(p) for p in data["processer"]],
                   [Ordningskrav.fran_json(k) for k in data["krav"]])
