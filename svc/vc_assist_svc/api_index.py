# -*- coding: utf-8 -*-
"""Sokbart index over VC:s Python-API, plus en AST-validator over det.

Fas 4 i docs/spec/70_faser.md. Grinden som stanger fasen star i
docs/spec/46_kunskapsindex.md: indexet ska bara minst de matta 204 typerna,
966 metoderna och 1159 egenskaperna, ett kant namn ska ge exakt signatur, ett
pahittat namn ska ge TOMT svar (aldrig en gissning), och over N forsok ska noll
uppfunna namn slippa igenom.

Kallor, alla under docs/referens/vc_api/ (docs/spec/10_matta_fakta.md:
utdragna ur VC 4.10:s egen "Python 2/Auto Complete"-mapp):

  vc_python_api.json  namnen, atkomsten och beskrivningarna. MANDATERAD kalla:
                      det ar den har filen fasens grind raknar sina tal ur.
  api.xml             samma 204 typer men med det JSON-filen tappat:
                      parameterlistor, returtyper och arv (<parents>).
  constants.xml       709 VC_-konstanter.
  helpers.xml         8 vcHelpers-moduler.

Bara standardbiblioteket. Python 3 (tjanstesidan; VC:s egen sida ar 2.7 och
rors inte harifran).

Arlighet om rackvidden, last innan du litar pa ett godkannande:

  * Validatorn domer VC-NAMN. Rena Python-namn (str.split, math.sqrt, egna
    funktioner) ligger utanfor och domes inte alls.
  * VC-objekt bar anvandardefinierade egenskaper som ingen statisk kalla kan
    kanna till. En OKAND EGENSKAPSLASNING pa en typ som kan skapa egenskaper
    ar darfor OBESTAMBAR, inte ett fel -- men den godkanns inte heller
    (docs/spec/90_invarianter.md I3, fail-closed).
  * En VC-hake (def OnComponentAdded(component)) far sina parametrar typade
    ur handelsens deklaration i api.xml. En EGEN funktions parameter har ingen
    deklarerad typ och domes darfor inte alls -- det ar den kvarvarande blinda
    flacken, provad och uttalad i test_egen_funktions_parameter_domes_inte_alls.
  * Kallan deklarerar grova returtyper (findBehaviour ger "vcBehaviour" aven
    nar objektet ar en vcSimInterface). Ett namn som finns pa en UNDERTYP
    slapps darfor igenom med en notering, inte som ett fel.
  * vcScript:s modulfunktioner star inte i nagon av kallorna. De som ocksa ar
    metoder pa en skripttyp (getApplication, getComponent, getSimulation,
    getTrigger ...) kan harledas darur; ovriga bara namn blir OBESTAMBARA.
  * Koden som VC kor ar Python 2.7. `ast` i Python 3 kan inte parsa
    2.7-satser (`print x`). Oparsbar kod ar ett FEL, aldrig ett godkannande.
"""
from __future__ import annotations

import ast
import builtins
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Ordagrant ur docs/spec/46_kunskapsindex.md: raden som varje lookup-svar bar.
INSTRUKTION = "Anvand namnet exakt som det star. Omformulera det inte."

# docs/spec/10_matta_fakta.md: API-ytan ar utdragen ur VC 4.10:s installation.
# docs/spec/36_versioner.md kraver att tva versioner aldrig blandas i ett svar,
# darfor bar varje symbol sin version och indexet byggs per version.
VC_VERSION_STANDARD = "4.10"

# Matt i kallan: `access` i api.xml ar R/RW/W/RO/RW/R for 1125 av 1159
# egenskaper. De ovriga 34 bar en PARAMETERLISTA i atkomstfaltet -- de ar
# metoder som kallan felklassat (t.ex. vcCurveData.getCurveLength). Vi behaller
# kallans klassning men lagger parameterlistan dar den hor hemma, i signaturen,
# och raknar dem i statistik()["egenskaper_med_parameterlista"].
ATKOMSTVARDEN = frozenset(("R", "RW", "W", "RO", "Rw", "RW/R", "None"))

# Matt: 84 egenskapsnamn och 56 metodnamn i api.xml bar ett efterslapande
# blanksteg ("vcProduct.getProperty "). Ostrippade skulle de gora 140 riktiga
# namn okanda for validatorn, alltsa 140 falskt positiva. Namn strippas.
_NAMNSKRAP = " \t\r\n"

# Tre tal, tre olika storheter (en parameter som bar tva storheter doljer
# felet i det vanliga fallet). Alla tre ar matta over provsamlingen i
# tests/enhet/test_api_index.py, 29 kodstrangar med kanda uppfunna namn varav
# 24 har ett avsett namn. test_forslagstrosklarna_kommer_ur_provsamlingen
# raknar om dem och faller om nagot av talen inte langre stammer.
#
# FORSLAG_AVSTAND_TAK: hur langt bort ett forslag far ligga och anda visas.
# Matt med MAX_FORSLAG platser i listan: det avsedda namnet ligger som langst
# 8 redigeringar bort (getMinimumDistance -> getMinimumDistanceDistance). Ett
# storre tak ger inte en enda traff till, bara brus. Finns inget inom taket
# blir forslagslistan TOM -- det ar det arliga svaret, inte en gissning
# (docs/spec/46_kunskapsindex.md, punkt 3).
#
# MAX_FORSLAG: matt over samma samling, andel av de 24 fall som har ett avsett
# namn: 3 platser ger 14, 5 ger 18, 7 ger 20, 10 ger fortfarande 20. Vi tar 5:
# steget till 7 kostar 40 procent langre lista for tva fall till, och de tva
# ligger 9-10 redigeringar bort.
#
# NARAMISS_AVSTAND: hur nara ett OKANT namn maste ligga ett kant for att
# raknas som en fordarvning av det kanda i stallet for ett nytt namn. Matt
# over provsamlingens stavfelsklass (PostionMatrix, SimSped, canConect,
# getPropety, isConnected): storsta avstandet dar ar 1. Talet anvands bara
# till att skilja FEL fran OBESTAMBART pa typer som kan bara
# anvandardefinierade egenskaper; bada stoppar godkannandet.
FORSLAG_AVSTAND_TAK = 8
MAX_FORSLAG = 5
NARAMISS_AVSTAND = 1

# Ordinal rangordning for sokning, inte ett matt tal: exakt fore prefix fore
# delstrang, namn fore typnamn fore beskrivning. Poangen ar platsen i listan.
_RANGORDNING = (
    "exakt",
    "exakt_skiftlagesokant",
    "prefix",
    "delstrang_namn",
    "delstrang_inuti_ord",
    "delstrang_typ",
    "delstrang_beskrivning",
)

_ORD_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z]+|[0-9]+")


def _segment(text: str) -> set:
    """Dela namn i ordsegment for ordgranskontroll (M-119 / E3e)."""
    return {m.group(0).lower() for m in _ORD_RE.finditer(text or "")}

# Medlemsnamn som hor till Python sjalv, hamtade ur den korande tolkens egna
# typer i stallet for en handskriven lista som skulle aldras.
_PYTHONMEDLEMMAR = frozenset(
    namn
    for typ in (str, bytes, list, dict, tuple, set, int, float, bool, object)
    for namn in dir(typ)
)

# Python egna inbyggda funktioner, ur den korande tolken.
_INBYGGDA = frozenset(dir(builtins))

# Namn som gor ett uppslag dynamiskt och darmed ostatiskt domsbart.
_DYNAMISKA = frozenset(("getattr", "setattr", "hasattr", "delattr", "eval",
                        "exec", "execfile", "__import__", "vars", "globals",
                        "locals"))

_KONSTANTMONSTER = re.compile(r"^VC_[A-Z0-9_]+$")
_TYPMONSTER = re.compile(r"^vc[A-Z][A-Za-z0-9_]*$")
_PY2PRINT = re.compile(r"^[ \t]*print[ \t]+[^(=\n]", re.MULTILINE)

_HAR = os.path.dirname(os.path.abspath(__file__))
KATALOG_STANDARD = os.path.normpath(
    os.path.join(_HAR, "..", "..", "docs", "referens", "vc_api"))


def avstand(a: str, b: str) -> int:
    """Redigeringsavstand (Levenshtein) mellan tva namn, skiftlagesokansligt.

    Skiftlagesokansligt for att `PositionMatrix` mot `positionmatrix` ar samma
    hallucination som `PositionMatrix` mot `PositionMatrics`.
    """
    a = a.lower()
    b = b.lower()
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    forra = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        denna = [i]
        for j, cb in enumerate(b, 1):
            denna.append(min(forra[j] + 1, denna[j - 1] + 1,
                             forra[j - 1] + (ca != cb)))
        forra = denna
    return forra[-1]


@dataclass(frozen=True)
class Symbol:
    """En namngiven punkt i API-ytan, med sin harkomst."""

    sort: str                 # typ | metod | egenskap | handelse | konstant
    typ_namn: str             # agande typ, "" for konstanter och typer
    namn: str
    signatur: Optional[str] = None      # parameterlista, ur api.xml
    vardetyp: Optional[str] = None      # retur- eller egenskapstyp
    atkomst: Optional[str] = None       # R | RW | W ...
    beskrivning: str = ""
    kalla: str = ""                     # filen namnet kom ur
    berikad_av: Optional[str] = None    # filen signatur/vardetyp kom ur
    vc_version: str = VC_VERSION_STANDARD

    @property
    def fullnamn(self) -> str:
        return "%s.%s" % (self.typ_namn, self.namn) if self.typ_namn else self.namn

    def harkomst(self) -> str:
        """Varifran namnet kommer: vilken klass, vilken fil."""
        var = "typ %s" % self.typ_namn if self.typ_namn else "modulniva"
        text = "%s, %s, VC %s" % (var, self.kalla, self.vc_version)
        if self.berikad_av:
            text += " (signatur ur %s)" % self.berikad_av
        return text

    def svar(self, anropad_typ: Optional[str] = None) -> str:
        """Svarstexten till modellen. Bar alltid INSTRUKTION (spec 46)."""
        arvd = anropad_typ and self.typ_namn and anropad_typ != self.typ_namn
        fullnamn = "%s.%s" % (anropad_typ, self.namn) if arvd else self.fullnamn
        rad0 = "%s %s" % (self.sort, fullnamn)
        if arvd:
            rad0 += " (arvd fran %s)" % self.typ_namn
        rader = [rad0]
        if self.signatur is not None:
            rader.append("parametrar: %s" % self.signatur)
        if self.vardetyp:
            rader.append("typ: %s" % self.vardetyp)
        if self.atkomst:
            rader.append("atkomst: %s" % self.atkomst)
        if self.beskrivning:
            rader.append(self.beskrivning)
        harkomst = self.harkomst()
        if arvd:
            harkomst += " (arvd fran typ %s, kan anropas pa %s)" % (self.typ_namn, anropad_typ)
        rader.append("harkomst: %s" % harkomst)
        rader.append(INSTRUKTION)
        return "\n".join(rader)


@dataclass(frozen=True)
class Traff:
    """En soktraff: symbolen, hur den traffades, och varifran den kommer."""

    symbol: Symbol
    rang: str                 # ett varde ur _RANGORDNING
    poang: int

    @property
    def harkomst(self) -> str:
        return self.symbol.harkomst()


def _text(nod, tagg) -> str:
    v = nod.findtext(tagg)
    return (v or "").strip()


class ApiIndex(object):
    """Uppslag pa klass, metod, egenskap, handelse och konstant."""

    def __init__(self, katalog: Optional[str] = None,
                 vc_version: str = VC_VERSION_STANDARD):
        self.katalog = katalog or KATALOG_STANDARD
        self.vc_version = vc_version

        self.symboler: List[Symbol] = []
        self.spec_symboler: List[Symbol] = []
        self.typer: Dict[str, Symbol] = {}
        self.hjalpmoduler: Dict[str, Symbol] = {}
        self.konstanter: Dict[str, Symbol] = {}
        self._medlemmar: Dict[str, Dict[str, List[Symbol]]] = {}
        self._foraldrar: Dict[str, List[str]] = {}
        self._globala: Dict[str, List[Symbol]] = {}
        self._mro_cache: Dict[str, List[str]] = {}
        self._barn: Dict[str, List[str]] = {}
        self._subtyp_cache: Dict[str, List[str]] = {}
        self._ytor: Dict[str, Dict[str, List[Symbol]]] = {}

        self._raknare = {
            "egenskaper_med_parameterlista": 0,
            "strippade_namn": 0,
        }

        self._las_json()
        self._berika_ur_api_xml()
        self._las_konstanter()
        self._las_hjalpare()
        self._las_spec()
        self._efterbygg()

    # ---------------------------------------------------------------- laddning

    def _stig(self, filnamn: str) -> str:
        stig = os.path.join(self.katalog, filnamn)
        if not os.path.exists(stig):
            raise IOError("kallan saknas: %s" % stig)
        return stig

    def _lagg(self, symbol: Symbol) -> None:
        self.symboler.append(symbol)
        if symbol.sort == "typ":
            self.typer[symbol.namn] = symbol
            self._medlemmar.setdefault(symbol.namn, {})
            return
        if symbol.sort == "konstant":
            self.konstanter[symbol.namn] = symbol
        else:
            self._medlemmar.setdefault(symbol.typ_namn, {}) \
                .setdefault(symbol.namn, []).append(symbol)
        self._globala.setdefault(symbol.namn, []).append(symbol)

    def _rent(self, namn: str) -> str:
        rent = namn.strip(_NAMNSKRAP)
        if rent != namn:
            self._raknare["strippade_namn"] += 1
        return rent

    def _las_json(self) -> None:
        """Den mandaterade kallan. Namn, atkomst, beskrivningar."""
        kalla = "vc_python_api.json"
        with open(self._stig(kalla), "r", encoding="utf-8") as f:
            data = json.load(f)
        for typ_namn in data:
            self._lagg(Symbol(sort="typ", typ_namn="", namn=typ_namn,
                              beskrivning="Visual Components API-typ %s." % typ_namn,
                              kalla=kalla, vc_version=self.vc_version))
        for typ_namn, kropp in data.items():
            for m in kropp.get("methods", []):
                self._lagg(Symbol(
                    sort="metod", typ_namn=typ_namn,
                    namn=self._rent(m["name"]),
                    beskrivning=(m.get("desc") or "").strip(),
                    kalla=kalla, vc_version=self.vc_version))
            for p in kropp.get("properties", []):
                atkomst = (p.get("access") or "").strip()
                signatur = None
                if atkomst not in ATKOMSTVARDEN:
                    # Kallans felklassade metod: atkomstfaltet bar parametrarna.
                    signatur = " ".join(atkomst.split())
                    atkomst = None
                    self._raknare["egenskaper_med_parameterlista"] += 1
                self._lagg(Symbol(
                    sort="egenskap", typ_namn=typ_namn,
                    namn=self._rent(p["name"]),
                    signatur=signatur,
                    vardetyp=(p.get("type") or "").strip() or None,
                    atkomst=atkomst,
                    beskrivning=(p.get("desc") or "").strip(),
                    kalla=kalla, vc_version=self.vc_version))
            for e in kropp.get("events", []):
                # Matt: events i JSON-filen ar rena strangar, inga objekt.
                self._lagg(Symbol(
                    sort="handelse", typ_namn=typ_namn, namn=self._rent(e),
                    beskrivning="Handelse %s pa typen %s." % (self._rent(e), typ_namn),
                    kalla=kalla, vc_version=self.vc_version))

    def _berika_ur_api_xml(self) -> None:
        """Det JSON-filen tappat: parametrar, returtyper och arv."""
        kalla = "api.xml"
        rot = ET.parse(self._stig(kalla)).getroot()
        berikade: Dict[Tuple[str, str, str], Tuple[str, str]] = {}
        for typ in rot.findall("type"):
            typ_namn = _text(typ, "name")
            foraldrar = [f for f in _text(typ, "parents").split() if f]
            if foraldrar:
                self._foraldrar[typ_namn] = foraldrar
                for f in foraldrar:
                    self._barn.setdefault(f, []).append(typ_namn)
            for sort, vag in (("metod", "methods/method"),
                              ("handelse", "events/event"),
                              ("egenskap", "properties/property")):
                for nod in typ.findall(vag):
                    namn = _text(nod, "name")
                    berikade[(typ_namn, sort, namn)] = (
                        " ".join(_text(nod, "parameters").split()),
                        _text(nod, "type"))
        for i, s in enumerate(self.symboler):
            extra = berikade.get((s.typ_namn, s.sort, s.namn))
            if extra is None:
                continue
            parametrar, vardetyp = extra
            if s.sort == "egenskap":
                # Egenskapens typ star redan i JSON; api.xml tillfor inget dar.
                continue
            self.symboler[i] = Symbol(
                sort=s.sort, typ_namn=s.typ_namn, namn=s.namn,
                signatur=parametrar, vardetyp=vardetyp or None,
                atkomst=s.atkomst, beskrivning=s.beskrivning,
                kalla=s.kalla, berikad_av=kalla, vc_version=s.vc_version)

    def _las_konstanter(self) -> None:
        kalla = "constants.xml"
        rot = ET.parse(self._stig(kalla)).getroot()
        for namn in (rot.text or "").split():
            namn = namn.strip()
            if namn:
                besk = self._konstantbeskrivning(namn)
                self._lagg(Symbol(sort="konstant", typ_namn="", namn=namn,
                                  beskrivning=besk,
                                  kalla=kalla, vc_version=self.vc_version))

    @staticmethod
    def _konstantbeskrivning(namn: str) -> str:
        """Beskrivning av en VC-konstant ur dess familj och namn (M-119 / E3d)."""
        if namn.startswith("VC_STATEMENT_"):
            return "Typkonstant for satsen %s i sekvenser och rutiner." % namn[13:]
        if namn.endswith("SIGNAL") or namn.endswith("SIGNALMAP"):
            return "Typkonstant for signal av typen %s i komponenters beteendestruktur." % namn[3:]
        if namn.startswith("VC_ACTION_"):
            return "Atgardskonstant %s for vcAction och vcExecutor." % namn[10:]
        if namn.startswith("VC_JOINT_"):
            return "Ledtypkonstant %s for vcJoint." % namn[9:]
        if namn.startswith("VC_KINEMATICS_"):
            return "Kinematikkonstant %s for kinematikmodeller." % namn[14:]
        if namn.startswith("VC_MATERIAL_"):
            return "Materialkonstant %s for visuell representation." % namn[12:]
        if namn.startswith("VC_MOTION_"):
            return "Rorelsekonstant %s for rorelseplaneraren och robotcontrollers." % namn[10:]
        if namn.startswith("VC_PHYSICS_"):
            return "Fysikkonstant %s for fysikmotorn i scenen." % namn[11:]
        if namn.startswith("VC_SIMULATION_"):
            return "Simuleringskonstant %s for simuleringsstatus och handelser." % namn[14:]
        if namn.startswith("VC_SELECTION_"):
            return "Urvalskonstant %s for 3D-markering och interaktion." % namn[13:]
        if namn.startswith("VC_PROPERTY_"):
            return "Egenskapskonstant %s for komponentvariabler." % namn[12:]
        if namn.startswith("VC_INTERFACE_"):
            return "Granssnittskonstant %s for komponentkopplingar." % namn[13:]
        if namn.startswith("VC_FEATURE_"):
            return "Geometri-feature-konstant %s for noder." % namn[11:]
        if namn.startswith("VC_COLOR_"):
            return "Fargkonstant %s for grafisk visualisering." % namn[9:]
        if namn.startswith("VC_CAMERA_"):
            return "Kamerakonstant %s for vyhantering i 3D-scenen." % namn[10:]
        delar = namn.split("_")[1:]
        if delar:
            return "Konstant %s for %s i Visual Components API." % (namn, " ".join(delar).lower())
        return "Konstant %s i Visual Components API." % namn

    def _las_spec(self) -> None:
        """Grindregler och specifikationer ur docs/spec/ och bankens facit_spar."""
        rot = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        kontrakt_fil = os.path.join(rot, "docs", "spec", "41_ogat_kontrakt.md")
        if os.path.isfile(kontrakt_fil):
            try:
                with open(kontrakt_fil, "r", encoding="utf-8") as f:
                    rader = f.readlines()
                akt_sektion = ""
                for rad in rader:
                    rad_s = rad.strip()
                    if rad_s.startswith("SECTION "):
                        akt_sektion = rad_s
                        sekt_namn = rad_s.split()[1]
                        sym = Symbol(sort="grindregel", typ_namn="OGAT", namn=sekt_namn,
                                     beskrivning="Ogats sektion %s i domskontraktet (docs/spec/41_ogat_kontrakt.md)." % sekt_namn,
                                     kalla="docs/spec/41_ogat_kontrakt.md", vc_version=self.vc_version)
                        self.spec_symboler.append(sym)
                    elif akt_sektion and (rad.startswith("  ") or rad.startswith("\t")):
                        delar = rad_s.split(None, 1)
                        if delar:
                            nyckelord = delar[0]
                            sig = delar[1] if len(delar) > 1 else ""
                            besk = ("Ogats rapportrad %s i %s (docs/spec/41_ogat_kontrakt.md). Signatur: %s"
                                    % (nyckelord, akt_sektion, sig))
                            sym = Symbol(sort="grindregel", typ_namn=akt_sektion, namn=nyckelord,
                                         signatur=sig, beskrivning=besk,
                                         kalla="docs/spec/41_ogat_kontrakt.md", vc_version=self.vc_version)
                            self.spec_symboler.append(sym)
                    elif rad_s.startswith("EYES VERDICT"):
                        sym = Symbol(sort="grindregel", typ_namn="OGAT", namn="VERDICT",
                                     signatur="<PASS|FAIL|INCONCLUSIVE> <orsak>",
                                     beskrivning="Ogats slutdom i domskontraktet (docs/spec/41_ogat_kontrakt.md).",
                                     kalla="docs/spec/41_ogat_kontrakt.md", vc_version=self.vc_version)
                        self.spec_symboler.append(sym)
            except Exception:
                pass

        # Grindar ur docs/spec/50_grindar.md
        grindar_fil = os.path.join(rot, "docs", "spec", "50_grindar.md")
        if os.path.isfile(grindar_fil):
            for g_namn, g_besk in (
                ("KOMPILERING", "Grind 1: syntax, typer, okanda symboler via STruC++ CLI."),
                ("STATISK_ANALYS", "Grind 2: statisk analys av kanda dodsfallor och stilbrott."),
                ("DEKLARATIONSMATCHNING", "Grind 3: deklarationer matchade mot scenens signalkarta."),
                ("ANROPSVALIDERING", "Grind 4: anropsvalidering AST mot verktygsschema."),
                ("OGAT", "Grind 5: vc_eyes simuleringsovervakning av sekvens, timing, grepp."),
                ("KOMPOSITION", "Grind 6: komposition per station och hela linan."),
                ("GRANSKNING", "Grind 7: granskning."),
            ):
                self.spec_symboler.append(
                    Symbol(sort="grindregel", typ_namn="GRIND", namn=g_namn,
                           beskrivning=g_besk, kalla="docs/spec/50_grindar.md",
                           vc_version=self.vc_version)
                )

        # Standarder ur bank/uppgifter/
        bank_kat = os.path.join(rot, "bank", "uppgifter")
        if os.path.isdir(bank_kat):
            import glob
            STD_RE = re.compile(r"\b(?:ISO|IEC|EN|DIN|ANSI|VDI|VDA|RIA)\s?\d{3,5}(?:-\d+)?(?::\d{4})?")
            sedda_std = set()
            for fil in sorted(glob.glob(os.path.join(bank_kat, "*.json"))):
                try:
                    with open(fil, "r", encoding="utf-8") as f:
                        d = json.load(f)
                    fs = d.get("facit_spar") or {}
                    std_text = fs.get("standard", "")
                    for m in STD_RE.findall(std_text + " " + json.dumps(d)):
                        clean = m.strip()
                        kort = clean.split(":")[0]
                        if kort not in sedda_std:
                            sedda_std.add(kort)
                            self.spec_symboler.append(
                                Symbol(sort="standard", typ_namn="STANDARD", namn=clean,
                                       beskrivning="Standardhanvisning ur bankens facit_spar: %s. %s" % (clean, std_text[:200]),
                                       kalla="docs/spec/ och bankens facit_spar",
                                       vc_version=self.vc_version)
                            )
                except Exception:
                    continue

    def _las_hjalpare(self) -> None:
        """vcHelpers-modulerna. Samma form som en typ, egen kalla."""
        kalla = "helpers.xml"
        rot = ET.parse(self._stig(kalla)).getroot()
        for typ in rot.findall("type"):
            modul = _text(typ, "name")
            symbol = Symbol(sort="typ", typ_namn="", namn=modul, kalla=kalla,
                            vc_version=self.vc_version)
            self._lagg(symbol)
            self.hjalpmoduler[modul] = symbol
            for sort, vag in (("metod", "methods/method"),
                              ("egenskap", "properties/property"),
                              ("handelse", "events/event")):
                for nod in typ.findall(vag):
                    # helpers.xml lagger atkomsten (RW/R) i <parameters> for
                    # sina egenskaper. Matt: samma falt, tva storheter.
                    parametrar = " ".join(_text(nod, "parameters").split())
                    atkomst = parametrar if parametrar in ATKOMSTVARDEN else None
                    self._lagg(Symbol(
                        sort=sort, typ_namn=modul, namn=self._rent(_text(nod, "name")),
                        signatur=None if atkomst else parametrar,
                        vardetyp=_text(nod, "type") or None,
                        atkomst=atkomst,
                        beskrivning=_text(nod, "description"),
                        kalla=kalla, vc_version=self.vc_version))

    def _efterbygg(self) -> None:
        """Bygg om uppslagen sa att de pekar pa de berikade symbolerna."""
        self._globala = {}
        self._medlemmar = {namn: {} for namn in self.typer}
        for s in self.symboler:
            if s.sort == "typ":
                continue
            self._globala.setdefault(s.namn, []).append(s)
            if s.sort == "konstant":
                self.konstanter[s.namn] = s
            else:
                self._medlemmar.setdefault(s.typ_namn, {}) \
                    .setdefault(s.namn, []).append(s)

    # ------------------------------------------------------------------- arv

    def arvskedja(self, typ_namn: str) -> List[str]:
        """Typen sjalv forst, sedan foraldrarna i bredden. Cykelsakrad."""
        if typ_namn in self._mro_cache:
            return self._mro_cache[typ_namn]
        kedja: List[str] = []
        ko = [typ_namn]
        sedda = set()
        while ko:
            nu = ko.pop(0)
            if nu in sedda or nu not in self.typer:
                continue
            sedda.add(nu)
            kedja.append(nu)
            ko.extend(self._foraldrar.get(nu, []))
        self._mro_cache[typ_namn] = kedja
        return kedja

    def subtyper(self, typ_namn: str) -> List[str]:
        """Alla typer som arver typen, transitivt."""
        if typ_namn in self._subtyp_cache:
            return self._subtyp_cache[typ_namn]
        ut: List[str] = []
        ko = list(self._barn.get(typ_namn, []))
        sedda = set()
        while ko:
            nu = ko.pop(0)
            if nu in sedda:
                continue
            sedda.add(nu)
            ut.append(nu)
            ko.extend(self._barn.get(nu, []))
        self._subtyp_cache[typ_namn] = ut
        return ut

    def medlem_i_subtyp(self, typ_namn: str, namn: str) -> List[Symbol]:
        """Medlemmen pa nagon typ som arver typ_namn.

        Behovs for att kallan deklarerar grova returtyper: findBehaviour ger
        "vcBehaviour", men det objekt som kommer tillbaka ar i praktiken en
        vcSimInterface eller vcRobotController. Namnet finns alltsa, men pa
        undertypen. Matt i api.xml: vcSimInterface och vcRobotController har
        bada vcBehaviour som <parents>.
        """
        ut: List[Symbol] = []
        for under in self.subtyper(typ_namn):
            ut.extend(self._medlemmar.get(under, {}).get(namn, []))
        return ut

    def typytan(self, typ_namn: str) -> Dict[str, List[Symbol]]:
        """Alla metoder, egenskaper och handelser pa typen, arvet inrakat."""
        if typ_namn in self._ytor:
            return self._ytor[typ_namn]
        yta: Dict[str, List[Symbol]] = {}
        for tn in self.arvskedja(typ_namn):
            for namn, symboler in self._medlemmar.get(tn, {}).items():
                yta.setdefault(namn, []).extend(symboler)
        self._ytor[typ_namn] = yta
        return yta

    # -------------------------------------------------------------- uppslag

    def medlem(self, typ_namn: str, namn: str) -> List[Symbol]:
        """Symbolerna for ett medlemsnamn pa en typ, arvet inrakat. [] = finns ej."""
        return list(self.typytan(typ_namn).get(namn, []))

    def slag_upp(self, namn: str) -> List[Symbol]:
        """Exakt uppslag. Tar "vcRobotController.moveTo" eller ett bart namn.

        Ett pahittat namn ger [] -- aldrig en gissning (docs/spec/46, punkt 3).
        Forslag hamtas separat med narmaste().
        """
        namn = namn.strip()
        if "." in namn:
            typ_namn, _, medlem = namn.rpartition(".")
            if typ_namn in self.typer:
                return self.medlem(typ_namn, medlem)
            for s in self.spec_symboler:
                if s.fullnamn == namn:
                    return [s]
            return []
        ut: List[Symbol] = []
        if namn in self.typer:
            ut.append(self.typer[namn])
        ut.extend(self._globala.get(namn, []))
        for s in self.spec_symboler:
            if s.namn == namn and s not in ut:
                ut.append(s)
        return ut

    def symboler_med_namn(self, namn: str) -> List[Symbol]:
        """Alla symboler med det namnet, oavsett vilken typ de sitter pa."""
        return list(self._globala.get(namn, []))

    def finns(self, namn: str) -> bool:
        """Finns namnet nagonstans i indexet?"""
        return bool(self.slag_upp(namn))

    def sok(self, fras: str, grans: Optional[int] = None) -> List[Traff]:
        """Fritextsokning. Tal delstrang och skiftlage."""
        fras = fras.strip()
        if not fras:
            return []
        lag = fras.lower()
        traffar: List[Traff] = []
        for s in self.symboler + self.spec_symboler:
            rang = self._rang(s, fras, lag)
            if rang is None:
                continue
            traffar.append(Traff(symbol=s, rang=rang,
                                 poang=len(_RANGORDNING) - _RANGORDNING.index(rang)))
        traffar.sort(key=lambda t: (-t.poang, t.symbol.typ_namn, t.symbol.namn,
                                    t.symbol.sort))
        return traffar[:grans] if grans else traffar

    @staticmethod
    def _rang(s: Symbol, fras: str, lag: str) -> Optional[str]:
        namn_lag = s.namn.lower()
        if s.namn == fras:
            return "exakt"
        if namn_lag == lag:
            return "exakt_skiftlagesokant"
        if namn_lag.startswith(lag):
            return "prefix"
        if lag in namn_lag:
            segs = _segment(s.namn)
            if lag in segs or any(seg.startswith(lag) for seg in segs):
                return "delstrang_namn"
            return "delstrang_inuti_ord"
        if lag in s.typ_namn.lower():
            return "delstrang_typ"
        if lag in s.beskrivning.lower():
            return "delstrang_beskrivning"
        return None

    def narmaste(self, namn: str, typ_namn: Optional[str] = None,
                 antal: int = MAX_FORSLAG,
                 tak: int = FORSLAG_AVSTAND_TAK) -> List[Tuple[str, int]]:
        """Nara kanda namn, sorterade pa redigeringsavstand.

        Med typ_namn sokes forst pa den typens yta OCH pa dess undertypers,
        eftersom kallans grova returtyper gor att ett riktigt namn ofta sitter
        pa undertypen (findBehaviour -> vcBehaviour, men namnet finns pa
        vcSimInterface). Racker inte det fylls listan pa ur hela indexet.
        Returnerar (namn, avstand).
        """
        kandidater: List[str] = []
        if typ_namn:
            kandidater = ["%s.%s" % (typ_namn, n) for n in self.typytan(typ_namn)]
            for under in self.subtyper(typ_namn):
                kandidater.extend("%s.%s" % (under, n)
                                  for n in self._medlemmar.get(under, {}))
        ut = self._narmaste_bland(namn, kandidater, antal, tak)
        if len(ut) < antal:
            alla = list(self._globala) + list(self.typer)
            redan = set(n.rpartition(".")[2] for n, _ in ut)
            ut.extend(self._narmaste_bland(
                namn, [n for n in alla if n not in redan], antal - len(ut), tak))
        return ut

    @staticmethod
    def _narmaste_bland(namn: str, kandidater: Iterable[str], antal: int,
                        tak: int) -> List[Tuple[str, int]]:
        if antal <= 0:
            return []
        matt = []
        for kandidat in kandidater:
            d = avstand(namn, kandidat.rpartition(".")[2])
            if d <= tak:
                matt.append((kandidat, d))
        matt.sort(key=lambda x: (x[1], x[0]))
        return matt[:antal]

    def statistik(self) -> Dict[str, int]:
        raknat = {
            "typer": 0, "metoder": 0, "egenskaper": 0, "handelser": 0,
            "konstanter": 0,
        }
        hjalp = {"hjalpmoduler": 0, "hjalpmedlemmar": 0}
        for s in self.symboler:
            hjalpsymbol = s.kalla == "helpers.xml"
            if s.sort == "typ":
                if hjalpsymbol:
                    hjalp["hjalpmoduler"] += 1
                else:
                    raknat["typer"] += 1
            elif hjalpsymbol:
                hjalp["hjalpmedlemmar"] += 1
            else:
                raknat[{"metod": "metoder", "egenskap": "egenskaper",
                        "handelse": "handelser", "konstant": "konstanter"}[s.sort]] += 1
        raknat.update(hjalp)
        raknat["typer_med_foralder"] = len(self._foraldrar)
        raknat["symboler_totalt"] = len(self.symboler)
        raknat.update(self._raknare)
        return raknat


# ------------------------------------------------------------------ validator


@dataclass(frozen=True)
class Varde:
    """Vad validatorn tror att ett uttryck ar.

    sort: typ      -- en kand VC-typ, namnet i .typ
          lista    -- en Python-lista, elementet i .element
          okand_vc -- harlett ur ett VC-objekt men typen ar okand
          enkel    -- ett icke-VC-varde (String, Real, None ...)
          hjalprot -- namnet vcHelpers, roten till hjalpmodulerna
          okand    -- inte VC-harlett alls; domes inte
    """

    sort: str
    typ: Optional[str] = None
    element: Optional["Varde"] = None


OKAND = Varde("okand")
ENKEL = Varde("enkel")
OKAND_VC = Varde("okand_vc")


@dataclass(frozen=True)
class Fel:
    """Ett namn som bevisligen inte finns."""

    sort: str            # okant_medlemsnamn | okant_namn | okand_typ |
                         # okand_konstant | okand_hjalpmodul | ej_parsbar
    namn: str
    rad: int
    text: str
    forslag: Tuple[Tuple[str, int], ...] = ()

    def __str__(self) -> str:
        rad = "rad %d: %s" % (self.rad, self.text)
        if self.forslag:
            rad += " Menade du: %s?" % ", ".join(
                "%s (avstand %d)" % (n, d) for n, d in self.forslag)
        return rad


@dataclass(frozen=True)
class Obestambar:
    """Nagot som inte GAR att doma statiskt. Godkanner aldrig, anklagar aldrig."""

    sort: str            # dynamiskt_uppslag | okand_modulfunktion |
                         # mojlig_anvandaregenskap | okand_listmedlem
    namn: str
    rad: int
    text: str

    def __str__(self) -> str:
        return "rad %d: %s" % (self.rad, self.text)


@dataclass
class Granskning:
    fel: List[Fel] = field(default_factory=list)
    obestambara: List[Obestambar] = field(default_factory=list)
    noteringar: List[str] = field(default_factory=list)
    sedda_namn: "Counter[str]" = field(default_factory=Counter)

    @property
    def kontrollerade_namn(self) -> int:
        """Harledd ur sedda_namn - aldrig en egen rakning.

        Stod forst som ett eget falt som atta stallen okade for hand. En sadan
        siffra gar inte att revidera: "584 kontrollerade" kan inte provas mot
        nagonting, och om ett stalle okade utan att prova ett namn hade ingen
        sett det. Nu ar talet summan av mangdens medlemmar, sa det kan inte
        saga nagot annat an vad som faktiskt slogs upp.
        """
        return sum(self.sedda_namn.values())

    def rakna(self, namn: str) -> None:
        """Rakna ETT kontrollerat namn och behall vilket det var."""
        self.sedda_namn[namn] += 1

    @property
    def godkand(self) -> bool:
        """Fail-closed: bade fel och obestambarheter stoppar (I3)."""
        return not self.fel and not self.obestambara

    def rapport(self) -> str:
        rader = []
        if self.fel:
            rader.append("FEL (%d):" % len(self.fel))
            rader.extend("  " + str(f) for f in self.fel)
        if self.obestambara:
            rader.append("OBESTAMBART (%d), gar inte att avgora statiskt:"
                         % len(self.obestambara))
            rader.extend("  " + str(o) for o in self.obestambara)
        if self.noteringar:
            rader.extend("NOTERING: " + n for n in self.noteringar)
        rader.append("godkand: %s (kontrollerade %d namn)"
                     % ("ja" if self.godkand else "nej", self.kontrollerade_namn))
        return "\n".join(rader)


class Validator(object):
    """Domer VC-namn i en kodstrang mot indexet.

    Regeln: ett namn som bevisligen inte finns ar ett FEL med forslag. Ett namn
    som inte GAR att avgora ar OBESTAMBART -- och godkanns inte heller.
    """

    def __init__(self, index: ApiIndex):
        self.index = index
        self._dynamiska_typer = self._typer_som_skapar_egenskaper()
        self._handelseparametrar = self._parametrar_per_handelse()

    def _typer_som_skapar_egenskaper(self) -> frozenset:
        """Typer vars objekt kan bara egenskaper som ingen kalla kanner till.

        Matt kriterium, inte en handskriven lista: typen har createProperty
        eller getProperty pa sin yta.
        """
        ut = set()
        for typ_namn in self.index.typer:
            yta = self.index.typytan(typ_namn)
            if "createProperty" in yta or "getProperty" in yta:
                ut.add(typ_namn)
        return frozenset(ut)

    def _parametrar_per_handelse(self) -> Dict[str, List[str]]:
        """Deklarerade parametertyper per handelsenamn, ur api.xml.

        VC:s skript ar hakar: def OnComponentAdded(component). Handelsen
        deklarerar sin parameterlista ("vcComponent component"), sa haken far
        typade parametrar i stallet for otypade -- utan det gar namnen i en
        hakkropp inte att doma alls.

        Matt: 15 handelsenamn har OLIKA signaturer pa olika typer (OnSignalTrigger
        har tva). De hoppas over: en tvetydig kalla far inte bli en gissning.
        """
        sedd: Dict[str, Optional[str]] = {}
        tvetydiga = set()
        for symbol in self.index.symboler:
            if symbol.sort != "handelse" or symbol.signatur is None:
                continue
            if symbol.namn in sedd and sedd[symbol.namn] != symbol.signatur:
                tvetydiga.add(symbol.namn)
            sedd[symbol.namn] = symbol.signatur
        ut: Dict[str, List[str]] = {}
        for namn, signatur in sedd.items():
            if namn in tvetydiga:
                continue
            typer = self._parametertyper(signatur)
            if typer:
                ut[namn] = typer
        return ut

    @staticmethod
    def _parametertyper(signatur: str) -> List[str]:
        """["vcComponent component", ...] -> ["vcComponent", ...]."""
        if signatur.strip() in ("", "None"):
            return []
        typer = []
        for del_ in signatur.split(","):
            ord_ = del_.split()
            if not ord_:
                return []
            typer.append(ord_[0])
        return typer

    # -------------------------------------------------------------- ingangen

    def granska(self, kod: str) -> Granskning:
        g = Granskning()
        try:
            trad = ast.parse(kod)
        except SyntaxError as e:
            text = "koden gar inte att parsa: %s (rad %s)" % (e.msg, e.lineno)
            if _PY2PRINT.search(kod):
                text += ". Ser ut som en Python 2-print; VC 4.10 kor 2.7 men" \
                        " validatorn parsar med Python 3 och kan inte doma den."
            g.fel.append(Fel(sort="ej_parsbar", namn="", rad=e.lineno or 0,
                             text=text))
            return g
        self._g = g
        self._bundna = self._bundna_namn(trad)
        self._satser(trad.body, {})
        return g

    @staticmethod
    def _bundna_namn(trad: ast.AST) -> frozenset:
        """Namn som koden sjalv binder. Ett sadant namn ar inte ett VC-namn."""
        ut = set()
        for nod in ast.walk(trad):
            if isinstance(nod, ast.Name) and isinstance(nod.ctx, (ast.Store, ast.Del)):
                ut.add(nod.id)
            elif isinstance(nod, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                ut.add(nod.name)
            elif isinstance(nod, ast.arg):
                ut.add(nod.arg)
            elif isinstance(nod, (ast.Import, ast.ImportFrom)):
                for alias in nod.names:
                    ut.add((alias.asname or alias.name).split(".")[0])
        return frozenset(ut)

    # -------------------------------------------------------------- statser

    def _satser(self, kropp: Sequence[ast.stmt], env: Dict[str, Varde]) -> None:
        for sats in kropp:
            self._sats(sats, env)

    def _sats(self, sats: ast.stmt, env: Dict[str, Varde]) -> None:
        if isinstance(sats, ast.Assign):
            varde = self._ut(sats.value, env)
            for mal in sats.targets:
                self._bind(mal, varde, env)
        elif isinstance(sats, (ast.AnnAssign, ast.AugAssign)):
            if sats.value is not None:
                varde = self._ut(sats.value, env)
                self._bind(sats.target, varde, env)
        elif isinstance(sats, (ast.For, ast.AsyncFor)):
            self._bind(sats.target, self._element(self._ut(sats.iter, env)), env)
            self._satser(sats.body, env)
            self._satser(sats.orelse, env)
        elif isinstance(sats, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in sats.decorator_list:
                self._ut(d, env)
            self._satser(sats.body, self._hakmiljo(sats, env))
        elif isinstance(sats, (ast.Import, ast.ImportFrom)):
            self._import(sats)
        else:
            for _falt, varde in ast.iter_fields(sats):
                for x in (varde if isinstance(varde, list) else [varde]):
                    if isinstance(x, ast.expr):
                        self._ut(x, env)
                    elif isinstance(x, ast.stmt):
                        self._sats(x, env)
                    elif isinstance(x, ast.excepthandler):
                        self._satser(x.body, env)
                    elif isinstance(x, ast.withitem):
                        v = self._ut(x.context_expr, env)
                        if x.optional_vars is not None:
                            self._bind(x.optional_vars, v, env)

    def _hakmiljo(self, sats, env: Dict[str, Varde]) -> Dict[str, Varde]:
        """Miljon inne i en funktion. Ar den en VC-hake blir parametrarna typade."""
        inre = dict(env)
        typer = self._handelseparametrar.get(sats.name)
        argument = list(sats.args.args)
        if typer and len(argument) == len(typer):
            for arg, typ_namn in zip(argument, typer):
                inre[arg.arg] = self._typ_varde(typ_namn)
        return inre

    def _import(self, sats) -> None:
        namn = []
        if isinstance(sats, ast.ImportFrom):
            namn.append(sats.module or "")
        namn.extend(a.name for a in sats.names if isinstance(sats, ast.Import))
        for modul in namn:
            if not modul.startswith("vcHelpers"):
                continue
            if modul == "vcHelpers" or modul in self.index.hjalpmoduler:
                continue
            self._g.rakna(modul)
            self._g.fel.append(Fel(
                sort="okand_hjalpmodul", namn=modul, rad=sats.lineno,
                text="hjalpmodulen %s finns inte i helpers.xml" % modul,
                forslag=tuple(self._narmaste_hjalpmodul(modul))))

    def _narmaste_hjalpmodul(self, modul: str) -> List[Tuple[str, int]]:
        matt = [(m, avstand(modul, m)) for m in self.index.hjalpmoduler]
        matt.sort(key=lambda x: (x[1], x[0]))
        return [x for x in matt if x[1] <= FORSLAG_AVSTAND_TAK][:MAX_FORSLAG]

    def _bind(self, mal: ast.expr, varde: Varde, env: Dict[str, Varde]) -> None:
        if isinstance(mal, ast.Name):
            env[mal.id] = varde
        elif isinstance(mal, (ast.Tuple, ast.List)):
            for delmal in mal.elts:
                self._bind(delmal, self._element(varde), env)
        elif isinstance(mal, (ast.Attribute, ast.Subscript)):
            self._ut(mal, env)

    # ------------------------------------------------------------- uttrycken

    def _ut(self, nod: Optional[ast.expr], env: Dict[str, Varde]) -> Varde:
        if nod is None:
            return OKAND
        if isinstance(nod, ast.Name):
            return self._namn(nod, env)
        if isinstance(nod, ast.Attribute):
            return self._attribut(nod, env, ar_anrop=False)
        if isinstance(nod, ast.Call):
            return self._anrop(nod, env)
        if isinstance(nod, ast.Subscript):
            bas = self._ut(nod.value, env)
            if isinstance(nod.slice, ast.expr):
                self._ut(nod.slice, env)
            if bas.sort == "lista":
                return bas.element or OKAND_VC
            if bas.sort in ("typ", "okand_vc"):
                return OKAND_VC
            return OKAND
        if isinstance(nod, (ast.List, ast.Tuple, ast.Set)):
            element = OKAND
            for e in nod.elts:
                element = self._ut(e, env)
            return Varde("lista", element=element)
        if isinstance(nod, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            inre = dict(env)
            self._generatorer(nod.generators, inre)
            return Varde("lista", element=self._ut(nod.elt, inre))
        if isinstance(nod, ast.DictComp):
            inre = dict(env)
            self._generatorer(nod.generators, inre)
            self._ut(nod.key, inre)
            self._ut(nod.value, inre)
            return OKAND
        if isinstance(nod, ast.Lambda):
            self._ut(nod.body, dict(env))
            return OKAND
        if isinstance(nod, ast.Constant):
            return ENKEL
        # Allt ovrigt: gar igenom barnen sa inga namn missas, men ger inget varde.
        for _falt, varde in ast.iter_fields(nod):
            for x in (varde if isinstance(varde, list) else [varde]):
                if isinstance(x, ast.expr):
                    self._ut(x, env)
        return OKAND

    def _generatorer(self, generatorer, env: Dict[str, Varde]) -> None:
        for gen in generatorer:
            self._bind(gen.target, self._element(self._ut(gen.iter, env)), env)
            for villkor in gen.ifs:
                self._ut(villkor, env)

    def _element(self, varde: Varde) -> Varde:
        if varde.sort == "lista":
            return varde.element or OKAND_VC
        if varde.sort in ("typ", "okand_vc"):
            return OKAND_VC
        return OKAND

    def _namn(self, nod: ast.Name, env: Dict[str, Varde]) -> Varde:
        namn = nod.id
        if namn in env:
            return env[namn]
        if namn == "vcHelpers":
            return Varde("hjalprot")
        if namn in _DYNAMISKA:
            return OKAND
        if namn not in self._bundna:
            if _KONSTANTMONSTER.match(namn):
                self._g.rakna(namn)
                if namn not in self.index.konstanter:
                    self._g.fel.append(Fel(
                        sort="okand_konstant", namn=namn, rad=nod.lineno,
                        text="konstanten %s finns inte i constants.xml" % namn,
                        forslag=tuple(self._narmaste_konstant(namn))))
                return ENKEL
            if _TYPMONSTER.match(namn):
                self._g.rakna(namn)
                if namn not in self.index.typer:
                    self._g.fel.append(Fel(
                        sort="okand_typ", namn=namn, rad=nod.lineno,
                        text="typen %s finns inte i API-indexet" % namn,
                        forslag=tuple(self.index.narmaste(namn))))
                return OKAND_VC
        return OKAND

    def _narmaste_konstant(self, namn: str) -> List[Tuple[str, int]]:
        matt = [(k, avstand(namn, k)) for k in self.index.konstanter]
        matt = [x for x in matt if x[1] <= FORSLAG_AVSTAND_TAK]
        matt.sort(key=lambda x: (x[1], x[0]))
        return matt[:MAX_FORSLAG]

    # ---------------------------------------------------------------- anrop

    def _anrop(self, nod: ast.Call, env: Dict[str, Varde]) -> Varde:
        for arg in nod.args:
            self._ut(arg, env)
        for nyckel in nod.keywords:
            self._ut(nyckel.value, env)

        if isinstance(nod.func, ast.Name) and nod.func.id in _DYNAMISKA \
                and nod.func.id not in self._bundna:
            return self._dynamiskt(nod, env)

        if isinstance(nod.func, ast.Attribute):
            return self._attribut(nod.func, env, ar_anrop=True)

        varde = self._ut(nod.func, env)
        if isinstance(nod.func, ast.Name):
            return self._bar_funktion(nod.func, env)
        return varde

    def _dynamiskt(self, nod: ast.Call, env: Dict[str, Varde]) -> Varde:
        """getattr/setattr/eval ... Kan inte domas statiskt.

        Med ett strangkonstant namn GAR det dock: da domes det som ett vanligt
        attributuppslag i stallet for att kastas i obestambarhogen.
        """
        funk = nod.func.id
        if funk in ("getattr", "setattr", "hasattr", "delattr") and len(nod.args) >= 2:
            namnarg = nod.args[1]
            if isinstance(namnarg, ast.Constant) and isinstance(namnarg.value, str):
                bas = self._ut(nod.args[0], env)
                return self._slag(bas, namnarg.value, nod.lineno,
                                  ar_anrop=False)
        self._g.obestambara.append(Obestambar(
            sort="dynamiskt_uppslag", namn=funk, rad=nod.lineno,
            text="%s() slar upp namnet vid korning; det gar inte att avgora"
                 " statiskt vilket VC-namn som traffas" % funk))
        return OKAND_VC

    def _bar_funktion(self, nod: ast.Name, env: Dict[str, Varde]) -> Varde:
        """Ett bart funktionsanrop, t.ex. getApplication().

        vcScript:s modulfunktioner star inte i kallorna. De som ocksa ar metoder
        pa en skripttyp kan harledas darur, och bara da: om alla agare av namnet
        ar overens om returtypen anvands den.
        """
        namn = nod.id
        if namn in self._bundna or namn in env \
                or namn in _INBYGGDA or namn in _PYTHONMEDLEMMAR:
            return OKAND
        symboler = [s for s in self.index.symboler_med_namn(namn)
                    if s.sort in ("metod", "egenskap")]
        if not symboler:
            self._g.obestambara.append(Obestambar(
                sort="okand_modulfunktion", namn=namn, rad=nod.lineno,
                text="%s() ar varken definierad i koden eller kand i indexet;"
                     " vcScript:s modulfunktioner star inte i nagon matt kalla"
                     " sa det gar inte att avgora om namnet finns" % namn))
            return OKAND_VC
        self._g.rakna(namn)
        typer = set(s.vardetyp for s in symboler if s.vardetyp)
        if len(typer) == 1:
            return self._typ_varde(typer.pop())
        return OKAND_VC

    # ------------------------------------------------------------- attribut

    def _attribut(self, nod: ast.Attribute, env: Dict[str, Varde],
                  ar_anrop: bool) -> Varde:
        bas = self._ut(nod.value, env)
        if bas.sort == "hjalprot":
            modul = "vcHelpers.%s" % nod.attr
            self._g.rakna(modul)
            if modul in self.index.hjalpmoduler:
                return Varde("typ", typ=modul)
            self._g.fel.append(Fel(
                sort="okand_hjalpmodul", namn=modul, rad=nod.lineno,
                text="hjalpmodulen %s finns inte i helpers.xml" % modul,
                forslag=tuple(self._narmaste_hjalpmodul(modul))))
            return OKAND_VC
        return self._slag(bas, nod.attr, nod.lineno, ar_anrop)

    def _slag(self, bas: Varde, namn: str, rad: int, ar_anrop: bool) -> Varde:
        if bas.sort == "typ":
            return self._slag_pa_typ(bas.typ, namn, rad, ar_anrop)
        if bas.sort == "lista":
            return self._slag_pa_lista(namn, rad)
        if bas.sort == "okand_vc":
            return self._slag_utan_typ(namn, rad)
        return OKAND

    def _slag_pa_typ(self, typ_namn: str, namn: str, rad: int,
                     ar_anrop: bool) -> Varde:
        self._g.rakna("%s.%s" % (typ_namn, namn))
        symboler = self.index.medlem(typ_namn, namn)
        if symboler:
            return self._varde_av_medlem(symboler, ar_anrop)

        under = self.index.medlem_i_subtyp(typ_namn, namn)
        if under:
            notering = ("%s.%s finns inte pa %s men pa en undertyp (%s);"
                        " kallan deklarerar grova typer sa detta kan vara en"
                        " korrekt nedcastning"
                        % (typ_namn, namn, typ_namn,
                           ", ".join(sorted(set(s.typ_namn for s in under))[:3])))
            if notering not in self._g.noteringar:
                self._g.noteringar.append(notering)
            return self._varde_av_medlem(under, ar_anrop)

        forslag = tuple(self.index.narmaste(namn, typ_namn=typ_namn))
        narmast = forslag[0][1] if forslag else FORSLAG_AVSTAND_TAK + 1
        anvandaregenskap = (not ar_anrop
                            and typ_namn in self._dynamiska_typer
                            and narmast > NARAMISS_AVSTAND)
        if anvandaregenskap:
            # En anvandardefinierad egenskap syns inte i nagon statisk kalla.
            # Fail-closed: stoppar anda, men anklagar inte.
            self._g.obestambara.append(Obestambar(
                sort="mojlig_anvandaregenskap", namn=namn, rad=rad,
                text="%s.%s finns inte i indexet; %s kan bara"
                     " anvandardefinierade egenskaper sa det gar inte att"
                     " avgora statiskt" % (typ_namn, namn, typ_namn)))
            return OKAND_VC
        vad = "metoden" if ar_anrop else "namnet"
        self._g.fel.append(Fel(
            sort="okant_medlemsnamn", namn="%s.%s" % (typ_namn, namn), rad=rad,
            text="%s %s finns inte pa %s (arvet inrakat)" % (vad, namn, typ_namn),
            forslag=forslag))
        return OKAND_VC

    def _slag_pa_lista(self, namn: str, rad: int) -> Varde:
        if namn in _PYTHONMEDLEMMAR:
            return OKAND
        self._g.rakna(namn)
        if self.index.finns(namn):
            self._g.obestambara.append(Obestambar(
                sort="okand_listmedlem", namn=namn, rad=rad,
                text="%s slas upp pa en lista; namnet finns i API:t men pa en"
                     " typ, inte pa listan sjalv" % namn))
            return OKAND_VC
        self._g.fel.append(Fel(
            sort="okant_namn", namn=namn, rad=rad,
            text="%s finns varken pa en Python-lista eller nagonstans i"
                 " API-indexet" % namn,
            forslag=tuple(self.index.narmaste(namn))))
        return OKAND_VC

    def _slag_utan_typ(self, namn: str, rad: int) -> Varde:
        """Basen ar VC-harledd men otypad. Da racker en global namnkontroll."""
        if namn in _PYTHONMEDLEMMAR:
            return OKAND
        self._g.rakna(namn)
        symboler = self.index.symboler_med_namn(namn)
        if symboler:
            typer = set(s.vardetyp for s in symboler if s.vardetyp)
            if len(typer) == 1:
                return self._typ_varde(typer.pop())
            return OKAND_VC
        self._g.fel.append(Fel(
            sort="okant_namn", namn=namn, rad=rad,
            text="%s finns inte pa nagon typ i API-indexet" % namn,
            forslag=tuple(self.index.narmaste(namn))))
        return OKAND_VC

    def _varde_av_medlem(self, symboler: List[Symbol], ar_anrop: bool) -> Varde:
        for s in symboler:
            if ar_anrop and s.sort == "handelse":
                continue
            if not ar_anrop and s.sort == "metod":
                # En obunden metod. Namnet finns, men vardet ar inget VC-objekt.
                return OKAND
            if s.vardetyp:
                return self._typ_varde(s.vardetyp)
        return OKAND_VC

    def _typ_varde(self, text: str) -> Varde:
        text = (text or "").strip()
        if not text:
            return OKAND_VC
        if text.lower().startswith("list of "):
            return Varde("lista", element=self._typ_varde(text[8:]))
        if text in self.index.typer:
            return Varde("typ", typ=text)
        # helpers.xml namnger sina egna returtyper som "vcHelpers.Robot.vcRobot"
        # medan medlemmarna star under typnamnet "vcHelpers.Robot". Matt i
        # helpers.xml: getRobot -> vcHelpers.Robot.vcRobot.
        for modul in self.index.hjalpmoduler:
            if text.startswith(modul + "."):
                return Varde("typ", typ=modul)
        if text in ("unknown", "<Type>", "&lt;Type&gt;"):
            return OKAND_VC
        # String, Real, Integer, Boolean, Enumeration, None ...: inte VC-objekt.
        return ENKEL


def bygg_index(katalog: Optional[str] = None,
               vc_version: str = VC_VERSION_STANDARD) -> ApiIndex:
    return ApiIndex(katalog=katalog, vc_version=vc_version)


def bygg_validator(katalog: Optional[str] = None) -> Validator:
    return Validator(bygg_index(katalog))
