# -*- coding: utf-8 -*-
"""Specmodellen: tre nivaer som kan forfinas stegvis.

    GRUNDBEGARAN     operatorens korta text. Det enda som ar hans.
    DETALJERAD SPEC  vad som ska byggas: delar, matt, takt, signaler, villkor
    BYGGPLAN         en ordnad graf av steg (byggplan.py)

Har ligger de tva forsta. Byggplanen bor i byggplan.py darfor att den ocksa
maste kanna verktygsregistret, och en spec ska ga att skriva och lasa utan
att registret finns.

Den barande regeln, och skalet till att lagret finns:

    ALLT SOM INTE STAR I BEGARAN MEN BEHOVS BLIR ETT UTTALAT ANTAGANDE MED
    MOTIV, ELLER EN FRAGA TILL OPERATOREN. ALDRIG ETT TYST VAL.

Darfor bar en spec tva listor som inte gar att komma runt: antaganden och
fragor. Ett antagande utan motiv avvisas mekaniskt, och en obesvarad
blockerande fraga gor planen till en kandidat, aldrig en leverans.

Serialisering: varje niva har till_json()/fran_json() och lasningen ar STRIKT.
En okand nyckel avvisas i stallet for att ignoreras - annars kan ett faltnamn
bytas och en gammal fil las in halv, tyst.

Endast standardbiblioteket.
"""
from __future__ import annotations

from .fel import Specfel
from .harkomst import Harkomst
from .kallor import bankschema
from .processer import Processordning
from .verifiering import Verifieringskrav
from .villkorssprak import Prosakrav, Relation, Typvillkor, granska_roller

# Formatversionen. Hojs den ska lasaren falla pa en aldre fil i stallet for
# att gissa, precis som ogats "EYES v1" (docs/spec/41_ogat_kontrakt.md).
# Hojd fran 1 till 2 av M-63: specen bar nu omrade, typade villkor,
# relationer, processordning och prosakrav. En fil skriven i version 1 saknar
# de falten och ska falla pa versionen i stallet for att lasas halv.
SPECVERSION = 2   # formatversion, ingen troskel: hojd av M-63 nar specen fick fem nya falt

# Ett motiv kortare an sa har hinner inte saga VARFOR. Talet ags av
# bank/schema.py (MIN_MOTIV_TECKEN) och importeras darifran sa att ett
# antagande i banken och ett antagande i en spec haller samma matt.
MIN_MOTIV_TECKEN = bankschema.MIN_MOTIV_TECKEN

# Minsta antal oberoende korningar bakom ett rapporterat tal. I5 i
# docs/spec/90_invarianter.md: "Minst tre oberoende korningar ... med
# uppvarmning som inte raknas."
MIN_KORNINGAR = 3   # harkomst: I5 i docs/spec/90_invarianter.md, minst tre korningar

RIKTNINGAR = bankschema.SIGNALRIKTNINGAR      # ("in", "out")
SIGNALTYPER = bankschema.SIGNALTYPER          # ("bool", "int", "real")

# VILLKORSSORTER bor numera i villkorssprak.py, dar villkoret sjalvt bor.

# Varifran ett antagande kommer. Sluten lista, sa att en matning kan svara pa
# fragan "hur manga antaganden var vara egna och hur manga stod redan i
# uppgiften".
ANTAGANDEKALLOR = ("begaran", "bank", "katalog", "standard", "layout")


def _text(varde, falt, problem, minst=1):
    if not isinstance(varde, str) or len(varde.strip()) < minst:
        problem.append("%s: kravs text pa minst %d tecken, fick %r"
                       % (falt, minst, varde))
        return ""
    return varde


def _tal(varde, falt, problem, tillat_none=False, minst=None):
    if varde is None:
        if not tillat_none:
            problem.append("%s: talet saknas" % falt)
        return None
    if not isinstance(varde, (int, float)) or isinstance(varde, bool):
        problem.append("%s: %r ar inget tal" % (falt, varde))
        return None
    if minst is not None and varde < minst:
        problem.append("%s: %r ar under %r" % (falt, varde, minst))
    return varde


def granska_nycklar(data, vantade, vad):
    """Strikt nyckelkontroll. Okand nyckel avvisas, saknad nyckel avvisas."""
    if not isinstance(data, dict):
        raise Specfel(vad, ["forvantade ett objekt, fick %s"
                            % type(data).__name__])
    problem = []
    for n in sorted(set(vantade) - set(data)):
        problem.append("nyckeln %r saknas" % n)
    for n in sorted(set(data) - set(vantade)):
        problem.append("okand nyckel %r; kanda ar %s"
                       % (n, ", ".join(sorted(vantade))))
    if problem:
        raise Specfel(vad, problem)
    return data


# --------------------------------------------------------------- niva 1

class Grundbegaran(object):
    """Operatorens korta text, ordagrant, plus varifran den kom."""

    __slots__ = ("id", "text", "kalla")

    def __init__(self, id, text, kalla):
        self.id = id
        self.text = text
        self.kalla = kalla
        problem = []
        _text(id, "id", problem)
        _text(text, "text", problem)
        _text(kalla, "kalla", problem)
        if problem:
            raise Specfel("grundbegaran %r" % (id,), problem)

    def __repr__(self):
        return "Grundbegaran(%s, %d tecken)" % (self.id, len(self.text))

    def till_json(self):
        return {"v": SPECVERSION, "niva": "grundbegaran", "id": self.id,
                "text": self.text, "kalla": self.kalla}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("v", "niva", "id", "text", "kalla"), "grundbegaran")
        if data["v"] != SPECVERSION:
            raise Specfel("grundbegaran", ["formatversion %r, lasaren kan %d"
                                           % (data["v"], SPECVERSION)])
        if data["niva"] != "grundbegaran":
            raise Specfel("grundbegaran", ["niva %r, forvantade grundbegaran"
                                           % (data["niva"],)])
        return cls(data["id"], data["text"], data["kalla"])


# ------------------------------------------------------- vardeobjekt

class Antagande(object):
    """Ett val vi gjorde at operatoren, med skalet utskrivet.

    Ett antagande utan motiv ar precis den tysta nedgradering hela projektet
    ar byggt for att undvika, sa motivet ar ett formkrav och inte en artighet.
    """

    __slots__ = ("vad", "varde", "motiv", "kalla")

    def __init__(self, vad, varde, motiv, kalla):
        self.vad = vad
        self.varde = varde
        self.motiv = motiv
        self.kalla = kalla
        problem = []
        _text(vad, "vad", problem)
        _text(str(varde), "varde", problem)
        _text(motiv, "motiv", problem, minst=MIN_MOTIV_TECKEN)
        if kalla not in ANTAGANDEKALLOR:
            problem.append("kalla %r ar inte en av %s"
                           % (kalla, ", ".join(ANTAGANDEKALLOR)))
        if problem:
            raise Specfel("antagandet %r" % (vad,), problem)

    def __repr__(self):
        return "Antagande(%s = %s, %s)" % (self.vad, self.varde, self.kalla)

    def till_json(self):
        return {"vad": self.vad, "varde": self.varde, "motiv": self.motiv,
                "kalla": self.kalla}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("vad", "varde", "motiv", "kalla"), "antagande")
        return cls(data["vad"], data["varde"], data["motiv"], data["kalla"])


class Fraga(object):
    """Nagot som behovs och som vi inte far valja at operatoren.

    blockerar=True betyder att planen inte ar en leverans forran fragan ar
    besvarad. Det ar fail-closed: en obesvarad fraga ar aldrig ett tyst ja
    (I3).
    """

    __slots__ = ("id", "vad", "varfor", "blockerar", "svar")

    def __init__(self, id, vad, varfor, blockerar=True, svar=None):
        self.id = id
        self.vad = vad
        self.varfor = varfor
        self.blockerar = blockerar
        self.svar = svar
        problem = []
        _text(id, "id", problem)
        _text(vad, "vad", problem)
        _text(varfor, "varfor", problem, minst=MIN_MOTIV_TECKEN)
        if not isinstance(blockerar, bool):
            problem.append("blockerar %r ar inget booleskt varde" % (blockerar,))
        if svar is not None and not isinstance(svar, str):
            problem.append("svaret %r ar varken None eller text" % (svar,))
        if problem:
            raise Specfel("fragan %r" % (id,), problem)

    def __repr__(self):
        return "Fraga(%s, %s)" % (self.id, "besvarad" if self.svar else "oppen")

    @property
    def oppen(self):
        return self.svar is None

    def besvara(self, svar):
        """Operatorens svar. Ett tomt svar ar inget svar."""
        if not isinstance(svar, str) or not svar.strip():
            raise Specfel("fragan %s" % self.id, ["ett tomt svar ar inget svar"])
        self.svar = svar
        return self

    def till_json(self):
        return {"id": self.id, "vad": self.vad, "varfor": self.varfor,
                "blockerar": self.blockerar, "svar": self.svar}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("id", "vad", "varfor", "blockerar", "svar"), "fraga")
        return cls(data["id"], data["vad"], data["varfor"], data["blockerar"],
                   data["svar"])


class Del(object):
    """En komponent scenen ska bestå av, i sin roll.

    Rollen ar det namn resten av specen anvander. URI:n ar den enda vagen till
    en komponent: modellen valjer bara ur indexet (I9), sa den far aldrig
    hittas pa har heller.
    """

    __slots__ = ("roll", "uri", "antal", "kategori", "matt_mm", "massa_kg")

    def __init__(self, roll, uri, antal=1, kategori=None, matt_mm=None,
                 massa_kg=None):
        self.roll = roll
        self.uri = uri
        self.antal = antal
        self.kategori = kategori
        self.matt_mm = list(matt_mm) if matt_mm else None
        self.massa_kg = massa_kg
        problem = []
        _text(roll, "roll", problem)
        _text(uri, "uri", problem)
        if not isinstance(antal, int) or isinstance(antal, bool) or antal < 1:
            problem.append("antal %r maste vara ett heltal >= 1" % (antal,))
        if kategori is not None:
            _text(kategori, "kategori", problem)
        if self.matt_mm is not None:
            if len(self.matt_mm) != 3:
                problem.append("matt_mm ska vara tre tal l, b, h")
            else:
                for i, v in enumerate(self.matt_mm):
                    _tal(v, "matt_mm[%d]" % i, problem, minst=0)
        if massa_kg is not None:
            _tal(massa_kg, "massa_kg", problem, minst=0)
        if problem:
            raise Specfel("delen %r" % (roll,), problem)

    def __repr__(self):
        return "Del(%s, %s)" % (self.roll, self.uri)

    def till_json(self):
        return {"roll": self.roll, "uri": self.uri, "antal": self.antal,
                "kategori": self.kategori, "matt_mm": self.matt_mm,
                "massa_kg": self.massa_kg}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("roll", "uri", "antal", "kategori", "matt_mm",
                        "massa_kg"), "del")
        return cls(data["roll"], data["uri"], data["antal"], data["kategori"],
                   data["matt_mm"], data["massa_kg"])


class Koppling(object):
    """En relation mellan tva roller.

    Bar AVSIKTLIGT inga koordinater. I8: modellen anger relationer, aldrig
    koordinater; geometrin raknas av VC:s plug and play. Formen ar mekanisk:
    klassen har tva falt och lasningen avvisar varje annan nyckel, sa ett
    "position"-falt gar inte att smyga in i en kopplingspost.
    """

    __slots__ = ("fran_roll", "till_roll")

    def __init__(self, fran_roll, till_roll):
        self.fran_roll = fran_roll
        self.till_roll = till_roll
        problem = []
        _text(fran_roll, "fran_roll", problem)
        _text(till_roll, "till_roll", problem)
        if fran_roll == till_roll:
            problem.append("en roll kan inte kopplas till sig sjalv")
        if problem:
            raise Specfel("kopplingen %s->%s" % (fran_roll, till_roll), problem)

    def __repr__(self):
        return "Koppling(%s -> %s)" % (self.fran_roll, self.till_roll)

    def till_json(self):
        return {"fran_roll": self.fran_roll, "till_roll": self.till_roll}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("fran_roll", "till_roll"), "koppling")
        return cls(data["fran_roll"], data["till_roll"])


class Signal(object):
    """En signal i styrningens grannsnitt mot scenen."""

    __slots__ = ("namn", "riktning", "typ", "kommentar")

    def __init__(self, namn, riktning, typ, kommentar=""):
        self.namn = namn
        self.riktning = riktning
        self.typ = typ
        self.kommentar = kommentar
        problem = []
        _text(namn, "namn", problem)
        if riktning not in RIKTNINGAR:
            problem.append("riktning %r ar inte en av %s"
                           % (riktning, ", ".join(RIKTNINGAR)))
        if typ not in SIGNALTYPER:
            problem.append("typ %r ar inte en av %s"
                           % (typ, ", ".join(SIGNALTYPER)))
        if not isinstance(kommentar, str):
            problem.append("kommentaren ar ingen text")
        if problem:
            raise Specfel("signalen %r" % (namn,), problem)

    def __repr__(self):
        return "Signal(%s %s %s)" % (self.namn, self.riktning, self.typ)

    def till_json(self):
        return {"namn": self.namn, "riktning": self.riktning, "typ": self.typ,
                "kommentar": self.kommentar}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("namn", "riktning", "typ", "kommentar"), "signal")
        return cls(data["namn"], data["riktning"], data["typ"],
                   data["kommentar"])


class Takt(object):
    """Vad cellen ska hinna, och hur det ska matas.

    Minst ett av cykeltid och genomflode kravs; en takt utan tal ar ingen
    takt. Ett tidskrav utan tolerans avvisas (samma regel som bankens
    lintkod M10_TIMING_NO_TOLERANCE).
    """

    __slots__ = ("cykeltid_s", "tolerans_s", "genomflode_per_h", "korningar",
                 "uppvarmning_s")

    def __init__(self, cykeltid_s=None, tolerans_s=None, genomflode_per_h=None,
                 korningar=MIN_KORNINGAR, uppvarmning_s=0.0):
        self.cykeltid_s = cykeltid_s
        self.tolerans_s = tolerans_s
        self.genomflode_per_h = genomflode_per_h
        self.korningar = korningar
        self.uppvarmning_s = uppvarmning_s
        problem = []
        if cykeltid_s is None and genomflode_per_h is None:
            problem.append("varken cykeltid_s eller genomflode_per_h ar satt; "
                           "en takt utan tal ar ingen takt")
        _tal(cykeltid_s, "cykeltid_s", problem, tillat_none=True, minst=0)
        _tal(genomflode_per_h, "genomflode_per_h", problem, tillat_none=True,
             minst=0)
        _tal(uppvarmning_s, "uppvarmning_s", problem, minst=0)
        if cykeltid_s is not None and tolerans_s is None:
            problem.append("cykeltid utan tolerans_s; ett tidskrav utan "
                           "tolerans gar inte att prova")
        _tal(tolerans_s, "tolerans_s", problem, tillat_none=True, minst=0)
        if (not isinstance(korningar, int) or isinstance(korningar, bool)
                or korningar < MIN_KORNINGAR):
            problem.append("korningar %r; I5 kraver minst %d oberoende "
                           "korningar" % (korningar, MIN_KORNINGAR))
        if problem:
            raise Specfel("takten", problem)

    def __repr__(self):
        return "Takt(cykel=%s s, %s/h)" % (self.cykeltid_s,
                                           self.genomflode_per_h)

    def till_json(self):
        return {"cykeltid_s": self.cykeltid_s, "tolerans_s": self.tolerans_s,
                "genomflode_per_h": self.genomflode_per_h,
                "korningar": self.korningar,
                "uppvarmning_s": self.uppvarmning_s}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("cykeltid_s", "tolerans_s", "genomflode_per_h",
                        "korningar", "uppvarmning_s"), "takt")
        return cls(data["cykeltid_s"], data["tolerans_s"],
                   data["genomflode_per_h"], data["korningar"],
                   data["uppvarmning_s"])


class Omrade(object):
    """Ytan cellen far ta, och det minsta gangstraket i den.

    K11 i docs/spec/22_planeringslagret.md: `aisle_min_mm` har INGET forval.
    Saknas det ar det ett hart slot, och ett hart slot ar fail-closed (K2).
    Darfor ar gang_min_mm None tills nagon sagt vad det ska vara - aldrig noll,
    for noll gangstrak ar ett krav och inte en tystnad.

    Matten ar millimeter, som allt annat i VC (docs/spec/33_varldsenheten... se
    M-33). Bredd och djup ar golvets, hojden ar den fria hojden.
    """

    __slots__ = ("bredd_mm", "djup_mm", "hojd_mm", "gang_min_mm", "harkomst")

    def __init__(self, bredd_mm=None, djup_mm=None, hojd_mm=None,
                 gang_min_mm=None, harkomst=None):
        self.bredd_mm = bredd_mm
        self.djup_mm = djup_mm
        self.hojd_mm = hojd_mm
        self.gang_min_mm = gang_min_mm
        self.harkomst = harkomst
        problem = []
        for namn in ("bredd_mm", "djup_mm", "hojd_mm", "gang_min_mm"):
            _tal(getattr(self, namn), namn, problem, tillat_none=True, minst=0)
        if bredd_mm is None and djup_mm is None and hojd_mm is None:
            problem.append("ett omrade utan ett enda matt ar inget omrade; "
                           "lamna None i stallet")
        if not isinstance(harkomst, Harkomst):
            problem.append("omradet bar ingen harkomst; cellens matt styr hela "
                           "layouten och far inte komma fran ingenstans")
        if problem:
            raise Specfel("omradet", problem)

    def __repr__(self):
        return "Omrade(%s x %s mm)" % (self.bredd_mm, self.djup_mm)

    def rad(self):
        return ("omrade %s x %s mm, fri hojd %s mm, gangstrak %s mm [%s]"
                % (self.bredd_mm, self.djup_mm, self.hojd_mm,
                   self.gang_min_mm if self.gang_min_mm is not None
                   else "OKANT (hart slot, K11)", self.harkomst.text()))

    def till_json(self):
        return {"bredd_mm": self.bredd_mm, "djup_mm": self.djup_mm,
                "hojd_mm": self.hojd_mm, "gang_min_mm": self.gang_min_mm,
                "harkomst": self.harkomst.till_json()}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("bredd_mm", "djup_mm", "hojd_mm", "gang_min_mm",
                        "harkomst"), "omrade")
        return cls(data["bredd_mm"], data["djup_mm"], data["hojd_mm"],
                   data["gang_min_mm"], Harkomst.fran_json(data["harkomst"]))


# --------------------------------------------------------------- niva 2

class DetaljeradSpec(object):
    """Vad som ska byggas, med allt som behovs utskrivet.

    Barandet: specen bar sin egen grundbegaran, sa att man alltid kan lasa vad
    operatoren faktiskt bad om bredvid det vi gjorde av det. Och den bar
    antagandena och fragorna, sa att skillnaden mellan de tva gar att rakna.
    """

    __slots__ = ("id", "begaran", "delar", "kopplingar", "signaler", "takt",
                 "villkor", "antaganden", "fragor", "verifiering", "omrade",
                 "relationer", "processordning", "prosakrav")

    def __init__(self, id, begaran, delar=(), kopplingar=(), signaler=(),
                 takt=None, villkor=(), antaganden=(), fragor=(),
                 verifiering=None, omrade=None, relationer=(),
                 processordning=None, prosakrav=()):
        self.id = id
        self.begaran = begaran
        self.delar = list(delar)
        self.kopplingar = list(kopplingar)
        self.signaler = list(signaler)
        self.takt = takt
        self.villkor = list(villkor)
        self.antaganden = list(antaganden)
        self.fragor = list(fragor)
        self.verifiering = verifiering
        self.omrade = omrade
        self.relationer = list(relationer)
        self.processordning = (processordning if processordning is not None
                               else Processordning())
        self.prosakrav = list(prosakrav)
        self._granska()

    def _granska(self):
        problem = []
        _text(self.id, "id", problem)
        if not isinstance(self.begaran, Grundbegaran):
            problem.append("begaran saknas; en spec utan sin grundbegaran gar "
                           "inte att stalla mot det operatoren bad om")
        roller = [d.roll for d in self.delar]
        for roll in sorted(set(roller)):
            if roller.count(roll) > 1:
                problem.append("rollen %r finns %d ganger; roller ar namn"
                               % (roll, roller.count(roll)))
        for k in self.kopplingar:
            for roll in (k.fran_roll, k.till_roll):
                if roll not in roller:
                    problem.append("kopplingen %s->%s pekar pa rollen %r som "
                                   "inte finns bland delarna"
                                   % (k.fran_roll, k.till_roll, roll))
        namn = [s.namn for s in self.signaler]
        for n in sorted(set(namn)):
            if namn.count(n) > 1:
                problem.append("signalen %r deklareras %d ganger"
                               % (n, namn.count(n)))
        ids = [f.id for f in self.fragor]
        for n in sorted(set(ids)):
            if ids.count(n) > 1:
                problem.append("fragan %r finns %d ganger" % (n, ids.count(n)))
        if self.takt is not None and not isinstance(self.takt, Takt):
            problem.append("takt ar inte ett Takt-objekt")
        if (self.verifiering is not None
                and not isinstance(self.verifiering, Verifieringskrav)):
            problem.append("verifiering ar inte ett Verifieringskrav")
        if self.omrade is not None and not isinstance(self.omrade, Omrade):
            problem.append("omrade ar inget Omrade")
        for v in self.villkor:
            if not isinstance(v, Typvillkor):
                problem.append(
                    "%r ar inget Typvillkor. Villkorsspraket ar slutet (K6): "
                    "fri text i ett villkor ar ett lintfel, inte en varning"
                    % (v,))
        for r in self.relationer:
            if not isinstance(r, Relation):
                problem.append("%r ar ingen Relation" % (r,))
        for k in self.prosakrav:
            if not isinstance(k, Prosakrav):
                problem.append("%r ar inget Prosakrav" % (k,))
        if not isinstance(self.processordning, Processordning):
            problem.append("processordning ar ingen Processordning")
        # Roller ar namn, och ett krav som pekar pa ett namn som inte finns ar
        # ett skrivfel som annars upptacks forst i layouten.
        if not problem:
            problem += ["%s: %s" % p for p in granska_roller(
                self.villkor, self.relationer, roller)]
        if problem:
            raise Specfel("specen %r" % (self.id,), problem)

    def __repr__(self):
        return ("DetaljeradSpec(%s, %d delar, %d villkor, %d processer, "
                "%d antaganden, %d fragor)"
                % (self.id, len(self.delar), len(self.villkor),
                   len(self.processordning), len(self.antaganden),
                   len(self.fragor)))

    # -- fragor och antaganden ------------------------------------------

    def oppna_fragor(self):
        return [f for f in self.fragor if f.oppen]

    def blockerande_fragor(self):
        return [f for f in self.fragor if f.oppen and f.blockerar]

    def antaganden_per_kalla(self):
        ut = dict((k, 0) for k in ANTAGANDEKALLOR)
        for a in self.antaganden:
            ut[a.kalla] += 1
        return ut

    def roll(self, namn):
        for d in self.delar:
            if d.roll == namn:
                return d
        raise Specfel("specen %s" % self.id, ["ingen del har rollen %r" % (namn,)])

    # -- harkomsten -------------------------------------------------------

    def harkomster(self):
        """[(vad, Harkomst)] over varje krav specen bar.

        Listan ar det harkomstgrinden gar igenom. Star ett krav inte har kan
        det inte provas, sa varje ny kravsort maste laggas till bade i specen
        och har - och det ar avsiktligt samma stalle."""
        ut = []
        if self.omrade is not None:
            ut.append(("omradet", self.omrade.harkomst))
        for v in self.villkor:
            ut.append(("villkoret %s" % v.id, v.harkomst))
        for r in self.relationer:
            ut.append(("relationen %s" % r.id, r.harkomst))
        for k in self.prosakrav:
            ut.append(("prosakravet %s" % k.id, k.harkomst))
        for p in self.processordning.processer:
            ut.append(("processen %s" % p.id, p.harkomst))
        for k in self.processordning.krav:
            ut.append(("ordningskravet %s" % k.id, k.harkomst))
        return ut

    # -- serialisering ---------------------------------------------------

    def till_json(self):
        return {
            "v": SPECVERSION,
            "niva": "detaljerad_spec",
            "id": self.id,
            "begaran": self.begaran.till_json(),
            "delar": [d.till_json() for d in self.delar],
            "kopplingar": [k.till_json() for k in self.kopplingar],
            "signaler": [s.till_json() for s in self.signaler],
            "takt": self.takt.till_json() if self.takt else None,
            "villkor": [v.till_json() for v in self.villkor],
            "antaganden": [a.till_json() for a in self.antaganden],
            "fragor": [f.till_json() for f in self.fragor],
            "verifiering": (self.verifiering.till_json()
                            if self.verifiering else None),
            "omrade": self.omrade.till_json() if self.omrade else None,
            "relationer": [r.till_json() for r in self.relationer],
            "processordning": self.processordning.till_json(),
            "prosakrav": [k.till_json() for k in self.prosakrav],
        }

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("v", "niva", "id", "begaran", "delar", "kopplingar",
                        "signaler", "takt", "villkor", "antaganden", "fragor",
                        "verifiering", "omrade", "relationer",
                        "processordning", "prosakrav"), "detaljerad spec")
        if data["v"] != SPECVERSION:
            raise Specfel("detaljerad spec",
                          ["formatversion %r, lasaren kan %d"
                           % (data["v"], SPECVERSION)])
        if data["niva"] != "detaljerad_spec":
            raise Specfel("detaljerad spec",
                          ["niva %r, forvantade detaljerad_spec"
                           % (data["niva"],)])
        return cls(
            data["id"],
            Grundbegaran.fran_json(data["begaran"]),
            [Del.fran_json(d) for d in data["delar"]],
            [Koppling.fran_json(k) for k in data["kopplingar"]],
            [Signal.fran_json(s) for s in data["signaler"]],
            Takt.fran_json(data["takt"]) if data["takt"] else None,
            [Typvillkor.fran_json(v) for v in data["villkor"]],
            [Antagande.fran_json(a) for a in data["antaganden"]],
            [Fraga.fran_json(f) for f in data["fragor"]],
            (Verifieringskrav.fran_json(data["verifiering"])
             if data["verifiering"] else None),
            Omrade.fran_json(data["omrade"]) if data["omrade"] else None,
            [Relation.fran_json(r) for r in data["relationer"]],
            Processordning.fran_json(data["processordning"]),
            [Prosakrav.fran_json(k) for k in data["prosakrav"]],
        )
