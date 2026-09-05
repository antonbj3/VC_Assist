# -*- coding: utf-8 -*-
"""Kanda skador i en fungerande losning. Facit ar mutationen sjalv.

## Varfor

Banken har 63 uppgifter, 26 med referenslosning. Det ar for lite for att mata
nagot om grindkedjans KANSLIGHET, och `M-111` visade problemet skarpt: 31 av
grind 2:s 68 fallplatser hade aldrig fyrat under hela provsviten.

En mutation loser det utan att fuska. Vi tar en losning som **passerar** alla
grindar, gor EN kand skada, och vet darmed exakt vad som maste fangas. Facit
kommer ur skadan - inte ur var egen domare, som `85_bankkontraktet.md` §2
forbjuder.

De 26 referenserna bar **2 192 brytpunkter**: 971 tilldelningar, 469
TRUE/FALSE-literaler, 282 AND/OR, 193 NOT, 79 jamforelser, 57 IF/ELSE, 42
timerinstanser, 42 tidsliteraler, 30 flankdetektorer, 27 CASE.

## Vad matningen faktiskt svarar pa

Inte "ar koden ratt" - det vet vi, den ar referensen. Utan:

**fangas skadan, och av VEM?**

En textmutation (obalanserat block, ogiltig tidsliteral) ska fangas av grind
1-2. En BETEENDEmutation (ett struket NOT, en flank som blir en niva) kan inte
fangas av en textgrind alls - den maste fangas av sparfacit. Att den slipper
igenom grind 2 ar alltsa RATT, och att den slipper igenom ALLT ar ett hal i
banken.

Det ar samma sak `54_felstallda_fragor.md` §3 efterlyste: andelen domar som
kraver att man ser mer an en fil.

## Fangad ar inte fangad av RATT skal

`M-115` bevisade tre oberoende vagar att flank- och latchfel ar OSYNLIGA for
varje sparbaserad verifierare: bankens spar med ett enda kolli gor korrekt och
trasig styrning byte-identiska, och skillnaden lever i ett matt band pa
220-900 ms som det fasta sparet aldrig nar.

Det forklarar ett resultat i forsta korningen som annars ser bra ut.
`FLANK_STRUKEN` (hette `FLANK_TILL_NIVA` fore C0) fangades 6 av 7 och `FLANKENS_Q_TILL_SIGNAL` 15 av 15 - men
av TEXTLAGRET: en struken flankdetektor gor variabeln odeklarerad, och `.Q`
utbytt mot instansen ger ett typfel. Beteendedefekten fangades aldrig.

Det var tur, inte en fungerande beteendegrind. En matning som bara raknar
"fangad" kan inte skilja de tva, och den skillnaden ar hela poangen. Darfor bar
varje `Skada` sitt `vantat_lager`: fangas en beteendeskada av textlagret ska det
rapporteras som en LYCKOTRAFF, inte som tackning.

## Tre rattelser (C0, mot M-122 §6.2)

* Initierare i VAR-block undantas fran `SANT_TILL_FALSKT`/`FALSKT_TILL_SANT`:
  matt 64 av 91 overlevare stod pa en saadan rad (M-122 §2) - ett startvarde
  som skrivs over innan det las ar ingen skada vard att rakna. Motorn hoppar
  over traffar pa VAR-rader och tar nasta traff i stallet, sa taket per sort
  fortfarande fylls med kodrader.
* Sorten som stryker flankdetektorns anrop heter `FLANK_STRUKEN` - det ar vad
  den gor. `FLANK_TILL_NIVA` heter nu vad DEN gor: `inst.Q` byts mot
  instansens CLK-signal (den riktiga F15, M-122 §3, M-115).
* `var_rader` ar radskanningen pa ETT stalle: bade motorn och korningen
  klassar radtyp med den. Den ar grov (radskanning, inte parsning - M-122
  LIMITS) och det star i korningens utdata sa lange det star kvar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass(frozen=True)
class Skada:
    """En kand skada i en fungerande kropp."""

    sort: str
    beskrivning: str
    # Vilket LAGER som rimligen ska fanga den. Inte ett lofte - en hypotes som
    # matningen provar, och en avvikelse ar fyndet.
    vantat_lager: str          # "text" (grind 1-3) eller "beteende" (sparfacit)
    kropp: str
    rad: int
    fore: str
    efter: str


def var_rader(kropp: str) -> frozenset:
    """1-baserade radnummer med deklarationer i VAR/VAR_INPUT/VAR_OUTPUT/...

    En RADSKANNING, inte en parsning (M-122 LIMITS): allt mellan en rad som
    borjar pa VAR och nasta END_VAR raknas som deklaration. Samma skanning
    kor korningens radtyp - pa ett stalle, inte tva.
    """
    rader = set()
    inne = False
    for i, rad in enumerate(kropp.split("\n"), 1):
        s = rad.strip().upper()
        if s.startswith("END_VAR"):
            inne = False
        elif s.startswith("VAR"):
            inne = True
        elif inne:
            rader.add(i)
    return frozenset(rader)


# (namn, monster, ersattning, vantat lager, beskrivning, undanta VAR-rader)
#
# undanta_var ar True bara for de tva booleska literalsorterna (M-122 §6.2):
# ett startvarde som skrivs over innan det las ar ingen skada. Tidsconstanter
# i VAR undantas INTE - ett T#500ms i deklarationen las ofta utan att
# skrivas, sa dar vore undantaget fel.
_SKADOR: List[Tuple[str, str, Callable, str, str, bool]] = [
    ("NOT_STRUKEN", r"\bNOT\s+", lambda m: "", "beteende",
     "ett NOT struket - villkoret blir sitt eget motsatta", False),
    ("AND_TILL_OR", r"\bAND\b", lambda m: "OR", "beteende",
     "AND blir OR - villkoret slapper igenom nar bara ett led haller", False),
    ("OR_TILL_AND", r"\bOR\b", lambda m: "AND", "beteende",
     "OR blir AND - villkoret kraver bada leden", False),
    ("SANT_TILL_FALSKT", r"\bTRUE\b", lambda m: "FALSE", "beteende",
     "TRUE blir FALSE - utgangen satts aldrig", True),
    ("FALSKT_TILL_SANT", r"\bFALSE\b", lambda m: "TRUE", "beteende",
     "FALSE blir TRUE - utgangen nollstalls aldrig", True),
    ("FLANK_STRUKEN", r"(\w+)\s*\(\s*CLK\s*:=\s*(\w+)\s*\)\s*;",
     lambda m: "(* flank struken *)", "beteende",
     "flankdetektorns anrop struket - Q blir aldrig sant (inte F15)", False),
    ("FLANKENS_Q_TILL_SIGNAL", r"(\w+)\.Q\b", lambda m: m.group(1),
     "beteende", "flankens Q byts mot instansen sjalv", False),
    ("TID_FORDUBBLAD", r"T#(\d+(?:\.\d+)?)(ms|s|m|h)\b",
     lambda m: "T#%s%s" % (float(m.group(1)) * 2, m.group(2)), "beteende",
     "tiden fordubblad - vakten faller utanfor sin brakett (F6)", False),
    ("TID_OGILTIG", r"T#(\d+(?:\.\d+)?)(ms|s|m|h)\b",
     lambda m: "T#%s" % m.group(1), "text",
     "tidsliteralen tappar sin enhet - grind 2 ska falla den", False),
    ("JAMFORELSE_VAND", r"(?<![:<>])(<=|>=|<|>)(?!=)",
     lambda m: {"<": ">", ">": "<", "<=": ">=", ">=": "<="}[m.group(1)],
     "beteende", "jamforelsen vand - villkoret galler tvartom", False),
    ("END_IF_STRUKEN", r"\bEND_IF\s*;", lambda m: "", "text",
     "ett END_IF struket - blocket balanserar inte (grind 2)", False),
    ("SEMIKOLON_STRUKET", r";", lambda m: "", "text",
     "ett semikolon struket - satsen avslutas inte", False),
    ("ICKE_ASCII", r"\(\*", lambda m: "(* ä", "text",
     "ett icke-ASCII-tecken i en kommentar - teckenkodningen agar vi inte",
     False),
]


def _flank_till_niva(kropp: str, per_sort: int) -> List[Skada]:
    """Den riktiga F15 (M-122 §3, M-115): `inst.Q` mot instansens CLK-signal.

    Vet motorn inte vilken CLK en instans laser pa finns inget att byta mot,
    och instansen hoppas over. TON/TOF-anrop utan CLK i kartan ligger
    utanfor: deras niva kommer ur IN-signalen, och det ar ett annat fel.
    """
    clk = dict(re.findall(r"(\w+)\s*\(\s*CLK\s*:=\s*([\w\.]+)\s*\)", kropp))
    if not clk:
        return []
    ut: List[Skada] = []
    for m in re.finditer(r"(\w+)\.Q\b", kropp):
        if len(ut) >= per_sort:
            break
        signal = clk.get(m.group(1))
        if signal is None or signal == m.group(0):
            continue
        rad = kropp[: m.start()].count("\n") + 1
        ut.append(Skada(
            sort="FLANK_TILL_NIVA",
            beskrivning="flankens Q byts mot CLK-signalen - villkoret las "
                        "pa niva i stallet for pa flank (F15)",
            vantat_lager="beteende",
            kropp=kropp[: m.start()] + signal + kropp[m.end():],
            rad=rad, fore=m.group(0), efter=signal))
    return ut


def skador(kropp: str, per_sort: int = 3) -> List[Skada]:
    """Alla kanda skador vi kan gora i en kropp, hogst `per_sort` av varje.

    Taket per sort finns for att 971 tilldelningar annars dranker de 30
    flankdetektorerna, och det ar flankarna som ar intressanta. Traffar pa
    VAR-rader hoppas over (C0) och taket fylls med nasta traff i stallet.
    """
    ut: List[Skada] = []
    for sort, monster, ers, lager, besk, undanta_var in _SKADOR:
        var = var_rader(kropp) if undanta_var else frozenset()
        n = 0
        for m in re.finditer(monster, kropp):
            if n >= per_sort:
                break
            rad = kropp[: m.start()].count("\n") + 1
            if rad in var:
                continue
            ny = kropp[: m.start()] + ers(m) + kropp[m.end():]
            if ny == kropp:
                continue
            ut.append(Skada(sort=sort, beskrivning=besk, vantat_lager=lager,
                            kropp=ny, rad=rad, fore=m.group(0),
                            efter=ers(m)))
            n += 1
    ut.extend(_flank_till_niva(kropp, per_sort))
    return ut
