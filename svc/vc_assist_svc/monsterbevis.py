# -*- coding: utf-8 -*-
"""Monstren som avgor domar, och bevisningen for dem.

FELKLASSEN, i en mening: ETT MONSTER SOM ALDRIG KORTS MOT TEXTEN DET SKA LASA.

Tre fall pa en natt hade samma form.

  * `skuld._ARLIGHET` var skriven i ASCII mot svensk text. Atta av elva grenar
    kunde aldrig matcha nagonting, och tva av dem var tillagda just for att
    fanga M-44 och M-47 - och fangade ingendera. (M-70)
  * `st.lexer._TIDSDEL` saknade `re.I` medan prefixregexen bredvid hade den.
    `T#3s` gick igenom, `T#3S` avvisades. IEC 61131-3 ar skiftlagesokansligt.
    Nio av sexton grinddomar i fas 9:s forsta modelldrivna korning var den
    falska rodgrinden. (M-96)
  * `harness.text.NEKANDE` ar ingen regex utan en ordlista, och den fyrade pa
    fel storhet: vilket nekande ord som helst i texten tystade
    arlighetsgrinden. (M-94)

Det gemensamma ar INTE att de ar regexar. Det ar att de ar MATCHARE SOM ALDRIG
KORTS MOT TEXTEN DE SKA LASA. Samma form drabbar ordlistor och handskrivna
parsrar lika hart.


HUR DEN HAR MODULEN MATER
-------------------------
Tva fragor, och bara den forsta ar en klassning:

1. AVGOR MONSTRET EN DOM, eller hjalper det bara till att TOLKA?

   Gransen ar mekanisk och gar vid TEXTENS PRODUCENT:

     TOLKANDE  monstret plockar isar en fil som Visual Components sjalvt har
               skrivit - .rsc, .vcmx, dess XML. Formen ar last av en producent
               vi inte ar, en miss ger ett falt som SAKNAS, och den som far
               tomt vet att fragan inte gick att besvara.
     DOMANDE   allt annat. Texten kommer fran en manniska, en sprakmodell, ett
               frammande verktygs utdata eller vart eget protokoll, och en miss
               andrar en anmarkning, ett fel, ett godkannande eller ett tal som
               rapporteras - TYST.

   MATT 2026-09-05: 116 monster pa modulniva under svc/ och ext/. 16 tolkar
   (fyra filformatslasare), 100 avgor en dom.

2. FINNS BEVISNING? Bada halvorna kravs, och de mater olika saker:

     FYRAR       ett prov som visar att monstret traffar nagot det SKA fanga
     FYRAR INTE  ett prov som visar att det INTE traffar nagot det inte ska

   Ett monster som fyrar pa allt mater lika lite som ett som aldrig fyrar. Bada
   halvorna ligger i `tests/enhet/test_monsterbevis.py` som konkreta strangar,
   och provas mot det LEVANDE kompilerade monstret.

VARFOR BEVISET AR ETT PROV OCH INTE EN OBSERVATION
--------------------------------------------------
Mätningen bakom M-105 gjordes genom att instrumentera varje monster och kora
hela enhetssviten: vilka fyrade, vilka fyrade aldrig. Den mätningen sager var
man ska sikta - men den ar INGET bevis. Att ett monster returnerade en traff
under sviten visar att det ANROPADES, inte att nagon KONTROLLERADE svaret, och
observationen forsvinner den dag det orelaterade provet skrivs om. Ett prov som
namnger bade en strang som MASTE matcha och en som INTE far det ar det enda som
overlever en refaktorering.
"""
from __future__ import annotations

import ast
import importlib
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Ett monster pa modulniva: `NAMN = re.compile(...)` eller `_NAMN = ...`.
_MONSTERNAMN = re.compile(r"^_?[A-Z][A-Z_0-9]*$")

# Katalogerna som svepet gar over.
KATALOGER = ("svc", "ext")


@dataclass(frozen=True)
class Monster:
    """Ett monster pa modulniva, sett ur kallan."""

    fil: str                  # relativ mot ROT
    rad: int
    namn: str
    kod: str

    @property
    def nyckel(self) -> str:
        return "%s::%s" % (self.fil, self.namn)

    @property
    def skiftlagesokanslig(self) -> bool:
        """Bar monstret re.I? Halva svaret pa M-96:s fraga."""
        return bool(re.search(r"re\.(I|IGNORECASE)", self.kod))

    @property
    def bar_diakriter(self) -> bool:
        """Star det a, a eller o i sjalva monstret? Halva svaret pa M-70:s."""
        return any(c in self.kod for c in "åäöÅÄÖ")


def monster(rot: str = ROT) -> Tuple[Monster, ...]:
    """Alla monster pa modulniva under svc/ och ext/, lasta ur kallan med AST.

    AST och inte grep: en regex over kallan hade varit precis den felklass
    modulen finns for att mata.
    """
    ut: List[Monster] = []
    for bas in KATALOGER:
        for kat, undermappar, filer in os.walk(os.path.join(rot, bas)):
            undermappar[:] = [d for d in undermappar
                              if d not in ("__pycache__", ".git")]
            for filnamn in sorted(filer):
                if not filnamn.endswith(".py"):
                    continue
                stig = os.path.join(kat, filnamn)
                with open(stig, "r", encoding="utf-8") as f:
                    kalla = f.read()
                try:
                    trad = ast.parse(kalla)
                except SyntaxError:
                    continue
                rader = kalla.splitlines()
                for nod in trad.body:
                    if not isinstance(nod, ast.Assign) or len(nod.targets) != 1:
                        continue
                    mal = nod.targets[0]
                    if not isinstance(mal, ast.Name):
                        continue
                    if not _MONSTERNAMN.match(mal.id):
                        continue
                    v = nod.value
                    if not (isinstance(v, ast.Call)
                            and isinstance(v.func, ast.Attribute)
                            and v.func.attr == "compile"):
                        continue
                    ut.append(Monster(
                        fil=os.path.relpath(stig, rot).replace(os.sep, "/"),
                        rad=nod.lineno, namn=mal.id,
                        kod="\n".join(rader[nod.lineno - 1:nod.end_lineno])))
    return tuple(ut)


# ---------------------------------------------------------------------------
# Klassningen: mätningens yta, 116 monster, klassade en gang for hand
# ---------------------------------------------------------------------------
#
# Listan ar ytan M-105 MATTE, inte "allt som nagonsin finns". Skalet ar mekaniskt
# och star i mätningens LIMITS: repot arbetar med flera samtidiga celler, och
# elva nya monster tillkom i tre andra moduler medan mätningen pagick. En sparre
# som raknar allt som finns just nu blir rod av nagon annans arbete i stallet
# for av sitt eget, och en sparre som blir rod av fel sak slutar lasas.
#
# Ett monster som forsvinner ur en fil FALLER daremot, se
# test_klassningen_pekar_pa_monster_som_finns. Ytan far krympa - men da med
# vett, inte tyst.

# TOLKANDE: de fyra lasarna over Visual Components EGNA filformat. Formen ar
# last av VC, och en miss lander i ett uttalat SAKNAS - "den som far tomt vet
# att fragan inte gick att besvara" (datablad.py:_familj).
#
# Det ar HAR gransen ar svarast, och det ska sagas rent ut: `katalogindex._NAMN`
# bygger falt som ett soklager sedan svarar "finns inte" pa. Att sokningens dom
# ar sokningens och inte monstrets ar ett OMDOME, inte en matning. Se M-105 §
# LIMITS.
_TOLKANDE_FILER: Dict[str, Tuple[str, ...]] = {
    "svc/vc_assist_svc/datablad.py": ("_HUVUD", "_STRANG"),
    "svc/vc_assist_svc/komponentfil.py": ("_TOKEN", "_FORTS", "_EGENSKAP"),
    "svc/vc_assist_svc/komponentdatablad.py": (
        "_KLAMMER", "_STRANGSLUT", "_ORD", "_BLANK", "_ARG", "_KATALOGFALT"),
    "svc/vc_assist_svc/katalogindex.py": (
        "_EGENSKAP", "_NAMN", "_KATEGORI", "_GRANSSNITT", "_PARAMETER"),
}

# DOMANDE: allt annat pa den mätta ytan. Motiveringen star per fil - den ar
# svaret pa fragan "vad blir en TYST miss har?".
_DOMANDE_FILER: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "ext/vc_addon/vc_assist/oga_kontrakt.py": (
        "ogats domskontrakt; en miss ar en malformed-dom i guldgrinden",
        ("_HUVUD", "_TEMPLATE", "_RUN", "_SEKTION", "_DOM")),
    "svc/vc_assist_svc/api_index.py": (
        "klassar API-namn och lintar VC-kod; en miss andrar indexets tal",
        ("_KONSTANTMONSTER", "_TYPMONSTER", "_PY2PRINT")),
    "svc/vc_assist_svc/forlopp/grind.py": (
        "grinden over forloppsytan domer PARET protokoll och text",
        ("_RAKNING", "_DOLDA")),
    "svc/vc_assist_svc/forlopp/yta.py": (
        "vilka sektioner ogat rapporterade; en miss ar en utebliven anmarkning",
        ("_SEKTIONSRAD",)),
    "svc/vc_assist_svc/harness/instruktioner.py": (
        "granskningen av modellens egna beteenderegler; varje miss ar en "
        "anmarkning eller en utebliven sadan",
        ("_REGEL_ID", "_FILNAMN", "_MATNING", "_INVARIANT", "_SKULD")),
    "svc/vc_assist_svc/harness/kodfallor.py": (
        "de matta fallorna i koden modellen skriver",
        ("_S_MED_U", "_U_STRANG")),
    "svc/vc_assist_svc/harness/text.py": (
        "textlagret arlighetsgrinden och verify-contract domer med; en miss "
        "gor att ett pastaende aldrig provas",
        ("_MENINGSSLUT", "_TAL", "_URI", "_BAKATCITAT", "_CITAT", "_VCTYP",
         "_VCKONST", "_MEDLEM")),
    "svc/vc_assist_svc/harness/verifiering.py": (
        "VERIFY-CONTRACT: talen ur verktygssvaren som modellens text provas mot",
        ("_TAL_I_STRANG",)),
    "svc/vc_assist_svc/personatackning.py": (
        "specdokumentet blir ett tackningstal som rapporteras",
        ("_RUBRIK", "_ANNAN_RUBRIK", "_TABELLRAD", "_KOD")),
    "svc/vc_assist_svc/plan/forfining.py": (
        "operatorens fria text; en omatt storhet blir en fraga till honom om "
        "nagot han redan har svarat pa",
        ("_ORD", "_MM", "_TAKT", "_CYKEL")),
    "svc/vc_assist_svc/plan/lasning.py": (
        "operatorens fria text till typade krav; en miss ar ett krav som tyst "
        "aldrig lastes",
        ("_YTA", "_SIDA", "_GANG", "_RACKVIDD", "_MED", "_DELARE",
         "_ORD_I_BIT", "_NA")),
    "svc/vc_assist_svc/plc/baslinje/morfologi.py": (
        "vad en tagg BETYDER; baslinjens jamforelsetal bygger pa den",
        ("_TAGG",)),
    "svc/vc_assist_svc/plc/baslinje/sprak.py": (
        "bankens krav- och sekvensrader till IR; en olast rad hamnar i "
        "`olasta`, och det talet rapporteras",
        ("_SIGNAL", "_TAL", "_TALORDRE", "_VERBORD", "_BRYT", "_NIVA", "_TILL",
         "_M_VAKT", "_M_UPPEHALL", "_M_ATERSTALL", "_M_KVITTENS", "_M_VID",
         "_M_VANTA_OCH", "_M_VANTA", "_M_HANDLING_OCH_VANTA",
         "_M_HANDLING_OCH_HALL", "_M_BARA_HANDLING", "_M_SATT_NAR",
         "_M_HANDLING_PA_FLANK", "_M_NOLLSTALL_NAR", "_M_HALL", "_M_FOLJ",
         "_M_RAKNA", "_M_LAGE", "_M_LARM", "_F_OMSESIDIG", "_F_FORVILLKOR",
         "_F_HALL", "_F_ENBART", "_F_PERMISSIV", "_F_CYKEL", "_F_HANDSPARR",
         "_F_AUTOSPARR", "_I_MELLAN", "_I_OMRADE", "_I_NAR", "_T_UTGANG",
         "_P_NUMMER", "_P_PUNKT", "_P_FORTSATT")),
    "svc/vc_assist_svc/plc/reparation.py": (
        "grindens egna markorer ur utdata; styr reparationsslingans varv",
        ("_MARKNING",)),
    "svc/vc_assist_svc/plc/signalkarta.py": (
        "kartan vagrar beskriva det den inte litar pa; en miss ar ett KartFel",
        ("_ADRESS", "_IDENT")),
    "svc/vc_assist_svc/plc/skelett.py": (
        "laset som bevisar att modellen holl sig i sitt fack",
        ("_ARBETSRAD", "_HAR_ADRESS")),
    "svc/vc_assist_svc/skuld.py": (
        "skuldregistrets domar om matningarna och koden",
        ("_ARLIGHET", "_KODMARKOR", "_RATTAR", "_NAMNER_M")),
    "svc/vc_assist_svc/st/lexer.py": (
        "M-96 matte att en miss har blir en falsk rodgrind, inte ett syntaxfel",
        ("_TIDSDEL", "_ADRESS")),
    "svc/vc_assist_svc/st/sekvens.py": (
        "namnkontrollen som stoppar en ogiltig CASE-sekvens",
        ("_IDENT",)),
    "svc/vc_assist_svc/st/strucpp_orakel.py": (
        "ett FRAMMANDE verktygs utdata blir differentialdomen mot var tolk",
        ("_CYKELRAD", "_SVARSRAD")),
    "svc/vc_assist_svc/verktyg/schema.py": (
        "verktygsschemats validering; en miss ar en utebliven anmarkning",
        ("_NAMN", "_VERSION")),
}


def _nycklar(tabell: Dict[str, Tuple[str, ...]]) -> frozenset:
    return frozenset("%s::%s" % (fil, n)
                     for fil, namn in tabell.items() for n in namn)


TOLKANDE = _nycklar(_TOLKANDE_FILER)
DOMANDE = _nycklar({fil: namn for fil, (_skal, namn)
                    in _DOMANDE_FILER.items()})
YTAN = TOLKANDE | DOMANDE


def motivering(nyckel: str) -> str:
    """Varfor monstret klassades som det gjorde."""
    fil = nyckel.split("::")[0]
    if fil in _TOLKANDE_FILER:
        return ("tolkar: plockar isar en fil Visual Components sjalvt har "
                "skrivit; en miss lander i ett uttalat SAKNAS")
    if fil in _DOMANDE_FILER:
        return "avgor en dom: " + _DOMANDE_FILER[fil][0]
    return "oklassad"


# ---------------------------------------------------------------------------
# Uppslag mot det LEVANDE monstret
# ---------------------------------------------------------------------------

def _sokvagar(rot: str) -> None:
    for p in (os.path.join(rot, "svc"),
              os.path.join(rot, "ext", "vc_addon", "vc_assist")):
        if p not in sys.path:
            sys.path.insert(0, p)


def hamta(nyckel: str, rot: str = ROT):
    """Det kompilerade monstret bakom nyckeln, hamtat ur den KORANDE modulen.

    Att ga via modulen och inte via kallan ar med flit: da provas monstret som
    koden faktiskt anvander det, och en flyttad konstant eller en omdopt modul
    faller i stallet for att tyst sluta provas.
    """
    _sokvagar(rot)
    fil, namn = nyckel.split("::")
    if fil.startswith("svc/"):
        modul = fil[len("svc/"):-len(".py")].replace("/", ".")
    elif fil.startswith("ext/vc_addon/vc_assist/"):
        modul = fil[len("ext/vc_addon/vc_assist/"):-len(".py")].replace("/", ".")
    else:
        raise KeyError("okand katalog i %r" % (nyckel,))
    m = importlib.import_module(modul)
    if not hasattr(m, namn):
        raise KeyError("%s finns inte i %s" % (namn, modul))
    return getattr(m, namn)


# ---------------------------------------------------------------------------
# Sparren
# ---------------------------------------------------------------------------

# Metoderna ett bevis far provas med. `sub`/`subn`/`split` ar med darfor att
# ett monster som BARA anvands for att stryka eller dela text anda avgor vad
# som blir kvar att doma pa.
METODER = ("match", "search", "fullmatch", "findall", "finditer", "split")


def fyrar(monstret, metod: str, text: str) -> bool:
    """Fyrade monstret pa texten, med den metod koden faktiskt anvander?"""
    if metod == "findall":
        return bool(monstret.findall(text))
    if metod == "finditer":
        return any(True for _ in monstret.finditer(text))
    if metod == "split":
        return len(monstret.split(text)) > 1
    return getattr(monstret, metod)(text) is not None


def granska_bevis(bevis: Dict[str, Tuple[str, Sequence[str], Sequence[str]]],
                  rot: str = ROT) -> List[str]:
    """Fel i sjalva bevistabellen: en strang som inte gor det den lovar.

    Det ar HAR den trasiga fixturen sitter. Ett bevis som pastar att monstret
    fyrar pa en strang, och inte gor det, faller.
    """
    fel: List[str] = []
    for nyckel in sorted(bevis):
        metod, traffar, missar = bevis[nyckel]
        if metod not in METODER:
            fel.append("%s: okand metod %r" % (nyckel, metod))
            continue
        try:
            m = hamta(nyckel, rot)
        except Exception as e:                                   # noqa: BLE001
            fel.append("%s: gar inte att hamta (%s: %s)"
                       % (nyckel, type(e).__name__, e))
            continue
        for text in traffar:
            if not fyrar(m, metod, text):
                fel.append("%s: skulle fyra pa %r men gjorde det inte"
                           % (nyckel, text))
        for text in missar:
            if fyrar(m, metod, text):
                fel.append("%s: skulle INTE fyra pa %r men gjorde det"
                           % (nyckel, text))
    return fel


def har_bada_halvorna(post) -> bool:
    """Bada halvorna kravs. Ett monster som fyrar pa allt mater lika lite."""
    _metod, traffar, missar = post
    return bool(traffar) and bool(missar)


def utan_bevis(bevis, rot: str = ROT) -> List[str]:
    """De DOMANDE monstren pa mätningens yta som saknar tvasidig bevisning."""
    return sorted(n for n in DOMANDE
                  if n not in bevis or not har_bada_halvorna(bevis[n]))


def halv_bevisning(bevis) -> List[str]:
    """De som har en halva men inte den andra - lika blinda som ingen alls."""
    return sorted(n for n in DOMANDE
                  if n in bevis and not har_bada_halvorna(bevis[n]))


def saknade_i_ytan(rot: str = ROT) -> List[str]:
    """Klassade monster som inte langre finns i kallan."""
    finns = set(m.nyckel for m in monster(rot))
    return sorted(YTAN - finns)


def nytt_sedan_matningen(rot: str = ROT) -> List[str]:
    """Monster som tillkommit efter M-105. RAPPORTERAS, faller inte.

    Se modulens kommentar vid klassningen: en sparre som blir rod av en annan
    cells arbete slutar lasas.
    """
    return sorted(m.nyckel for m in monster(rot) if m.nyckel not in YTAN)
