# -*- coding: utf-8 -*-
"""TURORDNINGEN: grindarna som inte gar att doma pa ETT anrop.

Forgranskningen (forgranskning.py) domer varje anrop for sig: finns
verktyget, haller argumenten schemat, ror koden en sakerhetsfunktion. Den
kan inte se det som ligger MELLAN anropen, och fyra av korpusens matta
fallor ligger just dar:

  efter_sparning     ARB-006, FAL-004. MATT M-13: app.save() stoppar
                     simuleringen och bryggan svarar inte efterat. Allt som
                     skulle goras efter en sparning blir ogjort UTAN att
                     nagon far veta det. Anropet efter sparningen ar alltsa
                     inte ett anrop som misslyckas - det ar ett anrop som
                     forsvinner.
  slapande_matris    FAL-002, ARB-004. MATT M-11: efter en tilldelning stod
                     lokal matris pa 52,5 medan varldsmatrisen stod pa 10,5,
                     och den stod kvar dar genom render, flush och
                     omlasning. Bara update() hamtar hem den. Var egen
                     get_transform-mall laser n.WorldPositionMatrix UTAN
                     update(), medan matmallarna kor _farsk() (M-36). Ett
                     get_transform i varldsramen direkt efter en flytt ger
                     alltsa ett tal som SER RIMLIGT UT och beskriver laget
                     fore flytten.
  olast_scen         ARB-001. Modellen far bara valja ur det som finns (I9),
                     och det enda sattet att veta vad som finns ar att lasa.
                     Ett scenandrande anrop som namnger en komponent som
                     ingen lasning i turen har returnerat ar en gissning.
  olast_skrivning    ARB-003, FAL-005. MATT M-09: VC svaljer fel tyst. Ett
                     anrop som inte kastade ar inget bevis pa att atgarden
                     tog, sa en andring ska lasas tillbaka innan nasta gors.

VARFOR GRINDARNA LIGGER SIST I KEDJAN. 82_felklasser.md sorteringsregel 1
sager att forsta grinden som faller bestammer klassen. Turordningsgrindarna
behover den GENERERADE koden (slapande_matris laser den) och de fragar om ett
anrop som redan ar giltigt i sig: fragan "kommer det har anropet att ge ett
gammalt varde" ar meningslos innan man vet att verktyget finns och att
argumenten haller. Darfor domer de sist, och darfor bar en trasig
argumentlista fortfarande klassen argument.

TILLSTANDET LIGGER I TURLAGE, INTE I FORGRANSKAREN. Forgranskaren ar
tillstandslos med flit - samma grindar ska ge samma dom oavsett vilken tur
de kors i. Loopen ager ett Turlage per tur och skickar in det.

Fragan modulen staller om koden ar SNAVARE an skrivgrindens. Skrivgrinden
fragar om koden SKRIVER (och domer darfor update() som skrivning, se
verktyg/matning.py), medan vi fragar om den ANDRAR GEOMETRIN. En matmall som
bara uppdaterar noder for att fa farska matt andrar ingenting, och far inte
rakans som en andring som maste lasas tillbaka.
"""
from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .sakerhet import ROT
from .text import normalisera

_EXT = os.path.join(ROT, "ext", "vc_addon", "vc_assist")
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import skrivgrind  # noqa: E402

# Aterbruk och inte omimplementering. Skrivgrinden ager tre fragor som vi
# behover svaren pa och som ar mattade i dess egna prov: vad ar ett muterande
# namn, vilka namn ar behallare koden sjalv byggt (svar["a"] = ... ar
# bokforing, inte en scenandring) och vad heter det sista ledet i ett uttryck.
# Att skriva om dem har hade gett tva listor som driftar isar.
_ar_muterande_namn = skrivgrind._ar_muterande_namn
_lokala_behallare = skrivgrind._lokala_behallare
_rotnamn = skrivgrind._rotnamn
_sista_namnet = skrivgrind._sista_namnet

GRINDAR = ("efter_sparning", "slapande_matris", "olast_scen",
           "olast_skrivning")

# Attribut vars TILLDELNING flyttar nagot i scenen. MATT M-11: det ar just
# efter en sadan tilldelning varldsmatrisen slapar. Matrisens egen .P star
# INTE har: den satts pa en lokal kopia (se set_transform-mallen), och det ar
# raden n.PositionMatrix = m som ar flytten.
FLYTTATTRIBUT = ("PositionMatrix", "WorldPositionMatrix", "Position",
                 "WorldPosition")

# Anrop som far VC att rakna om scenen, sa att varldsmatrisen ar aktuell
# igen. update() ar det MATTA fallet (M-11: bara sim.update() hamtar hem
# den; M-36: matmallarna kor n.update() plus getSimulation().update()).
# run och step tas med darfor att de driver simuleringen framat, och en
# simulering som gatt ett steg har raknat om lagena.
UPPDATERANDE = ("update", "run", "step")

# Attributet vars LASNING ger det slapande vardet.
VARLDSMATRIS = "WorldPositionMatrix"

# Argumentnamn som alltid pekar pa en komponent som redan MASTE finnas i
# scenen. De tva namnen star har och inte som en genomsokning av
# beskrivningarna, av ett skal: registret har ocksa argument som heter name
# och new_name och som namnger en komponent som ska SKAPAS (load_component,
# clone_component). Att krava att den redan ar last vore att krava att den
# fanns innan den laddades. Provet test_komponentargumenten_betyder_befintlig
# faller om ett nytt verktyg ger namnen en annan betydelse.
KOMPONENTARGUMENT = ("component", "other_component")


@dataclass(frozen=True)
class Turdom:
    """Grindens svar. Tomt skal betyder att anropet far goras."""

    grind: str = ""
    skal: Tuple[str, ...] = ()

    @property
    def nekas(self) -> bool:
        return bool(self.skal)


# ---- vad koden gor -------------------------------------------------------

def _trad(kod: str):
    try:
        return ast.parse(kod or "")
    except (SyntaxError, ValueError):
        return None


def flyttar(kod: str) -> Tuple[str, ...]:
    """Raderna dar koden tilldelar ett lagesattribut. Tom = ingen flytt."""
    trad = _trad(kod)
    if trad is None:
        return ()
    ut = []
    for nod in ast.walk(trad):
        mal = None
        if isinstance(nod, ast.Assign):
            mal = list(nod.targets)
        elif isinstance(nod, ast.AugAssign):
            mal = [nod.target]
        if not mal:
            continue
        for m in mal:
            if isinstance(m, ast.Attribute) and m.attr in FLYTTATTRIBUT:
                ut.append("rad %s: tilldelning till .%s"
                          % (getattr(nod, "lineno", "?"), m.attr))
    return tuple(ut)


def uppdaterar(kod: str) -> bool:
    """Sant om koden far VC att rakna om scenen innan den laser."""
    trad = _trad(kod)
    if trad is None:
        return False
    for nod in ast.walk(trad):
        if isinstance(nod, ast.Call) and _sista_namnet(nod.func) in UPPDATERANDE:
            return True
    return False


def laser_varldsmatrisen(kod: str) -> Tuple[str, ...]:
    """Raderna dar koden LASER WorldPositionMatrix (aldrig skriver den)."""
    trad = _trad(kod)
    if trad is None:
        return ()
    skrivna = set()
    for nod in ast.walk(trad):
        mal = (list(nod.targets) if isinstance(nod, ast.Assign)
               else [nod.target] if isinstance(nod, ast.AugAssign) else [])
        for m in mal:
            if isinstance(m, ast.Attribute) and m.attr == VARLDSMATRIS:
                skrivna.add(id(m))
    ut = []
    for nod in ast.walk(trad):
        if (isinstance(nod, ast.Attribute) and nod.attr == VARLDSMATRIS
                and id(nod) not in skrivna):
            ut.append("rad %s: laser .%s" % (getattr(nod, "lineno", "?"),
                                             VARLDSMATRIS))
    return tuple(ut)


def andrar_scenen(kod: str) -> Tuple[str, ...]:
    """Skalen till att koden andrar scenen. Tom lista = den andrar inget.

    Snavare an skrivgrind.granska: ett anrop som BARA uppdaterar (update, run,
    step) andrar ingen geometri, och en matmall som kor _farsk() for att fa
    farska matt (M-36) far inte se ut som en andring som maste lasas tillbaka.
    """
    trad = _trad(kod)
    if trad is None:
        # Oparsbar kod ar redan avvisad av skrivgrinden i forgranskningen.
        # Har raknas den som en andring: okant ar inte godkant (I3).
        return ("koden gar inte att tolka som Python",) if kod else ()
    egna = _lokala_behallare(trad)
    ut = []
    for nod in ast.walk(trad):
        rad = getattr(nod, "lineno", "?")
        if isinstance(nod, (ast.Assign, ast.AugAssign)):
            mal = (list(nod.targets) if isinstance(nod, ast.Assign)
                   else [nod.target])
            for m in mal:
                if isinstance(m, ast.Attribute):
                    ut.append("rad %s: tilldelning till attributet .%s"
                              % (rad, m.attr))
                # En INDEXTILLDELNING raknas INTE har, och skrivgrinden gor
                # tvartom. Skillnaden ar avsiktlig och matt: matmallen skriver
                # svar["a"] = a.Name i den ordbok _matt() lamnade, och
                # skrivgrindens _lokala_behallare ser inte den som egen
                # eftersom den kommer ur ett anrop. Geometrin andras genom en
                # ATTRIBUTTILLDELNING eller ett muterande metodanrop, aldrig
                # genom ett index i ett svar som ar pa vag ut som JSON. Att
                # rakna den hade fallt kontrollfall K-20, ett farskt matt
                # efter en flytt. Fail-closed-fragan "skriver koden nagot" ags
                # fortfarande av skrivgrinden, som domer fore oss.
        elif isinstance(nod, ast.Delete):
            ut.append("rad %s: del-sats" % rad)
        elif isinstance(nod, ast.Call):
            namn = _sista_namnet(nod.func)
            # Samma rattelse som i skrivgrind.py (M-94 fynd 2). Rotnamns-
            # vandringen slappte d["app"].deleteComponent(x) igenom eftersom
            # rotnamnet "d" ar egen, och da var ett VC-objekt i en egen
            # behallare en vag rakt forbi. Ett DIREKT anrop pa namnet ar
            # sakert; ett anrop GENOM behallaren slapps bara for en sluten
            # lista av behallarmetoder, eftersom vi inte vet vad som ligger i
            # facket. Listan LANAS ur skrivgrinden - tva kopior som glider isar
            # vore ett hal i den ena.
            if isinstance(nod.func, ast.Attribute):
                if isinstance(nod.func.value, ast.Name):
                    if nod.func.value.id in egna:
                        continue
                elif (_rotnamn(nod.func.value) in egna
                      and namn in skrivgrind.BEHALLARMETODER):
                    continue
            if namn in UPPDATERANDE:
                continue
            if _ar_muterande_namn(namn):
                ut.append("rad %s: anropar %s()" % (rad, namn))
    return tuple(ut)


# ---- turens tillstand ----------------------------------------------------

@dataclass
class Turlage:
    """Vad turen har gjort hittills. Ett per tur, agt av loopen."""

    # Skalen till att pumpen ar dod. Tom lista = bryggan svarar an.
    pumpen_dod: Tuple[str, ...] = ()
    # Verktyget som dodade den, for felmeddelandet.
    dodades_av: str = ""
    # Har scenen flyttats utan att nagot rakat om den sedan dess?
    slapande: Tuple[str, ...] = ()
    slapande_av: str = ""
    # Andringar som annu inte lasts tillbaka: [(verktyg, skal)]
    olasta: List[Tuple[str, str]] = field(default_factory=list)
    # Normaliserade namn ur LYCKADE lasande verktygssvar.
    lasta_namn: set = field(default_factory=set)
    lasningar: int = 0

    # ---- fragan fore anropet -------------------------------------------

    def domer(self, verktyg: Any, argument: Dict[str, Any],
              kod: str) -> Turdom:
        """Domen over ett anrop som redan passerat forgranskningen."""
        if self.pumpen_dod:
            return Turdom("efter_sparning", tuple(
                ["%s stoppade simuleringen: %s"
                 % (self.dodades_av, "; ".join(self.pumpen_dod)),
                 "MATT M-13: bryggan svarar inte efterat, sa det har anropet "
                 "kommer inte att koras och inget utfall kommer tillbaka. "
                 "Sparningen laggs sist i turen (ARB-006, FAL-004)"]))

        laser = laser_varldsmatrisen(kod)
        if laser and self.slapande and not uppdaterar(kod):
            return Turdom("slapande_matris", tuple(
                ["%s flyttade nagot (%s) och ingenting har rakat om scenen "
                 "sedan dess" % (self.slapande_av, "; ".join(self.slapande)),
                 "det har anropet laser varldsmatrisen utan att uppdatera "
                 "forst (%s)" % "; ".join(laser),
                 "MATT M-11: varldsmatrisen slapar ett scensteg och bara "
                 "sim.update() hamtar hem den; varken render() eller flush() "
                 "gor det. Talet skulle se rimligt ut och beskriva laget "
                 "FORE flytten (FAL-002, ARB-004)"]))

        andringar = andrar_scenen(kod)
        if not andringar:
            return Turdom()

        okanda = self._okanda_komponenter(argument)
        if okanda:
            return Turdom("olast_scen", tuple(
                ["anropet andrar scenen (%s) och namnger %s, som inget "
                 "lasande anrop i den har turen har returnerat"
                 % (andringar[0], ", ".join(repr(n) for n in okanda)),
                 "las scenen innan du andrar den: lista komponenterna och las "
                 "granssnitten pa det du tanker koppla (ARB-001). Modellen "
                 "far bara valja ur det som finns (I9)"]))

        if self.olasta:
            verktyg_, skal_ = self.olasta[0]
            return Turdom("olast_skrivning", tuple(
                ["%s andrade scenen (%s) och ingenting har lasts tillbaka "
                 "sedan dess" % (verktyg_, skal_),
                 "MATT M-09: VC svaljer fel tyst, och en skrivning som inte "
                 "tog syns bara vid aterlasning. Gor en andring i taget och "
                 "las tillbaka utfallet innan du gor nasta (ARB-003, "
                 "FAL-005)"]))
        return Turdom()

    def _okanda_komponenter(self, argument: Dict[str, Any]) -> Tuple[str, ...]:
        ut = []
        for namn in KOMPONENTARGUMENT:
            varde = argument.get(namn)
            if not isinstance(varde, str) or not varde.strip():
                continue
            if normalisera(varde) not in self.lasta_namn:
                ut.append(varde)
        return tuple(ut)

    # ---- vad anropet lamnade efter sig ---------------------------------

    def lagg(self, verktyg: str, kod: str, ok: bool, resultat: Any) -> None:
        """Bokfor ett anrop som KORDES. Anropet behover inte ha lyckats.

        VAD SOM RAKNAS SOM EN LASNING avgors av KODEN och inte av verktygets
        deklarerade effect. Skalet ar matt i registret: measure_distance,
        min_distance och test_collision ar alla deklarerade write, men bara
        for att de kor update() for att fa farska matt (M-36, se
        verktyg/matning.py). De ANDRAR ingenting, och en grind som lat dem
        rakna som andringar hade stangt enda vagen till ett farskt matt efter
        en flytt (kontrollfall K-20).

        Ett DATA-verktyg (mode != codegen) genererar ingen kod och nar aldrig
        scenen. Dess svar far darfor inte fylla pa lasta_namn: en trafflista
        ur katalogen sager att en komponent finns pa disk, inte att den star
        i den har layouten.
        """
        dodar = skrivgrind.dodar_pumpen(kod or "")
        if dodar:
            # Bokfors aven nar utfallet sager ok. MATT M-13: sparningen SKER,
            # men bryggan gar ned efterat, sa ett ok-svar sager ingenting om
            # vad som hander harnast.
            self.pumpen_dod = tuple(dodar)
            self.dodades_av = verktyg
        if not ok:
            # Ett anrop som foll andrade ingenting, och far darfor varken
            # satta slapflaggan eller kraven pa aterlasning.
            return
        andringar = andrar_scenen(kod or "")
        if andringar:
            self.olasta.append((verktyg, andringar[0]))
        flyttningar = flyttar(kod or "")
        if flyttningar:
            self.slapande = flyttningar
            self.slapande_av = verktyg
        elif uppdaterar(kod or ""):
            self.slapande = ()
            self.slapande_av = ""
        if kod and not andringar:
            self.lasningar += 1
            self.olasta = []
            self._lagg_namn(resultat)

    def _lagg_namn(self, varde: Any) -> None:
        if isinstance(varde, str):
            ren = normalisera(varde)
            if ren:
                self.lasta_namn.add(ren)
        elif isinstance(varde, dict):
            for v in varde.values():
                self._lagg_namn(v)
        elif isinstance(varde, (list, tuple)):
            for v in varde:
                self._lagg_namn(v)


def komponentargument(register) -> List[Tuple[str, str]]:
    """(verktyg, argument) for varje argument som heter component-nagot.

    Konsument: provet som kraver att namnen fortfarande betyder EN BEFINTLIG
    komponent. Ett nytt verktyg som later component betyda nagot annat ska
    fella provet i stallet for att tyst oppna ett hal i olast_scen.
    """
    ut = []
    for namn, verktyg in sorted(register.items()):
        for arg in sorted(verktyg.parameters["properties"]):
            if arg in KOMPONENTARGUMENT:
                ut.append((namn, arg))
    return ut
