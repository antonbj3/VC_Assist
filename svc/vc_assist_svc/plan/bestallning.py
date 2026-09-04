# -*- coding: utf-8 -*-
"""Bestallningen: fran operatorens text till en byggplan - eller till ett nej.

Det har ar grinden som stanger fas 16, ordagrant ur docs/spec/70_faser.md:

    "En grundbestallning i fritext blir en detaljerad, korbar byggplan med
     villkor och processordning - och planen AVVISAS nar den ar omojlig, i
     stallet for att byggas halvt."

TRE BESKED, OCH TVA AV DEM AR ETT NEJ

    BYGGBAR       en plan som haller verktygsregistret, bar sitt bevis och
                  vars villkor och processordning inte motsager varandra.
    AVVISAD       nagot GAR INTE. Beskedet namner vad, med operatorens egna ord.
    OFULLSTANDIG  nagot SAKNAS. Beskedet namner fragorna som maste besvaras.

En planerare som alltid producerar en plan ar vardelos: den producerar en plan
ocksa for det omojliga, och da upptacks felet forst nar nagot gar sonder i
scenen. Darfor lamnar `bestall` ALDRIG ut en Byggplan tillsammans med ett nej.
Planen ar None nar beskedet ar AVVISAD eller OFULLSTANDIG, och det ar en form,
inte en overenskommelse.

GRINDARNA I ORDNING, OCH ORDNINGEN AR MATT

    1. HARKOMST     bar varje krav en kalla som gar att sla upp? (harkomst.py)
    2. PROCESSORDNING  ar ordningen acyklisk? (processer.py)
    3. MOTSAGELSE   kan villkoren galla samtidigt? (motsagelse.py)
    4. FRAGOR       ar nagon blockerande fraga obesvarad?
    5. LAYOUT       finns en placering? (layoutmotor.py -> layout/losare.py)
    6. PLANEN       haller stegen verktygsregistret? (byggplan.py)

De tre forsta kostar mikrosekunder och behover varken katalog eller sokning.
Den femte kostar upp till fyra sekunder. MATT i M-63: bestallningen "hogst
2x2 meter" med tre komponenter faller i grind 3 pa ett ytbevis, medan
layoutmotorn brande hela sin nodbudget pa samma scen och andade svara
OBESTAMBART. Att stalla den billiga och exakta grinden fore den dyra och
sokande ar alltsa inte en optimering utan ett battre svar.

Endast standardbiblioteket (plus paketets egna moduler).
"""
from __future__ import annotations

from . import motsagelse as MO
from .fel import Planfel
from .forfining import Forfinare
from .harkomst import granska_alla
from .layoutport import Layoutport
from .layoutmotor import harled_fotavtryck
from .planering import Planerare
from .spec import Antagande, Grundbegaran
from .storheter import Faktarum

BYGGBAR = "BYGGBAR"
AVVISAD = "AVVISAD"
OFULLSTANDIG = "OFULLSTANDIG"

# Grindarna i ordning, med sina koder. Listan ar sluten och lases av
# provprotokollet: en grind som inte star har kors inte, och en grind som star
# har utan att kora ar ett fel i sig.
GRINDAR = ("B1_HARKOMST", "B2_PROCESSORDNING", "B3_MOTSAGELSE", "B4_FRAGOR",
           "B5_LAYOUT", "B6_PLANEN")


class Besked(object):
    """Svaret pa en bestallning. Bar alltid sitt skal."""

    __slots__ = ("status", "spec", "plan", "grind", "problem", "motsagelsedom",
                 "layoutsvar", "processordning", "datablad")

    def __init__(self, status, spec=None, plan=None, grind="", problem=(),
                 motsagelsedom=None, layoutsvar=None, processordning=(),
                 datablad=None):
        self.status = status
        self.spec = spec
        self.plan = plan
        self.grind = grind
        self.problem = list(problem)          # [(kod, text)]
        self.motsagelsedom = motsagelsedom
        self.layoutsvar = layoutsvar
        self.processordning = list(processordning)
        self.datablad = dict(datablad or {})
        if status != BYGGBAR and plan is not None:
            raise Planfel("ett nej far aldrig lamna ut en plan; da byggs den "
                          "halvt anda")

    def __repr__(self):
        return "Besked(%s, %d problem)" % (self.status, len(self.problem))

    @property
    def byggbar(self):
        return self.status == BYGGBAR

    def rader(self):
        """Svaret som rader, i fast ordning. Det har ar det operatoren ser."""
        ut = ["BESKED %s" % self.status]
        if self.grind:
            ut.append("GRIND %s" % self.grind)
        for kod, text in self.problem:
            ut.append("%s %s" % (kod, text))
        if self.processordning:
            ut.append("PROCESSORDNING %s" % " -> ".join(self.processordning))
        if self.motsagelsedom is not None:
            # En grind som inte kordes far aldrig se ut som en grind som gick.
            for storhet, villkor_id in self.motsagelsedom.att_mata:
                ut.append("ATT MATA EFTER BYGGET %s (villkoret %s)"
                          % (storhet, villkor_id))
            for kontroll, skal in self.motsagelsedom.hoppade:
                ut.append("EJ PROVAD %s: %s" % (kontroll, skal))
        if self.spec is not None:
            for a in self.spec.antaganden:
                ut.append("ANTAGET %s = %s" % (a.vad, a.varde))
            for f in self.spec.oppna_fragor():
                ut.append("FRAGA%s %s: %s"
                          % (" (blockerar)" if f.blockerar else "", f.id, f.vad))
        if self.plan is not None:
            ut.append("PLAN %d steg, bredd %d"
                      % (len(self.plan), self.plan.graf.bredd()))
        return ut

    def text(self):
        return "\n".join(self.rader())


def bestall(begaran, katalogindex=None, urikarta=None, motor=None,
            datablad=None, geometri=True):
    """Grundbegaran (eller ren text) -> Besked. Kastar aldrig ett Planfel.

    `motor` ar en layoutmotor som uppfyller layoutport-kontraktet. Utan motor
    hoppas grind 5 over och det SKRIVS UT: en grind som inte kordes far aldrig
    se ut som en grind som gick.
    """
    if isinstance(begaran, str):
        begaran = Grundbegaran("bestallning", begaran, "operator")
    forfinare = Forfinare(katalogindex, urikarta)
    try:
        spec = forfinare.ur_fritext(begaran)
    except Planfel as fel:
        return Besked(AVVISAD, grind="B1_HARKOMST",
                      problem=[("B0_SPECFEL", str(fel))])
    blad = dict(forfinare.datablad)
    for roll, falt in (datablad or {}).items():
        blad.setdefault(roll, {}).update(falt)
    return doma(spec, blad, motor, geometri)


def doma(spec, datablad=None, motor=None, geometri=True):
    """Grindkedjan over en FARDIG spec. Samma dom oavsett hur specen kom till.

    Bankvagen (forfining.ur_bankuppgift) och fritextvagen ska domas av samma
    grindar; annars ar en uppgift ur banken provad mot en annan mattstock an
    en bestallning fran operatoren.
    """
    datablad = dict(datablad or {})
    roller = [d.roll for d in spec.delar]

    # -- 1. harkomsten ---------------------------------------------------
    problem = granska_alla(spec.harkomster(), spec.begaran.text,
                           spec.antaganden, spec.fragor)
    if problem:
        return Besked(AVVISAD, spec, grind="B1_HARKOMST", problem=problem,
                      datablad=datablad)

    # -- 2. processordningen ---------------------------------------------
    problem = spec.processordning.problem(roller)
    if problem:
        return Besked(AVVISAD, spec, grind="B2_PROCESSORDNING",
                      problem=problem, datablad=datablad)
    ordning = spec.processordning.ordning()

    # -- 3. motsagelsen ---------------------------------------------------
    # Robotarnas fotavtryck harleds ur rackvidden INNAN domen, sa att
    # ytbeviset och passformen gar att kora. Utan det blir svaret OKANT for
    # varenda bestallning som innehaller en robot, och en grind som alltid
    # sager okant har slutat mata. Varje harledning lamnar ett markt antagande.
    datablad, harledda = harled_fotavtryck(spec, datablad)
    for vad, varde, motiv in harledda:
        spec.antaganden.append(Antagande(vad, varde, motiv, "katalog"))
    faktarum = Faktarum(spec, datablad)
    dom = MO.granska(spec.villkor, faktarum, spec, geometri)
    if dom.dom in (MO.OMOJLIG, MO.VALET_FALLER):
        return Besked(AVVISAD, spec, grind="B3_MOTSAGELSE",
                      problem=[(k.kod, k.text()) for k in dom.krockar],
                      motsagelsedom=dom, processordning=ordning,
                      datablad=datablad)
    if dom.okanda:
        # En STATISK storhet utan varde. Grinden vet inte om villkoret haller,
        # och da ar svaret en fraga - aldrig ett ja. En storhet som bara ar
        # okand for att scenen inte ar byggd an star i dom.att_mata och
        # blockerar inte: den ar planens verifiering, inte ett hal i datan.
        return Besked(OFULLSTANDIG, spec, grind="B3_MOTSAGELSE",
                      problem=[("B3_OKAND_STORHET", "%s: %s" % (storhet, skal))
                               for storhet, skal in dom.okanda],
                      motsagelsedom=dom, processordning=ordning,
                      datablad=datablad)

    # -- 4. de blockerande fragorna ---------------------------------------
    blockerande = spec.blockerande_fragor()
    if blockerande:
        return Besked(OFULLSTANDIG, spec, grind="B4_FRAGOR",
                      problem=[("B4_OBESVARAD_FRAGA",
                                "%s: %s" % (f.id, f.vad)) for f in blockerande],
                      motsagelsedom=dom, processordning=ordning,
                      datablad=datablad)

    # -- 5 och 6. layouten och planen -------------------------------------
    port = Layoutport(motor) if motor is not None else None
    frigang = (spec.omrade.gang_min_mm
               if spec.omrade is not None and spec.omrade.gang_min_mm is not None
               else None)
    planerare = Planerare(spec, port if frigang is not None else None,
                          frigang, None, datablad)
    try:
        plan = planerare.planera()
    except Planfel as fel:
        return Besked(AVVISAD, spec, grind="B6_PLANEN",
                      problem=[("B6_PLANFEL", str(fel))],
                      motsagelsedom=dom, processordning=ordning,
                      layoutsvar=planerare.layoutsvar, datablad=datablad)

    svar = planerare.layoutsvar
    if svar is not None and svar.konflikt:
        # OMOJLIGT eller OBESTAMT? Skillnaden ar botemedlet. Bar motorn en
        # BLOCKERANDE fraga vars svar skulle andra utfallet - till exempel
        # vilken lasning rackvidden har - da ar ingenting bevisat omojligt;
        # nagot ar obestamt, och det rattas av ett svar och inte av en ny
        # bestallning. Att kalla det avvisat vore ett falskt rott.
        oppen = [f for f in svar.fragor if f.get("blockerar")]
        problem = [("B5_LAYOUT_%s" % svar.status,
                    "%s %s" % (k.get("kod"), k.get("text")))
                   for k in svar.konflikt]
        problem += [("B5_OBESVARAD_FRAGA", "%s: %s" % (f.get("id"),
                                                       f.get("vad")))
                    for f in oppen]
        return Besked(OFULLSTANDIG if oppen else AVVISAD, spec,
                      grind="B5_LAYOUT", problem=problem,
                      motsagelsedom=dom, processordning=ordning,
                      layoutsvar=svar, datablad=datablad)

    brister = plan.granska()
    if brister:
        # En obesvarad fraga som DYKT UPP under planeringen ar ofullstandigt,
        # inte omojligt. Skillnaden ar botemedlet: den ena rattas av ett svar,
        # den andra av en ny bestallning.
        bara_fragor = all(kod == "P7_OBESVARAD_FRAGA" for kod, _t in brister)
        return Besked(OFULLSTANDIG if bara_fragor else AVVISAD, spec,
                      grind="B6_PLANEN", problem=brister,
                      motsagelsedom=dom, processordning=ordning,
                      layoutsvar=svar, datablad=datablad)

    return Besked(BYGGBAR, spec, plan, grind="B6_PLANEN",
                  motsagelsedom=dom, processordning=ordning, layoutsvar=svar,
                  datablad=datablad)
