# -*- coding: utf-8 -*-
"""Ett steg i byggplanen: ett verktygsanrop eller en kontroll.

Tva sorter, och ingen tredje:

    verktyg    ett anrop i det befintliga registret (svc/vc_assist_svc/verktyg)
    kontroll   nagot som ska GALLA, eller ett varde som ska HAMTAS ur tidigare
               svar innan nasta steg kan skrivas

ROUTINGEN AGS AV UTFORAREN. Ett steg bar verktygets NAMN och ARGUMENT, aldrig
ett exekveringslage. Det ar inte en overenskommelse utan en form: klassen har
inget falt for det, och lasningen avvisar uttryckligen nycklarna 'op',
'effect', 'exec' och 'exec_queue' med hanvisning till I12. Planen KAN darfor
inte valja ko eller direktkorning ens av misstag.

BINDNINGAR loser det som annars hade blivit ett tyst pahitt. Ett gransnittsnamn
star sallan i begaran, och I9 forbjuder att modellen hittar pa ett. I stallet
lases det UR SCENEN: ett steg hamtar komponentens gransnittslista, en kontroll
valjer paret enligt en regel ur en sluten tabell, och kopplingssteget far
vardet genom en bindning. En bindning bar sin typ, sa argumenten kan provas
mot verktygets schema redan vid planeringen med ett vittnesvarde - samma
grepp som banken anvander for att prova en facitmall mot ogats grammatik.
"""
from __future__ import annotations

from .fel import Specfel
from .predikat import Forvillkor, Korlage, OPERATORER, Predikat

# Typerna en bindning kan bara. Samma namn som JSON-schemats, sa att en
# bindnings typ gar att stalla mot verktygets returns utan oversattning.
BINDNINGSTYPER = ("string", "integer", "number", "boolean")

# Ett vittnesvarde per typ: nagot att prova argumenten med vid planeringen,
# innan det verkliga vardet finns. Vardena ar avsiktligt intetsagande - de ska
# aldrig na VC, och gor det inte heller: koraren byter ut dem mot det lasta
# vardet innan utforaren anropas, och utforaren validerar om.
_VITTNEN = {"string": "vittne", "integer": 1, "number": 1.0, "boolean": True}

# Nycklar som skulle betyda att planen valde exekveringslage. I12: regeln
# effect -> exec / exec_queue ar mekanisk och ags av utforaren.
FORBJUDNA_STEGNYCKLAR = ("op", "effect", "exec", "exec_queue", "lage", "ko")

KONTROLLSORTER = ("villkor", "bindning", "oga")
STEGSORTER = ("verktyg", "kontroll")

# Operatorer i en efterkontroll som jamfor storlek. De kraver tal pa bada
# sidor; ett strangvarde skulle annars jamforas alfabetiskt och se ut att
# fungera (samma falla som predikat._ORDNINGSOPERATORER).
_ORDNING_I_POST = ("<", "<=", ">", ">=")


def _ar_tal(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# Vad ett kontrollsteg svarar med. Det ar kontrollstegens motsvarighet till
# verktygens returns-schema, och finns av samma skal: ett forvillkor som laser
# ett kontrollstegs svar ska kunna provas mot en form redan vid planeringen.
# korning.py bygger sina svar ur PRECIS de har formerna.
KONTROLLSVAR = {
    "villkor": {
        "type": "object",
        "properties": {
            "holl": {"type": "boolean", "description": "Om villkoret holl."},
            "skal": {"type": "string", "description": "Varje predikats utfall."},
        },
        "required": ["holl", "skal"],
    },
    "bindning": {
        "type": "object",
        "properties": {
            "bindningar": {"type": "object",
                           "description": "Namn -> last varde."},
            "skal": {"type": "string", "description": "Hur regeln valde."},
        },
        "required": ["bindningar", "skal"],
    },
    "oga": {
        "type": "object",
        "properties": {
            "uppfyllt": {"type": "boolean",
                         "description": "Om verifieringskravet ar uppfyllt."},
            "dom": {"type": ["string", "null"],
                    "description": "Ogats egen dom, ordagrant."},
            "skal": {"type": "string", "description": "Vad som brast, om nagot."},
        },
        "required": ["uppfyllt", "dom", "skal"],
    },
}


class Bindning(object):
    """Ett argumentvarde som lases ur scenen i stallet for att hittas pa."""

    __slots__ = ("sort", "fran_steg", "vag", "namn", "typ")

    def __init__(self, sort, fran_steg, vag=None, namn=None, typ="string"):
        self.sort = sort
        self.fran_steg = fran_steg
        self.vag = vag
        self.namn = namn
        self.typ = typ
        problem = []
        if sort not in ("steg", "namngiven"):
            problem.append("okand sort %r; kanda ar steg, namngiven" % (sort,))
        if not fran_steg:
            problem.append("bindningen maste namna steget den lases ur")
        if sort == "steg" and not vag:
            problem.append("en bindning ur ett svar kraver en vag")
        if sort == "namngiven" and not namn:
            problem.append("en namngiven bindning kraver ett namn")
        if sort == "steg" and namn is not None:
            problem.append("en bindning ur ett svar bar ingen namn-nyckel")
        if sort == "namngiven" and vag is not None:
            problem.append("en namngiven bindning bar ingen vag")
        if typ not in BINDNINGSTYPER:
            problem.append("okand typ %r; kanda ar %s"
                           % (typ, ", ".join(BINDNINGSTYPER)))
        if problem:
            raise Specfel("bindningen", problem)

    def __repr__(self):
        if self.sort == "steg":
            return "Bindning(%s.%s: %s)" % (self.fran_steg, self.vag, self.typ)
        return "Bindning(%s ur %s: %s)" % (self.namn, self.fran_steg, self.typ)

    def vittne(self):
        """Ett varde av ratt typ att prova schemat med vid planeringen."""
        return _VITTNEN[self.typ]

    def los(self, lage):
        """(finns, varde) ur korlaget. Kastar aldrig."""
        from .predikat import las_vag
        if self.sort == "steg":
            svar = lage.resultat.get(self.fran_steg)
            if svar is None:
                return False, None
            return las_vag(svar, self.vag)
        if self.namn in lage.bindningar:
            return True, lage.bindningar[self.namn]
        return False, None

    def till_json(self):
        return {"$bindning": {"sort": self.sort, "fran_steg": self.fran_steg,
                              "vag": self.vag, "namn": self.namn,
                              "typ": self.typ}}

    @classmethod
    def fran_json(cls, data):
        inre = data["$bindning"]
        vantade = ("sort", "fran_steg", "vag", "namn", "typ")
        if not isinstance(inre, dict) or set(inre) != set(vantade):
            raise Specfel("bindning", ["forvantade precis nycklarna %s"
                                       % ", ".join(sorted(vantade))])
        return cls(inre["sort"], inre["fran_steg"], inre["vag"], inre["namn"],
                   inre["typ"])

    @staticmethod
    def ar_bindning(varde):
        return isinstance(varde, dict) and set(varde) == {"$bindning"}


# ---------------------------------------------------------- bindningsregler

def _enda_gemensamma_par(kallsvar, ger):
    """(bindningar, skal). Valjer gransnittspar NAR det inte finns nagot val.

    Regeln ar avsiktligt trang: bar bada komponenterna precis ett gransnitt ar
    paret givet, och da valjer vi det. Bar nagon av dem flera gar det inte att
    avgora har utan att gissa - och att gissa ett gransnittsnamn ar precis vad
    I9 forbjuder. Da faller kontrollen med en text som listar kandidaterna, sa
    att operatoren kan svara.

    Kompatibiliteten domes ALDRIG har. Den domer VC sjalv, genom can_connect,
    i steget efter (I1: implementera aldrig om nagon annans matt).
    """
    if len(kallsvar) != 2:
        return None, ("regeln kraver precis tva gransnittslistor, fick %d"
                      % len(kallsvar))
    if len(ger) != 2:
        return None, ("regeln ger precis tva namn, planen bad om %d" % len(ger))
    namn = []
    for svar in kallsvar:
        lista = (svar or {}).get("interfaces")
        if not isinstance(lista, list):
            return None, "ett svar bar ingen gransnittslista"
        komponent = (svar or {}).get("component", "?")
        if len(lista) != 1:
            return None, ("%s bar %d gransnitt (%s); planen kan inte valja at "
                          "operatoren, fragan maste stallas"
                          % (komponent, len(lista),
                             ", ".join(str(i.get("name")) for i in lista) or "inga"))
        namn.append(lista[0].get("name"))
    for n in namn:
        if not isinstance(n, str) or not n:
            return None, "ett gransnitt saknar namn i svaret"
    return (dict(zip([g[0] for g in ger], namn)),
            "de tva komponenterna bar ett gransnitt var: %s" % ", ".join(namn))


# Sluten tabell. En regel som inte star har finns inte, och en plan som namner
# en okand regel avvisas vid planeringen.
BINDNINGSREGLER = {"enda_gemensamma_par": _enda_gemensamma_par}


class Efterkontroll(object):
    """Ett verktygsanrop plus en jamforelse. K16, och den viktigaste luckan.

    Specen sager det rakt ut om kallprojektet: `spec_generator.py` skriver
    `post_condition` som PROSA, och fältet har NOLL konsumenter i hela repot.
    En efterkontroll som ingen kor ar ingen efterkontroll - den ar en
    formulering som ser ut som en garanti.

    Formen ar darfor mekanisk: {verktyg, argument, vag, operator, forvantat}.
    Verktyget maste finnas i registret, det maste vara LASANDE (K23: all
    matning ar read och far aldrig ligga i skrivkon), vagen maste finnas i
    verktygets returns-schema, och jamforelsen gors av predikat.py - samma
    kod som forvillkoren anvander, sa att de tva aldrig kan drifta isar.

    FORVANTAT AR ALLTID ETT LITTERALT VARDE.

    Ett facit som raknas fram ur korningen ar inget facit. Det ar precis
    kallans `L-SC-01_REJECT_SELF_REF`: en kontroll dar `cube_path ==
    target_path` var trivialt sann och darfor aldrig kunde falla. En bindning
    far darfor sta i ARGUMENTEN - dar den pekar ut VAD som ska matas - men
    aldrig i det som svaret jamfors mot.
    """

    __slots__ = ("verktyg", "argument", "vag", "operator", "forvantat",
                 "motiv")

    def __init__(self, verktyg, argument, vag, operator, forvantat=None,
                 motiv=""):
        self.verktyg = verktyg
        self.argument = dict(argument or {})
        self.vag = vag
        self.operator = operator
        self.forvantat = forvantat
        self.motiv = motiv
        problem = []
        if not isinstance(verktyg, str) or not verktyg.strip():
            problem.append("efterkontrollen maste namna sitt verktyg")
        if not isinstance(vag, str) or not vag.strip():
            problem.append("efterkontrollen maste namna vagen i svaret den "
                           "laser")
        if operator not in OPERATORER:
            problem.append("okand operator %r; kanda ar %s"
                           % (operator, ", ".join(OPERATORER)))
        if isinstance(forvantat, Bindning):
            problem.append(
                "det forvantade vardet ar en bindning. Ett facit som raknas "
                "fram ur korningen ar inget facit - da kan kontrollen inte "
                "falla (L-SC-01_REJECT_SELF_REF)")
        if operator in _ORDNING_I_POST and not _ar_tal(forvantat):
            problem.append("%r kraver ett tal att jamfora med, fick %r"
                           % (operator, forvantat))
        if operator in ("finns", "saknas") and forvantat is not None:
            problem.append("%r tar inget varde" % operator)
        smitare = sorted(set(self.argument) & set(FORBJUDNA_STEGNYCKLAR))
        if smitare:
            problem.append("efterkontrollen bar %s; exekveringslaget ags av "
                           "utforaren (I12)" % ", ".join(smitare))
        if problem:
            raise Specfel("efterkontrollen %r" % (verktyg,), problem)

    def __repr__(self):
        return "Efterkontroll(%s.%s %s %r)" % (self.verktyg, self.vag,
                                               self.operator, self.forvantat)

    def rad(self):
        return "%s(%s) -> %s %s %r%s" % (
            self.verktyg, ", ".join(sorted(self.argument)), self.vag,
            self.operator, self.forvantat,
            (" (%s)" % self.motiv) if self.motiv else "")

    def bindningar(self):
        return tuple(sorted(((n, v) for n, v in self.argument.items()
                             if isinstance(v, Bindning)), key=lambda p: p[0]))

    def lasta_steg(self):
        return tuple(sorted(set(b.fran_steg for _n, b in self.bindningar())))

    def argument_med_vittnen(self):
        ut = {}
        for namn, varde in self.argument.items():
            ut[namn] = varde.vittne() if isinstance(varde, Bindning) else varde
        return ut

    def prova(self, svar):
        """(uppfyllt, skal) mot verktygets EGNA svar. Kastar aldrig.

        Jamforelsen gors av predikat.Predikat, alltsa av samma kod som
        forvillkoren. Tva jamforelser av samma sak ar tva olika jamforelser sa
        fort nagon ratter den ena.
        """
        try:
            predikat = Predikat("resultat", steg="_post", vag=self.vag,
                                operator=self.operator, varde=self.forvantat)
        except Specfel as fel:
            return False, str(fel)
        return predikat.prova(Korlage(resultat={"_post": svar}))

    def till_json(self):
        argument = {}
        for namn, varde in self.argument.items():
            argument[namn] = (varde.till_json() if isinstance(varde, Bindning)
                              else varde)
        return {"verktyg": self.verktyg, "argument": argument, "vag": self.vag,
                "operator": self.operator, "forvantat": self.forvantat,
                "motiv": self.motiv}

    @classmethod
    def fran_json(cls, data):
        vantade = ("verktyg", "argument", "vag", "operator", "forvantat",
                   "motiv")
        if not isinstance(data, dict) or set(data) != set(vantade):
            raise Specfel("efterkontroll",
                          ["forvantade precis nycklarna %s"
                           % ", ".join(sorted(vantade))])
        argument = {}
        for namn, varde in (data["argument"] or {}).items():
            argument[namn] = (Bindning.fran_json(varde)
                              if Bindning.ar_bindning(varde) else varde)
        return cls(data["verktyg"], argument, data["vag"], data["operator"],
                   data["forvantat"], data["motiv"])


class Kontroll(object):
    """Ett steg som inte anropar VC, men som avgor nagot.

        villkor    predikaten maste halla, annars faller steget
        bindning   las ut varden ur tidigare svar enligt en regel
        oga        hall planens verifieringskrav mot ogats rapport
    """

    __slots__ = ("sort", "villkor", "regel", "kallor", "ger", "fakta_nyckel")

    def __init__(self, sort, villkor=None, regel=None, kallor=(), ger=(),
                 fakta_nyckel=None):
        self.sort = sort
        self.villkor = villkor
        self.regel = regel
        self.kallor = list(kallor)
        self.ger = [(n, t) for n, t in ger]
        self.fakta_nyckel = fakta_nyckel
        problem = []
        if sort not in KONTROLLSORTER:
            raise Specfel("kontrollen", ["okand sort %r; kanda ar %s"
                                         % (sort, ", ".join(KONTROLLSORTER))])
        if sort == "villkor":
            if not isinstance(villkor, Forvillkor):
                problem.append("en villkorskontroll kraver ett Forvillkor")
            if regel or self.kallor or self.ger or fakta_nyckel:
                problem.append("en villkorskontroll bar bara sitt villkor")
        elif sort == "bindning":
            if regel not in BINDNINGSREGLER:
                problem.append("okand bindningsregel %r; kanda ar %s"
                               % (regel, ", ".join(sorted(BINDNINGSREGLER))))
            if not self.kallor:
                problem.append("en bindningskontroll kraver kallsteg")
            if not self.ger:
                problem.append("en bindningskontroll som inte ger nagot ar dod")
            for n, t in self.ger:
                if not n:
                    problem.append("ett bindningsnamn ar tomt")
                if t not in BINDNINGSTYPER:
                    problem.append("okand typ %r pa bindningen %r" % (t, n))
            if villkor is not None or fakta_nyckel:
                problem.append("en bindningskontroll bar varken villkor eller "
                               "faktanyckel")
        else:
            if not fakta_nyckel:
                problem.append("en ogonkontroll maste namna faktumet "
                               "ogonrapporten kommer in som")
            if villkor is not None or regel or self.kallor or self.ger:
                problem.append("en ogonkontroll bar bara sin faktanyckel")
        if problem:
            raise Specfel("kontrollen %r" % (sort,), problem)

    def __repr__(self):
        return "Kontroll(%s)" % self.sort

    def berorda_steg(self):
        if self.sort == "villkor":
            return self.villkor.berorda_steg()
        if self.sort == "bindning":
            return tuple(self.kallor)
        return ()

    def till_json(self):
        return {"sort": self.sort,
                "villkor": self.villkor.till_json() if self.villkor else None,
                "regel": self.regel,
                "kallor": list(self.kallor),
                "ger": [{"namn": n, "typ": t} for n, t in self.ger],
                "fakta_nyckel": self.fakta_nyckel}

    @classmethod
    def fran_json(cls, data):
        vantade = ("sort", "villkor", "regel", "kallor", "ger", "fakta_nyckel")
        if not isinstance(data, dict) or set(data) != set(vantade):
            raise Specfel("kontroll", ["forvantade precis nycklarna %s"
                                       % ", ".join(sorted(vantade))])
        return cls(data["sort"],
                   Forvillkor.fran_json(data["villkor"]) if data["villkor"] else None,
                   data["regel"], data["kallor"],
                   [(g["namn"], g["typ"]) for g in data["ger"]],
                   data["fakta_nyckel"])


class Steg(object):
    """Ett steg i grafen."""

    __slots__ = ("id", "sort", "motiv", "verktyg", "argument", "kontroll",
                 "beroenden", "forvillkor", "alternativ_grupp",
                 "parallell_grupp", "efterkontroller")

    def __init__(self, id, sort, motiv, verktyg=None, argument=None,
                 kontroll=None, beroenden=(), forvillkor=None,
                 alternativ_grupp=None, parallell_grupp=None,
                 efterkontroller=()):
        self.id = id
        self.sort = sort
        self.motiv = motiv
        self.verktyg = verktyg
        self.argument = dict(argument or {})
        self.kontroll = kontroll
        self.beroenden = tuple(beroenden)
        self.forvillkor = forvillkor
        self.alternativ_grupp = alternativ_grupp
        self.parallell_grupp = parallell_grupp
        self.efterkontroller = tuple(efterkontroller)
        problem = []
        if not isinstance(id, str) or not id.strip():
            problem.append("steget saknar id")
        if sort not in STEGSORTER:
            problem.append("okand sort %r; kanda ar %s"
                           % (sort, ", ".join(STEGSORTER)))
        if not isinstance(motiv, str) or not motiv.strip():
            problem.append("steget saknar motiv; ett steg ingen kan forklara "
                           "hor inte hemma i en plan")
        if sort == "verktyg":
            if not verktyg:
                problem.append("ett verktygssteg maste namna sitt verktyg")
            if kontroll is not None:
                problem.append("ett verktygssteg bar ingen kontroll")
        elif sort == "kontroll":
            if not isinstance(kontroll, Kontroll):
                problem.append("ett kontrollsteg kraver en Kontroll")
            if verktyg is not None or self.argument:
                problem.append("ett kontrollsteg anropar inget verktyg")
        if len(set(self.beroenden)) != len(self.beroenden):
            problem.append("dubblerat beroende")
        if id in self.beroenden:
            problem.append("steget beror pa sig sjalvt")
        if forvillkor is not None and not isinstance(forvillkor, Forvillkor):
            problem.append("forvillkoret ar inget Forvillkor")
        for namn, varde in self.argument.items():
            if isinstance(varde, Bindning) and sort != "verktyg":
                problem.append("bindningen %r sitter pa ett kontrollsteg" % namn)
        for e in self.efterkontroller:
            if not isinstance(e, Efterkontroll):
                problem.append("%r ar ingen Efterkontroll" % (e,))
        if self.efterkontroller and sort != "verktyg":
            problem.append("ett kontrollsteg anropar inget verktyg och har "
                           "darfor ingenting att efterkontrollera")
        if problem:
            raise Specfel("steget %r" % (id,), problem)

    def __repr__(self):
        vad = self.verktyg if self.sort == "verktyg" else self.kontroll.sort
        return "Steg(%s, %s)" % (self.id, vad)

    # -- bekvamligheter ---------------------------------------------------

    @classmethod
    def verktygssteg(cls, id, verktyg, argument, motiv, **ovrigt):
        return cls(id, "verktyg", motiv, verktyg=verktyg, argument=argument,
                   **ovrigt)

    @classmethod
    def kontrollsteg(cls, id, kontroll, motiv, **ovrigt):
        return cls(id, "kontroll", motiv, kontroll=kontroll, **ovrigt)

    def bindningar(self):
        """(argumentnamn, Bindning) for varje bundet argument."""
        return tuple(sorted(((n, v) for n, v in self.argument.items()
                             if isinstance(v, Bindning)), key=lambda p: p[0]))

    def argument_med_vittnen(self):
        """Argumenten dar varje bindning ersatts av ett vittnesvarde.

        Det ar DE HAR argumenten som provas mot verktygets schema vid
        planeringen. Vittnet har ratt typ, sa allt utom just det okanda
        vardet provas pa riktigt.
        """
        ut = {}
        for namn, varde in self.argument.items():
            ut[namn] = varde.vittne() if isinstance(varde, Bindning) else varde
        return ut

    def lasta_steg(self):
        """Steg vars SVAR det har steget laser. De maste vara beroenden."""
        ut = set()
        if self.forvillkor is not None:
            ut.update(self.forvillkor.berorda_steg())
        if self.kontroll is not None:
            ut.update(self.kontroll.berorda_steg())
        for _namn, b in self.bindningar():
            ut.add(b.fran_steg)
        for e in self.efterkontroller:
            ut.update(e.lasta_steg())
        return tuple(sorted(ut))

    # -- serialisering ----------------------------------------------------

    def till_json(self):
        argument = {}
        for namn, varde in self.argument.items():
            argument[namn] = (varde.till_json() if isinstance(varde, Bindning)
                              else varde)
        return {"id": self.id, "sort": self.sort, "motiv": self.motiv,
                "verktyg": self.verktyg, "argument": argument,
                "kontroll": self.kontroll.till_json() if self.kontroll else None,
                "beroenden": list(self.beroenden),
                "forvillkor": (self.forvillkor.till_json()
                               if self.forvillkor else None),
                "alternativ_grupp": self.alternativ_grupp,
                "parallell_grupp": self.parallell_grupp,
                "efterkontroller": [e.till_json()
                                    for e in self.efterkontroller]}

    @classmethod
    def fran_json(cls, data):
        vantade = ("id", "sort", "motiv", "verktyg", "argument", "kontroll",
                   "beroenden", "forvillkor", "alternativ_grupp",
                   "parallell_grupp", "efterkontroller")
        if not isinstance(data, dict):
            raise Specfel("steg", ["forvantade ett objekt, fick %s"
                                   % type(data).__name__])
        smitare = sorted(set(data) & set(FORBJUDNA_STEGNYCKLAR))
        if smitare:
            raise Specfel(
                "steget %r" % (data.get("id"),),
                ["nyckeln %r valjer exekveringslage; routingen read->exec och "
                 "write->exec_queue ags av utforaren och far inte sta i planen "
                 "(I12)" % n for n in smitare])
        saknade = sorted(set(vantade) - set(data))
        okanda = sorted(set(data) - set(vantade))
        if saknade or okanda:
            raise Specfel("steget %r" % (data.get("id"),),
                          ["nyckeln %r saknas" % n for n in saknade]
                          + ["okand nyckel %r" % n for n in okanda])
        argument = {}
        for namn, varde in (data["argument"] or {}).items():
            argument[namn] = (Bindning.fran_json(varde)
                              if Bindning.ar_bindning(varde) else varde)
        return cls(data["id"], data["sort"], data["motiv"], data["verktyg"],
                   argument,
                   Kontroll.fran_json(data["kontroll"]) if data["kontroll"] else None,
                   data["beroenden"],
                   Forvillkor.fran_json(data["forvillkor"]) if data["forvillkor"] else None,
                   data["alternativ_grupp"], data["parallell_grupp"],
                   [Efterkontroll.fran_json(e)
                    for e in (data["efterkontroller"] or [])])
