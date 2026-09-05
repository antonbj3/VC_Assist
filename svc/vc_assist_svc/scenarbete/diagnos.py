# -*- coding: utf-8 -*-
"""DIAGNOSEN: intention 1 - varfor gor scenen som den gor.

Billigast av de tre, och darfor byggd forst: svaret finns REDAN i ogats data
ur en korning som redan gatt. Ingenting behover andras, ingenting behover
koras om, och ingenting far roras (sparr.lasurval).

I1: OGAT FALLER DOMEN. Modulen raknar inte om ett enda matt. Den laser ogats
rapport genom ogats EGET kontrakt (ext/vc_addon/vc_assist/oga_kontrakt.py -
samma modulinstans som ogat skriver med) och citerar RADER. En diagnos som
raknade fram sitt eget tal hade blivit ett andra matt bredvid ogats, och de
tva hade drivit isar tyst.

TRE DOMAR, OCH INGEN AV DEM HETER "ALLT AR BRA"

    BELAGD   ogats egna rader bar svaret, och de star med i .fynd
    FRAGA    ordet operatoren skrev syftar pa flera stationer i rapporten
    OKANT    ogat matte inte det som fragan galler. Det ar INTE ett besked om
             att allt star ratt till - det ar ett besked om att ingen matt
             det. Att svara "nej, den svalter inte" pa en rapport utan
             STARVED-rad vore att lasa tystnad som ett godkannande (I3).

VAD RAPPORTEN INTE BAR, OCH VARFOR DET INTE FYLLS I

Ogats THROUGHPUT-sektion sager VILKEN station som ar flaskhalsen och HUR
mycket, men den bar ingen topologi: den vet inte vem som matar vem. Nar
flaskhalsen ar stationen sjalv gar orsaken darfor inte att lasa ur rapporten,
och modulen namner da de LASANDE verktyg som skulle avgora det i stallet for
att gissa en granne. Listan ligger i .nasta_lasningar, och varje namn i den
provas mot registret: ett skrivande verktyg far aldrig sta i en diagnos.

Endast standardbiblioteket plus tjanstens egna lager.
"""
from __future__ import annotations

import os
import sys

from ..plan.harkomst import normalisera
from . import sparr

_HAR = os.path.dirname(os.path.abspath(__file__))
_EXT = os.path.normpath(os.path.join(_HAR, "..", "..", "..",
                                     "ext", "vc_addon", "vc_assist"))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import oga_kontrakt as K  # noqa: E402

BELAGD = "BELAGD"
FRAGA = "FRAGA"
OKANT = "OKANT"

# TRE SORTERS "GAR INTE ATT AVGORA", OCH DE HAR MOTSATTA ATGARDER.
#
# Ett matt som bara skiljer den forsta kollapsar de tva andra till "avgjort",
# och det ar falsk trygghet av precis den sort ogat finns for att fanga. Ett
# OKANT utan sort sager "vi vet inte" och doljer att atgarderna ar olika:
#
#   MATBART      en matning loser det. Kor om med kravet deklarerat, sa
#                skriver ogat raden. INGEN fraga till operatoren (fragor.py).
#   ANNAN_SORT   mer av SAMMA matning loser det aldrig. Rapporten bar ingen
#                topologi, hur manga ganger den an kors; det kravs en annan
#                observabel, och .nasta_lasningar namner den.
#   OLOSLIGT     fragan gar inte att stalla som den ar stalld. Stationen
#                finns inte i det som mattes, och da ar det fragan som ska
#                omformuleras, inte matningen som ska goras om.
OKANT_MATBART = "OKANT_MATBART"
OKANT_ANNAN_SORT = "OKANT_ANNAN_SORT"
OKANT_OLOSLIGT = "OKANT_OLOSLIGT"
OKANTSORTER = (OKANT_MATBART, OKANT_ANNAN_SORT, OKANT_OLOSLIGT)

# Sektionen svalt och flaskhals star i. Namnet hamtas inte ur en strang har
# utan provas mot kontraktets egen lista vid import, sa att en omdopt sektion
# blir ett fel och inte en tyst tom diagnos.
SEKTION = "THROUGHPUT"
if SEKTION not in K.SEKTIONER:
    raise ImportError(
        "ogats kontrakt har ingen sektion %r langre; diagnosen laser en "
        "sektion som inte finns och skulle svara OKANT om varje fraga"
        % (SEKTION,))

# Radernas nyckelord, ur oga_kontrakt.RADER. Samma kontroll: ett nyckelord
# som fallit ur grammatiken ska falla vid import.
NYCKELORD = ("STATION", "STARVED", "BLOCKED", "BOTTLENECK")
for _n in NYCKELORD:
    if (SEKTION, _n) not in K.RADER:
        raise ImportError(
            "ogats kontrakt har ingen rad %s/%s langre" % (SEKTION, _n))

# De lasande verktyg som avgor VEM som matar en svaltande station. Rapporten
# bar ingen topologi, och de har tva ar vagen till den. Namnen provas mot
# registret i _granska_lasningar innan de lamnas ut.
LASNINGAR_FOR_TOPOLOGIN = ("list_connections", "list_flow_connectors")
# De lasande verktyg som delar upp en stations tid pa dess tillstand. Ogats
# STARVED-rad ger summan; de har ger fordelningen.
LASNINGAR_FOR_TIDEN = ("layout_statistics", "station_state_times")


class Diagnos(object):
    """Svaret, med ogats egna rader som belagg."""

    __slots__ = ("dom", "mal", "fynd", "orsak_station", "kandidater",
                 "nasta_lasningar", "skal", "sort")

    def __init__(self, dom, mal, fynd=(), orsak_station="", kandidater=(),
                 nasta_lasningar=(), skal=(), sort=""):
        if dom == OKANT and sort not in OKANTSORTER:
            raise ValueError(
                "ett OKANT utan sort doljer att de tre sorterna har motsatta "
                "atgarder; sorterna ar %s" % ", ".join(OKANTSORTER))
        self.sort = sort
        self.dom = dom
        self.mal = mal
        self.fynd = tuple(fynd)
        self.orsak_station = orsak_station
        self.kandidater = tuple(kandidater)
        self.nasta_lasningar = tuple(nasta_lasningar)
        self.skal = tuple(skal)

    def __repr__(self):
        return "Diagnos(%s, %s)" % (self.dom, self.mal)

    def harkomster(self):
        """Varje fynd som en scenharkomst ur ogat, sa att sparren kan prova."""
        return tuple(sparr.ur_ogat(rad) for rad in self.fynd)

    def fragor(self):
        """De oppna fragorna, med VEM som kan svara pa var och en.

        En MATBART blir en matningsfraga och gar aldrig till operatoren; en
        FRAGA over flera stationer ar ett operatorsval. Skillnaden ar
        kravformulering_v1.py:s, och den ar hela skalet diagnosen kan koras
        utan att nagon manniska stors.
        """
        from . import fragor as F
        if self.dom == FRAGA:
            return (F.Fraga(
                "vilken station menar du?", F.OPERATORSVAL,
                kandidater=self.kandidater,
                skal="ingen matning kan avgora vilken av dem du syftade pa"),)
        if self.dom == OKANT and self.sort == OKANT_MATBART and self.nasta_lasningar:
            return (F.Fraga(
                "vad sager en korning dar kravet ar deklarerat?", F.MATNING,
                verktyg=self.nasta_lasningar,
                skal="ogat matter svalt mot ett DEKLARERAT krav; utan kravet "
                     "skrevs raden aldrig"),)
        if self.dom == OKANT and self.sort == OKANT_ANNAN_SORT and self.nasta_lasningar:
            return (F.Fraga(
                "vem matar den har stationen?", F.MATNING,
                verktyg=self.nasta_lasningar,
                skal="ogats rapport bar ingen topologi; mer av samma matning "
                     "svarar aldrig pa det"),)
        return ()

    def text(self):
        rader = ["DIAGNOS %s%s: %s" % (self.dom,
                                       " (%s)" % self.sort if self.sort else "",
                                       self.mal or "hela scenen")]
        for s in self.skal:
            rader.append("    " + s)
        for rad in self.fynd:
            rader.append("    ogat: %s" % rad)
        if self.orsak_station:
            rader.append("    orsaken sitter i %s" % self.orsak_station)
        if self.kandidater:
            rader.append("    kandidater: %s" % ", ".join(self.kandidater))
        if self.nasta_lasningar:
            rader.append("    detta skulle avgora det: %s"
                         % ", ".join(self.nasta_lasningar))
        return "\n".join(rader)


def _rader(rapport):
    for namn, rader in rapport.sektioner:
        if namn == SEKTION:
            for r in rader:
                yield r


def _stationsnamn(rapport):
    """Stationerna rapporten namner, i rapportens egen ordning."""
    ut = []
    for rad in _rader(rapport):
        ord_ = rad.split()
        if len(ord_) < 2 or ord_[0] not in ("STATION", "STARVED", "BLOCKED"):
            continue
        if ord_[1] not in ut:
            ut.append(ord_[1])
    return tuple(ut)


def _granska_lasningar(namn):
    """Bara verktyg som FINNS och som LASER far namnas i en diagnos.

    Kontrollen ar mekanisk och stalls till verktygets deklarerade effect -
    samma falt som lassparren och utforarens routingtabell laser (I12). En
    diagnos som foreslog ett skrivande verktyg hade varit ett rad om att bryta
    den regel modulen finns for att halla.
    """
    from ..verktyg.register import REGISTER
    ut = []
    for n in namn:
        verktyg = REGISTER.get(n)
        if verktyg is None or verktyg.effect != "read":
            continue
        ut.append(n)
    return tuple(ut)


def ur_rapport(rapport_text, mal):
    """Diagnosen for ett mal, ur en ogonrapport. Kastar aldrig (S10)."""
    try:
        rapport = K.las(rapport_text)
    except K.Kontraktsfel as fel:
        # Kontraktets EGEN grinddom, inte en egen formulering. En rapport som
        # inte gar att lasa ar inte ett underlag.
        return Diagnos(OKANT, mal, sort=OKANT_OLOSLIGT, skal=[
            "ogats rapport gick inte att lasa: %s" % fel,
            "kontraktets dom: %s" % fel.grinddom,
            "en rapport som inte foljer grammatiken blir inte lasbar av att "
            "lasas igen; den maste skrivas om"])

    stationer = _stationsnamn(rapport)
    n = normalisera(mal)
    traffar = tuple(s for s in stationer if n and n in normalisera(s))
    if not traffar:
        return Diagnos(OKANT, mal, sort=OKANT_OLOSLIGT, skal=[
            "ogat namner ingen station som %r kan syfta pa. Rapporten bar %s"
            % (mal, ", ".join(stationer) or "inga stationer alls"),
            "det ar inte ett besked om att stationen ar frisk - det ar ett "
            "besked om att den inte ar matt"])
    if len(traffar) > 1:
        return Diagnos(FRAGA, mal, kandidater=traffar, skal=[
            "%r kan syfta pa %d stationer i ogats rapport. Vilken menar du?"
            % (mal, len(traffar))])

    station = traffar[0]
    svalt = _rad_for(rapport, "STARVED", station)
    if svalt is None:
        return Diagnos(OKANT, station, sort=OKANT_MATBART, skal=[
            "ogat har ingen STARVED-rad for %s. Svalt matt s mot ett DEKLARERAT "
            "krav, och utan kravet matte ogat den aldrig" % station,
            "tystnad ar aldrig ett godkannande (I3): rapporten sager inte att "
            "%s slipper svalta, den sager att ingen mat te det" % station],
            nasta_lasningar=_granska_lasningar(LASNINGAR_FOR_TIDEN))

    fynd = [svalt]
    blockad = _rad_for(rapport, "BLOCKED", station)
    if blockad is not None:
        fynd.append(blockad)
    egen = _rad_for(rapport, "STATION", station)
    if egen is not None:
        fynd.append(egen)

    if svalt.split()[-1] != "EXCEEDED":
        return Diagnos(BELAGD, station, fynd=fynd, skal=[
            "ogat matte svalten och den holl kravet. Fragan utgar fran nagot "
            "raden inte stodjer - %s svalter inte over sitt krav" % station])

    # Svalten ar belagd. Orsaken ar flaskhalsraden, och bara den.
    flaskhals = _flaskhalsrad(rapport)
    if flaskhals is None or flaskhals.split()[1] == "none":
        return Diagnos(BELAGD, station, fynd=fynd, skal=[
            "%s svalter, matt av ogat. Rapporten pekar inte ut nagon flaskhals, "
            "sa VEM som inte matar gar inte att lasa ur den" % station],
            nasta_lasningar=_granska_lasningar(
                LASNINGAR_FOR_TOPOLOGIN + LASNINGAR_FOR_TIDEN))

    fynd.append(flaskhals)
    flaskhalsstation = flaskhals.split()[1]
    if flaskhalsstation == station:
        return Diagnos(OKANT, station, sort=OKANT_ANNAN_SORT, fynd=fynd, skal=[
            "%s svalter, och ogat pekar ut %s sjalv som flaskhalsen. Da sitter "
            "orsaken uppstroms, och rapporten bar ingen topologi som sager vem "
            "det ar" % (station, station)],
            nasta_lasningar=_granska_lasningar(LASNINGAR_FOR_TOPOLOGIN))

    # Flaskhalsen ar en ANNAN station. Det ar svaret, och det star i raden.
    tillstand = flaskhals.split()[2]
    egna = [f for f in fynd if f.startswith("STATION %s " % flaskhalsstation)]
    if not egna:
        rad = _rad_for(rapport, "STATION", flaskhalsstation)
        if rad is not None:
            fynd.append(rad)
    return Diagnos(BELAGD, station, fynd=fynd, orsak_station=flaskhalsstation,
                   skal=[
        "%s svalter darfor att %s ar flaskhalsen och star %s" % (
            station, flaskhalsstation, tillstand),
        "bade svalten och flaskhalsen ar ogats egna rader; ingenting har ar "
        "omraknat (I1)"],
        nasta_lasningar=_granska_lasningar(LASNINGAR_FOR_TIDEN))


def _rad_for(rapport, nyckelord, station):
    for rad in _rader(rapport):
        ord_ = rad.split()
        if len(ord_) > 1 and ord_[0] == nyckelord and ord_[1] == station:
            return rad
    return None


def _flaskhalsrad(rapport):
    for rad in _rader(rapport):
        if rad.split()[:1] == ["BOTTLENECK"]:
            return rad
    return None
