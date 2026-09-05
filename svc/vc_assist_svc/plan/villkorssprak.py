# -*- coding: utf-8 -*-
"""Villkorsspraket: ett krav pa cellen, i en form som gar att prova.

K6 i docs/spec/22_planeringslagret.md, ordagrant: "Villkorsspraket ar slutet.
Ett villkor ar en trippel {lhs, op, rhs} dar lhs ar en namngiven storhet ur en
sluten lista ... Fri text i ett villkor ar ett lintfel, inte en varning."

VAD SOM STOD HAR FORE

spec.Villkor bar (id, sort, text) dar text var ren prosa: "hogst 0 kollisioner
i cellen", "minsta fria avstand 12.0 mm". MATT i M-63: noll rader kod i hela
repot laste den texten. Fältet var alltsa skrivet men aldrig last - exakt den
felklass specen sjalv kallar PL5 (efterkontroll utan konsument) och som den
skrev in i kravlistan efter att ha hittat den i KALLPROJEKTET. Vi hade den
sjalva, i vart eget planeringslager, i samma fil som beskrev regeln.

TRE FORMER, OCH VAR OCH EN BAR SIN HARKOMST

    Typvillkor  {storhet, operator, varde} - ett tal eller ett lage som gar
                att lasa ur ett faktarum och jamfora. Det har ar det som en
                motsagelsegrind kan rakna pa.
    Relation    en typad relation mellan tva roller: "roboten ska NA pallen".
                Formen ar kallans egen (Relation i multimodal/types.py, listad
                i 22_planeringslagret.md §2) och den avgors GEOMETRISKT, av
                layoutmotorn, aldrig av en text.
    Prosakrav   ett krav som INTE gar att uttrycka i de tva forsta, med en
                utskriven KONSUMENT: vem provar det, och nar. Ett prosakrav
                utan konsument ar samma dodkott som spec.Villkor.text var, och
                avvisas darfor vid konstruktionen.

Det tredje ar det arliga i konstruktionen. Bankens forreglingar ("ingen
robotrorelse nar EMG_OK ar lag", 125 stycken over 51 uppgifter) ar aktta krav
som spraket i K6 inte kan uttrycka - de ar en VILLKORAD FORBUD, inte en
jamforelse. Att tvinga in dem i en trippel hade gett falska triplar. Att kasta
dem hade tappat krav. De far darfor en egen form med en namngiven konsument:
grind 3 och ST-lagret, som redan provar dem.

Endast standardbiblioteket.
"""
from __future__ import annotations

from .fel import Specfel
from .harkomst import Harkomst
from .storheter import Faktarum, granska_namn, lage

# Operatorerna ur K6, ordagrant och inte fler.
OPERATORER = ("eq", "ne", "lt", "le", "gt", "ge", "in", "exists")

# Operatorer som kraver tal pa bada sidor. En storleksjamforelse mellan
# stringar ser ut att fungera och jamfor alfabetiskt (samma falla som
# predikat._ORDNINGSOPERATORER).
_ORDNINGSOPERATORER = ("lt", "le", "gt", "ge")

# Vad villkoret handlar om. Sluten lista, oforandrad fran spec.py: en sort som
# inte gar att prova mot nagot hor inte hemma i en spec.
VILLKORSSORTER = ("forregling", "geometri", "kapacitet", "sakerhet", "ordning")

# Relationstyperna ur 22_planeringslagret.md §2, plus en:
#
#   nar   "A ska na B" - rackviddskravet. Det star inte i specens lista, och
#         det ar en LUCKA i specen och inte i koden: uppgiften som stanger
#         fas 16 namner "roboten ska na bade bandet och pallplatsen" som sitt
#         exempel pa ett villkor som kan vara omojligt. Utan en relationstyp
#         for det hade kravet blivit prosa. Forslaget till specen star i M-63.
RELATIONSSORTER = ("on_top_of", "above", "inside", "contains", "supports",
                   "beside", "feeds", "handoff", "sequence", "nar")

# Relationer som INTE avgors av geometrin utan av planens ordning och ogats
# tidsserie (K8, samma gradering som kallans static_eyes.py:419).
SEMANTISKA_RELATIONER = ("feeds", "handoff", "sequence")

UPPFYLLT = "uppfyllt"
BRUTET = "brutet"
OKANT = "okant"

LINTKODER = {
    "VS1_PROSAVILLKOR": "villkoret ar fri text och gar inte att utvardera",
    "VS2_OKAND_STORHET": "vansterledet ar ingen storhet i det slutna spraket",
    "VS3_OKAND_OPERATOR": "operatorn star inte i K6:s lista",
    "VS4_VARDE_UTAN_TAL": "en storleksjamforelse utan tal jamfor alfabetiskt",
    "VS5_PROSAKRAV_UTAN_KONSUMENT": "prosakravet namner ingen som provar det",
    "VS6_OKAND_ROLL": "relationen pekar pa en roll som inte finns bland delarna",
    "VS7_OKAND_RELATION": "relationssorten star inte i den slutna listan",
}


def _text(varde, falt, problem, minst=1):
    if not isinstance(varde, str) or len(varde.strip()) < minst:
        problem.append("%s: kravs text pa minst %d tecken, fick %r"
                       % (falt, minst, varde))


def _ar_tal(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Typvillkor(object):
    """Ett krav pa cellen som gar att lasa ur ett faktarum och jamfora."""

    __slots__ = ("id", "sort", "storhet", "operator", "varde", "harkomst",
                 "text_")

    def __init__(self, id, sort, storhet, operator, varde=None, harkomst=None,
                 text=""):
        self.id = id
        self.sort = sort
        self.storhet = storhet
        self.operator = operator
        self.varde = varde
        self.harkomst = harkomst
        self.text_ = text
        problem = []
        _text(id, "id", problem)
        if sort not in VILLKORSSORTER:
            problem.append("sorten %r ar inte en av %s"
                           % (sort, ", ".join(VILLKORSSORTER)))
        fel = granska_namn(storhet)
        if fel:
            problem.append("VS2_OKAND_STORHET: %s" % fel)
        if operator not in OPERATORER:
            problem.append("VS3_OKAND_OPERATOR: okand operator %r; K6 tillater "
                           "%s" % (operator, ", ".join(OPERATORER)))
        else:
            problem += self._granska_varde()
        if not isinstance(harkomst, Harkomst):
            problem.append("villkoret bar ingen harkomst; ett krav ingen kan "
                           "spara till begaran eller till ett markt antagande "
                           "ar ett krav vi hittat pa")
        if not isinstance(self.text_, str):
            problem.append("text ska vara en manniskolaslig omskrivning, "
                           "aldrig sjalva kravet")
        if problem:
            raise Specfel("the requirement %r" % (id,), problem)

    def _granska_varde(self):
        problem = []
        if self.operator == "exists":
            if self.varde is not None:
                problem.append("exists tar inget varde")
            return problem
        if self.operator == "in":
            if not isinstance(self.varde, (list, tuple)) or not self.varde:
                problem.append("in kraver en icke-tom lista, fick %r"
                               % (self.varde,))
            return problem
        if self.operator in _ORDNINGSOPERATORER and not _ar_tal(self.varde):
            problem.append("VS4_VARDE_UTAN_TAL: %r kraver ett tal att jamfora "
                           "med, fick %r" % (self.operator, self.varde))
            return problem
        if not _ar_tal(self.varde) and not isinstance(self.varde, (str, bool)):
            problem.append("hogerledet ar %r; K6 tillater ett tal, en strang "
                           "eller en lista" % (self.varde,))
        return problem

    def __repr__(self):
        return "Typvillkor(%s: %s)" % (self.id, self.uttryck())

    def uttryck(self):
        """Kravet som en rad, i spraket sjalvt."""
        if self.operator == "exists":
            return "%s exists" % self.storhet
        return "%s %s %r" % (self.storhet, self.operator, self.varde)

    def rad(self):
        """Raden operatoren far se: kravet, dess harkomst och ev. omskrivning."""
        delar = [self.uttryck()]
        if self.text_:
            delar.append("(%s)" % self.text_)
        delar.append("[%s]" % self.harkomst.text())
        return "%s: %s" % (self.id, " ".join(delar))

    @property
    def lage(self):
        """Om kravet gar att prova statiskt eller forst i en matt scen."""
        return lage(self.storhet)

    # -- provningen -------------------------------------------------------

    def prova(self, faktarum):
        """(dom, skal). dom ar uppfyllt, brutet eller OKANT. Kastar aldrig.

        OKANT ar aldrig ett godkannande (I3). Kallprojektets stubbar svarade
        `pass` nar argumentet saknades; det arvs inte.
        """
        if not isinstance(faktarum, Faktarum):
            return OKANT, "inget faktarum att lasa %s ur" % self.storhet
        varde = faktarum.las(self.storhet)
        if self.operator == "exists":
            return ((UPPFYLLT if varde.kant else BRUTET),
                    "%s %s" % (self.storhet,
                               "finns: %s" % varde.text() if varde.kant
                               else "saknas: %s" % varde.skal))
        if not varde.kant:
            return OKANT, "%s ar okand: %s" % (self.storhet, varde.skal)
        if self.operator == "in":
            haller = varde.tal in list(self.varde)
            return ((UPPFYLLT if haller else BRUTET),
                    "%s = %s, kravet var en av %r"
                    % (self.storhet, varde.text(), list(self.varde)))
        if self.operator in ("eq", "ne"):
            lika = varde.tal == self.varde
            haller = lika if self.operator == "eq" else not lika
            return ((UPPFYLLT if haller else BRUTET),
                    "%s = %s, kravet var %s %r"
                    % (self.storhet, varde.text(), self.operator, self.varde))
        utfall = {"lt": varde.tal < self.varde, "le": varde.tal <= self.varde,
                  "gt": varde.tal > self.varde,
                  "ge": varde.tal >= self.varde}[self.operator]
        return ((UPPFYLLT if utfall else BRUTET),
                "%s = %s, kravet var %s %g %s"
                % (self.storhet, varde.text(), self.operator, self.varde,
                   varde.enhet))

    # -- serialisering ----------------------------------------------------

    def till_json(self):
        return {"id": self.id, "sort": self.sort, "storhet": self.storhet,
                "operator": self.operator,
                "varde": (list(self.varde) if isinstance(self.varde, tuple)
                          else self.varde),
                "harkomst": self.harkomst.till_json(), "text": self.text_}

    @classmethod
    def fran_json(cls, data):
        vantade = ("id", "sort", "storhet", "operator", "varde", "harkomst",
                   "text")
        _nycklar(data, vantade, "villkor")
        return cls(data["id"], data["sort"], data["storhet"], data["operator"],
                   data["varde"], Harkomst.fran_json(data["harkomst"]),
                   data["text"])


class Relation(object):
    """En typad relation mellan tva roller. Geometrin avgors av layouten."""

    __slots__ = ("sort", "fran_roll", "till_roll", "harkomst", "hard")

    def __init__(self, sort, fran_roll, till_roll, harkomst=None, hard=True):
        self.sort = sort
        self.fran_roll = fran_roll
        self.till_roll = till_roll
        self.harkomst = harkomst
        self.hard = bool(hard)
        problem = []
        if sort not in RELATIONSSORTER:
            problem.append("VS7_OKAND_RELATION: %r ar ingen relationssort; "
                           "kanda ar %s" % (sort, ", ".join(RELATIONSSORTER)))
        _text(fran_roll, "fran_roll", problem)
        _text(till_roll, "till_roll", problem)
        if fran_roll == till_roll:
            problem.append("en roll kan inte sta i relation till sig sjalv")
        if not isinstance(harkomst, Harkomst):
            problem.append("relationen bar ingen harkomst")
        if problem:
            raise Specfel("the relation %s %s %s" % (fran_roll, sort, till_roll),
                          problem)

    def __repr__(self):
        return "Relation(%s %s %s)" % (self.fran_roll, self.sort,
                                       self.till_roll)

    @property
    def id(self):
        return "rel:%s:%s:%s" % (self.sort, self.fran_roll, self.till_roll)

    @property
    def semantisk(self):
        """Sant for relationer ogat och planens ordning domer, inte geometrin."""
        return self.sort in SEMANTISKA_RELATIONER

    def rad(self):
        return "%s: %s %s %s [%s]" % (self.id, self.fran_roll, self.sort,
                                      self.till_roll, self.harkomst.text())

    def till_json(self):
        return {"sort": self.sort, "fran_roll": self.fran_roll,
                "till_roll": self.till_roll,
                "harkomst": self.harkomst.till_json(), "hard": self.hard}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("sort", "fran_roll", "till_roll", "harkomst", "hard"),
                 "relation")
        return cls(data["sort"], data["fran_roll"], data["till_roll"],
                   Harkomst.fran_json(data["harkomst"]), data["hard"])


class Prosakrav(object):
    """Ett krav som spraket inte kan uttrycka, med en NAMNGIVEN konsument.

    Formen finns for att ingenting ska tappas bort. Ett krav som inte gar att
    typa far skjutas vidare, men inte tyst: konsumenten sager vem som provar
    det och var. Samma disciplin som verifiering.Uppskjutet har for ogats
    krav - ett uppskjutet krav ar synligt, ett bortglomt ar det inte.
    """

    __slots__ = ("id", "sort", "text", "konsument", "harkomst")

    def __init__(self, id, sort, text, konsument, harkomst=None):
        self.id = id
        self.sort = sort
        self.text = text
        self.konsument = konsument
        self.harkomst = harkomst
        problem = []
        _text(id, "id", problem)
        _text(text, "text", problem)
        if sort not in VILLKORSSORTER:
            problem.append("sorten %r ar inte en av %s"
                           % (sort, ", ".join(VILLKORSSORTER)))
        if not isinstance(konsument, str) or len(konsument.strip()) < 8:
            problem.append(
                "VS5_PROSAKRAV_UTAN_KONSUMENT: konsumenten maste namna VEM som "
                "provar kravet och VAR. Ett prosakrav utan konsument ar en "
                "efterkontroll utan konsument (PL5), och den felklassen skrevs "
                "in i specen efter att den hittats i kallprojektet")
        if not isinstance(harkomst, Harkomst):
            problem.append("prosakravet bar ingen harkomst")
        if problem:
            raise Specfel("the prose requirement %r" % (id,), problem)

    def __repr__(self):
        return "Prosakrav(%s -> %s)" % (self.id, self.konsument)

    def rad(self):
        return "%s: %s [provas av %s] [%s]" % (self.id, self.text,
                                               self.konsument,
                                               self.harkomst.text())

    def till_json(self):
        return {"id": self.id, "sort": self.sort, "text": self.text,
                "konsument": self.konsument,
                "harkomst": self.harkomst.till_json()}

    @classmethod
    def fran_json(cls, data):
        _nycklar(data, ("id", "sort", "text", "konsument", "harkomst"),
                 "prosakrav")
        return cls(data["id"], data["sort"], data["text"], data["konsument"],
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


def granska_roller(villkor, relationer, roller):
    """[(lintkod, text)] for krav som pekar pa roller som inte finns."""
    ut = []
    kanda = set(roller)
    from .storheter import rollen_i, rollparet_i
    for v in villkor:
        roll = rollen_i(v.storhet)
        if roll is not None and roll not in kanda:
            ut.append(("VS6_OKAND_ROLL",
                       "villkoret %s handlar om rollen %r som inte finns bland "
                       "delarna (%s)" % (v.id, roll,
                                         ", ".join(sorted(kanda)) or "inga")))
        par = rollparet_i(v.storhet)
        for r in (par or ()):
            if r not in kanda:
                ut.append(("VS6_OKAND_ROLL",
                           "villkoret %s mater avstandet till rollen %r som "
                           "inte finns bland delarna" % (v.id, r)))
    for r in relationer:
        for roll in (r.fran_roll, r.till_roll):
            if roll not in kanda:
                ut.append(("VS6_OKAND_ROLL",
                           "relationen %s pekar pa rollen %r som inte finns "
                           "bland delarna" % (r.id, roll)))
    return ut
