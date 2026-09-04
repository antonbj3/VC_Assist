# -*- coding: utf-8 -*-
"""Avgor om en kodstrang SKRIVER. Syntaktiskt, konservativt, stanger vid tvivel.

Regeln "effect=write medfor ko" ar mekanisk och avgors av verktygets deklarerade
effect (45_verktyg.md). Den regeln bor i tjansten. Denna grind ar den ANDRA
forsvarslinjen: bryggan far inte lita pa sin anropare, och rat exec ar oppen for
vad som helst.

Vad den ar: en AST-analys. Vad den INTE ar: ett bevis. En namnuppslagning i
kortid (getattr med berakat namn) gar inte att avgora syntaktiskt, och da
svarar grinden SKRIVER - felet ska falla at det hallet.

Kalla: docs/spec/45_verktyg.md, tests/protocol/fas1_bryggan.md
"""
from __future__ import absolute_import, division, print_function

import ast

# Anropsnamn som andrar nagot. Matchas pa hela namnet i gemener, med prefix,
# sa bade "setProperty" och "set_property" fastnar.
MUTERANDE_PREFIX = (
    "set", "create", "delete", "remove", "add", "clear", "insert", "append",
    "extend", "pop", "update", "load", "save", "write", "start", "stop",
    "reset", "run", "connect", "disconnect", "move", "rebuild", "execute",
    "export", "teach", "jog", "attach", "detach", "grasp", "release",
    "rename", "apply", "commit", "kill", "terminate", "send", "trigger",
    "enable", "disable", "makedirs", "mkdir", "rmdir", "unlink", "rename",
    "chmod", "system", "popen", "spawn", "call", "check_output",
    # Funna av verktygsregistrets korsprov 2026-09-04: clone() ensamt domdes
    # som LASANDE, sa en komponentkloning hade sluppit forbi kon. De ovriga ar
    # samma klass av namn som inte borjar pa nagot av prefixen ovan.
    "clone", "duplicate", "makeunique", "transfer", "attach", "detach",
    "grab", "drop", "paste", "cut", "undo", "redo", "restore", "halt",
    # Funnet av simuleringsdomanens korsprov (M-47): sim.autoHalt() STOPPAR
    # simuleringen men domdes som LASANDE - "halt" ar ett prefix och autoHalt
    # borjar inte pa det. Ett verktyg pa den metoden hade darfor kunnat ga
    # genom exec, utan godkannande, och ta ned en pagaende korning. Prefixet
    # star som helt ord och inte som "auto", som skulle doma varje autoScale
    # och autoSize som skrivande. Samma korsprov faller sim.continueRun():
    # den startar en stoppad simulering igen, och "run" ar ett prefix som
    # continueRun inte borjar pa.
    "autohalt", "continuerun",
)

# Namn som gor syntaktisk analys omojlig. Konservativt: de raknas som skrivande.
OGENOMSKINLIGA = ("eval", "exec", "execfile", "compile", "__import__",
                  "setattr", "delattr", "getattr", "globals", "locals", "vars",
                  # Dunder-vagarna runt en vanlig tilldelning. Funna av
                  # motbevisningen 2026-09-04: c.__setattr__("Name", "x") gor
                  # exakt vad c.Name = "x" gor, men domdes som LASANDE.
                  "__setattr__", "__delattr__", "__getattr__", "__setitem__",
                  "__delitem__", "__getattribute__", "__dict__")

SKRIVLAGEN = ("w", "a", "x", "+")

try:
    _STRANGAR = (str, unicode)      # noqa: F821 - py2
except NameError:
    _STRANGAR = (str,)


class Dom(object):
    def __init__(self, skriver, skal=None):
        self.skriver = bool(skriver)
        self.skal = skal or []

    def __repr__(self):
        return "Dom(skriver=%r, skal=%r)" % (self.skriver, self.skal)


def _sista_namnet(nod):
    if isinstance(nod, ast.Name):
        return nod.id
    if isinstance(nod, ast.Attribute):
        return nod.attr
    return None


def _ar_muterande_namn(namn):
    """Prefixet jamfors skiftlagesokansligt, men GRANSEN i ursprungsnamnet.

    Sa fastnar bade setProperty och set_property, medan setup och runtime gar
    fria - de ar egna ord som rakar borja pa ett muterande prefix.
    """
    if not namn:
        return False
    ren = namn.lstrip("_")
    lag = ren.lower()
    for p in MUTERANDE_PREFIX:
        if not lag.startswith(p):
            continue
        rest = ren[len(p):]
        if rest == "":                 # set, run, add, remove
            return True
        if rest[0] == "_":             # set_property
            return True
        if rest[0].isupper():          # setProperty
            return True
    return False


def _oppnar_for_skrivning(nod):
    """open(x, 'w') och liknande."""
    namn = _sista_namnet(nod.func)
    if namn not in ("open", "file"):
        return False
    lagen = None
    if len(nod.args) >= 2:
        lagen = nod.args[1]
    for kw in getattr(nod, "keywords", []) or []:
        if kw.arg == "mode":
            lagen = kw.value
    if lagen is None:
        return False        # standardlage ar lasning
    # ast.Constant.value i py3.8+, ast.Str.s i py2. Bada mates, ingen antas.
    varde = getattr(lagen, "value", None)
    if not isinstance(varde, _STRANGAR):
        varde = getattr(lagen, "s", None)
    if not isinstance(varde, _STRANGAR):
        return True         # berakat lage - stang vid tvivel
    return any(t in varde for t in SKRIVLAGEN)


BEHALLARANROP = ("dict", "list", "set", "OrderedDict", "defaultdict", "Counter")


def _lokala_behallare(trad):
    """Namn som binds till en behallare koden SJALV skapat.

    Att skriva i en ordbok man nyss byggt ar bokforing, inte en scenandring.
    Utan den skillnaden faller varje lasande skript som samlar sitt svar i en
    dict - alltsa nastan alla, eftersom svaret gar tillbaka som JSON.

    Konservativt: binds namnet nagon gang till nagot ANNAT stryks det, sa
    d = {} foljt av d = comp.Properties inte oppnar en lucka.
    """
    behallare, smutsiga = set(), set()
    for nod in ast.walk(trad):
        if not isinstance(nod, ast.Assign):
            continue
        egen = isinstance(nod.value, (ast.Dict, ast.List, ast.Set))
        if not egen:
            for k in ("DictComp", "ListComp", "SetComp"):
                if hasattr(ast, k) and isinstance(nod.value, getattr(ast, k)):
                    egen = True
        if not egen and isinstance(nod.value, ast.Call):
            egen = _sista_namnet(nod.value.func) in BEHALLARANROP
        for m in nod.targets:
            if isinstance(m, ast.Name):
                (behallare if egen else smutsiga).add(m.id)
    return behallare - smutsiga


def _rotnamn(nod):
    while isinstance(nod, (ast.Subscript, ast.Attribute)):
        nod = nod.value
    return nod.id if isinstance(nod, ast.Name) else None


def _doma_mal(mal, egna, rad, skal):
    """Domer ETT tilldelningsmal.

    Strukturellt, inte med ast.walk: en walk over malet besoker aven
    INDEXUTTRYCKET, sa ut[c.Name] = v anklagades for att skriva till .Name.
    """
    if isinstance(mal, ast.Attribute):
        skal.append("rad %s: tilldelning till attributet .%s" % (rad, mal.attr))
    elif isinstance(mal, ast.Subscript):
        rot = _rotnamn(mal)
        if rot not in egna:
            skal.append("rad %s: tilldelning till ett index i %s"
                        % (rad, rot or "ett okant uttryck"))
    elif isinstance(mal, (ast.Tuple, ast.List)):
        for e in mal.elts:
            _doma_mal(e, egna, rad, skal)
    elif hasattr(ast, "Starred") and isinstance(mal, ast.Starred):
        _doma_mal(mal.value, egna, rad, skal)
    # Ett rent Name binder en lokal variabel och ar ingen andring.


def granska(kod):
    """Returnerar en Dom. Kod som inte gar att tolka raknas som skrivande."""
    skal = []
    try:
        trad = ast.parse(kod)
    except SyntaxError as e:
        return Dom(True, ["gar inte att tolka som Python, rad %s: %s"
                          % (getattr(e, "lineno", "?"), e.msg)])

    egna = _lokala_behallare(trad)

    for nod in ast.walk(trad):
        rad = getattr(nod, "lineno", None)

        if isinstance(nod, (ast.Assign, ast.AugAssign)):
            mal = nod.targets if isinstance(nod, ast.Assign) else [nod.target]
            for m in mal:
                _doma_mal(m, egna, rad, skal)

        elif isinstance(nod, ast.Delete):
            skal.append("rad %s: del-sats" % rad)

        elif isinstance(nod, ast.Call):
            namn = _sista_namnet(nod.func)
            if (isinstance(nod.func, ast.Attribute)
                    and _rotnamn(nod.func.value) in egna):
                continue    # metodanrop pa en egen behallare, t.ex. rader.append()
            if namn in OGENOMSKINLIGA:
                skal.append("rad %s: %s() gor syntaktisk analys omojlig" % (rad, namn))
            elif _oppnar_for_skrivning(nod):
                skal.append("rad %s: oppnar en fil for skrivning" % rad)
            elif _ar_muterande_namn(namn):
                skal.append("rad %s: anropar %s()" % (rad, namn))

        elif hasattr(ast, "Exec") and isinstance(nod, getattr(ast, "Exec")):
            skal.append("rad %s: exec-sats" % rad)

    return Dom(bool(skal), skal)


# Skriptbeteenden ar en egen klass av fara: att skapa ett STOPPAR den korande
# simuleringen, och pumpen bor i simuleringen (M-13). Koden kors, men bryggan
# dor mitt i sitt eget svar och kommer inte tillbaka.

SKRIPTTYPER = ("VC_SCRIPT", "VC_PYTHONSCRIPT")

# Anrop som ocksa stoppar simuleringen och darmed dodar pumpen. app.save() ar
# MATT: den dodade bryggan mitt i fas 5:s verktygsprov.
#
# Skillnaden mot skriptbeteenden ar avsiktlig. Att lagga till ett skript ar
# sallsynt och har en uppskjuten vag; det AVVISAS. Att spara en layout ar en
# helt normal sak att vilja gora; den TILLATS men markeras, sa anroparen vet
# att inget utfall kommer och slutar vanta pa ett svar som aldrig kan skickas.
DODANDE_ANROP = ("save",)


def dodar_pumpen(kod):
    """Anrop som stoppar simuleringen utan att vara skriptbeteenden."""
    skal = []
    try:
        trad = ast.parse(kod)
    except SyntaxError:
        return skal
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Call) and _sista_namnet(nod.func) in DODANDE_ANROP:
            skal.append("rad %s: %s() stoppar simuleringen"
                        % (getattr(nod, "lineno", None), _sista_namnet(nod.func)))
    return skal


def _konstantbindningar(trad):
    """Namn som binds till en VC_-konstant, ett led djupt.

    Funnet av motbevisningen 2026-09-04: `t = VC_SCRIPT` foljt av
    `createBehaviour(t, "x")` slapp forbi, eftersom grinden bara sag efter
    konstanten DIREKT i anropet. Ett mellanled racker for att komma runt en
    grind som domer stavning.
    """
    bindningar = {}
    smutsiga = set()
    for nod in ast.walk(trad):
        if not isinstance(nod, ast.Assign):
            continue
        for m in nod.targets:
            if not isinstance(m, ast.Name):
                continue
            if isinstance(nod.value, ast.Name) and nod.value.id.startswith("VC_"):
                bindningar[m.id] = nod.value.id
            else:
                smutsiga.add(m.id)
    for namn in smutsiga:
        bindningar.pop(namn, None)
    return bindningar


def _ar_strangliteral(nod, varde):
    for attr in ("value", "s"):
        v = getattr(nod, attr, None)
        if isinstance(v, _STRANGAR) and v == varde:
            return True
    return False


def skapar_skriptbeteende(kod):
    """Returnerar en lista skal, tom om koden inte ror skriptbeteenden.

    Fail-closed: gar det inte att avgora VILKEN beteendetyp som skapas raknas
    det som ett skriptbeteende. Det ar den enda operation som dodar bryggan
    utan vag tillbaka (M-13), och en gissning at fel hall kostar hela sessionen.
    """
    skal = []
    try:
        trad = ast.parse(kod)
    except SyntaxError:
        return skal          # otolkbar kod fangas redan av granska()
    bindningar = _konstantbindningar(trad)

    for nod in ast.walk(trad):
        rad = getattr(nod, "lineno", None)

        if isinstance(nod, ast.Call) and _sista_namnet(nod.func) == "createBehaviour":
            if not nod.args:
                skal.append("rad %s: createBehaviour utan argument" % rad)
                continue
            a = nod.args[0]
            if isinstance(a, ast.Name):
                namn = bindningar.get(a.id, a.id)
                if namn in SKRIPTTYPER:
                    skal.append("rad %s: createBehaviour(%s, ...)" % (rad, namn))
                elif not namn.startswith("VC_"):
                    skal.append("rad %s: createBehaviour med en berakad typ (%s); "
                                "vilket beteende som skapas gar inte att avgora"
                                % (rad, a.id))
            else:
                skal.append("rad %s: createBehaviour med ett uttryck som typ; "
                            "vilket beteende som skapas gar inte att avgora" % rad)

        if isinstance(nod, ast.Assign):
            for m in nod.targets:
                if isinstance(m, ast.Attribute) and m.attr == "Script":
                    skal.append("rad %s: tilldelning till .Script" % rad)

        # setattr(obj, "Script", ...) och varje setattr med berakat namn
        if isinstance(nod, ast.Call) and _sista_namnet(nod.func) in (
                "setattr", "__setattr__"):
            if len(nod.args) >= 2:
                namnnod = nod.args[-2]
                if _ar_strangliteral(namnnod, "Script"):
                    skal.append("rad %s: setattr(..., 'Script', ...)" % rad)
                elif not isinstance(namnnod, (ast.Str, ast.Constant)):
                    skal.append("rad %s: setattr med ett berakat attributnamn; "
                                "det kan vara Script" % rad)
    return skal
