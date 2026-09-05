# -*- coding: utf-8 -*-
"""Predikat: det sprak forvillkor och kontroller ar skrivna i.

Ett forvillkor ("steget kors bara om nagot galler") och en kontroll ("det har
maste galla") ar samma fraga stalld pa tva stallen, sa de delar ett sprak:

    resultat   ett varde ur ett TIDIGARE stegs svar, pa en vag genom svaret
    status     hur det gick for ett tidigare steg
    fakta      nagot koraren fick veta utifran, till exempel en ogonrapport

Tre egenskaper ar krav, inte bekvamligheter:

1. Ett predikat SVARAR ALLTID med ett skal. Ett steg som hoppades over utan
   att protokollet sager varfor ar en tyst nedgradering.
2. Ett predikat KASTAR ALDRIG vid utvardering. En saknad nyckel ar falskt med
   ett skal, inte ett undantag. S10 i 96_ingen_skuld.md: en rapport far aldrig
   kunna falla domaren.
3. En vag gar att prova MOT VERKTYGETS returns-SCHEMA redan vid planeringen.
   Ett predikat som laser en nyckel verktyget aldrig svarar med ar ett fel i
   planen, och ska falla dar - inte i korningen.
"""
from __future__ import annotations

from .fel import Specfel

# Hur det gick for ett steg. Sluten lista; koraren satter dem.
STATUSAR = ("kord", "hoppad", "fallen", "koad", "ej_utford")

# Sluten operatortabell. Allt som inte gar att prova mekaniskt hor inte hemma
# i ett forvillkor.
OPERATORER = ("==", "!=", "<", "<=", ">", ">=", "finns", "saknas")

# Operatorer som jamfor storlek. De kraver tal pa bada sidor; ett strangvarde
# skulle annars jamforas alfabetiskt och se ut att fungera.
_ORDNINGSOPERATORER = ("<", "<=", ">", ">=")

# Operatorer som inte tar nagot varde alls.
_UTAN_VARDE = ("finns", "saknas")

SORTER = ("resultat", "status", "fakta")


# ------------------------------------------------------------------ vagar

def dela_vag(vag):
    """'interfaces.0.name' -> ['interfaces', 0, 'name']."""
    delar = []
    for bit in str(vag).split("."):
        if bit == "":
            raise Specfel("the path %r" % (vag,), ["empty segment in the path"])
        delar.append(int(bit) if bit.isdigit() else bit)
    if not delar:
        raise Specfel("the path %r" % (vag,), ["the path is empty"])
    return delar


def las_vag(varde, vag):
    """(finns, varde). Kastar aldrig; en saknad vag ar (False, None)."""
    try:
        delar = dela_vag(vag)
    except Specfel:
        return False, None
    aktuellt = varde
    for del_ in delar:
        if isinstance(del_, int):
            if not isinstance(aktuellt, list) or del_ >= len(aktuellt):
                return False, None
            aktuellt = aktuellt[del_]
        else:
            if not isinstance(aktuellt, dict) or del_ not in aktuellt:
                return False, None
            aktuellt = aktuellt[del_]
    return True, aktuellt


def granska_vag(returns_schema, vag):
    """None om vagen finns i schemat, annars ett felmeddelande.

    Detta ar hela poangen med att verktygen bar ett returns-schema: en plan
    som laser 'interfaces.0.namn' i stallet for '.name' ska falla vid
    planeringen, inte vid korningen.
    """
    try:
        delar = dela_vag(vag)
    except Specfel as fel:
        return str(fel)
    schema = returns_schema
    gangen = []
    for del_ in delar:
        gangen.append(str(del_))
        if isinstance(del_, int):
            if _typer(schema) != ["array"] or "items" not in schema:
                return ("vagen %r: %s ar ingen lista i verktygets returns"
                        % (vag, ".".join(gangen[:-1]) or "svaret"))
            schema = schema["items"]
            continue
        egenskaper = schema.get("properties")
        if not isinstance(egenskaper, dict):
            return ("vagen %r: %s ar inget objekt i verktygets returns"
                    % (vag, ".".join(gangen[:-1]) or "svaret"))
        if del_ not in egenskaper:
            return ("vagen %r: verktyget svarar aldrig med %r; det svarar med %s"
                    % (vag, del_, ", ".join(sorted(egenskaper))))
        schema = egenskaper[del_]
    return None


def typ_pa_vag(returns_schema, vag):
    """Typen vagen leder till, eller None om vagen inte finns.

    Anvands for att prova en bindnings deklarerade typ mot verkligheten.
    """
    if granska_vag(returns_schema, vag) is not None:
        return None
    schema = returns_schema
    for del_ in dela_vag(vag):
        schema = schema["items"] if isinstance(del_, int) else schema["properties"][del_]
    typer = _typer(schema)
    return typer[0] if typer else None


def _typer(schema):
    if not isinstance(schema, dict) or "type" not in schema:
        return []
    typ = schema["type"]
    return list(typ) if isinstance(typ, list) else [typ]


# --------------------------------------------------------------- tillstand

class Korlage(object):
    """Vad koraren vet just nu. Det predikaten laser, och inget mer."""

    __slots__ = ("resultat", "statusar", "fakta", "bindningar")

    def __init__(self, resultat=None, statusar=None, fakta=None,
                 bindningar=None):
        self.resultat = dict(resultat or {})      # steg_id -> svar (dict)
        self.statusar = dict(statusar or {})      # steg_id -> status
        self.fakta = dict(fakta or {})            # nyckel -> varde
        self.bindningar = dict(bindningar or {})  # namn -> varde

    def __repr__(self):
        return "Korlage(%d resultat, %d fakta, %d bindningar)" % (
            len(self.resultat), len(self.fakta), len(self.bindningar))


# --------------------------------------------------------------- predikat

class Predikat(object):
    """En fraga med ett ja, ett nej och ALLTID ett skal."""

    __slots__ = ("sort", "steg", "vag", "nyckel", "operator", "varde", "status")

    def __init__(self, sort, steg=None, vag=None, nyckel=None, operator=None,
                 varde=None, status=None):
        self.sort = sort
        self.steg = steg
        self.vag = vag
        self.nyckel = nyckel
        self.operator = operator
        self.varde = varde
        self.status = status
        problem = []
        if sort not in SORTER:
            raise Specfel("the predicate", ["unknown kind %r; known are %s"
                                         % (sort, ", ".join(SORTER))])
        if sort == "resultat":
            if not steg:
                problem.append("resultat kraver steg")
            if not vag:
                problem.append("resultat kraver vag")
            problem += self._granska_operator()
            if nyckel is not None or status is not None:
                problem.append("resultat tar varken nyckel eller status")
        elif sort == "status":
            if not steg:
                problem.append("status kraver steg")
            if status not in STATUSAR:
                problem.append("okand status %r; kanda ar %s"
                               % (status, ", ".join(STATUSAR)))
            if vag is not None or nyckel is not None or operator is not None:
                problem.append("status tar bara steg och status")
        else:
            if not nyckel:
                problem.append("fakta kraver nyckel")
            problem += self._granska_operator()
            if steg is not None or vag is not None or status is not None:
                problem.append("fakta tar bara nyckel, operator och varde")
        if problem:
            raise Specfel("the predicate %r" % (sort,), problem)

    def _granska_operator(self):
        problem = []
        if self.operator not in OPERATORER:
            problem.append("okand operator %r; kanda ar %s"
                           % (self.operator, ", ".join(OPERATORER)))
            return problem
        if self.operator in _UTAN_VARDE and self.varde is not None:
            problem.append("%r tar inget varde" % self.operator)
        if self.operator in _ORDNINGSOPERATORER and not _ar_tal(self.varde):
            problem.append("%r kraver ett tal att jamfora med, fick %r"
                           % (self.operator, self.varde))
        return problem

    def __repr__(self):
        if self.sort == "status":
            return "Predikat(%s %s == %s)" % (self.sort, self.steg, self.status)
        mal = "%s.%s" % (self.steg, self.vag) if self.sort == "resultat" else self.nyckel
        return "Predikat(%s %s %s %r)" % (self.sort, mal, self.operator, self.varde)

    def text(self):
        return repr(self)[9:-1]

    def berorda_steg(self):
        return (self.steg,) if self.steg else ()

    # -- utvardering ------------------------------------------------------

    def prova(self, lage):
        """(sant, skal). Kastar aldrig."""
        if self.sort == "status":
            har = lage.statusar.get(self.steg)
            if har is None:
                return False, ("steget %s har inget utfall an" % self.steg)
            return (har == self.status,
                    "steget %s ar %s, kravet var %s" % (self.steg, har, self.status))
        if self.sort == "resultat":
            svar = lage.resultat.get(self.steg)
            if svar is None:
                return False, "steget %s har inget svar an" % self.steg
            finns, varde = las_vag(svar, self.vag)
            return self._jamfor(finns, varde, "%s.%s" % (self.steg, self.vag))
        finns = self.nyckel in lage.fakta
        varde = lage.fakta.get(self.nyckel)
        return self._jamfor(finns, varde, "faktumet %s" % self.nyckel)

    def _jamfor(self, finns, varde, vad):
        if self.operator == "finns":
            return finns, "%s %s" % (vad, "finns" if finns else "saknas")
        if self.operator == "saknas":
            return not finns, "%s %s" % (vad, "finns" if finns else "saknas")
        if not finns:
            return False, "%s finns inte i svaret" % vad
        if self.operator == "==":
            return varde == self.varde, "%s = %r, kravet var %r" % (vad, varde, self.varde)
        if self.operator == "!=":
            return varde != self.varde, "%s = %r, fick inte vara %r" % (vad, varde, self.varde)
        if not _ar_tal(varde):
            return False, ("%s = %r ar inget tal och gar inte att jamfora med %s"
                           % (vad, varde, self.operator))
        utfall = {"<": varde < self.varde, "<=": varde <= self.varde,
                  ">": varde > self.varde, ">=": varde >= self.varde}[self.operator]
        return utfall, "%s = %r %s %r" % (vad, varde, self.operator, self.varde)

    # -- serialisering ----------------------------------------------------

    def till_json(self):
        return {"sort": self.sort, "steg": self.steg, "vag": self.vag,
                "nyckel": self.nyckel, "operator": self.operator,
                "varde": self.varde, "status": self.status}

    @classmethod
    def fran_json(cls, data):
        vantade = ("sort", "steg", "vag", "nyckel", "operator", "varde", "status")
        if not isinstance(data, dict) or set(data) != set(vantade):
            raise Specfel("predicate", ["expected exactly the keys %s, got %s"
                                       % (", ".join(sorted(vantade)),
                                          ", ".join(sorted(data)) if isinstance(data, dict)
                                          else type(data).__name__)])
        return cls(data["sort"], data["steg"], data["vag"], data["nyckel"],
                   data["operator"], data["varde"], data["status"])


def _ar_tal(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# -------------------------------------------------------------- forvillkor

SAMMANSATTNINGAR = ("alla", "nagot")


class Forvillkor(object):
    """Villkoret for att ett steg ska koras alls.

    Ett steg vars forvillkor inte haller HOPPAS OVER med skal - det faller
    inte. Skillnaden ar hela poangen: ett hoppat steg ar ett medvetet val i
    planen, ett fallet steg ar ett fel.
    """

    __slots__ = ("predikat", "sammansattning")

    def __init__(self, predikat=(), sammansattning="alla"):
        self.predikat = list(predikat)
        self.sammansattning = sammansattning
        problem = []
        if sammansattning not in SAMMANSATTNINGAR:
            problem.append("okand sammansattning %r; kanda ar %s"
                           % (sammansattning, ", ".join(SAMMANSATTNINGAR)))
        if not self.predikat:
            problem.append("ett forvillkor utan predikat ar inget villkor")
        for p in self.predikat:
            if not isinstance(p, Predikat):
                problem.append("%r ar inget Predikat" % (p,))
        if problem:
            raise Specfel("the precondition", problem)

    def __repr__(self):
        return "Forvillkor(%s av %d)" % (self.sammansattning, len(self.predikat))

    def berorda_steg(self):
        ut = []
        for p in self.predikat:
            ut.extend(p.berorda_steg())
        return tuple(sorted(set(ut)))

    def prova(self, lage):
        """(sant, skal). Skalet namner varje predikat, aven de som holl."""
        utfall = [(p, ) + p.prova(lage) for p in self.predikat]
        sanna = [u for u in utfall if u[1]]
        skal = "; ".join(u[2] for u in utfall)
        if self.sammansattning == "alla":
            return len(sanna) == len(utfall), skal
        return bool(sanna), skal

    def till_json(self):
        return {"sammansattning": self.sammansattning,
                "predikat": [p.till_json() for p in self.predikat]}

    @classmethod
    def fran_json(cls, data):
        if not isinstance(data, dict) or set(data) != {"sammansattning", "predikat"}:
            raise Specfel("precondition", ["expected the keys sammansattning "
                                         "and predikat"])
        return cls([Predikat.fran_json(p) for p in data["predikat"]],
                   data["sammansattning"])
