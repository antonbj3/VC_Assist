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
`nyttolast` (payload) finns INTE i nagon av de 3201 filerna - matt i M-59. Den
frestelsen ar precis den har modulens huvudrisk: ett datablad dar payload alltid
star ifyllt ser komplett ut och ljuger snyggt. `SAKNAS` ar ett forstklassigt
svar och skrivs ut, aldrig som noll och aldrig som tystnad.

SCHEMAT AR INTE ENHETLIGT
-------------------------
2665 unika parameternamn over biblioteket. Det finns inget gemensamt Payload-
eller Reach-falt. Avbildningen fran STORHET till PARAMETERNAMN ar darfor matt
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

import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import katalogindex

FORMAT = 1                      # Satt av M-59.

LAST = "last"
HARLEDD = "harledd"
SAKNAS = "saknas"

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
            raise Databladsfel("okand harkomst %r" % (self.harkomst,))
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


def _rackvidd(kin: Optional[Block], rotvar: Dict[str, Variabel]) -> Varde:
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
    """
    if kin is None:
        return saknas("rackvidd", "inget kinematikblock i filen")
    typ = kin.arg

    def t(n):
        return _kin_tal(kin, rotvar, n)

    if typ == "rKinArticulated2":
        if t("L12X") is None or t("L23Z") is None:
            return saknas("rackvidd",
                          "rKinArticulated2 utan lanklangderna L12X/L23Z")
        delar = [t("L12X"), _hyp(t("L23X"), t("L23Z")),
                 _hyp(t("L34X"), t("L34Z")), _hyp(t("L45X"), t("L45Z"))]
        formel = ("L12X+|L23|+|L34|+|L45| ur rKinArticulated2 (flanslanken L56 "
                  "ar inte med, tillverkaren matter till handledscentrum); "
                  "provad mot 386 modellnamn, median 1,001 (M-59)")
    elif typ == "rKinScara2":
        a, b = t("L12X"), t("L23X")
        if a is None or b is None:
            return saknas("rackvidd", "rKinScara2 utan L12X/L23X")
        delar = [a, b]
        formel = "OVRE GRANS: L12X+L23X ur rKinScara2, ledgranser ej inraknade"
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
                "%s utan lanklangder i blocket eller i rotens variabler" % typ)
        delar = [j12x, _hyp(j23x, j23z), _hyp(j34x, j34z), j46x or 0.0]
        formel = ("OVRE GRANS: JointOffset1 + |LinkLength2,JointOffset4| + "
                  "|LinkLength3,JointOffset3| + LinkLength4 ur %s" % typ)
    return harledd("rackvidd", round(sum(d or 0.0 for d in delar), 1), formel,
                   "mm")


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
        s["rackvidd"] = _rackvidd(kin, rotvar)
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
                raise Databladsfel("%s saknar %s"
                                   % (sokvag, katalogindex.METADATA))
            text = z.read(katalogindex.METADATA).decode("utf-8", "replace")
    except (zipfile.BadZipFile, OSError) as fel:
        raise Databladsfel("%s gar inte att lasa: %s" % (sokvag, fel))
    return fran_text(text, sokvag, tillverkare)


def _tillverkare_ur_sokvag(sokvag: str, rot: str) -> str:
    rel = os.path.relpath(sokvag, rot)
    delar = [d for d in rel.split(os.sep) if d not in (".", "")]
    return delar[0] if len(delar) > 1 else ""


def bygg(rot: str, skriv=None):
    """Datablad for hela biblioteket. Ger (blad, olasliga)."""
    if not os.path.isdir(rot):
        raise Databladsfel("ingen biblioteksrot pa %s" % rot)
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
