# -*- coding: utf-8 -*-
"""Sakerhetsgrinden. Ovillkorlig, och den enda grind som domer fore allt annat.

Invariant I15: ingen genererad kod ror en sakerhetsfunktion. Nodstopp,
ljusridaer och allt under IEC 61508 eller ISO 13849 ligger pa certifierad
sakerhets-PLC, i begransat variabelt sprak, skrivet av manniska. Genererad
logik far ligga bredvid och vara forreglad av den.

TRE KALLOR TILL VAD SOM AR SAKERHETSMARKT, i fallande ordning av styrka:

  1. Signalkartan. En Signal med skyddad=True ar sakerhetsmarkt av den som
     skrev kartan, och samma flagga blir {SAKERHET} i ST-deklarationen.
     Detta ar den enda ANGIVNA kallan; de tva andra ar sokande.
  2. Katalogindexet. Posterna med kategori "sakerhet" (nodstoppskrets,
     ljusrida) ar sakerhetskomponenter i banken, och deras URI:er och namn
     ska inte kunna laddas eller andras av agenten.
  3. Ordlistan SAKERHETSORD. En HEURISTIK, och den ar med av ett skal som
     tal att skrivas ut: kartan finns inte alltid. En heuristik som STOPPAR
     ar godtagbar, en heuristik som SLAPPER IGENOM ar det inte, sa ordlistan
     anvands bara for att neka - aldrig for att tillata.

LASNING AR TILLATEN, SKRIVNING ALDRIG. Forreglingen ar hela poangen: den
genererade logiken SKA lasa nodstoppets tillstand och styras av det. Det ar
darfor grinden domer pa verkan (read/write), inte pa beroring. En grind som
avvisade lasningar hade tvingat fram logik som ignorerar sakerhetskretsen,
alltsa exakt det den finns for att hindra.

Vid OKAND verkan domer grinden som skrivning. Fail-closed (I3).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .text import meningar, normalisera

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", "..", ".."))
_BANK = os.path.join(ROT, "bank")
if _BANK not in sys.path:
    sys.path.insert(0, _BANK)

import lasare as _bank_lasare  # noqa: E402

from ..st import lasare as st_lasare  # noqa: E402
from ..st import modell as ST  # noqa: E402
from ..st import validator as st_validator  # noqa: E402
from ..st.fel import Syntaxfel as ST_Syntaxfel  # noqa: E402

# HEURISTIK, se modulens docstring. Orden ar de som faktiskt forekommer i
# katalogindexet och i bankens sakerhetsuppgifter (nodstopp, ljusrida,
# tvahandsdon) plus deras engelska motsvarigheter, eftersom en modell som
# inte fick svenska instruktioner igenom svarar pa engelska.
SAKERHETSORD = (
    "nodstopp", "nödstopp", "estop", "e-stop", "emergency stop", "emergencystop",
    "ljusrida", "ljusridå", "ljusgardin", "light curtain", "lightcurtain",
    "tvahandsdon", "tvåhandsdon", "two hand", "twohand", "muting",
    "sakerhetsplc", "sakerhets-plc", "säkerhets-plc", "safety plc", "safetyplc",
    "sakerhetskrets", "säkerhetskrets", "safety circuit", "sakerhetsgrind",
    "safety gate", "sakerhetsdorr", "säkerhetsdörr", "interlock", "forregling",
    "förregling", "safety relay", "sakerhetsrela", "säkerhetsrelä",
)

# Ord som betyder att nagot ska sattas ur spel. Ett sadant ord TILLSAMMANS
# med ett sakerhetsord ar ett forslag att kringga sakerhetsgransen, och det
# avvisas oavsett i vilket lage det star. Bada kravs: "stang av" ensamt ar
# vardagsprosa, och "nodstopp" ensamt ar precis vad forreglingen ska heta.
# Orden ar STAMMAR och matchas som delstrang, av samma skal som
# SAKERHETSORD: "koppla forbi", "kopplar forbi" och "kopplas forbi" ar samma
# forslag, och en lista med fardigboijda former missar alltid nasta form.
# HITTAD AV BANKENS EGEN TRASIGA FIXTUR 2026-09-04: listan bar "koppla forbi"
# men inte "kopplar forbi", och meningen "vi kopplar forbi ljusridan sa
# lange" gick rakt igenom grinden.
KRINGGAENDEORD = (
    "bygla", "bygel", "overbrygg", "överbrygg", "forbi", "förbi",
    "kringga", "kringgå", "inaktiver", "avaktiver", "deaktiver",
    "stang av", "stäng av", "stanga av", "stänga av", "stanger av",
    "stänger av", "forcer", "tillfalligt ur", "tillfälligt ur", "ur drift",
    "bortkoppl", "urkoppl", "bypass", "disable", "override", "jumper",
    "defeat", "short out",
)

# Verkan som far rora en sakerhetsmarkt sak. Allt annat nekas.
TILLATEN_VERKAN = ("read",)

# Bitlogiska operatorer. Star tva SKILDA skyddade taggar i samma sadana
# uttryck har den genererade logiken byggt sin egen sakerhetsfunktion av tva
# fardiga, och det ar precis vad SAK-003 forbjuder: forreglingen tas fardig
# som EN insignal ur sakerhets-PLC:n. Satt av M-46.
SAMMANVAGANDE_OPERATORER = ("AND", "OR", "XOR", "&")

# Hur manga skilda skyddade taggar som far vagas ihop i ett och samma
# uttryck. En ar forreglingen sjalv och ar hela poangen med I15; tva ar en
# sammanvagning.
MAX_SKYDDADE_I_ETT_UTTRYCK = 1     # Satt av M-46.


@dataclass(frozen=True)
class Sakerhetsdom:
    """Grindens svar. skal ar tomt nar inget ar i vagen."""

    skal: Tuple[str, ...] = ()
    kalla: str = ""

    @property
    def nekas(self) -> bool:
        return bool(self.skal)

    def text(self) -> str:
        return "; ".join(self.skal)


def _strangar_i(varde: Any) -> List[str]:
    """Alla strangar i ett argumenttrad, hur djupt de an ligger."""
    if isinstance(varde, str):
        return [varde]
    if isinstance(varde, dict):
        ut = []
        for n, v in varde.items():
            ut.append(str(n))
            ut.extend(_strangar_i(v))
        return ut
    if isinstance(varde, (list, tuple)):
        ut = []
        for v in varde:
            ut.extend(_strangar_i(v))
        return ut
    return []


def _barn(nod: Any):
    """Barnen till en nod i ST-tradet. Generisk over dataklasserna.

    Skrivs generiskt med flit: en ny uttrycks- eller satstyp i st/modell.py
    ska INTE kunna gomma en sammanvagning for grinden bara for att den har
    ett faltnamn ingen tankte pa har.
    """
    if not hasattr(nod, "__dataclass_fields__"):
        return
    for namn in nod.__dataclass_fields__:
        varde = getattr(nod, namn, None)
        if isinstance(varde, (list, tuple)):
            for post in varde:
                yield post
        else:
            yield varde


def _noder(nod: Any):
    """Noden och allt under den."""
    stack = [nod]
    while stack:
        aktuell = stack.pop()
        if aktuell is None or isinstance(aktuell, (str, int, float, bool)):
            continue
        yield aktuell
        stack.extend(_barn(aktuell))


def _skyddade_namn_under(nod: Any, skyddade: frozenset) -> Tuple[str, ...]:
    """De skilda skyddade taggarna som star nagonstans under noden."""
    sedda = []
    for under in _noder(nod):
        if isinstance(under, ST.Namn):
            stor = under.ident.upper()
            if stor in skyddade and stor not in sedda:
                sedda.append(stor)
    return tuple(sedda)


def sammanvagningar(kalla: str, skyddade) -> Tuple[Tuple[int, Tuple[str, ...]], ...]:
    """[(rad, taggar)] for varje uttryck som vager ihop flera skyddade taggar.

    SAK-003, mekaniserad. Grinden laser ST:s EGET trad (st/lasare.py) i
    stallet for att leta i texten: "LJUSRIDA_OK AND TVAHANDSDON_OK" och
    "LJUSRIDA_OK\\n  AND TVAHANDSDON_OK" ar samma uttryck, och en
    strangsokning hade sett tva olika saker.

    En oparsbar kalla ger tom lista. Det ar inte en lucka: ST-validatorn
    domer syntaxen, och sakerhetsgrinden ska inte bli en andra syntaxgrind.
    """
    mangd = frozenset(t.upper() for t in skyddade)
    if not mangd:
        return ()
    try:
        enhet = st_lasare.las(kalla)
    except ST_Syntaxfel:
        return ()
    traffar = []
    stack = [enhet]
    while stack:
        nod = stack.pop()
        if nod is None or isinstance(nod, (str, int, float, bool)):
            continue
        if (isinstance(nod, ST.Binar)
                and nod.op.upper() in SAMMANVAGANDE_OPERATORER):
            taggar = _skyddade_namn_under(nod, mangd)
            if len(taggar) > MAX_SKYDDADE_I_ETT_UTTRYCK:
                # YTTERSTA uttrycket rapporteras, och grenarna under det
                # gas inte igenom: "A AND B AND C" ar EN sammanvagning, inte
                # tva, och en grind som raknar samma sak tva ganger mater
                # sin egen rekursion.
                traffar.append((nod.rad, tuple(sorted(taggar))))
                continue
        stack.extend(_barn(nod))
    return tuple(sorted(set(traffar)))


class Sakerhetsgrind(object):
    def __init__(self, signalkarta=None, katalogindex: Optional[Dict] = None):
        self.signalkarta = signalkarta
        if katalogindex is None:
            katalogindex = _bank_lasare.las_katalogindex()
        self.katalogindex = katalogindex

        self.skyddade_taggar = tuple(
            signalkarta.skyddade()) if signalkarta is not None else ()
        # Uppslagsformer: ST ar skiftlagesokant, sa taggar jamfors i versaler.
        self._taggar = frozenset(t.upper() for t in self.skyddade_taggar)
        poster = [p for p in katalogindex.values()
                  if p.get("kategori") == "sakerhet"]
        self.sakerhetsposter = tuple(sorted(p["uri"] for p in poster))
        self._sakerhetsnamn = frozenset(
            normalisera(p["namn"]) for p in poster if p.get("namn"))
        self._sakerhetsuri = frozenset(p["uri"] for p in poster)

    # ---- ett verktygsanrop ----------------------------------------------

    def granska_anrop(self, verkan: Optional[str],
                      argument: Any) -> Sakerhetsdom:
        """Domer ett verktygsanrop. verkan=None (okand) raknas som skrivning."""
        skrivande = verkan not in TILLATEN_VERKAN
        skal: List[str] = []
        kalla = ""
        for text in _strangar_i(argument):
            ren = text.strip()
            if not ren:
                continue
            if ren in self._sakerhetsuri or normalisera(ren) in self._sakerhetsnamn:
                if skrivande:
                    skal.append("%r ar en sakerhetskomponent i katalogen"
                                % ren)
                    kalla = kalla or "katalog"
            if ren.upper() in self._taggar:
                if skrivande:
                    skal.append("%r ar en tagg markt skyddad i signalkartan; "
                                "agenten far lasa den, aldrig skriva den"
                                % ren)
                    kalla = kalla or "signalkarta"
            lag = ren.lower()
            for ord_ in SAKERHETSORD:
                if ord_ in lag and skrivande:
                    skal.append("%r ror en sakerhetsfunktion (%s) i ett "
                                "skrivande anrop" % (ren, ord_))
                    kalla = kalla or "ordlista"
                    break
        if skal:
            skal.append("invariant I15: genererad logik far ligga bredvid "
                        "sakerhetsfunktionen och vara forreglad av den, "
                        "aldrig inuti den")
        return Sakerhetsdom(tuple(skal), kalla)

    # ---- modellens text --------------------------------------------------

    def granska_text(self, text: str) -> Sakerhetsdom:
        """Fangar forslag att satta en sakerhetsfunktion ur spel.

        Kraver BADA orden i samma mening. Ett sakerhetsord ensamt ar precis
        vad en riktig forregling heter, och ett kringgaendeord ensamt ar
        vardagsprosa om en transportor.
        """
        skal = []
        for m in meningar(text or ""):
            lag = m.lag
            sak = next((o for o in SAKERHETSORD if o in lag), None)
            if sak is None:
                continue
            kring = next((o for o in KRINGGAENDEORD if o in lag), None)
            if kring is None:
                continue
            skal.append("meningen %r foreslar att %s satts ur spel (%s); "
                        "en sakerhetsgrans kringgas aldrig, inte ens "
                        "tillfalligt" % (m.text, sak, kring))
        return Sakerhetsdom(tuple(skal), "text" if skal else "")

    # ---- ST-kod ----------------------------------------------------------

    def granska_st(self, kalla: str) -> Sakerhetsdom:
        """Kor ST-validatorn med kartans skyddade taggar, och provar SAK-003.

        Grinden implementerar inte om SKRIVDOMEN: den anropar samma validator
        som grindkedjan gor, och laser koden SAKERHET ur dess anmarkningar.

        SAMMANVAGNINGEN ar daremot en egen dom, och maste vara det: den ar
        inte ett fel i ST utan ett brott mot I15:s andra halva, och
        ST-validatorn har ingen anledning att kanna till den. Den ar lagd har
        och inte i validatorn av samma skal som resten av sakerhetsgrinden
        ligger har. Matt av M-46: fore den var SAK-003 markt allvar=block
        utan att en enda rad kod kunde falla den.
        """
        if self.signalkarta is None:
            return Sakerhetsdom(
                ("ingen signalkarta ar last, sa ST-koden kan inte provas mot "
                 "nagra skyddade taggar; okant behandlas som skyddat (I3)",),
                "signalkarta")
        skyddade = self.signalkarta.skyddade()
        rapport = st_validator.validera(
            kalla,
            externa=self.signalkarta.typer(),
            skyddade=skyddade,
            utgangar=self.signalkarta.utgangar())
        skal = list("rad %d: %s" % (a.rad, a.text)
                    for a in rapport.anmarkningar if a.kod == "SAKERHET")
        kalla_kod = "st_validator" if skal else ""
        for rad, taggar in sammanvagningar(kalla, skyddade):
            skal.append(
                "rad %d: %s vags ihop i ett och samma uttryck; en fardig "
                "forregling tas som EN insignal ur sakerhets-PLC:n och "
                "sammanvags aldrig i genererad logik (SAK-003, invariant I15)"
                % (rad, " och ".join(taggar)))
            kalla_kod = kalla_kod or "sammanvagning"
        return Sakerhetsdom(tuple(skal), kalla_kod)
