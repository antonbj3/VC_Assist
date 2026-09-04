# -*- coding: utf-8 -*-
"""Forgranskningen: allt som avvisas INNAN nagot kors.

Grinden bygger ingen ny validering. Den anropar den som redan finns:

    verktyg.REGISTER            finns verktyget alls (I9)
    formagegrind.Urval.krav     ar det pa i den har VC-installationen
    verktyg.validera_argument   haller argumenten schemat (I9)
    api_index.Validator         ar VC-namnen i koden riktiga (fas 4)
    skrivgrind.granska          skriver koden nagot (bryggans andra linje)
    skrivgrind.skapar_skriptbeteende / dodar_pumpen   M-13
    sakerhet.Sakerhetsgrind     ror anropet en sakerhetsfunktion (I15)
    bank/katalog_index.json     finns URI:n (I9)

GRINDORDNINGEN, och varfor den ar som den ar:

  1 tomt_anrop      ett anrop utan namn ar inget anrop
  2 sakerhet        FORE allt annat, med flit. I15 ar ovillkorlig och far
                    inte kunna maskeras av ett annat avslag; dessutom maste
                    den kunna doma ett anrop till ett verktyg som inte ens
                    finns, och det kan den, eftersom den laser argumentens
                    varden och inte verktygets schema.
  3 ratkod          ra Python fran modellen kringgar bade kon och
                    skrivgrinden och avvisas fore namnuppslaget, eftersom
                    fragan inte ar om koden ar riktig utan om den far finnas.
  4 okant_verktyg   registret
  5 avstangt        formagegrinden
  6 argument        schemat
  7 katalog_uri     en URI som varken star i katalogindexet eller i
                    operatorens egen uppgift
  8 api_namn        AST-validering av den genererade koden
  9 skrivgrind      lasande verktyg vars kod skriver, och skriptbeteenden

82_felklasser.md, sorteringsregel 1: forsta grinden som faller bestammer
klassen. Ordningen ar alltsa inte en smakfraga utan en klassningsregel, och
den ar darfor skriven en gang, har.
"""
from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import api_index
from .. import verktyg as V
from ..verktyg.fel import Argumentfel, Avstangt
from .sakerhet import ROT, Sakerhetsgrind

_EXT = os.path.join(ROT, "ext", "vc_addon", "vc_assist")
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import skrivgrind  # noqa: E402

GRINDAR = ("tomt_anrop", "sakerhet", "ratkod", "okant_verktyg", "avstangt",
           "argument", "katalog_uri", "api_namn", "skrivgrind")

# Bryggan lagger _s i exec-globalerna vid varje korning (pump.py:_kor), sa
# mallarna kallar en funktion som inte star i deras egen kod. Validatorn ser
# bara koden, och maste darfor fa _s deklarerad. MATT 2026-09-04 over
# registrets da 66 kodgenererande verktyg: utan raden blir 55 av 66 mallar
# OBESTAMBARA pa sitt eget hjalpanrop, med raden 0 av 66. Provet raknar om
# talen vid varje korning i stallet for att lita pa dem
# (test_harness.test_alla_verktygsmallar_passerar_api_grinden), eftersom
# registret vaxer.
BRYGGANS_GLOBALER = "def _s(text):\n    return text\n"
_STUBRADER = BRYGGANS_GLOBALER.count("\n")

# Argumentnamn som inte far finnas: de bar kod, och kod fran modellen gar
# aldrig in i bryggan (I12, VRK-005).
KODARGUMENT = ("code", "kod", "script", "skript", "python", "source",
               "kallkod", "expression", "eval", "exec", "snippet")

# Teckenfoljder som visar att ett argumentvarde ar kod och inte ett namn.
# Listan ar avsiktligt kort och specifik: ett komponentnamn ska aldrig
# fastna, och en modell som smugglar kod traffar minst en av dem.
KODSPAR = ("getapplication(", "getsimulation(", "import ", "exec(", "eval(",
           "createbehaviour(", "lambda ", "def ", "__import__", "os.system",
           "subprocess")

# Vilka (verktyg, argument) som bar en URI, och om URI:n ar en KALLA (nagot
# som redan ska finnas) eller ett MAL (nagot som ska skrivas). Bara kallor
# provas mot katalogindexet: att krava att en sparsokvag redan star i
# katalogen vore att krava att filen finns innan den har skrivits.
#
# Ett verktyg som INTE star har och anda bar en URI behandlas som kalla.
# Fail-closed, och test_harness.test_varje_uriargument_ar_klassat faller sa
# fort registret far ett nytt uri-argument - sa att ett nytt verktyg tvingar
# fram ett beslut i stallet for att arva ett.
URIMAL = frozenset((("save_layout", "uri"),))

# (verktyg, argument) dar en URI ar en FRAGA till indexet i stallet for ett
# bruk av det. Katalogverktygen svarar sjalva found=false med verkliga
# alternativ ur indexet, och det svaret ar arligare an ett avslag: en modell
# maste kunna FRAGA om en URI finns utan att grinden domer fragan.
URIFRAGOR = frozenset((("catalog_item", "uri"), ("search_catalog", "query")))

# (verktyg, argument) dar URI:n ar en KALLA. Listan star har for att den ska
# ga att lasa, men den ar inte det som styr: allt som varken ar mal eller
# fraga behandlas som kalla. Fail-closed.
URIKALLOR = frozenset((("load_component", "uri"),))

# Sprakmarkning pa ett kodblock i modellens text -> hur blocket domes.
_PYTHONSPRAK = ("python", "py", "python2", "python27", "vc", "")
_STSPRAK = ("st", "iec", "structured-text", "iecst")


@dataclass(frozen=True)
class Avvisning:
    """Ett avslag fore korning."""

    grind: str
    skal: Tuple[str, ...]
    vad: str

    @property
    def kod(self) -> str:
        return "AVVISAD:%s" % self.grind

    def text(self) -> str:
        return "%s avvisades av grinden %s: %s" % (
            self.vad, self.grind, "; ".join(self.skal))


@dataclass
class Forgranskningsdom:
    """Domen over ett anrop eller en text."""

    avvisning: Optional[Avvisning] = None
    varningar: Tuple[str, ...] = ()
    kod: str = ""                     # den genererade koden, om nagon
    verktyg: Optional[Any] = None
    argument: Dict[str, Any] = field(default_factory=dict)

    @property
    def slapps(self) -> bool:
        return self.avvisning is None


def _uri_i(varde: Any) -> List[str]:
    ut = []
    if isinstance(varde, str):
        if "://" in varde:
            ut.append(varde.strip())
    elif isinstance(varde, dict):
        for v in varde.values():
            ut.extend(_uri_i(v))
    elif isinstance(varde, (list, tuple)):
        for v in varde:
            ut.extend(_uri_i(v))
    return ut


def uriargument(register) -> List[Tuple[str, str]]:
    """Alla (verktyg, argument) i registret vars beskrivning ror en URI.

    Anvands av provet som kraver att varje uri-argument ar klassat som mal,
    fraga eller kalla. Ett nytt verktyg med en URI ska tvinga fram ett
    beslut, inte arva ett.
    """
    ut = []
    for namn, verktyg in sorted(register.items()):
        for arg, schema in sorted(verktyg.parameters["properties"].items()):
            text = "%s %s" % (arg, schema.get("description", ""))
            if "uri" in text.lower():
                ut.append((namn, arg))
    return ut


class Forgranskare(object):
    """Grindkedjan fore korning. Aterbrukar, implementerar inte om."""

    def __init__(self, urval=None, register=None, validator=None,
                 sakerhetsgrind=None, katalogindex=None, kodgen=None):
        self.register = V.REGISTER if register is None else register
        self.urval = (V.urval_allt_pa(self.register) if urval is None
                      else urval)
        self.validator = (api_index.bygg_validator() if validator is None
                          else validator)
        self.sakerhet = (Sakerhetsgrind() if sakerhetsgrind is None
                         else sakerhetsgrind)
        self.katalogindex = (self.sakerhet.katalogindex if katalogindex is None
                             else katalogindex)
        self.kodgen = V.CODE_GEN_HANDLERS if kodgen is None else kodgen

    # ---- ett verktygsanrop ----------------------------------------------

    def granska_anrop(self, anrop, uppgiftstext: str = "") -> Forgranskningsdom:
        """Provar ett anrop mot hela kedjan. Forsta grinden som faller vinner."""
        vad = anrop.beskrivning()

        namn = (anrop.namn or "").strip()
        if not namn:
            return self._nej("tomt_anrop", vad, [
                "anropet saknar verktygsnamn; ett anrop utan namn ar inget "
                "anrop, och tystnad ar aldrig ett godkannande (I3)"])
        if not isinstance(anrop.argument, dict):
            return self._nej("tomt_anrop", vad, [
                "argumenten ar %s, inte ett objekt"
                % type(anrop.argument).__name__])

        verktyg = self.register.get(namn)
        verkan = verktyg.effect if verktyg is not None else None

        dom = self.sakerhet.granska_anrop(verkan, anrop.argument)
        if dom.nekas:
            return self._nej("sakerhet", vad, dom.skal)

        rat = self._ratkod(anrop.argument)
        if rat:
            return self._nej("ratkod", vad, rat)

        if verktyg is None:
            return self._nej("okant_verktyg", vad, [
                "%r finns inte bland de %d registrerade verktygen; ett namn "
                "som inte star i listan finns inte (I9)"
                % (namn, len(self.register))])

        try:
            self.urval.krav(namn)
        except Avstangt as e:
            return self._nej("avstangt", vad, [str(e)])

        try:
            argument = V.validera_argument(verktyg, anrop.argument)
        except Argumentfel as e:
            return self._nej("argument", vad, e.problem)

        uri_skal = self._uri_problem(namn, argument, uppgiftstext)
        if uri_skal:
            return self._nej("katalog_uri", vad, uri_skal)

        if verktyg.mode != "codegen":
            # Ett data-verktyg genererar ingen kod och har ingenting for de
            # tva sista grindarna att lasa. Det ar inte en lucka: schemat och
            # sakerhetsgrinden har redan dömt argumenten, och handlaren nar
            # aldrig bryggan.
            return Forgranskningsdom(verktyg=verktyg, argument=argument)

        kod = self.kodgen[namn](argument)
        if not isinstance(kod, str):
            return self._nej("api_namn", vad, [
                "kodgeneratorn lamnade %s, inte en strang" % type(kod).__name__])

        api = self._api_problem(kod)
        if api:
            return self._nej("api_namn", vad, api)

        skriv = self._skrivproblem(kod, verktyg.effect)
        if skriv:
            return self._nej("skrivgrind", vad, skriv)

        return Forgranskningsdom(verktyg=verktyg, argument=argument, kod=kod,
                                 varningar=tuple(self._pumpvarningar(kod)))

    # ---- modellens egen text --------------------------------------------

    def granska_svarstext(self, text: str) -> Forgranskningsdom:
        """Provar modellens SLUTSVAR: kodblock och sakerhetsforslag.

        Ett kodblock i ett svar ar inte ofarligt. Det ar det operatoren
        klistrar in, och det gar da forbi bade kon och skrivgrinden. Darfor
        provas det med SAMMA grindar som en verktygsmall.
        """
        dom = self.sakerhet.granska_text(text)
        if dom.nekas:
            return self._nej("sakerhet", "slutsvaret", dom.skal)

        for sprak, block in kodblock(text):
            lag = (sprak or "").lower()
            if lag in _STSPRAK:
                st_dom = self.sakerhet.granska_st(block)
                if st_dom.nekas:
                    return self._nej("sakerhet", "ST-blocket i slutsvaret",
                                     st_dom.skal)
                continue
            if lag not in _PYTHONSPRAK:
                continue
            if not lag and not _ar_python(block):
                # Ett OMARKT block som inte ens gar att parsa ar prosa, inte
                # kod. Att doma det hade gjort grinden till en som anklagar
                # loptext, och en grind som anklagar i onodan slutar bli last.
                # Ett omarkt block som DAREMOT parsar domes: en modell ska
                # inte kunna gomma kod genom att utelamna sprakmarkningen.
                continue
            api = self._api_problem(block)
            if api:
                return self._nej("api_namn", "kodblocket i slutsvaret", api)
            skriv = self._skrivproblem(block, "read")
            if skriv:
                return self._nej(
                    "skrivgrind", "kodblocket i slutsvaret",
                    skriv + ["kod som andrar scenen gar genom ett skrivande "
                             "verktyg och darmed genom godkannandekon (I12); "
                             "den klistras aldrig in i VC forbi kon"])
        return Forgranskningsdom()

    # ---- delgrindar ------------------------------------------------------

    @staticmethod
    def _nej(grind: str, vad: str, skal: Sequence[str]) -> Forgranskningsdom:
        return Forgranskningsdom(
            avvisning=Avvisning(grind=grind, skal=tuple(skal), vad=vad))

    @staticmethod
    def _ratkod(argument: Dict[str, Any]) -> List[str]:
        skal = []
        for namn in sorted(argument):
            if namn.lower() in KODARGUMENT:
                skal.append(
                    "argumentet %r bar kod; modellen skickar aldrig egen kod, "
                    "allt som ror scenen gar genom ett verktyg (I12)" % namn)
        for namn in sorted(argument):
            varde = argument[namn]
            if not isinstance(varde, str):
                continue
            lag = varde.lower()
            for spar in KODSPAR:
                if spar in lag:
                    skal.append(
                        "argumentet %r innehaller %r och ar alltsa kod, inte "
                        "ett namn" % (namn, spar))
                    break
        return skal

    def _uri_problem(self, verktyg: str, argument: Dict[str, Any],
                     uppgiftstext: str) -> List[str]:
        skal = []
        for arg in sorted(argument):
            if (verktyg, arg) in URIMAL or (verktyg, arg) in URIFRAGOR:
                continue
            for uri in _uri_i(argument[arg]):
                skal.extend(self._en_uri(uri, uppgiftstext))
        return skal

    def _en_uri(self, uri: str, uppgiftstext: str) -> List[str]:
        """Skalen mot EN kall-URI. Tom lista betyder att den far anvandas."""
        if uri in self.katalogindex:
            return []
        if uppgiftstext and uri in uppgiftstext:
            # Operatorens egen URI. Modellen har inte hittat pa den, och
            # katalogen ar matt tom pa laddbara VC-URI:er - att neka den vore
            # att stanga enda vagen in for en verklig fil.
            return []
        return ["%r star varken i katalogindexet (%d poster) eller i "
                "uppgiften; en uppfunnen URI ar ett hart fel, inte en varning "
                "(I9). Valj ur katalogverktygets trafflista."
                % (uri, len(self.katalogindex))]

    def _api_problem(self, kod: str) -> List[str]:
        granskning = self.validator.granska(BRYGGANS_GLOBALER + kod)
        if granskning.godkand:
            return []
        skal = []
        for fel in granskning.fel:
            skal.append("rad %d: %s" % (max(1, fel.rad - _STUBRADER), fel.text))
        for obestambar in granskning.obestambara:
            skal.append("rad %d: %s (obestambart, och obestambart ar inte "
                        "godkant, I3)"
                        % (max(1, obestambar.rad - _STUBRADER), obestambar.text))
        return skal

    @staticmethod
    def _skrivproblem(kod: str, verkan: str) -> List[str]:
        skal = []
        skript = skrivgrind.skapar_skriptbeteende(kod)
        if skript:
            skal.append(
                "koden skapar ett skriptbeteende (%s); MATT M-13: det stoppar "
                "den korande simuleringen och dodar bryggan mitt i dess eget "
                "svar" % "; ".join(skript))
        if verkan == "read":
            dom = skrivgrind.granska(kod)
            if dom.skriver:
                skal.append(
                    "verktyget ar deklarerat lasande men bryggans skrivgrind "
                    "domer koden som skrivande: %s" % "; ".join(dom.skal))
        return skal

    @staticmethod
    def _pumpvarningar(kod: str) -> List[str]:
        skal = skrivgrind.dodar_pumpen(kod)
        if not skal:
            return []
        return ["MATT M-13: %s. Bryggan svarar inte efterat, sa det kommer "
                "inget utfall och ingenting efter detta anrop kors."
                % "; ".join(skal)]


# ---- kodblock ------------------------------------------------------------

def _ar_python(kod: str) -> bool:
    """Sant om texten alls gar att parsa som Python 3."""
    try:
        ast.parse(kod)
    except (SyntaxError, ValueError):
        return False
    return True


def kodblock(text: str) -> List[Tuple[str, str]]:
    """(sprakmarkning, kod) for varje trestreckat block i texten.

    Ett oavslutat block raknas MED, med det som star efter oppningen. En
    avhuggen kodmarkering ska inte kunna gomma koden for grinden.
    """
    ut = []
    rader = (text or "").splitlines()
    i = 0
    while i < len(rader):
        rad = rader[i].strip()
        if rad.startswith("```"):
            sprak = rad[3:].strip()
            kropp = []
            i += 1
            while i < len(rader) and not rader[i].strip().startswith("```"):
                kropp.append(rader[i])
                i += 1
            ut.append((sprak, "\n".join(kropp)))
        i += 1
    return ut
