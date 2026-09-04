# -*- coding: utf-8 -*-
"""Ogats provtagande halva. Kors INNE i VC, py2.7.

Provtagaren rors av pumpen (M-08) och laser scenen. Domen fals inte har - den
fals i oga_analys.py, utanfor VC, pa den tidsserie som skrivs har. Uppdelningen
ar avsiktlig: domaren gar da att prova utan VC.

HELA SCENEN PROVTAS. Planens `parts` och `tools` ar en ROLLTILLDELNING - vilka
objekt som ska tolkas som detalj och verktyg i greppanalysen - inte ett filter
for vad som lases. Varje komponent i scenen far sin pose i varje prov, sa ett
objekt som ingen tankte pa anda finns i serien nar man i efterhand fragar
varfor nagot gick fel.

Kalla: docs/spec/40_ogat.md, docs/spec/41_ogat_kontrakt.md, 42_ogat_utbyggt.md
Matt: M-11 (kvaternionens ordning och varldsmatrisens eftersläpning),
      M-03 (pumpens takt), M-13 (vad som dodar pumpen)
"""
from __future__ import absolute_import, division, print_function

import json
import os
import time

import oga_harledning as H
import plats

# Hur ofta serien skrivs till disk. Kontraktet kraver inkrementell skrivning
# sa en avbruten korning anda gar att lasa.
SKRIV_VAR_N_RAD = 100       # PRELIMINAR. Satts av matning M-10.

# Enheterna. TVA storheter, inte en - de var ihopslagna i en enda konstant, och
# det doljer felet i det vanliga fallet: sa lange bade skrivning och lasning gar
# genom samma faktor blir domarna ratt medan varje ABSOLUT millimetertal ar fel.
#
# MATT i M-33: VC:s basenhet ar MILLIMETER (findUnit("mm") har faktor 1.0,
# "m" har 1000.0). Ogats analys raknar daremot i METER - oga_analys.py
# multiplicerar med 1000 pa sju stallen for att fa millimeter.
#
# Darfor: allt som lases UR VC delas med 1000 pa vagen in, och allt som skrivs
# TILL VC multipliceras med 1000 pa vagen ut. Kanonisk enhet i serien ar meter.
VC_TILL_MM = 1.0             # VC:s varldsenhet uttryckt i mm. MATT i M-33.
KANONISK_TILL_VC = 1000.0    # meter -> VC:s varldsenhet. MATT i M-33.

# Fullscenprovtagningens kostnadsstyrning. Pumpens tick har en budget pa
# 25 ms (pump.TICK_BUDGET_S, satt av M-03:s taktmatning). Ogat far en femtedel
# av den; over det glesas SCENEN ut - aldrig rollerna, aldrig tyst.
SCEN_BUDGET_MS = 5.0        # Beslut ur M-03:s takt, se 42_ogat_utbyggt.md.
# Hur manga scenavlasningar som mats innan glesningen andras. En enda dyr
# avlasning ar ett utslag, inte en takt.
GLES_FONSTER = 8            # Beslut, motiverat i 42_ogat_utbyggt.md.
# Hogsta glesningsfaktor. Over den ar serien sa gles att den inte langre ar
# ett underlag, och ogat sager det i stallet for att glesa vidare.
GLES_TAK = 64               # Beslut, motiverat i 42_ogat_utbyggt.md.
# Hur ofta komponentlistan hamtas om, sa nya och borttagna objekt syns.
KOMPONENTLISTA_VAR_N_RAD = 20   # Beslut, motiverat i 42_ogat_utbyggt.md.
# Hur gammalt ett PLC-varde far vara och anda raknas som samtidigt med provet.
PLC_FARSK_S = 0.25          # PRELIMINAR. Satts av matning M-19.
# Hur lange serien far bara ett PLC-varde vidare utan att fa ett nytt. Bortom
# den gransen ar talet inte langre ett varde utan ett minne, och serien visar
# ett HAL med skal i stallet. Kopplaren sager ifran sjalv nar den tappar
# kontakten - den har gransen ar backstoppet for nar kopplaren sjalv ar borta
# och alltsa inte kan saga nagonting alls.
PLC_TYSTNAD_S = 0.5         # Satt av M-42.
# Hur langt bakat en tidsstampel far ligga fore den raknas som en klocka som
# flyttat sig bakat (sim.reset nollar simuleringstiden). Under den ar det
# avrundningsbrus, over den ar det en annan tidsaxel.
PLC_BAKAT_TOL_S = 0.001     # Satt av M-42.


def kvat_fran_vc(vcvektor):
    """VC ger kvaternionen SKALAR-FORST. MATT i M-11.

    q.X foljer cos(theta/2) och ar alltsa skalaren; vektordelen ligger i
    (Y, Z, W). Las man rakt av blir en orord detalj en 180-graders vridning,
    och CARRY SLIPPING faller pa varje korning med en orsak som ser ut att
    sitta i scenen.
    """
    return [vcvektor.Y, vcvektor.Z, vcvektor.W, vcvektor.X]


class Scen(object):
    """Vad provtagaren behover av en scen. Finns for att kunna bytas ut i test.

    Allt utom pose() och signal() har ett tomt standardsvar. Ett tomt svar ar
    INTE ett godkannande: analysen skiljer "ingen frag stalld" fran "fragan
    stalld och obesvarad" och domer INCONCLUSIVE i det senare fallet.
    """

    def konfigurera(self, plan):
        """Anropas en gang, fore forsta provet. Har byggs det som ar dyrt."""
        return self

    def uppdatera(self):
        pass

    def pose(self, spec):
        raise NotImplementedError

    def poser_alla(self):
        """{namn: pose} for HELA scenen, rollerna undantagna. None = ej stodd."""
        return None

    def signal(self, spec):
        raise NotImplementedError

    def leder(self, spec):
        return None

    def ledmal(self, spec):
        return None

    def mindist(self, spec):
        return None

    def stat(self, spec):
        return None

    def traff(self):
        return None


class VcScen(Scen):
    """Den riktiga scenen. Namnger objekt som 'Komponent' eller 'Komponent/Nod'."""

    def __init__(self, app, sim, uppdatera_fore_last=True):
        self.app = app
        self.sim = sim
        # M-11: varldsmatrisen slapar ett scenuppdateringssteg, och varken
        # render() eller flush() hamtar hem den. Bara sim.update() gor det.
        self.uppdatera_fore_last = uppdatera_fore_last
        self._cache = {}
        self.saknade = []
        self.plan = {}
        self.roller = set()
        self._komponenter = None      # cachad lista, hamtas om med jamna mellanrum
        self._servo = {}              # robotspec -> vcServoController
        self._detektorer = {}         # parnamn -> vcCollisionDetector
        self._statistik = {}          # stationsspec -> vcStatistics
        self.ledgranser = {}          # robotspec -> [[lag, hog], ...]
        self.ledtyper = {}            # robotspec -> ["deg" | "mm" | None, ...]

    def uppdatera(self):
        if self.uppdatera_fore_last:
            self.sim.update()

    def _nod(self, spec):
        if spec in self._cache:
            return self._cache[spec]
        delar = spec.split("/", 1)
        comp = self.app.findComponent(str(delar[0]))
        if comp is None:
            self._saknas(spec, "ingen komponent som heter %r" % delar[0])
            return None
        objekt = comp
        if len(delar) == 2:
            objekt = comp.findNode(str(delar[1]))
            if objekt is None:
                self._saknas(spec, "komponenten %r har ingen nod %r"
                             % (delar[0], delar[1]))
                return None
        self._cache[spec] = objekt
        return objekt

    def _saknas(self, spec, varfor):
        post = {"spec": spec, "varfor": varfor}
        if post not in self.saknade:
            self.saknade.append(post)

    def pose(self, spec):
        nod = self._nod(spec)
        if nod is None:
            return None
        try:
            m = nod.WorldPositionMatrix
            p = m.P
            return {"p": [p.X / KANONISK_TILL_VC,
                          p.Y / KANONISK_TILL_VC,
                          p.Z / KANONISK_TILL_VC],
                    "q": kvat_fran_vc(m.getQuaternion())}
        except Exception as e:
            self._saknas(spec, "kunde inte lasa posen: %s" % type(e).__name__)
            return None

    def satt_pose(self, spec, punkt):
        """Satter ett objekts lage. Anvands av bandrivaren, inte av provtagningen."""
        nod = self._nod(spec)
        if nod is None:
            return False
        # translateAbs ar RELATIV i absoluta axlar (matt M-11), sa en absolut
        # position satts som skillnaden mot nuvarande lage.
        m = nod.PositionMatrix
        if len(punkt) >= 4:
            # Fjarde talet ar gir i grader. setWPR nollstaller vridningen, sa
            # den maste satts FORE forflyttningen.
            m.setWPR(0.0, 0.0, float(punkt[3]))
            nod.PositionMatrix = m
            m = nod.PositionMatrix
        # Kanonisk enhet i serien ar METER; VC:s varld ar millimeter (M-33).
        x = punkt[0] * KANONISK_TILL_VC
        y = punkt[1] * KANONISK_TILL_VC
        z = punkt[2] * KANONISK_TILL_VC
        m.translateAbs(x - m.P.X, y - m.P.Y, z - m.P.Z)
        nod.PositionMatrix = m
        return True

    def signal(self, spec):
        delar = spec.split("/", 1)
        if len(delar) != 2:
            self._saknas(spec, "en signal namnges 'Komponent/Signal'")
            return None
        comp = self.app.findComponent(str(delar[0]))
        if comp is None:
            self._saknas(spec, "ingen komponent som heter %r" % delar[0])
            return None
        try:
            beh = comp.findBehaviour(str(delar[1]))
            if beh is None:
                self._saknas(spec, "ingen signal %r" % delar[1])
                return None
            return beh.Value
        except Exception as e:
            self._saknas(spec, "kunde inte lasa signalen: %s" % type(e).__name__)
            return None

    # -- uppsattning ------------------------------------------------------

    def konfigurera(self, plan):
        """Bygger det dyra en gang: detektorer, servostyrningar, statistik.

        Allt som misslyckas hamnar i `saknade`. Det ar avsiktligt att en
        misslyckad uppsattning INTE kastar: en scen utan kollisionsdetektor
        ska ge en dom som sager att avstandet ar obekant, inte en krasch och
        inte ett tyst godkannande.
        """
        plan = dict(plan or {})
        self.plan = plan
        self.roller = set(plan.get("parts") or []) | set(plan.get("tools") or [])
        for spec in (plan.get("joints") or []):
            self._servostyrning(spec, plan)
        for post in (plan.get("mind") or []):
            self._detektor(post, plan)
        for spec in (plan.get("stat") or []):
            self._statistikbeteende(spec)
        return self

    # -- hela scenen ------------------------------------------------------

    def komponenter(self, tvinga=False):
        """Scenens komponenter. Cachad: app.Components bygger en ny lista."""
        if self._komponenter is None or tvinga:
            try:
                self._komponenter = list(self.app.Components)
            except Exception as e:
                self._saknas("app.Components",
                             "kunde inte lasa komponentlistan: %s" % type(e).__name__)
                self._komponenter = []
        return self._komponenter

    def poser_alla(self):
        """Pose for varje komponent i scenen, utom de som redan bar en roll.

        Rollerna provtas separat och i full takt; hade de legat i bada hade
        samma objekt burit tva serier och en skillnad mellan dem hade varit
        omojlig att tolka.
        """
        ut = {}
        for comp in self.komponenter():
            try:
                namn = comp.Name
            except Exception as e:
                self._saknas("app.Components",
                             "en komponent saknar Name: %s" % type(e).__name__)
                continue
            if namn in self.roller:
                continue
            try:
                m = comp.WorldPositionMatrix
                pkt = m.P
                # SAMMA enhet som pose(): kanonisk meter. Fore M-65 lag
                # scenen kvar i VC:s millimeter medan rollerna delats med
                # 1000, och analysen (som multiplicerar med 1000 for att fa
                # mm) sag da varje bakgrundsobjekts driv tusen ganger for
                # stort. Osynligt i varje syntetisk cell, for de skriver
                # meter direkt. Matt i M-65 §2.
                ut[namn] = {"p": [pkt.X / KANONISK_TILL_VC,
                                  pkt.Y / KANONISK_TILL_VC,
                                  pkt.Z / KANONISK_TILL_VC],
                            "q": kvat_fran_vc(m.getQuaternion())}
            except Exception as e:
                self._saknas(namn, "kunde inte lasa posen: %s" % type(e).__name__)
        return ut

    # -- robotleder -------------------------------------------------------

    def _servostyrning(self, spec, plan):
        """Hittar en vcServoController. Namnges 'Robot' eller 'Robot/Beteende'.

        Utan namngivet beteende letas det upp pa FORMEN - ett beteende som
        bar Joints - i stallet for pa VC_SERVOCONTROLLER-konstanten. Skalet
        star i M-15: createBehaviour returnerar tyst None pa en konstant som
        inte ar en beteendetyp, och ett uppslag som bygger pa en konstant i
        skriptets scope faller sonder nar scopet ser annorlunda ut.
        """
        if spec in self._servo:
            return self._servo[spec]
        delar = spec.split("/", 1)
        comp = self.app.findComponent(str(delar[0]))
        if comp is None:
            self._saknas(spec, "ingen komponent som heter %r" % delar[0])
            return None
        ctrl = None
        try:
            if len(delar) == 2:
                ctrl = comp.findBehaviour(str(delar[1]))
            else:
                for beh in comp.Behaviours:
                    if hasattr(beh, "Joints"):
                        ctrl = beh
                        break
        except Exception as e:
            self._saknas(spec, "kunde inte leta upp servostyrningen: %s"
                         % type(e).__name__)
            return None
        if ctrl is None or not hasattr(ctrl, "Joints"):
            self._saknas(spec, "hittade ingen servostyrning med Joints")
            return None
        self._servo[spec] = ctrl
        self._ledmetadata(spec, ctrl, plan)
        return ctrl

    def _ledmetadata(self, spec, ctrl, plan):
        """Ledgranser och ledtyper, en gang. Bada far vara OKANDA.

        MinValue och MaxValue ar UTTRYCK i VC, inte tal. Gar uttrycket inte
        att lasa som ett tal blir gransen okand, och da domer analysen inte pa
        den. Ett gissat gransvarde vore varre an inget.
        """
        granser, typer = [], []
        planens_typer = list((plan.get("ledtyper") or {}).get(spec) or [])
        try:
            leder = list(ctrl.Joints)
        except Exception as e:
            self._saknas(spec, "kunde inte lasa Joints: %s" % type(e).__name__)
            return
        for i, j in enumerate(leder):
            lag = self._tal(getattr(j, "MinValue", None))
            hog = self._tal(getattr(j, "MaxValue", None))
            if lag is None or hog is None:
                granser.append(None)
                self._saknas(spec, "led %d har uttryck som gransvarden (%r, %r)"
                             % (i, getattr(j, "MinValue", None),
                                getattr(j, "MaxValue", None)))
            else:
                granser.append([lag, hog])
            if i < len(planens_typer):
                typer.append(planens_typer[i])
            else:
                typer.append(self._ledtyp(j))
        self.ledgranser[spec] = granser
        self.ledtyper[spec] = typer

    @staticmethod
    def _tal(varde):
        try:
            return float(varde)
        except (TypeError, ValueError):
            return None

    def _ledtyp(self, led):
        """'deg', 'mm' eller None. Okand typ ger None, och da namnges ingen
        fart i en enhet den inte har."""
        for attribut in ("JointServoType", "Type"):
            varde = getattr(getattr(led, "Dof", None), attribut, None)
            if varde is None:
                varde = getattr(led, attribut, None)
            if varde is None:
                continue
            text = str(varde).upper()
            if "ROT" in text or text.endswith("_R"):
                return "deg"
            if "TRANS" in text or "PRISM" in text:
                return "mm"
        return None

    def leder(self, spec):
        ctrl = self._servo.get(spec) or self._servostyrning(spec, self.plan)
        if ctrl is None:
            return None
        try:
            return [float(j.CurrentValue) for j in ctrl.Joints]
        except Exception as e:
            self._saknas(spec, "kunde inte lasa ledvarden: %s" % type(e).__name__)
            return None

    def ledmal(self, spec):
        """Kommenderat varde per led - halften av 'kommenderat mot uppnatt'."""
        ctrl = self._servo.get(spec)
        if ctrl is None:
            return None
        try:
            return [float(ctrl.getJointTarget(i))
                    for i in range(len(list(ctrl.Joints)))]
        except Exception as e:
            self._saknas(spec, "kunde inte lasa ledmal: %s" % type(e).__name__)
            return None

    # -- kollision och minsta avstand -------------------------------------

    def _detektor(self, post, plan):
        """sim.newCollisionDetector() - i API-ytan sedan lange, aldrig anropad.

        `post` ar antingen ett parnamn (en strang) eller
        {"namn":..., "a": [nodspec...], "b": [nodspec...], "tolerans_mm":...}.
        Ett blott parnamn gar INTE att bygga en detektor av; da registreras
        det som saknat och analysen far ingen MINDIST-rad for paret.
        """
        if not isinstance(post, dict):
            self._saknas(str(post), "paret saknar nodlistor; en detektor kraver "
                                    "a och b")
            return None
        namn = post.get("namn") or "%s+%s" % (post.get("a"), post.get("b"))
        if namn in self._detektorer:
            return self._detektorer[namn]
        noder_a = [self._nod(x) for x in (post.get("a") or [])]
        noder_b = [self._nod(x) for x in (post.get("b") or [])]
        noder_a = [n for n in noder_a if n is not None]
        noder_b = [n for n in noder_b if n is not None]
        if not noder_a or not noder_b:
            self._saknas(namn, "en av nodlistorna blev tom")
            return None
        try:
            det = self.sim.newCollisionDetector()
        except Exception as e:
            self._saknas(namn, "newCollisionDetector kastade %s" % type(e).__name__)
            return None
        if det is None:
            self._saknas(namn, "newCollisionDetector gav None")
            return None
        try:
            det.NodeListA = noder_a
            det.NodeListB = noder_b
            tol_mm = float(post.get("tolerans_mm",
                                    (plan or {}).get("mind_tolerans_mm", 100.0)))
            det.Tolerance = tol_mm / VC_TILL_MM
            det.DisplayMinimumDistance = False
            # StopOnCollision maste vara av: ett stopp river simuleringen och
            # med den pumpen (M-13), och da finns ingen som kan rapportera
            # traffen.
            # MATT 2026-09-04: StopOnCollision star i api.xml men finns INTE
            # pa objektet VC returnerar (AttributeError i 4.10). Satts darfor
            # bara om den gar - men den maste forsokas, for ett stopp river
            # simuleringen och med den pumpen (M-13).
            try:
                det.StopOnCollision = False
            except Exception:
                pass
            det.Active = True
        except Exception as e:
            self._saknas(namn, "kunde inte satta upp detektorn: %s" % type(e).__name__)
            return None
        self._detektorer[namn] = det
        return det

    def mindist(self, spec):
        namn = spec.get("namn") if isinstance(spec, dict) else spec
        det = self._detektorer.get(namn)
        if det is None:
            return None
        try:
            traffade = bool(det.testMinimumDistance())
            d = det.getMinimumDistanceDistance()
            p1 = det.getMinimumDistancePoint1()
            p2 = det.getMinimumDistancePoint2()
        except Exception as e:
            self._saknas(namn, "kunde inte lasa minsta avstandet: %s"
                         % type(e).__name__)
            return None
        if d is None:
            return None
        return {"d_mm": float(d) * VC_TILL_MM,
                "p1": self._punkt(p1), "p2": self._punkt(p2),
                "inom_tolerans": traffade}

    @staticmethod
    def _punkt(v):
        """VC:s varldsenhet -> kanonisk meter, samma vag som posen (M-33)."""
        if v is None:
            return [0.0, 0.0, 0.0]
        return [getattr(v, "X", 0.0) / KANONISK_TILL_VC,
                getattr(v, "Y", 0.0) / KANONISK_TILL_VC,
                getattr(v, "Z", 0.0) / KANONISK_TILL_VC]

    def traff(self):
        """Forsta verkliga traffen bland detektorerna, med nod OCH feature."""
        for namn in sorted(self._detektorer):
            det = self._detektorer[namn]
            try:
                if not det.testAllCollisions():
                    continue
                a = det.getHitNodeA()
                b = det.getHitNodeB()
                fa = det.getHitFeatureA()
                fb = det.getHitFeatureB()
            except Exception as e:
                self._saknas(namn, "kunde inte lasa traffen: %s" % type(e).__name__)
                continue
            return [self._namn(a), self._namn(b), self._namn(fa), self._namn(fb)]
        return None

    @staticmethod
    def _namn(objekt):
        if objekt is None:
            return "okand"
        return str(getattr(objekt, "Name", objekt))

    # -- statistik per station --------------------------------------------

    def _statistikbeteende(self, spec):
        if spec in self._statistik:
            return self._statistik[spec]
        delar = spec.split("/", 1)
        comp = self.app.findComponent(str(delar[0]))
        if comp is None:
            self._saknas(spec, "ingen komponent som heter %r" % delar[0])
            return None
        beh = None
        try:
            if len(delar) == 2:
                beh = comp.findBehaviour(str(delar[1]))
            else:
                for b in comp.Behaviours:
                    if hasattr(b, "ComponentsArrived"):
                        beh = b
                        break
        except Exception as e:
            self._saknas(spec, "kunde inte leta upp statistiken: %s"
                         % type(e).__name__)
            return None
        if beh is None or not hasattr(beh, "ComponentsArrived"):
            self._saknas(spec, "hittade inget vcStatistics-beteende")
            return None
        self._statistik[spec] = beh
        return beh

    def stat(self, spec):
        beh = self._statistik.get(spec)
        if beh is None:
            return None
        ut = {}
        # in/out behaller sina namn ur kontraktets eyes.json. De nya falten
        # laggs bredvid, sa en aldre lasare fortsatter fungera.
        for nyckel, attribut in (("in", "ComponentsArrived"),
                                 ("out", "ComponentsDeparted"),
                                 ("cur", "ComponentsCurrent")):
            varde = self._heltal(beh, attribut, spec)
            if varde is not None:
                ut[nyckel] = varde
        for nyckel, attribut in (("idle_pct", "IdlePercentage"),
                                 ("busy_pct", "BusyPercentage"),
                                 ("blocked_pct", "BlockedPercentage"),
                                 ("broken_pct", "BreakPercentage")):
            try:
                ut[nyckel] = float(getattr(beh, attribut))
            except Exception:
                pass
        try:
            ut["state"] = str(beh.State)
        except Exception:
            pass
        return ut or None

    def _heltal(self, beh, attribut, spec):
        try:
            return int(getattr(beh, attribut))
        except Exception as e:
            self._saknas(spec, "kunde inte lasa %s: %s" % (attribut, type(e).__name__))
            return None


class Plckalla(object):
    """Gransnittet mot PLC-bandet i svc/vc_assist_svc/plc/.

    PUSH, inte pull. En OPC UA-lasning inne i pumpens tick skulle ata av
    tick-budgeten pa 25 ms och kan blockera pa natverket; da stannar bade
    provtagningen och bryggan. Den externa sidan skjuter i stallet in sin
    senaste ogonblicksbild med `skjut_in`, och provtagaren tar den som den ar
    - tillsammans med dess ALDER, sa ett gammalt varde aldrig kan gora sig
    till ett samtidigt.
    """

    def __init__(self):
        self.varden = {}
        self.t = None
        self.avbrott = None
        self.n_inskott = 0
        self.n_avbrott = 0

    def skjut_in(self, varden, t=None):
        self.varden = dict(varden or {})
        self.t = None if t is None else float(t)
        self.avbrott = None
        self.n_inskott += 1
        return self

    def bryt(self, skal, t=None):
        """Kontakten ar borta. Vardena SLAPPS, de foljer inte med vidare.

        Tystnad gar inte att skilja fran "inget nytt har hant". Darfor sager
        den yttre sidan ifran uttryckligen nar den inte langre har nagot
        farskt att komma med, och serien far ett hal med skal i stallet for
        gamla tal som ser samtidiga ut.
        """
        self.varden = {}
        self.t = None if t is None else float(t)
        # "%s" i stallet for str(): i py2 kastar str() pa en unicodestrang med
        # aao, och skalet kommer over protokollet som unicode.
        self.avbrott = ("%s" % (skal,))[:200] if skal else "kontakten bruten"
        self.n_avbrott += 1
        return self

    def las(self, t):
        """({tagg: varde}, alder_s, avbrott).

        alder_s ar None nar ingen tidsstampel foljde med, och NEGATIV nar
        stampeln ligger i framtiden. Det senare klipps inte till noll: en
        stampel i framtiden betyder att klockan flyttat sig bakat under
        handerna pa oss, inte att vardet ar farskt.
        """
        if self.avbrott:
            return None, None, self.avbrott
        if not self.varden:
            return None, None, None
        alder = None if self.t is None else float(t) - self.t
        return dict(self.varden), alder, None


class Provtagare(object):
    def __init__(self, scen, plan, sokvag=None, plckalla=None, klocka=None):
        self.scen = scen
        self.plan = dict(plan or {})
        self.rate_hz = float(self.plan.get("rate_hz", 20.0))
        self.intervall = 1.0 / self.rate_hz if self.rate_hz > 0 else 0.05
        # plats.fil(), inte expanduser: de tva sidorna av sommen far inte
        # peka pa olika mappar pa Windows. Se plats.py och M-44.
        self.sokvag = sokvag or plats.fil(plats.OGONFIL)
        self.rader = []
        self.startad = None
        self.t0 = None
        self.nasta_t = None
        self.aktiv = False
        self.n_skrivna = 0
        # Hela scenen provtas som standard. "roller" begransar till de utpekade
        # objekten och finns for en cell dar scenen ar for stor for att lasas
        # alls; det ar ett medvetet val, aldrig ett tyst standardvarde.
        self.scenlage = self.plan.get("scene", "all")
        self.plckalla = plckalla
        self.klocka = klocka or time.time
        # Glesning: mats, antas aldrig. Faktorn andras bara av en MATT kostnad.
        self.gles_faktor = 1
        self.glesningar = []
        self.scenkostnad_ms = []
        self._kostnadsfonster = []
        self._scen_forra = {}
        self._scen_namn = set()
        self._n_scenlast = 0
        self.scen_avstangd = None
        if hasattr(scen, "konfigurera"):
            scen.konfigurera(self.plan)

    # -- livscykel --

    def starta(self, t):
        self.rader = []
        self.startad = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.t0 = float(t)
        self.nasta_t = float(t)
        self.aktiv = True
        return self

    def stoppa(self):
        self.aktiv = False
        self.skriv()
        return self.sokvag

    # -- provtagning --

    def kanske_prov(self, t):
        """Anropas varje pumpvarv. Provtar nar simuleringstiden natt intervallet."""
        if not self.aktiv:
            return False
        t = float(t)
        if t + 1e-9 < self.nasta_t:
            return False
        self.prov(t)
        # Nasta punkt ska ligga PA rutnatet och samtidigt minst ett helt
        # intervall bort. Bara det forsta ger drift efter ett uppehall; bara
        # det andra ger en for kort lucka nar man snapper tillbaka till
        # rutnatet - matt till 0,01 s i ett prov med ojamn pump.
        mal = t + self.intervall
        steg = int((mal - self.nasta_t) / self.intervall)
        if self.nasta_t + steg * self.intervall < mal - 1e-9:
            steg += 1
        self.nasta_t += max(1, steg) * self.intervall
        if len(self.rader) % SKRIV_VAR_N_RAD == 0:
            self.skriv(delvis=True)
        return True

    def prov(self, t):
        self.scen.uppdatera()
        rad = {"t": round(float(t) - self.t0, 4)}
        for grupp, nyckel in (("parts", "parts"), ("tools", "tools")):
            ut = {}
            for spec in (self.plan.get(grupp) or []):
                pose = self.scen.pose(spec)
                if pose is not None:
                    ut[spec] = pose
            if ut:
                rad[nyckel] = ut
        sig = {}
        for spec in (self.plan.get("signals") or []):
            v = self.scen.signal(spec)
            if v is not None:
                sig[spec] = bool(v)
        if sig:
            rad["sig"] = sig
        leder, ledmal = {}, {}
        for spec in (self.plan.get("joints") or []):
            v = self.scen.leder(spec)
            if v is not None:
                leder[spec] = list(v)
            m = self.scen.ledmal(spec)
            if m is not None:
                ledmal[spec] = list(m)
        if leder:
            rad["joints"] = leder
        if ledmal:
            rad["joints_mal"] = ledmal
        mind = {}
        for spec in (self.plan.get("mind") or []):
            namn = spec.get("namn") if isinstance(spec, dict) else spec
            v = self.scen.mindist(spec)
            if v is not None:
                mind[namn] = v
        if mind:
            rad["mind"] = mind
        stat = {}
        for spec in (self.plan.get("stat") or []):
            v = self.scen.stat(spec)
            if v is not None:
                stat[spec] = v
        if stat:
            rad["stat"] = stat
        self._plc(rad, t)
        traff = self.scen.traff()
        if traff:
            rad["hit"] = list(traff)
        self._scen(rad)
        self.rader.append(rad)
        return rad

    def _plc(self, rad, t):
        """PLC-varden pa SAMMA tidsaxel som fysiken - hela poangen med ogat.

        Vardet bar sin ALDER. Ett varde som ar aldre an provet ar inte
        samtidigt med det, och ett fasforhallande raknat pa ett gammalt varde
        vore ett tal utan storhet.

        FYRA utfall, aldrig tva:
          farskt          - varde + alder
          gammalt         - varde + alder + plc_gammal (analysen: INCONCLUSIVE)
          hal av tystnad  - INGA varden, plc_avbrott med skal, plc_gammal
          hal av avbrott  - INGA varden, den yttre sidans egna ord om varfor

        De tva sista slapper vardena med avsikt. En serie som visar inaktuella
        PLC-tal utan att marka dem ar varre an en som visar hal (M-42).
        """
        if self.plckalla is None:
            return
        varden, alder, avbrott = self.plckalla.las(float(t))
        if avbrott:
            rad["plc_avbrott"] = avbrott
            rad["plc_gammal"] = True
            return
        if not varden:
            return
        if alder is None:
            # Fail-closed: utan tidsstampel gar samtidigheten inte att styrka.
            rad["plc"] = dict(varden)
            rad["plc_alder_s"] = None
            rad["plc_gammal"] = True
            return
        if alder < -PLC_BAKAT_TOL_S:
            rad["plc_avbrott"] = (
                "tidsstampeln ligger %.3f s i framtiden; klockan har gatt bakat"
                % (-alder))
            rad["plc_gammal"] = True
            return
        if alder > PLC_TYSTNAD_S:
            rad["plc_avbrott"] = "ingen ny ogonblicksbild pa %.2f s" % alder
            rad["plc_alder_s"] = round(alder, 4)
            rad["plc_gammal"] = True
            return
        rad["plc"] = dict(varden)
        rad["plc_alder_s"] = round(alder, 4)
        if alder > PLC_FARSK_S:
            rad["plc_gammal"] = True

    def _scen(self, rad):
        """Hela scenens poser, delta-lagrade, med MATT kostnadsstyrning."""
        if self.scenlage != "all":
            return
        if self.gles_faktor > 1 and (len(self.rader) % self.gles_faktor) != 0:
            return
        fore = self.klocka()
        poser = self.scen.poser_alla()
        kostnad_ms = (self.klocka() - fore) * 1000.0
        if poser is None:
            if self.scen_avstangd is None:
                self.scen_avstangd = "scenen svarar inte pa poser_alla"
            return
        self._notera_kostnad(kostnad_ms, rad["t"])
        namn = set(poser)
        nya = sorted(namn - self._scen_namn)
        borta = sorted(self._scen_namn - namn)
        forsta = self._n_scenlast == 0
        self._scen_namn = namn
        full = (self._n_scenlast % H.SCEN_FULL_VAR_N_RAD) == 0
        delta, self._scen_forra = H.koda_scen(poser, self._scen_forra, full)
        self._n_scenlast += 1
        rad["scenlast"] = True
        rad["scene"] = delta
        if full:
            rad["scenfull"] = True
        if nya and not forsta:
            rad["scen_nya"] = nya
        if borta:
            rad["scen_borta"] = borta

    def _notera_kostnad(self, ms, t):
        """Glesningen styrs av en MATT kostnad, aldrig av en gissad scenstorlek.

        Varje andring skrivs ner med talet som orsakade den. Ett oga som
        glesar tyst tappar objekt utan att nagon vet om det, och en serie dar
        ett objekt saknas ser likadan ut som en serie dar det stod still.
        """
        self.scenkostnad_ms.append(round(ms, 4))
        self._kostnadsfonster.append(ms)
        if len(self._kostnadsfonster) < GLES_FONSTER:
            return
        fonster = self._kostnadsfonster
        self._kostnadsfonster = []
        median = sorted(fonster)[len(fonster) // 2]
        if median > SCEN_BUDGET_MS:
            if self.gles_faktor >= GLES_TAK:
                if not any(g.get("orsak") == "TAK" for g in self.glesningar):
                    self.glesningar.append(
                        {"t": t, "fran": self.gles_faktor, "till": self.gles_faktor,
                         "median_ms": round(median, 4), "budget_ms": SCEN_BUDGET_MS,
                         "orsak": "TAK"})
                return
            ny = min(GLES_TAK, self.gles_faktor * 2)
            self.glesningar.append(
                {"t": t, "fran": self.gles_faktor, "till": ny,
                 "median_ms": round(median, 4), "budget_ms": SCEN_BUDGET_MS,
                 "orsak": "OVER_BUDGET"})
            self.gles_faktor = ny
        elif median * 2.0 < SCEN_BUDGET_MS and self.gles_faktor > 1:
            # Halveras forst nar kostnaden ligger under HALVA budgeten. Utan
            # den hysteresen pendlar faktorn kring gransen och serien far en
            # takt som varken ar den ena eller den andra.
            ny = max(1, self.gles_faktor // 2)
            self.glesningar.append(
                {"t": t, "fran": self.gles_faktor, "till": ny,
                 "median_ms": round(median, 4), "budget_ms": SCEN_BUDGET_MS,
                 "orsak": "UNDER_BUDGET"})
            self.gles_faktor = ny

    # -- utdata --

    def data(self, delvis=False):
        dur = (self.rader[-1]["t"] if self.rader else 0.0)
        takt = (len(self.rader) / dur) if dur > 0 else 0.0
        d = {
            "v": 1,
            "template": self.plan.get("template", "okand"),
            "run": {"started": self.startad or "okand", "dur_s": round(dur, 3),
                    "samples": len(self.rader), "rate_hz": round(takt, 3)},
            "tracked": {"parts": list(self.plan.get("parts") or []),
                        "tools": list(self.plan.get("tools") or []),
                        "signals": list(self.plan.get("signals") or []),
                        "pairs": list(self.plan.get("mind") or []),
                        "joints": list(self.plan.get("joints") or []),
                        "stations": list(self.plan.get("stat") or []),
                        "scene": sorted(self._scen_namn)},
            "rows": self.rader,
            "scen": self.scenrapport(),
        }
        for nyckel in ("ledgranser", "ledtyper"):
            varde = getattr(self.scen, nyckel, None)
            if varde:
                d[nyckel] = dict(varde)
        saknade = getattr(self.scen, "saknade", None)
        if saknade:
            # Det som INTE gick att lasa ska synas i underlaget. En tyst lucka
            # blir annars en dom pa ofullstandig grund.
            d["saknade"] = list(saknade)
        if delvis:
            d["partial"] = True
        return d

    def scenrapport(self):
        """Vad ogat gjorde med scenen - inklusive det den inte hann med.

        Talen har ar MATTA under korningen. De ligger i serien for att en
        utglesad provtagning ska ga att se i efterhand: en analys som inte vet
        att scenen glesades kan inte skilja "stod still" fran "sags aldrig".
        """
        kostnader = sorted(self.scenkostnad_ms)
        rapport = {"lage": self.scenlage,
                   "gles_faktor": self.gles_faktor,
                   "handelser": list(self.glesningar),
                   "budget_ms": SCEN_BUDGET_MS,
                   "avlasningar": self._n_scenlast,
                   "objekt": len(self._scen_namn)}
        if kostnader:
            rapport["kostnad_ms"] = {
                "n": len(kostnader),
                "median": kostnader[len(kostnader) // 2],
                "max": kostnader[-1],
                "summa": round(sum(kostnader), 4)}
        if self.scen_avstangd:
            rapport["avstangd"] = self.scen_avstangd
        return rapport

    def skriv(self, delvis=False):
        f = open(self.sokvag, "w")
        try:
            json.dump(self.data(delvis=delvis), f)
        finally:
            f.close()
        self.n_skrivna = len(self.rader)
        return self.sokvag


class Bandrivare(object):
    """Flyttar objekt langs en fardig bana, driven av pumpen.

    Finns for att fas 2:s celler ska ga att bygga UTAN ett eget drivskript:
    att skapa ett skriptbeteende stoppar simuleringen och dodar pumpen (M-13).
    Rorelsen drivs darfor av samma varv som provtar den.
    """

    def __init__(self, scen, bana):
        self.scen = scen
        self.objekt = list(bana.get("objekt") or [])
        self.punkter = list(bana.get("punkter") or [])
        self.dt = float(bana.get("dt", 0.05))
        self.t0 = None
        self.i = -1
        self.klar = False

    def starta(self, t):
        self.t0 = float(t)
        self.i = -1
        self.klar = False
        return self

    def kanske_flytta(self, t):
        if self.t0 is None or self.klar or not self.punkter:
            return False
        n = int((float(t) - self.t0) / self.dt)
        if n <= self.i:
            return False
        if n >= len(self.punkter):
            self.klar = True
            n = len(self.punkter) - 1
        self.i = n
        for spec, punkt in zip(self.objekt, self.punkter[n]):
            self.scen.satt_pose(spec, punkt)
        return True
