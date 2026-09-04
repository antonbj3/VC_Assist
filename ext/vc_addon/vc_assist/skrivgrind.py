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
)

# Namn som gor syntaktisk analys omojlig. Konservativt: de raknas som skrivande.
OGENOMSKINLIGA = ("eval", "exec", "execfile", "compile", "__import__",
                  "setattr", "delattr", "getattr", "globals", "locals", "vars")

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


def granska(kod):
    """Returnerar en Dom. Kod som inte gar att tolka raknas som skrivande."""
    skal = []
    try:
        trad = ast.parse(kod)
    except SyntaxError as e:
        return Dom(True, ["gar inte att tolka som Python, rad %s: %s"
                          % (getattr(e, "lineno", "?"), e.msg)])

    for nod in ast.walk(trad):
        rad = getattr(nod, "lineno", None)

        if isinstance(nod, (ast.Assign, ast.AugAssign)):
            mal = nod.targets if isinstance(nod, ast.Assign) else [nod.target]
            for m in mal:
                for u in ast.walk(m):
                    if isinstance(u, ast.Attribute):
                        skal.append("rad %s: tilldelning till attributet .%s"
                                    % (rad, u.attr))
                    elif isinstance(u, ast.Subscript):
                        skal.append("rad %s: tilldelning till ett index" % rad)

        elif isinstance(nod, ast.Delete):
            skal.append("rad %s: del-sats" % rad)

        elif isinstance(nod, ast.Call):
            namn = _sista_namnet(nod.func)
            if namn in OGENOMSKINLIGA:
                skal.append("rad %s: %s() gor syntaktisk analys omojlig" % (rad, namn))
            elif _oppnar_for_skrivning(nod):
                skal.append("rad %s: oppnar en fil for skrivning" % rad)
            elif _ar_muterande_namn(namn):
                skal.append("rad %s: anropar %s()" % (rad, namn))

        elif hasattr(ast, "Exec") and isinstance(nod, getattr(ast, "Exec")):
            skal.append("rad %s: exec-sats" % rad)

    return Dom(bool(skal), skal)
