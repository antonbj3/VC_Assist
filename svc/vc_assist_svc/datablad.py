# -*- coding: utf-8 -*-
"""Databladslagret: de storheter man behover for att VALJA en komponent.

VARFOR DEN HAR FILEN FINNS
--------------------------
`katalogindex.py` svarar pa VAD som finns i biblioteket: 3201 komponenter, 149
tillverkare (M-57). Den svarar inte pa om en robot nar 1,5 m eller 2,6 m, hur
manga axlar den har, eller hur snabbt ett band gar. Utan de talen kan varken en
manniska eller en sprakmodell VALJA - bara rakna upp.

TRE HARKOMSTKLASSER, MEKANISKT SKILDA
-------------------------------------
Varje tal bar `harkomst`:

  LAST      stod ordagrant i metadatan. `kalla` sager var.
  HARLEDD   raknat fram. `kalla` sager UR VAD och MED VILKEN FORMEL.
  SAKNAS    finns inte i datan. `kalla` sager vad som lettes efter.

Skillnaden ar inte prosa. Den ar ett falt, och den kan provas. En harledd siffra
som inte gar att skilja fran en avlast ar den tysta uppgraderingen fran gissning
till fakta som hela bygget star emot.

ETT FALT SOM INTE STAR I DATAN FYLLS ALDRIG I
---------------------------------------------
Frestelsen ar den har modulens huvudrisk: ett datablad dar varje falt star
ifyllt ser komplett ut och ljuger snyggt. `SAKNAS` ar ett forstklassigt svar och
skrivs ut, aldrig som noll och aldrig som tystnad.

RATTAD 2026-09-05. Raden ovan sa tidigare: "`nyttolast` (payload) finns INTE i
nagon av de 3201 filerna - matt i M-59." Den var fel, och den motsade dessutom
M-59:s EGEN tabell, som sager 426 av 2275 lasta. Tre tal om samma sak stod pa
tre stallen.

Det verkliga talet ar hogre an bada: `model.xml` deklarerar `MaxPayload` i
2986 av 3201, och `Reach` i 2556 (M-76). Ingen av de tva forsta matningarna
oppnade den filen.

Regeln ovan galler oforandrad. Det som foll var pastaendet att falter inte
FINNS - och det ar vart att notera att ett sant pastaende om en risk stod
bredvid ett falskt pastaende om datan, i samma stycke, utan att nagon marker
skillnaden.

SCHEMAT AR INTE ENHETLIGT
-------------------------
2665 unika parameternamn over biblioteket, och inget gemensamt Payload- eller
Reach-falt *i component.rsc*. (Katalogposten `model.xml` har bada deklarerade -
M-76 - men den lastes inte av den har modulen nar den skrevs.) Avbildningen fran STORHET till PARAMETERNAMN ar darfor matt
per komponentfamilj (M-59) och familjen bestams av vilka `Functionality`-block
komponenten bar - inte av katalognamnet, som ar tillverkarens mapp och heter
"sixx", "extra" och "ultra" lika ofta som "Robots" (M-58).

ROTENS VARIABELRYMD, INTE ALL TEXT
----------------------------------
`Length`, `Width` och `Height` finns i nastan varje komponent - men de sitter
till overvaldigande del i GEOMETRIPRIMITIVER (`rPrimitiveBoxFeature`), dar de
ar en lados matt och inte komponentens. Den har modulen laser darfor bara
rotnodens egen variabelrymd, den anvandaren ser i egenskapspanelen. En
oscopead sokning efter "Height" ger bandets sista rullstods hojd och ser
likadan ut som ett svar.

ORDFORRADET AR LITET MED FLIT
-----------------------------
En sprakmodell kan inte lara sig 2665 parameternamn. Den kan lara sig tjugo.
`STORHETER` nedan ar hela ordforradet, samma namn oavsett tillverkare, och
`saknas` nar datan inte bar storheten.
"""
from __future__ import annotations

import math
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import katalogindex

FORMAT = 1                      # Satt av M-59.

LAST = "last"
HARLEDD = "harledd"
SAKNAS = "saknas"

# Rackvidden ar den enda storheten som kan harledas pa TVA satt, och de tva
# talen ar inte samma matning. `harkomst` skiljer last fran harledd; de har tva
# markorerna skiljer de tva harledningarna, och de star ordagrant i `kalla` sa
# att skillnaden gar att lasa mekaniskt (M-179).
VAG_VARIABLER = "ur namngivna lanklangdsvariabler"
VAG_TRANSFORMER = "ur den kinematiska kedjans nodtransformer"

# ---------------------------------------------------------------------------
# Ordforradet
# ---------------------------------------------------------------------------

# Storhet -> (enhet, kort beskrivning). Enheten ar en del av storheten: ett tal
# utan enhet ar en falla, inte ett svar (operatorens krav pa formen).
#
# Listan ar HELA ordforradet. Vaxer den ska den vaxa med en matning, inte med
# ett infall - varje rad har ett matt tackningstal i M-59.
STORHETER: Dict[str, Tuple[str, str]] = {
    "frihetsgrader":     ("st",     "antal styrda leder"),
    "ledtyper":          ("",       "led for led: vridande eller skjutande"),
    "ledgranser":        ("grad/mm", "min och max per led"),
    "maxhastighet":      ("grad/s eller mm/s", "per led"),
    "maxacceleration":   ("grad/s2 eller mm/s2", "per led"),
    "rackvidd":          ("mm",     "hur langt armen nar"),
    "monteringsram":     ("",       "ramen ett verktyg skruvas fast i"),
    "basram":            ("",       "ramen komponenten star pa"),
    "styrenhet":         ("",       "robotstyrningens namn"),
    "kinematik":         ("",       "kinematikmodellens typ"),
    "nyttolast":         ("kg",     "vad den orkar bara"),
    "egenvikt":          ("kg",     "komponentens egen massa"),
    "verktygslast":      ("kg",     "massa satt pa en verktygsram"),
    "langd":             ("mm",     ""),
    "bredd":             ("mm",     ""),
    "hojd":              ("mm",     ""),
    "hastighet":         ("mm/s",   "transporthastighet"),
    "kapacitet":         ("st",     "hur manga produkter som ryms"),
    "granssnitt":        ("",       "namngivna anslutningar"),
    "monteringsgranssnitt": ("",    "anslutningar som monterar, inte floda"),
}

# Vilka storheter som hor till vilken familj, och i vilken ordning de ska
# visas. En storhet som INTE star har for familjen ar inte "saknas" - den ar
# INTE TILLAMPLIG, och de tva ar olika svar. Att fraga efter en robots
# bandhastighet ar en fraga som inte har ett varde, inte ett hal i datan.
FAMILJENS_STORHETER: Dict[str, Tuple[str, ...]] = {
    "robot": ("frihetsgrader", "ledtyper", "ledgranser", "maxhastighet",
              "maxacceleration", "rackvidd", "monteringsram", "basram",
              "styrenhet", "kinematik", "nyttolast", "egenvikt",
              "verktygslast", "granssnitt"),
    "transportor": ("langd", "bredd", "hojd", "hastighet", "kapacitet",
                    "granssnitt", "egenvikt"),
    "verktyg": ("monteringsgranssnitt", "egenvikt", "nyttolast", "granssnitt",
                "frihetsgrader", "ledtyper", "ledgranser"),
    "ovrig": ("granssnitt", "langd", "bredd", "hojd", "egenvikt"),
}

# De storheter som ryms i den KORTA formen per familj. Kort ar standard: en
# agent som vager tio robotar mot varandra far inte branna sin kontext pa ett
# falt den inte fragade efter. Talen for vad formerna kostar star i M-59.
KORTA_STORHETER: Dict[str, Tuple[str, ...]] = {
    "robot": ("frihetsgrader", "rackvidd", "nyttolast", "kinematik",
              "monteringsram"),
    "transportor": ("langd", "bredd", "hojd", "hastighet", "kapacitet"),
    "verktyg": ("monteringsgranssnitt", "frihetsgrader", "ledgranser"),
    "ovrig": ("granssnitt",),
}

# ---------------------------------------------------------------------------
# Familjen lases ur STRUKTUREN, inte ur katalognamnet
# ---------------------------------------------------------------------------

# Ordningen ar en prioritetsordning, och MATT i M-59 avgor den ingenting: NOLL
# av 3201 komponenter bar bade en robotstyrning och en transportbana. Ordningen
# star kvar for den dag en sadan komponent dyker upp, och att den aldrig har
# provats star har i stallet for att antas fungera.
#
# Familjen lases ur strukturen och inte ur katalognamnet, och skillnaden ar
# stor (M-59): katalogen "Robots" har 1736 komponenter och alla ar robotar -
# men 466 robotar TILL ligger i kataloger som heter Archiv, Legacy, extra och
# ultra. For transportorer ar det varre: 45 i "Conveyors", 182 utanfor.
FAMILJEMARKORER: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("robot", ("rSimRobotController", "rSimRrsRobotController")),
    ("transportor", ("rOneWayPath", "rTwoWayPath", "rSimCapacityBlock",
                     "rTransportNode")),
    ("verktyg", ("rToolContainer",)),
)

# VC:s varldsenhet ar millimeter. MATT i M-33, inte antaget.
_ENHET_UR_QUANTITY = {
    "Distance": "mm",
    "Angle": "grad",
    "Angular velocity": "grad/s",
    "Angular acceleration": "grad/s2",
    "Velocity": "mm/s",
    "Speed": "mm/s",
    "Acceleration": "mm/s2",
    "Time": "s",
    "Percentage": "%",
}


class Databladsfel(Exception):
    pass


# ---------------------------------------------------------------------------
# Ett varde med harkomst
# ---------------------------------------------------------------------------

@dataclass
class Varde:
    """Ett tal, en lista eller ett namn - och VAR det kommer ifran.

    `harkomst` ar LAST, HARLEDD eller SAKNAS. `kalla` ar obligatorisk i alla
    tre fallen: for LAST var det stod, for HARLEDD vilken formel som anvandes,
    for SAKNAS vad som lettes efter. Ett falt utan kalla far inte finnas -
    darfor faller konstruktorn pa det.
    """

    storhet: str
    varde: object = None
    enhet: str = ""
    harkomst: str = SAKNAS
    kalla: str = ""

    def __post_init__(self):
        if self.harkomst not in (LAST, HARLEDD, SAKNAS):
            raise Databladsfel("unknown provenance %r" % (self.harkomst,))
        if not self.kalla:
            raise Databladsfel(
                "%s: ett varde utan kalla ar inte ett varde" % self.storhet)
        if self.harkomst == SAKNAS and self.varde is not None:
            raise Databladsfel(
                "%s: harkomst SAKNAS men vardet ar %r" % (self.storhet,
                                                          self.varde))
        if self.harkomst != SAKNAS and self.varde is None:
            raise Databladsfel(
                "%s: harkomst %s utan varde" % (self.storhet, self.harkomst))

    @property
    def finns(self) -> bool:
        return self.harkomst != SAKNAS

    def till_json(self, kort: bool = False) -> Dict[str, object]:
        """Vardet som JSON. `kort` stryker kallan, ALDRIG harkomsten.

        MATT i M-59: kallorna ar tva tredjedelar av ett kort datablads tecken.
        Att stryka dem halverar kostnaden - men den mekaniska skillnaden mellan
        last, harledd och saknas ar just faltet `harkomst`, och det faltet star
        kvar i bada formerna. Det ar den skillnaden regeln handlar om.
        """
        d: Dict[str, object] = {"harkomst": self.harkomst}
        if not kort:
            d["kalla"] = self.kalla
        if self.harkomst != SAKNAS:
            d["varde"] = self.varde
            if self.enhet:
                d["enhet"] = self.enhet
        return d

    def text(self, kort: bool = False) -> str:
        """En rad som bar sitt eget svar.

        "rackvidd: 2944 mm (harledd ur lanklangderna)" ar anvandbart.
        "Reach: 2944" ar en falla. Formen ar darfor inte forhandlingsbar.

        `kort=True` lamnar kvar ORDEN last/harledd/saknas men stryker den langa
        kallan. Harkomsten far aldrig falla bort - det ar hela poangen - men
        den behover inte kosta tvahundra tecken per rad i en lista pa tio.
        """
        if self.harkomst == SAKNAS:
            return ("%s: saknas" % self.storhet if kort
                    else "%s: saknas (%s)" % (self.storhet, self.kalla))
        v = self.varde
        listvarde = isinstance(v, (list, tuple))
        if isinstance(v, float):
            v = ("%.6g" % v)
        elif listvarde:
            v = ", ".join(_postrad(x) for x in v)
        ut = "%s: %s" % (self.storhet, v)
        if self.enhet and not listvarde:
            ut += " " + self.enhet
        if self.harkomst == HARLEDD:
            ut += (" (harledd)" if kort else " (harledd: %s)" % self.kalla)
        return ut


def _postrad(x) -> str:
    """En post i en ledlista som EN kort strang.

    Ledgranserna ar sex ordboksrader i JSON och det ar ratt for en maskin. I
    text ar samma sak "Axis1 -170..170 grad" - samma innehall, en femtedel av
    tecknen. Vilket som ar ratt beror pa vem som laser, sa bada finns.
    """
    if not isinstance(x, dict):
        return str(x)
    if "varde" in x:
        if x.get("varde") is None:
            return "%s -" % x.get("led", "?")
        return "%s %g%s" % (x.get("led", "?"), x["varde"],
                            (" " + x["enhet"]) if x.get("enhet") else "")
    lo = x.get("min", x.get("min_uttryck", "-"))
    hi = x.get("max", x.get("max_uttryck", "-"))
    if isinstance(lo, str) and len(lo) > 18:
        lo = "uttryck"
    if isinstance(hi, str) and len(hi) > 18:
        hi = "uttryck"
    lo = "%g" % lo if isinstance(lo, float) else lo
    hi = "%g" % hi if isinstance(hi, float) else hi
    return "%s %s..%s%s" % (x.get("led", "?"), lo, hi,
                            (" " + x["enhet"]) if x.get("enhet") else "")


def last(storhet, varde, kalla, enhet="") -> Varde:
    return Varde(storhet, varde, enhet or STORHETER.get(storhet, ("", ""))[0],
                 LAST, kalla)


def harledd(storhet, varde, formel, enhet="") -> Varde:
    return Varde(storhet, varde, enhet or STORHETER.get(storhet, ("", ""))[0],
                 HARLEDD, formel)


def saknas(storhet, skal) -> Varde:
    return Varde(storhet, None, "", SAKNAS, skal)


# ---------------------------------------------------------------------------
# .rsc-lasaren
# ---------------------------------------------------------------------------

_HUVUD = re.compile(r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*(.*)$')
_STRANG = re.compile(r'"([^"]*)"')


@dataclass
class Block:
    """En nod i .rsc-tradet: `Namn "arg" { ... }`."""

    namn: str
    arg: str = ""
    rader: List[Tuple[str, str]] = field(default_factory=list)
    barn: List["Block"] = field(default_factory=list)

    def sok(self, namn: str, arg: Optional[str] = None) -> List["Block"]:
        ut = []
        for b in self.barn:
            if b.namn == namn and (arg is None or b.arg == arg):
                ut.append(b)
        return ut

    def alla(self, namn: str) -> List["Block"]:
        """Rekursivt over hela tradet."""
        ut = []
        for b in self.barn:
            if b.namn == namn:
                ut.append(b)
            ut.extend(b.alla(namn))
        return ut

    def rad(self, nyckel: str) -> Optional[str]:
        for k, v in self.rader:
            if k == nyckel:
                return v
        return None

    def strang(self, nyckel: str) -> Optional[str]:
        v = self.rad(nyckel)
        if v is None:
            return None
        m = _STRANG.search(v)
        return m.group(1) if m else v.strip()


# Geometrifeatures ar 90 procent av texten och bar bara ritdata. De hoppas over
# UTAN att laggas i tradet - men brakparen raknas, sa strukturen halls hel.
_HOPPAS_OVER = ("Feature",)


def _logiska_rader(text: str) -> List[str]:
    """Rader dar VC:s radbrytning inne i en strang ar hoplagd igen.

    VC bryter langa uttryck med ett avslutande bakstreck mitt i strangen:
        Expression "Tz(Kinematics::L01Z).Tx(Kinematics::L12X)\\
    .Ry(-Kinematics::JointZeroOffset2)"
    Den som laser rad for rad far da ett halvt uttryck och ser det inte.
    """
    if "\\\n" in text:
        text = text.replace("\\\n", "")
    return text.split("\n")


def las_trad(text: str) -> Block:
    """.rsc-texten som ett trad. Geometrifeatures hoppas over."""
    rot = Block("*ROT*")
    stack = [rot]
    rader = _logiska_rader(text)
    i = 0
    n = len(rader)
    hoppa_djup = None
    djup = 0
    while i < n:
        rad = rader[i].strip()
        i += 1
        if not rad:
            continue
        if rad == "{":
            djup += 1
            continue
        if rad == "}":
            djup -= 1
            if hoppa_djup is not None and djup < hoppa_djup:
                hoppa_djup = None
            elif hoppa_djup is None and len(stack) > 1:
                stack.pop()
            continue
        if hoppa_djup is not None:
            continue
        m = _HUVUD.match(rad)
        if not m:
            continue
        nyckel, rest = m.group(1), m.group(2).strip()
        # Ar nasta icke-tomma rad en oppningsparentes ar det ett block.
        j = i
        while j < n and not rader[j].strip():
            j += 1
        if j < n and rader[j].strip() == "{":
            sm = _STRANG.match(rest)
            arg = sm.group(1) if sm else rest
            if nyckel in _HOPPAS_OVER:
                hoppa_djup = djup + 1
            else:
                b = Block(nyckel, arg)
                stack[-1].barn.append(b)
                stack.append(b)
        else:
            stack[-1].rader.append((nyckel, rest))
    return rot


def _rot_nod(trad: Block) -> Optional[Block]:
    for b in trad.sok("Node"):
        if b.arg == "rSimResource":
            return b
    return None


def _tal(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    s = s.strip().strip('"')
    try:
        return float(s)
    except ValueError:
        return None


@dataclass
class Variabel:
    namn: str
    varde: str
    typ: str = ""
    quantity: str = ""

    @property
    def enhet(self) -> str:
        return _ENHET_UR_QUANTITY.get(self.quantity, "")


def _variabler(rymd: Optional[Block]) -> Dict[str, Variabel]:
    """Namn -> Variabel ur EN variabelrymd. Ingen rekursion, med flit."""
    ut: Dict[str, Variabel] = {}
    if rymd is None:
        return ut
    for v in rymd.sok("Variable"):
        namn = v.strang("Name")
        if namn is None:
            continue
        varde = v.rad("Value")
        if varde is None:
            # Uttrycksvariabler bar sitt varde i ett underblock.
            for u in v.sok("Value"):
                e = u.strang("Expression")
                if e is not None:
                    varde = '"%s"' % e
                    break
        q = v.strang("Quantity") or ""
        ut[namn] = Variabel(namn, (varde or "").strip(), v.arg, q)
    return ut


def rotvariabler(trad: Block) -> Dict[str, Variabel]:
    """Komponentens EGNA egenskaper: rotnodens variabelrymd, inget annat.

    Det ar de faltet anvandaren ser i egenskapspanelen. En `Height` langre in i
    tradet ar en geometriprimitivs hojd och sager ingenting om komponenten.
    """
    rot = _rot_nod(trad)
    if rot is None:
        return {}
    for r in rot.sok("VariableSpace"):
        return _variabler(r)
    return {}


def funktioner(trad: Block) -> List[Block]:
    return trad.alla("Functionality")


def funktionsnamn(trad: Block) -> List[str]:
    return sorted(set(b.arg for b in funktioner(trad)))


# ---------------------------------------------------------------------------
# Avbildningen storhet -> parameternamn, matt per familj (M-59)
# ---------------------------------------------------------------------------

# Ordningen ar en prioritetsordning. Antalet komponenter varje namn traffar
# star i M-59; ett namn utan matt traff hor inte hemma i listan.
NYTTOLAST_FALT = ("MaxLoad", "MaxPayload", "Payload")
LANGD_FALT = ("ConveyorLength",)
BREDD_FALT = ("ConveyorWidth",)
HOJD_FALT = ("ConveyorHeight",)
HASTIGHET_FALT = ("ConveyorSpeed",)
KAPACITET_FALT = ("Advanced::ConveyorCapacity", "Advanced::Capacity_Section1")

# Falt som SER ut som svaret men mater nagot annat. De star har for att nasta
# lasare inte ska "hitta" dem igen - varje rad ar en matning i M-59.
FORKASTADE_FALT = {
    "WT_Weight": "Werkstucktragerns vikt - lastbararen som ATER pa bandet, "
                 "inte bandets egen. Bar Quantity Mass och ser darfor ut som "
                 "en egenvikt.",
    "Advanced::StructureWeight": "en PROCENTSATS (Quantity Percentage, vardet "
                                 "0,6 i alla 11) for ytutnyttjande - ordet "
                                 "Weight bar ingen massa har.",
    "Radius": "ett uttryck (0.5*sassd(145,180-J1,75)) som ritar en cirkel i "
              "vyn, inte ett matt pa rackvidden.",
    "WorkSpace::Envelope": "en bock for att VISA arbetsomradet (rBool), inte "
                           "arbetsomradets storlek.",
}

# Filens massenhet ar gram. MATT i M-59: MaxLoad = 20000 i KUKA KR 20, 12000 i
# KR 12, 3000 i en 3 kg-robot - modellnumret ar kilo och faltet ar tusen ganger
# storre. Talet skrivs darfor om till kilo, och att det ar gjort star i kallan.
GRAM_PER_KILO = 1000            # Satt av M-59.

# En negativ massa ar ingen massa. VC skriver -1000 i TOOL_DATA nar ingen last
# ar satt, och den som laser raden rakt av far en minus-kilos verktygslast.
# MATT i M-59: 351 komponenter bar exakt det vardet.
_INGEN_MASSA = -1000            # Satt av M-59.


def _rot_var_tal(rotvar: Dict[str, Variabel], falt: Sequence[str]):
    """Forsta faltet i `falt` som finns OCH bar ett tal. (namn, tal, Variabel)."""
    for namn in falt:
        v = rotvar.get(namn)
        if v is None:
            continue
        t = _tal(v.varde)
        if t is None:
            continue
        return namn, t, v
    return None, None, None


# ---------------------------------------------------------------------------
# Robotens leder
# ---------------------------------------------------------------------------

_LEDTYP = {"Rotational": "vridande", "Translational": "skjutande",
           "RotationalFollower": "vridande foljare",
           "TranslationalFollower": "skjutande foljare",
           "Fixed": "fast"}

_LEDENHET = {"vridande": "grad", "vridande foljare": "grad",
             "skjutande": "mm", "skjutande foljare": "mm"}


def _styrenhet(trad: Block) -> Optional[Block]:
    for b in trad.alla("Functionality"):
        if b.arg in ("rSimRobotController", "rSimRrsRobotController"):
            return b
    return None


def _kinematik(trad: Block) -> Optional[Block]:
    for b in trad.alla("Functionality"):
        if b.arg.startswith("rKin") or b.arg == "rPythonKinematics":
            return b
    return None


def _ledordning(ctl: Optional[Block]) -> List[str]:
    """Ledernas namn i styrenhetens ordning, ur JointMap."""
    if ctl is None:
        return []
    ut = []
    for jm in ctl.sok("JointMap"):
        for k, v in jm.rader:
            if k != "Joint":
                continue
            m = _STRANG.search(v)
            if m:
                ut.append(m.group(1))
    return ut


def _dofar(trad: Block) -> Dict[str, Block]:
    ut = {}
    for d in trad.alla("Dof"):
        n = d.strang("Name")
        if n and n not in ut:
            ut[n] = d
    return ut


def _granssnittsblock(trad: Block) -> List[Block]:
    return [b for b in trad.alla("Functionality") if b.arg == "rSimInterface"]


def _monterar(iface: Block) -> bool:
    """Bar granssnittet ett hierarkifalt med Mount satt?

    Det ar skillnaden mellan ett granssnitt som MONTERAR (en robotfot i ett
    postbord, ett verktyg i en flans) och ett som bara flodar produkter.
    """
    for sek in iface.sok("Section"):
        for falt in sek.sok("Fields"):
            for h in falt.sok("rSimHierarchyField"):
                if (_tal(h.rad("Mount")) or 0) != 0:
                    return True
    return False


# ---------------------------------------------------------------------------
# Rackvidden - en HARLEDNING, och den skrivs ut som en
# ---------------------------------------------------------------------------

def _hyp(*t):
    s = 0.0
    for x in t:
        s += (x or 0.0) ** 2
    return s ** 0.5


def _kin_tal(kin: Block, rotvar: Dict[str, Variabel], namn: str):
    """Lanklangd ur kinematikblocket, annars ur rotens variabelrymd.

    rPythonKinematics bar sin kinematik som ett Python-skript och lagger
    lanklangderna i komponentens EGNA variabler i stallet. Bada stallena maste
    provas; att bara lasa blocket ger 576 tomma svar.
    """
    v = None
    if kin is not None:
        v = _tal(kin.rad(namn))
    if v is None and namn in rotvar:
        v = _tal(rotvar[namn].varde)
    return v


def _rackvidd(trad: Block, kin: Optional[Block],
              rotvar: Dict[str, Variabel]) -> Varde:
    """Hur langt armen nar, raknad ur lanklangderna. HARLEDD, aldrig last.

    FACIT UTANFOR KODEN. 407 robotar bar tillverkarens egen rackvidd i sitt
    MODELLNAMN - "KR 210 R2700" ar 2700 mm, "IRB 6700-300/2.60" ar 2,60 m. Det
    talet kommer inte ur den har formeln, sa det gar att prova mot.

    Provet valde ocksa formeln, och det ar den intressanta raden i M-59: att
    summera ALLA lanklangder ger median 1,086 mot namnet - atta procent for
    langt, systematiskt. Utan den sista lanken L56, flansens egen forskjutning,
    blir medianen 1,001 och 379 av 386 ligger inom fem procent. Tillverkaren
    matter till handledens centrum, inte till flansen. Formeln nedan ar den
    valda, och att den ar VALD mot ett facit star har for att nasta lasare inte
    ska tro att den foll ut ur geometrin av sig sjalv.

    Ledgranserna ar inte inraknade. En arm vars led 3 inte kan strackas helt
    nar kortare an summan, sa talet ar en ovre grans - men en ovre grans som
    ligger 0,1 procent fran tillverkarens tal i median, inte 8.

    TVA VAGAR, OCH DEN HAR HAR FORETRADE. Sedan M-179 finns en andra harledning
    som gar kedjans NODTRANSFORMER och inte beror pa vad nagon dopt sina
    variabler till. Den taper bredare - men bredare tackning ar inget skal att
    byta dar bada kan svara. MATT i M-179: av de 149 robotar dar vagarna skiljer
    sig mer an fem procent ligger den har formeln narmare model.xml:s
    deklarerade Reach i 86 fall och transformvagen i 47. Transformvagen fyller
    darfor bara luckorna, och den sager i sin kalla att den gjort det.
    """
    variabelsvar = _rackvidd_ur_variabler(kin, rotvar)
    if variabelsvar.finns:
        return variabelsvar
    transformsvar = _rackvidd_ur_transformer(trad)
    if transformsvar.finns:
        return transformsvar
    return saknas("rackvidd", "%s; %s" % (variabelsvar.kalla,
                                          transformsvar.kalla))


def _rackvidd_ur_variabler(kin: Optional[Block],
                           rotvar: Dict[str, Variabel]) -> Varde:
    """Den formel M-59 valde mot facit: summan av de NAMNGIVNA lanklangderna."""
    if kin is None:
        return saknas("rackvidd", "%s: inget kinematikblock i filen"
                                  % VAG_VARIABLER)
    typ = kin.arg

    def t(n):
        return _kin_tal(kin, rotvar, n)

    # Kedjan kanns igen pa sina VARIABLER, inte pa blockets typnamn.
    #
    # MATT 2026-09-05: av de 509 robotar som saknade rackvidd bar 143 exakt de
    # artikulerade namnen L12X/L23Z/L34*/L45* men har typen rPythonKinematics.
    # De definierar sin kinematik i ett skript och behaller kedjans namn; den
    # artikulerade formeln raknar dem korrekt. Att lasa typnamnet i stallet for
    # variablerna gjorde 143 robotar rackviddslosa utan att datan saknades.
    # Kvar star 293 utan L-namn alls (en annan kedjeform) och 73 med dem bara
    # delvis - de forblir saknas, och det ar ratt.
    artikulerad_kedja = t("L12X") is not None and t("L23Z") is not None
    if typ == "rKinArticulated2" or artikulerad_kedja:
        if not artikulerad_kedja:
            return saknas("rackvidd",
                          "%s: rKinArticulated2 utan lanklangderna L12X/L23Z"
                          % VAG_VARIABLER)
        delar = [t("L12X"), _hyp(t("L23X"), t("L23Z")),
                 _hyp(t("L34X"), t("L34Z")), _hyp(t("L45X"), t("L45Z"))]
        formel = ("L12X+|L23|+|L34|+|L45| %s i den artikulerade kedjan "
                  "(blocktyp %s; flanslanken L56 ar inte med, tillverkaren "
                  "matter till handledscentrum); provad mot 386 modellnamn, "
                  "median 1,001 (M-59)" % (VAG_VARIABLER, typ))
    elif typ == "rKinScara2":
        a, b = t("L12X"), t("L23X")
        if a is None or b is None:
            return saknas("rackvidd", "%s: rKinScara2 utan L12X/L23X"
                                      % VAG_VARIABLER)
        delar = [a, b]
        formel = ("OVRE GRANS: L12X+L23X %s i rKinScara2, ledgranser ej "
                  "inraknade" % VAG_VARIABLER)
    else:
        # rKinParallellogram och de rPythonKinematics som lagger sina matt i
        # komponentens egna variabler bar samma namn: LinkLength1..5 och
        # JointOffset1..4. Avbildningen till kedjan star i palletterarnas egna
        # kinematikskript (OnFinalize) och ar last darifran, inte gissad.
        j12x, j23x, j23z = t("JointOffset1"), t("JointOffset4"), t("LinkLength2")
        j34x, j34z, j46x = t("LinkLength3"), t("JointOffset3"), t("LinkLength4")
        if j12x is None or j23z is None or j34x is None:
            return saknas(
                "rackvidd",
                "%s: %s utan lanklangder i blocket eller i rotens variabler"
                % (VAG_VARIABLER, typ))
        delar = [j12x, _hyp(j23x, j23z), _hyp(j34x, j34z), j46x or 0.0]
        formel = ("OVRE GRANS: JointOffset1 + |LinkLength2,JointOffset4| + "
                  "|LinkLength3,JointOffset3| + LinkLength4 %s i %s"
                  % (VAG_VARIABLER, typ))
    return harledd("rackvidd", round(sum(d or 0.0 for d in delar), 1), formel,
                   "mm")


# ---------------------------------------------------------------------------
# Rackvidden ur NODTRANSFORMERNA - den generella vagen (M-179)
#
# Formeln ovan laser NAMN: L12X, L23Z, LinkLength2. Den ar bara sa bred som
# tillverkarnas namngivning, och tva matningar i rad har gatt at att flytta
# den gransen (M-59 -> M-177). Kedjan sjalv star i filen oberoende av vad
# nagon dopt sina variabler till: varje led ar en `Node "rSimLink"` med ett
# `Offset`, och offsetens translationsdel AR lanklangden.
#
# Uttrycken ser ut sa har, och alla operatorer i biblioteket ryms i listan:
#   Tx/Ty/Tz  Rx/Ry/Rz  Sx/Sy/Sz  Identity()  Set(16 tal)
# med Tz(Kinematics::L01Z), Ty(0.5*Kinematics::ConnectorWidth) och rena tal som
# argument. Symbolerna bor i rotens variabelrymd eller i funktionsblockets egna
# rader. En symbol som INTE gar att losa ger saknas - aldrig ett antagande.
# ---------------------------------------------------------------------------


class _Olost(Exception):
    """En del av kedjan gick inte att lasa. Barer skalet, inte ett tal."""


_UTTRYCKSTECKEN = re.compile(r"""
    (?P<tal>\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?)
  | (?P<namn>[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*(?:\.[XYZW])?)
  | (?P<op>[-+*/(),])
  | (?P<blank>\s+)
""", re.X)

_OFFSETLED = re.compile(r'([A-Za-z][A-Za-z0-9_]*)\s*\(')


def _tecken(text: str) -> List[Tuple[str, str]]:
    ut = []
    i = 0
    while i < len(text):
        m = _UTTRYCKSTECKEN.match(text, i)
        if not m:
            raise _Olost("okant tecken %r" % (text[i],))
        i = m.end()
        if m.lastgroup != "blank":
            ut.append((m.lastgroup, m.group()))
    return ut


def _uttrycksfunktion(namn: str, arg: List[float]) -> float:
    """VC:s gradbaserade trigonometri. En okand funktion ar OLOST, inte noll."""
    if namn == "sind" and len(arg) == 1:
        return math.sin(math.radians(arg[0]))
    if namn == "cosd" and len(arg) == 1:
        return math.cos(math.radians(arg[0]))
    if namn == "tand" and len(arg) == 1:
        return math.tan(math.radians(arg[0]))
    if namn == "atand" and len(arg) == 1:
        return math.degrees(math.atan(arg[0]))
    if namn == "atan2d" and len(arg) == 2:
        return math.degrees(math.atan2(arg[0], arg[1]))
    raise _Olost("okand funktion %s/%d" % (namn, len(arg)))


class _Uttryck:
    """Rekursiv nedstigning over ett VC-uttryck. Okand symbol -> _Olost."""

    def __init__(self, tecken, slauppe):
        self.t = tecken
        self.i = 0
        self.slauppe = slauppe

    def _kika(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def _ta(self):
        v = self._kika()
        self.i += 1
        return v

    def uttryck(self) -> float:
        v = self._term()
        while self._kika()[1] in ("+", "-"):
            op = self._ta()[1]
            h = self._term()
            v = v + h if op == "+" else v - h
        return v

    def _term(self) -> float:
        v = self._faktor()
        while self._kika()[1] in ("*", "/"):
            op = self._ta()[1]
            h = self._faktor()
            if op == "*":
                v = v * h
            else:
                if h == 0:
                    raise _Olost("division med noll")
                v = v / h
        return v

    def _faktor(self) -> float:
        sort, txt = self._kika()
        if txt == "-":
            self._ta()
            return -self._faktor()
        if txt == "+":
            self._ta()
            return self._faktor()
        if txt == "(":
            self._ta()
            v = self.uttryck()
            if self._kika()[1] != ")":
                raise _Olost("obalanserad parentes")
            self._ta()
            return v
        if sort == "tal":
            self._ta()
            return float(txt)
        if sort == "namn":
            self._ta()
            if self._kika()[1] == "(":
                self._ta()
                arg = []
                if self._kika()[1] != ")":
                    arg.append(self.uttryck())
                    while self._kika()[1] == ",":
                        self._ta()
                        arg.append(self.uttryck())
                if self._kika()[1] != ")":
                    raise _Olost("obalanserad parentes i %s()" % txt)
                self._ta()
                return _uttrycksfunktion(txt, arg)
            return self.slauppe(txt)
        raise _Olost("ovantat %r i uttrycket" % (txt,))


def _rakna(text: str, slauppe) -> float:
    return _Uttryck(_tecken(text), slauppe).uttryck()


def _symboluppslag(trad: Block):
    """namn -> tal. Rotens variabelrymd forst, sedan funktionsblockens.

    `Kinematics::L01Z` ar funktionsblockets NAMN och en av dess rader; samma
    namn kan ocksa sta prefixat i rotens variabelrymd (sa gor de robotar som
    definierar kinematiken i ett Python-skript). Bada stallena lases, och den
    som inte finns i nagotdera ar OLOST - inte noll.
    """
    rot = rotvariabler(trad)
    block: Dict[str, str] = {}
    for fb in trad.alla("Functionality"):
        namn = fb.strang("Name") or ""
        for k, v in fb.rader:
            block.setdefault("%s::%s" % (namn, k), v)
            block.setdefault(k, v)
        for rymd in fb.sok("VariableSpace"):
            for k, var in _variabler(rymd).items():
                block.setdefault("%s::%s" % (namn, k), var.varde)
                block.setdefault(k, var.varde)

    def slauppe(namn: str) -> float:
        bas, _, del_ = namn.partition(".")
        for kalla in (rot, block):
            if bas not in kalla:
                continue
            ra = kalla[bas]
            text = str(ra.varde if isinstance(ra, Variabel) else ra)
            text = text.strip().strip('"')
            if del_:
                # rVector-variabler: "200 0 142 1" med .X/.Y/.Z pa slutet.
                d = text.split()
                i = "XYZW".index(del_)
                if len(d) <= i:
                    raise _Olost("%s saknar komponent %s" % (bas, del_))
                text = d[i]
            try:
                return float(text)
            except ValueError:
                raise _Olost("%s = %r ar inget tal" % (namn, text))
        raise _Olost("olost symbol %s" % namn)
    return slauppe


# --- 4x4 -------------------------------------------------------------------

def _enhetsmatris() -> List[List[float]]:
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def _matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
            for i in range(4)]


def _flytta(x, y, z):
    m = _enhetsmatris()
    m[0][3], m[1][3], m[2][3] = x, y, z
    return m


def _vrid(axel: str, grader: float):
    c, s = math.cos(math.radians(grader)), math.sin(math.radians(grader))
    m = _enhetsmatris()
    if axel == "x":
        m[1][1], m[1][2], m[2][1], m[2][2] = c, -s, s, c
    elif axel == "y":
        m[0][0], m[0][2], m[2][0], m[2][2] = c, s, -s, c
    else:
        m[0][0], m[0][1], m[1][0], m[1][1] = c, -s, s, c
    return m


def _offsetmatris(uttryck: str, slauppe) -> List[List[float]]:
    """Ett Offset-uttryck som 4x4. Okand operator -> _Olost."""
    m = _enhetsmatris()
    i, n = 0, len(uttryck)
    while i < n:
        while i < n and uttryck[i] in " .*":
            i += 1
        if i >= n:
            break
        huvud = _OFFSETLED.match(uttryck, i)
        if not huvud:
            raise _Olost("oparsbart led %r" % (uttryck[i:i + 24],))
        namn = huvud.group(1)
        j, djup = huvud.end(), 1
        while j < n and djup:
            if uttryck[j] == "(":
                djup += 1
            elif uttryck[j] == ")":
                djup -= 1
            j += 1
        if djup:
            raise _Olost("obalanserad parentes")
        inne, i = uttryck[huvud.end():j - 1], j
        if namn == "Identity":
            steg = _enhetsmatris()
        elif namn in ("Tx", "Ty", "Tz"):
            v = _rakna(inne, slauppe)
            steg = _flytta(*[(v if namn[1] == a else 0.0) for a in "xyz"])
        elif namn in ("Rx", "Ry", "Rz"):
            steg = _vrid(namn[1], _rakna(inne, slauppe))
        elif namn in ("Sx", "Sy", "Sz"):
            steg = _enhetsmatris()
            steg["xyz".index(namn[1])]["xyz".index(namn[1])] = _rakna(inne, slauppe)
        elif namn == "Set":
            d = [_rakna(x, slauppe) for x in inne.split(",")]
            if len(d) != 16:
                raise _Olost("Set() med %d tal i stallet for 16" % len(d))
            steg = [[d[j * 4 + r] for j in range(4)] for r in range(4)]
        else:
            raise _Olost("okand transformoperator %s" % namn)
        m = _matmul(m, steg)
    return m


# --- kedjan ----------------------------------------------------------------

# Ledens rotationsaxel i sin egen ram. VC skriver 0/1/2 for X/Y/Z; andra varden
# (5 och 6 forekommer) betyder nagot den har koden inte last, och da ar axeln
# OKAND i stallet for gissad.
_AXELINDEX = {0: (1.0, 0.0, 0.0), 1: (0.0, 1.0, 0.0), 2: (0.0, 0.0, 1.0)}

_FOLJARLED = ("RotationalFollower", "TranslationalFollower")

# VC:s varldsuppaxel ar Z (M-33), och komponentens rot star i varldens ram.
# Anvands bara nar led 1:s Dof-block inte deklarerar nagon AxisType alls -
# 237 robotar i biblioteket bar `Dof "Custom"` utan axel (M-179).
_UPPAXEL = (0.0, 0.0, 1.0)

# Tva ledaxlar raknas som parallella over den har granen. MATT i M-179: av
# 4254 axelpar i biblioteket ligger 4245 antingen over 1-1e-9 eller under 1e-9
# i |cos| - fordelningen ar tvatoppig med ett tomrum daremellan, sa varje
# trosket mellan 1e-9 och 1e-3 ger samma svar for 4245 av 4254 paren.
_PARALLELLGRANS = 1e-6          # Satt av M-179.


def _norm(v) -> float:
    return math.sqrt(sum(x * x for x in v))


def _vinkelrat_del(v, axel) -> float:
    """Den del av v som ligger vinkelratt mot axel."""
    n = _norm(axel)
    if n < 1e-12:
        return _norm(v)
    langs = sum(v[i] * axel[i] for i in range(3)) / n
    return math.sqrt(max(0.0, sum(x * x for x in v) - langs * langs))


def _ar_parallella(a, b) -> bool:
    na, nb = _norm(a), _norm(b)
    if na < 1e-12 or nb < 1e-12:
        return False
    return abs(sum(a[i] * b[i] for i in range(3))) / (na * nb) > 1 - _PARALLELLGRANS


def _nodvag(trad: Block, flansnamn: str) -> Optional[List[Block]]:
    """Vagen fran rotnoden ned till flansnoden, som en lista av noder."""
    rot = _rot_nod(trad)
    if rot is None:
        return None

    def gren(nod, sa_langt):
        for b in nod.sok("Node"):
            vag = sa_langt + [b]
            if (b.strang("Name") or "") == flansnamn:
                return vag
            djupare = gren(b, vag)
            if djupare:
                return djupare
        return None
    return gren(rot, [])


def _nodens_dof(nod: Block) -> Optional[Block]:
    for b in nod.barn:
        if b.namn == "Dof":
            return b
    return None


def _kedjans_leder(trad: Block, ctl: Optional[Block]):
    """(punkter, axlar, ledtyper, skal).

    `punkter[i]` ar led i+1:s origo i komponentens ram, `axlar[i]` dess
    rotationsaxel dar filen deklarerar en och None annars. Gar nagon del av
    kedjan inte att folja ar `skal` satt och de tre andra None - en delsumma
    far aldrig lamna den har funktionen.
    """
    if ctl is None:
        return None, None, None, "ingen robotstyrning att lasa kedjan ur"
    flans = ctl.strang("FlangeNode")
    if not flans:
        return None, None, None, "robotstyrningen namnger ingen FlangeNode"
    vag = _nodvag(trad, flans)
    if not vag:
        return None, None, None, ("ingen nodvag fran rotnoden till flansnoden "
                                  "%r" % flans)
    lednamn = _ledordning(ctl)
    slauppe = _symboluppslag(trad)
    m = _enhetsmatris()
    punkter, axlar, typer = [], [], []
    for nod in vag:
        uttryck = None
        for off in nod.sok("Offset"):
            uttryck = off.strang("Expression") or ""
            break
        if uttryck is None:
            rad = nod.rad("Offset")           # matrisform: 16 tal pa raden
            if rad is not None:
                uttryck = "Set(%s)" % ",".join(rad.split())
        if uttryck is None:
            return None, None, None, ("noden %r i kedjan bar ingen transform"
                                      % (nod.strang("Name"),))
        try:
            m = _matmul(m, _offsetmatris(uttryck, slauppe))
        except _Olost as fel:
            return None, None, None, ("nodtransformen for %r gar inte att losa: "
                                      "%s" % (nod.strang("Name"), fel))
        dof = _nodens_dof(nod)
        if dof is None:
            continue
        if dof.arg in _FOLJARLED:
            return None, None, None, (
                "kedjan gar genom foljarleden %r - en parallell mekanism har "
                "ingen serie att summera" % (dof.strang("Name")
                                             or nod.strang("Name"),))
        if (dof.strang("Name") or "") not in lednamn:
            continue
        axel = None
        rad = dof.rad("AxisType")
        if rad is not None:
            try:
                axel = _AXELINDEX.get(int(float(rad)))
            except ValueError:
                axel = None
        if axel is not None:
            axel = tuple(sum(m[i][k] * axel[k] for k in range(3))
                         for i in range(3))
        punkter.append((m[0][3], m[1][3], m[2][3]))
        axlar.append(axel)
        typer.append(dof.arg)
    return punkter, axlar, typer, None


def _rackvidd_ur_transformer(trad: Block) -> Varde:
    """Rackvidden summerad ur kedjans nodtransformer. HARLEDD eller SAKNAS.

    STORHETEN ar avstandet fran led 1:s axel ut till handledscentrum, och den
    ar inte samma sak som summan av alla translationer:

      * Den del av forsta lanken som ligger LANGS led 1:s axel (pelarens hojd)
        vrider sig inte ut fran axeln och hor inte till rackvidden. Samma sak
        galler vidare sa lange lederna dittills ar parallella med led 1 - det
        ar precis fallet SCARA, dar bade L01Z och L23:s Z-del ska bort.
      * SISTA lanken raknas bara till den del som ligger vinkelratt mot sista
        ledens axel. Handledscentrum ar den punkt sista leden inte flyttar;
        resten ar flansforskjutning. Star sista ledens axel inte i filen faller
        hela sista lanken bort, vilket ar M-59:s matta val - att ta med den ger
        median 1,086 mot tillverkarens tal i stallet for 1,001.

    MATT i M-179 over hela biblioteket: mot de 405 robotar som bar tillverkarens
    rackvidd i sitt modellnamn ger den har vagen median 1,0006 och 399 av 405
    inom fem procent. Ledgranserna ar fortfarande inte inraknade, sa talet ar en
    OVRE GRANS - precis som variabelvagens.
    """
    ctl = _styrenhet(trad)
    punkter, axlar, typer, skal = _kedjans_leder(trad, ctl)
    if skal:
        return saknas("rackvidd", "%s: %s" % (VAG_TRANSFORMER, skal))
    n = len(punkter)
    if n < 3:
        return saknas("rackvidd", "%s: bara %d styrd led i kedjan - for kort "
                                  "for att bara en rackvidd"
                                  % (VAG_TRANSFORMER, n))
    if typer[0] == "Translational":
        return saknas("rackvidd", "%s: kedjans forsta led ar skjutande, sa "
                                  "rackvidden ar dess slaglangd - en ledgrans, "
                                  "och ledgranser raknas inte in"
                                  % VAG_TRANSFORMER)
    axel1 = axlar[0] if axlar[0] is not None else _UPPAXEL
    summa = 0.0
    for i in range(1, n):
        lank = tuple(punkter[i][k] - punkter[i - 1][k] for k in range(3))
        if i == n - 1:
            summa += 0.0 if axlar[-1] is None else _vinkelrat_del(lank, axlar[-1])
            continue
        parallella = all(axlar[j] is not None and _ar_parallella(axlar[j], axel1)
                         for j in range(1, i))
        summa += _vinkelrat_del(lank, axel1) if parallella else _norm(lank)
    if summa <= 0.0:
        return saknas("rackvidd", "%s: kedjans translationer summerar till %g - "
                                  "det ar ingen rackvidd"
                                  % (VAG_TRANSFORMER, summa))
    return harledd(
        "rackvidd", round(summa, 1),
        "OVRE GRANS: %s - translationerna langs %d leder fran %r till %r, "
        "handledscentrum och inte flansen, ledgranser ej inraknade; provad mot "
        "405 modellnamn, median 1,0006 (M-179)"
        % (VAG_TRANSFORMER, n, ctl.strang("RootNode") or "?",
           ctl.strang("FlangeNode") or "?"), "mm")


def harledningsvag(varde: Varde) -> str:
    """Vilken av de tva harledningarna talet kom ur. Faller om kallan tiger.

    Bada vagarna ar HARLEDD och bada ger millimeter, sa `harkomst` skiljer dem
    inte. Skillnaden ska ga att lasa mekaniskt ur `kalla` av samma skal som
    `harkomst` ar ett falt och inte prosa: en transformharledd rackvidd som ser
    ut som en variabelharledd ar en tyst uppgradering.
    """
    if varde.harkomst != HARLEDD:
        raise Databladsfel(
            "%s: harledningsvagen fragas bara om ett HARLEDD varde, inte om %s"
            % (varde.storhet, varde.harkomst))
    tratt = [v for v in (VAG_VARIABLER, VAG_TRANSFORMER) if v in varde.kalla]
    if len(tratt) != 1:
        raise Databladsfel(
            "%s: kallan sager inte vilken harledning talet kom ur (%r)"
            % (varde.storhet, varde.kalla))
    return tratt[0]


def rackviddens_vagar(blad: Sequence["Datablad"]) -> Dict[str, int]:
    """Hur manga rackvidder som kom ur vilken vag. Faller pa en omarkt kalla."""
    ut = {VAG_VARIABLER: 0, VAG_TRANSFORMER: 0}
    for b in blad:
        if not b.har("rackvidd"):
            continue
        v = b["rackvidd"]
        if v.harkomst == HARLEDD:
            ut[harledningsvag(v)] += 1
    return ut


# ---------------------------------------------------------------------------
# Databladet
# ---------------------------------------------------------------------------

@dataclass
class Datablad:
    namn: str
    tillverkare: str
    familj: str
    sokvag: str
    modell_id: str = ""
    kategori: str = ""
    storheter: Dict[str, Varde] = field(default_factory=dict)

    def __getitem__(self, storhet: str) -> Varde:
        """Storheten, eller ett tydligt fel om den inte hor till familjen.

        Att fraga en robot om dess bandhastighet ar inte ett hal i datan - det
        ar en fraga som inte har ett varde. De tva svaren far inte se likadana
        ut, sa det ena ar ett undantag och det andra ett falt.
        """
        if storhet in self.storheter:
            return self.storheter[storhet]
        if storhet not in STORHETER:
            raise Databladsfel(
                "%r ar ingen storhet i ordforradet. Ordforradet ar: %s"
                % (storhet, ", ".join(sorted(STORHETER))))
        raise Databladsfel(
            "storheten %r hor inte till familjen %r. Familjens storheter: %s"
            % (storhet, self.familj,
               ", ".join(FAMILJENS_STORHETER.get(self.familj, ()))))

    def har(self, storhet: str) -> bool:
        return storhet in self.storheter and self.storheter[storhet].finns

    # -- de tva formerna -------------------------------------------------
    def identitet(self) -> Dict[str, str]:
        d = {"namn": self.namn, "tillverkare": self.tillverkare,
             "familj": self.familj}
        if self.modell_id:
            d["modell"] = self.modell_id
        return d

    def kort(self) -> Dict[str, object]:
        """Identitet plus de storheter som avgor VALET. Standardformen.

        En agent som vager tio robotar mot varandra ska inte behova betala for
        ledgranser per axel den inte fragat efter. Vad formerna kostar i tecken
        star i M-59.
        """
        d = self.identitet()
        for s in KORTA_STORHETER.get(self.familj, ()):
            v = self.storheter.get(s)
            if v is not None:
                d[s] = v.till_json(kort=True)
        return d

    def fullt(self) -> Dict[str, object]:
        d = self.identitet()
        d["kategori"] = self.kategori
        d["sokvag"] = self.sokvag
        for s in FAMILJENS_STORHETER.get(self.familj, ()):
            v = self.storheter.get(s)
            if v is not None:
                d[s] = v.till_json()
        return d

    def kort_text(self) -> str:
        rader = ["%s (%s, %s)" % (self.namn, self.tillverkare, self.familj)]
        for s in KORTA_STORHETER.get(self.familj, ()):
            v = self.storheter.get(s)
            if v is not None:
                rader.append("  " + v.text(kort=True))
        return "\n".join(rader)

    def full_text(self) -> str:
        rader = ["%s (%s, %s)" % (self.namn, self.tillverkare, self.familj)]
        if self.modell_id:
            rader.append("  modell: %s" % self.modell_id)
        for s in FAMILJENS_STORHETER.get(self.familj, ()):
            v = self.storheter.get(s)
            if v is not None:
                rader.append("  " + v.text())
        return "\n".join(rader)


def _familj(funktioner_: Sequence[str]) -> str:
    for namn, markorer in FAMILJEMARKORER:
        if any(m in funktioner_ for m in markorer):
            return namn
    return "ovrig"


def _massa(varde) -> Optional[float]:
    """Ett massatal i filens enhet -> kilo, eller None om det inte ar en massa.

    Noll ar inte en massa har: VC skriver 0 i varje verktygsram som ingen satt
    en last pa, och -1000 nar faltet ar uttryckligen tomt. Bada skulle bli
    "0 kg" och "−1 kg" i ett datablad som laser raden rakt av.
    """
    t = _tal(varde)
    if t is None or t <= 0 or t == _INGEN_MASSA:
        return None
    return t / float(GRAM_PER_KILO)


def _nyttolast(rotvar: Dict[str, Variabel]) -> Varde:
    namn, t, v = _rot_var_tal(rotvar, NYTTOLAST_FALT)
    if namn is None:
        return saknas("nyttolast",
                      "ingen av rotvariablerna %s (M-59)"
                      % ", ".join(NYTTOLAST_FALT))
    kg = _massa(v.varde)
    if kg is None:
        return saknas("nyttolast",
                      "rotvariabeln %s finns men bar %r, vilket inte ar en "
                      "massa" % (namn, v.varde))
    return last("nyttolast", kg,
                "rotvariabeln %s (Quantity %s); filens massenhet ar gram, "
                "omraknad till kilo (M-59)" % (namn, v.quantity or "saknas"),
                "kg")


def _verktygslast(trad: Block) -> Varde:
    """Massan som star pa komponentens verktygsramar.

    Det ar INTE robotens egen vikt och inte heller dess maxlast - det ar den
    last nagon har lagt in pa en tool-ram. M-55 sa att VC:s Python-API bar noll
    massa och noll troghet. Filformatet BAR falten - men matt over 3201 filer
    ar de tomma eller sentinel i de allra flesta, sa fyndet galler at bada
    hallen.
    """
    kandidater = []
    for tb in trad.alla("Tools"):
        for bf in tb.sok("BaseFrame"):
            kg = _massa(bf.rad("Mass"))
            if kg is not None:
                kandidater.append((bf.strang("Frame") or "?", kg))
    if not kandidater:
        return saknas("verktygslast",
                      "ingen Tools/BaseFrame med Mass > 0 (0 och -1000 raknas "
                      "inte som massa)")
    return last("verktygslast", max(k for _n, k in kandidater),
                "storsta Mass i Tools/BaseFrame (%s), omraknad till kilo"
                % ", ".join("%s=%g" % (n, k) for n, k in kandidater[:4]), "kg")


def _egenvikt(trad: Block, rotvar: Dict[str, Variabel]) -> Varde:
    """Komponentens EGEN massa.

    Den finns inte. MATT i M-59 over 3201 filer: noll komponenter bar sin egen
    vikt. Tre falt ser ut som svaret och ar det inte - de star i
    FORKASTADE_FALT och namns i skalet, sa nasta lasare slipper hitta dem igen.
    """
    return saknas("egenvikt",
                  "finns inte i metadatan; 0 av 3201 (M-59). Falten som ser ut "
                  "som svaret star i FORKASTADE_FALT")


def _ledstorheter(trad: Block, ctl: Optional[Block]) -> Dict[str, Varde]:
    """Frihetsgrader, ledtyper, ledgranser, maxhastighet, maxacceleration."""
    ut: Dict[str, Varde] = {}
    dofar = _dofar(trad)
    ordning = _ledordning(ctl)

    if ordning:
        ut["frihetsgrader"] = last(
            "frihetsgrader", len(ordning),
            "rSimRobotController/JointMap: de STYRDA lederna. Filen har %d "
            "Dof-block totalt, dar fasta leder och foljare ingar." % len(dofar))
    else:
        rorliga = [n for n, d in dofar.items() if d.arg != "Fixed"]
        if not rorliga:
            ut["frihetsgrader"] = saknas(
                "frihetsgrader",
                "varken JointMap eller ett enda Dof-block som inte ar Fixed")
            ut["ledtyper"] = saknas("ledtyper", "inga rorliga Dof-block")
            ut["ledgranser"] = saknas("ledgranser", "inga rorliga Dof-block")
            ut["maxhastighet"] = saknas("maxhastighet", "inga rorliga Dof-block")
            ut["maxacceleration"] = saknas("maxacceleration",
                                           "inga rorliga Dof-block")
            return ut
        ordning = rorliga
        ut["frihetsgrader"] = harledd(
            "frihetsgrader", len(rorliga),
            "antal Dof-block som inte ar Fixed; komponenten har ingen "
            "robotstyrning som listar sina leder")

    typer, granser, fart, acc = [], [], [], []
    saknade = []
    for namn in ordning:
        d = dofar.get(namn)
        if d is None:
            saknade.append(namn)
            typer.append("okand")
            continue
        typ = _LEDTYP.get(d.arg, d.arg)
        typer.append(typ)
        enhet = _LEDENHET.get(typ, "")
        post: Dict[str, object] = {"led": namn, "enhet": enhet}
        for grans, nyckel in (("MinLimit", "min"), ("MaxLimit", "max")):
            block = d.sok(grans)
            uttryck = block[0].strang("Expression") if block else None
            t = _tal(uttryck)
            if t is not None:
                post[nyckel] = t
            elif uttryck:
                post[nyckel + "_uttryck"] = uttryck
        granser.append(post)
        props = d.sok("Properties")
        pv = _variabler(props[0]) if props else {}
        for kalla_namn, lista in (("MaxSpeed", fart),
                                  ("MaxAcceleration", acc)):
            v = pv.get(kalla_namn)
            t = _tal(v.varde) if v is not None else None
            lista.append({"led": namn, "varde": t,
                          "enhet": (v.enhet if v is not None else "")}
                         if t is not None else {"led": namn, "varde": None})

    ut["ledtyper"] = last("ledtyper", typer,
                          "Dof-blockens typ i styrenhetens ledordning"
                          + (" (%d led saknar Dof-block)" % len(saknade)
                             if saknade else ""))
    if any("min" in g or "max" in g or "min_uttryck" in g or "max_uttryck" in g
           for g in granser):
        ut["ledgranser"] = last(
            "ledgranser", granser,
            "Dof/MinLimit och Dof/MaxLimit. En grans som beror av en annan led "
            "star kvar som uttryck i stallet for att raknas om till ett tal.")
    else:
        ut["ledgranser"] = saknas("ledgranser",
                                  "Dof-blocken bar varken MinLimit eller MaxLimit")
    for namn, lista, kalla_namn in (("maxhastighet", fart, "MaxSpeed"),
                                    ("maxacceleration", acc, "MaxAcceleration")):
        if any(p.get("varde") is not None for p in lista):
            ut[namn] = last(namn, lista,
                            "Dof/Properties/%s; enheten star som Quantity i "
                            "filen" % kalla_namn)
        else:
            ut[namn] = saknas(namn, "inget %s i nagot Dof-block" % kalla_namn)
    return ut


def _granssnittsstorheter(trad: Block) -> Dict[str, Varde]:
    ifs = _granssnittsblock(trad)
    ut: Dict[str, Varde] = {}
    if not ifs:
        ut["granssnitt"] = saknas("granssnitt",
                                  "inga Functionality rSimInterface i filen")
        ut["monteringsgranssnitt"] = saknas(
            "monteringsgranssnitt", "inga granssnitt alls i filen")
        return ut
    namn = [b.strang("Name") or "?" for b in ifs]
    ut["granssnitt"] = last("granssnitt", namn,
                            "namnen pa Functionality rSimInterface")
    mont = []
    for b in ifs:
        for sek in b.sok("Section"):
            for falt in sek.sok("Fields"):
                for h in falt.sok("rSimHierarchyField"):
                    roll = "vard" if (_tal(h.rad("Mount")) or 0) != 0 else "gast"
                    mont.append("%s:%s" % (b.strang("Name") or "?", roll))
                    break
    if mont:
        ut["monteringsgranssnitt"] = last(
            "monteringsgranssnitt", sorted(set(mont)),
            "granssnitt med ett rSimHierarchyField. vard = tar emot en annan "
            "komponent, gast = monteras sjalv i en annan.")
    else:
        ut["monteringsgranssnitt"] = saknas(
            "monteringsgranssnitt",
            "inget granssnitt bar ett rSimHierarchyField; de %d som finns "
            "flodar produkter i stallet" % len(ifs))
    return ut


def _matt(rotvar: Dict[str, Variabel], storhet: str,
          falt: Sequence[str], enhet: str, enhetskalla: str) -> Varde:
    namn, t, v = _rot_var_tal(rotvar, falt)
    if namn is None:
        finns = [f for f in falt if f in rotvar]
        if finns:
            return saknas(storhet,
                          "rotvariabeln %s finns men bar %r, inte ett tal"
                          % (finns[0], rotvar[finns[0]].varde))
        return saknas(storhet,
                      "ingen av rotvariablerna %s i komponentens egen "
                      "variabelrymd" % ", ".join(falt))
    e = v.enhet or enhet
    kalla = "rotvariabeln %s" % namn
    if v.enhet:
        kalla += ' (Quantity "%s")' % v.quantity
    else:
        kalla += "; ingen Quantity i filen, enheten ar %s" % enhetskalla
    return last(storhet, t, kalla, e)


def fran_text(text: str, sokvag: str = "", tillverkare: str = "") -> Datablad:
    """Databladet ur en component.rsc-text. Ingen fil, ingen VC."""
    trad = las_trad(text)
    rot = _rot_nod(trad)
    rotvar = rotvariabler(trad)
    funk = funktionsnamn(trad)
    familj = _familj(funk)
    namn = (rot.strang("Name") if rot is not None else None) or (
        os.path.splitext(os.path.basename(sokvag))[0] if sokvag else "")
    modell = ""
    if "RobotModelID" in rotvar:
        modell = rotvar["RobotModelID"].varde.strip('"')
    blad = Datablad(namn=namn, tillverkare=tillverkare, familj=familj,
                    sokvag=sokvag, modell_id=modell,
                    kategori=(rot.strang("Category") or "")
                    if rot is not None else "")

    ctl = _styrenhet(trad)
    kin = _kinematik(trad)
    s: Dict[str, Varde] = {}
    s.update(_granssnittsstorheter(trad))
    s["egenvikt"] = _egenvikt(trad, rotvar)
    s["nyttolast"] = _nyttolast(rotvar)

    if familj in ("robot", "verktyg"):
        s.update(_ledstorheter(trad, ctl))
    if familj == "robot":
        s["verktygslast"] = _verktygslast(trad)
        s["rackvidd"] = _rackvidd(trad, kin, rotvar)
        for storhet, nyckel, vad in (("monteringsram", "FlangeNode",
                                      "ramen ett verktyg skruvas fast i"),
                                     ("basram", "RootNode",
                                      "komponentens rotnod")):
            v = ctl.strang(nyckel) if ctl is not None else None
            s[storhet] = (last(storhet, v,
                               "rSimRobotController/%s: %s" % (nyckel, vad))
                          if v else
                          saknas(storhet,
                                 "ingen robotstyrning med %s" % nyckel))
        s["styrenhet"] = (last("styrenhet", ctl.strang("Name") or "?",
                               "namnet pa Functionality %s" % ctl.arg)
                          if ctl is not None else
                          saknas("styrenhet", "ingen robotstyrning i filen"))
        s["kinematik"] = (last("kinematik", kin.arg,
                               "typen pa kinematikblocket")
                          if kin is not None else
                          saknas("kinematik", "inget kinematikblock i filen"))
    if familj in ("transportor", "ovrig"):
        s["langd"] = _matt(rotvar, "langd", LANGD_FALT, "mm",
                           "VC:s varldsenhet millimeter (M-33)")
        s["bredd"] = _matt(rotvar, "bredd", BREDD_FALT, "mm",
                           "VC:s varldsenhet millimeter (M-33)")
        s["hojd"] = _matt(rotvar, "hojd", HOJD_FALT, "mm",
                          "VC:s varldsenhet millimeter (M-33)")
    if familj == "transportor":
        s["hastighet"] = _matt(rotvar, "hastighet", HASTIGHET_FALT, "mm/s",
                               "VC:s varldsenhet millimeter per sekund (M-33)")
        s["kapacitet"] = _matt(rotvar, "kapacitet", KAPACITET_FALT, "st",
                               "ett antal, inte en fysisk storhet")

    # Bara familjens egna storheter far folja med. En robot som bar ett falt
    # som heter "hastighet" vore ett svar pa en fraga ingen stallt.
    for namn_ in FAMILJENS_STORHETER.get(familj, ()):
        if namn_ in s:
            blad.storheter[namn_] = s[namn_]
    return blad


def las(sokvag: str, tillverkare: str = "") -> Datablad:
    """Databladet ur en .vcmx pa disk."""
    try:
        with zipfile.ZipFile(sokvag) as z:
            if katalogindex.METADATA not in z.namelist():
                raise Databladsfel("%s is missing %s"
                                   % (sokvag, katalogindex.METADATA))
            text = z.read(katalogindex.METADATA).decode("utf-8", "replace")
    except (zipfile.BadZipFile, OSError) as fel:
        raise Databladsfel("%s cannot be read: %s" % (sokvag, fel))
    return fran_text(text, sokvag, tillverkare)


def _tillverkare_ur_sokvag(sokvag: str, rot: str) -> str:
    rel = os.path.relpath(sokvag, rot)
    delar = [d for d in rel.split(os.sep) if d not in (".", "")]
    return delar[0] if len(delar) > 1 else ""


def bygg(rot: str, skriv=None):
    """Datablad for hela biblioteket. Ger (blad, olasliga)."""
    if not os.path.isdir(rot):
        raise Databladsfel("no library root at %s" % rot)
    blad: List[Datablad] = []
    olasliga: List[str] = []
    for katalog, _k, filer in os.walk(rot):
        for f in sorted(filer):
            if not f.lower().endswith((".vcmx", ".vcm")):
                continue
            hel = os.path.join(katalog, f)
            try:
                blad.append(las(hel, _tillverkare_ur_sokvag(hel, rot)))
            except Databladsfel as fel:
                olasliga.append("%s: %s" % (hel, fel))
        if skriv and len(blad) % 500 == 0 and blad:
            skriv("  %d datablad ..." % len(blad))
    return blad, olasliga


def tackning(blad: Sequence[Datablad]) -> Dict[str, Dict[str, int]]:
    """Hur manga komponenter varje storhet kunde fyllas i, LAST mot HARLEDD.

    Det ar hela poangen med matningen: en avbildning som inte redovisar hur
    manga den traffade ar ett pastaende, inte ett matt. Namnaren foljer med i
    varje rad - "tillamplig" ar antalet komponenter dar storheten alls hor till
    familjen, och det ar den namnare procenten ska raknas mot.
    """
    ut: Dict[str, Dict[str, int]] = {}
    for s in STORHETER:
        ut[s] = {"tillamplig": 0, "last": 0, "harledd": 0, "saknas": 0}
    for b in blad:
        for s, v in b.storheter.items():
            rad = ut[s]
            rad["tillamplig"] += 1
            rad[v.harkomst] += 1
    return ut


def tackningstabell(blad: Sequence[Datablad]) -> str:
    """Tackningen som en tabell med NAMNAREN utskriven pa varje rad.

    Aldrig bara procent. Ett tal utan namnare gar inte att prova mot nasta
    korning, och det ar hela poangen med raden.
    """
    t = tackning(blad)
    rader = ["%-22s %10s %8s %9s %9s" % ("storhet", "tillamplig", "last",
                                         "harledd", "saknas")]
    for s in STORHETER:
        r = t[s]
        rader.append("%-22s %10d %8d %9d %9d"
                     % (s, r["tillamplig"], r["last"], r["harledd"],
                        r["saknas"]))
    return "\n".join(rader)


def _teckenstat(blad: Sequence[Datablad]) -> str:
    import json as _json

    def stat(x):
        x = sorted(x)
        n = len(x)
        return x[0], x[n // 2], x[int(n * 0.95)], x[-1]

    rader = ["%-12s %7s %8s %6s %6s" % ("form", "min", "median", "p95", "max")]
    for namn, matt in (
            ("kort text", [len(b.kort_text()) for b in blad]),
            ("kort JSON", [len(_json.dumps(b.kort(), ensure_ascii=False))
                           for b in blad]),
            ("full text", [len(b.full_text()) for b in blad]),
            ("full JSON", [len(_json.dumps(b.fullt(), ensure_ascii=False))
                           for b in blad])):
        rader.append("%-12s %7d %8d %6d %6d" % ((namn,) + stat(matt)))
    return "\n".join(rader)


def main(argv=None):
    """Bygger tackningstabellen i M-59 ur den kod som levereras.

    Matningen ska ga att kora om. En tabell som bara finns i ett skript nagon
    kastade ar ett pastaende, inte ett matt.
    """
    import argparse
    p = argparse.ArgumentParser(description="datablad ur komponentbiblioteket")
    p.add_argument("--rot", help="biblioteksrot; annars soks den upp")
    p.add_argument("--visa", help="skriv ut databladet for komponenter vars "
                                  "namn innehaller den har texten")
    p.add_argument("--fullt", action="store_true",
                   help="full form i stallet for kort")
    a = p.parse_args(argv)

    rot = a.rot
    if not rot:
        fynd = katalogindex.hitta()
        if not fynd:
            print("found no library. Tried:")
            for sokvag, hur in katalogindex.kandidatrotter():
                print("  %-60s %s" % (sokvag, hur))
            return 1
        rot = fynd[0].rot
        print("library: %s\n  found via: %s" % (fynd[0].rot, fynd[0].hur))
    blad, olasliga = bygg(rot)
    print("%d datasheets, %d unreadable" % (len(blad), len(olasliga)))
    if a.visa:
        for b in blad:
            if a.visa.lower() in b.namn.lower():
                print()
                print(b.full_text() if a.fullt else b.kort_text())
        return 0
    familjer: Dict[str, int] = {}
    for b in blad:
        familjer[b.familj] = familjer.get(b.familj, 0) + 1
    print("families: " + ", ".join("%s %d" % (k, v)
                                   for k, v in sorted(familjer.items())))
    print()
    print(tackningstabell(blad))
    print()
    print(_teckenstat(blad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
