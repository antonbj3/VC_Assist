# -*- coding: utf-8 -*-
"""KODFALLORNA: de matta fallor som syns i koden modellen skriver.

Tre av korpusens matta fallor handlar om kod som gar att LASA. De var bedda
fram till M-53, och det ar en dalig plats att be pa: en modell som gar i en
av dem far ett tal eller ett fel som SER RIMLIGT UT.

  kvaternion     FAL-001. MATT M-11: VC:s kvaternion ar skalar-forst.
                 getQuaternion() ger en vcVector dar q.X ar SKALAREN och
                 vektordelen ligger i (q.Y, q.Z, q.W). Vid noll graders
                 vridning ger falten (1, 0, 0, 0), vilket avlast som
                 (x, y, z, w) ar en 180-gradersvridning: en helt orord detalj
                 ser ut att ha vant sig upp och ned.
  bytestrangar   FAL-006. MATT M-05: varje strangskrivning kastade
                 SystemError: error return without exception set, orsakat av
                 unicode_literals. VC 4.10:s py2-bindning tar bytestrangar.
  py27           FAL-008. Koden som kors inne i VC 4.10 ar Python 2.7
                 (inbaddad python27.dll). En f-strang ar ett syntaxfel dar,
                 och ett syntaxfel i ett skript som ska klistras in i VC
                 upptacks forst av operatoren.

VARFOR ETT KODBLOCK I ETT SVAR RAKNAS SOM VC-KOD. Det ar redan harnessens
antagande: granska_svarstext provar varje parsbart Python-block mot
API-indexet och mot skrivgrinden, eftersom blocket ar det operatoren
klistrar in. Kodfallorna staller sig i samma led. Ett block med kod som inte
ar VC-kod fastnar redan i dag pa api_namn, sa antagandet ar inte nytt.

RIKTNINGEN. Alla tre grindar kraver en TYDLIG traff i tradet: ett namn bundet
ur getQuaternion(), en __future__-import eller en u-prefixad strang som inte
gar genom _s(), en syntaxnod som inte finns i Python 2.7. Prosa och
allmanpython anklagas inte.
"""
from __future__ import annotations

import ast
import re
from typing import List, Tuple

GRINDAR = ("kvaternion", "bytestrangar", "py27")

# Anropet som lamnar en kvaternion. MATT M-11: q.X ar skalaren.
KVATERNIONANROP = "getQuaternion"
KVATERNIONFALT = ("X", "Y", "Z", "W")

# Bryggans egen omvandlare till bytestrang. En u-prefixad strang INNE i ett
# _s()-anrop ar ratt gjort: det ar precis sa verktygsmallarna skriver
# (verktyg/kodmall.py), och en grind som anklagade den hade anklagat var egen
# genererade kod.
_S_MED_U = re.compile(r"_s\(\s*u['\"]")
_U_STRANG = re.compile(r"(?<![A-Za-z0-9_'\"])u['\"]")


def _sista_namnet(nod) -> str:
    if isinstance(nod, ast.Name):
        return nod.id
    if isinstance(nod, ast.Attribute):
        return nod.attr
    return ""


def _trad(kod: str):
    try:
        return ast.parse(kod or "")
    except (SyntaxError, ValueError):
        return None


# ---- FAL-001: kvaternionen ----------------------------------------------

def _kvaternionnamn(trad) -> frozenset:
    """Namnen som ar bundna till en kvaternion i den har koden."""
    namn = set()
    for nod in ast.walk(trad):
        if not isinstance(nod, ast.Assign):
            continue
        varde = nod.value
        if not (isinstance(varde, ast.Call)
                and _sista_namnet(varde.func) == KVATERNIONANROP):
            continue
        for mal in nod.targets:
            if isinstance(mal, ast.Name):
                namn.add(mal.id)
    return frozenset(namn)


def _ar_kvaternion(nod, namn: frozenset) -> bool:
    """Sant om uttrycket ar en kvaternion: en bunden variabel eller anropet."""
    if isinstance(nod, ast.Name):
        return nod.id in namn
    if isinstance(nod, ast.Call):
        return _sista_namnet(nod.func) == KVATERNIONANROP
    return False


def _falt(nod, namn: frozenset) -> str:
    """Faltnamnet om noden laser ett kvaternionfalt, annars tom strang."""
    if (isinstance(nod, ast.Attribute) and nod.attr in KVATERNIONFALT
            and _ar_kvaternion(nod.value, namn)):
        return nod.attr
    return ""


def kvaternion_i_namnordning(kod: str) -> Tuple[str, ...]:
    """Skalen till att koden laser kvaternionen i namnordning.

    Tva former fangas, och bada ar den SAMMA missen sedd fran olika hall:

      1. en sekvens som plockar falten i ordningen X, Y, Z, W - det ar
         precis den avlasning som gor (1, 0, 0, 0) till en 180-graders
         vridning
      2. en tilldelning dar variabeln heter samma sak som faltet
         (x = q.X, w = q.W). Ratt avlasning binder skalaren till q.X, och
         da heter variabeln inte x.
    """
    trad = _trad(kod)
    if trad is None:
        return ()
    namn = _kvaternionnamn(trad)
    om_anrop = any(isinstance(n, ast.Call)
                   and _sista_namnet(n.func) == KVATERNIONANROP
                   for n in ast.walk(trad))
    if not namn and not om_anrop:
        return ()

    skal: List[str] = []
    for nod in ast.walk(trad):
        if isinstance(nod, (ast.Tuple, ast.List)):
            falt = tuple(f for f in (_falt(e, namn) for e in nod.elts) if f)
            if falt == KVATERNIONFALT:
                skal.append(
                    "rad %s: falten lases i ordningen X, Y, Z, W"
                    % getattr(nod, "lineno", "?"))
        elif isinstance(nod, ast.Assign) and len(nod.targets) == 1:
            mal = nod.targets[0]
            falt = _falt(nod.value, namn)
            if (isinstance(mal, ast.Name) and falt
                    and mal.id.lower() == falt.lower()):
                skal.append("rad %s: %s = <kvaternion>.%s"
                            % (getattr(nod, "lineno", "?"), mal.id, falt))
    if not skal:
        return ()
    return tuple(skal) + (
        "MATT M-11: VC:s kvaternion ar skalar-forst. q.X ar SKALAREN och "
        "vektordelen ligger i (q.Y, q.Z, q.W). Vid noll graders vridning ger "
        "falten (1, 0, 0, 0), och avlast i namnordning blir det en "
        "180-gradersvridning pa en helt orord detalj (FAL-001)",)


# ---- FAL-006: bytestrangarna --------------------------------------------

def unicodetext(kod: str) -> Tuple[str, ...]:
    """Skalen till att koden skickar unicode in i VC:s API."""
    skal: List[str] = []
    trad = _trad(kod)
    if trad is not None:
        for nod in ast.walk(trad):
            if (isinstance(nod, ast.ImportFrom) and nod.module == "__future__"
                    and any(a.name == "unicode_literals" for a in nod.names)):
                skal.append("rad %s: from __future__ import unicode_literals"
                            % getattr(nod, "lineno", "?"))
    # Den u-prefixade strangen syns inte i tradet: py3:s parser slanger
    # prefixet. Texten far darfor svara, och _s(u"...") undantas eftersom det
    # ar precis sa verktygsmallarna gor det ratt.
    utan_s = _S_MED_U.sub("_s(", kod or "")
    if _U_STRANG.search(utan_s):
        skal.append("koden bar en u-prefixad strang som inte gar genom _s()")
    if not skal:
        return ()
    return tuple(skal) + (
        "MATT M-05: varje strangskrivning kastade SystemError: error return "
        "without exception set, orsakat av unicode_literals. All text in i "
        "VC 4.10:s API maste vara bytestrangar (FAL-006)",)


# ---- FAL-008: Python 2.7 -------------------------------------------------

def _nodtyp(namn: str):
    return getattr(ast, namn, None)


# Syntax som inte finns i Python 2.7. Varje post ar (nodtyp, vad det heter i
# klartext). Listan ar av SYNTAX och inte av bibliotek: en grind som ocksa
# domde importer hade fallt allt som ar nytt i standardbiblioteket, och det
# ar en annan fraga.
_PY3SYNTAX = tuple(
    (_nodtyp(n), text) for n, text in (
        ("JoinedStr", "f-strang"),
        ("NamedExpr", "tilldelningsuttryck (:=)"),
        ("AsyncFunctionDef", "async def"),
        ("Await", "await"),
        ("AsyncFor", "async for"),
        ("AsyncWith", "async with"),
        ("YieldFrom", "yield from"),
        ("AnnAssign", "typannoterad tilldelning"),
        ("Nonlocal", "nonlocal"),
        ("MatMult", "matrisoperatorn @"),
    ) if _nodtyp(n) is not None)


def inte_python27(kod: str) -> Tuple[str, ...]:
    """Skalen till att koden inte gar att kora i VC 4.10:s Python 2.7."""
    trad = _trad(kod)
    if trad is None:
        return ()
    skal: List[str] = []
    for nod in ast.walk(trad):
        rad = getattr(nod, "lineno", "?")
        for typ, text in _PY3SYNTAX:
            if isinstance(nod, typ):
                skal.append("rad %s: %s" % (rad, text))
                break
        else:
            if isinstance(nod, (ast.FunctionDef,)):
                args = nod.args
                if getattr(args, "kwonlyargs", None):
                    skal.append("rad %s: nyckelordsbara argument" % rad)
                if nod.returns is not None or any(
                        a.annotation is not None
                        for a in list(args.args) + list(
                            getattr(args, "kwonlyargs", []))):
                    skal.append("rad %s: typannoterad funktion" % rad)
            elif isinstance(nod, (ast.Assign,)):
                for mal in nod.targets:
                    if isinstance(mal, (ast.Tuple, ast.List)) and any(
                            isinstance(e, ast.Starred) for e in mal.elts):
                        skal.append("rad %s: stjarnuppackning i en "
                                    "tilldelning" % rad)
    if not skal:
        return ()
    # Dubbletter tas bort men ordningen behalls: en rad ska namnas en gang.
    sedda, unika = set(), []
    for s in skal:
        if s not in sedda:
            sedda.add(s)
            unika.append(s)
    return tuple(unika) + (
        "Koden som kors inne i VC 4.10 ar Python 2.7 (inbaddad python27.dll, "
        "docs/spec/36_versioner.md). Ett syntaxfel dar upptacks forst av "
        "operatoren, nar blocket redan ar inklistrat (FAL-008)",)


# ---- kedjan --------------------------------------------------------------

def granska(kod: str) -> Tuple[str, Tuple[str, ...]]:
    """(grind, skal) for det forsta som faller. ("", ()) nar inget gor det.

    Ordningen ar en klassningsregel (82_felklasser.md sorteringsregel 1) och
    gar fran det som ger ETT FALSKT TAL till det som ger ett fel operatoren
    ser direkt:

      1 kvaternion     ger en vridning som inte skedde. Ingen kraschar.
      2 bytestrangar   kastar SystemError nar koden kors i VC.
      3 py27           ar ett syntaxfel; blocket kor inte alls.
    """
    for grind, skal in (("kvaternion", kvaternion_i_namnordning(kod)),
                        ("bytestrangar", unicodetext(kod)),
                        ("py27", inte_python27(kod))):
        if skal:
            return grind, skal
    return "", ()
