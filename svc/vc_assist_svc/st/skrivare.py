# -*- coding: utf-8 -*-
"""Skrivare: modell in, ST-text ut.

Två krav styr all formatering här:

1. **Determinism.** Samma modell ger byte-identisk text, varje gång. Utdata är
   ett kontrakt (docs/spec/95_testprotokoll.md, "Guldfil"), och en guldfil som
   ändrar sig av sig själv mäter ingenting.
2. **Ren ASCII.** Texten ska genom STruC++, OpenPLC:s inladdning och vidare ut
   som OPC UA-namn. Teckenkodningen där äger vi inte, så skrivaren vägrar
   hellre än skickar iväg något oläsbart.

Parenteser sätts efter prioritet, inte efter smak: exakt de som behövs. Då ger
läsare(skrivare(m)) samma träd igen, och skrivare(läsare(text)) samma text.
"""
from __future__ import annotations

from . import modell as M
from . import typer as T
from .fel import SkrivFel

# Fyra blanksteg per nivå. IEC-litteraturen och OpenPLC:s egna exempel
# använder fyra; talet är en konvention, inte en mätning.
INDRAG = "    "

# Prioritet per operator, lägre binder svagare. Speglar lasare.NIVAER;
# ändras den ena måste den andra följa med, och testet skrivare-läsare-tur-
# och-retur fäller om de glider isär.
PRIORITET = {
    "OR": 1, "XOR": 2, "AND": 3,
    "=": 4, "<>": 4,
    "<": 5, ">": 5, "<=": 5, ">=": 5,
    "+": 6, "-": 6,
    "*": 7, "/": 7, "MOD": 7,
    # Exponent binder hardare an unart minus (IEC 61131-3 tabell 71), darfor
    # 9 och inte 8: `-a ** b` ar `-(a ** b)`.
    "**": 9,
}
# Ett steg over den hardast bindande operatorn i tabellen ovan (MOD = 7):
# NOT och unart minus binder hardare an all tvastallig aritmetik.
UNAR_PRIORITET = 8

# De hogerassociativa operatorerna. Alla andra ar vansterassociativa, och
# skillnaden syns i VILKEN sida som maste parentesera vid samma prioritet.
HOGERASSOCIATIVA = ("**",)


def _ascii(text: str, vad: str) -> str:
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        raise SkrivFel("%s innehåller icke-ASCII: %r. Genererad ST måste vara "
                       "ren ASCII hela vägen till PLC:n." % (vad, text))
    return text


def skriv_typ(t: T.Typ) -> str:
    return _ascii(t.st(), "en typ")


def skriv_uttryck(u: M.Uttryck, yttre: int = 0) -> str:
    if isinstance(u, M.Namn):
        return _ascii(u.ident, "ett namn")
    if isinstance(u, M.Literal):
        return _ascii(u.text, "en literal")
    if isinstance(u, M.Medlem):
        return "%s.%s" % (skriv_uttryck(u.bas, UNAR_PRIORITET + 1),
                          _ascii(u.falt, "ett faltnamn"))
    if isinstance(u, M.Element):
        return "%s[%s]" % (skriv_uttryck(u.bas, UNAR_PRIORITET + 1),
                           ", ".join(skriv_uttryck(i) for i in u.index))
    if isinstance(u, M.Anrop):
        return "%s(%s)" % (_ascii(u.namn, "ett anropsnamn"),
                           ", ".join(_skriv_argument(a) for a in u.argument))
    if isinstance(u, M.Unar):
        inre = skriv_uttryck(u.operand, UNAR_PRIORITET)
        text = ("NOT " + inre) if u.op == "NOT" else ("-" + inre)
        return "(%s)" % text if yttre > UNAR_PRIORITET else text
    if isinstance(u, M.Binar):
        p = PRIORITET[u.op]
        if u.op in ("AND", "OR", "XOR"):
            # Jamforelser binder hardare an AND enligt IEC, men det ar en
            # klassisk lasfalla vid granskning. Parentesen runt jamforelsen
            # kostar inget, andrar inte tradet och forsvinner inte i lasaren,
            # sa turen-och-retur star kvar.
            text = "%s %s %s" % (_logikled(u.vanster, p), u.op,
                                 _logikled(u.hoger, p + 1))
            return "(%s)" % text if yttre > p else text
        if u.op in HOGERASSOCIATIVA:
            # Spegelvant mot fallet nedan: har ar det VANSTER operand som
            # maste parentesera vid samma prioritet, annars laser laesaren
            # (a ** b) ** c som a ** (b ** c).
            text = "%s %s %s" % (skriv_uttryck(u.vanster, p + 1),
                                 u.op, skriv_uttryck(u.hoger, p))
            return "(%s)" % text if yttre > p else text
        # Vänsterassociativt: höger operand måste parentesera vid samma
        # prioritet, annars läses a - (b - c) som (a - b) - c.
        text = "%s %s %s" % (skriv_uttryck(u.vanster, p),
                             u.op, skriv_uttryck(u.hoger, p + 1))
        return "(%s)" % text if yttre > p else text
    raise SkrivFel("vet inte hur %s skrivs" % type(u).__name__)


JAMFORELSER = ("=", "<>", "<", ">", "<=", ">=")


def _logikled(u: M.Uttryck, p: int) -> str:
    if isinstance(u, M.Binar) and u.op in JAMFORELSER:
        return "(%s)" % skriv_uttryck(u, 0)
    return skriv_uttryck(u, p)


def _skriv_argument(a: M.Argument) -> str:
    if a.namn is None:
        return skriv_uttryck(a.uttryck)
    return "%s %s %s" % (_ascii(a.namn, "ett argumentnamn"),
                         "=>" if a.ut else ":=", skriv_uttryck(a.uttryck))


def _skriv_etikett(e: M.Etikett) -> str:
    if e.till is None:
        return str(e.fran)
    return "%d..%d" % (e.fran, e.till)


def skriv_satser(satser, niva: int = 0):
    ut = []
    for s in satser:
        ut.extend(_skriv_sats(s, niva))
    return ut


def _rad(niva: int, text: str) -> str:
    return (INDRAG * niva + text).rstrip()


def _skriv_sats(s: M.Sats, niva: int):
    if isinstance(s, M.Kommentar):
        return [_rad(niva, "(* %s *)" % _ascii(s.text, "en kommentar"))]
    if isinstance(s, M.Tilldelning):
        return [_rad(niva, "%s := %s;" % (skriv_uttryck(s.mal),
                                          skriv_uttryck(s.uttryck)))]
    if isinstance(s, M.Anropssats):
        return [_rad(niva, "%s;" % skriv_uttryck(s.anrop))]
    if isinstance(s, M.Avbryt):
        return [_rad(niva, "EXIT;")]
    if isinstance(s, M.Retur):
        return [_rad(niva, "RETURN;")]
    if isinstance(s, M.Om):
        ut = []
        for i, g in enumerate(s.grenar):
            ord_ = "IF" if i == 0 else "ELSIF"
            ut.append(_rad(niva, "%s %s THEN" % (ord_, skriv_uttryck(g.villkor))))
            ut.extend(skriv_satser(g.satser, niva + 1))
        if s.annars is not None:
            ut.append(_rad(niva, "ELSE"))
            ut.extend(skriv_satser(s.annars, niva + 1))
        ut.append(_rad(niva, "END_IF;"))
        return ut
    if isinstance(s, M.Fall):
        ut = [_rad(niva, "CASE %s OF" % skriv_uttryck(s.uttryck))]
        for g in s.grenar:
            ut.append(_rad(niva, "%s:" % ", ".join(_skriv_etikett(e)
                                                   for e in g.etiketter)))
            ut.extend(skriv_satser(g.satser, niva + 1))
        if s.annars is not None:
            ut.append(_rad(niva, "ELSE"))
            ut.extend(skriv_satser(s.annars, niva + 1))
        ut.append(_rad(niva, "END_CASE;"))
        return ut
    if isinstance(s, M.ForSats):
        huvud = "FOR %s := %s TO %s" % (_ascii(s.styrvar, "en styrvariabel"),
                                        skriv_uttryck(s.fran), skriv_uttryck(s.till))
        if s.steg is not None:
            huvud += " BY %s" % skriv_uttryck(s.steg)
        ut = [_rad(niva, huvud + " DO")]
        ut.extend(skriv_satser(s.satser, niva + 1))
        ut.append(_rad(niva, "END_FOR;"))
        return ut
    if isinstance(s, M.Medan):
        ut = [_rad(niva, "WHILE %s DO" % skriv_uttryck(s.villkor))]
        ut.extend(skriv_satser(s.satser, niva + 1))
        ut.append(_rad(niva, "END_WHILE;"))
        return ut
    if isinstance(s, M.Upprepa):
        ut = [_rad(niva, "REPEAT")]
        ut.extend(skriv_satser(s.satser, niva + 1))
        ut.append(_rad(niva, "UNTIL %s" % skriv_uttryck(s.villkor)))
        ut.append(_rad(niva, "END_REPEAT;"))
        return ut
    raise SkrivFel("vet inte hur satsen %s skrivs" % type(s).__name__)


def skriv_deklaration(d: M.Deklaration, niva: int = 1) -> str:
    text = _ascii(d.namn, "ett variabelnamn")
    if d.adress:
        text += " AT %s" % _ascii(d.adress, "en adress")
    text += " : %s" % skriv_typ(d.typ)
    if d.init is not None:
        text += " := %s" % skriv_uttryck(d.init)
    text += ";"
    if d.skyddad:
        text += " {SAKERHET}"
    if d.kommentar:
        text += " (* %s *)" % _ascii(d.kommentar, "en kommentar")
    return _rad(niva, text)


def skriv_varblock(b: M.Varblock, niva: int = 0):
    huvud = " ".join((b.sort,) + b.kvalificerare)
    ut = [_rad(niva, huvud)]
    ut.extend(skriv_deklaration(d, niva + 1) for d in b.deklarationer)
    ut.append(_rad(niva, "END_VAR"))
    return ut


def skriv_pou(p: M.Pou) -> str:
    huvud = "%s %s" % (p.sort, _ascii(p.namn, "ett POU-namn"))
    if p.returtyp is not None:
        huvud += " : %s" % skriv_typ(p.returtyp)
    ut = [huvud]
    for b in p.block:
        ut.extend(skriv_varblock(b, 0))
    ut.extend(skriv_satser(p.kropp, 1))
    ut.append("END_%s" % p.sort)
    return "\n".join(ut) + "\n"


def skriv_strukturdef(sd: M.Strukturdef):
    ut = [_rad(1, "%s : STRUCT" % _ascii(sd.namn, "ett typnamn"))]
    ut.extend(skriv_deklaration(d, 2) for d in sd.falt)
    ut.append(_rad(1, "END_STRUCT;"))
    return ut


def skriv_enhet(e: M.Enhet) -> str:
    delar = []
    if e.typer:
        rader = ["TYPE"]
        for sd in e.typer:
            rader.extend(skriv_strukturdef(sd))
        rader.append("END_TYPE")
        delar.append("\n".join(rader) + "\n")
    for b in e.globala:
        delar.append("\n".join(skriv_varblock(b, 0)) + "\n")
    for p in e.pouer:
        delar.append(skriv_pou(p))
    return "\n".join(delar)
